#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MF6 — ORTAK CARİ ve ORTAK LİSTE SEÇİMİ
============================================

ÖNKOŞUL: MF5 uygulanmış olmalı.

SORUN
-----
Yeni firma bomboş açılıyor: 170 cariyi ve bütün tanım listelerini
(cins, yüzey, ülke, ödeme şekli) yeniden girmek gerekiyor. Zaman
alıcı ve hataya açık.

NE GELİYOR
----------

1) FİRMA AÇARKEN "ORTAK KULLANIM" SEÇİMİ
   İki kutu: ortak cari, ortak liste. İkisi de işaretli, biri, ya
   da hiçbiri olabilir.

2) ORTAK CARİ — KURULUŞTA KOPYALAMA
   İşaretliyse mevcut bütün cariler yeni firmaya da BAĞLANIR; hiçbir
   şey yeniden girilmez. Sonrası AYRI: A'da açılan yeni müşteri B'de
   görünmez.

   Kart ORTAK kaldığı için vergi no, adres ve kişiler tek yerde
   durur; hareketler, bakiye ve risk limiti zaten firma bazında ayrı.

3) CARİ KARTINDA FİRMA SEÇİMİ
   Cari formuna "Hangi firmalarda görünsün" kutuları eklendi. Bir
   müşteriyi sonradan öteki firmaya açmak ya da kapatmak tek tık.
   Yalnızca admin değiştirebilir — görünürlük kaldırmak o firmada
   cariyi kaybettirir.

4) ORTAK LİSTE — CANLI PAYLAŞIM
   İşaretliyse (varsayılan) cins, yüzey, ülke gibi tanımlar bütün
   firmalarda aynıdır; yeni bir cins bir kez girilir, her yerde
   görünür. Sistem bugün zaten böyle.

   İşaretli DEĞİLSE o firma ortak listeleri görmez — ama boş da
   kalmaz: kuruluşta mevcut listelerin bir KOPYASI ona yazılır.
   Yoksa bütün açılır listeler bomboş gelir ve firma kullanılamaz
   hale gelirdi; "paylaşma" demek "sıfırdan başla" demek değil.

DOSYALAR
--------
  models.py              (firma.ortak_liste)
  flask_app.py           (süzgeç, firma açma, cari firmaları)
  templates/firma_sec.html  (giriş ekranındaki yeni firma formu)
  templates/ayarlar.html    (ayarlardaki yeni firma formu)
  templates/cari.html       (cari kartında firma kutuları)

ŞEMA: bir sütun ekleniyor, GÖÇ GEREKMİYOR — açılıştaki SD2 denetimi
eksik sütunu kendisi ekler. Mevcut firmalar için NULL = ortak
(varsayılan davranış korunur).

KULLANIM
--------
  python3 yama_mf6.py            # RAPOR
  python3 yama_mf6.py --uygula
  sudo systemctl restart milestone-erp
"""

import os
import sys
import shutil
import py_compile
import tempfile

UYGULA = '--uygula' in sys.argv
KOK = os.path.dirname(os.path.abspath(__file__))

DOSYA_IMZA = {
    'templates/base.html': 'AKTIF_FIRMA',
    'models.py': 'ortak_liste',
    'flask_app.py': 'def _firma_ortak_liste():',
    'templates/firma_sec.html': 'nOrtakCari',
    'templates/ayarlar.html': 'nfOrtakCari',
    'templates/cari.html': 'cFirmalar',
}
ONKOSUL = {
    'templates/base.html': 'firmaMenuAc',      # MF3
    'models.py': 'class Firma(db.Model)',
    'flask_app.py': 'def _firma_kayit():',     # MF5
    'templates/firma_sec.html': 'const CSRF',
    'templates/ayarlar.html': 'firmaListesiYukle',
    'templates/cari.html': 'function formAc',
}


# ══════════════════════════════════════════════════════════════════
#  flask_app.py
# ══════════════════════════════════════════════════════════════════

SUZGEC = '''            # 2 · ayarlar ve tanım listeleri
            #    MF6: firma "ortak liste" kullanıyorsa NULL satırlar
            #    (cins, yüzey, ülke) da görünür. Kullanmıyorsa
            #    YALNIZCA kendi satırları — kuruluşta bir kopya
            #    yazıldığı için boş kalmaz.
            _wlc(Veriler,
                 ((Veriler.firma_id == _f) | (Veriler.firma_id.is_(None)))
                 if _firma_ortak_liste() else (Veriler.firma_id == _f),
                 include_aliases=True),'''

ORTAK_LISTE_YARDIMCI = '''    def _firma_ortak_liste():
        """Aktif firma ortak tanım listelerini kullanıyor mu?

        HAM SQL ve istek içi önbellek: bu fonksiyon SÜZGECİN içinden
        çağrılıyor, ORM sorgusu açmak kancayı yeniden tetiklerdi
        (CRM-C2'de ölçülmüş tuzak).

        NULL = ortak (varsayılan). MF6'dan önce açılmış firmalarda
        sütun boş; eski davranış korunsun diye ortak sayılır.
        """
        if not has_request_context():
            return True
        _o = getattr(g, '_mf6_ortak_liste', None)
        if _o is not None:
            return _o
        _sonuc = True
        try:
            _f = session.get('firma_id') or _varsayilan_firma()
            if _f:
                with db.engine.connect() as _b:
                    _r = _b.execute(sa_text(
                        'SELECT ortak_liste FROM firma WHERE id = :i'),
                        {'i': _f}).fetchone()
                if _r is not None and _r[0] is not None:
                    _sonuc = bool(_r[0])
        except Exception:
            _sonuc = True
        g._mf6_ortak_liste = _sonuc
        return _sonuc

'''

FIRMA_EKLE = '''            _son = db.session.query(db.func.max(Firma.sira)).scalar() or 0
            # ── MF6 · ORTAK KULLANIM ──
            # Yeni firma bomboş açılıyordu: 170 cari ve bütün tanım
            # listeleri yeniden girilecekti. İki seçenek:
            #   ortak_cari  → mevcut cariler bu firmaya da BAĞLANIR
            #                 (kuruluşta kopyalama; sonrası ayrı)
            #   ortak_liste → cins/yüzey/ülke CANLI paylaşılır
            _ortak_cari = bool(data.get('ortak_cari'))
            _ortak_liste = bool(data.get('ortak_liste'))'''

FIRMA_EKLE_SONRASI = '''            db.session.add(f)
            _log_audit('EKLE', 'firma', ad, yeni={'ad': ad, 'kod': kod,
                                                  'ortak_cari': _ortak_cari,
                                                  'ortak_liste': _ortak_liste})
            ok, hata = _safe_commit(f'Firma ekle: {ad}')'''


CARI_FIRMALARI = '''    def _cari_firma_idleri(cari_idler):
        """MF6 — hangi cari hangi firmalarda görünüyor: {cari_id: [firma…]}.

        Tek sorgu. Cari listesi 170 satır; her satır için ayrı sorgu
        açmak sayfayı dakikalara çıkarırdı.
        """
        _h = {}
        if not cari_idler:
            return _h
        try:
            with firma_atla():          # üyelik tablosu süzülmez
                for _cid, _fid in db.session.query(
                        CariFirma.cari_id, CariFirma.firma_id).filter(
                        CariFirma.cari_id.in_(list(cari_idler))).all():
                    _h.setdefault(_cid, []).append(_fid)
        except Exception as _e:
            app.logger.warning(f'[MF6] cari firma baglari okunamadi: {_e}')
        return _h

    def _cari_firmalari_uygula(cari_id, istenen):
        """MF6 — cari kartındaki firma seçimini üyelik tablosuna işler.

        YALNIZCA ADMIN çağırmalı: bir firmayı listeden çıkarmak o
        firmada cariyi görünmez yapar.

        HİÇ firma seçilmemişse DOKUNULMAZ. Boş listeyi "hepsini kaldır"
        saymak, formu eksik dolduran birinin müşteriyi her yerden
        silmesi demek olurdu.
        """
        if not istenen:
            return 0, 0
        _istenen = {int(x) for x in istenen if str(x).strip().isdigit()}
        if not _istenen:
            return 0, 0
        with firma_atla():
            _gecerli = {f.id for f in Firma.query.filter_by(aktif=True).all()}
            _istenen &= _gecerli
            if not _istenen:
                return 0, 0
            _mevcut = {m.firma_id: m for m in
                       CariFirma.query.filter_by(cari_id=cari_id).all()}
            _eklenen = 0
            for _fid in _istenen - set(_mevcut):
                db.session.add(CariFirma(cari_id=cari_id, firma_id=_fid))
                _eklenen += 1
            _silinen = 0
            for _fid in set(_mevcut) - _istenen:
                db.session.delete(_mevcut[_fid])
                _silinen += 1
        return _eklenen, _silinen

'''


def degisiklikler():
    return [
        # ── models.py ──
        ('models.py', 'MF6-a · firma.ortak_liste',
         "    varsayilan    = db.Column(db.Boolean, default=False, index=True)",
         "    # MF6: tanim listelerini (cins, yuzey, ulke) ORTAK kullanir mi?\n"
         "    # NULL = ortak — MF6'dan once acilmis firmalarda eski davranis\n"
         "    # korunur. Kapaliysa firma yalnizca KENDI satirlarini gorur;\n"
         "    # kurulusta bir kopya yazildigi icin bos kalmaz.\n"
         "    ortak_liste   = db.Column(db.Boolean, default=True)\n"
         "    varsayilan    = db.Column(db.Boolean, default=False, index=True)"),

        # ── flask_app.py ──
        ('flask_app.py', 'MF6-b · ortak liste yardimcisi',
         "    def _firma_kayit():", ORTAK_LISTE_YARDIMCI + "    def _firma_kayit():"),
        ('flask_app.py', 'MF6-c · Veriler suzgeci ortak listeye baglanir',
         """            # 2 · ayarlar: NULL = ortak liste (cins, yüzey, ülke)
            _wlc(Veriler,
                 (Veriler.firma_id == _f) | (Veriler.firma_id.is_(None)),
                 include_aliases=True),""",
         SUZGEC),
        ('flask_app.py', 'MF6-d · firma acarken ortak kullanim secimi',
         "            _son = db.session.query(db.func.max(Firma.sira)).scalar() or 0",
         FIRMA_EKLE),
        ('flask_app.py', 'MF6-e · firma acilinca kopyalama',
         """            db.session.add(f)
            _log_audit('EKLE', 'firma', ad, yeni={'ad': ad, 'kod': kod})
            ok, hata = _safe_commit(f'Firma ekle: {ad}')""",
         FIRMA_EKLE_SONRASI),
        ('flask_app.py', 'MF6-f · cari firma baglantisi yardimcilari',
         "    @app.route('/api/cari', methods=['GET'])", CARI_FIRMALARI
         + "    @app.route('/api/cari', methods=['GET'])"),
        ('flask_app.py', 'MF6-g · cari listesine firmalar alani',
         """                                  'gorunurluk': c.gorunurluk or 'kapali'}
                                 for c in paginated.items],""",
         """                                  'gorunurluk': c.gorunurluk or 'kapali',
                                  # MF6: kartta "hangi firmalarda görünsün"
                                  'firmalar': _cf.get(c.id, [])}
                                 for c in paginated.items],"""),
        ('flask_app.py', 'MF6-h · firma baglari tek sorguda',
         """        return jsonify({'data': [{'id': c.id, 'unvan': c.unvan, 'cari_tip': c.cari_tip, 'telefon': c.telefon,""",
         """        _cf = _cari_firma_idleri(_sayfa_idler)      # MF6
        return jsonify({'data': [{'id': c.id, 'unvan': c.unvan, 'cari_tip': c.cari_tip, 'telefon': c.telefon,"""),
        ('flask_app.py', 'MF6-i · yeni caride firma secimi',
         """            db.session.add(cari)
            _log_audit('EKLE', 'cari', cari.id, yeni={'unvan': cari.unvan, 'tip': cari.cari_tip})
            db.session.commit()""",
         """            db.session.add(cari)
            db.session.flush()
            # MF6: formda firma seçildiyse ona göre bağlanır. Seçim
            # yoksa models.py'deki kanca AKTİF firmaya bağlar.
            if data.get('firmalar') and (session.get('rol') or '').upper() == 'ADMIN':
                _cari_firmalari_uygula(cari.id, data.get('firmalar'))
            _log_audit('EKLE', 'cari', cari.id, yeni={'unvan': cari.unvan, 'tip': cari.cari_tip})
            db.session.commit()"""),
        ('flask_app.py', 'MF6-j · cari guncellemede firma secimi',
         "        _eski_unvan = c.unvan          # BL-16: yeniden adlandirma izi",
         """        # ── MF6 · FİRMA GÖRÜNÜRLÜĞÜ ──
        # Yalnızca admin: bir firmayı listeden çıkarmak o firmada
        # cariyi görünmez yapar. Alan HİÇ gönderilmemişse dokunulmaz.
        if 'firmalar' in data and (session.get('rol') or '').upper() == 'ADMIN':
            try:
                _ek, _sil = _cari_firmalari_uygula(c.id, data.get('firmalar'))
                if _ek or _sil:
                    _log_audit('GUNCELLE', 'cari', c.id,
                               aciklama=f'firma gorunurlugu: +{_ek} / -{_sil}')
            except Exception as _e:
                app.logger.warning(f'[MF6] cari firma baglari yazilamadi: {_e}')

        _eski_unvan = c.unvan          # BL-16: yeniden adlandirma izi"""),
        # ── MF6-k · firma kaydina ortak_liste + kopyalama ──
        ('flask_app.py', 'MF6-k · ortak_liste kaydedilir, kopyalama yapilir',
         """                      varsayilan=False, aktif=True, sira=_son + 1)
            db.session.add(f)""",
         """                      varsayilan=False, aktif=True, sira=_son + 1,
                      ortak_liste=_ortak_liste)
            db.session.add(f)
            db.session.flush()         # f.id lazim

            # ── ORTAK CARİ: kuruluşta KOPYALAMA ──
            # Mevcut bütün cariler yeni firmaya da bağlanır; 170
            # müşteriyi yeniden girmek gerekmez. Sonrası AYRI:
            # A'da açılan yeni müşteri B'de görünmez.
            _kopya_cari = 0
            if _ortak_cari:
                _bagli = {m.cari_id for m in
                          CariFirma.query.filter_by(firma_id=f.id).all()}
                for (_cid,) in db.session.query(Cari.id).all():
                    if _cid in _bagli:
                        continue
                    db.session.add(CariFirma(cari_id=_cid, firma_id=f.id))
                    _kopya_cari += 1

            # ── ORTAK LİSTE KAPALIYSA: listeleri KOPYALA ──
            # "Paylaşma" demek "sıfırdan başla" demek değil. Kopya
            # yazılmazsa cins/yüzey/ülke açılır listeleri bomboş gelir
            # ve firma kullanılamaz olurdu.
            _kopya_liste = 0
            if not _ortak_liste:
                for _v in Veriler.query.filter(
                        Veriler.firma_id.is_(None)).all():
                    db.session.add(Veriler(
                        kategori=_v.kategori, deger=_v.deger,
                        kisaltma=_v.kisaltma, ek_bilgi=_v.ek_bilgi,
                        uzun_deger=_v.uzun_deger, firma_id=f.id))
                    _kopya_liste += 1"""),

        ('flask_app.py', 'MF6-l · sonuc mesajinda kopyalananlar',
         """        _firma_onbellek_dusur()
        return jsonify({'ok': True, 'id': f.id,
                        'mesaj': f'{ad} eklendi. Bilgilerini girmek için '
                                 f'o firmaya geçin.'})""",
         """        _firma_onbellek_dusur()
        _m = f'{ad} eklendi'
        if _kopya_cari:
            _m += f' · {_kopya_cari} cari bağlandı'
        if _kopya_liste:
            _m += f' · {_kopya_liste} liste tanımı kopyalandı'
        _m += '. Bilgilerini girmek için o firmaya geçin.'
        return jsonify({'ok': True, 'id': f.id, 'mesaj': _m,
                        'kopya_cari': _kopya_cari,
                        'kopya_liste': _kopya_liste})"""),

        # ── templates/firma_sec.html ──
        ('templates/firma_sec.html', 'MF6-m · giris ekraninda ortak kullanim',
         """      <div class="alan"><label for="nVno">Vergi no</label>
        <input id="nVno" placeholder="1234567890"></div>""",
         """      <div class="alan"><label for="nVno">Vergi no</label>
        <input id="nVno" placeholder="1234567890"></div>
      <!-- MF6: yeni firma bomboş açılıyordu; 170 cari ve bütün tanım
           listeleri yeniden girilecekti. -->
      <div class="alan">
        <label>Mevcut firmadan ortak kullanılsın</label>
        <label class="kutu"><input type="checkbox" id="nOrtakCari" checked>
          <span>Cari listesi — mevcut müşteri ve tedarikçiler bu firmaya da
          bağlanır. Sonrasında her firma kendi müşterisini ekler.</span></label>
        <label class="kutu"><input type="checkbox" id="nOrtakListe" checked>
          <span>Tanım listeleri — cins, yüzey, ülke, ödeme şekli her
          firmada aynı kalır; bir kez girilen her yerde görünür.</span></label>
        <div class="ipucu">İşaretlemezsen bu firma kendi listesini
          kullanır; kuruluşta mevcut listelerin bir kopyası yazılır.</div>
      </div>"""),
        ('templates/firma_sec.html', 'MF6-n · ortak kullanim bicemi',
         """.sil:hover{color:var(--kirmizi);border-color:var(--kirmizi);background:var(--kirmizi-bg)}""",
         """.sil:hover{color:var(--kirmizi);border-color:var(--kirmizi);background:var(--kirmizi-bg)}
.kutu{display:flex;gap:9px;align-items:flex-start;padding:8px 0;cursor:pointer;
  font-size:.84rem;font-weight:400;color:var(--murekkep);text-transform:none;
  letter-spacing:0}
.kutu input{margin-top:2px;width:15px;height:15px;cursor:pointer;flex:0 0 auto}
.kutu span{line-height:1.45}
.ipucu{color:var(--soluk);font-size:.79rem;line-height:1.45;margin-top:2px}"""),
        ('templates/firma_sec.html', 'MF6-o · secim sunucuya gonderilir',
         """      ad: ad, belge_kodu: kod,
      unvan: (document.getElementById('nUnvan').value || '').trim(),
      vergi_no: (document.getElementById('nVno').value || '').trim()""",
         """      ad: ad, belge_kodu: kod,
      unvan: (document.getElementById('nUnvan').value || '').trim(),
      vergi_no: (document.getElementById('nVno').value || '').trim(),
      ortak_cari: document.getElementById('nOrtakCari').checked,
      ortak_liste: document.getElementById('nOrtakListe').checked"""),

        # ── templates/ayarlar.html ──
        ('templates/ayarlar.html', 'MF6-p · ayarlarda ortak kullanim',
         """        <div class="form-alan"><label>Vergi No</label>
          <input id="nfVno" placeholder="1234567890"></div>""",
         """        <div class="form-alan"><label>Vergi No</label>
          <input id="nfVno" placeholder="1234567890"></div>
      </div>
      <!-- MF6: ortak kullanım seçimi -->
      <div class="form-alan" style="margin-top:10px">
        <label>Mevcut firmadan ortak kullanılsın</label>
        <label style="display:flex;gap:8px;align-items:flex-start;padding:6px 0;
                      font-weight:400;cursor:pointer;font-size:.86rem">
          <input type="checkbox" id="nfOrtakCari" checked
                 style="margin-top:3px;width:15px;height:15px;cursor:pointer">
          <span>Cari listesi — mevcut müşteri ve tedarikçiler bu firmaya da
          bağlanır, yeniden girmen gerekmez.</span></label>
        <label style="display:flex;gap:8px;align-items:flex-start;padding:6px 0;
                      font-weight:400;cursor:pointer;font-size:.86rem">
          <input type="checkbox" id="nfOrtakListe" checked
                 style="margin-top:3px;width:15px;height:15px;cursor:pointer">
          <span>Tanım listeleri — cins, yüzey, ülke her firmada aynı kalır.
          İşaretlemezsen kuruluşta bir kopya yazılır, sonra ayrışır.</span></label>
      </div>
      <div style="display:none">"""),
        ('templates/ayarlar.html', 'MF6-r · secim sunucuya gonderilir',
         """      unvan: (document.getElementById('nfUnvan').value || '').trim(),
      vergi_no: (document.getElementById('nfVno').value || '').trim() }) });""",
         """      unvan: (document.getElementById('nfUnvan').value || '').trim(),
      vergi_no: (document.getElementById('nfVno').value || '').trim(),
      ortak_cari: document.getElementById('nfOrtakCari').checked,
      ortak_liste: document.getElementById('nfOrtakListe').checked }) });"""),

        # ── templates/cari.html ──
        ('templates/cari.html', 'MF6-s · cari kartinda firma kutulari',
         """          <input type="hidden" id="cTip" value="Müşteri">
        </div>""",
         """          <input type="hidden" id="cTip" value="Müşteri">
        </div>
        <!-- MF6: bu cari HANGİ FİRMALARDA görünsün. Tek firma varsa
             blok hiç basılmaz; yalnızca admin değiştirebilir, çünkü
             bir firmayı kaldırmak orada cariyi görünmez yapar. -->
        <div class="form-alan" id="cFirmaAlan" style="display:none">
          <label>Hangi firmalarda görünsün
            <span style="font-weight:400;color:var(--soluk)">(birden çok)</span></label>
          <div id="cFirmalar" style="display:flex;gap:12px;flex-wrap:wrap;padding:7px 0"></div>
        </div>"""),
        ('templates/cari.html', 'MF6-t · formda firma kutulari doldurulur',
         """  document.getElementById('cKisaltma').value = c ? (c.uretici_kisaltma || '') : '';
  tipDegisti();""",
         """  document.getElementById('cKisaltma').value = c ? (c.uretici_kisaltma || '') : '';
  firmaKutulariniDoldur(c ? (c.firmalar || []) : null);   // MF6
  tipDegisti();"""),
        ('templates/cari.html', 'MF6-u · secim kaydedilirken gonderilir',
         """    uretici_kisaltma: (document.getElementById('cKisaltma').value || '').trim().toUpperCase() || null
  };""",
         """    uretici_kisaltma: (document.getElementById('cKisaltma').value || '').trim().toUpperCase() || null,
    // MF6: yalnızca admin gönderir; sunucu da admin değilse yok sayar.
    ...(window.ADMIN && FIRMALAR.length > 1
        ? { firmalar: [...document.querySelectorAll('.firma-kutu:checked')]
              .map(x => parseInt(x.value, 10)) }
        : {})
  };"""),
        ('templates/cari.html', 'MF6-v · firma listesi ve kutu ciz',
         """function formAc(c) {""",
         """/* ── MF6 · CARİ HANGİ FİRMALARDA GÖRÜNÜR ──
   Cari kartı ORTAK; görünürlük cari_firma üyeliğinden geliyor.
   Liste bir kez çekilip saklanır — her form açılışında sorgu
   açmak çekmeceyi yavaşlatırdı. */
let FIRMALAR = [];
async function firmalariYukle() {
  if (!window.ADMIN) return;
  try {
    const d = await api('/api/firma');
    FIRMALAR = (d && d.firmalar || []).filter(f => f.aktif);
  } catch (e) { FIRMALAR = []; }
}

function firmaKutulariniDoldur(secili) {
  const alan = document.getElementById('cFirmaAlan');
  const kap = document.getElementById('cFirmalar');
  if (!alan || !kap) return;
  /* Tek firma varsa seçecek bir şey yok — blok hiç gösterilmez,
     bugünkü cari formu aynen kalır. */
  if (!window.ADMIN || FIRMALAR.length < 2) { alan.style.display = 'none'; return; }
  alan.style.display = '';
  /* Yeni caride AKTİF firma işaretli gelir: kullanıcı zaten o
     firmada çalışıyor ve müşteriyi oraya açıyor. */
  const set = new Set(secili && secili.length ? secili.map(Number)
                                              : [Number(window.AKTIF_FIRMA || 0)]);
  kap.innerHTML = FIRMALAR.map(f => `
    <label style="display:flex;align-items:center;gap:5px;cursor:pointer;font-weight:400">
      <input type="checkbox" class="firma-kutu" value="${f.id}"
             ${set.has(f.id) ? 'checked' : ''}
             style="width:15px;height:15px;cursor:pointer">
      ${kacar(f.ad)}</label>`).join('');
}

function formAc(c) {"""),
        # ── MF6-y/z · BAGLANTI ──
        # MF3'te aynisi olmustu: fonksiyon tanimlandi ama CAGRILMADI.
        # Bu sefer yama yazilirken kontrol edildi.
        ('templates/base.html', 'MF6-y · AKTIF_FIRMA kuresel degiskeni',
         "window.ADMIN = {{ (menu_admin|default(false))|tojson }};",
         "window.ADMIN = {{ (menu_admin|default(false))|tojson }};\n"
         "/* MF6: cari kartindaki firma kutulari yeni kayitta AKTIF\n"
         "   firmayi isaretli getirir — kullanici zaten orada calisiyor. */\n"
         "window.AKTIF_FIRMA = {{ (aktif_firma.id if aktif_firma else 0)|tojson }};"),
        ('templates/cari.html', 'MF6-z · firma listesi acilista cekilir',
         "\nyukle();\n</script>",
         "\n/* MF6: firma listesi bir kez cekilir; form her acilista\n"
         "   sorgu acsaydi cekmece yavaslardi. */\nfirmalariYukle();\nyukle();\n</script>"),
        # ── MF6-aa/ab · yeni liste tanimi HANGI havuza ──
        # OLCULDU: ortak listesi KAPALI firmada eklenen cins ORTAK
        # havuza dusuyor ve o firma kendi ekledigini GOREMIYORDU.
        ('flask_app.py', 'MF6-aa · liste havuzu yardimcisi',
         "    def _firma_kayit():",
         """    def _liste_firma_id():
        \"\"\"Yeni liste tanımı (cins, yüzey, ülke…) HANGİ havuza yazılsın.

        Ortak liste kullanan firmada ORTAK havuza (NULL): bir kez
        girilen cins her firmada görünür. Kullanmayan firmada KENDİ
        havuzuna; yoksa eklediğini kendisi göremezdi.

        ÖLÇÜLDÜ: ortak listesi kapalı firmada eklenen "SADECE D"
        ortak havuza düşüyor, o firmanın açılır listesinde
        çıkmıyordu — kullanıcı aynı cinsi tekrar tekrar eklerdi.
        \"\"\"
        return None if _firma_ortak_liste() else aktif_firma_id()

    def _firma_kayit():"""),
        ('flask_app.py', 'MF6-ab · ayarlar liste ekleme dogru havuza',
         """        v = Veriler(kategori=kategori, deger=deger,
                    kisaltma=(data.get('kisaltma') or None))""",
         """        v = Veriler(kategori=kategori, deger=deger,
                    kisaltma=(data.get('kisaltma') or None),
                    firma_id=_liste_firma_id())          # MF6"""),
        ('flask_app.py', 'MF6-ac · hizli liste ekleme dogru havuza',
         """        v = Veriler(kategori=kategori, deger=deger)
        db.session.add(v)
        db.session.flush()""",
         """        v = Veriler(kategori=kategori, deger=deger,
                    firma_id=_liste_firma_id())          # MF6
        db.session.add(v)
        db.session.flush()"""),
    ]


def main():
    print('=' * 70)
    print('  YAMA MF6 — ORTAK CARİ ve ORTAK LİSTE SEÇİMİ')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    gruplar = {}
    for dosya, aciklama, eski, yerine in degisiklikler():
        gruplar.setdefault(dosya, []).append((aciklama, eski, yerine))

    sonuclar, hata, zaten = {}, False, []
    for dosya, isler in gruplar.items():
        yol = os.path.join(KOK, dosya)
        print(f'\n── {dosya} ' + '─' * max(0, 52 - len(dosya)))
        if not os.path.exists(yol):
            print(f'  ✗ DOSYA YOK: {yol}')
            hata = True
            continue

        with open(yol, 'rb') as f:
            ham = f.read()
        crlf = b'\r\n' in ham
        icerik = ham.decode('utf-8')
        if crlf:
            icerik = icerik.replace('\r\n', '\n')
            print('  · CRLF satır sonu algılandı, korunacak')

        onk = ONKOSUL.get(dosya)
        if onk and onk not in icerik:
            print(f'  ✗ ÖNKOŞUL YOK: "{onk}" yok — önce MF5 uygulanmalı')
            hata = True
            continue
        if DOSYA_IMZA[dosya] in icerik:
            print('  ⊙ İmza zaten var — ATLANIR')
            zaten.append(dosya)
            continue

        yeni, bozuk = icerik, False
        for aciklama, eski, yerine in isler:
            n = yeni.count(eski)
            if n != 1:
                print(f'  ✗ {aciklama}')
                print(f'     kalıp {n} kez eşleşti (tam 1 olmalı)')
                hata = bozuk = True
                continue
            yeni = yeni.replace(eski, yerine, 1)
            print(f'  ✓ {aciklama}')
        if bozuk:
            continue

        if dosya.endswith('.py'):
            with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False,
                                             encoding='utf-8') as tf:
                tf.write(yeni)
                gec = tf.name
            try:
                py_compile.compile(gec, doraise=True, cfile=gec + 'c')
                print('  ✓ söz dizimi doğrulandı (py_compile)')
            except py_compile.PyCompileError as e:
                print(f'  ✗ SÖZDİZİMİ HATASI:\n{e}')
                hata = True
            finally:
                for p in (gec, gec + 'c'):
                    if os.path.exists(p):
                        os.unlink(p)

        sonuclar[yol] = (yeni.replace('\n', '\r\n') if crlf else yeni)

    print('\n' + '=' * 70)
    if hata:
        print('  ✗ HATA VAR → Hiçbir dosyaya DOKUNULMADI')
        return 1
    if zaten and sonuclar:
        print('  ✗ YARIM DURUM → Hiçbir dosyaya DOKUNULMADI')
        print(f'    imzası olan: {", ".join(zaten)}')
        return 1
    if zaten:
        print('  ⊙ Yama MF6 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_mf6.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        yedek = yol + '.yedek_mf6'
        shutil.copy2(yol, yedek)
        with open(yol, 'w', encoding='utf-8', newline='') as f:
            f.write(icerik)
        print(f'  ✓ yazıldı: {os.path.relpath(yol, KOK)}')
        print(f'    yedek  : {os.path.relpath(yedek, KOK)}')

    print('\n  ✓ YAMA UYGULANDI')
    print()
    print('  Bir sütun eklendi, GÖÇ GEREKMİYOR: SD2 açılışta ekler.')
    print('  Mevcut firmalarda NULL = ortak — davranış değişmez.')
    print()
    print('    sudo systemctl restart milestone-erp')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MF5 — FİRMA KİMLİĞİ TEK KAYNAKTAN
=======================================

ÖNKOŞUL: MF4 uygulanmış olmalı.

SORUN
-----
İkinci firmayı açarken "Belgelerde görünen tam ünvan"a
"STONEHUB USA CO., LTD." yazıldı. Ayarlar → Firma açılınca
"Milestone Mermer San. ve Tic. Ltd. Şti." görünüyor.

İKİ AYRI SEBEP, İKİSİ DE GERÇEK:

1) FORM BOŞ, GÖRÜNEN ŞEY PLACEHOLDER.
   Alanlardaki "Milestone…", "MST", "Organize Sanayi Bölgesi…",
   "info@milestonemermer.com" girilmiş DEĞER değil, şablonda sabit
   yazılmış ÖRNEK metin. STONEHUB'ın bilgisi kaybolmadı; hiç
   yazılmamıştı. Ama örnek metin başka bir firmanın gerçek adı
   olunca "veriler karıştı" gibi görünüyor — haklı olarak.

2) FİRMA KİMLİĞİ İKİ YERDE TUTULUYORDU.
   · `firma` tablosu        → firma açarken girilen ünvan/adres
   · `Veriler(kategori='firma')` → Ayarlar formunun yazdığı ünvan

   İkisi birbirini görmüyordu. Firma seçim ekranından girdiğin ünvan
   `firma` tablosuna yazılıyor, Ayarlar formu ise Veriler'i okuyor ve
   boş buluyordu. Aynı bilginin iki kaynağı = iki ayrı gerçek.

   Logo da aynı durumdaydı (`firma.logo` ve
   `Veriler(kategori='firma_logo')`).

ÇÖZÜM
-----
`firma` tablosu TEK KAYNAK olur. Ayarlar formu, belgeler, logo ve
proforma satıcı bilgileri hep oradan okur ve oraya yazar.

Eski `Veriler` satırlarındaki değerler, firmada KARŞILIĞI BOŞSA ilk
okumada taşınır — bir kez olur, sonra Veriler'e bakılmaz. Böylece
ana firmanın yıllardır girilmiş bilgisi ve logosu olduğu gibi
kalır.

Placeholder metinleri de gerçek bir firma adı olmaktan çıkarıldı.

Ayrıca "Firma Bilgileri" başlığı artık HANGİ firmayı düzenlediğini
yazıyor. İki firma arasında gidip gelirken yanlış firmanın ünvanını
değiştirmek çok kolaydı.

DOSYALAR
--------
  models.py              (firma.kisaltma, firma.logo_dosya)
  flask_app.py           (tek kaynak: bağlam, ayarlar, logo, proforma)
  templates/ayarlar.html (placeholder + başlıkta firma adı)

ŞEMA: iki sütun ekleniyor ama GÖÇ GEREKMİYOR — açılıştaki SD2
denetimi eksik sütunları kendisi ekliyor (NULL kabul eder).

KULLANIM
--------
  python3 yama_mf5.py            # RAPOR
  python3 yama_mf5.py --uygula
  sudo systemctl restart milestone-erp
"""

import os
import sys
import shutil
import py_compile
import tempfile

UYGULA = '--uygula' in sys.argv
KOK = os.path.dirname(os.path.abspath(__file__))

# IMZA TAM OLMALI. "_firma_kayit" denendi ve YANILTTI: MF4'un
# `_firma_kayit_sayim` fonksiyonu onu ALT DIZGI olarak iceriyor,
# dosya "uygulanmis" sayiliyordu. Ayni tuzaga MF3B ve MF3C'de de
# dusuldu — imza, yamanin ekledigi metnin AYIRT EDICI tamami olmali.
DOSYA_IMZA = {
    'models.py': 'logo_dosya',
    'flask_app.py': 'def _firma_kayit():',
    'templates/ayarlar.html': 'fBaslikFirma',
}
ONKOSUL = {
    'models.py': 'class Firma(db.Model)',
    'flask_app.py': 'api_firma_sil',          # MF4
    'templates/ayarlar.html': 'firmaListesiYukle',
}


# ══════════════════════════════════════════════════════════════════
#  flask_app.py
# ══════════════════════════════════════════════════════════════════

FIRMA_KAYIT = '''    def _firma_kayit():
        """Aktif firmanın kaydı — firma kimliğinin TEK KAYNAĞI.

        MF5'ten önce ünvan, adres, telefon, e-posta ve logo İKİ yerde
        duruyordu:
          · `firma` tablosu            — firma açılırken girilenler
          · `Veriler(kategori='firma')` — Ayarlar formunun yazdıkları
        İkisi birbirini görmüyordu. İkinci firmayı açıp ünvanını
        girince Ayarlar formu BOŞ geliyor, ekranda şablondaki örnek
        metin (ana firmanın adı) görünüyordu. Ölçüldü 16.10.

        Artık tek kaynak `firma`. Eski Veriler satırındaki değerler,
        firmada KARŞILIĞI BOŞSA ilk okumada taşınır — bir kez olur,
        sonra Veriler'e bakılmaz. Veriler sorgusu da süzgeçten
        geçtiği için doğru firmanın satırını getirir.
        """
        _fid = aktif_firma_id()
        if not _fid:
            return None
        f = db.session.get(Firma, _fid)
        if f is None or not has_request_context():
            return f
        if getattr(g, '_mf5_tasindi', False):
            return f
        g._mf5_tasindi = True
        try:
            import json as _j
            _tasindi = False
            _v = Veriler.query.filter_by(kategori='firma').first()
            if _v:
                try:
                    _ek = _j.loads(_v.uzun_deger or '{}') or {}
                except Exception:
                    _ek = {}
                for _alan, _deger in (('unvan', _v.deger),
                                      ('kisaltma', _v.kisaltma),
                                      ('adres', _ek.get('adres')),
                                      ('telefon', _ek.get('tel')),
                                      ('eposta', _ek.get('email'))):
                    if _deger and not str(getattr(f, _alan, '') or '').strip():
                        setattr(f, _alan, _deger)
                        _tasindi = True
            _l = Veriler.query.filter_by(kategori='firma_logo',
                                         deger='logo').first()
            if _l and _l.uzun_deger and not (f.logo or ''):
                f.logo = _l.uzun_deger
                f.logo_dosya = _l.ek_bilgi
                _tasindi = True
            if _tasindi:
                db.session.commit()
        except Exception as _e:
            db.session.rollback()
            app.logger.warning(f'[MF5] firma bilgisi tasinamadi: {_e}')
        return f

'''


def degisiklikler():
    return [
        # ── models.py ──
        ('models.py', 'MF5-a · firma.kisaltma ve firma.logo_dosya',
         "    logo          = db.Column(db.Text)                          # base64",
         "    logo          = db.Column(db.Text)                          # base64\n"
         "    # MF5: ikisi de Veriler(kategori='firma') icinde duruyordu.\n"
         "    # Firma kimliginin TEK kaynagi `firma` tablosu olunca\n"
         "    # buraya tasindilar. SD2 acilista eksik sutunu kendisi\n"
         "    # ekler; ayri goc gerekmiyor.\n"
         "    kisaltma      = db.Column(db.String(10))   # stok kodlarinda\n"
         "    logo_dosya    = db.Column(db.String(200))  # yuklenen dosyanin adi"),

        # ── flask_app.py · bağlam ──
        ('flask_app.py', 'MF5-b · sablon baglami tek kaynaktan',
         """        def _logo():
            try:
                k = Veriler.query.filter_by(kategori='firma_logo', deger='logo').first()
                return (k.uzun_deger if k else None) or None
            except Exception:
                return None
        def _firma_adi():
            try:
                k = Veriler.query.filter_by(kategori='firma').first()
                return (k.deger if k else None) or ''
            except Exception:
                return ''""",
         """        # MF5: TEK KAYNAK `firma` tablosu. Eskiden burasi
        # Veriler'i okuyordu ve firma tablosundaki ünvan/logoyu
        # görmüyordu — ikinci firmanın belgelerinde ana firmanın
        # bilgisi çıkardı.
        def _logo():
            try:
                f = _firma_kayit()
                return (f.logo if f else None) or None
            except Exception:
                return None
        def _firma_adi():
            try:
                f = _firma_kayit()
                return (f.unvan or f.ad) if f else ''
            except Exception:
                return ''"""),

        # ── flask_app.py · yardımcı ──
        ('flask_app.py', 'MF5-c · _firma_kayit yardimcisi',
         "    def _firma_logo_al():", FIRMA_KAYIT + "    def _firma_logo_al():"),

        # ── flask_app.py · logo oku ──
        ('flask_app.py', 'MF5-d · logo okuma tek kaynaktan',
         '''    def _firma_logo_al():
        """Kayıtlı logoyu döner: 'data:image/png;base64,...' veya None."""
        k = Veriler.query.filter_by(kategori='firma_logo', deger='logo').first()
        return (k.uzun_deger if k else None) or None''',
         '''    def _firma_logo_al():
        """Aktif firmanın logosu: 'data:image/png;base64,…' ya da None."""
        f = _firma_kayit()                        # MF5: tek kaynak
        return (f.logo if f else None) or None'''),

        ('flask_app.py', 'MF5-e · logo GET',
         """        logo = _firma_logo_al()
        k = Veriler.query.filter_by(kategori='firma_logo', deger='logo').first()
        return jsonify({
            'ok': True,
            'var_mi': bool(logo),
            'logo': logo,                      # data URI (önizleme için)
            'dosya_adi': (k.ek_bilgi if k else None) or '',""",
         """        f = _firma_kayit()                        # MF5: tek kaynak
        logo = (f.logo if f else None) or None
        return jsonify({
            'ok': True,
            'var_mi': bool(logo),
            'logo': logo,                      # data URI (önizleme için)
            'dosya_adi': (f.logo_dosya if f else None) or '',"""),

        ('flask_app.py', 'MF5-f · logo POST',
         """        k = Veriler.query.filter_by(kategori='firma_logo', deger='logo').first()
        if not k:
            k = Veriler(kategori='firma_logo', deger='logo')
            db.session.add(k)
        k.uzun_deger = logo
        k.ek_bilgi = (data.get('dosya_adi') or '')[:200]""",
         """        f = _firma_kayit()                        # MF5: tek kaynak
        if not f:
            return jsonify({'ok': False,
                            'mesaj': 'Aktif firma bulunamadi.'}), 400
        f.logo = logo
        f.logo_dosya = (data.get('dosya_adi') or '')[:200]"""),

        ('flask_app.py', 'MF5-g · logo DELETE',
         """        k = Veriler.query.filter_by(kategori='firma_logo', deger='logo').first()
        if k:
            _log_audit('SIL', 'ayarlar', 'firma_logo', eski={'dosya': k.ek_bilgi})
            db.session.delete(k)
            db.session.commit()""",
         """        f = _firma_kayit()                        # MF5: tek kaynak
        if f and f.logo:
            _log_audit('SIL', 'ayarlar', 'firma_logo',
                       eski={'dosya': f.logo_dosya, 'firma': f.ad})
            f.logo = None
            f.logo_dosya = None
            db.session.commit()"""),

        # ── flask_app.py · ayarlar GET ──
        ('flask_app.py', 'MF5-h · ayarlar firma GET',
         '''        kayit = Veriler.query.filter_by(kategori='firma').first()
        if kayit:
            # F3-1: adres/tel/e-posta uzun_deger icinde JSON olarak tutulur;
            # yeni tablo veya sutun gerektirmez.
            _ek = {}
            try:
                import json as _json
                _ek = _json.loads(kayit.uzun_deger or '{}') or {}
            except Exception:
                _ek = {}
            return jsonify({
                'satici_firma': kayit.deger or '',
                'kisaltma': kayit.kisaltma or '',
                'satici_adres': _ek.get('adres', ''),
                'satici_tel': _ek.get('tel', ''),
                'satici_email': _ek.get('email', ''),
            })
        return jsonify({'satici_firma': '', 'kisaltma': '',
                        'satici_adres': '', 'satici_tel': '', 'satici_email': ''})''',
         '''        # MF5: TEK KAYNAK `firma`. Eskiden Veriler okunuyordu ve
        # firma tablosundaki ünvanı görmüyordu — ikinci firmada form
        # boş geliyor, ekranda şablondaki örnek metin kalıyordu.
        f = _firma_kayit()
        if f:
            return jsonify({
                'satici_firma': f.unvan or '',
                'kisaltma': f.kisaltma or '',
                'satici_adres': f.adres or '',
                'satici_tel': f.telefon or '',
                'satici_email': f.eposta or '',
                # Hangi firmayı düzenlediğini ekran yazsın: iki firma
                # arasında gidip gelirken yanlış firmanın ünvanını
                # değiştirmek çok kolaydı.
                'firma_ad': f.ad or '', 'firma_id': f.id,
            })
        return jsonify({'satici_firma': '', 'kisaltma': '',
                        'satici_adres': '', 'satici_tel': '',
                        'satici_email': '', 'firma_ad': '', 'firma_id': None})'''),

        # ── flask_app.py · ayarlar POST ──
        ('flask_app.py', 'MF5-i · ayarlar firma POST',
         '''        satici = (data.get('satici_firma') or '').strip()
        kayit = Veriler.query.filter_by(kategori='firma').first()
        if not kayit:
            kayit = Veriler(kategori='firma', deger=satici, kisaltma=(data.get('kisaltma') or ''))
            db.session.add(kayit)
        else:
            kayit.deger = satici
            if data.get('kisaltma') is not None:
                kayit.kisaltma = data.get('kisaltma')
        # F3-1: iletisim bilgileri — belgelerde basiliyor, bir kez girilir
        import json as _json
        try:
            _ek = _json.loads(kayit.uzun_deger or '{}') or {}
        except Exception:
            _ek = {}
        for _a, _k in (('satici_adres', 'adres'), ('satici_tel', 'tel'),
                       ('satici_email', 'email')):
            if data.get(_a) is not None:
                _ek[_k] = (data.get(_a) or '').strip()
        kayit.uzun_deger = _json.dumps(_ek, ensure_ascii=False)
        ok, hata = _safe_commit('Firma ayarı kaydet')''',
         '''        satici = (data.get('satici_firma') or '').strip()
        # MF5: AKTİF FİRMANIN kaydına yazılır. Eskiden Veriler'e
        # yazılıyordu ve firma tablosundaki ünvanla ayrışıyordu.
        f = _firma_kayit()
        if not f:
            return jsonify({'ok': False,
                            'mesaj': 'Aktif firma bulunamadi.'}), 400
        f.unvan = satici
        if data.get('kisaltma') is not None:
            f.kisaltma = (data.get('kisaltma') or '').strip()[:10]
        for _a, _alan in (('satici_adres', 'adres'), ('satici_tel', 'telefon'),
                          ('satici_email', 'eposta')):
            if data.get(_a) is not None:
                setattr(f, _alan, (data.get(_a) or '').strip())
        ok, hata = _safe_commit(f'Firma ayarı kaydet: {f.ad}')'''),

        # ── flask_app.py · proforma satıcı bilgileri ──
        ('flask_app.py', 'MF5-j · proforma satici bilgileri',
         '''        _ayar, _ek = None, {}
        try:
            _ayar = Veriler.query.filter_by(kategori='firma').first()
            if _ayar and _ayar.uzun_deger:
                import json as _json
                _ek = _json.loads(_ayar.uzun_deger) or {}
        except Exception:
            pass
        _sec = lambda anahtar, varsayilan: (
            data.get(anahtar) if data.get(anahtar) else varsayilan) or None
        return {
            'satici_firma': _sec('satici_firma', _ayar.deger if _ayar else ''),
            'satici_adres': _sec('satici_adres', _ek.get('adres', '')),
            'satici_tel':   _sec('satici_tel',   _ek.get('tel', '')),
            'satici_email': _sec('satici_email', _ek.get('email', '')),
        }''',
         '''        # MF5: TEK KAYNAK `firma`. Belgenin üstünde hangi firmanın
        # ünvanı yazacağı buradan geliyor — yanlış kaynak, yanlış
        # firmanın adıyla fatura demekti.
        _f = None
        try:
            _f = _firma_kayit()
        except Exception:
            pass
        _sec = lambda anahtar, varsayilan: (
            data.get(anahtar) if data.get(anahtar) else varsayilan) or None
        return {
            'satici_firma': _sec('satici_firma',
                                 ((_f.unvan or _f.ad) if _f else '')),
            'satici_adres': _sec('satici_adres', (_f.adres if _f else '')),
            'satici_tel':   _sec('satici_tel',   (_f.telefon if _f else '')),
            'satici_email': _sec('satici_email', (_f.eposta if _f else '')),
        }'''),

        # ── ayarlar.html · placeholder + başlık ──
        ('templates/ayarlar.html', 'MF5-k · baslikta firma adi',
         """      <h4>Firma Bilgileri</h4>
      <p style="color:var(--soluk);font-size:.83rem;margin-bottom:14px">Proforma ve fatura belgelerinde görünür.</p>""",
         """      <h4>Firma Bilgileri <span id="fBaslikFirma" style="color:var(--verde);font-weight:600"></span></h4>
      <p style="color:var(--soluk);font-size:.83rem;margin-bottom:14px">
        Proforma ve fatura belgelerinde görünür.
        <b>Aktif firmanın</b> bilgileridir — başka bir firmanınkini
        düzenlemek için önce o firmaya geç.</p>"""),
        ('templates/ayarlar.html', 'MF5-l · ornek metinler gercek firma adi olmaktan cikar',
         '''        <input id="fFirma" placeholder="Milestone Mermer San. ve Tic. Ltd. Şti.">''',
         '''        <!-- MF5: örnek metin GERÇEK bir firma adı olmamalı. Boş
             formda "Milestone Mermer…" yazınca, ikinci firmadayken
             ana firmanın bilgisi oraya yazılmış gibi görünüyordu. -->
        <input id="fFirma" placeholder="Tam ticari ünvan — belgelerde basılır">'''),
        ('templates/ayarlar.html', 'MF5-m · diger ornek metinler',
         '''        <input id="fAdres" placeholder="Organize Sanayi Bölgesi ... Denizli / Türkiye">''',
         '''        <input id="fAdres" placeholder="Açık adres — belgelerde basılır">'''),
        ('templates/ayarlar.html', 'MF5-n · eposta ornek metni',
         '''          <input id="fEposta" data-buyuk-harf="hayir" placeholder="info@milestonemermer.com"></div>''',
         '''          <input id="fEposta" data-buyuk-harf="hayir" placeholder="ornek@firma.com"></div>'''),
        ('templates/ayarlar.html', 'MF5-o · baslik firma adiyla dolar',
         '''  document.getElementById('fFirma').value = d.satici_firma || '';''',
         '''  document.getElementById('fFirma').value = d.satici_firma || '';
  // MF5: hangi firmayı düzenlediğin başlıkta yazsın.
  const _bf = document.getElementById('fBaslikFirma');
  if (_bf) _bf.textContent = d.firma_ad ? '· ' + d.firma_ad : '';'''),
    ]


def main():
    print('=' * 70)
    print('  YAMA MF5 — FİRMA KİMLİĞİ TEK KAYNAKTAN')
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
            print(f'  ✗ ÖNKOŞUL YOK: "{onk}" yok — önce MF4 uygulanmalı')
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
        print('  ⊙ Yama MF5 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_mf5.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        yedek = yol + '.yedek_mf5'
        shutil.copy2(yol, yedek)
        with open(yol, 'w', encoding='utf-8', newline='') as f:
            f.write(icerik)
        print(f'  ✓ yazıldı: {os.path.relpath(yol, KOK)}')
        print(f'    yedek  : {os.path.relpath(yedek, KOK)}')

    print('\n  ✓ YAMA UYGULANDI')
    print()
    print('  İki sütun eklendi ama GÖÇ GEREKMİYOR: açılıştaki SD2')
    print('  denetimi eksik sütunu kendisi ekler.')
    print()
    print('    sudo systemctl restart milestone-erp')
    print()
    print('  Ana firmanın ünvanı ve LOGOSU ilk açılışta eski yerinden')
    print('  taşınır — hiçbir şey girmen gerekmez. İkinci firmada ise')
    print('  oluştururken yazdığın ünvan artık formda görünecek.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

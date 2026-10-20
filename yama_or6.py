#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA OR6 — FASON VE DİĞER ÖDEMELER KATKI DEFTERİNE GİRİYOR
===========================================================

ÖNKOŞUL: yama_or5.py uygulanmış olmalı.

Anlattığın durum: ortak sermaye koyuyor, o parayla blok/plaka
alınıyor, mal fason işleniyor ve FASON BEDELİNİ BİZ ödüyoruz;
ayrıca başka kalemler için de ödeme yapabiliyoruz. Bunlar zaten
Maliyetler'de duruyor.

── ÇİFT SAYIM YOK — ÖNEMLİ ──
  Fason gideri `maliyetler`den `satis_kaydi.maliyet_usd`'ye giriyor
  ve KÂRI ZATEN DÜŞÜRÜYOR. Katkı defteri kârdan İKİNCİ bir indirim
  yapmıyor; tuttuğu şey O PARAYI KİMİN ÖDEDİĞİ.

  Nakit şöyle kapanıyor:

      ciro = (ortağın katkısı + bizim katkımız) + diğer maliyet
             + vergi + net kâr

  Dağıtımda önce herkes koyduğunu geri alıyor, kalan kâr paylara
  bölünüyor. Test bu denkliği sayıyla sabitliyor.

── NE GELDİ ──
  Katkılar bölümünde "Maliyetten al" düğmesi. Bağlı işlere işlenmiş
  maliyet kayıtları listeleniyor — hem SİPARİŞE hem o işte satılan
  STOĞA bağlı olanlar, çünkü kâr hesabı da ikisini birden topluyor.

  HEPSİ OTOMATİK ALINMIYOR. Bir maliyeti kimin ödediği maliyet
  kaydında yazmıyor: nakliyeyi ortak, fasonu biz ödemiş olabiliriz.
  Ödeyen tarafı sen seçiyorsun, işaretlediklerin ekleniyor.

  Alınan kayıt ikinci kez alınamıyor (`maliyet_id` bağı) ve başka
  bir işin gideri bu hesaba giremiyor. Katkı satırını silersen
  maliyet yeniden alınabilir hâle geliyor.

── EKRANDA BİZİM TARAFIMIZ DA VAR ARTIK ──
  Motor "bize ödenecek"i hep hesaplıyordu ama döküm yalnız ortağın
  satırlarını yazıyordu — biz para koymadığımız sürece fark
  edilmemişti. Katkı koyduğumuz anda o satırlar şart oldu:
  "Bize ödenecek", "Bizim bakiye". Katkımız da dağıtımımız da
  yoksa çıkmıyor, gürültü olmasın diye.

── İKİ KUSUR, İKİSİ DE ÖLÇÜLDÜ VE DÜZELTİLDİ ──
  1) TİPSİZ MALİYET LİSTEDE HİÇ ÇIKMIYORDU. Süzgeç
     `~tip.in_(hariç_listesi)` idi; SQL'de `NULL NOT IN (...)`
     sonucu NULL'dır, satır düşer. Tipini yazmadan girdiğin bir
     fason gideri listede görünmez, eksik olduğu da anlaşılmazdı.
  2) İPTAL EDİLMİŞ MALİYET LİSTEDE ÇIKIYORDU. `aktif=False`
     kayıtlar uygulamanın geri kalanında her yerde süzülüyor;
     burada süzülmediği için iptal edilmiş bir gideri katkı olarak
     alabilirdin.

  İkisi de SQLite üzerinde ölçüldü, düzeltildi ve test edildi;
  testin gerçekten yakaladığını da ölçtüm (eski süzgece dönünce
  düşüyor).

── ÖLÇÜLDÜ (tarayıcıda) ──
  Fason 9.400 + tipsiz kalem 1.250 katkı olarak alındı:
      bizim pay      7.455,00
      katkımız      10.650,00
      BİZE ÖDENECEK 18.105,00   ✓ satır satır tutuyor
      tipsiz kalem listede GÖRÜNÜYOR
      JS hatası yok

  151 test geçti (147 + 4 yeni kalıcı test);
  firma · js · form · zincir · akis · degismezlik temiz.

── ŞEMA ──
  `ortaklik_sermaye.maliyet_id` sütunu açılışta kendiliğinden
  ekleniyor (ADD COLUMN). Göç betiği yok, veri dokunulmuyor.

── NE YAPMADIM ──
  · Ortağın sermayesiyle alınan malın ALIŞ BEDELİ otomatik
    çekilmiyor — senin dediğin gibi sermayeyi elle giriyorsun.
    Böylece çift sayma riski yok.
  · "Önce iade" yöntemini ortaklık kaydında seçmen gerekiyor;
    varsayılan hâlâ "ayrı takip". Fason modeli için doğrusu
    "önce iade".

DOSYALAR
--------
  models.py                maliyet_id bağı
  flask_app.py             maliyet listesi + katkıya alma + süzgeç
  templates/ortaklik.html  maliyet seçme penceresi · bizim taraf
  tests/test_kritik.py     4 yeni test

KULLANIM
--------
  python3 yama_or6.py            # RAPOR
  python3 yama_or6.py --uygula
  sudo systemctl restart milestone-erp     ← sütun burada eklenir
  (tarayıcıda Ctrl+F5)
"""

import base64
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile

UYGULA = '--uygula' in sys.argv
KOK = os.path.dirname(os.path.abspath(__file__))

DOSYA_IMZA = {
    'models.py': 'maliyet_id  = db.Column(db.String(20), nullable=True, index=True)',
    'flask_app.py': 'def api_ortaklik_maliyetler(oid):',
    'templates/ortaklik.html': 'Maliyetlerden katkı ekle',
    'tests/test_kritik.py': 'def test_or6_maliyet_katkiya_aliniyor_ve_iki_kez_girmiyor',
}
ONKOSUL = {
    'models.py': "yon         = db.Column(db.String(12), default='koydu')",
    'flask_app.py': 'genisletilecek = [',
    'templates/ortaklik.html': 'async function isListesiYukle()',
    'tests/test_kritik.py': 'def test_or5_metin_sutunlari_yazilacak_degerleri_tasiyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('models.py', 'OR6 · models.py blok 1',
     r'''    """Anapara hareketi: kim ne koydu, ne zaman geri aldı."""
''',
     r'''    """KATKI defteri: kim ne koydu, ne zaman geri aldı.

    Yalnız nakit sermaye değil — işe harcanan her kalem buraya
    girebiliyor. Tipik ortaklık şöyle işliyor: ortak sermaye koyuyor,
    o parayla blok/plaka alınıyor, mal fason işleniyor ve FASON
    BEDELİNİ BİZ ödüyoruz.

    ── ÇİFT SAYIM DEĞİL ──
    Fason gideri `maliyetler` tablosunda duruyor ve oradan
    `satis_kaydi.maliyet_usd`'ye giriyor; yani KÂRI ZATEN
    DÜŞÜRÜYOR. Burada tutulan şey kârdan ikinci bir indirim değil,
    O PARAYI KİMİN ÖDEDİĞİ. Dağıtımda önce herkesin koyduğu geri
    döner, kalan kâr paylaşılır.

    `maliyet_id` dolu olan satır bir maliyet kaydından TÜREMİŞTİR;
    elle yazılmaz, aynı maliyet iki kez katkıya çevrilemez.
    """
'''),
    ('models.py', 'OR6 · models.py blok 2',
     r'''    tarih       = db.Column(db.Date, default=date.today)
    aciklama    = db.Column(db.Text)
    olusturma   = db.Column(db.DateTime, default=datetime.now)
''',
     r'''    tarih       = db.Column(db.Date, default=date.today)
    aciklama    = db.Column(db.Text)
    # OR6: bu katkı hangi maliyet kaydından türedi (boşsa elle girilmiş)
    maliyet_id  = db.Column(db.String(20), nullable=True, index=True)
    olusturma   = db.Column(db.DateTime, default=datetime.now)
'''),
    ('flask_app.py', 'OR6 · flask_app.py blok 1',
     r'''                ('kasa_hareket', 'siparis_id', 'VARCHAR(20)'),
''',
     r'''                # OR6: katkı satırı bir maliyet kaydından türeyebilir
                ('ortaklik_sermaye', 'maliyet_id', 'VARCHAR(20)'),
                ('kasa_hareket', 'siparis_id', 'VARCHAR(20)'),
'''),
    ('flask_app.py', 'OR6 · flask_app.py blok 2',
     r'''                 # OR2: USD karşılığı burada da dönüyor — vergi ve
''',
     r'''                 # OR6: maliyetten türeyen satır elle silinebilir ama
                 # ekranda KAYNAĞI görünsün.
                 'maliyet_id': getattr(s, 'maliyet_id', None),
                 # OR2: USD karşılığı burada da dönüyor — vergi ve
'''),
    ('flask_app.py', 'OR6 · flask_app.py blok 3',
     r'''    @app.route('/api/ortaklik/<oid>/baglanabilir', methods=['GET'])
''',
     r'''    # OR6: kâr hesabı bu iki maliyet tipini DIŞARIDA bırakıyor
    # (Devreden/İade KDV maliyet değil). Katkı listesi de aynı
    # kuralı kullanmalı; başka türlü aynı iş için iki ayrı maliyet
    # rakamı görünürdü.
    ORTAKLIK_MALIYET_HARIC = ('Devreden KDV', 'Iade KDV')

    def _ortaklik_maliyet_kayitlari(ort):
        """Ortaklığın işlerine bağlı maliyet kayıtları.

        Maliyet iki şekilde bağlanabiliyor: doğrudan siparişe, ya da
        o işte satılan STOĞA. Kâr hesabı ikisini de topluyor; burada
        da ikisi birden toplanıyor.
        """
        satislar, isler = _ortaklik_satislari(ort)
        anahtarlar = {i.kaynak_id for i in isler}
        anahtarlar |= {s.stok_id for s in satislar if s.stok_id}
        if not anahtarlar:
            return []
        # ── İKİ SÜZGEÇ, İKİSİ DE ÖLÇÜLDÜ ──
        # 1) `~tip.in_(...)` TEK BAŞINA, tipi BOŞ olan satırı da eler:
        #    SQL'de NULL NOT IN (...) sonucu NULL'dır, satır düşer.
        #    Tipsiz girilmiş bir fason gideri listede hiç görünmez ve
        #    katkıya alınamazdı — eksik olduğu da fark edilmezdi.
        # 2) `aktif=False` kayıtlar İPTAL EDİLMİŞ maliyetlerdir;
        #    uygulamanın geri kalanı onları her yerde süzüyor. Burada
        #    süzülmezse iptal edilmiş bir gider katkı sayılabilirdi.
        return Maliyet.query.filter(
            Maliyet.baglanti_id.in_(list(anahtarlar)),
            Maliyet.aktif.is_(True),
            db.or_(Maliyet.maliyet_tip.is_(None),
                   ~Maliyet.maliyet_tip.in_(ORTAKLIK_MALIYET_HARIC))
        ).order_by(Maliyet.maliyet_tarihi.desc(), Maliyet.id.desc()).all()

    @app.route('/api/ortaklik/<oid>/maliyetler', methods=['GET'])
    def api_ortaklik_maliyetler(oid):
        """Bu ortaklığın işlerine işlenmiş maliyetler.

        `katki_id` dolu olanlar katkı defterine ALINMIŞ demektir.
        """
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('karlilik', 'okuma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        o = _ortaklik_bul(oid)
        if not o:
            return jsonify({'ok': False, 'mesaj': 'Ortaklık bulunamadı'}), 404

        alinmis = {s.maliyet_id: s.id for s in OrtaklikSermaye.query.filter(
            OrtaklikSermaye.ortaklik_id == oid,
            OrtaklikSermaye.maliyet_id.isnot(None)).all()}

        kayitlar = []
        for m in _ortaklik_maliyet_kayitlari(o):
            kayitlar.append({
                'id': m.id, 'tip': m.maliyet_tip or '',
                'tarih': _iso(m.maliyet_tarihi),
                'tutar': m.tutar or 0, 'doviz': m.doviz or 'USD',
                'usd': m.usd_karsilik or 0,
                'baglanti_id': m.baglanti_id or '',
                'fatura_no': m.fatura_no or '',
                'aciklama': m.aciklama or '',
                'katki_id': alinmis.get(m.id)})
        return jsonify({'ok': True, 'data': kayitlar,
                        'alinmis_adedi': len([k for k in kayitlar
                                              if k['katki_id']])})

    @app.route('/api/ortaklik/<oid>/maliyet_katki', methods=['POST'])
    def api_ortaklik_maliyet_katki(oid):
        """Seçilen maliyet kayıtlarını KATKI olarak defterе işler.

        HEPSİNİ otomatik almıyoruz: bir maliyeti kimin ödediği
        kayıtta yazmıyor. Nakliyeyi ortak, fasonu biz ödemiş
        olabiliriz; tarafı kullanıcı söylüyor.
        """
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('karlilik', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        o = _ortaklik_bul(oid)
        if not o:
            return jsonify({'ok': False, 'mesaj': 'Ortaklık bulunamadı'}), 404
        d = request.get_json(silent=True) or {}
        taraf = (d.get('taraf') or 'biz').strip()
        if taraf not in ('ortak', 'biz'):
            return jsonify({'ok': False, 'mesaj': 'Taraf geçersiz'}), 400
        idler = d.get('maliyet_idler') or []
        if not isinstance(idler, list) or not idler:
            return jsonify({'ok': False, 'mesaj': 'Maliyet seçilmedi'}), 400

        # Yalnızca BU ortaklığın işlerine bağlı maliyetler alınabilir:
        # başka bir işin gideri bu hesaba giremesin.
        uygun = {m.id: m for m in _ortaklik_maliyet_kayitlari(o)}
        alinmis = {s.maliyet_id for s in OrtaklikSermaye.query.filter(
            OrtaklikSermaye.ortaklik_id == oid,
            OrtaklikSermaye.maliyet_id.isnot(None)).all()}

        eklenen, atlanan = 0, []
        for mid in idler:
            m = uygun.get(mid)
            if m is None:
                atlanan.append(f'{mid} (bu ortaklığın işine bağlı değil)')
                continue
            if mid in alinmis:
                atlanan.append(f'{mid} (zaten eklenmiş)')
                continue
            db.session.add(OrtaklikSermaye(
                ortaklik_id=oid, taraf=taraf, yon='koydu',
                tutar=m.tutar or 0, doviz=m.doviz or 'USD',
                tarih=m.maliyet_tarihi or date.today(),
                maliyet_id=m.id,
                aciklama=(f'{m.maliyet_tip or "Maliyet"} · {m.id}'
                          + (f' · {m.fatura_no}' if m.fatura_no else ''))))
            alinmis.add(mid)
            eklenen += 1
        db.session.commit()
        return jsonify({'ok': True, 'eklenen': eklenen, 'atlanan': atlanan})

    @app.route('/api/ortaklik/<oid>/baglanabilir', methods=['GET'])
'''),
    ('templates/ortaklik.html', 'OR6 · templates/ortaklik.html blok 1',
     r'''<!-- ── KALEM EKLE (vergi / iş / sermaye / dağıtım) ── -->
''',
     r'''<!-- ── MALİYETTEN KATKI ── -->
<div class="modal-ortu" id="maliyetModal">
  <div class="modal" style="width:720px">
    <div class="modal-bas">
      <h3>Maliyetlerden katkı ekle</h3>
      <p>Bu ortaklığın işlerine işlenmiş maliyet kayıtları.</p>
    </div>
    <div class="modal-gov">
      <div class="yardim" style="margin-bottom:10px">Bir maliyeti
        <b>kimin ödediği</b> maliyet kaydında yazmıyor — nakliyeyi ortak,
        fasonu biz ödemiş olabiliriz. Bu yüzden hepsi kendiliğinden
        alınmıyor; ödeyen tarafı seçip işaretlediklerini ekliyorsun.</div>
      <div class="form-satir f2">
        <div class="form-alan"><label>Ödeyen taraf</label>
          <select id="mkTaraf">
            <option value="biz">Biz</option>
            <option value="ortak">Ortak</option></select></div>
        <div class="form-alan"><label>&nbsp;</label>
          <button class="blok-btn" onclick="maliyetHepsiniSec()">Tümünü seç / bırak</button></div>
      </div>
      <table class="or-mini"><tbody id="mkGovde"></tbody></table>
      <div class="yardim" id="mkNot">Yükleniyor…</div>
    </div>
    <div class="modal-alt">
      <button class="blok-btn" onclick="maliyetSeciciKapat()">Vazgeç</button>
      <button class="btn-yeni" onclick="maliyetKatkiEkle()">Seçilenleri ekle</button>
    </div>
  </div>
</div>

<!-- ── KALEM EKLE (vergi / iş / sermaye / dağıtım) ── -->
'''),
    ('templates/ortaklik.html', 'OR6 · templates/ortaklik.html blok 2',
     r'''      <div class="or-satir alt"><span class="et">Ortağın iade edilecek anaparası</span>
''',
     r'''      <div class="or-satir alt"><span class="et">Ortağın iade edilecek katkısı</span>
'''),
    ('templates/ortaklik.html', 'OR6 · templates/ortaklik.html blok 3',
     r'''    </div>`;
''',
     r'''      ${/* OR6: BİZİM tarafımız da görünmeli. Fason bedelini biz
             ödediğimizde bu satırlar olmadan "biz ne alacağız"
             sorusunun cevabı ekranda hiç yoktu — motor hesaplıyordu
             ama kimse göremiyordu. Katkımız yoksa gürültü olmasın
             diye yalnız katkı ya da dağıtım varsa çıkıyor. */ ''}
      ${(h.sermaye.biz || h.dagitilan.biz) ? `
      <div class="or-satir" style="border-top:1px solid var(--cizgi)">
        <span class="et" style="font-size:.74rem;text-transform:uppercase;
              letter-spacing:.05em;font-weight:700">Bizim tarafımız</span>
        <span class="tt"></span></div>
      ${h.anapara_yontemi === 'once_iade' ? `
      <div class="or-satir alt"><span class="et">Bizim iade edilecek katkımız</span>
        <span class="tt">${para2(h.kalan_anapara.biz, dv)}</span></div>` : ''}
      <div class="or-satir kalin"><span class="et">Bize ödenecek</span>
        <span class="tt">${para2(h.odenecek.biz, dv)}</span></div>
      <div class="or-satir alt"><span class="et">Şimdiye kadar alınan</span>
        <span class="tt">${para2(h.dagitilan.biz, dv)}</span></div>
      <div class="or-satir kalin"><span class="et">Bizim bakiye (kalan)</span>
        <span class="tt">${para2(h.bakiye.biz, dv)}</span></div>` : ''}
    </div>`;
'''),
    ('templates/ortaklik.html', 'OR6 · templates/ortaklik.html blok 4',
     r'''      <td>${s.taraf === 'ortak' ? 'Ortak' : 'Biz'} · ${s.yon === 'koydu' ? 'koydu' : 'geri aldı'}</td>
''',
     r'''      <td>${s.taraf === 'ortak' ? 'Ortak' : 'Biz'} · ${s.yon === 'koydu' ? 'koydu' : 'geri aldı'}${
        s.maliyet_id ? `<span class="or-ham">maliyet ${kacar(s.maliyet_id)}</span>` : ''}</td>
'''),
    ('templates/ortaklik.html', 'OR6 · templates/ortaklik.html blok 5',
     r'''    <div class="or-bolum">Sermaye
      <button class="blok-btn" onclick="kalemAc('sermaye')">+ Hareket</button></div>
''',
     r'''    <div class="or-bolum">Katkılar — sermaye ve ödenen giderler
      <button class="blok-btn" onclick="maliyetSeciciAc()">Maliyetlerden ekle</button>
      <button class="blok-btn" onclick="kalemAc('sermaye')">+ Elle</button></div>
    <div class="yardim" style="margin-bottom:6px">Bu bölüm kârdan İKİNCİ
      bir indirim değil — işe harcanan paranın <b>kimden çıktığını</b>
      tutuyor. Fason gibi giderler maliyet kaydı üzerinden brüt kârı
      <b>zaten düşürmüş</b> durumda; burada görünmeleri, dağıtımda o
      parayı ödeyene geri dönmesi içindir.</div>
'''),
    ('templates/ortaklik.html', 'OR6 · templates/ortaklik.html blok 6',
     r'''/* ── BAĞLANABİLİR İŞLER (OR3) ──
''',
     r'''/* ── MALİYETTEN KATKI (OR6) ──
   Fason ve benzeri giderler `maliyetler` modülünde zaten duruyor ve
   brüt kârı düşürüyor. Burada yapılan iş onları KÂRDAN TEKRAR
   DÜŞMEK değil, ödeyeni kaydetmek: dağıtımda önce herkesin koyduğu
   geri döner, kalan kâr paylaşılır. */
let MK_LISTE = [];

async function maliyetSeciciAc() {
  if (!ACIK) return;
  document.getElementById('maliyetModal').classList.add('acik');
  document.getElementById('mkNot').textContent = 'Yükleniyor…';
  document.getElementById('mkGovde').innerHTML = '';
  let d;
  try { d = await api(`/api/ortaklik/${encodeURIComponent(ACIK.id)}/maliyetler`); }
  catch (e) { document.getElementById('mkNot').textContent =
                'Liste alınamadı'; return; }
  MK_LISTE = d.data || [];
  maliyetSeciciCiz();
}

function maliyetSeciciKapat() {
  document.getElementById('maliyetModal').classList.remove('acik');
}

function maliyetSeciciCiz() {
  const g = document.getElementById('mkGovde');
  const not = document.getElementById('mkNot');
  if (!MK_LISTE.length) {
    g.innerHTML = '';
    not.textContent = 'Bu ortaklığın işlerine işlenmiş maliyet kaydı yok.';
    return;
  }
  const kalan = MK_LISTE.filter(x => !x.katki_id).length;
  not.textContent = `${MK_LISTE.length} maliyet kaydı · ` +
    `${MK_LISTE.length - kalan} tanesi katkı defterinde`;
  g.innerHTML = MK_LISTE.map(x => `<tr${x.katki_id ? ' style="opacity:.5"' : ''}>
      <td style="width:28px">${x.katki_id ? '✓'
        : `<input type="checkbox" class="mk-sec" value="${kacar(x.id)}">`}</td>
      <td>${kacar(x.tip || '—')}
        <span class="or-ham">${kacar(x.id)}${
          x.fatura_no ? ' · ' + kacar(x.fatura_no) : ''}</span></td>
      <td class="mono">${kacar(x.tarih || '')}</td>
      <td class="mono">${kacar(x.baglanti_id)}</td>
      <td class="sag">${para2(x.tutar, x.doviz)}</td>
      <td>${x.katki_id ? 'eklendi' : ''}</td>
    </tr>`).join('');
}

function maliyetHepsiniSec() {
  const kutular = [...document.querySelectorAll('.mk-sec')];
  const hepsi = kutular.every(k => k.checked);
  kutular.forEach(k => { k.checked = !hepsi; });
}

async function maliyetKatkiEkle() {
  if (!ACIK) return;
  const secili = [...document.querySelectorAll('.mk-sec')]
    .filter(k => k.checked).map(k => k.value);
  if (!secili.length) { bildir('Maliyet seç', true); return; }
  let d;
  try {
    d = await api(`/api/ortaklik/${encodeURIComponent(ACIK.id)}/maliyet_katki`,
      {method: 'POST', body: JSON.stringify({
        taraf: document.getElementById('mkTaraf').value,
        maliyet_idler: secili})});
  } catch (e) { return; }               /* api() zaten bildirdi */
  bildir(`${d.eklenen} katkı eklendi`);
  maliyetSeciciKapat();
  detayAc(ACIK.id);
  yukle();
}

/* ── BAĞLANABİLİR İŞLER (OR3) ──
'''),
    ('tests/test_kritik.py', 'OR6 · tests/test_kritik.py blok 1',
     r'''    assert not kotu, 'Varsayılanı sığmayan sütun(lar): ' + ' · '.join(kotu)
''',
     r'''    assert not kotu, 'Varsayılanı sığmayan sütun(lar): ' + ' · '.join(kotu)


# ══════════════════════════════════════════════════════════════════════
#  OR6 · FASON VE DİĞER ÖDEMELER KATKI DEFTERİNE GİRİYOR
# ══════════════════════════════════════════════════════════════════════

def _or6_kur(sip_id, stok_id, tutar, maliyet):
    """Sipariş + satış kaydı + o satışın stoğu."""
    from models import Siparis, SatisKaydi
    with fa.app.app_context():
        db.session.add(Siparis(id=sip_id, musteri='ACIK CARI', doviz='USD',
                               toplam_tutar=tutar, durum='Onaylandi',
                               siparis_tarihi=date(2026, 4, 1)))
        db.session.flush()
        db.session.add(SatisKaydi(
            id=f'{sip_id}-S1', siparis_id=sip_id, stok_id=stok_id,
            stok_tip='PLAKA', cins='TEST', musteri='ACIK CARI',
            satis_tarihi=date(2026, 4, 5), tutar=tutar, tutar_usd=tutar,
            doviz='USD', maliyet_usd=maliyet, kar_usd=tutar - maliyet))
        db.session.commit()


def test_or6_maliyet_katkiya_aliniyor_ve_iki_kez_girmiyor():
    """OR6: fason gideri elle yazılmıyor, maliyetten alınıyor.

    Bir maliyeti KİMİN ödediği maliyet kaydında yazmıyor —
    nakliyeyi ortak, fasonu biz ödemiş olabiliriz. Bu yüzden
    otomatik değil, tarafı işaretleyerek alınıyor."""
    from models import Maliyet, OrtaklikSermaye
    _or6_kur('SIPOR6A', 'PLK-OR6-1', 20000, 13000)
    with fa.app.app_context():
        db.session.add(Maliyet(id='MAL-OR6-1', baglanti_tip='stok',
                               baglanti_id='PLK-OR6-1',
                               maliyet_tip='Kesim / Fason / Üretim',
                               maliyet_tarihi=date(2026, 3, 10),
                               tutar=3000, doviz='USD', usd_karsilik=3000,
                               aktif=True))
        db.session.add(Maliyet(id='MAL-OR6-2', baglanti_tip='siparis',
                               baglanti_id='SIPOR6A', maliyet_tip='Nakliye',
                               maliyet_tarihi=date(2026, 3, 12),
                               tutar=500, doviz='USD', usd_karsilik=500,
                               aktif=True))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Fason ortaklığı', 'bizim_pay': 50, 'ortak_pay': 50,
        'anapara_yontemi': 'once_iade'}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR6A'})

    # Hem STOĞA hem SİPARİŞE bağlı maliyetler görünmeli
    d = c.get(f'/api/ortaklik/{oid}/maliyetler').get_json()
    idler = sorted(x['id'] for x in d['data'])
    assert idler == ['MAL-OR6-1', 'MAL-OR6-2'], idler
    assert all(x['katki_id'] is None for x in d['data'])

    # Fason BİZE, nakliye ORTAĞA
    r = c.post(f'/api/ortaklik/{oid}/maliyet_katki', headers=H, json={
        'taraf': 'biz', 'maliyet_idler': ['MAL-OR6-1']})
    assert r.status_code == 200 and r.get_json()['eklenen'] == 1
    r2 = c.post(f'/api/ortaklik/{oid}/maliyet_katki', headers=H, json={
        'taraf': 'ortak', 'maliyet_idler': ['MAL-OR6-2']})
    assert r2.status_code == 200 and r2.get_json()['eklenen'] == 1

    # AYNI maliyet ikinci kez giremez
    r3 = c.post(f'/api/ortaklik/{oid}/maliyet_katki', headers=H, json={
        'taraf': 'biz', 'maliyet_idler': ['MAL-OR6-1']})
    assert r3.get_json()['eklenen'] == 0, r3.get_json()
    assert 'zaten' in ' '.join(r3.get_json()['atlanan'])
    with fa.app.app_context():
        assert OrtaklikSermaye.query.filter_by(
            ortaklik_id=oid, maliyet_id='MAL-OR6-1').count() == 1

    # Başka bir işin gideri bu hesaba giremez
    with fa.app.app_context():
        db.session.add(Maliyet(id='MAL-YABANCI', baglanti_tip='stok',
                               baglanti_id='BASKA-STOK', maliyet_tip='Nakliye',
                               maliyet_tarihi=date(2026, 3, 1), tutar=999,
                               doviz='USD', usd_karsilik=999, aktif=True))
        db.session.commit()
    r4 = c.post(f'/api/ortaklik/{oid}/maliyet_katki', headers=H, json={
        'taraf': 'biz', 'maliyet_idler': ['MAL-YABANCI']})
    assert r4.get_json()['eklenen'] == 0
    assert 'bağlı değil' in ' '.join(r4.get_json()['atlanan'])


def test_or6_iki_taraf_da_koydugunu_geri_aliyor_ve_nakit_kapaniyor():
    """OR6: ortak sermayeyi, biz fasonu koyuyoruz — ikisi de geri döner.

    Nakit denkliği: CİRO = (ortağın katkısı + bizim katkımız) +
    net kâr + vergi. Bu tutmazsa ya biri iki kez sayılmıştır ya da
    biri hiç sayılmamıştır."""
    from models import Maliyet
    _or6_kur('SIPOR6B', 'PLK-OR6-2', 50000, 32000)
    with fa.app.app_context():
        db.session.add(Maliyet(id='MAL-OR6-3', baglanti_tip='stok',
                               baglanti_id='PLK-OR6-2',
                               maliyet_tip='Kesim / Fason / Üretim',
                               maliyet_tarihi=date(2026, 3, 10),
                               tutar=12000, doviz='USD', usd_karsilik=12000,
                               aktif=True))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Nakit denkliği', 'bizim_pay': 50, 'ortak_pay': 50,
        'anapara_yontemi': 'once_iade'}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR6B'})
    # Ortak blok parasını koydu (elle), fasonu biz ödedik (maliyetten)
    c.post(f'/api/ortaklik/{oid}/sermaye', headers=H, json={
        'taraf': 'ortak', 'yon': 'koydu', 'tutar': 20000,
        'tarih': '2026-03-01'})
    c.post(f'/api/ortaklik/{oid}/maliyet_katki', headers=H, json={
        'taraf': 'biz', 'maliyet_idler': ['MAL-OR6-3']})

    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h['ciro'] == 50000 and h['brut_kar'] == 18000, h
    assert h['sermaye']['ortak'] == 20000, h['sermaye']
    assert h['sermaye']['biz'] == 12000, h['sermaye']
    # Her iki taraf da koyduğunu + payını alıyor
    assert h['odenecek']['ortak'] == 20000 + 9000, h['odenecek']
    assert h['odenecek']['biz'] == 12000 + 9000, h['odenecek']
    # NAKİT DENKLİĞİ: maliyetin içinde olan katkılar + kâr = ciro
    katki = h['sermaye']['ortak'] + h['sermaye']['biz']
    assert katki + h['brut_kar'] + (h['maliyet'] - katki) == h['ciro']


def test_or6_tipsiz_ve_iptal_maliyet_dogru_elenir():
    """OR6: süzgeç iki şeyi birden doğru yapmalı.

    · `~tip.in_(...)` TEK BAŞINA tipi BOŞ satırı da eler (SQL'de
      NULL NOT IN (...) → NULL). Tipsiz girilmiş bir fason gideri
      listede hiç görünmez, eksik olduğu da anlaşılmazdı.
    · `aktif=False` kayıt İPTAL EDİLMİŞ maliyettir; listede
      çıkarsa iptal edilmiş bir gider katkı sayılabilirdi.

    İkisi de ÖLÇÜLDÜ, ikisi de düzeltildi."""
    from models import Maliyet
    _or6_kur('SIPOR6C', 'PLK-OR6-3', 9000, 5000)
    with fa.app.app_context():
        db.session.add_all([
            Maliyet(id='MAL-TIPSIZ', baglanti_tip='stok',
                    baglanti_id='PLK-OR6-3', maliyet_tip=None,
                    maliyet_tarihi=date(2026, 3, 5), tutar=700,
                    doviz='USD', usd_karsilik=700, aktif=True),
            Maliyet(id='MAL-IPTAL', baglanti_tip='stok',
                    baglanti_id='PLK-OR6-3', maliyet_tip='Nakliye',
                    maliyet_tarihi=date(2026, 3, 6), tutar=800,
                    doviz='USD', usd_karsilik=800, aktif=False),
            Maliyet(id='MAL-KDV', baglanti_tip='stok',
                    baglanti_id='PLK-OR6-3', maliyet_tip='Iade KDV',
                    maliyet_tarihi=date(2026, 3, 7), tutar=900,
                    doviz='USD', usd_karsilik=900, aktif=True)])
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H,
                 json={'ad': 'Süzgeç'}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR6C'})

    idler = [x['id'] for x in
             c.get(f'/api/ortaklik/{oid}/maliyetler').get_json()['data']]
    assert 'MAL-TIPSIZ' in idler, ('tipsiz kayıt elenmiş', idler)
    assert 'MAL-IPTAL' not in idler, ('iptal kayıt görünüyor', idler)
    assert 'MAL-KDV' not in idler, ('KDV kalemi görünüyor', idler)


def test_or6_ekranda_bizim_taraf_da_gorunuyor():
    """OR6: fason bedelini biz ödediğimizde "biz ne alacağız" ekranda olmalı.

    Motor `odenecek['biz']`'i hep hesaplıyordu ama döküm yalnız
    ortağın satırlarını yazıyordu — OR6 öncesi biz para koymadığımız
    için fark edilmemişti. Katkı koyduğumuz anda o satırlar şart."""
    import io as _io
    h = _io.open('templates/ortaklik.html', encoding='utf-8').read()
    for parca in ('Bize ödenecek', 'Bizim bakiye (kalan)',
                  'h.odenecek.biz', 'h.bakiye.biz'):
        assert parca in h, parca
    # Katkımız da dağıtımımız da yoksa gürültü çıkarmasın
    assert '(h.sermaye.biz || h.dagitilan.biz)' in h
'''),
]

TAM_ICERIK = {}

def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA OR6 — FASON VE DIGER ODEMELER KATKI DEFTERINDE')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    # ── --yaz-gecici ──
    # base64 gömülü iki dosyayı /tmp'ye çıkarır, PROJEYE DOKUNMAZ.
    # Tam dosya yazan bir yamayı önce okumak istemek yerinde bir
    # istek; "uygula da sonra bak" demek yanlış olurdu.
    if '--yaz-gecici' in sys.argv:
        hedef = tempfile.mkdtemp(prefix='tz1-')
        print()
        for ad in TAM_YAZILAN:
            p = os.path.join(hedef, ad)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(_tam_dosya(ad))
            print(f'  {p}')
        print()
        print('  Projeye DOKUNULMADI. Okuduktan sonra:')
        print('    python3 yama_or6.py            # rapor')
        print('    python3 yama_or6.py --uygula')
        print('=' * 70)
        return 0

    gruplar = {}
    for dosya, aciklama, eski, yerine in DEGISIKLIKLER:
        gruplar.setdefault(dosya, []).append((aciklama, eski, yerine))

    sonuclar, hata, zaten = {}, False, []

    # ══════════════════════════════════════════════════════════════
    #  TAM DOSYA YAZILANLAR
    # ══════════════════════════════════════════════════════════════
    for dosya in TAM_YAZILAN:
        yol = os.path.join(KOK, dosya)
        print(f'\n── {dosya} ' + '─' * max(0, 52 - len(dosya)))
        yeni = _tam_dosya(dosya)

        if os.path.exists(yol):
            with open(yol, 'rb') as f:
                ham = f.read()
            try:
                mevcut = ham.decode('utf-8')
            except UnicodeDecodeError:
                print('  ✗ Dosya UTF-8 değil — dokunmuyorum.')
                hata = True
                continue
            imza = DOSYA_IMZA.get(dosya)
            if imza and imza in mevcut:
                print('  ⊙ İmza zaten var — ATLANIR')
                zaten.append(dosya)
                continue
            onk = ONKOSUL.get(dosya)
            if onk and onk not in mevcut:
                # Beklenmeyen bir dosyanın üzerine yazmayı reddediyoruz:
                # bu betik TAM DOSYA yazıyor, yanlış hedefte geri
                # dönüşü yedekten olur.
                print(f'  ✗ Beklenen içerik yok ("{onk}")')
                print('    Bu dosya tanıdığım sifirla2.py değil; tam dosya')
                print('    yazdığım için üzerine yazmayı reddediyorum.')
                hata = True
                continue
            print(f'  · mevcut dosya {len(mevcut.splitlines())} satır '
                  f'→ yeni {len(yeni.splitlines())} satır (YENİDEN YAZILIR)')
        else:
            print(f'  · yeni dosya ({len(yeni.splitlines())} satır)')

        # Söz dizimi doğrulaması — UZANTIYA GÖRE.
        _uzanti = os.path.splitext(dosya)[1].lower()
        with tempfile.NamedTemporaryFile('w', suffix=_uzanti or '.txt',
                                         delete=False, encoding='utf-8') as tf:
            tf.write(yeni)
            gec = tf.name
        try:
            if _uzanti == '.py':
                try:
                    py_compile.compile(gec, doraise=True, cfile=gec + 'c')
                    print('  ✓ söz dizimi doğrulandı (py_compile)')
                except py_compile.PyCompileError as e:
                    print(f'  ✗ SÖZDİZİMİ HATASI:\n{e}')
                    hata = True
            elif _uzanti == '.js':
                _node = shutil.which('node') or shutil.which('nodejs')
                if not _node:
                    print('  ⚠ node bulunamadı — JS söz dizimi DENETLENMEDİ')
                else:
                    _s = subprocess.run([_node, '--check', gec],
                                        capture_output=True, text=True)
                    if _s.returncode != 0:
                        print(f'  ✗ JS SÖZDİZİMİ HATASI:\n{_s.stderr[:400]}')
                        hata = True
                    else:
                        print('  ✓ söz dizimi doğrulandı (node --check)')
            else:
                print(f'  · {_uzanti or "uzantısız"} — söz dizimi denetimi yok')
        finally:
            for p in (gec, gec + 'c'):
                if os.path.exists(p):
                    os.unlink(p)

        sonuclar[yol] = yeni

    # ══════════════════════════════════════════════════════════════
    #  CERRAHİ DEĞİŞİKLİKLER
    # ══════════════════════════════════════════════════════════════
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

        # ── SIRA ÖNEMLİ: İMZA ÖNCE, ÖNKOŞUL SONRA ──
        # Ters sırada yazmıştım ve ikinci koşuda patladı. Bu yamanın
        # ÖNKOŞUL çapaları, yamanın DEĞİŞTİRDİĞİ satırların kendisi
        # (örn. `grep -q "Zaten uygulanmış"`). Uygulandıktan sonra o
        # satır artık yok; önkoşulu önce denetlersen uygulanmış dosya
        # "ÖNKOŞUL YOK" diye HATA veriyor — oysa durum "zaten
        # uygulanmış". İmza sorusu her zaman önce gelmeli.
        if DOSYA_IMZA[dosya] in icerik:
            print('  ⊙ İmza zaten var — ATLANIR')
            zaten.append(dosya)
            continue
        onk = ONKOSUL.get(dosya)
        if onk and onk not in icerik:
            print(f'  ✗ ÖNKOŞUL YOK: "{onk}" yok')
            hata = True
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

        if dosya.endswith('.sh'):
            # Kabuk betiğini bash ile söz dizimi denetimine sok;
            # bozuk bir gonder.sh push yolunu kapatır.
            try:
                with tempfile.NamedTemporaryFile('w', suffix='.sh',
                                                 delete=False,
                                                 encoding='utf-8') as tf:
                    tf.write(yeni)
                    gecs = tf.name
                _s = subprocess.run(['bash', '-n', gecs],
                                    capture_output=True, text=True)
                if _s.returncode != 0:
                    print(f'  ✗ KABUK SÖZDİZİMİ HATASI:\n{_s.stderr[:400]}')
                    hata = True
                else:
                    print('  ✓ söz dizimi doğrulandı (bash -n)')
            except FileNotFoundError:
                print('  ⚠ bash bulunamadı, kabuk denetimi atlandı')
            finally:
                if os.path.exists(gecs):
                    os.unlink(gecs)

        sonuclar[yol] = (yeni.replace('\n', '\r\n') if crlf else yeni)

    # ══════════════════════════════════════════════════════════════
    print('\n' + '=' * 70)
    if hata:
        print('  ✗ HATA VAR → Hiçbir dosyaya DOKUNULMADI')
        return 1
    if zaten and sonuclar:
        # Yarım durum: bazı dosyalar yamalı, bazıları değil. Devam
        # etmek sistemi tutarsız bırakırdı.
        print('  ✗ YARIM DURUM → Hiçbir dosyaya DOKUNULMADI')
        print(f'    imzası olan: {", ".join(zaten)}')
        return 1
    if zaten:
        print('  ⊙ Yama OR6 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_or6.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_or6'
            shutil.copy2(yol, yedek)
            _y = f'    yedek  : {os.path.relpath(yedek, KOK)}'
        else:
            _y = '    (yeni dosya — yedek yok)'
            _klasor = os.path.dirname(yol)
            if _klasor and not os.path.isdir(_klasor):
                os.makedirs(_klasor, exist_ok=True)
                print(f'    klasör oluşturuldu: {os.path.relpath(_klasor, KOK)}')
        with open(yol, 'w', encoding='utf-8', newline='') as f:
            f.write(icerik)
        if yol.endswith('.sh'):
            os.chmod(yol, 0o755)
        print(f'  ✓ yazıldı: {os.path.relpath(yol, KOK)}')
        print(_y)

    print('\n  ✓ YAMA UYGULANDI')
    print()
    print('    1) sudo systemctl restart milestone-erp')
    print('    2) Tarayicida Ctrl+F5')
    print('    3) venv/bin/python -m pytest tests/test_kritik.py -q')
    print()
    print('  BAKILACAK YER')
    print('    Analiz -> Is Ortakliklari -> bir ortaklik ac')
    print('    1) sudo systemctl restart milestone-erp  <- sutun burada')
    print('    2) Ctrl+F5')
    print('    3) Analiz -> Is Ortakliklari -> ortakligi ac')
    print('       KATKILAR bolumunde "Maliyetten al" dugmesi.')
    print('       Fason model icin ortakligi "once iade" yap.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

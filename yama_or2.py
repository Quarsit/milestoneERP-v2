#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA OR2 — ORTAKLIKTA DÖVİZ (OR1'İN EKSİĞİ)
============================================

ÖNKOŞUL: yama_or1.py uygulanmış olmalı.

Sermaye bölümünde döviz cinsi yoktu, yalnız tutar girişi vardı.
Haklısın — ve kazdıkça eksik tek bir açılır kutudan büyük çıktı.

── ASIL SORUN: MOTOR DÖVİZE BAKMIYORDU ──
  Tablolarda `doviz` sütunu vardı ama hesap şöyleydi:

      sermaye[taraf] += sm.tutar          # döviz? bakılmıyor

  Formda alan olmadığı için bugün her şey USD yazılıyordu ve sorun
  görünmüyordu. Alanı ekleyip çevrimi eklememek, 30.000 EUR ile
  30.000 USD'yi aynı sayı saymakla biterdi — ortağa ödenecek tutar
  sessizce yanlış çıkardı.

── NE GELDİ ──
  · Sermaye, dağıtım ve sabit vergi kalemine DÖVİZ alanı.
    Ortaklığın varsayılan dövizi ön seçili geliyor.
  · Motor her satırı USD'ye çeviriyor. Hesabın tamamı USD çünkü kâr
    `satis_kaydi` içinde USD duruyor; ekranın en üstünde artık
    "HESAP PARA BİRİMİ · USD" yazıyor.
  · Çevrilen satırların yanında GİRİLEN tutar da duruyor
    (− 850,00 USD · altında soluk 34.850,00 TRY). Çevrilmiş rakamın
    yanında orijinali yoksa hangi kurun uygulandığını kontrol
    edemezsin.
  · USD dışı kalem varsa ekran ayrıca uyarıyor.

── KUR, SATIRIN KENDİ TARİHİNDEN ALINIYOR ──
  Bugünün kuruyla çevirmek, aylar önce konmuş bir anaparayı bugünkü
  kurla değerlemek olurdu. Ortakla paylaşılan bir hesapta en
  tartışmalı yer tam burası olurdu; o yüzden her satır kendi
  tarihindeki TCMB kuruyla çevriliyor (sistemdeki kur arşivi).

  Kur bulunamazsa tutar olduğu gibi bırakılıyor ve log'a yazılıyor —
  sessizce sıfır yazmak, kalemi hesaptan silmek olurdu.

── ORTAKLIK DÖVİZİ NE İŞE YARIYOR ──
  Alanın adı "Varsayılan döviz" oldu ve altına ne yaptığı yazıldı:
  yeni kalemlerde ön seçili gelir, hesabı değiştirmez. Önceki hâli
  bütün hesabın o dövizde yapıldığını ima ediyordu — etmiyor.

── ÖLÇÜLDÜ (tarayıcıda, karışık dövizle) ──
      27.000 EUR anapara, 10.07.2026 (EUR 33 / USD 30)
          → 29.700,00 USD      ✓ 27000 × 33/30
      34.850 TRY sabit vergi, 05.10.2026 (USD 41)
          → 850,00 USD          ✓ 34850 / 41
      ortağa ödenecek  34.670,00 USD  (29.700 + 4.970)
      her iki satırda da girilen tutar yanında duruyor
      JS hatası yok

  141 test geçti (139 + 2 yeni kalıcı test);
  firma · js · form · zincir · akis · degismezlik temiz.

── YOL ÜSTÜNDE: KIRILGAN TEST (kendi hatam) ──
  Yeni testler önce Şubat/Mayıs kurları kuruyordu. Kur kayıtları
  takım genelinde PAYLAŞILIYOR ve `_kur_getir` "tarihi <= aranan en
  SON kayıt" diye çalışıyor; başka testlerin koyduğu kurlar benim
  beklediğim rakamı kaydırdı. Testler tek başına GEÇİYOR, takımda
  DÜŞÜYORDU.

  Kimsenin dokunmadığı bir pencereye taşındı (Temmuz-Ağustos) ve
  araya kur girerse testin NEDEN kırıldığını söyleyen bir koruma
  eklendi. İkinci test de artık kendi kurunu kendi koyuyor: ötekinin
  koyduğuna güvenmek, tek başına koşunca düşen bir test demekti.

── NE YAPMADIM ──
  Hesabın kendisini EUR ya da TRY'de raporlamak. Kâr satış
  kaydından USD olarak geliyor; rapor para birimini değiştirmek
  ciro ve maliyetin de çevrilmesi demek — ayrı bir iş. İstersen
  yaparım.

DOSYALAR
--------
  flask_app.py             çevirici + motor + sermaye sözlüğü
  templates/ortaklik.html  üç forma döviz, satırlarda orijinal tutar
  tests/test_kritik.py     2 yeni test

Şema yok, göç yok. `doviz` sütunları OR1'de zaten vardı.

KULLANIM
--------
  python3 yama_or2.py            # RAPOR
  python3 yama_or2.py --uygula
  sudo systemctl restart milestone-erp
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
    'flask_app.py': 'def _ortaklik_usd(tutar, doviz, tarih=None):',
    'templates/ortaklik.html': 'Hesap para birimi',
    'tests/test_kritik.py': 'def test_or2_farkli_dovizler_kendi_tarihinin_kuruyla_cevrilir',
}
ONKOSUL = {
    'flask_app.py': 'def _ortaklik_hesap(ort):',
    'templates/ortaklik.html': 'İŞ ORTAKLIKLARI — OR1',
    'tests/test_kritik.py': 'def test_or1_hesap_zinciri_basamak_basamak',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'OR2 · flask_app.py blok 1',
     r'''                 'tarih': _iso(s.tarih), 'aciklama': s.aciklama or ''}
''',
     r'''                 # OR2: USD karşılığı burada da dönüyor — vergi ve
                 # dağıtım satırları gösteriyor, sermaye göstermiyor
                 # olsaydı aynı tablo iki farklı dilde konuşurdu.
                 'usd': _ortaklik_usd(s.tutar or 0, s.doviz, s.tarih),
                 'cevrildi': (s.doviz or 'USD').upper() != 'USD',
                 'tarih': _iso(s.tarih), 'aciklama': s.aciklama or ''}
'''),
    ('flask_app.py', 'OR2 · flask_app.py blok 2',
     r'''    def _ortaklik_satislari(ort):
''',
     r'''    def _ortaklik_usd(tutar, doviz, tarih=None):
        """OR2 — tutarı O GÜNÜN kuruyla USD'ye çevirir.

        Hesabın tamamı USD üzerinden yapılıyor çünkü kâr `satis_kaydi`
        içinde USD olarak duruyor. Sermaye ya da dağıtım başka
        dövizde girilebiliyor; çevrilmeden toplanırsa 30.000 EUR ile
        30.000 USD aynı sayı sayılır ve ortağa ödenecek tutar yanlış
        çıkar.

        KUR, SATIRIN KENDİ TARİHİNDEN alınır. Bugünün kuruyla
        çevirmek, aylar önce konmuş bir anaparayı bugünkü kurla
        değerlemek olurdu — ortakla paylaşılan bir hesapta en
        tartışmalı yer burası olurdu.
        """
        if not tutar:
            return 0
        d = (doviz or 'USD').upper()
        if d == 'USD':
            return q2(tutar)
        try:
            usd_kur = _kur_getir('USD', tarih)
            if not usd_kur:
                return q2(tutar)      # kur yoksa olduğu gibi — sessiz sıfır değil
            return q2(tutar * _kur_getir(d, tarih) / usd_kur)
        except Exception as e:
            app.logger.warning(f'Ortaklık kur çevrimi başarısız ({d}): {e}')
            return q2(tutar)

    def _ortaklik_satislari(ort):
'''),
    ('flask_app.py', 'OR2 · flask_app.py blok 3',
     r'''        for v in OrtaklikVergi.query.filter_by(ortaklik_id=ort.id).order_by(
                OrtaklikVergi.id).all():
            if v.matrah_tipi == 'ciro':
                matrah, tut = ciro, q2(ciro * (v.oran or 0) / 100)
            elif v.matrah_tipi == 'sabit':
                matrah, tut = None, q2(v.tutar or 0)
''',
     r'''        # OR2: USD disinda girilmis kalem var mi — vergi, sermaye ve
        # dagitim donguleri bunu birlikte isaretliyor.
        cevrim_yapildi = False
        for v in OrtaklikVergi.query.filter_by(ortaklik_id=ort.id).order_by(
                OrtaklikVergi.id).all():
            if v.matrah_tipi == 'ciro':
                matrah, tut = ciro, q2(ciro * (v.oran or 0) / 100)
            elif v.matrah_tipi == 'sabit':
                # OR2: sabit kalem kendi dövizinde girilir, USD'ye çevrilir.
                matrah = None
                tut = _ortaklik_usd(v.tutar or 0, v.doviz, v.odeme_tarihi)
                if (v.doviz or 'USD').upper() != 'USD':
                    cevrim_yapildi = True
'''),
    ('flask_app.py', 'OR2 · flask_app.py blok 4',
     r'''                'durum': v.durum, 'odeme_tarihi': _iso(v.odeme_tarihi),
''',
     r'''                # Orijinali de dönüyor: çevrilmiş rakamın yanında
                # girilen rakamı göremezsen hangi kurun uygulandığını
                # kontrol edemezsin.
                'ham_tutar': v.tutar or 0, 'doviz': v.doviz or 'USD',
                'cevrildi': (v.doviz or 'USD').upper() != 'USD',
                'durum': v.durum, 'odeme_tarihi': _iso(v.odeme_tarihi),
'''),
    ('flask_app.py', 'OR2 · flask_app.py blok 5',
     r'''            hedef[sm.taraf if sm.taraf in hedef else 'ortak'] += (sm.tutar or 0)
''',
     r'''            # OR2: her satır KENDİ TARİHİNDEKİ kurla USD'ye çevrilir.
            _usd = _ortaklik_usd(sm.tutar or 0, sm.doviz, sm.tarih)
            if (sm.doviz or 'USD').upper() != 'USD':
                cevrim_yapildi = True
            hedef[sm.taraf if sm.taraf in hedef else 'ortak'] += _usd
'''),
    ('flask_app.py', 'OR2 · flask_app.py blok 6',
     r'''            dagitilan[d.taraf if d.taraf in dagitilan else 'ortak'] += (d.tutar or 0)
            dagitimlar.append({
                'id': d.id, 'taraf': d.taraf, 'tutar': d.tutar or 0,
                'doviz': d.doviz or 'USD', 'tarih': _iso(d.tarih),
''',
     r'''            _usd = _ortaklik_usd(d.tutar or 0, d.doviz, d.tarih)
            if (d.doviz or 'USD').upper() != 'USD':
                cevrim_yapildi = True
            dagitilan[d.taraf if d.taraf in dagitilan else 'ortak'] += _usd
            dagitimlar.append({
                'id': d.id, 'taraf': d.taraf,
                # `tutar` HER ZAMAN USD: ekrandaki toplamlarla aynı
                # birimde olsun. Girilen rakam `ham_tutar`da duruyor.
                'tutar': _usd, 'ham_tutar': d.tutar or 0,
                'doviz': d.doviz or 'USD',
                'cevrildi': (d.doviz or 'USD').upper() != 'USD',
                'tarih': _iso(d.tarih),
'''),
    ('flask_app.py', 'OR2 · flask_app.py blok 7',
     r'''            uyarilar.append('Bu ortaklığa henüz iş bağlanmadı.')
''',
     r'''            uyarilar.append('Bu ortaklığa henüz iş bağlanmadı.')
        if cevrim_yapildi:
            uyarilar.append(
                'Bazı kalemler USD dışında girilmiş; her biri KENDİ '
                'TARİHİNDEKİ TCMB kuruyla USD\'ye çevrildi. Satırların '
                'yanında girilen tutar da duruyor.')
'''),
    ('flask_app.py', 'OR2 · flask_app.py blok 8',
     r'''            'uyarilar': uyarilar}
''',
     r'''            # Hesap HER ZAMAN USD: kâr `satis_kaydi`'nda USD duruyor.
            'para_birimi': 'USD', 'cevrim_yapildi': cevrim_yapildi,
            'uyarilar': uyarilar}
'''),
    ('templates/ortaklik.html', 'OR2 · templates/ortaklik.html blok 1',
     r'''  .or-sil{cursor:pointer;color:var(--kirmizi);font-size:.76rem;
''',
     r'''  /* Çevrilen kalemlerde GİRİLEN tutar da görünür: çevrilmiş
     rakamın yanında orijinali yoksa hangi kurun uygulandığını
     kontrol edemezsin. */
  .or-ham{display:block;font-size:.72rem;color:var(--soluk);font-weight:400}
  .or-sil{cursor:pointer;color:var(--kirmizi);font-size:.76rem;
'''),
    ('templates/ortaklik.html', 'OR2 · templates/ortaklik.html blok 2',
     r'''        <div class="form-alan"><label>Döviz</label>
          <select id="mDoviz"><option>USD</option><option>EUR</option><option>TRY</option></select></div>
''',
     r'''        <div class="form-alan"><label>Varsayılan döviz</label>
          <select id="mDoviz"><option>USD</option><option>EUR</option><option>TRY</option></select>
          <div class="yardim">Yeni kalemlerde ön seçili gelir. <b>Hesap her
            zaman USD</b> üzerinden yapılır — kâr satış kayıtlarında USD
            duruyor.</div></div>
'''),
    ('templates/ortaklik.html', 'OR2 · templates/ortaklik.html blok 3',
     r'''      <span class="tt">− ${para2(v.tutar, dv)}</span>
      <span class="or-sil" onclick="vergiSil(${v.id})">sil</span>
    </div>`).join('');

  const hesapHTML = `
    <div class="or-hesap">
''',
     r'''      <span class="tt">− ${para2(v.tutar, 'USD')}${
        v.cevrildi ? `<span class="or-ham">${para2(v.ham_tutar, v.doviz)}</span>` : ''}</span>
      <span class="or-sil" onclick="vergiSil(${v.id})">sil</span>
    </div>`).join('');

  const hesapHTML = `
    <div class="or-hesap">
      <div class="or-satir" style="border-bottom:1px solid var(--cizgi)">
        <span class="et" style="font-size:.74rem;text-transform:uppercase;
              letter-spacing:.05em;font-weight:700">Hesap para birimi</span>
        <span class="tt">${h.para_birimi || 'USD'}</span></div>
'''),
    ('templates/ortaklik.html', 'OR2 · templates/ortaklik.html blok 4',
     r'''      <td class="sag">${para2(s.tutar, s.doviz)}</td>
      <td class="sag"><span class="sil" onclick="sermayeSil(${s.id})">sil</span></td>
    </tr>`).join('') || '<tr><td colspan="4" style="color:var(--soluk)">sermaye hareketi yok</td></tr>';

  const dag = (h.dagitimlar || []).map(x => `<tr>
      <td>${x.taraf === 'ortak' ? 'Ortak' : 'Biz'}</td>
      <td class="mono">${kacar(x.tarih || '')}</td>
      <td class="sag">${para2(x.tutar, x.doviz)}</td>
''',
     r'''      <td class="sag">${s.cevrildi ? para2(s.usd, 'USD') : para2(s.tutar, s.doviz)}${
        s.cevrildi ? `<span class="or-ham">${para2(s.tutar, s.doviz)}</span>` : ''}</td>
      <td class="sag"><span class="or-sil" onclick="sermayeSil(${s.id})">sil</span></td>
    </tr>`).join('') || '<tr><td colspan="4" style="color:var(--soluk)">sermaye hareketi yok</td></tr>';

  const dag = (h.dagitimlar || []).map(x => `<tr>
      <td>${x.taraf === 'ortak' ? 'Ortak' : 'Biz'}</td>
      <td class="mono">${kacar(x.tarih || '')}</td>
      <td class="sag">${para2(x.tutar, 'USD')}${
        x.cevrildi ? `<span class="or-ham">${para2(x.ham_tutar, x.doviz)}</span>` : ''}</td>
'''),
    ('templates/ortaklik.html', 'OR2 · templates/ortaklik.html blok 5',
     r'''      <div class="form-alan" id="kTutarAlan" style="display:none"><label>Tutar</label>
        <input id="kTutar" type="number" step="0.01" min="0"></div>
''',
     r'''      <div class="form-alan" id="kTutarAlan" style="display:none"><label>Tutar</label>
        <div style="display:flex;gap:6px">
          <input id="kTutar" type="number" step="0.01" min="0" style="flex:1">
          <select id="kDoviz" style="width:84px"></select>
        </div></div>
'''),
    ('templates/ortaklik.html', 'OR2 · templates/ortaklik.html blok 6',
     r'''    <div class="form-satir f2">
      <div class="form-alan"><label>Tutar *</label>
        <input id="kTutar" type="number" step="0.01" min="0"></div>
      <div class="form-alan"><label>Tarih</label><input id="kTarih" type="date"></div>
    </div>
    <div class="form-satir"><div class="form-alan"><label>Açıklama</label>
      <input id="kAciklama"></div></div>`},
  dagitim: {baslik: 'Dağıtım', alt: 'Ortağa yapılan/yapılacak ödeme.', html: `
    <div class="form-satir f2">
      <div class="form-alan"><label>Taraf</label><select id="kTaraf">
        <option value="ortak">Ortak</option><option value="biz">Biz</option></select></div>
      <div class="form-alan"><label>Tutar *</label>
        <input id="kTutar" type="number" step="0.01" min="0"></div>
''',
     r'''    <div class="form-satir f3">
      <div class="form-alan"><label>Tutar *</label>
        <input id="kTutar" type="number" step="0.01" min="0"></div>
      <div class="form-alan"><label>Döviz</label><select id="kDoviz"></select></div>
      <div class="form-alan"><label>Tarih</label><input id="kTarih" type="date"></div>
    </div>
    <div class="form-satir"><div class="form-alan"><label>Açıklama</label>
      <input id="kAciklama"></div></div>
    <div class="yardim">USD dışında girersen <b>o günün TCMB kuruyla</b>
      USD'ye çevrilir; girdiğin tutar listede yanında durur.</div>`},
  dagitim: {baslik: 'Dağıtım', alt: 'Ortağa yapılan/yapılacak ödeme.', html: `
    <div class="form-satir f3">
      <div class="form-alan"><label>Taraf</label><select id="kTaraf">
        <option value="ortak">Ortak</option><option value="biz">Biz</option></select></div>
      <div class="form-alan"><label>Tutar *</label>
        <input id="kTutar" type="number" step="0.01" min="0"></div>
      <div class="form-alan"><label>Döviz</label><select id="kDoviz"></select></div>
'''),
    ('templates/ortaklik.html', 'OR2 · templates/ortaklik.html blok 7',
     r'''  document.getElementById('kalemModal').classList.add('acik');
''',
     r'''  /* OR2: döviz kutusu ortaklığın varsayılanıyla açılır. Boş bırakmak,
     her kalemde yeniden düşünmeyi gerektirirdi. */
  const dv = document.getElementById('kDoviz');
  if (dv) {
    const secili = (ACIK && ACIK.doviz) || 'USD';
    dv.innerHTML = ['USD', 'EUR', 'TRY'].map(x =>
      `<option${x === secili ? ' selected' : ''}>${x}</option>`).join('');
  }
  document.getElementById('kalemModal').classList.add('acik');
'''),
    ('templates/ortaklik.html', 'OR2 · templates/ortaklik.html blok 8',
     r'''             durum: _deger('kDurum'), odeme_tarihi: _deger('kTarih') || null};
    if (!govde.ad) { bildir('Vergi adı zorunlu', true); return; }
  } else if (KALEM_TIP === 'sermaye') {
    yol = kok + 'sermaye';
    govde = {taraf: _deger('kTaraf'), yon: _deger('kYon'),
             tutar: parseFloat(_deger('kTutar')) || 0,
             tarih: _deger('kTarih') || null, aciklama: _deger('kAciklama')};
  } else {
    yol = kok + 'dagitim';
    govde = {taraf: _deger('kTaraf'), tutar: parseFloat(_deger('kTutar')) || 0,
''',
     r'''             doviz: _deger('kDoviz') || 'USD',
             durum: _deger('kDurum'), odeme_tarihi: _deger('kTarih') || null};
    if (!govde.ad) { bildir('Vergi adı zorunlu', true); return; }
  } else if (KALEM_TIP === 'sermaye') {
    yol = kok + 'sermaye';
    govde = {taraf: _deger('kTaraf'), yon: _deger('kYon'),
             tutar: parseFloat(_deger('kTutar')) || 0,
             doviz: _deger('kDoviz') || 'USD',
             tarih: _deger('kTarih') || null, aciklama: _deger('kAciklama')};
  } else {
    yol = kok + 'dagitim';
    govde = {taraf: _deger('kTaraf'), tutar: parseFloat(_deger('kTutar')) || 0,
             doviz: _deger('kDoviz') || 'USD',
'''),
    ('tests/test_kritik.py', 'OR2 · tests/test_kritik.py blok 1',
     r'''    assert any('%80' in u for u in h['uyarilar']), h['uyarilar']
''',
     r'''    assert any('%80' in u for u in h['uyarilar']), h['uyarilar']


def test_or2_farkli_dovizler_kendi_tarihinin_kuruyla_cevrilir():
    """OR2: sermaye/dağıtım USD dışında girilebilir ve ÇEVRİLİR.

    Önce yalnız tutar alanı vardı; motor da dövize bakmadan
    topluyordu. Alan eklenip çevrim eklenmeseydi 30.000 EUR ile
    30.000 USD aynı sayı sayılır, ortağa ödenecek tutar yanlış
    çıkardı.

    Kur SATIRIN KENDİ TARİHİNDEN alınır: aylar önce konmuş anaparayı
    bugünkü kurla değerlemek, ortakla paylaşılan hesapta en
    tartışmalı yer olurdu."""
    from models import DovizKur
    # TEMMUZ-AĞUSTOS PENCERESİ: kur kayıtları takım genelinde
    # PAYLAŞILIYOR ve `_kur_getir` "tarihi <= aranan en SON kayıt"
    # kuralıyla çalışıyor. Başka testlerin koyduğu Şubat/Mart/Mayıs
    # kurları bu testin beklediği rakamı kaydırıyordu — bu pencereye
    # kimse dokunmuyor. Aşağıdaki koruma, ileride biri koyarsa
    # testin NEDEN kırıldığını söylüyor.
    with fa.app.app_context():
        for t, usd, eur in ((date(2026, 7, 1), 30.0, 33.0),
                            (date(2026, 8, 1), 40.0, 48.0)):
            for dv, val in (('USD', usd), ('EUR', eur)):
                if not DovizKur.query.filter_by(doviz=dv, tarih=t).first():
                    db.session.add(DovizKur(doviz=dv, tarih=t, alis=val,
                                            satis=val, efektif=val))
        db.session.commit()
        _araya_giren = DovizKur.query.filter(
            DovizKur.tarih > date(2026, 7, 1),
            DovizKur.tarih <= date(2026, 8, 10),
            DovizKur.tarih != date(2026, 8, 1)).all()
        assert not _araya_giren, (
            'Temmuz-Ağustos penceresine başka bir test kur koymuş: '
            + str([(k.doviz, str(k.tarih)) for k in _araya_giren]))

    _or1_kur('SIPOR6', [(10000, 6000)])
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Döviz testi', 'bizim_pay': 50, 'ortak_pay': 50,
        'anapara_yontemi': 'once_iade', 'doviz': 'EUR'}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR6'})

    # TEMMUZ: 1000 EUR → 1000 × 33 / 30 = 1100 USD
    assert c.post(f'/api/ortaklik/{oid}/sermaye', headers=H, json={
        'taraf': 'ortak', 'yon': 'koydu', 'tutar': 1000, 'doviz': 'EUR',
        'tarih': '2026-07-10'}).status_code == 200
    # AĞUSTOS: 1000 EUR → 1000 × 48 / 40 = 1200 USD (aynı tutar, başka kur)
    assert c.post(f'/api/ortaklik/{oid}/sermaye', headers=H, json={
        'taraf': 'ortak', 'yon': 'koydu', 'tutar': 1000, 'doviz': 'EUR',
        'tarih': '2026-08-10'}).status_code == 200
    # TEMMUZ: 3000 TRY → 3000 / 30 = 100 USD
    assert c.post(f'/api/ortaklik/{oid}/sermaye', headers=H, json={
        'taraf': 'ortak', 'yon': 'koydu', 'tutar': 3000, 'doviz': 'TRY',
        'tarih': '2026-07-10'}).status_code == 200

    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h['para_birimi'] == 'USD'
    # 1100 + 1200 + 100 = 2400 — ham toplam 5000 olurdu
    assert h['sermaye']['ortak'] == 2400, h['sermaye']
    assert h['kalan_anapara']['ortak'] == 2400
    # Net kâr 4000, ortak payı 2000, ödenecek = 2400 + 2000
    assert h['odenecek']['ortak'] == 4400, h['odenecek']
    assert h['cevrim_yapildi'] is True
    assert any('TCMB' in u for u in h['uyarilar']), h['uyarilar']

    # Sermaye SATIRI da USD karşılığını taşımalı: vergi ve dağıtım
    # gösterip sermaye göstermezse aynı tablo iki dilde konuşur.
    sh = c.get(f'/api/ortaklik/{oid}').get_json()['data']['sermaye_hareketleri']
    temmuz = [x for x in sh if x['tarih'] == '2026-07-10' and x['doviz'] == 'EUR'][0]
    assert temmuz['tutar'] == 1000 and temmuz['usd'] == 1100, temmuz
    assert temmuz['cevrildi'] is True

    # DAĞITIM da çevrilir ve ORİJİNALİ görünür
    c.post(f'/api/ortaklik/{oid}/dagitim', headers=H, json={
        'taraf': 'ortak', 'tutar': 1000, 'doviz': 'EUR',
        'tarih': '2026-08-10'})
    h2 = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    dg = h2['dagitimlar'][0]
    assert dg['tutar'] == 1200 and dg['ham_tutar'] == 1000, dg
    assert dg['doviz'] == 'EUR' and dg['cevrildi'] is True
    assert h2['dagitilan']['ortak'] == 1200
    assert h2['bakiye']['ortak'] == 3200, h2['bakiye']   # 4400 − 1200


def test_or2_sabit_vergi_kalemi_de_cevrilir():
    """OR2: 'sabit' vergi kalemi kendi dövizinde girilir.

    İade alınamayan KDV TL üzerinden doğar — USD sayılırsa kâr
    otuz kat fazla düşerdi."""
    from models import DovizKur
    # Kendi kurunu KENDİ koyuyor: öteki testin koyduğuna güvenmek,
    # tek başına koşunca düşen bir test demekti.
    with fa.app.app_context():
        if not DovizKur.query.filter_by(doviz='USD', tarih=date(2026, 7, 1)).first():
            db.session.add(DovizKur(doviz='USD', tarih=date(2026, 7, 1),
                                    alis=30.0, satis=30.0, efektif=30.0))
            db.session.commit()
    _or1_kur('SIPOR7', [(10000, 4000)])
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Sabit vergi dövizi', 'bizim_pay': 50,
        'ortak_pay': 50}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR7'})
    # 6000 TRY, Temmuz kuru 30 → 200 USD
    assert c.post(f'/api/ortaklik/{oid}/vergi', headers=H, json={
        'ad': 'İade alınamayan KDV', 'matrah_tipi': 'sabit', 'tutar': 6000,
        'doviz': 'TRY', 'durum': 'odendi',
        'odeme_tarihi': '2026-07-10'}).status_code == 200

    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    v = h['vergiler'][0]
    assert v['tutar'] == 200, v          # 6000 TRY → 200 USD
    assert v['ham_tutar'] == 6000 and v['doviz'] == 'TRY'
    assert v['cevrildi'] is True
    assert h['net_kar'] == 5800, h['net_kar']    # 6000 − 200
    assert h['cevrim_yapildi'] is True
'''),
]

TAM_ICERIK = {}

def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA OR2 — ORTAKLIKTA DOVIZ')
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
        print('    python3 yama_or2.py            # rapor')
        print('    python3 yama_or2.py --uygula')
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
        print('  ⊙ Yama OR2 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_or2.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_or2'
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
    print('    Sermaye / Dagitim / Vergi pencerelerinde DOVIZ alani.')
    print('    USD disinda girersen satirin altinda girdigin tutar,')
    print('    ustunde USD karsiligi gorunur.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

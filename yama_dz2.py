#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA DZ2 — STOK KAYITLARI DÜZENLENEBİLİR
=========================================

ÖNKOŞUL: yama_dz1.py uygulanmış olmalı.

Dörtlü sıranın ikincisi. Yine önce ölçtüm, sonra yazdım.

── 1 · DÜZENLEME SONRASI HİÇBİR HESAP YENİLENMİYORDU ──
  Stok düzenleme ucu hiçbir yeniden hesap çağırmıyordu. Ölçüm:

      alış fiyatı 300 → 500 yapıldı
      stok kartı : alış bedeli 6.000 → 10.000 USD   ✓
      satış kaydı: maliyet 6.000'de, kâr 14.000'de  ✗

  Doğrusu 10.000 / 10.000 idi. Stok kartı ile satış kârlılığı
  sessizce ayrışıyordu — ve bu, kâr tablosuna bakan herkesi
  yanıltır.

  Artık alış fiyatı, fiyat birimi, döviz veya ÖLÇÜ değiştiğinde
  bağlı satış kayıtlarının maliyeti ve kârı yeniden hesaplanıyor;
  blok ise kesimden çıkan plakalara maliyet dağılımı da
  yenileniyor. Yanıt kaç kaydın güncellendiğini yazıyor.

── 2 · ÖLÇÜLER DÜZENLENEMİYORDU ──
  Düzenleme formunda ölçü kutusu YOKTU ve sunucu da ölçü alanlarını
  kabul etmiyordu. Yanlış girilmiş bir tonaj ya da metraj
  düzeltilemiyordu — oysa ölçü maliyetin temeli:
  alış bedeli = `alis_fiyati × ölçü`.

  Geldi, tipe göre:

      BLOK          boy · yükseklik · en · hacim (m³) · tonaj
      PLAKA/EBATLI  boy · yükseklik · kalınlık · metraj (m²)

  Anlamsız olan gizleniyor. PLAKA'ya tonaj yazmak alanı yalan
  söyletirdi; sunucu da `hasattr` ile süzüyor — test ölçüyor.

  Boş bırakılan kutu GÖNDERİLMİYOR. Böylece bir alanı yanlışlıkla
  sıfırlamak mümkün değil; silmek istiyorsan 0 yazman gerekir.

  Geçersiz değer reddediliyor: ölçü sayı olmalı ve negatif
  olamaz. Negatif tonaj, negatif alış bedeli demek.

── 3 · DAĞITILMIŞ MALİYET PAYLARI: UYARIYORUZ, DOKUNMUYORUZ ──
  Dağıtım BİR KEZ yapılır ve paylar SABİT tutar olarak yazılır
  (20 ton / 10 ton için 2.000 / 1.000 gibi). Ölçüyü sonradan
  değiştirirsen o paylar eski ölçüye göre hesaplanmış kalır.

  KENDİLİĞİNDEN YENİDEN DAĞITMIYORUM. Çünkü bu, aynı gruptaki
  BAŞKA stokların maliyetini de değiştirirdi — ve onların satışı
  çoktan faturalanmış olabilir. Bir bloğun tonajını düzeltmek,
  başka bir bloğun kârını sessizce değiştirmemeli.

  Onun yerine söylüyor:

      "Bu stok 1 dağıtılmış maliyet grubunda (MGR-061051). O
       paylar ESKİ ölçüye göre hesaplandı ve olduğu gibi duruyor —
       aynı gruptaki öteki stokların maliyetini değiştirmemek için
       kendiliğinden yeniden dağıtılmadı."

  Grubu gerçekten yeniden dağıtmak istersen o ayrı bir iş; söyle,
  "grubu yeniden dağıt" düğmesi olarak yaparım. Burada sessiz
  kalmamayı seçtim, karar vermemeyi değil.

── ÖLÇÜLDÜ ──
  API üzerinden önce/sonra:
      alış 300 → 500       : satış maliyeti 6.000 → 10.000,
                             kâr 14.000 → 10.000
      tonaj 20 → 25        : maliyet 7.500'e çıktı
      PLAKA'ya tonaj: 99   : yazılmadı (alan yok), metraj yazıldı
      tonaj -5 ve "abc"    : 400, eski değer korundu
      ölçü değişti         : dağıtım uyarısı çıktı, paylar
                             2.000 / 1.000 olduğu gibi kaldı

  Tarayıcıda: BLOK formunda boy/yükseklik/en/hacim/tonaj dolu
  geliyor, kalınlık ve metraj gizli; tonajı 24 → 30 yapıp
  kaydettim, veritabanına düştü. JS hatası yok.

  181 test geçti (175 + 6 yeni kalıcı test); iki ayrı koşuda da
  aynı. firma · js · form · zincir · akis · degismezlik temiz.
  Tabanı DZ1'i uygulayarak ürettim (elle kesmedim) ve DZ2
  testlerinin orada DÜŞTÜĞÜNÜ görerek doğruladım.

── SIRADA ──
      DZ1  maliyet ↔ cari hareket            ✓ uygulandı
      DZ2  stok kayıtları                    ← bu yama
      DZ3  satış / proforma / sipariş kalemleri
      DZ4  kesim kayıtları

DOSYALAR
--------
  flask_app.py          ölçü alanları kabul · türetilmiş hesaplar
                        tazeleniyor · dağıtım uyarısı
  templates/stok.html   ölçü kutuları (tipe göre) · gönderim
  tests/test_kritik.py  6 yeni test

Şema yok, göç yok, yeni alan yok.

KULLANIM
--------
  python3 yama_dz2.py            # RAPOR
  python3 yama_dz2.py --uygula
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
    'flask_app.py': 'DZ2 · ÖLÇÜLER DÜZENLENEBİLİR',
    'templates/stok.html': 'function olcuDoldur',
    'tests/test_kritik.py': 'def test_dz2_olculer_duzenlenebiliyor_ve_kar_takip_ediyor',
}
ONKOSUL = {
    'flask_app.py': 'DZ1 · MALİYET GRUBU',
    'templates/stok.html': 'function durumSecenekleriniKur',
    'tests/test_kritik.py': 'def test_dz1_cari_hareket_silinince_kdv_satiri_oksuz_kalmaz',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'DZ2 · flask_app.py blok 1',
     r'''                db.session.commit()
                if _doviz_uyari:
                    return jsonify({'ok': True, 'mesaj': _doviz_uyari,
                                    'uyari': True})
                return jsonify({'ok': True})
''',
     r'''
                # ══════════════════════════════════════════════════
                #  DZ2 · ÖLÇÜLER DÜZENLENEBİLİR
                #
                #  Ölçü alanları buradan HİÇ güncellenmiyordu: yanlış
                #  girilmiş bir tonaj ya da metraj düzeltilemiyordu.
                #  Oysa ölçü maliyetin temeli — alış bedeli
                #  `alis_fiyati × ölçü` olarak hesaplanıyor.
                #
                #  Hangi alan hangi tipte anlamlı: BLOK ton/m3 ile,
                #  PLAKA/EBATLI m2 ile ölçülüyor. `hasattr` ile
                #  süzüyoruz — PLAKA'ya tonaj yazmak alanı yalan
                #  söyletirdi.
                # ══════════════════════════════════════════════════
                OLCU_ALANLARI = ('boy', 'yukseklik', 'en', 'kalinlik',
                                 'hacim_m3', 'tonaj', 'metraj_m2',
                                 'metraj_sqft')
                olcu_degisti = False
                for _alan in OLCU_ALANLARI:
                    if _alan not in data or not hasattr(stok, _alan):
                        continue
                    _ham = data[_alan]
                    if _ham in (None, ''):
                        continue
                    try:
                        _yeni = float(_ham)
                    except (TypeError, ValueError):
                        return jsonify({'ok': False,
                            'mesaj': f'{_alan} sayı olmalı'}), 400
                    if _yeni < 0:
                        return jsonify({'ok': False,
                            'mesaj': f'{_alan} negatif olamaz'}), 400
                    if (getattr(stok, _alan) or 0) != _yeni:
                        setattr(stok, _alan, _yeni)
                        olcu_degisti = True

                # ══════════════════════════════════════════════════
                #  DZ2 · TÜRETİLMİŞ HESAPLARI TAZELE
                #
                #  Bu uc nokta hicbir yeniden hesap CAGIRMIYORDU.
                #  Olculdu: alis fiyatini 300 -> 500 yaptim, satis
                #  kaydinin maliyeti 6.000'de, kari 14.000'de kaldi;
                #  dogrusu 10.000 / 10.000 idi. Stok karti ile satis
                #  karliligi sessizce ayrisiyordu.
                #
                #  Alis bedeli = alis_fiyati × olcu (birime gore),
                #  dovizle USD'ye cevriliyor. Dordunden biri degistiyse
                #  satis kayitlari yeniden hesaplanmali.
                # ══════════════════════════════════════════════════
                _temel_degisti = olcu_degisti or any(
                    k in data for k in ('alis_fiyati', 'fiyat_birim', 'doviz'))
                _tazelenen = 0
                if _temel_degisti:
                    db.session.flush()
                    _tazelenen = _satis_kaydi_maliyet_guncelle([stok_id])
                    if str(stok_id).startswith('BLK'):
                        _kesilmis_blok_maliyet_yeniden_dagit(stok_id)

                # DAGITILMIS MALIYET UYARISI
                # Dagitim bir KEZ yapilir ve paylar SABIT tutar olarak
                # yazilir. Olcu sonradan degisince o paylar eski olcuye
                # gore hesaplanmis olarak kalir — kendiliginden yeniden
                # dagitmiyoruz, cunku bu AYNI GRUPTAKI BASKA stoklarin
                # maliyetini de degistirirdi ve onlarin satisi coktan
                # faturalanmis olabilir. Sessiz kalmak yerine soyluyoruz.
                _dagitim_uyari = None
                if olcu_degisti:
                    _gruplar = sorted({
                        x.grup_id for x in Maliyet.query.filter(
                            Maliyet.baglanti_tip == 'stok',
                            Maliyet.baglanti_id == stok_id,
                            Maliyet.grup_id.isnot(None)).all()
                        if x.grup_id})
                    _coklu = [g for g in _gruplar
                              if Maliyet.query.filter_by(grup_id=g).count() > 1]
                    if _coklu:
                        _dagitim_uyari = (
                            f'Bu stok {len(_coklu)} dağıtılmış maliyet '
                            f'grubunda ({", ".join(_coklu[:3])}'
                            f'{"…" if len(_coklu) > 3 else ""}). O paylar '
                            f'ESKİ ölçüye göre hesaplandı ve olduğu gibi '
                            f'duruyor — aynı gruptaki öteki stokların '
                            f'maliyetini değiştirmemek için kendiliğinden '
                            f'yeniden dağıtılmadı.')

                db.session.commit()
                # DZ2: yanit, NE OLDUGUNU tasimali. Sessizce 200
                # donmek, kullaniciya "kar da guncellendi mi" diye
                # merak birakiyordu.
                _uyarilar = [u for u in (_doviz_uyari, _dagitim_uyari) if u]
                _mesaj = 'Stok güncellendi'
                if _tazelenen:
                    _mesaj += (f', {_tazelenen} satış kaydının maliyeti ve '
                               f'kârı yeniden hesaplandı')
                return jsonify({
                    'ok': True,
                    'mesaj': ' · '.join([_mesaj] + _uyarilar),
                    'satis_kaydi_guncel': _tazelenen,
                    'uyari': bool(_uyarilar),
                    'uyarilar': _uyarilar})
'''),
    ('templates/stok.html', 'DZ2 · templates/stok.html blok 1',
     r'''           maliyet. Sunucu ikisini de zaten kabul ediyordu. -->
''',
     r'''           maliyet. Sunucu ikisini de zaten kabul ediyordu. -->
      <!-- DZ2 · ÖLÇÜLER
           Ölçü alanları düzenleme formunda HİÇ yoktu: yanlış
           girilmiş bir tonaj ya da metraj düzeltilemiyordu. Oysa
           ölçü maliyetin temeli — alış bedeli `alis_fiyati × ölçü`.
           BLOK ton/m³ ile, PLAKA/EBATLI m² ile ölçülüyor; alanlar
           tipe göre gösteriliyor. -->
      <div class="form-satir f3" id="duzOlcuSatir1">
        <div class="form-alan"><label>Boy (cm)</label>
          <input id="duzBoy" type="number" step="0.1" min="0"></div>
        <div class="form-alan"><label>Yükseklik (cm)</label>
          <input id="duzYukseklik" type="number" step="0.1" min="0"></div>
        <div class="form-alan" id="duzEnAlan"><label>En (cm)</label>
          <input id="duzEn" type="number" step="0.1" min="0"></div>
        <div class="form-alan" id="duzKalinlikAlan"><label>Kalınlık (cm)</label>
          <input id="duzKalinlik" type="number" step="0.1" min="0"></div>
      </div>
      <div class="form-satir f2" id="duzOlcuSatir2">
        <div class="form-alan" id="duzHacimAlan"><label>Hacim (m³)</label>
          <input id="duzHacim" type="number" step="0.001" min="0"></div>
        <div class="form-alan" id="duzTonajAlan"><label>Tonaj</label>
          <input id="duzTonaj" type="number" step="0.001" min="0"></div>
        <div class="form-alan" id="duzMetrajAlan"><label>Metraj (m²)</label>
          <input id="duzMetraj" type="number" step="0.001" min="0"></div>
      </div>
'''),
    ('templates/stok.html', 'DZ2 · templates/stok.html blok 2',
     r'''  listeyeBagla('duzCins', 'cins');
  listeyeBagla('duzOzellik', 'ozellik');
  ureticiOnerileriDoldur();
  document.getElementById('duzModal').classList.add('acik');
}
function duzenleKapat() { document.getElementById('duzModal').classList.remove('acik'); }
''',
     r'''  /* DZ2: olculeri doldur ve TIPE GORE goster. BLOK ton/m3 ile,
     PLAKA/EBATLI m2 ile olculuyor; PLAKA'ya tonaj kutusu koymak
     alani yalan soyletirdi. */
  olcuDoldur(s);
  listeyeBagla('duzCins', 'cins');
  listeyeBagla('duzOzellik', 'ozellik');
  ureticiOnerileriDoldur();
  document.getElementById('duzModal').classList.add('acik');
}
function duzenleKapat() { document.getElementById('duzModal').classList.remove('acik'); }

/* DZ2 · ÖLÇÜ KUTULARI
   Hangi ölçü hangi tipte anlamlı:
     BLOK          boy · yükseklik · en · hacim(m³) · tonaj
     PLAKA/EBATLI  boy · yükseklik · kalınlık · metraj(m²)
   Anlamsız olanı gizliyoruz; boş bir "tonaj" kutusu PLAKA'da
   doldurulmayı bekler gibi durur ve yanlış veriye davet olur. */
function olcuDoldur(s) {
  const blok = (s.tip === 'BLOK');
  const koy = (id, deger) => {
    const el = document.getElementById(id);
    if (el) el.value = (deger === 0 || deger) ? deger : '';
  };
  koy('duzBoy', s.boy); koy('duzYukseklik', s.yukseklik);
  koy('duzEn', s.en); koy('duzKalinlik', s.kalinlik);
  /* DIKKAT: liste ucu bu ikisini KISA adla veriyor —
     hacim_m3 -> `hacim`, metraj_m2 -> `m2`. Uzun adi da
     yokluyoruz ki baska bir uc noktadan gelen kayit da dolsun. */
  koy('duzHacim', s.hacim_m3 !== undefined ? s.hacim_m3 : s.hacim);
  koy('duzTonaj', s.tonaj);
  koy('duzMetraj', s.metraj_m2 !== undefined ? s.metraj_m2 : s.m2);
  const goster = (id, acik) => {
    const el = document.getElementById(id);
    if (el) el.style.display = acik ? '' : 'none';
  };
  goster('duzEnAlan', blok);
  goster('duzKalinlikAlan', !blok);
  goster('duzHacimAlan', blok);
  goster('duzTonajAlan', blok);
  goster('duzMetrajAlan', !blok);
}
'''),
    ('templates/stok.html', 'DZ2 · templates/stok.html blok 3',
     r'''async function duzenleKaydet() {
''',
     r'''/* DZ2: yalniz DOLU ve GORUNUR olcu kutularini gonder. */
function olcuGovde() {
  const es = {duzBoy: 'boy', duzYukseklik: 'yukseklik', duzEn: 'en',
              duzKalinlik: 'kalinlik', duzHacim: 'hacim_m3',
              duzTonaj: 'tonaj', duzMetraj: 'metraj_m2'};
  const g = {};
  for (const [id, alan] of Object.entries(es)) {
    const el = document.getElementById(id);
    if (!el || el.value === '') continue;
    const kap = el.closest('.form-alan');
    if (kap && kap.style.display === 'none') continue;
    g[alan] = parseFloat(el.value);
  }
  return g;
}

async function duzenleKaydet() {
'''),
    ('templates/stok.html', 'DZ2 · templates/stok.html blok 4',
     r'''        aciklama: document.getElementById('duzAciklama').value
''',
     r'''        /* DZ2: olculer. Bos birakilan alan GONDERILMIYOR —
           sunucu bos degeri atliyor, boylece "temizlemek"
           istemeden sifirlamak mumkun degil. */
        ...olcuGovde(),
        aciklama: document.getElementById('duzAciklama').value
'''),
    ('tests/test_kritik.py', 'DZ2 · tests/test_kritik.py blok 1',
     r'''        assert db.session.get(Maliyet, mid) is None
''',
     r'''        assert db.session.get(Maliyet, mid) is None


def _dz2_kur(ek, tonaj=20, alis=300):
    """DZ2 testleri: her teste kendi stogu ve kendi satis kaydi."""
    from models import SatisKaydi
    with fa.app.app_context():
        sid = f'BLK-{ek}'
        if not db.session.get(BlokStok, sid):
            db.session.add(BlokStok(
                id=sid, blok_no=ek, cins='TEST', boy=300, yukseklik=180,
                en=170, hacim_m3=9.18, tonaj=tonaj, alis_fiyati=alis,
                alis_fiyat_birim='ton', doviz='USD', durum='Serbest'))
            db.session.add(SatisKaydi(
                id=f'SK-{ek}', stok_tip='BLOK', stok_id=sid,
                musteri='ALICI', satis_tarihi=date(2026, 10, 1),
                doviz='USD', tutar=20000, tutar_usd=20000,
                maliyet_usd=alis * tonaj, kar_usd=20000 - alis * tonaj))
        db.session.commit()
    return sid


def test_dz2_alis_fiyati_degisince_satis_kari_guncellenir():
    """DZ2: stok düzenleme ucu hiçbir yeniden hesap çağırmıyordu.
    Ölçüldü: alış fiyatını 300 → 500 yaptım, satış kaydının maliyeti
    6.000'de, kârı 14.000'de kaldı; doğrusu 10.000 / 10.000 idi.
    Stok kartı ile satış kârlılığı sessizce ayrışıyordu."""
    from models import SatisKaydi
    c = istemci('admin', 'ADMIN')
    sid = _dz2_kur('DZA', tonaj=20, alis=300)
    with fa.app.app_context():
        assert db.session.get(SatisKaydi, 'SK-DZA').maliyet_usd == 6000

    r = c.put(f'/api/stok/{sid}', headers=H,
              json={'tip': 'BLOK', 'cins': 'TEST', 'alis_fiyati': 500})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()['satis_kaydi_guncel'] >= 1, r.get_json()
    with fa.app.app_context():
        sk = db.session.get(SatisKaydi, 'SK-DZA')
        assert sk.maliyet_usd == 10000, sk.maliyet_usd
        assert sk.kar_usd == 10000, sk.kar_usd


def test_dz2_olculer_duzenlenebiliyor_ve_kar_takip_ediyor():
    """DZ2: ölçü alanları düzenleme ucundan HİÇ güncellenmiyordu —
    yanlış girilmiş bir tonaj düzeltilemiyordu. Oysa ölçü maliyetin
    temeli: alış bedeli `alis_fiyati × ölçü`."""
    from models import SatisKaydi
    c = istemci('admin', 'ADMIN')
    sid = _dz2_kur('DZB', tonaj=20, alis=300)

    r = c.put(f'/api/stok/{sid}', headers=H, json={
        'tip': 'BLOK', 'cins': 'TEST',
        'tonaj': 25, 'boy': 320, 'hacim_m3': 11.0})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        s = db.session.get(BlokStok, sid)
        assert s.tonaj == 25 and s.boy == 320 and s.hacim_m3 == 11.0
        # 25 ton × 300 = 7500
        assert db.session.get(SatisKaydi, 'SK-DZB').maliyet_usd == 7500


def test_dz2_plakaya_tonaj_yazilmaz():
    """DZ2: hangi ölçü hangi tipte anlamlı — BLOK ton/m³ ile,
    PLAKA m² ile ölçülüyor. PLAKA'ya tonaj yazmak alanı yalan
    söyletirdi; `hasattr` süzgeci onu engelliyor."""
    from models import PlakaStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not db.session.get(PlakaStok, 'PLK-DZC'):
            db.session.add(PlakaStok(
                id='PLK-DZC', blok_no='DZC', cins='TEST', boy=300,
                yukseklik=180, kalinlik=2, metraj_m2=5.4,
                durum='Serbest', giris_tarihi=date(2026, 10, 1)))
            db.session.commit()
    r = c.put('/api/stok/PLK-DZC', headers=H, json={
        'tip': 'PLAKA', 'cins': 'TEST', 'tonaj': 99, 'metraj_m2': 6.0})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        p = db.session.get(PlakaStok, 'PLK-DZC')
        assert p.metraj_m2 == 6.0, 'metraj yazılmadı'
        assert not hasattr(p, 'tonaj'), 'PLAKA tonaj taşımamalı'


def test_dz2_olcu_degisince_dagitim_uyarisi_cikar():
    """DZ2: dağıtım BİR KEZ yapılır ve paylar SABİT tutar olarak
    yazılır. Ölçü sonradan değişince o paylar eski ölçüye göre
    hesaplanmış kalır.

    Kendiliğinden yeniden dağıtmıyoruz: bu AYNI GRUPTAKİ BAŞKA
    stokların maliyetini de değiştirirdi ve onların satışı çoktan
    faturalanmış olabilir. Sessiz kalmak yerine söylüyoruz."""
    c = istemci('admin', 'ADMIN')
    a = _dz2_kur('DZD1', tonaj=20)
    b = _dz2_kur('DZD2', tonaj=10)
    r = c.post('/api/maliyet/dagit', headers=H, json={
        'maliyet_tip': 'Navlun', 'baglanti_tip': 'stok',
        'hedefler': [a, b], 'tutar': 3000, 'doviz': 'USD',
        'kdv_oran': 0, 'dagitim': 'oransal'})
    assert r.status_code == 200, r.get_json()

    # Olcu DEGISMEYEN bir duzenlemede uyari CIKMAMALI
    r = c.put(f'/api/stok/{a}', headers=H,
              json={'tip': 'BLOK', 'cins': 'TEST', 'konum': 'Depo 3'})
    assert not r.get_json().get('uyarilar'), r.get_json()

    # Olcu degisince uyari CIKMALI
    r = c.put(f'/api/stok/{a}', headers=H,
              json={'tip': 'BLOK', 'cins': 'TEST', 'tonaj': 40})
    d = r.get_json()
    assert d['uyari'] is True, d
    assert any('dağıtılmış maliyet' in u for u in d['uyarilar']), d
    # Paylar DEGISMEDI — baskasinin maliyetine dokunmadik
    with fa.app.app_context():
        from models import Maliyet
        paylar = {m.baglanti_id: m.tutar for m in
                  Maliyet.query.filter(Maliyet.baglanti_id.in_([a, b]),
                                       Maliyet.maliyet_tip == 'Navlun').all()}
        assert paylar[a] == 2000 and paylar[b] == 1000, paylar


def test_dz2_gecersiz_olcu_reddedilir():
    """DZ2: ölçü sayı olmalı ve negatif olamaz. Negatif tonaj,
    negatif alış bedeli demek — kâr tablosu anlamını yitirir."""
    c = istemci('admin', 'ADMIN')
    sid = _dz2_kur('DZE', tonaj=20)
    for deger, bekle in ((-5, 400), ('abc', 400)):
        r = c.put(f'/api/stok/{sid}', headers=H,
                  json={'tip': 'BLOK', 'cins': 'TEST', 'tonaj': deger})
        assert r.status_code == bekle, (deger, r.status_code, r.get_json())
    with fa.app.app_context():
        assert db.session.get(BlokStok, sid).tonaj == 20, 'bozuk değer yazıldı'


def test_dz2_formda_olcu_kutulari_var():
    """DZ2: sunucu düzelmesi tek başına yetmez — kullanıcının
    gördüğü formda kutu yoksa alan yine düzenlenemez."""
    import io as _io
    h = _io.open('templates/stok.html', encoding='utf-8').read()
    for kimlik in ('duzBoy', 'duzYukseklik', 'duzEn', 'duzKalinlik',
                   'duzHacim', 'duzTonaj', 'duzMetraj'):
        assert f'id="{kimlik}"' in h, kimlik
    assert 'function olcuDoldur' in h
    assert 'function olcuGovde' in h
    assert '...olcuGovde(),' in h, 'ölçüler gönderilmiyor'
    # Liste ucu bu ikisini KISA adla veriyor; uzun ad tek basina
    # bos kutu birakirdi
    assert 's.hacim_m3 !== undefined ? s.hacim_m3 : s.hacim' in h
    assert 's.metraj_m2 !== undefined ? s.metraj_m2 : s.m2' in h
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA DZ2 — STOK KAYITLARI DUZENLENEBILIR')
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
        print('    python3 yama_dz2.py            # rapor')
        print('    python3 yama_dz2.py --uygula')
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
        print('  ⊙ Yama DZ2 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_dz2.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_dz2'
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
    print('    Depo -> Stok -> bir blokta Duzenle')
    print('    BOY/YUKSEKLIK/EN/HACIM/TONAJ kutulari gelmis olmali.')
    print('    Tonaji degistir, kaydet: mesaj kac satis kaydinin')
    print('    karinin yeniden hesaplandigini yazacak.')
    print('    Dagitilmis maliyeti olan bir stokta ayrica UYARI cikar.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

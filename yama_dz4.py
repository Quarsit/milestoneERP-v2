#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA DZ4 — KESİM KAYITLARI
===========================

ÖNKOŞUL: yama_dz3.py uygulanmış olmalı.

Dörtlü sıranın sonuncusu.

── ÖLÇÜLEN ──
  Bir bloğu iki plakaya kestim (6.000 USD matrah, 2 × 5,4 m²):
  birim maliyet 555,56 USD/m² — doğru.

  Sonra bir plakanın m²'sini 5,4 → 30 yaptım:

      plaka birim maliyeti : 555,56 → 555,56   ✗
      kardeş plaka         : 555,56 → 555,56   ✗
      kesim kaydının satırı: hâlâ 5,4 m²       ✗

  Doğrusu 6.000 / (30 + 5,4) = 169,49 idi — İKİ plakada da.

── 1 · ÖLÇÜ DEĞİŞİNCE MALİYET YENİDEN DAĞILIYOR ──
  Bloğun maliyeti plakalara m² ORANINDA dağıtılıyor:
  birim = (blok matrahı + ek maliyetler) / toplam m².

  Bir plakanın m²'si değişince PAYDA değişir — yani KARDEŞ
  plakaların birim maliyeti de değişmeli. Dağıtıcı zaten vardı
  (`_kesilmis_blok_maliyet_yeniden_dagit`) ve plakaların canlı
  m²'sini okuyordu; ama yalnız BLOĞA dokunulunca çağrılıyordu.

  Artık kesimden çıkmış bir ürünün ölçüsü değişince o da
  çağrılıyor, ardından bütün kardeş plakaların satış kayıtları
  tazeleniyor. Yeni bir formül yazmadım — iki ayrı dağıtım
  hesabı zamanla birbirinden ayrılırdı.

── 2 · KESİM KAYDI STOKTAN AYRIŞMIYOR ──
  Kesim, o gün ne çıktığının kaydı. Stok düzeltilince kesim
  satırı eski ölçüde kalıyordu: depoda 30 m², belgede 5,4 m².

  Artık kesim satırının boy/yükseklik/kalınlık/m² alanları
  stokla eşitleniyor; birim ve toplam maliyeti de yeni dağıtımdan
  yazılıyor.

── 3 · YALNIZ KESİMDEN ÇIKMIŞ ÜRÜN İÇİN ──
  Doğrudan girilmiş bir plakanın ölçüsünü değiştirmek hiçbir
  bloğun dağıtımını tetiklemiyor — ortada dağıtılacak bir blok
  maliyeti yok. Test bunu ayrıca ölçüyor; yoksa elle girilmiş
  stokların alış fiyatı sessizce ezilebilirdi.

── YANIT NE SÖYLÜYOR ──
      "Stok güncellendi, KSM-MS-K1-01 kesiminin 2 ürününde
       BLK-K bloğunun maliyeti yeniden dağıtıldı"

── ÖLÇÜLDÜ (yamadan sonra) ──
      plaka m²  5,4 → 30
      iki plakanın birim maliyeti : 169,49  ✓
      kesim satırı                : 30,0 m², birim 169,49  ✓
      kesimden gelmeyen plaka     : alış fiyatı dokunulmadı  ✓

  193 test geçti (190 + 3 yeni); iki ayrı koşuda da aynı.
  firma · js · form · zincir · akis · degismezlik temiz.
  Tabanı DZ3'ü uygulayarak ürettim ve DZ4 testlerinin orada
  DÜŞTÜĞÜNÜ görerek doğruladım.

── KESİM KAYDININ KENDİSİ HÂLÂ DÜZENLENEMİYOR ──
  `/api/kesim` yalnız POST ve DELETE taşıyor; kesimin kendi
  başlığını (tarih, açıklama, fire) düzenleyecek bir uç yok.
  Bunu bilerek eklemedim: kesim bir OLAY kaydı ve ondan çıkan
  ürünler artık düzenlenebiliyor, maliyet de takip ediyor.
  Başlığı da düzenlemek istersen söyle, ayrı bir yamayla
  eklerim — ama fire oranını elle değiştirmek maliyeti
  gerçeklikten koparabilir, önce onu konuşalım.

── SIRA TAMAMLANDI ──
      DZ1  maliyet ↔ cari hareket            ✓
      DZ2  stok kayıtları                    ✓
      DZ3  satış / proforma / sipariş        ✓
      DZ4  kesim kayıtları                   ← bu yama

DOSYALAR
--------
  flask_app.py          kesimden çıkan üründe yeniden dağıtım ·
                        kesim satırı stokla eşitleniyor
  tests/test_kritik.py  3 yeni test

Şema yok, göç yok, yeni alan yok.

KULLANIM
--------
  python3 yama_dz4.py            # RAPOR
  python3 yama_dz4.py --uygula
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
    'flask_app.py': 'DZ4 · KESİMDEN ÇIKMIŞ ÜRÜNÜN ÖLÇÜSÜ DEĞİŞTİYSE',
    'tests/test_kritik.py': 'def test_dz4_plaka_olcusu_degisince_maliyet_yeniden_dagilir',
}
ONKOSUL = {
    'flask_app.py': 'DZ3 · PROFORMA TOPLAMI SUNUCUDA TÜRETİLİR',
    'tests/test_kritik.py': 'def test_dz3_proforma_toplami_kalemlerden_turetilir',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'DZ4 · flask_app.py blok 1',
     r'''                db.session.commit()
                # DZ2: yanit, NE OLDUGUNU tasimali. Sessizce 200
                # donmek, kullaniciya "kar da guncellendi mi" diye
                # merak birakiyordu.
                _uyarilar = [u for u in (_doviz_uyari, _dagitim_uyari) if u]
                _mesaj = 'Stok güncellendi'
''',
     r'''                # ══════════════════════════════════════════════════
                #  DZ4 · KESİMDEN ÇIKMIŞ ÜRÜNÜN ÖLÇÜSÜ DEĞİŞTİYSE
                #
                #  Bloğun maliyeti plakalara m² ORANINDA dağıtılıyor:
                #  birim = (blok matrahı + ek maliyetler) / toplam m².
                #  Bir plakanın m²'si değişince PAYDA değişir, yani
                #  KARDEŞ plakaların birim maliyeti de değişmeli.
                #
                #  Dağıtıcı (`_kesilmis_blok_maliyet_yeniden_dagit`)
                #  zaten var ve plakaların CANLI m²'sini okuyor — ama
                #  yalnız bloğa dokunulunca çağrılıyordu. Ölçüldü:
                #  plakanın m²'si 5,4 → 30 yapıldı, iki plakanın da
                #  birim maliyeti 555,56'da kaldı; doğrusu 169,49 idi.
                #
                #  Burada DAĞITIMI yeniden yapmıyoruz, mevcut
                #  dağıtıcıyı çağırıyoruz — iki ayrı formül, zamanla
                #  birbirinden ayrılırdı.
                #
                #  Ayrıca KESİM KAYDININ KENDİ SATIRI stoktan
                #  ayrışıyordu: stok 30 m² olurken kesim satırı 5,4'te
                #  kalıyordu. Kesim, o gün ne çıktığının kaydı; stok
                #  düzeltilince o da düzelmeli.
                # ══════════════════════════════════════════════════
                _kesim_bilgi = None
                if olcu_degisti and not str(stok_id).startswith('BLK'):
                    _dt = KesimDetay.query.filter_by(
                        hedef_stok_id=stok_id).first()
                    if _dt:
                        for _s_alan, _d_alan in (('boy', 'boy'),
                                                 ('yukseklik', 'yukseklik'),
                                                 ('kalinlik', 'kalinlik'),
                                                 ('metraj_m2', 'miktar_m2')):
                            _v = getattr(stok, _s_alan, None)
                            if _v is not None:
                                setattr(_dt, _d_alan, _v)
                        _ks = Kesim.query.get(_dt.kesim_id)
                        if _ks and _ks.kaynak_tip == 'BLOK' and _ks.kaynak_id:
                            db.session.flush()
                            _n = _kesilmis_blok_maliyet_yeniden_dagit(
                                _ks.kaynak_id)
                            db.session.flush()
                            # Kardes plakalarin satis kayitlari da
                            # tazelensin: birim maliyetleri degisti.
                            _kardes = [d.hedef_stok_id for d in
                                       KesimDetay.query.filter_by(
                                           kesim_id=_ks.id).all()
                                       if d.hedef_stok_id]
                            _tazelenen += _maliyet_etkilenen_stoklari_tazele(
                                _kardes)
                            # Kesim satirlarindaki maliyet de stokla
                            # ayni olsun.
                            for _d2 in KesimDetay.query.filter_by(
                                    kesim_id=_ks.id).all():
                                _pl = PlakaStok.query.get(_d2.hedef_stok_id) \
                                    if _d2.hedef_stok_id else None
                                if _pl:
                                    _d2.birim_maliyet = _pl.alis_fiyati
                                    _d2.toplam_maliyet = q2(
                                        (_pl.alis_fiyati or 0)
                                        * (_pl.metraj_m2 or 0))
                            _kesim_bilgi = {
                                'kesim_id': _ks.id,
                                'blok': _ks.kaynak_id,
                                'plaka_sayisi': _n}

                db.session.commit()
                # DZ2: yanit, NE OLDUGUNU tasimali. Sessizce 200
                # donmek, kullaniciya "kar da guncellendi mi" diye
                # merak birakiyordu.
                _uyarilar = [u for u in (_doviz_uyari, _dagitim_uyari) if u]
                _mesaj = 'Stok güncellendi'
                if _kesim_bilgi:
                    _mesaj += (f', {_kesim_bilgi["kesim_id"]} kesiminin '
                               f'{_kesim_bilgi["plaka_sayisi"]} ürününde '
                               f'{_kesim_bilgi["blok"]} bloğunun maliyeti '
                               f'yeniden dağıtıldı')
'''),
    ('flask_app.py', 'DZ4 · flask_app.py blok 2',
     r'''                    'uyari': bool(_uyarilar),
''',
     r'''                    'kesim_yeniden_dagitim': _kesim_bilgi,
                    'uyari': bool(_uyarilar),
'''),
    ('tests/test_kritik.py', 'DZ4 · tests/test_kritik.py blok 1',
     r'''            'kilitli siparişin fiyatı değişmiş'
''',
     r'''            'kilitli siparişin fiyatı değişmiş'


def _dz4_kesim(c, ek, tonaj=20, alis=300):
    """DZ4: bir blogu iki plakaya kes. Her teste kendi kimlikleri."""
    from models import Kesim, KesimDetay
    bid = f'BLK-{ek}'
    with fa.app.app_context():
        if not db.session.get(BlokStok, bid):
            db.session.add(BlokStok(
                id=bid, blok_no=ek, cins='TEST', boy=300, yukseklik=180,
                en=170, hacim_m3=9.18, tonaj=tonaj, alis_fiyati=alis,
                alis_fiyat_birim='ton', doviz='USD', durum='Serbest'))
            db.session.commit()
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': [bid],
        'kesim_tarihi': '2026-10-01',
        'hedefler': [
            {'hedef_tip': 'PLAKA', 'cins': 'TEST', 'boy': 300,
             'yukseklik': 180, 'kalinlik': 2, 'adet': 1},
            {'hedef_tip': 'PLAKA', 'cins': 'TEST', 'boy': 300,
             'yukseklik': 180, 'kalinlik': 2, 'adet': 1}]})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        ks = Kesim.query.filter_by(kaynak_id=bid).first()
        plakalar = [d.hedef_stok_id for d in
                    KesimDetay.query.filter_by(kesim_id=ks.id).all()]
    return bid, ks.id, plakalar


def test_dz4_plaka_olcusu_degisince_maliyet_yeniden_dagilir():
    """DZ4: bloğun maliyeti plakalara m² ORANINDA dağıtılıyor —
    birim = (matrah + ek maliyet) / toplam m². Bir plakanın m²'si
    değişince PAYDA değişir, yani KARDEŞ plakaların birim maliyeti
    de değişmeli.

    Dağıtıcı zaten vardı ve plakaların canlı m²'sini okuyordu, ama
    yalnız BLOĞA dokunulunca çağrılıyordu. Ölçüldü: plakanın m²'si
    5,4 → 30 yapıldı, iki plakanın da birim maliyeti 555,56'da
    kaldı; doğrusu 169,49 idi."""
    from models import PlakaStok
    c = istemci('admin', 'ADMIN')
    bid, kid, plakalar = _dz4_kesim(c, 'DZ4A', tonaj=20, alis=300)
    assert len(plakalar) == 2
    with fa.app.app_context():
        ilk = db.session.get(PlakaStok, plakalar[0])
        # 6000 USD / 10.8 m2
        assert abs((ilk.alis_fiyati or 0) - 555.56) < 0.05, ilk.alis_fiyati

    r = c.put(f'/api/stok/{plakalar[0]}', headers=H,
              json={'tip': 'PLAKA', 'cins': 'TEST', 'metraj_m2': 30})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert d['kesim_yeniden_dagitim'], d
    assert d['kesim_yeniden_dagitim']['blok'] == bid, d

    with fa.app.app_context():
        # 6000 / (30 + 5.4) = 169.49 — IKISINDE DE
        for pid in plakalar:
            p = db.session.get(PlakaStok, pid)
            assert abs((p.alis_fiyati or 0) - 169.49) < 0.05, (pid, p.alis_fiyati)


def test_dz4_kesim_kaydi_stoktan_ayrismaz():
    """DZ4: kesim, o gün ne çıktığının kaydı. Stok düzeltilince
    kesim satırı 5,4 m²'de kalıyordu — belge ile depo birbirini
    tutmuyordu."""
    from models import KesimDetay, PlakaStok
    c = istemci('admin', 'ADMIN')
    bid, kid, plakalar = _dz4_kesim(c, 'DZ4B', tonaj=20, alis=300)

    c.put(f'/api/stok/{plakalar[0]}', headers=H,
          json={'tip': 'PLAKA', 'cins': 'TEST', 'metraj_m2': 25,
                'kalinlik': 3})
    with fa.app.app_context():
        dt = KesimDetay.query.filter_by(hedef_stok_id=plakalar[0]).first()
        p = db.session.get(PlakaStok, plakalar[0])
        assert dt.miktar_m2 == 25, dt.miktar_m2
        assert dt.kalinlik == 3, dt.kalinlik
        # Maliyet de stokla ayni
        assert abs((dt.birim_maliyet or 0) - (p.alis_fiyati or 0)) < 0.01
        # Kardesin maliyeti de guncellendi
        dt2 = KesimDetay.query.filter_by(hedef_stok_id=plakalar[1]).first()
        p2 = db.session.get(PlakaStok, plakalar[1])
        assert abs((dt2.birim_maliyet or 0) - (p2.alis_fiyati or 0)) < 0.01


def test_dz4_kesimden_gelmeyen_stokta_dagitim_calismaz():
    """DZ4: yeniden dağıtım yalnız KESİMDEN çıkmış ürün için.
    Doğrudan girilmiş bir plakanın ölçüsünü değiştirmek hiçbir
    bloğun dağıtımını tetiklememeli — ortada dağıtılacak bir blok
    maliyeti yok."""
    from models import PlakaStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not db.session.get(PlakaStok, 'PLK-DZ4C'):
            db.session.add(PlakaStok(
                id='PLK-DZ4C', blok_no='DZ4C', cins='TEST', boy=300,
                yukseklik=180, kalinlik=2, metraj_m2=5.4,
                alis_fiyati=100, durum='Serbest',
                giris_tarihi=date(2026, 10, 1)))
            db.session.commit()
    r = c.put('/api/stok/PLK-DZ4C', headers=H,
              json={'tip': 'PLAKA', 'cins': 'TEST', 'metraj_m2': 8})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()['kesim_yeniden_dagitim'] is None, r.get_json()
    with fa.app.app_context():
        p = db.session.get(PlakaStok, 'PLK-DZ4C')
        assert p.metraj_m2 == 8
        assert p.alis_fiyati == 100, 'dokunulmamalıydı'
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA DZ4 — KESIM KAYITLARI')
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
        print('    python3 yama_dz4.py            # rapor')
        print('    python3 yama_dz4.py --uygula')
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
        print('  ⊙ Yama DZ4 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_dz4.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_dz4'
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
    print('    Depo -> Stok -> kesimden cikmis bir PLAKADA Duzenle,')
    print('    metrajini degistir. Mesaj, o kesimdeki kac uruneo')
    print('    blogun maliyetinin yeniden dagitildigini yazmali;')
    print('    KARDES plakalarin birim maliyeti de degismeli.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

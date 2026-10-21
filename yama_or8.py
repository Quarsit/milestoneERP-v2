#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA OR8 — KESİLMİŞ BLOĞUN PLAKALARI SEÇİCİDE ÇIKMASIN
=======================================================

ÖNKOŞUL: yama_or7.py uygulanmış olmalı.

Haklısın, bu OR7'de eksik bıraktığım yer.

── ÖNCE İYİ HABER: RAKAMIN BOZULMUYOR ──
  Plakaları da bağlasan ciro İKİ KEZ SAYILMIYOR. Ölçtüm:

      yalnız blok bağlı        ciro 3.000 · 1 satış
      blok + plakalar bağlı    ciro 3.000 · 1 satış

  Sebebi: eşleşme bir KÜME üzerinden tek `or_` sorgusuyla yapılıyor;
  aynı satış iki yoldan eşleşse bile SQL onu bir kez döndürüyor.
  Yani şu ana kadar yaptığın bağlamalarda yanlış bir rakam yok.

── ASIL SORUN EKRANDAYDI ──
  Kesilmiş bir bloğun plakaları seçicide çıkmaya devam ediyordu.
  Bu iki şeye yol açıyor: gereksiz bağlama, ve daha kötüsü
  "bağlamazsam dahil değil" yanılgısı. Oysa blok bağlandığı an
  plakalar zaten dahil.

── NE GELDİ ──
  · Bağlı bir bloğun kesim zinciriyle kapsadığı stoklar seçicide
    ARTIK ÇIKMIYOR.
  · Yine de bağlamaya kalkarsan sebebini söyleyerek duruyor:
    "Bu stok kesim zinciriyle … ortaklığına ZATEN dahil —
     bağlandığı bloktan türemiş."
  · Bağlı iş satırı kapsamı yazıyor:
        BLOK K9001   kesildi → 10 ürün ortaklığa dahil
    "Bloğu bağladım, plakalar dahil mi?" sorusunun cevabı artık
    ekranda duruyor.

── SENİN DURUMUN ──
  4 bloğu bağlamışsın; doğrusu bu. Plakaları ayrıca bağladıysan
  rakam bozulmadı, ama bu yamadan sonra o satırları listeden
  çözebilirsin — blok zaten hepsini kapsıyor.

── ÖLÇÜLDÜ ──
  blok bağlanmadan önce  plakalar seçilebilir
  blok bağlandıktan sonra plaka seçicisi BOŞ
  bağlamaya zorlarsan     409 · 'zaten_kapsanda'
  bağlı iş satırı         kapsanan = 3
  ciro                    3.000 (değişmedi)

  156 test geçti (155 + 1 yeni kalıcı test);
  firma · js · form · zincir · akis · degismezlik temiz.

DOSYALAR
--------
  flask_app.py             kapsam hesabı · seçici · bağlama kapısı
  templates/ortaklik.html  bağlı iş satırında kapsam
  tests/test_kritik.py     1 yeni test

Şema yok, göç yok.

KULLANIM
--------
  python3 yama_or8.py            # RAPOR
  python3 yama_or8.py --uygula
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
    'flask_app.py': 'def _ortaklik_kapsanan_stoklar():',
    'templates/ortaklik.html': 'ürün ortaklığa dahil',
    'tests/test_kritik.py': 'def test_or8_zincirle_kapsanan_stok_secilebilir_gorunmez',
}
ONKOSUL = {
    'flask_app.py': 'def _ortaklik_stok_zinciri(isler):',
    'templates/ortaklik.html': '<option value="BLOK">Blok (stok)</option>',
    'tests/test_kritik.py': 'def test_or7_blok_baglanir_ve_fason_siparis_yokken_gorunur',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'OR8 · flask_app.py blok 1',
     r'''                           'aciklama': i.aciklama or ''}
''',
     r'''                           # OR8: bu iş kaç stoğu dolaylı kapsıyor —
                           # "bloğu bağladım, plakalar dahil mi?"
                           # sorusunun cevabı ekranda dursun.
                           'kapsanan': _ortaklik_is_kapsami(i),
                           'aciklama': i.aciklama or ''}
'''),
    ('flask_app.py', 'OR8 · flask_app.py blok 2',
     r'''        return q2((getattr(s, 'metraj_m2', 0) or 0) * _f)
''',
     r'''        return q2((getattr(s, 'metraj_m2', 0) or 0) * _f)

    def _ortaklik_is_kapsami(i):
        """Bu iş kesimle kaç stok türetmiş (kendisi hariç)."""
        if i.kaynak_tip not in ORTAKLIK_STOK_TIPLERI:
            return 0
        return len(_ortaklik_stok_zinciri([i]) - {i.kaynak_id})

    def _ortaklik_kapsanan_stoklar():
        """OR8 — bir ortaklığa DOLAYLI dahil olan stoklar.

        Blok bağlanınca ondan kesilen plakalar zaten ortaklığa
        dahil: maliyetleri listeleniyor, satışları ciroya giriyor.
        Ama seçicide ayrıca görünüyorlardı — hem gereksiz, hem
        "demek ki dahil değiller" izlenimi veriyordu.

        Döner: {stok_id: (ortaklik_id, kok_stok_id)}  (kökün KENDİSİ
        hariç; o zaten doğrudan bağlı sayılıyor.)
        """
        kapsam = {}
        for ort_id, in db.session.query(OrtaklikIs.ortaklik_id).filter(
                OrtaklikIs.kaynak_tip.in_(ORTAKLIK_STOK_TIPLERI)).distinct():
            isler = OrtaklikIs.query.filter_by(ortaklik_id=ort_id).all()
            kokler = {i.kaynak_id for i in isler
                      if i.kaynak_tip in ORTAKLIK_STOK_TIPLERI}
            for sid in _ortaklik_stok_zinciri(isler) - kokler:
                # İlk bağ kazanır; aynı stok iki zincire düşerse
                # (veride tuhaflık) ikincisini sessizce ezmeyelim.
                kapsam.setdefault(sid, (ort_id, None))
        return kapsam
'''),
    ('flask_app.py', 'OR8 · flask_app.py blok 3',
     r'''            kaynak_tip=tip).all()}
''',
     r'''            kaynak_tip=tip).all()}
        # OR8: doğrudan bağlı olmasa da bir bloğun kesim zinciriyle
        # KAPSANAN stoklar da seçilebilir görünmemeli.
        if tip in ORTAKLIK_STOK_TIPLERI:
            bagli |= set(_ortaklik_kapsanan_stoklar())
'''),
    ('flask_app.py', 'OR8 · flask_app.py blok 4',
     r'''        i = OrtaklikIs(ortaklik_id=oid, kaynak_tip=tip, kaynak_id=kid,
''',
     r'''        # OR8: zincirle zaten kapsanan stoğu ayrıca bağlamaya gerek yok.
        # Rakamı bozmaz (eşleşme küme üzerinden tek sorguyla yapılıyor)
        # ama listeyi şişirir ve "bağlamazsam dahil değil" yanılgısını
        # besler. Sebebini söyleyip durduruyoruz.
        if tip in ORTAKLIK_STOK_TIPLERI:
            _kap = _ortaklik_kapsanan_stoklar().get(kid)
            if _kap:
                _o = _kap[0]
                return jsonify({'ok': False, 'error': 'zaten_kapsanda',
                    'mesaj': (f'Bu stok kesim zinciriyle {_o} ortaklığına '
                              f'ZATEN dahil — bağlandığı bloktan türemiş. '
                              f'Ayrıca bağlamaya gerek yok.')}), 409
        i = OrtaklikIs(ortaklik_id=oid, kaynak_tip=tip, kaynak_id=kid,
'''),
    ('templates/ortaklik.html', 'OR8 · templates/ortaklik.html blok 1',
     r'''      <td>${kacar(i.aciklama || '')}</td>
''',
     r'''      <td>${kacar(i.aciklama || '')}${
        /* OR8: "bloğu bağladım, plakalar dahil mi?" sorusunun cevabı
           ekranda dursun — plakaları ayrıca bağlamaya çalışmayasın. */
        i.kapsanan ? `<span style="color:var(--soluk);font-size:.78rem">${
          i.aciklama ? ' · ' : ''}kesildi → ${i.kapsanan} ürün ortaklığa dahil</span>` : ''}</td>
'''),
    ('tests/test_kritik.py', 'OR8 · tests/test_kritik.py blok 1',
     r'''    assert 'BLK-OR7D' not in idler
''',
     r'''    assert 'BLK-OR7D' not in idler


def test_or8_zincirle_kapsanan_stok_secilebilir_gorunmez():
    """OR8: bağlı bloktan türeyen plakalar seçicide ÇIKMAMALI.

    Rakamı bozmuyordu — eşleşme küme üzerinden tek sorguyla
    yapılıyor, ciro iki kez sayılmıyor (ölçüldü). Ama plakalar
    seçilebilir göründüğü sürece "bağlamazsam dahil değil"
    yanılgısını besliyordu; bağlayınca da bağlı iş listesi gereksiz
    şişiyordu."""
    from models import BlokStok, SatisKaydi
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BLK-OR8', firma_id=1, blok_no='K8800', cins='TEST',
            boy=300, yukseklik=180, en=170, hacim_m3=9.18, tonaj=24,
            alis_fiyati=420, alis_fiyat_birim='ton', doviz='USD',
            durum='Serbest', uretici='ALBSTONE'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': ['BLK-OR8'],
        'kesim_tarihi': '2026-10-10',
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'TEST', 'boy': 280,
                      'yukseklik': 170, 'kalinlik': 2, 'adet': 3}]})
    plakalar = [o['id'] for o in r.get_json()['olusan_stoklar']]
    with fa.app.app_context():
        db.session.add(SatisKaydi(
            id='SAT-OR8', firma_id=1, stok_id=plakalar[0], stok_tip='PLAKA',
            cins='TEST', musteri='ACIK CARI', satis_tarihi=date(2026, 10, 20),
            tutar=3000, tutar_usd=3000, doviz='USD',
            maliyet_usd=1800, kar_usd=1200))
        db.session.commit()

    oid = c.post('/api/ortaklik', headers=H,
                 json={'ad': 'Kapsam'}).get_json()['id']
    # Blok bağlanmadan ÖNCE plakalar seçilebilir
    once = [x['id'] for x in
            c.get(f'/api/ortaklik/{oid}/baglanabilir?tip=PLAKA').get_json()['data']]
    assert all(p in once for p in plakalar), once

    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'BLOK', 'kaynak_id': 'BLK-OR8'})

    # Blok bağlandıktan SONRA plakalar listede YOK
    sonra = [x['id'] for x in
             c.get(f'/api/ortaklik/{oid}/baglanabilir?tip=PLAKA').get_json()['data']]
    assert not any(p in sonra for p in plakalar), sonra

    # Yine de bağlamaya kalkarsan SEBEBİNİ söyleyerek durduruyor
    r2 = c.post(f'/api/ortaklik/{oid}/is', headers=H,
                json={'kaynak_tip': 'PLAKA', 'kaynak_id': plakalar[0]})
    assert r2.status_code == 409, r2.get_data(as_text=True)
    assert r2.get_json().get('error') == 'zaten_kapsanda'
    assert 'türemiş' in r2.get_json()['mesaj']

    # Bağlı iş satırı kapsamı söylüyor
    isler = c.get(f'/api/ortaklik/{oid}').get_json()['data']['isler']
    blok = [i for i in isler if i['kaynak_id'] == 'BLK-OR8'][0]
    assert blok['kapsanan'] == 3, blok

    # Ve ciro zaten plakadan geliyor — blok tek başına yeterli
    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h['ciro'] == 3000 and h['satis_adedi'] == 1, h
'''),
]

TAM_ICERIK = {}

def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA OR8 — KESILMIS BLOGUN PLAKALARI SECICIDE CIKMASIN')
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
        print('    python3 yama_or8.py            # rapor')
        print('    python3 yama_or8.py --uygula')
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
        print('  ⊙ Yama OR8 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_or8.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_or8'
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

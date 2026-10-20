#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA OR5 — SERMAYE "GERİ ALDI" KAYDEDİLEMİYORDU (500)
======================================================

ÖNKOŞUL: yama_or4.py uygulanmış olmalı.

Günlük sebebi tek satırda söyledi:

    psycopg2.errors.StringDataRightTruncation
    HATA: varying(8) veri tipi için çok uzun
    'yon': 'geri_aldi'

`geri_aldi` DOKUZ karakter; sütunu `String(8)` yapmışım. Benim
hatam.

── NEDEN TESTLERDEN GEÇTİ ──
  Testler SQLite'ta koşuyor. SQLite VARCHAR uzunluğunu UYGULAMIYOR —
  on karakterlik değeri `String(8)` sütuna sorunsuz yazıyor.
  PostgreSQL uyguluyor. Yani bu sınıf hata testlerden geçer,
  yalnızca üretimde görünür.

  "Koydu" (5 karakter) çalışıp "Geri aldı" çalışmamasının sebebi
  buydu.

── NE YAPILDI ──
  1) `ortaklik_sermaye.yon` → String(12).

  2) MEVCUT TABLO DA DÜZELTİLİYOR. `db.create_all()` yalnız eksik
     TABLO kurar, var olan sütunun tipini değiştirmez; senin
     veritabanında sütun hâlâ varchar(8). Açılış migrasyonuna
     genişletme adımı eklendi:

         ALTER TABLE ortaklik_sermaye ALTER COLUMN yon TYPE VARCHAR(12)

     Yalnızca PostgreSQL'de ve yalnızca sütun darsa çalışır;
     idempotent. VARCHAR genişletmek tabloyu yeniden yazmaz,
     anında biter. Ayrı bir göç betiği YOK — servisi yeniden
     başlatman yeterli.

  3) BÜTÜN yeni sütunlarımı taradım; dar olan yalnız buydu.

── BU SINIF HATA ARTIK YAKALANIYOR ──
  İki yapısal test eklendi (veritabanı gerekmiyor):

    · Ortaklık tablolarındaki her sabit-değerli sütun, kodun
      yazabileceği EN UZUN değeri taşıyor mu? Sözlük testin
      içinde; yeni bir değer eklerken oraya da eklemek gerekiyor —
      testin görevi bunu zorlamak.
    · models.py'nin TAMAMINDA, bir sütunun `default`'u kendi
      genişliğini aşıyor mu?

  Testin gerçekten yakaladığını ölçtüm: sütunu String(8)'e geri
  alınca düşüyor, düzeltilince geçiyor.

── ÖLÇÜLDÜ ──
  147 test geçti (145 + 2 yeni kalıcı test);
  firma · js · form · zincir · akis · degismezlik temiz.

DOSYALAR
--------
  models.py             yon → String(12)
  flask_app.py          açılışta sütun genişletme
  tests/test_kritik.py  2 yeni test

Göç betiği yok — genişletme açılışta kendiliğinden yapılıyor.

KULLANIM
--------
  python3 yama_or5.py            # RAPOR
  python3 yama_or5.py --uygula
  sudo systemctl restart milestone-erp     ← ALTER burada çalışır
  (tarayıcıda Ctrl+F5)

  Yeniden başlattıktan sonra günlükte şunu görmelisin:
      Migrasyon: ortaklik_sermaye.yon -> VARCHAR(12) (eski 8).
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
    'models.py': "yon         = db.Column(db.String(12), default='koydu')",
    'flask_app.py': 'genisletilecek = [',
    'tests/test_kritik.py': 'def test_or5_metin_sutunlari_yazilacak_degerleri_tasiyor',
}
ONKOSUL = {
    'models.py': 'class OrtaklikSermaye(FirmaKapsamli, db.Model):',
    'flask_app.py': 'def api_ortaklik_baglanabilir(oid):',
    'tests/test_kritik.py': 'def test_or4_sunucunun_hata_mesaji_ustu_ortulmuyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('models.py', 'OR5 · models.py blok 1',
     r'''    yon         = db.Column(db.String(8), default='koydu')  # koydu|geri_aldi
''',
     r'''    # OR5: 'geri_aldi' DOKUZ karakter — String(8) PostgreSQL'de
    # reddediyordu (SQLite sessizce kabul ettiği için testler
    # geçiyordu). Genişlik, taşıyacağı en uzun değere göre.
    yon         = db.Column(db.String(12), default='koydu')  # koydu|geri_aldi
'''),
    ('flask_app.py', 'OR5 · flask_app.py blok 1',
     r'''                print(f'Migrasyon: {tablo}.{sutun} sutunu eklendi.')
''',
     r'''                print(f'Migrasyon: {tablo}.{sutun} sutunu eklendi.')

            # ── OR5 · SÜTUN GENİŞLETME ──
            # `db.create_all()` yalnız eksik TABLO kurar, var olan bir
            # sütunun tipini DEĞİŞTİRMEZ. Dar kalmış bir VARCHAR,
            # PostgreSQL'de kaydı reddeder (SQLite kabul eder — bu
            # yüzden yalnız üretimde görülür).
            #
            # VARCHAR genişletmek PostgreSQL'de tabloyu yeniden
            # yazmaz; anında biter.
            genisletilecek = [
                # (tablo, sutun, yeni uzunluk)
                ('ortaklik_sermaye', 'yon', 12),
            ]
            if _dialect in ('postgresql', 'postgres'):
                for _t, _s, _uz in genisletilecek:
                    if _t not in mufettis.get_table_names():
                        continue
                    _k = {c['name']: c for c in mufettis.get_columns(_t)}
                    _mevcut = _k.get(_s)
                    if not _mevcut:
                        continue
                    _boy = getattr(_mevcut.get('type'), 'length', None)
                    if _boy is None or _boy >= _uz:
                        continue
                    try:
                        with db.engine.begin() as baglanti:
                            baglanti.execute(_text(
                                f'ALTER TABLE {_t} ALTER COLUMN {_s} '
                                f'TYPE VARCHAR({_uz})'))
                        print(f'Migrasyon: {_t}.{_s} -> VARCHAR({_uz}) '
                              f'(eski {_boy}).')
                    except Exception as _e:
                        app.logger.warning(
                            f'Sutun genisletilemedi ({_t}.{_s}): {_e}')
'''),
    ('tests/test_kritik.py', 'OR5 · tests/test_kritik.py blok 1',
     r'''    assert 'istek_hatasi' not in h
''',
     r'''    assert 'istek_hatasi' not in h


# ══════════════════════════════════════════════════════════════════════
#  OR5 · SÜTUN GENİŞLİĞİ — SQLite'ın GÖRMEDİĞİ HATA
# ══════════════════════════════════════════════════════════════════════

def test_or5_metin_sutunlari_yazilacak_degerleri_tasiyor():
    """OR5: VARCHAR genişliği, kodun yazabileceği en uzun değeri almalı.

    SQLite uzunluk kısıtını UYGULAMIYOR; PostgreSQL uyguluyor. Bu
    yüzden dar bir sütun testlerden geçer, üretimde 500 verir —
    `ortaklik_sermaye.yon` String(8) iken 'geri_aldi' (9 karakter)
    tam bunu yaptı.

    Bu test o boşluğu yapısal olarak kapatıyor: veritabanı
    gerekmiyor, sözlükle genişliği karşılaştırıyor."""
    import io as _io, re as _re
    kaynak = _io.open('models.py', encoding='utf-8').read()

    # Kodun bu sütunlara yazabileceği SABİT değerler. Yeni bir değer
    # eklerken buraya da eklenmeli — testin görevi bunu zorlamak.
    SOZLUK = {
        'Ortaklik': {
            'anapara_yontemi': ['ayri', 'once_iade'],
            'durum': ['Acik', 'Kapandi'],
            'doviz': ['USD', 'EUR', 'TRY']},
        'OrtaklikIs': {
            'kaynak_tip': ['SIPARIS', 'SEVKIYAT', 'PROFORMA']},
        'OrtaklikVergi': {
            'matrah_tipi': ['kar', 'ciro', 'sabit'],
            'durum': ['tahmini', 'kesinlesti', 'odendi'],
            'doviz': ['USD', 'EUR', 'TRY']},
        'OrtaklikSermaye': {
            'taraf': ['ortak', 'biz'],
            'yon': ['koydu', 'geri_aldi'],
            'doviz': ['USD', 'EUR', 'TRY']},
        'OrtaklikDagitim': {
            'taraf': ['ortak', 'biz'],
            'doviz': ['USD', 'EUR', 'TRY']},
    }

    dar = []
    for sinif, alanlar in SOZLUK.items():
        _b = kaynak.index(f'class {sinif}(')
        _s = kaynak.index('\nclass ', _b + 1) if '\nclass ' in kaynak[_b + 1:] else len(kaynak)
        govde = kaynak[_b:_s]
        for alan, degerler in alanlar.items():
            e = _re.search(r'\b%s\s*=\s*db\.Column\(db\.String\((\d+)\)' % alan, govde)
            assert e, f'{sinif}.{alan} bulunamadı'
            boy, enuzun = int(e.group(1)), max(degerler, key=len)
            if len(enuzun) > boy:
                dar.append(f'{sinif}.{alan}: String({boy}) ama '
                           f"'{enuzun}' {len(enuzun)} karakter")
    assert not dar, 'Dar sütun(lar): ' + ' · '.join(dar)


def test_or5_varsayilan_degerler_sutuna_sigiyor():
    """OR5: bir sütunun `default`'u kendi genişliğini aşamaz.

    Aynı sınıf hata, genel hâli: SQLite'ta görünmez, PostgreSQL'de
    kayıt açılamaz. Bütün modeli tarıyor."""
    import io as _io, re as _re
    kaynak = _io.open('models.py', encoding='utf-8').read()
    kotu = []
    for e in _re.finditer(
            r"db\.Column\(db\.String\((\d+)\)[^)\n]*?default=(['\"])(.*?)\2",
            kaynak):
        boy, deger = int(e.group(1)), e.group(3)
        if len(deger) > boy:
            satir = kaynak[:e.start()].count('\n') + 1
            kotu.append(f"models.py:{satir} String({boy}) <- '{deger}'")
    assert not kotu, 'Varsayılanı sığmayan sütun(lar): ' + ' · '.join(kotu)
'''),
]

TAM_ICERIK = {}

def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA OR5 — SERMAYE GERI ALDI 500 VERIYORDU')
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
        print('    python3 yama_or5.py            # rapor')
        print('    python3 yama_or5.py --uygula')
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
        print('  ⊙ Yama OR5 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_or5.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_or5'
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
    print('    1) sudo systemctl restart milestone-erp  <- ALTER burada')
    print('    2) Gunlukte sunu gormelisin:')
    print('       Migrasyon: ortaklik_sermaye.yon -> VARCHAR(12) (eski 8).')
    print('    3) Sermaye > Geri aldi hareketini tekrar dene.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

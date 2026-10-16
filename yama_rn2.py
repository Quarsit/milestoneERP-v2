#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA RN2 — CARİ HAREKET KİMLİĞİ FİRMA KODUNU TAŞIR
===================================================

ÖNKOŞUL: MF1–MF7 ve TZ1 uygulanmış olmalı.

── SORUN  [ÖLÇÜLDÜ] ──
   Okunur kimlikler sayaçla üretiliyor: üreteç kökü `LIKE` ile
   tarayıp en büyük numarayı bulur, bir ekler. Sipariş, proforma,
   fatura ve kesim `_okunur_id` üzerinden geçiyor ve orada kök
   FİRMA KODUNU taşıyor. Cari hareket ise AYRI BİR YOLDA:
   `_cari_hareket_okunur_id` kancası kendi kökünü kuruyor ve kodu
   almıyordu.

   Sonuç ölçüldü — üç firma, aynı müşteri, kod öncesi hâl:

       STONEHUB'ın hareketi   HR-STN26-0001
       MILESTONE'un hareketi  HR-STN26-0002

   Kimlikler ÇAKIŞMIYOR; tarama tüm firmalarda benzersizlik arıyor.
   Ama her firmanın defteri DELİKLİ görünüyor: MILESTONE'un
   ekstresinde 0002 var, 0001 yok — çünkü 0001 başka şirkete ait.
   Denetimde "silinmiş kayıt" diye okunur ve açıklaması yoktur.
   Üstelik "bu firmalar bağımsız şirketler, hepsi kendi belge
   kimliklerini taşımalı" kuralına aykırı.

   Hata vermiyor, günlüğe düşmüyor, hiçbir denetim görmüyordu.

── ŞİMDİ YAPMANIN SEBEBİ ──
   Kimlik şeması değiştirmenin maliyeti normalde "mevcut kimlikler
   ne olacak" sorusudur. Sıfırlama sonrası cari hareket sayısı SIFIR
   — korunacak hiçbir kimlik yok, göç gerekmiyor. Veri girişi
   başladıktan sonra aynı değişiklik göç işine dönerdi.

── ÇÖZÜM ──
   Kök artık firma kodunu taşıyor:

       ANA firma (kodu boş)   HR-STN26-0001      ← biçim değişmedi
       STONEHUB (kod SHB)     HR-SHB-STN26-0001
       UCUNCU   (kod UCU)     HR-UCU-STN26-0001

   `LIKE` taraması bu köke baktığı için her firmanın sayacı
   kendiliğinden 0001'den başlıyor. Benzersizlik korunuyor: kökler
   birbirinin öneki olamıyor, çünkü kod her zaman `-` ile kapanıyor
   ve kısaltma+yıl bloğu her zaman 5 karakter.

   KOD OTURUMDAN DEĞİL SATIRDAN OKUNUYOR. `_firma_belge_kodu()`
   istek bağlamına bakıyor ve CLI'da, betiklerde, testlerde boş
   dönüyor. Oysa damga (`before_flush`) bu kancadan ÖNCE çalışıp
   `firma_id`yi dolduruyor — ölçüldü. Satırdan okumak hem bağlamsız
   yollarda doğru çalışır hem de kimlik ile damga asla ayrışmaz.
   Firma sorgusu flush başına önbellekleniyor; kanca her satır için
   çalışıyor, her birinde sorgu açmak gereksizdi.

   ANA firmanın kodu boş olduğu için MILESTONE'un kimlik biçimi
   DEĞİŞMİYOR. Ana firmaya da kod vermek istersen Ayarlar →
   Firmalar'dan belge kodunu doldurmak yeterli: hem bu üreteç hem
   `_okunur_id` kodu oradan okuyor, kod değişikliği gerekmiyor.
   Şu an belge yok, yani bunun için de en uygun an.

── F5 · DENETİM EKSENİ ──
   Bunu düzeltmek yetmez; bir daha sessizce geri gelmemeli.
   `firma_denetim.py`'ye F5 ekseni ekleniyor:

     `id LIKE` ile sayaç tarayan HER fonksiyon firma kodunu da
     çözmeli.

   Kaynakta iki sayaç tarayıcısı var (`_cari_hareket_okunur_id` ve
   `_okunur_id`); F5 ikisini de bulup gövdesinde kod çözümü arıyor.
   Tersten denendi: düzeltme geri alındığında F5 bulguyu yakalıyor
   ve push kapısı kapanıyor.

── NE DEĞİŞMİYOR ──
   • Elle verilen kimlikler (içe aktarma, testler, düzeltme
     betikleri) dokunulmadan kalıyor — kanca yalnızca
     `HR-[0-9A-F]{6}` kalıbındaki otomatik rastgele kimliği
     yeniden yazıyor.
   • `HX-{cek.id}` (çek ters hareketi), `{kok_id}_Rev.{n}`
     (proforma revizyonu) ve `_yeni_id` (rastgele KRS/yedek kimlik)
     ellenmedi: ilk ikisi kodu ebeveyninden devralıyor, üçüncüsü
     sayaç değil rastgele — deliği okunacak bir dizi yok.
   • Şema değişmiyor, göç gerekmiyor.

── ÖLÇÜMLER ──
   t_rn2.py · sekiz eksen, hepsi geçti:
     1 her firmanın sayacı 0001'den başlıyor
     2 ana firma eski biçimi koruyor, diğerleri kod taşıyor
     3 kimlikler benzersiz, hiçbiri 20 karakteri geçmiyor (en uzun 17)
     4 kökler karışmıyor — LIKE taraması sızmıyor
     5 elle verilen kimliğe dokunulmuyor
     6 aynı flush'ta iki bacak (avans devri) ayrı numara alıyor
     7 firma_id yoksa damga koyuluyor, kimlik damgaya uyuyor
     8 EKRANDAN girilen hareket: HTTP 200, HR-UCU-STN26-0004 ve
       FTR-UCU-STN26-01 — ikisi de kodlu

   Sekizinci eksen ilk turda YALANCI GEÇMİŞTİ: uç 400 dönüyordu
   (test veritabanında kur yoktu), kayıt hiç açılmıyordu ve test
   eski satırları sayıp "geçti" diyordu. Artık uç 200 dönmedikçe
   test başarısız sayılıyor — ekran yolu gerçekten koşuyor.

   81 test geçti; altı denetim temiz.

DOSYALAR
--------
  flask_app.py       _cari_hareket_okunur_id — kök firma kodunu alır
  firma_denetim.py   F5 ekseni

KULLANIM
--------
  python3 yama_rn2.py            # RAPOR
  python3 yama_rn2.py --uygula
  sudo systemctl restart milestone-erp
  venv/bin/python firma_denetim.py
"""

import os
import py_compile
import shutil
import sys
import tempfile

UYGULA = '--uygula' in sys.argv
KOK = os.path.dirname(os.path.abspath(__file__))

# ── İMZA ──
# Her dosyada TAM ve AYIRT EDİCİ bir dize. Bu projede alt dizgi
# tuzağına üç kez düştüm ('MF2' imzası MF1'in docstring'inde
# MF2'den söz edildiği için eşleşmişti). İmza, yamanın GERÇEKTEN
# eklediği benzersiz satır.
DOSYA_IMZA = {
    'flask_app.py': 'RN2 · FİRMA KODU KÖKE GİRER',
    'firma_denetim.py': 'F5 · KİMLİK SAYAÇLARI',
}
ONKOSUL = {
    # MF3'ün firma kodu yardımcısı olmadan bu yamanın anlamı yok.
    'flask_app.py': 'def _firma_belge_kodu',
    # TZ1 ile gelen dosya; yoksa önce TZ1 uygulanmalı.
    'firma_denetim.py': 'ÇOKLU FİRMA DENETİMİ',
}

DEGISIKLIKLER = [
    ('flask_app.py', 'RN2-a · kok firma kodunu tasir',
     r'''            kis = (kis + 'XXX')[:3]
            yil = (hareket.hareket_tarihi or date.today()).strftime('%y')
            kok = f'HR-{kis}{yil}-'
''',
     r'''            kis = (kis + 'XXX')[:3]
            yil = (hareket.hareket_tarihi or date.today()).strftime('%y')
            # ── RN2 · FİRMA KODU KÖKE GİRER ──
            # Eskiden kök `HR-{kis}{yil}-` idi ve firma kodu YOKTU.
            # Sayaç bu kökü `LIKE` ile tarıyor, yani iki firma aynı
            # müşteri için AYNI SAYACI paylaşıyordu. Ölçüldü: STONEHUB'ın
            # hareketi HR-STN26-0001, MILESTONE'un hareketi HR-STN26-0002
            # oldu. Kimlikler çakışmıyor (tarama tüm firmalarda
            # benzersizlik arıyor) ama her firmanın defteri DELİKLİ
            # görünüyor: MILESTONE'un ekstresinde 0002 var, 0001 yok.
            # Denetimde "silinmiş kayıt" diye okunur.
            #
            # Sipariş/proforma/kesim kimlikleri bunu `_okunur_id`
            # içinde zaten yapıyordu; cari hareket ayrı bir yolda
            # olduğu için atlanmıştı. Kök artık firma kodunu taşıyor,
            # LIKE taraması o köke bakıyor ve her firmanın sayacı
            # kendiliğinden 0001'den başlıyor.
            #
            # KOD, OTURUMDAN DEĞİL SATIRDAN OKUNUYOR.
            # `_firma_belge_kodu()` istek bağlamına bakıyor ve CLI'da,
            # betiklerde, testlerde boş dönüyor. Oysa damga (before_flush)
            # bu kancadan ÖNCE çalışıp `firma_id`yi dolduruyor (ölçüldü),
            # yani satırın gerçek firması burada zaten biliniyor. Satırdan
            # okumak hem bağlamsız yollarda da doğru çalışır hem de kimlik
            # ile damga asla birbirinden ayrılmaz.
            #
            # ANA firmada belge kodu BOŞSA kök eskisi gibi kalır
            # (HR-STN26-0001) — mevcut kimlikler korunur. Ana firmaya da
            # kod vermek istersen Ayarlar → Firmalar'dan belge kodunu
            # doldurmak yeterli; burada kod değişikliği gerekmiyor.
            _fk = ''
            try:
                _fid = getattr(hareket, 'firma_id', None)
                if _fid:
                    # Flush başına önbellek: bu kanca her satır için
                    # çalışıyor, her birinde firma sorgusu açmak gereksiz.
                    # Aynı desen aşağıdaki sayaç için de kullanılıyor.
                    _kod_onb = baglanti.info.setdefault('rn2_firma_kod', {})
                    if _fid in _kod_onb:
                        _fk = _kod_onb[_fid]
                    else:
                        _fr = baglanti.execute(sa_text(
                            'SELECT belge_kodu FROM firma WHERE id = :i'),
                            {'i': _fid}).fetchone()
                        _fk = ((_fr[0] if _fr else '') or '').strip().upper()
                        _kod_onb[_fid] = _fk
            except Exception:
                # Kod okunamazsa kimliksiz kalmaktansa eski kökle devam:
                # kimlik üretilemezse hareket rastgele kimlikle yazılır ve
                # okunurluk kaybolur. Benzersizlik her durumda korunur.
                _fk = ''
            kok = f'HR-{_fk}-{kis}{yil}-' if _fk else f'HR-{kis}{yil}-'
'''),
    ('firma_denetim.py', 'RN2-b · F5 ekseni',
     r'''        print(f"       {_d:<34} {_n}")

''',
     r'''        print(f"       {_d:<34} {_n}")

# ══════════════════════════════════════════════════════════════════════
#  F5 · KİMLİK SAYAÇLARI
# ══════════════════════════════════════════════════════════════════════
#
# Okunur kimlikler (SIP-STN26-03, HR-STN26-0007) sayaçla üretiliyor:
# üreteç kökü `LIKE` ile tarayıp en büyük numarayı bulur, bir ekler.
# Kök FİRMA KODUNU TAŞIMAZSA iki firma AYNI SAYACI paylaşır.
#
# Ölçüldü (RN2): kök `HR-{kisaltma}{yil}-` idi, firma kodu yoktu.
# STONEHUB'ın hareketi HR-STN26-0001, MILESTONE'un HR-STN26-0002
# oldu. Kimlikler çakışmıyor — tarama tüm firmalarda benzersizlik
# arıyor — ama her firmanın defteri DELİKLİ görünüyor: MILESTONE'un
# ekstresinde 0002 var, 0001 yok. Denetimde "silinmiş kayıt" diye
# okunur. Sessiz, çünkü hiçbir hata vermiyor.
#
# Kural: `id LIKE` ile sayaç tarayan her fonksiyon firma kodunu da
# çözmeli. İki yolla olur — `_firma_belge_kodu()` (oturumdan) ya da
# satırın firma_id'sinden `belge_kodu` okumak.
KOD_BELIRTILERI = ('_firma_belge_kodu', 'belge_kodu FROM firma')
print()
print("─" * 70)
print(" F5 · KİMLİK SAYAÇLARI   [FİRMALARIN PAYLAŞTIĞI SAYAÇ]")
print("─" * 70)
_satirlar = KAYNAK.split('\n')
_tarama = [i for i, s in enumerate(_satirlar)
           if re.search(r'id LIKE|id\.like\(', s)]
_eksik, _tamam = [], []
for _i in _tarama:
    # Kapsayan `def`i geriye doğru arayıp gövdesini çıkar: girintisi
    # def'ten büyük olan satırlar o fonksiyonun gövdesi.
    _d = None
    for _j in range(_i, -1, -1):
        _m = re.match(r'^(\s*)def\s+(\w+)', _satirlar[_j])
        if _m:
            _d = (_j, len(_m.group(1)), _m.group(2))
            break
    if not _d:
        _eksik.append((_i + 1, '<fonksiyon dışı>'))
        continue
    _bas, _gir, _ad = _d
    _govde = []
    for _k in range(_bas + 1, len(_satirlar)):
        _s = _satirlar[_k]
        if _s.strip() and (len(_s) - len(_s.lstrip())) <= _gir:
            break
        _govde.append(_s)
    _metin = '\n'.join(_govde)
    if any(b in _metin for b in KOD_BELIRTILERI):
        _tamam.append((_ad, _i + 1))
    else:
        _eksik.append((_i + 1, _ad))
if _eksik:
    for _n, _ad in _eksik:
        print(f"   ✗ {_ad}  (satır {_n}) — sayaç tarıyor ama firma kodunu")
        print("     çözmüyor: iki firma aynı numara dizisini paylaşır")
    print()
    print("   → Köke firma kodunu ekleyin. Satırın kendi firmasından")
    print("     okumak yeğdir (`SELECT belge_kodu FROM firma WHERE id`):")
    print("     `_firma_belge_kodu()` istek bağlamına bakıyor ve CLI'da,")
    print("     betiklerde, testlerde boş döner.")
    bulgu += len(_eksik)
else:
    print(f"   ✓ temiz — {len(_tamam)} sayaç tarayıcısının hepsi firma")
    print("     kodunu çözüyor")
    for _ad, _n in _tamam:
        print(f"       {_ad:<28} satır {_n}")

'''),
]


def main():
    print('=' * 70)
    print('  YAMA RN2 — CARİ HAREKET KİMLİĞİ FİRMA KODUNU TAŞIR')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    gruplar = {}
    for dosya, aciklama, eski, yerine in DEGISIKLIKLER:
        gruplar.setdefault(dosya, []).append((aciklama, eski, yerine))

    sonuclar, hata, zaten = {}, False, []

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
        print('  ⊙ Yama RN2 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_rn2.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_rn2'
            shutil.copy2(yol, yedek)
            _y = f'    yedek  : {os.path.relpath(yedek, KOK)}'
        else:
            _y = '    (yeni dosya — yedek yok)'
        with open(yol, 'w', encoding='utf-8', newline='') as f:
            f.write(icerik)
        if yol.endswith('.sh'):
            os.chmod(yol, 0o755)
        print(f'  ✓ yazıldı: {os.path.relpath(yol, KOK)}')
        print(_y)

    print('\n  ✓ YAMA UYGULANDI')
    print()
    print('    sudo systemctl restart milestone-erp')
    print()
    print('  SONRA:')
    print('    venv/bin/python firma_denetim.py     # F5 ekseni temiz mi')
    print()
    print('  Yeni kimlik biçimi (ana firmanın kodu boş olduğu için')
    print('  MILESTONE\'un biçimi DEĞİŞMİYOR):')
    print('      MILESTONE          HR-STN26-0001')
    print('      kodu SHB olan firma  HR-SHB-STN26-0001')
    print()
    print('  Ana firmaya da kod vermek istersen Ayarlar → Firmalar\'dan')
    print('  belge kodunu doldur — kod değişikliği gerekmiyor, hem bu')
    print('  üreteç hem sipariş/fatura üreteci oradan okuyor. Şu an')
    print('  belge yok, en uygun an.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA R4 — sifirla2.py'ye `kalem_karsilama` eklenir
===================================================

SORUN
-----
`sifirla2.py` şu an ÇALIŞMAYI REDDEDİYOR:

    ✗ KAPSAM DIŞI TABLO(LAR) VAR — çalışmayı reddediyorum:
        kalem_karsilama

Betiğin kapsama denetimi, veritabanındaki her tablonun ya KORUNAN ya
da SİLİNECEK listesinde olmasını şart koşuyor. `kalem_karsilama`
tablosu F1 ile eklendi (sipariş kalemlerinin kaynak kırılımı: stok /
üretim / dış alım) ama sıfırlama betiğine yazılmadı.

Denetim tam da bunun için konmuştu — sessizce test verisi bırakmak
yerine durdu. Düzeltmesi tek satır.

NE DEĞİŞİYOR
------------
1) `kalem_karsilama` SİLİNECEK listesine girer.
   İşlem verisidir: silinen sipariş kalemlerine atıfta bulunur,
   tutmak olmayan kalemlerden söz eden kayıtlar bırakırdı.
   Silme SIRASI listeden değil modelin topolojik sırasından
   türetiliyor, o yüzden listedeki yeri önemli değil.

2) `bildirimler`, `proforma_kalem`, `siparis_kalem` dizi sıfırlama
   listesine eklenir. Üçü de tamsayı `id` taşıyor ve siliniyor; dizi
   sıfırlanmazsa temiz başlangıçta ilk kalem id'si 1 değil, eski
   sayacın kaldığı yerden devam eder. (`kalem_karsilama` metin id
   kullanıyor — KRS... — dizisi yok.)

3) Başlıktaki tablo sayıları düzeltilir (6/27 yazıyordu, 8/27 doğru).

DOSYA
-----
  sifirla2.py  (4 nokta)

KULLANIM
--------
  python3 yama_r4.py            # RAPOR — hiçbir dosyaya dokunmaz
  python3 yama_r4.py --uygula   # uygular, yanına .yedek_r4 bırakır
"""

import os
import sys
import shutil
import py_compile
import tempfile

UYGULA = '--uygula' in sys.argv
IMZA = 'R4'
KOK = os.path.dirname(os.path.abspath(__file__))

DEGISIKLIKLER = [
    (
        'sifirla2.py',
        'R4-a · kalem_karsilama SILINECEK listesine',
        """    'proforma_kalem', 'proforma',
    'siparis_kalem',""",
        """    'proforma_kalem', 'proforma',
    # R4: F1 ile gelen kalem kaynak kirilimi (stok/uretim/dis alim).
    # Betige yazilmadigi icin kapsama denetimi calismayi REDDEDIYORDU.
    'kalem_karsilama',
    'siparis_kalem',""",
    ),
    (
        'sifirla2.py',
        'R4-b · dizi sifirlamaya uc tablo daha',
        """DIZI_SIFIRLA = ['kasa_hareket', 'kesim_detay',
                'cek_hareket', 'audit_log', 'konteyner', 'cari_aktivite']""",
        """# R4: bildirimler / proforma_kalem / siparis_kalem de tamsayi id
# tasiyor ve siliniyor. Dizi sifirlanmazsa "temiz baslangic"ta ilk
# kalem id'si 1 degil, eski sayacin kaldigi yerden devam ederdi.
# kalem_karsilama METIN id kullaniyor (KRS...), dizisi yok.
DIZI_SIFIRLA = ['kasa_hareket', 'kesim_detay',
                'cek_hareket', 'audit_log', 'konteyner', 'cari_aktivite',
                'bildirimler', 'proforma_kalem', 'siparis_kalem']""",
    ),
    (
        'sifirla2.py',
        'R4-e · kapanis mesaji: kasa tanimlari artik siliNMIyor',
        """print(" SONRAKİ ADIMLAR:")
print("   1) Kasa/banka hesaplarını yeniden tanımlayın (açılış bakiyesiyle)")""",
        """print(" SONRAKİ ADIMLAR:")
# R4: KB1'den beri kasa/banka TANIMLARI korunuyor, yalnizca bakiye
# sifirlaniyor. Mesaj "yeniden tanimlayin" diyordu; yeniden tanimlamak
# mukerrer kasa acardi.
print("   1) Kasa açılış bakiyelerini girin (tanımlar duruyor)")""",
    ),
    (
        'sifirla2.py',
        'R4-c · baslik: korunan tablo sayisi 6 -> 8',
        """#  ══ KORUNUR (6 tablo) ══""",
        """#  ══ KORUNUR (8 tablo) ══""",
    ),
    (
        'sifirla2.py',
        'R4-d · baslik: silinen tablo sayisi 27 (kalem_karsilama ile)',
        """#  ══ SİLİNİR (27 tablo) ══
#    Tüm işlem verisi: stok, sipariş, proforma, fatura, sevkiyat,
#    kesim, maliyet, çek, kasa+hareketleri, cari hareketleri,
#    KDV iade, konteyner, sabit gider, nakit planı, denetim izi,
#    banka tanımları.""",
        """#  ══ SİLİNİR (27 tablo) ══
#    Tüm işlem verisi: stok, sipariş (kalem karşılama kırılımı
#    dahil), proforma, fatura, sevkiyat, kesim, maliyet, çek, kasa
#    hareketleri, cari hareketleri, KDV iade, konteyner, sabit gider,
#    nakit planı, bildirimler, denetim izi.
#    NOT: `banka` tablosu SİLİNMEZ — tanımlar korunur (aşağıda).""",
    ),
]


def main():
    print('=' * 68)
    print(f'  YAMA {IMZA} — sifirla2.py kapsama eksigi')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 68)

    gruplar = {}
    for dosya, aciklama, eski, yeni in DEGISIKLIKLER:
        gruplar.setdefault(dosya, []).append((aciklama, eski, yeni))

    sonuclar, hata_var, zaten = {}, False, []

    for dosya, isler in gruplar.items():
        yol = os.path.join(KOK, dosya)
        print(f'\n── {dosya} ' + '─' * max(0, 50 - len(dosya)))
        if not os.path.exists(yol):
            print(f'  ✗ DOSYA YOK: {yol}')
            hata_var = True
            continue

        with open(yol, 'rb') as f:
            ham = f.read()
        crlf = b'\r\n' in ham
        icerik = ham.decode('utf-8')
        if crlf:
            icerik = icerik.replace('\r\n', '\n')
            print('  · CRLF satır sonu algılandı, korunacak')

        if IMZA in icerik:
            print(f'  ⊙ İmza "{IMZA}" zaten var — ATLANIR')
            zaten.append(dosya)
            continue

        yeni_icerik, bozuk = icerik, False
        for aciklama, eski, yeni in isler:
            n = yeni_icerik.count(eski)
            if n != 1:
                print(f'  ✗ {aciklama}')
                print(f'     kalıp {n} kez eşleşti (tam 1 olmalı)')
                hata_var = bozuk = True
                continue
            yeni_icerik = yeni_icerik.replace(eski, yeni, 1)
            print(f'  ✓ {aciklama}')
        if bozuk:
            continue

        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False,
                                         encoding='utf-8') as tf:
            tf.write(yeni_icerik)
            gec = tf.name
        try:
            py_compile.compile(gec, doraise=True, cfile=gec + 'c')
            print('  ✓ söz dizimi doğrulandı (py_compile)')
        except py_compile.PyCompileError as e:
            print(f'  ✗ SÖZDİZİMİ HATASI:\n{e}')
            hata_var = True
        finally:
            for p in (gec, gec + 'c'):
                if os.path.exists(p):
                    os.unlink(p)

        sonuclar[yol] = (yeni_icerik.replace('\n', '\r\n') if crlf
                         else yeni_icerik)

    print('\n' + '=' * 68)
    if hata_var:
        print('  ✗ HATA VAR → Hiçbir dosyaya DOKUNULMADI')
        return 1
    if zaten and not sonuclar:
        print(f'  ⊙ Yama {IMZA} zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_r4.py --uygula')
        return 0

    for yol, icerik in sonuclar.items():
        yedek = yol + '.yedek_r4'
        shutil.copy2(yol, yedek)
        with open(yol, 'w', encoding='utf-8', newline='') as f:
            f.write(icerik)
        print(f'  ✓ yazıldı: {os.path.relpath(yol, KOK)}')
        print(f'    yedek  : {os.path.relpath(yedek, KOK)}')

    print('\n  ✓ YAMA UYGULANDI')
    print('\n  Sonraki adım — ÖNCE RAPOR MODU:')
    print('    venv/bin/python sifirla2.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA TZ1 — SIFIRLAMA / TEMİZLİK / PUSH BETİKLERİ ÇOKLU FİRMAYA UYARLANIR
=========================================================================

ÖNKOŞUL: MF1–MF7 uygulanmış olmalı.

Çoklu firma geldikten sonra bu üç betik aileyi de gözden geçirdim.
Beşi bozuktu; ikisi ÖLÇÜLDÜ, üçü SESSİZCE yanlış çalışıyordu.

── 1 · sifirla2.py ÇALIŞMAYI REDDEDİYOR  [ÖLÇÜLDÜ]
   `firma` ve `cari_firma` tabloları ne KORUNAN ne SİLİNECEK
   listesindeydi; kapsama denetimi doğru davranıp durdu:

       ✗ KAPSAM DIŞI TABLO(LAR) VAR — çalışmayı reddediyorum:
           cari_firma
           firma

   Reddetmesi doğruydu — yarım sıfırlama yapmaktan iyidir. Ama
   sıfırlamak istediğin an öğrenilen bir şey.

── 2 · ÜÇ SIFIRLAMA KİPİ YOKTU  [İSTENEN, YAPILMAMIŞTI]
   Çoklu firmayı isterken şunu söylemiştin:

     "eğer sıfırlama yapmak istenirse sistem tüm verileri sil, tüm
      firmaları sıfırla ve sadece... firmasını sıfırla gibi seçimler
      sunmalı ve A firmasını sıfırlayı seçtiğimizde B, C ...
      firmalarının verileri kaybolmamalı"

   MF4 yalnızca FİRMA SİLMEYİ getirdi; sıfırlama kipleri yapılmadı.
   Şimdi üçü de var ve "diğerleri kaybolmamalı" sözü ÖLÇÜLÜYOR:
   betik silmeden önce her firmayı sayıyor, sildikten sonra tekrar
   sayıyor; dokunulmayan bir firmanın sayısı değiştiyse DOĞRULAMA
   BAŞARISIZ verip çıkıyor. Söz verip ölçmemek, söz vermemekten
   kötüdür.

── 3 · temizle.sh HİÇBİR YAMAMI TANIMIYOR  [SESSİZ, ÖLÇÜLDÜ]
   Betik "uygulanmış" kararını şu satırla veriyordu:

       grep -q "Zaten uygulanmış"          ← BÜYÜK Z

   Benim yamalarım ise şöyle yazıyor:

       ⊙ Yama MF7 zaten uygulanmış.        ← küçük z

   Sonuç: uygulanmış 10 yamanın HEPSİ "UYGULANMAMIŞ" göründü,
   betik hiçbirini silmedi ve ekrana zaten uygulanmış yamaları
   TEKRAR UYGULA diye yazdı — en altta da "✓ Zaten temiz" dedi.
   İki cümle birbirini yalanlıyordu.

   Bu benim hatam: kendi yama şablonumun çıktısını, onu okuyacak
   betiğe uydurmadım. Eşleşme artık büyük/küçük harfe duyarsız.

── 4 · YEDEK DOSYALARI İKİ TEMİZLİKTEN DE KAÇIYOR  [SESSİZ, ÖLÇÜLDÜ]
   temizle.py ve temizle.sh `*.yedek-*` (TİRE) arıyor. Yamalarım
   `*.yedek_*` (ALT ÇİZGİ) yazıyor — flask_app.py.yedek_mf7 gibi.
   Hiçbiri eşleşmiyor.

   Depoya sızmıyorlar (.gitignore'da `*.yedek_*` var) ama diskte
   birikiyorlar: bu klonda 28 tane vardı. Her iki betik de artık
   iki deseni birlikte arıyor.

── 5 · gonder.sh BAŞARIYI KELİME ARAYARAK ANLIYOR  [YAPISAL]
   Denetim kapısı başarıyı metinde kelime arayarak ölçüyordu:

       grep -qE "TEMİZ|temiz$|uyumlu"

   Bu tasarım bir kez çoktan patladı: sema_denetim "Şema modellerle
   uyumlu" diyor, kelime listesinde yoktu ve iki tur boyunca
   "çalıştırılamadı" sanıldı. Dosyadaki yorumda yazılı.

   Çare kelime eklemek değil — her denetim aracı ÇIKIŞ KODUNU
   doğru veriyor (0 temiz / 1 bulgu). Ölçtüm: altı aracın hepsi.
   Artık esas sinyal çıkış kodu; metne yalnızca "çöktü mü bulgu mu
   buldu" ayrımı için bakılıyor (Traceback / HATA:).

── 6 · PUSH KAPISINDA ÇOKLU FİRMA DENETİMİ YOKTU  [YENİ ARAÇ]
   Çoklu firma tek bir şeye dayanıyor: her sorgunun aktif firmaya
   süzülmesi. Süzgeç de damga da OTOMATİK — otomatik olan şey
   SESSİZ bozulur:

     • Yeni bir model `FirmaKapsamli` mixin'ini almazsa o tablo HER
       FİRMADA görünür. Hata vermez. A firmasının müşterisi B'nin
       ekranında çıkar; fark etmenin tek yolu birinin ekrana bakıp
       "bu benim kaydım değil" demesi.
     • Yeni bir tablo sifirla2.py'ye yazılmazsa sıfırlama reddeder.
       İki kez yaşandı (R4: kalem_karsilama · R5: firma+cari_firma).
     • `firma_atla()` süzgeci kapatır; sessizce eklenen bir tanesi
       tüm firmaların verisini tek ekrana döker.

   `firma_denetim.py` bu dördünü denetliyor (F1–F4) ve gonder.sh
   kapısına ekleniyor. Veritabanı gerekmiyor — model tanımı ve
   kaynak kod üzerinden çalışıyor.

   Denetimi boş vaat olmasın diye tersten de denedim: sifirla2'den
   bir tablo düşürdüm → F1 yakaladı; mixin'siz model ekledim → F1
   ve F2 yakaladı; fazladan bir firma_atla() koydum → F3 yakaladı.

DOSYALAR
--------
  sifirla2.py        YENİDEN YAZILDI (R2/R4 → R5) · yedek alınır
  firma_denetim.py   YENİ
  temizle.sh         yama tanıma + yedek deseni
  temizle.py         yedek deseni + güncelliğini yitirmiş liste
  gonder.sh          çıkış kodu + firma_denetim + yedek deseni

NE YAPMIYOR
-----------
  Tek seferlik göç betikleri (goc_mf1.py, karsilama_goc.py,
  yetki_goc.py, kisaltma_goc.py, cari_bag_goc.py,
  durum_tarihi_goc.py) `yama_` desenine uymadığı için temizlikte
  silinmiyor — işleri bitmiş olsa da duruyorlar. Bilerek
  dokunmadım: `goc.py` KALICI bir araç ve ikisini tek desenle
  ayırmaya kalkmak kalıcı aracı silme riski taşır. İstersen elle
  kaldırırız.

KULLANIM
--------
  python3 yama_tz1.py            # RAPOR
  python3 yama_tz1.py --uygula

  Sonra sıfırlama seçeneklerini gör (hiçbir şey silmez):
    venv/bin/python sifirla2.py
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

# ── İMZA ──
# Her dosyada TAM ve AYIRT EDİCİ bir dize aranır. Bu projede alt
# dizgi tuzağına üç kez düştüm: 'MF2' imzası MF1'in docstring'inde
# MF2'den söz edildiği için eşleşti; '_firma_kayit' MF4'ün
# '_firma_kayit_sayim'ına takıldı. İmza artık yamanın GERÇEKTEN
# eklediği benzersiz satır.
DOSYA_IMZA = {
    'sifirla2.py': 'R5: çoklu firma',
    # Tam dosya yazılanların da imzası OLMALI. İlk sürümde
    # firma_denetim.py'ye imza vermemiştim: her koşuda yeniden
    # yazılıyor, diğer dosyalar "zaten uygulanmış" diyor ve betik
    # YARIM DURUM sanıp hata veriyordu.
    'firma_denetim.py': 'ÇOKLU FİRMA DENETİMİ',
    'temizle.sh': 'TZ1',
    'temizle.py': 'TZ1',
    'gonder.sh': 'TZ1',
}
ONKOSUL = {
    'sifirla2.py': 'SILINECEK_TABLOLAR',
    'temizle.sh': 'grep -q "Zaten uygulanmış"',
    'temizle.py': "KOK.glob('*.yedek-*')",
    'gonder.sh': 'for D in js_denetim',
}

# ── TAM DOSYA YAZILANLAR ──
# sifirla2.py baştan sona değişti (üç kip, firma başına süzme, firma
# başına doğrulama). Cerrahi değiştirmelerle yapmak kırılgan olurdu.
TAM_YAZILAN = ['sifirla2.py', 'firma_denetim.py']

DEGISIKLIKLER = [
    # ══════════════════════════════════════════════════════════════
    #  temizle.sh
    # ══════════════════════════════════════════════════════════════
    ('temizle.sh', 'TZ1-a · yama durumu CIKIS KODU ile belirlenir',
     '''        CIKTI=$("$PY" "$Y" 2>&1)
        if echo "$CIKTI" | grep -q "Zaten uygulanmış"; then
            printf "   ✓ %-34s uygulanmış → silinecek\\n" "$Y"
            SILINECEK+=("$Y")
        elif echo "$CIKTI" | grep -qE "bağlantılar çalışır durumda|Üç şablon da yerinde"; then
            printf "   ✓ %-34s doğrulandı → silinecek\\n" "$Y"
            SILINECEK+=("$Y")
        elif echo "$CIKTI" | grep -q "atlandı (zaten var)"; then''',
     '''        CIKTI=$("$PY" "$Y" 2>&1); KOD=$?
        # Kaç blok "zaten var" / "zaten uygulanmış" diyor:
        ZATEN=$(echo "$CIKTI" | grep -ciE "zaten (var|uygulanmış)")

        # ══ TZ1 · KARAR ARTIK ÇIKIŞ KODUNDAN ══
        #
        # Eski sürüm tek bir cümle arıyordu: grep -q "Zaten
        # uygulanmış" (BÜYÜK Z). Yama şablonlarım o cümleyi
        # kurmuyor — "⊙ Yama MF7 zaten uygulanmış." (küçük z)
        # ya da MF1'de "⊙ İmza "MF1" zaten var — yama uygulanmış."
        # diyorlar. Sonuç ölçüldü: uygulanmış 10 yamanın HEPSİ
        # "UYGULANMAMIŞ" göründü, hiçbiri silinmedi, ekrana zaten
        # uygulanmış yamaları TEKRAR UYGULA diye yazdı ve en altta
        # "✓ Zaten temiz" dedi. İki cümle birbirini yalanlıyordu.
        #
        # Harfi düzeltmek yetmez; cümleyi kovalamak yapısal olarak
        # kırılgan. Yama betiklerinin hepsi ÇIKIŞ KODUNU doğru
        # veriyor (ölçüldü) ve iki sinyali birleştirmek durumu
        # tam ayırıyor:
        #
        #   kod 0 · zaten>0  → TAM UYGULANMIŞ      → silinebilir
        #   kod 0 · zaten=0  → hiç uygulanmamış    → KORUNUR
        #                      (rapor kipi temiz geçti, o kadar)
        #   kod≠0 · zaten>0  → YARIM / AŞILMIŞ     → KORUNUR
        #                      (bir blok imzalı, biri eşleşmiyor)
        #   kod≠0 · zaten=0  → uygulanmamış/bozuk  → KORUNUR
        #
        # Şüphe her durumda KORUMA yönünde: bu betiğin en önemli
        # kuralı "uygulanmamış yama silinmez" ve bir kez çiğnendi.
        if echo "$CIKTI" | grep -qE "bağlantılar çalışır durumda|Üç şablon da yerinde"; then
            printf "   ✓ %-34s doğrulandı → silinecek\\n" "$Y"
            SILINECEK+=("$Y")
        elif [ "$KOD" -eq 0 ] && [ "$ZATEN" -gt 0 ]; then
            printf "   ✓ %-34s uygulanmış → silinecek\\n" "$Y"
            SILINECEK+=("$Y")
        elif [ "$ZATEN" -gt 0 ]; then'''),
    ('temizle.sh', 'TZ1-a2 · asilmis etiketi yeni olcute gore',
     '''            printf "   ↷ %-34s AŞILMIŞ (sonraki yama değiştirmiş)\\n" "$Y"''',
     '''            # TZ1: "aşılmış" ile "yarım" aynı ölçüte düşüyor —
            # ikisinde de bir kısım blok imzalı, biri eşleşmiyor.
            # Hangisi olduğuna kullanıcı bakar; betik silmez.
            printf "   ↷ %-34s YARIM/AŞILMIŞ (bir blok eşleşmiyor)\\n" "$Y"'''),
    ('temizle.sh', 'TZ1-b · yedek deseni: tire VE alt cizgi',
     'YEDEKLER=(*.yedek-* templates/*.yedek-*)',
     '''# TZ1: iki desen birlikte. Eski betikler `.yedek-mf1` yazıyordu,
# yeni yama şablonum `.yedek_mf1` yazıyor (ALT ÇİZGİ). Yalnızca
# tireli desen arandığı için yenileri hiç görünmüyordu: bu klonda
# 28 tanesi birikmişti.
YEDEKLER=(*.yedek-* templates/*.yedek-* *.yedek_* templates/*.yedek_*)'''),

    # ══════════════════════════════════════════════════════════════
    #  temizle.py
    # ══════════════════════════════════════════════════════════════
    ('temizle.py', 'TZ1-c · yedek deseni: tire VE alt cizgi',
     """_yedekler = sorted(KOK.glob('*.yedek-*'))
_yedekler += sorted((KOK / 'templates').glob('*.yedek-*'))
_yedekler += sorted((KOK / 'migrations').glob('*.yedek-*'))""",
     """# TZ1: İKİ DESEN. Eski yamalar `.yedek-mf1` bırakıyordu, yeni yama
# şablonum `.yedek_mf1` bırakıyor (ALT ÇİZGİ). Tek desen arandığı
# için yeniler hiç silinmiyordu; depoya sızmıyorlar (.gitignore'da
# `*.yedek_*` var) ama diskte birikiyorlardı.
_yedekler = []
for _d in ('.', 'templates', 'migrations'):
    for _desen in ('*.yedek-*', '*.yedek_*'):
        _yedekler += sorted((KOK / _d).glob(_desen))"""),
    ('temizle.py', 'TZ1-d · yedek grubu adi iki deseni soylesin',
     "    'Yedek dosyaları (*.yedek-*)',",
     "    'Yedek dosyaları (*.yedek-* ve *.yedek_*)',"),
    ('temizle.py', 'TZ1-e · KORUNAN listesi guncellendi',
     """    ('templates/*.html (25)', 'arayüz'),
    ('static/ (4)', 'PWA ve stil'),
    ('migrations/ kaynak + 3 revizyon', 'ŞEMA GEÇMİŞİ — silinemez'),
    ('sema_ form_ sessiz_ zincir_ js_ degismezlik_denetim.py', '6 denetim aracı'),
    ('goc.py · migration_kur.py · migration_ayarla.py', 'şema göçü'),
    ('sifirla.py · sifirla_windows.py', 'veri sıfırlama'),""",
     """    # TZ1: bu liste güncelliğini yitirmişti. `sifirla.py` ve
    # `sifirla_windows.py` ARTIK YOK — adı geçen dosya korunuyor
    # sanmak, aslında var olmayan bir güvence verir. Şablon sayısı
    # da 25 değil; sayı yazmak her yeni şablonda yanlışa döner,
    # artık yazmıyoruz.
    ('templates/*.html', 'arayüz (firma_sec.html dahil)'),
    ('static/', 'PWA ve stil'),
    ('migrations/ kaynak + revizyonlar', 'ŞEMA GEÇMİŞİ — silinemez'),
    ('sema_ form_ sessiz_ zincir_ js_ akis_ degismezlik_denetim.py',
     'kalıcı denetim araçları'),
    ('firma_denetim.py', 'çoklu firma kapsam denetimi (F1–F4)'),
    ('goc.py · migration_kur.py · migration_ayarla.py', 'şema göçü'),
    ('sifirla2.py', 'veri sıfırlama (üç kip: tümü / tüm firmalar / tek firma)'),"""),

    # ══════════════════════════════════════════════════════════════
    #  gonder.sh
    # ══════════════════════════════════════════════════════════════
    ('gonder.sh', 'TZ1-f · denetim kapisina firma_denetim',
     '    for D in js_denetim form_denetim zincir_denetim akis_denetim sema_denetim; do',
     '''    # TZ1: firma_denetim eklendi. Çoklu firmanın tek dayanağı her
    # sorgunun aktif firmaya süzülmesi; süzgeç de damga da otomatik
    # ve otomatik olan şey SESSİZ bozulur. Mixin'i almayan bir
    # model tüm firmalarda görünür ve hiçbir hata vermez.
    for D in js_denetim form_denetim zincir_denetim akis_denetim sema_denetim firma_denetim; do'''),
    ('gonder.sh', 'TZ1-g · basari olcutu CIKIS KODU, kelime degil',
     '''        CIKTI=$("$PY" "$D.py" 2>&1)
        # BASARI KELIMESI ARACA GORE DEGISIYOR:
        #   js/form/zincir/akis -> "TEMİZ"
        #   sema_denetim        -> "Şema modellerle uyumlu"
        # Ilk surum yalnizca "TEMİZ" ariyordu ve sema_denetim'i
        # "calistirilamadi" saniyordu. Iki tur boyunca "sema
        # dogrulanmadi" diye uyardik; oysa dogrulanmisti.
        # Yanlis rapor, hic rapor vermemekten kotudur.
        if echo "$CIKTI" | grep -qE "TEMİZ|temiz$|uyumlu"; then
            echo "temiz"
        elif echo "$CIKTI" | grep -qE "BULGU|✗ "; then
            echo "✗ BULGU"
            HATA=1
        else
            echo "⚠ çalıştırılamadı (ortam)"
            UYARI=1
        fi''',
     '''        CIKTI=$("$PY" "$D.py" 2>&1); KOD=$?
        # ── TZ1: ESAS SİNYAL ÇIKIŞ KODU ──
        # Eski sürüm başarıyı METİNDE KELİME ARAYARAK ölçüyordu
        # ("TEMİZ|temiz$|uyumlu"). Bu tasarım bir kez çoktan
        # patladı: sema_denetim "Şema modellerle uyumlu" diyor,
        # kelime listesinde yoktu ve iki tur boyunca
        # "çalıştırılamadı" sanıldı — "şema doğrulanmadı" diye
        # uyardık, oysa doğrulanmıştı.
        #
        # Çare kelime eklemek değil: her denetim aracı çıkış kodunu
        # DOĞRU veriyor (0 temiz / 1 bulgu) — altısında da ölçüldü.
        # Metne yalnızca ÇÖKTÜ mü BULDU mu ayrımı için bakılıyor;
        # ikisi ayrı şeydir:
        #   · Bulgu     → kodda sorun var, push ENGELLENİR.
        #   · Çöktü     → ortam sorunu (veritabanı yok, modül
        #                 eksik). Engellemek yanlış olur; ama
        #                 SESSİZ de geçilmez.
        if [ "$KOD" -eq 0 ]; then
            echo "temiz"
        elif echo "$CIKTI" | grep -qE "Traceback \\(most recent|^HATA:|ModuleNotFoundError|No module named|OperationalError|could not connect"; then
            echo "⚠ çalıştırılamadı (ortam)"
            UYARI=1
        else
            echo "✗ BULGU"
            HATA=1
        fi'''),
    ('gonder.sh', 'TZ1-h · commit disi tutulan yedek deseni',
     "for DESEN in '*.yedek-*' '__pycache__/*' '__pycache__' '*.pyc' '*.db' '.env' 'venv'; do",
     """# TZ1: '*.yedek_*' eklendi (ALT ÇİZGİ). .gitignore onu zaten yok
# sayıyor, yani sızmıyordu; ama bu liste "neyi bilerek dışarıda
# tutuyoruz"un okunur kaydı ve iki desenden birini atlamış olması
# okuyana yanlış bilgi veriyordu.
for DESEN in '*.yedek-*' '*.yedek_*' '__pycache__/*' '__pycache__' '*.pyc' '*.db' '.env' 'venv'; do"""),
]

# ══════════════════════════════════════════════════════════════════════
#  TAM DOSYA İÇERİKLERİ
#
#  sifirla2.py ve firma_denetim.py PARÇA değil, TAM DOSYA. Python
#  dizgisi içine gömmek iç içe tırnak ve kaçış karakteri yığını
#  üretir, okunmaz hale gelirdi; o yüzden base64. Uygulandıktan
#  sonra diskteki dosyalar baştan sona yorumlu, okunur Python —
#  önce okumak istersen:
#      python3 yama_tz1.py --yaz-gecici   (sadece /tmp'ye yazar)
# ══════════════════════════════════════════════════════════════════════
TAM_ICERIK = {
    'sifirla2.py': (
        'IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwojIOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkAojICBNaWxlc3RvbmUgRVJQIOKA'
        'lCBTRcOHxLBDxLAgU0lGSVJMQU1BICDCtyAgUjUgICjDh09LTFUgRsSwUk1BKQojCiMg'
        'IOKUgOKUgCBSNCdURU4gRkFSS0kg4pSA4pSACiMgICAgUjQgdGVrIGZpcm1hbMSxIHNp'
        'c3RlbWUgZ8O2cmUgeWF6xLFsbcSxxZ90xLEuIMOHb2tsdSBmaXJtYSAoTUYx4oCTTUY3'
        'KQojICAgIGdlbGluY2UgaWtpIMWfZXkgb2xkdToKIwojICAgICAgMS4gYGZpcm1hYCB2'
        'ZSBgY2FyaV9maXJtYWAgdGFibG9sYXLEsSBla2xlbmRpLiDEsGtpc2kgZGUgbmUKIyAg'
        'ICAgICAgIEtPUlVOQU4gbmUgU8SwTMSwTkVDRUsgbGlzdGVzaW5kZXlkaTsga2Fwc2Ft'
        'YSBkZW5ldGltaQojICAgICAgICAgZG/En3J1IGRhdnJhbmTEsSB2ZSBiZXRpayDDh0FM'
        'ScWeTUFZSSBSRURERVRUxLAuIFNlc3NpemNlCiMgICAgICAgICB5YXLEsW0gc8SxZsSx'
        'cmxhbWEgeWFwbWFrIHllcmluZSBkdXJtYXPEsSBpeWl5ZGkuCiMKIyAgICAgIDIuIFRl'
        'ayBiaXIgInPEsWbEsXJsYSIgYXJ0xLFrIHlldG1peW9yLiDDnMOnIGF5csSxIGlzdGVr'
        'IHZhciB2ZQojICAgICAgICAgw7zDp8O8IGJhxZ9rYSDFn2V5IHlhcGFyLgojCiMgIOKV'
        'kOKVkCDDnMOHIEvEsFAg4pWQ4pWQCiMKIyAgICAxKSBUw5xNIEbEsFJNQUxBUkkgU0lG'
        'SVJMQSAgICAgICAgICAgICh2YXJzYXnEsWxhbikKIyAgICAgICAgIEhlciBmaXJtYW7E'
        'sW4gacWfbGVtIHZlcmlzaSBnaWRlcjsgRsSwUk1BIFRBTklNTEFSSSwKIyAgICAgICAg'
        'IGtpbWxpa2xlcmksIGxvZ29sYXLEsSwga2FzYS9iYW5rYSB0YW7EsW1sYXLEsSBLQUxJ'
        'Ui4KIyAgICAgICAgICJIZXBzaXlsZSB0ZW1peiBiYcWfbGFuZ8Sxw6cgeWFwYWNhxJ/E'
        'sW0iIGR1cnVtdS4KIwojICAgIDIpIFNBREVDRSBCxLBSIEbEsFJNQVlJIFNJRklSTEEg'
        'ICAgICAgLS1maXJtYT08aWR8YWQ+CiMgICAgICAgICBZYWxuxLF6Y2EgbyBmaXJtYW7E'
        'sW4gacWfbGVtIHZlcmlzaSBnaWRlci4gRMSwxJ5FUiBGxLBSTUFMQVJJTgojICAgICAg'
        'ICAgVkVSxLBTxLAgWkVSUkUgS0FEQVIgREXEnsSwxZ5NRVog4oCUIGJldGlrIGJ1bnUg'
        'c2lsbWVkZW4gw7ZuY2UKIyAgICAgICAgIHNheWFyLCBzaWxkaWt0ZW4gc29ucmEgdGVr'
        'cmFyIHNheWFyIHZlIHR1dG1henNhIEhBVEEgdmVyaXIuCiMKIyAgICAzKSBUw5xNIFZF'
        'UsSwTEVSxLAgU8SwTCAgICAgICAgICAgICAgICAgLS10dW11bnUtc2lsCiMgICAgICAg'
        'ICDEsMWfbGVtIHZlcmlzaSArIEbEsFJNQUxBUklOIEtFTkTEsFPEsC4gQmlyIGZpcm1h'
        'IGthbMSxcgojICAgICAgICAgKHZhcnNhecSxbGFuIG9sYW4pOiBzaXN0ZW0gZmlybWFz'
        'xLF6IMOnYWzEscWfbWF6IHZlIGZpcm1hCiMgICAgICAgICBraW1sacSfaSBSMidkZW4g'
        'YmVyaSBrb3J1bmFuICJmaXJtYSBiaWxnaWxlcmksIExPR08ibnVuCiMgICAgICAgICB5'
        'YcWfYWTEscSfxLEgeWVyLiBDYXJpIGthcnRsYXLEsSBrb3J1bnVyIHZlIEtBTEFOIEbE'
        'sFJNQVlBCiMgICAgICAgICBCQcSeTEFOSVIg4oCUIGJhxJ9sYW5tYXpzYSBrYXJ0IGRp'
        'c2t0ZSBkdXJ1ciBhbWEgaGnDp2JpcgojICAgICAgICAgZmlybWFkYSBnw7Zyw7xubWV6'
        'OyBzZXNzaXogdmVyaSBrYXlixLFuZGFuIGJldGVyIG9sdXIsCiMgICAgICAgICDDp8O8'
        'bmvDvCB2ZXJpICJ2YXIiIGfDtnLDvG7DvHIuCiMKIyAg4pWQ4pWQIEtPUlVOVVIgKDEw'
        'IHRhYmxvKSDilZDilZAKIyAgICBjYXJpbGVyICAgICAgIENhcmkgZmlybWEga2F5xLF0'
        'bGFyxLEuIMOWbmJlbGxlayBiYWtpeWUgYWxhbsSxIFlPSzsKIyAgICAgICAgICAgICAg'
        'ICAgIGJha2l5ZSBoYXJla2V0bGVyZGVuIGhlc2FwbGFuZMSxxJ/EsSBpw6dpbiBoYXJl'
        'a2V0bGVyaQojICAgICAgICAgICAgICAgICAgc2lsbWVrIGJha2l5ZXlpIGtlbmRpbGnE'
        'n2luZGVuIHPEsWbEsXJsYXIuCiMgICAgY2FyaV9maXJtYSAgICBIYW5naSBjYXJpIGhh'
        'bmdpIGZpcm1hZGEgZ8O2csO8bsO8ciAoTUYyKS4gU8SxZsSxcmxhbWEKIyAgICAgICAg'
        'ICAgICAgICAgIGfDtnLDvG7DvHJsw7zEn8O8IEJPWk1BWjogaGVyIGZpcm1hIGnDp2lu'
        'IGNhcmlsZXJpIHllbmlkZW4KIyAgICAgICAgICAgICAgICAgIGnFn2FyZXRsZW1layBz'
        'YWF0bGVyIGFsxLFyIHZlIGhhdGF5YSBhw6fEsWt0xLFyLgojICAgIGNhcmlfa2lzaSAg'
        'ICAgTcO8xZ90ZXJpZGVraSBracWfaWxlciAoc2F0xLFuIGFsbWEsIGxvamlzdGlrLCBt'
        'dWhhc2ViZSkKIyAgICBjYXJpX2VyaXNpbSAgIEthcGFsxLEgbcO8xZ90ZXJpbGVyZSB2'
        'ZXJpbG1pxZ8gaXN0aXNuYSBlcmnFn2ltbGVyCiMgICAgZmlybWEgICAgICAgICBGaXJt'
        'YSB0YW7EsW1sYXLEsSwga2ltbGlrLCBsb2dvLCBiZWxnZSBrb2R1IChNRjUpCiMgICAg'
        'a2FzYSAvIGJhbmthICBUYW7EsW1sYXIga29ydW51cjsgS0FTQSBCQUvEsFlFTEVSxLAg'
        'U0lGSVJMQU5JUgojICAgIGt1bGxhbmljaWxhciAgS3VsbGFuxLFjxLFsYXIsIMWfaWZy'
        'ZWxlciwgeWV0a2lsZXIKIyAgICB2ZXJpbGVyICAgICAgIExpc3RlbGVyIChjaW5zLCB5'
        'w7x6ZXksIMO2ZGVtZSwgw7xsa2UpLCBmaXJtYSBraW1sacSfaSwKIyAgICAgICAgICAg'
        'ICAgICAgIExPR08sIFNNVFAsIEtEViBvcmFubGFyxLEKIyAgICBkb3Zpel9rdXIgICAg'
        'IFRDTUIga3VyIGFyxZ9pdmkgKHllbmlkZW4gw6dla21layB1enVuIHPDvHJlcikKIwoj'
        'ICDilZDilZAgU8SwTMSwTsSwUiAoMjcgdGFibG8pIOKVkOKVkAojICAgIFTDvG0gacWf'
        'bGVtIHZlcmlzaTogc3Rvaywgc2lwYXJpxZ8gKGthbGVtIGthcsWfxLFsYW1hIGvEsXLE'
        'sWzEsW3EsSBkYWhpbCksCiMgICAgcHJvZm9ybWEsIGZhdHVyYSwgc2V2a2l5YXQsIGtl'
        'c2ltLCBtYWxpeWV0LCDDp2VrLCBrYXNhIGhhcmVrZXRsZXJpLAojICAgIGNhcmkgaGFy'
        'ZWtldGxlcmksIEtEViBpYWRlLCBrb250ZXluZXIsIHNhYml0IGdpZGVyLCBuYWtpdCBw'
        'bGFuxLEsCiMgICAgYmlsZGlyaW1sZXIsIGRlbmV0aW0gaXppLgojCiMgIOKVkOKVkCBU'
        'QU0gS0FQU0FNQSBERU5FVMSwTcSwIOKVkOKVkAojICAgIEhlciB0YWJsbyB5YSBLT1JV'
        'TkFOIHlhIFPEsEzEsE5FQ0VLIGxpc3Rlc2luZGUgb2xtYWzEsS4gQmlyaSBpa2lzaW5k'
        'ZQojICAgIGRlIHlva3NhIGJldGlrIMOHQUxJxZ5NQVlJIFJFRERFREVSIOKAlCBpbGVy'
        'aWRlIG1vZGVsIGVrbGVuZGnEn2luZGUgYnUKIyAgICBkb3N5YXnEsSBnw7xuY2VsbGVt'
        'ZXlpIHVudXRtYWsgc2Vzc2l6IGthbMSxbnTEsSBixLFyYWttYXPEsW4uCiMKIyAgICBS'
        'NSBFSyBERU5FVMSwTcSwOiB0ZWsgZmlybWEga2lwaW5kZSwgc2lsaW5lY2VrIGhlciB0'
        'YWJsb2RhCiMgICAgYGZpcm1hX2lkYCBzw7x0dW51IE9MTUFMSS4gT2xtYXlhbiBiaXIg'
        'dGFibG8gImJpciBmaXJtYXlhIGFpdCIKIyAgICBzYXnEsWxhbWF6OyBvIHRhYmxveXUg'
        'dMO8bWRlbiBzaWxtZWsgZGnEn2VyIGZpcm1hbGFyxLFuIHZlcmlzaW5pCiMgICAgZ8O2'
        'dMO8csO8cmTDvCwgYsSxcmFrbWFrIGRhIGFydMSxayBrYXnEsXQgYsSxcmFrxLFyZMSx'
        'LiDEsGtpc2kgZGUgeWFubMSxxZ8sCiMgICAgbyB5w7x6ZGVuIG8ga2lwdGUgw6dhbMSx'
        'xZ9tYXnEsSByZWRkZWRpeW9ydXouCiMKIyAg4pWQ4pWQIEfDnFZFTkzEsEsg4pWQ4pWQ'
        'CiMgICAg4oCiIC0tb25heWxhIE9MTUFEQU4gSMSww4dCxLBSIMWeRVkgU8SwTE1FWjsg'
        'eWFsbsSxemNhIHJhcG9yIHZlcmlyLgojICAgIOKAoiBTaWxtZWRlbiDDtm5jZSBwZ19k'
        'dW1wIHllZGXEn2kgYWzEsXI7IHllZGVrIGJhxZ9hcsSxc8SxenNhIMSwUFRBTC4KIyAg'
        'ICDigKIgVGVrIHRyYW5zYWN0aW9uOiBiaXIgdGFibG8gaGF0YSB2ZXJpcnNlIEjEsMOH'
        'QsSwUsSwIHNpbGlubWV6LgojICAgIOKAoiBZYWJhbmPEsSBhbmFodGFyIHPEsXJhc8Sx'
        'bmEgZ8O2cmUgc2lsZXIgKMOnb2N1ayB0YWJsbyDDtm5jZSkuCiMgICAg4oCiIFNpbG1l'
        'IHNvbnJhc8SxIERPS1VOVUxNQVlBTiBmaXJtYWxhcsSxbiBzYXnEsWxhcsSxIGRlxJ9p'
        'xZ9tZWRpIG1pCiMgICAgICB2ZSBrb3J1bmFuIHRhYmxvbGFyIHllcmluZGUgbWkgZGl5'
        'ZSBrb250cm9sIGVkZXIuCiMgICAg4oCiIERpemlsZXIgWUFMTklaQ0EgdGFibG8gdGFt'
        'YW1lbiBib8WfYWxkxLHEn8SxbmRhIHPEsWbEsXJsYW7EsXIuCiMgICAgICBUZWsgZmly'
        'bWEga2lwaW5kZSBzxLFmxLFybGFubWF6OiBiYcWfa2EgZmlybWFuxLFuIDUwMCdlIGdl'
        'bG1pxZ8KIyAgICAgIGthecSxdGxhcsSxIGR1cnVya2VuIHNheWFjxLEgMSdlIMOnZWtt'
        'ZWssIGlsZXJsZXllbiBla2xlbWVsZXJkZQojICAgICAgYmlyaW5jaWwgYW5haHRhciDD'
        'p2FrxLHFn21hc8SxIMO8cmV0aXJkaS4KIwojICBLVUxMQU5JTSAocHJvamUgZGl6aW5p'
        'bmRlKToKIyAgICAgIHZlbnYvYmluL3B5dGhvbiBzaWZpcmxhMi5weSAgICAgICAgICAg'
        'ICAgICAgICAgICAgIyBSQVBPUgojICAgICAgdmVudi9iaW4vcHl0aG9uIHNpZmlybGEy'
        'LnB5IC0tZmlybWFsYXIgICAgICAgICAgICAjIGZpcm1hIGxpc3Rlc2kKIyAgICAgIHZl'
        'bnYvYmluL3B5dGhvbiBzaWZpcmxhMi5weSAtLWZpcm1hPTIgICAgICAgICAgICAgIyBS'
        'QVBPUiwgdGVrIGZpcm1hCiMKIyAgICAgIHZlbnYvYmluL3B5dGhvbiBzaWZpcmxhMi5w'
        'eSAtLW9uYXlsYSAgICAgICAgICAgICAgIyBUw5xNIEbEsFJNQUxBUgojICAgICAgdmVu'
        'di9iaW4vcHl0aG9uIHNpZmlybGEyLnB5IC0tZmlybWE9MiAtLW9uYXlsYSAgICAjIFNB'
        'REVDRSBvIGZpcm1hCiMgICAgICB2ZW52L2Jpbi9weXRob24gc2lmaXJsYTIucHkgLS10'
        'dW11bnUtc2lsIC0tb25heWxhICMgVMOcTSBWRVLEsExFUgojCiMgIOKaoCBHRVLEsCBB'
        'TElOQU1BWi4KIyDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZAKaW1wb3J0IG9zCmltcG9ydCBzdWJwcm9jZXNzCmltcG9y'
        'dCBzeXMKZnJvbSBkYXRldGltZSBpbXBvcnQgZGF0ZXRpbWUKZnJvbSBwYXRobGliIGlt'
        'cG9ydCBQYXRoCmZyb20gdXJsbGliLnBhcnNlIGltcG9ydCB1cmxwYXJzZQoKZnJvbSBk'
        'b3RlbnYgaW1wb3J0IGxvYWRfZG90ZW52CmZyb20gc3FsYWxjaGVteSBpbXBvcnQgY3Jl'
        'YXRlX2VuZ2luZSwgaW5zcGVjdCwgdGV4dAoKbG9hZF9kb3RlbnYoKQoKT05BWSA9ICct'
        'LW9uYXlsYScgaW4gc3lzLmFyZ3YKVFVNVU5VX1NJTCA9ICctLXR1bXVudS1zaWwnIGlu'
        'IHN5cy5hcmd2CkZJUk1BX0xJU1RFU0kgPSAnLS1maXJtYWxhcicgaW4gc3lzLmFyZ3YK'
        'VEVLX0ZJUk1BX0FSRyA9IE5vbmUKZm9yIF9hIGluIHN5cy5hcmd2WzE6XToKICAgIGlm'
        'IF9hLnN0YXJ0c3dpdGgoJy0tZmlybWE9Jyk6CiAgICAgICAgVEVLX0ZJUk1BX0FSRyA9'
        'IF9hLnNwbGl0KCc9JywgMSlbMV0uc3RyaXAoKQoKIyDEsGtpIGtpcCBiaXJiaXJpbmkg'
        'ZMSxxZ9sYXIuICJUw7xtIHZlcmlsZXJpIHNpbCBhbWEgeWFsbsSxemNhIMWfdQojIGZp'
        'cm1hZGEiIGRpeWUgYmlyIMWfZXkgeW9rOyBzZXNzaXpjZSBiaXJpbmkgc2XDp21layB5'
        'ZXJpbmUgc29ydXlvcnV6LgppZiBUVU1VTlVfU0lMIGFuZCBURUtfRklSTUFfQVJHOgog'
        'ICAgcHJpbnQoIkhBVEE6IC0tdHVtdW51LXNpbCBpbGUgLS1maXJtYT0gYmlybGlrdGUg'
        'a3VsbGFuxLFsYW1hei4iKQogICAgcHJpbnQoIiAgLS10dW11bnUtc2lsICBiw7x0w7xu'
        'IHNpc3RlbWkgc2lsZXIgKGZpcm1hbGFyIGRhaGlsKSIpCiAgICBwcmludCgiICAtLWZp'
        'cm1hPU4gICAgIHlhbG7EsXpjYSBvIGZpcm1hbsSxbiBpxZ9sZW0gdmVyaXNpbmkgc2ls'
        'ZXIiKQogICAgc3lzLmV4aXQoMSkKClZUX1VSTCA9IG9zLmVudmlyb24uZ2V0KCdEQVRB'
        'QkFTRV9VUkwnKQppZiBub3QgVlRfVVJMOgogICAgcHJpbnQoIkhBVEE6IERBVEFCQVNF'
        'X1VSTCBidWx1bmFtYWTEsSAoLmVudiBva3VuYW1hZMSxKS4iKQogICAgcHJpbnQoIiAg'
        'QWRyZXMgb2xtYWRhbiB5YW5sxLHFnyB2ZXJpdGFiYW7EsW5hIGJhxJ9sYW5hYmlsaXJk'
        'aW0uIikKICAgIHN5cy5leGl0KDEpCgojIOKUgOKUgCBTaWxpbmVjZWsgdGFibG9sYXIg'
        '4pSA4pSACiMKIyBTSVJBIEVMTEUgVFVUVUxNVVlPUiDigJQgYcWfYcSfxLFkYSBtb2Rl'
        'bGluIHRvcG9sb2ppayBzxLFyYXPEsW5kYW4KIyBUw5xSRVTEsEzEsFlPUi4gQnUgbGlz'
        'dGUgeWFsbsSxemNhICJoYW5naSB0YWJsb2xhciBzaWxpbmVjZWsiaSBzw7Z5bGVyLgoj'
        'CiMgTkVERU46IGVsbGUgc8SxcmFsYW5hbiBzw7xyw7xtIMO8cmV0aW1kZSBwYXRsYWTE'
        'sS4gYGtvbnRleW5lcmAKIyB0YWJsb3N1IGBwcm9mb3JtYWB5YSB5YWJhbmPEsSBhbmFo'
        'dGFybGEgYmHEn2zEsXlkxLEgYW1hIGxpc3RlZGUKIyBwcm9mb3JtYWRhbiBTT05SQSBn'
        'ZWxpeW9yZHU6CiMgICAgIEZvcmVpZ25LZXlWaW9sYXRpb246ICJrb250ZXluZXJfcHJv'
        'Zm9ybWFfaWRfZmtleSIKIyBUZWsgdHJhbnNhY3Rpb24gc2F5ZXNpbmRlIGhpw6diaXIg'
        'xZ9leSBzaWxpbm1lZGksIGFtYSBlbGxlCiMgc8SxcmFsYW1hIGhlciB5ZW5pIHlhYmFu'
        'Y8SxIGFuYWh0YXJkYSBheW7EsSBoYXRhecSxIMO8cmV0aXIuCiMgU1FMQWxjaGVteSBi'
        'YcSfxLFtbMSxbMSxayBzxLFyYXPEsW7EsSB6YXRlbiBiaWxpeW9yOyBvbmRhbiBhbGFs'
        'xLFtLgpTSUxJTkVDRUtfVEFCTE9MQVIgPSBbCiAgICAjIERlbmV0aW0gaXppCiAgICAn'
        'YXVkaXRfbG9nJywKICAgICMgQmlsZGlyaW1sZXIgKEJMMSkg4oCUIDIxLjA5J2RhIGVr'
        'bGVuZGk7IGVrc2lra2VuIGthcHNhbWEgZGVuZXRpbWkKICAgICMgYmV0acSfaSDDp2Fs'
        'xLHFn3TEsXJtYXnEsSBSRURERUTEsFlPUkRVLgogICAgJ2JpbGRpcmltbGVyJywKICAg'
        'ICMgw4dlawogICAgJ2Nla19oYXJla2V0JywgJ2NlaycsCiAgICAjIEtlc2ltCiAgICAn'
        'a2VzaW1fZGV0YXknLCAna2VzaW0nLAogICAgIyBTYXTEscWfIHppbmNpcmkKICAgICdz'
        'YXRpc19rYXlkaScsICdyZXplcnZhc3lvbicsCiAgICAncHJvZm9ybWFfa2FsZW0nLCAn'
        'cHJvZm9ybWEnLAogICAgIyBSNDogRjEgaWxlIGdlbGVuIGthbGVtIGtheW5hayBraXJp'
        'bGltaSAoc3Rvay91cmV0aW0vZGlzIGFsaW0pLgogICAgIyBCZXRpZ2UgeWF6aWxtYWRp'
        'Z2kgaWNpbiBrYXBzYW1hIGRlbmV0aW1pIGNhbGlzbWF5aSBSRURERURJWU9SRFUuCiAg'
        'ICAna2FsZW1fa2Fyc2lsYW1hJywKICAgICdzaXBhcmlzX2thbGVtJywKICAgICdmYXR1'
        'cmFsYXInLAogICAgJ2tvbnRleW5lcicsCiAgICAnc2V2a2l5YXRfa2F5aXQnLAogICAg'
        'J3NpcGFyaXNfa2F5aXQnLAogICAgIyBLRFYgaWFkZQogICAgJ2tkdl9pYWRlX2Rvc3lh'
        'JywKICAgICMgTWFsaXlldAogICAgJ21hbGl5ZXRsZXInLAogICAgIyBTdG9rCiAgICAn'
        'c3Rva19jaWtpcycsICdibG9rX3N0b2snLCAncGxha2Ffc3RvaycsICdlYmF0bGlfc3Rv'
        'aycsCiAgICAjIE5ha2l0IGFrxLHFn8SxCiAgICAnbmFraXRfcGxhbicsICdzYWJpdF9n'
        'aWRlcicsCiAgICAjIENSTSDigJQgY2FyaV9raXNpIHZlIGNhcmlfZXJpc2ltIEtPUlVO'
        'VVlPUiAoYcWfYcSfxLFkYSksIHlhbG7EsXpjYQogICAgIyBha3Rpdml0ZSBzaWxpbml5'
        'b3IuCiAgICAnY2FyaV9ha3Rpdml0ZScsCiAgICAjIEZpbmFucyDigJQgY2FyaWxlciwg'
        'S0FTQSB2ZSBCQU5LQSBrb3J1bnV5b3I7IHlhbG7EsXpjYQogICAgIyBoYXJla2V0bGVy'
        'aSBzaWxpbml5b3IuCiAgICAna2FzYV9oYXJla2V0JywgJ2NhcmlfaGFyZWtldCcsCl0K'
        'CktPUlVOQU4gPSB7CiAgICAnY2FyaWxlcic6ICdDYXJpIGZpcm1hIGthecSxdGxhcsSx'
        'IChoYXJla2V0bGVyaSBzaWxpbmlyKScsCiAgICAjIOKUgOKUgCDDh09LTFUgRsSwUk1B'
        'IChSNSkg4pSA4pSACiAgICAjCiAgICAjICAgZmlybWEgICAgICAgRmlybWEgdGFuxLFt'
        'bGFyxLE6IMO8bnZhbiwgdmVyZ2kgbm8sIExPR08sIGJlbGdlIGtvZHUuCiAgICAjICAg'
        'ICAgICAgICAgICAgTUY1J3RlbiBiZXJpIGZpcm1hIEvEsE1MxLDEnsSwIGJ1cmFkYSB5'
        'YcWfxLF5b3I7IHNpbG1lawogICAgIyAgICAgICAgICAgICAgIFIyJ25pbiAiZmlybWEg'
        'YmlsZ2lsZXJpIHZlIExPR08ga29ydW51ciIgc8O2esO8bsO8CiAgICAjICAgICAgICAg'
        'ICAgICAgYm96YXJkxLEuIC0tdHVtdW51LXNpbCBraXBpbmRlIGJpcmkgaGFyacOnIHNp'
        'bGluaXIuCiAgICAjCiAgICAjICAgY2FyaV9maXJtYSAgSGFuZ2kgY2FyaSBoYW5naSBm'
        'aXJtYWRhIEfDllLDnE7DnFIgKE1GMikuIFPEsWbEsXJsYW1hCiAgICAjICAgICAgICAg'
        'ICAgICAgacWfbGVtIHZlcmlzaW5pIHNpbGVyLCBnw7Zyw7xuw7xybMO8xJ/DvCBCT1pN'
        'QVouIEhlcgogICAgIyAgICAgICAgICAgICAgIGZpcm1hZGEgY2FyaWxlcmkgeWVuaWRl'
        'biBpxZ9hcmV0bGVtZWsgc2FhdGxlciBhbMSxcgogICAgIyAgICAgICAgICAgICAgIHZl'
        'IGFzxLFsIHJpc2sgxZ91OiBpxZ9hcmV0bGVubWV5ZW4gY2FyaSBkaXNrdGUgZHVydXIK'
        'ICAgICMgICAgICAgICAgICAgICBhbWEgZWtyYW5kYSB5b2sg4oCUIGt1bGxhbsSxY8Sx'
        'ICJ2ZXJpIGdpdG1pxZ8iIHNhbsSxci4KICAgICdmaXJtYSc6ICdGaXJtYSB0YW7EsW1s'
        'YXLEsSwga2ltbGlrLCBMT0dPLCBiZWxnZSBrb2R1JywKICAgICdjYXJpX2Zpcm1hJzog'
        'J0NhcmkgZ8O2csO8bsO8cmzDvGsgw7x5ZWxpa2xlcmkgKGhhbmdpIGNhcmkgaGFuZ2kg'
        'ZmlybWFkYSknLAogICAgIyBLQVNBL0JBTktBIEtPUlVOVVlPUiAoS0IxKS4KICAgICMg'
        'RXNraWRlbiBzaWxpbml5b3JkdTsgaGVyIHPEsWbEsXJsYW1hZGEgOCBrYXNhIHllbmlk'
        'ZW4KICAgICMgdGFuxLFtbGFubWFrIHpvcnVuZGEga2FsxLF5b3JkdSB2ZSBrYXNhIHlv'
        'a2tlbiDDtmRlbWUKICAgICMga2F5ZGVkaWxlbWl5b3JkdS4gVGFuxLFtbGFyIGthbMSx'
        'Y8SxZMSxciwgcGFyYSBoYXJla2V0bGVyaSBkZcSfaWwuCiAgICAjCiAgICAjIEJBS8Sw'
        'WUVMRVIgU0lGSVJMQU5JUiAoYcWfYcSfxLFkYSk6IGhhcmVrZXRsZXIgc2lsaW5pcCBi'
        'YWtpeWUKICAgICMga2Fsc2F5ZMSxICJoYXlhbGV0IHBhcmEiIG9sdXJkdSDigJQgRDEg'
        'ZGXEn2nFn21lemxpxJ9pIGlobGFsCiAgICAjIGVkaWxpcmRpLiBBw6fEsWzEscWfIGJh'
        'a2l5ZWxlcmluaSBrdWxsYW7EsWPEsSB5ZW5pZGVuIGdpcmVyLgogICAgJ2thc2EnOiAn'
        'S2FzYS9iYW5rYSB0YW7EsW1sYXLEsSAoQkFLxLBZRUxFUiBTSUZJUkxBTklSKScsCiAg'
        'ICAnYmFua2EnOiAnQmFua2EgaGVzYXAgdGFuxLFtbGFyxLEgKGJha2l5ZSB0dXRtYXop'
        'JywKICAgICdrdWxsYW5pY2lsYXInOiAnS3VsbGFuxLFjxLFsYXIsIMWfaWZyZWxlciwg'
        'eWV0a2lsZXInLAogICAgJ3ZlcmlsZXInOiAnTGlzdGVsZXIsIGZpcm1hIGJpbGdpc2ks'
        'IExPR08sIFNNVFAsIEtEViBheWFybGFyxLEnLAogICAgJ2Rvdml6X2t1cic6ICdUQ01C'
        'IGt1ciBhcsWfaXZpJywKCiAgICAjIOKUgOKUgCBDUk0gKFIzKSDilIDilIAKICAgICMg'
        'QnUgaWtpc2kgQ0FSxLAgS0FZRElOSU4gUEFSw4dBU0ksIGnFn2xlbSB2ZXJpc2kgZGXE'
        'n2lsOgogICAgIwogICAgIyAgIGNhcmlfa2lzaSAgIE3DvMWfdGVyaWRla2kga2nFn2ls'
        'ZXIg4oCUIHNhdMSxbiBhbG1hY8SxLCBsb2ppc3RpaywKICAgICMgICAgICAgICAgICAg'
        'ICBtdWhhc2ViZS4gQ2FyaSBrYXJ0xLFuxLEga29ydXl1cCBracWfaWxlcmluaSBzaWxt'
        'ZWssCiAgICAjICAgICAgICAgICAgICAga2FydMSxbiB5YXLEsXPEsW7EsSBhdG1hayBv'
        'bHVyZHUuIMOcc3RlbGlrIGfDtsOnIGJ1bmxhcsSxCiAgICAjICAgICAgICAgICAgICAg'
        'ZXNraSBgeWV0a2lsaWAgYWxhbsSxbmRhbiB0YcWfxLFkxLE7IHNpbGluaXJzZSBvIGJp'
        'bGdpCiAgICAjICAgICAgICAgICAgICAgYmlyIGRhaGEgZ2VyaSBnZWxtZXouCiAgICAj'
        'CiAgICAjICAgY2FyaV9lcmlzaW0gS2FwYWzEsSBtw7zFn3RlcmlsZXJlIHZlcmlsbWnF'
        'nyBpc3Rpc25hIGVyacWfaW1sZXIuCiAgICAjICAgICAgICAgICAgICAgU2lsaW5pcnNl'
        'IHNhdMSxxZ8gZWtpYmkgc2Vzc2l6Y2UgbcO8xZ90ZXJpIGtheWJlZGVyOwogICAgIyAg'
        'ICAgICAgICAgICAgIGtpbXNlICJlcmnFn2ltaW0ga2Fsa3TEsSIgZGl5ZSB1eWFyxLEg'
        'YWxtYXouCiAgICAjCiAgICAjIGNhcmlfYWt0aXZpdGUgaXNlIFPEsEzEsE7EsFI6IHRl'
        'bWFzIGdlw6dtacWfaSBpxZ9sZW0gdmVyaXNpZGlyIHZlCiAgICAjIHPEsWbEsXJsYW5h'
        'biBzaXBhcmnFn2xlcmUvdGVrbGlmbGVyZSBhdMSxZnRhIGJ1bHVudXIuIFR1dG1haywK'
        'ICAgICMgb2xtYXlhbiBiZWxnZWxlcmRlbiBzw7Z6IGVkZW4gbm90bGFyIGLEsXJha8Sx'
        'cmTEsS4KICAgICdjYXJpX2tpc2knOiAnTcO8xZ90ZXJpIGtpxZ9pbGVyaSAoc2F0xLFu'
        'IGFsbWEsIGxvamlzdGlrLCBtdWhhc2ViZSknLAogICAgJ2NhcmlfZXJpc2ltJzogJ0th'
        'cGFsxLEgbcO8xZ90ZXJpbGVyZSB2ZXJpbG1pxZ8gaXN0aXNuYSBlcmnFn2ltbGVyJywK'
        'fQoKIyBUYW1zYXnEsSBiaXJpbmNpbCBhbmFodGFybMSxIHRhYmxvbGFyIOKAlCBkaXpp'
        'bGVyaSAxJ2Ugw6dla2lsaXIuCiMKIyBLQVNBL0JBTktBIEJVUkFEQSBZT0sgKEtCMSk6'
        'IHRhYmxvbGFyIGFydGlrIHNpbGlubWl5b3IsIGlkCiMgc2F5YWNpbmkgc2lmaXJsYW1h'
        'ayBNRVZDVVQga2F5aXRsYXJsYSBjYWtpc2FuIGlkIHVyZXRpcmRpLgojCiMgUjQ6IGJp'
        'bGRpcmltbGVyIC8gcHJvZm9ybWFfa2FsZW0gLyBzaXBhcmlzX2thbGVtIGRlIHRhbXNh'
        'eWkgaWQKIyB0YXNpeW9yIHZlIHNpbGluaXlvci4gRGl6aSBzaWZpcmxhbm1henNhICJ0'
        'ZW1peiBiYXNsYW5naWMidGEgaWxrCiMga2FsZW0gaWQnc2kgMSBkZWdpbCwgZXNraSBz'
        'YXlhY2luIGthbGRpZ2kgeWVyZGVuIGRldmFtIGVkZXJkaS4KIyBrYWxlbV9rYXJzaWxh'
        'bWEgTUVUSU4gaWQga3VsbGFuaXlvciAoS1JTLi4uKSwgZGl6aXNpIHlvay4KIwojIFI1'
        'OiBidSBsaXN0ZSBZQUxOSVpDQSB0YWJsbyB0YW1hbWVuIGJvc2FsZGlnaW5kYSB1eWd1'
        'bGFuaXIKIyAoYXNhZ2lkYWtpIGBkaXppbGVyaV9zaWZpcmxhYCBjYWdyaXNpbmEgYmFr'
        'KS4gVGVrIGZpcm1hIGtpcGluZGUKIyB0YWJsbyBib3NhbG1peW9yOyBzYXlhY2kgMSdl'
        'IGNla21layBiYXNrYSBmaXJtYW5pbiBtZXZjdXQKIyBpZCdsZXJpeWxlIGNha2lzaXJk'
        'aS4KRElaSV9TSUZJUkxBID0gWydrYXNhX2hhcmVrZXQnLCAna2VzaW1fZGV0YXknLAog'
        'ICAgICAgICAgICAgICAgJ2Nla19oYXJla2V0JywgJ2F1ZGl0X2xvZycsICdrb250ZXlu'
        'ZXInLCAnY2FyaV9ha3Rpdml0ZScsCiAgICAgICAgICAgICAgICAnYmlsZGlyaW1sZXIn'
        'LCAncHJvZm9ybWFfa2FsZW0nLCAnc2lwYXJpc19rYWxlbSddCgojIOKUgOKUgCBTxLBM'
        'TUUgU0lSQVNJOiBtb2RlbGluIHRvcG9sb2ppayBzxLFyYXPEsW5kYW4sIFRFUlMg4pSA'
        '4pSACiMgbWV0YWRhdGEuc29ydGVkX3RhYmxlcyBlYmV2ZXluZGVuIMOnb2N1xJ9hIHPE'
        'sXJhbMSxOyBzaWxtZWsgacOnaW4KIyB0ZXJzaSBnZXJla2l5b3IgKMOnb2N1ayDDtm5j'
        'ZSkuCnRyeToKICAgIG9zLmVudmlyb24uc2V0ZGVmYXVsdCgnTUlMRVNUT05FX0FDSUxJ'
        'U19BVExBJywgJzEnKQogICAgc3lzLnBhdGguaW5zZXJ0KDAsIHN0cihQYXRoKCcuJyku'
        'cmVzb2x2ZSgpKSkKICAgIGltcG9ydCBmbGFza19hcHAgYXMgX2ZhICAjIG5vcWE6IEY0'
        'MDEKICAgIGZyb20gbW9kZWxzIGltcG9ydCBkYiBhcyBfZGIKICAgIF9zaXJhbGkgPSBb'
        'dC5uYW1lIGZvciB0IGluIF9kYi5tZXRhZGF0YS5zb3J0ZWRfdGFibGVzXQogICAgX3Np'
        'cmFsaS5yZXZlcnNlKCkKICAgIF9oZWRlZiA9IHNldChTSUxJTkVDRUtfVEFCTE9MQVIp'
        'CiAgICAjIE1vZGVsZGUgYmlsaW5lbiB0YWJsb2xhciBkb8SfcnUgc8SxcmF5bGE7IG1v'
        'ZGVsZGUgb2xtYXlhbmxhcgogICAgIyAodmFyc2EpIHNvbmEuCiAgICBTSUxfU0lSQVNJ'
        'ID0gW3QgZm9yIHQgaW4gX3NpcmFsaSBpZiB0IGluIF9oZWRlZl0KICAgIFNJTF9TSVJB'
        'U0kgKz0gW3QgZm9yIHQgaW4gU0lMSU5FQ0VLX1RBQkxPTEFSIGlmIHQgbm90IGluIF9z'
        'aXJhbGldCiAgICBpZiBzZXQoU0lMX1NJUkFTSSkgIT0gX2hlZGVmOgogICAgICAgIHBy'
        'aW50KCIg4pyXIFPEsXJhIHTDvHJldGlsZW1lZGkg4oCUIERPU1lBWUEgRE9LVU5VTE1B'
        'REkuIikKICAgICAgICBzeXMuZXhpdCgxKQogICAgIyBNb2RlbGRla2kgc8O8dHVubGFy'
        'IOKAlCBmaXJtYSBrYXBzYW3EsSBkZW5ldGltaSBpw6dpbi4KICAgIE1PREVMX1NVVFVO'
        'ID0ge3QubmFtZToge2MubmFtZSBmb3IgYyBpbiB0LmN9CiAgICAgICAgICAgICAgICAg'
        'ICBmb3IgdCBpbiBfZGIubWV0YWRhdGEuc29ydGVkX3RhYmxlc30KICAgICMgLS10dW11'
        'bnUtc2lsIGtpcGluZGUgZmlybWEgU8SwTMSwTsSwUktFTiBvbmEgYmHEn2zEsSBLT1JV'
        'TkFOCiAgICAjIHRhYmxvbGFyZGFuIGRhIChrYXNhLCBiYW5rYSwgdmVyaWxlcikgbyBm'
        'aXJtYW7EsW4gc2F0xLFybGFyxLEKICAgICMgZ2l0bWVsaTsgeW9rc2EgeWFiYW5jxLEg'
        'YW5haHRhciBrxLFyxLFsxLFyLgogICAgRklSTUFfQkFHTEkgPSBbdC5uYW1lIGZvciB0'
        'IGluIHJldmVyc2VkKF9kYi5tZXRhZGF0YS5zb3J0ZWRfdGFibGVzKQogICAgICAgICAg'
        'ICAgICAgICAgaWYgJ2Zpcm1hX2lkJyBpbiBNT0RFTF9TVVRVTi5nZXQodC5uYW1lLCBz'
        'ZXQoKSkKICAgICAgICAgICAgICAgICAgIGFuZCB0Lm5hbWUgbm90IGluICgnZmlybWEn'
        'LCAnYXVkaXRfbG9nJyldCmV4Y2VwdCBTeXN0ZW1FeGl0OgogICAgcmFpc2UKZXhjZXB0'
        'IEV4Y2VwdGlvbiBhcyBfZToKICAgIHByaW50KGYiIOKclyBTaWxtZSBzxLFyYXPEsSBt'
        'b2RlbGRlbiB0w7xyZXRpbGVtZWRpOiB7X2V9IikKICAgIHByaW50KCIgICBFbGxlIHPE'
        'sXJhbGFtYXlhIGTDvMWfbWVrIHlhYmFuY8SxIGFuYWh0YXIgaGF0YXPEsSByaXNraSIp'
        'CiAgICBwcmludCgiICAgdGHFn8Sxcjsgw6dhbMSxxZ9tYXnEsSByZWRkZWRpeW9ydW0u'
        'IikKICAgIHN5cy5leGl0KDEpCgojIFRlayBmaXJtYSBraXBpbmRlIHPDvHrDvGxlbWV5'
        'ZW4gdGFibG8gdmFyIG3EsT8KRklSTUFTSVpfU0lMSU5FQ0VLID0gW3QgZm9yIHQgaW4g'
        'U0lMSU5FQ0VLX1RBQkxPTEFSCiAgICAgICAgICAgICAgICAgICAgICBpZiAnZmlybWFf'
        'aWQnIG5vdCBpbiBNT0RFTF9TVVRVTi5nZXQodCwgc2V0KCkpXQoKbW90b3IgPSBjcmVh'
        'dGVfZW5naW5lKFZUX1VSTCkKZGVuZXRjaSA9IGluc3BlY3QobW90b3IpCm1ldmN1dCA9'
        'IHNldChkZW5ldGNpLmdldF90YWJsZV9uYW1lcygpKQpwZyA9IG1vdG9yLmRpYWxlY3Qu'
        'bmFtZSBpbiAoJ3Bvc3RncmVzcWwnLCAncG9zdGdyZXMnKQoKCmRlZiB0cihuKToKICAg'
        'IHJldHVybiBmJ3tuOix9Jy5yZXBsYWNlKCcsJywgJy4nKQoKCiMg4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCiMgIFlB'
        'UkRJTUNJTEFSCiMg4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCmRlZiBmaXJtYWxhcmlfb2t1KGIpOgogICAgaWYgJ2Zp'
        'cm1hJyBub3QgaW4gbWV2Y3V0OgogICAgICAgIHJldHVybiBbXQogICAgc2F0aXJsYXIg'
        'PSBiLmV4ZWN1dGUodGV4dCgKICAgICAgICAnU0VMRUNUIGlkLCBhZCwgdW52YW4sIGJl'
        'bGdlX2tvZHUsIHZhcnNheWlsYW4sIGFrdGlmICcKICAgICAgICAnRlJPTSBmaXJtYSBP'
        'UkRFUiBCWSBpZCcpKS5mZXRjaGFsbCgpCiAgICByZXR1cm4gW3snaWQnOiByWzBdLCAn'
        'YWQnOiByWzFdIG9yICcnLCAndW52YW4nOiByWzJdIG9yICcnLAogICAgICAgICAgICAg'
        'J2tvZCc6IHJbM10gb3IgJycsICd2YXJzYXlpbGFuJzogYm9vbChyWzRdKSwgJ2FrdGlm'
        'JzogYm9vbChyWzVdKX0KICAgICAgICAgICAgZm9yIHIgaW4gc2F0aXJsYXJdCgoKZGVm'
        'IGZpcm1hX3NheWltKGIsIGZpZCk6CiAgICAiIiJCaXIgZmlybWFuxLFuIHNpbGluZWNl'
        'ayB0YWJsb2xhcmRha2kga2F5xLF0IHNhecSxc8SxLiIiIgogICAgZCwgdG9wbGFtID0g'
        'e30sIDAKICAgIGZvciB0IGluIFNJTF9TSVJBU0k6CiAgICAgICAgaWYgdCBub3QgaW4g'
        'bWV2Y3V0IG9yICdmaXJtYV9pZCcgbm90IGluIE1PREVMX1NVVFVOLmdldCh0LCBzZXQo'
        'KSk6CiAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgbiA9IGIuZXhlY3V0ZSh0ZXh0'
        'KGYnU0VMRUNUIENPVU5UKCopIEZST00gInt0fSIgV0hFUkUgZmlybWFfaWQgPSA6Zicp'
        'LAogICAgICAgICAgICAgICAgICAgICAgeydmJzogZmlkfSkuc2NhbGFyKCkgb3IgMAog'
        'ICAgICAgIGRbdF0gPSBuCiAgICAgICAgdG9wbGFtICs9IG4KICAgIHJldHVybiBkLCB0'
        'b3BsYW0KCgpkZWYgdGFibG9fc2F5aW0oYiwgdGFibG9sYXIpOgogICAgZCA9IHt9CiAg'
        'ICBmb3IgdCBpbiB0YWJsb2xhcjoKICAgICAgICBpZiB0IGluIG1ldmN1dDoKICAgICAg'
        'ICAgICAgZFt0XSA9IGIuZXhlY3V0ZSh0ZXh0KGYnU0VMRUNUIENPVU5UKCopIEZST00g'
        'Int0fSInKSkuc2NhbGFyKCkgb3IgMAogICAgcmV0dXJuIGQKCgpkZWYgZGl6aWxlcmlf'
        'c2lmaXJsYShiKToKICAgICIiIllBTE5JWkNBIHRhYmxvIHRhbWFtZW4gYm/Fn2FsZMSx'
        'xJ/EsW5kYSDDp2HEn3LEsWzEsXIuIiIiCiAgICBpZiBub3QgcGc6CiAgICAgICAgcmV0'
        'dXJuCiAgICBmb3IgdCBpbiBESVpJX1NJRklSTEE6CiAgICAgICAgaWYgdCBpbiBtZXZj'
        'dXQ6CiAgICAgICAgICAgIHRyeToKICAgICAgICAgICAgICAgIGIuZXhlY3V0ZSh0ZXh0'
        'KAogICAgICAgICAgICAgICAgICAgIGYiU0VMRUNUIHNldHZhbChwZ19nZXRfc2VyaWFs'
        'X3NlcXVlbmNlKCdcInt0fVwiJywnaWQnKSwgMSwgZmFsc2UpIikpCiAgICAgICAgICAg'
        'IGV4Y2VwdCBFeGNlcHRpb246CiAgICAgICAgICAgICAgICBwYXNzCgoKZGVmIGthc2Ff'
        'YmFraXllX3NpZmlybGEoYiwgZmlkPU5vbmUpOgogICAgIiIiSGFyZWtldGxlciBzaWxp'
        'bmRpOyBiYWtpeWUgYWxhbsSxIGVza2kgZGXEn2VyaW5kZSBrYWxhbWF6LgoKICAgIETE'
        'sEtLQVQ6IGJ1IGnFnyBgaWYgcGc6YCBEScWeSU5EQSBvbG1hbMSxLiDEsGxrIHPDvHLD'
        'vG1kZSBpw6dpbmRlIGthbG3EscWfdMSxCiAgICB2ZSB5YWxuxLF6Y2EgUG9zdGdyZVNR'
        'TCdkZSDDp2FsxLHFn8SxeW9yZHU7IFNRTGl0ZSd0YSBiYWtpeWVsZXIgb2xkdcSfdQog'
        'ICAgZ2liaSBrYWzEsXlvcmR1LgoKICAgIFlBTE5JWkNBIGBrYXNhYCDigJQgYGJhbmth'
        'YCB0YWJsb3N1bmRhIEJBS8SwWUUgU8OcVFVOVSBZT0suIMSwbGsKICAgIHPDvHLDvG1k'
        'ZSAoJ2thc2EnLCdiYW5rYScpIHlhem3EscWfdMSxbTsgb2xtYXlhbiBzw7x0dW5hIHlh'
        'em1heWEKICAgIGthbGttYWsgUG9zdGdyZVNRTCdkZSBVbmRlZmluZWRDb2x1bW4gYXR0'
        'xLEsIGJhxZ9hcsSxc8SxeiBzb3JndQogICAgacWfbGVtaSBaRUjEsFJMRUTEsCB2ZSBv'
        'IGFuYSBrYWRhcmtpIFTDnE0gU8SwTE1FTEVSIGdlcmkgYWzEsW5kxLEuCiAgICBFa3Jh'
        'bmRhICI0MSBrYXnEsXQgc2lsaW5kaSIgeWF6xLFwIGRvxJ9ydWxhbWFkYSAiaMOibMOi'
        'IDQxIGthecSxdCB2YXIiCiAgICDDp8Sxa21hc8SxbsSxbiBzZWJlYmkgYnV5ZHUuIHRy'
        'eS9leGNlcHQgeWV0bWV6OiBQb3N0Z3JlU1FMJ2RlIGhhdGFsxLEKICAgIHNvcmd1ZGFu'
        'IHNvbnJhIGnFn2xlbSBhbmNhayBST0xMQkFDSyBpbGUga3VydHVsdXIuIERvxJ9ydSDD'
        'p8O2esO8bQogICAgaGF0YXnEsSBoacOnIGRvxJ91cm1hbWFrLgogICAgIiIiCiAgICBp'
        'ZiAna2FzYScgbm90IGluIG1ldmN1dDoKICAgICAgICByZXR1cm4gMAogICAgaWYgZmlk'
        'IGlzIE5vbmU6CiAgICAgICAgcyA9IGIuZXhlY3V0ZSh0ZXh0KCdVUERBVEUga2FzYSBT'
        'RVQgYmFraXllID0gMCBXSEVSRSBiYWtpeWUgPD4gMCcpKQogICAgZWxzZToKICAgICAg'
        'ICBzID0gYi5leGVjdXRlKHRleHQoJ1VQREFURSBrYXNhIFNFVCBiYWtpeWUgPSAwICcK'
        'ICAgICAgICAgICAgICAgICAgICAgICAgICAgJ1dIRVJFIGJha2l5ZSA8PiAwIEFORCBm'
        'aXJtYV9pZCA9IDpmJyksIHsnZic6IGZpZH0pCiAgICByZXR1cm4gZ2V0YXR0cihzLCAn'
        'cm93Y291bnQnLCAwKSBvciAwCgoKZGVmIHllZGVrX2FsKCk6CiAgICAiIiJwZ19kdW1w'
        'IOKAlCBiYcWfYXLEsXPEsXpzYSDDp2HEn8SxcmFuIMSwUFRBTCBlZGVyLiIiIgogICAg'
        'aWYgbm90IHBnOgogICAgICAgIHByaW50KCIg4pqgIFBvc3RncmVTUUwgZGXEn2lsIOKA'
        'lCBvdG9tYXRpayB5ZWRlayBhdGxhbmTEsS4iKQogICAgICAgIHJldHVybiBUcnVlCiAg'
        'ICBoZWRlZiA9IFBhdGguaG9tZSgpIC8gJ3llZGVrbGVyJwogICAgaGVkZWYubWtkaXIo'
        'ZXhpc3Rfb2s9VHJ1ZSkKICAgIGRvc3lhID0gaGVkZWYgLyBmInNpZmlybGFtYS1vbmNl'
        'c2kte2RhdGV0aW1lLm5vdygpOiVZJW0lZF8lSCVNJVN9LmR1bXAiCiAgICB0cnk6CiAg'
        'ICAgICAgb3J0YW0gPSBkaWN0KG9zLmVudmlyb24pCiAgICAgICAgaWYga2F5bmFrLnBh'
        'c3N3b3JkOgogICAgICAgICAgICBvcnRhbVsnUEdQQVNTV09SRCddID0ga2F5bmFrLnBh'
        'c3N3b3JkCiAgICAgICAgc29udWMgPSBzdWJwcm9jZXNzLnJ1bigKICAgICAgICAgICAg'
        'WydwZ19kdW1wJywgJy1GYycsICctZicsIHN0cihkb3N5YSksCiAgICAgICAgICAgICAn'
        'LWgnLCBrYXluYWsuaG9zdG5hbWUgb3IgJ2xvY2FsaG9zdCcsCiAgICAgICAgICAgICAn'
        'LXAnLCBzdHIoa2F5bmFrLnBvcnQgb3IgNTQzMiksCiAgICAgICAgICAgICAnLVUnLCBr'
        'YXluYWsudXNlcm5hbWUgb3IgJ3Bvc3RncmVzJywKICAgICAgICAgICAgIGtheW5hay5w'
        'YXRoLmxzdHJpcCgnLycpXSwKICAgICAgICAgICAgZW52PW9ydGFtLCBjYXB0dXJlX291'
        'dHB1dD1UcnVlLCB0ZXh0PVRydWUsIHRpbWVvdXQ9NjAwKQogICAgICAgIGlmIChzb251'
        'Yy5yZXR1cm5jb2RlICE9IDAgb3Igbm90IGRvc3lhLmV4aXN0cygpCiAgICAgICAgICAg'
        'ICAgICBvciBkb3N5YS5zdGF0KCkuc3Rfc2l6ZSA8IDEwMjQpOgogICAgICAgICAgICBw'
        'cmludCgiIOKclyBZZWRlayBBTElOQU1BREkg4oCUIHNpbG1lIMSwUFRBTCBlZGlsZGku'
        'IikKICAgICAgICAgICAgcHJpbnQoZiIgICB7KHNvbnVjLnN0ZGVyciBvciAnJykuc3Ry'
        'aXAoKVs6MjAwXX0iKQogICAgICAgICAgICByZXR1cm4gRmFsc2UKICAgICAgICBwcmlu'
        'dChmIiDinJMge2Rvc3lhfSAgKHtkb3N5YS5zdGF0KCkuc3Rfc2l6ZSAvIDEwMjQ6LjBm'
        'fSBLQikiKQogICAgICAgIHJldHVybiBUcnVlCiAgICBleGNlcHQgRmlsZU5vdEZvdW5k'
        'RXJyb3I6CiAgICAgICAgcHJpbnQoIiDinJcgcGdfZHVtcCBidWx1bmFtYWTEsSDigJQg'
        'c2lsbWUgxLBQVEFMIGVkaWxkaS4iKQogICAgICAgIHJldHVybiBGYWxzZQogICAgZXhj'
        'ZXB0IHN1YnByb2Nlc3MuVGltZW91dEV4cGlyZWQ6CiAgICAgICAgcHJpbnQoIiDinJcg'
        'WWVkZWsgemFtYW4gYcWfxLFtxLFuYSB1xJ9yYWTEsSDigJQgc2lsbWUgxLBQVEFMIGVk'
        'aWxkaS4iKQogICAgICAgIHJldHVybiBGYWxzZQoKCiMg4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCiMgIEJBxZ5MSUsK'
        'IyDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZAKa2F5bmFrID0gdXJscGFyc2UoVlRfVVJMKQpwcmludCgi4pWQIiAqIDcw'
        'KQpwcmludCgiIE1JTEVTVE9ORSBFUlAg4oCUIFNFw4fEsEPEsCBTSUZJUkxBTUEgIChS'
        'NTogw6dva2x1IGZpcm1hKSIpCnByaW50KCLilZAiICogNzApCnByaW50KGYiIFZlcml0'
        'YWJhbsSxIDoge2theW5hay5wYXRoLmxzdHJpcCgnLycpfSBAIHtrYXluYWsuaG9zdG5h'
        'bWUgb3IgJ3llcmVsJ30iKQpwcmludChmIiBTw7xyw7xjw7wgICAgIDoge21vdG9yLmRp'
        'YWxlY3QubmFtZX0iKQpwcmludCgpCgojIOKUgOKUgCBUQU0gS0FQU0FNQSBERU5FVMSw'
        'TcSwIOKUgOKUgAojIEhlciB0YWJsbyB5YSBrb3J1bm1hbMSxIHlhIHNpbGlubWVsaS4g'
        'VWN1IGFjaWsgdGFibG8ga2FsaXJzYQojIHNlc3NpemNlIHRlc3QgdmVyaXNpIGthbGly'
        'OyBidW51IEhBVEEgc2F5aXlvcnV6LgpiaWxpbmVuID0gc2V0KFNJTElORUNFS19UQUJM'
        'T0xBUikgfCBzZXQoS09SVU5BTikKZ296ZGVuX2thY2FuID0gc29ydGVkKHQgZm9yIHQg'
        'aW4gbWV2Y3V0CiAgICAgICAgICAgICAgICAgICAgICBpZiB0IG5vdCBpbiBiaWxpbmVu'
        'IGFuZCB0ICE9ICdhbGVtYmljX3ZlcnNpb24nKQppZiBnb3pkZW5fa2FjYW46CiAgICBw'
        'cmludCgiIOKclyBLQVBTQU0gREnFnkkgVEFCTE8oTEFSKSBWQVIg4oCUIMOnYWzEscWf'
        'bWF5xLEgcmVkZGVkaXlvcnVtOiIpCiAgICBmb3IgdCBpbiBnb3pkZW5fa2FjYW46CiAg'
        'ICAgICAgcHJpbnQoZiIgICAgIHt0fSIpCiAgICBwcmludCgpCiAgICBwcmludCgiICAg'
        'QnUgdGFibG9sYXIgbmUga29ydW51eW9yIG5lIHNpbGluaXlvci4gU2Vzc2l6Y2UgdGVz'
        'dCIpCiAgICBwcmludCgiICAgdmVyaXNpIGLEsXJha21hbWFrIGnDp2luIGJldGnEn2kg'
        'Z8O8bmNlbGxleWluLiIpCiAgICBzeXMuZXhpdCgxKQpwcmludChmIiDinJMga2Fwc2Ft'
        'YSB0YW0g4oCUIHtsZW4obWV2Y3V0KX0gdGFibG9udW4gaGVwc2kgc8SxbsSxZmxhbmTE'
        'sXLEsWxtxLHFnyIpCgojIOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkAojICBGxLBSTUFMQVIKIyDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZAKd2l0aCBt'
        'b3Rvci5jb25uZWN0KCkgYXMgYjoKICAgIGZpcm1hbGFyID0gZmlybWFsYXJpX29rdShi'
        'KQogICAgZmlybWFfc2F5aW1sYXJpID0ge2ZbJ2lkJ106IGZpcm1hX3NheWltKGIsIGZb'
        'J2lkJ10pWzFdIGZvciBmIGluIGZpcm1hbGFyfQoKaWYgbm90IGZpcm1hbGFyOgogICAg'
        'cHJpbnQoKQogICAgcHJpbnQoIiDimqAgSGnDpyBmaXJtYSBrYXlkxLEgeW9rLiIpCiAg'
        'ICBwcmludCgiICAgw4dva2x1IGZpcm1hIGfDtsOnw7wgKGdvY19tZjEucHkpIMOnYWzE'
        'scWfdMSxcsSxbG1hbcSxxZ8gb2xhYmlsaXI7IikKICAgIHByaW50KCIgICB5YSBkYSB2'
        'ZXJpdGFiYW7EsSBib21ib8WfLiBUZWsgZmlybWEga2lwaSBrdWxsYW7EsWxhbWF6LiIp'
        'CiAgICBpZiBURUtfRklSTUFfQVJHIG9yIFRVTVVOVV9TSUw6CiAgICAgICAgc3lzLmV4'
        'aXQoMSkKZWxzZToKICAgIHByaW50KGYiIOKckyB7bGVuKGZpcm1hbGFyKX0gZmlybWEg'
        'a2F5xLF0bMSxIikKCnByaW50KCkKcHJpbnQoIuKUgCIgKiA3MCkKcHJpbnQoIiBGxLBS'
        'TUFMQVIiKQpwcmludCgi4pSAIiAqIDcwKQpmb3IgZiBpbiBmaXJtYWxhcjoKICAgIGlz'
        'YXJldCA9ICcg4piFJyBpZiBmWyd2YXJzYXlpbGFuJ10gZWxzZSAnICAnCiAgICBrYXBh'
        'bGkgPSAnJyBpZiBmWydha3RpZiddIGVsc2UgJyAgKGthcGFsxLEpJwogICAgcHJpbnQo'
        'ZiIgIHtpc2FyZXR9IFt7ZlsnaWQnXTo+Mn1dIHtmWydhZCddOjwxOH0ge2ZbJ2tvZCdd'
        'Ojw1fSAiCiAgICAgICAgICBmInt0cihmaXJtYV9zYXlpbWxhcmkuZ2V0KGZbJ2lkJ10s'
        'IDApKTo+OX0ga2F5xLF0e2thcGFsaX0iKQpwcmludCgiICAgICDimIUgdmFyc2F5xLFs'
        'YW4gZmlybWEiKQoKaWYgRklSTUFfTElTVEVTSToKICAgIHByaW50KCLilZAiICogNzAp'
        'CiAgICBzeXMuZXhpdCgwKQoKIyDilIDilIAgS8SwUCBTRcOHxLBNxLAg4pSA4pSAClRF'
        'S19GSVJNQSA9IE5vbmUKaWYgVEVLX0ZJUk1BX0FSRzoKICAgIGFkYXlsYXIgPSBbZiBm'
        'b3IgZiBpbiBmaXJtYWxhcgogICAgICAgICAgICAgICBpZiBzdHIoZlsnaWQnXSkgPT0g'
        'VEVLX0ZJUk1BX0FSRwogICAgICAgICAgICAgICBvciBmWydhZCddLnN0cmlwKCkudXBw'
        'ZXIoKSA9PSBURUtfRklSTUFfQVJHLnVwcGVyKCldCiAgICBpZiBub3QgYWRheWxhcjoK'
        'ICAgICAgICBwcmludCgpCiAgICAgICAgcHJpbnQoZiIg4pyXIEZpcm1hIGJ1bHVuYW1h'
        'ZMSxOiB7VEVLX0ZJUk1BX0FSR30iKQogICAgICAgIHByaW50KCIgICBZdWthcsSxZGFr'
        'aSBsaXN0ZWRlbiBraW1saWsgeWEgZGEgYWTEsSB5YXrEsW4uIikKICAgICAgICBzeXMu'
        'ZXhpdCgxKQogICAgaWYgbGVuKGFkYXlsYXIpID4gMToKICAgICAgICBwcmludCgpCiAg'
        'ICAgICAgcHJpbnQoZiIg4pyXICd7VEVLX0ZJUk1BX0FSR30nIGJpcmRlbiDDp29rIGZp'
        'cm1heWEgdXl1eW9yIOKAlCBraW1saWsgeWF6xLFuLiIpCiAgICAgICAgc3lzLmV4aXQo'
        'MSkKICAgIFRFS19GSVJNQSA9IGFkYXlsYXJbMF0KCiAgICAjIFPDvHrDvGxlbWV5ZW4g'
        'dGFibG8gdmFyc2EgdGVrIGZpcm1hIGtpcGkgR8OcVkVOTMSwIERFxJ7EsEwuCiAgICBp'
        'ZiBGSVJNQVNJWl9TSUxJTkVDRUs6CiAgICAgICAgcHJpbnQoKQogICAgICAgIHByaW50'
        'KCIg4pyXIFRFSyBGxLBSTUEgS8SwUMSwIEtVTExBTklMQU1BWiDigJQgZmlybWFfaWQn'
        'c2kgb2xtYXlhbiIpCiAgICAgICAgcHJpbnQoIiAgIHNpbGluZWNlayB0YWJsbyhsYXIp'
        'IHZhcjoiKQogICAgICAgIGZvciB0IGluIEZJUk1BU0laX1NJTElORUNFSzoKICAgICAg'
        'ICAgICAgcHJpbnQoZiIgICAgIHt0fSIpCiAgICAgICAgcHJpbnQoKQogICAgICAgIHBy'
        'aW50KCIgICBCdSB0YWJsb3l1IHTDvG1kZW4gc2lsbWVrIETEsMSeRVIgZmlybWFsYXLE'
        'sW4gdmVyaXNpbmkiKQogICAgICAgIHByaW50KCIgICBnw7Z0w7xyw7xyLCBixLFyYWtt'
        'YWsgZGEgYXJ0xLFrIGthecSxdCBixLFyYWvEsXIuIMSwa2lzaSBkZSIpCiAgICAgICAg'
        'cHJpbnQoIiAgIHlhbmzEscWfOyB0YWJsb3lhIGZpcm1hX2lkIGVrbGV5aW4gKEZpcm1h'
        'S2Fwc2FtbGkpIHlhIGRhIikKICAgICAgICBwcmludCgiICAgS09SVU5BTiBsaXN0ZXNp'
        'bmUgYWzEsW4uIikKICAgICAgICBzeXMuZXhpdCgxKQoKaWYgVFVNVU5VX1NJTDoKICAg'
        'IEtJUCA9ICd0dW11bnUnCiAgICAjIEthbGFjYWsgZmlybWE6IHZhcnNhecSxbGFuLCB5'
        'b2tzYSBlbiBrw7zDp8O8ayBraW1saWtsaS4KICAgICMgU2lzdGVtIGZpcm1hc8SxeiDD'
        'p2FsxLHFn21hejsgw7xzdGVsaWsgZmlybWEga2F5ZMSxIFIyJ2RlbiBiZXJpCiAgICAj'
        'IGtvcnVuYW4gImZpcm1hIGJpbGdpbGVyaSB2ZSBMT0dPIm51biB5YcWfYWTEscSfxLEg'
        'eWVyIChNRjUpLgogICAgX2thbGFuID0gbmV4dCgoZiBmb3IgZiBpbiBmaXJtYWxhciBp'
        'ZiBmWyd2YXJzYXlpbGFuJ10pLCBOb25lKSBvciBmaXJtYWxhclswXQogICAgS0FMQU5f'
        'RklSTUEgPSBfa2FsYW4KICAgIFNJTElORU5fRklSTUFMQVIgPSBbZiBmb3IgZiBpbiBm'
        'aXJtYWxhciBpZiBmWydpZCddICE9IF9rYWxhblsnaWQnXV0KICAgIEtJUF9BREkgPSAn'
        'VMOcTSBWRVLEsExFUsSwIFPEsEwnCmVsaWYgVEVLX0ZJUk1BOgogICAgS0lQID0gJ3Rl'
        'aycKICAgIEtJUF9BREkgPSBmIlNBREVDRSB7VEVLX0ZJUk1BWydhZCddfSBGxLBSTUFT'
        'SU5JIFNJRklSTEEiCmVsc2U6CiAgICBLSVAgPSAndHVtX2Zpcm1hbGFyJwogICAgS0lQ'
        'X0FESSA9ICdUw5xNIEbEsFJNQUxBUkkgU0lGSVJMQSAoZmlybWEgdGFuxLFtbGFyxLEg'
        'a2FsxLFyKScKCnByaW50KCkKcHJpbnQoIuKUgCIgKiA3MCkKcHJpbnQoZiIgS8SwUDog'
        'e0tJUF9BREl9IikKcHJpbnQoIuKUgCIgKiA3MCkKCndpdGggbW90b3IuY29ubmVjdCgp'
        'IGFzIGI6CiAgICBrb3J1bmFuX3NheWltID0gdGFibG9fc2F5aW0oYiwgS09SVU5BTi5r'
        'ZXlzKCkpCiAgICBpZiBLSVAgPT0gJ3Rlayc6CiAgICAgICAgc2F5aW0sIHRvcGxhbSA9'
        'IGZpcm1hX3NheWltKGIsIFRFS19GSVJNQVsnaWQnXSkKICAgICAgICBla3NpayA9IFtd'
        'CiAgICBlbHNlOgogICAgICAgIHNheWltLCBla3NpaywgdG9wbGFtID0ge30sIFtdLCAw'
        'CiAgICAgICAgZm9yIHQgaW4gU0lMX1NJUkFTSToKICAgICAgICAgICAgaWYgdCBub3Qg'
        'aW4gbWV2Y3V0OgogICAgICAgICAgICAgICAgZWtzaWsuYXBwZW5kKHQpCiAgICAgICAg'
        'ICAgICAgICBjb250aW51ZQogICAgICAgICAgICBuID0gYi5leGVjdXRlKHRleHQoZidT'
        'RUxFQ1QgQ09VTlQoKikgRlJPTSAie3R9IicpKS5zY2FsYXIoKSBvciAwCiAgICAgICAg'
        'ICAgIHNheWltW3RdID0gbgogICAgICAgICAgICB0b3BsYW0gKz0gbgogICAgIyBhdWRp'
        'dF9sb2cnZGEgZmlybWF5YSBiYcSfbGFubWFtxLHFnyBzYXTEsXJsYXI6IHRlayBmaXJt'
        'YSBraXBpbmRlCiAgICAjIFPEsEzEsE5NRVogKGhhbmdpIGZpcm1heWEgYWl0IG9sZHXE'
        'n3UgYmlsaW5taXlvcikuIFNlc3NpeiBrYWxtYXPEsW4uCiAgICBhdWRpdF9iYWdzaXog'
        'PSAwCiAgICBpZiAnYXVkaXRfbG9nJyBpbiBtZXZjdXQ6CiAgICAgICAgYXVkaXRfYmFn'
        'c2l6ID0gYi5leGVjdXRlKHRleHQoCiAgICAgICAgICAgICdTRUxFQ1QgQ09VTlQoKikg'
        'RlJPTSBhdWRpdF9sb2cgV0hFUkUgZmlybWFfaWQgSVMgTlVMTCcpKS5zY2FsYXIoKSBv'
        'ciAwCgpwcmludCgpCnByaW50KCIgS09SVU5BQ0FLIikKZm9yIHQsIGFjaWtsYW1hIGlu'
        'IEtPUlVOQU4uaXRlbXMoKToKICAgIG4gPSBrb3J1bmFuX3NheWltLmdldCh0LCAwKQog'
        'ICAgbm90XyA9ICcnCiAgICBpZiBLSVAgPT0gJ3R1bXVudScgYW5kIHQgaW4gKCdmaXJt'
        'YScsKToKICAgICAgICBub3RfID0gZicgIOKGkiB7bGVuKFNJTElORU5fRklSTUFMQVIp'
        'fSBmaXJtYSBTxLBMxLBORUNFSywgMSBrYWxhY2FrJwogICAgZWxpZiBLSVAgPT0gJ3R1'
        'bXVudScgYW5kIHQgaW4gKCdrYXNhJywgJ2JhbmthJywgJ3ZlcmlsZXInLCAnY2FyaV9m'
        'aXJtYScpOgogICAgICAgIG5vdF8gPSAnICDihpIgc2lsaW5lbiBmaXJtYWxhcsSxbiBz'
        'YXTEsXJsYXLEsSBnaWRlcicKICAgIHByaW50KGYiICAge3Q6PDE2c30ge3RyKG4pOj43'
        'fSBrYXnEsXQgICB7YWNpa2xhbWF9e25vdF99IikKCnByaW50KCkKcHJpbnQoIiBTxLBM'
        'xLBORUNFSyIpCmZvciB0IGluIFNJTF9TSVJBU0k6CiAgICBpZiBzYXlpbS5nZXQodCk6'
        'CiAgICAgICAgcHJpbnQoZiIgICB7dDo8MTZzfSB7dHIoc2F5aW1bdF0pOj43fSBrYXnE'
        'sXQiKQpib3MgPSBbdCBmb3IgdCBpbiBTSUxfU0lSQVNJIGlmIHNheWltLmdldCh0KSA9'
        'PSAwXQppZiBib3M6CiAgICBwcmludChmIiAgICh6YXRlbiBib8WfOiB7JywgJy5qb2lu'
        'KGJvcyl9KSIpCmlmIGVrc2lrOgogICAgcHJpbnQoZiIgICAodGFibG9kYSB5b2s6IHsn'
        'LCAnLmpvaW4oZWtzaWspfSkiKQpwcmludCgpCnByaW50KGYiICAgVE9QTEFNIHt0cih0'
        'b3BsYW0pfSBrYXnEsXQgc2lsaW5lY2VrIikKCmlmIEtJUCA9PSAndGVrJzoKICAgIHBy'
        'aW50KCkKICAgIHByaW50KCIgRE9LVU5VTE1BWUFDQUsgRsSwUk1BTEFSIikKICAgIGZv'
        'ciBmIGluIGZpcm1hbGFyOgogICAgICAgIGlmIGZbJ2lkJ10gPT0gVEVLX0ZJUk1BWydp'
        'ZCddOgogICAgICAgICAgICBjb250aW51ZQogICAgICAgIHByaW50KGYiICAgW3tmWydp'
        'ZCddOj4yfV0ge2ZbJ2FkJ106PDE4fSAiCiAgICAgICAgICAgICAgZiJ7dHIoZmlybWFf'
        'c2F5aW1sYXJpLmdldChmWydpZCddLCAwKSk6Pjl9IGthecSxdCDigJQgREXEnsSwxZ5N'
        'RVlFQ0VLIikKICAgIGlmIGF1ZGl0X2JhZ3NpejoKICAgICAgICBwcmludCgpCiAgICAg'
        'ICAgcHJpbnQoZiIgICBOT1Q6IGF1ZGl0X2xvZydkYSBmaXJtYXlhIGJhxJ9sYW5tYW3E'
        'scWfIHt0cihhdWRpdF9iYWdzaXopfSBzYXTEsXIiKQogICAgICAgIHByaW50KCIgICAg'
        'ICAgIHZhcjsgaGFuZ2kgZmlybWF5YSBhaXQgb2xkdcSfdSBiaWxpbm1lZGnEn2kgacOn'
        'aW4iKQogICAgICAgIHByaW50KCIgICAgICAgIFPEsEzEsE5NRVlFQ0VLLiAoR8O2w6cg'
        'w7ZuY2VzaSBrYXnEsXRsYXIgdmUgc2lsaW5tacWfIikKICAgICAgICBwcmludCgiICAg'
        'ICAgICBmaXJtYWxhcmRhbiBrb3BhbiBpemxlci4pIikKCmlmIEtJUCA9PSAndHVtdW51'
        'JzoKICAgIHByaW50KCkKICAgIHByaW50KCIgRsSwUk1BIFRBTklNTEFSSSIpCiAgICBw'
        'cmludChmIiAgIEtBTEFDQUsgOiBbe0tBTEFOX0ZJUk1BWydpZCddfV0ge0tBTEFOX0ZJ'
        'Uk1BWydhZCddfSAiCiAgICAgICAgICBmIuKAlCBraW1sacSfaSwgw7xudmFuxLEsIGxv'
        'Z29zdSBrb3J1bnVyIikKICAgIGZvciBmIGluIFNJTElORU5fRklSTUFMQVI6CiAgICAg'
        'ICAgcHJpbnQoZiIgICBTxLBMxLBOxLBSIDogW3tmWydpZCddfV0ge2ZbJ2FkJ119IikK'
        'ICAgIHByaW50KCkKICAgIHByaW50KCIgICBDYXJpIGthcnRsYXLEsSBrb3J1bnVyIHZl'
        'IEtBTEFOIEbEsFJNQVlBIEJBxJ5MQU5JUi4iKQogICAgcHJpbnQoIiAgIEJhxJ9sYW5t'
        'YXpzYSBrYXJ0IGRpc2t0ZSBkdXJ1ciBhbWEgaGnDp2JpciBmaXJtYWRhIikKICAgIHBy'
        'aW50KCIgICBnw7Zyw7xubWV6IOKAlCBrdWxsYW7EsWPEsSAndmVyaW0gZ2l0dGknIHNh'
        'bmFyLiIpCgojIOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkAojICBSQVBPUiBNT0RVCiMg4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCmlmIG5vdCBPTkFZ'
        'OgogICAgcHJpbnQoKQogICAgcHJpbnQoIuKVkCIgKiA3MCkKICAgIHByaW50KCIgUkFQ'
        'T1IgTU9EVSDigJQgaGnDp2JpciDFn2V5IHNpbGlubWVkaS4iKQogICAgcHJpbnQoKQog'
        'ICAgcHJpbnQoIiBTRcOHRU5FS0xFUiIpCiAgICBwcmludCgpCiAgICBwcmludCgiICAg'
        'MSkgVMOcTSBGxLBSTUFMQVJJIFNJRklSTEEg4oCUIGnFn2xlbSB2ZXJpc2kgZ2lkZXIs'
        'IikKICAgIHByaW50KCIgICAgICBmaXJtYSB0YW7EsW1sYXLEsS9raW1saWtsZXJpL2th'
        'c2FsYXLEsSBrYWzEsXI6IikKICAgIHByaW50KCIgICAgICAgIHZlbnYvYmluL3B5dGhv'
        'biBzaWZpcmxhMi5weSAtLW9uYXlsYSIpCiAgICBwcmludCgpCiAgICBwcmludCgiICAg'
        'MikgU0FERUNFIELEsFIgRsSwUk1BWUkgU0lGSVJMQSDigJQgZGnEn2VybGVyaW5lIGRv'
        'a3VudWxtYXo6IikKICAgIGZvciBmIGluIGZpcm1hbGFyOgogICAgICAgIHByaW50KGYi'
        'ICAgICAgICB2ZW52L2Jpbi9weXRob24gc2lmaXJsYTIucHkgLS1maXJtYT17ZlsnaWQn'
        'XX0gIgogICAgICAgICAgICAgIGYiLS1vbmF5bGEgICAgICAjIHtmWydhZCddfSIpCiAg'
        'ICBwcmludCgpCiAgICBwcmludCgiICAgMykgVMOcTSBWRVLEsExFUsSwIFPEsEwg4oCU'
        'IGZpcm1hbGFyIGRhIGdpZGVyLCBiaXJpIGthbMSxcjoiKQogICAgcHJpbnQoIiAgICAg'
        'ICAgdmVudi9iaW4vcHl0aG9uIHNpZmlybGEyLnB5IC0tdHVtdW51LXNpbCAtLW9uYXls'
        'YSIpCiAgICBwcmludCgpCiAgICBwcmludCgiIOKaoCDDlm5jZSBlbGxlIHllZGVrIGFs'
        'xLFuOiIpCiAgICBwcmludCgiICAgc3VkbyAvdXNyL2xvY2FsL2Jpbi9taWxlc3RvbmUt'
        'eWVkZWsuc2giKQogICAgcHJpbnQoIuKVkCIgKiA3MCkKICAgIHN5cy5leGl0KDApCgoj'
        'IOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkAojICBZRURFSwojIOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkApwcmludCgpCnByaW50KCLilIAiICogNzAp'
        'CnByaW50KCIgWUVERUsiKQpwcmludCgi4pSAIiAqIDcwKQppZiBub3QgeWVkZWtfYWwo'
        'KToKICAgIHN5cy5leGl0KDEpCgojIOKUgOKUgCBTaWxtZSDDtm5jZXNpIEbEsFJNQSBC'
        'QcWeSU5BIGZvdG/En3JhZiDilIDilIAKIyBUZWsgZmlybWEga2lwaW5pbiB0ZWsgc8O2'
        'esO8IGJ1OiBkacSfZXIgZmlybWFsYXIgREXEnsSwxZ5NRVouIFPDtnrDvAojIHR1dHVw'
        'IHR1dG1hZMSxxJ/EsW3EsXrEsSDDtmzDp21lbmluIHlvbHUsIHNpbG1lZGVuIMO2bmNl'
        'IHZlIHNvbnJhCiMgc2F5bWFrdGFuIGdlw6dpeW9yLgp3aXRoIG1vdG9yLmNvbm5lY3Qo'
        'KSBhcyBiOgogICAgb25jZV9maXJtYSA9IHtmWydpZCddOiBmaXJtYV9zYXlpbShiLCBm'
        'WydpZCddKVsxXSBmb3IgZiBpbiBmaXJtYWxhcn0KICAgIG9uY2Vfa29ydW5hbiA9IHRh'
        'YmxvX3NheWltKGIsIEtPUlVOQU4ua2V5cygpKQoKIyDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZAKIyAgU8SwTE1FICh0'
        'ZWsgdHJhbnNhY3Rpb24pCiMg4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCnByaW50KCkKcHJpbnQoIuKUgCIgKiA3MCkK'
        'cHJpbnQoIiBTxLBMxLBOxLBZT1IiKQpwcmludCgi4pSAIiAqIDcwKQp3aXRoIG1vdG9y'
        'LmJlZ2luKCkgYXMgYjoKICAgIGlmIEtJUCA9PSAndGVrJzoKICAgICAgICBmaWQgPSBU'
        'RUtfRklSTUFbJ2lkJ10KICAgICAgICBmb3IgdCBpbiBTSUxfU0lSQVNJOgogICAgICAg'
        'ICAgICBpZiB0IG5vdCBpbiBtZXZjdXQ6CiAgICAgICAgICAgICAgICBjb250aW51ZQog'
        'ICAgICAgICAgICBuID0gc2F5aW0uZ2V0KHQsIDApCiAgICAgICAgICAgIGIuZXhlY3V0'
        'ZSh0ZXh0KGYnREVMRVRFIEZST00gInt0fSIgV0hFUkUgZmlybWFfaWQgPSA6ZicpLCB7'
        'J2YnOiBmaWR9KQogICAgICAgICAgICBpZiBuOgogICAgICAgICAgICAgICAgcHJpbnQo'
        'ZiIgICB7dDo8MTZzfSB7dHIobik6Pjd9IGthecSxdCBzaWxpbmRpIikKICAgICAgICAj'
        'IETEsFrEsCBTSUZJUkxBTUEgWU9LOiB0YWJsb2xhciBib8WfYWxtYWTEsS4gU2F5YWPE'
        'sSAxJ2Ugw6dla21lawogICAgICAgICMgZGnEn2VyIGZpcm1hbsSxbiBtZXZjdXQgaWQn'
        'bGVyaXlsZSDDp2FrxLHFn2FuIGlkIMO8cmV0aXJkaS4KICAgICAgICBfbiA9IGthc2Ff'
        'YmFraXllX3NpZmlybGEoYiwgZmlkKQogICAgICAgIGlmIF9uOgogICAgICAgICAgICBw'
        'cmludChmIiAgIGthc2EgICAgICAgICAgICAge19ufSBrYXlkxLFuIGJha2l5ZXNpIHPE'
        'sWbEsXJsYW5kxLEiKQogICAgZWxzZToKICAgICAgICBmb3IgdCBpbiBTSUxfU0lSQVNJ'
        'OgogICAgICAgICAgICBpZiB0IG5vdCBpbiBtZXZjdXQ6CiAgICAgICAgICAgICAgICBj'
        'b250aW51ZQogICAgICAgICAgICBuID0gc2F5aW0uZ2V0KHQsIDApCiAgICAgICAgICAg'
        'IGIuZXhlY3V0ZSh0ZXh0KGYnREVMRVRFIEZST00gInt0fSInKSkKICAgICAgICAgICAg'
        'aWYgbjoKICAgICAgICAgICAgICAgIHByaW50KGYiICAge3Q6PDE2c30ge3RyKG4pOj43'
        'fSBrYXnEsXQgc2lsaW5kaSIpCiAgICAgICAgZGl6aWxlcmlfc2lmaXJsYShiKQogICAg'
        'ICAgIF9uID0ga2FzYV9iYWtpeWVfc2lmaXJsYShiLCBOb25lKQogICAgICAgIGlmIF9u'
        'OgogICAgICAgICAgICBwcmludChmIiAgIGthc2EgICAgICAgICAgICAge19ufSBrYXlk'
        'xLFuIGJha2l5ZXNpIHPEsWbEsXJsYW5kxLEiKQoKICAgIGlmIEtJUCA9PSAndHVtdW51'
        'JzoKICAgICAgICBwcmludCgpCiAgICAgICAgZm9yIGYgaW4gU0lMSU5FTl9GSVJNQUxB'
        'UjoKICAgICAgICAgICAgIyBGaXJtYXlhIGJhxJ9sxLEgS09SVU5BTiB0YWJsb2xhcmRh'
        'biBkYSAoa2FzYSwgYmFua2EsCiAgICAgICAgICAgICMgdmVyaWxlciwgY2FyaV9maXJt'
        'YSkgYnUgZmlybWFuxLFuIHNhdMSxcmxhcsSxIGdpdG1lbGk7CiAgICAgICAgICAgICMg'
        'eW9rc2EgYGZpcm1hYCBzaWxpbmlya2VuIHlhYmFuY8SxIGFuYWh0YXIga8SxcsSxbMSx'
        'ci4KICAgICAgICAgICAgZm9yIHQgaW4gRklSTUFfQkFHTEk6CiAgICAgICAgICAgICAg'
        'ICBpZiB0IGluIG1ldmN1dDoKICAgICAgICAgICAgICAgICAgICBiLmV4ZWN1dGUodGV4'
        'dChmJ0RFTEVURSBGUk9NICJ7dH0iIFdIRVJFIGZpcm1hX2lkID0gOmYnKSwKICAgICAg'
        'ICAgICAgICAgICAgICAgICAgICAgICAgeydmJzogZlsnaWQnXX0pCiAgICAgICAgICAg'
        'ICMgRGVuZXRpbSBpemkgU8SwTMSwTk1FWiwgeWFsbsSxemNhIGJhxJ/EsSBrb3BhcsSx'
        'bMSxcjogc2lsaW5tacWfCiAgICAgICAgICAgICMgZmlybWFkYSBuZSB5YXDEsWxkxLHE'
        'n8SxIGRhIGfDtnLDvG5lYmlsbWVsaSAoTUY0IGlsZSBheW7EsQogICAgICAgICAgICAj'
        'IGRhdnJhbsSxxZ8pLgogICAgICAgICAgICBpZiAnYXVkaXRfbG9nJyBpbiBtZXZjdXQ6'
        'CiAgICAgICAgICAgICAgICBiLmV4ZWN1dGUodGV4dCgnVVBEQVRFIGF1ZGl0X2xvZyBT'
        'RVQgZmlybWFfaWQgPSBOVUxMICcKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg'
        'ICdXSEVSRSBmaXJtYV9pZCA9IDpmJyksIHsnZic6IGZbJ2lkJ119KQogICAgICAgICAg'
        'ICBiLmV4ZWN1dGUodGV4dCgnREVMRVRFIEZST00gZmlybWEgV0hFUkUgaWQgPSA6Zicp'
        'LCB7J2YnOiBmWydpZCddfSkKICAgICAgICAgICAgcHJpbnQoZiIgICBmaXJtYSBbe2Zb'
        'J2lkJ119XSB7ZlsnYWQnXX0gc2lsaW5kaSIpCgogICAgICAgICMgS2FsYW4gZmlybWEg'
        'dmFyc2F5xLFsYW4gdmUgYcOnxLFrIG9sc3VuIOKAlCB0ZWsgZmlybWEga2FsZMSxxJ/E'
        'sW5kYQogICAgICAgICMgInZhcnNhecSxbGFuIHlvayIgZHVydW11IGdpcmnFnyBha8Sx'
        'xZ/EsW7EsSBrxLFyYXJkxLEuCiAgICAgICAgYi5leGVjdXRlKHRleHQoJ1VQREFURSBm'
        'aXJtYSBTRVQgdmFyc2F5aWxhbiA9IDplLCBha3RpZiA9IDplICcKICAgICAgICAgICAg'
        'ICAgICAgICAgICAnV0hFUkUgaWQgPSA6ZicpLAogICAgICAgICAgICAgICAgICB7J2Un'
        'OiBUcnVlLCAnZic6IEtBTEFOX0ZJUk1BWydpZCddfSkKCiAgICAgICAgIyDilIDilIAg'
        'Q0FSxLAgR8OWUsOcTsOcUkzDnMSew5wg4pSA4pSACiAgICAgICAgIyDDnHllbGnEn2kg'
        'a2FsbWF5YW4gY2FyaSBoacOnYmlyIGZpcm1hZGEgTMSwU1RFTEVOTUVaLiBLYXJ0CiAg'
        'ICAgICAgIyBkaXNrdGUgZHVydXIgYW1hIGVrcmFuZGEgeW9rOyBidSwgdmVyaXlpIHNp'
        'bG1la3RlbiBiZXRlcjoKICAgICAgICAjIGt1bGxhbsSxY8SxIGtheWLEsSBnw7Zyw7xy'
        'LCBzZWJlYmluaSBidWxhbWF6LiBIZXBzaW5pIGthbGFuCiAgICAgICAgIyBmaXJtYXlh'
        'IGJhxJ9sxLF5b3J1ei4KICAgICAgICBfc2ltZGkgPSBkYXRldGltZS5ub3coKQogICAg'
        'ICAgIF9hcnRpayA9IFtyWzBdIGZvciByIGluIGIuZXhlY3V0ZSh0ZXh0KAogICAgICAg'
        'ICAgICAnU0VMRUNUIGMuaWQgRlJPTSBjYXJpbGVyIGMgV0hFUkUgTk9UIEVYSVNUUyAn'
        'CiAgICAgICAgICAgICcoU0VMRUNUIDEgRlJPTSBjYXJpX2Zpcm1hIGNmIFdIRVJFIGNm'
        'LmNhcmlfaWQgPSBjLmlkICcKICAgICAgICAgICAgJyBBTkQgY2YuZmlybWFfaWQgPSA6'
        'ZiknKSwgeydmJzogS0FMQU5fRklSTUFbJ2lkJ119KS5mZXRjaGFsbCgpXQogICAgICAg'
        'IGZvciBfY2lkIGluIF9hcnRpazoKICAgICAgICAgICAgYi5leGVjdXRlKHRleHQoJ0lO'
        'U0VSVCBJTlRPIGNhcmlfZmlybWEgKGNhcmlfaWQsIGZpcm1hX2lkLCBvbHVzdHVybWEp'
        'ICcKICAgICAgICAgICAgICAgICAgICAgICAgICAgJ1ZBTFVFUyAoOmMsIDpmLCA6bykn'
        'KSwKICAgICAgICAgICAgICAgICAgICAgIHsnYyc6IF9jaWQsICdmJzogS0FMQU5fRklS'
        'TUFbJ2lkJ10sICdvJzogX3NpbWRpfSkKICAgICAgICBpZiBfYXJ0aWs6CiAgICAgICAg'
        'ICAgIHByaW50KGYiICAge2xlbihfYXJ0aWspfSBjYXJpIFt7S0FMQU5fRklSTUFbJ2lk'
        'J119XSAiCiAgICAgICAgICAgICAgICAgIGYie0tBTEFOX0ZJUk1BWydhZCddfSBmaXJt'
        'YXPEsW5hIGJhxJ9sYW5kxLEiKQoKIyDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZAKIyAgRE/EnlJVTEFNQQojIOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kApwcmludCgpCnByaW50KCLilIAiICogNzApCnByaW50KCIgRE/EnlJVTEFNQSIpCnBy'
        'aW50KCLilIAiICogNzApCmhhdGFsaSA9IEZhbHNlCndpdGggbW90b3IuY29ubmVjdCgp'
        'IGFzIGI6CiAgICAjIDEgwrcgU2lsaW5tZXNpIGdlcmVrZW5sZXIgZ2l0dGkgbWk/CiAg'
        'ICBpZiBLSVAgPT0gJ3Rlayc6CiAgICAgICAgXywga2FsYW5fdG9wbGFtID0gZmlybWFf'
        'c2F5aW0oYiwgVEVLX0ZJUk1BWydpZCddKQogICAgICAgIGlmIGthbGFuX3RvcGxhbToK'
        'ICAgICAgICAgICAgcHJpbnQoZiIgICDinJcge1RFS19GSVJNQVsnYWQnXX06IGjDomzD'
        'oiB7dHIoa2FsYW5fdG9wbGFtKX0ga2F5xLF0IHZhciIpCiAgICAgICAgICAgIGhhdGFs'
        'aSA9IFRydWUKICAgICAgICBlbHNlOgogICAgICAgICAgICBwcmludChmIiAgIOKckyB7'
        'VEVLX0ZJUk1BWydhZCddfSBzxLFmxLFybGFuZMSxIikKICAgIGVsc2U6CiAgICAgICAg'
        'a2FsaW50aSA9IDAKICAgICAgICBmb3IgdCBpbiBTSUxfU0lSQVNJOgogICAgICAgICAg'
        'ICBpZiB0IG5vdCBpbiBtZXZjdXQ6CiAgICAgICAgICAgICAgICBjb250aW51ZQogICAg'
        'ICAgICAgICBuID0gYi5leGVjdXRlKHRleHQoZidTRUxFQ1QgQ09VTlQoKikgRlJPTSAi'
        'e3R9IicpKS5zY2FsYXIoKSBvciAwCiAgICAgICAgICAgIGlmIG46CiAgICAgICAgICAg'
        'ICAgICBwcmludChmIiAgIOKclyB7dDo8MTZzfSBow6Jsw6Ige3RyKG4pfSBrYXnEsXQg'
        'dmFyIikKICAgICAgICAgICAgICAgIGthbGludGkgKz0gbgogICAgICAgICAgICAgICAg'
        'aGF0YWxpID0gVHJ1ZQogICAgICAgIGlmIG5vdCBrYWxpbnRpOgogICAgICAgICAgICBw'
        'cmludCgiICAg4pyTIHNpbGluZWNlayB0YWJsb2xhcsSxbiBoZXBzaSBib8WfIikKCiAg'
        'ICAjIDIgwrcgRE9LVU5VTE1BWUFOIEbEsFJNQUxBUiDigJQgdGVrIGZpcm1hIGtpcGlu'
        'aW4gYXPEsWwgc8O2esO8CiAgICBpZiBLSVAgPT0gJ3Rlayc6CiAgICAgICAgZm9yIGYg'
        'aW4gZmlybWFsYXI6CiAgICAgICAgICAgIGlmIGZbJ2lkJ10gPT0gVEVLX0ZJUk1BWydp'
        'ZCddOgogICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgXywgc2ltZGkg'
        'PSBmaXJtYV9zYXlpbShiLCBmWydpZCddKQogICAgICAgICAgICBiZWtsZW5lbiA9IG9u'
        'Y2VfZmlybWEuZ2V0KGZbJ2lkJ10sIDApCiAgICAgICAgICAgIGlmIHNpbWRpICE9IGJl'
        'a2xlbmVuOgogICAgICAgICAgICAgICAgcHJpbnQoZiIgICDinJcgW3tmWydpZCddfV0g'
        'e2ZbJ2FkJ119OiB7dHIoYmVrbGVuZW4pfSBrYXnEsXQgIgogICAgICAgICAgICAgICAg'
        'ICAgICAgZiJiZWtsZW5pcmtlbiB7dHIoc2ltZGkpfSB2YXIg4oCUIFZFUsSwIEtBWUJJ'
        'IikKICAgICAgICAgICAgICAgIGhhdGFsaSA9IFRydWUKICAgICAgICAgICAgZWxzZToK'
        'ICAgICAgICAgICAgICAgIHByaW50KGYiICAg4pyTIFt7ZlsnaWQnXX1dIHtmWydhZCdd'
        'OjwxOH0gIgogICAgICAgICAgICAgICAgICAgICAgZiJ7dHIoc2ltZGkpOj45fSBrYXnE'
        'sXQg4oCUIGRlxJ9pxZ9tZWRpIikKCiAgICAjIDMgwrcgS29ydW5hbiB0YWJsb2xhcgog'
        'ICAgc2ltZGlfa29ydW5hbiA9IHRhYmxvX3NheWltKGIsIEtPUlVOQU4ua2V5cygpKQog'
        'ICAgZm9yIHQgaW4gS09SVU5BTjoKICAgICAgICBpZiB0IG5vdCBpbiBtZXZjdXQ6CiAg'
        'ICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgc2ltZGkgPSBzaW1kaV9rb3J1bmFuLmdl'
        'dCh0LCAwKQogICAgICAgIGJla2xlbmVuID0gb25jZV9rb3J1bmFuLmdldCh0LCAwKQoK'
        'ICAgICAgICAjIOKUgOKUgCBjYXJpX2Zpcm1hLCAtLXR1bXVudS1zaWwga2lwaW5kZSBB'
        'UlRBQsSwTMSwUiDilIDilIAKICAgICAgICAjIMSwbGsgc8O8csO8bWRlIGJ1IHRhYmxv'
        'eXUgInlhbG7EsXpjYSBhemFsxLFyIiBzYXlhbiBncnViYQogICAgICAgICMga295bXXF'
        'n3R1bSB2ZSBkb8SfcnVsYW1hIHRlayBmaXJtYWzEsSBzaXN0ZW1kZSBIQVRBIHZlcmRp'
        'OgogICAgICAgICMgc2lsaW5lbiDDvHllbGlrIHlva3R1IGFtYSBhcnTEsWsgY2FyaWxl'
        'cmkga2FsYW4gZmlybWF5YQogICAgICAgICMgYmHEn2xhbWFrIHNhdMSxciBFS0zEsFlP'
        'Ui4gU2F5xLEga2FyxZ/EsWxhxZ90xLFybWFzxLEgYnUgdGFibG9kYQogICAgICAgICMg'
        'YW5sYW1zxLF6OyBkb8SfcnUgw7Zsw6fDvHQgxZ91OiBoZXIgY2FyaSBUQU0gQsSwUiDD'
        'vHllbGlrbGUga2FsYW4KICAgICAgICAjIGZpcm1hZGEgZ8O2csO8bnPDvG4uIE8gZGEg'
        'YcWfYcSfxLFkYSBzYXnEsWzEsXlvci4KICAgICAgICBpZiBLSVAgPT0gJ3R1bXVudScg'
        'YW5kIHQgPT0gJ2NhcmlfZmlybWEnOgogICAgICAgICAgICBfY2FyaV9hZGV0ID0gc2lt'
        'ZGlfa29ydW5hbi5nZXQoJ2NhcmlsZXInLCAwKQogICAgICAgICAgICBfeWFiYW5jaSA9'
        'IGIuZXhlY3V0ZSh0ZXh0KAogICAgICAgICAgICAgICAgJ1NFTEVDVCBDT1VOVCgqKSBG'
        'Uk9NIGNhcmlfZmlybWEgV0hFUkUgZmlybWFfaWQgPD4gOmYnKSwKICAgICAgICAgICAg'
        'ICAgIHsnZic6IEtBTEFOX0ZJUk1BWydpZCddfSkuc2NhbGFyKCkgb3IgMAogICAgICAg'
        'ICAgICBpZiBfeWFiYW5jaToKICAgICAgICAgICAgICAgIHByaW50KGYiICAg4pyXIGNh'
        'cmlfZmlybWEgICAgICBzaWxpbm1pxZ8gZmlybWF5YSBiYWthbiAiCiAgICAgICAgICAg'
        'ICAgICAgICAgICBmInt0cihfeWFiYW5jaSl9IMO8eWVsaWsga2FsZMSxIikKICAgICAg'
        'ICAgICAgICAgIGhhdGFsaSA9IFRydWUKICAgICAgICAgICAgZWxpZiBzaW1kaSAhPSBf'
        'Y2FyaV9hZGV0OgogICAgICAgICAgICAgICAgcHJpbnQoZiIgICDinJcgY2FyaV9maXJt'
        'YSAgICAgIHt0cihfY2FyaV9hZGV0KX0gY2FyaSBpw6dpbiAiCiAgICAgICAgICAgICAg'
        'ICAgICAgICBmInt0cihzaW1kaSl9IMO8eWVsaWsgdmFyIChiaXJlIGJpciBvbG1hbMSx'
        'KSIpCiAgICAgICAgICAgICAgICBoYXRhbGkgPSBUcnVlCiAgICAgICAgICAgIGVsc2U6'
        'CiAgICAgICAgICAgICAgICBwcmludChmIiAgIOKckyBjYXJpX2Zpcm1hICAgICB7dHIo'
        'c2ltZGkpOj43fSDDvHllbGlrIOKAlCAiCiAgICAgICAgICAgICAgICAgICAgICBmImhl'
        'ciBjYXJpIGthbGFuIGZpcm1hZGEgZ8O2csO8bsO8eW9yIikKICAgICAgICAgICAgY29u'
        'dGludWUKCiAgICAgICAgaWYgS0lQID09ICd0dW11bnUnIGFuZCB0IGluICgnZmlybWEn'
        'LCAna2FzYScsICdiYW5rYScsICd2ZXJpbGVyJyk6CiAgICAgICAgICAgICMgQnUga2lw'
        'dGUgYmlsZXJlayBhemFsxLF5b3JsYXIgKHNpbGluZW4gZmlybWFsYXLEsW4KICAgICAg'
        'ICAgICAgIyBzYXTEsXJsYXLEsSkuIFNhecSxIGXFn2l0bGnEn2kgYmVrbGVubWV6OyBB'
        'UlRNQU1BTEFSSSB2ZQogICAgICAgICAgICAjIGZpcm1hJ27EsW4gMSdlIGlubWVzaSBi'
        'ZWtsZW5pci4KICAgICAgICAgICAgaWYgdCA9PSAnZmlybWEnIGFuZCBzaW1kaSAhPSAx'
        'OgogICAgICAgICAgICAgICAgcHJpbnQoZiIgICDinJcgZmlybWE6IDEgZmlybWEgYmVr'
        'bGVuaXJrZW4ge3NpbWRpfSB2YXIiKQogICAgICAgICAgICAgICAgaGF0YWxpID0gVHJ1'
        'ZQogICAgICAgICAgICBlbGlmIHNpbWRpID4gYmVrbGVuZW46CiAgICAgICAgICAgICAg'
        'ICBwcmludChmIiAgIOKclyB7dDo8MTZzfSBhcnRtxLHFnzoge2Jla2xlbmVufSDihpIg'
        'e3NpbWRpfSIpCiAgICAgICAgICAgICAgICBoYXRhbGkgPSBUcnVlCiAgICAgICAgICAg'
        'IGVsc2U6CiAgICAgICAgICAgICAgICBfbm90ID0gKGYiICjDtm5jZSB7dHIoYmVrbGVu'
        'ZW4pfSwgc2lsaW5lbiBmaXJtYWxhcmxhIGF6YWxkxLEpIgogICAgICAgICAgICAgICAg'
        'ICAgICAgICBpZiBzaW1kaSA8IGJla2xlbmVuIGVsc2UgJycpCiAgICAgICAgICAgICAg'
        'ICBwcmludChmIiAgIOKckyB7dDo8MTZzfSB7dHIoc2ltZGkpOj43fSBrYXnEsXR7X25v'
        'dH0iKQogICAgICAgICAgICBjb250aW51ZQogICAgICAgIGlzYXJldCA9ICfinJMnIGlm'
        'IHNpbWRpID09IGJla2xlbmVuIGVsc2UgJ+KclycKICAgICAgICBpZiBzaW1kaSAhPSBi'
        'ZWtsZW5lbjoKICAgICAgICAgICAgaGF0YWxpID0gVHJ1ZQogICAgICAgIHByaW50KGYi'
        'ICAge2lzYXJldH0ge3Q6PDE2c30ge3RyKHNpbWRpKTo+N30ga2F5xLF0IGtvcnVuZHUg'
        'IgogICAgICAgICAgICAgIGYiKMO2bmNlIHt0cihiZWtsZW5lbil9KSIpCgogICAgIyA0'
        'IMK3IEfDtnLDvG7DvHJsw7zEn8O8IGthbG1heWFuIGNhcmkgdmFyIG3EsT8KICAgICMg'
        'S2FydMSxIG9sdXAgaGnDp2JpciBmaXJtYWRhIGxpc3RlbGVubWV5ZW4gY2FyaSwgInZl'
        'cmkgdmFyIGFtYQogICAgIyB5b2siIGR1cnVtdWR1cjsgc2Vzc2l6IGdlw6dpbG1lbWVs'
        'aS4KICAgIGlmICdjYXJpX2Zpcm1hJyBpbiBtZXZjdXQgYW5kICdjYXJpbGVyJyBpbiBt'
        'ZXZjdXQ6CiAgICAgICAgX2dvcnVubWV6ID0gYi5leGVjdXRlKHRleHQoCiAgICAgICAg'
        'ICAgICdTRUxFQ1QgQ09VTlQoKikgRlJPTSBjYXJpbGVyIGMgV0hFUkUgTk9UIEVYSVNU'
        'UyAnCiAgICAgICAgICAgICcoU0VMRUNUIDEgRlJPTSBjYXJpX2Zpcm1hIGNmIFdIRVJF'
        'IGNmLmNhcmlfaWQgPSBjLmlkKScpKS5zY2FsYXIoKSBvciAwCiAgICAgICAgaWYgX2dv'
        'cnVubWV6OgogICAgICAgICAgICBwcmludChmIiAgIOKaoCB7dHIoX2dvcnVubWV6KX0g'
        'Y2FyaSBoacOnYmlyIGZpcm1hZGEgZ8O2csO8bm3DvHlvciIpCiAgICAgICAgICAgIHBy'
        'aW50KCIgICAgIChrYXJ0IGR1cnV5b3I7IENhcmkgZWtyYW7EsW5kYSBmaXJtYSBrdXR1'
        'bGFyxLFuZGFuIikKICAgICAgICAgICAgcHJpbnQoIiAgICAgIGnFn2FyZXRsZXllcmVr'
        'IGdlcmkgZ2V0aXJlYmlsaXJzaW4pIikKICAgICAgICBlbHNlOgogICAgICAgICAgICBw'
        'cmludCgiICAg4pyTIGhlciBjYXJpIGVuIGF6IGJpciBmaXJtYWRhIGfDtnLDvG7DvHlv'
        'ciIpCgpwcmludCgpCnByaW50KCLilZAiICogNzApCmlmIGhhdGFsaToKICAgIHByaW50'
        'KCIg4pyXIERPxJ5SVUxBTUEgQkHFnkFSSVNJWiDigJQgeWVkZWt0ZW4gZMO2bm1leWkg'
        'ZGXEn2VybGVuZGlyaW4uIikKICAgIHN5cy5leGl0KDEpCnByaW50KCIg4pyTIFNJRklS'
        'TEFNQSBUQU1BTUxBTkRJIikKcHJpbnQoKQpwcmludCgiIENhcmkgZmlybWEga2F5xLF0'
        'bGFyxLFuxLF6IGR1cnV5b3I7IGhhcmVrZXRsZXJpIHPEsWbEsXJsYW5kxLEuIikKcHJp'
        'bnQoIiBCYWtpeWVsZXIgaGFyZWtldGxlcmRlbiBoZXNhcGxhbmTEscSfxLEgacOnaW4g'
        'aGVwc2kgMCBnw7Zyw7xuw7xyLiIpCnByaW50KCkKcHJpbnQoIiBTT05SQUvEsCBBRElN'
        'TEFSOiIpCiMgT3R1cnVtZGFraSBmaXJtYSBzZcOnaW1pIGBzZXNzaW9uYCdkYSBkdXJ1'
        'eW9yLiBTaWxpbmVuIGJpciBmaXJtYQojIHNlw6dpbGl5c2UgZWtyYW5sYXIgYm/Fny9o'
        'YXRhbMSxIGdlbGlyOyBzZXJ2aXNpIHllbmlkZW4gYmHFn2xhdG1hayB2ZQojIHllbmlk'
        'ZW4gZ2lyacWfIHlhcG1hayBzZcOnaW1pIHRhemVsZXIuCnByaW50KCIgICAxKSBzdWRv'
        'IHN5c3RlbWN0bCByZXN0YXJ0IG1pbGVzdG9uZS1lcnAiKQpwcmludCgiICAgICAgc29u'
        'cmEgw6fEsWvEscWfIHlhcMSxcCB5ZW5pZGVuIGdpcmnFnyB5YXAgKGZpcm1hIHNlw6dp'
        'bWkgdGF6ZWxlbmlyKSIpCiMgUjQ6IEtCMSdkZW4gYmVyaSBrYXNhL2JhbmthIFRBTklN'
        'TEFSSSBrb3J1bnV5b3IsIHlhbG5pemNhIGJha2l5ZQojIHNpZmlybGFuaXlvci4gTWVz'
        'YWogInllbmlkZW4gdGFuaW1sYXlpbiIgZGl5b3JkdTsgeWVuaWRlbiB0YW5pbWxhbWFr'
        'CiMgbXVrZXJyZXIga2FzYSBhY2FyZGkuCnByaW50KCIgICAyKSBLYXNhIGHDp8SxbMSx'
        'xZ8gYmFraXllbGVyaW5pIGdpcmluICh0YW7EsW1sYXIgZHVydXlvcikiKQpwcmludCgi'
        'ICAgMykgQXlhcmxhciDihpIgTGlzdGVsZXInaSBnw7Z6ZGVuIGdlw6dpcmluIikKcHJp'
        'bnQoIiAgIDQpIFNhYml0IGdpZGVybGVyaSBnaXJpbiAoa2lyYSwgbWFhxZ8sIFNHSy4u'
        'LikiKQpwcmludCgiICAgNSkgdmVudi9iaW4vcHl0aG9uIGRlZ2lzbWV6bGlrX2RlbmV0'
        'aW0ucHkiKQpwcmludCgi4pWQIiAqIDcwKQo='
    ),
    'firma_denetim.py': (
        'IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwojIOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkAojICBNaWxlc3RvbmUgRVJQIOKA'
        'lCDDh09LTFUgRsSwUk1BIERFTkVUxLBNxLAgIMK3ICBGMeKAk0Y0CiMKIyAgTkVERU4g'
        'VkFSOgojICAgIMOHb2tsdSBmaXJtYSAoTUYx4oCTTUY3KSB0ZWsgYmlyIMWfZXllIGRh'
        'eWFuxLF5b3I6IGhlciBzb3JndW51bgojICAgIEFLVMSwRiBGxLBSTUFZQSBzw7x6w7xs'
        'bWVzaS4gU8O8emdlw6cgYGRvX29ybV9leGVjdXRlYCBrYW5jYXPEsW5kYSwKIyAgICB5'
        'YXptYSBkYW1nYXPEsSBgYmVmb3JlX2ZsdXNoYCd0YSDigJQgaWtpc2kgZGUgT1RPTUFU'
        'xLBLLiBPdG9tYXRpawojICAgIG9sYW4gxZ9leSBTRVNTxLBaIGJvenVsdXI6CiMKIyAg'
        'ICAgIOKAoiBZZW5pIGJpciBtb2RlbCBgRmlybWFLYXBzYW1saWAgbWl4aW4naW5pIGFs'
        'bWF6c2EsIG8gdGFibG8KIyAgICAgICAgSEVSIEbEsFJNQURBIEfDllLDnE7DnFIuIEhh'
        'dGEgdmVybWV6OyBBIGZpcm1hc8SxbsSxbiBtw7zFn3RlcmlzaQojICAgICAgICBCIGZp'
        'cm1hc8SxbsSxbiBla3JhbsSxbmRhIMOnxLFrYXIuIEJ1bnUgZmFyayBldG1lbmluIHRl'
        'ayB5b2x1CiMgICAgICAgIGJpcmluaW4gZWtyYW5hIGJha8SxcCAiYnUgYmVuaW0ga2F5'
        'ZMSxbSBkZcSfaWwiIGRlbWVzaS4KIwojICAgICAg4oCiIFllbmkgYmlyIHRhYmxvIGBz'
        'aWZpcmxhMi5weWAneWUgeWF6xLFsbWF6c2EsIHPEsWbEsXJsYW1hCiMgICAgICAgIGJl'
        'dGnEn2kgw4dBTEnFnk1BWUkgUkVEREVERVIuIEJ1IGl5aSBoYWJlciDigJQgYW1hIHJl'
        'ZGRpCiMgICAgICAgIMO2xJ9yZW5kacSfaW4gYW4sIHPEsWbEsXJsYW1hayBpc3RlZGnE'
        'n2luIGFuZMSxci4gxLBraSBrZXogeWHFn2FuZMSxCiMgICAgICAgIChSNDoga2FsZW1f'
        'a2Fyc2lsYW1hLCBSNTogZmlybWEgKyBjYXJpX2Zpcm1hKS4gUHVzaAojICAgICAgICBh'
        'bsSxbmRhIMO2xJ9yZW5tZWssIHPEsWbEsXJsYW1hIGFuxLFuZGEgw7bEn3Jlbm1la3Rl'
        'biBpeWlkaXIuCiMKIyAgICAgIOKAoiBgZmlybWFfYXRsYSgpYCBzw7x6Z2VjaSBLQVBB'
        'VElSLiBZZXJpbmRlIGJpciDDp8Sxa8SxxZ8ga2FwxLFzxLEKIyAgICAgICAgKGZpcm1h'
        'IGxpc3Rlc2luaW4ga2VuZGlzaSBzw7x6w7xsZW1leiksIGFtYSBoZXIgeWVuaQojICAg'
        'ICAgICBrdWxsYW7EsW3EsSBiaWxpbsOnbGkgYmlyIGthcmFyIG9sbWFsxLE7IHNlc3Np'
        'emNlIGVrbGVuZW4gYmlyCiMgICAgICAgIHRhbmVzaSB0w7xtIGZpcm1hbGFyxLFuIHZl'
        'cmlzaW5pIHRlayBla3JhbmEgZMO2a2VyLgojCiMgIETDllJUIEVLU0VOOgojICAgIEYx'
        'ICBTxLFmxLFybGFtYSBrYXBzYW3EsSAgIOKAlCBoZXIgdGFibG8gc2lmaXJsYTIucHkn'
        'ZGUgc8SxbsSxZmzEsSBtxLEKIyAgICBGMiAgRmlybWEga2Fwc2FtxLEgICAgICAg4oCU'
        'IGhlciB0YWJsb2RhIGZpcm1hX2lkIHZhciBtxLEKIyAgICBGMyAgw4fEsWvEscWfIGth'
        'cMSxbGFyxLEgICAgICDigJQgZmlybWFfYXRsYSgpIGt1bGxhbsSxbWxhcsSxIGfDtnpk'
        'ZW4gZ2XDp2lyaWxkaSBtaQojICAgIEY0ICBIYW0gU1FMIHPDvHpnZWNpICAgICDigJQg'
        'dGV4dCgpIHNvcmd1bGFyxLEgZmlybWFfaWQneWkgYXRsxLF5b3IgbXUKIwojICBTYWx0'
        'IG9rdW51ci4gVmVyaXRhYmFuxLEgR0VSRUtNRVog4oCUIG1vZGVsIHRhbsSxbcSxIHZl'
        'IGtheW5hayBrb2QKIyAgw7x6ZXJpbmRlbiDDp2FsxLHFn8SxciwgYnUgecO8emRlbiBw'
        'dXNoIGthcMSxc8SxbmRhIChnb25kZXIuc2gpIGfDvHZlbmxlCiMgIGtvxZ90dXJ1bGFi'
        'aWxpci4KIwojICBLVUxMQU5JTSAocHJvamUga2xhc8O2csO8bmRlKToKIyAgICAgIHZl'
        'bnYvYmluL3B5dGhvbiBmaXJtYV9kZW5ldGltLnB5CiMKIyAgw4dJS0nFniBLT0RVOiBi'
        'dWxndSB2YXJzYSAxLCB0ZW1penNlIDAuCiMg4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCmltcG9ydCBpbwppbXBvcnQg'
        'b3MKaW1wb3J0IHJlCmltcG9ydCBzeXMKZnJvbSBwYXRobGliIGltcG9ydCBQYXRoCgpL'
        'T0sgPSBQYXRoKCcuJykucmVzb2x2ZSgpCmlmIG5vdCAoS09LIC8gJ2ZsYXNrX2FwcC5w'
        'eScpLmV4aXN0cygpOgogICAgcHJpbnQoIkhBVEE6IGZsYXNrX2FwcC5weSBidSBrbGFz'
        'w7ZyZGUgeW9rLiBQcm9qZSBrbGFzw7Zyw7xuZGUgw6dhbMSxxZ90xLFyxLFuLiIpCiAg'
        'ICBzeXMuZXhpdCgxKQoKb3MuZW52aXJvbi5zZXRkZWZhdWx0KCdNSUxFU1RPTkVfQUNJ'
        'TElTX0FUTEEnLCAnMScpCgojIOKUgOKUgCBWRVLEsFRBQkFOSU5JIEtBU1RFTiBERVZS'
        'RSBEScWeSSBCSVJBS0lZT1JVWiDilIDilIAKIyBCdSBhcmHDpyBNT0RFTCBUQU5JTUlO'
        'SSB2ZSBLQVlOQUsgS09EVSBva3VyOyB0ZWsgc2F0xLFyIHZlcmkKIyBva3VtYXouIGAu'
        'ZW52YGRla2kgZ2Vyw6dlayBhZHJlc2UgYmHEn2xhbm1hc8SxbmEgaXppbiB2ZXJpcnNl'
        'aywKIyBQb3N0Z3JlU1FMIGthcGFsxLF5a2VuIHlhIGRhIHPDvHLDvGPDvCBla3Npa2tl'
        'biBpbXBvcnQgcGF0bGFyIHZlCiMgcHVzaCBrYXDEsXPEsSAoZ29uZGVyLnNoKSBidSBk'
        'ZW5ldGltaSAiw6dhbMSxxZ90xLFyxLFsYW1hZMSxIiBzYXnEsXAKIyBhdGxhci4gT3lz'
        'YSBhdGxhbm1hbWFzxLEgZ2VyZWtlbiB0YW0gZGEgYnU6IGtvZCBkZW5ldGltaSwKIyB2'
        'ZXJpdGFiYW7EsW7EsW4gZHVydW11eWxhIGlsZ2lzaSBvbG1heWFuIGJpciDFn2V5Lgoj'
        'CiMgc2V0ZGVmYXVsdCBZRVRNRVog4oCUIG9ydGFtZGEgREFUQUJBU0VfVVJMIHphdGVu'
        'IGRvbHUgb2x1ci4KIyDDnHplcmluZSB5YXrEsXlvcnV6Lgpvcy5lbnZpcm9uWydEQVRB'
        'QkFTRV9VUkwnXSA9ICdzcWxpdGU6Ly8vOm1lbW9yeTonCnN5cy5wYXRoLmluc2VydCgw'
        'LCBzdHIoS09LKSkKCnRyeToKICAgIGltcG9ydCBmbGFza19hcHAgYXMgX2ZhICAjIG5v'
        'cWE6IEY0MDEKICAgIGZyb20gbW9kZWxzIGltcG9ydCBkYiBhcyBfZGIKZXhjZXB0IEV4'
        'Y2VwdGlvbiBhcyBfZToKICAgIHByaW50KGYiSEFUQTogbW9kZWwgecO8a2xlbmVtZWRp'
        'OiB7X2V9IikKICAgIHN5cy5leGl0KDEpCgpUQUJMT0xBUiA9IHt0Lm5hbWU6IHtjLm5h'
        'bWUgZm9yIGMgaW4gdC5jfSBmb3IgdCBpbiBfZGIubWV0YWRhdGEuc29ydGVkX3RhYmxl'
        'c30KS0FZTkFLID0gaW8ub3BlbihLT0sgLyAnZmxhc2tfYXBwLnB5JywgZW5jb2Rpbmc9'
        'J3V0Zi04JykucmVhZCgpClNJRklSTEEgPSBLT0sgLyAnc2lmaXJsYTIucHknCgpidWxn'
        'dSA9IDAKcHJpbnQoIuKVkCIgKiA3MCkKcHJpbnQoIiBNSUxFU1RPTkUgRVJQIOKAlCDD'
        'h09LTFUgRsSwUk1BIERFTkVUxLBNxLAiKQpwcmludCgi4pWQIiAqIDcwKQpwcmludChm'
        'IiBNb2RlbCAgICAgIDoge2xlbihUQUJMT0xBUil9IHRhYmxvIikKcHJpbnQoKQoKIyDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZAKIyAgRjEgwrcgU0lGSVJMQU1BIEtBUFNBTUkKIyDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZAKcHJpbnQoIuKU'
        'gCIgKiA3MCkKcHJpbnQoIiBGMSDCtyBTSUZJUkxBTUEgS0FQU0FNSSAgIFtTRVNTxLBa'
        'IEtBTElOVEkgLyBSRURERUTEsExFTiBTSUZJUkxBTUFdIikKcHJpbnQoIuKUgCIgKiA3'
        'MCkKaWYgbm90IFNJRklSTEEuZXhpc3RzKCk6CiAgICBwcmludCgiICAg4pqgIHNpZmly'
        'bGEyLnB5IHlvayDigJQgYnUgZWtzZW4gYXRsYW5kxLEiKQplbHNlOgogICAgX3MgPSBp'
        'by5vcGVuKFNJRklSTEEsIGVuY29kaW5nPSd1dGYtOCcpLnJlYWQoKQoKICAgIGRlZiBf'
        'bGlzdGVfY2lrYXIoYWQpOgogICAgICAgICIiImBBRCA9IFsgLi4uIF1gIHlhIGRhIGBB'
        'RCA9IHsgLi4uIH1gIGnDp2luZGVraSB0xLFybmFrbMSxIGFkbGFyLiIiIgogICAgICAg'
        'IG0gPSByZS5zZWFyY2goYWQgKyByJ1xzKj1ccypbXFt7XSguKj8pXltcXX1dJywgX3Ms'
        'IHJlLlMgfCByZS5NKQogICAgICAgIGlmIG5vdCBtOgogICAgICAgICAgICByZXR1cm4g'
        'Tm9uZQogICAgICAgIGdvdmRlID0gbS5ncm91cCgxKQogICAgICAgICMgWW9ydW0gc2F0'
        'xLFybGFyxLFuxLEgYXQ6IHRhYmxvIGFkxLEgeW9ydW0gacOnaW5kZSBnZcOnaXlvcnNh'
        'CiAgICAgICAgIyBzxLFuxLFmbGFuZMSxcsSxbG3EscWfIFNBWUlMTUFaLgogICAgICAg'
        'IGdvdmRlID0gJ1xuJy5qb2luKHMgZm9yIHMgaW4gZ292ZGUuc3BsaXQoJ1xuJykKICAg'
        'ICAgICAgICAgICAgICAgICAgICAgICBpZiBub3Qgcy5sc3RyaXAoKS5zdGFydHN3aXRo'
        'KCcjJykpCiAgICAgICAgcmV0dXJuIHNldChyZS5maW5kYWxsKHIiJyhbYS16X11bYS16'
        'MC05X10qKSciLCBnb3ZkZSkpCgogICAgX3NpbCA9IF9saXN0ZV9jaWthcignU0lMSU5F'
        'Q0VLX1RBQkxPTEFSJykKICAgIF9rb3IgPSBfbGlzdGVfY2lrYXIoJ0tPUlVOQU4nKQog'
        'ICAgaWYgX3NpbCBpcyBOb25lIG9yIF9rb3IgaXMgTm9uZToKICAgICAgICBwcmludCgi'
        'ICAg4pyXIHNpZmlybGEyLnB5J2RlIFNJTElORUNFS19UQUJMT0xBUiAvIEtPUlVOQU4g'
        'bGlzdGVzaSIpCiAgICAgICAgcHJpbnQoIiAgICAgb2t1bmFtYWTEsSDigJQgYmnDp2lt'
        'IGRlxJ9pxZ9tacWfIG9sYWJpbGlyLiIpCiAgICAgICAgYnVsZ3UgKz0gMQogICAgZWxz'
        'ZToKICAgICAgICBfYmlsaW5lbiA9IF9zaWwgfCBfa29yCiAgICAgICAgX2thY2FuID0g'
        'c29ydGVkKHQgZm9yIHQgaW4gVEFCTE9MQVIgaWYgdCBub3QgaW4gX2JpbGluZW4pCiAg'
        'ICAgICAgX2hheWFsZXQgPSBzb3J0ZWQodCBmb3IgdCBpbiBfYmlsaW5lbiBpZiB0IG5v'
        'dCBpbiBUQUJMT0xBUikKICAgICAgICBpZiBfa2FjYW46CiAgICAgICAgICAgIGZvciB0'
        'IGluIF9rYWNhbjoKICAgICAgICAgICAgICAgIHByaW50KGYiICAg4pyXIHt0fSDigJQg'
        'c2lmaXJsYTIucHknZGUgbmUgS09SVU5BTiBuZSBTxLBMxLBORUNFSyIpCiAgICAgICAg'
        'ICAgIHByaW50KCkKICAgICAgICAgICAgcHJpbnQoIiAgIOKGkiBTxLFmxLFybGFtYSBi'
        'dSB0YWJsb3l1IGfDtnLDvG5jZSDDh0FMScWeTUFZSSBSRURERURFUi4iKQogICAgICAg'
        'ICAgICBwcmludCgiICAgICBNb2RlbGkgZWtsZXllbiB5YW1hIHNpZmlybGEyLnB5J3lp'
        'IGRlIGfDvG5jZWxsZW1lbGk6IikKICAgICAgICAgICAgcHJpbnQoIiAgICAgICBpxZ9s'
        'ZW0gdmVyaXNpICAgIOKGkiBTSUxJTkVDRUtfVEFCTE9MQVIiKQogICAgICAgICAgICBw'
        'cmludCgiICAgICAgIGFuYSB2ZXJpL3RhbsSxbSAg4oaSIEtPUlVOQU4gKGdlcmVrw6dl'
        'c2l5bGUpIikKICAgICAgICAgICAgYnVsZ3UgKz0gbGVuKF9rYWNhbikKICAgICAgICBp'
        'ZiBfaGF5YWxldDoKICAgICAgICAgICAgcHJpbnQoZiIgICDimqAgbW9kZWxkZSBvbG1h'
        'eWFuIHRhYmxvIGFkxLE6IHsnLCAnLmpvaW4oX2hheWFsZXQpfSIpCiAgICAgICAgICAg'
        'IHByaW50KCIgICAgICh6YXJhcnPEsXo7IHRhYmxvIGthbGTEsXLEsWxtxLHFn3NhIGxp'
        'c3RlZGVuIGRlIGTDvMWfc8O8bikiKQogICAgICAgIGlmIG5vdCBfa2FjYW46CiAgICAg'
        'ICAgICAgIHByaW50KGYiICAg4pyTIHRlbWl6IOKAlCB7bGVuKFRBQkxPTEFSKX0gdGFi'
        'bG9udW4gaGVwc2kgc8SxbsSxZmxhbmTEsXLEsWxtxLHFnyIpCgojIOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkAojICBG'
        'MiDCtyBGxLBSTUEgS0FQU0FNSQojIOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkAojCiMgZmlybWFfaWQnc2kgT0xNQVlB'
        'TiB0YWJsbyBoZXIgZmlybWFkYSBnw7Zyw7xuw7xyLiBCdSBiYXplbiBET8SeUlU6CiMg'
        'Y2FyaSBrYXJ0xLEgb3J0YWsgKHZlcmdpIG5vLCBhZHJlcyB0ZWsgeWVyZGUgZHVydXI7'
        'IGfDtnLDvG7DvHJsw7zEn8O8CiMgY2FyaV9maXJtYSBiZWxpcmxlciksIGt1ciBhcsWf'
        'aXZpIG9ydGFrLCBrdWxsYW7EsWPEsWxhciBvcnRhaywgZmlybWEKIyB0YWJsb3N1bnVu'
        'IGtlbmRpc2kgZGUgZG/En2FsIG9sYXJhayBmaXJtYXPEsXouCiMKIyBBbWEgYnUgbGlz'
        'dGV5ZSBiaWxtZWRlbiBla2xlbmVuIGJpciB0YWJsbyBTRVNTxLBaIFNJWklOVEkgb2x1'
        'ci4KIyBPIHnDvHpkZW4gbGlzdGUgQlVSQURBLCBhw6fEsWvDp2EgeWF6xLFsxLE6IHll'
        'bmkgYmlyIHRhYmxvIGZpcm1hc8SxegojIGthbGFjYWtzYSBidXJheWEgZ2VyZWvDp2Vz'
        'aXlsZSB5YXrEsWxtYWzEsS4KRklSTUFTSVpfQkVLTEVORU4gPSB7CiAgICAnZmlybWEn'
        'OiAnZmlybWFsYXLEsW4ga2VuZGlzaScsCiAgICAnY2FyaV9maXJtYSc6ICfDvHllbGlr'
        'IHRhYmxvc3Ug4oCUIGZpcm1hX2lkIHRhxZ/EsXIgYW1hIGthcHNhbSBkxLHFn8SxIHNh'
        'ecSxbG1heicsCiAgICAnY2FyaWxlcic6ICdjYXJpIGthcnTEsSBPUlRBSzsgZ8O2csO8'
        'bsO8cmzDvMSfw7wgY2FyaV9maXJtYSBiZWxpcmxlciAoTUYyKScsCiAgICAnY2FyaV9r'
        'aXNpJzogJ2Nhcmkga2FydMSxbsSxbiBwYXLDp2FzxLEg4oCUIGthcnQgb3J0YWtzYSBr'
        'acWfaWxlcmkgZGUgb3J0YWsnLAogICAgJ2NhcmlfZXJpc2ltJzogJ2t1bGxhbsSxY8Sx'
        '4oaUY2FyaSBlcmnFn2ltIGlzdGlzbmFzxLEsIGZpcm1hZGFuIGJhxJ/EsW1zxLF6JywK'
        'ICAgICdkb3Zpel9rdXInOiAnVENNQiBrdXIgYXLFn2l2aSDigJQgaGVya2VzIGnDp2lu'
        'IGF5bsSxJywKICAgICdrdWxsYW5pY2lsYXInOiAna3VsbGFuxLFjxLFsYXIgdMO8bSBm'
        'aXJtYWxhcmRhIGF5bsSxIGtpxZ9pbGVyJywKICAgICdhbGVtYmljX3ZlcnNpb24nOiAn'
        'xZ9lbWEgc8O8csO8bSBkYW1nYXPEsScsCn0KcHJpbnQoKQpwcmludCgi4pSAIiAqIDcw'
        'KQpwcmludCgiIEYyIMK3IEbEsFJNQSBLQVBTQU1JICAgW1NFU1PEsFogU0laSU5USV0i'
        'KQpwcmludCgi4pSAIiAqIDcwKQpfZmlybWFzaXogPSBzb3J0ZWQodCBmb3IgdCwgcyBp'
        'biBUQUJMT0xBUi5pdGVtcygpIGlmICdmaXJtYV9pZCcgbm90IGluIHMpCl9iZWtsZW5t'
        'ZXllbiA9IFt0IGZvciB0IGluIF9maXJtYXNpeiBpZiB0IG5vdCBpbiBGSVJNQVNJWl9C'
        'RUtMRU5FTl0KaWYgX2Jla2xlbm1leWVuOgogICAgZm9yIHQgaW4gX2Jla2xlbm1leWVu'
        'OgogICAgICAgIHByaW50KGYiICAg4pyXIHt0fSDigJQgZmlybWFfaWQgWU9LLCBoZXIg'
        'ZmlybWFkYSBnw7Zyw7xuw7xyIikKICAgIHByaW50KCkKICAgIHByaW50KCIgICDihpIg'
        'VGFibG8gacWfbGVtIHZlcmlzaSB0dXR1eW9yc2EgYEZpcm1hS2Fwc2FtbGlgIG1peGlu'
        'J2luaSIpCiAgICBwcmludCgiICAgICBhbG1hbMSxIChtb2RlbHMucHkpLiBHZXLDp2Vr'
        'dGVuIG9ydGFrc2EgYnUgZG9zeWFkYWtpIikKICAgIHByaW50KCIgICAgIEZJUk1BU0la'
        'X0JFS0xFTkVOIGxpc3Rlc2luZSBHRVJFS8OHRVPEsFlMRSB5YXrEsW4g4oCUIikKICAg'
        'IHByaW50KCIgICAgIG9ydGFrbMSxayBiaWxpbsOnbGkgYmlyIGthcmFyIG9sbWFsxLEs'
        'IHZhcnNhecSxbGFuIGRlxJ9pbC4iKQogICAgYnVsZ3UgKz0gbGVuKF9iZWtsZW5tZXll'
        'bikKZWxzZToKICAgIHByaW50KGYiICAg4pyTIHRlbWl6IOKAlCBmaXJtYXPEsXoge2xl'
        'bihfZmlybWFzaXopfSB0YWJsb251biBoZXBzaSBiZWtsZW5lbiIpCiAgICBmb3IgdCBp'
        'biBfZmlybWFzaXo6CiAgICAgICAgcHJpbnQoZiIgICAgICAge3Q6PDE2c30ge0ZJUk1B'
        'U0laX0JFS0xFTkVOW3RdfSIpCgojIERhbWdhIHRhcmFmxLE6IGZpcm1hX2lkIE5PVCBO'
        'VUxMIG9sbWFsxLEuIE51bGxhYmxlIGthbMSxcnNhIGRhbWdhCiMgYXRsYW5kxLHEn8Sx'
        'bmRhIHNhdMSxciBIxLDDh0LEsFIgZmlybWF5YSBhaXQgb2xtYXogdmUgaGnDp2JpciBl'
        'a3JhbmRhCiMgZ8O2csO8bm1leiDigJQgImtheWRldHRpbSwga2F5Ym9sZHUiIMWfaWvD'
        'onlldGkuCk5VTExBQkxFX0JFS0xFTkVOID0gewogICAgJ2F1ZGl0X2xvZyc6ICdkZW5l'
        'dGltIGl6aTogc2lsaW5lbiBmaXJtYW7EsW4gaXppIE5VTExcJ2Egw6dla2lsaXIsIGl6'
        'IGthbMSxcicsCiAgICAndmVyaWxlcic6ICdOVUxMID0gT1JUQUsgbGlzdGUgc2F0xLFy'
        'xLEgKGNpbnMsIHnDvHpleSwgw7xsa2UpJywKfQpfbnVsbGFibGUgPSBbXQpmb3IgdCBp'
        'biBfZGIubWV0YWRhdGEuc29ydGVkX3RhYmxlczoKICAgIGlmICdmaXJtYV9pZCcgaW4g'
        'VEFCTE9MQVIuZ2V0KHQubmFtZSwgc2V0KCkpIGFuZCB0LmNbJ2Zpcm1hX2lkJ10ubnVs'
        'bGFibGU6CiAgICAgICAgaWYgdC5uYW1lIG5vdCBpbiBOVUxMQUJMRV9CRUtMRU5FTjoK'
        'ICAgICAgICAgICAgX251bGxhYmxlLmFwcGVuZCh0Lm5hbWUpCmlmIF9udWxsYWJsZToK'
        'ICAgIHByaW50KCkKICAgIGZvciB0IGluIHNvcnRlZChfbnVsbGFibGUpOgogICAgICAg'
        'IHByaW50KGYiICAg4pyXIHt0fSDigJQgZmlybWFfaWQgbnVsbGFibGU7IGRhbWdhIGF0'
        'bGFuxLFyc2Egc2F0xLFyIikKICAgICAgICBwcmludCgiICAgICBoacOnYmlyIGZpcm1h'
        'ZGEgZ8O2csO8bm1leiAoc2Vzc2l6IGthecSxcCkiKQogICAgYnVsZ3UgKz0gbGVuKF9u'
        'dWxsYWJsZSkKCiMg4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCiMgIEYzIMK3IMOHSUtJxZ4gS0FQSUxBUkkKIyDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZAKIwojIGB3aXRoIGZpcm1hX2F0bGEoKTpgIHPDvHpnZWNpIEtBUEFUSVIuIEhlciBr'
        'dWxsYW7EsW3EsSBnZXJla2xpIOKAlCBhbWEKIyBoZXIga3VsbGFuxLFtxLEgZGEgZ8O2'
        'emRlbiBnZcOnaXJpbG1pxZ8gb2xtYWzEsS4gU2F5xLEgYXJ0YXJzYSBkZW5ldGltCiMg'
        'dXlhcsSxcjsgeWVuaSBrdWxsYW7EsW0gYmlsaW7Dp2xpeXNlIGJ1IHNhecSxecSxIGfD'
        'vG5jZWxsZXlpbi4KQVRMQV9CRUtMRU5FTiA9IDEyCnByaW50KCkKcHJpbnQoIuKUgCIg'
        'KiA3MCkKcHJpbnQoIiBGMyDCtyDDh0lLScWeIEtBUElMQVJJIChmaXJtYV9hdGxhKSAg'
        'IFtHw5ZaREVOIEdFw4fEsFLEsExNRU3EsMWeIEFUTEFNQV0iKQpwcmludCgi4pSAIiAq'
        'IDcwKQpfYXRsYSA9IFsoaSArIDEsIHMuc3RyaXAoKSkgZm9yIGksIHMgaW4gZW51bWVy'
        'YXRlKEtBWU5BSy5zcGxpdCgnXG4nKSkKICAgICAgICAgaWYgJ2Zpcm1hX2F0bGEoKScg'
        'aW4gcyBhbmQgJ2RlZiBmaXJtYV9hdGxhJyBub3QgaW4gc10KcHJpbnQoZiIgICB7bGVu'
        'KF9hdGxhKX0ga3VsbGFuxLFtIChiZWtsZW5lbiB7QVRMQV9CRUtMRU5FTn0pIikKaWYg'
        'bGVuKF9hdGxhKSA+IEFUTEFfQkVLTEVORU46CiAgICBwcmludCgpCiAgICBmb3Igbiwg'
        'cyBpbiBfYXRsYToKICAgICAgICBwcmludChmIiAgICAge246PjZ9ICB7c1s6NjJdfSIp'
        'CiAgICBwcmludCgpCiAgICBwcmludCgiICAg4pyXIEJla2xlbmVuZGVuIGZhemxhLiBZ'
        'ZW5pIGhlciBhdGxhbWEgc8O8emdlY2kga2FwYXTEsXI6IikKICAgIHByaW50KCIgICAg'
        'IG8gYmxvayBpw6dpbmRla2kgc29yZ3VsYXIgVMOcTSBmaXJtYWxhcsSxbiB2ZXJpc2lu'
        'aSBnw7Zyw7xyLiIpCiAgICBwcmludCgiICAgICBCaWxpbsOnbGl5c2UgZmlybWFfZGVu'
        'ZXRpbS5weSdkZSBBVExBX0JFS0xFTkVOJ2kgZ8O8bmNlbGxleWluLiIpCiAgICBidWxn'
        'dSArPSAxCmVsaWYgbGVuKF9hdGxhKSA8IEFUTEFfQkVLTEVORU46CiAgICBwcmludChm'
        'IiAgIOKaoCBCZWtsZW5lbmRlbiBheiDigJQgYmlyIMOnxLFrxLHFnyBrYXDEsXPEsSBr'
        'YWxrbcSxxZ8gb2xhYmlsaXIuIikKICAgIHByaW50KCIgICAgIEZpcm1hIGxpc3Rlc2kv'
        'w7x5ZWxpayBla3JhbmxhcsSxIGjDomzDoiDDp2FsxLHFn8SxeW9yIG11IGJha8Sxbiwi'
        'KQogICAgcHJpbnQoIiAgICAgc29ucmEgQVRMQV9CRUtMRU5FTidpIGTDvMWfw7xyw7xu'
        'LiIpCmVsc2U6CiAgICBwcmludCgiICAg4pyTIHRlbWl6IOKAlCBrdWxsYW7EsW0gc2F5'
        'xLFzxLEgZ8O2emRlbiBnZcOnaXJpbG1pxZ8gbGlzdGV5bGUgYXluxLEiKQoKIyDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZAKIyAgRjQgwrcgSEFNIFNRTCBTw5xaR0VDxLAKIyDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZAKIwojIE9STSBzw7x6'
        'Z2VjaSBgZG9fb3JtX2V4ZWN1dGVgIGthbmNhc8SxbmRhIOKAlCBZQUxOSVpDQSBPUk0g'
        'c29yZ3VsYXLEsW7EsQojIHlha2FsYXIuIGB0ZXh0KC4uLilgIGlsZSB5YXrEsWxhbiBo'
        'YW0gU1FMIGthbmNhZGFuIEdFw4dNRVo7IGZpcm1hCiMgc8O8emdlY2luaSBlbGxlIGtv'
        'eW1hayBnZXJla2lyLiBLb3l1bG1henNhIHNvcmd1IHTDvG0gZmlybWFsYXLEsQojIG9r'
        'dXIveWF6YXIgdmUgaGnDp2JpciBoYXRhIHZlcm1lei4KIwojIEZpcm1hIHRhYmxvc3Vu'
        'dW4gS0VORMSwU8SwTsSwIG9rdXlhbiBoYW0gU1FMIGJla2xlbmVuOiBraW1saWsgw7xy'
        'ZXRpbWkKIyB2ZSB2YXJzYXnEsWxhbiBmaXJtYSBhcmFtYXPEsSB6YXRlbiBzw7x6Z2Vj'
        'aW4gREnFnklOREEgb2xtYWsgem9ydW5kYQojIChPUk0gc29yZ3VzdSBhw6dtYWsga2Fu'
        'Y2F5xLEgeWVuaWRlbiB0ZXRpa2xlcmRpKS4KSEFNX1NRTF9CRUtMRU5FTiA9IHsKICAg'
        'ICMgZGVzZW4gcGFyw6dhc8SxIOKGkiBORURFTiBzw7x6Z2XDp3NpeiBvbG1hc8SxIERP'
        'xJ5SVQogICAgJ0ZST00gZmlybWEnOiAnZmlybWEgdGFibG9zdW51biBrZW5kaXNpIOKA'
        'lCBzw7x6Z2VjaW4gZMSxxZ/EsSBvbG1hbMSxJywKICAgICdGUk9NIGNhcmlsZXInOiAn'
        'Y2FyaSBrYXJ0xLEgb3J0YWs7IGfDtnLDvG7DvHJsw7xrIGNhcmlfZmlybWEgaWxlJywK'
        'ICAgICdGUk9NIGNhcmlfZmlybWEnOiAnw7x5ZWxpayB0YWJsb3N1LCBmaXJtYV9pZCB6'
        'YXRlbiBrb8WfdWxkYScsCiAgICAnRlJPTSBjYXJpX2hhcmVrZXQgV0hFUkUgaWQgTElL'
        'RSc6ICdraW1saWsgc2F5YWPEsTogYmVuemVyc2l6bGlrICcKICAgICAgICAgICAgICAg'
        'ICAgICAgICAgICAgICAgICAgICAgICAgJ1TDnE0gZmlybWFsYXIgacOnaW4gYXJhbsSx'
        'cicsCiAgICAnRlJPTSBhdWRpdF9sb2cnOiAnZGVuZXRpbSBpemkgecO2bmV0aW1pJywK'
        'ICAgICdVUERBVEUgcHJvZm9ybWEgU0VUJzogJ2HDp8SxbMSxxZ8gZ8O2w6fDvCAoU0Qy'
        'KSBnZXJpeWUgZMO2bsO8ayBkb2xkdXJtYSDigJQgJwogICAgICAgICAgICAgICAgICAg'
        'ICAgICAgICAnaGVyIGZpcm1hbsSxbiBzYXTEsXLEsW5hIHV5Z3VsYW5tYWzEsScsCiAg'
        'ICAnV0hFUkUgY2FyaV9pZCA9IDpjIExJTUlUIDEnOiAnYXJ0xLFrIGNhcmkgdGFyYW1h'
        'c8SxIChNRjQpOiBjYXJpIEJBxZ5LQSAnCiAgICAgICAgICAgICAgICAgICAgICAgICAg'
        'ICAgICAgICAnZmlybWFkYSBrYXnEsXRsxLF5c2Egc2lsaW5tZW1lbGksICcKICAgICAg'
        'ICAgICAgICAgICAgICAgICAgICAgICAgICAgICdvIHnDvHpkZW4ga2FzdGVuIHPDvHpn'
        'ZcOnc2l6JywKfQpwcmludCgpCnByaW50KCLilIAiICogNzApCnByaW50KCIgRjQgwrcg'
        'SEFNIFNRTCBTw5xaR0VDxLAgICBbU8OcWkdFw4cgQVRMQVlBTiBTT1JHVV0iKQpwcmlu'
        'dCgi4pSAIiAqIDcwKQpfZmlybWFfa2Fwc2FtbGkgPSB7dCBmb3IgdCwgcyBpbiBUQUJM'
        'T0xBUi5pdGVtcygpCiAgICAgICAgICAgICAgICAgICBpZiAnZmlybWFfaWQnIGluIHMg'
        'YW5kIHQgIT0gJ2NhcmlfZmlybWEnfQpfYmxva2xhciA9IHJlLmZpbmRhbGwoCiAgICBy'
        'InRleHRcKFxzKig/OmY/cj8nJycoLio/KScnJ3xmP3I/XCJcIlwiKC4qPylcIlwiXCJ8'
        'Zj9yPycoW14nXSopJyIKICAgIHIifGY/cj9cIihbXlwiXSopXCIpIiwgS0FZTkFLLCBy'
        'ZS5TKQpfc3VwaGVsaSA9IFtdCmZvciBfZyBpbiBfYmxva2xhcjoKICAgIF9xID0gbmV4'
        'dCgoeCBmb3IgeCBpbiBfZyBpZiB4KSwgJycpCiAgICBfdGVrID0gJyAnLmpvaW4oX3Eu'
        'c3BsaXQoKSkKICAgIGlmIG5vdCByZS5zZWFyY2gocidcYihTRUxFQ1R8VVBEQVRFfERF'
        'TEVURSlcYicsIF90ZWssIHJlLkkpOgogICAgICAgIGNvbnRpbnVlCiAgICBpZiAnZmly'
        'bWFfaWQnIGluIF90ZWs6CiAgICAgICAgY29udGludWUgICAgICAgICAgICAgICAgICAg'
        'ICAgICAgICAgICAgICAgICMgc8O8emdlw6cgZWxsZSBrb25tdcWfCiAgICBpZiBhbnko'
        'ayBpbiBfdGVrIGZvciBrIGluIEhBTV9TUUxfQkVLTEVORU4pOgogICAgICAgIGNvbnRp'
        'bnVlICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAjIGdlcmVrw6dlc2kg'
        'eWF6xLFsxLEKICAgICMgRmlybWEga2Fwc2FtxLFuZGFraSBiaXIgdGFibG95YSBtxLEg'
        'ZG9rdW51eW9yPwogICAgX2Rva3VuZHVndSA9IFt0IGZvciB0IGluIF9maXJtYV9rYXBz'
        'YW1saQogICAgICAgICAgICAgICAgICBpZiByZS5zZWFyY2gocidcYicgKyByZS5lc2Nh'
        'cGUodCkgKyByJ1xiJywgX3RlaykKICAgICAgICAgICAgICAgICAgb3IgJ3tfdC5uYW1l'
        'fScgaW4gX3RlayBvciAne190bn0nIGluIF90ZWtdCiAgICBpZiBfZG9rdW5kdWd1Ogog'
        'ICAgICAgIF9zdXBoZWxpLmFwcGVuZCgoX3Rla1s6OTBdLCBzb3J0ZWQoX2Rva3VuZHVn'
        'dSlbOjNdKSkKaWYgX3N1cGhlbGk6CiAgICBmb3IgX3EsIF90IGluIF9zdXBoZWxpOgog'
        'ICAgICAgIHByaW50KGYiICAg4pyXIHtfcX0iKQogICAgICAgIHByaW50KGYiICAgICAg'
        '4oaSIHsnLCAnLmpvaW4oX3QpfSBmaXJtYSBrYXBzYW3EsW5kYSwga2/Fn3VsZGEgZmly'
        'bWFfaWQgeW9rIikKICAgIHByaW50KCkKICAgIHByaW50KCIgICDihpIgSGFtIFNRTCBP'
        'Uk0gc8O8emdlY2luZGVuIEdFw4dNRVouIFdIRVJFJ2UgZmlybWFfaWQgZWtsZXlpbiIp'
        'CiAgICBwcmludCgiICAgICB5YSBkYSBnZXJla8OnZXNpbmkgYnUgZG9zeWFkYWtpIEhB'
        'TV9TUUxfQkVLTEVORU4nZSB5YXrEsW4uIikKICAgIGJ1bGd1ICs9IGxlbihfc3VwaGVs'
        'aSkKZWxzZToKICAgIHByaW50KCIgICDinJMgdGVtaXog4oCUIGZpcm1hIGthcHNhbWzE'
        'sSB0YWJsb3lhIHPDvHpnZcOnc2l6IGRva3VuYW4gaGFtIFNRTCB5b2siKQogICAgcHJp'
        'bnQoZiIgICAgICh7bGVuKEhBTV9TUUxfQkVLTEVORU4pfSBkZXNlbiBiaWxlcmVrIG11'
        'YWY6KSIpCiAgICBmb3IgX2QsIF9uIGluIEhBTV9TUUxfQkVLTEVORU4uaXRlbXMoKToK'
        'ICAgICAgICBwcmludChmIiAgICAgICB7X2Q6PDM0fSB7X259IikKCnByaW50KCkKcHJp'
        'bnQoIuKVkCIgKiA3MCkKaWYgYnVsZ3U6CiAgICBwcmludChmIiDinJcge2J1bGd1fSDD'
        'h09LTFUgRsSwUk1BIEJVTEdVU1UiKQplbHNlOgogICAgcHJpbnQoIiDinJMgVEVNxLBa'
        'IOKAlCDDp29rbHUgZmlybWEga2Fwc2FtxLEgdHV0YXJsxLEiKQpwcmludCgi4pWQIiAq'
        'IDcwKQpzeXMuZXhpdCgxIGlmIGJ1bGd1IGVsc2UgMCkK'
    ),
}


def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA TZ1 — SIFIRLAMA / TEMİZLİK / PUSH BETİKLERİ')
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
        print('    python3 yama_tz1.py            # rapor')
        print('    python3 yama_tz1.py --uygula')
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

        # Söz dizimi doğrulaması: bozuk bir denetim aracı push
        # kapısını kilitler.
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
        print('  ⊙ Yama TZ1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_tz1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_tz1'
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
    print('  SIRA SIRA:')
    print()
    print('    1) Çoklu firma kapsamı tutuyor mu:')
    print('         venv/bin/python firma_denetim.py')
    print()
    print('    2) Sıfırlama seçeneklerini gör (HİÇBİR ŞEY SİLMEZ):')
    print('         venv/bin/python sifirla2.py')
    print()
    print('       Üç kip rapor çıktısının sonunda komutuyla listeli.')
    print('       Tek firma kipinde betik, dokunulmayan firmaları')
    print('       silmeden ÖNCE ve SONRA sayıp karşılaştırır.')
    print()
    print('    3) Temizlik artık yamaları tanıyor:')
    print('         ./temizle.sh')
    print()
    print('    4) Push kapısı:')
    print('         ./gonder.sh "coklu firma MF1-MF7 + sifirlama kipleri"')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

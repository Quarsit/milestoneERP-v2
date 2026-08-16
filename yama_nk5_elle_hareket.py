#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — ELLE HAREKET SINIFLANDIRMASI  ·  NK5
#
#  ── ÖN KOŞUL ──
#      yama_nk1_nakit_zincir.py + yama_nk4_kalem_duzeyi.py
#
#  ── BELİRTİ ──
#    Cari hesaba tahsilat girilince nakit akışında ÇIKIŞ görünüyor.
#
#  ── İKİ AYRI HATA (ikisi de benim) ──
#
#    1) `CariHareket.kaynak` alanının model varsayılanı 'manuel'.
#       Cari ekranından girilen HER hareket bu değeri alıyor:
#       satış faturası da, tahsilat da, ödeme de. Ben 'manuel'i
#       NAKIT_YUKUMLULUK listesine koymuştum. Tahsilat `alacak`
#       sütununa yazıldığı için "biz borçluyuz" sanılıp ÇIKIŞ
#       oluyordu.
#
#       Kaynak alanı burada AYIRT EDİCİ DEĞİL. Ayrımı `islem_tip`
#       yapar: 'Tahsilat', 'Odeme', 'Avans Tahsilati',
#       'Avans Odemesi' kapatmadır; 'Fatura (Satis)',
#       'Fatura (Alis)' yükümlülüktür.
#
#    2) Cari ekranından fatura kesilince kaynak 'cari_fatura'
#       oluyor — ve bu değer İKİ LİSTEDE DE YOK. Yani hareket
#       sessizce yok sayılıyordu: 100.000'lik satış faturası
#       projeksiyonda HİÇ görünmüyordu.
#
#       Bildirilen hatadan daha ağırı bu. Yanlış yönde görünen bir
#       rakam fark edilir; hiç görünmeyen alacak fark edilmez.
#
#    Ölçüldü (gerçek uç nokta /api/cari/hareket ile):
#        Satış faturası 100.000 → giriş 0      (olması gereken 100.000)
#        Tahsilat        40.000 → çıkış 40.000 (olması gereken 0)
#
#  ── DÜZELTME ──
#    Rol tayini tek bir fonksiyona alındı: `_nakit_rol(h)`.
#      · kaynak 'manuel'/'elle' → islem_tip'e bakılır
#      · diğerleri            → kaynak listelerine bakılır
#    'cari_fatura' yükümlülük listesine eklendi.
#
#    Tanınmayan bir islem_tip yükümlülük sayılır — GÖRÜNÜR kalsın
#    diye. Kapatma saysaydık başka faturaları sessizce eritirdi;
#    yanlış görünen rakam, görünmeyen rakamdan iyidir.
#
#  KULLANIM (proje klasöründe):
#      python yama_nk5_elle_hareket.py            # rapor
#      python yama_nk5_elle_hareket.py --uygula
#
#  Şema değişikliği YOK.
# ══════════════════════════════════════════════════════════════════════
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
APP = Path('flask_app.py')

if not APP.exists():
    print("HATA: flask_app.py bu klasörde yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

_h = APP.read_text(encoding='utf-8', errors='replace')
if 'NAKIT_YUKUMLULUK' not in _h:
    print("✗ ÖN KOŞUL: önce yama_nk1_nakit_zincir.py uygulanmalı.")
    sys.exit(1)

# ── A) Sınıflandırma: liste + rol fonksiyonu ───────────────────────
A_ESKI = """    # YUKUMLULUK: gelecekte nakit hareketi DOGURAN kayitlar.
    NAKIT_YUKUMLULUK = ('fatura', 'maliyet', 'stok', 'siparis_teslim',
                        'sicak_satis', 'rezervasyon', 'sabit',
                        'elle', 'manuel')"""

A_YENI = '''    # YUKUMLULUK: gelecekte nakit hareketi DOGURAN kayitlar.
    # 'cari_fatura' = cari ekranindan kesilen fatura. Onceden bu
    # deger HICBIR listede yoktu ve hareket sessizce yok sayiliyordu;
    # 100.000'lik bir satis faturasi projeksiyonda gorunmuyordu.
    NAKIT_YUKUMLULUK = ('fatura', 'cari_fatura', 'maliyet', 'stok',
                        'siparis_teslim', 'sicak_satis', 'rezervasyon',
                        'sabit')

    # ELLE GIRILEN HAREKETLER
    # `CariHareket.kaynak` alaninin model varsayilani 'manuel'. Cari
    # ekranindan girilen HER hareket bu degeri aliyor — satis
    # faturasi da, tahsilat da. Yani kaynak burada AYIRT EDICI
    # DEGIL; ayrimi islem_tip yapar.
    NAKIT_ELLE_KAPATMA = ('tahsilat', 'odeme',
                          'avans tahsilati', 'avans odemesi')

    def _nakit_sadelestir(s):
        """Turkce karakterleri sadelestirip kucultur.

        'Ödeme' ile 'Odeme' ayni sayilsin diye — form degerleri
        zaman icinde iki bicimde de yazilmis olabilir.
        """
        s = (s or '').strip().lower()
        for _a, _b in (('ı', 'i'), ('İ', 'i'), ('ğ', 'g'), ('ü', 'u'),
                       ('ş', 's'), ('ö', 'o'), ('ç', 'c')):
            s = s.replace(_a, _b)
        return s

    def _nakit_rol(h):
        """Hareketin nakit projeksiyonundaki rolu.

        Doner: 'yukumluluk' | 'kapatma' | None (hesap disi)

        Tanınmayan islem_tip YUKUMLULUK sayilir: boylece ekranda
        gorunur ve yanlissa fark edilir. Kapatma saysaydik baska
        faturalari sessizce eritirdi.
        """
        _k = (h.kaynak or '')
        if _k in ('elle', 'manuel'):
            if _nakit_sadelestir(h.islem_tip) in NAKIT_ELLE_KAPATMA:
                return 'kapatma'
            return 'yukumluluk'
        if _k in NAKIT_YUKUMLULUK:
            return 'yukumluluk'
        if _k in NAKIT_KAPATMA:
            return 'kapatma'
        return None'''

# ── B) Döngü rol fonksiyonunu kullansın ────────────────────────────
B_ESKI = """            if _k in NAKIT_YUKUMLULUK:"""
B_YENI = """            _rol = _nakit_rol(h)
            if _rol == 'yukumluluk':"""

C_ESKI = """            elif _k in NAKIT_KAPATMA:
                if (_k == 'cek' and h.baglanti_tip == 'cek'
                        and h.baglanti_id in _olu_cek):"""
C_YENI = """            elif _rol == 'kapatma':
                if (_k == 'cek' and h.baglanti_tip == 'cek'
                        and h.baglanti_id in _olu_cek):"""

BLOKLAR = [
    ("sınıflandırma + rol fonksiyonu", A_ESKI, A_YENI, 'def _nakit_rol('),
    ("döngü: yükümlülük dalı",         B_ESKI, B_YENI, "_rol = _nakit_rol(h)"),
    ("döngü: kapatma dalı",            C_ESKI, C_YENI, "elif _rol == 'kapatma':"),
]

print("═" * 70)
print(" NK5 · ELLE HAREKET SINIFLANDIRMASI")
print("═" * 70)
print()

ham = APP.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


icerik = ham
plan, atlanan, sorunlu = [], [], []
for aciklama, eski, yeni, imza in BLOKLAR:
    if uyarla(imza) in icerik or imza in icerik:
        atlanan.append(aciklama)
        continue
    e = uyarla(eski)
    adet = icerik.count(e)
    if adet != 1:
        sorunlu.append((aciklama, adet))
        continue
    icerik = icerik.replace(e, uyarla(yeni), 1)
    plan.append(aciklama)

for a in atlanan:
    print(f"  ↷ atlandı (zaten var)  {a}")
for a in plan:
    print(f"  ✓ uygulanacak          {a}")
for a, n in sorunlu:
    print(f"  ✗ KALIP BULUNAMADI     {a}  (eşleşme: {n})")

print()
if sorunlu:
    print(f" ✗ {len(sorunlu)} blok yerleştirilemedi — DOSYAYA DOKUNULMADI.")
    sys.exit(1)
if not plan:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

try:
    compile(icerik, 'flask_app.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)
print(" ✓ sözdizimi doğrulandı (compile)")

# Dongu artik ham liste kiyasi yapmamali.
_b = icerik.split('def _nakit_kalemleri(')[1].split('def _nakit_projeksiyon')[0]
_kalan = [l.strip() for l in _b.split('\n')
          if ('in NAKIT_YUKUMLULUK' in l or 'in NAKIT_KAPATMA' in l)
          and not l.strip().startswith('#')]
if _kalan:
    print(" ✗ Döngüde hâlâ ham liste kıyası var:")
    for l in _kalan[:3]:
        print(f"     {l[:70]}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)
print(" ✓ döngü rol fonksiyonunu kullanıyor")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_nk5_elle_hareket.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = APP.with_name(f'flask_app.py.yedek-{damga}')
shutil.copy2(APP, yedek)
APP.write_bytes(icerik.encode('utf-8'))
print()
print(f" ✓ flask_app.py  (yedek: {yedek.name})")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print(" Tahsilat artık alacağı azaltıyor, çıkış olarak görünmüyor.")
print(" Cari ekranından kesilen fatura projeksiyona giriyor.")
print("═" * 70)

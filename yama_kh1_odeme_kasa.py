#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — 'Ödeme' KASAYA DOKUNMUYOR  ·  KH1
#
#  ── ÖLÇÜLEN HATA ──
#    Kasa hareketi ureten liste Ö'lu yazimi TANIMIYOR:
#
#        tahsilat_odeme_tipleri = ['Tahsilat', 'Avans Tahsilati',
#                                  'Odeme', 'Avans Odemesi']
#
#    Oysa KASA_ZORUNLU_TIPLER ikisini de tanıyor:
#        ('Tahsilat', 'Odeme', 'Ödeme', 'Avans Odemesi', 'Avans Ödemesi')
#
#    Sonuc olculdu (10.000 USD kasa, 1.000 USD odeme):
#        islem_tip='Odeme'  -> kasa  9.000  ✓
#        islem_tip='Ödeme'  -> kasa 10.000  ✗
#
#    Yani 'Ödeme' secilirse CARI BORCU DUSUYOR ama KASADAN PARA
#    CIKMIYOR. Kasa defteri ile gercek para ayrisiyor; D1
#    degismezligi (kasa bakiyesi = hareketler toplami) korunuyor
#    cunku hic hareket yazilmiyor — hata SESSIZ.
#
#  ── NEDEN İKİ YAZIM VAR ──
#    Ekranlar zamanla ikisini de gondermis; kod bir yerde ikisini
#    de kabul edip baska yerde etmeyince tutarsizlik olustu. Kalici
#    cozum tek yazima gecmek ama mevcut KAYITLAR iki bicimde;
#    listeyi genisletmek hem eskiyi hem yeniyi kurtarir.
#
#  ── AVANS TIPLERI DE EKLENDI ──
#    'Avans Ödemesi' de ayni sekilde eksikti.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python yama_kh1_odeme_kasa.py            # rapor
#      venv/bin/python yama_kh1_odeme_kasa.py --uygula
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

ESKI = """        tahsilat_odeme_tipleri = ['Tahsilat', 'Avans Tahsilati', 'Odeme', 'Avans Odemesi']"""

YENI = """        # Ö'LU YAZIM DA TANINIR (KH1).
        # Bu liste kasa hareketi uretimini kontrol ediyor. Ö'lu
        # yazim eksik oldugu icin 'Ödeme' secildiginde cari borcu
        # dusuyor ama KASADAN PARA CIKMIYORDU — hata sessizdi,
        # cunku hic kasa hareketi yazilmadigi icin D1 degismezligi
        # de ihlal edilmiyordu.
        #
        # Olculdu (10.000 USD kasa, 1.000 USD odeme):
        #   'Odeme' -> kasa 9.000 ✓   'Ödeme' -> kasa 10.000 ✗
        #
        # KASA_ZORUNLU_TIPLER zaten ikisini de taniyordu; tutarsizlik
        # oradaydi.
        tahsilat_odeme_tipleri = ['Tahsilat', 'Avans Tahsilati',
                                  'Odeme', 'Ödeme',
                                  'Avans Odemesi', 'Avans Ödemesi']"""

# Giriş/çıkış yönü de Ö'lü yazımı bilmeli (tahsilat tarafı)
B_ESKI = """            giris_mi = islem_tip in ('Tahsilat', 'Avans Tahsilati')"""
B_YENI = """            # Tahsilat = kasaya GIRIS, odeme = CIKIS. Odeme
            # yazimlari yukarida genisletildi; burada tahsilat
            # tarafi zaten tek yazimli.
            giris_mi = islem_tip in ('Tahsilat', 'Avans Tahsilati')"""

# Imza BENZERSIZ olmali. Ilk surumde "'Odeme', 'Ödeme'," secilmisti
# ama o metin KASA_ZORUNLU_TIPLER satirinda ZATEN vardi; yama hic
# uygulanmadan "zaten uygulanmis" deyip cikiyordu.
IMZA = "Ö'LU YAZIM DA TANINIR (KH1)"

print("═" * 70)
print(" KH1 · 'Ödeme' KASAYA DOKUNMUYOR")
print("═" * 70)
print()

ham = APP.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


if uyarla(IMZA) in ham or IMZA in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

e = uyarla(ESKI)
adet = ham.count(e)
if adet != 1:
    print(f" ✗ Kalıp {adet} kez bulundu (1 bekleniyordu). DOSYAYA DOKUNULMADI.")
    sys.exit(1)

icerik = ham.replace(e, uyarla(YENI), 1)

_b = uyarla(B_ESKI)
if icerik.count(_b) == 1:
    icerik = icerik.replace(_b, uyarla(B_YENI), 1)

try:
    compile(icerik, 'flask_app.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print("  ✓ uygulanacak          'Ödeme' ve 'Avans Ödemesi' eklendi")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   venv/bin/python yama_kh1_odeme_kasa.py --uygula")
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
print(" ⚠ GEÇMİŞTE 'Ödeme' ile girilmiş kayıtlar varsa kasadan")
print("   düşülmemiş olabilir. Kontrol:")
print("     venv/bin/python degismezlik_denetim.py")
print("   ve kasa defterini gerçek bakiyeyle karşılaştırın.")
print("═" * 70)

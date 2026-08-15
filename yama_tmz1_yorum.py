#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — YORUM DÜZELTMESİ  ·  TMZ1
#
#  ── SORUN ──
#    flask_app.py'de nakit projeksiyonundaki şu yorum KIRIK bir atıf
#    yapıyor:
#
#        # Gerekce icin dosya basindaki acikliamaya bakin
#
#    "Dosya başı" ile kastedilen yama_na2_projeksiyon.py'nin başlığıydı.
#    Ama yorum flask_app.py'ye yazıldı — o dosyanın başında böyle bir
#    açıklama YOK. Atıf yazıldığı anda kırıktı.
#
#    (Ayrıca yazım hatası: "acikliamaya" → "aciklamaya")
#
#  ── NEDEN ŞİMDİ ──
#    Uygulanmış yama betikleri depodan siliniyor. Silinmeden önce,
#    hiçbir yorumun onlara BAĞIMLI kalmaması gerekiyor. Kod kendi
#    başına anlaşılır olmalı; gerekçe koda gömülü, geçmiş git'te.
#
#  ── NE DEĞİŞİYOR ──
#    Yalnızca YORUM. Çalışan tek satır kod değişmiyor —
#    NAKIT_HARIC_KAYNAK demeti aynı kalıyor. Betik bunu token
#    karşılaştırmasıyla KANITLAR; kod değişecek olsa yazmaz.
#
#  KULLANIM (proje klasöründe):
#      python yama_tmz1_yorum.py            # rapor
#      python yama_tmz1_yorum.py --uygula   # uygula
#
#  Bu betik de işini bitirince silinecek (bkz. temizlik adımı).
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

ESKI = """    # Cari hareketin nakit projeksiyonuna GIRMEYECEGI kaynaklar.
    # Gerekce icin dosya basindaki acikliamaya bakin — ozetle: ya
    # parasi zaten kasaya girmis, ya baska bir tablodan sayiliyor,
    # ya da hic nakit hareketi yok.
    NAKIT_HARIC_KAYNAK = ('cek', 'tahsilat', 'virman', 'mahsup', 'avans_devir')"""

YENI = """    # Cari hareketin nakit projeksiyonuna GIRMEYECEGI kaynaklar.
    # Her biri AYRI sebeple disarida:
    #
    #   'cek'          Cek kendi tablosundan sayiliyor (asagida,
    #                  Cek.query dongusu).
    #   'tahsilat'     Bu hareket CEK ALINIRKEN aciliyor — bkz.
    #                  api_cek_ekle(). Yani cekin ta kendisi.
    #                  Sayilsaydi ayni tahsilat hem Cek hem
    #                  CariHareket uzerinden IKI KEZ gorunurdu.
    #   'virman'       Parayi zaten kasaya tasimis; tutar kasa.bakiye
    #                  icinde, yani acilis bakiyesine dahil.
    #   'mahsup'       Hesap denklestirme — nakit hareketi yok.
    #   'avans_devir'  Hesaplar arasi avans aktarimi — nakit hareketi
    #                  yok.
    #
    # Fatura tablosu HIC okunmuyor: fatura kesilince cari hareket
    # zaten aciliyor. Ikisini de okumak her borcu iki kez sayardi.
    NAKIT_HARIC_KAYNAK = ('cek', 'tahsilat', 'virman', 'mahsup', 'avans_devir')"""

IMZA = "#   'tahsilat'     Bu hareket CEK ALINIRKEN aciliyor"

print("═" * 70)
print(" TMZ1 · kırık yorum atfı düzeltmesi")
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

try:
    compile(icerik, 'flask_app.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

# Calisan kodun DEGISMEDIGINI kanitla: yorumlar atilinca iki surum
# birebir ayni olmali. Yorum yamasinin davranisa dokunmadiginin ispati.
import io
import tokenize


def kod_ozu(kaynak):
    parcalar = []
    for tok in tokenize.generate_tokens(io.StringIO(kaynak).readline):
        if tok.type in (tokenize.COMMENT, tokenize.NL):
            continue
        parcalar.append((tok.type, tok.string))
    return parcalar


if kod_ozu(ham.replace('\r\n', '\n')) != kod_ozu(icerik.replace('\r\n', '\n')):
    print(" ✗ Çalışan kod değişmiş olurdu — DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print("  ✓ uygulanacak          yorum kendi içinde tam hale geliyor")
print("  ✓ sözdizimi doğrulandı (compile)")
print("  ✓ çalışan kod BİREBİR aynı (token karşılaştırması)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_tmz1_yorum.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = APP.with_name(f'flask_app.py.yedek-{damga}')
shutil.copy2(APP, yedek)
APP.write_bytes(icerik.encode('utf-8'))
print()
print(f" ✓ flask_app.py  (yedek: {yedek.name})")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI — artık hiçbir yorum yama betiklerine bağımlı değil")
print("═" * 70)

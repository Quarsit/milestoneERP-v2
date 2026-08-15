#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — NK1 DÜZELTMESİ  ·  NK2
#
#  ── ÖN KOŞUL ──
#      yama_nk1_nakit_zincir.py --uygula
#
#  ── HATA (NK1'de benim yaptığım) ──
#    NK1'in FIFO döngüsünde şöyle bir koruma vardı:
#
#        if h.kapatildi:
#            continue        # yükümlülük sayma
#
#    Bu satır, hareketi YÜKÜMLÜLÜK listesinden çıkarıyor ama
#    karşılığındaki tahsilatı KAPATMA HAVUZUNDA bırakıyordu. Yani
#    aynı ödeme iki kez kapatma yapıyordu: bir kez faturayı atlayarak,
#    bir kez de havuzda kalarak BAŞKA bir faturayı silerek.
#
#    Ölçülen (100.000 USD tahsil edildi, 70.000 USD hâlâ bekliyor):
#        HF1 100.000  kapatildi=True   → atlandı
#        HF2  70.000  kapatildi=False  → yükümlülük
#        tahsilat 100.000              → kapatma havuzunda KALDI
#        FIFO: 100.000 kapatma → 70.000'lik F2'yi de sildi
#        projeksiyon: 0        DOĞRUSU: 70.000
#
#    Tahsil EDİLMEMİŞ bir alacak ekrandan kayboluyordu. Yön olarak
#    ilk hatanın tersi ve daha sinsi: fazla göstermek göze batar,
#    eksik göstermek batmaz.
#
#  ── NEDEN GÖRÜNMEDİ ──
#    `kapatildi` yalnızca kur farkı hesabı çalışabildiğinde atanıyor
#    (_kur_farki_hesapla_ve_olustur). O da DovizKur tablosunda kur
#    yoksa erken dönüyor. Test ortamımda kur tablosu boştu, üretimde
#    TCMB kurları var — hata yalnızca ÜRETİMDE ortaya çıkardı.
#
#  ── DÜZELTME ──
#    Koruma satırı KALDIRILDI. FIFO kapatmayı zaten kendisi
#    hesapliyor; `kapatildi` bayrağına ayrıca bakmak gereksiz ve
#    zararlı. Kapatan her hareket (tahsilat, odeme, cek, virman,
#    mahsup, avans_devir) zaten NAKIT_KAPATMA listesinde ve havuza
#    giriyor — yani kapanmış fatura FIFO ile kendiliğinden düşüyor.
#
#  ── `kapatildi` ALANI HAKKINDA ──
#    Daha önce "bu alan ölü" demiştim; YANLIŞTI. Alan
#    _kur_farki_hesapla_ve_olustur içinde atanıyor ve iki gerçek
#    kullanıcısı var:
#      · stok silme koruması ("alış borcu kapatılmışsa silme")
#      · cari hareket serileştiricileri (ekranda gösterim)
#    Bu yüzden alana DOKUNULMUYOR. Yalnızca nakit projeksiyonunun
#    ona olan bağımlılığı kaldırılıyor.
#
#  KULLANIM (proje klasöründe):
#      python yama_nk2_kapatildi_duzeltme.py            # rapor
#      python yama_nk2_kapatildi_duzeltme.py --uygula   # uygula
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

if '_kalan_kapatma' not in APP.read_text(encoding='utf-8', errors='replace'):
    print("✗ ÖN KOŞUL: önce yama_nk1_nakit_zincir.py uygulanmalı.")
    sys.exit(1)

ESKI = """            if _k in NAKIT_YUKUMLULUK:
                if h.kapatildi:
                    # Alan sistemde kullanilmiyor ama isaretlenmisse saygi duy.
                    continue
                # borc   = musteri bize borclu       → GIRIS"""

YENI = """            if _k in NAKIT_YUKUMLULUK:
                # DIKKAT: burada `kapatildi` bayragina BAKILMAZ.
                #
                # Bakilsaydi hareket yukumluluk listesinden cikardi ama
                # karsiligindaki tahsilat kapatma havuzunda KALIRDI —
                # ayni odeme iki kez kapatma yapar, BASKA bir faturayi
                # yanlislikla silerdi. Olculdu: 100.000 tahsil edilince
                # tahsil EDILMEMIS 70.000'lik fatura da ekrandan
                # kayboluyordu.
                #
                # FIFO kapatmayi zaten kendisi hesapliyor: kapatan her
                # hareket NAKIT_KAPATMA listesinde ve havuza giriyor,
                # yani kapanmis fatura kendiliginden dusuyor. Bayraga
                # ayrica bakmak gereksiz ve zararli.
                #
                # (`kapatildi` alani baska yerlerde kullaniliyor —
                #  stok silme korumasi, ekran gosterimi — bu yuzden
                #  alanin kendisine dokunulmadi.)
                # borc   = musteri bize borclu       → GIRIS"""

IMZA = "burada `kapatildi` bayragina BAKILMAZ"

print("═" * 70)
print(" NK2 · NK1 DÜZELTMESİ — kapatildi bağımlılığı kaldırılıyor")
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

# Projeksiyon artik `kapatildi`ya HIC bakmamali.
# YORUMLAR AYIKLANIR: aciklama metninde gecen kelime kod degildir.
# (Ilk surumde bu ayrim yoktu ve yama kendi yorumuna takiliyordu.)
_bolum = icerik.split('def _nakit_kalemleri(')[1].split('def api_nakit_akis')[0]
_kod = [l for l in _bolum.split('\n') if not l.strip().startswith('#')]
_kalan = [l.strip() for l in _kod if 'kapatildi' in l]
if _kalan:
    print(" ✗ Projeksiyon kodunda hâlâ `kapatildi` kullanımı var:")
    for l in _kalan[:5]:
        print(f"     {l[:70]}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print("  ✓ uygulanacak          kapatildi koruması kaldırılıyor")
print("  ✓ projeksiyonda `kapatildi` referansı kalmadı")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_nk2_kapatildi_duzeltme.py --uygula")
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
print(" Tahsil edilmemiş alacaklar artık kaybolmuyor.")
print("═" * 70)

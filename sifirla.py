#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — TEST VERİSİ SIFIRLAMA  ·  R1
#
#  NE YAPAR:
#    Deneme amaçlı girilmiş TÜM işlem verisini siler; sistemin
#    çalışması için gereken YAPILANDIRMAYI korur. Gerçek kullanıma
#    temiz bir veritabanıyla başlamak içindir.
#
#  ══ SİLİNİR (18 tablo) ══
#    Stok        : blok_stok, plaka_stok, ebatli_stok, stok_cikis
#    Satış       : siparis_kayit, siparis_kalem, rezervasyon,
#                  proforma, proforma_kalem, satis_kaydi, faturalar
#    Finans      : cariler, cari_hareket, kasa_hareket, cek, cek_hareket
#    Üretim      : kesim, kesim_detay
#    Maliyet     : maliyetler
#    Lojistik    : sevkiyat_kayit
#    KDV         : kdv_iade_dosya
#    Denetim     : audit_log
#    Tanımlar    : kasa, banka          ← isteğiniz üzerine bunlar da
#
#  ══ KORUNUR (3 tablo) ══
#    kullanicilar  Kullanıcılar, şifreler, yetkiler
#    veriler       Ayarlar → Listeler (cins, yüzey, ödeme şekli, ülke),
#                  firma bilgileri, FİRMA LOGOSU, SMTP ayarları,
#                  KDV oranları, sipariş/muhasebe ayarları
#    doviz_kur     TCMB kur arşivi (yeniden çekmek dakikalar sürer)
#
#  ══ GÜVENLİK ══
#    • --onayla BAYRAĞI OLMADAN HİÇBİR ŞEY SİLMEZ. Bayraksız
#      çalıştırma yalnızca ne silineceğini SAYIYLA raporlar.
#    • Silmeden önce pg_dump ile yedek alır; yedek başarısız olursa
#      İŞLEMİ İPTAL EDER.
#    • Tek bir işlem (transaction) içinde çalışır: bir tablo bile
#      hata verirse HİÇBİRİ silinmez.
#    • Yabancı anahtar sırasına göre siler (çocuk tablo önce).
#
#  ══ KİMLİKLER ══
#    Çoğu tablo UUID tabanlı kimlik kullanır (_yeni_id: 'BLK-A3F91C'),
#    dolayısıyla sayaç sıfırlaması GEREKMEZ. Yalnızca tamsayı birincil
#    anahtarlı tablolarda PostgreSQL dizisi (sequence) 1'e çekilir.
#
#  KULLANIM (proje dizininde):
#      venv/bin/python sifirla.py             # RAPOR — hiçbir şey silinmez
#      venv/bin/python sifirla.py --onayla    # SİLER
#
#  ⚠ GERİ ALINAMAZ. Yalnızca gerçek kullanıma geçmeden önce, bir kez.
# ══════════════════════════════════════════════════════════════════════
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

load_dotenv()

ONAYLA = '--onayla' in sys.argv
YEDEK_ATLA = '--yedek-atla' in sys.argv   # yalnızca geliştirme içindir

VT_URL = None
for arg in sys.argv[1:]:
    if arg.startswith('--url='):
        VT_URL = arg.split('=', 1)[1].strip().strip('"').strip("'")
VT_URL = VT_URL or os.environ.get('DATABASE_URL')

if not VT_URL:
    print("HATA: DATABASE_URL bulunamadı (.env okunamadı).")
    sys.exit(1)
if VT_URL.startswith('postgres://'):
    VT_URL = VT_URL.replace('postgres://', 'postgresql://', 1)

# ── Silinecek tablolar: ÇOCUK TABLO ÖNCE (yabancı anahtar sırası) ──
SIL_SIRASI = [
    # Denetim izi
    'audit_log',
    # Çek
    'cek_hareket', 'cek',
    # Kesim
    'kesim_detay', 'kesim',
    # Satış zinciri
    'satis_kaydi', 'rezervasyon',
    'proforma_kalem', 'proforma',
    'siparis_kalem',
    'faturalar',
    'sevkiyat_kayit',
    'siparis_kayit',
    # KDV iade
    'kdv_iade_dosya',
    # Maliyet
    'maliyetler',
    # Stok
    'stok_cikis', 'blok_stok', 'plaka_stok', 'ebatli_stok',
    # Finans
    'kasa_hareket', 'cari_hareket', 'cariler', 'kasa', 'banka',
]

KORUNAN = {
    'kullanicilar': 'Kullanıcılar, şifreler, yetkiler',
    'veriler': 'Listeler, firma bilgisi, LOGO, SMTP, KDV ayarları',
    'doviz_kur': 'TCMB kur arşivi',
}

# Tamsayı birincil anahtarlı tablolar — dizileri 1'e çekilir.
DIZI_SIFIRLA = ['banka', 'kasa', 'kasa_hareket', 'kesim_detay', 'cek_hareket',
                'audit_log']

motor = create_engine(VT_URL)
denetci = inspect(motor)
mevcut = set(denetci.get_table_names())
pg = motor.dialect.name in ('postgresql', 'postgres')

print("═" * 70)
print(" MILESTONE ERP — TEST VERİSİ SIFIRLAMA")
print("═" * 70)
kaynak = urlparse(VT_URL)
print(f" Veritabanı : {kaynak.path.lstrip('/')} @ {kaynak.hostname or 'yerel'}")
print(f" Sürücü     : {motor.dialect.name}")
print()

# ── Sayım ──
sayim, eksik, toplam = {}, [], 0
with motor.connect() as b:
    for t in SIL_SIRASI:
        if t not in mevcut:
            eksik.append(t)
            continue
        n = b.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() or 0
        sayim[t] = n
        toplam += n
    korunan_sayim = {}
    for t in KORUNAN:
        if t in mevcut:
            korunan_sayim[t] = b.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() or 0

print("─" * 70)
print(" SİLİNECEK")
print("─" * 70)
for t in SIL_SIRASI:
    if t in sayim:
        isaret = '·' if sayim[t] == 0 else '✗'
        print(f"   {isaret} {t:<20s} {sayim[t]:>7,} kayıt")
if eksik:
    print(f"\n   (tabloda yok, atlanacak: {', '.join(eksik)})")
print(f"\n   TOPLAM {toplam:,} kayıt")
print()

print("─" * 70)
print(" KORUNACAK")
print("─" * 70)
for t, aciklama in KORUNAN.items():
    n = korunan_sayim.get(t, 0)
    print(f"   ✓ {t:<16s} {n:>6,} kayıt   {aciklama}")
print()

if not ONAYLA:
    print("═" * 70)
    print(" RAPOR MODU — HİÇBİR ŞEY SİLİNMEDİ")
    print()
    print(" Yukarıdaki listeyi dikkatle okuyun. Doğruysa:")
    print("   venv/bin/python sifirla.py --onayla")
    print()
    print(" ⚠ Bu işlem GERİ ALINAMAZ.")
    print("═" * 70)
    sys.exit(0)

if toplam == 0:
    print("═" * 70)
    print(" Silinecek kayıt yok — veritabanı zaten temiz.")
    print("═" * 70)
    sys.exit(0)

# ── Yedek (zorunlu) ──
print("─" * 70)
print(" YEDEK ALINIYOR")
print("─" * 70)
if YEDEK_ATLA:
    print("   ⚠ --yedek-atla verildi, yedek ALINMADI (yalnızca geliştirme).")
elif pg:
    damga = datetime.now().strftime('%Y%m%d_%H%M%S')
    hedef_dizin = Path.home() / 'yedekler'
    hedef_dizin.mkdir(exist_ok=True)
    hedef = hedef_dizin / f'milestone_sifirlama_oncesi_{damga}.dump'
    ortam = dict(os.environ)
    if kaynak.password:
        ortam['PGPASSWORD'] = kaynak.password
    komut = ['pg_dump', '-Fc', '-f', str(hedef)]
    if kaynak.hostname:
        komut += ['-h', kaynak.hostname]
    if kaynak.port:
        komut += ['-p', str(kaynak.port)]
    if kaynak.username:
        komut += ['-U', kaynak.username]
    komut.append(kaynak.path.lstrip('/'))
    try:
        s = subprocess.run(komut, env=ortam, capture_output=True, text=True, timeout=600)
        if s.returncode != 0 or not hedef.exists() or hedef.stat().st_size == 0:
            print("   ✗ YEDEK BAŞARISIZ — işlem İPTAL edildi, hiçbir şey silinmedi.")
            print(f"     {(s.stderr or '').strip()[:300]}")
            print("\n     Elle yedek alıp tekrar deneyin:")
            print("       sudo /usr/local/bin/milestone-yedek.sh")
            sys.exit(1)
        print(f"   ✓ {hedef}  ({hedef.stat().st_size / 1024:.0f} KB)")
    except FileNotFoundError:
        print("   ✗ pg_dump bulunamadı — işlem İPTAL edildi.")
        print("     Önce elle yedek alın: sudo /usr/local/bin/milestone-yedek.sh")
        print("     Yedeği aldıysanız --yedek-atla ile tekrar çalıştırın.")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("   ✗ pg_dump zaman aşımı — işlem İPTAL edildi.")
        sys.exit(1)
else:
    print("   ℹ PostgreSQL değil; pg_dump atlandı (dosyayı elle kopyalayın).")
print()

# ── Silme: TEK İŞLEM ──
print("─" * 70)
print(" SİLİNİYOR")
print("─" * 70)
silinen_toplam = 0
try:
    with motor.begin() as b:          # hata olursa tamamı geri alınır
        if pg:
            b.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        for t in SIL_SIRASI:
            if t not in sayim:
                continue
            b.execute(text(f'DELETE FROM "{t}"'))
            if sayim[t]:
                print(f"   ✓ {t:<20s} {sayim[t]:>7,} kayıt silindi")
            silinen_toplam += sayim[t]
        if pg:
            for t in DIZI_SIFIRLA:
                if t in mevcut:
                    b.execute(text(
                        f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), 1, false)"
                    ))
            print("   ✓ tamsayı kimlik sayaçları 1'e çekildi")
except Exception as e:
    print(f"\n   ✗ HATA: {e}")
    print("   İşlem geri alındı — HİÇBİR ŞEY SİLİNMEDİ.")
    sys.exit(1)

# ── Doğrulama ──
print()
print("─" * 70)
print(" DOĞRULAMA")
print("─" * 70)
sorun = []
with motor.connect() as b:
    for t in sayim:
        n = b.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() or 0
        if n:
            sorun.append((t, n))
    for t in KORUNAN:
        if t in mevcut:
            n = b.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() or 0
            beklenen = korunan_sayim.get(t, 0)
            isaret = '✓' if n == beklenen else '✗'
            print(f"   {isaret} {t:<16s} {n:>6,} kayıt korundu (önce {beklenen:,})")
            if n != beklenen:
                sorun.append((t, n))

if sorun:
    print("\n   ✗ Beklenmeyen durum:")
    for t, n in sorun:
        print(f"     {t}: {n} kayıt")
    sys.exit(1)

print()
print("═" * 70)
print(f" ✓ TAMAMLANDI — {silinen_toplam:,} kayıt silindi")
print()
print(" SONRAKİ ADIMLAR:")
print("   1) sudo systemctl restart milestone-erp")
print("   2) Ayarlar → Kasalar: kasa tanımlarını yeniden girin")
print("   3) Ayarlar → Bankalar: banka hesaplarını yeniden girin")
print("   4) Cari Hesaplar: gerçek müşteri ve tedarikçileri girin")
print("   5) Stok: gerçek stok girişlerine başlayın")
print()
print(" Kullanıcılar, yetkiler, listeler, firma logosu ve kur arşivi")
print(" olduğu gibi duruyor — yeniden girmeniz gerekmez.")
print("═" * 70)

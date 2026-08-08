#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — TEST VERİSİ SIFIRLAMA (WINDOWS)  ·  R1-WIN
#
#  sifirla.py'nin Windows sürümüdür. Mantık AYNIDIR; farkları:
#    • pg_dump'ı PATH'te bulamazsa Program Files altında KENDİ ARAR
#      (Windows kurulumlarında pg_dump genelde PATH'te olmaz)
#    • Yedekler  C:\Users\<kullanici>\Desktop\milestone-yedekler  altına
#    • Sanal ortam yok — sistem Python'u ile çalışır
#    • Linux'a özgü komut önerileri kaldırıldı
#
#  ⚠ ÖNEMLİ — YANLIŞ ANLAŞILMASIN:
#    Bu betik YALNIZCA çalıştırıldığı makinedeki veritabanını temizler.
#    Veritabanı depoda DEĞİLDİR (.env ve *.dump .gitignore'dadır), bu
#    yüzden sıfırlama sonrası GitHub'a gönderilecek bir DEĞİŞİKLİK
#    OLUŞMAZ. Windows'taki sıfırlama Pardus'u etkilemez; orada da
#    temizlemek isterseniz sifirla.py'yi Pardus'ta ayrıca çalıştırın.
#
#  ══ SİLİNİR (24 tablo) ══
#    Stok, sipariş, rezervasyon, proforma, fatura, satış kaydı,
#    sevkiyat, maliyet, cari + hareket, kasa + hareket, banka,
#    çek + hareket, kesim + detay, KDV iade dosyası, denetim kaydı
#
#  ══ KORUNUR (3 tablo) ══
#    kullanicilar  Kullanıcılar, şifreler, yetkiler
#    veriler       Listeler, firma bilgisi, LOGO, SMTP, KDV ayarları
#    doviz_kur     TCMB kur arşivi
#
#  ══ GÜVENLİK ══
#    • --onayla olmadan HİÇBİR ŞEY silmez, yalnızca sayar
#    • Silmeden önce pg_dump ile yedek alır; yedek başarısızsa İPTAL eder
#    • Tek işlem içinde çalışır: bir hata olursa hiçbiri silinmez
#    • Yabancı anahtar sırasına göre siler (çocuk tablo önce)
#
#  ══ KULLANIM ══
#    Komut isteminde (cmd) proje klasörüne gidip:
#
#      cd "C:\Users\MileStone\Desktop\milestoneERP-v2-main\milestoneERP-v2-main"
#      python sifirla_windows.py             ← RAPOR, hiçbir şey silmez
#      python sifirla_windows.py --onayla    ← SİLER
#
#    pg_dump elle vermek gerekirse:
#      python sifirla_windows.py --onayla --pgdump="C:\Program Files\PostgreSQL\17\bin\pg_dump.exe"
#
#  ⚠ GERİ ALINAMAZ.
# ══════════════════════════════════════════════════════════════════════
import glob
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("HATA: python-dotenv kurulu değil.")
    print("  pip install python-dotenv")
    sys.exit(1)

try:
    from sqlalchemy import create_engine, inspect, text
except ImportError:
    print("HATA: SQLAlchemy kurulu değil.")
    print("  pip install SQLAlchemy psycopg2-binary")
    sys.exit(1)

ONAYLA = '--onayla' in sys.argv
YEDEK_ATLA = '--yedek-atla' in sys.argv

VT_URL = None
PGDUMP_ELLE = None
for a in sys.argv[1:]:
    if a.startswith('--url='):
        VT_URL = a.split('=', 1)[1].strip().strip('"').strip("'")
    if a.startswith('--pgdump='):
        PGDUMP_ELLE = a.split('=', 1)[1].strip().strip('"').strip("'")

VT_URL = VT_URL or os.environ.get('DATABASE_URL')
if not VT_URL:
    print("HATA: DATABASE_URL bulunamadı.")
    print()
    print("  Proje klasöründe .env dosyası olmalı ve içinde şu satır bulunmalı:")
    print("    DATABASE_URL=postgresql://kullanici:sifre@localhost:5432/milestone")
    print()
    print("  Ya da elle verin:")
    print('    python sifirla_windows.py --url="postgresql://..."')
    sys.exit(1)
if VT_URL.startswith('postgres://'):
    VT_URL = VT_URL.replace('postgres://', 'postgresql://', 1)

# ── Silinecek tablolar: ÇOCUK TABLO ÖNCE ──
SIL_SIRASI = [
    'audit_log',
    'cek_hareket', 'cek',
    'kesim_detay', 'kesim',
    'satis_kaydi', 'rezervasyon',
    'proforma_kalem', 'proforma',
    'siparis_kalem',
    'faturalar',
    'sevkiyat_kayit',
    'siparis_kayit',
    'kdv_iade_dosya',
    'maliyetler',
    'stok_cikis', 'blok_stok', 'plaka_stok', 'ebatli_stok',
    'kasa_hareket', 'cari_hareket', 'cariler', 'kasa', 'banka',
]

KORUNAN = {
    'kullanicilar': 'Kullanıcılar, şifreler, yetkiler',
    'veriler': 'Listeler, firma bilgisi, LOGO, SMTP, KDV ayarları',
    'doviz_kur': 'TCMB kur arşivi',
}

DIZI_SIFIRLA = ['banka', 'kasa', 'kasa_hareket', 'kesim_detay', 'cek_hareket',
                'audit_log']


def pg_dump_bul():
    """pg_dump.exe'yi bulur: elle verilen > PATH > Program Files taraması."""
    if PGDUMP_ELLE:
        return PGDUMP_ELLE if Path(PGDUMP_ELLE).exists() else None
    yol = shutil.which('pg_dump')
    if yol:
        return yol
    # Windows'ta PostgreSQL genelde PATH'e eklenmez; klasik konumları tara.
    desenler = [
        r'C:\Program Files\PostgreSQL\*\bin\pg_dump.exe',
        r'C:\Program Files (x86)\PostgreSQL\*\bin\pg_dump.exe',
    ]
    bulunanlar = []
    for d in desenler:
        bulunanlar.extend(glob.glob(d))
    if not bulunanlar:
        return None
    # En yüksek sürüm numarasını seç (…\PostgreSQL\17\bin\…)

    def surum(p):
        try:
            return int(Path(p).parent.parent.name)
        except ValueError:
            return 0
    return sorted(bulunanlar, key=surum)[-1]


motor = create_engine(VT_URL)
try:
    denetci = inspect(motor)
    mevcut = set(denetci.get_table_names())
except Exception as e:
    print("HATA: Veritabanına bağlanılamadı.")
    print(f"  {str(e)[:300]}")
    print()
    print("  Kontrol edin: PostgreSQL servisi çalışıyor mu, .env'deki")
    print("  kullanıcı/şifre/port doğru mu?")
    sys.exit(1)

pg = motor.dialect.name in ('postgresql', 'postgres')

print("=" * 70)
print(" MILESTONE ERP - TEST VERISI SIFIRLAMA (Windows)")
print("=" * 70)
kaynak = urlparse(VT_URL)
print(f" Veritabani : {kaynak.path.lstrip('/')} @ {kaynak.hostname or 'yerel'}"
      f":{kaynak.port or 5432}")
print(f" Surucu     : {motor.dialect.name}")
print(f" Klasor     : {os.getcwd()}")
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
            korunan_sayim[t] = b.execute(
                text(f'SELECT COUNT(*) FROM "{t}"')).scalar() or 0

print("-" * 70)
print(" SILINECEK")
print("-" * 70)
for t in SIL_SIRASI:
    if t in sayim:
        isaret = '.' if sayim[t] == 0 else 'X'
        print(f"   {isaret} {t:<20s} {sayim[t]:>7,} kayit")
if eksik:
    print(f"\n   (tabloda yok, atlanacak: {', '.join(eksik)})")
print(f"\n   TOPLAM {toplam:,} kayit")
print()

print("-" * 70)
print(" KORUNACAK")
print("-" * 70)
for t, aciklama in KORUNAN.items():
    n = korunan_sayim.get(t, 0)
    print(f"   + {t:<16s} {n:>6,} kayit   {aciklama}")
print()

if not ONAYLA:
    print("=" * 70)
    print(" RAPOR MODU - HICBIR SEY SILINMEDI")
    print()
    print(" Yukaridaki listeyi dikkatle okuyun. Dogruysa:")
    print("   python sifirla_windows.py --onayla")
    print()
    print(" ! Bu islem GERI ALINAMAZ.")
    print("=" * 70)
    sys.exit(0)

if toplam == 0:
    print("=" * 70)
    print(" Silinecek kayit yok - veritabani zaten temiz.")
    print("=" * 70)
    sys.exit(0)

# ── Yedek (zorunlu) ──
print("-" * 70)
print(" YEDEK ALINIYOR")
print("-" * 70)
if YEDEK_ATLA:
    print("   ! --yedek-atla verildi, yedek ALINMADI.")
elif pg:
    pgdump = pg_dump_bul()
    if not pgdump:
        print("   X pg_dump.exe bulunamadi - islem IPTAL edildi.")
        print()
        print("     PostgreSQL kurulu ise su klasorde olmali:")
        print(r"       C:\Program Files\PostgreSQL\<surum>\bin\pg_dump.exe")
        print()
        print("     Yolu elle verin:")
        print(r'       python sifirla_windows.py --onayla --pgdump="C:\Program Files\PostgreSQL\17\bin\pg_dump.exe"')
        sys.exit(1)
    print(f"   pg_dump: {pgdump}")

    damga = datetime.now().strftime('%Y%m%d_%H%M%S')
    hedef_dizin = Path.home() / 'Desktop' / 'milestone-yedekler'
    if not (Path.home() / 'Desktop').exists():
        hedef_dizin = Path.home() / 'milestone-yedekler'
    hedef_dizin.mkdir(parents=True, exist_ok=True)
    hedef = hedef_dizin / f'milestone_sifirlama_oncesi_{damga}.dump'

    ortam = dict(os.environ)
    if kaynak.password:
        ortam['PGPASSWORD'] = unquote(kaynak.password)
    komut = [pgdump, '-Fc', '-f', str(hedef)]
    if kaynak.hostname:
        komut += ['-h', kaynak.hostname]
    if kaynak.port:
        komut += ['-p', str(kaynak.port)]
    if kaynak.username:
        komut += ['-U', unquote(kaynak.username)]
    komut.append(kaynak.path.lstrip('/'))
    try:
        s = subprocess.run(komut, env=ortam, capture_output=True,
                           text=True, timeout=600)
        if s.returncode != 0 or not hedef.exists() or hedef.stat().st_size == 0:
            print("   X YEDEK BASARISIZ - islem IPTAL edildi, hicbir sey silinmedi.")
            print(f"     {(s.stderr or '').strip()[:300]}")
            sys.exit(1)
        print(f"   + {hedef}")
        print(f"     ({hedef.stat().st_size / 1024:.0f} KB)")
    except subprocess.TimeoutExpired:
        print("   X pg_dump zaman asimi - islem IPTAL edildi.")
        sys.exit(1)
    except Exception as e:
        print(f"   X Yedek hatasi: {str(e)[:200]}")
        print("     Islem IPTAL edildi.")
        sys.exit(1)
else:
    print("   PostgreSQL degil; pg_dump atlandi (dosyayi elle kopyalayin).")
print()

# ── Silme: TEK İŞLEM ──
print("-" * 70)
print(" SILINIYOR")
print("-" * 70)
silinen_toplam = 0
try:
    with motor.begin() as b:
        if pg:
            b.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        for t in SIL_SIRASI:
            if t not in sayim:
                continue
            b.execute(text(f'DELETE FROM "{t}"'))
            if sayim[t]:
                print(f"   + {t:<20s} {sayim[t]:>7,} kayit silindi")
            silinen_toplam += sayim[t]
        if pg:
            for t in DIZI_SIFIRLA:
                if t in mevcut:
                    b.execute(text(
                        f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), 1, false)"
                    ))
            print("   + tamsayi kimlik sayaclari 1'e cekildi")
except Exception as e:
    print(f"\n   X HATA: {str(e)[:400]}")
    print("   Islem geri alindi - HICBIR SEY SILINMEDI.")
    sys.exit(1)

# ── Doğrulama ──
print()
print("-" * 70)
print(" DOGRULAMA")
print("-" * 70)
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
            isaret = '+' if n == beklenen else 'X'
            print(f"   {isaret} {t:<16s} {n:>6,} kayit korundu (once {beklenen:,})")
            if n != beklenen:
                sorun.append((t, n))

if sorun:
    print("\n   X Beklenmeyen durum:")
    for t, n in sorun:
        print(f"     {t}: {n} kayit")
    sys.exit(1)

print()
print("=" * 70)
print(f" TAMAMLANDI - {silinen_toplam:,} kayit silindi")
print()
print(" SONRAKI ADIMLAR (Windows kopyasi icin):")
print("   1) Uygulamayi yeniden baslatin")
print("   2) Ayarlar > Kasalar: kasa tanimlarini girin")
print("   3) Ayarlar > Bankalar: banka hesaplarini girin")
print("   4) Cari Hesaplar, sonra Stok")
print()
print(" Kullanicilar, yetkiler, listeler, firma logosu ve kur arsivi")
print(" oldugu gibi duruyor.")
print()
print(" NOT: Bu islem SADECE bu makinenin veritabanini temizledi.")
print(" Veritabani depoda olmadigi icin GitHub'a gonderilecek bir")
print(" degisiklik OLUSMADI. Pardus'ta da temizlemek isterseniz orada")
print(" sifirla.py'yi ayrica calistirin.")
print("=" * 70)

#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — SEÇİCİ SIFIRLAMA  ·  R2
#
#  ── R1'DEN FARKI ──
#    sifirla.py (R1) `cariler` tablosunu SİLİYORDU. Bu sürüm cari
#    firma kayıtlarını KORUR — yalnızca hareketlerini siler. Ayrıca
#    R1'de eksik olan üç tablo eklendi: sabit_gider, nakit_plan,
#    konteyner. R1 ile sıfırlarsanız bu tablolardaki test verisi
#    kalırdı.
#
#  ══ KORUNUR (6 tablo) ══
#    cariler       Cari firma kayıtları (unvan, vergi no, adres,
#                  risk limiti, ödeme vadesi...). Cari'de ÖNBELLEK
#                  BAKİYE ALANI YOK — bakiye hareketlerden
#                  hesaplandığı için hareketleri silmek bakiyeyi
#                  kendiliğinden sıfırlar. Hayalet bakiye kalmaz.
#    kullanicilar  Kullanıcılar, şifreler, yetkiler
#    veriler       Ayarlar → Listeler (cins, yüzey, ödeme, ülke),
#                  firma bilgileri, LOGO, SMTP, KDV oranları
#    doviz_kur     TCMB kur arşivi (yeniden çekmek uzun sürer)
#
#  ══ SİLİNİR (27 tablo) ══
#    Tüm işlem verisi: stok, sipariş, proforma, fatura, sevkiyat,
#    kesim, maliyet, çek, kasa+hareketleri, cari hareketleri,
#    KDV iade, konteyner, sabit gider, nakit planı, denetim izi,
#    banka tanımları.
#
#  ══ TAM KAPSAMA DENETİMİ ══
#    Betik, veritabanındaki her tablonun ya KORUNAN ya da SİLİNECEK
#    listesinde olduğunu doğrular. Bir tablo ikisinde de yoksa
#    ÇALIŞMAYI REDDEDER. Böylece ileride model eklendiğinde bu
#    betiği güncellemeyi unutmak sessiz kalıntı bırakmaz.
#
#  ══ GÜVENLİK ══
#    • --onayla OLMADAN HİÇBİR ŞEY SİLMEZ; yalnızca rapor verir.
#    • Silmeden önce pg_dump yedeği alır; yedek başarısızsa İPTAL.
#    • Tek transaction: bir tablo hata verirse HİÇBİRİ silinmez.
#    • Yabancı anahtar sırasına göre siler (çocuk tablo önce).
#    • Silme sonrası korunan tabloların sayısı DEĞİŞMEDİ mi diye
#      kontrol eder.
#
#  KULLANIM (proje dizininde):
#      venv/bin/python sifirla2.py             # RAPOR — hiçbir şey silinmez
#      venv/bin/python sifirla2.py --onayla    # SİLER
#
#  ⚠ GERİ ALINAMAZ.
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

ONAY = '--onayla' in sys.argv
VT_URL = os.environ.get('DATABASE_URL')

if not VT_URL:
    print("HATA: DATABASE_URL bulunamadı (.env okunamadı).")
    print("  Adres olmadan yanlış veritabanına bağlanabilirdim.")
    sys.exit(1)

# ── Silinecek tablolar ──
#
# SIRA ELLE TUTULMUYOR — aşağıda modelin topolojik sırasından
# TÜRETİLİYOR. Bu liste yalnızca "hangi tablolar silinecek"i söyler.
#
# NEDEN: elle sıralanan sürüm üretimde patladı. `konteyner`
# tablosu `proforma`ya yabancı anahtarla bağlıydı ama listede
# proformadan SONRA geliyordu:
#     ForeignKeyViolation: "konteyner_proforma_id_fkey"
# Tek transaction sayesinde hiçbir şey silinmedi, ama elle
# sıralama her yeni yabancı anahtarda aynı hatayı üretir.
# SQLAlchemy bağımlılık sırasını zaten biliyor; ondan alalım.
SILINECEK_TABLOLAR = [
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
    'konteyner',
    'sevkiyat_kayit',
    'siparis_kayit',
    # KDV iade
    'kdv_iade_dosya',
    # Maliyet
    'maliyetler',
    # Stok
    'stok_cikis', 'blok_stok', 'plaka_stok', 'ebatli_stok',
    # Nakit akışı
    'nakit_plan', 'sabit_gider',
    # CRM — cari_kisi ve cari_erisim KORUNUYOR (aşağıda), yalnızca
    # aktivite siliniyor.
    'cari_aktivite',
    # Finans — cariler KORUNUYOR, yalnızca hareketleri siliniyor
    'kasa_hareket', 'cari_hareket', 'kasa', 'banka',
]

KORUNAN = {
    'cariler': 'Cari firma kayıtları (hareketleri silinir)',
    'kullanicilar': 'Kullanıcılar, şifreler, yetkiler',
    'veriler': 'Listeler, firma bilgisi, LOGO, SMTP, KDV ayarları',
    'doviz_kur': 'TCMB kur arşivi',

    # ── CRM (R3) ──
    # Bu ikisi CARİ KAYDININ PARÇASI, işlem verisi değil:
    #
    #   cari_kisi   Müşterideki kişiler — satın almacı, lojistik,
    #               muhasebe. Cari kartını koruyup kişilerini silmek,
    #               kartın yarısını atmak olurdu. Üstelik göç bunları
    #               eski `yetkili` alanından taşıdı; silinirse o bilgi
    #               bir daha geri gelmez.
    #
    #   cari_erisim Kapalı müşterilere verilmiş istisna erişimler.
    #               Silinirse satış ekibi sessizce müşteri kaybeder;
    #               kimse "erişimim kalktı" diye uyarı almaz.
    #
    # cari_aktivite ise SİLİNİR: temas geçmişi işlem verisidir ve
    # sıfırlanan siparişlere/tekliflere atıfta bulunur. Tutmak,
    # olmayan belgelerden söz eden notlar bırakırdı.
    'cari_kisi': 'Müşteri kişileri (satın alma, lojistik, muhasebe)',
    'cari_erisim': 'Kapalı müşterilere verilmiş istisna erişimler',
}

# Tamsayı birincil anahtarlı tablolar — dizileri 1'e çekilir.
DIZI_SIFIRLA = ['banka', 'kasa', 'kasa_hareket', 'kesim_detay',
                'cek_hareket', 'audit_log', 'konteyner', 'cari_aktivite']

# ── SİLME SIRASI: modelin topolojik sırasından, TERS ──
# metadata.sorted_tables ebeveynden çocuğa sıralı; silmek için
# tersi gerekiyor (çocuk önce).
try:
    os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
    sys.path.insert(0, str(Path('.').resolve()))
    import flask_app as _fa  # noqa: F401
    from models import db as _db
    _sirali = [t.name for t in _db.metadata.sorted_tables]
    _sirali.reverse()
    _hedef = set(SILINECEK_TABLOLAR)
    # Modelde bilinen tablolar doğru sırayla; modelde olmayanlar
    # (varsa) sona.
    SIL_SIRASI = [t for t in _sirali if t in _hedef]
    SIL_SIRASI += [t for t in SILINECEK_TABLOLAR if t not in _sirali]
    if set(SIL_SIRASI) != _hedef:
        print(" ✗ Sıra türetilemedi — DOSYAYA DOKUNULMADI.")
        sys.exit(1)
except Exception as _e:
    print(f" ✗ Silme sırası modelden türetilemedi: {_e}")
    print("   Elle sıralamaya düşmek yabancı anahtar hatası riski")
    print("   taşır; çalışmayı reddediyorum.")
    sys.exit(1)

motor = create_engine(VT_URL)
denetci = inspect(motor)
mevcut = set(denetci.get_table_names())
pg = motor.dialect.name in ('postgresql', 'postgres')

print("═" * 70)
print(" MILESTONE ERP — SEÇİCİ SIFIRLAMA  (R2: cari kayıtları korunur)")
print("═" * 70)
kaynak = urlparse(VT_URL)
print(f" Veritabanı : {kaynak.path.lstrip('/')} @ {kaynak.hostname or 'yerel'}")
print(f" Sürücü     : {motor.dialect.name}")
print()

# ── TAM KAPSAMA DENETİMİ ──
# Her tablo ya korunmalı ya silinmeli. Ucu acik tablo kalirsa
# sessizce test verisi kalir; bunu HATA sayiyoruz.
bilinen = set(SILINECEK_TABLOLAR) | set(KORUNAN)
gozden_kacan = sorted(t for t in mevcut
                      if t not in bilinen and t != 'alembic_version')
if gozden_kacan:
    print(" ✗ KAPSAM DIŞI TABLO(LAR) VAR — çalışmayı reddediyorum:")
    for t in gozden_kacan:
        print(f"     {t}")
    print()
    print("   Bu tablolar ne korunuyor ne siliniyor. Sessizce test")
    print("   verisi bırakmamak için betiği güncelleyin.")
    sys.exit(1)
print(f" ✓ kapsama tam — {len(mevcut)} tablonun hepsi sınıflandırılmış")
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

print("─" * 70)
print(" KORUNACAK")
print("─" * 70)
for t, aciklama in KORUNAN.items():
    n = korunan_sayim.get(t, 0)
    print(f"   {t:<16s} {n:>7,} kayıt   {aciklama}")

print()
print("─" * 70)
print(" SİLİNECEK")
print("─" * 70)
for t in SIL_SIRASI:
    if t in sayim and sayim[t]:
        print(f"   {t:<16s} {sayim[t]:>7,} kayıt")
bos = [t for t in SIL_SIRASI if sayim.get(t) == 0]
if bos:
    print(f"   (zaten boş: {', '.join(bos)})")
if eksik:
    print(f"   (tabloda yok: {', '.join(eksik)})")
print()
print(f"   TOPLAM {toplam:,} kayıt silinecek")

if not ONAY:
    print()
    print("═" * 70)
    print(" RAPOR MODU — hiçbir şey silinmedi.")
    print()
    print(" Silmek için:")
    print("   venv/bin/python sifirla2.py --onayla")
    print()
    print(" ⚠ Önce elle yedek alın:")
    print("   sudo /usr/local/bin/milestone-yedek.sh")
    print("═" * 70)
    sys.exit(0)

# ── Yedek ──
print()
print("─" * 70)
print(" YEDEK")
print("─" * 70)
if pg:
    hedef = Path.home() / 'yedekler'
    hedef.mkdir(exist_ok=True)
    dosya = hedef / f"sifirlama-oncesi-{datetime.now():%Y%m%d_%H%M%S}.dump"
    try:
        ortam = dict(os.environ)
        if kaynak.password:
            ortam['PGPASSWORD'] = kaynak.password
        sonuc = subprocess.run(
            ['pg_dump', '-Fc', '-f', str(dosya),
             '-h', kaynak.hostname or 'localhost',
             '-p', str(kaynak.port or 5432),
             '-U', kaynak.username or 'postgres',
             kaynak.path.lstrip('/')],
            env=ortam, capture_output=True, text=True, timeout=600)
        if sonuc.returncode != 0 or not dosya.exists() or dosya.stat().st_size < 1024:
            print(" ✗ Yedek ALINAMADI — silme İPTAL edildi.")
            print(f"   {(sonuc.stderr or '').strip()[:200]}")
            sys.exit(1)
        print(f" ✓ {dosya}  ({dosya.stat().st_size / 1024:.0f} KB)")
    except FileNotFoundError:
        print(" ✗ pg_dump bulunamadı — silme İPTAL edildi.")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(" ✗ Yedek zaman aşımına uğradı — silme İPTAL edildi.")
        sys.exit(1)
else:
    print(" ⚠ PostgreSQL değil — otomatik yedek atlandı.")

# ── Silme (tek transaction) ──
print()
print("─" * 70)
print(" SİLİNİYOR")
print("─" * 70)
with motor.begin() as b:
    for t in SIL_SIRASI:
        if t not in mevcut:
            continue
        n = sayim.get(t, 0)
        b.execute(text(f'DELETE FROM "{t}"'))
        if n:
            print(f"   {t:<16s} {n:>7,} kayıt silindi")
    if pg:
        for t in DIZI_SIFIRLA:
            if t in mevcut:
                try:
                    b.execute(text(
                        f"SELECT setval(pg_get_serial_sequence('\"{t}\"','id'), 1, false)"))
                except Exception:
                    pass

# ── Doğrulama ──
print()
print("─" * 70)
print(" DOĞRULAMA")
print("─" * 70)
hatali = False
with motor.connect() as b:
    for t in SIL_SIRASI:
        if t not in mevcut:
            continue
        n = b.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() or 0
        if n:
            print(f"   ✗ {t:<16s} hâlâ {n:,} kayıt var")
            hatali = True
    for t in KORUNAN:
        if t not in mevcut:
            continue
        n = b.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() or 0
        beklenen = korunan_sayim.get(t, 0)
        isaret = '✓' if n == beklenen else '✗'
        if n != beklenen:
            hatali = True
        print(f"   {isaret} {t:<16s} {n:>7,} kayıt korundu (önce {beklenen:,})")

print()
print("═" * 70)
if hatali:
    print(" ✗ DOĞRULAMA BAŞARISIZ — yedekten dönmeyi değerlendirin.")
    sys.exit(1)
print(" ✓ SIFIRLAMA TAMAMLANDI")
print()
print(" Cari firma kayıtlarınız duruyor; hareketleri sıfırlandı.")
print(" Bakiyeler hareketlerden hesaplandığı için hepsi 0 görünür.")
print()
print(" SONRAKİ ADIMLAR:")
print("   1) Kasa/banka hesaplarını yeniden tanımlayın (açılış bakiyesiyle)")
print("   2) Ayarlar → Listeler'i gözden geçirin")
print("   3) Sabit giderleri girin (kira, maaş, SGK...)")
print("   4) venv/bin/python degismezlik_denetim.py")
print("═" * 70)

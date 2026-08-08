#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — ALEMBIC AYARLARI  ·  M3
#
#  İKİ SORUN, İKİSİ DE GÖÇÜ ENGELLİYOR:
#
#  ── M3a · İSİMSİZ KISIT ÇÖKMESİ  [şu an yaşanıyor] ──
#    `goc.py olustur` sonrası upgrade çöküyor:
#
#      sqlalchemy.exc.CompileError: Can't emit DROP CONSTRAINT for
#      constraint ForeignKeyConstraint(... table='proforma_kalem');
#      it has no name
#
#    KÖK NEDEN: models.py'de 20 yabancı anahtarın HİÇBİRİNİN adı yok
#    (`db.ForeignKey('konteyner.id')` — name= verilmemiş). Veritabanı
#    ise sema_denetim.py ile büyümüş; o araç `ADD COLUMN` yapıyor ama
#    YABANCI ANAHTAR KISITINI EKLEMİYOR.
#
#    Sonuç: model ile veritabanı SÜTUN düzeyinde uyumlu ama KISIT
#    düzeyinde ayrışmış. Autogenerate farkı kapatmaya çalışıyor,
#    kısıtın adı olmadığı için DROP komutunu üretemiyor ve çöküyor.
#
#    ÇÖZÜM: autogenerate yabancı anahtar kısıtlarını KARŞILAŞTIRMASIN.
#    Sütunlar, tipler ve tablolar karşılaştırılmaya devam eder —
#    göç için gereken bunlar. FK kısıtları elle yönetilir.
#
#    NEDEN İSİMLENDİRME KURALI EKLEMİYORUZ: SQLAlchemy'ye naming
#    convention vermek DOĞRU uzun vadeli çözümdür ama mevcut
#    veritabanındaki kısıtların adları o kurala uymaz; autogenerate
#    20 kısıtı birden yeniden adlandırmaya kalkar. Dolu bir
#    veritabanında bu, göçten çok daha büyük bir risk. Şimdi değil.
#
#  ── M3b · TİP DEĞİŞİKLİĞİ GÖRÜNMÜYOR  [Numeric göçünün ön koşulu] ──
#    Alembic varsayılan olarak `compare_type=False` çalışır — sütun
#    TİPİ değişikliğini ALGILAMAZ.
#
#    Yani Float→Numeric göçü için model değiştirilse bile
#    `goc.py olustur` BOŞ revizyon üretir. Göç hiç yapılmamış olur
#    ve bunu kimse fark etmez.
#
#    ÇÖZÜM: compare_type=True.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python migration_ayarla.py            # rapor
#      venv/bin/python migration_ayarla.py --uygula   # uygula
#
#  ⚠ ÖN KOŞUL: migrations/ klasörü kurulmuş olmalı
#      venv/bin/python migration_kur.py --uygula
# ══════════════════════════════════════════════════════════════════════
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
ENV = Path('migrations/env.py')

if not ENV.exists():
    print("HATA: migrations/env.py yok — altyapı kurulmamış.")
    print("  venv/bin/python migration_kur.py --uygula")
    sys.exit(1)

ham = ENV.read_text(encoding='utf-8')

AYAR_BLOK = '''
# ══════════════════════════════════════════════════════════════════
#  MILESTONE AYARLARI  (M3)
# ══════════════════════════════════════════════════════════════════
def milestone_include_object(nesne, ad, tur, yansitildi, karsilastirilan):
    """Autogenerate'in NEYI karsilastiracagini belirler.

    YABANCI ANAHTAR KISITLARI DISLANIR — bilerek.

    models.py'deki 20 yabanci anahtarin hicbirinin ADI yok
    (db.ForeignKey(...) — name= verilmemis). Veritabani ise
    sema_denetim.py ile buyumus; o arac ADD COLUMN yapiyor ama
    KISIT eklemiyor. Sonuc: model ve veritabani sutun duzeyinde
    uyumlu, kisit duzeyinde ayrisik.

    Autogenerate bu farki kapatmaya calisinca isimsiz kisit icin
    DROP CONSTRAINT uretemiyor ve coküyor:
        CompileError: Can't emit DROP CONSTRAINT ... it has no name

    Sutunlar, tipler ve tablolar KARSILASTIRILMAYA DEVAM EDER —
    goc icin gereken bunlar. FK kisitlari elle yonetilir.
    """
    if tur == 'foreign_key_constraint':
        return False
    return True


def milestone_render_item(tur, nesne, autogen_context):
    """Ozel TypeDecorator tiplerini DUZ sa.Numeric olarak yazar.

    NEDEN GEREKLI: models.py'deki Para/Kur/Olcu birer TypeDecorator.
    Autogenerate bunlari `models.Olcu(precision=18, scale=3)` diye
    uretir ama revizyon dosyasi `models`'i ICE AKTARMAZ:
        NameError: name 'models' is not defined
    Uygulama gocun ortasinda coker.

    Veritabani zaten dekoratoru umursamaz — onun icin bu sutun
    NUMERIC(18,3)'tur. Bu yuzden duz sa.Numeric olarak yaziyoruz;
    revizyon bagimsiz ve okunabilir olur.
    """
    if tur == 'type' and nesne.__class__.__name__ in ('Para', 'Kur', 'Olcu'):
        autogen_context.imports.add('import sqlalchemy as sa')
        return 'sa.Numeric(precision=%d, scale=%d)' % (
            nesne.impl.precision or 18, nesne.impl.scale or 4)
    return False


MILESTONE_AYAR = {
    # compare_type: sutun TIPI degisikligini algila.
    # Varsayilan False'tur ve Float->Numeric gocu bu yuzden BOS
    # revizyon uretirdi — goc hic yapilmamis olur, kimse fark etmez.
    'compare_type': True,
    'compare_server_default': False,
    'include_object': milestone_include_object,
    'render_item': milestone_render_item,
}
'''

print("═" * 70)
print(" M3 · ALEMBIC AYARLARI")
print("═" * 70)
print()

# ── İMZA KONTROLÜ: PARÇA PARÇA ──
# DIKKAT: onceki surum yalnizca 'MILESTONE_AYAR' bloguna bakiyordu.
# Blok ilk kurulumdan kalinca betik "zaten uygulanmis" deyip cikiyor,
# sonradan eklenen render_item ASLA uygulanmiyordu. Bu iki kez yasandi:
# goc revizyonu `models.Para(...)` diye uretildi ve uygulaninca
# NameError ile cokecekti.
#
# Artik HER PARCA ayri kontrol edilir; eksik olan varsa is yapilir.
_parcalar = {
    'MILESTONE_AYAR bloğu': 'MILESTONE_AYAR',
    # DIKKAT: fonksiyon TANIMINI degil, ayar sozlugune BAGLANMIS
    # halini ariyoruz. Fonksiyon dosyada durup sozluge baglanmamis
    # olabilir — yasanan hata tam olarak buydu: render_item tanimliydi
    # ama context.configure'a gecmiyordu, dolayisiyla calismiyordu.
    'FK dışlama (include_object)': "'include_object': milestone_include_object",
    'tip yazımı (render_item)': "'render_item': milestone_render_item",
    'compare_type': "'compare_type': True",
}
_eksik = [ad for ad, imza in _parcalar.items() if imza not in ham]

if not _eksik:
    print(" ✓ Tüm ayarlar yerinde — yapılacak iş yok.")
    print()
    for ad in _parcalar:
        print(f"   ✓ {ad}")
    sys.exit(0)

if len(_eksik) < len(_parcalar):
    print(" ⚠ AYARLAR EKSİK — bir kısmı var, bir kısmı yok:")
    for ad, imza in _parcalar.items():
        print(f"   {'✓' if imza in ham else '✗ EKSİK'}  {ad}")
    print()
    print(" env.py kısmen ayarlanmış. Temiz kurulum için yedekten")
    print(" geri alıp bu betiği tekrar çalıştırın:")
    print("   cp $(ls -t migrations/env.py.yedek-* | head -1) migrations/env.py")
    print("   venv/bin/python migration_ayarla.py --uygula")
    sys.exit(1)

# ── Yerleştirme noktalarını bul ────────────────────────────────────
yeni = ham
degisiklikler = []

# 1) Ayar bloğunu run_migrations_offline'dan önce ekle
if 'def run_migrations_offline' in yeni:
    yeni = yeni.replace('def run_migrations_offline',
                        AYAR_BLOK + '\ndef run_migrations_offline', 1)
    degisiklikler.append('ayar bloğu eklendi (compare_type + FK dışlama)')
else:
    print(" ✗ 'def run_migrations_offline' bulunamadı — env.py beklenenden farklı.")
    sys.exit(1)

# 2) context.configure çağrılarına ayarları geçir
#
# NOT: Flask-Migrate'in urettigi env.py `get_metadata()` ve `conf_args`
# kullanir (duz `target_metadata` degil). Kaliplar buna gore yazildi.
sayac = 0

# Cevrimdisi (offline) mod
OFF_ESKI = """    context.configure(
        url=url, target_metadata=get_metadata(), literal_binds=True
    )"""
OFF_YENI = """    context.configure(
        url=url, target_metadata=get_metadata(), literal_binds=True,
        **MILESTONE_AYAR
    )"""
if OFF_ESKI in yeni:
    yeni = yeni.replace(OFF_ESKI, OFF_YENI, 1)
    sayac += 1

# Cevrimici (online) mod — conf_args sozlugune ekle
ON_ESKI = """        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **conf_args
        )"""
ON_YENI = """        conf_args.update(MILESTONE_AYAR)
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **conf_args
        )"""
if ON_ESKI in yeni:
    yeni = yeni.replace(ON_ESKI, ON_YENI, 1)
    sayac += 1

if sayac:
    degisiklikler.append(f'context.configure güncellendi ({sayac} yer)')

for d in degisiklikler:
    print(f"  ✓ {d}")
print()

# Sözdizimi doğrulaması
try:
    compile(yeni, 'env.py', 'exec')
    print(" ✓ sözdizimi doğrulandı (compile)")
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

if 'MILESTONE_AYAR' not in yeni or sayac < 2:
    print(" ✗ Ayarlar context.configure'a geçirilemedi — env.py beklenenden farklı.")
    print(" DOSYAYA DOKUNULMADI. env.py'yi elle düzenleyin:")
    print("   context.configure(..., compare_type=True,")
    print("                     include_object=milestone_include_object)")
    sys.exit(1)

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   venv/bin/python migration_ayarla.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = ENV.with_name(f'env.py.yedek-{damga}')
shutil.copy2(ENV, yedek)
ENV.write_text(yeni, encoding='utf-8')
print(f" ✓ migrations/env.py  (yedek: {yedek.name})")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print(" ⚠ BOZUK REVİZYONU TEMİZLEYİN")
print("   Ayarlar öncesinde üretilmiş revizyon varsa kullanılamaz.")
print("   1) venv/bin/python goc.py gecmis     ← listeyi görün")
print("   2) baseline DIŞINDAKİ dosyaları silin:")
print("      rm migrations/versions/<bozuk>.py")
print("   3) veritabanını baseline'a geri damgalayın:")
print("      MILESTONE_ACILIS_ATLA=1 FLASK_APP=flask_app.py \\")
print("        venv/bin/python -m flask db stamp <baseline_id>")
print()
print(" Sonra tekrar deneyin:")
print("   venv/bin/python goc.py olustur \"test\"")
print("   → artık FK kısıtı yüzünden çökmemeli")
print("═" * 70)

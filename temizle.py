#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — PROJE DİZİNİ TEMİZLİĞİ  ·  T
#
#  Dosya listesi tek tek incelenerek hazırlandı. Silinecek her grubun
#  gerekçesi aşağıda yazılı; kalacaklar da açıkça listeli.
#
#  ── YEDEKLER VARSAYILAN OLARAK KORUNUR ──
#    Betik yedeklere DOKUNMAZ. Silmek icin acikca istemek gerekir:
#        --yedekleri-sil
#
#    Neden: gercek veriye gecildikten sonra bu betigi yanlislikla
#    calistirmak pahali olur. Kod artiklarini temizlemek rutin bir
#    istir; yedek silmek degil. Ikisini ayni komuta baglamak, rutin
#    bir islemi tehlikeli hale getirir.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python temizle.py                  # RAPOR
#      venv/bin/python temizle.py --uygula         # sil (yedekler KALIR)
#      venv/bin/python temizle.py --uygula --yedekleri-sil
# ══════════════════════════════════════════════════════════════════════
import os
import shutil
import sys
from pathlib import Path

UYGULA = '--uygula' in sys.argv
# Yedekler VARSAYILAN OLARAK korunur — silmek icin acik istek gerekir.
YEDEKLERI_SIL = '--yedekleri-sil' in sys.argv
KOK = Path('.').resolve()

if not (KOK / 'flask_app.py').exists():
    print("HATA: flask_app.py bu klasörde yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

EV = Path.home()

# ══════════════════════════════════════════════════════════════════
#  SİLİNECEKLER — grup grup, gerekçeli
# ══════════════════════════════════════════════════════════════════
GRUPLAR = []

# 1) Yama ve onarım betikleri
#    Hepsi UYGULANMIŞ durumda; yaptıkları değişiklik flask_app.py,
#    models.py ve şablonlarda duruyor. Artık kayıt işlevi de yok:
#    şema geçmişini Alembic (migrations/versions/) tutuyor, kod
#    geçmişini git tutuyor. Depoda da kalacaklar — gerekirse
#    `git show <commit>:yama_x.py` ile geri gelirler.
GRUPLAR.append((
    'Yama betikleri (uygulanmış)',
    sorted(KOK.glob('yama_*.py')),
    'Değişiklikleri koda işlendi. Şema geçmişi Alembic\'te,\n'
    '     kod geçmişi git\'te. Depodan geri alınabilir.',
))

GRUPLAR.append((
    'Onarım betikleri (kullanılmış)',
    sorted(KOK.glob('onarim_*.py')),
    'Tek seferlik veri onarımları — işleri bitti.',
))

# 2) Yedek dosyaları (.yedek-*)
#    Yama betiklerinin bıraktığı kopyalar. git zaten sürüm tutuyor.
_yedekler = sorted(KOK.glob('*.yedek-*'))
_yedekler += sorted((KOK / 'templates').glob('*.yedek-*'))
_yedekler += sorted((KOK / 'migrations').glob('*.yedek-*'))
GRUPLAR.append((
    'Yedek dosyaları (*.yedek-*)',
    _yedekler,
    'Yama betiklerinin bıraktığı kopyalar. Sürüm takibi git\'te.',
))

# 3) Python derleme önbelleği
_pycache = [p for p in KOK.rglob('__pycache__')
            if 'venv' not in p.parts and p.is_dir()]
GRUPLAR.append((
    'Python önbelleği (__pycache__)',
    _pycache,
    'Otomatik üretilir. İçinde SİLİNMİŞ revizyonların derlemeleri de\n'
    '     var (b5e453bb0e25, 8050e3292cb9) — kafa karıştırıcı.',
))

# 4) Uygulama yedekleri
if YEDEKLERI_SIL:
    GRUPLAR.append((
        'Uygulama yedekleri (backups/*.dump)  ⚠',
        sorted((KOK / 'backups').glob('*.dump')),
        'AÇIKCA istendi (--yedekleri-sil). Geri dönüşü yok.',
    ))

# 5) Zamanlanmış sistem yedekleri
if YEDEKLERI_SIL:
    GRUPLAR.append((
        'Sistem yedekleri (~/yedekler/*.dump)  ⚠',
        sorted((EV / 'yedekler').glob('*.dump')),
        'AÇIKCA istendi. Klasör KALIR (timer oraya yazıyor).',
    ))

# 6) Günlük dosyası
_log = [p for p in [KOK / 'erp.log'] if p.exists()]
GRUPLAR.append((
    'Günlük dosyası (erp.log)',
    _log,
    'Uygulama yeniden üretir. Depoya da sızmıştı.',
))

# 7) Başıboş SQLite veritabanı  ← DİKKAT
#    flask_app.py:213
#        db_url = os.environ.get('DATABASE_URL', 'sqlite:///milestone.db')
#    DATABASE_URL ayarlı DEĞİLKEN uygulama SQLite'a düşüyor ve bu
#    dosyayı yaratıyor. Bir betik .env yüklemeyi atlarsa sessizce
#    YANLIŞ VERİTABANINA yazar — asıl PostgreSQL'e değil.
#    Dosyanın varlığı bunun en az bir kez olduğunu gösteriyor.
_sqlite = [p for p in [KOK / 'instance' / 'milestone.db'] if p.exists()]
GRUPLAR.append((
    'Başıboş SQLite veritabanı (instance/milestone.db)',
    _sqlite,
    'DATABASE_URL ayarlı değilken oluşan YEDEK veritabanı\n'
    '     (flask_app.py:213). Varlığı, bir betiğin .env yüklemeden\n'
    '     çalıştığını gösteriyor. Silmek doğru; ama tekrar oluşursa\n'
    '     hangi betiğin .env okumadığını araştırmak gerekir.',
))

# ══════════════════════════════════════════════════════════════════
#  KORUNACAKLAR — silinmeyeceği açıkça yazılı
# ══════════════════════════════════════════════════════════════════
KORUNAN = [
    ('.env', 'veritabanı bağlantısı ve SECRET_KEY'),
    ('.gitignore', 'depo yapılandırması'),
    ('flask_app.py · models.py · server.py', 'uygulama'),
    ('export_utils.py · yedek.py', 'uygulama modülleri'),
    ('requirements.txt · requirements_pardus.txt', 'bağımlılıklar'),
    ('blueprints/ (5 dosya)', 'aktif — server.py kaydediyor'),
    ('templates/*.html (25)', 'arayüz'),
    ('static/ (4)', 'PWA ve stil'),
    ('migrations/ kaynak + 3 revizyon', 'ŞEMA GEÇMİŞİ — silinemez'),
    ('sema_ form_ sessiz_ zincir_ js_ degismezlik_denetim.py', '6 denetim aracı'),
    ('goc.py · migration_kur.py · migration_ayarla.py', 'şema göçü'),
    ('sifirla.py · sifirla_windows.py', 'veri sıfırlama'),
    ('listeler_excel.py · envanter_kdv.py', 'veri aktarma'),
    ('tani_izli_kdv.py · tani_fatura_kilit.py', 'tanı araçları'),
    ('kur_arsivi_doldur.py · kur_guncelle.py', 'kur yönetimi'),
    ('backups/ · ~/yedekler/ klasörleri', 'klasörler her durumda kalır'),
]
if not YEDEKLERI_SIL:
    KORUNAN.append(('backups/*.dump · ~/yedekler/*.dump',
                    'YEDEKLER KORUNDU — silmek için --yedekleri-sil'))

print("═" * 74)
print(" MILESTONE ERP — PROJE DİZİNİ TEMİZLİĞİ")
print("═" * 74)
print(f" Dizin: {KOK}")
print()

toplam_adet = toplam_boyut = 0
for ad, ogeler, gerekce in GRUPLAR:
    ogeler = [p for p in ogeler if p.exists()]
    if not ogeler:
        continue
    boyut = 0
    for p in ogeler:
        try:
            boyut += (sum(f.stat().st_size for f in p.rglob('*') if f.is_file())
                      if p.is_dir() else p.stat().st_size)
        except OSError:
            pass
    toplam_adet += len(ogeler)
    toplam_boyut += boyut
    print(f" ── {ad}")
    print(f"    {len(ogeler)} öge · {boyut / 1024 / 1024:.2f} MB")
    print(f"     {gerekce}")
    for p in ogeler[:4]:
        try:
            gorunen = p.relative_to(KOK)
        except ValueError:
            gorunen = p
        print(f"       • {gorunen}")
    if len(ogeler) > 4:
        print(f"       … +{len(ogeler) - 4} öge daha")
    print()

print("─" * 74)
print(f" SİLİNECEK: {toplam_adet} öge · {toplam_boyut / 1024 / 1024:.2f} MB")
print("─" * 74)
print()
print(" KORUNACAKLAR:")
for ad, neden in KORUNAN:
    print(f"   ✓ {ad:52s} {neden}")
print()

if not UYGULA:
    print("═" * 74)
    print(" RAPOR MODU — HİÇBİR ŞEY SİLİNMEDİ")
    print()
    if YEDEKLERI_SIL:
        print(" ⚠ --yedekleri-sil VERİLDİ: yedekler de silinecek.")
        print("    Önce yedek alın: sudo /usr/local/bin/milestone-yedek.sh")
    else:
        print(" ✓ Yedekler KORUNACAK (silmek için --yedekleri-sil)")
    print()
    print(" Silmek için:")
    print("   venv/bin/python temizle.py --uygula"
          + (" --yedekleri-sil" if YEDEKLERI_SIL else ""))
    print("═" * 74)
    sys.exit(0)

# ── Yedek silinecekse ONAY İSTE ────────────────────────────────────
if YEDEKLERI_SIL:
    print("═" * 74)
    print(" ⚠ TÜM VERİTABANI YEDEKLERİ SİLİNECEK")
    print("═" * 74)
    print()
    print(" Silme sonrası ELİNİZDE YEDEK KALMAYACAK. Geri dönüşü yoktur.")
    print(" Devam etmeden önce güncel bir yedek aldığınızdan emin olun:")
    print("   sudo /usr/local/bin/milestone-yedek.sh")
    print()
    onay = input(" Yedekleri silmek istediğinizden EMİN misiniz? (evet/hayir): ")
    if onay.strip().lower() not in ('evet', 'e'):
        print(" İptal edildi — hiçbir şey silinmedi.")
        sys.exit(0)
    print()

print()
silinen = hata = 0
for ad, ogeler, _ in GRUPLAR:
    for p in [x for x in ogeler if x.exists()]:
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            silinen += 1
        except OSError as exc:
            print(f"   ✗ {p}: {exc}")
            hata += 1

print("═" * 74)
print(f" ✓ {silinen} öge silindi" + (f" · {hata} hata" if hata else ""))
print("═" * 74)
print()
if YEDEKLERI_SIL:
    print(" ŞİMDİ YENİ TABAN YEDEĞİ ALIN — elinizde yedek yok:")
    print("   sudo /usr/local/bin/milestone-yedek.sh")
    print("   ls -la ~/yedekler/")
    print()
print(" Ardından doğrulama:")
print("   git status --short          # beklenmedik silme var mı")
print("   venv/bin/python goc.py durum")
print("   venv/bin/python zincir_denetim.py")
print("   venv/bin/python degismezlik_denetim.py")
print("   sudo systemctl restart milestone-erp")
print("═" * 74)

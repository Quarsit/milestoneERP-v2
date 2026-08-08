#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — MIGRATION ALTYAPISI KURULUMU  ·  M1
#
#  SORUN:
#    Şema değişiklikleri şu an iki yoldan yapılıyor:
#      1. sema_denetim.py --uygula  → EKSİK SÜTUN ekler
#      2. Elle ALTER TABLE          → tip değişikliği için
#
#    İkincisi bugün yaşandı: hs_kodu 30→120 genişletmesi için yedi
#    ALTER TABLE komutunu psql'de elle çalıştırdık. Bu:
#      • Tekrarlanabilir değil (Windows kopyasında da yapılmalı)
#      • Kayıt bırakmıyor (kim, ne zaman, neden)
#      • Geri alınamıyor
#      • Yeni kurulumda unutulur
#
#    Flask-Migrate zaten requirements.txt'de (4.0.7) ama migrations/
#    klasörü yok — kurulmamış.
#
#  ── KRİTİK: MEVCUT ŞEMA "BASELINE"LANMALI ──
#    Alembic'i boş bir projeye kurmak kolaydır. Burada 28 tablo
#    DOLU bir veritabanı var. `alembic upgrade` çalıştırılırsa
#    Alembic "hiç migration uygulanmamış" sanıp tabloları SIFIRDAN
#    yaratmaya kalkar ve çöker.
#
#    Doğru yol: mevcut şemayı BAŞLANGIÇ NOKTASI olarak damgalamak
#    (`alembic stamp head`). Böylece Alembic "buraya kadar zaten
#    uygulanmış" bilgisini kaydeder ve bundan SONRAKİ değişiklikleri
#    yönetir.
#
#  ── İŞ BÖLÜMÜ: ALEMBIC UYGULAR, sema_denetim DOĞRULAR ──
#    sema_denetim.py KALDIRILMIYOR. Rolü değişiyor:
#      Alembic       → şema değişikliğini UYGULAR (versiyonlu, geri alınabilir)
#      sema_denetim  → model ile veritabanının uyuştuğunu DOĞRULAR
#    İkisi birbirini denetler. Alembic'in kaçırdığı bir şey olursa
#    sema_denetim yakalar; bu, tek kaynağa güvenmekten iyidir.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python migration_kur.py            # durum raporu
#      venv/bin/python migration_kur.py --uygula   # kur ve damgala
#
#  ⚠ ÖNCE YEDEK: sudo /usr/local/bin/milestone-yedek.sh
# ══════════════════════════════════════════════════════════════════════
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.getcwd())

UYGULA = '--uygula' in sys.argv
MIG = Path('migrations')

print("═" * 74)
print(" M1 · MIGRATION ALTYAPISI (Alembic / Flask-Migrate)")
print("═" * 74)
print()

# ── Ön koşullar ────────────────────────────────────────────────────
try:
    import flask_migrate  # noqa: F401
    surum = getattr(__import__('flask_migrate'), '__version__', '?')
    print(f" ✓ Flask-Migrate kurulu")
except ImportError:
    print(" ✗ Flask-Migrate KURULU DEĞİL")
    print("   venv/bin/pip install Flask-Migrate==4.0.7")
    sys.exit(1)

import flask_app  # noqa: E402
from models import db  # noqa: E402

app = flask_app.app

with app.app_context():
    from sqlalchemy import inspect as _inspect
    mufettis = _inspect(db.engine)
    tablolar = [t for t in mufettis.get_table_names() if t != 'alembic_version']
    damgali = 'alembic_version' in mufettis.get_table_names()
    surum_kaydi = None
    if damgali:
        try:
            from sqlalchemy import text as _text
            with db.engine.connect() as b:
                surum_kaydi = b.execute(
                    _text('SELECT version_num FROM alembic_version')).scalar()
        except Exception:
            pass

print(f" Veritabanında tablo : {len(tablolar)}")
print(f" migrations/ klasörü : {'VAR' if MIG.exists() else 'YOK'}")
print(f" Alembic damgası     : {surum_kaydi or 'YOK'}")
print()

if MIG.exists() and damgali and surum_kaydi:
    print(" ✓ Migration altyapısı ZATEN KURULU.")
    print()
    print(" Bundan sonra şema değişikliği:")
    print("   1) models.py'yi düzenleyin")
    print("   2) venv/bin/flask db migrate -m 'ne yaptigini yaz'")
    print("   3) migrations/versions/ altındaki dosyayı OKUYUN")
    print("   4) venv/bin/flask db upgrade")
    print("   5) venv/bin/python sema_denetim.py     ← doğrulama")
    sys.exit(0)

print("─" * 74)
print(" YAPILACAKLAR")
print("─" * 74)
adimlar = []
if not MIG.exists():
    adimlar.append("migrations/ klasörünü oluştur (flask db init)")
if not damgali or not surum_kaydi:
    adimlar.append(f"mevcut {len(tablolar)} tabloyu BAŞLANGIÇ olarak damgala")
    adimlar.append("  → Alembic bunları 'zaten uygulanmış' sayacak")
    adimlar.append("  → damgalanmazsa sıfırdan yaratmaya kalkar ve ÇÖKER")
for a in adimlar:
    print(f"   • {a}")
print()

if not UYGULA:
    print("═" * 74)
    print(" RAPOR MODU — HİÇBİR ŞEY DEĞİŞTİRİLMEDİ")
    print()
    print(" Uygulamak için:")
    print("   venv/bin/python migration_kur.py --uygula")
    print()
    print(" ⚠ ÖNCE YEDEK: sudo /usr/local/bin/milestone-yedek.sh")
    print("═" * 74)
    sys.exit(0)

# ── Kurulum ────────────────────────────────────────────────────────
# MILESTONE_ACILIS_ATLA: Alembic uygulamayi ICE AKTARIR; acilis
# isleri (db.create_all, seed, TCMB kur cekme) o anda calisirsa
# HENUZ EKLENMEMIS sutunu sorgulayip coker (bkz. yama_m2).
ORTAM = dict(os.environ, FLASK_APP='flask_app.py',
             MILESTONE_ACILIS_ATLA='1')

# DIKKAT: 'flask' komutu SISTEM python'una isaret edebilir; o zaman
# sqlalchemy bulunamaz ve 'No such command: db' hatasi alinir.
# Bu yuzden calisan yorumlayicinin KENDISINI kullaniyoruz:
#     <bu python> -m flask db init
# Boylece sanal ortam garanti.
FLASK_KOMUT = [sys.executable, '-m', 'flask']


def calistir(komut, aciklama):
    print(f"   → {aciklama}")
    s = subprocess.run(komut, env=ORTAM, capture_output=True, text=True)
    if s.returncode != 0:
        print(f"     ✗ HATA:\n{(s.stderr or s.stdout)[:600]}")
        return False
    for satir in (s.stdout or '').strip().split('\n')[:4]:
        if satir.strip():
            print(f"     {satir.strip()[:100]}")
    return True


print("─" * 74)
print(" UYGULANIYOR")
print("─" * 74)

if not MIG.exists():
    if not calistir(FLASK_KOMUT + ['db', 'init'], 'migrations/ oluşturuluyor'):
        print("\n ✗ Kurulum başarısız — hiçbir şey damgalanmadı.")
        sys.exit(1)

# Mevcut şemayı baseline olarak damgala.
# Önce boş bir "başlangıç" revizyonu üret (autogenerate DEĞİL — mevcut
# tablolari yeniden yaratmasin diye), sonra head'e damgala.
if not calistir(FLASK_KOMUT + ['db', 'revision', '-m', 'baseline: mevcut sema'],
                'başlangıç revizyonu (boş) üretiliyor'):
    sys.exit(1)

if not calistir(FLASK_KOMUT + ['db', 'stamp', 'head'],
                'mevcut şema BAŞLANGIÇ olarak damgalanıyor'):
    sys.exit(1)

print()
print("═" * 74)
print(" ✓ KURULDU")
print("═" * 74)
print()
print(" ÖNEMLİ — İLK REVİZYON BOŞ:")
print("   migrations/versions/ altındaki ilk dosya BİLEREK boştur.")
print("   Mevcut 28 tablo zaten var; onları yeniden yaratmaya")
print("   çalışmamalı. Alembic artık 'buradan sonrasını' yönetiyor.")
print()
print(" BUNDAN SONRA ŞEMA DEĞİŞİKLİĞİ:")
print("   1) models.py'yi düzenleyin")
print("   2) venv/bin/flask db migrate -m 'ne yaptigini yaz'")
print("   3) ⚠ migrations/versions/ altındaki YENİ dosyayı OKUYUN")
print("      Autogenerate bazen yanlış tahmin eder — özellikle")
print("      sütun ADI değişikliğini 'sil + ekle' sanar ve VERİ KAYBEDER.")
print("   4) venv/bin/flask db upgrade")
print("   5) venv/bin/python sema_denetim.py       ← doğrulama")
print("   6) venv/bin/python degismezlik_denetim.py ← hesap doğruluğu")
print()
print(" GERİ ALMA:")
print("   venv/bin/flask db downgrade")
print()
print(" sema_denetim.py KALDIRILMADI — rolü değişti:")
print("   Alembic UYGULAR, sema_denetim DOĞRULAR. İkisi birbirini denetler.")
print("═" * 74)

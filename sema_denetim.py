#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — Veritabanı Şema Denetimi ve Onarımı
#
#  SORUN:
#    models.py'ye sonradan sütun eklendiğinde, db.create_all() MEVCUT
#    tablolara sütun EKLEMEZ (yalnızca hiç olmayan tabloyu yaratır).
#    Bu yüzden model ile PostgreSQL şeması zamanla birbirinden ayrılır ve
#    "column ... does not exist" hataları çıkar.
#
#  NE YAPAR:
#    • Tüm modelleri gerçek veritabanı şemasıyla karşılaştırır
#    • Eksik TABLO ve eksik SÜTUNLARI listeler
#    • --uygula verilirse eksikleri ekler
#
#  GÜVENLİK:
#    • Sadece EKLER. Hiçbir sütunu/tabloyu silmez, tip değiştirmez.
#    • Yeni sütunlar NULL kabul eder eklenir; modelde varsayılan varsa
#      mevcut satırlara geri doldurulur, modelde nullable=False ise
#      doldurma sonrası NOT NULL yapılır.
#    • Önce --uygula OLMADAN çalıştırıp planı görün.
#
#  KULLANIM (proje dizininde — models.py'nin yanında):
#
#    Linux / Pardus (venv ile):
#      venv/bin/python sema_denetim.py            # sadece rapor
#      venv/bin/python sema_denetim.py --uygula   # düzelt
#
#    Windows (venv olmadan):
#      python sema_denetim.py
#      python sema_denetim.py --uygula
#
#    .env yoksa bağlantıyı elle verin:
#      python sema_denetim.py --url="postgresql://kullanici:sifre@localhost:5432/vt"
# ══════════════════════════════════════════════════════════════════════
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects import postgresql

load_dotenv()

# Bağlantı adresi: --url=... > DATABASE_URL ortam değişkeni > .env
VT_URL = None
for arg in sys.argv[1:]:
    if arg.startswith('--url='):
        VT_URL = arg.split('=', 1)[1].strip().strip('"').strip("'")
VT_URL = VT_URL or os.environ.get('DATABASE_URL')

if not VT_URL:
    print("HATA: Veritabanı adresi bulunamadı.")
    print()
    print("Şu üç yoldan biriyle verin:")
    print("  1) Proje dizininde .env dosyası:  DATABASE_URL=postgresql://...")
    print("  2) Komut satırından:")
    print('     python sema_denetim.py --url="postgresql://kullanici:sifre@localhost:5432/veritabani"')
    print("  3) Ortam değişkeni:")
    print("     Windows :  set DATABASE_URL=postgresql://...")
    print("     Linux   :  export DATABASE_URL=postgresql://...")
    sys.exit(1)

UYGULA = '--uygula' in sys.argv

import models  # noqa: E402  (load_dotenv sonrası)

md = models.db.metadata
motor = create_engine(VT_URL)
denetci = inspect(motor)
lehce = postgresql.dialect()

mevcut_tablolar = set(denetci.get_table_names())

eksik_tablolar = []
eksik_sutunlar = []   # (tablo_adi, Column nesnesi)

for tablo in md.sorted_tables:
    if tablo.name not in mevcut_tablolar:
        eksik_tablolar.append(tablo)
        continue
    gercek = {s['name'] for s in denetci.get_columns(tablo.name)}
    for sutun in tablo.columns:
        if sutun.name not in gercek:
            eksik_sutunlar.append((tablo.name, sutun))

print("═" * 62)
print(" MILESTONE ERP — ŞEMA DENETİMİ")
print("═" * 62)
print(f" Model sayısı      : {len(md.sorted_tables)} tablo")
print(f" Veritabanında     : {len(mevcut_tablolar)} tablo")
print(f" Eksik tablo       : {len(eksik_tablolar)}")
print(f" Eksik sütun       : {len(eksik_sutunlar)}")
print()

if eksik_tablolar:
    print("── EKSİK TABLOLAR ──")
    for t in eksik_tablolar:
        print(f"   • {t.name}  ({len(t.columns)} sütun)")
    print()

if eksik_sutunlar:
    print("── EKSİK SÜTUNLAR ──")
    for tablo_adi, s in eksik_sutunlar:
        tip = s.type.compile(dialect=lehce)
        vars_ = getattr(s.default, 'arg', None) if s.default is not None else None
        ek = ''
        if vars_ is not None and not callable(vars_):
            ek = f"  [varsayılan: {vars_!r}]"
        elif callable(vars_):
            ek = "  [varsayılan: fonksiyon]"
        print(f"   • {tablo_adi}.{s.name}  →  {tip}{ek}")
    print()

if not eksik_tablolar and not eksik_sutunlar:
    print("✓ Şema modellerle uyumlu. Yapılacak bir şey yok.")
    sys.exit(0)

if not UYGULA:
    print("─" * 62)
    print(" Bu yalnızca RAPOR. Düzeltmek için:")
    print("   venv/bin/python sema_denetim.py --uygula")
    print()
    print(" ÖNCE YEDEK ALIN:")
    print("   sudo /usr/local/bin/milestone-yedek.sh")
    print("─" * 62)
    sys.exit(0)

# ─────────────────── UYGULAMA ───────────────────
print("─" * 62)
print(" DEĞİŞİKLİKLER UYGULANIYOR…")
print("─" * 62)

with motor.begin() as baglanti:
    # 1) Eksik tablolar
    for t in eksik_tablolar:
        t.create(bind=baglanti)
        print(f" ✓ tablo oluşturuldu: {t.name}")

    # 2) Eksik sütunlar
    for tablo_adi, s in eksik_sutunlar:
        tip = s.type.compile(dialect=lehce)
        # Her zaman NULL kabul eden olarak ekle — mevcut satırlar patlamasın
        baglanti.execute(text(
            f'ALTER TABLE "{tablo_adi}" ADD COLUMN "{s.name}" {tip}'))
        print(f" ✓ sütun eklendi: {tablo_adi}.{s.name} ({tip})")

        # Modelde sabit bir varsayılan varsa mevcut satırlara geri doldur
        vars_ = getattr(s.default, 'arg', None) if s.default is not None else None
        dolduruldu = False
        if vars_ is not None and not callable(vars_):
            baglanti.execute(
                text(f'UPDATE "{tablo_adi}" SET "{s.name}" = :d '
                     f'WHERE "{s.name}" IS NULL'), {'d': vars_})
            print(f"     ↳ mevcut satırlara {vars_!r} yazıldı")
            dolduruldu = True
        elif callable(vars_):
            # datetime.now gibi fonksiyon varsayılanı — şimdiki zamanı yaz
            try:
                deger = vars_() if vars_.__code__.co_argcount == 0 else None
            except Exception:
                deger = None
            if deger is not None:
                baglanti.execute(
                    text(f'UPDATE "{tablo_adi}" SET "{s.name}" = :d '
                         f'WHERE "{s.name}" IS NULL'), {'d': deger})
                print(f"     ↳ mevcut satırlara {deger!r} yazıldı")
                dolduruldu = True

        # Model NOT NULL diyorsa ve doldurma yapıldıysa kısıtı uygula
        if not s.nullable and dolduruldu:
            try:
                baglanti.execute(text(
                    f'ALTER TABLE "{tablo_adi}" '
                    f'ALTER COLUMN "{s.name}" SET NOT NULL'))
                print("     ↳ NOT NULL kısıtı uygulandı")
            except Exception as e:
                print(f"     ! NOT NULL uygulanamadı ({e.__class__.__name__}) — "
                      f"sütun NULL kabul eder kaldı, sorun değil")

print()
print("═" * 62)
print(" ✓ TAMAMLANDI")
print()
print(" Doğrulamak için betiği tekrar çalıştırın (--uygula olmadan):")
print("   venv/bin/python sema_denetim.py")
print("═" * 62)

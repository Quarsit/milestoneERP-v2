#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — CARİ ÜNVAN ALANLARI 200'E  ·  UZ1
#
#  ── ÖLÇÜLEN HATA (üretimde görüldü) ──
#    Toplu stok ice aktarma "0 kayit aktarildi" verdi:
#
#      StringDataRightTruncation: varying(100) veri tipi icin cok uzun
#      'AKSEL MERMER MADENCİLİK VE İNŞAAT NAKLİYAT PAZARLAMA
#       İTHALAT İHRACAT SANAYİ VE TİCARET LİMİTED ŞİRKETİ'  (102 karakter)
#
#    `Cari.unvan` 200 karakter — yani sisteme KAYDEDILEBILEN bir
#    unvan, stok tablosuna SIGMIYOR. Cari ice aktarmayla gelen
#    gercek unvanlar bu sinirin uzerinde.
#
#  ── TUTARSIZLIK ──
#    Ayni bilgiyi tasiyan alanlarin bir kismi 200, bir kismi 100:
#      200 → CariHareket.cari_unvan, Fatura.musteri, Proforma.musteri,
#            SatisKaydi.musteri, Cek.cari_unvan, Cek.hesap_sahibi
#      100 → BlokStok/PlakaStok/EbatliStok.uretici, StokCikis.uretici,
#            StokCikis.musteri, Siparis.musteri, Rezervasyon.musteri,
#            Sevkiyat.musteri
#
#    Hepsi `Cari.unvan`dan besleniyor; 100 olanlar 200'e cikariliyor.
#
#  ── NEDEN KISALTMIYORUZ ──
#    Unvani kesmek belgede yanlis firma adi yazdirirdi — fatura,
#    proforma ve ekstre resmi evrak. Alani genisletmek dogru cozum.
#
#  KULLANIM (proje klasöründe):
#      python yama_uz1_unvan_uzunluk.py            # rapor
#      python yama_uz1_unvan_uzunluk.py --uygula
#      venv/bin/python goc.py uygula               # ŞART
# ══════════════════════════════════════════════════════════════════════
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
MOD = Path('models.py')
GOC = Path('migrations/versions')

if not MOD.exists():
    print("HATA: models.py bu klasörde yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

# (sinif, alan, tablo)
HEDEFLER = [
    ('BlokStok', 'uretici', 'blok_stok'),
    ('PlakaStok', 'uretici', 'plaka_stok'),
    ('EbatliStok', 'uretici', 'ebatli_stok'),
    ('StokCikis', 'uretici', 'stok_cikis'),
    ('StokCikis', 'musteri', 'stok_cikis'),
    ('Siparis', 'musteri', 'siparis_kayit'),
    ('Rezervasyon', 'musteri', 'rezervasyon'),
    ('Sevkiyat', 'musteri', 'sevkiyat_kayit'),
]

print("═" * 70)
print(" UZ1 · CARİ ÜNVAN ALANLARI 200 KARAKTERE")
print("═" * 70)
print()

ham = MOD.read_bytes().decode('utf-8')
crlf = '\r\n' in ham
if 'UZ1' in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

icerik = ham
degisen = []
for sinif, alan, tablo in HEDEFLER:
    m = re.search(rf"^class {sinif}\(db\.Model\):", icerik, re.M)
    if not m:
        print(f" ✗ {sinif} bulunamadı. DOSYAYA DOKUNULMADI.")
        sys.exit(1)
    son = icerik.find('\nclass ', m.end())
    son = son if son > 0 else len(icerik)
    govde = icerik[m.start():son]
    kalip = re.search(rf"^(    {alan}\s*= db\.Column\(db\.String\()(\d+)(\).*)$",
                      govde, re.M)
    if not kalip:
        print(f" ✗ {sinif}.{alan} bulunamadı. DOSYAYA DOKUNULMADI.")
        sys.exit(1)
    if int(kalip.group(2)) >= 200:
        continue
    yeni_satir = f"{kalip.group(1)}200{kalip.group(3)}"
    icerik = (icerik[:m.start()]
              + govde.replace(kalip.group(0), yeni_satir, 1)
              + icerik[son:])
    degisen.append((sinif, alan, tablo, kalip.group(2)))

if not degisen:
    print(" ✓ Tüm alanlar zaten 200 veya üzeri.")
    sys.exit(0)

# UZ1 izi — idempotens için
icerik = icerik.replace(
    "class BlokStok(db.Model):",
    "# UZ1: cari ünvanı taşıyan alanlar Cari.unvan (200) ile hizalandı.\n"
    "# Üretimde 102 karakterlik bir ünvan varchar(100)'e sığmayıp toplu\n"
    "# içe aktarmayı tümüyle engellemişti. Ünvanı kesmek belgede yanlış\n"
    "# firma adı yazdırırdı — alan genişletildi.\n"
    "class BlokStok(db.Model):", 1)

try:
    compile(icerik.replace('\r\n', '\n'), 'models.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    sys.exit(1)

for s, a, t, eski in degisen:
    print(f"  ✓ {s:<14} {a:<10} {eski} → 200")
print("  ✓ sözdizimi doğrulandı (compile)")

# ── Göç zinciri ──
zincir = {}
for f in sorted(GOC.glob('*.py')):
    t = f.read_text(encoding='utf-8', errors='replace')
    r = re.search(r"^revision = '([^']+)'", t, re.M)
    d = re.search(r"^down_revision = '([^']+)'", t, re.M)
    if r:
        zincir[r.group(1)] = d.group(1) if d else None
uclar = [r for r in zincir if r not in set(v for v in zincir.values() if v)]
if len(uclar) != 1:
    print(f" ✗ Göç zincirinde {len(uclar)} uç: {uclar}. DOSYAYA DOKUNULMADI.")
    sys.exit(1)
bas = uclar[0]
REV = 'uz1unvan200'

_alter = "\n".join(
    f"""    with op.batch_alter_table('{t}', schema=None) as batch_op:
        batch_op.alter_column('{a}', existing_type=sa.String(length={e}),
                              type_=sa.String(length=200),
                              existing_nullable=True)"""
    for _s, a, t, e in degisen)
_geri = "\n".join(
    f"""    with op.batch_alter_table('{t}', schema=None) as batch_op:
        batch_op.alter_column('{a}', existing_type=sa.String(length=200),
                              type_=sa.String(length={e}),
                              existing_nullable=True)"""
    for _s, a, t, e in degisen)

GOC_ICERIK = f'''"""cari unvani tasiyan alanlar 200 karaktere (UZ1)

Revision ID: {REV}
Revises: {bas}
Create Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}

Uretimde olculdu: 102 karakterlik tedarikci unvani varchar(100)'e
sigmayip toplu stok ice aktarmayi tumuyle engelledi. Cari.unvan
zaten 200; bu alanlar onunla hizalandi.
"""
from alembic import op
import sqlalchemy as sa

revision = '{REV}'
down_revision = '{bas}'
branch_labels = None
depends_on = None


def upgrade():
{_alter}


def downgrade():
    # DIKKAT: 200 karakterlik kayitlar varsa geri alma VERI KESER.
{_geri}
'''

print(f"  ✓ göç zinciri tek uçlu ({bas})")
print(f"  ✓ yeni revizyon: {REV}")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_uz1_unvan_uzunluk.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = MOD.with_name(f'models.py.yedek-{damga}')
shutil.copy2(MOD, yedek)
MOD.write_bytes(icerik.encode('utf-8'))
(GOC / f'{REV}_unvan_200.py').write_text(GOC_ICERIK, encoding='utf-8')
print()
print(f" ✓ models.py  (yedek: {yedek.name})")
print(f" ✓ {GOC / (REV + '_unvan_200.py')}")
print()
print("═" * 70)
print(" ⚠ ŞEMA DEĞİŞTİ:  venv/bin/python goc.py uygula")
print("═" * 70)

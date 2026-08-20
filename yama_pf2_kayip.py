#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — KAYIP KAYDI VE SATIŞ TEMSİLCİSİ  ·  PF2 (model)
#
#  ── NEDEN ──
#    PF1 ile 'Siparise Donustu' durumu geldi ve KAZANILAN teklif
#    artik gorunuyor. Ama KAYBEDILEN gorunmuyor:
#
#      · 'Kaybedildi' durumu yok — kaybedilen teklif ya 'Iptal'
#        yaziliyor ya da 'Onaylandi' olarak asili kaliyor. Ikisi de
#        yanlis: iptal, TEKLIFI GERI CEKMEK demek; kaybetmek ise
#        MUSTERININ BASKASINI SECMESI. Ayni kutuya koymak, kazanma
#        oranini olculemez yapar.
#
#      · Kayip SEBEBI hic tutulmuyor. "Kac teklif kaybettik" bilgisi
#        tek basina bir sey ogretmez; "neden kaybettik" ogretir —
#        fiyat mi, termin mi, rakip mi.
#
#      · Teklifi KIMIN hazirladigi yok. Ekip buyudugunde kimin
#        teklifi kimin musterisi belli olmaz; performans da yetki de
#        tanimlanamaz. `onaya_gonderen` var ama o ONAY akisinin
#        parcasi, sahiplik degil.
#
#  ── EKLENENLER ──
#    temsilci      Teklifi hazirlayan satisci (Kullanici.ad).
#                  Olusturulurken oturumdan otomatik yazilir.
#    kayip_sebep   'fiyat' | 'termin' | 'rakip' | 'musteri_vazgecti'
#                  | 'stok_yok' | 'diger'
#    kayip_not     Serbest aciklama (rakip adi, verilen fiyat...)
#    kayip_tarihi
#
#  ── 'Kaybedildi' DURUMU PF3'TE ──
#    Bu yama YALNIZCA modeli hazirlar. Durum gecisleri ve uc nokta
#    bir sonraki adimda; boylece goc ile kod degisikligi ayri
#    dogrulanabilir.
#
#  KULLANIM (proje klasöründe):
#      python yama_pf2_kayip.py            # rapor
#      python yama_pf2_kayip.py --uygula
#      venv/bin/python goc.py uygula       # ŞART
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

ham = MOD.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


print("═" * 70)
print(" PF2 · KAYIP KAYDI VE SATIŞ TEMSİLCİSİ (model)")
print("═" * 70)
print()

if 'kayip_sebep' in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

m = re.search(r"^class Proforma\(db\.Model\):", ham, re.M)
if not m:
    print(" ✗ Proforma sınıfı bulunamadı. DOSYAYA DOKUNULMADI.")
    sys.exit(1)
son = ham.find('\nclass ', m.start() + 10)
son = son if son > 0 else len(ham)
govde = ham[m.start():son]

mm = re.search(r"^(    avans_tip .*)$", govde, re.M)
if not mm:
    mm = re.search(r"^(    notlar .*)$", govde, re.M)
if not mm:
    print(" ✗ Proforma içinde çapa alan bulunamadı. DOSYAYA DOKUNULMADI.")
    sys.exit(1)

YENI_ALANLAR = mm.group(1) + uyarla('''

    # ── SATIŞ TAKİBİ (PF2) ──
    # temsilci: teklifi HAZIRLAYAN satisci (Kullanici.ad). Var olan
    # `onaya_gonderen` ONAY akisinin parcasi, sahiplik degil.
    temsilci        = db.Column(db.String(50), index=True)

    # KAYIP KAYDI.
    # 'Iptal' ile 'Kaybedildi' AYRI seylerdir: iptal TEKLIFI GERI
    # CEKMEK, kayip MUSTERININ BASKASINI SECMESI. Ayni kutuya
    # koymak kazanma oranini olculemez yapar.
    #
    # Sebep alani asil degerli olan: "kac teklif kaybettik" tek
    # basina bir sey ogretmez, "neden kaybettik" ogretir.
    # fiyat | termin | rakip | musteri_vazgecti | stok_yok | diger
    kayip_sebep     = db.Column(db.String(30), index=True)
    kayip_not       = db.Column(db.Text)
    kayip_tarihi    = db.Column(db.Date)''')

icerik = ham[:m.start()] + govde.replace(mm.group(1), YENI_ALANLAR, 1) + ham[son:]

try:
    compile(icerik.replace('\r\n', '\n'), 'models.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print("  ✓ temsilci        teklifi hazırlayan satışçı")
print("  ✓ kayip_sebep     fiyat / termin / rakip / …")
print("  ✓ kayip_not       serbest açıklama")
print("  ✓ kayip_tarihi")
print("  ✓ sözdizimi doğrulandı (compile)")

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
bas_rev = uclar[0]
YENI_REV = 'pf2kayip001'
GOC_DOSYA = GOC / f'{YENI_REV}_proforma_kayip_temsilci.py'
GOC_ICERIK = f'''"""proforma kayip kaydi ve satis temsilcisi

Revision ID: {YENI_REV}
Revises: {bas_rev}
Create Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}

"""
from alembic import op
import sqlalchemy as sa

revision = '{YENI_REV}'
down_revision = '{bas_rev}'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('proforma', schema=None) as batch_op:
        batch_op.add_column(sa.Column('temsilci', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('kayip_sebep', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('kayip_not', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('kayip_tarihi', sa.Date(), nullable=True))
        batch_op.create_index(batch_op.f('ix_proforma_temsilci'), ['temsilci'], unique=False)
        batch_op.create_index(batch_op.f('ix_proforma_kayip_sebep'), ['kayip_sebep'], unique=False)

    # Mevcut proformalarda temsilci BOS kalir. `onaya_gonderen`den
    # kopyalamak CAZIP ama YANLIS olurdu: o alan onaya GONDEREN
    # kisiyi tutar, teklifi HAZIRLAYANI degil. Cogu durumda ayni
    # kisidir ama "cogu durumda" ile veri doldurulmaz — yanlis
    # atfedilmis bir teklif, bos birakilmisdan kotudur.


def downgrade():
    with op.batch_alter_table('proforma', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_proforma_kayip_sebep'))
        batch_op.drop_index(batch_op.f('ix_proforma_temsilci'))
        batch_op.drop_column('kayip_tarihi')
        batch_op.drop_column('kayip_not')
        batch_op.drop_column('kayip_sebep')
        batch_op.drop_column('temsilci')
'''

print(f"  ✓ göç zinciri tek uçlu ({bas_rev})")
print(f"  ✓ yeni revizyon: {YENI_REV}")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_pf2_kayip.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = MOD.with_name(f'models.py.yedek-{damga}')
shutil.copy2(MOD, yedek)
MOD.write_bytes(icerik.encode('utf-8'))
GOC_DOSYA.write_text(GOC_ICERIK, encoding='utf-8')
print()
print(f" ✓ models.py  (yedek: {yedek.name})")
print(f" ✓ {GOC_DOSYA}")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print(" ⚠ ŞEMA DEĞİŞTİ:  venv/bin/python goc.py uygula")
print(" SIRADAKİ: yama_pf3_kayip_akis.py (durum + uç nokta)")
print("═" * 70)

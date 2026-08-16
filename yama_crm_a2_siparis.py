#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — SİPARİŞ KİMLİK BAĞI  ·  CRM-A2
#
#  ── NEDEN AYRI YAMA ──
#    CRM-A bes tabloya `cari_id` ekledi ama SIPARIS'i atladi.
#    Sebebi benim tarama hatam: `Siparis` icinde `acente_cari_id`
#    alanini gorup "cari_id var" diye isaretledim. Gercekte siparis
#    musteriye yalnizca `musteri` METNIYLE bagliydi.
#
#    Kuresel erisim suzgeci (CRM-C2) Siparis'i listeye alinca
#    AttributeError ile cokerek bunu ortaya cikardi.
#
#  ── NEDEN ÖNEMLİ ──
#    Siparis cekirdek satis belgesi. Suzgec disinda birakilsaydi
#    kapali bir musterinin siparisleri tum satis ekibine gorunur,
#    ama siz kapali sandiginiz icin fark etmezdiniz.
#
#  ── acente_cari_id KARISTIRILMASIN ──
#    O alan siparisin ACENTESINI (komisyoncu) gosterir, musteriyi
#    degil. Erisim kurali musteriye gore isler; acente ayri bir
#    kavram ve suzgece girmez.
#
#  KULLANIM (proje klasöründe):
#      python yama_crm_a2_siparis.py            # rapor
#      python yama_crm_a2_siparis.py --uygula
#      venv/bin/python goc.py uygula            # ŞART
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


if 'cari_id_otomatik_doldur' not in ham:
    print("✗ ÖN KOŞUL: önce yama_crm_a_cari_id.py uygulanmalı.")
    sys.exit(1)

print("═" * 70)
print(" CRM-A2 · SİPARİŞ KİMLİK BAĞI")
print("═" * 70)
print()

m = re.search(r"^class Siparis\(db\.Model\):", ham, re.M)
if not m:
    print(" ✗ Siparis sınıfı bulunamadı. DOSYAYA DOKUNULMADI.")
    sys.exit(1)
son = ham.find('\nclass ', m.start() + 10)
son = son if son > 0 else len(ham)
govde = ham[m.start():son]

if re.search(r"^    cari_id ", govde, re.M):
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

mm = re.search(r"^(    musteri +=.*)$", govde, re.M)
if not mm:
    print(" ✗ Siparis içinde 'musteri' alanı bulunamadı. DOSYAYA DOKUNULMADI.")
    sys.exit(1)

YENI_SATIR = mm.group(1) + uyarla(
    "\n    # Musteri KIMLIGI (CRM-A2). CRM-A'da atlanmisti: taramada"
    "\n    # `acente_cari_id` gorulup 'cari_id var' sanilmisti. O alan"
    "\n    # siparisin ACENTESINI gosterir, musteriyi degil."
    "\n    cari_id         = db.Column(db.String(20), index=True)")

icerik = ham[:m.start()] + govde.replace(mm.group(1), YENI_SATIR, 1) + ham[son:]

# Dinleyiciye Siparis'i ekle
D_ESKI = "for _model in (Proforma, Fatura, SatisKaydi, Sevkiyat, Rezervasyon):"
D_YENI = "for _model in (Proforma, Fatura, SatisKaydi, Sevkiyat, Rezervasyon, Siparis):"
if uyarla(D_ESKI) not in icerik:
    print(" ✗ Otomatik doldurma döngüsü bulunamadı. DOSYAYA DOKUNULMADI.")
    sys.exit(1)
icerik = icerik.replace(uyarla(D_ESKI), uyarla(D_YENI), 1)

try:
    compile(icerik.replace('\r\n', '\n'), 'models.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print("  ✓ Siparis.cari_id eklenecek")
print("  ✓ otomatik doldurma dinleyicisine eklenecek")
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
YENI_REV = 'crma2siparis'
GOC_DOSYA = GOC / f'{YENI_REV}_siparis_cari_id.py'
GOC_ICERIK = f'''"""siparis musteri kimlik bagi

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
    with op.batch_alter_table('siparis_kayit', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cari_id', sa.String(length=20), nullable=True))
        batch_op.create_index(batch_op.f('ix_siparis_kayit_cari_id'),
                              ['cari_id'], unique=False)

    op.execute("UPDATE siparis_kayit SET cari_id = c.id FROM cariler c "
               "WHERE siparis_kayit.cari_id IS NULL AND siparis_kayit.musteri = c.unvan")


def downgrade():
    with op.batch_alter_table('siparis_kayit', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_siparis_kayit_cari_id'))
        batch_op.drop_column('cari_id')
'''

print(f"  ✓ göç zinciri tek uçlu ({bas_rev})")
print(f"  ✓ yeni revizyon: {YENI_REV}")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_crm_a2_siparis.py --uygula")
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
print("═" * 70)

#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — AKTİVİTE KAYDI  ·  CRM-E (model)
#
#  ── ÖN KOŞUL ──
#      yama_crm_b_sahiplik.py + goc.py uygula
#
#  ── NE İÇİN ──
#    Sistemde musteriyle NE KONUSULDUGUNU tutan hicbir yer yok.
#    Gorusme, e-posta, fuar temasi, numune gonderimi — hepsi
#    satiscinin kafasinda ya da kendi not defterinde.
#
#    Satis ekibi buyudugunde bu bilgi paylasilamaz hale gelir:
#    bir musteriyle en son ne konusuldugu, kimin ne soz verdigi,
#    hangi teklifin cevabinin beklendigi kaybolur.
#
#  ── EN ÖNEMLİ ALAN: SONRAKİ ADIM ──
#    `sonraki_adim` + `sonraki_tarih`. Bir CRM'i not defterinden
#    ayiran sey gecmisi kaydetmesi degil, GELECEGI hatirlatmasidir.
#    Vadesi gecmis takipler listelenebilsin diye ikisi de indeksli.
#
#  ── GÖRÜNÜRLÜK ──
#    Aktivite musteriye bagli; `cari_id` uzerinden CRM-C2'nin
#    kuresel suzgecine dahil edilecek (CRM-E2). Kapali bir
#    musterinin gorusme notlari da kapali olmali.
#
#  ── NEDEN AYRI TABLO ──
#    Bu veri sistemde HIC YOK; kopyalama riski tasimiyor. Oysa
#    musteri gecmisi (siparis, fatura, sevkiyat) zaten var ve
#    aktivite tablosuna KOPYALANMAYACAK — 360 ekrani ikisini
#    birlestirerek gosterecek, saklamayacak.
#
#  KULLANIM (proje klasöründe):
#      python yama_crm_e_aktivite.py            # rapor
#      python yama_crm_e_aktivite.py --uygula
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


if 'class CariKisi' not in ham:
    print("✗ ÖN KOŞUL: önce yama_crm_b_sahiplik.py uygulanmalı.")
    sys.exit(1)

print("═" * 70)
print(" CRM-E · AKTİVİTE KAYDI (model)")
print("═" * 70)
print()

if 'class CariAktivite' in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

CAPA = "class CariKisi(db.Model):"
if CAPA not in ham:
    print(" ✗ CariKisi sınıfı bulunamadı. DOSYAYA DOKUNULMADI.")
    sys.exit(1)

YENI = '''class CariAktivite(db.Model):
    """Musteriyle yapilan temaslar ve SONRAKI ADIM.

    Sistemde musteriyle ne konusuldugunu tutan hicbir yer yoktu;
    bilgi satiscinin kafasinda kaliyordu. Ekip buyudugunde bu
    paylasilamaz hale gelir.

    `sonraki_adim` + `sonraki_tarih` en onemli alanlar: bir CRM'i
    not defterinden ayiran sey gecmisi kaydetmesi degil, GELECEGI
    hatirlatmasidir.
    """
    __tablename__ = 'cari_aktivite'
    id            = db.Column(db.Integer, primary_key=True)
    cari_id       = db.Column(db.String(20), index=True, nullable=False)
    # Kiminle konusuldugu — CariKisi.id. Zorunlu degil: fuarda
    # tanismadigi biriyle de konusulabilir.
    kisi_id       = db.Column(db.Integer, index=True)
    tarih         = db.Column(db.Date, index=True, default=date.today)
    # telefon | eposta | ziyaret | fuar | numune | teklif | diger
    tip           = db.Column(db.String(20), index=True)
    ozet          = db.Column(db.String(200), nullable=False)
    detay         = db.Column(db.Text)

    # ── TAKIP ──
    sonraki_adim  = db.Column(db.String(200))
    sonraki_tarih = db.Column(db.Date, index=True)
    # Takip yapildi mi. Vadesi gecmis takipleri listelemek icin
    # sonraki_tarih ile birlikte kullanilir.
    tamamlandi    = db.Column(db.Boolean, default=False, index=True)
    tamamlanma    = db.Column(db.Date)

    kullanici     = db.Column(db.String(50), index=True)
    olusturma     = db.Column(db.DateTime, default=datetime.now)


class CariKisi(db.Model):'''

icerik = ham.replace(uyarla(CAPA), uyarla(YENI), 1)

try:
    compile(icerik.replace('\r\n', '\n'), 'models.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print("  ✓ CariAktivite       temas kaydı + sonraki adım")
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
YENI_REV = 'crmeaktivite'
GOC_DOSYA = GOC / f'{YENI_REV}_cari_aktivite.py'
GOC_ICERIK = f'''"""cari aktivite kaydi

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
    op.create_table(
        'cari_aktivite',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cari_id', sa.String(length=20), nullable=False),
        sa.Column('kisi_id', sa.Integer(), nullable=True),
        sa.Column('tarih', sa.Date(), nullable=True),
        sa.Column('tip', sa.String(length=20), nullable=True),
        sa.Column('ozet', sa.String(length=200), nullable=False),
        sa.Column('detay', sa.Text(), nullable=True),
        sa.Column('sonraki_adim', sa.String(length=200), nullable=True),
        sa.Column('sonraki_tarih', sa.Date(), nullable=True),
        sa.Column('tamamlandi', sa.Boolean(), nullable=True),
        sa.Column('tamamlanma', sa.Date(), nullable=True),
        sa.Column('kullanici', sa.String(length=50), nullable=True),
        sa.Column('olusturma', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_cari_aktivite_cari_id'), 'cari_aktivite', ['cari_id'])
    op.create_index(op.f('ix_cari_aktivite_kisi_id'), 'cari_aktivite', ['kisi_id'])
    op.create_index(op.f('ix_cari_aktivite_tarih'), 'cari_aktivite', ['tarih'])
    op.create_index(op.f('ix_cari_aktivite_tip'), 'cari_aktivite', ['tip'])
    op.create_index(op.f('ix_cari_aktivite_kullanici'), 'cari_aktivite', ['kullanici'])
    # Vadesi gecmis takipleri hizli bulmak icin: sonraki_tarih +
    # tamamlandi birlikte sorgulanacak.
    op.create_index(op.f('ix_cari_aktivite_sonraki_tarih'),
                    'cari_aktivite', ['sonraki_tarih'])
    op.create_index(op.f('ix_cari_aktivite_tamamlandi'),
                    'cari_aktivite', ['tamamlandi'])


def downgrade():
    op.drop_index(op.f('ix_cari_aktivite_tamamlandi'), table_name='cari_aktivite')
    op.drop_index(op.f('ix_cari_aktivite_sonraki_tarih'), table_name='cari_aktivite')
    op.drop_index(op.f('ix_cari_aktivite_kullanici'), table_name='cari_aktivite')
    op.drop_index(op.f('ix_cari_aktivite_tip'), table_name='cari_aktivite')
    op.drop_index(op.f('ix_cari_aktivite_tarih'), table_name='cari_aktivite')
    op.drop_index(op.f('ix_cari_aktivite_kisi_id'), table_name='cari_aktivite')
    op.drop_index(op.f('ix_cari_aktivite_cari_id'), table_name='cari_aktivite')
    op.drop_table('cari_aktivite')
'''

print(f"  ✓ göç zinciri tek uçlu ({bas_rev})")
print(f"  ✓ yeni revizyon: {YENI_REV}")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_crm_e_aktivite.py --uygula")
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
print(" SIRADAKİ: yama_crm_e2_api.py (uç noktalar)")
print("═" * 70)

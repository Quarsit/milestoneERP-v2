#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — SAHİPLİK, GÖRÜNÜRLÜK VE KİŞİLER  ·  CRM-B
#
#  ── ÖN KOŞUL ──
#      yama_crm_a_cari_id.py --uygula  +  goc.py uygula
#
#  ── EKLENENLER ──
#
#    Cari.sorumlu       Musteriden sorumlu satisci (Kullanici.ad).
#                       `ad` alani BENZERSIZ ve DEGISTIRILEMIYOR
#                       (guncelleme ucu bu alani yazmiyor), bu yuzden
#                       anahtar olarak guvenli — Cari.unvan'da
#                       yasadigimiz kopma riski burada yok.
#
#    Cari.gorunurluk    'kapali' (varsayilan) | 'ortak'
#                       kapali → yalnizca sorumlusu + admin + acikca
#                                yetkilendirilenler
#                       ortak  → tum satis ekibi
#
#    CariErisim         Istisnalar: "bu musteriyi Ali ve Ayse gorsun,
#                       baskasi gormesin". cari_id + kullanici.
#
#    CariKisi           Bir musteride BIRDEN FAZLA kisi. Ihracatta
#                       satin almaci, lojistik sorumlusu ve muhasebe
#                       ayri kisilerdir; Cari'deki tek `yetkili`
#                       alani yetmiyordu.
#
#  ── VARSAYILAN NEDEN 'kapali' ──
#    Guvenli taraf. Yeni musteri acan kisi gorunurlugu isaretlemeyi
#    unutursa musteri gizli kalir; tersi olsaydi gizli kalmasi
#    gereken musteri sessizce herkese acilirdi.
#
#  ── MEVCUT KAYITLAR DA 'kapali' OLUYOR ──
#    Goc, mevcut cari kayitlarini da 'kapali' yapar ve sorumlulari
#    BOS kalir. Bu KASITLI:
#
#      · 'ortak' yapsaydik, kullanici politikanin gecmise de
#        uygulandigini varsayip sessiz bir sizinti yasardi.
#      · 'kapali' ise suzgec devreye girdiginde satis ekibi HICBIR
#        musteri goremez — gurultulu, hemen fark edilen bir durum.
#
#    Sessiz sizinti, gurultulu ariza'dan kotudur.
#
#  ── SÜZGEÇ BU ADIMDA DEVREDE DEGIL ──
#    Bu yama YALNIZCA veri modelini kurar. Erisim suzgeci CRM-C'de
#    gelecek. Arada sorumlulari atayin; boylece suzgec acildiginda
#    kimse disarida kalmaz.
#
#  KULLANIM (proje klasöründe):
#      python yama_crm_b_sahiplik.py            # rapor
#      python yama_crm_b_sahiplik.py --uygula
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
print(" CRM-B · SAHİPLİK, GÖRÜNÜRLÜK VE KİŞİLER")
print("═" * 70)
print()

if 'class CariKisi' in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

# ── Cari'ye iki alan ──
m = re.search(r"^class Cari\(db\.Model\):", ham, re.M)
if not m:
    print(" ✗ Cari sınıfı bulunamadı. DOSYAYA DOKUNULMADI.")
    sys.exit(1)
son = ham.find('\nclass ', m.start() + 10)
son = son if son > 0 else len(ham)
govde = ham[m.start():son]

mm = re.search(r"^(    odeme_vadesi_gun.*)$", govde, re.M)
if not mm:
    mm = re.search(r"^(    aciklama +=.*)$", govde, re.M)
if not mm:
    print(" ✗ Cari içinde çapa alan bulunamadı. DOSYAYA DOKUNULMADI.")
    sys.exit(1)

CARI_EK = mm.group(1) + uyarla('''
    # ── CRM: sahiplik ve gorunurluk ──
    # sorumlu: Kullanici.ad. O alan BENZERSIZ ve degistirilemiyor
    # (guncelleme ucu yazmiyor), bu yuzden anahtar olarak guvenli.
    sorumlu         = db.Column(db.String(50), index=True)
    # 'kapali' (varsayilan) | 'ortak'
    # Varsayilan KAPALI: isaretlemeyi unutan biri musteriyi gizli
    # birakir. Tersi olsaydi gizli kalmasi gereken musteri sessizce
    # herkese acilirdi — sessiz sizinti, gurultulu arizadan kotudur.
    gorunurluk      = db.Column(db.String(10), default='kapali', index=True)''')

icerik = ham[:m.start()] + govde.replace(mm.group(1), CARI_EK, 1) + ham[son:]

# ── İki yeni tablo — dinleyici bloğundan ÖNCE ──
CAPA = "\n\n# ══════════════════════════════════════════════════════════════════\n#  MUSTERI KIMLIGI OTOMATIK DOLDURMA  (CRM-A)"
YENI_TABLOLAR = '''

class CariErisim(db.Model):
    """Kapali bir musteriye ISTISNA erisim.

    "Bu musteriyi Ali ve Ayse gorsun, baskasi gormesin" durumu icin.
    Sorumlu ve admin zaten gorur; bu tablo onlarin disindakileri
    tek tek yetkilendirir.
    """
    __tablename__ = 'cari_erisim'
    id          = db.Column(db.Integer, primary_key=True)
    cari_id     = db.Column(db.String(20), index=True, nullable=False)
    kullanici   = db.Column(db.String(50), index=True, nullable=False)
    veren       = db.Column(db.String(50))
    olusturma   = db.Column(db.DateTime, default=datetime.now)

    __table_args__ = (
        db.UniqueConstraint('cari_id', 'kullanici', name='uq_cari_erisim'),
    )


class CariKisi(db.Model):
    """Musterideki kisiler.

    Cari'de tek bir `yetkili` alani vardi. Ihracatta bir musteride
    satin almaci, lojistik sorumlusu ve muhasebe AYRI kisilerdir;
    hangisine ne zaman yazilacagi satis ekibinin gunluk sorusudur.
    """
    __tablename__ = 'cari_kisi'
    id          = db.Column(db.Integer, primary_key=True)
    cari_id     = db.Column(db.String(20), index=True, nullable=False)
    ad          = db.Column(db.String(120), nullable=False)
    gorev       = db.Column(db.String(80))
    telefon     = db.Column(db.String(50))
    email       = db.Column(db.String(120))
    dil         = db.Column(db.String(30))
    birincil    = db.Column(db.Boolean, default=False)
    aktif       = db.Column(db.Boolean, default=True)
    aciklama    = db.Column(db.Text)
    olusturma   = db.Column(db.DateTime, default=datetime.now)
''' + CAPA[1:]

if CAPA not in icerik:
    print(" ✗ CRM-A dinleyici bloğu bulunamadı. DOSYAYA DOKUNULMADI.")
    sys.exit(1)
icerik = icerik.replace(CAPA, uyarla('\n' + YENI_TABLOLAR), 1)

try:
    compile(icerik.replace('\r\n', '\n'), 'models.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print("  ✓ Cari.sorumlu       satıştan sorumlu kullanıcı")
print("  ✓ Cari.gorunurluk    'kapali' (varsayılan) | 'ortak'")
print("  ✓ CariErisim         kapalı müşteriye istisna erişim")
print("  ✓ CariKisi           müşteride birden fazla kişi")
print("  ✓ sözdizimi doğrulandı (compile)")

# ── Göç ──
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
YENI_REV = 'crmbsahip01'
GOC_DOSYA = GOC / f'{YENI_REV}_sahiplik_gorunurluk.py'
GOC_ICERIK = f'''"""cari sahiplik, gorunurluk, erisim ve kisiler

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
    with op.batch_alter_table('cariler', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sorumlu', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('gorunurluk', sa.String(length=10), nullable=True))
        batch_op.create_index(batch_op.f('ix_cariler_sorumlu'), ['sorumlu'], unique=False)
        batch_op.create_index(batch_op.f('ix_cariler_gorunurluk'), ['gorunurluk'], unique=False)

    # MEVCUT kayitlar da 'kapali'. Kasitli: 'ortak' yapsaydik
    # politikanin gecmise uygulandigi varsayilir ve sessiz bir
    # sizinti olurdu. 'kapali' ise suzgec acildiginda hemen fark
    # edilir. Sessiz sizinti, gurultulu arizadan kotudur.
    op.execute("UPDATE cariler SET gorunurluk = 'kapali' WHERE gorunurluk IS NULL")

    op.create_table(
        'cari_erisim',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cari_id', sa.String(length=20), nullable=False),
        sa.Column('kullanici', sa.String(length=50), nullable=False),
        sa.Column('veren', sa.String(length=50), nullable=True),
        sa.Column('olusturma', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cari_id', 'kullanici', name='uq_cari_erisim'),
    )
    op.create_index(op.f('ix_cari_erisim_cari_id'), 'cari_erisim', ['cari_id'])
    op.create_index(op.f('ix_cari_erisim_kullanici'), 'cari_erisim', ['kullanici'])

    op.create_table(
        'cari_kisi',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cari_id', sa.String(length=20), nullable=False),
        sa.Column('ad', sa.String(length=120), nullable=False),
        sa.Column('gorev', sa.String(length=80), nullable=True),
        sa.Column('telefon', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('dil', sa.String(length=30), nullable=True),
        sa.Column('birincil', sa.Boolean(), nullable=True),
        sa.Column('aktif', sa.Boolean(), nullable=True),
        sa.Column('aciklama', sa.Text(), nullable=True),
        sa.Column('olusturma', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_cari_kisi_cari_id'), 'cari_kisi', ['cari_id'])

    # Cari'deki tek `yetkili` alanini ilk kisi olarak tasi — bilgi
    # kaybolmasin, satis ekibi sifirdan girmesin.
    op.execute("""
        INSERT INTO cari_kisi (cari_id, ad, telefon, email, birincil, aktif)
        SELECT id, yetkili, telefon, email, TRUE, TRUE
        FROM cariler
        WHERE yetkili IS NOT NULL AND TRIM(yetkili) <> ''
    """)


def downgrade():
    op.drop_index(op.f('ix_cari_kisi_cari_id'), table_name='cari_kisi')
    op.drop_table('cari_kisi')
    op.drop_index(op.f('ix_cari_erisim_kullanici'), table_name='cari_erisim')
    op.drop_index(op.f('ix_cari_erisim_cari_id'), table_name='cari_erisim')
    op.drop_table('cari_erisim')
    with op.batch_alter_table('cariler', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_cariler_gorunurluk'))
        batch_op.drop_index(batch_op.f('ix_cariler_sorumlu'))
        batch_op.drop_column('gorunurluk')
        batch_op.drop_column('sorumlu')
'''

print(f"  ✓ göç zinciri tek uçlu ({bas_rev})")
print(f"  ✓ yeni revizyon: {YENI_REV}")
print("  ✓ mevcut `yetkili` alanı ilk kişi olarak taşınacak")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_crm_b_sahiplik.py --uygula")
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
print()
print(" ⚠ SÜZGEÇ HENÜZ DEVREDE DEĞİL — bu adım yalnızca veri modeli.")
print("   Mevcut cariler 'kapali' ve sorumluları BOŞ. CRM-C ile süzgeç")
print("   açılmadan ÖNCE sorumluları atayın, yoksa satış ekibi hiçbir")
print("   müşteri göremez.")
print("═" * 70)

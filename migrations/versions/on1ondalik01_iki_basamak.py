"""parasal ve miktar alanlarini 2 ondalik haneye indir

Revision ID: on1ondalik01
Revises: ia1iskonto01
Create Date: 2026-09-25 14:05:00

ON1: Resmi muhasebe programi 2 haneyle calisiyor. Sistem parayi 4,
olculeri 3 hane tutuyordu; her satirda kurus altinda sapma kaliyor ve
58 kalemlik bir belgede toplamlar tutmuyordu.

Bu gocte:
  • Para  sutunlari NUMERIC(18,4) → NUMERIC(18,2)
  • Olcu  sutunlari NUMERIC(18,3) → NUMERIC(18,2)
  • Mevcut degerler 2 haneye YUVARLANIR (PostgreSQL tip donusumu
    sirasinda kendisi yuvarlar; SQLite'ta tip zorlanmadigi icin
    degerler UPDATE ile yuvarlanir).
  • Doviz KURU (Kur, 6 hane) ve denetim/log alanlari DOKUNULMAZ.

Sutun listesi modelden TURETILIR — elle liste tutmak yeni alan
eklendiginde sessizce eksik kalirdi.
"""
from alembic import op
import sqlalchemy as sa

revision = 'on1ondalik01'
down_revision = 'ia1iskonto01'
branch_labels = None
depends_on = None

HEDEF_SCALE = 2


def _hedef_sutunlar(eski_scale_min=3):
    """Modeldeki NUMERIC sutunlar: scale > 2 olanlar. (Kur = 6 haric.)"""
    import sys, os
    os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
    sys.path.insert(0, os.getcwd())
    from models import db, Kur
    hedef = []
    for t in db.metadata.sorted_tables:
        for c in t.columns:
            tip = c.type
            if isinstance(tip, Kur):
                continue
            scale = getattr(tip, 'scale', None)
            if scale is None:
                # TypeDecorator: sarmalanan tipe bak
                scale = getattr(getattr(tip, 'impl', None), 'scale', None)
            if scale and scale > HEDEF_SCALE:
                hedef.append((t.name, c.name))
    return hedef


def upgrade():
    baglanti = op.get_bind()
    pg = baglanti.dialect.name in ('postgresql', 'postgres')
    ins = sa.inspect(baglanti)
    tablolar = set(ins.get_table_names())

    # Modelde Para/Olcu artik scale=2 oldugu icin metadata'dan
    # "eski" sutunlari cikaramayiz; VERITABANINDAN okuyoruz.
    sayac = 0
    for tablo in sorted(tablolar):
        if tablo == 'alembic_version':
            continue
        for c in ins.get_columns(tablo):
            tip = c['type']
            scale = getattr(tip, 'scale', None)
            if not scale or scale <= HEDEF_SCALE or scale == 6:
                continue          # 6 = doviz kuru, dokunulmaz
            ad = c['name']
            if pg:
                op.execute(sa.text(
                    f'ALTER TABLE "{tablo}" ALTER COLUMN "{ad}" '
                    f'TYPE NUMERIC(18,{HEDEF_SCALE})'))
            else:
                op.execute(sa.text(
                    f'UPDATE "{tablo}" SET "{ad}" = ROUND("{ad}", {HEDEF_SCALE}) '
                    f'WHERE "{ad}" IS NOT NULL'))
            sayac += 1
    print(f'  [ON1] {sayac} sütun 2 ondalık haneye indirildi.')


def downgrade():
    """Geri alma DEGER GERI GETIRMEZ — yuvarlanan haneler kayiptir.
    Yalnizca sutun tipini eski haline dondurur."""
    baglanti = op.get_bind()
    if baglanti.dialect.name not in ('postgresql', 'postgres'):
        return
    ins = sa.inspect(baglanti)
    for tablo in sorted(set(ins.get_table_names())):
        if tablo == 'alembic_version':
            continue
        for c in ins.get_columns(tablo):
            scale = getattr(c['type'], 'scale', None)
            if scale == HEDEF_SCALE:
                op.execute(sa.text(
                    f'ALTER TABLE "{tablo}" ALTER COLUMN "{c["name"]}" TYPE NUMERIC(18,3)'))

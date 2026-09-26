"""proforma kalem karsilama plani (F8)

Revision ID: f8plan01
Revises: uz1uretimizi
Create Date: 2026-09-26 18:20:00

Fiyat musteriye taahhut edilmeden once kalemin nasil karsilanacagi
belli olmali: stoktan mi, kendi uretimimizden mi, dis alimla mi.
Bu goc yalnizca ALAN ekler; mevcut proformalara dokunmaz — gecmis
onaylar gecerliligini korur, kontrol YENI onaylarda calisir.
IDEMPOTENT.
"""
from alembic import op
import sqlalchemy as sa

revision = 'f8plan01'
down_revision = 'uz1uretimizi'
branch_labels = None
depends_on = None

TABLO = 'proforma_kalem'
SUTUNLAR = (
    ('karsilama_plan', sa.String(length=10)),
    ('plan_maliyet', sa.Numeric(18, 2)),
    ('plan_notu', sa.String(length=200)),
)


def _mevcut_sutunlar():
    mufettis = sa.inspect(op.get_bind())
    if TABLO not in mufettis.get_table_names():
        return None
    return {s['name'] for s in mufettis.get_columns(TABLO)}


def upgrade():
    var = _mevcut_sutunlar()
    if var is None:
        return
    for ad, tip in SUTUNLAR:
        if ad not in var:
            op.add_column(TABLO, sa.Column(ad, tip, nullable=True))


def downgrade():
    var = _mevcut_sutunlar()
    if var is None:
        return
    for ad, _ in SUTUNLAR:
        if ad in var:
            op.drop_column(TABLO, ad)

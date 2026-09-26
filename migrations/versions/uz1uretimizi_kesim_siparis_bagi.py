"""kesime siparis/kalem/karsilama bagi (F6 / BL-08)

Revision ID: uz1uretimizi
Revises: kk1karsilama
Create Date: 2026-09-26 14:30:00

Uretimin hangi siparis kalemi icin yapildigi kesim kaydinda dursun;
sevk edilen plakadan kaynaga (blok, tedarikci) kadar iz kurulabilsin.
Yalnizca SUTUN EKLER, veriye dokunmaz. IDEMPOTENT.
"""
from alembic import op
import sqlalchemy as sa

revision = 'uz1uretimizi'
down_revision = 'kk1karsilama'
branch_labels = None
depends_on = None

SUTUNLAR = [
    ('siparis_id', sa.String(length=20)),
    ('siparis_kalem_id', sa.Integer()),
    ('karsilama_id', sa.String(length=20)),
]


def _var_mi(tablo, sutun):
    ins = sa.inspect(op.get_bind())
    return tablo in ins.get_table_names() and \
        sutun in {c['name'] for c in ins.get_columns(tablo)}


def upgrade():
    for ad, tip in SUTUNLAR:
        if not _var_mi('kesim', ad):
            with op.batch_alter_table('kesim', schema=None) as b:
                b.add_column(sa.Column(ad, tip, nullable=True))


def downgrade():
    for ad, _ in SUTUNLAR:
        if _var_mi('kesim', ad):
            with op.batch_alter_table('kesim', schema=None) as b:
                b.drop_column(ad)

"""stok tablolarina ve proforma kalemine mense (malin mensei) alani

Revision ID: ms1mense001
Revises: bl1bildirim
Create Date: 2026-09-22 12:30:00

MS1: Bundle/crate etiketi ve ticari faturadaki "Materials of Origin"
bilgisi. Eskiden ticari faturada sabit "TURKEY" yaziyordu; Iran vb.
kaynakli mal da satildigi icin mense kayda baglandi.

Stok tablolarinda varsayilan TURKIYE (BM'nin kabul ettigi yazim).
Proforma kaleminde bos birakilir: bos = TURKIYE sayilir, stoktan
gelen kalemlerde stogun mensei yazilir.

IDEMPOTENT: flask_app._otomatik_migrasyon ayni sutunu acilista
eklemis olabilir; varsa atlanir.
"""
from alembic import op
import sqlalchemy as sa

revision = 'ms1mense001'
down_revision = 'bl1bildirim'
branch_labels = None
depends_on = None

STOK = ['blok_stok', 'plaka_stok', 'ebatli_stok']


def _var_mi(tablo, sutun):
    ins = sa.inspect(op.get_bind())
    return tablo in ins.get_table_names() and \
        sutun in {c['name'] for c in ins.get_columns(tablo)}


def upgrade():
    for t in STOK:
        if not _var_mi(t, 'mense'):
            with op.batch_alter_table(t, schema=None) as b:
                b.add_column(sa.Column('mense', sa.String(length=50), nullable=True))
        op.execute(sa.text(f"UPDATE {t} SET mense = 'TURKIYE' "
                           f"WHERE mense IS NULL OR mense = ''"))
    if not _var_mi('proforma_kalem', 'mense'):
        with op.batch_alter_table('proforma_kalem', schema=None) as b:
            b.add_column(sa.Column('mense', sa.String(length=50), nullable=True))


def downgrade():
    for t in STOK + ['proforma_kalem']:
        if _var_mi(t, 'mense'):
            with op.batch_alter_table(t, schema=None) as b:
                b.drop_column('mense')

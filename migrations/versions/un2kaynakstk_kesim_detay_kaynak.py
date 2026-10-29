"""kesim_detay.kaynak_stok_id — hedef hangi kaynaktan cikti (UN2)

Revision ID: un2kaynakstk
Revises: dt1durumtar
Create Date: 2026-10-28 20:55:00

Cok kaynakli kesimde (PLAKA->EBATLI birden fazla plaka secilebiliyor)
her hedef stok TEK bir kaynaktan gelir; menşeini, ureticisini ve
maliyetini ondan almasi gerekir. Kolon olmadan "hepsi ilk kaynaktan"
varsayimi kaciniimazdi ve karisik menşeli kesimde ticari faturaya
yanlis menşe basiliyordu.

Yalnizca SUTUN EKLER, veriye dokunmaz. IDEMPOTENT.
"""
from alembic import op
import sqlalchemy as sa

revision = 'un2kaynakstk'
down_revision = 'dt1durumtar'
branch_labels = None
depends_on = None

TABLO = 'kesim_detay'
SUTUN = 'kaynak_stok_id'
INDEKS = 'ix_kesim_detay_kaynak_stok_id'


def _var_mi(tablo, sutun):
    ins = sa.inspect(op.get_bind())
    return tablo in ins.get_table_names() and \
        sutun in {c['name'] for c in ins.get_columns(tablo)}


def _indeks_var_mi(tablo, ad):
    ins = sa.inspect(op.get_bind())
    if tablo not in ins.get_table_names():
        return False
    return ad in {i['name'] for i in ins.get_indexes(tablo)}


def upgrade():
    if not _var_mi(TABLO, SUTUN):
        with op.batch_alter_table(TABLO, schema=None) as b:
            b.add_column(sa.Column(SUTUN, sa.String(length=20), nullable=True))
    if not _indeks_var_mi(TABLO, INDEKS):
        op.create_index(INDEKS, TABLO, [SUTUN], unique=False)


def downgrade():
    if _indeks_var_mi(TABLO, INDEKS):
        op.drop_index(INDEKS, table_name=TABLO)
    if _var_mi(TABLO, SUTUN):
        with op.batch_alter_table(TABLO, schema=None) as b:
            b.drop_column(SUTUN)

"""proformaya iskonto_aciklama alani

Revision ID: ia1iskonto01
Revises: ms1mense001
Create Date: 2026-09-25 13:30:00

IA1: genel iskontonun gerekcesi. Belgede (PI ve ticari fatura)
iskonto satirinin altinda basilir. IDEMPOTENT — otomatik migrasyon
sutunu acilista eklemis olabilir.
"""
from alembic import op
import sqlalchemy as sa

revision = 'ia1iskonto01'
down_revision = 'ms1mense001'
branch_labels = None
depends_on = None


def _var_mi(tablo, sutun):
    ins = sa.inspect(op.get_bind())
    return tablo in ins.get_table_names() and \
        sutun in {c['name'] for c in ins.get_columns(tablo)}


def upgrade():
    if not _var_mi('proforma', 'iskonto_aciklama'):
        with op.batch_alter_table('proforma', schema=None) as b:
            b.add_column(sa.Column('iskonto_aciklama', sa.String(length=200), nullable=True))


def downgrade():
    if _var_mi('proforma', 'iskonto_aciklama'):
        with op.batch_alter_table('proforma', schema=None) as b:
            b.drop_column('iskonto_aciklama')

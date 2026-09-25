"""faturaya kur_ozel (sozlesme kuru) alani

Revision ID: fk2ozelkur01
Revises: on1ondalik01
Create Date: 2026-09-25 15:20:00

FK2: faturanin TL karsiligi normalde fatura tarihinin TCMB doviz alis
kurundan bulunur. Sozlesmede kur kararlastirilmissa o kur gecerlidir;
bu alan onu tutar. Bos ise davranis degismez (TCMB). IDEMPOTENT.
"""
from alembic import op
import sqlalchemy as sa

revision = 'fk2ozelkur01'
down_revision = 'on1ondalik01'
branch_labels = None
depends_on = None


def _var_mi(tablo, sutun):
    ins = sa.inspect(op.get_bind())
    return tablo in ins.get_table_names() and \
        sutun in {c['name'] for c in ins.get_columns(tablo)}


def upgrade():
    if not _var_mi('faturalar', 'kur_ozel'):
        with op.batch_alter_table('faturalar', schema=None) as b:
            b.add_column(sa.Column('kur_ozel', sa.Numeric(18, 6), nullable=True))


def downgrade():
    if _var_mi('faturalar', 'kur_ozel'):
        with op.batch_alter_table('faturalar', schema=None) as b:
            b.drop_column('kur_ozel')

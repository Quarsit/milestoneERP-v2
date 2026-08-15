"""sabit gider surum zinciri (grup_id)

Revision ID: sg1grupid0001
Revises: 0c6388f1e72e
Create Date: 2026-08-15 22:55:14.764158

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'sg1grupid0001'
down_revision = '0c6388f1e72e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('sabit_gider', schema=None) as batch_op:
        batch_op.add_column(sa.Column('grup_id', sa.String(length=20), nullable=True))
        batch_op.create_index(batch_op.f('ix_sabit_gider_grup_id'),
                              ['grup_id'], unique=False)

    # Mevcut kayitlar: her biri kendi zincirinin kokudur.
    op.execute("UPDATE sabit_gider SET grup_id = id WHERE grup_id IS NULL")


def downgrade():
    with op.batch_alter_table('sabit_gider', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_sabit_gider_grup_id'))
        batch_op.drop_column('grup_id')

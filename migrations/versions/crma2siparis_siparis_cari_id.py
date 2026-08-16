"""siparis musteri kimlik bagi

Revision ID: crma2siparis
Revises: crmbsahip01
Create Date: 2026-08-16 23:48:49.924544

"""
from alembic import op
import sqlalchemy as sa

revision = 'crma2siparis'
down_revision = 'crmbsahip01'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('siparis_kayit', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cari_id', sa.String(length=20), nullable=True))
        batch_op.create_index(batch_op.f('ix_siparis_kayit_cari_id'),
                              ['cari_id'], unique=False)

    op.execute("UPDATE siparis_kayit SET cari_id = c.id FROM cariler c "
               "WHERE siparis_kayit.cari_id IS NULL AND siparis_kayit.musteri = c.unvan")


def downgrade():
    with op.batch_alter_table('siparis_kayit', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_siparis_kayit_cari_id'))
        batch_op.drop_column('cari_id')

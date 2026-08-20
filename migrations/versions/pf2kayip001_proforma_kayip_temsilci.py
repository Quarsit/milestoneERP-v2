"""proforma kayip kaydi ve satis temsilcisi

Revision ID: pf2kayip001
Revises: crmeaktivite
Create Date: 2026-08-20 12:12:26.864434

"""
from alembic import op
import sqlalchemy as sa

revision = 'pf2kayip001'
down_revision = 'crmeaktivite'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('proforma', schema=None) as batch_op:
        batch_op.add_column(sa.Column('temsilci', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('kayip_sebep', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('kayip_not', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('kayip_tarihi', sa.Date(), nullable=True))
        batch_op.create_index(batch_op.f('ix_proforma_temsilci'), ['temsilci'], unique=False)
        batch_op.create_index(batch_op.f('ix_proforma_kayip_sebep'), ['kayip_sebep'], unique=False)

    # Mevcut proformalarda temsilci BOS kalir. `onaya_gonderen`den
    # kopyalamak CAZIP ama YANLIS olurdu: o alan onaya GONDEREN
    # kisiyi tutar, teklifi HAZIRLAYANI degil. Cogu durumda ayni
    # kisidir ama "cogu durumda" ile veri doldurulmaz — yanlis
    # atfedilmis bir teklif, bos birakilmisdan kotudur.


def downgrade():
    with op.batch_alter_table('proforma', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_proforma_kayip_sebep'))
        batch_op.drop_index(batch_op.f('ix_proforma_temsilci'))
        batch_op.drop_column('kayip_tarihi')
        batch_op.drop_column('kayip_not')
        batch_op.drop_column('kayip_sebep')
        batch_op.drop_column('temsilci')

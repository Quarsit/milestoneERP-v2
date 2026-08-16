"""musteri kimlik bagi (cari_id)

Revision ID: crmacariid01
Revises: sg1grupid0001
Create Date: 2026-08-16 23:08:23.189046

"""
from alembic import op
import sqlalchemy as sa

revision = 'crmacariid01'
down_revision = 'sg1grupid0001'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('proforma', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cari_id', sa.String(length=20), nullable=True))
        batch_op.create_index(batch_op.f('ix_proforma_cari_id'), ['cari_id'], unique=False)

    with op.batch_alter_table('faturalar', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cari_id', sa.String(length=20), nullable=True))
        batch_op.create_index(batch_op.f('ix_faturalar_cari_id'), ['cari_id'], unique=False)

    with op.batch_alter_table('satis_kaydi', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cari_id', sa.String(length=20), nullable=True))
        batch_op.create_index(batch_op.f('ix_satis_kaydi_cari_id'), ['cari_id'], unique=False)

    with op.batch_alter_table('sevkiyat_kayit', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cari_id', sa.String(length=20), nullable=True))
        batch_op.create_index(batch_op.f('ix_sevkiyat_kayit_cari_id'), ['cari_id'], unique=False)

    with op.batch_alter_table('rezervasyon', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cari_id', sa.String(length=20), nullable=True))
        batch_op.create_index(batch_op.f('ix_rezervasyon_cari_id'), ['cari_id'], unique=False)

    # Mevcut kayitlari isimden esle. Sifirlama sonrasi bu tablolar
    # bos oldugu icin normalde 0 satir etkilenir; yine de yaziliyor
    # ki goc baska bir kurulumda da dogru calissin.
    op.execute("UPDATE proforma SET cari_id = c.id FROM cariler c WHERE proforma.cari_id IS NULL AND proforma.musteri = c.unvan")
    op.execute("UPDATE faturalar SET cari_id = c.id FROM cariler c WHERE faturalar.cari_id IS NULL AND faturalar.musteri = c.unvan")
    op.execute("UPDATE satis_kaydi SET cari_id = c.id FROM cariler c WHERE satis_kaydi.cari_id IS NULL AND satis_kaydi.musteri = c.unvan")
    op.execute("UPDATE sevkiyat_kayit SET cari_id = c.id FROM cariler c WHERE sevkiyat_kayit.cari_id IS NULL AND sevkiyat_kayit.musteri = c.unvan")
    op.execute("UPDATE rezervasyon SET cari_id = c.id FROM cariler c WHERE rezervasyon.cari_id IS NULL AND rezervasyon.musteri = c.unvan")


def downgrade():
    with op.batch_alter_table('rezervasyon', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_rezervasyon_cari_id'))
        batch_op.drop_column('cari_id')

    with op.batch_alter_table('sevkiyat_kayit', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_sevkiyat_kayit_cari_id'))
        batch_op.drop_column('cari_id')

    with op.batch_alter_table('satis_kaydi', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_satis_kaydi_cari_id'))
        batch_op.drop_column('cari_id')

    with op.batch_alter_table('faturalar', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_faturalar_cari_id'))
        batch_op.drop_column('cari_id')

    with op.batch_alter_table('proforma', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_proforma_cari_id'))
        batch_op.drop_column('cari_id')

"""cari unvani tasiyan alanlar 200 karaktere (UZ1)

Revision ID: uz1unvan200
Revises: sk1stokcari1
Create Date: 2026-09-01 12:01:48.542530

Uretimde olculdu: 102 karakterlik tedarikci unvani varchar(100)'e
sigmayip toplu stok ice aktarmayi tumuyle engelledi. Cari.unvan
zaten 200; bu alanlar onunla hizalandi.
"""
from alembic import op
import sqlalchemy as sa

revision = 'uz1unvan200'
down_revision = 'sk1stokcari1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('blok_stok', schema=None) as batch_op:
        batch_op.alter_column('uretici', existing_type=sa.String(length=100),
                              type_=sa.String(length=200),
                              existing_nullable=True)
    with op.batch_alter_table('plaka_stok', schema=None) as batch_op:
        batch_op.alter_column('uretici', existing_type=sa.String(length=100),
                              type_=sa.String(length=200),
                              existing_nullable=True)
    with op.batch_alter_table('ebatli_stok', schema=None) as batch_op:
        batch_op.alter_column('uretici', existing_type=sa.String(length=100),
                              type_=sa.String(length=200),
                              existing_nullable=True)
    with op.batch_alter_table('stok_cikis', schema=None) as batch_op:
        batch_op.alter_column('uretici', existing_type=sa.String(length=100),
                              type_=sa.String(length=200),
                              existing_nullable=True)
    with op.batch_alter_table('stok_cikis', schema=None) as batch_op:
        batch_op.alter_column('musteri', existing_type=sa.String(length=100),
                              type_=sa.String(length=200),
                              existing_nullable=True)
    with op.batch_alter_table('siparis_kayit', schema=None) as batch_op:
        batch_op.alter_column('musteri', existing_type=sa.String(length=100),
                              type_=sa.String(length=200),
                              existing_nullable=True)
    with op.batch_alter_table('rezervasyon', schema=None) as batch_op:
        batch_op.alter_column('musteri', existing_type=sa.String(length=100),
                              type_=sa.String(length=200),
                              existing_nullable=True)
    with op.batch_alter_table('sevkiyat_kayit', schema=None) as batch_op:
        batch_op.alter_column('musteri', existing_type=sa.String(length=100),
                              type_=sa.String(length=200),
                              existing_nullable=True)


def downgrade():
    # DIKKAT: 200 karakterlik kayitlar varsa geri alma VERI KESER.
    with op.batch_alter_table('blok_stok', schema=None) as batch_op:
        batch_op.alter_column('uretici', existing_type=sa.String(length=200),
                              type_=sa.String(length=100),
                              existing_nullable=True)
    with op.batch_alter_table('plaka_stok', schema=None) as batch_op:
        batch_op.alter_column('uretici', existing_type=sa.String(length=200),
                              type_=sa.String(length=100),
                              existing_nullable=True)
    with op.batch_alter_table('ebatli_stok', schema=None) as batch_op:
        batch_op.alter_column('uretici', existing_type=sa.String(length=200),
                              type_=sa.String(length=100),
                              existing_nullable=True)
    with op.batch_alter_table('stok_cikis', schema=None) as batch_op:
        batch_op.alter_column('uretici', existing_type=sa.String(length=200),
                              type_=sa.String(length=100),
                              existing_nullable=True)
    with op.batch_alter_table('stok_cikis', schema=None) as batch_op:
        batch_op.alter_column('musteri', existing_type=sa.String(length=200),
                              type_=sa.String(length=100),
                              existing_nullable=True)
    with op.batch_alter_table('siparis_kayit', schema=None) as batch_op:
        batch_op.alter_column('musteri', existing_type=sa.String(length=200),
                              type_=sa.String(length=100),
                              existing_nullable=True)
    with op.batch_alter_table('rezervasyon', schema=None) as batch_op:
        batch_op.alter_column('musteri', existing_type=sa.String(length=200),
                              type_=sa.String(length=100),
                              existing_nullable=True)
    with op.batch_alter_table('sevkiyat_kayit', schema=None) as batch_op:
        batch_op.alter_column('musteri', existing_type=sa.String(length=200),
                              type_=sa.String(length=100),
                              existing_nullable=True)

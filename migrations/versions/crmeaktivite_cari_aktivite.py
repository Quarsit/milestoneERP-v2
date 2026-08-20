"""cari aktivite kaydi

Revision ID: crmeaktivite
Revises: crma2siparis
Create Date: 2026-08-17 08:07:41.708597

"""
from alembic import op
import sqlalchemy as sa

revision = 'crmeaktivite'
down_revision = 'crma2siparis'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'cari_aktivite',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cari_id', sa.String(length=20), nullable=False),
        sa.Column('kisi_id', sa.Integer(), nullable=True),
        sa.Column('tarih', sa.Date(), nullable=True),
        sa.Column('tip', sa.String(length=20), nullable=True),
        sa.Column('ozet', sa.String(length=200), nullable=False),
        sa.Column('detay', sa.Text(), nullable=True),
        sa.Column('sonraki_adim', sa.String(length=200), nullable=True),
        sa.Column('sonraki_tarih', sa.Date(), nullable=True),
        sa.Column('tamamlandi', sa.Boolean(), nullable=True),
        sa.Column('tamamlanma', sa.Date(), nullable=True),
        sa.Column('kullanici', sa.String(length=50), nullable=True),
        sa.Column('olusturma', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_cari_aktivite_cari_id'), 'cari_aktivite', ['cari_id'])
    op.create_index(op.f('ix_cari_aktivite_kisi_id'), 'cari_aktivite', ['kisi_id'])
    op.create_index(op.f('ix_cari_aktivite_tarih'), 'cari_aktivite', ['tarih'])
    op.create_index(op.f('ix_cari_aktivite_tip'), 'cari_aktivite', ['tip'])
    op.create_index(op.f('ix_cari_aktivite_kullanici'), 'cari_aktivite', ['kullanici'])
    # Vadesi gecmis takipleri hizli bulmak icin: sonraki_tarih +
    # tamamlandi birlikte sorgulanacak.
    op.create_index(op.f('ix_cari_aktivite_sonraki_tarih'),
                    'cari_aktivite', ['sonraki_tarih'])
    op.create_index(op.f('ix_cari_aktivite_tamamlandi'),
                    'cari_aktivite', ['tamamlandi'])


def downgrade():
    op.drop_index(op.f('ix_cari_aktivite_tamamlandi'), table_name='cari_aktivite')
    op.drop_index(op.f('ix_cari_aktivite_sonraki_tarih'), table_name='cari_aktivite')
    op.drop_index(op.f('ix_cari_aktivite_kullanici'), table_name='cari_aktivite')
    op.drop_index(op.f('ix_cari_aktivite_tip'), table_name='cari_aktivite')
    op.drop_index(op.f('ix_cari_aktivite_tarih'), table_name='cari_aktivite')
    op.drop_index(op.f('ix_cari_aktivite_kisi_id'), table_name='cari_aktivite')
    op.drop_index(op.f('ix_cari_aktivite_cari_id'), table_name='cari_aktivite')
    op.drop_table('cari_aktivite')

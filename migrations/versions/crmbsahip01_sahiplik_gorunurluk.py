"""cari sahiplik, gorunurluk, erisim ve kisiler

Revision ID: crmbsahip01
Revises: crmacariid01
Create Date: 2026-08-16 23:17:47.305908

"""
from alembic import op
import sqlalchemy as sa

revision = 'crmbsahip01'
down_revision = 'crmacariid01'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('cariler', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sorumlu', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('gorunurluk', sa.String(length=10), nullable=True))
        batch_op.create_index(batch_op.f('ix_cariler_sorumlu'), ['sorumlu'], unique=False)
        batch_op.create_index(batch_op.f('ix_cariler_gorunurluk'), ['gorunurluk'], unique=False)

    # MEVCUT kayitlar da 'kapali'. Kasitli: 'ortak' yapsaydik
    # politikanin gecmise uygulandigi varsayilir ve sessiz bir
    # sizinti olurdu. 'kapali' ise suzgec acildiginda hemen fark
    # edilir. Sessiz sizinti, gurultulu arizadan kotudur.
    op.execute("UPDATE cariler SET gorunurluk = 'kapali' WHERE gorunurluk IS NULL")

    op.create_table(
        'cari_erisim',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cari_id', sa.String(length=20), nullable=False),
        sa.Column('kullanici', sa.String(length=50), nullable=False),
        sa.Column('veren', sa.String(length=50), nullable=True),
        sa.Column('olusturma', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cari_id', 'kullanici', name='uq_cari_erisim'),
    )
    op.create_index(op.f('ix_cari_erisim_cari_id'), 'cari_erisim', ['cari_id'])
    op.create_index(op.f('ix_cari_erisim_kullanici'), 'cari_erisim', ['kullanici'])

    op.create_table(
        'cari_kisi',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cari_id', sa.String(length=20), nullable=False),
        sa.Column('ad', sa.String(length=120), nullable=False),
        sa.Column('gorev', sa.String(length=80), nullable=True),
        sa.Column('telefon', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('dil', sa.String(length=30), nullable=True),
        sa.Column('birincil', sa.Boolean(), nullable=True),
        sa.Column('aktif', sa.Boolean(), nullable=True),
        sa.Column('aciklama', sa.Text(), nullable=True),
        sa.Column('olusturma', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_cari_kisi_cari_id'), 'cari_kisi', ['cari_id'])

    # Cari'deki tek `yetkili` alanini ilk kisi olarak tasi — bilgi
    # kaybolmasin, satis ekibi sifirdan girmesin.
    op.execute("""
        INSERT INTO cari_kisi (cari_id, ad, telefon, email, birincil, aktif)
        SELECT id, yetkili, telefon, email, TRUE, TRUE
        FROM cariler
        WHERE yetkili IS NOT NULL AND TRIM(yetkili) <> ''
    """)


def downgrade():
    op.drop_index(op.f('ix_cari_kisi_cari_id'), table_name='cari_kisi')
    op.drop_table('cari_kisi')
    op.drop_index(op.f('ix_cari_erisim_kullanici'), table_name='cari_erisim')
    op.drop_index(op.f('ix_cari_erisim_cari_id'), table_name='cari_erisim')
    op.drop_table('cari_erisim')
    with op.batch_alter_table('cariler', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_cariler_gorunurluk'))
        batch_op.drop_index(batch_op.f('ix_cariler_sorumlu'))
        batch_op.drop_column('gorunurluk')
        batch_op.drop_column('sorumlu')

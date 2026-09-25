"""kalem karsilama tablosu (F1 / BL-01)

Revision ID: kk1karsilama
Revises: fk2ozelkur01
Create Date: 2026-09-25 23:45:00

Bir siparis kalemi birden cok kaynaktan (stok + uretim + dis alim)
karsilanabilsin diye kaynak kirilimi tablosu. Mevcut rezervasyonlardan
geriye donuk doldurma AYRI betikle yapilir (karsilama_goc.py) — goc
yalnizca semayi kurar, veriye dokunmaz. IDEMPOTENT.
"""
from alembic import op
import sqlalchemy as sa

revision = 'kk1karsilama'
down_revision = 'fk2ozelkur01'
branch_labels = None
depends_on = None


def _tablo_var_mi(ad):
    return ad in sa.inspect(op.get_bind()).get_table_names()


def upgrade():
    if _tablo_var_mi('kalem_karsilama'):
        return
    op.create_table(
        'kalem_karsilama',
        sa.Column('id', sa.String(length=20), primary_key=True),
        sa.Column('siparis_id', sa.String(length=20),
                  sa.ForeignKey('siparis_kayit.id'), nullable=True, index=True),
        sa.Column('siparis_kalem_id', sa.Integer,
                  sa.ForeignKey('siparis_kalem.id'), nullable=False, index=True),
        sa.Column('kaynak_tip', sa.String(length=10), nullable=False),
        sa.Column('kaynak_ref', sa.String(length=50)),
        sa.Column('kaynak_ad', sa.String(length=200)),
        sa.Column('rezervasyon_id', sa.String(length=20), nullable=True, index=True),
        sa.Column('miktar', sa.Numeric(18, 2)),
        sa.Column('birim', sa.String(length=20)),
        sa.Column('birim_maliyet', sa.Numeric(18, 2)),
        sa.Column('doviz', sa.String(length=5)),
        sa.Column('durum', sa.String(length=20)),
        sa.Column('gerceklesen_stok_ids', sa.Text),
        sa.Column('aciklama', sa.Text),
        sa.Column('kullanici', sa.String(length=50)),
        sa.Column('olusturma', sa.DateTime),
        sa.Column('guncelleme', sa.DateTime),
    )


def downgrade():
    if _tablo_var_mi('kalem_karsilama'):
        op.drop_table('kalem_karsilama')

"""siparis durum tarihi (DT1)

Revision ID: dt1durumtar
Revises: f8plan01
Create Date: 2026-09-26 21:55:00

Ekranda "Bu durumda N gundur" yaziyordu ama olctugu sey siparisin
YASIYDI. Bu kolon, durumun en son ne zaman degistigini tutar.

Goc yalnizca ALAN ekler. Mevcut siparisler icin deger BOS kalir;
uygulama bos degeri siparis tarihine dusurur (eski davranis), ilk
durum degisikliginde gercek damga yazilir. Geriye donuk doldurma
AYRI betikle yapilir: durum_tarihi_goc.py  ·  IDEMPOTENT.
"""
from alembic import op
import sqlalchemy as sa

revision = 'dt1durumtar'
down_revision = 'f8plan01'
branch_labels = None
depends_on = None

TABLO = 'siparis_kayit'
SUTUN = 'durum_tarihi'


def _sutunlar():
    mufettis = sa.inspect(op.get_bind())
    if TABLO not in mufettis.get_table_names():
        return None
    return {s['name'] for s in mufettis.get_columns(TABLO)}


def upgrade():
    var = _sutunlar()
    if var is None or SUTUN in var:
        return
    op.add_column(TABLO, sa.Column(SUTUN, sa.DateTime(), nullable=True))


def downgrade():
    var = _sutunlar()
    if var is None or SUTUN not in var:
        return
    op.drop_column(TABLO, SUTUN)

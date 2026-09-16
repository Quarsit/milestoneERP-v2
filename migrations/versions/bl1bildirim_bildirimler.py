"""sistem ici bildirimler (BL1)

Revision ID: bl1bildirim
Revises: kp1carikapsam
Create Date: 2026-09-06 10:00:00.000000

OLAY BASINA TEK KAYIT: bir proforma onaya gonderildiginde tek
bildirim dogar, onay yetkisi olan herkese gorunur. Yetkililerden
biri onaylayinca `kapandi` isaretlenir ve digerleri artik gormez.

Kullanici basina satir acmiyoruz; acsaydik onaylayanin satirini
kapatmak digerlerininkini kapatmaz, herkesin ayri ayri temizlemesi
gerekirdi.
"""
from alembic import op
import sqlalchemy as sa

revision = 'bl1bildirim'
down_revision = 'kp1carikapsam'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'bildirimler',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tip', sa.String(length=30), nullable=False),
        sa.Column('konu_tip', sa.String(length=20), nullable=True),
        sa.Column('konu_id', sa.String(length=40), nullable=True),
        sa.Column('baslik', sa.String(length=160), nullable=True),
        sa.Column('mesaj', sa.Text(), nullable=True),
        sa.Column('hedef_yetki', sa.String(length=40), nullable=True),
        sa.Column('olusturan', sa.String(length=50), nullable=True),
        sa.Column('olusturma', sa.DateTime(), nullable=True),
        sa.Column('kapandi', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('kapatan', sa.String(length=50), nullable=True),
        sa.Column('kapanma', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('bildirimler', schema=None) as b:
        b.create_index('ix_bildirimler_tip', ['tip'])
        b.create_index('ix_bildirimler_konu_id', ['konu_id'])
        b.create_index('ix_bildirimler_olusturma', ['olusturma'])
        b.create_index('ix_bildirimler_kapandi', ['kapandi'])


def downgrade():
    with op.batch_alter_table('bildirimler', schema=None) as b:
        b.drop_index('ix_bildirimler_kapandi')
        b.drop_index('ix_bildirimler_olusturma')
        b.drop_index('ix_bildirimler_konu_id')
        b.drop_index('ix_bildirimler_tip')
    op.drop_table('bildirimler')

"""kullaniciya cari kapsami (KP1)

Revision ID: kp1carikapsam
Revises: uz1unvan200
Create Date: 2026-09-05 22:00:00.000000

YETKI ile KAPSAM ayri eksenler:
  yetkiler → NE yapabilir
  kapsam   → HANGI carilerde yapabilir

Eskiden ikisi tek eksendeydi: muhasebeci tum carilerde islem
yapabilmek icin ADMIN olmak zorundaydi, o da ayarlari ve kullanici
yonetimini aciyordu.

  'atanan' → sorumlusu oldugu + ortak cariler  (satis)
  'tumu'   → butun cariler                     (muhasebe, yonetim)

MEVCUT KULLANICILAR 'atanan' ile baslar — guvenli taraf. Kimsenin
gorunurlugu bu gocle GENISLEMEZ; yoneticinin bilerek 'tumu'
secmesi gerekir.
"""
from alembic import op
import sqlalchemy as sa

revision = 'kp1carikapsam'
down_revision = 'uz1unvan200'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('kullanicilar', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('cari_kapsam', sa.String(length=10),
                      nullable=True, server_default='atanan'))
    # Mevcut satirlarda NULL kalmasin: NULL da 'atanan' sayiliyor
    # ama acik deger, ekranlarda ve sorgularda belirsizlik birakmaz.
    op.execute("UPDATE kullanicilar SET cari_kapsam = 'atanan' "
               "WHERE cari_kapsam IS NULL")


def downgrade():
    with op.batch_alter_table('kullanicilar', schema=None) as batch_op:
        batch_op.drop_column('cari_kapsam')

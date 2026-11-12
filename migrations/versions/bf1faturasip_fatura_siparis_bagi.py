"""fatura <-> siparis bagi: birlesik fatura (BF1)

Revision ID: bf1faturasip
Revises: un2kaynakstk
Create Date: 2026-11-06 23:55:00.000000

`Fatura.siparis_id` TEK bir alandi. Kullanici birkac teslimati tek
faturada birlestirmek istiyor (ayni cariye birden fazla sevkiyat);
tek alan buna yetmiyor.

Alan KALDIRILMIYOR: dokuz ayri yer ona bakiyor ve gocten once
acilmis faturalarin bagi yalnizca orada. Artik "birincil siparis"
anlaminda duruyor, kapsamin tamami bu tabloda.

`firma_id` ZORUNLU: sifirlamanin TEK FIRMA kipi sildigi her tabloda
bu sutunu ariyor. Ilk tasarimda "saf bag tablosu, kapsam gerekmez"
diye yazmistim; SZ1 denetim testi yakaladi ve hakliydi.

═══ BU GOC IKI SIRAYA DA DAYANIKLI ═══

OLCULDU: uygulama acilista `db.create_all()` cagiriyor. Servis
gocten ONCE yeniden baslatilirsa tablo BOS olarak olusuyor ve duz
bir `create_table` "table fatura_siparis already exists" ile
patliyor — `flask db upgrade` tumuyle duruyor.

Bu yuzden:
  · tablo VARSA kurulmuyor, yalnizca geriye doldurma yapiliyor
  · geriye doldurma NOT EXISTS ile korunuyor, yani iki kez
    kosturulsa da yinelenen satir uretmiyor

Boylece "once goc sonra restart" ve "once restart sonra goc"
siralarinin ikisi de ayni sonuca variyor.

═══ GERIYE DOLDURMA ═══

Mevcut her faturanin `siparis_id`si bag tablosuna kopyalaniyor;
boylece tablo tek basina da yeterli oluyor. Kapi (`_siparis_faturalari`)
yine de eski alani OR'luyor: kopyalanmamis ya da bag yazmadan
`siparis_id` koyan bir yol kalirsa fatura gene bulunur. Yanlis
tarafa dusmek cift faturalama demek.
"""
from alembic import op
import sqlalchemy as sa

revision = 'bf1faturasip'
down_revision = 'un2kaynakstk'
branch_labels = None
depends_on = None

GERIYE_DOLDUR = """
INSERT INTO fatura_siparis (fatura_id, siparis_id, firma_id)
SELECT f.id, f.siparis_id, f.firma_id
FROM   faturalar f
WHERE  f.siparis_id IS NOT NULL
  AND  f.siparis_id <> ''
  AND  f.firma_id IS NOT NULL
  AND  NOT EXISTS (SELECT 1 FROM fatura_siparis b
                   WHERE b.fatura_id = f.id
                     AND b.siparis_id = f.siparis_id)
"""


def upgrade():
    baglanti = op.get_bind()
    mevcut = sa.inspect(baglanti).get_table_names()

    if 'fatura_siparis' not in mevcut:
        op.create_table(
            'fatura_siparis',
            sa.Column('fatura_id', sa.String(length=20), nullable=False),
            sa.Column('siparis_id', sa.String(length=20), nullable=False),
            sa.Column('firma_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['firma_id'], ['firma.id']),
            sa.PrimaryKeyConstraint('fatura_id', 'siparis_id'),
        )
        with op.batch_alter_table('fatura_siparis', schema=None) as toplu:
            toplu.create_index('ix_fatura_siparis_fatura_id',
                               ['fatura_id'], unique=False)
            toplu.create_index('ix_fatura_siparis_siparis_id',
                               ['siparis_id'], unique=False)
            toplu.create_index('ix_fatura_siparis_firma_id',
                               ['firma_id'], unique=False)
    else:
        # Tablo `db.create_all()` ile dizinsiz kurulmus olabilir.
        # Eksik dizinleri ekle; var olani atla.
        var = {d['name'] for d in
               sa.inspect(baglanti).get_indexes('fatura_siparis')}
        with op.batch_alter_table('fatura_siparis', schema=None) as toplu:
            for ad, sutun in (
                    ('ix_fatura_siparis_fatura_id', 'fatura_id'),
                    ('ix_fatura_siparis_siparis_id', 'siparis_id'),
                    ('ix_fatura_siparis_firma_id', 'firma_id')):
                if ad not in var:
                    toplu.create_index(ad, [sutun], unique=False)

    op.execute(sa.text(GERIYE_DOLDUR))


def downgrade():
    baglanti = op.get_bind()
    if 'fatura_siparis' not in sa.inspect(baglanti).get_table_names():
        return
    var = {d['name'] for d in
           sa.inspect(baglanti).get_indexes('fatura_siparis')}
    with op.batch_alter_table('fatura_siparis', schema=None) as toplu:
        for ad in ('ix_fatura_siparis_firma_id',
                   'ix_fatura_siparis_siparis_id',
                   'ix_fatura_siparis_fatura_id'):
            if ad in var:
                toplu.drop_index(ad)
    op.drop_table('fatura_siparis')

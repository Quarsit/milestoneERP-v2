"""stok tablolarina cari_id (tedarikci kimlik bagi)

Revision ID: sk1stokcari1
Revises: pf2kayip001
Create Date: 2026-08-23 14:27:40.650260

"""
from alembic import op
import sqlalchemy as sa

revision = 'sk1stokcari1'
down_revision = 'pf2kayip001'
branch_labels = None
depends_on = None

TABLOLAR = ['blok_stok', 'plaka_stok', 'ebatli_stok']


def upgrade():
    for t in TABLOLAR:
        with op.batch_alter_table(t, schema=None) as batch_op:
            batch_op.add_column(sa.Column('cari_id', sa.String(length=20),
                                          nullable=True))
            batch_op.create_index(batch_op.f(f'ix_{t}_cari_id'), ['cari_id'],
                                  unique=False)

    # Uretici ADINDAN cari cozulur. ESLESMEYEN BOS BIRAKILIR —
    # yanlis cariye baglamak SF2'deki hatanin ta kendisiydi.
    baglanti = op.get_bind()
    harita = {}
    for _id, _unvan in baglanti.execute(sa.text(
            'SELECT id, unvan FROM cariler WHERE unvan IS NOT NULL')):
        harita[(_unvan or '').strip().upper()] = _id

    eslesen = bos = 0
    for t in TABLOLAR:
        for _sid, _uret in list(baglanti.execute(sa.text(
                f'SELECT id, uretici FROM {t} WHERE uretici IS NOT NULL'))):
            _cid = harita.get((_uret or '').strip().upper())
            if _cid:
                baglanti.execute(
                    sa.text(f'UPDATE {t} SET cari_id = :c WHERE id = :s'),
                    {'c': _cid, 's': _sid})
                eslesen += 1
            else:
                bos += 1
    print(f'  [SK1] {eslesen} stok cariye baglandi, {bos} kayit eslesmedi.')


def downgrade():
    for t in TABLOLAR:
        with op.batch_alter_table(t, schema=None) as batch_op:
            batch_op.drop_index(batch_op.f(f'ix_{t}_cari_id'))
            batch_op.drop_column('cari_id')

#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — STOKTA TEDARİKÇİ KİMLİK BAĞI  ·  SK1 (model)
#
#  ── SORUN ──
#    Stok tablolarinda tedarikci yalnizca `uretici` ALANINDA, AD
#    olarak duruyor. Kimlik bagi yok.
#
#    Sonucu uretimde goruldu: stok silinirken bagli alis faturasi
#    aranirken cari ADLA eslestirilmek zorunda kalindi (SF2). Ad
#    degisirse ya da iki cari benzer adliysa bag kopar.
#
#    Bu projede ayni hatanin bes ornegini duzelttik; CRM-A'da alti
#    tabloya `cari_id` eklemistik. Stok tablolari disarida kalmisti.
#
#  ── EKLENEN ──
#    BlokStok / PlakaStok / EbatliStok → `cari_id` (indeksli)
#
#  ── GERİYE DOLDURMA ──
#    Mevcut kayitlarda `uretici` adindan cari cozulup yaziliyor.
#    ESLESMEYEN kayit BOS BIRAKILIR — yanlis cariye baglamaktansa
#    bos kalmasi yeglenir. Goc sonunda kac kaydin eslestigi
#    bildirilir.
#
#    Buyuk/kucuk harf duyarsiz karsilastirma; Turkce 'İ' sorunu
#    icin iki taraf da ayni yontemle normalize ediliyor.
#
#  ── `uretici` ALANI KALIYOR ──
#    Silmek gecmis kayitlarda tedarikci adini kaybettirirdi
#    (cari silinmis olabilir). Ad GORUNTU icin, cari_id BAG icin.
#
#  KULLANIM (proje klasöründe):
#      python yama_sk1_stok_cari.py            # rapor
#      python yama_sk1_stok_cari.py --uygula
#      venv/bin/python goc.py uygula           # ŞART
# ══════════════════════════════════════════════════════════════════════
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
MOD = Path('models.py')
GOC = Path('migrations/versions')

if not MOD.exists():
    print("HATA: models.py bu klasörde yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

ham = MOD.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


print("═" * 70)
print(" SK1 · STOKTA TEDARİKÇİ KİMLİK BAĞI")
print("═" * 70)
print()

if 'SK1: TEDARIKCI KIMLIK BAGI' in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

icerik = ham
eklenen = []
for sinif, tablo in (('BlokStok', 'blok_stok'), ('PlakaStok', 'plaka_stok'),
                     ('EbatliStok', 'ebatli_stok')):
    m = re.search(rf"^class {sinif}\(db\.Model\):", icerik, re.M)
    if not m:
        print(f" ✗ {sinif} bulunamadı. DOSYAYA DOKUNULMADI.")
        sys.exit(1)
    son = icerik.find('\nclass ', m.end())
    son = son if son > 0 else len(icerik)
    govde = icerik[m.start():son]
    capa = re.search(r"^(    uretici\s+= .*)$", govde, re.M)
    if not capa:
        print(f" ✗ {sinif} içinde 'uretici' alanı bulunamadı. DOSYAYA DOKUNULMADI.")
        sys.exit(1)
    yeni = capa.group(1) + uyarla('''
    # SK1: TEDARIKCI KIMLIK BAGI.
    # `uretici` bir AD; ad degisirse ya da iki cari benzer adliysa
    # bag kopar. Uretimde olculdu: stok silinirken bagli fatura
    # ADLA eslestirilmek zorunda kalindi (SF2).
    # `uretici` GORUNTU icin kaliyor, cari_id BAG icin.
    cari_id         = db.Column(db.String(20), index=True)''')
    icerik = icerik[:m.start()] + govde.replace(capa.group(1), yeni, 1) + icerik[son:]
    eklenen.append((sinif, tablo))

try:
    compile(icerik.replace('\r\n', '\n'), 'models.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

for s, t in eklenen:
    print(f"  ✓ {s:<12} cari_id eklendi")
print("  ✓ sözdizimi doğrulandı (compile)")

# ── Göç zinciri ──
zincir = {}
for f in sorted(GOC.glob('*.py')):
    t = f.read_text(encoding='utf-8', errors='replace')
    r = re.search(r"^revision = '([^']+)'", t, re.M)
    d = re.search(r"^down_revision = '([^']+)'", t, re.M)
    if r:
        zincir[r.group(1)] = d.group(1) if d else None
uclar = [r for r in zincir if r not in set(v for v in zincir.values() if v)]
if len(uclar) != 1:
    print(f" ✗ Göç zincirinde {len(uclar)} uç: {uclar}. DOSYAYA DOKUNULMADI.")
    sys.exit(1)
bas = uclar[0]
REV = 'sk1stokcari1'
GOC_DOSYA = GOC / f'{REV}_stok_cari_kimlik.py'
GOC_ICERIK = f'''"""stok tablolarina cari_id (tedarikci kimlik bagi)

Revision ID: {REV}
Revises: {bas}
Create Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}

"""
from alembic import op
import sqlalchemy as sa

revision = '{REV}'
down_revision = '{bas}'
branch_labels = None
depends_on = None

TABLOLAR = ['blok_stok', 'plaka_stok', 'ebatli_stok']


def upgrade():
    for t in TABLOLAR:
        with op.batch_alter_table(t, schema=None) as batch_op:
            batch_op.add_column(sa.Column('cari_id', sa.String(length=20),
                                          nullable=True))
            batch_op.create_index(batch_op.f(f'ix_{{t}}_cari_id'), ['cari_id'],
                                  unique=False)

    # ── GERİYE DOLDURMA ──
    # `uretici` adindan cari cozulur. ESLESMEYEN kayit BOS BIRAKILIR —
    # yanlis cariye baglamaktansa bos kalmasi yeglenir; SF2'deki
    # hatanin (yanlis cariye karsi kayit) kaynagi tam olarak yanlis
    # eslestirmeydi.
    baglanti = op.get_bind()
    cariler = list(baglanti.execute(sa.text(
        'SELECT id, unvan FROM cariler WHERE unvan IS NOT NULL')))
    harita = {{}}
    for _id, _unvan in cariler:
        harita[(_unvan or '').strip().upper()] = _id

    toplam_eslesen = toplam_bos = 0
    for t in TABLOLAR:
        satirlar = list(baglanti.execute(sa.text(
            f'SELECT id, uretici FROM {{t}} WHERE uretici IS NOT NULL')))
        for _sid, _uret in satirlar:
            _cid = harita.get((_uret or '').strip().upper())
            if _cid:
                baglanti.execute(
                    sa.text(f'UPDATE {{t}} SET cari_id = :c WHERE id = :s'),
                    {{'c': _cid, 's': _sid}})
                toplam_eslesen += 1
            else:
                toplam_bos += 1
    print(f'  [SK1] {{toplam_eslesen}} stok cariye baglandi, '
          f'{{toplam_bos}} kayit eslesmedi (bos birakildi).')


def downgrade():
    for t in TABLOLAR:
        with op.batch_alter_table(t, schema=None) as batch_op:
            batch_op.drop_index(batch_op.f(f'ix_{{t}}_cari_id'))
            batch_op.drop_column('cari_id')
'''

print(f"  ✓ göç zinciri tek uçlu ({bas})")
print(f"  ✓ yeni revizyon: {REV}")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_sk1_stok_cari.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = MOD.with_name(f'models.py.yedek-{damga}')
shutil.copy2(MOD, yedek)
MOD.write_bytes(icerik.encode('utf-8'))
GOC_DOSYA.write_text(GOC_ICERIK, encoding='utf-8')
print()
print(f" ✓ models.py  (yedek: {yedek.name})")
print(f" ✓ {GOC_DOSYA}")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print(" ⚠ ŞEMA DEĞİŞTİ:  venv/bin/python goc.py uygula")
print("   Göç, mevcut stokları üretici adından cariye bağlar ve")
print("   kaç kaydın eşleştiğini yazar.")
print("═" * 70)

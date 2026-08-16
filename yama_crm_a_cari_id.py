#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — MÜŞTERİ KİMLİK BAĞI  ·  CRM-A
#
#  ── SORUN ──
#    Müşteri geçmişi İSİMLE bağlı:
#
#        Siparis, CariHareket, Cek  →  cari_id  ✓
#        Proforma, Fatura, SatisKaydi, Sevkiyat, Rezervasyon
#                                   →  yalnizca musteri (metin)  ✗
#
#    `Cari.unvan` BENZERSIZ DEGIL ve duzenlenebiliyor. Bir musterinin
#    adini duzeltirseniz ("ACME Inc" -> "ACME Marble Inc", ya da bir
#    yazim hatasi) o firmanin tum proforma/fatura/sevkiyat/satis
#    gecmisi KOPAR. Kod 14 yerde filter_by(unvan=...) yapiyor.
#
#  ── NEDEN ŞİMDİ ──
#    Sifirlama sonrasi bu bes tablo BOS. Eslestirilecek gecmis kayit
#    yok, goc sifir riskle geciyor. Bir yil gercek veriden sonra ayni
#    is, yuzlerce kaydi isimden eslestirip eslesmeyenleri elle
#    cozmeye donerdi.
#
#  ── NEDEN CRM'İN ÖN KOŞULU ──
#    Musteri bazli gorunurluk (ortak / kapali) planlaniyor. Bir
#    proformanin hangi musteriye ait oldugunu isim eslesmesiyle
#    bulmak, gizli kalmasi gereken bir teklifin sizmasi demektir.
#    Gorunurluk kararı kirilgan bir eslesmeye dayanamaz.
#
#  ── OTOMATİK DOLDURMA — NEDEN OLAY DİNLEYİCİSİ ──
#    Bu bes tabloyu 11 ayri fonksiyon olusturuyor. Hepsini elle
#    duzenlemek, 12.'si eklendiginde unutulmasi demek — kayit
#    sessizce sahipsiz kalirdi. Bunun yerine SQLAlchemy
#    `before_insert` dinleyicisi: cari_id bos gelirse `musteri`
#    adindan cozulur. Ileride eklenecek her kod kendiliginden
#    kapsanir.
#
#    Dinleyici ham baglanti uzerinden SELECT yapar; oturumu
#    kullanmak flush icinde ozyineleme riski dogururdu.
#
#  ── AÇIKTA KALAN ──
#    Eslesme bulunamazsa cari_id NULL kalir (kayit reddedilmez —
#    fatura kesilmesini engellemek daha kotu olurdu). Bunlari
#    bulmak icin: crm_bag_denetim.py
#
#  KULLANIM (proje klasöründe):
#      python yama_crm_a_cari_id.py            # rapor
#      python yama_crm_a_cari_id.py --uygula
#      venv/bin/python goc.py uygula           # ŞART
# ══════════════════════════════════════════════════════════════════════
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
if not GOC.exists():
    print("HATA: migrations/versions yok.")
    sys.exit(1)

TABLOLAR = {
    'Proforma': 'proforma',
    'Fatura': 'faturalar',
    'SatisKaydi': 'satis_kaydi',
    'Sevkiyat': 'sevkiyat_kayit',
    'Rezervasyon': 'rezervasyon',
}

print("═" * 70)
print(" CRM-A · MÜŞTERİ KİMLİK BAĞI")
print("═" * 70)
print()

ham = MOD.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


if 'cari_id_otomatik_doldur' in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

icerik = ham
eklenen = []

# ── Her modele cari_id sütunu ──
import re as _re
for sinif, tablo in TABLOLAR.items():
    m = _re.search(rf"^class {sinif}\(db\.Model\):", icerik, _re.M)
    if not m:
        print(f" ✗ {sinif} sınıfı bulunamadı — DOSYAYA DOKUNULMADI.")
        sys.exit(1)
    # Sinifin 'musteri' satirini bul, hemen ardina ekle.
    bas = m.start()
    son = icerik.find('\nclass ', bas + 10)
    son = son if son > 0 else len(icerik)
    govde = icerik[bas:son]
    if 'cari_id' in govde:
        print(f"  ↷ {sinif:<12} zaten cari_id var")
        continue
    mm = _re.search(r"^(    musteri +=.*)$", govde, _re.M)
    if not mm:
        print(f" ✗ {sinif} içinde 'musteri' alanı bulunamadı.")
        sys.exit(1)
    yeni_satir = (mm.group(1) + uyarla(
        "\n    # Musteri KIMLIGI. Onceden bag yalnizca `musteri` metniydi;"
        "\n    # unvan duzenlenince gecmis koptugu icin eklendi (CRM-A)."
        "\n    cari_id         = db.Column(db.String(20), index=True)"))
    govde_yeni = govde.replace(mm.group(1), yeni_satir, 1)
    icerik = icerik[:bas] + govde_yeni + icerik[son:]
    eklenen.append(sinif)
    print(f"  ✓ {sinif:<12} cari_id eklenecek  ({tablo})")

# ── Otomatik doldurma dinleyicisi ──
DINLEYICI = '''

# ══════════════════════════════════════════════════════════════════
#  MUSTERI KIMLIGI OTOMATIK DOLDURMA  (CRM-A)
#
#  Asagidaki bes tabloyu 11 ayri fonksiyon olusturuyor. Her birine
#  elle `cari_id=` eklemek, 12.'si yazildiginda unutulmasi demekti —
#  kayit sessizce sahipsiz kalirdi. Bunun yerine kayit yazilirken
#  `musteri` adindan cozuluyor; ileride eklenecek her kod
#  kendiliginden kapsaniyor.
#
#  Ham baglanti uzerinden SELECT yapiliyor: oturumu kullanmak flush
#  icinde ozyineleme riski dogururdu.
#
#  Eslesme bulunamazsa cari_id NULL kalir ve kayit REDDEDILMEZ.
#  Fatura kesilmesini engellemek, eksik bagdan kotu olurdu.
#  Acikta kalanlari bulmak icin: crm_bag_denetim.py
# ══════════════════════════════════════════════════════════════════
from sqlalchemy import event as _event, text as _text


def cari_id_otomatik_doldur(mapper, connection, target):
    if getattr(target, 'cari_id', None):
        return
    unvan = (getattr(target, 'musteri', None) or '').strip()
    if not unvan:
        return
    try:
        r = connection.execute(
            _text('SELECT id FROM cariler WHERE unvan = :u LIMIT 1'),
            {'u': unvan}).fetchone()
        if r:
            target.cari_id = r[0]
    except Exception:
        # Baglanti cozulmezse kayit YINE DE yazilir; eksik bag
        # denetimle bulunur, veri kaybi olmaz.
        pass


for _model in (Proforma, Fatura, SatisKaydi, Sevkiyat, Rezervasyon):
    _event.listen(_model, 'before_insert', cari_id_otomatik_doldur)
'''

icerik = icerik.rstrip('\r\n') + uyarla(DINLEYICI)

try:
    compile(icerik.replace('\r\n', '\n'), 'models.py', 'exec')
except SyntaxError as exc:
    print(f"\n ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print("  ✓ otomatik doldurma dinleyicisi eklenecek")
print("  ✓ sözdizimi doğrulandı (compile)")

# ── Göç ──
zincir = {}
for f in sorted(GOC.glob('*.py')):
    t = f.read_text(encoding='utf-8', errors='replace')
    r = _re.search(r"^revision = '([^']+)'", t, _re.M)
    d = _re.search(r"^down_revision = '([^']+)'", t, _re.M)
    if r:
        zincir[r.group(1)] = d.group(1) if d else None
uclar = [r for r in zincir if r not in set(v for v in zincir.values() if v)]
if len(uclar) != 1:
    print(f"\n ✗ Göç zincirinde {len(uclar)} uç: {uclar}. DOSYAYA DOKUNULMADI.")
    sys.exit(1)
bas_rev = uclar[0]
YENI_REV = 'crmacariid01'
GOC_DOSYA = GOC / f'{YENI_REV}_cari_kimlik_bagi.py'

_ops = '\n\n'.join(
    f"""    with op.batch_alter_table('{t}', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cari_id', sa.String(length=20), nullable=True))
        batch_op.create_index(batch_op.f('ix_{t}_cari_id'), ['cari_id'], unique=False)"""
    for t in TABLOLAR.values())
_geri = '\n\n'.join(
    f"""    with op.batch_alter_table('{t}', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_{t}_cari_id'))
        batch_op.drop_column('cari_id')"""
    for t in reversed(list(TABLOLAR.values())))

GOC_ICERIK = f'''"""musteri kimlik bagi (cari_id)

Revision ID: {YENI_REV}
Revises: {bas_rev}
Create Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}

"""
from alembic import op
import sqlalchemy as sa

revision = '{YENI_REV}'
down_revision = '{bas_rev}'
branch_labels = None
depends_on = None


def upgrade():
{_ops}

    # Mevcut kayitlari isimden esle. Sifirlama sonrasi bu tablolar
    # bos oldugu icin normalde 0 satir etkilenir; yine de yaziliyor
    # ki goc baska bir kurulumda da dogru calissin.
{chr(10).join(f"    op.execute(\"UPDATE {t} SET cari_id = c.id FROM cariler c WHERE {t}.cari_id IS NULL AND {t}.musteri = c.unvan\")" for t in TABLOLAR.values())}


def downgrade():
{_geri}
'''

print(f"  ✓ göç zinciri tek uçlu ({bas_rev})")
print(f"  ✓ yeni revizyon: {YENI_REV}")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_crm_a_cari_id.py --uygula")
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
print(" ⚠ ŞEMA DEĞİŞTİ:")
print("     venv/bin/python goc.py uygula")
print("     venv/bin/python crm_bag_denetim.py")
print("═" * 70)

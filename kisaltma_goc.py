#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — CARİ KISALTMA GÖÇÜ  (RN1)
#
#  ── NE İÇİN ──
#    Yeni belge numaraları carinin 3 harfli kısaltmasından üretiliyor:
#        SIP-STN26-03   ·   PI-STN26-01   ·   FTR-STN26-02
#    Kısaltma cari kartında durur. Bugüne kadar yalnızca üretici/
#    tedarikçi kartlarında doluydu; bu betik TÜM carilere benzersiz bir
#    kısaltma yazar.
#
#  ── KURAL ──
#    İlk kelimenin ilk harfi + sonraki sessizler:
#        PINAR MERMER    → PNR
#        STONELAND USA   → STN
#        NORTHSTONE      → NRT
#    Çakışma olursa RAKAM DEĞİL, unvanın sıradaki sessiz harfleri
#    denenir; sessiz kalmazsa sesliler:
#        STONELAND USA → STN · STONELAND MIAMI → STL · CANADA → STD
#        ALIMOĞLU → ALM · ALIMKAR → ALK · ALIM TAŞ → ALT
#    Kartta görünür; istediğin zaman değiştirirsin.
#
#  ── GÜVENLİ ──
#    • Dolu kısaltmalara DOKUNMAZ.
#    • Yalnızca `uretici_kisaltma` alanını yazar, başka hiçbir alanı değil.
#    • Tekrar çalıştırılabilir.
#
#  ── KULLANIM ──
#      venv/bin/python kisaltma_goc.py            # rapor
#      venv/bin/python kisaltma_goc.py --uygula   # yaz
# ══════════════════════════════════════════════════════════════════════
import os
import sys
from pathlib import Path

if not Path('flask_app.py').exists():
    print('HATA: flask_app.py bu klasörde yok. Proje klasöründe çalıştırın.')
    sys.exit(1)

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

UYGULA = '--uygula' in sys.argv
for _a in sys.argv[1:]:
    if _a.startswith('--url='):
        os.environ['DATABASE_URL'] = _a.split('=', 1)[1]

if not os.environ.get('DATABASE_URL'):
    print('HATA: DATABASE_URL bulunamadı (.env okunamadı).')
    sys.exit(1)

os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
sys.path.insert(0, str(Path('.').resolve()))

import flask_app  # noqa: E402
from models import db, Cari  # noqa: E402

TR = str.maketrans('ÇĞİIÖŞÜçğıiöşü', 'CGIIOSUCGIIOSU')
UNLU = set('AEIOU')


ABC = 'BCDFGHJKLMNPRSTVYZXQWAEIOU'   # once sessizler, sonra sesliler


def adaylar(unvan):
    """flask_app._kisaltma_adaylari ile AYNI kural (o fonksiyon uygulama
    fabrikasının içinde olduğu için burada birebir tekrarlanır)."""
    s = str(unvan or '').translate(TR).upper()
    kelimeler = [''.join(h for h in k if h.isalpha()) for k in s.split()]
    kelimeler = [k for k in kelimeler if k]
    if not kelimeler:
        yield 'XXX'
        return
    ilk = kelimeler[0][0]
    kalan = list(kelimeler[0][1:]) + [h for k in kelimeler[1:] for h in k]
    havuz = [h for h in kalan if h not in UNLU] + \
            [h for h in kalan if h in UNLU]
    gorulen = set()

    def ver(a):
        if len(a) == 3 and a not in gorulen:
            gorulen.add(a)
            return a
        return None

    ikinci = havuz[0] if havuz else 'X'
    for u in havuz[1:]:
        a = ver(ilk + ikinci + u)
        if a:
            yield a
    for i in range(len(havuz)):
        for j in range(len(havuz)):
            if i == j:
                continue
            a = ver(ilk + havuz[i] + havuz[j])
            if a:
                yield a
    for u in ABC:
        a = ver(ilk + ikinci + u)
        if a:
            yield a
    for v in ABC:
        for u in ABC:
            a = ver(ilk + v + u)
            if a:
                yield a


def bos_bul(unvan, kullanilan):
    for a in adaylar(unvan):
        if a not in kullanilan:
            return a
    on = (str(unvan or 'X').translate(TR).upper() + 'XX')[:1]
    for i in range(2, 100):
        a = f'{on}{i:02d}'
        if a not in kullanilan:
            return a
    return 'XXX'


print('═' * 74)
print(' CARİ KISALTMA GÖÇÜ (RN1) — belge numaraları bu kısaltmadan üretilir')
print('═' * 74)

with flask_app.app.app_context():
    cariler = Cari.query.order_by(Cari.unvan).all()
    kullanilan = {(c.uretici_kisaltma or '').strip().upper()
                  for c in cariler if (c.uretici_kisaltma or '').strip()}
    bos = [c for c in cariler if not (c.uretici_kisaltma or '').strip()]

    print(f' {len(cariler)} cari · {len(kullanilan)} kısaltma dolu · {len(bos)} boş')
    print()
    if not bos:
        print(' ✓ Her carinin kısaltması var.')
        sys.exit(0)

    plan = []
    for c in bos:
        aday = bos_bul(c.unvan, kullanilan)
        kullanilan.add(aday)
        plan.append((c, aday))

    for c, aday in plan[:25]:
        print(f'   {aday}   {(c.unvan or "")[:56]}')
    if len(plan) > 25:
        print(f'   … ve {len(plan) - 25} cari daha')

    if not UYGULA:
        print()
        print(' Bu bir ÖN İZLEME. Yazmak için: venv/bin/python kisaltma_goc.py --uygula')
        sys.exit(0)

    for c, aday in plan:
        c.uretici_kisaltma = aday
    db.session.commit()
    print()
    print(f' ✓ {len(plan)} cariye kısaltma yazıldı.')
    print(' Cari kartından istediğini değiştirebilirsin; yeni belgeler ona göre numaralanır.')

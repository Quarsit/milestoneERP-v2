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
#    Çakışma olursa unvanın ilk üç harfi, o da doluysa rakamla ayrılır
#    (STN → STO → ST2). Kartta görünür; istediğin zaman değiştirirsin.
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


def kisaltma_uret(unvan):
    """flask_app._kisaltma_uret ile AYNI kural (o fonksiyon uygulama
    fabrikasının içinde olduğu için burada birebir tekrarlanır)."""
    if not unvan:
        return 'XXX'
    s = str(unvan).translate(TR).upper().strip()
    kelime = next((k for k in s.split() if k and k[0].isalpha()), '')
    harfler = [h for h in kelime if h.isalpha()]
    if not harfler:
        return 'XXX'
    sonuc = harfler[0]
    for h in harfler[1:]:
        if h not in UNLU:
            sonuc += h
        if len(sonuc) == 3:
            break
    for h in harfler[1:]:
        if len(sonuc) >= 3:
            break
        if h not in sonuc:
            sonuc += h
    return (sonuc + 'XXX')[:3]


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
        aday = kisaltma_uret(c.unvan)
        if aday in kullanilan:
            harfler = ''.join(h for h in str(c.unvan).translate(TR).upper() if h.isalpha())
            alternatif = (harfler + 'XXX')[:3]
            if alternatif not in kullanilan:
                aday = alternatif
            else:
                for i in range(2, 10):
                    deneme = aday[:2] + str(i)
                    if deneme not in kullanilan:
                        aday = deneme
                        break
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

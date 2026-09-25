#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — KASA MUTABAKATI  (F10)
#
#  ── NE İÇİN ──
#    Kasa bakiyesi kolonda SAKLANIYOR ve her işlemde artımlı
#    güncelleniyor (tahsilat, ödeme, virman, çek, manuel hareket).
#    Bu hızlıdır ama bir yol bakiyeyi güncellemeyi atlarsa ya da bir
#    hareket sonradan elle silinirse, saklı bakiye ile hareketlerin
#    toplamı SESSİZCE ayrışır: kasa ekranı bir rakam, kasa defteri
#    başka bir rakam gösterir.
#
#    Bu betik ikisini karşılaştırır. Fark varsa, farkın hangi tarihten
#    sonra başladığını bulmak için son hareketleri de yazar.
#
#  ── VARSAYILAN: SALT OKUNUR ──
#    venv/bin/python kasa_mutabakat.py            # rapor
#    venv/bin/python kasa_mutabakat.py --duzelt   # saklı bakiyeyi
#                                                 # hareket toplamına çeker
#    Düzeltme yalnızca BAKİYE kolonunu yazar; hiçbir hareket eklenmez
#    ya da silinmez. Önce raporu okuyun: fark bir eksik hareketten
#    geliyorsa doğru çözüm o hareketi girmektir, bakiyeyi ezmek değil.
# ══════════════════════════════════════════════════════════════════════
import os
import sys
from pathlib import Path

if not Path('flask_app.py').exists():
    print('HATA: flask_app.py bu klasörde yok. Proje klasöründe çalıştırın.')
    sys.exit(1)

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

DUZELT = '--duzelt' in sys.argv
for _a in sys.argv[1:]:
    if _a.startswith('--url='):
        os.environ['DATABASE_URL'] = _a.split('=', 1)[1]

if not os.environ.get('DATABASE_URL'):
    print('HATA: DATABASE_URL bulunamadı (.env okunamadı).')
    sys.exit(1)

os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
sys.path.insert(0, str(Path('.').resolve()))

import flask_app  # noqa: E402
from models import db, Kasa, KasaHareket  # noqa: E402


def para(v):
    return f'{float(v or 0):,.2f}'.replace(',', '#').replace('.', ',').replace('#', '.')


print('═' * 74)
print(' KASA MUTABAKATI — saklı bakiye ile hareket toplamı karşılaştırılır')
print('═' * 74)

with flask_app.app.app_context():
    kasalar = Kasa.query.order_by(Kasa.ad).all()
    sapan = []
    for k in kasalar:
        hrk = KasaHareket.query.filter_by(kasa_id=k.id).all()
        giris = sum(float(h.tutar or 0) for h in hrk if h.tip == 'giris')
        cikis = sum(float(h.tutar or 0) for h in hrk if h.tip == 'cikis')
        hesap = round(giris - cikis, 2)
        sakli = round(float(k.bakiye or 0), 2)
        fark = round(sakli - hesap, 2)
        durum = '✓' if abs(fark) < 0.01 else '✗'
        print(f' {durum} {k.ad:24} {k.doviz or "":4} '
              f'saklı {para(sakli):>16}   hareket {para(hesap):>16}'
              + (f'   FARK {para(fark)}' if abs(fark) >= 0.01 else ''))
        if abs(fark) >= 0.01:
            sapan.append((k, hesap, fark, hrk))

    print()
    if not sapan:
        print(' ✓ Tüm kasalar tutuyor — saklı bakiye hareket toplamına eşit.')
        sys.exit(0)

    print(f' {len(sapan)} kasada sapma var. Son hareketler:')
    for k, hesap, fark, hrk in sapan:
        print()
        print(f' ── {k.ad} ({k.doviz}) · fark {para(fark)}')
        son = sorted(hrk, key=lambda h: (h.tarih or __import__("datetime").date.min,
                                         h.id or 0))[-5:]
        for h in son:
            isaret = '+' if h.tip == 'giris' else '−'
            print(f'    {str(h.tarih or "—"):12} {isaret}{para(h.tutar):>14}  '
                  f'{(h.aciklama or "")[:52]}')
        print('    → Fark bir hareketin EKSİK olmasından geliyorsa doğru çözüm '
              'o hareketi girmektir.')

    if not DUZELT:
        print()
        print(' Bu bir RAPOR. Saklı bakiyeyi hareket toplamına çekmek için:')
        print('   venv/bin/python kasa_mutabakat.py --duzelt')
        sys.exit(1)

    for k, hesap, fark, _ in sapan:
        k.bakiye = hesap
    db.session.commit()
    print()
    print(f' ✓ {len(sapan)} kasanın bakiyesi hareket toplamına çekildi.')

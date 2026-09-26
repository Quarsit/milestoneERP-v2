#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — CARİ BAĞI GÖÇÜ  (BL-16)
#
#  ── NE İÇİN ──
#    Belgeler müşteriyi hem KİMLİKLE (cari_id) hem ADIYLA taşır. Ad
#    belgede basıldığı için gerekli; ama BAĞ adla kurulduğunda ünvan
#    değişikliği bağı sessizce koparıyordu:
#
#      • açık faturalar listesi boşalıyor, tahsilat girilemiyor
#      • silme koruması "bağlı kayıt yok" diyor, cari silinebiliyor
#      • kârlılık aynı müşteriyi iki satıra bölüyor
#
#    Artık ünvan değişince bağlı kayıtların görünen adı KİMLİK
#    üzerinden eşitleniyor. Bunun geçmiş kayıtlarda da çalışması için
#    kimliğin DOLU olması gerekir — bu betik onu doldurur.
#
#  ── NE YAPAR ──
#    Kimliği boş her kaydın adını cari tablosunda arar ve bulursa
#    cari_id yazar. Eşleşme: birebir, sonra boşluk/büyük-küçük harf
#    duyarsız.
#
#  ── GÜVENLİ ──
#    • Yalnızca BOŞ cari_id doldurulur; dolu olan hiç ellenmez.
#    • Hiçbir ad, tutar ya da durum değiştirilmez.
#    • Eşleşmeyen kayıtlar RAPORLANIR, tahmin yürütülmez — yanlış
#      cariye bağlamak, bağlamamaktan kötüdür.
#    • Tekrar çalıştırılabilir.
#
#  ── KULLANIM (proje klasöründe) ──
#      venv/bin/python cari_bag_goc.py            # rapor
#      venv/bin/python cari_bag_goc.py --uygula   # yaz
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
from models import (db, Cari, Siparis, Proforma, Fatura, SatisKaydi,  # noqa: E402
                    Sevkiyat, Rezervasyon, CariHareket, Cek,
                    BlokStok, PlakaStok, EbatliStok)

# (model, ad kolonu, insan adı)
HEDEFLER = [
    (Siparis, 'musteri', 'Sipariş'),
    (Proforma, 'musteri', 'Proforma'),
    (Fatura, 'musteri', 'Fatura'),
    (SatisKaydi, 'musteri', 'Satış kaydı'),
    (Sevkiyat, 'musteri', 'Sevkiyat'),
    (Rezervasyon, 'musteri', 'Rezervasyon'),
    (CariHareket, 'cari_unvan', 'Cari hareket'),
    (Cek, 'cari_unvan', 'Çek'),
    (BlokStok, 'uretici', 'Blok stok'),
    (PlakaStok, 'uretici', 'Plaka stok'),
    (EbatliStok, 'uretici', 'Ebatlı stok'),
]


def _norm(s):
    return ' '.join((s or '').split()).strip().upper() \
        .replace('İ', 'I').replace('İ', 'I')


print('═' * 74)
print(' CARİ BAĞI GÖÇÜ (BL-16) — belgelerin müşteri KİMLİĞİ doldurulur')
print('═' * 74)

with flask_app.app.app_context():
    cariler = Cari.query.all()
    birebir = {c.unvan: c.id for c in cariler if c.unvan}
    normal = {}
    for c in cariler:
        if c.unvan:
            normal.setdefault(_norm(c.unvan), c.id)

    print(f' {len(cariler)} cari okundu.')
    print()

    plan = []          # (model, kolon, kayit, cari_id)
    eslesmeyen = {}    # ad -> kaç kayıt
    ozet = []

    for model, kolon, insan in HEDEFLER:
        sutun = getattr(model, kolon)
        bos = model.query.filter(model.cari_id.is_(None)).all()
        dolu = model.query.filter(model.cari_id.isnot(None)).count()
        bulunan = 0
        for kayit in bos:
            ad = (getattr(kayit, kolon, None) or '').strip()
            if not ad:
                continue
            cid = birebir.get(ad) or normal.get(_norm(ad))
            if cid:
                plan.append((model, kolon, kayit, cid))
                bulunan += 1
            else:
                eslesmeyen[ad] = eslesmeyen.get(ad, 0) + 1
        ozet.append((insan, dolu, len(bos), bulunan))

    genislik = max(len(o[0]) for o in ozet)
    print(f' {"Kayıt tipi":<{genislik}}  {"kimliği var":>11}  {"boş":>6}  {"eşleşen":>8}')
    print(' ' + '─' * (genislik + 32))
    for insan, dolu, bos_sayi, bulunan in ozet:
        isaret = '' if bos_sayi == bulunan else '  ← eşleşmeyen var'
        print(f' {insan:<{genislik}}  {dolu:>11}  {bos_sayi:>6}  {bulunan:>8}{isaret}')

    print()
    print(f' Bağlanacak kayıt: {len(plan)}')

    if eslesmeyen:
        print()
        print(f' ⚠ Cari tablosunda BULUNAMAYAN {len(eslesmeyen)} ad '
              f'({sum(eslesmeyen.values())} kayıt):')
        for ad, adet in sorted(eslesmeyen.items(), key=lambda x: -x[1])[:15]:
            print(f'    {adet:>4} kayıt   "{ad[:58]}"')
        if len(eslesmeyen) > 15:
            print(f'    … ve {len(eslesmeyen) - 15} ad daha')
        print()
        print(' Bunlar TAHMİNLE bağlanmaz. Doğru davranış: bu adlarla cari')
        print(' kartı açmak ya da adı doğru cariyle aynı yazmak, sonra bu')
        print(' betiği yeniden çalıştırmak.')

    if not plan:
        print()
        print(' ✓ Bağlanacak yeni kayıt yok.')
        sys.exit(0)

    if not UYGULA:
        print()
        print(' Bu bir ÖN İZLEME. Yazmak için:')
        print('   venv/bin/python cari_bag_goc.py --uygula')
        sys.exit(0)

    yazilan = 0
    for model, kolon, kayit, cid in plan:
        kayit.cari_id = cid
        yazilan += 1
        if yazilan % 300 == 0:
            db.session.commit()
    db.session.commit()
    print()
    print(f' ✓ {yazilan} kaydın müşteri kimliği dolduruldu.')
    print(' Artık cari ünvanı değiştirildiğinde bu kayıtların adı da eşitlenir.')

#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — KARŞILAMA GÖÇÜ  (F1 / BL-01)
#
#  ── NE İÇİN ──
#    Yeni `kalem_karsilama` tablosu, bir sipariş kaleminin hangi
#    kaynaklardan (stok / üretim / dış alım) karşılandığını tutar.
#    Bugüne kadarki siparişlerde bu kırılım REZERVASYONLARDA örtük
#    duruyor: her rezervasyon bir "stoktan karşılama" satırıdır.
#
#    Bu betik mevcut rezervasyonları okuyup eksik STOK karşılama
#    satırlarını oluşturur. Böylece geçmiş siparişler de yeni
#    kârlılık ve fatura-tipi mantığıyla doğru çalışır.
#
#  ── GÜVENLİ ──
#    • Yalnızca EKLER; hiçbir rezervasyonu ya da kalemi değiştirmez.
#    • İptal edilmiş rezervasyonlar atlanır.
#    • Aynı rezervasyon için satır varsa tekrar yazılmaz (idempotent).
#
#  ── KULLANIM ──
#      venv/bin/python karsilama_goc.py            # rapor
#      venv/bin/python karsilama_goc.py --uygula   # yaz
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
from models import (db, KalemKarsilama, Rezervasyon, SiparisKalem,  # noqa: E402
                    BlokStok, PlakaStok, EbatliStok)

STOK_SINIF = {'BLOK': BlokStok, 'PLAKA': PlakaStok, 'EBATLI': EbatliStok}


def _olcu(stok, birim):
    """Stoğun verilen birimdeki ölçüsü (uygulamadaki mantığın sadesi)."""
    b = (birim or '').lower()
    if b == 'ton':
        return float(getattr(stok, 'tonaj', 0) or 0)
    if b == 'm3':
        return float(getattr(stok, 'hacim_m3', 0) or 0)
    if b == 'sqft':
        return float(getattr(stok, 'metraj_sqft', 0) or 0)
    if b == 'adet':
        return 1.0
    return float(getattr(stok, 'metraj_m2', 0) or 0)


print('═' * 74)
print(' KARŞILAMA GÖÇÜ — rezervasyonlardan "stoktan karşılama" satırları')
print('═' * 74)

with flask_app.app.app_context():
    rezler = Rezervasyon.query.filter(Rezervasyon.iptal_nedeni.is_(None)).all()
    mevcut = {k.rezervasyon_id for k in KalemKarsilama.query.all() if k.rezervasyon_id}
    eklenecek, atlanan_kalemsiz, atlanan_stoksuz = [], 0, 0

    for r in rezler:
        if r.id in mevcut:
            continue
        if not r.siparis_kalem_id:
            atlanan_kalemsiz += 1
            continue
        kalem = SiparisKalem.query.get(r.siparis_kalem_id)
        if not kalem:
            atlanan_kalemsiz += 1
            continue
        sinif = STOK_SINIF.get((r.stok_tip or '').upper())
        stok = sinif.query.get(r.stok_id) if sinif else None
        if not stok:
            atlanan_stoksuz += 1
            continue
        birim = (kalem.birim or ('ton' if r.stok_tip == 'BLOK' else 'm2')).lower()
        eklenecek.append((r, kalem, stok, birim))

    print(f' {len(rezler)} aktif rezervasyon · {len(mevcut)} zaten kırılımlı')
    print(f' eklenecek: {len(eklenecek)}'
          + (f' · kalemsiz atlanan: {atlanan_kalemsiz}' if atlanan_kalemsiz else '')
          + (f' · stoğu bulunamayan: {atlanan_stoksuz}' if atlanan_stoksuz else ''))
    print()
    if not eklenecek:
        print(' ✓ Yapacak bir şey yok.')
        sys.exit(0)

    ornek = eklenecek[:8]
    for r, kalem, stok, birim in ornek:
        print(f'   {kalem.siparis_id:14} kalem#{kalem.id:<5} {r.stok_id:14} '
              f'{_olcu(stok, birim):8.2f} {birim}')
    if len(eklenecek) > len(ornek):
        print(f'   … ve {len(eklenecek) - len(ornek)} satır daha')

    if not UYGULA:
        print()
        print(' Bu bir ÖN İZLEME. Yazmak için: venv/bin/python karsilama_goc.py --uygula')
        sys.exit(0)

    sayac = 0
    for r, kalem, stok, birim in eklenecek:
        db.session.add(KalemKarsilama(
            # _yeni_id uygulama fabrikasinin icinde; burada
            # rezervasyon id'sinden TUREYEN sabit bir kimlik kullanilir
            # (tekrar calistirilinca ayni satir iki kez yazilmasin).
            id=('KRS' + (r.id or '')[-16:]),
            siparis_id=kalem.siparis_id, siparis_kalem_id=kalem.id,
            kaynak_tip='STOK', kaynak_ref=r.stok_id,
            kaynak_ad=f'{getattr(stok, "cins", "") or ""} {r.stok_id}'.strip(),
            rezervasyon_id=r.id,
            miktar=round(_olcu(stok, birim), 2), birim=birim,
            birim_maliyet=float(getattr(stok, 'alis_fiyati', 0) or 0),
            doviz=getattr(stok, 'doviz', None) or 'USD',
            durum='Gerceklesti', kullanici='goc'))
        sayac += 1
        if sayac % 200 == 0:
            db.session.commit()
    db.session.commit()
    print()
    print(f' ✓ {sayac} stok karşılama satırı oluşturuldu.')
    print(' Üretim ve dış alım satırları sipariş ekranından elle eklenir.')

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GEÇMİŞ KESİM STOKLARINI İŞARETLE  (kaynak = 'kesim')
=====================================================

Kesim, oluşturduğu stoğun `kaynak` alanını hiç yazmıyordu; model
varsayılanı devreye girip 'satinalma' kalıyordu. Yani kesimden çıkan
her plaka "satın alındı" diye kayıtlıydı — kimse satın almamış
olmasına rağmen.

Yama bunu BUNDAN SONRASI için düzeltiyor. Bu betik GEÇMİŞİ düzeltir:
bir `KesimDetay` kaydında hedef olarak geçen her stoğu bulur ve
`kaynak` alanını 'kesim' yapar.

Dokunulan tek alan `kaynak`. Fiyat, maliyet, ölçü, fatura, durum —
hiçbiri değişmez. Muhasebede hiçbir şey oynamaz; değişen, ekranın ne
söylediği ve denetimin ne görebildiği.

KULLANIM
--------
  venv/bin/python goc_kesim_kaynak.py              # RAPOR — yazmaz
  venv/bin/python goc_kesim_kaynak.py --uygula     # yazar
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')

import flask_app as fa                                    # noqa: E402
from models import (db, BlokStok, PlakaStok, EbatliStok,   # noqa: E402
                    KesimDetay)

UYGULA = '--uygula' in sys.argv
MODEL = {'BLOK': BlokStok, 'PLAKA': PlakaStok, 'EBATLI': EbatliStok}


def main():
    with fa.app.app_context():
        print('=' * 70)
        print('  KESİMDEN ÇIKAN STOKLAR — kaynak alanı')
        print('  MOD: ' + ('UYGULA' if UYGULA else 'RAPOR (yazmaz)'))
        print('=' * 70)

        hedefler = {}
        for d in KesimDetay.query.all():
            if d.hedef_stok_id and d.hedef_tip in MODEL:
                hedefler.setdefault(d.hedef_tip, set()).add(d.hedef_stok_id)

        if not hedefler:
            print('  Kesim kaydı yok — yapılacak bir şey yok.')
            print('=' * 70)
            return 0

        degisecek, zaten = 0, 0
        for tip, idler in sorted(hedefler.items()):
            Model = MODEL[tip]
            kayitlar = Model.query.filter(Model.id.in_(idler)).all()
            bu_tip = [s for s in kayitlar
                      if (getattr(s, 'kaynak', None) or 'satinalma') != 'kesim']
            zaten += len(kayitlar) - len(bu_tip)
            if not bu_tip:
                continue
            print()
            print(f'── {tip} · {len(bu_tip)} kayıt ' + '─' * 28)
            for s in bu_tip[:12]:
                eski = getattr(s, 'kaynak', None) or 'satinalma'
                print(f'   {s.id:<22} {eski!r:<13} → \'kesim\'')
                if UYGULA:
                    s.kaynak = 'kesim'
            if len(bu_tip) > 12:
                print(f'   … ve {len(bu_tip) - 12} kayıt daha')
                if UYGULA:
                    for s in bu_tip[12:]:
                        s.kaynak = 'kesim'
            degisecek += len(bu_tip)

        print()
        print('=' * 70)
        if zaten:
            print(f'  {zaten} kayıt zaten \'kesim\' — atlandı.')
        if not degisecek:
            print('  ✓ Değişecek bir şey yok.')
        elif UYGULA:
            db.session.commit()
            print(f'  ✓ {degisecek} kayıt güncellendi.')
            print('  Tarayıcıda Ctrl+F5 — stok kartında artık')
            print('  "Kesim Maliyeti" yazar ve uydurma alış tipi gitmiştir.')
        else:
            print(f'  {degisecek} kayıt güncellenecek. Yazmak için:')
            print('      venv/bin/python goc_kesim_kaynak.py --uygula')
        print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

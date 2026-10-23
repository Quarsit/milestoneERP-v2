#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KAÇ ÜRETİM STOĞU VAR — SALT OKUNUR SAYIM
=========================================

`denetim_uretim_maliyet.py` "bedeli girilmemiş üretim stoğu yok"
dedi. Bu iki anlama gelebilir:

  a) üretim stokların var ve hepsinin bedeli girili   → her şey yolunda
  b) hiç üretim stoğun yok                            → betiğin bakacak
                                                        bir şeyi yoktu

Denetim betiği bu ikisini ayırmıyordu — benim eksiğim. Bu sayım
ayırıyor. Hiçbir şey yazmaz.

KULLANIM
--------
  venv/bin/python sayim_uretim.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')

import flask_app as fa                                    # noqa: E402
from models import BlokStok, PlakaStok, EbatliStok        # noqa: E402


def main():
    with fa.app.app_context():
        print('=' * 64)
        print('  STOK SAYIMI — KAYNAĞINA GÖRE')
        print('=' * 64)
        print(f'  {"":<8}{"toplam":>9}{"üretim":>9}{"kesim":>9}'
              f'{"satın alma":>13}')
        print('  ' + '-' * 48)
        top_u = top_k = 0
        for ad, M in (('BLOK', BlokStok), ('PLAKA', PlakaStok),
                      ('EBATLI', EbatliStok)):
            t = M.query.count()
            u = M.query.filter(M.kaynak == 'uretim').count()
            # KS1: kesimden çıkan stok artık kendi adıyla anılıyor.
            k = M.query.filter(M.kaynak == 'kesim').count()
            top_u += u
            top_k += k
            print(f'  {ad:<8}{t:>9}{u:>9}{k:>9}{t - u - k:>13}')
        print()
        if top_k:
            print(f'  {top_k} stok KESİMDEN çıkmış — kimse satın almadı,'
                  f' bloktan kesildi.')
            print()
        if top_u:
            # DİKKAT: bu betik bedele BAKMAZ, yalnız sayar. "Hepsinin
            # bedeli girili" demek denetim betiğinin işi — ikisini
            # birbirine karıştırmak tam da kaçınmaya çalıştığımız şey.
            print(f'  {top_u} üretim stoğu var.')
            print('  denetim_uretim_maliyet.py bunlarda bedeli')
            print('  girilmemiş olan var mı diye bakar; temiz çıktıysa')
            print('  gerçekten temiz demektir.')
        else:
            print('  Hiç üretim stoğu yok — denetimin bakacağı bir şey')
            print('  yoktu. Kendi ocağın olmadığı için beklenen de bu.')
        print('=' * 64)
    return 0


if __name__ == '__main__':
    sys.exit(main())

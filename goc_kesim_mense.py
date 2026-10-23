#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KESİM STOKLARININ MENŞEİNİ KAYNAĞINDAN DÜZELT
==============================================

Kesim, oluşturduğu stoğun `mense` alanını hiç yazmıyordu; model
varsayılanı devreye girip 'TURKIYE' kalıyordu. ARNAVUTLUK menşeli
bir bloktan kesilen plaka TÜRK MALI olarak kaydoluyordu.

NEDEN ÖNEMLİ: bu değer ticari faturaya ve kasa etiketine BASILIYOR.
Fatura şablonu tüm kalemlerin menşei TURKIYE ise
"the goods are of Turkish origin" yazıyor. Yani yanlış menşe beyanı.

Yama bunu bundan sonrası için düzeltti. Bu betik GEÇMİŞİ düzeltir:
her kesim hedefini kaynak bloğunun menşeine çeker.

Dokunulan tek alan `mense`. Başka hiçbir şey değişmez.

KULLANIM
--------
  venv/bin/python goc_kesim_mense.py              # RAPOR — yazmaz
  venv/bin/python goc_kesim_mense.py --uygula     # yazar
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')

import flask_app as fa                                     # noqa: E402
from models import (db, BlokStok, PlakaStok, EbatliStok,    # noqa: E402
                    Kesim, KesimDetay)

UYGULA = '--uygula' in sys.argv
MODEL = {'BLOK': BlokStok, 'PLAKA': PlakaStok, 'EBATLI': EbatliStok}


def _kaynak_mense(kesim):
    """Kesimin kaynak stoğunun menşei."""
    if not kesim or not kesim.kaynak_id:
        return None
    for Model in (BlokStok, PlakaStok, EbatliStok):
        s = db.session.get(Model, kesim.kaynak_id)
        if s:
            return getattr(s, 'mense', None) or None
    return None


def main():
    with fa.app.app_context():
        print('=' * 72)
        print('  KESİM STOKLARININ MENŞEİ')
        print('  MOD: ' + ('UYGULA' if UYGULA else 'RAPOR (yazmaz)'))
        print('=' * 72)

        kesimler = {k.id: k for k in Kesim.query.all()}
        degisecek, ayni, kaynaksiz = [], 0, 0

        for d in KesimDetay.query.all():
            if not d.hedef_stok_id or d.hedef_tip not in MODEL:
                continue
            hedef = db.session.get(MODEL[d.hedef_tip], d.hedef_stok_id)
            if hedef is None:
                continue
            km = _kaynak_mense(kesimler.get(d.kesim_id))
            if not km:
                kaynaksiz += 1
                continue
            mevcut = getattr(hedef, 'mense', None) or ''
            if mevcut == km:
                ayni += 1
                continue
            degisecek.append((d.hedef_tip, hedef, mevcut, km))

        if kaynaksiz:
            print(f'  · {kaynaksiz} hedefin kaynağı bulunamadı (silinmiş'
                  f' olabilir) — dokunulmadı.')
        if ayni:
            print(f'  · {ayni} hedefin menşei zaten doğru.')

        if not degisecek:
            print()
            print('  ✓ Düzeltilecek bir şey yok.')
            print('=' * 72)
            return 0

        # Menşe değişimlerini GRUPLAYARAK göster: 66 satır okunmaz,
        # "ARNAVUTLUK → TURKIYE, 24 kayıt" okunur.
        gruplar = {}
        for tip, hedef, eski, yeni in degisecek:
            gruplar.setdefault((tip, eski or '(boş)', yeni), []).append(hedef)

        print()
        for (tip, eski, yeni), kayitlar in sorted(gruplar.items()):
            print(f'── {tip} · {len(kayitlar)} kayıt ' + '─' * 26)
            print(f'   {eski}  →  {yeni}')
            for h in kayitlar[:6]:
                print(f'      {h.id}')
            if len(kayitlar) > 6:
                print(f'      … ve {len(kayitlar) - 6} kayıt daha')
            print()

        if UYGULA:
            for _tip, hedef, _eski, yeni in degisecek:
                hedef.mense = yeni
            db.session.commit()
            print('=' * 72)
            print(f'  ✓ {len(degisecek)} kayıt düzeltildi.')
            print('  Ticari fatura ve etiket artık doğru menşei basar.')
            print('  DAHA ÖNCE BASILMIŞ belgeleri kontrol et.')
        else:
            print('=' * 72)
            print(f'  {len(degisecek)} kayıt düzeltilecek. Yazmak için:')
            print('      venv/bin/python goc_kesim_mense.py --uygula')
        print('=' * 72)
    return 0


if __name__ == '__main__':
    sys.exit(main())

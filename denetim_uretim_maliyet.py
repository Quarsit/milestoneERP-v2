#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MALİYETİ OLMAYAN ÜRETİM STOKLARI — SALT OKUNUR DENETİM
=======================================================

Kaynağı "üretim" olan ama alış/üretim bedeli girilmemiş stokları
bulur. Böyle bir stokta maliyet YALNIZCA sonradan eklenen gider
kalemlerinden ibaret kalır; satılırsa kâr olduğundan büyük görünür.

ÖLÇÜLDÜ (deneme verisiyle): aynı 10.000 USD'lik satış,
  · bedeli girilmemiş üretim bloğunda   kâr 9.999 USD
  · 6.000 USD bedelli üretim bloğunda   kâr 3.999 USD

Bu betik HİÇBİR ŞEY YAZMAZ. Yalnız okur ve listeler.

KULLANIM
--------
  venv/bin/python denetim_uretim_maliyet.py
  venv/bin/python denetim_uretim_maliyet.py --satilmis   # yalnız satılmışlar
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')

import flask_app as fa                                   # noqa: E402
from models import (db, BlokStok, PlakaStok, EbatliStok,  # noqa: E402
                    SatisKaydi, Maliyet)

YALNIZ_SATILMIS = '--satilmis' in sys.argv
TIPLER = (('BLOK', BlokStok, 'blok_no'),
          ('PLAKA', PlakaStok, 'blok_no'),
          ('EBATLI', EbatliStok, 'kasa_no'))


def _bedel(s):
    """Stoğun KENDİ bedeli — matrah varsa o, yoksa fiyat x ölçü."""
    matrah = float(getattr(s, 'matrah', 0) or 0)
    if matrah > 0:
        return matrah
    fiyat = float(getattr(s, 'alis_fiyati', 0) or 0)
    if not fiyat:
        return 0.0
    birim = (getattr(s, 'alis_fiyat_birim', None) or '').lower()
    olcu = {'ton': getattr(s, 'tonaj', 0),
            'm3': getattr(s, 'hacim_m3', 0),
            'm2': getattr(s, 'metraj_m2', 0),
            'sqft': getattr(s, 'metraj_m2', 0)}.get(birim, 0)
    return fiyat * float(olcu or 0)


def main():
    with fa.app.app_context():
        print('=' * 72)
        print('  KAYNAĞI ÜRETİM, BEDELİ GİRİLMEMİŞ STOKLAR')
        print('=' * 72)
        toplam, satilmis_zarar = 0, 0.0
        for ad, Model, no_alan in TIPLER:
            kayitlar = [s for s in Model.query.filter(
                Model.kaynak == 'uretim').all() if _bedel(s) <= 0]
            if YALNIZ_SATILMIS:
                kayitlar = [s for s in kayitlar
                            if (s.durum or '') == 'Satildi']
            if not kayitlar:
                continue
            print()
            print(f'── {ad} · {len(kayitlar)} kayıt ' + '─' * 30)
            for s in kayitlar:
                toplam += 1
                ek = db.session.query(
                    db.func.sum(Maliyet.usd_karsilik)).filter(
                        Maliyet.baglanti_id == s.id,
                        Maliyet.aktif.is_(True)).scalar() or 0
                sk = SatisKaydi.query.filter_by(stok_id=s.id).first()
                satir = (f'  {s.id:<22} {getattr(s, no_alan, "") or "—":<14}'
                         f' {(s.cins or "")[:18]:<18}'
                         f' durum {s.durum or "—":<9}'
                         f' ek maliyet {float(ek):>9,.2f} $')
                if sk:
                    kar = float(sk.kar_usd or 0)
                    satilmis_zarar += kar
                    satir += f'  SATILDI · kayıtlı kâr {kar:>10,.2f} $'
                print(satir)

        print()
        print('=' * 72)
        if not toplam:
            print('  ✓ Bedeli girilmemiş üretim stoğu yok.')
        else:
            print(f'  {toplam} stokta üretim bedeli YOK.')
            if satilmis_zarar:
                print(f'  Bunlardan satılmış olanların kayıtlı kârı'
                      f' {satilmis_zarar:,.2f} USD — üretim bedeli'
                      f' girilseydi bu rakam DÜŞECEKTİ.')
            print()
            print('  Düzeltmek için: Depo → Stok → ilgili kayıt →')
            print('  Düzenle → "Üretim Maliyeti" alanına birim bedeli')
            print('  gir. Satılmışların kârı kaydedince tazelenir.')
        print('=' * 72)
    return 0


if __name__ == '__main__':
    sys.exit(main())

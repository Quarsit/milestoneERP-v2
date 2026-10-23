#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VADE DENETİMİ — anlamsız vadeler ve yaşlanmayan faturalar
==========================================================

VT1 yamasıyla birlikte okunur. Yama YENİ kayıtları düzeltiyor;
bu betik ESKİ kayıtların durumunu gösteriyor.

── NE ARIYOR ──

  1. NAKİT HAREKETİNDE VADE
     Tahsilat, ödeme, virman, mahsup, kur farkı — bunlarda vade
     anlamsız. Form eskiden her harekette vadeyi BUGÜNLE
     dolduruyordu; bu yüzden tahsil edilmiş paralar "yaklaşan
     ödemeler" listesine düşüyordu.

     Yamadan sonra o liste işlem tipine de baktığı için sorun
     görünmüyor; ama kayıtlardaki anlamsız tarih duruyor.

  2. VADESİZ AÇIK FATURA
     Vadesi boş fatura, VT1'den önce hiç "gecikmiş" görünmüyordu.
     Artık gecikme fatura tarihinden sayılıyor — yani bu faturalar
     YAMADAN SONRA birden gecikmiş görünecek. Hangileri olduğunu
     önceden bilmek iyi olur.

  3. ÖDEME VADESİ TANIMSIZ CARİLER
     Cari kartındaki "Ödeme Vadesi (gün)" doluysa yeni faturanın
     vadesi kendiliğinden hesaplanıyor. Boşsa her faturada elle
     girmek gerekiyor — girilmezse (2) oluşuyor.

── KULLANIM ──

  venv/bin/python denetim_vade.py              # RAPOR (hiçbir şey değişmez)
  venv/bin/python denetim_vade.py --temizle    # (1)'deki vadeleri siler

  --temizle YALNIZCA nakit hareketlerinin vade alanını boşaltır.
  Tutara, kasaya, bakiyeye DOKUNMAZ. Öncesinde JSON yedek yazar.
"""

import json
import os
import sys
from datetime import date

TEMIZLE = '--temizle' in sys.argv
KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')

import flask_app as fa                                    # noqa: E402
from models import db, CariHareket, Fatura, Cari          # noqa: E402

# VT1 ile AYNI liste olmali (flask_app.NAKIT_TIPLERI).
NAKIT_TIPLERI = ('Tahsilat', 'Odeme', 'Ödeme',
                 'Avans Tahsilati', 'Avans Tahsilatı',
                 'Avans Odemesi', 'Avans Ödemesi',
                 'Kur Farki (Borc)', 'Kur Farki (Alacak)',
                 'Bakiye Transfer', 'Mahsup')

CIZGI = '═' * 72


def ana():
    with fa.app.app_context():
        bugun = date.today()
        print(CIZGI)
        print('  VADE DENETİMİ')
        print(CIZGI)

        # ── 1 ──
        nakit = CariHareket.query.filter(
            CariHareket.vade_tarihi.isnot(None),
            CariHareket.islem_tip.in_(NAKIT_TIPLERI)).order_by(
                CariHareket.hareket_tarihi).all()
        print(f'\n1 · NAKİT HAREKETİNDE VADE — {len(nakit)} kayıt')
        if not nakit:
            print('    ✓ yok')
        else:
            print('    Bu kayıtlarda vade anlamsız; para zaten el')
            print('    değiştirmiş. Yamadan sonra listeleri kirletmiyor,')
            print('    ama alan dolu duruyor.\n')
            _tip = {}
            for h in nakit:
                _tip[h.islem_tip] = _tip.get(h.islem_tip, 0) + 1
            for t, n in sorted(_tip.items(), key=lambda x: -x[1]):
                print(f'      {n:4d} × {t}')
            print()
            for h in nakit[:10]:
                print(f'      {h.id:16s} {str(h.hareket_tarihi):11s} '
                      f'vade={h.vade_tarihi} {h.islem_tip}')
            if len(nakit) > 10:
                print(f'      … {len(nakit) - 10} kayıt daha')

        # ── 2 ──
        vadesiz = Fatura.query.filter(
            Fatura.vade_tarihi.is_(None),
            Fatura.durum.in_(('Kesildi', 'Kismi Tahsil'))).order_by(
                Fatura.fatura_tarihi).all()
        print(f'\n2 · VADESİZ AÇIK FATURA — {len(vadesiz)} kayıt')
        if not vadesiz:
            print('    ✓ yok')
        else:
            print('    Bunlar VT1\'den önce hiç "gecikmiş" görünmüyordu.')
            print('    Yamadan sonra gecikme FATURA TARİHİNDEN sayılacak:\n')
            for f in vadesiz[:15]:
                _g = ((bugun - f.fatura_tarihi).days
                      if f.fatura_tarihi and f.fatura_tarihi < bugun else 0)
                print(f'      {(f.fatura_no or f.id):18s} '
                      f'{str(f.fatura_tarihi):11s} '
                      f'{(f.toplam or 0):>12,.2f} {f.doviz or "":4s} '
                      f'→ {_g} gün')
            if len(vadesiz) > 15:
                print(f'      … {len(vadesiz) - 15} kayıt daha')

        # ── 3 ──
        tanimsiz = Cari.query.filter(
            Cari.odeme_vadesi_gun.is_(None)).count()
        toplam_cari = Cari.query.count()
        print(f'\n3 · ÖDEME VADESİ TANIMSIZ CARİ — '
              f'{tanimsiz}/{toplam_cari}')
        if tanimsiz:
            print('    Kartta "Ödeme Vadesi (gün)" doluysa yeni faturanın')
            print('    vadesi kendiliğinden hesaplanır; boşsa her faturada')
            print('    elle girmek gerekir — girilmezse (2) oluşur.')

        # ── TEMİZLİK ──
        print('\n' + CIZGI)
        if not nakit:
            print('  Temizlenecek bir şey yok.')
            print(CIZGI)
            return 0
        if not TEMIZLE:
            print(f'  {len(nakit)} kaydın vadesi anlamsız.')
            print('  Silmek için:  venv/bin/python denetim_vade.py --temizle')
            print('  (yalnız vade alanı boşaltılır; tutara, kasaya,')
            print('   bakiyeye DOKUNULMAZ ve önce JSON yedek yazılır)')
            print(CIZGI)
            return 0

        yedek = os.path.join(KOK, f'vade_yedek_{bugun.isoformat()}.json')
        with open(yedek, 'w', encoding='utf-8') as fh:
            json.dump([{'id': h.id, 'islem_tip': h.islem_tip,
                        'vade_tarihi': h.vade_tarihi.isoformat()}
                       for h in nakit], fh, ensure_ascii=False, indent=1)
        print(f'  yedek yazıldı: {os.path.basename(yedek)}')

        for h in nakit:
            h.vade_tarihi = None
        db.session.commit()
        print(f'  ✓ {len(nakit)} kaydın vade alanı boşaltıldı')
        print(CIZGI)
        return 0


if __name__ == '__main__':
    sys.exit(ana())

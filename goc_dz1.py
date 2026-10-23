#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GÖÇ DZ1 — eski maliyet kayıtlarına grup kimliği
================================================

DZ1'den önce `grup_id` yalnız DAĞITILMIŞ maliyetlerde doluydu.
Tekil maliyetin net satırı ile KDV satırı arasında hiçbir bağ
yoktu; biri silinince öteki öksüz kalıyordu.

Bu betik geriye dönük o çiftleri bir gruba alır.

EŞLEŞTİRME ÖLÇÜTÜ — bilerek DAR tutuldu:
  · aynı `baglanti_tip` + `baglanti_id` (aynı stok/sipariş)
  · aynı `fatura_no` (ikisi de dolu)
  · biri 'Devreden KDV', öteki değil
  · ve o ölçütlere uyan TEK bir aday olmalı

Birden çok aday varsa DOKUNULMAZ ve raporda listelenir. Yanlış
iki kaydı birleştirmek, birini silerken ötekini de götürmek
demekti; şüphede kalmayı yeğliyorum.

Fatura no'su boş eski kayıtlar eşleştirilemez — onlar için
elimizde ayırt edici bir ip yok. Onlar da raporda görünür;
DZ1'den sonra girilen kayıtlarda bu sorun yok.

  python3 goc_dz1.py              # RAPOR — hiçbir şey yazılmaz
  python3 goc_dz1.py --uygula
"""
import os
import sys

UYGULA = '--uygula' in sys.argv
os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def _venv_uyar(hata):
    """Flask yoksa ne yapacagini SOYLE. Yamalar duz python3 ile
    calisiyor (yalniz dosya duzenliyorlar); veritabanina baglanan
    betikler venv istiyor. Ikisinin karismasi dogal."""
    print('=' * 70)
    print('  HATA: ' + str(hata))
    print('=' * 70)
    print('  Bu betik veritabanina baglaniyor, yani sanal ortam gerekli.')
    print('  Duz `python3` ile degil, soyle calistir:')
    print()
    print('      cd ~/milestoneERP-v2')
    print('      venv/bin/python ' + os.path.basename(__file__))
    print()
    print('  (Yamalar `python3` ile calisiyor cunku onlar yalniz')
    print('   dosya duzenliyor, Flask\'a dokunmuyorlar.)')
    print('=' * 70)
    sys.exit(1)


try:
    import flask_app as fa          # noqa: E402
    from models import db, Maliyet  # noqa: E402
except ModuleNotFoundError as _h:
    _venv_uyar(_h)


def ana():
    with fa.app.app_context():
        gruplanacak = []
        coklu = []
        ipsiz = []

        kdvler = Maliyet.query.filter(
            Maliyet.maliyet_tip == 'Devreden KDV',
            Maliyet.grup_id.is_(None)).all()

        for k in kdvler:
            if not (k.fatura_no and k.baglanti_id):
                ipsiz.append(k.id)
                continue
            adaylar = Maliyet.query.filter(
                Maliyet.fatura_no == k.fatura_no,
                Maliyet.baglanti_tip == k.baglanti_tip,
                Maliyet.baglanti_id == k.baglanti_id,
                Maliyet.maliyet_tip != 'Devreden KDV',
                Maliyet.id != k.id).all()
            if len(adaylar) == 1:
                gruplanacak.append((adaylar[0], k))
            elif len(adaylar) > 1:
                coklu.append((k.id, [a.id for a in adaylar]))
            else:
                ipsiz.append(k.id)

        print('=' * 68)
        print('  GÖÇ DZ1 — maliyet gruplama')
        print('=' * 68)
        print(f'  grup kimliği olmayan KDV satırı : {len(kdvler)}')
        print(f'  eşleşen çift (gruplanacak)      : {len(gruplanacak)}')
        print(f'  birden çok aday (DOKUNULMAZ)    : {len(coklu)}')
        print(f'  eşleştirilemeyen                : {len(ipsiz)}')

        if gruplanacak:
            print()
            print('  GRUPLANACAK:')
            for net, kdv in gruplanacak[:20]:
                print(f'    {net.id} ({net.maliyet_tip}) + {kdv.id} (KDV)'
                      f'  →  {net.baglanti_id}  fatura {net.fatura_no}')
            if len(gruplanacak) > 20:
                print(f'    … ve {len(gruplanacak) - 20} çift daha')

        if coklu:
            print()
            print('  BİRDEN ÇOK ADAY — elle bakman gerek:')
            for kdv_id, adaylar in coklu[:10]:
                print(f'    {kdv_id} → {adaylar}')

        if ipsiz:
            print()
            print('  EŞLEŞTİRİLEMEYEN (fatura no boş ya da karşılığı yok):')
            print(f'    {", ".join(ipsiz[:15])}'
                  + (f' … (+{len(ipsiz) - 15})' if len(ipsiz) > 15 else ''))
            print('    Bunlar öksüz kalabilir; silerken tek tek git.')

        if not UYGULA:
            print()
            print('=' * 68)
            print('  RAPOR — hiçbir şey yazılmadı. Uygulamak için:')
            print('      python3 goc_dz1.py --uygula')
            print('=' * 68)
            return 0

        if not gruplanacak:
            print()
            print('  Yapacak bir şey yok.')
            return 0

        import uuid
        for net, kdv in gruplanacak:
            grup = net.grup_id or ('MGR-' + uuid.uuid4().hex[:6].upper())
            net.grup_id = grup
            kdv.grup_id = grup
        db.session.commit()
        print()
        print('=' * 68)
        print(f'  ✓ {len(gruplanacak)} çift gruplandı.')
        print('  Tekrar çalıştırırsan "yapacak bir şey yok" demeli.')
        print('=' * 68)
        return 0


if __name__ == '__main__':
    sys.exit(ana())

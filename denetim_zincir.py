#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DENETİM — maliyet ↔ cari hareket ↔ stok maliyeti tutarlılığı
=============================================================

HİÇBİR ŞEYE DOKUNMAZ. Yalnız okur ve rapor eder.

DZ1 yamasını uygulamadan ÖNCE çalıştır: geçmiş silmelerden
kalan tutarsızlıklar varsa burada görünür. Yamadan sonra tekrar
çalıştırırsan neyin düzeldiğini karşılaştırabilirsin.

    cd ~/milestoneERP-v2
    python3 denetim_zincir.py

Baktığı yedi şey:

  1 ÖKSÜZ KDV      net satırı silinmiş Devreden KDV kayıtları
  2 KOPUK HAREKET  artık var olmayan maliyeti işaret eden cari
                   hareket
  3 TUTAR UYUŞMAZLIĞI  cari hareketin tutarı, karşılığı olan
                   maliyet grubunun toplamını tutmuyor
  4 EKSİK GRUP     dağıtım grubunun bazı satırları silinmiş
  5 HAYALET STOK   artık var olmayan stoğa bağlı maliyet
  6 BAYAT KÂR      satış kaydındaki maliyet, bugünkü maliyet
                   satırlarıyla uyuşmuyor
  7 PASİF SATIR    aktif=False maliyetler (hesaba KATILIYORLAR —
                   `_satis_kaydi_maliyet_guncelle` aktif süzgeci
                   uygulamıyor)
"""
import os
import sys

os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import flask_app as fa                                  # noqa: E402
from models import (db, Maliyet, CariHareket, SatisKaydi,  # noqa: E402
                    BlokStok, PlakaStok, EbatliStok)

KDV_TIPLERI = ('Devreden KDV', 'Iade KDV')
CIZGI = '=' * 70


def _baslik(n, ad):
    print()
    print(CIZGI)
    print(f'  {n} · {ad}')
    print(CIZGI)


def _liste(kayitlar, bicim, en_fazla=15):
    for k in kayitlar[:en_fazla]:
        print('    ' + bicim(k))
    if len(kayitlar) > en_fazla:
        print(f'    … ve {len(kayitlar) - en_fazla} tane daha')


def ana():
    with fa.app.app_context():
        sorunlu = 0
        maliyetler = Maliyet.query.all()
        hareketler = CariHareket.query.filter_by(baglanti_tip='maliyet').all()
        m_idler = {m.id for m in maliyetler}

        print(CIZGI)
        print('  ZİNCİR DENETİMİ — hiçbir şeye dokunulmaz')
        print(CIZGI)
        print(f'  maliyet satırı        : {len(maliyetler)}')
        print(f'  maliyete bağlı hareket: {len(hareketler)}')
        gruplu = [m for m in maliyetler if m.grup_id]
        print(f'  grup kimliği olan     : {len(gruplu)}'
              f'  (olmayan: {len(maliyetler) - len(gruplu)})')

        # ── 1 · ÖKSÜZ KDV ──
        _baslik(1, 'ÖKSÜZ KDV SATIRLARI')
        oksuz = []
        for m in maliyetler:
            if m.maliyet_tip not in KDV_TIPLERI:
                continue
            if m.grup_id:
                kardes = [x for x in maliyetler
                          if x.grup_id == m.grup_id
                          and x.maliyet_tip not in KDV_TIPLERI]
            else:
                kardes = [x for x in maliyetler
                          if x.id != m.id
                          and x.maliyet_tip not in KDV_TIPLERI
                          and x.baglanti_id == m.baglanti_id
                          and (x.fatura_no or '') == (m.fatura_no or '')
                          and m.fatura_no]
            if not kardes:
                oksuz.append(m)
        if oksuz:
            sorunlu += 1
            print(f'  ✗ {len(oksuz)} KDV satırının net karşılığı yok.')
            print('    Net satır silinmiş ama KDV satırı kalmış.')
            _liste(oksuz, lambda m: f'{m.id}  {m.baglanti_id}  '
                                    f'{m.tutar} {m.doviz}  '
                                    f'fatura={m.fatura_no or "—"}')
        else:
            print('  ✓ yok')

        # ── 2 · KOPUK HAREKET ──
        _baslik(2, 'ARTIK VAR OLMAYAN MALİYETİ İŞARET EDEN HAREKETLER')
        kopuk = [h for h in hareketler if h.baglanti_id not in m_idler]
        if kopuk:
            sorunlu += 1
            print(f'  ✗ {len(kopuk)} cari hareket, silinmiş bir maliyeti'
                  f' işaret ediyor.')
            print('    Tedarikçi borcu duruyor ama karşılığı yok.')
            _liste(kopuk, lambda h: f'{h.id}  {h.cari_unvan or h.cari_id}  '
                                    f'{h.alacak} {h.doviz}  '
                                    f'→ {h.baglanti_id} (YOK)')
        else:
            print('  ✓ yok')

        # ── 3 · TUTAR UYUŞMAZLIĞI ──
        _baslik(3, 'HAREKET TUTARI ↔ MALİYET GRUBU TOPLAMI')
        uyusmaz = []
        for h in hareketler:
            if h.baglanti_id not in m_idler:
                continue
            m = next(x for x in maliyetler if x.id == h.baglanti_id)
            if m.grup_id:
                grup = [x for x in maliyetler if x.grup_id == m.grup_id]
            else:
                grup = [m] + [x for x in maliyetler
                              if x.id != m.id and m.fatura_no
                              and (x.fatura_no or '') == m.fatura_no
                              and x.baglanti_id == m.baglanti_id]
            toplam = round(sum((x.tutar or 0) for x in grup), 2)
            borc = round(h.alacak or 0, 2)
            if abs(toplam - borc) > 0.01:
                uyusmaz.append((h, toplam, borc, len(grup)))
        if uyusmaz:
            sorunlu += 1
            print(f'  ✗ {len(uyusmaz)} harekette tutar tutmuyor.')
            _liste(uyusmaz,
                   lambda t: f'{t[0].id}  borç={t[2]} {t[0].doviz}  '
                             f'maliyet toplamı={t[1]}  '
                             f'({t[3]} satır)  fark={round(t[2]-t[1], 2)}')
        else:
            print('  ✓ hepsi tutuyor')

        # ── 4 · EKSİK GRUP ──
        _baslik(4, 'DAĞITIM GRUPLARI')
        gruplar = {}
        for m in gruplu:
            gruplar.setdefault(m.grup_id, []).append(m)
        coklu = {g: s for g, s in gruplar.items()
                 if len([x for x in s if x.maliyet_tip not in KDV_TIPLERI]) > 1}
        print(f'  dağıtım grubu sayısı: {len(coklu)}')
        if coklu:
            for g, s in list(coklu.items())[:10]:
                net = [x for x in s if x.maliyet_tip not in KDV_TIPLERI]
                stoklar = {x.baglanti_id for x in net}
                print(f'    {g}: {len(net)} satır, {len(stoklar)} stok, '
                      f'toplam {round(sum((x.tutar or 0) for x in net), 2)} '
                      f'{net[0].doviz}')

        # ── 5 · HAYALET STOK ──
        _baslik(5, 'ARTIK VAR OLMAYAN STOĞA BAĞLI MALİYET')
        stok_idler = set()
        for M in (BlokStok, PlakaStok, EbatliStok):
            stok_idler |= {s.id for s in M.query.all()}
        hayalet = [m for m in maliyetler
                   if m.baglanti_tip == 'stok' and m.baglanti_id
                   and m.baglanti_id not in stok_idler]
        if hayalet:
            sorunlu += 1
            print(f'  ✗ {len(hayalet)} maliyet, silinmiş bir stoğa bağlı.')
            _liste(hayalet, lambda m: f'{m.id}  {m.maliyet_tip}  '
                                      f'→ {m.baglanti_id} (YOK)  '
                                      f'{m.tutar} {m.doviz}')
        else:
            print('  ✓ yok')

        # ── 6 · BAYAT KÂR ──
        _baslik(6, 'SATIŞ KAYDINDAKİ MALİYET GÜNCEL Mİ')
        bayat = []
        for sk in SatisKaydi.query.all():
            if not sk.stok_id:
                continue
            stok_maliyet = sum(
                (m.usd_karsilik or 0) for m in maliyetler
                if m.baglanti_id == sk.stok_id
                and m.maliyet_tip not in KDV_TIPLERI)
            kayitli = sk.maliyet_usd or 0
            # Alış bedelini yeniden hesaplamıyoruz (kur/ölçü işin içinde);
            # yalnız MALİYET SATIRLARI tarafındaki farkı arıyoruz.
            # Kayıtlı maliyet, satır toplamından KÜÇÜKSE eksik,
            # satır toplamı + makul bir alış bedelinden büyükse fazla.
            if kayitli + 0.01 < stok_maliyet:
                bayat.append((sk, kayitli, stok_maliyet))
        if bayat:
            sorunlu += 1
            print(f'  ✗ {len(bayat)} satış kaydında maliyet, maliyet'
                  f' satırlarının toplamından DÜŞÜK.')
            print('    (alış bedeli hariç bile düşükse kesin bayattır)')
            _liste(bayat, lambda t: f'{t[0].id}  stok={t[0].stok_id}  '
                                    f'kayıtlı={round(t[1], 2)}  '
                                    f'satırlar={round(t[2], 2)}')
        else:
            print('  ✓ hepsi satır toplamını kapsıyor')

        # ── 7 · PASİF SATIR ──
        _baslik(7, 'PASİF (aktif=False) MALİYET SATIRLARI')
        pasif = [m for m in maliyetler if m.aktif is False]
        if pasif:
            sorunlu += 1
            print(f'  ✗ {len(pasif)} pasif satır var ve bunlar stok'
                  f' maliyetine KATILIYOR.')
            print('    `_satis_kaydi_maliyet_guncelle` aktif süzgeci')
            print('    uygulamıyor; pasif sayılan gider kâra giriyor.')
            _liste(pasif, lambda m: f'{m.id}  {m.maliyet_tip}  '
                                    f'{m.baglanti_id}  {m.tutar} {m.doviz}')
        else:
            print('  ✓ yok')

        print()
        print(CIZGI)
        if sorunlu:
            print(f'  {sorunlu} başlıkta tutarsızlık var — çıktıyı gönder.')
            print('  Hiçbir şeye DOKUNULMADI.')
        else:
            print('  ✓ Yedi başlıkta da tutarsızlık yok.')
        print(CIZGI)
        return 0


if __name__ == '__main__':
    sys.exit(ana())

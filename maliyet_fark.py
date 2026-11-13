#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MALİYET FARKI — SALT OKUNUR
====================================================================

GD1 ile alış bedeli FATURA GÜNÜNÜN kuruyla dolara çevriliyor.
Kesilmiş blokların ürün maliyetleri ve satılmış ürünlerin kâr
kayıtları ise hesaplandıkları günün kuralıyla yazılı duruyor.

Bu betik "Maliyetleri yeniden hesapla" düğmesine basılırsa NEYİN
DEĞİŞECEĞİNİ döker: ürün ürün eski/yeni birim maliyet, satış satış
eski/yeni maliyet ve kâr. Programın kendi ucunu ÖNİZLEME kipinde
çağırır; uç hesaplar, farkı çıkarır ve GERİ ALIR.

NE YAPMAZ: HİÇBİR ŞEY YAZMAZ. Rakamlar doğru görünüyorsa değişikliği
Depo → Maliyetler sayfasındaki "Maliyetleri yeniden hesapla"
düğmesiyle (yalnız yönetici) sen yaparsın.

Kullanım (PROJE DİZİNİNDE, yama_gd1 uygulandıktan sonra):
    cd ~/milestoneERP-v2 && venv/bin/python maliyet_fark.py
"""
import os
import sys

KOK = os.path.dirname(os.path.abspath(__file__)) or '.'


def _p(v):
    try:
        return f'{float(v or 0):,.2f}'
    except (TypeError, ValueError):
        return '0.00'


def _s(v, n):
    v = '' if v is None else str(v)
    return (v[:n - 1] + '…') if len(v) > n else v.ljust(n)


def main():
    os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
    if KOK not in sys.path:
        sys.path.insert(0, KOK)
    try:
        os.chdir(KOK)
        import flask_app as fa
        from models import Kullanici
    except Exception as e:  # noqa: BLE001
        print(f'HATA: program içe aktarılamadı: {e}')
        print('  Bu betik PROJE DİZİNİNDE durmalı ve venv/bin/python ile '
              'çalıştırılmalı.')
        return 1
    try:
        from models import Firma
    except Exception:  # noqa: BLE001
        Firma = None

    with fa.app.app_context():
        yonetici = Kullanici.query.filter_by(rol='ADMIN').order_by(
            Kullanici.id).first()
        if yonetici is None:
            print('HATA: ADMIN rolünde kullanıcı bulunamadı.')
            return 1
        ad = yonetici.ad
        firmalar = [None]
        if Firma is not None:
            firmalar = [f.id for f in Firma.query.filter_by(
                aktif=True).order_by(Firma.id).all()] or [None]

    print()
    print('=' * 100)
    print('  MALİYET FARKI · salt okunur · "Maliyetleri yeniden hesapla" '
          'neyi değiştirir')
    print('=' * 100)

    toplam_satis = toplam_urun = 0
    for fid in firmalar:
        c = fa.app.test_client()
        with c.session_transaction() as o:
            o['kullanici'] = ad
            o['rol'] = 'ADMIN'
            o['_csrf'] = 'mf'
            o['firma_id'] = fid
        r = c.post('/api/maliyet/yeniden_hesapla',
                   headers={'X-CSRF-Token': 'mf'}, json={'onizleme': True})
        if r.status_code == 404:
            print('HATA: uç bulunamadı — yama_gd1.py uygulanmamış.')
            return 1
        if r.status_code != 200:
            print(f'HATA: uç {r.status_code} döndü: '
                  f'{(r.get_json(silent=True) or {})}')
            return 1
        d = r.get_json() or {}
        z = d.get('ozet') or {}
        if len(firmalar) > 1:
            print(f'\n── Firma {fid} ' + '─' * 86)
        print(f'\n  Taranan (dövizi USD olmayan) stok: {z.get("taranan_stok", 0)}')

        urunler = d.get('urunler') or []
        print(f'\n  ÜRÜN BİRİM MALİYETİ DEĞİŞECEKLER: {len(urunler)}')
        if urunler:
            print('  ' + _s('STOK', 26) + _s('TİP', 8) + _s('NO', 16)
                  + _s('CİNS', 22) + 'ESKİ'.rjust(12) + 'YENİ'.rjust(12)
                  + 'FARK'.rjust(12))
            for u in urunler:
                print('  ' + _s(u.get('id'), 26) + _s(u.get('tip'), 8)
                      + _s(u.get('no'), 16) + _s(u.get('cins'), 22)
                      + _p(u.get('eski')).rjust(12) + _p(u.get('yeni')).rjust(12)
                      + f'{float(u.get("yeni") or 0) - float(u.get("eski") or 0):+,.2f}'.rjust(12))

        satislar = d.get('satislar') or []
        print(f'\n  SATIŞ KAYDI DEĞİŞECEKLER: {len(satislar)}')
        if satislar:
            print('  ' + _s('TARİH', 12) + _s('NO', 16) + _s('MÜŞTERİ', 26)
                  + 'ESKİ MAL.'.rjust(12) + 'YENİ MAL.'.rjust(12)
                  + 'ESKİ KÂR'.rjust(12) + 'YENİ KÂR'.rjust(12))
            for s in satislar:
                print('  ' + _s(s.get('tarih'), 12)
                      + _s(s.get('no') or s.get('stok_id'), 16)
                      + _s(s.get('musteri'), 26)
                      + _p(s.get('eski_maliyet')).rjust(12)
                      + _p(s.get('yeni_maliyet')).rjust(12)
                      + _p(s.get('eski_kar')).rjust(12)
                      + _p(s.get('yeni_kar')).rjust(12))
            print(f'\n  Satışların toplam maliyeti '
                  f'{float(z.get("maliyet_farki_usd") or 0):+,.2f} USD, '
                  f'toplam kârı {float(z.get("kar_farki_usd") or 0):+,.2f} '
                  f'USD değişir.')
        toplam_satis += len(satislar)
        toplam_urun += len(urunler)

    print('\n' + '=' * 100)
    if toplam_satis or toplam_urun:
        print(f'  {toplam_urun} ürün ve {toplam_satis} satış kaydı değişecek. '
              f'Rakamlar doğruysa:')
        print('  Depo → Maliyetler → "Maliyetleri yeniden hesapla" (yönetici).')
    else:
        print('  ✓ Değişecek kayıt yok; her şey güncel kuralla hesaplanmış.')
    print('  Hiçbir şey değiştirilmedi.')
    print('=' * 100)
    return 0


if __name__ == '__main__':
    sys.exit(main())

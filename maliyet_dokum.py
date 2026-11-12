#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MALİYET DÖKÜMÜ — SALT OKUNUR

Bir stoğun "giydirilmiş maliyeti" hangi satırlardan oluşuyor?
Stok listesindeki rakamı KALEM KALEM açar: her maliyet satırının
tutarı, dolar karşılığı ve o karşılığın ima ettiği kur. Yanlış kurla
çevrilmiş ya da iki kez girilmiş satır burada göze batar.

Hiçbir şey yazmaz.

Kullanım (proje dizininde):
    venv/bin/python maliyet_dokum.py K6461 K6462 K6463 K6464
"""
import io
import os
import sys

KOK = os.path.dirname(os.path.abspath(__file__)) or '.'
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(KOK, '.env'))
except Exception:
    yol = os.path.join(KOK, '.env')
    if os.path.exists(yol):
        for satir in io.open(yol, encoding='utf-8'):
            satir = satir.strip()
            if not satir or satir.startswith('#') or '=' not in satir:
                continue
            ad, _, deger = satir.partition('=')
            os.environ.setdefault(ad.strip(), deger.strip().strip('"\''))
URL = os.environ.get('DATABASE_URL')
if not URL or len(sys.argv) < 2:
    print('Kullanım: venv/bin/python maliyet_dokum.py <blok no> [<blok no> …]')
    sys.exit(1)
from sqlalchemy import create_engine, text

motor = create_engine(URL)
KDV = ('Devreden KDV', 'Iade KDV')


def f(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def g(v, n):
    v = '' if v is None else str(v)
    return (v[:n - 1] + '…') if len(v) > n else v.ljust(n)


def kur_bul(b, doviz, gun):
    """O günün, yoksa ondan önceki son günün kuru."""
    r = b.execute(text(
        "SELECT tarih, alis, satis, efektif FROM doviz_kur "
        "WHERE doviz = :d AND tarih <= :g ORDER BY tarih DESC LIMIT 1"),
        {'d': doviz, 'g': gun}).mappings().first()
    return r


with motor.connect() as b:
    for ad in sys.argv[1:]:
        st = b.execute(text(
            "SELECT id, blok_no, cins, uretici, tonaj, hacim_m3, alis_fiyati, "
            "alis_fiyat_birim, doviz, matrah, kdv_tutar, durum, alis_tarihi "
            "FROM blok_stok WHERE blok_no = :a OR id = :a OR id LIKE :l"),
            {'a': ad, 'l': '%' + ad}).mappings().all()
        if not st:
            print(f'\n✗ {ad}: blok bulunamadı (yalnız bloklara bakıyorum)')
            continue
        for s in st:
            print('\n' + '=' * 108)
            print(f'  {s["id"]} · {s["cins"]} · {s["uretici"]} · {s["durum"]}')
            print(f'  {f(s["tonaj"]):g} ton · {f(s["hacim_m3"]):g} m³ · alış '
                  f'{f(s["alis_fiyati"]):g} {s["doviz"]}/{s["alis_fiyat_birim"]} '
                  f'· matrah {f(s["matrah"]):,.2f} {s["doviz"]} · alış tarihi '
                  f'{s["alis_tarihi"]}')
            print('=' * 108)
            ml = b.execute(text(
                "SELECT id, maliyet_tarihi, maliyet_tip, tutar, doviz, "
                "usd_karsilik, fatura_no, grup_id, aktif "
                "FROM maliyetler WHERE baglanti_id = :i "
                "ORDER BY maliyet_tarihi, id"), {'i': s['id']}).mappings().all()
            print('  ' + g('TARİH', 12) + g('TİP', 26) + g('FATURA', 20)
                  + g('TUTAR', 20) + g('USD KARŞ.', 13) + g('İMA EDİLEN KUR', 30)
                  + 'SAYILIR MI')
            ek = 0.0
            for m in ml:
                t, u, dv = f(m['tutar']), f(m['usd_karsilik']), (m['doviz'] or '')
                sayilir = bool(m['aktif']) and m['maliyet_tip'] not in KDV
                if sayilir:
                    ek += u
                ima = ''
                if dv != 'USD' and u:
                    if dv == 'TRY':
                        ima = f'1 USD = {t / u:,.4f} TRY'
                    else:
                        ima = f'1 {dv} = {u / t:,.4f} USD'
                    k = kur_bul(b, 'USD', str(m['maliyet_tarihi'])[:10])
                    kd = (kur_bul(b, dv, str(m['maliyet_tarihi'])[:10])
                          if dv != 'TRY' else None)
                    if k:
                        if dv == 'TRY':
                            beklenen = f(k['alis'])
                            sapma = abs(t / u - beklenen) / beklenen if beklenen else 0
                        elif kd:
                            beklenen = f(kd['alis']) / f(k['alis']) if f(k['alis']) else 0
                            sapma = abs(u / t - beklenen) / beklenen if beklenen else 0
                        else:
                            beklenen, sapma = 0, 0
                        if sapma > 0.03:
                            ima += f'  ⚠ arşiv≈{beklenen:,.4f}'
                elif dv != 'USD' and not u:
                    ima = '⚠ dolar karşılığı BOŞ'
                neden = ('evet' if sayilir else
                         'hayır (KDV)' if m['maliyet_tip'] in KDV else
                         'hayır (iptal)')
                print('  ' + g(str(m['maliyet_tarihi'])[:10], 12)
                      + g(m['maliyet_tip'], 26) + g(m['fatura_no'] or '—', 20)
                      + g(f'{t:,.2f} {dv}', 20) + g(f'{u:,.2f}', 13)
                      + g(ima, 30) + neden)
            ton = f(s['tonaj'])
            print('  ' + '-' * 104)
            print(f'  EK MALİYET (sayılanlar): {ek:,.2f} USD'
                  + (f'  →  {ek / ton:,.2f} USD/ton' if ton else ''))
            print('  (Listedeki "giydirilmiş maliyet" = alış bedelinin BUGÜNKÜ '
                  'kurla dolar karşılığı + bu ek maliyet, tona bölünmüş.)')
print('\nHiçbir şey değiştirilmedi.')

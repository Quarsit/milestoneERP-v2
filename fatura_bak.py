#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FATURA BAK — SALT OKUNUR

Bir fatura numarasına bağlı HER ŞEYİ döker: cari hareketler, stoklar,
maliyet satırları. Hiçbir şey yazmaz.

Kullanım (proje dizininde):
    venv/bin/python fatura_bak.py ALB20260905
    venv/bin/python fatura_bak.py "Beklenen Fatura 1"
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
    print('Kullanım: venv/bin/python fatura_bak.py <fatura no>   '
          '(proje dizininde, .env yanında)')
    sys.exit(1)
from sqlalchemy import create_engine, text

FNO = sys.argv[1]
motor = create_engine(URL)


def g(v, n):
    v = '' if v is None else str(v)
    return (v[:n - 1] + '…') if len(v) > n else v.ljust(n)


def p(v):
    return f'{float(v or 0):>12,.2f}'


with motor.connect() as b:
    har = b.execute(text(
        "SELECT id, hareket_tarihi, cari_id, cari_unvan, islem_tip, borc, "
        "alacak, doviz, kur_uygulanan, kalem_sayisi, baglanti_tip, "
        "baglanti_id, evrak_no, kaynak, aciklama FROM cari_hareket "
        "WHERE baglanti_id = :f OR evrak_no = :f "
        "ORDER BY hareket_tarihi, id"), {'f': FNO}).mappings().all()
    stoklar = []
    for tablo in ('blok_stok', 'plaka_stok', 'ebatli_stok'):
        for r in b.execute(text(
                f"SELECT id, uretici, cari_id, alis_tarihi, giris_tarihi, "
                f"matrah, kdv_tutar, doviz, durum FROM {tablo} "
                f"WHERE fatura_no = :f ORDER BY id"), {'f': FNO}).mappings():
            stoklar.append((tablo, r))
    mal = b.execute(text(
        "SELECT id, maliyet_tarihi, maliyet_tip, baglanti_id, tutar, doviz, "
        "grup_id, aktif FROM maliyetler WHERE fatura_no = :f ORDER BY id"),
        {'f': FNO}).mappings().all()

print('=' * 100)
print(f'  FATURA: {FNO} · salt okunur')
print('=' * 100)
print(f'\nCARİ HAREKETLER: {len(har)}')
net = 0.0
for h in har:
    net += float(h['alacak'] or 0) - float(h['borc'] or 0)
    print(f'  {h["hareket_tarihi"]}  {g(h["id"], 20)} {g(h["cari_unvan"], 26)} '
          f'{g(h["islem_tip"], 22)} borç{p(h["borc"])} alacak{p(h["alacak"])} '
          f'{h["doviz"] or ""}  kalem={h["kalem_sayisi"]}')
    print(f'              bağ={h["baglanti_tip"]}/{h["baglanti_id"]} '
          f'evrak={h["evrak_no"]} kaynak={h["kaynak"]} cari_id={h["cari_id"]}')
    if h['aciklama']:
        print(f'              {str(h["aciklama"])[:86]}')
print(f'  NET (alacak − borç): {net:,.2f}')
print(f'\nSTOKLAR: {len(stoklar)}')
top = 0.0
for tablo, r in stoklar:
    top += float(r['matrah'] or 0) + float(r['kdv_tutar'] or 0)
    print(f'  {g(tablo, 12)} {g(r["id"], 24)} alış {r["alis_tarihi"]} giriş '
          f'{r["giris_tarihi"]} matrah{p(r["matrah"])} KDV{p(r["kdv_tutar"])} '
          f'{r["doviz"] or ""} {g(r["durum"], 10)} cari_id={r["cari_id"]} '
          f'{g(r["uretici"], 24)}')
print(f'  TOPLAM (matrah + KDV): {top:,.2f}')
print(f'\nMALİYET SATIRLARI: {len(mal)}')
for m in mal:
    print(f'  {m["maliyet_tarihi"]}  {g(m["id"], 20)} {g(m["maliyet_tip"], 24)} '
          f'{g(m["baglanti_id"], 22)} {p(m["tutar"])} {m["doviz"] or ""} '
          f'grup={m["grup_id"]} aktif={m["aktif"]}')
print('\nHiçbir şey değiştirilmedi.')

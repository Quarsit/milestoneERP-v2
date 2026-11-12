#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TARİH TARAMASI — SALT OKUNUR
====================================================================

NE ARAR: Belirli bir güne (varsayılan 06.11.2026) yazılmış maliyet,
stok alışı ve tedarikçi cari hareketlerini. Tarih kutusu yokken
girilen kayıtlar giriş gününe düşmüştü; bu betik o günün dökümünü
verir ki toplu düzeltmeden ÖNCE neyin taşınacağını göresin.

Dört bölüm:
  1 · O güne yazılmış MALİYET satırları (cari, KDV, grup)
  2 · Alış tarihi o gün olan STOKLAR
  3 · O güne yazılmış tedarikçi CARİ HAREKETLERİ
        BAĞSIZ = hiçbir maliyet satırına bağlı değil; toplu araç
        bunları BULAMAZ (eski "Bloğa Dağıt" kayıtları)
  4 · UYUMSUZ: maliyet tarihi ile cari hareket tarihi FARKLI
        (bütün tarihlerde aranır)

NE YAPMAZ: HİÇBİR ŞEY YAZMAZ, SİLMEZ, DEĞİŞTİRMEZ. Yalnız okur.

Kullanım (PROJE DİZİNİNDE — `.env`i burada arıyor):
    cp tarih_tara.py ~/milestoneERP-v2/
    cd ~/milestoneERP-v2 && venv/bin/python tarih_tara.py
    venv/bin/python tarih_tara.py 2026-11-07      # başka bir gün
"""
import io
import os
import sys
from datetime import datetime

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
if not URL:
    print('✗ DATABASE_URL okunamadı.')
    print('  Bu betik .env dosyasını KENDİ BULUNDUĞU klasörde arıyor;')
    print('  proje dizinine kopyalayıp oradan çalıştır.')
    sys.exit(1)

GUN = '2026-11-06'
for a in sys.argv[1:]:
    try:
        GUN = datetime.strptime(a, '%Y-%m-%d').date().isoformat()
    except ValueError:
        print(f'✗ Tarih YYYY-AA-GG biçiminde olmalı: {a}')
        sys.exit(1)

try:
    from sqlalchemy import create_engine, text
except ImportError:
    print('✗ sqlalchemy bulunamadı — venv/bin/python ile çalıştır.')
    sys.exit(1)

motor = create_engine(URL)
KDV_TIPLERI = ('Devreden KDV', 'Iade KDV')


def s(v, n):
    v = '' if v is None else str(v)
    return (v[:n - 1] + '…') if len(v) > n else v.ljust(n)


def para(v, dv):
    return f'{float(v or 0):>12,.2f} {dv or ""}'


with motor.connect() as b:
    mal = b.execute(text(
        "SELECT id, maliyet_tip, baglanti_tip, baglanti_id, tutar, doviz, "
        "fatura_no, grup_id, maliyet_tarihi FROM maliyetler "
        "WHERE aktif = :t ORDER BY fatura_no, id"), {'t': True}).mappings().all()
    har = b.execute(text(
        "SELECT id, cari_id, cari_unvan, baglanti_tip, baglanti_id, evrak_no, "
        "alacak, doviz, hareket_tarihi, kur_uygulanan FROM cari_hareket "
        "WHERE baglanti_tip IN ('maliyet', 'stok_fatura') "
        "ORDER BY hareket_tarihi, id")).mappings().all()
    stoklar = []
    for tablo, ad in (('blok_stok', 'BLOK'), ('plaka_stok', 'PLAKA'),
                      ('ebatli_stok', 'EBATLI')):
        for r in b.execute(text(
                f"SELECT id, uretici, fatura_no, alis_tarihi FROM {tablo} "
                f"ORDER BY fatura_no, id")).mappings().all():
            stoklar.append((ad, r))

gun = lambda v: str(v or '')[:10]
mal_id = {m['id']: m for m in mal}
grup = {}
for m in mal:
    grup.setdefault(m['grup_id'] or m['id'], []).append(m)
# maliyet → cari hareket (doğrudan ya da grubu üzerinden)
h_maliyet = {}
for h in har:
    if h['baglanti_tip'] == 'maliyet' and h['baglanti_id'] in mal_id:
        m = mal_id[h['baglanti_id']]
        h_maliyet[m['grup_id'] or m['id']] = h

print('=' * 78)
print(f'  TARİH TARAMASI · {GUN} · salt okunur')
print('=' * 78)

# ── 1 · MALİYETLER ────────────────────────────────────────────────
o_gun = [m for m in mal if gun(m['maliyet_tarihi']) == GUN]
print(f'\n1 · {GUN} TARİHLİ MALİYET SATIRLARI: {len(o_gun)}')
if o_gun:
    print('   ' + s('TİP', 26) + s('BAĞLANTI', 18) + s('FATURA', 16)
          + s('TUTAR', 18) + s('CARİ', 24) + 'KDV')
kdvli_fatura, kdvsiz_fatura = set(), set()
for m in o_gun:
    gk = m['grup_id'] or m['id']
    kdvli = any(x['maliyet_tip'] in KDV_TIPLERI for x in grup[gk])
    (kdvli_fatura if kdvli else kdvsiz_fatura).add(gk)
    h = h_maliyet.get(gk)
    print('   ' + s(m['maliyet_tip'], 26) + s(m['baglanti_id'], 18)
          + s(m['fatura_no'] or '—', 16) + s(para(m['tutar'], m['doviz']), 18)
          + s((h or {}).get('cari_unvan')
              or ('(stok alış faturası)'
                  if m['maliyet_tip'] in KDV_TIPLERI and not m['grup_id']
                  else '— carisiz —'), 24)
          + ('KDV\'li' if kdvli else ''))
if o_gun:
    print(f'   → {len(kdvsiz_fatura)} fatura KDV\'siz (sorulmadan taşınır), '
          f'{len(kdvli_fatura)} fatura KDV\'li (kapalı dönem sorusu gelir)')

# ── 2 · STOKLAR ───────────────────────────────────────────────────
o_stok = [(ad, r) for ad, r in stoklar if gun(r['alis_tarihi']) == GUN]
print(f'\n2 · ALIŞ TARİHİ {GUN} OLAN STOKLAR: {len(o_stok)}')
for ad, r in o_stok:
    print('   ' + s(ad, 8) + s(r['id'], 22) + s(r['fatura_no'] or '—', 18)
          + s(r['uretici'], 30))
if o_stok:
    print('   → Maliyetler sayfasında bunların "Alış Bedeli" satırını '
          'seçersen fatura bütün taşınır.')

# ── 3 · CARİ HAREKETLER ───────────────────────────────────────────
o_har = [h for h in har if gun(h['hareket_tarihi']) == GUN]
print(f'\n3 · {GUN} TARİHLİ TEDARİKÇİ CARİ HAREKETLERİ: {len(o_har)}')
bagsiz = 0
for h in o_har:
    if h['baglanti_tip'] == 'stok_fatura':
        not_ = 'stok alış faturası'
    elif h['baglanti_id'] in mal_id:
        not_ = 'maliyet ' + str(h['baglanti_id'])
    else:
        not_ = 'BAĞSIZ — toplu araç bunu bulamaz'
        bagsiz += 1
    print('   ' + s(h['cari_unvan'], 26) + s(h['evrak_no'] or '—', 16)
          + s(para(h['alacak'], h['doviz']), 18) + not_)

# ── 4 · UYUMSUZ ───────────────────────────────────────────────────
uyumsuz = []
for gk, h in h_maliyet.items():
    ana = grup[gk][0]
    if gun(ana['maliyet_tarihi']) != gun(h['hareket_tarihi']):
        uyumsuz.append((ana, h))
print(f'\n4 · MALİYET TARİHİ ≠ CARİ HAREKET TARİHİ (bütün tarihler): '
      f'{len(uyumsuz)}')
for m, h in uyumsuz:
    print('   ' + s(m['maliyet_tip'], 26) + s(m['fatura_no'] or '—', 16)
          + f'maliyet {gun(m["maliyet_tarihi"])} · hareket '
            f'{gun(h["hareket_tarihi"])} · ' + s(h['cari_unvan'], 24))

print('\n' + '=' * 78)
if not (o_gun or o_stok or o_har):
    print(f'  ✓ {GUN} tarihine yazılmış kayıt yok.')
else:
    print('  DÜZELTME: Depo → Maliyetler → tarih aralığı '
          f'{GUN} – {GUN} → hepsini seç')
    print('            → Yeni tarih → "Seçilenlerin tarihini değiştir"')
if bagsiz or uyumsuz:
    print(f'  ⚠ {bagsiz} BAĞSIZ hareket, {len(uyumsuz)} UYUMSUZ kayıt var: '
          'toplu araç bunları')
    print('    kendiliğinden düzeltmez. Bu çıktıyı bana gönder.')
print('  Hiçbir şey değiştirilmedi.')
print('=' * 78)

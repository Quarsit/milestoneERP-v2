#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — ÜRETİM BLOK NO SADELEŞTİRME  ·  B3
#
#  ÖNKOŞUL: yama_b3.py uygulanmış olmalı. (Şema değişikliği YOK; bu
#  betik yalnızca metin düzeltiyor, servisin yeniden başlamasını
#  beklemek zorunda değil.)
#
#  ── SORUN ──
#    Kesim kaydederken üretim blok no boş bırakılırsa sunucu şunu
#    üretiyordu:
#
#        uretim_blok_no = blok_no + '-U' + kesim_id[-4:]
#
#    Kesim numarası KSM-K6461-01 biçiminde. Son DÖRT karakter
#    '1-01' — yani K6461'in son hanesi de dilime giriyor:
#
#        K6461  →  K6461-U1-01        (beklenen: K6461-U01)
#
#    Plakanın kodu bu no'dan türediği için depoda
#    K6461-U1-01#1 diye okunuyordu.
#
#  ── YAMA NE YAPTI ──
#    Yeni kesimlerde üretim no artık ORİJİNAL BLOK NO. Ama ESKİ
#    kayıtlar düzelmez: yamadan sonra onlar yeni biçimle birleşip
#    K6461-U1-01-01 diye görünür. Bu betik onları kısaltıyor.
#
#  ── ÖLÇÜT: TAHMİN YOK, KAYIT VAR ──
#    Bir değer YALNIZCA üç şartın hepsi tutarsa düzeltilir:
#
#      1) Kalıba uyuyor:  <kök>-U<rakam>-<iki hane>
#         (yalnız sunucunun ürettiği kazanın şekli. Senin elle
#          yazdığın ya da "öner" düğmesiyle gelen -U261 gibi
#          değerler BU KALIBA UYMAZ ve dokunulmaz.)
#      2) O değere sahip bir KESİM var ve o kesimin kaynak_no'su
#         tam olarak <kök>'e eşit.
#      3) Kısaltılmış hâli, aynı blokta BAŞKA bir plakayla
#         çakışmıyor (blok_no + slab_no çifti serbest).
#
#    Üçünden biri tutmazsa o kayıt ATLANIR ve raporda neden
#    atlandığı yazar.
#
#  ── NE DEĞİŞİR ──
#    plaka_stok.blok_no      ve      kesim.uretim_blok_no
#
#  ── NE DEĞİŞMEZ ──
#    · Kimlikler (plaka_stok.id = PLK-K6461-U1-01-01) OLDUĞU GİBİ
#      KALIR. Kimliğe sipariş kalemleri, proforma satırları, kesim
#      detayları ve denetim kayıtları bağlı; onları yeniden
#      yazmak, görünen bir kodu düzeltmek için veri zincirini
#      kesmek olurdu. Kimlik iç numara; depoda okuduğun kod
#      blok_no'dan türüyor ve o düzeliyor.
#    · Hiçbir satır silinmez, tutarlar değişmez, slab numaraları
#      değişmez.
#
#  ── GÜVENLİK ──
#    • --uygula OLMADAN HİÇBİR ŞEY DEĞİŞMEZ; yalnızca rapor verir.
#    • PostgreSQL'de önce pg_dump yedeği alır; yedek başarısızsa İPTAL.
#    • Tek transaction.
#    • Tekrar çalıştırılabilir: ikinci koşu "yapılacak iş yok" der.
#
#  KULLANIM (proje dizininde):
#      venv/bin/python goc_b3.py             # RAPOR
#      venv/bin/python goc_b3.py --uygula    # UYGULAR
# ══════════════════════════════════════════════════════════════════════
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

load_dotenv()

UYGULA = '--uygula' in sys.argv
VT_URL = os.environ.get('DATABASE_URL')

if not VT_URL:
    print('HATA: DATABASE_URL bulunamadı (.env okunamadı).')
    print('  Adres olmadan yanlış veritabanına bağlanabilirdim.')
    sys.exit(1)

motor = create_engine(VT_URL)
kaynak_url = urlparse(VT_URL)
pg = motor.dialect.name in ('postgresql', 'postgres')
denetci = inspect(motor)

print('═' * 70)
print('  MILESTONE ERP — ÜRETİM BLOK NO SADELEŞTİRME  ·  B3')
print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (hiçbir şey değişmez)')
print('═' * 70)
print(f" Veritabanı : {kaynak_url.path.lstrip('/')} @ {kaynak_url.hostname or 'yerel'}")
print(f' Sürücü     : {motor.dialect.name}')
print()

# Sunucunun ürettiği kazanın ŞEKLİ: kök + '-U' + <rakam> + '-' + <iki hane>
KALIP = re.compile(r'^(?P<kok>.+)-U\d-\d{2}$')

TABLOLAR = ('plaka_stok', 'kesim')
tablolar = set(denetci.get_table_names())
eksik = [t for t in TABLOLAR if t not in tablolar]
if eksik:
    print(f" ✗ Şu tablo(lar) yok: {', '.join(eksik)}")
    print('   Yanlış veritabanına bağlanmış olabilirim. Duruyorum.')
    sys.exit(1)


def yedek_al():
    if not pg:
        print(' ⚠ PostgreSQL değil — otomatik yedek atlandı.')
        return True
    hedef = Path.home() / 'yedekler'
    hedef.mkdir(exist_ok=True)
    dosya = hedef / f'b3-oncesi-{datetime.now():%Y%m%d_%H%M%S}.dump'
    try:
        ortam = dict(os.environ)
        if kaynak_url.password:
            ortam['PGPASSWORD'] = kaynak_url.password
        s = subprocess.run(
            ['pg_dump', '-Fc', '-f', str(dosya),
             '-h', kaynak_url.hostname or 'localhost',
             '-p', str(kaynak_url.port or 5432),
             '-U', kaynak_url.username or 'postgres',
             kaynak_url.path.lstrip('/')],
            env=ortam, capture_output=True, text=True, timeout=600)
        if (s.returncode != 0 or not dosya.exists()
                or dosya.stat().st_size < 1024):
            print(' ✗ Yedek ALINAMADI — göç İPTAL edildi.')
            print(f'   {(s.stderr or "").strip()[:200]}')
            return False
        print(f' ✓ {dosya}  ({dosya.stat().st_size / 1024:.0f} KB)')
        return True
    except FileNotFoundError:
        print(' ✗ pg_dump bulunamadı — göç İPTAL edildi.')
        return False
    except subprocess.TimeoutExpired:
        print(' ✗ Yedek zaman aşımına uğradı — göç İPTAL edildi.')
        return False


# ══════════════════════════════════════════════════════════════════════
#  1 · ADAYLARI BUL
# ══════════════════════════════════════════════════════════════════════
with motor.connect() as b:
    kesimler = {}
    for kid, ubn, kno in b.execute(text(
            'SELECT id, uretim_blok_no, kaynak_no FROM kesim '
            'WHERE uretim_blok_no IS NOT NULL')):
        kesimler.setdefault(str(ubn), []).append((kid, kno))

    plakalar = [(pid, str(bn or ''), sn) for pid, bn, sn in b.execute(text(
        'SELECT id, blok_no, slab_no FROM plaka_stok '
        'WHERE blok_no IS NOT NULL'))]

# Çakışma denetimi için mevcut (blok_no, slab_no) çiftleri
mevcut_cift = {(bn.upper(), sn) for _, bn, sn in plakalar}

duzeltilecek = {}      # eski_no -> yeni_no
atlanan = []           # (eski_no, sebep)

for eski in sorted(set(list(kesimler.keys()) + [bn for _, bn, _ in plakalar])):
    m = KALIP.match(eski)
    if not m:
        continue
    kok = m.group('kok')

    # ŞART 2: kesim kaydı doğruluyor mu
    kayitlar = kesimler.get(eski) or []
    if not kayitlar:
        atlanan.append((eski, 'bu üretim no ile bir kesim kaydı yok'))
        continue
    if not any(str(kno or '') == kok for _, kno in kayitlar):
        atlanan.append((eski, f'kesimin kaynak no\'su "{kok}" değil '
                              f'({kayitlar[0][1]})'))
        continue

    # ŞART 3: kısaltılmış hâli başka bir plakayla çakışıyor mu
    cakisan = [sn for _, bn, sn in plakalar
               if bn == eski and (kok.upper(), sn) in mevcut_cift]
    if cakisan:
        atlanan.append((eski, f'{kok} bloğunda {cakisan[0]} numaralı '
                              f'plaka ZATEN VAR — çakışırdı'))
        continue

    duzeltilecek[eski] = kok

print(' ── ADAYLAR ' + '─' * 56)
if not duzeltilecek and not atlanan:
    print('   Düzeltilecek kayıt yok — bütün üretim no\'lar zaten sade.')
    print()
    print('═' * 70)
    print('  ✓ YAPILACAK İŞ YOK')
    print('═' * 70)
    sys.exit(0)

for eski, yeni in duzeltilecek.items():
    pl = [p for p in plakalar if p[1] == eski]
    ks = len(kesimler.get(eski) or [])
    print(f'   {eski:<24} → {yeni}')
    print(f'      {len(pl)} plaka · {ks} kesim kaydı')
    if pl:
        ornek = sorted(pl, key=lambda x: (x[2] is None, x[2]))[:3]
        for _, bn, sn in ornek:
            esk = f'{bn}-{int(sn):02d}' if sn is not None else bn
            yen = f'{yeni}-{int(sn):02d}' if sn is not None else yeni
            print(f'         {esk}  →  {yen}')

if atlanan:
    print()
    print(' ── ATLANANLAR ' + '─' * 53)
    for eski, sebep in atlanan:
        print(f'   {eski:<24} {sebep}')

print()
if not duzeltilecek:
    print('═' * 70)
    print('  ⊙ Düzeltilebilecek kayıt yok (hepsi atlandı).')
    print('═' * 70)
    sys.exit(0)

if not UYGULA:
    print('═' * 70)
    print('  RAPOR MODU — hiçbir şey değişmedi.')
    print('  Uygulamak için:  venv/bin/python goc_b3.py --uygula')
    print('═' * 70)
    sys.exit(0)

# ══════════════════════════════════════════════════════════════════════
#  2 · UYGULA
# ══════════════════════════════════════════════════════════════════════
print(' ── YEDEK ' + '─' * 58)
if not yedek_al():
    sys.exit(1)
print()

with motor.begin() as b:
    pl_top = ks_top = 0
    for eski, yeni in duzeltilecek.items():
        r1 = b.execute(text('UPDATE plaka_stok SET blok_no = :y '
                            'WHERE blok_no = :e'), {'y': yeni, 'e': eski})
        r2 = b.execute(text('UPDATE kesim SET uretim_blok_no = :y '
                            'WHERE uretim_blok_no = :e'), {'y': yeni, 'e': eski})
        pl_top += r1.rowcount or 0
        ks_top += r2.rowcount or 0
        print(f'   {eski} → {yeni}: {r1.rowcount} plaka, {r2.rowcount} kesim')

print()
print('═' * 70)
print(f'  ✓ GÖÇ TAMAM — {pl_top} plaka, {ks_top} kesim kaydı güncellendi')
print('═' * 70)
print()
print('  Kimlikler (PLK-…) bilerek DEĞİŞTİRİLMEDİ: onlara sipariş,')
print('  proforma ve kesim detayları bağlı. Depoda okuduğun kod')
print('  blok_no\'dan türüyor ve o düzeldi.')

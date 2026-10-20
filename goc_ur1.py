#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — STOK KAYNAĞI GÖÇÜ  ·  UR1
#
#  ÖNKOŞUL: yama_ur1.py uygulanmış VE SERVİS YENİDEN BAŞLATILMIŞ olmalı.
#
#  ── SIRA NEDEN ÖNEMLİ ──
#    yama → systemctl restart → BU BETİK
#
#    `kaynak` sütununu açılış kendisi ekliyor (SD2 otomatik
#    migrasyonu). Bu betik onu KURMAZ; yoksa "önce yeniden başlat"
#    deyip çıkar.
#
#  ── NE YAPAR ──
#    1) KESİMDEN ÇIKMIŞ stokları `kaynak = 'uretim'` işaretler.
#
#       Bugün kesim modülü plaka/ebatlı üretirken `alis_tipi` alanına
#       dokunmuyor, yani model varsayılanı olan 'yurtici_kdvli'
#       kalıyor: ÜRETTİĞİMİZ mal, sistemde SATIN ALINMIŞ gibi
#       duruyor. Kimse fark etmedi çünkü KDV'si sıfır ve tedarikçi
#       borcu doğmuyor — ama stok listesinde ve ileride yazılacak her
#       raporda yanlış bilgi.
#
#       Ölçüt `kesim_detay` izi: hedef_stok_id o tablodaysa o stok
#       bir kesimden çıkmıştır. Tahmin yok, kayıt var.
#
#    2) GERİ KALAN her satırı `kaynak = 'satinalma'` yapar.
#
#       Sütun NULL olarak ekleniyor ve kod NULL'ı zaten "satın alma"
#       sayıyor. Yine de açıkça dolduruyorum: yarı NULL yarı dolu bir
#       sütun, "bu satırın kaynağı bilinmiyor mu yoksa satın alma
#       mı?" sorusunu her sorguda yeniden doğururdu.
#
#  ── NE YAPMAZ ──
#    Hiçbir satırı silmez, taşımaz, tutarını değiştirmez. Yalnızca
#    tek bir metin sütununu doldurur. Yanlış giderse geri dönüş de
#    tek bir UPDATE.
#
#  ── GÜVENLİK ──
#    • --uygula OLMADAN HİÇBİR ŞEY DEĞİŞMEZ; yalnızca rapor verir.
#    • PostgreSQL'de önce pg_dump yedeği alır; yedek başarısızsa İPTAL.
#    • Tek transaction.
#    • Tekrar çalıştırılabilir: ikinci koşu "yapılacak iş yok" der.
#
#  KULLANIM (proje dizininde):
#      venv/bin/python goc_ur1.py             # RAPOR
#      venv/bin/python goc_ur1.py --uygula    # UYGULAR
# ══════════════════════════════════════════════════════════════════════
import os
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
print('  MILESTONE ERP — STOK KAYNAĞI GÖÇÜ  ·  UR1')
print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (hiçbir şey değişmez)')
print('═' * 70)
print(f" Veritabanı : {kaynak_url.path.lstrip('/')} @ {kaynak_url.hostname or 'yerel'}")
print(f' Sürücü     : {motor.dialect.name}')
print()


def yedek_al():
    if not pg:
        print(' ⚠ PostgreSQL değil — otomatik yedek atlandı.')
        return True
    hedef = Path.home() / 'yedekler'
    hedef.mkdir(exist_ok=True)
    dosya = hedef / f'ur1-oncesi-{datetime.now():%Y%m%d_%H%M%S}.dump'
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
#  ÖNKOŞUL: `kaynak` sütunu açılışta kurulmuş olmalı
# ══════════════════════════════════════════════════════════════════════
TABLOLAR = ('blok_stok', 'plaka_stok', 'ebatli_stok')
tablolar = set(denetci.get_table_names())

eksik_tablo = [t for t in TABLOLAR if t not in tablolar]
if eksik_tablo:
    print(f" ✗ Şu tablo(lar) yok: {', '.join(eksik_tablo)}")
    print('   Yanlış veritabanına bağlanmış olabilirim. Duruyorum.')
    sys.exit(1)

eksik_sutun = [t for t in TABLOLAR
               if 'kaynak' not in {s['name'] for s in denetci.get_columns(t)}]
if eksik_sutun:
    print(' ✗ `kaynak` SÜTUNU HENÜZ YOK:')
    for t in eksik_sutun:
        print(f'     {t}.kaynak')
    print()
    print('   Sütunu uygulamanın AÇILIŞI ekliyor (SD2 otomatik')
    print('   migrasyonu). Sıra şu:')
    print()
    print('     python3 yama_ur1.py --uygula')
    print('     sudo systemctl restart milestone-erp')
    print('     venv/bin/python goc_ur1.py --uygula      ← sonra ben')
    sys.exit(1)

if 'kesim_detay' not in tablolar:
    print(' ✗ `kesim_detay` tablosu yok — kesimden çıkan stokları')
    print('   ayırt edemem. Tahminle işaretlemektense duruyorum.')
    sys.exit(1)

print(' ✓ `kaynak` sütunu üç stok tablosunda da yerinde')
print()

# ══════════════════════════════════════════════════════════════════════
#  DURUM
# ══════════════════════════════════════════════════════════════════════
# Kesim hedefi olarak YALNIZCA plaka ve ebatlı üretiliyor; blok
# kesimin GİRDİSİ, çıktısı değil. Yine de blok tablosunu da
# dolduruyoruz (hepsi satın alma) — sütun yarı boş kalmasın.
URETIM_SORGU = {
    'plaka_stok': "SELECT DISTINCT hedef_stok_id FROM kesim_detay "
                  "WHERE hedef_tip = 'PLAKA' AND hedef_stok_id IS NOT NULL",
    'ebatli_stok': "SELECT DISTINCT hedef_stok_id FROM kesim_detay "
                   "WHERE hedef_tip = 'EBATLI' AND hedef_stok_id IS NOT NULL",
}

print('─' * 70)
print(' DURUM')
print('─' * 70)

plan = {}
with motor.connect() as b:
    for t in TABLOLAR:
        toplam = b.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() or 0
        bos = b.execute(text(
            f'SELECT COUNT(*) FROM "{t}" WHERE kaynak IS NULL')).scalar() or 0
        if t in URETIM_SORGU:
            uretim = b.execute(text(
                f'SELECT COUNT(*) FROM "{t}" WHERE id IN ({URETIM_SORGU[t]}) '
                f"AND (kaynak IS NULL OR kaynak <> 'uretim')")).scalar() or 0
        else:
            uretim = 0
        plan[t] = {'toplam': toplam, 'bos': bos, 'uretim': uretim}
        print(f'   {t:<12} {toplam:>6} kayıt   '
              f'{bos:>5} kaynağı boş   {uretim:>5} kesimden çıkmış')

toplam_is = sum(v['bos'] for v in plan.values()) + sum(v['uretim'] for v in plan.values())
print()
if not toplam_is:
    print('═' * 70)
    print(' ✓ YAPILACAK İŞ YOK — kaynak alanları zaten dolu.')
    print('═' * 70)
    sys.exit(0)

print('─' * 70)
print(' YAPILACAK')
print('─' * 70)
for t, v in plan.items():
    if v['uretim']:
        print(f"   {t:<12} {v['uretim']:>5} satır → 'uretim'    (kesim_detay izi var)")
for t, v in plan.items():
    if v['bos']:
        print(f"   {t:<12} {v['bos']:>5} satır → 'satinalma'  (kaynağı boş olanlar)")
print()
print('   Not: önce üretim işaretleniyor, sonra KALAN boşlar satın')
print('   alma yapılıyor. Ters sırada kesimden çıkanlar da satın')
print('   alma olurdu.')
print()

if not UYGULA:
    print('═' * 70)
    print(' RAPOR MODU — hiçbir şey değişmedi.')
    print()
    print(' Uygulamak için:  venv/bin/python goc_ur1.py --uygula')
    print('═' * 70)
    sys.exit(0)

# ══════════════════════════════════════════════════════════════════════
#  UYGULA
# ══════════════════════════════════════════════════════════════════════
print('─' * 70)
print(' YEDEK')
print('─' * 70)
if not yedek_al():
    sys.exit(1)
print()

print('─' * 70)
print(' UYGULANIYOR')
print('─' * 70)
with motor.begin() as b:
    for t in TABLOLAR:
        if t in URETIM_SORGU:
            s = b.execute(text(
                f'UPDATE "{t}" SET kaynak = \'uretim\' '
                f'WHERE id IN ({URETIM_SORGU[t]}) '
                f"AND (kaynak IS NULL OR kaynak <> 'uretim')"))
            if s.rowcount:
                print(f"   {t:<12} {s.rowcount:>5} satır 'uretim' işaretlendi")
    for t in TABLOLAR:
        s = b.execute(text(
            f'UPDATE "{t}" SET kaynak = \'satinalma\' WHERE kaynak IS NULL'))
        if s.rowcount:
            print(f"   {t:<12} {s.rowcount:>5} satır 'satinalma' yapıldı")

print()
print('─' * 70)
print(' DOĞRULAMA')
print('─' * 70)
sorun = 0
with motor.connect() as b:
    for t in TABLOLAR:
        kalan = b.execute(text(
            f'SELECT COUNT(*) FROM "{t}" WHERE kaynak IS NULL')).scalar() or 0
        if kalan:
            print(f'   ✗ {t:<12} {kalan} satırın kaynağı hâlâ boş')
            sorun += 1
        else:
            print(f'   ✓ {t:<12} kaynağı boş satır kalmadı')
    for t, sorgu in URETIM_SORGU.items():
        yanlis = b.execute(text(
            f'SELECT COUNT(*) FROM "{t}" WHERE id IN ({sorgu}) '
            f"AND kaynak <> 'uretim'")).scalar() or 0
        if yanlis:
            print(f'   ✗ {t:<12} kesimden çıkan {yanlis} satır üretim değil')
            sorun += 1
        else:
            print(f'   ✓ {t:<12} kesimden çıkanların hepsi üretim')
    # Satın alma sayılan hiçbir satırın kesim izi OLMAMALI
    for t, sorgu in URETIM_SORGU.items():
        sayi = b.execute(text(
            f"SELECT COUNT(*) FROM \"{t}\" WHERE kaynak = 'uretim' "
            f'AND id NOT IN ({sorgu})')).scalar() or 0
        if sayi:
            print(f'   ⚠ {t:<12} {sayi} satır üretim ama kesim izi yok')
            print('     (elle girilmiş üretim kayıtları olabilir — normal)')

print()
print('═' * 70)
if sorun:
    print(f' ✗ {sorun} DOĞRULAMA BULGUSU — yedekten dönebilirsin.')
    sys.exit(1)
print(' ✓ GÖÇ TAMAMLANDI')
print()
print(' Kesimden çıkan stoklar artık ÜRETİM olarak işaretli;')
print(' geri kalanlar satın alma. Stok listesinde ayırt edilebilirler.')
print('═' * 70)

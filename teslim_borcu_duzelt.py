#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SH1 ÖNCESİ TESLİM BORCUNU DÜZELT — ÖNCE SALT OKUNUR
====================================================================

NE YAPAR: `kaynak='otomatik-teslim'` ile yazılmış, FATURASI OLMAYAN
teslim borçlarını gösterir. `--sil` verilirse SİLER.

NEDEN GEREKLİ: SH1 yamasından sonra teslim artık cariye borç
yazmıyor — borç yalnız faturadan doğuyor. Ama yamadan ÖNCE yazılmış
satırlar veritabanında duruyor. O siparişin faturası kesildiği anda
fatura kendi borcunu yazar ve müşteri İKİ KEZ borçlanır. Bu betik o
tuzağı fatura kesilmeden önce kaldırmak için.

NEYE DOKUNMAZ:
  · Faturadan doğan borçlar               (kaynak='fatura')
  · Elle girilmiş hareketler, tahsilatlar, kur farkları
  · `kaynak` damgası 'otomatik-teslim' OLMAYAN hiçbir satır
  · FATURASI OLAN siparişlerin teslim borçları — onlar ÇİFT BORÇ
    durumudur, tutarlar farklı olabilir (kısmi teslim / kısmi
    fatura) ve körü körüne silinmemeli. Betik onları AYRI listeler
    ve DOKUNMAZ; çıktıyı paylaş, kayıt kayıt bakalım.

Kullanım (PROJE DİZİNİNDE — `.env`i burada arıyor):
    venv/bin/python teslim_borcu_duzelt.py            # yalnız göster
    venv/bin/python teslim_borcu_duzelt.py --sil      # sil

`--sil` her satır için ONAY SORAR. Silmeden önce silinecek satırın
tamamını ve carinin bakiyesinin ne olacağını yazar.
"""
import io
import os
import sys

KOK = os.path.dirname(os.path.abspath(__file__)) or '.'
SIL = '--sil' in sys.argv

# ── .env oku ──
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
    print('✗ DATABASE_URL okunamadı — proje dizininde çalıştır.')
    sys.exit(1)

try:
    from sqlalchemy import create_engine, text
except ImportError:
    print('✗ sqlalchemy bulunamadı — venv/bin/python ile çalıştır.')
    sys.exit(1)

motor = create_engine(URL)

# Faturasi OLMAYAN teslim borclari — silinebilir olanlar.
TEMIZ = text('''
SELECT  t.id, t.cari_id, t.cari_unvan, t.baglanti_id AS siparis_id,
        t.hareket_tarihi, t.doviz, t.borc, t.islem_tip, t.aciklama,
        t.evrak_no
FROM    cari_hareket t
WHERE   t.kaynak       = 'otomatik-teslim'
  AND   t.baglanti_tip = 'siparis'
  AND   COALESCE(t.borc, 0) > 0
  AND   NOT EXISTS (SELECT 1 FROM faturalar fa
                    WHERE fa.siparis_id = t.baglanti_id
                      AND COALESCE(fa.durum, '') <> 'Iptal')
ORDER BY t.cari_unvan, t.hareket_tarihi
''')

# Faturasi OLAN teslim borclari — CIFT BORC, bu betik DOKUNMAZ.
CIFT = text('''
SELECT  t.id, t.cari_unvan, t.baglanti_id AS siparis_id,
        t.doviz, t.borc, fa.fatura_no, fa.toplam AS fatura_toplam
FROM    cari_hareket t
JOIN    faturalar   fa ON fa.siparis_id = t.baglanti_id
                      AND COALESCE(fa.durum, '') <> 'Iptal'
WHERE   t.kaynak       = 'otomatik-teslim'
  AND   t.baglanti_tip = 'siparis'
  AND   COALESCE(t.borc, 0) > 0
ORDER BY t.cari_unvan
''')

BAKIYE = text('''
SELECT COALESCE(SUM(COALESCE(borc,0) - COALESCE(alacak,0)), 0)
FROM   cari_hareket WHERE cari_id = :c
''')

print('=' * 68)
print('  SH1 ÖNCESİ TESLİM BORCU · ' + ('SİLME KİPİ' if SIL
                                        else 'salt okunur'))
print('=' * 68)

with motor.connect() as b:
    temiz = list(b.execute(TEMIZ))
    cift = list(b.execute(CIFT))

if cift:
    print()
    print(f'  ✗ {len(cift)} ÇİFT BORÇ VAR — BU BETİK DOKUNMUYOR')
    for r in cift:
        print(f'     {r.cari_unvan} · {r.siparis_id}')
        print(f'       teslim borcu {float(r.borc or 0):>12,.2f} {r.doviz}')
        print(f'       fatura       {float(r.fatura_toplam or 0):>12,.2f}'
              f'       ({r.fatura_no or "no yok"})')
    print('     Tutarlar farklıysa (kısmi teslim / kısmi fatura) körü')
    print('     körüne silinmemeli. Bu çıktıyı paylaş, birlikte bakalım.')

if not temiz:
    print()
    print('  ✓ Faturası olmayan otomatik teslim borcu YOK.')
    print('     Silinecek bir şey bulunamadı.')
    print('=' * 68)
    sys.exit(0)

print()
print(f'  {len(temiz)} FATURASIZ TESLİM BORCU')
print()
for r in temiz:
    with motor.connect() as b:
        bak = float(b.execute(BAKIYE, {'c': r.cari_id}).scalar() or 0)
    print(f'  ── {r.cari_unvan}  ({r.cari_id}) ──')
    print(f'     hareket     : {r.id}')
    print(f'     sipariş     : {r.siparis_id}')
    print(f'     tarih       : {r.hareket_tarihi}')
    print(f'     işlem tipi  : {r.islem_tip}')
    print(f'     evrak no    : {r.evrak_no or "YOK  ← belge yok, bu yüzden siliniyor"}')
    print(f'     borç        : {float(r.borc or 0):,.2f} {r.doviz}')
    print(f'     açıklama    : {(r.aciklama or "")[:60]}')
    print(f'     carinin bakiyesi ŞİMDİ  : {bak:>14,.2f}')
    print(f'     silinirse               : {bak - float(r.borc or 0):>14,.2f}')
    print()

if not SIL:
    print('  Hiçbir şey değiştirilmedi (salt okunur).')
    print()
    print('  SİLMEK İÇİN:')
    print('    venv/bin/python teslim_borcu_duzelt.py --sil')
    print()
    print('  SİLMEK NEDEN DOĞRU: bu satır bir FATURA DEĞİL, sistemin')
    print('  kendi otomatik kaydı ve evrak numarası yok. SH1\'den sonra')
    print('  borç yalnız faturadan doğuyor; bu satır dururken fatura')
    print('  kesilirse müşteri iki kez borçlanır.')
    print()
    print('  KAYBOLAN BİR ŞEY OLMUYOR: teslim, Faturalar sayfasındaki')
    print('  "Faturası Beklenen Teslimler" listesinde duruyor ve')
    print('  oradan faturalanabiliyor.')
    print('=' * 68)
    sys.exit(0)

# ── SİLME ─────────────────────────────────────────────────────────
print('  ── SİLME ──')
silinen = 0
for r in temiz:
    soru = (f'  {r.cari_unvan} · {r.siparis_id} · '
            f'{float(r.borc or 0):,.2f} {r.doviz} SİLİNSİN Mİ? '
            f'(e/h): ')
    try:
        cevap = input(soru).strip().lower()
    except EOFError:
        print('\n  ✗ Giriş okunamadı (betiği doğrudan terminalden '
              'çalıştır). Hiçbir şey silinmedi.')
        sys.exit(1)
    if cevap not in ('e', 'evet', 'y', 'yes'):
        print('     atlandı.')
        continue
    with motor.begin() as b:          # islem: ya hepsi ya hicbiri
        # Tam o SATIR, kimlikle. Damga + kimlik birlikte: yanlis
        # satiri silmenin yolu yok.
        n = b.execute(text('''
            DELETE FROM cari_hareket
            WHERE id = :i AND kaynak = 'otomatik-teslim'
              AND baglanti_tip = 'siparis'
        '''), {'i': r.id}).rowcount
    if n == 1:
        silinen += 1
        with motor.connect() as b:
            bak = float(b.execute(BAKIYE, {'c': r.cari_id}).scalar() or 0)
        print(f'     ✓ silindi. {r.cari_unvan} yeni bakiye: {bak:,.2f}')
    else:
        print(f'     ✗ silinemedi (etkilenen satır: {n}) — damga ya da '
              f'kimlik değişmiş olabilir.')

print()
print(f'  {silinen} satır silindi.')
if silinen:
    print('  Şimdi o siparişin faturasını normal akıştan kesebilirsin:')
    print('    Faturalar → "Faturası Beklenen Teslimler" → Fatura Kes')
print('=' * 68)

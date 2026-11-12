#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÇİFT BORÇ TARAMASI — SALT OKUNUR
====================================================================

NE ARAR: Aynı sipariş için cariye İKİ KEZ borç yazılmış durumları.

    teslim borcu   (kaynak='otomatik-teslim', baglanti_tip='siparis')
  + fatura borcu   (kaynak='fatura',          baglanti_tip='fatura')
  = müşteri iki kez borçlu

NEDEN OLUYOR: Sipariş teslim edilirken faturası YOKSA sistem
otomatik bir teslim borcu yazıyor ("fatura zaten borcu işledi"
varsayımıyla). Ama fatura SONRADAN kesilince o satır kaldırılmıyor.
Fatura kesimi kendi borcunu yazıyor ve iki satır yan yana duruyor.

ÖLÇÜLDÜ (gerçek uçlarla): 5.000 USD'lik bir satışta cari ekstresi
10.000 USD gösteriyor. İki istek de 200 dönüyor, ekranda hiçbir
uyarı yok.

NE YAPMAZ: HİÇBİR ŞEY YAZMAZ, SİLMEZ, DEĞİŞTİRMEZ. Yalnız okur.
Düzeltmeyi kendi başına yapmıyor — hangi satırın kalacağı para
kararıdır, sana ait.

Kullanım (PROJE DİZİNİNDE — `.env`i burada arıyor):
    cp cift_borc_tara.py ~/milestoneERP-v2/
    cd ~/milestoneERP-v2 && venv/bin/python cift_borc_tara.py
"""
import io
import os
import sys

KOK = os.path.dirname(os.path.abspath(__file__)) or '.'

# ── .env oku (dotenv kurulu olmasa da çalışsın) ──
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

try:
    from sqlalchemy import create_engine, text
except ImportError:
    print('✗ sqlalchemy bulunamadı — venv/bin/python ile çalıştır.')
    sys.exit(1)

motor = create_engine(URL)

# ── 1 · OTOMATİK TESLİM BORÇLARI ──────────────────────────────────
# Tek sorgu, tek geçiş: teslim borcu olan her siparişin yanına o
# siparişin faturalarından doğan borçları getiriyor.
SORGU = text('''
SELECT  t.id                AS teslim_id,
        t.cari_id,
        t.cari_unvan,
        t.baglanti_id       AS siparis_id,
        t.hareket_tarihi    AS teslim_tarihi,
        t.doviz             AS teslim_doviz,
        t.borc              AS teslim_borc,
        f.id                AS fatura_hareket_id,
        f.evrak_no          AS fatura_no,
        f.hareket_tarihi    AS fatura_tarihi,
        f.doviz             AS fatura_doviz,
        f.borc              AS fatura_borc
FROM        cari_hareket t
JOIN        faturalar       fa ON fa.siparis_id = t.baglanti_id
                              AND COALESCE(fa.durum, '') <> 'Iptal'
JOIN        cari_hareket f  ON f.baglanti_tip = 'fatura'
                              AND f.baglanti_id  = fa.id
                              AND COALESCE(f.borc, 0) > 0
WHERE   t.kaynak        = 'otomatik-teslim'
  AND   t.baglanti_tip  = 'siparis'
  AND   COALESCE(t.borc, 0) > 0
ORDER BY t.cari_unvan, t.baglanti_id
''')

# Teslim borcu var ama faturası YOK — bu bir hata DEĞİL, bilgi:
# teslim edilmiş, henüz faturalanmamış satış.
BEKLEYEN = text('''
SELECT  t.cari_unvan, t.baglanti_id, t.hareket_tarihi, t.doviz, t.borc
FROM    cari_hareket t
WHERE   t.kaynak       = 'otomatik-teslim'
  AND   t.baglanti_tip = 'siparis'
  AND   COALESCE(t.borc, 0) > 0
  AND   NOT EXISTS (SELECT 1 FROM faturalar fa
                    WHERE fa.siparis_id = t.baglanti_id
                      AND COALESCE(fa.durum, '') <> 'Iptal')
ORDER BY t.cari_unvan, t.hareket_tarihi
''')

print('=' * 68)
print('  ÇİFT BORÇ TARAMASI  ·  salt okunur, hiçbir şey değiştirilmez')
print('=' * 68)

with motor.connect() as b:
    try:
        cift = list(b.execute(SORGU))
        bekleyen = list(b.execute(BEKLEYEN))
    except Exception as e:
        print(f'  ✗ sorgu çalışmadı: {str(e)[:200]}')
        print('    Tablo adları beklenenden farklı olabilir; çıktıyı bana')
        print('    gönder, sorguyu şemaya göre düzeltirim.')
        sys.exit(1)

if not cift:
    print()
    print('  ✓ ÇİFT BORÇ YOK.')
    print('    Aynı sipariş için hem otomatik teslim borcu hem fatura')
    print('    borcu taşıyan cari bulunmadı.')
else:
    print()
    print(f'  ✗ {len(cift)} ÇİFT BORÇ BULUNDU')
    print()
    # Doviz basina toplam: farkli dovizleri TOPLAMIYORUM.
    fazla = {}
    son_cari = None
    for r in cift:
        if r.cari_unvan != son_cari:
            print(f'  ── {r.cari_unvan}  ({r.cari_id}) ──')
            son_cari = r.cari_unvan
        print(f'     sipariş {r.siparis_id}')
        print(f'       teslim borcu  {float(r.teslim_borc or 0):>12,.2f} '
              f'{r.teslim_doviz or "":<4} {r.teslim_tarihi}   '
              f'(evrak no YOK · {r.teslim_id})')
        print(f'       fatura borcu  {float(r.fatura_borc or 0):>12,.2f} '
              f'{r.fatura_doviz or "":<4} {r.fatura_tarihi}   '
              f'({r.fatura_no or "no yok"} · {r.fatura_hareket_id})')
        dv = r.teslim_doviz or '?'
        fazla[dv] = fazla.get(dv, 0) + float(r.teslim_borc or 0)
    print()
    print('  FAZLA YAZILAN BORÇ (teslim satırları toplamı):')
    for dv, t in sorted(fazla.items()):
        print(f'     {t:>14,.2f} {dv}')
    print()
    print('  NE YAPMALI — bu bir PARA KARARI, betik kendi başına')
    print('  yapmıyor:')
    print('    Belge fatura. Teslim satırı sistemin kendi otomatik')
    print('    kaydı ve evrak numarası yok; kalması gereken fatura')
    print('    satırıdır. Ama silmeden önce her satırın gerçekten')
    print('    aynı satışa ait olduğunu ekstrede gör — tutarlar')
    print('    farklıysa (kısmi teslim, kısmi fatura) öylece')
    print('    silinmemeli.')
    print('    Listeyi bana gönder, sana kayıt kayıt düzeltme')
    print('    betiği yazayım.')

print()
if bekleyen:
    print(f'  ⓘ FATURASI OLMAYAN {len(bekleyen)} TESLİM BORCU')
    print('    Bunlar HATA DEĞİL: teslim edilmiş, henüz faturalanmamış')
    print('    satışlar. Faturası kesilince yukarıdaki çift borç')
    print('    durumuna düşerler — fatura kesmeden önce haberdar ol.')
    print()
    for r in bekleyen:
        print(f'     {r.cari_unvan:<28} {r.baglanti_id:<24} '
              f'{float(r.borc or 0):>12,.2f} {r.doviz or "":<4} '
              f'{r.hareket_tarihi}')
    print()
else:
    print('  ⓘ Faturası beklenen otomatik teslim borcu da yok.')
    print()

print('  (Bu betik hiçbir şey değiştirmedi.)')
print('=' * 68)

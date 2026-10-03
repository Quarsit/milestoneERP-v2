#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — GİDER FATURASI TRY KARŞILIĞINI DÜZELT  (GT1)
#
#  ── NE İÇİN ──
#    Nakliye/gider faturası cariye işlenirken `alacak_try` alanı üç
#    ayrı yerde üç farklı şekilde hesaplanıyordu ve ikisi hatalıydı:
#
#      · TRY faturada tutarın USD KARŞILIĞI yazılıyordu.
#        5.235,00 ₺ → alacak_try = 107,16   (olması gereken 5.235,00)
#      · Blok dağılımında alan HİÇ yazılmıyordu.
#      · `kur_uygulanan` her zaman 1.0 yazılıyordu; EUR faturada
#        ekstrede "1 EUR = 1,0000 ₺" görünüyordu.
#
#    Ölçülen sonuç: PINAR GÜMRÜK MÜŞAVİRLİĞİ'nin 166.895,62 ₺
#    tutarındaki gümrük hareketleri, cari ekstresinin "Net Özet"
#    kutusunda 3.413,48 TRY çıkıyordu. Satırlar ve bakiye sütunu
#    doğruydu (onlar ham tutarı kullanıyor), özet yanlıştı — aynı
#    belgede iki farklı rakam.
#
#    Yazan taraf düzeltildi; bu betik GEÇMİŞ kayıtları onarır.
#
#  ── GÜVENLİ ──
#    • Varsayılan SALT OKUNUR; --uygula demeden hiçbir şey yazılmaz.
#    • Yalnızca `alacak_try` / `borc_try` / `kur_uygulanan` güncellenir.
#      Tutar (`alacak`), döviz, bağlantı, tarih DEĞİŞMEZ.
#    • Kuru bulunamayan hareket ATLANIR ve raporlanır — sessizce
#      sıfır yazmaz.
#    • Tekrar çalıştırılabilir; düzelmiş kayıt ikinci kez ele alınmaz.
#
#  ── KULLANIM ──
#      venv/bin/python gider_try_duzelt.py              # önizleme
#      venv/bin/python gider_try_duzelt.py --uygula     # yaz
#      venv/bin/python gider_try_duzelt.py --cari CR-XXXX
# ══════════════════════════════════════════════════════════════════════
import os
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))

try:
    from dotenv import load_dotenv
    load_dotenv(KOK / '.env')
except Exception:
    pass

os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')

import flask_app                                   # noqa: E402
from models import db, CariHareket                 # noqa: E402

UYGULA = '--uygula' in sys.argv
CARI = None
if '--cari' in sys.argv:
    i = sys.argv.index('--cari')
    if i + 1 < len(sys.argv):
        CARI = sys.argv[i + 1]

# Gider faturaları bu iki işaretten biriyle yazılıyor; ikisini de al
# ki eski kayıtlar (kaynak alanı yokken yazılanlar) atlanmasın.
ISLEM = 'Nakliye/Gider Faturası'


def tr(x):
    return f'{x:,.2f}'.replace(',', '~').replace('.', ',').replace('~', '.')


print('═' * 70)
print(' MILESTONE ERP — GİDER FATURASI TRY KARŞILIĞI')
print('═' * 70)
print(' Kip        :', 'UYGULA (yazacak)' if UYGULA else 'ÖNİZLEME (salt okunur)')
if CARI:
    print(' Süzgeç     : cari =', CARI)
print()

with flask_app.app.app_context():
    sorgu = CariHareket.query.filter(
        db.or_(CariHareket.kaynak == 'maliyet',
               CariHareket.islem_tip == ISLEM))
    if CARI:
        sorgu = sorgu.filter(CariHareket.cari_id == CARI)
    hareketler = sorgu.order_by(CariHareket.hareket_tarihi.asc()).all()

    print(f' İncelenen  : {len(hareketler)} gider hareketi')
    if not hareketler:
        print('\n ✓ Gider faturası kaydı yok. Yapacak bir şey yok.')
        sys.exit(0)

    duzelecek, atlanan, zaten = [], [], 0
    for h in hareketler:
        dv = (h.doviz or 'TRY').upper()
        for alan in ('alacak', 'borc'):
            ham = float(getattr(h, alan) or 0)
            if ham <= 0:
                continue
            # ASIL KODLA AYNI HESAP: `app.try_karsilik` uygulamanın
            # kendi yardımcısı. Burada kopyası tutulsaydı zamanla
            # ayrışırdı — hatanın kökeni de buydu.
            try_tutar, kur = flask_app.app.try_karsilik(
                ham, dv, tarih=h.hareket_tarihi)
            if dv != 'TRY' and (not kur or kur <= 0):
                atlanan.append((h, alan, 'kur bulunamadı'))
                continue
            mevcut = float(getattr(h, alan + '_try') or 0)
            mevcut_kur = float(h.kur_uygulanan or 0)
            tutar_bozuk = abs(mevcut - float(try_tutar)) > 0.02
            kur_bozuk = abs(mevcut_kur - float(kur)) > 0.000001
            if not tutar_bozuk and not kur_bozuk:
                zaten += 1
                continue
            duzelecek.append((h, alan, mevcut, float(try_tutar),
                              mevcut_kur, float(kur)))

    print(f' Zaten doğru: {zaten}')
    print(f' Düzelecek  : {len(duzelecek)}')
    if atlanan:
        print(f' Atlanan    : {len(atlanan)}  (kuru bulunamayan)')
    print()

    if duzelecek:
        print('─' * 70)
        print(f'{"TARİH":<12}{"CARİ":<22}{"DVZ":<5}{"TUTAR":>12}'
              f'{"ESKİ TRY":>14}{"YENİ TRY":>14}')
        print('─' * 70)
        for h, alan, eski, yeni, e_kur, y_kur in duzelecek[:40]:
            ad = (h.cari_unvan or h.cari_id or '?')[:20]
            print(f'{str(h.hareket_tarihi or ""):<12}{ad:<22}'
                  f'{(h.doviz or "TRY"):<5}'
                  f'{tr(float(getattr(h, alan) or 0)):>12}'
                  f'{tr(eski):>14}{tr(yeni):>14}')
        if len(duzelecek) > 40:
            print(f'   … ve {len(duzelecek) - 40} kayıt daha')
        print('─' * 70)
        fark = sum(y - e for _, _, e, y, _, _ in duzelecek)
        print(f' TRY toplamındaki değişim: {tr(fark)} ₺')
        print()

    for h, alan, _e, _ad in [(a, b, c, d) for a, b, c, d in atlanan]:
        print(f'   ⚠ {h.id} ({h.doviz}) — {_ad}, dokunulmadı')
    if atlanan:
        print()

    if not duzelecek:
        print(' ✓ Bütün gider hareketlerinin TRY karşılığı doğru.')
        sys.exit(0)

    if not UYGULA:
        print(' Hiçbir şey yazılmadı. Uygulamak için:')
        print('   venv/bin/python gider_try_duzelt.py --uygula')
        sys.exit(0)

    for h, alan, _e, yeni, _ek, y_kur in duzelecek:
        setattr(h, alan + '_try', yeni)
        h.kur_uygulanan = y_kur
    db.session.commit()
    print(f' ✓ {len(duzelecek)} hareket düzeltildi.')
    print('   Cari ekstresini yeniden alıp Net Özet kutusunu kontrol edin.')

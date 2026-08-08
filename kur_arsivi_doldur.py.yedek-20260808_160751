#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — KUR ARŞİVİNİ GEÇMİŞE DOLDUR  ·  K1
#
#  NEDEN GEREKLİ:
#    Kur arşivi 1 Ocak 2026'da başlıyordu. Daha eski tarihli bir alış
#    girildiğinde (örn. 2025 faturası) o güne ait kur bulunamıyor ve
#    _try_karsilik() SIFIR dönüyor. Sonuç: cari hareketin TL karşılığı
#    0 yazılıyor, ekstre TL üzerinden topladığı için BAKİYE 0.00
#    görünüyor — oysa çekmece ham dövizi topladığı için doğru
#    gösteriyor. İki ekran birbirini tutmuyor.
#
#    Bu betik arşivi 2019'a kadar geriye doldurur; sorunun KÖKÜNÜ
#    kurutur. Geçmiş alışların TL karşılığı doğru hesaplanır.
#
#  NEDEN AÇILIŞTA DEĞİL, AYRI BETİKTE:
#    2019 → bugün ≈ 1.800 iş günü. Her gün için TCMB'ye ayrı istek
#    gidiyor. Açılışta yapılsaydı uygulama DAKİKALARCA kilitlenirdi
#    ve systemd servisi zaman aşımına düşebilirdi. Bu yüzden tek
#    seferlik, elle çalıştırılan bir betik.
#
#  ÖZELLİKLER:
#    • Kesintiye uğrarsa KALDIĞI YERDEN devam eder (kayıtlı günleri
#      atlar) — Ctrl+C güvenli
#    • Her 20 günde bir kaydeder, ilerleme gösterir
#    • Hafta sonlarını atlar (TCMB kur yayınlamaz)
#    • TCMB'ye nazik davranır: istekler arası kısa bekleme
#    • Resmî tatillerde kur yoktur; o günler sessizce atlanır
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python kur_arsivi_doldur.py                  # 2019'dan
#      venv/bin/python kur_arsivi_doldur.py --baslangic 2023-01-01
#      venv/bin/python kur_arsivi_doldur.py --tahmin         # süre tahmini
#
#  SÜRE: 2019'dan bugüne ilk çalıştırma 15–30 dakika sürebilir.
#  Uygulama çalışırken de koşturulabilir (yalnızca ekleme yapar).
# ══════════════════════════════════════════════════════════════════════
import os
import sys
import time
from datetime import date, datetime, timedelta

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.getcwd())

BASLANGIC = date(2019, 1, 1)
SADECE_TAHMIN = '--tahmin' in sys.argv
for i, a in enumerate(sys.argv[1:]):
    if a == '--baslangic' and i + 2 <= len(sys.argv[1:]):
        try:
            BASLANGIC = datetime.strptime(sys.argv[i + 2], '%Y-%m-%d').date()
        except ValueError:
            print("HATA: tarih biçimi YYYY-AA-GG olmalı (örn. 2019-01-01)")
            sys.exit(1)

import xml.etree.ElementTree as ET  # noqa: E402

import requests  # noqa: E402

import flask_app  # noqa: E402
from models import db, DovizKur  # noqa: E402


def tcmb_gun_kuru_cek(gun):
    """Bir gunun TCMB kurunu ceker. Doner: (usd, eur) ya da (None, None).

    NOT: flask_app icindeki _tcmb_gun_kuru_cek() ile AYNI mantik.
    Oradaki fonksiyon create_app() govdesinde yuvalanmis oldugu icin
    disaridan cagrilamiyor; bu yuzden burada tekrarlandi. Mantik
    degisirse iki yeri de guncelleyin.

    Hafta sonu ve resmi tatillerde TCMB kur yayinlamaz -> 404.
    """
    try:
        url = (f"https://www.tcmb.gov.tr/kurlar/{gun.strftime('%Y%m')}/"
               f"{gun.strftime('%d%m%Y')}.xml")
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return None, None
        root = ET.fromstring(r.content)
        usd = eur = None
        for c in root.findall('Currency'):
            kod = c.get('CurrencyCode')
            if kod not in ('USD', 'EUR'):
                continue
            satis_el = c.find('ForexSelling')
            alis_el = c.find('ForexBuying')
            val = None
            if satis_el is not None and satis_el.text:
                val = float(satis_el.text)
            elif alis_el is not None and alis_el.text:
                val = float(alis_el.text)
            if kod == 'USD':
                usd = val
            else:
                eur = val
        return usd, eur
    except Exception:
        return None, None

app = flask_app.app

print("═" * 70)
print(" MILESTONE ERP — KUR ARŞİVİ GEÇMİŞE DOLDURMA")
print("═" * 70)

with app.app_context():
    bugun = date.today()
    kayitli = set(t[0] for t in db.session.query(DovizKur.tarih)
                  .filter_by(doviz='USD').all())

    eksik = []
    g = BASLANGIC
    while g <= bugun:
        if g.weekday() < 5 and g not in kayitli:
            eksik.append(g)
        g += timedelta(days=1)

    print(f" Başlangıç   : {BASLANGIC}")
    print(f" Bugün       : {bugun}")
    print(f" Kayıtlı gün : {len(kayitli):,}")
    print(f" Eksik gün   : {len(eksik):,}")
    print()

    if not eksik:
        print(" ✓ Arşiv zaten tam — yapılacak iş yok.")
        sys.exit(0)

    dk = len(eksik) * 0.6 / 60
    print(f" Tahmini süre: ~{dk:.0f} dakika  (gün başına ~0,6 sn)")
    print()

    if SADECE_TAHMIN:
        print(" --tahmin verildi, hiçbir şey çekilmedi.")
        sys.exit(0)

    print(" Başlıyor. Ctrl+C ile durdurabilirsiniz — kaldığı yerden")
    print(" devam eder, kaydedilenler korunur.")
    print("─" * 70)

    eklenen = tatil = hata = 0
    basla = time.time()
    try:
        for sira, g in enumerate(eksik, start=1):
            try:
                usd, eur = tcmb_gun_kuru_cek(g)
            except Exception as e:
                hata += 1
                usd = eur = None
                if hata <= 3:
                    print(f"   ! {g}: {str(e)[:60]}")

            if usd:
                db.session.add(DovizKur(doviz='USD', alis=usd, satis=usd,
                                        efektif=usd, tarih=g, kaynak='TCMB'))
                eklenen += 1
            else:
                tatil += 1
            if eur:
                db.session.add(DovizKur(doviz='EUR', alis=eur, satis=eur,
                                        efektif=eur, tarih=g, kaynak='TCMB'))

            if sira % 20 == 0:
                db.session.commit()
                gecen = time.time() - basla
                kalan = (gecen / sira) * (len(eksik) - sira) / 60
                print(f"   {sira:>5,}/{len(eksik):,}  ({sira * 100 // len(eksik)}%)  "
                      f"eklenen {eklenen:,} · kursuz {tatil:,}  "
                      f"· kalan ~{kalan:.0f} dk")
            time.sleep(0.15)   # TCMB'ye nazik davran
    except KeyboardInterrupt:
        db.session.commit()
        print()
        print("─" * 70)
        print(f" ⏸ Durduruldu. {eklenen:,} gün kaydedildi.")
        print(" Aynı komutu tekrar çalıştırın, kaldığı yerden devam eder.")
        sys.exit(0)

    db.session.commit()
    print("─" * 70)
    print()
    print("═" * 70)
    print(f" ✓ TAMAMLANDI — {eklenen:,} günlük kur eklendi")
    if tatil:
        print(f"   {tatil:,} gün kursuz (resmî tatil — normal)")
    if hata:
        print(f"   {hata:,} günde hata alındı")
    print(f"   Süre: {(time.time() - basla) / 60:.1f} dakika")
    print()
    print(" SONRAKİ ADIM — mevcut sıfır kayıtları onarın:")
    print("   venv/bin/python onarim_try_karsilik.py")
    print("═" * 70)

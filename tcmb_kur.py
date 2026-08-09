"""
Milestone ERP — TCMB KUR ÇEKME (ORTAK MODÜL)

═══════════════════════════════════════════════════════════════════
 NEDEN VAR
═══════════════════════════════════════════════════════════════════
Aynı XML ayrıştırma mantığı DÖRT ayrı yerde kopyalanmıştı:

    flask_app.py       _tcmb_gun_kuru_cek()     tarih bazlı
    flask_app.py       guncel_kurlari_cek()     today.xml
    kur_arsivi_doldur  tcmb_gun_kuru_cek()      tarih bazlı
    kur_guncelle       tcmb_gun_kuru_cek()      tarih bazlı

Bedeli somut oldu: K9 yamasında alış/satış hatasını düzeltirken üç
kopyayı buldum, dördüncüsünü kaçırdım. Kullanıcı ekranda gördü —
arşiv doğru, bugünün kuru yanlış. K10 ile ancak o zaman kapandı.

Kod yorumlarında "mantık değişirse iki yeri de güncelleyin" yazıyordu
ama sayı dörttü. Kopyalanan kod, hatanın da kopyalanması demek.

Bu modül tek doğruluk kaynağı. Yeni bir çağrı noktası eklenirse
buradan çağıracak; beşinci bir kopya çıkmayacak.

═══════════════════════════════════════════════════════════════════
 TCMB XML YAPISI
═══════════════════════════════════════════════════════════════════
    <Currency CurrencyCode="USD">
      <ForexBuying>47.4832</ForexBuying>       ← döviz alış
      <ForexSelling>47.5550</ForexSelling>     ← döviz satış
      <BanknoteBuying>47.4499</BanknoteBuying>
      <BanknoteSelling>47.6264</BanknoteSelling>  ← efektif satış
    </Currency>

Üçü de AYRI saklanır. Hesaplarda `alis` kullanılır (VUK/GİB: dövizli
işlemin TL karşılığı TCMB döviz alış kuru ile hesaplanır).

Hafta sonu ve resmî tatillerde TCMB kur yayımlamaz → 404 → (None, None).
Bu bir hata değil, beklenen durumdur.
"""
import xml.etree.ElementTree as ET
from datetime import date

import requests

# Tarih bazlı arşiv: /kurlar/YYYYAA/GGAAYYYY.xml
TCMB_ARSIV = "https://www.tcmb.gov.tr/kurlar/{yilay}/{tamtarih}.xml"
# Günün kuru: 15:30 sonrası bugünün, öncesi dünün kuru
TCMB_BUGUN = "https://www.tcmb.gov.tr/kurlar/today.xml"

ZAMAN_ASIMI = 10


def _sayi(deger):
    """XML metnini sayıya çevirir; boş/bozuksa None."""
    try:
        return float(deger) if deger else None
    except (TypeError, ValueError):
        return None


def _xml_ayristir(icerik):
    """TCMB XML'inden USD ve EUR üçlülerini çıkarır.

    Doner: (usd, eur) — her biri (alis, satis, efektif) ya da None.

    ÜÇ DEĞER DE AYRI okunur. K9 öncesinde yalnızca ForexSelling
    okunup üç alana birden yazılıyordu; alış/satış farkı (spread)
    kayboluyordu. 100.000 $'lık işlemde ~7.000 TL fark eden bir hata.
    """
    try:
        kok = ET.fromstring(icerik)
    except ET.ParseError:
        return None, None

    usd = eur = None
    for kur in kok.findall('Currency'):
        kod = kur.get('CurrencyCode')
        if kod not in ('USD', 'EUR'):
            continue

        def oku(etiket):
            el = kur.find(etiket)
            return _sayi(el.text) if el is not None else None

        alis = oku('ForexBuying')
        satis = oku('ForexSelling')
        # Efektif satış yoksa döviz satışa, o da yoksa alışa düşer
        efektif = oku('BanknoteSelling') or satis or alis
        # EA1: efektif ALIŞ (nakit döviz bozdurma kuru).
        # TCMB veriyordu ama saklanmıyordu.
        efektif_alis = oku('BanknoteBuying') or alis

        if not (alis or satis or efektif):
            continue

        # Biri eksikse diğeriyle doldurulur — sıfır yazmaktan iyidir
        deger = (alis or satis, satis or alis, efektif, efektif_alis)
        if kod == 'USD':
            usd = deger
        else:
            eur = deger

    return usd, eur


def gun_kuru_cek(gun=None):
    """Belirli bir günün TCMB kurunu çeker.

    gun=None ise BUGÜNÜN kuru (today.xml) çekilir.

    Doner: (usd, eur) — her biri (alis, satis, efektif) ya da None.
    Hafta sonu/tatil → (None, None). Bu beklenen durumdur.
    """
    if gun is None:
        url = TCMB_BUGUN
    else:
        url = TCMB_ARSIV.format(yilay=gun.strftime('%Y%m'),
                                tamtarih=gun.strftime('%d%m%Y'))
    try:
        yanit = requests.get(url, timeout=ZAMAN_ASIMI)
        if yanit.status_code != 200:
            return None, None
        return _xml_ayristir(yanit.content)
    except Exception:
        # Ağ hatası, zaman aşımı, bozuk XML — hepsi "kur yok" demektir.
        # Cagiran taraf None'i zaten ele aliyor.
        return None, None


def bugun_kuru_cek():
    """Bugünün kuru — gun_kuru_cek() için okunabilir kısayol."""
    return gun_kuru_cek(None)

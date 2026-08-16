#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — MÜŞTERİ BAĞI DENETİMİ  (salt okunur)
#
#  ── NE İÇİN ──
#    CRM-A ile beş tabloya `cari_id` eklendi ve kayıt yazılırken
#    `musteri` adından otomatik dolduruluyor. Ama eşleşme
#    bulunamazsa alan NULL kalır — kayıt reddedilmez, çünkü fatura
#    kesilmesini engellemek eksik bağdan kötü olurdu.
#
#    Bu betik açıkta kalan kayıtları bulur. Düzenli çalıştırılmazsa
#    bağsız kayıtlar sessizce birikir ve CRM ekranları eksik geçmiş
#    gösterir — üstelik eksik olduğu belli olmaz.
#
#  ── ÜÇ DENETİM ──
#    B1  cari_id boş        → müşteri geçmişinde görünmez
#    B2  cari_id var ama o cari YOK  → kırık referans
#    B3  cari_id ile musteri adı ÇELİŞİYOR → hangisi doğru belirsiz
#        (unvan sonradan değiştiyse normaldir; kimlik esas alınır)
#
#  ── HİÇBİR ŞEY DEĞİŞTİRMEZ ──  Sadece SELECT.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python crm_bag_denetim.py
#      venv/bin/python crm_bag_denetim.py --tam    # her kaydı listele
# ══════════════════════════════════════════════════════════════════════
import os
import sys
from pathlib import Path

if not Path('flask_app.py').exists():
    print("HATA: flask_app.py bu klasörde yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

for _a in sys.argv[1:]:
    if _a.startswith('--url='):
        os.environ['DATABASE_URL'] = _a.split('=', 1)[1]

_URL = os.environ.get('DATABASE_URL')
if not _URL:
    print("HATA: DATABASE_URL bulunamadı (.env okunamadı).")
    print("  Adres olmadan boş bir SQLite'a bağlanıp yanlışlıkla")
    print("  'her şey temiz' raporu verirdim. Çalışmayı reddediyorum.")
    sys.exit(1)

TAM = '--tam' in sys.argv
os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
sys.path.insert(0, str(Path('.').resolve()))

import flask_app  # noqa: E402
from models import (Cari, Fatura, Proforma, Rezervasyon,  # noqa: E402
                    SatisKaydi, Sevkiyat)

MODELLER = [
    (Proforma, 'Proforma'),
    (Fatura, 'Fatura'),
    (SatisKaydi, 'Satış Kaydı'),
    (Sevkiyat, 'Sevkiyat'),
    (Rezervasyon, 'Rezervasyon'),
]


def _gizle(u):
    if '@' in u and '//' in u:
        bas, son = u.split('//', 1)
        if '@' in son:
            kimlik, sunucu = son.split('@', 1)
            return f"{bas}//{kimlik.split(':')[0]}:***@{sunucu}"
    return u


print("═" * 70)
print(" MÜŞTERİ BAĞI DENETİMİ  (salt okunur)")
print("═" * 70)
print(f" Veritabanı : {_gizle(_URL)}")
print()

with flask_app.app.app_context():
    unvanlar = {c.id: c.unvan for c in Cari.query.all()}
    print(f"  Cari kaydı : {len(unvanlar)}")

    bos, kirik, celiski, toplam = [], [], [], 0
    for model, ad in MODELLER:
        kayitlar = model.query.all()
        toplam += len(kayitlar)
        for k in kayitlar:
            cid = getattr(k, 'cari_id', None)
            musteri = (getattr(k, 'musteri', None) or '').strip()
            if not cid:
                bos.append((ad, k.id, musteri))
            elif cid not in unvanlar:
                kirik.append((ad, k.id, musteri, cid))
            elif musteri and unvanlar[cid] != musteri:
                celiski.append((ad, k.id, musteri, unvanlar[cid]))

    print(f"  Denetlenen : {toplam} kayıt "
          f"({', '.join(a for _, a in MODELLER)})")
    print()

    def _bolum(baslik, liste, aciklama, bicim):
        print("─" * 70)
        print(f" {baslik}")
        print("─" * 70)
        if not liste:
            print("   ✓ temiz")
            print()
            return
        print(f"   {len(liste)} kayıt — {aciklama}")
        for satir in (liste if TAM else liste[:12]):
            print("     " + bicim(satir))
        if not TAM and len(liste) > 12:
            print(f"     … {len(liste) - 12} kayıt daha (--tam ile hepsi)")
        print()

    _bolum("B1 · MÜŞTERİ KİMLİĞİ BOŞ   [GEÇMİŞTE GÖRÜNMEZ]", bos,
           "müşteri kartında geçmiş olarak listelenmez",
           lambda s: f"{s[0]:<14} {s[1]:<16} musteri: {s[2] or '(boş)'}")

    _bolum("B2 · KIRIK REFERANS   [SİLİNMİŞ CARİ]", kirik,
           "cari_id dolu ama o cari kaydı yok",
           lambda s: f"{s[0]:<14} {s[1]:<16} cari_id: {s[3]}  musteri: {s[2]}")

    _bolum("B3 · İSİM ↔ KİMLİK ÇELİŞKİSİ   [bilgi]", celiski,
           "cari sonradan yeniden adlandırılmışsa NORMALDİR; kimlik esastır",
           lambda s: f"{s[0]:<14} {s[1]:<16} kayıtta: {s[2]}  →  caride: {s[3]}")

    print("═" * 70)
    if bos or kirik:
        print(" ✗ BAĞSIZ KAYIT VAR")
        print()
        if bos:
            print("   B1 için: ilgili kaydı düzenleyip müşteriyi yeniden")
            print("   seçin, ya da o adda bir cari kaydı açın. Otomatik")
            print("   doldurma yalnızca YAZILIRKEN çalışır, geçmişe dönük")
            print("   düzeltmez.")
        if kirik:
            print("   B2 için: cari silinmiş olabilir. Kayıtları elle")
            print("   doğru cariye bağlayın.")
        sys.exit(1)
    print(" ✓ HER KAYIT BİR MÜŞTERİYE BAĞLI")
    if celiski:
        print(f"   ({len(celiski)} kayıtta isim farkı var — yeniden")
        print("    adlandırma sonucu, sorun değil.)")
    print("═" * 70)

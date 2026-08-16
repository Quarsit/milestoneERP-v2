#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — TAHSİLAT/ÖDEME KASA TEŞHİSİ  (salt okunur)
#
#  ── NE İÇİN ──
#    Cari hesaba elle 'Tahsilat' ya da 'Ödeme' girilirken kasa
#    seçmek ZORUNLU DEĞİL. Seçilmezse cari bakiyesi değişir ama
#    hiçbir kasaya para girmez/çıkmaz — para iki ekran arasında
#    kaybolur.
#
#    Bu betik, kasaya bağlanmamış tahsilat/ödeme kayıtlarını
#    listeler.
#
#  ── HİÇBİR ŞEY DEĞİŞTİRMEZ ──  Sadece SELECT.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python tahsilat_kasa_teshis.py
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
    print("  'kayıt yok' raporu verirdim. Çalışmayı reddediyorum.")
    sys.exit(1)

os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
sys.path.insert(0, str(Path('.').resolve()))

import flask_app  # noqa: E402
from models import db, CariHareket, KasaHareket  # noqa: E402


def _gizle(u):
    if '@' in u and '//' in u:
        bas, son = u.split('//', 1)
        if '@' in son:
            kimlik, sunucu = son.split('@', 1)
            return f"{bas}//{kimlik.split(':')[0]}:***@{sunucu}"
    return u


def _sade(s):
    s = (s or '').strip().lower()
    for a, b in (('ı', 'i'), ('İ', 'i'), ('ğ', 'g'), ('ü', 'u'),
                 ('ş', 's'), ('ö', 'o'), ('ç', 'c')):
        s = s.replace(a, b)
    return s


NAKIT_TIPLER = ('tahsilat', 'odeme', 'avans tahsilati', 'avans odemesi')

print("═" * 70)
print(" TAHSİLAT / ÖDEME — KASA BAĞLANTISI TEŞHİSİ  (salt okunur)")
print("═" * 70)
print(f" Veritabanı : {_gizle(_URL)}")
if _URL.startswith('sqlite'):
    print(" ⚠ SQLite'a bağlanıldı — üretim PostgreSQL ise rapor anlamsız.")

with flask_app.app.app_context():
    hepsi = CariHareket.query.all()
    ilgili = [h for h in hepsi if _sade(h.islem_tip) in NAKIT_TIPLER]

    print()
    print(f"  Toplam cari hareket              : {len(hepsi)}")
    print(f"  Tahsilat / ödeme kaydı           : {len(ilgili)}")

    if not ilgili:
        print()
        print("  Tahsilat/ödeme kaydı yok — inceleyecek bir şey yok.")
        print("═" * 70)
        sys.exit(0)

    # Ayni gun + ayni tutarda kasa hareketi var mi? Cari hareket ile
    # kasa hareketi arasinda dogrudan bag YOK, bu yuzden esleme
    # tarih+tutar uzerinden YAKLASIK yapiliyor. Kesin degil —
    # bulgular elle dogrulanmali.
    baglisiz = []
    for h in ilgili:
        tutar = float(h.borc or 0) or float(h.alacak or 0)
        q = KasaHareket.query.filter(KasaHareket.tutar == tutar)
        if h.hareket_tarihi:
            q = q.filter(KasaHareket.tarih == h.hareket_tarihi)
        if not q.first():
            baglisiz.append((h, tutar))

    print(f"  Kasa karşılığı BULUNAMAYAN       : {len(baglisiz)}")

    if not baglisiz:
        print()
        print("  ✓ Her tahsilat/ödemenin bir kasa hareketi var.")
        print("    Para kasaya girmiş demektir; nakit akışında")
        print("    AÇILIŞ bakiyesinde görünür, ayrı satır olarak")
        print("    değil — çünkü zaten gerçekleşti.")
        print("═" * 70)
        sys.exit(0)

    print()
    print("─" * 70)
    print(" KASAYA BAĞLANMAMIŞ KAYITLAR")
    print("─" * 70)
    toplam = {}
    for h, tutar in baglisiz:
        d = (h.doviz or 'TRY').upper()
        yon = 'tahsilat' if float(h.alacak or 0) > 0 else 'ödeme'
        toplam[d] = toplam.get(d, 0) + tutar
        print(f"  ✗ {(h.hareket_tarihi.isoformat() if h.hareket_tarihi else '—'):<12}"
              f" {(h.cari_unvan or h.cari_id or '—')[:22]:<24}"
              f" {tutar:>12,.2f} {d:<4} {h.islem_tip or ''} ({yon})")

    print()
    print("─" * 70)
    for d in sorted(toplam):
        print(f"  {d:<5} {toplam[d]:>14,.2f}  kasaya yansımamış")
    print("─" * 70)
    print()
    print("  Bu kayıtlarda cari bakiyesi değişmiş ama para hiçbir")
    print("  kasaya girmemiş/çıkmamış. İki ihtimal:")
    print("    1) Kasa seçmeyi unuttunuz → kaydı düzeltin ya da")
    print("       silip kasa seçerek yeniden girin.")
    print("    2) Para takip edilmeyen bir banka hesabına geldi →")
    print("       o hesabı kasa olarak tanımlayın.")
    print()
    print("  NOT: eşleştirme tarih+tutar üzerinden YAKLAŞIK yapıldı;")
    print("  cari hareket ile kasa hareketi arasında doğrudan bağ yok.")
    print("  Bulguları gözle doğrulayın.")
    print("═" * 70)

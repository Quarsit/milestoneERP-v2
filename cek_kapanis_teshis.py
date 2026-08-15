#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — ÇEK KAPANIŞ TEŞHİSİ  (salt okunur)
#
#  ── NE İÇİN ──
#    Karşılıksız / iade edilen çeklerde sistem ters cari hareket
#    açmıyor. Yani çek ölse bile müşterinin borcu kapalı görünüyor.
#
#    Bu betik, VERİTABANINDA bu durumun kaç kaydı etkilediğini
#    söyler ve elle düzeltme yapılıp yapılmadığını arar.
#
#  ── HİÇBİR ŞEY DEĞİŞTİRMEZ ──
#    Sadece SELECT. Yazma yok, commit yok.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python cek_kapanis_teshis.py
#      venv/bin/python cek_kapanis_teshis.py --url=postgresql://...
#
#  BAĞLANTI: .env dosyasındaki DATABASE_URL kullanılır (sema_denetim
#  ve degismezlik_denetim ile aynı yöntem). Ortam yüklenemezse betik
#  ÇALIŞMAYI REDDEDER — sessizce boş bir SQLite dosyasına bağlanıp
#  "kayıt yok" demek, yanlış rapordan daha kötüdür.
# ══════════════════════════════════════════════════════════════════════
import os
import sys
from pathlib import Path

if not Path('flask_app.py').exists():
    print("HATA: flask_app.py bu klasörde yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

# .env YUKLE — flask_app import edilmeden ONCE olmali, cunku
# flask_app modul yuklenirken DATABASE_URL'i okuyor.
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

for _a in sys.argv[1:]:
    if _a.startswith('--url='):
        os.environ['DATABASE_URL'] = _a.split('=', 1)[1]

_URL = os.environ.get('DATABASE_URL')
if not _URL:
    print("HATA: DATABASE_URL bulunamadı.")
    print()
    print("  Bu betik ÜRETİM veritabanını okumalı. Adres olmadan")
    print("  uygulama 'sqlite:///milestone.db' varsayılanına düşer;")
    print("  o dosya boş olduğu için betik yanlışlıkla 'kayıt yok'")
    print("  raporu verirdi. Bu yüzden çalışmayı reddediyorum.")
    print()
    print("  Çözüm — biri yeterli:")
    print("    1) Proje dizininde .env dosyası:  DATABASE_URL=postgresql://...")
    print("    2) export DATABASE_URL=postgresql://...")
    print("    3) venv/bin/python cek_kapanis_teshis.py --url=postgresql://...")
    sys.exit(1)

os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
sys.path.insert(0, str(Path('.').resolve()))

import flask_app  # noqa: E402
from models import db, Cek, CariHareket, Fatura  # noqa: E402

# Hangi veritabanina baglandigimizi GOSTER — sifreyi gizleyerek.
def _gizle(u):
    if '@' in u and '//' in u:
        bas, son = u.split('//', 1)
        if '@' in son:
            kimlik, sunucu = son.split('@', 1)
            ad = kimlik.split(':')[0]
            return f'{bas}//{ad}:***@{sunucu}'
    return u

OLU_DURUMLAR = ('Karsiliksiz', 'Iade Edildi', 'Iade Alindi')

print("═" * 70)
print(" ÇEK KAPANIŞ TEŞHİSİ  (salt okunur — hiçbir şey değişmez)")
print("═" * 70)
print(f" Veritabanı : {_gizle(_URL)}")

if _URL.startswith('sqlite'):
    print()
    print(" ⚠ SQLite'a bağlanıldı. Üretim PostgreSQL ise bu YANLIŞ")
    print("   veritabanıdır ve rapor anlamsız olur. Devam etmeden")
    print("   .env dosyanızdaki DATABASE_URL'i kontrol edin.")

with flask_app.app.app_context():
    tum = Cek.query.count()
    olu = Cek.query.filter(Cek.durum.in_(OLU_DURUMLAR)).all()

    print()
    print(f"  Toplam çek/senet kaydı            : {tum}")
    print(f"  Karşılıksız / iade edilmiş        : {len(olu)}")

    if not olu:
        print()
        print("  ✓ Etkilenen kayıt YOK.")
        print("    Geçmiş veri temiz — geriye dönük düzeltme betiği")
        print("    GEREKMİYOR. Yamalar yalnızca bundan sonrasını")
        print("    kapsayacak.")
        print()
        print("═" * 70)
        sys.exit(0)

    print()
    print("─" * 70)
    print(" ETKİLENEN ÇEKLER")
    print("─" * 70)

    # UC gruba ayrilir. Ayrim onemli: geriye donuk duzeltme betigi
    # yalnizca UCUNCU gruba dokunmali.
    sistem, elle, duzeltilmemis = [], [], []
    for c in olu:
        # 1) CK2 yamasinin actigi otomatik ters hareket
        oto = CariHareket.query.filter(
            CariHareket.kaynak == 'cek_olu',
            CariHareket.baglanti_id == c.id).all()
        if oto:
            sistem.append((c, oto))
            continue
        # 2) Elle girilmis duzeltme izi (ters BORC hareketi)
        ters = CariHareket.query.filter(
            CariHareket.cari_id == c.cari_id,
            CariHareket.borc > 0,
            db.or_(CariHareket.baglanti_id == c.id,
                   CariHareket.aciklama.ilike(f'%{c.cek_no or c.id}%'),
                   CariHareket.islem_tip.ilike('%karşılıksız%'),
                   CariHareket.islem_tip.ilike('%karsiliksiz%'),
                   CariHareket.islem_tip.ilike('%iade%'))).all()
        (elle if ters else duzeltilmemis).append((c, ters))

    for c, ters in duzeltilmemis:
        f = (db.session.get(Fatura, c.fatura_id)
             if getattr(c, 'fatura_id', None) else None)
        print(f"  ✗ {(c.cek_no or c.id):<14} {float(c.tutar or 0):>12,.2f} {c.doviz or 'TRY':<4}"
              f" {c.durum:<12} {(c.cari_unvan or c.cari_id or '—')[:24]}")
        if f:
            print(f"       └ fatura {f.fatura_no or f.id} · durum: {f.durum}")

    if sistem:
        print()
        print("  Sistem düzeltmiş (CK2 yaması uygulandıktan sonra oluşmuş):")
        for c, ters in sistem:
            print(f"  ✓ {(c.cek_no or c.id):<14} {float(c.tutar or 0):>12,.2f} {c.doviz or 'TRY':<4}"
                  f" → otomatik ters hareket var, işlem gerekmiyor")

    if elle:
        print()
        print("  Elle düzeltilmiş GÖRÜNENLER (ters borç hareketi bulundu):")
        print("  ⚠ Bunları gözle teyit edin — düzeltme betiği bunlara")
        print("    DOKUNMAMALI, yoksa çift kayıt oluşur.")
        for c, ters in elle:
            print(f"  ~ {(c.cek_no or c.id):<14} {float(c.tutar or 0):>12,.2f} {c.doviz or 'TRY':<4}"
                  f" → {len(ters)} ilgili hareket")

    # Etkilenen tutarin doviz bazinda toplami
    print()
    print("─" * 70)
    print(" AÇIKTA KALAN TUTAR  (ters hareketi olmayanlar)")
    print("─" * 70)
    toplam = {}
    for c, _ in duzeltilmemis:
        d = (c.doviz or 'TRY').upper()
        toplam[d] = toplam.get(d, 0) + float(c.tutar or 0)
    if toplam:
        for d in sorted(toplam):
            print(f"  {d:<5} {toplam[d]:>14,.2f}")
    else:
        print("  yok")

    print()
    print("─" * 70)
    print(" SONUÇ")
    print("─" * 70)
    if duzeltilmemis:
        print(f"  {len(duzeltilmemis)} çek için cari bakiye OLMASI GEREKENDEN DÜŞÜK.")
        print("  Bu müşteriler borçsuz görünüyor ve risk limitleri boşta.")
        print()
        print("  → Geriye dönük düzeltme betiği GEREKİYOR.")
    if sistem:
        print(f"  {len(sistem)} çek zaten sistem tarafından düzeltilmiş (CK2).")
    if elle:
        print(f"  {len(elle)} çekte elle düzeltme izi var.")
        print("  → Bunlar düzeltme betiğinden HARİÇ tutulmalı,")
        print("    yoksa çift kayıt oluşur. Yukarıdaki listeyi")
        print("    kontrol edip teyit edin.")
    if not duzeltilmemis and not elle:
        print("  ✓ Açıkta kalan kayıt yok — geriye dönük düzeltme")
        print("    GEREKMİYOR.")
    print()
    print("═" * 70)

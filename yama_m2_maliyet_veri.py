#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — MALİYET SÜZGEÇLERİ İÇİN VERİ  ·  M2
#
#  ── BELİRTİ (gerçek veriyle) ──
#    30 plaka var, maliyet sayfasında 60 kayıt görünüyor. Ama:
#        Stok Tipi süzgeci  → "Stok Tipi (Tümü)" ve "Stok (60)"
#        Cins süzgeci       → PASİF
#        Cari süzgeci       → PASİF
#
#    Beklenen: Stok tipinde BLOK / PLAKA / EBATLI seçenekleri.
#
#  ── KÖK NEDEN: SUNUCU O ALANLARI DÖNDÜRMÜYOR ──
#    M1 yamasında süzgeçleri `baglanti_tip`, `baglanti_ad` ve
#    `cari_unvan` alanlarından besledim — ama serializer'ı
#    doğrulamadım. Gerçekte:
#
#      • `baglanti_tip` SANAL kayıtlarda sabit 'stok' yazılıyor
#        (flask_app.py:8952) — blok/plaka/ebatli ayrımı YOK.
#        Bu yüzden tek seçenek "Stok (60)" çıkıyor.
#      • `baglanti_ad` alanı HİÇ YOK → cins süzgeci boş
#      • `cari_unvan` alanı HİÇ YOK → cari süzgeci boş
#
#    Süzgeç mantığı doğruydu; beslendiği veri yoktu.
#
#  ── ÇÖZÜM: SERIALIZER'A ÜÇ ALAN ──
#      stok_tip   : BLOK / PLAKA / EBATLI  (gerçek tip)
#      cins       : stoğun cinsi
#      cari_unvan : maliyeti kesen tedarikçi
#
#    Alanlar EKLENİYOR, mevcutlar değişmiyor — `baglanti_tip`
#    olduğu gibi kalır (başka yerler ona bakıyor olabilir).
#
#  KULLANIM (proje klasöründe):
#      python yama_m2_maliyet_veri.py            # rapor
#      python yama_m2_maliyet_veri.py --uygula   # uygula
#
#  ⚠ ÖN KOŞUL: yama_m1_maliyet_suzgec.py uygulanmış olmalı.
#  Şema değişikliği YOK.
# ══════════════════════════════════════════════════════════════════════
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
APP = Path('flask_app.py')
ML = Path('templates/maliyet.html')

for d in (APP, ML):
    if not d.exists():
        print(f"HATA: {d} bulunamadı. Proje klasöründe çalıştırın.")
        sys.exit(1)

if 'mSecenekleriDoldur' not in ML.read_text(encoding='utf-8', errors='replace'):
    print("✗ ÖN KOŞUL: önce yama_m1_maliyet_suzgec.py uygulanmalı.")
    sys.exit(1)


def dogrula(kaynak, ad):
    if not ad.endswith('.py'):
        return None
    try:
        compile(kaynak, ad, 'exec')
        return None
    except SyntaxError as exc:
        return f"satır {exc.lineno}: {exc.msg}"


# ── A) Gerçek maliyet kayıtları: üç alan ekle ──────────────────────
A_ESKI = """                'maliyet_tip': m.maliyet_tip, 'baglanti_tip': m.baglanti_tip,
                'baglanti_id': m.baglanti_id,
                'baglanti_no': _okunabilir_no(m),"""

A_YENI = """                'maliyet_tip': m.maliyet_tip, 'baglanti_tip': m.baglanti_tip,
                'baglanti_id': m.baglanti_id,
                'baglanti_no': _okunabilir_no(m),
                # YAMA M2 — SUZGEC VERISI
                # Maliyet sayfasindaki Stok Tipi / Cins / Cari suzgecleri
                # bu alanlardan besleniyor. Eskiden HIC DONMUYORLARDI;
                # cins ve cari suzgecleri bos, stok tipi tek secenekliydi.
                'stok_tip': _maliyet_stok_tip(m),
                'cins': _maliyet_cins(m),
                'cari_unvan': _maliyet_cari(m),"""

# ── B) Sanal (alış bedeli) kayıtları ───────────────────────────────
B_ESKI = """                    'baglanti_tip': 'stok', 'baglanti_id': stok_id,"""
B_YENI = """                    'baglanti_tip': 'stok', 'baglanti_id': stok_id,
                    # M2: sanal kayitta GERCEK tip zaten bilgi sozlugunde
                    'stok_tip': (bilgi.get('tip') or '').upper(),
                    'cins': bilgi.get('cins') or '',
                    'cari_unvan': bilgi.get('uretici') or '',"""

# ── C) Yardımcılar ─────────────────────────────────────────────────
# _okunabilir_no, api_maliyet_liste() ICINDE ic ice tanimli (8 bosluk
# girinti). Yardimcilar da AYNI girintiyle eklenmeli; 4 boslukla
# eklemek "expected an indented block" hatasi veriyordu.
C_ESKI = """        # Stok dışı bağlantılar için okunabilir no (sipariş/fatura zaten anlamlı ID taşır)
        def _okunabilir_no(m):"""

C_YENI = '''        def _maliyet_stok_tip(m):
            """Maliyetin bagli oldugu stogun GERCEK tipi: BLOK/PLAKA/EBATLI.

            `baglanti_tip` yeterli degil: sanal kayitlarda sabit 'stok'
            yaziliyor, gerceklerde ise 'blok'/'plaka' gibi kucuk harf ya da
            'sevkiyat'/'siparis' gibi stok disi degerler olabiliyor.
            """
            bt = (getattr(m, 'baglanti_tip', '') or '').lower()
            if bt in ('blok', 'plaka', 'ebatli'):
                return bt.upper()
            if bt not in ('stok', ''):
                return ''          # sevkiyat / siparis — stok tipi yok
            # 'stok' ya da bos: kaydin kendisinden bul
            for _M, _ad in ((BlokStok, 'BLOK'), (PlakaStok, 'PLAKA'),
                            (EbatliStok, 'EBATLI')):
                try:
                    if db.session.get(_M, m.baglanti_id) is not None:
                        return _ad
                except Exception:
                    continue
            return ''

        def _maliyet_cins(m):
            """Bagli stogun cinsi. Stok disi baglantilarda bos."""
            for _M in (BlokStok, PlakaStok, EbatliStok):
                try:
                    s = db.session.get(_M, m.baglanti_id)
                    if s is not None:
                        return (getattr(s, 'cins', '') or '').strip()
                except Exception:
                    continue
            return ''

        def _maliyet_cari(m):
            """Maliyeti kesen cari. Once maliyetin kendi cari_id'si,
            yoksa bagli stogun ureticisi."""
            try:
                if getattr(m, 'cari_id', None):
                    c = db.session.get(Cari, m.cari_id)
                    if c:
                        return c.unvan or ''
            except Exception:
                pass
            for _M in (BlokStok, PlakaStok, EbatliStok):
                try:
                    s = db.session.get(_M, m.baglanti_id)
                    if s is not None:
                        return (getattr(s, 'uretici', '') or '').strip()
                except Exception:
                    continue
            return ''

        # Stok dışı bağlantılar için okunabilir no (sipariş/fatura zaten anlamlı ID taşır)
        def _okunabilir_no(m):'''

# ── D) Ön yüz: doğru alanları kullan ───────────────────────────────
D_ESKI = """  kur(m => m.baglanti_tip || '', 'mStokTip', 'Stok tipi', M_STOKTIP);"""
D_YENI = """  /* M2: `baglanti_tip` DEGIL `stok_tip`. Ilki sanal kayitlarda sabit
     'stok' yaziyordu ve tek secenek "Stok (60)" cikiyordu. */
  kur(m => m.stok_tip || '', 'mStokTip', 'Stok tipi', M_STOKTIP);"""

E_ESKI = """  kur(m => (['blok', 'plaka', 'ebatli'].includes(m.baglanti_tip || '')
            ? String(m.baglanti_ad || '').trim().split(/[\\s·#]+/)[0] : '') || '',
      'mCins', 'Cins', M_CINS);"""
E_YENI = """  /* M2: cins artik SUNUCUDAN geliyor — bağlantı adından tahmin
     etmeye gerek yok. */
  kur(m => m.cins || '', 'mCins', 'Cins', M_CINS);"""

# ── F) Süzme mantığı ───────────────────────────────────────────────
F_ESKI = """    (!M_STOKTIP || (m.baglanti_tip || '') === M_STOKTIP) &&
    (!M_CINS    || String(m.baglanti_ad || '').toLocaleUpperCase('tr')
                     .includes(M_CINS.toLocaleUpperCase('tr'))) &&"""
F_YENI = """    (!M_STOKTIP || (m.stok_tip || '') === M_STOKTIP) &&
    (!M_CINS    || (m.cins || '') === M_CINS) &&"""

BLOKLAR = [
    (APP, 'def _maliyet_stok_tip(', C_ESKI, C_YENI, 'sunucu: üç yardımcı'),
    (APP, "'stok_tip': _maliyet_stok_tip(m)", A_ESKI, A_YENI, 'sunucu: gerçek kayıtlar'),
    (APP, "'stok_tip': (bilgi.get('tip')", B_ESKI, B_YENI, 'sunucu: sanal kayıtlar'),
    (ML, "m.stok_tip || '', 'mStokTip'", D_ESKI, D_YENI, 'ön yüz: stok tipi kaynağı  [ASIL]'),
    (ML, "m.cins || '', 'mCins'", E_ESKI, E_YENI, 'ön yüz: cins kaynağı'),
    (ML, "(m.stok_tip || '') === M_STOKTIP", F_ESKI, F_YENI, 'ön yüz: süzme mantığı'),
]

print("═" * 70)
print(" M2 · MALİYET SÜZGEÇLERİ İÇİN VERİ")
print("═" * 70)
print()

icerik, crlf = {}, {}
for yol in (APP, ML):
    ham = yol.read_bytes().decode('utf-8')
    icerik[yol] = ham
    crlf[yol] = '\r\n' in ham


def uyarla(t, yol):
    return t.replace('\n', '\r\n') if crlf[yol] else t


plan, atlanan, sorunlu = [], [], []
for yol, imza, eski, yeni, aciklama in BLOKLAR:
    metin = icerik[yol]
    if uyarla(imza, yol) in metin or imza in metin:
        atlanan.append(aciklama)
        continue
    e = uyarla(eski, yol)
    adet = metin.count(e)
    if adet != 1:
        sorunlu.append((aciklama, adet))
        continue
    icerik[yol] = metin.replace(e, uyarla(yeni, yol), 1)
    plan.append(aciklama)

for a in atlanan:
    print(f"  ↷ atlandı (zaten var)  {a}")
for a in plan:
    print(f"  ✓ uygulanacak          {a}")
for a, n in sorunlu:
    print(f"  ✗ KALIP BULUNAMADI     {a}  (eşleşme: {n})")

print()
if sorunlu:
    print(f" ✗ {len(sorunlu)} blok yerleştirilemedi — HİÇBİR DOSYAYA DOKUNULMADI.")
    sys.exit(1)
if not plan:
    print(" ✓ Tüm bloklar zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

hata = dogrula(icerik[APP], APP.name)
if hata:
    print(f" ✗ {APP.name} SÖZDİZİMİ HATASI → {hata}")
    print(" Hiçbir dosyaya DOKUNULMADI.")
    sys.exit(1)
print(" ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_m2_maliyet_veri.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
for yol in (APP, ML):
    yedek = yol.with_name(f'{yol.name}.yedek-{damga}')
    shutil.copy2(yol, yedek)
    yol.write_bytes(icerik[yol].encode('utf-8'))
    print(f" ✓ {yol.name}")

print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print(" Stok Tipi süzgecinde artık BLOK / PLAKA / EBATLI görünür;")
print(" cins ve cari süzgeçleri de dolar.")
print("═" * 70)

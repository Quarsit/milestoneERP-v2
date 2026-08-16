#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — KD1 DÜZELTMESİ  ·  KD3
#
#  ── ÖN KOŞUL ──
#      yama_kd1_kasa_defteri.py --uygula
#
#  ── HATA (KD1'de benim yaptığım) ──
#    Ana kasa seçilince defter YANLIŞ mutabakatsızlık bildiriyor:
#
#        "defterden hesaplanan 1.000.000,00 ₺,
#         kasada kayıtlı 0,00 ₺. Fark 1.000.000,00 ₺"
#
#    Oysa degismezlik_denetim.py D1 kontrolü TEMİZ diyor. İkisi
#    çelişiyorsa biri yanlış — yanlış olan benim defterimdi.
#
#  ── SEBEP ──
#    Ana kasanın `Kasa.bakiye` alanı HİÇ GÜNCELLENMİYOR, 0 olarak
#    duruyor. Ana kasaya doğrudan hareket girilmiyor; gösterilen
#    bakiyesi, aynı dövizdeki alt kasaların bakiye toplamından
#    CANLI hesaplanıyor (api_kasa_liste).
#
#    Defter, hareketleri alt kasalardan topluyordu (doğru) ama
#    karşılaştırmayı ana kasanın ham `bakiye` alanıyla yapıyordu
#    (yanlış). 1.000.000 ile 0 karşılaştırılınca sahte alarm.
#
#    D1'in temiz demesinin sebebi de aynı madalyonun öteki yüzü:
#    ana kasanın kendi kasa_id'sinde hiç hareket yok, 0 = 0.
#
#  ── NEDEN CİDDİ ──
#    Sahte alarm, gerçek alarmı değersizleştirir. Defterin
#    mutabakat satırı her ana kasada kırmızı yanarsa, gün gelip
#    GERÇEK bir bakiye kayması olduğunda kimse bakmaz.
#
#  ── DÜZELTME ──
#    Kıyaslanacak bakiye tek bir yerden alınıyor:
#      · alt kasa  → kendi `bakiye` alanı
#      · ana kasa  → aynı dövizdeki alt kasaların toplamı
#    Kural api_kasa_liste ile AYNI; iki yerde farklı davranmasın.
#
#  KULLANIM (proje klasöründe):
#      python yama_kd3_ana_kasa_mutabakat.py            # rapor
#      python yama_kd3_ana_kasa_mutabakat.py --uygula
#
#  Şema değişikliği YOK.
# ══════════════════════════════════════════════════════════════════════
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
APP = Path('flask_app.py')

if not APP.exists():
    print("HATA: flask_app.py bu klasörde yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

if 'def api_kasa_defter(' not in APP.read_text(encoding='utf-8', errors='replace'):
    print("✗ ÖN KOŞUL: önce yama_kd1_kasa_defteri.py uygulanmalı.")
    sys.exit(1)

# ── A) Gerçek bakiye yardımcısı ────────────────────────────────────
A_ESKI = """    @app.route('/api/kasa/defter', methods=['GET'])"""

A_YENI = '''    def _kasa_gercek_bakiye(k):
        """Kasanin GOSTERILEN bakiyesi.

        Ana kasanin `bakiye` alani hic guncellenmiyor (0 kalir);
        ona dogrudan hareket girilmiyor, bakiyesi ayni dovizdeki alt
        kasalarin toplamindan canli hesaplaniyor. Ham alani okumak
        her ana kasada sahte mutabakatsizlik uretirdi.

        Kural api_kasa_liste ile AYNI olmali — iki yerde farkli
        davranirsa hangisinin dogru oldugu belirsizlesir.
        """
        if not bool(getattr(k, 'ana_kasa', False)):
            return q3(float(k.bakiye or 0))
        alt_q = Kasa.query.filter_by(doviz=k.doviz)
        if hasattr(Kasa, 'ana_kasa'):
            alt_q = alt_q.filter_by(ana_kasa=False)
        return q3(sum(float(a.bakiye or 0) for a in alt_q.all()))

    @app.route('/api/kasa/defter', methods=['GET'])'''

# ── B) Mutabakatta kullan ──────────────────────────────────────────
B_ESKI = """        kayitli = q3(float(k.bakiye or 0))
        beklenen = q3(float(kapanis) + sonraki)"""
B_YENI = """        kayitli = _kasa_gercek_bakiye(k)
        beklenen = q3(float(kapanis) + sonraki)"""

# ── C) Kasa bilgisinde de doğrusu görünsün ─────────────────────────
C_ESKI = """            'kasa': {'id': k.id, 'ad': k.ad, 'doviz': k.doviz,
                     'ana_kasa': bool(getattr(k, 'ana_kasa', False)),
                     'bakiye': q3(float(k.bakiye or 0))},"""
C_YENI = """            'kasa': {'id': k.id, 'ad': k.ad, 'doviz': k.doviz,
                     'ana_kasa': bool(getattr(k, 'ana_kasa', False)),
                     'bakiye': _kasa_gercek_bakiye(k)},"""

BLOKLAR = [
    ("gerçek bakiye yardımcısı", A_ESKI, A_YENI, 'def _kasa_gercek_bakiye('),
    ("mutabakat doğru bakiyeyi kullanıyor", B_ESKI, B_YENI, 'kayitli = _kasa_gercek_bakiye(k)'),
    ("kasa bilgisi doğru bakiye", C_ESKI, C_YENI, "'bakiye': _kasa_gercek_bakiye(k)},"),
]

print("═" * 70)
print(" KD3 · ANA KASA MUTABAKATI — sahte alarm düzeltmesi")
print("═" * 70)
print()

ham = APP.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


icerik = ham
plan, atlanan, sorunlu = [], [], []
for aciklama, eski, yeni, imza in BLOKLAR:
    if uyarla(imza) in icerik or imza in icerik:
        atlanan.append(aciklama)
        continue
    e = uyarla(eski)
    adet = icerik.count(e)
    if adet != 1:
        sorunlu.append((aciklama, adet))
        continue
    icerik = icerik.replace(e, uyarla(yeni), 1)
    plan.append(aciklama)

for a in atlanan:
    print(f"  ↷ atlandı (zaten var)  {a}")
for a in plan:
    print(f"  ✓ uygulanacak          {a}")
for a, n in sorunlu:
    print(f"  ✗ KALIP BULUNAMADI     {a}  (eşleşme: {n})")

print()
if sorunlu:
    print(f" ✗ {len(sorunlu)} blok yerleştirilemedi — DOSYAYA DOKUNULMADI.")
    sys.exit(1)
if not plan:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

try:
    compile(icerik, 'flask_app.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)
print(" ✓ sözdizimi doğrulandı (compile)")

# Defterde ham `k.bakiye` okuması kalmamali.
_b = icerik.split('def api_kasa_defter(')[1].split("@app.route('/api/kasa/hareket'")[0]
_kalan = [l.strip() for l in _b.split('\n')
          if 'k.bakiye' in l and not l.strip().startswith('#')]
if _kalan:
    print(" ✗ Defterde hâlâ ham k.bakiye okuması var:")
    for l in _kalan[:3]:
        print(f"     {l[:70]}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)
print(" ✓ defterde ham bakiye okuması kalmadı")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_kd3_ana_kasa_mutabakat.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = APP.with_name(f'flask_app.py.yedek-{damga}')
shutil.copy2(APP, yedek)
APP.write_bytes(icerik.encode('utf-8'))
print()
print(f" ✓ flask_app.py  (yedek: {yedek.name})")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print(" Ana kasada sahte mutabakatsızlık uyarısı kalkıyor.")
print("═" * 70)

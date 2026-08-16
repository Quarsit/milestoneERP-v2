#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — CSRF BAŞLIK BİRLEŞTİRME  ·  AP1
#
#  ── BELİRTİ ──
#    Ayarlar → Listeler → GTİP altındaki "Önerilen 5 değeri ekle"
#    düğmesi onay soruyor, onaylıyorsunuz, hiçbir şey eklenmiyor.
#    Üstelik "Öneriler eklendi" bildirimi çıkıyor.
#
#  ── KÖK SEBEP ──
#    base.html'deki `api()` yardımcısında NESNE SIRASI hatası:
#
#        fetch(yol, {
#          headers: { 'Content-Type':…, 'X-CSRF-Token':…,
#                     ...(secenek.headers || {}) },
#          ...secenek          ← BURASI
#        });
#
#    `...secenek` EN SONDA yayıldığı için, çağıran kendi `headers`
#    nesnesini geçtiyse yukarıda özenle birleştirilen başlıkların
#    TAMAMINI eziyor — X-CSRF-Token dahil. Sunucu 403 döndürüyor.
#
#    Doğrulandı:
#        CSRF ile        → HTTP 200
#        CSRF olmadan    → HTTP 403 {'error': 'csrf'}
#
#  ── NEDEN SESSİZ ──
#    Üstüne iki katman daha var:
#      · lookupOneriEkle'nin `catch` bloğu boş ("zaten varsa atla"),
#        yani 403'ü yutuyor ve sonunda "Öneriler eklendi" diyor.
#      · api(), 403/csrf görünce 1,5 sn sonra sayfayı YENİLİYOR.
#        Beş öneri = beş yenileme emri. Bunun ardından başka bir
#        listeye ekleme yapmaya çalışırsanız sayfa altınızdan
#        yenilendiği için o da kaybolur — "Mermer Cinsleri'ne
#        ekleyemiyorum" şikayeti büyük olasılıkla bunun sonucu.
#
#  ── ETKİLENEN ÇAĞRILAR ──
#    Kendi `headers`'ını geçen her yer: ayarlar.html (3), fatura.html (1).
#    stok.html'deki ikisi CSRF'i elle eklediği için çalışıyordu —
#    yani hata bir süredir oradaki elle çözümle maskeleniyordu.
#
#  ── DÜZELTME ──
#    `headers` artık nesnenin EN SONUNDA; hiçbir yayılma onu ezemez.
#    Çağıranın verdiği başlıklar birleştirilmeye devam ediyor.
#
#  KULLANIM (proje klasöründe):
#      python yama_ap1_csrf_baslik.py            # rapor
#      python yama_ap1_csrf_baslik.py --uygula
#
#  Şema değişikliği YOK.
# ══════════════════════════════════════════════════════════════════════
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
BASE = Path('templates/base.html')

if not BASE.exists():
    print("HATA: templates/base.html yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

ESKI = """async function api(yol, secenek = {}) {
  const c = await fetch(yol, {
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': window.CSRF_TOKEN,
      ...(secenek.headers || {})
    },
    ...secenek
  });"""

YENI = """async function api(yol, secenek = {}) {
  /* SIRA ÖNEMLİ — `headers` EN SONDA olmalı.
     Önceki sürümde `...secenek` en sonda yayılıyordu; çağıran kendi
     `headers` nesnesini geçtiyse birleştirilmiş başlıkların tamamını
     eziyor ve X-CSRF-Token kayboluyordu. Sunucu 403 döner, istek
     sessizce başarısız olurdu. */
  const { headers: _cagiranBaslik, ...digerSecenekler } = secenek;
  const c = await fetch(yol, {
    ...digerSecenekler,
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': window.CSRF_TOKEN,
      ...(_cagiranBaslik || {})
    }
  });"""

IMZA = '_cagiranBaslik'

print("═" * 70)
print(" AP1 · CSRF BAŞLIK BİRLEŞTİRME")
print("═" * 70)
print()

ham = BASE.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


if uyarla(IMZA) in ham or IMZA in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

e = uyarla(ESKI)
adet = ham.count(e)
if adet != 1:
    print(f" ✗ Kalıp {adet} kez bulundu (1 bekleniyordu). DOSYAYA DOKUNULMADI.")
    sys.exit(1)

icerik = ham.replace(e, uyarla(YENI), 1)

print("  ✓ uygulanacak          headers artık ezilmiyor")

# `...secenek` kalintisi kalmamali.
if uyarla('    ...secenek\n  });') in icerik or '    ...secenek\n  });' in icerik:
    print(" ✗ Eski yayılma hâlâ duruyor — DOSYAYA DOKUNULMADI.")
    sys.exit(1)
print("  ✓ eski yayılma kaldırıldı")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_ap1_csrf_baslik.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = BASE.with_name(f'base.html.yedek-{damga}')
shutil.copy2(BASE, yedek)
BASE.write_bytes(icerik.encode('utf-8'))
print()
print(f" ✓ templates/base.html  (yedek: {yedek.name})")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print(" Kendi başlığını geçen tüm çağrılar artık CSRF'i koruyor.")
print("═" * 70)

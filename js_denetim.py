#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — ŞABLON JAVASCRIPT DENETİMİ  ·  J1
#
#  NEDEN VAR:
#    Bir yama, "+ Yeni Proforma" butonunu çalışmaz hale getirdi.
#    Sebep tek bir kelimeydi:
#
#      Orijinal:  async function revizeEt(id) {
#      Kalıp   :        function revizeEt(id) {     ← 'async' yok
#
#    Kalıp eşleşti ama 'async' kelimesi ortada kaldı:
#
#      async /* yorum */
#      async function siparisedonustur(id) { ... }
#      function revizeEt(id) { ... await ... }   ← artık async DEĞİL
#
#    Sonuç: revizeEt içindeki `await` geçersiz oldu, tarayıcı SAYFADAKİ
#    TÜM JavaScript'i reddetti. Yalnızca revize düğmesi değil, sayfadaki
#    HER buton çalışmaz hale geldi — "+ Yeni Proforma" dahil.
#
#  BU HATA SINIFI NEDEN GÖZDEN KAÇAR:
#    • Python tarafı sorunsuz — compile() temiz geçer
#    • Sayfa HTTP 200 döner, ekran normal görünür
#    • Sunucu günlüğünde hiçbir iz yok
#    • form_denetim / zincir_denetim / sessiz_denetim: hepsi temiz
#    Hata YALNIZCA tarayıcı konsolunda görünür. Bir düğmeye basmadan
#    fark edilmez. "Sessiz başarı"nın ön yüz karşılığı.
#
#  NE YAPAR:
#    Her şablondaki <script> bloklarını çıkarır, Jinja ifadelerini
#    ({{ }} ve {% %}) yer tutucuyla değiştirir ve `node --check` ile
#    ayrıştırır. Sözdizimi hatası varsa dosya, satır ve mesajı verir.
#
#  ÖN KOŞUL: Node.js kurulu olmalı.
#      Windows : https://nodejs.org  (LTS)
#      Pardus  : sudo apt install nodejs
#    Node yoksa betik denge kontrolüne düşer (kaba ama boş değil).
#
#  KULLANIM (proje klasöründe):
#      python js_denetim.py
#      python js_denetim.py --dosya proforma.html
#
#  ÇIKIŞ KODU: hata varsa 1, temizse 0.
# ══════════════════════════════════════════════════════════════════════
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SABLON = Path('templates')
if not SABLON.exists():
    print("HATA: templates/ klasörü yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

TEK = None
if '--dosya' in sys.argv:
    i = sys.argv.index('--dosya')
    if i + 1 < len(sys.argv):
        TEK = sys.argv[i + 1]

NODE = shutil.which('node') or shutil.which('nodejs')

SCRIPT = re.compile(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', re.S | re.I)


def jinja_temizle(js):
    """Jinja ifadelerini JS ayrıştırıcısının kabul edeceği hale getirir.

    {{ deger }}  → "X"   (ifade yerine dize)
    {% if %}     → ''    (blok etiketi tamamen silinir)
    Bu kabalık kasıtlı: amaç Jinja'yı değil, ÇEVRESİNDEKİ JS'i
    doğrulamak. Yanlış pozitif üretirse ilgili satır elle bakılır.
    """
    js = re.sub(r'\{\{.*?\}\}', '"X"', js, flags=re.S)
    js = re.sub(r'\{%.*?%\}', '', js, flags=re.S)
    return js


def denge_kontrol(js):
    """Node yoksa kaba yedek: süslü/parantez dengesi."""
    hatalar = []
    for ac, kap, ad in (('{', '}', 'süslü parantez'),
                        ('(', ')', 'parantez'),
                        ('[', ']', 'köşeli parantez')):
        f = js.count(ac) - js.count(kap)
        if f:
            hatalar.append(f'{ad} dengesiz (fark {f:+d})')
    return hatalar


def node_kontrol(js):
    """node --check ile ayrıştır. Döner: hata metni ya da None."""
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False,
                                     encoding='utf-8') as t:
        t.write(js)
        yol = t.name
    try:
        s = subprocess.run([NODE, '--check', yol],
                           capture_output=True, text=True, timeout=30)
        if s.returncode == 0:
            return None
        satirlar = [x for x in s.stderr.splitlines() if x.strip()]
        mesaj = next((x for x in satirlar if 'Error' in x), satirlar[0] if satirlar else '')
        konum = satirlar[0] if satirlar else ''
        return f'{mesaj.strip()}  ({konum.strip()[:70]})'
    except subprocess.TimeoutExpired:
        return 'node --check zaman aşımı'
    finally:
        try:
            Path(yol).unlink()
        except OSError:
            pass


print("═" * 70)
print(" MILESTONE ERP — ŞABLON JAVASCRIPT DENETİMİ")
print("═" * 70)

dosyalar = sorted(SABLON.glob('*.html'))
if TEK:
    dosyalar = [p for p in dosyalar if p.name == TEK]
    if not dosyalar:
        print(f" HATA: templates/{TEK} bulunamadı.")
        sys.exit(1)

if NODE:
    print(f" Ayrıştırıcı : node --check  ({NODE})")
else:
    print(" Ayrıştırıcı : YOK — Node.js kurulu değil.")
    print("               Yalnızca denge kontrolü yapılacak (kaba).")
    print("               Tam kontrol için: sudo apt install nodejs")
print(f" Şablon      : {len(dosyalar)}")
print()

bulgu, betikli = 0, 0
for p in dosyalar:
    metin = p.read_text(encoding='utf-8', errors='replace')
    bloklar = SCRIPT.findall(metin)
    if not bloklar:
        continue
    betikli += 1
    js = jinja_temizle('\n'.join(bloklar))

    if NODE:
        hata = node_kontrol(js)
        if hata:
            bulgu += 1
            print("─" * 70)
            print(f" ✗ {p.name}")
            print("─" * 70)
            print(f"   {hata}")
            print()
            print("   Bu dosyadaki TÜM butonlar çalışmaz — tarayıcı betiğin")
            print("   tamamını reddeder. Sayfa yine 200 döner, hata yalnızca")
            print("   tarayıcı konsolunda görünür.")
            print()
    else:
        hatalar = denge_kontrol(js)
        if hatalar:
            bulgu += 1
            print(f" ✗ {p.name}: {', '.join(hatalar)}")



# ══════════════════════════════════════════════════════════════════
#  J2 · ONCLICK'TE TANIMSIZ FONKSİYON   [SESSİZ ÖLÜ DÜĞME]
# ══════════════════════════════════════════════════════════════════
# node --check yalnızca SÖZDİZİMİ denetler. `ciz()` diye olmayan bir
# fonksiyonu çağırmak SÖZDİZİMSEL OLARAK GEÇERLİDİR — denetim temiz
# der, ama tarayıcıda "ciz is not defined" ile çöker ve o işleyicinin
# GERİ KALANI hiç çalışmaz.
#
# H4'te tam bu yaşandı: stok süzgeçleri, seçim kutuları ve "Seçimi
# Bırak" üçü birden sessizce bozuldu; dört denetim de temiz geçmişti.
#
# Bu kontrol DAR tutuluyor: yalnızca onclick/onchange/oninput
# özniteliklerindeki doğrudan çağrılara bakar. Serbest JS gövdesini
# taramak yorum ve dize gürültüsü yüzünden yanlış alarm üretiyor.
ONCLICK_DESEN = re.compile(
    r'on(?:click|change|input|submit)\s*=\s*"([a-zA-Z_$][\w$]*)\s*\(')

def olay_isleyici_kontrol(ham_html, js):
    """onclick="fn(...)" içindeki fn tanımlı mı?"""
    tanimli = set(re.findall(r'(?:async\s+)?function\s+([\w$]+)', js))
    tanimli |= set(re.findall(r'(?:const|let|var)\s+([\w$]+)\s*=', js))
    tanimli |= set(re.findall(r'window\.([\w$]+)\s*=', js))
    # JS anahtar kelimeleri ve tarayici genelleri fonksiyon degildir
    ATLA = {'if', 'for', 'while', 'switch', 'return', 'typeof', 'new',
            'await', 'else', 'do', 'try', 'catch', 'delete', 'void',
            'alert', 'confirm', 'prompt', 'parseInt', 'parseFloat',
            'isNaN', 'isFinite', 'encodeURIComponent', 'decodeURIComponent',
            'setTimeout', 'clearTimeout', 'fetch', 'event'}
    eksik = []
    for ad in sorted(set(ONCLICK_DESEN.findall(ham_html))):
        if ad in ATLA or ad in tanimli or ad in BASE_TANIMLI:
            continue
        eksik.append(ad)
    return eksik


# base.html tüm sayfalarda yüklendiği için oradaki tanımlar geçerli
try:
    _b = (SABLON / 'base.html').read_text(encoding='utf-8', errors='replace')
    _bjs = ''.join(re.findall(r'<script[^>]*>(.*?)</script>', _b, re.S))
    BASE_TANIMLI = set(re.findall(r'(?:async\s+)?function\s+([\w$]+)', _bjs))
    BASE_TANIMLI |= set(re.findall(r'(?:const|let|var)\s+([\w$]+)\s*=', _bjs))
    BASE_TANIMLI |= set(re.findall(r'window\.([\w$]+)\s*=', _bjs))
except Exception:
    BASE_TANIMLI = set()

print()
print("─" * 70)
print(" J2 · ONCLICK'TE TANIMSIZ FONKSİYON   [SESSİZ ÖLÜ DÜĞME]")
print("─" * 70)
_j2 = 0
for p2 in sorted(SABLON.glob('*.html')):
    ham2 = p2.read_text(encoding='utf-8', errors='replace')
    js2 = ''.join(re.findall(r'<script[^>]*>(.*?)</script>', ham2, re.S))
    if not js2.strip():
        continue
    eksik2 = olay_isleyici_kontrol(ham2, jinja_temizle(js2))
    if eksik2:
        _j2 += len(eksik2)
        print(f"   ✗ {p2.name}: {', '.join(eksik2)}")
if _j2:
    print()
    print(f"   → {_j2} düğme TANIMSIZ fonksiyon çağırıyor.")
    print("   Tıklandığında sessizce hiçbir şey olmaz.")
    bulgu += _j2
else:
    print("   ✓ temiz — her olay işleyicisi tanımlı bir fonksiyon çağırıyor")

print()
print("═" * 70)
if bulgu:
    print(f" ✗ {bulgu} şablonda JavaScript hatası ({betikli} şablon tarandı)")
else:
    print(f" ✓ TEMİZ — {betikli} şablonun JavaScript'i ayrıştırılabiliyor")
print("═" * 70)
sys.exit(1 if bulgu else 0)

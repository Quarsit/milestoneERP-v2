#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — NAKİT AKIŞI  ·  NA3  (3/3: sayfa + menü)
#
#  ── ÖN KOŞUL ──
#      yama_na1_nakit_model.py --uygula   (model + sabit gider API)
#      goc.py uygula                      (nakit akisi tablolari)
#      yama_na2_projeksiyon.py --uygula   (projeksiyon motoru)
#      templates/nakit.html ve templates/sabit_gider.html yerinde olmali
#
#  ── EKLENENLER ──
#      /nakit        → projeksiyon ekrani
#      /sabit-gider  → sabit gider yonetimi
#      base.html'de DORT navigasyon blogu
#
#  ── NEDEN DORT BLOK ──
#    base.html menuyu iki ayri yerde kuruyor:
#      1. Sol ray dugmesinin "aktif" vurgusu          (~390)
#      2. Sol ray ucan menusundeki baglanti listesi   (~396)
#      3. Alt sekme cubugunun elif kosulu             (~487)
#      4. Alt sekme cubugunun sekme listesi           (~488)
#    Yalnizca 1-2 yamalanirsa /nakit sayfasinda ALT SEKME CUBUGU HIC
#    CIKMAZ — elif hicbir dala uymaz, alan_sekmeleri tanimsiz kalir.
#    Ilk taslakta bu atlanmisti; dordu birden yamaniyor.
#
#  ── YETKİ ──
#    Ikisi de 'kasa' moduluna bagli. Nakit akisi kasa bakiyelerini ve
#    tum borc/alacaklari gosterir; finans yetkisi olmayan gormemeli.
#
#  KULLANIM (proje klasöründe):
#      python yama_na3_nakit_sayfa.py            # rapor
#      python yama_na3_nakit_sayfa.py --uygula   # uygula
#
#  SONRA:  python js_denetim.py && python form_denetim.py
#  Şema değişikliği YOK.
# ══════════════════════════════════════════════════════════════════════
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv

APP = Path('flask_app.py')
BASE = Path('templates/base.html')
NAKIT = Path('templates/nakit.html')
GIDER = Path('templates/sabit_gider.html')

for d in (APP, BASE):
    if not d.exists():
        print(f"HATA: {d} bulunamadı. Proje klasöründe çalıştırın.")
        sys.exit(1)

eksik = [str(t) for t in (NAKIT, GIDER) if not t.exists()]
if eksik:
    print("✗ ÖN KOŞUL: şu şablon(lar) yok →", ", ".join(eksik))
    print("  Bu yama olmadan rotalar TemplateNotFound ile çöker.")
    sys.exit(1)

if 'api_nakit_akis' not in APP.read_text(encoding='utf-8', errors='replace'):
    print("✗ ÖN KOŞUL: önce yama_na2_projeksiyon.py uygulanmalı.")
    sys.exit(1)


def dogrula(kaynak, ad):
    if not ad.endswith('.py'):
        return None
    try:
        compile(kaynak, ad, 'exec')
        return None
    except SyntaxError as exc:
        return f"satır {exc.lineno}: {exc.msg}"


# ── A) Sayfa rotaları ──────────────────────────────────────────────
A_ESKI = """    @app.route('/maliyet')
    def maliyet_sayfa():"""

A_YENI = '''    @app.route('/nakit')
    def nakit_sayfa():
        """Nakit akisi projeksiyonu.

        YETKI: 'kasa' moduluna bagli — bu ekran kasa bakiyelerini ve
        tum borc/alacaklari gosterir, finans yetkisi olmayan gormemeli.
        """
        if _auth_required(): return _auth_required()
        if not _yetki_var_mi('kasa', 'okuma'):
            return redirect(url_for('dashboard'))
        return render_template('nakit.html')

    @app.route('/sabit-gider')
    def sabit_gider_sayfa():
        """Tekrarlayan gider sablonlari — projeksiyonun tek eksik girdisi."""
        if _auth_required(): return _auth_required()
        if not _yetki_var_mi('kasa', 'okuma'):
            return redirect(url_for('dashboard'))
        return render_template('sabit_gider.html')

    @app.route('/maliyet')
    def maliyet_sayfa():'''

# ── B) Sol ray: aktif vurgusu ──────────────────────────────────────
B_ESKI = """      <a href="/kasa" class="ray-btn {% if yol.startswith('/kasa') or yol.startswith('/cari') or yol.startswith('/cek') %}aktif{% endif %}">"""
B_YENI = """      <a href="/kasa" class="ray-btn {% if yol.startswith('/kasa') or yol.startswith('/cari') or yol.startswith('/cek') or yol.startswith('/nakit') or yol.startswith('/sabit-gider') %}aktif{% endif %}">"""

# ── C) Sol ray: uçan menü bağlantıları ─────────────────────────────
C_ESKI = """        {% for hedef, ad, modul in [('/kasa','Kasalar','kasa'), ('/cari','Cari Hesaplar','cari'), ('/cek','Çek / Senet','kasa')] %}"""
C_YENI = """        {% for hedef, ad, modul in [('/kasa','Kasalar','kasa'), ('/cari','Cari Hesaplar','cari'), ('/cek','Çek / Senet','kasa'), ('/nakit','Nakit Akışı','kasa'), ('/sabit-gider','Sabit Giderler','kasa')] %}"""

# ── D) Alt sekme çubuğu: elif koşulu ───────────────────────────────
D_ESKI = """    {% elif yol.startswith('/kasa') or yol.startswith('/cari') or yol.startswith('/cek') %}"""
D_YENI = """    {% elif yol.startswith('/kasa') or yol.startswith('/cari') or yol.startswith('/cek')
            or yol.startswith('/nakit') or yol.startswith('/sabit-gider') %}"""

# ── E) Alt sekme çubuğu: sekme listesi ─────────────────────────────
E_ESKI = """      {% set alan_sekmeleri = [('/kasa','Kasalar','kasa'), ('/cari','Cari Hesaplar','cari'),
                               ('/cek','Çek / Senet','kasa')] %}"""
E_YENI = """      {% set alan_sekmeleri = [('/kasa','Kasalar','kasa'), ('/cari','Cari Hesaplar','cari'),
                               ('/cek','Çek / Senet','kasa'), ('/nakit','Nakit Akışı','kasa'),
                               ('/sabit-gider','Sabit Giderler','kasa')] %}"""

BLOKLAR = [
    (APP,  "def nakit_sayfa(",                    A_ESKI, A_YENI, 'sayfa rotaları (/nakit, /sabit-gider)'),
    (BASE, "yol.startswith('/sabit-gider') %}aktif", B_ESKI, B_YENI, 'sol ray · aktif vurgusu'),
    (BASE, "('/nakit','Nakit Akışı','kasa'), ('/sabit-gider'", C_ESKI, C_YENI, 'sol ray · uçan menü'),
    # DIKKAT: bu imza B_YENI ile CAKISMAMALI. B tek satirda
    # "or yol.startswith('/nakit')" iceriyor; ayirt edici olan, satir
    # basindaki 12 boslukla gelen devam satiri.
    (BASE, "\n            or yol.startswith('/nakit')", D_ESKI, D_YENI, 'alt sekme · koşul'),
    (BASE, "('/nakit','Nakit Akışı','kasa'),\n                               ('/sabit-gider'", E_ESKI, E_YENI, 'alt sekme · liste'),
]

print("═" * 70)
print(" NA3 · NAKİT AKIŞI  (3/3: sayfa + menü)")
print("═" * 70)
print()

icerik, crlf = {}, {}
for yol in (APP, BASE):
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
    print("   python yama_na3_nakit_sayfa.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
for yol in (APP, BASE):
    yedek = yol.with_name(f'{yol.name}.yedek-{damga}')
    shutil.copy2(yol, yedek)
    yol.write_bytes(icerik[yol].encode('utf-8'))
    print(f" ✓ {yol.name}")

print()
print("═" * 70)
print(" ✓ TAMAMLANDI  (3/3)")
print()
print(" Finans menüsünde 'Nakit Akışı' ve 'Sabit Giderler' görünür.")
print(" SONRA:  venv/bin/python js_denetim.py")
print("         venv/bin/python form_denetim.py")
print("═" * 70)

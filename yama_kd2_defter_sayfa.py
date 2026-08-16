#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — KASA DEFTERİ  ·  KD2  (2/2: sayfa + menü)
#
#  ── ÖN KOŞUL ──
#      yama_kd1_kasa_defteri.py --uygula
#      templates/kasa_defter.html yerinde olmali
#
#  ── EKLENENLER ──
#      /kasa-defteri  → defter ekrani
#      base.html'de DORT navigasyon blogu (NA3 ile ayni yerler)
#
#  ── DORT BLOK ──
#    base.html menuyu iki ayri yerde kuruyor: sol ray (vurgu +
#    ucan menu) ve alt sekme cubugu (kosul + liste). NA3'te
#    yalnizca ikisi yamalanmis, alt sekme cubugu atlanmisti; ayni
#    hataya dusmemek icin dordu birden.
#
#  ── YETKİ ──
#    'kasa' moduluna bagli — defter kasa bakiyelerini ve cari
#    baglantilarini gosterir.
#
#  KULLANIM (proje klasöründe):
#      python yama_kd2_defter_sayfa.py            # rapor
#      python yama_kd2_defter_sayfa.py --uygula
#
#  Şema değişikliği YOK.
# ══════════════════════════════════════════════════════════════════════
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
APP = Path('flask_app.py')
BASE = Path('templates/base.html')
SAYFA = Path('templates/kasa_defter.html')

for d in (APP, BASE):
    if not d.exists():
        print(f"HATA: {d} bulunamadı. Proje klasöründe çalıştırın.")
        sys.exit(1)
if not SAYFA.exists():
    print("✗ ÖN KOŞUL: templates/kasa_defter.html yok.")
    print("  Bu yama olmadan rota TemplateNotFound ile çöker.")
    sys.exit(1)
if 'api_kasa_defter' not in APP.read_text(encoding='utf-8', errors='replace'):
    print("✗ ÖN KOŞUL: önce yama_kd1_kasa_defteri.py uygulanmalı.")
    sys.exit(1)


# ── A) Sayfa rotası ────────────────────────────────────────────────
A_ESKI = """    @app.route('/nakit')
    def nakit_sayfa():"""

A_YENI = '''    @app.route('/kasa-defteri')
    def kasa_defter_sayfa():
        """Kasa defteri — devir + yuruyen bakiyeli hareket dokumu."""
        if _auth_required(): return _auth_required()
        if not _yetki_var_mi('kasa', 'okuma'):
            return redirect(url_for('dashboard'))
        return render_template('kasa_defter.html')

    @app.route('/nakit')
    def nakit_sayfa():'''

# ── B) Sol ray: aktif vurgusu ──────────────────────────────────────
B_ESKI = """      <a href="/kasa" class="ray-btn {% if yol.startswith('/kasa') or yol.startswith('/cari') or yol.startswith('/cek') or yol.startswith('/nakit') or yol.startswith('/sabit-gider') %}aktif{% endif %}">"""
B_YENI = """      <a href="/kasa" class="ray-btn {% if yol.startswith('/kasa') or yol.startswith('/cari') or yol.startswith('/cek') or yol.startswith('/nakit') or yol.startswith('/sabit-gider') or yol.startswith('/kasa-defteri') %}aktif{% endif %}">"""

# ── C) Sol ray: uçan menü ──────────────────────────────────────────
C_ESKI = """('/nakit','Nakit Akışı','kasa'), ('/sabit-gider','Sabit Giderler','kasa')] %}"""
C_YENI = """('/kasa-defteri','Kasa Defteri','kasa'), ('/nakit','Nakit Akışı','kasa'), ('/sabit-gider','Sabit Giderler','kasa')] %}"""

# ── D) Alt sekme çubuğu: koşul ─────────────────────────────────────
D_ESKI = """            or yol.startswith('/nakit') or yol.startswith('/sabit-gider') %}"""
D_YENI = """            or yol.startswith('/nakit') or yol.startswith('/sabit-gider')
            or yol.startswith('/kasa-defteri') %}"""

# ── E) Alt sekme çubuğu: liste ─────────────────────────────────────
E_ESKI = """                               ('/cek','Çek / Senet','kasa'), ('/nakit','Nakit Akışı','kasa'),
                               ('/sabit-gider','Sabit Giderler','kasa')] %}"""
E_YENI = """                               ('/cek','Çek / Senet','kasa'),
                               ('/kasa-defteri','Kasa Defteri','kasa'),
                               ('/nakit','Nakit Akışı','kasa'),
                               ('/sabit-gider','Sabit Giderler','kasa')] %}"""

BLOKLAR = [
    (APP,  "sayfa rotası (/kasa-defteri)", A_ESKI, A_YENI, 'def kasa_defter_sayfa('),
    (BASE, "sol ray · aktif vurgusu",      B_ESKI, B_YENI, "yol.startswith('/kasa-defteri') %}aktif"),
    (BASE, "sol ray · uçan menü",          C_ESKI, C_YENI, "('/kasa-defteri','Kasa Defteri','kasa'), ('/nakit'"),
    (BASE, "alt sekme · koşul",            D_ESKI, D_YENI, "\n            or yol.startswith('/kasa-defteri') %}"),
    (BASE, "alt sekme · liste",            E_ESKI, E_YENI, "\n                               ('/kasa-defteri','Kasa Defteri','kasa'),"),
]

print("═" * 70)
print(" KD2 · KASA DEFTERİ  (2/2: sayfa + menü)")
print("═" * 70)
print()

icerik, crlf = {}, {}
for yol in (APP, BASE):
    _t = yol.read_bytes().decode('utf-8')
    icerik[yol] = _t
    crlf[yol] = '\r\n' in _t


def uyarla(t, yol):
    return t.replace('\n', '\r\n') if crlf[yol] else t


plan, atlanan, sorunlu = [], [], []
for yol, aciklama, eski, yeni, imza in BLOKLAR:
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
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

try:
    compile(icerik[APP], 'flask_app.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" HİÇBİR DOSYAYA DOKUNULMADI.")
    sys.exit(1)
print(" ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_kd2_defter_sayfa.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
for yol in (APP, BASE):
    yedek = yol.with_name(f'{yol.name}.yedek-{damga}')
    shutil.copy2(yol, yedek)
    yol.write_bytes(icerik[yol].encode('utf-8'))
    print(f" ✓ {yol.name}")

print()
print("═" * 70)
print(" ✓ TAMAMLANDI  (2/2)")
print()
print(" Finans menüsünde 'Kasa Defteri' görünür.")
print("═" * 70)

#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — TOPLU SİLMEYE MALİ SEÇİM  ·  SF3
#
#  ── ÖLÇÜLEN HATA (üretimde görüldü) ──
#    Toplu silme `api_stok_sil()`'i tek tek cagiriyor. SF1'den sonra
#    faturaya bagli her stok icin 409 (secim iste) donuyor; toplu
#    silme bunu "atlandi" sayiyor ve HICBIRI silinmiyor.
#
#    SF1 tekli silmeyi duzeltirken toplu silmeyi kirdi. Ayni uc
#    noktayi cagiran ikinci bir yol oldugunu gozden kacirdim.
#
#  ── DÜZELTME ──
#    Toplu silme istegi de `mali_islem` alabiliyor ve alt cagriya
#    GECIRIYOR. Secim gelmezse, faturaya bagli stoklar icin 409
#    donuyor — tekli silmedeki kural birebir ayni.
#
#  ── NEDEN ALT ÇAĞRIYA "request" ÜZERİNDEN GEÇMİYOR ──
#    `api_stok_sil` secimi `request`ten okuyor; toplu silmede her
#    kalem icin ayri istek YOK. Bu yuzden fonksiyona parametre
#    olarak veriliyor ve `request` yalnizca parametre gelmediginde
#    okunuyor. Boylece tekli cagri davranisi degismiyor.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python yama_sf3_toplu_mali.py            # rapor
#      venv/bin/python yama_sf3_toplu_mali.py --uygula
#
#  ⚠ templates/stok.html güncellenmeli.
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

_h = APP.read_text(encoding='utf-8', errors='replace')
if 'MALİ KARAR KULLANICIYA AİT  (SF1)' not in _h:
    print("✗ ÖN KOŞUL: önce yama_sf1_stok_fatura_ayrim.py uygulanmalı.")
    sys.exit(1)

# ── A) api_stok_sil parametre alsın ────────────────────────────────
A_ESKI = """    def api_stok_sil(tip, stok_id):"""
A_YENI = """    def api_stok_sil(tip, stok_id, mali_islem=None):"""

# ── B) Parametre öncelikli okuma ───────────────────────────────────
B_ESKI = """        _govde = request.get_json(silent=True) or {}
        _mali = _govde.get('mali_islem') or request.args.get('mali_islem')"""

B_YENI = """        # SF3: TOPLU silmede her kalem icin ayri istek YOK; secim
        # parametre olarak gelir. Parametre yoksa (tekli silme)
        # istekten okunur — tekli davranis degismez.
        if mali_islem:
            _mali = mali_islem
        else:
            _govde = request.get_json(silent=True) or {}
            _mali = _govde.get('mali_islem') or request.args.get('mali_islem')"""

# ── C) Toplu silme seçimi okusun ve geçirsin ───────────────────────
C_ESKI = """        for sid in idler:
            try:
                sonuc = api_stok_sil(tip, sid)"""

C_YENI = """        # SF3: mali secim toplu silmede de gecerli. Gelmezse alt
        # cagri faturaya bagli stoklarda 409 doner ve o kalem
        # atlanir — tekli silmedeki kuralla ayni.
        _toplu_mali = ((request.get_json(silent=True) or {}).get('mali_islem')
                       or request.args.get('mali_islem') or None)

        for sid in idler:
            try:
                sonuc = api_stok_sil(tip, sid, mali_islem=_toplu_mali)"""

# ── D) 409'u ayrı raporla ──────────────────────────────────────────
D_ESKI = """                else:
                    atlanan.append({'stok_id': sid,
                                    'sebep': govde.get('mesaj') or f'HTTP {kod}'})"""

D_YENI = """                elif kod == 409:
                    # Mali secim gerekiyor — HATA DEGIL, SORU.
                    # Ayri sayilir ki kullaniciya "secim yapin" denebilsin.
                    secim_bekleyen.append({
                        'stok_id': sid, 'fatura_no': govde.get('fatura_no'),
                        'pay': govde.get('pay'), 'doviz': govde.get('doviz'),
                        'secenekler': govde.get('secenekler')})
                else:
                    atlanan.append({'stok_id': sid,
                                    'sebep': govde.get('mesaj') or f'HTTP {kod}'})"""

E_ESKI = """        for sid in idler:
            try:
                sonuc = api_stok_sil(tip, sid, mali_islem=_toplu_mali)"""
E_YENI = """        secim_bekleyen = []
        for sid in idler:
            try:
                sonuc = api_stok_sil(tip, sid, mali_islem=_toplu_mali)"""

BLOKLAR = [
    ("api_stok_sil parametresi", A_ESKI, A_YENI, 'def api_stok_sil(tip, stok_id, mali_islem=None)'),
    ("parametre öncelikli okuma", B_ESKI, B_YENI, 'SF3: TOPLU silmede her kalem icin ayri istek YOK'),
    ("toplu silme seçimi geçirsin", C_ESKI, C_YENI, '_toplu_mali = ((request.get_json'),
    ("409 ayrı raporlansın", D_ESKI, D_YENI, 'secim_bekleyen.append({'),
    ("secim_bekleyen başlatma", E_ESKI, E_YENI, 'secim_bekleyen = []'),
]

print("═" * 70)
print(" SF3 · TOPLU SİLMEYE MALİ SEÇİM")
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

# Yanıta secim_bekleyen ekle
# Gercek yanit bicimi: silinen/atlanan SAYI olarak doner, detay ayri.
F_ESKI = uyarla("""        return jsonify({'ok': True, 'silinen': len(silinen),
                        'atlanan': len(atlanan), 'atlanan_detay': atlanan,""")
F_YENI = uyarla("""        return jsonify({'ok': True, 'silinen': len(silinen),
                        'atlanan': len(atlanan), 'atlanan_detay': atlanan,
                        # SF3: mali secim bekleyenler AYRI — hata degil, soru.
                        'secim_bekleyen': secim_bekleyen,""")
if uyarla("'secim_bekleyen': secim_bekleyen,") in icerik:
    atlanan.append("yanıta secim_bekleyen")
elif icerik.count(F_ESKI) == 1:
    icerik = icerik.replace(F_ESKI, F_YENI, 1)
    plan.append("yanıta secim_bekleyen")
else:
    sorunlu.append(("yanıta secim_bekleyen", icerik.count(F_ESKI)))

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

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   venv/bin/python yama_sf3_toplu_mali.py --uygula")
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
print(" ⚠ templates/stok.html güncellenmeli (toplu silmede seçim penceresi).")
print("═" * 70)

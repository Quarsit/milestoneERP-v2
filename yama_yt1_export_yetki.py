#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — DIŞA AKTARMA YETKİSİ  ·  YT1
#
#  ── AÇIK ──
#    /api/export/<modul> YALNIZCA oturum kontrolü yapıyor:
#
#        def api_export(modul):
#            if _auth_required(): return ... 401
#            # ...modül yetkisine BAKILMIYOR
#
#    Sonuç: 'fatura' yetkisi kapalı bir kullanıcı fatura sayfasını
#    açamıyor ama fatura listesini Excel olarak İNDİREBİLİYOR.
#    Ekranda gizlenen veri dosya olarak dışarı çıkıyor.
#
#    NA4'te nakit çıktılarına açık kontrol konmuştu; kalan 13 modül
#    hâlâ açıktaydı. Bu yama hepsini kapatıyor.
#
#  ── EŞLEME UYDURULMADI ──
#    Her modülün yetki adı, o modülün KENDİ SAYFA ROTASINDAN okundu:
#
#        /fatura      → _yetki_var_mi('fatura', ...)
#        /cek         → _yetki_var_mi('kasa', ...)     ← dikkat
#        /cari        → _yetki_var_mi('cari', ...)
#        ...
#
#    'cek' modülü 'kasa' yetkisine bağlı; tahmin edilseydi 'cek'
#    yazılırdı ve öyle bir yetki modülü YOK — kontrol sessizce
#    yanlış çalışırdı.
#
#  ── FAIL-CLOSED ──
#    Tablo bir sözlük; bilinmeyen modül için varsayılan 'kasa'
#    DEĞİL, ERİŞİM YOK. Yani ileride yeni bir export modülü eklenip
#    tabloya yazılmazsa, açıkta kalmaz — kapalı kalır ve fark edilir.
#    Sessizce açılan bir kapı, gürültüyle kapanan kapıdan kötüdür.
#
#  ── NAKİT MODÜLLERİ ──
#    NA4'te branşların içine konan kontroller DURUYOR. Çift kontrol
#    zararsız (ikisi de 'kasa' okuma) ve kaldırmak gereksiz risk.
#
#  KULLANIM (proje klasöründe):
#      python yama_yt1_export_yetki.py            # rapor
#      python yama_yt1_export_yetki.py --uygula   # uygula
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


def dogrula(kaynak):
    try:
        compile(kaynak, 'flask_app.py', 'exec')
        return None
    except SyntaxError as exc:
        return f"satır {exc.lineno}: {exc.msg}"


A_ESKI = """    @app.route('/api/export/<modul>', methods=['GET'])
    def api_export(modul):
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        try:
            from export_utils import liste_xlsx, liste_pdf"""

A_YENI = '''    # Disa aktarma modulu → yetki modulu.
    #
    # Her satir, o modulun KENDI SAYFA ROTASINDAKI kontrolden
    # okundu; tahmin edilmedi. Ozellikle 'cek' → 'kasa': tahmin
    # edilseydi 'cek' yazilirdi, oyle bir yetki modulu yok ve
    # kontrol sessizce yanlis calisirdi.
    EXPORT_YETKI = {
        'siparis': 'siparis',
        'fatura': 'fatura',
        'cek': 'kasa',
        'cari': 'cari',
        'cari_hareket': 'cari',
        'stok': 'stok',
        'proforma': 'proforma',
        'sevkiyat': 'sevkiyat',
        'satislar': 'satislar',
        'karlilik': 'karlilik',
        'maliyet': 'maliyet',
        'kesim': 'kesim',
        'rezervasyon': 'rezervasyon',
        'denetim': 'denetim',
        'nakit': 'kasa',
        'nakit_detay': 'kasa',
        'sabit_gider': 'kasa',
    }

    @app.route('/api/export/<modul>', methods=['GET'])
    def api_export(modul):
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401

        # YETKI: ekranda gizlenen veri dosya olarak disari cikmasin.
        # Onceden burada YALNIZCA oturum kontrolu vardi; fatura
        # yetkisi kapali bir kullanici fatura listesini indirebiliyordu.
        #
        # FAIL-CLOSED: tabloda olmayan modul icin varsayilan yetki
        # YOK. Ileride yeni bir export modulu eklenip tabloya
        # yazilmazsa acikta kalmaz — kapali kalir ve hemen fark
        # edilir.
        _yetki = EXPORT_YETKI.get(modul)
        if not _yetki:
            return jsonify({'ok': False,
                            'mesaj': f'Bilinmeyen modül: {modul}'}), 400
        if not _yetki_var_mi(_yetki, 'okuma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403

        try:
            from export_utils import liste_xlsx, liste_pdf'''

print("═" * 70)
print(" YT1 · DIŞA AKTARMA YETKİSİ")
print("═" * 70)
print()

ham = APP.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


if 'EXPORT_YETKI = {' in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

e = uyarla(A_ESKI)
adet = ham.count(e)
if adet != 1:
    print(f" ✗ Kalıp {adet} kez bulundu (1 bekleniyordu). DOSYAYA DOKUNULMADI.")
    sys.exit(1)

icerik = ham.replace(e, uyarla(A_YENI), 1)

hata = dogrula(icerik)
if hata:
    print(f" ✗ SÖZDİZİMİ HATASI → {hata}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

# Tablodaki her modul, dagiticida GERCEKTEN var mi? Yoksa olmayan
# bir modul icin yetki tanimlamis oluruz — sessiz yanlislik.
import re

_dag = set(re.findall(r"modul == '([a-z_]+)'", icerik))
_dag |= set(re.findall(r"modul in \(([^)]*)\)", icerik) and
            re.findall(r"'([a-z_]+)'", ' '.join(
                re.findall(r"modul in \(([^)]*)\)", icerik))) or [])
_tablo = set(re.findall(r"^        '([a-z_]+)': '[a-z_]+',", icerik, re.M))

_fazla = _tablo - _dag
_eksik = _dag - _tablo

print(f"  dağıtıcıdaki modül : {len(_dag)}")
print(f"  tablodaki modül    : {len(_tablo)}")
if _fazla:
    print(f" ✗ Tabloda olup dağıtıcıda OLMAYAN: {sorted(_fazla)}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)
if _eksik:
    print(f" ✗ Dağıtıcıda olup tabloda OLMAYAN: {sorted(_eksik)}")
    print("   Bu modüller 400 dönerdi. DOSYAYA DOKUNULMADI.")
    sys.exit(1)
print("  ✓ tablo ile dağıtıcı birebir örtüşüyor")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_yt1_export_yetki.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = APP.with_name(f'flask_app.py.yedek-{damga}')
shutil.copy2(APP, yedek)
APP.write_bytes(icerik.encode('utf-8'))
print()
print(f" ✓ flask_app.py  (yedek: {yedek.name})")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI — 17 dışa aktarma modülünün hepsi yetkiye bağlı")
print("═" * 70)

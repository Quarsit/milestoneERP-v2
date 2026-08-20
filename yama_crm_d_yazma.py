#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — YAZMA KORUMASI  ·  CRM-D
#
#  ── ÖN KOŞUL ──
#      yama_crm_c2_kuresel.py --uygula
#
#  ── ÖLÇÜLEN DURUM ──
#    Kuresel okuma suzgeci, KAYIT ARAYAN yazma uclarini da zaten
#    koruyor. Olculdu — `ali`, `ayse`'nin kayitlarina:
#
#        PUT    /api/cari/C2            -> 404
#        PUT    /api/proforma/P2        -> 404
#        PUT    /api/fatura/F2          -> 404
#        DELETE /api/proforma/P2        -> 404
#        DELETE /api/cari/hareket/H2    -> 404
#
#    Hicbir kayit degismedi. Cunku uc noktalar once `query.get()`
#    yapiyor ve gorunmeyen kayit BULUNAMIYOR. Denetim aracinin
#    "60 uc acik" uyarisi bu yuzden buyuk olcude YANLIS ALARMDI —
#    yalnizca acik suzgec cagrisi ariyordu, ortuk korumayi degil.
#
#  ── GERÇEK BOŞLUK: OLUŞTURMA ──
#    Olculdu: `ali`, GORMEDIGI musteri adina proforma acabiliyor.
#
#        POST /api/proforma {"musteri": "AYSE MUS"}  -> 200
#
#    CRM-A dinleyicisi cari_id'yi otomatik doldurdugu icin kayit
#    `ayse`'nin musterisine yaziliyor. `ali` sonra onu goremiyor
#    bile; `ayse` ise acmadigi bir proforma buluyor.
#
#  ── ÇÖZÜM ──
#    Yine tek yerde: cari_id'yi dolduran `before_insert` dinleyicisi
#    artik GORUNURLUGU de denetliyor. Kullanicinin goremedigi bir
#    musteri adina kayit acilamaz.
#
#    Uc nokta basina kontrol yazilmadi — 11 olusturma noktasi var ve
#    12.'si eklendiginde unutulurdu. Dinleyici ileride eklenecek
#    kodu da kendiliginden kapsar.
#
#  ── TEMİZ HATA ──
#    Dinleyici `ErisimHatasi` firlatiyor; Flask hata isleyicisi bunu
#    403 + anlasilir mesaja ceviriyor. Aksi halde kullanici 500
#    gorurdu ve neyin yanlis oldugunu anlamazdi.
#
#  ── SİSTEM İŞLEMLERİ ──
#    `erisim_atla()` icinde kontrol yapilmaz: proformadan faturaya
#    donusum, toplu islemler ve gorevler engellenmemeli.
#
#  KULLANIM (proje klasöründe):
#      python yama_crm_d_yazma.py            # rapor
#      python yama_crm_d_yazma.py --uygula
#
#  Şema değişikliği YOK.
# ══════════════════════════════════════════════════════════════════════
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
MOD = Path('models.py')
APP = Path('flask_app.py')

for _d in (MOD, APP):
    if not _d.exists():
        print(f"HATA: {_d} bu klasörde yok. Proje klasöründe çalıştırın.")
        sys.exit(1)

if '_erisim_suzgeci' not in APP.read_text(encoding='utf-8', errors='replace'):
    print("✗ ÖN KOŞUL: önce yama_crm_c2_kuresel.py uygulanmalı.")
    sys.exit(1)

# ══ models.py: dinleyiciye görünürlük denetimi ═════════════════════
M_ESKI = '''def cari_id_otomatik_doldur(mapper, connection, target):
    if getattr(target, 'cari_id', None):
        return
    unvan = (getattr(target, 'musteri', None) or '').strip()
    if not unvan:
        return
    try:
        r = connection.execute(
            _text('SELECT id FROM cariler WHERE unvan = :u LIMIT 1'),
            {'u': unvan}).fetchone()
        if r:
            target.cari_id = r[0]
    except Exception:
        # Baglanti cozulmezse kayit YINE DE yazilir; eksik bag
        # denetimle bulunur, veri kaybi olmaz.
        pass'''

M_YENI = '''class ErisimHatasi(Exception):
    """Kullanicinin GORMEDIGI bir musteri adina kayit acilmaya
    calisildi. flask_app bunu 403'e cevirir."""


def cari_id_otomatik_doldur(mapper, connection, target):
    if not getattr(target, 'cari_id', None):
        unvan = (getattr(target, 'musteri', None) or '').strip()
        if unvan:
            try:
                r = connection.execute(
                    _text('SELECT id FROM cariler WHERE unvan = :u LIMIT 1'),
                    {'u': unvan}).fetchone()
                if r:
                    target.cari_id = r[0]
            except Exception:
                # Baglanti cozulmezse kayit YINE DE yazilir; eksik bag
                # denetimle bulunur, veri kaybi olmaz.
                pass

    # ── GORUNURLUK DENETIMI (CRM-D) ──
    # Olculdu: kullanici GORMEDIGI musteri adina kayit acabiliyordu.
    # Kayit o musteriye yaziliyor; acan kisi sonra goremiyor,
    # sorumlu satisci ise acmadigi bir belge buluyor.
    #
    # Kontrol 11 olusturma noktasina tek tek yazilmadi: 12.'si
    # eklendiginde unutulurdu. Dinleyici ileride eklenecek kodu da
    # kendiliginden kapsar.
    cid = getattr(target, 'cari_id', None)
    if not cid:
        return                      # bagsiz kayit — crm_bag_denetim yakalar
    kontrol = globals().get('_erisim_kontrol_kancasi')
    if kontrol is None:
        return                      # flask_app henuz baglamadi (CLI, goc)
    if not kontrol(cid):
        raise ErisimHatasi(
            'Bu müşteri adına kayıt açma yetkiniz yok. '
            'Müşteri size kapalı; sorumlusundan erişim isteyin.')'''

# ══ flask_app.py: kancayı bağla + hata işleyici ════════════════════
A_ESKI = """    # ---------- API: CARİ VE HAREKETLER ----------"""

A_YENI = '''    # ── YAZMA KORUMASI KANCASI  (CRM-D) ──
    # models.py'deki before_insert dinleyicisi, gorunurlugu bilmek
    # icin bu kancayi cagirir. Kural TEK YERDE kalsin diye mantik
    # burada; models.py yalnizca cagirir.
    def _erisim_kontrol_kancasi(cari_id):
        if not has_request_context():
            return True                      # CLI, gorev, goc
        if getattr(g, 'erisim_atla_bayrak', False):
            return True                      # sistem islemi
        if (session.get('rol') or '').upper() == 'ADMIN':
            return True
        if not session.get('kullanici'):
            return True                      # _auth_required zaten engeller
        return _cari_gorulebilir_mi(cari_id)

    import models as _models_modulu
    _models_modulu._erisim_kontrol_kancasi = _erisim_kontrol_kancasi

    @app.errorhandler(_models_modulu.ErisimHatasi)
    def _erisim_hatasi_isle(hata):
        # Temiz 403 — aksi halde kullanici 500 gorur ve neyin yanlis
        # oldugunu anlamaz.
        db.session.rollback()
        return jsonify({'ok': False, 'mesaj': str(hata)}), 403

    # ---------- API: CARİ VE HAREKETLER ----------'''

print("═" * 70)
print(" CRM-D · YAZMA KORUMASI")
print("═" * 70)
print()

mham = MOD.read_bytes().decode('utf-8')
aham = APP.read_bytes().decode('utf-8')
mcrlf, acrlf = '\r\n' in mham, '\r\n' in aham


def um(t):
    return t.replace('\n', '\r\n') if mcrlf else t


def ua(t):
    return t.replace('\n', '\r\n') if acrlf else t


# HER IKI DOSYA AYRI kontrol edilir.
# Onceki surum yalnizca models.py'ye bakiyordu: models uygulanip
# flask_app atlanmis bir durumda "zaten uygulanmis" deyip cikiyor,
# yazma korumasi SESSIZCE devre disi kaliyordu.
_m_var = 'class ErisimHatasi' in mham
_a_var = '_erisim_kontrol_kancasi' in aham
if _m_var and _a_var:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)
if _m_var != _a_var:
    print(f"  ⚠ YARIM UYGULANMIŞ: models.py={_m_var} flask_app.py={_a_var}")
    print("    Eksik olan taraf tamamlanacak.")


if not _m_var:
    if um(M_ESKI) not in mham:
        print(" ✗ models.py kalıbı bulunamadı. HİÇBİR DOSYAYA DOKUNULMADI.")
        sys.exit(1)
    myeni = mham.replace(um(M_ESKI), um(M_YENI), 1)
else:
    myeni = mham
if not _a_var:
    if ua(A_ESKI) not in aham or aham.count(ua(A_ESKI)) != 1:
        print(" ✗ flask_app.py kalıbı bulunamadı. HİÇBİR DOSYAYA DOKUNULMADI.")
        sys.exit(1)
    ayeni = aham.replace(ua(A_ESKI), ua(A_YENI), 1)
else:
    ayeni = aham

for kaynak, ad in ((myeni, 'models.py'), (ayeni, 'flask_app.py')):
    try:
        compile(kaynak.replace('\r\n', '\n'), ad, 'exec')
    except SyntaxError as exc:
        print(f" ✗ {ad} SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
        print(" HİÇBİR DOSYAYA DOKUNULMADI.")
        sys.exit(1)

print("  ✓ models.py     görünürlük denetimi + ErisimHatasi")
print("  ✓ flask_app.py  kanca + 403 hata işleyici")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_crm_d_yazma.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
for yol, icerik in ((MOD, myeni), (APP, ayeni)):
    yedek = yol.with_name(f'{yol.name}.yedek-{damga}')
    shutil.copy2(yol, yedek)
    yol.write_bytes(icerik.encode('utf-8'))
    print(f" ✓ {yol.name}")

print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print(" Görmediğiniz müşteri adına kayıt açılamaz.")
print("═" * 70)

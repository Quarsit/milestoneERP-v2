#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — CRM'İ FİNANSTAN AYIR  ·  CRM-G
#
#  ── SORUN (tasarım hatası, benim) ──
#    CRM'i `cari` YETKISINE bagladim. Sonucu:
#
#      · Satisci takipleri gormek icin `cari` yetkisi almak zorunda
#        — o yetki ayni zamanda finansal cari hareketleri, bakiyeyi,
#        tahsilat/odeme girisini aciyor. Satisciya finansal islem
#        yetkisi vermek istemiyoruz.
#
#      · Finans ekibi `cari` yetkisi oldugu icin gormesi gerekmeyen
#        gorusme notlarini, temas gecmisini goruyor.
#
#    Menu yerlesimi (Takipler'in Finans altinda olmasi) bunun
#    yalnizca gorunen yuzuydu; kok sebep yetki bagiydi.
#
#  ── ÇÖZÜM ──
#    Ayri bir `crm` yetki modulu. Ayni Cari kaydina IKI MERCEK:
#      · `cari` → finansal mercek (bakiye, hareket, tahsilat)
#      · `crm`  → satis mercegi (kisiler, temas, takip)
#
#    Kayit tek; kopyalanmiyor. Yalnizca kimin neyi gordugu ayriliyor.
#
#  ── ⚠ MEVCUT KULLANICILAR ──
#    Sistem kurali: "kayitli yetki JSON'i varsa, tanimsiz modul ->
#    gizli". Yani bu yama uygulandiktan sonra HICBIR kullanici
#    (admin haric) CRM'i goremez.
#
#    Bu KASITLI ve dogru: yeni modul kendiliginden acilmamali. Ama
#    uyguladiktan sonra Ayarlar > Kullanicilar'dan satis ekibine
#    `crm` yetkisi VERMENIZ gerekiyor, yoksa Takipler menusu
#    kimsede gorunmez.
#
#  ── MENÜ ──
#    Takipler, Finans'tan Satis grubuna tasindi.
#
#  KULLANIM (proje klasöründe):
#      python yama_crm_g_ayir.py            # rapor
#      python yama_crm_g_ayir.py --uygula
#
#  ⚠ templates/ayarlar.html ve templates/cari.html güncellenmeli.
#  Şema değişikliği YOK.
# ══════════════════════════════════════════════════════════════════════
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
APP = Path('flask_app.py')
BASE = Path('templates/base.html')

for _d in (APP, BASE):
    if not _d.exists():
        print(f"HATA: {_d} bulunamadı. Proje klasöründe çalıştırın.")
        sys.exit(1)

if 'def api_takipler(' not in APP.read_text(encoding='utf-8', errors='replace'):
    print("✗ ÖN KOŞUL: önce yama_crm_e2_api.py uygulanmalı.")
    sys.exit(1)

print("═" * 70)
print(" CRM-G · CRM'İ FİNANSTAN AYIR")
print("═" * 70)
print()

aham = APP.read_bytes().decode('utf-8')
bham = BASE.read_bytes().decode('utf-8')
acrlf, bcrlf = '\r\n' in aham, '\r\n' in bham


def ua(t):
    return t.replace('\n', '\r\n') if acrlf else t


def ub(t):
    return t.replace('\n', '\r\n') if bcrlf else t


# Idempotens imzasi: bu yamanin kendi urettigi BENZERSIZ metin.
# Ilk surumde imza cok darsa yama uygulanmis dosyayi tanimiyor ve
# "kalip bulunamadi" ile duruyordu.
if 'CRM_YOL_DESENLERI' in aham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

aicerik = aham

# ── 1) Yetki modülü listesi ──
Y_ESKI = """                       'satislar', 'raporlar', 'kasa', 'kesim', 'ayarlar', 'denetim']"""
Y_YENI = """                       'satislar', 'raporlar', 'kasa', 'kesim', 'ayarlar', 'denetim',
                       # CRM ayri modul: satisci takip/temas gorsun diye
                       # finansal `cari` yetkisi almak zorunda kalmasin,
                       # finans ekibi de gorusme notlarini gormesin.
                       'crm']"""
if ua(Y_ESKI) not in aicerik:
    print(" ✗ YETKI_MODULLERI kalıbı bulunamadı. DOSYAYA DOKUNULMADI.")
    sys.exit(1)
aicerik = aicerik.replace(ua(Y_ESKI), ua(Y_YENI), 1)
print("  ✓ yetki modülü          'crm' eklendi")

# ── 2) CRM uçlarını 'cari' yerine 'crm'e bağla ──
# CRM blogu, api_aktivite_liste ile api_erisim_sil arasinda.
_bas = aicerik.find(ua("    def _crm_cari_al(cari_id):"))
_son = aicerik.find(ua("    # ---------- API: CARİ VE HAREKETLER ----------"), _bas)
if _bas < 0 or _son < 0:
    print(" ✗ CRM bloğu sınırları bulunamadı. DOSYAYA DOKUNULMADI.")
    sys.exit(1)
_blok = aicerik[_bas:_son]
_sayi = _blok.count("_yetki_var_mi('cari'")
if _sayi == 0:
    print(" ✗ CRM bloğunda 'cari' yetki kontrolü yok. DOSYAYA DOKUNULMADI.")
    sys.exit(1)
_blok_yeni = _blok.replace("_yetki_var_mi('cari'", "_yetki_var_mi('crm'")
aicerik = aicerik[:_bas] + _blok_yeni + aicerik[_son:]
print(f"  ✓ CRM uç noktaları      {_sayi} kontrol 'cari' → 'crm'")

# ── 3) /takipler sayfası ──
T_ESKI = """        if not _yetki_var_mi('cari', 'okuma'):
            return redirect(url_for('dashboard'))
        return render_template('takipler.html')"""
T_YENI = """        if not _yetki_var_mi('crm', 'okuma'):
            return redirect(url_for('dashboard'))
        return render_template('takipler.html')"""
if ua(T_ESKI) not in aicerik:
    print(" ✗ /takipler yetki kalıbı bulunamadı. DOSYAYA DOKUNULMADI.")
    sys.exit(1)
aicerik = aicerik.replace(ua(T_ESKI), ua(T_YENI), 1)
print("  ✓ /takipler sayfası     'crm' yetkisine bağlandı")

# ── 3b) Yol → modül eşlemesi ──
#  URL_MODUL_MAP ONEK tabanli ve ilk eslesen kazaniyor. CRM uclari
#  `/api/cari/<id>/aktivite` bicimindeki yollari kullaniyor ve
#  `/api/cari` onekine takilip 'cari' modulune baglaniyorlar —
#  yani uc noktada 'crm' yazsa bile YOL KONTROLU 'cari' istiyor.
#
#  Olculdu: satisciya (crm var, cari yok) temas kaydi 403 donuyordu:
#    "Modul: cari (mevcut: gizli)"
#
#  Ayirt edici kisim yolun ORTASINDA, onekle cozulmuyor. Bu yuzden
#  onek haritasindan ONCE bakilan desen listesi eklendi.
D_ESKI = """    URL_MODUL_MAP = ["""
D_YENI = """    # CRM yollari — ONEK haritasindan ONCE bakilir.
    # `/api/cari/<id>/aktivite` gibi yollarda ayirt edici kisim
    # ORTADA oldugu icin onek eslemesi yetmiyor; onek haritasi
    # bunlari 'cari' sanip satisciyi engelliyordu.
    import re as _re_modul
    CRM_YOL_DESENLERI = [
        (_re_modul.compile(r'^/api/cari/[^/]+/(aktivite|kisi|erisim)/?$'), 'crm'),
        (_re_modul.compile(r'^/api/(aktivite|kisi|erisim)(/|$)'), 'crm'),
        (_re_modul.compile(r'^/api/takipler(/|$)'), 'crm'),
    ]

    URL_MODUL_MAP = ["""
if ua(D_ESKI) not in aicerik:
    print(" ✗ URL_MODUL_MAP kalıbı bulunamadı. DOSYAYA DOKUNULMADI.")
    sys.exit(1)
aicerik = aicerik.replace(ua(D_ESKI), ua(D_YENI), 1)
print("  ✓ yol eşlemesi          CRM desenleri eklendi")

# Ayni kalip IKI YERDE var: OKUMA ve YAZMA korumasi. Ilk surumde
# yalnizca ilki degistirilmisti; okuma tarafi hala onek haritasina
# bakip CRM uclarini 'cari' saniyordu ve satisci aktivite LISTESINI
# goremiyordu (yazabiliyor ama okuyamiyor — sacma bir durum).
E_ESKI = """        modul = None
        for prefix, m in URL_MODUL_MAP:"""
E_YENI = """        modul = None
        # CRM desenleri ONCE: onek haritasi `/api/cari/...` yollarini
        # 'cari' sanip CRM uclarini engelliyordu.
        for _desen, _m in CRM_YOL_DESENLERI:
            if _desen.match(request.path):
                modul = _m
                break
        for prefix, m in URL_MODUL_MAP:
            if modul:
                break"""
_n = aicerik.count(ua(E_ESKI))
if _n < 2:
    print(f" ✗ Yol kontrolü kalıbı {_n} kez bulundu (2 bekleniyordu).")
    print("   OKUMA ve YAZMA korumalarının ikisi de gerekli.")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)
aicerik = aicerik.replace(ua(E_ESKI), ua(E_YENI))
print(f"  ✓ yol kontrolü          {_n} yerde (okuma + yazma)")

try:
    compile(aicerik, 'flask_app.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" HİÇBİR DOSYAYA DOKUNULMADI.")
    sys.exit(1)

# ── 4) Menü: Takipler Finans'tan Satış'a ──
bicerik = bham
M_ESKI = """('/cari','Cari Hesaplar','cari'), ('/takipler','Takipler','cari'), ('/cek','Çek / Senet','kasa')"""
M_YENI = """('/cari','Cari Hesaplar','cari'), ('/cek','Çek / Senet','kasa')"""
if ub(M_ESKI) in bicerik:
    bicerik = bicerik.replace(ub(M_ESKI), ub(M_YENI), 1)
    print("  ✓ menü                  Takipler Finans'tan çıkarıldı")

S_ESKI = """('/sevkiyat','Sevkiyat','sevkiyat'), ('/satislar','Satışlar','satislar')] %}"""
S_YENI = """('/sevkiyat','Sevkiyat','sevkiyat'), ('/satislar','Satışlar','satislar'), ('/takipler','Takipler','crm')] %}"""
if ub(S_ESKI) not in bicerik:
    print(" ✗ Satış menü kalıbı bulunamadı. HİÇBİR DOSYAYA DOKUNULMADI.")
    sys.exit(1)
bicerik = bicerik.replace(ub(S_ESKI), ub(S_YENI), 1)
print("  ✓ menü                  Takipler Satış grubuna eklendi")

# Sol ray: Satis vurgusuna /takipler
R_ESKI = """or yol.startswith('/satislar') or yol.startswith('/sevkiyat') %}aktif{% endif %}\">"""
R_YENI = """or yol.startswith('/satislar') or yol.startswith('/sevkiyat') or yol.startswith('/takipler') %}aktif{% endif %}\">"""
if ub(R_ESKI) in bicerik:
    bicerik = bicerik.replace(ub(R_ESKI), ub(R_YENI), 1)
    print("  ✓ menü                  sol ray Satış vurgusu")

# Finans alt sekme kosulundan /takipler cikar
F_ESKI = """            or yol.startswith('/kasa-defteri') or yol.startswith('/takipler') %}"""
F_YENI = """            or yol.startswith('/kasa-defteri') %}"""
if ub(F_ESKI) in bicerik:
    bicerik = bicerik.replace(ub(F_ESKI), ub(F_YENI), 1)
    print("  ✓ menü                  Finans alt sekmesinden çıkarıldı")

L_ESKI = """                               ('/takipler','Takipler','cari'),\n"""
if ub(L_ESKI) in bicerik:
    bicerik = bicerik.replace(ub(L_ESKI), '', 1)
    print("  ✓ menü                  Finans sekme listesinden çıkarıldı")

# Satis alt sekme: kosul + liste
SK_ESKI = """    {% if yol.startswith('/siparis') or yol.startswith('/proforma') or yol.startswith('/fatura')"""
SK_YENI = """    {% if yol.startswith('/takipler') or yol.startswith('/siparis') or yol.startswith('/proforma') or yol.startswith('/fatura')"""
if ub(SK_ESKI) in bicerik:
    bicerik = bicerik.replace(ub(SK_ESKI), ub(SK_YENI), 1)
    print("  ✓ menü                  Satış alt sekme koşulu")

print()
print(" ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_crm_g_ayir.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
for yol, icerik in ((APP, aicerik), (BASE, bicerik)):
    yedek = yol.with_name(f'{yol.name}.yedek-{damga}')
    shutil.copy2(yol, yedek)
    yol.write_bytes(icerik.encode('utf-8'))
    print(f" ✓ {yol.name}")

print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print(" ⚠ HİÇ KİMSE (admin hariç) CRM'i GÖREMEZ.")
print("   Sistem kuralı: kayıtlı yetki JSON'ı olan kullanıcıda")
print("   tanımsız modül 'gizli' sayılır. Yeni modül kendiliğinden")
print("   açılmamalı — bu doğru davranış.")
print()
print("   Ayarlar → Kullanıcılar'dan satış ekibine 'CRM' yetkisi")
print("   verin, yoksa Takipler menüsü kimsede görünmez.")
print("═" * 70)

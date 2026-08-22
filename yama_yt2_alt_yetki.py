#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — ALT İŞLEV YETKİLERİ  ·  YT2 (motor)
#
#  ── İHTİYAÇ ──
#    Bir kullanicinin modulun BIR BOLUMUNE erisip digerine
#    erisememesi gerekebilir. Ornek: satis destek elemani faturalari
#    GORSUN ama TAHSILAT GIREMESIN; ya da cari kartini duzeltsin ama
#    finansal hareket ekleyemesin.
#
#    Bugun yetki yalnizca MODUL duzeyinde: 'fatura' ya tamamen acik
#    ya tamamen kapali.
#
#  ── TASARIM: ALT YETKİ = İSTEĞE BAĞLI GEÇERSİZ KILMA ──
#    Yetki JSON'i boyle gorunur:
#
#        {"fatura": "yazma", "fatura.tahsilat": "okuma"}
#
#    · Modul anahtari VARSAYILANI belirler
#    · Nokta iceren anahtar o alt islevi GECERSIZ KILAR
#    · Tanimsiz alt islev modulu MIRAS ALIR
#
#    Bu yuzden MEVCUT DAVRANIS HIC DEGISMEZ: kimse alt yetki
#    tanimlamadigi surece sistem bugunku gibi calisir. Geriye donuk
#    uyumluluk, bu buyuklukte bir degisiklikte en onemli sart.
#
#  ── ALT İŞLEVLER KODDAN ÇIKARILDI ──
#    Uydurulmadi; her modulun GERCEK uc noktalari incelenip dogal
#    ayrim noktalari alindi. Ornegin fatura modulunde kayit,
#    tahsilat ve iptal ayri risk tasiyan islemler; sevkiyat
#    modulunde boyle bir ayrim yok, o yuzden alt islevi de yok.
#
#  ── YOL EŞLEMESİ ──
#    URL_MODUL_MAP bir yolu module esliyordu; artik once ALT ISLEV
#    desenlerine bakiliyor. Eslesen yol 'fatura.tahsilat' anahtarini
#    alir; o anahtar tanimli degilse 'fatura'ya duser. Yani desen
#    eklemek tek basina hicbir seyi kisitlamaz.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python yama_yt2_alt_yetki.py            # rapor
#      venv/bin/python yama_yt2_alt_yetki.py --uygula
#
#  ⚠ templates/ayarlar.html'in GÜNCEL sürümü de kopyalanmalı.
#  Şema değişikliği YOK — mevcut JSON sütununa yazılıyor.
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
if 'CRM_YOL_DESENLERI' not in _h:
    print("✗ ÖN KOŞUL: önce yama_crm_g_ayir.py uygulanmalı.")
    sys.exit(1)

# ── A) Alt işlev tanımları + çözümleyici ───────────────────────────
A_ESKI = """    def _yetki_var_mi(modul, seviye='okuma'):"""

A_YENI = '''    # ══════════════════════════════════════════════════════════
    #  ALT İŞLEV YETKİLERİ  (YT2)
    #
    #  Alt islevler KODDAN cikarildi; her modulun gercek uc
    #  noktalari incelenip DOGAL ayrim noktalari alindi. Ayrimi
    #  olmayan modul (sevkiyat, kesim...) burada YOK — yapay
    #  bolme, kullaniciya anlamsiz secenek gostermek olurdu.
    # ══════════════════════════════════════════════════════════
    ALT_YETKILER = {
        'cari': [
            ('cari.kayit', 'Müşteri kartı (ekle / düzenle / sil)'),
            ('cari.hareket', 'Finansal hareket, bakiye, ekstre'),
        ],
        'fatura': [
            ('fatura.kayit', 'Fatura oluşturma ve düzenleme'),
            ('fatura.tahsilat', 'Tahsilat girişi'),
            ('fatura.iptal', 'Fatura silme / iptal'),
        ],
        'proforma': [
            ('proforma.kayit', 'Teklif oluşturma ve düzenleme'),
            ('proforma.durum', 'Durum değiştirme, kayıp kaydı'),
            ('proforma.donusum', 'Siparişe / faturaya dönüştürme'),
        ],
        'kasa': [
            ('kasa.tanim', 'Kasa ve banka tanımlama'),
            ('kasa.hareket', 'Kasa giriş / çıkış'),
            ('kasa.virman', 'Kasalar arası virman'),
        ],
        'stok': [
            ('stok.kayit', 'Stok girişi ve düzenleme'),
            ('stok.cikis', 'Stok çıkışı / hurda'),
        ],
        'ayarlar': [
            ('ayarlar.firma', 'Firma bilgileri, logo, SMTP'),
            ('ayarlar.liste', 'Listeler (cins, yüzey, ülke...)'),
            ('ayarlar.kullanici', 'Kullanıcı ve yetki yönetimi'),
        ],
    }

    # Yol → alt islev. Onek haritasindan ONCE bakilir.
    # Bir yolun burada olmasi TEK BASINA kisitlama getirmez: alt
    # yetki tanimlanmamissa modul seviyesine duser.
    import re as _re_alt
    ALT_YOL_DESENLERI = [
        (_re_alt.compile(r'^/api/fatura/[^/]+/tahsilat'), 'fatura.tahsilat'),
        (_re_alt.compile(r'^/api/tahsilat'), 'fatura.tahsilat'),
        (_re_alt.compile(r'^/api/fatura/[^/]+/?$'), 'fatura.kayit'),
        (_re_alt.compile(r'^/api/cari/hareket'), 'cari.hareket'),
        (_re_alt.compile(r'^/api/cari/[^/]+/(bakiye|hareketler|ekstre)'), 'cari.hareket'),
        (_re_alt.compile(r'^/api/cari/finansal_ozet'), 'cari.hareket'),
        (_re_alt.compile(r'^/api/proforma/[^/]+/(durum|kaybedildi|kaybi_geri_al|revize)'),
         'proforma.durum'),
        (_re_alt.compile(r'^/api/proforma/[^/]+/\\w*donustur'), 'proforma.donusum'),
        (_re_alt.compile(r'^/api/kasa/virman'), 'kasa.virman'),
        (_re_alt.compile(r'^/api/kasa/hareket'), 'kasa.hareket'),
        (_re_alt.compile(r'^/api/kasa/[^/]+/hareket'), 'kasa.hareket'),
        (_re_alt.compile(r'^/api/stok/cikis'), 'stok.cikis'),
        (_re_alt.compile(r'^/api/ayarlar/kullanici'), 'ayarlar.kullanici'),
        (_re_alt.compile(r'^/api/ayarlar/(firma|logo|smtp)'), 'ayarlar.firma'),
        (_re_alt.compile(r'^/api/(ayarlar/)?lookup'), 'ayarlar.liste'),
    ]

    def _yetki_seviye(anahtar):
        """Bir modul ya da alt islev icin gecerli seviye.

        ALT YETKI = ISTEGE BAGLI GECERSIZ KILMA:
          · 'fatura.tahsilat' tanimliysa o kullanilir
          · tanimli degilse 'fatura' seviyesine DUSER

        Bu yuzden alt yetki tanimlanmadigi surece davranis
        BUGUNKUYLE AYNI kalir.
        """
        yetkiler = _kullanici_yetkileri()
        if anahtar in yetkiler:
            return yetkiler[anahtar]
        if '.' in anahtar:
            return yetkiler.get(anahtar.split('.', 1)[0], 'gizli')
        return yetkiler.get(anahtar, 'gizli')

    def _yetki_var_mi(modul, seviye='okuma'):'''

# ── B) _yetki_var_mi alt işlevi çözsün ─────────────────────────────
B_ESKI = """        yetkiler = _kullanici_yetkileri()
        mevcut = yetkiler.get(modul, 'gizli')
        if seviye == 'yazma':
            return mevcut == 'yazma'
        return mevcut in ('okuma', 'yazma')"""

B_YENI = """        # Alt islev anahtari ('fatura.tahsilat') verildiginde once
        # kendisi, yoksa modul seviyesi kullanilir.
        mevcut = _yetki_seviye(modul)
        if seviye == 'yazma':
            return mevcut == 'yazma'
        return mevcut in ('okuma', 'yazma')"""

# ── C) Yol kontrolü alt işlevi bulsun ──────────────────────────────
C_ESKI = """        modul = None
        # CRM desenleri ONCE: onek haritasi `/api/cari/...` yollarini
        # 'cari' sanip CRM uclarini engelliyordu.
        for _desen, _m in CRM_YOL_DESENLERI:
            if _desen.match(request.path):
                modul = _m
                break"""

C_YENI = """        modul = None
        # CRM desenleri ONCE: onek haritasi `/api/cari/...` yollarini
        # 'cari' sanip CRM uclarini engelliyordu.
        for _desen, _m in CRM_YOL_DESENLERI:
            if _desen.match(request.path):
                modul = _m
                break
        # ALT ISLEV desenleri: eslesirse 'fatura.tahsilat' gibi bir
        # anahtar doner. O anahtar tanimli degilse _yetki_seviye
        # modul seviyesine duser — yani desen eklemek TEK BASINA
        # hicbir seyi kisitlamaz.
        if not modul:
            for _desen, _m in ALT_YOL_DESENLERI:
                if _desen.match(request.path):
                    modul = _m
                    break"""

# ── G) KAYDETME alt yetkileri korusun ──
#  `temiz_yetki` yalnizca MODUL anahtarlarini yaziyordu; ekran
#  'fatura.tahsilat' gonderse bile KAYITTA DUSUYORDU. Arayuz
#  bosuna calisirdi.
#
#  Alt anahtarlar da dogrulanarak eklenir: gecersiz seviye ya da
#  tanimsiz alt islev SESSIZCE atlanir — istemciden gelen serbest
#  metnin yetki sozlugune girmesine izin verilmez.
G_ESKI = """        # Özel yetki: proforma iç onay (çift kontrol için ayrı bayrak)
        if gelen_yetki.get('proforma_onay'):
            temiz_yetki['proforma_onay'] = True"""
G_YENI = """        # ALT ISLEV YETKILERI (YT2) — istege bagli gecersiz kilma.
        # Yalnizca ALT_YETKILER'de TANIMLI anahtarlar kabul edilir;
        # istemciden gelen serbest metin yetki sozlugune giremez.
        _gecerli_alt = {a for _liste in ALT_YETKILER.values()
                        for a, _ in _liste}
        for _k, _v in gelen_yetki.items():
            if _k in _gecerli_alt and _v in ('gizli', 'okuma', 'yazma'):
                temiz_yetki[_k] = _v

        # Özel yetki: proforma iç onay (çift kontrol için ayrı bayrak)
        if gelen_yetki.get('proforma_onay'):
            temiz_yetki['proforma_onay'] = True"""

# ── F) Alt islev listesini EKRANA ver ──
#  Liste ekranda ikinci kez yazilsaydi PARALEL GERCEK olurdu:
#  sunucuya alt islev eklenir, ekran bilmez; ya da tersi. Bu
#  projede o hata sinifinin bes ornegini duzelttik. Tek kaynak
#  ALT_YETKILER; ekran onu sunucudan alir.
F_ESKI = """        return render_template('ayarlar.html')"""
F_YENI = """        return render_template('ayarlar.html', alt_yetkiler=ALT_YETKILER)"""

# ── E) Alt yetkiler sozlukten DUSMESIN ──
#  `_kullanici_yetkileri` sonucu MODUL anahtarlariyla yeniden
#  kuruyordu:
#      return {m: kayitli.get(m, 'gizli') for m in YETKI_MODULLERI}
#  Nokta iceren alt anahtarlar ('fatura.tahsilat') bu adimda
#  ELENIYORDU; kayitta duruyor ama coumleyiciye hic ulasmiyordu.
#  Olculdu: alt yetki 'gizli' yazilmasina ragmen tahsilat aciliyordu.
E_ESKI = """        return {m: kayitli.get(m, 'gizli') for m in YETKI_MODULLERI}"""
E_YENI = """        _sonuc = {m: kayitli.get(m, 'gizli') for m in YETKI_MODULLERI}
        # ALT YETKILER KORUNUR (YT2). Ustteki sozluk kavramasi
        # yalnizca MODUL anahtarlarini aliyordu; 'fatura.tahsilat'
        # gibi alt anahtarlar sessizce eleniyor ve kisitlama hic
        # uygulanmiyordu.
        for _k, _v in kayitli.items():
            if '.' in _k and _v in ('gizli', 'okuma', 'yazma'):
                _sonuc[_k] = _v
        return _sonuc"""

# ── D) Yol korumaları da MIRAS uygulasin ──
#  Okuma ve yazma korumalari `_kullanici_yetkileri()` sozlugunu
#  DOGRUDAN okuyordu; o sozlukte yalnizca MODUL anahtarlari var.
#  Yol 'cari.hareket'e cozulunce sozlukte bulunamiyor ve 'gizli'
#  sayiliyordu — alt yetki tanimlamamis ESKI kullanicilar bile
#  engelleniyordu. Olculdu: modul yetkisi 'yazma' olan kullanici
#  /api/cari/C1/bakiye'de 403 aliyordu.
#
#  Cozumleyiciden gecmeli ki tanimsiz alt islev modulu MIRAS ALSIN.
D_ESKI = """            yetkiler = _kullanici_yetkileri()
            mevcut = yetkiler.get(modul, 'gizli')"""
D_YENI = """            mevcut = _yetki_seviye(modul)"""

BLOKLAR = [
    ("alt yetkiler sözlükte korunsun",    E_ESKI, E_YENI, '# ALT YETKILER KORUNUR (YT2)'),
    ("alt işlev listesi ekrana",          F_ESKI, F_YENI, 'alt_yetkiler=ALT_YETKILER'),
    ("kaydetme alt yetkileri korusun",    G_ESKI, G_YENI, '_gecerli_alt = {a for _liste'),
    ("alt işlev tanımları + çözümleyici", A_ESKI, A_YENI, 'ALT_YETKILER = {'),
    ("_yetki_var_mi alt işlev çözsün",    B_ESKI, B_YENI, 'mevcut = _yetki_seviye(modul)'),
]

print("═" * 70)
print(" YT2 · ALT İŞLEV YETKİLERİ (motor)")
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

# D bloğu OKUMA ve YAZMA korumalarında AYRI AYRI var.
_d = uyarla(D_ESKI)
_nd = icerik.count(_d)
if _nd == 0 and icerik.count(uyarla("mevcut = _yetki_seviye(modul)")) >= 3:
    atlanan.append("yol korumaları miras (okuma + yazma)")
elif _nd != 2:
    sorunlu.append(("yol korumaları miras (2 bekleniyordu)", _nd))
else:
    icerik = icerik.replace(_d, uyarla(D_YENI))
    plan.append("yol korumaları miras (okuma + yazma)")

# C bloğu OKUMA ve YAZMA korumalarında AYRI AYRI var.
if 'ALT_YOL_DESENLERI:' in icerik and icerik.count(uyarla('for _desen, _m in ALT_YOL_DESENLERI')) >= 2:
    atlanan.append("yol kontrolü (okuma + yazma)")
else:
    _c = uyarla(C_ESKI)
    _n = icerik.count(_c)
    if _n != 2:
        sorunlu.append((f"yol kontrolü (2 bekleniyordu)", _n))
    else:
        icerik = icerik.replace(_c, uyarla(C_YENI))
        plan.append("yol kontrolü (okuma + yazma)")

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
    print("   venv/bin/python yama_yt2_alt_yetki.py --uygula")
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
print(" MEVCUT DAVRANIŞ DEĞİŞMEDİ — alt yetki tanımlanmadığı sürece")
print(" her şey modül seviyesinden miras alınır.")
print("═" * 70)

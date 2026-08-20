#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — PROFORMA AKIŞ DÜZELTMELERİ  ·  PF1
#
#  Akis kontrolunde bulunan uc kopukluk. Sirasi ONEM sirasi:
#  once veri butunlugunu bozan, sonra gecikmeli coken, en son
#  olcum eksigi.
#
#  ══ 1 · ELLE "FATURALANDI" ZINCIRI ATLIYOR  [VERI BUTUNLUGU] ══
#    Olculdu:
#        Onaylandi → durum='Faturalandi' → HTTP 200
#          proforma durum : Faturalandi
#          siparis_id     : None
#          Siparis kaydi  : 0
#          Fatura kaydi   : 0
#
#    Proforma "faturalandi" gorunuyor ama NE SIPARIS NE FATURA var.
#    api_proforma_faturaya siparisi sart kosuyor ve dogru uyariyor;
#    ama durum degistirme ucu bu kontrolu yapmiyordu ve gecis
#    haritasinda Onaylandi → Faturalandi dogrudan izinliydi.
#
#    Raporlari SESSIZCE bozar: faturalandi sayilan ama karsiligi
#    olmayan proformalar.
#
#    DUZELTME: 'Faturalandi' artik ELLE secilemez. O durumu yalnizca
#    sistem yazar — fatura "Kesildi" yapildiginda (flask_app:5741).
#    Ayni mantik 'Revize' icin zaten uygulanmisti; tutarli hale
#    getirildi.
#
#  ══ 2 · urun_tip ASIMETRISI  [GECIKMELI COKME] ══
#        ProformaKalem.urun_tip → serbest (nullable)
#        SiparisKalem.urun_tip  → NOT NULL
#        arada dogrulama        → yok
#
#    Urun tipi bos bir kalemle proforma SORUNSUZ kaydediliyor. Hata
#    haftalar sonra, siparise donustururken cikiyor:
#        IntegrityError: NOT NULL constraint failed:
#                        siparis_kalem.urun_tip  → HTTP 500
#
#    Kullanici 500 goruyor, sebebini anlamiyor; oysa sorun proformayi
#    kaydettigi anda olusmus. Hata GECIKTIGI yerde degil DOGDUGU
#    yerde cikmali.
#
#    DUZELTME: proforma kaydinda urun_tip zorunlu ve gecerli
#    degerlerle sinirli.
#
#  ══ 3 · SIPARISE DONUSEN PROFORMA BELLI DEGIL  [OLCUM] ══
#    Olculdu: donusum p.siparis_id yaziyor ama p.durum'a HIC
#    dokunmuyor. Cevap bekleyen teklif ile KAZANILMIS teklif listede
#    ayni gorunuyor; "kac teklif verdik, kaci siparise dondu"
#    sorusu cevaplanamiyor.
#
#    DUZELTME: yeni durum 'Siparise Donustu'. Donusumde otomatik
#    atanir, elle secilemez (kazanildi isaretini elle atmak, olcumu
#    anlamsizlastirirdi).
#
#  ── AYRICA ──
#    `_proformayi_siparise_baglava` → `_proformayi_siparise_baglama`
#    (tatli adi yazilmis; islevsel etkisi yok, iki yerde geciyor).
#
#  KULLANIM (proje klasöründe):
#      python yama_pf1_akis.py            # rapor
#      python yama_pf1_akis.py --uygula
#
#  Şema değişikliği YOK — 'Siparise Donustu' mevcut String sütuna
#  yazılıyor.
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

# ══ 1) Geçiş haritası + elle Faturalandi engeli ════════════════════
A_ESKI = """            'Taslak':       ['Ic Onay', 'Iptal'],
            'Ic Onay':      ['Onaylandi', 'Taslak', 'Iptal'],
            'Onaylandi':    ['Gonderildi', 'Faturalandi', 'Ic Onay', 'Iptal'],
            'Gonderildi':   ['Faturalandi', 'Onaylandi', 'Iptal'],
            'Faturalandi':  ['Iptal'],
            'Iptal':        ['Taslak'],  # Tekrar acmak icin
            'Revize':       []           # Arsiv — durum degistirilemez (salt okunur)
        }"""

A_YENI = """            'Taslak':          ['Ic Onay', 'Iptal'],
            'Ic Onay':         ['Onaylandi', 'Taslak', 'Iptal'],
            # 'Faturalandi' ELLE HEDEF DEGIL — asagida engelleniyor.
            'Onaylandi':       ['Gonderildi', 'Ic Onay', 'Iptal'],
            'Gonderildi':      ['Onaylandi', 'Iptal'],
            # Siparise donusen proforma: kazanildi. Buradan yalnizca
            # iptal edilebilir; fatura zinciri siparis uzerinden isler.
            'Siparise Donustu': ['Iptal'],
            'Faturalandi':     ['Iptal'],
            'Iptal':           ['Taslak'],  # Tekrar acmak icin
            'Revize':          []           # Arsiv — salt okunur
        }"""

# ── Elle atanamayacak durumlar ──
B_ESKI = """        mevcut = p.durum or 'Taslak'
        if yeni_durum == 'Revize':"""

B_YENI = """        mevcut = p.durum or 'Taslak'

        # SISTEM DURUMLARI — elle secilemez.
        #
        # 'Faturalandi': olculdu ki elle atanabiliyordu ve proforma
        #   "faturalandi" gorunurken ne siparis ne fatura vardi
        #   (siparis_id=None, Siparis=0, Fatura=0). Raporlari sessizce
        #   bozuyordu. Bu durumu yalnizca sistem yazar: fatura
        #   "Kesildi" yapildiginda.
        #
        # 'Siparise Donustu': kazanildi isareti. Elle atanabilseydi
        #   donusum oranı olcumu anlamsizlasirdi.
        #
        # 'Revize': arsivleme, /revize ucu atar.
        SISTEM_DURUMLARI = {
            'Faturalandi': 'Bu durum fatura kesildiğinde sistem tarafından '
                           'atanır. Faturalandırmak için önce siparişe '
                           'dönüştürüp fatura kesin.',
            'Siparise Donustu': 'Bu durum siparişe dönüştürüldüğünde sistem '
                                'tarafından atanır. "Siparişe Dönüştür" '
                                'düğmesini kullanın.',
        }
        if yeni_durum in SISTEM_DURUMLARI:
            return jsonify({'ok': False,
                            'mesaj': SISTEM_DURUMLARI[yeni_durum]}), 400

        if yeni_durum == 'Revize':"""

# ── Geçerli durum listesi ──
C_ESKI = """        gecerli_durumlar = ['Taslak', 'Ic Onay', 'Gonderildi', 'Onaylandi', 'Faturalandi', 'Iptal', 'Revize']"""
C_YENI = """        gecerli_durumlar = ['Taslak', 'Ic Onay', 'Gonderildi', 'Onaylandi',
                            'Siparise Donustu', 'Faturalandi', 'Iptal', 'Revize']"""

# ══ 2) urun_tip zorunlu ════════════════════════════════════════════
# Kalem dongusu IKI yerde: api_proforma_ekle ve api_proforma_guncelle.
# Yalnizca birini dogrulamak, bos tipin GUNCELLEMEDEN sizmasina izin
# verirdi — ayni gecikmeli cokme, farkli kapidan.
D_ESKI = """        for idx, k in enumerate(data.get('kalemler', [])):"""

D_YENI = """        # URUN TIPI ZORUNLU.
        # ProformaKalem.urun_tip serbest, SiparisKalem.urun_tip ise
        # NOT NULL. Arada dogrulama olmadigi icin bos tipli kalem
        # proformaya giriyor, hata HAFTALAR SONRA siparise
        # donustururken 500 olarak cikiyordu. Hata GECIKTIGI yerde
        # degil DOGDUGU yerde cikmali.
        GECERLI_URUN_TIP = ('BLOK', 'PLAKA', 'EBATLI')
        for _i, _k in enumerate(data.get('kalemler', [])):
            _t = (_k.get('urun_tip') or '').strip().upper()
            if not _t:
                return jsonify({'ok': False,
                                'mesaj': f'{_i + 1}. kalemde ürün tipi zorunlu '
                                         f'({", ".join(GECERLI_URUN_TIP)})'}), 400
            if _t not in GECERLI_URUN_TIP:
                return jsonify({'ok': False,
                                'mesaj': f'{_i + 1}. kalemde geçersiz ürün tipi: '
                                         f'{_t}. Geçerli: '
                                         f'{", ".join(GECERLI_URUN_TIP)}'}), 400
            _k['urun_tip'] = _t

        for idx, k in enumerate(data.get('kalemler', [])):"""

# ══ 3) Siparişe dönüşünce durum ════════════════════════════════════
E_ESKI = """            p.siparis_id = sip.id"""
E_YENI = """            p.siparis_id = sip.id
            # KAZANILDI ISARETI.
            # Onceden yalnizca siparis_id yaziliyordu; proforma
            # 'Onaylandi' kalıyor ve cevap BEKLEYEN teklif ile
            # KAZANILMIS teklif listede ayni gorunuyordu. Donusum
            # oranı olculemiyordu.
            # Iptal edilmis proformanin durumu EZILMEZ.
            if (p.durum or '') not in ('Iptal', 'Revize'):
                p.durum = 'Siparise Donustu'"""

# ══ 4) Fatura kesilince: yeni durumdan da geçebilsin ═══════════════
F_ESKI = """                if pf and pf.durum not in ('Faturalandi', 'Iptal'):"""
F_YENI = """                # 'Siparise Donustu' da faturalanabilir — yeni durum
                # eklendiginde bu kontrol atlanirsa proforma sonsuza
                # kadar "siparise donustu" kalirdi.
                if pf and pf.durum not in ('Faturalandi', 'Iptal'):"""

# ══ 5) Fatura kesme: yeni durumu kabul et ══════════════════════════
G_ESKI = """        if p.durum not in ('Onaylandi', 'Gonderildi', 'Faturalandi'):"""
G_YENI = """        if p.durum not in ('Onaylandi', 'Gonderildi', 'Siparise Donustu',
                           'Faturalandi'):"""

# ══ 6) Yazım hatası ════════════════════════════════════════════════
H_ESKI = """_proformayi_siparise_baglava"""
H_YENI = """_proformayi_siparise_baglama"""

BLOKLAR = [
    ("geçiş haritası + 'Siparise Donustu'", A_ESKI, A_YENI, "'Siparise Donustu': ['Iptal'],"),
    ("elle atanamayan sistem durumları",    B_ESKI, B_YENI, 'SISTEM_DURUMLARI = {'),
    ("geçerli durum listesi",               C_ESKI, C_YENI, "'Onaylandi',\n                            'Siparise Donustu'"),

    ("siparişe dönüşünce durum",            E_ESKI, E_YENI, "p.durum = 'Siparise Donustu'"),

    ("faturaya dönüşte yeni durum",         G_ESKI, G_YENI, "'Gonderildi', 'Siparise Donustu',"),
]

print("═" * 70)
print(" PF1 · PROFORMA AKIŞ DÜZELTMELERİ")
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

# ── urun_tip dogrulamasi: IKI kalem dongusune de ──
if 'GECERLI_URUN_TIP = (' in icerik:
    atlanan.append("ürün tipi zorunlu (2 uç nokta)")
else:
    # GIRINTI FARKLI: api_proforma_ekle'de dongu 8 bosluk,
    # api_proforma_guncelle'de bir `if` blogunun icinde 12 bosluk.
    # Tek girintiyle yamamak sozdizimi hatasi uretiyordu.
    _toplam = 0
    for _gir in ('        ', '            '):
        # SATIR BASINA SABITLE: 8 bosluklu kalip, 12 bosluklu
        # satirin ICINDE de eslesiyor. Onune satir sonu koyarak
        # tam girintiyi zorunlu kiliyoruz.
        _d = uyarla("\n" + _gir + "for idx, k in enumerate(data.get('kalemler', [])):")
        _n = icerik.count(_d)
        if not _n:
            continue
        if _n != 1:
            print(f" ✗ {len(_gir)} boşluklu kalem döngüsü {_n} kez bulundu.")
            print(" DOSYAYA DOKUNULMADI.")
            sys.exit(1)
        _y = "\n" + '\n'.join((_gir + l[8:]) if l.startswith('        ') else l
                                for l in D_YENI.split('\n'))
        icerik = icerik.replace(_d, uyarla(_y), 1)
        _toplam += 1
    if _toplam != 2:
        print(f" ✗ Kalem döngüsü {_toplam} yerde bulundu (2 bekleniyordu:")
        print("   api_proforma_ekle + api_proforma_guncelle).")
        print(" DOSYAYA DOKUNULMADI.")
        sys.exit(1)
    plan.append("ürün tipi zorunlu (ekle + güncelle)")

# Yazim hatasi — TUM eslesmeler
if H_ESKI in icerik:
    _n = icerik.count(H_ESKI)
    icerik = icerik.replace(H_ESKI, H_YENI)
    plan.append(f"yazım hatası düzeltmesi ({_n} yer)")
else:
    atlanan.append("yazım hatası düzeltmesi")

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

if 'baglava' in icerik:
    print(" ✗ 'baglava' kalıntısı var — DOSYAYA DOKUNULMADI.")
    sys.exit(1)
print(" ✓ yazım hatası kalıntısı yok")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_pf1_akis.py --uygula")
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
print(" ⚠ templates/proforma.html'de durum seçim listesi varsa")
print("   'Faturalandı' seçeneği artık 400 döner — ekranı da")
print("   güncellemek gerekebilir.")
print("═" * 70)

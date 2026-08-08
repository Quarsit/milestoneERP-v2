#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — KATMAN TUTARLILIK DENETİMİ
#
#  NEDEN VAR:
#    Bu projede tekrar eden bir hata sınıfı var: katmanlar (model, API,
#    form, yazdırma şablonu) elle senkron tutuluyor ve biri unutuluyor.
#    Yaşanmış örnekler:
#      • vergi_no      → model ✓ API ✓ form ✗  (veri hiç girilemiyordu)
#      • yuklenme_limani → model ✓ şablon ✓ API ✗ (belge boş basılıyordu)
#      • muhur_no      → API ✓ model ✗          (HTTP 500 ile çöküyordu)
#    Üçü de aynı kökten: kimse tüm katmanları birden kontrol etmiyor.
#
#  ÜÇ DENETİM:
#    D1 · API modele olmayan alan geçiriyor mu?   → ÇÖKME RİSKİ
#         ModelAdi(alan=...) çağrısındaki alan modelde yoksa SQLAlchemy
#         TypeError fırlatır ve uç nokta 500 döner.
#
#    D2 · Modelde olup formda hiç geçmeyen alan   → ÖKSÜZ ALAN
#         Kullanıcının girmesi gereken ama giremediği alanlar. İç hesap
#         alanları BEKLENEN_GIZLI listesiyle elenir.
#
#    D3 · Yazdırma şablonu basıyor ama forma girilemiyor → BOŞ BELGE
#         Belge şablonunda {{ p.alan }} varsa o alan bir formdan
#         girilebilmelidir; yoksa belge o alanı hep boş basar.
#
#  KULLANIM (proje dizininde):
#      python form_denetim.py              # tüm denetimler
#      python form_denetim.py --sadece D1  # tek denetim
#      python form_denetim.py --liste      # BEKLENEN_GIZLI önerisi üret
#
#  ÇIKIŞ KODU: bulgu varsa 1, temizse 0 (CI'da kullanılabilir).
# ══════════════════════════════════════════════════════════════════════
import re
import sys
from pathlib import Path

MODELS = Path('models.py')
APP = Path('flask_app.py')
SABLON = Path('templates')

for d in (MODELS, APP, SABLON):
    if not d.exists():
        print(f"HATA: {d} bulunamadı. Proje klasöründe çalıştırın.")
        sys.exit(1)

# ── Model ↔ form eşlemesi ─────────────────────────────────────────────
MODUL_FORM = {
    'Cari': 'cari',
    'Siparis': 'siparis',
    'Proforma': 'proforma',
    'Sevkiyat': 'sevkiyat',
    'Fatura': 'fatura',
    'Cek': 'cek',
    'Kasa': 'kasa',
    'BlokStok': 'stok',
    'PlakaStok': 'stok',
    'EbatliStok': 'stok',
    'Kesim': 'kesim',
    'Maliyet': 'maliyet',
    'Kullanici': 'ayarlar',
    'KdvIadeDosya': 'kdv_iade',
}

# Kullanıcının GİRMEMESİ gereken alanlar — bilinçli olarak formda yok.
# Yeni bir iç alan eklendiğinde buraya yazılır; aksi halde D2 uyarır.
# Kullanıcının GİRMEMESİ gereken alanlar — bilinçli olarak formda yok.
# Her giriş bir GEREKÇE ile birlikte yazılır; "sustur ve unut" listesi değildir.
BEKLENEN_GIZLI = {
    '*': {  # tüm modeller için ortak
        'id', 'olusturma', 'guncelleme', 'kullanici', 'aktif',
        'hareketler', 'kalemler',
    },
    # Satıcı bilgileri Ayarlar → Firma'dan bir kez girilir ve proforma
    # oluşturulurken otomatik doldurulur (F3). Her belgede elle yazılmaz.
    # avans_yuzdesi/tip/sabit: form 'avans_deger' gönderir, backend
    # avans_tutari'na yazar; diğerleri eski gösterim biçimleridir.
    # onay* alanları onay iş akışında sistem tarafından yazılır.
    'Proforma': {'satici_firma', 'satici_adres', 'satici_tel', 'satici_email',
                 'avans_yuzdesi', 'avans_tip', 'avans_sabit',
                 'onaya_gonderme_tarihi', 'onay_reddeden',
                 'proforma_no', 'revizyon_no', 'aktif_surum', 'ana_pi_id',
                 'durum', 'toplam', 'onay_tarihi', 'onaylayan',
                 'ic_onay_tarihi', 'ic_onaylayan', 'gonderim_tarihi'},
    # gumruk_tarihi: gümrük adımında sistem yazar (bkz. BILINEN_EKSIK).
    'Sevkiyat': {'durum', 'hazirlama_tarihi', 'cikis_tarihi', 'teslim_tarihi',
                 'iptal_tarihi', 'gercek_teslim', 'sofor', 'siparis_li',
                 'gumruk_tarihi'},
    # Fatura ÜÇ yoldan doğar: proformadan dönüşüm, doğrudan POST
    # /api/fatura (F4) ve satış kaydından POST /api/satislar/<id>/fatura
    # (H1). Aşağıdaki alanlar hiçbirinde elle girilmez; tutar ve maliyet
    # hesaplanır, durum akışla değişir.
    # (Eski yorum "yalnızca GET kabul ediyor" diyordu — F4'ten beri yanlıştı.)
    # iade_dosya_id: fatura formundan girilmez; KDV İade ekranındaki
    # "Fatura / KDV ekle" işlemiyle sistem yazar (F7).
    'Fatura': {'durum', 'fatura_tarihi', 'toplam', 'kalan', 'ara_toplam',
               'kdv_tutar', 'tevkifat_tutar', 'kalemler_json',
               'cari_hareket_id', 'alis_maliyeti', 'maliyet_doviz',
               'maliyet_kalemleri_json', 'iade_dosya_id'},
    'Cari': {'bakiye', 'borc', 'alacak'},
    'Siparis': {'siparis_tarihi', 'durum', 'kdv_tutar', 'tevkifat_tutar',
                'komisyon_tutar', 'toplam', 'ana_pi_id'},
    # Bağlantı kimlikleri işlem sırasında sistem tarafından kurulur.
    'Cek': {'durum', 'tahsil_banka_id', 'cari_hareket_id', 'kasa_hareket_id'},
    'Maliyet': {'try_karsilik', 'usd_karsilik', 'eur_karsilik', 'kur',
                'grup_id', 'donusum_id', 'donusum_tarihi', 'birim_maliyet',
                'toplam_miktar', 'baglanti_tip', 'baglanti_id',
                'iade_dosya_id'},
    # m2_kg / metraj_* ölçülerden hesaplanır.
    # alis_fiyat_birim: formda 'fiyat_birim' adıyla mevcut (farklı ad).
    # bas_kasa_no: formda 'baslangic_no' olarak giriliyor.
    'BlokStok': {'durum', 'giris_tarihi', 'hacim_m3', 'matrah', 'kdv_tutar',
                 'maliyet_usd', 'alis_fiyat_birim'},
    'PlakaStok': {'durum', 'giris_tarihi', 'metraj_m2', 'matrah', 'kdv_tutar',
                  'slab_no', 'maliyet_usd', 'm2_kg', 'metraj_sqft',
                  'alis_fiyat_birim'},
    'EbatliStok': {'durum', 'giris_tarihi', 'metraj_m2', 'matrah', 'kdv_tutar',
                   'maliyet_usd', 'm2_kg', 'metraj_sqft', 'alis_fiyat_birim',
                   'bas_kasa_no'},
    # kaynak_*: kesim anındaki durumu dondurup saklayan anlık görüntü
    # alanları; kullanıcı girmez, sistem kesim işleminde doldurur.
    'Kesim': {'kaynak_ids_json', 'kaynak_miktar_once', 'kaynak_miktar_sonra',
              'kaynak_durum', 'kaynak_onceki_durum', 'kaynak_birim_maliyet'},
    # varsayilan: modelde tanımlı ama hiçbir mantık okumuyor. Anlamı
    # "tahsilat formunda ön seçili kasa" olurdu; bu davranış henüz
    # uygulanmadığı için forma kutu eklenmedi — çalışmayan bir kutu
    # kullanıcıya yanlış izlenim verirdi. Davranış yazılırsa kaldırılır.
    'Kasa': {'varsayilan'},
    'Kullanici': {'sifre_hash', 'son_giris', 'yetkiler'},
    # donem/iade_tur yeni dosya kipinde giriliyor (yDonem/yTur); denetim
    # 'donem' ve 'iade_tur' dizgelerini formda arar, ikisi de var.
    # Aşağıdakiler sistemin yazdığı alanlardır.
    'KdvIadeDosya': {'olusturma'},
}

# BİLİNEN EKSİKLER — gerçek boşluklar, henüz yapılmadı.
# Muaf listesine konulup unutulmasınlar diye AYRI raporlanır.
BILINEN_EKSIK = {
    # Bekleyen bilinen eksik yok. Yeni bir alan bilinçli olarak
    # ertelendiğinde buraya gerekçesiyle yazılır; muaf listesine gömülüp
    # unutulmasın diye ayrı raporlanır.
}


def model_kolonlari():
    """models.py → {ModelAdi: [kolon, ...]}"""
    s = MODELS.read_text(encoding='utf-8')
    sonuc = {}
    for m in re.finditer(r'class (\w+)\(db\.Model\):(.*?)(?=\nclass |\Z)', s, re.S):
        ad, govde = m.group(1), m.group(2)
        sonuc[ad] = re.findall(r'^\s{4}(\w+)\s*=\s*db\.Column\(', govde, re.M)
    return sonuc


def gizli(model):
    """Formda olmaması BEKLENEN alanlar (iç hesap + bilinen eksikler)."""
    return (BEKLENEN_GIZLI.get('*', set())
            | BEKLENEN_GIZLI.get(model, set())
            | set(BILINEN_EKSIK.get(model, {})))


# ══ D1 · API modele olmayan alan geçiriyor mu? ════════════════════════
def denetim_d1(kolonlar):
    """ModelAdi(alan=...) çağrılarını tarar; modelde olmayan alanı bulur."""
    s = APP.read_text(encoding='utf-8')
    bulgular = []
    for model in kolonlar:
        # ModelAdi( ... ) çağrısını kabaca yakala (iç içe parantez dahil)
        for m in re.finditer(rf'\b{model}\(', s):
            bas = m.end()
            derinlik, i = 1, bas
            while i < len(s) and derinlik > 0:
                if s[i] == '(':
                    derinlik += 1
                elif s[i] == ')':
                    derinlik -= 1
                i += 1
            cagri = s[bas:i - 1]
            if 'query' in cagri[:20]:
                continue
            # İÇ İÇE ÇAĞRILARI TEMİZLE: json.dumps(x, ensure_ascii=False)
            # gibi gömülü çağrıların kendi parametreleri, dıştaki modelin
            # alanıymış gibi görünüp yanlış alarm üretiyordu.
            duz, derin = [], 0
            for ch in cagri:
                if ch == '(':
                    derin += 1
                elif ch == ')':
                    derin -= 1
                elif derin == 0:
                    duz.append(ch)
            cagri = ''.join(duz)
            for alan in re.findall(r'(?:^|[,\s])(\w+)\s*=(?!=)', cagri):
                if alan in kolonlar[model] or alan in ('id',):
                    continue
                # Python anahtar kelimeleri ve yaygın yerel değişkenler değil
                if alan.startswith('_') or alan in ('key', 'default', 'index'):
                    continue
                satir = s[:bas].count('\n') + 1
                bulgular.append((model, alan, satir))
    return bulgular


# ══ D2 · Modelde olup formda hiç geçmeyen alan ════════════════════════
def denetim_d2(kolonlar):
    bulgular = []
    for model, form in MODUL_FORM.items():
        if model not in kolonlar:
            continue
        yol = SABLON / f'{form}.html'
        if not yol.exists():
            continue
        metin = yol.read_text(encoding='utf-8').lower()
        muaf = gizli(model)
        oksuz = [k for k in kolonlar[model]
                 if k not in muaf and k.lower() not in metin]
        if oksuz:
            bulgular.append((model, form, oksuz))
    return bulgular


# ══ D3 · Şablon basıyor ama forma girilemiyor ═════════════════════════
def denetim_d3(kolonlar):
    """Yazdırma şablonlarındaki {{ nesne.alan }} referanslarını, o alanın
    herhangi bir formda geçip geçmediğiyle karşılaştırır."""
    tum_form = ''
    for form in set(MODUL_FORM.values()):
        y = SABLON / f'{form}.html'
        if y.exists():
            tum_form += y.read_text(encoding='utf-8').lower()

    tum_kolon = set()
    for k in kolonlar.values():
        tum_kolon |= set(k)

    bulgular = []
    for y in sorted(SABLON.glob('*print*.html')):
        metin = y.read_text(encoding='utf-8')
        alanlar = set(re.findall(r'\{\{\s*\w+\.(\w+)', metin))
        eksik = sorted(a for a in alanlar
                       if a in tum_kolon and a.lower() not in tum_form)
        if eksik:
            bulgular.append((y.name, eksik))
    return bulgular


# ══════════════════════════════════════════════════════════════════════
def main():
    sadece = None
    for a in sys.argv[1:]:
        if a.startswith('--sadece'):
            sadece = a.split('=')[-1].upper() if '=' in a else None
    if '--sadece' in sys.argv:
        i = sys.argv.index('--sadece')
        if i + 1 < len(sys.argv):
            sadece = sys.argv[i + 1].upper()

    kolonlar = model_kolonlari()
    print("═" * 70)
    print(" MILESTONE ERP — KATMAN TUTARLILIK DENETİMİ")
    print("═" * 70)
    print(f" {len(kolonlar)} model · {len(list(SABLON.glob('*.html')))} şablon")
    print()

    toplam = 0

    # ── D1 ──
    if sadece in (None, 'D1'):
        b = denetim_d1(kolonlar)
        print("─" * 70)
        print(" D1 · API MODELDE OLMAYAN ALAN GEÇİRİYOR   [ÇÖKME RİSKİ]")
        print("─" * 70)
        if b:
            for model, alan, satir in b:
                print(f"   ✗ {model}({alan}=...) — flask_app.py:{satir}")
                print(f"     '{alan}' {model} modelinde yok → TypeError → HTTP 500")
            print(f"\n   {len(b)} bulgu. models.py güncel mi kontrol edin.")
            toplam += len(b)
        else:
            print("   ✓ temiz — API ile model uyumlu")
        print()

    # ── D2 ──
    if sadece in (None, 'D2'):
        b = denetim_d2(kolonlar)
        print("─" * 70)
        print(" D2 · MODELDE VAR, FORMDA YOK   [ÖKSÜZ ALAN]")
        print("─" * 70)
        if b:
            for model, form, alanlar in b:
                print(f"   ✗ {model} → templates/{form}.html")
                for a in alanlar:
                    print(f"       · {a}")
                toplam += len(alanlar)
            print("\n   Her alan için: ya forma ekleyin, ya BEKLENEN_GIZLI'ye yazın.")
        else:
            print("   ✓ temiz — tüm alanlar ya formda ya muaf listesinde")
        print()

    # ── D3 ──
    if sadece in (None, 'D3'):
        b = denetim_d3(kolonlar)
        print("─" * 70)
        print(" D3 · BELGE BASIYOR, FORMA GİRİLEMİYOR   [BOŞ BELGE]")
        print("─" * 70)
        if b:
            for dosya, alanlar in b:
                print(f"   ✗ {dosya}")
                for a in alanlar:
                    print(f"       · {a} — belgede basılıyor, hiçbir formda yok")
                toplam += len(alanlar)
            print("\n   Bu alanlar belgelerde HEP BOŞ çıkar.")
        else:
            print("   ✓ temiz — basılan her alan bir formdan girilebiliyor")
        print()

    # ── D4 · Bilinen eksikler (bulgu sayılmaz, hatırlatma) ──
    if sadece in (None, 'D4'):
        print("─" * 70)
        print(" D4 · BİLİNEN EKSİKLER   [kayıt altında, henüz yapılmadı]")
        print("─" * 70)
        if BILINEN_EKSIK:
            for model in sorted(BILINEN_EKSIK):
                print(f"   {model}")
                for alan, neden in BILINEN_EKSIK[model].items():
                    print(f"       · {alan:16s} {neden}")
            print("\n   Bunlar bulgu sayılmaz — bilinçli olarak ertelenmiş işlerdir.")
            print("   Yapıldıklarında BILINEN_EKSIK listesinden çıkarın.")
        else:
            print("   ✓ bekleyen bilinen eksik yok")
        print()

    print("═" * 70)
    if toplam:
        print(f" {toplam} BULGU")
    else:
        print(" ✓ TÜM DENETİMLER TEMİZ")
    print("═" * 70)
    return 1 if toplam else 0


if __name__ == '__main__':
    sys.exit(main())

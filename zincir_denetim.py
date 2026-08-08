#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — ALAN ZİNCİRİ DENETİMİ  ·  Z1–Z4
#
#  NEDEN VAR:
#    form_denetim.py katmanlar arası tutarlılığa bakar ama YALNIZCA
#    YAZMA EKSENİNDE: model → API(POST) → form → yazdırma şablonu.
#    GERİ OKUMA eksenini hiç görmez: PUT alan listesi ve GET serializer.
#
#    Kanıt: Y-1 ve Y-2 kodda dururken form_denetim.py "TÜM DENETİMLER
#    TEMİZ" dedi. Yeşil rapor yanlış güven verdi.
#
#    Yaşanmış örnekler (hepsi bu eksende):
#      • Sevkiyat.muhur_no       model✓ POST✓ form✓ serializer✗
#        → kaydediliyor, düzenlemede boş açılıyor, kaydedince SİLİNİYOR
#      • Cari.odeme_vadesi_gun   model✓ POST✓ form✓ PUT✗ serializer✗
#        → aynı sonuç
#      • Proforma.notlar         PUT korumalı döngüde VAR ama
#        döngüden sonra korumasız TEKRAR yazılıyor → koruma etkisiz
#
#    Ortak kök: bir alanın beş katmanda birden tutarlı olması gerekiyor.
#    Biri eksikse sistem HATA VERMEZ — veriyi sessizce kaybeder.
#    Bu, en tehlikeli hata sınıfı: başarılı görünür, sonuç yoktur.
#
#  BEŞ KATMAN:
#    model      models.py'de db.Column tanımı
#    post       POST uç noktasında Model(alan=data.get('alan'))
#    put        PUT uç noktasında güncelleniyor (korumalı döngü veya atama)
#    serializer GET yanıtında 'alan': x.alan olarak dönüyor
#    form       templates/<modul>.html içinde geçiyor
#
#  DÖRT DENETİM:
#    Z1 · GERİ OKUNMUYOR      [VERİ KAYBI]
#         Kaydediliyor ama serializer döndürmüyor. Form boş açılır,
#         kullanıcı kaydettiğinde önceki DOĞRU veri null ile ezilir.
#         En yüksek şiddet: sessizce veri siler.
#
#    Z2 · GÜNCELLENEMİYOR     [DÜZENLEME KAYBI]
#         POST'ta var, PUT'ta yok. İlk kayıtta girilir, bir daha
#         hiç değiştirilemez; kısmi güncellemede null'lanabilir.
#
#    Z3 · KORUMA EZİLİYOR     [F0-6 SINIFI]
#         Alan hem korumalı döngüde (if alan in data) hem de döngü
#         DIŞINDA korumasız atanıyor. Sonraki atama kazanır, koruma
#         etkisiz kalır. Sessiz ve fark edilmesi çok zor.
#
#    Z4 · VARSAYILANLA EZİLİYOR  [SESSİZ SIFIRLAMA]
#         PUT'ta p.alan = data.get('alan', VARSAYILAN) deseni.
#         Kısmi güncellemede alan gövdede yoksa varsayılana döner.
#         kdv_oran için bu, KDV'nin sessizce %0 olması demektir.
#
#  KULLANIM (proje dizininde):
#      python zincir_denetim.py                # tüm denetimler
#      python zincir_denetim.py --sadece Z1    # tek denetim
#      python zincir_denetim.py --tam          # tam zincir tablosu
#
#  ÇIKIŞ KODU: bulgu varsa 1, temizse 0 (CI'da kullanılabilir).
#
#  NOT: Bu betik STATİK analiz yapar — kodu çalıştırmaz, veritabanına
#  dokunmaz. Yanlış pozitif verebilir; her bulgu koda bakılarak
#  doğrulanmalıdır. Doğrulanan yanlış pozitifler BEKLENEN_* listelerine
#  GEREKÇESİYLE yazılır, susturulmaz.
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

# ── Model ↔ form ↔ API yolu eşlemesi ─────────────────────────────────
# api_yolu: serializer ve PUT taramasında bu modelin uç noktalarını bulmak
# için kullanılır. form_denetim.py'deki MODUL_FORM ile uyumlu tutulmalı.
MODUL = {
    'Cari':        {'form': 'cari',      'api': 'cari'},
    'Siparis':     {'form': 'siparis',   'api': 'siparis'},
    'Proforma':    {'form': 'proforma',  'api': 'proforma'},
    'Sevkiyat':    {'form': 'sevkiyat',  'api': 'sevkiyat'},
    'Fatura':      {'form': 'fatura',    'api': 'fatura'},
    'Cek':         {'form': 'cek',       'api': 'cek'},
    'Kasa':        {'form': 'kasa',      'api': 'kasa'},
    'Kesim':       {'form': 'kesim',     'api': 'kesim'},
    'Maliyet':     {'form': 'maliyet',   'api': 'maliyet'},
    # DIKKAT: sablon adi alt cizgili (kdv_iade.html) ama URL TIRELI
    # (/api/kdv-iade). Ilk surumde 'api' alt cizgiliydi ve tarayici
    # modelin hicbir uc noktasini bulamayip "PUT UC NOKTASI YOK"
    # diyordu — oysa PUT var (flask_app.py:13323).
    'KdvIadeDosya':{'form': 'kdv_iade',  'api': 'kdv-iade'},
    'BlokStok':    {'form': 'stok',      'api': 'stok'},
    'PlakaStok':   {'form': 'stok',      'api': 'stok'},
    'EbatliStok':  {'form': 'stok',      'api': 'stok'},
}

# ── Muafiyetler ──────────────────────────────────────────────────────
# Her giriş GEREKÇESİYLE yazılır. Bu bir "sustur" listesi değil,
# "bilinçli olarak böyle" beyanıdır. Gerekçesiz giriş eklemeyin.

# Hiçbir katmanda aranmayan alanlar — sistem yazar, kullanıcı görmez.
ORTAK_MUAF = {
    'id', 'olusturma', 'guncelleme', 'kullanici', 'aktif',
    'hareketler', 'kalemler', 'detaylar', 'rezervasyonlar', 'maliyetler',
}

# Z1 muafiyeti: serializer'da olmaması normal olan alanlar.
# Genellikle hesaplanan veya yalnızca yazdırma şablonunda kullanılanlar.
BEKLENEN_SERIALIZER_YOK = {
    # Stok giriş/alış tarihleri: form bunları `|| null` ile gönderir
    # (yeni kayıt için doğru), ama PUT /api/stok/<id> bu alanlara HİÇ
    # DOKUNMUYOR — yalnızca durum, konum, uretici, alis_fiyati,
    # fiyat_birim ve aciklama güncellenir (flask_app.py:3772).
    # Yani sıfırlanmaları mümkün değil. Kod okunarak doğrulandı.
    # Serializer bu ikisini FARKLI ADLA döndürüyor (flask_app.py:10523):
    #   'iskonto': p.iskonto_sabit        'avans_deger': p.avans_tutari
    # Form da aynı adları kullanıyor, yani zincir SAĞLAM. Tarayıcı
    # model alan adını aradığı için göremiyor. Kod okunarak doğrulandı.
    'Proforma':   {'iskonto_sabit', 'avans_tutari'},
    'BlokStok':   {'giris_tarihi', 'alis_tarihi'},
    'PlakaStok':  {'giris_tarihi', 'alis_tarihi'},
    'EbatliStok': {'giris_tarihi', 'alis_tarihi'},
}

# Z2 muafiyeti: PUT'ta güncellenmemesi BİLİNÇLİ olan alanlar.
# Tipik olarak: iş akışı adımlarında sistem yazar, elle değiştirilemez.
BEKLENEN_PUT_YOK = {
    'Proforma': {
        # Onay akışı alanları: /onay, /ic_onay uç noktaları yazar.
        # Genel PUT'tan değiştirilmeleri çift kontrolü delerdi.
        'durum', 'onay_tarihi', 'onaylayan', 'ic_onay_tarihi',
        'ic_onaylayan', 'gonderim_tarihi', 'onaya_gonderme_tarihi',
        'onay_reddeden', 'revizyon_no', 'aktif_surum', 'ana_pi_id',
        'proforma_no',
        # PUT bu ikisini FARKLI ANAHTARLA isliyor (flask_app.py):
        #   if 'iskonto' in data:      p.iskonto_sabit = ...
        #   if 'avans_deger' in data:  p.avans_tutari  = ...
        # Form da ayni anahtarlari gonderiyor; zincir SAGLAM. Tarayici
        # model alan adini aradigi icin goremiyor.
        'iskonto_sabit', 'avans_tutari',
    },
    'Sevkiyat': {
        # Durum adımları /durum uç noktasından ilerler.
        'durum', 'hazirlama_tarihi', 'cikis_tarihi', 'gumruk_tarihi',
        'teslim_tarihi', 'iptal_tarihi',
        # Yapısal bağ: sevkiyatın hangi siparişe ait olduğu sonradan
        # değiştirilemez (bkz. Fatura gerekçesi).
        'siparis_id',
    },
    'Fatura': {
        'durum', 'kalan', 'cari_hareket_id', 'iade_dosya_id',
    },
    'KdvIadeDosya': {
        # Bağlama/çözme ayrı uç noktalardan yapılır (F7).
        'durum',
    },
    # ── YAPISAL BAĞLAR — bilerek değiştirilemez ──
    # Bir belge oluşturulduktan sonra HANGİ siparişe/yöne ait olduğu
    # değiştirilemez. Değiştirilebilseydi: cari hareketler, maliyet
    # kayıtları ve KDV iade izi eski siparişe bağlı kalır, yenisiyle
    # tutmazdı. Yanlış bağ kurulduysa doğru yol belgeyi iptal edip
    # yeniden oluşturmaktır — iz kalsın diye.
    # (Fatura için /api/diag/fatura/<id>/siparis_bagla var; ADMIN
    #  kapısı arkasında ve denetim kaydı bırakıyor.)
    'Fatura': {
        'durum', 'kalan', 'cari_hareket_id', 'iade_dosya_id',
        'siparis_id', 'yon',
    },
    # ── STOK ──
    # blok_no: PUT'ta VAR ama tek degiskene toplanarak isleniyor:
    #     _no = data.get('blok_no') or data.get('kasa_no')
    #     if _no: stok.blok_no = _no          (flask_app.py, Z2S yamasi)
    # EBATLI'da kasa_no, digerlerinde blok_no oldugu icin bu birlestirme
    # gerekli. Tarayici tek tek anahtar aradigi icin goremiyor.
    #
    # doviz: DUZENLEME FORMU BU ALANI GONDERMIYOR (stok.html'de duzDoviz
    # yok) ve bilerek: alis dovizi karlilik ve maliyet hesaplarini
    # besliyor (flask_app.py:1673, 2192, 3192). Sonradan degistirilmesi
    # mevcut maliyet kayitlarini gecersiz kilardi. Yanlis girildiyse
    # stok silinip yeniden olusturulmali.
    # kdv_oran: alis_tipi ile birlikte matrah ve kdv_tutar'i belirler;
    # bunlar hem stokta hem de TEDARIKCI CARI HAREKETINDE saklanir (B3).
    # Sonradan degistirilirse stok, cari hareket ve KDV iade izi
    # birbirini tutmaz. doviz ile ayni gerekce — yanlissa stok silinip
    # yeniden olusturulmali.
    'BlokStok':   {'blok_no', 'doviz', 'kdv_oran'},
    'PlakaStok':  {'blok_no', 'doviz', 'kdv_oran'},
    'EbatliStok': {'kasa_no', 'doviz', 'kdv_oran'},
    'Kesim': {
        # PUT UÇ NOKTASI YOK — bilinçli. Kesim, bir bloğu tüketip
        # yerine N adet plaka/ebatlı stok YARATAN geri dönüşsüz bir
        # işlem. "Düzenlemek" üretilen stokların kimliğini ve
        # maliyetini bozardı. Yanlışsa kesim silinir (DELETE),
        # kaynak blok geri gelir, yeniden yapılır.
        '__PUT_YOK__',
    },
}

# ── Serializer YARDIMCI FONKSİYONLARI ────────────────────────────────
# Bazı modüller serializer'ı satır içi sözlük yerine ayrı bir yardımcı
# fonksiyonda tutuyor (iyi bir pratik — tekrar önlüyor). Tarayıcı uç
# nokta gövdesine baktığı için bu fonksiyonları GÖREMEZ ve alanları
# "serializer'da yok" sanır.
#
# Kanıt: Cek'in beş alanı ilk taramada Z1'de çıkmıştı; kodda
# _cek_to_dict() hepsini döndürüyordu. Araç eksiğiydi, kod doğruydu.
#
# Buraya model → yardımcı fonksiyon adı yazın; tarayıcı o fonksiyonun
# gövdesini de serializer sayar.
SERIALIZER_YARDIMCI = {
    'Cek': ('_cek_to_dict',),
    'KdvIadeDosya': ('_iade_dosya_ozet',),
}


# Z4 muafiyeti: varsayılanla yazılması doğru olan alanlar.
# Yalnızca "gövdede yoksa gerçekten varsayılan olmalı" durumlar.
BEKLENEN_VARSAYILAN = {
    # 'Model': {'alan'},
}


# ══════════════════════════════════════════════════════════════════════
#  AYRIŞTIRMA
# ══════════════════════════════════════════════════════════════════════

def model_kolonlari():
    """models.py → {ModelAdi: {kolon: satir_no}}"""
    src = MODELS.read_text(encoding='utf-8', errors='replace')
    sonuc = {}
    bloklar = re.findall(
        r"class (\w+)\(db\.Model\):(.*?)(?=\nclass |\Z)", src, re.S)
    satir_ofset = {}
    for i, satir in enumerate(src.split('\n'), 1):
        m = re.match(r'class (\w+)\(db\.Model\):', satir)
        if m:
            satir_ofset[m.group(1)] = i
    for ad, govde in bloklar:
        kolonlar = {}
        for j, satir in enumerate(govde.split('\n')):
            m = re.match(r'\s{4}(\w+)\s*=\s*db\.Column', satir)
            if m:
                kolonlar[m.group(1)] = satir_ofset.get(ad, 0) + j
        sonuc[ad] = kolonlar
    return sonuc


def uc_noktalar():
    """flask_app.py → [{yol, yontemler, ad, govde, satir}]"""
    lines = APP.read_text(encoding='utf-8', errors='replace').split('\n')
    idx = [i for i, l in enumerate(lines) if '@app.route' in l]
    sonuc = []
    for i in idx:
        m = re.search(r"@app\.route\(\s*'([^']+)'", lines[i])
        if not m:
            continue
        yol = m.group(1)
        yontemler = re.findall(r"'(GET|POST|PUT|PATCH|DELETE)'", lines[i])
        if not yontemler:
            yontemler = ['GET']
        j = i
        while j < len(lines) and not re.match(r'\s+def ', lines[j]):
            j += 1
        k = j + 1
        while k < len(lines) and '@app.route' not in lines[k]:
            k += 1
        ad_m = re.match(r'\s+def (\w+)', lines[j]) if j < len(lines) else None
        sonuc.append({
            'yol': yol,
            'yontemler': yontemler,
            'ad': ad_m.group(1) if ad_m else '?',
            'govde': '\n'.join(lines[j:k]),
            'satir': i + 1,
        })
    return sonuc


def model_uc_noktalari(uclar, api_yolu):
    """Bir modele ait uç noktaları yol parçasına göre ayıkla."""
    return [u for u in uclar if f'/api/{api_yolu}' in u['yol']]


def serializer_alanlari(govde):
    """Gövdedeki 'alan': ... biçimindeki JSON anahtarlarını topla."""
    return set(re.findall(r"'(\w+)'\s*:", govde))


def post_alanlari(govde, model_adi):
    """Model(alan=...) çağrısındaki anahtar kelimeleri topla."""
    alanlar = set()
    for m in re.finditer(rf'{model_adi}\s*\(', govde):
        parca = govde[m.end():m.end() + 3000]
        alanlar |= set(re.findall(r'(\w+)\s*=\s*(?:data\.get|_parse|data\[)',
                                  parca))
    return alanlar


def put_korumali_alanlar(govde):
    """PUT'ta KORUMALI olarak guncellenen alanlar.

    İki desen de korumalıdır — ikisi de "gövdede varsa yaz" der:

      1) Toplu döngü:
             for _alan in ('a', 'b', 'c'):
                 if _alan in data: setattr(p, _alan, data.get(_alan))

      2) Tek tek koşul:
             if 'konum' in data: stok.konum = data['konum']

    İkinci desen ilk sürümde TANINMIYORDU ve stok PUT'unun gerçekten
    işlediği aciklama/uretici/fiyat_birim alanları "PUT'ta yok" diye
    raporlanıyordu. Araç eksiğiydi; kod doğruydu.
    """
    alanlar = set()
    # 1) for _alan in ('a','b',...) döngüleri
    for m in re.finditer(r"for\s+_?\w+\s+in\s*[\(\[]([^\)\]]*)[\)\]]", govde, re.S):
        alanlar |= set(re.findall(r"'(\w+)'", m.group(1)))
    # 2) if 'alan' in <govde_degiskeni>:  (tek satır veya blok)
    #    Govde degiskeni her yerde 'data' degil — Cek PUT'u 'd',
    #    bazi uc noktalar 'veri' kullaniyor. Ilk surum yalnizca 'data'
    #    ariyordu ve Cek.keside_tarihi "PUT'ta yok" saniliyordu; oysa
    #    flask_app.py:9693'te `if 'keside_tarihi' in d:` var.
    alanlar |= set(re.findall(
        r"if\s+'(\w+)'\s+in\s+(?:data|d|veri|govde|payload)\b", govde))
    # 3) if data.get('alan'):  — "gonderildiyse ve doluysa yaz"
    #    Kimlik alanlarinda (cins, blok_no) bilerek kullanilir:
    #    bos gonderim kaydi silmesin diye.
    alanlar |= set(re.findall(
        r"if\s+(?:data|d|veri|govde|payload)\.get\(\s*'(\w+)'", govde))
    return alanlar


def put_dogrudan_atamalar(govde):
    """KORUMASIZ p.alan = data.get('alan'[, VARSAYILAN]) atamalarini bul.

    "Korumasiz" onemli: bir atama `if 'alan' in data:` bloğunun
    ICINDEYSE aslinda KORUMALIDIR ve Z3/Z4'te bulgu sayilmamalidir.

        if 'termin' in data:                 ← koruma
            p.termin = _parse_date(data.get('termin'))   ← korumali atama

    Ilk surum bu ayrimi yapmiyordu; yukaridaki desen hem korumali
    listeye hem dogrudan listeye giriyor ve Z3 "koruma eziliyor"
    diye YANLIS BULGU uretiyordu.

    Doner: {alan: varsayilan_var_mi}
    """
    sonuc = {}
    satirlar = govde.split('\n')
    desen = re.compile(
        r"^\s*\w+\.(\w+)\s*=\s*(?:_parse_date\()?\s*data\.get\(\s*'(\w+)'"
        r"(\s*,\s*[^)]+)?\)")
    kosul = re.compile(
        r"if\s+(?:'(\w+)'\s+in\s+(?:data|d|veri)|"
        r"(?:data|d|veri)\.get\(\s*'(\w+)')")
    for i, satir in enumerate(satirlar):
        m = desen.match(satir)
        if not m:
            continue
        alan = m.group(1)
        anahtar = m.group(2)
        # Onceki 2 satirda bu alani koruyan bir kosul var mi?
        korumali = False
        for onceki in satirlar[max(0, i - 2):i]:
            k = kosul.search(onceki)
            if k and (k.group(1) or k.group(2)) in (alan, anahtar):
                korumali = True
                break
        if korumali:
            continue
        varsayilan = m.group(3) is not None
        sonuc[alan] = sonuc.get(alan, False) or varsayilan
    return sonuc


def form_metni(form_adi):
    p = SABLON / f'{form_adi}.html'
    if not p.exists():
        return ''
    return p.read_text(encoding='utf-8', errors='replace').lower()


# Z5 — ön yüzün SIFIRLAYICI olarak gönderdiği alanlar.
#
# NEDEN AYRI BİR DENETİM: Proforma limanları vakası beş katmanda da
# "doğru" görünüyordu (model✓ post✓ put✓ form✓) ama yine de veri
# kayboluyordu. Kırılma noktası ön yüzdeydi:
#
#     yuklenme_limani: document.getElementById('fYukLiman')
#                        .value.trim() || null,
#
# Alan boş olsa bile ANAHTAR gövdede gider (değeri null). Korumalı
# döngünün `if _alan in data` koşulu bu durumda GEÇER ve null yazılır.
# Yani F0-6 koruması bu desende işe yaramaz.
#
# Tek başına `|| null` sorun değildir — yeni kayıtta doğru davranıştır.
# Tek başına eksik serializer da fark edilmeyebilir. İKİSİ BİRLEŞİNCE
# veri kaybı KESİNLEŞİR: form boş açılır → null gönderir → veri silinir.
SIFIRLAYICI = re.compile(
    r"(\w+)\s*:\s*[^,;{}\n]*?\|\|\s*null", re.IGNORECASE)


def yardimci_serializer_alanlari(model_adi):
    """SERIALIZER_YARDIMCI'da tanımlı fonksiyonların döndürdüğü alanlar."""
    adlar = SERIALIZER_YARDIMCI.get(model_adi)
    if not adlar:
        return set()
    kaynak = APP.read_text(encoding='utf-8', errors='replace')
    satirlar = kaynak.split('\n')
    bulunan = set()
    for ad in adlar:
        for i, satir in enumerate(satirlar):
            if f'def {ad}(' not in satir:
                continue
            girinti = len(satir) - len(satir.lstrip())
            govde = []
            for t in satirlar[i + 1:]:
                if t.strip() and (len(t) - len(t.lstrip())) <= girinti:
                    break
                govde.append(t)
            bulunan |= serializer_alanlari('\n'.join(govde))
            break
    return bulunan


def form_sifirlayici_alanlar(form_adi):
    """Formun PUT gövdesine `alan: ... || null` olarak koyduğu alanlar."""
    p = SABLON / f'{form_adi}.html'
    if not p.exists():
        return set()
    ham = p.read_text(encoding='utf-8', errors='replace')
    return {m.group(1).lower() for m in SIFIRLAYICI.finditer(ham)}


# ══════════════════════════════════════════════════════════════════════
#  ZİNCİR HARİTASI
# ══════════════════════════════════════════════════════════════════════

def zincir_haritasi():
    modeller = model_kolonlari()
    uclar = uc_noktalar()
    harita = {}

    for model_adi, cfg in MODUL.items():
        kolonlar = modeller.get(model_adi, {})
        if not kolonlar:
            continue
        m_uclar = model_uc_noktalari(uclar, cfg['api'])

        post_govdeler = [u for u in m_uclar if 'POST' in u['yontemler']]
        put_govdeler = [u for u in m_uclar if 'PUT' in u['yontemler']
                        or 'PATCH' in u['yontemler']]
        get_govdeler = [u for u in m_uclar if 'GET' in u['yontemler']]

        post_set = set()
        for u in post_govdeler:
            post_set |= post_alanlari(u['govde'], model_adi)

        put_korumali, put_dogrudan = set(), {}
        for u in put_govdeler:
            put_korumali |= put_korumali_alanlar(u['govde'])
            put_dogrudan.update(put_dogrudan_atamalar(u['govde']))

        ser_set = set()
        for u in get_govdeler:
            ser_set |= serializer_alanlari(u['govde'])
        # Ayrı yardımcı fonksiyondaki serializer'ları da say
        ser_set |= yardimci_serializer_alanlari(model_adi)

        form_txt = form_metni(cfg['form'])
        form_sifirlayici = form_sifirlayici_alanlar(cfg['form'])

        harita[model_adi] = {
            'kolonlar': kolonlar,
            'post': post_set,
            'put_korumali': put_korumali,
            'put_dogrudan': put_dogrudan,
            'serializer': ser_set,
            'form': form_txt,
            'form_sifirlayici': form_sifirlayici,
            'put_var_mi': bool(put_govdeler),
            'api': cfg['api'],
        }
    return harita


# ══════════════════════════════════════════════════════════════════════
#  DENETİMLER
# ══════════════════════════════════════════════════════════════════════

def z1_geri_okunmuyor(harita):
    """Kaydediliyor ama serializer döndürmüyor → düzenlemede siliniyor."""
    bulgular = []
    for model, d in harita.items():
        muaf = BEKLENEN_SERIALIZER_YOK.get(model, set()) | ORTAK_MUAF
        for alan, satir in d['kolonlar'].items():
            if alan in muaf:
                continue
            yazilir = alan in d['post'] or alan in d['put_korumali'] \
                or alan in d['put_dogrudan']
            formda = alan.lower() in d['form']
            if yazilir and formda and alan not in d['serializer']:
                bulgular.append((model, alan, satir))
    return bulgular


def _gercek_kolon(d, alan):
    """Alan modelde GERCEKTEN var mi?

    POST govdesinden cikarilan bazi adlar model kolonu degildir:
    'kalemler_data', 'hedef_id', 'kaynak_id', '_tarih' gibi istek
    govdesine ozgu anahtarlar. Bunlari raporlamak gurultu uretir.
    """
    return alan in d['kolonlar']


def z2_guncellenemiyor(harita):
    """POST'ta var, PUT'ta yok → ilk kayıttan sonra değiştirilemiyor."""
    bulgular = []
    for model, d in harita.items():
        muaf = BEKLENEN_PUT_YOK.get(model, set()) | ORTAK_MUAF
        if not d['put_var_mi']:
            # PUT'un OLMAMASI bilinçli olabilir (geri dönüşsüz işlemler).
            # BEKLENEN_PUT_YOK'a '__PUT_YOK__' gerekçesiyle eklenir.
            if '__PUT_YOK__' not in muaf:
                bulgular.append((model, '(PUT UÇ NOKTASI YOK)', 0))
            continue
        for alan in sorted(d['post']):
            if alan in muaf or not _gercek_kolon(d, alan):
                continue
            if alan not in d['put_korumali'] and alan not in d['put_dogrudan']:
                bulgular.append((model, alan, d['kolonlar'].get(alan, 0)))
    return bulgular


def z3_koruma_eziliyor(harita):
    """Hem korumalı döngüde hem döngü dışında atanıyor → koruma etkisiz."""
    bulgular = []
    for model, d in harita.items():
        cakisan = d['put_korumali'] & set(d['put_dogrudan'].keys())
        for alan in sorted(cakisan):
            bulgular.append((model, alan, d['kolonlar'].get(alan, 0)))
    return bulgular


def z4_varsayilanla_eziliyor(harita):
    """p.alan = data.get('alan', VARSAYILAN) → kısmi güncellemede sıfırlanır."""
    bulgular = []
    for model, d in harita.items():
        muaf = BEKLENEN_VARSAYILAN.get(model, set()) | ORTAK_MUAF
        for alan, varsayilan_var in sorted(d['put_dogrudan'].items()):
            if alan in muaf or not varsayilan_var:
                continue
            bulgular.append((model, alan, d['kolonlar'].get(alan, 0)))
    return bulgular


def z6_korumasiz_kalem_silme():
    """PUT gövdesinde KORUMASIZ 'önce sil sonra kur' deseni.

    Desen:
        XKalem.query.filter_by(...).delete()          ← koşulsuz
        for k in data.get('kalemler', []):            ← gövdede yoksa []

    Gövdede 'kalemler' anahtarı yoksa TÜM KALEMLER SİLİNİR ve yerine
    hiçbir şey konmaz. HTTP 200 döner, uyarı çıkmaz.

    Z4 ile aynı kök: "gövdede yoksa VARSAYILANA dön" — doğrusu
    "gövdede yoksa DOKUNMA". Z4 tekil alanlara bakar, bu denetim
    LİSTE alanlarına (kalem koleksiyonları) bakar.

    Doğru desen (Siparis PUT'u böyle yapıyor):
        if 'kalemler' in data:
            XKalem.query.filter_by(...).delete()
            for k in data['kalemler']: ...
    """
    kaynak = APP.read_text(encoding='utf-8', errors='replace')
    satirlar = kaynak.split('\n')
    bulgular = []
    for i, satir in enumerate(satirlar):
        m = re.search(r'(\w*Kalem)\.query\.filter_by\([^)]*\)\.delete\(\)', satir)
        if not m:
            continue
        # Sonraki birkaç satırda data.get('...', []) ile yeniden kurma var mı?
        sonraki = '\n'.join(satirlar[i + 1:i + 4])
        if not re.search(r"data\.get\(\s*'(\w+)'\s*,\s*\[\s*\]\s*\)", sonraki):
            continue  # gerçek silme uç noktası — bu denetimin konusu değil
        anahtar = re.search(r"data\.get\(\s*'(\w+)'", sonraki).group(1)
        # Önceki 3 satırda koruma var mı?
        onceki = '\n'.join(satirlar[max(0, i - 3):i])
        if re.search(rf"if\s+'{anahtar}'\s+in\s+(?:data|d|veri)", onceki):
            continue  # korumalı — doğru desen
        bulgular.append((m.group(1), anahtar, i + 1))
    return bulgular


def z5_null_sifirlayici(harita):
    """Form `|| null` gönderiyor AMA serializer alanı döndürmüyor.

    Bu kombinasyon veri kaybının KESİN göstergesidir:
      1. Serializer alanı döndürmez  → form boş açılır
      2. Form `|| null` gönderir     → anahtar gövdede, değer null
      3. Korumalı döngü `in data` görür → null YAZILIR
      4. Doğru veri silinir

    Z1'den farkı: Z1 yalnızca serializer eksikliğine bakar ve alan
    formda geçiyorsa uyarır. Z5 ayrıca ön yüzün SIFIRLAYICI gönderdiğini
    doğrular — yani kaybın teorik değil KESİN olduğunu söyler.
    """
    bulgular = []
    for model, d in harita.items():
        muaf = BEKLENEN_SERIALIZER_YOK.get(model, set()) | ORTAK_MUAF
        for alan in sorted(d['kolonlar']):
            if alan in muaf:
                continue
            if alan not in d['form_sifirlayici']:
                continue
            if alan in d['serializer']:
                continue
            bulgular.append((model, alan, d['kolonlar'].get(alan, 0)))
    return bulgular


# ══════════════════════════════════════════════════════════════════════
#  ÇIKTI
# ══════════════════════════════════════════════════════════════════════

CIZGI = '─' * 70
KALIN = '═' * 70


def baslik(kod, ad, etiket):
    print(f"\n{CIZGI}\n {kod} · {ad}   [{etiket}]\n{CIZGI}")


def yazdir(bulgular, bos_mesaj, aciklama=None):
    if not bulgular:
        print(f"   ✓ temiz — {bos_mesaj}")
        return 0
    if aciklama:
        print(f"   {aciklama}\n")
    gecerli = None
    for model, alan, satir in bulgular:
        if model != gecerli:
            print(f"   {model}")
            gecerli = model
        yer = f"models.py:{satir}" if satir else ""
        print(f"      • {alan:<24} {yer}")
    print(f"\n   → {len(bulgular)} bulgu")
    return len(bulgular)


def tam_tablo(harita):
    print(f"\n{KALIN}\n TAM ZİNCİR TABLOSU\n{KALIN}")
    for model, d in sorted(harita.items()):
        print(f"\n{model}")
        print(f"  {'alan':<26}{'model':>6}{'post':>6}{'put':>6}"
              f"{'ser':>6}{'form':>6}")
        for alan in sorted(d['kolonlar']):
            if alan in ORTAK_MUAF:
                continue
            p = '✓' if alan in d['post'] else '·'
            u = '✓' if (alan in d['put_korumali']
                        or alan in d['put_dogrudan']) else '·'
            s = '✓' if alan in d['serializer'] else '·'
            f = '✓' if alan.lower() in d['form'] else '·'
            print(f"  {alan:<26}{'✓':>6}{p:>6}{u:>6}{s:>6}{f:>6}")


def main():
    sadece = None
    tam = '--tam' in sys.argv
    if '--sadece' in sys.argv:
        i = sys.argv.index('--sadece')
        if i + 1 < len(sys.argv):
            sadece = sys.argv[i + 1].upper()

    harita = zincir_haritasi()

    print(KALIN)
    print(" MILESTONE ERP — ALAN ZİNCİRİ DENETİMİ")
    print(KALIN)
    print(f" {len(harita)} model · beş katman: model → post → put "
          f"→ serializer → form")

    if tam:
        tam_tablo(harita)
        return 0

    toplam = 0

    if sadece in (None, 'Z1'):
        baslik('Z1', 'KAYDEDİLİYOR AMA GERİ OKUNMUYOR', 'VERİ KAYBI')
        toplam += yazdir(
            z1_geri_okunmuyor(harita),
            'yazılan her alan GET yanıtında da dönüyor',
            'Form boş açılır. Kullanıcı başka bir alanı düzeltip\n'
            '   kaydettiğinde bu alanlar null ile EZİLİR.')

    if sadece in (None, 'Z5'):
        baslik('Z5', 'FORM null GÖNDERİYOR + SERIALIZER DÖNDÜRMÜYOR',
               'KESİN VERİ KAYBI')
        toplam += yazdir(
            z5_null_sifirlayici(harita),
            'sıfırlayıcı gönderilen her alan geri de okunuyor',
            'Form boş açılır (serializer yok) ve `|| null` ile\n'
            '   anahtarı YİNE gönderir. Korumalı döngü null yazar.\n'
            '   Kayıp teorik değil KESİN.')

    if sadece in (None, 'Z6'):
        baslik('Z6', 'KORUMASIZ KALEM SİLME', 'KOLEKSİYON KAYBI')
        b = z6_korumasiz_kalem_silme()
        if b:
            for model, anahtar, satir in b:
                print(f"   ✗ {model}  —  flask_app.py:{satir}")
                print(f"     Kalemler koşulsuz siliniyor, sonra data.get('{anahtar}', [])")
                print(f"     ile kuruluyor. Gövdede '{anahtar}' yoksa HEPSİ GİDER.")
                print(f"     Çözüm:  if '{anahtar}' in data:  koruması ekleyin.")
            print(f"\n   → {len(b)} bulgu")
            toplam += len(b)
        else:
            print('   ✓ temiz — kalem silme işlemlerinin hepsi korumalı')
        print()

    if sadece in (None, 'Z2'):
        baslik('Z2', 'POST\'TA VAR, PUT\'TA YOK', 'DÜZENLEME KAYBI')
        toplam += yazdir(
            z2_guncellenemiyor(harita),
            'kaydedilen her alan güncellenebiliyor da',
            'İlk kayıtta girilir, bir daha değiştirilemez.')

    if sadece in (None, 'Z3'):
        baslik('Z3', 'KORUMALI DÖNGÜ SONRADAN EZİLİYOR', 'F0-6 SINIFI')
        toplam += yazdir(
            z3_koruma_eziliyor(harita),
            'korumalı döngü alanları döngü dışında tekrar yazılmıyor',
            'Alan hem korumalı döngüde hem döngü dışında atanıyor.\n'
            '   Sonraki atama kazanır; koruma ETKİSİZ.')

    if sadece in (None, 'Z4'):
        baslik('Z4', 'VARSAYILANLA SESSİZ SIFIRLAMA', 'SESSİZ SIFIRLAMA')
        toplam += yazdir(
            z4_varsayilanla_eziliyor(harita),
            'kısmi güncellemede varsayılana dönen alan yok',
            'data.get(\'alan\', VARSAYILAN) — gövdede alan yoksa\n'
            '   sessizce varsayılana döner. kdv_oran için bu, KDV\'nin\n'
            '   fark edilmeden %0 olması demektir.')

    print(f"\n{KALIN}")
    if toplam:
        print(f" ✗ TOPLAM {toplam} BULGU")
        print(f"{KALIN}")
        print("\n Her bulguyu koda bakarak doğrulayın. Yanlış pozitifse")
        print(" ilgili BEKLENEN_* listesine GEREKÇESİYLE ekleyin.")
        return 1
    print(" ✓ TÜM DENETİMLER TEMİZ")
    print(KALIN)
    return 0


if __name__ == '__main__':
    sys.exit(main())

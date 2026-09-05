#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — BAĞLAM DENETİMİ  ·  baglam_denetim.py
#
#  Bir formun BAŞLANGIÇ BAĞLAMINI (seçili cari, stok, sipariş)
#  kaybedip kaybetmediğini arar.
#
#  ── NEDEN ──
#    Üretimde iki kez yaşandı:
#      · Cari kartından "Alınan Çek" → çek formunda cari SEÇİLİ
#        GELMİYOR, alfabetik ilk cari seçili kalıyordu. Kullanıcı
#        fark etmezse hareket YANLIŞ CARİYE yazılırdı.
#      · Proforma siparişe dönüşünce `/siparis?ara=SIP-123`
#        adresine gidiliyordu ama sipariş sayfası parametreyi HİÇ
#        OKUMUYORDU; kullanıcı tüm listeye düşüyordu.
#
#    İkisi de SESSİZ: hata yok, ekran açılıyor, yalnızca bağlam yok.
#    Bu yüzden js_denetim (sözdizimi) ve form_denetim (alan) bunu
#    göremez.
#
#  ── B1 · URL BAĞLAMI OKUNMUYOR ──
#    `location.href = '/hedef?p=deger'` var ama hedef şablon
#    `p` parametresini hiç okumuyor.
#
#  ── B2 · SELECT ÖN SEÇİMİ DOĞRULANMIYOR ──
#    Seçenekleri API'den gelen bir `<select>`e `.value = X`
#    atanıyor ama sonuç KONTROL EDİLMİYOR. Eşleşme yoksa atama
#    sessizce başarısız olur.
#
#  ── B3 · BOŞ İLK SEÇENEK YOK ──
#    Dinamik select'te boş seçenek yoksa, başarısız ön seçim
#    listedeki İLK KAYDI seçili bırakır — yanlış veri sessizce
#    kaydedilir. Boş seçenek başarısızlığı görünür kılar.
#
#  ── KÖRLÜK TESTİ SONUCU (dürüst kapsam) ──
#    Bilinen iki hata geri konarak sınandı:
#      B1 → YAKALADI  (siparis.html url okumasi kaldirilinca)
#      B3 → KAÇIRDI   (cek.html bos secenegi kaldirilinca)
#
#    B3 hâlâ tarıyor ama güvenilirliği kanıtlanmadı; ona TEK
#    DAYANAK olarak güvenmeyin. B1 ve B2 sınanmış durumda.
#
#  Her bulguyu KODA BAKARAK doğrulayın; yanlış pozitifse ilgili
#  BEKLENEN_* listesine GEREKÇESİYLE ekleyin.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python baglam_denetim.py
# ══════════════════════════════════════════════════════════════════════
import re
import sys
from pathlib import Path

SABLON = Path('templates')
if not SABLON.is_dir():
    print("HATA: templates/ bulunamadı. Proje klasöründe çalıştırın.")
    sys.exit(1)

# ── Yanlış pozitifler ──
# B1: hedef parametreyi okumasa da sorun olmayan geçişler
BEKLENEN_URL_OKUNMAZ = {
    # Dışa aktarma ve yazdırma: sunucu tarafı uçlar, şablon okumaz.
    ('base.html', 'format'), ('base.html', 'ek'),
    ('proforma.html', 'mod'), ('fatura.html', 'mod'),
}

# B2: ön seçimi doğrulanmasa da güvenli select'ler
BEKLENEN_DOGRULANMAZ = {
    # fatura.html #tDoviz: seçenek listesi seçilecek değerle
    # (fatura dövizi) BAŞLIYOR — eşleşme garanti. Kod okunarak
    # doğrulandı.
    ('fatura.html', 'tDoviz'),
    # sabit_gider.html #sgAy: seçenekler 1..12 (SG_AYLAR), atama
    # `String(g.ay || 1)` — her zaman bu aralıkta. Eşleşme garanti.
    # Kod okunarak doğrulandı.
    ('sabit_gider.html', 'sgAy'),
}

# B3: boş ilk seçeneği olmaması normal olanlar
BEKLENEN_BOS_YOK = {
    ('fatura.html', 'tDoviz'),      # yukarıdaki gerekçe
}


def js_al(metin):
    """Şablondan <script> içeriğini toplar."""
    return '\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', metin, re.S))


def baslik(kod, ad, etiket):
    print()
    print("─" * 70)
    print(f" {kod} · {ad}   [{etiket}]")
    print("─" * 70)


def yazdir(bulgular, bos_mesaj):
    if not bulgular:
        print(f"   ✓ temiz — {bos_mesaj}")
        return 0
    for b in bulgular:
        print(f"   {b}")
    return len(bulgular)


sablonlar = {f.name: f.read_text(encoding='utf-8', errors='replace')
             for f in sorted(SABLON.glob('*.html'))}

print("═" * 70)
print(" MILESTONE ERP — BAĞLAM DENETİMİ")
print("═" * 70)
print(f" Şablon: {len(sablonlar)}")

toplam = 0

# ══ B1 · URL BAĞLAMI OKUNMUYOR ══
baslik('B1', 'URL BAĞLAMI OKUNMUYOR', 'SESSİZ BAĞLAM KAYBI')
b1 = []
for ad, metin in sablonlar.items():
    # `location.href` VE `<a href=` — ikisi de bağlam taşır.
    # İlk sürüm yalnızca location.href arıyordu ve dashboard'daki
    # `<a href="/cari?cari=X">` bağlam kaybını KAÇIRDI (parametre
    # adı `ac` olmalıydı; kullanıcı tüm listeyi görüyordu).
    adaylar = re.findall(r"location\.href\s*=\s*[`'\"]([^`'\"]+)[`'\"]", metin)
    adaylar += re.findall(r"""href=[`'\"](/[^`'\"]*[?][^`'\"]*)[`'\"]""", metin)
    for hedef in adaylar:
        if '?' not in hedef:
            continue
        yol = hedef.split('?')[0].strip('/').split('/')[0]
        if not yol or yol.startswith('api'):
            continue
        parametreler = re.findall(r'[?&](\w+)=', hedef)
        hedef_dosya = f'{yol}.html'
        # kasa-defteri gibi tireli yollar
        if hedef_dosya not in sablonlar:
            hedef_dosya = yol.replace('-', '_') + '.html'
        if hedef_dosya not in sablonlar:
            continue
        hedef_js = js_al(sablonlar[hedef_dosya])
        for p in parametreler:
            if (ad, p) in BEKLENEN_URL_OKUNMAZ:
                continue
            okunuyor = re.search(rf"get\(\s*['\"]{p}['\"]\s*\)", hedef_js)
            if not okunuyor:
                b1.append(f"✗ {ad} → /{yol}?{p}=…   "
                          f"{hedef_dosya} bu parametreyi OKUMUYOR")
toplam += yazdir(sorted(set(b1)), 'her URL bağlamı hedefte okunuyor')

# ══ B2 · SELECT ÖN SEÇİMİ DOĞRULANMIYOR ══
baslik('B2', 'SELECT ÖN SEÇİMİ DOĞRULANMIYOR', 'SESSİZ YANLIŞ KAYIT')
b2 = []
for ad, metin in sablonlar.items():
    js = js_al(metin)
    # API'den doldurulan select'ler
    dinamik = set()
    for m in re.finditer(r"getElementById\(['\"](\w+)['\"]\)\.innerHTML\s*=", js):
        sid = m.group(1)
        if re.search(rf'<select[^>]*id="{sid}"', metin):
            dinamik.add(sid)
    for sid in sorted(dinamik):
        if (ad, sid) in BEKLENEN_DOGRULANMAZ:
            continue
        atamalar = re.findall(
            rf"getElementById\(['\"]{sid}['\"]\)\.value\s*=\s*([^;\n]+)", js)
        # sabit değer ataması ('' veya 'USD') güvenli
        atamalar = [a for a in atamalar
                    if not re.match(r"^\s*['\"][^'\"]*['\"]\s*$", a.strip())]
        if not atamalar:
            continue
        # sonuç kontrol ediliyor mu
        # DOĞRULAMA ARAMASI: select doğrudan ya da bir DEĞİŞKEN
        # üzerinden kontrol edilmiş olabilir. İlk sürümde yalnızca
        # `sel` adını tanıyordum ve `_sipSec` gibi adları kaçırıyordu.
        dogrulama = re.search(
            rf"{sid}['\"]\)\.value\s*!==|"
            rf"\.value\s*!==\s*\w|"
            rf"querySelector\([^)]*option\[value", js)
        if not dogrulama:
            b2.append(f"✗ {ad:<18} #{sid:<14} ön seçim yapılıyor, "
                      f"SONUÇ KONTROL EDİLMİYOR")
toplam += yazdir(sorted(set(b2)), 'her ön seçim doğrulanıyor')

# ══ B3 · BOŞ İLK SEÇENEK YOK ══
baslik('B3', 'DİNAMİK SELECT’TE BOŞ İLK SEÇENEK YOK', 'İLK KAYIT SESSİZCE SEÇİLİ')
b3 = []
for ad, metin in sablonlar.items():
    js = js_al(metin)
    for m in re.finditer(
            r"getElementById\(['\"](\w+)['\"]\)\.innerHTML\s*=([^;]{0,400})", js, re.S):
        sid, dolum = m.group(1), m.group(2)
        if not re.search(rf'<select[^>]*id="{sid}"', metin):
            continue
        if (ad, sid) in BEKLENEN_BOS_YOK:
            continue
        # ÖN SEÇİM ARAMASI: doğrudan ya da DEĞİŞKEN üzerinden.
        # İlk sürüm yalnızca `getElementById(...).value =` arıyordu;
        # `const sel = getElementById('fCari'); sel.value = x`
        # kalıbını KAÇIRIYORDU — körlük testinde yakalandı.
        atanan = re.search(
            rf"getElementById\(['\"]{sid}['\"]\)\.value\s*=\s*(?!['\"])", js)
        if not atanan:
            # değişkene alınıp atanmış mı
            for dm in re.finditer(
                    rf"(?:const|let|var)\s+(\w+)\s*=\s*document\.getElementById\("
                    rf"['\"]{sid}['\"]\)", js):
                deg = dm.group(1)
                if re.search(rf"\b{deg}\.value\s*=\s*(?!['\"])", js):
                    atanan = dm
                    break
        if not atanan:
            continue
        if not re.search(r"<option value=[\"']{2}", dolum):
            b3.append(f"✗ {ad:<18} #{sid:<14} boş ilk seçenek yok — "
                      f"eşleşmezse İLK KAYIT seçili kalır")
toplam += yazdir(sorted(set(b3)), 'ön seçimli her select boş seçenekle başlıyor')

print()
print("═" * 70)
if toplam:
    print(f" ✗ TOPLAM {toplam} BULGU")
    print()
    print(" Her bulguyu koda bakarak doğrulayın. Yanlış pozitifse")
    print(" ilgili BEKLENEN_* listesine GEREKÇESİYLE ekleyin.")
else:
    print(" ✓ TEMİZ — form bağlamı hiçbir yerde sessizce kaybolmuyor")
print("═" * 70)
sys.exit(1 if toplam else 0)

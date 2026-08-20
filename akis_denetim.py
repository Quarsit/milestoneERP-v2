#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — İŞ AKIŞI ZİNCİRİ DENETİMİ
#
#  ── NE ARAR ──
#    PF1'de proforma akisinda bulunan UC HATA SINIFINI, sistemin
#    TAMAMINDA arar. Tek tek grep'lemek yerine kalibi tanimlayip
#    her modulde kovaliyoruz; boylece ileride eklenen kod da ayni
#    denetimden gecer.
#
#    A1 · SISTEM DURUMU ELLE ATANABILIYOR      [VERI BUTUNLUGU]
#         Bir modulun durumunu BASKA BIR MODULUN uc noktasi
#         yaziyor (or. fatura kesilince proforma 'Faturalandi'),
#         ama ayni durum elle degistirme ucunun gecerli listesinde
#         de var.
#
#         AYIRT EDICI: "sistem de yaziyor" TEK BASINA yeterli
#         degil — 'Gonderildi' hem elle hem e-posta gonderiminde
#         yazilir ve ikisi de dogrudur. Asil tehlike CAPRAZ MODUL
#         yazimidir: o durum bir ZINCIRIN SONUCUDUR, elle atanirsa
#         zincir atlanir. Olculdu (PF1 oncesi): proforma elle
#         'Faturalandi' yapilabiliyordu; ne siparis ne fatura vardi.
#
#    A2 · DONUSUM DURUMU GUNCELLEMIYOR         [OLCUM KAYBI]
#         `*_donustur` ucu hedef kaydi olusturup kaynak kayda
#         `<hedef>_id` yaziyor ama kaynagin `durum` alanina
#         DOKUNMUYOR. Sonuc: bekleyen ile tamamlanan ayirt
#         edilemiyor. Olculdu: siparise donusen proforma
#         'Onaylandi' kaliyordu.
#
#    A3 · NOT NULL ASIMETRISI                  [GECIKMELI COKME]
#         Kaynak modelde serbest, hedef modelde NOT NULL olan
#         ayni adli alan. Kayit sorunsuz giriyor, hata HAFTALAR
#         SONRA donusumde 500 olarak cikiyor. Olculdu:
#         ProformaKalem.urun_tip serbest ↔ SiparisKalem.urun_tip
#         NOT NULL.
#
#         YALNIZCA GERCEK DONUSUM CIFTLERI karsilastirilir. Ilk
#         surum ayni adli her alani her modelde kiyasliyordu ve
#         `Maliyet.aktif` ile `Banka.aktif` gibi ILGISIZ ciftleri
#         bulgu sayiyordu. Gurultulu denetim, gormezden gelinmeyi
#         ogretir.
#
#  ── YANLIŞ POZİTİF ──
#    Betik IDDIA ETMEZ, GOSTERIR. Her bulgu koda bakilarak
#    dogrulanmali. Gercekten kasitliysa asagidaki BEKLENEN_*
#    listesine GEREKCESIYLE yazilmali — susturmak degil,
#    kararı kayda gecirmek icin.
#
#  ── HİÇBİR ŞEY DEĞİŞTİRMEZ ──  Yalnızca kaynak kodu okur.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python akis_denetim.py
#      venv/bin/python akis_denetim.py --tam
# ══════════════════════════════════════════════════════════════════════
import re
import sys
from pathlib import Path

APP = Path('flask_app.py')
MOD = Path('models.py')
for _d in (APP, MOD):
    if not _d.exists():
        print(f"HATA: {_d} bu klasörde yok. Proje klasöründe çalıştırın.")
        sys.exit(1)

TAM = '--tam' in sys.argv
kaynak = APP.read_text(encoding='utf-8', errors='replace').replace('\r\n', '\n')
modeller = MOD.read_text(encoding='utf-8', errors='replace').replace('\r\n', '\n')

# ── Kasıtlı durumlar: gerekçesiyle ────────────────────────────────
BEKLENEN_A1 = {
    # PF1 ile kapatildi: bu ikisi artik SISTEM_DURUMLARI icinde ve
    # elle atanmaya calisilirsa 400 doner. Gecerli listede olmalari
    # DOGRU — sistem onlari yaziyor.
    ('proforma', 'Faturalandi'),
    ('proforma', 'Siparise Donustu'),

    # 'Iptal' — siparis IPTAL edilince bagli proformalar da iptal
    # oluyor (api_siparis_guncelle:8360). Ama iptal GERI DONUSU
    # OLMAYAN bir kapatma degil, aksine 'Iptal' -> 'Taslak' geri
    # acilabiliyor. Elle iptal etmek de mesru: kullanici teklifi
    # geri cekebilmeli. Zincir ATLANMIYOR.
    ('proforma', 'Iptal'),

    # 'Onaylandi' — fatura IPTAL edilince proforma 'Faturalandi'dan
    # geri 'Onaylandi'ya cekiliyor (api_fatura_durum:16389). Bu bir
    # GERI ALMA; ileri yonlu bir zincirin sonucu degil. Elle onay
    # zaten akisin normal adimi ve cift kontrolu var (hazirlayan
    # kendi teklifini onaylayamiyor).
    ('proforma', 'Onaylandi'),
}

# A2 muafiyeti: (uc nokta yolu, degisken) — donusumun KAYNAGI
# olmayan, yalnizca yan kayit guncelleyen atamalar.
BEKLENEN_A2 = {
    # `mevcut` bir Rezervasyon kaydi; donusumun kaynagi DEGIL,
    # proformanin rezervasyonlari siparise tasiniyor. Rezervasyon
    # modelinde `durum` alani ZATEN YOK, dolayisiyla "durumu
    # guncellenmiyor" olcumu orada anlamsiz. Kod okunarak
    # dogrulandi (models.py: Rezervasyon).
    ('/api/proforma/<proforma_id>/siparise_donustur', 'mevcut'),
}

BEKLENEN_A3 = {
    # 'id' her modelde birincil anahtar; asimetri degil.
    'id',
    # 'cari_id' CRM-A ile eklendi ve before_insert dinleyicisi
    # dolduruyor; CariErisim/CariKisi'de NOT NULL olmasi dogru,
    # cunku o kayitlar musterisiz var olamaz.
    'cari_id',
    # 'kullanici' oturumdan yaziliyor.
    'kullanici',

    # 'urun_tip' — ProformaKalem'de serbest, SiparisKalem'de NOT
    # NULL. Asimetri MODELDE duruyor ama PF1 ile UC NOKTADA
    # kapatildi: proforma ekleme ve guncellemede urun_tip zorunlu ve
    # gecerli degerlerle sinirli (GECERLI_URUN_TIP). Modeli
    # degistirmek mevcut kayitlari bozacagi icin dogrulama katmani
    # tercih edildi. Test: tipsiz kalem 400 doner.
    'urun_tip',

    # 'sira' — kalem sira numarasi. Donusumde ISTEMCIDEN GELMIYOR,
    # dongu sayacindan uretiliyor: `sira=idx + 1`
    # (api_proforma_siparise_donustur). Kaynakta bos olmasi hedefi
    # etkilemez; asimetri gorunuste, pratikte yok. Kod okunarak
    # dogrulandi.
    'sira',
}

print("═" * 74)
print(" İŞ AKIŞI ZİNCİRİ DENETİMİ")
print("═" * 74)
print()

# ══ Model alanlarını çıkar ════════════════════════════════════════
model_alan = {}   # model -> {alan: nullable_false_mi}
for m in re.finditer(r"^class (\w+)\(db\.Model\):", modeller, re.M):
    ad = m.group(1)
    bas = m.end()
    son = modeller.find('\nclass ', bas)
    son = son if son > 0 else len(modeller)
    govde = modeller[bas:son]
    alanlar = {}
    # PARANTEZ SAYAN AYRISTIRICI — duzenli ifade DEGIL.
    #
    # Ilk surum `db.Column\((.*?)\)` desenini re.S ile kullaniyordu;
    # nokta satir sonunu da yakaladigi icin desen BIRDEN COK ALAN
    # TANIMINI yutuyordu. Korluk testinde olculdu: SiparisKalem'in
    # ~25 alanindan yalnizca 3'u goruluyordu ve A3 pratikte kordu.
    #
    # Alan tanimlari cok satira yayilabildigi icin parantez
    # dengesine bakiliyor; satir sonu yorumlari da boylece
    # kendiliginden dogru ele aliniyor.
    _sat = govde.split('\n')
    _i = 0
    while _i < len(_sat):
        _m = re.match(r"^\s{4}(\w+)\s*=\s*db\.Column\(", _sat[_i])
        if not _m:
            _i += 1
            continue
        _parca = _sat[_i]
        _derinlik = _parca.count('(') - _parca.count(')')
        _j = _i
        while _derinlik > 0 and _j + 1 < len(_sat):
            _j += 1
            _parca += ' ' + _sat[_j]
            _derinlik += _sat[_j].count('(') - _sat[_j].count(')')
        alanlar[_m.group(1)] = 'nullable=False' in _parca
        _i = _j + 1
    model_alan[ad] = alanlar

print(f" Model         : {len(model_alan)}")

# ══ Uç nokta gövdelerini çıkar ════════════════════════════════════
satirlar = kaynak.split('\n')
uclar = []
for i, s in enumerate(satirlar):
    m = re.match(r"\s*@app\.route\('([^']+)'(?:,\s*methods=\[([^\]]*)\])?", s)
    if not m:
        continue
    j = i + 1
    while j < len(satirlar) and not re.match(r"\s*def ", satirlar[j]):
        j += 1
        if j - i > 6:
            break
    if j >= len(satirlar) or not re.match(r"\s*def ", satirlar[j]):
        continue
    girinti = len(satirlar[j]) - len(satirlar[j].lstrip())
    k = j + 1
    while k < len(satirlar):
        t = satirlar[k]
        if t.strip() and (len(t) - len(t.lstrip())) <= girinti \
                and not t.lstrip().startswith('#'):
            break
        k += 1
    uclar.append({'yol': m.group(1),
                  'ad': re.match(r"\s*def (\w+)", satirlar[j]).group(1),
                  'govde': '\n'.join(satirlar[j:k]), 'satir': j + 1})

print(f" Uç nokta      : {len(uclar)}")
print()


def _kod(metin):
    """Yorum ve docstring satırlarını at — açıklamada geçen bir
    kelime kod sayılmamalı."""
    cikti, ds = [], False
    for l in metin.split('\n'):
        t = l.strip()
        if t.count('"""') == 1:
            ds = not ds
            continue
        if ds or t.startswith('#') or t.startswith('"""'):
            continue
        cikti.append(l)
    return '\n'.join(cikti)


bulgular = {'A1': [], 'A2': [], 'A3': []}

# ══ A1 · Sistem durumu elle atanabiliyor ══════════════════════════
# Sistemin OTOMATIK yazdigi durumlar: `<sey>.durum = 'X'` kaliplari,
# durum ucunun DISINDA geciyorsa.
durum_uclari = {u['ad']: u for u in uclar if u['yol'].endswith('/durum')}
sistem_yazilan = {}   # modul -> {durum}
IPUCU = {'proforma': ('pf', 'proforma'), 'fatura': ('f', 'fat', 'fatura'),
         'siparis': ('sip', 'siparis'), 'cek': ('cek',),
         'sevkiyat': ('sv', 'sevk', 'sevkiyat')}
for u in uclar:
    # Ucun KENDI modulu — yolun ikinci parcasi (/api/<modul>/...)
    _p = u['yol'].split('/')
    ait_modul = _p[2] if len(_p) > 2 else ''
    for m in re.finditer(r"\b(\w+)\.durum\s*=\s*'([^']+)'", _kod(u['govde'])):
        degisken, deger = m.group(1), m.group(2)
        for modul, ipuclari in IPUCU.items():
            if degisken not in ipuclari:
                continue
            # YALNIZCA CAPRAZ MODUL yazimi. Kendi modulunun durumunu
            # kendi ucunun yazmasi normaldir ('Gonderildi' gibi).
            if modul != ait_modul:
                sistem_yazilan.setdefault(modul, set()).add(deger)

for ad, u in durum_uclari.items():
    modul = u['yol'].split('/')[2]
    kod = _kod(u['govde'])
    m = re.search(r"gecerli_durumlar\s*=\s*\[([^\]]*)\]", kod)
    if not m:
        continue
    gecerli = {x.strip().strip("'\"") for x in m.group(1).split(',') if x.strip()}
    # Elle engellenenler
    engelli = set(re.findall(r"^\s*'([^']+)':\s*'", kod, re.M)) \
        if 'SISTEM_DURUMLARI' in kod else set()
    for d in sorted(sistem_yazilan.get(modul, set()) & gecerli):
        if (modul, d) in BEKLENEN_A1 or d in engelli:
            continue
        bulgular['A1'].append((modul, d, u['yol'], u['satir']))

# ══ A2 · Dönüşüm durumu güncellemiyor ═════════════════════════════
for u in uclar:
    if 'donustur' not in u['ad'] and 'donustur' not in u['yol']:
        continue
    kod = _kod(u['govde'])
    # KAYNAK degiskeni yakala: `p.siparis_id = sip.id` -> 'p'
    fk = re.findall(r"\b(\w+)\.(\w+_id)\s*=\s*\w+\.id", kod)
    if not fk:
        continue
    # KAYNAGIN KENDI durumu yaziliyor mu?
    #
    # Ilk surum govdedeki HERHANGI bir `.durum =` atamasini yeterli
    # sayiyordu. Korluk testinde yakalandi: donusum govdesinde
    # `stok.durum = 'Satildi'` var ve bu, kaynak proformanin durumu
    # hic yazilmasa bile denetimi susturuyordu.
    for _degisken, _alan in sorted(set(fk)):
        if (u['yol'], _degisken) in BEKLENEN_A2:
            continue
        if re.search(rf"\b{re.escape(_degisken)}\.durum\s*=", kod):
            continue
        bulgular['A2'].append((u['yol'], f"{_degisken}.{_alan}", u['satir']))

# ══ A3 · NOT NULL asimetrisi ══════════════════════════════════════
# GERCEK donusum ciftleri: kaynak -> hedef. Sistemde bir kayit
# otekine DONUSUYOR ve alanlar kopyalaniyor.
DONUSUM_CIFTLERI = [
    ('ProformaKalem', 'SiparisKalem'),   # proforma -> siparis
    ('Proforma', 'Fatura'),              # proforma -> fatura
    ('Siparis', 'Fatura'),               # siparis  -> fatura
    ('Siparis', 'Sevkiyat'),             # siparis  -> sevkiyat
    ('SiparisKalem', 'Konteyner'),       # kalem    -> konteyner
    ('Fatura', 'SatisKaydi'),            # fatura   -> satis kaydi
]
for kaynak_m, hedef_m in DONUSUM_CIFTLERI:
    k_alan = model_alan.get(kaynak_m, {})
    h_alan = model_alan.get(hedef_m, {})
    for alan, hedef_nn in sorted(h_alan.items()):
        if alan in BEKLENEN_A3 or not hedef_nn:
            continue
        if alan not in k_alan:
            continue          # kaynakta hic yok — kopyalanmiyor
        if k_alan[alan]:
            continue          # kaynakta da zorunlu — asimetri yok
        bulgular['A3'].append((alan, [f'{hedef_m} (hedef)'],
                               [f'{kaynak_m} (kaynak)']))


def _yaz(kod, baslik, liste, aciklama, bicim):
    print("─" * 74)
    print(f" {kod} · {baslik}")
    print("─" * 74)
    if not liste:
        print("   ✓ temiz")
        print()
        return
    print(f"   {len(liste)} bulgu — {aciklama}")
    for x in (liste if TAM else liste[:12]):
        print("     " + bicim(x))
    if not TAM and len(liste) > 12:
        print(f"     … {len(liste) - 12} tane daha (--tam ile hepsi)")
    print()


_yaz('A1', "SİSTEM DURUMU ELLE ATANABİLİYOR   [VERİ BÜTÜNLÜĞÜ]",
     bulgular['A1'],
     "sistem bu durumu başka yerde yazıyor; elle atanırsa zincir atlanır",
     lambda x: f"{x[0]:<12} '{x[1]}'   {x[2]}  (satır {x[3]})")

_yaz('A2', "DÖNÜŞÜM DURUMU GÜNCELLEMİYOR   [ÖLÇÜM KAYBI]",
     bulgular['A2'],
     "yabancı anahtar yazılıyor ama kaynağın durumu değişmiyor",
     lambda x: f"{x[0]:<44} yazıyor: {x[1]}  (satır {x[2]})")

_yaz('A3', "NOT NULL ASİMETRİSİ   [GECİKMELİ ÇÖKME]",
     bulgular['A3'],
     "aynı alan bir modelde serbest, diğerinde zorunlu",
     lambda x: f"{x[0]:<18} ZORUNLU: {', '.join(x[1])[:30]:<32} "
               f"serbest: {', '.join(x[2])[:30]}")

toplam = sum(len(v) for v in bulgular.values())
print("═" * 74)
if not toplam:
    print(" ✓ ÜÇ DENETİM DE TEMİZ")
    print("═" * 74)
    sys.exit(0)
print(f" ✗ TOPLAM {toplam} BULGU")
print()
print(" Her bulguyu KODA BAKARAK doğrulayın. Betik iddia etmez, gösterir.")
print(" Kasıtlıysa BEKLENEN_* listesine GEREKÇESİYLE yazın — susturmak")
print(" değil, kararı kayda geçirmek için.")
print("═" * 74)
sys.exit(1)

#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — NAKİT ZİNCİRİ  ·  NK1  (A adımı)
#
#  ── ÖN KOŞUL ──
#      yama_ck2_olu_cek.py --uygula   (CEK_OLU_DURUMLAR buradan gelir)
#
#  ── SORUN ──
#    Sistem tahsilatı, asıl faturanın `borc` alanını AZALTARAK
#    kaydetmiyor — ayrı bir kapatma satırı açıyor. Projeksiyon ise
#    ham `borc` değerini okuyordu. Sonuç: tahsil edilmiş fatura
#    sonsuza kadar "bekleyen tahsilat" olarak kalıyor.
#
#    Gerçek uç noktalarla ölçüldü (100.000 USD fatura, tamamı nakit
#    tahsil edildi):
#        açılış (kasada olan)  : 100.000
#        hâlâ "bekleyen" giriş : 100.000
#        TOPLAM görünen        : 200.000   ← gerçeğin iki katı
#
#    `kapatildi` alanı da bu işi görmüyor: kod tabanında hiçbir yerde
#    True yapılmıyor, ölü bir alan.
#
#  ── ÇÖZÜM: FIFO KAPATMA ──
#    Her cari + döviz + yön grubunda, kapatma satırları yükümlülüklere
#    VADE SIRASIYLA (en eski önce) uygulanır. Artan kısım projeksiyona
#    girer.
#
#        Fatura 100.000, vade +30 gün       → yükümlülük
#        Tahsilat 100.000                   → kapatma
#        kalan = 0                          → projeksiyona GİRMEZ ✓
#
#        Fatura 100.000 · kısmi tahsilat 40.000
#        kalan = 60.000, vade +30 gün       → projeksiyona girer ✓
#
#  ── NEDEN NETLEŞTİRME DEĞİL ──
#    "Cari bakiyeyi topla, netini yaz" daha kolaydı ama ZAMANLAMAYI
#    bozardı. Aynı cariyle hem satış hem alış varsa:
#        satış 100.000 vade +30 · alış 80.000 vade +10
#    net 20.000 der ve 10. gündeki 80.000'lik ÇIKIŞI gizler. Oysa
#    nakit sıkışıklığı tam orada yaşanır. Bu yüzden yükümlülükler
#    yön bazında ayrı tutulur.
#
#  ── BORÇ/ALACAK SÜTUNU YETMEZ ──
#    Bir `alacak` satırı hem alış faturası (ödenecek borç) hem de
#    tahsilat (alınan para) olabilir. Ayrımı `kaynak` yapar; bu
#    yüzden iki liste var: NAKIT_YUKUMLULUK ve NAKIT_KAPATMA.
#
#  ── ÖLÜ ÇEK ──
#    Karşılıksız/iade çekin kapatma satırı SAYILMAZ — para hiç
#    gelmedi. Böylece asıl fatura projeksiyona kendiliğinden geri
#    döner, kendi vadesiyle.
#
#    CK2'nin açtığı `cek_olu` ters kaydı nakit tarafında SAYILMAZ:
#    o kayıt cari bakiyeyi düzeltmek için var. Hem onu hem geri dönen
#    faturayı saymak çift kayıt olurdu.
#
#  KULLANIM (proje klasöründe):
#      python yama_nk1_nakit_zincir.py            # rapor
#      python yama_nk1_nakit_zincir.py --uygula   # uygula
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

_h = APP.read_text(encoding='utf-8', errors='replace')
if 'CEK_OLU_DURUMLAR' not in _h:
    print("✗ ÖN KOŞUL: önce yama_ck2_olu_cek.py uygulanmalı.")
    print("  (Ölü çek listesi oradan geliyor.)")
    sys.exit(1)
if '_nakit_kalemleri' not in _h:
    print("✗ ÖN KOŞUL: nakit akışı modülü kurulu değil (NA2).")
    sys.exit(1)


def dogrula(kaynak):
    try:
        compile(kaynak, 'flask_app.py', 'exec')
        return None
    except SyntaxError as exc:
        return f"satır {exc.lineno}: {exc.msg}"


# ══ A) Sınıflandırma ═══════════════════════════════════════════════
A_ESKI = """    # Cari hareketin nakit projeksiyonuna GIRMEYECEGI kaynaklar.
    # Her biri AYRI sebeple disarida:
    #
    #   'cek'          Cek kendi tablosundan sayiliyor (asagida,
    #                  Cek.query dongusu).
    #   'tahsilat'     Bu hareket CEK ALINIRKEN aciliyor — bkz.
    #                  api_cek_ekle(). Yani cekin ta kendisi.
    #                  Sayilsaydi ayni tahsilat hem Cek hem
    #                  CariHareket uzerinden IKI KEZ gorunurdu.
    #   'virman'       Parayi zaten kasaya tasimis; tutar kasa.bakiye
    #                  icinde, yani acilis bakiyesine dahil.
    #   'mahsup'       Hesap denklestirme — nakit hareketi yok.
    #   'avans_devir'  Hesaplar arasi avans aktarimi — nakit hareketi
    #                  yok.
    #
    # Fatura tablosu HIC okunmuyor: fatura kesilince cari hareket
    # zaten aciliyor. Ikisini de okumak her borcu iki kez sayardi.
    NAKIT_HARIC_KAYNAK = ('cek', 'tahsilat', 'virman', 'mahsup', 'avans_devir')"""

A_YENI = """    # Cari hareketlerin nakit projeksiyonundaki ROLU.
    #
    # BORC/ALACAK sutunu tek basina YETMEZ: bir 'alacak' satiri hem
    # alis faturasi (odenecek borc) hem de tahsilat (alinan para)
    # olabilir. Ikisi zit yonde nakit demek. Ayrimi kaynak yapar.

    # YUKUMLULUK: gelecekte nakit hareketi DOGURAN kayitlar.
    NAKIT_YUKUMLULUK = ('fatura', 'maliyet', 'stok', 'siparis_teslim',
                        'sicak_satis', 'rezervasyon', 'sabit',
                        'elle', 'manuel')

    # KAPATMA: yukumlulugu azaltan kayitlar. Ya para zaten hareket
    # etti (tahsilat, odeme, virman), ya baska bir enstrumana devredildi
    # (cek — Cek tablosundan ayrica sayiliyor), ya da hesaplar arasi
    # denklestirme yapildi (mahsup, avans_devir).
    NAKIT_KAPATMA = ('tahsilat', 'odeme', 'cek', 'virman',
                     'mahsup', 'avans_devir')

    # Ikisi de degil — yalnizca muhasebe kaydi, nakit tarafinda isi yok:
    #   'cek_olu'            CK2'nin olen cek icin actigi ters kayit.
    #                        Cari bakiyeyi duzeltmek icin var. Olu cekin
    #                        kapatma satiri zaten sayilmadigindan asil
    #                        fatura kendiliginden geri donuyor; ikisini
    #                        birden saymak cift kayit olurdu.
    #   'otomatik_kur_farki' Kur degerlemesi — nakit hareketi yok.

    # Fatura tablosu HIC okunmuyor: fatura kesilince cari hareket
    # zaten aciliyor. Ikisini de okumak her borcu iki kez sayardi."""

# ══ B) FIFO kapatma döngüsü ════════════════════════════════════════
B_ESKI = """        # ── 1) CARİ HAREKETLER ────────────────────────────────
        for h in CariHareket.query.filter(
                CariHareket.kapatildi.isnot(True)).all():
            if (h.kaynak or '') in NAKIT_HARIC_KAYNAK:
                continue
            borc = float(h.borc or 0)
            alacak = float(h.alacak or 0)
            if borc <= 0 and alacak <= 0:
                continue
            # borc   = musteri bize borclu       → GIRIS
            # alacak = biz tedarikciye borcluyuz → CIKIS
            yon = 'giris' if borc > 0 else 'cikis'
            tutar = borc if borc > 0 else alacak
            vade = h.vade_tarihi
            _ad = (h.cari_unvan or h.cari_id or '').strip()
            _tip = (h.islem_tip or '').strip()
            kalemler.append({
                'tarih': vade.isoformat() if vade else None,
                'yon': yon, 'tutar': q3(tutar),
                'doviz': (h.doviz or 'TRY').upper(),
                'kaynak': 'cari', 'kayit_id': h.id,
                'aciklama': f"{_ad} — {_tip}".strip(' —') or 'Cari hareket',
                'vadesiz': vade is None,
            })"""

B_YENI = '''        # ── 1) CARİ HAREKETLER — FIFO KAPATMA ─────────────────
        # Sistem tahsilati, asil faturanin borc'unu AZALTMIYOR; ayri
        # bir kapatma satiri aciyor. Ham borc'u okumak, tahsil edilmis
        # faturayi da "bekleyen" gostermek demek.
        #
        # Bu yuzden her cari + doviz + yon grubunda kapatmalar
        # yukumluluklere VADE SIRASIYLA uygulanir; artan kisim
        # projeksiyona girer.

        # Olu cekler (karsiliksiz / iade) kapatma SAYILMAZ — para hic
        # gelmedi. Boylece asil fatura kendi vadesiyle geri doner.
        _olu_cek = {c.id for c in Cek.query.filter(
            Cek.durum.in_(CEK_OLU_DURUMLAR)).all()}

        _yuk, _kap = {}, {}
        for h in CariHareket.query.all():
            _k = (h.kaynak or '')
            _borc = float(h.borc or 0)
            _alacak = float(h.alacak or 0)
            if _borc <= 0 and _alacak <= 0:
                continue
            _grup = h.cari_id or h.cari_unvan or '?'
            _dv = (h.doviz or 'TRY').upper()

            if _k in NAKIT_YUKUMLULUK:
                if h.kapatildi:
                    # Alan sistemde kullanilmiyor ama isaretlenmisse saygi duy.
                    continue
                # borc   = musteri bize borclu       → GIRIS
                # alacak = biz tedarikciye borcluyuz → CIKIS
                _yon = 'giris' if _borc > 0 else 'cikis'
                _yuk.setdefault((_grup, _dv, _yon), []).append(h)

            elif _k in NAKIT_KAPATMA:
                if (_k == 'cek' and h.baglanti_tip == 'cek'
                        and h.baglanti_id in _olu_cek):
                    continue
                # Alacak sutunu BORC yukumlulugunu kapatir, ve tersi.
                _yon = 'giris' if _alacak > 0 else 'cikis'
                _kap[(_grup, _dv, _yon)] = (
                    _kap.get((_grup, _dv, _yon), 0.0)
                    + (_alacak if _alacak > 0 else _borc))

        for _anahtar, _hs in _yuk.items():
            _grup, _dv, _yon = _anahtar
            _kalan_kapatma = _kap.get(_anahtar, 0.0)
            # En eski vade once kapanir. Vadesizler en sona — vadesi
            # belli olan bir borc, belirsiz olandan once odenir.
            _hs.sort(key=lambda x: (x.vade_tarihi is None,
                                    x.vade_tarihi or date.max))
            for h in _hs:
                _tutar = float(h.borc or 0) if _yon == 'giris' else float(h.alacak or 0)
                if _kalan_kapatma > 0:
                    _dus = min(_tutar, _kalan_kapatma)
                    _tutar -= _dus
                    _kalan_kapatma -= _dus
                if _tutar <= 0.005:   # kurus artigi — kapanmis say
                    continue
                _vade = h.vade_tarihi
                _ad = (h.cari_unvan or h.cari_id or '').strip()
                _tip = (h.islem_tip or '').strip()
                _tam = float(h.borc or 0) if _yon == 'giris' else float(h.alacak or 0)
                _not = '' if abs(_tutar - _tam) < 0.005 else ' (kısmi)'
                kalemler.append({
                    'tarih': _vade.isoformat() if _vade else None,
                    'yon': _yon, 'tutar': q3(_tutar),
                    'doviz': _dv,
                    'kaynak': 'cari', 'kayit_id': h.id,
                    'aciklama': (f"{_ad} — {_tip}{_not}".strip(' —')
                                 or 'Cari hareket'),
                    'vadesiz': _vade is None,
                })'''

BLOKLAR = [
    ("kaynak sınıflandırması (yükümlülük / kapatma)", A_ESKI, A_YENI, 'NAKIT_YUKUMLULUK = ('),
    ("FIFO kapatma döngüsü",                          B_ESKI, B_YENI, '_kalan_kapatma = _kap.get'),
]

print("═" * 70)
print(" NK1 · NAKİT ZİNCİRİ — FIFO kapatma  (A adımı)")
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

if 'NAKIT_HARIC_KAYNAK' in icerik:
    print(" ✗ NAKIT_HARIC_KAYNAK hâlâ kullanımda — beklenmedik durum.")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)
print(" ✓ eski sınıflandırmadan artık kalmadı")

hata = dogrula(icerik)
if hata:
    print(f" ✗ SÖZDİZİMİ HATASI → {hata}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)
print(" ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_nk1_nakit_zincir.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = APP.with_name(f'flask_app.py.yedek-{damga}')
shutil.copy2(APP, yedek)
APP.write_bytes(icerik.encode('utf-8'))
print(f" ✓ flask_app.py  (yedek: {yedek.name})")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI  (A adımı)")
print()
print(" Tahsil edilmiş faturalar projeksiyondan düşüyor;")
print(" kısmi tahsilatta yalnızca kalan görünüyor.")
print("═" * 70)

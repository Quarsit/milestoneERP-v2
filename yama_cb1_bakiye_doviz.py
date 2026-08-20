#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — CARİ BAKİYE DÖVİZ AYRIMI  ·  CB1
#
#  ── ÖLÇÜLEN HATA ──
#    /api/cari/<id>/bakiye FARKLI DOVIZLERI AYNI TOPLAMA ATIYOR:
#
#        borc   = sum(h.borc)      # USD, TRY, EUR hepsi bir arada
#        alacak = sum(h.alacak)
#        net    = borc - alacak
#
#    Uretilen sonuc (gercek uc noktayla olculdu):
#        10.000 USD borc + 200.000 TRY tahsilat
#        -> {'borc': 10000, 'alacak': 200000, 'net': -190000}
#
#    Musteri 5.000 USD BORCLU iken ekranda 190.000 ALACAKLI
#    gorunuyor. "190.000" hangi para biriminde? Hicbirinde —
#    anlamsiz bir sayi.
#
#  ── NEDEN ŞİMDİYE KADAR PATLAMADI ──
#    Ekran bu ucu KULLANMIYOR; cari sayfasi bakiyeyi
#    /api/rapor/yaslandirilmis_cari'den aliyor. Yani gorunur zarar
#    yok. Ama uc nokta acik ve yanlis rakam donduruyor; yarin bir
#    ekrana baglanirsa hata gorunur hale gelir.
#
#  ── DÜZELTME ──
#    Sistemde `borc_try` / `alacak_try` alanlari ZATEN VAR ve islem
#    gunu kuruyla dolduruluyor (api_cari_finansal_ozet bunlari dogru
#    kullaniyor). Bakiye ucu da onlari kullanacak:
#
#      · borc/alacak/net  → TRY KARSILIGI (tek anlamli sayi)
#      · dovizler         → her doviz AYRI (ham tutarlar)
#      · para_birimi      → carinin kendi para birimi
#
#    Eski TRY kayitlarinda borc_try bos olabilir; finansal_ozet'teki
#    ayni geri dusme uygulaniyor (doviz TRY ise ham tutar kullanilir).
#
#  ── DÖVİZ AYRIMI NEDEN KORUNUYOR ──
#    Tek TRY sayisi kolay okunur ama KUR RISKINI GIZLER — nakit
#    akisi ekraninda ayni sebeple uc dovizi ayri gosteriyoruz.
#    Ikisi birden donuluyor; cagiran hangisine ihtiyaci varsa onu
#    kullanir.
#
#  KULLANIM (proje klasöründe):
#      python yama_cb1_bakiye_doviz.py            # rapor
#      python yama_cb1_bakiye_doviz.py --uygula
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

ESKI = """        hareketler = CariHareket.query.filter_by(cari_id=cari_id).all()
        borc = sum(h.borc or 0 for h in hareketler)
        alacak = sum(h.alacak or 0 for h in hareketler)
        net = borc - alacak
        return jsonify({'borc': borc, 'alacak': alacak, 'net': net})"""

YENI = '''        hareketler = CariHareket.query.filter_by(cari_id=cari_id).all()

        # DOVIZLER AYRI TOPLANIR.
        #
        # Onceki surum farkli dovizleri ayni toplama atiyordu:
        #     10.000 USD borc + 200.000 TRY tahsilat -> net -190.000
        # Musteri 5.000 USD BORCLU iken 190.000 ALACAKLI gorunuyordu
        # ve o sayi hicbir para biriminde anlamli degildi.
        dovizler = {}
        for h in hareketler:
            dv = (h.doviz or 'TRY').upper()
            k = dovizler.setdefault(dv, {'borc': 0.0, 'alacak': 0.0})
            k['borc'] += float(h.borc or 0)
            k['alacak'] += float(h.alacak or 0)
        for dv, k in dovizler.items():
            k['borc'] = q3(k['borc'])
            k['alacak'] = q3(k['alacak'])
            k['net'] = q3(float(k['borc']) - float(k['alacak']))

        # TRY KARSILIGI — islem gunu kuruyla, `borc_try`/`alacak_try`
        # alanlarindan. Bu alanlar zaten dolduruluyor ve
        # api_cari_finansal_ozet onlari boyle kullaniyor.
        #
        # Eski TRY kayitlarinda borc_try bos olabilir; o durumda ham
        # tutar kullanilir (finansal_ozet ile ayni geri dusme).
        borc_try = alacak_try = 0.0
        for h in hareketler:
            _dv = (h.doviz or 'TRY').upper()
            _bt, _at = float(h.borc_try or 0), float(h.alacak_try or 0)
            if _dv == 'TRY':
                if not _bt:
                    _bt = float(h.borc or 0)
                if not _at:
                    _at = float(h.alacak or 0)
            borc_try += _bt
            alacak_try += _at

        _c = db.session.get(Cari, cari_id)
        return jsonify({
            # TEK ANLAMLI SAYI: TRY karsiligi.
            'borc': q3(borc_try), 'alacak': q3(alacak_try),
            'net': q3(borc_try - alacak_try),
            'birim': 'TRY',
            # DOVIZ AYRIMI KORUNUR: tek TRY sayisi kolay okunur ama
            # KUR RISKINI GIZLER. Nakit akisinda da ayni sebeple uc
            # dovizi ayri gosteriyoruz.
            'dovizler': dovizler,
            'para_birimi': (_c.para_birimi if _c else None) or 'TRY',
        })'''

IMZA = "'birim': 'TRY',"

print("═" * 70)
print(" CB1 · CARİ BAKİYE DÖVİZ AYRIMI")
print("═" * 70)
print()

ham = APP.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


if uyarla(IMZA) in ham or IMZA in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

e = uyarla(ESKI)
adet = ham.count(e)
if adet != 1:
    print(f" ✗ Kalıp {adet} kez bulundu (1 bekleniyordu). DOSYAYA DOKUNULMADI.")
    sys.exit(1)

icerik = ham.replace(e, uyarla(YENI), 1)

try:
    compile(icerik, 'flask_app.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print("  ✓ uygulanacak          döviz bazlı bakiye + TRY karşılığı")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_cb1_bakiye_doviz.py --uygula")
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
print(" NOT: 'borc'/'alacak'/'net' artık TRY KARŞILIĞI döndürüyor.")
print("      Ham döviz tutarları 'dovizler' altında.")
print("═" * 70)

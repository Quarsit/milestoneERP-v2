#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — STOK SİLME MALİ KARARI AYIRIR  ·  SF1
#
#  ── ÖLÇÜLEN DAVRANIŞ ──
#    Stok silinince sistem, bagli alis faturasinin cari borcundan
#    o stogun PAYINI SESSIZCE DUSUYOR (YAMA C1). Kullaniciya
#    sorulmuyor.
#
#  ── NEDEN YANLIŞ ──
#    Stok miktarindaki degisiklik ile fatura tutarindaki degisiklik
#    AYNI SEY DEGILDIR:
#
#    · 100 m² girildi ama aslinda 90 m²ymis → FATURA DOGRU (10.000$),
#      yalnizca stok yanlis. Faturayi 9.000$'a dusurmek TEDARIKCIYE
#      OLAN BORCU yanlis gosterir.
#
#    · 100 m² ve 10.000$ dogruydu, sonra 10 m² iade/hurda/konsinye
#      oldu → stok gercekten 90 m², ama ORIJINAL FATURA degismemeli;
#      1.000$'lik KARSI KAYIT acilmali. Faturayi degistirmek belge
#      ile kaydi ayristirir.
#
#    Ikisini ayirt edebilecek tek kisi KULLANICIDIR.
#
#  ── ÜÇ SEÇENEK ──
#    mali_islem='fatura_duzelt'  Faturanin cari borcundan pay dusulur
#                                (eski davranis — artik ACIK SECIM)
#    mali_islem='karsi_kayit'    Orijinal fatura KORUNUR, pay kadar
#                                ters hareket acilir. Iade/hurda/
#                                konsinye icin DOGRU olan budur.
#    mali_islem='sadece_stok'    Finansal tarafa DOKUNULMAZ.
#                                Stok yanlis girilmisse budur.
#
#  ── NEDEN 409, 400 DEĞİL ──
#    base.html'deki `api()` yardimcisi 409'u OZEL sayiyor:
#      "409 (Conflict) cagiran fonksiyonun ozel ele almasi icin:
#       sessiz gec, yaniti tasi. Diger hatalarda kullaniciya bildir."
#    Ilk surumde 400 donuyordu ve kullanici karar penceresinden ONCE
#    kirmizi "istek basarisiz" uyarisi goruyordu — hata degil, SORU
#    oldugu halde. 409 bu kurala uyar; uyari cikmaz, dogrudan pencere
#    acilir.
#
#  ── SEÇİM YOKSA SİLME YOK ──
#    Faturaya bagli bir stok icin secim gelmezse 400 doner ve
#    secenekler listelenir. Varsayilan atamak — hangisi olursa
#    olsun — kullanici adina muhasebe karari vermek olurdu.
#
#    FATURAYA BAGLI OLMAYAN stokta secim istenmez; mali sonuc yok.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python yama_sf1_stok_fatura_ayrim.py            # rapor
#      venv/bin/python yama_sf1_stok_fatura_ayrim.py --uygula
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

ESKI = """        _pay = q3((getattr(stok, 'matrah', 0) or 0) + (getattr(stok, 'kdv_tutar', 0) or 0))
        _fno = (getattr(stok, 'fatura_no', '') or '').strip()
        _grup = CariHareket.query.filter_by(
            baglanti_tip='stok_fatura', baglanti_id=_fno).first() if _fno else None
        if _grup:"""

YENI = '''        _pay = q3((getattr(stok, 'matrah', 0) or 0) + (getattr(stok, 'kdv_tutar', 0) or 0))
        _fno = (getattr(stok, 'fatura_no', '') or '').strip()
        _grup = CariHareket.query.filter_by(
            baglanti_tip='stok_fatura', baglanti_id=_fno).first() if _fno else None

        # ══════════════════════════════════════════════════════
        #  MALİ KARAR KULLANICIYA AİT  (SF1)
        #
        #  Onceden fatura borcundan pay SESSIZCE dusuluyordu. Ama
        #  stok miktarindaki degisiklik ile fatura tutarindaki
        #  degisiklik AYNI SEY DEGILDIR:
        #
        #   · Stok yanlis girildi, fatura dogru  -> faturaya
        #     dokunulmamali (sadece_stok)
        #   · Iade/hurda/konsinye -> orijinal fatura korunmali,
        #     KARSI KAYIT acilmali (karsi_kayit)
        #   · Fatura da yanlissa  -> duzeltilmeli (fatura_duzelt)
        #
        #  Ikisini ayirt edebilecek tek kisi KULLANICIDIR; bu yuzden
        #  varsayilan ATANMAZ, secim istenir.
        # ══════════════════════════════════════════════════════
        MALI_SECENEKLER = {
            'fatura_duzelt': 'Fatura bedeli düzeltilsin (cari borçtan pay düşülür)',
            'karsi_kayit': 'Karşı kayıt oluşturulsun (orijinal fatura korunur)',
            'sadece_stok': 'Sadece stok düzeltilsin (fatura değişmez)',
        }
        # `request.json` KULLANILMAZ.
        # base.html'deki api() HER istege 'Content-Type: application/json'
        # koyuyor — govde bos olsa bile. O durumda `request.is_json`
        # True doner ama `request.json` govde bos oldugu icin Werkzeug
        # 400 (HTML) firlatir; kendi kodumuz hic calismaz ve kullanici
        # "istek basarisiz (400)" gorur.
        #
        # Olculdu: Content-Type YOK -> 409 (dogru), VAR -> 400 (HTML).
        # `silent=True` bos/bozuk govdede None doner, istisna atmaz.
        _govde = request.get_json(silent=True) or {}
        _mali = _govde.get('mali_islem') or request.args.get('mali_islem')
        _mali = (_mali or '').strip().lower() or None

        if _grup and not _mali:
            return jsonify({
                'ok': False, 'error': 'mali_islem_gerekli',
                'fatura_no': _fno,
                'pay': _pay, 'doviz': _grup.doviz or 'TRY',
                'secenekler': MALI_SECENEKLER,
                'mesaj': f'Bu stok {_fno} numaralı alış faturasına bağlı '
                         f'({_pay:,.2f} {_grup.doviz or "TRY"} pay). Faturaya ne '
                         f'yapılacağını seçin — stok düzeltmesi ile mali '
                         f'düzeltme aynı şey değildir.'}), 409

        if _grup and _mali not in MALI_SECENEKLER:
            return jsonify({
                'ok': False, 'error': 'gecersiz_mali_islem',
                'secenekler': MALI_SECENEKLER,
                'mesaj': f'Geçersiz mali işlem: {_mali}'}), 400

        # SADECE STOK: finansal tarafa hic dokunulmaz.
        if _grup and _mali == 'sadece_stok':
            _grup = None

        # KARSI KAYIT: orijinal fatura KORUNUR, ters hareket acilir.
        # Iade/hurda/konsinye icin dogru olan budur — belge ile kayit
        # ayrismaz, stok hareketi ayrica izlenebilir.
        elif _grup and _mali == 'karsi_kayit':
            _kk_t, _kk_k = _try_karsilik(_pay, _grup.doviz or 'TRY',
                                         tarih=date.today())
            db.session.add(CariHareket(
                id=_yeni_id('HR'), hareket_tarihi=date.today(),
                cari_id=_grup.cari_id, cari_unvan=_grup.cari_unvan,
                islem_tip='Alis Iade / Duzeltme',
                borc=_pay, alacak=0,
                doviz=_grup.doviz or 'TRY',
                borc_try=_kk_t, kur_uygulanan=_kk_k,
                vade_tarihi=date.today(),
                kaynak='stok_karsi_kayit',
                baglanti_tip='stok_fatura', baglanti_id=_fno,
                aciklama=f'{_fno} · stok çıkışı karşı kaydı '
                         f'({getattr(stok, "id", "")})',
                kullanici=session.get('kullanici')))
            # Orijinal harekete DOKUNULMAZ; yalnizca kalem sayaci
            # azalir ki son kalemde grup yanlislikla silinmesin.
            _grup.kalem_sayisi = max(0, (getattr(_grup, 'kalem_sayisi', 1) or 1) - 1)
            _grup = None

        if _grup:'''

IMZA = 'MALİ KARAR KULLANICIYA AİT  (SF1)'

print("═" * 70)
print(" SF1 · STOK SİLME MALİ KARARI AYIRIR")
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

print("  ✓ uygulanacak          üç seçenekli mali karar")
print("  ✓ uygulanacak          seçim yoksa 400 + seçenek listesi")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   venv/bin/python yama_sf1_stok_fatura_ayrim.py --uygula")
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
print(" ⚠ EKRAN GÜNCELLENMELİ: faturaya bağlı stok silinirken artık")
print("   400 dönüyor ve seçim isteniyor. templates/stok.html")
print("   güncellenmeden o stoklar silinemez.")
print("═" * 70)

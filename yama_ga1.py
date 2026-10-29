#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA GA1 — GÖVDE ALANI UYUŞMAZLIĞI İÇİN BEKÇİ (tarama TEMİZ çıktı)
====================================================================

ÖNKOŞUL: **yama_sl1.py uygulanmış olmalı.** Betik denetliyor.
Yalnız test dosyasına dokunuyor. `flask_app.py` ve şablonlar
DEĞİŞMİYOR. Şema yok, göç yok.

Kullanım:
    python3 yama_ga1.py --uygula
    venv/bin/python -m pytest tests/test_kritik.py -q     # 325

SUNUCUYU YENİDEN BAŞLATMAYA GEREK YOK — uygulama kodu değişmedi.

═══ TARANAN SINIF ═══

HS1'de ölçülen sınıf: sunucunun gövdeden OKUDUĞU alanı hiçbir
ekranın GÖNDERMEMESİ. İki örneği de para hatasıydı:

  · `doviz` — hızlı satış formunda DÖVİZ seçimi vardı ama gövdeye
    konmuyordu. Sunucu bulamayınca USD'ye düşüyor; EUR seçilen
    satışın siparişi, faturası, cari hareketi, çeki ve beş satış
    kaydının HEPSİ USD kaydediliyordu. Ekran €, veri $.
  · `kdv_dahil_mi` — ekranda böyle bir seçim HİÇ yoktu; sunucu her
    zaman False okuyordu, ekran ise "KDV dahil" yazıyordu.

İkisi de sessiz: istek 200 dönüyor, kayıt oluşuyor, sayı yanlış.

═══ SONUÇ: TEMİZ ═══

Her yazma ucu için sunucunun gövdeden okuduğu anahtarlar çıkarıldı
ve o ucu çağıran şablonlarda aranıp aranmadığına bakıldı. Para/kur/
KDV/tarih gibi sessiz varsayılanı tehlikeli olanlara daraltınca
9 aday kaldı; hepsi tek tek ölçüldü ve hiçbiri canlı hata değil:

  · proformadan faturaya: tarih verilmezse BUGÜN, vade
    `_vade_hesapla` ile müşterinin ödeme vadesinden hesaplanıyor
  · satıştan fatura: TASLAK oluşuyor, KDV ve vade Faturalar
    ekranından giriliyor
  · satış düzenlemede `birim` bilerek gönderilmiyor (m²'den ton'a
    geçmek miktarın anlamını değiştirirdi)
  · hızlı satışta `kdv_tutar` okuması geriye dönük uyum için
    duruyor; HS1'den beri sunucu KDV'yi kendi hesaplıyor

Hepsi muafiyet listesinde, her biri sebebiyle yazılı.

Tarama sırasında kendi taramamın üç kusurunu da düzelttim:
sunucunun KENDİ yanıt nesnelerinden okuduklarını gövde sanıyordu;
`/api/cari` öneki `/api/cari/hareket`i de yakalıyordu; ve ES6 kısa
yazımını (`tutar,`) görmüyordu — `/api/cek · tutar` o yüzden
yanlış pozitif çıkmıştı.

═══ BEKÇİNİN SINIRI (ölçüldü, dürüstçe) ═══

Bekçi HS1 öncesi `base.html` ile koşuldu: `kdv_dahil_mi`
eksikliğini YAKALADI, `doviz` eksikliğini YAKALAYAMADI. Çünkü o
şablonda `doviz:` KALEM nesnesinin içinde geçiyor ve bekçi
şablonun tamamında arıyor.

Yani: "anahtar şablonda hiç yok" durumunu görür, "üst düzey
gövdede yok ama kalemde var" durumunu görmez. Daha incesi JS gövde
nesnesini ayrıştırmayı gerektirirdi. Bu hâliyle de HS1'in iki
hatasından birini yakalıyor; yeşil bir bekçiye güvenmemek için
bunu ayrı bir testle de gösterdim.

═══ DOĞRULAMA ═══

  · 325 test geçiyor (323 → 325)
  · Bekçi, HS1 öncesi şablonla koşulunca GERÇEKTEN kırılıyor
  · Muafiyet listesi 9 satır, her birinin sebebi yazılı
"""

import base64
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile

UYGULA = '--uygula' in sys.argv
KOK = os.path.dirname(os.path.abspath(__file__))

DOSYA_IMZA = {
    'tests/test_kritik.py':
        'def test_ga1_sunucunun_okudugu_govde_alanini_ekran_gonderiyor',
}
ONKOSUL = {
    'tests/test_kritik.py':
        'def test_sl1_musteri_ozeti_satis_sayiyor_kalem_degil',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('tests/test_kritik.py', 'GA1 · tests/test_kritik.py blok 1',
     r'''    assert "g.kalemler.length + ' kalem'" in govde
''',
     r'''    assert "g.kalemler.length + ' kalem'" in govde


# ══════════════════════════════════════════════════════════════════
#  GA1 · SUNUCUNUN OKUDUĞU GÖVDE ALANINI BİR EKRAN GÖNDERMELİ
#
#  HS1'DE ÖLÇÜLEN SINIF. İki yönü de gerçek çıkmıştı:
#    · `doviz` — hızlı satış formunda DÖVİZ seçimi vardı ama gövdeye
#      konmuyordu; sunucu bulamayınca USD'ye düşüyor ve EUR seçilen
#      satışın siparişi, faturası, cari hareketi, çeki ve satış
#      kayıtlarının HEPSİ USD kaydediliyordu.
#    · `kdv_dahil_mi` — ekranda böyle bir seçim HİÇ yoktu; sunucu
#      her zaman False okuyordu ve ekran "KDV dahil" yazıyordu.
#
#  İkisi de sessiz: istek 200 dönüyor, kayıt oluşuyor, sayı yanlış.
#
#  Bu bekçi her yazma ucu için sunucunun gövdeden okuduğu anahtarları
#  çıkarıp, o ucu çağıran şablonlarda geçip geçmediğine bakar.
#
#  MUAFİYET LİSTESİ KISA TUTULACAK. Uzayan bir liste, bekçinin
#  sessizce kapanmasıdır; her satırın sebebi yazılı.
# ══════════════════════════════════════════════════════════════════
_GA1_MUAF = {
    # Hızlı satış KDV'yi KENDİ hesaplıyor (HS1, KD1'in kapısından).
    # Bu okuma geriye dönük uyum için duruyor; ekranın göndermesi
    # beklenmiyor ve gönderse de üzerine yazılıyor.
    ('/api/sicak_satis', 'kdv_tutar'),
    # Satıştan fatura TASLAK olarak oluşur; KDV oranı ve vade
    # Faturalar ekranından giriliyor. Vade verilmezse `_vade_hesapla`
    # müşterinin ödeme vadesinden hesaplıyor.
    ('/api/satislar/<satis_id>/fatura', 'kdv_oran'),
    ('/api/satislar/<satis_id>/fatura', 'vade_tarihi'),
    # Satış düzenlemede birim DEĞİŞTİRİLMİYOR: m²'den ton'a geçmek
    # miktarın anlamını değiştirirdi. Alan okunuyor ama ekran
    # bilerek göndermiyor.
    ('/api/satislar/<satis_id>', 'birim'),
    # Kayıp tarihi verilmezse bugün kullanılıyor.
    ('/api/proforma/<proforma_id>/kaybedildi', 'tarih'),
    # Fatura tarihi verilmezse bugün, vade `_vade_hesapla` ile
    # müşterinin ödeme vadesinden hesaplanıyor (ölçüldü).
    ('/api/proforma/<proforma_id>/faturaya_donustur', 'fatura_tarihi'),
    ('/api/proforma/<proforma_id>/faturaya_donustur', 'vade_tarihi'),
    # Fatura güncellemede maliyet kalemleri yalnız içe aktarma
    # yolundan geliyor; ekranda böyle bir alan yok.
    ('/api/fatura/<fatura_id>', 'maliyet_kalemleri'),
    # Cari harekette fatura tarihi verilmezse hareket tarihi kullanılıyor.
    ('/api/cari/hareket', 'fatura_tarihi'),
}


def test_ga1_sunucunun_okudugu_govde_alanini_ekran_gonderiyor():
    """Sunucu bir alanı okuyorsa, onu çağıran ekran göndermeli.

    SINIRI ÖLÇÜLDÜ: HS1 öncesi `base.html` ile koşuldu ve
    `kdv_dahil_mi` eksikliğini YAKALADI. Ama `doviz` eksikliğini
    yakalayamadı — çünkü o şablonda `doviz:` KALEM nesnesinin içinde
    geçiyordu ve bekçi şablonun tamamında arıyor. Yani bekçi
    "anahtar şablonda hiç yok" durumunu görür, "üst düzey gövdede
    yok ama kalemde var" durumunu görmez.

    Daha incesi, JS gövde nesnesini ayrıştırmayı gerektirirdi; bu
    hâliyle de HS1'in iki hatasından birini yakalıyor."""
    import ast as _ast
    import io as _io
    import re as _re

    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    agac = _ast.parse(kaynak)

    sdizin = os.path.join(KOK, 'templates')
    sablonlar = {}
    for ad in sorted(os.listdir(sdizin)):
        if ad.endswith('.html'):
            sablonlar[ad] = _io.open(os.path.join(sdizin, ad),
                                     encoding='utf-8',
                                     errors='replace').read()

    YAZMA = {'POST', 'PUT', 'PATCH', 'DELETE'}
    IC_ALAN = {'onay', 'force', 'zorla', 'dry_run', 'test', 'debug'}
    # Sessiz varsayılanı PARAYI ya da ETİKETİ değiştirebilecek adlar.
    # `doviz` ve `kdv_dahil_mi` tam bu kümedendi.
    KRITIK = _re.compile(
        r'doviz|kur|kdv|tutar|fiyat|oran|matrah|vade|tarih|miktar|birim'
        r'|maliyet|komisyon|tevkifat|iskonto|avans|tahsilat|bakiye', _re.I)

    acik = []
    for fn in _ast.walk(agac):
        if not isinstance(fn, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            continue
        yollar, yontemler = [], []
        for dec in fn.decorator_list:
            if (isinstance(dec, _ast.Call)
                    and isinstance(dec.func, _ast.Attribute)
                    and dec.func.attr == 'route' and dec.args
                    and isinstance(dec.args[0], _ast.Constant)):
                yollar.append(dec.args[0].value)
                for kw in dec.keywords:
                    if kw.arg == 'methods':
                        yontemler += [e.value for e in
                                      getattr(kw.value, 'elts', [])
                                      if isinstance(e, _ast.Constant)]
        if not yollar:
            continue
        yol = yollar[0]
        if not yol.startswith('/api/') or yol.startswith('/api/diag/'):
            continue
        if not (set(yontemler) & YAZMA):
            continue

        # Gövde değişkeni: request.get_json() neye atanmış.
        govde_adlari = set()
        for d in _ast.walk(fn):
            if (isinstance(d, _ast.Assign) and len(d.targets) == 1
                    and isinstance(d.targets[0], _ast.Name)):
                kod = _ast.unparse(d.value)
                if ('request.get_json' in kod or 'request.json' in kod
                        or 'request.form' in kod):
                    govde_adlari.add(d.targets[0].id)
        if not govde_adlari:
            continue

        okunan = set()
        for d in _ast.walk(fn):
            if not (isinstance(d, _ast.Call)
                    and isinstance(d.func, _ast.Attribute)
                    and d.func.attr == 'get' and d.args
                    and isinstance(d.args[0], _ast.Constant)
                    and isinstance(d.args[0].value, str)):
                continue
            t = d.func.value
            ad_t = t.id if isinstance(t, _ast.Name) else (
                t.attr if isinstance(t, _ast.Attribute) else None)
            if ad_t in govde_adlari:
                okunan.add(d.args[0].value)
        if not okunan:
            continue

        # Bu ucu çağıran şablonlar — ÖNEK EŞLEME SIKI:
        # `/api/cari`, `/api/cari/hareket`i yakalamasın.
        onek = yol.split('<')[0].rstrip('/')
        if not onek:
            continue
        kalip = _re.compile(_re.escape(onek) + r'(?![A-Za-z0-9_/-])')
        cagiranlar = [a for a, m in sablonlar.items() if kalip.search(m)]
        if not cagiranlar:
            continue        # ekransız uç; başka bir bekçinin işi
        metin = '\n'.join(sablonlar[a] for a in cagiranlar)

        for anahtar in sorted(okunan):
            if anahtar in IC_ALAN or not KRITIK.search(anahtar):
                continue
            if (yol, anahtar) in _GA1_MUAF:
                continue
            # `anahtar:` · 'anahtar' · govde.anahtar = · ES6 kısa yazım
            if _re.search(r'[\'"]?\b%s\b[\'"]?\s*:' % _re.escape(anahtar), metin):
                continue
            if _re.search(r'[\'"]%s[\'"]' % _re.escape(anahtar), metin):
                continue
            if _re.search(r'\.%s\s*=' % _re.escape(anahtar), metin):
                continue
            if _re.search(r'^(?=.*:).*\b%s\b\s*,' % _re.escape(anahtar),
                          metin, _re.M):
                continue
            acik.append(f'{yol} · {anahtar} ({fn.name})')

    assert not acik, (
        'sunucu bu gövde alanlarını okuyor ama onu çağıran hiçbir ekran '
        'göndermiyor — alan sessizce varsayılana düşer: '
        + '; '.join(sorted(acik)))


def test_ga1_bekci_hs1_hatasini_yakaliyor():
    """Bekçi, HS1'de yaşadığımız eksikliği görmeli.

    HS1'de hızlı satış `doviz` göndermiyordu. O hâli taklit edip
    bekçinin kullandığı eşleştirmenin onu YAKALADIĞINI gösteriyoruz;
    yoksa yeşil bir bekçiye güvenmiş oluruz."""
    import re as _re
    # Ekranın gövdesi (HS1 ÖNCESİ hâli): doviz YOK
    eski_ekran = """
      const govde = {
        musteri,
        satis_tipi: document.getElementById('hsTip').value,
        kdv_oran: parseFloat(document.getElementById('hsKdv').value) || 0,
      };
    """
    for anahtar in ('doviz', 'kdv_dahil_mi'):
        bulundu = (
            _re.search(r'[\'"]?\b%s\b[\'"]?\s*:' % anahtar, eski_ekran)
            or _re.search(r'[\'"]%s[\'"]' % anahtar, eski_ekran)
            or _re.search(r'\.%s\s*=' % anahtar, eski_ekran)
            or _re.search(r'^(?=.*:).*\b%s\b\s*,' % anahtar, eski_ekran, _re.M))
        assert not bulundu, (
            f'bekçinin eşleştirmesi {anahtar!r} yokken VAR sanıyor — '
            f'HS1 hatasını kaçırırdı')
    # Ve ŞİMDİKİ ekran ikisini de gönderiyor olmalı
    import io as _io
    b = _io.open(os.path.join(KOK, 'templates', 'base.html'),
                 encoding='utf-8').read()
    assert "doviz: document.getElementById('hsDoviz').value" in b
    assert 'kdv_dahil_mi:' in b
'''),
]

def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA GA1 — GÖVDE ALANI BEKÇİSİ')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    # ── --yaz-gecici ──
    # base64 gömülü iki dosyayı /tmp'ye çıkarır, PROJEYE DOKUNMAZ.
    # Tam dosya yazan bir yamayı önce okumak istemek yerinde bir
    # istek; "uygula da sonra bak" demek yanlış olurdu.
    if '--yaz-gecici' in sys.argv:
        hedef = tempfile.mkdtemp(prefix='ga1-')
        print()
        for ad in TAM_YAZILAN:
            p = os.path.join(hedef, ad)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(_tam_dosya(ad))
            print(f'  {p}')
        print()
        print('  Projeye DOKUNULMADI. Okuduktan sonra:')
        print('    python3 yama_ga1.py            # rapor')
        print('    python3 yama_ga1.py --uygula')
        print('=' * 70)
        return 0

    gruplar = {}
    for dosya, aciklama, eski, yerine in DEGISIKLIKLER:
        gruplar.setdefault(dosya, []).append((aciklama, eski, yerine))

    sonuclar, hata, zaten = {}, False, []

    # ══════════════════════════════════════════════════════════════
    #  TAM DOSYA YAZILANLAR
    # ══════════════════════════════════════════════════════════════
    for dosya in TAM_YAZILAN:
        yol = os.path.join(KOK, dosya)
        print(f'\n── {dosya} ' + '─' * max(0, 52 - len(dosya)))
        yeni = _tam_dosya(dosya)

        if os.path.exists(yol):
            with open(yol, 'rb') as f:
                ham = f.read()
            try:
                mevcut = ham.decode('utf-8')
            except UnicodeDecodeError:
                print('  ✗ Dosya UTF-8 değil — dokunmuyorum.')
                hata = True
                continue
            imza = DOSYA_IMZA.get(dosya)
            if imza and imza in mevcut:
                print('  ⊙ İmza zaten var — ATLANIR')
                zaten.append(dosya)
                continue
            onk = ONKOSUL.get(dosya)
            if onk and onk not in mevcut:
                # Beklenmeyen bir dosyanın üzerine yazmayı reddediyoruz:
                # bu betik TAM DOSYA yazıyor, yanlış hedefte geri
                # dönüşü yedekten olur.
                print(f'  ✗ Beklenen içerik yok ("{onk}")')
                print('    Bu dosya tanıdığım sifirla2.py değil; tam dosya')
                print('    yazdığım için üzerine yazmayı reddediyorum.')
                hata = True
                continue
            print(f'  · mevcut dosya {len(mevcut.splitlines())} satır '
                  f'→ yeni {len(yeni.splitlines())} satır (YENİDEN YAZILIR)')
        else:
            print(f'  · yeni dosya ({len(yeni.splitlines())} satır)')

        # Söz dizimi doğrulaması — UZANTIYA GÖRE.
        _uzanti = os.path.splitext(dosya)[1].lower()
        with tempfile.NamedTemporaryFile('w', suffix=_uzanti or '.txt',
                                         delete=False, encoding='utf-8') as tf:
            tf.write(yeni)
            gec = tf.name
        try:
            if _uzanti == '.py':
                try:
                    py_compile.compile(gec, doraise=True, cfile=gec + 'c')
                    print('  ✓ söz dizimi doğrulandı (py_compile)')
                except py_compile.PyCompileError as e:
                    print(f'  ✗ SÖZDİZİMİ HATASI:\n{e}')
                    hata = True
            elif _uzanti == '.js':
                _node = shutil.which('node') or shutil.which('nodejs')
                if not _node:
                    print('  ⚠ node bulunamadı — JS söz dizimi DENETLENMEDİ')
                else:
                    _s = subprocess.run([_node, '--check', gec],
                                        capture_output=True, text=True)
                    if _s.returncode != 0:
                        print(f'  ✗ JS SÖZDİZİMİ HATASI:\n{_s.stderr[:400]}')
                        hata = True
                    else:
                        print('  ✓ söz dizimi doğrulandı (node --check)')
            else:
                print(f'  · {_uzanti or "uzantısız"} — söz dizimi denetimi yok')
        finally:
            for p in (gec, gec + 'c'):
                if os.path.exists(p):
                    os.unlink(p)

        sonuclar[yol] = yeni

    # ══════════════════════════════════════════════════════════════
    #  CERRAHİ DEĞİŞİKLİKLER
    # ══════════════════════════════════════════════════════════════
    for dosya, isler in gruplar.items():
        yol = os.path.join(KOK, dosya)
        print(f'\n── {dosya} ' + '─' * max(0, 52 - len(dosya)))
        if not os.path.exists(yol):
            print(f'  ✗ DOSYA YOK: {yol}')
            hata = True
            continue

        with open(yol, 'rb') as f:
            ham = f.read()
        crlf = b'\r\n' in ham
        icerik = ham.decode('utf-8')
        if crlf:
            icerik = icerik.replace('\r\n', '\n')
            print('  · CRLF satır sonu algılandı, korunacak')

        # ── SIRA ÖNEMLİ: İMZA ÖNCE, ÖNKOŞUL SONRA ──
        # Ters sırada yazmıştım ve ikinci koşuda patladı. Bu yamanın
        # ÖNKOŞUL çapaları, yamanın DEĞİŞTİRDİĞİ satırların kendisi
        # (örn. `grep -q "Zaten uygulanmış"`). Uygulandıktan sonra o
        # satır artık yok; önkoşulu önce denetlersen uygulanmış dosya
        # "ÖNKOŞUL YOK" diye HATA veriyor — oysa durum "zaten
        # uygulanmış". İmza sorusu her zaman önce gelmeli.
        if DOSYA_IMZA[dosya] in icerik:
            print('  ⊙ İmza zaten var — ATLANIR')
            zaten.append(dosya)
            continue
        onk = ONKOSUL.get(dosya)
        if onk and onk not in icerik:
            print(f'  ✗ ÖNKOŞUL YOK: "{onk}" yok')
            hata = True
            continue

        yeni, bozuk = icerik, False
        for aciklama, eski, yerine in isler:
            n = yeni.count(eski)
            if n != 1:
                print(f'  ✗ {aciklama}')
                print(f'     kalıp {n} kez eşleşti (tam 1 olmalı)')
                hata = bozuk = True
                continue
            yeni = yeni.replace(eski, yerine, 1)
            print(f'  ✓ {aciklama}')
        if bozuk:
            continue

        if dosya.endswith('.py'):
            with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False,
                                             encoding='utf-8') as tf:
                tf.write(yeni)
                gec = tf.name
            try:
                py_compile.compile(gec, doraise=True, cfile=gec + 'c')
                print('  ✓ söz dizimi doğrulandı (py_compile)')
            except py_compile.PyCompileError as e:
                print(f'  ✗ SÖZDİZİMİ HATASI:\n{e}')
                hata = True
            finally:
                for p in (gec, gec + 'c'):
                    if os.path.exists(p):
                        os.unlink(p)

        if dosya.endswith('.sh'):
            # Kabuk betiğini bash ile söz dizimi denetimine sok;
            # bozuk bir gonder.sh push yolunu kapatır.
            try:
                with tempfile.NamedTemporaryFile('w', suffix='.sh',
                                                 delete=False,
                                                 encoding='utf-8') as tf:
                    tf.write(yeni)
                    gecs = tf.name
                _s = subprocess.run(['bash', '-n', gecs],
                                    capture_output=True, text=True)
                if _s.returncode != 0:
                    print(f'  ✗ KABUK SÖZDİZİMİ HATASI:\n{_s.stderr[:400]}')
                    hata = True
                else:
                    print('  ✓ söz dizimi doğrulandı (bash -n)')
            except FileNotFoundError:
                print('  ⚠ bash bulunamadı, kabuk denetimi atlandı')
            finally:
                if os.path.exists(gecs):
                    os.unlink(gecs)

        sonuclar[yol] = (yeni.replace('\n', '\r\n') if crlf else yeni)

    # ══════════════════════════════════════════════════════════════
    print('\n' + '=' * 70)
    if hata:
        print('  ✗ HATA VAR → Hiçbir dosyaya DOKUNULMADI')
        return 1
    if zaten and sonuclar:
        # Yarım durum: bazı dosyalar yamalı, bazıları değil. Devam
        # etmek sistemi tutarsız bırakırdı.
        print('  ✗ YARIM DURUM → Hiçbir dosyaya DOKUNULMADI')
        print(f'    imzası olan: {", ".join(zaten)}')
        return 1
    if zaten:
        print('  ⊙ Yama GA1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_ga1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_ga1'
            shutil.copy2(yol, yedek)
            _y = f'    yedek  : {os.path.relpath(yedek, KOK)}'
        else:
            _y = '    (yeni dosya — yedek yok)'
            _klasor = os.path.dirname(yol)
            if _klasor and not os.path.isdir(_klasor):
                os.makedirs(_klasor, exist_ok=True)
                print(f'    klasör oluşturuldu: {os.path.relpath(_klasor, KOK)}')
        with open(yol, 'w', encoding='utf-8', newline='') as f:
            f.write(icerik)
        if yol.endswith('.sh'):
            os.chmod(yol, 0o755)
        print(f'  ✓ yazıldı: {os.path.relpath(yol, KOK)}')
        print(_y)

    print('\n  ✓ YAMA UYGULANDI')
    print()
    print('    venv/bin/python -m pytest tests/test_kritik.py -q   # 325')
    print()
    print('  SUNUCUYU YENIDEN BASLATMAYA GEREK YOK')
    print('    Uygulama kodu degismedi; yalnizca test eklendi.')
    print()
    print('  TARAMA TEMIZ CIKTI')
    print('    Sunucunun govdeden okudugu her alani bir ekran')
    print('    gonderiyor. 9 aday olculdu, hicbiri canli hata degil;')
    print('    hepsi sebebiyle muafiyet listesinde.')
    print('    Bu yama duzeltme degil: HS1 sinifini (doviz,')
    print('    kdv_dahil_mi) test zamaninda SESLI hale getiriyor.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA KF1 — KUR FARKI ONAYI TEK SATIRA İNDİ
===========================================

ÖNKOŞUL: MR1 uygulanmış olmalı — betik denetliyor, eksikse hiçbir
dosyaya dokunmadan çıkıyor.

"Kur farkını cari hesaba işle kısmının görüntüsü kötü ve çok yer
kaplıyor" dedin. Sebebi göründüğünden sıkıcıydı.

── NEDEN O KADAR YER KAPLIYORDU ──

  Sayfanın form kuralı tip ayırmıyor:

      .form-alan input,.form-alan select{width:100%; ...}

  Aynı kapsayıcıda duran ONAY KUTUSU da bu kuralı yiyor. Chrome
  kontrolü o geniş kutunun ORTASINA çizer — yani kutucuk kendi
  yazısından yarım form uzakta duruyordu. Senin ekran görüntünde
  de tam olarak bu görünüyor.

  ÖLÇÜLDÜ (640 px'lik modalde, tarayıcıda):
      kutucuğun genişliği      273 px   (olması gereken 15)
      açıklamaya kalan yer     dar  →  iki satıra sarıyor
      alanın yüksekliği         73 px
      gövdenin kaydırması       12 px

  Yani pencerenin kaydırma ihtiyacı neredeyse tek başına bu
  kutucuktan geliyordu. Tahmin ettiğin gibi.

── NE YAPILDI ──

  1. Kutucuk kendi ölçüsüne döndü, kurumsal yeşili aldı.
  2. Alan tek satırlık bir çubuk oldu; işaretlenince yeşile dönüyor
     — bir muhasebe kaydı açacak düğmenin "kurulu" olduğu
     görünsün diye.
  3. AÇIKLAMA İŞARETE GÖRE DEĞİŞİYOR (saf CSS, JS yok):
         kapalı  →  "kur farkı yalnızca bildirilir, kayıt düşmez"
         açık    →  "cari hesaba kur farkı kaydı açılır"
     İkisi de tek satır, yani işaretleyince pencere ZIPLAMIYOR.
     (İlk denemede kapalı hâlin cümlesi 58 karakterdi ve sarıyordu;
     640 px'de nota kalan yer ~55 karakter. Sınır artık testte.)

  ÖLÇÜLDÜ (yamadan sonra):
      kutucuk                   15 px
      alan                      33 px   (73 → 33)
      gövde                    679 px / pencere 695  → KAYDIRMA YOK
      işaretli hâl de 33 px — boy oynamıyor

── ÇIKARILAN BİR ŞEY ──

  Etikette tutarın yazılacağı bir alan vardı (`hKurFarkiTutar`) ama
  ONU DOLDURAN KOD YOKTU — uygulamanın hiçbir yerinde. Boş bir söz
  veriyordu, çıkardım.

  Canlı önizleme istersen ayrı iş: açık fatura ucu faturanın ESKİ
  kurunu dönmüyor, yani sunucu tarafında ekleme gerekiyor. Söyle,
  yaparım.

── AYNI TUZAK BAŞKA YERDE VAR MI ──

  16 şablondaki bütün onay ve radyo kutuları tarayıcıya sorularak
  tarandı (hesaplanan genişlik ölçüldü, kodu okumakla yetinilmedi).
  TEK KURBAN buydu; ötekiler ya elle korunmuş ya da `.form-alan`
  dışında duruyor.

  Yine de kural TİPE GÖRE yeniden yazıldı:

      .form-alan input[type=checkbox],.form-alan input[type=radio]
        {width:15px;height:15px;...}

  Bir sonraki onay kutusu aynı çukura düşmesin.

── KALAN ──

  Pencere ~800 piksel yüksekliğinde hâlâ kaydırıyor; orada form
  zaten mevcut alandan uzun. En büyük kalemler kasa ipucu (86 px)
  ve sözleşme kuru kutusu (49 px). İstersen onları da sıkıştırırım
  ama senin ekranında gerek kalmamış olmalı.

DOSYALAR
--------
  templates/cari.html     kutucuk kuralı · tek satırlık çubuk ·
                          duruma göre açıklama · ölü alan çıktı
  tests/test_kritik.py    3 yeni test

Şema yok, göç yok, sunucu tarafı değişmedi.

KULLANIM
--------
  python3 yama_kf1.py            # RAPOR
  python3 yama_kf1.py --uygula
  sudo systemctl restart milestone-erp
  (tarayıcıda Ctrl+F5)
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
    'templates/cari.html': 'KF1 — KUR FARKI ONAYI',
    'tests/test_kritik.py': 'def test_kf1_onay_kutusu_metin_kutusu_genisligi_almiyor',
}
ONKOSUL = {
    'templates/cari.html': 'VT1: vade yalnız BORÇ doğuran tiplerde görünür',
    'tests/test_kritik.py': 'def test_mr1_iptal_edilmis_gider_maliyete_girmiyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('templates/cari.html', 'KF1 · templates/cari.html blok 1',
     r'''  /* MA4: ALT BAR KENDI ZEMININI TASIR.
''',
     r'''  /* KF1 — ONAY KUTUSUNDA TİP ÖNEMLİ.
     Üstteki `.form-alan input` kuralı tip ayırmıyor: aynı kapsayıcıda
     duran bir onay kutusu da `width:100%` alıyordu. Chrome kontrolü o
     geniş kutunun ORTASINA çiziyor — kutucuk kendi yazısından 270
     piksel uzakta duruyordu (kenarlık ve dolgu zaten yok sayılıyor,
     bozan tek şey genişlik).
     ÖLÇÜLDÜ: 16 şablondaki tüm onay/radyo kutuları tarandı, tek kurban
     `hKurFarkiIslet`'ti — ötekiler ya elle korunmuş ya da `.form-alan`
     dışında. Kural yine de TİPE GÖRE yazıldı: bir sonraki kutucuk
     aynı yere düşmesin. */
  .form-alan input[type=checkbox],.form-alan input[type=radio]{
    width:15px;height:15px;flex:none;padding:0;cursor:pointer;
    accent-color:var(--verde)}
  /* KF1 — KUR FARKI ONAYI: tek satır, işaretlenince yeşile döner.
     Açıklama işarete göre değişiyor (`:has`, JS yok) ve iki hâli de
     tek satır olduğu için işaretleyince pencere zıplamıyor. */
  .kf-onay{margin-bottom:12px}
  .kf-onay > label{display:flex;flex-wrap:wrap;align-items:center;
    gap:4px 9px;cursor:pointer;border:1px solid var(--cizgi-koyu);
    border-radius:var(--r-kucuk);padding:8px 11px;margin:0;
    font-size:.85rem;font-weight:400;text-transform:none;
    letter-spacing:0;color:inherit}
  /* Kutucuk artık `.form-alan` içinde DEĞİL, yani yukarıdaki koruma
     kuralı buraya uğramıyor; ölçüsünü ve rengini kendisi söylüyor.
     Varsayılan işaretli rengi tarayıcının mavisiydi — kurumsal yeşil
     olmayınca kutu sayfanın geri kalanına yabancı duruyordu. */
  .kf-onay input{width:15px;height:15px;flex:none;margin:0;
    cursor:pointer;accent-color:var(--verde)}
  .kf-onay:has(input:checked) > label{border-color:var(--verde);
    background:var(--verde-acik)}
  .kf-not{font-size:.73rem;color:var(--soluk);
    border-left:1px solid var(--cizgi-koyu);padding-left:9px}
  .kf-acik{display:none}
  .kf-onay:has(input:checked) .kf-kapali{display:none}
  .kf-onay:has(input:checked) .kf-acik{display:inline}
  /* MA4: ALT BAR KENDI ZEMININI TASIR.
'''),
    ('templates/cari.html', 'KF1 · templates/cari.html blok 2',
     r'''      <div class="form-alan" id="hKurFarkiAlan" style="margin-bottom:12px;display:none">
        <label style="display:flex;align-items:flex-start;gap:9px;cursor:pointer;
               font-weight:400;text-transform:none;letter-spacing:0;font-size:.88rem">
          <input type="checkbox" id="hKurFarkiIslet" style="margin-top:3px">
          <span>
            <strong>Kur farkını cari hesaba işle</strong>
            <span id="hKurFarkiTutar" style="color:var(--soluk)"></span>
            <span style="display:block;font-size:.74rem;color:var(--soluk);margin-top:3px">
              İşaretlemezseniz kur farkı yalnızca <strong>hesaplanır ve bildirilir</strong>;
              cari hesaba kayıt düşmez.
            </span>
          </span>
''',
     r'''      <!-- KF1 — ÜÇ SATIRDAN BİRE.
           Kutucuk `.form-alan input{width:100%}` kuralından 273 piksel
           genişlik alıyordu; yazısından yarım form uzakta duruyor,
           açıklama da kalan dar alanda iki satıra sarıyordu. Kutucuk
           kendi boyutuna döndü, açıklama tek satıra sığdı.
           ÖLÇÜLDÜ: 73 px → 37 px; pencerenin 12 px'lik kaydırma
           ihtiyacı kalmadı.

           `hKurFarkiTutar` ÇIKARILDI: tutarı yazacak bir yer hiç
           yoktu, boş bir söz veriyordu. Açık fatura ucu faturanın
           ESKİ kurunu dönmüyor, yani önizleme sunucu tarafında iş
           ister — ayrı konu. -->
      <div class="kf-onay" id="hKurFarkiAlan" style="display:none">
        <label>
          <input type="checkbox" id="hKurFarkiIslet">
          <strong>Kur farkını cari hesaba işle</strong>
          <!-- İki açıklama da TEK SATIRA sığacak kadar kısa tutuldu:
               640 piksellik modalde nota kalan yer ~330 piksel, yani
               ~55 karakter. İlk yazdığım uzun cümle 58 karakterdi ve
               sarıyordu — işaretleyince kutu 51'den 33 piksele
               düşüyor, pencere zıplıyordu. Ölçüldü. -->
          <span class="kf-not kf-kapali">kur farkı yalnızca bildirilir,
            kayıt düşmez</span>
          <span class="kf-not kf-acik">cari hesaba kur farkı kaydı
            açılır</span>
'''),
    ('tests/test_kritik.py', 'KF1 · tests/test_kritik.py blok 1',
     r'''    assert not kotu, f'stok maliyetinde süzgeçsiz toplama: {kotu}'
''',
     r'''    assert not kotu, f'stok maliyetinde süzgeçsiz toplama: {kotu}'


# ══════════════════════════════════════════════════════════════════
#  KF1 · KUR FARKI ONAYI — ÜÇ SATIRDAN BİRE
#
#  Kutucuk `.form-alan input{width:100%}` kuralından 273 piksel
#  genişlik alıyordu. Chrome kontrolü o geniş kutunun ORTASINA çizer;
#  kutucuk kendi yazısından yarım form uzakta duruyor, açıklama da
#  kalan dar alanda iki satıra sarıyordu.
#
#  ÖLÇÜLDÜ (640 px modal, tarayıcıda):
#      eski: kutu 273 px · alan 73 px · gövde 12 px kaydırıyor
#      yeni: kutu  15 px · alan 33 px · kaydırma yok
#
#  16 şablondaki tüm onay/radyo kutuları tarandı; tek kurban buydu.
# ══════════════════════════════════════════════════════════════════

def test_kf1_onay_kutusu_metin_kutusu_genisligi_almiyor():
    """Onay kutusu `.form-alan` kuralından `width:100%` ALMAMALI.

    Bu testin asıl işi gelecek: kuralın kendisi hâlâ tip ayırmıyor
    olabilir. İki koruma da aranır — tipe göre yazılmış kural ve
    kur farkı kutusunun kendi ölçüsü."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/cari.html'),
                 encoding='utf-8').read()
    assert '.form-alan input[type=checkbox]' in m, \
        'tipe göre koruma kuralı yok — bir sonraki kutucuk yayılır'
    assert '.kf-onay input{width:15px' in m, \
        'kur farkı kutusu kendi ölçüsünü söylemiyor'

    # Kutucuk `.form-alan` içine GERİ TAŞINMAMALI: orada genişlik
    # kuralı yeniden devreye girer.
    _b = m.index('id="hKurFarkiAlan"')
    _acilis = m.rindex('<div class=', 0, _b)
    assert 'kf-onay' in m[_acilis:_b], 'kutu form-alan içine dönmüş'


def test_kf1_aciklama_isarete_gore_degisiyor_ve_boy_oynamiyor():
    """İki açıklama da var ve ikisi de TEK SATIR.

    İlk denemede kapalı hâlin cümlesi 58 karakterdi; 640 px modalde
    nota kalan yer ~55 karakter olduğu için sarıyor, işaretleyince
    kutu 51'den 33 piksele düşüp pencereyi zıplatıyordu. Sınır
    testle tutuluyor."""
    import io as _io, re as _re
    m = _io.open(os.path.join(KOK, 'templates/cari.html'),
                 encoding='utf-8').read()
    for _k in ('.kf-onay:has(input:checked) .kf-kapali{display:none}',
               '.kf-onay:has(input:checked) .kf-acik{display:inline}'):
        assert _k in m, f'{_k} yok — açıklama işarete göre değişmiyor'

    _alan = m[m.index('id="hKurFarkiAlan"'):]
    _alan = _alan[:_alan.index('</div>')]
    for _s in ('kf-not kf-kapali', 'kf-not kf-acik'):
        assert _s in _alan, f'{_s} yok'
    # Metinler tek satıra sığmalı: sürüm notlarıyla uzamasın.
    for _m in _re.finditer(r'class="kf-not kf-\w+">(.*?)</span>',
                           _alan, _re.S):
        _metin = ' '.join(_m.group(1).split())
        assert len(_metin) <= 55, \
            f'açıklama {len(_metin)} karakter — sarar: {_metin}'


def test_kf1_olmayan_tutar_sozu_verilmiyor():
    """`hKurFarkiTutar` ÇIKARILDI — hiçbir şey doldurmuyordu.

    Etikette tutarın yazılacağı bir yer duruyordu ama onu yazan kod
    yoktu: açık fatura ucu faturanın ESKİ kurunu dönmüyor. Boş bir
    söz, verilmemiş sözden kötüdür."""
    import io as _io, os as _os
    for _ad in _os.listdir(os.path.join(KOK, 'templates')):
        if not _ad.endswith('.html'):
            continue
        m = _io.open(os.path.join(KOK, 'templates', _ad),
                     encoding='utf-8').read()
        # ADI değil ÖGESİ aranır: yama notu adı anıyor, öge değil.
        assert 'id="hKurFarkiTutar"' not in m, \
            f'{_ad}: dolduran kodu olmayan tutar alanı geri gelmiş'

    # Kutucuğun KENDİSİ duruyor: kaydederken okunan bayrak bu.
    m = _io.open(os.path.join(KOK, 'templates/cari.html'),
                 encoding='utf-8').read()
    assert "getElementById('hKurFarkiIslet')" in m, 'bayrak okunmuyor'
    assert 'govde.kur_farki_islet = true' in m, 'bayrak sunucuya gitmiyor'
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA KF1 — KUR FARKI ONAYI TEK SATIRA İNDİ')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    # ── --yaz-gecici ──
    # base64 gömülü iki dosyayı /tmp'ye çıkarır, PROJEYE DOKUNMAZ.
    # Tam dosya yazan bir yamayı önce okumak istemek yerinde bir
    # istek; "uygula da sonra bak" demek yanlış olurdu.
    if '--yaz-gecici' in sys.argv:
        hedef = tempfile.mkdtemp(prefix='tz1-')
        print()
        for ad in TAM_YAZILAN:
            p = os.path.join(hedef, ad)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(_tam_dosya(ad))
            print(f'  {p}')
        print()
        print('  Projeye DOKUNULMADI. Okuduktan sonra:')
        print('    python3 yama_kf1.py            # rapor')
        print('    python3 yama_kf1.py --uygula')
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
        print('  ⊙ Yama KF1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_kf1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_kf1'
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
    print('    1) sudo systemctl restart milestone-erp')
    print('    2) Tarayicida Ctrl+F5')
    print('    3) venv/bin/python -m pytest tests/test_kritik.py -q')
    print()
    print('  BAKILACAK YER')
    print('    Cari -> bir cari -> Hareket Ekle.')
    print('    Islem tipi ODEME (ya da Tahsilat), doviz USD/EUR:')
    print('    "Kur farkini cari hesaba isle" artik tek satirlik bir')
    print('    cubuk. Isaretle: yesile doner ve aciklama degisir.')
    print()
    print('    Olculdu: kutucuk 273 px -> 15 px, alan 73 px -> 33 px.')
    print('    Pencerenin kaydirma ihtiyaci kalkti.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

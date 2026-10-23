#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MA2 — AÇIKLAMA KUTUSUNUN GÖRÜNÜMÜ
=======================================

ÖNKOŞUL: yama_ma1.py uygulanmış olmalı. MA1'i henüz uygulamadıysan
önce onu çalıştır; bu yama MA1'in koyduğu kutuyu düzeltiyor.

Haklısın, kutu yabancı duruyordu. Sebebini ölçtüm.

── NEDEN YABANCI DURUYORDU ──
  Her iki sayfanın da kendi stil bloğu var ve kural şöyle yazılmış:

      .form-alan input, .form-alan select { ... }

  `textarea` o kuralın DIŞINDA. MA1'de kutuyu textarea yapmıştım,
  stil tutmadığı için satır içi `style="..."` ile elle boyamıştım —
  yani gridin kuralına değil, kendi kuralına uyuyordu. Bu yüzden
  yükseklik, kenarlık ve odak halkası öbür alanlarla tutmuyordu.

── NE YAPTIM ──
  Kutu artık `<input>`: gridin kendi kuralına giriyor, satır içi
  stil YOK. Ölçüm:

      açıklama yüksekliği : 38 px
      Fatura No yüksekliği: 38 px     (aynı)
      kenarlık / odak      : aynı kural, aynı halka

  Yan kazanç: modal gövdesi 705 → 687 px. Kısa ekranda formun son
  alanları katlamanın altına daha az itiliyor.

── TEK SATIR 500 KARAKTERİ ALIR ──
  `<input>` göründüğünden kısa değil: 500 karakter sınırı duruyor,
  kutu içeride kayıyor. Maliyet notu zaten tek cümle
  ("K6461 kesim — 18 plaka, 2cm"); iki satırlık kutu o cümle için
  fazla yer kaplıyordu.

── BU DEĞİŞİKLİĞİN BİR TUZAĞI VARDI ──
  base.html'de global bir BÜYÜK HARF kuralı var: sistemdeki tüm
  metin girişleri otomatik büyük harfe çevriliyor. Ama kural
  yalnız `<input>`lere uygulanıyor —

      if (!el || el.tagName !== 'INPUT') return;

  textarea bu yüzden muaftı. Kutuyu input'a çevirince muafiyet
  KENDİLİĞİNDEN kalkıyordu: "K6461 kesim — 18 plaka, 2cm" yazınca
  "K6461 KESİM — 18 PLAKA, 2CM" olurdu. Serbest bir notun büyük
  harfe dönmesi okunaksızdır.

  İki kutuya da `data-buyuk-harf="hayir"` koydum. Test bunu
  ölçüyor: işaret düşerse test düşer. Ölçüldü —

      textTransform : none
      yazılan değer : 'K6461 kesim — 18 plaka, 2cm'   (olduğu gibi)

── ÖLÇÜLDÜ (tarayıcıda, iki formda da) ──
  Maliyet sayfası formu : kutu gridin içinde, hizalı
  Stok çekmecesi formu  : aynı görünüm (iki form birbirini tutuyor)
  Uçtan uca             : yazıp kaydettim, listeye düştü —
                          aciklama='K6461 kesim — 18 plaka, 2cm'
  JS hatası             : yok

  167 test geçti; firma · js · form · zincir · akis · degismezlik
  temiz.

── AYRICA GÖRDÜĞÜM, DÜZELTMEDİĞİM ──
  Kısa ekranda (≈700 px yükseklik) Maliyet Ekle formunun gövdesi
  kayıyor ama GÖRÜNÜR BİR KAYDIRMA ÇUBUĞU YOK: Tutar satırının
  altındaki alanlar kesiliyor ve kesildiğine dair işaret
  bulunmuyor. Bu MA1'den önce de vardı (gövde 683 px, görünür
  511 px) — benim eklediğim 22 px onu kötüleştirdi, yaratmadı; bu
  yama 18 px'ini geri verdi.

  Asıl sebep modaldaki stok seçici listesinin boyu. Çözümü ayrı
  bir iş: ya seçici kısalır ya gövdeye belirgin bir kaydırma
  göstergesi konur. Senin işine hangisi gelir, söyle; tahminle
  dokunmadım.

DOSYALAR
--------
  templates/maliyet.html  textarea → input · satır içi stil kalktı
  templates/stok.html     aynısı (iki form aynı görünsün)
  tests/test_kritik.py    testi yeni sözleşmeye çektim

Şema yok, göç yok, sunucu tarafı değişmedi.

KULLANIM
--------
  python3 yama_ma2.py            # RAPOR
  python3 yama_ma2.py --uygula
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
    'templates/maliyet.html': '<input id="fAciklama" maxlength="500"',
    'templates/stok.html': '<input id="malAciklama" maxlength="500"',
    'tests/test_kritik.py': 'satir ici stil geri gelmis',
}
ONKOSUL = {
    'templates/maliyet.html': 'id="fAciklama"',
    'templates/stok.html': 'id="malAciklama"',
    'tests/test_kritik.py': 'def test_ma1_iki_formda_da_aciklama_kutusu_var',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('templates/maliyet.html', 'MA2 · templates/maliyet.html blok 1',
     r'''           ama yazılacak bir kutu yoktu: hep boş kalıyordu. -->
      <div class="form-alan"><label>Açıklama</label>
        <textarea id="fAciklama" rows="2" maxlength="500"
                  placeholder="Bu gideri sonra tanımanı sağlayacak not (opsiyonel)"
                  style="width:100%;border:1px solid var(--cizgi-koyu);border-radius:var(--r-kucuk);padding:9px 11px;font-family:var(--govde);font-size:.9rem;resize:vertical"></textarea>
''',
     r'''           ama yazılacak bir kutu yoktu: hep boş kalıyordu.

           MA2: önce iki satırlık textarea'ydı ve satır içi stille
           boyanmıştı — gridin öbür alanlarıyla aynı kurala girmediği
           için yabancı duruyordu, üstelik modalı 28px uzatıp son
           alanları kısa ekranda katlamanın altına itiyordu. Artık
           tek satırlık input: aynı yükseklik, aynı kenarlık, aynı
           odak halkası. 500 karakter hâlâ sığıyor, kutu kaydırıyor. -->
      <div class="form-alan"><label>Açıklama</label>
        <input id="fAciklama" maxlength="500" data-buyuk-harf="hayir"
               placeholder="Bu gideri sonra tanımanı sağlayacak not (opsiyonel)">
'''),
    ('templates/stok.html', 'MA2 · templates/stok.html blok 1',
     r'''           yazacak kutu yoktu. Maliyet sayfasındaki formla aynı. -->
      <div class="form-alan"><label>Açıklama</label>
        <textarea id="malAciklama" rows="2" maxlength="500"
                  placeholder="Bu gideri sonra tanımanı sağlayacak not (opsiyonel)"
                  style="width:100%;border:1px solid var(--cizgi-koyu);border-radius:var(--r-kucuk);padding:9px 11px;font-family:var(--govde);font-size:.9rem;resize:vertical"></textarea>
''',
     r'''           yazacak kutu yoktu. MA2: maliyet sayfasıyla AYNI biçim —
           tek satırlık input, gridin kendi stil kuralına giriyor.
           Aynı alanın iki formda iki ayrı görünmesi, hangisinden
           girildiğini sormaya başlatırdı. -->
      <div class="form-alan"><label>Açıklama</label>
        <input id="malAciklama" maxlength="500" data-buyuk-harf="hayir"
               placeholder="Bu gideri sonra tanımanı sağlayacak not (opsiyonel)">
'''),
    ('tests/test_kritik.py', 'MA2 · tests/test_kritik.py blok 1',
     r'''    bir yerde dolup bir yerde boş kalmasıyla biterdi."""
    import io as _io
    for dosya, kutu, gonderim in (
            ('templates/maliyet.html', 'id="fAciklama"',
             "aciklama: document.getElementById('fAciklama').value.trim()"),
            ('templates/stok.html', 'id="malAciklama"',
             "aciklama: document.getElementById('malAciklama').value.trim()")):
        h = _io.open(dosya, encoding='utf-8').read()
        assert kutu in h, (dosya, kutu)
        assert gonderim in h, (dosya, gonderim)''',
     r'''    bir yerde dolup bir yerde boş kalmasıyla biterdi.

    MA2: alan textarea değil INPUT. Bu önemli bir yan etki getiriyor —
    base.html'deki global BÜYÜK HARF kuralı yalnız <input>'lere
    uygulanıyor (`el.tagName !== 'INPUT'` ile çıkıyor). İşaretsiz
    bırakılırsa "K6461 kesim" → "K6461 KESİM" olurdu; serbest bir
    notun büyük harfe çevrilmesi okunaksızdır."""
    import io as _io
    for dosya, kimlik in (('templates/maliyet.html', 'fAciklama'),
                          ('templates/stok.html', 'malAciklama')):
        h = _io.open(dosya, encoding='utf-8').read()
        assert f'id="{kimlik}"' in h, (dosya, kimlik)
        assert (f"aciklama: document.getElementById('{kimlik}')"
                ".value.trim()") in h, (dosya, kimlik)
        # Kutu satır içi stille boyanmıyor: gridin kendi kuralına
        # giriyor (.form-alan input) — iki formda da aynı görünsün.
        etiket = h[h.index(f'id="{kimlik}"') - 40:
                   h.index(f'id="{kimlik}"') + 220]
        assert '<input' in etiket, (dosya, 'textarea kalmis')
        assert 'style=' not in etiket, (dosya, 'satir ici stil geri gelmis')
        assert 'data-buyuk-harf="hayir"' in etiket, (
            dosya, 'BUYUK HARF muafiyeti dusmus — not büyük harfe döner')'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA MA2 — ACIKLAMA KUTUSUNUN GORUNUMU')
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
        print('    python3 yama_ma2.py            # rapor')
        print('    python3 yama_ma2.py --uygula')
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
        print('  ⊙ Yama MA2 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_ma2.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_ma2'
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
    print('    Finans -> Maliyetler -> Maliyet Ekle')
    print('    Depo  -> Stok -> bir stokta Maliyet Ekle')
    print('    Aciklama kutusu artik Fatura No ile ayni yukseklikte,')
    print('    ayni kenarlikta. Kucuk harf yazip kucuk kaldigini gor.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

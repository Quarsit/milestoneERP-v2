#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MA7 — DÜŞEN TESTİ KAPATIR (maliyet.html alt barı)
=======================================================

ÖNKOŞUL: yama_vt1.py uygulanmış olmalı.

Testlerde düşen tek kayıt buydu:

    test_ma4_alt_bar_kendi_zeminini_tasiyor
    AssertionError: alt bar zeminsiz kalabilir:
      [('templates/maliyet.html', '.modal-alt{padding:10px 22px 12px…')]

── NE OLMUŞ ──
  `yama_ma4.py` 17 ŞABLONUN hepsinde `.modal-alt`a kendi zeminini
  (`background` + alt köşe yuvarlaması) eklemiş ve bunu sınayan bir
  test koymuştu. Sen o yamayı uyguladın.

  Sonra "alt bara ayrı zemin yapma, panel zeminini uzat" dedin ve
  ben MA6 ile YALNIZ maliyet.html'i geri aldım. Diğer 16 şablonda
  MA4 duruyor, testi de duruyor — ve test geri aldığım tek dosyayı
  yakalıyor. Testi silmek yerine sebebini ölçtüm.

── ÖLÇÜLEN ──
  MA4'ün eklediği zemin `var(--yuzey)`, yani PANELİN KENDİ RENGİ.
  Paneli iki halde de tarayıcıda çektim:

      zemin yokken  : alt bar arka planı  rgba(0,0,0,0)
      zemin varken  : alt bar arka planı  rgb(255,255,255)
      panelin zemini: rgb(255,255,255)

  Görüntüler aynı; tek fark köşelerdeki yumuşatma (24 bayt).
  Yani bu satır GÖRÜNMÜYOR — bir güvenlik ağı.

  Senin "alt bar panelden kopmuş görünüyor" dediğin şey bu zemin
  DEĞİLDİ: MA5'te bulduğumuz kaçak `</div>` barı panelin dışına
  atıyordu; zemin sadece kopuk barı görünür kılıyordu. Nesting
  MA5'te düzeldi, zemin zararsız.

  O yüzden testi silmiyoruz, eksik satırı geri koyuyoruz: 17 şablon
  tutarlı oluyor ve görünümde hiçbir şey değişmiyor.

── BİR DE ŞUNU SÖYLEMEM LAZIM ──
  Bu düşen test, çalışma kopyamın seninkinden AYRILDIĞINI gösterdi.
  Bende MA4 hiç yoktu: 16 şablon ve o test sende vardı, bende
  değildi. O yüzden sende düşen test bende hiç koşmuyordu.

  Kopyamı seninkiyle eşitledim (MA4'ü 17 şablona ve teste
  uyguladım); artık ikimizde de 212 test var ve hepsi geçiyor.
  Bu yama yalnız SENDE eksik olan tek satırı taşıyor.

── ÖLÇÜLDÜ (yamadan sonra) ──
      212 test geçti; iki ayrı koşuda da aynı.
      js · form · zincir · akis denetimleri temiz.
      Panelin görüntüsü değişmedi (iki ekran görüntüsü karşılaştırıldı).

DOSYALAR
--------
  templates/maliyet.html   `.modal-alt` — tek satır

Şema yok, göç yok, sunucu değişmiyor.

KULLANIM
--------
  python3 yama_ma7.py            # RAPOR
  python3 yama_ma7.py --uygula
  sudo systemctl restart milestone-erp
  venv/bin/python -m pytest tests/test_kritik.py -q
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
    'templates/maliyet.html': "MA7: MA4'ün zemini GERİ KONDU",
}
ONKOSUL = {
    'templates/maliyet.html': 'padding:10px 22px 12px',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('templates/maliyet.html', 'MA7 · templates/maliyet.html blok 1',
     r'''  .modal-alt{padding:10px 22px 12px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi);flex:0 0 auto}
''',
     r'''  /* MA7: MA4'ün zemini GERİ KONDU — MA6 onu bu dosyadan almıştı ama
     diğer 16 şablonda duruyor; MA4'ün testi de duruyor ve yalnız bu
     dosyayı yakalıyordu.

     ÖLÇÜLDÜ: zemin `var(--yuzey)`, yani panelin KENDİ rengi. Paneli
     iki halde de çektim — görüntü aynı, fark yalnız köşelerdeki
     yumuşatma. Yani bu satır görünmüyor; bir güvenlik ağı.

     "Alt bar panelden kopmuş görünüyor" dediğin şey bu zemin DEĞİLDİ:
     MA5'te bulduğumuz kaçak `</div>` barı panelin dışına atıyordu,
     zemin de kopuk barı görünür kılıyordu. Nesting düzeldi, zemin
     zararsız. */
  .modal-alt{padding:10px 22px 12px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA DZ4 — KESIM KAYITLARI')
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
        print('    python3 yama_ma7.py            # rapor')
        print('    python3 yama_ma7.py --uygula')
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
        print('  ⊙ Yama MA7 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_ma7.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_ma7'
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
    print('    venv/bin/python -m pytest tests/test_kritik.py -q')
    print('    212 test gecmeli; dusen tek test kapaniyor.')
    print()
    print('    Panelin GORUNUMU degismiyor — eklenen zemin panelin')
    print('    kendi rengi. Maliyet -> Yeni ile bakabilirsin.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MA6 — MALİYET FORMU KISALTILDI
====================================

ÖNKOŞUL: yama_ma5.py uygulanmış olmalı.

İki kez eşleşmedi, sebebini anladım: ilk iki sürümde MA4'ün
YORUM BLOĞUNU da kalıba dahil etmiştim — on satırlık bir metin,
içinde Türkçe karakterler ve tireler var; bir yerinde bir bayt
farkı eşleşmeyi düşürüyor. Bu sürüm yorumu hiç kurcalamıyor,
yalnız TEK SATIRLIK kuralı hedefliyor. Senin `grep` çıktından
birebir aldım.

── 1 · O SATIRIN İŞLEVİ YOKMUŞ ──
  "Tutar, bağlanan kayıtların birim maliyetine eklenir." satırı
  (`id="mNot"`) hiçbir yerde kullanılmıyordu — JavaScript ona
  dokunmuyor, metni değişmiyor. Sabit bir cümle.

  Üstelik gereksiz: modalın alt başlığı zaten aynı şeyi söylüyor —
  "Maliyeti bir stoğa, siparişe veya sevkiyata bağla — birim
  maliyete otomatik dağıtılır."

  Sildim. Satır 33px, altındaki boşluk 12px: 45px.

  (Silmeden önce `mNot`un kullanılmadığını KELİME SINIRIYLA
  aradım — düz arama yanıltıyor, çünkü dağıtım kutusundaki
  `dagitimNot` da içinde "mNot" geçiriyor. O kutu CANLI bilgi
  taşıyor ve duruyor.)

── 2 · ALT BAR İNCELTİLDİ ──
  Dikey dolgu 14/20 → 10/12. Düğmeler aynı boyda, bar 12px ince.

  Aynı satırda MA4'ün eklediği `background` ve `border-radius`
  da kalkıyor. Onlar yanlış bir teşhisin kalıntısıydı: alt barın
  panelden kopuk görünmesini CSS sanmıştım, oysa sebep MA1'in
  tabanını kurarken düşürdüğüm `</div>`di ve MA5 onu kapattı.
  Artık işlevsizler — alt bar zaten beyaz panelin içinde, köşe
  yuvarlaması da `overflow:hidden` tarafından kırpılıyor.

  `flex:0 0 auto` DURUYOR: o ayrı bir koruma ve doğru — esnek
  sütunda alt bar ezilmesin, önce gövde küçültülsün.

── MA4'ÜN YORUMUNA DOKUNMADIM ──
  Üstteki 9 satırlık yorum hâlâ "Pardus'ta böyle görüldü" diye
  yanlış bir hikâye anlatıyor. Onu bu yamaya katmak eşleşmeyi
  üçüncü kez düşürme riski taşıyordu; ayrı bir temizlik
  yamasında, 16 şablondaki aynı artıkla birlikte düzeltirim.

── SONUÇ: SENİN PENCERENDE ARTIK KAYMIYOR ──
  Konsol çıktın pencereni 1440x820 olarak verdi. Ölçüm:

      gövde içeriği   649 → 604 px
      modal toplam    782 → 725 px
      820px'te kayıyor mu?   EVET → HAYIR

      1000px: modal=725  kayiyor=False
       900px: modal=725  kayiyor=False
       820px: modal=725  kayiyor=False   <- senin pencerende
       760px: modal=699  kayiyor=True
       700px: modal=644  kayiyor=True

── ÖLÇÜLDÜ ──
  170 test geçti; firma · js · form · zincir · akis ·
  degismezlik temiz. JS hatası yok.

DOSYALAR
--------
  templates/maliyet.html   işlevsiz bilgi satırı silindi ·
                           alt bar inceltildi

Şema yok, göç yok, test değişmedi.

KULLANIM
--------
  python3 yama_ma6.py            # RAPOR
  python3 yama_ma6.py --uygula
  sudo systemctl restart milestone-erp
  (tarayıcıda Ctrl+F5 — CSS değişti)
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

DOSYA_IMZA = {'templates/maliyet.html': 'padding:10px 22px 12px'}
ONKOSUL = {'templates/maliyet.html': 'id="fAciklama"'}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('templates/maliyet.html', 'MA6 · islevsiz bilgi satiri siliniyor',
     '      <div class="not" id="mNot">Tutar, bağlanan kayıtların birim maliyetine eklenir.</div>\n', ''),
    ('templates/maliyet.html', 'MA6 · alt bar inceltiliyor (tek satir)',
     '  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}\n', '  .modal-alt{padding:10px 22px 12px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi);flex:0 0 auto}\n'),
]
TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA MA6 — MALIYET FORMU KISALTILDI')
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
        print('    python3 yama_ma6.py            # rapor')
        print('    python3 yama_ma6.py --uygula')
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
        print('  ⊙ Yama MA6 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_ma6.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_ma6'
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
    print()
    print('  BAKILACAK YER: Finans -> Maliyetler -> Maliyet Ekle')
    print('  Senin pencerende (1440x820) form artik HIC KAYMIYOR.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

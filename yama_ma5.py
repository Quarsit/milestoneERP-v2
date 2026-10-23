#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MA5 — FAZLADAN </div> SİLİNİYOR
=====================================

ÖNKOŞUL: yama_ma1.py uygulanmış olmalı. MA4'ü geri aldıysan sorun
değil, bu yama ondan bağımsız.

Alt barın modalin dışında kalmasının sebebi buydu ve BENİM
HATAMDI.

── NE OLDU ──
  MA1'in tabanını kurarken maliyet.html'den açıklama bloğunu elle
  kestim. Kesme noktasını `id="fAciklama"` sonrasındaki İKİNCİ
  `</div>`e göre hesapladım — ama o ikinci kapanış açıklama
  kutusunun değil, `.modal-gov`un kapanışıydı. Tabanım bir
  `</div>` eksik çıktı; yama da onu "eklenecek" bir parça sanıp
  geri koyan bir blok olarak kodlandı.

  Senin dosyanda o `</div>` zaten vardı. Yama kendi kopyasını da
  ekleyince fazladan bir kapanış oluştu:

      </div>          ← form-satir f2 (dogru)
    </div>            ← FAZLADAN: .modal-gov burada kapaniyor
      <!-- MA1 · AÇIKLAMA

  Gerisi zincir: açıklama bir kat yukarı `.modal`in içine düşüyor,
  blok sonundaki kapanış bu sefer `.modal`i kapatıyor, alt bar
  `.modal-ortu` ızgarasına kalıyor — ızgara `place-items:center`
  olduğu için ortalanıp içeriği kadar daralıyor. 220px'lik o
  ensiz düğme kutusu tam olarak bu.

── DOĞRULAMAM NEDEN YAKALAMADI ──
  Yamayı kendi tabanıma uygulayıp kendi dosyamla bayt bayt
  karşılaştırıyordum. İkisi de aynı hatayı taşıdığı için
  karşılaştırma hep "aynı" diyordu. Taban, senin gerçek dosyandan
  türetilmediği sürece bu doğrulama kendi kendini onaylıyor.
  Bundan sonra elle kesilmiş taban kullanmayacağım; taban ya
  origin'den ya da önceki yamanın uygulanmasıyla üretilecek.

── BU YAMA NE YAPIYOR ──
  Tek satır siliyor: 327. satırdaki fazladan `    </div>`.
  Başka hiçbir şeye dokunmuyor.

── ÖNCESİ / SONRASI ──
  önce   .modal-gov 327'de kapanıyor, .modal 343'te,
         alt bar 344'te — yani DIŞARIDA
  sonra  .modal-gov 333'te kapanıyor, alt bar 334'te — İÇERİDE

── BİR DE ŞUNU KONTROL ET ──
  Aynı hata stok.html'de yok: oranın tabanını elle kesmedim,
  SD1 yamasını temiz kopyaya uygulayarak ürettim. Yine de bir
  bakalım — Depo → Stok → bir stokta "Maliyet Ekle" aç, Vazgeç/
  Kaydet barı panelin içinde mi? Değilse söyle, aynı şekilde
  kapatırım.

── ARTIK TEST KORUYOR ──
  Yeni test şablonu gerçek bir HTML ayrıştırıcısıyla okuyup
  YAPIYA bakıyor: her modalda `.modal-alt`, `.modal`in içinde mi?
  Bayt bayt karşılaştırmaya güvenmiyor — beni yanıltan oydu.
  Bozuk kopyada düştüğünü, sağlam kopyada geçtiğini gördüm.

DOSYALAR
--------
  templates/maliyet.html   bir satır siliniyor
  tests/test_kritik.py     1 yeni yapısal test

Şema yok, göç yok.

KULLANIM
--------
  python3 yama_ma5.py            # RAPOR
  python3 yama_ma5.py --uygula
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

# Uygulanmis hali: form-satir kapanisini DOGRUDAN aciklama yorumu
# izliyor. Bozuk halde arada bir `    </div>` var.
DOSYA_IMZA = {
    'templates/maliyet.html':
        '      </div>\n      <!-- MA1 · AÇIKLAMA',
    'tests/test_kritik.py':
        'def test_ma5_her_modalda_alt_bar_modalin_icinde',
}
ONKOSUL = {
    'templates/maliyet.html': '<!-- MA1 · AÇIKLAMA',
    'tests/test_kritik.py': 'def test_ma3_maliyet_formu_iki_uclu_satirda',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('templates/maliyet.html', 'MA5 · fazladan </div> siliniyor',
     '        <div class="form-alan"><label>Tedarikçi (cari)</label><select id="fCari"><option value="">— yok —</option></select></div>\n      </div>\n    </div>\n      <!-- MA1 · AÇIKLAMA\n',
     '        <div class="form-alan"><label>Tedarikçi (cari)</label><select id="fCari"><option value="">— yok —</option></select></div>\n      </div>\n      <!-- MA1 · AÇIKLAMA\n'),
    ('tests/test_kritik.py', 'MA5 · yapisal test',
     '    assert "[\'fAlanUretici\', \'fAlanCins\', \'fAlanBlok\']" in tam\n',
     '    assert "[\'fAlanUretici\', \'fAlanCins\', \'fAlanBlok\']" in tam\n\n\ndef test_ma5_her_modalda_alt_bar_modalin_icinde():\n    """MA5: `.modal-alt`, `.modal`in İÇİNDE olmak zorunda. Dışına\n    çıkarsa `.modal-ortu` ızgarasının (place-items:center) çocuğu\n    olur: ortalanır ve içeriği kadar daralır — panelden kopmuş\n    ensiz bir düğme kutusu.\n\n    Bunu bir yamam yaptı. MA1\'in tabanını kurarken maliyet.html\'den\n    açıklama bloğunu elle kesmiştim ve kesme noktası `.modal-gov`un\n    kapanışını da götürmüştü; yama o `</div>`i "eklenecek" sanıp\n    geri koyunca kullanıcının dosyasında FAZLADAN bir kapanış\n    oluştu. Bayt bayt doğrulamam yakalayamadı çünkü yamayı kendi\n    bozuk tabanıma uygulayıp kendi dosyamla karşılaştırıyordum —\n    ikisi de aynı hatayı taşıyordu.\n\n    Bu test o karşılaştırmaya güvenmiyor: şablonu gerçek bir HTML\n    ayrıştırıcısıyla okuyup YAPIYA bakıyor."""\n    import glob\n    import io as _io\n    import re\n    from html.parser import HTMLParser\n\n    BOS = {\'input\', \'br\', \'hr\', \'img\', \'meta\', \'link\', \'source\',\n           \'col\', \'area\', \'base\', \'embed\', \'track\', \'wbr\'}\n\n    class Y(HTMLParser):\n        def __init__(self):\n            super().__init__(convert_charrefs=True)\n            self.yigin = []\n            self.kapanis = {}\n\n        def handle_starttag(self, etiket, nitelikler):\n            if etiket in BOS:\n                return\n            self.yigin.append((etiket, dict(nitelikler).get(\'class\', \'\') or \'\',\n                               self.getpos()[0]))\n\n        def handle_endtag(self, etiket):\n            sat = self.getpos()[0]\n            for i in range(len(self.yigin) - 1, -1, -1):\n                if self.yigin[i][0] == etiket:\n                    for _e, snf, ac in self.yigin[i:]:\n                        k = snf.split()[0] if snf else \'\'\n                        if k in (\'modal\', \'modal-alt\'):\n                            self.kapanis.setdefault((k, ac), sat)\n                    del self.yigin[i:]\n                    return\n\n    bozuk = []\n    for yol in sorted(glob.glob(\'templates/*.html\')):\n        g = _io.open(yol, encoding=\'utf-8\').read()\n        t = re.sub(r\'\\{%.*?%\\}\', \'\', g, flags=re.S)\n        t = re.sub(r\'\\{\\{.*?\\}\\}\', \'\', t, flags=re.S)\n        for ortu in re.finditer(r\'<div class="modal-ortu"[^>]*>\', t):\n            bas, derin, kes = ortu.start(), 0, len(t)\n            for x in re.finditer(r\'<div\\b|</div>\', t[bas:]):\n                derin += 1 if x.group(0) == \'<div\' else -1\n                if derin == 0:\n                    kes = bas + x.end()\n                    break\n            y = Y()\n            y.feed(t[bas:kes])\n            mo = [(a, b) for (k, a), b in y.kapanis.items() if k == \'modal\']\n            al = [(a, b) for (k, a), b in y.kapanis.items() if k == \'modal-alt\']\n            if not (mo and al):\n                continue\n            ac_m, kap_m = mo[0]\n            ac_a, _ = al[0]\n            if not (ac_m < ac_a < kap_m):\n                bozuk.append((yol, t[:bas].count(\'\\n\') + 1))\n    assert not bozuk, f\'alt bar .modal dışında kalmış: {bozuk}\'\n'),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA MA5 — FAZLADAN </div> SILINIYOR')
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
        print('    python3 yama_ma5.py            # rapor')
        print('    python3 yama_ma5.py --uygula')
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
        print('  ⊙ Yama MA5 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_ma5.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_ma5'
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
    print('  DOGRULAMA: teshis_modal.py yeniden calistir.')
    print('  Soyle demeli:')
    print('      .modal-gov  kapanis satir 333')
    print('      .modal-alt  acilis  satir 334')
    print('      ✓ Yuvalanma dogru: alt bar .modal icinde.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

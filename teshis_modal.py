#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEŞHİS — modal yuvalanması nerede bozuluyor
===========================================

Tarayıcı konsolu şunu söyledi:

    alt_modalin_cocugu : "modal-ortu acik"   ← alt bar modalin DIŞINDA
    aciklama_ebeveyni  : "modal"             ← açıklama gövdenin DIŞINDA

İkisi birden FAZLADAN BİR </div> ile açıklanıyor. Bu betik o
fazlalığın hangi satırda olduğunu bulur. Hiçbir dosyayı
DEĞİŞTİRMEZ — yalnız okur ve rapor eder.

    cd ~/milestoneERP-v2
    python3 teshis_modal.py

Çıktıyı bana gönder, tek satırlık yamayı ona göre yazayım.
"""
import hashlib
import io
import os
import re
import sys
from html.parser import HTMLParser

# Bende (MA3 uygulanmis halde) bu dosya soyle:
BEKLENEN = {'templates/maliyet.html': ('5d1fd8095ae8bad2', 1053, 82)}

BEKLENEN_KAPANIS = 333   # bende .modal-gov burada kapaniyor

BOS_ETIKET = {'input', 'br', 'hr', 'img', 'meta', 'link', 'source',
              'col', 'area', 'base', 'embed', 'track', 'wbr'}


class Yoklayici(HTMLParser):
    """Etiket yigini tutar; ilgilendigimiz kutularin nerede
    kapandigini ve fazladan kapanis etiketlerini isaretler."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.yigin = []
        self.notlar = []
        self.kapanis = {}

    def _snf(self, nitelikler):
        return dict(nitelikler).get('class', '') or ''

    def handle_starttag(self, etiket, nitelikler):
        if etiket in BOS_ETIKET:
            return
        self.yigin.append((etiket, self._snf(nitelikler),
                           self.getpos()[0]))

    def handle_startendtag(self, etiket, nitelikler):
        pass

    def handle_endtag(self, etiket):
        satir = self.getpos()[0]
        for i in range(len(self.yigin) - 1, -1, -1):
            if self.yigin[i][0] == etiket:
                for e, s, ac in self.yigin[i:]:
                    for isim in ('modal-ortu', 'modal-gov', 'modal-alt'):
                        if s.split()[0:1] == [isim] or s == isim:
                            self.kapanis.setdefault(isim, (ac, satir))
                    if s.strip() == 'modal':
                        self.kapanis.setdefault('modal', (
                            self.yigin[i][2], satir))
                if i != len(self.yigin) - 1:
                    acikta = [f'{e}.{s}' if s else e
                              for e, s, _ in self.yigin[i + 1:]]
                    self.notlar.append(
                        f'satir {satir}: </{etiket}> kapanirken su kutular '
                        f'hala acikti: {acikta}')
                del self.yigin[i:]
                return
        self.notlar.append(f'satir {satir}: FAZLADAN </{etiket}>')


def ana():
    yol = 'templates/maliyet.html'
    if not os.path.exists(yol):
        print(f'HATA: {yol} bulunamadi. Repo kokunde calistir.')
        return 1

    ham = io.open(yol, encoding='utf-8', newline='').read()
    ozet = hashlib.sha256(ham.encode('utf-8')).hexdigest()[:16]
    satir_sayisi = ham.count('\n') + (0 if ham.endswith('\n') else 1)
    kapanis_sayisi = ham.count('</div>')
    b_ozet, b_satir, b_kapanis = BEKLENEN[yol]

    print('=' * 68)
    print('  DOSYA KARSILASTIRMASI')
    print('=' * 68)
    print(f'  ozet       sende {ozet}   bende {b_ozet}')
    print(f'  satir      sende {satir_sayisi:<6}             bende {b_satir}')
    print(f'  </div>     sende {kapanis_sayisi:<6}             bende {b_kapanis}')
    if ozet == b_ozet:
        print()
        print('  → DOSYALAR AYNI. O zaman sorun dosyada degil:')
        print('    tarayici eski surumu onbellekten okuyor olabilir.')
        print('    Ctrl+Shift+R dene, ya da gizli pencerede ac.')
    else:
        fark = kapanis_sayisi - b_kapanis
        print()
        if fark > 0:
            print(f'  → SENDE {fark} FAZLA </div> VAR. Yeri asagida.')
        elif fark < 0:
            print(f'  → SENDE {-fark} EKSIK </div> VAR. Yeri asagida.')
        else:
            print('  → Sayilar ayni ama icerik farkli; yapiya bakiyorum.')

    # Jinja bloklarini ayikla — ayristiriciyi yaniltmasinlar
    temiz = re.sub(r'\{%.*?%\}', '', ham, flags=re.S)
    temiz = re.sub(r'\{\{.*?\}\}', '', temiz, flags=re.S)

    # YALNIZ "Maliyet Ekle" modali: sayfada baska modallar da var,
    # ilkini olcmek yanlis yeri gosterirdi.
    try:
        bas = temiz.index('<div class="modal-ortu" id="modal"')
    except ValueError:
        print('  HATA: id="modal" kapsayicisi bulunamadi.')
        return 1
    son = temiz.index('{% endblock %}') if '{% endblock %}' in temiz else len(temiz)
    son = temiz.index('</div>', temiz.rindex('</div>', bas, len(temiz))) + 6
    parca = temiz[bas:]
    # Kapsayici kapanana kadar oku
    derin, kes = 0, len(parca)
    for mm in re.finditer(r'<div\b|</div>', parca):
        derin += 1 if mm.group(0) == '<div' else -1
        if derin == 0:
            kes = mm.end()
            break
    parca = parca[:kes]
    satir_ofset = temiz[:bas].count('\n')

    print()
    print('=' * 68)
    print('  YUVALANMA  ("Maliyet Ekle" modali)')
    print('=' * 68)
    y = Yoklayici()
    try:
        y.feed(parca)
    except Exception as hata:            # noqa: BLE001
        print(f'  ayristirma hatasi: {hata}')
    for isim in ('modal-ortu', 'modal', 'modal-gov', 'modal-alt'):
        if isim in y.kapanis:
            ac, kap = y.kapanis[isim]
            print(f'  .{isim:<11} acilis satir {ac + satir_ofset:>5}'
                  f'   kapanis satir {kap + satir_ofset:>5}')
        else:
            print(f'  .{isim:<11} BULUNAMADI')

    g = y.kapanis.get('modal-gov')
    a = y.kapanis.get('modal-alt')
    m = y.kapanis.get('modal')
    print()
    if g and a and m:
        if not (g[1] < a[0] < m[1]):
            print('  ✗ BOZUK: alt bar .modal icinde DEGIL.')
            print(f'    .modal {m[1] + satir_ofset}. satirda kapaniyor, '
                  f'alt bar {a[0] + satir_ofset}. satirda aciliyor.')
            print()
            print('  FAZLALIK BURADA: .modal-gov '
                  f'{g[1] + satir_ofset}. satirda kapaniyor. Bende '
                  f'{BEKLENEN_KAPANIS}. satirda kapaniyor.')
            print('  O satirin cevresi:')
            satirlar = ham.split('\n')
            sn = g[1] + satir_ofset
            for i in range(max(1, sn - 6), min(len(satirlar), sn + 2) + 1):
                im = '  >>' if i == sn else '    '
                print(f'   {im} {i:>5}: {satirlar[i - 1].rstrip()[:84]}')
        else:
            print('  ✓ Yuvalanma dogru: alt bar .modal icinde.')

    if y.notlar:
        print()
        print('  ISARETLENEN SATIRLAR:')
        for n in y.notlar[:12]:
            print('   ', re.sub(r'satir (\d+)',
                  lambda x: 'satir ' + str(int(x.group(1)) + satir_ofset), n))
            sn = int(re.search(r'satir (\d+)', n).group(1)) + satir_ofset
            for i in range(max(1, sn - 2), min(satir_sayisi, sn + 2) + 1):
                im = '  >>' if i == sn else '    '
                try:
                    icerik = ham.split('\n')[i - 1].rstrip()[:88]
                except IndexError:
                    continue
                print(f'   {im} {i:>5}: {icerik}')
            print()
    else:
        print()
        print('  (Esleshen bir acilis bulundugu icin ayristirici bunu')
        print('   "fazladan etiket" diye isaretlemiyor — yanlis kutuyu')
        print('   kapatiyor, o kadar. Yukaridaki satir numaralari bakin.)')
    print('=' * 68)
    print('  Bu ciktinin tamamini gonder.')
    print('=' * 68)
    return 0


if __name__ == '__main__':
    sys.exit(ana())

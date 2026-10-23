#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MA4 — ALT BAR PANELİN İÇİNDE KALSIN
=========================================

ÖNKOŞUL: yama_ma3.py uygulanmış olmalı.

Dediğini yaptım: alt bar artık KENDİ zeminini taşıyor.

── NEDEN ÖYLE GÖRÜNÜYORDU ──
  Vazgeç/Kaydet barının kendi zemini yoktu — `.modal`in beyaz
  zemininin üzerinde duruyordu. Yani zemini kendisinin değil,
  KAPSAYICISININDI. Gövde bir şekilde kapsayıcıyı aşınca alt bar
  zeminsiz kalıyor ve panelden kopmuş görünüyor; senin gördüğün
  bu.

  Artık `.modal-alt` kendi `background` ve alt köşe
  yuvarlamasını taşıyor. Dizilim ne olursa olsun panelin parçası
  gibi duruyor — zemin düğmelerin altına kadar iniyor.

  Yanına bir koruma daha: `flex:0 0 auto`. Esnek sütunda alt bar
  asla ezilmesin, önce gövde küçültülsün.

── HÂLÂ ÜRETEMİYORUM, BUNU SÖYLEMELİYİM ──
  MA3'teki `min-height:0` düzeltmesi doğruydu ve gerekliydi ama
  seninkini çözmemiş. Burada — Chromium'da — taşma hiçbir ekran
  boyunda olmuyor; ölçtüm, alt bar taşması 0 px. Yani sendeki
  farkı hâlâ bilmiyorum; bu yama o farkı ARAMIYOR, görüntüyü
  her hâlükârda doğru yapıyor.

  Kesin teşhis için tarayıcı konsoluna yapıştıracağın tek satır
  yamanın sonunda duruyor. Çıktısını bana gönderirsen sebebi
  kesin bulurum.

── ÖLÇÜLDÜ ──
  17 şablonda alt bar kendi zeminini taşıyor.
  13 sayfa, 73 modal tarandı: JS hatası yok, taşma 0 px.
  170 test geçti; firma · js · form · zincir · akis ·
  degismezlik temiz.

DOSYALAR
--------
  17 şablon            `.modal-alt` kendi zeminini taşıyor
  tests/test_kritik.py 1 yeni test

Şema yok, göç yok, sunucu tarafı değişmedi.

KULLANIM
--------
  python3 yama_ma4.py            # RAPOR
  python3 yama_ma4.py --uygula
  sudo systemctl restart milestone-erp
  (tarayıcıda Ctrl+F5 — CSS değişti)

TEŞHİS (hâlâ bozuksa)
---------------------
  Maliyet Ekle'yi aç, F12 → Konsol, şunu yapıştır ve çıktıyı
  bana gönder:

  (()=>{const a=document.getElementById('fAciklama'),
  g=document.querySelector('#modal .modal-gov'),
  m=document.querySelector('#modal .modal'),
  f=document.querySelector('#modal .modal-alt'),
  S=getComputedStyle;return JSON.stringify({
  aciklama_govdede:!!(a&&a.closest('.modal-gov')),
  gov_minh:S(g).minHeight,gov_ovf:S(g).overflowY,
  modal_ovf:S(m).overflow,modal_maxh:S(m).maxHeight,
  modal_display:S(m).display,modal_dir:S(m).flexDirection,
  modal_h:Math.round(m.getBoundingClientRect().height),
  gov_h:Math.round(g.getBoundingClientRect().height),
  alt_tasma:Math.round(f.getBoundingClientRect().bottom-
  m.getBoundingClientRect().bottom),
  pencere:innerWidth+'x'+innerHeight,
  ua:navigator.userAgent},null,1)})()
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

_IMZA = 'MA4: ALT BAR'
_ON = '.modal-alt{'
DOSYA_IMZA = {'tests/test_kritik.py':
              'def test_ma4_alt_bar_kendi_zeminini_tasiyor'}
ONKOSUL = {'tests/test_kritik.py':
           'def test_ma3_modal_govdesi_esnek_kutuda_kuculebiliyor'}
for _a in ['ayarlar.html', 'base.html', 'cari.html', 'cek.html', 'fatura.html', 'kasa.html', 'kdv_iade.html', 'kesim.html', 'maliyet.html', 'musteri.html', 'nakit.html', 'ortaklik.html', 'proforma.html', 'sabit_gider.html', 'sevkiyat.html', 'siparis.html', 'stok.html']:
    DOSYA_IMZA['templates/' + _a] = _IMZA
    ONKOSUL['templates/' + _a] = _ON
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('templates/ayarlar.html', 'MA4 · templates/ayarlar.html blok 1',
     r'''  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi)}
''',
     r'''  /* MA4: ALT BAR KENDI ZEMININI TASIR.
     Alt bar `.modal`in beyaz zemininin uzerinde duruyordu —
     yani zemini kendisinin degil, kapsayicisinindi. Gövde
     bir sekilde kapsayiciyi asinca alt bar ZEMINSIZ kaliyor
     ve panelden kopmus gorunuyor (Pardus'ta boyle goruldu,
     burada uretilemedi). Kendi zeminini ve alt kose
     yuvarlamasini tasiyinca panelin parcasi gibi kaliyor.
     `flex:0 0 auto` de ayri bir koruma: esnek sutunda alt bar
     asla ezilmesin, once govde kucultulsun. */
  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
    ('templates/base.html', 'MA4 · templates/base.html blok 1',
     r'''.modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi)}
''',
     r'''/* MA4: ALT BAR KENDI ZEMININI TASIR.
   Alt bar `.modal`in beyaz zemininin uzerinde duruyordu —
   yani zemini kendisinin degil, kapsayicisinindi. Gövde
   bir sekilde kapsayiciyi asinca alt bar ZEMINSIZ kaliyor
   ve panelden kopmus gorunuyor (Pardus'ta boyle goruldu,
   burada uretilemedi). Kendi zeminini ve alt kose
   yuvarlamasini tasiyinca panelin parcasi gibi kaliyor.
   `flex:0 0 auto` de ayri bir koruma: esnek sutunda alt bar
   asla ezilmesin, once govde kucultulsun. */
.modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
    ('templates/cari.html', 'MA4 · templates/cari.html blok 1',
     r'''  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi)}
''',
     r'''  /* MA4: ALT BAR KENDI ZEMININI TASIR.
     Alt bar `.modal`in beyaz zemininin uzerinde duruyordu —
     yani zemini kendisinin degil, kapsayicisinindi. Gövde
     bir sekilde kapsayiciyi asinca alt bar ZEMINSIZ kaliyor
     ve panelden kopmus gorunuyor (Pardus'ta boyle goruldu,
     burada uretilemedi). Kendi zeminini ve alt kose
     yuvarlamasini tasiyinca panelin parcasi gibi kaliyor.
     `flex:0 0 auto` de ayri bir koruma: esnek sutunda alt bar
     asla ezilmesin, once govde kucultulsun. */
  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
    ('templates/cek.html', 'MA4 · templates/cek.html blok 1',
     r'''  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi)}
''',
     r'''  /* MA4: ALT BAR KENDI ZEMININI TASIR.
     Alt bar `.modal`in beyaz zemininin uzerinde duruyordu —
     yani zemini kendisinin degil, kapsayicisinindi. Gövde
     bir sekilde kapsayiciyi asinca alt bar ZEMINSIZ kaliyor
     ve panelden kopmus gorunuyor (Pardus'ta boyle goruldu,
     burada uretilemedi). Kendi zeminini ve alt kose
     yuvarlamasini tasiyinca panelin parcasi gibi kaliyor.
     `flex:0 0 auto` de ayri bir koruma: esnek sutunda alt bar
     asla ezilmesin, once govde kucultulsun. */
  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
    ('templates/fatura.html', 'MA4 · templates/fatura.html blok 1',
     r'''  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi)}
''',
     r'''  /* MA4: ALT BAR KENDI ZEMININI TASIR.
     Alt bar `.modal`in beyaz zemininin uzerinde duruyordu —
     yani zemini kendisinin degil, kapsayicisinindi. Gövde
     bir sekilde kapsayiciyi asinca alt bar ZEMINSIZ kaliyor
     ve panelden kopmus gorunuyor (Pardus'ta boyle goruldu,
     burada uretilemedi). Kendi zeminini ve alt kose
     yuvarlamasini tasiyinca panelin parcasi gibi kaliyor.
     `flex:0 0 auto` de ayri bir koruma: esnek sutunda alt bar
     asla ezilmesin, once govde kucultulsun. */
  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
    ('templates/kasa.html', 'MA4 · templates/kasa.html blok 1',
     r'''  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi)}
''',
     r'''  /* MA4: ALT BAR KENDI ZEMININI TASIR.
     Alt bar `.modal`in beyaz zemininin uzerinde duruyordu —
     yani zemini kendisinin degil, kapsayicisinindi. Gövde
     bir sekilde kapsayiciyi asinca alt bar ZEMINSIZ kaliyor
     ve panelden kopmus gorunuyor (Pardus'ta boyle goruldu,
     burada uretilemedi). Kendi zeminini ve alt kose
     yuvarlamasini tasiyinca panelin parcasi gibi kaliyor.
     `flex:0 0 auto` de ayri bir koruma: esnek sutunda alt bar
     asla ezilmesin, once govde kucultulsun. */
  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
    ('templates/kdv_iade.html', 'MA4 · templates/kdv_iade.html blok 1',
     r'''  .modal-alt{padding:14px 22px;border-top:1px solid var(--cizgi);display:flex;justify-content:flex-end;gap:9px}
''',
     r'''  /* MA4: ALT BAR KENDI ZEMININI TASIR.
     Alt bar `.modal`in beyaz zemininin uzerinde duruyordu —
     yani zemini kendisinin degil, kapsayicisinindi. Gövde
     bir sekilde kapsayiciyi asinca alt bar ZEMINSIZ kaliyor
     ve panelden kopmus gorunuyor (Pardus'ta boyle goruldu,
     burada uretilemedi). Kendi zeminini ve alt kose
     yuvarlamasini tasiyinca panelin parcasi gibi kaliyor.
     `flex:0 0 auto` de ayri bir koruma: esnek sutunda alt bar
     asla ezilmesin, once govde kucultulsun. */
  .modal-alt{padding:14px 22px;border-top:1px solid var(--cizgi);display:flex;justify-content:flex-end;gap:9px;background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
    ('templates/kesim.html', 'MA4 · templates/kesim.html blok 1',
     r'''  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi)}
''',
     r'''  /* MA4: ALT BAR KENDI ZEMININI TASIR.
     Alt bar `.modal`in beyaz zemininin uzerinde duruyordu —
     yani zemini kendisinin degil, kapsayicisinindi. Gövde
     bir sekilde kapsayiciyi asinca alt bar ZEMINSIZ kaliyor
     ve panelden kopmus gorunuyor (Pardus'ta boyle goruldu,
     burada uretilemedi). Kendi zeminini ve alt kose
     yuvarlamasini tasiyinca panelin parcasi gibi kaliyor.
     `flex:0 0 auto` de ayri bir koruma: esnek sutunda alt bar
     asla ezilmesin, once govde kucultulsun. */
  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
    ('templates/maliyet.html', 'MA4 · templates/maliyet.html blok 1',
     r'''  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi)}
''',
     r'''  /* MA4: ALT BAR KENDI ZEMININI TASIR.
     Alt bar `.modal`in beyaz zemininin uzerinde duruyordu —
     yani zemini kendisinin degil, kapsayicisinindi. Gövde
     bir sekilde kapsayiciyi asinca alt bar ZEMINSIZ kaliyor
     ve panelden kopmus gorunuyor (Pardus'ta boyle goruldu,
     burada uretilemedi). Kendi zeminini ve alt kose
     yuvarlamasini tasiyinca panelin parcasi gibi kaliyor.
     `flex:0 0 auto` de ayri bir koruma: esnek sutunda alt bar
     asla ezilmesin, once govde kucultulsun. */
  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
    ('templates/musteri.html', 'MA4 · templates/musteri.html blok 1',
     r'''  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;
    border-top:1px solid var(--cizgi)}
''',
     r'''  /* MA4: ALT BAR KENDI ZEMININI TASIR.
     Alt bar `.modal`in beyaz zemininin uzerinde duruyordu —
     yani zemini kendisinin degil, kapsayicisinindi. Gövde
     bir sekilde kapsayiciyi asinca alt bar ZEMINSIZ kaliyor
     ve panelden kopmus gorunuyor (Pardus'ta boyle goruldu,
     burada uretilemedi). Kendi zeminini ve alt kose
     yuvarlamasini tasiyinca panelin parcasi gibi kaliyor.
     `flex:0 0 auto` de ayri bir koruma: esnek sutunda alt bar
     asla ezilmesin, once govde kucultulsun. */
  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;
    border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
    ('templates/nakit.html', 'MA4 · templates/nakit.html blok 1',
     r'''  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;
    border-top:1px solid var(--cizgi)}
''',
     r'''  /* MA4: ALT BAR KENDI ZEMININI TASIR.
     Alt bar `.modal`in beyaz zemininin uzerinde duruyordu —
     yani zemini kendisinin degil, kapsayicisinindi. Gövde
     bir sekilde kapsayiciyi asinca alt bar ZEMINSIZ kaliyor
     ve panelden kopmus gorunuyor (Pardus'ta boyle goruldu,
     burada uretilemedi). Kendi zeminini ve alt kose
     yuvarlamasini tasiyinca panelin parcasi gibi kaliyor.
     `flex:0 0 auto` de ayri bir koruma: esnek sutunda alt bar
     asla ezilmesin, once govde kucultulsun. */
  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;
    border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
    ('templates/ortaklik.html', 'MA4 · templates/ortaklik.html blok 1',
     r'''  .modal-alt{padding:14px 22px 18px;display:flex;gap:10px;justify-content:flex-end;
    border-top:1px solid var(--cizgi)}
''',
     r'''  /* MA4: ALT BAR KENDI ZEMININI TASIR.
     Alt bar `.modal`in beyaz zemininin uzerinde duruyordu —
     yani zemini kendisinin degil, kapsayicisinindi. Gövde
     bir sekilde kapsayiciyi asinca alt bar ZEMINSIZ kaliyor
     ve panelden kopmus gorunuyor (Pardus'ta boyle goruldu,
     burada uretilemedi). Kendi zeminini ve alt kose
     yuvarlamasini tasiyinca panelin parcasi gibi kaliyor.
     `flex:0 0 auto` de ayri bir koruma: esnek sutunda alt bar
     asla ezilmesin, once govde kucultulsun. */
  .modal-alt{padding:14px 22px 18px;display:flex;gap:10px;justify-content:flex-end;
    border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
    ('templates/proforma.html', 'MA4 · templates/proforma.html blok 1',
     r'''  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi)}
''',
     r'''  /* MA4: ALT BAR KENDI ZEMININI TASIR.
     Alt bar `.modal`in beyaz zemininin uzerinde duruyordu —
     yani zemini kendisinin degil, kapsayicisinindi. Gövde
     bir sekilde kapsayiciyi asinca alt bar ZEMINSIZ kaliyor
     ve panelden kopmus gorunuyor (Pardus'ta boyle goruldu,
     burada uretilemedi). Kendi zeminini ve alt kose
     yuvarlamasini tasiyinca panelin parcasi gibi kaliyor.
     `flex:0 0 auto` de ayri bir koruma: esnek sutunda alt bar
     asla ezilmesin, once govde kucultulsun. */
  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
    ('templates/sabit_gider.html', 'MA4 · templates/sabit_gider.html blok 1',
     r'''  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;
    border-top:1px solid var(--cizgi)}
''',
     r'''  /* MA4: ALT BAR KENDI ZEMININI TASIR.
     Alt bar `.modal`in beyaz zemininin uzerinde duruyordu —
     yani zemini kendisinin degil, kapsayicisinindi. Gövde
     bir sekilde kapsayiciyi asinca alt bar ZEMINSIZ kaliyor
     ve panelden kopmus gorunuyor (Pardus'ta boyle goruldu,
     burada uretilemedi). Kendi zeminini ve alt kose
     yuvarlamasini tasiyinca panelin parcasi gibi kaliyor.
     `flex:0 0 auto` de ayri bir koruma: esnek sutunda alt bar
     asla ezilmesin, once govde kucultulsun. */
  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;
    border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
    ('templates/sevkiyat.html', 'MA4 · templates/sevkiyat.html blok 1',
     r'''  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi)}
''',
     r'''  /* MA4: ALT BAR KENDI ZEMININI TASIR.
     Alt bar `.modal`in beyaz zemininin uzerinde duruyordu —
     yani zemini kendisinin degil, kapsayicisinindi. Gövde
     bir sekilde kapsayiciyi asinca alt bar ZEMINSIZ kaliyor
     ve panelden kopmus gorunuyor (Pardus'ta boyle goruldu,
     burada uretilemedi). Kendi zeminini ve alt kose
     yuvarlamasini tasiyinca panelin parcasi gibi kaliyor.
     `flex:0 0 auto` de ayri bir koruma: esnek sutunda alt bar
     asla ezilmesin, once govde kucultulsun. */
  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
    ('templates/siparis.html', 'MA4 · templates/siparis.html blok 1',
     r'''  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi)}
''',
     r'''  /* MA4: ALT BAR KENDI ZEMININI TASIR.
     Alt bar `.modal`in beyaz zemininin uzerinde duruyordu —
     yani zemini kendisinin degil, kapsayicisinindi. Gövde
     bir sekilde kapsayiciyi asinca alt bar ZEMINSIZ kaliyor
     ve panelden kopmus gorunuyor (Pardus'ta boyle goruldu,
     burada uretilemedi). Kendi zeminini ve alt kose
     yuvarlamasini tasiyinca panelin parcasi gibi kaliyor.
     `flex:0 0 auto` de ayri bir koruma: esnek sutunda alt bar
     asla ezilmesin, once govde kucultulsun. */
  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
    ('templates/stok.html', 'MA4 · templates/stok.html blok 1',
     r'''  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi)}
''',
     r'''  /* MA4: ALT BAR KENDI ZEMININI TASIR.
     Alt bar `.modal`in beyaz zemininin uzerinde duruyordu —
     yani zemini kendisinin degil, kapsayicisinindi. Gövde
     bir sekilde kapsayiciyi asinca alt bar ZEMINSIZ kaliyor
     ve panelden kopmus gorunuyor (Pardus'ta boyle goruldu,
     burada uretilemedi). Kendi zeminini ve alt kose
     yuvarlamasini tasiyinca panelin parcasi gibi kaliyor.
     `flex:0 0 auto` de ayri bir koruma: esnek sutunda alt bar
     asla ezilmesin, once govde kucultulsun. */
  .modal-alt{padding:14px 22px 20px;display:flex;gap:10px;justify-content:flex-end;border-top:1px solid var(--cizgi);background:var(--yuzey);border-radius:0 0 14px 14px;flex:0 0 auto}
'''),
    ('tests/test_kritik.py', 'MA4 · tests/test_kritik.py blok 1',
     r'''    assert "['fAlanUretici', 'fAlanCins', 'fAlanBlok']" in tam
''',
     r'''    assert "['fAlanUretici', 'fAlanCins', 'fAlanBlok']" in tam


def test_ma4_alt_bar_kendi_zeminini_tasiyor():
    """MA4: alt bar (Vazgeç/Kaydet) `.modal`in beyaz zemini üzerinde
    duruyordu — zemini kendisinin değil, kapsayıcısınındı. Gövde bir
    şekilde kapsayıcıyı aşınca alt bar ZEMİNSİZ kalıyor ve panelden
    kopmuş görünüyor. Kendi zeminini ve alt köşe yuvarlamasını
    taşıyınca, dizilim ne olursa olsun panelin parçası kalıyor.

    `flex:0 0 auto` ayrı bir koruma: esnek sütunda alt bar asla
    ezilmesin, önce gövde küçültülsün."""
    import glob
    import io as _io
    import re
    eksik = []
    for yol in sorted(glob.glob('templates/*.html')):
        g = _io.open(yol, encoding='utf-8').read()
        for k in re.findall(r'\.modal-alt\{[^}]*\}', g):
            if ('background:' not in k or 'border-radius:0 0' not in k
                    or 'flex:0 0 auto' not in k):
                eksik.append((yol, k[:70]))
    assert not eksik, f'alt bar zeminsiz kalabilir: {eksik}'
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA MA4 — ALT BAR PANELIN ICINDE KALSIN')
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
        print('    python3 yama_ma4.py            # rapor')
        print('    python3 yama_ma4.py --uygula')
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
        print('  ⊙ Yama MA4 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_ma4.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_ma4'
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
    print('    Herhangi bir modal ac. Vazgec/Kaydet barinin zemini')
    print('    artik kendisine ait: panelin alt kosesine kadar')
    print('    iniyor, dizilim ne olursa olsun kopuk gorunmuyor.')
    print()
    print('  HALA BOZUKSA: yamanin sonundaki TESHIS satirini')
    print('  konsola yapistir, ciktiyi gonder.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

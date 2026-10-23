#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MA3 — TAŞMANIN SEBEBİ VE FORMUN YENİ DÜZENİ
=================================================

ÖNKOŞUL: yama_ma2.py uygulanmış olmalı.

Haklıymışsın, taşma gerçekmiş. Sebebini buldum ve bu yalnız
maliyet formunun meselesi değilmiş.

── TAŞMANIN SEBEBİ: TEK BİR EKSİK SATIR ──
  `.modal` esnek bir sütun (`display:flex;flex-direction:column`)
  ve `max-height:92vh` ile sınırlı. Gövdesi (`.modal-gov`) o
  sütunun çocuğu ve `overflow-y:auto` taşıyor.

  Ama CSS'te bir esnek kutu çocuğunun varsayılanı
  `min-height:auto` — yani çocuk KENDİ İÇERİĞİNDEN kısa olamaz.
  Bu yüzden `overflow-y:auto` hiç devreye girmiyor: gövde
  büyüyor, büyüyor ve ALT BAR'ı (Vazgeç/Kaydet) modalın dışına
  itiyor. Senin ekran görüntündeki tam olarak bu.

  Chromium bunu bazı durumlarda affediyor — bende o yüzden
  üretemedim, yedi ekran boyunda taşma görmedim. Firefox
  affetmiyor. Pardus'ta Firefox kullanıyorsan açıklaması bu.

  Doğrusu açıkça yazmak: `flex:1 1 auto;min-height:0`.

── VE BU HATA ON ÜÇ SAYFADA DURUYORDU ──
  `.modal-gov` kuralı base.html'de bir kez tanımlı, ama 14 sayfa
  onu KENDİ içinde yeniden yazmış. Sayfanın kuralı sonra geldiği
  için base'inkini EZİYOR — yani base.html'i düzeltmek tek başına
  hiçbirini kurtarmıyordu.

  Dokunduğum sayfalar: base · maliyet · stok · ayarlar · cari ·
  cek · kdv_iade · kesim · musteri · nakit · proforma ·
  sabit_gider · sevkiyat · siparis

  Yani uzun modalı olan her yerde aynı taşma vardı; sen onu
  maliyet formunda gördün çünkü en uzun modal o.

  TEST BUNU KORUYOR: yeni bir sayfa kuralı kopyalayıp bu parçayı
  unutursa test düşer, adını da yazar.

── SENİN İSTEDİĞİN DÜZEN ──
  Süzgeçler tek bir esnek satırdaydı ve 620px'lik modalda DÖRT
  kutu sığmayıp alt satıra sarıyordu. Şimdi iki üçlü satır:

      MALİYET TİPİ   | BAĞLANTI TİPİ | ÜRETİCİ
      BAĞLANACAK STOK| CİNS          | BLOK NO

  Seçici bloğu 307 → 201 px, gövde 687 → 649 px.

  Yan kazanç: her kutunun artık bir ETİKETİ var. Önce ne
  oldukları yalnız "— üretici (tümü) —" gibi seçenek
  metinlerinden anlaşılıyordu.

── BİR ŞEY DAHA EKLEDİM ──
  Üretici / Cins / Blok No yalnız STOK için anlamlı. Seçici
  bloğunun içindeyken boş durmaları göze batmıyordu; artık üst
  satırlarda oldukları için Sipariş veya Sevkiyat seçince üç BOŞ
  kutu formun başında duracaktı. O durumda gizleniyorlar.

── ÖLÇÜLDÜ ──
  13 sayfa, 73 modal tarandı: hepsinde gövde küçülebiliyor,
  alt bar taşması 0 px, JS hatası yok.

      maliyet modalı, 900px ekran : gövde 649/649  taşma 0
                       800px      : gövde 603/649  taşma 0
                       700px      : gövde 511/649  taşma 0
                       600px      : gövde 419/649  taşma 0

  169 test geçti (167 + 2 yeni kalıcı test);
  firma · js · form · zincir · akis · degismezlik temiz.
  `min-height:0`'ı geri alıp testin DÜŞTÜĞÜNÜ gördüm.

── DOKUNMADIĞIM İKİ SAYFA ──
  fatura.html ve kasa.html'in modalı başka kalıpta: `max-height`
  de yok, esnek sütun da değil. Orada modal içerik kadar uzuyor
  ve ekrandan taşarsa kaydırılamıyor — ayrı ve daha büyük bir
  iş. Bu yamanın işi değil, körlemesine dokunmadım.

DOSYALAR
--------
  templates/base.html          modal gövdesi küçülebiliyor
  templates/maliyet.html       iki üçlü satır · süzgeç gizleme · aynısı
  templates/stok.html          aynısı
  + ayarlar · cari · cek · kdv_iade · kesim · musteri · nakit ·
    proforma · sabit_gider · sevkiyat · siparis   (aynı tek satır)
  tests/test_kritik.py         2 yeni test

Şema yok, göç yok, sunucu tarafı değişmedi.

KULLANIM
--------
  python3 yama_ma3.py            # RAPOR
  python3 yama_ma3.py --uygula
  sudo systemctl restart milestone-erp
  (tarayıcıda Ctrl+F5 — CSS değişti, önbellek yanıltmasın)
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

# İMZA, DEĞİŞİKLİĞE ÖZEL OLMALI. Önce yalnız 'min-height:0' yazmıştım;
# ayarlar.html'de bambaşka bir kuralda (bir düğmenin konumlandırması)
# o metin zaten geçiyordu ve yama "uygulanmış" sanıp yarım duruma
# düştü — koruma yakaladı. MA3 yorumu dosyada tek.
_MH = 'MA3: `min-height:0`'
DOSYA_IMZA = {
    'templates/base.html': _MH,
    'templates/maliyet.html': 'id="fAlanUretici"',
    'templates/stok.html': _MH,
    'templates/ayarlar.html': _MH,
    'templates/cari.html': _MH,
    'templates/cek.html': _MH,
    'templates/kdv_iade.html': _MH,
    'templates/kesim.html': _MH,
    'templates/musteri.html': _MH,
    'templates/nakit.html': _MH,
    'templates/proforma.html': _MH,
    'templates/sabit_gider.html': _MH,
    'templates/sevkiyat.html': _MH,
    'templates/siparis.html': _MH,
    'tests/test_kritik.py': 'def test_ma3_modal_govdesi_esnek_kutuda_kuculebiliyor',
}
_MG = '.modal-gov{'
ONKOSUL = {
    'templates/base.html': _MG,
    'templates/maliyet.html': '<input id="fAciklama" maxlength="500"',
    'templates/stok.html': '<input id="malAciklama" maxlength="500"',
    'templates/ayarlar.html': _MG,
    'templates/cari.html': _MG,
    'templates/cek.html': _MG,
    'templates/kdv_iade.html': _MG,
    'templates/kesim.html': _MG,
    'templates/musteri.html': _MG,
    'templates/nakit.html': _MG,
    'templates/proforma.html': _MG,
    'templates/sabit_gider.html': _MG,
    'templates/sevkiyat.html': _MG,
    'templates/siparis.html': _MG,
    'tests/test_kritik.py': 'def test_ma1_iki_formda_da_aciklama_kutusu_var',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('templates/base.html', 'MA3 · templates/base.html blok 1',
     r'''.modal-gov{padding:18px 22px;overflow-y:auto;background:var(--taban)}
''',
     r'''/* MA3: `min-height:0` OLMADAN esnek kutu cocugu kendi iceriginden
   kisa olamaz; `overflow-y:auto` devreye girmez ve uzun bir modalda
   ALT BAR disari itilir. Chromium bazi durumlarda affediyor,
   Firefox affetmiyor. Butun modallari ilgilendirir. */
.modal-gov{padding:18px 22px;overflow-y:auto;flex:1 1 auto;min-height:0;background:var(--taban)}
'''),
    ('templates/maliyet.html', 'MA3 · templates/maliyet.html blok 1',
     r'''  .modal-gov{padding:18px 22px;overflow-y:auto}
''',
     r'''  /* MA3: `min-height:0` OLMADAN bir esnek kutu cocugu kendi
     icerigininden kisa olamaz — `overflow-y:auto` o yuzden hic
     devreye girmez, govde buyur ve ALT BAR (Vazgec/Kaydet)
     modalin disina itilir. Chromium bazi durumlarda affediyor,
     Firefox affetmiyor. Dogrusu acikca yazmak. */
  .modal-gov{padding:18px 22px;overflow-y:auto;flex:1 1 auto;min-height:0}
'''),
    ('templates/maliyet.html', 'MA3 · templates/maliyet.html blok 2',
     r'''      <div class="form-satir f2">
        <div class="form-alan"><label>Maliyet Tipi</label>
''',
     r'''      <!-- MA3 · İKİ ÜÇLÜ SATIR
           Süzgeçler eskiden tek bir esnek satırdaydı ve 620px'lik
           modalda DÖRT kutu sığmayıp alt satıra sarıyordu: seçici
           bloğu tek başına 307px tutuyor, gövdenin yarısını yiyor,
           formun son alanlarını katlamanın altına itiyordu.
           Artık iki üçlü ızgara satırı — sarma yok, iki satır
           kazanıldı ve her kutunun artık bir ETİKETİ var
           (önce ne olduklarını yalnız "— üretici (tümü) —" gibi
           seçenek metinleri söylüyordu). -->
      <div class="form-satir f3">
        <div class="form-alan"><label>Maliyet Tipi</label>
'''),
    ('templates/maliyet.html', 'MA3 · templates/maliyet.html blok 3',
     r'''      </div>

      <div class="form-alan" style="margin-bottom:10px">
        <label id="hedefBaslik">Bağlanacak kayıt</label>
        <!-- SÜZGEÇ + ÇOKLU SEÇİM (MS1).
             Binlerce stok kaydında aranan ürünü kaydırarak bulmak
             zahmetliydi. Süzgeçler listeyi daraltır; birden çok
             kayıt seçilebilir ve tutar aralarında eşit bölünür. -->
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px">
          <input id="hAra" placeholder="Ara — cins, blok no, kayıt no…"
                 oninput="hedefSuz()" style="flex:1;min-width:150px">
          <select id="hUretici" onchange="hedefSuz()" style="max-width:170px"></select>
          <select id="hCins" onchange="hedefSuz()" style="max-width:140px"></select>
          <select id="hBlok" onchange="hedefSuz()" style="max-width:130px"></select>
        </div>
''',
     r'''        <div class="form-alan" id="fAlanUretici"><label>Üretici</label>
          <select id="hUretici" onchange="hedefSuz()"></select>
        </div>
      </div>

      <!-- SÜZGEÇ + ÇOKLU SEÇİM (MS1).
           Binlerce stok kaydında aranan ürünü kaydırarak bulmak
           zahmetliydi. Süzgeçler listeyi daraltır; birden çok
           kayıt seçilebilir ve tutar aralarında eşit bölünür. -->
      <div class="form-satir f3">
        <div class="form-alan"><label id="hedefBaslik">Bağlanacak kayıt</label>
          <input id="hAra" placeholder="cins, blok no, kayıt no…"
                 oninput="hedefSuz()" data-buyuk-harf="hayir">
        </div>
        <div class="form-alan" id="fAlanCins"><label>Cins</label>
          <select id="hCins" onchange="hedefSuz()"></select>
        </div>
        <div class="form-alan" id="fAlanBlok"><label>Blok No</label>
          <select id="hBlok" onchange="hedefSuz()"></select>
        </div>
      </div>

      <div class="form-alan" style="margin-bottom:10px">
'''),
    ('templates/maliyet.html', 'MA3 · templates/maliyet.html blok 4',
     r'''  kok.innerHTML = '<div class="yukleniyor" style="padding:10px">Yükleniyor…</div>';
''',
     r'''  /* MA3: uretici/cins/blok yalniz STOK icin anlamli. Suzgecler
     eskiden secici blogunun icindeydi ve bos da olsa goze
     batmiyordu; artik ust satirlarda duruyorlar — siparis veya
     sevkiyat secilince uc BOS kutu formun basinda durmasin. */
  const stokMu = (tip === 'Stok');
  ['fAlanUretici', 'fAlanCins', 'fAlanBlok'].forEach(k => {
    const el = document.getElementById(k);
    if (el) el.style.display = stokMu ? '' : 'none';
  });
  kok.innerHTML = '<div class="yukleniyor" style="padding:10px">Yükleniyor…</div>';
'''),
    ('templates/stok.html', 'MA3 · templates/stok.html blok 1',
     r'''  .modal-gov{padding:18px 22px;overflow-y:auto}
''',
     r'''  /* MA3: `min-height:0` OLMADAN esnek kutu cocugu kendi iceriginden
     kisa olamaz; `overflow-y:auto` hic devreye girmez ve uzun bir
     modalda ALT BAR (Vazgec/Kaydet) disari itilir. Chromium bazi
     durumlarda affediyor, Firefox affetmiyor. Sayfanin kendi
     kurali base.html'inkini EZDIGI icin her sayfada ayri yaziyor. */
  .modal-gov{padding:18px 22px;overflow-y:auto;flex:1 1 auto;min-height:0}
'''),
    ('templates/ayarlar.html', 'MA3 · templates/ayarlar.html blok 1',
     r'''  .modal-gov{padding:18px 22px;overflow-y:auto}
''',
     r'''  /* MA3: `min-height:0` OLMADAN esnek kutu cocugu kendi iceriginden
     kisa olamaz; `overflow-y:auto` hic devreye girmez ve uzun bir
     modalda ALT BAR (Vazgec/Kaydet) disari itilir. Chromium bazi
     durumlarda affediyor, Firefox affetmiyor. Sayfanin kendi
     kurali base.html'inkini EZDIGI icin her sayfada ayri yaziyor. */
  .modal-gov{padding:18px 22px;overflow-y:auto;flex:1 1 auto;min-height:0}
'''),
    ('templates/cari.html', 'MA3 · templates/cari.html blok 1',
     r'''  .modal-gov{padding:18px 22px;overflow-y:auto}
''',
     r'''  /* MA3: `min-height:0` OLMADAN esnek kutu cocugu kendi iceriginden
     kisa olamaz; `overflow-y:auto` hic devreye girmez ve uzun bir
     modalda ALT BAR (Vazgec/Kaydet) disari itilir. Chromium bazi
     durumlarda affediyor, Firefox affetmiyor. Sayfanin kendi
     kurali base.html'inkini EZDIGI icin her sayfada ayri yaziyor. */
  .modal-gov{padding:18px 22px;overflow-y:auto;flex:1 1 auto;min-height:0}
'''),
    ('templates/cek.html', 'MA3 · templates/cek.html blok 1',
     r'''  .modal-gov{padding:18px 22px;overflow-y:auto}
''',
     r'''  /* MA3: `min-height:0` OLMADAN esnek kutu cocugu kendi iceriginden
     kisa olamaz; `overflow-y:auto` hic devreye girmez ve uzun bir
     modalda ALT BAR (Vazgec/Kaydet) disari itilir. Chromium bazi
     durumlarda affediyor, Firefox affetmiyor. Sayfanin kendi
     kurali base.html'inkini EZDIGI icin her sayfada ayri yaziyor. */
  .modal-gov{padding:18px 22px;overflow-y:auto;flex:1 1 auto;min-height:0}
'''),
    ('templates/kdv_iade.html', 'MA3 · templates/kdv_iade.html blok 1',
     r'''  .modal-gov{padding:18px 22px;overflow-y:auto;flex:1}
''',
     r'''  /* MA3: `min-height:0` OLMADAN esnek kutu cocugu kendi iceriginden
     kisa olamaz; `overflow-y:auto` hic devreye girmez ve uzun bir
     modalda ALT BAR (Vazgec/Kaydet) disari itilir. Chromium bazi
     durumlarda affediyor, Firefox affetmiyor. Sayfanin kendi
     kurali base.html'inkini EZDIGI icin her sayfada ayri yaziyor. */
  .modal-gov{padding:18px 22px;overflow-y:auto;flex:1;flex:1 1 auto;min-height:0}
'''),
    ('templates/kesim.html', 'MA3 · templates/kesim.html blok 1',
     r'''  .modal-gov{padding:18px 22px;overflow-y:auto}
''',
     r'''  /* MA3: `min-height:0` OLMADAN esnek kutu cocugu kendi iceriginden
     kisa olamaz; `overflow-y:auto` hic devreye girmez ve uzun bir
     modalda ALT BAR (Vazgec/Kaydet) disari itilir. Chromium bazi
     durumlarda affediyor, Firefox affetmiyor. Sayfanin kendi
     kurali base.html'inkini EZDIGI icin her sayfada ayri yaziyor. */
  .modal-gov{padding:18px 22px;overflow-y:auto;flex:1 1 auto;min-height:0}
'''),
    ('templates/musteri.html', 'MA3 · templates/musteri.html blok 1',
     r'''  .modal-gov{padding:18px 22px;overflow-y:auto}
''',
     r'''  /* MA3: `min-height:0` OLMADAN esnek kutu cocugu kendi iceriginden
     kisa olamaz; `overflow-y:auto` hic devreye girmez ve uzun bir
     modalda ALT BAR (Vazgec/Kaydet) disari itilir. Chromium bazi
     durumlarda affediyor, Firefox affetmiyor. Sayfanin kendi
     kurali base.html'inkini EZDIGI icin her sayfada ayri yaziyor. */
  .modal-gov{padding:18px 22px;overflow-y:auto;flex:1 1 auto;min-height:0}
'''),
    ('templates/nakit.html', 'MA3 · templates/nakit.html blok 1',
     r'''  .modal-gov{padding:18px 22px;overflow-y:auto}
''',
     r'''  /* MA3: `min-height:0` OLMADAN esnek kutu cocugu kendi iceriginden
     kisa olamaz; `overflow-y:auto` hic devreye girmez ve uzun bir
     modalda ALT BAR (Vazgec/Kaydet) disari itilir. Chromium bazi
     durumlarda affediyor, Firefox affetmiyor. Sayfanin kendi
     kurali base.html'inkini EZDIGI icin her sayfada ayri yaziyor. */
  .modal-gov{padding:18px 22px;overflow-y:auto;flex:1 1 auto;min-height:0}
'''),
    ('templates/proforma.html', 'MA3 · templates/proforma.html blok 1',
     r'''  .modal-gov{padding:18px 22px;overflow-y:auto}
''',
     r'''  /* MA3: `min-height:0` OLMADAN esnek kutu cocugu kendi iceriginden
     kisa olamaz; `overflow-y:auto` hic devreye girmez ve uzun bir
     modalda ALT BAR (Vazgec/Kaydet) disari itilir. Chromium bazi
     durumlarda affediyor, Firefox affetmiyor. Sayfanin kendi
     kurali base.html'inkini EZDIGI icin her sayfada ayri yaziyor. */
  .modal-gov{padding:18px 22px;overflow-y:auto;flex:1 1 auto;min-height:0}
'''),
    ('templates/sabit_gider.html', 'MA3 · templates/sabit_gider.html blok 1',
     r'''  .modal-gov{padding:18px 22px;overflow-y:auto}
''',
     r'''  /* MA3: `min-height:0` OLMADAN esnek kutu cocugu kendi iceriginden
     kisa olamaz; `overflow-y:auto` hic devreye girmez ve uzun bir
     modalda ALT BAR (Vazgec/Kaydet) disari itilir. Chromium bazi
     durumlarda affediyor, Firefox affetmiyor. Sayfanin kendi
     kurali base.html'inkini EZDIGI icin her sayfada ayri yaziyor. */
  .modal-gov{padding:18px 22px;overflow-y:auto;flex:1 1 auto;min-height:0}
'''),
    ('templates/sevkiyat.html', 'MA3 · templates/sevkiyat.html blok 1',
     r'''  .modal-gov{padding:18px 22px;overflow-y:auto}
''',
     r'''  /* MA3: `min-height:0` OLMADAN esnek kutu cocugu kendi iceriginden
     kisa olamaz; `overflow-y:auto` hic devreye girmez ve uzun bir
     modalda ALT BAR (Vazgec/Kaydet) disari itilir. Chromium bazi
     durumlarda affediyor, Firefox affetmiyor. Sayfanin kendi
     kurali base.html'inkini EZDIGI icin her sayfada ayri yaziyor. */
  .modal-gov{padding:18px 22px;overflow-y:auto;flex:1 1 auto;min-height:0}
'''),
    ('templates/siparis.html', 'MA3 · templates/siparis.html blok 1',
     r'''  .modal-gov{padding:18px 22px;overflow-y:auto}
''',
     r'''  /* MA3: `min-height:0` OLMADAN esnek kutu cocugu kendi iceriginden
     kisa olamaz; `overflow-y:auto` hic devreye girmez ve uzun bir
     modalda ALT BAR (Vazgec/Kaydet) disari itilir. Chromium bazi
     durumlarda affediyor, Firefox affetmiyor. Sayfanin kendi
     kurali base.html'inkini EZDIGI icin her sayfada ayri yaziyor. */
  .modal-gov{padding:18px 22px;overflow-y:auto;flex:1 1 auto;min-height:0}
'''),
    ('tests/test_kritik.py', 'MA3 · tests/test_kritik.py blok 1',
     r'''            dosya, 'BUYUK HARF muafiyeti dusmus — not büyük harfe döner')
''',
     r'''            dosya, 'BUYUK HARF muafiyeti dusmus — not büyük harfe döner')


def test_ma3_modal_govdesi_esnek_kutuda_kuculebiliyor():
    """MA3: `.modal` esnek sütun + `max-height`. Gövde çocuğunda
    `min-height:0` YOKSA çocuk kendi içeriğinden kısa olamaz —
    `overflow-y:auto` hiç devreye girmez ve uzun bir modalda ALT BAR
    (Vazgeç/Kaydet) modalın dışına itilir. Chromium bazı durumlarda
    affediyor, Firefox affetmiyor.

    Kural 14 sayfada ayrı ayrı KOPYALANMIŞ ve sayfanınki base'i
    eziyor — base.html'i düzeltmek tek başına hiçbirini kurtarmıyor.
    Bu yüzden test tek tek bakıyor: yeni bir sayfa kuralı kopyalayıp
    bu parçayı unutursa burada düşer."""
    import glob
    import io as _io
    import re
    eksik = []
    for yol in sorted(glob.glob('templates/*.html')):
        g = _io.open(yol, encoding='utf-8').read()
        kurallar = re.findall(r'\.modal-gov\{[^}]*\}', g)
        if not kurallar:
            continue
        # Yalnız `.modal` gerçekten esnek sütunsa kural anlamlı
        if not re.search(r'\.modal\{[^}]*flex-direction:column', g):
            continue
        for k in kurallar:
            if 'min-height:0' not in k:
                eksik.append(yol)
    assert not eksik, f'modal gövdesi küçülemiyor: {eksik}'


def test_ma3_maliyet_formu_iki_uclu_satirda():
    """MA3: süzgeçler tek esnek satırdaydı, 620px modalda dört kutu
    sarıyordu — seçici bloğu 307px tutup formun son alanlarını
    katlamanın altına itiyordu. İki üçlü ızgara satırı oldu."""
    import io as _io
    tam = _io.open('templates/maliyet.html', encoding='utf-8').read()
    # YALNIZ MODALIN İÇİ: `fTip` gibi kimlikler sayfanın üst
    # süzgecinde de geçiyor, dışarıdan arayınca yanlış yeri bulur.
    h = tam[tam.index('<div class="modal-ortu" id="modal"'):
            tam.index('{% endblock %}',
                      tam.index('<div class="modal-ortu" id="modal"'))]
    # Konum karşılaştırmasıyla ölçüyoruz: biçimlendirme değişse de
    # "hangi kutu hangi satırda" sorusu aynı kalsın.
    y = {k: h.index(f'id="{k}"') for k in
         ('fTip', 'fBagTip', 'hUretici', 'hAra', 'hCins', 'hBlok')}
    f3ler = []
    ara = 0
    while True:
        try:
            ara = h.index('<div class="form-satir f3">', ara) + 1
        except ValueError:
            break
        f3ler.append(ara - 1)
    assert len(f3ler) >= 3, f'üç f3 satırı bekleniyordu, {len(f3ler)} var'
    satir1, satir2, satir3 = f3ler[0], f3ler[1], f3ler[2]
    liste = h.index('hedef-liste')

    # 1. üçlü: Maliyet Tipi · Bağlantı Tipi · Üretici
    for k in ('fTip', 'fBagTip', 'hUretici'):
        assert satir1 < y[k] < satir2, (k, 'ilk üçlü satırda değil')
    # 2. üçlü: Bağlanacak stok (ara) · Cins · Blok No — listeden ÖNCE
    for k in ('hAra', 'hCins', 'hBlok'):
        assert satir2 < y[k] < liste, (k, 'ikinci üçlü satırda değil')
    # 3. üçlü (Tutar/Döviz/KDV) listeden SONRA gelmeli
    assert liste < satir3

    # Her kutunun artık ETİKETİ var — önce ne oldukları yalnız
    # "— üretici (tümü) —" gibi seçenek metinlerinden anlaşılıyordu
    for etiket in ('>Üretici<', '>Cins<', '>Blok No<'):
        assert etiket in h, etiket
    # Süzgeçler yalnız STOK için anlamlı: sipariş/sevkiyatta gizleniyor
    assert "['fAlanUretici', 'fAlanCins', 'fAlanBlok']" in tam
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA MA3 — MODAL TASMASI VE FORM DUZENI')
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
        print('    python3 yama_ma3.py            # rapor')
        print('    python3 yama_ma3.py --uygula')
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
        print('  ⊙ Yama MA3 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_ma3.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_ma3'
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
    print('    Ust iki satir UCER kutu olmali:')
    print('      Maliyet Tipi | Baglanti Tipi | Uretici')
    print('      Baglanacak stok | Cins | Blok No')
    print('    Pencereyi KISALT: govde kaymali, Vazgec/Kaydet')
    print('    her zaman modalin icinde kalmali. Tasma buydu.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

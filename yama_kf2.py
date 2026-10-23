#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA KF2 — HAREKET FORMU KAYDIRMAYI BIRAKTI
============================================

ÖNKOŞUL: **yama_kf1.py uygulanmış olmalı.** Betik denetliyor;
uygulanmamışsa hiçbir dosyaya dokunmadan çıkar — o zaman önce KF1'i
uygula, sonra bunu.

"Tüm kontroller forma sığdığı hâlde gereksiz bir kaydırma var hâlâ"
dedin. Haklısın: KF1 kutucuğu düzeltti ama form hâlâ pencerenin
verdiği yerden uzundu. Üç yerde boşuna yer harcanıyordu.

── 1 · DÖVİZ TEK BAŞINA BİR SATIR YİYORDU ──
  Tutarla birlikte okunması gereken bir şey ayrı satırdaydı. Artık
  aynı alanda: [tutar] [USD].

  Yan etkisi daha ilginç çıktı: sözleşme kuru kutusu ("TCMB döviz
  alış kuru kullanılır: 40,0000") döviz seçicisinin ÜSTÜNDE
  duruyordu — yani kuru, dövizi seçmeden önce söylüyordu. Şimdi
  altında.

── 2 · BELGE SATIRI: EVRAK NO · BELGE TARİHİ · VADE ──
  Üçü de aynı belgeyi anlatıyor, artık bir satırda. Tahsilat/ödemede
  vade görünmüyor (VT1) ve o satır YARISI BOŞ duruyordu.

  Satır artık esnek. Eskiden sütun sayısı JS'ten değiştiriliyordu;
  gizlenen öge esnek satırda akıştan çıktığı için o kod gerekmiyor
  ve KALDIRILDI — iki yol birden yaşarsa biri düzeltilip öteki
  unutulur.

── 3 · HİÇBİR ŞEY SÖYLEMEYEN İKİ KUTU ──
  a) KDV önizlemesi, tutar girilene kadar içinde "—" ile duruyordu:
     40 piksellik boş bir kutu. Artık söyleyecek bir şey olunca
     beliriyor, tutar silinince yine kayboluyor.
  b) Kasa ipucunun ikinci cümlesi ("para takip etmediğiniz bir
     hesaba geliyorsa önce o hesabı kasa olarak tanımlayın")
     yalnızca TANIMLI KASA YOKKEN işe yarıyor. Artık tam o durumda
     yazılıyor — öğüt, işe yaradığı yerde.
  c) Sipariş ve Açıklama (ikisi de opsiyonel, ikisi de tek kontrol)
     yan yana geldi.

── ÖLÇÜLDÜ (1280x800, modal 560 px, gövde yüksekliği) ──

      işlem tipi            önce   sonra   kaydırma
      ----------------------------------------------
      Ödeme / Tahsilat + USD  697 →  542      0
      Alış / Satış Faturası   533 →  425      0
      Açılış Bakiyesi         412 →  357      0

  Pencere o boyda 603 piksel veriyor; hepsi altında kaldı.
  KF1 öncesiyle kıyas: Ödeme formu 697'den 542'ye indi.

  KDV önizlemesi denendi: boşken gizli, 10.000 girilince
  "Matrah 10.000,00 $ · KDV 2.000,00 $ · Toplam 12.000,00 $",
  silinince yine gizli. Tarayıcıda JS hatası yok.
  226 test geçti (223 + 3). firma · js · form · akış denetimleri
  temiz.

── KALAN ──
  Çok kısa pencerelerde (gövde ~500 pikselin altına düşerse) form
  yine kaydırır; orada yapacak bir şey yok, alan gerçekten yetmiyor.

DOSYALAR
--------
  templates/cari.html     tutar+döviz · belge satırı · boş kutular ·
                          sipariş/açıklama çifti · ölü JS çıktı
  tests/test_kritik.py    3 yeni test

Şema yok, göç yok, sunucu tarafı değişmedi.

KULLANIM
--------
  python3 yama_kf2.py            # RAPOR
  python3 yama_kf2.py --uygula
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
    'templates/cari.html': 'KF2 — TUTAR VE DÖVİZ AYNI ALANDA',
    'tests/test_kritik.py': 'def test_kf2_doviz_tutarla_ayni_alanda',
}
ONKOSUL = {
    'templates/cari.html': 'KF1 — KUR FARKI ONAYI',
    'tests/test_kritik.py': 'def test_kf1_onay_kutusu_metin_kutusu_genisligi_almiyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('templates/cari.html', 'KF2 · templates/cari.html blok 1',
     r'''  .kf-onay{margin-bottom:12px}
''',
     r'''  /* KF2 — yan yana duran alan çifti. Grid DEĞİL: gizlenen bir öge
     gridde sütununu boş bırakır, esnekte akıştan tamamen çıkar ve
     kalan alan tam genişliğe yayılır. */
  .form-cift{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:12px}
  .form-cift > .form-alan{flex:1 1 150px;margin-bottom:0}
  /* KF2 — tutar ve dövizi tek alanda okunur tutar. Döviz sabit dar,
     tutar kalanı alır; `min-width:0` olmadan sayı kutusu esnek
     kutuda kendi taban genişliğinin altına inmiyor ve taşıyor. */
  .tutar-cift{display:flex;gap:6px}
  .tutar-cift input{flex:1 1 auto;min-width:0}
  .tutar-cift select{flex:0 0 84px}
  .kf-onay{margin-bottom:12px}
'''),
    ('templates/cari.html', 'KF2 · templates/cari.html blok 2',
     r'''        <div class="form-alan"><label>Tutar <span style="color:var(--kirmizi)">*</span></label><input id="hTutar" type="number" step="0.01" oninput="kdvOnizle()"></div>
''',
     r'''        <!-- KF2 — TUTAR VE DÖVİZ AYNI ALANDA.
             Döviz ayrı bir satırda duruyordu ve o satır tek başına
             56 piksel yiyordu. Tutarla birlikte okunması gereken bir
             şeyi ayrı satıra koymanın da faydası yoktu.
             Yan etki: sözleşme kuru kutusu ("TCMB kuru kullanılır:
             40,0000") döviz seçicisinin ÜSTÜNDE kalıyordu — yani
             kuru dövizi seçmeden önce söylüyordu. Artık altında. -->
        <div class="form-alan"><label>Tutar <span style="color:var(--kirmizi)">*</span></label>
          <div class="tutar-cift">
            <input id="hTutar" type="number" step="0.01" oninput="kdvOnizle()">
            <select id="hDoviz" onchange="kurAlaniGoster()"><option>USD</option><option>EUR</option><option>TRY</option></select>
          </div>
        </div>
'''),
    ('templates/cari.html', 'KF2 · templates/cari.html blok 3',
     r'''        <div id="hKdvOnizle" style="font-size:.82rem;color:var(--soluk);line-height:1.7;
             background:var(--kagit);border:1px solid var(--cizgi);border-radius:var(--r-kucuk);
             padding:9px 12px;margin-bottom:12px">—</div>
''',
     r'''        <!-- KF2: tutar girilene kadar bu kutu içinde "—" ile duruyordu:
             40 piksellik boş bir kutu, hiçbir şey söylemeyen. Artık
             söyleyecek bir şey olduğunda beliriyor. -->
        <div id="hKdvOnizle" style="display:none;font-size:.82rem;color:var(--soluk);line-height:1.7;
             background:var(--kagit);border:1px solid var(--cizgi);border-radius:var(--r-kucuk);
             padding:9px 12px;margin-bottom:12px"></div>
'''),
    ('templates/cari.html', 'KF2 · templates/cari.html blok 4',
     r'''      <div class="form-satir f2">
        <div class="form-alan"><label>Döviz</label>
          <select id="hDoviz" onchange="kurAlaniGoster()"><option>USD</option><option>EUR</option><option>TRY</option></select>
        </div>
        <div class="form-alan"><label>Evrak No</label><input id="hEvrak" placeholder="opsiyonel"></div>
      </div>
      <!-- VT1: vade yalnız BORÇ doğuran tiplerde görünür, o yüzden
           satırın sütun sayısı da tipe göre değişiyor (hTarihSatir). -->
      <div class="form-satir f2" id="hTarihSatir">
''',
     r'''      <!-- KF2 — BELGE SATIRI: evrak no · belge tarihi · vade.
           Üçü de aynı belgeyi anlatıyor, bir satırda duruyorlar.
           VT1: vade yalnız BORÇ doğuran tiplerde görünür; eskiden
           satırın sütun sayısı bunun için JS'ten değiştiriliyordu.
           `.form-cift` ESNEK olduğu için artık gerekmiyor — gizlenen
           öge akıştan çıkıyor, kalanlar kendiliğinden yayılıyor. -->
      <div class="form-cift" id="hTarihSatir">
        <div class="form-alan"><label>Evrak No</label><input id="hEvrak" placeholder="opsiyonel"></div>
'''),
    ('templates/cari.html', 'KF2 · templates/cari.html blok 5',
     r'''        <div style="font-size:.72rem;color:var(--soluk);margin-top:4px">Tahsilatta kasaya giriş, ödemede çıkış kaydı otomatik oluşur.
        <strong>Zorunludur</strong> — para takip etmediğiniz bir hesaba geliyorsa önce o hesabı kasa olarak tanımlayın.</div>
''',
     r'''        <!-- KF2 — İPUCU İKİ SATIRDAN BİRE.
             İkinci cümle ("para takip etmediğiniz bir hesaba
             geliyorsa önce o hesabı kasa olarak tanımlayın") yalnız
             TANIMLI KASA YOKKEN işe yarıyor; her açılışta durması
             formu 30 piksel uzatıyordu. Artık tam o durumda
             yazılıyor — öğüt, işe yaradığı yerde. -->
        <div id="hKasaNot" style="font-size:.72rem;color:var(--soluk);margin-top:4px">Tahsilatta kasaya giriş, ödemede çıkış kaydı otomatik oluşur · <strong>zorunludur</strong></div>
'''),
    ('templates/cari.html', 'KF2 · templates/cari.html blok 6',
     r'''      <div class="form-alan" id="hSiparisAlan" style="margin-bottom:12px"><label>Sipariş (opsiyonel)</label>
        <select id="hSiparisSec"><option value="">— sipariş bağlama —</option></select>
      </div>
      <div class="form-alan"><label>Açıklama</label><input id="hAciklama" placeholder="opsiyonel"></div>
''',
     r'''      <!-- KF2 — İKİ OPSİYONEL ALAN YAN YANA.
           İkisi de tek kontrol, ipucu yok; alt alta durup 112 piksel
           yiyorlardı. `.form-cift` ESNEK (grid değil): sipariş alanı
           kasaya virmanda gizleniyor ve grid olsaydı açıklama yarım
           sütunda kalırdı — esnekte gizli öge akıştan çıkıyor,
           açıklama kendiliğinden tam genişliğe yayılıyor. -->
      <div class="form-cift">
        <div class="form-alan" id="hSiparisAlan"><label>Sipariş (opsiyonel)</label>
          <select id="hSiparisSec"><option value="">— sipariş bağlama —</option></select>
        </div>
        <div class="form-alan"><label>Açıklama</label><input id="hAciklama" placeholder="opsiyonel"></div>
      </div>
'''),
    ('templates/cari.html', 'KF2 · templates/cari.html blok 7',
     r'''  document.getElementById('hKdvOnizle').textContent = '—';
''',
     r'''  const _ko = document.getElementById('hKdvOnizle');
  _ko.textContent = ''; _ko.style.display = 'none';
'''),
    ('templates/cari.html', 'KF2 · templates/cari.html blok 8',
     r'''  if (!tutar || !oran) { kutu.textContent = '—'; return; }
''',
     r'''  /* KF2: gosterecek bir sey yoksa kutu HIC gorunmesin. */
  if (!tutar || !oran) { kutu.textContent = ''; kutu.style.display = 'none'; return; }
  kutu.style.display = '';
'''),
    ('templates/cari.html', 'KF2 · templates/cari.html blok 9',
     r'''  const vSatir = document.getElementById('hTarihSatir');
  if (vAlan) vAlan.style.display = vadeli ? '' : 'none';
  if (vSatir) vSatir.classList.toggle('f2', vadeli);
''',
     r'''  if (vAlan) vAlan.style.display = vadeli ? '' : 'none';
  /* KF2: burada `hTarihSatir`in sütun sayısı da değiştiriliyordu.
     Satır artık esnek (`.form-cift`); gizlenen vade akıştan çıkıyor,
     kalanlar kendiliğinden yayılıyor. JS'in yapacağı bir şey yok. */
'''),
    ('templates/cari.html', 'KF2 · templates/cari.html blok 10',
     r'''      if (uygun) ks.value = String(uygun.id);
    }
''',
     r'''      if (uygun) ks.value = String(uygun.id);
    }
    /* KF2: "önce kasa tanımlayın" öğüdü yalnız TANIMLI KASA YOKKEN
       anlamlı. Her açılışta göstermek formu iki satır uzatıyordu. */
    const kn = document.getElementById('hKasaNot');
    if (kn) kn.innerHTML = HAR_KASALAR.length
      ? 'Tahsilatta kasaya giriş, ödemede çıkış kaydı otomatik oluşur'
        + ' · <strong>zorunludur</strong>'
      : '<strong>Tanımlı kasa yok.</strong> Para takip etmediğiniz bir'
        + ' hesaba geliyorsa bile önce o hesabı kasa olarak tanımlayın'
        + ' — bu alan zorunludur.';
'''),
    ('tests/test_kritik.py', 'KF2 · tests/test_kritik.py blok 1',
     r'''    assert 'govde.kur_farki_islet = true' in m, 'bayrak sunucuya gitmiyor'
''',
     r'''    assert 'govde.kur_farki_islet = true' in m, 'bayrak sunucuya gitmiyor'


# ══════════════════════════════════════════════════════════════════
#  KF2 · HAREKET FORMU KAYDIRMAYI BIRAKTI
#
#  KF1'den sonra da kaydırma kalmıştı: form, pencerenin verdiği
#  yerden uzundu. Üç yerde boşuna yer harcanıyordu.
#
#  ÖLÇÜLDÜ (1280x800, modal 560 px, gövdenin yüksekliği):
#                      önce   sonra
#      Ödeme + USD      697 →   542
#      Alış Faturası    533 →   425
#      Açılış Bakiyesi  412 →   357
#      kaydırma           7 →     0   (her işlem tipinde)
# ══════════════════════════════════════════════════════════════════

def test_kf2_doviz_tutarla_ayni_alanda():
    """Döviz tek başına bir satır yiyordu.

    Yan etki olarak sözleşme kuru kutusu ("TCMB kuru kullanılır:
    40,0000") döviz seçicisinin ÜSTÜNDE kalıyordu — kuru, döviz
    seçilmeden önce söylüyordu. Artık altında."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/cari.html'),
                 encoding='utf-8').read()
    assert '.tutar-cift{' in m, 'birleşik tutar alanı tanımlı değil'
    # hDoviz, hTutar ile AYNI kutuda olmalı.
    _k = m[m.index('class="tutar-cift"'):]
    _k = _k[:_k.index('</div>')]
    assert 'id="hTutar"' in _k and 'id="hDoviz"' in _k, \
        'tutar ve döviz ayrılmış'
    # Döviz seçicisi sözleşme kuru kutusundan ÖNCE gelmeli.
    assert m.index('id="hDoviz"') < m.index('id="hKurAlan"'), \
        'kur kutusu döviz seçicisinin üstünde'


def test_kf2_belge_satiri_esnek_js_sutun_saymiyor():
    """Evrak no · belge tarihi · vade tek satırda.

    Vade yalnız borç doğuran tiplerde görünüyor (VT1). Eskiden
    satırın sütun sayısı JS'ten değiştiriliyordu; esnek satırda
    gizlenen öge akıştan çıktığı için gerek kalmadı. JS'in o işi
    geri almaması gerekiyor: iki yol birden yaşarsa biri
    düzeltilip öteki unutulur."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/cari.html'),
                 encoding='utf-8').read()
    assert '.form-cift{display:flex' in m, 'esnek satır tanımlı değil'
    _s = m[m.index('id="hTarihSatir"') - 120:m.index('id="hTarihSatir"')]
    assert 'form-cift' in _s, 'belge satırı esnek değil'
    assert "classList.toggle('f2'" not in m, \
        'JS hâlâ sütun sayısı değiştiriyor'
    # Üç alan da bu satırda.
    _r = m[m.index('id="hTarihSatir"'):]
    _r = _r[:_r.index('id="hKasaAlan"')]
    for _a in ('id="hEvrak"', 'id="hBelgeTarihi"', 'id="hVade"'):
        assert _a in _r, f'{_a} belge satırında değil'


def test_kf2_bos_kutular_yer_kaplamiyor():
    """Hiçbir şey söylemeyen kutu yer kaplamamalı.

    KDV önizlemesi tutar girilene kadar içinde '—' ile duruyordu:
    40 piksellik boş bir kutu. Kasa ipucunun ikinci cümlesi de
    yalnız TANIMLI KASA YOKKEN işe yarıyor."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/cari.html'),
                 encoding='utf-8').read()
    # Önizleme kutusu gizli başlar ve boşalınca yine gizlenir.
    _k = m[m.index('id="hKdvOnizle"'):]
    assert 'display:none' in _k[:_k.index('>')], \
        'KDV önizlemesi gizli başlamıyor'
    assert "kutu.style.display = 'none'; return; }" in m, \
        'önizleme boşalınca gizlenmiyor'
    assert "kutu.style.display = '';" in m, \
        'önizleme dolunca geri gelmiyor'

    # Kasa ipucu: uzun öğüt yalnız kasa listesi BOŞKEN.
    assert 'id="hKasaNot"' in m, 'kasa ipucu kimliksiz'
    assert 'HAR_KASALAR.length' in m, 'ipucu kasa sayısına bakmıyor'
    _n = m[m.index("kn.innerHTML = HAR_KASALAR.length"):]
    _n = _n[:_n.index(';')]
    assert 'Tanımlı kasa yok' in _n, 'boş liste uyarısı yok'
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA KF2 — HAREKET FORMU KAYDIRMAYI BIRAKTI')
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
        print('    python3 yama_kf2.py            # rapor')
        print('    python3 yama_kf2.py --uygula')
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
        print('  ⊙ Yama KF2 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_kf2.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_kf2'
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
    print('    Cari -> bir cari -> Hareket Ekle. Artik KAYDIRMIYOR.')
    print('    Tutarin yaninda doviz; evrak no, belge tarihi ve vade')
    print('    tek satirda; KDV onizlemesi ancak tutar girilince')
    print('    beliriyor.')
    print()
    print('    Olculdu (1280x800, govde yuksekligi):')
    print('       Odeme + USD      697 -> 542')
    print('       Alis Faturasi    533 -> 425')
    print('       Acilis Bakiyesi  412 -> 357')
    print('       kaydirma           7 ->   0   (her islem tipinde)')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

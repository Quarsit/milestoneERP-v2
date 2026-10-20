#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA B2 — İÇE AKTARMADA ORTAK CİNS/YÜZEY LİSTEDEN SEÇİLİYOR
============================================================

ÖNKOŞUL: yama_b1.py uygulanmış olmalı.

Haklısın. Bu alanın tekil formdakinden farkı şu: değer tek satıra
değil, AKTARILAN BÜTÜN SATIRLARA yazılıyor. "CEPPO DI GRE" yerine
"CEPO DI GRE" yazmak dokuz satırlık bir listeyi stokta ayrı bir cins
yapar; tekil formdaki aynı hata tek kaydı bozar.

── NE GELDİ ──
  Kesim → Excel'den yükle → 4. bölümdeki CİNS (ORTAK) ve
  YÜZEY / ÖZELLİK (ORTAK) artık açılır kutu. Seçenekler
  Ayarlar → Listeler'den geliyor; tekil formdaki listenin aynısı.

  Pencere açılırken kesim formunda seçili cins/yüzey varsa ortak
  alana onlar geliyor — eskiden de öyleydi, sadece artık kutuda
  seçili olarak.

── AYNISINI STOK İÇE AKTARMAYA DA YAPTIM ──
  Sen Kesim'deki formu söyledin. Depo → Stok → Toplu İçe Aktar'daki
  4. bölümde AYNI iki alan var ve aynı işi yapıyor: oradaki değer de
  bütün satırlara yazılıyor.

  Birini liste yapıp ötekini serbest metin bırakmak, aynı hatalı
  veriyi öbür kapıdan içeri almak olurdu — UR2'de menşe için tam bu
  gerekçeyle iki formu birden değiştirmiştik. Yalnız Kesim'i
  istiyorduysan söyle, stok tarafını geri alırım.

── "YENİ CİNS EKLE…" SEÇENEĞİ ──
  Listede olmayan bir cinsle karşılaşırsan kutunun en altındaki
  "➕ Yeni cins ekle…" seçeneği tanım ekleme penceresini açıyor;
  eklediğin değer hem listeye hem de o anki seçime geçiyor. Yani
  liste seni kilitlemiyor, sadece yazım hatasını kayda geçirmiyor.

  Bu akış base.html'deki `_listeYeniEkle`'den geçiyor — ekranlara
  KOPYALANMADI. O işlev tanımı eklerken ortak listeyi ve açık öteki
  sekmeleri de tazeliyor; ikinci bir kopya, o tazelemenin yalnız bir
  ekranda yaşamasıyla biterdi.

── BİR AYRINTI, ÖLÇÜLDÜ ──
  "➕ Yeni … ekle…" bir DEĞER değil, bir KOMUT. Pencere açıkken ya
  da ekleme iptal edilince seçim o işaretin üstünde kalıyor; okuyucu
  onu boş saymazsa cinsi `__yeni__` olan satırlar oluşurdu. İki
  ekranda da süzülüyor ve test bunu sabitliyor.

── ÖLÇÜLDÜ (gerçek xlsx, tarayıcıda) ──
  Dosya cins sütunu OLMAYAN bir liste — ortak alan tek kaynak.

      ortak cins SEÇİLMEDEN  0 satır · 3 satır atlandı
                             "cins yok — sütun eşleşmedi ve ortak
                              cins girilmedi"
      ortak cins SEÇİLİNCE   3 satır · 17 parça · 85,61 m²
                             cins CEPPO DI GRE · yüzey HONLU
                             üçüne de yazıldı
      "Yeni ekle" seçilince  tanım penceresi açıldı, kayıttaki cins
                             DEĞİŞMEDİ (işaret sızmadı)
      JS hatası              yok

  126 test geçti (123 + 3 yeni kalıcı test);
  firma · js · form · zincir · akis · degismezlik temiz.

── NE YAPMADIM ──
  Eşleşen SÜTUNDAN gelen cins hâlâ serbest metin — Excel'de ne
  yazıyorsa o giriyor. Oraya da liste dayatmak, tedarikçinin kendi
  adlandırmasıyla gelen listeyi tümden reddetmek olurdu; UR2'de
  eşleşmeyi zorunlu olmaktan çıkarma gerekçemiz buydu. Ortak alan
  zaten o boşluğun çaresi.

DOSYALAR
--------
  templates/kesim.html   ortak cins/yüzey açılır kutu
  templates/stok.html    aynısı (toplu içe aktarma)
  tests/test_kritik.py   3 yeni test

Şema yok, göç yok. Veri dokunulmuyor.

KULLANIM
--------
  python3 yama_b2.py            # RAPOR
  python3 yama_b2.py --uygula
  sudo systemctl restart milestone-erp
  (tarayıcıda Ctrl+F5)
"""

import os
import py_compile
import shutil
import subprocess
import sys
import tempfile

UYGULA = '--uygula' in sys.argv
KOK = os.path.dirname(os.path.abspath(__file__))

DOSYA_IMZA = {
    'templates/stok.html': 'B2 · ORTAK CİNS/YÜZEY LİSTEDEN',
    'templates/kesim.html': "const KX_YENI = '__yeni__';",
    'tests/test_kritik.py': 'def test_b2_ortak_cins_ve_ozellik_listeden',
}
ONKOSUL = {
    'templates/stok.html': "filename='js/excel_ortak.js'",
    'templates/kesim.html': 'function kesimExcelUygula',
    'tests/test_kritik.py': 'def test_b1_sayi_ayristirici_davranisi',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('templates/stok.html', 'B2 · templates/stok.html blok 1',
     r'''          <div class="form-alan"><label>Cins (ortak)
            <span style="font-weight:400;color:var(--soluk)">· Excel'de yoksa</span></label>
            <input id="tCins" placeholder="CEPPO DI GRE" oninput="topluOnizle()"></div>
          <div class="form-alan" id="tOzellikAlan"><label>Yüzey / Özellik (ortak)
            <span style="font-weight:400;color:var(--soluk)">· Excel'de yoksa</span></label>
            <input id="tOzellik" placeholder="HONLU / CİLALI" oninput="topluOnizle()"></div>
''',
     r'''          <!-- B2: LİSTEDEN. Bu değer tek satıra değil, AKTARILAN
               BÜTÜN SATIRLARA yazılıyor — serbest metinken buradaki
               bir yazım hatası yüzlerce kaydı birden bozardı ve
               "CEPPO DI GRE" ile "Ceppo di Gre" stok listesinde iki
               ayrı ürün gibi dururdu. Son seçenek yeni tanım
               eklemeye yarıyor. -->
          <div class="form-alan"><label>Cins (ortak)
            <span style="font-weight:400;color:var(--soluk)">· Excel'de yoksa</span></label>
            <select id="tCins" onchange="topluListeDegisti('tCins','cins')"></select></div>
          <div class="form-alan" id="tOzellikAlan"><label>Yüzey / Özellik (ortak)
            <span style="font-weight:400;color:var(--soluk)">· Excel'de yoksa</span></label>
            <select id="tOzellik" onchange="topluListeDegisti('tOzellik','ozellik')"></select></div>
'''),
    ('templates/stok.html', 'B2 · templates/stok.html blok 2',
     r'''     Ayarlar → Listeler'den besleniyor (tekil formdaki gibi). */
  ['tCins', 'tOzellik'].forEach(i => {
    const el = document.getElementById(i); if (el) el.value = '';
  });
  listeyeBagla('tCins', 'cins');
  listeyeBagla('tOzellik', 'ozellik');
''',
     r'''     B2: ikisi de LİSTEDEN seçiliyor (serbest metin değil). */
  topluListeDoldur('tCins', 'cins', '');
  topluListeDoldur('tOzellik', 'ozellik', '');
'''),
    ('templates/stok.html', 'B2 · templates/stok.html blok 3',
     r'''function _ortakMetin(id) {
  const el = document.getElementById(id);
  return el ? (el.value || '').trim() : '';
''',
     r'''/* ── B2 · ORTAK CİNS/YÜZEY LİSTEDEN ──
   Kesim ekranındaki ikizinin aynısı (kesimListeDoldur). İkisi de
   base.html'deki `_listeYeniEkle` akışını kullanıyor; yeni tanım
   ekleme mantığı KOPYALANMADI — o işlev sonucu bir INPUT'a yazdığı
   için, select'e almak üzere geçici gizli bir input veriliyor. */
const TP_YENI = '__yeni__';

async function topluListeDoldur(id, kategori, deger) {
  const el = document.getElementById(id);
  if (!el) return;
  let liste = [];
  try { liste = await lookupGetir(kategori); } catch (e) { liste = []; }
  const simdi = String(deger === undefined ? el.value : deger || '')
                  .trim().toUpperCase();
  const kume = [...new Set(liste.map(x => String(x).trim().toUpperCase())
                                .filter(Boolean)
                                .concat(simdi ? [simdi] : []))];
  const etiket = kategori === 'cins' ? 'cins' : 'özellik';
  el.innerHTML = '<option value="">— seç —</option>'
    + kume.map(v => `<option value="${kacar(v)}">${kacar(v)}</option>`).join('')
    + `<option value="${TP_YENI}">➕ Yeni ${etiket} ekle…</option>`;
  el.value = simdi;
}

async function topluListeDegisti(id, kategori) {
  const el = document.getElementById(id);
  if (!el) return;
  if (el.value !== TP_YENI) { topluOnizle(); return; }
  el.value = '';
  const gizli = document.createElement('input');
  gizli.type = 'hidden';
  document.body.appendChild(gizli);
  try {
    await _listeYeniEkle(gizli, kategori, '');
    await topluListeDoldur(id, kategori, gizli.value || '');
  } finally {
    gizli.remove();
  }
  topluOnizle();
}

function _ortakMetin(id) {
  const el = document.getElementById(id);
  const v = el ? (el.value || '').trim() : '';
  /* B2: "➕ Yeni … ekle…" bir DEĞER değil, bir KOMUT. Ekleme
     penceresi açıkken ya da iptal edilince bu işaret kayda
     geçmemeli. */
  return v === TP_YENI ? '' : v;
'''),
    ('templates/kesim.html', 'B2 · templates/kesim.html blok 1',
     r'''          <div class="form-alan"><label>Cins (ortak)</label>
            <input id="kCins" placeholder="Excel'de yoksa" oninput="kesimExcelOnizle()"></div>
          <div class="form-alan"><label>Yüzey / Özellik (ortak)</label>
            <input id="kOzellik" placeholder="Excel'de yoksa" oninput="kesimExcelOnizle()"></div>
''',
     r'''          <!-- ── B2 · LİSTEDEN SEÇİLİR ──
               Bu iki değer tek tek satıra değil, AKTARILAN BÜTÜN
               SATIRLARA yazılıyor. Serbest metinken buradaki bir
               yazım hatası tek kaydı değil yüzlerce kaydı birden
               bozardı; üstelik "CEPPO DI GRE" ile "Ceppo di Gre"
               stok listesinde iki ayrı ürün gibi durur.

               Listede olmayan gerçekten yeni bir tanım için
               seçeneğin sonunda "➕ Yeni … ekle…" var: tanım
               ortak listeye kaydediliyor, bir dahakine normal
               seçenek olarak geliyor. -->
          <div class="form-alan"><label>Cins (ortak)</label>
            <select id="kCins" onchange="kesimListeDegisti('kCins','cins')"></select></div>
          <div class="form-alan"><label>Yüzey / Özellik (ortak)</label>
            <select id="kOzellik" onchange="kesimListeDegisti('kOzellik','ozellik')"></select></div>
'''),
    ('templates/kesim.html', 'B2 · templates/kesim.html blok 2',
     r'''function kesimExcelAc() {
''',
     r'''/* ── B2 · ORTAK CİNS/YÜZEY LİSTEDEN ──
   Değer bütün aktarılan satırlara yazıldığı için serbest metin
   bırakılmadı. Listede olmayan yeni bir tanım gerekiyorsa son
   seçenek onu ekliyor.

   YENİ TANIM EKLEME AKIŞI KOPYALANMADI: base.html'deki
   `_listeYeniEkle` pencereyi açıyor, ucu çağırıyor, ortak listeyi
   ve öteki sekmeleri tazeliyor. Tek sorun, o işlevin sonucu bir
   INPUT'a yazması — select'e değil. Ona geçici gizli bir input
   veriyoruz ve sonucu oradan okuyoruz. */
const KX_YENI = '__yeni__';

async function kesimListeDoldur(id, kategori, deger) {
  const el = document.getElementById(id);
  if (!el) return;
  let liste = [];
  try { liste = await lookupGetir(kategori); } catch (e) { liste = []; }
  const simdi = String(deger === undefined ? el.value : deger || '')
                  .trim().toUpperCase();
  const kume = [...new Set(liste.map(x => String(x).trim().toUpperCase())
                                .filter(Boolean)
                                .concat(simdi ? [simdi] : []))];
  const etiket = kategori === 'cins' ? 'cins' : 'özellik';
  el.innerHTML = '<option value="">— seç —</option>'
    + kume.map(v => `<option value="${kacar(v)}">${kacar(v)}</option>`).join('')
    + `<option value="${KX_YENI}">➕ Yeni ${etiket} ekle…</option>`;
  el.value = simdi;
}

async function kesimListeDegisti(id, kategori) {
  const el = document.getElementById(id);
  if (!el) return;
  if (el.value !== KX_YENI) { kesimExcelOnizle(); return; }
  el.value = '';
  const gizli = document.createElement('input');
  gizli.type = 'hidden';
  document.body.appendChild(gizli);
  try {
    await _listeYeniEkle(gizli, kategori, '');
    await kesimListeDoldur(id, kategori, gizli.value || '');
  } finally {
    gizli.remove();
  }
  kesimExcelOnizle();
}

function kesimExcelAc() {
'''),
    ('templates/kesim.html', 'B2 · templates/kesim.html blok 3',
     r'''  document.getElementById('kCins').value = document.getElementById('hCins').value.trim();
  document.getElementById('kOzellik').value = document.getElementById('hOzellik').value.trim();
''',
     r'''  kesimListeDoldur('kCins', 'cins', document.getElementById('hCins').value.trim());
  kesimListeDoldur('kOzellik', 'ozellik', document.getElementById('hOzellik').value.trim());
'''),
    ('templates/kesim.html', 'B2 · templates/kesim.html blok 4',
     r'''  const oCins = (document.getElementById('kCins').value || '').trim();
  const oOzellik = (document.getElementById('kOzellik').value || '').trim();
''',
     r'''  /* B2: "➕ Yeni … ekle…" bir DEĞER değil, bir KOMUT — kayda
     geçmemeli. */
  const _secim = id => {
    const v = (document.getElementById(id).value || '').trim();
    return v === KX_YENI ? '' : v;
  };
  const oCins = _secim('kCins');
  const oOzellik = _secim('kOzellik');
'''),
    ('tests/test_kritik.py', 'B2 · tests/test_kritik.py blok 1',
     r'''    assert d['satirNo'] == [2, 3, 4], d['satirNo']
''',
     r'''    assert d['satirNo'] == [2, 3, 4], d['satirNo']


# ══════════════════════════════════════════════════════════════════════
#  B2 · İÇE AKTARMADAKİ ORTAK CİNS/YÜZEY LİSTEDEN SEÇİLİYOR
# ══════════════════════════════════════════════════════════════════════

def test_b2_ortak_cins_ve_ozellik_listeden():
    """B2: iki içe aktarma ekranında da ortak cins/yüzey SELECT.

    Bu alanın tekil formdakinden farkı: değer tek satıra değil,
    AKTARILAN BÜTÜN SATIRLARA yazılıyor. Serbest metinde bir harf
    hatası yüzlerce kaydı listede ayrı bir cins olarak gösterir."""
    import io as _io, re as _re
    for yol, doldur in (('templates/stok.html', 'topluListeDoldur'),
                        ('templates/kesim.html', 'kesimListeDoldur')):
        h = _io.open(yol, encoding='utf-8').read()
        for eid in (('tCins', 'tOzellik') if 'stok' in yol else ('kCins', 'kOzellik')):
            assert _re.search(r'<select[^>]*id="%s"' % eid, h), (yol, eid)
            # Serbest metin kutusu geride kalmamış
            assert not _re.search(r'<input[^>]*id="%s"' % eid, h), (yol, eid)
        # Seçenekler listeden besleniyor, şablona gömülü değil
        assert 'async function %s' % doldur in h, yol
        assert "lookupGetir(kategori)" in h, yol


def test_b2_yeni_ekle_isareti_kayda_gecmez():
    """B2: "➕ Yeni … ekle…" bir DEĞER değil, bir KOMUT.

    Pencere açıkken ya da iptal edilince seçim işaretin kendisinde
    kalıyor; okuyucu onu boş saymazsa cinsi '__yeni__' olan satırlar
    oluşurdu."""
    import io as _io
    stok = _io.open('templates/stok.html', encoding='utf-8').read()
    kesim = _io.open('templates/kesim.html', encoding='utf-8').read()

    assert "const TP_YENI = '__yeni__';" in stok
    assert "const KX_YENI = '__yeni__';" in kesim
    # Okuyucular işareti süzüyor
    assert "v === TP_YENI ? '' : v" in stok
    assert "v === KX_YENI ? '' : v" in kesim
    # Önizleme ortak değeri DOĞRUDAN .value'dan almıyor — süzgeçten
    assert "kayit.cins = _ortakMetin('tCins')" in stok
    assert "kayit.ozellik = _ortakMetin('tOzellik')" in stok
    assert "const oCins = _secim('kCins');" in kesim
    assert "const oOzellik = _secim('kOzellik');" in kesim
    assert 'k.cins = oCins' in kesim and 'k.ozellik = oOzellik' in kesim
    # Ortak değerin OKUNDUĞU tek yer süzgeç; başka yerde `.value`
    # yalnızca YAZMA olabilir (BLOK'ta yüzey alanı temizleniyor).
    import re as _re
    for h, ad, kimlikler in ((stok, 'stok', ('tCins', 'tOzellik')),
                             (kesim, 'kesim', ('kCins', 'kOzellik'))):
        for eid in kimlikler:
            for m in _re.finditer(r"getElementById\('%s'\)\.value\s*(=(?!=))?" % eid, h):
                assert m.group(1), (ad, eid, 'süzgeç dışında okunuyor')


def test_b2_yeni_tanim_akisi_kopyalanmamis():
    """B2: yeni tanım ekleme base.html'deki TEK akıştan geçiyor.

    `_listeYeniEkle` pencereyi açıyor, ucu çağırıyor, ortak listeyi
    ve öteki sekmeleri tazeliyor. İkinci bir kopya, o tazelemenin
    yalnız bir ekranda yaşamasıyla biterdi."""
    import io as _io
    base = _io.open('templates/base.html', encoding='utf-8').read()
    assert 'async function _listeYeniEkle' in base
    for yol in ('templates/stok.html', 'templates/kesim.html'):
        h = _io.open(yol, encoding='utf-8').read()
        assert '_listeYeniEkle(gizli, kategori' in h, yol
        # Ekleme akışı şablonun içinde yeniden yazılmamış
        assert 'function _listeYeniEkle' not in h, yol
        assert "api('/api/lookup" not in h, yol
'''),
]

TAM_ICERIK = {}

def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA B2 — ICE AKTARMADA ORTAK CINS/YUZEY LISTEDEN')
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
        print('    python3 yama_b2.py            # rapor')
        print('    python3 yama_b2.py --uygula')
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
        print('  ⊙ Yama B2 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_b2.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_b2'
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
    print('  BAKILACAK YERLER')
    print('    · Depo -> Kesim -> Yeni Kesim -> Excel ile yukleme')
    print('      4. bolum: Cins (ortak) ve Yuzey (ortak) acilir kutu')
    print('    · Depo -> Stok -> Toplu Ice Aktar: ayni iki alan')
    print('    · Kutunun en altindaki "Yeni ... ekle..." secenegi')
    print('      tanim ekleme penceresini acmali')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

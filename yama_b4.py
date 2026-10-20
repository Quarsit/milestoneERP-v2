#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA B4 — SIFIR PLAKA NUMARASI YUTULUYORDU  (B3'ÜN DÜZELTMESİ)
================================================================

ÖNKOŞUL: yama_b3.py uygulanmış olmalı.

BU BENİM HATAM. B3'te 0'ı geçerli bir plaka numarası yaptım ama onu
ÇAĞIRAN yerlerdeki doğruluk denetimlerini süpürmedim.

── NE OLDU ──
  Ortak yardımcı (`_plaka_kodu` / `plakaKodu`) 0'ı doğru işliyordu:
  `K6461-00` döndürüyordu. Ama onu çağıran yerler şöyleydi:

      if (x.slab_no) ...        ← JS'te 0 YANLIŞ sayılır
      if s.slab_no: ...         ← Python'da da öyle
      'slab_no': p.slab_no or ''  ← 0'ı boş dizeye çeviriyor

  Yani yardımcı hiç çağrılmıyordu ve ekran `K6461` yazıyordu.
  Senin gördüğün tam olarak buydu.

  0'ı geçerli bir değer hâline getirip bu denetimleri olduğu gibi
  bırakmak, B3'ün eksik kalan yarısıydı.

── DÜZELTİLEN YERLER ──
  Sekiz nokta. Yalnız ekran değil — sıfır, veri yolunun birkaç
  yerinde daha sessizce kayboluyordu:

    stok listesi            `x.slab_no ?` kalktı; `plakaKodu`
                            zaten boş/dolu ayrımını kendi yapıyor
    stok detay çekmecesi    "Plaka No" alanı 0'da hiç çıkmıyordu
    denetim kaydı etiketi   `if s.slab_no:`
    maliyet ekranı          `if s.slab_no:`
    KESİM KAYNAK LİSTESİ    `p.slab_no or ''` — 0'lı plakayı
                            kesmek istersen listede numarasız
                            görünüyordu
    PROFORMAYA AKTARMA      `getattr(..., '') or ''` — 0'lı plaka
                            proformaya numarasız giriyordu
    PROFORMA GRUP BAŞLANGICI  `if slab_no and ...` — bir grubun en
                            küçük slab'ı 0 ise atlanıyor ve
                            başlangıç 1'e kayıyordu

  Son üçü ekranda görünmüyordu ama belgeye kadar gidiyordu; asıl
  tehlikeli olan onlardı.

  "Plaka no VAR MI" denetimi de artık ortak: `slabVar()`.

── NEDEN TESTLER YAKALAMADI ──
  B3'ün testleri `plakaKodu(blok, 0)` çağırıp `K6461-00` aldığını
  doğruluyordu — yardımcı DOĞRUYDU. Ölçülmeyen şey, onu çağıran
  kodun 0'ı yardımcıya kadar getirip getirmediğiydi.

  Yeni testler biçim kuralını değil, SIFIRIN HAYATTA KALMASINI
  ölçüyor: 0 numaralı bir plaka gerçekten kaydediliyor, sonra stok
  listesinden, kesim kaynak listesinden, global aramadan ve Excel
  dışa aktarmadan geri okunuyor. Ekran tarafı da `stokNo`'yu node
  ile gerçekten çağırıyor.

── ÖLÇÜLDÜ (gerçek kesim, tarayıcıda) ──
  Başlangıç No = 0 ile 5 plakalık kesim:

      stok listesi    K6461-00 · K6461-01 · K6461-02 · K6461-03
                      · K6461-04
      kimlikler       PLK-MS-K6461-00 … -04
      JS hatası       yok

  133 test geçti (131 + 2 yeni kalıcı test);
  firma · js · form · zincir · akis · degismezlik temiz.

── GÖÇ GEREKMİYOR ──
  Veri doğruydu; sorun okuma tarafındaydı. `goc_b3.py`'yi
  çalıştırdıysan bir şey yapmana gerek yok.

DOSYALAR
--------
  flask_app.py          5 doğruluk denetimi
  templates/base.html   slabVar() — ortak "plaka no var mı"
  templates/stok.html   liste kodu · detay çekmecesi
  tests/test_kritik.py  2 yeni test

Şema yok, göç yok. Veri dokunulmuyor.

KULLANIM
--------
  python3 yama_b4.py            # RAPOR
  python3 yama_b4.py --uygula
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
    'flask_app.py': "'slab_no': '' if p.slab_no is None else p.slab_no,",
    'templates/base.html': 'function slabVar(',
    'templates/stok.html': 'slabVar(s.slab_no)',
    'tests/test_kritik.py': 'def test_b4_sifir_slab_hicbir_yerde_yutulmuyor',
}
ONKOSUL = {
    'flask_app.py': 'def _plaka_kodu(',
    'templates/base.html': 'function plakaKodu(',
    'templates/stok.html': 'function _basNoOku(',
    'tests/test_kritik.py': 'def test_b3_plaka_kodu_tek_kaynaktan',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'B4 · flask_app.py blok 1',
     r'''                if getattr(s, 'slab_no', None):
                    return _plaka_kodu(s.blok_no, s.slab_no) or baglanti_id
''',
     r'''                if getattr(s, 'slab_no', None) is not None:
                    return _plaka_kodu(s.blok_no, s.slab_no) or baglanti_id
'''),
    ('flask_app.py', 'B4 · flask_app.py blok 2',
     r'''                    'slab_no': p.slab_no or '', 'blok_no': p.blok_no or '',
''',
     r'''                    # B4: `or ''` sıfırı siliyordu.
                    'slab_no': '' if p.slab_no is None else p.slab_no,
                    'blok_no': p.blok_no or '',
'''),
    ('flask_app.py', 'B4 · flask_app.py blok 3',
     r'''                if getattr(s, 'slab_no', None):
''',
     r'''                if getattr(s, 'slab_no', None) is not None:
'''),
    ('flask_app.py', 'B4 · flask_app.py blok 4',
     r'''            slab_no = getattr(stok, 'slab_no', '') or ''
''',
     r'''            # B4: `or ''` sıfırı siliyordu.
            _sn = getattr(stok, 'slab_no', None)
            slab_no = '' if _sn is None else _sn
'''),
    ('flask_app.py', 'B4 · flask_app.py blok 5',
     r'''                    if slab_no and str(slab_no).isdigit():
                        mevcut = g.get('slab_no')
                        if not mevcut or not str(mevcut).isdigit() or int(slab_no) < int(mevcut):
''',
     r'''                    # B4: 0 geçerli bir plaka numarası; `if slab_no`
                    # onu atlıyor ve grubun başlangıcını 1'e kaydırıyordu.
                    if slab_no is not None and str(slab_no).strip().isdigit():
                        mevcut = g.get('slab_no')
                        if (mevcut is None or str(mevcut).strip() == ''
                                or not str(mevcut).strip().isdigit()
                                or int(slab_no) < int(mevcut)):
'''),
    ('templates/base.html', 'B4 · templates/base.html blok 1',
     r'''/* ══ BANKA/KASA ETİKETİ (BK4) ══
''',
     r'''/* B4: "plaka no VAR MI" — `if (slab_no)` demek 0'ı yok saymak
   demekti ve B3'ten sonra 0 geçerli bir numara. */
function slabVar(v) {
  return v !== null && v !== undefined && String(v).trim() !== '';
}

/* ══ BANKA/KASA ETİKETİ (BK4) ══
'''),
    ('templates/stok.html', 'B4 · templates/stok.html blok 1',
     r'''  if (x.tip === 'PLAKA')  return x.slab_no ? plakaKodu(x.blok_no, x.slab_no)
                                           : (x.blok_no || x.id);
''',
     r'''  if (x.tip === 'PLAKA')  return plakaKodu(x.blok_no, x.slab_no) || x.id;
'''),
    ('templates/stok.html', 'B4 · templates/stok.html blok 2',
     r'''      ${s.slab_no ? `<div class="alan"><label>Plaka No</label><div class="mono">${kacar(String(s.slab_no))}</div></div>` : ''}
''',
     r'''      ${slabVar(s.slab_no) ? `<div class="alan"><label>Plaka No</label><div class="mono">${kacar(String(s.slab_no))}</div></div>` : ''}
'''),
    ('templates/stok.html', 'B4 · templates/stok.html blok 3',
     r'''  const basNo = s.slab_no ? `${kacar(s.blok_no || '')} · Plaka ${kacar(String(s.slab_no))}`
''',
     r'''  const basNo = slabVar(s.slab_no) ? `${kacar(s.blok_no || '')} · Plaka ${kacar(String(s.slab_no))}`
'''),
    ('tests/test_kritik.py', 'B4 · tests/test_kritik.py blok 1',
     r'''        assert nolar == [1, 2, 3, 4, 5, 6], nolar
''',
     r'''        assert nolar == [1, 2, 3, 4, 5, 6], nolar


# ══════════════════════════════════════════════════════════════════════
#  B4 · SIFIR PLAKA NUMARASI HER EKRANDA GÖRÜNÜR
# ══════════════════════════════════════════════════════════════════════

def test_b4_sifir_slab_hicbir_yerde_yutulmuyor():
    """B4: slab_no = 0 'yok' sayılmamalı.

    B3 ortak yardımcıyı 0'a hazır yaptı ama onu ÇAĞIRAN yerlerdeki
    doğruluk denetimleri (`if s.slab_no:`, `p.slab_no or ''`) olduğu
    gibi kaldı. 0 hem Python'da hem JS'te falsy — ekranda plaka no
    hiç yazılmadı, K6461-00 yerine sadece K6461 göründü.

    Bu test 0'ı GERÇEKTEN kaydedip her uçtan geri okuyor; biçim
    kuralını değil, sıfırın hayatta kalmasını ölçüyor."""
    from models import PlakaStok
    with fa.app.app_context():
        for _i in (0, 1):
            db.session.add(PlakaStok(
                id=f'PLKB4{_i}', firma_id=1, cins='TEST', blok_no='K8000',
                slab_no=_i, boy=298, yukseklik=169, kalinlik=2,
                metraj_m2=5.04, alis_fiyati=20, doviz='USD',
                durum='Serbest', uretici='ALBSTONE'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')

    # 1 · stok listesi: 0 sayı olarak gelmeli, '' değil
    d = c.get('/api/stok?tip=PLAKA&per_page=300').get_json()
    kayit = [x for x in d['data'] if x['id'] == 'PLKB40']
    assert kayit, 'kayıt listede yok'
    assert kayit[0]['slab_no'] == 0, kayit[0]['slab_no']

    # 2 · kesim kaynak listesi
    kl = c.get('/api/kesim/kaynak_listesi?tip=PLAKA').get_json()
    kk = [x for x in kl['kaynaklar'] if x['id'] == 'PLKB40']
    assert kk and kk[0]['slab_no'] == 0, kk

    # 3 · global arama: kod K8000-00 olmalı
    ar = c.get('/api/ara?q=K8000').get_json()
    adlar = [k.get('ad') for g in ar.get('gruplar', [])
             for k in g.get('kayitlar', [])]
    assert 'K8000-00' in adlar, adlar

    # 4 · Excel dışa aktarma: "Blok-Slab" sütunu
    xl = c.get('/api/export/stok?tip=PLAKA&fmt=xlsx')
    assert xl.status_code == 200, xl.status_code
    import io as _io, openpyxl as _ox
    ws = _ox.load_workbook(_io.BytesIO(xl.data)).active
    kodlar = [r[0] for r in ws.iter_rows(min_row=2, values_only=True)]
    assert 'K8000-00' in kodlar, kodlar[:10]


def test_b4_sifir_slab_ekranda_yaziliyor():
    """B4: ekran tarafı — `stokNo` 0'ı yutmamalı.

    Hata tam buradaydı: `x.slab_no ? ... : x.blok_no` 0'ı yanlış
    saydığı için K6461-00 yerine K6461 yazıyordu."""
    import shutil as _shutil, subprocess as _sp, os as _os, json as _json
    node = _shutil.which('node') or '/opt/node22/bin/node'
    if not _os.path.exists(node):
        import pytest as _pytest
        _pytest.skip('node yok')
    betik = r"""
const fs = require('fs'), vm = require('vm');
const base = fs.readFileSync('templates/base.html', 'utf8');
const stok = fs.readFileSync('templates/stok.html', 'utf8');
const kes = (m, bas, son) => m.slice(m.indexOf(bas), m.indexOf(son, m.indexOf(bas)));
const kum = {}; vm.createContext(kum);
vm.runInContext(kes(base, 'function slabVar(', '/* ══ BANKA/KASA'), kum);
vm.runInContext(kes(base, 'function plakaKodu(', '/* ══ BANKA/KASA'), kum);
vm.runInContext(kes(stok, 'function stokNo(', 'const RENK'), kum);
console.log(JSON.stringify({
  sifir:  kum.stokNo({tip:'PLAKA', blok_no:'K6461', slab_no:0}),
  bir:    kum.stokNo({tip:'PLAKA', blok_no:'K6461', slab_no:1}),
  yok:    kum.stokNo({tip:'PLAKA', blok_no:'K6461', slab_no:null, id:'PLK-1'}),
  bosMtn: kum.stokNo({tip:'PLAKA', blok_no:'K6461', slab_no:'', id:'PLK-1'}),
  blok:   kum.stokNo({tip:'BLOK',  blok_no:'K6461'}),
  varSifir: kum.slabVar(0), varBos: kum.slabVar(''), varNull: kum.slabVar(null),
}));
"""
    r = _sp.run([node, '-e', betik], capture_output=True, text=True, cwd='.')
    assert r.returncode == 0, r.stderr[:400]
    d = _json.loads(r.stdout.strip().splitlines()[-1])
    assert d['sifir'] == 'K6461-00', d['sifir']
    assert d['bir'] == 'K6461-01', d['bir']
    assert d['yok'] == 'K6461' and d['bosMtn'] == 'K6461'
    assert d['blok'] == 'K6461'
    # `slabVar` 0'ı VAR sayar — hatanın özü buydu
    assert d['varSifir'] is True
    assert d['varBos'] is False and d['varNull'] is False
'''),
]

TAM_ICERIK = {}

def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA B4 — SIFIR PLAKA NUMARASI YUTULUYORDU')
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
        print('    python3 yama_b4.py            # rapor')
        print('    python3 yama_b4.py --uygula')
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
        print('  ⊙ Yama B4 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_b4.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_b4'
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
    print('    Depo -> Stok -> Plaka: 0 numarali plaka artik')
    print('    K6461-00 diye gorunmeli (eskiden sadece K6461).')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

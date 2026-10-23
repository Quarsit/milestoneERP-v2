#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MA1 — MALİYET AÇIKLAMA ALANI
==================================

ÖNKOŞUL: yama_sd1.py uygulanmış olmalı (aynı dosyalara dokunuyor).

Açıklama alanı geldi. Ama asıl bulgu şu: alan ZATEN VARDI.

── ALAN VARDI, KUTU YOKTU ──
  `Maliyet.aciklama` sütunu modelde duruyordu ve sistem onu HER
  YERDE okuyordu:

      · maliyet detay panelinde bir satır olarak basılıyor
      · arama kutusu içinde arıyor
      · Excel/PDF dışa aktarmada kendi sütunu var
      · ortaklık ekstresinde katkının açıklaması olarak çıkıyor

  Ama hiçbir form onu göndermiyor, hiçbir uç nokta kabul etmiyordu.
  Dört okuyucu, sıfır yazıcı: alan hep boş kalıyordu.

── İKİ FORM, İKİSİ DE ──
  Sistemde iki ayrı maliyet ekleme formu var: Maliyet sayfasının
  kendi formu ve stok çekmecesindeki "Maliyet Ekle". İkisine de
  ekledim. Birine ekleyip ötekini unutmak, aynı alanın bir yerde
  dolup bir yerde boş kalmasıyla biterdi — ve hangisinden
  girildiğini kimse hatırlamaz.

── ÜÇ UÇ NOKTA ──
  Maliyet kaydını üç yer açıyor; üçü de artık `aciklama` kabul
  ediyor:

      /api/maliyet                tek kayıt
      /api/maliyet/dagit          seçili kayıtlara dağıtım
      /api/maliyet/blok_dagilim   bloktan çıkan ürünlere dağıtım

── DAĞITIMDA SIRA ÖNEMLİ ──
  Dağıtım uç noktaları kendi notlarını üretiyordu: "Navlun — 4
  kayda orantılı dağıtıldı (ton)". O bilgi değerli, atmadım.
  Kullanıcının notu ÖNE geçiyor:

      "MSC konteyner 4 nolu · Navlun — 2 kayda orantılı dağıtıldı (ton)"

  Sebebi OR9'da koyduğumuz kural: ortaklık ekstresinin ORTAK
  kipinde açıklama ilk ' · ' ye kadar kırpılıyor (fatura no ortağın
  belgesine sızmasın diye). O ilk parçada senin yazdığın şey
  dursun, sistemin ürettiği dağıtım notu değil. Test bunu ölçüyor.

── KDV SATIRLARINA DOKUNMADIM ──
  KDV tutarı ayrı bir maliyet satırı olarak açılıyor ve kendi
  açıklaması var: "KDV %20 — Nakliye (FSN-114)". Oraya senin
  notunu da yazmak, ortak kipinde ilk parça olarak KDV satırında
  senin notunun görünmesi demekti — yanıltıcı olurdu. KDV satırı
  ne olduğunu zaten söylüyor.

── SINIRLAR ──
  · Opsiyonel: boş bırakırsan eskisi gibi boş (NULL) kalıyor.
  · 500 karakterde kırpılıyor. Sütun Text, sınırsız yazılabilirdi
    ama serbest metnin sınırsız olması PDF/Excel çıktılarını
    bozar. Formda da maxlength var; sunucu ikinci kapı.

── ÖLÇÜLDÜ (tarayıcıda, uçtan uca) ──
  Maliyet sayfası formu : açıklama kutusu var
  Stok çekmecesi formu  : açıklama kutusu var
  Forma yazıp kaydettim → listeye düştü:
      'Kesim / Fason / Üretim'  aciklama='K6461 kesim — 18 plaka, 2cm'
  JS hatası             : yok

  167 test geçti (163 + 4 yeni kalıcı test);
  firma · js · form · zincir · akis · degismezlik temiz.

DOSYALAR
--------
  flask_app.py            üç uç nokta aciklama kabul ediyor
  templates/maliyet.html  açıklama kutusu · gönderim · form sıfırlama
  templates/stok.html     açıklama kutusu · gönderim · form sıfırlama
  tests/test_kritik.py    4 yeni test

Şema yok, göç yok — sütun zaten vardı.

KULLANIM
--------
  python3 yama_ma1.py            # RAPOR
  python3 yama_ma1.py --uygula
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
    'flask_app.py': 'aciklama_metni = ',
    'templates/maliyet.html': 'id="fAciklama"',
    'templates/stok.html': 'id="malAciklama"',
    'tests/test_kritik.py': 'def test_ma1_maliyet_aciklamasi_kaydediliyor',
}
ONKOSUL = {
    'flask_app.py': 'SD1: BOS durum ASLA yazilmaz',
    'templates/maliyet.html': 'async function maliyetKaydet() {',
    'templates/stok.html': 'function durumSecenekleriniKur',
    'tests/test_kritik.py': 'def test_sd1_bos_durum_stogun_durumunu_silemez',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'MA1 · flask_app.py blok 1',
     r'''        kullanici   = session['kullanici']
        kdv_dahil_mi = bool(data.get('kdv_dahil_mi', False))
''',
     r'''        kullanici   = session['kullanici']
        # MA1: aciklama alani modelde vardi ve her yerde OKUNUYORDU
        # (detay paneli, arama, disa aktarma, ortaklik ekstresi) ama
        # hicbir uc nokta onu KABUL ETMIYORDU: hep bos kaliyordu.
        aciklama_metni = (data.get('aciklama') or '').strip()[:500] or None
        kdv_dahil_mi = bool(data.get('kdv_dahil_mi', False))
'''),
    ('flask_app.py', 'MA1 · flask_app.py blok 2',
     r'''                    fatura_no=fatura_no, kullanici=kullanici)
''',
     r'''                    fatura_no=fatura_no, aciklama=aciklama_metni,
                    kullanici=kullanici)
'''),
    ('flask_app.py', 'MA1 · flask_app.py blok 3',
     r'''        cari_id = data.get('cari_id') or None
''',
     r'''        cari_id = data.get('cari_id') or None
        # MA1: aciklama alani modelde vardi ve her yerde OKUNUYORDU
        # (detay paneli, arama, disa aktarma, ortaklik ekstresi) ama
        # hicbir uc nokta onu KABUL ETMIYORDU: hep bos kaliyordu.
        aciklama_metni = (data.get('aciklama') or '').strip()[:500] or None
'''),
    ('flask_app.py', 'MA1 · flask_app.py blok 4',
     r'''                m = Maliyet(id=_okunur_id('MYT', Maliyet, basamak=4),
''',
     r'''                # MA1: kullanicinin notu ONE gecer. Ortaklik ekstresi
                # ortak kipinde ilk ' · ' ye kadarini gosteriyor (OR9);
                # orada insanin yazdigi kisim dursun, sistem notu degil.
                if aciklama_metni:
                    aciklama = aciklama_metni + ' · ' + aciklama
                m = Maliyet(id=_okunur_id('MYT', Maliyet, basamak=4),
'''),
    ('flask_app.py', 'MA1 · flask_app.py blok 5',
     r'''        cari_id     = data.get('cari_id') or None
        kdv_dahil_mi = bool(data.get('kdv_dahil_mi', False))
''',
     r'''        cari_id     = data.get('cari_id') or None
        # MA1: aciklama alani modelde vardi ve her yerde OKUNUYORDU
        # (detay paneli, arama, disa aktarma, ortaklik ekstresi) ama
        # hicbir uc nokta onu KABUL ETMIYORDU: hep bos kaliyordu.
        aciklama_metni = (data.get('aciklama') or '').strip()[:500] or None
        kdv_dahil_mi = bool(data.get('kdv_dahil_mi', False))
'''),
    ('flask_app.py', 'MA1 · flask_app.py blok 6',
     r'''                        aciklama=f'Toplu dağıtım — Blok {blok_no} ({datetime.now().strftime("%Y-%m-%d")})',
''',
     r'''                        aciklama=((aciklama_metni + ' · ') if aciklama_metni
                                  else '') + f'Toplu dağıtım — Blok {blok_no} '
                                  + f'({datetime.now().strftime("%Y-%m-%d")})',
'''),
    ('templates/maliyet.html', 'MA1 · templates/maliyet.html blok 1',
     r'''    <div class="modal-alt">
      <button class="iptal-btn" onclick="modalKapat()">Vazgeç</button>
''',
     r'''      <!-- MA1 · AÇIKLAMA
           Alan modelde vardı ve HER YERDE okunuyordu — detay
           panelinde, aramada, dışa aktarmada, ortaklık ekstresinde —
           ama yazılacak bir kutu yoktu: hep boş kalıyordu. -->
      <div class="form-alan"><label>Açıklama</label>
        <textarea id="fAciklama" rows="2" maxlength="500"
                  placeholder="Bu gideri sonra tanımanı sağlayacak not (opsiyonel)"
                  style="width:100%;border:1px solid var(--cizgi-koyu);border-radius:var(--r-kucuk);padding:9px 11px;font-family:var(--govde);font-size:.9rem;resize:vertical"></textarea>
      </div>
    </div>
    <div class="modal-alt">
      <button class="iptal-btn" onclick="modalKapat()">Vazgeç</button>
'''),
    ('templates/maliyet.html', 'MA1 · templates/maliyet.html blok 2',
     r'''  ['fTutar','fFaturaNo'].forEach(i => document.getElementById(i).value = '');
''',
     r'''  ['fTutar','fFaturaNo','fAciklama'].forEach(i => document.getElementById(i).value = '');
'''),
    ('templates/maliyet.html', 'MA1 · templates/maliyet.html blok 3',
     r'''      cari_id: document.getElementById('fCari').value || null
''',
     r'''      aciklama: document.getElementById('fAciklama').value.trim(),
      cari_id: document.getElementById('fCari').value || null
'''),
    ('templates/stok.html', 'MA1 · templates/stok.html blok 1',
     r'''          </label>
        </div>
''',
     r'''          </label>
        </div>
      </div>
      <!-- MA1: açıklama alanı modelde vardı, her yerde okunuyordu,
           yazacak kutu yoktu. Maliyet sayfasındaki formla aynı. -->
      <div class="form-alan"><label>Açıklama</label>
        <textarea id="malAciklama" rows="2" maxlength="500"
                  placeholder="Bu gideri sonra tanımanı sağlayacak not (opsiyonel)"
                  style="width:100%;border:1px solid var(--cizgi-koyu);border-radius:var(--r-kucuk);padding:9px 11px;font-family:var(--govde);font-size:.9rem;resize:vertical"></textarea>
'''),
    ('templates/stok.html', 'MA1 · templates/stok.html blok 2',
     r'''  document.getElementById('malKdvSec').value = '20';
''',
     r'''  document.getElementById('malAciklama').value = '';
  document.getElementById('malKdvSec').value = '20';
'''),
    ('templates/stok.html', 'MA1 · templates/stok.html blok 3',
     r'''        cari_id: document.getElementById('malCari').value || null
''',
     r'''        aciklama: document.getElementById('malAciklama').value.trim(),
        cari_id: document.getElementById('malCari').value || null
'''),
    ('tests/test_kritik.py', 'MA1 · tests/test_kritik.py blok 1',
     r'''    assert 'DUZ_ELLE_DURUMLAR.includes(d)' in h
''',
     r'''    assert 'DUZ_ELLE_DURUMLAR.includes(d)' in h


def test_ma1_maliyet_aciklamasi_kaydediliyor():
    """MA1: `aciklama` modelde vardı ve HER YERDE okunuyordu — detay
    paneli, arama, dışa aktarma, ortaklık ekstresi — ama hiçbir uç
    nokta onu kabul etmiyordu. Girilen not hiçbir yere ulaşmıyordu."""
    from models import Maliyet
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BMA1', blok_no='MA1-1', cins='TEST', boy=300, yukseklik=150,
            en=120, hacim_m3=5.4, tonaj=15, durum='Serbest'))
        db.session.commit()

    r = c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Nakliye', 'baglanti_tip': 'stok',
        'baglanti_id': 'BMA1', 'tutar': 1000, 'doviz': 'USD',
        'aciklama': 'Limandan depoya çekici — şoför Ahmet'})
    assert r.status_code == 200, r.status_code
    with fa.app.app_context():
        m = Maliyet.query.filter_by(baglanti_id='BMA1',
                                    maliyet_tip='Nakliye').first()
        assert m is not None
        assert m.aciklama == 'Limandan depoya çekici — şoför Ahmet', m.aciklama


def test_ma1_dagitimda_kullanici_notu_sistem_notunun_onune_gecer():
    """MA1: dağıtım kendi notunu üretiyor ("4 kayda orantılı
    dağıtıldı") — o bilgi değerli, atılmıyor. Kullanıcının notu ÖNE
    geçiyor: ortaklık ekstresi ortak kipinde ilk ' · ' ye kadarını
    gösteriyor (OR9), orada insanın yazdığı kısım durmalı."""
    from models import Maliyet
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add_all([
            BlokStok(id='BMA2', blok_no='MA1-2', cins='TEST', boy=300,
                     yukseklik=150, en=120, hacim_m3=5.4, tonaj=15,
                     durum='Serbest'),
            BlokStok(id='BMA3', blok_no='MA1-3', cins='TEST', boy=300,
                     yukseklik=150, en=120, hacim_m3=10.8, tonaj=30,
                     durum='Serbest')])
        db.session.commit()

    r = c.post('/api/maliyet/dagit', headers=H, json={
        'maliyet_tip': 'Navlun', 'baglanti_tip': 'stok',
        'hedefler': ['BMA2', 'BMA3'], 'tutar': 3000, 'doviz': 'USD',
        'dagitim': 'oransal', 'aciklama': 'MSC konteyner 4 nolu'})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        kayitlar = Maliyet.query.filter(
            Maliyet.baglanti_id.in_(['BMA2', 'BMA3']),
            Maliyet.maliyet_tip == 'Navlun').all()
        assert len(kayitlar) == 2, len(kayitlar)
        for m in kayitlar:
            assert m.aciklama.startswith('MSC konteyner 4 nolu · '), m.aciklama
            # Sistem notu ATILMADI
            assert 'dağıtıldı' in m.aciklama, m.aciklama
            # Ortak kipinin gördüğü kısım (OR9 kesme kuralı)
            assert m.aciklama.split(' · ')[0] == 'MSC konteyner 4 nolu'


def test_ma1_aciklama_bos_birakilabilir_ve_kirpiliyor():
    """MA1: alan opsiyonel — boş bırakmak eski davranışı korur
    (None), ve 500 karakterde kırpılıyor: sütun Text ama serbest
    metnin sınırsız olması belge çıktılarını bozar."""
    from models import Maliyet
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BMA4', blok_no='MA1-4', cins='TEST', boy=300, yukseklik=150,
            en=120, hacim_m3=5.4, tonaj=15, durum='Serbest'))
        db.session.commit()

    c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Sigorta', 'baglanti_tip': 'stok',
        'baglanti_id': 'BMA4', 'tutar': 50, 'doviz': 'USD',
        'aciklama': '   '})
    c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Komisyon', 'baglanti_tip': 'stok',
        'baglanti_id': 'BMA4', 'tutar': 60, 'doviz': 'USD',
        'aciklama': 'x' * 900})
    with fa.app.app_context():
        bos = Maliyet.query.filter_by(baglanti_id='BMA4',
                                      maliyet_tip='Sigorta').first()
        assert bos.aciklama is None, repr(bos.aciklama)
        uzun = Maliyet.query.filter_by(baglanti_id='BMA4',
                                       maliyet_tip='Komisyon').first()
        assert len(uzun.aciklama) == 500, len(uzun.aciklama)


def test_ma1_iki_formda_da_aciklama_kutusu_var():
    """MA1: iki ayrı maliyet ekleme formu var (Maliyet sayfası ve
    stok çekmecesi). Birine ekleyip ötekini unutmak, aynı alanın
    bir yerde dolup bir yerde boş kalmasıyla biterdi."""
    import io as _io
    for dosya, kutu, gonderim in (
            ('templates/maliyet.html', 'id="fAciklama"',
             "aciklama: document.getElementById('fAciklama').value.trim()"),
            ('templates/stok.html', 'id="malAciklama"',
             "aciklama: document.getElementById('malAciklama').value.trim()")):
        h = _io.open(dosya, encoding='utf-8').read()
        assert kutu in h, (dosya, kutu)
        assert gonderim in h, (dosya, gonderim)
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA MA1 — MALIYET ACIKLAMA ALANI')
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
        print('    python3 yama_ma1.py            # rapor')
        print('    python3 yama_ma1.py --uygula')
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
        print('  ⊙ Yama MA1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_ma1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_ma1'
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
    print('    Depo -> Stok -> bir stokta Maliyet Ekle')
    print('    Ikisinde de ACIKLAMA kutusu olmali. Yaz, kaydet,')
    print('    maliyet detayinda ve Disa Aktar ciktisinda gor.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

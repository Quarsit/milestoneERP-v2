#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA SD1 — STOK DÜZENLEME: DÖVİZ, BİRİM VE DURUM
=================================================

ÖNKOŞUL: yok. Ortaklık yamalarından bağımsız, istediğin sırada
uygulanabilir.

Sen dövizi sordun; formu ölçerken yanında iki şey daha çıktı.
Üçü de aynı cinsten: kullanıcının gördüğü değer ile kaydedilen
değer birbirini tutmuyordu.

── 1 · DÖVİZ (senin bildirdiğin) ──
  Tutar düzenlenebiliyordu, para birimi düzenlenemiyordu. "270"
  tek başına bir şey söylemiyor — stok EUR alınmışsa ekran onu
  USD gibi okutuyordu ve yanlış dövizle girilmiş bir stok
  düzeltilemiyordu. Döviz kutusu geldi.

── 2 · FİYAT BİRİMİ ──
  Aynı sebeple yanına koydum: 270/ton ile 270/m³ ayrı maliyet.
  Sunucu bu alanı zaten kabul ediyordu, form göndermiyordu.

── 3 · DURUM YUTULUYORDU (asıl mesele) ──
  Durum listesinde dört seçenek vardı: Serbest, Rezerve, Satildi,
  Hasarlı. Ama stoğun durumu bunlardan biri olmak zorunda değil —
  kesilmiş blok 'Kesildi', sevk edilmiş mal 'Sevkedildi' oluyor.

  <select>.value listede olmayan bir değer alınca SESSİZCE
  boşalıyor. Senin ekran görüntündeki boş DURUM kutusu buydu.
  Kaydet'e basılınca o boşluk veritabanına yazılıyordu.

  ÖLÇTÜM (yamadan önce, tarayıcıda):
      duzDurum.value         : ''        (Kesildi olmalıydı)
      kaydetten sonra durum  : ''
  Kesilmiş blok "Depoda" görünmeye başlıyordu — kaybolmuyor, boş
  durum bilerek 'depo'ya düşüyor; ama yanlış yerde duruyor.

  Daha kötüsü: silme korumaları duruma bakıyor. Durumu boşalmış
  satılmış bir bloğu DELETE ettim, 200 dönüp sildi — normalde
  "Satilmis stoklar silinemez" demesi gerekiyordu.

  ARTIK: tanımadığımız durum listenin başına ekleniyor ve seçili
  geliyor — "Kesildi (sistem)". Kaydet'e basmak onu olduğu gibi
  bırakıyor. Dört duruma elle geçiş hâlâ serbest; kapatmak değil,
  kazayla silmemek istediğimiz.

  SUNUCUDA İKİNCİ KAPI: boş/boşluk durum artık hiç yazılmıyor.
  Form düzeldi, ama başka bir çağıran aynı hatayı yapmasın.

── DOKUNMADIĞIM YER: TEDARİKÇİ BORCU ──
  Stok girişi tedarikçi cariye borç yazıyor. Döviz değişince o
  borcu da çevirmek ilk bakışta doğru görünüyor — ama C1'den beri
  BİR CariHareket BİRDEN ÇOK stoğu kapsıyor (fatura bazlı
  gruplama). Tek stoğun dövizi değişti diye o satırı çevirmek,
  aynı faturadaki öbür stokların borcunu da sessizce değiştirirdi.

  Borca dokunulmuyor. Ama sessiz de kalınmıyor: dövizi
  değiştirdiğinde ekranda şunu görüyorsun —

      "Stok dövizi USD → EUR yapıldı. Bu stoğun tedarikçi borcu
       hâlâ USD: aynı faturadaki başka stoklar da olabileceği
       için borca dokunulmadı. Gerekiyorsa Finans → Cari'den
       düzeltin."

  Karar senin; sistem kendi başına borç çevirmiyor.

── ÖLÇÜLDÜ (tarayıcıda, yamadan sonra) ──
  döviz kutusu          : var
  birim kutusu          : var
  kesilmiş blok açıldı  : 'Kesildi' seçili geliyor
  seçenekler            : Kesildi · Serbest · Rezerve · Satildi · Hasarlı
  Kaydet'ten sonra durum: 'Kesildi'   (önce '' oluyordu)
  JS hatası             : yok

  163 test geçti (159 + 4 yeni kalıcı test);
  firma · js · form · zincir · akis · degismezlik temiz.
  Durum testini, korumayı geri alıp DÜŞTÜĞÜNÜ görerek doğruladım.

── VERİNDE ZARAR VAR MI, NASIL BAKARSIN ──
  Düzenleme formunu kesilmiş/satılmış bir stokta açıp Kaydet'e
  bastıysan o stoğun durumu boşalmıştır. Bakmak için:

      sudo -u postgres psql milestone -c "SELECT id, blok_no FROM
      blok_stok WHERE durum IS NULL OR trim(durum) = '';"

  (plaka_stok ve ebatli_stok için de aynısı.) Satır çıkarsa
  söyle, doğru durumu birlikte koyarız — kesim kaydı varsa
  'Kesildi', yoksa 'Serbest'. Yama bunu kendiliğinden yapmıyor:
  hangi stoğun ne olduğunu veriye bakmadan bilemem, körlemesine
  'Serbest' yazmak kesilmiş bloğu depoda göstermeye devam ederdi.

DOSYALAR
--------
  flask_app.py            boş durum yazılmaz · döviz kabul · uyarı
  templates/stok.html     döviz + birim kutuları · durum listesi
  tests/test_kritik.py    4 yeni test

Şema yok, göç yok, yeni alan yok.

KULLANIM
--------
  python3 yama_sd1.py            # RAPOR
  python3 yama_sd1.py --uygula
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
    'flask_app.py': 'SD1: BOS durum ASLA yazilmaz',
    'templates/stok.html': 'function durumSecenekleriniKur',
    'tests/test_kritik.py': 'def test_sd1_bos_durum_stogun_durumunu_silemez',
}
ONKOSUL = {
    'flask_app.py': 'def api_stok_guncelle(stok_id):',
    'templates/stok.html': "function duzenleAc(id) {",
    'tests/test_kritik.py': 'def istemci(',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'SD1 · flask_app.py blok 1',
     r'''                if 'durum' in data:
                    yeni_durum = data['durum']
''',
     r'''                # SD1: BOS durum ASLA yazilmaz. On yuzdeki <select>,
                # stogun durumu listesinde yoksa (Kesildi, Sevkedildi…)
                # sessizce bosaliyordu ve Kaydet o boslugu buraya
                # gonderiyordu: kesilmis blok "Depoda" gorunuyor,
                # silme korumalari (Satildi/Rezerve/Teslim Edildi)
                # duruma baktigi icin dusuyordu. Form duzeltildi;
                # burasi ikinci kapi — baska bir cagiran ayni hatayi
                # yapmasin diye.
                if data.get('durum') and str(data['durum']).strip():
                    yeni_durum = str(data['durum']).strip()
'''),
    ('flask_app.py', 'SD1 · flask_app.py blok 2',
     r'''                if 'mense' in data and hasattr(stok, 'mense'):   # MS1
                    stok.mense = _mense_normal(data.get('mense'))
                if 'aciklama' in data: stok.aciklama = data['aciklama']
                db.session.commit()
''',
     r'''                # SD1: doviz duzenleme formunda HIC yoktu — tutar
                # degistirilebiliyor, para birimi degistirilemiyordu.
                # Yanlis dovizle girilmis bir stok duzeltilemiyordu.
                #
                # TEDARIKCI BORCUNA DOKUNMUYORUZ. C1'den beri bir
                # CariHareket BIRDEN COK stogu kapsiyor (fatura bazli
                # gruplama): tek stogun dovizi degisti diye o satiri
                # cevirmek, ayni faturadaki obur stoklarin borcunu da
                # sessizce degistirirdi. Bunun yerine uyariyoruz —
                # borcu duzeltmek cari tarafinin isi.
                _doviz_uyari = None
                if data.get('doviz') and hasattr(stok, 'doviz'):
                    _dv = str(data['doviz']).strip().upper()
                    if _dv in ('USD', 'EUR', 'TRY') and _dv != (stok.doviz or ''):
                        _eski_dv = stok.doviz
                        stok.doviz = _dv
                        _ch = CariHareket.query.filter_by(
                            baglanti_tip='stok', baglanti_id=stok_id).first()
                        if _ch and (_ch.doviz or '') != _dv:
                            _doviz_uyari = (
                                f'Stok dövizi {_eski_dv or "—"} → {_dv} yapıldı. '
                                f'Bu stoğun tedarikçi borcu hâlâ '
                                f'{_ch.doviz}: aynı faturadaki başka stoklar '
                                f'da olabileceği için borca dokunulmadı. '
                                f'Gerekiyorsa Finans → Cari’den düzeltin.')
                if 'mense' in data and hasattr(stok, 'mense'):   # MS1
                    stok.mense = _mense_normal(data.get('mense'))
                if 'aciklama' in data: stok.aciklama = data['aciklama']
                db.session.commit()
                if _doviz_uyari:
                    return jsonify({'ok': True, 'mesaj': _doviz_uyari,
                                    'uyari': True})
'''),
    ('templates/stok.html', 'SD1 · templates/stok.html blok 1',
     r'''        <div class="form-alan"><label>Alış Fiyatı</label><input id="duzFiyat" type="number" step="0.01"></div>
''',
     r'''        <div class="form-alan"><label>Alış Fiyatı</label><input id="duzFiyat" type="number" step="0.01"></div>
      </div>
      <!-- SD1: tutar vardi, PARA BIRIMI yoktu. "270" tek basina bir sey
           soylemiyor; stok EUR alinmisken ekran USD gibi okunuyordu.
           Fiyat birimi de ayni sebeple burada: 270/ton ile 270/m3 ayri
           maliyet. Sunucu ikisini de zaten kabul ediyordu. -->
      <div class="form-satir f2">
        <div class="form-alan"><label>Fiyat Birimi</label>
          <select id="duzFiyatBirim">
            <option value="ton">/ton</option>
            <option value="m3">/m³</option>
            <option value="m2">/m²</option>
            <option value="sqft">/sqft</option>
          </select>
        </div>
        <div class="form-alan"><label>Döviz</label>
          <select id="duzDoviz"><option>USD</option><option>EUR</option><option>TRY</option></select>
        </div>
'''),
    ('templates/stok.html', 'SD1 · templates/stok.html blok 2',
     r'''  document.getElementById('duzDurum').value = s.durum || 'Serbest';
  document.getElementById('duzFiyat').value = s.alis_fiyati || '';
''',
     r'''  durumSecenekleriniKur(s.durum);
  document.getElementById('duzFiyat').value = s.alis_fiyati || '';
  document.getElementById('duzFiyatBirim').value = s.fiyat_birim || (s.tip === 'BLOK' ? 'ton' : 'm2');
  document.getElementById('duzDoviz').value = (s.doviz || 'USD').toUpperCase();
'''),
    ('templates/stok.html', 'SD1 · templates/stok.html blok 3',
     r'''function duzenleKapat() { document.getElementById('duzModal').classList.remove('acik'); }
''',
     r'''function duzenleKapat() { document.getElementById('duzModal').classList.remove('acik'); }

/* SD1 · DURUM KUTUSU — mevcut durum listede yoksa YUTULUYORDU.
   Elle secilebilen dort durum var; ama stogun durumu bunlardan biri
   olmak zorunda degil: kesilmis blok 'Kesildi', sevk edilmis mal
   'Sevkedildi' oluyor. <select>.value listede olmayan bir deger
   alinca sessizce BOSALIYOR ve Kaydet o bosluğu veritabanina
   yaziyordu — kesilmis blok "Depoda" gorunuyor, silme korumalari
   (Satildi/Rezerve/Teslim Edildi) duruma baktigi icin dusuyordu.

   Artik tanimadigimiz durum listenin basina EKLENIYOR ve secili
   geliyor: Kaydet'e basmak onu oldugu gibi birakiyor. Elle dort
   duruma gecis hala serbest — kapatmak degil, kaza ile silmemek
   istedigimiz. */
const DUZ_ELLE_DURUMLAR = ['Serbest', 'Rezerve', 'Satildi', 'Hasarlı'];
function durumSecenekleriniKur(mevcut) {
  const sec = document.getElementById('duzDurum');
  const d = (mevcut || '').trim();
  let html = DUZ_ELLE_DURUMLAR.map(x => `<option value="${kacar(x)}">${kacar(x)}</option>`).join('');
  if (d && !DUZ_ELLE_DURUMLAR.includes(d)) {
    html = `<option value="${kacar(d)}">${kacar(d)} (sistem)</option>` + html;
  }
  sec.innerHTML = html;
  sec.value = d || 'Serbest';
}
'''),
    ('templates/stok.html', 'SD1 · templates/stok.html blok 4',
     r'''        aciklama: document.getElementById('duzAciklama').value
''',
     r'''        fiyat_birim: document.getElementById('duzFiyatBirim').value,
        doviz: document.getElementById('duzDoviz').value,
        aciklama: document.getElementById('duzAciklama').value
'''),
    ('tests/test_kritik.py', 'SD1 · tests/test_kritik.py blok 1',
     r'''    assert d.get('/api/export/ortaklik?format=xlsx').status_code == 403
''',
     r'''    assert d.get('/api/export/ortaklik?format=xlsx').status_code == 403


def test_sd1_bos_durum_stogun_durumunu_silemez():
    """SD1: düzenleme formu, durumu listesinde olmayan stoklarda
    (Kesildi, Sevkedildi…) <select>'i boş bırakıyordu ve Kaydet o
    boşluğu yazıyordu. Kesilmiş blok 'Depoda' görünüyor, silme
    korumaları duruma baktığı için düşüyordu.

    Sunucu ikinci kapı: boş/boşluk durum ASLA yazılmaz."""
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BSD1', blok_no='SD1-1', cins='TEST', boy=300, yukseklik=150,
            en=120, hacim_m3=5.4, tonaj=15, durum='Kesildi',
            alis_fiyati=270, alis_fiyat_birim='ton', doviz='EUR'))
        db.session.commit()

    for bos in ('', '   ', None):
        r = c.put('/api/stok/BSD1', headers=H,
                  json={'tip': 'BLOK', 'durum': bos, 'cins': 'TEST'})
        assert r.status_code == 200, (bos, r.status_code)
        with fa.app.app_context():
            assert db.session.get(BlokStok, 'BSD1').durum == 'Kesildi', bos

    # Gerçek bir durum hâlâ yazılabiliyor — kapıyı kapatmadık
    c.put('/api/stok/BSD1', headers=H,
          json={'tip': 'BLOK', 'durum': 'Serbest', 'cins': 'TEST'})
    with fa.app.app_context():
        assert db.session.get(BlokStok, 'BSD1').durum == 'Serbest'


def test_sd1_doviz_ve_birim_duzenlenebiliyor():
    """SD1: düzenleme formunda tutar vardı, PARA BİRİMİ yoktu —
    '270' tek başına bir şey söylemiyor. Yanlış dövizle girilmiş
    stok düzeltilemiyordu."""
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BSD2', blok_no='SD1-2', cins='TEST', boy=300, yukseklik=150,
            en=120, hacim_m3=5.4, tonaj=15, durum='Serbest',
            alis_fiyati=270, alis_fiyat_birim='ton', doviz='USD'))
        db.session.commit()

    r = c.put('/api/stok/BSD2', headers=H,
              json={'tip': 'BLOK', 'cins': 'TEST', 'durum': 'Serbest',
                    'alis_fiyati': 270, 'doviz': 'EUR', 'fiyat_birim': 'm3'})
    assert r.status_code == 200, r.status_code
    with fa.app.app_context():
        s = db.session.get(BlokStok, 'BSD2')
        assert s.doviz == 'EUR', s.doviz
        assert s.alis_fiyat_birim == 'm3', s.alis_fiyat_birim

    # Tanınmayan döviz yazılmaz — serbest metin para birimi olmaz
    c.put('/api/stok/BSD2', headers=H,
          json={'tip': 'BLOK', 'cins': 'TEST', 'doviz': 'ZZZ'})
    with fa.app.app_context():
        assert db.session.get(BlokStok, 'BSD2').doviz == 'EUR'


def test_sd1_doviz_degisince_tedarikci_borcu_sessizce_donmez():
    """SD1: C1'den beri BİR CariHareket BİRDEN ÇOK stoğu kapsıyor
    (fatura bazlı gruplama). Tek stoğun dövizi değişti diye o satırı
    çevirmek, aynı faturadaki öbür stokların borcunu da değiştirirdi.
    Borca dokunulmuyor — ama sessiz kalınmıyor, kullanıcı uyarılıyor."""
    from models import CariHareket
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add_all([
            BlokStok(id='BSD3', blok_no='SD1-3', cins='TEST', boy=300,
                     yukseklik=150, en=120, hacim_m3=5.4, tonaj=15,
                     durum='Serbest', alis_fiyati=270, doviz='USD'),
            CariHareket(id='CH-SD3', cari_id='C1', cari_unvan='TEDARIKCI',
                        hareket_tarihi=date.today(), islem_tip='Alis',
                        alacak=4050, doviz='USD', aciklama='stok alis',
                        baglanti_tip='stok', baglanti_id='BSD3')])
        db.session.commit()

    r = c.put('/api/stok/BSD3', headers=H,
              json={'tip': 'BLOK', 'cins': 'TEST', 'doviz': 'EUR'})
    d = r.get_json()
    assert d.get('uyari') is True, d
    assert 'USD' in (d.get('mesaj') or '') and 'EUR' in (d.get('mesaj') or ''), d
    with fa.app.app_context():
        assert db.session.get(BlokStok, 'BSD3').doviz == 'EUR'
        ch = CariHareket.query.filter_by(baglanti_id='BSD3').first()
        assert ch.doviz == 'USD', 'tedarikçi borcu sessizce çevrilmiş'


def test_sd1_formda_doviz_birim_ve_durum_korumasi_var():
    """SD1: üç eksik de ŞABLONDA — sunucu düzelmesi tek başına
    yetmez, kullanıcının gördüğü form yanlış değer gönderiyordu."""
    import io as _io
    h = _io.open('templates/stok.html', encoding='utf-8').read()
    for parca in ("id=\"duzDoviz\"", "id=\"duzFiyatBirim\"",
                  "doviz: document.getElementById('duzDoviz').value",
                  "fiyat_birim: document.getElementById('duzFiyatBirim').value",
                  'function durumSecenekleriniKur'):
        assert parca in h, parca
    # Durum artık sabit listeyle doldurulmuyor: tanınmayan değer
    # listeye EKLENİYOR, yoksa <select> sessizce boşalır.
    assert "document.getElementById('duzDurum').value = s.durum" not in h
    assert 'DUZ_ELLE_DURUMLAR.includes(d)' in h
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA SD1 — STOK DUZENLEME: DOVIZ, BIRIM VE DURUM')
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
        print('    python3 yama_sd1.py            # rapor')
        print('    python3 yama_sd1.py --uygula')
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
        print('  ⊙ Yama SD1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_sd1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_sd1'
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
    print('    Depo -> Stok -> bir blokta Duzenle')
    print('    DOVIZ ve FIYAT BIRIMI kutulari geldi.')
    print('    KESILMIS bir blokta ac: DURUM artik bos degil,')
    print('    "Kesildi (sistem)" secili geliyor.')
    print()
    print('  VERINDE ZARAR VAR MI:')
    print('    Yamanin basindaki aciklamada tek satirlik psql')
    print('    sorgusu var; durumu bosalmis stok varsa onu gosterir.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA KS1 — KESİMDEN ÇIKAN STOĞU KİMSE SATIN ALMADI
===================================================

ÖNKOŞUL: **yama_us2.py uygulanmış olmalı.** Betik denetliyor.

Haklıydın. Kesim, oluşturduğu stoğun `kaynak` alanını HİÇ
yazmıyordu; yazılmayınca model varsayılanı devreye giriyor ve
'satinalma' kalıyordu. Yani 66 plakanın hepsi "satın alındı" diye
kayıtlıydı — kimse satın almamış olmasına rağmen.

── ÖNCE BİR DÜZELTME: DÜN ABARTMIŞIM ──

  Sana "plakalar stok kartında 'Yurt içi KDV'li alış' yazıyor
  olmalı" demiştim. Kontrol ettim: **hiçbir ekran `alis_tipi`
  basmıyor.** Yani görünür bir yalan değilmiş, uç noktanın
  gönderdiği ama henüz kimsenin göstermediği bir yalanmış. Yine de
  düzeltiyorum — o alanı basan ilk ekran yalanı gösterecekti.

── ÖLÇÜLDÜ (ithalat EUR bloğu kesildi) ──

                      kaynak        alis_tipi (veritabanı)   (uç nokta)
      blok K6463      satinalma     ithalat                  ithalat
      plaka (önce)    satinalma     NULL                     yurtici_kdvli
      plaka (sonra)   kesim         NULL                     NULL

── NE DEĞİŞTİ ──

  1. Kesim artık `kaynak='kesim'` yazıyor (plaka ve ebatlı).
     "Üretim" demedim bilerek: kendi ocağın yok, üretim senin
     işinde bir şey ifade etmiyor. Olan şey tam olarak kesim.

  2. BOŞ ALANA DEĞER UYDURULMUYOR. Uç nokta `alis_tipi` boşsa
     'yurtici_kdvli' yazıyordu; bu varsayılan yalnızca satın almada
     anlamlı. Kesim ve üretimde boş dönüyor.

  3. Stoğun bedeli üç ekranda da doğru adla anılıyor:
       satın alma → Alış Fiyatı
       üretim     → Üretim Maliyeti
       kesim      → Kesim Maliyeti
     Üçü TEK yerden geliyor (`bedelAdi`); ayrı ayrı yazılsaydı biri
     değiştirilip ötekiler unutulurdu — bu dosyada defalarca olan
     şey.

  4. KESİM STOĞU FATURALANDIRILAMAZ. `faturalandir` ucu stoğun
     matrahı kadar TEDARİKÇİ BORCU yazıyor; kesim plakasının
     matrahı kaynak bloktan dağıtılan paydır, borcu zaten o blokta.
     Buradan faturalandırmak aynı malı iki kez borçlandırırdı.

     Bugün bu durum kendiliğinden oluşamıyor ama tek bir veri
     düzeltmesi kapıyı açardı. Denedim: elle 'faturasiz' yapılmış
     bir kesim plakası faturalandırılmak istendi → 400, cari
     hareket sayısı 0.

── GEÇMİŞ İÇİN AYRI BİR BETİK ──

  Yama bundan SONRASINI düzeltir. Mevcut 66 plaka için:

      venv/bin/python goc_kesim_kaynak.py            # RAPOR
      venv/bin/python goc_kesim_kaynak.py --uygula   # yazar

  `KesimDetay` kayıtlarında hedef olarak geçen her stoğu bulur ve
  yalnız `kaynak` alanını 'kesim' yapar. Fiyat, maliyet, ölçü,
  fatura, durum — hiçbirine dokunmaz. Muhasebede hiçbir şey
  oynamaz.

  sayim_uretim.py de güncellendi: artık "kesim" sütunu da var.

── DOĞRULANDI ──
  Kesim sonrası plaka: kaynak='kesim', uç nokta alis_tipi boş
  dönüyor, stok kartı ve düzenleme modalı "Kesim Maliyeti" diyor.
  Göç betiği önce raporladı (3 kayıt), sonra uyguladı, hepsi
  'kesim' oldu. Faturalandırma kapısı tuttu.
  237 test geçti (233 + 4). firma · js · form · akış · zincir
  denetimleri temiz. Tarayıcıda JS hatası yok.

DOSYALAR
--------
  flask_app.py            kesim kaynağı · uydurma alış tipi ·
                          faturalandırma kapısı
  templates/stok.html     ortak bedel adlandırıcı (bedelAdi)
  goc_kesim_kaynak.py     YENİ · geçmiş kayıtlar için göç
  sayim_uretim.py         kesim sütunu eklendi
  tests/test_kritik.py    4 yeni test

Şema yok, göç dosyası yok (betik veri yazar, tablo değiştirmez).

KULLANIM
--------
  python3 yama_ks1.py            # RAPOR
  python3 yama_ks1.py --uygula
  sudo systemctl restart milestone-erp
  venv/bin/python goc_kesim_kaynak.py
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
    'flask_app.py': 'KS1 · BOŞ ALANA DEĞER UYDURULMAZ',
    'templates/stok.html': 'KS1 · STOĞUN BEDELİ NE ADLA ANILIR',
    'goc_kesim_kaynak.py': 'GEÇMİŞ KESİM STOKLARINI İŞARETLE',
    'sayim_uretim.py': 'KS1: kesimden çıkan stok artık kendi adıyla',
    'tests/test_kritik.py': 'def test_ks1_kesim_kaynagi_yaziyor',
}
ONKOSUL = {
    'flask_app.py': 'MR1 · STOK MALİYET RAPORU',
    'templates/stok.html': 'US2 · EKRAN, SUNUCUNUN YAPTIĞINI SÖYLESİN',
    'tests/test_kritik.py': 'def test_us2_uretimde_fiyat_alani_duruyor_adi_degisiyor',
}
TAM_YAZILAN = ['goc_kesim_kaynak.py', 'sayim_uretim.py']

DEGISIKLIKLER = [
    ('flask_app.py', 'KS1 · flask_app.py blok 1',
     r'''            item['alis_tipi'] = (None if item['kaynak'] == 'uretim'
                                 else (getattr(s, 'alis_tipi', None)
                                       or 'yurtici_kdvli'))
''',
     r'''            # ── KS1 · BOŞ ALANA DEĞER UYDURULMAZ ──
            # `or 'yurtici_kdvli'` yalnız üretimde atlanıyordu; kesimden
            # çıkan stokta `alis_tipi` NULL olduğu için ekran onu "Yurt
            # içi KDV'li alış" diye gösteriyordu — kaynak blok İTHALAT
            # olsa bile. Ölçüldü: ithalat EUR bloğundan kesilen plaka
            # ekranda yurt içi KDV'li alış görünüyordu.
            #
            # Varsayılan yalnızca SATIN ALMADA anlamlı: orada alan her
            # zaman yazılıyor, NULL ise gerçekten eski bir kayıttır ve
            # onu da tahmin etmek doğru değil. Boşsa boş döner.
            item['alis_tipi'] = (getattr(s, 'alis_tipi', None)
                                 if item['kaynak'] in ('uretim', 'kesim')
                                 else getattr(s, 'alis_tipi', None)
                                 or 'yurtici_kdvli')
'''),
    ('flask_app.py', 'KS1 · flask_app.py blok 2',
     r'''        if getattr(stok, 'fatura_durumu', 'faturali') != 'faturasiz':
''',
     r'''        # ── KS1 · KESİMDEN ÇIKAN STOK FATURALANDIRILAMAZ ──
        # Bu uç nokta stoğun matrahı kadar TEDARİKÇİ BORCU yazıyor.
        # Kesimden çıkan plakanın matrahı kaynak bloktan dağıtılmış
        # paydır; borcu zaten o blokta. Buradan faturalandırmak aynı
        # malı iki kez borçlandırırdı.
        #
        # Bugün bu durum oluşamıyor (kesim 'faturali' yazıyor, aşağıdaki
        # denetim de onu eliyor) ama tek bir veri düzeltmesi kapıyı
        # açardı. Para söz konusuysa kapı kapalı dursun.
        if (getattr(stok, 'kaynak', None) or '') == 'kesim':
            return jsonify({'ok': False, 'mesaj':
                'Bu stok kesimden çıktı; malın borcu kaynak blokta. '
                'Faturalandırmak aynı malı iki kez borçlandırır.'}), 400
        if getattr(stok, 'fatura_durumu', 'faturali') != 'faturasiz':
'''),
    ('flask_app.py', 'KS1 · flask_app.py blok 3',
     r'''                            aciklama=f'Kesim {kesim_id} ({uretim_blok_no}-{slab_int}) | Orijinal Blok: {ana_kaynak.blok_no or ana_kaynak.id}',
''',
     r'''                            # KS1: bu plakayi KIMSE SATIN ALMADI.
                            # `kaynak` hic yazilmiyordu ve model
                            # varsayilani 'satinalma' devreye giriyordu.
                            kaynak='kesim',
                            aciklama=f'Kesim {kesim_id} ({uretim_blok_no}-{slab_int}) | Orijinal Blok: {ana_kaynak.blok_no or ana_kaynak.id}',
'''),
    ('flask_app.py', 'KS1 · flask_app.py blok 4',
     r'''                            aciklama=f'Kesim {kesim_id} - Üretim Blok: {uretim_blok_no} | Orijinal: {getattr(ana_kaynak, "blok_no", "") or ana_kaynak.id}',
''',
     r'''                            kaynak='kesim',          # KS1 — bkz. plaka
                            aciklama=f'Kesim {kesim_id} - Üretim Blok: {uretim_blok_no} | Orijinal: {getattr(ana_kaynak, "blok_no", "") or ana_kaynak.id}',
'''),
    ('templates/stok.html', 'KS1 · templates/stok.html blok 1',
     r'''      ${alan(s.kaynak === 'uretim' ? 'Üretim Maliyeti' : 'Alış Fiyatı', alisBirim, true)}
''',
     r'''      ${alan(bedelAdi(s.kaynak), alisBirim, true)}
'''),
    ('templates/stok.html', 'KS1 · templates/stok.html blok 2',
     r'''/* US2: üretime geçmeden önceki fatura durumu seçimi. */
''',
     r'''/* ── KS1 · STOĞUN BEDELİ NE ADLA ANILIR ──
   Üç kaynak, üç ad. Üç ekranda ayrı ayrı yazılsaydı biri
   değiştirilip ötekiler unutulurdu — bu dosyada defalarca olan şey.
     satinalma → alınan fiyat
     uretim    → kendi masrafın
     kesim     → kaynak bloktan DAĞITILAN pay (kimse satın almadı) */
const BEDEL_ADI = {uretim: 'Üretim Maliyeti', kesim: 'Kesim Maliyeti'};
function bedelAdi(kaynak) {
  return BEDEL_ADI[kaynak] || 'Alış Fiyatı';
}

/* US2: üretime geçmeden önceki fatura durumu seçimi. */
'''),
    ('templates/stok.html', 'KS1 · templates/stok.html blok 3',
     r'''  if (_fe) _fe.innerHTML = uretim
    ? 'Üretim Maliyeti <span style="font-weight:400;text-transform:none;'
      + 'letter-spacing:0;color:var(--soluk)">· kendi masrafın</span>'
    : 'Alış Fiyatı';
''',
     r'''  if (_fe) _fe.innerHTML = bedelAdi(uretim ? 'uretim' : 'satinalma')
    + (uretim
       ? ' <span style="font-weight:400;text-transform:none;'
         + 'letter-spacing:0;color:var(--soluk)">· kendi masrafın</span>'
       : '');
'''),
    ('templates/stok.html', 'KS1 · templates/stok.html blok 4',
     r'''  if (_dfe) _dfe.textContent = (s.kaynak === 'uretim')
    ? 'Üretim Maliyeti' : 'Alış Fiyatı';
''',
     r'''  if (_dfe) _dfe.textContent = bedelAdi(s.kaynak);
'''),
    ('tests/test_kritik.py', 'KS1 · tests/test_kritik.py blok 1',
     r'''    assert "_fe.innerHTML = uretim" in m, 'etiket kaynağa göre değişmiyor'
    assert 'Üretim Maliyeti' in m, 'üretim adı yok'

    # Aynı alan düzenleme modalında ve stok kartında da doğru adla.
    assert "_dfe.textContent = (s.kaynak === 'uretim')" in m, \
        'düzenleme modalında etiket kaynağa bakmıyor'
    assert "alan(s.kaynak === 'uretim' ? 'Üretim Maliyeti' : 'Alış Fiyatı'" in m, \
        'stok kartında etiket kaynağa bakmıyor'
''',
     r'''    assert 'Üretim Maliyeti' in m, 'üretim adı yok'

    # KS1: etiket üç ekranda da TEK yerden geliyor (`bedelAdi`).
    # Üç ayrı yerde yazılsaydı biri değiştirilip ötekiler unutulurdu.
    assert 'function bedelAdi(' in m, 'ortak adlandırıcı yok'
    assert m.count('bedelAdi(') >= 4, \
        'etiket her yerde ortak adlandırıcıdan gelmiyor'
    for _yer in ("_fe.innerHTML = bedelAdi(",       # yeni stok formu
                 "_dfe.textContent = bedelAdi(",    # düzenleme modalı
                 "alan(bedelAdi(s.kaynak)"):        # stok kartı
        assert _yer in m, f'{_yer} ortak adlandırıcıyı kullanmıyor'
'''),
    ('tests/test_kritik.py', 'KS1 · tests/test_kritik.py blok 2',
     r'''        assert _yasak not in _m, f'salt okunur olmalı ama {_yasak} var'
''',
     r'''        assert _yasak not in _m, f'salt okunur olmalı ama {_yasak} var'


# ══════════════════════════════════════════════════════════════════
#  KS1 · KESİMDEN ÇIKAN STOĞU KİMSE SATIN ALMADI
#
#  Bahadır sordu: "üretim 0 geldi ama plakalar kesimden oluştu."
#  Haklıydı. Kesim, oluşturduğu stoğun `kaynak` alanını HİÇ
#  yazmıyordu; model varsayılanı 'satinalma' devreye giriyordu.
#
#  ÖLÇÜLDÜ (ithalat EUR bloğu kesildi):
#      blok   kaynak='satinalma'  alis_tipi='ithalat'
#      plaka  kaynak='satinalma'  alis_tipi=NULL
#             → uç nokta NULL'u 'yurtici_kdvli' diye DOLDURUYORDU
#
#  Bugün bu değeri basan bir ekran yok; yani görünür bir yalan
#  değildi, ekrana çıkmayı bekleyen bir yalandı.
# ══════════════════════════════════════════════════════════════════

def test_ks1_kesim_kaynagi_yaziyor():
    """Kesim, oluşturduğu her stoğa kaynak='kesim' yazmalı."""
    import io as _io, re as _re
    m = _io.open(os.path.join(KOK, 'flask_app.py'),
                 encoding='utf-8').read().replace('\r\n', '\n')
    _r = m[m.index("@app.route('/api/kesim', methods=['POST'])"):]
    _r = _r[:_r.index("@app.route('/api/kesim/<kesim_id>', methods=['DELETE'])")]
    # Kesim icinde olusturulan HER stok kaydinda kaynak yazili olmali.
    for _ctor in ('PlakaStok(', 'EbatliStok('):
        for _p in _re.finditer(_re.escape(_ctor), _r):
            _govde = _r[_p.start():_p.start() + 1600]
            _govde = _govde[:_govde.index('db.session.add')]
            assert "kaynak='kesim'" in _govde, \
                f'{_ctor} kaynak yazmıyor — varsayılan satinalma kalır'


def test_ks1_bos_alis_tipine_deger_uydurulmuyor():
    """NULL `alis_tipi` 'yurtici_kdvli' diye doldurulmamalı.

    Kesimden çıkan stokta alan NULL; kaynak blok İTHALAT olsa bile
    uç nokta onu yurt içi KDV'li alış diye dönüyordu."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'flask_app.py'),
                 encoding='utf-8').read().replace('\r\n', '\n')
    assert "if item['kaynak'] in ('uretim', 'kesim')" in m, \
        'kesim, uydurma değerden muaf değil'
    # Eski tek kosullu hali geri gelmesin.
    assert "(None if item['kaynak'] == 'uretim'" not in m, \
        'eski hal duruyor'


def test_ks1_kesim_stogu_faturalandirilamaz():
    """Kesimden çıkan stok tedarikçi borcu doğurmamalı.

    `faturalandir` stoğun matrahı kadar borç yazıyor. Kesim
    plakasının matrahı kaynak bloktan dağıtılan paydır; borcu zaten
    o blokta. Buradan faturalandırmak aynı malı iki kez
    borçlandırırdı."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'flask_app.py'),
                 encoding='utf-8').read().replace('\r\n', '\n')
    _u = m[m.index("def api_stok_faturalandir("):]
    _u = _u[:_u.index('def api_stok_mal_teslim(')]
    assert "(getattr(stok, 'kaynak', None) or '') == 'kesim'" in _u, \
        'kesim stoğu faturalandırmaya karşı korunmuyor'
    # Denetim, borcu yazan koddan ÖNCE gelmeli.
    assert _u.index("== 'kesim'") < _u.index('_stok_cari_hareket_olustur'), \
        'denetim borç yazıldıktan sonra geliyor'


def test_ks1_gecmis_icin_goc_betigi_var():
    """Mevcut kayıtlar için göç betiği — varsayılan RAPOR olmalı."""
    import io as _io
    _y = os.path.join(KOK, 'goc_kesim_kaynak.py')
    assert os.path.exists(_y), 'göç betiği yok'
    _m = _io.open(_y, encoding='utf-8').read()
    assert "UYGULA = '--uygula' in sys.argv" in _m, '--uygula kapısı yok'
    assert 'if UYGULA:' in _m, 'rapor kipi yazıyor olabilir'
    # Yalnız `kaynak` alanina dokunmali.
    import re as _re
    _atamalar = set(_re.findall(r'\bs\.(\w+) =', _m))
    assert _atamalar <= {'kaynak'}, f'başka alana da yazıyor: {_atamalar}'
'''),
]

TAM_ICERIK = {
    'goc_kesim_kaynak.py':
        'IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwojIC0qLSBjb2Rpbmc6IHV0Zi04IC0qLQoiIiIKR0XDh03EsMWeIEtFU8SwTSBTVE9LTEFSSU5JIMSwxZ5BUkVUTEUgIChrYXluYWsgPSAna2VzaW0nKQo9PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PQoKS2VzaW0sIG9sdcWfdHVyZHXEn3Ugc3RvxJ91biBga2F5bmFrYCBhbGFuxLFuxLEgaGnDpyB5YXptxLF5b3JkdTsgbW9kZWwKdmFyc2F5xLFsYW7EsSBkZXZyZXllIGdpcmlwICdzYXRpbmFsbWEnIGthbMSxeW9yZHUuIFlhbmkga2VzaW1kZW4gw6fEsWthbgpoZXIgcGxha2EgInNhdMSxbiBhbMSxbmTEsSIgZGl5ZSBrYXnEsXRsxLF5ZMSxIOKAlCBraW1zZSBzYXTEsW4gYWxtYW3EscWfCm9sbWFzxLFuYSByYcSfbWVuLgoKWWFtYSBidW51IEJVTkRBTiBTT05SQVNJIGnDp2luIGTDvHplbHRpeW9yLiBCdSBiZXRpayBHRcOHTcSwxZ7EsCBkw7x6ZWx0aXI6CmJpciBgS2VzaW1EZXRheWAga2F5ZMSxbmRhIGhlZGVmIG9sYXJhayBnZcOnZW4gaGVyIHN0b8SfdSBidWx1ciB2ZQpga2F5bmFrYCBhbGFuxLFuxLEgJ2tlc2ltJyB5YXBhci4KCkRva3VudWxhbiB0ZWsgYWxhbiBga2F5bmFrYC4gRml5YXQsIG1hbGl5ZXQsIMO2bMOnw7wsIGZhdHVyYSwgZHVydW0g4oCUCmhpw6diaXJpIGRlxJ9pxZ9tZXouIE11aGFzZWJlZGUgaGnDp2JpciDFn2V5IG95bmFtYXo7IGRlxJ9pxZ9lbiwgZWtyYW7EsW4gbmUKc8O2eWxlZGnEn2kgdmUgZGVuZXRpbWluIG5lIGfDtnJlYmlsZGnEn2kuCgpLVUxMQU5JTQotLS0tLS0tLQogIHZlbnYvYmluL3B5dGhvbiBnb2Nfa2VzaW1fa2F5bmFrLnB5ICAgICAgICAgICAgICAjIFJBUE9SIOKAlCB5YXptYXoKICB2ZW52L2Jpbi9weXRob24gZ29jX2tlc2ltX2theW5hay5weSAtLXV5Z3VsYSAgICAgIyB5YXphcgoiIiIKaW1wb3J0IG9zCmltcG9ydCBzeXMKCnN5cy5wYXRoLmluc2VydCgwLCBvcy5wYXRoLmRpcm5hbWUob3MucGF0aC5hYnNwYXRoKF9fZmlsZV9fKSkpCm9zLmVudmlyb24uc2V0ZGVmYXVsdCgnTUlMRVNUT05FX0FDSUxJU19BVExBJywgJzEnKQoKaW1wb3J0IGZsYXNrX2FwcCBhcyBmYSAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgbm9xYTogRTQwMgpmcm9tIG1vZGVscyBpbXBvcnQgKGRiLCBCbG9rU3RvaywgUGxha2FTdG9rLCBFYmF0bGlTdG9rLCAgICMgbm9xYTogRTQwMgogICAgICAgICAgICAgICAgICAgIEtlc2ltRGV0YXkpCgpVWUdVTEEgPSAnLS11eWd1bGEnIGluIHN5cy5hcmd2Ck1PREVMID0geydCTE9LJzogQmxva1N0b2ssICdQTEFLQSc6IFBsYWthU3RvaywgJ0VCQVRMSSc6IEViYXRsaVN0b2t9CgoKZGVmIG1haW4oKToKICAgIHdpdGggZmEuYXBwLmFwcF9jb250ZXh0KCk6CiAgICAgICAgcHJpbnQoJz0nICogNzApCiAgICAgICAgcHJpbnQoJyAgS0VTxLBNREVOIMOHSUtBTiBTVE9LTEFSIOKAlCBrYXluYWsgYWxhbsSxJykKICAgICAgICBwcmludCgnICBNT0Q6ICcgKyAoJ1VZR1VMQScgaWYgVVlHVUxBIGVsc2UgJ1JBUE9SICh5YXptYXopJykpCiAgICAgICAgcHJpbnQoJz0nICogNzApCgogICAgICAgIGhlZGVmbGVyID0ge30KICAgICAgICBmb3IgZCBpbiBLZXNpbURldGF5LnF1ZXJ5LmFsbCgpOgogICAgICAgICAgICBpZiBkLmhlZGVmX3N0b2tfaWQgYW5kIGQuaGVkZWZfdGlwIGluIE1PREVMOgogICAgICAgICAgICAgICAgaGVkZWZsZXIuc2V0ZGVmYXVsdChkLmhlZGVmX3RpcCwgc2V0KCkpLmFkZChkLmhlZGVmX3N0b2tfaWQpCgogICAgICAgIGlmIG5vdCBoZWRlZmxlcjoKICAgICAgICAgICAgcHJpbnQoJyAgS2VzaW0ga2F5ZMSxIHlvayDigJQgeWFwxLFsYWNhayBiaXIgxZ9leSB5b2suJykKICAgICAgICAgICAgcHJpbnQoJz0nICogNzApCiAgICAgICAgICAgIHJldHVybiAwCgogICAgICAgIGRlZ2lzZWNlaywgemF0ZW4gPSAwLCAwCiAgICAgICAgZm9yIHRpcCwgaWRsZXIgaW4gc29ydGVkKGhlZGVmbGVyLml0ZW1zKCkpOgogICAgICAgICAgICBNb2RlbCA9IE1PREVMW3RpcF0KICAgICAgICAgICAga2F5aXRsYXIgPSBNb2RlbC5xdWVyeS5maWx0ZXIoTW9kZWwuaWQuaW5fKGlkbGVyKSkuYWxsKCkKICAgICAgICAgICAgYnVfdGlwID0gW3MgZm9yIHMgaW4ga2F5aXRsYXIKICAgICAgICAgICAgICAgICAgICAgIGlmIChnZXRhdHRyKHMsICdrYXluYWsnLCBOb25lKSBvciAnc2F0aW5hbG1hJykgIT0gJ2tlc2ltJ10KICAgICAgICAgICAgemF0ZW4gKz0gbGVuKGtheWl0bGFyKSAtIGxlbihidV90aXApCiAgICAgICAgICAgIGlmIG5vdCBidV90aXA6CiAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICBwcmludCgpCiAgICAgICAgICAgIHByaW50KGYn4pSA4pSAIHt0aXB9IMK3IHtsZW4oYnVfdGlwKX0ga2F5xLF0ICcgKyAn4pSAJyAqIDI4KQogICAgICAgICAgICBmb3IgcyBpbiBidV90aXBbOjEyXToKICAgICAgICAgICAgICAgIGVza2kgPSBnZXRhdHRyKHMsICdrYXluYWsnLCBOb25lKSBvciAnc2F0aW5hbG1hJwogICAgICAgICAgICAgICAgcHJpbnQoZicgICB7cy5pZDo8MjJ9IHtlc2tpIXI6PDEzfSDihpIgXCdrZXNpbVwnJykKICAgICAgICAgICAgICAgIGlmIFVZR1VMQToKICAgICAgICAgICAgICAgICAgICBzLmtheW5hayA9ICdrZXNpbScKICAgICAgICAgICAgaWYgbGVuKGJ1X3RpcCkgPiAxMjoKICAgICAgICAgICAgICAgIHByaW50KGYnICAg4oCmIHZlIHtsZW4oYnVfdGlwKSAtIDEyfSBrYXnEsXQgZGFoYScpCiAgICAgICAgICAgICAgICBpZiBVWUdVTEE6CiAgICAgICAgICAgICAgICAgICAgZm9yIHMgaW4gYnVfdGlwWzEyOl06CiAgICAgICAgICAgICAgICAgICAgICAgIHMua2F5bmFrID0gJ2tlc2ltJwogICAgICAgICAgICBkZWdpc2VjZWsgKz0gbGVuKGJ1X3RpcCkKCiAgICAgICAgcHJpbnQoKQogICAgICAgIHByaW50KCc9JyAqIDcwKQogICAgICAgIGlmIHphdGVuOgogICAgICAgICAgICBwcmludChmJyAge3phdGVufSBrYXnEsXQgemF0ZW4gXCdrZXNpbVwnIOKAlCBhdGxhbmTEsS4nKQogICAgICAgIGlmIG5vdCBkZWdpc2VjZWs6CiAgICAgICAgICAgIHByaW50KCcgIOKckyBEZcSfacWfZWNlayBiaXIgxZ9leSB5b2suJykKICAgICAgICBlbGlmIFVZR1VMQToKICAgICAgICAgICAgZGIuc2Vzc2lvbi5jb21taXQoKQogICAgICAgICAgICBwcmludChmJyAg4pyTIHtkZWdpc2VjZWt9IGthecSxdCBnw7xuY2VsbGVuZGkuJykKICAgICAgICAgICAgcHJpbnQoJyAgVGFyYXnEsWPEsWRhIEN0cmwrRjUg4oCUIHN0b2sga2FydMSxbmRhIGFydMSxaycpCiAgICAgICAgICAgIHByaW50KCcgICJLZXNpbSBNYWxpeWV0aSIgeWF6YXIgdmUgdXlkdXJtYSBhbMSxxZ8gdGlwaSBnaXRtacWfdGlyLicpCiAgICAgICAgZWxzZToKICAgICAgICAgICAgcHJpbnQoZicgIHtkZWdpc2VjZWt9IGthecSxdCBnw7xuY2VsbGVuZWNlay4gWWF6bWFrIGnDp2luOicpCiAgICAgICAgICAgIHByaW50KCcgICAgICB2ZW52L2Jpbi9weXRob24gZ29jX2tlc2ltX2theW5hay5weSAtLXV5Z3VsYScpCiAgICAgICAgcHJpbnQoJz0nICogNzApCiAgICByZXR1cm4gMAoKCmlmIF9fbmFtZV9fID09ICdfX21haW5fXyc6CiAgICBzeXMuZXhpdChtYWluKCkpCg==',
    'sayim_uretim.py':
        'IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwojIC0qLSBjb2Rpbmc6IHV0Zi04IC0qLQoiIiIKS0HDhyDDnFJFVMSwTSBTVE/EnlUgVkFSIOKAlCBTQUxUIE9LVU5VUiBTQVlJTQo9PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PQoKYGRlbmV0aW1fdXJldGltX21hbGl5ZXQucHlgICJiZWRlbGkgZ2lyaWxtZW1pxZ8gw7xyZXRpbSBzdG/En3UgeW9rIgpkZWRpLiBCdSBpa2kgYW5sYW1hIGdlbGViaWxpcjoKCiAgYSkgw7xyZXRpbSBzdG9rbGFyxLFuIHZhciB2ZSBoZXBzaW5pbiBiZWRlbGkgZ2lyaWxpICAg4oaSIGhlciDFn2V5IHlvbHVuZGEKICBiKSBoacOnIMO8cmV0aW0gc3RvxJ91biB5b2sgICAgICAgICAgICAgICAgICAgICAgICAgICAg4oaSIGJldGnEn2luIGJha2FjYWsKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBiaXIgxZ9leWkgeW9rdHUKCkRlbmV0aW0gYmV0acSfaSBidSBpa2lzaW5pIGF5xLFybcSxeW9yZHUg4oCUIGJlbmltIGVrc2nEn2ltLiBCdSBzYXnEsW0KYXnEsXLEsXlvci4gSGnDp2JpciDFn2V5IHlhem1hei4KCktVTExBTklNCi0tLS0tLS0tCiAgdmVudi9iaW4vcHl0aG9uIHNheWltX3VyZXRpbS5weQoiIiIKaW1wb3J0IG9zCmltcG9ydCBzeXMKCnN5cy5wYXRoLmluc2VydCgwLCBvcy5wYXRoLmRpcm5hbWUob3MucGF0aC5hYnNwYXRoKF9fZmlsZV9fKSkpCm9zLmVudmlyb24uc2V0ZGVmYXVsdCgnTUlMRVNUT05FX0FDSUxJU19BVExBJywgJzEnKQoKaW1wb3J0IGZsYXNrX2FwcCBhcyBmYSAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgbm9xYTogRTQwMgpmcm9tIG1vZGVscyBpbXBvcnQgQmxva1N0b2ssIFBsYWthU3RvaywgRWJhdGxpU3RvayAgICAgICAgIyBub3FhOiBFNDAyCgoKZGVmIG1haW4oKToKICAgIHdpdGggZmEuYXBwLmFwcF9jb250ZXh0KCk6CiAgICAgICAgcHJpbnQoJz0nICogNjQpCiAgICAgICAgcHJpbnQoJyAgU1RPSyBTQVlJTUkg4oCUIEtBWU5BxJ5JTkEgR8OWUkUnKQogICAgICAgIHByaW50KCc9JyAqIDY0KQogICAgICAgIHByaW50KGYnICB7IiI6PDh9eyJ0b3BsYW0iOj45fXsiw7xyZXRpbSI6Pjl9eyJrZXNpbSI6Pjl9JwogICAgICAgICAgICAgIGYneyJzYXTEsW4gYWxtYSI6PjEzfScpCiAgICAgICAgcHJpbnQoJyAgJyArICctJyAqIDQ4KQogICAgICAgIHRvcF91ID0gdG9wX2sgPSAwCiAgICAgICAgZm9yIGFkLCBNIGluICgoJ0JMT0snLCBCbG9rU3RvayksICgnUExBS0EnLCBQbGFrYVN0b2spLAogICAgICAgICAgICAgICAgICAgICAgKCdFQkFUTEknLCBFYmF0bGlTdG9rKSk6CiAgICAgICAgICAgIHQgPSBNLnF1ZXJ5LmNvdW50KCkKICAgICAgICAgICAgdSA9IE0ucXVlcnkuZmlsdGVyKE0ua2F5bmFrID09ICd1cmV0aW0nKS5jb3VudCgpCiAgICAgICAgICAgICMgS1MxOiBrZXNpbWRlbiDDp8Sxa2FuIHN0b2sgYXJ0xLFrIGtlbmRpIGFkxLF5bGEgYW7EsWzEsXlvci4KICAgICAgICAgICAgayA9IE0ucXVlcnkuZmlsdGVyKE0ua2F5bmFrID09ICdrZXNpbScpLmNvdW50KCkKICAgICAgICAgICAgdG9wX3UgKz0gdQogICAgICAgICAgICB0b3BfayArPSBrCiAgICAgICAgICAgIHByaW50KGYnICB7YWQ6PDh9e3Q6Pjl9e3U6Pjl9e2s6Pjl9e3QgLSB1IC0gazo+MTN9JykKICAgICAgICBwcmludCgpCiAgICAgICAgaWYgdG9wX2s6CiAgICAgICAgICAgIHByaW50KGYnICB7dG9wX2t9IHN0b2sgS0VTxLBNREVOIMOnxLFrbcSxxZ8g4oCUIGtpbXNlIHNhdMSxbiBhbG1hZMSxLCcKICAgICAgICAgICAgICAgICAgZicgYmxva3RhbiBrZXNpbGRpLicpCiAgICAgICAgICAgIHByaW50KCkKICAgICAgICBpZiB0b3BfdToKICAgICAgICAgICAgIyBExLBLS0FUOiBidSBiZXRpayBiZWRlbGUgQkFLTUFaLCB5YWxuxLF6IHNheWFyLiAiSGVwc2luaW4KICAgICAgICAgICAgIyBiZWRlbGkgZ2lyaWxpIiBkZW1layBkZW5ldGltIGJldGnEn2luaW4gacWfaSDigJQgaWtpc2luaQogICAgICAgICAgICAjIGJpcmJpcmluZSBrYXLEscWfdMSxcm1hayB0YW0gZGEga2HDp8Sxbm1heWEgw6dhbMSxxZ90xLHEn8SxbcSxeiDFn2V5LgogICAgICAgICAgICBwcmludChmJyAge3RvcF91fSDDvHJldGltIHN0b8SfdSB2YXIuJykKICAgICAgICAgICAgcHJpbnQoJyAgZGVuZXRpbV91cmV0aW1fbWFsaXlldC5weSBidW5sYXJkYSBiZWRlbGknKQogICAgICAgICAgICBwcmludCgnICBnaXJpbG1lbWnFnyBvbGFuIHZhciBtxLEgZGl5ZSBiYWthcjsgdGVtaXogw6fEsWt0xLF5c2EnKQogICAgICAgICAgICBwcmludCgnICBnZXLDp2VrdGVuIHRlbWl6IGRlbWVrdGlyLicpCiAgICAgICAgZWxzZToKICAgICAgICAgICAgcHJpbnQoJyAgSGnDpyDDvHJldGltIHN0b8SfdSB5b2sg4oCUIGRlbmV0aW1pbiBiYWthY2HEn8SxIGJpciDFn2V5JykKICAgICAgICAgICAgcHJpbnQoJyAgeW9rdHUuIEtlbmRpIG9jYcSfxLFuIG9sbWFkxLHEn8SxIGnDp2luIGJla2xlbmVuIGRlIGJ1LicpCiAgICAgICAgcHJpbnQoJz0nICogNjQpCiAgICByZXR1cm4gMAoKCmlmIF9fbmFtZV9fID09ICdfX21haW5fXyc6CiAgICBzeXMuZXhpdChtYWluKCkpCg==',
}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA KS1 — KESİMDEN ÇIKAN STOĞU KİMSE SATIN ALMADI')
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
        print('    python3 yama_ks1.py            # rapor')
        print('    python3 yama_ks1.py --uygula')
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
        print('  ⊙ Yama KS1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_ks1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_ks1'
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
    print('  SIMDI GECMISI DUZELT (mevcut 66 plaka):')
    print('    venv/bin/python goc_kesim_kaynak.py            # RAPOR')
    print('    venv/bin/python goc_kesim_kaynak.py --uygula')
    print()
    print('    Yalniz `kaynak` alanina dokunur. Fiyat, maliyet,')
    print('    olcu, fatura, durum degismez.')
    print()
    print('  SONRA: Depo -> Stok -> Plaka -> bir plakanin karti.')
    print('    Bedel artik "Kesim Maliyeti" diye aniliyor.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

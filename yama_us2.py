#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA US2 — ÜRETİLEN MALIN "ALIŞ FİYATI" OLMAZ, MALİYETİ OLUR
=============================================================

ÖNKOŞUL: **yama_us1.py uygulanmış olmalı.** Betik denetliyor;
uygulanmamışsa hiçbir dosyaya dokunmadan çıkar.

Sorduğun soruydu: "kaynak üretim seçilince Alış Fiyatı olmalı mı?"
Ölçtüm. Cevap: ALAN KALMALI, ADI DEĞİŞMELİ.

── NEDEN KALMALI ──

  Sunucu üretimde alış tipini NULL, KDV'yi 0, fatura durumunu zorla
  "faturasız" yapıyor ve tedarikçi cari hareketi hiç doğmuyor. Ama
  FİYATI saklıyor ve stoğun matrahını ondan kuruyor.

  İki üretim bloğu açıp ikisini de 10.000 $'a sattım:

      girilen bedel    kaydedilen matrah   satış maliyeti      kâr
      —                            0 $          1,00 $   9.999,00 $
      300 $/ton                6.000 $      6.001,00 $   3.999,00 $

  Yani alanı kaldırsak ya da boş bıraksak, kendi ocağından çıkan
  bloğun maliyeti HİÇBİR YERDE olmaz ve kâr 6.000 $ şişer. MR1'de
  düzelttiğim şeyin aynısı, bu sefer kaynağında.

  Üretilen malın da maliyeti var — ocak çıkarma, fason, nakliye.
  Fark şu ki bu bir BORÇ değil: kimseye ödemiyorsun, kendi masrafın.
  Sistem zaten tam böyle davranıyor.

── NE DEĞİŞTİ ──

  1. Kaynak "Üretim" seçilince etiket **Üretim Maliyeti · kendi
     masrafın** oluyor. Aynı alan düzenleme modalında ve stok
     kartında da aynı adı alıyor — tek alanın üç ekranda iki ayrı
     adı olmasın. (Toplu aktarma formu bu ayrımı zaten yapıyordu.)

  2. EKRAN, SUNUCUNUN YAPTIĞINI SÖYLÜYOR. Üretimde "Fatura Durumu"
     ve "Fatura No" alanları duruyordu; üstelik "Faturalı" seçili ve
     altındaki not "tedarikçi cariye borç işlenir" diyordu — yani
     olacağın TERSİ. Sunucu o değeri zaten yok sayıp "faturasız"
     yazıyor. İkisi de artık üretimde gizleniyor, notun yerine şu
     geçiyor:

       "Üretimde tedarikçi borcu, fatura ve KDV yok. Girilen maliyet
        stoğun kendi bedeli olarak saklanır."

     Toplu aktarma formu bunları zaten gizliyordu; tekil form
     gizlemiyordu.

  3. "Alış fiyatına nakliye dahil" işareti üretimde "Maliyete
     nakliye dahil" oluyor.

── YOL ÜSTÜNDE ÇIKAN BİR KUSUR ──

  Üretime geçip geri dönünce "Faturalı" seçimin sessizce
  "Faturasız"a dönüyordu. İkisi arasındaki fark tedarikçiye borç
  yazılıp yazılmamasıdır — sessizce değişmesi en olmayacak şey.
  Seçim artık saklanıp geri yükleniyor.

  AYNI KUSUR TOPLU AKTARMA FORMUNDA DA VARDI, o da düzeltildi.
  Birini düzeltip ötekini unutmak bu dosyada defalarca gördüğümüz
  şey.

── YENİ BİR DENETİM BETİĞİ ──

  denetim_uretim_maliyet.py — kaynağı "üretim" olup bedeli
  girilmemiş stokları listeler. HİÇBİR ŞEY YAZMAZ, yalnız okur.

      venv/bin/python denetim_uretim_maliyet.py
      venv/bin/python denetim_uretim_maliyet.py --satilmis

  Satılmış olanları ayrıca işaretliyor ve kayıtlı kârlarını
  topluyor: o rakam, bedel girilseydi düşecek olan rakamdır.
  Bunu bir çalıştır, çıktıyı bana gönder.

── DOĞRULANDI ──
  Kaynak satın alma ↔ üretim arasında gidip gelindi: etiketler,
  gizlenen alanlar, not ve fatura durumu seçimi her seferinde doğru.
  Üretimde form yine kaydırmıyor (gövde 574 px).
  233 test geçti (229 + 4). firma · js · form · akış denetimleri
  temiz. Tarayıcıda JS hatası yok.

DOSYALAR
--------
  templates/stok.html           etiketler · gizlenen fatura alanları ·
                                not · seçim koruma (iki formda)
  denetim_uretim_maliyet.py     YENİ · salt okunur denetim
  tests/test_kritik.py          4 yeni test

Şema yok, göç yok, sunucu tarafı değişmedi.

KULLANIM
--------
  python3 yama_us2.py            # RAPOR
  python3 yama_us2.py --uygula
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
    'templates/stok.html': 'US2 · EKRAN, SUNUCUNUN YAPTIĞINI SÖYLESİN',
    'denetim_uretim_maliyet.py': 'MALİYETİ OLMAYAN ÜRETİM STOKLARI',
    'tests/test_kritik.py': 'def test_us2_uretimde_fiyat_alani_duruyor_adi_degisiyor',
}
ONKOSUL = {
    'templates/stok.html': 'US1 · ALANLAR TİPE GÖRE AKIYOR',
    'tests/test_kritik.py': 'def test_us1_alanlar_tipe_gore_dogru_sirada',
}
TAM_YAZILAN = ['denetim_uretim_maliyet.py']

DEGISIKLIKLER = [
    ('templates/stok.html', 'US2 · templates/stok.html blok 1',
     r'''        <div class="form-alan"><label>Alış Fiyatı</label><input id="duzFiyat" type="number" step="0.01"></div>
''',
     r'''        <div class="form-alan"><label id="duzFiyatEtiket">Alış Fiyatı</label><input id="duzFiyat" type="number" step="0.01"></div>
'''),
    ('templates/stok.html', 'US2 · templates/stok.html blok 2',
     r'''        <div class="form-alan"><label>Alış Fiyatı</label><input id="sFiyat" type="number" step="0.01" oninput="hesapla()"></div>
''',
     r'''        <!-- US2: ÜRETİLEN MALIN "ALIŞ FİYATI" OLMAZ.
             Alan duruyor çünkü üretilen malın da maliyeti var (ocak,
             fason, nakliye) ve sunucu onu matrah olarak saklıyor;
             boş bırakılırsa o stoğun maliyeti HİÇ olmuyor. Ölçüldü:
             aynı 10.000 $'lık satış, fiyatı girilmemiş üretim
             bloğunda 9.999 $ kâr, 6.000 $'lık bloğunda 3.999 $ kâr
             gösteriyordu. Değişen tek şey ADI — toplu aktarma formu
             bu ayrımı zaten yapıyordu, tekil form yapmıyordu. -->
        <div class="form-alan"><label id="sFiyatEtiket">Alış Fiyatı</label><input id="sFiyat" type="number" step="0.01" oninput="hesapla()"></div>
'''),
    ('templates/stok.html', 'US2 · templates/stok.html blok 3',
     r'''        <div class="form-alan"><label>Fatura Durumu</label>
          <select id="sFaturaDurum" onchange="faturaDurumDegisti()">
''',
     r'''        <div class="form-alan" id="sFaturaDurumAlan"><label>Fatura Durumu</label>
          <select id="sFaturaDurum" onchange="faturaDurumDegisti()">
'''),
    ('templates/stok.html', 'US2 · templates/stok.html blok 4',
     r'''        <div class="form-alan"><label>Fatura No</label><input id="sFaturaNo" placeholder="AKD-2026-118"></div>
''',
     r'''        <div class="form-alan" id="sFaturaNoAlan"><label>Fatura No</label><input id="sFaturaNo" placeholder="AKD-2026-118"></div>
'''),
    ('templates/stok.html', 'US2 · templates/stok.html blok 5',
     r'''          Alış fiyatına nakliye dahil
''',
     r'''          <span id="sNakliyeEtiket">Alış fiyatına nakliye dahil</span>
'''),
    ('templates/stok.html', 'US2 · templates/stok.html blok 6',
     r'''      ${alan('Alış Fiyatı', alisBirim, true)}
''',
     r'''      ${alan(s.kaynak === 'uretim' ? 'Üretim Maliyeti' : 'Alış Fiyatı', alisBirim, true)}
'''),
    ('templates/stok.html', 'US2 · templates/stok.html blok 7',
     r'''function kaynakDegisti() {
''',
     r'''/* US2: üretime geçmeden önceki fatura durumu seçimi. */
let FATURA_DURUM_ONCEKI = null;

function kaynakDegisti() {
'''),
    ('templates/stok.html', 'US2 · templates/stok.html blok 8',
     r'''  if (_te) _te.textContent = uretim ? 'Üretim Tarihi' : 'Fatura Tarihi';
''',
     r'''  if (_te) _te.textContent = uretim ? 'Üretim Tarihi' : 'Fatura Tarihi';
  /* US2: fiyat alanı da öyle. Satın almadığın malın "alış fiyatı"
     olmaz; girilen rakam senin kendi masrafın ve cariye borç
     yazılmıyor. Alanın KENDİSİ duruyor — boş bırakılırsa o stoğun
     maliyeti hiç olmuyor. */
  const _fe = document.getElementById('sFiyatEtiket');
  if (_fe) _fe.innerHTML = uretim
    ? 'Üretim Maliyeti <span style="font-weight:400;text-transform:none;'
      + 'letter-spacing:0;color:var(--soluk)">· kendi masrafın</span>'
    : 'Alış Fiyatı';
  /* ── US2 · EKRAN, SUNUCUNUN YAPTIĞINI SÖYLESİN ──
     Üretimde sunucu fatura durumunu ZORLA 'faturasiz' yapıyor ve
     tedarikçi cari hareketi hiç doğmuyor (flask_app: "ÜRETİMDE
     FATURA YOK"). Ekran ise "Faturalı" seçili duruyor ve altındaki
     not "tedarikçi cariye borç işlenir" diyordu — yani olacağın
     TERSİNİ söylüyordu. Toplu aktarma formu bu alanları zaten
     gizliyordu; tekil form gizlemiyordu. */
  const _gos = (id, ac) => {
    const e = document.getElementById(id);
    if (e) e.style.display = ac ? '' : 'none';
  };
  _gos('sFaturaDurumAlan', !uretim);
  _gos('sFaturaNoAlan', !uretim);
  const _fd = document.getElementById('fdNot');
  const _fdSec = document.getElementById('sFaturaDurum');
  if (uretim) {
    /* Seçimi SAKLA. Üretime geçip geri dönünce kullanıcının
       "Faturalı" seçimi sessizce "Faturasız"a dönüyordu — ikisi
       arasındaki fark tedarikçiye borç yazılıp yazılmaması, yani
       sessiz değişmesi en olmayacak şey. */
    if (_fdSec.value !== 'faturasiz') FATURA_DURUM_ONCEKI = _fdSec.value;
    _fdSec.value = 'faturasiz';
    document.getElementById('sFaturaNo').value = '';
    if (_fd) {
      _fd.style.background = 'var(--kehribar-bg,#FDF6E3)';
      _fd.style.color = 'var(--kehribar,#8A6D1F)';
      _fd.textContent = 'Üretimde tedarikçi borcu, fatura ve KDV yok.'
        + ' Girilen maliyet stoğun kendi bedeli olarak saklanır.';
    }
  } else {
    if (FATURA_DURUM_ONCEKI) {
      _fdSec.value = FATURA_DURUM_ONCEKI;
      FATURA_DURUM_ONCEKI = null;
    }
    faturaDurumDegisti();
  }
  /* Üretimde "alış fiyatı" diye bir şey olmadığı için işaretin adı
     da değişiyor — toplu aktarma formunda olduğu gibi. */
  const _ne = document.getElementById('sNakliyeEtiket');
  if (_ne) _ne.textContent = uretim
    ? 'Maliyete nakliye dahil' : 'Alış fiyatına nakliye dahil';
'''),
    ('templates/stok.html', 'US2 · templates/stok.html blok 9',
     r'''function topluKaynakDegisti() {
''',
     r'''/* US2: üretime geçmeden önceki fatura durumu seçimi (toplu form). */
let TP_FATURA_DURUM_ONCEKI = null;

function topluKaynakDegisti() {
'''),
    ('templates/stok.html', 'US2 · templates/stok.html blok 10',
     r'''  if (uretim) {
    document.getElementById('tCari').value = '';
    document.getElementById('tFaturaNo').value = '';
    document.getElementById('tKdv').value = 0;
    document.getElementById('tKdvDahil').checked = false;
    document.getElementById('tFaturaDurum').value = 'faturasiz';
''',
     r'''  /* US2: tekil formdaki ile AYNI sessiz değişim burada da vardı —
     üretime geçip geri dönünce "Faturalı" seçimi "Faturasız" olarak
     kalıyordu. Tek yerde düzeltip ötekini unutmak, bu dosyada
     defalarca gördüğümüz şey. */
  const _tfd = document.getElementById('tFaturaDurum');
  if (uretim) {
    document.getElementById('tCari').value = '';
    document.getElementById('tFaturaNo').value = '';
    document.getElementById('tKdv').value = 0;
    document.getElementById('tKdvDahil').checked = false;
    if (_tfd.value !== 'faturasiz') TP_FATURA_DURUM_ONCEKI = _tfd.value;
    _tfd.value = 'faturasiz';
  } else if (TP_FATURA_DURUM_ONCEKI) {
    _tfd.value = TP_FATURA_DURUM_ONCEKI;
    TP_FATURA_DURUM_ONCEKI = null;
'''),
    ('templates/stok.html', 'US2 · templates/stok.html blok 11',
     r'''  document.getElementById('duzFiyatBirim').value = s.fiyat_birim || (s.tip === 'BLOK' ? 'ton' : 'm2');
''',
     r'''  /* US2: üretilen malda etiket "Üretim Maliyeti". Aynı alanın iki
     ekranda iki adı olmasın. */
  const _dfe = document.getElementById('duzFiyatEtiket');
  if (_dfe) _dfe.textContent = (s.kaynak === 'uretim')
    ? 'Üretim Maliyeti' : 'Alış Fiyatı';
  document.getElementById('duzFiyatBirim').value = s.fiyat_birim || (s.tip === 'BLOK' ? 'ton' : 'm2');
'''),
    ('tests/test_kritik.py', 'US2 · tests/test_kritik.py blok 1',
     r'''    assert 'id="grupEkleAlan"' in m, 'grup ekle düğmesi miktar satırında değil'
''',
     r'''    assert 'id="grupEkleAlan"' in m, 'grup ekle düğmesi miktar satırında değil'


# ══════════════════════════════════════════════════════════════════
#  US2 · ÜRETİLEN MALIN "ALIŞ FİYATI" OLMAZ — AMA MALİYETİ OLUR
#
#  Bahadır sordu: "kaynak üretim seçilince Alış Fiyatı olmalı mı?"
#  Ölçüldü — alan KALMALI, adı değişmeli.
#
#  Sunucu üretimde alış tipini NULL, KDV'yi 0, fatura durumunu zorla
#  'faturasiz' yapıyor ve tedarikçi cari hareketi hiç doğmuyor. Ama
#  FİYATI saklıyor ve matrahı ondan kuruyor. İki üretim bloğu açıp
#  ikisini de 10.000 USD'ye sattım:
#
#      girilen bedel   kaydedilen matrah   satış maliyeti   kâr
#      —                        0            1,00 $      9.999,00 $
#      300 $/ton            6.000 $      6.001,00 $      3.999,00 $
#
#  Yani alan kaldırılsa ya da boş bırakılsa, kendi ocağından çıkan
#  bloğun maliyeti HİÇBİR YERDE olmaz ve kâr 6.000 $ şişer.
#
#  Ekran ayrıca sunucunun yaptığının TERSİNİ söylüyordu: üretimde
#  "Fatura Durumu: Faturalı" seçili duruyor ve altındaki not
#  "tedarikçi cariye borç işlenir" diyordu.
# ══════════════════════════════════════════════════════════════════

def test_us2_uretimde_fiyat_alani_duruyor_adi_degisiyor():
    """Alan silinmemeli — silinirse üretim maliyeti kaybolur."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/stok.html'),
                 encoding='utf-8').read()
    # Alanın kendisi hiçbir koşulda gizlenmiyor.
    assert "getElementById('sFiyat').style.display" not in m, \
        'fiyat alanı gizleniyor — üretim maliyeti kaybolur'
    assert 'id="sFiyatEtiket"' in m, 'fiyat etiketi kimliksiz'
    assert "_fe.innerHTML = uretim" in m, 'etiket kaynağa göre değişmiyor'
    assert 'Üretim Maliyeti' in m, 'üretim adı yok'

    # Aynı alan düzenleme modalında ve stok kartında da doğru adla.
    assert "_dfe.textContent = (s.kaynak === 'uretim')" in m, \
        'düzenleme modalında etiket kaynağa bakmıyor'
    assert "alan(s.kaynak === 'uretim' ? 'Üretim Maliyeti' : 'Alış Fiyatı'" in m, \
        'stok kartında etiket kaynağa bakmıyor'


def test_us2_uretimde_ekran_sunucunun_yaptigini_soyluyor():
    """Üretimde fatura alanları gizli, not doğru şeyi söylüyor.

    Sunucu `_fatura_durumu = 'faturasiz'` diye ZORLUYOR; ekran
    "Faturalı" gösterip "tedarikçi cariye borç işlenir" diyordu."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/stok.html'),
                 encoding='utf-8').read()
    for _id in ('sFaturaDurumAlan', 'sFaturaNoAlan'):
        assert f'id="{_id}"' in m, f'{_id} kimliksiz — gizlenemez'
        assert f"_gos('{_id}', !uretim)" in m, f'{_id} üretimde gizlenmiyor'
    assert 'Üretimde tedarikçi borcu, fatura ve KDV yok' in m, \
        'üretim notu yok'
    # Nakliye işaretinin adı da üretimde değişiyor (toplu form gibi).
    assert "? 'Maliyete nakliye dahil' : 'Alış fiyatına nakliye dahil'" in m, \
        'nakliye etiketi üretimde düzeltilmiyor'


def test_us2_fatura_durumu_secimi_sessizce_degismiyor():
    """Üretime geçip geri dönünce seçim geri gelmeli.

    'Faturalı' ile 'Faturasız' arasındaki fark tedarikçiye borç
    yazılıp yazılmamasıdır — sessizce değişmesi en olmayacak şey.
    İki formda da aynı kusur vardı; ikisi birden düzeltildi."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/stok.html'),
                 encoding='utf-8').read()
    for _d in ('FATURA_DURUM_ONCEKI', 'TP_FATURA_DURUM_ONCEKI'):
        assert f'let {_d} = null;' in m, f'{_d} tanımlı değil'
        assert f'{_d} = _' in m, f'{_d} hiç yazılmıyor'
        assert f'if ({_d})' in m or f'else if ({_d})' in m, \
            f'{_d} hiç geri yüklenmiyor'


def test_us2_denetim_betigi_var_ve_salt_okunur():
    """Maliyeti olmayan üretim stoklarını bulan betik yazmamalı."""
    import io as _io
    _y = os.path.join(KOK, 'denetim_uretim_maliyet.py')
    assert os.path.exists(_y), 'denetim betiği yok'
    _m = _io.open(_y, encoding='utf-8').read()
    for _yasak in ('db.session.commit', 'db.session.add',
                   'db.session.delete'):
        assert _yasak not in _m, f'salt okunur olmalı ama {_yasak} var'
'''),
]

TAM_ICERIK = {
    'denetim_uretim_maliyet.py':
        'IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwojIC0qLSBjb2Rpbmc6IHV0Zi04IC0qLQoiIiIKTUFMxLBZRVTEsCBPTE1BWUFOIMOcUkVUxLBNIFNUT0tMQVJJIOKAlCBTQUxUIE9LVU5VUiBERU5FVMSwTQo9PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09CgpLYXluYcSfxLEgIsO8cmV0aW0iIG9sYW4gYW1hIGFsxLHFny/DvHJldGltIGJlZGVsaSBnaXJpbG1lbWnFnyBzdG9rbGFyxLEKYnVsdXIuIELDtnlsZSBiaXIgc3Rva3RhIG1hbGl5ZXQgWUFMTklaQ0Egc29ucmFkYW4gZWtsZW5lbiBnaWRlcgprYWxlbWxlcmluZGVuIGliYXJldCBrYWzEsXI7IHNhdMSxbMSxcnNhIGvDonIgb2xkdcSfdW5kYW4gYsO8ecO8ayBnw7Zyw7xuw7xyLgoKw5ZMw4fDnExEw5wgKGRlbmVtZSB2ZXJpc2l5bGUpOiBheW7EsSAxMC4wMDAgVVNEJ2xpayBzYXTEscWfLAogIMK3IGJlZGVsaSBnaXJpbG1lbWnFnyDDvHJldGltIGJsb8SfdW5kYSAgIGvDonIgOS45OTkgVVNECiAgwrcgNi4wMDAgVVNEIGJlZGVsbGkgw7xyZXRpbSBibG/En3VuZGEgICBrw6JyIDMuOTk5IFVTRAoKQnUgYmV0aWsgSMSww4dCxLBSIMWeRVkgWUFaTUFaLiBZYWxuxLF6IG9rdXIgdmUgbGlzdGVsZXIuCgpLVUxMQU5JTQotLS0tLS0tLQogIHZlbnYvYmluL3B5dGhvbiBkZW5ldGltX3VyZXRpbV9tYWxpeWV0LnB5CiAgdmVudi9iaW4vcHl0aG9uIGRlbmV0aW1fdXJldGltX21hbGl5ZXQucHkgLS1zYXRpbG1pcyAgICMgeWFsbsSxeiBzYXTEsWxtxLHFn2xhcgoiIiIKaW1wb3J0IG9zCmltcG9ydCBzeXMKCnN5cy5wYXRoLmluc2VydCgwLCBvcy5wYXRoLmRpcm5hbWUob3MucGF0aC5hYnNwYXRoKF9fZmlsZV9fKSkpCm9zLmVudmlyb24uc2V0ZGVmYXVsdCgnTUlMRVNUT05FX0FDSUxJU19BVExBJywgJzEnKQoKaW1wb3J0IGZsYXNrX2FwcCBhcyBmYSAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIyBub3FhOiBFNDAyCmZyb20gbW9kZWxzIGltcG9ydCAoZGIsIEJsb2tTdG9rLCBQbGFrYVN0b2ssIEViYXRsaVN0b2ssICAjIG5vcWE6IEU0MDIKICAgICAgICAgICAgICAgICAgICBTYXRpc0theWRpLCBNYWxpeWV0KQoKWUFMTklaX1NBVElMTUlTID0gJy0tc2F0aWxtaXMnIGluIHN5cy5hcmd2ClRJUExFUiA9ICgoJ0JMT0snLCBCbG9rU3RvaywgJ2Jsb2tfbm8nKSwKICAgICAgICAgICgnUExBS0EnLCBQbGFrYVN0b2ssICdibG9rX25vJyksCiAgICAgICAgICAoJ0VCQVRMSScsIEViYXRsaVN0b2ssICdrYXNhX25vJykpCgoKZGVmIF9iZWRlbChzKToKICAgICIiIlN0b8SfdW4gS0VORMSwIGJlZGVsaSDigJQgbWF0cmFoIHZhcnNhIG8sIHlva3NhIGZpeWF0IHggw7Zsw6fDvC4iIiIKICAgIG1hdHJhaCA9IGZsb2F0KGdldGF0dHIocywgJ21hdHJhaCcsIDApIG9yIDApCiAgICBpZiBtYXRyYWggPiAwOgogICAgICAgIHJldHVybiBtYXRyYWgKICAgIGZpeWF0ID0gZmxvYXQoZ2V0YXR0cihzLCAnYWxpc19maXlhdGknLCAwKSBvciAwKQogICAgaWYgbm90IGZpeWF0OgogICAgICAgIHJldHVybiAwLjAKICAgIGJpcmltID0gKGdldGF0dHIocywgJ2FsaXNfZml5YXRfYmlyaW0nLCBOb25lKSBvciAnJykubG93ZXIoKQogICAgb2xjdSA9IHsndG9uJzogZ2V0YXR0cihzLCAndG9uYWonLCAwKSwKICAgICAgICAgICAgJ20zJzogZ2V0YXR0cihzLCAnaGFjaW1fbTMnLCAwKSwKICAgICAgICAgICAgJ20yJzogZ2V0YXR0cihzLCAnbWV0cmFqX20yJywgMCksCiAgICAgICAgICAgICdzcWZ0JzogZ2V0YXR0cihzLCAnbWV0cmFqX20yJywgMCl9LmdldChiaXJpbSwgMCkKICAgIHJldHVybiBmaXlhdCAqIGZsb2F0KG9sY3Ugb3IgMCkKCgpkZWYgbWFpbigpOgogICAgd2l0aCBmYS5hcHAuYXBwX2NvbnRleHQoKToKICAgICAgICBwcmludCgnPScgKiA3MikKICAgICAgICBwcmludCgnICBLQVlOQcSeSSDDnFJFVMSwTSwgQkVERUzEsCBHxLBSxLBMTUVNxLDFniBTVE9LTEFSJykKICAgICAgICBwcmludCgnPScgKiA3MikKICAgICAgICB0b3BsYW0sIHNhdGlsbWlzX3phcmFyID0gMCwgMC4wCiAgICAgICAgZm9yIGFkLCBNb2RlbCwgbm9fYWxhbiBpbiBUSVBMRVI6CiAgICAgICAgICAgIGtheWl0bGFyID0gW3MgZm9yIHMgaW4gTW9kZWwucXVlcnkuZmlsdGVyKAogICAgICAgICAgICAgICAgTW9kZWwua2F5bmFrID09ICd1cmV0aW0nKS5hbGwoKSBpZiBfYmVkZWwocykgPD0gMF0KICAgICAgICAgICAgaWYgWUFMTklaX1NBVElMTUlTOgogICAgICAgICAgICAgICAga2F5aXRsYXIgPSBbcyBmb3IgcyBpbiBrYXlpdGxhcgogICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgKHMuZHVydW0gb3IgJycpID09ICdTYXRpbGRpJ10KICAgICAgICAgICAgaWYgbm90IGtheWl0bGFyOgogICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgcHJpbnQoKQogICAgICAgICAgICBwcmludChmJ+KUgOKUgCB7YWR9IMK3IHtsZW4oa2F5aXRsYXIpfSBrYXnEsXQgJyArICfilIAnICogMzApCiAgICAgICAgICAgIGZvciBzIGluIGtheWl0bGFyOgogICAgICAgICAgICAgICAgdG9wbGFtICs9IDEKICAgICAgICAgICAgICAgIGVrID0gZGIuc2Vzc2lvbi5xdWVyeSgKICAgICAgICAgICAgICAgICAgICBkYi5mdW5jLnN1bShNYWxpeWV0LnVzZF9rYXJzaWxpaykpLmZpbHRlcigKICAgICAgICAgICAgICAgICAgICAgICAgTWFsaXlldC5iYWdsYW50aV9pZCA9PSBzLmlkLAogICAgICAgICAgICAgICAgICAgICAgICBNYWxpeWV0LmFrdGlmLmlzXyhUcnVlKSkuc2NhbGFyKCkgb3IgMAogICAgICAgICAgICAgICAgc2sgPSBTYXRpc0theWRpLnF1ZXJ5LmZpbHRlcl9ieShzdG9rX2lkPXMuaWQpLmZpcnN0KCkKICAgICAgICAgICAgICAgIHNhdGlyID0gKGYnICB7cy5pZDo8MjJ9IHtnZXRhdHRyKHMsIG5vX2FsYW4sICIiKSBvciAi4oCUIjo8MTR9JwogICAgICAgICAgICAgICAgICAgICAgICAgZicgeyhzLmNpbnMgb3IgIiIpWzoxOF06PDE4fScKICAgICAgICAgICAgICAgICAgICAgICAgIGYnIGR1cnVtIHtzLmR1cnVtIG9yICLigJQiOjw5fScKICAgICAgICAgICAgICAgICAgICAgICAgIGYnIGVrIG1hbGl5ZXQge2Zsb2F0KGVrKTo+OSwuMmZ9ICQnKQogICAgICAgICAgICAgICAgaWYgc2s6CiAgICAgICAgICAgICAgICAgICAga2FyID0gZmxvYXQoc2sua2FyX3VzZCBvciAwKQogICAgICAgICAgICAgICAgICAgIHNhdGlsbWlzX3phcmFyICs9IGthcgogICAgICAgICAgICAgICAgICAgIHNhdGlyICs9IGYnICBTQVRJTERJIMK3IGthecSxdGzEsSBrw6JyIHtrYXI6PjEwLC4yZn0gJCcKICAgICAgICAgICAgICAgIHByaW50KHNhdGlyKQoKICAgICAgICBwcmludCgpCiAgICAgICAgcHJpbnQoJz0nICogNzIpCiAgICAgICAgaWYgbm90IHRvcGxhbToKICAgICAgICAgICAgcHJpbnQoJyAg4pyTIEJlZGVsaSBnaXJpbG1lbWnFnyDDvHJldGltIHN0b8SfdSB5b2suJykKICAgICAgICBlbHNlOgogICAgICAgICAgICBwcmludChmJyAge3RvcGxhbX0gc3Rva3RhIMO8cmV0aW0gYmVkZWxpIFlPSy4nKQogICAgICAgICAgICBpZiBzYXRpbG1pc196YXJhcjoKICAgICAgICAgICAgICAgIHByaW50KGYnICBCdW5sYXJkYW4gc2F0xLFsbcSxxZ8gb2xhbmxhcsSxbiBrYXnEsXRsxLEga8OicsSxJwogICAgICAgICAgICAgICAgICAgICAgZicge3NhdGlsbWlzX3phcmFyOiwuMmZ9IFVTRCDigJQgw7xyZXRpbSBiZWRlbGknCiAgICAgICAgICAgICAgICAgICAgICBmJyBnaXJpbHNleWRpIGJ1IHJha2FtIETDnMWeRUNFS1TEsC4nKQogICAgICAgICAgICBwcmludCgpCiAgICAgICAgICAgIHByaW50KCcgIETDvHplbHRtZWsgacOnaW46IERlcG8g4oaSIFN0b2sg4oaSIGlsZ2lsaSBrYXnEsXQg4oaSJykKICAgICAgICAgICAgcHJpbnQoJyAgRMO8emVubGUg4oaSICLDnHJldGltIE1hbGl5ZXRpIiBhbGFuxLFuYSBiaXJpbSBiZWRlbGknKQogICAgICAgICAgICBwcmludCgnICBnaXIuIFNhdMSxbG3EscWfbGFyxLFuIGvDonLEsSBrYXlkZWRpbmNlIHRhemVsZW5pci4nKQogICAgICAgIHByaW50KCc9JyAqIDcyKQogICAgcmV0dXJuIDAKCgppZiBfX25hbWVfXyA9PSAnX19tYWluX18nOgogICAgc3lzLmV4aXQobWFpbigpKQo=',
}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA US2 — ÜRETİLEN MALIN "ALIŞ FİYATI" OLMAZ, MALİYETİ OLUR')
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
        print('    python3 yama_us2.py            # rapor')
        print('    python3 yama_us2.py --uygula')
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
        print('  ⊙ Yama US2 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_us2.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_us2'
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
    print('    Depo -> Stok -> Yeni Stok -> Kaynak: Uretim.')
    print('    "Alis Fiyati" -> "Uretim Maliyeti", fatura alanlari')
    print('    gizleniyor, not dogru seyi soyluyor.')
    print()
    print('  BUNU BIR CALISTIR, CIKTIYI BANA GONDER:')
    print('    venv/bin/python denetim_uretim_maliyet.py')
    print('    (salt okunur — bedeli girilmemis uretim stoklarini')
    print('     listeler; satilmis olanlarin kari sismis olabilir)')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

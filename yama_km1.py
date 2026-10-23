#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA KM1 — KESİLEN TAŞIN MENŞEİ DEĞİŞMEZ
=========================================

ÖNKOŞUL: **yama_ks1.py uygulanmış olmalı.** Betik denetliyor.

Sen "menşe detaylarına bak" dedin. Baktım. Bu, oturumdaki en ağır
bulgu.

── NE OLUYORDU ──

  Kesim, hedef stoğun `mense` alanını HİÇ yazmıyordu. Yazılmayınca
  model varsayılanı devreye giriyor: **'TURKIYE'**.

      blok  K6462   menşe ARNAVUTLUK   (ALBSTONE1 SHPK, Arnavutluk)
      plaka K6462-17 menşe TURKIYE     ← uydurulmuş

  Bu kozmetik DEĞİL. `mense` ticari faturaya ve kasa etiketine
  basılıyor:

    · commercial_invoice_print.html — tüm kalemlerin menşei TURKIYE
      ise faturaya **"the goods are of Turkish origin"** yazıyor
    · etiket_print.html — "Materials of Origin" alanı

  Yani Arnavutluk mermerinden kesilmiş plakalar, ticari faturada ve
  kasa etiketinde **Türk malı olarak beyan ediliyordu.**

── NE DEĞİŞTİ ──

  Kesim artık menşei kaynağından taşıyor. İki hedef tipi (PLAKA ve
  EBATLI) TEK yardımcıdan geçiyor (`_kesim_mense`): birinde
  düzeltip ötekinde unutmak, hatanın kendisiyle aynı sınıftı.

  Kaynağın menşei boşsa yine 'TURKIYE' — ama artık BİLİNÇLİ bir
  varsayılan, unutulmuş bir alan değil.

── BİR DE ALAN ALAN TARADIM ──

  "Menşe unutulmuşsa başkası da unutulmuş olabilir" diye tahmin
  yürütmek yerine saydım: her alanı dolu bir blok kesildi ve hedefin
  alanları kaynakla karşılaştırıldı.

      uretici · cins · doviz · konum · fatura_durumu   taşınıyor ✓
      mense                                            TAŞINMIYORDU → düzeltildi
      alis_tipi                                        taşınmıyor — kesim bir ALIŞ değil (KK1)
      fatura_no · alis_tarihi                          taşınmıyor — plakanın kendi faturası yok
      kaynak                                           'kesim' yazılıyor (KK1)

  Yani menşe tek başına kalmış. Gerekçeler artık kodda yazılı.

── BİR ETİKET ÇAKIŞMASI DÜZELTİLDİ ──

  Dün "KS1" etiketini kullanmıştım; oysa stok.html'de KASKAD SÜZGEÇ
  için zaten bir KS1 vardı. Aynı dosyada iki ayrı KS1, ileride
  arayanı yanıltır. Benimkiler **KK1** oldu (Kesim Kaynağı).

── GEÇMİŞ İÇİN AYRI BETİK ──

  Yama bundan sonrasını düzeltir. MEVCUT plakaların menşei hâlâ
  yanlış:

      venv/bin/python goc_kesim_mense.py            # RAPOR
      venv/bin/python goc_kesim_mense.py --uygula

  Her kesim hedefini kaynak bloğunun menşeine çeker. Dokunduğu tek
  alan `mense`. Raporu gruplayarak gösteriyor ("ARNAVUTLUK →
  TURKIYE, 24 kayıt") — 66 satır okumana gerek yok.

  **Bunu çalıştırdıktan sonra daha önce bastığın ticari faturaları
  ve etiketleri gözden geçir.** Yazılım geçmişe basılmış kâğıdı
  düzeltemez.

── DOĞRULANDI ──
  ARNAVUTLUK bloğu kesildi → iki plaka da ARNAVUTLUK.
  Göç betiği: önce rapor (2 kayıt), sonra uygula, ikisi de düzeldi.
  Yeni test METİN değil DAVRANIŞ bakıyor — blok kesiyor, hedefin
  alanlarını kaynakla karşılaştırıyor; unutulan bir sonraki alan
  da orada patlar.
  240 test geçti (237 + 3). firma · js · form · akış · zincir
  denetimleri temiz.

DOSYALAR
--------
  flask_app.py           menşe taşıma · ortak kapı · etiket düzeltmesi
  goc_kesim_mense.py     YENİ · geçmiş kayıtlar için göç
  tests/test_kritik.py   3 yeni test

Şema yok, göç dosyası yok (betik veri yazar, tablo değiştirmez).

KULLANIM
--------
  python3 yama_km1.py            # RAPOR
  python3 yama_km1.py --uygula
  sudo systemctl restart milestone-erp
  venv/bin/python goc_kesim_mense.py
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
    'flask_app.py': 'KM1 · MENSE KAYNAKTAN GELIR',
    'goc_kesim_mense.py': 'KESİM STOKLARININ MENŞEİNİ KAYNAĞINDAN DÜZELT',
    'tests/test_kritik.py': 'def test_km1_kesim_menseyi_kaynaktan_tasir',
}
ONKOSUL = {
    'flask_app.py': "kaynak='kesim',",
    'tests/test_kritik.py': 'def test_ks1_kesim_kaynagi_yaziyor',
}
TAM_YAZILAN = ['goc_kesim_mense.py']

DEGISIKLIKLER = [
    ('flask_app.py', 'KM1 · flask_app.py blok 1',
     r'''            # ── KS1 · BOŞ ALANA DEĞER UYDURULMAZ ──
''',
     r'''            # ── KK1 · BOŞ ALANA DEĞER UYDURULMAZ ──
'''),
    ('flask_app.py', 'KM1 · flask_app.py blok 2',
     r'''        # ── KS1 · KESİMDEN ÇIKAN STOK FATURALANDIRILAMAZ ──
''',
     r'''        # ── KK1 · KESİMDEN ÇIKAN STOK FATURALANDIRILAMAZ ──
'''),
    ('flask_app.py', 'KM1 · flask_app.py blok 3',
     r'''    @app.route('/api/kesim', methods=['POST'])
''',
     r'''    def _kesim_mense(kaynak):
        """Kesim hedefinin mensei — KAYNAGIN mensei.

        ── KM1 · NEDEN AYRI BIR FONKSIYON ──
        Kesim hedef stogu olustururken alanlari TEK TEK yaziyordu ve
        `mense` unutulmustu. Ayni unutma iki yerde (PLAKA ve EBATLI)
        ayri ayri olabilirdi; tek kapidan gecirince ikisi birden
        duzeliyor ve bir sonraki hedef tipi de ayni kapidan geciyor.

        Kaynagin mensei bossa 'TURKIYE' — model varsayilaniyla ayni,
        ama artik BILINCLI bir varsayilan, unutulmus bir alan degil.

        TASINMAYANLAR ve gerekceleri (olculdu, listelendi):
          alis_tipi    — kesim bir ALIS degil; KK1'de NULL birakildi
          fatura_no    — plakanin kendi faturasi yok, blogunki var
          alis_tarihi  — plaka satin alinmadi
          kaynak       — 'kesim' yaziliyor (KK1)
        """
        return (getattr(kaynak, 'mense', None) or 'TURKIYE')

    @app.route('/api/kesim', methods=['POST'])
'''),
    ('flask_app.py', 'KM1 · flask_app.py blok 4',
     r'''                            # KS1: bu plakayi KIMSE SATIN ALMADI.
                            # `kaynak` hic yazilmiyordu ve model
                            # varsayilani 'satinalma' devreye giriyordu.
                            kaynak='kesim',
''',
     r'''                            # KK1 (eski adiyla KS1 — o ad stok.html'de
                            # KASKAD SUZGEC icin zaten kullaniliyordu):
                            # bu plakayi KIMSE SATIN ALMADI. `kaynak` hic
                            # yazilmiyordu, model varsayilani 'satinalma'
                            # devreye giriyordu.
                            kaynak='kesim',
                            # ── KM1 · MENSE KAYNAKTAN GELIR ──
                            # Yazilmayinca model varsayilani 'TURKIYE'
                            # devreye giriyordu: ARNAVUTLUK mensesli
                            # blokdan kesilen plaka TURK MALI olarak
                            # kaydoluyordu. Bu deger TICARI FATURAYA ve
                            # ETIKETE BASILIYOR ("the goods are of Turkish
                            # origin"), yani yanlis mense beyani.
                            # Bahadir yakaladi; K6462 (ARNAVUTLUK) bunun
                            # canli ornegiydi.
                            mense=_kesim_mense(ana_kaynak),
'''),
    ('flask_app.py', 'KM1 · flask_app.py blok 5',
     r'''                            kaynak='kesim',          # KS1 — bkz. plaka
''',
     r'''                            kaynak='kesim',          # KK1 — bkz. plaka
                            mense=_kesim_mense(ana_kaynak),   # KM1
'''),
    ('tests/test_kritik.py', 'KM1 · tests/test_kritik.py blok 1',
     r'''            _govde = _r[_p.start():_p.start() + 1600]
            _govde = _govde[:_govde.index('db.session.add')]
''',
     r'''            # Sabit pencere KULLANMA: KM1'in menşe yorumu eklenince
            # gövde 1600 karakteri aştı ve test kodu değil KENDİNİ
            # kırdı. Sınır bir sonraki `db.session.add`.
            _son = _r.index('db.session.add', _p.start())
            _govde = _r[_p.start():_son]
'''),
    ('tests/test_kritik.py', 'KM1 · tests/test_kritik.py blok 2',
     r'''    assert _atamalar <= {'kaynak'}, f'başka alana da yazıyor: {_atamalar}'
''',
     r'''    assert _atamalar <= {'kaynak'}, f'başka alana da yazıyor: {_atamalar}'


# ══════════════════════════════════════════════════════════════════
#  KM1 · KESİLEN TAŞIN MENŞEİ DEĞİŞMEZ
#
#  Kesim, hedef stoğun `mense` alanını hiç yazmıyordu; model
#  varsayılanı devreye girip 'TURKIYE' kalıyordu. ARNAVUTLUK
#  menşeli K6462 bloğundan kesilen plakalar TÜRK MALI olarak
#  kaydolmuştu — Bahadır stok kartında yakaladı.
#
#  Bu kozmetik değil: `mense` TİCARİ FATURAYA ve kasa ETİKETİNE
#  basılıyor. Fatura şablonu tüm kalemler TURKIYE ise "the goods
#  are of Turkish origin" yazıyor.
#
#  Aşağıdaki test METİN değil DAVRANIŞ bakıyor: bir blok kesiliyor
#  ve hedefin alanları kaynakla karşılaştırılıyor. Unutulan bir
#  sonraki alan da burada patlar.
# ══════════════════════════════════════════════════════════════════

def test_km1_kesim_menseyi_kaynaktan_tasir():
    """ARNAVUTLUK bloğundan kesilen plaka ARNAVUTLUK olmalı."""
    from models import PlakaStok, KesimDetay
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BLK-KM1', firma_id=1, blok_no='KM1', cins='KMTEST',
            uretici='ALBSTONE1 SHPK', mense='ARNAVUTLUK',
            boy=310, yukseklik=155, en=50, hacim_m3=2.4, tonaj=6.78,
            alis_fiyati=200, alis_fiyat_birim='ton', doviz='EUR',
            durum='Serbest', giris_tarihi=date(2026, 9, 14),
            kaynak='satinalma', alis_tipi='ithalat'))
        db.session.commit()

    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': ['BLK-KM1'],
        'kesim_tarihi': '2026-10-18',
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'KMTEST', 'boy': 302,
                      'yukseklik': 151, 'kalinlik': 2, 'adet': 2,
                      'miktar_m2': 4.56}]})
    assert r.status_code == 200, r.get_json()

    with fa.app.app_context():
        hedefler = [d.hedef_stok_id for d in
                    KesimDetay.query.filter_by(hedef_tip='PLAKA').all()]
        plakalar = PlakaStok.query.filter(
            PlakaStok.id.in_(hedefler),
            PlakaStok.cins == 'KMTEST').all()
        assert len(plakalar) == 2, len(plakalar)
        for p in plakalar:
            assert p.mense == 'ARNAVUTLUK', \
                f'{p.id} menşei {p.mense!r} — ticari faturaya bu basılır'
            # KK1 ile birlikte gelenler de yerinde dursun.
            assert p.kaynak == 'kesim', f'{p.id} kaynak {p.kaynak!r}'
            assert p.uretici == 'ALBSTONE1 SHPK'
            assert (p.doviz or '').upper() == 'EUR'


def test_km1_mense_tek_kapidan_geciyor():
    """Menşe iki hedef tipinde ayrı ayrı yazılmasın.

    PLAKA'da düzeltip EBATLI'da unutmak, hatanın kendisiyle aynı
    sınıf. İkisi de tek yardımcıdan geçiyor."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'flask_app.py'),
                 encoding='utf-8').read().replace('\r\n', '\n')
    assert 'def _kesim_mense(' in m, 'ortak menşe kapısı yok'
    _r = m[m.index("@app.route('/api/kesim', methods=['POST'])"):]
    _r = _r[:_r.index("@app.route('/api/kesim/<kesim_id>', methods=['DELETE'])")]
    assert _r.count('mense=_kesim_mense(ana_kaynak)') == 2, \
        'her iki hedef tipi de ortak kapıdan geçmiyor'


def test_km1_mense_gocu_var_ve_rapor_kipinde_yazmaz():
    """Geçmiş kayıtlar için göç betiği — varsayılan RAPOR."""
    import io as _io, re as _re
    _y = os.path.join(KOK, 'goc_kesim_mense.py')
    assert os.path.exists(_y), 'menşe göç betiği yok'
    _m = _io.open(_y, encoding='utf-8').read()
    assert "UYGULA = '--uygula' in sys.argv" in _m, '--uygula kapısı yok'
    assert 'if UYGULA:' in _m, 'rapor kipi yazıyor olabilir'
    _atamalar = set(_re.findall(r'\bhedef\.(\w+) =', _m))
    assert _atamalar <= {'mense'}, f'başka alana da yazıyor: {_atamalar}'
'''),
]

TAM_ICERIK = {
    'goc_kesim_mense.py':
        'IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwojIC0qLSBjb2Rpbmc6IHV0Zi04IC0qLQoiIiIKS0VTxLBNIFNUT0tMQVJJTklOIE1FTsWeRcSwTsSwIEtBWU5BxJ5JTkRBTiBEw5xaRUxUCj09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT0KCktlc2ltLCBvbHXFn3R1cmR1xJ91IHN0b8SfdW4gYG1lbnNlYCBhbGFuxLFuxLEgaGnDpyB5YXptxLF5b3JkdTsgbW9kZWwKdmFyc2F5xLFsYW7EsSBkZXZyZXllIGdpcmlwICdUVVJLSVlFJyBrYWzEsXlvcmR1LiBBUk5BVlVUTFVLIG1lbsWfZWxpCmJpciBibG9rdGFuIGtlc2lsZW4gcGxha2EgVMOcUksgTUFMSSBvbGFyYWsga2F5ZG9sdXlvcmR1LgoKTkVERU4gw5ZORU1MxLA6IGJ1IGRlxJ9lciB0aWNhcmkgZmF0dXJheWEgdmUga2FzYSBldGlrZXRpbmUgQkFTSUxJWU9SLgpGYXR1cmEgxZ9hYmxvbnUgdMO8bSBrYWxlbWxlcmluIG1lbsWfZWkgVFVSS0lZRSBpc2UKInRoZSBnb29kcyBhcmUgb2YgVHVya2lzaCBvcmlnaW4iIHlhesSxeW9yLiBZYW5pIHlhbmzEscWfIG1lbsWfZSBiZXlhbsSxLgoKWWFtYSBidW51IGJ1bmRhbiBzb25yYXPEsSBpw6dpbiBkw7x6ZWx0dGkuIEJ1IGJldGlrIEdFw4dNxLDFnsSwIGTDvHplbHRpcjoKaGVyIGtlc2ltIGhlZGVmaW5pIGtheW5hayBibG/En3VudW4gbWVuxZ9laW5lIMOnZWtlci4KCkRva3VudWxhbiB0ZWsgYWxhbiBgbWVuc2VgLiBCYcWfa2EgaGnDp2JpciDFn2V5IGRlxJ9pxZ9tZXouCgpLVUxMQU5JTQotLS0tLS0tLQogIHZlbnYvYmluL3B5dGhvbiBnb2Nfa2VzaW1fbWVuc2UucHkgICAgICAgICAgICAgICMgUkFQT1Ig4oCUIHlhem1hegogIHZlbnYvYmluL3B5dGhvbiBnb2Nfa2VzaW1fbWVuc2UucHkgLS11eWd1bGEgICAgICMgeWF6YXIKIiIiCmltcG9ydCBvcwppbXBvcnQgc3lzCgpzeXMucGF0aC5pbnNlcnQoMCwgb3MucGF0aC5kaXJuYW1lKG9zLnBhdGguYWJzcGF0aChfX2ZpbGVfXykpKQpvcy5lbnZpcm9uLnNldGRlZmF1bHQoJ01JTEVTVE9ORV9BQ0lMSVNfQVRMQScsICcxJykKCmltcG9ydCBmbGFza19hcHAgYXMgZmEgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIyBub3FhOiBFNDAyCmZyb20gbW9kZWxzIGltcG9ydCAoZGIsIEJsb2tTdG9rLCBQbGFrYVN0b2ssIEViYXRsaVN0b2ssICAgICMgbm9xYTogRTQwMgogICAgICAgICAgICAgICAgICAgIEtlc2ltLCBLZXNpbURldGF5KQoKVVlHVUxBID0gJy0tdXlndWxhJyBpbiBzeXMuYXJndgpNT0RFTCA9IHsnQkxPSyc6IEJsb2tTdG9rLCAnUExBS0EnOiBQbGFrYVN0b2ssICdFQkFUTEknOiBFYmF0bGlTdG9rfQoKCmRlZiBfa2F5bmFrX21lbnNlKGtlc2ltKToKICAgICIiIktlc2ltaW4ga2F5bmFrIHN0b8SfdW51biBtZW7Fn2VpLiIiIgogICAgaWYgbm90IGtlc2ltIG9yIG5vdCBrZXNpbS5rYXluYWtfaWQ6CiAgICAgICAgcmV0dXJuIE5vbmUKICAgIGZvciBNb2RlbCBpbiAoQmxva1N0b2ssIFBsYWthU3RvaywgRWJhdGxpU3Rvayk6CiAgICAgICAgcyA9IGRiLnNlc3Npb24uZ2V0KE1vZGVsLCBrZXNpbS5rYXluYWtfaWQpCiAgICAgICAgaWYgczoKICAgICAgICAgICAgcmV0dXJuIGdldGF0dHIocywgJ21lbnNlJywgTm9uZSkgb3IgTm9uZQogICAgcmV0dXJuIE5vbmUKCgpkZWYgbWFpbigpOgogICAgd2l0aCBmYS5hcHAuYXBwX2NvbnRleHQoKToKICAgICAgICBwcmludCgnPScgKiA3MikKICAgICAgICBwcmludCgnICBLRVPEsE0gU1RPS0xBUklOSU4gTUVOxZ5FxLAnKQogICAgICAgIHByaW50KCcgIE1PRDogJyArICgnVVlHVUxBJyBpZiBVWUdVTEEgZWxzZSAnUkFQT1IgKHlhem1heiknKSkKICAgICAgICBwcmludCgnPScgKiA3MikKCiAgICAgICAga2VzaW1sZXIgPSB7ay5pZDogayBmb3IgayBpbiBLZXNpbS5xdWVyeS5hbGwoKX0KICAgICAgICBkZWdpc2VjZWssIGF5bmksIGtheW5ha3NpeiA9IFtdLCAwLCAwCgogICAgICAgIGZvciBkIGluIEtlc2ltRGV0YXkucXVlcnkuYWxsKCk6CiAgICAgICAgICAgIGlmIG5vdCBkLmhlZGVmX3N0b2tfaWQgb3IgZC5oZWRlZl90aXAgbm90IGluIE1PREVMOgogICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgaGVkZWYgPSBkYi5zZXNzaW9uLmdldChNT0RFTFtkLmhlZGVmX3RpcF0sIGQuaGVkZWZfc3Rva19pZCkKICAgICAgICAgICAgaWYgaGVkZWYgaXMgTm9uZToKICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgIGttID0gX2theW5ha19tZW5zZShrZXNpbWxlci5nZXQoZC5rZXNpbV9pZCkpCiAgICAgICAgICAgIGlmIG5vdCBrbToKICAgICAgICAgICAgICAgIGtheW5ha3NpeiArPSAxCiAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICBtZXZjdXQgPSBnZXRhdHRyKGhlZGVmLCAnbWVuc2UnLCBOb25lKSBvciAnJwogICAgICAgICAgICBpZiBtZXZjdXQgPT0ga206CiAgICAgICAgICAgICAgICBheW5pICs9IDEKICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgIGRlZ2lzZWNlay5hcHBlbmQoKGQuaGVkZWZfdGlwLCBoZWRlZiwgbWV2Y3V0LCBrbSkpCgogICAgICAgIGlmIGtheW5ha3NpejoKICAgICAgICAgICAgcHJpbnQoZicgIMK3IHtrYXluYWtzaXp9IGhlZGVmaW4ga2F5bmHEn8SxIGJ1bHVuYW1hZMSxIChzaWxpbm1pxZ8nCiAgICAgICAgICAgICAgICAgIGYnIG9sYWJpbGlyKSDigJQgZG9rdW51bG1hZMSxLicpCiAgICAgICAgaWYgYXluaToKICAgICAgICAgICAgcHJpbnQoZicgIMK3IHtheW5pfSBoZWRlZmluIG1lbsWfZWkgemF0ZW4gZG/En3J1LicpCgogICAgICAgIGlmIG5vdCBkZWdpc2VjZWs6CiAgICAgICAgICAgIHByaW50KCkKICAgICAgICAgICAgcHJpbnQoJyAg4pyTIETDvHplbHRpbGVjZWsgYmlyIMWfZXkgeW9rLicpCiAgICAgICAgICAgIHByaW50KCc9JyAqIDcyKQogICAgICAgICAgICByZXR1cm4gMAoKICAgICAgICAjIE1lbsWfZSBkZcSfacWfaW1sZXJpbmkgR1JVUExBWUFSQUsgZ8O2c3RlcjogNjYgc2F0xLFyIG9rdW5tYXosCiAgICAgICAgIyAiQVJOQVZVVExVSyDihpIgVFVSS0lZRSwgMjQga2F5xLF0IiBva3VudXIuCiAgICAgICAgZ3J1cGxhciA9IHt9CiAgICAgICAgZm9yIHRpcCwgaGVkZWYsIGVza2ksIHllbmkgaW4gZGVnaXNlY2VrOgogICAgICAgICAgICBncnVwbGFyLnNldGRlZmF1bHQoKHRpcCwgZXNraSBvciAnKGJvxZ8pJywgeWVuaSksIFtdKS5hcHBlbmQoaGVkZWYpCgogICAgICAgIHByaW50KCkKICAgICAgICBmb3IgKHRpcCwgZXNraSwgeWVuaSksIGtheWl0bGFyIGluIHNvcnRlZChncnVwbGFyLml0ZW1zKCkpOgogICAgICAgICAgICBwcmludChmJ+KUgOKUgCB7dGlwfSDCtyB7bGVuKGtheWl0bGFyKX0ga2F5xLF0ICcgKyAn4pSAJyAqIDI2KQogICAgICAgICAgICBwcmludChmJyAgIHtlc2tpfSAg4oaSICB7eWVuaX0nKQogICAgICAgICAgICBmb3IgaCBpbiBrYXlpdGxhcls6Nl06CiAgICAgICAgICAgICAgICBwcmludChmJyAgICAgIHtoLmlkfScpCiAgICAgICAgICAgIGlmIGxlbihrYXlpdGxhcikgPiA2OgogICAgICAgICAgICAgICAgcHJpbnQoZicgICAgICDigKYgdmUge2xlbihrYXlpdGxhcikgLSA2fSBrYXnEsXQgZGFoYScpCiAgICAgICAgICAgIHByaW50KCkKCiAgICAgICAgaWYgVVlHVUxBOgogICAgICAgICAgICBmb3IgX3RpcCwgaGVkZWYsIF9lc2tpLCB5ZW5pIGluIGRlZ2lzZWNlazoKICAgICAgICAgICAgICAgIGhlZGVmLm1lbnNlID0geWVuaQogICAgICAgICAgICBkYi5zZXNzaW9uLmNvbW1pdCgpCiAgICAgICAgICAgIHByaW50KCc9JyAqIDcyKQogICAgICAgICAgICBwcmludChmJyAg4pyTIHtsZW4oZGVnaXNlY2VrKX0ga2F5xLF0IGTDvHplbHRpbGRpLicpCiAgICAgICAgICAgIHByaW50KCcgIFRpY2FyaSBmYXR1cmEgdmUgZXRpa2V0IGFydMSxayBkb8SfcnUgbWVuxZ9laSBiYXNhci4nKQogICAgICAgICAgICBwcmludCgnICBEQUhBIMOWTkNFIEJBU0lMTUnFniBiZWxnZWxlcmkga29udHJvbCBldC4nKQogICAgICAgIGVsc2U6CiAgICAgICAgICAgIHByaW50KCc9JyAqIDcyKQogICAgICAgICAgICBwcmludChmJyAge2xlbihkZWdpc2VjZWspfSBrYXnEsXQgZMO8emVsdGlsZWNlay4gWWF6bWFrIGnDp2luOicpCiAgICAgICAgICAgIHByaW50KCcgICAgICB2ZW52L2Jpbi9weXRob24gZ29jX2tlc2ltX21lbnNlLnB5IC0tdXlndWxhJykKICAgICAgICBwcmludCgnPScgKiA3MikKICAgIHJldHVybiAwCgoKaWYgX19uYW1lX18gPT0gJ19fbWFpbl9fJzoKICAgIHN5cy5leGl0KG1haW4oKSkK',
}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA KM1 — KESİLEN TAŞIN MENŞEİ DEĞİŞMEZ')
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
        print('    python3 yama_km1.py            # rapor')
        print('    python3 yama_km1.py --uygula')
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
        print('  ⊙ Yama KM1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_km1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_km1'
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
    print('    2) venv/bin/python -m pytest tests/test_kritik.py -q')
    print()
    print('  SIMDI GECMISI DUZELT — MENSE FATURAYA BASILIYOR:')
    print('    venv/bin/python goc_kesim_mense.py            # RAPOR')
    print('    venv/bin/python goc_kesim_mense.py --uygula')
    print()
    print('    Dokundugu tek alan `mense`.')
    print()
    print('  SONRA: daha once BASILMIS ticari faturalari ve')
    print('    etiketleri gozden gecir. Yazilim gecmise basilmis')
    print('    kagidi duzeltemez.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

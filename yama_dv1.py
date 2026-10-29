#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA DV1 — FİYAT KENDİ PARA BİRİMİYLE YOLCULUK EDER
=====================================================

ÖNKOŞUL: **yama_kd1.py uygulanmış olmalı.** Betik denetliyor.
Şema değişikliği YOK, göç YOK. Yalnız `flask_app.py` ve testler.

Kullanım:
    python3 yama_dv1.py              # rapor, dosyalara dokunmaz
    python3 yama_dv1.py --uygula
    venv/bin/python -m pytest tests/test_kritik.py -q     # 299

═══ 1 · EUR PROFORMANIN KALEMLERİ USD DAMGALANIYORDU ═══

Kodda kalem dövizi belgeden alınmıyordu:

    doviz=k.get('doviz','USD')      ← belgenin dövizi değil, SABİT

Ekran kalem satırını `k.doviz || p.doviz` ile bastığı için EUR bir
proformada HER SATIRDA $ görünüyor, belgenin toplamı ise € yazıyordu.
Müşteriye giden belgede.

Sipariş tarafında aynı şey SAYIYA dönüşüyordu. Kalemler USD, sipariş
EUR; `_siparis_toplam_guncelle` kalemleri çevirmeden topluyor ve
sonucu siparişin döviziyle etiketliyordu. Kodda şöyle yazıyordu:

    # Şimdilik kalem dövizi sipariş dövizine eşit varsayılıyor.

Varsayım DENETLENMİYORDU. Ölçüldü:

    10.000 USD + 10.000 EUR  ->  sipariş "20.000 USD" yazıyor
    gerçeği 21.250 USD · fark 1.250 USD (%6)

ve bu sayı olduğu gibi faturaya (20.000 USD), cari harekete
(20.000 USD borç / 800.000 TRY) ve satış kaydına geçiyordu. Yani
müşteriye eksik fatura kesiliyor, cari eksik borçlanıyor, kâr
yanlış çıkıyordu.

ÇÖZÜM — İŞİN KURALI: fiyat kendi para birimiyle yolculuk eder.
Proformada 50 EUR ise siparişte de, faturada da, satış kaydında da
50 EUR'dur; hiçbir yerde çevrilmez.

Bunun gereği, kalem dövizinin BELGEDEN miras alınması. Artık tek
kapı var (`_kalem_doviz_denetle`) ve beş yazma ucu ondan geçiyor:
proforma ekle/güncelle, sipariş ekle/güncelle, sıcak satış. Kalem
bilerek farklı bir döviz taşıyorsa belge REDDEDİLİR ve sebebi
söylenir — çevirmek fiyatı değiştirmek, sessizce toplamak ise
yanlış sayı üretmek olurdu. Ticari faturanın tek para birimi olur;
üçüncü yol yok.

`_siparis_toplam_guncelle` içinde son çare bir denetim kaldı: eski
bir kayıt ya da bir betik karışık sipariş üretmişse, sessizce
yanlış toplamak yerine günlüğe HATA yazıyor.

═══ 2 · TRANSİT FATURADA HER KALEM KENDİ SATIŞ KAYDINI ALIYOR ═══

Stoktan karşılanmayan faturadan TEK satış kaydı çıkıyordu ve o
kayıt cinsini İLK kalemden alıyor, miktarı FARKLI BİRİMLERDEN
topluyordu. Ölçüldü:

    100 m² plaka + 20 ton blok  ->  "CALACATTA · 120 m²"

Kârlılık ve satış raporları bu kayıttan besleniyor: ikinci ürün hiç
satılmamış görünüyor, cirosu birincisine yazılıyordu.

Stoklu faturada zaten kaynak başına ayrı kayıt vardı (F1/F2).
Transit de aynı yola girdi: gelir ve maliyet kalemlerin DEĞERİ
oranında dağıtılıyor, son kaleme artık verilerek payların toplamı
faturanın matrahını kuruşu kuruşuna tutuyor (UN2'deki tam sayı
paylaştırmayla aynı gerekçe).

Alış maliyeti fatura düzeyinde tek rakam olduğu için kaleme gelire
orantılı dağıtılıyor — bu bir TAHMİN, ama eskisinden dürüst:
eskiden tüm maliyet tek ürüne yazılıyordu.

═══ 3 · `/api/stok/gruplar` SİLİNDİ ═══

Cari hareket ekranında fatura kesmek için stokları gruplayan uçtu.
Hiçbir ekrandan çağrılmıyordu; ayrıca grubun matrah ve KDV
toplamını çevirmeden topluyor, sonucu İLK stoğun döviziyle
etiketliyordu. EBATLI grubu `cins + ölçü` ile kurulduğu için ayrı
alımlar aynı gruba düşüyordu.

Önceki ulaşılmaz-uç taramam bunu KAÇIRMIŞTI: ÖNEK eşliyordu ve
`/api/stok` şablonlarda geçiyor, GET de kullanılıyordu. Kör nokta
kapatıldı — artık parametresiz uçların TAM YOLU aranıyor ve bu bir
test (aşağıda).

F5 kuralını (sevk edilmiş mal fatura seçicisinde kalır) bu ölü uç
üzerinden denetleyen test, CANLI uca taşındı (`/api/stok`).
Testi ölü uçta bırakmak kuralı hiç denetlememek olurdu.

═══ BEKÇİLER ═══

  · Parametresiz her `/api/` ucunun TAM YOLU bir ekranda ya da
    blueprint'te geçmeli (diag hariç — onlar bilerek ekransız).
  · Kalem dövizi sabit bir para birimine düşmemeli. Bekçi yalnız
    KALEM değişkenlerine bakıyor; belgenin kendi `doviz` varsayılanı
    doğru olduğu için kapsamı geniş tutmak doğru satırları da
    kırmızıya boyar ve bekçiyi kapattırırdı.

═══ DOĞRULAMA ═══

  · 299 test geçiyor (291 → 299)
  · 8 DV1 testinin HEPSİ tabanda düşüyor; tabanda başka hiçbir test
    kırılmıyor
  · Bir testim önce tabanda da geçiyordu (EUR→USD yönü seçtiğim
    için, eski kod zaten USD yapıyordu). Yön USD→EUR'a çevrildi;
    düzeltmeden önce düşmeyen test hiçbir şey ölçmüyor.
  · EUR proforma → siparişe dönüşüm elle koşuldu: sipariş EUR,
    kalem EUR, 50 EUR 50 EUR kaldı
  · `js_denetim.py` temiz · 29 şablon ayrıştırılabiliyor
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
    'flask_app.py': 'def _kalem_doviz_denetle(kalemler, belge_doviz)',
    'tests/test_kritik.py': 'def test_dv1_kalem_dovizi_belgeden_geliyor',
}
ONKOSUL = {
    'flask_app.py': 'def _kdv_ayristir(brut, kdv_oran)',
    'tests/test_kritik.py': 'def test_kd1_olu_fonksiyon_yok',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'DV1 · flask_app.py blok 1',
     r'''            # ── TRANSIT FATURA: tek SatisKaydi, maliyet faturadan ──
            alis_mal_usd = _usd(f.alis_maliyeti or 0, f.maliyet_doviz or 'USD')
            maliyet_usd = alis_mal_usd + ek_maliyet_usd
            kar_usd = satis_toplam_usd - maliyet_usd
            marj = (kar_usd / satis_toplam_usd * 100) if satis_toplam_usd else 0

            # Kalemlerden ozet bilgi
            ilk_cins = kalemler[0].get('cins') if kalemler else None
            top_miktar = sum((k.get('miktar') or 0) for k in kalemler)
            ilk_birim = kalemler[0].get('birim') if kalemler else None

            sk = SatisKaydi(
                id=_yeni_id('SAT'),
                stok_id=f'TRANSIT-{fatura_id}',
                stok_tip='TRANSIT',
                cins=ilk_cins,
                siparis_id=f.siparis_id,
                proforma_id=f.proforma_id,
                fatura_id=fatura_id,
                kaynak='fatura',
                musteri=f.musteri,
                musteri_ulke=f.musteri_ulke,
                satis_tarihi=f.fatura_tarihi or date.today(),
                miktar=top_miktar,
                birim=ilk_birim,
                doviz=f.doviz or 'USD',
                tutar=q2(satis_toplam_usd),
                kur_usd=q_kur(kur_usd), kur_eur=q_kur(kur_eur),
                tutar_usd=q2(satis_toplam_usd),
                tutar_try=q2(satis_toplam_usd * kur_usd if kur_usd else 0),
                maliyet_usd=q2(maliyet_usd),
                maliyet_try=q2(maliyet_usd * kur_usd if kur_usd else 0),
                kar_usd=q2(kar_usd),
                marj_yuzde=q_oran(marj),
                fatura_no=f.fatura_no,
                fatura_tarihi=f.fatura_tarihi,
                kullanici=session.get('kullanici')
            )
            db.session.add(sk)
            return 1, None
''',
     r'''            # ══════════════════════════════════════════════════════
            #  DV1 · TRANSIT FATURA: KALEM BAŞINA AYRI SatisKaydi
            #
            #  Eskiden TEK kayıt üretiliyordu ve o kayıt:
            #    · cins'i İLK kalemden alıyordu
            #    · miktarı FARKLI BİRİMLERDEN topluyordu
            #  Ölçüldü: 100 m² plaka + 20 ton blok satışı
            #  "CALACATTA · 120 m²" olarak kaydediliyordu. Kârlılık
            #  ve satış raporları bu kayıttan besleniyor; ikinci ürün
            #  hiç satılmamış görünüyor, ilkine onun cirosu yazılıyor.
            #
            #  Stoklu faturada zaten kaynak başına ayrı kayıt vardı
            #  (F1/F2). Transit de aynı yola girdi: gelir ve maliyet
            #  kalemlerin DEĞERİ oranında dağıtılır.
            #
            #  Alış maliyeti fatura düzeyinde TEK rakam (`alis_maliyeti`)
            #  — kalem bazında bilinmiyor. Gelire orantılı dağıtmak,
            #  her kaleme aynı marjı vermek demek. Bu bir TAHMİN ve
            #  eskisinden dürüst: eskiden tüm maliyet tek ürüne
            #  yazılıyordu.
            # ══════════════════════════════════════════════════════
            alis_mal_usd = _usd(f.alis_maliyeti or 0, f.maliyet_doviz or 'USD')
            maliyet_usd = alis_mal_usd + ek_maliyet_usd
            _dvz = (f.doviz or 'USD').upper()
            _matrah_orj = float(f.ara_toplam or f.toplam or 0)

            if not kalemler:
                # Kalem bilgisi yok — bölünecek bir şey de yok.
                _kalemler = [{'cins': None, 'miktar': 0, 'birim': None,
                              'toplam_fiyat': _matrah_orj,
                              'urun_tip': 'TRANSIT'}]
            else:
                _kalemler = kalemler

            # Paylar kalem DEĞERİNE göre; değer yoksa EŞİT pay.
            _degerler = [float(k.get('toplam_fiyat') or 0) for k in _kalemler]
            _deger_top = sum(_degerler)
            if _deger_top <= 0:
                _n = len(_kalemler)
                _degerler = [1.0] * _n
                _deger_top = float(_n)

            # TOPLAM KORUNUR: son kaleme ARTIK verilir, böylece
            # payların toplamı faturanın matrahını kuruşu kuruşuna
            # tutar (UN2'deki tam sayı paylaştırmayla aynı gerekçe).
            _kalan_usd = satis_toplam_usd
            _kalan_orj = _matrah_orj
            _kalan_mal = maliyet_usd
            olusan = 0
            for _i, _k in enumerate(_kalemler):
                _son = (_i == len(_kalemler) - 1)
                _oran = _degerler[_i] / _deger_top
                _pay_usd = _kalan_usd if _son else satis_toplam_usd * _oran
                _pay_orj = _kalan_orj if _son else _matrah_orj * _oran
                _pay_mal = _kalan_mal if _son else maliyet_usd * _oran
                _kalan_usd -= _pay_usd
                _kalan_orj -= _pay_orj
                _kalan_mal -= _pay_mal

                _kar = _pay_usd - _pay_mal
                _mik = float(_k.get('miktar') or 0)
                db.session.add(SatisKaydi(
                    id=_yeni_id('SAT'),
                    stok_id=f'TRANSIT-{fatura_id}-{_i + 1}',
                    stok_tip=_k.get('urun_tip') or 'TRANSIT',
                    cins=_k.get('cins'),
                    ozellik=_k.get('ozellik'),
                    siparis_id=f.siparis_id,
                    proforma_id=f.proforma_id,
                    fatura_id=fatura_id,
                    kaynak='fatura',
                    musteri=f.musteri,
                    musteri_ulke=f.musteri_ulke,
                    satis_tarihi=f.fatura_tarihi or date.today(),
                    miktar=q2(_mik),
                    birim=_k.get('birim'),
                    birim_fiyat=q2(_pay_orj / _mik) if _mik else 0,
                    doviz=_dvz,
                    tutar=q2(_pay_orj),
                    kur_usd=q_kur(kur_usd), kur_eur=q_kur(kur_eur),
                    tutar_usd=q2(_pay_usd),
                    tutar_try=q2(_pay_usd * kur_usd if kur_usd else 0),
                    maliyet_usd=q2(_pay_mal),
                    maliyet_try=q2(_pay_mal * kur_usd if kur_usd else 0),
                    kar_usd=q2(_kar),
                    marj_yuzde=q_oran((_kar / _pay_usd * 100) if _pay_usd else 0),
                    fatura_no=f.fatura_no,
                    fatura_tarihi=f.fatura_tarihi,
                    kullanici=session.get('kullanici')
                ))
                olusan += 1
            return olusan, None
'''),
    ('flask_app.py', 'DV1 · flask_app.py blok 2',
     r'''    def _kalem_hesapla(k_data):
''',
     r'''    # ══════════════════════════════════════════════════════════════
    #  DV1 · KALEM DÖVİZİ BELGEDEN GELİR
    #
    #  ÖLÇÜLDÜ: EUR bir proformanın kalemleri `'USD'` damgalanıyordu
    #  (`doviz=k.get('doviz','USD')` — belgenin dövizi yerine sabit
    #  USD). Ekran kalem satırını `k.doviz || p.doviz` ile bastığı
    #  için EUR proformada HER SATIRDA $ görünüyor, belgenin toplamı
    #  ise € yazıyordu. Müşteriye giden belgede.
    #
    #  Sipariş tarafında aynı şey sayıya dönüşüyordu: kalemler USD,
    #  sipariş EUR; toplam çevrilmeden toplanıp siparişin döviziyle
    #  etiketleniyordu. 10.000 USD + 10.000 EUR = "20.000 USD"
    #  (gerçeği 21.250) ve bu sayı faturaya, cari harekete, satış
    #  kaydına aynen geçiyordu.
    #
    #  KURAL (işin sahibinden): fiyat KENDİ para birimiyle yolculuk
    #  eder. Proformada 50 EUR ise siparişte de, faturada da, satış
    #  kaydında da 50 EUR'dur — hiçbir yerde çevrilmez.
    #
    #  Bunun gereği: kalemin dövizi BELGENİN dövizidir, ayrıca
    #  seçilmez. Kalem bilerek farklı bir döviz taşıyorsa belge
    #  REDDEDİLİR. Çevirmek fiyatı değiştirmek olurdu; sessizce
    #  toplamak ise yanlış sayı üretmek. Üçüncü yol yok: ticari
    #  faturanın tek para birimi olur.
    # ══════════════════════════════════════════════════════════════
    def _kalem_doviz_denetle(kalemler, belge_doviz):
        """Kalem dövizlerini belgeninkine sabitler (inplace).

        Döner: (None, None) sorun yoksa; aksi halde (sıra_no, gelen).
        """
        bd = (belge_doviz or 'USD').strip().upper()
        for _i, _k in enumerate(kalemler or []):
            if not isinstance(_k, dict):
                continue
            _gelen = str(_k.get('doviz') or '').strip().upper()
            if _gelen and _gelen != bd:
                return _i + 1, _gelen
            _k['doviz'] = bd
        return None, None

    def _kalem_doviz_hatasi(sira, gelen, belge_doviz):
        """Reddi, sebebini söyleyerek döner."""
        bd = (belge_doviz or 'USD').strip().upper()
        return jsonify({
            'ok': False, 'error': 'kalem_dovizi',
            'mesaj': f'{sira}. kalemin para birimi {gelen}, belgenin '
                     f'para birimi {bd}. Bir belgenin tüm kalemleri aynı '
                     f'para biriminde olmalı — kalemi {bd} fiyatıyla girin '
                     f'ya da belgenin para birimini {gelen} yapın. '
                     f'(Fiyat çevrilmez: {gelen} girdiyseniz {gelen} kalır.)'
        }), 400

    def _kalem_hesapla(k_data):
'''),
    ('flask_app.py', 'DV1 · flask_app.py blok 3',
     r'''        for k in SiparisKalem.query.filter_by(siparis_id=siparis.id).all():
            # Şimdilik kalem dövizi sipariş dövizine eşit varsayılıyor.
            # Farklı dövizler için kur çevrimi eklenebilir.
''',
     r'''        # ── DV1 · KALEM DÖVİZİ SİPARİŞİNKİNE EŞİT OLMALI ──
        # Eskiden burada "şimdilik eşit varsayılıyor" yazıyordu ve
        # varsayım DENETLENMİYORDU. Ölçüldü: 10.000 USD + 10.000 EUR
        # kalemli bir sipariş "20.000 USD" yazıyordu (gerçeği 21.250)
        # ve bu sayı faturaya, cari harekete ve satış kaydına aynen
        # geçiyordu. Artık kalem dövizi belgeden MİRAS ALINIYOR
        # (`_kalem_doviz_denetle`), yani karışık sipariş yazma
        # yolundan hiç doğmuyor. Burası son çare: eski bir kayıt ya
        # da betikle üretilmiş bir sipariş karışıksa sessizce yanlış
        # toplamaktansa GÖRÜNÜR olsun.
        kalemler = SiparisKalem.query.filter_by(siparis_id=siparis.id).all()
        _sip_dv = (siparis.doviz or 'USD').upper()
        _yabanci = sorted({(k.doviz or _sip_dv).upper() for k in kalemler}
                          - {_sip_dv})
        if _yabanci:
            app.logger.error(
                f'DV1 · sipariş {siparis.id} dövizi {_sip_dv} ama kalemlerde '
                f'{", ".join(_yabanci)} var. Toplam ÇEVRİLMEDEN hesaplandı; '
                f'tutar güvenilmez.')
        for k in kalemler:
'''),
    ('flask_app.py', 'DV1 · flask_app.py blok 4',
     r'''        for idx, k_data in enumerate(kalemler_data):
            # Hesaplama
''',
     r'''        # DV1 · kalem dövizi SİPARİŞTEN gelir (inplace sabitlenir).
        _dv_sira, _dv_gelen = _kalem_doviz_denetle(kalemler_data, sip.doviz)
        if _dv_sira:
            db.session.rollback()
            return _kalem_doviz_hatasi(_dv_sira, _dv_gelen, sip.doviz)

        for idx, k_data in enumerate(kalemler_data):
            # Hesaplama
'''),
    ('flask_app.py', 'DV1 · flask_app.py blok 5',
     r'''            for idx, k_data in enumerate(kalemler_data):
''',
     r'''            # DV1 · kalem dövizi SİPARİŞTEN gelir (inplace sabitlenir).
            _dv_sira, _dv_gelen = _kalem_doviz_denetle(kalemler_data, doviz)
            if _dv_sira:
                db.session.rollback()
                return _kalem_doviz_hatasi(_dv_sira, _dv_gelen, doviz)

            for idx, k_data in enumerate(kalemler_data):
'''),
    ('flask_app.py', 'DV1 · flask_app.py blok 6',
     r'''
            # Yeni kalemleri ekle
''',
     r'''
            # DV1 · kalem dövizi SİPARİŞTEN gelir (inplace sabitlenir).
            # `sip.doviz` bu noktada güncellenmiş değeri taşır.
            _dv_sira, _dv_gelen = _kalem_doviz_denetle(
                data['kalemler'], sip.doviz)
            if _dv_sira:
                db.session.rollback()
                return _kalem_doviz_hatasi(_dv_sira, _dv_gelen, sip.doviz)

            # Yeni kalemleri ekle
'''),
    ('flask_app.py', 'DV1 · flask_app.py blok 7',
     r'''    @app.route('/api/stok/gruplar', methods=['GET'])
    def api_stok_gruplar():
        """Cari hareket icin gruplandirilmis stok listesi.
        BLOK: her stok ayri (id ile)
        PLAKA: blok_no'ya gore grup (ayni blok = ayni alim)
        EBATLI: kasa_no veya referans'a gore grup
        """
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        # Sadece aktif stoklari (Teslim Edildi haric) goster.
        # F5 · DUZELTME: 'Sevkedildi' listede YOKTU. Mal gemiye
        # yuklendigi an bu seciciden kayboluyordu; henuz faturasi
        # kesilmemis bir sevkiyatin stogunu secmek imkansizdi.
        # Yoldaki mal HALA BIZIM malimiz — listede kalir.
        aktif_durumlar = ['Serbest', 'Rezerve', 'Satildi', 'Sevkedildi']

        gruplar = {'blok': [], 'plaka': [], 'ebatli': []}

        # BLOK - her stok ayri grup
        for s in BlokStok.query.filter(BlokStok.durum.in_(aktif_durumlar)).all():
            _fd = getattr(s, 'fatura_durumu', 'faturali') or 'faturali'
            _ek = ' · ⏳ FATURASIZ' if _fd == 'faturasiz' else ''
            _ref = s.blok_no or s.id
            _matrah = s.matrah or 0
            _kdv = s.kdv_tutar or 0
            gruplar['blok'].append({
                'grup_id': s.id,  # baglanti_id olarak kullanilacak
                'etiket': f"{_ref} · {s.cins or '-'} · {s.tonaj or 0:.1f} ton{_ek}",
                'tip': 'BLOK',
                'cins': s.cins,
                'blok_no': s.blok_no,
                'stok_idler': [s.id],
                'toplam_miktar': s.tonaj or 0,
                'birim': 'ton',
                'adet': 1,
                'fatura_durumu': _fd,
                'matrah': q2(_matrah),
                'kdv': q2(_kdv),
                'toplam': q2(_matrah + _kdv),
                'doviz': s.doviz or 'USD'
            })

        # PLAKA - blok_no'ya gore grupla
        from collections import defaultdict
        plaka_gruplar = defaultdict(list)
        for s in PlakaStok.query.filter(PlakaStok.durum.in_(aktif_durumlar)).all():
            anahtar = s.blok_no or s.id  # blok_no yoksa kendi id'si
            plaka_gruplar[anahtar].append(s)

        for blok_no, stoklar in plaka_gruplar.items():
            ilk = stoklar[0]
            toplam_m2 = sum(s.metraj_m2 or 0 for s in stoklar)
            _faturasiz_var = any(getattr(s, 'fatura_durumu', 'faturali') == 'faturasiz' for s in stoklar)
            _ek = ' · ⏳ FATURASIZ' if _faturasiz_var else ''
            # Sadece faturasız olanların tutarı (faturalandırma için)
            _fsiz = [s for s in stoklar if getattr(s, 'fatura_durumu', 'faturali') == 'faturasiz']
            _hedef = _fsiz if _fsiz else stoklar
            _matrah = sum(s.matrah or 0 for s in _hedef)
            _kdv = sum(s.kdv_tutar or 0 for s in _hedef)
            gruplar['plaka'].append({
                'grup_id': f"BLOK:{blok_no}",  # baglanti_id format
                'etiket': f"{blok_no} · {ilk.cins or '-'} · {len(stoklar)} plaka · {toplam_m2:.2f} m²{_ek}",
                'tip': 'PLAKA',
                'cins': ilk.cins,
                'blok_no': blok_no,
                'stok_idler': [s.id for s in stoklar],
                'toplam_miktar': toplam_m2,
                'birim': 'm²',
                'adet': len(stoklar),
                'fatura_durumu': 'faturasiz' if _faturasiz_var else 'faturali',
                'matrah': q2(_matrah),
                'kdv': q2(_kdv),
                'toplam': q2(_matrah + _kdv),
                'doviz': ilk.doviz or 'USD'
            })

        # EBATLI - kasa_no varsa onun ortak prefix'ine, yoksa cins+olcu kombinasyonuna gore
        # Aslinda kasa_no genelde "PREFIX-1", "PREFIX-2" formatinda
        import re as _re
        ebatli_gruplar = defaultdict(list)
        for s in EbatliStok.query.filter(EbatliStok.durum.in_(aktif_durumlar)).all():
            # Kasa_no'dan PREFIX cikar (sondaki -N)
            if s.kasa_no:
                m = _re.match(r'^(.*?)-\d+$', s.kasa_no)
                anahtar = m.group(1) if m else s.kasa_no
            else:
                # Kasa_no yok: cins + olcu kombinasyonu
                anahtar = f"{s.cins or '?'}_{s.boy or 0}x{s.yukseklik or 0}x{s.kalinlik or 0}"
            ebatli_gruplar[anahtar].append(s)

        for anahtar, stoklar in ebatli_gruplar.items():
            ilk = stoklar[0]
            toplam_m2 = sum(((s.boy or 0) * (s.yukseklik or 0) / 10000) * (s.kasa_ici_adet or 1)
                           for s in stoklar)
            _faturasiz_var = any(getattr(s, 'fatura_durumu', 'faturali') == 'faturasiz' for s in stoklar)
            _ek = ' · ⏳ FATURASIZ' if _faturasiz_var else ''
            _fsiz = [s for s in stoklar if getattr(s, 'fatura_durumu', 'faturali') == 'faturasiz']
            _hedef = _fsiz if _fsiz else stoklar
            _matrah = sum(s.matrah or 0 for s in _hedef)
            _kdv = sum(s.kdv_tutar or 0 for s in _hedef)
            gruplar['ebatli'].append({
                'grup_id': f"EBATLI_GRP:{anahtar}",
                'etiket': f"{anahtar} · {ilk.cins or '-'} · {len(stoklar)} kasa · {toplam_m2:.2f} m²{_ek}",
                'tip': 'EBATLI',
                'cins': ilk.cins,
                'kasa_prefix': anahtar,
                'olculer': f"{ilk.boy}x{ilk.yukseklik}x{ilk.kalinlik}" if ilk.boy else '',
                'stok_idler': [s.id for s in stoklar],
                'toplam_miktar': toplam_m2,
                'birim': 'm²',
                'adet': len(stoklar),
                'fatura_durumu': 'faturasiz' if _faturasiz_var else 'faturali',
                'matrah': q2(_matrah),
                'kdv': q2(_kdv),
                'toplam': q2(_matrah + _kdv),
                'doviz': ilk.doviz or 'USD'
            })

        return jsonify(gruplar)
''',
     r'''    # ── DV1 · SİLİNDİ: GET /api/stok/gruplar
    #
    #    Cari hareket ekranında fatura kesmek için stokları
    #    blok/kasa bazında gruplayan uçtu. Hiçbir ekrandan
    #    çağrılmıyordu (tam yol taraması; önceki ulaşılmaz-uç
    #    taraması ÖNEK eşlediği için kaçırmıştı — `/api/stok`
    #    şablonlarda geçiyor ve GET de kullanılıyordu).
    #
    #    Ayrıca grubun matrah ve KDV toplamını çevirmeden
    #    topluyor, sonucu İLK stoğun döviziyle etiketliyordu.
    #    EBATLI grubu `cins + ölçü` ile kurulduğu için ayrı
    #    alımlar aynı gruba düşüyordu: farklı dövizdeki iki alım
    #    tek sayıya toplanıp tek para birimiyle yazılabiliyordu.
    #    Yarım kurulmuş ve yanlış hesaplayan bir ucu bekletmek,
    #    yarın birinin onu doğru sanıp bağlaması demekti.
'''),
    ('flask_app.py', 'DV1 · flask_app.py blok 8',
     r'''        for idx, k in enumerate(data.get('kalemler', [])):
            pk = ProformaKalem(proforma_id=p.id, urun_tip=k.get('urun_tip'), cins=k.get('cins'), yuzey_spec=k.get('ozellik'),
''',
     r'''        # DV1 · kalem dövizi BELGEDEN gelir (inplace sabitlenir).
        _dv_sira, _dv_gelen = _kalem_doviz_denetle(
            data.get('kalemler', []), p.doviz)
        if _dv_sira:
            return _kalem_doviz_hatasi(_dv_sira, _dv_gelen, p.doviz)

        for idx, k in enumerate(data.get('kalemler', [])):
            pk = ProformaKalem(proforma_id=p.id, urun_tip=k.get('urun_tip'), cins=k.get('cins'), yuzey_spec=k.get('ozellik'),
'''),
    ('flask_app.py', 'DV1 · flask_app.py blok 9',
     r'''                               doviz=k.get('doviz','USD'), toplam_fiyat=k.get('toplam_fiyat'), net_fiyat=k.get('net_fiyat'),
''',
     r'''                               doviz=k.get('doviz') or (p.doviz or 'USD'), toplam_fiyat=k.get('toplam_fiyat'), net_fiyat=k.get('net_fiyat'),
'''),
    ('flask_app.py', 'DV1 · flask_app.py blok 10',
     r'''            for idx, k in enumerate(data.get('kalemler', [])):
                pk = ProformaKalem(
                    proforma_id=p.id, urun_tip=k.get('urun_tip'), cins=k.get('cins'),
                    yuzey_spec=k.get('ozellik'), blok_no=k.get('blok_no'), en=k.get('en'),
                    boy=k.get('boy'), yukseklik=k.get('yukseklik'), kalinlik=k.get('kalinlik'),
                    adet=k.get('adet', 1), miktar=k.get('miktar'), birim=k.get('birim', 'm2'),
                    birim_fiyat=k.get('birim_fiyat'), doviz=k.get('doviz', 'USD'),
''',
     r'''            # DV1 · kalem dövizi BELGEDEN gelir (inplace sabitlenir).
            # `p.doviz` bu noktada GÜNCELLENMİŞ değeri taşıyor: belge
            # dövizi değiştirilerek güncelleniyorsa kalemler yeni
            # dövize göre denetlenir.
            _dv_sira, _dv_gelen = _kalem_doviz_denetle(
                data.get('kalemler', []), p.doviz)
            if _dv_sira:
                return _kalem_doviz_hatasi(_dv_sira, _dv_gelen, p.doviz)

            for idx, k in enumerate(data.get('kalemler', [])):
                pk = ProformaKalem(
                    proforma_id=p.id, urun_tip=k.get('urun_tip'), cins=k.get('cins'),
                    yuzey_spec=k.get('ozellik'), blok_no=k.get('blok_no'), en=k.get('en'),
                    boy=k.get('boy'), yukseklik=k.get('yukseklik'), kalinlik=k.get('kalinlik'),
                    adet=k.get('adet', 1), miktar=k.get('miktar'), birim=k.get('birim', 'm2'),
                    birim_fiyat=k.get('birim_fiyat'), doviz=k.get('doviz') or (p.doviz or 'USD'),
'''),
    ('tests/test_kritik.py', 'DV1 · tests/test_kritik.py blok 1',
     r'''    seçicisinden kaybolmamalı — hâlâ bizim malımız."""
    c = istemci('admin', 'ADMIN')
    r = c.get('/api/stok/gruplar', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    hepsi = str(j)
    assert 'PLK-F5-Y1' in hepsi or 'T-F5' in hepsi, \
        'sevk edilmis stok gruplarda gorunmuyor'
''',
     r'''    seçicisinden kaybolmamalı — hâlâ bizim malımız.

    DV1 · TEST CANLI UCA TAŞINDI. Eskiden `/api/stok/gruplar`
    sorgulanıyordu; o uç DV1'de silindi çünkü hiçbir ekrandan
    çağrılmıyordu (ve grup toplamlarında döviz karıştırıyordu).
    Kuralın asıl yeri `/api/stok`: maliyet, proforma ve sipariş
    ekranlarındaki stok seçicileri oradan besleniyor. Testi ölü
    uçta bırakmak, kuralı hiç denetlememek olurdu."""
    c = istemci('admin', 'ADMIN')
    r = c.get('/api/stok?tip=PLAKA&per_page=2000', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    idler = {x.get('id') for x in (r.get_json() or {}).get('data', [])}
    assert 'PLK-F5-Y1' in idler, (
        'sevk edilmiş stok seçicide görünmüyor — henüz faturası '
        'kesilmemiş bir sevkiyatın stoğu seçilemez hâle gelir')
'''),
    ('tests/test_kritik.py', 'DV1 · tests/test_kritik.py blok 2',
     r'''        'ters tırnağı yakalamıyor')
''',
     r'''        'ters tırnağı yakalamıyor')


# ══════════════════════════════════════════════════════════════════
#  DV1 · FİYAT KENDİ PARA BİRİMİYLE YOLCULUK EDER
#
#  ÖLÇÜLDÜ: EUR bir proformanın kalemleri `'USD'` damgalanıyordu
#  (`doviz=k.get('doviz','USD')` — belgenin dövizi yerine sabit
#  USD). Ekran kalem satırını `k.doviz || p.doviz` ile bastığı için
#  EUR proformada HER SATIRDA $ görünüyordu; müşteriye giden
#  belgede. Sipariş tarafında aynı şey sayıya dönüşüyordu:
#
#     10.000 USD + 10.000 EUR kalemli sipariş -> "20.000 USD"
#     (gerçeği 21.250) ve bu sayı faturaya, cari harekete ve
#     satış kaydına aynen geçiyordu.
#
#  KURAL: proformada 50 EUR ise siparişte de, faturada da, satış
#  kaydında da 50 EUR. Hiçbir yerde çevrilmez. Bunun gereği, kalem
#  dövizinin BELGEDEN miras alınması; farklı bir döviz bilerek
#  gönderilirse belge reddedilir.
# ══════════════════════════════════════════════════════════════════
def _dv1_kurulum():
    from models import Firma
    with fa.app.app_context():
        if not Cari.query.get('DV1-MUS'):
            db.session.add(Cari(id='DV1-MUS', unvan='DV1 STONE LLC',
                                cari_tip='Müşteri', para_birimi='EUR',
                                gorunurluk='acik'))
        for dv, k in (('USD', 40.0), ('EUR', 45.0)):
            if not DovizKur.query.filter_by(
                    doviz=dv, tarih=date(2026, 10, 28)).first():
                db.session.add(DovizKur(doviz=dv, tarih=date(2026, 10, 28),
                                        alis=k, satis=k, efektif=k))
        db.session.commit()
    return istemci('admin', 'ADMIN')


_DV1_KALEM = {'urun_tip': 'PLAKA', 'cins': 'DV1 CALACATTA', 'miktar': 100,
              'birim': 'm2', 'birim_fiyat': 50}


def test_dv1_kalem_dovizi_belgeden_geliyor():
    """EUR proformanın kalemi EUR olmalı; 50 EUR, 50 EUR kalmalı."""
    from models import Proforma, ProformaKalem
    c = _dv1_kurulum()
    r = c.post('/api/proforma', headers=H, json={
        'musteri': 'DV1 STONE LLC', 'tarih': '2026-10-28',
        'doviz': 'EUR', 'kalemler': [dict(_DV1_KALEM)]})
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    pid = r.get_json()['id']
    with fa.app.app_context():
        p = db.session.get(Proforma, pid)
        kalemler = ProformaKalem.query.filter_by(proforma_id=pid).all()
        assert p.doviz == 'EUR', p.doviz
        assert kalemler, 'kalem yazılmamış'
        for k in kalemler:
            # ESKI DAVRANIS: k.doviz == 'USD'
            assert (k.doviz or '').upper() == 'EUR', (
                f'belge EUR ama kalem {k.doviz} — ekran kalem satırını '
                f'`k.doviz || p.doviz` ile basıyor, EUR belgede $ görünür')
            assert float(k.birim_fiyat or 0) == 50.0, k.birim_fiyat


def test_dv1_farkli_dovizli_kalem_reddediliyor():
    """Kalem bilerek farklı döviz taşıyorsa belge 400 almalı."""
    c = _dv1_kurulum()
    r = c.post('/api/proforma', headers=H, json={
        'musteri': 'DV1 STONE LLC', 'tarih': '2026-10-28',
        'doviz': 'EUR', 'kalemler': [dict(_DV1_KALEM, doviz='USD')]})
    assert r.status_code == 400, r.status_code
    j = r.get_json()
    assert j.get('error') == 'kalem_dovizi', j
    # Sebep SOYLENMELI: hangi kalem, hangi para birimi
    assert 'USD' in j.get('mesaj', '') and 'EUR' in j.get('mesaj', ''), j


def test_dv1_proforma_dovizi_degisince_kalemler_takip_ediyor():
    """Belgenin dövizi değişince kalemler yeni dövize geçmeli."""
    from models import Proforma, ProformaKalem
    c = _dv1_kurulum()
    r = c.post('/api/proforma', headers=H, json={
        'musteri': 'DV1 STONE LLC', 'tarih': '2026-10-28',
        'doviz': 'USD', 'kalemler': [dict(_DV1_KALEM)]})
    pid = r.get_json()['id']
    # USD -> EUR. Yönü USD'DEN ÇIKACAK şekilde seçmek önemli: ilk
    # yazdığımda EUR -> USD yapmıştım ve test ESKİ KODDA DA geçti,
    # çünkü eski kod kalemi zaten sabit 'USD' yapıyordu. Bir test,
    # düzeltmeden önce düşmüyorsa hiçbir şey ölçmüyordur.
    r2 = c.put(f'/api/proforma/{pid}', headers=H, json={
        'musteri': 'DV1 STONE LLC', 'doviz': 'EUR',
        'kalemler': [dict(_DV1_KALEM)]})
    assert r2.status_code == 200, r2.get_data(as_text=True)[:300]
    with fa.app.app_context():
        p = db.session.get(Proforma, pid)
        assert p.doviz == 'EUR', p.doviz
        for k in ProformaKalem.query.filter_by(proforma_id=pid).all():
            assert (k.doviz or '').upper() == 'EUR', (
                f'belge EUR oldu ama kalem {k.doviz} kaldı')


def test_dv1_karisik_dovizli_siparis_olusturulamiyor():
    """Sıcak satış karışık dövizli kalem kabul etmemeli.

    ESKIDEN: 10.000 USD + 10.000 EUR kabul ediliyor, sipariş
    'toplam_tutar=20000 USD' yazıyor, fatura ve cari hareket de
    o sayıyı alıyordu."""
    c = _dv1_kurulum()
    r = c.post('/api/sicak_satis', headers=H, json={
        'musteri': 'DV1 STONE LLC', 'tarih': '2026-10-28',
        'siparis_tarihi': '2026-10-28', 'doviz': 'USD',
        'kalemler': [
            dict(_DV1_KALEM, cins='DV1 A', birim_fiyat=100, doviz='USD'),
            dict(_DV1_KALEM, cins='DV1 B', birim_fiyat=100, doviz='EUR'),
        ]})
    assert r.status_code == 400, (
        f'karışık dövizli sipariş kabul edildi ({r.status_code}) — '
        f'toplam çevrilmeden toplanır ve tek para birimiyle etiketlenir')
    assert r.get_json().get('error') == 'kalem_dovizi', r.get_json()


def test_dv1_transit_faturada_kalem_basina_satis_kaydi():
    """Transit faturada her kalem kendi satış kaydını almalı.

    ESKIDEN tek kayıt vardı: cins İLK kalemden, miktar FARKLI
    BİRİMLERDEN toplanarak. 100 m² plaka + 20 ton blok satışı
    "CALACATTA · 120 m²" olarak kaydediliyordu."""
    from models import SatisKaydi
    c = _dv1_kurulum()
    r = c.post('/api/sicak_satis', headers=H, json={
        'musteri': 'DV1 STONE LLC', 'tarih': '2026-10-28',
        'siparis_tarihi': '2026-10-28', 'doviz': 'USD',
        'kalemler': [
            {'urun_tip': 'PLAKA', 'cins': 'DV1 PLAKA', 'miktar': 100,
             'birim': 'm2', 'birim_fiyat': 100, 'adet': 1,
             'boy': 300, 'yukseklik': 180, 'kalinlik': 2},
            {'urun_tip': 'BLOK', 'cins': 'DV1 BLOK', 'miktar': 20,
             'birim': 'ton', 'birim_fiyat': 500, 'adet': 1,
             'boy': 300, 'yukseklik': 180, 'en': 170},
        ]})
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    fid = r.get_json().get('fatura_id')
    assert fid, r.get_json()

    with fa.app.app_context():
        kayitlar = SatisKaydi.query.filter_by(fatura_id=fid).all()
        assert len(kayitlar) == 2, (
            f'{len(kayitlar)} satış kaydı — 2 kalem için 2 olmalı: '
            + str([(k.cins, k.miktar, k.birim) for k in kayitlar]))
        esle = {k.cins: k for k in kayitlar}
        assert set(esle) == {'DV1 PLAKA', 'DV1 BLOK'}, list(esle)
        # Her kayıt KENDİ birimini ve miktarını taşır
        assert esle['DV1 PLAKA'].birim == 'm2', esle['DV1 PLAKA'].birim
        assert esle['DV1 BLOK'].birim == 'ton', esle['DV1 BLOK'].birim
        assert float(esle['DV1 PLAKA'].miktar or 0) == 100.0
        assert float(esle['DV1 BLOK'].miktar or 0) == 20.0
        # TOPLAM KORUNUR: paylar faturanın matrahını tam verir
        toplam = round(sum(float(k.tutar or 0) for k in kayitlar), 2)
        assert toplam == 20000.0, (
            f'payların toplamı {toplam}, fatura matrahı 20000')
        toplam_usd = round(sum(float(k.tutar_usd or 0) for k in kayitlar), 2)
        assert toplam_usd == 20000.0, toplam_usd


def test_dv1_stok_gruplar_ucu_silindi():
    """Ölü ve döviz karıştıran uç gerçekten kalkmış olmalı.

    404 DEĞİL 405 dönüyor: yol artık `/api/stok/<stok_id>`
    kuralına düşüyor ve o kural GET kabul etmiyor. Önemli olan
    veri DÖNMEMESİ."""
    c = istemci('admin', 'ADMIN')
    r = c.get('/api/stok/gruplar', headers=H)
    assert r.status_code in (404, 405), r.status_code
    assert b'gruplar' not in r.get_data(), r.get_data()[:120]


def test_dv1_sabit_yollu_her_uc_bir_ekrandan_cagriliyor():
    """Parametresiz /api/ uçlarının TAM YOLU bir yerde geçmeli.

    BU TARAMANIN KÖR NOKTASIYDI. `ulasilmaz_uc_tara` ÖNEK
    eşliyordu: `/api/stok/gruplar` için `/api/stok` şablonlarda
    geçiyor ve GET de kullanılıyor, bu yüzden uç "ulaşılabilir"
    sayılıyordu — oysa tam yolu hiçbir yerde yoktu ve uç yarım
    kurulmuş hâlde, döviz karıştırarak duruyordu.

    Parametresiz yollarda tahmine gerek yok: tam dizge aranır."""
    import ast as _ast
    import io as _io
    import re as _re

    ANA = os.path.join(KOK, 'flask_app.py')
    kaynak = _io.open(ANA, encoding='utf-8').read().replace('\r\n', '\n')
    agac = _ast.parse(kaynak)

    tuketici = []
    for dizin in ('templates', 'static', 'blueprints'):
        kok = os.path.join(KOK, dizin)
        if not os.path.isdir(kok):
            continue
        for yer, _, dosyalar in os.walk(kok):
            for ad in dosyalar:
                if ad.endswith(('.html', '.js', '.py')):
                    tuketici.append(_io.open(
                        os.path.join(yer, ad), encoding='utf-8',
                        errors='replace').read())
    tuketici = '\n'.join(tuketici)

    olu = []
    for fn in _ast.walk(agac):
        if not isinstance(fn, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            continue
        for dec in fn.decorator_list:
            if not (isinstance(dec, _ast.Call)
                    and isinstance(dec.func, _ast.Attribute)
                    and dec.func.attr == 'route' and dec.args
                    and isinstance(dec.args[0], _ast.Constant)):
                continue
            yol = dec.args[0].value
            if not yol.startswith('/api/') or '<' in yol:
                continue
            # Teshis uclari BILEREK ekransiz: ADMIN'in elle cagirdigi
            # tani araclari. `_diag_guard` onlari zaten kapatiyor.
            if yol.startswith('/api/diag/'):
                continue
            if _re.search(_re.escape(yol), tuketici):
                continue
            if kaynak.count(yol) > 1:
                continue        # flask_app kendi icinde cagiriyor
            olu.append(f'{yol} ({fn.name}, satır {fn.lineno})')

    assert not olu, (
        'tam yolu hiçbir ekranda/blueprint\'te geçmeyen uç(lar) — '
        'ya bağlanmalı ya silinmeli: ' + ', '.join(sorted(olu)))


def test_dv1_kalem_dovizi_sabit_usd_yazilmamis():
    """KALEM dövizi sabit 'USD'ye düşmemeli — belgeden gelmeli.

    BELGENİN kendi dövizi için `data.get('doviz','USD')` doğrudur:
    orada varsayılan gerçekten USD. Yanlış olan, KALEMİN dövizini
    belgeye bakmadan USD yapmaktı. Bekçi yalnız kalem değişkenlerine
    (`k`, `_k`, `k_data`, `kalem`) bakar; kapsamı geniş tutmak,
    doğru satırları da kırmızıya boyayıp bekçiyi kapattırırdı."""
    import io as _io
    import re as _re
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    desen = _re.compile(
        r"doviz\s*=\s*(k|_k|kl|kalem|k_data|pk|_kalem)\.get\("
        r"'doviz'\s*,\s*'[A-Z]{3}'\)")
    kacak = []
    for i, t in enumerate(kaynak.split('\n'), 1):
        if t.lstrip().startswith('#'):
            continue                  # yorum; açıklama metni olabilir
        if desen.search(t):
            kacak.append(f'satır {i}: {t.strip()[:70]}')
    assert not kacak, (
        'kalem dövizi belgeden değil sabit bir para biriminden '
        'alınıyor: ' + '; '.join(kacak))
'''),
]

def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA DV1 — FİYAT KENDİ PARA BİRİMİYLE YOLCULUK EDER')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    # ── --yaz-gecici ──
    # base64 gömülü iki dosyayı /tmp'ye çıkarır, PROJEYE DOKUNMAZ.
    # Tam dosya yazan bir yamayı önce okumak istemek yerinde bir
    # istek; "uygula da sonra bak" demek yanlış olurdu.
    if '--yaz-gecici' in sys.argv:
        hedef = tempfile.mkdtemp(prefix='dv1-')
        print()
        for ad in TAM_YAZILAN:
            p = os.path.join(hedef, ad)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(_tam_dosya(ad))
            print(f'  {p}')
        print()
        print('  Projeye DOKUNULMADI. Okuduktan sonra:')
        print('    python3 yama_dv1.py            # rapor')
        print('    python3 yama_dv1.py --uygula')
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
        print('  ⊙ Yama DV1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_dv1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_dv1'
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
    print('    venv/bin/python -m pytest tests/test_kritik.py -q   # 299')
    print()
    print('  SUNUCUYU YENIDEN BASLAT')
    print('    sudo systemctl restart milestone-erp')
    print('    Sema degisikligi YOK, goc YOK.')
    print()
    print('  NE DEGISTI')
    print('    · Kalem dovizi BELGEDEN geliyor. EUR proformanin')
    print('      kalemleri USD damgalanmiyor; 50 EUR, 50 EUR kaliyor.')
    print('      Kalem bilerek farkli doviz tasiyorsa belge reddedilir.')
    print('    · Transit faturada her kalem KENDI satis kaydini alir.')
    print('      100 m2 + 20 ton artik "120 m2" olmuyor.')
    print('    · Kullanilmayan /api/stok/gruplar ucu silindi.')
    print('    · Iki yeni bekci: tam yol ulasilabilirligi ve kalem')
    print('      dovizinin sabit yazilmamasi.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

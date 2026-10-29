#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA UN1 — KESİM MALİYETİ USD · HER HEDEF KENDİ KAYNAĞINDAN
============================================================

ÖNKOŞUL: **yama_kr1.py uygulanmış olmalı.** Betik denetliyor.
ŞEMA DEĞİŞİYOR: yeni bir kolon ve bir Alembic göçü var (aşağıda).

Üç soru sordum, üçünü de cevapladın. Bu yama o üç cevabın
uygulanması — artı yol üstünde çıkan iki şey.

═══ 1 · TOPLANAN ŞEY BİR PARA BİRİMİ DEĞİLDİ ═══

Blok/plaka `matrah`'ı stoğun KENDİ dövizinde tutuluyor. Bloğa
işlenen ek maliyetler ise `usd_karsilik` ile USD. Dağıtıcı ikisini
TOPLUYORDU.

MR1'de buraya kendi elimle not düşmüştüm: *"matrah stoğun kendi
dövizinde, çevrilmeden kullanılıyor. Düzeltmek USD dışı bloklarda
mevcut birim maliyetleri oynatır; ayrı bir karar, Bahadır'a
soruldu."* Karar geldi: **USD**.

ÖLÇÜLDÜ — 20 ton × 200,00 EUR/ton blok (4.000 EUR matrah), bloğa
500,00 USD fason, 10,80 m² plaka çıktı; 1 EUR = 45, 1 USD = 40:

      önce   416,67 EUR/m²   ← 500 USD, 500 EUR sayılmış
      sonra  462,96 USD/m²   = (4.500,00 + 500,00) / 10,80 ✓

Plakanın ETİKETİ de USD oldu. Eskiden plaka bloğun dövizini
taşıyordu ve dağıtıcı ona USD bir rakam yazıyordu — sessiz bir
yalan.

  ÇEVİREMİYORSA KESMİYOR. `_usd_cevrim` kur bulamazsa tutarı olduğu
  gibi döndürüp uyarıyla geçiyor; maliyet ekranında bu doğru
  davranış. Ama etiket USD'ye döndüğü için, çevrilmemiş bir EUR
  rakamına USD demek düzelttiğimiz hatanın ters yönü olurdu. Kesim
  artık reddediyor ve hangi döviz için kur olmadığını yazıyor.
  Pratikte yalnız arşiv O DÖVİZ için TAMAMEN boşsa devreye girer.

═══ 2 · 20 EBATLININ HEPSİ ARNAVUTLUK ÇIKIYORDU ═══

PLAKA→EBATLI kesiminde birden fazla plaka seçilebiliyor. Çıkan her
ebatlı FİZİKSEL olarak tek bir plakadan gelir — ama hepsi
`kaynaklar[0]`dan okuyordu.

ÖLÇÜLDÜ — 5.400 EUR Arnavutluk plakası + 5.400 USD Türk plakası,
20 adet 60×60:

      20 ebatlının HEPSİ menşe ALBANIA. Yarısı Türk malı.

Bu değer ticari faturaya basılıyor. KM1 tek kaynaklı hâli
düzeltmişti; çok kaynaklı hâli aynı hatayı sessizce sürdürüyordu.
Üretici ve konum da ilk kaynaktan geliyordu.

Sen "tek kesim kalsın, sistem kendi bölsün" dedin. Öyle oldu:

      menşe       döviz  parça    m²      birim       tutar  kasa
      ───────────────────────────────────────────────────────────
      ALBANIA     USD       10  3,60   1.687,50    6.075,00    10
      TURKIYE     USD       10  3,60   1.500,00    5.400,00    10
      ───────────────────────────────────────────────────────────
      TOPLAM                    7,20              11.475,00
      gerçek maliyet                              11.475,00 ✓

Her grup kendi menşesini, üreticisini, konumunu ve KENDİ kaynağının
maliyetini taşıyor. Harmanlanmış 1.593,75 ikisinin ortalamasıydı ve
hiçbir ürünün maliyeti o değildi.

  PARÇALAR BÖLÜNEMEZ. Bir 60×60 yarım plakadan çıkmaz, o yüzden her
  hedef satırının adedi kaynaklara TAM SAYI paylaştırılıyor:
  ağırlık kaynağın giren miktarı, artıklar en büyük artık yöntemiyle
  dağıtılıyor. Toplam her zaman tam tutuyor — ölçüldü, 8,0 m² ve
  2,0 m² plakadan 10 parça: 8 + 2.

  BİRİM MALİYET TAHSİSTEN SONRA hesaplanıyor: her kaynağın maliyeti
  GERÇEKTEN ona düşen m²'ye bölünüyor. Böylece paylarla maliyet
  birbirini tutuyor, yuvarlama kaymıyor.

  KASALAR MENŞE KARIŞTIRMIYOR. Kasa döngüsü artık kaynak kaynak
  dönüyor. Menşe beyanı kasa düzeyinde yapıldığı için bu gerekli.

  PAYI SIFIR KALAN KAYNAK REDDEDİLİYOR. 3 kaynak, 2 parça gibi bir
  durumda bir kaynaktan hiç parça çıkmaz ve maliyetinin gidecek yeri
  olmaz. Sessizce yutmak o maliyeti ortadan kaldırırdı.

  TEK KAYNAKLI KESİM BİREBİR AYNI. Yapıyı kaynak kaynak üretime
  çevirdim; tek kaynakta döngü bir kez dönüyor. Alan alan
  karşılaştırdım — plaka, ebatlı, kesim detayı ve kesim kaydının
  bütün alanları ÖNCE ve SONRA aynı. BLOK yönleri zaten tek kaynağa
  zorlanmış durumda, yani blok kesimlerine hiç dokunulmadı.

═══ 3 · GEÇMİŞE DOKUNULMADI ═══

"Sistemi sıfırlayacağım" dedin, göç betiği yazmadım. Şema göçü var
(kolon ekler), VERİ göçü yok. Mevcut kayıtların birim maliyeti
olduğu gibi kalıyor; yeni kesimler doğru hesaplıyor.

═══ 4 · YOL ÜSTÜNDE ÇIKAN İKİ ŞEY ═══

**Yön ile hedef tipi hiç karşılaştırılmıyordu.** PLAKA_EBATLI
yönüne PLAKA hedefi verince çağrı `int('PLK-A')` ile 500 dönüyordu.
Kötü veri üretmiyor ama kullanıcıya çıplak bir sunucu hatası
gösteriyordu. Artık ne beklendiği söylenerek reddediliyor.

**Başarı mesajı tek rakam söylüyordu.** Kaynak başına ayrı birim
maliyet olunca "1.593,75" ikisinin ortalaması oluyor. Birden fazla
kaynak varsa artık aralık yazıyor ve yanıtta kaynak dökümü
(hangi kaynaktan kaç parça, hangi menşeyle, hangi maliyetle)
dönüyor.

═══ 5 · EKRANDA ═══

  · Kaynak listesinde her satırın yanında MENŞE etiketi.
  · İki ayrı menşe seçersen özetin altında uyarı: hangi menşeden kaç
    parça çıkacağının önizlemesi. Hesap sunucudaki `_tahsis_et` ile
    aynı kural; hedef satırını değiştirince önizleme de yenileniyor.
  · Uyarı YASAK demiyor — bölünmenin ne yapacağını söylüyor.

═══ SANA BİR ŞEY DAHA — DÜZELTMEDİM ═══

Firma logosu kaydeden uçta `k.ek_bilgi` diye bir ad var ve `k`
hiçbir yerde tanımlı değil (flask_app, logo kaydet). Yani logo
kaydetmeye çalışmak NameError'a düşüyor olmalı. Bu yamanın konusu
değil, ayrı bakacağım — ama denk geldi, haberin olsun.

═══ DOĞRULANDI ═══
  261 test geçti (253 + 8). Yedisi DAVRANIŞ bakıyor: gerçek uçtan
  karışık dövizli ve karışık menşeli kesim yapıp çıkan grupları,
  paylarını ve toplamın gerçek maliyete eşitliğini ölçüyor.

  Göç ileri, geri ve ikinci kez koşuldu: kolonsuz veritabanına kolonu
  ekliyor, ikinci koşuda hiçbir şey yapmıyor, downgrade temiz
  geri alıyor.

  js · form · akış · bağlam · firma denetimleri temiz. kur ve sessiz
  denetimlerinin bulguları tabanla AYNI — yenisi yok.

DOSYALAR
--------
  flask_app.py           USD çevrimi · tahsis · kaynak başına üretim
  models.py              KesimDetay.kaynak_stok_id
  templates/kesim.html   menşe etiketi · karışık menşe önizlemesi
  tests/test_kritik.py   8 yeni test, 2 güncellenen
  migrations/versions/un2kaynakstk_kesim_detay_kaynak.py   YENİ

KULLANIM
--------
  python3 yama_un1.py            # RAPOR
  python3 yama_un1.py --uygula
  venv/bin/python -m flask --app flask_app db upgrade
  sudo systemctl restart milestone-erp
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
    'flask_app.py': 'UN1 · KESİM MALİYETİ ARTIK HER ZAMAN USD',
    'models.py': 'kaynak_stok_id  = db.Column(db.String(20), index=True)',
    'templates/kesim.html': 'UN3 · KARISIK MENSE SECIM ANINDA GORUNUR',
    'tests/test_kritik.py': 'def test_un2_karisik_mense_kaynak_basina_bolunur',
    # Goc dosyasi TAM yaziliyor; imzasi olmadan calistirici onu her
    # kosuda yeniden yazmaya calisiyor ve ikinci kosuda "yarim durum"
    # diyordu (olculdu). Kendi revision kimligi en saglam imza.
    'migrations/versions/un2kaynakstk_kesim_detay_kaynak.py':
        "revision = 'un2kaynakstk'",
}
ONKOSUL = {
    'flask_app.py': 'KR1 · TARİH DE TUTARI DEĞİŞTİRİR',
    'tests/test_kritik.py': 'def test_kr1_tarih_degisince_yeni_gunun_kuru_yazilir',
}
TAM_YAZILAN = ['migrations/versions/un2kaynakstk_kesim_detay_kaynak.py']

DEGISIKLIKLER = [
    ('flask_app.py', 'UN1 · flask_app.py blok 1',
     r'''        return t * dv_kur / usd_kur
''',
     r'''        return t * dv_kur / usd_kur

    def _usd_cevrilebilir(doviz, tarih=None):
        """UN1 — bu döviz bu tarihte USD'ye ÇEVRİLEBİLİYOR mu?

        `_usd_cevrim` kur bulamazsa tutarı OLDUĞU GİBİ döndürüp
        uyarıyla geçiyor. Maliyet ekranında bu doğru davranış: tutar
        korunur, sıfırlanmaz.

        Ama KESİM, çıkan stoğun para birimi ETİKETİNİ de USD'ye
        çeviriyor. Çevrilemeyen bir tutara USD demek, EUR rakamını
        USD diye kaydetmek olur — bu yamanın düzelttiği hatanın
        aynısını ters yönde üretirdi. Kesim bu yüzden çeviremiyorsa
        REDDEDİYOR.

        Pratikte yalnız kur arşivi O DÖVİZ için TAMAMEN boşsa False
        döner: `_kur_getir` geriye, `_en_yakin_kur` iki yöne de
        bakıyor. Yani kurulum anı dışında kesimi durdurmaz.
        """
        dv = (doviz or 'USD').upper()
        if dv == 'USD':
            return True
        if not (float(_kur_getir('USD', tarih) or 0)
                or float(_en_yakin_kur('USD', tarih) or 0)):
            return False
        if dv == 'TRY':
            return True
        return bool(float(_kur_getir(dv, tarih) or 0)
                    or float(_en_yakin_kur(dv, tarih) or 0))
'''),
    ('flask_app.py', 'UN1 · flask_app.py blok 2',
     r'''        # MATRAH'a DOKUNULMADI: burada (ve kesim ucunda) matrah
        # stogun kendi dovizinde, cevrilmeden kullaniliyor. Duzeltmek
        # USD disi bloklarda mevcut birim maliyetleri oynatir; ayri
        # bir karar, Bahadir'a soruldu.
        matrah = blok.matrah or ((blok.alis_fiyati or 0) * (blok.tonaj or 0)
                                 if blok.alis_fiyat_birim == 'ton' else
                                 (blok.alis_fiyati or 0) * (blok.hacim_m3 or 0))
        ek_top = sum(float(m.usd_karsilik or 0)
                     for m in _stok_maliyet_kalemleri(blok_id))
        yeni_toplam = (matrah or 0) + ek_top

        guncellenen = 0
        for kesim in kesimler:
''',
     r'''        # UN1 · MATRAH ARTIK USD'YE CEVRILIYOR.
        #
        # MR1'de buraya "matrah stogun kendi dovizinde, cevrilmeden
        # kullaniliyor; duzeltmek ayri bir karar" diye yazmistim.
        # Karar verildi: USD. Kesim ucunda da ayni cevrim var, iki
        # yer ayni sonucu vermeli — yoksa bloga sonradan gider
        # eklemek birim maliyeti SICRATIR.
        #
        # Tarih: bloga bagli en son maliyetin tarihi degil, KESIM
        # tarihi olmali ki kesim ucuyla ayni cikisin. Blok birden
        # fazla kez kesilmisse her kesim kendi gununden cevirir.
        matrah_ham = blok.matrah or ((blok.alis_fiyati or 0) * (blok.tonaj or 0)
                                     if blok.alis_fiyat_birim == 'ton' else
                                     (blok.alis_fiyati or 0) * (blok.hacim_m3 or 0))
        ek_top = sum(float(m.usd_karsilik or 0)
                     for m in _stok_maliyet_kalemleri(blok_id))

        guncellenen = 0
        for kesim in kesimler:
            # UN1: cevrim O KESIMIN tarihinden.
            _kt = getattr(kesim, 'kesim_tarihi', None)
            if not _usd_cevrilebilir(blok.doviz, _kt):
                # Cevrilemiyorsa YANLIS rakam yazmaktansa DOKUNMUYORUZ:
                # plakalarin mevcut (o gun dogru cevrilmis) maliyeti
                # oldugu gibi kaliyor. Kesim ucu kur olmadan kesime
                # izin vermedigi icin bu dal pratikte kurulum aninda
                # kalmis kayitlar disinda gorulmez.
                app.logger.warning(
                    f'{blok.id}: {blok.doviz} kuru yok ({_kt}) — plaka '
                    f'maliyetleri yenilenmedi')
                continue
            matrah = _usd_cevrim(matrah_ham, blok.doviz or 'USD', _kt)
            yeni_toplam = (matrah or 0) + ek_top
'''),
    ('flask_app.py', 'UN1 · flask_app.py blok 3',
     r'''                p.alis_fiyati = yeni_birim
''',
     r'''                p.alis_fiyati = yeni_birim
                # UN1: rakam USD oldu, etiket de USD olmali. Eskiden
                # plaka blogun dovizini tasiyordu ve bu satir ona USD
                # bir rakam yaziyordu — sessiz bir yalan.
                p.doviz = 'USD'
'''),
    ('flask_app.py', 'UN1 · flask_app.py blok 4',
     r'''                    'ozellik': '',  # BlokStok'ta ozellik alani yok
''',
     r'''                    # UN3: menşe listede gorunsun. Kaynak secerken
                    # karisik menşeyi FARK ETMEK, kesimden sonra
                    # ayirmaktan iyidir.
                    'mense': getattr(b, 'mense', '') or '',
                    'ozellik': '',  # BlokStok'ta ozellik alani yok
'''),
    ('flask_app.py', 'UN1 · flask_app.py blok 5',
     r'''                    'boy': p.boy, 'yukseklik': p.yukseklik, 'kalinlik': p.kalinlik,
''',
     r'''                    'mense': getattr(p, 'mense', '') or '',   # UN3
                    'boy': p.boy, 'yukseklik': p.yukseklik, 'kalinlik': p.kalinlik,
'''),
    ('flask_app.py', 'UN1 · flask_app.py blok 6',
     r'''            # ── F6 · BU KESIM HANGI SIPARIS ICIN? ──
''',
     r'''            # ── UN2 · HEDEF TIPI YONLE UYUMLU MU ──
            # Hic denetlenmiyordu. Olculdu: PLAKA_EBATLI yonune PLAKA
            # hedefi verince cagri `int('PLK-A')` ile 500 donuyor —
            # kotu veri uretmiyor ama kullaniciya cıplak bir sunucu
            # hatasi gosteriyor. Artik ne istendigi soylenerek
            # reddediliyor.
            _YON_HEDEF = {'BLOK_PLAKA': 'PLAKA', 'BLOK_EBATLI': 'EBATLI',
                          'PLAKA_EBATLI': 'EBATLI'}
            _beklenen_hedef = _YON_HEDEF[kesim_yon]
            _yanlis = sorted({(h.get('hedef_tip') or '?').upper()
                              for h in hedefler
                              if (h.get('hedef_tip') or '').upper()
                              != _beklenen_hedef})
            if _yanlis:
                return jsonify({
                    'ok': False, 'error': 'hedef_tip_uyumsuz',
                    'mesaj': f'{kesim_yon} yonunde hedef {_beklenen_hedef} '
                             f'olmali; {", ".join(_yanlis)} gonderildi.'}), 400

            # ── F6 · BU KESIM HANGI SIPARIS ICIN? ──
'''),
    ('flask_app.py', 'UN1 · flask_app.py blok 7',
     r'''            kaynak_doviz = kaynaklar[0].doviz or 'USD'
''',
     r'''            # UN1: kesim tarihi TEK yerde cozuluyor. Asagidaki USD
            # cevrimleri ve Kesim kaydinin kendisi AYNI gunu gormeli;
            # iki yerde ayri ayri parse edilse gece yarisini geciren
            # bir istek iki farkli gun yazabilirdi.
            _kesim_tarih = _parse_date(data.get('kesim_tarihi')) or date.today()
            # ══════════════════════════════════════════════════
            #  UN1 · KESİM MALİYETİ ARTIK HER ZAMAN USD
            #
            #  Burada `kaynaklar[0].doviz` vardı ve kesimin para
            #  birimi İLK kaynağın dövizi oluyordu. Altındaki toplama
            #  ise ham matrahları topluyordu: EUR blok + USD gider,
            #  ya da (çok kaynaklı plaka kesiminde) EUR plaka + USD
            #  plaka. Toplanan şey bir para birimi değildi.
            #
            #  ÖLÇÜLDÜ — 20 ton × 200,00 EUR/ton blok (4.000 EUR),
            #  bloğa 500,00 USD fason, 10,80 m² plaka çıktı;
            #  1 EUR = 45,00 TRY, 1 USD = 40,00 TRY:
            #
            #    görünen  416,67 EUR/m²   ← 500 USD, 500 EUR sayılmış
            #    doğrusu  411,52 EUR/m²
            #
            #  ÖLÇÜLDÜ — tek kesimde 5.400 EUR plaka + 5.400 USD
            #  plaka, 7,20 m² ebatlı:
            #
            #    görünen  1.500,00 EUR/m²  ← iki döviz toplanıp EUR
            #                                etiketi vurulmuş
            #    doğrusu  1.593,75 USD/m²
            #
            #  Hangi dövizde duracağı bir KARARDI, çünkü mevcut
            #  birim maliyetleri oynatıyor. Bahadır USD dedi: maliyet
            #  raporu ve `Maliyet.usd_karsilik` zaten USD, yani
            #  sistemin maliyet tarafı tek para birimine oturuyor.
            #
            #  Çevrim `_usd_cevrim` ile — maliyet ekranlarının F15'ten
            #  beri kullandığı TCMB çapraz kuru. Tarih KESİM TARİHİ:
            #  maliyet o gün sabitlenir, sonradan kur oynayınca
            #  geçmiş kesimlerin maliyeti değişmez.
            # ══════════════════════════════════════════════════
            kaynak_doviz = 'USD'
'''),
    ('flask_app.py', 'UN1 · flask_app.py blok 8',
     r'''                    for m in _stok_maliyet_kalemleri(_kid))
''',
     r'''                    for m in _stok_maliyet_kalemleri(_kid))

            # UN1 · ÇEVİREMİYORSAM KESMİYORUM.
            # Maliyet USD'ye normalize ediliyor; kur yoksa çevrilmemiş
            # bir tutara USD etiketi vurmak yerine baştan reddediyoruz.
            _kaynak_maliyet, _kaynak_miktar = {}, {}
            _cevrilemez = sorted({(k.doviz or 'USD').upper()
                                  for k in kaynaklar
                                  if not _usd_cevrilebilir(k.doviz,
                                                           _kesim_tarih)})
            if _cevrilemez:
                return jsonify({
                    'ok': False, 'error': 'kur_yok',
                    'mesaj': f'{", ".join(_cevrilemez)} için kur kaydı yok. '
                             f'Kesim maliyeti USD cinsinden tutuluyor; '
                             f'çeviremediğim tutara USD demek rakamı yanlış '
                             f'para biriminde kaydetmek olurdu. Döviz '
                             f'kurlarını güncelleyip tekrar deneyin.'}), 400
'''),
    ('flask_app.py', 'UN1 · flask_app.py blok 9',
     r'''                # Bloğa/plakaya eklenmiş ek maliyetleri (nakliye vb.) de dahil et (USD).
                maliyet += ek_maliyet_map.get(k.id, 0)
                kaynak_toplam_maliyet += maliyet
                kaynak_toplam_miktar += miktar
''',
     r'''                # UN1: matrah STOGUN KENDI dovizinde. Ek maliyetler
                # `usd_karsilik` ile USD. Ikisini toplamadan ONCE
                # matrah USD'ye cevriliyor — yukaridaki olcumler.
                maliyet = _usd_cevrim(maliyet, k.doviz or 'USD',
                                      _kesim_tarih)
                # Ek maliyetler zaten USD.
                maliyet += ek_maliyet_map.get(k.id, 0)
                kaynak_toplam_maliyet += maliyet
                kaynak_toplam_miktar += miktar
                # UN2: kaynak BASINA maliyet ve miktar. Cok kaynakli
                # kesimde her hedef TEK kaynaktan cikar ve maliyetini
                # ONDAN alir; tek bir harmanlanmis rakam her hedefe
                # digerinin maliyetini de bulastiriyordu.
                _kaynak_maliyet[k.id] = maliyet
                _kaynak_miktar[k.id] = miktar
'''),
    ('flask_app.py', 'UN1 · flask_app.py blok 10',
     r'''            birim_m2_maliyet = kaynak_toplam_maliyet / hedef_toplam_m2
''',
     r'''            birim_m2_maliyet = kaynak_toplam_maliyet / hedef_toplam_m2

            # ══════════════════════════════════════════════════════
            #  UN2 · HER HEDEF TEK BIR KAYNAKTAN CIKAR
            #
            #  PLAKA->EBATLI kesiminde birden fazla plaka seçilebiliyor.
            #  Cikan her ebatli FIZIKSEL olarak tek bir plakadan gelir;
            #  menşeini, ureticisini ve maliyetini ONDAN almasi gerekir.
            #
            #  Eskiden hepsi `kaynaklar[0]`dan aliyordu. ÖLÇÜLDÜ —
            #  5.400 EUR Arnavutluk plakasi + 5.400 USD Turk plakasi,
            #  20 adet 60x60:
            #
            #      20 ebatlinin HEPSI mense ALBANIA cikti.
            #
            #  Yarisi Turk mali. Bu deger TICARI FATURAYA basiliyor,
            #  yani 10 parca icin yanlis mense beyani. KM1 tek kaynakli
            #  hali duzeltmisti; cok kaynakli hali ayni hatayi sessizce
            #  surduruyordu.
            #
            #  PARCALAR BOLUNEMEZ. Bir 60x60 yarim plakadan cikmaz, o
            #  yuzden her hedef satirinin adedi kaynaklara TAM SAYI
            #  olarak paylastiriliyor: agirlik kaynagin giren miktari,
            #  artiklar EN BUYUK ARTIK yontemiyle dagitiliyor ki toplam
            #  tam tutsun.
            #
            #  BIRIM MALIYET TAHSISTEN SONRA hesaplaniyor: her kaynagin
            #  maliyeti GERCEKTEN ona dusen m2'ye bolunuyor. Boylece
            #  paylar ile maliyet birbirini tutar, yuvarlama kaymaz.
            #
            #  TEK KAYNAKLI KESIM AYNEN ESKISI GIBI: tek kaynak her
            #  seyi alir, birim = toplam/toplam. BLOK yonleri zaten tek
            #  kaynaga zorlanmis durumda.
            # ══════════════════════════════════════════════════════
            def _tahsis_et(toplam_adet, agirliklar):
                """`toplam_adet` parcayi agirliklara gore TAM SAYI paylastir.

                En buyuk artik yontemi: tabanlar verilir, kalan parcalar
                artigi en buyuk olana birer birer gider. Toplam her zaman
                `toplam_adet`e esittir.
                """
                _ag_top = sum(agirliklar.values())
                if _ag_top <= 0:
                    # Miktari olmayan kaynaklar: esit bol.
                    _n = len(agirliklar)
                    _pay = {kid: toplam_adet // _n for kid in agirliklar}
                    for kid in list(agirliklar)[:toplam_adet % _n]:
                        _pay[kid] += 1
                    return _pay
                _tam, _artik = {}, []
                for kid, ag in agirliklar.items():
                    _ham = toplam_adet * (ag / _ag_top)
                    _tam[kid] = int(_ham)
                    _artik.append((_ham - int(_ham), kid))
                _kalan = toplam_adet - sum(_tam.values())
                for _, kid in sorted(_artik, reverse=True)[:_kalan]:
                    _tam[kid] += 1
                return _tam

            _agirlik = {k.id: float(_kaynak_miktar.get(k.id) or 0)
                        for k in kaynaklar}
            # Satir satir tahsis; cikti m2'si kaynak basina toplanir.
            _tahsis = {}
            _cikti_m2 = {k.id: 0.0 for k in kaynaklar}
            for _hi, h in enumerate(hedefler):
                _pay = _tahsis_et(int(h.get('adet') or 1), _agirlik)
                _tahsis[_hi] = _pay
                for _kid, _n in _pay.items():
                    _cikti_m2[_kid] += _n * (h.get('_m2_birim') or 0)

            # Payi SIFIR kalan kaynak: maliyetinin gidecek yeri yok.
            # Sessizce yutmak yerine reddediyoruz.
            _bos = [k.id for k in kaynaklar if _cikti_m2.get(k.id, 0) <= 0]
            if _bos and len(kaynaklar) > 1:
                _top_parca = sum(int(h.get('adet') or 1) for h in hedefler)
                return jsonify({
                    'ok': False, 'error': 'kaynak_payi_yok',
                    'mesaj': f'{", ".join(_bos)} kaynagindan hic parca '
                             f'cikmiyor ({len(kaynaklar)} kaynak, '
                             f'{_top_parca} parca). Her kaynaktan en az '
                             f'bir parca cikmali; parca sayisini artirin '
                             f'ya da kaynaklari ayri ayri kesin.'}), 400

            _birim_kaynak = {
                k.id: (float(_kaynak_maliyet.get(k.id) or 0)
                       / _cikti_m2[k.id]) if _cikti_m2.get(k.id) else 0.0
                for k in kaynaklar}
            _kaynak_map = {k.id: k for k in kaynaklar}
'''),
    ('flask_app.py', 'UN1 · flask_app.py blok 11',
     r'''                kesim_tarihi=_parse_date(data.get('kesim_tarihi')) or date.today(),
''',
     r'''                kesim_tarihi=_kesim_tarih,
'''),
    ('flask_app.py', 'UN1 · flask_app.py blok 12',
     r'''            for h in hedefler:
                hedef_tip = (h.get('hedef_tip') or '').upper()
''',
     r'''            for _hedef_sira, h in enumerate(hedefler):
                hedef_tip = (h.get('hedef_tip') or '').upper()
'''),
    ('flask_app.py', 'UN1 · flask_app.py blok 13',
     r'''                if hedef_tip == 'PLAKA':
                    # PLAKA: her parca ayri bir plaka stok kaydi olur
                    for i in range(adet):
                        slab_int = _sonraki_slab()
                        etiket = f'{slab_int}/{adet}'
                        # RN1: üretim blok no + plaka no (PLK-T77-U1-03)
                        plk_id = _stok_okunur_id('PLK', PlakaStok,
                                                 uretim_blok_no or ana_kaynak.blok_no,
                                                 slab_int)
                        plk = PlakaStok(
                            id=plk_id, cins=cins, uretici=ana_kaynak.uretici,
                            boy=boy, yukseklik=yukseklik, kalinlik=kalinlik,
                            metraj_m2=m2_birim, metraj_sqft=m2_birim * 10.7639 if m2_birim else 0,
                            blok_no=uretim_blok_no, ozellik=ozellik,
                            slab_no=slab_int,
                            alis_fiyati=birim_m2_maliyet,
                            doviz=kaynak_doviz, konum=ana_kaynak.konum,
                            durum='Serbest',
                            # KK1 (eski adiyla KS1 — o ad stok.html'de
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
                            aciklama=f'Kesim {kesim_id} ({uretim_blok_no}-{slab_int}) | Orijinal Blok: {ana_kaynak.blok_no or ana_kaynak.id}',
                            kullanici=session.get('kullanici')
                        )
                        db.session.add(plk)
                        olusan_stoklar.append({'tip': 'PLAKA', 'id': plk_id, 'm2': m2_birim, 'etiket': f'{uretim_blok_no}-{slab_int}'})
                        kd = KesimDetay(
                            kesim_id=kesim_id, hedef_tip='PLAKA', hedef_stok_id=plk_id,
                            cins=cins, boy=boy, yukseklik=yukseklik, kalinlik=kalinlik,
                            miktar_m2=m2_birim, adet=1,
                            slab_no=str(slab_int), ozellik=ozellik,
                            birim_maliyet=birim_m2_maliyet,
                            toplam_maliyet=m2_birim * birim_m2_maliyet
                        )
                        db.session.add(kd)
                else:
                    # EBATLI: adet = toplam parca, kasa_ici_adet = bir kasada kac parca
                    # Kasa sayisi = ceil(adet / kasa_ici_adet)
                    # ornek: 6 parca, kasa_ici 10 -> 1 kasa (6 parca icinde)
                    #         18 parca, kasa_ici 10 -> 2 kasa (10 + 8)
                    if kasa_ici_adet < 1:
                        kasa_ici_adet = 1
                    import math as _math
                    kasa_sayisi = _math.ceil(adet / kasa_ici_adet)
                    kalan = adet  # dagitilacak toplam parca

                    # Tum kasalar icin tek seferde referans kodlari uret (sirali olsun)
                    try:
                        ref_kodlar = _referans_kodu_uret(
                            ana_kaynak.uretici or 'XXX',
                            cins or ana_kaynak.cins or 'XXX',
                            boy, yukseklik, kalinlik,
                            adet=kasa_sayisi
                        )
                    except Exception as ex:
                        app.logger.warning(f'Referans kodu uretilemedi: {type(ex).__name__}: {ex}')
                        ref_kodlar = []

                    for k_idx in range(kasa_sayisi):
                        # Bu kasada kac parca?
                        bu_kasa_parca = min(kasa_ici_adet, kalan)
                        kalan -= bu_kasa_parca

                        # Kasa no - referans kodu listesinden al, yoksa fallback
                        if k_idx < len(ref_kodlar) and ref_kodlar[k_idx]:
                            kasa_no = ref_kodlar[k_idx]
                        else:
                            try:
                                urt_kis = _uretici_kisaltma(ana_kaynak.uretici or 'XXX')
                                cks_kis = _cins_kisaltma(cins or 'XXX')
                                by_int = int(boy or 0)
                                yk_int = int(yukseklik or 0)
                                kk_int = int(round((kalinlik or 0) * 10))
                                kasa_no = f'{urt_kis}-{cks_kis}{by_int}{yk_int}{kk_int}A-{kasa_sayac}'
                            except Exception:
                                kasa_no = f'EBT-{kasa_sayac:04d}'
                            kasa_sayac += 1

                        kasa_m2 = m2_birim * bu_kasa_parca
                        ebt = EbatliStok(
                            id=_stok_okunur_id('EBT', EbatliStok, kasa_no),   # RN1
                            cins=cins, uretici=ana_kaynak.uretici,
                            boy=boy, yukseklik=yukseklik, kalinlik=kalinlik,
                            metraj_m2=kasa_m2, kasa_no=kasa_no,
                            kasa_ici_adet=bu_kasa_parca,
                            ozellik=ozellik,
                            alis_fiyati=birim_m2_maliyet,
                            doviz=kaynak_doviz, konum=ana_kaynak.konum,
                            durum='Serbest',
                            kaynak='kesim',          # KK1 — bkz. plaka
                            mense=_kesim_mense(ana_kaynak),   # KM1
                            aciklama=f'Kesim {kesim_id} - Üretim Blok: {uretim_blok_no} | Orijinal: {getattr(ana_kaynak, "blok_no", "") or ana_kaynak.id}',
                            kullanici=session.get('kullanici')
                        )
                        db.session.add(ebt)
                        olusan_stoklar.append({
                            'tip': 'EBATLI', 'id': ebt.id, 'kasa_no': kasa_no,
                            'kasa_ici_adet': bu_kasa_parca,
                            'm2_toplam': kasa_m2
                        })
                        kd = KesimDetay(
                            kesim_id=kesim_id, hedef_tip='EBATLI', hedef_stok_id=ebt.id,
                            cins=cins, boy=boy, yukseklik=yukseklik, kalinlik=kalinlik,
                            miktar_m2=m2_birim, adet=bu_kasa_parca,
                            kasa_no=kasa_no, ozellik=ozellik,
                            birim_maliyet=birim_m2_maliyet,
                            toplam_maliyet=kasa_m2 * birim_m2_maliyet
                        )
                        db.session.add(kd)
''',
     r'''                # ── UN2 · KAYNAK KAYNAK URET ──
                # Bu satirin adedi kaynaklara TAM SAYI paylastirildi;
                # her pay KENDI kaynagiyla uretiliyor, yani menşe,
                # uretici, konum ve birim maliyet o kaynaktan geliyor.
                # Tek kaynakli kesimde dongu bir kez doner ve sonuc
                # eskisiyle AYNIDIR.
                for _kid, _pay_adet in _tahsis[_hedef_sira].items():
                    if _pay_adet <= 0:
                        continue
                    _kay = _kaynak_map[_kid]
                    _birim_kay = _birim_kaynak[_kid]
                    if hedef_tip == 'PLAKA':
                        # PLAKA: her parca ayri bir plaka stok kaydi olur
                        for i in range(_pay_adet):
                            slab_int = _sonraki_slab()
                            etiket = f'{slab_int}/{adet}'
                            # RN1: üretim blok no + plaka no (PLK-T77-U1-03)
                            plk_id = _stok_okunur_id('PLK', PlakaStok,
                                                     uretim_blok_no or _kay.blok_no,
                                                     slab_int)
                            plk = PlakaStok(
                                id=plk_id, cins=cins, uretici=_kay.uretici,
                                boy=boy, yukseklik=yukseklik, kalinlik=kalinlik,
                                metraj_m2=m2_birim, metraj_sqft=m2_birim * 10.7639 if m2_birim else 0,
                                blok_no=uretim_blok_no, ozellik=ozellik,
                                slab_no=slab_int,
                                alis_fiyati=_birim_kay,
                                doviz=kaynak_doviz, konum=_kay.konum,
                                durum='Serbest',
                                # KK1 (eski adiyla KS1 — o ad stok.html'de
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
                                mense=_kesim_mense(_kay),
                                aciklama=f'Kesim {kesim_id} ({uretim_blok_no}-{slab_int}) | Orijinal Blok: {_kay.blok_no or _kay.id}',
                                kullanici=session.get('kullanici')
                            )
                            db.session.add(plk)
                            olusan_stoklar.append({'tip': 'PLAKA', 'id': plk_id, 'm2': m2_birim, 'etiket': f'{uretim_blok_no}-{slab_int}'})
                            kd = KesimDetay(
                                kesim_id=kesim_id, hedef_tip='PLAKA', hedef_stok_id=plk_id,
                                cins=cins, boy=boy, yukseklik=yukseklik, kalinlik=kalinlik,
                                miktar_m2=m2_birim, adet=1,
                                slab_no=str(slab_int), ozellik=ozellik,
                                birim_maliyet=_birim_kay,
                                toplam_maliyet=m2_birim * _birim_kay,
                                kaynak_stok_id=_kay.id          # UN2
                            )
                            db.session.add(kd)
                    else:
                        # EBATLI: adet = toplam parca, kasa_ici_adet = bir kasada kac parca
                        # Kasa sayisi = ceil(adet / kasa_ici_adet)
                        # ornek: 6 parca, kasa_ici 10 -> 1 kasa (6 parca icinde)
                        #         18 parca, kasa_ici 10 -> 2 kasa (10 + 8)
                        if kasa_ici_adet < 1:
                            kasa_ici_adet = 1
                        import math as _math
                        kasa_sayisi = _math.ceil(_pay_adet / kasa_ici_adet)
                        kalan = _pay_adet  # bu kaynaga dusen parca

                        # Tum kasalar icin tek seferde referans kodlari uret (sirali olsun)
                        try:
                            ref_kodlar = _referans_kodu_uret(
                                _kay.uretici or 'XXX',
                                cins or _kay.cins or 'XXX',
                                boy, yukseklik, kalinlik,
                                adet=kasa_sayisi
                            )
                        except Exception as ex:
                            app.logger.warning(f'Referans kodu uretilemedi: {type(ex).__name__}: {ex}')
                            ref_kodlar = []

                        for k_idx in range(kasa_sayisi):
                            # Bu kasada kac parca?
                            bu_kasa_parca = min(kasa_ici_adet, kalan)
                            kalan -= bu_kasa_parca

                            # Kasa no - referans kodu listesinden al, yoksa fallback
                            if k_idx < len(ref_kodlar) and ref_kodlar[k_idx]:
                                kasa_no = ref_kodlar[k_idx]
                            else:
                                try:
                                    urt_kis = _uretici_kisaltma(_kay.uretici or 'XXX')
                                    cks_kis = _cins_kisaltma(cins or 'XXX')
                                    by_int = int(boy or 0)
                                    yk_int = int(yukseklik or 0)
                                    kk_int = int(round((kalinlik or 0) * 10))
                                    kasa_no = f'{urt_kis}-{cks_kis}{by_int}{yk_int}{kk_int}A-{kasa_sayac}'
                                except Exception:
                                    kasa_no = f'EBT-{kasa_sayac:04d}'
                                kasa_sayac += 1

                            kasa_m2 = m2_birim * bu_kasa_parca
                            ebt = EbatliStok(
                                id=_stok_okunur_id('EBT', EbatliStok, kasa_no),   # RN1
                                cins=cins, uretici=_kay.uretici,
                                boy=boy, yukseklik=yukseklik, kalinlik=kalinlik,
                                metraj_m2=kasa_m2, kasa_no=kasa_no,
                                kasa_ici_adet=bu_kasa_parca,
                                ozellik=ozellik,
                                alis_fiyati=_birim_kay,
                                doviz=kaynak_doviz, konum=_kay.konum,
                                durum='Serbest',
                                kaynak='kesim',          # KK1 — bkz. plaka
                                mense=_kesim_mense(_kay),   # KM1
                                aciklama=f'Kesim {kesim_id} - Üretim Blok: {uretim_blok_no} | Orijinal: {getattr(_kay, "blok_no", "") or _kay.id}',
                                kullanici=session.get('kullanici')
                            )
                            db.session.add(ebt)
                            olusan_stoklar.append({
                                'tip': 'EBATLI', 'id': ebt.id, 'kasa_no': kasa_no,
                                'kasa_ici_adet': bu_kasa_parca,
                                'm2_toplam': kasa_m2
                            })
                            kd = KesimDetay(
                                kesim_id=kesim_id, hedef_tip='EBATLI', hedef_stok_id=ebt.id,
                                cins=cins, boy=boy, yukseklik=yukseklik, kalinlik=kalinlik,
                                miktar_m2=m2_birim, adet=bu_kasa_parca,
                                kasa_no=kasa_no, ozellik=ozellik,
                                birim_maliyet=_birim_kay,
                                toplam_maliyet=kasa_m2 * _birim_kay,
                                kaynak_stok_id=_kay.id          # UN2
                            )
                            db.session.add(kd)
'''),
    ('flask_app.py', 'UN1 · flask_app.py blok 14',
     r'''                'siparis_id': _uretim_siparis_id,
                'mesaj': f'✅ Kesim tamam: {len(olusan_stoklar)} hedef stok olustu. Birim maliyet: {birim_m2_maliyet:.2f} {kaynak_doviz}/m²'
''',
     r'''                # UN2: hangi kaynaktan kac parca, hangi menşeyle,
                # hangi birim maliyetle. Ekran bunu gosterebilsin.
                'kaynak_dokumu': [
                    {'kaynak_id': _k.id,
                     'mense': _kesim_mense(_k),
                     'uretici': _k.uretici,
                     'parca': sum(_t.get(_k.id, 0)
                                  for _t in _tahsis.values()),
                     'cikti_m2': q2(_cikti_m2.get(_k.id, 0)),
                     'birim_maliyet': q2(_birim_kaynak.get(_k.id, 0)),
                     'doviz': kaynak_doviz}
                    for _k in kaynaklar],
                'siparis_id': _uretim_siparis_id,
                # UN2: kaynak basina ayri birim maliyet olusunca TEK
                # bir rakam yaniltici oluyor — 1.687,50 ve 1.500,00
                # cikan bir kesimde "1.593,75" ikisinin ortalamasidir
                # ve hicbir urunun maliyeti o degildir. Birden fazla
                # kaynak varsa aralik, yoksa tek rakam yaziliyor.
                'mesaj': f'✅ Kesim tamam: {len(olusan_stoklar)} hedef stok '
                         f'olustu. Birim maliyet: ' + (
                             f'{min(_birim_kaynak.values()):.2f}–'
                             f'{max(_birim_kaynak.values()):.2f} '
                             f'{kaynak_doviz}/m² ({len(kaynaklar)} kaynak, '
                             f'her urun kendi kaynaginin maliyetini tasiyor)'
                             if len(set(round(v, 2) for v
                                        in _birim_kaynak.values())) > 1
                             else f'{birim_m2_maliyet:.2f} {kaynak_doviz}/m²')
'''),
    ('models.py', 'UN1 · models.py blok 1',
     r'''    cins            = db.Column(db.String(50))
''',
     r'''    # UN2: bu hedef HANGI kaynaktan cikti. Cok kaynakli kesimde
    # (PLAKA->EBATLI) her hedef tek bir kaynaktan gelir ve menşeini,
    # ureticisini, maliyetini ONDAN alir. Kolon olmadan "hepsi ilk
    # kaynaktan" varsayimi kaciniimazdi.
    kaynak_stok_id  = db.Column(db.String(20), index=True)
    cins            = db.Column(db.String(50))
'''),
    ('templates/kesim.html', 'UN1 · templates/kesim.html blok 1',
     r'''  @media (max-width:820px){ .f3,.f4{grid-template-columns:1fr 1fr} }
''',
     r'''  /* UN3 · MENSE. Etiket kaynak satirinda, uyari ozetin altinda.
     Karisik mense YASAK DEGIL — sunucu her hedefi kendi kaynagindan
     uretiyor — ama ne olacagi onceden yazilmali. */
  .mense-et{display:inline-block;padding:0 5px;border-radius:3px;
    background:var(--cizgi);color:var(--metin);font-size:.68rem;
    font-weight:600;letter-spacing:.02em}
  .mense-uyari{margin-top:8px;border-radius:var(--r-kucuk);
    padding:9px 12px;font-size:.78rem;background:var(--kehribar-bg);
    color:var(--kehribar);border:1px solid var(--kehribar)}
  .mense-uyari b{font-weight:700}
  .mense-uyari ul{margin:6px 0 0;padding-left:18px}
  @media (max-width:820px){ .f3,.f4{grid-template-columns:1fr 1fr} }
'''),
    ('templates/kesim.html', 'UN1 · templates/kesim.html blok 2',
     r'''        <div style="margin-top:8px;font-size:.8rem;color:var(--soluk)" id="kaynakOzet">Kaynak seçilmedi</div>
''',
     r'''        <div style="margin-top:8px;font-size:.8rem;color:var(--soluk)" id="kaynakOzet">Kaynak seçilmedi</div>
        <div class="mense-uyari" id="menseUyari" hidden></div>
'''),
    ('templates/kesim.html', 'UN1 · templates/kesim.html blok 3',
     r'''        <div style="color:var(--soluk);font-size:.75rem">${kacar(k.id)}${k.uretici ? ' · ' + kacar(k.uretici) : ''}</div>
''',
     r'''        <div style="color:var(--soluk);font-size:.75rem">${kacar(k.id)}${k.uretici ? ' · ' + kacar(k.uretici) : ''}${k.mense ? ' · <span class="mense-et">' + kacar(k.mense) + '</span>' : ''}</div>
'''),
    ('templates/kesim.html', 'UN1 · templates/kesim.html blok 4',
     r'''function kaynakOzetCiz() {
''',
     r'''/* UN3 · KARISIK MENSE SECIM ANINDA GORUNUR.
   Sunucu artik her hedefi KENDI kaynagindan uretiyor (UN2), yani
   karisik menseli kesim yasak degil — ama ne olacagini ONCEDEN
   soylemek gerekiyor: hangi menseden kac parca cikacak. Pay, kaynagin
   giren miktariyla orantili; burada ayni hesap gosteriliyor. */
function menseDagilimi(secilenler, toplamParca) {
  const ag = secilenler.map(k => ({
    k, w: (k.tonaj || 0) > 0 ? k.tonaj : (k.mevcut || 0)
  }));
  const top = ag.reduce((a, x) => a + x.w, 0);
  if (!top || !toplamParca) return [];
  // En buyuk artik — sunucudaki `_tahsis_et` ile ayni kural
  const ham = ag.map(x => ({ ...x, h: toplamParca * (x.w / top) }));
  const pay = ham.map(x => ({ ...x, n: Math.floor(x.h) }));
  let kalan = toplamParca - pay.reduce((a, x) => a + x.n, 0);
  pay.map((x, i) => ({ i, art: x.h - Math.floor(x.h) }))
     .sort((a, b) => b.art - a.art)
     .slice(0, kalan)
     .forEach(x => { pay[x.i].n += 1; });
  const grup = {};
  pay.forEach(x => {
    const ms = x.k.mense || '—';
    grup[ms] = (grup[ms] || 0) + x.n;
  });
  return Object.entries(grup).sort();
}

function menseUyarisiCiz(secilenler) {
  const el = document.getElementById('menseUyari');
  if (!el) return;
  const menseler = [...new Set(secilenler.map(k => k.mense || '—'))];
  if (secilenler.length < 2 || menseler.length < 2) { el.hidden = true; return; }
  const toplamParca = HEDEFLER.reduce((a, h) => a + (h.adet || 0), 0);
  const dagilim = menseDagilimi(secilenler, toplamParca);
  el.hidden = false;
  el.innerHTML =
    `<b>${menseler.length} ayrı menşe seçildi.</b> Çıkan ürünler menşelerine `
    + `göre AYRI gruplara bölünür; her grup kendi kaynağının menşesini, `
    + `üreticisini ve maliyetini taşır. Kasalar menşe karıştırmaz.`
    + (dagilim.length
        ? '<ul>' + dagilim.map(([ms, n]) =>
            `<li>${kacar(ms)} — ${n} parça</li>`).join('') + '</ul>'
        : '<div style="margin-top:4px">Hedef satırı girince dağılım burada görünecek.</div>');
}

function kaynakOzetCiz() {
'''),
    ('templates/kesim.html', 'UN1 · templates/kesim.html blok 5',
     r'''  document.getElementById('uretimNoOrijinal').textContent =
''',
     r'''  menseUyarisiCiz(secilenler);
  document.getElementById('uretimNoOrijinal').textContent =
'''),
    ('templates/kesim.html', 'UN1 · templates/kesim.html blok 6',
     r'''    (maliyet > 0 && cikanM2 > 0) ? para2(maliyet / cikanM2) + ' /m²' : '—';
''',
     r'''    (maliyet > 0 && cikanM2 > 0) ? para2(maliyet / cikanM2) + ' /m²' : '—';
  /* UN3: dagilim HEDEF ADEDINE bagli — hedef satiri degisince
     uyarinin da yenilenmesi gerekiyor, yoksa eski parca sayisini
     gosterir. Ayni seyin iki yerde farkli gorunmesi. */
  menseUyarisiCiz(secilenler);
'''),
    ('tests/test_kritik.py', 'UN1 · tests/test_kritik.py blok 1',
     r'''            assert (p.doviz or '').upper() == 'EUR'
''',
     r'''            # UN1: plaka artik blogun dovizini DEGIL, USD tasiyor.
            # Menşe kaynaktan gelir, PARA BIRIMI gelmez — maliyetin
            # tamami tek para biriminde tutuluyor.
            assert (p.doviz or '').upper() == 'USD', \
                f'{p.id} dövizi {p.doviz!r} — maliyet USD olmalı'
'''),
    ('tests/test_kritik.py', 'UN1 · tests/test_kritik.py blok 2',
     r'''    assert _r.count('mense=_kesim_mense(ana_kaynak)') == 2, \
        'her iki hedef tipi de ortak kapıdan geçmiyor'
''',
     r'''    # UN2: menşe artik `ana_kaynak`tan DEGIL, o hedefin KENDI
    # kaynagindan (`_kay`) geliyor — cok kaynakli kesimde hepsi ilk
    # kaynagin menşeini aliyordu. Test KAPIYI tutuyor, adi degil:
    # iki hedef tipi de `_kesim_mense` uzerinden gecmeli.
    assert _r.count('mense=_kesim_mense(_kay)') == 2, \
        'her iki hedef tipi de ortak kapıdan geçmiyor'
    assert 'mense=_kesim_mense(ana_kaynak)' not in _r, \
        'hâlâ ilk kaynaktan okunuyor'
'''),
    ('tests/test_kritik.py', 'UN1 · tests/test_kritik.py blok 3',
     r'''    assert abs(kayit[0]['kalan'] - 9500.0) < 0.02, kayit[0]['kalan']
''',
     r'''    assert abs(kayit[0]['kalan'] - 9500.0) < 0.02, kayit[0]['kalan']


# ══════════════════════════════════════════════════════════════════
#  UN1 · KESİM MALİYETİ HER ZAMAN USD
#
#  Blok/plaka matrahı stoğun kendi dövizinde tutuluyor; bloğa işlenen
#  ek maliyetler `usd_karsilik` ile USD. Dağıtıcı ikisini TOPLUYORDU,
#  yani toplanan şey bir para birimi değildi.
#
#  Karar (Bahadır): her şey USD'ye normalize edilsin. Maliyet raporu
#  ve `Maliyet.usd_karsilik` zaten USD.
# ══════════════════════════════════════════════════════════════════
_UN1_T = date(2026, 5, 7)     # baska test bu gune kur yazmiyor
_UN1_EUR, _UN1_USD = 45.0, 40.0


def _un1_kurlar():
    from models import DovizKur
    for _dv, _k in (('USD', _UN1_USD), ('EUR', _UN1_EUR)):
        if not DovizKur.query.filter_by(doviz=_dv, tarih=_UN1_T).first():
            db.session.add(DovizKur(doviz=_dv, tarih=_UN1_T,
                                    alis=_k, satis=_k, efektif=_k))


def test_un1_eur_blok_kesiminde_gider_cevrilir():
    """EUR bloğa işlenen USD fason, EUR sayılmamalı.

    ÖLÇÜLDÜ — 4.000,00 EUR matrah + 500,00 USD fason, 10,80 m²;
    1 EUR = 45, 1 USD = 40 (yani 1 EUR = 1,125 USD):

        önce   416,67  ← 500 USD, 500 EUR sayılmış, etiket EUR
        sonra  462,96 USD  = (4.500,00 + 500,00) / 10,80 ✓
    """
    from models import PlakaStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _un1_kurlar()
        db.session.add(BlokStok(
            id='BLK-UN1', firma_id=1, blok_no='UN1', cins='UN1TEST',
            uretici='OCAK', mense='ALBANIA',
            boy=300, yukseklik=180, en=170, hacim_m3=9.18, tonaj=20,
            alis_fiyati=200, alis_fiyat_birim='ton', matrah=4000,
            doviz='EUR', durum='Serbest', giris_tarihi=_UN1_T))
        db.session.commit()

    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': ['BLK-UN1'],
        'kesim_tarihi': _UN1_T.isoformat(),
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'UN1TEST', 'boy': 300,
                      'yukseklik': 180, 'kalinlik': 2, 'adet': 2}]})
    assert r.status_code == 200, r.get_json()

    # Bloga 500 USD fason: dagitici matrah + ek_top yapiyor
    r2 = c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Fason', 'baglanti_tip': 'stok',
        'baglanti_id': 'BLK-UN1', 'tutar': 500, 'doviz': 'USD',
        'maliyet_tarihi': _UN1_T.isoformat(), 'fatura_no': 'UN1-FSN'})
    assert r2.status_code in (200, 201), r2.get_json()

    with fa.app.app_context():
        pl = PlakaStok.query.filter_by(cins='UN1TEST').all()
        assert len(pl) == 2, len(pl)
        _m2 = sum(float(p.metraj_m2 or 0) for p in pl)
        _eur_usd = _UN1_EUR / _UN1_USD
        _beklenen = (4000 * _eur_usd + 500) / _m2
        _karisik = (4000 + 500) / _m2
        for p in pl:
            assert (p.doviz or '').upper() == 'USD', p.doviz
            _b = float(p.alis_fiyati or 0)
            assert abs(_b - _beklenen) < 0.02, \
                f'{p.id} birim {_b:,.2f} — beklenen {_beklenen:,.2f}; ' \
                f'{_karisik:,.2f} ise ham toplanmış demektir'


def test_un1_karisik_dovizli_kesim_cevrilerek_toplanir():
    """Tek kesimde EUR plaka + USD plaka: her grup KENDİ maliyetini alır.

    ÖLÇÜLDÜ — 5.400,00 EUR (Arnavutluk) + 5.400,00 USD (Türk),
    20 adet 60×60 (toplam 7,20 m²); 1 EUR = 45, 1 USD = 40:

        önce   hepsi 1.500,00 EUR  ← iki döviz ham toplanıp EUR
                                     etiketi vurulmuş
        sonra  Arnavutluk 3,60 m² × 1.687,50 USD = 6.075,00
               Türk       3,60 m² × 1.500,00 USD = 5.400,00
                                      toplam    = 11.475,00 ✓

    Harmanlanmış 1.593,75 ortalamadır; iki grup fiziksel olarak ayrı
    malzemeden geldiği için her biri kendi kaynağının maliyetini
    taşır (UN2).
    """
    from models import PlakaStok, EbatliStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _un1_kurlar()
        for _id, _dv, _mense in (('PLK-UN1E', 'EUR', 'ALBANIA'),
                                 ('PLK-UN1U', 'USD', 'TURKIYE')):
            db.session.add(PlakaStok(
                id=_id, firma_id=1, cins='UN2TEST', slab_no=_id,
                mense=_mense, boy=300, yukseklik=180, kalinlik=2,
                metraj_m2=5.4, alis_fiyati=1000, matrah=5400,
                doviz=_dv, durum='Serbest', giris_tarihi=_UN1_T))
        db.session.commit()

    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'PLAKA_EBATLI',
        'kaynak_ids': ['PLK-UN1E', 'PLK-UN1U'],
        'kesim_tarihi': _UN1_T.isoformat(),
        'hedefler': [{'hedef_tip': 'EBATLI', 'cins': 'UN2TEST', 'boy': 60,
                      'yukseklik': 60, 'kalinlik': 2, 'adet': 20}]})
    assert r.status_code == 200, r.get_json()

    _eur_usd = _UN1_EUR / _UN1_USD
    with fa.app.app_context():
        eb = EbatliStok.query.filter_by(cins='UN2TEST').all()
        assert eb, 'ebatlı oluşmadı'
        # Her parca USD etiketli
        for e in eb:
            assert (e.doviz or '').upper() == 'USD', e.doviz
        # Menşeye gore gruplar
        _grup = {}
        for e in eb:
            _g = _grup.setdefault(e.mense or '?', {'m2': 0.0, 'tutar': 0.0})
            _g['m2'] += float(e.metraj_m2 or 0)
            _g['tutar'] += float(e.metraj_m2 or 0) * float(e.alis_fiyati or 0)
        assert set(_grup) == {'ALBANIA', 'TURKIYE'}, \
            f'menşeler {sorted(_grup)} — hepsi ilk kaynaktan gelmiş olabilir'
        # Her grup KENDI kaynaginin maliyetini tasiyor
        assert abs(_grup['ALBANIA']['tutar'] - 5400 * _eur_usd) < 0.05, \
            _grup['ALBANIA']
        assert abs(_grup['TURKIYE']['tutar'] - 5400) < 0.05, _grup['TURKIYE']
        # Ve toplam gercek maliyete esit: para ne kayboluyor ne doguyor
        _toplam = sum(g['tutar'] for g in _grup.values())
        assert abs(_toplam - (5400 * _eur_usd + 5400)) < 0.05, _toplam
        # Ham toplama olsaydi toplam 10.800 olurdu
        assert _toplam > 11000, _toplam


def test_un1_kur_yoksa_kesim_reddedilir():
    """Çeviremiyorsa USD etiketi vurmak yerine reddetmeli.

    `_usd_cevrim` kur bulamazsa tutarı olduğu gibi döndürüyor. Etiket
    USD'ye çevrildiği için bu, EUR rakamını USD diye kaydetmek olurdu
    — düzelttiğimiz hatanın ters yönü."""
    from models import DovizKur, PlakaStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        # Arsivde HIC kaydi olmayan bir doviz
        assert not DovizKur.query.filter_by(doviz='CHF').first()
        db.session.add(BlokStok(
            id='BLK-UN3', firma_id=1, blok_no='UN3', cins='UN3TEST',
            uretici='OCAK', mense='SWITZERLAND',
            boy=300, yukseklik=180, en=170, hacim_m3=9.18, tonaj=20,
            alis_fiyati=200, alis_fiyat_birim='ton', matrah=4000,
            doviz='CHF', durum='Serbest', giris_tarihi=_UN1_T))
        db.session.commit()

    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': ['BLK-UN3'],
        'kesim_tarihi': _UN1_T.isoformat(),
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'UN3TEST', 'boy': 300,
                      'yukseklik': 180, 'kalinlik': 2, 'adet': 2}]})
    assert r.status_code == 400, r.status_code
    _y = r.get_json()
    assert _y.get('error') == 'kur_yok', _y
    assert 'CHF' in _y.get('mesaj', ''), _y.get('mesaj')
    with fa.app.app_context():
        assert PlakaStok.query.filter_by(cins='UN3TEST').count() == 0, \
            'kesim reddedildi ama plaka oluşmuş'
        assert (db.session.get(BlokStok, 'BLK-UN3').durum or '') == 'Serbest'


# ══════════════════════════════════════════════════════════════════
#  UN2 · HER HEDEF TEK BİR KAYNAKTAN ÇIKAR
#
#  PLAKA→EBATLI kesiminde birden fazla plaka seçilebiliyor. Çıkan her
#  ebatlı fiziksel olarak TEK bir plakadan gelir; menşeini, üreticisini
#  ve maliyetini ondan almalı. Eskiden hepsi `kaynaklar[0]`dan alıyordu
#  ve karışık menşeli kesimde ticari faturaya yanlış menşe basılıyordu.
#
#  Karar (Bahadır): tek kesim kalsın, sistem kaynak başına ayrı grup
#  üretsin.
# ══════════════════════════════════════════════════════════════════
def _un2_plakalar(ids_mense_m2, cins='UN4TEST'):
    """(id, mense, m2) uclulerinden USD plakalar — doviz sabit USD ki
    bu testler YALNIZ bolunmeyi olcsun, UN1 cevrimini degil."""
    from models import PlakaStok
    for _id, _ms, _m2 in ids_mense_m2:
        db.session.add(PlakaStok(
            id=_id, firma_id=1, cins=cins, slab_no=_id, mense=_ms,
            uretici='OCAK-' + _ms[:3], boy=300, yukseklik=180, kalinlik=2,
            metraj_m2=_m2, alis_fiyati=1000, matrah=1000 * _m2,
            doviz='USD', durum='Serbest', giris_tarihi=_UN1_T))


def test_un2_karisik_mense_kaynak_basina_bolunur():
    """İki menşeli kesim, iki menşeli grup üretmeli — tek değil.

    ÖLÇÜLDÜ (düzeltmeden önce): 20 ebatlının HEPSİ ALBANIA çıkıyordu,
    yarısı Türk malı olduğu hâlde. Bu değer ticari faturaya basılıyor."""
    from models import EbatliStok, KesimDetay
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _un1_kurlar()
        _un2_plakalar([('PLK-UN2A', 'ALBANIA', 5.4),
                       ('PLK-UN2T', 'TURKIYE', 5.4)])
        db.session.commit()
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'PLAKA_EBATLI',
        'kaynak_ids': ['PLK-UN2A', 'PLK-UN2T'],
        'kesim_tarihi': _UN1_T.isoformat(),
        'hedefler': [{'hedef_tip': 'EBATLI', 'cins': 'UN4TEST', 'boy': 60,
                      'yukseklik': 60, 'kalinlik': 2, 'adet': 20,
                      'kasa_ici_adet': 5}]})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        eb = EbatliStok.query.filter_by(cins='UN4TEST').all()
        assert eb, 'ebatlı oluşmadı'
        _ms = {e.mense for e in eb}
        assert _ms == {'ALBANIA', 'TURKIYE'}, \
            f'menşeler {_ms} — bölünme olmamış, ticari faturaya yanlış basar'
        # Parca sayisi korunmali: ne kayboldu ne dogdu
        assert sum(int(e.kasa_ici_adet or 0) for e in eb) == 20, \
            [int(e.kasa_ici_adet or 0) for e in eb]
        # KASALAR KAYNAK KARISTIRMAZ: her kasanin tek bir menşesi var
        for e in eb:
            assert e.mense in ('ALBANIA', 'TURKIYE')
        # Üretici de kendi kaynagindan
        for e in eb:
            assert e.uretici == 'OCAK-' + (e.mense or '')[:3], \
                f'{e.id} üretici {e.uretici!r} menşe {e.mense!r}'
        # KesimDetay hangi kaynaktan cikti SOYLUYOR
        _dt = KesimDetay.query.filter_by(cins='UN4TEST').all()
        assert _dt, 'kesim detayı yok'
        assert all(d.kaynak_stok_id in ('PLK-UN2A', 'PLK-UN2T')
                   for d in _dt), [d.kaynak_stok_id for d in _dt]
        assert len({d.kaynak_stok_id for d in _dt}) == 2


def test_un2_paylar_agirliga_gore_ve_toplam_tam():
    """Pay, kaynağın giren m²'siyle orantılı; toplam tam tutmalı.

    PLK 8,0 m² ve PLK 2,0 m² → 10 parçanın 8'i birinciden, 2'si
    ikinciden. Parçalar bölünemez, o yüzden tam sayı paylaştırma
    (en büyük artık) kullanılıyor ve toplam her zaman tam."""
    from models import EbatliStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _un1_kurlar()
        _un2_plakalar([('PLK-UN2X', 'ALBANIA', 8.0),
                       ('PLK-UN2Y', 'TURKIYE', 2.0)], cins='UN5TEST')
        db.session.commit()
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'PLAKA_EBATLI',
        'kaynak_ids': ['PLK-UN2X', 'PLK-UN2Y'],
        'kesim_tarihi': _UN1_T.isoformat(),
        'hedefler': [{'hedef_tip': 'EBATLI', 'cins': 'UN5TEST', 'boy': 60,
                      'yukseklik': 60, 'kalinlik': 2, 'adet': 10}]})
    assert r.status_code == 200, r.get_json()
    _dok = {x['kaynak_id']: x for x in r.get_json().get('kaynak_dokumu', [])}
    assert _dok, 'kaynak dökümü yok'
    assert _dok['PLK-UN2X']['parca'] == 8, _dok['PLK-UN2X']
    assert _dok['PLK-UN2Y']['parca'] == 2, _dok['PLK-UN2Y']
    with fa.app.app_context():
        eb = EbatliStok.query.filter_by(cins='UN5TEST').all()
        assert sum(int(e.kasa_ici_adet or 0) for e in eb) == 10


def test_un2_payi_olmayan_kaynak_reddedilir():
    """Parça sayısı kaynak sayısından azsa reddetmeli.

    Payı sıfır kalan kaynağın maliyetinin gidecek yeri yok; sessizce
    yutmak o maliyeti ortadan kaldırırdı."""
    from models import EbatliStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _un1_kurlar()
        _un2_plakalar([('PLK-UN2P', 'ALBANIA', 5.0),
                       ('PLK-UN2Q', 'TURKIYE', 5.0),
                       ('PLK-UN2R', 'ITALY', 5.0)], cins='UN6TEST')
        db.session.commit()
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'PLAKA_EBATLI',
        'kaynak_ids': ['PLK-UN2P', 'PLK-UN2Q', 'PLK-UN2R'],
        'kesim_tarihi': _UN1_T.isoformat(),
        'hedefler': [{'hedef_tip': 'EBATLI', 'cins': 'UN6TEST', 'boy': 60,
                      'yukseklik': 60, 'kalinlik': 2, 'adet': 2}]})
    assert r.status_code == 400, r.status_code
    _y = r.get_json()
    assert _y.get('error') == 'kaynak_payi_yok', _y
    with fa.app.app_context():
        assert EbatliStok.query.filter_by(cins='UN6TEST').count() == 0
        # Kaynaklar tuketilmemis olmali
        from models import PlakaStok
        for _id in ('PLK-UN2P', 'PLK-UN2Q', 'PLK-UN2R'):
            assert db.session.get(PlakaStok, _id).durum == 'Serbest'


def test_un2_hedef_tipi_yonle_uyumsuzsa_400():
    """PLAKA_EBATLI yönüne PLAKA hedefi → temiz 400, çıplak 500 değil.

    ÖLÇÜLDÜ: eskiden `int('PLK-A')` ile 500 dönüyordu — kötü veri
    üretmiyordu ama kullanıcıya ham sunucu hatası gösteriyordu."""
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _un1_kurlar()
        _un2_plakalar([('PLK-UN2Z', 'TURKIYE', 5.4)], cins='UN7TEST')
        db.session.commit()
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'PLAKA_EBATLI', 'kaynak_ids': ['PLK-UN2Z'],
        'kesim_tarihi': _UN1_T.isoformat(),
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'UN7TEST', 'boy': 150,
                      'yukseklik': 180, 'kalinlik': 2, 'adet': 2}]})
    assert r.status_code == 400, r.status_code
    _y = r.get_json()
    assert _y.get('error') == 'hedef_tip_uyumsuz', _y
    assert 'EBATLI' in _y.get('mesaj', ''), _y.get('mesaj')


def test_un2_tek_kaynakta_birim_harmanla_ayni():
    """Tek kaynaklı kesimde kaynak başına birim = harmanlanmış birim.

    Yapı kaynak kaynak üretime geçti; tek kaynakta döngü bir kez
    dönmeli ve sonuç eskisiyle aynı olmalı. (Alan alan karşılaştırma
    ayrıca ölçüldü: birebir aynı.)"""
    from models import EbatliStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _un1_kurlar()
        _un2_plakalar([('PLK-UN2S', 'TURKIYE', 5.4)], cins='UN8TEST')
        db.session.commit()
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'PLAKA_EBATLI', 'kaynak_ids': ['PLK-UN2S'],
        'kesim_tarihi': _UN1_T.isoformat(),
        'hedefler': [{'hedef_tip': 'EBATLI', 'cins': 'UN8TEST', 'boy': 60,
                      'yukseklik': 60, 'kalinlik': 2, 'adet': 10,
                      'kasa_ici_adet': 4}]})
    assert r.status_code == 200, r.get_json()
    _d = r.get_json()
    _dok = _d['kaynak_dokumu']
    assert len(_dok) == 1, _dok
    assert _dok[0]['parca'] == 10, _dok
    # Harmanlanmis birim ile kaynak basina birim ayni olmali
    assert abs(float(_dok[0]['birim_maliyet'])
               - float(_d['birim_maliyet'])) < 0.02, (_dok, _d['birim_maliyet'])
    # Tek kaynakta mesaj ARALIK yazmamali
    assert '–' not in _d.get('mesaj', ''), _d.get('mesaj')
    with fa.app.app_context():
        eb = EbatliStok.query.filter_by(cins='UN8TEST').all()
        assert sum(int(e.kasa_ici_adet or 0) for e in eb) == 10
        assert {e.mense for e in eb} == {'TURKIYE'}
'''),
]

TAM_ICERIK = {
    'migrations/versions/un2kaynakstk_kesim_detay_kaynak.py':
        'IiIia2VzaW1fZGV0YXkua2F5bmFrX3N0b2tfaWQg4oCUIGhlZGVmIGhhbmdpIGtheW5ha3RhbiBj'
        'aWt0aSAoVU4yKQoKUmV2aXNpb24gSUQ6IHVuMmtheW5ha3N0awpSZXZpc2VzOiBkdDFkdXJ1bXRh'
        'cgpDcmVhdGUgRGF0ZTogMjAyNi0xMC0yOCAyMDo1NTowMAoKQ29rIGtheW5ha2xpIGtlc2ltZGUg'
        'KFBMQUtBLT5FQkFUTEkgYmlyZGVuIGZhemxhIHBsYWthIHNlY2lsZWJpbGl5b3IpCmhlciBoZWRl'
        'ZiBzdG9rIFRFSyBiaXIga2F5bmFrdGFuIGdlbGlyOyBtZW7Fn2VpbmksIHVyZXRpY2lzaW5pIHZl'
        'Cm1hbGl5ZXRpbmkgb25kYW4gYWxtYXNpIGdlcmVraXIuIEtvbG9uIG9sbWFkYW4gImhlcHNpIGls'
        'ayBrYXluYWt0YW4iCnZhcnNheWltaSBrYWNpbmlpbWF6ZGkgdmUga2FyaXNpayBtZW7Fn2VsaSBr'
        'ZXNpbWRlIHRpY2FyaSBmYXR1cmF5YQp5YW5saXMgbWVuxZ9lIGJhc2lsaXlvcmR1LgoKWWFsbml6'
        'Y2EgU1VUVU4gRUtMRVIsIHZlcml5ZSBkb2t1bm1hei4gSURFTVBPVEVOVC4KIiIiCmZyb20gYWxl'
        'bWJpYyBpbXBvcnQgb3AKaW1wb3J0IHNxbGFsY2hlbXkgYXMgc2EKCnJldmlzaW9uID0gJ3VuMmth'
        'eW5ha3N0aycKZG93bl9yZXZpc2lvbiA9ICdkdDFkdXJ1bXRhcicKYnJhbmNoX2xhYmVscyA9IE5v'
        'bmUKZGVwZW5kc19vbiA9IE5vbmUKClRBQkxPID0gJ2tlc2ltX2RldGF5JwpTVVRVTiA9ICdrYXlu'
        'YWtfc3Rva19pZCcKSU5ERUtTID0gJ2l4X2tlc2ltX2RldGF5X2theW5ha19zdG9rX2lkJwoKCmRl'
        'ZiBfdmFyX21pKHRhYmxvLCBzdXR1bik6CiAgICBpbnMgPSBzYS5pbnNwZWN0KG9wLmdldF9iaW5k'
        'KCkpCiAgICByZXR1cm4gdGFibG8gaW4gaW5zLmdldF90YWJsZV9uYW1lcygpIGFuZCBcCiAgICAg'
        'ICAgc3V0dW4gaW4ge2NbJ25hbWUnXSBmb3IgYyBpbiBpbnMuZ2V0X2NvbHVtbnModGFibG8pfQoK'
        'CmRlZiBfaW5kZWtzX3Zhcl9taSh0YWJsbywgYWQpOgogICAgaW5zID0gc2EuaW5zcGVjdChvcC5n'
        'ZXRfYmluZCgpKQogICAgaWYgdGFibG8gbm90IGluIGlucy5nZXRfdGFibGVfbmFtZXMoKToKICAg'
        'ICAgICByZXR1cm4gRmFsc2UKICAgIHJldHVybiBhZCBpbiB7aVsnbmFtZSddIGZvciBpIGluIGlu'
        'cy5nZXRfaW5kZXhlcyh0YWJsbyl9CgoKZGVmIHVwZ3JhZGUoKToKICAgIGlmIG5vdCBfdmFyX21p'
        'KFRBQkxPLCBTVVRVTik6CiAgICAgICAgd2l0aCBvcC5iYXRjaF9hbHRlcl90YWJsZShUQUJMTywg'
        'c2NoZW1hPU5vbmUpIGFzIGI6CiAgICAgICAgICAgIGIuYWRkX2NvbHVtbihzYS5Db2x1bW4oU1VU'
        'VU4sIHNhLlN0cmluZyhsZW5ndGg9MjApLCBudWxsYWJsZT1UcnVlKSkKICAgIGlmIG5vdCBfaW5k'
        'ZWtzX3Zhcl9taShUQUJMTywgSU5ERUtTKToKICAgICAgICBvcC5jcmVhdGVfaW5kZXgoSU5ERUtT'
        'LCBUQUJMTywgW1NVVFVOXSwgdW5pcXVlPUZhbHNlKQoKCmRlZiBkb3duZ3JhZGUoKToKICAgIGlm'
        'IF9pbmRla3NfdmFyX21pKFRBQkxPLCBJTkRFS1MpOgogICAgICAgIG9wLmRyb3BfaW5kZXgoSU5E'
        'RUtTLCB0YWJsZV9uYW1lPVRBQkxPKQogICAgaWYgX3Zhcl9taShUQUJMTywgU1VUVU4pOgogICAg'
        'ICAgIHdpdGggb3AuYmF0Y2hfYWx0ZXJfdGFibGUoVEFCTE8sIHNjaGVtYT1Ob25lKSBhcyBiOgog'
        'ICAgICAgICAgICBiLmRyb3BfY29sdW1uKFNVVFVOKQo='
        ,
}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA UN1 — KESİM MALİYETİ USD · HER HEDEF KENDİ KAYNAĞINDAN')
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
        print('    python3 yama_un1.py            # rapor')
        print('    python3 yama_un1.py --uygula')
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
        print('  ⊙ Yama UN1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_un1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_un1'
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
    print('  SIRA ONEMLI — GOC ONCE:')
    print('    1) venv/bin/python -m flask --app flask_app db upgrade')
    print('    2) sudo systemctl restart milestone-erp')
    print('    3) venv/bin/python -m pytest tests/test_kritik.py -q   # 261')
    print()
    print('  BAKILACAK YER')
    print('    1. Kesim -> PLAKA->EBATLI: iki AYRI MENSELI plaka sec.')
    print('       Ozetin altinda uyari cikar ve hangi menseden kac')
    print('       parca cikacagini yazar. Kes: cikan ebatlilar menseye')
    print('       gore AYRI gruplara bolunur, kasalar karismaz.')
    print('    2. EUR bir bloktan kesim yap: plakanin birim maliyeti')
    print('       ve dovizi artik USD.')
    print('    3. Tek kaynakli kesim hic degismedi (alan alan')
    print('       karsilastirildi).')
    print()
    print('  RAKAMLARIN DEGISEBILIR')
    print('    USD DISI bloklardan YENI yapilan kesimlerin birim')
    print('    maliyeti artik cevrilerek hesaplaniyor, yani eskisinden')
    print('    FARKLI cikacak. Mevcut kayitlara DOKUNULMADI — sistemi')
    print('    sifirlayacagini soyledigin icin veri gocu yazmadim.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

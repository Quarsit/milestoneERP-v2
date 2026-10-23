#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA DZ6 — EŞLEŞME YENİDEN KURULUR, ONAY ÖLÇÜME DAYANIR
=========================================================

ÖNKOŞUL: yama_dz5.py uygulanmış olmalı.
         (DZ5'i henüz uygulamadıysan ÖNCE onu uygula; bu yama
          onsuz kendini uygulamaz, dosyalara dokunmadan durur.)

DZ5'i sen denerken ekran görüntüsündeki uyarıyı sordun ve
açıklarken kendi işimde iki kusur buldum. Bu yama ikisini de
kapatıyor.

── KUSUR 1 · SANA YAPAMAYACAĞIN BİR ŞEY SÖYLÜYORDUM ──
  DZ5 kapanışları çözüp AÇIK bırakıyor ve şunu yazıyordu:

      "1 kapatılmış hareket yeniden açılacak — eşleştirmeyi
       tekrar yapmanız gerekir"

  YAPAMAZSIN. Baktım: eşleştirmeyi yeniden çalıştıran bir uç
  nokta da yok, ekran da yok; o kutucuk yalnızca YENİ hareket
  girerken var. Üstelik silinen kur farkı kaydı gerçek bir
  gideri temsil ediyordu.

  ÖLÇÜLDÜ: 10.000 EUR borç 44 kurdan, 100.000 EUR yanlış ödeme
  46 kurdan. Sistem borcu kapatıp 20.000 TL kur farkı açıyor.
  Ödeme 10.000 EUR'ya düzeltilince o kayıt siliniyor ve yerine
  YENİSİ GELMİYORDU — oysa fark gerçek: 44'ten borçlanıp 46'dan
  ödenmiş.

  Artık eşleşme düzeltmenin içinde yeniden kuruluyor ve doğan
  kur farkı RAKAMIYLA onay ekranında yazıyor:

      "Tutar 9.900,00 → 10.000,00 EUR olacak. Şunlar da olacak:
       bu hareketin kendi kapanışı geri alınıyor; İŞ BANKASI ·
       ÇAMLIK kasası 455.400,00 → 460.000,00 TRY; 1 otomatik kur
       farkı kaydı siliniyor; yerine 20.000,00 TRY tutarında
       Kur Farkı (Borç) kaydı oluşuyor."

  EK2'nin kuralı korunuyor: muhasebe kaydı sessizce oluşmuyor,
  önce soruluyor.

  YALNIZCA ÖNCEDEN EŞLEŞME VARSA. Kaydı eşleştirmeden girdiysen,
  düzeltme bahanesiyle sana hiç istemediğin bir kur farkı kaydı
  açılmıyor.

── KUSUR 2 · ONAY EKRANI TAHMİN EDİYORDU ──
  DZ5 kapsamı AYRI bir fonksiyonla önceden sayıyordu. İki sorunu
  vardı:

    · Sayan kod ile YAPAN kod iki ayrı yerdeydi. DZ4'te tam bu
      dersi almıştık: iki ayrı hesap zamanla birbirinden ayrışır.
    · Yeni kur farkının tutarı zaten tahmin edilemiyordu — onu
      hesaplamak için hareketin ZATEN yeni tutarı taşıması ve
      eski kapanışın ZATEN çözülmüş olması gerekiyor.

  Artık iş baştan sona YAPILIYOR, ne olduğu ÖLÇÜLÜYOR, sonra
  onay yoksa `db.session.rollback()` ile hepsi geri alınıyor.
  Onay ekranındaki her rakam fiilen olmuş bir şeyin ölçümü.

  Bunu yapabilmek için yardımcıların hiçbirinin kendi başına
  commit etmediğini tek tek doğruladım:
      _kur_farki_geri_al · _kasa_tutari · _fatura_tahsilat_durumu
      _maliyet_etkilenen_stoklari_tazele
      _satis_kaydi_maliyet_guncelle
      _kesilmis_blok_maliyet_yeniden_dagit
  Altısında da sıfır commit — geri alma gerçekten her şeyi geri
  alıyor.

  Tahmin eden fonksiyon (`_hareket_tutar_kapsami`) SİLİNDİ. Ölü
  kod bırakmak, sonraki birinin onu doğru sanıp çağırması demek.

── TARAYICIDA BULDUĞUM ŞEY (testler kaçırmıştı) ──
  "Eşleşme vardı"nın ÜÇ işareti var. Başta yalnız birine
  bakıyordum: "bu hareket bir borç kapattı mı".

  Ekranda şu durumu denedim: 10.000 EUR borca 9.900 EUR ödeme.
  Ödeme KÜÇÜK olduğu için kapanan taraf borç değil, ÖDEMEnin
  kendisi oluyor. Yani "kapattığı hareket" sayısı sıfır — ama
  kur farkı kaydı gayet vardı ve siliniyordu, yerine yenisi
  gelmiyordu.

  İki testim de ödemenin BÜYÜK olduğu durumu kuruyordu, o yüzden
  ikisi de bunu kaçırdı. Koşul üç işareti de sayacak şekilde
  genişletildi ve bu duruma ayrı bir test yazıldı.

── BİR DE ŞU ──
  Kayıt tipi veride ASCII tutuluyor ('Kur Farki (Borc)'); mesajda
  artık okunabilir yazıyor: "Kur Farkı (Borç)".

── NE DEĞİŞMEDİ ──
  Ekran dosyası (cari.html) bu yamada DEĞİŞMİYOR — 409 onayını
  zaten genel olarak karşılıyor, mesaj sunucudan geliyor.
  Vazgeçtiğinde hiçbir şey olmuyor; bu, DZ5'teki gibi.

── ÖLÇÜLDÜ ──
  Vazgeçme, dört tablonun (CariHareket · Kasa · KasaHareket ·
  AuditLog) SHA özetiyle sınandı: 409'dan sonra tek bayt
  değişmemiş, arka arkaya üç kez daha vazgeçilince de aynı —
  tekrarlanan vazgeçmeler artık bırakmıyor.

  Onay verilince:
      ödeme 10.000 EUR · TRY karşılığı 460.000 (ödeme kurundan)
      borç yeniden kapandı
      TEK kur farkı kaydı: 20.000 TRY  (10.000 × (46 − 44))
      kasa 5.000.000 → 4.540.000
  Kısmi ödemede (1.000 USD borca 600 USD): borç kapanmıyor ama
  eşleşen 600 üzerinden 6.000 TRY kur farkı doğuyor.

  205 test geçti (200 + 5); iki ayrı koşuda da aynı.
  firma · js · form · zincir · akis denetimleri temiz.
  Tabanı DZ5'i uygulayarak ürettim.

  Tarayıcıda baktım: onay kutusu 440×200, ekrana sığıyor,
  taşma yok, JS hatası yok.

── SIRA ──
      DZ1  maliyet ↔ cari hareket            ✓
      DZ2  stok kayıtları                    ✓
      DZ3  satış / proforma / sipariş        ✓
      DZ4  kesim kayıtları                   ✓
      DZ5  cari hareketin tutarı             ✓
      DZ6  eşleşme ve onay                   ← bu yama

DOSYALAR
--------
  flask_app.py          eşleşme yeniden kurulur · onay ölçüme
                        dayanır · tahmin eden fonksiyon silindi
  tests/test_kritik.py  5 yeni test, 1 test yeni davranışa göre
                        güncellendi

Şema yok, göç yok, yeni alan yok, ekran değişmiyor.

KULLANIM
--------
  python3 yama_dz6.py            # RAPOR
  python3 yama_dz6.py --uygula
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
    'flask_app.py': 'DZ6 · ÖNCE YAP, ONAY YOKSA GERİ AL',
    'tests/test_kritik.py': 'def test_dz6_vazgecince_hicbir_sey_kalmiyor',
}
ONKOSUL = {
    'flask_app.py': 'DZ5 · TUTAR DÜZELTİLEBİLİR',
    'tests/test_kritik.py':
        'def test_dz5_cari_hareket_tutari_duzeltilebiliyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'DZ6 · flask_app.py blok 1',
     r'''    def _hareket_tutar_kapsami(hareket):
        """
        Bir cari hareketin TUTARI degisirse, hareketin KENDISI
        disinda ne kimildiyor. Kullaniciya ISTEN ONCE bu liste
        gosteriliyor — DZ1'de silme icin ayni sey yapilmisti.

        Burada hicbir sey DEGISTIRILMIYOR; yalniz sayilip
        anlatiliyor.
        """
        maddeler = []
        for kh in KasaHareket.query.filter_by(
                baglanti_tip='cari_hareket', baglanti_id=hareket.id).all():
            _k = Kasa.query.get(kh.kasa_id)
            maddeler.append(f'{_k.ad if _k else kh.kasa_id} kasasının '
                            f'bakiyesi ve hareketi')
        _kapatilan = CariHareket.query.filter_by(
            kapanis_hareket_id=hareket.id).count()
        if _kapatilan:
            maddeler.append(f'{_kapatilan} kapatılmış hareket yeniden '
                            f'açılacak — eşleştirmeyi tekrar yapmanız gerekir')
        if hareket.kapatildi or hareket.kapanis_hareket_id:
            maddeler.append('bu hareketin kendi kapanışı geri alınacak')
        _kf = CariHareket.query.filter(
            CariHareket.kaynak == 'otomatik_kur_farki',
            CariHareket.aciklama.like(f'%{hareket.id}%')).count()
        if _kf:
            maddeler.append(f'{_kf} otomatik kur farkı kaydı silinecek')
        if hareket.baglanti_tip == 'fatura' and hareket.baglanti_id:
            maddeler.append(f'{hareket.baglanti_id} faturasının tahsilat '
                            f'durumu yeniden hesaplanacak')
        if hareket.baglanti_tip == 'maliyet' and hareket.kaynak == 'maliyet':
            maddeler.append('bağlı maliyet kaydı ve o stoğun birim maliyeti')
        return maddeler
''',
     r'''    # DZ6 NOTU — burada `_hareket_tutar_kapsami` adli bir fonksiyon
    # vardi: tutar degisirse ne kimildayacagini ONCEDEN TAHMIN edip
    # sayiyordu. Kaldirildi. Sayan kod ile YAPAN kod iki ayri yerde
    # durdugu surece zamanla ayrisirlar (DZ4'te ayni dersi aldik), ve
    # yeni kur farkinin tutari zaten tahmin edilemiyordu — onu
    # hesaplamak icin hareketin yeni tutari tasimasi ve eski
    # kapanisin cozulmus olmasi gerekiyor. Artik is YAPILIYOR, ne
    # oldugu OLCULUYOR, onay yoksa rollback ile geri alınıyor.
'''),
    ('flask_app.py', 'DZ6 · flask_app.py blok 2',
     r'''                _kapsam = _hareket_tutar_kapsami(hareket)
                if _kapsam and not _onay_verildi():
                    return jsonify({
                        'ok': False, 'error': 'onay_gerekli',
                        'kapsam': {'maddeler': _kapsam,
                                   'eski_tutar': _eski_tutar,
                                   'yeni_tutar': _yeni_tutar,
                                   'doviz': _yeni_doviz},
                        'mesaj': f'Tutar {_eski_tutar:,.2f} → '
                                 f'{_yeni_tutar:,.2f} {_yeni_doviz} olacak. '
                                 f'Şunlar da güncellenecek: '
                                 f'{"; ".join(_kapsam)}.'}), 409
''',
     r''''''),
    ('flask_app.py', 'DZ6 · flask_app.py blok 3',
     r'''        # ── TUTARI UYGULA ──
        _notlar = []
        if _plan:
            # 1) ESKI ESLESMEYI GERI AL — DELETE ile AYNI fonksiyon
            _kf_acilan, _kf_silinen = _kur_farki_geri_al(hareket.id)
            if hareket.kapatildi or hareket.kapanis_hareket_id:
                hareket.kapatildi = False
                hareket.kapanis_hareket_id = None
                _notlar.append('bu hareketin kapanışı geri alındı')
''',
     r'''        # ══════════════════════════════════════════════════════════
        #  DZ6 · ÖNCE YAP, ONAY YOKSA GERİ AL
        #
        #  DZ5'te kapsamı ÖNCEDEN TAHMİN ediyordum: kasayı, kapanışları
        #  ve kur farkı kayıtlarını ayrı bir fonksiyonla sayıp
        #  "şunlar değişecek" diyordum. İki kusuru vardı:
        #
        #   1. Tahmin ile gerçek ayrışabilir. Sayan kod ile yapan kod
        #      iki ayrı yerdeydi — DZ4'te öğrendiğimiz şey.
        #   2. YENİ kur farkının tutarı tahmin edilemiyordu: onu
        #      hesaplamak için hareketin ZATEN yeni tutarı taşıması
        #      ve eski kapanışın ZATEN çözülmüş olması gerekiyor.
        #
        #  Artık iş baştan sona YAPILIYOR, ne olduğu ÖLÇÜLÜYOR, sonra
        #  onay yoksa `db.session.rollback()` ile hepsi geri alınıyor.
        #  Yardımcıların hiçbiri kendi başına commit etmiyor (bakıldı:
        #  _kur_farki_geri_al · _kasa_tutari · _fatura_tahsilat_durumu
        #  · _maliyet_etkilenen_stoklari_tazele · _satis_kaydi_maliyet_
        #  guncelle · _kesilmis_blok_maliyet_yeniden_dagit), o yüzden
        #  geri alma gerçekten her şeyi geri alıyor.
        #
        #  Notlar NÖTR yazılıyor ("kasası 100.000,00 → 10.000,00 TRY"),
        #  çünkü aynı liste hem soruda hem sonuçta kullanılıyor.
        # ══════════════════════════════════════════════════════════
        _notlar = []
        if _plan:
            # 1) ESKI ESLESMEYI GERI AL — DELETE ile AYNI fonksiyon
            _kf_acilan, _kf_silinen = _kur_farki_geri_al(hareket.id)
            # Bu hareket KENDISI kapanmis olabilir: odeme borctan
            # KUCUKSE kapanan taraf borc degil, odemedir. O durumda
            # `_kf_acilan` 0 kalir ama esleşme YINE DE vardi.
            _kendi_kapaliydi = bool(hareket.kapatildi
                                    or hareket.kapanis_hareket_id)
            if _kendi_kapaliydi:
                hareket.kapatildi = False
                hareket.kapanis_hareket_id = None
                _notlar.append('bu hareketin kendi kapanışı geri alınıyor')
'''),
    ('flask_app.py', 'DZ6 · flask_app.py blok 4',
     r'''                _notlar.append(f'{_m.id} maliyet kaydı ve bağlı stok '
                               f'maliyeti güncellendi')
                if _sk:
                    _notlar.append(f'{_sk} satış kaydının kârı yenilendi')

            # 5) BAGLI FATURANIN TAHSILAT DURUMU
            if hareket.baglanti_tip == 'fatura' and hareket.baglanti_id:
                db.session.flush()
                _fatura_tahsilat_durumu(hareket.baglanti_id)
                _notlar.append(f'{hareket.baglanti_id} faturasının tahsilat '
                               f'durumu yenilendi')

            if _kf_acilan:
                _notlar.append(f'{_kf_acilan} kapatılmış hareket yeniden '
                               f'açıldı')
            if _kf_silinen:
                _notlar.append(f'{_kf_silinen} otomatik kur farkı kaydı '
                               f'geri alındı')
''',
     r'''                _notlar.append(f'{_m.id} maliyet kaydı ve bağlı stoğun '
                               f'birim maliyeti güncelleniyor')
                if _sk:
                    _notlar.append(f'{_sk} satış kaydının kârı yenileniyor')

            # 5) BAGLI FATURANIN TAHSILAT DURUMU
            if hareket.baglanti_tip == 'fatura' and hareket.baglanti_id:
                db.session.flush()
                _fatura_tahsilat_durumu(hareket.baglanti_id)
                _notlar.append(f'{hareket.baglanti_id} faturasının tahsilat '
                               f'durumu yenileniyor')

            if _kf_acilan:
                _notlar.append(f'{_kf_acilan} kapatılmış hareket yeniden '
                               f'açılıyor')
            if _kf_silinen:
                _notlar.append(f'{_kf_silinen} otomatik kur farkı kaydı '
                               f'siliniyor')

            # ══════════════════════════════════════════════════════
            #  6) DZ6 · ESLESME YENIDEN KURULUYOR
            #
            #  DZ5'te kapanislar cozulup ACIK birakiliyordu. Olculdu:
            #  10.000 EUR borc 44 kurdan, 100.000 EUR yanlis odeme 46
            #  kurdan — sistem borcu kapatip 20.000 TL kur farki
            #  aciyor. Odeme 10.000 EUR'ya duzeltilince o kur farki
            #  SILINIYOR ve yerine yenisi GELMIYORDU.
            #
            #  Oysa fark gercekti: 44'ten borclanip 46'dan odemisiz.
            #  Daha kotusu, eslesmeyi yeniden calistiran bir uc nokta
            #  ya da ekran YOK — kutucuk yalnizca YENI hareket
            #  girerken var. Yani kullaniciya yapamayacagi bir sey
            #  soyluyordum: "esleştirmeyi tekrar yapmaniz gerekir".
            #
            #  Artik esleşme burada yeniden kuruluyor ve dogan kur
            #  farki RAKAMIYLA onay ekraninda yaziliyor. EK2'nin
            #  kurali korunuyor: muhasebe kaydi sessizce olusmuyor,
            #  once soruluyor.
            #
            #  YALNIZCA ONCEDEN ESLESME VARSA. Kullanici o kaydi
            #  eslestirmeden girdiyse, duzeltme bahanesiyle ona hic
            #  istemedigi bir kur farki kaydi acmak dogru olmazdi.
            #
            #  "Esleşme vardi"nin UC isareti var ve UCU DE sayilir:
            #    · bu hareket bir borc KAPATTI      (_kf_acilan)
            #    · bu hareketten kur farki DOGDU    (_kf_silinen)
            #    · bu hareketin KENDISI kapandi     (_kendi_kapaliydi)
            #
            #  Basta yalniz birincisine bakiyordum. Tarayicida
            #  goruldu: 10.000 EUR borca 9.900 EUR odeme — odeme
            #  kucuk oldugu icin kapanan taraf ODEME oluyor, borc
            #  acik kaliyor. `_kf_acilan` 0, ama kur farki kaydi
            #  gayet vardi ve siliniyordu. Testler bunu kacirdi
            #  cunku ikisi de odemenin BUYUK oldugu durumu kuruyordu.
            #
            #  Yeni eslesme BASKA bir karsi tarafa denk gelebilir —
            #  FIFO en eski acik borcu secer. Bu dogru davranis:
            #  sifirdan girilen bir odeme de ayni kurali izlerdi.
            # ══════════════════════════════════════════════════════
            _TAHSILAT_ODEME = ('Tahsilat', 'Avans Tahsilati',
                               'Avans Tahsilatı', 'Odeme', 'Ödeme',
                               'Avans Odemesi', 'Avans Ödemesi')
            _yeni_kf = None
            _eslesme_vardi = bool(_kf_acilan or _kf_silinen
                                  or _kendi_kapaliydi)
            if _eslesme_vardi and hareket.islem_tip in _TAHSILAT_ODEME:
                db.session.flush()
                _yeni_kf = _kur_farki_hesapla_ve_olustur(hareket, islet=True)
                db.session.flush()
                if _yeni_kf is not None:
                    _kf_tut = q2((_yeni_kf.borc or 0) + (_yeni_kf.alacak or 0))
                    # Kayit tipi ASCII tutuluyor ('Kur Farki (Borc)') —
                    # kullaniciya gosterirken okunabilir yaziliyor.
                    _kf_ad = (_yeni_kf.islem_tip or 'Kur Farkı').replace(
                        'Kur Farki', 'Kur Farkı').replace('(Borc)', '(Borç)')
                    _notlar.append(
                        f'yerine {_kf_tut:,.2f} {_yeni_kf.doviz or "TRY"} '
                        f'tutarında {_kf_ad} kaydı oluşuyor')
                else:
                    _notlar.append('eşleşme yeniden kuruluyor '
                                   '(kur farkı doğmuyor)')

        # ── ONAY KAPISI ──
        # Is bitti, ne oldugu olculdu. Onay yoksa HEPSI geri alinir.
        if _plan and _notlar and not _onay_verildi():
            db.session.rollback()
            return jsonify({
                'ok': False, 'error': 'onay_gerekli',
                'kapsam': {'maddeler': _notlar,
                           'eski_tutar': _plan['eski_tutar'],
                           'yeni_tutar': _plan['tutar'],
                           'doviz': _plan['doviz']},
                'mesaj': f'Tutar {_plan["eski_tutar"]:,.2f} → '
                         f'{_plan["tutar"]:,.2f} {_plan["doviz"]} olacak. '
                         f'Şunlar da olacak: {"; ".join(_notlar)}.'}), 409
'''),
    ('flask_app.py', 'DZ6 · flask_app.py blok 5',
     r'''            _mesaj += '. ' + ', '.join(_notlar)
''',
     r'''            # Notlar NOTR yazildi; sonucta "oldu" diye kapatiliyor.
            _mesaj += '. Birlikte: ' + '; '.join(_notlar)
'''),
    ('tests/test_kritik.py', 'DZ6 · tests/test_kritik.py blok 1',
     r'''def test_dz5_tutar_duzeltilince_kapanis_geri_aliniyor():
    """DZ5: tahsilat bir borcu kapatmış ve kur farkı doğmuşsa, tutar
    değişince o eşleşme artık geçersiz. DELETE'in kullandığı
    `_kur_farki_geri_al` burada da çağrılıyor — ikinci bir çözme
    mantığı yazmadık, zamanla ayrışırdı.

    EŞLEŞME KENDİLİĞİNDEN YENİLENMİYOR: kapanışlar açık bırakılıyor.
    Bir muhasebe kaydını (kur farkı) sessizce oluşturmak,
    oluşturmamaktan daha zararlı — EK2'de böyle karar verilmişti."""
''',
     r'''def test_dz5_tutar_duzeltilince_kapanis_yeniden_kuruluyor():
    """DZ5+DZ6: tahsilat bir borcu kapatmış ve kur farkı doğmuşsa,
    tutar değişince o eşleşme geçersiz. DELETE'in kullandığı
    `_kur_farki_geri_al` ile çözülüyor — ikinci bir çözme mantığı
    yazmadık, zamanla ayrışırdı — sonra YENİ tutarla yeniden
    kuruluyor.

    DZ5'te açık bırakılıyordu. Bu yanlıştı: kur farkı gerçek bir
    gider ve onu yeniden hesaplatacak bir ekran YOK, yani
    kullanıcıya yapamayacağı bir şey söyleniyordu. DZ6 ile eşleşme
    burada yeniden kuruluyor; doğan kur farkı önce onay ekranında
    rakamıyla gösteriliyor, yani EK2'nin kuralı korunuyor.

    BURADA ÖDEME KISMİ: 1.000 USD borca 600 USD. Borç KAPANMIYOR
    (kısmi), ama eşleşen 600 USD üzerinden kur farkı doğuyor:
    600 × (48 − 38) = 6.000 TRY."""
'''),
    ('tests/test_kritik.py', 'DZ6 · tests/test_kritik.py blok 2',
     r'''        assert not eski.kapatildi, 'kapatılmış borç yeniden açılmadı'
        assert eski.kapanis_hareket_id is None, 'kapanış bağı kaldı'
        assert CariHareket.query.filter_by(
            cari_id='MD5E', kaynak='otomatik_kur_farki').count() == 0, \
            'geçersiz kur farkı kaydı duruyor'
''',
     r'''        # 600 < 1.000 → borc KISMI odendi, kapanmiyor
        assert not eski.kapatildi, 'kısmi ödeme borcu kapatmamalı'
        assert eski.kapanis_hareket_id is None, 'kapanış bağı kalmamalı'
        # Eski (1.000 USD uzerinden) kayit gitti, YENISI geldi:
        # eslesen 600 USD × (48 − 38) = 6.000 TRY
        kf = CariHareket.query.filter_by(
            cari_id='MD5E', kaynak='otomatik_kur_farki').all()
        assert len(kf) == 1, f'{len(kf)} kur farkı kaydı (1 olmalı)'
        _kf_tut = float((kf[0].borc or 0) + (kf[0].alacak or 0))
        assert _kf_tut == 6000, f'kur farkı {_kf_tut} (6000 olmalı)'
'''),
    ('tests/test_kritik.py', 'DZ6 · tests/test_kritik.py blok 3',
     r'''    assert 'belge_no' in r.get_json()['mesaj'], r.get_json()
''',
     r'''    assert 'belge_no' in r.get_json()['mesaj'], r.get_json()


# ══════════════════════════════════════════════════════════════════
#  DZ6 · ÖNCE YAP, ONAY YOKSA GERİ AL — VE EŞLEŞMEYİ YENİDEN KUR
#
#  DZ5 kapsamı ÖNCEDEN TAHMİN ediyordu ve kapanışları çözüp AÇIK
#  bırakıyordu. İki sonucu vardı:
#
#   · Yeni kur farkının tutarı tahmin edilemiyordu — onu hesaplamak
#     için hareketin yeni tutarı taşıması ve eski kapanışın çözülmüş
#     olması gerekiyor.
#   · Eşleşmeyi yeniden çalıştıran bir uç nokta ya da ekran YOK.
#     Yani kullanıcıya yapamayacağı bir şey söyleniyordu.
#
#  Ölçüldü: 10.000 EUR borç 44 kurdan, 100.000 EUR yanlış ödeme 46
#  kurdan. Sistem borcu kapatıp 20.000 TL kur farkı açıyor. Ödeme
#  10.000 EUR'ya düzeltilince o kayıt siliniyor ve yerine yenisi
#  GELMİYORDU — oysa fark gerçek: 44'ten borçlanıp 46'dan ödenmiş.
# ══════════════════════════════════════════════════════════════════

def _dz6_kur(c, ek):
    """EUR borç (44 kurdan) + yanlış tutarlı EUR ödeme (46 kurdan).
    Ödeme eşleştirilerek giriliyor, yani kur farkı doğuyor."""
    from models import Cari, Kasa, DovizKur
    cid = f'TD6{ek}'
    with fa.app.app_context():
        if not db.session.get(Cari, cid):
            db.session.add(Cari(id=cid, unvan=f'DZ6 {ek}',
                                cari_tip='Tedarikçi'))
        for _t, _k in ((date(2026, 3, 1), 44), (date(2026, 3, 2), 46)):
            if not DovizKur.query.filter_by(doviz='EUR', tarih=_t).first():
                db.session.add(DovizKur(doviz='EUR', tarih=_t,
                                        alis=_k, satis=_k))
        k = Kasa.query.filter_by(ad=f'DZ6 {ek} KASA').first()
        if not k:
            k = Kasa(ad=f'DZ6 {ek} KASA', doviz='TRY', bakiye=5000000)
            db.session.add(k)
        db.session.commit()
        kid = k.id
        bid = f'HR-D6{ek}'
        if not db.session.get(CariHareket, bid):
            db.session.add(CariHareket(
                id=bid, cari_id=cid, cari_unvan=f'DZ6 {ek}',
                islem_tip='Fatura (Alis)', hareket_tarihi=date(2026, 3, 1),
                vade_tarihi=date(2026, 3, 1), borc=0, alacak=10000,
                alacak_try=440000, doviz='EUR', kur_uygulanan=44,
                kaynak='manuel', kapatildi=False))
            db.session.commit()
    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': cid, 'islem_tip': 'Odeme', 'doviz': 'EUR',
        'tutar': 100000, 'borc': 100000, 'kasa_id': kid,
        'hareket_tarihi': '2026-03-02', 'vade_tarihi': '2026-03-02',
        'evrak_no': f'DK-{ek}', 'kur_farki_islet': True})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        o = CariHareket.query.filter_by(cari_id=cid,
                                        islem_tip='Odeme').first()
        return o.id, bid, cid, kid


def _dz6_iz(cid, kid):
    """Bu testin dokunduğu HER ŞEYİN özeti. Tek alan değişse tutmaz."""
    from models import Kasa
    with fa.app.app_context():
        p = []
        for h in CariHareket.query.filter_by(cari_id=cid).order_by(
                CariHareket.id).all():
            p.append(f'{h.id}|{h.borc}|{h.alacak}|{h.borc_try}|{h.doviz}|'
                     f'{h.kur_uygulanan}|{h.kapatildi}|'
                     f'{h.kapanis_hareket_id}|{h.aciklama}|{h.evrak_no}')
        p.append(f'KASA|{db.session.get(Kasa, kid).bakiye}')
        return '\n'.join(p)


def test_dz6_vazgecince_hicbir_sey_kalmiyor():
    """DZ6: iş artık ÖNCE YAPILIYOR, sonra onay yoksa rollback ile
    geri alınıyor. Bu testin tek sorusu: geri alma GERÇEKTEN her şeyi
    geri alıyor mu — kasa bakiyesi, kapanış bayrakları, silinen ve
    yeni açılan kur farkı kayıtları dahil.

    Üst üste vazgeçmek de artık artık bırakmamalı."""
    c = istemci('admin', 'ADMIN')
    oid, bid, cid, kid = _dz6_kur(c, 'A')
    once = _dz6_iz(cid, kid)

    r = c.put(f'/api/cari/hareket/{oid}', headers=H,
              json={'tutar': 10000, 'aciklama': 'DUZELTILDI'})
    assert r.status_code == 409, (r.status_code, r.get_json())
    assert _dz6_iz(cid, kid) == once, 'vazgeçmeye rağmen bir şey kaldı'

    # Üç kez daha vazgeç — birikmemeli
    for _ in range(3):
        c.put(f'/api/cari/hareket/{oid}', headers=H, json={'tutar': 10000})
    assert _dz6_iz(cid, kid) == once, 'tekrarlanan vazgeçme artık bıraktı'


def test_dz6_eslesme_yeniden_kuruluyor_kur_farki_onayda_yaziyor():
    """DZ6: düzeltmeden sonra eşleşme yeniden kuruluyor ve doğan kur
    farkı RAKAMIYLA onay ekranında yazıyor.

    10.000 EUR 44'ten borçlanılmış, 46'dan ödenmiş → 20.000 TL fark.
    DZ5'te bu kayıt siliniyor ve yerine yenisi gelmiyordu."""
    from models import Kasa
    c = istemci('admin', 'ADMIN')
    oid, bid, cid, kid = _dz6_kur(c, 'B')
    with fa.app.app_context():
        assert db.session.get(CariHareket, bid).kapatildi is True, \
            'kurulum tutmadı: borç kapanmamış'
        assert CariHareket.query.filter_by(
            cari_id=cid, kaynak='otomatik_kur_farki').count() == 1

    r = c.put(f'/api/cari/hareket/{oid}', headers=H, json={'tutar': 10000})
    assert r.status_code == 409, r.get_json()
    msj = r.get_json()['mesaj']
    # Tahmin DEGIL: bu rakam isi yapip olcerek bulundu.
    assert '20,000.00' in msj, msj
    # Kayit tipi veride ASCII ('Kur Farki (Borc)'), kullaniciya
    # OKUNABILIR gosteriliyor.
    assert 'Kur Farkı' in msj, msj

    r = c.put(f'/api/cari/hareket/{oid}?onay=1', headers=H,
              json={'tutar': 10000})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        o = db.session.get(CariHareket, oid)
        assert float(o.borc) == 10000
        assert float(o.borc_try) == 460000, 'TRY karşılığı ödeme kurundan'
        assert db.session.get(CariHareket, bid).kapatildi is True, \
            'eşleşme yeniden kurulmadı — borç açık kaldı'
        kf = CariHareket.query.filter_by(
            cari_id=cid, kaynak='otomatik_kur_farki').all()
        assert len(kf) == 1, f'{len(kf)} kur farkı kaydı (1 olmalı)'
        assert float(kf[0].borc) == 20000, float(kf[0].borc)
        # 5.000.000 − 460.000
        assert float(db.session.get(Kasa, kid).bakiye) == 4540000


def test_dz6_eslesmesiz_kayitta_kur_farki_acilmiyor():
    """DZ6: eşleşme YALNIZCA önceden varsa yeniden kuruluyor.

    Kullanıcı o ödemeyi eşleştirmeden girdiyse, düzeltme bahanesiyle
    ona hiç istemediği bir kur farkı kaydı açmak doğru olmazdı —
    muhasebe kaydını sessizce oluşturmama kuralı (EK2) bunu da
    kapsıyor."""
    c = istemci('admin', 'ADMIN')
    hid, kid, cid = _dz5_kur(c, 'G')   # TRY tahsilat, eşleştirme yok
    with fa.app.app_context():
        assert CariHareket.query.filter_by(
            cari_id=cid, kaynak='otomatik_kur_farki').count() == 0

    r = c.put(f'/api/cari/hareket/{hid}?onay=1', headers=H,
              json={'tutar': 10000})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        assert CariHareket.query.filter_by(
            cari_id=cid, kaynak='otomatik_kur_farki').count() == 0, \
            'istenmediği halde kur farkı kaydı açıldı'


def test_dz6_kapsam_tahmin_eden_fonksiyon_kaldirildi():
    """DZ6: kapsamı önceden sayan `_hareket_tutar_kapsami` kaldırıldı.
    Sayan kod ile YAPAN kod iki ayrı yerde durdukça zamanla
    ayrışırlar — DZ4'te aynı dersi almıştık. Ölü kod da bırakmıyoruz:
    sonraki biri onu doğru sanıp çağırabilir."""
    import io as _io
    f = _io.open(os.path.join(KOK, 'flask_app.py'), encoding='utf-8').read()
    assert 'def _hareket_tutar_kapsami' not in f, \
        'tahmin eden fonksiyon hâlâ duruyor'


def test_dz6_odeme_borctan_kucukse_de_eslesme_yeniden_kuruluyor():
    """DZ6: "eşleşme vardı"nın ÜÇ işareti var ve üçü de sayılmalı.

    Başta yalnız birine bakıyordum: "bu hareket bir borç kapattı mı".
    TARAYICIDA görüldü — testler kaçırmıştı, çünkü ikisi de ödemenin
    borçtan BÜYÜK olduğu durumu kuruyordu:

        10.000 EUR borç, 9.900 EUR ödeme (44 → 46 kur)

    Ödeme küçük olduğu için kapanan taraf BORÇ değil ÖDEMEnin
    kendisi oluyor; borç açık kalıyor. Yani "kapattığı hareket"
    sayısı sıfır — ama kur farkı kaydı gayet vardı ve düzeltmede
    siliniyordu. Yerine yenisi gelmiyordu.

    Doğrusu: ödemenin kendi kapanışı da bir eşleşme işaretidir."""
    from models import Cari, Kasa, DovizKur
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not db.session.get(Cari, 'TD6K'):
            db.session.add(Cari(id='TD6K', unvan='DZ6 K',
                                cari_tip='Tedarikçi'))
        for _t, _k in ((date(2026, 3, 1), 44), (date(2026, 3, 2), 46)):
            if not DovizKur.query.filter_by(doviz='EUR', tarih=_t).first():
                db.session.add(DovizKur(doviz='EUR', tarih=_t,
                                        alis=_k, satis=_k))
        k = Kasa.query.filter_by(ad='DZ6 K KASA').first()
        if not k:
            k = Kasa(ad='DZ6 K KASA', doviz='TRY', bakiye=5000000)
            db.session.add(k)
        db.session.commit()
        kid = k.id
        if not db.session.get(CariHareket, 'HR-D6K'):
            db.session.add(CariHareket(
                id='HR-D6K', cari_id='TD6K', cari_unvan='DZ6 K',
                islem_tip='Fatura (Alis)', hareket_tarihi=date(2026, 3, 1),
                vade_tarihi=date(2026, 3, 1), borc=0, alacak=10000,
                alacak_try=440000, doviz='EUR', kur_uygulanan=44,
                kaynak='manuel', kapatildi=False))
            db.session.commit()

    # ODEME BORCTAN KUCUK: 9.900 < 10.000
    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': 'TD6K', 'islem_tip': 'Odeme', 'doviz': 'EUR',
        'tutar': 9900, 'borc': 9900, 'kasa_id': kid,
        'hareket_tarihi': '2026-03-02', 'vade_tarihi': '2026-03-02',
        'evrak_no': 'DK-K', 'kur_farki_islet': True})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        o = CariHareket.query.filter_by(cari_id='TD6K',
                                        islem_tip='Odeme').first()
        oid = o.id
        # Kurulumun ta kendisi: KAPANAN taraf ODEME, borc acik
        assert o.kapatildi is True, 'kurulum tutmadı: ödeme kapanmamış'
        assert db.session.get(CariHareket, 'HR-D6K').kapatildi is False, \
            'kurulum tutmadı: kısmi ödeme borcu kapatmış'
        assert CariHareket.query.filter_by(
            cari_id='TD6K', kaynak='otomatik_kur_farki').count() == 1

    r = c.put(f'/api/cari/hareket/{oid}', headers=H, json={'tutar': 10000})
    assert r.status_code == 409, r.get_json()
    msj = r.get_json()['mesaj']
    assert 'siliniyor' in msj, msj
    assert 'oluşuyor' in msj, f'yerine yenisi gelmiyor: {msj}'
    # Kayit tipi kullaniciya OKUNABILIR yaziliyor ('Kur Farki' degil)
    assert 'Kur Farkı' in msj, msj

    r = c.put(f'/api/cari/hareket/{oid}?onay=1', headers=H,
              json={'tutar': 10000})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        kf = CariHareket.query.filter_by(
            cari_id='TD6K', kaynak='otomatik_kur_farki').all()
        assert len(kf) == 1, f'{len(kf)} kur farkı kaydı (1 olmalı)'
        # 10.000 EUR tam eslesti: 10.000 × (46 − 44) = 20.000 TRY
        assert float((kf[0].borc or 0) + (kf[0].alacak or 0)) == 20000
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA DZ4 — KESIM KAYITLARI')
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
        print('    python3 yama_dz6.py            # rapor')
        print('    python3 yama_dz6.py --uygula')
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
        print('  ⊙ Yama DZ6 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_dz6.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_dz6'
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
    print('    Dovizli bir odemeyi/tahsilati ESLESTIREREK girdiysen')
    print('    (yani kur farki dogmussa), tutarini duzelt.')
    print()
    print('    Onay kutusu artik SILINEN kur farkinin YERINE hangi')
    print('    tutarda yeni kayit olusacagini da yaziyor; onay')
    print('    verince o kayit gercekten olusuyor.')
    print()
    print('    Vazgec dersen hicbir sey olmuyor — bu degismedi.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

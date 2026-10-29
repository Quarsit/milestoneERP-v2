#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA KD1 — KDV MATEMATİĞİNİN TEK KAPISI + ÖLÜ KOD + ÜÇ UÇ
===========================================================

ÖNKOŞUL: **yama_yk2.py uygulanmış olmalı.** Betik denetliyor.
Şema değişikliği YOK, göç YOK.

Dokunulan dosyalar:
    flask_app.py · templates/satislar.html · templates/ayarlar.html
    tests/test_kritik.py

Kullanım:
    python3 yama_kd1.py              # rapor, dosyalara dokunmaz
    python3 yama_kd1.py --uygula
    venv/bin/python -m pytest tests/test_kritik.py -q     # 291

═══ 1 · KDV KAPISI: BEKLEDİĞİMİN TERSİ ÇIKTI ═══

"Tanımlanmış ama hiç çağrılmayan fonksiyon" taraması 10 aday verdi.
Biri `_kdv_hesapla` idi: KDV matrahını ayırmak için yazılmış ortak
kapı, HİÇBİR YERDEN çağrılmıyor, formül ise 10 ayrı uca elle
yazılmış. AF1/TS1/EM2'nin aynısı gibi duruyordu.

Refleks "uçları kapıya bağla" demekti. ÖLÇTÜM, ters çıktı:

    0,45 USD · %20    kapı: 0,38 + 0,08 = 0,46      (toplam 0,45)
    1.000,35 USD · %20  kapı: 833,63 + 166,73 = 1.000,36

1.000.000 denemede 11.968 sapma. Sebep: kapı matrahı ve KDV'yi
BİRBİRİNDEN BAĞIMSIZ yuvarlıyordu. Uçlar ise doğrusunu yapıyordu —
bir tarafı yuvarlayıp ötekini ÇIKARMAYLA buluyorlardı.

Yani kapıya bağlamak, 10 para yoluna hata EKLERDİ. Önce kapı
düzeltildi (tamamlayan yuvarlama: matrah + KDV == toplam, her
zaman), sonra uçlar bağlandı.

İki uç gerçekten hatalıydı — ikisi de bağımsız yuvarlıyordu:
  · `/api/diag/fatura/<id>/kdv_duzelt` — faturanın matrahı ile
    KDV'si toplandığında faturanın kendi toplamını vermiyordu
  · proformadan faturaya dönüşüm — aynısı

Fatura matrahı ile KDV'sinin toplamının faturanın toplamını
tutmaması, mutabakatı ve beyanı sessizce bozar.

Bağlanan 10 yer: blok/plaka/ebatlı stok alışı (birim fiyattan KDV
sıyırma), maliyet ekleme, maliyet dağıtımı, üretim maliyeti, cari
hareket faturası, fatura KDV düzeltme, proforma→fatura.

═══ 2 · ÖLÜ KOD: 7 FONKSİYON SİLİNDİ ═══

Taramanın 10 adayı tek tek ölçüldü:

  · `_cari_hareket_okunur_id` — YANLIŞ POZİTİF. SQLAlchemy onu her
    insert'te çağırıyor (`listens_for`); tarayıcım dinleyicileri
    görmüyordu. Düzeltildi.
  · `_cari_kimlik_ver` — işi ZATEN yapılıyor: models.py'deki
    `cari_id_otomatik_doldur` / `stok_cari_id_otomatik_doldur`
    dinleyicileri 9 modelde kimliği dolduruyor, kayıt üreten 29
    yerin hepsi kapsanıyor. (Önce "29 yerde cari_id boş kalıyor"
    diye bir bulgu çıkarmıştım; fixture'la ölçünce yanlış çıktı —
    dinleyiciler statik taramada görünmüyordu.)
  · `_stok_temel_olcu`, `_birim_cevir`, `_tutar_hesapla`,
    `_birim_etiket`, `_stok_durum_degistir`, `_safe_transaction` —
    hepsinin canlı karşılığı var (`_stok_olcu`, `_guvenli_commit`,
    sevkiyatın toplu durum güncellemesi).
  · `_senaryo_oner` — BIRAKILDI. GİB senaryosu öneriyor; e-fatura
    ekranı bağlandığında çağrılacak. Bekçinin muafiyet listesinde,
    sebebiyle birlikte.

Hiçbiri canlı bir hata saklamıyordu. Silinmelerinin sebebi, ölü bir
fonksiyonu canlı sanıp çağırmanın AF1/TS1/EM2/KD1'in ta kendisi
olması.

═══ 3 · BAĞLANAN ÜÇ UÇ ═══

  · `POST /api/cari/hareket/try_yeniden_hesapla`
    Ayarlar → **Bakım** (yeni sekme). Kur arşivine o güne ait kur
    sonradan girildiğinde, TRY karşılığı boş kalmış hareketleri
    toptan doldurur. Dolu karşılığa ve elle girilmiş kura dokunmaz.

    NOT: önce Yönetim paneline koymuştum. Tarayıcıda bastım, 409
    "firma seçilmedi" aldı — panel firma bağlamını BİLEREK
    düşürüyor, bu uç ise firmaya bağlı çalışıyor. Sekme vardı,
    düğme vardı, sonuç yoktu. Ayarlar tarafına taşındı ve testle
    çivilendi.

  · `GET /api/satislar/lookup` — Satışlar ekranına müşteri ve cins
    süzgeçleri. Listeler SUNUCUDAN geliyor: ekrandaki 300 satırdan
    türetilse, sayfalama yüzünden listede olmayan bir müşteri
    süzgeçte de görünmez ve kullanıcı "o müşteri yok" sanırdı.

  · `GET /api/satislar/musteri/<musteri>/ozet` — satış çekmecesine
    "bu müşteriyle toplamda nereye geldik" bölümü: adet, ciro,
    maliyet, kâr, marj, dönem. Tek satışın marjı yüksek olup
    müşterinin genel marjı düşük olabilir.

═══ 4 · İKİ YENİ BEKÇİ ═══

  · ÖLÜ FONKSİYON BEKÇİSİ — tanımlı ama hiçbir yerden erişilmeyen
    fonksiyon kalırsa takımı kırar. Ulaşılabilirlik: route ve Flask
    kancaları, dekoratörler, SQLAlchemy dinleyicileri (hem
    `listens_for` hem models.py'deki `_event.listen(...)`), gövde
    dışı her ad, dizge içinde geçen adlar, şablonlar, static ve
    projedeki diğer .py dosyaları. Muafiyet listesi TEK isimden
    ibaret ve sebebi yazılı — uzayan muafiyet listesi, bekçinin
    sessizce kapanmasıdır.

  · ŞABLON BETİĞİ BEKÇİSİ — her şablonun satır içi `<script>`i
    `node --check`ten geçmeli.

    BU YAMADA OLDU: çekmeceye yazdığım bir yorumun içindeki ters
    tırnak, onu saran şablon dizgesini orada sonlandırdı ve
    satislar.html'in TÜM betiği ayrıştırılamaz hâle geldi. Tablo
    "Yükleniyor…"da kaldı, süzgeçler boş geldi. **289 test geçti**,
    çünkü hiçbiri şablon JS'ini ayrıştırmıyordu. `js_denetim.py`
    bunu yakalıyor ama yalnız `gonder.sh` içinde — yani push
    anında, benim göremediğim yerde. Artık takımda.

═══ DOĞRULAMA ═══

  · 291 test geçiyor (282 → 291)
  · Yeni testler TABANDA düşüyor: KDV testi 1.000,36 ≠ 1.000,35
    diyor, ölü-kod bekçisi tam o 7 fonksiyonu sayıyor
  · Bekçiler kırılabildikleri gösterilerek doğrulandı
  · `js_denetim.py` temiz · 29 şablon ayrıştırılabiliyor
  · Üç ekran tarayıcıda açıldı, tıklandı, konsol okundu:
    süzgeç 3 satırı 2'ye indiriyor, özet paneli doğru rakamları
    basıyor, bakım düğmesi "1 hareketin TRY karşılığı dolduruldu"
    diyor. Konsolda yalnız çevrimdışı yazı tipi hatası var.
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
    'flask_app.py': 'def _kdv_ayristir(brut, kdv_oran)',
    'templates/satislar.html': 'function musteriOzetiYukle(',
    'templates/ayarlar.html': 'function tryYenidenHesapla(',
    'tests/test_kritik.py': 'def test_kd1_olu_fonksiyon_yok',
}
ONKOSUL = {
    'flask_app.py': 'def _maliyet_sayilir(',
    'templates/satislar.html': 'sFaturaBilgiAc',
    'templates/ayarlar.html': 'firmaAyarAc',
    'tests/test_kritik.py':
        'def test_yk2_her_yazma_ucu_ya_haritada_ya_kendi_denetimini_yapiyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'KD1 · flask_app.py blok 1',
     r'''    def _kdv_hesapla(toplam_tutar, kdv_oran, kdv_dahil_mi):
        """
        Tutar ve KDV oranindan matrah + KDV tutarini hesaplar.
        - kdv_dahil_mi=True  -> tutar KDV dahildir, matrah ve KDV ayristirilir
        - kdv_dahil_mi=False -> tutar matrahdir, KDV ustune eklenir
        Donus: (matrah, kdv_tutar, toplam_kdv_dahil)
        """
        tutar = float(toplam_tutar or 0)
        oran = float(kdv_oran or 0) / 100.0
        if oran <= 0:
            return q2(tutar), 0.0, q2(tutar)
        if kdv_dahil_mi:
            matrah = tutar / (1 + oran)
            kdv = tutar - matrah
            return q2(matrah), q2(kdv), q2(tutar)
        else:
            kdv = tutar * oran
            return q2(tutar), q2(kdv), q2(tutar + kdv)
''',
     r'''    # ══════════════════════════════════════════════════════════════
    #  KD1 · KDV MATEMATİĞİNİN TEK KAPISI
    #
    #  Bu iki fonksiyon yazılmıştı ama HİÇBİR YERDEN çağrılmıyordu;
    #  KDV ayrıştırma 10 ayrı uca elle yazılmıştı. Ölçüldü: ölü
    #  kapının kendisi uçlardan DAHA KÖTÜYDÜ — matrahı ve KDV'yi
    #  BİRBİRİNDEN BAĞIMSIZ yuvarladığı için ikisinin toplamı genel
    #  toplamı tutmuyordu:
    #
    #      0,45 USD · %20  ->  0,38 + 0,08 = 0,46   (toplam 0,45)
    #
    #  1.000.000 denemede 11.968 sapma. Bir faturanın matrahı ile
    #  KDV'si toplandığında faturanın kendi toplamını vermemesi,
    #  mutabakatı ve beyanı sessizce bozar.
    #
    #  ÇÖZÜM — TAMAMLAYAN YUVARLAMA: bir taraf yuvarlanır, öteki
    #  ÇIKARMAYLA bulunur. Böylece matrah + KDV == toplam HER ZAMAN.
    #  Uçlarda zaten bu yapılıyordu; doğru olan davranış kapının
    #  içine alındı ve uçlar kapıya bağlandı.
    # ══════════════════════════════════════════════════════════════
    def _kdv_ayristir(brut, kdv_oran):
        """KDV DAHİL bir tutardan matrahı sıyırır (tek değer döner).

        Birim fiyattan KDV sıyırmak da aynı işlem — stok alışında
        birim fiyat matrah olarak saklanıyor.
        """
        oran = float(kdv_oran or 0)
        tutar = float(brut or 0)
        if oran <= 0:
            return q2(tutar)
        return q2(tutar / (1 + oran / 100.0))

    def _kdv_hesapla(toplam_tutar, kdv_oran, kdv_dahil_mi):
        """
        Tutar ve KDV oranindan matrah + KDV tutarini hesaplar.
        - kdv_dahil_mi=True  -> tutar KDV dahildir, matrah ve KDV ayristirilir
        - kdv_dahil_mi=False -> tutar matrahdir, KDV ustune eklenir
        Donus: (matrah, kdv_tutar, toplam_kdv_dahil)

        GARANTİ: matrah + kdv_tutar == toplam, kuruşu kuruşuna.
        """
        tutar = q2(float(toplam_tutar or 0))
        oran = float(kdv_oran or 0)
        if oran <= 0:
            return tutar, 0.0, tutar
        if kdv_dahil_mi:
            # Genel toplam KORUNUR; KDV çıkarmayla bulunur.
            matrah = _kdv_ayristir(tutar, oran)
            return matrah, q2(tutar - matrah), tutar
        # Matrah KORUNUR; toplam toplamayla büyür.
        kdv = q2(tutar * oran / 100.0)
        return tutar, kdv, q2(tutar + kdv)
'''),
    ('flask_app.py', 'KD1 · flask_app.py blok 2',
     r'''    def _stok_temel_olcu(stok, stok_tip):
        """
        Stoğun TEMEL birimindeki ölçüsü (hesap motorunun kullandığı).
        BLOK -> tonaj,  PLAKA/EBATLI -> metraj_m2
        """
        if stok_tip == 'BLOK':
            return getattr(stok, 'tonaj', 0) or 0
        else:
            return getattr(stok, 'metraj_m2', 0) or 0

    def _birim_cevir(deger, kaynak_birim, hedef_birim, stok=None):
        """
        Bir ölçü değerini kaynak birimden hedef birime çevirir.
        m2 <-> sqft sabit katsayıyla çevrilir.
        ton <-> m3 BLOK'ta bağımsız ölçülerdir; çevrim için stok kaydı gerekir
        (stoğun kendi tonaj ve hacim_m3 oranı kullanılır).
        """
        if kaynak_birim == hedef_birim:
            return deger
        # m2 <-> sqft
        if kaynak_birim == 'm2' and hedef_birim == 'sqft':
            return deger * M2_TO_SQFT
        if kaynak_birim == 'sqft' and hedef_birim == 'm2':
            return deger / M2_TO_SQFT
        # ton <-> m3 : stoğun kendi oranıyla
        if stok and {kaynak_birim, hedef_birim} == {'ton', 'm3'}:
            tonaj = getattr(stok, 'tonaj', 0) or 0
            hacim = getattr(stok, 'hacim_m3', 0) or 0
            if kaynak_birim == 'ton' and hedef_birim == 'm3':
                return (deger / tonaj * hacim) if tonaj else 0
            if kaynak_birim == 'm3' and hedef_birim == 'ton':
                return (deger / hacim * tonaj) if hacim else 0
        return deger  # çevrilemezse aynen döner

    def _tutar_hesapla(stok, stok_tip, fiyat, fiyat_birim):
        """
        Bir stok için tutar = fiyat × (fiyat biriminin karşılığı olan ölçü).
        Örn: PLAKA, fiyat=90, fiyat_birim='m2' -> 90 × metraj_m2
             BLOK, fiyat=500, fiyat_birim='ton' -> 500 × tonaj
        """
        if not stok or not fiyat:
            return 0
        olcu = _stok_olcu(stok, fiyat_birim)
        return fiyat * olcu

    def _birim_etiket(birim):
        """Birim kodunu okunabilir etikete çevirir."""
        return {'ton': 'ton', 'm3': 'm³', 'm2': 'm²', 'sqft': 'sqft'}.get(birim, birim)

    def _stok_durum_degistir(stok_id, stok_tip, yeni_durum):
        """Stok durumunu güvenli şekilde değiştir. Geçerli durumlar: Serbest, Rezerve, Satildi, Sevkedildi."""
        stok = _stok_getir(stok_id, stok_tip)
        if stok:
            stok.durum = yeni_durum
            return True
        return False
''',
     r'''    # ── KD1 · SİLİNDİ: _stok_temel_olcu, _birim_cevir, _tutar_hesapla,
    #    _birim_etiket, _stok_durum_degistir
    #
    #    Beşi de hiçbir yerden çağrılmıyordu; işlerini yapan canlı
    #    karşılıkları var (`_stok_olcu`, sevkiyatın toplu durum
    #    güncellemesi). Ölü bir fonksiyonu canlı sanıp çağırmak,
    #    AF1/TS1/EM2'de düzelttiğimiz hata sınıfının ta kendisi —
    #    o yüzden dosyada bırakılmadılar.
'''),
    ('flask_app.py', 'KD1 · flask_app.py blok 3',
     r'''    def _cari_kimlik_ver(kayit, unvan=None):
        """Kaydın cari_id'si boşsa adından çözüp yazar. Kayıt üretilen
        her yolda kimliğin dolması, adla eşleşmeye ihtiyacı zamanla
        bitirir."""
        if kayit is None or not hasattr(kayit, 'cari_id'):
            return None
        if getattr(kayit, 'cari_id', None):
            return kayit.cari_id
        ad = unvan or getattr(kayit, 'musteri', None) or \
            getattr(kayit, 'cari_unvan', None) or getattr(kayit, 'uretici', None)
        c = _cari_bul(ad) if ad else None
        if c:
            kayit.cari_id = c.id
            return c.id
        return None
''',
     r'''    # ── KD1 · SİLİNDİ: _cari_kimlik_ver
    #
    #    Kimliği adından doldurmak için yazılmıştı ama hiç
    #    çağrılmıyordu. Ölçüldü: işi ZATEN yapılıyor — models.py
    #    içindeki `cari_id_otomatik_doldur` / `stok_cari_id_otomatik_
    #    doldur` dinleyicileri Proforma, Fatura, SatisKaydi, Sevkiyat,
    #    Rezervasyon, Siparis ve üç stok modelinde `before_insert`'te
    #    kimliği dolduruyor. Kayıt üreten 29 yerin hepsi kapsanıyor.
    #    İki ayrı kapı olması, hangisinin geçerli olduğunu belirsiz
    #    bırakırdı.
'''),
    ('flask_app.py', 'KD1 · flask_app.py blok 4',
     r'''    def _safe_transaction(func, islem_adi='işlem'):
        """Bir fonksiyonu cagiri, hata olursa otomatik rollback yapar.
        Decorator olarak da kullanilabilir.
        return: (success, sonuc_veya_hata)"""
        try:
            sonuc = func()
            db.session.commit()
            return True, sonuc
        except Exception as e:
            db.session.rollback()
            app.logger.exception(f'[{islem_adi}] islem hatasi - rollback yapildi')
            return False, str(e)
''',
     r'''    # ── KD1 · SİLİNDİ: _safe_transaction
    #    Hiç çağrılmıyordu. Yukarıdaki `_guvenli_commit` canlı ve
    #    aynı işi yapıyor; iki benzer sarmalayıcıdan birinin ölü
    #    olduğunu bilmek, hangisini çağıracağını her seferinde
    #    yeniden araştırmak demekti.
'''),
    ('flask_app.py', 'KD1 · flask_app.py blok 5',
     r'''                    fiyat = q2(fiyat_girilen / (1 + kdv_oran/100))
                else:
                    fiyat = fiyat_girilen
                # Toplam tutarlar
''',
     r'''                    fiyat = _kdv_ayristir(fiyat_girilen, kdv_oran)   # KD1
                else:
                    fiyat = fiyat_girilen
                # Toplam tutarlar
'''),
    ('flask_app.py', 'KD1 · flask_app.py blok 6',
     r'''                    # KDV dahil girilmis: ayristir
                    fiyat = q2(fiyat_girilen / (1 + kdv_oran/100))
''',
     r'''                    # KDV dahil girilmis: ayristir
                    fiyat = _kdv_ayristir(fiyat_girilen, kdv_oran)   # KD1
'''),
    ('flask_app.py', 'KD1 · flask_app.py blok 7',
     r'''                    fiyat = q2(fiyat_girilen / (1 + kdv_oran/100))
''',
     r'''                    fiyat = _kdv_ayristir(fiyat_girilen, kdv_oran)   # KD1
'''),
    ('flask_app.py', 'KD1 · flask_app.py blok 8',
     r'''        if yeni_kdv_oran > 0:
            yeni_matrah = mevcut_toplam / (1 + yeni_kdv_oran/100)
            yeni_kdv_tutar = mevcut_toplam - yeni_matrah
        else:
            # KDV YOK: matrah = toplam, kdv_tutar = 0
            yeni_matrah = mevcut_toplam
            yeni_kdv_tutar = 0
''',
     r'''        # KD1: tek kapı. Toplam KDV DAHİL olduğu için kapının
        # "dahil" dalı kullanılıyor; matrah + kdv == toplam garanti.
        # Eskiden ikisi birbirinden bağımsız yuvarlanıyordu ve
        # faturanın matrahı ile KDV'si toplamını tutmayabiliyordu.
        yeni_matrah, yeni_kdv_tutar, _ = _kdv_hesapla(
            mevcut_toplam, yeni_kdv_oran, True)
'''),
    ('flask_app.py', 'KD1 · flask_app.py blok 9',
     r'''            if kdv_dahil_mi:
                # Girilen tutar KDV dahil → matrahı ayır
                matrah = q2(islem_tutar / (1 + kdv_oran / 100.0))
                kdv_tutar = q2(islem_tutar - matrah)
                # borc/alacak zaten genel toplam, değişmez
            else:
                # Girilen tutar matrah → KDV'yi üste ekle, toplamı büyüt
                matrah = islem_tutar
                kdv_tutar = q2(matrah * kdv_oran / 100.0)
                islem_tutar = q2(matrah + kdv_tutar)
''',
     r'''            # KD1: tek kapı. Kapı üç değer döner ve matrah + KDV
            # her zaman toplamı verir.
            matrah, kdv_tutar, _brut = _kdv_hesapla(
                islem_tutar, kdv_oran, kdv_dahil_mi)
            if kdv_dahil_mi:
                # borc/alacak zaten genel toplam, değişmez
                pass
            else:
                # Girilen tutar matrah → KDV'yi üste ekle, toplamı büyüt
                islem_tutar = _brut
'''),
    ('flask_app.py', 'KD1 · flask_app.py blok 10',
     r'''        # Net matrah ve KDV hesapla
        if kdv_dahil_mi and kdv_oran > 0:
            net_tutar = q2(tutar_ham / (1 + kdv_oran / 100))
            kdv_tutar = q2(tutar_ham - net_tutar)
        elif not kdv_dahil_mi and kdv_oran > 0:
            net_tutar = tutar_ham
            kdv_tutar = q2(tutar_ham * kdv_oran / 100)
        else:
            net_tutar = tutar_ham
            kdv_tutar = 0.0
''',
     r'''        # Net matrah ve KDV — KD1: tek kapı
        net_tutar, kdv_tutar, _kdv_brut = _kdv_hesapla(
            tutar_ham, kdv_oran, kdv_dahil_mi)
'''),
    ('flask_app.py', 'KD1 · flask_app.py blok 11',
     r'''        if kdv_dahil_mi and kdv_oran > 0:
            toplam_net = q2(tutar_ham / (1 + kdv_oran / 100))
            toplam_kdv = q2(tutar_ham - toplam_net)
        elif not kdv_dahil_mi and kdv_oran > 0:
            toplam_net = tutar_ham
            toplam_kdv = q2(tutar_ham * kdv_oran / 100)
        else:
            toplam_net = tutar_ham
            toplam_kdv = 0.0

        satirlar, olcu_notu, kullanilan = _maliyet_dagitim_plani(
''',
     r'''        # KD1: tek kapı
        toplam_net, toplam_kdv, _kdv_brut = _kdv_hesapla(
            tutar_ham, kdv_oran, kdv_dahil_mi)

        satirlar, olcu_notu, kullanilan = _maliyet_dagitim_plani(
'''),
    ('flask_app.py', 'KD1 · flask_app.py blok 12',
     r'''        # Net matrah ve KDV
        if kdv_dahil_mi and kdv_oran > 0:
            toplam_net = q2(tutar_ham / (1 + kdv_oran / 100))
            toplam_kdv = q2(tutar_ham - toplam_net)
        elif not kdv_dahil_mi and kdv_oran > 0:
            toplam_net = tutar_ham
            toplam_kdv = q2(tutar_ham * kdv_oran / 100)
        else:
            toplam_net = tutar_ham
            toplam_kdv = 0.0
''',
     r'''        # Net matrah ve KDV — KD1: tek kapı
        toplam_net, toplam_kdv, _kdv_brut = _kdv_hesapla(
            tutar_ham, kdv_oran, kdv_dahil_mi)
'''),
    ('flask_app.py', 'KD1 · flask_app.py blok 13',
     r'''        if kdv_oran > 0:
            ara_toplam = toplam / (1 + kdv_oran / 100)
            kdv_tutar = toplam - ara_toplam
        else:
            ara_toplam = toplam
            kdv_tutar = 0
''',
     r'''        # KD1: tek kapı. Proforma toplamı KDV DAHİL; ara toplam ile
        # KDV'nin toplamı her zaman proformanın toplamını verir.
        ara_toplam, kdv_tutar, _ = _kdv_hesapla(toplam, kdv_oran, True)
'''),
    ('templates/satislar.html', 'KD1 · templates/satislar.html blok 1',
     r'''  <div class="suz"><input id="ara" placeholder="Müşteri, cins, fatura no ara…" autocomplete="off"></div>
''',
     r'''  <!-- KD1: `GET /api/satislar/lookup` yazılmıştı ama hiçbir ekrandan
       çağrılmıyordu. Listeler SUNUCUDAN geliyor, ekrandaki 300
       satırdan türetilmiyor: sayfalama yüzünden ekranda olmayan bir
       müşteri süzgeçte de görünmezdi ve kullanıcı "o müşteri yok"
       sanırdı. -->
  <select id="sMusteri" style="max-width:190px">
    <option value="">Tüm müşteriler</option></select>
  <select id="sCins" style="max-width:170px">
    <option value="">Tüm cinsler</option></select>
  <div class="suz"><input id="ara" placeholder="Müşteri, cins, fatura no ara…" autocomplete="off"></div>
'''),
    ('templates/satislar.html', 'KD1 · templates/satislar.html blok 2',
     r'''let TUM = [], OZET = {}, FILTRE = '', ARA = '';
''',
     r'''let TUM = [], OZET = {}, FILTRE = '', ARA = '';
let F_MUSTERI = '', F_CINS = '';
'''),
    ('templates/satislar.html', 'KD1 · templates/satislar.html blok 3',
     r'''  kpiCiz(); ciz();
''',
     r'''  kpiCiz(); ciz();
}

/* KD1 · süzgeç listeleri sunucudan. Hata olursa SESSİZCE geçilir:
   liste gelmezse süzgeçler "Tümü"de kalır ve ekran çalışmaya devam
   eder — bir yardımcı listenin yokluğu satış tablosunu kapatmamalı. */
async function suzgecListeleri() {
  try {
    const d = await api('/api/satislar/lookup');
    const doldur = (id, degerler) => {
      const s = document.getElementById(id);
      if (!s) return;
      for (const v of (degerler || [])) {
        const o = document.createElement('option');
        o.value = v; o.textContent = v;
        s.appendChild(o);
      }
    };
    doldur('sMusteri', d.musteriler);
    doldur('sCins', d.cinsler);
  } catch (e) { /* süzgeç yoksa ekran yine çalışır */ }
'''),
    ('templates/satislar.html', 'KD1 · templates/satislar.html blok 4',
     r'''    if (s && ![x.id, x.musteri, x.cins, x.fatura_no, x.stok_tip].filter(Boolean)
''',
     r'''    if (F_MUSTERI && x.musteri !== F_MUSTERI) return false;   /* KD1 */
    if (F_CINS && x.cins !== F_CINS) return false;            /* KD1 */
    if (s && ![x.id, x.musteri, x.cins, x.fatura_no, x.stok_tip].filter(Boolean)
'''),
    ('templates/satislar.html', 'KD1 · templates/satislar.html blok 5',
     r'''function detayAc(id) {
''',
     r'''/* KD1 · çekmecenin sonuna MÜŞTERİ ÖZETİ bölümü eklendi (#msOzet).
   GET /api/satislar/musteri/<musteri>/ozet yazılmıştı ama hiçbir
   ekrandan çağrılmıyordu. Yeri burası: tek bir satışa bakarken "bu
   müşteriyle toplamda nereye geldik" sorusunun cevabı, satışın kendi
   kârını okumak kadar gerekli — tek satışın marjı yüksek olup
   müşterinin genel marjı düşük olabilir. Bölüm çekmece AÇILDIKTAN
   sonra asenkron doldurulur, çekmece özeti beklemez.

   DİKKAT: aşağıdaki `govde` bir şablon dizgesidir. İçine ters tırnak
   koymak (bir yorumda bile) dizgeyi orada sonlandırır ve TÜM betik
   ayrıştırılamaz hâle gelir — ölçüldü, ekran "Yükleniyor…"da kaldı. */
function detayAc(id) {
'''),
    ('templates/satislar.html', 'KD1 · templates/satislar.html blok 6',
     r'''    </div>`;
''',
     r'''    </div>
    <div id="msOzet" style="margin-top:14px"></div>`;
'''),
    ('templates/satislar.html', 'KD1 · templates/satislar.html blok 7',
     r'''  cekmeceAc(kacar(x.musteri || id), `${x.id} · ${x.satis_tarihi || ''}`, govde, eylem.join(''));
''',
     r'''  cekmeceAc(kacar(x.musteri || id), `${x.id} · ${x.satis_tarihi || ''}`, govde, eylem.join(''));
  musteriOzetiYukle(x.musteri);   /* KD1 */
}

/* KD1 · MÜŞTERİ ÖZETİ
   Çekmece açıldıktan SONRA dolduruluyor; uç yavaşsa ya da hata
   verirse çekmecenin kendisi etkilenmiyor ve bölüm sessizce boş
   kalıyor. Tek satışın detayı, bir yardımcı özet yüzünden
   görünmez kalmamalı. */
async function musteriOzetiYukle(musteri) {
  const kutu = document.getElementById('msOzet');
  if (!kutu || !musteri) return;
  let d;
  try {
    d = await api('/api/satislar/musteri/' +
                  encodeURIComponent(musteri) + '/ozet');
  } catch (e) { return; }
  if (!d || !d.adet) return;
  const marj = Number(d.marj_yuzde || 0);
  const renk = marj >= 25 ? '--verde' : marj >= 15 ? '--kehribar' : '--kirmizi';
  const satir = (l, v) => `<div style="display:flex;justify-content:space-between;
      padding:5px 0;border-bottom:1px solid var(--cizgi)">
      <span style="color:var(--soluk)">${l}</span>
      <span class="mono" style="font-weight:600">${v}</span></div>`;
  const aralik = [d.ilk_satis, d.son_satis].filter(Boolean);
  kutu.innerHTML = `
    <div class="panel" style="padding:12px 14px">
      <h4 style="margin:0 0 8px;font-size:.86rem">
        ${kacar(musteri)} · tüm satışlar</h4>
      ${satir('Satış adedi', d.adet)}
      ${satir('Ciro', para2(d.toplam_usd))}
      ${satir('Maliyet', para2(d.maliyet_usd))}
      ${satir('Kâr', `<span style="color:var(--verde)">${para2(d.kar_usd)}</span>`)}
      ${satir('Marj', `<span style="color:var(${renk})">%${
         marj.toFixed(1).replace('.', ',')}</span>`)}
      ${aralik.length === 2 && aralik[0] !== aralik[1]
         ? satir('Dönem', kacar(aralik[0]) + ' → ' + kacar(aralik[1]))
         : (aralik.length ? satir('Satış tarihi', kacar(aralik[0])) : '')}
    </div>`;
'''),
    ('templates/satislar.html', 'KD1 · templates/satislar.html blok 8',
     r'''  araZaman = setTimeout(() => { ARA = e.target.value; ciz(); }, 200);
''',
     r'''  araZaman = setTimeout(() => { ARA = e.target.value; ciz(); }, 200);
});
/* KD1 */
document.getElementById('sMusteri').addEventListener('change', e => {
  F_MUSTERI = e.target.value; ciz();
});
document.getElementById('sCins').addEventListener('change', e => {
  F_CINS = e.target.value; ciz();
'''),
    ('templates/satislar.html', 'KD1 · templates/satislar.html blok 9',
     r'''</script>
''',
     r'''suzgecListeleri();   /* KD1 */
</script>
'''),
    ('templates/ayarlar.html', 'KD1 · templates/ayarlar.html blok 1',
     r'''  {% endif %}
''',
     r'''  {# KD1: Bakım, Yönetim panelinde DEĞİL burada. Yönetim paneli
     firma bağlamını bilerek düşürüyor (session.pop('firma_id')),
     bakım ucu ise firmaya bağlı çalışıyor — ÖLÇÜLDÜ: düğme orada
     409 "firma seçilmedi" alıyordu. Çalışmayan bir düğme, hiç
     olmayan düğmeden kötüdür. #}
  <button class="sekme" data-b="bakim">Bakım</button>
  {% endif %}
'''),
    ('templates/ayarlar.html', 'KD1 · templates/ayarlar.html blok 2',
     r'''    <button class="btn-yeni" onclick="bankaAc()">+ Yeni Banka Hesabı</button>
''',
     r'''    <button class="btn-yeni" onclick="bankaAc()">+ Yeni Banka Hesabı</button>
  </div>
</section>

<!-- ══════════════════════════════════════════════════════════════
     KD1 · BAKIM

     `POST /api/cari/hareket/try_yeniden_hesapla` yazılmıştı ama
     hiçbir ekrandan çağrılmıyordu — çalıştırmanın tek yolu elle
     istek atmaktı.
     ═══════════════════════════════════════════════════════════ -->
<section class="bolum" id="b-bakim">
  <div class="panel">
    <h4>TRY Karşılıklarını Tamamla</h4>
    <p style="color:var(--soluk);font-size:.83rem;margin-bottom:12px">
      Dövizli bir cari hareket, kaydedildiği gün kur arşivinde o güne
      ait kur <strong>yoksa</strong> TRY karşılığı boş kalır. Kuru
      sonradan girdiğinde bu düğme, karşılığı boş kalmış hareketleri
      arşivden toptan doldurur. <strong>Dolu olan hiçbir karşılığa
      dokunmaz</strong> ve elle girilmiş kurları değiştirmez.
      Aktif firmanın hareketleri üzerinde çalışır.
    </p>
    <div id="tryKutu" style="background:var(--notr-bg);border-radius:7px;
         padding:10px 12px;font-size:.8rem;color:var(--soluk);
         margin-bottom:12px;display:none"></div>
    <button class="btn-yeni" id="tryBtn" onclick="tryYenidenHesapla()">
      TRY Karşılıklarını Tamamla</button>
'''),
    ('templates/ayarlar.html', 'KD1 · templates/ayarlar.html blok 3',
     r'''async function yedekGeriYukle(dosya) {
''',
     r'''/* ══════════════════════════════════════════════════════════════════
   KD1 · TRY KARŞILIKLARINI TAMAMLA

   Uç TOPLU yazıyor, o yüzden önce onay soruluyor. Sonuç KALICI
   olarak gösteriliyor (sadece bildirim değil): "kaç hareket için kur
   bulunamadı" sayısı, kur arşivine hangi günlerin girilmesi
   gerektiğini söyleyen tek bilgi — bildirimin kaybolmasıyla
   kaybolmamalı.
   ═══════════════════════════════════════════════════════════════ */
async function tryYenidenHesapla() {
  if (!await onayla('TRY karşılığı boş kalmış tüm cari hareketler, kur ' +
      'arşivinden yeniden hesaplanacak.\n\nDolu olan karşılıklara ' +
      'DOKUNULMAZ. Devam edilsin mi?')) return;
  const btn = document.getElementById('tryBtn');
  const kutu = document.getElementById('tryKutu');
  btn.disabled = true; btn.textContent = 'Hesaplanıyor…';
  try {
    const d = await api('/api/cari/hareket/try_yeniden_hesapla', {
      method: 'POST', body: JSON.stringify({})
    });
    const g = Number(d.guncellenen || 0), b = Number(d.bulunmayan || 0);
    kutu.style.display = 'block';
    kutu.innerHTML = `<strong>${g}</strong> hareketin TRY karşılığı ` +
      `dolduruldu.` + (b
        ? ` <span style="color:var(--kehribar);font-weight:600">${b} hareket` +
          ` için kur bulunamadı</span> — o günlerin kurunu Döviz Kur` +
          ` ekranından girip tekrar dene.`
        : ` Karşılığı eksik hareket kalmadı.`);
    bildir(d.mesaj || (g + ' hareket güncellendi'));
  } catch (e) { /* api() zaten bildirdi */ }
  finally {
    btn.disabled = false; btn.textContent = 'TRY Karşılıklarını Tamamla';
  }
}

async function yedekGeriYukle(dosya) {
'''),
    ('templates/ayarlar.html', 'KD1 · templates/ayarlar.html blok 4',
     r'''  if (!yuklendi[ad]) { yuklendi[ad] = true; yukleyici[ad](); }
''',
     r'''  /* KD1: `yukleyici[ad]` doğrudan çağrılıyordu ve yükleyicisi
     OLMAYAN bir sekme (Bakım — yüklenecek verisi yok) eklendiğinde
     "yukleyici[ad] is not a function" atıyordu. Hata sekme
     değişiminin ORTASINDA düşüyor: bölüm açılmış ama sayfadaki
     betik o noktada durmuş oluyor. Varlık kontrolü, aşağıdaki
     açılış kodunda zaten yapılıyordu — iki yerde iki kural kalmasın. */
  if (!yuklendi[ad] && yukleyici[ad]) {
    yuklendi[ad] = true; yukleyici[ad]();
  }
'''),
    ('tests/test_kritik.py', 'KD1 · tests/test_kritik.py blok 1',
     r'''    assert aya == {'eposta', 'listeler', 'banka'}, aya
''',
     r'''    # KD1: "Bakım" EKLENDİ ve bilerek Ayarlar tarafında — yönetim
    # paneli firma bağlamını düşürüyor, bakım ucu ise firmaya bağlı
    # çalışıyor (orada 409 "firma seçilmedi" alıyordu, ölçüldü).
    assert aya == {'eposta', 'listeler', 'banka', 'bakim'}, aya
'''),
    ('tests/test_kritik.py', 'KD1 · tests/test_kritik.py blok 2',
     r'''        'yetkili kullanıcı da çağırabilir: ' + '; '.join(sorted(acik)))
''',
     r'''        'yetkili kullanıcı da çağırabilir: ' + '; '.join(sorted(acik)))


# ══════════════════════════════════════════════════════════════════
#  KD1 · KDV MATEMATİĞİNİN TEK KAPISI + ÖLÜ FONKSİYON BEKÇİSİ
#
#  Sınıf, AF1/TS1/EM2'nin aynısı: ortak kapı YAZILMIŞ ama hiçbir
#  yerden çağrılmıyor; iş 10 ayrı yere elle kopyalanmış. Buradaki
#  fark, ölçüm beklenmedik bir şey söyledi: ÖLÜ KAPI, CANLI UÇLARDAN
#  DAHA KÖTÜYDÜ. Matrahı ve KDV'yi birbirinden bağımsız yuvarladığı
#  için ikisinin toplamı genel toplamı tutmuyordu:
#
#      1.000,35 USD · %20  ->  833,63 + 166,73 = 1.000,36
#
#  Yani "ortak kapıya bağla" refleksi, 10 para yoluna hata EKLERDİ.
#  Kapı önce düzeltildi (tamamlayan yuvarlama: bir taraf yuvarlanır,
#  öteki çıkarmayla bulunur), sonra uçlar bağlandı.
# ══════════════════════════════════════════════════════════════════
def test_kd1_fatura_kdv_duzeltmesi_matrah_ve_kdv_toplami_tutuyor():
    """Matrah + KDV, faturanın kendi toplamını vermeli."""
    from models import Fatura
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(Cari(id='MUS-KD1', unvan='MUSTERI KD1',
                            cari_tip='Müşteri'))
        db.session.add(Fatura(
            id='FT-KD1', fatura_no='KD1-001', cari_id='MUS-KD1',
            musteri='MUSTERI KD1', yon='satis', durum='Kesildi',
            doviz='USD', toplam=1000.35, ara_toplam=1000.35,
            kdv_oran=0, kdv_tutar=0,
            fatura_tarihi=date(2026, 10, 28)))
        db.session.commit()

    r = c.post('/api/diag/fatura/FT-KD1/kdv_duzelt?kdv_oran=20', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)[:300]

    with fa.app.app_context():
        f = db.session.get(Fatura, 'FT-KD1')
        matrah = float(f.ara_toplam or 0)
        kdv = float(f.kdv_tutar or 0)
        toplam = float(f.toplam or 0)
    # ESKI DAVRANIS: 833.63 + 166.73 = 1000.36  (toplam 1000.35)
    assert round(matrah + kdv, 2) == round(toplam, 2), (
        f'matrah {matrah} + KDV {kdv} = {round(matrah + kdv, 2)} '
        f'ama faturanın toplamı {toplam}')
    assert matrah == 833.63, matrah
    assert kdv == 166.72, kdv


def test_kd1_kdv_ayristirma_elle_yazilmamis():
    """KDV ayrıştırma formülü TEK yerde olmalı.

    EM2'nin maliyet kapısı bekçisiyle aynı desen: formülün kendisini
    aramak, onu kopyalayan yeni bir ucu doğduğu gün yakalar."""
    import io as _io
    import re as _re
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    satirlar = kaynak.split('\n')
    # `_kdv_ayristir` govdesinin kendisi MUAF — kapi orada.
    kapi = [i for i, t in enumerate(satirlar, 1)
            if 'def _kdv_ayristir(' in t]
    assert kapi, 'kapı (_kdv_ayristir) bulunamadı'
    kapi_araligi = range(kapi[0], kapi[0] + 12)

    desen = _re.compile(r'/\s*\(\s*1\s*\+\s*[a-z_]*kdv[a-z_]*')
    kacak = [f'satır {i}: {t.strip()[:70]}'
             for i, t in enumerate(satirlar, 1)
             if desen.search(t) and i not in kapi_araligi]
    assert not kacak, (
        'KDV ayrıştırma formülü kapının DIŞINDA elle yazılmış — '
        '`_kdv_ayristir` / `_kdv_hesapla` kullanılmalı: '
        + '; '.join(kacak))

    # Kapi TAMAMLAYAN yuvarlama yapiyor mu: bir taraf cikarmayla
    # bulunmali. "q2(tutar - matrah)" bunun imzasi.
    g = '\n'.join(satirlar[kapi[0] - 20:kapi[0] + 40])
    assert 'q2(tutar - matrah)' in g, (
        'kapı matrahı ve KDV\'yi bağımsız yuvarlıyor olabilir — '
        'tamamlayan yuvarlama (çıkarma) izi yok')


def test_kd1_olu_fonksiyon_yok():
    """Tanımlanmış ama hiçbir yerden erişilmeyen fonksiyon olmamalı.

    BU SINIFIN BEKÇİSİ. AF1'in ölü çek süzgeci, TS1'in kasa geri
    alması, EM2'nin maliyet kapısı ve KD1'in KDV kapısı — dördü de
    "kod doğru ama çağrılmıyor" idi. Tarama, yarın yazılıp bir yere
    bağlanmayı bekleyen bir fonksiyonu görünür kılar.

    ULAŞILABİLİRLİK: @app.route ve Flask kancaları, dekoratörler,
    SQLAlchemy dinleyicileri (`listens_for` ve models.py'deki
    `_event.listen(...)` çağrıları), gövde dışında geçen her ad,
    dizge içinde geçen adlar (url_for/getattr), şablonlar, static
    ve projedeki diğer .py dosyaları.
    """
    import ast as _ast
    import io as _io
    import re as _re

    ANA = os.path.join(KOK, 'flask_app.py')
    kaynak = _io.open(ANA, encoding='utf-8').read().replace('\r\n', '\n')
    agac = _ast.parse(kaynak)

    KANCA = {
        'route', 'before_request', 'after_request', 'before_first_request',
        'teardown_request', 'teardown_appcontext', 'errorhandler',
        'context_processor', 'template_filter', 'template_global',
        'template_test', 'command', 'cli', 'app_errorhandler',
        'shell_context_processor', 'url_value_preprocessor', 'url_defaults',
        'user_loader', 'property', 'staticmethod', 'classmethod',
        'contextmanager', 'cache', 'lru_cache', 'validates', 'event',
        # ÖLÇÜLDÜ: ilk halimde bu yoktu ve `_cari_hareket_okunur_id`
        # (RN1 dinleyicisi) "ölü" diye işaretlendi. SQLAlchemy onu
        # her insert'te çağırıyor.
        'listens_for', 'hybrid_property', 'setter', 'expression',
    }

    def _dek(fn):
        out = []
        for d in fn.decorator_list:
            k = d.func if isinstance(d, _ast.Call) else d
            if isinstance(k, _ast.Attribute):
                out.append(k.attr)
            elif isinstance(k, _ast.Name):
                out.append(k.id)
        return out

    sinif_ici = set()
    for s in _ast.walk(agac):
        if isinstance(s, _ast.ClassDef):
            for a in _ast.walk(s):
                if isinstance(a, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                    sinif_ici.add((a.name, a.lineno))

    tanim = {}
    for fn in _ast.walk(agac):
        if isinstance(fn, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            tanim.setdefault(fn.name, []).append(
                (fn.lineno, fn.end_lineno, _dek(fn),
                 (fn.name, fn.lineno) in sinif_ici))

    # Dekorator satirlari "kullanim" sayilmaz: dekorator olarak
    # kullanilmak zaten KANCA uzerinden degerlendiriliyor.
    dek_satir = set()
    for fn in _ast.walk(agac):
        if isinstance(fn, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            for d in fn.decorator_list:
                for a in _ast.walk(d):
                    dek_satir.add(getattr(a, 'lineno', 0))

    kullanim = {}
    for d in _ast.walk(agac):
        ad = None
        if isinstance(d, _ast.Name) and isinstance(d.ctx, _ast.Load):
            ad = d.id
        elif isinstance(d, _ast.Attribute) and isinstance(d.ctx, _ast.Load):
            ad = d.attr
        if ad:
            kullanim.setdefault(ad, set()).add(getattr(d, 'lineno', 0))

    dizge = '\n'.join(d.value for d in _ast.walk(agac)
                      if isinstance(d, _ast.Constant)
                      and isinstance(d.value, str))

    # Sablonlar, static ve PROJEDEKI DIGER .py dosyalari.
    # models.py burada onemli: `_event.listen(Model, 'before_insert',
    # cari_id_otomatik_doldur)` gibi EMIR KIPLI kayitlar yalnizca
    # oradaki metinde gorunuyor.
    disari = []
    for dizin in ('templates', 'static'):
        kok = os.path.join(KOK, dizin)
        for yer, _, dosyalar in os.walk(kok):
            for ad in dosyalar:
                if ad.endswith(('.html', '.js')):
                    disari.append(_io.open(os.path.join(yer, ad),
                                           encoding='utf-8',
                                           errors='replace').read())
    for yer, _, dosyalar in os.walk(KOK):
        if '/.git' in yer or '__pycache__' in yer:
            continue
        for ad in dosyalar:
            if ad.endswith('.py') and os.path.join(yer, ad) != ANA:
                disari.append(_io.open(os.path.join(yer, ad),
                                       encoding='utf-8',
                                       errors='replace').read())
    disari = '\n'.join(disari)

    # MUAF: bilerek bekletilen fonksiyonlar. Liste KISA kalmalı —
    # uzayan bir muafiyet listesi, bekçinin sessizce kapanmasıdır.
    MUAF = {
        # GİB senaryosu önerir (IHRACAT / TEMELFATURA). E-fatura
        # ekranı bağlandığında çağrılacak; silinmesi yerine
        # bekletilmesi KD1'de bilerek seçildi.
        '_senaryo_oner',
    }

    olu = []
    for ad, yerler in sorted(tanim.items()):
        if ad in MUAF or ad.startswith('__') or len(yerler) > 1:
            continue
        satir, son, dekler, sinifta = yerler[0]
        if sinifta or (set(dekler) & KANCA):
            continue
        dis = {s for s in kullanim.get(ad, set())
               if not (satir <= s <= son) and s not in dek_satir}
        if dis:
            continue
        kalip = r'\b%s\b' % _re.escape(ad)
        if _re.search(kalip, dizge) or _re.search(kalip, disari):
            continue
        olu.append(f'{ad} (satır {satir}, {son - satir + 1} satır)')

    assert not olu, (
        'hiçbir yerden çağrılmayan fonksiyon(lar) — ya bir yere '
        'bağlanmalı ya silinmeli: ' + ', '.join(olu))


def test_kd1_bekci_olu_fonksiyonu_gercekten_yakaliyor():
    """Bekçi, bilerek eklenmiş ölü bir fonksiyonu görmeli.

    HY1'de bekçinin kendisi yanlış yazılmıştı ve "temiz" sonucu
    şanstı. Bir bekçiye, kırmadığını görmeden güvenilmez."""
    import ast as _ast
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    sahte = kaynak + (
        '\n\ndef _kd1_bekci_denemesi_hic_cagrilmayan():\n'
        '    return 42\n')
    agac = _ast.parse(sahte)
    adlar = {f.name for f in _ast.walk(agac)
             if isinstance(f, (_ast.FunctionDef, _ast.AsyncFunctionDef))}
    assert '_kd1_bekci_denemesi_hic_cagrilmayan' in adlar
    # Govde disinda HICBIR kullanimi olmamali — bekcinin olculdugu sey.
    kullanim = [d for d in _ast.walk(agac)
                if isinstance(d, _ast.Name)
                and d.id == '_kd1_bekci_denemesi_hic_cagrilmayan'
                and isinstance(d.ctx, _ast.Load)]
    assert not kullanim, 'deneme fonksiyonu beklenmedik şekilde çağrılıyor'


def test_kd1_uc_uc_artik_bir_ekrandan_cagriliyor():
    """Bağlanan üç uç şablonlarda GEÇMELİ (SD4/EK1 ile aynı bekçi)."""
    import io as _io
    _sablon = os.path.join(KOK, 'templates')
    tum = ''
    for ad in os.listdir(_sablon):
        if ad.endswith('.html'):
            tum += _io.open(os.path.join(_sablon, ad),
                            encoding='utf-8', errors='replace').read()
    for yol, nerede in (
            ('/api/cari/hareket/try_yeniden_hesapla', 'TRY karşılığı bakımı'),
            ('/api/satislar/lookup', 'satış süzgeç listeleri'),
            ('/api/satislar/musteri/', 'müşteri satış özeti')):
        assert yol in tum, f'{nerede} ({yol}) hiçbir şablonda yok'
    satislar = _io.open(os.path.join(_sablon, 'satislar.html'),
                        encoding='utf-8').read()
    assert 'suzgecListeleri' in satislar
    assert 'musteriOzetiYukle' in satislar
    ayarlar = _io.open(os.path.join(_sablon, 'ayarlar.html'),
                       encoding='utf-8').read()
    assert 'tryYenidenHesapla' in ayarlar

    # ── BAKIM SEKMESİ DOĞRU PANELDE Mİ ──
    # ÖLÇÜLDÜ: önce Yönetim paneline koymuştum ve düğme 409 "firma
    # seçilmedi" alıyordu — panel firma bağlamını bilerek düşürüyor
    # (session.pop('firma_id')), bakım ucu ise firmaya bağlı. Tarayıcıda
    # basmadan görünmezdi: sekme vardı, düğme vardı, sonuç yoktu.
    c = istemci('admin', 'ADMIN')
    _aya = c.get('/ayarlar').get_data(as_text=True)
    _yon = c.get('/yonetim').get_data(as_text=True)
    assert 'id="b-bakim"' in _aya, 'Bakım bölümü Ayarlar\'da basılmıyor'
    assert 'id="b-bakim"' not in _yon, (
        'Bakım bölümü Yönetim panelinde — orada firma seçili değil, '
        'düğme 409 alır')


def test_kd1_try_yeniden_hesapla_bos_karsiligi_dolduruyor():
    """Kur sonradan girilince boş TRY karşılığı dolmalı."""
    c = istemci('admin', 'ADMIN')
    _t = date(2026, 3, 17)
    with fa.app.app_context():
        db.session.add(Cari(id='MUS-KD2', unvan='MUSTERI KD2',
                            cari_tip='Müşteri', para_birimi='USD'))
        db.session.add(CariHareket(
            id='HR-KD2', cari_id='MUS-KD2', cari_unvan='MUSTERI KD2',
            hareket_tarihi=_t, islem_tip='Satis Faturasi',
            doviz='USD', borc=1000, alacak=0,
            borc_try=None, alacak_try=None))
        # `_kur_getir` önceliği: alis -> efektif -> satis
        db.session.add(DovizKur(doviz='USD', tarih=_t, alis=38.40,
                                satis=38.60, efektif=38.40))
        db.session.commit()

    r = c.post('/api/cari/hareket/try_yeniden_hesapla', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    j = r.get_json()
    assert j.get('ok') is True, j
    assert j.get('guncellenen', 0) >= 1, j

    with fa.app.app_context():
        h = db.session.get(CariHareket, 'HR-KD2')
        assert h.borc_try == 38400.0, h.borc_try
        assert float(h.kur_uygulanan or 0) == 38.40, h.kur_uygulanan
        assert h.kur_kaynak == 'TCMB', h.kur_kaynak


def test_kd1_satis_suzgeci_ve_musteri_ozeti():
    """Süzgeç listesi ve müşteri özeti gerçek veriyi döndürmeli."""
    from models import SatisKaydi
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(Cari(id='MUS-KD3', unvan='KD3 STONE LLC',
                            cari_tip='Müşteri', para_birimi='USD'))
        for i, (tutar, maliyet, t) in enumerate((
                (10000, 7000, date(2026, 2, 3)),
                (20000, 13000, date(2026, 6, 9))), 1):
            db.session.add(SatisKaydi(
                id=f'SK-KD3-{i}', cari_id='MUS-KD3',
                musteri='KD3 STONE LLC', cins='KD3 Beyaz',
                stok_tip='PLAKA', miktar=100, birim='m2',
                doviz='USD', tutar_usd=tutar, maliyet_usd=maliyet,
                kar_usd=tutar - maliyet, satis_tarihi=t))
        db.session.commit()

    d = c.get('/api/satislar/lookup', headers=H)
    assert d.status_code == 200, d.get_data(as_text=True)[:200]
    j = d.get_json()
    assert 'KD3 STONE LLC' in (j.get('musteriler') or []), j
    assert 'KD3 Beyaz' in (j.get('cinsler') or []), j

    o = c.get('/api/satislar/musteri/KD3%20STONE%20LLC/ozet', headers=H)
    assert o.status_code == 200, o.get_data(as_text=True)[:200]
    jo = o.get_json()
    assert jo.get('adet') == 2, jo
    assert float(jo.get('toplam_usd') or 0) == 30000.0, jo
    assert float(jo.get('kar_usd') or 0) == 10000.0, jo
    # 10.000 / 30.000 = %33,33
    assert round(float(jo.get('marj_yuzde') or 0), 2) == 33.33, jo
    assert jo.get('ilk_satis') == '2026-02-03', jo
    assert jo.get('son_satis') == '2026-06-09', jo


def test_kd1_sablon_betikleri_ayristirilabiliyor():
    """Her şablonun satır içi <script>'i node ile ayrıştırılmalı.

    BU YAMADA OLDU: çekmeceye eklediğim bir yorumun içindeki ters
    tırnak, onu saran şablon dizgesini orada sonlandırdı ve
    satislar.html'in TÜM betiği ayrıştırılamaz hâle geldi — tablo
    "Yükleniyor…"da kaldı, süzgeçler boş geldi. 289 test geçti,
    çünkü hiçbiri şablon JS'ini ayrıştırmıyordu.

    `js_denetim.py` bunu yakalıyor ama yalnızca `gonder.sh`
    içinde — yani push anında. Takımın içinde de olması gerekiyor:
    hatanın DOĞDUĞU yerde çıkması, push'ta çıkmasından iyidir.
    """
    import io as _io
    import os as _os
    import re as _re
    import shutil as _shutil
    import subprocess as _sp
    import tempfile as _tf

    node = _shutil.which('node') or _shutil.which('nodejs')
    if not node:
        import pytest as _pytest
        _pytest.skip('node yok')

    _sablon = _os.path.join(KOK, 'templates')
    # src= taşıyan <script> dış dosya; gövdesi yok.
    desen = _re.compile(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', _re.S)
    kirik = []
    gec = _tf.mkdtemp()
    for ad in sorted(_os.listdir(_sablon)):
        if not ad.endswith('.html'):
            continue
        metin = _io.open(_os.path.join(_sablon, ad),
                         encoding='utf-8', errors='replace').read()
        for sira, m in enumerate(desen.finditer(metin), 1):
            js = m.group(1)
            # Jinja ifadeleri JS degil: degeri sabitle, blogu at.
            js = _re.sub(r'\{\{.*?\}\}', '0', js, flags=_re.S)
            js = _re.sub(r'\{%.*?%\}', '', js, flags=_re.S)
            if not js.strip():
                continue
            yol = _os.path.join(gec, f'{ad}.{sira}.js')
            _io.open(yol, 'w', encoding='utf-8').write(js)
            r = _sp.run([node, '--check', yol],
                        capture_output=True, text=True)
            if r.returncode != 0:
                ilk = [s for s in r.stderr.split('\n')
                       if 'Error' in s or ':' in s][:3]
                kirik.append(f'{ad} (script #{sira}): ' + ' / '.join(ilk))
    assert not kirik, ('şablon betiği ayrıştırılamıyor — o sayfadaki '
                       'HİÇBİR düğme çalışmaz: ' + '; '.join(kirik))


def test_kd1_betik_bekcisi_kirik_betigi_yakaliyor():
    """Bekçi, bu yamada yaptığım hatanın tam kopyasını görmeli."""
    import os as _os
    import shutil as _shutil
    import subprocess as _sp
    import tempfile as _tf
    node = _shutil.which('node') or _shutil.which('nodejs')
    if not node:
        import pytest as _pytest
        _pytest.skip('node yok')
    # Sablon dizgesinin ICINDE ters tirnak tasiyan bir yorum
    sahte = (
        'function f(x) {\n'
        '  const g = `<div>\n'
        '    <!-- aciklama: `GET /api/bir/sey` yazilmisti -->\n'
        '    <div id="y"></div>`;\n'
        '  return g;\n'
        '}\n')
    p = _os.path.join(_tf.mkdtemp(), 'k.js')
    open(p, 'w', encoding='utf-8').write(sahte)
    r = _sp.run([node, '--check', p], capture_output=True, text=True)
    assert r.returncode != 0, (
        'bekçinin dayandığı `node --check`, şablon dizgesini bölen '
        'ters tırnağı yakalamıyor')
'''),
]

def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA KD1 — KDV TEK KAPI + ÖLÜ KOD + ÜÇ UÇ')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    # ── --yaz-gecici ──
    # base64 gömülü iki dosyayı /tmp'ye çıkarır, PROJEYE DOKUNMAZ.
    # Tam dosya yazan bir yamayı önce okumak istemek yerinde bir
    # istek; "uygula da sonra bak" demek yanlış olurdu.
    if '--yaz-gecici' in sys.argv:
        hedef = tempfile.mkdtemp(prefix='kd1-')
        print()
        for ad in TAM_YAZILAN:
            p = os.path.join(hedef, ad)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(_tam_dosya(ad))
            print(f'  {p}')
        print()
        print('  Projeye DOKUNULMADI. Okuduktan sonra:')
        print('    python3 yama_kd1.py            # rapor')
        print('    python3 yama_kd1.py --uygula')
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
        print('  ⊙ Yama KD1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_kd1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_kd1'
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
    print('    venv/bin/python -m pytest tests/test_kritik.py -q   # 291')
    print()
    print('  SUNUCUYU YENIDEN BASLAT')
    print('    sudo systemctl restart milestone-erp')
    print('    flask_app.py ve iki sablon degisti. Sema degisikligi')
    print('    YOK, goc YOK.')
    print()
    print('  NE DEGISTI')
    print('    · KDV matrahi/KDV ayrimi TEK KAPIDAN geciyor; matrah')
    print('      ile KDV toplandiginda artik her zaman belgenin')
    print('      toplamini veriyor (1.000,35 -> 833,63 + 166,72).')
    print('    · Ayarlar > BAKIM: TRY karsiligi bos kalmis cari')
    print('      hareketleri kur arsivinden toptan doldurur.')
    print('    · Satislar: musteri/cins suzgeci ve cekmecede')
    print('      "bu musteriyle toplamda nereye geldik" bolumu.')
    print('    · 7 olu fonksiyon silindi; 2 yeni bekci eklendi.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

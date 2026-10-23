#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA DZ5 — CARİ HAREKETİN TUTARI DÜZELTİLEBİLİR
================================================

ÖNKOŞUL: yama_dz4.py uygulanmış olmalı.

Sen sordun: "10.000 TL alacak kaydı yapması gerekirken yanlışlıkla
100.000 TL yazıldı ve kaydedildi, bunu düzeltemiyoruz." Haklıydın.

── ÖLÇÜLEN (yamadan önce, senin sistemindeki hâli) ──

  1) TUTAR REDDEDİLİYOR
         PUT {"alacak": 10000}  →  400
         "Bu alanlar buradan değiştirilemez: alacak."

     Beyaz liste borç/alacak/döviz/kuru bilerek dışarıda
     bırakıyordu; yanındaki not "tutar düzeltmesi iptal+yeniden
     giriş ile yapılmalı" diyordu.

  2) `tutar` ADIYLA GÖNDERİNCE SESSİZCE YUTULUYOR
         PUT {"tutar": 10000}   →  200  "Değişiklik yok"
         kayıt: alacak = 100.000 (değişmedi)

     Süzgeç `hasattr(hareket, k)` diye bakıyordu. `tutar`
     CariHareket'te bir alan DEĞİL (alanlar borc/alacak), o yüzden
     ne reddediliyor ne uygulanıyordu. Ekranı naif yazsaydım
     "kaydedildi" diyecek, rakam yerinde duracaktı.

  3) OLMAYAN BİR ALAN "GÜNCELLENDİ" DİYE SAYILIYOR
         PUT {"belge_no": "X"}  →  200 {'guncellenen': ['belge_no']}
         kayıtta duran          →  (alan yok)

     `belge_no` beyaz listedeydi ama o alan CariHareket'te yok —
     Sevkiyat'ın alanı. Bunu formu yazarken buldum: alanı forma
     koydum, tarayıcıda açtım, hareket listesi çöktü.

  4) EKRANDA ZATEN HİÇBİR ŞEY DÜZENLENEMİYOR
     Hareket satırının TEK eylemi `✕` silmekti. Sunucu açıklama,
     evrak no, vade ve tarihi kabul ediyordu ama o PUT'u çağıran
     hiçbir ekran yoktu.

── BUGÜNKÜ TEK YOL VE NEYE MAL OLUYOR ──
  Sil + yeniden gir çalışıyor; kasa bakiyesi de doğru geri
  alınıyor (ölçüldü: 100.000 → 0 → 10.000). Ama denetim kaydında
  "düzeltme" diye bir iz kalmıyor — bir SİLME ve bir YENİ KAYIT
  kalıyor. Hareket bir faturayı kapatmışsa silme kapanışı çözüyor,
  yeniden giriş FIFO'ya başka yerden giriyor.

── 1 · TUTAR DÜZELTİLEBİLİR ──
  Borç/alacak, döviz ve kur artık değiştirilebiliyor. Ekranın
  kullandığı `tutar` adı da tanınıyor; hangi tarafa yazılacağı
  KAYDIN KENDİSİNDEN okunuyor, dışarıdan yön seçilemiyor.

  Tutarın arkasında ne varsa birlikte gidiyor:
    · TRY karşılığı ve uygulanan kur — hareketin KENDİ tarihinden
    · bağlı kasa hareketi ve o kasanın bakiyesi
    · kapattığı hareketler — yeniden açılır
    · eşleşmeden doğan otomatik kur farkı kayıtları — silinir
    · bağlı faturanın tahsilat durumu — yeniden hesaplanır
    · tek satırlık maliyet grubu ve o stoğun birim maliyeti

  Geri alma zincirini YENİDEN YAZMADIM: DELETE'in kullandığı
  `_kur_farki_geri_al` çağrılıyor, kasa çevrimi de POST'un
  kullandığı hesaptan geçiyor — o hesabı `_kasa_tutari`ya taşıdım,
  artık iki çağıran tek fonksiyon. İki kopya zamanla ayrışırdı:
  kasa dövizi farklı bir hareket önce bir kurdan girer, sonra
  başka bir kurdan düzelirdi.

── 2 · KAPSAM ÖNCE SORULUYOR ──
  DZ1'de silme için kurduğumuz kural burada da geçerli:

      "Tutar 100.000,00 → 10.000,00 TRY olacak. Şunlar da
       güncellenecek: MERKEZ TRY kasasının bakiyesi ve hareketi;
       1 kapatılmış hareket yeniden açılacak — eşleştirmeyi tekrar
       yapmanız gerekir; 1 otomatik kur farkı kaydı silinecek."

  Onay verilmezse HİÇBİR ŞEY değişmiyor. Yalnızca tarih ya da
  açıklama değiştiyse bu soru hiç çıkmıyor.

── 3 · EŞLEŞME KENDİLİĞİNDEN YENİLENMİYOR ──
  Kapanışlar çözülüp AÇIK bırakılıyor, yeniden eşleştirmeyi sen
  yapıyorsun. Bir muhasebe kaydını — kur farkını — sessizce
  oluşturmak, oluşturmamaktan daha zararlı; sonradan fark
  edilmesi zor, geri alınması zahmetli. Bu karar EK2'de verilmişti,
  burada da aynısı geçerli. Mesaj kaç kapanışın açıldığını yazıyor.

── 4 · NELER KAPALI KALDI ──
    fatura otomatik borcu → zaten korunuyordu, korunmaya devam
    cari_id              → hareketi başka müşteriye taşır
    kaynak               → nakit akışı sınıflandırması buna bağlı
    kapatildi            → stok silme koruması bunu kullanıyor
    borç ↔ alacak YÖNÜ   → kaydın niteliği değişir; o bir düzeltme
                           değil, başka bir kayıttır
    tutar = 0            → silmenin yerine geçmez; kaydı ekstrede
                           bırakır ama bakiyeye hiç girmez
    çok satırlı maliyet  → net + KDV'ye nasıl bölüşeceği belirsiz;
      grubu                Maliyet ekranından düzeltiliyor (DZ1'den
                           beri o yön doğru çalışıyor)

── 5 · EKRAN ──
  Hareket satırına `✎` geldi. Form tutar, döviz, belge tarihi,
  vade, evrak no ve açıklamayı gösteriyor; 409 kapsamını soruyor.

  İKİ TUZAĞIN KAPAĞI:
    · Açıklama `data-buyuk-harf="hayir"` taşıyor. Genel büyük harf
      kuralı `<input>`lara uygulanıyor; form MEVCUT metni
      gösterdiği için kural açık olsaydı formu sadece AÇMAK
      kullanıcının yazdığı metni büyük harfe çevirirdi.
    · "Belge No" alanı YOK — yukarıdaki (3) yüzünden.

── ÖLÇÜLDÜ (yamadan sonra) ──
      100.000 TRY → 10.000 TRY : kayıt, TRY karşılığı ve kasa ✓
      1.000 USD → 500, TRY kasa: borç_try 40.000 → 20.000,
                                 kasa 40.000 → 20.000 ✓
      kapanış + kur farkı       : borç yeniden açıldı, kur farkı
                                  kaydı silindi, kasa düzeldi ✓
      alacak kaydına borç       : 400, yön kilitli ✓
      tutar = 0                 : 400, silmeye yönlendiriyor ✓
      bilinmeyen alan           : 400, artık yutulmuyor ✓
      belge_no                  : 400, artık "güncellendi" demiyor ✓
      maliyete bağlı borç       : maliyet 2.000 → 500, stok
                                  maliyeti ve cari birlikte ✓
      denetim kaydı             : {"alacak": "100000.0"} →
                                  {"alacak": "10000.0"}  tek satır ✓

  Tarayıcıda açtım: form satırdan doluyor, alt bar panelin içinde
  (taşma 0 piksel), açıklama büyük harfe çevrilmiyor, JS hatası
  yok. Form aralıklarında bir pürüz vardı — `.form-satir` alt
  boşluk taşıyor, çıplak `.form-alan` taşımıyor; iki çıplak alanı
  alt alta koyunca aralarındaki boşluk kapanıyordu. Ev stilinde
  çıplak alan hep tek ve en sonda olduğu için bu hiç görünmemiş.
  İkisini tek `.form-satir` içine aldım.

  200 test geçti (193 + 7 yeni); iki ayrı koşuda da aynı.
  firma · js · form · zincir · akis denetimleri temiz.
  Tabanı DZ4'ü uygulayarak ürettim ve DZ5 testlerinin orada
  DÜŞTÜĞÜNÜ görerek doğruladım. Taban, çalışma kopyamla bayt bayt
  aynı çıktı — DZ4'ten beri dışarıdan bir yazım girmemiş.

── SIRA ──
      DZ1  maliyet ↔ cari hareket            ✓
      DZ2  stok kayıtları                    ✓
      DZ3  satış / proforma / sipariş        ✓
      DZ4  kesim kayıtları                   ✓
      DZ5  cari hareketin tutarı             ← bu yama

DOSYALAR
--------
  flask_app.py         tutar düzeltme · kapsam onayı · kasa
                       çevrimi tek yerde · sessiz yutmalar kapandı
  templates/cari.html  satırda ✎ · düzenleme formu · 409 onayı
  tests/test_kritik.py 7 yeni test

Şema yok, göç yok, yeni alan yok.

KULLANIM
--------
  python3 yama_dz5.py            # RAPOR
  python3 yama_dz5.py --uygula
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
    'flask_app.py': 'DZ5 · TUTAR DÜZELTİLEBİLİR',
    'templates/cari.html': 'function hareketDuzenleAc(',
    'tests/test_kritik.py': 'def test_dz5_cari_hareket_tutari_duzeltilebiliyor',
}
ONKOSUL = {
    'flask_app.py': 'DZ4 · KESİMDEN ÇIKMIŞ ÜRÜNÜN ÖLÇÜSÜ DEĞİŞTİYSE',
    'templates/cari.html': "e.yanit.error === 'onay_gerekli'",
    'tests/test_kritik.py':
        'def test_dz4_plaka_olcusu_degisince_maliyet_yeniden_dagilir',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'DZ5 · flask_app.py blok 1',
     r'''        return acilan, silinen
''',
     r'''        return acilan, silinen

    def _kasa_tutari(kasa, islem_tut, tutar_try, doviz, tarih=None):
        """
        Bir cari hareketin KASA tarafina yazilacak tutar.

        ── NEDEN AYRI FONKSIYON ──
        Bu cevrim yalnizca POST'un icinde, satir ici yaziliydi.
        DZ5 ile tutar DUZELTILEBILIR hale gelince ayni hesap PUT'ta
        da gerekti. Ikinci bir kopya yazmak, kasa dovizi farkli bir
        hareketin once bir kurdan girip sonra baska bir kurdan
        duzelmesi demekti.

        Doner: (kasa_tutari, hata_mesaji). Hata varsa tutar None.
        """
        if kasa.doviz == doviz:
            return q2(islem_tut), None
        if kasa.doviz == 'TRY':
            return q2(tutar_try), None
        k_kur = _kur_getir(kasa.doviz, tarih)
        if not k_kur or k_kur <= 0:
            return None, (f'{kasa.doviz} kuru alınamadı — farklı dövizli '
                          f'kasa için kur gerekli.')
        return q2(tutar_try / k_kur), None

    def _hareket_tutar_kapsami(hareket):
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
'''),
    ('flask_app.py', 'DZ5 · flask_app.py blok 2',
     r'''            if e_kasa.doviz == doviz:
                k_tutar = islem_tut
            elif e_kasa.doviz == 'TRY':
                k_tutar = tutar_try
            else:
                k_kur = _kur_getir(e_kasa.doviz, vade)
                if not k_kur or k_kur <= 0:
                    db.session.rollback()
                    return jsonify({'ok': False,
                        'mesaj': f'{e_kasa.doviz} kuru alınamadı — farklı dövizli kasa için kur gerekli.'}), 400
                k_tutar = q2(tutar_try / k_kur)
''',
     r'''            # DZ5: cevrim `_kasa_tutari`ya tasindi — ayni hesap tutar
            # DUZELTMESINDE de gerekiyor, iki kopya ayrisirdi.
            k_tutar, _k_hata = _kasa_tutari(e_kasa, islem_tut, tutar_try,
                                            doviz, vade)
            if _k_hata:
                db.session.rollback()
                return jsonify({'ok': False, 'mesaj': _k_hata}), 400
'''),
    ('flask_app.py', 'DZ5 · flask_app.py blok 3',
     r'''        # ── BEYAZ LİSTE ──
        # Onceden `for key, val in data.items(): setattr(...)` vardi
        # ve istemciden gelen HER alan yaziliyordu. Olculdu:
        # kaynak, kapatildi, cari_id ve doviz disaridan
        # degistirilebiliyordu.
        #
        # Asagidakiler DISARIDA birakildi, cunku kaydin KIMLIGINI
        # olusturuyorlar:
        #   cari_id  → degisirse hareket baska musteriye tasinir,
        #              D3 degismezligi kirilir
        #   borc/alacak/doviz/kur → tutar duzeltmesi iptal+yeniden
        #              giris ile yapilmali; sessizce degistirilirse
        #              kasa ve fatura ile ayrisir
        #   kaynak   → nakit akisi siniflandirmasi buna bagli;
        #              taninmayan kaynak SESSIZCE yok sayilir (NK5)
        #   kapatildi→ stok silme korumasi ve kur farki hesabi kullanir
        GUNCELLENEBILIR = ('aciklama', 'vade_tarihi', 'evrak_no',
                           'belge_no', 'hareket_tarihi')
        reddedilen = [k for k in data
                      if k not in GUNCELLENEBILIR and hasattr(hareket, k)]
        if reddedilen:
            return jsonify({
                'ok': False,
                'mesaj': f"Bu alanlar buradan değiştirilemez: "
                         f"{', '.join(sorted(reddedilen))}. "
                         f"Değiştirilebilir: {', '.join(GUNCELLENEBILIR)}."}), 400
''',
     r'''        # ══════════════════════════════════════════════════════════
        #  DZ5 · TUTAR DÜZELTİLEBİLİR
        #
        #  Beyaz liste tutarı DIŞARIDA bırakıyordu; yanındaki not
        #  "tutar düzeltmesi iptal+yeniden giriş ile yapılmalı"
        #  diyordu. Ölçüldü: 10.000 TL yerine 100.000 TL girilmiş
        #  bir tahsilatı düzeltmenin hiçbir yolu yoktu. Kaydı silip
        #  yeniden girmek çalışıyor ama denetim kaydında "düzeltme"
        #  diye bir iz bırakmıyor — bir SİLME ve bir YENİ KAYIT
        #  bırakıyor; hareket bir faturayı kapatmışsa FIFO'daki
        #  yeri de değişiyor.
        #
        #  AYRICA SESSİZ YUTMA: süzgeç `hasattr(hareket, k)` diye
        #  bakıyordu. `tutar` CariHareket'te bir alan DEĞİL (alanlar
        #  borc/alacak), dolayısıyla ne reddediliyor ne uygulanıyordu.
        #  Ölçüldü: `PUT {"tutar": 10000}` → 200 "Değişiklik yok",
        #  rakam 100.000'de kalıyor. Ekranı naif yazsaydım
        #  "kaydedildi" diyecekti.
        #
        #  Tutar artık değiştirilebiliyor ve arkasındaki her şey
        #  birlikte gidiyor. Bunlar İŞTEN ÖNCE sorulur (409):
        #    · TRY karşılığı ve uygulanan kur
        #    · bağlı kasa hareketi ve o kasanın bakiyesi
        #    · kapattığı hareketler — yeniden açılır
        #    · eşleşmeden doğan otomatik kur farkı kayıtları
        #    · bağlı faturanın tahsilat durumu
        #    · tek satırlık maliyet grubu ve o stoğun birim maliyeti
        #
        #  Geri alma zincirini YENİDEN YAZMIYORUZ: DELETE'in
        #  kullandığı `_kur_farki_geri_al` çağrılıyor, kasa çevrimi
        #  POST'un kullandığı `_kasa_tutari`dan geçiyor.
        #
        #  EŞLEŞME KENDİLİĞİNDEN YENİLENMEZ: kapanışlar çözülür ve
        #  açık bırakılır. Bir muhasebe kaydını (kur farkı) sessizce
        #  oluşturmak, oluşturmamaktan daha zararlı — EK2'de böyle
        #  karar verilmişti, burada da aynısı geçerli.
        #
        #  KAPALI KALANLAR ve nedeni:
        #    cari_id   → hareketi başka müşteriye taşır, D3
        #                değişmezliği kırılır
        #    kaynak    → nakit akışı sınıflandırması buna bağlı;
        #                tanınmayan kaynak SESSİZCE yok sayılır (NK5)
        #    kapatildi → stok silme koruması ve kur farkı kullanır
        #    borç↔alacak YÖN değişimi → kaydın niteliği değişir; o
        #                bir düzeltme değil, başka bir kayıttır
        # ══════════════════════════════════════════════════════════
        #  BIR SEY DAHA: beyaz listede `belge_no` vardi ama o alan
        #  CariHareket'te YOK — Sevkiyat'in alani. Olculdu:
        #    PUT {"belge_no": "X"} → 200 {'guncellenen': ['belge_no']}
        #    kayitta duran        → (alan yok)
        #  Yani alani GUNCELLENDI diye adiyla sayip hicbir yere
        #  yazmiyordu. Listeden cikarildi; artik reddediliyor.
        GUNCELLENEBILIR = ('aciklama', 'vade_tarihi', 'evrak_no',
                           'hareket_tarihi')
        TUTAR_ALANLARI = ('borc', 'alacak', 'doviz', 'kur_uygulanan')

        # `tutar` EKRANIN kullandigi ad. Hangi tarafa yazilacagi
        # KAYDIN KENDISINDEN okunur; disaridan yon secilemez.
        if 'tutar' in data and not ({'borc', 'alacak'} & set(data)):
            if (hareket.borc or 0) > 0:
                data['borc'] = data.pop('tutar')
            elif (hareket.alacak or 0) > 0:
                data['alacak'] = data.pop('tutar')
            else:
                return jsonify({
                    'ok': False,
                    'mesaj': 'Bu kaydın borç/alacak tarafı belirsiz; tutarı '
                             '"borc" ya da "alacak" adıyla gönderin.'}), 400

        # BILINMEYEN ALAN ARTIK SESSIZCE YUTULMUYOR.
        _taninan = set(GUNCELLENEBILIR) | set(TUTAR_ALANLARI) | {'onay'}
        reddedilen = [k for k in data if k not in _taninan]
        if reddedilen:
            return jsonify({
                'ok': False,
                'mesaj': f"Bu alanlar buradan değiştirilemez: "
                         f"{', '.join(sorted(reddedilen))}. "
                         f"Değiştirilebilir: "
                         f"{', '.join(GUNCELLENEBILIR + TUTAR_ALANLARI)}."}), 400

        # ── TUTAR: DOGRULA, KAPSAMI SOR, SONRA UYGULA ──
        # Hicbir sey bu asamada DEGISMIYOR; plan kuruluyor.
        _plan = None
        if set(TUTAR_ALANLARI) & set(data):
            _borc_kaydi = (hareket.borc or 0) > 0
            if ('borc' in data and not _borc_kaydi) or \
                    ('alacak' in data and _borc_kaydi):
                return jsonify({
                    'ok': False,
                    'mesaj': f'Bu kayıt bir '
                             f'{"borç" if _borc_kaydi else "alacak"} kaydı; '
                             f'yönü buradan değiştirilemez. Yön yanlışsa '
                             f'kaydı silip doğru yönde girin.'}), 400

            _yan = 'borc' if _borc_kaydi else 'alacak'
            _eski_tutar = q2((hareket.borc or 0) + (hareket.alacak or 0))
            _yeni_tutar = _eski_tutar
            if _yan in data:
                try:
                    _yeni_tutar = q2(float(str(data[_yan]).replace(',', '.')))
                except (TypeError, ValueError):
                    return jsonify({'ok': False,
                                    'mesaj': 'Tutar sayı olmalı'}), 400
                if _yeni_tutar <= 0:
                    return jsonify({
                        'ok': False,
                        'mesaj': 'Tutar sıfırdan büyük olmalı. Kaydı tamamen '
                                 'geri almak için SİLİN — sıfır yazmak kaydı '
                                 'ekstrede bırakır ama bakiyeye hiç '
                                 'girmez.'}), 400

            _yeni_doviz = (data.get('doviz') or hareket.doviz or 'TRY')
            _yeni_kur = data.get('kur_uygulanan')
            if _yeni_kur in (None, ''):
                _yeni_kur = None
            else:
                try:
                    _yeni_kur = float(str(_yeni_kur).replace(',', '.'))
                except (TypeError, ValueError):
                    return jsonify({'ok': False,
                                    'mesaj': 'Kur sayı olmalı'}), 400
                if _yeni_kur <= 0:
                    return jsonify({'ok': False,
                                    'mesaj': 'Kur sıfırdan büyük olmalı'}), 400

            _degisti = (_yeni_tutar != _eski_tutar
                        or _yeni_doviz != (hareket.doviz or 'TRY')
                        or (_yeni_kur is not None
                            and q_kur(_yeni_kur)
                            != q_kur(hareket.kur_uygulanan or 0)))
            if _degisti:
                # MALIYET GRUBU: net + KDV gibi COK satirli bir grubun
                # karsiligindaysa tutar buradan BOLUSTURULEMEZ —
                # hangi satira ne kadar gidecegi belirsiz. Maliyet
                # ekrani bu yonu DZ1'den beri dogru yapiyor.
                _maliyet = None
                if (hareket.baglanti_tip == 'maliyet'
                        and hareket.kaynak == 'maliyet'
                        and hareket.baglanti_id):
                    _maliyet = Maliyet.query.get(hareket.baglanti_id)
                    if _maliyet:
                        _grup = _maliyet_grubu(_maliyet)
                        if len(_grup) > 1:
                            return jsonify({
                                'ok': False, 'error': 'maliyet_grubu',
                                'mesaj': f'Bu borç bir faturanın karşılığı '
                                         f'({len(_grup)} maliyet satırı — net '
                                         f'+ KDV). Tutarı Maliyet ekranından '
                                         f'düzeltin; oradan düzeltince '
                                         f'tedarikçi borcu da birlikte '
                                         f'düzelir.'}), 400

                _kapsam = _hareket_tutar_kapsami(hareket)
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
                _plan = {'yan': _yan, 'tutar': _yeni_tutar,
                         'doviz': _yeni_doviz, 'kur': _yeni_kur,
                         'eski_tutar': _eski_tutar, 'maliyet': _maliyet}
'''),
    ('flask_app.py', 'DZ5 · flask_app.py blok 4',
     r'''        if not _eski:
            return jsonify({'ok': True, 'mesaj': 'Değişiklik yok'})
''',
     r'''        if not _eski and not _plan:
            return jsonify({'ok': True, 'mesaj': 'Değişiklik yok'})

        # ── TUTARI UYGULA ──
        _notlar = []
        if _plan:
            # 1) ESKI ESLESMEYI GERI AL — DELETE ile AYNI fonksiyon
            _kf_acilan, _kf_silinen = _kur_farki_geri_al(hareket.id)
            if hareket.kapatildi or hareket.kapanis_hareket_id:
                hareket.kapatildi = False
                hareket.kapanis_hareket_id = None
                _notlar.append('bu hareketin kapanışı geri alındı')

            # 2) YENI TUTAR + TRY KARSILIGI (hareketin KENDI tarihinden)
            _try_tut, _kur_kul = _try_karsilik(
                _plan['tutar'], _plan['doviz'], _plan['kur'],
                hareket.hareket_tarihi)
            if _plan['yan'] == 'borc':
                hareket.borc, hareket.borc_try = _plan['tutar'], _try_tut
                hareket.alacak, hareket.alacak_try = 0, 0
            else:
                hareket.alacak, hareket.alacak_try = _plan['tutar'], _try_tut
                hareket.borc, hareket.borc_try = 0, 0
            hareket.doviz = _plan['doviz']
            hareket.kur_uygulanan = q_kur(_kur_kul)
            _eski[_plan['yan']] = str(_plan['eski_tutar'])

            # 3) KASA — POST ile ayni cevrim
            for _kh in KasaHareket.query.filter_by(
                    baglanti_tip='cari_hareket',
                    baglanti_id=hareket.id).all():
                _k = Kasa.query.get(_kh.kasa_id)
                if not _k:
                    continue
                _yeni_k, _k_hata = _kasa_tutari(
                    _k, _plan['tutar'], _try_tut, _plan['doviz'],
                    hareket.hareket_tarihi)
                if _k_hata:
                    db.session.rollback()
                    return jsonify({'ok': False, 'mesaj': _k_hata}), 400
                _eski_k = q2(_kh.tutar or 0)
                _fark = q2(_yeni_k - _eski_k)
                _k.bakiye = q2((_k.bakiye or 0)
                               + (_fark if _kh.tip == 'giris' else -_fark))
                _kh.tutar = _yeni_k
                _notlar.append(f'{_k.ad} kasası {_eski_k:,.2f} → '
                               f'{_yeni_k:,.2f} {_k.doviz}')

            # 4) TEK SATIRLIK MALIYET GRUBU — stok maliyeti de takip etsin
            if _plan['maliyet'] is not None:
                _m = _plan['maliyet']
                _m.tutar = _plan['tutar']
                _m.doviz = _plan['doviz']
                _m.usd_karsilik = q2(_usd_cevrim(
                    _m.tutar, _m.doviz, getattr(_m, 'maliyet_tarihi', None)))
                _m.guncelleme = datetime.now()
                db.session.flush()
                _sk = _maliyet_etkilenen_stoklari_tazele([_m.baglanti_id])
                _notlar.append(f'{_m.id} maliyet kaydı ve bağlı stok '
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
'''),
    ('flask_app.py', 'DZ5 · flask_app.py blok 5',
     r'''        return jsonify({'ok': True, 'guncellenen': sorted(_eski)})
''',
     r'''        _mesaj = 'Hareket güncellendi'
        if _plan:
            _mesaj = (f'Tutar {_plan["eski_tutar"]:,.2f} → '
                      f'{_plan["tutar"]:,.2f} {_plan["doviz"]} olarak '
                      f'düzeltildi')
        if _notlar:
            _mesaj += '. ' + ', '.join(_notlar)
        return jsonify({'ok': True, 'guncellenen': sorted(_eski),
                        'mesaj': _mesaj})
'''),
    ('templates/cari.html', 'DZ5 · templates/cari.html blok 1',
     r'''  .not{border-radius:var(--r-kucuk);padding:9px 12px;font-size:.8rem;margin-bottom:12px;background:var(--verde-acik);color:var(--verde)}
''',
     r'''  /* DZ5: satirin tek eylemi SILMEK degil artik. Duzenleme ayni
     sessizlikte durur, uzerine gelince kehribar olur — silme
     kirmizi, duzeltme degil. */
  .hduz{border:0;background:transparent;color:var(--cizgi-koyu);font-size:.85rem;cursor:pointer;padding:0 2px}
  .hduz:hover{color:var(--kehribar)}
  .not{border-radius:var(--r-kucuk);padding:9px 12px;font-size:.8rem;margin-bottom:12px;background:var(--verde-acik);color:var(--verde)}
'''),
    ('templates/cari.html', 'DZ5 · templates/cari.html blok 2',
     r'''      <button class="btn-yeni" id="tKaydet" onclick="tahsilatKaydet()">Kaydet</button>
''',
     r'''      <button class="btn-yeni" id="tKaydet" onclick="tahsilatKaydet()">Kaydet</button>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════════════
     DZ5 — HAREKET DÜZENLEME

     Hareket satırının tek eylemi SİLMEK'ti. Yanlış tutarla
     girilmiş bir kaydı düzeltmenin yolu, kaydı silip yeniden
     girmekten geçiyordu; denetim kaydında da "düzeltme" diye bir
     iz kalmıyordu — bir silme ve bir yeni kayıt kalıyordu.

     YÖN ve KASA burada DEĞİŞMEZ. Yön kaydın niteliğidir; kasa
     seçimi para nereye girdiğidir — ikisi de düzeltme değil,
     başka bir kayıttır. Sunucu da ikisini reddediyor.
     ══════════════════════════════════════════════════════════════ -->
<div class="modal-ortu" id="hdModal" onclick="if(event.target===this)hareketDuzenleKapat()">
  <div class="modal" style="width:520px" role="dialog" aria-label="Hareketi düzenle">
    <div class="modal-bas">
      <h3>Hareketi Düzenle</h3>
      <p id="hdAlt">—</p>
    </div>
    <div class="modal-gov">
      <div class="form-satir f2">
        <div class="form-alan">
          <label id="hdTutarEtiket">Tutar</label>
          <input id="hdTutar" type="number" step="0.01" min="0">
        </div>
        <div class="form-alan"><label>Döviz</label>
          <select id="hdDoviz"><option>USD</option><option>EUR</option><option>TRY</option></select>
        </div>
      </div>
      <div class="form-satir f2">
        <div class="form-alan"><label>Belge Tarihi</label><input id="hdTarih" type="date"></div>
        <div class="form-alan"><label>Vade Tarihi</label><input id="hdVade" type="date"></div>
      </div>
      <!-- Burada bir "Belge No" alanı YOK: sunucunun beyaz listesinde
           `belge_no` vardı ama o alan CariHareket'te bulunmuyor
           (Sevkiyat'ın alanı). Ölçüldü — PUT 200 dönüp alanı
           "güncellenen" diye sayıyor, hiçbir yere yazmıyordu. Forma
           koysaydım kullanıcı yazar, "kaydedildi" görür, ertesi gün
           alanı boş bulurdu.

           İKİSİ TEK `.form-satir` İÇİNDE: alt boşluk `.form-satir`da
           duruyor, çıplak `.form-alan`da yok. Yan yana iki çıplak
           alan koyunca aralarındaki boşluk kapanıyor — ölçüldü.
           Ev stilinde çıplak alan hep TEK ve en sonda olduğu için
           bu hiç görünmemiş. -->
      <div class="form-satir">
        <div class="form-alan"><label>Evrak No</label>
          <input id="hdEvrak" placeholder="opsiyonel"></div>
        <!-- Serbest metin: GENEL BÜYÜK HARF KURALI BURADA UYGULANMAZ.
             Form MEVCUT açıklamayı gösteriyor; kural açık olsaydı
             formu sadece AÇMAK kullanıcının yazdığı metni büyük
             harfe çevirirdi. -->
        <div class="form-alan"><label>Açıklama</label>
          <input id="hdAciklama" data-buyuk-harf="hayir" placeholder="opsiyonel"></div>
      </div>
      <div class="not" id="hdNot" style="display:none"></div>
    </div>
    <div class="modal-alt">
      <button class="iptal-btn" onclick="hareketDuzenleKapat()">Vazgeç</button>
      <button class="btn-yeni" id="hdKaydet" onclick="hareketDuzenleKaydet()">Kaydet</button>
'''),
    ('templates/cari.html', 'DZ5 · templates/cari.html blok 3',
     r'''let HAR_ACIK_FATURALAR = [];
''',
     r'''let HAR_ACIK_FATURALAR = [];
/* DZ5: cekmecede gosterilen son hareket listesi. Duzenleme formu
   satiri ID ile buradan okuyor; onclick'e JSON gomseydik tek bir
   kacis hatasi o satirin butonunu bozardi. */
let HAR_SON = [];
'''),
    ('templates/cari.html', 'DZ5 · templates/cari.html blok 4',
     r'''    bakiye = b || {};
''',
     r'''    HAR_SON = hareketler;        // DZ5
    bakiye = b || {};
'''),
    ('templates/cari.html', 'DZ5 · templates/cari.html blok 5',
     r'''          ${yazabilir('cari') ? `<button class="hsil" onclick="hareketSil('${kacar(h.id)}','${kacar(id)}')" title="Hareketi sil">✕</button>` : ''}
''',
     r'''          ${yazabilir('cari') ? `<button class="hduz" onclick="hareketDuzenleAc('${kacar(h.id)}','${kacar(id)}')" title="Hareketi düzenle">✎</button>` : ''}
          ${yazabilir('cari') ? `<button class="hsil" onclick="hareketSil('${kacar(h.id)}','${kacar(id)}')" title="Hareketi sil">✕</button>` : ''}
'''),
    ('templates/cari.html', 'DZ5 · templates/cari.html blok 6',
     r'''async function hareketSil(hareketId, cariId) {
''',
     r'''/* ═══════════════════════════════════════════════════════════════
   DZ5 — HAREKET DÜZENLEME

   Satırın tek eylemi silmekti; yanlış tutarı düzeltmenin yolu
   kaydı silip yeniden girmekten geçiyordu.
   ═══════════════════════════════════════════════════════════════ */
let HD_ID = null, HD_CARI = null;

function hareketDuzenleAc(hareketId, cariId) {
  const h = (HAR_SON || []).find(x => x.id === hareketId);
  if (!h) { bildir('Hareket bulunamadı — çekmeceyi yenile.', true); return; }
  HD_ID = hareketId; HD_CARI = cariId;
  const borcMu = (h.borc || 0) > 0;
  const g = i => document.getElementById(i);
  g('hdAlt').textContent = `${islemEtiket(h.islem_tip)} · ${h.id}`;
  /* Hangi tarafi duzenledigi YAZIYOR: yon buradan degismiyor,
     kullanici neyi degistirdigini bilmeli. */
  g('hdTutarEtiket').textContent = borcMu ? 'Tutar (borç)' : 'Tutar (alacak)';
  g('hdTutar').value   = borcMu ? (h.borc || '') : (h.alacak || '');
  g('hdDoviz').value   = h.doviz || 'TRY';
  g('hdTarih').value   = (h.hareket_tarihi || '').slice(0, 10);
  g('hdVade').value    = (h.vade_tarihi || '').slice(0, 10);
  g('hdEvrak').value   = h.evrak_no || '';
  g('hdAciklama').value = h.aciklama || '';

  /* OTOMATIK KAYITLAR — kullanici Kaydet'e basmadan once bilsin.
     Sunucu bunlari zaten reddediyor ya da zincirle birlikte
     goturuyor; surpriz olmasin. */
  const not = g('hdNot');
  let uyari = '';
  if (h.kaynak === 'fatura' && borcMu) {
    uyari = 'Bu, faturanın otomatik borç kaydı. Tutarı buradan '
          + 'değişmez — faturayı iptal edip yeniden kesmek gerekir.';
  } else if (h.kaynak === 'maliyet') {
    uyari = 'Bu borç bir gider faturasının karşılığı. Tutarı '
          + 'değiştirirsen bağlı maliyet kaydı ve o stoğun birim '
          + 'maliyeti de güncellenir.';
  } else if (h.kaynak === 'otomatik_kur_farki') {
    uyari = 'Bu, eşleşmeden doğan otomatik kur farkı kaydı. Elle '
          + 'düzeltmek yerine ilgili tahsilatı/ödemeyi düzeltmek '
          + 'daha doğru — kur farkı o zaman kendiliğinden gider.';
  } else if (h.kapatildi) {
    uyari = 'Bu hareket kapatılmış. Tutarı değişirse kapanış geri '
          + 'alınır ve eşleştirmeyi tekrar yapman gerekir.';
  }
  not.textContent = uyari;
  not.style.display = uyari ? '' : 'none';

  g('hdModal').classList.add('acik');
  g('hdTutar').focus();
}

function hareketDuzenleKapat() {
  document.getElementById('hdModal').classList.remove('acik');
  HD_ID = null; HD_CARI = null;
}

async function hareketDuzenleKaydet() {
  if (!HD_ID) return;
  const tut = parseFloat(document.getElementById('hdTutar').value);
  if (!(tut > 0)) {
    bildir('Tutar sıfırdan büyük olmalı. Kaydı tamamen geri almak '
         + 'için satırdaki ✕ ile sil.', true);
    return;
  }
  const govde = {
    tutar: tut,
    doviz: document.getElementById('hdDoviz').value,
    hareket_tarihi: document.getElementById('hdTarih').value || null,
    vade_tarihi: document.getElementById('hdVade').value || null,
    evrak_no: document.getElementById('hdEvrak').value,
    aciklama: document.getElementById('hdAciklama').value
  };
  const yol = `/api/cari/hareket/${encodeURIComponent(HD_ID)}`;
  const btn = document.getElementById('hdKaydet');
  const cari = HD_CARI;
  btn.disabled = true; btn.textContent = 'Kaydediliyor…';
  try {
    let d;
    try {
      d = await api(yol, { method: 'PUT', body: JSON.stringify(govde) });
    } catch (e) {
      /* DZ5: tutar degisiyorsa sunucu NE KIMILDAYACAGINI 409 ile
         ONCE soyluyor — kasa bakiyesi, kapanislar, otomatik kur
         farki kayitlari, faturanin tahsilat durumu. Kapsami
         gosterip ikinci kez soruyoruz. Yalnizca tarih ya da
         aciklama degistiyse bu soru HIC cikmiyor. */
      if (e && e.status === 409 && e.yanit && e.yanit.error === 'onay_gerekli') {
        if (!await onayla(e.yanit.mesaj, { tehlike: true })) return;
        d = await api(yol + '?onay=1',
                      { method: 'PUT', body: JSON.stringify(govde) });
      } else { throw e; }
    }
    bildir(d.mesaj || 'Hareket güncellendi');
    hareketDuzenleKapat();
    await yukle();
    if (cari) detayAc(cari);
  } catch (e) { /* api() zaten bildiriyor */ }
  finally { btn.disabled = false; btn.textContent = 'Kaydet'; }
}

async function hareketSil(hareketId, cariId) {
'''),
    ('tests/test_kritik.py', 'DZ5 · tests/test_kritik.py blok 1',
     r'''        assert p.alis_fiyati == 100, 'dokunulmamalıydı'
''',
     r'''        assert p.alis_fiyati == 100, 'dokunulmamalıydı'


# ══════════════════════════════════════════════════════════════════
#  DZ5 · CARİ HAREKETİN TUTARI DÜZELTİLEBİLİR
#
#  Ölçülen: 10.000 TL tahsilat girilecekken 100.000 TL girilmiş bir
#  kaydı düzeltmenin hiçbir yolu yoktu. Beyaz liste borç/alacak/
#  döviz/kuru DIŞARIDA bırakıyordu; yanındaki not "tutar düzeltmesi
#  iptal+yeniden giriş ile yapılmalı" diyordu. O yol çalışıyor ama
#  denetim kaydında düzeltme diye bir iz bırakmıyor — bir SİLME ve
#  bir YENİ KAYIT bırakıyor.
#
#  Ayrıca: süzgeç `hasattr(hareket, k)` idi. `tutar` modelde bir
#  alan DEĞİL, o yüzden ne reddediliyor ne uygulanıyordu —
#  `PUT {"tutar": 10000}` 200 "Değişiklik yok" dönüyordu.
# ══════════════════════════════════════════════════════════════════

def _dz5_kur(c, ek, tutar=100000, doviz='TRY', tip='Tahsilat'):
    """DZ5 kurulumu. HER TESTE KENDİ cari/kasa/hareket kimliği:
    genel sayım yapılırsa başka testlerin bıraktığı satırlar girer
    ve test sırası önemli hale gelir (DZ1'de bir kez yaşandı)."""
    from models import Cari, Kasa
    cid = f'MD5{ek}'
    with fa.app.app_context():
        if not db.session.get(Cari, cid):
            db.session.add(Cari(id=cid, unvan=f'DZ5 {ek}',
                                cari_tip='Müşteri'))
        k = Kasa.query.filter_by(ad=f'DZ5 {ek} KASA').first()
        if not k:
            k = Kasa(ad=f'DZ5 {ek} KASA', doviz=doviz, bakiye=0)
            db.session.add(k)
        db.session.commit()
        kid = k.id
    yan = 'alacak' if tip == 'Tahsilat' else 'borc'
    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': cid, 'islem_tip': tip, 'doviz': doviz,
        'tutar': tutar, yan: tutar, 'kasa_id': kid,
        'hareket_tarihi': '2026-10-01', 'vade_tarihi': '2026-10-01',
        'evrak_no': f'MK-{ek}'})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        h = CariHareket.query.filter_by(cari_id=cid).first()
        return h.id, kid, cid


def test_dz5_cari_hareket_tutari_duzeltilebiliyor():
    """DZ5: tutar düzeltilince TRY karşılığı ve bağlı kasa birlikte
    gidiyor. Eskiden bu PUT 400 dönüyordu: 'Bu alanlar buradan
    değiştirilemez: alacak.'"""
    from models import Kasa
    c = istemci('admin', 'ADMIN')
    hid, kid, _ = _dz5_kur(c, 'A')
    with fa.app.app_context():
        assert float(db.session.get(Kasa, kid).bakiye) == 100000

    r = c.put(f'/api/cari/hareket/{hid}?onay=1', headers=H,
              json={'tutar': 10000})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        h = db.session.get(CariHareket, hid)
        assert float(h.alacak) == 10000, 'tutar düzelmedi'
        assert float(h.alacak_try) == 10000, 'TRY karşılığı takip etmedi'
        assert float(db.session.get(Kasa, kid).bakiye) == 10000, \
            'kasa bakiyesi eski tutarda kaldı'


def test_dz5_tutar_degisimi_once_kapsami_soruyor():
    """DZ5: tutarın arkasında kasa bakiyesi, kapanışlar, kur farkı
    kayıtları ve fatura durumu var. DZ1'de silme için kurulan kural
    burada da geçerli: kapsam ÖNCE söylenir, sonra iş yapılır.

    Onay verilmediyse HİÇBİR ŞEY değişmemeli."""
    from models import Kasa
    c = istemci('admin', 'ADMIN')
    hid, kid, _ = _dz5_kur(c, 'B')

    r = c.put(f'/api/cari/hareket/{hid}', headers=H, json={'tutar': 5000})
    assert r.status_code == 409, r.status_code
    d = r.get_json()
    assert d['error'] == 'onay_gerekli', d
    assert float(d['kapsam']['eski_tutar']) == 100000, d['kapsam']
    assert float(d['kapsam']['yeni_tutar']) == 5000, d['kapsam']
    assert any('kasa' in m for m in d['kapsam']['maddeler']), d['kapsam']

    with fa.app.app_context():
        assert float(db.session.get(CariHareket, hid).alacak) == 100000, \
            'onay verilmeden tutar değişmiş'
        assert float(db.session.get(Kasa, kid).bakiye) == 100000, \
            'onay verilmeden kasa değişmiş'


def test_dz5_bilinmeyen_alan_sessizce_yutulmuyor():
    """DZ5: eski süzgeç yalnız MODELDE OLAN alanları reddediyordu.
    Modelde olmayan bir ad ne reddediliyor ne uygulanıyordu; PUT
    200 ve 'Değişiklik yok' dönüyordu. Ölçüldü. Ekranı naif
    yazsaydım 'kaydedildi' diyecek, rakam yerinde duracaktı."""
    c = istemci('admin', 'ADMIN')
    hid, _, _ = _dz5_kur(c, 'C')
    r = c.put(f'/api/cari/hareket/{hid}', headers=H, json={'tutarr': 5})
    assert r.status_code == 400, r.get_json()
    assert 'tutarr' in r.get_json()['mesaj'], r.get_json()

    # `tutar` ise ARTIK TANINIYOR: ekranın kullandığı ad bu.
    r = c.put(f'/api/cari/hareket/{hid}', headers=H, json={'tutar': 7000})
    assert r.status_code == 409, (r.status_code, r.get_json())


def test_dz5_yon_ve_sifir_tutar_kapali():
    """DZ5: yön kaydın NİTELİĞİ — alacak kaydına borç yazmak
    düzeltme değil, başka bir kayıt. Sıfır da silmenin yerine
    geçmez: kaydı ekstrede bırakır ama bakiyeye hiç girmez."""
    c = istemci('admin', 'ADMIN')
    hid, _, _ = _dz5_kur(c, 'D')

    r = c.put(f'/api/cari/hareket/{hid}?onay=1', headers=H,
              json={'borc': 500})
    assert r.status_code == 400, r.get_json()
    assert 'yön' in r.get_json()['mesaj'], r.get_json()

    r = c.put(f'/api/cari/hareket/{hid}?onay=1', headers=H, json={'tutar': 0})
    assert r.status_code == 400, r.get_json()

    with fa.app.app_context():
        h = db.session.get(CariHareket, hid)
        assert float(h.alacak) == 100000 and float(h.borc or 0) == 0


def test_dz5_tutar_duzeltilince_kapanis_geri_aliniyor():
    """DZ5: tahsilat bir borcu kapatmış ve kur farkı doğmuşsa, tutar
    değişince o eşleşme artık geçersiz. DELETE'in kullandığı
    `_kur_farki_geri_al` burada da çağrılıyor — ikinci bir çözme
    mantığı yazmadık, zamanla ayrışırdı.

    EŞLEŞME KENDİLİĞİNDEN YENİLENMİYOR: kapanışlar açık bırakılıyor.
    Bir muhasebe kaydını (kur farkı) sessizce oluşturmak,
    oluşturmamaktan daha zararlı — EK2'de böyle karar verilmişti."""
    from models import Cari, Kasa
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not db.session.get(Cari, 'MD5E'):
            db.session.add(Cari(id='MD5E', unvan='DZ5 E',
                                cari_tip='Müşteri'))
        if not db.session.get(CariHareket, 'HR-DZ5E'):
            db.session.add(CariHareket(
                id='HR-DZ5E', cari_id='MD5E', cari_unvan='DZ5 E',
                islem_tip='Fatura (Satis)', hareket_tarihi=date(2026, 1, 2),
                vade_tarihi=date(2026, 1, 2), borc=1000, alacak=0,
                borc_try=38000, doviz='USD', kur_uygulanan=38,
                kaynak='manuel', kapatildi=False))
        k = Kasa.query.filter_by(ad='DZ5 E KASA').first()
        if not k:
            k = Kasa(ad='DZ5 E KASA', doviz='USD', bakiye=0)
            db.session.add(k)
        db.session.commit()
        kid = k.id

    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': 'MD5E', 'islem_tip': 'Tahsilat', 'doviz': 'USD',
        'tutar': 1000, 'alacak': 1000, 'kasa_id': kid,
        'hareket_tarihi': date.today().isoformat(),
        'vade_tarihi': date.today().isoformat(),
        'evrak_no': 'MK-E', 'kur_farki_islet': True})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        th = CariHareket.query.filter_by(cari_id='MD5E',
                                         islem_tip='Tahsilat').first()
        tid = th.id
        assert db.session.get(CariHareket, 'HR-DZ5E').kapatildi is True, \
            'kurulum tutmadı: borç kapanmamış'
        kf_once = CariHareket.query.filter_by(
            cari_id='MD5E', kaynak='otomatik_kur_farki').count()
        assert kf_once == 1, f'kurulum tutmadı: {kf_once} kur farkı kaydı'

    r = c.put(f'/api/cari/hareket/{tid}?onay=1', headers=H,
              json={'tutar': 600})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        assert float(db.session.get(CariHareket, tid).alacak) == 600
        eski = db.session.get(CariHareket, 'HR-DZ5E')
        assert not eski.kapatildi, 'kapatılmış borç yeniden açılmadı'
        assert eski.kapanis_hareket_id is None, 'kapanış bağı kaldı'
        assert CariHareket.query.filter_by(
            cari_id='MD5E', kaynak='otomatik_kur_farki').count() == 0, \
            'geçersiz kur farkı kaydı duruyor'
        assert float(db.session.get(Kasa, kid).bakiye) == 600


def test_dz5_hareket_duzenleme_ekrani_var():
    """DZ5: sunucu tarafı tek başına işe yaramaz. Hareket satırının
    TEK eylemi `✕` silmekti; düzenlemeyi çağıran bir ekran yoktu —
    sunucu açıklama/evrak/vade/tarihi kabul ediyordu ama onu
    çağıran hiçbir şey yoktu.

    Yapı testi: düğme, form, 409 onay yolu ve iki sessiz tuzağın
    kapağı yerinde mi."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/cari.html'),
                 encoding='utf-8').read()
    assert 'hareketDuzenleAc(' in m, 'satırda düzenleme düğmesi yok'
    assert 'id="hdModal"' in m, 'düzenleme formu yok'
    assert 'hareketDuzenleKaydet' in m
    assert "e.yanit.error === 'onay_gerekli'" in m.split(
        'async function hareketDuzenleKaydet')[1], \
        'düzenleme yolunda 409 onayı ele alınmıyor'

    # TUZAK 1 — genel büyük harf kuralı `<input>`lara uygulanıyor.
    # Form MEVCUT açıklamayı gösteriyor; kural açık olsaydı formu
    # sadece AÇMAK kullanıcının yazdığı metni büyük harfe çevirirdi.
    i = m.index('id="hdAciklama"')
    assert 'data-buyuk-harf="hayir"' in m[i - 40:i + 200], \
        'açıklama alanı büyük harf kuralına açık kalmış'

    # TUZAK 2 — `belge_no` CariHareket'te YOK (Sevkiyat'ın alanı) ama
    # sunucunun beyaz listesindeydi. Forma koysaydım kullanıcı yazar,
    # "kaydedildi" görür, ertesi gün alanı boş bulurdu.
    assert 'hdBelge' not in m, 'olmayan bir alan forma konmuş'


def test_dz5_olmayan_alan_guncellendi_diye_sayilmiyor():
    """DZ5: beyaz listede `belge_no` vardı ama o alan CariHareket'te
    bulunmuyor — Sevkiyat'ın alanı. Ölçüldü:

        PUT {"belge_no": "X"} → 200 {'guncellenen': ['belge_no']}
        kayıtta duran         → (alan yok)

    Alanı GÜNCELLENDİ diye adıyla sayıp hiçbir yere yazmıyordu.
    Bunu DZ5'in formunu yazarken buldum: alanı forma koymuş,
    tarayıcıda açmış ve listenin çöktüğünü görmüştüm."""
    from models import CariHareket as _CH
    assert 'belge_no' not in [k.name for k in _CH.__table__.columns], \
        'model değişmiş — bu testin gerekçesi kalktı'
    c = istemci('admin', 'ADMIN')
    hid, _, _ = _dz5_kur(c, 'F')
    r = c.put(f'/api/cari/hareket/{hid}', headers=H,
              json={'belge_no': 'DENEME-1'})
    assert r.status_code == 400, (r.status_code, r.get_json())
    assert 'belge_no' in r.get_json()['mesaj'], r.get_json()
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
        print('    python3 yama_dz5.py            # rapor')
        print('    python3 yama_dz5.py --uygula')
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
        print('  ⊙ Yama DZ5 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_dz5.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_dz5'
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
    print('    Cari -> bir musteriyi ac -> SON HAREKETLER.')
    print('    Satirin sagina kalem (duzenle) dugmesi geldi.')
    print('    Yanlis tutarli bir tahsilati ac, tutari degistir:')
    print('    once NE KIMILDAYACAGINI soruyor (kasa bakiyesi,')
    print('    kapanislar, kur farki kayitlari), onay verince')
    print('    hepsi birlikte duzeliyor.')
    print()
    print('    Vazgec dersen HICBIR SEY degismiyor.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

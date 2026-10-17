#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA KF — ÇOKLU FİRMA TÜM KULLANICILARA AÇILIYOR
=================================================

ÖNKOŞUL: MF1–MF7, TZ1 ve RN2/RN3 uygulanmış olmalı (depo 38f79fa).

İstenen üç şey:

  1. Çoklu firma özelliği diğer kullanıcılara da açılsın
  2. Hangi kullanıcının hangi firmaları göreceğine YETKİ PANELİNDEN
     admin karar versin
  3. Varsayılan firma OLMASIN; sistem tamamen seçilen firma ile açılsın
     — tek firma tanımlıysa varsayılan ihtiyacı kendiliğinden kalkıyor

── İKİ KARAR (senin seçimin) ──
  · Firma yetkisi İKİ EKSENLİ: 'seçili firmalar' / 'tüm firmalar'.
    `cari_kapsam` deseninin aynısı. Sebebi: yalnızca açık liste
    tutulsaydı, yeni bir firma açtığında onu görmesi gereken herkesi
    tek tek düzenlemek gerekirdi ve unutulan kullanıcı firmayı hiç
    görmezdi.
  · `varsayilan` bayrağı TAMAMEN kalkıyor, ★ işareti de.

── NEDEN TEK YAMA ──
  Dört aşama var (KF1 şema · KF2 giriş · KF3 yetki paneli · KF4
  denetim) ama tek dosyada geliyorlar, çünkü ARALARINDA DURMAK
  TEHLİKELİ: yalnızca KF1 uygulanırsa modeldeki varsayılan kapsam
  'secili' olur, kimsenin atanmış firması olmaz ve ADMIN OLMAYAN
  HERKES sisteme giremez. Ara durumda bırakmak pazartesi sabahı
  ekibi kapıda bırakmak olurdu.

══ UYGULAMA SIRASI — ÖNEMLİ ══

    python3 yama_kf.py --uygula
    sudo systemctl restart milestone-erp        ← ÖNCE yeniden başlat
    venv/bin/python goc_kf1.py --uygula         ← SONRA göç

  Göç betiği bu yamayla birlikte diske yazılıyor. Sırası neden
  böyle:

    · `kullanici_firma` tablosunu ve `kullanicilar.firma_kapsam`
      sütununu AÇILIŞ kuruyor (db.create_all yeni tabloyu, SD2 yeni
      sütunu). Göç onları kurmuyor.
    · Göç `firma.varsayilan` sütununu DÜŞÜRÜYOR. Yeniden
      başlatılmamış bir sistemde ESKİ KOD hâlâ o sütunu okuyor;
      düşürmek çalışan uygulamayı kırardı.

  Göç yanlış sırada çalıştırılırsa kendisi durur ve sırayı yazar —
  tahmin etmesi gerekmiyor.

══ EN ÖNEMLİ ADIM: KİMSE KİLİTLENMİYOR ══
  Göç MEVCUT KULLANICILARIN HEPSİNE `firma_kapsam='tumu'` veriyor.
  Modeldeki varsayılan 'secili' ve izin tablosu boş; dokunulmazsa
  yükseltmeden sonra admin olmayan hiç kimse giremezdi. Bugün herkes
  tek firmada çalışıyor, 'tumu' bu davranışı AYNEN koruyor.
  Daraltma kararı senin: Ayarlar → Kullanıcılar → firma kapsamını
  "seçili firmalar" yapıp kutuları işaretle.

══ NE DEĞİŞTİ ══

── KF1 · ŞEMA ──
  `kullanici_firma` üyelik tablosu · `Kullanici.firma_kapsam`
  ('secili'|'tumu', varsayılan 'secili' — güvenli taraf).
  `Firma.varsayilan` kaldırıldı; `_varsayilan_firma_id` →
  `_sistem_firma_id` oldu ve artık "varsayılan firma" DEĞİL, yalnızca
  KULLANICISIZ yolların (CLI, göç, test, boş kurulum onarımı) yazma
  çapası — en küçük kimlikli firma.

  `sifirla2.py`: `kullanici_firma` sınıflandırıldı (KORUNUR — yetki
  kaydı, işlem verisi değil; sıfırlama sonrası kimse hiçbir firmaya
  giremezse sebebi ekranda görünmez). `--tumunu-sil` kipinde silinen
  firmaların izin satırları gider.

  `--kalan=` EKLENDİ: bayrak gidince "hangi firma kalacak" kararının
  dayanağı kalmadı. Betik artık SORUYOR; geri alınamaz bir kararı
  kimlik sırasına bırakmıyor.

── KF2 · GİRİŞ AKIŞI ──
  `_kullanici_firma_idleri()`: ADMIN → hepsi (firmaları açan, silen
  ve yetkilendiren o; kendi erişimini kapatması kilitlenmek olurdu),
  kapsam 'tumu' → hepsi, 'secili' → üyelikler. Kapalı firma hiçbir
  listede yok. Ham SQL — süzgecin içinden çağrılıyor, ORM sorgusu
  kancayı yeniden tetikler.

  Giriş: 0 firma → ekran + sebep, içeri girilemez · 1 firma →
  DOĞRUDAN içeri · çok → ekran. Admin tek firmada da ekranı görür,
  çünkü YENİ FİRMA oradan açılıyor.

  Seçim kapısı (`_firma_secim_guard`): seçmeden hiçbir ekran/uç
  çalışmaz. HTML isteği seçim ekranına, API isteği net bir JSON'a
  gider (409 "firma_secilmedi" / 403 "firma_yok") — HTML dönmek
  tarayıcıdaki `api()` yardımcısını anlamsız hataya düşürürdü.

  Firma listesi her yerde İZİNLE süzüldü: seçim ekranı, banner çipi,
  ayarlar paneli. Çip artık admin olmayanda da SEÇİLEBİLİR; eskiden
  `disabled` idi ve iki firması olan muhasebeci geçiş için çıkış
  yapmak zorundaydı.

── KF3 · YETKİ PANELİ ──
  Kullanıcı düzenleme penceresine Firma Kapsamı seçici + firma
  işaret kutuları + duruma göre açıklama. ADMIN'de kutular gizli ve
  sebebi yazılı (gizli alan "neden yok?" sorusu doğurur).
  Liste ucu kapsamı ve üyelikleri döndürüyor; gövdede alan
  GÖNDERİLMEZSE dokunulmuyor — kısmi güncelleme bir kullanıcının
  firma erişimini sessizce kesmemeli.

── KF4 · DENETİM ──
  `firma_denetim.py`'ye F6 ekseni: bu düzen DÖRT SATIRA dayanıyor ve
  dördü de tek kelimeyle, HATA VERMEDEN bozulabilir. Dördü de
  tersten denendi (bozuldu → yakalandı → geri alındı).

  `sifirla2` kozmetik: "38 tablonun hepsi sınıflandırılmış" diyordu;
  `alembic_version` sınıflandırılmış değil, MUAF tutulmuş. Söz
  verdiğim düzeltme.

══ YOL ÜSTÜNDE BULUNAN HATALAR ══

1) SÜZGEÇ TERS ÇALIŞIYORDU  [kendi hatam, en tehlikelisi]
   Çözümleyiciyi "firma seçilmedi" durumunda 0 döndürecek şekilde
   yazdım — fail-closed olsun diye. Ama süzgeçte `if not _f: return`
   yazılıydı: 0 falsy olduğu için süzgeç HİÇ KURULMUYOR ve kullanıcı
   BÜTÜN firmaların verisini görüyordu. Yani emniyet diye koyduğum
   değer tam tersi etki yapıyordu. Süzgeç artık YALNIZCA None'da
   kapanıyor (None = CLI / firma_atla). Aynı tuzak models.py'deki
   damgada da vardı: `if v:` sistem çapasına düşürüyordu.

   F6 bu iki satırı artık denetliyor.

2) FİRMA DEĞİŞTİRMEK 'AYARLAR: YAZMA' İSTİYORDU  [ölçüldü]
   `/api/firma/sec` rol denetiminden kurtuldu ama küresel yazma
   muhafızı yolu `/api/firma/...` görüp 'ayarlar' modülüne sayıyor.
   Sonuç: iki firması olan ama ayar yetkisi olmayan bir satışçı
   firmalar arasında GEÇEMİYORDU — çoklu firmayı kullanıcılara
   açmanın amacı tam olarak buydu. Uç muaf listeye alındı; firma
   AÇMA ve SİLME muaf DEĞİL.

3) BİR KULLANICININ TEK FİRMASI SİLİNEBİLİYORDU
   Silinirse o kullanıcının izin listesi boşalır ve sisteme giremez.
   `_firma_tek_dayanak()` denetimi eklendi: hem silme önizlemesi hem
   silmenin kendisi kimi kilitleyeceğini ADIYLA söylüyor.

4) ÇİP LİSTESİ SÜZÜLMÜYORDU
   `_firma_listesi_ozet` bütün açık firmaları dönüyordu. Çoklu firma
   admin'e özelken sorun değildi; herkese açılınca sızıntı oldu —
   yetkisi olmayan kullanıcı firma ADINI ve BELGE KODUNU çipin
   açılır listesinde görürdü. Geçiş yapamasa bile firma adı bilgidir.

5) F6 VE F3 YORUMLARI SAYIYORDU  [kendi hatam, iki kez]
   F3'ü yazarken 'firma_atla()' geçen her satırı saymıştım; bir kapıyı
   kaldırıp yerine "burada gerekmiyor çünkü…" diye yorum yazınca sayı
   12'den 14'e ÇIKTI. F6'da aynı hatayı tekrarladım: `aktif_firma_id`
   içindeki "eskiden _sistem_firma() dönüyordu" açıklaması, fonksiyon
   hâlâ çapaya düşüyor gibi okundu. İkisi de artık yorumları atıyor.
   Denetim kodu ölçmeli, metni değil.

6) F6 GERÇEK BİR KALINTI BULDU
   `_firma_ortak_liste()` içinde `session.get('firma_id') or
   _sistem_firma()` duruyordu — KF2'de dokuz çağrı yerini
   güncellemişim, bu dokuzuncu gözden kaçmış. Seçim yapılmamışken
   kullanıcının hiç seçmediği firmanın ortak-liste ayarını
   uygulardı.

7) TESTLERDEKİ `istemci()` FİRMA SEÇİMİNİ TAKLİT ETMİYORDU
   Eskiden çalışıyordu çünkü testlerde tek firma vardı ve çözümleyici
   onu kendiliğinden seçiyordu. KF testleri ikinci/üçüncü firmayı
   açınca 5 test 409 aldı. Hata testlerde değil taklidin
   eksikliğindeydi; yardımcı artık kullanıcının izinli ilk firmasını
   seçiyor.

8) FİXTURE KULLANICILARI KİLİTLİYDİ  [ölçüldü]
   KF1'den sonra 5 test düştü, hepsi "firma_yok" yüzünden: fixture
   kullanıcılarının kapsamı 'secili' ve atanmış firması yok. ÜRÜN
   DOĞRU DAVRANIYORDU. Fixture artık göçün gerçekte yaptığını
   taklit ediyor ('tumu'), erişim kuralları ise ayrı testlerde
   sınanıyor. Test içinde doğan üç kullanıcı fixture'ı kaçırıyordu;
   tek tek değil, hepsini taradım.

9) EKLEDİĞİM İKİ GEREKSİZ `firma_atla()`
   F3 ikisini de yakaladı. `firma` tablosu okuma süzgecinin
   kapsamında değil; işe yaramayan her çıkış kapısı o listeyi
   anlamsızlaştırıyor.

══ ÖLÇÜMLER ══
  · 94 test geçti (81 eski + 7 KF2 + 6 KF3 yeni KALICI test)
  · js · form · zincir · akis · sema · firma · degismezlik: temiz
    (`sessiz_denetim` 7 bulgu veriyor — KF'den ÖNCE de aynı 7'ydi,
     push kapısında değil, bu yamayla ilgisi yok)
  · `sifirla2` üç kipi izin satırlarıyla doğrulandı:
      --kalan=2        izin 3 → 1  (silinen firmaların satırı gitti)
      --firma=2        izin 3 → 3  (yalnızca işlem verisi)
      (varsayılan)     izin 3 → 3
  · `goc_kf1.py` yükseltme durumu taklit edilerek koşturuldu:
    4 kullanıcı 'tumu', `varsayilan` düşürüldü, ikinci koşu
    "yapılacak iş yok" dedi
  · F6'nın dört denetimi de tersten sınandı

══ YENİ KALICI TESTLER ══
  test_kf2_firmasiz_kullanici_giremez
  test_kf2_tek_firma_kendiliginden_secilir
  test_kf2_izinsiz_firmaya_gecilemez
  test_kf2_yetkisiz_firmanin_adi_dahi_gorunmez
  test_kf2_kapsam_tumu_yeni_firmayi_da_gorur
  test_kf2_tek_firmasi_olan_kullanici_kilitlenmez
  test_kf2_secim_yapilmadan_suzgec_kapanmaz
  test_kf3_yetki_paneli_firma_atar
  test_kf3_liste_ucu_kapsam_ve_uyelik_donduruyor
  test_kf3_kismi_guncelleme_izinleri_silmez
  test_kf3_gecersiz_kapsam_guvenli_tarafa_duser
  test_kf3_olmayan_firma_atanamaz
  test_kf3_formda_firma_kapsami_var

DOSYALAR
--------
  models.py                 şema + damga
  flask_app.py              çözümleyici, kapı, giriş, uçlar
  templates/firma_sec.html  izinli liste, admin ayrımı, sebep
  templates/base.html       çip herkeste seçilebilir
  templates/ayarlar.html    yetki paneli firma kapsamı
  sifirla2.py               kullanici_firma + --kalan= + sayı
  firma_denetim.py          F6 ekseni + F3/F6 yorum düzeltmesi
  tests/test_kritik.py      fixture + istemci() + 13 yeni test
  goc_kf1.py                YENİ — göç betiği

KULLANIM
--------
  python3 yama_kf.py                  # RAPOR
  python3 yama_kf.py --yaz-gecici     # goc_kf1.py'yi /tmp'ye yaz, oku
  python3 yama_kf.py --uygula
  sudo systemctl restart milestone-erp
  venv/bin/python goc_kf1.py          # RAPOR
  venv/bin/python goc_kf1.py --uygula

  Sonra tarayıcıda Ctrl+F5 (yetki penceresi şablonu önbellekte
  kalmasın) ve Ayarlar → Kullanıcılar'dan kapsamları daralt.
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

# ── İMZA ──
# Her dosyada TAM ve AYIRT EDİCİ bir dize. Bu projede alt dizgi
# tuzağına üç kez düştüm ('MF2' imzası MF1'in docstring'inde MF2'den
# söz edildiği için eşleşmişti). İmza, yamanın GERÇEKTEN eklediği
# benzersiz satır.
DOSYA_IMZA = {
    'models.py': 'class KullaniciFirma',
    'flask_app.py': '_kullanici_firma_idleri',
    'templates/firma_sec.html': 'KF2: yeni firma açmak admin işi',
    'templates/base.html': 'KF2: çip artık HERKESTE seçilebilir',
    'templates/ayarlar.html': 'FİRMA KAPSAMI (KF3)',
    'sifirla2.py': "'kullanici_firma':",
    'firma_denetim.py': 'F6 · ERİŞİM ÇÖZÜMLEYİCİSİ',
    'tests/test_kritik.py': 'def test_kf2_firmasiz_kullanici_giremez',
    'goc_kf1.py': 'KULLANICI↔FİRMA GÖÇÜ',
}
ONKOSUL = {
    # MF1 şeması olmadan bu yamanın anlamı yok.
    'models.py': 'class CariFirma',
    # RN3 uygulanmış olmalı (belge kodu düzenlenebilir).
    'flask_app.py': 'RN3 · BELGE KODU',
    'templates/firma_sec.html': 'firmaSil(',
    'templates/base.html': 'firma-cip',
    'templates/ayarlar.html': 'uKapsam',
    # TZ1 ile gelen R5 sürümü.
    'sifirla2.py': 'R5: çoklu firma',
    # TZ1 + F5.
    'firma_denetim.py': 'F5 · KİMLİK SAYAÇLARI',
    'tests/test_kritik.py': 'def istemci(',
}

# goc_kf1.py PARÇA değil TAM DOSYA — base64 taşınıyor.
TAM_YAZILAN = ['goc_kf1.py']

DEGISIKLIKLER = [
    ('models.py', 'KF · models.py blok 1',
     r'''    ortak_liste   = db.Column(db.Boolean, default=True)
    varsayilan    = db.Column(db.Boolean, default=False, index=True)
''',
     r'''    ortak_liste   = db.Column(db.Boolean, default=True)
    # ── KF1: `varsayilan` KALDIRILDI ──
    # Çoklu firma artık tüm kullanıcılara açık ve her kullanıcı kendi
    # izinli firmalarından BİRİNİ SEÇEREK giriyor. Küresel bir
    # "varsayılan firma" bu düzende yalnızca zarar verir: seçim
    # ekranını atlatıp kullanıcıyı sessizce bir firmaya düşürür ve
    # "ben hangi firmadayım?" sorusunu ekranda cevapsız bırakır.
    #
    # Kullanıcısız yollar (CLI betikleri, boş kurulumun kendini
    # onarması) yine bir çapaya ihtiyaç duyuyor; o çapa artık bir
    # bayrak değil, EN KÜÇÜK KİMLİKLİ AKTİF FİRMA — bkz.
    # _sistem_firma_id(). Bayrak kimsenin bilinçli olarak
    # ayarlamadığı bir alandı; kimlik sırası en azından belirli.
    #
    # Sütun göçle DÜŞÜRÜLÜYOR (goc_kf1.py): modelde olmayıp
    # veritabanında kalan sütun, `kisaltma` tuzağının aynısı olurdu —
    # sema_denetim FAZLA sütunu görmüyor, yalnızca eksiği görüyor.
'''),
    ('models.py', 'KF · models.py blok 2',
     r'''                                          name='uq_cari_firma'),)
''',
     r'''                                          name='uq_cari_firma'),)


class KullaniciFirma(db.Model):
    """Hangi kullanıcı HANGİ FİRMADA çalışabilir (KF1).

    Çoklu firma artık admin'e özel değil. Kimin hangi firmayı
    göreceğine yönetici karar veriyor ve kararın yaşadığı yer bu
    tablo.

    `Kullanici.firma_kapsam` ile birlikte okunur:

        'tumu'   → bu tablo DİKKATE ALINMAZ, bütün firmalar
        'secili' → YALNIZCA burada yazılı firmalar

    Satır YOKSA ve kapsam 'secili' ise kullanıcı hiçbir firmada
    çalışamaz ve sisteme giremez. Bu bilinçli: firmasız bir
    kullanıcıyı sessizce bir firmaya düşürmek, yöneticinin
    vermediği bir yetkiyi vermek olurdu. Giriş ekranı o kullanıcıya
    ne olduğunu açıkça söylüyor (KF2).

    ADMIN rolü bu tablodan bağımsız olarak HER firmayı görür:
    firmaları açan, silen ve yetkilendiren o. Kendi erişimini
    kazara kapatabilmesi, sistemden kilitlenmesi demek olurdu.
    """
    __tablename__ = 'kullanici_firma'
    id           = db.Column(db.Integer, primary_key=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'),
                             nullable=False, index=True)
    firma_id     = db.Column(db.Integer, db.ForeignKey('firma.id'),
                             nullable=False, index=True)
    olusturma    = db.Column(db.DateTime, default=datetime.now)
    __table_args__ = (db.UniqueConstraint('kullanici_id', 'firma_id',
                                          name='uq_kullanici_firma'),)
'''),
    ('models.py', 'KF · models.py blok 3',
     r'''    cari_kapsam = db.Column(db.String(10), default='atanan')
''',
     r'''    cari_kapsam = db.Column(db.String(10), default='atanan')
    # ── FİRMA KAPSAMI (KF1) ──
    # `cari_kapsam` ile AYNI iki eksenli desen:
    #
    #   'secili' → yalnızca `kullanici_firma` ile atanmış firmalar
    #   'tumu'   → bütün firmalar (muhasebe, yönetim)
    #
    # 'tumu' olanlar YENİ AÇILAN firmayı da kendiliğinden görür.
    # Yalnızca açık liste tutulsaydı, her yeni firmada o firmayı
    # görmesi gereken herkesi tek tek düzenlemek gerekirdi ve
    # unutulan kullanıcı firmayı hiç görmezdi.
    #
    # Varsayılan 'secili' — güvenli taraf. Eksik değer "herkes her
    # firmayı görsün" anlamına GELMEMELİ. Göç mevcut kullanıcıları
    # bilerek 'tumu' yapıyor (goc_kf1.py): yükseltme kimsenin
    # erişimini sessizce kesmemeli, daraltma kararı yöneticinin.
    firma_kapsam = db.Column(db.String(10), default='secili')
'''),
    ('models.py', 'KF · models.py blok 4',
     r'''_firma_cozucu = None               # MF2/MF3: oturumdaki aktif firmayı verir
_varsayilan_firma_onbellek = None
''',
     r'''_firma_cozucu = None               # MF2/MF3: oturumdaki aktif firmayı verir
_sistem_firma_onbellek = None      # KF1: kullanıcısız yolların çapası
'''),
    ('models.py', 'KF · models.py blok 5',
     r'''
def varsayilan_firma_unut():
''',
     r'''
def sistem_firma_unut():
'''),
    ('models.py', 'KF · models.py blok 6',
     r'''    """Firma kaydı eklenip değişince önbelleği düşürür."""
    global _varsayilan_firma_onbellek
    _varsayilan_firma_onbellek = None
''',
     r'''    """Firma kaydı eklenip değişince önbelleği düşürür."""
    global _sistem_firma_onbellek
    _sistem_firma_onbellek = None
'''),
    ('models.py', 'KF · models.py blok 7',
     r'''
def _varsayilan_firma_id():
    """Varsayılan firmanın kimliği.
''',
     r'''
def _sistem_firma_id():
    """KULLANICISIZ yollarda yazma damgasının bastığı firma (KF1).

    BU BİR "VARSAYILAN FİRMA" DEĞİL. Ekranda hiçbir kullanıcı buraya
    düşmez; giriş akışı herkesi kendi izinli firmalarından seçim
    yapmaya zorluyor (KF2). Buranın tek işi, OTURUM OLMAYAN yollarda
    yazılan kaydın bir firmaya damgalanabilmesi: CLI betikleri,
    göçler, testler ve taze kurulumun kendini onarması.

    KF1'den önce `firma.varsayilan` bayrağına bakılıyordu. Bayrak
    kaldırıldı: kimsenin bilinçli ayarlamadığı bir alandı ve giriş
    akışında kullanıcıyı sessizce bir firmaya düşürüyordu. Yerine EN
    KÜÇÜK KİMLİKLİ firma alınıyor — belirli ve açıklanabilir.
'''),
    ('models.py', 'KF · models.py blok 8',
     r'''    oturuma yeniden girmek demek olurdu.

    `ORDER BY varsayilan DESC` iki lehçede de çalışır (PostgreSQL'de
    TRUE, SQLite'ta 1 önce gelir); `WHERE varsayilan = 1` SQLite'a,
    `WHERE varsayilan` PostgreSQL'e özgü olurdu.
''',
     r'''    oturuma yeniden girmek demek olurdu.
'''),
    ('models.py', 'KF · models.py blok 9',
     r'''    """
    global _varsayilan_firma_onbellek
    if _varsayilan_firma_onbellek is not None:
        return _varsayilan_firma_onbellek
''',
     r'''    """
    global _sistem_firma_onbellek
    if _sistem_firma_onbellek is not None:
        return _sistem_firma_onbellek
'''),
    ('models.py', 'KF · models.py blok 10',
     r'''            r = b.execute(_text(
                'SELECT id FROM firma ORDER BY varsayilan DESC, id '
                'LIMIT 1')).fetchone()
''',
     r'''            r = b.execute(_text(
                'SELECT id FROM firma ORDER BY id LIMIT 1')).fetchone()
'''),
    ('models.py', 'KF · models.py blok 11',
     r'''                b.execute(_text(
                    'INSERT INTO firma (ad, unvan, varsayilan, aktif, sira)'
                    " VALUES ('ANA FİRMA', 'ANA FİRMA', :e, :e, 0)"),
''',
     r'''                b.execute(_text(
                    'INSERT INTO firma (ad, unvan, aktif, sira)'
                    " VALUES ('ANA FİRMA', 'ANA FİRMA', :e, 0)"),
'''),
    ('models.py', 'KF · models.py blok 12',
     r'''        return None                # firma tablosu henüz yok (göç öncesi)
    _varsayilan_firma_onbellek = r[0] if r else None
    return _varsayilan_firma_onbellek
''',
     r'''        return None                # firma tablosu henüz yok (göç öncesi)
    _sistem_firma_onbellek = r[0] if r else None
    return _sistem_firma_onbellek
'''),
    ('models.py', 'KF · models.py blok 13',
     r'''            v = None
        if v:
''',
     r'''            v = None
        # KF2: `if v:` yazılıydı. Çözümleyici "firma seçilmedi"
        # durumunda 0 dönüyor ve 0 falsy olduğu için eski satır
        # SİSTEM ÇAPASINA düşerdi — yani seçim yapmamış bir
        # kullanıcının yazdığı kayıt rastgele bir firmaya
        # damgalanırdı. 0 bir BİLGİ taşıyor, onu yukarı geçiriyoruz;
        # damga aşağıda açıkça reddediyor.
        if v is not None:
'''),
    ('models.py', 'KF · models.py blok 14',
     r'''            return v
    return _varsayilan_firma_id()
''',
     r'''            return v
    return _sistem_firma_id()
'''),
    ('models.py', 'KF · models.py blok 15',
     r'''                'goc_mf1.py çalıştırıldı mı?')
''',
     r'''                'goc_mf1.py çalıştırıldı mı?')
        if not fid:
            # KF2: 0 = "oturumda firma SEÇİLMEDİ ya da seçilen firma
            # artık izinli değil". Bu sayıyı damgalamak yabancı
            # anahtarı kırardı; sistem çapasına düşmek ise kaydı
            # rastgele bir firmaya yazmak olurdu — ikisi de yanlış.
            # Kullanıcı seçim yapmadan yazma yolu açılmamalı; buraya
            # düşülüyorsa bir uç `_firma_secim_guard`'ın dışında
            # kalmış demektir ve bunu sessizce geçmek istemiyorum.
            if isinstance(n, AuditLog):
                continue
            raise RuntimeError(
                'Firma seçilmedi — kayıt yazılamaz. Çıkış yapıp '
                'yeniden girerek firma seçin.')
'''),
    ('models.py', 'KF · models.py blok 16',
     r'''    fid = aktif_firma_id()
    if fid is None:
''',
     r'''    fid = aktif_firma_id()
    # KF2: `is None` değil `not` — 0 da (firma seçilmedi) geçmemeli;
    # firma_id=0 ile üyelik yazmak yabancı anahtarı kırardı.
    if not fid:
'''),
    ('flask_app.py', 'KF · flask_app.py blok 1',
     r'''        '/api/yetkilerim',
''',
     r'''        '/api/yetkilerim',
        # ── KF2 · FİRMA DEĞİŞTİRME AYAR DEĞİL, GEZİNMEDİR ──
        # ÖLÇÜLDÜ: bu satır olmadan `/api/firma/sec` 403 veriyordu —
        # yol `/api/firma/...` olduğu için yazma muhafızı onu
        # 'ayarlar' modülüne sayıyor ve 'ayarlar: yazma' arıyor.
        # Sonuç: iki firması olan ama ayar yetkisi olmayan bir
        # satışçı firmalar arasında GEÇEMİYORDU. Çoklu firmayı
        # kullanıcılara açmanın amacı tam olarak buydu; rol
        # denetimini kaldırıp yerine yetki duvarı bırakmak
        # özelliği kâğıt üstünde açmak olurdu.
        #
        # Yetkisizlik riski yok: uç kendi İZİN denetimini yapıyor
        # (istenen firma kullanıcının listesinde değilse 403) ve
        # hiçbir veriyi değiştirmiyor — yalnızca oturumdaki seçimi
        # taşıyor. Firma AÇMA (`POST /api/firma`) ve SİLME
        # (`DELETE /api/firma/<id>`) muaf DEĞİL; onlar admin şartı
        # arayan ayrı uçlar.
        '/api/firma/sec',
'''),
    ('flask_app.py', 'KF · flask_app.py blok 2',
     r'''    def _firma_listesi_ozet():
        """Aktif firmaların kısa listesi — banner ve ayarlar için."""
''',
     r'''    def _firma_listesi_ozet():
        """Kullanıcının İZİNLİ firmaları — banner çipi ve ayarlar için.

        KF2: burada süzgeç YOKTU ve bütün açık firmalar dönüyordu.
        Çoklu firma admin'e özelken sorun değildi; herkese açılınca
        sızıntı oldu — admin olmayan bir kullanıcı, yetkisi olmayan
        firmaların ADINI ve BELGE KODUNU çipin açılır listesinde
        görürdü. Geçiş yapamasa bile (uç 403 veriyor) firma adı tek
        başına bilgidir: kaç şirket var, adları ne.

        `firma_atla()` DURUYOR: firma tablosu okuma süzgecinin
        kapsamında değil ama çağıran yerlerden biri süzgeç içinden
        geliyor; MF3'ten beri böyle ve dokunmak için sebep yok.
        Süzmeyi ORM koşulu yapıyor, süzgeç kancası değil.
        """
'''),
    ('flask_app.py', 'KF · flask_app.py blok 3',
     r'''        try:
            with firma_atla():          # firma listesi SÜZÜLMEZ
                for f in (Firma.query.filter_by(aktif=True)
''',
     r'''        try:
            _izinli = _kullanici_firma_idleri()
            with firma_atla():
                for f in (Firma.query
                          .filter(Firma.aktif.is_(True),
                                  Firma.id.in_(_izinli or [0]))
'''),
    ('flask_app.py', 'KF · flask_app.py blok 4',
     r'''                threading.Thread(target=yedek_modul.yedek_al, args=('auto',), daemon=True).start()
                # ── MF3B/MF3C · GİRİŞTE FİRMA SEÇİMİ ──
                # Admin önce hangi firmada çalışacağını seçer
                # (Logo/Mikro/Netsis'teki yerleşik akış).
''',
     r'''                threading.Thread(target=yedek_modul.yedek_al, args=('auto',), daemon=True).start()
                # ── KF2 · GİRİŞTE FİRMA SEÇİMİ (HERKESE) ──
                # Çoklu firma artık admin'e özel değil. Giriş akışı
                # kullanıcının İZİNLİ firma sayısına göre ayrışıyor:
'''),
    ('flask_app.py', 'KF · flask_app.py blok 5',
     r'''                #
                # MF3C: eskiden ekran yalnızca İKİ ve daha çok firma
                # varken çıkıyordu. Oysa yeni firmayı BİR FİRMANIN
                # İÇİNE GİRMEDEN açabilmek gerekiyor — tek firma
                # varken de. Artık koşulsuz.
''',
     r'''                #
                #   0 firma  → seçim ekranı, sebebini yazar, içeri
                #              girilemez. Sessizce bir firmaya
                #              atamak yöneticinin vermediği yetkiyi
                #              vermek olurdu.
                #   1 firma  → DOĞRUDAN içeri. Seçtirecek bir şey
                #              yok; istenen de buydu — tek firma
                #              varsa varsayılan ihtiyacı kalmıyor.
                #              (Admin bu kuralın dışında: tek firma
                #              olsa da ekranı görür, çünkü YENİ
                #              FİRMA oradan açılıyor ve bunu bir
                #              firmanın içine girmeden yapabilmek
                #              gerekiyor — MF3C.)
                #   çok      → seçim ekranı.
'''),
    ('flask_app.py', 'KF · flask_app.py blok 6',
     r'''                #
                # Admin OLMAYAN kullanıcı ekranı görmez: firma seçimi
                # şimdilik admin yetkisinde, onlar varsayılan firmaya
                # girer.
''',
     r'''                #
                # Önceki seçim HER GİRİŞTE silinir: "tamamen seçilen
                # firma ile açılsın" denmişti; eski oturumdan kalan
                # kimlik sessizce devralınmamalı.
'''),
    ('flask_app.py', 'KF · flask_app.py blok 7',
     r'''                try:
                    if (k.rol or '').upper() == 'ADMIN':
                        session.pop('firma_id', None)
''',
     r'''                try:
                    session.pop('firma_id', None)
                    session.pop('firma_hata', None)
                    _n = len(_kullanici_firma_idleri())
                    if _n != 1 or (k.rol or '').upper() == 'ADMIN':
'''),
    ('flask_app.py', 'KF · flask_app.py blok 8',
     r'''                except Exception as _e:
                    app.logger.warning(f'[MF3B] firma secim ekrani atlandi: {_e}')
''',
     r'''                except Exception as _e:
                    app.logger.warning(f'[KF2] firma secim ekrani atlandi: {_e}')
                    return redirect(url_for('firma_sec_ekran'))
'''),
    ('flask_app.py', 'KF · flask_app.py blok 9',
     r'''            return _auth_required()
        # Firma seçimi şimdilik admin yetkisinde; diğerleri varsayılan
        # firmada çalışır ve bu ekranı hiç görmez.
        if (session.get('rol') or '').upper() != 'ADMIN':
            return redirect(url_for('dashboard'))
''',
     r'''            return _auth_required()
        # ── KF2 · EKRAN HERKESE AÇIK, LİSTE KİŞİYE ÖZEL ──
        # Eskiden admin olmayan buradan dashboard'a çevriliyordu.
        # Artık herkes kendi izinli firmalarını görüyor; liste
        # `_kullanici_firma_idleri()` ile süzülüyor, yani kimse
        # yetkisi olmayan bir firmanın ADINI dahi görmüyor.
        _admin = (session.get('rol') or '').upper() == 'ADMIN'
        _izinli = _kullanici_firma_idleri()
'''),
    ('flask_app.py', 'KF · flask_app.py blok 10',
     r'''        with firma_atla():
            kayitlar = (Firma.query.filter_by(aktif=True)
''',
     r'''        with firma_atla():
            kayitlar = (Firma.query.filter(Firma.aktif.is_(True),
                                           Firma.id.in_(_izinli or [0]))
'''),
    ('flask_app.py', 'KF · flask_app.py blok 11',
     r'''                        .order_by(Firma.sira, Firma.id).all())
        # MF3C: tek firma varken de açılır. Ekranın işi yalnızca
        # seçtirmek değil; YENİ FİRMA buradan açılıyor ve bunu bir
        # firmanın içine girmeden yapabilmek gerekiyor. Hiç firma
        # yoksa da sorun değil: liste boş gelir, "yeni firma ekle"
        # durur.
''',
     r'''                        .order_by(Firma.sira, Firma.id).all())
        # MF3C: admin'de tek firma varken de açılır — ekranın işi
        # yalnızca seçtirmek değil, YENİ FİRMA buradan açılıyor ve
        # bunu bir firmanın içine girmeden yapabilmek gerekiyor.
        #
        # KF2: admin OLMAYAN ve tek firması olan kullanıcı buraya hiç
        # gelmiyor (giriş akışı doğrudan içeri alıyor). Yine de adres
        # çubuğundan gelirse ekran açılır ve tek kartını gösterir.
        _hata = session.pop('firma_hata', None)
'''),
    ('flask_app.py', 'KF · flask_app.py blok 12',
     r'''            'kod': f.belge_kodu or '', 'vergi_no': f.vergi_no or '',
            'varsayilan': bool(f.varsayilan),
        } for f in kayitlar], secili=session.get('firma_id'))
''',
     r'''            'kod': f.belge_kodu or '', 'vergi_no': f.vergi_no or '',
        } for f in kayitlar], secili=session.get('firma_id'),
            admin=_admin, hata=_hata)
'''),
    ('flask_app.py', 'KF · flask_app.py blok 13',
     r'''                        firma_cozucu_ayarla as _firma_cozucu_ayarla,
                        _varsayilan_firma_id as _varsayilan_firma)
''',
     r'''                        firma_cozucu_ayarla as _firma_cozucu_ayarla,
                        _sistem_firma_id as _sistem_firma)
'''),
    ('flask_app.py', 'KF · flask_app.py blok 14',
     r'''            g.firma_atla_bayrak = onceki

''',
     r'''            g.firma_atla_bayrak = onceki

    def _kullanici_firma_idleri():
        """Oturumdaki kullanıcının ÇALIŞABİLECEĞİ firma kimlikleri (KF1).

        Üç kaynak, bu sırayla:

          ADMIN            → bütün AÇIK firmalar. Firmaları açan,
                             silen ve yetkilendiren o; kendi erişimini
                             kazara kapatması sistemden kilitlenmesi
                             demek olurdu.
          kapsam 'tumu'    → bütün AÇIK firmalar (muhasebe, yönetim).
                             Yeni açılan firmayı da kendiliğinden görür.
          kapsam 'secili'  → yalnızca `kullanici_firma` satırları.

        KAPALI firma hiçbir listede yok: seçilemeyen bir firmaya
        düşmek, girilemeyen bir sistem demek.

        HAM SQL — ZORUNLU. Bu işlev okuma süzgecinin içinden
        çağrılıyor; ORM sorgusu açmak `do_orm_execute` kancasını
        yeniden tetikler ve sonsuz döngü olur (CRM-C2'de ölçülmüştü).

        Sonuç istek başına `g`'de saklanır: kanca her sorguda
        çalışıyor, her birinde iki sorgu açmak pahalı olurdu.
        """
        if not has_request_context():
            return []
        _o = getattr(g, '_kf1_firmalar', None)
        if _o is not None:
            return _o
        _sonuc = []
        try:
            _rol = (session.get('rol') or '').upper()
            _ad = session.get('kullanici')
            _hepsi = ('SELECT id FROM firma WHERE aktif = :e '
                      'ORDER BY sira, id')
            with db.engine.connect() as _b:
                if _rol == 'ADMIN':
                    _sonuc = [r[0] for r in _b.execute(
                        sa_text(_hepsi), {'e': True}).fetchall()]
                elif _ad:
                    _k = _b.execute(sa_text(
                        'SELECT id, firma_kapsam FROM kullanicilar '
                        'WHERE ad = :a'), {'a': _ad}).fetchone()
                    if _k:
                        if (_k[1] or 'secili') == 'tumu':
                            _sonuc = [r[0] for r in _b.execute(
                                sa_text(_hepsi), {'e': True}).fetchall()]
                        else:
                            _sonuc = [r[0] for r in _b.execute(sa_text(
                                'SELECT f.id FROM firma f '
                                'JOIN kullanici_firma kf ON kf.firma_id = f.id '
                                'WHERE kf.kullanici_id = :k AND f.aktif = :e '
                                'ORDER BY f.sira, f.id'),
                                {'k': _k[0], 'e': True}).fetchall()]
        except Exception as _e:
            # Göç öncesi (tablo/sütun yok) ya da beklenmedik hata:
            # BOŞ dönüyoruz, yani hiçbir firma. Fail-closed; dolu
            # dönmek yetkisiz erişim açardı.
            app.logger.warning(f'[KF1] firma izinleri okunamadi: {_e}')
            _sonuc = []
        g._kf1_firmalar = _sonuc
        return _sonuc

'''),
    ('flask_app.py', 'KF · flask_app.py blok 15',
     r'''        _onbellek = getattr(g, '_mf2_firma', None)
        if _onbellek is not None:
            return _onbellek
''',
     r'''        _onbellek = getattr(g, '_mf2_firma', None)
        if _onbellek is not None:
            return _onbellek
        # ══ KF2 · KÜRESEL VARSAYILANA DÜŞMEK YOK ══
        #
        # Eskiden seçim yoksa `_sistem_firma()` dönüyordu: kullanıcı
        # sessizce bir firmaya düşerdi ve "ben hangi firmadayım?"
        # sorusu ekranda cevapsız kalırdı. Varsayılan firma kavramı
        # kaldırıldı; artık yalnızca İZİNLİ firmalar konuşuyor.
        #
        # Dört durum var ve dördü de kapalı uçlu:
        _izinli = _kullanici_firma_idleri()
'''),
    ('flask_app.py', 'KF · flask_app.py blok 16',
     r'''        _f = session.get('firma_id')
        if not _f:
            # Firma seçici MF3'te geliyor; o zamana kadar (ve seçim
            # yapılmamışsa) varsayılan firma. HAM SQL okur, ORM değil
            # — ORM sorgusu bu kancayı yeniden tetiklerdi.
            _f = _varsayilan_firma()
''',
     r'''        _f = session.get('firma_id')

        if _f and _f in _izinli:
            pass                        # 1 · seçili ve hâlâ izinli

        elif len(_izinli) == 1:
            # 2 · TEK FİRMA → seçtirecek bir şey yok, kendiliğinden
            # girer. İstenen de buydu: "kullanıcıya sadece tek firma
            # tanımlanmışsa varsayılan ihtiyacı ortadan kalkıyor."
            _f = _izinli[0]
            session['firma_id'] = _f

        else:
            # 3 · hiç izinli firma yok   ·   4 · çok firma var ama
            # seçilmemiş (ya da oturumdaki seçim artık izinli değil —
            # yönetici yetkiyi geri almış olabilir).
            #
            # 0 DÖNÜYORUZ, None DEĞİL. Fark hayati: None "süzgeç
            # yok" demek ve kullanıcı BÜTÜN firmaların verisini
            # görürdü — tam tersi. 0 hiçbir firmanın kimliği
            # olmadığı için süzgeç HİÇBİR SATIRI geçirmez.
            #
            # Bu duruma normalde hiç düşülmüyor: aşağıdaki
            # `_firma_secim_guard` isteği zaten seçim ekranına
            # çeviriyor. Burası o kapının arkasındaki emniyet;
            # ileride kapının dışında kalan bir uç eklenirse
            # sızıntı değil boş liste görülsün.
            _f = 0
'''),
    ('flask_app.py', 'KF · flask_app.py blok 17',
     r'''        _f = aktif_firma_id()
        if not _f:
''',
     r'''        _f = aktif_firma_id()
        # ══ KF2 · `is None` İLE `not` ARASINDAKİ FARK HAYATİ ══
        # Burada `if not _f:` yazılıydı. KF2'den sonra çözümleyici
        # "firma seçilmedi / izinli değil" durumunda 0 dönüyor; 0
        # falsy olduğu için eski satır SÜZGECİ HİÇ KURMUYOR ve
        # kullanıcı BÜTÜN firmaların verisini görüyordu. Yani fail-
        # closed diye yazdığım değer, tam tersi etki yapardı.
        #
        # Süzgeç YALNIZCA None'da kapanmalı: None demek "istek
        # bağlamı yok" (CLI, betik) ya da "firma_atla() ile bilerek
        # atlandı". 0 ise süzülmeli — ve hiçbir satırı geçirmemeli.
        if _f is None:
'''),
    ('flask_app.py', 'KF · flask_app.py blok 18',
     r'''                         'acente_cari_id', 'kaynak_cari_id')
''',
     r'''                         'acente_cari_id', 'kaynak_cari_id')

    # ── MUAF YOLLAR (KF2) ──
    # Seçim kapısı bu yolları engellemez; aksi halde seçim ekranının
    # kendisi de engellenir ve kullanıcı sonsuz yönlendirmede kalır.
    FIRMA_SECIM_MUAF = (
        '/firma-sec', '/api/firma/sec', '/api/firma/liste', '/api/firma',
        '/giris', '/cikis', '/static/', '/favicon', '/saglik',
    )

    @app.before_request
    def _firma_secim_guard():
        """Firma seçmeden hiçbir ekran/uç çalışmaz (KF2).

        Varsayılan firma kaldırıldı: kullanıcı artık sessizce bir
        firmaya DÜŞMÜYOR, seçmek zorunda. Seçmeden istek çalıştırmak
        iki kötü sonuçtan birini verirdi — ya boş ekran (süzgeç
        hiçbir satırı geçirmiyor) ya da sebebi görünmeyen bir yazma
        hatası. İkisi de kullanıcıya ne yapacağını söylemiyor.

        Burada erkenden durdurup seçim ekranına gönderiyoruz; API
        isteklerine de HTML değil net bir JSON dönüyor, yoksa
        tarayıcıdaki `api()` yardımcısı HTML'i ayrıştıramayıp
        anlamsız hata basardı.
        """
        if 'kullanici' not in session:
            return None                 # oturum yok: _auth_required işi
        for _m in FIRMA_SECIM_MUAF:
            if request.path.startswith(_m):
                return None
        if session.get('firma_id') and aktif_firma_id():
            return None                 # seçim var ve hâlâ izinli

        _izinli = _kullanici_firma_idleri()
        if len(_izinli) == 1:
            # Tek firma: çözümleyici zaten kendiliğinden seçiyor,
            # kapıdan geçsin.
            return None
        if not _izinli:
            # ── HİÇ FİRMA ATANMAMIŞ ──
            # Sessizce bir firmaya atamak, yöneticinin VERMEDİĞİ bir
            # yetkiyi vermek olurdu. Durup sebebini söylüyoruz.
            if request.path.startswith('/api/'):
                return jsonify({'ok': False, 'error': 'firma_yok',
                                'mesaj': 'Hesabınıza hiçbir firma '
                                'tanımlanmamış. Yöneticinizden Ayarlar → '
                                'Kullanıcılar bölümünden firma yetkisi '
                                'istemeniz gerekiyor.'}), 403
            session['firma_hata'] = ('Hesabınıza hiçbir firma tanımlanmamış. '
                                     'Yöneticinizden firma yetkisi isteyin.')
            return redirect(url_for('firma_sec_ekran'))
        # Birden çok firma var, seçim yapılmamış
        if request.path.startswith('/api/'):
            return jsonify({'ok': False, 'error': 'firma_secilmedi',
                            'mesaj': 'Firma seçilmedi. Firma seçim '
                            'ekranına dönün.'}), 409
        return redirect(url_for('firma_sec_ekran'))
'''),
    ('flask_app.py', 'KF · flask_app.py blok 19',
     r'''        try:
            _f = session.get('firma_id') or _varsayilan_firma()
''',
     r'''        try:
            # KF2: `or _sistem_firma()` KALDIRILDI. Firma seçilmemişse
            # küresel çapaya düşmek, kullanıcının hiç seçmediği bir
            # firmanın ortak-liste ayarını uygulamak olurdu. Seçim
            # yoksa varsayılan davranış (ortak = True) yeterli;
            # seçim kapısı isteği zaten geçirmiyor.
            #
            # firma_denetim F6 bu kalıntıyı yakaladı — KF2'de dokuz
            # çağrı yerini güncellemiştim, bu dokuzuncu gözden
            # kaçmıştı.
            _f = session.get('firma_id')
'''),
    ('flask_app.py', 'KF · flask_app.py blok 20',
     r'''            return jsonify({'error': 'Unauthorized'}), 401
        _admin = (session.get('rol') or '').upper() == 'ADMIN'
''',
     r'''            return jsonify({'error': 'Unauthorized'}), 401
        _admin = (session.get('rol') or '').upper() == 'ADMIN'
        # ── KF2 · LİSTE KİŞİYE ÖZEL ──
        # Banner çipi ve Ayarlar paneli bu uçtan besleniyor. Admin
        # bütün firmaları (kapalılar dahil — yönetmesi gerekiyor),
        # diğerleri YALNIZCA izinli olduklarını görür. Süzmezsek
        # kullanıcı yetkisi olmayan firmanın adını, ünvanını ve vergi
        # numarasını görürdü: veri sızıntısı, geçiş yapamasa bile.
        _izinli = _kullanici_firma_idleri()
'''),
    ('flask_app.py', 'KF · flask_app.py blok 21',
     r'''        with firma_atla():
            kayitlar = (Firma.query.order_by(Firma.sira, Firma.id).all())
''',
     r'''        with firma_atla():
            _q = Firma.query
            if not _admin:
                _q = _q.filter(Firma.id.in_(_izinli or [0]))
            kayitlar = _q.order_by(Firma.sira, Firma.id).all()
'''),
    ('flask_app.py', 'KF · flask_app.py blok 22',
     r'''                'vergi_no': f.vergi_no or '',
                'varsayilan': bool(f.varsayilan), 'aktif': bool(f.aktif),
''',
     r'''                'vergi_no': f.vergi_no or '',
                'aktif': bool(f.aktif),
'''),
    ('flask_app.py', 'KF · flask_app.py blok 23',
     r'''                      eposta=(data.get('eposta') or '').strip() or None,
                      varsayilan=False, aktif=True, sira=_son + 1,
''',
     r'''                      eposta=(data.get('eposta') or '').strip() or None,
                      aktif=True, sira=_son + 1,
'''),
    ('flask_app.py', 'KF · flask_app.py blok 24',
     r'''            engel = 'İçinde bulunduğun firmayı silemezsin. Önce başka bir firmaya geç.'
        elif f.varsayilan:
            engel = 'Varsayılan firma silinemez. Önce başka bir firmayı varsayılan yap.'
''',
     r'''            engel = 'İçinde bulunduğun firmayı silemezsin. Önce başka bir firmaya geç.'
'''),
    ('flask_app.py', 'KF · flask_app.py blok 25',
     r'''            engel = 'Son firma silinemez — firmasız sistem kayıt yazamaz.'
''',
     r'''            engel = 'Son firma silinemez — firmasız sistem kayıt yazamaz.'
        else:
            _kilit = _firma_tek_dayanak(fid)
            if _kilit:
                engel = ('Bu firma şu kullanıcıların TEK firması: '
                         + ', '.join(_kilit)
                         + '. Silinirse sisteme giremezler. Önce onlara '
                         'Ayarlar → Kullanıcılar\'dan başka bir firma verin.')
'''),
    ('flask_app.py', 'KF · flask_app.py blok 26',
     r'''                        'silinebilir': engel is None})
''',
     r'''                        'silinebilir': engel is None})

    def _firma_tek_dayanak(fid):
        """Bu firma SİLİNİRSE firmasız kalacak kullanıcıların adları (KF2).

        Kapsamı 'secili' olan ve yalnızca bu firmaya atanmış bir
        kullanıcı, firma silindiğinde sisteme GİREMEZ hâle gelir:
        izin listesi boşalır. Silme bunu sessizce yapmamalı —
        yöneticinin kimi kilitlediğini görmesi gerekiyor.

        Kapsamı 'tumu' olanlar etkilenmez; onların listesi firma
        tablosundan geliyor ve boşalmaz (son firma zaten silinemiyor).
        """
        try:
            with db.engine.connect() as _b:
                return [r[0] for r in _b.execute(sa_text(
                    'SELECT k.ad FROM kullanicilar k '
                    'JOIN kullanici_firma kf ON kf.kullanici_id = k.id '
                    'WHERE kf.firma_id = :f '
                    "  AND COALESCE(k.firma_kapsam, 'secili') <> 'tumu' "
                    '  AND NOT EXISTS (SELECT 1 FROM kullanici_firma k2 '
                    '                  JOIN firma f2 ON f2.id = k2.firma_id '
                    '                  WHERE k2.kullanici_id = k.id '
                    '                    AND k2.firma_id <> :f '
                    '                    AND f2.aktif = :e) '
                    'ORDER BY k.ad'), {'f': fid, 'e': True}).fetchall()]
        except Exception as _e:
            app.logger.warning(f'[KF2] tek dayanak sorgusu basarisiz: {_e}')
            return []
'''),
    ('flask_app.py', 'KF · flask_app.py blok 27',
     r'''                            'Önce başka bir firmaya geç.'}), 400
        if f.varsayilan:
            return jsonify({'ok': False, 'mesaj':
                            'Varsayılan firma silinemez.'}), 400
''',
     r'''                            'Önce başka bir firmaya geç.'}), 400
        # KF1: "varsayılan firma silinemez" denetimi KALKTI —
        # bayrağın kendisi kalktı. Yerine bir şey koymak gerekmiyor:
        # "içinde bulunduğun firma" ve "son firma" denetimleri
        # duruyor ve asıl korumayı onlar veriyor.
'''),
    ('flask_app.py', 'KF · flask_app.py blok 28',
     r'''                            'Son firma silinemez.'}), 400
''',
     r'''                            'Son firma silinemez.'}), 400
        # KF2: kimseyi sistemden kilitleyerek silme.
        _kilit = _firma_tek_dayanak(fid)
        if _kilit:
            return jsonify({'ok': False, 'mesaj':
                            'Bu firma şu kullanıcıların TEK firması: '
                            + ', '.join(_kilit) + '. Silinirse sisteme '
                            'giremezler. Önce onlara başka bir firma '
                            'verin (Ayarlar → Kullanıcılar).'}), 400
'''),
    ('flask_app.py', 'KF · flask_app.py blok 29',
     r'''        # NameError veriyordu (olculdu).
        from models import varsayilan_firma_unut as _vfu
''',
     r'''        # NameError veriyordu (olculdu).
        from models import sistem_firma_unut as _vfu
'''),
    ('flask_app.py', 'KF · flask_app.py blok 30',
     r'''    def api_firma_sec():
        """Çalışılan firmayı değiştirir. YALNIZCA ADMIN."""
''',
     r'''    def api_firma_sec():
        """Çalışılan firmayı değiştirir.

        KF2: artık admin'e özel DEĞİL — herkes kendi izinli firmaları
        arasında geçiş yapabilir. Rol denetiminin yerini İZİN
        denetimi aldı: istenen firma kullanıcının listesinde yoksa
        403. Rol denetimini korumak, çoklu firmayı kullanıcılara
        açmanın tam tersi olurdu.
        """
'''),
    ('flask_app.py', 'KF · flask_app.py blok 31',
     r'''            return jsonify({'error': 'Unauthorized'}), 401
        if (session.get('rol') or '').upper() != 'ADMIN':
            return jsonify({'ok': False, 'mesaj':
                            'Firma değiştirmek yalnızca admin yetkisindedir'}), 403
''',
     r'''            return jsonify({'error': 'Unauthorized'}), 401
'''),
    ('flask_app.py', 'KF · flask_app.py blok 32',
     r'''            return jsonify({'ok': False, 'mesaj': 'Firma kimliği sayı olmalı'}), 400
''',
     r'''            return jsonify({'ok': False, 'mesaj': 'Firma kimliği sayı olmalı'}), 400
        if fid not in _kullanici_firma_idleri():
            # "Bulunamadı" demiyoruz: izin yoksa sebebi söylenmeli,
            # yoksa kullanıcı var olan bir firmayı silinmiş sanır.
            return jsonify({'ok': False, 'mesaj':
                            'Bu firmada çalışma yetkiniz yok.'}), 403
'''),
    ('flask_app.py', 'KF · flask_app.py blok 33',
     r'''                'cari_kapsam': (k.cari_kapsam or 'atanan'),
''',
     r'''                'cari_kapsam': (k.cari_kapsam or 'atanan'),
                # KF3: düzenleme penceresi bunları DOLDURMAK zorunda;
                # doldurmazsa kaydet izinleri sessizce siler.
                'firma_kapsam': (k.firma_kapsam or 'secili'),
                'firmalar': _kullanici_firma_uyelikleri(k.id),
'''),
    ('flask_app.py', 'KF · flask_app.py blok 34',
     r'''                'olusturma': k.olusturma.strftime('%Y-%m-%d %H:%M') if k.olusturma else None
            })
        return jsonify(result)
''',
     r'''                'olusturma': k.olusturma.strftime('%Y-%m-%d %H:%M') if k.olusturma else None
            })
        return jsonify(result)

    def _kullanici_firma_uyelikleri(kid):
        """Bir kullanıcının atanmış firma kimlikleri (KF3)."""
        from models import KullaniciFirma as _KF
        try:
            return sorted(r.firma_id for r in
                          _KF.query.filter_by(kullanici_id=kid).all())
        except Exception:
            return []

    def _firma_kapsam_temizle(v):
        """Geçersiz değer 'secili'ye düşer — GÜVENLİ TARAF (KF3).

        Eksik ya da bozuk değer "herkes her firmayı görsün" anlamına
        GELMEMELİ. `_kapsam_temizle` (cari kapsamı) ile aynı mantık.
        """
        return 'tumu' if (v or '').strip().lower() == 'tumu' else 'secili'

    def _kullanici_firmalari_yaz(kid, idler):
        """Kullanıcının firma üyeliklerini verilen listeye EŞİTLER.

        Var olmayan firma kimlikleri atılır: ekrandan eski bir liste
        gelirse (firma bu arada silinmişse) yabancı anahtar kırılırdı.
        """
        from models import KullaniciFirma as _KF
        _istek = {int(x) for x in (idler or []) if str(x).strip().isdigit()}
        # Çıkış kapısı GEREKMİYOR: okuma süzgeci yalnızca
        # FirmaKapsamli, Veriler ve Cari'ye uygulanıyor; `firma`
        # tablosu kapsam dışı. (İlk yazışta buraya bir atlama
        # koymuştum, firma_denetim F3 yakaladı — işe yaramayan her
        # atlama o listeyi anlamsızlaştırıyor.)
        _gecerli = {f.id for f in Firma.query.all()}
        _istek &= _gecerli
        _KF.query.filter_by(kullanici_id=kid).delete()
        for _fid in sorted(_istek):
            db.session.add(_KF(kullanici_id=kid, firma_id=_fid))
        return sorted(_istek)
'''),
    ('flask_app.py', 'KF · flask_app.py blok 35',
     r'''                cari_kapsam=_kapsam_temizle(data.get('cari_kapsam')),
''',
     r'''                cari_kapsam=_kapsam_temizle(data.get('cari_kapsam')),
                # KF3: firma kapsamı da ayrı eksen
                firma_kapsam=_firma_kapsam_temizle(data.get('firma_kapsam')),
'''),
    ('flask_app.py', 'KF · flask_app.py blok 36',
     r'''            db.session.add(k)
            db.session.commit()
''',
     r'''            db.session.add(k)
            db.session.commit()
            if 'firmalar' in data:
                _kullanici_firmalari_yaz(k.id, data.get('firmalar'))
                db.session.commit()
'''),
    ('flask_app.py', 'KF · flask_app.py blok 37',
     r'''            k.cari_kapsam = _kapsam_temizle(data.get('cari_kapsam'))
''',
     r'''            k.cari_kapsam = _kapsam_temizle(data.get('cari_kapsam'))
        # KF3: firma kapsamı ve üyelikler. İkisi de GÖNDERİLDİYSE
        # güncellenir, gönderilmediğinde DOKUNULMAZ — kısmi
        # güncelleme bir kullanıcının firma erişimini sessizce
        # kesmemeli. (Aynı kural cari kapsamında da geçerli, yorumu
        # yukarıda.)
        if 'firma_kapsam' in data:
            k.firma_kapsam = _firma_kapsam_temizle(data.get('firma_kapsam'))
        if 'firmalar' in data:
            _kullanici_firmalari_yaz(k.id, data.get('firmalar'))
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 1',
     r'''#    3) TÜM VERİLERİ SİL                 --tumunu-sil
#         İşlem verisi + FİRMALARIN KENDİSİ. Bir firma kalır
#         (varsayılan olan): sistem firmasız çalışmaz ve firma
''',
     r'''#    3) TÜM VERİLERİ SİL                 --tumunu-sil
#         İşlem verisi + FİRMALARIN KENDİSİ. Bir firma kalır ve
#         HANGİSİ olduğunu --kalan= ile sen söylersin (KF1: eskiden
#         `varsayilan` bayrağı karar veriyordu, bayrak kaldırıldı;
#         geri alınamaz bir kararı kimlik sırasına bırakmıyorum):
#         sistem firmasız çalışmaz ve firma
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 2',
     r'''#      venv/bin/python sifirla2.py --firma=2 --onayla    # SADECE o firma
#      venv/bin/python sifirla2.py --tumunu-sil --onayla # TÜM VERİLER
''',
     r'''#      venv/bin/python sifirla2.py --firma=2 --onayla    # SADECE o firma
#      venv/bin/python sifirla2.py --tumunu-sil --kalan=1 --onayla
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 3',
     r'''TEK_FIRMA_ARG = None
''',
     r'''TEK_FIRMA_ARG = None
KALAN_ARG = None
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 4',
     r'''        TEK_FIRMA_ARG = _a.split('=', 1)[1].strip()
''',
     r'''        TEK_FIRMA_ARG = _a.split('=', 1)[1].strip()
    # KF1: --tumunu-sil kipinde hangi firmanın KALACAĞI.
    elif _a.startswith('--kalan='):
        KALAN_ARG = _a.split('=', 1)[1].strip()
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 5',
     r'''    'cari_firma': 'Cari görünürlük üyelikleri (hangi cari hangi firmada)',
''',
     r'''    'cari_firma': 'Cari görünürlük üyelikleri (hangi cari hangi firmada)',
    #   kullanici_firma  Hangi kullanıcı hangi firmada çalışabilir (KF1).
    #               YETKİ kaydıdır, işlem verisi değil. Sıfırlamada
    #               silinmesi, yöneticinin tek tek verdiği firma
    #               izinlerini yok etmek olurdu: sıfırlama sonrası
    #               kimse hiçbir firmaya giremezdi ve sebebi
    #               ekranda görünmezdi. `kullanicilar` korunuyorsa
    #               onların erişimi de korunmalı.
    #
    #               --tumunu-sil kipinde SİLİNEN firmaların
    #               satırları gider (aşağıda, FIRMA_BAGLI ile):
    #               olmayan firmaya bakan izin kaydı artık kalıntı.
    'kullanici_firma': 'Kullanıcı firma izinleri (yetki kaydı)',
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 6',
     r'''        return []
''',
     r'''        return []
    # KF1: `varsayilan` sütunu KALDIRILDI. Firma sırası artık
    # kimliğe göre; "hangi firma kalacak" kararı bayraktan değil
    # --kalan= seçeneğinden geliyor (aşağıda).
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 7',
     r'''    satirlar = b.execute(text(
        'SELECT id, ad, unvan, belge_kodu, varsayilan, aktif '
''',
     r'''    satirlar = b.execute(text(
        'SELECT id, ad, unvan, belge_kodu, aktif '
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 8',
     r'''    return [{'id': r[0], 'ad': r[1] or '', 'unvan': r[2] or '',
             'kod': r[3] or '', 'varsayilan': bool(r[4]), 'aktif': bool(r[5])}
''',
     r'''    return [{'id': r[0], 'ad': r[1] or '', 'unvan': r[2] or '',
             'kod': r[3] or '', 'aktif': bool(r[4])}
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 9',
     r'''    sys.exit(1)
print(f" ✓ kapsama tam — {len(mevcut)} tablonun hepsi sınıflandırılmış")
''',
     r'''    sys.exit(1)
# KF4 · SAYI DOĞRU OLSUN
# Burada `len(mevcut)` yazıyordu ve `alembic_version`'ı da sayıyordu.
# Oysa o tablo SINIFLANDIRILMIŞ değil, kapsama denetiminden MUAF
# TUTULMUŞ (yukarıdaki `t != 'alembic_version'`). "38 tablonun hepsi
# sınıflandırılmış" cümlesi 37 doğru, 1 yanlıştı. Küçük bir sapma ama
# bu betiğin bütün değeri raporunun doğruluğundan geliyor.
_muaf = sorted(t for t in mevcut if t == 'alembic_version')
_siniflanan = len(mevcut) - len(_muaf)
print(f" ✓ kapsama tam — {_siniflanan} tablonun hepsi sınıflandırılmış"
      + (f" ({', '.join(_muaf)} muaf)" if _muaf else ""))
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 10',
     r'''print(" FİRMALAR")
print("─" * 70)
''',
     r'''print(" FİRMALAR")
print("─" * 70)
# KF1: ★ (varsayılan) işareti KALKTI — bayrak kaldırıldı.
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 11',
     r'''for f in firmalar:
    isaret = ' ★' if f['varsayilan'] else '  '
''',
     r'''for f in firmalar:
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 12',
     r'''    kapali = '' if f['aktif'] else '  (kapalı)'
    print(f"  {isaret} [{f['id']:>2}] {f['ad']:<18} {f['kod']:<5} "
''',
     r'''    kapali = '' if f['aktif'] else '  (kapalı)'
    print(f"     [{f['id']:>2}] {f['ad']:<18} {f['kod']:<5} "
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 13',
     r'''          f"{tr(firma_sayimlari.get(f['id'], 0)):>9} kayıt{kapali}")
print("     ★ varsayılan firma")
''',
     r'''          f"{tr(firma_sayimlari.get(f['id'], 0)):>9} kayıt{kapali}")
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 14',
     r'''    KIP = 'tumunu'
    # Kalacak firma: varsayılan, yoksa en küçük kimlikli.
''',
     r'''    KIP = 'tumunu'
    # ── HANGİ FİRMA KALACAK? ──
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 15',
     r'''    # Sistem firmasız çalışmaz; üstelik firma kaydı R2'den beri
    # korunan "firma bilgileri ve LOGO"nun yaşadığı yer (MF5).
    _kalan = next((f for f in firmalar if f['varsayilan']), None) or firmalar[0]
''',
     r'''    # Sistem firmasız çalışmaz; üstelik firma kaydı R2'den beri
    # korunan "firma bilgileri ve LOGO"nun yaşadığı yer (MF5). Yani
    # bu kipte bir firma KALMAK ZORUNDA.
    #
    # KF1'den önce bu karar `varsayilan` bayrağından geliyordu.
    # Bayrak kaldırıldı ve yerine EN KÜÇÜK KİMLİĞİ koymadım: hangi
    # firmanın yaşayacağı GERİ ALINAMAZ bir karar ve kimlik sırası
    # bunun için bir gerekçe değil. Birden çok firma varsa betik
    # artık SORUYOR.
    if len(firmalar) > 1 and not KALAN_ARG:
        print()
        print(" ✗ HANGİ FİRMA KALACAK? --kalan= ile söyle.")
        print()
        print("   Bu kip diğer firmaları SİLER; hangisinin kalacağı")
        print("   geri alınamaz bir karar, tahmin etmiyorum.")
        print()
        for f in firmalar:
            print(f"     venv/bin/python sifirla2.py --tumunu-sil "
                  f"--kalan={f['id']} --onayla      # {f['ad']}")
        print()
        sys.exit(1)
    if KALAN_ARG:
        _ad = [f for f in firmalar
               if str(f['id']) == KALAN_ARG
               or f['ad'].strip().upper() == KALAN_ARG.upper()]
        if not _ad:
            print(f"\n ✗ Kalacak firma bulunamadı: {KALAN_ARG}")
            sys.exit(1)
        if len(_ad) > 1:
            print(f"\n ✗ '{KALAN_ARG}' birden çok firmaya uyuyor — kimlik yaz.")
            sys.exit(1)
        _kalan = _ad[0]
    else:
        _kalan = firmalar[0]          # tek firma var, seçilecek bir şey yok
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 16',
     r'''    print()
    print("   3) TÜM VERİLERİ SİL — firmalar da gider, biri kalır:")
    print("        venv/bin/python sifirla2.py --tumunu-sil --onayla")
''',
     r'''    print()
    print("   3) TÜM VERİLERİ SİL — firmalar da gider, biri kalır.")
    print("      Hangisinin KALACAĞINI sen söylüyorsun (KF1):")
    if len(firmalar) > 1:
        for f in firmalar:
            print(f"        venv/bin/python sifirla2.py --tumunu-sil "
                  f"--kalan={f['id']} --onayla   # {f['ad']} kalır")
    else:
        print("        venv/bin/python sifirla2.py --tumunu-sil --onayla")
        print("        (tek firma var, seçilecek bir şey yok)")
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 17',
     r'''
        # Kalan firma varsayılan ve açık olsun — tek firma kaldığında
        # "varsayılan yok" durumu giriş akışını kırardı.
        b.execute(text('UPDATE firma SET varsayilan = :e, aktif = :e '
                       'WHERE id = :f'),
''',
     r'''
        # Kalan firma AÇIK olsun: kapalı tek firma, girilemeyen bir
        # sistem demek olurdu. (KF1: `varsayilan` kalktı, yalnızca
        # `aktif` yazılıyor.)
        b.execute(text('UPDATE firma SET aktif = :e WHERE id = :f'),
'''),
    ('sifirla2.py', 'KF · sifirla2.py blok 18',
     r'''
        if KIP == 'tumunu' and t in ('firma', 'kasa', 'banka', 'veriler'):
''',
     r'''
        # KF1: `kullanici_firma` da bu gruba girer. Korunan bir tablo
        # ama --tumunu-sil kipinde SİLİNEN firmalara bakan satırları
        # bilerek gidiyor; eşitlik beklemek, doğru çalışan silmeyi
        # HATA diye raporlamak olurdu. (cari_firma'da aynı tuzağa bir
        # kez düşmüştüm — orada sayı ARTABİLDİĞİ için.)
        if KIP == 'tumunu' and t in ('firma', 'kasa', 'banka', 'veriler',
                                     'kullanici_firma'):
'''),
    ('firma_denetim.py', 'KF · firma_denetim.py blok 1',
     r'''        print(f"       {_ad:<28} satır {_n}")

''',
     r'''        print(f"       {_ad:<28} satır {_n}")

# ══════════════════════════════════════════════════════════════════════
#  F6 · ERİŞİM ÇÖZÜMLEYİCİSİ
# ══════════════════════════════════════════════════════════════════════
#
# KF1/KF2 ile çoklu firma tüm kullanıcılara açıldı ve "varsayılan
# firma" kavramı kaldırıldı. Bu düzen DÖRT SATIRA dayanıyor; dördü de
# tek kelimeyle bozulabilir ve bozulduğunda HATA VERMEZ:
#
#   1. Süzgeç `if _f is None:` ile kapanır. `if not _f:` yazılırsa
#      "firma seçilmedi" değeri (0) falsy olduğu için süzgeç HİÇ
#      KURULMAZ ve kullanıcı BÜTÜN firmaların verisini görür. Yani
#      fail-closed diye konan değer tam tersi etki yapar. Bu satır
#      zaten bir kez yanlış yazılmıştı.
#   2. `aktif_firma_id` küresel çapaya (_sistem_firma) DÜŞMEZ. Düşerse
#      yetkisi olmayan kullanıcı sessizce bir firmaya girer.
#   3. Damga 0'ı REDDEDER. Etmezse seçim yapmamış kullanıcının yazdığı
#      kayıt rastgele bir firmaya damgalanır.
#   4. Firma listesi uçları İZİNLE süzülür. Süzülmezse kullanıcı
#      yetkisi olmayan firmaların adını ve belge kodunu görür.
print()
print("─" * 70)
print(" F6 · ERİŞİM ÇÖZÜMLEYİCİSİ   [SESSİZ SIZINTI / SESSİZ ERİŞİM]")
print("─" * 70)


def _govde(kaynak, ad):
    """Bir fonksiyonun gövdesi, YORUMLAR ATILMIŞ (girintiye göre).

    Yorumları atmak şart: F3'te aynı hatayı yapmıştım, 'firma_atla()'
    geçen yorum satırları çıkış kapısı sayılıyordu. Burada da öyle
    oldu — `aktif_firma_id` içindeki "eskiden _sistem_firma()
    dönüyordu" açıklaması, fonksiyon hâlâ çapaya düşüyor gibi
    okundu. Denetim kodu ölçmeli, metni değil.
    """
    m = re.search(r'^(\s*)def\s+' + re.escape(ad) + r'\s*\(', kaynak, re.M)
    if not m:
        return None
    gir = len(m.group(1))
    satirlar = kaynak[m.end():].split('\n')
    toplanan = []
    for sat in satirlar[1:]:
        if sat.strip() and (len(sat) - len(sat.lstrip())) <= gir:
            break
        _k = sat.find('#')
        toplanan.append(sat if _k < 0 else sat[:_k])
    return '\n'.join(toplanan)


try:
    MODELS = io.open(KOK / 'models.py', encoding='utf-8').read()
except Exception:
    MODELS = ''

_f6 = 0

# 1 · süzgeç `is None` ile kapanıyor mu
_suz = _govde(KAYNAK, '_firma_suzgeci')
if _suz is None:
    print("   ✗ _firma_suzgeci bulunamadı — süzgeç kancası kalkmış mı?")
    _f6 += 1
elif 'if _f is None:' not in _suz:
    print("   ✗ _firma_suzgeci: `if _f is None:` YOK")
    print("     Süzgeç `not` ile kapatılıyorsa 0 (firma seçilmedi)")
    print("     değeri süzgeci HİÇ KURMAZ → bütün firmaların verisi")
    print("     görünür. Fail-closed sanılan satır ters çalışır.")
    _f6 += 1
else:
    print("   ✓ süzgeç yalnızca None'da kapanıyor (0 süzülüyor)")

# 2 · çözümleyici küresel çapaya düşmüyor mu
_akt = _govde(KAYNAK, 'aktif_firma_id')
if _akt is None:
    print("   ✗ aktif_firma_id bulunamadı")
    _f6 += 1
elif re.search(r'_sistem_firma\s*\(', _akt):
    print("   ✗ aktif_firma_id küresel çapaya (_sistem_firma) DÜŞÜYOR")
    print("     Varsayılan firma kaldırıldı; buraya düşmek yetkisi")
    print("     olmayan kullanıcıyı sessizce bir firmaya sokar.")
    print("     Çapa YALNIZCA kullanıcısız yollar için (models).")
    _f6 += 1
else:
    print("   ✓ aktif_firma_id küresel çapaya düşmüyor")

# 3 · damga 0'ı reddediyor mu
_dmg = _govde(MODELS, '_firma_damgasi') if MODELS else None
if _dmg is None:
    print("   ⚠ models.py'de _firma_damgasi okunamadı — bu eksen atlandı")
elif 'if not fid:' not in _dmg:
    print("   ✗ _firma_damgasi 0'ı (firma seçilmedi) REDDETMİYOR")
    print("     Reddetmezse ya yabancı anahtar kırılır ya kayıt")
    print("     rastgele bir firmaya yazılır.")
    _f6 += 1
else:
    print("   ✓ damga 'firma seçilmedi' durumunu reddediyor")

# 4 · firma listesi uçları izinle süzülüyor mu
for _ad, _aciklama in (('_firma_listesi_ozet', 'banner çipi'),
                       ('api_firma_liste', 'ayarlar paneli'),
                       ('firma_sec_ekran', 'firma seçim ekranı')):
    _g = _govde(KAYNAK, _ad)
    if _g is None:
        print(f"   ⚠ {_ad} bulunamadı — atlandı")
        continue
    if '_kullanici_firma_idleri' not in _g:
        print(f"   ✗ {_ad} ({_aciklama}) izinle SÜZÜLMÜYOR")
        print("     Kullanıcı yetkisi olmayan firmanın adını ve belge")
        print("     kodunu görür; geçiş yapamasa bile bu bilgidir.")
        _f6 += 1
    else:
        print(f"   ✓ {_ad:<22} izinle süzülüyor ({_aciklama})")

bulgu += _f6

'''),
    ('templates/firma_sec.html', 'KF · templates/firma_sec.html blok 1',
     r'''
    <div id="hata" class="hata gizli"></div>
''',
     r'''
    {# KF2: sunucu bir sebep yolladıysa (örn. hiç firma atanmamış)
       ekranda baştan görünsün — boş liste tek başına sebebini
       anlatmıyor. #}
    <div id="hata" class="hata{% if not hata %} gizli{% endif %}">
      {{ hata or '' }}</div>

    {% if not firmalar and not admin %}
    <p class="alt">Hesabınıza henüz firma tanımlanmamış. Yöneticiniz
       Ayarlar → Kullanıcılar bölümünden size firma yetkisi verdikten
       sonra buradan seçim yapabileceksiniz.</p>
    {% endif %}
'''),
    ('templates/firma_sec.html', 'KF · templates/firma_sec.html blok 2',
     r'''      </span>
      {% if f.varsayilan %}<span class="rozet">varsayılan</span>{% endif %}
      {% if not f.varsayilan %}
''',
     r'''      </span>
      {# KF1: "varsayılan" rozeti ve onun Sil düğmesini gizlemesi
         KALKTI — bayrak kaldırıldı. Sil silinemeyecek bir firmaya
         basılırsa sunucu sebebini söylüyor ("içinde bulunduğun
         firma", "son firma", "şu kullanıcıların tek firması").

         KF2: Sil YALNIZCA ADMIN'de. Ekran artık herkese açık; firma
         silmeyi herkese göstermek, basınca 403 yiyecek bir düğme
         koymak olurdu. #}
      {% if admin %}
'''),
    ('templates/firma_sec.html', 'KF · templates/firma_sec.html blok 3',
     r'''    {% endfor %}

''',
     r'''    {% endfor %}

    {# KF2: yeni firma açmak admin işi. #}
    {% if admin %}
'''),
    ('templates/firma_sec.html', 'KF · templates/firma_sec.html blok 4',
     r'''    <button class="ekle-btn" id="ekleBtn" onclick="formAc()">+ Yeni firma ekle</button>
''',
     r'''    <button class="ekle-btn" id="ekleBtn" onclick="formAc()">+ Yeni firma ekle</button>
    {% endif %}
'''),
    ('templates/base.html', 'KF · templates/base.html blok 1',
     r'''      <div class="ust-sag">
        {# ── FİRMA ÇİPİ (MF3) ──
''',
     r'''      <div class="ust-sag">
        {# ── FİRMA ÇİPİ (MF3 · KF2) ──
'''),
    ('templates/base.html', 'KF · templates/base.html blok 2',
     r'''           Tek firma varsa HİÇ basılmaz: bugünkü üst bar aynen kalır.
           Admin seçici görür, diğerleri yalnızca etiket — firma
           değiştirmek admin yetkisinde. #}
''',
     r'''           Tek firma varsa HİÇ basılmaz: bugünkü üst bar aynen kalır.

           KF2: çip artık HERKESTE seçilebilir. `firma_listesi` zaten
           kullanıcının İZİNLİ firmalarını taşıyor (api_firma_liste /
           _firma_listesi_ozet süzüyor), yani listede yalnızca
           geçebileceği firmalar var. Eskiden admin olmayan için
           `disabled` idi ve iki firması olan bir muhasebeci, ikisi
           arasında geçmek için çıkış yapıp yeniden girmek zorunda
           kalıyordu. #}
'''),
    ('templates/base.html', 'KF · templates/base.html blok 3',
     r'''        <div style="position:relative">
          <button class="firma-cip" {% if menu_admin %}data-secilebilir="1"
                  onclick="firmaMenuAc(event)" title="Çalışılan firma — değiştir"
                  {% else %}disabled title="Çalışılan firma"{% endif %}>
''',
     r'''        <div style="position:relative">
          <button class="firma-cip" data-secilebilir="1"
                  onclick="firmaMenuAc(event)" title="Çalışılan firma — değiştir">
'''),
    ('templates/ayarlar.html', 'KF · templates/ayarlar.html blok 1',
     r'''          işlemlerini yapabilir.
        </div>
      </div>
''',
     r'''          işlemlerini yapabilir.
        </div>
      </div>
      <!-- ── FİRMA KAPSAMI (KF3) ──
           Hangi kullanıcı HANGİ FİRMADA çalışabilir. `cari_kapsam`
           ile aynı iki eksenli desen; sebebi de aynı: yalnızca açık
           liste tutulsaydı, yeni bir firma açıldığında onu görmesi
           gereken herkesi tek tek düzenlemek gerekirdi ve unutulan
           kullanıcı firmayı hiç görmezdi. -->
      <div class="form-alan" id="uFirmaKapsamAlan" style="margin-top:6px">
        <label>Firma Kapsamı</label>
        <select id="uFirmaKapsam" onchange="uFirmaKapsamDegisti()">
          <option value="secili">Seçili firmalar — aşağıda işaretlenenler</option>
          <option value="tumu">Tüm firmalar — muhasebe, yönetim</option>
        </select>
        <div id="uFirmaKutular" style="margin-top:8px"></div>
        <div id="uFirmaNot" style="font-size:.76rem;color:var(--soluk);
             margin-top:4px;line-height:1.5"></div>
      </div>
'''),
    ('templates/ayarlar.html', 'KF · templates/ayarlar.html blok 2',
     r'''async function kullaniciYukle() {
''',
     r'''async function kullaniciYukle() {
  /* KF3: firma kutuları için firma listesi de gerekiyor. Kullanıcı
     panelinden yükleniyor; Firmalar paneline hiç uğramadan kullanıcı
     düzenlenebiliyor ve o zaman kutular BOŞ çizilirdi — kaydet
     basıldığında izinler sessizce silinirdi. İkinci bir uç
     açmıyoruz, Firmalar panelinin kullandığı uç bu. */
  try {
    const _f = await api('/api/firma');
    FIRMALAR_KF = (_f && _f.firmalar) || [];
  } catch (e) { FIRMALAR_KF = []; }
'''),
    ('templates/ayarlar.html', 'KF · templates/ayarlar.html blok 3',
     r'''    DUZENLENEN ? (DUZENLENEN.cari_kapsam || 'atanan') : 'atanan';
''',
     r'''    DUZENLENEN ? (DUZENLENEN.cari_kapsam || 'atanan') : 'atanan';
  /* KF3: firma kapsamı ve işaretli firmalar da doldurulmalı —
     doldurulmazsa kaydet, kullanıcının firma izinlerini siler. */
  const _fk = document.getElementById('uFirmaKapsam');
  if (_fk) _fk.value = DUZENLENEN ? (DUZENLENEN.firma_kapsam || 'secili')
                                  : 'secili';
  SECILI_FIRMALAR = (DUZENLENEN && Array.isArray(DUZENLENEN.firmalar))
    ? DUZENLENEN.firmalar.slice() : [];
  uFirmaKutulariCiz();
'''),
    ('templates/ayarlar.html', 'KF · templates/ayarlar.html blok 4',
     r'''  }
  yetkiCiz(); rolDegisti();
''',
     r'''  }
  yetkiCiz(); rolDegisti(); uFirmaKapsamDegisti();
'''),
    ('templates/ayarlar.html', 'KF · templates/ayarlar.html blok 5',
     r'''  document.getElementById('modal').classList.add('acik');
}
''',
     r'''  document.getElementById('modal').classList.add('acik');
}
/* ══ FİRMA KAPSAMI (KF3) ══
   Kutular `FIRMALAR_KF` listesinden çiziliyor; o liste
   `firmaListesiYukle()` ile zaten çekilen firma özetinden besleniyor
   (Firmalar paneli de aynı veriyi kullanıyor, ikinci bir uç
   açmıyoruz).

   ÖNEMLİ: kutular `kullaniciAc()` içinde DOLDURULMALI. Doldurulmazsa
   düzenleme penceresi her açılışta boş kutularla gelir ve kaydet'e
   basmak kullanıcının firma izinlerini sessizce SİLER — KP1'de cari
   kapsamı için aynı tuzağa düşülmüştü, yorumu hâlâ yukarıda. */
let FIRMALAR_KF = [];
let SECILI_FIRMALAR = [];

function uFirmaKutulariCiz() {
  const kap = document.getElementById('uFirmaKutular');
  if (!kap) return;
  if (!FIRMALAR_KF.length) {
    kap.innerHTML = '<div style="font-size:.76rem;color:var(--soluk)">' +
      'Henüz firma yok.</div>';
    return;
  }
  kap.innerHTML = FIRMALAR_KF.map(f => `
    <label style="display:flex;align-items:center;gap:8px;padding:4px 0;
                  font-size:.84rem;cursor:pointer">
      <input type="checkbox" value="${f.id}"
             ${SECILI_FIRMALAR.includes(f.id) ? 'checked' : ''}>
      <span><b>${kacar(f.ad)}</b>${f.belge_kodu
        ? ` <span class="rozet rz-gri">${kacar(f.belge_kodu)}</span>` : ''}
        ${f.aktif === false ? ' <span style="color:var(--soluk)">(kapalı)</span>' : ''}
      </span>
    </label>`).join('');
}

function uFirmaKapsamDegisti() {
  const kapsam = (document.getElementById('uFirmaKapsam') || {}).value;
  const rol = (document.getElementById('uRol') || {}).value;
  const kutular = document.getElementById('uFirmaKutular');
  const not = document.getElementById('uFirmaNot');
  const admin = rol === 'ADMIN';
  /* ADMIN'de kapsam da kutular da ANLAMSIZ: firmaları açan, silen ve
     yetkilendiren o, rolü gereği hepsini görüyor. Gizlemek yerine
     sebebini yazıyoruz — gizli alan "neden yok?" sorusu doğurur. */
  if (kutular) kutular.style.display = (admin || kapsam === 'tumu') ? 'none' : '';
  if (not) {
    not.innerHTML = admin
      ? 'ADMIN rolü <b>bütün firmaları</b> görür — firma kapsamı bu rolde ' +
        'dikkate alınmaz. Rolü değiştirirsen buradaki seçim devreye girer.'
      : (kapsam === 'tumu'
        ? 'Bütün firmalarda çalışabilir. <b>Sonradan açılan firmaları da</b> ' +
          'kendiliğinden görür — işaretleme gerekmez.'
        : 'Yalnızca işaretlenen firmalarda çalışabilir. Hiçbiri ' +
          'işaretlenmezse <b>sisteme giremez</b>; yeni açılan firmaları ' +
          'da görmez, buradan eklemen gerekir.');
  }
}

'''),
    ('templates/ayarlar.html', 'KF · templates/ayarlar.html blok 6',
     r'''  document.getElementById('yetkiKutu').style.display = admin ? 'none' : '';
''',
     r'''  document.getElementById('yetkiKutu').style.display = admin ? 'none' : '';
  /* KF3: rol değişince firma kapsamı notu da tazelenmeli — ADMIN'de
     kapsam dikkate alınmıyor ve bunu ekranın söylemesi gerekiyor. */
  uFirmaKapsamDegisti();
'''),
    ('templates/ayarlar.html', 'KF · templates/ayarlar.html blok 7',
     r'''                  cari_kapsam: (document.getElementById('uKapsam') || {}).value || 'atanan' };
''',
     r'''                  cari_kapsam: (document.getElementById('uKapsam') || {}).value || 'atanan' };
  /* KF3: firma kapsamı + işaretli firmalar. Kutular gizliyken de
     (kapsam 'tumu' ya da rol ADMIN) gönderiliyor: kullanıcı kapsamı
     geri 'secili' yaptığında eski işaretleri bulsun. */
  govde.firma_kapsam =
    (document.getElementById('uFirmaKapsam') || {}).value || 'secili';
  govde.firmalar = Array.from(
    document.querySelectorAll('#uFirmaKutular input[type=checkbox]'))
    .filter(x => x.checked).map(x => parseInt(x.value, 10));
'''),
    ('templates/ayarlar.html', 'KF · templates/ayarlar.html blok 8',
     r'''    <tr>
      <td><b>${kacar(f.ad)}</b>${f.varsayilan ? ' <span class="rozet rz-gri">varsayılan</span>' : ''}
''',
     r'''    <tr>
      <td><b>${kacar(f.ad)}</b>
'''),
    ('tests/test_kritik.py', 'KF · tests/test_kritik.py blok 1',
     r'''                        baglanti_id='FT1', hareket_tarihi=date(2026, 1, 1)),
        ])
        db.session.commit()
''',
     r'''                        baglanti_id='FT1', hareket_tarihi=date(2026, 1, 1)),
        ])
        db.session.commit()
        # ── KF1/KF2 · FİRMA KAPSAMI ──
        # Modeldeki varsayılan 'secili' ve kullanici_firma boş; yani
        # bu kullanıcıların izinli firması YOK ve seçim kapısı onları
        # 403 ile durduruyor. Doğru davranış — ÖLÇÜLDÜ: bu satır
        # eklenmeden 5 test düştü, hepsi "firma_yok" yüzünden.
        #
        # Gerçek sistemde göç (goc_kf1.py) mevcut kullanıcılara tam
        # olarak bunu yapıyor: yükseltme kimsenin erişimini sessizce
        # kesmemeli. Fixture gerçeği taklit ediyor.
        #
        # Erişim KURALLARININ kendisi ayrı testlerde sınanıyor
        # (test_kf2_*): firmasız giremez, izinsiz firmaya geçemez.
        Kullanici.query.update({'firma_kapsam': 'tumu'})
        db.session.commit()
'''),
    ('tests/test_kritik.py', 'KF · tests/test_kritik.py blok 2',
     r'''        s['_csrf'] = 't'
''',
     r'''        s['_csrf'] = 't'
        # ── KF2 · FİRMA SEÇİMİ DE TAKLİT EDİLMELİ ──
        # Gerçek giriş akışı ya firmayı seçtiriyor ya (tek firma
        # varsa) kendiliğinden seçiyor. Yardımcı bunu yapmazsa seçim
        # kapısı isteği 409 ile durdurur.
        #
        # ÖLÇÜLDÜ: eskiden çalışıyordu çünkü testlerde TEK firma
        # vardı ve çözümleyici onu kendiliğinden seçiyordu. KF2/KF3
        # testleri ikinci, üçüncü firmayı açınca admin'in izinli
        # firma sayısı 1'i geçti ve 5 test 409 aldı. Hata testlerde
        # değil, taklidin eksikliğindeydi.
        #
        # KULLANICININ İZİNLİ olduğu ilk firma seçiliyor: gelişigüzel
        # bir kimlik yazmak, izni olmayan firmayı seçmek olurdu ve
        # kapı yine durdururdu.
        s['firma_id'] = _ilk_izinli_firma(ad, rol)
'''),
    ('tests/test_kritik.py', 'KF · tests/test_kritik.py blok 3',
     r'''    return c
''',
     r'''    return c


def _ilk_izinli_firma(ad, rol):
    """Testlik: kullanıcının çalışabileceği ilk firma kimliği."""
    from models import Firma, Kullanici, KullaniciFirma
    with fa.app.app_context():
        if (rol or '').upper() == 'ADMIN':
            f = Firma.query.filter_by(aktif=True).order_by(Firma.id).first()
            return f.id if f else None
        k = Kullanici.query.filter_by(ad=ad).first()
        if k and (k.firma_kapsam or 'secili') == 'tumu':
            f = Firma.query.filter_by(aktif=True).order_by(Firma.id).first()
            return f.id if f else None
        if k:
            u = (KullaniciFirma.query.filter_by(kullanici_id=k.id)
                 .order_by(KullaniciFirma.firma_id).first())
            if u:
                return u.firma_id
        return None
'''),
    ('tests/test_kritik.py', 'KF · tests/test_kritik.py blok 4',
     r'''        if not Kullanici.query.filter_by(ad='yetkisiz').first():
            db.session.add(Kullanici(ad='yetkisiz', sifre=generate_password_hash('x'),
''',
     r'''        if not Kullanici.query.filter_by(ad='yetkisiz').first():
            # KF1: test icinde dogan kullanici fixture'in kapsam
            # guncellemesini KACIRIR — kendisi 'tumu' almali.
            db.session.add(Kullanici(ad='yetkisiz', firma_kapsam='tumu',
                                     sifre=generate_password_hash('x'),
'''),
    ('tests/test_kritik.py', 'KF · tests/test_kritik.py blok 5',
     r'''        if not k:
            k = Kullanici(ad='bgkisitli', sifre='x', rol='SATIS')
''',
     r'''        if not k:
            k = Kullanici(ad='bgkisitli', sifre='x', rol='SATIS',
                          firma_kapsam='tumu')
'''),
    ('tests/test_kritik.py', 'KF · tests/test_kritik.py blok 6',
     r'''        if not k:
            k = Kullanici(ad='bg2kisitli', sifre='x', rol='SATIS')
''',
     r'''        if not k:
            k = Kullanici(ad='bg2kisitli', sifre='x', rol='SATIS',
                          firma_kapsam='tumu')
'''),
    ('tests/test_kritik.py', 'KF · tests/test_kritik.py blok 7',
     r'''            h.borc_try, kur)
''',
     r'''            h.borc_try, kur)


# ══════════════════════════════════════════════════════════════════════
#  KF2 · FİRMA ERİŞİM KURALLARI
#
#  Çoklu firma artık tüm kullanıcılara açık ve kimin hangi firmayı
#  göreceğine yönetici karar veriyor. Bu kuralların HEPSİ sessizce
#  bozulabilecek türden: yanlış tarafa düşen bir koşul ya kullanıcıyı
#  sistemden kilitler ya da ona başka şirketin defterini açar. İkisi
#  de hata vermez, o yüzden burada sınanıyor.
# ══════════════════════════════════════════════════════════════════════

def _kf_kullanici(ad, kapsam='secili', firmalar=(), rol='SATIS'):
    """Testlik kullanıcı + firma izinleri. Varsa günceller."""
    from models import Kullanici, KullaniciFirma
    with fa.app.app_context():
        k = Kullanici.query.filter_by(ad=ad).first()
        if not k:
            k = Kullanici(ad=ad, sifre=generate_password_hash('x'), rol=rol)
            db.session.add(k)
        k.rol = rol
        k.firma_kapsam = kapsam
        k.yetkiler = json.dumps({m: 'yazma' for m in TUM_YAZMA})
        db.session.commit()
        KullaniciFirma.query.filter_by(kullanici_id=k.id).delete()
        for fid in firmalar:
            db.session.add(KullaniciFirma(kullanici_id=k.id, firma_id=fid))
        db.session.commit()
        return k.id


def test_kf2_firmasiz_kullanici_giremez():
    """KF1/KF2: kapsamı 'secili' ve hiç firması olmayan kullanıcı
    sisteme giremez — SESSİZCE bir firmaya atanmaz.

    Eskiden küresel bir varsayılan firma vardı ve böyle bir kullanıcı
    oraya düşüyordu: yöneticinin VERMEDİĞİ bir erişim. Artık durup
    sebebini söylüyor."""
    _kf_kullanici('kfyok', kapsam='secili', firmalar=())
    c = istemci('kfyok', 'SATIS')
    r = c.get('/api/dashboard/ozet', headers=H)
    assert r.status_code == 403, r.get_data(as_text=True)
    d = r.get_json() or {}
    assert d.get('error') == 'firma_yok', d
    # Sebep YAZILI olmalı: boş ekran kullanıcıya ne yapacağını
    # söylemiyor.
    assert 'firma' in (d.get('mesaj') or '').lower(), d


def test_kf2_tek_firma_kendiliginden_secilir():
    """KF2: tek firması olan kullanıcı seçim ekranı görmeden çalışır.

    İstenen buydu: "kullanıcıya sadece tek firma tanımlanmışsa
    varsayılan ihtiyacı ortadan kalkıyor"."""
    from models import Firma
    with fa.app.app_context():
        fid = Firma.query.order_by(Firma.id).first().id
    _kf_kullanici('kftek', kapsam='secili', firmalar=(fid,))
    c = fa.app.test_client()
    with c.session_transaction() as s:
        s['kullanici'] = 'kftek'; s['rol'] = 'SATIS'; s['_csrf'] = 't'
        # firma_id BİLEREK yazılmıyor — kendiliğinden seçmesi gerek.
    r = c.get('/api/dashboard/ozet', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    with c.session_transaction() as s:
        assert s.get('firma_id') == fid, dict(s)


def test_kf2_izinsiz_firmaya_gecilemez():
    """KF2: kullanıcı izinli olmadığı firmaya GEÇEMEZ.

    /api/firma/sec eskiden 'yalnızca admin' idi; rol denetiminin
    yerini izin denetimi aldı. Yerine bir şey konmazsa herkes her
    firmaya geçebilirdi — çoklu firmayı açmanın tam tersi."""
    from models import Firma
    with fa.app.app_context():
        f2 = Firma(ad='KF YABANCI', unvan='KF YABANCI', belge_kodu='KFY',
                   aktif=True)
        db.session.add(f2)
        db.session.commit()
        yabanci = f2.id
        kendi = Firma.query.order_by(Firma.id).first().id
    _kf_kullanici('kfsinir', kapsam='secili', firmalar=(kendi,))
    c = istemci('kfsinir', 'SATIS')
    r = c.post('/api/firma/sec', headers=H,
               json={'firma_id': yabanci})
    assert r.status_code == 403, r.get_data(as_text=True)
    # Oturum DEĞİŞMEMELİ — reddedilen geçiş yan etki bırakmasın.
    with c.session_transaction() as s:
        assert s.get('firma_id') != yabanci, dict(s)
    # Kendi firmasına geçiş SERBEST (admin olmayan da geçebilir).
    r = c.post('/api/firma/sec', headers=H, json={'firma_id': kendi})
    assert r.status_code == 200, r.get_data(as_text=True)


def test_kf2_yetkisiz_firmanin_adi_dahi_gorunmez():
    """KF2: yetkisi olmayan firmanın ADI bile sızmamalı.

    Geçiş yapamamak yetmez: firma adı ve belge kodu tek başına
    bilgidir (kaç şirket var, adları ne).

    NEREYE BAKIYORUZ: ilk sürümde `/api/firma/liste` ucuna
    bakıyordum ve test 403 aldı — o uç 'ayarlar' modülünde ve
    satışçının orada yetkisi YOK. Doğrusu da bu; ama o zaman test
    yanlış yüzeyi sınıyor demektir. Admin olmayan kullanıcıya firma
    adları GERÇEKTEN iki yerden ulaşıyor ve ikisi de sunucuda
    basılıyor: banner çipi (base.html · _firma_listesi_ozet) ve
    firma seçim ekranı. Sızıntı olacaksa orada olur, o yüzden
    basılan HTML'e bakıyoruz."""
    from models import Firma
    with fa.app.app_context():
        f = Firma.query.filter_by(ad='KF YABANCI').first()
        if not f:
            f = Firma(ad='KF YABANCI', unvan='KF YABANCI',
                      belge_kodu='KFY', aktif=True)
            db.session.add(f); db.session.commit()
        kendi = Firma.query.order_by(Firma.id).first().id
    _kf_kullanici('kfgoz', kapsam='secili', firmalar=(kendi,))
    c = istemci('kfgoz', 'SATIS')

    # 1 · firma seçim ekranı
    r = c.get('/firma-sec')
    assert r.status_code == 200, r.status_code
    assert 'KF YABANCI' not in r.get_data(as_text=True)

    # 2 · banner çipi (base.html ile basılan herhangi bir sayfa)
    r = c.get('/', follow_redirects=True)
    assert r.status_code == 200, r.status_code
    assert 'KF YABANCI' not in r.get_data(as_text=True)


def test_kf2_kapsam_tumu_yeni_firmayi_da_gorur():
    """KF1: kapsamı 'tumu' olan kullanıcı SONRADAN açılan firmayı da
    görür — iki eksenli desenin sebebi bu.

    Yalnızca açık liste tutulsaydı, her yeni firmada onu görmesi
    gereken herkesi tek tek düzenlemek gerekirdi."""
    from models import Firma
    _kf_kullanici('kftumu', kapsam='tumu', firmalar=())
    # Firma adlarına admin olmayanın ulaştığı yer seçim ekranı
    # (yukarıdaki testin notu).
    c = istemci('kftumu', 'SATIS')
    assert 'KF SONRADAN' not in c.get('/firma-sec').get_data(as_text=True)
    with fa.app.app_context():
        db.session.add(Firma(ad='KF SONRADAN', unvan='KF SONRADAN',
                             belge_kodu='KFS', aktif=True))
        db.session.commit()
    c = istemci('kftumu', 'SATIS')
    r = c.get('/firma-sec')
    assert r.status_code == 200, r.status_code
    # Kapsamı 'tumu': hiç üyelik satırı olmadan yeni firmayı GÖRÜR.
    assert 'KF SONRADAN' in r.get_data(as_text=True)


def test_kf2_tek_firmasi_olan_kullanici_kilitlenmez():
    """KF2: bir kullanıcının TEK firması silinemez.

    Silinirse o kullanıcının izin listesi boşalır ve sisteme giremez.
    Yöneticinin kimi kilitlediğini görmesi gerekiyor; sessizce
    yapılmamalı."""
    from models import Firma
    with fa.app.app_context():
        f = Firma(ad='KF SILINECEK', unvan='KF SILINECEK',
                  belge_kodu='KFD', aktif=True)
        db.session.add(f); db.session.commit()
        fid = f.id
    _kf_kullanici('kfbagli', kapsam='secili', firmalar=(fid,))
    c = istemci('admin', 'ADMIN')
    # Önizleme engeli söylüyor mu
    r = c.get(f'/api/firma/{fid}/ozet', headers=H)
    if r.status_code == 200:
        assert 'kfbagli' in ((r.get_json() or {}).get('engel') or ''), \
            r.get_data(as_text=True)
    # Gerçek silme REDDEDİLMELİ
    r = c.delete(f'/api/firma/{fid}', headers=H)
    assert r.status_code == 400, r.get_data(as_text=True)
    assert 'kfbagli' in ((r.get_json() or {}).get('mesaj') or ''), \
        r.get_data(as_text=True)
    with fa.app.app_context():
        assert db.session.get(Firma, fid) is not None, 'firma silinmiş'


def test_kf2_secim_yapilmadan_suzgec_kapanmaz():
    """KF2 · EN KRİTİK: firma seçilmeden süzgeç AÇIK kalmamalı.

    Çözümleyici "seçilmedi" durumunda 0 dönüyor. Süzgeçte
    `if not _f: return` yazılı olsaydı 0 falsy olduğu için süzgeç
    HİÇ KURULMAZ ve kullanıcı BÜTÜN firmaların verisini görürdü —
    fail-closed diye yazılan değer tam tersi etki yapardı. Süzgeç
    yalnızca None'da (CLI / firma_atla) kapanmalı.

    Burada doğrudan çözümleyiciye bakıyoruz: iki firması olup seçim
    yapmamış bir kullanıcıda dönen değer 0 olmalı, None OLMAMALI."""
    from models import Firma
    with fa.app.app_context():
        kayitlar = Firma.query.filter_by(aktif=True).order_by(Firma.id).all()
        assert len(kayitlar) >= 2, 'test iki firma istiyor'
        ikisi = (kayitlar[0].id, kayitlar[1].id)
    _kf_kullanici('kfiki', kapsam='secili', firmalar=ikisi)
    c = fa.app.test_client()
    with c.session_transaction() as s:
        s['kullanici'] = 'kfiki'; s['rol'] = 'SATIS'; s['_csrf'] = 't'
    # Seçim yapılmadı: API 409 ile seçim istemeli
    r = c.get('/api/dashboard/ozet', headers=H)
    assert r.status_code == 409, r.get_data(as_text=True)
    assert (r.get_json() or {}).get('error') == 'firma_secilmedi', \
        r.get_data(as_text=True)


# ══════════════════════════════════════════════════════════════════════
#  KF3 · YETKİ PANELİNDEN FİRMA ATAMA
# ══════════════════════════════════════════════════════════════════════

def test_kf3_yetki_paneli_firma_atar():
    """KF3: admin, yetki panelinden kullanıcıya firma atayabilir ve
    atama ANINDA erişime dönüşür."""
    from models import Firma, Kullanici, KullaniciFirma
    with fa.app.app_context():
        f = Firma.query.filter_by(ad='KF3 HEDEF').first()
        if not f:
            f = Firma(ad='KF3 HEDEF', unvan='KF3 HEDEF', belge_kodu='KF3',
                      aktif=True)
            db.session.add(f); db.session.commit()
        hedef = f.id
    a = istemci('admin', 'ADMIN')
    r = a.post('/api/ayarlar/kullanici', headers=H, json={
        'ad': 'kf3yeni', 'sifre': 'x', 'rol': 'SATIS',
        'yetkiler': {'dashboard': 'okuma'},
        'firma_kapsam': 'secili', 'firmalar': [hedef]})
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    with fa.app.app_context():
        k = Kullanici.query.filter_by(ad='kf3yeni').first()
        assert k is not None
        assert (k.firma_kapsam or '') == 'secili', k.firma_kapsam
        uyelik = [x.firma_id for x in
                  KullaniciFirma.query.filter_by(kullanici_id=k.id).all()]
        assert uyelik == [hedef], uyelik


def test_kf3_liste_ucu_kapsam_ve_uyelik_donduruyor():
    """KF3: düzenleme penceresinin DOLDURABİLMESİ için liste ucu
    kapsamı ve üyelikleri vermeli.

    Vermezse pencere boş kutularla açılır ve kaydet'e basmak
    kullanıcının firma izinlerini SESSİZCE SİLER. KP1'de cari
    kapsamında tam olarak bu yaşanmıştı."""
    a = istemci('admin', 'ADMIN')
    r = a.get('/api/ayarlar/kullanici', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    kayitlar = d if isinstance(d, list) else (d.get('data') or [])
    assert kayitlar, d
    for k in kayitlar:
        assert 'firma_kapsam' in k, k
        assert 'firmalar' in k and isinstance(k['firmalar'], list), k


def test_kf3_kismi_guncelleme_izinleri_silmez():
    """KF3: gövdede `firmalar` YOKSA üyeliklere DOKUNULMAZ.

    Başka bir alanı (örn. rol) güncellemek firma erişimini
    kesmemeli — kısmi güncellemenin sessiz yan etkisi olmamalı."""
    from models import Firma, Kullanici, KullaniciFirma
    with fa.app.app_context():
        fid = Firma.query.order_by(Firma.id).first().id
    _kf_kullanici('kf3kismi', kapsam='secili', firmalar=(fid,))
    a = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        kid = Kullanici.query.filter_by(ad='kf3kismi').first().id
    # YALNIZCA rol gönderiliyor
    r = a.put(f'/api/ayarlar/kullanici/{kid}', headers=H,
              json={'rol': 'SATIS'})
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        uyelik = [x.firma_id for x in
                  KullaniciFirma.query.filter_by(kullanici_id=kid).all()]
        assert uyelik == [fid], uyelik
        assert (Kullanici.query.get(kid).firma_kapsam or '') == 'secili'


def test_kf3_gecersiz_kapsam_guvenli_tarafa_duser():
    """KF3: tanınmayan kapsam değeri 'secili'ye düşer.

    Eksik ya da bozuk değer "herkes her firmayı görsün" anlamına
    gelmemeli — gorunurluk='kapali' varsayılanıyla aynı mantık."""
    from models import Kullanici
    a = istemci('admin', 'ADMIN')
    r = a.post('/api/ayarlar/kullanici', headers=H, json={
        'ad': 'kf3bozuk', 'sifre': 'x', 'rol': 'SATIS',
        'yetkiler': {'dashboard': 'okuma'},
        'firma_kapsam': 'HEPSI_BIRDEN', 'firmalar': []})
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    with fa.app.app_context():
        k = Kullanici.query.filter_by(ad='kf3bozuk').first()
        assert (k.firma_kapsam or '') == 'secili', k.firma_kapsam


def test_kf3_olmayan_firma_atanamaz():
    """KF3: ekrandan eski/silinmiş bir firma kimliği gelirse atılır.

    Yabancı anahtarı kırmak yerine sessizce süzülüyor; aksi halde
    bu arada silinmiş bir firmayı işaretli bırakan bir pencere
    kaydet'te 500 verirdi."""
    from models import Kullanici, KullaniciFirma
    a = istemci('admin', 'ADMIN')
    r = a.post('/api/ayarlar/kullanici', headers=H, json={
        'ad': 'kf3hayalet', 'sifre': 'x', 'rol': 'SATIS',
        'yetkiler': {'dashboard': 'okuma'},
        'firma_kapsam': 'secili', 'firmalar': [999999]})
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    with fa.app.app_context():
        k = Kullanici.query.filter_by(ad='kf3hayalet').first()
        uyelik = [x.firma_id for x in
                  KullaniciFirma.query.filter_by(kullanici_id=k.id).all()]
        assert uyelik == [], uyelik


def test_kf3_formda_firma_kapsami_var():
    """KF3: `firma_kapsam` ekranda GİRİLEBİLİR olmalı.

    form_denetim D2 bunu zaten arıyor (modelde var, formda yok →
    öksüz alan). Burada ayrıca sabitliyoruz: alan ve onu dolduran
    JS birlikte durmalı — biri eksikse pencere boş açılır ve
    kaydet izinleri siler."""
    import io as _io
    ay = _io.open('templates/ayarlar.html', encoding='utf-8').read()
    assert 'id="uFirmaKapsam"' in ay
    assert "getElementById('uFirmaKapsam')" in ay
    assert 'uFirmaKutulariCiz()' in ay
    # Kutular kullaniciAc içinde DOLDURULUYOR mu
    assert 'SECILI_FIRMALAR = (DUZENLENEN' in ay
'''),
]

# ══════════════════════════════════════════════════════════════════════
#  TAM DOSYA · goc_kf1.py
#
#  Parça değil tam dosya; iç içe tırnak yığını üretmesin diye
#  base64. Uygulandıktan sonra diskteki dosya baştan sona
#  yorumlu, okunur Python — önce okumak istersen:
#      python3 yama_kf.py --yaz-gecici
# ══════════════════════════════════════════════════════════════════════
TAM_ICERIK = {
    'goc_kf1.py': (
        'IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwojIC0qLSBjb2Rpbmc6IHV0Zi04IC0qLQojIOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkAojICBNaWxlc3RvbmUgRVJQIOKAlCBLVUxMQU5JQ0nihpRGxLBSTUEgR8OWw4fD'
        'nCAgwrcgIEtGMQojCiMgIMOWTktPxZ5VTDogeWFtYV9rZjEucHkgdXlndWxhbm3EscWf'
        'IFZFIFNFUlbEsFMgWUVOxLBERU4gQkHFnkxBVElMTUnFniBvbG1hbMSxLgojCiMgIOKU'
        'gOKUgCBTSVJBIE5FREVOIMOWTkVNTMSwIOKUgOKUgAojICAgIHlhbWEg4oaSIHN5c3Rl'
        'bWN0bCByZXN0YXJ0IOKGkiBCVSBCRVTEsEsKIwojICAgIGBrdWxsYW5pY2lfZmlybWFg'
        'IHRhYmxvc3VudSB2ZSBga3VsbGFuaWNpbGFyLmZpcm1hX2thcHNhbWAKIyAgICBzw7x0'
        'dW51bnUgYcOnxLFsxLHFnyBrZW5kaXNpIGt1cnV5b3IgKGRiLmNyZWF0ZV9hbGwgeWVu'
        'aSBUQUJMTywKIyAgICBTRDIgeWVuaSBTw5xUVU4gZWtsaXlvcikuIEJ1IGJldGlrIG9u'
        'bGFyxLEgS1VSTUFaOyB5b2tzYQojICAgICLDtm5jZSB5ZW5pZGVuIGJhxZ9sYXQiIGRl'
        'eWlwIMOnxLFrYXIuCiMKIyAgICBEYWhhIMO2bmVtbGlzaTogYmV0aWsgYGZpcm1hLnZh'
        'cnNheWlsYW5gIHPDvHR1bnVudSBEw5zFnsOcUsOcWU9SLgojICAgIFllbmlkZW4gYmHF'
        'n2xhdMSxbG1hbcSxxZ8gYmlyIHNpc3RlbWRlIEVTS8SwIEtPRCBow6Jsw6Igw6dhbMSx'
        'xZ/EsXlvciB2ZSBvCiMgICAgc8O8dHVudSBva3V5b3Ig4oCUIGTDvMWfw7xybWVrIMOn'
        'YWzEscWfYW4gdXlndWxhbWF5xLEga8SxcmFyZMSxLiBPIHnDvHpkZW4KIyAgICDDtm5j'
        'ZSB5ZW5pZGVuIGJhxZ9sYXQuCiMKIyAg4pSA4pSAIE5FIFlBUEFSIOKUgOKUgAojICAg'
        'IDEpIE1FVkNVVCBLVUxMQU5JQ0lMQVJBIGBmaXJtYV9rYXBzYW0gPSAndHVtdSdgIHZl'
        'cmlyLgojCiMgICAgICAgRU4gw5ZORU1MxLAgQURJTSBCVS4gTW9kZWxkZWtpIHZhcnNh'
        'ecSxbGFuICdzZWNpbGknIHZlCiMgICAgICAgYGt1bGxhbmljaV9maXJtYWAgdGFibG9z'
        'dSBib8WfLiBIacOnYmlyIMWfZXkgeWFwxLFsbWF6c2EKIyAgICAgICB5w7xrc2VsdG1l'
        'ZGVuIHNvbnJhIEFETUlOIE9MTUFZQU4gSEVSS0VTIHNpc3RlbWUgZ2lyZW1lejoKIyAg'
        'ICAgICBrYXBzYW3EsSAnc2VjaWxpJywgYXRhbm3EscWfIGZpcm1hc8SxIHlvay4gUGF6'
        'YXJ0ZXNpIHNhYmFoxLEKIyAgICAgICBla2lwIGthcMSxZGEga2FsxLFyLgojCiMgICAg'
        'ICAgWcO8a3NlbHRtZSBraW1zZW5pbiBlcmnFn2ltaW5pIFNFU1PEsFpDRSBrZXNtZW1l'
        'bGkuIEJ1Z8O8bgojICAgICAgIGhlcmtlcyB0ZWsgZmlybWFkYSDDp2FsxLHFn8SxeW9y'
        'OyAndHVtdScgYnUgZGF2cmFuxLHFn8SxIGF5bmVuCiMgICAgICAga29ydXIuIERhcmFs'
        'dG1hIGthcmFyxLEgecO2bmV0aWNpbmluOiBBeWFybGFyIOKGkiBLdWxsYW7EsWPEsWxh'
        'cidkYW4KIyAgICAgICBrYXBzYW3EsSAnc2XDp2lsaSBmaXJtYWxhcidhIMOnZXZpcmlw'
        'IGt1dHVsYXLEsSBpxZ9hcmV0bGVyIChLRjMpLgojCiMgICAgICAgQURNSU4nZSBkb2t1'
        'bm1hayBnZXJla21peW9yOiByb2zDvCBnZXJlxJ9pIGhlciBmaXJtYXnEsSBnw7Zyw7x5'
        'b3IuCiMgICAgICAgWWluZSBkZSBrYXBzYW3EsSAndHVtdScgeWF6xLFsxLF5b3I7IHJv'
        'bCBkZcSfacWfaXJzZSBlcmnFn2ltaQojICAgICAgIHNlc3NpemNlIGRhcmFsbWFzxLFu'
        'LgojCiMgICAgMikgYGZpcm1hLnZhcnNheWlsYW5gIHPDvHR1bnVudSBEw5zFnsOcUsOc'
        'Ui4KIwojICAgICAgIEJheXJhayBrYWxkxLFyxLFsZMSxOiBnaXJpxZ8gYWvEscWfxLFu'
        'ZGEga3VsbGFuxLFjxLF5xLEgc2Vzc2l6Y2UgYmlyCiMgICAgICAgZmlybWF5YSBkw7zF'
        'n8O8csO8eW9yZHUgdmUga2ltc2Ugb251IGJpbGluw6dsaSBheWFybGFtxLF5b3JkdS4K'
        'IyAgICAgICBLdWxsYW7EsWPEsXPEsXogeW9sbGFyxLFuIMOnYXBhc8SxIGFydMSxayBl'
        'biBrw7zDp8O8ayBraW1saWtsaSBmaXJtYQojICAgICAgIChfc2lzdGVtX2Zpcm1hX2lk'
        'KS4KIwojICAgICAgIFPDvHR1bnUgdmVyaXRhYmFuxLFuZGEgQklSQUtNQUsgaXN0ZW1l'
        'ZGltOiBtb2RlbGRlIG9sbWF5xLFwCiMgICAgICAgdmVyaXRhYmFuxLFuZGEga2FsYW4g'
        'c8O8dHVuIGBraXNhbHRtYWAgdHV6YcSfxLFuxLFuIGF5bsSxc8SxIG9sdXJkdQojICAg'
        'ICAgIHZlIHNlbWFfZGVuZXRpbSBGQVpMQSBzw7x0dW51IGfDtnJlbWl5b3IsIHlhbG7E'
        'sXpjYSBla3NpxJ9pCiMgICAgICAgZ8O2csO8eW9yIOKAlCB5YW5pIHNlc3NpeiBrYWzE'
        'sXJkxLEuCiMKIyAg4pSA4pSAIEfDnFZFTkzEsEsg4pSA4pSACiMgICAg4oCiIC0tdXln'
        'dWxhIE9MTUFEQU4gSMSww4dCxLBSIMWeRVkgREXEnsSwxZ5NRVo7IHlhbG7EsXpjYSBy'
        'YXBvciB2ZXJpci4KIyAgICDigKIgUG9zdGdyZVNRTCdkZSDDtm5jZSBwZ19kdW1wIHll'
        'ZGXEn2kgYWzEsXI7IHllZGVrIGJhxZ9hcsSxc8SxenNhIMSwUFRBTC4KIyAgICDigKIg'
        'VGVrIHRyYW5zYWN0aW9uLgojICAgIOKAoiBUZWtyYXIgw6dhbMSxxZ90xLFyxLFsYWJp'
        'bGlyOiBpa2luY2kga2/Fn3UgInlhcMSxbGFjYWsgacWfIHlvayIgZGVyLgojICAgIOKA'
        'oiBTw7x0dW4gZMO8xZ/DvHJtZSBHRVLEsCBBTElOQU1BWiDigJQgeWVkZWsgbyB5w7x6'
        'ZGVuIHpvcnVubHUuCiMKIyAg4pSA4pSAIE5PVDogZ29jX21mMS5weSBhcnTEsWsgeWVu'
        'aWRlbiBLT8WeVFVSVUxBTUFaIOKUgOKUgAojICAgIE8gYmV0aWsgYEZpcm1hKHZhcnNh'
        'eWlsYW49VHJ1ZSlgIHlhesSxeW9yOyBhbGFuIGthbGt0xLEuIMSwxZ9pCiMgICAgYml0'
        'bWnFnyB0ZWsgc2VmZXJsaWsgYmlyIGfDtsOnLCB5ZW5pZGVuIGtvxZ90dXJ1bG1hc8Sx'
        'IGdlcmVrbWl5b3IuCiMgICAgWWluZSBkZSBkZW5lbmlyc2UgYcOnxLFrIGJpciBUeXBl'
        'RXJyb3IgdmVyaXAgZHVydXIg4oCUIHNlc3NpeiB5YW5sxLHFnwojICAgIGnFnyB5YXBt'
        'YXosIG8gecO8emRlbiBkb2t1bm11eW9ydW0uCiMKIyAgS1VMTEFOSU0gKHByb2plIGRp'
        'emluaW5kZSk6CiMgICAgICB2ZW52L2Jpbi9weXRob24gZ29jX2tmMS5weSAgICAgICAg'
        'ICAgICAjIFJBUE9SCiMgICAgICB2ZW52L2Jpbi9weXRob24gZ29jX2tmMS5weSAtLXV5'
        'Z3VsYSAgICAjIFVZR1VMQVIKIyDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZAKaW1wb3J0IG9zCmltcG9ydCBzdWJwcm9j'
        'ZXNzCmltcG9ydCBzeXMKZnJvbSBkYXRldGltZSBpbXBvcnQgZGF0ZXRpbWUKZnJvbSBw'
        'YXRobGliIGltcG9ydCBQYXRoCmZyb20gdXJsbGliLnBhcnNlIGltcG9ydCB1cmxwYXJz'
        'ZQoKZnJvbSBkb3RlbnYgaW1wb3J0IGxvYWRfZG90ZW52CmZyb20gc3FsYWxjaGVteSBp'
        'bXBvcnQgY3JlYXRlX2VuZ2luZSwgaW5zcGVjdCwgdGV4dAoKbG9hZF9kb3RlbnYoKQoK'
        'VVlHVUxBID0gJy0tdXlndWxhJyBpbiBzeXMuYXJndgpWVF9VUkwgPSBvcy5lbnZpcm9u'
        'LmdldCgnREFUQUJBU0VfVVJMJykKCmlmIG5vdCBWVF9VUkw6CiAgICBwcmludCgnSEFU'
        'QTogREFUQUJBU0VfVVJMIGJ1bHVuYW1hZMSxICguZW52IG9rdW5hbWFkxLEpLicpCiAg'
        'ICBwcmludCgnICBBZHJlcyBvbG1hZGFuIHlhbmzEscWfIHZlcml0YWJhbsSxbmEgYmHE'
        'n2xhbmFiaWxpcmRpbS4nKQogICAgc3lzLmV4aXQoMSkKCm1vdG9yID0gY3JlYXRlX2Vu'
        'Z2luZShWVF9VUkwpCmtheW5hayA9IHVybHBhcnNlKFZUX1VSTCkKcGcgPSBtb3Rvci5k'
        'aWFsZWN0Lm5hbWUgaW4gKCdwb3N0Z3Jlc3FsJywgJ3Bvc3RncmVzJykKZGVuZXRjaSA9'
        'IGluc3BlY3QobW90b3IpCgpwcmludCgn4pWQJyAqIDcwKQpwcmludCgnICBNSUxFU1RP'
        'TkUgRVJQIOKAlCBLVUxMQU5JQ0nihpRGxLBSTUEgR8OWw4fDnCAgwrcgIEtGMScpCnBy'
        'aW50KCcgIE1PRDonLCAnVVlHVUxBJyBpZiBVWUdVTEEgZWxzZSAnUkFQT1IgKGhpw6di'
        'aXIgxZ9leSBkZcSfacWfbWV6KScpCnByaW50KCfilZAnICogNzApCnByaW50KGYiIFZl'
        'cml0YWJhbsSxIDoge2theW5hay5wYXRoLmxzdHJpcCgnLycpfSBAIHtrYXluYWsuaG9z'
        'dG5hbWUgb3IgJ3llcmVsJ30iKQpwcmludChmJyBTw7xyw7xjw7wgICAgIDoge21vdG9y'
        'LmRpYWxlY3QubmFtZX0nKQpwcmludCgpCgoKZGVmIHllZGVrX2FsKCk6CiAgICBpZiBu'
        'b3QgcGc6CiAgICAgICAgcHJpbnQoJyDimqAgUG9zdGdyZVNRTCBkZcSfaWwg4oCUIG90'
        'b21hdGlrIHllZGVrIGF0bGFuZMSxLicpCiAgICAgICAgcmV0dXJuIFRydWUKICAgIGhl'
        'ZGVmID0gUGF0aC5ob21lKCkgLyAneWVkZWtsZXInCiAgICBoZWRlZi5ta2RpcihleGlz'
        'dF9vaz1UcnVlKQogICAgZG9zeWEgPSBoZWRlZiAvIGYna2YxLW9uY2VzaS17ZGF0ZXRp'
        'bWUubm93KCk6JVklbSVkXyVIJU0lU30uZHVtcCcKICAgIHRyeToKICAgICAgICBvcnRh'
        'bSA9IGRpY3Qob3MuZW52aXJvbikKICAgICAgICBpZiBrYXluYWsucGFzc3dvcmQ6CiAg'
        'ICAgICAgICAgIG9ydGFtWydQR1BBU1NXT1JEJ10gPSBrYXluYWsucGFzc3dvcmQKICAg'
        'ICAgICBzID0gc3VicHJvY2Vzcy5ydW4oCiAgICAgICAgICAgIFsncGdfZHVtcCcsICct'
        'RmMnLCAnLWYnLCBzdHIoZG9zeWEpLAogICAgICAgICAgICAgJy1oJywga2F5bmFrLmhv'
        'c3RuYW1lIG9yICdsb2NhbGhvc3QnLAogICAgICAgICAgICAgJy1wJywgc3RyKGtheW5h'
        'ay5wb3J0IG9yIDU0MzIpLAogICAgICAgICAgICAgJy1VJywga2F5bmFrLnVzZXJuYW1l'
        'IG9yICdwb3N0Z3JlcycsCiAgICAgICAgICAgICBrYXluYWsucGF0aC5sc3RyaXAoJy8n'
        'KV0sCiAgICAgICAgICAgIGVudj1vcnRhbSwgY2FwdHVyZV9vdXRwdXQ9VHJ1ZSwgdGV4'
        'dD1UcnVlLCB0aW1lb3V0PTYwMCkKICAgICAgICBpZiAocy5yZXR1cm5jb2RlICE9IDAg'
        'b3Igbm90IGRvc3lhLmV4aXN0cygpCiAgICAgICAgICAgICAgICBvciBkb3N5YS5zdGF0'
        'KCkuc3Rfc2l6ZSA8IDEwMjQpOgogICAgICAgICAgICBwcmludCgnIOKclyBZZWRlayBB'
        'TElOQU1BREkg4oCUIGfDtsOnIMSwUFRBTCBlZGlsZGkuJykKICAgICAgICAgICAgcHJp'
        'bnQoZicgICB7KHMuc3RkZXJyIG9yICIiKS5zdHJpcCgpWzoyMDBdfScpCiAgICAgICAg'
        'ICAgIHJldHVybiBGYWxzZQogICAgICAgIHByaW50KGYnIOKckyB7ZG9zeWF9ICAoe2Rv'
        'c3lhLnN0YXQoKS5zdF9zaXplIC8gMTAyNDouMGZ9IEtCKScpCiAgICAgICAgcmV0dXJu'
        'IFRydWUKICAgIGV4Y2VwdCBGaWxlTm90Rm91bmRFcnJvcjoKICAgICAgICBwcmludCgn'
        'IOKclyBwZ19kdW1wIGJ1bHVuYW1hZMSxIOKAlCBnw7bDpyDEsFBUQUwgZWRpbGRpLicp'
        'CiAgICAgICAgcmV0dXJuIEZhbHNlCiAgICBleGNlcHQgc3VicHJvY2Vzcy5UaW1lb3V0'
        'RXhwaXJlZDoKICAgICAgICBwcmludCgnIOKclyBZZWRlayB6YW1hbiBhxZ/EsW3EsW5h'
        'IHXEn3JhZMSxIOKAlCBnw7bDpyDEsFBUQUwgZWRpbGRpLicpCiAgICAgICAgcmV0dXJu'
        'IEZhbHNlCgoKIyDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZAKIyAgw5ZOS0/FnlVMOiB5ZW5pIMWfZW1hIGHDp8SxbMSx'
        'xZ90YSBrdXJ1bG11xZ8gb2xtYWzEsQojIOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkAp0YWJsb2xhciA9IHNldChkZW5l'
        'dGNpLmdldF90YWJsZV9uYW1lcygpKQppZiAna3VsbGFuaWNpbGFyJyBub3QgaW4gdGFi'
        'bG9sYXIgb3IgJ2Zpcm1hJyBub3QgaW4gdGFibG9sYXI6CiAgICBwcmludCgnIOKclyBg'
        'a3VsbGFuaWNpbGFyYCB5YSBkYSBgZmlybWFgIHRhYmxvc3UgeW9rIOKAlCB5YW5sxLHF'
        'nycpCiAgICBwcmludCgnICAgdmVyaXRhYmFuxLFuYSBiYcSfbGFubcSxxZ8gb2xhYmls'
        'aXJpbS4gRHVydXlvcnVtLicpCiAgICBzeXMuZXhpdCgxKQoKa19zdXR1biA9IHtzWydu'
        'YW1lJ10gZm9yIHMgaW4gZGVuZXRjaS5nZXRfY29sdW1ucygna3VsbGFuaWNpbGFyJyl9'
        'CmZfc3V0dW4gPSB7c1snbmFtZSddIGZvciBzIGluIGRlbmV0Y2kuZ2V0X2NvbHVtbnMo'
        'J2Zpcm1hJyl9Cgpla3NpayA9IFtdCmlmICdrdWxsYW5pY2lfZmlybWEnIG5vdCBpbiB0'
        'YWJsb2xhcjoKICAgIGVrc2lrLmFwcGVuZCgna3VsbGFuaWNpX2Zpcm1hIHRhYmxvc3Un'
        'KQppZiAnZmlybWFfa2Fwc2FtJyBub3QgaW4ga19zdXR1bjoKICAgIGVrc2lrLmFwcGVu'
        'ZCgna3VsbGFuaWNpbGFyLmZpcm1hX2thcHNhbSBzw7x0dW51JykKaWYgZWtzaWs6CiAg'
        'ICBwcmludCgnIOKclyBZRU7EsCDFnkVNQSBIRU7DnFogS1VSVUxNQU1JxZ46JykKICAg'
        'IGZvciBlIGluIGVrc2lrOgogICAgICAgIHByaW50KGYnICAgICB7ZX0nKQogICAgcHJp'
        'bnQoKQogICAgcHJpbnQoJyAgIEJ1bmxhcsSxIHV5Z3VsYW1hbsSxbiBBw4dJTEnFnkkg'
        'a3VydXlvciAoZGIuY3JlYXRlX2FsbCB5ZW5pJykKICAgIHByaW50KCcgICB0YWJsb3l1'
        'LCBTRDIgeWVuaSBzw7x0dW51IGVrbGl5b3IpLiBTxLFyYSDFn3U6JykKICAgIHByaW50'
        'KCkKICAgIHByaW50KCcgICAgIHB5dGhvbjMgeWFtYV9rZjEucHkgLS11eWd1bGEnKQog'
        'ICAgcHJpbnQoJyAgICAgc3VkbyBzeXN0ZW1jdGwgcmVzdGFydCBtaWxlc3RvbmUtZXJw'
        'JykKICAgIHByaW50KCcgICAgIHZlbnYvYmluL3B5dGhvbiBnb2Nfa2YxLnB5IC0tdXln'
        'dWxhICAgICAg4oaQIHNvbnJhIGJlbicpCiAgICBwcmludCgpCiAgICBwcmludCgnICAg'
        'QnUgYmV0aWsgb25sYXLEsSBLVVJNVVlPUiwgYmlsZXJlazogYHZhcnNheWlsYW5gJykK'
        'ICAgIHByaW50KCcgICBzw7x0dW51bnUgZMO8xZ/DvHLDvHlvciB2ZSB5ZW5pZGVuIGJh'
        'xZ9sYXTEsWxtYW3EscWfIHNpc3RlbWRlJykKICAgIHByaW50KCcgICBFU0vEsCBLT0Qg'
        'byBzw7x0dW51IGjDomzDoiBva3V5b3Ig4oCUIGTDvMWfw7xybWVrIMOnYWzEscWfYW4n'
        'KQogICAgcHJpbnQoJyAgIHV5Z3VsYW1hecSxIGvEsXJhcmTEsS4nKQogICAgc3lzLmV4'
        'aXQoMSkKCnByaW50KCcg4pyTIHllbmkgxZ9lbWEgeWVyaW5kZSAoa3VsbGFuaWNpX2Zp'
        'cm1hICsgZmlybWFfa2Fwc2FtKScpCnByaW50KCkKCiMg4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCiMgIERVUlVNCiMg'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQCndpdGggbW90b3IuY29ubmVjdCgpIGFzIGI6CiAgICBrdWxsYW5pY2lsYXIg'
        'PSBiLmV4ZWN1dGUodGV4dCgKICAgICAgICAnU0VMRUNUIGlkLCBhZCwgcm9sLCBmaXJt'
        'YV9rYXBzYW0gRlJPTSBrdWxsYW5pY2lsYXIgT1JERVIgQlkgaWQnCiAgICApKS5mZXRj'
        'aGFsbCgpCiAgICBmaXJtYWxhciA9IGIuZXhlY3V0ZSh0ZXh0KAogICAgICAgICdTRUxF'
        'Q1QgaWQsIGFkIEZST00gZmlybWEgT1JERVIgQlkgaWQnKSkuZmV0Y2hhbGwoKQogICAg'
        'aXppbl9uID0gYi5leGVjdXRlKHRleHQoCiAgICAgICAgJ1NFTEVDVCBDT1VOVCgqKSBG'
        'Uk9NIGt1bGxhbmljaV9maXJtYScpKS5zY2FsYXIoKSBvciAwCgp2YXJzYXlpbGFuX3Zh'
        'ciA9ICd2YXJzYXlpbGFuJyBpbiBmX3N1dHVuCmthcHNhbXNpeiA9IFtrIGZvciBrIGlu'
        'IGt1bGxhbmljaWxhciBpZiAoa1szXSBvciAnJykgIT0gJ3R1bXUnXQoKcHJpbnQoJ+KU'
        'gCcgKiA3MCkKcHJpbnQoJyBEVVJVTScpCnByaW50KCfilIAnICogNzApCnByaW50KGYn'
        'ICAgZmlybWEgICAgICAgICAgICA6IHtsZW4oZmlybWFsYXIpfScpCmZvciBmIGluIGZp'
        'cm1hbGFyOgogICAgcHJpbnQoZicgICAgICAgW3tmWzBdfV0ge2ZbMV19JykKcHJpbnQo'
        'ZicgICBrdWxsYW7EsWPEsSAgICAgICAgOiB7bGVuKGt1bGxhbmljaWxhcil9JykKZm9y'
        'IGsgaW4ga3VsbGFuaWNpbGFyOgogICAgcHJpbnQoZiIgICAgICAgW3trWzBdfV0ge2tb'
        'MV06PDE0fSB7a1syXSBvciAn4oCUJzo8MTB9ICIKICAgICAgICAgIGYia2Fwc2FtOiB7'
        'a1szXSBvciAnKGJvxZ8pJ30iKQpwcmludChmJyAgIGZpcm1hIGl6bmkgc2F0xLFyxLE6'
        'IHtpemluX259JykKcHJpbnQoZiIgICBmaXJtYS52YXJzYXlpbGFuIDogeydWQVIg4oaS'
        'IGTDvMWfw7xyw7xsZWNlaycgaWYgdmFyc2F5aWxhbl92YXIgZWxzZSAneW9rIChkw7zF'
        'n8O8csO8bG3DvMWfKSd9IikKCnByaW50KCkKcHJpbnQoJ+KUgCcgKiA3MCkKcHJpbnQo'
        'JyBZQVBJTEFDQUsnKQpwcmludCgn4pSAJyAqIDcwKQppc192YXIgPSBGYWxzZQoKaWYg'
        'a2Fwc2Ftc2l6OgogICAgaXNfdmFyID0gVHJ1ZQogICAgcHJpbnQoZicgICAxKSB7bGVu'
        'KGthcHNhbXNpeil9IGt1bGxhbsSxY8SxeWEgZmlybWFfa2Fwc2FtID0gInR1bXUiIHlh'
        'esSxbGFjYWs6JykKICAgIGZvciBrIGluIGthcHNhbXNpejoKICAgICAgICBwcmludChm'
        'IiAgICAgICAgW3trWzBdfV0ge2tbMV19ICAoe2tbM10gb3IgJ2JvxZ8nfSDihpIgdHVt'
        'dSkiKQogICAgcHJpbnQoKQogICAgcHJpbnQoJyAgICAgIFNFQkVQOiBtb2RlbGRla2kg'
        'dmFyc2F5xLFsYW4gInNlY2lsaSIgdmUgaXppbiB0YWJsb3N1JykKICAgIHByaW50KCcg'
        'ICAgICBib8WfLiBEb2t1bnVsbWF6c2EgecO8a3NlbHRtZWRlbiBzb25yYSBhZG1pbiBv'
        'bG1heWFuJykKICAgIHByaW50KCcgICAgICBIxLDDhyBLxLBNU0Ugc2lzdGVtZSBnaXJl'
        'bWV6IOKAlCBrYXBzYW3EsSAic2VjaWxpIiwgYXRhbm3EscWfJykKICAgIHByaW50KCcg'
        'ICAgICBmaXJtYXPEsSB5b2suIFnDvGtzZWx0bWUga2ltc2VuaW4gZXJpxZ9pbWluaSBz'
        'ZXNzaXpjZScpCiAgICBwcmludCgnICAgICAga2VzbWVtZWxpOyBkYXJhbHRtYSBrYXJh'
        'csSxIHNlbmluIChBeWFybGFyIOKGkicpCiAgICBwcmludCgnICAgICAgS3VsbGFuxLFj'
        'xLFsYXIg4oaSIGZpcm1hIGthcHNhbcSxKS4nKQplbHNlOgogICAgcHJpbnQoJyAgIDEp'
        'IOKckyBiw7x0w7xuIGt1bGxhbsSxY8SxbGFyxLFuIGthcHNhbcSxIHphdGVuICJ0dW11'
        'IicpCgppZiB2YXJzYXlpbGFuX3ZhcjoKICAgIGlzX3ZhciA9IFRydWUKICAgIHByaW50'
        'KCkKICAgIHByaW50KCcgICAyKSBgZmlybWEudmFyc2F5aWxhbmAgc8O8dHVudSBEw5zF'
        'nsOcUsOcTEVDRUsgIOKaoCBnZXJpIGFsxLFuYW1heicpCiAgICBwcmludCgnICAgICAg'
        'QmF5cmFrIGthbGTEsXLEsWxkxLE7IGt1bGxhbsSxY8Sxc8SxeiB5b2xsYXLEsW4gw6dh'
        'cGFzxLEgYXJ0xLFrJykKICAgIHByaW50KCcgICAgICBlbiBrw7zDp8O8ayBraW1saWts'
        'aSBmaXJtYS4gU8O8dHVudSB2ZXJpdGFiYW7EsW5kYScpCiAgICBwcmludCgnICAgICAg'
        'YsSxcmFrbWFrLCBtb2RlbGRlIG9sbWF5YW4gYmlyIHPDvHR1biBixLFyYWttYWsgb2x1'
        'cmR1JykKICAgIHByaW50KCcgICAgICB2ZSBzZW1hX2RlbmV0aW0gZmF6bGEgc8O8dHVu'
        'dSBnw7ZyZW1peW9yLicpCmVsc2U6CiAgICBwcmludCgnICAgMikg4pyTIGBmaXJtYS52'
        'YXJzYXlpbGFuYCB6YXRlbiBkw7zFn8O8csO8bG3DvMWfJykKCmlmIG5vdCBpc192YXI6'
        'CiAgICBwcmludCgpCiAgICBwcmludCgn4pWQJyAqIDcwKQogICAgcHJpbnQoJyDiipkg'
        'WWFwxLFsYWNhayBpxZ8geW9rIOKAlCBnw7bDpyBLRjEgemF0ZW4gdXlndWxhbm3EscWf'
        'LicpCiAgICBwcmludCgn4pWQJyAqIDcwKQogICAgc3lzLmV4aXQoMCkKCmlmIG5vdCBV'
        'WUdVTEE6CiAgICBwcmludCgpCiAgICBwcmludCgn4pWQJyAqIDcwKQogICAgcHJpbnQo'
        'JyBSQVBPUiBNT0RVIOKAlCBoacOnYmlyIMWfZXkgZGXEn2nFn21lZGkuJykKICAgIHBy'
        'aW50KCkKICAgIHByaW50KCcgVXlndWxhbWFrIGnDp2luOicpCiAgICBwcmludCgnICAg'
        'dmVudi9iaW4vcHl0aG9uIGdvY19rZjEucHkgLS11eWd1bGEnKQogICAgcHJpbnQoJ+KV'
        'kCcgKiA3MCkKICAgIHN5cy5leGl0KDApCgojIOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkAojICBZRURFSwojIOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kApwcmludCgpCnByaW50KCfilIAnICogNzApCnByaW50KCcgWUVERUsnKQpwcmludCgn'
        '4pSAJyAqIDcwKQppZiBub3QgeWVkZWtfYWwoKToKICAgIHN5cy5leGl0KDEpCgojIOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkAojICBVWUdVTEEgKHRlayB0cmFuc2FjdGlvbikKIyDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZAKcHJpbnQoKQpw'
        'cmludCgn4pSAJyAqIDcwKQpwcmludCgnIFVZR1VMQU5JWU9SJykKcHJpbnQoJ+KUgCcg'
        'KiA3MCkKdHJ5OgogICAgd2l0aCBtb3Rvci5iZWdpbigpIGFzIGI6CiAgICAgICAgaWYg'
        'a2Fwc2Ftc2l6OgogICAgICAgICAgICBzID0gYi5leGVjdXRlKHRleHQoCiAgICAgICAg'
        'ICAgICAgICAiVVBEQVRFIGt1bGxhbmljaWxhciBTRVQgZmlybWFfa2Fwc2FtID0gJ3R1'
        'bXUnICIKICAgICAgICAgICAgICAgICJXSEVSRSBmaXJtYV9rYXBzYW0gSVMgTlVMTCBP'
        'UiBmaXJtYV9rYXBzYW0gPD4gJ3R1bXUnIikpCiAgICAgICAgICAgIHByaW50KGYiICAg'
        '4pyTIHtnZXRhdHRyKHMsICdyb3djb3VudCcsIDApfSBrdWxsYW7EsWPEsSDihpIgJ3R1'
        'bXUnIikKICAgICAgICBpZiB2YXJzYXlpbGFuX3ZhcjoKICAgICAgICAgICAgIyBTUUxp'
        'dGUgMy4zNSsgdmUgUG9zdGdyZVNRTCBpa2lzaSBkZSBEUk9QIENPTFVNTiBkZXN0ZWts'
        'ZXIuCiAgICAgICAgICAgIGIuZXhlY3V0ZSh0ZXh0KCdBTFRFUiBUQUJMRSBmaXJtYSBE'
        'Uk9QIENPTFVNTiB2YXJzYXlpbGFuJykpCiAgICAgICAgICAgIHByaW50KCcgICDinJMg'
        'ZmlybWEudmFyc2F5aWxhbiBkw7zFn8O8csO8bGTDvCcpCmV4Y2VwdCBFeGNlcHRpb24g'
        'YXMgZToKICAgIHByaW50KGYnICAg4pyXIEfDlsOHIEJBxZ5BUklTSVog4oCUIGhpw6di'
        'aXIgxZ9leSBkZcSfacWfbWVkaTpcbiAgICAge2V9JykKICAgIHN5cy5leGl0KDEpCgoj'
        'IOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkAojICBET8SeUlVMQU1BCiMg4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCnByaW50KCkKcHJpbnQoJ+KUgCcg'
        'KiA3MCkKcHJpbnQoJyBET8SeUlVMQU1BJykKcHJpbnQoJ+KUgCcgKiA3MCkKaGF0YWxp'
        'ID0gRmFsc2UKZGVuZXRjaTIgPSBpbnNwZWN0KGNyZWF0ZV9lbmdpbmUoVlRfVVJMKSkK'
        'd2l0aCBtb3Rvci5jb25uZWN0KCkgYXMgYjoKICAgIF9rYXBzYW1zaXogPSBiLmV4ZWN1'
        'dGUodGV4dCgKICAgICAgICAiU0VMRUNUIENPVU5UKCopIEZST00ga3VsbGFuaWNpbGFy'
        'ICIKICAgICAgICAiV0hFUkUgZmlybWFfa2Fwc2FtIElTIE5VTEwgT1IgZmlybWFfa2Fw'
        'c2FtIDw+ICd0dW11JyIpKS5zY2FsYXIoKSBvciAwCiAgICBfbiA9IGIuZXhlY3V0ZSh0'
        'ZXh0KCdTRUxFQ1QgQ09VTlQoKikgRlJPTSBrdWxsYW5pY2lsYXInKSkuc2NhbGFyKCkg'
        'b3IgMAogICAgaWYgX2thcHNhbXNpejoKICAgICAgICBwcmludChmJyAgIOKclyB7X2th'
        'cHNhbXNpen0ga3VsbGFuxLFjxLFuxLFuIGthcHNhbcSxIGjDomzDoiAidHVtdSIgZGXE'
        'n2lsJykKICAgICAgICBoYXRhbGkgPSBUcnVlCiAgICBlbHNlOgogICAgICAgIHByaW50'
        'KGYnICAg4pyTIHtfbn0ga3VsbGFuxLFjxLFuxLFuIGhlcHNpICJ0dW11IiDigJQga2lt'
        'c2Uga2lsaXRsZW5tZWRpJykKCl9mMiA9IHtzWyduYW1lJ10gZm9yIHMgaW4gZGVuZXRj'
        'aTIuZ2V0X2NvbHVtbnMoJ2Zpcm1hJyl9CmlmICd2YXJzYXlpbGFuJyBpbiBfZjI6CiAg'
        'ICBwcmludCgnICAg4pyXIGZpcm1hLnZhcnNheWlsYW4gaMOibMOiIGR1cnV5b3InKQog'
        'ICAgaGF0YWxpID0gVHJ1ZQplbHNlOgogICAgcHJpbnQoJyAgIOKckyBmaXJtYS52YXJz'
        'YXlpbGFuIGTDvMWfw7xyw7xsbcO8xZ8nKQoKIyBGaXJtYSBzYXnEsXPEsSBkZcSfacWf'
        'bWVtZWxpOiBidSBnw7bDpyBmaXJtYSBrYXlkxLFuYSBET0tVTk1VWU9SLgp3aXRoIG1v'
        'dG9yLmNvbm5lY3QoKSBhcyBiOgogICAgX2ZuID0gYi5leGVjdXRlKHRleHQoJ1NFTEVD'
        'VCBDT1VOVCgqKSBGUk9NIGZpcm1hJykpLnNjYWxhcigpIG9yIDAKaWYgX2ZuICE9IGxl'
        'bihmaXJtYWxhcik6CiAgICBwcmludChmJyAgIOKclyBmaXJtYSBzYXnEsXPEsSBkZcSf'
        'acWfdGk6IHtsZW4oZmlybWFsYXIpfSDihpIge19mbn0nKQogICAgaGF0YWxpID0gVHJ1'
        'ZQplbHNlOgogICAgcHJpbnQoZicgICDinJMge19mbn0gZmlybWEga29ydW5kdSAoYnUg'
        'Z8O2w6cgZmlybWF5YSBkb2t1bm1heiknKQoKcHJpbnQoKQpwcmludCgn4pWQJyAqIDcw'
        'KQppZiBoYXRhbGk6CiAgICBwcmludCgnIOKclyBET8SeUlVMQU1BIEJBxZ5BUklTSVog'
        '4oCUIHllZGVrdGVuIGTDtm5tZXlpIGRlxJ9lcmxlbmRpcmluLicpCiAgICBzeXMuZXhp'
        'dCgxKQpwcmludCgnIOKckyBHw5bDhyBLRjEgVEFNQU1MQU5ESScpCnByaW50KCkKcHJp'
        'bnQoJyDFnnUgYW4gSEVSS0VTxLBOIGthcHNhbcSxICJ0w7xtIGZpcm1hbGFyIiDigJQg'
        'ecO8a3NlbHRtZSBraW1zZW5pbicpCnByaW50KCcgZXJpxZ9pbWluaSBrZXNtZWRpLiBE'
        'YXJhbHRtYWsgacOnaW46JykKcHJpbnQoJyAgIEF5YXJsYXIg4oaSIEt1bGxhbsSxY8Sx'
        'bGFyIOKGkiBrdWxsYW7EsWPEsXnEsSBkw7x6ZW5sZSDihpInKQpwcmludCgnICAgZmly'
        'bWEga2Fwc2FtxLEgInNlw6dpbGkgZmlybWFsYXIiIOKGkiBrdXR1bGFyxLEgacWfYXJl'
        'dGxlJykKcHJpbnQoKQpwcmludCgnIFNPTlJBS8SwIEFESU06JykKcHJpbnQoJyAgIHZl'
        'bnYvYmluL3B5dGhvbiBmaXJtYV9kZW5ldGltLnB5JykKcHJpbnQoJ+KVkCcgKiA3MCkK'
    ),
}


def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA KF — COKLU FIRMA TUM KULLANICILARA')
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
        print('    python3 yama_kf.py            # rapor')
        print('    python3 yama_kf.py --uygula')
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

        # Söz dizimi doğrulaması: bozuk bir denetim aracı push
        # kapısını kilitler.
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
        print('  ⊙ Yama KF zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_kf.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_kf'
            shutil.copy2(yol, yedek)
            _y = f'    yedek  : {os.path.relpath(yedek, KOK)}'
        else:
            _y = '    (yeni dosya — yedek yok)'
        with open(yol, 'w', encoding='utf-8', newline='') as f:
            f.write(icerik)
        if yol.endswith('.sh'):
            os.chmod(yol, 0o755)
        print(f'  ✓ yazıldı: {os.path.relpath(yol, KOK)}')
        print(_y)

    print('\n  ✓ YAMA UYGULANDI')
    print()
    print('  ══ SIRA ONEMLI ══')
    print()
    print('    1) sudo systemctl restart milestone-erp')
    print('       Yeni tablo ve sutun ACILISTA kuruluyor.')
    print()
    print('    2) venv/bin/python goc_kf1.py            # RAPOR')
    print('       venv/bin/python goc_kf1.py --uygula')
    print('       Mevcut kullanicilarin HEPSINE firma kapsami "tumu"')
    print('       verir — yukseltme kimsenin erisimini kesmesin —')
    print('       ve firma.varsayilan sutununu dusurur.')
    print()
    print('       Gocu once calistirirsan kendisi durur ve sirayi')
    print('       yazar; tahmin etmesi gerekmiyor.')
    print()
    print('    3) venv/bin/python firma_denetim.py       # F1-F6')
    print('       venv/bin/python -m pytest tests/test_kritik.py -q')
    print()
    print('    4) Tarayicida Ctrl+F5, sonra')
    print('       Ayarlar -> Kullanicilar -> firma kapsamini daralt')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA YP — YÖNETİM PANELİ: FİRMA ÜSTÜ İŞLER AYRI SAYFADA
========================================================

ÖNKOŞUL: yama_kf.py, yama_kf5.py ve yama_kf6.py uygulanmış olmalı.

── NEDEN ──
  Firma açmak/silmek, kullanıcı açmak/silmek ve yetki vermek bir
  firmaya AİT DEĞİL; sisteme ait. Bugüne kadar Ayarlar'ın içindeydiler
  ve Ayarlar bir firmanın İÇİNDE açılıyor: banner bir firma gösteriyor,
  süzgeç çalışıyor, kimlik formu "aktif firmayı" düzenliyor.

  Uyumsuzluk soyut değildi, can yaktı: MF3B'de A firmasının
  ayarlarındayken B eklenebiliyor, hemen altındaki form ise hâlâ
  A'yı düzenliyordu. Bir firmayı silmek için de önce BAŞKA bir
  firmaya geçmek gerekiyor ("içinde bulunduğun firmayı silemezsin").

── AYRIM ÖLÇÜTÜ ──
  "Bu ayar bir firmaya mı ait, sisteme mi?" — cevabı veri modeli
  veriyor: TABLOSU `firma_id` TAŞIYOR MU?

    taşımıyor → sisteme ait → Yönetim paneline
        kullanicilar · firma · yedekler (bütün veritabanı)

    taşıyor   → o firmaya ait → Ayarlar'da kalır
        banka (firma_id NOT NULL) · veriler/listeler (firma_id)
        firma kimliği (ünvan, logo, belge kodu, SMTP, KDV)

── SONUÇ ──
    /yonetim  → Kullanıcılar · Firmalar · Yedekleme
    /ayarlar  → Firma Bilgileri · E-posta · Listeler · Bankalar

  Panel firma seçmeden açılıyor (seçim kapısı muaf tutuyor) —
  varlık sebebi bu. İçeri girince oturumdaki firma seçimi KORUNUYOR;
  panelden çıkınca kullanıcı kaldığı firmaya döner.

  Bağlantısı iki yerde: sol raydaki Sistem menüsünde (admin'e
  görünür) ve FİRMA SEÇİM EKRANINDA — kullanıcı açmak için rastgele
  bir firmaya girmek gerekmesin.

── NASIL TAŞINDI: TEK ŞABLON, İKİ YÜZ ──
  Bölümleri kesip ikinci bir dosyaya kopyalamadım. İki sebep:

    1. 19 KB'lık HTML ve onunla iç içe geçmiş JS'i bölmek, kazancından
       çok risk taşıyordu.
    2. MÜKERRER PANEL bu projede çoktan can yaktı — MF4'te iki
       `yedekGovde` yüzünden yedek listesi boş görünüyordu, diskte 30
       yedek varken.

  Bunun yerine aynı şablon iki rotaya hizmet ediyor ve `PANEL`
  değişkeni hangi sekmelerin BASILACAĞINI seçiyor. İkizlenme böylece
  YAPISAL OLARAK imkânsız: her bölüm yalnızca bir sayfada basılıyor.
  Testler bunu ölçüyor (test_yp_paneller_ikizlenmemis).

── SIFIRLAMA PANELE GELMEDİ, BİLEREK ──
  `sifirla2.py` pg_dump alıp geri alınamaz silme yapıyor ve kendi
  doğrulamasını koşturuyor. Web düğmesinin arkasına koymak, yanlışlıkla
  basılabilecek bir yere koymak olurdu. CLI'da kalıyor.

── YOL ÜSTÜNDE ──
  · "Firma" sekmesi İKİYE bölündü: `firmalar` (sistem, panelde) ve
    `firma` (aktif firmanın kimliği, Ayarlar'da). Yükleyici haritası
    da ikiye ayrıldı — MF3B'de bu haritaya bağlamayı unutmak tabloyu
    "Yükleniyor…"da bırakmıştı.
  · Açılışta yüklenecek sekme SABİT `kullanici` yazılıydı; Ayarlar'da
    o sekme artık yok. Artık açık olan sekme neyse o yükleniyor.
  · Ayarlar'ın alt başlığında, admin'e Yönetim paneline bağlantı var:
    alışkanlıkla oraya giden boşluk bulmasın.
  · KENDİ HATAM: açıklama yorumuna örnek olsun diye şablon etiketi
    yazmıştım. Jinja JS yorumunun içinde olduğunu bilmiyor; etiketi
    ayrıştırıp sayfayı TemplateSyntaxError'a düşürdü. Yorumlarda
    şablon etiketi yazmamak gerekiyor.

── ÖLÇÜLDÜ ──
  /yonetim  200 · sekmeler [Kullanıcılar, Firmalar, Yedekleme]
            kullaniciGovde · firmaGovde · yedekGovde  birer kez
  /ayarlar  200 · sekmeler [Firma Bilgileri, E-posta, Listeler, Bankalar]
            fFirma · bankaGovde · lookupIzgara        birer kez
  örtüşme   YOK — hiçbir bileşen iki sayfada birden değil
  admin olmayan /yonetim  → 302 (yönlendirildi)
  firma SEÇMEDEN /yonetim → 200

  99 test geçti (94 + 5 yeni kalıcı test);
  js · form · zincir · akis · sema · firma temiz.

  EKSİK KALAN: panelin EKRAN GÖRÜNTÜSÜNÜ alamadım. Dört deneme de
  harness sorunlarına takıldı (statik yollar, sunucu yarışı, sayfanın
  kendi JS'inin /cikis'e yönlendirmesi, imzalı oturum çerezinin kabul
  edilmemesi). Yapı ve davranış yukarıdaki ölçümlerle doğrulandı ama
  "göze nasıl geliyor"u sen göreceksin — bozuk bir şey varsa söyle.

DOSYALAR
--------
  flask_app.py              /yonetim rotası · kapı muafiyeti · PANEL
  templates/ayarlar.html    sekme/bölüm ayrımı · yükleyici · başlık
  templates/base.html       sol rayda Yönetim girişi
  templates/firma_sec.html  firmaya girmeden panele bağlantı
  tests/test_kritik.py      5 yeni test

Şema yok, göç yok.

KULLANIM
--------
  python3 yama_yp.py            # RAPOR
  python3 yama_yp.py --uygula
  sudo systemctl restart milestone-erp
  (tarayıcıda Ctrl+F5)
"""

import os
import py_compile
import shutil
import subprocess
import sys
import tempfile

UYGULA = '--uygula' in sys.argv
KOK = os.path.dirname(os.path.abspath(__file__))

DOSYA_IMZA = {
    'flask_app.py': 'def yonetim_sayfa',
    'templates/ayarlar.html': "SEKMELER ROTAYA GÖRE (YP2)",
    'templates/base.html': 'YP1: Yönetim paneli',
    'templates/firma_sec.html': 'YP1 · YÖNETİM PANELİ',
    'tests/test_kritik.py': 'def test_yp_panel_firma_secmeden_acilir',
}
ONKOSUL = {
    'flask_app.py': '_firma_secim_guard',
    'templates/ayarlar.html': 'FİRMA KAPSAMI (KF3)',
    'templates/base.html': 'KF2: çip artık HERKESTE seçilebilir',
    'templates/firma_sec.html': 'KF2: yeni firma açmak admin işi',
    'tests/test_kritik.py': 'def test_kf2_firmasiz_kullanici_giremez',
}

DEGISIKLIKLER = [
    ('flask_app.py', 'YP · flask_app.py blok 1',
     r'''        return render_template('raporlar.html')

''',
     r'''        return render_template('raporlar.html')

    @app.route('/yonetim')
    def yonetim_sayfa():
        """YÖNETİM PANELİ — firma ÜSTÜ işler (YP1).

        Firma ekle/sil, kullanıcı ekle/sil, yetkiler ve yedekler
        bir firmaya AİT DEĞİL; sisteme ait. Bugüne kadar Ayarlar'ın
        içindeydiler ve Ayarlar bir firmanın içinde açılıyor: banner
        bir firma gösteriyor, süzgeç çalışıyor, kimlik formu "aktif
        firmayı" düzenliyor. Uyumsuzdu ve can yaktı — MF3B'de
        A firmasının ayarlarındayken B eklenebiliyor, hemen
        altındaki form ise hâlâ A'yı düzenliyordu.
        
        Burası firma bağlamının DIŞINDA: firma seçmeden açılabiliyor
        (seçim kapısı bu yolu muaf tutuyor) ve içeri girildiğinde
        oturumdaki firma seçimi KORUNUYOR — panelden çıkınca
        kullanıcı kaldığı firmaya döner.

        AYRIM ÖLÇÜTÜ — "bu ayar bir firmaya mı ait, sisteme mi":
        tablosu `firma_id` taşıyorsa firmaya aittir ve Ayarlar'da
        kalır (banka, veriler/listeler, firma kimliği). Taşımıyorsa
        sisteme aittir ve buraya gelir (kullanicilar, firma).

        SIFIRLAMA BURAYA GELMEDİ, bilerek: `sifirla2.py` pg_dump
        alıp geri alınamaz silme yapıyor ve kendi doğrulamasını
        koşturuyor. Web düğmesinin arkasına koymak, yanlışlıkla
        basılabilecek bir yere koymak olurdu.
        """
        if _auth_required():
            return _auth_required()
        # Yalnızca ADMIN. Yetki haritasına bağlamıyoruz: burada
        # yapılan işler (kullanıcı açmak, yetki vermek, firma
        # silmek) yetkinin KENDİSİNİ belirliyor.
        if (session.get('rol') or '').upper() != 'ADMIN':
            return redirect(url_for('dashboard'))
        # YP2: AYNI ŞABLON, farklı yüz. Panelleri ikinci bir
        # dosyaya kopyalamak bu projede çoktan can yaktı (MF4'te
        # mükerrer `yedekGovde` yedek listesini boş gösteriyordu).
        # `PANEL` değişkeni hangi sekmelerin basılacağını seçiyor;
        # her bölüm yalnızca BİR sayfada basıldığı için ikizlenme
        # yapısal olarak imkânsız.
        return render_template('ayarlar.html', alt_yetkiler=ALT_YETKILER,
                               PANEL='yonetim')

'''),
    ('flask_app.py', 'YP · flask_app.py blok 2',
     r'''            return redirect(url_for('dashboard'))
        return render_template('ayarlar.html', alt_yetkiler=ALT_YETKILER)
''',
     r'''            return redirect(url_for('dashboard'))
        return render_template('ayarlar.html', alt_yetkiler=ALT_YETKILER,
                               PANEL='ayarlar')
'''),
    ('flask_app.py', 'YP · flask_app.py blok 3',
     r'''        '/giris', '/cikis', '/static/', '/favicon', '/saglik',
''',
     r'''        '/giris', '/cikis', '/static/', '/favicon', '/saglik',
        # ── YP1 · YÖNETİM PANELİ ──
        # Panelin varlık sebebi "herhangi bir firmaya girmeden
        # yönetmek". Kapı burayı da durdursaydı panel yalnızca
        # firma seçtikten sonra açılırdı ve hiçbir işe yaramazdı.
        # Sakıncası yok: paneldeki uçların hepsi ADMIN şartı arıyor
        # ve hiçbiri firmaya bağlı veri okumuyor.
        '/yonetim', '/api/ayarlar/kullanici', '/api/yedek',
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 1',
     r'''{% extends "base.html" %}
{% block title %}Ayarlar{% endblock %}
''',
     r'''{% extends "base.html" %}
{% block title %}{{ 'Yönetim' if PANEL == 'yonetim' else 'Ayarlar' }}{% endblock %}
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 2',
     r'''{% block content %}
''',
     r'''{% block content %}
{% if PANEL == 'yonetim' %}
<h1 class="g-baslik">Yönetim</h1>
<p class="g-alt">Firma üstü işler: firmalar, kullanıcılar ve yetkiler,
   yedekler. Buradaki hiçbir ayar tek bir firmaya ait değildir —
   o yüzden firma seçmeden de açılır.</p>
{% else %}
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 3',
     r'''<h1 class="g-baslik">Ayarlar</h1>
<p class="g-alt">Kullanıcılar ve yetkiler, firma bilgileri, liste tanımları.</p>
''',
     r'''<h1 class="g-baslik">Ayarlar</h1>
<p class="g-alt">Bu firmanın ayarları: kimlik bilgileri, e-posta,
   liste tanımları, banka hesapları.
   {% if menu_admin %}Firma ve kullanıcı yönetimi
   <a href="/yonetim" style="color:var(--verde);font-weight:600">Yönetim</a>
   panelinde.{% endif %}</p>
{% endif %}
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 4',
     r'''</svg>

''',
     r'''</svg>

{# ── SEKMELER ROTAYA GÖRE (YP2) ──
   Aynı şablon iki sayfaya hizmet ediyor:

     /yonetim  → Kullanıcılar · Firmalar · Yedekleme   (SİSTEM)
     /ayarlar  → Firma Bilgileri · E-posta · Listeler · Bankalar
                                                       (O FİRMA)

   NEDEN AYNI ŞABLON: panelleri kesip ikinci bir dosyaya taşımak
   19 KB'lık HTML ve onunla iç içe geçmiş JS'i bölmek demekti.
   Daha kötüsü, bu projede MÜKERRER PANEL çoktan can yaktı — MF4'te
   iki `yedekGovde` yüzünden yedek listesi boş görünüyordu. Tek
   kaynak, iki yüz: ikizlenme yapısal olarak imkânsız, çünkü her
   bölüm yalnızca bir sayfada BASILIYOR. #}
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 5',
     r'''<div class="sekmeler">
''',
     r'''<div class="sekmeler">
  {% if PANEL == 'yonetim' %}
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 6',
     r'''  <button class="sekme aktif" data-b="kullanici">Kullanıcılar</button>
  <button class="sekme" data-b="firma">Firma</button>
''',
     r'''  <button class="sekme aktif" data-b="kullanici">Kullanıcılar</button>
  <button class="sekme" data-b="firmalar">Firmalar</button>
  <button class="sekme" data-b="yedek">Yedekleme</button>
  {% else %}
  <button class="sekme aktif" data-b="firma">Firma Bilgileri</button>
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 7',
     r'''  <button class="sekme" data-b="banka">Bankalar</button>
  <button class="sekme" data-b="yedek">Yedekleme</button>
''',
     r'''  <button class="sekme" data-b="banka">Bankalar</button>
  {% endif %}
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 8',
     r'''<!-- KULLANICILAR -->
''',
     r'''<!-- KULLANICILAR -->
{% if PANEL == 'yonetim' %}
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 9',
     r'''    <button class="btn-yeni" onclick="kullaniciAc()">+ Yeni Kullanıcı</button>
  </div>
</section>
''',
     r'''    <button class="btn-yeni" onclick="kullaniciAc()">+ Yeni Kullanıcı</button>
  </div>
</section>
{% endif %}
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 10',
     r'''<!-- FİRMA -->
<section class="bolum" id="b-firma">
  <!-- ── FİRMALAR (MF3) ──
       Sistem birden çok tüzel kişilik taşıyabilir. Aşağıdaki "Firma
       Bilgileri" formu AKTİF FİRMAYI düzenler; başka bir firmanın
       bilgisini girmek için önce üst bardan o firmaya geç. -->
''',
     r'''<!-- FİRMA -->
{% if PANEL == 'yonetim' %}
<!-- ── FİRMALAR · SİSTEM DÜZEYİ (YP2) ──
     Firma açmak/silmek bir firmaya AİT DEĞİL, sisteme ait. Bu yüzden
     Yönetim panelinde; Ayarlar'da yalnızca AKTİF FİRMANIN kimliği
     düzenleniyor. Ayrım ölçütü: tablosu `firma_id` taşıyor mu. -->
<section class="bolum aktif" id="b-firmalar">
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 11',
     r'''      Her firmanın stoğu, siparişi, kasası ve defteri ayrıdır.
      Aşağıdaki form <b>aktif firmayı</b> düzenler.</p>
''',
     r'''      Her firmanın stoğu, siparişi, kasası ve defteri ayrıdır.
      Bir firmanın <b>ünvanı, logosu ve belge kodu</b> o firmaya
      geçip Ayarlar → Firma Bilgileri'nden düzenlenir.</p>
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 12',
     r'''    <div id="firmaEkleKutu" style="margin-top:14px"></div>
  </div>
''',
     r'''    <div id="firmaEkleKutu" style="margin-top:14px"></div>
  </div>
</section>
{% endif %}

{% if PANEL != 'yonetim' %}
<section class="bolum" id="b-firma">
  <!-- ── FİRMA BİLGİLERİ ──
       AKTİF FİRMAYI düzenler; başka bir firmanın bilgisini girmek
       için önce üst bardan o firmaya geç. Firma AÇMA/SİLME burada
       DEĞİL, Yönetim panelinde (YP2). -->
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 13',
     r'''      <button class="btn-yeni" onclick="avansKaydet()">Kaydet</button>
    </div>
  </div>
</section>
''',
     r'''      <button class="btn-yeni" onclick="avansKaydet()">Kaydet</button>
    </div>
  </div>
</section>
{% endif %}
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 14',
     r'''<!-- E-POSTA (SMTP) -->
''',
     r'''<!-- E-POSTA (SMTP) -->
{% if PANEL != 'yonetim' %}
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 15',
     r'''    <button class="btn-yeni" onclick="bankaAc()">+ Yeni Banka Hesabı</button>
  </div>
</section>
''',
     r'''    <button class="btn-yeni" onclick="bankaAc()">+ Yeni Banka Hesabı</button>
  </div>
</section>
{% endif %}
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 16',
     r'''
<!-- YEDEKLEME -->
''',
     r'''
<!-- YEDEKLEME · SİSTEM DÜZEYİ: yedek bütün veritabanını kapsıyor,
     bir firmaya ait değil. -->
{% if PANEL == 'yonetim' %}
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 17',
     r'''      </table>
    </div>
  </div>
</section>
''',
     r'''      </table>
    </div>
  </div>
</section>
{% endif %}
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 18',
     r'''const yuklendi = { kullanici: false, firma: false, listeler: false, banka: false, yedek: false };
''',
     r'''const yuklendi = { kullanici: false, firma: false, listeler: false, banka: false, yedek: false };
/* YP2: "firma" sekmesi ikiye ayrıldı — `firmalar` (sistem, Yönetim
   panelinde) ve `firma` (aktif firmanın kimliği, Ayarlar'da). İkisi
   ayrı yükleyici istiyor.

   MF3B notu hâlâ geçerli: firmaListesiYukle yazılmış ama buraya
   bağlanmamıştı ve tablo "Yükleniyor…"da kalıyor, "+ Yeni Firma"
   düğmesi hiç basılmıyordu. Bağlamayı unutmak sessiz bir hata. */
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 19',
     r'''const yukleyici = { kullanici: kullaniciYukle,
                    // MF3B: "firma" sekmesi İKİ şey yükler — firma
                    // bilgisi formu ve FİRMALAR listesi. MF3'te
                    // firmaListesiYukle yazılmış ama buraya
                    // bağlanmamıştı: tablo "Yükleniyor…"da kalıyor,
                    // "+ Yeni Firma" düğmesi hiç basılmıyordu.
                    firma: () => { firmaYukle(); firmaListesiYukle(); },
''',
     r'''const yukleyici = { kullanici: kullaniciYukle,
                    firmalar: firmaListesiYukle,
                    firma: firmaYukle,
'''),
    ('templates/ayarlar.html', 'YP · templates/ayarlar.html blok 20',
     r'''
yuklendi.kullanici = true;
kullaniciYukle();
''',
     r'''
/* ── AÇILIŞTA HANGİ SEKME ── (YP2)
   Sabit `kullanici` yazılıydı; Ayarlar'da o sekme artık YOK ve
   kullaniciYukle() orada 403 alır (uç 'ayarlar' yazma yetkisi
   arıyor, panel admin'e özel). Açık olan sekme neyse onu
   yüklüyoruz — şablon koşulu doğru sekmeyi zaten `aktif` basıyor.

   NOT: bu yorumda şablon etiketi YAZMAYIN. İlk hâlinde örnek
   olsun diye açılı-yüzde etiketi yazmıştım; Jinja JS yorumunun
   içinde olduğunu bilmiyor, onu etiket sanıp ayrıştırdı ve
   sayfa TemplateSyntaxError verdi. */
(function acilisSekmesi() {
  const ilk = document.querySelector('.sekme.aktif');
  const ad = ilk && ilk.dataset.b;
  if (ad && yukleyici[ad]) { yuklendi[ad] = true; yukleyici[ad](); }
})();
'''),
    ('templates/base.html', 'YP · templates/base.html blok 1',
     r'''    <div class="ray-oge">
    <a href="/ayarlar" class="ray-btn {% if yol.startswith('/ayarlar') or yol.startswith('/denetim') %}aktif{% endif %}">
''',
     r'''    <div class="ray-oge">
    <a href="/ayarlar" class="ray-btn {% if yol.startswith('/ayarlar') or yol.startswith('/denetim') or yol.startswith('/yonetim') %}aktif{% endif %}">
'''),
    ('templates/base.html', 'YP · templates/base.html blok 2',
     r'''      <a href="/ayarlar" class="{% if yol.startswith('/ayarlar') %}aktif{% endif %}"><span class="nokta"></span>Ayarlar</a>
''',
     r'''      <a href="/ayarlar" class="{% if yol.startswith('/ayarlar') %}aktif{% endif %}"><span class="nokta"></span>Ayarlar</a>
      {# YP1: Yönetim paneli — firma üstü işler. Yalnızca admin. #}
      {% if admin %}
      <a href="/yonetim" class="{% if yol.startswith('/yonetim') %}aktif{% endif %}"><span class="nokta"></span>Yönetim</a>
      {% endif %}
'''),
    ('templates/firma_sec.html', 'YP · templates/firma_sec.html blok 1',
     r'''    <button class="ekle-btn" id="ekleBtn" onclick="formAc()">+ Yeni firma ekle</button>
''',
     r'''    <button class="ekle-btn" id="ekleBtn" onclick="formAc()">+ Yeni firma ekle</button>
    {# ── YP1 · YÖNETİM PANELİ ──
       Panelin varlık sebebi "herhangi bir firmaya girmeden
       yönetmek"; o yüzden bağlantısı BURADA, firmaya girmeden
       önce duruyor. Kullanıcı açmak ya da yetki vermek için
       rastgele bir firmaya girip Ayarlar'a gitmek gerekmiyor. #}
    <p style="margin-top:14px;text-align:center;font-size:.86rem">
      <a href="/yonetim" style="color:var(--soluk)">Yönetim paneli —
        firmalar, kullanıcılar, yetkiler, yedekler</a>
    </p>
'''),
    ('tests/test_kritik.py', 'YP · tests/test_kritik.py blok 1',
     r'''    assert 'SECILI_FIRMALAR = (DUZENLENEN' in ay
''',
     r'''    assert 'SECILI_FIRMALAR = (DUZENLENEN' in ay


# ══════════════════════════════════════════════════════════════════════
#  YP · YÖNETİM PANELİ (firma üstü işler)
# ══════════════════════════════════════════════════════════════════════

def test_yp_panel_firma_secmeden_acilir():
    """YP1: panelin VARLIK SEBEBİ bu — firmaya girmeden yönetmek.

    Seçim kapısı burayı durdursaydı panel yalnızca firma seçtikten
    sonra açılırdı ve hiçbir işe yaramazdı."""
    c = fa.app.test_client()
    with c.session_transaction() as s:
        s['kullanici'] = 'admin'; s['rol'] = 'ADMIN'; s['_csrf'] = 't'
        # firma_id BİLEREK yok
    r = c.get('/yonetim')
    assert r.status_code == 200, r.status_code


def test_yp_admin_olmayan_panele_giremez():
    """YP1: panelde yapılan işler YETKİNİN KENDİSİNİ belirliyor
    (kullanıcı açmak, yetki vermek, firma silmek). Yetki haritasına
    bağlanmıyor, doğrudan ADMIN şartı aranıyor."""
    c = istemci('satis', 'SATIS')
    r = c.get('/yonetim')
    assert r.status_code in (301, 302), r.status_code
    assert '/yonetim' not in (r.headers.get('Location') or '')


def test_yp_paneller_ikizlenmemis():
    """YP2: taşınan bölümler İKİ sayfada birden basılmamalı.

    Bu projede mükerrer panel çoktan can yaktı: MF4'te iki
    `yedekGovde` yüzünden yedek listesi boş görünüyordu. Aynı
    şablon iki rotaya hizmet ediyor ama her bölüm YALNIZCA bir
    sayfada basılıyor; bu testin işi o sözü tutturmak."""
    a = istemci('admin', 'ADMIN')
    yon = a.get('/yonetim').get_data(as_text=True)
    aya = a.get('/ayarlar').get_data(as_text=True)

    # Sistem düzeyi — YALNIZCA yönetimde
    for kimlik in ('kullaniciGovde', 'firmaGovde', 'yedekGovde'):
        assert yon.count(f'id="{kimlik}"') == 1, kimlik
        assert aya.count(f'id="{kimlik}"') == 0, (kimlik, 'ayarlarda da var')

    # Firma düzeyi — YALNIZCA ayarlarda
    for kimlik in ('fFirma', 'bankaGovde', 'lookupIzgara'):
        assert aya.count(f'id="{kimlik}"') == 1, kimlik
        assert yon.count(f'id="{kimlik}"') == 0, (kimlik, 'yonetimde de var')


def test_yp_sekme_kumeleri_ayrik():
    """YP2: iki sayfanın sekmeleri ÖRTÜŞMEMELİ."""
    import re as _re
    a = istemci('admin', 'ADMIN')

    def sekmeler(yol):
        h = a.get(yol).get_data(as_text=True)
        return {b for b, _ in _re.findall(
            r'class="sekme[^"]*" data-b="([a-z]+)">([^<]+)<', h)}

    yon, aya = sekmeler('/yonetim'), sekmeler('/ayarlar')
    assert yon == {'kullanici', 'firmalar', 'yedek'}, yon
    assert aya == {'firma', 'eposta', 'listeler', 'banka'}, aya
    assert not (yon & aya), yon & aya


def test_yp_panelden_firma_ve_kullanici_yonetilebilir():
    """YP1/YP2: panelin beslendiği uçlar firma seçmeden ÇALIŞMALI.

    Uçlar seçim kapısında muaf; muafiyet kalkarsa panel açılır ama
    tabloları boş kalır — sessiz bir arıza."""
    c = fa.app.test_client()
    with c.session_transaction() as s:
        s['kullanici'] = 'admin'; s['rol'] = 'ADMIN'; s['_csrf'] = 't'
    assert c.get('/api/firma', headers=H).status_code == 200
    assert c.get('/api/ayarlar/kullanici', headers=H).status_code == 200
'''),
]


def main():
    print('=' * 70)
    print('  YAMA YP — YONETIM PANELI')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    gruplar = {}
    for dosya, aciklama, eski, yerine in DEGISIKLIKLER:
        gruplar.setdefault(dosya, []).append((aciklama, eski, yerine))

    sonuclar, hata, zaten = {}, False, []

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
        print('  ⊙ Yama YP zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_yp.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_yp'
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
    print('    sudo systemctl restart milestone-erp')
    print('    (tarayicida Ctrl+F5)')
    print()
    print('  Sol ray -> Ayarlar simgesi -> Sistem menusunde "Yonetim".')
    print('  Firma secim ekraninda da bagi var: kullanici acmak icin')
    print('  rastgele bir firmaya girmek gerekmiyor.')
    print()
    print('    /yonetim  -> Kullanicilar · Firmalar · Yedekleme')
    print('    /ayarlar  -> Firma Bilgileri · E-posta · Listeler · Bankalar')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

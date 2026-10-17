#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA YP4 — PANEL FİRMA ÜSTÜNE ÇIKIYOR
======================================

ÖNKOŞUL: yama_yp3.py uygulanmış olmalı.

Dört madde vardı; dördü de yapıldı. Biri yolda beşinci bir şey
ölçtürdü, o da aşağıda.

── 1 · PANELDEN ÇIKIŞ SİSTEMDEN ATIYORDU ──
  "Çıkış" panelde "panelden çık" sanılıp basılıyordu ve oturumu
  kapatıyordu. Panelde artık oturum kapatma YOK. Tek kapı kaldı:
  sağ üstteki "← Firma seçimine dön". Oturum, firma seçim
  ekranından kapatılıyor.

── 2 · ÜSTTEKİ FİRMA DÜĞMESİ ──
  "← MİLESTONE MERMER…" düğmesi firmanın İÇİNE giriyordu; oradan
  bütün menüler açılıyordu. Kalktı.

  Ama asıl düzeltme düğmeyi silmek değil: panele girerken
  oturumdaki firma seçimi DÜŞÜYOR. Böylece "firma seçili panel"
  diye ikinci bir durum kalmıyor ve ekranda firmaya açılan yeni
  bir kapı doğamıyor. Düğmeyi silmekle yetinseydim, yarın başka
  bir yerden aynı sızıntı çıkardı.

  (Tek firmalı kurulumda çözümleyici o firmayı kendiliğinden
  seçmeye devam ediyor — "tek firma varsa seçtirecek bir şey yok"
  kuralı KF2'den beri öyle. Panelde görünen bir şey değişmiyor.)

── 3 · FİRMA AYARLARI PANELE TAŞINDI ──
  Ünvan, belge kodu, adres, telefon, e-posta ve logo artık
  Ayarlar'da değil, panelin Firmalar sekmesinde: tablodan
  "Ayarlar"a bas, o firmanın formu açılsın. Firmaya GİRMEDEN.

  Taşındı, kopyalanmadı — Ayarlar'da artık yok. Ayarlar'da kalan
  üç sekme o firmada ÇALIŞIRKEN kullanılan tanımlar: gönderim
  hesabı, listeler, banka hesapları.

  NASIL ÇALIŞIYOR: uçlar (`/api/ayarlar/firma`, `logo`) artık
  `firma_id` kabul ediyor. Kimlik varsa istek O FİRMANIN
  bağlamında koşuyor; yoksa eski davranış sürüyor (aktif firma) —
  proforma ekranları aynı uçları öyle kullanmaya devam ediyor.

  Bağlam `g._mf2_firma` üzerinden çevriliyor. `firma_atla()` ile
  KARIŞTIRMAYIN, tersi iş yapıyor:

      firma_atla()  süzgeci KAPATIR   → tüm firmalar görünür
      YP4 kancası   süzgeci ÇEVİRİR   → yalnızca hedef firma

  Yani kaçış kapısı değil; kapsam yine tek firma, sadece hedefini
  oturum belirlemiyor. ADMIN şartı var, firma doğrulanıyor ve
  firma_denetim'e F7 ekseni eklendi: bağlamı çeviren yerleri
  sayıyor ve kancada ADMIN şartını arıyor.

── 4 · KULLANICILAR FİRMA BAZLI ──
  Üstte firma seçimi var; liste o firmada çalışabilenleri
  gösteriyor. 5 firma × 10 kullanıcı artık 50 satır değil.

  Üç grup da görünür kalıyor:
    · o firmaya atanmış olanlar
    · "tüm firmalar" kapsamlılar — her firmada çalışıyorlar, her
      listede görünüyorlar, rozetle ayrılıyorlar
    · HİÇBİR firmaya atanmamış olanlar — kendi satırları var
      ("⚠ Firması olmayanlar"). Bu seçenek olmasaydı sisteme
      giremeyen ama düzeltilmek için de bulunamayan kullanıcılar
      ekrandan kaybolurdu.

  Yeni kullanıcı penceresi, listede açık olan firmayı işaretli
  getiriyor; yoksa açtığın kullanıcı hiçbir firmada çalışamaz ve
  kendi listesinde bile görünmezdi.

── 5 · YOLDA ÖLÇÜLEN: KDV VE AVANS SİSTEM GENELİ ──
  Firma ayarlarını taşırken Vergi (KDV oranı) ve Üretim Ödeme
  Kapısı (avans eşiği) de firma formuna girecekti. Ölçtüm: panelden
  firma B için %18 yazdım, firma A da %18 okudu. Sebep veri
  modelinde — ikisi de `Veriler`de firma_id'si NULL tek satırda
  duruyor ve damga `Veriler`i bilerek atlıyor.

  Yani bu iki değer BUGÜN sistem geneli. Firma formuna koymak,
  firma başına ayrıymış gibi göstermek olurdu: STONEHUB'ın KDV'sini
  değiştirdiğini sanıp MILESTONE'unkini de değiştirirdin. İkisi
  panelde "Tüm firmalar için" başlığı altında, ne olduğu yazılı
  duruyor.

  Firma başına ayrı istiyorsan ayrı bir iş: veri taşıma gerekiyor.
  Söyle, yaparım.

── YOL ÜSTÜNDE ──
  · `_firma_ortak_liste()` "hangi firmadayım" sorusunu KENDİ
    başına hesaplıyordu (`session['firma_id']`), süzgeç ve damga
    ise çözümleyiciden besleniyordu. Panelden gelen istekte ikisi
    AYRIŞTI ve ölçüldü. Tek kaynağa bağlandı.
  · Ayarlar'ın alt başlığı hâlâ "kimlik bilgileri" diyordu; artık
    orada değil.

── ÖLÇÜLDÜ ──
  /yonetim   ray YOK · arama YOK · Çıkış YOK · /dashboard bağı YOK
             dönüş: "← Firma seçimine dön" → /firma-sec
             panele girince oturumdaki firma_id düşüyor
  Kullanıcılar  firma seçimi: 3 firma + "Tüm kullanıcılar (7)" +
             "⚠ Firması olmayanlar (1)";  MILESTONE → 5 satır
             (atanan 3 + tüm-firma kapsamlı 2), John ve Atanmamis yok
  Firmalar   her satırda Ayarlar + Sil · altında "+ Yeni Firma"
             ve "Tüm firmalar için" (KDV, avans)
  Firma ayarı  STONEHUB USA'nın ünvanı, firmaya GİRMEDEN kaydedildi;
             komşu firmanın ünvanı değişmedi (test)
  /ayarlar   ilk sekme E-posta · firma kimliği YOK

  110 test geçti (104 + 6 yeni kalıcı test);
  firma (F1–F7) · js · form · zincir · akis · degismezlik temiz.

  Dört ekran Chromium'da basıldı ve bakıldı.

DOSYALAR
--------
  flask_app.py             panel kancası · muafiyet · firma düşürme
                           · ortak liste kaynağı
  firma_denetim.py         F7 ekseni (bağlamı çevirenler)
  templates/base.html      panelde Çıkış ve firma düğmesi yok
  templates/ayarlar.html   firma ayarları panelde · firma bazlı
                           kullanıcı listesi · sistem ayarları
  tests/test_kritik.py     6 yeni test, 5 güncellenen

Şema yok, göç yok. Veri dokunulmuyor.

KULLANIM
--------
  python3 yama_yp4.py            # RAPOR
  python3 yama_yp4.py --uygula
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
    'flask_app.py': 'def _panel_firma_baglami',
    'firma_denetim.py': 'F7 · FİRMA BAĞLAMINI ÇEVİRENLER',
    'templates/base.html': 'PANELDEN ÇIKIŞ (YP3 · YP4)',
    'templates/ayarlar.html': 'FİRMA BAZLI KULLANICI LİSTESİ (YP4)',
    'tests/test_kritik.py': 'def test_yp4_panele_girince_firma_secimi_dusuyor',
}
ONKOSUL = {
    'flask_app.py': 'YP3 · YENİ FİRMA ARTIK BURADA DEĞİL',
    'firma_denetim.py': 'F6 · ERİŞİM ÇÖZÜMLEYİCİSİ',
    'templates/base.html': 'YALIN KABUK · YÖNETİM PANELİ (YP3)',
    'templates/ayarlar.html': 'FİRMA SİL (YP3)',
    'tests/test_kritik.py': 'def test_yp3_panelde_ray_ve_arama_basilmaz',
}

DEGISIKLIKLER = [
    ('flask_app.py', 'YP4 · flask_app.py blok 1',
     r'''        # YP2: AYNI ŞABLON, farklı yüz. Panelleri ikinci bir
''',
     r'''        # ── YP4 · PANELE GİRERKEN FİRMA BAĞLAMI DÜŞER ──
        # YP3'te oturumdaki seçim korunuyordu ve üst barda "←
        # MİLESTONE…" diye bir düğme çıkıyordu; basınca firmanın
        # İÇİNE giriyor, bütün menüler açılıyordu. Panelin içinden
        # bir firmaya girilebiliyorsa panel firma üstü değildir.
        #
        # Seçimi burada düşürmek kuralı DEĞİŞMEZ hâle getiriyor:
        # panelde firma seçili değildir. Böylece "firma seçilmiş
        # panel" diye ikinci bir durum kalmıyor ve ekranda firmaya
        # açılan hiçbir kapı doğamıyor. Çıkışta seçim ekranına
        # düşülüyor, firma oradan seçiliyor — istenen akış buydu.
        session.pop('firma_id', None)
        # YP2: AYNI ŞABLON, farklı yüz. Panelleri ikinci bir
'''),
    ('flask_app.py', 'YP4 · flask_app.py blok 2',
     r'''    FIRMA_SECIM_MUAF = (
''',
     r'''    # ── YP4 · PANELDEN DÜZENLENEN FİRMA AYARLARI ──
    # Bu dört uç "aktif firmanın" ayarını okur/yazar. Yönetim paneli
    # aynı uçları `firma_id` ile çağırıyor ve o zaman HEDEF firma
    # istekte belirtiliyor (aşağıda `_panel_firma_baglami`).
    #
    # NEDEN YENİ UÇ AÇMADIM: aynı doğrulamanın (belge kodu çakışması,
    # logo biçimi/boyutu, oran aralığı) ikinci bir kopyası olurdu ve
    # bu projede ikiz kopyalar hep ayrışıyor — biri düzeltilip öteki
    # unutuluyor (MF4'teki mükerrer panel, YP3'teki ikiz firma formu).
    PANEL_AYAR_UCLARI = ('/api/ayarlar/firma', '/api/ayarlar/logo',
                         '/api/ayarlar/kdv_oran', '/api/ayarlar/uretim_avans')

    FIRMA_SECIM_MUAF = (
'''),
    ('flask_app.py', 'YP4 · flask_app.py blok 3',
     r'''        '/yonetim', '/api/ayarlar/kullanici', '/api/yedek',
    )
''',
     r'''        '/yonetim', '/api/ayarlar/kullanici', '/api/yedek',
        # ── YP4 · FİRMA KİMLİK UÇLARI ──
        # Firma Bilgileri (ünvan, belge kodu, adres, logo, KDV,
        # avans) panele taşındı; panelde firma seçili DEĞİL, yani
        # kapı bu uçları da durdurursa form hiç açılmaz.
        #
        # Muafiyet neden sızıntı açmıyor:
        #   · `firma_id` YOKSA eski davranış sürüyor ve aktif firma
        #     0'dır — `Firma.query.get(0)` None, Veriler sorguları
        #     boş. Yani seçimsiz çağrı boş form döndürür.
        #   · `firma_id` VARSA aşağıdaki `_panel_firma_baglami`
        #     ADMIN şartı arıyor ve firmayı doğruluyor.
        *PANEL_AYAR_UCLARI,
    )

    @app.before_request
    def _panel_firma_baglami():
        """Panelden gelen `firma_id` bu isteğin firmasını belirler (YP4).

        `aktif_firma_id()` sonucu istek başına `g._mf2_firma`'da
        önbellekli ve HEM okuma süzgeci HEM yazma damgası oradan
        besleniyor. Önbelleği burada doldurmak ikisini birden
        çeviriyor; ayrı ayrı çevirmeye kalkmak, okunan firmayla
        yazılan firmanın ayrışması demek olurdu.

        `firma_atla()` İLE KARIŞTIRMAYIN — tam tersi iş yapıyor:

          firma_atla()  süzgeci KAPATIR     → tüm firmalar görünür
          burası        süzgeci ÇEVİRİR     → yalnızca hedef firma

        Yani kaçış kapısı değil: kapsam yine tek firma, sadece
        hedefini oturumdaki seçim belirlemiyor. Panelin varlık sebebi
        bu — bir firmanın ünvanını, belge kodunu, logosunu ve KDV
        oranını O FİRMAYA GİRMEDEN düzenlemek. Eski düzende önce o
        firmaya geçmek şarttı ve MF3B'de can yakan tuzak buydu:
        A'nın ayarlarındayken B'yi düzenlediğini sanmak.

        Tek yazma noktası burası; firma_denetim F7 başka yazan
        olmadığını denetliyor.
        """
        if request.path not in PANEL_AYAR_UCLARI:
            return None
        _ham = request.args.get('firma_id')
        if _ham is None and request.method in ('POST', 'PUT', 'DELETE'):
            _g = request.get_json(silent=True) or {}
            _ham = _g.get('firma_id')
        if _ham in (None, ''):
            return None                 # eski davranış: aktif firma
        if 'kullanici' not in session:
            return None                 # oturum yok: _auth_required işi
        # Başka firmanın ayarını açmak YÖNETİCİ işi. Yetki haritasına
        # bağlamıyoruz: 'ayarlar' yazma yetkisi olan bir kullanıcı
        # kendi firmasının ayarını düzenleyebilir ama BAŞKA firmanın
        # ünvanını değiştirmek firma üstü bir yetkidir.
        if (session.get('rol') or '').upper() != 'ADMIN':
            return jsonify({'ok': False, 'error': 'yetkisiz',
                            'mesaj': 'Başka bir firmanın ayarını '
                            'düzenlemek için yönetici yetkisi '
                            'gerekiyor.'}), 403
        try:
            _fid = int(_ham)
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'mesaj': 'Geçersiz firma'}), 400
        # Firma GERÇEKTEN var mı: doğrulamadan bağlamı çevirmek,
        # olmayan bir kimliğe yazma damgası basmak olurdu.
        # `firma` tablosu süzgeç kapsamı dışında (bkz. _firma_suzgeci),
        # o yüzden atlama gerekmiyor.
        if not Firma.query.filter(Firma.id == _fid,
                                  Firma.aktif.is_(True)).first():
            return jsonify({'ok': False, 'mesaj': 'Firma bulunamadı'}), 404
        g._mf2_firma = _fid
        return None
'''),
    ('flask_app.py', 'YP4 · flask_app.py blok 4',
     r'''            _f = session.get('firma_id')
''',
     r'''            # ── YP4 · KAYNAK `aktif_firma_id()`, OTURUM DEĞİL ──
            # Burası `session.get('firma_id')` okuyordu ve bu, "hangi
            # firmadayım" sorusunun İKİNCİ bir hesabıydı. Yönetim
            # paneli bir firmanın ayarını `firma_id` ile düzenlerken
            # aradaki fark ÖLÇÜLDÜ: süzgeç ve damga hedef firmayı
            # gösterirken burası oturuma bakıp "seçim yok" diyor,
            # ortak havuza düşüyordu — panelden girilen KDV oranı
            # firma_id'siz yazılıp BÜTÜN firmalarda görünüyordu.
            #
            # Tek kaynak: çözümleyici. Oturumdaki seçim zaten onun
            # ilk girdisi, yani seçim varken davranış aynı.
            _f = aktif_firma_id()
'''),
    ('firma_denetim.py', 'YP4 · firma_denetim.py blok 1',
     r'''print()
print("═" * 70)
''',
     r'''# ══════════════════════════════════════════════════════════════════════
#  F7 · FİRMA BAĞLAMINI ÇEVİREN YERLER
# ══════════════════════════════════════════════════════════════════════
#
# `g._mf2_firma`, "şu an hangi firmadayım" sorusunun önbelleği ve HEM
# okuma süzgeci HEM yazma damgası oradan besleniyor. Yazan her yer,
# o isteğin bütün sorgularını başka bir firmaya çeviriyor demektir.
#
# F3'ten FARKI: `firma_atla()` süzgeci KAPATIR (tüm firmalar görünür),
# burası ÇEVİRİR (yalnızca hedef firma). İkincisi daha dar ama yetki
# denetimi olmazsa daha tehlikeli: yanlış firmaya YAZDIRIR.
#
# Meşru yazan: `aktif_firma_id()` kendi önbelleği + yönetim panelinin
# `_panel_firma_baglami` kancası. Başkası çıkarsa ADMIN şartı aranmış
# mı diye bakılmalı.
MF2_BEKLENEN = 2
print()
print("─" * 70)
print(" F7 · FİRMA BAĞLAMINI ÇEVİRENLER (g._mf2_firma)")
print("─" * 70)
_yazan = [(i + 1, s2.strip()) for i, s2 in enumerate(KAYNAK.split('\n'))
          if re.search(r'g\._mf2_firma\s*=', _kodsuz(s2))]
print(f"   {len(_yazan)} yazan (beklenen {MF2_BEKLENEN})")
_f7 = 0
if len(_yazan) != MF2_BEKLENEN:
    for n, s2 in _yazan:
        print(f"     {n:>6}  {s2[:62]}")
    print()
    print("   ✗ Liste değişmiş. Her yazan, o isteğin TÜM sorgularını")
    print("     başka firmaya çevirir — yetki denetimi şart.")
    _f7 += 1
else:
    print("   ✓ temiz — yazan yerler gözden geçirilmiş listeyle aynı")

# Panel kancası ADMIN arıyor mu
_g = _govde(KAYNAK, '_panel_firma_baglami')
if _g is None:
    print("   ⚠ _panel_firma_baglami bulunamadı — atlandı")
elif "!= 'ADMIN'" not in _g:
    print("   ✗ _panel_firma_baglami ADMIN şartı ARAMIYOR")
    print("     `firma_id` yollayan herkes başka firmanın ayarını")
    print("     düzenleyebilirdi — yetki yükseltme.")
    _f7 += 1
else:
    print("   ✓ panel kancası ADMIN şartı arıyor")
bulgu += _f7

print()
print("═" * 70)
'''),
    ('templates/base.html', 'YP4 · templates/base.html blok 1',
     r'''        {# ── PANELDEN ÇIKIŞ (YP3) ──
           Paneli firma SEÇMEDEN açan (olağan hâli) seçim ekranına
           döner ve oradan bir firmaya girer. Bir firmanın içinden
           gelen ise kaldığı yere döner; onu da seçim ekranına
           atmak, yaptığı işi bıraktırıp yeniden firma seçtirmek
           olurdu. #}
        {% if yalin %}
          {% if aktif_firma %}
          <a href="/dashboard" class="geri-btn">← {{ aktif_firma.ad }}</a>
          {% else %}
          <a href="/firma-sec" class="geri-btn">← Firma seçimine dön</a>
          {% endif %}
''',
     r'''        {# ── PANELDEN ÇIKIŞ (YP3 · YP4) ──
           YP3'te iki düğme vardı ve ikisi de yanlıştı:

             "← MİLESTONE…"  firmanın İÇİNE giriyordu. Panelin
                 içinden bir firmaya girilebiliyorsa panel firma
                 üstü değildir; o düğme kalktı.
             "Çıkış"  sistemden atıyordu. Panelden çıkmak isteyen
                 oturumu kapatmış oluyordu; o da kalktı.

           Geriye TEK kapı kaldı ve hep aynı yere açılıyor: firma
           seçim ekranı. Oturum kapatma orada duruyor. #}
        {% if yalin %}
        <a href="/firma-sec" class="geri-btn">← Firma seçimine dön</a>
'''),
    ('templates/base.html', 'YP4 · templates/base.html blok 2',
     r'''        <a href="/cikis" class="cikis-btn">Çıkış</a>
''',
     r'''        {# YP4: panelde oturum kapatma YOK. "Çıkış" orada "panelden
           çık" sanılıp basılıyordu ve kullanıcıyı sistemden
           atıyordu. Panelin tek kapısı yukarıdaki dönüş
           bağlantısı; oturum, firma seçim ekranından kapatılır. #}
        {% if not yalin %}
        <a href="/cikis" class="cikis-btn">Çıkış</a>
        {% endif %}
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 1',
     r'''  @media (max-width:900px){ .izgara-2{grid-template-columns:1fr} }
''',
     r'''  /* YP4: firma seçim kutusu `.form-alan` içinde DEĞİL (satır değil,
     tek satırlık bir araç çubuğu). Kendi kuralı olmazsa tarayıcının
     ham <select>'i çıkıyor ve sayfanın geri kalanına yabancı
     duruyordu — KF5'te aynı ders ölçülmüştü. */
  #kullaniciFirmaSecim select{border:1px solid var(--cizgi-koyu);
    border-radius:var(--r-kucuk);padding:8px 11px;font-family:var(--govde);
    font-size:.88rem;background:var(--yuzey);color:var(--murekkep);
    min-width:260px}
  #kullaniciFirmaSecim select:focus{outline:none;border-color:var(--verde);
    box-shadow:0 0 0 3px var(--verde-acik)}
  @media (max-width:900px){ .izgara-2{grid-template-columns:1fr} }
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 2',
     r'''<p class="g-alt">Bu firmanın ayarları: kimlik bilgileri, e-posta,
   liste tanımları, banka hesapları.
   {% if menu_admin %}Firma ve kullanıcı yönetimi
''',
     r'''<p class="g-alt">Bu firmada çalışırken kullanılan tanımlar: gönderim
   hesabı, liste tanımları, banka hesapları.
   {% if menu_admin %}Firmanın <b>kimliği</b> (ünvan, belge kodu, logo),
   firmalar ve kullanıcılar
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 3',
     r'''  <button class="sekme aktif" data-b="firma">Firma Bilgileri</button>
  <button class="sekme" data-b="eposta">E-posta</button>
''',
     r'''  {# YP4: "Firma Bilgileri" buradan KALKTI. Ünvan, belge kodu,
     adres, logo, KDV ve avans firmanın KİMLİĞİ; o firmaya girmeden,
     Yönetim panelindeki Firmalar sekmesinden düzenleniyor. Burada
     kalan üç sekme ise o firmada ÇALIŞIRKEN kullanılan tanımlar:
     gönderim hesabı, listeler, banka hesapları. #}
  <button class="sekme aktif" data-b="eposta">E-posta</button>
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 4',
     r'''<section class="bolum aktif" id="b-kullanici">
''',
     r'''<section class="bolum aktif" id="b-kullanici">
  <!-- YP4: önce firma, sonra o firmanın kullanıcıları. 5 firma ×
       10 kullanıcı tek listede 50 satır ediyordu. -->
  <div id="kullaniciFirmaSecim" style="display:flex;align-items:center;
       gap:10px;margin-bottom:14px"></div>
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 5',
     r'''      Firma <b>açmak ve silmek</b> buradan yapılır — bir firmanın
      içine girmeden. Bir firmanın <b>ünvanı, logosu ve belge
      kodu</b> ise o firmaya ait: o firmaya geçip Ayarlar → Firma
      Bilgileri'nden düzenlenir.</p>
    <div class="tablo-kutu">
      <table>
        <thead><tr><th>Firma</th><th>Belge Kodu</th><th>Vergi No</th>
          <th class="sag" style="width:120px"></th></tr></thead>
        <tbody id="firmaGovde"><tr><td colspan="4" class="yukleniyor">Yükleniyor…</td></tr></tbody>
      </table>
    </div>
    <div id="firmaEkleKutu" style="margin-top:14px"></div>
  </div>
</section>
{% endif %}

{% if PANEL != 'yonetim' %}
<section class="bolum aktif" id="b-firma">
  <!-- ── FİRMA BİLGİLERİ ──
       AKTİF FİRMAYI düzenler; başka bir firmanın bilgisini girmek
       için önce üst bardan o firmaya geç. Firma AÇMA/SİLME burada
       DEĞİL, Yönetim panelinde (YP2).

       YP3 · `aktif` BURAYA EKLENDİ. Ayarlar'ın ilk sekmesi YP2'de
       `kullanici`dan `firma`ya geçti ama açılışta görünen bölüm
       değişmedi: sekme "Firma Bilgileri"nde duruyor, altı ise
       BOMBOŞ açılıyordu. Açık sekme ile açık bölüm aynı adı
       göstermek zorunda. -->
  <div class="izgara-2">
    <div class="panel">
      <h4>Firma Bilgileri <span id="fBaslikFirma" style="color:var(--verde);font-weight:600"></span></h4>
      <p style="color:var(--soluk);font-size:.83rem;margin-bottom:14px">
        Proforma ve fatura belgelerinde görünür.
        <b>Aktif firmanın</b> bilgileridir — başka bir firmanınkini
        düzenlemek için önce o firmaya geç.</p>
      <div class="form-alan" style="margin-bottom:12px">
        <label>Satıcı Firma Ünvanı</label>
        <!-- MF5: örnek metin GERÇEK bir firma adı olmamalı. Boş
             formda "Milestone Mermer…" yazınca, ikinci firmadayken
             ana firmanın bilgisi oraya yazılmış gibi görünüyordu. -->
        <input id="fFirma" placeholder="Tam ticari ünvan — belgelerde basılır">
      </div>
      <!-- ── RN3 · BELGE KODU ──
           Buradaki alan eskiden "Kısaltma (stok kodlarında)" idi.
           Etiket stok kodlarını etkilediğini söylüyordu ama `kisaltma`
           alanını HİÇBİR YER OKUMUYOR (tüm kaynakta arandı: yalnızca
           bu form yazıyor ve geri okuyor). Stok ve belge kodlarını
           gerçekten belirleyen alan `belge_kodu` ve o da yalnızca
           firma AÇILIRKEN sorulup bir daha değiştirilemiyordu.

           Yani ekranda etkisi olmayan bir alan dururken, etkisi olan
           alana erişim yoktu. Alan değiştirildi; `kisaltma` sütunu
           veritabanında duruyor (göç yok, veri kaybı yok) ama forma
           dönmüyor — ölü alanı ekranda tutmak aynı karışıklığı
           yeniden doğurur. -->
      <div class="form-alan" style="margin-bottom:12px">
        <label>Belge Kodu (sipariş, fatura, stok ve cari kimliklerinde)</label>
        <input id="fBelgeKodu" placeholder="en çok 4 karakter — örn. MLS"
               maxlength="4" style="text-transform:uppercase">
        <div class="ipucu" style="font-size:12px;color:var(--soluk);margin-top:4px">
          Her firmanın belge sayacı bu koda göre ayrılır:
          <code>SIP-MLS-STN26-01</code>. Boş bırakılırsa kimlikler
          kodsuz üretilir (<code>SIP-STN26-01</code>).
          <b>Belge varken değiştirmeyin</b> — eski belgeler eski kökte
          kalır, yeni seri 01'den başlar; kimlikler bozulmaz ama
          numara sürekliliği kopar.
        </div>
      </div>

      <!-- F3: Bu üç alan proforma, ticari fatura ve packing list
           şablonlarında BASILIYOR ama hiçbir yerden girilemiyordu —
           belgeler satıcı iletişim bilgisi olmadan çıkıyordu.
           Bir kez girilir, oluşturulan her belgeye otomatik işlenir. -->
      <div class="form-alan" style="margin-bottom:12px">
        <label>Firma Adresi <span style="color:var(--soluk);font-weight:400;text-transform:none">· belgelerde basılır</span></label>
        <input id="fAdres" placeholder="Açık adres — belgelerde basılır">
      </div>
      <div class="form-satir f2" style="margin-bottom:14px">
        <div class="form-alan"><label>Telefon</label>
          <input id="fTelefon" data-buyuk-harf="hayir" placeholder="+90 258 000 00 00"></div>
        <div class="form-alan"><label>E-posta</label>
          <input id="fEposta" data-buyuk-harf="hayir" placeholder="ornek@firma.com"></div>
      </div>
      <button class="btn-yeni" onclick="firmaKaydet()">Kaydet</button>

      <div style="border-top:1px solid var(--cizgi);margin-top:18px;padding-top:16px">
        <h4 style="margin-bottom:6px">Firma Logosu</h4>
        <p style="color:var(--soluk);font-size:.83rem;margin-bottom:12px">
          Proforma, Packing List, Commercial Invoice ve ekstre belgelerinin
          üst kısmında görünür. Değiştirdiğinizde tüm belgeler anında güncellenir.
        </p>
        <div id="logoOnizleme" style="display:none;margin-bottom:12px;padding:14px;
             background:#fff;border:1px solid var(--cizgi);border-radius:var(--r-kucuk);text-align:center">
          <img id="logoResim" style="max-height:70px;max-width:100%;object-fit:contain">
          <div id="logoBilgi" style="font-size:.75rem;color:var(--soluk);margin-top:8px"></div>
        </div>
        <div id="logoYokNot" style="padding:14px;background:var(--kagit);border:1px dashed var(--cizgi-koyu);
             border-radius:var(--r-kucuk);text-align:center;color:var(--soluk);font-size:.85rem;margin-bottom:12px">
          Henüz logo yüklenmedi — belgelerde firma adı yazı olarak görünüyor.
        </div>
        <input type="file" id="logoDosya" accept="image/png,image/jpeg,image/svg+xml,image/webp"
               style="display:none" onchange="logoSecildi(event)">
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button class="blok-btn" onclick="document.getElementById('logoDosya').click()">
            Logo seç ve yükle</button>
          <button class="blok-btn" id="logoSilBtn" style="color:var(--kirmizi);display:none"
                  onclick="logoSil()">Logoyu kaldır</button>
        </div>
        <div style="font-size:.75rem;color:var(--soluk);margin-top:8px">
          PNG, JPG, SVG veya WEBP · en fazla 500 KB · şeffaf arka planlı PNG önerilir
        </div>
      </div>
    </div>
    <div class="panel">
      <h4>Vergi</h4>
      <p style="color:var(--soluk);font-size:.83rem;margin-bottom:14px">Yurt içi faturalarda varsayılan KDV oranı.</p>
      <div class="form-alan" style="margin-bottom:14px">
        <label>KDV Oranı (%)</label>
        <input id="fKdv" type="number" step="0.1" placeholder="20">
      </div>
      <button class="btn-yeni" onclick="kdvKaydet()">Kaydet</button>
    </div>
    <div class="panel">
      <h4>Üretim Ödeme Kapısı</h4>
      <p style="color:var(--soluk);font-size:.83rem;margin-bottom:14px">Onaylı sipariş üretime geçmeden önce gereken minimum avans oranı. <b>0 = kapalı</b> (ödeme kontrolü yapılmaz). Yönetici kapıyı zorla geçebilir.</p>
      <div class="form-alan" style="margin-bottom:14px">
        <label>Minimum Avans (%)</label>
        <input id="fAvans" type="number" step="1" min="0" max="100" placeholder="0">
      </div>
      <button class="btn-yeni" onclick="avansKaydet()">Kaydet</button>
    </div>
  </div>
</section>
{% endif %}

<!-- E-POSTA (SMTP) -->
{% if PANEL != 'yonetim' %}
<section class="bolum" id="b-eposta">
''',
     r'''      Firma <b>açmak, silmek ve ayarlarını düzenlemek</b> buradan
      yapılır — hiçbirinin içine girmeden.</p>
    <div class="tablo-kutu">
      <table>
        <thead><tr><th>Firma</th><th>Belge Kodu</th><th>Vergi No</th>
          <th class="sag" style="width:180px"></th></tr></thead>
        <tbody id="firmaGovde"><tr><td colspan="4" class="yukleniyor">Yükleniyor…</td></tr></tbody>
      </table>
    </div>
    <div id="firmaEkleKutu" style="margin-top:14px"></div>
  </div>

  <!-- ── TÜM FİRMALAR İÇİN (YP4) ──
       KDV oranı ve üretim avans eşiği BUGÜN sistem geneli: ikisi de
       `Veriler`de firma_id'siz tek satırda duruyor (damga Veriler'i
       bilerek atlıyor, bkz. models._firma_damgasi). Yani bir firmanın
       ayar kutusunda göstermek yalan olurdu — orada değiştirilen
       değer öteki firmalarda da değişirdi.

       Ölçüldü: panelden firma 2 için %18 yazıldı, firma 1 de %18
       okudu; satırın firma_id'si NULL'dı. Firma başına ayrı oran
       istenirse ayrı bir iş — veri taşıma gerekir. -->
  <div class="panel" style="margin-bottom:18px" id="sistemAyarPanel">
    <h4>Tüm firmalar için</h4>
    <p style="color:var(--soluk);font-size:.83rem;margin-bottom:14px">
      Bu iki değer <b>sistem geneli</b>: hangi firmada olursan ol
      aynısı geçerli. Firma başına ayrı tutulmuyor.</p>
    <div class="izgara-2">
        <div class="panel">
          <h4>Vergi</h4>
          <p style="color:var(--soluk);font-size:.83rem;margin-bottom:14px">Yurt içi faturalarda varsayılan KDV oranı.</p>

          <div class="form-alan" style="margin-bottom:14px">
            <label>KDV Oranı (%)</label>
            <input id="fKdv" type="number" step="0.1" placeholder="20">
          </div>
          <button class="btn-yeni" onclick="kdvKaydet()">Kaydet</button>
        </div>
        <div class="panel">
          <h4>Üretim Ödeme Kapısı</h4>
          <p style="color:var(--soluk);font-size:.83rem;margin-bottom:14px">Onaylı sipariş üretime geçmeden önce gereken minimum avans oranı. <b>0 = kapalı</b> (ödeme kontrolü yapılmaz). Yönetici kapıyı zorla geçebilir.</p>
          <div class="form-alan" style="margin-bottom:14px">
            <label>Minimum Avans (%)</label>
            <input id="fAvans" type="number" step="1" min="0" max="100" placeholder="0">
          </div>
          <button class="btn-yeni" onclick="avansKaydet()">Kaydet</button>
        </div>
    </div>
  </div>

  {# ── SEÇİLEN FİRMANIN AYARLARI (YP4) ──
     Ayarlar sayfasındaki "Firma Bilgileri" sekmesi BURAYA TAŞINDI
     (kopyalanmadı — orada artık yok). Orası AKTİF firmayı
     düzenliyordu ve başka bir firmanınkini girmek için önce o
     firmaya geçmek gerekiyordu; MF3B'de can yakan tuzak buydu —
     A'nın ayarlarındayken B'yi düzenlediğini sanmak.

     Artık düzenlenen firmayı TABLODAN seçiyorsun: `AYAR_FIRMA`
     hangisi olduğunu tutuyor ve bütün uçlar `firma_id` ile
     çağrılıyor. Kutu, firma seçilene kadar kapalı. #}
  <div id="firmaAyarKutu" style="display:none">
    <div style="display:flex;align-items:center;gap:12px;margin:4px 0 14px">
      <button class="mini-btn" onclick="firmaAyarKapat()">← Firmalar</button>
      <div style="font-family:var(--baslik);font-weight:700;font-size:1.02rem"
           id="fAyarBaslik"></div>
    </div>
    <div style="max-width:760px">
      <div class="panel">
        <h4>Firma Bilgileri</h4>
        <p style="color:var(--soluk);font-size:.83rem;margin-bottom:14px">
          Proforma, fatura ve packing list belgelerinde basılır.
          Hangi firmayı düzenlediğin yukarıda yazıyor — bu firmaya
          GİRMEDEN değiştiriliyor.</p>
        <div class="form-alan" style="margin-bottom:12px">
          <label>Satıcı Firma Ünvanı</label>
          <!-- MF5: örnek metin GERÇEK bir firma adı olmamalı. Boş
               formda "Milestone Mermer…" yazınca, ikinci firmadayken
               ana firmanın bilgisi oraya yazılmış gibi görünüyordu. -->
          <input id="fFirma" placeholder="Tam ticari ünvan — belgelerde basılır">
        </div>
        <!-- ── RN3 · BELGE KODU ──
             Buradaki alan eskiden "Kısaltma (stok kodlarında)" idi.
             Etiket stok kodlarını etkilediğini söylüyordu ama `kisaltma`
             alanını HİÇBİR YER OKUMUYOR (tüm kaynakta arandı: yalnızca
             bu form yazıyor ve geri okuyor). Stok ve belge kodlarını
             gerçekten belirleyen alan `belge_kodu` ve o da yalnızca
             firma AÇILIRKEN sorulup bir daha değiştirilemiyordu.

             Yani ekranda etkisi olmayan bir alan dururken, etkisi olan
             alana erişim yoktu. Alan değiştirildi; `kisaltma` sütunu
             veritabanında duruyor (göç yok, veri kaybı yok) ama forma
             dönmüyor — ölü alanı ekranda tutmak aynı karışıklığı
             yeniden doğurur. -->
        <div class="form-alan" style="margin-bottom:12px">
          <label>Belge Kodu (sipariş, fatura, stok ve cari kimliklerinde)</label>
          <input id="fBelgeKodu" placeholder="en çok 4 karakter — örn. MLS"
                 maxlength="4" style="text-transform:uppercase">
          <div class="ipucu" style="font-size:12px;color:var(--soluk);margin-top:4px">
            Her firmanın belge sayacı bu koda göre ayrılır:
            <code>SIP-MLS-STN26-01</code>. Boş bırakılırsa kimlikler
            kodsuz üretilir (<code>SIP-STN26-01</code>).
            <b>Belge varken değiştirmeyin</b> — eski belgeler eski kökte
            kalır, yeni seri 01'den başlar; kimlikler bozulmaz ama
            numara sürekliliği kopar.
          </div>
        </div>

        <!-- F3: Bu üç alan proforma, ticari fatura ve packing list
             şablonlarında BASILIYOR ama hiçbir yerden girilemiyordu —
             belgeler satıcı iletişim bilgisi olmadan çıkıyordu.
             Bir kez girilir, oluşturulan her belgeye otomatik işlenir. -->
        <div class="form-alan" style="margin-bottom:12px">
          <label>Firma Adresi <span style="color:var(--soluk);font-weight:400;text-transform:none">· belgelerde basılır</span></label>
          <input id="fAdres" placeholder="Açık adres — belgelerde basılır">
        </div>
        <div class="form-satir f2" style="margin-bottom:14px">
          <div class="form-alan"><label>Telefon</label>
            <input id="fTelefon" data-buyuk-harf="hayir" placeholder="+90 258 000 00 00"></div>
          <div class="form-alan"><label>E-posta</label>
            <input id="fEposta" data-buyuk-harf="hayir" placeholder="ornek@firma.com"></div>
        </div>
        <button class="btn-yeni" onclick="firmaKaydet()">Kaydet</button>

        <div style="border-top:1px solid var(--cizgi);margin-top:18px;padding-top:16px">
          <h4 style="margin-bottom:6px">Firma Logosu</h4>
          <p style="color:var(--soluk);font-size:.83rem;margin-bottom:12px">
            Proforma, Packing List, Commercial Invoice ve ekstre belgelerinin
            üst kısmında görünür. Değiştirdiğinizde tüm belgeler anında güncellenir.
          </p>
          <div id="logoOnizleme" style="display:none;margin-bottom:12px;padding:14px;
               background:#fff;border:1px solid var(--cizgi);border-radius:var(--r-kucuk);text-align:center">
            <img id="logoResim" style="max-height:70px;max-width:100%;object-fit:contain">
            <div id="logoBilgi" style="font-size:.75rem;color:var(--soluk);margin-top:8px"></div>
          </div>
          <div id="logoYokNot" style="padding:14px;background:var(--kagit);border:1px dashed var(--cizgi-koyu);
               border-radius:var(--r-kucuk);text-align:center;color:var(--soluk);font-size:.85rem;margin-bottom:12px">
            Henüz logo yüklenmedi — belgelerde firma adı yazı olarak görünüyor.
          </div>
          <input type="file" id="logoDosya" accept="image/png,image/jpeg,image/svg+xml,image/webp"
                 style="display:none" onchange="logoSecildi(event)">
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button class="blok-btn" onclick="document.getElementById('logoDosya').click()">
              Logo seç ve yükle</button>
            <button class="blok-btn" id="logoSilBtn" style="color:var(--kirmizi);display:none"
                    onclick="logoSil()">Logoyu kaldır</button>
          </div>
          <div style="font-size:.75rem;color:var(--soluk);margin-top:8px">
            PNG, JPG, SVG veya WEBP · en fazla 500 KB · şeffaf arka planlı PNG önerilir
          </div>
        </div>
      </div>
    </div>
  </div>
</section>
{% endif %}


<!-- E-POSTA (SMTP) -->
{% if PANEL != 'yonetim' %}
<!-- YP4: "Firma Bilgileri" panele taşındı; Ayarlar'ın ilk sekmesi
     artık bu. Açık sekme ile açık bölüm aynı olmak zorunda. -->
<section class="bolum aktif" id="b-eposta">
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 6',
     r'''  const g = document.getElementById('kullaniciGovde');
  g.innerHTML = KULLANICILAR.length ? KULLANICILAR.map(u => {
    let y = {};
    try { y = typeof u.yetkiler === 'string' ? JSON.parse(u.yetkiler || '{}') : (u.yetkiler || {}); } catch (e) { y = {}; }
    const admin = (u.rol || '').toUpperCase() === 'ADMIN';
    const acik = Object.entries(y).filter(([, v]) => v !== 'gizli');
    return `
    <tr style="border-left-color:var(${u.aktif === false ? '--cizgi-koyu' : '--verde'})">
      <td><strong>${kacar(u.ad)}</strong></td>
''',
     r'''  kullaniciFirmaSecimiCiz();
  kullaniciListeCiz();
}

/* ══ FİRMA BAZLI KULLANICI LİSTESİ (YP4) ══

   Önce bütün kullanıcılar tek listede basılıyordu. 5 firma × 10
   kullanıcı = 50 satır: aradığını bulmak için gözle tarama. Artık
   önce firma seçiliyor, liste o firmada çalışabilenleri gösteriyor.

   SÜZME İSTEMCİDE: uç zaten her kullanıcının `firma_kapsam` ve
   `firmalar` alanlarını veriyor (KF3). İkinci bir uç açmak, aynı
   yetki mantığının ikinci bir kopyası demekti.

   ÜÇ GRUP VAR, üçü de görünür olmalı:
     · o firmaya atanmış olanlar
     · `firma_kapsam = tumu` olanlar — HER firmada çalışıyorlar,
       dolayısıyla her firmanın listesinde görünmeliler (muhasebe,
       yönetim). Rozetle ayırt ediliyor.
     · HİÇBİR firmaya atanmamış olanlar — bunlar hiçbir firmanın
       listesine girmez ve seçenek olmasa EKRANDAN KAYBOLURLARDI:
       sisteme giremeyen ama düzeltilmek için de bulunamayan
       kullanıcı. Seçim kutusunda kendi satırları var. */
let KF_LISTE_FIRMA = null;

function _kfFirmasiz(u) {
  return (u.firma_kapsam || 'secili') !== 'tumu'
      && (u.rol || '').toUpperCase() !== 'ADMIN'
      && !((u.firmalar || []).length);
}

function _kfGorunur(u) {
  if (KF_LISTE_FIRMA === 'yok') return _kfFirmasiz(u);
  if (!KF_LISTE_FIRMA) return true;
  if ((u.firma_kapsam || 'secili') === 'tumu') return true;
  if ((u.rol || '').toUpperCase() === 'ADMIN') return true;
  return (u.firmalar || []).includes(KF_LISTE_FIRMA);
}

function kullaniciFirmaSecimiCiz() {
  const k = document.getElementById('kullaniciFirmaSecim');
  if (!k) return;
  const firmasiz = KULLANICILAR.filter(_kfFirmasiz).length;
  if (KF_LISTE_FIRMA === null) {
    /* Açılışta ilk firma seçili gelir: tek firmalı kurulumda
       seçtirecek bir şey yok, çok firmalıda da bir yerden
       başlamak gerekiyor. */
    KF_LISTE_FIRMA = (FIRMALAR_KF[0] || {}).id || 'tum';
  }
  k.innerHTML = `
    <label style="font-size:.76rem;font-weight:600;letter-spacing:.04em;
           text-transform:uppercase;color:var(--soluk)">Firma</label>
    <select id="kfListeSecim" onchange="kullaniciFirmaDegisti(this.value)"
            style="max-width:420px">
      ${FIRMALAR_KF.map(f => `<option value="${f.id}"${
          f.id === KF_LISTE_FIRMA ? ' selected' : ''}>${kacar(f.ad)}</option>`).join('')}
      <option value="tum"${KF_LISTE_FIRMA === 'tum' ? ' selected' : ''}
        >Tüm kullanıcılar (${KULLANICILAR.length})</option>
      ${firmasiz ? `<option value="yok"${KF_LISTE_FIRMA === 'yok' ? ' selected' : ''}
        >⚠ Firması olmayanlar (${firmasiz})</option>` : ''}
    </select>`;
}

function kullaniciFirmaDegisti(deger) {
  KF_LISTE_FIRMA = (deger === 'tum' || deger === 'yok') ? deger : parseInt(deger, 10);
  kullaniciListeCiz();
}

function kullaniciListeCiz() {
  const g = document.getElementById('kullaniciGovde');
  const liste = KULLANICILAR.filter(_kfGorunur);
  g.innerHTML = liste.length ? liste.map(u => {
    let y = {};
    try { y = typeof u.yetkiler === 'string' ? JSON.parse(u.yetkiler || '{}') : (u.yetkiler || {}); } catch (e) { y = {}; }
    const admin = (u.rol || '').toUpperCase() === 'ADMIN';
    const acik = Object.entries(y).filter(([, v]) => v !== 'gizli');
    return `
    <tr style="border-left-color:var(${u.aktif === false ? '--cizgi-koyu' : '--verde'})">
      <td><strong>${kacar(u.ad)}</strong>${
        (u.firma_kapsam || 'secili') === 'tumu' || admin
          ? ' <span class="rozet rz-mavi" title="Her firmada çalışabilir">tüm firmalar</span>'
          : ''}</td>
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 7',
     r'''  }).join('') : '<tr><td colspan="5" class="bos">Kullanıcı yok.</td></tr>';
''',
     r'''  }).join('')
    : `<tr><td colspan="5" class="bos">${KF_LISTE_FIRMA === 'yok'
        ? 'Firması olmayan kullanıcı yok.'
        : 'Bu firmada kullanıcı yok — "+ Yeni Kullanıcı" ile ekleyebilirsin.'
      }</td></tr>`;
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 8',
     r'''  SECILI_FIRMALAR = (DUZENLENEN && Array.isArray(DUZENLENEN.firmalar))
    ? DUZENLENEN.firmalar.slice() : [];
''',
     r'''  /* YP4: YENİ kullanıcı, listede açık olan firmayla başlar. Liste
     artık firma bazlı; "MILESTONE'un kullanıcıları"na bakarken
     açılan pencere hiçbir firma işaretli gelirse, kaydedilen
     kullanıcı hiçbir firmada çalışamaz ve kendi listesinde bile
     görünmez. */
  SECILI_FIRMALAR = (DUZENLENEN && Array.isArray(DUZENLENEN.firmalar))
    ? DUZENLENEN.firmalar.slice()
    : (typeof KF_LISTE_FIRMA === 'number' ? [KF_LISTE_FIRMA] : []);
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 9',
     r'''/* ── Firma + KDV ── */
/* ═══ FİRMA LOGOSU ═══
   Logo veritabanında saklanır; yüklendiği an tüm belgelerde kullanılır.
   Değiştirmek için yeni dosya seçmek yeterli — eskisi otomatik değişir. */
async function logoYukle() {
  try {
    const d = await api('/api/ayarlar/logo');
''',
     r'''/* ══ FİRMA AYARLARI · PANELDEN, FİRMAYA GİRMEDEN (YP4) ══

   Bu formun düzenlediği firmayı artık oturumdaki seçim değil,
   tablodan tıklanan satır belirliyor. `AYAR_FIRMA` o kimliği
   tutuyor ve aşağıdaki her çağrı onu taşıyor.

   TAŞIMAYI UNUTMAK SESSİZ BİR HATA olurdu: uç, `firma_id` yoksa
   AKTİF firmayı düzenliyor (eski davranış, proforma ekranları hâlâ
   öyle kullanıyor). Panelde aktif firma yok — yani kimlik gitmezse
   istek boşa düşer ya da yanlış firmaya yazar. O yüzden tek bir
   yardımcıdan geçiriliyor; çağrı yerlerinde elle string birleştirmek
   yok. */
let AYAR_FIRMA = null;

function fYol(yol) {
  /* GET için sorgu dizesi, POST/DELETE için gövde — ikisi de
     sunucuda okunuyor. Kimlik yoksa hiç eklenmiyor: o zaman uç
     eski davranışıyla aktif firmayı düzenler. */
  if (!AYAR_FIRMA) return yol;
  return yol + (yol.includes('?') ? '&' : '?') + 'firma_id=' + AYAR_FIRMA;
}

function fGovde(nesne) {
  return JSON.stringify(AYAR_FIRMA
    ? Object.assign({ firma_id: AYAR_FIRMA }, nesne) : nesne);
}

/* ═══ FİRMA LOGOSU ═══
   Logo veritabanında saklanır; yüklendiği an tüm belgelerde kullanılır.
   Değiştirmek için yeni dosya seçmek yeterli — eskisi otomatik değişir. */
async function logoYukle() {
  try {
    const d = await api(fYol('/api/ayarlar/logo'));
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 10',
     r'''        body: JSON.stringify({ logo: okuyucu.result, dosya_adi: dosya.name })
''',
     r'''        body: fGovde({ logo: okuyucu.result, dosya_adi: dosya.name })
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 11',
     r'''    const d = await api('/api/ayarlar/logo', { method: 'DELETE' });
    bildir(d.mesaj || 'Logo kaldırıldı');
    logoYukle();
  } catch (e) { /* */ }
}

async function firmaYukle() {
  try {
    const d = await api('/api/ayarlar/firma');
    document.getElementById('fFirma').value = d.satici_firma || '';
  // MF5: hangi firmayı düzenlediğin başlıkta yazsın.
  const _bf = document.getElementById('fBaslikFirma');
  if (_bf) _bf.textContent = d.firma_ad ? '· ' + d.firma_ad : '';
    document.getElementById('fBelgeKodu').value = d.belge_kodu || '';
    document.getElementById('fAdres').value = d.satici_adres || '';
    document.getElementById('fTelefon').value = d.satici_tel || '';
    document.getElementById('fEposta').value = d.satici_email || '';
  } catch (e) { /* */ }
  logoYukle();
''',
     r'''    const d = await api('/api/ayarlar/logo',
                        { method: 'DELETE', body: fGovde({}) });
    bildir(d.mesaj || 'Logo kaldırıldı');
    logoYukle();
  } catch (e) { /* */ }
}

/* Tablodan bir firmanın "Ayarlar" düğmesine basılınca açılır. */
async function firmaAyarAc(fid) {
  AYAR_FIRMA = fid;
  const f = ((FIRMA_VERI && FIRMA_VERI.firmalar) || [])
            .find(x => x.id === fid);
  document.getElementById('fAyarBaslik').textContent =
    (f && f.ad) ? f.ad + ' · ayarlar' : 'Firma ayarları';
  document.getElementById('firmalarPanel').style.display = 'none';
  document.getElementById('sistemAyarPanel').style.display = 'none';
  document.getElementById('firmaAyarKutu').style.display = '';
  await firmaYukle();
}

function firmaAyarKapat() {
  AYAR_FIRMA = null;
  document.getElementById('firmaAyarKutu').style.display = 'none';
  document.getElementById('firmalarPanel').style.display = '';
  document.getElementById('sistemAyarPanel').style.display = '';
  /* Belge kodu ya da ünvan değişmiş olabilir; tablo tazelensin. */
  firmaListesiYukle();
}

async function firmaYukle() {
  try {
    const d = await api(fYol('/api/ayarlar/firma'));
    document.getElementById('fFirma').value = d.satici_firma || '';
    document.getElementById('fBelgeKodu').value = d.belge_kodu || '';
    document.getElementById('fAdres').value = d.satici_adres || '';
    document.getElementById('fTelefon').value = d.satici_tel || '';
    document.getElementById('fEposta').value = d.satici_email || '';
  } catch (e) { /* */ }
  logoYukle();
}

/* ── TÜM FİRMALAR İÇİN (YP4) ──
   KDV oranı ve avans eşiği firma ayarı DEĞİL: ikisi de `Veriler`de
   firma_id'siz tek satırda duruyor. `firma_id` göndermiyoruz —
   göndermek, firma başına ayrı tutuluyormuş gibi davranmak olurdu
   ve uç yine aynı tek satırı yazardı. */
async function sistemAyarYukle() {
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 12',
     r'''    const d = await api('/api/ayarlar/uretim_avans', { method: 'POST', body: JSON.stringify({ yuzde }) });
''',
     r'''    const d = await api('/api/ayarlar/uretim_avans',
                        { method: 'POST', body: JSON.stringify({ yuzde }) });
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 13',
     r'''      body: JSON.stringify({
        satici_firma: document.getElementById('fFirma').value,
        belge_kodu: document.getElementById('fBelgeKodu').value
                      .trim().toUpperCase(),
      satici_adres: document.getElementById('fAdres').value.trim(),
      satici_tel: document.getElementById('fTelefon').value.trim(),
      satici_email: document.getElementById('fEposta').value.trim()
''',
     r'''      body: fGovde({
        satici_firma: document.getElementById('fFirma').value,
        belge_kodu: document.getElementById('fBelgeKodu').value
                      .trim().toUpperCase(),
        satici_adres: document.getElementById('fAdres').value.trim(),
        satici_tel: document.getElementById('fTelefon').value.trim(),
        satici_email: document.getElementById('fEposta').value.trim()
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 14',
     r'''    await api('/api/ayarlar/kdv_oran', { method: 'POST', body: JSON.stringify({ oran }) });
''',
     r'''    await api('/api/ayarlar/kdv_oran',
                { method: 'POST', body: JSON.stringify({ oran }) });
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 15',
     r'''const yuklendi = { kullanici: false, firma: false, listeler: false, banka: false, yedek: false };
''',
     r'''const yuklendi = { kullanici: false, firmalar: false, listeler: false, banka: false, yedek: false };
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 16',
     r'''const yukleyici = { kullanici: kullaniciYukle,
                    firmalar: firmaListesiYukle,
                    firma: firmaYukle,
''',
     r'''/* YP4: `firma` anahtarı KALKTI — Ayarlar'da artık öyle bir sekme
   yok. Firma ayarları panelin Firmalar sekmesinden, tablodan bir
   firma seçilerek açılıyor (firmaAyarAc). Haritada ölü anahtar
   bırakmak, sekme sanıp aramaya yol açardı. */
const yukleyici = { kullanici: kullaniciYukle,
                    firmalar: firmaListesiYukle,
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 17',
     r'''        ? `<button class="mini-btn" style="color:var(--kirmizi)"
''',
     r'''        ? `<button class="mini-btn" onclick="firmaAyarAc(${f.id})">Ayarlar</button>
           <button class="mini-btn" style="color:var(--kirmizi)"
'''),
    ('templates/ayarlar.html', 'YP4 · templates/ayarlar.html blok 18',
     r'''  kutu.innerHTML = `<button class="btn-yeni" onclick="firmaEkleAc()">+ Yeni Firma</button>`;
''',
     r'''  kutu.innerHTML = `<button class="btn-yeni" onclick="firmaEkleAc()">+ Yeni Firma</button>`;
  sistemAyarYukle();
'''),
    ('tests/test_kritik.py', 'YP4 · tests/test_kritik.py blok 1',
     r'''    yon = a.get('/yonetim').get_data(as_text=True)
    aya = a.get('/ayarlar').get_data(as_text=True)

    # Sistem düzeyi — YALNIZCA yönetimde
    for kimlik in ('kullaniciGovde', 'firmaGovde', 'yedekGovde'):
        assert yon.count(f'id="{kimlik}"') == 1, kimlik
        assert aya.count(f'id="{kimlik}"') == 0, (kimlik, 'ayarlarda da var')

    # Firma düzeyi — YALNIZCA ayarlarda
    for kimlik in ('fFirma', 'bankaGovde', 'lookupIzgara'):
''',
     r'''    # SIRA ÖNEMLİ: /yonetim oturumdaki firma seçimini DÜŞÜRÜYOR
    # (YP4). Önce panele girilirse /ayarlar seçim ekranına çevrilir
    # ve bu test boş sayfayı ölçerdi.
    aya = a.get('/ayarlar').get_data(as_text=True)
    yon = a.get('/yonetim').get_data(as_text=True)

    # Sistem düzeyi — YALNIZCA yönetimde.
    # YP4: `fFirma` (firma ünvanı) buraya KATILDI; firmanın kimliği
    # firmaya ait değil, firmanın KENDİSİ.
    for kimlik in ('kullaniciGovde', 'firmaGovde', 'yedekGovde', 'fFirma'):
        assert yon.count(f'id="{kimlik}"') == 1, kimlik
        assert aya.count(f'id="{kimlik}"') == 0, (kimlik, 'ayarlarda da var')

    # Firma düzeyi — YALNIZCA ayarlarda
    for kimlik in ('bankaGovde', 'lookupIzgara'):
'''),
    ('tests/test_kritik.py', 'YP4 · tests/test_kritik.py blok 2',
     r'''    yon, aya = sekmeler('/yonetim'), sekmeler('/ayarlar')
    assert yon == {'kullanici', 'firmalar', 'yedek'}, yon
    assert aya == {'firma', 'eposta', 'listeler', 'banka'}, aya
''',
     r'''    # /ayarlar ÖNCE: panel firma seçimini düşürüyor (YP4).
    aya, yon = sekmeler('/ayarlar'), sekmeler('/yonetim')
    assert yon == {'kullanici', 'firmalar', 'yedek'}, yon
    # YP4: "Firma Bilgileri" sekmesi panele taşındı.
    assert aya == {'eposta', 'listeler', 'banka'}, aya
'''),
    ('tests/test_kritik.py', 'YP4 · tests/test_kritik.py blok 3',
     r'''    yon = a.get('/yonetim').get_data(as_text=True)
    aya = a.get('/ayarlar').get_data(as_text=True)
''',
     r'''    aya = a.get('/ayarlar').get_data(as_text=True)   # panelden ÖNCE
    yon = a.get('/yonetim').get_data(as_text=True)
'''),
    ('tests/test_kritik.py', 'YP4 · tests/test_kritik.py blok 4',
     r'''    """YP3: 'çıkış yapınca bir önceki sayfaya dönsün'.

    Paneli firma SEÇMEDEN açan (olağan hâli) seçim ekranına döner.
    Bir firmanın içinden gelen ise kaldığı yere döner — onu seçim
    ekranına atmak, yarım işi bıraktırıp yeniden firma seçtirmek
    olurdu."""
    firmasiz = fa.app.test_client()
    with firmasiz.session_transaction() as s:
        s['kullanici'] = 'admin'; s['rol'] = 'ADMIN'; s['_csrf'] = 't'
    h = firmasiz.get('/yonetim').get_data(as_text=True)
    assert 'class="geri-btn" href="/firma-sec"' in h.replace(
        'href="/firma-sec" class="geri-btn"',
        'class="geri-btn" href="/firma-sec"'), 'dönüş bağlantısı yok'

    icerden = istemci('admin', 'ADMIN')      # firma seçili
    h2 = icerden.get('/yonetim').get_data(as_text=True)
    assert '/firma-sec' not in h2
    assert 'geri-btn' in h2 and '/dashboard' in h2
''',
     r'''    """YP3/YP4: panelin TEK kapısı firma seçim ekranı.

    YP3'te iki kapı vardı ve ikisi de yanlış yere açılıyordu:
    "← MİLESTONE…" firmanın İÇİNE giriyordu (panel firma üstüyse
    oradan bir firmaya girilememeli), "Çıkış" ise sistemden
    atıyordu. İkisi de kalktı."""
    # İki giriş yolu da aynı yere çıkmalı: firma seçmeden gelen de,
    # bir firmanın içinden (sol raydan) gelen de.
    for kurulum in (lambda: fa.app.test_client(),
                    lambda: istemci('admin', 'ADMIN')):
        c = kurulum()
        with c.session_transaction() as s:
            s['kullanici'] = 'admin'; s['rol'] = 'ADMIN'; s['_csrf'] = 't'
        h = c.get('/yonetim').get_data(as_text=True)
        assert 'geri-btn' in h, 'dönüş bağlantısı yok'
        assert '/firma-sec' in h
        # Firmaya açılan kapı YOK: ne dashboard bağlantısı ne de
        # oturumu kapatan Çıkış.
        #
        # SINIFA DEĞİL BAĞLANTIYA bakılıyor: `.cikis-btn` kuralı
        # <style> içinde her sayfada duruyor (tek stil bloğu, bütün
        # sayfalar aynı kabuktan geliyor). Sınıf adını aramak,
        # düğme basılmasa da eşleşirdi.
        assert 'href="/cikis"' not in h, 'panelde oturum kapatma var'
        assert 'href="/dashboard"' not in h, 'panelden firmaya giriliyor'


def test_yp4_panele_girince_firma_secimi_dusuyor():
    """YP4: panelde firma seçili DEĞİLDİR — değişmez kural.

    Seçim korunsaydı ekranda ona açılan bir kapı doğabilirdi; YP3'te
    tam bu oldu. Seçimi girişte düşürmek, 'firma seçili panel' diye
    ikinci bir durumun var olmasını engelliyor."""
    c = istemci('admin', 'ADMIN')
    with c.session_transaction() as s:
        assert s.get('firma_id'), 'ön koşul: firma seçili başlamalı'
    assert c.get('/yonetim').status_code == 200
    with c.session_transaction() as s:
        assert not s.get('firma_id'), 'panel firma seçimini düşürmedi'
'''),
    ('tests/test_kritik.py', 'YP4 · tests/test_kritik.py blok 5',
     r'''    for yol in ('/yonetim', '/ayarlar'):
''',
     r'''    # /ayarlar ÖNCE: panele girmek firma seçimini düşürüyor (YP4).
    for yol in ('/ayarlar', '/yonetim'):
'''),
    ('tests/test_kritik.py', 'YP4 · tests/test_kritik.py blok 6',
     r'''        assert Firma.query.get(yeni) is None
''',
     r'''        assert Firma.query.get(yeni) is None


# ══════════════════════════════════════════════════════════════════════
#  YP4 · FİRMA AYARLARI PANELDEN, FİRMAYA GİRMEDEN
# ══════════════════════════════════════════════════════════════════════

def test_yp4_baska_firmanin_ayari_firmaya_girmeden_duzenlenir():
    """YP4: `firma_id` hedefi belirler — oturumdaki seçim değil.

    Bu testin asıl işi YAZILANIN DOĞRU FİRMAYA gittiğini ölçmek.
    Kimlik taşınmazsa uç eski davranışına düşüp AKTİF firmayı
    düzenler; panelde aktif firma olmadığı için de ya boşa yazar ya
    da — seçim kalmış olsaydı — yanlış firmanın ünvanını değiştirirdi.
    MF3B'de can yakan tuzak buydu."""
    from models import Firma
    a = istemci('admin', 'ADMIN')
    r = a.post('/api/firma', headers=H, json={
        'ad': 'YP4 HEDEF', 'belge_kodu': 'Y4',
        'ortak_cari': False, 'ortak_liste': False})
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    hedef = r.get_json()['id']
    with fa.app.app_context():
        baska = (Firma.query.filter(Firma.id != hedef, Firma.aktif.is_(True))
                 .order_by(Firma.id).first())
        assert baska, 'ön koşul: en az iki firma'
        baska_id, baska_unvan = baska.id, baska.unvan

    # Panel: firma SEÇİLİ DEĞİL
    c = fa.app.test_client()
    with c.session_transaction() as s:
        s['kullanici'] = 'admin'; s['rol'] = 'ADMIN'; s['_csrf'] = 't'

    d = c.post('/api/ayarlar/firma', headers=H, json={
        'firma_id': hedef, 'satici_firma': 'YP4 HEDEF A.Ş.',
        'satici_adres': 'DENİZLİ'})
    assert d.status_code == 200, d.get_data(as_text=True)

    with fa.app.app_context():
        assert Firma.query.get(hedef).unvan == 'YP4 HEDEF A.Ş.'
        # Komşu firma DOKUNULMAMIŞ olmalı
        assert Firma.query.get(baska_id).unvan == baska_unvan

    g = c.get(f'/api/ayarlar/firma?firma_id={hedef}', headers=H)
    assert g.status_code == 200
    assert g.get_json()['satici_firma'] == 'YP4 HEDEF A.Ş.'


def test_yp4_kdv_ve_avans_sistem_geneli_kaliyor():
    """YP4: KDV oranı ve avans eşiği FİRMA AYARI DEĞİL.

    ÖLÇÜLDÜ (18.10): panelden firma B için %18 yazıldı, firma A da
    %18 okudu — çünkü ikisi de `Veriler`de firma_id'si NULL tek
    satırda duruyor. Damga `Veriler`i bilerek atlıyor
    (models._firma_damgasi), yani bu satırlar hiçbir zaman firmaya
    damgalanmıyor.

    Bu yüzden ikisi bir firmanın ayar kutusunda DEĞİL, panelde
    "Tüm firmalar için" başlığı altında duruyor. Test, yarın biri
    onları firma kutusuna taşımak isterse önce bu gerçeğe çarpsın
    diye burada: davranış değişecekse veri taşıma gerekiyor."""
    from models import Firma
    a = istemci('admin', 'ADMIN')
    r = a.post('/api/firma', headers=H, json={
        'ad': 'YP4 KDV', 'belge_kodu': 'Y4K',
        'ortak_cari': False, 'ortak_liste': False})
    hedef = r.get_json()['id']

    c = fa.app.test_client()
    with c.session_transaction() as s:
        s['kullanici'] = 'admin'; s['rol'] = 'ADMIN'; s['_csrf'] = 't'
    assert c.post('/api/ayarlar/kdv_oran', headers=H,
                  json={'oran': 18}).status_code == 200

    with fa.app.app_context():
        ilk = Firma.query.filter(Firma.id != hedef).order_by(Firma.id).first()
    for fid in (hedef, ilk.id):
        okundu = c.get(f'/api/ayarlar/kdv_oran?firma_id={fid}', headers=H)
        assert float(okundu.get_json()['oran']) == 18.0, fid

    # Ekran da öyle söylüyor: oran firma kutusunda değil, "Tüm
    # firmalar için" panelinde.
    h = a.get('/yonetim').get_data(as_text=True)
    assert 'id="sistemAyarPanel"' in h
    assert h.index('id="sistemAyarPanel"') < h.index('id="fKdv"')
    assert h.index('id="firmaAyarKutu"') > h.index('id="fKdv"')


def test_yp4_baska_firmanin_ayarini_yonetici_olmayan_duzenleyemez():
    """YP4: `firma_id` yetki yükseltme kapısı OLMAMALI.

    Kendi firmasının ayarını düzenleyebilen bir kullanıcı, kimliği
    değiştirerek başka firmanın ünvanını değiştirememeli."""
    from models import Firma
    with fa.app.app_context():
        hedef = Firma.query.filter_by(aktif=True).order_by(Firma.id).first().id
    c = istemci('mudur_yp4', 'MUDUR')
    r = c.post('/api/ayarlar/firma', headers=H,
               json={'firma_id': hedef, 'satici_firma': 'OLMAZ'})
    assert r.status_code == 403, r.status_code
    with fa.app.app_context():
        assert Firma.query.get(hedef).unvan != 'OLMAZ'


def test_yp4_olmayan_firma_kimligi_reddedilir():
    """YP4: doğrulanmamış kimlikle bağlam çevirmek, olmayan bir
    firmaya yazma damgası basmak olurdu."""
    c = fa.app.test_client()
    with c.session_transaction() as s:
        s['kullanici'] = 'admin'; s['rol'] = 'ADMIN'; s['_csrf'] = 't'
    assert c.get('/api/ayarlar/firma?firma_id=999999',
                 headers=H).status_code == 404
    assert c.get('/api/ayarlar/firma?firma_id=abc',
                 headers=H).status_code == 400


def test_yp4_kullanici_listesi_firma_bazli():
    """YP4: kullanıcılar firma seçilerek listeleniyor.

    Süzme istemcide; uç zaten her kullanıcının `firma_kapsam` ve
    `firmalar` alanlarını veriyor. Test ikisini birden sabitliyor:
    ekranda seçim kutusu ve süzgeç VAR, uçta da süzmeyi besleyen
    alanlar VAR. Alanlardan biri uçtan düşerse liste sessizce
    herkesi gösterirdi."""
    a = istemci('admin', 'ADMIN')
    h = a.get('/yonetim').get_data(as_text=True)
    assert 'id="kullaniciFirmaSecim"' in h
    assert 'function _kfGorunur' in h
    assert 'kullaniciFirmaDegisti' in h
    # Hiçbir firmaya atanmamış kullanıcı EKRANDAN KAYBOLMAMALI:
    # seçim kutusunda kendi satırı var.
    assert 'Firması olmayanlar' in h

    d = a.get('/api/ayarlar/kullanici', headers=H)
    assert d.status_code == 200
    kayitlar = d.get_json()
    assert kayitlar, 'ön koşul: en az bir kullanıcı'
    for u in kayitlar:
        assert 'firma_kapsam' in u, u.get('ad')
        assert isinstance(u.get('firmalar'), list), u.get('ad')
'''),
]



def main():
    print('=' * 70)
    print('  YAMA YP4 — PANEL FIRMA USTUNE CIKIYOR')
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
        print('  ⊙ Yama YP4 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_yp4.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_yp4'
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
    print('    1) sudo systemctl restart milestone-erp')
    print('    2) Tarayicida Ctrl+F5')
    print()
    print('  BAKILACAK YERLER')
    print('    · Panelde sag ustte yalnizca "Firma secimine don"')
    print('      var; Cikis ve firma dugmesi gitti.')
    print('    · Kullanicilar sekmesinde ustte FIRMA secimi.')
    print('    · Firmalar sekmesinde her satirda "Ayarlar":')
    print('      firmaya GIRMEDEN unvan/belge kodu/logo.')
    print('    · Ayarlar sayfasi artik E-posta ile aciliyor;')
    print('      firma kimligi orada YOK.')
    print()
    print('    3) venv/bin/python -m pytest tests/test_kritik.py -q')
    print('       venv/bin/python firma_denetim.py')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

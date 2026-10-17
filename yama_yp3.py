#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA YP3 — PANEL YALIN KABUK · FİRMA İŞLERİ TEK YERDE
======================================================

ÖNKOŞUL: yama_yp.py uygulanmış olmalı (o da kf, kf5, kf6 istiyor).

── NE İSTENDİ ──
  1. Firma seçim ekranındaki "+ Yeni firma ekle" kalksın, yerine
     yönetim paneli düğmesi gelsin; firma ekleme panelden yapılsın.
  2. Panelde DİĞER MENÜLER olmasın — admin firma seçmeden panele
     giriyor ve oradan diğer menülere geçebiliyordu.
  3. Panelden çıkınca bir önceki sayfaya, yani firma seçim
     ekranına dönsün; firmayı orada seçip öyle girsin.

── 1 · FİRMA AÇMA/SİLME TEK YERE TOPLANDI ──
  Seçim ekranındaki ekleme formu ve Sil düğmesi kaldırıldı; ikisi
  de panelin Firmalar sekmesinde zaten vardı/şimdi var. Sebep sade:
  aynı formun iki kopyası iki ekranda yaşarsa ikisi ayrı ayrı bakım
  ister ve biri düzeltilip öteki unutulur.

  Sil düğmesi KARTIN İÇİNDEYDİ — firmaya girmek için basılacak
  düğmenin üstünde. Tıklamayı yutması için ayrıca kod gerekiyordu
  (stopPropagation); yutmasaydı silinecek firmaya GEÇİLİRDİ.
  O ekranın tek işi "nerede çalışacağım" sorusunu sormak.

  Panele taşınan silme, dökümü ÖNCE gösteriyor: "STONEHUB USA
  firmasında 12.480 kayıt var: stok 4.210 · cari_hareket 3.180 …
  Hepsi silinecek." Boş firmada düğme "Sil" yazıyor, dolu firmada
  "Yedekle ve sil" — sunucu boş firmada yedek ALMIYOR ve alınmayan
  bir yedeği söz vermek doğru olmaz.

── 2 · PANELİN KABUĞU YALIN ──
  base.html `PANEL='yonetim'` görünce sol rayı ve arama kutusunu
  BASMIYOR. Ray oradayken "Depo", "Finans", "Satış" duruyordu;
  hiçbiri firma seçilmeden açılamaz, basınca seçim ekranına geri
  atıyordu. Görünen ama çalışmayan menü, olmayan menüden kötüdür:
  sistem bozukmuş gibi durur.

  Ctrl+K kısayolu hâlâ bağlı olduğu için paleti bir bayrak
  kapatıyor (`window.YALIN_PANEL`); aradığı şeylerin hepsi
  (blok, kasa, müşteri, fatura) firmaya bağlı veri.

  Üst barda kalanlar menü değil: tarih, kur, kullanıcı, çıkış.
  Firma çipi de kalktı — panel firmaların ÜSTÜNDE, orada
  "çalışılan firma" diye bir şey yok.

── 3 · PANELDEN ÇIKIŞ ──
  Üst barda tek bir dönüş bağlantısı var ve nereye döneceğini
  oturum belirliyor:

    firma seçilmemiş (olağan hâli) → "← Firma seçimine dön"
    bir firmanın içinden gelinmiş  → "← <FİRMA ADI>"

  İkincisi bilerek: sol raydaki Sistem menüsünden panele giren
  biri yarım bıraktığı işin başına döner. Onu da seçim ekranına
  atmak, iş ortasında yeniden firma seçtirmek olurdu.

── YOL ÜSTÜNDE BULUNAN İKİ ARIZA (ikisi de YP'den) ──
  Gönderdiğin ekran görüntüsünde Kullanıcılar sekmesinin ALTINDA
  bir "Firmalar" paneli duruyordu ve sonsuza kadar "Yükleniyor…"
  yazıyordu. Sebep: `b-firmalar` bölümü de `aktif` basılıyordu.
  İki bölüm birden açıktı; yükleyicisi ise sekme tıklanmadığı için
  hiç koşmuyordu. Bölüm `aktif` olmaktan çıkarıldı.

  Aynı hatanın TERSİ Ayarlar'daydı ve onu henüz görmemiştin:
  YP2'de ilk sekme `kullanici`dan `firma`ya geçti ama `aktif`
  bölüm `b-firma` değildi — Ayarlar'ın altı BOMBOŞ açılıyordu.
  `aktif` oraya eklendi.

  Kural artık testle sabit (test_yp3_her_sayfada_TEK_bolum_acik):
  her sayfada tam bir bölüm açık ve açık bölümün adı açık sekmenin
  adıyla AYNI.

── ÖLÇÜLDÜ ──
  /yonetim   ray YOK · arama YOK · kabuk "yalin"
             dönüş: "← Firma seçimine dön" → /firma-sec
             açık bölüm [b-kullanici] = açık sekme [kullanici]
  /yonetim (firma seçiliyken)
             dönüş: "← MILESTONE…" → /dashboard
  /ayarlar   ray VAR · arama VAR
             açık bölüm [b-firma] = açık sekme [firma]
  /firma-sec ekleme formu YOK · silme penceresi YOK · <input> YOK
             "Yönetim paneli" düğmesi VAR

  104 test geçti (99 + 5 yeni kalıcı test);
  firma · js · form · zincir · akis denetimleri temiz.

  BU SEFER GÖZLE DE BAKILDI. Dört ekran Chromium'da basıldı:
  panel (Kullanıcılar ve Firmalar sekmeleri), Ayarlar, firma seçim
  ekranı ve silme onay penceresi — biri 12.480 kayıtlık dolu bir
  firmayla, uzun döküm pencereyi taşırıyor mu diye.

  Önceki denemeler neden tutmuyordu, bulundu: base.html'deki
  oturum HEARTBEAT kapısı localStorage'da damga arıyor ve damgayı
  sunucu yalnızca oturumda `taze_giris` varken yazdırıyor. Çerezi
  kendim imzaladığım için o bayrak yoktu; sayfa açılıyor, JS
  hemen /cikis'e gidiyordu ve elime giriş ekranı geçiyordu.

DOSYALAR
--------
  flask_app.py              bayatlayan 4 açıklama (yeni firma artık
                            seçim ekranında açılmıyor)
  templates/base.html       yalın kabuk · dönüş bağlantısı · palet
  templates/ayarlar.html    bölüm/sekme eşleşmesi · firma silme
  templates/firma_sec.html  ekleme formu ve silme penceresi kalktı,
                            yerine panel düğmesi
  tests/test_kritik.py      5 yeni test

Şema yok, göç yok. Veri dokunulmuyor.

KULLANIM
--------
  python3 yama_yp3.py            # RAPOR
  python3 yama_yp3.py --uygula
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
    'flask_app.py': 'YP3 · YENİ FİRMA ARTIK BURADA DEĞİL',
    'templates/base.html': 'YALIN KABUK · YÖNETİM PANELİ (YP3)',
    'templates/ayarlar.html': 'FİRMA SİL (YP3)',
    'templates/firma_sec.html': 'YÖNETİM PANELİ DÜĞMESİ (YP3)',
    'tests/test_kritik.py': 'def test_yp3_panelde_ray_ve_arama_basilmaz',
}
ONKOSUL = {
    'flask_app.py': 'def yonetim_sayfa',
    'templates/base.html': 'YP1: Yönetim paneli',
    'templates/ayarlar.html': 'SEKMELER ROTAYA GÖRE (YP2)',
    'templates/firma_sec.html': 'YP1 · YÖNETİM PANELİ',
    'tests/test_kritik.py': 'def test_yp_panel_firma_secmeden_acilir',
}

DEGISIKLIKLER = [
    ('flask_app.py', 'YP3 · flask_app.py blok 1',
     r'''                #              (Admin bu kuralın dışında: tek firma
                #              olsa da ekranı görür, çünkü YENİ
                #              FİRMA oradan açılıyor ve bunu bir
                #              firmanın içine girmeden yapabilmek
                #              gerekiyor — MF3C.)
''',
     r'''                #              (Admin bu kuralın dışında: tek firma
                #              olsa da ekranı görür. YP3'te sebebi
                #              değişti — yeni firma artık orada
                #              açılmıyor — ama ekran hâlâ ZORUNLU:
                #              YÖNETİM PANELİNİN kapısı orada ve
                #              panele bir firmaya girmeden
                #              ulaşabilmek gerekiyor.)
'''),
    ('flask_app.py', 'YP3 · flask_app.py blok 2',
     r'''
        Yeni firma da BURADAN açılır — bir firmanın ayarlarının
        içinden değil. Eski düzende A'nın ayarlarındayken B ekleniyor,
        hemen altındaki "Firma Bilgileri" formu ise hâlâ A'yı
        düzenliyordu; yeni firmanın unvanını oraya yazmak A'nın
        unvanını sessizce değiştirirdi.
''',
     r'''
        YP3 · YENİ FİRMA ARTIK BURADA DEĞİL. Form (ve firma silme)
        Yönetim paneline taşındı; bu ekranda yalnızca panelin
        bağlantısı var. Sebep: firma açmak/silmek bir firmaya AİT
        OLMAYAN bir iş ve aynı formun iki kopyasını iki ekranda
        sürdürmek, ikisinin ayrı ayrı bakım istemesi demekti.

        Taşınırken korunan kural: form hangi ekranda olursa olsun
        BİR FİRMANIN AYARLARININ İÇİNDE olamaz. Eski düzende A'nın
        ayarlarındayken B ekleniyor, hemen altındaki "Firma
        Bilgileri" formu ise hâlâ A'yı düzenliyordu; yeni firmanın
        unvanını oraya yazmak A'nın unvanını sessizce değiştirirdi.
        Panel firma bağlamının dışında olduğu için bu tuzak yok.
'''),
    ('flask_app.py', 'YP3 · flask_app.py blok 3',
     r'''                        .order_by(Firma.sira, Firma.id).all())
        # MF3C: admin'de tek firma varken de açılır — ekranın işi
        # yalnızca seçtirmek değil, YENİ FİRMA buradan açılıyor ve
        # bunu bir firmanın içine girmeden yapabilmek gerekiyor.
''',
     r'''                        .order_by(Firma.sira, Firma.id).all())
        # MF3C · YP3: admin'de tek firma varken de açılır — ekranın
        # işi yalnızca seçtirmek değil, YÖNETİM PANELİNİN kapısı da
        # burası ve panele bir firmanın içine girmeden ulaşabilmek
        # gerekiyor. (MF3C'de sebep "yeni firma buradan açılıyor"du;
        # form panele taşındı, kapı kaldı.)
'''),
    ('flask_app.py', 'YP3 · flask_app.py blok 4',
     r'''        kullanıcı kaldığı firmaya döner.
''',
     r'''        kullanıcı kaldığı firmaya döner.

        YP3 · KABUK DA YALIN. Şablon `PANEL='yonetim'` görünce
        base.html sol rayı ve aramayı BASMIYOR. Ray oradayken
        "Depo", "Finans", "Satış" görünüyordu; hiçbiri firma
        seçilmeden açılamaz, basınca seçim ekranına geri atıyordu —
        görünen ama çalışmayan menü. Panelden tek çıkış, üst
        bardaki dönüş bağlantısı: firma seçilmemişse seçim
        ekranına, seçilmişse kalınan firmaya.
'''),
    ('templates/base.html', 'YP3 · templates/base.html blok 1',
     r'''.kabuk{display:grid;grid-template-columns:76px minmax(0,1fr);min-height:100vh}
''',
     r'''.kabuk{display:grid;grid-template-columns:76px minmax(0,1fr);min-height:100vh}

/* ── YALIN KABUK · YÖNETİM PANELİ (YP3) ──
   Panel firma bağlamının DIŞINDA çalışıyor. Sol ray oradayken
   "Depo", "Finans", "Satış" düğmeleri duruyordu — hepsi firma
   seçilmeden açılamayan ekranlar. Basınca seçim ekranına geri
   atılıyorlardı: görünen ama çalışmayan menü.

   Ray basılmadığı için ilk sütun da kalkmalı; yoksa 76px'lik boş
   bir şerit kalırdı. */
.kabuk.yalin{grid-template-columns:minmax(0,1fr)}
.yalin-marka{display:flex;align-items:center;gap:11px;flex:1;min-width:0}
.yalin-marka .im{width:30px;height:30px;border-radius:8px;background:var(--murekkep);
  display:flex;align-items:center;justify-content:center;flex:0 0 30px}
.yalin-marka .im svg{stroke:#fff}
.yalin-marka .ad{font-family:var(--baslik);font-weight:700;font-size:1rem;
  letter-spacing:-.01em}
.yalin-marka .etiket{font-size:.78rem;color:var(--soluk)}
.geri-btn{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--cizgi-koyu);
  background:var(--yuzey);border-radius:8px;padding:7px 13px;font-size:.84rem;
  font-weight:600;color:var(--murekkep);text-decoration:none;white-space:nowrap;
  transition:border-color .15s,color .15s}
.geri-btn:hover{border-color:var(--verde);color:var(--verde)}
@media (max-width:760px){.yalin-marka .etiket{display:none}}
'''),
    ('templates/base.html', 'YP3 · templates/base.html blok 2',
     r'''{% macro alan_var(moduller) %}{% for m in moduller %}{% if y.get(m,'gizli') != 'gizli' %}1{% endif %}{% endfor %}{% endmacro %}
''',
     r'''{% macro alan_var(moduller) %}{% for m in moduller %}{% if y.get(m,'gizli') != 'gizli' %}1{% endif %}{% endfor %}{% endmacro %}
{# ── YALIN MOD (YP3) ──
   Yönetim paneli firma bağlamının DIŞINDA. Ray ve arama
   basılmıyor: hepsi firma seçilmeden açılamayan ekranlara
   gidiyordu. `|default('')` ŞART — base.html'i PANEL tanımlamadan
   kullanan onlarca sayfa var. #}
{% set yalin = (PANEL|default('') == 'yonetim') %}
'''),
    ('templates/base.html', 'YP3 · templates/base.html blok 3',
     r'''
<div class="kabuk">
''',
     r'''
<div class="kabuk{% if yalin %} yalin{% endif %}">
  {% if not yalin %}
'''),
    ('templates/base.html', 'YP3 · templates/base.html blok 4',
     r'''    {% endif %}
  </nav>
''',
     r'''    {% endif %}
  </nav>
  {% endif %}
'''),
    ('templates/base.html', 'YP3 · templates/base.html blok 5',
     r'''    <header class="ust">
''',
     r'''    <header class="ust">
      {% if yalin %}
      {# Panelde arama kutusu da yok: palet blok/kasa/müşteri arıyor,
         hepsi firmaya bağlı veri. Yerine nerede olunduğunu söyleyen
         sabit bir başlık. #}
      <div class="yalin-marka">
        <span class="im"><svg width="17" height="17" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="1.9"><path d="M3 21h18"/>
          <path d="M5 21V7l7-4 7 4v14"/><path d="M10 21v-6h4v6"/></svg></span>
        <span class="ad">Yönetim</span>
        <span class="etiket">· firma üstü ayarlar</span>
      </div>
      {% else %}
'''),
    ('templates/base.html', 'YP3 · templates/base.html blok 6',
     r'''        <kbd>Ctrl K</kbd>
      </button>
''',
     r'''        <kbd>Ctrl K</kbd>
      </button>
      {% endif %}
'''),
    ('templates/base.html', 'YP3 · templates/base.html blok 7',
     r'''      <div class="ust-sag">
''',
     r'''      <div class="ust-sag">
        {# ── PANELDEN ÇIKIŞ (YP3) ──
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
        {% endif %}
'''),
    ('templates/base.html', 'YP3 · templates/base.html blok 8',
     r'''           arasında geçmek için çıkış yapıp yeniden girmek zorunda
           kalıyordu. #}
        {% if firma_listesi and firma_listesi|length > 1 %}
''',
     r'''           arasında geçmek için çıkış yapıp yeniden girmek zorunda
           kalıyordu.

           YP3: panelde basılmaz. Panel firmaların ÜSTÜNDE duruyor;
           orada "çalışılan firma" diye bir şey yok. #}
        {% if not yalin and firma_listesi and firma_listesi|length > 1 %}
'''),
    ('templates/base.html', 'YP3 · templates/base.html blok 9',
     r'''window.AKTIF_FIRMA = {{ (aktif_firma.id if aktif_firma else 0)|tojson }};
''',
     r'''window.AKTIF_FIRMA = {{ (aktif_firma.id if aktif_firma else 0)|tojson }};
/* YP3: yalın kabuk (yönetim paneli). Arama düğmesi basılmıyor ama
   Ctrl+K kısayolu hâlâ bağlı — paleti oradan da açtırmıyoruz;
   aradığı şeylerin hepsi (blok, kasa, müşteri) firmaya bağlı. */
window.YALIN_PANEL = {{ (yalin|default(false))|tojson }};
'''),
    ('templates/base.html', 'YP3 · templates/base.html blok 10',
     r'''function paletAc() {
''',
     r'''function paletAc() {
  if (window.YALIN_PANEL) return;   // YP3
'''),
    ('templates/ayarlar.html', 'YP3 · templates/ayarlar.html blok 1',
     r'''     Yönetim panelinde; Ayarlar'da yalnızca AKTİF FİRMANIN kimliği
     düzenleniyor. Ayrım ölçütü: tablosu `firma_id` taşıyor mu. -->
<section class="bolum aktif" id="b-firmalar">
''',
     r'''     Yönetim panelinde; Ayarlar'da yalnızca AKTİF FİRMANIN kimliği
     düzenleniyor. Ayrım ölçütü: tablosu `firma_id` taşıyor mu.

     YP3 · `aktif` BURADAN ALINDI. Bölümler `.bolum.aktif` ile
     gösteriliyor ve bu bölüm de aktif basılıyordu: Kullanıcılar
     sekmesindeyken Firmalar paneli de AYNI ANDA görünüyordu —
     üstelik yükleyicisi (sekme tıklanmadığı için) hiç koşmadığından
     sonsuza kadar "Yükleniyor…" yazıyordu. Hangi bölümün açık
     geleceğini `.sekme.aktif` söylüyor; ikisi TEK olmalı. -->
<section class="bolum" id="b-firmalar">
'''),
    ('templates/ayarlar.html', 'YP3 · templates/ayarlar.html blok 2',
     r'''      Her firmanın stoğu, siparişi, kasası ve defteri ayrıdır.
      Bir firmanın <b>ünvanı, logosu ve belge kodu</b> o firmaya
      geçip Ayarlar → Firma Bilgileri'nden düzenlenir.</p>
''',
     r'''      Her firmanın stoğu, siparişi, kasası ve defteri ayrıdır.
      Firma <b>açmak ve silmek</b> buradan yapılır — bir firmanın
      içine girmeden. Bir firmanın <b>ünvanı, logosu ve belge
      kodu</b> ise o firmaya ait: o firmaya geçip Ayarlar → Firma
      Bilgileri'nden düzenlenir.</p>
'''),
    ('templates/ayarlar.html', 'YP3 · templates/ayarlar.html blok 3',
     r'''{% if PANEL != 'yonetim' %}
<section class="bolum" id="b-firma">
''',
     r'''{% if PANEL != 'yonetim' %}
<section class="bolum aktif" id="b-firma">
'''),
    ('templates/ayarlar.html', 'YP3 · templates/ayarlar.html blok 4',
     r'''       için önce üst bardan o firmaya geç. Firma AÇMA/SİLME burada
       DEĞİL, Yönetim panelinde (YP2). -->
''',
     r'''       için önce üst bardan o firmaya geç. Firma AÇMA/SİLME burada
       DEĞİL, Yönetim panelinde (YP2).

       YP3 · `aktif` BURAYA EKLENDİ. Ayarlar'ın ilk sekmesi YP2'de
       `kullanici`dan `firma`ya geçti ama açılışta görünen bölüm
       değişmedi: sekme "Firma Bilgileri"nde duruyor, altı ise
       BOMBOŞ açılıyordu. Açık sekme ile açık bölüm aynı adı
       göstermek zorunda. -->
'''),
    ('templates/ayarlar.html', 'YP3 · templates/ayarlar.html blok 5',
     r'''      <td class="mono">${kacar(f.vergi_no || '—')}</td>
      <td class="sag">${(FIRMA_VERI.admin && f.id !== FIRMA_VERI.aktif)
        ? `<button class="mini-btn" onclick="firmaGec(${f.id})">Bu firmaya geç</button>` : ''}</td>
''',
     r'''      <td class="mono">${kacar(f.vergi_no || '—')}</td>
      <td class="sag">${FIRMA_VERI.admin
        ? `<button class="mini-btn" style="color:var(--kirmizi)"
             onclick="firmaSilAc(${f.id})">Sil</button>` : ''}</td>
'''),
    ('templates/ayarlar.html', 'YP3 · templates/ayarlar.html blok 6',
     r'''
async function firmaGec(id) {
''',
     r'''
/* ── FİRMA SİL (YP3) ──
   Silme firma seçim ekranından BURAYA taşındı. Oradaki yeri
   yanlıştı: o ekran "nerede çalışacağım" ekranı ve kartın İÇİNDE
   duran Sil, girmek için basılacak düğmenin üstündeydi.

   "Bu firmaya geç" düğmesi de kalktı. Panel firma bağlamının
   DIŞINDA; içeriden bir firmaya girmek, panelden çıkarken nereye
   döneceğini belirsizleştiriyordu. Firmaya giriş tek kapıdan:
   firma seçim ekranı.

   Döküm ÖNCE gösteriliyor. "1.240 kayıt silinecek" ile "bu firma
   boş" arasındaki fark, onay penceresinin tek işi. */
async function firmaSilAc(id) {
  const f = ((FIRMA_VERI && FIRMA_VERI.firmalar) || [])
            .find(x => x.id === id);
  const ad = (f && f.ad) || ('#' + id);
  let o;
'''),
    ('templates/ayarlar.html', 'YP3 · templates/ayarlar.html blok 7',
     r'''  try {
    const d = await api('/api/firma/sec', {
      method: 'POST', body: JSON.stringify({ firma_id: id }) });
    if (d && d.ok) location.reload();
    else bildir((d && d.mesaj) || 'Geçilemedi', true);
  } catch (e) { bildir('Geçilemedi', true); }
''',
     r'''  try {
    o = await api('/api/firma/' + id + '/ozet');
  } catch (e) { bildir('Firma bilgisi okunamadı', true); return; }
  if (!o || !o.ok) { bildir((o && o.mesaj) || 'Firma bilgisi okunamadı', true); return; }
  /* Sunucu engeli (son firma, içinde bulunduğun firma, birilerinin
     TEK firması) onay penceresinden ÖNCE söylenir — kullanıcıyı
     "Evet"e tıklatıp sonra reddetmek kaba olurdu. */
  if (o.engel) { bildir(o.engel, true); return; }

  /* Düğmenin yazısı da KAYIT SAYISINA bağlı. Boş firmada sunucu
     yedek ALMIYOR (toplam > 0 şartı); "Yedekle ve sil" yazmak
     alınmayan bir yedeği söz vermek olurdu. */
  let metin;
  if (o.kayit_sayisi > 0) {
    const d = Object.entries(o.dagilim || {})
      .sort((a, b) => b[1] - a[1]).slice(0, 12)
      .map(([t, n]) => `${t} ${n.toLocaleString('tr-TR')}`).join(' · ');
    metin = `${ad} firmasında ${o.kayit_sayisi.toLocaleString('tr-TR')}`
          + ` kayıt var:\n\n${d}\n\nHepsi silinecek. Silmeden önce tam`
          + ` veritabanı yedeği alınır; yedek alınamazsa silme yapılmaz.`;
  } else {
    metin = `${ad} firmasında hiç kayıt yok. Doğrudan silinecek.`;
  }
  if (!await onayla(metin, { baslik: 'Firmayı sil', tehlike: true,
        tamam: o.kayit_sayisi > 0 ? 'Yedekle ve sil' : 'Sil' })) return;
  try {
    const d = await api('/api/firma/' + id, { method: 'DELETE' });
    if (d && d.ok) { bildir(d.mesaj || 'Firma silindi'); await firmaListesiYukle(); }
    else bildir((d && d.mesaj) || 'Silinemedi', true);
  } catch (e) { bildir('Silinemedi', true); }
'''),
    ('templates/firma_sec.html', 'YP3 · templates/firma_sec.html blok 1',
     r'''.ayrac::before,.ayrac::after{content:"";flex:1;height:1px;background:var(--cizgi)}
.ekle-btn{width:100%;background:transparent;border:1px dashed var(--cizgi-koyu);
  border-radius:12px;padding:14px;font-family:inherit;font-size:.92rem;
  font-weight:600;color:var(--soluk);cursor:pointer;transition:all .14s}
.ekle-btn:hover{border-color:var(--verde);color:var(--verde);background:var(--yuzey)}
.form{background:var(--yuzey);border:1px solid var(--cizgi);border-radius:12px;padding:18px}
.form h2{font-family:var(--baslik);font-size:1.05rem;margin-bottom:6px}
.form p{color:var(--soluk);font-size:.83rem;margin-bottom:14px;line-height:1.5}
.ikili{display:grid;grid-template-columns:1fr 110px;gap:12px}
.alan{margin-bottom:12px}
.alan label{display:block;font-size:.76rem;font-weight:600;letter-spacing:.04em;
  text-transform:uppercase;color:var(--soluk);margin-bottom:5px}
.alan input{width:100%;padding:10px 12px;border:1px solid var(--cizgi-koyu);
  border-radius:8px;font-family:inherit;font-size:.95rem;background:var(--taban);
''',
     r'''.ayrac::before,.ayrac::after{content:"";flex:1;height:1px;background:var(--cizgi)}
/* ── YÖNETİM PANELİ DÜĞMESİ (YP3) ──
   Burası "+ Yeni firma ekle"nin yeriydi. Form, onay penceresi ve
   Sil düğmesiyle birlikte kalktı; bu ekranın tek işi seçtirmek.
   Firma açma/silme ve kullanıcı işleri panelde. */
.panel-btn{display:block;width:100%;text-align:center;text-decoration:none;
  background:transparent;border:1px dashed var(--cizgi-koyu);border-radius:12px;
  padding:14px;font-family:inherit;cursor:pointer;transition:all .14s}
.panel-btn:hover{border-color:var(--verde);background:var(--yuzey)}
.panel-btn .pb-ad{display:block;font-size:.95rem;font-weight:700;
'''),
    ('templates/firma_sec.html', 'YP3 · templates/firma_sec.html blok 2',
     r'''  color:var(--murekkep)}
.alan input:focus{outline:0;border-color:var(--verde);background:var(--yuzey)}
.dugmeler{display:flex;gap:8px;margin-top:4px}
.bas{background:var(--verde);color:#fff;border:0;border-radius:8px;padding:11px 18px;
  font-family:inherit;font-size:.92rem;font-weight:600;cursor:pointer}
.bas:hover{background:var(--verde-koyu)}
.bas:disabled{opacity:.6;cursor:wait}
.vaz{background:transparent;color:var(--soluk);border:1px solid var(--cizgi-koyu);
  border-radius:8px;padding:11px 18px;font-family:inherit;font-size:.92rem;cursor:pointer}
''',
     r'''  color:var(--murekkep)}
.panel-btn:hover .pb-ad{color:var(--verde)}
.panel-btn .pb-alt{display:block;font-size:.8rem;color:var(--soluk);
  margin-top:3px;line-height:1.45}
'''),
    ('templates/firma_sec.html', 'YP3 · templates/firma_sec.html blok 3',
     r'''.gizli{display:none}
/* Sil — kartın içinde ama kartın tıklamasını YUTAR (firmaSil'de
   stopPropagation); yoksa silinecek firmaya geçilirdi. */
.sil{font-size:.78rem;font-weight:600;color:var(--soluk);border:1px solid var(--cizgi);
  border-radius:6px;padding:3px 9px;cursor:pointer;transition:all .14s}
.sil:hover{color:var(--kirmizi);border-color:var(--kirmizi);background:var(--kirmizi-bg)}
/* MF7: bu kurallar ÖNCE `.kutu` adıyla yazılmıştı — ama `.kutu`
   sayfanın ANA KAPSAYICISI (yukarıda .kutu{max-width:560px},
   <main class="kutu">). Sonra geldiği için kazandı ve <main> yatay
   satıra döndü: başlık, açıklama ve kartlar yan yana sıkıştı.
   Yeni sınıfa yeni ad. */
.onay-kutu{display:flex;gap:9px;align-items:flex-start;padding:8px 0;cursor:pointer;
  font-size:.84rem;font-weight:400;color:var(--murekkep);text-transform:none;
  letter-spacing:0}
.onay-kutu input{margin-top:2px;width:15px;height:15px;cursor:pointer;flex:0 0 auto}
.onay-kutu span{line-height:1.45}
.ipucu{color:var(--soluk);font-size:.79rem;line-height:1.45;margin-top:2px}

/* ── ONAY PENCERESİ ──
   Tarayıcının confirm/alert'i KULLANILMIYOR: js_denetim J4 ekseni
   bunları "sessiz hayır" sayıyor — tarayıcı engelleyebiliyor ve
   dökümü düzgün gösteremiyor. Bu sayfa bağımsız olduğu için
   base.html'deki onayla() de yok; penceresi kendi içinde. */
.ortu{position:fixed;inset:0;background:rgba(25,28,26,.45);display:flex;
  align-items:center;justify-content:center;padding:20px;z-index:80}
.ortu.gizli{display:none}
.pencere{background:var(--yuzey);border-radius:14px;max-width:460px;width:100%;
  box-shadow:0 24px 60px rgba(25,28,26,.3);overflow:hidden}
.pencere .bas{padding:18px 20px 12px}
.pencere .bas h2{font-family:var(--baslik);font-size:1.1rem;margin-bottom:4px}
.pencere .bas .hedef{color:var(--kirmizi);font-weight:700}
.pencere .gov{padding:0 20px 4px;font-size:.88rem;line-height:1.55;color:var(--murekkep)}
.pencere .gov p{margin-bottom:10px}
.pencere .gov .iyi{color:var(--soluk);font-size:.83rem}
.dokum{max-height:190px;overflow:auto;border:1px solid var(--cizgi);
  border-radius:8px;margin-bottom:10px}
.dokum table{width:100%;border-collapse:collapse;font-size:.83rem}
.dokum td{padding:5px 11px;border-bottom:1px solid var(--cizgi)}
.dokum tr:last-child td{border-bottom:0}
.dokum td.s{text-align:right;font-family:var(--mono);color:var(--soluk)}
.pencere .ayak{display:flex;gap:8px;justify-content:flex-end;
  padding:14px 20px 18px}
.teh{background:var(--kirmizi);color:#fff;border:0;border-radius:8px;
  padding:10px 17px;font-family:inherit;font-size:.9rem;font-weight:600;cursor:pointer}
.teh:hover{filter:brightness(.92)}
.teh:disabled{opacity:.6;cursor:wait}
@media (max-width:480px){.ikili{grid-template-columns:1fr}}
''',
     r'''.gizli{display:none}
'''),
    ('templates/firma_sec.html', 'YP3 · templates/firma_sec.html blok 4',
     r'''      </span>
      {# KF1: "varsayılan" rozeti ve onun Sil düğmesini gizlemesi
         KALKTI — bayrak kaldırıldı. Sil silinemeyecek bir firmaya
         basılırsa sunucu sebebini söylüyor ("içinde bulunduğun
         firma", "son firma", "şu kullanıcıların tek firması").

         KF2: Sil YALNIZCA ADMIN'de. Ekran artık herkese açık; firma
         silmeyi herkese göstermek, basınca 403 yiyecek bir düğme
         koymak olurdu. #}
      {% if admin %}
      <span class="sil" role="button" tabindex="0" title="Firmayı sil"
            onclick="firmaSil({{ f.id }}, '{{ f.ad|replace("'", "\\'") }}', event)">Sil</span>
      {% endif %}
''',
     r'''      </span>
      {# ── SİL BURADAN KALKTI (YP3) ──
         Bu ekranın tek işi "nerede çalışacağım" sorusunu
         sormak. Sil, kartın İÇİNDE, girmek için basılacak
         düğmenin üstünde duruyordu. Firma açmak/silmek artık
         Yönetim panelinde — ikisi de firmaya AİT olmayan,
         firma üstü işler. #}
'''),
    ('templates/firma_sec.html', 'YP3 · templates/firma_sec.html blok 5',
     r'''
    {# KF2: yeni firma açmak admin işi. #}
''',
     r'''
    {# ── YÖNETİM PANELİ (YP1 · YP3) ──
       Panelin varlık sebebi "herhangi bir firmaya girmeden
       yönetmek"; o yüzden bağlantısı BURADA, firmaya girmeden
       önce duruyor.

       YP3 · "+ Yeni firma ekle" BURADAN KALKTI, formuyla
       birlikte. Firma açmak firmaya AİT olmayan bir iş; aynı
       formun ikinci bir kopyasını bu ekranda tutmak, panelle
       bu ekranın ayrı ayrı bakım isteyen iki yüzü olması
       demekti. Artık tek yer: panelin Firmalar sekmesi. #}
'''),
    ('templates/firma_sec.html', 'YP3 · templates/firma_sec.html blok 6',
     r'''    <div class="ayrac">ya da</div>
    <button class="ekle-btn" id="ekleBtn" onclick="formAc()">+ Yeni firma ekle</button>
    {# ── YP1 · YÖNETİM PANELİ ──
       Panelin varlık sebebi "herhangi bir firmaya girmeden
       yönetmek"; o yüzden bağlantısı BURADA, firmaya girmeden
       önce duruyor. Kullanıcı açmak ya da yetki vermek için
       rastgele bir firmaya girip Ayarlar'a gitmek gerekmiyor. #}
    <p style="margin-top:14px;text-align:center;font-size:.86rem">
      <a href="/yonetim" style="color:var(--soluk)">Yönetim paneli —
        firmalar, kullanıcılar, yetkiler, yedekler</a>
    </p>
''',
     r'''    <div class="ayrac">ya da</div>
    <a class="panel-btn" href="/yonetim">
      <span class="pb-ad">Yönetim paneli</span>
      <span class="pb-alt">Firma ekle ve sil · kullanıcılar ve
        yetkiler · yedekler</span>
    </a>
'''),
    ('templates/firma_sec.html', 'YP3 · templates/firma_sec.html blok 7',
     r'''    {% endif %}

    <div class="form gizli" id="form">
      <h2>Yeni firma</h2>
      <p><b>Belge kodu</b> zorunlu ve kısa olmalı (örn. K). Bu kod belge
         kimliklerinin köküne girer — <span style="font-family:var(--mono)">SIP-K-STN26-01</span>
         — ve her firmanın numarasının kendi başına ilerlemesini sağlar.
         Kodsuz iki firmanın numaraları çakışır.</p>
      <div class="ikili">
        <div class="alan"><label for="nAd">Firma adı *</label>
          <input id="nAd" placeholder="İkinci Mermer A.Ş."></div>
        <div class="alan"><label for="nKod">Belge kodu *</label>
          <input id="nKod" maxlength="4" placeholder="K" style="text-transform:uppercase"></div>
      </div>
      <div class="alan"><label for="nUnvan">Ticari ünvan</label>
        <input id="nUnvan" placeholder="Belgelerde görünen tam ünvan"></div>
      <div class="alan"><label for="nVno">Vergi no</label>
        <input id="nVno" placeholder="1234567890"></div>
      <!-- MF6: yeni firma bomboş açılıyordu; 170 cari ve bütün tanım
           listeleri yeniden girilecekti. -->
      <div class="alan">
        <label>Mevcut firmadan ortak kullanılsın</label>
        <label class="onay-kutu"><input type="checkbox" id="nOrtakCari" checked>
          <span>Cari listesi — mevcut müşteri ve tedarikçiler bu firmaya da
          bağlanır. Sonrasında her firma kendi müşterisini ekler.</span></label>
        <label class="onay-kutu"><input type="checkbox" id="nOrtakListe" checked>
          <span>Tanım listeleri — cins, yüzey, ülke, ödeme şekli her
          firmada aynı kalır; bir kez girilen her yerde görünür.</span></label>
        <div class="ipucu">İşaretlemezsen bu firma kendi listesini
          kullanır; kuruluşta mevcut listelerin bir kopyası yazılır.</div>
      </div>
      <div class="dugmeler">
        <button class="bas" id="kaydetBtn" onclick="kaydet()">Ekle ve bu firmaya geç</button>
        <button class="vaz" onclick="formKapat()">Vazgeç</button>
      </div>
    </div>
''',
     r'''    {% endif %}
'''),
    ('templates/firma_sec.html', 'YP3 · templates/firma_sec.html blok 8',
     r'''  </main>

  <div class="ortu gizli" id="silOrtu" onclick="if(event.target===this)silKapat()">
    <div class="pencere" role="dialog" aria-label="Firma sil">
      <div class="bas">
        <h2>Firmayı sil</h2>
        <div class="hedef" id="silAd"></div>
      </div>
      <div class="gov" id="silGovde"></div>
      <div class="ayak">
        <button class="vaz" onclick="silKapat()">Vazgeç</button>
        <button class="teh" id="silBtn" onclick="silOnayla()">Yedekle ve sil</button>
      </div>
    </div>
  </div>
''',
     r'''  </main>
'''),
    ('templates/firma_sec.html', 'YP3 · templates/firma_sec.html blok 9',
     r'''}
function formAc() {
  document.getElementById('form').classList.remove('gizli');
  document.getElementById('ekleBtn').classList.add('gizli');
  document.getElementById('nAd').focus();
}
function formKapat() {
  document.getElementById('form').classList.add('gizli');
  document.getElementById('ekleBtn').classList.remove('gizli');
  document.getElementById('hata').classList.add('gizli');
}
''',
     r'''}
'''),
    ('templates/firma_sec.html', 'YP3 · templates/firma_sec.html blok 10',
     r'''
let SIL_HEDEF = null;

function silKapat() {
  document.getElementById('silOrtu').classList.add('gizli');
  SIL_HEDEF = null;
}

async function firmaSil(id, ad, e) {
  /* Düğme kartın İÇİNDE: tıklama kartın onclick'ine de giderdi ve
     silinecek firmaya GEÇİLİRDİ. */
  if (e) { e.stopPropagation(); e.preventDefault(); }
  document.getElementById('hata').classList.add('gizli');
  let o;
  try {
    const y = await fetch('/api/firma/' + id + '/ozet');
    o = await y.json();
  } catch (err) { hataGoster('Firma bilgisi okunamadı'); return; }
  if (!o || !o.ok) { hataGoster((o && o.mesaj) || 'Firma bilgisi okunamadı'); return; }
  if (o.engel) { hataGoster(o.engel); return; }

  SIL_HEDEF = id;
  document.getElementById('silAd').textContent = ad;
  const g = document.getElementById('silGovde');
  if (o.kayit_sayisi > 0) {
    const d = Object.entries(o.dagilim || {})
      .sort((a, b) => b[1] - a[1])
      .map(([t, n]) => `<tr><td>${t}</td><td class="s">${n.toLocaleString('tr-TR')}</td></tr>`)
      .join('');
    g.innerHTML = `
      <p>Bu firmada <b>${o.kayit_sayisi.toLocaleString('tr-TR')}</b> kayıt var:</p>
      <div class="dokum"><table>${d}</table></div>
      <p class="iyi">Silmeden önce <b>tam veritabanı yedeği</b> alınacak.
         Yanlışlıkla silersen Ayarlar → Yedekleme'den o yedeğe
         dönebilirsin. Yedek alınamazsa silme yapılmaz.</p>`;
  } else {
    g.innerHTML = '<p>Bu firmada hiç kayıt yok. Doğrudan silinecek.</p>';
  }
  document.getElementById('silOrtu').classList.remove('gizli');
}

async function silOnayla() {
  if (!SIL_HEDEF) return;
  const b = document.getElementById('silBtn');
  b.disabled = true; b.textContent = 'Siliniyor…';
  try {
    const y = await fetch('/api/firma/' + SIL_HEDEF, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': CSRF }
    });
    const d = await y.json();
    if (d && d.ok) { location.reload(); return; }
    silKapat(); hataGoster((d && d.mesaj) || 'Silinemedi');
  } catch (err) { silKapat(); hataGoster('Silinemedi'); }
  b.disabled = false; b.textContent = 'Yedekle ve sil';
}

''',
     r'''
'''),
    ('templates/firma_sec.html', 'YP3 · templates/firma_sec.html blok 11',
     r'''}

async function kaydet() {
  const ad = (document.getElementById('nAd').value || '').trim();
  const kod = (document.getElementById('nKod').value || '').trim().toUpperCase();
  if (!ad) { hataGoster('Firma adı gir.'); return; }
  if (!kod) { hataGoster('Belge kodu gir — yoksa belge numaraları çakışır.'); return; }
  const b = document.getElementById('kaydetBtn');
  b.disabled = true; b.textContent = 'Ekleniyor…';
  try {
    const d = await gonder('/api/firma', {
      ad: ad, belge_kodu: kod,
      unvan: (document.getElementById('nUnvan').value || '').trim(),
      vergi_no: (document.getElementById('nVno').value || '').trim(),
      ortak_cari: document.getElementById('nOrtakCari').checked,
      ortak_liste: document.getElementById('nOrtakListe').checked
    });
    if (d && d.ok && d.id) {
      /* Eklenen firmaya DOĞRUDAN geçilir: yeni firmanın unvanını,
         adresini ve logosunu girecek olan kişi zaten o firmada
         olmalı. Eski düzende A'nın ayarlarında kalıp B'nin bilgisi
         sanarak A'yı düzenlemek çok kolaydı. */
      await sec(d.id, null);
      return;
    }
    hataGoster((d && d.mesaj) || 'Firma eklenemedi');
  } catch (e) { hataGoster('Firma eklenemedi'); }
  b.disabled = false; b.textContent = 'Ekle ve bu firmaya geç';
}
''',
     r'''}
'''),
    ('tests/test_kritik.py', 'YP3 · tests/test_kritik.py blok 1',
     r'''    assert c.get('/api/ayarlar/kullanici', headers=H).status_code == 200
''',
     r'''    assert c.get('/api/ayarlar/kullanici', headers=H).status_code == 200


# ══════════════════════════════════════════════════════════════════════
#  YP3 · PANEL YALIN KABUK + FİRMA İŞLERİ TEK YERDE
# ══════════════════════════════════════════════════════════════════════

def test_yp3_panelde_ray_ve_arama_basilmaz():
    """YP3: panelde BAŞKA MENÜ olmamalı.

    Sol ray oradayken 'Depo', 'Finans', 'Satış' görünüyordu; hiçbiri
    firma seçilmeden açılamaz, basınca seçim ekranına geri atıyordu.
    Görünen ama çalışmayan menü, çalışmayan bir düğmeden daha kötü:
    sistem bozukmuş gibi duruyor."""
    a = istemci('admin', 'ADMIN')
    yon = a.get('/yonetim').get_data(as_text=True)
    aya = a.get('/ayarlar').get_data(as_text=True)

    assert 'class="ray"' not in yon
    assert 'onclick="paletAc()"' not in yon
    assert 'class="kabuk yalin"' in yon
    # Ayarlar bir firmanın içinde: kabuk AYNEN kalmalı
    assert 'class="ray"' in aya
    assert 'onclick="paletAc()"' in aya
    assert 'class="kabuk yalin"' not in aya
    # Ctrl+K kısayolu hâlâ bağlı; paleti bayrak kapatıyor
    assert 'window.YALIN_PANEL = true' in yon
    assert 'if (window.YALIN_PANEL) return;' in yon


def test_yp3_panelden_cikis_firma_secimine_doner():
    """YP3: 'çıkış yapınca bir önceki sayfaya dönsün'.

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


def test_yp3_her_sayfada_TEK_bolum_acik():
    """YP3: açık sekme ile açık bölüm AYNI olmalı.

    İki ayrı arıza bu testle kapanıyor:
      · Yönetim'de `b-firmalar` da `aktif` basılıyordu — Kullanıcılar
        sekmesindeyken Firmalar paneli de görünüyor, üstelik
        yükleyicisi koşmadığı için sonsuza kadar 'Yükleniyor…'
        yazıyordu.
      · Ayarlar'ın ilk sekmesi YP2'de `firma`ya geçti ama `aktif`
        bölüm `b-firma` değildi: sayfa altı BOMBOŞ açılıyordu."""
    import re as _re
    a = istemci('admin', 'ADMIN')
    for yol in ('/yonetim', '/ayarlar'):
        h = a.get(yol).get_data(as_text=True)
        acik = _re.findall(r'<section class="bolum aktif" id="b-([a-z]+)"', h)
        assert len(acik) == 1, (yol, acik)
        sekme = _re.findall(r'class="sekme aktif" data-b="([a-z]+)"', h)
        assert sekme == acik, (yol, sekme, acik)


def test_yp3_firma_secim_ekraninda_ekleme_yok():
    """YP3: firma açma/silme TEK yerde — panelde.

    Aynı formun iki kopyası iki ekranda yaşarsa ikisi ayrı ayrı
    bakım ister; biri düzeltilip öteki unutulur."""
    a = istemci('admin', 'ADMIN')
    h = a.get('/firma-sec').get_data(as_text=True)
    # Metne değil YAPIYA bakıyoruz: bu dosyadaki açıklama satırları
    # düğmenin adını anıyor, testin onlara takılması gerekmez.
    assert 'id="ekleBtn"' not in h      # ekleme düğmesi
    assert 'id="nAd"' not in h          # ekleme formu
    assert 'function kaydet' not in h
    assert 'silOnayla' not in h         # silme penceresi
    # Ekranda GİRİLECEK hiçbir şey kalmadı; işi yalnızca seçtirmek
    assert '<input' not in h
    assert 'href="/yonetim"' in h       # panelin kapısı


def test_yp3_firma_panelden_silinebilir():
    """YP3: silme panele taşındı — firma SEÇMEDEN de işlemeli.

    Uç seçim kapısında muaf; muafiyet kalkarsa düğme görünür ama
    basınca 409 döner."""
    from models import Firma
    a = istemci('admin', 'ADMIN')
    r = a.post('/api/firma', headers=H, json={
        'ad': 'YP3 SILINECEK', 'belge_kodu': 'Y3',
        'ortak_cari': False, 'ortak_liste': False})
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    yeni = r.get_json()['id']

    firmasiz = fa.app.test_client()
    with firmasiz.session_transaction() as s:
        s['kullanici'] = 'admin'; s['rol'] = 'ADMIN'; s['_csrf'] = 't'
    o = firmasiz.get(f'/api/firma/{yeni}/ozet', headers=H)
    assert o.status_code == 200, o.get_data(as_text=True)
    assert not o.get_json().get('engel'), o.get_json().get('engel')

    d = firmasiz.delete(f'/api/firma/{yeni}', headers=H)
    assert d.status_code == 200, d.get_data(as_text=True)
    assert d.get_json().get('ok'), d.get_json()
    with fa.app.app_context():
        assert Firma.query.get(yeni) is None
'''),
]



def main():
    print('=' * 70)
    print('  YAMA YP3 — PANEL YALIN KABUK')
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
        print('  ⊙ Yama YP3 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_yp3.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_yp3'
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
    print('    · Firma secim ekrani: "Yeni firma ekle" gitti,')
    print('      yerinde "Yonetim paneli" dugmesi var.')
    print('    · Panelde sol ray ve arama YOK; sag ustte')
    print('      "Firma secimine don".')
    print('    · Panel -> Firmalar: her satirda Sil, altinda')
    print('      "+ Yeni Firma".')
    print('    · Ayarlar: ilk sekme "Firma Bilgileri" ve altindaki')
    print('      form GORUNUYOR (bos acilmiyor).')
    print()
    print('    3) venv/bin/python -m pytest tests/test_kritik.py -q')
    print('       venv/bin/python firma_denetim.py')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

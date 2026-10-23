#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA US1 — YENİ STOK FORMU, ÇİZDİĞİN DÜZENDE
=============================================

ÖNKOŞUL: **yama_kf2.py uygulanmış olmalı.** Betik denetliyor;
uygulanmamışsa hiçbir dosyaya dokunmadan çıkar.

Gönderdiğin üç çizimin aynısı. Satırları tip tip YAZMADIM: alanlar
tek bir 4 sütunlu ızgarada sırayla duruyor, o tipte anlamı olmayan
alan gizlenince ızgara onu atlıyor ve kalanlar yukarı kayıyor. Tek
sıralama üç düzeni birden veriyor — tip başına ayrı satır yazsaydım
üç kopya olurdu ve biri düzeltilip ötekiler unutulurdu.

── TARAYICIDA ÖLÇÜLDÜ ──

  BLOK
    ürün tipi · üretici · menşe · giriş tarihi
    cins · blok no · kaynak · alış tipi
    alış fiyatı · döviz · fiyat birimi · tonaj
    boy · yükseklik · en · hacim
    fatura durumu · fatura no · fatura tarihi · kdv oranı

  PLAKA
    ... cins · blok no · özellik · kaynak
    alış tipi · alış fiyatı · döviz · fiyat birimi
    boy · yükseklik · kalınlık
    stok adedi · başlangıç slab no · toplam m² · + grup ekle
    fatura durumu · fatura no · fatura tarihi · kdv oranı

  EBATLI
    ... cins · kasa no · özellik · kaynak
    ... boy · yükseklik · kalınlık
    kasa adedi · kasa içi adet · toplam m²

  Üçü de çizimine birebir uydu. Kaydırma yok, kırpılan seçici yok.

── ETİKETLER ──
  Üretici / Ocak            → Üretici
  Yüzey / Özellik           → Özellik
  Blok No (kesildiği blok)  → Blok No
  Kasa No (ilk kasa, ops.)  → Kasa No
  Alış / Fatura Tarihi      → Fatura Tarihi

  Parantez içindeki açıklamalar SİLİNMEDİ, alanın ipucuna (üstüne
  gelince çıkan baloncuk) taşındı. Menşe'nin altındaki "Listede
  yoksa Ayarlar → Listeler → Ülkeler'den ekle" satırı da öyle: 4
  sütuna geçince o satırı tek başına iki katına çıkarıyordu.

  "Özellik" adını AYNI ALANIN geçtiği her yerde değiştirdim —
  stok düzenleme, toplu aktarma, kesim, proforma, sipariş. Tek
  alanın beş ekranda iki ayrı adı olması, düzeltilince birinin
  unutulduğu durumun ta kendisi. Excel eşleştirmesi etiketten değil
  anahtar kelimelerden yapılıyor, ona dokunulmadı.

── İKİ KARAR, SANA SÖYLÜYORUM ──

  1. ÜRETİM stoğunun faturası yok. Etiketi düz "Fatura Tarihi"ne
     sabitlemek orada yanlış olurdu; kaynak "Üretim" seçilince
     "Üretim Tarihi" yazıyor (toplu aktarma formu zaten böyle
     yapıyordu).

  2. Çizimlerinde "Fiyata KDV dahil" kutusu yoktu — KDV oranı
     fatura satırına geçince o kutu açıkta kaldı. Silmedim:
     girilen fiyatın KDV'li olup olmadığını söyleyen tek yer o.
     "Alış fiyatına nakliye dahil"in yanına, tek satıra aldım.
     İkisi hâlâ KDV oranıyla birlikte görünüp birlikte kayboluyor.

  3. PLAKA ve EBATLI çizimlerinde fatura satırı İKİ KEZ vardı
     (biri üç sütunlu, biri KDV oranlı dört sütunlu). Dört
     sütunlusunu aldım — bloktaki ile aynı olsun diye.

── İKİ KÜÇÜK TEMİZLİK ──
  · "+ Grup ekle" düğmesi aşağıdaki kutunun başlığındaydı; kutu
    boşken orada tek başına duruyordu. Artık adedin yanında,
    grubun açılacağı yerde — kutu da yalnız grup varken açılıyor.
  · Fatura durumu seçeneklerindeki parantezler ("Faturalı (mal +
    fatura geldi)") seçiciye sığmıyordu. Altındaki renkli not zaten
    seçilen durumu daha ayrıntılı anlatıyor; aynı şeyi iki kez,
    biri kırpılarak söylemenin anlamı yoktu.
  · Modal 720 → 880 piksel. 4 sütunda 720 dar kalıyordu.

── DOĞRULANDI ──
  Üç tip de formdan doldurulup KAYDEDİLDİ, veritabanında eksiksiz
  çıktı: blokta menşe/tonaj/hacim/kdv/üretici yerinde; plakada 3
  kayıt, numaralar girdiğim 5'ten başlıyor (PLK-A-77-05/06/07);
  ebatlıda 2 kasa, her birinde 10 adet.

  KDV oranı ve "fiyata KDV dahil" birlikte açılıp birlikte
  kapanıyor (alış tipi ve kaynak değiştirilerek denendi).
  Ölçü grubu kutusu: grup yokken kapalı, eklenince açık, silinince
  yine kapalı.

  229 test geçti (226 + 3). firma · js · form · akış denetimleri
  temiz. Tarayıcıda JS hatası yok.

DOSYALAR
--------
  templates/stok.html      form düzeni · etiketler · KDV ikilisi ·
                           ölçü grubu · modal genişliği
  templates/kesim.html     "Özellik" adı
  templates/proforma.html  "Özellik" adı
  templates/siparis.html   "Özellik" adı
  tests/test_kritik.py     3 yeni test

Şema yok, göç yok, sunucu tarafı değişmedi.

KULLANIM
--------
  python3 yama_us1.py            # RAPOR
  python3 yama_us1.py --uygula
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
    'templates/stok.html': 'US1 · ALANLAR TİPE GÖRE AKIYOR',
    'templates/kesim.html': '<label>Özellik (ortak)</label>',
    'templates/proforma.html': '<label>Özellik</label>',
    'templates/siparis.html': '<label>Özellik</label>',
    'tests/test_kritik.py': 'def test_us1_alanlar_tipe_gore_dogru_sirada',
}
ONKOSUL = {
    'templates/stok.html': 'grid-template-columns:minmax(0,19em)',
    'templates/kesim.html': 'Yüzey / Özellik (ortak)',
    'templates/proforma.html': 'Yüzey / Özellik',
    'templates/siparis.html': 'Yüzey / Özellik',
    'tests/test_kritik.py': 'def test_kf2_doviz_tutarla_ayni_alanda',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('templates/stok.html', 'US1 · templates/stok.html blok 1',
     r'''  .form-alan label{display:block;font-size:.72rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--soluk);margin-bottom:5px}
''',
     r'''  /* US1 — SATIR BAŞI. Plaka ve ebatlıda miktar alanları ölçülerin
     ALTINDAN başlasın diye ilk miktar alanı birinci sütuna
     sabitleniyor; ızgarada bu, satır başı demek. Blokta sınıf yok,
     hacim ölçülerin yanında kalıyor. */
  .f4.ayri > #adetAlan, .f4.ayri > #kasaAdediAlan{grid-column-start:1}
  /* US1 — yan yana iki işaret kutusu. */
  .isaret-cift{display:flex;flex-wrap:wrap;gap:8px 22px;margin-bottom:12px}
  .isaret-cift > label{display:flex;align-items:center;gap:8px;cursor:pointer;
    font-weight:500;text-transform:none;letter-spacing:0;font-size:.88rem;margin:0}
  .isaret-cift input{width:16px;height:16px;flex:none;margin:0;
    cursor:pointer;accent-color:var(--verde)}
  .is-not{color:var(--soluk);font-size:.78rem;font-weight:400}
  .form-alan label{display:block;font-size:.72rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--soluk);margin-bottom:5px}
'''),
    ('templates/stok.html', 'US1 · templates/stok.html blok 2',
     r'''        <div class="form-alan" id="duzOzellikAlan"><label>Yüzey / Özellik</label><input id="duzOzellik"></div>
''',
     r'''        <div class="form-alan" id="duzOzellikAlan"><label>Özellik</label><input id="duzOzellik"></div>
'''),
    ('templates/stok.html', 'US1 · templates/stok.html blok 3',
     r'''          <div class="form-alan" id="tOzellikAlan"><label>Yüzey / Özellik (ortak)
''',
     r'''          <div class="form-alan" id="tOzellikAlan"><label>Özellik (ortak)
'''),
    ('templates/stok.html', 'US1 · templates/stok.html blok 4',
     r'''  <div class="modal" role="dialog" aria-label="Yeni stok">
    <div class="modal-bas">
      <h3>Yeni Stok Girişi</h3>
      <p>Depoya blok, plaka veya ebatlı ürün ekle. Plakada adet kadar ayrı kayıt oluşur.</p>
    </div>
    <div class="modal-gov">
      <div class="form-satir f3">
''',
     r'''  <!-- US1: 4 sütuna geçince 720 pikselde sütun başına 160 piksel
       kalıyordu; "Faturalı (mal + fatura geldi)" gibi seçenekler
       kırpılıyordu. Ölçüldü, 880'de kırpılma kalmadı. -->
  <div class="modal" style="width:880px" role="dialog" aria-label="Yeni stok">
    <div class="modal-bas">
      <h3>Yeni Stok Girişi</h3>
      <p>Depoya blok, plaka veya ebatlı ürün ekle. Plakada adet kadar ayrı kayıt oluşur.</p>
    </div>
    <div class="modal-gov">
      <!-- ══ US1 · ALANLAR TİPE GÖRE AKIYOR ══
           Üç ürün tipinin formu artık Bahadır'ın çizdiği düzende.
           Satırları tip tip YAZMIYORUZ: alanlar tek bir 4 sütunlu
           ızgarada SIRAYLA duruyor, tipte anlamı olmayan alan
           gizlenince ızgara onu atlıyor ve kalanlar yukarı kayıyor.

           Böylece tek bir sıralama üç düzeni birden veriyor:

             BLOK    cins · blok no · kaynak · alış tipi
                     alış fiyatı · döviz · fiyat birimi · tonaj
             PLAKA   cins · blok no · özellik · kaynak
                     alış tipi · alış fiyatı · döviz · fiyat birimi
             EBATLI  aynısı (kasa no ile)

           Tip başına ayrı satır yazsaydık üç kopya olurdu ve biri
           düzeltilip ötekiler unutulurdu. -->
      <div class="form-satir f4">
'''),
    ('templates/stok.html', 'US1 · templates/stok.html blok 5',
     r'''        <div class="form-alan"><label>Üretici / Ocak</label><select id="sUretici"></select></div>
        <div class="form-alan"><label>Cins <span style="color:var(--kirmizi)">*</span></label><input id="sCins" placeholder="Emperador Dark"></div>
      </div>
      <div class="form-satir f4">
        <div class="form-alan"><label id="sNoLabel">Blok No</label><input id="sBlokNo" placeholder="B-100"></div>
        <!-- UR2: BLOK'ta yüzey/özellik gizlenir — ham blokta yüzey
             işlemi yok, alanı göstermek doldurulacak bir şey varmış
             gibi gösteriyordu. -->
        <div class="form-alan" id="ozellikAlan"><label>Yüzey / Özellik</label><input id="sOzellik" placeholder="Ham / Cilalı"></div>
        <!-- UR2: menşe artık LİSTEDEN. Elle yazılınca aynı ülke üç
             ayrı yazımla kaydediliyordu (TURKIYE / TÜRKİYE / Turkiye)
             ve bu değer ticari faturaya, packing list'e ve etikete
             BASILIYOR. Liste Ayarlar → Listeler → Ülkeler'den gelir. -->
        <div class="form-alan"><label>Menşe</label>
          <select id="sMense" title="Malın menşei — bundle/crate etiketinde ve ticari faturada basılır"></select>
          <div style="font-size:.72rem;color:var(--soluk);margin-top:3px">
            Listede yoksa Ayarlar → Listeler → Ülkeler'den ekle</div>
        </div>
        <div class="form-alan"><label>Giriş Tarihi</label><input id="sTarih" type="date"></div>
      </div>

      <!-- Ölçüler -->
      <div class="form-satir f4" id="olcuSatir">
        <div class="form-alan"><label>Boy (cm)</label><input id="sBoy" type="number" oninput="hesapla()"></div>
        <div class="form-alan"><label>Yükseklik (cm)</label><input id="sYuk" type="number" oninput="hesapla()"></div>
        <div class="form-alan" id="enAlan"><label>En (cm)</label><input id="sEn" type="number" oninput="hesapla()"></div>
        <div class="form-alan" id="kalAlan" style="display:none"><label>Kalınlık (cm)</label><input id="sKal" type="number" step="0.1" value="2" oninput="hesapla()"></div>
      </div>

      <!-- Miktar -->
      <div class="form-satir f3">
        <div class="form-alan" id="tonajAlan"><label>Tonaj</label><input id="sTonaj" type="number" step="0.01" oninput="hesapla()"></div>
        <div class="form-alan" id="adetAlan" style="display:none"><label>Stok Adedi</label><input id="sAdet" type="number" value="1" oninput="hesapla()"></div>
        <div class="form-alan" id="kasaAdediAlan" style="display:none"><label>Kasa Adedi</label><input id="sKasaAdedi" type="number" min="1" value="1" oninput="hesapla()"></div>
        <div class="form-alan" id="kasaIciAlan" style="display:none"><label>Kasa İçi Adet</label><input id="sKasaIci" type="number" min="1" value="1" oninput="hesapla()"></div>
        <div class="form-alan" id="basNoAlan" style="display:none"><label id="basNoLabel">Başlangıç Slab No</label><input id="sBasNo" type="number" min="0" value="1"
               title="İlk plakanın numarası. 0 da geçerlidir."></div>
        <div class="form-alan"><label id="olcuLabel">Hacim (m³)</label><input id="sOlcu" readonly></div>
      </div>

      <!-- ── ÖLÇÜ GRUPLARI (OG1) ──
           Bir blokta farklı ölçüde plaka grupları olabiliyor.
           K6318 örneği: 187×298'den 9 adet, 185×273'ten 1 adet,
           186×297'den 11+12+12+12 adet, 135×296'dan 6 adet — toplam
           63 plaka, numaralar kesintisiz 1-63.

           Ortak bilgiler (cins, blok no, yüzey işlemi, fiyat,
           tedarikçi, fatura) yukarıda BİR KEZ girilir; yalnızca
           ölçüler ve adet grup grup değişir. -->
      <div id="olcuGrupAlan" style="display:none;margin-top:4px">
        <div style="display:flex;align-items:center;gap:9px;margin-bottom:6px">
          <label style="margin:0">Ek Ölçü Grupları</label>
          <button type="button" class="mini-btn" onclick="olcuGrupEkle()">+ Grup ekle</button>
          <span id="olcuGrupOzet" style="font-size:.78rem;color:var(--soluk)"></span>
        </div>
        <div id="olcuGruplar"></div>
        <div style="font-size:.76rem;color:var(--soluk);margin-top:4px;line-height:1.5">
          Üstteki ölçü <b>1. grup</b>tur. Ek grup eklerseniz plaka numaraları
          kesintisiz devam eder.
        </div>
      </div>

      <!-- Fiyat -->
      <div class="form-satir f4">
        <div class="form-alan"><label>Alış Fiyatı</label><input id="sFiyat" type="number" step="0.01" oninput="hesapla()"></div>
        <div class="form-alan"><label>Fiyat Birimi</label>
          <select id="sFiyatBirim" onchange="hesapla()">
            <option value="ton">$/ton</option>
            <option value="m3">$/m³</option>
            <option value="m2">$/m²</option>
            <option value="sqft">$/sqft</option>
          </select>
        </div>
        <div class="form-alan"><label>Döviz</label>
          <select id="sDoviz" onchange="hesapla()"><option>USD</option><option>EUR</option><option>TRY</option></select>
        </div>
''',
     r'''        <div class="form-alan"><label>Üretici</label><select id="sUretici"></select></div>
        <!-- UR2: menşe artık LİSTEDEN. Elle yazılınca aynı ülke üç
             ayrı yazımla kaydediliyordu (TURKIYE / TÜRKİYE / Turkiye)
             ve bu değer ticari faturaya, packing list'e ve etikete
             BASILIYOR. Liste Ayarlar → Listeler → Ülkeler'den gelir. -->
        <div class="form-alan"><label>Menşe</label>
          <!-- US1: altındaki "Listede yoksa Ayarlar → Listeler →
               Ülkeler'den ekle" satırı, 4 sütuna geçince bu satırı tek
               başına iki kat uzatıyordu. Yazı silinmedi, seçicinin
               ipucuna (üstüne gelince çıkan baloncuk) taşındı. -->
          <select id="sMense" title="Malın menşei — bundle/crate etiketinde ve ticari faturada basılır. Listede yoksa Ayarlar → Listeler → Ülkeler'den ekleyin."></select>
        </div>
        <div class="form-alan"><label>Giriş Tarihi</label><input id="sTarih" type="date"></div>
      </div>

      <div class="form-satir f4" id="kimlikSatir">
        <div class="form-alan"><label>Cins <span style="color:var(--kirmizi)">*</span></label><input id="sCins" placeholder="Emperador Dark"></div>
        <div class="form-alan"><label id="sNoLabel">Blok No</label><input id="sBlokNo" placeholder="B-100"></div>
        <!-- UR2: BLOK'ta yüzey/özellik gizlenir — ham blokta yüzey
             işlemi yok, alanı göstermek doldurulacak bir şey varmış
             gibi gösteriyordu. -->
        <div class="form-alan" id="ozellikAlan"><label>Özellik</label><input id="sOzellik" placeholder="Ham / Cilalı"></div>
'''),
    ('templates/stok.html', 'US1 · templates/stok.html blok 6',
     r'''      </div>

      <div class="form-satir f3">
        <div class="form-alan"><label>Fatura Durumu</label>
          <select id="sFaturaDurum" onchange="faturaDurumDegisti()">
            <option value="faturali">Faturalı (mal + fatura geldi)</option>
            <option value="faturasiz">Faturasız (mal geldi, fatura bekliyor)</option>
            <option value="mal_bekliyor">Mal bekleniyor (fatura kesildi, mal yok)</option>
          </select>
        </div>
        <div class="form-alan"><label>Fatura No</label><input id="sFaturaNo" placeholder="AKD-2026-118"></div>
        <div class="form-alan"><label>Alış / Fatura Tarihi</label><input id="sAlisTarih" type="date"></div>
      </div>
      <div id="fdNot" style="background:var(--notr-bg);border-radius:7px;padding:9px 12px;font-size:.8rem;color:var(--soluk);margin-bottom:12px">
        Mal ve fatura birlikte geldi — tedarikçi cariye borç işlenir.
      </div>

      <div class="form-satir f3" id="kdvSatir">
        <div class="form-alan"><label>KDV Oranı (%)</label><input id="sKdv" type="number" value="20" oninput="hesapla()"></div>
        <div class="form-alan" style="display:flex;align-items:flex-end">
          <div class="onay" style="margin:0">
            <input type="checkbox" id="sKdvDahil" onchange="hesapla()">
            <label for="sKdvDahil" style="margin:0;text-transform:none;letter-spacing:0;font-weight:500;font-size:.85rem;color:var(--murekkep)">Fiyata KDV dahil</label>
          </div>
        </div>
      </div>

            <div class="form-alan" style="margin-bottom:10px">
        <!-- F5: Yalnızca BİLGİ amaçlı işaret. Maliyet hesabına karışmaz;
             işaretlenince açıklamaya not düşer ve bayrak kayda geçer.
             Nakliyeyi maliyete giydirmek için Maliyet modülü kullanılır. -->
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-weight:500;text-transform:none;letter-spacing:0">
          <input type="checkbox" id="sNakliyeDahil" style="width:16px;height:16px"
                 onchange="nakliyeNotu()">
          Alış fiyatına nakliye dahil
          <span style="color:var(--soluk);font-size:.78rem;font-weight:400">· bilgi amaçlı, maliyeti etkilemez</span>
''',
     r'''        <div class="form-alan"><label>Alış Fiyatı</label><input id="sFiyat" type="number" step="0.01" oninput="hesapla()"></div>
        <div class="form-alan"><label>Döviz</label>
          <select id="sDoviz" onchange="hesapla()"><option>USD</option><option>EUR</option><option>TRY</option></select>
        </div>
        <div class="form-alan"><label>Fiyat Birimi</label>
          <select id="sFiyatBirim" onchange="hesapla()">
            <option value="ton">$/ton</option>
            <option value="m3">$/m³</option>
            <option value="m2">$/m²</option>
            <option value="sqft">$/sqft</option>
          </select>
        </div>
        <div class="form-alan" id="tonajAlan"><label>Tonaj</label><input id="sTonaj" type="number" step="0.01" oninput="hesapla()"></div>
      </div>

      <!-- ÖLÇÜ + MİKTAR TEK IZGARADA.
           BLOK'ta hacim ölçülerin yanında (ondan hesaplanıyor);
           plaka ve ebatlıda toplam m² adedin yanında (ondan
           hesaplanıyor). Bu yüzden ikisi aynı ızgarada ve araya
           `.ayri` sınıfıyla satır başı konuyor:

             BLOK    boy · yükseklik · en · hacim
             PLAKA   boy · yükseklik · kalınlık
                     stok adedi · başlangıç slab no · toplam m² · + grup
             EBATLI  boy · yükseklik · kalınlık
                     kasa adedi · kasa içi adet · toplam m²

           `grid-column-start:1` ızgarada satır başı demektir; araya
           görünmez bir ayraç ögesi koymaktan daha az kırılgan. -->
      <div class="form-satir f4" id="olcuSatir">
        <div class="form-alan"><label>Boy (cm)</label><input id="sBoy" type="number" oninput="hesapla()"></div>
        <div class="form-alan"><label>Yükseklik (cm)</label><input id="sYuk" type="number" oninput="hesapla()"></div>
        <div class="form-alan" id="enAlan"><label>En (cm)</label><input id="sEn" type="number" oninput="hesapla()"></div>
        <div class="form-alan" id="kalAlan" style="display:none"><label>Kalınlık (cm)</label><input id="sKal" type="number" step="0.1" value="2" oninput="hesapla()"></div>
        <div class="form-alan" id="adetAlan" style="display:none"><label>Stok Adedi</label><input id="sAdet" type="number" value="1" oninput="hesapla()"></div>
        <div class="form-alan" id="kasaAdediAlan" style="display:none"><label>Kasa Adedi</label><input id="sKasaAdedi" type="number" min="1" value="1" oninput="hesapla()"></div>
        <div class="form-alan" id="kasaIciAlan" style="display:none"><label>Kasa İçi Adet</label><input id="sKasaIci" type="number" min="1" value="1" oninput="hesapla()"></div>
        <div class="form-alan" id="basNoAlan" style="display:none"><label id="basNoLabel">Başlangıç Slab No</label><input id="sBasNo" type="number" min="0" value="1"
               title="İlk plakanın numarası. 0 da geçerlidir."></div>
        <div class="form-alan"><label id="olcuLabel">Hacim (m³)</label><input id="sOlcu" readonly></div>
        <!-- US1: "+ Grup ekle" düğmesi aşağıdaki kutunun başlığındaydı;
             kutu boşken orada tek başına duruyordu. Artık adedin
             yanında, grubun açılacağı yerde. -->
        <div class="form-alan" id="grupEkleAlan" style="display:none"><label>Ölçü Grubu</label>
          <button type="button" class="mini-btn" onclick="olcuGrupEkle()"
                  style="height:38px;width:100%">+ Grup ekle</button></div>
      </div>

      <!-- ── ÖLÇÜ GRUPLARI (OG1) ──
           Bir blokta farklı ölçüde plaka grupları olabiliyor.
           K6318 örneği: 187×298'den 9 adet, 185×273'ten 1 adet,
           186×297'den 11+12+12+12 adet, 135×296'dan 6 adet — toplam
           63 plaka, numaralar kesintisiz 1-63.

           Ortak bilgiler (cins, blok no, yüzey işlemi, fiyat,
           tedarikçi, fatura) yukarıda BİR KEZ girilir; yalnızca
           ölçüler ve adet grup grup değişir.

           US1: kutu artık YALNIZCA grup varken açılıyor; boşken
           başlıktan ve nottan ibaret 40 piksel duruyordu. -->
      <div id="olcuGrupAlan" style="display:none;margin-top:4px">
        <div style="display:flex;align-items:center;gap:9px;margin-bottom:6px">
          <label style="margin:0">Ek Ölçü Grupları</label>
          <span id="olcuGrupOzet" style="font-size:.78rem;color:var(--soluk)"></span>
        </div>
        <div id="olcuGruplar"></div>
        <div style="font-size:.76rem;color:var(--soluk);margin-top:4px;line-height:1.5">
          Üstteki ölçü <b>1. grup</b>tur. Ek grup eklerseniz plaka numaraları
          kesintisiz devam eder.
        </div>
      </div>

      <div class="form-satir f4">
        <div class="form-alan"><label>Fatura Durumu</label>
          <select id="sFaturaDurum" onchange="faturaDurumDegisti()">
            <!-- US1: parantez içindeki açıklamalar kaldırıldı —
                 seçiciye sığmıyorlardı ve ALTINDAKİ renkli not zaten
                 seçilen durumu daha ayrıntılı anlatıyor. Aynı şeyi
                 iki kez, biri kırpılarak söylemenin anlamı yok. -->
            <option value="faturali">Faturalı</option>
            <option value="faturasiz">Faturasız</option>
            <option value="mal_bekliyor">Mal bekleniyor</option>
          </select>
        </div>
        <div class="form-alan"><label>Fatura No</label><input id="sFaturaNo" placeholder="AKD-2026-118"></div>
        <!-- US1: etiket "Alış / Fatura Tarihi" idi, "Fatura Tarihi"
             oldu. Ama ÜRETİM stoğunun faturası yok — o durumda
             "Üretim Tarihi" yazıyor (toplu aktarma formunda da
             böyle). Yanlış ada sabitlemektense tipe göre söylüyoruz. -->
        <div class="form-alan"><label id="sAlisTarihEtiket">Fatura Tarihi</label><input id="sAlisTarih" type="date"></div>
        <!-- US1: KDV oranı kendi satırındaydı; fatura satırının
             dördüncü sütununa geldi. Gizlenme kuralı aynı: yalnız
             yurt içi KDV'li alışta görünür. -->
        <div class="form-alan" id="kdvOranAlan"><label>KDV Oranı (%)</label><input id="sKdv" type="number" value="20" oninput="hesapla()"></div>
      </div>
      <div id="fdNot" style="background:var(--notr-bg);border-radius:7px;padding:9px 12px;font-size:.8rem;color:var(--soluk);margin-bottom:12px">
        Mal ve fatura birlikte geldi — tedarikçi cariye borç işlenir.
      </div>

      <!-- US1: İki işaret kutusu yan yana. "Fiyata KDV dahil" KDV
           oranıyla aynı satırdaydı; oran fatura satırına taşınınca
           kutu buraya geldi. Gizlenme kuralı değişmedi — oranla
           birlikte görünüp birlikte kayboluyor. -->
      <div class="isaret-cift">
        <!-- F5: Yalnızca BİLGİ amaçlı işaret. Maliyet hesabına karışmaz;
             işaretlenince açıklamaya not düşer ve bayrak kayda geçer.
             Nakliyeyi maliyete giydirmek için Maliyet modülü kullanılır. -->
        <label>
          <input type="checkbox" id="sNakliyeDahil" onchange="nakliyeNotu()">
          Alış fiyatına nakliye dahil
          <span class="is-not">· bilgi amaçlı, maliyeti etkilemez</span>
        </label>
        <label id="kdvDahilAlan">
          <input type="checkbox" id="sKdvDahil" onchange="hesapla()">
          Fiyata KDV dahil
          <span class="is-not">· girilen fiyat KDV'li ise işaretleyin</span>
'''),
    ('templates/stok.html', 'US1 · templates/stok.html blok 7',
     r'''    : '<option value="">— tedarikçi yok, Cari ekranından ekle —</option>';
''',
     r'''    /* US1: "Cari ekranından ekle" kısmı seçiciye sığmıyordu;
       ipucuna taşındı. */
    : '<option value="" title="Cari ekranından tedarikçi veya üretici'
      + ' ekleyin">— tedarikçi yok —</option>';
'''),
    ('templates/stok.html', 'US1 · templates/stok.html blok 8',
     r'''  if (!ek.length) { ozet.textContent = ''; return; }
''',
     r'''  /* US1: kutu yalnızca grup varken açılır. Boşken başlık ve nottan
     ibaret 40 piksel duruyordu. */
  const alan = document.getElementById('olcuGrupAlan');
  if (alan) alan.style.display = ek.length ? '' : 'none';
  if (!ek.length) { ozet.textContent = ''; return; }
'''),
    ('templates/stok.html', 'US1 · templates/stok.html blok 9',
     r'''  const og = document.getElementById('olcuGrupAlan');
  if (og) { og.style.display = plaka ? '' : 'none'; if (!plaka) olcuGruplariSifirla(); }
''',
     r'''  /* US1: kutu artık kendi başına karar veriyor (olcuGrupOzetle):
     grup yoksa görünmüyor. Düğme ise adedin yanında. */
  const gd = document.getElementById('grupEkleAlan');
  if (gd) gd.style.display = plaka ? '' : 'none';
  if (!plaka) olcuGruplariSifirla();
'''),
    ('templates/stok.html', 'US1 · templates/stok.html blok 10',
     r'''  document.getElementById('sNoLabel').textContent = blok ? 'Blok No' : (plaka ? 'Blok No (kesildiği blok)' : 'Kasa No (ilk kasa, ops.)');
  document.getElementById('olcuLabel').textContent = blok ? 'Hacim (m³)' : 'Toplam m²';
''',
     r'''  /* US1: etiketler sadeleşti — "Blok No (kesildiği blok)" ve
     "Kasa No (ilk kasa, ops.)" parantezleri kalktı. Açıklamalar
     alanın ipucuna (baloncuk) taşındı, silinmedi. */
  const _no = document.getElementById('sNoLabel');
  _no.textContent = blok || plaka ? 'Blok No' : 'Kasa No';
  const _noG = document.getElementById('sBlokNo');
  _noG.title = plaka ? 'Plakanın kesildiği blok numarası'
             : (blok ? 'Bloğun numarası'
                     : 'İlk kasanın numarası — opsiyonel');
  document.getElementById('olcuLabel').textContent = blok ? 'Hacim (m³)' : 'Toplam m²';
  /* US1: ölçü ızgarasında miktar alanları blokta ölçülerin YANINDA,
     ötekilerde ALT SATIRDA başlıyor. */
  const _os = document.getElementById('olcuSatir');
  if (_os) _os.classList.toggle('ayri', !blok);
'''),
    ('templates/stok.html', 'US1 · templates/stok.html blok 11',
     r'''  const kdv = document.getElementById('kdvSatir');
  if (uretim) {
    document.getElementById('sKdv').value = 0;
    document.getElementById('sKdvDahil').checked = false;
    if (kdv) kdv.style.display = 'none';
    hesapla();
  } else {
    alisTipiDegisti();
  }
}

function alisTipiDegisti() {
  const kdvli = document.getElementById('sAlisTipi').value === 'yurtici_kdvli';
  document.getElementById('kdvSatir').style.display = kdvli ? '' : 'none';
''',
     r'''  /* US1: KDV oranı artık fatura satırında, "fiyata KDV dahil" ise
     işaret kutularının yanında. İkisi birlikte görünür, birlikte
     kaybolur — eskiden ikisi tek satırdaydı ve satır gizleniyordu. */
  if (uretim) {
    document.getElementById('sKdv').value = 0;
    document.getElementById('sKdvDahil').checked = false;
    kdvAlanlariGoster(false);
    hesapla();
  } else {
    alisTipiDegisti();
  }
  /* US1: üretimde fatura yok — tarih etiketi onu söylesin. */
  const _te = document.getElementById('sAlisTarihEtiket');
  if (_te) _te.textContent = uretim ? 'Üretim Tarihi' : 'Fatura Tarihi';
}

/* US1: KDV oranı ve "fiyata KDV dahil" artık iki ayrı yerde durduğu
   için ikisini TEK yerden açıp kapatıyoruz; ayrı ayrı yazılsaydı
   biri gizlenip öteki ekranda kalırdı. */
function kdvAlanlariGoster(goster) {
  const o = document.getElementById('kdvOranAlan');
  const d = document.getElementById('kdvDahilAlan');
  if (o) o.style.display = goster ? '' : 'none';
  if (d) d.style.display = goster ? '' : 'none';
}

function alisTipiDegisti() {
  const kdvli = document.getElementById('sAlisTipi').value === 'yurtici_kdvli';
  kdvAlanlariGoster(kdvli);
'''),
    ('templates/stok.html', 'US1 · templates/stok.html blok 12',
     r'''    ['ozellik',   'Yüzey / Özellik', false],
''',
     r'''    ['ozellik',   'Özellik',         false],
'''),
    ('templates/stok.html', 'US1 · templates/stok.html blok 13',
     r'''    ['ozellik',       'Yüzey / Özellik', false],
''',
     r'''    ['ozellik',       'Özellik',         false],
'''),
    ('templates/kesim.html', 'US1 · templates/kesim.html blok 1',
     r'''          <div class="form-alan"><label>Yüzey / Özellik (ortak)</label>
''',
     r'''          <div class="form-alan"><label>Özellik (ortak)</label>
'''),
    ('templates/kesim.html', 'US1 · templates/kesim.html blok 2',
     r'''  ['ozellik',       'Yüzey / Özellik', false],
''',
     r'''  ['ozellik',       'Özellik',         false],
'''),
    ('templates/proforma.html', 'US1 · templates/proforma.html blok 1',
     r'''        <div class="form-alan"><label>Yüzey / Özellik</label>
''',
     r'''        <div class="form-alan"><label>Özellik</label>
'''),
    ('templates/siparis.html', 'US1 · templates/siparis.html blok 1',
     r'''          <div class="form-alan" id="kOzellikAlan"><label>Yüzey / Özellik</label><input id="kOzellik" placeholder="Polished, Honed…"></div>
''',
     r'''          <div class="form-alan" id="kOzellikAlan"><label>Özellik</label><input id="kOzellik" placeholder="Polished, Honed…"></div>
'''),
    ('tests/test_kritik.py', 'US1 · tests/test_kritik.py blok 1',
     r'''    assert 'Tanımlı kasa yok' in _n, 'boş liste uyarısı yok'
''',
     r'''    assert 'Tanımlı kasa yok' in _n, 'boş liste uyarısı yok'


# ══════════════════════════════════════════════════════════════════
#  US1 · YENİ STOK FORMU — ÜÇ TİP, ÜÇ DÜZEN, TEK IZGARA
#
#  Bahadır üç tip için ayrı düzen çizdi. Satırları tip tip yazmak
#  üç kopya demekti; bunun yerine alanlar TEK 4 sütunlu ızgarada
#  sırayla duruyor ve ızgara gizli alanı atlıyor. Sıralama şu üç
#  düzeni birden veriyor:
#
#    BLOK    ürün tipi · üretici · menşe · giriş tarihi
#            cins · blok no · kaynak · alış tipi
#            alış fiyatı · döviz · fiyat birimi · tonaj
#            boy · yükseklik · en · hacim
#            fatura durumu · fatura no · fatura tarihi · kdv oranı
#    PLAKA   ... cins · blok no · özellik · kaynak
#            alış tipi · alış fiyatı · döviz · fiyat birimi
#            boy · yükseklik · kalınlık
#            stok adedi · başlangıç slab no · toplam m² · + grup
#    EBATLI  aynısı; kasa no, kasa adedi · kasa içi adet · toplam m²
#
#  ÖLÇÜLDÜ (tarayıcıda, 880 px modal): üç düzen de çizime birebir
#  uydu, hiçbir seçici kırpılmıyor, kaydırma yok. Üç tip de formdan
#  kaydedildi ve veritabanında eksiksiz çıktı.
# ══════════════════════════════════════════════════════════════════

def _us1_sira(metin, kap_id):
    """Bir ızgaranın içindeki alanları SIRAYLA döner."""
    import re as _re
    _p = metin.index(f'id="{kap_id}"')
    _p = metin.index('>', _p) + 1
    _derinlik, _i, _son = 1, _p, _p
    while _derinlik and _i < len(metin):
        _a = metin.find('<div', _i)
        _k = metin.find('</div>', _i)
        if _k == -1:
            break
        if _a != -1 and _a < _k:
            _derinlik += 1; _i = _a + 4
        else:
            _derinlik -= 1; _i = _k + 6; _son = _k
    _ic = metin[_p:_son]
    return [m.group(1) for m in
            _re.finditer(r'<(?:input|select|button)[^>]*id="(s[A-Z]\w*)"', _ic)]


def test_us1_alanlar_tipe_gore_dogru_sirada():
    """Izgaradaki SIRA üç düzeni birden üretiyor.

    Sıra bozulursa blokta 'alış tipi' alt satıra, plakada 'özellik'
    yanlış sütuna düşer — ekrana bakmadan anlaşılmaz. Bu yüzden
    sıranın kendisi test ediliyor."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/stok.html'),
                 encoding='utf-8').read()
    assert _us1_sira(m, 'kimlikSatir') == [
        'sCins', 'sBlokNo', 'sOzellik', 'sKaynak', 'sAlisTipi',
        'sFiyat', 'sDoviz', 'sFiyatBirim', 'sTonaj'], 'kimlik sırası bozuk'
    assert _us1_sira(m, 'olcuSatir') == [
        'sBoy', 'sYuk', 'sEn', 'sKal', 'sAdet', 'sKasaAdedi',
        'sKasaIci', 'sBasNo', 'sOlcu'], 'ölçü/miktar sırası bozuk'

    # Blok dışında miktar alanları ALT SATIRDAN başlar.
    assert '.f4.ayri > #adetAlan, .f4.ayri > #kasaAdediAlan{grid-column-start:1}' in m, \
        'satır başı kuralı yok'
    assert "_os.classList.toggle('ayri', !blok)" in m, \
        'satır başı tipe göre açılmıyor'


def test_us1_etiketler_sadelesti_ama_bilgi_silinmedi():
    """Parantezli açıklamalar etiketten çıktı, ipucuna taşındı.

    "Blok No (kesildiği blok)", "Kasa No (ilk kasa, ops.)",
    "Üretici / Ocak", "Yüzey / Özellik", "Alış / Fatura Tarihi" —
    hepsi sadeleşti. Açıklamaları SİLMEK başka şey; onlar alanın
    baloncuğunda duruyor."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/stok.html'),
                 encoding='utf-8').read()
    # Etiket olarak YAZILIYOR mu diye bakılır; yama notunda adının
    # geçmesi başka şey (KF1'de bu tuzağa bir kez düşüldü).
    for _eski in ('Üretici / Ocak', 'Yüzey / Özellik'):
        assert f'>{_eski}<' not in m, f'eski etiket duruyor: {_eski}'
    for _eski in ('Blok No (kesildiği blok)', 'Kasa No (ilk kasa, ops.)'):
        assert f"'{_eski}'" not in m, f'eski etiket duruyor: {_eski}'
    assert '<label>Üretici</label>' in m, 'Üretici etiketi yok'
    assert '<label>Özellik</label>' in m, 'Özellik etiketi yok'
    assert "_no.textContent = blok || plaka ? 'Blok No' : 'Kasa No'" in m, \
        'no etiketi sadeleşmemiş'
    # Açıklamalar ipucuna taşındı.
    assert 'kesildiği blok numarası' in m, 'plaka ipucu kayıp'
    assert 'İlk kasanın numarası' in m, 'kasa ipucu kayıp'
    assert "Ülkeler'den ekleyin" in m, 'menşe ipucu kayıp'

    # ÜRETİMDE fatura yok: etiket "Üretim Tarihi" demeli.
    assert 'id="sAlisTarihEtiket">Fatura Tarihi<' in m, \
        'tarih etiketi sadeleşmemiş'
    assert "uretim ? 'Üretim Tarihi' : 'Fatura Tarihi'" in m, \
        'üretimde tarih etiketi düzeltilmiyor'


def test_us1_kdv_ikilisi_birlikte_gizlenir():
    """KDV oranı ve "fiyata KDV dahil" artık AYRI yerlerde.

    Eskiden ikisi tek satırdaydı ve satır gizleniyordu. Ayrı yerlere
    dağılınca biri gizlenip öteki ekranda kalma riski doğdu; ikisini
    tek fonksiyon açıp kapatıyor."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/stok.html'),
                 encoding='utf-8').read()
    assert 'id="kdvSatir"' not in m, 'eski KDV satırı duruyor'
    assert 'function kdvAlanlariGoster(' in m, 'ortak açıp kapatıcı yok'
    for _id in ('kdvOranAlan', 'kdvDahilAlan'):
        assert f"getElementById('{_id}')" in m, f'{_id} okunmuyor'
    # Gizleme KURALI tek yerden: doğrudan style ataması kalmamalı.
    for _id in ('kdvOranAlan', 'kdvDahilAlan'):
        assert f"getElementById('{_id}').style.display" not in m, \
            f'{_id} ortak fonksiyonun dışından gizleniyor'
    assert m.count('kdvAlanlariGoster(') == 3, \
        'açıp kapatıcı beklenen yerlerde çağrılmıyor'

    # Ölçü grubu kutusu yalnız grup varken.
    assert "alan.style.display = ek.length ? '' : 'none'" in m, \
        'boş ölçü grubu kutusu gizlenmiyor'
    assert 'id="grupEkleAlan"' in m, 'grup ekle düğmesi miktar satırında değil'
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA US1 — YENİ STOK FORMU, ÇİZDİĞİN DÜZENDE')
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
        print('    python3 yama_us1.py            # rapor')
        print('    python3 yama_us1.py --uygula')
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
        print('  ⊙ Yama US1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_us1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_us1'
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
    print('    Depo -> Stok -> Yeni Stok. Urun tipini BLOK, PLAKA ve')
    print('    EBATLI arasinda degistir: alanlar her tipte senin')
    print('    cizdigin duzene yerlesiyor.')
    print()
    print('    Not: kaynak "Uretim" secilirse tarih etiketi')
    print('    "Uretim Tarihi" olur — uretim stogunun faturasi yok.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

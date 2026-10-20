#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA B1 — KESİM'E EXCEL'DEN ÜRETİLECEK ÜRÜN SATIRLARI
======================================================

ÖNKOŞUL: yama_ur2.py uygulanmış olmalı.

UR1'de konuştuğumuz B işi bu. Kendi bloğunu kestiğinde doğru yol
Kesim modülü — ama orada hedef satırları tek tek giriliyordu. Senin
9 ölçü grubun zaten Excel'de.

── NE GELDİ ──
  Kesim penceresinde "+ Ürünü listeye ekle"nin yanında
  "Excel'den yükle". Dosya → sayfa → sütun eşleştirme → önizleme →
  listeye ekle. Satırlar MEVCUT listeye EKLENİYOR: elle girdiklerin
  duruyor.

  Buradan giren satırlar normal kesim akışına katılıyor. Kesimi
  kaydedince:
      · blok stoktan DÜŞER
      · m² maliyeti bloğun maliyetinden TÜRER
      · kesim izi (kesim_detay) yazılır
  Stok içe aktarmanın yapamadığı üç şey buydu; UR1'deki çift sayım
  kapısı da artık gerçek bir alternatife yönlendiriyor.

  Hedef tipi Excel'den DEĞİL, kesim yönünden geliyor (Blok→Plaka
  ise PLAKA). Excel'e tip sütunu koymak, aynı bilgiyi iki yerden
  sormak olurdu.

── ORTAK PARÇA: static/js/excel_ortak.js (YENİ DOSYA) ──
  Stok içe aktarma ile Kesim'in ekranları farklı (biri fiyat/fatura
  soruyor, öteki sormuyor) ama ALTINDAKİ işler aynı: başlıktan alan
  tahmini, sayı ayrıştırma, birleştirilmiş hücre doldurması.

  Bu üçü ortak dosyaya taşındı ve stok ekranı ARTIK ORADAN
  kullanıyor. Kopyalamadım çünkü ikisi de ÖLÇÜLMÜŞ hata düzeltmesi
  taşıyor:

      BS3  "1,234.56" bin kat küçük okunuyordu
      X1   birleştirilmiş hücrede 6 satırlık listeden 1 kayıt

  İkinci kopya, düzeltmenin yalnız birinde yaşamasıyla biterdi —
  bu projede MF4'te (iki `yedekGovde`) ve YP3'te (iki firma formu)
  tam bu oldu.

  STOK İÇE AKTARMANIN DAVRANIŞI DEĞİŞMEDİ. Bunu yapısal testle
  değil, GERÇEK bir xlsx'i tarayıcıda iki ekrandan da geçirerek
  ölçtüm — aşağıda.

── YOL ÜSTÜNDE ──
  · Kesim hedef listesi m²'yi tam basamakla yazıyordu; Excel'den
    gelen satırlarda önizleme 20,08 derken liste 20,077 diyordu.
    Aynı şeyin iki yerde farklı görünmesi bu projede en kötü hata
    biçimi olarak geçiyor — ikisi de iki basamak.
  · KENDİ HATAM: ortak dosyaya kazara bir kelime düşürdüm.
    `node --check` GEÇTİ (sözdizimi geçerliydi: tanımsız bir işlev
    çağrısı) ama çalışma anında patlardı. Ayrıştırıcı denetimi
    yetmiyor; testlerden biri artık işlevleri gerçekten ÇAĞIRIYOR.

── ÖLÇÜLDÜ (gerçek xlsx, tarayıcıda) ──
  Dosya senin listeni taklit ediyor: blok no ve cins YALNIZCA ilk
  satırda (birleştirilmiş hücre), ölçüler her satırda farklı.

      beklenen        9 satır · 50 parça · 252,86 m²
      stok ekranı     9 satır · 50 parça · 252,86 m²  cins ve blok
                      dokuz satıra da yayıldı
      kesim ekranı    9 satır · 50 parça · 252,86 m²
                      "8 satırda birleştirilmiş hücre tamamlandı"
      listeye ekle    9 hedef · 50 parça · 252,86 m²
                      kesim özetindeki "Çıkan" aynı sayıyı gösteriyor
      JS hatası       yok

  123 test geçti (120 + 3 yeni kalıcı test);
  firma · js · form · zincir · akis · degismezlik temiz.

── NE YAPMADIM ──
  Kesimde ATLANACAK NO (kırılan plaka) alanı Excel'den gelmiyor;
  onu pencerede elle giriyorsun. Excel'de kırık plaka sütunu
  tutuyorsan söyle, eşleştirmeye eklerim.

DOSYALAR
--------
  static/js/excel_ortak.js  YENİ — ortak eşleştirme parçası
                            (tam dosya, base64)
  templates/kesim.html      Excel'den yükle penceresi ve mantığı
  templates/stok.html       ortak parçaya bağlandı (davranış aynı)
  tests/test_kritik.py      3 yeni test

Şema yok, göç yok. Veri dokunulmuyor.

KULLANIM
--------
  python3 yama_b1.py            # RAPOR
  python3 yama_b1.py --uygula
  sudo systemctl restart milestone-erp
  (tarayıcıda Ctrl+F5 — yeni bir .js dosyası geliyor, önbellek
   tazelenmezse "ExcelOrtak is not defined" görürsün)
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
    'templates/stok.html': 'B1: sayı ayrıştırma (BS3) ve birleştirilmiş hücre',
    'templates/kesim.html': 'B1 · EXCEL\'DEN ÜRETİLECEK ÜRÜN SATIRLARI',
    'tests/test_kritik.py': 'def test_b1_excel_ortak_parcasi_tek_kopya',
    'static/js/excel_ortak.js': 'EXCEL EŞLEŞTİRME — ORTAK PARÇA',
}
ONKOSUL = {
    'templates/stok.html': 'UR2 · ORTAK CİNS VE YÜZEY',
    'templates/kesim.html': 'function hedefEkle',
    'tests/test_kritik.py': 'def test_ur2_mense_listeden_seciliyor',
}
TAM_YAZILAN = ['static/js/excel_ortak.js']

DEGISIKLIKLER = [
    ('templates/stok.html', 'B1 · templates/stok.html blok 1',
     r'''{% block head %}
''',
     r'''{% block head %}
<!-- B1: Excel eşleştirmenin ortak parçası — sayı ayrıştırma,
     başlık tahmini, birleştirilmiş hücre doldurması. Stok ve
     Kesim ekranlarının İKİSİ de kullanıyor; kopyalanınca bu
     projede hep ayrıştılar. -->
<script src="{{ url_for('static', filename='js/excel_ortak.js') }}"></script>
'''),
    ('templates/stok.html', 'B1 · templates/stok.html blok 2',
     r'''const TP_IPUCU = {
  cins: ['cins', 'urun', 'ürün', 'malzeme', 'tas', 'taş', 'material', 'type'],
  blok_no: ['blok', 'block', 'kasa', 'ref', 'parti'],
  boy: ['boy', 'uzunluk', 'length', 'en1'],
  yukseklik: ['yukseklik', 'yükseklik', 'yuk', 'genislik', 'genişlik', 'width', 'height'],
  en: ['en', 'derinlik', 'depth'],
  kalinlik: ['kalinlik', 'kalınlık', 'kal', 'thickness'],
  ozellik: ['yuzey', 'yüzey', 'ozellik', 'özellik', 'finish', 'surface'],
  fiyat: ['fiyat', 'birim', 'price', 'tutar', 'ucret', 'ücret'],
  adet: ['adet', 'miktar', 'qty', 'quantity'],
  tonaj: ['ton', 'tonaj', 'agirlik', 'ağırlık', 'weight'],
  kasa_adedi: ['kasa adedi', 'kasa sayi', 'paket'],
  kasa_ici_adet: ['kasa ici', 'kasa içi', 'ici adet', 'içi adet'],
  aciklama: ['aciklama', 'açıklama', 'not', 'description', 'desc'],
};
''',
     r'''/* B1: ipuçları ORTAK dosyada (static/js/excel_ortak.js).
   Kesim ekranı da aynı listeyi kullanıyor; iki kopya,
   yeni bir sütun adını yalnız birine eklemekle biterdi. */
const TP_IPUCU = ExcelOrtak.IPUCU;
'''),
    ('templates/stok.html', 'B1 · templates/stok.html blok 3',
     r'''  const fd = new FormData();
  fd.append('dosya', f);
  try {
    /* S1: api() sarmalayıcısı kullanılmıyor (multipart yükleme),
       CSRF başlığı ELLE eklenmeli. */
    const r = await fetch('/api/v2/excel/analiz', { method: 'POST', body: fd,
      headers: { 'X-CSRF-Token': window.CSRF_TOKEN } });
    const d = await r.json();
    if (!r.ok || !d.ok) { bildir(d.mesaj || 'Dosya okunamadı.', true); 
      document.getElementById('tDosyaAd').textContent = f.name + ' — okunamadı'; return; }

''',
     r'''  try {
    /* B1: dosya çözme ortak dosyada (Kesim de aynısını kullanıyor). */
    const d = await ExcelOrtak.dosyaAnaliz(f);
'''),
    ('templates/stok.html', 'B1 · templates/stok.html blok 4',
     r'''  const ipuclari = TP_IPUCU[alanKod] || [];
  const sadelestir = t => String(t || '').toLocaleLowerCase('tr')
    .replace(/[ıİ]/g, 'i').replace(/[şŞ]/g, 's').replace(/[ğĞ]/g, 'g')
    .replace(/[üÜ]/g, 'u').replace(/[öÖ]/g, 'o').replace(/[çÇ]/g, 'c').trim();
  /* Üç aşamalı: önce tam eşleşme, sonra baştan eşleşme, en son içerme.
     Tek aşamada yapılsaydı "Genişlik" başlığı içinde "en" geçtiği için
     En alanına yanlış eşleşebilirdi. */
  const sadeBas = basliklar.map(sadelestir);
  const sadeIp = ipuclari.map(sadelestir);
  for (const kural of ['tam', 'bas', 'icerik']) {
    for (let i = 0; i < sadeBas.length; i++) {
      const b = sadeBas[i];
      if (!b) continue;
      for (const s of sadeIp) {
        if (!s) continue;
        if (kural === 'tam' && b === s) return i;
        if (kural === 'bas' && b.startsWith(s)) return i;
        if (kural === 'icerik' && b.includes(s)) return i;
      }
    }
  }
  return -1;
''',
     r'''  return ExcelOrtak.tahmin(alanKod, basliklar, TP_IPUCU);
'''),
    ('templates/stok.html', 'B1 · templates/stok.html blok 5',
     r'''  const sayi = v => {
    if (v === '' || v === null || v === undefined) return 0;
    if (typeof v === 'number') return isFinite(v) ? v : 0;
    /* BS3: hem "1.234,56" (TR) hem "1,234.56" (EN) doğru okunur.
       Eskiden yalnızca İLK virgül noktaya çevriliyordu:
       "1,234.56" → "1.234.56" → 1.234 (bin kat küçük). İkisi
       birden varsa SONUNCUSU ondalık ayırıcıdır. */
    let t = String(v).replace(/\s/g, '').replace(/[^\d.,\-]/g, '');
    const sv = t.lastIndexOf(','), sn = t.lastIndexOf('.');
    if (sv >= 0 && sn >= 0) {
      t = sv > sn ? t.replace(/\./g, '').replace(',', '.') : t.replace(/,/g, '');
    } else if (sv >= 0) {
      t = t.replace(',', '.');
    }
    const n = parseFloat(t);
    return isFinite(n) ? n : 0;
  };

  TP_SATIRLAR = [];
  const hatalar = [];
  /* X1 — BİRLEŞTİRİLMİŞ HÜCRE (aşağı doğru doldurma)
     Çeki listelerinde blok no ve malzeme adı birleştirilmiş hücrede
     yazılır: tek blok, birçok satır. Excel bu değeri YALNIZCA ilk
     satıra koyar, kalanlar boş gelir ve "cins boş" diye atlanırdı.
     6 satırlık listeden 1 kayıt çıkıyordu.

     Yalnızca birleştirilmiş hücrede kullanılan alanlar doldurulur.
     ÖLÇÜ ve ADET doldurulmaz — onlar her satırda farklıdır, boş
     olmaları gerçek bir hatadır. */
  const DOLDURULACAK = ['cins', 'blok_no', 'ozellik', 'kalinlik', 'kasa_no'];
  const oncekiDeger = {};
  let dolduruldu = 0;

  (TP_AKTIF.satirlar || []).forEach((satir, idx) => {
    const al = kod => (kod in harita) ? satir[harita[kod]] : '';
    const kayit = { _satir: idx + 2 };   // +2: başlık satırı + 1 tabanlı
    alanlar.forEach(([kod]) => {
      if (['boy', 'yukseklik', 'en', 'kalinlik', 'fiyat', 'adet', 'tonaj',
           'kasa_adedi', 'kasa_ici_adet'].includes(kod)) kayit[kod] = sayi(al(kod));
      else kayit[kod] = String(al(kod) ?? '').trim();
    });

    /* ADET EŞLEŞTİRİLMEMİŞSE 1 SAYILIR.
       Sütun haritada yoksa al('adet') boş döner, sayi('') = 0 ve
       önizlemede "0 adet" görünüyordu. Kaydetme tarafı zaten
       `Math.max(1, ...)` ile 1'e düzeltiyordu — yani kayıt doğru,
       ÖNİZLEME yanlıştı. İki yerin farklı sayı göstermesi, en kötü
       hata biçimi: kullanıcı yanlış olanı doğru sanıyor.
       Her plaka, aksi belirtilmedikçe 1 adettir. */
    if (!('adet' in harita) || !(kayit.adet > 0)) kayit.adet = 1;

    /* Boşsa üstteki satırın değerini al; doluysa hatırla. */
    let buSatirDolduruldu = false;
    DOLDURULACAK.forEach(kod => {
      const bos = (kod === 'kalinlik') ? !(kayit[kod] > 0) : !kayit[kod];
      if (bos && oncekiDeger[kod] !== undefined && oncekiDeger[kod] !== '') {
        kayit[kod] = oncekiDeger[kod];
        buSatirDolduruldu = true;
      } else if (!bos) {
        oncekiDeger[kod] = kayit[kod];
      }
    });
    if (buSatirDolduruldu) dolduruldu++;
''',
     r'''  /* B1: sayı ayrıştırma (BS3) ve birleştirilmiş hücre doldurması
     (X1) ORTAK dosyada — Kesim ekranı da aynılarını kullanıyor.
     Burada kalan iş, çıkan kayıtları bu ekranın kurallarına göre
     süzmek. */
  const SAYISAL = ['boy', 'yukseklik', 'en', 'kalinlik', 'fiyat', 'adet',
                   'tonaj', 'kasa_adedi', 'kasa_ici_adet'];
  const DOLDURULACAK = ['cins', 'blok_no', 'ozellik', 'kalinlik', 'kasa_no'];

  const cikti = ExcelOrtak.satirlariCikar(
    TP_AKTIF.satirlar || [], alanlar, harita,
    { sayisal: SAYISAL, doldurulacak: DOLDURULACAK });
  const dolduruldu = cikti.dolduruldu;

  TP_SATIRLAR = [];
  const hatalar = [];

  cikti.kayitlar.forEach(kayit => {
    /* ADET EŞLEŞTİRİLMEMİŞSE 1 SAYILIR.
       Sütun haritada yoksa değer boş döner, sayı 0 olur ve
       önizlemede "0 adet" görünüyordu. Kaydetme tarafı zaten
       `Math.max(1, ...)` ile 1'e düzeltiyordu — yani kayıt doğru,
       ÖNİZLEME yanlıştı. İki yerin farklı sayı göstermesi, en kötü
       hata biçimi: kullanıcı yanlış olanı doğru sanıyor.
       Her plaka, aksi belirtilmedikçe 1 adettir. */
    if (!('adet' in harita) || !(kayit.adet > 0)) kayit.adet = 1;
'''),
    ('templates/kesim.html', 'B1 · templates/kesim.html blok 1',
     r'''<style>
''',
     r'''<!-- B1: Excel eşleştirmenin ortak parçası — sayı ayrıştırma,
     başlık tahmini, birleştirilmiş hücre doldurması. Stok ve
     Kesim ekranlarının İKİSİ de kullanıyor; kopyalanınca bu
     projede hep ayrıştılar. -->
<script src="{{ url_for('static', filename='js/excel_ortak.js') }}"></script>
<style>
'''),
    ('templates/kesim.html', 'B1 · templates/kesim.html blok 2',
     r'''  .kutu{border:1px dashed var(--cizgi-koyu);border-radius:var(--r-kucuk);padding:14px;margin-bottom:14px}
''',
     r'''  /* B1: Excel eşleştirme kutuları — stok ekranındaki `.tp-*` ile
     aynı ölçüler, iki ekran yan yana aynı görünsün. */
  .tp-eslestir{display:grid;grid-template-columns:repeat(2,1fr);gap:8px 14px}
  .tp-cift{display:flex;align-items:center;gap:8px}
  .tp-cift label{flex:0 0 42%;font-size:.8rem;font-weight:500}
  .tp-cift select{flex:1;min-width:0;border:1px solid var(--cizgi-koyu);
    border-radius:var(--r-kucuk);padding:7px 9px;font-family:var(--govde);
    font-size:.85rem;background:var(--yuzey)}
  .kutu{border:1px dashed var(--cizgi-koyu);border-radius:var(--r-kucuk);padding:14px;margin-bottom:14px}
'''),
    ('templates/kesim.html', 'B1 · templates/kesim.html blok 3',
     r'''        <button class="ekle-btn" onclick="hedefEkle()">+ Ürünü listeye ekle</button>
''',
     r'''        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <button class="ekle-btn" style="margin:0" onclick="hedefEkle()">+ Ürünü listeye ekle</button>
          <!-- ── B1 · EXCEL'DEN TOPLU HEDEF ──
               Kesim çıktısı ölçü ölçü değişiyor: 9 ayrı ölçü grubu
               tek tek yazılıyordu. Aynı liste zaten Excel'de geliyor.

               Buradan girilen satırlar blok stoktan DÜŞER, m²
               maliyeti bloğun maliyetinden TÜRER ve kesim izi
               yazılır — stok içe aktarmanın yapamadığı üç şey. -->
          <button class="ekle-btn" style="margin:0" onclick="kesimExcelAc()">
            Excel'den yükle</button>
        </div>
'''),
    ('templates/kesim.html', 'B1 · templates/kesim.html blok 4',
     r'''      <button class="btn-yeni" id="fKaydet" onclick="kesimKaydet()">Kesimi Kaydet</button>
''',
     r'''      <button class="btn-yeni" id="fKaydet" onclick="kesimKaydet()">Kesimi Kaydet</button>
    </div>
  </div>
</div>

<!-- ══ B1 · EXCEL'DEN HEDEF SATIRI ══
     Kesim penceresinin ÜSTÜNDE açılıyor (z-index daha yüksek):
     kapanınca altındaki kesim formu seçimleriyle duruyor. Ayrı bir
     sayfaya gitmek, seçili bloğu ve girilen üretim numarasını
     kaybettirirdi. -->
<div class="modal-ortu" id="excelModal" style="z-index:60"
     onclick="if(event.target===this)kesimExcelKapat()">
  <div class="modal" style="width:760px" role="dialog"
       aria-label="Excel'den hedef satırı">
    <div class="modal-bas">
      <h3>Excel'den üretilecek ürünler</h3>
      <p>Dosyayı seç · sayfayı seç · sütunları eşleştir · listeye ekle</p>
    </div>
    <div class="modal-gov">
      <div class="kutu">
        <h5>1 · Dosya</h5>
        <input type="file" id="kDosya" accept=".xlsx,.xlsm" style="display:none"
               onchange="kesimExcelDosya(this)">
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <button type="button" class="ekle-btn" style="margin:0"
                  onclick="document.getElementById('kDosya').click()">Dosya Seç…</button>
          <span id="kDosyaAd" style="font-size:.84rem;color:var(--soluk)">Henüz dosya seçilmedi</span>
        </div>
      </div>

      <div class="kutu" id="kAdimSayfa" style="display:none">
        <h5>2 · Sayfa</h5>
        <div class="form-alan">
          <select id="kSayfa" onchange="kesimExcelSayfa()"></select>
        </div>
      </div>

      <div class="kutu" id="kAdimEslestir" style="display:none">
        <h5>3 · Sütun eşleştirme</h5>
        <p style="font-size:.78rem;color:var(--soluk);margin:-4px 0 10px">
          Yıldızlı alanlar zorunlu. Cins ve yüzey Excel'de yoksa
          aşağıdaki ortak alandan verilebilir.</p>
        <div id="kEslestirme" class="tp-eslestir"></div>
      </div>

      <div class="kutu" id="kAdimOrtak" style="display:none">
        <h5>4 · Tüm satırlar için ortak</h5>
        <div class="form-satir f3">
          <div class="form-alan"><label>Cins (ortak)</label>
            <input id="kCins" placeholder="Excel'de yoksa" oninput="kesimExcelOnizle()"></div>
          <div class="form-alan"><label>Yüzey / Özellik (ortak)</label>
            <input id="kOzellik" placeholder="Excel'de yoksa" oninput="kesimExcelOnizle()"></div>
          <div class="form-alan"><label>Kalınlık (cm) · ortak</label>
            <input id="kKalinlik" type="number" step="0.1" placeholder="Excel'de yoksa"
                   oninput="kesimExcelOnizle()"></div>
        </div>
      </div>

      <div class="kutu" id="kAdimOnizleme" style="display:none">
        <h5>5 · Önizleme</h5>
        <div id="kOzet" style="font-size:.85rem;margin-bottom:10px"></div>
        <div id="kHatalar"></div>
        <div id="kOnizleme"></div>
      </div>
    </div>
    <div class="modal-alt">
      <button class="iptal-btn" onclick="kesimExcelKapat()">Vazgeç</button>
      <button class="btn-yeni" id="kEkle" disabled
              onclick="kesimExcelUygula()">Listeye Ekle</button>
'''),
    ('templates/kesim.html', 'B1 · templates/kesim.html blok 5',
     r'''function hedefListeCiz() {
''',
     r'''/* ══════════════════════════════════════════════════════════════
   B1 · EXCEL'DEN ÜRETİLECEK ÜRÜN SATIRLARI
   ══════════════════════════════════════════════════════════════

   Kesim çıktısı ölçü ölçü değişiyor; 9 ayrı ölçü grubunu tek tek
   yazmak yerine zaten Excel'de gelen listeyi okuyoruz.

   NEDEN STOK İÇE AKTARMA DEĞİL DE BURASI: sistemde KAYITLI bir
   bloktan kesilen plakalar stok içe aktarmayla girilirse blok
   stokta kesilmemiş gibi kalır (aynı mal iki kez sayılır),
   plakaların maliyeti bloktan türemez ve kesim izi oluşmaz.
   Buradan girilen satırlar normal kesim akışına katılıyor —
   kaydet'e basınca blok düşüyor, maliyet bloktan dağılıyor,
   kesim_detay yazılıyor.

   Sayı ayrıştırma, başlık tahmini ve birleştirilmiş hücre
   doldurması ORTAK dosyadan (static/js/excel_ortak.js); stok
   ekranı da aynılarını kullanıyor. */
const KX_ALANLAR = [
  ['cins',          'Cins',            false],
  ['ozellik',       'Yüzey / Özellik', false],
  ['boy',           'Boy (cm)',        true],
  ['yukseklik',     'Yükseklik (cm)',  true],
  ['kalinlik',      'Kalınlık (cm)',   false],
  ['adet',          'Adet',            false],
  ['kasa_ici_adet', 'Kasa İçi Adet',   false],
];
const KX_SAYISAL = ['boy', 'yukseklik', 'kalinlik', 'adet', 'kasa_ici_adet'];
/* Birleştirilmiş hücrede gelenler. ÖLÇÜ ve ADET yok: onlar her
   satırda farklıdır, boş olmaları gerçek bir hatadır. */
const KX_DOLDURULACAK = ['cins', 'ozellik', 'kalinlik'];

let KX_SAYFALAR = [], KX_AKTIF = null, KX_SATIRLAR = [];

function kesimExcelAc() {
  KX_SAYFALAR = []; KX_AKTIF = null; KX_SATIRLAR = [];
  document.getElementById('kDosya').value = '';
  document.getElementById('kDosyaAd').textContent = 'Henüz dosya seçilmedi';
  ['kAdimSayfa', 'kAdimEslestir', 'kAdimOrtak', 'kAdimOnizleme']
    .forEach(i => document.getElementById(i).style.display = 'none');
  document.getElementById('kEkle').disabled = true;
  /* Formdaki cins/yüzey/kalınlık varsa ortak alana taşı: aynı şeyi
     iki kez yazdırmanın anlamı yok. */
  document.getElementById('kCins').value = document.getElementById('hCins').value.trim();
  document.getElementById('kOzellik').value = document.getElementById('hOzellik').value.trim();
  document.getElementById('kKalinlik').value = document.getElementById('hKal').value || '';
  document.getElementById('excelModal').classList.add('acik');
}

function kesimExcelKapat() {
  document.getElementById('excelModal').classList.remove('acik');
}

async function kesimExcelDosya(inp) {
  const f = inp.files && inp.files[0];
  if (!f) return;
  document.getElementById('kDosyaAd').textContent = f.name + ' — okunuyor…';
  try {
    const d = await ExcelOrtak.dosyaAnaliz(f);
    KX_SAYFALAR = d.sayfalar || [];
    const toplam = KX_SAYFALAR.reduce((a, x) => a + x.satir_sayisi, 0);
    document.getElementById('kDosyaAd').textContent =
      `${d.dosya_adi} · ${KX_SAYFALAR.length} sayfa · ${toplam} satır`;
    document.getElementById('kSayfa').innerHTML = KX_SAYFALAR
      .map((x, i) => `<option value="${i}">${kacar(x.ad)} (${x.satir_sayisi} satır)</option>`).join('');
    document.getElementById('kAdimSayfa').style.display = '';
    kesimExcelSayfa();
  } catch (e) {
    bildir(e.message || 'Dosya yüklenemedi', true);
    document.getElementById('kDosyaAd').textContent = f.name + ' — okunamadı';
  }
}

function kesimExcelSayfa() {
  const i = parseInt(document.getElementById('kSayfa').value, 10) || 0;
  KX_AKTIF = KX_SAYFALAR[i] || null;
  if (!KX_AKTIF) return;
  ExcelOrtak.eslestirmeCiz(document.getElementById('kEslestirme'),
    KX_ALANLAR, KX_AKTIF.basliklar || [], kesimExcelOnizle);
  ['kAdimEslestir', 'kAdimOrtak', 'kAdimOnizleme']
    .forEach(x => document.getElementById(x).style.display = '');
  kesimExcelOnizle();
}

function kesimExcelOnizle() {
  if (!KX_AKTIF) return;
  const yon = document.getElementById('fYon').value;
  const hedefTip = yon.endsWith('EBATLI') ? 'EBATLI' : 'PLAKA';
  const harita = ExcelOrtak.haritaOku(document.getElementById('kEslestirme'));
  const cikti = ExcelOrtak.satirlariCikar(KX_AKTIF.satirlar || [], KX_ALANLAR,
    harita, { sayisal: KX_SAYISAL, doldurulacak: KX_DOLDURULACAK });

  const oCins = (document.getElementById('kCins').value || '').trim();
  const oOzellik = (document.getElementById('kOzellik').value || '').trim();
  const oKal = parseFloat(document.getElementById('kKalinlik').value) || 0;

  KX_SATIRLAR = [];
  const hatalar = [];
  cikti.kayitlar.forEach(k => {
    if (!k.cins) k.cins = oCins;
    if (!k.ozellik) k.ozellik = oOzellik;
    if (!(k.kalinlik > 0)) k.kalinlik = oKal || 2;
    /* Adet sütunu eşleşmemişse her satır 1 parçadır — stok
       aktarmasındaki kuralın aynısı. */
    if (!('adet' in harita) || !(k.adet > 0)) k.adet = 1;

    if (!k.cins) {
      hatalar.push(`Satır ${k._satir}: cins yok — sütun eşleşmedi ve ortak cins girilmedi`);
      return;
    }
    if (!(k.boy > 0) || !(k.yukseklik > 0)) {
      hatalar.push(`Satır ${k._satir}: boy/yükseklik geçersiz`);
      return;
    }
    k.hedef_tip = hedefTip;
    k.kasa_ici_adet = hedefTip === 'EBATLI'
      ? Math.max(1, Math.round(k.kasa_ici_adet || 1)) : undefined;
    k._m2 = (k.boy * k.yukseklik * k.adet) / 10000;
    KX_SATIRLAR.push(k);
  });

  const toplamM2 = KX_SATIRLAR.reduce((a, k) => a + k._m2, 0);
  const toplamAdet = KX_SATIRLAR.reduce((a, k) => a + k.adet, 0);
  document.getElementById('kOzet').innerHTML =
    `<b>${KX_SATIRLAR.length}</b> satır · <b>${toplamAdet}</b> parça · `
    + `<b>${toplamM2.toLocaleString('tr-TR', {maximumFractionDigits: 2})} m²</b>`
    + (cikti.dolduruldu ? ` · ${cikti.dolduruldu} satırda birleştirilmiş hücre tamamlandı` : '');

  document.getElementById('kHatalar').innerHTML = hatalar.length
    ? `<div class="not" style="background:var(--kehribar-bg);color:var(--kehribar);
         border-radius:var(--r-kucuk);padding:9px 12px;font-size:.8rem;margin-bottom:10px">
         ${hatalar.length} satır atlanacak:<br>${hatalar.slice(0, 6).map(kacar).join('<br>')}
         ${hatalar.length > 6 ? `<br>…ve ${hatalar.length - 6} tane daha` : ''}</div>`
    : '';

  document.getElementById('kOnizleme').innerHTML = KX_SATIRLAR.length
    ? KX_SATIRLAR.slice(0, 8).map(k => `
        <div class="hedef-satir">
          <span class="rozet rz-gri">${kacar(k.hedef_tip)}</span>
          <div><div>${kacar(k.cins)}${k.ozellik ? ' · ' + kacar(k.ozellik) : ''}</div>
            <div style="color:var(--soluk);font-size:.76rem">
              ${k.adet} adet · ${k.boy}×${k.yukseklik}×${k.kalinlik} cm</div></div>
          <span class="m">${k._m2.toLocaleString('tr-TR', {maximumFractionDigits: 2})} m²</span>
        </div>`).join('')
      + (KX_SATIRLAR.length > 8
         ? `<div style="font-size:.78rem;color:var(--soluk);padding:6px 0">
              …ve ${KX_SATIRLAR.length - 8} satır daha</div>` : '')
    : '<div class="bos" style="padding:12px">Aktarılacak satır yok.</div>';

  document.getElementById('kEkle').disabled = KX_SATIRLAR.length === 0;
}

function kesimExcelUygula() {
  if (!KX_SATIRLAR.length) return;
  /* Mevcut listeye EKLENİYOR, listenin yerine geçmiyor: elle
     girilmiş satırlar durmaya devam etsin. */
  KX_SATIRLAR.forEach(k => HEDEFLER.push({
    hedef_tip: k.hedef_tip, cins: k.cins, ozellik: k.ozellik,
    boy: k.boy, yukseklik: k.yukseklik, kalinlik: k.kalinlik,
    adet: k.adet, kasa_ici_adet: k.kasa_ici_adet, _m2: k._m2
  }));
  const n = KX_SATIRLAR.length;
  kesimExcelKapat();
  hedefListeCiz(); ozetHesapla();
  bildir(`${n} satır listeye eklendi`);
}

function hedefListeCiz() {
'''),
    ('templates/kesim.html', 'B1 · templates/kesim.html blok 6',
     r'''      <span class="m">${h._m2.toLocaleString('tr-TR')} m²</span>
''',
     r'''      <span class="m">${h._m2.toLocaleString('tr-TR', {maximumFractionDigits: 2})} m²</span>
'''),
    ('templates/kesim.html', 'B1 · templates/kesim.html blok 7',
     r'''  document.getElementById('ozCikan').textContent = cikanM2.toLocaleString('tr-TR') + ' m²';
''',
     r'''  /* B1: iki basamak. Excel'den gelen satırlarda m² uzun ondalık
     çıkıyor ve önizleme (2 basamak) ile liste farklı sayı
     gösteriyordu — aynı şeyin iki yerde farklı görünmesi bu
     projede en kötü hata biçimi olarak geçiyor. */
  document.getElementById('ozCikan').textContent =
    cikanM2.toLocaleString('tr-TR', {maximumFractionDigits: 2}) + ' m²';
'''),
    ('tests/test_kritik.py', 'B1 · tests/test_kritik.py blok 1',
     r'''        assert p.mense == 'ITALYA', p.mense
''',
     r'''        assert p.mense == 'ITALYA', p.mense


# ══════════════════════════════════════════════════════════════════════
#  B1 · KESİM'E EXCEL'DEN HEDEF SATIRI + ORTAK EŞLEŞTİRME PARÇASI
# ══════════════════════════════════════════════════════════════════════

def test_b1_excel_ortak_parcasi_tek_kopya():
    """B1: sayı ayrıştırma ve birleştirilmiş hücre doldurması TEK yerde.

    İkisi de ÖLÇÜLMÜŞ hata düzeltmesi taşıyor (BS3: "1,234.56" bin kat
    küçük okunuyordu · X1: birleştirilmiş hücrede 6 satırlık listeden
    1 kayıt çıkıyordu). İkinci bir kopya, düzeltmenin yalnız birinde
    yaşamasıyla biterdi — bu projede MF4 ve YP3'te tam bu oldu."""
    import io as _io, os as _os
    yol = _os.path.join('static', 'js', 'excel_ortak.js')
    assert _os.path.exists(yol), 'ortak dosya yok'
    ortak = _io.open(yol, encoding='utf-8').read()
    for parca in ('function sayi', 'function tahmin', 'function satirlariCikar',
                  'function dosyaAnaliz'):
        assert parca in ortak, parca

    stok = _io.open('templates/stok.html', encoding='utf-8').read()
    kesim = _io.open('templates/kesim.html', encoding='utf-8').read()
    # İki şablon da ORTAK dosyayı yüklüyor
    for sablon, ad in ((stok, 'stok'), (kesim, 'kesim')):
        assert "filename='js/excel_ortak.js'" in sablon, ad
        assert 'ExcelOrtak.' in sablon, ad
    # Ayrıştırıcı şablonların İÇİNDE yeniden yazılmamış
    for sablon, ad in ((stok, 'stok'), (kesim, 'kesim')):
        assert 'lastIndexOf(\',\')' not in sablon, (ad, 'sayı ayrıştırıcı kopyalanmış')


def test_b1_kesimde_excel_yukleme_var():
    """B1: Kesim ekranında Excel'den hedef satırı girişi."""
    import io as _io
    h = _io.open('templates/kesim.html', encoding='utf-8').read()
    assert 'id="excelModal"' in h
    assert 'function kesimExcelAc' in h
    assert 'function kesimExcelUygula' in h
    assert "onclick=\"kesimExcelAc()\"" in h
    # Satırlar listeye EKLENİYOR, listenin yerine geçmiyor
    assert 'HEDEFLER.push(' in h
    # Hedef tipi kesim YÖNÜNDEN geliyor, Excel'den değil
    assert "yon.endsWith('EBATLI') ? 'EBATLI' : 'PLAKA'" in h


def test_b1_sayi_ayristirici_davranisi():
    """B1: ortak ayrıştırıcı GERÇEKTEN çalışıyor mu — node ile koşulur.

    `js_denetim` yalnızca AYRIŞTIRILABİLİRLİK bakıyor; sözdizimi
    geçerli ama çalışma anında patlayan kod ondan geçer (bu yamada
    bir kez oldu: koda kazara düşen bir kelime `node --check`ten
    geçti). Burada işlevler çağrılıyor."""
    import json as _json, os as _os, shutil as _shutil, subprocess as _sp
    node = _shutil.which('node') or '/opt/node22/bin/node'
    if not _os.path.exists(node):
        import pytest as _pytest
        _pytest.skip('node yok')
    # NOT: üç tırnak ÇİFT olmalı — yama paketleyicisi blokları
    # ham tek-tırnaklı blok hâlinde sarıyor; aynısını burada
    # kullanmak o bloğu ortasından bölerdi.
    betik = r"""
const fs = require('fs'), vm = require('vm');
const kod = fs.readFileSync('static/js/excel_ortak.js', 'utf8');
const kum = { window: {}, FormData: class {}, fetch: async () => ({}) };
kum.globalThis = kum; vm.createContext(kum); vm.runInContext(kod, kum);
const E = kum.window.ExcelOrtak;
const sonuc = {
  tr: E.sayi('1.234,56'), en: E.sayi('1,234.56'), sade: E.sayi('2,4'),
  bos: E.sayi(''), metin: E.sayi('abc'), eksi: E.sayi('-3,5'),
  tahminBoy: E.tahmin('boy', ['Blok no','cins','uzunluk','Yükseklik']),
  tahminEn: E.tahmin('en', ['Genişlik','En']),
};
const c = E.satirlariCikar(
  [['CEPPO','K6461','298','8'], ['','','297','4'], ['','','297','7']],
  [['cins','Cins',false],['blok_no','Blok',false],['boy','Boy',true],['adet','Adet',false]],
  {cins:0, blok_no:1, boy:2, adet:3},
  {sayisal:['boy','adet'], doldurulacak:['cins','blok_no']});
sonuc.doldurulan = c.dolduruldu;
sonuc.cinsler = [...new Set(c.kayitlar.map(k => k.cins))];
sonuc.satirNo = c.kayitlar.map(k => k._satir);
console.log(JSON.stringify(sonuc));
"""
    r = _sp.run([node, '-e', betik], capture_output=True, text=True, cwd='.')
    assert r.returncode == 0, r.stderr[:400]
    d = _json.loads(r.stdout.strip().splitlines()[-1])

    # BS3: iki ayırıcı biçimi de doğru
    assert d['tr'] == 1234.56, d['tr']
    assert d['en'] == 1234.56, d['en']
    assert d['sade'] == 2.4 and d['eksi'] == -3.5
    assert d['bos'] == 0 and d['metin'] == 0
    # Başlık tahmini: "uzunluk" boya gider
    assert d['tahminBoy'] == 2, d['tahminBoy']
    # "Genişlik" içinde "en" geçiyor ama TAM eşleşen "En" kazanmalı
    assert d['tahminEn'] == 1, d['tahminEn']
    # X1: birleştirilmiş hücre üç satıra da yayıldı
    assert d['cinsler'] == ['CEPPO'], d['cinsler']
    assert d['doldurulan'] == 2, d['doldurulan']
    assert d['satirNo'] == [2, 3, 4], d['satirNo']
'''),
]

# ══════════════════════════════════════════════════════════════════════
#  TAM DOSYA · static/js/excel_ortak.js
#
#  Parça değil tam dosya; iç içe tırnak yığını üretmesin diye
#  base64. Uygulandıktan sonra diskteki dosya baştan sona
#  yorumlu, okunur Python — önce okumak istersen:
#      python3 yama_kf.py --yaz-gecici
# ══════════════════════════════════════════════════════════════════════
TAM_ICERIK = {
    'static/js/excel_ortak.js': (
        'Lyog4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCiAg'
        'IEVYQ0VMIEXFnkxFxZ5UxLBSTUUg4oCUIE9SVEFLIFBBUsOHQSAgwrcgIEIxCiAgIOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkAoKICAgxLBr'
        'aSBla3JhbiBFeGNlbCdkZW4gc2F0xLFyIGFsxLF5b3I6CgogICAgICAgRGVwbyDihpIg'
        'U3RvayAgIOKGkiBUb3BsdSDEsMOnZSBBa3RhciAgICAgIChzYXTEsW4gYWzEsW5hbi/D'
        'vHJldGlsZW4gc3RvaykKICAgICAgIERlcG8g4oaSIEtlc2ltICDihpIgRXhjZWwnZGVu'
        'IHnDvGtsZSAgICAgIChrZXNpbSBoZWRlZiBzYXTEsXJsYXLEsSkKCiAgIMSwa2lzaW5p'
        'biBFS1JBTkkgZmFya2zEsSAoYmlyaSBmaXlhdC9mYXR1cmEgc29ydXlvciwgw7Z0ZWtp'
        'CiAgIHNvcm11eW9yKSBhbWEgQUxUSU5EQUvEsCBpxZ9sZXIgYXluxLE6IGJhxZ9sxLFr'
        'dGFuIGFsYW4gdGFobWluaSwKICAgc2F5xLEgYXlyxLHFn3TEsXJtYSwgYmlybGXFn3Rp'
        'cmlsbWnFnyBow7xjcmUgZG9sZHVybWFzxLEuIEJ1IGRvc3lhIG8KICAgb3J0YWsga8Sx'
        'c23EsSB0dXR1eW9yLgoKICAgTkVERU4gS09QWUFMQU1BRElNOiBidSBwcm9qZWRlIGlr'
        'aXoga29weWFsYXIgaGVwIGF5csSxxZ90xLEg4oCUCiAgIE1GNCd0ZSBpa2kgYHllZGVr'
        'R292ZGVgLCBZUDMndGUgaWtpIGZpcm1hIGZvcm11LiBCdXJhZGFraSBpa2kKICAgYWxn'
        'b3JpdG1hIGRhIMOWTMOHw5xMTcOcxZ4gaGF0YSBkw7x6ZWx0bWVsZXJpIHRhxZ/EsXlv'
        'ciAoQlMzIHNhecSxCiAgIGF5csSxxZ90xLFybWEsIFgxIGJpcmxlxZ90aXJpbG1pxZ8g'
        'aMO8Y3JlKS4gxLBraW5jaSBrb3B5YSwgbwogICBkw7x6ZWx0bWVsZXJpbiB5YWxuxLF6'
        'IGJpcmluZGUgeWHFn2FtYXPEsXlsYSBiaXRlcmRpLgoKICAgR2xvYmFsIGBFeGNlbE9y'
        'dGFrYCBvbGFyYWsgZHVydXlvcjsgbW9kw7xsIHNpc3RlbWkgeW9rLCDFn2FibG9ubGFy'
        'CiAgIGTDvHogPHNjcmlwdD4gaWxlIHnDvGtsw7x5b3IuCiAgIOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkCAqLwp3aW5kb3cuRXhjZWxPcnRh'
        'ayA9IChmdW5jdGlvbiAoKSB7CiAgJ3VzZSBzdHJpY3QnOwoKICAvKiBCYcWfbMSxayBh'
        'ZMSxbmRhbiBhbGFuIHRhaG1pbmkgacOnaW4gaXB1w6dsYXLEsS4gU8O8dHVuIGFkbGFy'
        'xLEKICAgICB0ZWRhcmlrw6dpZGVuIHRlZGFyaWvDp2l5ZSBkZcSfacWfaXlvcjsgbGlz'
        'dGUgaWtpc2luaW4gZGUgacWfaW5lCiAgICAgeWFyxLF5b3IuICovCiAgdmFyIElQVUNV'
        'ID0gewogICAgY2luczogWydjaW5zJywgJ3VydW4nLCAnw7xyw7xuJywgJ21hbHplbWUn'
        'LCAndGFzJywgJ3RhxZ8nLCAnbWF0ZXJpYWwnLCAndHlwZSddLAogICAgYmxva19ubzog'
        'WydibG9rJywgJ2Jsb2NrJywgJ2thc2EnLCAncmVmJywgJ3BhcnRpJ10sCiAgICBib3k6'
        'IFsnYm95JywgJ3V6dW5sdWsnLCAnbGVuZ3RoJywgJ2VuMSddLAogICAgeXVrc2VrbGlr'
        'OiBbJ3l1a3Nla2xpaycsICd5w7xrc2VrbGlrJywgJ3l1aycsICdnZW5pc2xpaycsICdn'
        'ZW5pxZ9saWsnLCAnd2lkdGgnLCAnaGVpZ2h0J10sCiAgICBlbjogWydlbicsICdkZXJp'
        'bmxpaycsICdkZXB0aCddLAogICAga2FsaW5saWs6IFsna2FsaW5saWsnLCAna2FsxLFu'
        'bMSxaycsICdrYWwnLCAndGhpY2tuZXNzJ10sCiAgICBvemVsbGlrOiBbJ3l1emV5Jywg'
        'J3nDvHpleScsICdvemVsbGlrJywgJ8O2emVsbGlrJywgJ2ZpbmlzaCcsICdzdXJmYWNl'
        'J10sCiAgICBmaXlhdDogWydmaXlhdCcsICdiaXJpbScsICdwcmljZScsICd0dXRhcics'
        'ICd1Y3JldCcsICfDvGNyZXQnXSwKICAgIGFkZXQ6IFsnYWRldCcsICdtaWt0YXInLCAn'
        'cXR5JywgJ3F1YW50aXR5J10sCiAgICB0b25hajogWyd0b24nLCAndG9uYWonLCAnYWdp'
        'cmxpaycsICdhxJ/EsXJsxLFrJywgJ3dlaWdodCddLAogICAga2FzYV9hZGVkaTogWydr'
        'YXNhIGFkZWRpJywgJ2thc2Egc2F5aScsICdwYWtldCddLAogICAga2FzYV9pY2lfYWRl'
        'dDogWydrYXNhIGljaScsICdrYXNhIGnDp2knLCAnaWNpIGFkZXQnLCAnacOnaSBhZGV0'
        'J10sCiAgICBhY2lrbGFtYTogWydhY2lrbGFtYScsICdhw6fEsWtsYW1hJywgJ25vdCcs'
        'ICdkZXNjcmlwdGlvbicsICdkZXNjJ10KICB9OwoKICAvKiDilIDilIAgU0FZSSBBWVJJ'
        'xZ5USVJNQSAoQlMzKSDilIDilIAKICAgICBIZW0gIjEuMjM0LDU2IiAoVFIpIGhlbSAi'
        'MSwyMzQuNTYiIChFTikgZG/En3J1IG9rdW51ci4KICAgICBFc2tpZGVuIHlhbG7EsXpj'
        'YSDEsExLIHZpcmfDvGwgbm9rdGF5YSDDp2V2cmlsaXlvcmR1OgogICAgICIxLDIzNC41'
        'NiIg4oaSICIxLjIzNC41NiIg4oaSIDEuMjM0IChiaW4ga2F0IGvDvMOnw7xrKS4gxLBr'
        'aXNpIGJpcmRlbgogICAgIHZhcnNhIFNPTlVOQ1VTVSBvbmRhbMSxayBhecSxcsSxY8Sx'
        'ZMSxci4gKi8KICBmdW5jdGlvbiBzYXlpKHYpIHsKICAgIGlmICh2ID09PSAnJyB8fCB2'
        'ID09PSBudWxsIHx8IHYgPT09IHVuZGVmaW5lZCkgcmV0dXJuIDA7CiAgICBpZiAodHlw'
        'ZW9mIHYgPT09ICdudW1iZXInKSByZXR1cm4gaXNGaW5pdGUodikgPyB2IDogMDsKICAg'
        'IHZhciB0ID0gU3RyaW5nKHYpLnJlcGxhY2UoL1xzL2csICcnKS5yZXBsYWNlKC9bXlxk'
        'LixcLV0vZywgJycpOwogICAgdmFyIHN2ID0gdC5sYXN0SW5kZXhPZignLCcpLCBzbiA9'
        'IHQubGFzdEluZGV4T2YoJy4nKTsKICAgIGlmIChzdiA+PSAwICYmIHNuID49IDApIHsK'
        'ICAgICAgdCA9IHN2ID4gc24gPyB0LnJlcGxhY2UoL1wuL2csICcnKS5yZXBsYWNlKCcs'
        'JywgJy4nKSA6IHQucmVwbGFjZSgvLC9nLCAnJyk7CiAgICB9IGVsc2UgaWYgKHN2ID49'
        'IDApIHsKICAgICAgdCA9IHQucmVwbGFjZSgnLCcsICcuJyk7CiAgICB9CiAgICB2YXIg'
        'biA9IHBhcnNlRmxvYXQodCk7CiAgICByZXR1cm4gaXNGaW5pdGUobikgPyBuIDogMDsK'
        'ICB9CgogIGZ1bmN0aW9uIHNhZGVsZXN0aXIodCkgewogICAgcmV0dXJuIFN0cmluZyh0'
        'IHx8ICcnKS50b0xvY2FsZUxvd2VyQ2FzZSgndHInKQogICAgICAucmVwbGFjZSgvW8Sx'
        'xLBdL2csICdpJykucmVwbGFjZSgvW8WfxZ5dL2csICdzJykucmVwbGFjZSgvW8SfxJ5d'
        'L2csICdnJykKICAgICAgLnJlcGxhY2UoL1vDvMOcXS9nLCAndScpLnJlcGxhY2UoL1vD'
        'tsOWXS9nLCAnbycpLnJlcGxhY2UoL1vDp8OHXS9nLCAnYycpLnRyaW0oKTsKICB9Cgog'
        'IC8qIOKUgOKUgCBCQcWeTElLIOKGkiBBTEFOIFRBSE3EsE7EsCDilIDilIAKICAgICDD'
        'nMOnIGHFn2FtYWzEsTogw7ZuY2UgdGFtIGXFn2xlxZ9tZSwgc29ucmEgYmHFn3RhbiBl'
        'xZ9sZcWfbWUsIGVuIHNvbgogICAgIGnDp2VybWUuIFRlayBhxZ9hbWFkYSB5YXDEsWxz'
        'YXlkxLEgIkdlbmnFn2xpayIgYmHFn2zEscSfxLEgacOnaW5kZSAiZW4iCiAgICAgZ2XD'
        'p3RpxJ9pIGnDp2luIEVuIGFsYW7EsW5hIHlhbmzEscWfIGXFn2xlxZ9pcmRpLiAqLwog'
        'IGZ1bmN0aW9uIHRhaG1pbihhbGFuS29kLCBiYXNsaWtsYXIsIGlwdWN1SGFyaXRhc2kp'
        'IHsKICAgIHZhciBpcHVjbGFyaSA9IChpcHVjdUhhcml0YXNpIHx8IElQVUNVKVthbGFu'
        'S29kXSB8fCBbXTsKICAgIHZhciBzYWRlQmFzID0gKGJhc2xpa2xhciB8fCBbXSkubWFw'
        'KHNhZGVsZXN0aXIpOwogICAgdmFyIHNhZGVJcCA9IGlwdWNsYXJpLm1hcChzYWRlbGVz'
        'dGlyKTsKICAgIHZhciBrdXJhbGxhciA9IFsndGFtJywgJ2JhcycsICdpY2VyaWsnXTsK'
        'ICAgIGZvciAodmFyIGsgPSAwOyBrIDwga3VyYWxsYXIubGVuZ3RoOyBrKyspIHsKICAg'
        'ICAgZm9yICh2YXIgaSA9IDA7IGkgPCBzYWRlQmFzLmxlbmd0aDsgaSsrKSB7CiAgICAg'
        'ICAgdmFyIGIgPSBzYWRlQmFzW2ldOwogICAgICAgIGlmICghYikgY29udGludWU7CiAg'
        'ICAgICAgZm9yICh2YXIgaiA9IDA7IGogPCBzYWRlSXAubGVuZ3RoOyBqKyspIHsKICAg'
        'ICAgICAgIHZhciBzID0gc2FkZUlwW2pdOwogICAgICAgICAgaWYgKCFzKSBjb250aW51'
        'ZTsKICAgICAgICAgIGlmIChrdXJhbGxhcltrXSA9PT0gJ3RhbScgJiYgYiA9PT0gcykg'
        'cmV0dXJuIGk7CiAgICAgICAgICBpZiAoa3VyYWxsYXJba10gPT09ICdiYXMnICYmIGIu'
        'aW5kZXhPZihzKSA9PT0gMCkgcmV0dXJuIGk7CiAgICAgICAgICBpZiAoa3VyYWxsYXJb'
        'a10gPT09ICdpY2VyaWsnICYmIGIuaW5kZXhPZihzKSA+PSAwKSByZXR1cm4gaTsKICAg'
        'ICAgICB9CiAgICAgIH0KICAgIH0KICAgIHJldHVybiAtMTsKICB9CgogIGZ1bmN0aW9u'
        'IGthY2FyWWVyZWwocykgewogICAgcmV0dXJuIFN0cmluZyhzID09PSBudWxsIHx8IHMg'
        'PT09IHVuZGVmaW5lZCA/ICcnIDogcykKICAgICAgLnJlcGxhY2UoLyYvZywgJyZhbXA7'
        'JykucmVwbGFjZSgvPC9nLCAnJmx0OycpCiAgICAgIC5yZXBsYWNlKC8+L2csICcmZ3Q7'
        'JykucmVwbGFjZSgvIi9nLCAnJnF1b3Q7Jyk7CiAgfQoKICAvKiDilIDilIAgRcWeTEXF'
        'nlTEsFJNRSBLVVRVTEFSSSDilIDilIAKICAgICBgYWxhbmxhcmA6IFtba29kLCBldGlr'
        'ZXQsIHpvcnVubHVdLCDigKZdCiAgICAgU2XDp2ltbGVyIGBkYXRhLWFsYW5gIGlsZSBp'
        'xZ9hcmV0bGVuaXlvcjsgYGhhcml0YU9rdWAgb25sYXLEsSBva3VyLiAqLwogIGZ1bmN0'
        'aW9uIGVzbGVzdGlybWVDaXooa29rLCBhbGFubGFyLCBiYXNsaWtsYXIsIGRlZ2lzaW5j'
        'ZSkgewogICAgaWYgKCFrb2spIHJldHVybjsKICAgIGtvay5pbm5lckhUTUwgPSBhbGFu'
        'bGFyLm1hcChmdW5jdGlvbiAoYSkgewogICAgICB2YXIga29kID0gYVswXSwgZXRpa2V0'
        'ID0gYVsxXSwgem9ydW5sdSA9IGFbMl07CiAgICAgIHZhciB0ID0gdGFobWluKGtvZCwg'
        'YmFzbGlrbGFyKTsKICAgICAgdmFyIHNlY2VuZWtsZXIgPSBbJzxvcHRpb24gdmFsdWU9'
        'Ii0xIj7igJQgZcWfbGXFn3Rpcm1lIOKAlDwvb3B0aW9uPiddCiAgICAgICAgLmNvbmNh'
        'dCgoYmFzbGlrbGFyIHx8IFtdKS5tYXAoZnVuY3Rpb24gKGIsIGkpIHsKICAgICAgICAg'
        'IHJldHVybiAnPG9wdGlvbiB2YWx1ZT0iJyArIGkgKyAnIicgKyAoaSA9PT0gdCA/ICcg'
        'c2VsZWN0ZWQnIDogJycpICsKICAgICAgICAgICAgICAgICAnPicgKyBrYWNhclllcmVs'
        'KGIpICsgJzwvb3B0aW9uPic7CiAgICAgICAgfSkpLmpvaW4oJycpOwogICAgICByZXR1'
        'cm4gJzxkaXYgY2xhc3M9InRwLWNpZnQiPjxsYWJlbD4nICsga2FjYXJZZXJlbChldGlr'
        'ZXQpICsKICAgICAgICAoem9ydW5sdSA/ICcgPHNwYW4gc3R5bGU9ImNvbG9yOnZhcigt'
        'LWtpcm1pemkpIj4qPC9zcGFuPicgOiAnJykgKwogICAgICAgICc8L2xhYmVsPjxzZWxl'
        'Y3QgZGF0YS1hbGFuPSInICsga29kICsgJyI+JyArIHNlY2VuZWtsZXIgKyAnPC9zZWxl'
        'Y3Q+PC9kaXY+JzsKICAgIH0pLmpvaW4oJycpOwogICAgaWYgKGRlZ2lzaW5jZSkgewog'
        'ICAgICBrb2sucXVlcnlTZWxlY3RvckFsbCgnc2VsZWN0JykuZm9yRWFjaChmdW5jdGlv'
        'biAocykgeyBzLm9uY2hhbmdlID0gZGVnaXNpbmNlOyB9KTsKICAgIH0KICB9CgogIGZ1'
        'bmN0aW9uIGhhcml0YU9rdShrb2spIHsKICAgIHZhciBoYXJpdGEgPSB7fTsKICAgIGlm'
        'ICgha29rKSByZXR1cm4gaGFyaXRhOwogICAga29rLnF1ZXJ5U2VsZWN0b3JBbGwoJ3Nl'
        'bGVjdCcpLmZvckVhY2goZnVuY3Rpb24gKHMpIHsKICAgICAgdmFyIGkgPSBwYXJzZUlu'
        'dChzLnZhbHVlLCAxMCk7CiAgICAgIGlmIChpID49IDApIGhhcml0YVtzLmRhdGFzZXQu'
        'YWxhbl0gPSBpOwogICAgfSk7CiAgICByZXR1cm4gaGFyaXRhOwogIH0KCiAgLyog4pSA'
        '4pSAIFNBVElSTEFSSSBLQVlEQSDDh0VWxLBSIOKUgOKUgAogICAgIHNlY2VuZWsuc2F5'
        'aXNhbCAgICAgIDogc2F5xLF5YSDDp2V2cmlsZWNlayBhbGFuIGtvZGxhcsSxCiAgICAg'
        'c2VjZW5lay5kb2xkdXJ1bGFjYWsgOiBiaXJsZcWfdGlyaWxtacWfIGjDvGNyZSBkb2xk'
        'dXJtYXPEsSB5YXDEsWxhY2FrCiAgICAgICAgICAgICAgICAgICAgICAgICAgICBhbGFu'
        'IGtvZGxhcsSxCgogICAgIOKUgOKUgCBYMSDCtyBCxLBSTEXFnlTEsFLEsExNxLDFniBI'
        'w5xDUkUgKGHFn2HEn8SxIGRvxJ9ydSBkb2xkdXJtYSkg4pSA4pSACiAgICAgw4dla2kg'
        'bGlzdGVsZXJpbmRlIGJsb2sgbm8gdmUgbWFsemVtZSBhZMSxIGJpcmxlxZ90aXJpbG1p'
        'xZ8gaMO8Y3JlZGUKICAgICB5YXrEsWzEsXI6IHRlayBibG9rLCBiaXLDp29rIHNhdMSx'
        'ci4gRXhjZWwgYnUgZGXEn2VyaSBZQUxOSVpDQSBpbGsKICAgICBzYXTEsXJhIGtveWFy'
        'LCBrYWxhbmxhciBib8WfIGdlbGlyIHZlICJjaW5zIGJvxZ8iIGRpeWUgYXRsYW7EsXJk'
        'xLEg4oCUCiAgICAgNiBzYXTEsXJsxLFrIGxpc3RlZGVuIDEga2F5xLF0IMOnxLFrxLF5'
        'b3JkdS4KCiAgICAgw5ZMw4fDnCB2ZSBBREVUIGRvbGR1cnVsbWF6OiBvbmxhciBoZXIg'
        'c2F0xLFyZGEgZmFya2zEsWTEsXIsIGJvxZ8KICAgICBvbG1hbGFyxLEgZ2Vyw6dlayBi'
        'aXIgaGF0YWTEsXIuIMOHYcSfxLFyYW4gaGFuZ2kgYWxhbmxhcsSxbgogICAgIGRvbGR1'
        'cnVsYWNhxJ/EsW7EsSBrZW5kaXNpIHPDtnlsw7x5b3IuICovCiAgZnVuY3Rpb24gc2F0'
        'aXJsYXJpQ2lrYXIoc2F0aXJsYXIsIGFsYW5sYXIsIGhhcml0YSwgc2VjZW5laykgewog'
        'ICAgc2VjZW5layA9IHNlY2VuZWsgfHwge307CiAgICB2YXIgc2F5aXNhbCA9IHNlY2Vu'
        'ZWsuc2F5aXNhbCB8fCBbXTsKICAgIHZhciBkb2xkdXJ1bGFjYWsgPSBzZWNlbmVrLmRv'
        'bGR1cnVsYWNhayB8fCBbXTsKICAgIHZhciBvbmNla2lEZWdlciA9IHt9OwogICAgdmFy'
        'IGtheWl0bGFyID0gW10sIGRvbGR1cnVsZHUgPSAwOwoKICAgIChzYXRpcmxhciB8fCBb'
        'XSkuZm9yRWFjaChmdW5jdGlvbiAoc2F0aXIsIGlkeCkgewogICAgICB2YXIga2F5aXQg'
        'PSB7IF9zYXRpcjogaWR4ICsgMiB9OyAgIC8vICsyOiBiYcWfbMSxayBzYXTEsXLEsSAr'
        'IDEgdGFiYW5sxLEKICAgICAgYWxhbmxhci5mb3JFYWNoKGZ1bmN0aW9uIChhKSB7CiAg'
        'ICAgICAgdmFyIGtvZCA9IGFbMF07CiAgICAgICAgdmFyIGhhbSA9IChrb2QgaW4gaGFy'
        'aXRhKSA/IHNhdGlyW2hhcml0YVtrb2RdXSA6ICcnOwogICAgICAgIGtheWl0W2tvZF0g'
        'PSAoc2F5aXNhbC5pbmRleE9mKGtvZCkgPj0gMCkKICAgICAgICAgID8gc2F5aShoYW0p'
        'CiAgICAgICAgICA6IFN0cmluZyhoYW0gPT09IG51bGwgfHwgaGFtID09PSB1bmRlZmlu'
        'ZWQgPyAnJyA6IGhhbSkudHJpbSgpOwogICAgICB9KTsKCiAgICAgIHZhciBidVNhdGly'
        'ID0gZmFsc2U7CiAgICAgIGRvbGR1cnVsYWNhay5mb3JFYWNoKGZ1bmN0aW9uIChrb2Qp'
        'IHsKICAgICAgICB2YXIgYm9zID0gKHNheWlzYWwuaW5kZXhPZihrb2QpID49IDApID8g'
        'IShrYXlpdFtrb2RdID4gMCkgOiAha2F5aXRba29kXTsKICAgICAgICBpZiAoYm9zICYm'
        'IG9uY2VraURlZ2VyW2tvZF0gIT09IHVuZGVmaW5lZCAmJiBvbmNla2lEZWdlcltrb2Rd'
        'ICE9PSAnJykgewogICAgICAgICAga2F5aXRba29kXSA9IG9uY2VraURlZ2VyW2tvZF07'
        'CiAgICAgICAgICBidVNhdGlyID0gdHJ1ZTsKICAgICAgICB9IGVsc2UgaWYgKCFib3Mp'
        'IHsKICAgICAgICAgIG9uY2VraURlZ2VyW2tvZF0gPSBrYXlpdFtrb2RdOwogICAgICAg'
        'IH0KICAgICAgfSk7CiAgICAgIGlmIChidVNhdGlyKSBkb2xkdXJ1bGR1Kys7CiAgICAg'
        'IGtheWl0bGFyLnB1c2goa2F5aXQpOwogICAgfSk7CiAgICByZXR1cm4geyBrYXlpdGxh'
        'cjoga2F5aXRsYXIsIGRvbGR1cnVsZHU6IGRvbGR1cnVsZHUgfTsKICB9CgogIC8qIERv'
        'c3lhecSxIHN1bnVjdXlhIMOnw7Z6ZMO8csO8ci4gQXlyxLHFn3TEsXJtYSBTVU5VQ1VE'
        'QSAob3BlbnB5eGwpOwogICAgIHRhcmF5xLFjxLF5YSB4bHN4IGvDvHTDvHBoYW5lc2kg'
        'ecO8a2xlbm1peW9yLiAqLwogIGFzeW5jIGZ1bmN0aW9uIGRvc3lhQW5hbGl6KGRvc3lh'
        'KSB7CiAgICB2YXIgZmQgPSBuZXcgRm9ybURhdGEoKTsKICAgIGZkLmFwcGVuZCgnZG9z'
        'eWEnLCBkb3N5YSk7CiAgICAvKiBTMTogYXBpKCkgc2FybWFsYXnEsWPEsXPEsSBrdWxs'
        'YW7EsWxtxLF5b3IgKG11bHRpcGFydCB5w7xrbGVtZSksCiAgICAgICBDU1JGIGJhxZ9s'
        'xLHEn8SxIEVMTEUgZWtsZW5tZWxpLiAqLwogICAgdmFyIHIgPSBhd2FpdCBmZXRjaCgn'
        'L2FwaS92Mi9leGNlbC9hbmFsaXonLCB7CiAgICAgIG1ldGhvZDogJ1BPU1QnLCBib2R5'
        'OiBmZCwKICAgICAgaGVhZGVyczogeyAnWC1DU1JGLVRva2VuJzogd2luZG93LkNTUkZf'
        'VE9LRU4gfQogICAgfSk7CiAgICB2YXIgZCA9IGF3YWl0IHIuanNvbigpOwogICAgaWYg'
        'KCFyLm9rIHx8ICFkLm9rKSB0aHJvdyBuZXcgRXJyb3IoKGQgJiYgZC5tZXNhaikgfHwg'
        'J0Rvc3lhIG9rdW5hbWFkxLEuJyk7CiAgICByZXR1cm4gZDsKICB9CgogIHJldHVybiB7'
        'CiAgICBJUFVDVTogSVBVQ1UsCiAgICBzYXlpOiBzYXlpLAogICAgdGFobWluOiB0YWht'
        'aW4sCiAgICBlc2xlc3Rpcm1lQ2l6OiBlc2xlc3Rpcm1lQ2l6LAogICAgaGFyaXRhT2t1'
        'OiBoYXJpdGFPa3UsCiAgICBzYXRpcmxhcmlDaWthcjogc2F0aXJsYXJpQ2lrYXIsCiAg'
        'ICBkb3N5YUFuYWxpejogZG9zeWFBbmFsaXoKICB9Owp9KSgpOwo='
    ),
}


def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA B1 — KESIMDE EXCEL ILE HEDEF SATIRI')
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
        print('    python3 yama_b1.py            # rapor')
        print('    python3 yama_b1.py --uygula')
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
        print('  ⊙ Yama B1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_b1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_b1'
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
    print('  ══ SIRA ONEMLI ══')
    print()
    print('    1) sudo systemctl restart milestone-erp')
    print()
    print('    2) Tarayicida Ctrl+F5 — YENI bir .js dosyasi geliyor.')
    print('       Onbellek tazelenmezse "ExcelOrtak is not defined".')
    print()
    print('    3) venv/bin/python -m pytest tests/test_kritik.py -q')
    print()
    print('  BAKILACAK YERLER')
    print('    · Depo -> Kesim -> Yeni Kesim -> Excel ile yukleme')
    print('    · Depo -> Stok -> Toplu Ice Aktar: davranis AYNI')
    print('      olmali (ortak parcaya baglandi).')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

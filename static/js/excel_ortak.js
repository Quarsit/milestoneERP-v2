/* ══════════════════════════════════════════════════════════════════
   EXCEL EŞLEŞTİRME — ORTAK PARÇA  ·  B1
   ══════════════════════════════════════════════════════════════════

   İki ekran Excel'den satır alıyor:

       Depo → Stok   → Toplu İçe Aktar      (satın alınan/üretilen stok)
       Depo → Kesim  → Excel'den yükle      (kesim hedef satırları)

   İkisinin EKRANI farklı (biri fiyat/fatura soruyor, öteki
   sormuyor) ama ALTINDAKİ işler aynı: başlıktan alan tahmini,
   sayı ayrıştırma, birleştirilmiş hücre doldurması. Bu dosya o
   ortak kısmı tutuyor.

   NEDEN KOPYALAMADIM: bu projede ikiz kopyalar hep ayrıştı —
   MF4'te iki `yedekGovde`, YP3'te iki firma formu. Buradaki iki
   algoritma da ÖLÇÜLMÜŞ hata düzeltmeleri taşıyor (BS3 sayı
   ayrıştırma, X1 birleştirilmiş hücre). İkinci kopya, o
   düzeltmelerin yalnız birinde yaşamasıyla biterdi.

   Global `ExcelOrtak` olarak duruyor; modül sistemi yok, şablonlar
   düz <script> ile yüklüyor.
   ══════════════════════════════════════════════════════════════════ */
window.ExcelOrtak = (function () {
  'use strict';

  /* Başlık adından alan tahmini için ipuçları. Sütun adları
     tedarikçiden tedarikçiye değişiyor; liste ikisinin de işine
     yarıyor. */
  var IPUCU = {
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
    aciklama: ['aciklama', 'açıklama', 'not', 'description', 'desc']
  };

  /* ── SAYI AYRIŞTIRMA (BS3) ──
     Hem "1.234,56" (TR) hem "1,234.56" (EN) doğru okunur.
     Eskiden yalnızca İLK virgül noktaya çevriliyordu:
     "1,234.56" → "1.234.56" → 1.234 (bin kat küçük). İkisi birden
     varsa SONUNCUSU ondalık ayırıcıdır. */
  function sayi(v) {
    if (v === '' || v === null || v === undefined) return 0;
    if (typeof v === 'number') return isFinite(v) ? v : 0;
    var t = String(v).replace(/\s/g, '').replace(/[^\d.,\-]/g, '');
    var sv = t.lastIndexOf(','), sn = t.lastIndexOf('.');
    if (sv >= 0 && sn >= 0) {
      t = sv > sn ? t.replace(/\./g, '').replace(',', '.') : t.replace(/,/g, '');
    } else if (sv >= 0) {
      t = t.replace(',', '.');
    }
    var n = parseFloat(t);
    return isFinite(n) ? n : 0;
  }

  function sadelestir(t) {
    return String(t || '').toLocaleLowerCase('tr')
      .replace(/[ıİ]/g, 'i').replace(/[şŞ]/g, 's').replace(/[ğĞ]/g, 'g')
      .replace(/[üÜ]/g, 'u').replace(/[öÖ]/g, 'o').replace(/[çÇ]/g, 'c').trim();
  }

  /* ── BAŞLIK → ALAN TAHMİNİ ──
     Üç aşamalı: önce tam eşleşme, sonra baştan eşleşme, en son
     içerme. Tek aşamada yapılsaydı "Genişlik" başlığı içinde "en"
     geçtiği için En alanına yanlış eşleşirdi. */
  function tahmin(alanKod, basliklar, ipucuHaritasi) {
    var ipuclari = (ipucuHaritasi || IPUCU)[alanKod] || [];
    var sadeBas = (basliklar || []).map(sadelestir);
    var sadeIp = ipuclari.map(sadelestir);
    var kurallar = ['tam', 'bas', 'icerik'];
    for (var k = 0; k < kurallar.length; k++) {
      for (var i = 0; i < sadeBas.length; i++) {
        var b = sadeBas[i];
        if (!b) continue;
        for (var j = 0; j < sadeIp.length; j++) {
          var s = sadeIp[j];
          if (!s) continue;
          if (kurallar[k] === 'tam' && b === s) return i;
          if (kurallar[k] === 'bas' && b.indexOf(s) === 0) return i;
          if (kurallar[k] === 'icerik' && b.indexOf(s) >= 0) return i;
        }
      }
    }
    return -1;
  }

  function kacarYerel(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* ── EŞLEŞTİRME KUTULARI ──
     `alanlar`: [[kod, etiket, zorunlu], …]
     Seçimler `data-alan` ile işaretleniyor; `haritaOku` onları okur. */
  function eslestirmeCiz(kok, alanlar, basliklar, degisince) {
    if (!kok) return;
    kok.innerHTML = alanlar.map(function (a) {
      var kod = a[0], etiket = a[1], zorunlu = a[2];
      var t = tahmin(kod, basliklar);
      var secenekler = ['<option value="-1">— eşleştirme —</option>']
        .concat((basliklar || []).map(function (b, i) {
          return '<option value="' + i + '"' + (i === t ? ' selected' : '') +
                 '>' + kacarYerel(b) + '</option>';
        })).join('');
      return '<div class="tp-cift"><label>' + kacarYerel(etiket) +
        (zorunlu ? ' <span style="color:var(--kirmizi)">*</span>' : '') +
        '</label><select data-alan="' + kod + '">' + secenekler + '</select></div>';
    }).join('');
    if (degisince) {
      kok.querySelectorAll('select').forEach(function (s) { s.onchange = degisince; });
    }
  }

  function haritaOku(kok) {
    var harita = {};
    if (!kok) return harita;
    kok.querySelectorAll('select').forEach(function (s) {
      var i = parseInt(s.value, 10);
      if (i >= 0) harita[s.dataset.alan] = i;
    });
    return harita;
  }

  /* ── SATIRLARI KAYDA ÇEVİR ──
     secenek.sayisal      : sayıya çevrilecek alan kodları
     secenek.doldurulacak : birleştirilmiş hücre doldurması yapılacak
                            alan kodları

     ── X1 · BİRLEŞTİRİLMİŞ HÜCRE (aşağı doğru doldurma) ──
     Çeki listelerinde blok no ve malzeme adı birleştirilmiş hücrede
     yazılır: tek blok, birçok satır. Excel bu değeri YALNIZCA ilk
     satıra koyar, kalanlar boş gelir ve "cins boş" diye atlanırdı —
     6 satırlık listeden 1 kayıt çıkıyordu.

     ÖLÇÜ ve ADET doldurulmaz: onlar her satırda farklıdır, boş
     olmaları gerçek bir hatadır. Çağıran hangi alanların
     doldurulacağını kendisi söylüyor. */
  function satirlariCikar(satirlar, alanlar, harita, secenek) {
    secenek = secenek || {};
    var sayisal = secenek.sayisal || [];
    var doldurulacak = secenek.doldurulacak || [];
    var oncekiDeger = {};
    var kayitlar = [], dolduruldu = 0;

    (satirlar || []).forEach(function (satir, idx) {
      var kayit = { _satir: idx + 2 };   // +2: başlık satırı + 1 tabanlı
      alanlar.forEach(function (a) {
        var kod = a[0];
        var ham = (kod in harita) ? satir[harita[kod]] : '';
        kayit[kod] = (sayisal.indexOf(kod) >= 0)
          ? sayi(ham)
          : String(ham === null || ham === undefined ? '' : ham).trim();
      });

      var buSatir = false;
      doldurulacak.forEach(function (kod) {
        var bos = (sayisal.indexOf(kod) >= 0) ? !(kayit[kod] > 0) : !kayit[kod];
        if (bos && oncekiDeger[kod] !== undefined && oncekiDeger[kod] !== '') {
          kayit[kod] = oncekiDeger[kod];
          buSatir = true;
        } else if (!bos) {
          oncekiDeger[kod] = kayit[kod];
        }
      });
      if (buSatir) dolduruldu++;
      kayitlar.push(kayit);
    });
    return { kayitlar: kayitlar, dolduruldu: dolduruldu };
  }

  /* Dosyayı sunucuya çözdürür. Ayrıştırma SUNUCUDA (openpyxl);
     tarayıcıya xlsx kütüphanesi yüklenmiyor. */
  async function dosyaAnaliz(dosya) {
    var fd = new FormData();
    fd.append('dosya', dosya);
    /* S1: api() sarmalayıcısı kullanılmıyor (multipart yükleme),
       CSRF başlığı ELLE eklenmeli. */
    var r = await fetch('/api/v2/excel/analiz', {
      method: 'POST', body: fd,
      headers: { 'X-CSRF-Token': window.CSRF_TOKEN }
    });
    var d = await r.json();
    if (!r.ok || !d.ok) throw new Error((d && d.mesaj) || 'Dosya okunamadı.');
    return d;
  }

  return {
    IPUCU: IPUCU,
    sayi: sayi,
    tahmin: tahmin,
    eslestirmeCiz: eslestirmeCiz,
    haritaOku: haritaOku,
    satirlariCikar: satirlariCikar,
    dosyaAnaliz: dosyaAnaliz
  };
})();

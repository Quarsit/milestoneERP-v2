#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA EK1 — DÖRT EKRAN: KASA DÜZENLEME · ETTN · DÖNÜŞÜM · BLOK İZLEME
=====================================================================

ÖNKOŞUL: **yama_as1.py uygulanmış olmalı.** Betik denetliyor.
Şema yok, göç yok.

Seçtiğin dört uç bağlandı. Hepsi gerçek tarayıcıda açılıp
tıklanarak görüldü — şablonun ayrıştırılabilmesi çalıştığı anlamına
gelmiyor.

═══ 1 · KASA DÜZENLEME ═══

`PUT /api/kasa/<id>` yazılıydı, hiçbir ekran çağırmıyordu: yanlış
kurulmuş bir kasanın adı hiçbir yerden düzeltilemiyordu. Kasa
çekmecesine "Kasayı düzenle" eklendi.

**BAĞLAMADAN ÖNCE BİR KAPI KAPATTIM.** Uç, dövizi serbestçe
değiştirmeye izin veriyordu. ÖLÇÜLDÜ:

      USD kasa · 1.000 açılış + 5.000 giriş  →  6.000 USD
      PUT {"doviz": "EUR"} → 200
      sonra: bakiye 6.000 **EUR**, hareketler hâlâ USD

Rakam aynı kaldı, para birimi değişti. 6.000 USD'nin karşılığı
5.333,33 EUR'ydu. Yani bakiye, kasada olmayan bir parayı
gösteriyordu. Çevirmek de doğru olmazdı — her hareket ayrı günün
kuruyla girilmiş. Artık hareketi olan kasada döviz değiştirilemiyor;
hareketsizde serbest, çünkü orada yanlış seçimi düzeltmekten başka
bir şey olmuyor. Ekran alanı da kilitli ve SEBEBİNİ yazıyor.

**BİR ALANI DA KALDIRDIM.** Modalin ilk hâlinde "Açılış Bakiyesi"
vardı. Ölçtüm: `Kasa` modelinde `baslangic_bakiye` diye bir KOLON
YOK — uç noktada 10 yerde `hasattr`/`getattr` ile yoklanıyor ve
hepsi False dönüyor. Alanı göndermek hiçbir şey yapmıyordu: form
"kaydedildi" derdi, kayıtta hiçbir şey değişmezdi. **Tam DZ5
sınıfı ve az kalsın ben üretiyordum.** Düzenleme artık ad, döviz ve
açıklama soruyor.

  Güncel bakiye de düzenlenmiyor: o hareketlerden türüyor. Yanlış
  bakiyenin doğru yolu kasa hareketi girmek.

  Kasa listesine `hareket_sayisi` eklendi — ekran döviz alanını
  kilitlemek için bunu okuyor. Toplamlardan çıkarmak yetmezdi:
  0 tutarlı bir hareket toplamda görünmez ama dövizi kilitlemeli.

═══ 2 · ETTN → FATURA ═══

GİB portalındaki UUID'den faturayı bulma. **Ayrı bir kutu
açmadım:** fatura ekranındaki arama alanına 32 haneli onaltılık bir
şey yapıştırılınca sistem tanıyor ve ters aramayı kendisi yapıyor.
"Fatura no ararken ETTN aramaya geçmek" diye bir adım yok.

Tireli ve tiresiz, ikisi de çalışıyor. Bulunamazsa bunu da
YAZIYOR — bu ekranda "yok" bir cevaptır: GİB'de duran bir faturanın
karşılığı sistemde yoksa ya ETTN hiç yazılmamış ya fatura bu
sistemde hiç kesilmemiş.

GÖRÜLDÜ: UUID yapıştırıldı → "ETTN EŞLEŞTİ · MST-2026-001 · STONE
USA INC · Kesildi · 25.000 $" ve "Faturayı aç" düğmesi.

═══ 3 · TEKLİF DÖNÜŞÜMÜ ═══

Raporlar ekranına yeni sekme: dönüşüm oranı, kayıp sebepleri,
temsilciye göre döküm.

Ucun paydası KASITLI OLARAK DAR ve ekran bunu yazıyor: iptal edilen
teklifler orana katılmaz (iptal, teklifi geri çekmektir; kayıp,
müşterinin başkasını seçmesidir), bekleyenler de katılmaz. Oran
açıklanmazsa yanlış okunur.

═══ 4 · BLOK İZLEME ═══

Bir blok numarasından tüm yaşam döngüsü: orijinal blok, kesimler,
çıkan bütün stoklar, işlenen maliyetler. Uç hem ORİJİNAL hem ÜRETİM
blok numarasından arıyor, yani kesimden sonra verilen yeni
numarayla da bulunuyor.

Stok çekmecesindeki "Kaynak zinciri"nden FARKLI: o tek bir stok
KAYDININ geçmişi, bu bir blok NUMARASININ tüm ağacı — ve blok
tükendikten sonra da çalışıyor. İhracat izlenebilirliği için
gereken şey bu.

GÖRÜLDÜ: "Blok izleme · EK-77 · 1 kesim · 4 stok", orijinal blok
4.000,00 € matrahla, kesim 4.500,00 $ maliyetle, dört plaka
208,33 $/m² ile. (Bu arada UN1'in de kanıtı: EUR matrah kesimde
USD'ye çevrilmiş.)

  İLK HÂLİ YARIM GENİŞLİKTE KALIYORDU. Çekmece, tablo içermeyen
  bölümleri sütuna koyuyor (`cek-tam` yalnız tablolu bölümlere
  veriliyor); orijinal bloğu kartlarla yazmıştım ve ötekilerle
  hizalanmıyordu. Tabloya çevrildi — ev mekanizmasıyla kavga etmek
  yerine onu kullanmak.

═══ NASIL DOĞRULANDI ═══

Dört ekran gerçek bir tarayıcıda açıldı (Chromium), giriş yapıldı,
firma seçildi, her ekranda düğmelere tıklandı, konsol okundu ve
ekran görüntüsü alındı:

  kasa      modal açıldı · döviz "açık" (hareketsiz kasa) ·
            açılış bakiyesi alanı YOK · kaydedildi, kart
            "USD BANKA (ZIRAAT)" oldu
  ettn      eşleşti, fatura kartı çıktı
  dönüşüm   sekme açıldı, KPI ve tablolar doldu
  blok      EK-77 ağacı tam çıktı

Konsolda yalnız Google Fonts'un yüklenememesi var — benim
sandbox'ımın proxy'si, senin makinende çıkmaz.

═══ DOĞRULANDI ═══
  276 test geçti (270 + 6). js · form · akış · bağlam · firma
  denetimleri temiz; kur ve sessiz denetimlerinin bulguları tabanla
  aynı — yenisi yok.

DOSYALAR
--------
  flask_app.py            kasa döviz kapısı · hareket_sayisi
  templates/kasa.html     düzenle düğmesi + modal
  templates/fatura.html   arama alanında ETTN ters arama
  templates/raporlar.html Teklif Dönüşümü sekmesi
  templates/stok.html     blok izleme çekmecesi
  tests/test_kritik.py    6 yeni test

KULLANIM
--------
  python3 yama_ek1.py            # RAPOR
  python3 yama_ek1.py --uygula
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
    'flask_app.py': 'EK1 · HAREKETİ OLAN KASANIN DÖVİZİ DEĞİŞTİRİLEMEZ',
    'templates/kasa.html': 'EK1 · KASAYI DÜZENLE',
    'templates/fatura.html': 'EK1 · ETTN TERS ARAMA',
    'templates/raporlar.html': 'EK1 · TEKLİF DÖNÜŞÜMÜ',
    'templates/stok.html': 'EK1 · BLOK İZLEME',
    'tests/test_kritik.py': 'def test_ek1_hareketli_kasanin_dovizi_degistirilemez',
}
ONKOSUL = {
    'flask_app.py': 'AS1 · AYNI SLAB İKİ KEZ GİRİLEMEZ',
    'tests/test_kritik.py': 'def test_as2_ekranin_okudugu_alani_sunucu_gonderiyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'EK1 · flask_app.py blok 1',
     r'''                kasa_id=k.id, tip='cikis').scalar() or 0
''',
     r'''                kasa_id=k.id, tip='cikis').scalar() or 0
            # EK1: duzenleme ekrani doviz alanini KILITLEMEK icin
            # hareket sayisini bilmek zorunda. Toplamlardan cikarmak
            # yetmez: 0 tutarli bir hareket toplamda gorunmez ama
            # kasanin dovizini kilitlemesi gerekir.
            hareket_sayisi = KasaHareket.query.filter_by(
                kasa_id=k.id).count()
'''),
    ('flask_app.py', 'EK1 · flask_app.py blok 2',
     r'''                'ana_kasa': is_ana,
''',
     r'''                'hareket_sayisi': hareket_sayisi,      # EK1
                'ana_kasa': is_ana,
'''),
    ('flask_app.py', 'EK1 · flask_app.py blok 3',
     r'''        if 'doviz' in data and data['doviz']:
''',
     r'''
        # ══════════════════════════════════════════════════════════
        #  EK1 · HAREKETİ OLAN KASANIN DÖVİZİ DEĞİŞTİRİLEMEZ
        #
        #  Bu uç ekrana bağlanmamıştı, o yüzden hiç kullanılmıyordu.
        #  Bağlamadan önce ölçtüm:
        #
        #    USD kasa · 1.000 açılış + 5.000 giriş → bakiye 6.000 USD
        #    PUT {"doviz": "EUR"} → 200
        #    sonra: bakiye 6.000 **EUR**, hareketler hâlâ USD
        #
        #  Rakam aynı kaldı, para birimi değişti. 6.000 USD'nin
        #  karşılığı 5.333,33 EUR'ydu. Yani bakiye, kasada olmayan
        #  bir parayı gösteriyor — bu projede kovaladığımız hatanın
        #  tam tanımı.
        #
        #  Çevrim yapmak da doğru olmazdı: hangi hareket hangi günün
        #  kuruyla girilmiş, hepsi ayrı. Doğrusu DOKUNMAMAK: yanlış
        #  dövizle açılmış bir kasa varsa, doğru dövizde yenisini
        #  açıp hareketleri virmanla taşımak gerekir — o yol zaten
        #  var ve izi kalır.
        #
        #  Hareketi OLMAYAN kasada döviz serbestçe düzeltilebilir:
        #  orada yanlış seçimi düzeltmekten başka bir şey olmuyor.
        # ══════════════════════════════════════════════════════════
        if ('doviz' in data and data['doviz']
                and (data['doviz'] or '').upper() != (k.doviz or '')):
            _hs = KasaHareket.query.filter_by(kasa_id=k.id).count()
            if _hs:
                return jsonify({
                    'ok': False, 'error': 'doviz_degisemez',
                    'hareket_sayisi': _hs,
                    'mesaj': f'Bu kasada {_hs} hareket var; dövizi '
                             f'değiştirilemez. Bakiye {k.doviz} olarak '
                             f'birikti — {data["doviz"].upper()} demek '
                             f'rakamı çevirmeden başka bir para birimine '
                             f'yazmak olurdu. Doğru dövizde yeni bir kasa '
                             f'açıp hareketleri virmanla taşıyın.'}), 400
'''),
    ('templates/kasa.html', 'EK1 · templates/kasa.html blok 1',
     r'''{% endblock %}

{% block scripts %}
''',
     r'''<!-- ═══ EK1 · KASAYI DÜZENLE ═══
     Ad, döviz ve açılış bakiyesi. Döviz alanı HAREKETİ OLAN kasada
     kilitli: bakiye o dövizde birikti, başka bir para birimi yazmak
     rakamı çevirmeden ad değiştirmek olurdu. Sunucu da reddediyor —
     tarayıcıda yapılan bir denetim denetim değildir. -->
<div class="modal-ortu" id="kdModal">
  <div class="modal">
    <div class="modal-bas">
      <h3>Kasayı Düzenle</h3>
      <p id="kdAltBaslik">—</p>
    </div>
    <div class="modal-gov">
      <div class="form-satir">
        <div class="form-alan"><label>Kasa Adı</label>
          <input id="kdAd" placeholder="USD Banka"></div>
        <div class="form-alan"><label>Döviz</label>
          <select id="kdDoviz">
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
            <option value="TRY">TRY</option>
          </select>
          <div id="kdDovizNot" style="display:none;font-size:.74rem;color:var(--kehribar);margin-top:4px"></div>
        </div>
      </div>
      <div class="form-alan"><label>Açıklama</label>
        <input id="kdAciklama" placeholder="opsiyonel"></div>
      <!-- AÇILIŞ BAKİYESİ ALANI YOK, bilerek.
           Modalin ilk halinde vardi. Olctum: `Kasa` modelinde
           `baslangic_bakiye` diye bir KOLON YOK — uc noktada o alan
           10 yerde `hasattr`/`getattr` ile yoklaniyor, hepsi False
           donuyor. Yani alani gondermek hicbir sey yapmiyordu; form
           "kaydedildi" der, kayitta hicbir sey degismezdi. Tam DZ5
           sinifi, az kalsin gonderiyordum.
           GUNCEL bakiye de burada duzenlenmiyor: o hareketlerden
           turuyor, elle yazmak defteri ile bakiyeyi ayristirirdi.
           Yanlis bakiye icin dogru yol kasa hareketi girmek. -->
    </div>
    <div class="modal-alt">
      <button class="iptal-btn" onclick="kasaDuzenleKapat()">Vazgeç</button>
      <button class="btn-yeni" id="kdKaydet" onclick="kasaDuzenleKaydet()">Kaydet</button>
    </div>
  </div>
</div>

{% endblock %}

{% block scripts %}
'''),
    ('templates/kasa.html', 'EK1 · templates/kasa.html blok 2',
     r'''  if (yazabilir('kasa'))
    eylem.push(`<button class="blok-btn" style="color:var(--kirmizi)" onclick="kasaSil(${id}, '${kacar(k.ad)}')">Kasayı sil</button>`);
  eylem.push(`<button class="blok-btn" onclick="cekmeceKapat()">Kapat</button>`);
  cekmeceAc(k.ad, `${k.doviz}${k.ana_kasa ? ' · ana kasa' : ''}`, govde, eylem.join(''));
''',
     r'''  if (yazabilir('kasa')) {
    /* EK1: `PUT /api/kasa/<id>` ucu yaziliydi ama hicbir ekran
       cagirmiyordu — yanlis kurulmus bir kasanin adi, dovizi ya da
       acilis bakiyesi hicbir yerden duzeltilemiyordu. */
    eylem.push(`<button class="blok-btn" onclick="kasaDuzenleAc(${id})">Kasayı düzenle</button>`);
    eylem.push(`<button class="blok-btn" style="color:var(--kirmizi)" onclick="kasaSil(${id}, '${kacar(k.ad)}')">Kasayı sil</button>`);
  }
  eylem.push(`<button class="blok-btn" onclick="cekmeceKapat()">Kapat</button>`);
  cekmeceAc(k.ad, `${k.doviz}${k.ana_kasa ? ' · ana kasa' : ''}`, govde, eylem.join(''));
}

/* ═══════════════════════════════════════════════════════════════
   EK1 · KASAYI DÜZENLE
   Ucu (`PUT /api/kasa/<id>`) hicbir ekran cagirmiyordu.
   ═══════════════════════════════════════════════════════════════ */
let KD_ID = null;

function kasaDuzenleAc(id) {
  const k = KASALAR.find(x => x.id === id);
  if (!k) { bildir('Kasa bulunamadı.', true); return; }
  KD_ID = id;
  cekmeceKapat();
  document.getElementById('kdAd').value = k.ad || '';
  document.getElementById('kdAciklama').value = k.aciklama || '';
  const dv = document.getElementById('kdDoviz');
  dv.value = k.doviz || 'USD';
  /* DOVIZ KILIDI: hareketi varsa degistirilemez. Sunucu da ayni
     kurali uyguluyor; burasi SEBEBINI soyluyor. */
  const hs = k.hareket_sayisi;
  const kilit = !(hs === 0 || hs === undefined || hs === null);
  dv.disabled = kilit;
  const not = document.getElementById('kdDovizNot');
  if (kilit) {
    not.style.display = 'block';
    not.textContent = (hs ? hs + ' hareket var' : 'Hareketi olabilir')
      + ' — bakiye bu dövizde birikti, değiştirilemez. '
      + 'Doğru dövizde yeni kasa açıp virmanla taşıyın.';
  } else {
    not.style.display = 'none';
  }
  document.getElementById('kdAltBaslik').textContent =
    `${k.ad || ''} · güncel bakiye ${para(k.bakiye, k.doviz)}`
    + (hs ? ` · ${hs} hareket` : ' · hareket yok');
  document.getElementById('kdModal').classList.add('acik');
}

function kasaDuzenleKapat() {
  document.getElementById('kdModal').classList.remove('acik');
  KD_ID = null;
}

async function kasaDuzenleKaydet() {
  if (!KD_ID) return;
  const ad = document.getElementById('kdAd').value.trim();
  if (!ad) { bildir('Kasa adı zorunlu.', true); return; }
  const govde = { ad: ad, aciklama: document.getElementById('kdAciklama').value };
  const dv = document.getElementById('kdDoviz');
  if (!dv.disabled) govde.doviz = dv.value;
  const btn = document.getElementById('kdKaydet');
  btn.disabled = true; btn.textContent = 'Kaydediliyor…';
  try {
    const d = await api(`/api/kasa/${KD_ID}`,
                        { method: 'PUT', body: JSON.stringify(govde) });
    bildir(d.mesaj || 'Kasa güncellendi');
    kasaDuzenleKapat();
    await kasalariYukle();
  } catch (e) { /* api() zaten bildiriyor */ }
  finally { btn.disabled = false; btn.textContent = 'Kaydet'; }
'''),
    ('templates/fatura.html', 'EK1 · templates/fatura.html blok 1',
     r'''  <div class="suz"><input id="ara" placeholder="Müşteri, fatura no ara…" autocomplete="off"></div>
</div>
''',
     r'''  <div class="suz"><input id="ara" placeholder="Müşteri, fatura no veya ETTN ara…" autocomplete="off" spellcheck="false"></div>
</div>

<!-- ═══ EK1 · ETTN → FATURA (GİB MUTABAKATI) ═══
     GİB portalındaki listede bir UUID görünce hangi faturaya denk
     geldiğini bulmak için. Ayrı bir kutu AÇMADIK: arama alanına
     32 haneli onaltılık bir şey yapıştırılınca sistem tanıyor ve
     ters aramayı kendisi yapıyor. Fatura numarası ararken ETTN
     aramaya geçmek diye bir adım yok. -->
<div id="ettnSonuc" style="display:none;margin:-8px 0 16px"></div>
'''),
    ('templates/fatura.html', 'EK1 · templates/fatura.html blok 2',
     r'''let araZaman;
document.getElementById('ara').addEventListener('input', e => {
  clearTimeout(araZaman);
  araZaman = setTimeout(() => { ARA = e.target.value; ciz(); }, 200);
''',
     r'''/* ═══ EK1 · ETTN TERS ARAMA ═══
   Sunucudaki kuralin aynisi: tireli ya da tiresiz, 32 hane
   onaltilik (`_ettn_normalize`). Ayni kurali iki yerde yazmak
   ayrisma riski; burada YALNIZCA "bu bir ETTN mi" sorusuna cevap
   veriyoruz, normalizasyonu sunucu yapiyor. */
function ettnMi(metin) {
  const c = (metin || '').trim().replace(/[{} ]/g, '').replace(/-/g, '');
  return c.length === 32 && /^[0-9a-fA-F]+$/.test(c);
}

async function ettnAra(ham) {
  const kutu = document.getElementById('ettnSonuc');
  kutu.style.display = 'block';
  kutu.innerHTML = '<div class="bos" style="padding:12px">ETTN aranıyor…</div>';
  try {
    const d = await api('/api/fatura/ettn/' + encodeURIComponent(ham.trim()));
    const f = d.fatura || {};
    kutu.innerHTML = `
      <div class="tablo-kutu" style="border-left:3px solid var(--verde)">
        <div style="padding:13px 15px">
          <div style="font-size:.72rem;color:var(--soluk);text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px">ETTN eşleşti</div>
          <div style="font-family:var(--mono);font-size:.74rem;color:var(--soluk);margin-bottom:9px">${kacar(f.ettn || '')}</div>
          <div style="display:flex;flex-wrap:wrap;gap:6px 22px;align-items:baseline">
            <strong style="font-size:1rem">${kacar(f.fatura_no || f.id || '—')}</strong>
            <span>${kacar(f.musteri || '—')}</span>
            <span class="rozet rz-gri">${kacar(f.durum || '—')}</span>
            <span class="mono">${para(f.toplam, f.doviz)}</span>
            <span style="color:var(--soluk);font-size:.8rem">${kacar((f.fatura_tarihi || '').slice(0, 10))}</span>
          </div>
          <div style="margin-top:8px;font-size:.78rem;color:var(--soluk)">
            ${f.efatura_senaryo ? 'Senaryo: ' + kacar(f.efatura_senaryo) + ' · ' : ''}
            ${f.efatura_durum ? 'GİB durumu: ' + kacar(f.efatura_durum) : ''}
          </div>
          <button class="blok-btn birincil" style="margin-top:11px"
                  onclick="ettnSonucGit('${kacar(f.id || '')}')">Faturayı aç</button>
          <button class="blok-btn" style="margin-top:11px"
                  onclick="ettnSonucKapat()">Kapat</button>
        </div>
      </div>`;
  } catch (e) {
    /* 404 = kayitli fatura yok. api() zaten bildirdi; burada da
       YAZIYORUZ, cunku "bulunamadi" bu ekranda bir CEVAP:
       GIB'de olan bir fatura bizde yok demek. */
    const _m = (e && e.yanit && e.yanit.mesaj) || 'Bu ETTN ile kayıtlı fatura yok.';
    kutu.innerHTML = `
      <div class="tablo-kutu" style="border-left:3px solid var(--kehribar)">
        <div style="padding:13px 15px">
          <div style="font-weight:600;margin-bottom:4px">${kacar(_m)}</div>
          <div style="font-size:.79rem;color:var(--soluk)">
            GİB'de duran bir faturanın karşılığı sistemde yoksa, ya ETTN
            hiç yazılmamış ya da fatura bu sistemde hiç kesilmemiş.</div>
          <button class="blok-btn" style="margin-top:10px" onclick="ettnSonucKapat()">Kapat</button>
        </div>
      </div>`;
  }
}

function ettnSonucKapat() {
  const k = document.getElementById('ettnSonuc');
  k.style.display = 'none'; k.innerHTML = '';
}

function ettnSonucGit(fid) {
  if (!fid) return;
  ettnSonucKapat();
  document.getElementById('ara').value = '';
  ARA = ''; ciz();
  detayAc(fid);
}

let araZaman;
document.getElementById('ara').addEventListener('input', e => {
  clearTimeout(araZaman);
  const ham = e.target.value;
  araZaman = setTimeout(() => {
    /* EK1: ETTN yapistirildiysa liste suzmek anlamsiz — fatura no
       ile ETTN birbirine hic benzemez. Ters aramayi yapip listeyi
       oldugu gibi birakiyoruz. */
    if (ettnMi(ham)) { ettnAra(ham); return; }
    ettnSonucKapat();
    ARA = ham; ciz();
  }, 200);
'''),
    ('templates/raporlar.html', 'EK1 · templates/raporlar.html blok 1',
     r'''  <button class="sekme" data-b="stokmaliyet">Stok Maliyeti</button>
''',
     r'''  <button class="sekme" data-b="stokmaliyet">Stok Maliyeti</button>
  <button class="sekme" data-b="donusum">Teklif Dönüşümü</button>
'''),
    ('templates/raporlar.html', 'EK1 · templates/raporlar.html blok 2',
     r'''<section class="bolum" id="b-sevkiyat">
''',
     r'''<!-- ═══ EK1 · TEKLİF DÖNÜŞÜMÜ ═══
     Ucu (`/api/rapor/donusum`) yazılmıştı, paydası özenle
     düşünülmüştü, sonra hiçbir ekrana bağlanmamıştı. -->
<section class="bolum" id="b-donusum">
  <div class="izgara-2">
    <div class="panel">
      <h4>Dönüşüm oranı</h4>
      <div id="dnKpi" style="display:flex;flex-wrap:wrap;gap:10px 26px;align-items:baseline;margin:14px 0 6px">
        <div class="yukleniyor">Yükleniyor…</div>
      </div>
      <div id="dnNot" style="font-size:.78rem;color:var(--soluk);line-height:1.5;margin-top:10px"></div>
    </div>
    <div class="panel">
      <h4>Kayıp sebepleri</h4>
      <div class="tablo-kutu" style="margin-top:12px">
        <table>
          <thead><tr><th>Sebep</th><th class="sag">Teklif</th></tr></thead>
          <tbody id="dnSebep"><tr><td colspan="2" class="yukleniyor">Yükleniyor…</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>
  <div class="panel" style="margin-top:18px">
    <h4>Temsilciye göre</h4>
    <div class="tablo-kutu" style="margin-top:12px">
      <table>
        <thead><tr><th>Temsilci</th><th class="sag">Kazanılan</th>
          <th class="sag">Kaybedilen</th><th class="sag">Bekleyen</th>
          <th class="sag">Oran</th></tr></thead>
        <tbody id="dnTemsilci"><tr><td colspan="5" class="yukleniyor">Yükleniyor…</td></tr></tbody>
      </table>
    </div>
  </div>
</section>

<section class="bolum" id="b-sevkiyat">
'''),
    ('templates/raporlar.html', 'EK1 · templates/raporlar.html blok 3',
     r'''                    stokmaliyet: stokMaliyetYukle };
''',
     r'''                    stokmaliyet: stokMaliyetYukle, donusum: donusumYukle };
/* ═══ EK1 · TEKLİF DÖNÜŞÜMÜ ═══
   PAYDA DAR ve bu kasıtlı — ucun kendi yorumu söylüyor: iptal
   edilen teklif oranın dışında (iptal, teklifi GERİ ÇEKMEK
   demek; kayıp, müşterinin BAŞKASINI seçmesi), bekleyenler de
   dışında (henüz sonuçlanmadılar). Ekran bunu YAZIYOR, çünkü
   açıklanmamış bir oran yanlış okunur. */
async function donusumYukle() {
  if (!gorunur('raporlar')) {
    document.getElementById('dnKpi').innerHTML = bos('Yetkin yok.');
    return;
  }
  try {
    const d = await api('/api/rapor/donusum');
    const oran = Number(d.donusum_orani || 0);
    const renk = oran >= 40 ? '--verde' : oran >= 20 ? '--kehribar' : '--kirmizi';
    document.getElementById('dnKpi').innerHTML = `
      <div>
        <div style="font-family:var(--baslik);font-weight:800;font-size:2.1rem;letter-spacing:-.02em;color:var(${renk})">
          %${oran.toFixed(1).replace('.', ',')}</div>
        <div style="font-size:.74rem;color:var(--soluk);text-transform:uppercase;letter-spacing:.04em">dönüşüm</div>
      </div>
      <div><div class="mono" style="font-weight:700;font-size:1.1rem;color:var(--verde)">${d.kazanilan || 0}</div>
        <div style="font-size:.74rem;color:var(--soluk)">kazanılan</div></div>
      <div><div class="mono" style="font-weight:700;font-size:1.1rem;color:var(--kirmizi)">${d.kaybedilen || 0}</div>
        <div style="font-size:.74rem;color:var(--soluk)">kaybedilen</div></div>
      <div><div class="mono" style="font-weight:700;font-size:1.1rem">${d.sonuclanan || 0}</div>
        <div style="font-size:.74rem;color:var(--soluk)">sonuçlanan (payda)</div></div>
      <div><div class="mono" style="font-weight:700;font-size:1.1rem;color:var(--soluk)">${d.bekleyen || 0}</div>
        <div style="font-size:.74rem;color:var(--soluk)">bekleyen</div></div>
      <div><div class="mono" style="font-weight:700;font-size:1.1rem;color:var(--soluk)">${d.iptal || 0}</div>
        <div style="font-size:.74rem;color:var(--soluk)">iptal</div></div>`;
    document.getElementById('dnNot').textContent = d.not || '';

    const sb = Object.entries(d.kayip_sebepleri || {});
    document.getElementById('dnSebep').innerHTML = sb.length
      ? sb.map(([ad, n]) => `<tr><td>${kacar(ad)}</td>
          <td class="sag mono" style="font-weight:600">${n}</td></tr>`).join('')
      : '<tr><td colspan="2" class="bos">Kaybedilen teklif yok.</td></tr>';

    const tm = Object.entries(d.temsilciler || {});
    document.getElementById('dnTemsilci').innerHTML = tm.length
      ? tm.map(([ad, x]) => {
          const kz = x.kazanilan || 0, kb = x.kaybedilen || 0;
          const snc = kz + kb;
          const o = snc ? (kz / snc * 100) : null;
          return `<tr>
            <td><strong>${kacar(ad)}</strong></td>
            <td class="sag mono" style="color:var(--verde);font-weight:600">${kz}</td>
            <td class="sag mono" style="color:var(--kirmizi)">${kb}</td>
            <td class="sag mono" style="color:var(--soluk)">${x.bekleyen || 0}</td>
            <td class="sag mono" style="font-weight:600">${
              o === null ? '—' : '%' + o.toFixed(1).replace('.', ',')}</td>
          </tr>`;
        }).join('')
      : '<tr><td colspan="5" class="bos">Temsilci bilgisi olan teklif yok.</td></tr>';
  } catch (e) { /* api() bildirdi */ }
}

'''),
    ('templates/stok.html', 'EK1 · templates/stok.html blok 1',
     r'''async function detayAc(id) {
''',
     r'''/* ═══════════════════════════════════════════════════════════════
   EK1 · BLOK İZLEME

   Uç yazılmıştı, hiçbir ekran çağırmıyordu. Bir blok numarasından
   tüm yaşam döngüsünü veriyor ve hem ORİJİNAL hem ÜRETİM blok
   numarasından arıyor — yani kesimden sonra verilen yeni numarayla
   da bulunuyor.

   "Kaynak zinciri"nden farkı: o tek bir stok KAYDININ geçmişi, bu
   bir blok NUMARASININ tüm ağacı. Blok tükendikten sonra da
   çalışıyor; ihracat izlenebilirliği için gereken şey bu.
   ═══════════════════════════════════════════════════════════════ */
async function blokIzlemeAc(blokNo) {
  if (!blokNo) return;
  cekmeceAc(`Blok izleme · ${kacar(blokNo)}`, 'yükleniyor…',
            '<div class="yukleniyor">Yükleniyor…</div>', '');
  let d;
  try {
    d = await api('/api/blok/' + encodeURIComponent(blokNo) + '/izleme');
  } catch (e) { cekmeceKapat(); return; }

  const oz = d.ozet || {};
  const bl = d.kaynak_bloklar || [];
  const ks = d.kesimler || [];
  const ur = d.uretilen_stoklar || [];
  const ml = d.maliyetler || [];

  const kutu = (etiket, deger) =>
    `<div class="alan"><label>${etiket}</label><div>${deger}</div></div>`;

  /* ORIJINAL BLOK(LAR) */
  /* TABLO olarak: cekmece tablosuz bolumleri SUTUNA koyuyor
     (`cek-tam` yalniz tablo iceren bolumlere veriliyor). Ilk halinde
     kartlarla yazmistim ve bolum yarim genislikte kaliyordu —
     otekilerle hizalanmiyordu. */
  const blokGov = bl.length ? `<div class="tablo-kutu"><table>
      <thead><tr><th>Blok</th><th>Cins</th><th>Üretici</th>
        <th>Ölçü</th><th class="sag">Tonaj</th>
        <th class="sag">Matrah</th><th>Durum</th></tr></thead>
      <tbody>${bl.map(b => `<tr>
        <td class="mono">${kacar(b.id)}
          ${b.fatura_no ? '<div style="font-size:.7rem;color:var(--soluk)">fatura ' + kacar(b.fatura_no) + '</div>' : ''}</td>
        <td>${kacar(b.cins || '—')}</td>
        <td>${kacar(b.uretici || '—')}</td>
        <td class="mono" style="font-size:.76rem">${
          [b.boy, b.yukseklik, b.en].filter(x => x).join('×') || '—'}</td>
        <td class="sag mono">${b.tonaj ? Number(b.tonaj).toLocaleString('tr-TR') : '—'}</td>
        <td class="sag mono">${b.matrah ? para2(b.matrah, b.doviz) : '—'}</td>
        <td>${kacar(b.durum || '—')}
          ${b.giris_tarihi ? '<div style="font-size:.7rem;color:var(--soluk)">' + kacar(String(b.giris_tarihi).slice(0, 10)) + '</div>' : ''}</td>
      </tr>`).join('')}</tbody></table></div>`
    : '<div class="bos" style="padding:10px">Bu numarayla kayıtlı blok yok (blok tükenmiş olabilir).</div>';

  /* KESIMLER */
  const kesimGov = ks.length ? `<div class="tablo-kutu"><table>
      <thead><tr><th>Kesim</th><th>Tarih</th><th>Üretim No</th>
        <th class="sag">Fire</th><th class="sag">Maliyet</th></tr></thead>
      <tbody>${ks.map(k => `<tr>
        <td class="mono">${kacar(k.id)}</td>
        <td>${kacar(String(k.tarih || '—').slice(0, 10))}</td>
        <td class="mono">${kacar(k.uretim_blok_no || '—')}</td>
        <td class="sag mono">${(k.fire_orani || 0).toLocaleString('tr-TR')} %</td>
        <td class="sag mono">${para2(k.toplam_maliyet, k.doviz)}</td>
      </tr>`).join('')}</tbody></table></div>`
    : '<div class="bos" style="padding:10px">Bu blok hiç kesilmemiş.</div>';

  /* URETILEN STOKLAR — tipe gore grupla */
  const grup = {};
  ur.forEach(x => { (grup[x.tip] = grup[x.tip] || []).push(x); });
  const urGov = ur.length ? Object.entries(grup).map(([tip, liste]) => {
    const m2 = liste.reduce((a, x) => a + Number(x.metraj_m2 || 0), 0);
    return `
    <div style="margin-bottom:10px">
      <div style="font-size:.78rem;font-weight:700;margin-bottom:5px">
        ${kacar(tip)} · ${liste.length} kayıt
        ${m2 ? ' · ' + m2.toLocaleString('tr-TR', {maximumFractionDigits: 2}) + ' m²' : ''}</div>
      <div class="tablo-kutu"><table>
        <thead><tr><th>Stok</th><th>Ölçü</th><th>Durum</th>
          <th class="sag">m²</th><th class="sag">Birim</th></tr></thead>
        <tbody>${liste.map(x => `<tr>
          <td class="mono">${kacar(x.id)}${x.kasa_no ? '<div style="font-size:.7rem;color:var(--soluk)">' + kacar(x.kasa_no) + '</div>' : ''}</td>
          <td class="mono" style="font-size:.76rem">${[x.boy, x.yukseklik, x.kalinlik].filter(v => v).join('×')}</td>
          <td>${kacar(x.durum || '—')}</td>
          <td class="sag mono">${Number(x.metraj_m2 || 0).toLocaleString('tr-TR', {maximumFractionDigits: 2})}</td>
          <td class="sag mono">${para2(x.alis_fiyati, x.doviz)}</td>
        </tr>`).join('')}</tbody></table></div>
    </div>`;
  }).join('')
    : '<div class="bos" style="padding:10px">Bu bloktan üretilmiş stok yok.</div>';

  /* MALIYETLER */
  const mlGov = ml.length ? `<div class="tablo-kutu"><table>
      <thead><tr><th>Maliyet</th><th>Tip</th><th>Tarih</th>
        <th>Bağlı</th><th class="sag">Tutar</th></tr></thead>
      <tbody>${ml.map(m => `<tr>
        <td class="mono">${kacar(m.id)}</td>
        <td>${kacar(m.tip || '—')}</td>
        <td>${kacar(String(m.tarih || '—').slice(0, 10))}</td>
        <td class="mono" style="font-size:.74rem;color:var(--soluk)">${kacar(m.kaynak || '')}</td>
        <td class="sag mono">${para2(m.tutar, m.doviz)}</td>
      </tr>`).join('')}</tbody></table></div>`
    : '<div class="bos" style="padding:10px">İşlenmiş ek maliyet yok.</div>';

  const bas = (t) => `<h4 style="font-size:.8rem;font-weight:700;letter-spacing:.05em;
    text-transform:uppercase;color:var(--soluk);margin:16px 0 7px">${t}</h4>`;

  const govde = `
    <div class="alan-grid" style="margin-bottom:6px">
      ${kutu('Orijinal blok', oz.orijinal_blok_sayisi || 0)}
      ${kutu('Kesim', oz.kesim_sayisi || 0)}
      ${kutu('Üretilen stok', oz.uretilen_stok_sayisi || 0)}
      ${kutu('Maliyet kaydı', oz.maliyet_kayit_sayisi || 0)}
    </div>
    ${bas('Orijinal blok')}${blokGov}
    ${bas('Kesimler')}${kesimGov}
    ${bas('Üretilen stoklar')}${urGov}
    ${bas('İşlenen maliyetler')}${mlGov}`;

  cekmeceAc(`Blok izleme · ${kacar(d.blok_no || blokNo)}`,
            `${oz.kesim_sayisi || 0} kesim · ${oz.uretilen_stok_sayisi || 0} stok`,
            govde,
            `<button class="blok-btn" onclick="cekmeceKapat()">Kapat</button>`);
}

async function detayAc(id) {
'''),
    ('templates/stok.html', 'EK1 · templates/stok.html blok 2',
     r'''  eylem.push(`<button class="blok-btn" onclick="cekmeceKapat()">Kapat</button>`);
''',
     r'''  /* EK1 · BLOK İZLEME. "Kaynak zinciri" TEK STOK KAYDININ geçmişini
     gösteriyor; blok izleme BLOK NUMARASI üzerinden gidiyor ve blok
     tükendikten sonra da çalışıyor — kesimler, çıkan bütün stoklar,
     işlenen maliyetler bir arada. Uç (`/api/blok/<no>/izleme`) hem
     orijinal hem ÜRETİM blok numarasından arıyor. */
  if (s.blok_no)
    eylem.push(`<button class="blok-btn" onclick="blokIzlemeAc('${kacar(s.blok_no)}')">Blok izleme</button>`);
  eylem.push(`<button class="blok-btn" onclick="cekmeceKapat()">Kapat</button>`);
'''),
    ('tests/test_kritik.py', 'EK1 · tests/test_kritik.py blok 1',
     r'''                          + ' | '.join(bulgular))
''',
     r'''                          + ' | '.join(bulgular))


# ══════════════════════════════════════════════════════════════════
#  EK1 · YAZILMIŞ AMA BAĞLANMAMIŞ DÖRT UÇ BAĞLANDI
#
#  SD4 sınıfı: uç eksiksiz yazılmış, hiçbir ekran çağırmıyor. Tarama
#  275 uçtan 7'sini öyle bulmuştu; Bahadır dördünü seçti:
#    · PUT  /api/kasa/<id>            kasa düzenleme
#    · GET  /api/fatura/ettn/<ettn>   GİB mutabakatı için ters arama
#    · GET  /api/rapor/donusum        teklif dönüşüm oranı
#    · GET  /api/blok/<no>/izleme     bloğun tüm yaşam döngüsü
# ══════════════════════════════════════════════════════════════════
def test_ek1_hareketli_kasanin_dovizi_degistirilemez():
    """Bakiye bir dövizde biriktiyse para birimi değiştirilemez.

    ÖLÇÜLDÜ (kapı yokken): USD kasa, 1.000 açılış + 5.000 giriş =
    6.000 USD. `PUT {"doviz": "EUR"}` → 200 ve bakiye 6.000 **EUR**
    oldu; hareketler hâlâ USD. 6.000 USD'nin karşılığı 5.333,33
    EUR'ydu. Yani bakiye, kasada olmayan bir parayı gösteriyordu.

    Çevirmek de doğru olmazdı: her hareket ayrı günün kuruyla
    girilmiş. Doğrusu dokunmamak."""
    from models import Kasa, KasaHareket
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        k = Kasa(ad='EK1 USD KASA', doviz='USD', bakiye=0)
        db.session.add(k)
        db.session.commit()
        kid = k.id
    r = c.post('/api/kasa/hareket', headers=H, json={
        'kasa_id': kid, 'tip': 'giris', 'tutar': 5000,
        'tarih': date(2026, 10, 28).isoformat(), 'aciklama': 'EK1'})
    assert r.status_code in (200, 201), r.get_data(as_text=True)[:200]

    r2 = c.put(f'/api/kasa/{kid}', headers=H, json={'doviz': 'EUR'})
    assert r2.status_code == 400, \
        f'hareketli kasanın dövizi değişti: {r2.get_data(as_text=True)[:200]}'
    _y = r2.get_json()
    assert _y.get('error') == 'doviz_degisemez', _y
    assert _y.get('hareket_sayisi', 0) >= 1, _y
    with fa.app.app_context():
        assert db.session.get(Kasa, kid).doviz == 'USD'

    # Ad ve aciklama AYNI istekte degisebilmeli — doviz kapisi
    # otekileri kilitlemiyor
    r3 = c.put(f'/api/kasa/{kid}', headers=H,
               json={'ad': 'EK1 USD KASA (Ziraat)'})
    assert r3.status_code == 200, r3.get_data(as_text=True)[:200]
    with fa.app.app_context():
        assert db.session.get(Kasa, kid).ad == 'EK1 USD KASA (Ziraat)'


def test_ek1_hareketsiz_kasanin_dovizi_duzeltilebilir():
    """Hareketi yoksa yanlış seçilmiş döviz düzeltilebilmeli.

    Orada düzeltmekten başka bir şey olmuyor; kapıyı her duruma
    germek yeni kurulmuş bir kasayı onarılamaz yapardı."""
    from models import Kasa
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        k = Kasa(ad='EK1 BOS KASA', doviz='TRY', bakiye=0)
        db.session.add(k)
        db.session.commit()
        kid = k.id
    r = c.put(f'/api/kasa/{kid}', headers=H, json={'doviz': 'EUR'})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    with fa.app.app_context():
        assert db.session.get(Kasa, kid).doviz == 'EUR'


def test_ek1_kasa_listesi_hareket_sayisini_gonderiyor():
    """Düzenleme ekranı döviz alanını kilitlemek için bunu okuyor.

    Toplamlardan çıkarmak yetmez: 0 tutarlı bir hareket toplamda
    görünmez ama kasanın dövizini kilitlemesi gerekir."""
    from models import Kasa
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(Kasa(ad='EK1 SAYIM KASA', doviz='USD', bakiye=0))
        db.session.commit()
    d = c.get('/api/kasa', headers=H).get_json()
    kayitlar = d if isinstance(d, list) else (d.get('kasalar') or [])
    hedef = [x for x in kayitlar if x.get('ad') == 'EK1 SAYIM KASA']
    assert hedef, kayitlar[:3]
    assert 'hareket_sayisi' in hedef[0], hedef[0]
    assert hedef[0]['hareket_sayisi'] == 0, hedef[0]


def test_ek1_ettn_ters_arama_faturayi_buluyor():
    """GİB'deki UUID'den faturaya gidilebilmeli."""
    from models import Fatura
    c = istemci('admin', 'ADMIN')
    _ettn = '3f2a9c10-7b45-4e8d-9a12-0c5e6d7f8a90'
    with fa.app.app_context():
        db.session.add(Cari(id='MUS-EK1', unvan='MUSTERI EK1',
                            cari_tip='Müşteri'))
        db.session.add(Fatura(
            id='FT-EK1', fatura_no='EK1-001', cari_id='MUS-EK1',
            musteri='MUSTERI EK1', yon='satis', durum='Kesildi',
            doviz='USD', toplam=25000, ara_toplam=25000,
            fatura_tarihi=date(2026, 10, 28), ettn=_ettn))
        db.session.commit()
    # Tireli
    d = c.get(f'/api/fatura/ettn/{_ettn}', headers=H)
    assert d.status_code == 200, d.get_data(as_text=True)[:200]
    _j = d.get_json()
    assert _j.get('bulundu') is True, _j
    assert _j['fatura']['id'] == 'FT-EK1', _j
    # TIRESIZ de bulmali — GIB'den kopyalanan bicim degisebilir
    d2 = c.get('/api/fatura/ettn/' + _ettn.replace('-', ''), headers=H)
    assert d2.status_code == 200, d2.get_data(as_text=True)[:200]
    assert d2.get_json()['fatura']['id'] == 'FT-EK1'
    # Olmayan ETTN: 404 ve BULUNDU=False — "yok" da bir cevap
    d3 = c.get('/api/fatura/ettn/00000000-0000-0000-0000-000000000000',
               headers=H)
    assert d3.status_code == 404, d3.status_code
    assert d3.get_json().get('bulundu') is False, d3.get_json()


def test_ek1_dort_uc_artik_bir_ekrandan_cagriliyor():
    """Bağlanan dört uç şablonlarda GEÇMELİ.

    SD4 sınıfının bekçisi: uç yazılı, ekran yok. Biri yeniden
    kopsa bu test görünür kılar."""
    import io as _io
    _sablon = os.path.join(KOK, 'templates')
    tum = ''
    for ad in os.listdir(_sablon):
        if ad.endswith('.html'):
            tum += _io.open(os.path.join(_sablon, ad),
                            encoding='utf-8', errors='replace').read()
    for onek, nerede in (('/api/kasa/', 'kasa düzenleme'),
                         ('/api/fatura/ettn/', 'ETTN ters arama'),
                         ('/api/rapor/donusum', 'dönüşüm raporu'),
                         ('/api/blok/', 'blok izleme')):
        assert onek in tum, f'{nerede} ({onek}) hiçbir şablonda yok'
    # Kasa duzenleme PUT ile cagrilmali — GET/DELETE zaten vardi
    kasa = _io.open(os.path.join(_sablon, 'kasa.html'),
                    encoding='utf-8').read()
    assert "method: 'PUT'" in kasa, 'kasa.html PUT çağırmıyor'
    assert 'kasaDuzenleKaydet' in kasa, 'kasa düzenleme kaydet yok'


def test_ek1_kasa_duzenleme_olmayan_alani_sormuyor():
    """Modal `baslangic_bakiye` SORMAMALI — o kolon yok.

    Modalin ilk halinde "Açılış Bakiyesi" alanı vardı. Ölçtüm:
    `Kasa` modelinde `baslangic_bakiye` diye bir kolon YOK; uç
    noktada 10 yerde `hasattr`/`getattr` ile yoklanıyor ve hepsi
    False dönüyor. Yani alanı göndermek hiçbir şey yapmıyordu —
    form "kaydedildi" der, kayıtta hiçbir şey değişmezdi. DZ5
    sınıfı; az kalsın gönderiyordum."""
    import io as _io
    from models import Kasa
    assert not hasattr(Kasa, 'baslangic_bakiye') or \
        'baslangic_bakiye' not in {c.name for c in Kasa.__table__.columns}, \
        'kolon eklendiyse bu test gözden geçirilmeli'
    kasa = _io.open(os.path.join(KOK, 'templates', 'kasa.html'),
                    encoding='utf-8').read()
    _i = kasa.index('kdModal')
    _modal = kasa[_i:kasa.index('</div>\n</div>', _i)]
    assert 'kdBakiye' not in _modal, \
        'düzenleme modalı var olmayan bir alanı soruyor'
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA EK1 — DÖRT EKRAN: KASA DÜZENLEME · ETTN · DÖNÜŞÜM · BLOK İZLEME')
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
        print('    python3 yama_ek1.py            # rapor')
        print('    python3 yama_ek1.py --uygula')
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
        print('  ⊙ Yama EK1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_ek1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_ek1'
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
    print('    2) venv/bin/python -m pytest tests/test_kritik.py -q   # 276')
    print()
    print('  BAKILACAK YER')
    print('    1. Finans -> Banka ve Kasa -> bir kasaya tikla ->')
    print('       "Kasayi duzenle". Hareketi olan kasada DOVIZ alani')
    print('       kilitli ve sebebi yaziyor.')
    print('    2. Faturalar -> arama kutusuna bir ETTN yapistir.')
    print('       Tireli ya da tiresiz, ikisi de olur.')
    print('    3. Analiz -> Raporlar -> "Teklif Donusumu" sekmesi.')
    print('    4. Depo -> bir BLOK satirina tikla -> "Blok izleme".')
    print('       Blok tukendikten sonra da calisiyor; uretim blok')
    print('       numarasiyla da buluyor.')
    print()
    print('  RAKAM DEGISMIYOR')
    print('    Yeni ekranlar OKUYOR. Tek yazan yer kasa duzenleme ve')
    print('    o da artik dovizi oynatamiyor.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

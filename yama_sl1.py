#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA SL1 — SATIŞLAR LİSTESİ SATIŞ BAŞINA, KALEM BAŞINA DEĞİL
==============================================================

ÖNKOŞUL: **yama_vr1.py uygulanmış olmalı.** Betik denetliyor.
Şema değişikliği YOK, göç YOK.

Kullanım:
    python3 yama_sl1.py              # rapor, dosyalara dokunmaz
    python3 yama_sl1.py --uygula
    venv/bin/python -m pytest tests/test_kritik.py -q     # 323

NOT: Bu projede "SG1" kısaltması zaten sipariş güncelleme için
kullanılmış. Karışmasın diye bu yama SL1 (satış listesi).

═══ ÖNCE: KDV SORUNU KODDA DEĞİLDİ ═══

"KDV cariye borç yazılmıyor" dediğin durum, HS1'in dosyada olup
ÇALIŞAN SUNUCUDA olmamasıydı: Python kodu süreç başlarken yükleniyor,
yama dosyayı değiştiriyor ama çalışan sunucu eskisini tutuyor.
Restart'tan sonra düzeldi — ölçtüm: 1.008 + 201,60 = 1.209,60 fatura,
cariye 1.209,60 borç.

Ekran görüntündeki form da eski hâliydi: "VADE TARİHİ" yazıyordu
(yenisinde "Fatura Vadesi"), KDV DURUMU seçeneği yoktu ve toplam
satırı "(KDV %20 dahil)" diyordu.

BUNDAN SONRAKİ HER YAMADA: uygula → **systemctl restart** → Ctrl+F5.

═══ ASIL KONU: LİSTE ═══

İki plakalı TEK satış, satışlar sekmesinde İKİ KUTU olarak
görünüyordu — aynı fatura no, aynı müşteri, aynı tarih. Kullanıcı
iki satış yaptığını sanıyor.

Satış kaydının KALEM BAŞINA üretilmesi doğru ve değişmedi: ürün
bazlı kârlılık ondan besleniyor (F1/F2; DV1'de transit faturayı da
o yola soktuk — 100 m² plaka + 20 ton blok "CALACATTA · 120 m²"
diye tek kayıt oluyordu). Yanlış olan, LİSTENİN o kayıtları olduğu
gibi basmasıydı.

Artık:
  · Satırlar FATURAYA göre toplanıyor. Faturasız kayıt kendi
    başına bir satıştır (birleştirecek belge yok).
  · Çok kalemli bir satıra tıklayınca kalemler tek tek listeleniyor;
    her biri kendi detayını açıyor. Kalem bilgisi KAYBOLMUYOR.
  · Tek kalemli satır doğrudan detaya gidiyor — araya boş bir adım
    koymak en sık durumu yavaşlatmak olurdu.
  · Süzgeçler KALEM üzerinde çalışıp sonra gruplanıyor. Tersi,
    "cins = X" süzgecinde X içermeyen kalemleri de gruba takılı
    bırakırdı.
  · Miktar yalnız BİRİMLER AYNIYSA toplanıyor. Farklıysa "N kalem"
    yazıyor: 100 m² + 20 ton toplayıp "120 m²" demek, DV1'de
    düzelttiğimiz hatanın ekrandaki kopyası olurdu.
  · KPI "2 satış" değil "1 satış · 2 kalem" diyor.

═══ DÜZELTİRKEN ÇIKAN İKİNCİ TUTARSIZLIK ═══

Müşteri özeti ucu da KAYIT sayıyordu. Liste "1 satış" derken
çekmecedeki özet "Satış adedi 2" diyecekti — AYNI EKRANDA satır ve
özet farklı sayı. EM2'de düzelttiğimiz durumun kopyası. Uç artık
satış sayıyor ve kalem sayısını ayrıca veriyor.

Bir de AS2 sınıfı: ekran faturaya göre gruplayacak ama `/api/satislar`
`fatura_id` GÖNDERMİYORDU. `fatura_no` zayıf bir anahtar (iki ayrı
belge aynı numarayı taşıyabilir); kimlik eklendi.

═══ DOĞRULAMA ═══

  · 323 test geçiyor (319 → 323)
  · 4 SL1 testinin hepsi tabanda düşüyor
  · Tarayıcıda koşuldu: iki kalemli satış listede TEK satır,
    KPI "1 satış · 2 kalem", çekmecede iki kalem listeleniyor,
    kaleme tıklayınca o kalemin detayı açılıyor, müşteri özeti
    "1 · 2 kalem" diyor. Konsol temiz.
  · `js_denetim.py` temiz · 29 şablon ayrıştırılabiliyor
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
    'flask_app.py': "# ── SL1 · SATIŞ SAYISI, KAYIT SAYISI DEĞİL ──",
    'templates/satislar.html': 'function gruplaSatislar(',
    'tests/test_kritik.py': 'def test_sl1_musteri_ozeti_satis_sayiyor_kalem_degil',
}
ONKOSUL = {
    'flask_app.py': 'def _transfer_esi(hareket, pencere_sn=120)',
    'templates/satislar.html': 'function musteriOzetiYukle(',
    'tests/test_kritik.py':
        'def test_vr1_virmanin_tek_bacagi_silinince_para_yoktan_var_olmuyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'SL1 · flask_app.py blok 1',
     r'''                'sevkiyat_id': s.sevkiyat_id,
                'musteri': s.musteri, 'musteri_ulke': s.musteri_ulke,
                'satis_tarihi': s.satis_tarihi.isoformat() if s.satis_tarihi else None,
                'teslim_tarihi': s.teslim_tarihi.isoformat() if s.teslim_tarihi else None,
''',
     r'''                'sevkiyat_id': s.sevkiyat_id,
                'musteri': s.musteri, 'musteri_ulke': s.musteri_ulke,
                'satis_tarihi': s.satis_tarihi.isoformat() if s.satis_tarihi else None,
                'teslim_tarihi': s.teslim_tarihi.isoformat() if s.teslim_tarihi else None,
                # SL1: ekran satışları FATURAYA göre gruplayacak.
                # `fatura_no` tek başına zayıf bir anahtar (iki ayrı
                # belge aynı numarayı taşıyabilir); kimlik kesin.
                'fatura_id': s.fatura_id,
'''),
    ('flask_app.py', 'SL1 · flask_app.py blok 2',
     r'''        return jsonify({
            'ok': True,
            'adet': len(sklar),
''',
     r'''        # ── SL1 · SATIŞ SAYISI, KAYIT SAYISI DEĞİL ──
        # Satış kaydı KALEM başına üretiliyor. `len(sklar)` iki
        # plakalı tek satışa "2" diyordu. Liste artık faturaya göre
        # grupluyor ve "1 satış" yazıyor; bu uç düzeltilmeseydi
        # AYNI EKRANDA satır "1", özet "2" derdi — EM2'de düzelttiğimiz
        # "satırı ve özeti aynı sayıyı söylemiyor" durumunun kopyası.
        # Faturasız kayıt kendi başına bir satıştır.
        _satislar = {(s.fatura_id or s.fatura_no or f'tek:{s.id}')
                     for s in sklar}

        return jsonify({
            'ok': True,
            'adet': len(_satislar),
            'kalem_adedi': len(sklar),
'''),
    ('templates/satislar.html', 'SL1 · templates/satislar.html blok 1',
     r'''function kpiCiz() {
  const ciro = TUM.reduce((a, s) => a + (s.tutar_usd || 0), 0);
  const kar = TUM.reduce((a, s) => a + (s.kar_usd || 0), 0);
  const marj = ciro > 0 ? kar / ciro * 100 : 0;
  const fatursuz = TUM.filter(s => !s.fatura_no);
  document.getElementById('kCiro').innerHTML = para(ciro).replace(' $', '<small>$</small>');
  document.getElementById('kCiroEk').textContent = TUM.length + ' satış';
''',
     r'''/* ══════════════════════════════════════════════════════════════════
   SL1 · LİSTE SATIŞ BAŞINA, KALEM BAŞINA DEĞİL

   Satış kaydı STOK/KALEM başına üretiliyor ve bu DOĞRU: ürün bazlı
   kârlılık ondan besleniyor (F1/F2, DV1). Ama liste o kayıtları
   olduğu gibi basınca iki plakalı tek bir satış ekranda İKİ SATIR
   görünüyordu; aynı fatura no, aynı müşteri, aynı tarih. Kullanıcı
   iki satış yaptığını sanıyor.

   Artık satırlar FATURAYA göre toplanıyor. Faturasız kayıt kendi
   başına bir gruptur (birleştirecek bir belge yok).

   Kalem bilgisi KAYBOLMUYOR: çok kalemli bir gruba tıklayınca
   kalemler tek tek listeleniyor ve her biri kendi detayını açıyor.
   Tek kalemli grup doğrudan detaya gidiyor — araya boş bir adım
   koymak, en sık durumu yavaşlatmak olurdu.
   ═══════════════════════════════════════════════════════════════ */
function gruplaSatislar(kayitlar) {
  const harita = new Map();
  for (const x of kayitlar) {
    /* Faturasız kayıt kendi başına: birleştirecek belge yok. */
    const anahtar = x.fatura_id || x.fatura_no || ('tek:' + x.id);
    if (!harita.has(anahtar)) {
      harita.set(anahtar, {
        anahtar,
        kalemler: [],
        musteri: x.musteri, musteri_ulke: x.musteri_ulke,
        fatura_no: x.fatura_no, fatura_id: x.fatura_id,
        siparis_id: x.siparis_id,
        satis_tarihi: x.satis_tarihi,
        tutar_usd: 0, maliyet_usd: 0, kar_usd: 0,
      });
    }
    const g = harita.get(anahtar);
    g.kalemler.push(x);
    g.tutar_usd += (x.tutar_usd || 0);
    g.maliyet_usd += (x.maliyet_usd || 0);
    g.kar_usd += (x.kar_usd || 0);
    /* En eski tarih grubun tarihi: aynı faturanın kalemleri aynı
       gün olur, ama veri bozuksa en erkeni göstermek dürüst. */
    if (x.satis_tarihi && (!g.satis_tarihi || x.satis_tarihi < g.satis_tarihi))
      g.satis_tarihi = x.satis_tarihi;
  }
  for (const g of harita.values()) {
    g.marj = g.tutar_usd > 0 ? g.kar_usd / g.tutar_usd * 100 : 0;
    const cinsler = [...new Set(g.kalemler.map(k => k.cins).filter(Boolean))];
    g.cins_ozet = cinsler.length === 1 ? cinsler[0]
      : (cinsler.length ? cinsler[0] + ' +' + (cinsler.length - 1) : '—');
    /* Miktar yalnız BİRİMLER AYNIYSA toplanır. 100 m² + 20 ton
       toplanıp "120 m²" yazmak, DV1'de düzelttiğimiz hatanın
       ekrandaki kopyası olurdu. */
    const birimler = [...new Set(g.kalemler.map(k => k.birim).filter(Boolean))];
    if (birimler.length === 1) {
      g.miktar_ozet = g.kalemler.reduce((a, k) => a + (k.miktar || 0), 0)
        .toLocaleString('tr-TR') + ' ' + birimler[0];
    } else {
      g.miktar_ozet = g.kalemler.length + ' kalem';
    }
  }
  return [...harita.values()];
}

function kpiCiz() {
  const ciro = TUM.reduce((a, s) => a + (s.tutar_usd || 0), 0);
  const kar = TUM.reduce((a, s) => a + (s.kar_usd || 0), 0);
  const marj = ciro > 0 ? kar / ciro * 100 : 0;
  const fatursuz = TUM.filter(s => !s.fatura_no);
  document.getElementById('kCiro').innerHTML = para(ciro).replace(' $', '<small>$</small>');
  /* SL1: KAYIT değil SATIŞ sayılır. İki plakalı tek satış "2 satış"
     yazıyordu; kullanıcı iki satış yaptığını sanıyordu. */
  const satisSayisi = gruplaSatislar(TUM).length;
  document.getElementById('kCiroEk').textContent = satisSayisi + ' satış'
    + (TUM.length !== satisSayisi ? ' · ' + TUM.length + ' kalem' : '');
'''),
    ('templates/satislar.html', 'SL1 · templates/satislar.html blok 2',
     r'''  let liste = TUM.filter(x => {
''',
     r'''  /* SL1 · süzgeçler KALEM üzerinde çalışır, sonra gruplanır.
     Önce gruplayıp sonra süzmek, "cins = X" süzgecinde X içermeyen
     kalemleri de gruba takılı bırakırdı. */
  let kalemler = TUM.filter(x => {
'''),
    ('templates/satislar.html', 'SL1 · templates/satislar.html blok 3',
     r'''  liste.sort((a, b) => (b.satis_tarihi || '').localeCompare(a.satis_tarihi || ''));

  const g = document.getElementById('govde');
  g.innerHTML = liste.length ? liste.map(x => {
    const m = marjBul(x);
    const renk = m >= 25 ? '--verde' : m >= 15 ? '--kehribar' : '--kirmizi';
    return `
    <tr style="border-left-color:var(${renk})" onclick="detayAc('${kacar(x.id)}')">
      <td class="mono" style="font-size:.8rem">${kacar(x.id)}
        <div class="ikincil">${x.fatura_no
          ? kacar(x.fatura_no)
          : '<span style="color:var(--kehribar);font-weight:600">faturasız</span>'}</div></td>
      <td><strong>${kacar(x.musteri || '—')}</strong>
        ${x.musteri_ulke ? '<div class="ikincil">' + kacar(x.musteri_ulke) + '</div>' : ''}</td>
      <td>${kacar(x.cins || '—')}
        <div class="ikincil">${kacar(x.stok_tip || '')} · ${(x.miktar || 0).toLocaleString('tr-TR')} ${kacar(x.birim || '')}</div></td>
''',
     r'''  const liste = gruplaSatislar(kalemler);
  liste.sort((a, b) => (b.satis_tarihi || '').localeCompare(a.satis_tarihi || ''));

  const g = document.getElementById('govde');
  g.innerHTML = liste.length ? liste.map(x => {
    const m = x.marj;
    const renk = m >= 25 ? '--verde' : m >= 15 ? '--kehribar' : '--kirmizi';
    const cok = x.kalemler.length > 1;
    return `
    <tr style="border-left-color:var(${renk})" onclick="grupAc('${kacar(x.anahtar)}')">
      <td class="mono" style="font-size:.8rem">${kacar(
        cok ? (x.fatura_no || x.anahtar) : x.kalemler[0].id)}
        <div class="ikincil">${x.fatura_no
          ? (cok ? x.kalemler.length + ' kalem' : kacar(x.fatura_no))
          : '<span style="color:var(--kehribar);font-weight:600">faturasız</span>'}</div></td>
      <td><strong>${kacar(x.musteri || '—')}</strong>
        ${x.musteri_ulke ? '<div class="ikincil">' + kacar(x.musteri_ulke) + '</div>' : ''}</td>
      <td>${kacar(x.cins_ozet)}
        <div class="ikincil">${kacar(x.miktar_ozet)}</div></td>
'''),
    ('templates/satislar.html', 'SL1 · templates/satislar.html blok 4',
     r'''  }).join('') : '<tr><td colspan="7" class="bos">Satış kaydı yok.</td></tr>';
''',
     r'''  }).join('') : '<tr><td colspan="7" class="bos">Satış kaydı yok.</td></tr>';
}

/* SL1 · gruba tıklanınca: tek kalemliyse doğrudan detay, çok
   kalemliyse kalemler listesi. */
function grupAc(anahtar) {
  const liste = gruplaSatislar(TUM);
  const g = liste.find(x => x.anahtar === anahtar);
  if (!g) return;
  if (g.kalemler.length === 1) { detayAc(g.kalemler[0].id); return; }

  const alan = (l, v, mono) => `<div class="alan"><label>${l}</label><div class="${mono ? 'mono' : ''}">${v || '—'}</div></div>`;
  const renk = g.marj >= 25 ? '--verde' : g.marj >= 15 ? '--kehribar' : '--kirmizi';
  const satirlar = g.kalemler.map(k => {
    const km = marjBul(k);
    return `
    <div class="blok" style="display:flex;align-items:center;gap:12px;
         padding:10px 12px;border-bottom:1px solid var(--cizgi);cursor:pointer"
         onclick="detayAc('${kacar(k.id)}')">
      <div style="flex:1;min-width:0">
        <div style="font-weight:600">${kacar(k.cins || '—')}${
          k.ozellik ? ' · ' + kacar(k.ozellik) : ''}</div>
        <div class="ikincil mono" style="font-size:.76rem">${kacar(k.id)} · ${
          kacar(k.stok_tip || '')} · ${(k.miktar || 0).toLocaleString('tr-TR')} ${
          kacar(k.birim || '')}${k.stok_no || k.stok_id
            ? ' · ' + kacar(k.stok_no || k.stok_id) : ''}</div>
      </div>
      <div class="mono sag" style="font-weight:600">${para2(k.tutar_usd)}</div>
      <div class="mono sag" style="width:92px;color:var(--verde)">${para2(k.kar_usd)}</div>
      <div class="mono sag" style="width:62px">%${km.toFixed(1).replace('.', ',')}</div>
    </div>`;
  }).join('');

  const govde = `
    <div class="alan-grid">
      ${alan('Tutar', para2(g.tutar_usd), true)}
      ${alan('Maliyet', para2(g.maliyet_usd), true)}
      ${alan('Kâr', `<span style="color:var(--verde);font-weight:700">${para2(g.kar_usd)}</span>`)}
      ${alan('Marj', `<span style="font-weight:700;color:var(${renk})">%${g.marj.toFixed(1).replace('.', ',')}</span>`)}
      ${alan('Satış Tarihi', kacar(g.satis_tarihi || '—'), true)}
      ${alan('Fatura', g.fatura_no
        ? kacar(g.fatura_no)
        : '<span class="rozet rz-kehribar">Faturasız</span>')}
      ${g.siparis_id ? alan('Sipariş', kacar(g.siparis_id), true) : ''}
      ${alan('Kalem', g.kalemler.length + ' ürün', true)}
    </div>
    <div class="panel" style="margin-top:14px;padding:0;overflow:hidden">
      <div style="padding:10px 12px;font-size:.78rem;font-weight:700;
           letter-spacing:.04em;text-transform:uppercase;color:var(--soluk);
           border-bottom:1px solid var(--cizgi)">Kalemler · tıkla, detayı açılsın</div>
      ${satirlar}
    </div>
    <div id="msOzet" style="margin-top:14px"></div>`;

  const eylem = [];
  if (g.siparis_id)
    eylem.push(`<button class="blok-btn" onclick="location.href='/siparis'">Siparişi aç</button>`);
  eylem.push(`<button class="blok-btn" onclick="cekmeceKapat()">Kapat</button>`);
  cekmeceAc(kacar(g.musteri || anahtar),
            `${g.fatura_no || g.kalemler.length + ' kalem'} · ${g.satis_tarihi || ''}`,
            govde, eylem.join(''));
  musteriOzetiYukle(g.musteri);
'''),
    ('templates/satislar.html', 'SL1 · templates/satislar.html blok 5',
     r'''      ${satir('Satış adedi', d.adet)}
''',
     r'''      ${satir('Satış adedi', d.adet
        + (d.kalem_adedi && d.kalem_adedi !== d.adet
           ? ' <span style="color:var(--soluk);font-weight:400">· '
             + d.kalem_adedi + ' kalem</span>' : ''))}
'''),
    ('tests/test_kritik.py', 'SL1 · tests/test_kritik.py blok 1',
     r'''        'yolu yok: ' + ', '.join(acik))
''',
     r'''        'yolu yok: ' + ', '.join(acik))


# ══════════════════════════════════════════════════════════════════
#  SL1 · SATIŞLAR LİSTESİ SATIŞ BAŞINA, KALEM BAŞINA DEĞİL
#
#  İşin sahibi bildirdi: iki plakalı TEK satış, satışlar sekmesinde
#  İKİ KUTU olarak görünüyordu — aynı fatura no, aynı müşteri, aynı
#  tarih. Kullanıcı iki satış yaptığını sanıyor.
#
#  Satış kaydının kalem başına üretilmesi DOĞRU: ürün bazlı kârlılık
#  ondan besleniyor (F1/F2, DV1'de transit faturayı da o yola
#  soktuk). Yanlış olan, listenin o kayıtları olduğu gibi basması.
#
#  Düzeltirken aynı ekranda ikinci bir tutarsızlık çıktı: müşteri
#  özeti ucu da KAYIT sayıyordu. Liste "1 satış" derken özet "2"
#  diyecekti — EM2'de düzelttiğimiz "satır ve özet aynı sayıyı
#  söylemiyor" durumunun kopyası.
# ══════════════════════════════════════════════════════════════════
def test_sl1_musteri_ozeti_satis_sayiyor_kalem_degil():
    """Aynı faturanın kalemleri TEK satış sayılmalı."""
    from models import SatisKaydi, Fatura
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(Cari(id='SL1-MUS', unvan='SL1 ACAR',
                            cari_tip='Müşteri', para_birimi='USD'))
        db.session.add(Fatura(
            id='FT-SL1', fatura_no='SL1-001', cari_id='SL1-MUS',
            musteri='SL1 ACAR', yon='satis', durum='Kesildi',
            doviz='USD', toplam=1008, ara_toplam=1008,
            fatura_tarihi=date(2026, 10, 29)))
        # TEK faturanın İKİ kalemi
        for i in (1, 2):
            db.session.add(SatisKaydi(
                id=f'SK-SL1-{i}', cari_id='SL1-MUS', musteri='SL1 ACAR',
                cins='SL1 CEPPO', stok_tip='PLAKA', miktar=5.04,
                birim='m2', doviz='USD', tutar_usd=504, maliyet_usd=181.44,
                kar_usd=322.56, fatura_id='FT-SL1', fatura_no='SL1-001',
                satis_tarihi=date(2026, 10, 29)))
        db.session.commit()

    r = c.get('/api/satislar/musteri/SL1%20ACAR/ozet', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    j = r.get_json()
    # ESKI DAVRANIS: adet == 2
    assert j.get('adet') == 1, (
        f'adet {j.get("adet")} — iki kalemli TEK satış 1 sayılmalı')
    assert j.get('kalem_adedi') == 2, j
    assert float(j.get('toplam_usd') or 0) == 1008.0, j


def test_sl1_satis_listesi_fatura_kimligini_gonderiyor():
    """Ekran faturaya göre gruplayacak; kimlik gelmeli (AS2 sınıfı)."""
    c = istemci('admin', 'ADMIN')
    r = c.get('/api/satislar?per_page=300', headers=H)
    assert r.status_code == 200
    satirlar = (r.get_json() or {}).get('data') or []
    assert satirlar, 'satış kaydı yok, test anlamsız'
    assert 'fatura_id' in satirlar[0], (
        'ekran fatura_id ile gruplayacak ama sunucu göndermiyor')


def test_sl1_ekran_satislari_gruplayip_kalemleri_gosteriyor():
    """Gruplama ekranda olmalı ve kalem bilgisi kaybolmamalı."""
    import io as _io
    s = _io.open(os.path.join(KOK, 'templates', 'satislar.html'),
                 encoding='utf-8').read()
    assert 'function gruplaSatislar(' in s, 'gruplama yok'
    assert 'function grupAc(' in s, 'grup detayı yok'
    # Tek kalemli grup DOĞRUDAN detaya gitmeli (araya boş adım girmesin)
    assert 'if (g.kalemler.length === 1) { detayAc(' in s
    # Kalem satırları kendi detayını açmalı
    assert "onclick=\"detayAc('${kacar(k.id)}')\"" in s
    # KPI kayıt değil satış saymalı
    assert 'gruplaSatislar(TUM).length' in s


def test_sl1_farkli_birimler_toplanmiyor():
    """m² + ton toplanıp tek birimle yazılmamalı (DV1 dersi)."""
    import io as _io
    s = _io.open(os.path.join(KOK, 'templates', 'satislar.html'),
                 encoding='utf-8').read()
    # Birim sayısı 1 DEĞİLSE miktar toplanmaz, "N kalem" yazılır
    i = s.find('function gruplaSatislar(')
    govde = s[i:i + 3000]
    assert 'birimler.length === 1' in govde, (
        'miktar birim ayrımı yapmadan toplanıyor olabilir')
    assert "g.kalemler.length + ' kalem'" in govde
'''),
]

def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA SL1 — SATIŞLAR LİSTESİ SATIŞ BAŞINA')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    # ── --yaz-gecici ──
    # base64 gömülü iki dosyayı /tmp'ye çıkarır, PROJEYE DOKUNMAZ.
    # Tam dosya yazan bir yamayı önce okumak istemek yerinde bir
    # istek; "uygula da sonra bak" demek yanlış olurdu.
    if '--yaz-gecici' in sys.argv:
        hedef = tempfile.mkdtemp(prefix='sl1-')
        print()
        for ad in TAM_YAZILAN:
            p = os.path.join(hedef, ad)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(_tam_dosya(ad))
            print(f'  {p}')
        print()
        print('  Projeye DOKUNULMADI. Okuduktan sonra:')
        print('    python3 yama_sl1.py            # rapor')
        print('    python3 yama_sl1.py --uygula')
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
        print('  ⊙ Yama SL1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_sl1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_sl1'
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
    print('    venv/bin/python -m pytest tests/test_kritik.py -q   # 323')
    print()
    print('  ONEMLI — SIRAYLA:')
    print('    1) sudo systemctl restart milestone-erp')
    print('    2) tarayicida Ctrl+F5')
    print('    Python kodu surec baslarken yukleniyor; restart')
    print('    etmeden yamanin hicbir etkisi gorunmez. KDV sorunu')
    print('    bundandi.')
    print()
    print('  NE DEGISTI')
    print('    · Satislar listesi FATURAYA gore grupluyor: iki')
    print('      plakali tek satis artik TEK satir.')
    print('    · Cok kalemli satira tiklayinca kalemler listeleniyor,')
    print('      her biri kendi detayini aciyor.')
    print('    · KPI "1 satis · 2 kalem" diyor.')
    print('    · Musteri ozeti de satis sayiyor (liste 1 derken ozet')
    print('      2 demesin).')
    print('    · Farkli birimler toplanmiyor (m2 + ton).')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

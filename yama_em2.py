#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA EM2 — DEPO DEĞERİNDE 900 $ FAZLA · SON İKİ UÇ BAĞLANDI
=============================================================

ÖNKOŞUL: **yama_ek1.py uygulanmış olmalı.** Betik denetliyor.
Şema yok, göç yok.

Yeni bir sınıf taradım: **aynı para toplamı, farklı süzgeç.** EM1,
AF1, TS1 ve UN1 hep o kutudan çıkmıştı. Tarama dört aday verdi,
üçü gerçek çıktı — ve üçü de EM1'in kendisi.

═══ 1 · EM1'İN KAPISI ÜÇ YERDE DAHA ATLANIYORDU ═══

EM1'de "maliyete giren gider" kuralını `_maliyet_sayilir()`e
bağlamıştık: aktif olmalı VE maliyet dışı tiplerden (Devreden KDV,
İade KDV) olmamalı. Üç yer o kapıdan geçmiyordu — `aktif` bakıyor,
TİP süzgecini atlıyordu:

      api_dashboard_ozet      depodaki stok değeri
      api_dashboard_detay     stok kırılımı
      api_stok_liste          GENEL TOPLAM

Sonuncusu en kötüsü: **aynı uç noktada** sayfa satırları
`_maliyet_sayilir()` kullanıyor, genel toplam kullanmıyordu. Yani
aynı ekranın satırı ile özeti farklı sayıyordu.

ÖLÇÜLDÜ — 6.000 $ blok · 1.000 aktif + 400 iptal + 250 tipsiz +
900 Devreden KDV (maliyete girmesi gereken: 1.250):

      maliyet raporu          7.250,00  ✓
      stok listesi · satır    7.250,00  ✓
      stok listesi · ÖZET     8.150,00  ✗
      dashboard · stok        8.150,00  ✗

Fark tam 900 $: devreden KDV depo değerine girmiş. Devreden KDV
devletten alacağındır, malın maliyeti değil.

Düzeltmeden sonra dördü de **7.250,00**.

  BEKÇİ: `Maliyet.usd_karsilik` toplayan her yer artık ya ortak
  kapıdan geçiyor ya da KDV'yi BİLEREK sayan bir tip eşitliği
  taşıyor. Üçüncü bir hâl testi kırar.

═══ 2 · SON İKİ UÇ BAĞLANDI ═══

**Satış → Fatura bilgisi.** `PATCH /api/satislar/<id>/fatura-bilgi`
yazılıydı, çağıran yoktu. "Düzenle"den AYRI bir pencere, çünkü iki
uç ayrı sorular soruyor:

  · `PUT` para alanları — satış bir FATURADAN doğduysa REDDEDİYOR
    (belge ile kayıt ayrışmasın)
  · `PATCH` fatura no / tarih / teslim / not — paraya dokunmuyor,
    o yüzden faturalı satışta da çalışıyor

Yani faturadan doğmuş bir satışın fatura numarasını yalnız buradan
düzeltebilirsin. Test, ucun tutarı kabul ETMEDİĞİNİ de tutuyor:
999.999 gönderdim, tutar 1.000'de kaldı.

**Cari → kısaltma önerisi.** `GET /api/cari/kisaltma_oner` da
bağlanmamıştı. Kısaltma belge numaralarının temeli
(SIP-STN26-03, PI-STN26-01) ve elle yazılırken tutarsız kalıyordu.
Ünvan alanından çıkınca, kısaltma BOŞSA ve yalnızca BİR KEZ
öneriliyor — kullanıcının yazdığının üstüne geçmek bu formdaki en
kötü davranış olurdu.

  Kural ekranda TEKRARLANMIYOR, sunucuya soruluyor. Testi bunu da
  tutuyor: ekran kendi başına türetmeye kalkarsa kırılır.

═══ 3 · YANLIŞ BİR ŞEY DÜZELTMEYE KALKTIM ═══

Fatura bilgisi modalını yazarken satış listesinin `notlar`
göndermediğini "gördüm" — 60 satırlık bir grep penceresiyle. Buna
göre modalin notu boş okuyup kaydederken sileceğini, üstelik aynı
hatanın SD4'ün "Düzenle" modalında da olduğunu düşündüm.

Ölçtüm: **liste `notlar`'ı gönderiyor.** Benim penceremin dışında
kalmış. Alan doluyor, SD4 de sağlam. Düzeltmeye kalksaydım olmayan
bir hata için kod ekleyecektim.

Ölçmeden "buldum" dememek bu yüzden.

═══ 4 · KISALTMA ALANI MÜŞTERİDE GÖRÜNMÜYORDU ═══

Öneriyi bağlarken fark ettim: `cKisaltma` alanı `tedarikciAlan`
kapsayıcısının İÇİNDE ve o kapsayıcı `display:none` ile başlıyor —
yalnız Tedarikçi/Üretici rolünde açılıyor.

Oysa sunucu kısaltmayı HER cari için üretiyor: belge numarası
istendiğinde yoksa unvandan türetip kaydediyor (flask_app
2244-2256). Yani bir MÜŞTERİ için o harfler üretiliyor,
`SIP-XXX26-03` diye sipariş numarasına yazılıyor, müşteri belgede
görüyor — ama sen ne görüyor ne değiştirebiliyordun.

Alanın yanındaki RN1 yorumu zaten "kısaltma artık HER cari için
kullanılıyor" diyor. Kural değişmiş, yorum güncellenmiş, EKRAN
güncellenmemiş. Alan kapsayıcının dışına taşındı; artık her
cariden görünüyor.

GÖRÜLDÜ: müşteri rolünde alan görünür · "ABC Marble Stone LLC" →
AMS önerildi · elle yazılan XYZ, ünvan değişince KORUNDU.

═══ DOĞRULANDI ═══
  281 test geçti (276 + 5). Dördü taban üzerinde BAŞARISIZ oluyor;
  beşincisi ucun sözleşmesini tutuyor (uç zaten doğruydu, eksik
  olan ekrandı).

  js · form · akış · bağlam · firma denetimleri temiz; kur ve
  sessiz denetimlerinin bulguları tabanla aynı.

DOSYALAR
--------
  flask_app.py             üç toplam ortak kapıya bağlandı
  templates/satislar.html  Fatura bilgisi penceresi
  templates/cari.html      kısaltma önerisi + alan görünürlüğü
  tests/test_kritik.py     5 yeni test

KULLANIM
--------
  python3 yama_em2.py            # RAPOR
  python3 yama_em2.py --uygula
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
    'flask_app.py': 'EM2 · SATIR ile ÖZET AYNI ŞEYİ SAYSIN',
    'templates/satislar.html': 'EM2 · FATURA BİLGİSİ',
    'templates/cari.html': 'EM2 · KISALTMA ÖNERİSİ',
    'tests/test_kritik.py': 'def test_em2_stok_listesinin_satiri_ve_ozeti_ayni_sayiyor',
}
ONKOSUL = {
    'flask_app.py': 'EK1 · HAREKETİ OLAN KASANIN DÖVİZİ DEĞİŞTİRİLEMEZ',
    'tests/test_kritik.py': 'def test_ek1_hareketli_kasanin_dovizi_degistirilemez',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'EM2 · flask_app.py blok 1',
     r'''                        Maliyet.aktif.is_(True)).group_by(
''',
     r'''                        # ══════════════════════════════════════════
                        #  EM2 · SATIR ile ÖZET AYNI ŞEYİ SAYSIN
                        #
                        #  Bu uç noktada iki toplam var: sayfa
                        #  satırları `_maliyet_sayilir()` kullanıyordu,
                        #  GENEL TOPLAM kullanmıyordu. Yani aynı
                        #  ekranın satırı ile özeti farklı sayıyordu.
                        #
                        #  ÖLÇÜLDÜ — 6.000 $ blok · 1.000 aktif + 400
                        #  iptal + 250 tipsiz + 900 Devreden KDV:
                        #      satır  7.250,00    özet  8.150,00
                        #  Fark 900 $: devreden KDV depo değerine
                        #  girmiş. Maliyet raporu 7.250 diyordu.
                        # ══════════════════════════════════════════
                        *_maliyet_sayilir()).group_by(
'''),
    ('flask_app.py', 'EM2 · flask_app.py blok 2',
     r'''                    Maliyet.aktif.is_(True)).group_by(Maliyet.baglanti_id).all():
                _mal_map[_mid] = float(_mt or 0)
''',
     r'''                    # EM2: EM1'in kapisi. Burasi `aktif` bakiyor ama
                    # TIP suzgecini atliyordu — Devreden/Iade KDV
                    # depo degerine giriyordu. OLCULDU: 900 $ fazla.
                    *_maliyet_sayilir()).group_by(Maliyet.baglanti_id).all():
                _mal_map[_mid] = float(_mt or 0)
'''),
    ('flask_app.py', 'EM2 · flask_app.py blok 3',
     r'''                    Maliyet.aktif.is_(True)).group_by(Maliyet.baglanti_id).all():
''',
     r'''                    # EM2: EM1'in kapisi. Burasi `aktif` bakiyor ama
                    # TIP suzgecini atliyordu — Devreden/Iade KDV
                    # depo degerine giriyordu. OLCULDU: 900 $ fazla.
                    *_maliyet_sayilir()).group_by(Maliyet.baglanti_id).all():
'''),
    ('templates/satislar.html', 'EM2 · templates/satislar.html blok 1',
     r'''  eylem.push(`<button class="blok-btn" onclick="cekmeceKapat()">Kapat</button>`);
''',
     r'''  /* EM2: `PATCH /api/satislar/<id>/fatura-bilgi` de bağlanmamıştı.
     "Düzenle"den AYRI, çünkü iki uç AYRI sorular soruyor:
       · PUT  para alanları — satış bir FATURADAN doğduysa REDDEDİYOR
                              (belge ile kayıt ayrışmasın)
       · PATCH fatura no / tarih / teslim / not — paraya dokunmuyor,
                              o yüzden faturalı satışta da çalışıyor
     Yani faturadan doğmuş bir satışın fatura numarasını yalnız
     buradan düzeltebilirsin. */
  if (yazabilir('satis') || yazabilir('fatura'))
    eylem.push(`<button class="blok-btn" onclick="sFaturaBilgiAc('${kacar(id)}')">Fatura bilgisi</button>`);
  eylem.push(`<button class="blok-btn" onclick="cekmeceKapat()">Kapat</button>`);
'''),
    ('templates/satislar.html', 'EM2 · templates/satislar.html blok 2',
     r'''function sDuzKapat() {
''',
     r'''/* ═══ EM2 · FATURA BİLGİSİ ═══ */
let SFB_ID = null;

function sFaturaBilgiAc(id) {
  const x = TUM.find(s => s.id === id);
  if (!x) return;
  SFB_ID = id;
  cekmeceKapat();
  document.getElementById('sFbAlt').textContent =
    `${x.id} · ${kacar(x.musteri || '')}`;
  const koy = (k, v) => {
    const el = document.getElementById(k);
    if (el) el.value = v || '';
  };
  koy('sFbNo', x.fatura_no);
  koy('sFbTarih', (x.fatura_tarihi || '').slice(0, 10));
  koy('sFbTeslim', (x.teslim_tarihi || '').slice(0, 10));
  koy('sFbNot', x.notlar);
  document.getElementById('sFbModal').classList.add('acik');
}

function sFbKapat() {
  document.getElementById('sFbModal').classList.remove('acik');
  SFB_ID = null;
}

async function sFaturaBilgiKaydet() {
  if (!SFB_ID) return;
  const btn = document.getElementById('sFbKaydet');
  btn.disabled = true; btn.textContent = 'Kaydediliyor…';
  try {
    const d = await api(
      `/api/satislar/${encodeURIComponent(SFB_ID)}/fatura-bilgi`,
      { method: 'PATCH', body: JSON.stringify({
          fatura_no: document.getElementById('sFbNo').value.trim(),
          fatura_tarihi: document.getElementById('sFbTarih').value || null,
          teslim_tarihi: document.getElementById('sFbTeslim').value || null,
          notlar: document.getElementById('sFbNot').value
        }) });
    bildir(d.mesaj || 'Fatura bilgisi güncellendi');
    sFbKapat();
    await yukle();
  } catch (e) { /* api() bildirdi */ }
  finally { btn.disabled = false; btn.textContent = 'Kaydet'; }
}

function sDuzKapat() {
'''),
    ('templates/satislar.html', 'EM2 · templates/satislar.html blok 3',
     r'''<div class="modal-ortu" id="sDuzModal" onclick="if(event.target===this)sDuzKapat()">
''',
     r'''<!-- ═══ EM2 · FATURA BİLGİSİ ═══
     Yalnız belge alanları: tutar, maliyet ve kâr buradan
     DEĞİŞMEZ. Uç da öyle kurulmuş. -->
<div class="modal-ortu" id="sFbModal" onclick="if(event.target===this)sFbKapat()">
  <div class="modal" role="dialog" aria-label="Fatura bilgisi">
    <div class="modal-bas">
      <h3>Fatura Bilgisi</h3>
      <p id="sFbAlt">—</p>
    </div>
    <div class="modal-gov">
      <div class="form-satir">
        <div class="form-alan"><label>Fatura No</label>
          <input id="sFbNo" placeholder="MST-2026-001"></div>
        <div class="form-alan"><label>Fatura Tarihi</label>
          <input id="sFbTarih" type="date"></div>
      </div>
      <div class="form-satir">
        <div class="form-alan"><label>Teslim Tarihi</label>
          <input id="sFbTeslim" type="date"></div>
        <div class="form-alan"><label>Not</label>
          <input id="sFbNot" placeholder="opsiyonel"></div>
      </div>
      <div style="font-size:.76rem;color:var(--soluk);line-height:1.5">
        Tutar, maliyet ve kâr buradan değişmez — onlar "Düzenle"de.
        Satış bir faturadan doğduysa tutarı hiç değiştirilemez, ama
        belge bilgisini buradan düzeltebilirsin.
      </div>
    </div>
    <div class="modal-alt">
      <button class="iptal-btn" onclick="sFbKapat()">Vazgeç</button>
      <button class="btn-yeni" id="sFbKaydet" onclick="sFaturaBilgiKaydet()">Kaydet</button>
    </div>
  </div>
</div>

<div class="modal-ortu" id="sDuzModal" onclick="if(event.target===this)sDuzKapat()">
'''),
    ('templates/cari.html', 'EM2 · templates/cari.html blok 1',
     r'''        <div class="form-alan"><label>Ünvan <span style="color:var(--kirmizi)">*</span></label><input id="cUnvan" placeholder="ABC Marble LLC"></div>
''',
     r'''        <div class="form-alan"><label>Ünvan <span style="color:var(--kirmizi)">*</span></label><input id="cUnvan" placeholder="ABC Marble LLC" onblur="kisaltmaOner()"></div>
'''),
    ('templates/cari.html', 'EM2 · templates/cari.html blok 2',
     r'''        <div class="form-alan" style="margin-bottom:12px">
          <!-- RN1: kısaltma artık HER cari için kullanılıyor — belge
               numaraları bundan üretiliyor (SIP-STN26-03). Boş bırakılırsa
               unvandan türetilir ve buraya yazılır. -->
''',
     r'''        
      </div>
      <div class="form-alan" style="margin-bottom:12px" id="kisaltmaAlan">
          <!-- RN1: kısaltma artık HER cari için kullanılıyor — belge
               numaraları bundan üretiliyor (SIP-STN26-03). Boş bırakılırsa
               unvandan türetilir ve buraya yazılır.

               EM2: AMA BU ALAN YALNIZ TEDARİKÇİ/ÜRETİCİ ROLÜNDE
               GÖRÜNÜYORDU. `tedarikciAlan` kapsayıcısı içindeydi ve o
               kapsayıcı `display:none` ile başlıyor. Yani bir
               MÜŞTERİ için sunucu kısaltmayı kendi üretiyordu
               (flask_app 2244-2256, belge numarası istendiğinde) ama
               kullanıcı onu ne görüyor ne değiştirebiliyordu — oysa
               o harfler müşterinin gördüğü sipariş/proforma/fatura
               numarasında yazıyor.

               RN1 kuralı değiştirmiş, işaret güncellenmiş, ekran
               güncellenmemiş. Alan artık kapsayıcının DIŞINDA ve
               `tipDegisti()` onu ayrıca yönetmiyor. -->
'''),
    ('templates/cari.html', 'EM2 · templates/cari.html blok 3',
     r'''        </div>
      </div>
    </div>
''',
     r'''        </div>
    </div>
'''),
    ('templates/cari.html', 'EM2 · templates/cari.html blok 4',
     r'''function formAc(c) {
''',
     r'''/* ═══ EM2 · KISALTMA ÖNERİSİ ═══
   `GET /api/cari/kisaltma_oner` yazılıydı, hiçbir ekran
   çağırmıyordu. Kısaltma belge numaralarının temeli
   (SIP-STN26-03, PI-STN26-01); elle yazılırken tutarsız
   kalıyordu.

   YALNIZCA BOŞ ALANA yazıyor ve bir kez: kullanıcının yazdığı
   kısaltmanın üstüne geçmek, formdaki en kötü davranış olurdu.
   Sunucu kuralı tek yerde — 3 harfe tamamlama, kelime sayısına
   göre türetme — ekran onu TEKRARLAMIYOR, soruyor. */
let KISALTMA_ONERILDI = false;

async function kisaltmaOner() {
  const el = document.getElementById('cKisaltma');
  if (!el || el.value.trim() || KISALTMA_ONERILDI) return;
  const unvan = (document.getElementById('cUnvan').value || '').trim();
  if (unvan.length < 2) return;
  try {
    const d = await api('/api/cari/kisaltma_oner?unvan='
                        + encodeURIComponent(unvan));
    if (d && d.kisaltma && !el.value.trim()) {
      el.value = d.kisaltma;
      KISALTMA_ONERILDI = true;
      el.style.transition = 'background .4s';
      el.style.background = 'var(--verde-acik)';
      setTimeout(() => { el.style.background = ''; }, 900);
    }
  } catch (e) { /* oneri ikincil — sessiz gec */ }
}

function formAc(c) {
'''),
    ('templates/cari.html', 'EM2 · templates/cari.html blok 5',
     r'''  firmaKutulariniDoldur(c ? (c.firmalar || []) : null);   // MF6
''',
     r'''  KISALTMA_ONERILDI = false;
  firmaKutulariniDoldur(c ? (c.firmalar || []) : null);   // MF6
'''),
    ('tests/test_kritik.py', 'EM2 · tests/test_kritik.py blok 1',
     r'''        'düzenleme modalı var olmayan bir alanı soruyor'
''',
     r'''        'düzenleme modalı var olmayan bir alanı soruyor'


# ══════════════════════════════════════════════════════════════════
#  EM2 · EM1'İN KAPISI ÜÇ YERDE DAHA ATLANIYORDU
#
#  EM1'de "maliyete giren gider" kuralı `_maliyet_sayilir()`e
#  bağlanmıştı. Yeni tarama (aynı para toplamı, farklı süzgeç) üç
#  yerin o kapıdan geçmediğini buldu: iki dashboard toplamı ve
#  STOK LİSTESİNİN GENEL TOPLAMI.
#
#  Sonuncusu en kötüsü: aynı uç noktada sayfa satırları
#  `_maliyet_sayilir()` kullanıyordu, genel toplam kullanmıyordu.
#  Aynı ekranın satırı ile özeti farklı sayıyordu.
#
#  ÖLÇÜLDÜ — 6.000 $ blok · 1.000 aktif + 400 iptal + 250 tipsiz
#  + 900 Devreden KDV:
#      maliyet raporu          7.250,00  ✓
#      stok listesi · satır    7.250,00  ✓
#      stok listesi · ÖZET     8.150,00  ✗
#      dashboard · stok        8.150,00  ✗
#  Fark 900 $: devreden KDV depo değerine girmiş.
# ══════════════════════════════════════════════════════════════════
_EM2_T = date(2026, 1, 23)      # baska test bu gune kur yazmiyor


def _em2_kur():
    """6.000 $ blok + dört gider. Beklenen ek maliyet 1.250."""
    from models import DovizKur, Maliyet
    if not DovizKur.query.filter_by(doviz='USD', tarih=_EM2_T).first():
        db.session.add(DovizKur(doviz='USD', tarih=_EM2_T,
                                alis=40.0, satis=40.0, efektif=40.0))
    db.session.add(BlokStok(
        id='BLK-EM2', firma_id=1, blok_no='EM2-1', cins='EM2TEST',
        uretici='OCAK', mense='TURKIYE', boy=300, yukseklik=180, en=170,
        hacim_m3=9.18, tonaj=20, alis_fiyati=300, alis_fiyat_birim='ton',
        matrah=6000, doviz='USD', durum='Serbest', giris_tarihi=_EM2_T))
    db.session.flush()
    for i, (tip, tutar, aktif) in enumerate([
            ('Nakliye', 1000, True),          # sayilmali
            ('Gumruk', 400, False),           # IPTAL
            (None, 250, True),                # TIPSIZ — sayilmali
            ('Devreden KDV', 900, True)], 1):  # KDV — sayilmamali
        db.session.add(Maliyet(
            id=f'MYT-EM2-{i:04d}', firma_id=1, maliyet_tip=tip,
            baglanti_tip='stok', baglanti_id='BLK-EM2',
            tutar=tutar, doviz='USD', usd_karsilik=tutar,
            maliyet_tarihi=_EM2_T, aktif=aktif))
    db.session.commit()


def test_em2_stok_listesinin_satiri_ve_ozeti_ayni_sayiyor():
    """Sayfa satırları ile genel toplam aynı kuralı kullanmalı.

    Bu projede "aynı şeyin iki yerde farklı görünmesi" en kötü hata
    biçimi; burada iki yer AYNI EKRANDI."""
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _em2_kur()
    d = c.get('/api/stok?tip=BLOK&per_page=200', headers=H).get_json()
    satir = [x for x in (d.get('data') or []) if x.get('id') == 'BLK-EM2']
    assert satir, 'blok listede yok'
    assert abs(float(satir[0]['ek_maliyet_toplam']) - 1250) < 0.01, \
        satir[0]['ek_maliyet_toplam']
    assert abs(float(satir[0]['toplam_maliyet_usd']) - 7250) < 0.01, \
        satir[0]['toplam_maliyet_usd']
    # GENEL TOPLAM: bu bloğun payı 7.250 olmalı. Başka testlerin
    # stokları da sayıldığı için TOPLAMA değil, 900'ün girmediğine
    # bakıyoruz — iki toplamın farkı tam o kadardı.
    _ozet = d.get('ozet') or {}
    assert 'deger_usd' in _ozet, _ozet
    _tek = c.get('/api/stok?tip=BLOK&per_page=200&cins=EM2TEST',
                 headers=H).get_json()
    _o2 = (_tek.get('ozet') or {}).get('deger_usd')
    assert _o2 is not None, _tek.get('ozet')
    assert abs(float(_o2) - 7250) < 0.01, \
        f'özet {_o2} — satır 7.250 diyor; 8.150 ise devreden KDV girmiş'


def test_em2_dashboard_depo_degeri_kdv_saymiyor():
    """Dashboard'ın depo değeri maliyet raporuyla aynı olmalı."""
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        from models import BlokStok as _B
        if not db.session.get(_B, 'BLK-EM2'):
            _em2_kur()
    d = c.get('/api/dashboard/detay?k=stok', headers=H)
    assert d.status_code == 200, d.get_data(as_text=True)[:200]
    _j = d.get_json()
    _em2 = [x for x in (_j.get('satirlar') or [])
            if 'EM2TEST' in str(x.get('ad') or x.get('cins') or '')]
    assert _em2, [x.get('ad') for x in (_j.get('satirlar') or [])][:5]
    _t = float(_em2[0].get('usd') or _em2[0].get('tutar') or 0)
    assert abs(_t - 7250) < 0.01, \
        f'{_t} — 8.150 ise devreden KDV depo değerine girmiş'


def test_em2_depo_degeri_toplamlari_ortak_kapidan_geciyor():
    """`Maliyet.usd_karsilik` toplayan her yer aynı kapıyı kullanmalı.

    Bekçi: EM1'in kapısı (`_maliyet_sayilir`) atlanan yerlerde bu
    aile tekrar doğuyor. Tip süzgeci olmadan `aktif` tek başına
    yetmiyor — KDV kalemleri geçiyor."""
    import io as _io
    import re as _re
    m = _io.open(os.path.join(KOK, 'flask_app.py'),
                 encoding='utf-8').read().replace('\r\n', '\n')
    # `sum(Maliyet.usd_karsilik)` iceren her filter(...) zinciri
    kacak = []
    for _m in _re.finditer(r'func\.sum\(Maliyet\.usd_karsilik\)', m):
        _pencere = m[_m.start():_m.start() + 700]
        _son = _pencere.find('.all()')
        _zincir = _pencere[:_son if _son > 0 else 400]
        if '_maliyet_sayilir()' in _zincir:
            continue
        # KDV kalemlerini BILEREK sayan yer muaf: tip esitligi var
        if 'Maliyet.maliyet_tip ==' in _zincir:
            continue
        kacak.append(m[:_m.start()].count('\n') + 1)
    assert not kacak, \
        ('ortak kapıyı atlayan Maliyet toplamı — iptal/KDV kalemleri '
         'sızar: satır ' + ', '.join(str(x) for x in kacak))


# ══════════════════════════════════════════════════════════════════
#  EM2 · KALAN İKİ UÇ BAĞLANDI
# ══════════════════════════════════════════════════════════════════
def test_em2_satis_fatura_bilgisi_paraya_dokunmuyor():
    """`PATCH .../fatura-bilgi` belge alanlarını yazar, tutarı YAZMAZ.

    "Düzenle"den ayrı tutulmasının sebebi bu: PUT bir faturadan
    doğmuş satışta reddediyor; bu uç paraya dokunmadığı için orada
    da çalışıyor."""
    from models import SatisKaydi
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(SatisKaydi(
            id='SK-EM2', musteri='MUSTERI EM2', cins='EM2S',
            stok_tip='PLAKA', stok_id='PLK-EM2', miktar=10, birim='m2',
            birim_fiyat=100, tutar=1000, doviz='USD',
            satis_tarihi=_EM2_T, notlar='ILK NOT'))
        db.session.commit()
    r = c.patch('/api/satislar/SK-EM2/fatura-bilgi', headers=H, json={
        'fatura_no': 'EM2-FTR-9', 'fatura_tarihi': _EM2_T.isoformat(),
        'notlar': 'DUZELTILMIS NOT', 'tutar': 999999})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    with fa.app.app_context():
        s = db.session.get(SatisKaydi, 'SK-EM2')
        assert s.fatura_no == 'EM2-FTR-9', s.fatura_no
        assert s.notlar == 'DUZELTILMIS NOT', s.notlar
        # TUTAR DEGISMEDI — uc parayi kabul etmiyor
        assert abs(float(s.tutar) - 1000) < 0.01, \
            f'tutar {s.tutar} — bu uç paraya dokunmamalı'


def test_em2_kisaltma_onerisi_uctan_geliyor():
    """Kısaltma kuralı TEK yerde — ekran onu tekrarlamamalı."""
    import io as _io
    c = istemci('admin', 'ADMIN')
    for unvan, beklenen in (('ABC Marble Stone LLC', 'AMS'),
                            ('Stone USA', 'STU'),
                            ('Milestone', 'MIL')):
        d = c.get('/api/cari/kisaltma_oner?unvan='
                  + unvan.replace(' ', '%20'), headers=H).get_json()
        assert d.get('kisaltma') == beklenen, (unvan, d)
    cari = _io.open(os.path.join(KOK, 'templates', 'cari.html'),
                    encoding='utf-8').read()
    assert '/api/cari/kisaltma_oner' in cari, 'ekran ucu çağırmıyor'
    # Ekran kurali TEKRARLAMAMALI: kelime sayisina gore turetme
    # yalniz sunucuda olsun.
    _i = cari.index('async function kisaltmaOner')
    _govde = cari[_i:cari.index('\n}', _i)]
    assert 'split(' not in _govde, \
        'ekran kısaltmayı kendisi türetiyor — kural iki yerde olur'
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA EM2 — DEPO DEĞERİNDE 900 $ FAZLA · SON İKİ UÇ BAĞLANDI')
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
        print('    python3 yama_em2.py            # rapor')
        print('    python3 yama_em2.py --uygula')
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
        print('  ⊙ Yama EM2 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_em2.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_em2'
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
    print('    2) venv/bin/python -m pytest tests/test_kritik.py -q   # 281')
    print()
    print('  BAKILACAK YER')
    print('    1. Depo -> stok listesinin ALTINDAKI ozet ile satirlarin')
    print('       toplami artik ayni. Dashboard\'daki depo degeri de.')
    print('    2. Satislar -> bir satisa tikla -> "Fatura bilgisi".')
    print('       Faturadan dogmus satista "Duzenle" reddeder ama bu')
    print('       pencere calisir.')
    print('    3. Cari -> Yeni Cari -> unvani yaz, alandan cik:')
    print('       kisaltma onerilir. Elle yazdiginsa dokunmaz.')
    print()
    print('  RAKAM DEGISIYOR')
    print('    Depo degeri ve dashboard stok tutari DUSECEK: devreden')
    print('    ve iade KDV artik sayilmiyor. Dogru olan bu — maliyet')
    print('    raporu zaten oyle hesapliyordu.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

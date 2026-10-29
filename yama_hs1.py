#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA HS1 — HIZLI SATIŞ: EKRANIN SÖYLEDİĞİ İLE KAYDEDİLEN AYNI OLSUN
=====================================================================

ÖNKOŞUL: **yama_dv1.py uygulanmış olmalı.** Betik denetliyor.
Şema değişikliği YOK, göç YOK.

Kullanım:
    python3 yama_hs1.py              # rapor, dosyalara dokunmaz
    python3 yama_hs1.py --uygula
    venv/bin/python -m pytest tests/test_kritik.py -q     # 306

═══ ÖNCE: DV1 BU FORMU KIRIYORDU ═══

Önce bunu söyleyeyim. Hızlı satış formu dövizi yalnızca KALEMLERE
koyuyor, gövdeye koymuyordu. DV1'in kapısı kalemle belgeyi
karşılaştırdığı için, USD olmayan her hızlı satış artık

    "1. kalemin para birimi EUR, belgenin para birimi USD"

ile 400 alıyordu. Bu yama onu da kapatıyor: ekran artık dövizi
gövdeye de yazıyor, sunucu da gövdede bulamazsa kalemlerden geri
düşüyor (sessizce USD'ye düşmek yerine).

═══ 1 · KDV FATURAYA HİÇ YANSIMIYORDU  ← EN AĞIRI ═══

Faturada:

    toplam = ara_toplam = sip.toplam_tutar
    kdv_tutar = data.get('kdv_tutar', 0)      ← ekran bunu HİÇ göndermiyor

Yani KDV oranı giriliyor, ekranda toplama ekleniyor, ama faturaya
ve cariye GİRMİYORDU. Ölçüldü:

    ekran:  3.024 € (KDV %20 dahil)
    fatura: ara_toplam 2.520 · kdv_tutar 0 · toplam 2.520
    cari:   2.520 € borç

504 € müşteriye hiç fatura edilmiyor, hiç tahsil edilmiyordu.

Artık KD1'in tek kapısından geçiyor: matrah + KDV her zaman toplamı
veriyor, cariye KDV dahil tutar borç yazılıyor, siparişin kdv_tutar
alanı da doluyor (o da hep 0 kalıyordu).

═══ 2 · KDV DAHİL / HARİÇ SEÇİLEMİYORDU ═══

Ekran her durumda `ara * (1 + kdv/100)` hesaplayıp sonuca
"(KDV %20 dahil)" yazıyordu — hesap "hariç", etiket "dahil".
Seçim yoktu, oysa cari ve maliyet formlarında var.

Artık aynı sözlerle bir seçim var:
    Hariç — KDV üstüne eklenir
    Dahil — girilen tutar KDV içeriyor
ve ekranın önizlemesi sunucuyla AYNI hesabı yapıyor. Önizleme
artık "(matrah 2.520,00 € + KDV 504,00 €)" diye yazıyor; toplamın
neyden oluştuğu görünüyor.

═══ 3 · "VADE TARİHİ" HANGİ VADE BELLİ DEĞİLDİ ═══

Fatura No'nun yanındaki alan "Vade Tarihi" diyordu, aşağıda çekin
de bir "Vade" alanı vardı. Üstelik ikisi aynı şeye yazıyordu:
sunucu çekin vadesini `cek.vade_tarihi`'nden DEĞİL, üstteki fatura
vadesinden alıyordu. Ekrandaki çek vadesi alanı gövdede
gönderiliyor ama hiç okunmuyordu.

Artık:
    Fatura Vadesi  → müşteri parayı ne zaman ödeyecek
    Çek Vadesi     → çek ne zaman tahsil edilecek (boşsa fatura
                     vadesine düşer, eski davranış korunur)

═══ 4 · SEÇİLEN DÖVİZ HİÇBİR KAYDA GİTMİYORDU ═══

EUR seçilen satışın siparişi, faturası, cari hareketi, çeki ve beş
satış kaydının hepsi USD kaydediliyordu. Ekran €, veri $. Ekran
görüntüsünde satış hattı kartının "2.520 $" demesi, kalemin
"2.520 €" demesi bundandı.

═══ "CARİYE KAYIT İŞLENMEDİ" ═══

Bunu ölçtüm: cari hareket OLUŞUYOR. Çek ödemeli satışta İKİ hareket
oluşuyor — faturadan borç, çekten alacak — ve birbirlerini
götürdüğü için cari BAKİYESİ sıfır görünüyor. Hareket listesinde
ikisi de duruyor; cari kartındaki "çek riski" alanı da tutarı ayrı
gösteriyor. Bu bilinçli bir tasarım (çek portföyde, henüz tahsil
edilmedi).

Yani eksik olan kayıt değil, tutardı: borç 2.520 € yazılıyordu,
3.024 € yazılması gerekirken. O artık düzeldi.

Bakiyede gerçekten HİÇBİR hareket görmüyorsan bana fatura ve cari
kimliğini yaz, oraya ayrıca bakayım.

═══ DOĞRULAMA ═══

  · 306 test geçiyor (299 → 306)
  · 7 HS1 testinin 5'i tabanda düşüyor. İkisi bilerek geçiyor:
    biri korunan davranışı çiviliyor (çek vadesi boşsa faturanınki),
    öteki sunucunun zaten doğru olan tarafını ölçüyor — eksik olan
    EKRANDI ve onu ayrı bir test çiviliyor.
  · Ekranın gönderdiği gövdeyle birebir koşuldu: EUR · %20 hariç →
    fatura 2.520 + 504 = 3.024 €, cariye 3.024 € borç, çek vadesi
    15.12.2026, satış kayıtları EUR (tutar_usd 567 = 504 × 45/40).
  · "Dahil" seçilince: 2.520 € → matrah 2.100 + KDV 420.
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
    'flask_app.py': '#  HS1 · KDV FATURAYA HİÇ YANSIMIYORDU',
    'templates/base.html': 'id="hsKdvDahil"',
    'tests/test_kritik.py': 'def test_hs1_kdv_faturaya_ve_cariye_yansiyor',
}
ONKOSUL = {
    'flask_app.py': 'def _kalem_doviz_denetle(kalemler, belge_doviz)',
    'templates/base.html': 'function hizliSatisKaydet()',
    'tests/test_kritik.py': 'def test_dv1_kalem_dovizi_belgeden_geliyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'HS1 · flask_app.py blok 1',
     r'''        doviz = data.get('doviz', 'USD')
        bugun = date.today()
''',
     r'''        # ── HS1 · BELGE DÖVİZİ ──
        # Ekran dövizi yalnızca KALEMLERE koyuyordu, gövdeye değil.
        # Ölçüldü: EUR seçilen satış sipariş/fatura/cari hareket/satış
        # kaydının HEPSİNDE USD olarak kaydediliyordu — ekran €, veri $.
        # Ekran artık gövdeye de yazıyor; burada ayrıca kalemlerden
        # geri düşülüyor ki eski bir sekme açık kalmışsa da doğru
        # para birimi kullanılsın (sessizce USD'ye düşmektense).
        doviz = (data.get('doviz') or '').strip().upper()
        if not doviz:
            for _k in kalemler_data:
                if isinstance(_k, dict) and (_k.get('doviz') or '').strip():
                    doviz = str(_k['doviz']).strip().upper()
                    break
        doviz = doviz or 'USD'
        bugun = date.today()
'''),
    ('flask_app.py', 'HS1 · flask_app.py blok 2',
     r'''            ftr_no = data.get('fatura_no') or f'SF-{bugun.strftime("%Y%m%d")}-{sip.id[-4:]}'
''',
     r'''            ftr_no = data.get('fatura_no') or f'SF-{bugun.strftime("%Y%m%d")}-{sip.id[-4:]}'
            # ══════════════════════════════════════════════════════
            #  HS1 · KDV FATURAYA HİÇ YANSIMIYORDU
            #
            #  Eskiden: toplam = ara_toplam = sip.toplam_tutar ve
            #  kdv_tutar = data.get('kdv_tutar', 0) — ekran bu alanı
            #  HİÇ GÖNDERMİYOR, yani her zaman 0.
            #
            #  ÖLÇÜLDÜ: ekran "3.024 € (KDV %20 dahil)" yazarken
            #  fatura 2.520 € kesiliyor ve cariye 2.520 € borç
            #  işleniyordu. 504 € müşteriye hiç fatura edilmiyordu.
            #
            #  Artık KD1'in tek kapısından geçiyor; matrah + KDV her
            #  zaman toplamı veriyor. `kdv_dahil_mi` ekrandan geliyor
            #  (diğer satış formlarındaki gibi seçilebilir): "hariç"
            #  ise KDV üstüne eklenir ve toplam büyür, "dahil" ise
            #  girilen tutarın içinden ayrıştırılır.
            # ══════════════════════════════════════════════════════
            _kdv_oran = float(data.get('kdv_oran') or 0)
            _kdv_dahil = bool(data.get('kdv_dahil_mi'))
            _ara, _kdv_tut, _gen_toplam = _kdv_hesapla(
                sip.toplam_tutar or 0, _kdv_oran, _kdv_dahil)
            # Siparişin KDV'si de dolsun: kurulumda `data.get('kdv_tutar')`
            # okunuyordu ve ekran o alanı hiç göndermiyor — oran 20 iken
            # tutar 0 kalıyordu. `toplam_tutar` kalemlerin NET toplamı
            # olarak kalır; bütün sipariş yollarında öyle.
            sip.kdv_oran = _kdv_oran
            sip.kdv_tutar = _kdv_tut
'''),
    ('flask_app.py', 'HS1 · flask_app.py blok 3',
     r'''                toplam=sip.toplam_tutar or 0,
                ara_toplam=sip.toplam_tutar or 0,
                kdv_oran=data.get('kdv_oran', 0), kdv_tutar=data.get('kdv_tutar', 0),
''',
     r'''                toplam=_gen_toplam,
                ara_toplam=_ara,
                kdv_oran=_kdv_oran, kdv_tutar=_kdv_tut,
'''),
    ('flask_app.py', 'HS1 · flask_app.py blok 4',
     r'''                    vade_tarihi=_parse_date(data.get('vade_tarihi')) or bugun,
''',
     r'''                    # HS1 · ÇEKİN KENDİ VADESİ. Ekranda "Çek Bilgileri"
                    # altında bir vade alanı var ve gövdede de
                    # geliyordu, ama burada okunmuyordu: üstteki fatura
                    # vadesi çekin vadesini de eziyordu. İki ayrı tarih:
                    # fatura ne zaman ödenecek, çek ne zaman tahsil
                    # edilecek. Çek vadesi boşsa fatura vadesine düşer.
                    vade_tarihi=(_parse_date(cek_bilgi.get('vade_tarihi'))
                                 or _parse_date(data.get('vade_tarihi'))
                                 or bugun),
'''),
    ('templates/base.html', 'HS1 · templates/base.html blok 1',
     r'''        <div class="hs-alan"><label>Vade Tarihi</label><input id="hsVade" type="date"></div>
        <div class="hs-alan"><label>KDV Oranı (%)</label><input id="hsKdv" type="number" value="0" oninput="hsKalemCiz()"></div>
''',
     r'''        <!-- HS1: etiket "Vade Tarihi" idi ve aşağıda çekin de bir
             vadesi var; hangisinin neyin vadesi olduğu belirsizdi.
             Bu alan FATURANIN vadesi: müşteri parayı ne zaman
             ödeyecek. Çekin vadesi "Çek Bilgileri" altında, ayrı. -->
        <div class="hs-alan"><label>Fatura Vadesi</label><input id="hsVade" type="date"></div>
        <div class="hs-alan"><label>KDV Oranı (%)</label><input id="hsKdv" type="number" value="0" oninput="hsKalemCiz()"></div>
      </div>
      <!-- HS1: KDV dahil/hariç seçimi YOKTU. Ekran toplamı KDV'yi
           üstüne ekleyerek hesaplıyor ama "(KDV %20 dahil)" yazıyordu;
           kullanıcı hangisinin geçerli olduğunu seçemiyordu. Diğer
           satış/maliyet formlarında bu seçim var — aynı sözlerle. -->
      <div class="hs-satir hs-f4">
        <div class="hs-alan"><label>KDV Durumu</label>
          <select id="hsKdvDahil" onchange="hsKalemCiz()">
            <option value="0">Hariç — KDV üstüne eklenir</option>
            <option value="1">Dahil — girilen tutar KDV içeriyor</option>
          </select>
        </div>
'''),
    ('templates/base.html', 'HS1 · templates/base.html blok 2',
     r'''          <div class="hs-alan"><label>Vade</label><input id="hsCekVade" type="date"></div>
''',
     r'''          <!-- HS1: bu alan gövdede gönderiliyordu ama sunucu onu
               okumuyor, çekin vadesine FATURA vadesini yazıyordu.
               Artık çekin kendi vadesi geçerli; boş bırakılırsa
               fatura vadesine düşer. -->
          <div class="hs-alan"><label>Çek Vadesi</label>
            <input id="hsCekVade" type="date"
                   title="Boş bırakılırsa fatura vadesi kullanılır"></div>
'''),
    ('templates/base.html', 'HS1 · templates/base.html blok 3',
     r'''  hsKalemCiz(); hsOdemeDegisti();
''',
     r'''  document.getElementById('hsKdvDahil').value = '0';   /* HS1 */
  hsKalemCiz(); hsOdemeDegisti();
'''),
    ('templates/base.html', 'HS1 · templates/base.html blok 4',
     r'''  const ara = HS_KALEMLER.reduce((a, k) => a + k._toplam, 0);
  const kdv = parseFloat(document.getElementById('hsKdv').value) || 0;
  const t = ara * (1 + kdv / 100);
  const g = document.getElementById('hsGenelToplam');
  if (g) g.textContent = para(t, dov) + (kdv > 0 ? ` (KDV %${kdv} dahil)` : '');
''',
     r'''  /* HS1 · KDV ÖNİZLEMESİ SUNUCUYLA AYNI HESABI YAPAR.
     Eskiden her durumda `ara * (1 + kdv/100)` hesaplanıp sonuca
     "(KDV %x dahil)" yazılıyordu — seçim yoktu ve sunucu KDV'yi
     zaten HİÇ işlemiyordu. Şimdi ikisi de aynı kuralı izliyor:
     hariç -> KDV üstüne eklenir, dahil -> girilen tutarın içinden
     ayrıştırılır (matrah + KDV her zaman toplamı verir). */
  const ara = HS_KALEMLER.reduce((a, k) => a + k._toplam, 0);
  const kdv = parseFloat(document.getElementById('hsKdv').value) || 0;
  const dahilEl = document.getElementById('hsKdvDahil');
  const dahil = dahilEl ? dahilEl.value === '1' : false;
  let matrah = ara, kdvTutar = 0, t = ara;
  if (kdv > 0) {
    if (dahil) {
      matrah = Math.round((ara / (1 + kdv / 100)) * 100) / 100;
      kdvTutar = Math.round((ara - matrah) * 100) / 100;
      t = ara;
    } else {
      kdvTutar = Math.round(ara * kdv / 100 * 100) / 100;
      t = Math.round((ara + kdvTutar) * 100) / 100;
    }
  }
  const g = document.getElementById('hsGenelToplam');
  if (g) g.textContent = para(t, dov) + (kdv > 0
    ? ` (matrah ${para(matrah, dov)} + KDV ${para(kdvTutar, dov)})`
    : '');
'''),
    ('templates/base.html', 'HS1 · templates/base.html blok 5',
     r'''    kdv_oran: parseFloat(document.getElementById('hsKdv').value) || 0,
''',
     r'''    /* HS1: `doviz` GÖNDERİLMİYORDU. Döviz yalnız kalemlere
       konuyordu; sunucu gövdede bulamayınca USD'ye düşüyor ve
       sipariş/fatura/cari hareket/satış kaydının HEPSİ USD
       kaydediliyordu. Ekran € gösterirken veri $ oluyordu. */
    doviz: document.getElementById('hsDoviz').value,
    kdv_oran: parseFloat(document.getElementById('hsKdv').value) || 0,
    kdv_dahil_mi: document.getElementById('hsKdvDahil').value === '1',
'''),
    ('tests/test_kritik.py', 'HS1 · tests/test_kritik.py blok 1',
     r'''        'alınıyor: ' + '; '.join(kacak))
''',
     r'''        'alınıyor: ' + '; '.join(kacak))


# ══════════════════════════════════════════════════════════════════
#  HS1 · HIZLI SATIŞ: EKRANIN SÖYLEDİĞİ İLE KAYDEDİLEN AYNI OLMALI
#
#  İşin sahibi formu kullanırken bildirdi; ölçünce üçü de doğrulandı
#  ve ikisi daha çıktı:
#
#  1. KDV faturaya HİÇ yansımıyordu. `toplam = ara_toplam =
#     sip.toplam_tutar` ve `kdv_tutar = data.get('kdv_tutar', 0)` —
#     ekran o alanı hiç göndermiyor. Ekran "3.024 € (KDV %20 dahil)"
#     yazarken fatura 2.520 € kesiliyor, cariye 2.520 € borç
#     işleniyordu: 504 € müşteriye hiç fatura edilmiyordu.
#  2. Döviz gövdede GÖNDERİLMİYORDU, yalnız kalemlere konuyordu.
#     EUR seçilen satışın siparişi, faturası, cari hareketi ve satış
#     kayıtlarının hepsi USD kaydediliyordu — ekran €, veri $.
#     (DV1'den sonra aynı eksik, satışın 400 ile reddedilmesine yol
#     açıyordu: kalem EUR, belge USD.)
#  3. KDV dahil/hariç seçilemiyordu; ekran hariç hesaplayıp "dahil"
#     yazıyordu.
#  4. Üstteki tek vade alanı hem faturanın hem ÇEKİN vadesini
#     belirliyordu; çekin kendi alanı gövdede geliyor ama sunucuda
#     okunmuyordu.
#  5. Siparişin kdv_tutar'ı da hep 0 kalıyordu (aynı sebep).
# ══════════════════════════════════════════════════════════════════
def _hs1_kurulum(ek=''):
    from models import Firma, PlakaStok
    with fa.app.app_context():
        if not Cari.query.get('HS1-MUS'):
            db.session.add(Cari(id='HS1-MUS', unvan='HS1 ACAR MERMER',
                                cari_tip='Müşteri', para_birimi='TRY',
                                gorunurluk='acik'))
        for dv, k in (('USD', 40.0), ('EUR', 45.0)):
            if not DovizKur.query.filter_by(
                    doviz=dv, tarih=date(2026, 10, 29)).first():
                db.session.add(DovizKur(doviz=dv, tarih=date(2026, 10, 29),
                                        alis=k, satis=k, efektif=k))
        idler = []
        for i in range(1, 6):
            sid = f'PLK-HS1{ek}-{i:02d}'
            idler.append(sid)
            if not PlakaStok.query.get(sid):
                db.session.add(PlakaStok(
                    id=sid, blok_no=f'HS1{ek}', cins='HS1 CEPPO',
                    ozellik='BOOKMATCHED', boy=298, yukseklik=169,
                    kalinlik=2, metraj_m2=5.04, alis_fiyati=36.0,
                    alis_fiyat_birim='m2', matrah=181.44, doviz='USD',
                    durum='Serbest', giris_tarihi=date(2026, 10, 29)))
        db.session.commit()
    return istemci('admin', 'ADMIN'), idler


def _hs1_govde(idler, **ek):
    g = {
        'musteri': 'HS1 ACAR MERMER', 'satis_tipi': 'yurtici',
        'odeme_sekli': 'Cek', 'kasa_id': None, 'teslim_sekli': 'EXW',
        'vade_tarihi': '2026-10-30',
        'doviz': 'EUR', 'kdv_oran': 20, 'kdv_dahil_mi': False,
        'kalemler': [{
            'urun_tip': 'PLAKA', 'cins': 'HS1 CEPPO',
            'ozellik': 'BOOKMATCHED', 'stok_ids': idler,
            'adet': 5, 'miktar': 25.2, 'birim': 'm2',
            'birim_fiyat': 100, 'doviz': 'EUR', 'sira': 1,
            'boy': 298, 'yukseklik': 169, 'kalinlik': 2}],
        'cek': {'cek_no': 'CK-HS1', 'banka_adi': 'İş Bankası',
                'tutar': None, 'vade_tarihi': '2026-12-15'},
    }
    g.update(ek)
    return g


def test_hs1_kdv_faturaya_ve_cariye_yansiyor():
    """Ekran 3.024 € diyorsa fatura da cari de 3.024 € olmalı."""
    from models import Fatura, CariHareket, Siparis
    c, idler = _hs1_kurulum('A')
    r = c.post('/api/sicak_satis', headers=H,
               json=_hs1_govde(idler, fatura_no='HS1-A-001'))
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    fid = r.get_json()['fatura_id']
    with fa.app.app_context():
        f = db.session.get(Fatura, fid)
        # ESKI DAVRANIS: ara_toplam=2520, kdv_tutar=0, toplam=2520
        assert float(f.ara_toplam or 0) == 2520.0, f.ara_toplam
        assert float(f.kdv_tutar or 0) == 504.0, (
            f'KDV {f.kdv_tutar} — ekran %20 dedi, faturaya yansımamış')
        assert float(f.toplam or 0) == 3024.0, f.toplam
        # Matrah + KDV == toplam (KD1 garantisi)
        assert round(float(f.ara_toplam) + float(f.kdv_tutar), 2) \
            == round(float(f.toplam), 2)
        # CARİYE KDV DAHİL TUTAR BORÇ YAZILMALI
        borc = [h for h in CariHareket.query.filter_by(
            cari_id='HS1-MUS').all() if (h.borc or 0) > 0
            and h.baglanti_id == fid]
        assert borc, 'faturadan cariye borç hareketi oluşmamış'
        assert float(borc[0].borc or 0) == 3024.0, (
            f'cariye {borc[0].borc} borç işlendi, fatura 3024 — '
            f'aradaki fark hiç tahsil edilmez')
        # Siparişin KDV'si de dolmalı
        sip = db.session.get(Siparis, f.siparis_id)
        assert float(sip.kdv_tutar or 0) == 504.0, sip.kdv_tutar


def test_hs1_kdv_dahil_secilince_matrah_ayristiriliyor():
    """'Dahil' seçilince girilen tutarın içinden KDV ayrılmalı."""
    from models import Fatura
    c, idler = _hs1_kurulum('B')
    r = c.post('/api/sicak_satis', headers=H, json=_hs1_govde(
        idler, kdv_dahil_mi=True, fatura_no='HS1-B-001'))
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    with fa.app.app_context():
        f = db.session.get(Fatura, r.get_json()['fatura_id'])
        assert float(f.ara_toplam or 0) == 2100.0, f.ara_toplam
        assert float(f.kdv_tutar or 0) == 420.0, f.kdv_tutar
        assert float(f.toplam or 0) == 2520.0, f.toplam


def test_hs1_secilen_doviz_her_kayda_gidiyor():
    """EUR seçilen satış hiçbir yerde USD olmamalı."""
    from models import Fatura, Siparis, CariHareket, SatisKaydi, Cek
    c, idler = _hs1_kurulum('C')
    r = c.post('/api/sicak_satis', headers=H,
               json=_hs1_govde(idler, fatura_no='HS1-C-001'))
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    j = r.get_json()
    assert j.get('doviz') == 'EUR', j
    fid = j['fatura_id']
    with fa.app.app_context():
        f = db.session.get(Fatura, fid)
        assert (f.doviz or '').upper() == 'EUR', f.doviz
        sip = db.session.get(Siparis, f.siparis_id)
        assert (sip.doviz or '').upper() == 'EUR', sip.doviz
        for h in CariHareket.query.filter_by(cari_id='HS1-MUS').all():
            if h.baglanti_id in (fid, j.get('cek_id')):
                assert (h.doviz or '').upper() == 'EUR', (h.id, h.doviz)
        sk = SatisKaydi.query.filter_by(fatura_id=fid).all()
        assert sk, 'satış kaydı oluşmamış'
        for x in sk:
            assert (x.doviz or '').upper() == 'EUR', (x.id, x.doviz)
        if j.get('cek_id'):
            ck = db.session.get(Cek, j['cek_id'])
            assert (ck.doviz or '').upper() == 'EUR', ck.doviz


def test_hs1_doviz_gonderilmezse_kalemden_dusuluyor():
    """Eski bir sekme `doviz` göndermezse sessizce USD olmamalı.

    DV1'in kapısı kalem ile belgeyi karşılaştırıyor; gövdede döviz
    yoksa belge USD'ye düşüyor ve EUR kalemli satış 400 alıyordu.
    Artık kalemlerden geri düşülüyor."""
    from models import Fatura
    c, idler = _hs1_kurulum('D')
    g = _hs1_govde(idler, fatura_no='HS1-D-001')
    g.pop('doviz')                      # eski ekranın gövdesi
    r = c.post('/api/sicak_satis', headers=H, json=g)
    assert r.status_code == 200, (
        f'{r.status_code} — gövdede döviz yokken satış reddedildi: '
        + r.get_data(as_text=True)[:200])
    with fa.app.app_context():
        f = db.session.get(Fatura, r.get_json()['fatura_id'])
        assert (f.doviz or '').upper() == 'EUR', f.doviz


def test_hs1_cekin_kendi_vadesi_geciyor():
    """Çekin vadesi fatura vadesinden AYRI olmalı."""
    from models import Cek, Fatura
    c, idler = _hs1_kurulum('E')
    r = c.post('/api/sicak_satis', headers=H,
               json=_hs1_govde(idler, fatura_no='HS1-E-001'))
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    j = r.get_json()
    with fa.app.app_context():
        f = db.session.get(Fatura, j['fatura_id'])
        ck = db.session.get(Cek, j['cek_id'])
        assert f.vade_tarihi == date(2026, 10, 30), f.vade_tarihi
        # ESKI DAVRANIS: cek.vade_tarihi de 2026-10-30 oluyordu
        assert ck.vade_tarihi == date(2026, 12, 15), (
            f'çekin vadesi {ck.vade_tarihi} — ekranda 15.12.2026 '
            f'girilmişti, fatura vadesi onu ezmiş')


def test_hs1_cek_vadesi_bossa_fatura_vadesine_dusuyor():
    """Çek vadesi boşsa eski davranış korunur."""
    from models import Cek
    c, idler = _hs1_kurulum('F')
    g = _hs1_govde(idler, fatura_no='HS1-F-001')
    g['cek']['vade_tarihi'] = None
    r = c.post('/api/sicak_satis', headers=H, json=g)
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    with fa.app.app_context():
        ck = db.session.get(Cek, r.get_json()['cek_id'])
        assert ck.vade_tarihi == date(2026, 10, 30), ck.vade_tarihi


def test_hs1_ekran_dovizi_ve_kdv_durumunu_gonderiyor():
    """Form gövdesi `doviz` ve `kdv_dahil_mi` taşımalı.

    Sunucu düzelse de ekran göndermezse hiçbir şey değişmez; bu
    ikisi AYNI yamanın iki yarısı."""
    import io as _io
    b = _io.open(os.path.join(KOK, 'templates', 'base.html'),
                 encoding='utf-8').read()
    assert "doviz: document.getElementById('hsDoviz').value" in b, \
        'hızlı satış gövdesi döviz göndermiyor'
    assert "kdv_dahil_mi: document.getElementById('hsKdvDahil')" in b, \
        'hızlı satış gövdesi KDV durumunu göndermiyor'
    assert 'id="hsKdvDahil"' in b, 'KDV dahil/hariç seçeneği yok'
    # Etiketler: hangi vade neyin vadesi
    assert 'Fatura Vadesi' in b, 'fatura vadesi etiketi belirsiz'
    assert 'Çek Vadesi' in b, 'çek vadesi etiketi belirsiz'
'''),
]

def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA HS1 — HIZLI SATIŞ DÜZELTMELERİ')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    # ── --yaz-gecici ──
    # base64 gömülü iki dosyayı /tmp'ye çıkarır, PROJEYE DOKUNMAZ.
    # Tam dosya yazan bir yamayı önce okumak istemek yerinde bir
    # istek; "uygula da sonra bak" demek yanlış olurdu.
    if '--yaz-gecici' in sys.argv:
        hedef = tempfile.mkdtemp(prefix='hs1-')
        print()
        for ad in TAM_YAZILAN:
            p = os.path.join(hedef, ad)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(_tam_dosya(ad))
            print(f'  {p}')
        print()
        print('  Projeye DOKUNULMADI. Okuduktan sonra:')
        print('    python3 yama_hs1.py            # rapor')
        print('    python3 yama_hs1.py --uygula')
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
        print('  ⊙ Yama HS1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_hs1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_hs1'
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
    print('    venv/bin/python -m pytest tests/test_kritik.py -q   # 306')
    print()
    print('  SUNUCUYU YENIDEN BASLAT')
    print('    sudo systemctl restart milestone-erp')
    print('    Sema degisikligi YOK, goc YOK.')
    print('    TARAYICIDA SERT YENILE (Ctrl+F5): base.html degisti.')
    print()
    print('  NE DEGISTI (hizli satis)')
    print('    · KDV artik faturaya ve cariye YANSIYOR. Ekran 3.024 €')
    print('      derken fatura 2.520 € kesiliyordu; 504 € hic fatura')
    print('      edilmiyordu.')
    print('    · KDV dahil/haric SECILEBILIYOR; onizleme sunucuyla')
    print('      ayni hesabi yapiyor ve matrah+KDV ayri gosteriliyor.')
    print('    · Secilen doviz artik her kayda gidiyor (siparis,')
    print('      fatura, cari hareket, cek, satis kayitlari).')
    print('    · "Vade Tarihi" -> "Fatura Vadesi"; cekin KENDI vadesi')
    print('      artik gecerli (bosta fatura vadesine duser).')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA EM1 — İPTAL EDİLMİŞ GİDER ARTIK HİÇBİR YERDE SAYILMIYOR
             + YARIM KALAN SATIŞ DÜZENLEME TAMAMLANDI
=============================================================

ÖNKOŞUL: depodaki son hal (commit d1d0e74). Betik denetliyor.

Taramanın ilk iki maddesi. Üçüncü madde (kesim geri alınınca öksüz
kalan maliyet) ve alış faturasındaki döviz hatası ayrı yamada
gelecek — ikisi de para hareketine dokunuyor, tek tek görmek daha
iyi.

═══ 1 · İPTAL EDİLMİŞ GİDER (6 YER) ═══

MR1'de stok maliyetini tek kaynağa bağlamıştım. Tarama aynı sorunun
ALTI yerde daha durduğunu gösterdi; hiçbirinde `aktif` süzgeci
yoktu, ikisinde ayrıca NULL tuzağı vardı:

    2958/2961  sipariş kârlılığı (USD + TRY)
    3803       fatura/sipariş kârlılığı     + tipsizi de eliyordu
    4760       dashboard
    5536       stok listesi · "Ek Maliyet" sütunu + tipsizi de eliyordu
    5548       stok listesi · KDV toplamları
    18334      kârlılık raporu

ÖLÇÜLDÜ — bir bloğa 1.000 $ nakliye (aktif) + 400 $ gümrük (İPTAL)
+ 250 $ tipsiz gider + 900 $ Devreden KDV:

        önce                     sonra
        stok listesi  1.400 $    1.250 $   ✓
        maliyet raporu 1.250 $   1.250 $

Aynı bloğun ek maliyeti iki ekranda iki farklı sayıydı. Artık değil.

ŞART TEK YERDE: `_maliyet_sayilir()`. Koşulu döndürüyor, sorguyu
kendisi kurmuyor — altı yerin sorgu biçimi farklı (kimi gruplu, kimi
TRY karşılığı, kimi sipariş kimliğine bağlı); ortak olan ŞART.
Ayrı ayrı yazılsaydı biri düzeltilip ötekiler unutulurdu; bu
hatanın doğuş biçimi tam olarak buydu.

**RAKAMLARIN DEĞİŞECEK.** İptal ettiğin giderler artık sayılmayacağı
için dashboard, kârlılık ve sipariş kârlılığı rakamları DÜŞECEK;
tipi boş girdiğin giderler ise artık sayılacağı için ilgili yerlerde
ARTACAK. Doğru olan bu — ama eski bir çıktıyla karşılaştırırsan fark
göreceksin.

═══ 2 · SATIŞ DÜZENLEME — YARIM KALAN İŞ ═══

`PUT /api/satislar/<id>` ucu kodunda VARDI: tam, sağlam, faturadan
doğan satışı 409 ile reddedip sebebini bile yazıyor. Ama onu çağıran
HİÇBİR ŞEY yoktu — hiçbir şablon o uca istek atmıyordu.

Satış kaydı kârın kaynağı: ortaklık hesabı, kârlılık raporu ve
müşteri özeti hep oradan okuyor. Yanlış girilmiş bir satışı hiçbir
yerden düzeltemiyordun.

Satışlar → bir satıra tıkla → **Düzenle**. Birim fiyat, miktar,
tutar, döviz, tarih ve not.

  · Tutarı boş bırakırsan birim fiyat × miktardan türetiliyor.
  · Yazarsan yazdığın geçerli — faturada iskonto ya da yuvarlama
    olabilir.
  · Boş bıraktığın sayı alanı GÖNDERİLMİYOR; yanlışlıkla sıfırlamak
    mümkün olmasın.
  · Faturaya bağlı satışta sunucu reddediyor ve sebebini kırmızı
    gösteriyor — orada doğrunun kaynağı faturanın kendisi.

TARAYICIDA DENENDİ (bu özellik ilk kez çalıştırıldı):

    faturasız satış   birim 1.000 → 900, tutar boş bırakıldı
                      tutar 4.860'a türedi
                      kâr 4.860 → 4.320 olarak TAZELENDİ
    faturalı satış    409, uyarı göründü, hiçbir alan değişmedi
    JS hatası         yok

NOT — etiket çakışması: bendeki kopyada bu iş "DZ3" diye
etiketliydi, oysa DZ3 proforma→sipariş işinin etiketi. Bu yamada
**SD4** oldu.

═══ DOĞRULANDI ═══
  244 test geçti (240 + 4). Yeni testlerden ikisi DAVRANIŞ bakıyor:
  biri listeyle raporu karşılaştırıyor, öteki faturaya bağlı satışın
  değişmediğini doğruluyor.
  firma · js · form · akış denetimleri temiz.

DOSYALAR
--------
  flask_app.py             tek süzgeç kapısı + 6 çağrı yeri
  templates/satislar.html  düzenleme penceresi · düğme · JS
  tests/test_kritik.py     4 yeni test

Şema yok, göç yok.

KULLANIM
--------
  python3 yama_em1.py            # RAPOR
  python3 yama_em1.py --uygula
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
    'flask_app.py': 'EM1 · İKİ SÜZGEÇ, ALTI YER',
    'templates/satislar.html': 'SD4 · SATIŞ DÜZENLEME',
    'tests/test_kritik.py': 'def test_em1_liste_ve_rapor_ayni_sayiyi_soyluyor',
}
ONKOSUL = {
    'flask_app.py': 'KM1 · MENSE KAYNAKTAN GELIR',
    'templates/satislar.html': 'async function faturaOlustur(',
    'tests/test_kritik.py': 'def test_km1_kesim_menseyi_kaynaktan_tasir',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'EM1 · flask_app.py blok 1',
     r'''        ek_maliyet_usd = db.session.query(
            db.func.sum(Maliyet.usd_karsilik)
        ).filter(Maliyet.baglanti_id == siparis_id).scalar() or 0
        ek_maliyet_try = db.session.query(
            db.func.sum(Maliyet.try_karsilik)
        ).filter(Maliyet.baglanti_id == siparis_id).scalar() or 0
''',
     r'''        # EM1: sipariş kimliğine bağlı maliyetlerde de iki süzgeç.
        # Stok tarafı MR1'de düzeltilmişti, sipariş tarafı unutulmuştu.
        ek_maliyet_usd = db.session.query(
            db.func.sum(Maliyet.usd_karsilik)
        ).filter(Maliyet.baglanti_id == siparis_id,
                 *_maliyet_sayilir()).scalar() or 0
        ek_maliyet_try = db.session.query(
            db.func.sum(Maliyet.try_karsilik)
        ).filter(Maliyet.baglanti_id == siparis_id,
                 *_maliyet_sayilir()).scalar() or 0
'''),
    ('flask_app.py', 'EM1 · flask_app.py blok 2',
     r'''            _mr1 = db.or_(Maliyet.maliyet_tip.is_(None),
                          ~Maliyet.maliyet_tip.in_(MALIYET_DISI_TIPLER))
            ek_maliyet_usd += db.session.query(db.func.sum(Maliyet.usd_karsilik)).filter(
                Maliyet.baglanti_id.in_(stok_idler),
                Maliyet.aktif.is_(True), _mr1
            ).scalar() or 0
            ek_maliyet_try += db.session.query(db.func.sum(Maliyet.try_karsilik)).filter(
                Maliyet.baglanti_id.in_(stok_idler),
                Maliyet.aktif.is_(True), _mr1
''',
     r'''            ek_maliyet_usd += db.session.query(db.func.sum(Maliyet.usd_karsilik)).filter(
                Maliyet.baglanti_id.in_(stok_idler),
                *_maliyet_sayilir()
            ).scalar() or 0
            ek_maliyet_try += db.session.query(db.func.sum(Maliyet.try_karsilik)).filter(
                Maliyet.baglanti_id.in_(stok_idler),
                *_maliyet_sayilir()
'''),
    ('flask_app.py', 'EM1 · flask_app.py blok 3',
     r'''    def _stok_alim_usd(stok, stok_tip=None):
''',
     r'''    def _maliyet_sayilir():
        """Maliyete GİREN satırların koşulu — tek yerden.

        ── EM1 · İKİ SÜZGEÇ, ALTI YER ──
        MR1'de stok maliyetini tek kaynağa bağlamıştım ama aynı soru
        sistemde ALTI yerde daha soruluyordu ve hiçbirinde `aktif`
        süzgeci yoktu:

            sipariş kârlılığı · fatura kârlılığı · dashboard ·
            stok listesi · stok listesi KDV · kârlılık raporu

        ÖLÇÜLDÜ: bir bloğa 1.000 $ nakliye (aktif) + 400 $ gümrük
        (İPTAL) + 250 $ tipsiz gider konuldu.
            stok listesi         1.400,00 $
            stok maliyet raporu  1.250,00 $   ← doğru olan
        Aynı bloğun ek maliyeti iki ekranda iki farklı sayıydı.

        İki süzgeç de burada:
          · `aktif=False` İPTAL edilmiş maliyettir, sayılmaz.
          · `~tip.in_(...)` TEK BAŞINA tipi BOŞ satırı da eler —
            SQL'de `NULL NOT IN (...)` → NULL. Tipsiz gider gerçek
            bir giderdir, sayılmalı.

        Koşulu DÖNDÜRÜYOR, sorguyu kendisi kurmuyor: altı yerin
        sorgu biçimi farklı (kimi gruplu, kimi TRY karşılığı, kimi
        sipariş kimliğine bağlı). Ortak olan ŞART, sorgu değil.
        """
        return (Maliyet.aktif.is_(True),
                db.or_(Maliyet.maliyet_tip.is_(None),
                       ~Maliyet.maliyet_tip.in_(MALIYET_DISI_TIPLER)))

    def _stok_alim_usd(stok, stok_tip=None):
'''),
    ('flask_app.py', 'EM1 · flask_app.py blok 4',
     r'''                Maliyet.baglanti_id == f.siparis_id, ~Maliyet.maliyet_tip.in_(['Devreden KDV', 'Iade KDV'])).scalar() or 0
''',
     r'''                Maliyet.baglanti_id == f.siparis_id,
                *_maliyet_sayilir()).scalar() or 0   # EM1
'''),
    ('flask_app.py', 'EM1 · flask_app.py blok 5',
     r'''        maliyetler = db.session.query(Maliyet.baglanti_id, func.sum(Maliyet.usd_karsilik)).filter(func.lower(Maliyet.baglanti_tip) == 'stok').group_by(Maliyet.baglanti_id).all()
''',
     r'''        # EM1: dashboard da iptal edilmiş gideri sayıyordu.
        maliyetler = db.session.query(
            Maliyet.baglanti_id, func.sum(Maliyet.usd_karsilik)
        ).filter(func.lower(Maliyet.baglanti_tip) == 'stok',
                 *_maliyet_sayilir()).group_by(Maliyet.baglanti_id).all()
'''),
    ('flask_app.py', 'EM1 · flask_app.py blok 6',
     r'''            maliyet_sonuc = db.session.query(
                Maliyet.baglanti_id,
                db.func.sum(Maliyet.usd_karsilik)
            ).filter(
                Maliyet.baglanti_id.in_(sayfa_idler),
                ~Maliyet.maliyet_tip.in_(['Devreden KDV', 'Iade KDV'])
''',
     r'''            # EM1: ÖLÇÜLEN YER. Bu sütun 1.400 $ derken stok maliyet
            # raporu aynı blok için 1.250 $ diyordu.
            maliyet_sonuc = db.session.query(
                Maliyet.baglanti_id,
                db.func.sum(Maliyet.usd_karsilik)
            ).filter(
                Maliyet.baglanti_id.in_(sayfa_idler),
                *_maliyet_sayilir()
'''),
    ('flask_app.py', 'EM1 · flask_app.py blok 7',
     r'''                    Maliyet.maliyet_tip == tip_adi
''',
     r'''                    Maliyet.maliyet_tip == tip_adi,
                    # EM1: burada tip süzgeci EŞİTLİK olduğu için NULL
                    # tuzağı yok; eksik olan yalnız `aktif`. İptal
                    # edilmiş bir KDV kalemi de sayılıyordu.
                    Maliyet.aktif.is_(True)
'''),
    ('flask_app.py', 'EM1 · flask_app.py blok 8',
     r'''                    Maliyet.baglanti_id == s.id
''',
     r'''                    Maliyet.baglanti_id == s.id,
                    *_maliyet_sayilir()   # EM1
'''),
    ('templates/satislar.html', 'EM1 · templates/satislar.html blok 1',
     r'''  eylem.push(`<button class="blok-btn" onclick="cekmeceKapat()">Kapat</button>`);
''',
     r'''  /* SD4: `PUT /api/satislar/<id>` ucu kodda VARDI ama onu çağıran
     hiçbir şey yoktu — özellik yarım kurulmuştu. Satış kaydı kârın
     kaynağı (ortaklık hesabı, kârlılık raporu, müşteri özeti hep
     buradan okuyor); yanlış girilmiş bir satış hiçbir yerden
     düzeltilemiyordu. */
  if (yazabilir('satis') || yazabilir('fatura'))
    eylem.push(`<button class="blok-btn" onclick="sDuzenleAc('${kacar(id)}')">Düzenle</button>`);
  eylem.push(`<button class="blok-btn" onclick="cekmeceKapat()">Kapat</button>`);
'''),
    ('templates/satislar.html', 'EM1 · templates/satislar.html blok 2',
     r'''yukle();
</script>
''',
     r'''/* ═══ SD4 · SATIŞ DÜZENLEME ═══ */
let SDUZ_ID = null;

function sDuzenleAc(id) {
  const x = TUM.find(s => s.id === id);
  if (!x) return;
  SDUZ_ID = id;
  cekmeceKapat();
  document.getElementById('sDuzAlt').textContent =
    `${x.id} · ${kacar(x.musteri || '')}`;
  const koy = (kimlik, deger) => {
    const el = document.getElementById(kimlik);
    if (el) el.value = (deger === 0 || deger) ? deger : '';
  };
  koy('sDuzBirimFiyat', x.birim_fiyat);
  koy('sDuzMiktar', x.miktar);
  koy('sDuzTutar', x.tutar);
  koy('sDuzTarih', x.satis_tarihi);
  koy('sDuzNot', x.notlar);
  document.getElementById('sDuzDoviz').value = (x.doviz || 'USD').toUpperCase();
  document.getElementById('sDuzModal').classList.add('acik');
}
function sDuzKapat() {
  document.getElementById('sDuzModal').classList.remove('acik');
}

async function sDuzenleKaydet() {
  if (!SDUZ_ID) return;
  const btn = document.getElementById('sDuzKaydet');
  btn.disabled = true; btn.textContent = 'Kaydediliyor…';
  try {
    const say = (kimlik) => {
      const v = document.getElementById(kimlik).value;
      return v === '' ? undefined : parseFloat(v);
    };
    const govde = {
      doviz: document.getElementById('sDuzDoviz').value,
      satis_tarihi: document.getElementById('sDuzTarih').value || undefined,
      notlar: document.getElementById('sDuzNot').value
    };
    /* Bos birakilan sayi alani GONDERILMIYOR: yanlislikla
       sifirlamak mumkun olmasin. */
    for (const [kimlik, alan] of [['sDuzBirimFiyat', 'birim_fiyat'],
                                  ['sDuzMiktar', 'miktar'],
                                  ['sDuzTutar', 'tutar']]) {
      const v = say(kimlik);
      if (v !== undefined) govde[alan] = v;
    }
    const d = await api(`/api/satislar/${encodeURIComponent(SDUZ_ID)}`,
                        { method: 'PUT', body: JSON.stringify(govde) });
    bildir(d.mesaj || 'Satış kaydı güncellendi');
    sDuzKapat(); await yukle();
  } catch (e) {
    /* 409 = faturaya bagli. api() 409'u cagirana birakiyor;
       sebebi tehlike kipinde gosteriyoruz ki fark edilsin. */
    if (e && e.status === 409 && e.yanit && e.yanit.mesaj) {
      bildir(e.yanit.mesaj, true);
    }
  } finally { btn.disabled = false; btn.textContent = 'Kaydet'; }
}

yukle();
</script>
<!-- SD4 · SATIŞ DÜZENLEME
     Satışın tutar tarafı hiçbir yerden düzenlenemiyordu. Bu kayıt
     kârın kaynağı: ortaklık hesabı, kârlılık raporu ve müşteri
     özeti hep buradan okuyor. Faturaya bağlı satışta sunucu 409
     dönüyor ve sebebini yazıyor — orada doğrunun kaynağı fatura. -->
<div class="modal-ortu" id="sDuzModal" onclick="if(event.target===this)sDuzKapat()">
  <div class="modal" role="dialog" aria-label="Satış düzenle">
    <div class="modal-bas">
      <h3>Satışı Düzenle</h3>
      <p id="sDuzAlt">—</p>
    </div>
    <div class="modal-gov">
      <div class="form-satir f3">
        <div class="form-alan"><label>Birim Fiyat</label>
          <input id="sDuzBirimFiyat" type="number" step="0.01" min="0"></div>
        <div class="form-alan"><label>Miktar</label>
          <input id="sDuzMiktar" type="number" step="0.001" min="0"></div>
        <div class="form-alan"><label>Döviz</label>
          <select id="sDuzDoviz"><option>USD</option><option>EUR</option><option>TRY</option></select></div>
      </div>
      <div class="form-satir f2">
        <div class="form-alan"><label>Tutar</label>
          <input id="sDuzTutar" type="number" step="0.01" min="0"></div>
        <div class="form-alan"><label>Satış Tarihi</label>
          <input id="sDuzTarih" type="date"></div>
      </div>
      <div class="not" style="font-size:.8rem">
        Tutarı boş bırakırsan birim fiyat × miktardan hesaplanır.
        Yazarsan yazdığın geçerli olur — faturada iskonto ya da
        yuvarlama olabilir.
      </div>
      <div class="form-alan"><label>Not</label>
        <input id="sDuzNot" maxlength="500" data-buyuk-harf="hayir"></div>
    </div>
    <div class="modal-alt">
      <button class="iptal-btn" onclick="sDuzKapat()">Vazgeç</button>
      <button class="btn-yeni" id="sDuzKaydet" onclick="sDuzenleKaydet()">Kaydet</button>
    </div>
  </div>
</div>

'''),
    ('tests/test_kritik.py', 'EM1 · tests/test_kritik.py blok 1',
     r'''    # STOK kimligine bagli her toplama IKI SUZGECTEN gecmeli.
    # (Siparis kimligine bagli toplamalar BASKA bir soru soruyor —
    #  onlarda da `aktif` eksik, Bahadir'a bulgu olarak bildirildi.)
    kotu = []
    for parca in _re.findall(
            r'sum\(Maliyet\.(?:usd|try)_karsilik\).{0,320}?\.scalar\(\)',
            f, _re.S):
        if 'stok_idler' not in parca and 'baglanti_id == stok_id' not in parca:
            continue
        if 'aktif.is_(True)' not in parca:
            kotu.append(parca[:90])
    assert not kotu, f'stok maliyetinde süzgeçsiz toplama: {kotu}'
''',
     r'''    # EM1: artik SIPARIS kimligine bagli olanlar da dahil, Maliyet
    # uzerindeki HER toplama iki suzgecten gecmeli. Sart tek yerde
    # (`_maliyet_sayilir`), o yuzden ya o kapidan gecer ya da sarti
    # kendi yazar.
    kotu = []
    for parca in _re.findall(
            r'sum\(Maliyet\.(?:usd|try)_karsilik\).{0,420}?'
            r'(?:\.scalar\(\)|\.all\(\))', f, _re.S):
        if '_maliyet_sayilir()' in parca or 'aktif.is_(True)' in parca:
            continue
        kotu.append(' '.join(parca.split())[:100])
    assert not kotu, f'süzgeçsiz maliyet toplaması: {kotu}'
'''),
    ('tests/test_kritik.py', 'EM1 · tests/test_kritik.py blok 2',
     r'''    assert not eksik, f'alt bar zeminsiz kalabilir: {eksik}'
''',
     r'''    assert not eksik, f'alt bar zeminsiz kalabilir: {eksik}'


# ══════════════════════════════════════════════════════════════════
#  EM1 · İPTAL EDİLMİŞ GİDER ALTI YERDE DAHA SAYILIYORDU
#
#  MR1'de stok maliyetini tek kaynağa bağlamıştım. Tarama, aynı
#  sorunun ALTI yerde daha durduğunu gösterdi — hiçbirinde `aktif`
#  süzgeci yoktu, ikisinde ayrıca NULL tuzağı vardı:
#
#      sipariş kârlılığı · fatura kârlılığı · dashboard ·
#      stok listesi · stok listesi KDV · kârlılık raporu
#
#  ÖLÇÜLDÜ: 1.000 $ nakliye (aktif) + 400 $ gümrük (İPTAL) +
#  250 $ tipsiz gider konulmuş bir blokta
#      stok listesi         1.400,00 $
#      stok maliyet raporu  1.250,00 $   ← doğru olan
#  Aynı bloğun ek maliyeti iki ekranda iki farklı sayıydı.
# ══════════════════════════════════════════════════════════════════

def test_em1_liste_ve_rapor_ayni_sayiyi_soyluyor():
    """Ölçülen hatanın kendisi: iki ekran, iki sayı."""
    from models import Maliyet, PlakaStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BLK-EM1', firma_id=1, blok_no='EM1', cins='EMTEST',
            uretici='O', boy=300, yukseklik=180, en=170, hacim_m3=9.18,
            tonaj=20, alis_fiyati=300, matrah=6000,
            alis_fiyat_birim='ton', doviz='USD', durum='Serbest',
            giris_tarihi=date(2026, 5, 1)))
        db.session.flush()
        for _i, (_tip, _tut, _aktif) in enumerate((
                ('Nakliye (Ocak-Fabrika)', 1000, True),   # sayılmalı
                ('Gümrük/Liman Masrafı', 400, False),     # İPTAL
                (None, 250, True),                        # TİPSİZ
                ('Devreden KDV', 900, True)), 1):         # maliyet dışı
            db.session.add(Maliyet(
                id=f'MEM-{_i}', firma_id=1, maliyet_tip=_tip,
                baglanti_tip='stok', baglanti_id='BLK-EM1', tutar=_tut,
                doviz='USD', usd_karsilik=_tut,
                maliyet_tarihi=date(2026, 5, 1), aktif=_aktif))
        db.session.commit()

    liste = c.get('/api/stok?tip=BLOK&per_page=100', headers=H).get_json()
    kayit = [x for x in liste['data'] if x['id'] == 'BLK-EM1'][0]
    rapor = c.get('/api/rapor/stok_maliyet?blok_no=EM1',
                  headers=H).get_json()
    g = [x for x in rapor['gruplar'] if x['id'] == 'BLK-EM1'][0]

    _liste = float(kayit.get('ek_maliyet_toplam') or 0)
    _rapor = g['toplam_usd'] - g['alim_usd']
    assert abs(_liste - 1250) < 0.01, \
        f'stok listesi {_liste} diyor — doğrusu 1.250 (iptal 400 hariç, tipsiz 250 dahil)'
    assert abs(_liste - _rapor) < 0.01, \
        f'liste {_liste} · rapor {_rapor} — iki ekran iki sayı'


def test_em1_sart_tek_yerden_geliyor():
    """Altı yer de ortak kapıdan geçmeli.

    Ayrı ayrı yazılsaydı biri düzeltilip ötekiler unutulurdu —
    bu hatanın doğuş biçimi tam olarak buydu."""
    import io as _io, re as _re
    f = _io.open(os.path.join(KOK, 'flask_app.py'), encoding='utf-8').read()
    assert 'def _maliyet_sayilir(' in f, 'ortak süzgeç kapısı yok'
    # Kapi IKI sarti da tasimali.
    _k = f[f.index('def _maliyet_sayilir('):]
    _k = _k[:_k.index('\n    def ', 10)]
    assert 'aktif.is_(True)' in _k, 'kapıda `aktif` yok'
    assert 'maliyet_tip.is_(None)' in _k, 'kapıda NULL koruması yok'
    # En az alti cagiran.
    assert f.count('_maliyet_sayilir()') >= 7, \
        f'kapı yalnız {f.count("_maliyet_sayilir()") - 1} yerde kullanılıyor'


# ══════════════════════════════════════════════════════════════════
#  SD4 · SATIŞ DÜZENLEME — YARIM KURULMUŞ ÖZELLİK
#
#  `PUT /api/satislar/<id>` ucu kodda vardı, tam ve sağlamdı; ama
#  onu çağıran HİÇBİR ŞEY yoktu. Satış kaydı kârın kaynağı
#  (ortaklık hesabı, kârlılık raporu, müşteri özeti hep oradan
#  okuyor) ve yanlış girilmiş bir satış hiçbir yerden
#  düzeltilemiyordu.
#
#  TARAYICIDA DENENDİ: 1.000 → 900 yazıldı, tutar boş bırakıldı;
#  tutar 4.860'a türedi ve kâr 4.860 → 4.320 olarak tazelendi.
#  Faturaya bağlı satış 409 ile reddedildi, hiçbir şey değişmedi.
# ══════════════════════════════════════════════════════════════════

def test_sd4_satis_duzenleme_ucu_erisilebilir():
    """Uç ile arayüz birbirine bağlı olmalı."""
    import io as _io
    f = _io.open(os.path.join(KOK, 'flask_app.py'), encoding='utf-8').read()
    assert "@app.route('/api/satislar/<satis_id>', methods=['PUT'])" in f
    t = _io.open(os.path.join(KOK, 'templates/satislar.html'),
                 encoding='utf-8').read()
    assert 'sDuzenleAc(' in t, 'düzenleme açılmıyor'
    assert 'id="sDuzModal"' in t, 'düzenleme penceresi yok'
    assert "method: 'PUT'" in t, 'uç çağrılmıyor'
    # 409 (faturaya bagli) KULLANICIYA gosterilmeli, yutulmamali.
    _j = t[t.index('async function sDuzenleKaydet('):]
    _j = _j[:_j.index('\n}')]
    assert 'status === 409' in _j and 'bildir(' in _j, \
        'faturaya bağlı satış uyarısı yutuluyor'


def test_sd4_faturaya_bagli_satis_degismiyor():
    """Faturadan doğan satışın tutarı buradan değiştirilemez."""
    from models import SatisKaydi, Fatura, PlakaStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(PlakaStok(
            id='PLK-SD4T', firma_id=1, blok_no='SD4', cins='SDTEST',
            uretici='O', boy=300, yukseklik=180, kalinlik=2,
            metraj_m2=5.4, alis_fiyati=100, matrah=540,
            alis_fiyat_birim='m2', doviz='USD', durum='Satildi',
            giris_tarihi=date(2026, 5, 1)))
        db.session.add(Fatura(
            id='FT-SD4T', firma_id=1, fatura_no='SD4-1', yon='satis',
            durum='Kesildi', doviz='USD', toplam=5400,
            fatura_tarihi=date(2026, 5, 1)))
        db.session.flush()
        db.session.add_all([
            SatisKaydi(id='SK-SD4-SERBEST', firma_id=1, stok_tip='PLAKA',
                       stok_id='PLK-SD4T', musteri='ABC',
                       satis_tarihi=date(2026, 5, 1), doviz='USD',
                       birim_fiyat=1000, miktar=5.4, birim='m2',
                       tutar=5400, tutar_usd=5400, kur_usd=40),
            SatisKaydi(id='SK-SD4-FATURALI', firma_id=1, stok_tip='PLAKA',
                       stok_id='PLK-SD4T', musteri='ABC',
                       satis_tarihi=date(2026, 5, 1), doviz='USD',
                       birim_fiyat=1000, miktar=5.4, birim='m2',
                       tutar=5400, tutar_usd=5400, kur_usd=40,
                       fatura_id='FT-SD4T')])
        db.session.commit()

    # Faturasiz: degisiyor, tutar birim x miktardan tureiyor
    r = c.put('/api/satislar/SK-SD4-SERBEST', headers=H,
              json={'birim_fiyat': 900})
    assert r.status_code == 200, r.get_json()
    # Faturaya bagli: 409 ve DEGISMIYOR
    r = c.put('/api/satislar/SK-SD4-FATURALI', headers=H,
              json={'birim_fiyat': 1})
    assert r.status_code == 409, r.status_code
    assert 'SD4-1' in (r.get_json() or {}).get('mesaj', ''), r.get_json()
    with fa.app.app_context():
        serbest = db.session.get(SatisKaydi, 'SK-SD4-SERBEST')
        faturali = db.session.get(SatisKaydi, 'SK-SD4-FATURALI')
        assert abs(float(serbest.tutar) - 4860) < 0.01, serbest.tutar
        assert abs(float(faturali.birim_fiyat) - 1000) < 0.01, \
            'faturaya bağlı satış değişmiş'
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA EM1 — İPTAL EDİLMİŞ GİDER ARTIK HİÇBİR YERDE SAYILMIYOR')
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
        print('    python3 yama_em1.py            # rapor')
        print('    python3 yama_em1.py --uygula')
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
        print('  ⊙ Yama EM1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_em1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_em1'
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
    print('    3) venv/bin/python -m pytest tests/test_kritik.py -q   # 244')
    print()
    print('  BAKILACAK YER')
    print('    1. Satislar -> bir satira tikla -> DUZENLE (yeni).')
    print('       Faturaya bagli satista reddediyor, sebebini yaziyor.')
    print('    2. Depo -> Stok listesi "Ek Maliyet" sutunu artik stok')
    print('       maliyet raporuyla AYNI sayiyi soyluyor.')
    print()
    print('  RAKAMLARIN DEGISECEK')
    print('    Iptal ettigin giderler artik sayilmiyor: dashboard,')
    print('    karlilik ve siparis karliligi DUSECEK. Tipi bos')
    print('    girilmis giderler ise artik sayiliyor. Dogru olan bu.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

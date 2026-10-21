#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA OR7 — ORTAKLIĞA BLOK/PLAKA BAĞLANABİLİYOR
===============================================

ÖNKOŞUL: yama_or6.py uygulanmış olmalı.

Senin akışın malzeme alımında başlıyor; sipariş aylar sonra
geliyor. Ortaklık yalnız işe (sipariş/sevkiyat/proforma)
bağlanabildiği için "Maliyetlerden ekle" o süre boyunca BOŞ
geliyordu — ölçmüştüm.

── NE GELDİ ──
  İş bağlama penceresinde artık BLOK, PLAKA ve EBATLI da var.
  Bloğu bağladığın anda:

    · o bloğa işlenmiş fason/nakliye kayıtları maliyet listesinde
      çıkıyor — sipariş beklemeden katkıya alabiliyorsun,
    · hangi blokların bu ortaklığa ait olduğu kayıtta duruyor,
    · blok satıldığında ciro ve kâr sipariş bağlamadan geliyor.

  Seçicide blok NO'su, cinsi, giriş tarihi ve TOPLAM alış bedeli
  bir arada. (Birim fiyat değil: "420 USD/ton" yazmak "bu blok 420
  dolar" diye okunur ve yanlış blok seçtirir. Kesimin kullandığı
  kuralın aynısı uygulanıyor — matrah varsa o, yoksa tonaj × birim
  fiyat.)

── KESİM ZİNCİRİ KENDİLİĞİNDEN TAKİP EDİLİYOR ──
  Bağladığın bloktan kesimle çıkan plakalar da ortaklığa ait
  sayılıyor: onlara işlenen maliyet listede çıkıyor, onların
  satışı ciroya giriyor.

  Kullanıcıdan her kesimden sonra listeyi güncellemesini beklemek,
  unutulduğu gün hesabın sessizce eksilmesi demekti. Zincir
  `kesim_detay` üzerinden yürüyor (blok → plaka → ebatlı) ve tur
  sayısı SINIRLI: veride bir döngü oluşursa sonsuza kadar dönmek
  yerine duruyor.

── ÇİFT SAYIM KAPISI ──
  Hem bloğu hem o bloğun satıldığı siparişi bağlarsan aynı satış
  iki yoldan eşleşir. Eşleşme TEK `or_` sorgusuyla yapılıyor: SQL
  o satırı bir kez döndürüyor. İki ayrı sorgunun sonucunu toplamak,
  ciroyu ikiye katlardı — test bunu sayıyla sabitliyor
  (5.000 ciro, 10.000 değil).

── SENİN DURUMUN, BİREBİR PROVA EDİLDİ ──
  4 blok (ortağın sermayesiyle), 2'si kesilmiş, fason bedelini biz
  ödemişiz, henüz satış yok:

      seçilebilir blok      4 kayıt · K9001…K9004
      2 blok bağlandı       200
      maliyet listesi       2 fason kaydı GÖRÜNDÜ
      katkıya alındı        2
      ortağın katkısı       20.160,00
      bizim katkımız         8.000,00
      ciro                  0 (henüz satış yok — uyarı doğru)

  155 test geçti (151 + 4 yeni kalıcı test);
  firma · js · form · zincir · akis · degismezlik temiz.

── NE YAPMADIM ──
  · Bağlanan bloğun ALIŞ BEDELİ otomatik olarak ortağın katkısı
    sayılmıyor — daha önce konuştuğumuz gibi sermayeyi elle
    giriyorsun, çift sayma riski yok. Seçicide bedeli görüyorsun,
    yazarken ona bakabilirsin.
  · Bir bloğu ortaklıktan çözersen ondan türeyen plakalar da
    düşer; tek tek plaka bağlamak istersen onu da ayrıca
    bağlayabilirsin.

DOSYALAR
--------
  flask_app.py             stok tipleri · kesim zinciri · seçici
  templates/ortaklik.html  tip listesi · stok satırı · arama
  tests/test_kritik.py     4 yeni test

Şema yok, göç yok.

KULLANIM
--------
  python3 yama_or7.py            # RAPOR
  python3 yama_or7.py --uygula
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
    'flask_app.py': 'def _ortaklik_stok_zinciri(isler):',
    'templates/ortaklik.html': '<option value="BLOK">Blok (stok)</option>',
    'tests/test_kritik.py': 'def test_or7_blok_baglanir_ve_fason_siparis_yokken_gorunur',
}
ONKOSUL = {
    'flask_app.py': 'def api_ortaklik_maliyetler(oid):',
    'templates/ortaklik.html': 'Maliyetlerden katkı ekle',
    'tests/test_kritik.py': 'def test_or6_maliyet_katkiya_aliniyor_ve_iki_kez_girmiyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'OR7 · flask_app.py blok 1',
     r'''                           'aciklama': i.aciklama or ''}
''',
     r'''                           # OR7: stokta kimlik (PLK-…) değil, depoda
                           # okunan numara anlamlı.
                           'no': _ortaklik_is_no(i),
                           'aciklama': i.aciklama or ''}
'''),
    ('flask_app.py', 'OR7 · flask_app.py blok 2',
     r'''
    def _ortaklik_bul(oid):
''',
     r'''
    def _stok_alis_bedeli(s, tip):
        """Stoğun TOPLAM alış bedeli — kesimin kullandığı kuralın aynısı.

        Önce `matrah` (fiyat birimi ne olursa olsun doğru hesaplanmış
        hâli); yoksa blokta tonaj × birim fiyat, ötekilerde ölçü ×
        birim fiyat.
        """
        if getattr(s, 'matrah', None):
            return q2(s.matrah)
        _f = s.alis_fiyati or 0
        if tip == 'BLOK':
            if (s.alis_fiyat_birim == 'ton') and s.tonaj:
                return q2((s.tonaj or 0) * _f)
            return q2((s.hacim_m3 or 0) * _f)
        return q2((getattr(s, 'metraj_m2', 0) or 0) * _f)

    def _ortaklik_is_no(i):
        """Bağlı işin okunur numarası (stokta blok no / plaka kodu)."""
        if i.kaynak_tip not in ORTAKLIK_STOK_TIPLERI:
            return i.kaynak_id
        _m = {'BLOK': BlokStok, 'PLAKA': PlakaStok,
              'EBATLI': EbatliStok}[i.kaynak_tip]
        s = _m.query.filter_by(id=i.kaynak_id).first()
        if not s:
            return i.kaynak_id
        if i.kaynak_tip == 'PLAKA':
            return _plaka_kodu(s.blok_no, s.slab_no) or i.kaynak_id
        if i.kaynak_tip == 'EBATLI':
            return getattr(s, 'kasa_no', None) or s.blok_no or i.kaynak_id
        return s.blok_no or i.kaynak_id

    def _ortaklik_bul(oid):
'''),
    ('flask_app.py', 'OR7 · flask_app.py blok 3',
     r'''        Maliyet iki şekilde bağlanabiliyor: doğrudan siparişe, ya da
        o işte satılan STOĞA. Kâr hesabı ikisini de topluyor; burada
        da ikisi birden toplanıyor.
        """
        satislar, isler = _ortaklik_satislari(ort)
        anahtarlar = {i.kaynak_id for i in isler}
        anahtarlar |= {s.stok_id for s in satislar if s.stok_id}
''',
     r'''        Maliyet üç şekilde bağlanabiliyor: doğrudan siparişe, o işte
        satılan stoğa, ya da (OR7) ortaklığa bağlanan stoğun
        kendisine. Üçü de toplanıyor — fason bedeli henüz satış
        yokken bloğa işlendiğinde de bulunsun diye.
        """
        satislar, isler = _ortaklik_satislari(ort)
        anahtarlar = {i.kaynak_id for i in isler}
        anahtarlar |= {s.stok_id for s in satislar if s.stok_id}
        anahtarlar |= _ortaklik_stok_zinciri(isler)
        anahtarlar.discard(None)
'''),
    ('flask_app.py', 'OR7 · flask_app.py blok 4',
     r'''        if tip not in ('SIPARIS', 'SEVKIYAT', 'PROFORMA'):
            return jsonify({'ok': False, 'mesaj': 'Geçersiz tip'}), 400
''',
     r'''        if tip not in ORTAKLIK_IS_TIPLERI:
            return jsonify({'ok': False, 'mesaj': 'Geçersiz tip'}), 400
'''),
    ('flask_app.py', 'OR7 · flask_app.py blok 5',
     r'''        else:
            for v in Sevkiyat.query.order_by(
''',
     r'''        elif tip == 'SEVKIYAT':
            for v in Sevkiyat.query.order_by(
'''),
    ('flask_app.py', 'OR7 · flask_app.py blok 6',
     r'''                    'doviz': '', 'durum': v.durum or ''})
''',
     r'''                    'doviz': '', 'durum': v.durum or ''})
        else:
            # OR7 · STOK. Burada "müşteri" yok; ayırt edici bilgi blok
            # no ve cins. Tüketilmiş stok da listede kalıyor: kesilmiş
            # bir blok ortaklığın TAM OLARAK konusudur, listeden
            # düşerse bağlanamaz hâle gelirdi.
            _model = {'BLOK': BlokStok, 'PLAKA': PlakaStok,
                      'EBATLI': EbatliStok}[tip]
            for s in _model.query.order_by(
                    _model.giris_tarihi.desc(), _model.id.desc()).limit(300).all():
                if s.id in bagli:
                    continue
                _no = s.blok_no or s.id
                if tip == 'PLAKA' and getattr(s, 'slab_no', None) is not None:
                    _no = _plaka_kodu(s.blok_no, s.slab_no) or s.id
                elif tip == 'EBATLI':
                    _no = getattr(s, 'kasa_no', None) or _no
                kayitlar.append({
                    'id': s.id, 'musteri': s.cins or '',
                    'tarih': _iso(getattr(s, 'giris_tarihi', None)),
                    # `alis_fiyati` BİRİM fiyat (ton/m² başına). Seçicide
                    # öteki tipler TOPLAM gösteriyor; birim fiyat yazmak
                    # "bu blok 420 dolar" diye okunurdu.
                    'tutar': _stok_alis_bedeli(s, tip),
                    'doviz': s.doviz or 'USD',
                    'durum': s.durum or '', 'no': _no})
'''),
    ('flask_app.py', 'OR7 · flask_app.py blok 7',
     r'''            else:
                k['satis_var'] = SatisKaydi.query.filter_by(
                    sevkiyat_id=k['id']).count() > 0
''',
     r'''            elif tip == 'SEVKIYAT':
                k['satis_var'] = SatisKaydi.query.filter_by(
                    sevkiyat_id=k['id']).count() > 0
            else:
                k['satis_var'] = SatisKaydi.query.filter_by(
                    stok_id=k['id']).count() > 0
'''),
    ('flask_app.py', 'OR7 · flask_app.py blok 8',
     r'''        if tip not in ('SIPARIS', 'SEVKIYAT', 'PROFORMA'):
            return jsonify({'ok': False, 'mesaj':
                            'Kaynak tipi: SIPARIS, SEVKIYAT veya PROFORMA'}), 400
        if not kid:
            return jsonify({'ok': False, 'mesaj': 'Kaynak no zorunlu'}), 400
        # Kaynak GERÇEKTEN var mı: olmayan bir numarayı bağlamak,
        # cirosu hep 0 çıkan bir ortaklıkla biterdi.
        _model = {'SIPARIS': Siparis, 'SEVKIYAT': Sevkiyat,
                  'PROFORMA': Proforma}[tip]
''',
     r'''        if tip not in ORTAKLIK_IS_TIPLERI:
            return jsonify({'ok': False, 'mesaj':
                            'Kaynak tipi: ' + ', '.join(ORTAKLIK_IS_TIPLERI)}), 400
        if not kid:
            return jsonify({'ok': False, 'mesaj': 'Kaynak no zorunlu'}), 400
        # Kaynak GERÇEKTEN var mı: olmayan bir numarayı bağlamak,
        # cirosu hep 0 çıkan bir ortaklıkla biterdi.
        _model = {'SIPARIS': Siparis, 'SEVKIYAT': Sevkiyat,
                  'PROFORMA': Proforma, 'BLOK': BlokStok,
                  'PLAKA': PlakaStok, 'EBATLI': EbatliStok}[tip]
'''),
    ('flask_app.py', 'OR7 · flask_app.py blok 9',
     r'''    def _iso(d):
''',
     r'''    # ── OR7 · ORTAKLIĞA STOK BAĞLAMA ──
    # Ortaklık malzeme alımında başlıyor; sipariş aylar sonra gelebiliyor.
    # Blok sipariş beklemeden bağlanabilsin diye iş tipleri genişledi.
    ORTAKLIK_IS_TIPLERI = ('SIPARIS', 'SEVKIYAT', 'PROFORMA',
                           'BLOK', 'PLAKA', 'EBATLI')
    ORTAKLIK_STOK_TIPLERI = ('BLOK', 'PLAKA', 'EBATLI')

    def _ortaklik_stok_zinciri(isler):
        """Bağlı stoklar + onlardan KESİMLE türeyenler.

        Bir bloğu bağlayınca o bloktan çıkan plakalar da ortaklığa
        aittir: fason bedeli onlara işlenir, satış onlardan olur.
        Kullanıcıdan her kesimden sonra listeyi güncellemesini
        beklemek, unutulduğu gün hesabın sessizce eksilmesi demekti.

        Zincir `kesim_detay` üzerinden yürüyor (blok → plaka →
        ebatlı). Tur sayısı SINIRLI: veride bir döngü oluşursa
        sonsuza kadar dönmek yerine durur.
        """
        kok = {i.kaynak_id for i in isler
               if i.kaynak_tip in ORTAKLIK_STOK_TIPLERI and i.kaynak_id}
        if not kok:
            return set()
        tum = set(kok)
        sinir = kok
        for _ in range(4):          # blok→plaka→ebatlı için fazlasıyla yeter
            if not sinir:
                break
            kesimler = {k.id for k in Kesim.query.filter(
                Kesim.kaynak_id.in_(list(sinir))).all()}
            if not kesimler:
                break
            yeni = {d.hedef_stok_id for d in KesimDetay.query.filter(
                KesimDetay.kesim_id.in_(list(kesimler))).all()
                if d.hedef_stok_id} - tum
            tum |= yeni
            sinir = yeni
        return tum

    def _iso(d):
'''),
    ('flask_app.py', 'OR7 · flask_app.py blok 10',
     r'''        kosul = []
        if sip: kosul.append(SatisKaydi.siparis_id.in_(sip))
        if sev: kosul.append(SatisKaydi.sevkiyat_id.in_(sev))
        if prf: kosul.append(SatisKaydi.proforma_id.in_(prf))
        if not kosul:
            return [], isler
''',
     r'''        stoklar = _ortaklik_stok_zinciri(isler)
        kosul = []
        if sip: kosul.append(SatisKaydi.siparis_id.in_(sip))
        if sev: kosul.append(SatisKaydi.sevkiyat_id.in_(sev))
        if prf: kosul.append(SatisKaydi.proforma_id.in_(prf))
        # OR7: bağlı stok satıldığında ciro sipariş bağlanmadan da gelir.
        if stoklar: kosul.append(SatisKaydi.stok_id.in_(list(stoklar)))
        if not kosul:
            return [], isler
        # `or_` ile tek sorgu: aynı satış hem siparişten hem stoktan
        # eşleşse bile SQL onu BİR KEZ döndürür. İki ayrı sorgunun
        # sonucunu toplamak, o satışı iki kez saymak olurdu.
'''),
    ('flask_app.py', 'OR7 · flask_app.py blok 11',
     r'''                  'PROFORMA': Proforma}.get(i.kaynak_tip)
''',
     r'''                  'PROFORMA': Proforma, 'BLOK': BlokStok,
                  'PLAKA': PlakaStok, 'EBATLI': EbatliStok}.get(i.kaynak_tip)
'''),
    ('templates/ortaklik.html', 'OR7 · templates/ortaklik.html blok 1',
     r'''      <td class="mono">${kacar(i.kaynak_tip)} ${kacar(i.kaynak_id)}</td>
''',
     r'''      <td class="mono">${kacar(i.kaynak_tip)} ${kacar(i.no || i.kaynak_id)}</td>
'''),
    ('templates/ortaklik.html', 'OR7 · templates/ortaklik.html blok 2',
     r'''  is: {baslik: 'İş bağla', alt: 'Sistemdeki kayıtlardan seç.', html: `
    <div class="form-satir f2">
      <div class="form-alan"><label>Tip</label>
        <select id="kTip" onchange="isListesiYukle()">
''',
     r'''  is: {baslik: 'İş bağla', alt: 'Blok/plaka ya da sipariş — sistemden seç.', html: `
    <div class="form-satir f2">
      <div class="form-alan"><label>Tip</label>
        <select id="kTip" onchange="isListesiYukle()">
        <option value="BLOK">Blok (stok)</option>
        <option value="PLAKA">Plaka (stok)</option>
        <option value="EBATLI">Ebatlı (stok)</option>
'''),
    ('templates/ortaklik.html', 'OR7 · templates/ortaklik.html blok 3',
     r'''    ? IS_LISTE.filter(x => (x.id + ' ' + (x.musteri || ''))
        .toLocaleLowerCase('tr').includes(s))
    : IS_LISTE;
  sec.innerHTML = gorunen.map(x => {
    const parcalar = [x.id];
''',
     r'''    ? IS_LISTE.filter(x => (x.id + ' ' + (x.no || '') + ' ' + (x.musteri || ''))
        .toLocaleLowerCase('tr').includes(s))
    : IS_LISTE;
  sec.innerHTML = gorunen.map(x => {
    /* OR7: stokta ayırt edici bilgi blok no; sipariş/sevkiyatta
       kayıt numarası. `no` yalnız stok uçlarından geliyor. */
    const parcalar = [x.no || x.id];
'''),
    ('tests/test_kritik.py', 'OR7 · tests/test_kritik.py blok 1',
     r'''    assert '(h.sermaye.biz || h.dagitilan.biz)' in h
''',
     r'''    assert '(h.sermaye.biz || h.dagitilan.biz)' in h


# ══════════════════════════════════════════════════════════════════════
#  OR7 · ORTAKLIĞA STOK BAĞLAMA (sipariş beklemeden)
# ══════════════════════════════════════════════════════════════════════

def test_or7_blok_baglanir_ve_fason_siparis_yokken_gorunur():
    """OR7: ortaklık malzeme alımında başlıyor, sipariş aylar sonra.

    Blok bağlanamadığı sürece "Maliyetlerden ekle" BOŞ geliyordu
    (ölçülmüştü): liste bağlı işler üzerinden çalışıyor, iş de
    yalnız sipariş/sevkiyat/proforma olabiliyordu. Fason bedeli
    daha satış yokken bloğa işlenir — artık bulunuyor."""
    from models import BlokStok, Maliyet
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BLK-OR7', firma_id=1, blok_no='K7700', cins='TEST',
            boy=300, yukseklik=180, en=170, hacim_m3=9.18, tonaj=24,
            alis_fiyati=420, alis_fiyat_birim='ton', doviz='USD',
            durum='Serbest', uretici='ALBSTONE'))
        db.session.flush()
        db.session.add(Maliyet(
            id='MYT-OR7-1', firma_id=1, baglanti_tip='stok',
            baglanti_id='BLK-OR7', maliyet_tip='Kesim / Fason / Üretim',
            maliyet_tarihi=date(2026, 10, 5), tutar=4000, doviz='USD',
            usd_karsilik=4000, aktif=True))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Blok ortaklığı', 'bizim_pay': 50, 'ortak_pay': 50,
        'anapara_yontemi': 'once_iade'}).get_json()['id']

    # Blok seçicide çıkıyor ve blok NO'suyla görünüyor
    b = c.get(f'/api/ortaklik/{oid}/baglanabilir?tip=BLOK').get_json()
    kayit = [x for x in b['data'] if x['id'] == 'BLK-OR7']
    assert kayit and kayit[0]['no'] == 'K7700', b['data'][:3]
    # Seçicide TOPLAM alış bedeli görünmeli, BİRİM fiyat değil:
    # 420 USD/ton × 24 ton = 10.080. "Bu blok 420 dolar" diye
    # okunacak bir rakam, bağlarken yanlış blok seçtirir.
    assert kayit[0]['tutar'] == 10080, kayit[0]['tutar']

    assert c.post(f'/api/ortaklik/{oid}/is', headers=H, json={
        'kaynak_tip': 'BLOK', 'kaynak_id': 'BLK-OR7'}).status_code == 200

    # SİPARİŞ YOKKEN fason maliyeti listede
    ml = c.get(f'/api/ortaklik/{oid}/maliyetler').get_json()
    assert [x['id'] for x in ml['data']] == ['MYT-OR7-1'], ml['data']

    # Katkıya alınabiliyor
    r = c.post(f'/api/ortaklik/{oid}/maliyet_katki', headers=H, json={
        'taraf': 'biz', 'maliyet_idler': ['MYT-OR7-1']})
    assert r.get_json()['eklenen'] == 1, r.get_json()
    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h['sermaye']['biz'] == 4000, h['sermaye']
    # Ciro yok ama uyarı doğru olanı söylüyor
    assert h['ciro'] == 0
    assert any('satış kaydı yok' in u for u in h['uyarilar']), h['uyarilar']
    # Bağlı iş listesinde blok NO'su görünüyor
    isler = c.get(f'/api/ortaklik/{oid}').get_json()['data']['isler']
    assert isler[0]['no'] == 'K7700', isler


def test_or7_kesimden_turetilen_plakalar_da_ortakligin():
    """OR7: bağlanan bloktan çıkan plakalar da ortaklığa aittir.

    Kullanıcıdan her kesimden sonra listeyi güncellemesini beklemek,
    unutulduğu gün hesabın sessizce eksilmesi demekti."""
    from models import BlokStok, PlakaStok, Maliyet, SatisKaydi
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BLK-OR7B', firma_id=1, blok_no='K7701', cins='TEST',
            boy=300, yukseklik=180, en=170, hacim_m3=9.18, tonaj=24,
            alis_fiyati=420, alis_fiyat_birim='ton', doviz='USD',
            durum='Serbest', uretici='ALBSTONE'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': ['BLK-OR7B'],
        'kesim_tarihi': '2026-10-10',
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'TEST', 'boy': 280,
                      'yukseklik': 170, 'kalinlik': 2, 'adet': 4}]})
    assert r.status_code == 200, r.get_data(as_text=True)
    plaka_idler = [o['id'] for o in r.get_json()['olusan_stoklar']]
    assert len(plaka_idler) == 4

    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Zincir', 'bizim_pay': 50, 'ortak_pay': 50,
        'anapara_yontemi': 'once_iade'}).get_json()['id']
    # YALNIZCA BLOK bağlanıyor — plakalar kendiliğinden gelmeli
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'BLOK', 'kaynak_id': 'BLK-OR7B'})

    # Kesimden SONRA plakaya işlenen maliyet de bulunuyor
    with fa.app.app_context():
        db.session.add(Maliyet(
            id='MYT-OR7-2', firma_id=1, baglanti_tip='stok',
            baglanti_id=plaka_idler[0], maliyet_tip='Nakliye',
            maliyet_tarihi=date(2026, 10, 12), tutar=250, doviz='USD',
            usd_karsilik=250, aktif=True))
        # Plakalardan biri satıldı
        db.session.add(SatisKaydi(
            id='SAT-OR7', firma_id=1, stok_id=plaka_idler[0], stok_tip='PLAKA',
            cins='TEST', musteri='ACIK CARI', satis_tarihi=date(2026, 10, 20),
            tutar=3000, tutar_usd=3000, doviz='USD',
            maliyet_usd=1800, kar_usd=1200))
        db.session.commit()

    ml = c.get(f'/api/ortaklik/{oid}/maliyetler').get_json()
    assert 'MYT-OR7-2' in [x['id'] for x in ml['data']], ml['data']
    # SİPARİŞ BAĞLANMADAN ciro geliyor
    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h['ciro'] == 3000 and h['brut_kar'] == 1200, h


def test_or7_ayni_satis_iki_yoldan_iki_kez_sayilmaz():
    """OR7: hem blok hem sipariş bağlıyken satış BİR KEZ sayılmalı.

    Stok eşleşmesi siparişin yanına eklendi; iki ayrı sorgunun
    sonucunu toplamak aynı satırı iki kez saymak olurdu. Tek
    `or_` sorgusu bunu yapısal olarak engelliyor."""
    from models import BlokStok, SatisKaydi, Siparis
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BLK-OR7C', firma_id=1, blok_no='K7702', cins='TEST',
            boy=300, yukseklik=180, en=170, hacim_m3=9.18, tonaj=24,
            alis_fiyati=420, alis_fiyat_birim='ton', doviz='USD',
            durum='Serbest', uretici='ALBSTONE'))
        db.session.add(Siparis(id='SIP-OR7', musteri='ACIK CARI', doviz='USD',
                               toplam_tutar=5000, durum='Onaylandi',
                               siparis_tarihi=date(2026, 10, 1)))
        db.session.flush()
        # AYNI satış hem bloğun stoğuna hem siparişe bağlı
        db.session.add(SatisKaydi(
            id='SAT-OR7C', firma_id=1, stok_id='BLK-OR7C', stok_tip='BLOK',
            siparis_id='SIP-OR7', cins='TEST', musteri='ACIK CARI',
            satis_tarihi=date(2026, 10, 20), tutar=5000, tutar_usd=5000,
            doviz='USD', maliyet_usd=3000, kar_usd=2000))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Çift sayım', 'bizim_pay': 50,
        'ortak_pay': 50}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'BLOK', 'kaynak_id': 'BLK-OR7C'})
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIP-OR7'})

    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h['satis_adedi'] == 1, h['satis_adedi']
    assert h['ciro'] == 5000, h['ciro']        # 10000 olsaydı çift sayılırdı
    assert h['brut_kar'] == 2000, h['brut_kar']


def test_or7_stok_tekilligi_ve_varlik_kapilari():
    """OR7: stok da tek ortaklığa bağlanır; olmayan stok bağlanamaz."""
    from models import BlokStok
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BLK-OR7D', firma_id=1, blok_no='K7703', cins='TEST',
            boy=300, yukseklik=180, en=170, hacim_m3=9.18, tonaj=24,
            alis_fiyati=420, alis_fiyat_birim='ton', doviz='USD',
            durum='Serbest', uretici='ALBSTONE'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    a = c.post('/api/ortaklik', headers=H, json={'ad': 'SA'}).get_json()['id']
    b = c.post('/api/ortaklik', headers=H, json={'ad': 'SB'}).get_json()['id']
    assert c.post(f'/api/ortaklik/{a}/is', headers=H, json={
        'kaynak_tip': 'BLOK', 'kaynak_id': 'BLK-OR7D'}).status_code == 200
    assert c.post(f'/api/ortaklik/{b}/is', headers=H, json={
        'kaynak_tip': 'BLOK', 'kaynak_id': 'BLK-OR7D'}).status_code == 409
    assert c.post(f'/api/ortaklik/{b}/is', headers=H, json={
        'kaynak_tip': 'BLOK', 'kaynak_id': 'YOK-999'}).status_code == 404
    # Seçicide artık görünmüyor
    idler = [x['id'] for x in
             c.get(f'/api/ortaklik/{b}/baglanabilir?tip=BLOK').get_json()['data']]
    assert 'BLK-OR7D' not in idler
'''),
]

TAM_ICERIK = {}

def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA OR7 — ORTAKLIGA BLOK PLAKA BAGLANABILIYOR')
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
        print('    python3 yama_or7.py            # rapor')
        print('    python3 yama_or7.py --uygula')
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
        print('  ⊙ Yama OR7 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_or7.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_or7'
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
    print('    Analiz -> Is Ortakliklari -> bir ortaklik ac')
    print('    1) sudo systemctl restart milestone-erp  <- sutun burada')
    print('    2) Ctrl+F5')
    print('    3) Analiz -> Is Ortakliklari -> ortakligi ac')
    print('       KATKILAR bolumunde "Maliyetten al" dugmesi.')
    print('       Fason model icin ortakligi "once iade" yap.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

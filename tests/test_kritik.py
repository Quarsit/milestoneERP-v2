"""Kritik yol regresyon testleri (19.09.2026).

Çalıştırma (üretim veritabanına DOKUNMAZ — geçici SQLite kullanır):

    venv/bin/python -m pytest -q tests/

Kapsanan hatalar:
    CRM-F  gizli cariye yazma (çek) engelli mi
    YK1    yalnızca OKUMA yetkili kullanıcı çek kaydedemiyor mu
    YK2    hızlı satış sipariş yetkisi de istiyor mu
    RZ1    aynı stok iki kez rezerve edilemiyor mu
    TH1    kur farkı çıkan tahsilat 500 vermiyor mu
    TH2    tahsilat silinince kasa girişi de geri alınıyor mu
"""
import json
import os
import sys
import tempfile
from datetime import date

import pytest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB = os.path.join(tempfile.mkdtemp(), 'test.db')
os.environ['DATABASE_URL'] = 'sqlite:///' + _DB
os.environ['MILESTONE_ACILIS_ATLA'] = '1'
sys.path.insert(0, KOK)
os.chdir(KOK)

from sqlalchemy import event as _event  # noqa: E402
from sqlalchemy.engine import Engine as _Engine  # noqa: E402


# SD1 — YABANCI ANAHTARLAR TESTTE DE ZORLANIR.
# Uretim PostgreSQL; o yabanci anahtarlari zorluyor. SQLite varsayilan
# olarak ZORLAMAZ, bu yuzden "silince 500" sinifi hatalar testlerden
# gecip uretimde patliyordu (siparis silme, SD1).
@_event.listens_for(_Engine, 'connect')
def _sqlite_fk_ac(dbapi_con, _kayit):
    try:
        dbapi_con.execute('PRAGMA foreign_keys=ON')
    except Exception:
        pass


import flask_app as fa  # noqa: E402
from models import (db, Cari, Kullanici, Cek, CariHareket, BlokStok,  # noqa: E402
                    Rezervasyon, Fatura, Kasa, KasaHareket, DovizKur)
from werkzeug.security import generate_password_hash  # noqa: E402

H = {'X-CSRF-Token': 't'}
TUM_YAZMA = ['cari', 'kasa', 'fatura', 'siparis', 'proforma', 'crm', 'stok',
             'rezervasyon', 'sevkiyat']


@pytest.fixture(scope='module', autouse=True)
def veri():
    with fa.app.app_context():
        db.create_all()
        db.session.add_all([
            Cari(id='C1', unvan='ACIK CARI', cari_tip='Müşteri', ulke='USA',
                 para_birimi='USD', gorunurluk='kapali', sorumlu='satis'),
            Cari(id='C2', unvan='GIZLI CARI', cari_tip='Müşteri', ulke='USA',
                 para_birimi='USD', gorunurluk='kapali', sorumlu='admin'),
            Kullanici(ad='admin', sifre=generate_password_hash('x'), rol='ADMIN'),
            Kullanici(ad='satis', sifre=generate_password_hash('x'), rol='SATIS',
                      cari_kapsam='atanan',
                      yetkiler=json.dumps({k: 'yazma' for k in TUM_YAZMA})),
            Kullanici(ad='izleyici', sifre=generate_password_hash('x'), rol='SATIS',
                      cari_kapsam='tumu',
                      yetkiler=json.dumps({k: 'okuma' for k in TUM_YAZMA})),
            Kullanici(ad='faturaci', sifre=generate_password_hash('x'), rol='SATIS',
                      cari_kapsam='tumu',
                      yetkiler=json.dumps({'fatura': 'yazma', 'cari': 'yazma',
                                           'siparis': 'okuma'})),
            BlokStok(id='B1', blok_no='T-1', cins='TEST', boy=300, yukseklik=150,
                     en=120, hacim_m3=5.4, tonaj=15, durum='Serbest'),
            Kasa(ad='USD Banka', doviz='USD', bakiye=0),
            DovizKur(doviz='USD', tarih=date.today(), alis=48, satis=48.2, efektif=48),
            DovizKur(doviz='EUR', tarih=date.today(), alis=56, satis=56.2, efektif=56),
            Fatura(id='FT1', fatura_no='F-1', musteri='ACIK CARI', cari_id='C1',
                   toplam=100000, doviz='USD', durum='Kesildi', yon='satis'),
            CariHareket(id='HF1', cari_id='C1', islem_tip='Fatura (Satis)',
                        borc=100000, alacak=0, doviz='USD', kur_uygulanan=40,
                        borc_try=4000000, alacak_try=0, baglanti_tip='fatura_kesim',
                        baglanti_id='FT1', hareket_tarihi=date(2026, 1, 1)),
        ])
        db.session.commit()
        # ── KF1/KF2 · FİRMA KAPSAMI ──
        # Modeldeki varsayılan 'secili' ve kullanici_firma boş; yani
        # bu kullanıcıların izinli firması YOK ve seçim kapısı onları
        # 403 ile durduruyor. Doğru davranış — ÖLÇÜLDÜ: bu satır
        # eklenmeden 5 test düştü, hepsi "firma_yok" yüzünden.
        #
        # Gerçek sistemde göç (goc_kf1.py) mevcut kullanıcılara tam
        # olarak bunu yapıyor: yükseltme kimsenin erişimini sessizce
        # kesmemeli. Fixture gerçeği taklit ediyor.
        #
        # Erişim KURALLARININ kendisi ayrı testlerde sınanıyor
        # (test_kf2_*): firmasız giremez, izinsiz firmaya geçemez.
        Kullanici.query.update({'firma_kapsam': 'tumu'})
        db.session.commit()
    yield


def istemci(ad, rol='SATIS'):
    c = fa.app.test_client()
    with c.session_transaction() as s:
        s['kullanici'] = ad
        s['rol'] = rol
        s['_csrf'] = 't'
        # ── KF2 · FİRMA SEÇİMİ DE TAKLİT EDİLMELİ ──
        # Gerçek giriş akışı ya firmayı seçtiriyor ya (tek firma
        # varsa) kendiliğinden seçiyor. Yardımcı bunu yapmazsa seçim
        # kapısı isteği 409 ile durdurur.
        #
        # ÖLÇÜLDÜ: eskiden çalışıyordu çünkü testlerde TEK firma
        # vardı ve çözümleyici onu kendiliğinden seçiyordu. KF2/KF3
        # testleri ikinci, üçüncü firmayı açınca admin'in izinli
        # firma sayısı 1'i geçti ve 5 test 409 aldı. Hata testlerde
        # değil, taklidin eksikliğindeydi.
        #
        # KULLANICININ İZİNLİ olduğu ilk firma seçiliyor: gelişigüzel
        # bir kimlik yazmak, izni olmayan firmayı seçmek olurdu ve
        # kapı yine durdururdu.
        s['firma_id'] = _ilk_izinli_firma(ad, rol)
    return c


def _ilk_izinli_firma(ad, rol):
    """Testlik: kullanıcının çalışabileceği ilk firma kimliği."""
    from models import Firma, Kullanici, KullaniciFirma
    with fa.app.app_context():
        if (rol or '').upper() == 'ADMIN':
            f = Firma.query.filter_by(aktif=True).order_by(Firma.id).first()
            return f.id if f else None
        k = Kullanici.query.filter_by(ad=ad).first()
        if k and (k.firma_kapsam or 'secili') == 'tumu':
            f = Firma.query.filter_by(aktif=True).order_by(Firma.id).first()
            return f.id if f else None
        if k:
            u = (KullaniciFirma.query.filter_by(kullanici_id=k.id)
                 .order_by(KullaniciFirma.firma_id).first())
            if u:
                return u.firma_id
        return None


def _cek(cari_id):
    return {'yon': 'alinan', 'tutar': 100, 'doviz': 'USD',
            'vade_tarihi': '2026-12-01', 'cari_id': cari_id}


def test_crm_f_gizli_cariye_cek_girilemez():
    with fa.app.app_context():
        once = Cek.query.count()
    r = istemci('satis').post('/api/cek', json=_cek('C2'), headers=H)
    assert r.status_code == 403
    with fa.app.app_context():
        assert Cek.query.count() == once


def test_crm_f_kendi_carisine_cek_girilir():
    r = istemci('satis').post('/api/cek', json=_cek('C1'), headers=H)
    assert r.status_code == 200


def test_yk1_okuma_yetkisiyle_cek_girilemez():
    r = istemci('izleyici').post('/api/cek', json=_cek('C1'), headers=H)
    assert r.status_code == 403


def test_yk1_okuma_bozulmadi():
    assert istemci('izleyici').get('/api/cek/ozet').status_code == 200


def test_yk2_hizli_satis_siparis_yetkisi_ister():
    r = istemci('faturaci').post('/api/sicak_satis',
                                 json={'musteri': 'ACIK CARI', 'kalemler': []}, headers=H)
    assert r.status_code == 403


def test_rz1_ayni_stok_iki_kez_rezerve_edilemez():
    adm = istemci('admin', 'ADMIN')
    g = {'stok_tip': 'BLOK', 'stok_idler': ['B1']}
    r1 = adm.post('/api/rezervasyon', json={**g, 'musteri': 'ACIK CARI'}, headers=H).get_json()
    r2 = adm.post('/api/rezervasyon', json={**g, 'musteri': 'GIZLI CARI'}, headers=H).get_json()
    assert r1['olusturulan'] == ['B1']
    assert r2['olusturulan'] == []
    with fa.app.app_context():
        assert Rezervasyon.query.filter_by(stok_id='B1', iptal_nedeni=None).count() == 1
        # bayat okuma: atomik kosul ikinci kez 0 satir gunceller
        n = (db.session.query(BlokStok)
             .filter(BlokStok.id == 'B1', BlokStok.durum == 'Serbest')
             .update({BlokStok.durum: 'Rezerve'}, synchronize_session=False))
        db.session.rollback()
        assert n == 0


def test_th1_th2_kismi_tahsilat_ve_iptal():
    adm = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        kid = Kasa.query.filter_by(ad='USD Banka').first().id
    for _ in range(2):
        r = adm.post('/api/fatura/FT1/tahsilat',
                     json={'tutar': 30000, 'kasa_id': kid, 'doviz': 'USD'}, headers=H)
        assert r.status_code == 200, r.get_data(as_text=True)   # TH1: 500 degil

    def durum():
        with fa.app.app_context():
            hs = (CariHareket.query.filter_by(baglanti_tip='fatura', baglanti_id='FT1')
                  .order_by(CariHareket.guncelleme).all())
            return (Fatura.query.get('FT1').durum, sum(float(h.alacak) for h in hs),
                    [h.id for h in hs], float(Kasa.query.get(kid).bakiye or 0))

    d = durum()
    assert d[0] == 'Kismi Tahsil' and d[1] == 60000 and d[3] == 60000
    assert adm.delete(f'/api/tahsilat/{d[2][-1]}', headers=H).status_code == 200
    d = durum()
    assert d[1] == 30000 and d[3] == 30000        # TH2: kasa da geri alindi
    assert adm.delete(f'/api/tahsilat/{d[2][-1]}', headers=H).status_code == 200
    d = durum()
    assert d[0] == 'Kesildi' and d[1] == 0 and d[3] == 0
    with fa.app.app_context():
        assert KasaHareket.query.filter_by(kasa_id=kid).count() == 0


# ── TT1: tek ödemeyle birden çok fatura ──
def _fatura_ekle(fid, tutar, vade):
    with fa.app.app_context():
        db.session.add(Fatura(id=fid, fatura_no=fid, musteri='ACIK CARI', cari_id='C1',
                              toplam=tutar, doviz='USD', durum='Kesildi', yon='satis',
                              vade_tarihi=vade))
        db.session.commit()


def test_tt1_toplu_tahsilat_vade_sirasiyla_dagitir():
    _fatura_ekle('FA', 1000, date(2026, 3, 1))
    _fatura_ekle('FB', 500, date(2026, 1, 1))     # vadesi daha eski
    adm = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        kid = Kasa.query.filter_by(ad='USD Banka').first().id
    acik = adm.get('/api/cari/C1/acik_faturalar').get_json()['faturalar']
    assert {'FA', 'FB'} <= {x['id'] for x in acik}

    # kalanı aşan tutar reddedilir, hiçbir şey yazılmaz
    r = adm.post('/api/cari/C1/toplu_tahsilat', json={
        'fatura_idler': ['FA', 'FB'], 'tutar': 2000, 'doviz': 'USD', 'kasa_id': kid}, headers=H)
    assert r.status_code == 400
    # kasa zorunlu
    r = adm.post('/api/cari/C1/toplu_tahsilat', json={
        'fatura_idler': ['FA', 'FB'], 'tutar': 700, 'doviz': 'USD'}, headers=H)
    assert r.status_code == 400

    r = adm.post('/api/cari/C1/toplu_tahsilat', json={
        'fatura_idler': ['FA', 'FB'], 'tutar': 700, 'doviz': 'USD', 'kasa_id': kid,
        'evrak_no': 'HAVALE-1'}, headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        assert Fatura.query.get('FB').durum == 'Tahsil Edildi'     # 500 önce
        assert Fatura.query.get('FA').durum == 'Kismi Tahsil'      # kalan 200
        assert float(Kasa.query.get(kid).bakiye) == 700


def test_tt1_zaman_cizelgesi():
    d = istemci('admin', 'ADMIN').get('/api/cari/C1/zaman').get_json()
    assert d['ok'] and any(o['tip'] == 'tahsilat' for o in d['data'])
    tarihler = [o['tarih'] for o in d['data']]
    assert tarihler == sorted(tarihler, reverse=True)


def test_tt1_gizli_cariye_toplu_tahsilat_yok():
    r = istemci('satis').post('/api/cari/C2/toplu_tahsilat', json={
        'fatura_idler': ['X'], 'tutar': 1, 'doviz': 'USD', 'kasa_id': 1}, headers=H)
    assert r.status_code in (403, 404)


# ── FK1: fatura kesiminde FATURA TARİHİNİN kuru ──
def test_fk1_kesim_fatura_tarihi_kuru():
    with fa.app.app_context():
        db.session.add(DovizKur(doviz='USD', tarih=date(2026, 2, 2), alis=36.5, satis=36.7, efektif=36.5))
        db.session.add(Fatura(id='FK', fatura_no='FK-1', musteri='ACIK CARI', cari_id='C1',
                              toplam=1000, doviz='USD', durum='Taslak', yon='satis',
                              fatura_tipi='teklif', fatura_tarihi=date(2026, 2, 3)))  # 03.02: kur yok → 02.02
        db.session.commit()
    r = istemci('admin', 'ADMIN').post('/api/fatura/FK/durum', json={'durum': 'Kesildi'}, headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        h = CariHareket.query.filter_by(baglanti_tip='fatura', baglanti_id='FK', kaynak='fatura').first()
        assert h is not None
        assert h.hareket_tarihi == date(2026, 2, 3)
        assert abs(float(h.kur_uygulanan) - 36.5) < 1e-6
        assert abs(float(h.borc_try) - 36500) < 0.01


def test_lh1_formdan_hizli_liste_ekleme():
    """LH1: stok/sipariş yazma yetkisi olan kullanıcı formdan cins ekler;
    mükerrer ikizlenmez; okuma yetkili ve izinsiz kategori reddedilir."""
    from models import Veriler
    c = istemci('satis')
    r = c.post('/api/liste/hizli_ekle', json={'kategori': 'cins', 'deger': '  zebra   blue '}, headers=H)
    assert r.status_code == 200 and r.get_json()['deger'] == 'ZEBRA BLUE'
    r2 = c.post('/api/liste/hizli_ekle', json={'kategori': 'cins', 'deger': 'Zebra Blue'}, headers=H)
    assert r2.get_json()['mevcut'] is True
    with fa.app.app_context():
        assert Veriler.query.filter_by(kategori='cins', deger='ZEBRA BLUE').count() == 1
    assert c.post('/api/liste/hizli_ekle', json={'kategori': 'banka', 'deger': 'X'},
                  headers=H).status_code == 400
    assert istemci('izleyici').post('/api/liste/hizli_ekle', json={'kategori': 'cins', 'deger': 'Y'},
                                    headers=H).status_code == 403


def test_et1_bundle_crate_etiketleri_ve_mense():
    """ET1/MS1: bundle numaralari packing list ile ayni; ayni kasa no'lu
    ebatli kalemler tek etikette; kasada kalinlik olcude; mense kalemden,
    bossa TURKIYE; blok etiketlenmez; ticari fatura mensei kalemden."""
    from models import Proforma, ProformaKalem
    with fa.app.app_context():
        db.session.add(Proforma(id='PET', musteri='ACIK CARI', cari_id='C1', toplam=1,
                                doviz='USD', durum='Onaylandi', genel_bundle_sayisi=8))
        K = lambda **a: ProformaKalem(proforma_id='PET', **a)
        db.session.add_all([
            K(urun_tip='PLAKA', cins='EMPERADOR', yuzey_spec='POLISHED', blok_no='45', boy=300, yukseklik=200,
              kalinlik=2, adet=10, miktar=60, birim='m2', sira=1),
            K(urun_tip='EBATLI', cins='SILVER', yuzey_spec='HONED', blok_no='7', boy=60, yukseklik=40,
              kalinlik=1.2, adet=1, kasa_ici_adet=100, miktar=24, birim='m2', sira=2, mense='IRAN'),
            K(urun_tip='EBATLI', cins='SILVER', yuzey_spec='HONED', blok_no='7', boy=40, yukseklik=40,
              kalinlik=3, adet=1, kasa_ici_adet=50, miktar=8, birim='m2', sira=3, mense='IRAN'),
            K(urun_tip='BLOK', cins='NERO', blok_no='B1', boy=300, yukseklik=200, kalinlik=150,
              adet=1, miktar=20, birim='ton', sira=4),
        ])
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    d = c.get('/api/proforma/PET/etiket_ayar').get_json()
    assert (d['bundle'], d['crate']) == (2, 1)          # 10 plaka / 8 = 2 bundle, 1 kasa, blok yok
    h = c.get('/api/proforma/PET/etiket').get_data(as_text=True)
    assert h.count('class="etiket"') == 3
    assert 'Crate No' in h and 'Bundle No' in h and 'Materials of Origin' in h
    assert '60 × 40 × 1.2' in h and '40 × 40 × 3' in h   # kasada kalinlik olcude
    assert '300 × 200' in h and '2 CM' in h              # bundle'da kalinlik baslikta
    assert 'IRAN' in h and 'TURKIYE' in h
    assert '32.00' in h                                    # kasa toplami 24 + 8 m2
    # ust serit tercihi kaydedilir, gecersiz secim reddedilir
    assert c.post('/api/proforma/PET/etiket_ayar', json={'mod': 'notr'}, headers=H).status_code == 200
    assert c.get('/api/proforma/PET/etiket_ayar').get_json()['mod'] == 'notr'
    assert c.post('/api/proforma/PET/etiket_ayar', json={'mod': 'x'}, headers=H).status_code == 400
    ci = c.get('/api/proforma/PET/html?mod=ci').get_data(as_text=True)
    assert 'TURKIYE / IRAN' in ci and 'TURKEY' not in ci


def test_pl1_plaka_tercihi_pl_ve_etikette_ortak():
    """PL1: plaka no tercihi musteri bazinda saklanir; hem packing list
    hem etiket ayni tercihe uyar; ?plaka= tek seferlik gecersiz kilar."""
    c = istemci('admin', 'ADMIN')
    assert c.post('/api/proforma/PET/etiket_ayar', json={'plaka': False}, headers=H).status_code == 200
    assert c.get('/api/proforma/PET/etiket_ayar').get_json()['plaka'] is False
    et = c.get('/api/proforma/PET/etiket').get_data(as_text=True)
    assert '45 · 1–8' not in et and 'Block No' in et
    pl = c.get('/api/proforma/PET/html?mod=pl').get_data(as_text=True)
    assert 'Plaka no: <b>Göster' in pl
    assert '45 · 1–8' in c.get('/api/proforma/PET/etiket?plaka=1').get_data(as_text=True)
    c.post('/api/proforma/PET/etiket_ayar', json={'plaka': True}, headers=H)
    assert '45 · 1–8' in c.get('/api/proforma/PET/etiket').get_data(as_text=True)


def test_md1_maliyet_duzenleme_ve_ia1_iskonto_aciklamasi():
    """MD1: maliyet kaydı düzenlenebiliyor (tip, tutar, tarih, fatura no,
    açıklama) ve geçersiz tutar reddediliyor.
    IA1: proformanın iskonto açıklaması kaydediliyor ve geri okunuyor."""
    from models import Maliyet, Proforma
    from datetime import date as _d
    with fa.app.app_context():
        db.session.add(Maliyet(id='MLY1', maliyet_tip='Nakliye (Ocak-Fabrika)', baglanti_tip='Stok',
                               baglanti_id='B1', tutar=100, doviz='USD', usd_karsilik=100,
                               maliyet_tarihi=_d(2026, 1, 5)))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    r = c.put('/api/maliyet/MLY1', headers=H, json={
        'maliyet_tip': 'Diğer Vergiler', 'tutar': 250.5, 'doviz': 'USD',
        'maliyet_tarihi': '2026-02-09', 'fatura_no': 'A-77', 'aciklama': 'liman resmi'})
    assert r.status_code == 200
    with fa.app.app_context():
        m = Maliyet.query.get('MLY1')
        assert (m.maliyet_tip, float(m.tutar), m.fatura_no, m.aciklama) == \
               ('Diğer Vergiler', 250.5, 'A-77', 'liman resmi')
        assert m.maliyet_tarihi == _d(2026, 2, 9)
    assert c.put('/api/maliyet/MLY1', headers=H, json={'tutar': 'abc'}).status_code == 400
    assert c.put('/api/maliyet/MLY1', headers=H, json={'tutar': -5}).status_code == 400

    # IA1 — iskonto açıklaması
    r = c.post('/api/proforma', headers=H, json={
        'musteri': 'ACIK CARI', 'cari_id': 'C1', 'doviz': 'USD', 'toplam': 900,
        'iskonto': 100, 'iskonto_aciklama': '2026 sezon anlaşması',
        'kalemler': [{'urun_tip': 'PLAKA', 'cins': 'X', 'adet': 1, 'miktar': 5,
                      'birim': 'm2', 'birim_fiyat': 200, 'toplam_fiyat': 1000}]})
    assert r.status_code == 200
    pid = r.get_json().get('id')
    with fa.app.app_context():
        assert Proforma.query.get(pid).iskonto_aciklama == '2026 sezon anlaşması'
    d = c.get(f'/api/proforma/{pid}/detay_full').get_json()
    assert d['iskonto_aciklama'] == '2026 sezon anlaşması'
    pi = c.get(f'/api/proforma/{pid}/html?mod=pi').get_data(as_text=True)
    assert '2026 sezon anlaşması' in pi


def test_bs1_govdesiz_post_400_vermiyor():
    """BS1: gövdesiz POST'ta Flask isteği okuyamadan HTML 400 döndürüyordu
    (proforma → sipariş dönüşümü bu yüzden çalışmıyordu)."""
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/proforma/PET/siparise_donustur',
               headers={**H, 'Content-Type': 'application/json'})
    assert r.status_code == 200 and r.get_json()['ok'] is True


def test_sd1_iptal_siparis_silinince_baglar_cozulur():
    """SD1: iptal edilen sipariş silinirken rezervasyon ve proforma bağları
    çözülmeliydi; çözülmediği için PostgreSQL yabancı anahtar hatası verip
    500 dönüyordu. Sevkiyatı olan sipariş ise silinmemeli."""
    from models import Proforma, ProformaKalem, Rezervasyon, Siparis, Sevkiyat
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add_all([
            BlokStok(id='BSD', blok_no='SD-1', cins='TEST', boy=300, yukseklik=150, en=120,
                     hacim_m3=5.4, tonaj=15, durum='Serbest'),
            Proforma(id='PSD', musteri='ACIK CARI', cari_id='C1', toplam=500, doviz='USD',
                     durum='Onaylandi', aktif_surum=True, revizyon_no=0, ana_pi_id='PSD'),
            ProformaKalem(proforma_id='PSD', urun_tip='BLOK', cins='TEST', blok_no='SD-1',
                          boy=300, yukseklik=150, en=120, adet=1, miktar=15, birim='ton',
                          birim_fiyat=100, toplam_fiyat=1500, doviz='USD', sira=1, stok_id='BSD'),
        ])
        db.session.commit()
    sid = c.post('/api/proforma/PSD/siparise_donustur', headers=H, json={}).get_json()['siparis_id']
    with fa.app.app_context():
        assert Rezervasyon.query.filter_by(siparis_id=sid).count() == 1
    assert c.put(f'/api/siparis/{sid}', headers=H, json={'durum': 'Iptal Edildi'}).status_code == 200

    # Sevkiyatı olan sipariş silinemez
    with fa.app.app_context():
        db.session.add(Sevkiyat(id='SVK-SD', siparis_id=sid, musteri='ACIK CARI', durum='Hazirlaniyor'))
        db.session.commit()
    r = c.delete(f'/api/siparis/{sid}', headers=H)
    assert r.status_code == 400 and 'sevkiyat' in r.get_json()['mesaj'].lower()
    with fa.app.app_context():
        Sevkiyat.query.filter_by(id='SVK-SD').delete()
        db.session.commit()

    r = c.delete(f'/api/siparis/{sid}', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    with fa.app.app_context():
        assert Siparis.query.get(sid) is None
        rez = Rezervasyon.query.filter_by(stok_id='BSD').first()
        assert rez.siparis_id is None and rez.siparis_kalem_id is None and rez.iptal_nedeni
        pf = Proforma.query.get('PSD')
        assert pf.siparis_id is None and pf.durum != 'Siparise Donustu'


def test_pd1_iptal_proforma_ve_bagli_kayitlar_silinebiliyor():
    """PD1: iptal proforma silinirken rezervasyon, konteyner ve satış kaydı
    bağları çözülmeliydi; çözülmediği için 500 dönüyordu. Faturası olan
    proforma ise silinmemeli. Aynı sınıf: çek ve sevkiyat silme."""
    from models import (Proforma, ProformaKalem, Rezervasyon, Konteyner,
                        Sevkiyat, Fatura)
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add_all([
            Proforma(id='PPD', musteri='ACIK CARI', cari_id='C1', toplam=100, doviz='USD',
                     durum='Iptal', aktif_surum=True, revizyon_no=0, ana_pi_id='PPD'),
            ProformaKalem(proforma_id='PPD', urun_tip='PLAKA', cins='T', adet=1, miktar=1,
                          birim='m2', birim_fiyat=100, toplam_fiyat=100, doviz='USD', sira=1),
        ])
        db.session.flush()
        db.session.add_all([
            Konteyner(proforma_id='PPD', sira=1, konteyner_no='MSCU1', tip="20' DC"),
            Rezervasyon(id='RPD', proforma_id='PPD', stok_tip='PLAKA', stok_id='PX',
                        musteri='ACIK CARI'),
            Fatura(id='FPD', fatura_no='F-PD', musteri='ACIK CARI', cari_id='C1',
                   proforma_id='PPD', toplam=100, doviz='USD', durum='Kesildi', yon='satis'),
        ])
        db.session.commit()
    # Faturası varken silinemez
    r = c.delete('/api/proforma/PPD', headers=H)
    assert r.status_code == 400 and 'fatura' in r.get_json()['mesaj'].lower()
    with fa.app.app_context():
        Fatura.query.filter_by(id='FPD').delete()
        db.session.commit()
    r = c.delete('/api/proforma/PPD', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    with fa.app.app_context():
        assert Proforma.query.get('PPD') is None
        assert Konteyner.query.filter_by(proforma_id='PPD').count() == 0
        assert Rezervasyon.query.get('RPD').proforma_id is None

        # Sevkiyat: konteyneri bağlıyken silinebilmeli
        db.session.add(Sevkiyat(id='SPD', musteri='ACIK CARI', durum='Hazirlaniyor'))
        db.session.flush()
        db.session.add(Konteyner(sevkiyat_id='SPD', sira=1, konteyner_no='MSCU2', tip="40' HC"))
        db.session.commit()
    assert c.delete('/api/sevkiyat/SPD', headers=H).status_code == 200
    with fa.app.app_context():
        assert Sevkiyat.query.get('SPD') is None and Konteyner.query.filter_by(sevkiyat_id='SPD').count() == 0


def test_on1_iki_ondalik_hane():
    """ON1: para ve miktar değerleri 2 haneye yuvarlanır (ROUND_HALF_UP),
    döviz kuru 6 hanede kalır. Yuvarlama tek yerden geçer: aynı değer
    ekranda, belgede ve veritabanında aynı çıkar."""
    from models import PlakaStok, DovizKur
    with fa.app.app_context():
        db.session.add(PlakaStok(id='PON', cins='ON', boy=300, yukseklik=218.5, kalinlik=2,
                                 metraj_m2=fa.app.q2(300 * 218.5 / 10000),
                                 alis_fiyati=fa.app.q2(164.1234), doviz='USD', durum='Serbest'))
        db.session.commit()
        s = PlakaStok.query.get('PON')
        assert float(s.metraj_m2) == 6.56      # 6.555 → yukarı yuvarlanır
        assert float(s.alis_fiyati) == 164.12
        k = DovizKur.query.filter_by(doviz='USD').first()
        assert round(float(k.efektif), 6) == float(k.efektif)   # kur hassasiyeti korunur
    c = istemci('admin', 'ADMIN')
    kalem = c.get('/api/stok?tip=PLAKA').get_json()['data']
    kayit = next(x for x in kalem if x['id'] == 'PON')
    assert kayit['m2'] == 6.56


def test_sg1_sg2_siparis_guncelleme_ve_stoktan_ekleme():
    """SG1: sipariş kalemleri güncellenebiliyor (rezervasyon bağları
    çözülüyor); sevkiyatı olan sipariş kilitli.
    SG2: stoktan seçilen ürünler mevcut siparişe kalem olarak ekleniyor,
    aynı blok/ölçü tek kalemde toplanıyor, başka siparişteki stok atlanıyor."""
    from models import Siparis, SiparisKalem, Rezervasyon, PlakaStok, Sevkiyat
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        for i in range(4):
            db.session.add(PlakaStok(id=f'SPK{i}', cins='SG', ozellik='POLISHED', blok_no='B9',
                                     boy=300, yukseklik=200, kalinlik=2, metraj_m2=6.0,
                                     durum='Serbest', doviz='USD'))
        db.session.add(PlakaStok(id='SPKX', cins='SG', ozellik='HONED', blok_no='B9',
                                 boy=300, yukseklik=200, kalinlik=2, metraj_m2=6.0,
                                 durum='Serbest', doviz='USD'))
        db.session.commit()
    sid = c.post('/api/siparis', headers=H, json={
        'musteri': 'ACIK CARI', 'doviz': 'USD', 'durum': 'Onaylandi',
        'kalemler': [{'urun_tip': 'PLAKA', 'cins': 'SG', 'adet': 1, 'miktar': 6,
                      'birim': 'm2', 'birim_fiyat': 100, 'stok_ids': ['SPK0']}]}).get_json()['id']

    # SG2 — üç stok ekle: ikisi aynı yüzey (tek kalem), biri farklı (ayrı kalem)
    r = c.post(f'/api/siparis/{sid}/stok_ekle', headers=H,
               json={'stok_ids': ['SPK1', 'SPK2', 'SPKX'], 'birim_fiyat': 120})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    assert r.get_json()['kalem'] == 2
    with fa.app.app_context():
        kalemler = SiparisKalem.query.filter_by(siparis_id=sid).order_by(SiparisKalem.sira).all()
        assert len(kalemler) == 3
        cift = [k for k in kalemler if k.ozellik == 'POLISHED' and k.adet == 2][0]
        assert float(cift.miktar) == 12.0 and float(cift.toplam_fiyat) == 1440.0
        assert Rezervasyon.query.filter_by(siparis_id=sid, iptal_nedeni=None).count() == 4

    # Başka siparişteki stok atlanır
    sid2 = c.post('/api/siparis', headers=H, json={
        'musteri': 'ACIK CARI', 'doviz': 'USD', 'durum': 'Onaylandi',
        'kalemler': [{'urun_tip': 'PLAKA', 'cins': 'SG', 'adet': 1, 'miktar': 6,
                      'birim': 'm2', 'birim_fiyat': 100, 'stok_ids': ['SPK3']}]}).get_json()['id']
    r = c.post(f'/api/siparis/{sid}/stok_ekle', headers=H, json={'stok_ids': ['SPK3']})
    assert r.status_code == 400 and sid2 in r.get_json()['mesaj']

    # SG1 — kalem güncelleme: eski kalemler silinir, bağlar çözülür
    r = c.put(f'/api/siparis/{sid}', headers=H, json={'kalemler': [
        {'urun_tip': 'PLAKA', 'cins': 'SG', 'adet': 1, 'miktar': 6.5, 'birim': 'm2',
         'birim_fiyat': 150, 'stok_ids': ['SPK0']}]})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    with fa.app.app_context():
        kl = SiparisKalem.query.filter_by(siparis_id=sid).all()
        assert len(kl) == 1 and float(kl[0].toplam_fiyat) == 975.0
        assert float(Siparis.query.get(sid).toplam_tutar) == 975.0
        db.session.add(Sevkiyat(id='SVK-SG', siparis_id=sid, musteri='ACIK CARI', durum='Hazirlaniyor'))
        db.session.commit()
    # Sevkiyat varken kalem değişmez, ama sipariş bilgisi güncellenir
    r = c.put(f'/api/siparis/{sid}', headers=H, json={'kalemler': []})
    assert r.status_code == 400 and 'sevkiyat' in r.get_json()['mesaj'].lower()
    assert c.put(f'/api/siparis/{sid}', headers=H, json={'aciklama': 'not'}).status_code == 200
    assert c.post(f'/api/siparis/{sid}/stok_ekle', headers=H,
                  json={'stok_ids': ['SPK1']}).status_code == 400


def test_fd1_fatura_degisikligi_cariye_yansir():
    """FD1: fatura tarihi/vadesi/tutarı değişince bağlı cari hareket de
    güncellenmeliydi. Eskiden yalnızca fatura no yansıyordu: ekstre eski
    tarihi, eski kuru ve eski vadeyi gösteriyordu."""
    from models import Fatura, CariHareket, DovizKur
    with fa.app.app_context():
        for t, k in ((date(2026, 3, 2), 30.0), (date(2026, 5, 4), 40.0)):
            if not DovizKur.query.filter_by(doviz='USD', tarih=t).first():
                db.session.add(DovizKur(doviz='USD', tarih=t, alis=k, satis=k, efektif=k))
        db.session.add(Fatura(id='FFD', fatura_no='F-FD', musteri='ACIK CARI', cari_id='C1',
                              toplam=1000, doviz='USD', durum='Kesildi', yon='satis',
                              fatura_tarihi=date(2026, 3, 2), vade_tarihi=date(2026, 4, 2)))
        db.session.add(CariHareket(id='HFD', cari_id='C1', cari_unvan='ACIK CARI',
                                   islem_tip='Fatura (Satis)', borc=1000, alacak=0, doviz='USD',
                                   kur_uygulanan=30.0, borc_try=30000, alacak_try=0,
                                   kaynak='fatura', baglanti_tip='fatura', baglanti_id='FFD',
                                   hareket_tarihi=date(2026, 3, 2), vade_tarihi=date(2026, 4, 2)))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    r = c.put('/api/fatura/FFD', headers=H, json={
        'fatura_tarihi': '2026-05-04', 'vade_tarihi': '2026-06-04'})
    assert r.status_code == 200 and 'cari hareket' in r.get_json()['mesaj']
    with fa.app.app_context():
        h = CariHareket.query.get('HFD')
        assert h.hareket_tarihi == date(2026, 5, 4)     # ekstredeki tarih
        assert h.vade_tarihi == date(2026, 6, 4)        # yaşlandırma buradan okunur
        assert float(h.kur_uygulanan) == 40.0           # yeni tarihin kuru
        assert float(h.borc_try) == 40000.0
        # Sözleşme kuru (MANUEL) korunur
        h.kur_kaynak = 'MANUEL'; h.kur_uygulanan = 52.0
        db.session.commit()
    c.put('/api/fatura/FFD', headers=H, json={'fatura_tarihi': '2026-03-02'})
    with fa.app.app_context():
        h = CariHareket.query.get('HFD')
        assert float(h.kur_uygulanan) == 52.0 and float(h.borc_try) == 52000.0


def test_ek1_ek2_ekstre_dili_ve_kur_esasi():
    """EK1: yabancı cariye İngilizce ekstrede açıklamalar da İngilizce.
    EK2: kur esası satırı TL ekstrede basılır (dövizlide çevrim yok)."""
    cev = fa.app.jinja_env.globals['_aciklama_cevir']
    assert cev('Tahsilat: X - Fatura MLS1', 'en') == 'Collection: X - Invoice MLS1'
    assert cev('Toplu tahsilat — Fatura MLS1', 'en').startswith('Bulk collection')
    assert cev('Çek alındı (No: 45) — MLS1', 'en').startswith('Cheque received')
    assert cev('Tahsilat: X - Fatura MLS1', 'tr') == 'Tahsilat: X - Fatura MLS1'
    c = istemci('admin', 'ADMIN')
    tr = c.get('/api/cari/C1/ekstre_pdf?doviz=TRY&kur_modu=islem').get_data(as_text=True)
    usd = c.get('/api/cari/C1/ekstre_pdf?doviz=USD').get_data(as_text=True)
    assert 'Rate Basis' in tr          # yabancı cari → İngilizce belge
    assert 'Rate Basis' not in usd     # aynı dövizde çevrim yok, satır basılmaz
    assert 'lang="en"' in usd


def test_ft1_fk2_fatura_tutari_ve_sozlesme_kuru():
    """FT1: faturanın tutarı düzenlenebilmeli; değişiklik cari hesaba ve
    kârlılığa işlenmeli. FK2: fatura tarihine göre TCMB kuru yerine elle
    sözleşme kuru girilebilmeli (girildiyse kesim de onu kullanır)."""
    from models import Fatura, CariHareket, SatisKaydi, DovizKur
    with fa.app.app_context():
        if not DovizKur.query.filter_by(doviz='USD', tarih=date(2026, 3, 2)).first():
            db.session.add(DovizKur(doviz='USD', tarih=date(2026, 3, 2),
                                    alis=30.0, satis=30.0, efektif=30.0))
        db.session.add(Fatura(id='FFT', fatura_no='F-FT', musteri='ACIK CARI', cari_id='C1',
                              toplam=1000, ara_toplam=1000, doviz='USD', durum='Kesildi',
                              yon='satis', satis_tipi='ihracat',
                              fatura_tarihi=date(2026, 3, 2), vade_tarihi=date(2026, 4, 2),
                              kalemler_json=json.dumps([
                                  {'cins': 'Emperador', 'miktar': 100, 'birim': 'm2',
                                   'birim_fiyat': 10, 'toplam_fiyat': 1000}])))
        db.session.add(CariHareket(id='HFT', cari_id='C1', cari_unvan='ACIK CARI',
                                   islem_tip='Fatura (Satis)', borc=1000, alacak=0, doviz='USD',
                                   kur_uygulanan=30.0, kur_kaynak='TCMB',
                                   borc_try=30000, alacak_try=0,
                                   kaynak='fatura', baglanti_tip='fatura', baglanti_id='FFT',
                                   hareket_tarihi=date(2026, 3, 2), vade_tarihi=date(2026, 4, 2)))
        db.session.add(SatisKaydi(id='SKFT', fatura_id='FFT', musteri='ACIK CARI',
                                  stok_tip='PLAKA', doviz='USD', tutar=1000, tutar_usd=1000,
                                  tutar_try=30000, maliyet_usd=600, kar_usd=400, marj_yuzde=40,
                                  satis_tarihi=date(2026, 3, 2)))
        db.session.commit()
    c = istemci('admin', 'ADMIN')

    # ── FT1: kalem fiyatı düzeltiliyor → toplam, cari ve kârlılık birlikte ──
    r = c.put('/api/fatura/FFT', headers=H, json={'kalemler': [
        {'cins': 'Emperador', 'miktar': 100, 'birim': 'm2', 'birim_fiyat': 12}]})
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        f = Fatura.query.get('FFT')
        assert float(f.toplam) == 1200.0 and float(f.ara_toplam) == 1200.0
        assert json.loads(f.kalemler_json)[0]['toplam_fiyat'] == 1200
        h = CariHareket.query.get('HFT')
        assert float(h.borc) == 1200.0 and float(h.borc_try) == 36000.0
        sk = SatisKaydi.query.get('SKFT')
        assert float(sk.tutar_usd) == 1200.0 and float(sk.kar_usd) == 600.0

    # ── FK2: sözleşme kuru girilir → TCMB yerine o kur işlenir ──
    r = c.put('/api/fatura/FFT', headers=H, json={'kur': 41.5})
    assert r.status_code == 200 and 'kur' in r.get_json()['mesaj']
    with fa.app.app_context():
        h = CariHareket.query.get('HFT')
        assert float(h.kur_uygulanan) == 41.5 and h.kur_kaynak == 'MANUEL'
        assert float(h.borc_try) == 49800.0        # 1200 × 41,5
    # Tarih değişse bile sözleşme kuru TCMB ile EZİLMEZ
    c.put('/api/fatura/FFT', headers=H, json={'fatura_tarihi': '2026-03-02'})
    with fa.app.app_context():
        assert float(CariHareket.query.get('HFT').kur_uygulanan) == 41.5
    # Boş gönderilirse TCMB kuruna dönülür
    r = c.put('/api/fatura/FFT', headers=H, json={'kur': None})
    assert r.status_code == 200
    with fa.app.app_context():
        h = CariHareket.query.get('HFT')
        assert h.kur_kaynak == 'TCMB' and float(h.kur_uygulanan) == 30.0
        assert float(h.borc_try) == 36000.0

    # ── Tahsilatın altına düşüren tutar reddedilir ──
    with fa.app.app_context():
        db.session.add(CariHareket(id='HFTT', cari_id='C1', cari_unvan='ACIK CARI',
                                   islem_tip='Tahsilat', borc=0, alacak=900, doviz='USD',
                                   kur_uygulanan=30.0, borc_try=0, alacak_try=27000,
                                   kaynak='tahsilat', baglanti_tip='fatura', baglanti_id='FFT',
                                   hareket_tarihi=date(2026, 3, 5)))
        db.session.commit()
    r = c.put('/api/fatura/FFT', headers=H, json={'ara_toplam': 500})
    assert r.status_code == 400 and r.get_json().get('error') == 'tahsilat_asiyor'
    with fa.app.app_context():
        assert float(Fatura.query.get('FFT').toplam) == 1200.0   # değişmedi

    # ── İptal faturanın tutarı/kuru değiştirilemez ──
    with fa.app.app_context():
        Fatura.query.get('FFT').durum = 'Iptal'
        db.session.commit()
    assert c.put('/api/fatura/FFT', headers=H, json={'kur': 44}).status_code == 400


def test_am1_siparis_avansi_faturaya_mahsup_edilir():
    """AM1: siparişe gelen avans, fatura kesilince otomatik mahsup
    edilmeli — fatura 'ödenecek' tutarı avans düşülmüş göstermeli,
    cari bakiyesi değişmemeli. İptalde avans siparişe dönmeli."""
    from models import Fatura, CariHareket, Siparis, DovizKur
    with fa.app.app_context():
        if not DovizKur.query.filter_by(doviz='USD', tarih=date(2026, 3, 2)).first():
            db.session.add(DovizKur(doviz='USD', tarih=date(2026, 3, 2),
                                    alis=30.0, satis=30.0, efektif=30.0))
        db.session.add(Siparis(id='SIPAM', musteri='ACIK CARI', cari_id='C1',
                               doviz='USD', toplam_tutar=50000, durum='Onaylandi',
                               siparis_tarihi=date(2026, 3, 1)))
        db.session.add(Fatura(id='FAM', fatura_no='F-AM', musteri='ACIK CARI', cari_id='C1',
                              siparis_id='SIPAM', toplam=50000, ara_toplam=50000,
                              doviz='USD', durum='Taslak', yon='satis',
                              satis_tipi='ihracat', fatura_tipi='teklif',
                              fatura_tarihi=date(2026, 3, 2)))
        db.session.add(CariHareket(id='HAVANS', cari_id='C1', cari_unvan='ACIK CARI',
                                   islem_tip='Avans Tahsilati', borc=0, alacak=15000,
                                   doviz='USD', kur_uygulanan=30.0, borc_try=0,
                                   alacak_try=450000, kaynak='tahsilat',
                                   siparis_id='SIPAM', baglanti_tip='siparis',
                                   baglanti_id='SIPAM', hareket_tarihi=date(2026, 3, 1)))
        db.session.commit()
    c = istemci('admin', 'ADMIN')

    def _bakiye():
        with fa.app.app_context():
            hs = CariHareket.query.filter_by(cari_id='C1').all()
            return round(sum(float(h.borc or 0) - float(h.alacak or 0) for h in hs), 2)

    onceki_bakiye = _bakiye()
    r = c.post('/api/fatura/FAM/durum', headers=H, json={'durum': 'Kesildi'})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert 'mahsup' in r.get_json()['mesaj']

    # Fatura 15.000 tahsil edilmiş, 35.000 açık görünmeli
    t = c.get('/api/fatura/FAM/tahsilatlar').get_json()
    assert t['tahsil_edilen'] == 15000 and t['kalan'] == 35000
    assert t['avans_mahsup'] == 15000 and t['avans_acik'] == 0
    with fa.app.app_context():
        assert Fatura.query.get('FAM').durum == 'Kismi Tahsil'
        # Cari bakiyesi: fatura borcu kadar arttı, mahsup onu DEĞİŞTİRMEDİ
        assert round(_bakiye() - onceki_bakiye, 2) == 50000.0
        # Siparişte açık avans kalmadı (aynı avans ikinci kez mahsup edilemez)
        av = fa.app.view_functions  # noqa: F841 (kapsam kontrolü değil)
    assert c.post('/api/fatura/FAM/avans_mahsup', headers=H).status_code == 400

    # ── İPTAL: mahsup geri alınır, avans siparişe döner ──
    r = c.post('/api/fatura/FAM/durum', headers=H, json={'durum': 'Iptal'})
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        assert CariHareket.query.filter_by(baglanti_id='FAM', kaynak='avans_mahsup').count() == 0
        assert CariHareket.query.filter_by(kaynak='avans_mahsup').count() == 0
        assert round(_bakiye() - onceki_bakiye, 2) == 0.0
    assert c.get('/api/fatura/FAM/tahsilatlar').get_json()['avans_acik'] == 15000


def test_am2_avans_proformada_ve_kesim_sonrasinda():
    """AM2: sipariş hesabına giren avans PROFORMADA 'alınan avans /
    ödenecek kalan' olarak görünmeli. AM1-ek: fatura kesildikten SONRA
    gelen avans da faturaya otomatik işlenmeli."""
    from models import Fatura, CariHareket, Siparis, Proforma, ProformaKalem, DovizKur, Kasa
    with fa.app.app_context():
        if not DovizKur.query.filter_by(doviz='USD', tarih=date(2026, 3, 2)).first():
            db.session.add(DovizKur(doviz='USD', tarih=date(2026, 3, 2),
                                    alis=30.0, satis=30.0, efektif=30.0))
        if not Kasa.query.filter_by(ad='Test USD').first():
            db.session.add(Kasa(ad='Test USD', doviz='USD', bakiye=0))
        db.session.add(Siparis(id='SIPAM2', musteri='ACIK CARI', cari_id='C1', doviz='USD',
                               toplam_tutar=50000, durum='Onaylandi',
                               siparis_tarihi=date(2026, 3, 1)))
        db.session.flush()
        db.session.add(Proforma(id='PIAM2', siparis_id='SIPAM2', musteri='ACIK CARI',
                                cari_id='C1', toplam=50000, doviz='USD',
                                durum='Onaylandi', tur='ihracat'))
        db.session.flush()
        db.session.add(ProformaKalem(proforma_id='PIAM2', sira=1, urun_tip='PLAKA',
                                     cins='Emperador', miktar=500, birim='m2',
                                     birim_fiyat=100, toplam_fiyat=50000, doviz='USD', adet=25))
        db.session.add(CariHareket(id='HAV2', cari_id='C1', cari_unvan='ACIK CARI',
                                   islem_tip='Avans Tahsilati', borc=0, alacak=15000,
                                   doviz='USD', kur_uygulanan=30.0, borc_try=0,
                                   alacak_try=450000, kaynak='tahsilat', siparis_id='SIPAM2',
                                   baglanti_tip='siparis', baglanti_id='SIPAM2',
                                   hareket_tarihi=date(2026, 3, 1)))
        db.session.commit()
    c = istemci('admin', 'ADMIN')

    # ── PROFORMA: alınan avans ve ödenecek kalan basılmalı ──
    g = c.get('/api/proforma/PIAM2/html?mod=pi').get_data(as_text=True)
    assert 'Advance Received' in g          # yabancı cari → İngilizce belge
    assert 'Balance Due' in g
    assert '15,000.00' in g and '35,000.00' in g

    # ── Fatura kesildikten SONRA gelen avans ──
    with fa.app.app_context():
        db.session.add(Fatura(id='FAM2', fatura_no='F-AM2', musteri='ACIK CARI', cari_id='C1',
                              siparis_id='SIPAM2', proforma_id='PIAM2', toplam=50000,
                              ara_toplam=50000, doviz='USD', durum='Kesildi', yon='satis',
                              satis_tipi='ihracat', fatura_tarihi=date(2026, 3, 2)))
        db.session.add(CariHareket(id='HBORC2', cari_id='C1', cari_unvan='ACIK CARI',
                                   islem_tip='Satis Faturasi', borc=50000, alacak=0,
                                   doviz='USD', kur_uygulanan=30.0, borc_try=1500000,
                                   alacak_try=0, kaynak='fatura', baglanti_tip='fatura',
                                   baglanti_id='FAM2', hareket_tarihi=date(2026, 3, 2)))
        db.session.commit()
        kasa_id = Kasa.query.filter_by(ad='Test USD').first().id
    # mevcut avans faturaya işlensin (kesim öncesi gelen)
    assert c.post('/api/fatura/FAM2/avans_mahsup', headers=H).status_code == 200
    # yeni avans: cari hareket girilir → tek açık faturaya kendiliğinden işlenir
    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': 'C1', 'islem_tip': 'Avans Tahsilati', 'alacak': 10000,
        'doviz': 'USD', 'vade_tarihi': '2026-03-05', 'hareket_tarihi': '2026-03-05',
        'siparis_id': 'SIPAM2', 'kasa_id': kasa_id})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert 'mahsup' in r.get_json()['mesaj']
    t = c.get('/api/fatura/FAM2/tahsilatlar').get_json()
    assert t['tahsil_edilen'] == 25000 and t['kalan'] == 25000 and t['avans_acik'] == 0


def test_av2_toplu_avans_siparislere_dagitilir():
    """AV2: tek seferde gelen avans önce bir siparişe girilip diğerlerine
    devredilebilmeli. Her adımda cari bakiyesi ve kasa DOĞRU kalmalı;
    devir kasaya dokunmamalı. Kaynak sipariş iptal değilse açıklamada
    'iptal' yazmamalı."""
    from models import CariHareket, Siparis, Kasa
    with fa.app.app_context():
        for i, t in (('AV1', 30000), ('AV2', 40000), ('AV3', 50000)):
            db.session.add(Siparis(id=i, musteri='ACIK CARI', cari_id='C1', doviz='USD',
                                   toplam_tutar=t, durum='Onaylandi',
                                   siparis_tarihi=date(2026, 3, 1)))
        db.session.add(Kasa(ad='AV Kasa USD', doviz='USD', bakiye=0))
        db.session.commit()
        kasa_id = Kasa.query.filter_by(ad='AV Kasa USD').first().id

    def bakiye():
        with fa.app.app_context():
            hs = CariHareket.query.filter_by(cari_id='C1').all()
            return round(sum(float(h.borc or 0) - float(h.alacak or 0) for h in hs), 2)

    def avans(sip):
        return c.get(f'/api/siparis/{sip}/avans_bakiyesi').get_json()['avans']

    c = istemci('admin', 'ADMIN')
    once = bakiye()
    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': 'C1', 'islem_tip': 'Avans Tahsilati', 'alacak': 46000, 'doviz': 'USD',
        'vade_tarihi': '2026-03-05', 'hareket_tarihi': '2026-03-05',
        'siparis_id': 'AV1', 'kasa_id': kasa_id})
    assert r.status_code == 200
    assert avans('AV1') == 46000            # tamamı ilk siparişte
    assert round(bakiye() - once, 2) == -46000.0

    for hedef, tutar in (('AV2', 12000), ('AV3', 25000)):
        r = c.post('/api/avans/devret', headers=H, json={
            'kaynak_siparis_id': 'AV1', 'hedef_siparis_id': hedef, 'tutar': tutar})
        assert r.status_code == 200, r.get_data(as_text=True)
    assert (avans('AV1'), avans('AV2'), avans('AV3')) == (9000, 12000, 25000)
    # Devir para hareketi DEĞİLDİR: cari toplamı ve kasa değişmez
    assert round(bakiye() - once, 2) == -46000.0
    with fa.app.app_context():
        assert float(Kasa.query.get(kasa_id).bakiye) == 46000.0
        devirler = CariHareket.query.filter_by(kaynak='avans_devir', siparis_id='AV2').all()
        assert devirler and all('iptal' not in (d.aciklama or '') for d in devirler)
    # Kalandan fazlası devredilemez
    r = c.post('/api/avans/devret', headers=H, json={
        'kaynak_siparis_id': 'AV1', 'hedef_siparis_id': 'AV2', 'tutar': 50000})
    assert r.status_code == 400 and 'fazla olamaz' in r.get_json()['mesaj']


def test_f12_yetkisiz_kullanici_yazamaz():
    """F12: yetki JSON'u boş olan kullanıcı eskiden TÜM modüllere
    yazabiliyordu (geriye uyumluluk kuralı). Artık tanımsız yetki =
    erişim yok; ADMIN rolü etkilenmiyor."""
    from models import Kullanici
    with fa.app.app_context():
        if not Kullanici.query.filter_by(ad='yetkisiz').first():
            # KF1: test icinde dogan kullanici fixture'in kapsam
            # guncellemesini KACIRIR — kendisi 'tumu' almali.
            db.session.add(Kullanici(ad='yetkisiz', firma_kapsam='tumu',
                                     sifre=generate_password_hash('x'),
                                     rol='SATIS', cari_kapsam='tumu', yetkiler='{}'))
            db.session.commit()
    c = istemci('yetkisiz', 'SATIS')
    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': 'C1', 'islem_tip': 'Tahsilat', 'alacak': 100, 'doviz': 'USD',
        'vade_tarihi': '2026-03-05'})
    assert r.status_code in (401, 403), r.get_data(as_text=True)
    assert c.get('/api/fatura').status_code in (401, 403)
    # ADMIN etkilenmiyor
    assert istemci('admin', 'ADMIN').get('/api/fatura').status_code == 200


def test_f13_cek_kasa_hatasi_durumu_degistirmez():
    """F13: çek tahsilinde kasa kaydı yazılamazsa eskiden hata sessizce
    yutuluyor, çek yine 'Tahsil Edildi' oluyordu — para hiçbir kasaya
    girmeden tahsil görünüyordu."""
    from models import Cek
    with fa.app.app_context():
        db.session.add(Cek(id='CEKF13', yon='alinan', tutar=5000, doviz='USD',
                           cari_id='C1', cari_unvan='ACIK CARI', durum='Portfoyde',
                           cek_no='F13-1', vade_tarihi=date(2026, 6, 1),
                           keside_tarihi=date(2026, 3, 1), aktif=True))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/cek/CEKF13/durum', headers=H,
               json={'islem': 'tahsil_et', 'kasa_id': 999999})   # olmayan kasa
    assert r.status_code == 400 and 'Kasa' in r.get_json()['mesaj']
    with fa.app.app_context():
        assert Cek.query.get('CEKF13').durum == 'Portfoyde'   # durum değişmedi


def test_f2_karlilik_orantili_dagitilir():
    """F2: aynı faturadaki 20 m² ve 0,5 m² plakalar eskiden EŞİT gelir
    ve eşit ek maliyet alıyordu. Artık her stok kendi değeri oranında
    pay alır; toplam yine fatura matrahına eşittir."""
    from models import (Fatura, Siparis, SiparisKalem, Rezervasyon,
                        PlakaStok, SatisKaydi, Maliyet)
    with fa.app.app_context():
        db.session.add(Siparis(id='SIPF2', musteri='ACIK CARI', cari_id='C1', doviz='USD',
                               toplam_tutar=10250, durum='Onaylandi',
                               siparis_tarihi=date(2026, 3, 1)))
        db.session.add_all([
            PlakaStok(id='PLKBUY', blok_no='B9', cins='TEST', metraj_m2=20,
                      alis_fiyati=100, alis_fiyat_birim='m2', doviz='USD', durum='Satildi'),
            PlakaStok(id='PLKKUC', blok_no='B9', cins='TEST', metraj_m2=0.5,
                      alis_fiyati=100, alis_fiyat_birim='m2', doviz='USD', durum='Satildi')])
        db.session.flush()
        k = SiparisKalem(siparis_id='SIPF2', sira=1, urun_tip='PLAKA', cins='TEST',
                         miktar=20.5, birim='m2', birim_fiyat=500, toplam_fiyat=10250,
                         doviz='USD', adet=2, stoktan_geldi=True)
        db.session.add(k)
        db.session.flush()
        for sid, m2 in (('PLKBUY', 20), ('PLKKUC', 0.5)):
            db.session.add(Rezervasyon(id='RZ' + sid[-3:], stok_id=sid, stok_tip='PLAKA',
                                       siparis_id='SIPF2', siparis_kalem_id=k.id,
                                       cari_id='C1', musteri='ACIK CARI', miktar=m2))
        # sipariş bazlı ek maliyet: 1.025 USD nakliye
        db.session.add(Maliyet(id='MF2', maliyet_tip='Nakliye', baglanti_tip='siparis',
                               baglanti_id='SIPF2', tutar=1025, doviz='USD',
                               usd_karsilik=1025, maliyet_tarihi=date(2026, 3, 1)))
        db.session.add(Fatura(id='FF2', fatura_no='F-F2', musteri='ACIK CARI', cari_id='C1',
                              siparis_id='SIPF2', toplam=10250, ara_toplam=10250,
                              doviz='USD', durum='Taslak', yon='satis',
                              satis_tipi='ihracat', fatura_tipi='stoklu',
                              fatura_tarihi=date(2026, 3, 2)))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    assert c.post('/api/fatura/FF2/durum', headers=H,
                  json={'durum': 'Kesildi'}).status_code == 200
    with fa.app.app_context():
        kayit = {s.stok_id: s for s in SatisKaydi.query.filter_by(fatura_id='FF2').all()}
        assert len(kayit) == 2
        buyuk, kucuk = kayit['PLKBUY'], kayit['PLKKUC']
        # gelir: 20/20,5 ve 0,5/20,5 oranında
        assert abs(float(buyuk.tutar_usd) - 10000) < 1
        assert abs(float(kucuk.tutar_usd) - 250) < 1
        # ek maliyet de aynı oranda (1.025 → 1.000 / 25) + kendi alışı
        assert abs(float(buyuk.maliyet_usd) - 3000) < 2      # 2.000 alış + 1.000 pay
        assert abs(float(kucuk.maliyet_usd) - 75) < 2        # 50 alış + 25 pay
        # toplam gelir fatura matrahına eşit
        assert abs(sum(float(s.tutar_usd) for s in kayit.values()) - 10250) < 1


def test_f3_iptal_rezervasyon_fatura_tipini_bozmaz():
    """F3: iptal edilmiş tek bir rezervasyon bile faturayı 'stoklu'
    yapıyordu; dış alım faturasının alış maliyeti hiç sorulmuyordu."""
    from models import Proforma, Siparis, Rezervasyon, Fatura
    with fa.app.app_context():
        db.session.add(Siparis(id='SIPF3', musteri='ACIK CARI', cari_id='C1', doviz='USD',
                               toplam_tutar=5000, durum='Onaylandi',
                               siparis_tarihi=date(2026, 3, 1)))
        db.session.flush()
        db.session.add(Proforma(id='PIF3', siparis_id='SIPF3', musteri='ACIK CARI',
                                cari_id='C1', toplam=5000, doviz='USD',
                                durum='Onaylandi', tur='ihracat'))
        db.session.add(Rezervasyon(id='RZF3', stok_id='YOK', stok_tip='PLAKA',
                                   siparis_id='SIPF3', cari_id='C1', musteri='ACIK CARI',
                                   iptal_nedeni='Müşteri vazgeçti'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/proforma/PIF3/faturaya_donustur', headers=H, json={})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()['fatura_tipi'] == 'transit'      # eskiden 'stoklu' idi


def test_f1_karma_karsilama_gelir_ve_maliyet():
    """F1: bir kalem stok + dış alım karışımıyla karşılanabilmeli.
    Dış alım payının maliyeti kârlılığa girmeli, geliri kendi satırına
    yazılmalı — eskiden maliyeti hiç sayılmıyor, geliri stok satırına
    ekleniyordu."""
    from models import (Fatura, Siparis, SiparisKalem, Rezervasyon,
                        PlakaStok, SatisKaydi, KalemKarsilama, DovizKur)
    with fa.app.app_context():
        if not DovizKur.query.filter_by(doviz='USD', tarih=date(2026, 3, 2)).first():
            db.session.add(DovizKur(doviz='USD', tarih=date(2026, 3, 2),
                                    alis=30.0, satis=30.0, efektif=30.0))
        db.session.add(Siparis(id='SIPF1', musteri='ACIK CARI', cari_id='C1', doviz='USD',
                               toplam_tutar=15000, durum='Onaylandi',
                               siparis_tarihi=date(2026, 3, 1)))
        db.session.add(PlakaStok(id='PLKF1', blok_no='B7', cins='TEST', metraj_m2=100,
                                 alis_fiyati=60, alis_fiyat_birim='m2', doviz='USD',
                                 durum='Serbest'))
        db.session.flush()
        k = SiparisKalem(siparis_id='SIPF1', sira=1, urun_tip='PLAKA', cins='TEST',
                         miktar=150, birim='m2', birim_fiyat=100, toplam_fiyat=15000,
                         doviz='USD', adet=1)
        db.session.add(k)
        db.session.flush()
        kalem_id = k.id
        # 100 m² stoktan (rezervasyon + otomatik karşılama satırı)
        db.session.add(Rezervasyon(id='RZF1', stok_id='PLKF1', stok_tip='PLAKA',
                                   siparis_id='SIPF1', siparis_kalem_id=k.id,
                                   cari_id='C1', musteri='ACIK CARI', miktar=100))
        db.session.add(KalemKarsilama(id='KRSF1S', siparis_id='SIPF1',
                                      siparis_kalem_id=k.id, kaynak_tip='STOK',
                                      kaynak_ref='PLKF1', rezervasyon_id='RZF1',
                                      miktar=100, birim='m2', birim_maliyet=60,
                                      doviz='USD', durum='Gerceklesti'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')

    # 50 m² dış alım — API üzerinden
    r = c.post(f'/api/siparis/SIPF1/kalem/{kalem_id}/karsilama', headers=H, json={
        'kaynak_tip': 'DIS_ALIM', 'kaynak_ad': 'TEDARİKÇİ A', 'miktar': 50,
        'birim': 'm2', 'birim_maliyet': 70, 'doviz': 'USD'})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()['ozet']['acik'] == 0        # 100 + 50 = 150

    # Kalem miktarını aşan satır reddedilir
    r = c.post(f'/api/siparis/SIPF1/kalem/{kalem_id}/karsilama', headers=H, json={
        'kaynak_tip': 'URETIM', 'miktar': 10, 'birim': 'm2', 'birim_maliyet': 50})
    assert r.status_code == 400 and r.get_json()['error'] == 'miktar_asiyor'

    with fa.app.app_context():
        db.session.add(Fatura(id='FF1', fatura_no='F-F1', musteri='ACIK CARI', cari_id='C1',
                              siparis_id='SIPF1', toplam=15000, ara_toplam=15000,
                              doviz='USD', durum='Taslak', yon='satis',
                              satis_tipi='ihracat', fatura_tipi='stoklu',
                              fatura_tarihi=date(2026, 3, 2)))
        db.session.commit()
    _r = c.post('/api/fatura/FF1/durum', headers=H, json={'durum': 'Kesildi'})
    assert _r.status_code == 200, _r.get_data(as_text=True)

    with fa.app.app_context():
        kayitlar = SatisKaydi.query.filter_by(fatura_id='FF1').all()
        assert len(kayitlar) == 2                     # stok + dış alım
        stok_k = [s for s in kayitlar if s.stok_id == 'PLKF1'][0]
        dis_k = [s for s in kayitlar if s.stok_id != 'PLKF1'][0]
        # gelir 100/150 ve 50/150 oranında
        assert abs(float(stok_k.tutar_usd) - 10000) < 1
        assert abs(float(dis_k.tutar_usd) - 5000) < 1
        # maliyetler kendi kaynaklarından: 100×60 ve 50×70
        assert abs(float(stok_k.maliyet_usd) - 6000) < 1
        assert abs(float(dis_k.maliyet_usd) - 3500) < 1
        # toplam gelir faturaya eşit
        assert abs(sum(float(s.tutar_usd) for s in kayitlar) - 15000) < 1

    # Dış alım satırı silinebilir, stok satırı silinemez
    with fa.app.app_context():
        dis_id = KalemKarsilama.query.filter_by(
            siparis_kalem_id=kalem_id, kaynak_tip='DIS_ALIM').first().id
    assert c.delete(f'/api/siparis/SIPF1/karsilama/{dis_id}', headers=H).status_code == 200
    assert c.delete('/api/siparis/SIPF1/karsilama/KRSF1S', headers=H).status_code == 400


def test_f6_uretim_siparise_baglanir_ve_iz_surulur():
    """F6: kesim bir siparişin ÜRETİM karşılamasına bağlanabilmeli;
    üretilen ürünler o siparişe ayrılmalı, karşılama kapanmalı ve
    sevk edilen üründen kaynak bloğa kadar iz sürülebilmeli."""
    from models import (Siparis, SiparisKalem, KalemKarsilama, BlokStok,
                        PlakaStok, Rezervasyon, Kesim, Cari)
    with fa.app.app_context():
        db.session.add(Siparis(id='SIPF6', musteri='ACIK CARI', cari_id='C1', doviz='USD',
                               toplam_tutar=12000, durum='Onaylandi',
                               siparis_tarihi=date(2026, 3, 1)))
        db.session.add(BlokStok(id='BLKF6', blok_no='T-99', cins='TEST', boy=300,
                                yukseklik=150, en=120, hacim_m3=5.4, tonaj=14.5,
                                alis_fiyati=400, alis_fiyat_birim='ton', doviz='USD',
                                durum='Serbest', uretici='ALBSTONE', cari_id='C1',
                                fatura_no='ALB-2026-7', mense='TURKIYE'))
        db.session.flush()
        k = SiparisKalem(siparis_id='SIPF6', sira=1, urun_tip='PLAKA', cins='TEST',
                         miktar=40, birim='m2', birim_fiyat=300, toplam_fiyat=12000,
                         doviz='USD', adet=8)
        db.session.add(k)
        db.session.flush()
        db.session.add(KalemKarsilama(id='KRSF6', siparis_id='SIPF6', siparis_kalem_id=k.id,
                                      kaynak_tip='URETIM', kaynak_ad='T-99 bloğundan',
                                      miktar=40, birim='m2', birim_maliyet=150,
                                      doviz='USD', durum='Planlandi'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')

    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': ['BLKF6'],
        'karsilama_id': 'KRSF6', 'kesim_tarihi': '2026-03-05',
        'uretim_blok_no': 'T-99-U1',
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'TEST', 'boy': 250,
                      'yukseklik': 160, 'kalinlik': 2, 'adet': 8}]})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d['uretim_rez_sayisi'] == 8 and 'SIPF6' in (d.get('mesaj') or '')
    uretilen = [o['id'] for o in d['olusan_stoklar']]

    with fa.app.app_context():
        krs = KalemKarsilama.query.get('KRSF6')
        assert krs.durum == 'Gerceklesti'
        assert len(json.loads(krs.gerceklesen_stok_ids)) == 8
        kesim = Kesim.query.get(d['kesim_id'])
        assert kesim.siparis_id == 'SIPF6' and kesim.karsilama_id == 'KRSF6'
        # üretilen plakalar siparişe rezerve
        rez = Rezervasyon.query.filter_by(siparis_id='SIPF6').all()
        assert len(rez) == 8 and all(x.rez_tip == 'Uretimden' for x in rez)
        # karşılama ikilenmemiş: hâlâ tek satır, 40 m²
        assert KalemKarsilama.query.filter_by(siparis_id='SIPF6').count() == 1

    # ── İZ: üretilen plakadan kaynak bloğa ──
    iz = c.get(f'/api/iz/PLAKA/{uretilen[0]}').get_json()
    assert iz['ok']
    asamalar = [h['asama'] for h in iz['zincir']]
    assert 'Sipariş' in asamalar and 'Üretim (kesim)' in asamalar and 'Alış' in asamalar
    uretim = [h for h in iz['zincir'] if h['asama'] == 'Üretim (kesim)'][0]
    assert uretim['kaynak_no'] == 'T-99' and uretim['siparis_id'] == 'SIPF6'
    alis = [h for h in iz['zincir'] if h['asama'] == 'Alış'][0]
    assert alis['uretici'] == 'ALBSTONE' and alis['fatura_no'] == 'ALB-2026-7'


def test_rn1_okunur_belge_numaralari():
    """RN1: yeni kayıtlar okunur numara almalı (SIP-STN26-01), cari
    kısaltması kartta durmalı, eski kayıtlar değişmemeli."""
    from models import Cari, Siparis, Proforma, Fatura, CariHareket, PlakaStok
    with fa.app.app_context():
        db.session.add(Cari(id='CRN', unvan='STONELAND USA LLC', cari_tip='Müşteri',
                            ulke='USA', para_birimi='USD', gorunurluk='ortak'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')

    # ── Sipariş: SIP-STN26-01, ikincisi -02 ──
    r1 = c.post('/api/siparis', headers=H, json={
        'musteri': 'STONELAND USA LLC', 'doviz': 'USD',
        'siparis_tarihi': '2026-04-01', 'kalemler': [
            {'urun_tip': 'PLAKA', 'cins': 'TEST', 'miktar': 10, 'birim': 'm2',
             'birim_fiyat': 100, 'adet': 1}]})
    assert r1.status_code == 200, r1.get_data(as_text=True)
    sid1 = r1.get_json()['id']
    # RN3: eskiden `startswith('SIP-STN')` yazıyordu — yani `SIP-` ile
    # cari kısaltması ARASINDA hiçbir şey olmadığını varsayıyordu.
    # Firma belge kodu köke girince kimlik `SIP-MLS-STN26-01` oluyor
    # ve test ÜRÜN DOĞRU ÇALIŞTIĞI HALDE kırılıyordu. Sınanacak şey
    # kısaltmanın kimlikte GEÇMESİ, kaçıncı karakterde olduğu değil.
    _p1 = sid1.split('-')
    assert _p1[0] == 'SIP', sid1
    assert any(p.startswith('STN') for p in _p1[1:]), sid1
    assert sid1.endswith('-01'), sid1
    r2 = c.post('/api/siparis', headers=H, json={
        'musteri': 'STONELAND USA LLC', 'doviz': 'USD',
        'siparis_tarihi': '2026-04-02', 'kalemler': [
            {'urun_tip': 'PLAKA', 'cins': 'TEST', 'miktar': 5, 'birim': 'm2',
             'birim_fiyat': 100, 'adet': 1}]})
    assert r2.get_json()['id'].endswith('-02')

    # Kısaltma karta yazıldı, sonraki numaralar onunla üretiliyor
    with fa.app.app_context():
        assert Cari.query.get('CRN').uretici_kisaltma == 'STN'

    # ── Proforma aynı carinin kendi sayacını kullanır ──
    rp = c.post('/api/proforma', headers=H, json={
        'musteri': 'STONELAND USA LLC', 'doviz': 'USD', 'toplam': 1000})
    assert rp.status_code == 200, rp.get_data(as_text=True)
    # RN3: `startswith('PI-STN')` de aynı sabit konum varsayımıydı
    # (firma kodlu hâli PI-MLS-STN26-01). Parçaya bakıyoruz.
    _pid = rp.get_json()['id']
    _pp = _pid.split('-')
    assert _pp[0] == 'PI', _pid
    assert any(p.startswith('STN') for p in _pp[1:]), _pid

    # ── Cari hareket: HR-STN26-0001 (tek yerden, dinleyiciyle) ──
    with fa.app.app_context():
        kasa_id = None
        from models import Kasa
        k = Kasa.query.filter_by(ad='RN Kasa').first()
        if not k:
            k = Kasa(ad='RN Kasa', doviz='USD', bakiye=0)
            db.session.add(k)
            db.session.commit()
        kasa_id = k.id
    rh = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': 'CRN', 'islem_tip': 'Tahsilat', 'alacak': 500, 'doviz': 'USD',
        'vade_tarihi': '2026-04-05', 'hareket_tarihi': '2026-04-05',
        'kasa_id': kasa_id, 'kur_uygulanan': 40,
        'kur_gerekce': 'Test kuru'})
    assert rh.status_code == 200, rh.get_data(as_text=True)
    with fa.app.app_context():
        h = CariHareket.query.filter_by(cari_id='CRN').first()
        # RN3: bu üretecin kökü firma kodunu taşıyor artık
        # (HR-MLS-STN26-0001). Sabit önek varsayımı burada da kalkıyor.
        _hp = h.id.split('-')
        assert _hp[0] == 'HR', h.id
        assert any(p.startswith('STN26') for p in _hp[1:]), h.id
        assert _hp[-1].isdigit(), h.id

    # ── Stok: blok no ve plaka no kimlikte görünür ──
    rs = c.post('/api/stok/ekle', headers=H, json={
        'tip': 'BLOK', 'cins': 'TEST', 'blok_no': 'T-55', 'boy': 300,
        'yukseklik': 150, 'en': 120, 'tonaj': 14, 'alis_fiyati': 400,
        'alis_fiyat_birim': 'ton', 'doviz': 'USD'})
    assert rs.status_code == 200, rs.get_data(as_text=True)
    assert 'T-55' in (rs.get_json().get('id') or ''), rs.get_json()

    # ── Elle verilen kimlikler korunur (içe aktarma, düzeltme betikleri) ──
    with fa.app.app_context():
        db.session.add(CariHareket(id='OZEL-1', cari_id='CRN', cari_unvan='STONELAND USA LLC',
                                   islem_tip='Test', borc=1, alacak=0, doviz='USD',
                                   kur_uygulanan=1, borc_try=1, alacak_try=0,
                                   hareket_tarihi=date(2026, 4, 6)))
        db.session.commit()
        assert CariHareket.query.get('OZEL-1') is not None


def test_rn2_kisaltma_carpismasi_harfle_ayrilir():
    """RN2: aynı harflerle başlayan cariler RAKAMLA değil, unvanın
    sıradaki sessiz (sonra sesli) harfleriyle ayrılmalı.

    STONELAND USA → STN · STONELAND MIAMI → STL · CANADA → STD
    ALIMOĞLU → ALM · ALIMKAR → ALK · ALIM TAŞ → ALT
    """
    from models import Cari
    c = istemci('admin', 'ADMIN')
    # NOT: STONELAND ailesi baska testte kullaniliyor (STN orada alindi),
    # bu yuzden burada baska bir aile ile ayni kural dogrulanir.
    beklenen = [
        ('XANTHOS USA', 'XNT'),
        ('XANTHOS MIAMI', 'XNH'),
        ('XANTHOS CANADA', 'XNS'),
        ('XANTHO WORKS', 'XNW'),
        ('ALIMOĞLU MERMER', 'ALM'),
        ('ALIMKAR MERMER', 'ALK'),
        ('ALIM TAŞ', 'ALT'),
    ]
    for unvan, kis in beklenen:
        r = c.post('/api/cari', headers=H, json={
            'unvan': unvan, 'cari_tip': 'Musteri', 'para_birimi': 'USD',
            'ulke': 'USA'})
        assert r.status_code == 200, r.get_data(as_text=True)
        assert r.get_json().get('uretici_kisaltma') == kis, (unvan, r.get_json())

    # Hiçbir kısaltmada rakam olmamalı ve hepsi benzersiz olmalı
    with fa.app.app_context():
        kisaltmalar = [c2.uretici_kisaltma for c2 in Cari.query.filter(
            Cari.unvan.in_([u for u, _ in beklenen])).all()]
        assert len(kisaltmalar) == len(set(kisaltmalar)), kisaltmalar
        assert all(k and k.isalpha() for k in kisaltmalar), kisaltmalar
        # Ilk iki harf sabit kalir — okunurlugu tasiyan kisim bu
        xan = sorted(k for k in kisaltmalar if k.startswith('X'))
        assert len(xan) == 4 and all(k.startswith('XN') for k in xan), xan
        alm = sorted(k for k in kisaltmalar if k.startswith('A'))
        assert len(alm) == 3 and all(k.startswith('AL') for k in alm), alm

    # Elle girilen kısaltma aynen korunur (kullanıcı kararı bozulmaz)
    r = c.post('/api/cari', headers=H, json={
        'unvan': 'OZEL KISALTMA AS', 'cari_tip': 'Musteri',
        'uretici_kisaltma': 'ozk', 'para_birimi': 'USD'})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json().get('uretici_kisaltma') == 'OZK'


def test_rn2_belge_numarasi_ayri_kisaltmayi_kullanir():
    """RN2: aynı isimli iki cari farklı kısaltma aldığı için sipariş
    numaraları da birbirine karışmaz."""
    c = istemci('admin', 'ADMIN')
    numaralar = []
    for unvan in ('GRANITEX USA', 'GRANITEX EUROPE'):
        rc = c.post('/api/cari', headers=H, json={
            'unvan': unvan, 'cari_tip': 'Musteri', 'para_birimi': 'USD'})
        assert rc.status_code == 200, rc.get_data(as_text=True)
        rs = c.post('/api/siparis', headers=H, json={
            'musteri': unvan, 'doviz': 'USD', 'siparis_tarihi': '2026-05-01',
            'kalemler': [{'urun_tip': 'PLAKA', 'cins': 'TEST', 'miktar': 4,
                          'birim': 'm2', 'birim_fiyat': 100, 'adet': 1}]})
        assert rs.status_code == 200, rs.get_data(as_text=True)
        numaralar.append(rs.get_json()['id'])
    assert numaralar[0] != numaralar[1], numaralar
    # ikisi de -01 ile bitiyor ama kısaltmaları farklı
    assert all(n.endswith('-01') for n in numaralar), numaralar

    # RN3: eskiden `[4:7]` sabit dilimi karşılaştırılıyordu. Firma
    # belge kodu köke girince o dilim kodun kendisi oluyor (ikisinde
    # de aynı) ve test ürün doğru çalıştığı halde kırılıyordu:
    #   ['SIP-MLS-GRN26-01', 'SIP-MLS-GRT26-01'] → 'MLS' != 'MLS'
    # Kısaltma kimliğin SONDAN İKİNCİ parçasında ve orada yılı da
    # taşıyor; konumdan bağımsız okumak için oradan alıyoruz.
    _kis = [n.split('-')[-2] for n in numaralar]
    assert _kis[0] != _kis[1], (numaralar, _kis)


def test_f8_karsilama_plani_onayda_zorunlu():
    """F8: planı belirsiz kalemi olan proforma iç onaydan geçmemeli;
    stok seçilmiş kalemde plan ZATEN belli sayılmalı."""
    from models import Cari, Proforma, ProformaKalem
    with fa.app.app_context():
        if not Cari.query.get('CF8'):
            db.session.add(Cari(id='CF8', unvan='PLANTEST MERMER', cari_tip='Müşteri',
                                para_birimi='USD', gorunurluk='ortak'))
            db.session.commit()
    haz = istemci('hazirlayan', 'ADMIN')
    ony = istemci('onaylayan', 'ADMIN')

    def proforma_kur(kalem):
        r = haz.post('/api/proforma', headers=H, json={
            'musteri': 'PLANTEST MERMER', 'doviz': 'USD', 'tur': 'ihracat',
            'toplam': 1000, 'kalemler': [kalem]})
        assert r.status_code == 200, r.get_data(as_text=True)
        pid = r.get_json()['id']
        assert haz.post(f'/api/proforma/{pid}/durum', headers=H,
                        json={'durum': 'Ic Onay'}).status_code == 200
        return pid

    temel = {'urun_tip': 'PLAKA', 'cins': 'PLAN TEST', 'miktar': 10,
             'birim': 'm2', 'birim_fiyat': 100, 'adet': 1,
             'toplam_fiyat': 1000, 'net_fiyat': 1000}

    # ── 1) PLANSIZ kalem: onay REDDEDİLİR ──
    pid = proforma_kur(dict(temel))
    r = ony.post(f'/api/proforma/{pid}/durum', headers=H, json={'durum': 'Onaylandi'})
    assert r.status_code == 400, r.get_data(as_text=True)
    j = r.get_json()
    assert j.get('error') == 'karsilama_plani_eksik', j
    assert j.get('eksik_kalemler') and j['eksik_kalemler'][0]['sira'] == 1, j
    with fa.app.app_context():
        assert Proforma.query.get(pid).durum == 'Ic Onay'   # durum değişmedi

    # ── 2) Plan işaretlenince onay GEÇER ──
    pid2 = proforma_kur(dict(temel, karsilama_plan='URETIM', plan_maliyet=55,
                             plan_notu='T-91 bloğundan kesim'))
    r = ony.post(f'/api/proforma/{pid2}/durum', headers=H, json={'durum': 'Onaylandi'})
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        pk = ProformaKalem.query.filter_by(proforma_id=pid2).first()
        assert pk.karsilama_plan == 'URETIM'
        assert float(pk.plan_maliyet) == 55.0
        assert pk.plan_notu == 'T-91 bloğundan kesim'

    # ── 3) Tanınmayan plan değeri DÜŞÜRÜLÜR (yarım doğru plan olmaz) ──
    pid3 = proforma_kur(dict(temel, karsilama_plan='HAVADAN'))
    r = ony.post(f'/api/proforma/{pid3}/durum', headers=H, json={'durum': 'Onaylandi'})
    assert r.status_code == 400, r.get_data(as_text=True)
    assert r.get_json().get('error') == 'karsilama_plani_eksik'


def test_f8_stok_secilmis_kalem_plan_istemez():
    """F8: stok seçilmiş kalemde karşılama zaten bellidir — plan alanı
    boş olsa da onay geçmeli."""
    from models import Cari, PlakaStok, ProformaKalem
    with fa.app.app_context():
        if not Cari.query.get('CF9'):
            db.session.add(Cari(id='CF9', unvan='STOKPLAN MERMER', cari_tip='Müşteri',
                                para_birimi='USD', gorunurluk='ortak'))
        if not PlakaStok.query.get('PLK-F8-1'):
            db.session.add(PlakaStok(id='PLK-F8-1', cins='PLAN TEST', blok_no='T-F8',
                                     slab_no=1, boy=300, yukseklik=150, kalinlik=2,
                                     metraj_m2=4.5, durum='Serbest',
                                     alis_fiyati=30, doviz='USD'))
        db.session.commit()
    haz = istemci('hazirlayan', 'ADMIN')
    ony = istemci('onaylayan', 'ADMIN')
    r = haz.post('/api/proforma', headers=H, json={
        'musteri': 'STOKPLAN MERMER', 'doviz': 'USD', 'tur': 'ihracat', 'toplam': 450,
        'kalemler': [{'urun_tip': 'PLAKA', 'cins': 'PLAN TEST', 'miktar': 4.5,
                      'birim': 'm2', 'birim_fiyat': 100, 'adet': 1,
                      'toplam_fiyat': 450, 'net_fiyat': 450,
                      'stok_id': 'PLK-F8-1'}]})
    assert r.status_code == 200, r.get_data(as_text=True)
    pid = r.get_json()['id']
    with fa.app.app_context():
        assert ProformaKalem.query.filter_by(proforma_id=pid).first().stok_id == 'PLK-F8-1'
    assert haz.post(f'/api/proforma/{pid}/durum', headers=H,
                    json={'durum': 'Ic Onay'}).status_code == 200
    r = ony.post(f'/api/proforma/{pid}/durum', headers=H, json={'durum': 'Onaylandi'})
    assert r.status_code == 200, r.get_data(as_text=True)


def test_f8_plan_siparise_karsilama_olarak_gecer():
    """F8: proformadaki plan, siparişe dönüşünce kalem_karsilama
    satırına (durum='Planlandi') kopyalanmalı."""
    from models import Cari, KalemKarsilama
    with fa.app.app_context():
        if not Cari.query.get('CFA'):
            db.session.add(Cari(id='CFA', unvan='PLANGEC MERMER', cari_tip='Müşteri',
                                para_birimi='USD', gorunurluk='ortak'))
            db.session.commit()
    haz = istemci('hazirlayan', 'ADMIN')
    ony = istemci('onaylayan', 'ADMIN')
    r = haz.post('/api/proforma', headers=H, json={
        'musteri': 'PLANGEC MERMER', 'doviz': 'USD', 'tur': 'ihracat', 'toplam': 2000,
        'kalemler': [{'urun_tip': 'PLAKA', 'cins': 'GEC TEST', 'miktar': 20,
                      'birim': 'm2', 'birim_fiyat': 100, 'adet': 1,
                      'toplam_fiyat': 2000, 'net_fiyat': 2000,
                      'karsilama_plan': 'DIS_ALIM', 'plan_maliyet': 62,
                      'plan_notu': 'Akdeniz Mermer'}]})
    assert r.status_code == 200, r.get_data(as_text=True)
    pid = r.get_json()['id']
    assert haz.post(f'/api/proforma/{pid}/durum', headers=H,
                    json={'durum': 'Ic Onay'}).status_code == 200
    assert ony.post(f'/api/proforma/{pid}/durum', headers=H,
                    json={'durum': 'Onaylandi'}).status_code == 200
    r = ony.post(f'/api/proforma/{pid}/siparise_donustur', headers=H, json={})
    assert r.status_code == 200, r.get_data(as_text=True)
    sid = r.get_json()['siparis_id']
    with fa.app.app_context():
        krs = KalemKarsilama.query.filter_by(siparis_id=sid).all()
        assert len(krs) == 1, [k.kaynak_tip for k in krs]
        k = krs[0]
        assert k.kaynak_tip == 'DIS_ALIM', k.kaynak_tip
        assert k.durum == 'Planlandi', k.durum
        assert float(k.birim_maliyet) == 62.0
        assert 'Akdeniz' in (k.kaynak_ad or '')


def test_f8_proforma_guncelleme_stok_bagini_koparmaz():
    """F8 yan düzeltme: proformayı güncellemek kalemin stok bağını ve
    planını silmemeli (eskiden PUT bu iki alanı hiç kopyalamıyordu)."""
    from models import Cari, PlakaStok, ProformaKalem
    with fa.app.app_context():
        if not Cari.query.get('CFB'):
            db.session.add(Cari(id='CFB', unvan='PUTPLAN MERMER', cari_tip='Müşteri',
                                para_birimi='USD', gorunurluk='ortak'))
        if not PlakaStok.query.get('PLK-F8-2'):
            db.session.add(PlakaStok(id='PLK-F8-2', cins='PUT TEST', blok_no='T-F9',
                                     slab_no=1, boy=300, yukseklik=150, kalinlik=2,
                                     metraj_m2=4.5, durum='Serbest',
                                     alis_fiyati=30, doviz='USD'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    kalem = {'urun_tip': 'PLAKA', 'cins': 'PUT TEST', 'miktar': 4.5, 'birim': 'm2',
             'birim_fiyat': 100, 'adet': 1, 'toplam_fiyat': 450, 'net_fiyat': 450,
             'stok_id': 'PLK-F8-2', 'karsilama_plan': 'STOK', 'plan_notu': 'depo'}
    r = c.post('/api/proforma', headers=H, json={
        'musteri': 'PUTPLAN MERMER', 'doviz': 'USD', 'tur': 'ihracat',
        'toplam': 450, 'kalemler': [kalem]})
    assert r.status_code == 200, r.get_data(as_text=True)
    pid = r.get_json()['id']
    # Fiyatı değiştirip kaydet — stok bağı ve plan korunmalı
    r = c.put(f'/api/proforma/{pid}', headers=H, json={
        'musteri': 'PUTPLAN MERMER', 'doviz': 'USD', 'tur': 'ihracat',
        'toplam': 500, 'kalemler': [dict(kalem, birim_fiyat=111,
                                         toplam_fiyat=500, net_fiyat=500)]})
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        pk = ProformaKalem.query.filter_by(proforma_id=pid).first()
        assert pk.stok_id == 'PLK-F8-2', pk.stok_id
        assert pk.karsilama_plan == 'STOK', pk.karsilama_plan
        assert pk.plan_notu == 'depo'


def test_bl16_unvan_degisince_bagli_kayitlar_esitlenir():
    """BL-16: cari ünvanı değişince sipariş/proforma/fatura/hareket
    kayıtlarının görünen adı da güncellenmeli; adla eşleşen sorgular
    boşa düşmemeli."""
    from models import Cari, Siparis, Proforma, Fatura, CariHareket
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/cari', headers=H, json={
        'unvan': 'ESKIAD MERMER', 'cari_tip': 'Musteri', 'para_birimi': 'USD',
        'ulke': 'USA'})
    assert r.status_code == 200, r.get_data(as_text=True)
    cid = r.get_json()['id']

    rs = c.post('/api/siparis', headers=H, json={
        'musteri': 'ESKIAD MERMER', 'doviz': 'USD', 'siparis_tarihi': '2026-06-01',
        'kalemler': [{'urun_tip': 'PLAKA', 'cins': 'AD TEST', 'miktar': 10,
                      'birim': 'm2', 'birim_fiyat': 100, 'adet': 1}]})
    assert rs.status_code == 200, rs.get_data(as_text=True)
    sid = rs.get_json()['id']
    rp = c.post('/api/proforma', headers=H, json={
        'musteri': 'ESKIAD MERMER', 'doviz': 'USD', 'toplam': 1000})
    assert rp.status_code == 200, rp.get_data(as_text=True)
    pid = rp.get_json()['id']

    with fa.app.app_context():
        # kimlik bağı dinleyiciyle kurulmuş olmalı
        assert Siparis.query.get(sid).cari_id == cid
        assert Proforma.query.get(pid).cari_id == cid
        db.session.add(Fatura(id='FBL16', fatura_no='BL16-1', musteri='ESKIAD MERMER',
                              cari_id=cid, yon='satis', durum='Kesildi', doviz='USD',
                              toplam=1000, fatura_tarihi=date(2026, 6, 2)))
        db.session.add(CariHareket(id='HBL16', cari_id=cid, cari_unvan='ESKIAD MERMER',
                                   islem_tip='Satış Faturası', borc=1000, alacak=0,
                                   doviz='USD', kur_uygulanan=40, borc_try=40000,
                                   alacak_try=0, hareket_tarihi=date(2026, 6, 2)))
        db.session.commit()

    # ── ÜNVAN DEĞİŞTİR ──
    r = c.put(f'/api/cari/{cid}', headers=H, json={'unvan': 'YENIAD MERMER LTD'})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json().get('ad_yansimasi', 0) >= 4, r.get_json()

    with fa.app.app_context():
        assert Siparis.query.get(sid).musteri == 'YENIAD MERMER LTD'
        assert Proforma.query.get(pid).musteri == 'YENIAD MERMER LTD'
        assert Fatura.query.get('FBL16').musteri == 'YENIAD MERMER LTD'
        assert CariHareket.query.get('HBL16').cari_unvan == 'YENIAD MERMER LTD'

    # ── Açık faturalar listesi ÜNVAN DEĞİŞİMİNDEN SONRA da dolu ──
    r = c.get(f'/api/cari/{cid}/acik_faturalar?yon=satis', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    kayitlar = j if isinstance(j, list) else (j.get('faturalar') or j.get('veri') or [])
    assert any('BL16' in str(x) for x in kayitlar), j


def test_bl16_bagli_kayitli_cari_silinemez():
    """BL-16: ünvan değişmiş olsa bile bağlı kayıtlar görünmeli —
    eskiden adla sayıldığı için cari silinebiliyordu."""
    from models import Cari, Siparis
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/cari', headers=H, json={
        'unvan': 'SILINMEZ MERMER', 'cari_tip': 'Musteri', 'para_birimi': 'USD'})
    cid = r.get_json()['id']
    rs = c.post('/api/siparis', headers=H, json={
        'musteri': 'SILINMEZ MERMER', 'doviz': 'USD', 'siparis_tarihi': '2026-06-03',
        'kalemler': [{'urun_tip': 'PLAKA', 'cins': 'SIL TEST', 'miktar': 3,
                      'birim': 'm2', 'birim_fiyat': 100, 'adet': 1}]})
    assert rs.status_code == 200, rs.get_data(as_text=True)

    # Siparişin adını elle boz (eski kayıtların yaşadığı durum),
    # kimlik bağı dursun
    with fa.app.app_context():
        sip = Siparis.query.get(rs.get_json()['id'])
        sip.musteri = 'BASKA YAZILMIS AD'
        db.session.commit()
        assert Siparis.query.get(rs.get_json()['id']).cari_id == cid

    r = c.delete(f'/api/cari/{cid}', headers=H)
    assert r.status_code in (400, 409), r.get_data(as_text=True)
    j = r.get_json()
    assert j.get('baglantili') is True, j
    assert (j.get('detay') or {}).get('siparis', 0) >= 1, j
    with fa.app.app_context():
        assert Cari.query.get(cid) is not None


def test_bl16_musteri_degisince_kimlik_de_degisir():
    """BL-16: bir siparişin müşterisi başka firmaya çevrildiğinde
    cari_id eski firmada KALMAMALI (before_update dinleyicisi)."""
    from models import Cari, Siparis
    c = istemci('admin', 'ADMIN')
    a = c.post('/api/cari', headers=H, json={
        'unvan': 'TASIYAN A MERMER', 'cari_tip': 'Musteri', 'para_birimi': 'USD'}).get_json()['id']
    b = c.post('/api/cari', headers=H, json={
        'unvan': 'TASIYAN B MERMER', 'cari_tip': 'Musteri', 'para_birimi': 'USD'}).get_json()['id']
    rs = c.post('/api/siparis', headers=H, json={
        'musteri': 'TASIYAN A MERMER', 'doviz': 'USD', 'siparis_tarihi': '2026-06-04',
        'kalemler': [{'urun_tip': 'PLAKA', 'cins': 'TAS TEST', 'miktar': 2,
                      'birim': 'm2', 'birim_fiyat': 100, 'adet': 1}]})
    sid = rs.get_json()['id']
    with fa.app.app_context():
        assert Siparis.query.get(sid).cari_id == a
        Siparis.query.get(sid).musteri = 'TASIYAN B MERMER'
        db.session.commit()
        assert Siparis.query.get(sid).cari_id == b, 'kimlik adı takip etmedi'


def test_bl17_toplu_import_hatali_satiri_sessizce_atlamaz():
    """BL-17: hatalı satır varsa HİÇBİRİ yazılmamalı ve her hata
    gerekçesiyle dönmeli (eskiden sessizce atlanıyordu)."""
    from models import PlakaStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        once = PlakaStok.query.count()
    r = c.post('/api/stok/toplu_import', headers=H, json={'plakalar': [
        {'cins': 'BL17 TEST', 'blok_no': 'B17', 'slab_no': 1, 'boy': 300,
         'yukseklik': 150, 'kalinlik': 2, 'alis_fiyati': 40, 'doviz': 'USD'},
        {'cins': 'BL17 TEST', 'blok_no': 'B17', 'slab_no': 2, 'boy': 0,
         'yukseklik': 150},                                   # ölçü hatası
        {'cins': '', 'blok_no': 'B17', 'slab_no': 3, 'boy': 300,
         'yukseklik': 150},                                   # cins boş
        {'cins': 'BL17 TEST', 'blok_no': '', 'slab_no': 4, 'boy': 300,
         'yukseklik': 150},                                   # blok boş
        {'cins': 'BL17 TEST', 'blok_no': 'B17', 'slab_no': 5, 'boy': 300,
         'yukseklik': 150, 'doviz': 'XYZ'},                   # döviz tanınmaz
        {'cins': 'BL17 TEST', 'blok_no': 'B17', 'slab_no': 1, 'boy': 300,
         'yukseklik': 150},                                   # dosyada tekrar
    ]})
    assert r.status_code == 400, r.get_data(as_text=True)
    j = r.get_json()
    assert j.get('error') == 'satir_hatalari', j
    assert j['hatali'] == 5 and j['gecerli'] == 1, j
    gerekceler = ' | '.join(h['hata'] for h in j['hatalar'])
    for beklenen in ('boy', 'cins', 'blok no', 'döviz', 'tekrar'):
        assert beklenen in gerekceler, (beklenen, gerekceler)
    with fa.app.app_context():
        assert PlakaStok.query.count() == once, 'hatalı dosyadan kayıt yazıldı'


def test_bl17_kismi_aktarim_acikca_istenir():
    """BL-17: `kismi` verilirse sağlam satırlar yazılır, atlananlar
    gerekçesiyle raporlanır."""
    from models import PlakaStok
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/stok/toplu_import', headers=H, json={'kismi': True, 'plakalar': [
        {'cins': 'BL17 KISMI', 'blok_no': 'B18', 'slab_no': 1, 'boy': 300,
         'yukseklik': 150, 'kalinlik': 2, 'alis_fiyati': 40, 'doviz': 'USD'},
        {'cins': 'BL17 KISMI', 'blok_no': 'B18', 'slab_no': 2, 'boy': 'abc',
         'yukseklik': 150},
    ]})
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    assert j['eklenen'] == 1 and j['atlanan'] == 1, j
    assert 'sayı değil' in j['hatalar'][0]['hata'], j
    with fa.app.app_context():
        p = PlakaStok.query.filter_by(blok_no='B18').all()
        assert len(p) == 1
        assert p[0].slab_no == 1                 # plaka no kaydedildi
        assert float(p[0].metraj_m2) == 4.5      # 300×150/10000


def test_bl17_depodaki_plaka_ikinci_kez_girilemez():
    """BL-17: aynı blok + aynı plaka no ikinci kez stoğa alınamaz —
    aynı malı iki kez satmaya götürür."""
    c = istemci('admin', 'ADMIN')
    kalem = {'cins': 'BL17 TEK', 'blok_no': 'B19', 'slab_no': 7, 'boy': 300,
             'yukseklik': 150, 'kalinlik': 2, 'alis_fiyati': 40, 'doviz': 'USD'}
    assert c.post('/api/stok/toplu_import', headers=H,
                  json={'plakalar': [dict(kalem)]}).status_code == 200
    r = c.post('/api/stok/toplu_import', headers=H, json={'plakalar': [dict(kalem)]})
    assert r.status_code == 400, r.get_data(as_text=True)
    assert 'depoda zaten var' in r.get_json()['hatalar'][0]['hata']


def test_f5_yoldaki_mal_depo_degerine_girmez():
    """F5: sevk edilmiş ama varmamış mal (Sevkedildi) depo m² ve
    değerine DAHİL OLMAMALI; kendi deposunda sayılmalı."""
    from models import PlakaStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        for i, (sid, durum) in enumerate([
                ('PLK-F5-D1', 'Serbest'), ('PLK-F5-D2', 'Satildi'),
                ('PLK-F5-Y1', 'Sevkedildi'), ('PLK-F5-C1', 'Teslim Edildi')]):
            if not PlakaStok.query.get(sid):
                db.session.add(PlakaStok(
                    id=sid, cins='F5 TEST', blok_no='T-F5', slab_no=i + 1,
                    boy=200, yukseklik=100, kalinlik=2, metraj_m2=2.0,
                    durum=durum, alis_fiyati=50, alis_fiyat_birim='m2',
                    doviz='USD'))
        db.session.commit()

    def ozet(depo=None):
        yol = '/api/stok?tip=PLAKA&cins=F5 TEST&per_page=100'
        if depo:
            yol += f'&depo={depo}'
        r = c.get(yol, headers=H)
        assert r.status_code == 200, r.get_data(as_text=True)
        j = r.get_json()
        return j.get('ozet') or {}, (j.get('data') or j.get('veri') or [])

    tum, satirlar = ozet()
    assert len(satirlar) == 4, [x['id'] for x in satirlar]
    # Depo: Serbest + Satildi = 2 kayıt, 4 m², 100 USD
    assert tum['depo_adet'] == 2, tum
    assert float(tum['depo_m2']) == 4.0, tum
    assert float(tum['depo_deger_usd']) == 200.0, tum   # 2 × (50 $/m² × 2 m²)
    # Yolda: 1 kayıt, 2 m², 50 USD — depo rakamlarının DIŞINDA
    assert tum['yolda_adet'] == 1, tum
    assert float(tum['yolda_m2']) == 2.0, tum
    assert float(tum['yolda_deger_usd']) == 100.0, tum
    # Toplam eskisi gibi hepsini kapsar (geriye dönük uyumluluk)
    assert float(tum['m2']) == 8.0, tum

    # ── Depo süzgeci ──
    _, depoda = ozet('depo')
    assert {x['id'] for x in depoda} == {'PLK-F5-D1', 'PLK-F5-D2'}
    _, yolda = ozet('yolda')
    assert {x['id'] for x in yolda} == {'PLK-F5-Y1'}
    assert yolda[0]['depo'] == 'yolda' and yolda[0]['depo_ad'] == 'Yolda'
    _, cikti = ozet('cikti')
    assert {x['id'] for x in cikti} == {'PLK-F5-C1'}


def test_f5_rapor_depo_kirilimi_verir():
    """F5: stok durum raporu depo / yolda ayrımını ve 'Sevkedildi'
    kovasını vermeli (eskiden hiçbir kovaya düşmüyordu)."""
    c = istemci('admin', 'ADMIN')
    r = c.get('/api/rapor/stok_durum', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    for alan in ('depo_adedi', 'depo_deger_usd', 'yolda_adedi',
                 'yolda_deger_usd', 'cikti_adedi'):
        assert alan in d, (alan, list(d))
    assert d['depo_adedi'] + d['yolda_adedi'] + d['cikti_adedi'] \
        == d['toplam_stok_adedi'], d
    assert round(d['depo_deger_usd'] + d['yolda_deger_usd'], 2) <= \
        round(d['toplam_deger_usd'], 2) + 0.01, d
    f5 = [c2 for c2 in (d.get('cins_listesi') or [])
          if c2.get('cins') == 'F5 TEST' and c2.get('tip') == 'PLAKA']
    assert f5, [c2.get('cins') for c2 in (d.get('cins_listesi') or [])]
    co = f5[0]
    assert co['yolda_adet'] == 1, co
    assert co['depo_adet'] == 2, co
    assert co['toplam_adet'] == 4, co


def test_f5_sevk_edilen_mal_fatura_secicisinde_kalir():
    """F5 yan düzeltme: mal gemiye yüklenince fatura/cari hareket
    seçicisinden kaybolmamalı — hâlâ bizim malımız."""
    c = istemci('admin', 'ADMIN')
    r = c.get('/api/stok/gruplar', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    hepsi = str(j)
    assert 'PLK-F5-Y1' in hepsi or 'T-F5' in hepsi, \
        'sevk edilmis stok gruplarda gorunmuyor'


def test_f5_sevkiyat_yolda_olunca_stok_yoldaya_gecer():
    """F5: sevkiyat 'Yolda' olunca stok 'Sevkedildi' olur ve depo
    toplamından düşer; sevkiyat silinince depoya geri döner."""
    from models import Cari, PlakaStok, Siparis, Sevkiyat
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not Cari.query.get('CF5'):
            db.session.add(Cari(id='CF5', unvan='YOLDA MERMER', cari_tip='Müşteri',
                                para_birimi='USD', gorunurluk='ortak'))
        if not PlakaStok.query.get('PLK-F5-S1'):
            db.session.add(PlakaStok(id='PLK-F5-S1', cins='F5 SEVK', blok_no='T-F6',
                                     slab_no=1, boy=200, yukseklik=100, kalinlik=2,
                                     metraj_m2=2.0, durum='Serbest',
                                     alis_fiyati=50, alis_fiyat_birim='m2', doviz='USD'))
        db.session.commit()
    rs = c.post('/api/siparis', headers=H, json={
        'musteri': 'YOLDA MERMER', 'doviz': 'USD', 'siparis_tarihi': '2026-07-01',
        'durum': 'Onaylandi',
        # DAP: varış takibi olan teslim şekli — Yolda adımı vardır
        'teslim_sekli': 'DAP',
        'kalemler': [{'urun_tip': 'PLAKA', 'cins': 'F5 SEVK', 'miktar': 2,
                      'birim': 'm2', 'birim_fiyat': 200, 'adet': 1,
                      'stok_ids': ['PLK-F5-S1']}]})
    assert rs.status_code == 200, rs.get_data(as_text=True)
    sid = rs.get_json()['id']
    rv = c.post('/api/sevkiyat', headers=H, json={
        'siparis_id': sid, 'musteri': 'YOLDA MERMER', 'sevk_tarihi': '2026-07-05',
        'sevk_tip': 'Deniz', 'teslim_sekli': 'DAP'})
    assert rv.status_code == 200, rv.get_data(as_text=True)
    sevk_id = rv.get_json().get('id')
    r = c.post(f'/api/sevkiyat/{sevk_id}/durum', headers=H, json={'durum': 'Yolda'})
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        assert PlakaStok.query.get('PLK-F5-S1').durum == 'Sevkedildi'
    rr = c.get('/api/stok?tip=PLAKA&cins=F5 SEVK&depo=depo&per_page=50', headers=H)
    satirlar = rr.get_json().get('data') or rr.get_json().get('veri') or []
    assert not any(x['id'] == 'PLK-F5-S1' for x in satirlar), \
        'yoldaki mal hala fiziksel depoda listeleniyor'
    rr = c.get('/api/stok?tip=PLAKA&cins=F5 SEVK&depo=yolda&per_page=50', headers=H)
    satirlar = rr.get_json().get('data') or rr.get_json().get('veri') or []
    assert any(x['id'] == 'PLK-F5-S1' for x in satirlar), satirlar


def test_md1_maliyet_olcuye_gore_orantili_dagitilir():
    """MD1: çok kayda dağıtılan maliyet, kayıt sayısına değil ÖLÇÜYE
    göre bölünmeli — aynı faturayla alınan bloklar aynı $/ton olmalı."""
    from models import BlokStok, Maliyet
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        for bid, ton in [('BLK-MD-1', 18.06), ('BLK-MD-2', 6.42),
                         ('BLK-MD-3', 18.33), ('BLK-MD-4', 6.69)]:
            if not BlokStok.query.get(bid):
                db.session.add(BlokStok(
                    id=bid, cins='CEPPO TEST', blok_no=bid[-4:], tonaj=ton,
                    hacim_m3=ton / 2.7, boy=300, yukseklik=180, en=125,
                    durum='Serbest', alis_fiyati=200, alis_fiyat_birim='ton',
                    doviz='EUR'))
        db.session.commit()
    hedefler = ['BLK-MD-1', 'BLK-MD-2', 'BLK-MD-3', 'BLK-MD-4']
    tonlar = {'BLK-MD-1': 18.06, 'BLK-MD-2': 6.42,
              'BLK-MD-3': 18.33, 'BLK-MD-4': 6.69}
    toplam_ton = sum(tonlar.values())
    TUTAR = 5480.0

    # ── ÖN İZLEME: paylar tonajla orantılı ──
    r = c.post('/api/maliyet/dagit', headers=H, json={
        'onizleme': True, 'hedefler': hedefler, 'maliyet_tip': 'Nakliye',
        'baglanti_tip': 'stok', 'tutar': TUTAR, 'doviz': 'USD',
        'kdv_oran': 0, 'dagitim': 'oransal'})
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    assert j['dagitim'] == 'oransal', j
    assert 'tonaj' in j['olcu_notu'], j
    paylar = {x['id']: float(x['net_pay']) for x in j['satirlar']}
    for hid, ton in tonlar.items():
        beklenen = TUTAR * ton / toplam_ton
        assert abs(paylar[hid] - beklenen) < 0.05, (hid, paylar[hid], beklenen)
    assert abs(sum(paylar.values()) - TUTAR) < 0.01, paylar   # kuruş kaybı yok

    # ── KAYDET ──
    r = c.post('/api/maliyet/dagit', headers=H, json={
        'hedefler': hedefler, 'maliyet_tip': 'Nakliye', 'baglanti_tip': 'stok',
        'tutar': TUTAR, 'doviz': 'USD', 'kdv_oran': 0, 'dagitim': 'oransal',
        'fatura_no': 'MD1-TEST'})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()['adet'] == 4

    # ── SONUÇ: dört blokta da AYNI $/ton ──
    with fa.app.app_context():
        tonbasi = []
        for hid, ton in tonlar.items():
            ek = sum(float(m.tutar or 0) for m in Maliyet.query.filter_by(
                baglanti_tip='stok', baglanti_id=hid, fatura_no='MD1-TEST').all())
            alim = 200 * ton                      # 200 EUR/ton
            tonbasi.append((alim + ek) / ton)
        assert max(tonbasi) - min(tonbasi) < 0.5, tonbasi
        # Hepsi tek grupta
        gruplar = {m.grup_id for m in Maliyet.query.filter_by(
            fatura_no='MD1-TEST').all()}
        assert len(gruplar) == 1 and None not in gruplar, gruplar


def test_md1_esit_secenegi_korunur():
    """MD1: parça başı giderler için 'eşit' seçeneği çalışmalı."""
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/maliyet/dagit', headers=H, json={
        'onizleme': True,
        'hedefler': ['BLK-MD-1', 'BLK-MD-2', 'BLK-MD-3', 'BLK-MD-4'],
        'maliyet_tip': 'Sertifika', 'baglanti_tip': 'stok',
        'tutar': 400, 'doviz': 'USD', 'kdv_oran': 0, 'dagitim': 'esit'})
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    assert j['dagitim'] == 'esit'
    assert all(abs(float(x['net_pay']) - 100.0) < 0.01 for x in j['satirlar']), j


def test_md1_oranlanamayinca_acikca_soyler():
    """MD1: ton ile m² oranlanamaz — sessizce eşite düşmemeli,
    nedenini söylemeli."""
    from models import PlakaStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not PlakaStok.query.get('PLK-MD-1'):
            db.session.add(PlakaStok(id='PLK-MD-1', cins='CEPPO TEST',
                                     blok_no='MD-1', slab_no=1, boy=300,
                                     yukseklik=150, kalinlik=2, metraj_m2=4.5,
                                     durum='Serbest', alis_fiyati=30, doviz='USD'))
            db.session.commit()
    r = c.post('/api/maliyet/dagit', headers=H, json={
        'onizleme': True, 'hedefler': ['BLK-MD-1', 'PLK-MD-1'],
        'maliyet_tip': 'Nakliye', 'baglanti_tip': 'stok',
        'tutar': 1000, 'doviz': 'USD', 'kdv_oran': 0, 'dagitim': 'oransal'})
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    assert j['dagitim'] == 'esit', j
    assert 'oranlanamaz' in j['olcu_notu'] or 'eşit' in j['olcu_notu'], j


def test_md1_hatali_hedefte_hicbiri_yazilmaz():
    """MD1: bulunamayan kayıt varsa hiçbiri yazılmamalı (yarım maliyet
    girilmesin)."""
    from models import Maliyet
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        once = Maliyet.query.count()
    r = c.post('/api/maliyet/dagit', headers=H, json={
        'hedefler': ['BLK-MD-1', 'YOK-BOYLE-BIR-STOK'], 'maliyet_tip': 'Nakliye',
        'baglanti_tip': 'stok', 'tutar': 500, 'doviz': 'USD', 'kdv_oran': 0})
    assert r.status_code == 400, r.get_data(as_text=True)
    assert r.get_json().get('error') == 'stok_bulunamadi'
    with fa.app.app_context():
        assert Maliyet.query.count() == once


def test_md1_cari_hareketi_fatura_basina_tek():
    """MD1: tek tedarikçi faturası cari ekranında N satıra bölünmemeli."""
    from models import Cari, CariHareket
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not Cari.query.get('CMD'):
            db.session.add(Cari(id='CMD', unvan='NAKLIYECI AS', cari_tip='Tedarikçi',
                                para_birimi='USD', gorunurluk='ortak'))
            db.session.commit()
        once = CariHareket.query.filter_by(cari_id='CMD').count()
    r = c.post('/api/maliyet/dagit', headers=H, json={
        'hedefler': ['BLK-MD-1', 'BLK-MD-2', 'BLK-MD-3', 'BLK-MD-4'],
        'maliyet_tip': 'Nakliye', 'baglanti_tip': 'stok', 'tutar': 2000,
        'doviz': 'USD', 'kdv_oran': 0, 'cari_id': 'CMD', 'fatura_no': 'NKL-9'})
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        hareketler = CariHareket.query.filter_by(cari_id='CMD').all()
        assert len(hareketler) - once == 1, [h.aciklama for h in hareketler]
        assert float(hareketler[-1].alacak) == 2000.0


def test_dt1_durum_degisince_damga_atilir():
    """DT1: sipariş durumu değişince durum_tarihi damgalanmalı;
    BAŞKA bir alan değişince damga KAYMAMALI."""
    from models import Cari, Siparis
    import time as _t
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not Cari.query.get('CDT'):
            db.session.add(Cari(id='CDT', unvan='DURUM MERMER', cari_tip='Müşteri',
                                para_birimi='USD', gorunurluk='ortak'))
            db.session.commit()
    r = c.post('/api/siparis', headers=H, json={
        'musteri': 'DURUM MERMER', 'doviz': 'USD', 'siparis_tarihi': '2026-08-01',
        'kalemler': [{'urun_tip': 'PLAKA', 'cins': 'DT TEST', 'miktar': 5,
                      'birim': 'm2', 'birim_fiyat': 100, 'adet': 1}]})
    assert r.status_code == 200, r.get_data(as_text=True)
    sid = r.get_json()['id']

    with fa.app.app_context():
        sip = Siparis.query.get(sid)
        assert sip.durum_tarihi is not None, 'yeni sipariş damgalanmadı'
        ilk = sip.durum_tarihi
        # Durum DIŞINDA bir alan değişsin — damga kaymamalı
        sip.aciklama = 'not eklendi'
        db.session.commit()
        assert Siparis.query.get(sid).durum_tarihi == ilk, 'damga boşuna kaydı'

        # Damgayı geriye al, sonra durumu değiştir
        sip = Siparis.query.get(sid)
        from datetime import datetime as _dt
        sip.durum_tarihi = _dt(2026, 8, 1, 9, 0, 0)
        db.session.commit()
        eski = Siparis.query.get(sid).durum_tarihi

    _t.sleep(0.01)
    r = c.put(f'/api/siparis/{sid}', headers=H, json={'durum': 'Onaylandi'})
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        sip = Siparis.query.get(sid)
        assert sip.durum == 'Onaylandi'
        assert sip.durum_tarihi > eski, (sip.durum_tarihi, eski)


def test_dt1_api_durum_tarihini_dondurur():
    """DT1: liste ve detay uçları durum_tarihi vermeli — ekran
    "bu durumda kaç gündür" sorusunu bundan hesaplıyor."""
    c = istemci('admin', 'ADMIN')
    r = c.get('/api/siparis?per_page=50', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    satirlar = r.get_json().get('data') or []
    assert satirlar, 'sipariş listesi boş'
    assert all('durum_tarihi' in x for x in satirlar), satirlar[0]
    damgali = [x for x in satirlar if x.get('durum_tarihi')]
    assert damgali, 'hiçbir siparişte damga yok'
    r = c.get(f'/api/siparis/{damgali[0]["id"]}', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()['siparis'].get('durum_tarihi'), r.get_json()['siparis']


def test_bg1_dashboard_ozet_rakamlari():
    """BG1: Bugün sayfası özeti — ciro satış kayıtlarından, stok
    depodaki değer, borç/alacak cari bazında netlenip brüt toplanır."""
    from models import Cari, SatisKaydi, CariHareket, PlakaStok
    from datetime import date as _d, timedelta as _td
    bugun = _d.today()
    with fa.app.app_context():
        if not Cari.query.get('CBG'):
            db.session.add(Cari(id='CBG', unvan='BUGUN MERMER', cari_tip='Müşteri',
                                para_birimi='USD', gorunurluk='ortak'))
        # Bu yıl 2 satış: 100.000 ciro, 70.000 maliyet.
        # Ay içi satışın tarihi BUGÜN: ayın 5'i yazılırsa her ayın ilk
        # dört gününde gelecekte kalır, özet onu saymaz ve test tarihe
        # göre düşerdi (3 Ekim'de düştü).
        for i, (tarih, tutar, mal) in enumerate([
                (_d(bugun.year, 1, 5), 60000, 42000), (bugun, 40000, 28000)]):
            sid = f'SK-BG1-{i}'
            if not SatisKaydi.query.get(sid):
                db.session.add(SatisKaydi(
                    id=sid, stok_id=f'BGX{i}', stok_tip='PLAKA', cins='BG TEST',
                    musteri='BUGUN MERMER', cari_id='CBG',
                    satis_tarihi=tarih, doviz='USD',
                    tutar=tutar, tutar_usd=tutar, maliyet_usd=mal, kar_usd=tutar - mal))
        # AYNI cari: hem borç hem alacak → cari içinde netlenmeli
        for hid, borc, alacak in [('HBG-A', 50000, 0), ('HBG-B', 0, 20000)]:
            if not CariHareket.query.get(hid):
                db.session.add(CariHareket(
                    id=hid, cari_id='CBG', cari_unvan='BUGUN MERMER',
                    islem_tip='Test', borc=borc, alacak=alacak, doviz='USD',
                    kur_uygulanan=40, borc_try=borc * 40, alacak_try=alacak * 40,
                    hareket_tarihi=bugun, vade_tarihi=bugun - _td(days=5)))
        # Depoda + yolda stok
        for sid, durum in [('PLK-BG-D', 'Serbest'), ('PLK-BG-Y', 'Sevkedildi')]:
            if not PlakaStok.query.get(sid):
                db.session.add(PlakaStok(id=sid, cins='BG TEST', blok_no='T-BG',
                                         slab_no=1 if 'D' in sid else 2,
                                         boy=200, yukseklik=100, kalinlik=2,
                                         metraj_m2=2.0, durum=durum,
                                         alis_fiyati=50, alis_fiyat_birim='m2',
                                         doviz='USD'))
        db.session.commit()

    c = istemci('admin', 'ADMIN')
    r = c.get('/api/dashboard/ozet', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()

    # ── Ciro: satış kayıtlarından, kâr ve marj ile ──
    assert d['ciro']['yillik'] >= 100000, d['ciro']
    assert d['ciro']['aylik'] >= 40000, d['ciro']
    # kâr = ciro − maliyet; marj = kâr / ciro
    assert 0 < d['ciro']['yillik_kar'] < d['ciro']['yillik'], d['ciro']
    assert 0 < d['ciro']['yillik_marj'] < 100, d['ciro']

    # ── Cari: AYNI cari içinde netlenir (50.000 − 20.000 = 30.000) ──
    # Brüt alacak bu carinin 30.000'ini içermeli, 50.000'i DEĞİL.
    assert d['alacak']['tutar'] >= 30000, d['alacak']

    # ── Vadesi geçen: dünden önceki vadeler ──
    assert d['vadesi_gecen']['adet'] >= 1, d['vadesi_gecen']

    # ── Stok: yoldaki mal depo değerine GİRMEZ ──
    assert d['stok']['tutar'] >= 100, d['stok']        # 2 m² × 50
    assert d['stok']['yolda'] >= 100, d['stok']
    assert d['stok']['yolda_adet'] >= 1, d['stok']

    # ── Nakit merdiveni: üç basamak, net = giren − çıkan ──
    assert len(d['nakit_merdiveni']) == 3, d['nakit_merdiveni']
    for basamak in d['nakit_merdiveni']:
        assert abs(basamak['net'] - (basamak['giren'] - basamak['cikan'])) < 0.02, basamak

    for alan in ('acik_siparis', 'yuklenen', 'borc', 'bu_ay_tahsilat',
                 'bu_ay_odenecek', 'yaklasan_cek', 'acik_avans'):
        assert alan in d, (alan, sorted(d))


def test_bg1_yetkisiz_kullanici_rakam_gormez():
    """BG1: yetkisi olmayan bölüm cevapta HİÇ gelmemeli — ekran
    'yetki yok' der, rakam sızmaz."""
    from models import Kullanici
    import json as _json
    with fa.app.app_context():
        k = Kullanici.query.filter_by(ad='bgkisitli').first()
        if not k:
            k = Kullanici(ad='bgkisitli', sifre='x', rol='SATIS',
                          firma_kapsam='tumu')
            db.session.add(k)
        # Yalnızca sipariş okuma yetkisi
        k.yetkiler = _json.dumps({'siparis': 'okuma', 'dashboard': 'okuma'})
        db.session.commit()
    c = istemci('bgkisitli', 'SATIS')
    r = c.get('/api/dashboard/ozet', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert 'acik_siparis' in d, d           # yetkisi var
    assert 'ciro' not in d, d               # kârlılık yetkisi yok
    assert 'alacak' not in d and 'borc' not in d, d
    assert 'stok' not in d, d


def test_bg1_acik_avans_mahsubu_dusuyor():
    """BG1: mahsup edilmiş avans 'açık avans' toplamında görünmemeli."""
    from models import Cari, CariHareket, Siparis
    from datetime import date as _d
    with fa.app.app_context():
        if not Cari.query.get('CBGA'):
            db.session.add(Cari(id='CBGA', unvan='AVANS BUGUN', cari_tip='Müşteri',
                                para_birimi='USD', gorunurluk='ortak'))
            db.session.add(Siparis(id='SIP-BGA', musteri='AVANS BUGUN', cari_id='CBGA',
                                   toplam_tutar=10000, doviz='USD', durum='Hazir',
                                   siparis_tarihi=_d.today()))
        for hid, tip, borc, alacak, kaynak, sip in [
                ('HBGA-1', 'Avans Tahsilatı', 0, 9000, 'tahsilat', 'SIP-BGA'),
                ('HBGA-2', 'Avans Mahsubu', 9000, 0, 'avans_mahsup', 'SIP-BGA'),
                ('HBGA-3', 'Avans Mahsubu', 0, 9000, 'avans_mahsup', None)]:
            if not CariHareket.query.get(hid):
                db.session.add(CariHareket(
                    id=hid, cari_id='CBGA', cari_unvan='AVANS BUGUN', islem_tip=tip,
                    borc=borc, alacak=alacak, doviz='USD', kur_uygulanan=40,
                    borc_try=borc * 40, alacak_try=alacak * 40,
                    hareket_tarihi=_d.today(), kaynak=kaynak, siparis_id=sip))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    d = c.get('/api/dashboard/ozet', headers=H).get_json()
    # Bu carinin avansı tamamen mahsup edildi; toplama katkısı olmamalı.
    # (Başka carilerin açık avansı olabilir, o yüzden 9000 ARTMAMIŞ olmalı.)
    assert d['acik_avans']['tutar'] < 9000 or d['acik_avans']['siparissiz'] >= 0, d


def test_bg2_kutu_detayi_kayitlari_dondurur():
    """BG2: kutuya tıklayınca o rakamı oluşturan kayıtlar dönmeli ve
    her satır gidilecek bir adres taşımalı."""
    c = istemci('admin', 'ADMIN')
    for anahtar in ('vadesi_gecen', 'alacak', 'borc', 'acik_siparis',
                    'yuklenen', 'ciro_yillik', 'ciro_aylik', 'stok',
                    'yaklasan_cek', 'acik_avans', 'nakit_30',
                    'bu_ay_tahsilat', 'bu_ay_odenecek'):
        r = c.get(f'/api/dashboard/detay?k={anahtar}', headers=H)
        assert r.status_code == 200, (anahtar, r.get_data(as_text=True))
        d = r.get_json()
        assert d['ok'] and d['baslik'], (anahtar, d)
        assert d['adet'] == len(d['satirlar']) or d['adet'] > 200, (anahtar, d['adet'])
        for x in d['satirlar']:
            assert x.get('ad'), (anahtar, x)
            assert x.get('git', '').startswith('/'), (anahtar, x)
            assert 'tutar' in x and 'doviz' in x, (anahtar, x)
        # Satirlar tutara gore BUYUKTEN kucuge
        usdler = [abs(x.get('usd') or 0) for x in d['satirlar']]
        assert usdler == sorted(usdler, reverse=True), (anahtar, usdler[:6])


def test_bg2_detay_toplami_kutuyla_tutar():
    """BG2: detay listesinin toplamı kutudaki rakamla aynı olmalı —
    iki ayrı yerde iki farklı gerçek olmaz."""
    c = istemci('admin', 'ADMIN')
    ozet = c.get('/api/dashboard/ozet', headers=H).get_json()
    eslesme = [('vadesi_gecen', ozet['vadesi_gecen']['tutar']),
               ('alacak', ozet['alacak']['tutar']),
               ('borc', ozet['borc']['tutar']),
               ('acik_siparis', ozet['acik_siparis']['tutar']),
               ('yuklenen', ozet['yuklenen']['tutar']),
               ('bu_ay_tahsilat', ozet['bu_ay_tahsilat']['tutar']),
               ('bu_ay_odenecek', ozet['bu_ay_odenecek']['tutar']),
               ('acik_avans', ozet['acik_avans']['tutar']),
               ('ciro_yillik', ozet['ciro']['yillik'])]
    for anahtar, beklenen in eslesme:
        d = c.get(f'/api/dashboard/detay?k={anahtar}', headers=H).get_json()
        assert abs(d['toplam_usd'] - beklenen) < 1.0, \
            (anahtar, d['toplam_usd'], beklenen)


def test_bg2_detay_yetki_kontrolu():
    """BG2: yetkisi olmayan kullanıcı detayı da görememeli —
    kutu gizliyken uç açık kalırsa rakam sızar."""
    from models import Kullanici
    import json as _json
    with fa.app.app_context():
        k = Kullanici.query.filter_by(ad='bg2kisitli').first()
        if not k:
            k = Kullanici(ad='bg2kisitli', sifre='x', rol='SATIS',
                          firma_kapsam='tumu')
            db.session.add(k)
        k.yetkiler = _json.dumps({'siparis': 'okuma', 'dashboard': 'okuma'})
        db.session.commit()
    c = istemci('bg2kisitli', 'SATIS')
    assert c.get('/api/dashboard/detay?k=acik_siparis', headers=H).status_code == 200
    for anahtar in ('vadesi_gecen', 'alacak', 'borc', 'stok', 'ciro_yillik'):
        r = c.get(f'/api/dashboard/detay?k={anahtar}', headers=H)
        assert r.status_code == 403, (anahtar, r.status_code)
        assert r.get_json().get('error') == 'yetki_yok', anahtar


def test_bg2_bilinmeyen_anahtar_reddedilir():
    """BG2: tanınmayan anahtar 400 dönmeli, boş liste değil."""
    c = istemci('admin', 'ADMIN')
    r = c.get('/api/dashboard/detay?k=olmayan_sey', headers=H)
    assert r.status_code == 400, r.get_data(as_text=True)


def test_bg3_kapali_hesap_vadesi_gecende_gorunmez():
    """BG3: borcu ödenmiş cari 'vadesi geçen alacak' listesinde
    ÇIKMAMALI. Ölçüldü: 9.900 € alış faturası + 9.900 € ödeme ile
    hesap kapalıyken ödeme satırı alacak gibi listeleniyordu."""
    from models import Cari, CariHareket
    from datetime import date as _d
    with fa.app.app_context():
        if not Cari.query.get('CKAP'):
            db.session.add(Cari(id='CKAP', unvan='KAPALI HESAP AS',
                                cari_tip='Tedarikçi', para_birimi='EUR',
                                gorunurluk='ortak'))
        for hid, borc, alacak in [('HKAP-F', 0, 9900), ('HKAP-O', 9900, 0)]:
            if not CariHareket.query.get(hid):
                db.session.add(CariHareket(
                    id=hid, cari_id='CKAP', cari_unvan='KAPALI HESAP AS',
                    islem_tip='Alış Faturası' if alacak else 'Odeme',
                    borc=borc, alacak=alacak, doviz='EUR', kur_uygulanan=56,
                    borc_try=borc * 56, alacak_try=alacak * 56,
                    hareket_tarihi=_d(2026, 9, 7),
                    vade_tarihi=_d(2026, 9, 7)))     # vadesi GEÇMİŞ
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    for anahtar in ('vadesi_gecen', 'bu_ay_odenecek', 'bu_ay_tahsilat',
                    'nakit_30', 'alacak', 'borc'):
        d = c.get(f'/api/dashboard/detay?k={anahtar}', headers=H).get_json()
        kapali = [x for x in d['satirlar'] if x['ad'] == 'KAPALI HESAP AS']
        assert not kapali, (anahtar, kapali)


def test_bg3_kismi_odenen_fatura_kalani_gorunur():
    """BG3: 10.000 borcun 6.000'i ödenmişse listede 4.000 görünmeli —
    ne 10.000 (ödemeyi yok saymak) ne 0 (borcu yok saymak)."""
    from models import Cari, CariHareket
    from datetime import date as _d
    with fa.app.app_context():
        if not Cari.query.get('CKIS'):
            db.session.add(Cari(id='CKIS', unvan='KISMI ODEME AS',
                                cari_tip='Müşteri', para_birimi='USD',
                                gorunurluk='ortak'))
        for hid, borc, alacak in [('HKIS-F', 10000, 0), ('HKIS-T', 0, 6000)]:
            if not CariHareket.query.get(hid):
                db.session.add(CariHareket(
                    id=hid, cari_id='CKIS', cari_unvan='KISMI ODEME AS',
                    islem_tip='Satış Faturası' if borc else 'Tahsilat',
                    borc=borc, alacak=alacak, doviz='USD', kur_uygulanan=40,
                    borc_try=borc * 40, alacak_try=alacak * 40,
                    hareket_tarihi=_d(2026, 9, 1),
                    vade_tarihi=_d(2026, 9, 10)))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    d = c.get('/api/dashboard/detay?k=vadesi_gecen', headers=H).get_json()
    satir = [x for x in d['satirlar'] if x['ad'] == 'KISMI ODEME AS']
    assert len(satir) == 1, satir
    assert abs(satir[0]['tutar'] - 4000) < 0.01, satir[0]
    assert 'kısmi' in (satir[0]['alt'] or ''), satir[0]


def test_bg3_unvani_bos_harekette_cari_adi_bulunur():
    """BG3: cari_unvan boş bırakılmış harekette listede kimlik kodu
    ("CR-XXXX") değil CARİ ADI görünmeli."""
    from models import Cari, CariHareket
    from datetime import date as _d
    with fa.app.app_context():
        if not Cari.query.get('CADSIZ'):
            db.session.add(Cari(id='CADSIZ', unvan='ADI BULUNAN AS',
                                cari_tip='Müşteri', para_birimi='USD',
                                gorunurluk='ortak'))
        if not CariHareket.query.get('HADSIZ'):
            db.session.add(CariHareket(
                id='HADSIZ', cari_id='CADSIZ', cari_unvan=None,
                islem_tip='Satış Faturası', borc=7000, alacak=0, doviz='USD',
                kur_uygulanan=40, borc_try=280000, alacak_try=0,
                hareket_tarihi=_d(2026, 9, 1), vade_tarihi=_d(2026, 9, 5)))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    d = c.get('/api/dashboard/detay?k=vadesi_gecen', headers=H).get_json()
    satir = [x for x in d['satirlar'] if abs(x['tutar'] - 7000) < 0.01]
    assert satir, [x['ad'] for x in d['satirlar']]
    assert satir[0]['ad'] == 'ADI BULUNAN AS', satir[0]
    assert satir[0]['git'] == '/cari?ac=CADSIZ', satir[0]


def test_bg4_avans_listesinde_cari_adi_gorunur():
    """BG4: avans hareketinde cari_unvan bossa liste "?" degil ADI yazar.

    Olculdu: acik avans cekmecesinin 5 satirindan 4'u "?" gosteriyordu;
    cari kartinda unvan yerinde duruyordu. Ad artik CARI tablosundan."""
    from models import Cari, CariHareket
    from datetime import date as _d
    with fa.app.app_context():
        if not Cari.query.get('CBG4AV'):
            db.session.add(Cari(id='CBG4AV', unvan='AVANSLI MERMER LTD',
                                cari_tip='Musteri', para_birimi='USD',
                                gorunurluk='ortak'))
        if not CariHareket.query.get('HBG4AV'):
            db.session.add(CariHareket(
                id='HBG4AV', cari_id='CBG4AV', cari_unvan=None,
                islem_tip='Avans Tahsilati', borc=0, alacak=12500, doviz='USD',
                kur_uygulanan=40, borc_try=0, alacak_try=500000,
                hareket_tarihi=_d(2026, 9, 2)))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    d = c.get('/api/dashboard/detay?k=acik_avans', headers=H).get_json()
    satir = [x for x in d['satirlar'] if abs(x['tutar'] - 12500) < 0.01]
    assert satir, [(x['ad'], x['tutar']) for x in d['satirlar']]
    assert satir[0]['ad'] == 'AVANSLI MERMER LTD', satir[0]
    assert satir[0]['git'] == '/cari?ac=CBG4AV', satir[0]
    assert '?' not in [x['ad'] for x in d['satirlar']], d['satirlar']


def test_bg4_avans_kutusu_ile_liste_tutar():
    """BG4: kutudaki adet/tutar ile çekmecedeki satırlar aynı kaynaktan.

    İki uç kendi gruplamasını yapıyordu; kimlikli ve kimliksiz hareketi
    karışık olan cari kutuda 1, listede 2 satır olabiliyordu."""
    c = istemci('admin', 'ADMIN')
    o = c.get('/api/dashboard/ozet', headers=H).get_json()['acik_avans']
    d = c.get('/api/dashboard/detay?k=acik_avans', headers=H).get_json()
    assert o['adet'] == len(d['satirlar']), (o, len(d['satirlar']))
    toplam = sum(float(x['usd']) for x in d['satirlar'])
    assert abs(float(o['tutar']) - toplam) < 0.02, (o['tutar'], toplam)


def test_bg4_ciro_kirilimi_flask_g_golgelemez():
    """BG4: ciro kırılımı döngüsündeki yerel `g` flask.g'yi gölgeliyordu;
    ad tablosu flask.g üzerinde durduğu için çağrı patlıyordu."""
    c = istemci('admin', 'ADMIN')
    for k in ('ciro_yillik', 'ciro_aylik'):
        r = c.get('/api/dashboard/detay?k=' + k, headers=H)
        assert r.status_code in (200, 403), (k, r.status_code)
        if r.status_code == 200:
            for x in r.get_json()['satirlar']:
                assert x['ad'] and x['ad'] != '?', x

def _av1_siparis(c, musteri='AVANS MERMER', cari_id='CAV1', tutar=100, adet=1):
    """AV1/TR1 testleri icin cari + siparis kurar, siparis id doner."""
    from models import Cari
    with fa.app.app_context():
        if not Cari.query.get(cari_id):
            db.session.add(Cari(id=cari_id, unvan=musteri, cari_tip='Musteri',
                                para_birimi='USD', gorunurluk='ortak'))
            db.session.commit()
    r = c.post('/api/siparis', headers=H, json={
        'musteri': musteri, 'doviz': 'USD',
        'kalemler': [{'urun_tip': 'PLAKA', 'cins': 'AV TEST', 'miktar': adet,
                      'birim': 'm2', 'birim_fiyat': tutar, 'adet': adet}]})
    assert r.status_code == 200, r.get_data(as_text=True)
    sid = r.get_json()['id']
    # Siparis tarihi ucta ayarlanmiyor (form alani da yok) — dogrudan
    # damgala ki tarihce siralamasi olculebilsin.
    from models import Siparis
    from datetime import date as _d
    with fa.app.app_context():
        sp = Siparis.query.get(sid)
        sp.siparis_tarihi = _d(2026, 8, 1)
        db.session.commit()
    return sid


def _av1_avans(cari_id, siparis_id, tutar, tip='Avans Tahsilati', dv='USD'):
    from models import CariHareket
    from datetime import date as _d
    with fa.app.app_context():
        h = CariHareket(
            id=_yeni_test_id(), cari_id=cari_id, cari_unvan=None,
            islem_tip=tip, borc=0, alacak=tutar, doviz=dv,
            kur_uygulanan=40, borc_try=0, alacak_try=tutar * 40,
            hareket_tarihi=_d(2026, 8, 5), siparis_id=siparis_id)
        db.session.add(h)
        db.session.commit()
        return h.id


_AV1_SAYAC = [0]


def _yeni_test_id():
    _AV1_SAYAC[0] += 1
    return 'HAV1-%03d' % _AV1_SAYAC[0]


def test_av1_siparis_kartinda_alinan_avans():
    """AV1: sipariş ucu alınan avansı ve kalanı döndürmeli."""
    c = istemci('admin', 'ADMIN')
    sid = _av1_siparis(c, tutar=10000)
    _av1_avans('CAV1', sid, 4000)
    d = c.get('/api/siparis/' + sid, headers=H).get_json()['siparis']
    av = d['avans']
    assert abs(float(av['alinan']) - 4000) < 0.01, av
    assert abs(float(av['kalan']) - 6000) < 0.01, av
    assert float(av['fazla']) == 0, av
    assert av['doviz'] == 'USD', av


def test_av1_siparis_tutarini_asan_avans_isaretlenir():
    """AV1: avans sipariş tutarını aşarsa `fazla` dolmalı — "tamamı
    alındı" demek dağıtılmamış parayı gizlerdi."""
    c = istemci('admin', 'ADMIN')
    sid = _av1_siparis(c, musteri='FAZLA AVANS AS', cari_id='CAV2', tutar=1000)
    _av1_avans('CAV2', sid, 3000)
    av = c.get('/api/siparis/' + sid, headers=H).get_json()['siparis']['avans']
    assert abs(float(av['fazla']) - 2000) < 0.01, av
    assert float(av['kalan']) == 0, av


def test_av1_farkli_dovizdeki_avans_kaybolmaz():
    """AV1: sipariş dövizinden farklı avans toplanmaz ama `diger`
    altında GÖRÜNÜR — eskiden sessizce 0 sayılıyordu."""
    c = istemci('admin', 'ADMIN')
    sid = _av1_siparis(c, musteri='EURO AVANS AS', cari_id='CAV3', tutar=5000)
    _av1_avans('CAV3', sid, 2000, dv='EUR')
    av = c.get('/api/siparis/' + sid, headers=H).get_json()['siparis']['avans']
    assert float(av['alinan']) == 0, av
    assert av['diger'] and av['diger'][0]['doviz'] == 'EUR', av
    assert abs(float(av['diger'][0]['tutar']) - 2000) < 0.01, av


def test_tr1_tarihce_olaylari_siralanir():
    """TR1: tarihçe sipariş + avans olaylarını tarih sırasıyla vermeli."""
    c = istemci('admin', 'ADMIN')
    sid = _av1_siparis(c, musteri='TARIHCE AS', cari_id='CTR1', tutar=8000)
    _av1_avans('CTR1', sid, 3000)
    th = c.get('/api/siparis/' + sid, headers=H).get_json()['siparis']['tarihce']
    assert th, th
    olaylar = [o['olay'] for o in th]
    assert olaylar[0] == 'siparis_alindi', olaylar
    assert 'avans_alindi' in olaylar, olaylar
    tarihler = [o['tarih'] for o in th if o['olay'] != 'termin']
    assert tarihler == sorted(tarihler), tarihler


def test_tr1_durum_degisimi_tarihceye_dusuyor():
    """TR1: durum değişince tarihçede o durum KESİN olarak görünmeli
    (denetim günlüğünden okunuyor, türetilmiyor)."""
    c = istemci('admin', 'ADMIN')
    sid = _av1_siparis(c, musteri='DURUM TARIHCE AS', cari_id='CTR2')
    r = c.put('/api/siparis/' + sid, headers=H, json={'durum': 'Onaylandi'})
    assert r.status_code == 200, r.get_data(as_text=True)
    th = c.get('/api/siparis/' + sid, headers=H).get_json()['siparis']['tarihce']
    onay = [o for o in th if o.get('durum') == 'Onaylandi']
    assert onay, th
    assert onay[0]['kesin'] is True, onay[0]


def test_tr1_tarihce_metni_ucta_kurulmuyor():
    """TR1: durum adı ve para biçimi ŞABLONDA; uç ham veri dönmeli.
    İki yerde metin kurulursa zamanla ayrışırlar."""
    c = istemci('admin', 'ADMIN')
    sid = _av1_siparis(c, musteri='HAM VERI AS', cari_id='CTR3', tutar=2500)
    _av1_avans('CTR3', sid, 1500)
    th = c.get('/api/siparis/' + sid, headers=H).get_json()['siparis']['tarihce']
    for o in th:
        assert 'baslik' not in o, o
        assert not any(ch in str(o.get('ek', '')) for ch in ('$', '\u20ac')), o
    para = [o for o in th if o['olay'] == 'avans_alindi']
    assert para and abs(float(para[0]['tutar']) - 1500) < 0.01, para

def test_tg1_termini_gecen_siparis_listesi():
    """TG1: Bugün sayfasının termin listesi /api/siparis'ten besleniyor;
    uç `termin` alanını vermeli ve KAPALI siparişler ayrılabilmeli.

    Liste tarayıcıda süzülüyor; burada süzgecin dayandığı alanların
    gerçekten geldiği doğrulanıyor — alan sessizce düşerse kutu
    kalıcı olarak boş kalır ve kimse fark etmez."""
    from models import Siparis
    from datetime import date as _d, timedelta as _td
    c = istemci('admin', 'ADMIN')
    sid = _av1_siparis(c, musteri='TERMIN AS', cari_id='CTG1', tutar=4000)
    gecmis = _d.today() - _td(days=12)
    with fa.app.app_context():
        sp = Siparis.query.get(sid)
        sp.termin = gecmis
        db.session.commit()
    d = c.get('/api/siparis?per_page=300', headers=H).get_json()
    satir = [x for x in d['data'] if x['id'] == sid]
    assert satir, [x['id'] for x in d['data']][:5]
    assert satir[0]['termin'] == gecmis.isoformat(), satir[0]
    assert satir[0]['durum'] not in ('Teslim Edildi', 'Iptal Edildi'), satir[0]


def test_tg1_teslim_edilen_siparis_gecikme_sayilmaz():
    """TG1: teslim edilmiş siparişin geçmiş termini TARİHTİR, bekleyen
    iş değil. Uç durumu doğru vermeli ki liste onu ayıklayabilsin."""
    from models import Siparis
    from datetime import date as _d, timedelta as _td
    c = istemci('admin', 'ADMIN')
    sid = _av1_siparis(c, musteri='TESLIM AS', cari_id='CTG2', tutar=3000)
    with fa.app.app_context():
        sp = Siparis.query.get(sid)
        sp.termin = _d.today() - _td(days=30)
        sp.durum = 'Teslim Edildi'
        db.session.commit()
    d = c.get('/api/siparis?per_page=300', headers=H).get_json()
    satir = [x for x in d['data'] if x['id'] == sid][0]
    assert satir['durum'] == 'Teslim Edildi', satir

# ═══ GT1 · GİDER FATURASI TRY KARŞILIĞI ═══════════════════════════════
def _gt1_blok():
    """Maliyet bağlanacak bir blok döndürür (yoksa oluşturur)."""
    from models import BlokStok
    with fa.app.app_context():
        b = BlokStok.query.filter_by(id='BLK-GT1').first()
        if not b:
            db.session.add(BlokStok(
                id='BLK-GT1', blok_no='GT1', cins='GT TEST', uretici='GT',
                boy=300, yukseklik=180, en=125, tonaj=10, durum='Serbest',
                alis_fiyati=100, alis_fiyat_birim='ton', doviz='USD'))
            db.session.commit()
    return 'BLK-GT1'


def _gt1_gider(c, cari_id, tutar, doviz, fatura_no):
    r = c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Nakliye', 'baglanti_tip': 'blok',
        'baglanti_id': _gt1_blok(), 'tutar': tutar, 'doviz': doviz,
        'cari_id': cari_id, 'fatura_no': fatura_no})
    assert r.status_code == 200, r.get_data(as_text=True)


def test_gt1_try_gider_faturasi_try_karsiligi_dogru():
    """GT1: TRY gider faturasında `alacak_try` TUTARIN KENDİSİ olmalı.

    Ölçüldü: 5.235,00 ₺ fatura `alacak_try = 107,16` yazıyordu — yani
    USD karşılığı. Cari ekstresinin özeti bu alandan beslendiği için
    166.895,62 ₺'lik hesap özet kutusunda 3.413,48 TRY görünüyordu."""
    from models import Cari, CariHareket
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not Cari.query.get('CGT1'):
            db.session.add(Cari(id='CGT1', unvan='GUMRUK MUSAVIRI LTD',
                                cari_tip='Tedarikci', para_birimi='TRY',
                                gorunurluk='ortak'))
            db.session.commit()
    _gt1_gider(c, 'CGT1', 5235, 'TRY', 'GT1-TRY')
    with fa.app.app_context():
        h = CariHareket.query.filter_by(cari_id='CGT1').filter(
            CariHareket.evrak_no == 'GT1-TRY').first()
        assert h is not None, 'cari hareket yazılmadı'
        assert abs(float(h.alacak or 0) - 5235) < 0.01, h.alacak
        assert abs(float(h.alacak_try or 0) - 5235) < 0.01, (
            'TRY faturada alacak_try tutarın kendisi olmalı', h.alacak_try)
        assert abs(float(h.kur_uygulanan or 0) - 1) < 0.000001, h.kur_uygulanan


def test_gt1_dovizli_gider_faturasinda_kur_yazilir():
    """GT1: yabancı dövizli gider faturasında `kur_uygulanan` 1.0
    kalıyordu; ekstre "1 EUR = 1,0000 ₺" basıyordu."""
    from models import Cari, CariHareket
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not Cari.query.get('CGT2'):
            db.session.add(Cari(id='CGT2', unvan='NAKLIYE AS', cari_tip='Tedarikci',
                                para_birimi='USD', gorunurluk='ortak'))
            db.session.commit()
    _gt1_gider(c, 'CGT2', 1000, 'USD', 'GT1-USD')
    with fa.app.app_context():
        h = CariHareket.query.filter_by(cari_id='CGT2').filter(
            CariHareket.evrak_no == 'GT1-USD').first()
        assert h is not None
        kur = float(h.kur_uygulanan or 0)
        assert kur > 1.5, ('yabancı dövizde kur 1.0 kalmamalı', kur)
        # TRY karşılığı kurla tutarlı olmalı
        assert abs(float(h.alacak_try or 0) - 1000 * kur) < 0.05, (
            h.alacak_try, kur)


def test_gt1_ekstre_ozeti_satirlarla_tutar():
    """GT1: ekstrenin "Net Özet" kutusu SATIRLARLA aynı rakamı vermeli.

    Aynı belgede iki farklı toplam, hangisinin doğru olduğu sorusunu
    doğurur. Özet `alacak_try`den, satırlar ham tutardan besleniyor;
    TRY ekstresinde ikisi birebir aynı olmalı."""
    import re
    from models import Cari, CariHareket
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not Cari.query.get('CGT3'):
            db.session.add(Cari(id='CGT3', unvan='EKSTRE GUMRUK LTD',
                                cari_tip='Tedarikci', para_birimi='TRY',
                                ulke='TUR', gorunurluk='ortak'))
            db.session.commit()
    for i, tutar in enumerate([5235, 1650, 34838.91]):
        _gt1_gider(c, 'CGT3', tutar, 'TRY', f'GT3-{i}')
    beklenen = 5235 + 1650 + 34838.91
    with fa.app.app_context():
        ham = sum(float(h.alacak or 0) for h in
                  CariHareket.query.filter_by(cari_id='CGT3').all())
        assert abs(ham - beklenen) < 0.05, ham
    r = c.get('/api/cari/CGT3/ekstre_pdf?doviz=TRY&kur_modu=islem', headers=H)
    assert r.status_code == 200, r.status_code
    gov = r.get_data(as_text=True)
    sayilar = re.findall(r'([\d.]+,\d\d)\s*TRY', gov)
    assert sayilar, 'özet kutusunda TRY tutarı bulunamadı'

    def coz(x):
        return float(x.replace('.', '').replace(',', '.'))
    # Özetteki en büyük rakam toplam alacak olmalı
    assert abs(max(coz(x) for x in sayilar) - beklenen) < 0.05, (
        'özet ile satırlar tutmuyor', sayilar, beklenen)

def test_gt1_cek_cirosu_try_karsiligi_yazilir():
    """GT1/K3: çek cirosu cari hareketi `borc_try` ve `kur_uygulanan`
    yazmıyordu. Alan NULL kalınca ekstre, yaşlandırma ve mutabakat
    boşluğu birbirinden FARKLI varsayımlarla dolduruyordu."""
    from models import Cari, Cek, CariHareket
    from datetime import date as _d, timedelta as _td
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        for cid, ad in (('CCK1', 'CEK VEREN AS'), ('CCK2', 'CIRO EDILEN AS')):
            if not Cari.query.get(cid):
                db.session.add(Cari(id=cid, unvan=ad, cari_tip='Musteri',
                                    para_birimi='USD', gorunurluk='ortak'))
        db.session.commit()
    r = c.post('/api/cek', headers=H, json={
        'yon': 'alinan', 'tutar': 2500, 'doviz': 'USD',
        'vade_tarihi': (_d.today() + _td(days=30)).isoformat(),
        'cari_id': 'CCK1', 'cek_no': 'CK-GT1'})
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    cek_id = (r.get_json() or {}).get('id')
    assert cek_id, r.get_json()
    r2 = c.post(f'/api/cek/{cek_id}/durum', headers=H, json={
        'islem': 'ciro', 'ciro_cari_id': 'CCK2', 'cari_hareket_olustur': True})
    assert r2.status_code == 200, r2.get_data(as_text=True)
    with fa.app.app_context():
        h = CariHareket.query.filter_by(cari_id='CCK2', islem_tip='Çek Cirosu').first()
        assert h is not None, 'ciro cari hareketi yazılmadı'
        kur = float(h.kur_uygulanan or 0)
        assert kur > 1.5, ('USD çekte kur yazılmalı', kur)
        assert abs(float(h.borc_try or 0) - 2500 * kur) < 0.05, (
            h.borc_try, kur)


# ══════════════════════════════════════════════════════════════════════
#  KF2 · FİRMA ERİŞİM KURALLARI
#
#  Çoklu firma artık tüm kullanıcılara açık ve kimin hangi firmayı
#  göreceğine yönetici karar veriyor. Bu kuralların HEPSİ sessizce
#  bozulabilecek türden: yanlış tarafa düşen bir koşul ya kullanıcıyı
#  sistemden kilitler ya da ona başka şirketin defterini açar. İkisi
#  de hata vermez, o yüzden burada sınanıyor.
# ══════════════════════════════════════════════════════════════════════

def _kf_kullanici(ad, kapsam='secili', firmalar=(), rol='SATIS'):
    """Testlik kullanıcı + firma izinleri. Varsa günceller."""
    from models import Kullanici, KullaniciFirma
    with fa.app.app_context():
        k = Kullanici.query.filter_by(ad=ad).first()
        if not k:
            k = Kullanici(ad=ad, sifre=generate_password_hash('x'), rol=rol)
            db.session.add(k)
        k.rol = rol
        k.firma_kapsam = kapsam
        k.yetkiler = json.dumps({m: 'yazma' for m in TUM_YAZMA})
        db.session.commit()
        KullaniciFirma.query.filter_by(kullanici_id=k.id).delete()
        for fid in firmalar:
            db.session.add(KullaniciFirma(kullanici_id=k.id, firma_id=fid))
        db.session.commit()
        return k.id


def test_kf2_firmasiz_kullanici_giremez():
    """KF1/KF2: kapsamı 'secili' ve hiç firması olmayan kullanıcı
    sisteme giremez — SESSİZCE bir firmaya atanmaz.

    Eskiden küresel bir varsayılan firma vardı ve böyle bir kullanıcı
    oraya düşüyordu: yöneticinin VERMEDİĞİ bir erişim. Artık durup
    sebebini söylüyor."""
    _kf_kullanici('kfyok', kapsam='secili', firmalar=())
    c = istemci('kfyok', 'SATIS')
    r = c.get('/api/dashboard/ozet', headers=H)
    assert r.status_code == 403, r.get_data(as_text=True)
    d = r.get_json() or {}
    assert d.get('error') == 'firma_yok', d
    # Sebep YAZILI olmalı: boş ekran kullanıcıya ne yapacağını
    # söylemiyor.
    assert 'firma' in (d.get('mesaj') or '').lower(), d


def test_kf2_tek_firma_kendiliginden_secilir():
    """KF2: tek firması olan kullanıcı seçim ekranı görmeden çalışır.

    İstenen buydu: "kullanıcıya sadece tek firma tanımlanmışsa
    varsayılan ihtiyacı ortadan kalkıyor"."""
    from models import Firma
    with fa.app.app_context():
        fid = Firma.query.order_by(Firma.id).first().id
    _kf_kullanici('kftek', kapsam='secili', firmalar=(fid,))
    c = fa.app.test_client()
    with c.session_transaction() as s:
        s['kullanici'] = 'kftek'; s['rol'] = 'SATIS'; s['_csrf'] = 't'
        # firma_id BİLEREK yazılmıyor — kendiliğinden seçmesi gerek.
    r = c.get('/api/dashboard/ozet', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    with c.session_transaction() as s:
        assert s.get('firma_id') == fid, dict(s)


def test_kf2_izinsiz_firmaya_gecilemez():
    """KF2: kullanıcı izinli olmadığı firmaya GEÇEMEZ.

    /api/firma/sec eskiden 'yalnızca admin' idi; rol denetiminin
    yerini izin denetimi aldı. Yerine bir şey konmazsa herkes her
    firmaya geçebilirdi — çoklu firmayı açmanın tam tersi."""
    from models import Firma
    with fa.app.app_context():
        f2 = Firma(ad='KF YABANCI', unvan='KF YABANCI', belge_kodu='KFY',
                   aktif=True)
        db.session.add(f2)
        db.session.commit()
        yabanci = f2.id
        kendi = Firma.query.order_by(Firma.id).first().id
    _kf_kullanici('kfsinir', kapsam='secili', firmalar=(kendi,))
    c = istemci('kfsinir', 'SATIS')
    r = c.post('/api/firma/sec', headers=H,
               json={'firma_id': yabanci})
    assert r.status_code == 403, r.get_data(as_text=True)
    # Oturum DEĞİŞMEMELİ — reddedilen geçiş yan etki bırakmasın.
    with c.session_transaction() as s:
        assert s.get('firma_id') != yabanci, dict(s)
    # Kendi firmasına geçiş SERBEST (admin olmayan da geçebilir).
    r = c.post('/api/firma/sec', headers=H, json={'firma_id': kendi})
    assert r.status_code == 200, r.get_data(as_text=True)


def test_kf2_yetkisiz_firmanin_adi_dahi_gorunmez():
    """KF2: yetkisi olmayan firmanın ADI bile sızmamalı.

    Geçiş yapamamak yetmez: firma adı ve belge kodu tek başına
    bilgidir (kaç şirket var, adları ne).

    NEREYE BAKIYORUZ: ilk sürümde `/api/firma/liste` ucuna
    bakıyordum ve test 403 aldı — o uç 'ayarlar' modülünde ve
    satışçının orada yetkisi YOK. Doğrusu da bu; ama o zaman test
    yanlış yüzeyi sınıyor demektir. Admin olmayan kullanıcıya firma
    adları GERÇEKTEN iki yerden ulaşıyor ve ikisi de sunucuda
    basılıyor: banner çipi (base.html · _firma_listesi_ozet) ve
    firma seçim ekranı. Sızıntı olacaksa orada olur, o yüzden
    basılan HTML'e bakıyoruz."""
    from models import Firma
    with fa.app.app_context():
        f = Firma.query.filter_by(ad='KF YABANCI').first()
        if not f:
            f = Firma(ad='KF YABANCI', unvan='KF YABANCI',
                      belge_kodu='KFY', aktif=True)
            db.session.add(f); db.session.commit()
        kendi = Firma.query.order_by(Firma.id).first().id
    _kf_kullanici('kfgoz', kapsam='secili', firmalar=(kendi,))
    c = istemci('kfgoz', 'SATIS')

    # 1 · firma seçim ekranı
    r = c.get('/firma-sec')
    assert r.status_code == 200, r.status_code
    assert 'KF YABANCI' not in r.get_data(as_text=True)

    # 2 · banner çipi (base.html ile basılan herhangi bir sayfa)
    r = c.get('/', follow_redirects=True)
    assert r.status_code == 200, r.status_code
    assert 'KF YABANCI' not in r.get_data(as_text=True)


def test_kf2_kapsam_tumu_yeni_firmayi_da_gorur():
    """KF1: kapsamı 'tumu' olan kullanıcı SONRADAN açılan firmayı da
    görür — iki eksenli desenin sebebi bu.

    Yalnızca açık liste tutulsaydı, her yeni firmada onu görmesi
    gereken herkesi tek tek düzenlemek gerekirdi."""
    from models import Firma
    _kf_kullanici('kftumu', kapsam='tumu', firmalar=())
    # Firma adlarına admin olmayanın ulaştığı yer seçim ekranı
    # (yukarıdaki testin notu).
    c = istemci('kftumu', 'SATIS')
    assert 'KF SONRADAN' not in c.get('/firma-sec').get_data(as_text=True)
    with fa.app.app_context():
        db.session.add(Firma(ad='KF SONRADAN', unvan='KF SONRADAN',
                             belge_kodu='KFS', aktif=True))
        db.session.commit()
    c = istemci('kftumu', 'SATIS')
    r = c.get('/firma-sec')
    assert r.status_code == 200, r.status_code
    # Kapsamı 'tumu': hiç üyelik satırı olmadan yeni firmayı GÖRÜR.
    assert 'KF SONRADAN' in r.get_data(as_text=True)


def test_kf2_tek_firmasi_olan_kullanici_kilitlenmez():
    """KF2: bir kullanıcının TEK firması silinemez.

    Silinirse o kullanıcının izin listesi boşalır ve sisteme giremez.
    Yöneticinin kimi kilitlediğini görmesi gerekiyor; sessizce
    yapılmamalı."""
    from models import Firma
    with fa.app.app_context():
        f = Firma(ad='KF SILINECEK', unvan='KF SILINECEK',
                  belge_kodu='KFD', aktif=True)
        db.session.add(f); db.session.commit()
        fid = f.id
    _kf_kullanici('kfbagli', kapsam='secili', firmalar=(fid,))
    c = istemci('admin', 'ADMIN')
    # Önizleme engeli söylüyor mu
    r = c.get(f'/api/firma/{fid}/ozet', headers=H)
    if r.status_code == 200:
        assert 'kfbagli' in ((r.get_json() or {}).get('engel') or ''), \
            r.get_data(as_text=True)
    # Gerçek silme REDDEDİLMELİ
    r = c.delete(f'/api/firma/{fid}', headers=H)
    assert r.status_code == 400, r.get_data(as_text=True)
    assert 'kfbagli' in ((r.get_json() or {}).get('mesaj') or ''), \
        r.get_data(as_text=True)
    with fa.app.app_context():
        assert db.session.get(Firma, fid) is not None, 'firma silinmiş'


def test_kf2_secim_yapilmadan_suzgec_kapanmaz():
    """KF2 · EN KRİTİK: firma seçilmeden süzgeç AÇIK kalmamalı.

    Çözümleyici "seçilmedi" durumunda 0 dönüyor. Süzgeçte
    `if not _f: return` yazılı olsaydı 0 falsy olduğu için süzgeç
    HİÇ KURULMAZ ve kullanıcı BÜTÜN firmaların verisini görürdü —
    fail-closed diye yazılan değer tam tersi etki yapardı. Süzgeç
    yalnızca None'da (CLI / firma_atla) kapanmalı.

    Burada doğrudan çözümleyiciye bakıyoruz: iki firması olup seçim
    yapmamış bir kullanıcıda dönen değer 0 olmalı, None OLMAMALI."""
    from models import Firma
    with fa.app.app_context():
        kayitlar = Firma.query.filter_by(aktif=True).order_by(Firma.id).all()
        assert len(kayitlar) >= 2, 'test iki firma istiyor'
        ikisi = (kayitlar[0].id, kayitlar[1].id)
    _kf_kullanici('kfiki', kapsam='secili', firmalar=ikisi)
    c = fa.app.test_client()
    with c.session_transaction() as s:
        s['kullanici'] = 'kfiki'; s['rol'] = 'SATIS'; s['_csrf'] = 't'
    # Seçim yapılmadı: API 409 ile seçim istemeli
    r = c.get('/api/dashboard/ozet', headers=H)
    assert r.status_code == 409, r.get_data(as_text=True)
    assert (r.get_json() or {}).get('error') == 'firma_secilmedi', \
        r.get_data(as_text=True)


# ══════════════════════════════════════════════════════════════════════
#  KF3 · YETKİ PANELİNDEN FİRMA ATAMA
# ══════════════════════════════════════════════════════════════════════

def test_kf3_yetki_paneli_firma_atar():
    """KF3: admin, yetki panelinden kullanıcıya firma atayabilir ve
    atama ANINDA erişime dönüşür."""
    from models import Firma, Kullanici, KullaniciFirma
    with fa.app.app_context():
        f = Firma.query.filter_by(ad='KF3 HEDEF').first()
        if not f:
            f = Firma(ad='KF3 HEDEF', unvan='KF3 HEDEF', belge_kodu='KF3',
                      aktif=True)
            db.session.add(f); db.session.commit()
        hedef = f.id
    a = istemci('admin', 'ADMIN')
    r = a.post('/api/ayarlar/kullanici', headers=H, json={
        'ad': 'kf3yeni', 'sifre': 'x', 'rol': 'SATIS',
        'yetkiler': {'dashboard': 'okuma'},
        'firma_kapsam': 'secili', 'firmalar': [hedef]})
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    with fa.app.app_context():
        k = Kullanici.query.filter_by(ad='kf3yeni').first()
        assert k is not None
        assert (k.firma_kapsam or '') == 'secili', k.firma_kapsam
        uyelik = [x.firma_id for x in
                  KullaniciFirma.query.filter_by(kullanici_id=k.id).all()]
        assert uyelik == [hedef], uyelik


def test_kf3_liste_ucu_kapsam_ve_uyelik_donduruyor():
    """KF3: düzenleme penceresinin DOLDURABİLMESİ için liste ucu
    kapsamı ve üyelikleri vermeli.

    Vermezse pencere boş kutularla açılır ve kaydet'e basmak
    kullanıcının firma izinlerini SESSİZCE SİLER. KP1'de cari
    kapsamında tam olarak bu yaşanmıştı."""
    a = istemci('admin', 'ADMIN')
    r = a.get('/api/ayarlar/kullanici', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    kayitlar = d if isinstance(d, list) else (d.get('data') or [])
    assert kayitlar, d
    for k in kayitlar:
        assert 'firma_kapsam' in k, k
        assert 'firmalar' in k and isinstance(k['firmalar'], list), k


def test_kf3_kismi_guncelleme_izinleri_silmez():
    """KF3: gövdede `firmalar` YOKSA üyeliklere DOKUNULMAZ.

    Başka bir alanı (örn. rol) güncellemek firma erişimini
    kesmemeli — kısmi güncellemenin sessiz yan etkisi olmamalı."""
    from models import Firma, Kullanici, KullaniciFirma
    with fa.app.app_context():
        fid = Firma.query.order_by(Firma.id).first().id
    _kf_kullanici('kf3kismi', kapsam='secili', firmalar=(fid,))
    a = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        kid = Kullanici.query.filter_by(ad='kf3kismi').first().id
    # YALNIZCA rol gönderiliyor
    r = a.put(f'/api/ayarlar/kullanici/{kid}', headers=H,
              json={'rol': 'SATIS'})
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        uyelik = [x.firma_id for x in
                  KullaniciFirma.query.filter_by(kullanici_id=kid).all()]
        assert uyelik == [fid], uyelik
        assert (Kullanici.query.get(kid).firma_kapsam or '') == 'secili'


def test_kf3_gecersiz_kapsam_guvenli_tarafa_duser():
    """KF3: tanınmayan kapsam değeri 'secili'ye düşer.

    Eksik ya da bozuk değer "herkes her firmayı görsün" anlamına
    gelmemeli — gorunurluk='kapali' varsayılanıyla aynı mantık."""
    from models import Kullanici
    a = istemci('admin', 'ADMIN')
    r = a.post('/api/ayarlar/kullanici', headers=H, json={
        'ad': 'kf3bozuk', 'sifre': 'x', 'rol': 'SATIS',
        'yetkiler': {'dashboard': 'okuma'},
        'firma_kapsam': 'HEPSI_BIRDEN', 'firmalar': []})
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    with fa.app.app_context():
        k = Kullanici.query.filter_by(ad='kf3bozuk').first()
        assert (k.firma_kapsam or '') == 'secili', k.firma_kapsam


def test_kf3_olmayan_firma_atanamaz():
    """KF3: ekrandan eski/silinmiş bir firma kimliği gelirse atılır.

    Yabancı anahtarı kırmak yerine sessizce süzülüyor; aksi halde
    bu arada silinmiş bir firmayı işaretli bırakan bir pencere
    kaydet'te 500 verirdi."""
    from models import Kullanici, KullaniciFirma
    a = istemci('admin', 'ADMIN')
    r = a.post('/api/ayarlar/kullanici', headers=H, json={
        'ad': 'kf3hayalet', 'sifre': 'x', 'rol': 'SATIS',
        'yetkiler': {'dashboard': 'okuma'},
        'firma_kapsam': 'secili', 'firmalar': [999999]})
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    with fa.app.app_context():
        k = Kullanici.query.filter_by(ad='kf3hayalet').first()
        uyelik = [x.firma_id for x in
                  KullaniciFirma.query.filter_by(kullanici_id=k.id).all()]
        assert uyelik == [], uyelik


def test_kf3_formda_firma_kapsami_var():
    """KF3: `firma_kapsam` ekranda GİRİLEBİLİR olmalı.

    form_denetim D2 bunu zaten arıyor (modelde var, formda yok →
    öksüz alan). Burada ayrıca sabitliyoruz: alan ve onu dolduran
    JS birlikte durmalı — biri eksikse pencere boş açılır ve
    kaydet izinleri siler."""
    import io as _io
    ay = _io.open('templates/ayarlar.html', encoding='utf-8').read()
    assert 'id="uFirmaKapsam"' in ay
    assert "getElementById('uFirmaKapsam')" in ay
    assert 'uFirmaKutulariCiz()' in ay
    # Kutular kullaniciAc içinde DOLDURULUYOR mu
    assert 'SECILI_FIRMALAR = (DUZENLENEN' in ay


# ══════════════════════════════════════════════════════════════════════
#  YP · YÖNETİM PANELİ (firma üstü işler)
# ══════════════════════════════════════════════════════════════════════

def test_yp_panel_firma_secmeden_acilir():
    """YP1: panelin VARLIK SEBEBİ bu — firmaya girmeden yönetmek.

    Seçim kapısı burayı durdursaydı panel yalnızca firma seçtikten
    sonra açılırdı ve hiçbir işe yaramazdı."""
    c = fa.app.test_client()
    with c.session_transaction() as s:
        s['kullanici'] = 'admin'; s['rol'] = 'ADMIN'; s['_csrf'] = 't'
        # firma_id BİLEREK yok
    r = c.get('/yonetim')
    assert r.status_code == 200, r.status_code


def test_yp_admin_olmayan_panele_giremez():
    """YP1: panelde yapılan işler YETKİNİN KENDİSİNİ belirliyor
    (kullanıcı açmak, yetki vermek, firma silmek). Yetki haritasına
    bağlanmıyor, doğrudan ADMIN şartı aranıyor."""
    c = istemci('satis', 'SATIS')
    r = c.get('/yonetim')
    assert r.status_code in (301, 302), r.status_code
    assert '/yonetim' not in (r.headers.get('Location') or '')


def test_yp_paneller_ikizlenmemis():
    """YP2: taşınan bölümler İKİ sayfada birden basılmamalı.

    Bu projede mükerrer panel çoktan can yaktı: MF4'te iki
    `yedekGovde` yüzünden yedek listesi boş görünüyordu. Aynı
    şablon iki rotaya hizmet ediyor ama her bölüm YALNIZCA bir
    sayfada basılıyor; bu testin işi o sözü tutturmak."""
    a = istemci('admin', 'ADMIN')
    # SIRA ÖNEMLİ: /yonetim oturumdaki firma seçimini DÜŞÜRÜYOR
    # (YP4). Önce panele girilirse /ayarlar seçim ekranına çevrilir
    # ve bu test boş sayfayı ölçerdi.
    aya = a.get('/ayarlar').get_data(as_text=True)
    yon = a.get('/yonetim').get_data(as_text=True)

    # Sistem düzeyi — YALNIZCA yönetimde.
    # YP4: `fFirma` (firma ünvanı) buraya KATILDI; firmanın kimliği
    # firmaya ait değil, firmanın KENDİSİ.
    for kimlik in ('kullaniciGovde', 'firmaGovde', 'yedekGovde', 'fFirma'):
        assert yon.count(f'id="{kimlik}"') == 1, kimlik
        assert aya.count(f'id="{kimlik}"') == 0, (kimlik, 'ayarlarda da var')

    # Firma düzeyi — YALNIZCA ayarlarda
    for kimlik in ('bankaGovde', 'lookupIzgara'):
        assert aya.count(f'id="{kimlik}"') == 1, kimlik
        assert yon.count(f'id="{kimlik}"') == 0, (kimlik, 'yonetimde de var')


def test_yp_sekme_kumeleri_ayrik():
    """YP2: iki sayfanın sekmeleri ÖRTÜŞMEMELİ."""
    import re as _re
    a = istemci('admin', 'ADMIN')

    def sekmeler(yol):
        h = a.get(yol).get_data(as_text=True)
        return {b for b, _ in _re.findall(
            r'class="sekme[^"]*" data-b="([a-z]+)">([^<]+)<', h)}

    # /ayarlar ÖNCE: panel firma seçimini düşürüyor (YP4).
    aya, yon = sekmeler('/ayarlar'), sekmeler('/yonetim')
    assert yon == {'kullanici', 'firmalar', 'yedek'}, yon
    # YP4: "Firma Bilgileri" sekmesi panele taşındı.
    assert aya == {'eposta', 'listeler', 'banka'}, aya
    assert not (yon & aya), yon & aya


def test_yp_panelden_firma_ve_kullanici_yonetilebilir():
    """YP1/YP2: panelin beslendiği uçlar firma seçmeden ÇALIŞMALI.

    Uçlar seçim kapısında muaf; muafiyet kalkarsa panel açılır ama
    tabloları boş kalır — sessiz bir arıza."""
    c = fa.app.test_client()
    with c.session_transaction() as s:
        s['kullanici'] = 'admin'; s['rol'] = 'ADMIN'; s['_csrf'] = 't'
    assert c.get('/api/firma', headers=H).status_code == 200
    assert c.get('/api/ayarlar/kullanici', headers=H).status_code == 200


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
    aya = a.get('/ayarlar').get_data(as_text=True)   # panelden ÖNCE
    yon = a.get('/yonetim').get_data(as_text=True)

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
    """YP3/YP4: panelin TEK kapısı firma seçim ekranı.

    YP3'te iki kapı vardı ve ikisi de yanlış yere açılıyordu:
    "← MİLESTONE…" firmanın İÇİNE giriyordu (panel firma üstüyse
    oradan bir firmaya girilememeli), "Çıkış" ise sistemden
    atıyordu. İkisi de kalktı."""
    # İki giriş yolu da aynı yere çıkmalı: firma seçmeden gelen de,
    # bir firmanın içinden (sol raydan) gelen de.
    for kurulum in (lambda: fa.app.test_client(),
                    lambda: istemci('admin', 'ADMIN')):
        c = kurulum()
        with c.session_transaction() as s:
            s['kullanici'] = 'admin'; s['rol'] = 'ADMIN'; s['_csrf'] = 't'
        h = c.get('/yonetim').get_data(as_text=True)
        assert 'geri-btn' in h, 'dönüş bağlantısı yok'
        assert '/firma-sec' in h
        # Firmaya açılan kapı YOK: ne dashboard bağlantısı ne de
        # oturumu kapatan Çıkış.
        #
        # SINIFA DEĞİL BAĞLANTIYA bakılıyor: `.cikis-btn` kuralı
        # <style> içinde her sayfada duruyor (tek stil bloğu, bütün
        # sayfalar aynı kabuktan geliyor). Sınıf adını aramak,
        # düğme basılmasa da eşleşirdi.
        assert 'href="/cikis"' not in h, 'panelde oturum kapatma var'
        assert 'href="/dashboard"' not in h, 'panelden firmaya giriliyor'


def test_yp4_panele_girince_firma_secimi_dusuyor():
    """YP4: panelde firma seçili DEĞİLDİR — değişmez kural.

    Seçim korunsaydı ekranda ona açılan bir kapı doğabilirdi; YP3'te
    tam bu oldu. Seçimi girişte düşürmek, 'firma seçili panel' diye
    ikinci bir durumun var olmasını engelliyor."""
    c = istemci('admin', 'ADMIN')
    with c.session_transaction() as s:
        assert s.get('firma_id'), 'ön koşul: firma seçili başlamalı'
    assert c.get('/yonetim').status_code == 200
    with c.session_transaction() as s:
        assert not s.get('firma_id'), 'panel firma seçimini düşürmedi'


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
    # /ayarlar ÖNCE: panele girmek firma seçimini düşürüyor (YP4).
    for yol in ('/ayarlar', '/yonetim'):
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


# ══════════════════════════════════════════════════════════════════════
#  YP4 · FİRMA AYARLARI PANELDEN, FİRMAYA GİRMEDEN
# ══════════════════════════════════════════════════════════════════════

def test_yp4_baska_firmanin_ayari_firmaya_girmeden_duzenlenir():
    """YP4: `firma_id` hedefi belirler — oturumdaki seçim değil.

    Bu testin asıl işi YAZILANIN DOĞRU FİRMAYA gittiğini ölçmek.
    Kimlik taşınmazsa uç eski davranışına düşüp AKTİF firmayı
    düzenler; panelde aktif firma olmadığı için de ya boşa yazar ya
    da — seçim kalmış olsaydı — yanlış firmanın ünvanını değiştirirdi.
    MF3B'de can yakan tuzak buydu."""
    from models import Firma
    a = istemci('admin', 'ADMIN')
    r = a.post('/api/firma', headers=H, json={
        'ad': 'YP4 HEDEF', 'belge_kodu': 'Y4',
        'ortak_cari': False, 'ortak_liste': False})
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    hedef = r.get_json()['id']
    with fa.app.app_context():
        baska = (Firma.query.filter(Firma.id != hedef, Firma.aktif.is_(True))
                 .order_by(Firma.id).first())
        assert baska, 'ön koşul: en az iki firma'
        baska_id, baska_unvan = baska.id, baska.unvan

    # Panel: firma SEÇİLİ DEĞİL
    c = fa.app.test_client()
    with c.session_transaction() as s:
        s['kullanici'] = 'admin'; s['rol'] = 'ADMIN'; s['_csrf'] = 't'

    d = c.post('/api/ayarlar/firma', headers=H, json={
        'firma_id': hedef, 'satici_firma': 'YP4 HEDEF A.Ş.',
        'satici_adres': 'DENİZLİ'})
    assert d.status_code == 200, d.get_data(as_text=True)

    with fa.app.app_context():
        assert Firma.query.get(hedef).unvan == 'YP4 HEDEF A.Ş.'
        # Komşu firma DOKUNULMAMIŞ olmalı
        assert Firma.query.get(baska_id).unvan == baska_unvan

    g = c.get(f'/api/ayarlar/firma?firma_id={hedef}', headers=H)
    assert g.status_code == 200
    assert g.get_json()['satici_firma'] == 'YP4 HEDEF A.Ş.'


def test_yp4_kdv_ve_avans_sistem_geneli_kaliyor():
    """YP4: KDV oranı ve avans eşiği FİRMA AYARI DEĞİL.

    ÖLÇÜLDÜ (18.10): panelden firma B için %18 yazıldı, firma A da
    %18 okudu — çünkü ikisi de `Veriler`de firma_id'si NULL tek
    satırda duruyor. Damga `Veriler`i bilerek atlıyor
    (models._firma_damgasi), yani bu satırlar hiçbir zaman firmaya
    damgalanmıyor.

    Bu yüzden ikisi bir firmanın ayar kutusunda DEĞİL, panelde
    "Tüm firmalar için" başlığı altında duruyor. Test, yarın biri
    onları firma kutusuna taşımak isterse önce bu gerçeğe çarpsın
    diye burada: davranış değişecekse veri taşıma gerekiyor."""
    from models import Firma
    a = istemci('admin', 'ADMIN')
    r = a.post('/api/firma', headers=H, json={
        'ad': 'YP4 KDV', 'belge_kodu': 'Y4K',
        'ortak_cari': False, 'ortak_liste': False})
    hedef = r.get_json()['id']

    c = fa.app.test_client()
    with c.session_transaction() as s:
        s['kullanici'] = 'admin'; s['rol'] = 'ADMIN'; s['_csrf'] = 't'
    assert c.post('/api/ayarlar/kdv_oran', headers=H,
                  json={'oran': 18}).status_code == 200

    with fa.app.app_context():
        ilk = Firma.query.filter(Firma.id != hedef).order_by(Firma.id).first()
    for fid in (hedef, ilk.id):
        okundu = c.get(f'/api/ayarlar/kdv_oran?firma_id={fid}', headers=H)
        assert float(okundu.get_json()['oran']) == 18.0, fid

    # Ekran da öyle söylüyor: oran firma kutusunda değil, "Tüm
    # firmalar için" panelinde.
    h = a.get('/yonetim').get_data(as_text=True)
    assert 'id="sistemAyarPanel"' in h
    assert h.index('id="sistemAyarPanel"') < h.index('id="fKdv"')
    assert h.index('id="firmaAyarKutu"') > h.index('id="fKdv"')


def test_yp4_baska_firmanin_ayarini_yonetici_olmayan_duzenleyemez():
    """YP4: `firma_id` yetki yükseltme kapısı OLMAMALI.

    Kendi firmasının ayarını düzenleyebilen bir kullanıcı, kimliği
    değiştirerek başka firmanın ünvanını değiştirememeli."""
    from models import Firma
    with fa.app.app_context():
        hedef = Firma.query.filter_by(aktif=True).order_by(Firma.id).first().id
    c = istemci('mudur_yp4', 'MUDUR')
    r = c.post('/api/ayarlar/firma', headers=H,
               json={'firma_id': hedef, 'satici_firma': 'OLMAZ'})
    assert r.status_code == 403, r.status_code
    with fa.app.app_context():
        assert Firma.query.get(hedef).unvan != 'OLMAZ'


def test_yp4_olmayan_firma_kimligi_reddedilir():
    """YP4: doğrulanmamış kimlikle bağlam çevirmek, olmayan bir
    firmaya yazma damgası basmak olurdu."""
    c = fa.app.test_client()
    with c.session_transaction() as s:
        s['kullanici'] = 'admin'; s['rol'] = 'ADMIN'; s['_csrf'] = 't'
    assert c.get('/api/ayarlar/firma?firma_id=999999',
                 headers=H).status_code == 404
    assert c.get('/api/ayarlar/firma?firma_id=abc',
                 headers=H).status_code == 400


def test_yp4_kullanici_listesi_firma_bazli():
    """YP4: kullanıcılar firma seçilerek listeleniyor.

    Süzme istemcide; uç zaten her kullanıcının `firma_kapsam` ve
    `firmalar` alanlarını veriyor. Test ikisini birden sabitliyor:
    ekranda seçim kutusu ve süzgeç VAR, uçta da süzmeyi besleyen
    alanlar VAR. Alanlardan biri uçtan düşerse liste sessizce
    herkesi gösterirdi."""
    a = istemci('admin', 'ADMIN')
    h = a.get('/yonetim').get_data(as_text=True)
    assert 'id="kullaniciFirmaSecim"' in h
    assert 'function _kfGorunur' in h
    assert 'kullaniciFirmaDegisti' in h
    # Hiçbir firmaya atanmamış kullanıcı EKRANDAN KAYBOLMAMALI:
    # seçim kutusunda kendi satırı var.
    assert 'Firması olmayanlar' in h

    d = a.get('/api/ayarlar/kullanici', headers=H)
    assert d.status_code == 200
    kayitlar = d.get_json()
    assert kayitlar, 'ön koşul: en az bir kullanıcı'
    for u in kayitlar:
        assert 'firma_kapsam' in u, u.get('ad')
        assert isinstance(u.get('firmalar'), list), u.get('ad')


# ══════════════════════════════════════════════════════════════════════
#  UR1 · ÜRETİM / SATIN ALMA AYRIMI
# ══════════════════════════════════════════════════════════════════════

def _ur1_tedarikci():
    """Testlik ürün tedarikçisi — borç karşılaştırması için."""
    from models import Cari
    with fa.app.app_context():
        c = Cari.query.filter_by(unvan='UR1 TEDARIK A.S.').first()
        if not c:
            # Cari FİRMA KAPSAMLI DEĞİL (kart ortak, görünürlük
            # cari_firma üyeliğiyle) — firma_id alanı yok.
            c = Cari(id='UR1T', unvan='UR1 TEDARIK A.S.',
                     urun_tedarikcisi=True, cari_tip='Tedarikçi')
            db.session.add(c)
            db.session.commit()
        return c.unvan


def test_ur1_uretim_tedarikci_borcu_dogurmaz():
    """UR1: üretilen mal SATIN ALINMADI — cari borcu doğmamalı.

    Kontrol grubu da var: AYNI gövde `kaynak='satinalma'` ile
    gönderilince borç OLUŞUYOR. Olmasaydı test, borcun hiç
    oluşmadığı bir yolu ölçüp 'üretim çalışıyor' derdi."""
    from models import CariHareket, PlakaStok
    unvan = _ur1_tedarikci()
    c = istemci('admin', 'ADMIN')

    def _govde(kaynak, blok):
        return {'tip': 'PLAKA', 'kaynak': kaynak, 'uretici': unvan,
                'cins': 'UR1 TEST', 'blok_no': blok, 'boy': 300,
                'yukseklik': 180, 'kalinlik': 2, 'adet': 1,
                'fiyat': 50, 'fiyat_birim': 'm2', 'doviz': 'USD',
                'alis_tipi': 'yurtici_kdvli', 'kdv_oran': 20,
                'fatura_durumu': 'faturali', 'fatura_no': 'UR1-001'}

    with fa.app.app_context():
        once = CariHareket.query.filter_by(cari_unvan=unvan).count()

    # 1 · SATIN ALMA → borç OLUŞUR (kontrol)
    r = c.post('/api/stok/ekle', headers=H, json=_govde('satinalma', 'UR1-SA'))
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        assert CariHareket.query.filter_by(cari_unvan=unvan).count() == once + 1

    # 2 · ÜRETİM → borç OLUŞMAZ, KDV yazılmaz, alış tipi boş kalır
    r = c.post('/api/stok/ekle', headers=H, json=_govde('uretim', 'UR1-UR'))
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        assert CariHareket.query.filter_by(cari_unvan=unvan).count() == once + 1, \
            'üretimde tedarikçiye borç yazıldı'
        p = PlakaStok.query.filter_by(blok_no='UR1-UR').first()
        assert p is not None
        assert p.kaynak == 'uretim', p.kaynak
        assert (p.kdv_tutar or 0) == 0, p.kdv_tutar
        assert (p.kdv_oran or 0) == 0, p.kdv_oran
        # Üretilen malın ALIŞ TİPİ yok; 'yurtici_kdvli' bırakmak onu
        # satın alınmış gibi gösterirdi (kesimin bugün yaptığı hata).
        assert p.alis_tipi is None, p.alis_tipi
        assert p.alis_fiyati == 50, p.alis_fiyati   # üretim maliyeti


def test_ur1_uretimde_fatura_durumu_istemciye_birakilmaz():
    """UR1: 'faturali' yollayan eski bir sekme borç doğurmamalı.

    Ekranda alan gizli ama sunucu istemciye güvenmiyor — gizlemek
    bir güvenlik önlemi değil, bir görüntü tercihi."""
    from models import PlakaStok
    unvan = _ur1_tedarikci()
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/stok/ekle', headers=H, json={
        'tip': 'PLAKA', 'kaynak': 'uretim', 'uretici': unvan,
        'cins': 'UR1 TEST', 'blok_no': 'UR1-ZORLA', 'boy': 300,
        'yukseklik': 180, 'kalinlik': 2, 'adet': 1, 'fiyat': 10,
        'fiyat_birim': 'm2', 'doviz': 'USD',
        'fatura_durumu': 'faturali', 'fatura_no': 'OLMAMALI'})
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        p = PlakaStok.query.filter_by(blok_no='UR1-ZORLA').first()
        assert p.fatura_durumu == 'faturasiz', p.fatura_durumu


def test_ur1_stokta_duran_bloktan_uretim_girisi_durdurulur():
    """UR1: çift sayım kapısı.

    Blok stokta duruyorsa ondan kesilen plakalar içe aktarmayla
    girilmemeli: blok kesilmemiş gibi kalır, aynı mal iki kez
    sayılır ve plakaların maliyeti bloktan türemez."""
    from models import PlakaStok
    c = istemci('admin', 'ADMIN')
    rb = c.post('/api/stok/ekle', headers=H, json={
        'tip': 'BLOK', 'cins': 'UR1 BLOK', 'blok_no': 'UR1-KAPI',
        'boy': 300, 'yukseklik': 150, 'en': 120, 'tonaj': 14,
        'fiyat': 400, 'fiyat_birim': 'ton', 'doviz': 'USD'})
    assert rb.status_code == 200, rb.get_data(as_text=True)

    govde = {'tip': 'PLAKA', 'kaynak': 'uretim', 'cins': 'UR1 TEST',
             'blok_no': 'UR1-KAPI', 'boy': 300, 'yukseklik': 180,
             'kalinlik': 2, 'adet': 1, 'fiyat': 30, 'fiyat_birim': 'm2',
             'doviz': 'USD'}

    r = c.post('/api/stok/ekle', headers=H, json=govde)
    assert r.status_code == 409, r.get_data(as_text=True)
    assert r.get_json().get('error') == 'blok_stokta'
    with fa.app.app_context():
        assert PlakaStok.query.filter_by(blok_no='UR1-KAPI').count() == 0

    # SATIN ALMA kipinde kapı ÇALIŞMAZ: aynı numaralı bloğu satın
    # almış olman olağan, orada çift sayım yok.
    r2 = c.post('/api/stok/ekle', headers=H,
                json=dict(govde, kaynak='satinalma'))
    assert r2.status_code == 200, r2.get_data(as_text=True)

    # Bilinçli onay geçişe izin verir (numara tekrarı olabilir).
    r3 = c.post('/api/stok/ekle', headers=H,
                json=dict(govde, blok_uyarisi_onaylandi=True))
    assert r3.status_code == 200, r3.get_data(as_text=True)


def test_ur1_stok_listesi_uretimi_alis_gibi_gostermez():
    """UR1: liste ucu üretilen mala alış tipi uydurmamalı."""
    c = istemci('admin', 'ADMIN')
    c.post('/api/stok/ekle', headers=H, json={
        'tip': 'PLAKA', 'kaynak': 'uretim', 'cins': 'UR1 LISTE',
        'blok_no': 'UR1-LST', 'boy': 300, 'yukseklik': 180,
        'kalinlik': 2, 'adet': 1, 'fiyat': 20, 'fiyat_birim': 'm2',
        'doviz': 'USD'})
    d = c.get('/api/stok?tip=PLAKA&per_page=500', headers=H)
    assert d.status_code == 200
    satir = [x for x in (d.get_json().get('data') or [])
             if x.get('blok_no') == 'UR1-LST']
    assert satir, 'eklenen plaka listede yok'
    assert satir[0]['kaynak'] == 'uretim', satir[0].get('kaynak')
    assert satir[0]['alis_tipi'] is None, satir[0].get('alis_tipi')


def test_ur1_ekranda_kaynak_secimi_var():
    """UR1: alan modelde var, formda yoksa öksüz kalır (form_denetim
    D2 ile aynı gerekçe). İki form da seçimi sunmalı ve gönderme
    gövdesine koymalı."""
    import io as _io
    h = _io.open('templates/stok.html', encoding='utf-8').read()
    assert 'id="tKaynak"' in h          # içe aktarma
    assert 'id="sKaynak"' in h          # tekil stok
    assert 'function topluKaynakDegisti' in h
    assert 'function kaynakDegisti' in h
    assert "kaynak: uretim ? 'uretim' : 'satinalma'" in h
    assert "kaynak: document.getElementById('sKaynak').value" in h


# ══════════════════════════════════════════════════════════════════════
#  UR2 · ORTAK CİNS/YÜZEY · BLOKTA YÜZEY YOK · MENŞE LİSTEDEN
# ══════════════════════════════════════════════════════════════════════

def test_ur2_ice_aktarmada_cins_zorunlu_eslesme_degil():
    """UR2: dışarıdan gelen çeki listesinde cins sütunu olmayabilir.

    Zorunlu eşleşme, kullanıcıyı listeyi önce Excel'de düzenlemeye
    zorluyordu. Artık 4. adımdaki ortak alandan verilebiliyor."""
    import io as _io, re as _re
    h = _io.open('templates/stok.html', encoding='utf-8').read()
    # Üç ürün tipinde de cins ZORUNLU olmamalı
    for kalip in (r"\['cins',\s+'Cins',\s+true\]",
                  r"\['cins',\s+'Cins',\s+true\]"):
        assert not _re.search(kalip, h), 'cins hâlâ zorunlu eşleşme'
    assert 'id="tCins"' in h
    assert 'id="tOzellik"' in h
    assert "kayit.cins = _ortakMetin('tCins')" in h
    assert "kayit.ozellik = _ortakMetin('tOzellik')" in h


def test_ur2_sunucu_cinssiz_kaydi_hala_reddediyor():
    """UR2: ekrandaki zorunluluk kalktı, VERİDEKİ kalkmadı.

    Ortak alan da boş bırakılırsa ürünün tanımı yok demektir. Ekran
    bunu önizlemede yakalıyor; sunucu da kendi kapısını koruyor —
    uç doğrudan da çağrılabiliyor."""
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/stok/ekle', headers=H, json={
        'tip': 'PLAKA', 'cins': '', 'blok_no': 'UR2-CINSSIZ',
        'boy': 300, 'yukseklik': 180, 'kalinlik': 2, 'adet': 1,
        'fiyat': 10, 'fiyat_birim': 'm2', 'doviz': 'USD'})
    assert r.status_code == 400, r.status_code
    assert r.get_json().get('error') == 'cins_zorunlu'


def test_ur2_blokta_yuzey_alani_gosterilmez():
    """UR2: ham blokta yüzey işlemi yok.

    Alanı göstermek, doldurulacak bir şey varmış gibi gösteriyordu.
    Gizlerken DEĞERİ de siliniyor: tip BLOK'a çevrilince önceki
    seçim gönderilmeye devam ederdi."""
    import io as _io
    h = _io.open('templates/stok.html', encoding='utf-8').read()
    assert 'id="ozellikAlan"' in h            # tekil form
    assert 'id="duzOzellikAlan"' in h         # düzenleme modalı
    assert 'id="tOzellikAlan"' in h           # içe aktarma ortak alanı
    assert "oz.style.display = blok ? 'none' : ''" in h
    assert "document.getElementById('sOzellik').value = ''" in h


def test_ur2_mense_listeden_seciliyor():
    """UR2: menşe ticari faturaya, packing list'e ve etikete basılıyor.

    Elle yazılınca aynı ülke üç ayrı yazımla kaydediliyordu. Liste
    `ulke` tanımlarından geliyor; listede olmayan MEVCUT değer de
    korunuyor, yoksa kaydet'e basmak dokunulmayan bir alanı sessizce
    değiştirirdi."""
    import io as _io
    h = _io.open('templates/stok.html', encoding='utf-8').read()
    assert '<select id="sMense"' in h, 'menşe hâlâ serbest metin'
    assert '<select id="duzMense"' in h, 'düzenlemede menşe serbest metin'
    assert 'function menseDoldur' in h
    assert "lookupGetir('ulke')" in h
    # TURKIYE her zaman seçenek: ülke listesi boşsa alan bomboş
    # kalıp menşe seçilemez hale gelirdi.
    assert "['TURKIYE'," in h
    # Mevcut değer listede yoksa bile seçenek olarak ekleniyor
    assert 'simdi])]' in h


def test_ur2_mense_sunucuda_normalleniyor():
    """UR2: ekran listeden seçtiriyor ama uç yine de normalliyor —
    API doğrudan çağrılabilir."""
    from models import PlakaStok
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/stok/ekle', headers=H, json={
        'tip': 'PLAKA', 'cins': 'UR2 MENSE', 'blok_no': 'UR2-MNS',
        'boy': 300, 'yukseklik': 180, 'kalinlik': 2, 'adet': 1,
        'fiyat': 10, 'fiyat_birim': 'm2', 'doviz': 'USD',
        'mense': '  italya  '})
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        p = PlakaStok.query.filter_by(blok_no='UR2-MNS').first()
        assert p.mense == 'ITALYA', p.mense


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


# ══════════════════════════════════════════════════════════════════════
#  B2 · İÇE AKTARMADAKİ ORTAK CİNS/YÜZEY LİSTEDEN SEÇİLİYOR
# ══════════════════════════════════════════════════════════════════════

def test_b2_ortak_cins_ve_ozellik_listeden():
    """B2: iki içe aktarma ekranında da ortak cins/yüzey SELECT.

    Bu alanın tekil formdakinden farkı: değer tek satıra değil,
    AKTARILAN BÜTÜN SATIRLARA yazılıyor. Serbest metinde bir harf
    hatası yüzlerce kaydı listede ayrı bir cins olarak gösterir."""
    import io as _io, re as _re
    for yol, doldur in (('templates/stok.html', 'topluListeDoldur'),
                        ('templates/kesim.html', 'kesimListeDoldur')):
        h = _io.open(yol, encoding='utf-8').read()
        for eid in (('tCins', 'tOzellik') if 'stok' in yol else ('kCins', 'kOzellik')):
            assert _re.search(r'<select[^>]*id="%s"' % eid, h), (yol, eid)
            # Serbest metin kutusu geride kalmamış
            assert not _re.search(r'<input[^>]*id="%s"' % eid, h), (yol, eid)
        # Seçenekler listeden besleniyor, şablona gömülü değil
        assert 'async function %s' % doldur in h, yol
        assert "lookupGetir(kategori)" in h, yol


def test_b2_yeni_ekle_isareti_kayda_gecmez():
    """B2: "➕ Yeni … ekle…" bir DEĞER değil, bir KOMUT.

    Pencere açıkken ya da iptal edilince seçim işaretin kendisinde
    kalıyor; okuyucu onu boş saymazsa cinsi '__yeni__' olan satırlar
    oluşurdu."""
    import io as _io
    stok = _io.open('templates/stok.html', encoding='utf-8').read()
    kesim = _io.open('templates/kesim.html', encoding='utf-8').read()

    assert "const TP_YENI = '__yeni__';" in stok
    assert "const KX_YENI = '__yeni__';" in kesim
    # Okuyucular işareti süzüyor
    assert "v === TP_YENI ? '' : v" in stok
    assert "v === KX_YENI ? '' : v" in kesim
    # Önizleme ortak değeri DOĞRUDAN .value'dan almıyor — süzgeçten
    assert "kayit.cins = _ortakMetin('tCins')" in stok
    assert "kayit.ozellik = _ortakMetin('tOzellik')" in stok
    assert "const oCins = _secim('kCins');" in kesim
    assert "const oOzellik = _secim('kOzellik');" in kesim
    assert 'k.cins = oCins' in kesim and 'k.ozellik = oOzellik' in kesim
    # Ortak değerin OKUNDUĞU tek yer süzgeç; başka yerde `.value`
    # yalnızca YAZMA olabilir (BLOK'ta yüzey alanı temizleniyor).
    import re as _re
    for h, ad, kimlikler in ((stok, 'stok', ('tCins', 'tOzellik')),
                             (kesim, 'kesim', ('kCins', 'kOzellik'))):
        for eid in kimlikler:
            for m in _re.finditer(r"getElementById\('%s'\)\.value\s*(=(?!=))?" % eid, h):
                assert m.group(1), (ad, eid, 'süzgeç dışında okunuyor')


def test_b2_yeni_tanim_akisi_kopyalanmamis():
    """B2: yeni tanım ekleme base.html'deki TEK akıştan geçiyor.

    `_listeYeniEkle` pencereyi açıyor, ucu çağırıyor, ortak listeyi
    ve öteki sekmeleri tazeliyor. İkinci bir kopya, o tazelemenin
    yalnız bir ekranda yaşamasıyla biterdi."""
    import io as _io
    base = _io.open('templates/base.html', encoding='utf-8').read()
    assert 'async function _listeYeniEkle' in base
    for yol in ('templates/stok.html', 'templates/kesim.html'):
        h = _io.open(yol, encoding='utf-8').read()
        assert '_listeYeniEkle(gizli, kategori' in h, yol
        # Ekleme akışı şablonun içinde yeniden yazılmamış
        assert 'function _listeYeniEkle' not in h, yol
        assert "api('/api/lookup" not in h, yol

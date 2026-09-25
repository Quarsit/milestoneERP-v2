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
    yield


def istemci(ad, rol='SATIS'):
    c = fa.app.test_client()
    with c.session_transaction() as s:
        s['kullanici'] = ad
        s['rol'] = rol
        s['_csrf'] = 't'
    return c


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

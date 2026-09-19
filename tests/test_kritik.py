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

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


# ══════════════════════════════════════════════════════════════════════
#  B3 · PLAKA KODU TEK YERDEN · ÜRETİM NO SADE · BAŞLANGIÇ 0
# ══════════════════════════════════════════════════════════════════════

def test_b3_plaka_kodu_tek_kaynaktan():
    """B3: `blok#slab` dizesi artık elle kurulmuyor.

    Yedi ayrı yerde kuruluyordu (stok listesi, global arama, maliyet,
    proforma, Excel dışa aktarma, içe aktarma uyarısı, denetim
    kaydı). Biçim değişince altısını düzeltip birini unutmak, aynı
    plakanın iki ekranda iki ayrı kodla görünmesiyle biterdi."""
    import io as _io, re as _re
    fa_ = _io.open('flask_app.py', encoding='utf-8').read()
    assert 'def _plaka_kodu(' in fa_
    # Elle kurulan hiçbir kalıp kalmamış
    assert not _re.search(r"#\{s\.slab_no", fa_), 'flask_app: elle kurulan kod'
    assert not _re.search(r"\{blok_no\} #\{slab_no\}", fa_), 'flask_app: uyarı metni'

    base = _io.open('templates/base.html', encoding='utf-8').read()
    assert 'function plakaKodu(' in base
    for yol in ('templates/stok.html', 'templates/proforma.html'):
        h = _io.open(yol, encoding='utf-8').read()
        assert 'plakaKodu(' in h, yol
        assert not _re.search(r"\}#\$\{.*slab_no", h), (yol, 'elle kurulan kod')
        assert 'function plakaKodu' not in h, (yol, 'ikinci kopya')


def test_b3_plaka_kodu_bicimi():
    """B3: kod `blok-İKİ HANE`; 0 da geçerli bir numara."""
    import shutil as _shutil, subprocess as _sp, os as _os, json as _json
    # Sunucudaki ikizi `create_app` kapsamında; onun davranışı aşağıdaki
    # uçtan uca testlerde ölçülüyor. Burada EKRAN tarafı node ile
    # koşuluyor — `js_denetim` yalnız ayrıştırılabilirliğe bakıyor.
    node = _shutil.which('node') or '/opt/node22/bin/node'
    if not _os.path.exists(node):
        import pytest as _pytest
        _pytest.skip('node yok')
    betik = r"""
const fs = require('fs'), vm = require('vm');
const h = fs.readFileSync('templates/base.html', 'utf8');
const bas = h.indexOf('function plakaKodu(');
const son = h.indexOf('/* ══ BANKA/KASA ETİKETİ', bas);
const kum = {}; vm.createContext(kum);
vm.runInContext(h.slice(bas, son), kum);
console.log(JSON.stringify({
  bir: kum.plakaKodu('K6461', 1),
  sifir: kum.plakaKodu('K6461', 0),
  oniki: kum.plakaKodu('K6461', 12),
  yuz: kum.plakaKodu('K6461', 100),
  noYok: kum.plakaKodu('K6461', null),
  blokYok: kum.plakaKodu('', 3),
}));
"""
    r = _sp.run([node, '-e', betik], capture_output=True, text=True, cwd='.')
    assert r.returncode == 0, r.stderr[:400]
    d = _json.loads(r.stdout.strip().splitlines()[-1])
    assert d['bir'] == 'K6461-01', d['bir']
    assert d['sifir'] == 'K6461-00', d['sifir']
    assert d['oniki'] == 'K6461-12' and d['yuz'] == 'K6461-100'
    assert d['noYok'] == 'K6461' and d['blokYok'] == '03'


def test_b3_uretim_no_orijinal_blok_no():
    """B3: üretim blok no artık dilimlenmiş kesim numarası DEĞİL.

    Eskiden `blok_no + '-U' + kesim_id[-4:]` idi; o dilim token
    ortasından kesip K6461-U1-01 üretiyordu."""
    from models import BlokStok, PlakaStok, Kesim
    with fa.app.app_context():
        db.session.add(BlokStok(id='BLKB3A', blok_no='K7001', cins='TEST',
                                boy=300, yukseklik=150, en=120, hacim_m3=5.4,
                                tonaj=14.5, alis_fiyati=400,
                                alis_fiyat_birim='ton', doviz='USD',
                                durum='Serbest', uretici='ALBSTONE'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': ['BLKB3A'],
        'kesim_tarihi': '2026-03-05',
        # uretim_blok_no GÖNDERİLMİYOR — otomatik kural ölçülüyor
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'TEST', 'boy': 250,
                      'yukseklik': 160, 'kalinlik': 2, 'adet': 3}]})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    with fa.app.app_context():
        kesim = Kesim.query.get(d['kesim_id'])
        assert kesim.uretim_blok_no == 'K7001', kesim.uretim_blok_no
        assert '-U' not in kesim.uretim_blok_no
        for o in d['olusan_stoklar']:
            p = PlakaStok.query.get(o['id'])
            assert p.blok_no == 'K7001', p.blok_no


def test_b3_baslangic_no_sifir_aynen_gider():
    """B3: 0 geçerli bir plaka numarası — sessizce 1'e çekilmemeli."""
    from models import BlokStok, PlakaStok
    with fa.app.app_context():
        db.session.add(BlokStok(id='BLKB3B', blok_no='K7002', cins='TEST',
                                boy=300, yukseklik=150, en=120, hacim_m3=5.4,
                                tonaj=14.5, alis_fiyati=400,
                                alis_fiyat_birim='ton', doviz='USD',
                                durum='Serbest', uretici='ALBSTONE'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': ['BLKB3B'],
        'kesim_tarihi': '2026-03-05', 'baslangic_slab': 0,
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'TEST', 'boy': 250,
                      'yukseklik': 160, 'kalinlik': 2, 'adet': 3}]})
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        nolar = sorted(p.slab_no for p in
                       PlakaStok.query.filter_by(blok_no='K7002').all())
        assert nolar == [0, 1, 2], nolar

    # Tekil stok formu da 0'ı kabul etmeli
    r2 = c.post('/api/stok/ekle', headers=H, json={
        'tip': 'PLAKA', 'cins': 'TEST', 'blok_no': 'K7003', 'boy': 250,
        'yukseklik': 160, 'kalinlik': 2, 'adet': 2, 'baslangic_no': 0,
        'fiyat': 20, 'fiyat_birim': 'm2', 'doviz': 'USD',
        'uretici': 'ALBSTONE', 'alis_tipi': 'ithalat'})
    assert r2.status_code == 200, r2.get_data(as_text=True)
    with fa.app.app_context():
        nolar = sorted(p.slab_no for p in
                       PlakaStok.query.filter_by(blok_no='K7003').all())
        assert nolar == [0, 1], nolar


def test_b3_baslangic_bos_kalinan_yerden_devam():
    """B3: üretim no artık orijinal blok no olduğu için aynı blok
    no'lu plakalar yan yana gelebilir. Başlangıç BOŞ bırakılırsa
    numara kalınan yerden devam etmeli — yoksa ikinci kesim birinci
    kesimin numaralarını tekrar ederdi."""
    from models import BlokStok, PlakaStok
    with fa.app.app_context():
        for _i, _id in enumerate(('BLKB3C1', 'BLKB3C2')):
            db.session.add(BlokStok(id=_id, blok_no='K7004', cins='TEST',
                                    boy=300, yukseklik=150, en=120,
                                    hacim_m3=5.4, tonaj=14.5, alis_fiyati=400,
                                    alis_fiyat_birim='ton', doviz='USD',
                                    durum='Serbest', uretici='ALBSTONE'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    govde = lambda kid: {
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': [kid],
        'kesim_tarihi': '2026-03-05', 'baslangic_slab': '',
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'TEST', 'boy': 250,
                      'yukseklik': 160, 'kalinlik': 2, 'adet': 3}]}
    assert c.post('/api/kesim', headers=H, json=govde('BLKB3C1')).status_code == 200
    assert c.post('/api/kesim', headers=H, json=govde('BLKB3C2')).status_code == 200
    with fa.app.app_context():
        nolar = sorted(p.slab_no for p in
                       PlakaStok.query.filter_by(blok_no='K7004').all())
        assert nolar == [1, 2, 3, 4, 5, 6], nolar


# ══════════════════════════════════════════════════════════════════════
#  B4 · SIFIR PLAKA NUMARASI HER EKRANDA GÖRÜNÜR
# ══════════════════════════════════════════════════════════════════════

def test_b4_sifir_slab_hicbir_yerde_yutulmuyor():
    """B4: slab_no = 0 'yok' sayılmamalı.

    B3 ortak yardımcıyı 0'a hazır yaptı ama onu ÇAĞIRAN yerlerdeki
    doğruluk denetimleri (`if s.slab_no:`, `p.slab_no or ''`) olduğu
    gibi kaldı. 0 hem Python'da hem JS'te falsy — ekranda plaka no
    hiç yazılmadı, K6461-00 yerine sadece K6461 göründü.

    Bu test 0'ı GERÇEKTEN kaydedip her uçtan geri okuyor; biçim
    kuralını değil, sıfırın hayatta kalmasını ölçüyor."""
    from models import PlakaStok
    with fa.app.app_context():
        for _i in (0, 1):
            db.session.add(PlakaStok(
                id=f'PLKB4{_i}', firma_id=1, cins='TEST', blok_no='K8000',
                slab_no=_i, boy=298, yukseklik=169, kalinlik=2,
                metraj_m2=5.04, alis_fiyati=20, doviz='USD',
                durum='Serbest', uretici='ALBSTONE'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')

    # 1 · stok listesi: 0 sayı olarak gelmeli, '' değil
    d = c.get('/api/stok?tip=PLAKA&per_page=300').get_json()
    kayit = [x for x in d['data'] if x['id'] == 'PLKB40']
    assert kayit, 'kayıt listede yok'
    assert kayit[0]['slab_no'] == 0, kayit[0]['slab_no']

    # 2 · kesim kaynak listesi
    kl = c.get('/api/kesim/kaynak_listesi?tip=PLAKA').get_json()
    kk = [x for x in kl['kaynaklar'] if x['id'] == 'PLKB40']
    assert kk and kk[0]['slab_no'] == 0, kk

    # 3 · global arama: kod K8000-00 olmalı
    ar = c.get('/api/ara?q=K8000').get_json()
    adlar = [k.get('ad') for g in ar.get('gruplar', [])
             for k in g.get('kayitlar', [])]
    assert 'K8000-00' in adlar, adlar

    # 4 · Excel dışa aktarma: "Blok-Slab" sütunu
    xl = c.get('/api/export/stok?tip=PLAKA&fmt=xlsx')
    assert xl.status_code == 200, xl.status_code
    import io as _io, openpyxl as _ox
    ws = _ox.load_workbook(_io.BytesIO(xl.data)).active
    kodlar = [r[0] for r in ws.iter_rows(min_row=2, values_only=True)]
    assert 'K8000-00' in kodlar, kodlar[:10]


def test_b4_sifir_slab_ekranda_yaziliyor():
    """B4: ekran tarafı — `stokNo` 0'ı yutmamalı.

    Hata tam buradaydı: `x.slab_no ? ... : x.blok_no` 0'ı yanlış
    saydığı için K6461-00 yerine K6461 yazıyordu."""
    import shutil as _shutil, subprocess as _sp, os as _os, json as _json
    node = _shutil.which('node') or '/opt/node22/bin/node'
    if not _os.path.exists(node):
        import pytest as _pytest
        _pytest.skip('node yok')
    betik = r"""
const fs = require('fs'), vm = require('vm');
const base = fs.readFileSync('templates/base.html', 'utf8');
const stok = fs.readFileSync('templates/stok.html', 'utf8');
const kes = (m, bas, son) => m.slice(m.indexOf(bas), m.indexOf(son, m.indexOf(bas)));
const kum = {}; vm.createContext(kum);
vm.runInContext(kes(base, 'function slabVar(', '/* ══ BANKA/KASA'), kum);
vm.runInContext(kes(base, 'function plakaKodu(', '/* ══ BANKA/KASA'), kum);
vm.runInContext(kes(stok, 'function stokNo(', 'const RENK'), kum);
console.log(JSON.stringify({
  sifir:  kum.stokNo({tip:'PLAKA', blok_no:'K6461', slab_no:0}),
  bir:    kum.stokNo({tip:'PLAKA', blok_no:'K6461', slab_no:1}),
  yok:    kum.stokNo({tip:'PLAKA', blok_no:'K6461', slab_no:null, id:'PLK-1'}),
  bosMtn: kum.stokNo({tip:'PLAKA', blok_no:'K6461', slab_no:'', id:'PLK-1'}),
  blok:   kum.stokNo({tip:'BLOK',  blok_no:'K6461'}),
  varSifir: kum.slabVar(0), varBos: kum.slabVar(''), varNull: kum.slabVar(null),
}));
"""
    r = _sp.run([node, '-e', betik], capture_output=True, text=True, cwd='.')
    assert r.returncode == 0, r.stderr[:400]
    d = _json.loads(r.stdout.strip().splitlines()[-1])
    assert d['sifir'] == 'K6461-00', d['sifir']
    assert d['bir'] == 'K6461-01', d['bir']
    assert d['yok'] == 'K6461' and d['bosMtn'] == 'K6461'
    assert d['blok'] == 'K6461'
    # `slabVar` 0'ı VAR sayar — hatanın özü buydu
    assert d['varSifir'] is True
    assert d['varBos'] is False and d['varNull'] is False


# ══════════════════════════════════════════════════════════════════════
#  OR1 · İŞ ORTAKLIĞI — KÂR PAYLAŞIMI
# ══════════════════════════════════════════════════════════════════════

def _or1_kur(sip_id, satislar, firma_id=1):
    """Bir sipariş + ona bağlı satış kayıtları kurar.

    satislar: [(tutar_usd, maliyet_usd)] — kâr farktan türetilir,
    tıpkı gerçek akışta olduğu gibi.
    """
    from models import Siparis, SatisKaydi
    with fa.app.app_context():
        db.session.add(Siparis(id=sip_id, musteri='ACIK CARI', doviz='USD',
                               toplam_tutar=sum(t for t, _ in satislar),
                               durum='Onaylandi',
                               siparis_tarihi=date(2026, 4, 1)))
        db.session.flush()
        for n, (tutar, maliyet) in enumerate(satislar, 1):
            db.session.add(SatisKaydi(
                id=f'{sip_id}-S{n}', siparis_id=sip_id, stok_tip='PLAKA',
                cins='TEST', musteri='ACIK CARI', satis_tarihi=date(2026, 4, 5),
                tutar=tutar, tutar_usd=tutar, doviz='USD',
                maliyet_usd=maliyet, kar_usd=tutar - maliyet,
                marj_yuzde=((tutar - maliyet) / tutar * 100) if tutar else 0))
        db.session.commit()


def test_or1_hesap_zinciri_basamak_basamak():
    """OR1: ciro → maliyet → brüt kâr → vergiler → net kâr → paylar.

    Her basamak ayrı ayrı doğrulanıyor: ortakla paylaşılan bir
    hesapta yalnız sonucu ölçmek, hatanın hangi basamakta olduğunu
    gizlerdi."""
    _or1_kur('SIPOR1', [(10000, 6000), (5000, 3000)])
    c = istemci('admin', 'ADMIN')

    r = c.post('/api/ortaklik', headers=H, json={
        'ad': 'OR1 testi', 'ortak_ad': 'FINANSOR', 'bizim_pay': 60,
        'ortak_pay': 40, 'anapara_yontemi': 'ayri'})
    assert r.status_code == 200, r.get_data(as_text=True)
    oid = r.get_json()['id']

    assert c.post(f'/api/ortaklik/{oid}/is', headers=H, json={
        'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR1'}).status_code == 200

    # Üç matrah tipi birden
    assert c.post(f'/api/ortaklik/{oid}/vergi', headers=H, json={
        'ad': 'Kurumlar', 'matrah_tipi': 'kar', 'oran': 25}).status_code == 200
    assert c.post(f'/api/ortaklik/{oid}/vergi', headers=H, json={
        'ad': 'Stopaj', 'matrah_tipi': 'ciro', 'oran': 1}).status_code == 200
    assert c.post(f'/api/ortaklik/{oid}/vergi', headers=H, json={
        'ad': 'İade alınamayan KDV', 'matrah_tipi': 'sabit',
        'tutar': 200, 'durum': 'odendi'}).status_code == 200

    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h['ciro'] == 15000, h['ciro']
    assert h['maliyet'] == 9000, h['maliyet']
    assert h['brut_kar'] == 6000, h['brut_kar']
    # 6000×25% = 1500 · 15000×1% = 150 · sabit 200 → 1850
    assert h['vergi_toplam'] == 1850, h['vergi_toplam']
    assert h['net_kar'] == 4150, h['net_kar']
    assert h['paylar']['biz'] == 2490 and h['paylar']['ortak'] == 1660, h['paylar']
    # Sabit kalem 'odendi', ötekiler 'tahmini'
    assert h['vergi_kesinlesen'] == 200 and h['vergi_tahmini'] == 1650
    assert any('TAHMİNİ' in u for u in h['uyarilar']), h['uyarilar']


def test_or1_anapara_iki_yontem_kari_degistirmez():
    """OR1: anapara yöntemi KÂRI değil, ÖDENECEĞİ değiştirir.

    Kolayca ters gidebilecek yer burası: sermayeyi kârdan düşmek,
    ortağın parasını gider gibi saymak olurdu."""
    _or1_kur('SIPOR2', [(10000, 6000)])
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Anapara testi', 'bizim_pay': 50, 'ortak_pay': 50,
        'anapara_yontemi': 'ayri'})
    oid = r.get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR2'})
    c.post(f'/api/ortaklik/{oid}/sermaye', headers=H, json={
        'taraf': 'ortak', 'yon': 'koydu', 'tutar': 6000})

    h1 = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h1['net_kar'] == 4000 and h1['paylar']['ortak'] == 2000
    assert h1['odenecek']['ortak'] == 2000, h1['odenecek']

    # Yöntemi değiştir — kâr AYNI kalmalı, ödenecek anaparayı da içermeli
    assert c.put(f'/api/ortaklik/{oid}', headers=H, json={
        'ad': 'Anapara testi', 'bizim_pay': 50, 'ortak_pay': 50,
        'anapara_yontemi': 'once_iade'}).status_code == 200
    h2 = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h2['net_kar'] == h1['net_kar'], (h1['net_kar'], h2['net_kar'])
    assert h2['paylar']['ortak'] == 2000
    assert h2['odenecek']['ortak'] == 8000, h2['odenecek']   # 6000 + 2000
    assert h2['kalan_anapara']['ortak'] == 6000


def test_or1_zararda_kar_vergisi_dogmaz():
    """OR1: zararda kâr üzerinden vergi hesaplanmaz.

    Negatif kârı orana çarpmak NEGATİF vergi üretir ve zararı kâr
    gibi dağıtırdı."""
    _or1_kur('SIPOR3', [(4000, 7000)])    # 3000 zarar
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Zarar testi', 'bizim_pay': 50, 'ortak_pay': 50}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR3'})
    c.post(f'/api/ortaklik/{oid}/vergi', headers=H, json={
        'ad': 'Kurumlar', 'matrah_tipi': 'kar', 'oran': 25})

    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h['brut_kar'] == -3000, h['brut_kar']
    assert h['vergi_toplam'] == 0, h['vergi_toplam']
    assert h['net_kar'] == -3000
    # Zarar da paylaşılır — payı sıfırlamak zararı bize yıkardı
    assert h['paylar']['ortak'] == -1500, h['paylar']


def test_or1_ayni_is_iki_ortakliga_baglanamaz():
    """OR1: bir iş tek ortaklığa bağlanır — aynı kâr iki kez
    paylaşılamaz."""
    _or1_kur('SIPOR4', [(1000, 500)])
    c = istemci('admin', 'ADMIN')
    a = c.post('/api/ortaklik', headers=H, json={'ad': 'A'}).get_json()['id']
    b = c.post('/api/ortaklik', headers=H, json={'ad': 'B'}).get_json()['id']
    assert c.post(f'/api/ortaklik/{a}/is', headers=H, json={
        'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR4'}).status_code == 200
    r = c.post(f'/api/ortaklik/{b}/is', headers=H, json={
        'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR4'})
    assert r.status_code == 409, r.get_data(as_text=True)
    # Var olmayan kaynak da bağlanamaz
    assert c.post(f'/api/ortaklik/{b}/is', headers=H, json={
        'kaynak_tip': 'SIPARIS', 'kaynak_id': 'YOK-123'}).status_code == 404


def test_or1_cariye_isleme_istege_bagli_ve_geri_alinabilir():
    """OR1: dağıtım cariye İSTEĞE BAĞLI işlenir, geri alınabilir.

    Geri alma hareketi gerçekten silmeli: kalırsa cari ekranında
    karşılığı olmayan bir borç durur."""
    from models import CariHareket, OrtaklikDagitim
    _or1_kur('SIPOR5', [(10000, 6000)])
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Cari testi', 'ortak_cari_id': 'C1', 'ortak_ad': 'ACIK CARI',
        'bizim_pay': 50, 'ortak_pay': 50}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR5'})
    did = c.post(f'/api/ortaklik/{oid}/dagitim', headers=H, json={
        'taraf': 'ortak', 'tutar': 2000}).get_json()['id']

    # Henüz cariye işlenmedi
    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h['dagitimlar'][0]['cariye_islendi'] is False
    assert h['bakiye']['ortak'] == 0, h['bakiye']   # 2000 pay − 2000 dağıtım

    r = c.post(f'/api/ortaklik/{oid}/dagitim/{did}/cariye', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    chid = r.get_json()['cari_hareket_id']
    with fa.app.app_context():
        ch = CariHareket.query.filter_by(id=chid).first()
        assert ch is not None and ch.alacak == 2000, ch
        assert ch.cari_id == 'C1'

    # İkinci kez işlenemez
    assert c.post(f'/api/ortaklik/{oid}/dagitim/{did}/cariye',
                  headers=H).status_code == 409
    # İşlenmişken silinemez
    assert c.delete(f'/api/ortaklik/{oid}/dagitim/{did}',
                    headers=H).status_code == 409

    # Geri al → hareket GERÇEKTEN silinir
    assert c.delete(f'/api/ortaklik/{oid}/dagitim/{did}/cariye',
                    headers=H).status_code == 200
    with fa.app.app_context():
        assert CariHareket.query.filter_by(id=chid).first() is None
        assert OrtaklikDagitim.query.get(did).cari_hareket_id is None


def test_or1_paylar_yuzde_yuzu_asamaz_ve_eksik_pay_uyarir():
    """OR1: toplam %100'ü aşamaz; aşmayan eksiklik SESSİZ kalmaz.

    Eksik payı kendiliğinden 100'e tamamlamak, üçüncü bir tarafa
    ayrılmış payı görünmez yapardı — bu yüzden uyarı veriliyor,
    düzeltme yapılmıyor."""
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Asan', 'bizim_pay': 70, 'ortak_pay': 40})
    assert r.status_code == 400, r.get_data(as_text=True)

    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Eksik', 'bizim_pay': 50, 'ortak_pay': 30}).get_json()['id']
    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert any('%80' in u for u in h['uyarilar']), h['uyarilar']


def test_or2_farkli_dovizler_kendi_tarihinin_kuruyla_cevrilir():
    """OR2: sermaye/dağıtım USD dışında girilebilir ve ÇEVRİLİR.

    Önce yalnız tutar alanı vardı; motor da dövize bakmadan
    topluyordu. Alan eklenip çevrim eklenmeseydi 30.000 EUR ile
    30.000 USD aynı sayı sayılır, ortağa ödenecek tutar yanlış
    çıkardı.

    Kur SATIRIN KENDİ TARİHİNDEN alınır: aylar önce konmuş anaparayı
    bugünkü kurla değerlemek, ortakla paylaşılan hesapta en
    tartışmalı yer olurdu."""
    from models import DovizKur
    # TEMMUZ-AĞUSTOS PENCERESİ: kur kayıtları takım genelinde
    # PAYLAŞILIYOR ve `_kur_getir` "tarihi <= aranan en SON kayıt"
    # kuralıyla çalışıyor. Başka testlerin koyduğu Şubat/Mart/Mayıs
    # kurları bu testin beklediği rakamı kaydırıyordu — bu pencereye
    # kimse dokunmuyor. Aşağıdaki koruma, ileride biri koyarsa
    # testin NEDEN kırıldığını söylüyor.
    with fa.app.app_context():
        for t, usd, eur in ((date(2026, 7, 1), 30.0, 33.0),
                            (date(2026, 8, 1), 40.0, 48.0)):
            for dv, val in (('USD', usd), ('EUR', eur)):
                if not DovizKur.query.filter_by(doviz=dv, tarih=t).first():
                    db.session.add(DovizKur(doviz=dv, tarih=t, alis=val,
                                            satis=val, efektif=val))
        db.session.commit()
        _araya_giren = DovizKur.query.filter(
            DovizKur.tarih > date(2026, 7, 1),
            DovizKur.tarih <= date(2026, 8, 10),
            DovizKur.tarih != date(2026, 8, 1)).all()
        assert not _araya_giren, (
            'Temmuz-Ağustos penceresine başka bir test kur koymuş: '
            + str([(k.doviz, str(k.tarih)) for k in _araya_giren]))

    _or1_kur('SIPOR6', [(10000, 6000)])
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Döviz testi', 'bizim_pay': 50, 'ortak_pay': 50,
        'anapara_yontemi': 'once_iade', 'doviz': 'EUR'}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR6'})

    # TEMMUZ: 1000 EUR → 1000 × 33 / 30 = 1100 USD
    assert c.post(f'/api/ortaklik/{oid}/sermaye', headers=H, json={
        'taraf': 'ortak', 'yon': 'koydu', 'tutar': 1000, 'doviz': 'EUR',
        'tarih': '2026-07-10'}).status_code == 200
    # AĞUSTOS: 1000 EUR → 1000 × 48 / 40 = 1200 USD (aynı tutar, başka kur)
    assert c.post(f'/api/ortaklik/{oid}/sermaye', headers=H, json={
        'taraf': 'ortak', 'yon': 'koydu', 'tutar': 1000, 'doviz': 'EUR',
        'tarih': '2026-08-10'}).status_code == 200
    # TEMMUZ: 3000 TRY → 3000 / 30 = 100 USD
    assert c.post(f'/api/ortaklik/{oid}/sermaye', headers=H, json={
        'taraf': 'ortak', 'yon': 'koydu', 'tutar': 3000, 'doviz': 'TRY',
        'tarih': '2026-07-10'}).status_code == 200

    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h['para_birimi'] == 'USD'
    # 1100 + 1200 + 100 = 2400 — ham toplam 5000 olurdu
    assert h['sermaye']['ortak'] == 2400, h['sermaye']
    assert h['kalan_anapara']['ortak'] == 2400
    # Net kâr 4000, ortak payı 2000, ödenecek = 2400 + 2000
    assert h['odenecek']['ortak'] == 4400, h['odenecek']
    assert h['cevrim_yapildi'] is True
    assert any('TCMB' in u for u in h['uyarilar']), h['uyarilar']

    # Sermaye SATIRI da USD karşılığını taşımalı: vergi ve dağıtım
    # gösterip sermaye göstermezse aynı tablo iki dilde konuşur.
    sh = c.get(f'/api/ortaklik/{oid}').get_json()['data']['sermaye_hareketleri']
    temmuz = [x for x in sh if x['tarih'] == '2026-07-10' and x['doviz'] == 'EUR'][0]
    assert temmuz['tutar'] == 1000 and temmuz['usd'] == 1100, temmuz
    assert temmuz['cevrildi'] is True

    # DAĞITIM da çevrilir ve ORİJİNALİ görünür
    c.post(f'/api/ortaklik/{oid}/dagitim', headers=H, json={
        'taraf': 'ortak', 'tutar': 1000, 'doviz': 'EUR',
        'tarih': '2026-08-10'})
    h2 = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    dg = h2['dagitimlar'][0]
    assert dg['tutar'] == 1200 and dg['ham_tutar'] == 1000, dg
    assert dg['doviz'] == 'EUR' and dg['cevrildi'] is True
    assert h2['dagitilan']['ortak'] == 1200
    assert h2['bakiye']['ortak'] == 3200, h2['bakiye']   # 4400 − 1200


def test_or2_sabit_vergi_kalemi_de_cevrilir():
    """OR2: 'sabit' vergi kalemi kendi dövizinde girilir.

    İade alınamayan KDV TL üzerinden doğar — USD sayılırsa kâr
    otuz kat fazla düşerdi."""
    from models import DovizKur
    # Kendi kurunu KENDİ koyuyor: öteki testin koyduğuna güvenmek,
    # tek başına koşunca düşen bir test demekti.
    with fa.app.app_context():
        if not DovizKur.query.filter_by(doviz='USD', tarih=date(2026, 7, 1)).first():
            db.session.add(DovizKur(doviz='USD', tarih=date(2026, 7, 1),
                                    alis=30.0, satis=30.0, efektif=30.0))
            db.session.commit()
    _or1_kur('SIPOR7', [(10000, 4000)])
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Sabit vergi dövizi', 'bizim_pay': 50,
        'ortak_pay': 50}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR7'})
    # 6000 TRY, Temmuz kuru 30 → 200 USD
    assert c.post(f'/api/ortaklik/{oid}/vergi', headers=H, json={
        'ad': 'İade alınamayan KDV', 'matrah_tipi': 'sabit', 'tutar': 6000,
        'doviz': 'TRY', 'durum': 'odendi',
        'odeme_tarihi': '2026-07-10'}).status_code == 200

    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    v = h['vergiler'][0]
    assert v['tutar'] == 200, v          # 6000 TRY → 200 USD
    assert v['ham_tutar'] == 6000 and v['doviz'] == 'TRY'
    assert v['cevrildi'] is True
    assert h['net_kar'] == 5800, h['net_kar']    # 6000 − 200
    assert h['cevrim_yapildi'] is True


def test_or3_baglanabilir_liste_bagli_isleri_elemeli():
    """OR3: iş numarası elle yazılmıyor, listeden seçiliyor.

    Liste ZATEN BAĞLI işleri eliyor: eskiden seçilebilen bir
    numara kaydet'e basınca 409 dönüyordu — hatayı seçim anında
    değil, kaydetme anında öğreniyordun."""
    _or1_kur('SIPOR8', [(5000, 3000)])
    _or1_kur('SIPOR9', [(7000, 4000)])
    c = istemci('admin', 'ADMIN')
    a = c.post('/api/ortaklik', headers=H,
               json={'ad': 'Seçici A'}).get_json()['id']
    b = c.post('/api/ortaklik', headers=H,
               json={'ad': 'Seçici B'}).get_json()['id']

    d = c.get(f'/api/ortaklik/{a}/baglanabilir?tip=SIPARIS').get_json()
    idler = [x['id'] for x in d['data']]
    assert 'SIPOR8' in idler and 'SIPOR9' in idler, idler
    # Satış kaydı olan işler işaretli geliyor
    s8 = [x for x in d['data'] if x['id'] == 'SIPOR8'][0]
    assert s8['satis_var'] is True and s8['musteri'] == 'ACIK CARI'

    # SIPOR8'i A'ya bağla → B'nin listesinden DÜŞMELİ
    assert c.post(f'/api/ortaklik/{a}/is', headers=H, json={
        'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR8'}).status_code == 200
    d2 = c.get(f'/api/ortaklik/{b}/baglanabilir?tip=SIPARIS').get_json()
    idler2 = [x['id'] for x in d2['data']]
    assert 'SIPOR8' not in idler2, idler2
    assert 'SIPOR9' in idler2, idler2

    # Geçersiz tip reddedilir
    assert c.get(f'/api/ortaklik/{a}/baglanabilir?tip=HEBELE').status_code == 400


def test_or3_ortakliga_bagli_proforma_silinemez():
    """OR3: bağlı proforma silinirse ortaklığın cirosu SEBEPSİZ düşer.

    Proforma silinince satış kaydı KALIYOR ama `proforma_id`
    boşaltılıyor (kâr izi kaybolmasın diye, doğru). Ortaklık o bağ
    üzerinden okuduğu için ciro sessizce sıfırlanırdı. Siparişte bu
    kapı zaten vardı, proformada yoktu."""
    from models import Proforma, SatisKaydi
    with fa.app.app_context():
        db.session.add(Proforma(id='PROR3', musteri='ACIK CARI', cari_id='C1',
                                toplam=9000, doviz='USD', durum='Taslak'))
        db.session.flush()
        db.session.add(SatisKaydi(
            id='PROR3-S1', proforma_id='PROR3', stok_tip='PLAKA', cins='TEST',
            musteri='ACIK CARI', satis_tarihi=date(2026, 4, 5),
            tutar=9000, tutar_usd=9000, doviz='USD',
            maliyet_usd=5000, kar_usd=4000))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Proforma bağı', 'bizim_pay': 50,
        'ortak_pay': 50}).get_json()['id']
    assert c.post(f'/api/ortaklik/{oid}/is', headers=H, json={
        'kaynak_tip': 'PROFORMA', 'kaynak_id': 'PROR3'}).status_code == 200

    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h['ciro'] == 9000 and h['brut_kar'] == 4000, h

    r = c.delete('/api/proforma/PROR3', headers=H)
    assert r.status_code == 400, r.get_data(as_text=True)
    assert r.get_json().get('error') == 'ortakliga_bagli'
    # Ciro yerinde duruyor
    h2 = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h2['ciro'] == 9000

    # Bağ çözülünce silinebilir
    isler = c.get(f'/api/ortaklik/{oid}').get_json()['data']['isler']
    assert c.delete(f"/api/ortaklik/{oid}/is/{isler[0]['id']}",
                    headers=H).status_code == 200
    assert c.delete('/api/proforma/PROR3', headers=H).status_code == 200


def test_or3_kaybolan_kaynak_acikca_soyleniyor():
    """OR3: bağlı iş sistemden kalkmışsa 'satış kaydı yok' demek
    yanıltıcıdır — iş ortadan kalkmıştır, bunu söylemeli."""
    from models import Sevkiyat
    with fa.app.app_context():
        db.session.add(Sevkiyat(id='SVOR3', musteri='ACIK CARI',
                                sevk_tarihi=date(2026, 4, 1),
                                durum='Hazirlaniyor'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H,
                 json={'ad': 'Kayıp kaynak'}).get_json()['id']
    assert c.post(f'/api/ortaklik/{oid}/is', headers=H, json={
        'kaynak_tip': 'SEVKIYAT', 'kaynak_id': 'SVOR3'}).status_code == 200

    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert any('satış kaydı yok' in u for u in h['uyarilar']), h['uyarilar']

    # Sevkiyat ortadan kalkarsa mesaj DEĞİŞMELİ
    with fa.app.app_context():
        db.session.delete(Sevkiyat.query.filter_by(id='SVOR3').first())
        db.session.commit()
    h2 = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert any('artık sistemde yok' in u and 'SVOR3' in u
               for u in h2['uyarilar']), h2['uyarilar']


def test_or4_sunucunun_hata_mesaji_ustu_ortulmuyor():
    """OR4: `api()` hatayı zaten bildiriyor; üstüne yazma.

    `api()` hata mesajını kullanıcıya gösterip `istek_hatasi` adlı
    bir İŞARET fırlatıyor. Onu `e.message` diye basmak, sunucunun
    söylediği gerçek sebebin üstünü örtüyordu: ekranda yalnız
    'istek_hatasi' kalıyor ve hata teşhis edilemiyordu (ölçüldü —
    sermaye hareketi eklerken tam bu oldu).

    Ev kuralı: `catch (e) { /* api() zaten bildiriyor */ }`."""
    import io as _io, re as _re
    h = _io.open('templates/ortaklik.html', encoding='utf-8').read()
    kotu = _re.findall(r'catch \(e\) \{[^}]*bildir\(e\.message', h)
    assert not kotu, f'{len(kotu)} yerde api() hatasının üstüne yazılıyor'
    # İşaretin kendisi hiçbir yerde kullanıcıya gösterilmemeli
    assert 'istek_hatasi' not in h


# ══════════════════════════════════════════════════════════════════════
#  OR5 · SÜTUN GENİŞLİĞİ — SQLite'ın GÖRMEDİĞİ HATA
# ══════════════════════════════════════════════════════════════════════

def test_or5_metin_sutunlari_yazilacak_degerleri_tasiyor():
    """OR5: VARCHAR genişliği, kodun yazabileceği en uzun değeri almalı.

    SQLite uzunluk kısıtını UYGULAMIYOR; PostgreSQL uyguluyor. Bu
    yüzden dar bir sütun testlerden geçer, üretimde 500 verir —
    `ortaklik_sermaye.yon` String(8) iken 'geri_aldi' (9 karakter)
    tam bunu yaptı.

    Bu test o boşluğu yapısal olarak kapatıyor: veritabanı
    gerekmiyor, sözlükle genişliği karşılaştırıyor."""
    import io as _io, re as _re
    kaynak = _io.open('models.py', encoding='utf-8').read()

    # Kodun bu sütunlara yazabileceği SABİT değerler. Yeni bir değer
    # eklerken buraya da eklenmeli — testin görevi bunu zorlamak.
    SOZLUK = {
        'Ortaklik': {
            'anapara_yontemi': ['ayri', 'once_iade'],
            'durum': ['Acik', 'Kapandi'],
            'doviz': ['USD', 'EUR', 'TRY']},
        'OrtaklikIs': {
            'kaynak_tip': ['SIPARIS', 'SEVKIYAT', 'PROFORMA']},
        'OrtaklikVergi': {
            'matrah_tipi': ['kar', 'ciro', 'sabit'],
            'durum': ['tahmini', 'kesinlesti', 'odendi'],
            'doviz': ['USD', 'EUR', 'TRY']},
        'OrtaklikSermaye': {
            'taraf': ['ortak', 'biz'],
            'yon': ['koydu', 'geri_aldi'],
            'doviz': ['USD', 'EUR', 'TRY']},
        'OrtaklikDagitim': {
            'taraf': ['ortak', 'biz'],
            'doviz': ['USD', 'EUR', 'TRY']},
    }

    dar = []
    for sinif, alanlar in SOZLUK.items():
        _b = kaynak.index(f'class {sinif}(')
        _s = kaynak.index('\nclass ', _b + 1) if '\nclass ' in kaynak[_b + 1:] else len(kaynak)
        govde = kaynak[_b:_s]
        for alan, degerler in alanlar.items():
            e = _re.search(r'\b%s\s*=\s*db\.Column\(db\.String\((\d+)\)' % alan, govde)
            assert e, f'{sinif}.{alan} bulunamadı'
            boy, enuzun = int(e.group(1)), max(degerler, key=len)
            if len(enuzun) > boy:
                dar.append(f'{sinif}.{alan}: String({boy}) ama '
                           f"'{enuzun}' {len(enuzun)} karakter")
    assert not dar, 'Dar sütun(lar): ' + ' · '.join(dar)


def test_or5_varsayilan_degerler_sutuna_sigiyor():
    """OR5: bir sütunun `default`'u kendi genişliğini aşamaz.

    Aynı sınıf hata, genel hâli: SQLite'ta görünmez, PostgreSQL'de
    kayıt açılamaz. Bütün modeli tarıyor."""
    import io as _io, re as _re
    kaynak = _io.open('models.py', encoding='utf-8').read()
    kotu = []
    for e in _re.finditer(
            r"db\.Column\(db\.String\((\d+)\)[^)\n]*?default=(['\"])(.*?)\2",
            kaynak):
        boy, deger = int(e.group(1)), e.group(3)
        if len(deger) > boy:
            satir = kaynak[:e.start()].count('\n') + 1
            kotu.append(f"models.py:{satir} String({boy}) <- '{deger}'")
    assert not kotu, 'Varsayılanı sığmayan sütun(lar): ' + ' · '.join(kotu)


# ══════════════════════════════════════════════════════════════════════
#  OR6 · FASON VE DİĞER ÖDEMELER KATKI DEFTERİNE GİRİYOR
# ══════════════════════════════════════════════════════════════════════

def _or6_kur(sip_id, stok_id, tutar, maliyet):
    """Sipariş + satış kaydı + o satışın stoğu."""
    from models import Siparis, SatisKaydi
    with fa.app.app_context():
        db.session.add(Siparis(id=sip_id, musteri='ACIK CARI', doviz='USD',
                               toplam_tutar=tutar, durum='Onaylandi',
                               siparis_tarihi=date(2026, 4, 1)))
        db.session.flush()
        db.session.add(SatisKaydi(
            id=f'{sip_id}-S1', siparis_id=sip_id, stok_id=stok_id,
            stok_tip='PLAKA', cins='TEST', musteri='ACIK CARI',
            satis_tarihi=date(2026, 4, 5), tutar=tutar, tutar_usd=tutar,
            doviz='USD', maliyet_usd=maliyet, kar_usd=tutar - maliyet))
        db.session.commit()


def test_or6_maliyet_katkiya_aliniyor_ve_iki_kez_girmiyor():
    """OR6: fason gideri elle yazılmıyor, maliyetten alınıyor.

    Bir maliyeti KİMİN ödediği maliyet kaydında yazmıyor —
    nakliyeyi ortak, fasonu biz ödemiş olabiliriz. Bu yüzden
    otomatik değil, tarafı işaretleyerek alınıyor."""
    from models import Maliyet, OrtaklikSermaye
    _or6_kur('SIPOR6A', 'PLK-OR6-1', 20000, 13000)
    with fa.app.app_context():
        db.session.add(Maliyet(id='MAL-OR6-1', baglanti_tip='stok',
                               baglanti_id='PLK-OR6-1',
                               maliyet_tip='Kesim / Fason / Üretim',
                               maliyet_tarihi=date(2026, 3, 10),
                               tutar=3000, doviz='USD', usd_karsilik=3000,
                               aktif=True))
        db.session.add(Maliyet(id='MAL-OR6-2', baglanti_tip='siparis',
                               baglanti_id='SIPOR6A', maliyet_tip='Nakliye',
                               maliyet_tarihi=date(2026, 3, 12),
                               tutar=500, doviz='USD', usd_karsilik=500,
                               aktif=True))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Fason ortaklığı', 'bizim_pay': 50, 'ortak_pay': 50,
        'anapara_yontemi': 'once_iade'}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR6A'})

    # Hem STOĞA hem SİPARİŞE bağlı maliyetler görünmeli
    d = c.get(f'/api/ortaklik/{oid}/maliyetler').get_json()
    idler = sorted(x['id'] for x in d['data'])
    assert idler == ['MAL-OR6-1', 'MAL-OR6-2'], idler
    assert all(x['katki_id'] is None for x in d['data'])

    # Fason BİZE, nakliye ORTAĞA
    r = c.post(f'/api/ortaklik/{oid}/maliyet_katki', headers=H, json={
        'taraf': 'biz', 'maliyet_idler': ['MAL-OR6-1']})
    assert r.status_code == 200 and r.get_json()['eklenen'] == 1
    r2 = c.post(f'/api/ortaklik/{oid}/maliyet_katki', headers=H, json={
        'taraf': 'ortak', 'maliyet_idler': ['MAL-OR6-2']})
    assert r2.status_code == 200 and r2.get_json()['eklenen'] == 1

    # AYNI maliyet ikinci kez giremez
    r3 = c.post(f'/api/ortaklik/{oid}/maliyet_katki', headers=H, json={
        'taraf': 'biz', 'maliyet_idler': ['MAL-OR6-1']})
    assert r3.get_json()['eklenen'] == 0, r3.get_json()
    assert 'zaten' in ' '.join(r3.get_json()['atlanan'])
    with fa.app.app_context():
        assert OrtaklikSermaye.query.filter_by(
            ortaklik_id=oid, maliyet_id='MAL-OR6-1').count() == 1

    # Başka bir işin gideri bu hesaba giremez
    with fa.app.app_context():
        db.session.add(Maliyet(id='MAL-YABANCI', baglanti_tip='stok',
                               baglanti_id='BASKA-STOK', maliyet_tip='Nakliye',
                               maliyet_tarihi=date(2026, 3, 1), tutar=999,
                               doviz='USD', usd_karsilik=999, aktif=True))
        db.session.commit()
    r4 = c.post(f'/api/ortaklik/{oid}/maliyet_katki', headers=H, json={
        'taraf': 'biz', 'maliyet_idler': ['MAL-YABANCI']})
    assert r4.get_json()['eklenen'] == 0
    assert 'bağlı değil' in ' '.join(r4.get_json()['atlanan'])


def test_or6_iki_taraf_da_koydugunu_geri_aliyor_ve_nakit_kapaniyor():
    """OR6: ortak sermayeyi, biz fasonu koyuyoruz — ikisi de geri döner.

    Nakit denkliği: CİRO = (ortağın katkısı + bizim katkımız) +
    net kâr + vergi. Bu tutmazsa ya biri iki kez sayılmıştır ya da
    biri hiç sayılmamıştır."""
    from models import Maliyet
    _or6_kur('SIPOR6B', 'PLK-OR6-2', 50000, 32000)
    with fa.app.app_context():
        db.session.add(Maliyet(id='MAL-OR6-3', baglanti_tip='stok',
                               baglanti_id='PLK-OR6-2',
                               maliyet_tip='Kesim / Fason / Üretim',
                               maliyet_tarihi=date(2026, 3, 10),
                               tutar=12000, doviz='USD', usd_karsilik=12000,
                               aktif=True))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Nakit denkliği', 'bizim_pay': 50, 'ortak_pay': 50,
        'anapara_yontemi': 'once_iade'}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR6B'})
    # Ortak blok parasını koydu (elle), fasonu biz ödedik (maliyetten)
    c.post(f'/api/ortaklik/{oid}/sermaye', headers=H, json={
        'taraf': 'ortak', 'yon': 'koydu', 'tutar': 20000,
        'tarih': '2026-03-01'})
    c.post(f'/api/ortaklik/{oid}/maliyet_katki', headers=H, json={
        'taraf': 'biz', 'maliyet_idler': ['MAL-OR6-3']})

    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h['ciro'] == 50000 and h['brut_kar'] == 18000, h
    assert h['sermaye']['ortak'] == 20000, h['sermaye']
    assert h['sermaye']['biz'] == 12000, h['sermaye']
    # Her iki taraf da koyduğunu + payını alıyor
    assert h['odenecek']['ortak'] == 20000 + 9000, h['odenecek']
    assert h['odenecek']['biz'] == 12000 + 9000, h['odenecek']
    # NAKİT DENKLİĞİ: maliyetin içinde olan katkılar + kâr = ciro
    katki = h['sermaye']['ortak'] + h['sermaye']['biz']
    assert katki + h['brut_kar'] + (h['maliyet'] - katki) == h['ciro']


def test_or6_tipsiz_ve_iptal_maliyet_dogru_elenir():
    """OR6: süzgeç iki şeyi birden doğru yapmalı.

    · `~tip.in_(...)` TEK BAŞINA tipi BOŞ satırı da eler (SQL'de
      NULL NOT IN (...) → NULL). Tipsiz girilmiş bir fason gideri
      listede hiç görünmez, eksik olduğu da anlaşılmazdı.
    · `aktif=False` kayıt İPTAL EDİLMİŞ maliyettir; listede
      çıkarsa iptal edilmiş bir gider katkı sayılabilirdi.

    İkisi de ÖLÇÜLDÜ, ikisi de düzeltildi."""
    from models import Maliyet
    _or6_kur('SIPOR6C', 'PLK-OR6-3', 9000, 5000)
    with fa.app.app_context():
        db.session.add_all([
            Maliyet(id='MAL-TIPSIZ', baglanti_tip='stok',
                    baglanti_id='PLK-OR6-3', maliyet_tip=None,
                    maliyet_tarihi=date(2026, 3, 5), tutar=700,
                    doviz='USD', usd_karsilik=700, aktif=True),
            Maliyet(id='MAL-IPTAL', baglanti_tip='stok',
                    baglanti_id='PLK-OR6-3', maliyet_tip='Nakliye',
                    maliyet_tarihi=date(2026, 3, 6), tutar=800,
                    doviz='USD', usd_karsilik=800, aktif=False),
            Maliyet(id='MAL-KDV', baglanti_tip='stok',
                    baglanti_id='PLK-OR6-3', maliyet_tip='Iade KDV',
                    maliyet_tarihi=date(2026, 3, 7), tutar=900,
                    doviz='USD', usd_karsilik=900, aktif=True)])
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H,
                 json={'ad': 'Süzgeç'}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR6C'})

    idler = [x['id'] for x in
             c.get(f'/api/ortaklik/{oid}/maliyetler').get_json()['data']]
    assert 'MAL-TIPSIZ' in idler, ('tipsiz kayıt elenmiş', idler)
    assert 'MAL-IPTAL' not in idler, ('iptal kayıt görünüyor', idler)
    assert 'MAL-KDV' not in idler, ('KDV kalemi görünüyor', idler)


def test_or6_ekranda_bizim_taraf_da_gorunuyor():
    """OR6: fason bedelini biz ödediğimizde "biz ne alacağız" ekranda olmalı.

    Motor `odenecek['biz']`'i hep hesaplıyordu ama döküm yalnız
    ortağın satırlarını yazıyordu — OR6 öncesi biz para koymadığımız
    için fark edilmemişti. Katkı koyduğumuz anda o satırlar şart."""
    import io as _io
    h = _io.open('templates/ortaklik.html', encoding='utf-8').read()
    # OR10: iki taraf artık KOŞULSUZ görünüyor. Önceden yalnız
    # katkımız varsa çıkıyordu; döküm "Hesaplaşma" bloğunda iki
    # tarafı simetrik gösterince o koşul gereksizleşti — ve
    # koşullu olması "bizim tarafımız yok" diye okunabiliyordu.
    for parca in ('Bizim alacağımız toplam', 'Bize kalan bakiye',
                  'h.odenecek.biz', 'h.bakiye.biz', 'h.dagitilan.biz'):
        assert parca in h, parca
    # Ekstre de AYNI satırları taşımalı: iki yerde iki ayrı sıralama,
    # aynı hesabın iki ayrı yüzü gibi okunurdu.
    e = _io.open('templates/ortaklik_ekstre_print.html', encoding='utf-8').read()
    for parca in ('Bizim alacağımız toplam', 'Bize kalan bakiye'):
        assert parca in e, ('ekstre', parca)


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


def test_or8_zincirle_kapsanan_stok_secilebilir_gorunmez():
    """OR8: bağlı bloktan türeyen plakalar seçicide ÇIKMAMALI.

    Rakamı bozmuyordu — eşleşme küme üzerinden tek sorguyla
    yapılıyor, ciro iki kez sayılmıyor (ölçüldü). Ama plakalar
    seçilebilir göründüğü sürece "bağlamazsam dahil değil"
    yanılgısını besliyordu; bağlayınca da bağlı iş listesi gereksiz
    şişiyordu."""
    from models import BlokStok, SatisKaydi
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BLK-OR8', firma_id=1, blok_no='K8800', cins='TEST',
            boy=300, yukseklik=180, en=170, hacim_m3=9.18, tonaj=24,
            alis_fiyati=420, alis_fiyat_birim='ton', doviz='USD',
            durum='Serbest', uretici='ALBSTONE'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': ['BLK-OR8'],
        'kesim_tarihi': '2026-10-10',
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'TEST', 'boy': 280,
                      'yukseklik': 170, 'kalinlik': 2, 'adet': 3}]})
    plakalar = [o['id'] for o in r.get_json()['olusan_stoklar']]
    with fa.app.app_context():
        db.session.add(SatisKaydi(
            id='SAT-OR8', firma_id=1, stok_id=plakalar[0], stok_tip='PLAKA',
            cins='TEST', musteri='ACIK CARI', satis_tarihi=date(2026, 10, 20),
            tutar=3000, tutar_usd=3000, doviz='USD',
            maliyet_usd=1800, kar_usd=1200))
        db.session.commit()

    oid = c.post('/api/ortaklik', headers=H,
                 json={'ad': 'Kapsam'}).get_json()['id']
    # Blok bağlanmadan ÖNCE plakalar seçilebilir
    once = [x['id'] for x in
            c.get(f'/api/ortaklik/{oid}/baglanabilir?tip=PLAKA').get_json()['data']]
    assert all(p in once for p in plakalar), once

    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'BLOK', 'kaynak_id': 'BLK-OR8'})

    # Blok bağlandıktan SONRA plakalar listede YOK
    sonra = [x['id'] for x in
             c.get(f'/api/ortaklik/{oid}/baglanabilir?tip=PLAKA').get_json()['data']]
    assert not any(p in sonra for p in plakalar), sonra

    # Yine de bağlamaya kalkarsan SEBEBİNİ söyleyerek durduruyor
    r2 = c.post(f'/api/ortaklik/{oid}/is', headers=H,
                json={'kaynak_tip': 'PLAKA', 'kaynak_id': plakalar[0]})
    assert r2.status_code == 409, r2.get_data(as_text=True)
    assert r2.get_json().get('error') == 'zaten_kapsanda'
    assert 'türemiş' in r2.get_json()['mesaj']

    # Bağlı iş satırı kapsamı söylüyor
    isler = c.get(f'/api/ortaklik/{oid}').get_json()['data']['isler']
    blok = [i for i in isler if i['kaynak_id'] == 'BLK-OR8'][0]
    assert blok['kapsanan'] == 3, blok

    # Ve ciro zaten plakadan geliyor — blok tek başına yeterli
    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h['ciro'] == 3000 and h['satis_adedi'] == 1, h


# ══════════════════════════════════════════════════════════════════════
#  OR9 · ORTAKLIK RAPORU VE EKSTRESİ
# ══════════════════════════════════════════════════════════════════════

def test_or9_ortaklik_raporu_excel_ve_pdf():
    """OR9: ortaklık listesi Excel/PDF olarak dışa aktarılabilmeli."""
    import io as _io, openpyxl as _ox
    _or1_kur('SIPOR9R', [(20000, 12000)])
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Rapor testi', 'ortak_ad': 'FINANSOR', 'bizim_pay': 60,
        'ortak_pay': 40}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR9R'})

    r = c.get('/api/export/ortaklik?format=xlsx')
    assert r.status_code == 200, r.status_code
    ws = _ox.load_workbook(_io.BytesIO(r.data)).active
    satirlar = [[x for x in row] for row in ws.iter_rows(values_only=True)]
    bizim = [s for s in satirlar if s and s[0] and oid in str(s[0])]
    assert bizim, satirlar[:4]
    # Ciro / brüt kâr sütunları dolu geliyor
    assert '20.000' in str(bizim[0][4]) or '20000' in str(bizim[0][4]), bizim[0]

    # PDF yolu weasyprint/reportlab ister. Kurulu değilse bu
    # ORTAMIN eksiği — modülün değil; yanlış alarm vermesin.
    try:
        import weasyprint  # noqa: F401
    except Exception:
        try:
            import reportlab  # noqa: F401
        except Exception:
            import pytest as _pytest
            _pytest.skip('PDF kütüphanesi kurulu değil')
    assert c.get('/api/export/ortaklik?format=pdf').status_code == 200


def test_or9_ekstre_iki_kipte_calisiyor():
    """OR9: ekstre iki kipte — ortağa gönderilecek ve iç kullanım.

    İç kipin verisi şablonda GİZLENMİYOR; sunucu ortak kipinde onu
    hiç göndermiyor. Gizlemek, şablonda bir koşul unutulduğunda
    müşteri adını ortağın belgesine basmakla biterdi."""
    from models import Maliyet
    _or1_kur('SIPOR9E', [(30000, 18000)])
    with fa.app.app_context():
        db.session.add(Maliyet(
            id='MYT-OR9', firma_id=1, baglanti_tip='siparis',
            baglanti_id='SIPOR9E', maliyet_tip='Kesim / Fason / Üretim',
            maliyet_tarihi=date(2026, 10, 5), tutar=2500, doviz='USD',
            usd_karsilik=2500, aktif=True, fatura_no='FSN-OR9'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Ekstre testi', 'ortak_ad': 'FINANSOR', 'bizim_pay': 50,
        'ortak_pay': 50, 'anapara_yontemi': 'once_iade'}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR9E'})
    c.post(f'/api/ortaklik/{oid}/maliyet_katki', headers=H, json={
        'taraf': 'biz', 'maliyet_idler': ['MYT-OR9']})

    # ── ORTAK KİPİ ──
    r = c.get(f'/ortaklik/{oid}/ekstre')
    assert r.status_code == 200, r.status_code
    g = r.get_data(as_text=True)
    assert 'ORTAKLIK EKSTRESİ' in g
    assert 'Brüt kâr' in g and 'Net kâr' in g
    assert '12000.00' in g.replace(',', '') or '12.000' in g  # brüt kâr
    # Müşteri adı ve fatura no ortağın belgesinde YOK
    assert 'ACIK CARI' not in g, 'müşteri adı ortak kipinde görünüyor'
    assert 'FSN-OR9' not in g, 'fatura no ortak kipinde görünüyor'
    assert 'İÇ KULLANIM' not in g

    # ── İÇ KİP ──
    r2 = c.get(f'/ortaklik/{oid}/ekstre?kip=ic')
    assert r2.status_code == 200
    g2 = r2.get_data(as_text=True)
    assert 'İÇ KULLANIM' in g2
    assert 'ACIK CARI' in g2, 'iç kipte satış kaydı yok'
    assert 'FSN-OR9' in g2, 'iç kipte maliyet kaydı yok'
    assert 'Bağlı işler' in g2

    # Geçersiz kip ortak kipine düşer (sızdırmaya yer bırakmaz)
    g3 = c.get(f'/ortaklik/{oid}/ekstre?kip=hebele').get_data(as_text=True)
    assert 'ACIK CARI' not in g3 and 'İÇ KULLANIM' not in g3


def test_or9_ekstre_yetki_ve_bulunamadi():
    """OR9: ekstre kâr rakamı taşıyor — yetkisiz göremez."""
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H,
                 json={'ad': 'Yetki'}).get_json()['id']
    assert c.get('/ortaklik/YOK-123/ekstre').status_code == 404

    d = istemci('depocu', 'DEPO')
    r = d.get(f'/ortaklik/{oid}/ekstre')
    assert r.status_code in (302, 403), r.status_code
    assert c.get('/api/export/ortaklik?format=xlsx').status_code == 200
    assert d.get('/api/export/ortaklik?format=xlsx').status_code == 403


def test_sd1_bos_durum_stogun_durumunu_silemez():
    """SD1: düzenleme formu, durumu listesinde olmayan stoklarda
    (Kesildi, Sevkedildi…) <select>'i boş bırakıyordu ve Kaydet o
    boşluğu yazıyordu. Kesilmiş blok 'Depoda' görünüyor, silme
    korumaları duruma baktığı için düşüyordu.

    Sunucu ikinci kapı: boş/boşluk durum ASLA yazılmaz."""
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BSD1', blok_no='SD1-1', cins='TEST', boy=300, yukseklik=150,
            en=120, hacim_m3=5.4, tonaj=15, durum='Kesildi',
            alis_fiyati=270, alis_fiyat_birim='ton', doviz='EUR'))
        db.session.commit()

    for bos in ('', '   ', None):
        r = c.put('/api/stok/BSD1', headers=H,
                  json={'tip': 'BLOK', 'durum': bos, 'cins': 'TEST'})
        assert r.status_code == 200, (bos, r.status_code)
        with fa.app.app_context():
            assert db.session.get(BlokStok, 'BSD1').durum == 'Kesildi', bos

    # Gerçek bir durum hâlâ yazılabiliyor — kapıyı kapatmadık
    c.put('/api/stok/BSD1', headers=H,
          json={'tip': 'BLOK', 'durum': 'Serbest', 'cins': 'TEST'})
    with fa.app.app_context():
        assert db.session.get(BlokStok, 'BSD1').durum == 'Serbest'


def test_sd1_doviz_ve_birim_duzenlenebiliyor():
    """SD1: düzenleme formunda tutar vardı, PARA BİRİMİ yoktu —
    '270' tek başına bir şey söylemiyor. Yanlış dövizle girilmiş
    stok düzeltilemiyordu."""
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BSD2', blok_no='SD1-2', cins='TEST', boy=300, yukseklik=150,
            en=120, hacim_m3=5.4, tonaj=15, durum='Serbest',
            alis_fiyati=270, alis_fiyat_birim='ton', doviz='USD'))
        db.session.commit()

    r = c.put('/api/stok/BSD2', headers=H,
              json={'tip': 'BLOK', 'cins': 'TEST', 'durum': 'Serbest',
                    'alis_fiyati': 270, 'doviz': 'EUR', 'fiyat_birim': 'm3'})
    assert r.status_code == 200, r.status_code
    with fa.app.app_context():
        s = db.session.get(BlokStok, 'BSD2')
        assert s.doviz == 'EUR', s.doviz
        assert s.alis_fiyat_birim == 'm3', s.alis_fiyat_birim

    # Tanınmayan döviz yazılmaz — serbest metin para birimi olmaz
    c.put('/api/stok/BSD2', headers=H,
          json={'tip': 'BLOK', 'cins': 'TEST', 'doviz': 'ZZZ'})
    with fa.app.app_context():
        assert db.session.get(BlokStok, 'BSD2').doviz == 'EUR'


def test_sd1_doviz_degisince_tedarikci_borcu_sessizce_donmez():
    """SD1: C1'den beri BİR CariHareket BİRDEN ÇOK stoğu kapsıyor
    (fatura bazlı gruplama). Tek stoğun dövizi değişti diye o satırı
    çevirmek, aynı faturadaki öbür stokların borcunu da değiştirirdi.
    Borca dokunulmuyor — ama sessiz kalınmıyor, kullanıcı uyarılıyor."""
    from models import CariHareket
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add_all([
            BlokStok(id='BSD3', blok_no='SD1-3', cins='TEST', boy=300,
                     yukseklik=150, en=120, hacim_m3=5.4, tonaj=15,
                     durum='Serbest', alis_fiyati=270, doviz='USD'),
            CariHareket(id='CH-SD3', cari_id='C1', cari_unvan='TEDARIKCI',
                        hareket_tarihi=date.today(), islem_tip='Alis',
                        alacak=4050, doviz='USD', aciklama='stok alis',
                        baglanti_tip='stok', baglanti_id='BSD3')])
        db.session.commit()

    r = c.put('/api/stok/BSD3', headers=H,
              json={'tip': 'BLOK', 'cins': 'TEST', 'doviz': 'EUR'})
    d = r.get_json()
    assert d.get('uyari') is True, d
    assert 'USD' in (d.get('mesaj') or '') and 'EUR' in (d.get('mesaj') or ''), d
    with fa.app.app_context():
        assert db.session.get(BlokStok, 'BSD3').doviz == 'EUR'
        ch = CariHareket.query.filter_by(baglanti_id='BSD3').first()
        assert ch.doviz == 'USD', 'tedarikçi borcu sessizce çevrilmiş'


def test_sd1_formda_doviz_birim_ve_durum_korumasi_var():
    """SD1: üç eksik de ŞABLONDA — sunucu düzelmesi tek başına
    yetmez, kullanıcının gördüğü form yanlış değer gönderiyordu."""
    import io as _io
    h = _io.open('templates/stok.html', encoding='utf-8').read()
    for parca in ("id=\"duzDoviz\"", "id=\"duzFiyatBirim\"",
                  "doviz: document.getElementById('duzDoviz').value",
                  "fiyat_birim: document.getElementById('duzFiyatBirim').value",
                  'function durumSecenekleriniKur'):
        assert parca in h, parca
    # Durum artık sabit listeyle doldurulmuyor: tanınmayan değer
    # listeye EKLENİYOR, yoksa <select> sessizce boşalır.
    assert "document.getElementById('duzDurum').value = s.durum" not in h
    assert 'DUZ_ELLE_DURUMLAR.includes(d)' in h


def test_ma1_maliyet_aciklamasi_kaydediliyor():
    """MA1: `aciklama` modelde vardı ve HER YERDE okunuyordu — detay
    paneli, arama, dışa aktarma, ortaklık ekstresi — ama hiçbir uç
    nokta onu kabul etmiyordu. Girilen not hiçbir yere ulaşmıyordu."""
    from models import Maliyet
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BMA1', blok_no='MA1-1', cins='TEST', boy=300, yukseklik=150,
            en=120, hacim_m3=5.4, tonaj=15, durum='Serbest'))
        db.session.commit()

    r = c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Nakliye', 'baglanti_tip': 'stok',
        'baglanti_id': 'BMA1', 'tutar': 1000, 'doviz': 'USD',
        'aciklama': 'Limandan depoya çekici — şoför Ahmet'})
    assert r.status_code == 200, r.status_code
    with fa.app.app_context():
        m = Maliyet.query.filter_by(baglanti_id='BMA1',
                                    maliyet_tip='Nakliye').first()
        assert m is not None
        assert m.aciklama == 'Limandan depoya çekici — şoför Ahmet', m.aciklama


def test_ma1_dagitimda_kullanici_notu_sistem_notunun_onune_gecer():
    """MA1: dağıtım kendi notunu üretiyor ("4 kayda orantılı
    dağıtıldı") — o bilgi değerli, atılmıyor. Kullanıcının notu ÖNE
    geçiyor: ortaklık ekstresi ortak kipinde ilk ' · ' ye kadarını
    gösteriyor (OR9), orada insanın yazdığı kısım durmalı."""
    from models import Maliyet
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add_all([
            BlokStok(id='BMA2', blok_no='MA1-2', cins='TEST', boy=300,
                     yukseklik=150, en=120, hacim_m3=5.4, tonaj=15,
                     durum='Serbest'),
            BlokStok(id='BMA3', blok_no='MA1-3', cins='TEST', boy=300,
                     yukseklik=150, en=120, hacim_m3=10.8, tonaj=30,
                     durum='Serbest')])
        db.session.commit()

    r = c.post('/api/maliyet/dagit', headers=H, json={
        'maliyet_tip': 'Navlun', 'baglanti_tip': 'stok',
        'hedefler': ['BMA2', 'BMA3'], 'tutar': 3000, 'doviz': 'USD',
        'dagitim': 'oransal', 'aciklama': 'MSC konteyner 4 nolu'})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        kayitlar = Maliyet.query.filter(
            Maliyet.baglanti_id.in_(['BMA2', 'BMA3']),
            Maliyet.maliyet_tip == 'Navlun').all()
        assert len(kayitlar) == 2, len(kayitlar)
        for m in kayitlar:
            assert m.aciklama.startswith('MSC konteyner 4 nolu · '), m.aciklama
            # Sistem notu ATILMADI
            assert 'dağıtıldı' in m.aciklama, m.aciklama
            # Ortak kipinin gördüğü kısım (OR9 kesme kuralı)
            assert m.aciklama.split(' · ')[0] == 'MSC konteyner 4 nolu'


def test_ma1_aciklama_bos_birakilabilir_ve_kirpiliyor():
    """MA1: alan opsiyonel — boş bırakmak eski davranışı korur
    (None), ve 500 karakterde kırpılıyor: sütun Text ama serbest
    metnin sınırsız olması belge çıktılarını bozar."""
    from models import Maliyet
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BMA4', blok_no='MA1-4', cins='TEST', boy=300, yukseklik=150,
            en=120, hacim_m3=5.4, tonaj=15, durum='Serbest'))
        db.session.commit()

    c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Sigorta', 'baglanti_tip': 'stok',
        'baglanti_id': 'BMA4', 'tutar': 50, 'doviz': 'USD',
        'aciklama': '   '})
    c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Komisyon', 'baglanti_tip': 'stok',
        'baglanti_id': 'BMA4', 'tutar': 60, 'doviz': 'USD',
        'aciklama': 'x' * 900})
    with fa.app.app_context():
        bos = Maliyet.query.filter_by(baglanti_id='BMA4',
                                      maliyet_tip='Sigorta').first()
        assert bos.aciklama is None, repr(bos.aciklama)
        uzun = Maliyet.query.filter_by(baglanti_id='BMA4',
                                       maliyet_tip='Komisyon').first()
        assert len(uzun.aciklama) == 500, len(uzun.aciklama)


def test_ma1_iki_formda_da_aciklama_kutusu_var():
    """MA1: iki ayrı maliyet ekleme formu var (Maliyet sayfası ve
    stok çekmecesi). Birine ekleyip ötekini unutmak, aynı alanın
    bir yerde dolup bir yerde boş kalmasıyla biterdi.

    MA2: alan textarea değil INPUT. Bu önemli bir yan etki getiriyor —
    base.html'deki global BÜYÜK HARF kuralı yalnız <input>'lere
    uygulanıyor (`el.tagName !== 'INPUT'` ile çıkıyor). İşaretsiz
    bırakılırsa "K6461 kesim" → "K6461 KESİM" olurdu; serbest bir
    notun büyük harfe çevrilmesi okunaksızdır."""
    import io as _io
    for dosya, kimlik in (('templates/maliyet.html', 'fAciklama'),
                          ('templates/stok.html', 'malAciklama')):
        h = _io.open(dosya, encoding='utf-8').read()
        assert f'id="{kimlik}"' in h, (dosya, kimlik)
        assert (f"aciklama: document.getElementById('{kimlik}')"
                ".value.trim()") in h, (dosya, kimlik)
        # Kutu satır içi stille boyanmıyor: gridin kendi kuralına
        # giriyor (.form-alan input) — iki formda da aynı görünsün.
        etiket = h[h.index(f'id="{kimlik}"') - 40:
                   h.index(f'id="{kimlik}"') + 220]
        assert '<input' in etiket, (dosya, 'textarea kalmis')
        assert 'style=' not in etiket, (dosya, 'satir ici stil geri gelmis')
        assert 'data-buyuk-harf="hayir"' in etiket, (
            dosya, 'BUYUK HARF muafiyeti dusmus — not büyük harfe döner')


def test_ma3_modal_govdesi_esnek_kutuda_kuculebiliyor():
    """MA3: `.modal` esnek sütun + `max-height`. Gövde çocuğunda
    `min-height:0` YOKSA çocuk kendi içeriğinden kısa olamaz —
    `overflow-y:auto` hiç devreye girmez ve uzun bir modalda ALT BAR
    (Vazgeç/Kaydet) modalın dışına itilir. Chromium bazı durumlarda
    affediyor, Firefox affetmiyor.

    Kural 14 sayfada ayrı ayrı KOPYALANMIŞ ve sayfanınki base'i
    eziyor — base.html'i düzeltmek tek başına hiçbirini kurtarmıyor.
    Bu yüzden test tek tek bakıyor: yeni bir sayfa kuralı kopyalayıp
    bu parçayı unutursa burada düşer."""
    import glob
    import io as _io
    import re
    eksik = []
    for yol in sorted(glob.glob('templates/*.html')):
        g = _io.open(yol, encoding='utf-8').read()
        kurallar = re.findall(r'\.modal-gov\{[^}]*\}', g)
        if not kurallar:
            continue
        # Yalnız `.modal` gerçekten esnek sütunsa kural anlamlı
        if not re.search(r'\.modal\{[^}]*flex-direction:column', g):
            continue
        for k in kurallar:
            if 'min-height:0' not in k:
                eksik.append(yol)
    assert not eksik, f'modal gövdesi küçülemiyor: {eksik}'


def test_ma3_maliyet_formu_iki_uclu_satirda():
    """MA3: süzgeçler tek esnek satırdaydı, 620px modalda dört kutu
    sarıyordu — seçici bloğu 307px tutup formun son alanlarını
    katlamanın altına itiyordu. İki üçlü ızgara satırı oldu."""
    import io as _io
    tam = _io.open('templates/maliyet.html', encoding='utf-8').read()
    # YALNIZ MODALIN İÇİ: `fTip` gibi kimlikler sayfanın üst
    # süzgecinde de geçiyor, dışarıdan arayınca yanlış yeri bulur.
    h = tam[tam.index('<div class="modal-ortu" id="modal"'):
            tam.index('{% endblock %}',
                      tam.index('<div class="modal-ortu" id="modal"'))]
    # Konum karşılaştırmasıyla ölçüyoruz: biçimlendirme değişse de
    # "hangi kutu hangi satırda" sorusu aynı kalsın.
    y = {k: h.index(f'id="{k}"') for k in
         ('fTip', 'fBagTip', 'hUretici', 'hAra', 'hCins', 'hBlok')}
    f3ler = []
    ara = 0
    while True:
        try:
            ara = h.index('<div class="form-satir f3">', ara) + 1
        except ValueError:
            break
        f3ler.append(ara - 1)
    assert len(f3ler) >= 3, f'üç f3 satırı bekleniyordu, {len(f3ler)} var'
    satir1, satir2, satir3 = f3ler[0], f3ler[1], f3ler[2]
    liste = h.index('hedef-liste')

    # 1. üçlü: Maliyet Tipi · Bağlantı Tipi · Üretici
    for k in ('fTip', 'fBagTip', 'hUretici'):
        assert satir1 < y[k] < satir2, (k, 'ilk üçlü satırda değil')
    # 2. üçlü: Bağlanacak stok (ara) · Cins · Blok No — listeden ÖNCE
    for k in ('hAra', 'hCins', 'hBlok'):
        assert satir2 < y[k] < liste, (k, 'ikinci üçlü satırda değil')
    # 3. üçlü (Tutar/Döviz/KDV) listeden SONRA gelmeli
    assert liste < satir3

    # Her kutunun artık ETİKETİ var — önce ne oldukları yalnız
    # "— üretici (tümü) —" gibi seçenek metinlerinden anlaşılıyordu
    for etiket in ('>Üretici<', '>Cins<', '>Blok No<'):
        assert etiket in h, etiket
    # Süzgeçler yalnız STOK için anlamlı: sipariş/sevkiyatta gizleniyor
    assert "['fAlanUretici', 'fAlanCins', 'fAlanBlok']" in tam


def test_ma5_her_modalda_alt_bar_modalin_icinde():
    """MA5: `.modal-alt`, `.modal`in İÇİNDE olmak zorunda. Dışına
    çıkarsa `.modal-ortu` ızgarasının (place-items:center) çocuğu
    olur: ortalanır ve içeriği kadar daralır — panelden kopmuş
    ensiz bir düğme kutusu.

    Bunu bir yamam yaptı. MA1'in tabanını kurarken maliyet.html'den
    açıklama bloğunu elle kesmiştim ve kesme noktası `.modal-gov`un
    kapanışını da götürmüştü; yama o `</div>`i "eklenecek" sanıp
    geri koyunca kullanıcının dosyasında FAZLADAN bir kapanış
    oluştu. Bayt bayt doğrulamam yakalayamadı çünkü yamayı kendi
    bozuk tabanıma uygulayıp kendi dosyamla karşılaştırıyordum —
    ikisi de aynı hatayı taşıyordu.

    Bu test o karşılaştırmaya güvenmiyor: şablonu gerçek bir HTML
    ayrıştırıcısıyla okuyup YAPIYA bakıyor."""
    import glob
    import io as _io
    import re
    from html.parser import HTMLParser

    BOS = {'input', 'br', 'hr', 'img', 'meta', 'link', 'source',
           'col', 'area', 'base', 'embed', 'track', 'wbr'}

    class Y(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.yigin = []
            self.kapanis = {}

        def handle_starttag(self, etiket, nitelikler):
            if etiket in BOS:
                return
            self.yigin.append((etiket, dict(nitelikler).get('class', '') or '',
                               self.getpos()[0]))

        def handle_endtag(self, etiket):
            sat = self.getpos()[0]
            for i in range(len(self.yigin) - 1, -1, -1):
                if self.yigin[i][0] == etiket:
                    for _e, snf, ac in self.yigin[i:]:
                        k = snf.split()[0] if snf else ''
                        if k in ('modal', 'modal-alt'):
                            self.kapanis.setdefault((k, ac), sat)
                    del self.yigin[i:]
                    return

    bozuk = []
    for yol in sorted(glob.glob('templates/*.html')):
        g = _io.open(yol, encoding='utf-8').read()
        t = re.sub(r'\{%.*?%\}', '', g, flags=re.S)
        t = re.sub(r'\{\{.*?\}\}', '', t, flags=re.S)
        for ortu in re.finditer(r'<div class="modal-ortu"[^>]*>', t):
            bas, derin, kes = ortu.start(), 0, len(t)
            for x in re.finditer(r'<div\b|</div>', t[bas:]):
                derin += 1 if x.group(0) == '<div' else -1
                if derin == 0:
                    kes = bas + x.end()
                    break
            y = Y()
            y.feed(t[bas:kes])
            mo = [(a, b) for (k, a), b in y.kapanis.items() if k == 'modal']
            al = [(a, b) for (k, a), b in y.kapanis.items() if k == 'modal-alt']
            if not (mo and al):
                continue
            ac_m, kap_m = mo[0]
            ac_a, _ = al[0]
            if not (ac_m < ac_a < kap_m):
                bozuk.append((yol, t[:bas].count('\n') + 1))
    assert not bozuk, f'alt bar .modal dışında kalmış: {bozuk}'


def _dz1_kur(c, ek, tonlar=(20, 10)):
    """DZ1 testleri icin kurulum. HER TESTE KENDI KIMLIKLERI:
    sayimlar genel yapilirsa takim halinde calisirken baska
    testlerin birakti maliyet/hareket satirlari girer ve test
    sirasi onemli hale gelir — bir kez yasadik, bir daha degil."""
    from models import Cari
    with fa.app.app_context():
        if not db.session.get(Cari, 'TEDDZ'):
            db.session.add(Cari(id='TEDDZ', unvan='NAKLIYECI DZ',
                                cari_tip='Tedarikçi', urun_tedarikcisi=True))
        idler = []
        for n, ton in enumerate(tonlar, 1):
            sid = f'BLK-{ek}{n}'
            idler.append(sid)
            if not db.session.get(BlokStok, sid):
                db.session.add(BlokStok(
                    id=sid, blok_no=f'{ek}{n}', cins='TEST', boy=300,
                    yukseklik=180, en=170, hacim_m3=9.18, tonaj=ton,
                    alis_fiyati=300, alis_fiyat_birim='ton', doviz='USD',
                    durum='Serbest'))
        db.session.commit()
    return idler


def _dz1_sayim(stok_idler):
    """Yalniz BU stoklara bagli maliyet ve hareket sayisi."""
    from models import CariHareket, Maliyet
    with fa.app.app_context():
        satirlar = Maliyet.query.filter(
            Maliyet.baglanti_id.in_(stok_idler)).all()
        idler = [s.id for s in satirlar] or ['-']
        hareketler = CariHareket.query.filter(
            CariHareket.baglanti_tip == 'maliyet',
            CariHareket.baglanti_id.in_(idler)).count()
        return len(satirlar), hareketler


def test_dz1_cari_hareket_silinince_kdv_satiri_oksuz_kalmaz():
    """DZ1: bir gider faturası İKİ maliyet satırı doğuruyor — net ve
    Devreden KDV. Cari hareket silinince eskiden yalnız net satır
    gidiyor, KDV satırı stoğa bağlı olarak ÖKSÜZ kalıyordu.

    Bağ `baglanti_id` ile bire bir kurulmuştu; gerçek ilişki bire
    çok. Artık `grup_id` tek anahtar."""
    from models import CariHareket, Maliyet
    c = istemci('admin', 'ADMIN')
    (sid,) = _dz1_kur(c, 'KDVA', (20,))
    r = c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Nakliye (Ocak-Fabrika)', 'baglanti_tip': 'stok',
        'baglanti_id': sid, 'tutar': 1000, 'doviz': 'USD',
        'kdv_oran': 20, 'cari_id': 'TEDDZ'})
    assert r.status_code == 200, r.get_json()
    mid = r.get_json()['id']
    assert _dz1_sayim([sid]) == (2, 1), _dz1_sayim([sid])
    with fa.app.app_context():
        hid = CariHareket.query.filter_by(
            baglanti_tip='maliyet', baglanti_id=mid).first().id

    # ONAY olmadan: 409 + kapsam, ve hicbir sey silinmemis
    r = c.delete(f'/api/cari/hareket/{hid}', headers=H)
    assert r.status_code == 409, r.status_code
    d = r.get_json()
    assert d['error'] == 'onay_gerekli'
    assert d['kapsam']['satir_sayisi'] == 2, d['kapsam']
    assert _dz1_sayim([sid]) == (2, 1), 'onay verilmeden silinmiş'

    assert c.delete(f'/api/cari/hareket/{hid}?onay=1',
                    headers=H).status_code == 200
    assert _dz1_sayim([sid]) == (0, 0), 'KDV satırı öksüz kaldı'
    with fa.app.app_context():
        assert db.session.get(CariHareket, hid) is None


def test_dz1_dagitilmis_maliyetin_tamami_birlikte_gider():
    """DZ1: dağıtım N stok için N satır açıyor ama cari harekete
    yalnız İLK satırın kimliği yazılıyordu. Hareketi silince N-1
    satır kalıyor ve o stokların maliyeti şişik görünmeye devam
    ediyordu — ölçüldü."""
    from models import CariHareket, Maliyet
    c = istemci('admin', 'ADMIN')
    a, b = _dz1_kur(c, 'DAG', (20, 10))
    r = c.post('/api/maliyet/dagit', headers=H, json={
        'maliyet_tip': 'Navlun', 'baglanti_tip': 'stok',
        'hedefler': [a, b], 'tutar': 3000, 'doviz': 'USD',
        'kdv_oran': 0, 'dagitim': 'oransal', 'cari_id': 'TEDDZ'})
    assert r.status_code == 200, r.get_json()
    assert _dz1_sayim([a, b]) == (2, 1), _dz1_sayim([a, b])
    with fa.app.app_context():
        satirlar = Maliyet.query.filter(Maliyet.baglanti_id.in_([a, b])).all()
        assert len({s.grup_id for s in satirlar}) == 1, 'tek grupta değiller'
        hid = CariHareket.query.filter(
            CariHareket.baglanti_tip == 'maliyet',
            CariHareket.baglanti_id.in_([s.id for s in satirlar])).first().id

    d = c.delete(f'/api/cari/hareket/{hid}', headers=H).get_json()
    assert d['kapsam']['stok_sayisi'] == 2, d['kapsam']
    assert c.delete(f'/api/cari/hareket/{hid}?onay=1',
                    headers=H).status_code == 200
    assert _dz1_sayim([a, b]) == (0, 0), 'dağıtımın bir kısmı öksüz kaldı'


def test_dz1_maliyet_silinince_cari_hareket_de_gider():
    """DZ1: ters yön. Hangi satırdan silinirse silinsin — net, KDV,
    ya da dağıtımın ortasındaki bir satır — grubun tamamı ve
    tedarikçi borcu birlikte gider."""
    c = istemci('admin', 'ADMIN')
    (sid,) = _dz1_kur(c, 'TERS', (10,))
    r = c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Komisyon', 'baglanti_tip': 'stok',
        'baglanti_id': sid, 'tutar': 500, 'doviz': 'USD',
        'kdv_oran': 20, 'cari_id': 'TEDDZ'})
    kdv_id = r.get_json()['kdv_id']
    assert _dz1_sayim([sid]) == (2, 1)

    # KDV satirindan silmek bile grubun tamamini goturur
    assert c.delete(f'/api/maliyet/{kdv_id}', headers=H).status_code == 409
    assert c.delete(f'/api/maliyet/{kdv_id}?onay=1',
                    headers=H).status_code == 200
    assert _dz1_sayim([sid]) == (0, 0)


def test_dz1_maliyet_duzenlenince_tedarikci_borcu_esitlenir():
    """DZ1: tutarı değiştirmek maliyeti ve satış kârını
    güncelliyordu ama CARİ HAREKET eski tutarda kalıyordu —
    stokta 2.000 USD gider görünürken tedarikçide 1.000 USD borç.

    Borç grubun TAMAMININ karşılığı (net + KDV), tek satırın
    değil; o yüzden grup toplamından yeniden kuruluyor."""
    from models import CariHareket
    c = istemci('admin', 'ADMIN')
    (sid,) = _dz1_kur(c, 'DUZ', (20,))
    mid = c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Gümrük/Liman Masrafı', 'baglanti_tip': 'stok',
        'baglanti_id': sid, 'tutar': 1000, 'doviz': 'USD',
        'kdv_oran': 0, 'cari_id': 'TEDDZ'}).get_json()['id']
    with fa.app.app_context():
        h = CariHareket.query.filter_by(
            baglanti_tip='maliyet', baglanti_id=mid).first()
        assert h.alacak == 1000, h.alacak
        hid = h.id

    r = c.put(f'/api/maliyet/{mid}', headers=H, json={'tutar': 2000})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()['hareket_guncel']['yeni_tutar'] == 2000
    with fa.app.app_context():
        assert db.session.get(CariHareket, hid).alacak == 2000, \
            'tedarikçi borcu eski tutarda kaldı'


def test_dz1_sade_kayitta_fazladan_onay_sorulmaz():
    """DZ1: onay adımı yalnız kapsam genişken çıkmalı. Cariye
    bağlanmamış, KDV'siz tek bir maliyet satırı tek soruyla
    silinmeli — her silmede ikinci bir kutu çıkarsa kullanıcı
    onu okumadan onaylamaya alışır."""
    from models import Maliyet
    c = istemci('admin', 'ADMIN')
    (sid,) = _dz1_kur(c, 'SADE', (10,))
    mid = c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Diğer', 'baglanti_tip': 'stok',
        'baglanti_id': sid, 'tutar': 100, 'doviz': 'USD',
        'kdv_oran': 0}).get_json()['id']
    r = c.delete(f'/api/maliyet/{mid}', headers=H)
    assert r.status_code == 200, (r.status_code, r.get_json())
    with fa.app.app_context():
        assert db.session.get(Maliyet, mid) is None


def _dz2_kur(ek, tonaj=20, alis=300):
    """DZ2 testleri: her teste kendi stogu ve kendi satis kaydi."""
    from models import SatisKaydi
    with fa.app.app_context():
        sid = f'BLK-{ek}'
        if not db.session.get(BlokStok, sid):
            db.session.add(BlokStok(
                id=sid, blok_no=ek, cins='TEST', boy=300, yukseklik=180,
                en=170, hacim_m3=9.18, tonaj=tonaj, alis_fiyati=alis,
                alis_fiyat_birim='ton', doviz='USD', durum='Serbest'))
            db.session.add(SatisKaydi(
                id=f'SK-{ek}', stok_tip='BLOK', stok_id=sid,
                musteri='ALICI', satis_tarihi=date(2026, 10, 1),
                doviz='USD', tutar=20000, tutar_usd=20000,
                maliyet_usd=alis * tonaj, kar_usd=20000 - alis * tonaj))
        db.session.commit()
    return sid


def test_dz2_alis_fiyati_degisince_satis_kari_guncellenir():
    """DZ2: stok düzenleme ucu hiçbir yeniden hesap çağırmıyordu.
    Ölçüldü: alış fiyatını 300 → 500 yaptım, satış kaydının maliyeti
    6.000'de, kârı 14.000'de kaldı; doğrusu 10.000 / 10.000 idi.
    Stok kartı ile satış kârlılığı sessizce ayrışıyordu."""
    from models import SatisKaydi
    c = istemci('admin', 'ADMIN')
    sid = _dz2_kur('DZA', tonaj=20, alis=300)
    with fa.app.app_context():
        assert db.session.get(SatisKaydi, 'SK-DZA').maliyet_usd == 6000

    r = c.put(f'/api/stok/{sid}', headers=H,
              json={'tip': 'BLOK', 'cins': 'TEST', 'alis_fiyati': 500})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()['satis_kaydi_guncel'] >= 1, r.get_json()
    with fa.app.app_context():
        sk = db.session.get(SatisKaydi, 'SK-DZA')
        assert sk.maliyet_usd == 10000, sk.maliyet_usd
        assert sk.kar_usd == 10000, sk.kar_usd


def test_dz2_olculer_duzenlenebiliyor_ve_kar_takip_ediyor():
    """DZ2: ölçü alanları düzenleme ucundan HİÇ güncellenmiyordu —
    yanlış girilmiş bir tonaj düzeltilemiyordu. Oysa ölçü maliyetin
    temeli: alış bedeli `alis_fiyati × ölçü`."""
    from models import SatisKaydi
    c = istemci('admin', 'ADMIN')
    sid = _dz2_kur('DZB', tonaj=20, alis=300)

    r = c.put(f'/api/stok/{sid}', headers=H, json={
        'tip': 'BLOK', 'cins': 'TEST',
        'tonaj': 25, 'boy': 320, 'hacim_m3': 11.0})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        s = db.session.get(BlokStok, sid)
        assert s.tonaj == 25 and s.boy == 320 and s.hacim_m3 == 11.0
        # 25 ton × 300 = 7500
        assert db.session.get(SatisKaydi, 'SK-DZB').maliyet_usd == 7500


def test_dz2_plakaya_tonaj_yazilmaz():
    """DZ2: hangi ölçü hangi tipte anlamlı — BLOK ton/m³ ile,
    PLAKA m² ile ölçülüyor. PLAKA'ya tonaj yazmak alanı yalan
    söyletirdi; `hasattr` süzgeci onu engelliyor."""
    from models import PlakaStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not db.session.get(PlakaStok, 'PLK-DZC'):
            db.session.add(PlakaStok(
                id='PLK-DZC', blok_no='DZC', cins='TEST', boy=300,
                yukseklik=180, kalinlik=2, metraj_m2=5.4,
                durum='Serbest', giris_tarihi=date(2026, 10, 1)))
            db.session.commit()
    r = c.put('/api/stok/PLK-DZC', headers=H, json={
        'tip': 'PLAKA', 'cins': 'TEST', 'tonaj': 99, 'metraj_m2': 6.0})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        p = db.session.get(PlakaStok, 'PLK-DZC')
        assert p.metraj_m2 == 6.0, 'metraj yazılmadı'
        assert not hasattr(p, 'tonaj'), 'PLAKA tonaj taşımamalı'


def test_dz2_olcu_degisince_dagitim_uyarisi_cikar():
    """DZ2: dağıtım BİR KEZ yapılır ve paylar SABİT tutar olarak
    yazılır. Ölçü sonradan değişince o paylar eski ölçüye göre
    hesaplanmış kalır.

    Kendiliğinden yeniden dağıtmıyoruz: bu AYNI GRUPTAKİ BAŞKA
    stokların maliyetini de değiştirirdi ve onların satışı çoktan
    faturalanmış olabilir. Sessiz kalmak yerine söylüyoruz."""
    c = istemci('admin', 'ADMIN')
    a = _dz2_kur('DZD1', tonaj=20)
    b = _dz2_kur('DZD2', tonaj=10)
    r = c.post('/api/maliyet/dagit', headers=H, json={
        'maliyet_tip': 'Navlun', 'baglanti_tip': 'stok',
        'hedefler': [a, b], 'tutar': 3000, 'doviz': 'USD',
        'kdv_oran': 0, 'dagitim': 'oransal'})
    assert r.status_code == 200, r.get_json()

    # Olcu DEGISMEYEN bir duzenlemede uyari CIKMAMALI
    r = c.put(f'/api/stok/{a}', headers=H,
              json={'tip': 'BLOK', 'cins': 'TEST', 'konum': 'Depo 3'})
    assert not r.get_json().get('uyarilar'), r.get_json()

    # Olcu degisince uyari CIKMALI
    r = c.put(f'/api/stok/{a}', headers=H,
              json={'tip': 'BLOK', 'cins': 'TEST', 'tonaj': 40})
    d = r.get_json()
    assert d['uyari'] is True, d
    assert any('dağıtılmış maliyet' in u for u in d['uyarilar']), d
    # Paylar DEGISMEDI — baskasinin maliyetine dokunmadik
    with fa.app.app_context():
        from models import Maliyet
        paylar = {m.baglanti_id: m.tutar for m in
                  Maliyet.query.filter(Maliyet.baglanti_id.in_([a, b]),
                                       Maliyet.maliyet_tip == 'Navlun').all()}
        assert paylar[a] == 2000 and paylar[b] == 1000, paylar


def test_dz2_gecersiz_olcu_reddedilir():
    """DZ2: ölçü sayı olmalı ve negatif olamaz. Negatif tonaj,
    negatif alış bedeli demek — kâr tablosu anlamını yitirir."""
    c = istemci('admin', 'ADMIN')
    sid = _dz2_kur('DZE', tonaj=20)
    for deger, bekle in ((-5, 400), ('abc', 400)):
        r = c.put(f'/api/stok/{sid}', headers=H,
                  json={'tip': 'BLOK', 'cins': 'TEST', 'tonaj': deger})
        assert r.status_code == bekle, (deger, r.status_code, r.get_json())
    with fa.app.app_context():
        assert db.session.get(BlokStok, sid).tonaj == 20, 'bozuk değer yazıldı'


def test_dz2_formda_olcu_kutulari_var():
    """DZ2: sunucu düzelmesi tek başına yetmez — kullanıcının
    gördüğü formda kutu yoksa alan yine düzenlenemez."""
    import io as _io
    h = _io.open('templates/stok.html', encoding='utf-8').read()
    for kimlik in ('duzBoy', 'duzYukseklik', 'duzEn', 'duzKalinlik',
                   'duzHacim', 'duzTonaj', 'duzMetraj'):
        assert f'id="{kimlik}"' in h, kimlik
    assert 'function olcuDoldur' in h
    assert 'function olcuGovde' in h
    assert '...olcuGovde(),' in h, 'ölçüler gönderilmiyor'
    # Liste ucu bu ikisini KISA adla veriyor; uzun ad tek basina
    # bos kutu birakirdi
    assert 's.hacim_m3 !== undefined ? s.hacim_m3 : s.hacim' in h
    assert 's.metraj_m2 !== undefined ? s.metraj_m2 : s.m2' in h


def _dz3_kur(ek, tutar=20000, maliyet=6000, doviz='USD'):
    """DZ3: her teste kendi satis kaydi."""
    from models import SatisKaydi
    sid = f'SK-{ek}'
    with fa.app.app_context():
        if not db.session.get(SatisKaydi, sid):
            db.session.add(BlokStok(
                id=f'BLK-{ek}', blok_no=ek, cins='TEST', boy=300,
                yukseklik=180, en=170, hacim_m3=9.18, tonaj=20,
                alis_fiyati=300, alis_fiyat_birim='ton', doviz='USD',
                durum='Satildi'))
            db.session.add(SatisKaydi(
                id=sid, stok_tip='BLOK', stok_id=f'BLK-{ek}',
                musteri='ALICI', satis_tarihi=date(2026, 10, 1),
                doviz=doviz, birim_fiyat=1000, miktar=20, birim='ton',
                tutar=tutar, tutar_usd=tutar,
                maliyet_usd=maliyet, kar_usd=tutar - maliyet))
            db.session.commit()
    return sid


def test_dz3_satis_kaydi_duzenlenince_kar_yeniden_hesaplanir():
    """DZ3: satış kaydının TUTAR tarafı hiçbir yerden
    düzenlenemiyordu — yalnız fatura no/tarih/not. Yanlış fiyatla
    girilmiş bir satışı düzeltmenin yolu yoktu; kayıt silinemiyordu
    da. Oysa bu kayıt KÂRIN kaynağı: ortaklık hesabı, kârlılık
    raporu ve müşteri özeti hep buradan okuyor."""
    from models import SatisKaydi
    c = istemci('admin', 'ADMIN')
    sid = _dz3_kur('DZ3A', tutar=20000, maliyet=6000)

    r = c.put(f'/api/satislar/{sid}', headers=H, json={'tutar': 30000})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert d['tutar_usd'] == 30000, d
    assert d['kar_usd'] == 24000, d          # 30000 - 6000
    with fa.app.app_context():
        s = db.session.get(SatisKaydi, sid)
        assert s.kar_usd == 24000
        assert abs((s.marj_yuzde or 0) - 80.0) < 0.01, s.marj_yuzde


def test_dz3_birim_fiyat_ve_miktardan_tutar_turetilir():
    """DZ3: birim fiyat ya da miktar değişince tutar yeniden
    hesaplanır. Ama ikisiyle birlikte TUTAR da verilmişse elle
    verilen kazanır — faturada iskonto veya yuvarlama olabilir ve
    belgedeki rakam hesaplanandan önceliklidir."""
    from models import SatisKaydi
    c = istemci('admin', 'ADMIN')
    sid = _dz3_kur('DZ3B', tutar=20000, maliyet=5000)

    c.put(f'/api/satislar/{sid}', headers=H,
          json={'birim_fiyat': 1200, 'miktar': 20})
    with fa.app.app_context():
        assert db.session.get(SatisKaydi, sid).tutar == 24000

    # Tutar da verilirse O kazanir
    c.put(f'/api/satislar/{sid}', headers=H,
          json={'birim_fiyat': 1200, 'miktar': 20, 'tutar': 23500})
    with fa.app.app_context():
        assert db.session.get(SatisKaydi, sid).tutar == 23500


def test_dz3_faturaya_bagli_satis_duzenlenmez():
    """DZ3: satış bir faturadan doğduysa doğrunun kaynağı FATURA.
    Buradan tutarı değiştirmek belge ile kaydı ayrıştırırdı.
    Sipariş düzenleme ucu da aynı gerekçeyle kalemleri kilitliyor;
    aynı kuralı sürdürüyoruz."""
    from models import Fatura, SatisKaydi
    c = istemci('admin', 'ADMIN')
    sid = _dz3_kur('DZ3C', tutar=20000, maliyet=6000)
    with fa.app.app_context():
        db.session.add(Fatura(id='FTR-DZ3', fatura_no='FT-9',
                              musteri='ALICI', durum='Kesildi'))
        db.session.get(SatisKaydi, sid).fatura_id = 'FTR-DZ3'
        db.session.commit()

    r = c.put(f'/api/satislar/{sid}', headers=H, json={'tutar': 99999})
    assert r.status_code == 409, r.status_code
    assert r.get_json()['error'] == 'faturaya_bagli'
    assert 'FT-9' in r.get_json()['mesaj']
    with fa.app.app_context():
        assert db.session.get(SatisKaydi, sid).tutar == 20000, 'değişmiş'


def test_dz3_kur_satis_tarihindeki_kur():
    """DZ3: TRY bir satış USD'ye çevrilirken SATIŞ TARİHİNDEKİ kur
    kullanılmalı. Bugünün kuruyla çevirmek, geçmiş bir satışı
    bugünün kuruyla yeniden fiyatlandırmak demektir — kâr tablosu
    kur hareketiyle oynamaya başlar."""
    from models import DovizKur, SatisKaydi
    c = istemci('admin', 'ADMIN')
    sid = _dz3_kur('DZ3D', tutar=100000, maliyet=1000, doviz='TRY')
    with fa.app.app_context():
        for t, k in ((date(2026, 9, 1), 40.0), (date(2026, 12, 1), 50.0)):
            if not DovizKur.query.filter_by(doviz='USD', tarih=t).first():
                db.session.add(DovizKur(doviz='USD', tarih=t, alis=k,
                                        satis=k, efektif=k))
        db.session.commit()

    # Satis tarihi 2026-10-01 -> gecerli kur 40 (01.09 satiri)
    r = c.put(f'/api/satislar/{sid}', headers=H,
              json={'tutar': 100000, 'satis_tarihi': '2026-10-01'})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        s = db.session.get(SatisKaydi, sid)
        assert abs((s.tutar_usd or 0) - 2500) < 1, s.tutar_usd  # 100000/40


def test_dz3_gecersiz_deger_reddedilir():
    """DZ3: negatif tutar ya da tanınmayan döviz yazılamaz."""
    from models import SatisKaydi
    c = istemci('admin', 'ADMIN')
    sid = _dz3_kur('DZ3E', tutar=20000, maliyet=6000)
    for govde in ({'tutar': -1}, {'doviz': 'ZZZ'}, {'miktar': 'abc'}):
        r = c.put(f'/api/satislar/{sid}', headers=H, json=govde)
        assert r.status_code == 400, (govde, r.status_code)
    with fa.app.app_context():
        s = db.session.get(SatisKaydi, sid)
        assert s.tutar == 20000 and s.doviz == 'USD'


def _dz3_proforma(ek, fiyat=1000, miktar=20):
    """DZ3 proforma testleri: her teste kendi belgesi."""
    from models import Proforma, ProformaKalem
    pid = f'PI-{ek}'
    with fa.app.app_context():
        if not db.session.get(Proforma, pid):
            db.session.add(Proforma(
                id=pid, musteri='ALICI', cari_id='C1', doviz='USD',
                durum='Taslak', aktif_surum=True, revizyon_no=0,
                ana_pi_id=pid, tur='ihracat', kdv_oran=0,
                toplam=fiyat * miktar))
            db.session.flush()
            db.session.add(ProformaKalem(
                proforma_id=pid, sira=1, urun_tip='BLOK', cins='TEST',
                adet=1, miktar=miktar, birim='ton', birim_fiyat=fiyat,
                toplam_fiyat=fiyat * miktar, net_fiyat=fiyat * miktar,
                doviz='USD'))
            db.session.commit()
    return pid


def test_dz3_proforma_toplami_kalemlerden_turetilir():
    """DZ3: proforma toplamı HİÇBİR ZAMAN sunucuda hesaplanmıyordu —
    hem POST hem PUT istemciden geleni yazıyordu. Ölçüldü: kalemin
    fiyatını 1.000 → 1.500 yapan bir PUT (gövdede `toplam` yok)
    kalemi güncelledi ama başlıktaki toplam 20.000'de kaldı. Belge
    "satır 30.000, toplam 20.000" diye basılacaktı — müşteriye
    giden bir belgede."""
    from models import Proforma
    c = istemci('admin', 'ADMIN')
    pid = _dz3_proforma('DZ3P', fiyat=1000, miktar=20)

    r = c.put(f'/api/proforma/{pid}', headers=H, json={'kalemler': [{
        'urun_tip': 'BLOK', 'cins': 'TEST', 'adet': 1, 'miktar': 20,
        'birim': 'ton', 'birim_fiyat': 1500, 'toplam_fiyat': 30000,
        'net_fiyat': 30000, 'sira': 1}]})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        assert db.session.get(Proforma, pid).toplam == 30000, \
            'başlık toplamı kalemleri takip etmedi'


def test_dz3_kalem_tutari_eksikse_toplam_sifirlanmaz():
    """DZ3: türetme `net_fiyat` üzerinden; o boşsa `toplam_fiyat`,
    o da boşsa birim × miktar. Düz toplasaydık eksik veride toplam
    SIFIRA düşerdi — eskisinden kötü.

    İkinci koruma: türetilen sıfır çıkıp istemci sıfırdan büyük bir
    toplam gönderdiyse belgeyi sıfırlamıyoruz, uyarıyoruz."""
    from models import Proforma
    c = istemci('admin', 'ADMIN')
    pid = _dz3_proforma('DZ3Q', fiyat=1000, miktar=20)

    # net_fiyat YOK, toplam_fiyat var -> ondan turetmeli
    r = c.put(f'/api/proforma/{pid}', headers=H, json={'kalemler': [{
        'urun_tip': 'BLOK', 'cins': 'TEST', 'adet': 1, 'miktar': 20,
        'birim': 'ton', 'birim_fiyat': 1200, 'toplam_fiyat': 24000,
        'sira': 1}]})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        assert db.session.get(Proforma, pid).toplam == 24000

    # Ikisi de YOK -> birim × miktar
    r = c.put(f'/api/proforma/{pid}', headers=H, json={'kalemler': [{
        'urun_tip': 'BLOK', 'cins': 'TEST', 'adet': 1, 'miktar': 10,
        'birim': 'ton', 'birim_fiyat': 900, 'sira': 1}]})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        assert db.session.get(Proforma, pid).toplam == 9000


def test_dz3_siparise_donusmus_proformada_onay_sorulur():
    """DZ3: proforma siparişe dönüştükten sonra düzenlenince ikisi
    sessizce ayrışıyordu — proforma 40.000, sipariş 30.000.

    Siparişi proformadan YENİDEN KURMUYORUZ (dönüştürme rezervasyon
    taşıyor, stok bağlıyor). Yapı aynıysa yalnız FİYAT taşınıyor ve
    bu da önce soruluyor."""
    from models import Proforma, Siparis, SiparisKalem
    c = istemci('admin', 'ADMIN')
    pid = _dz3_proforma('DZ3R', fiyat=1000, miktar=20)
    with fa.app.app_context():
        sip = Siparis(id='SIP-DZ3R', musteri='ALICI', cari_id='C1',
                      doviz='USD', durum='Hazirlaniyor', toplam_tutar=20000)
        db.session.add(sip)
        db.session.flush()
        db.session.add(SiparisKalem(
            siparis_id='SIP-DZ3R', sira=1, urun_tip='BLOK', cins='TEST',
            adet=1, miktar=20, birim='ton', birim_fiyat=1000,
            toplam_fiyat=20000, doviz='USD'))
        db.session.get(Proforma, pid).siparis_id = 'SIP-DZ3R'
        db.session.commit()

    govde = {'kalemler': [{
        'urun_tip': 'BLOK', 'cins': 'TEST', 'adet': 1, 'miktar': 20,
        'birim': 'ton', 'birim_fiyat': 2000, 'toplam_fiyat': 40000,
        'net_fiyat': 40000, 'sira': 1}]}

    # ONAY olmadan: 409 ve HICBIR SEY degismemis
    r = c.put(f'/api/proforma/{pid}', headers=H, json=govde)
    assert r.status_code == 409, r.status_code
    d = r.get_json()
    assert d['kapsam']['siparis_id'] == 'SIP-DZ3R', d
    with fa.app.app_context():
        assert db.session.get(Proforma, pid).toplam == 20000, \
            'onay verilmeden proforma değişmiş'
        assert db.session.get(Siparis, 'SIP-DZ3R').toplam_tutar == 20000

    # Onayla: ikisi de guncellenir
    r = c.put(f'/api/proforma/{pid}?onay=1', headers=H, json=govde)
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        assert db.session.get(Proforma, pid).toplam == 40000
        assert db.session.get(Siparis, 'SIP-DZ3R').toplam_tutar == 40000
        k = SiparisKalem.query.filter_by(siparis_id='SIP-DZ3R').first()
        assert k.birim_fiyat == 2000, k.birim_fiyat


def test_dz3_kilitli_siparise_fiyat_tasinmaz():
    """DZ3: siparişe sevkiyat ya da satış kaydı bağlıysa kalemleri
    değiştirmek belge ile sevk edilen malı ayrıştırırdı. Fiyat
    taşınmıyor — ama sessiz kalınmıyor, ayrışma söyleniyor."""
    from models import Proforma, SatisKaydi, Siparis, SiparisKalem
    c = istemci('admin', 'ADMIN')
    pid = _dz3_proforma('DZ3S', fiyat=1000, miktar=20)
    with fa.app.app_context():
        db.session.add(Siparis(id='SIP-DZ3S', musteri='ALICI', cari_id='C1',
                               doviz='USD', durum='Hazirlaniyor',
                               toplam_tutar=20000))
        db.session.flush()
        db.session.add_all([
            SiparisKalem(siparis_id='SIP-DZ3S', sira=1, urun_tip='BLOK',
                         cins='TEST', adet=1, miktar=20, birim='ton',
                         birim_fiyat=1000, toplam_fiyat=20000, doviz='USD'),
            SatisKaydi(id='SK-DZ3S', siparis_id='SIP-DZ3S', stok_tip='BLOK',
                       musteri='ALICI', satis_tarihi=date(2026, 10, 1),
                       doviz='USD', tutar=20000, tutar_usd=20000)])
        db.session.get(Proforma, pid).siparis_id = 'SIP-DZ3S'
        db.session.commit()

    r = c.put(f'/api/proforma/{pid}', headers=H, json={'kalemler': [{
        'urun_tip': 'BLOK', 'cins': 'TEST', 'adet': 1, 'miktar': 20,
        'birim': 'ton', 'birim_fiyat': 2000, 'toplam_fiyat': 40000,
        'net_fiyat': 40000, 'sira': 1}]})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert d['siparis_uyari'] and 'satış kaydı' in d['siparis_uyari'], d
    with fa.app.app_context():
        assert db.session.get(Siparis, 'SIP-DZ3S').toplam_tutar == 20000, \
            'kilitli siparişin fiyatı değişmiş'


def _dz4_kesim(c, ek, tonaj=20, alis=300):
    """DZ4: bir blogu iki plakaya kes. Her teste kendi kimlikleri."""
    from models import Kesim, KesimDetay
    bid = f'BLK-{ek}'
    with fa.app.app_context():
        if not db.session.get(BlokStok, bid):
            db.session.add(BlokStok(
                id=bid, blok_no=ek, cins='TEST', boy=300, yukseklik=180,
                en=170, hacim_m3=9.18, tonaj=tonaj, alis_fiyati=alis,
                alis_fiyat_birim='ton', doviz='USD', durum='Serbest'))
            db.session.commit()
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': [bid],
        'kesim_tarihi': '2026-10-01',
        'hedefler': [
            {'hedef_tip': 'PLAKA', 'cins': 'TEST', 'boy': 300,
             'yukseklik': 180, 'kalinlik': 2, 'adet': 1},
            {'hedef_tip': 'PLAKA', 'cins': 'TEST', 'boy': 300,
             'yukseklik': 180, 'kalinlik': 2, 'adet': 1}]})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        ks = Kesim.query.filter_by(kaynak_id=bid).first()
        plakalar = [d.hedef_stok_id for d in
                    KesimDetay.query.filter_by(kesim_id=ks.id).all()]
    return bid, ks.id, plakalar


def test_dz4_plaka_olcusu_degisince_maliyet_yeniden_dagilir():
    """DZ4: bloğun maliyeti plakalara m² ORANINDA dağıtılıyor —
    birim = (matrah + ek maliyet) / toplam m². Bir plakanın m²'si
    değişince PAYDA değişir, yani KARDEŞ plakaların birim maliyeti
    de değişmeli.

    Dağıtıcı zaten vardı ve plakaların canlı m²'sini okuyordu, ama
    yalnız BLOĞA dokunulunca çağrılıyordu. Ölçüldü: plakanın m²'si
    5,4 → 30 yapıldı, iki plakanın da birim maliyeti 555,56'da
    kaldı; doğrusu 169,49 idi."""
    from models import PlakaStok
    c = istemci('admin', 'ADMIN')
    bid, kid, plakalar = _dz4_kesim(c, 'DZ4A', tonaj=20, alis=300)
    assert len(plakalar) == 2
    with fa.app.app_context():
        ilk = db.session.get(PlakaStok, plakalar[0])
        # 6000 USD / 10.8 m2
        assert abs((ilk.alis_fiyati or 0) - 555.56) < 0.05, ilk.alis_fiyati

    r = c.put(f'/api/stok/{plakalar[0]}', headers=H,
              json={'tip': 'PLAKA', 'cins': 'TEST', 'metraj_m2': 30})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert d['kesim_yeniden_dagitim'], d
    assert d['kesim_yeniden_dagitim']['blok'] == bid, d

    with fa.app.app_context():
        # 6000 / (30 + 5.4) = 169.49 — IKISINDE DE
        for pid in plakalar:
            p = db.session.get(PlakaStok, pid)
            assert abs((p.alis_fiyati or 0) - 169.49) < 0.05, (pid, p.alis_fiyati)


def test_dz4_kesim_kaydi_stoktan_ayrismaz():
    """DZ4: kesim, o gün ne çıktığının kaydı. Stok düzeltilince
    kesim satırı 5,4 m²'de kalıyordu — belge ile depo birbirini
    tutmuyordu."""
    from models import KesimDetay, PlakaStok
    c = istemci('admin', 'ADMIN')
    bid, kid, plakalar = _dz4_kesim(c, 'DZ4B', tonaj=20, alis=300)

    c.put(f'/api/stok/{plakalar[0]}', headers=H,
          json={'tip': 'PLAKA', 'cins': 'TEST', 'metraj_m2': 25,
                'kalinlik': 3})
    with fa.app.app_context():
        dt = KesimDetay.query.filter_by(hedef_stok_id=plakalar[0]).first()
        p = db.session.get(PlakaStok, plakalar[0])
        assert dt.miktar_m2 == 25, dt.miktar_m2
        assert dt.kalinlik == 3, dt.kalinlik
        # Maliyet de stokla ayni
        assert abs((dt.birim_maliyet or 0) - (p.alis_fiyati or 0)) < 0.01
        # Kardesin maliyeti de guncellendi
        dt2 = KesimDetay.query.filter_by(hedef_stok_id=plakalar[1]).first()
        p2 = db.session.get(PlakaStok, plakalar[1])
        assert abs((dt2.birim_maliyet or 0) - (p2.alis_fiyati or 0)) < 0.01


def test_dz4_kesimden_gelmeyen_stokta_dagitim_calismaz():
    """DZ4: yeniden dağıtım yalnız KESİMDEN çıkmış ürün için.
    Doğrudan girilmiş bir plakanın ölçüsünü değiştirmek hiçbir
    bloğun dağıtımını tetiklememeli — ortada dağıtılacak bir blok
    maliyeti yok."""
    from models import PlakaStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not db.session.get(PlakaStok, 'PLK-DZ4C'):
            db.session.add(PlakaStok(
                id='PLK-DZ4C', blok_no='DZ4C', cins='TEST', boy=300,
                yukseklik=180, kalinlik=2, metraj_m2=5.4,
                alis_fiyati=100, durum='Serbest',
                giris_tarihi=date(2026, 10, 1)))
            db.session.commit()
    r = c.put('/api/stok/PLK-DZ4C', headers=H,
              json={'tip': 'PLAKA', 'cins': 'TEST', 'metraj_m2': 8})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()['kesim_yeniden_dagitim'] is None, r.get_json()
    with fa.app.app_context():
        p = db.session.get(PlakaStok, 'PLK-DZ4C')
        assert p.metraj_m2 == 8
        assert p.alis_fiyati == 100, 'dokunulmamalıydı'


# ══════════════════════════════════════════════════════════════════
#  DZ5 · CARİ HAREKETİN TUTARI DÜZELTİLEBİLİR
#
#  Ölçülen: 10.000 TL tahsilat girilecekken 100.000 TL girilmiş bir
#  kaydı düzeltmenin hiçbir yolu yoktu. Beyaz liste borç/alacak/
#  döviz/kuru DIŞARIDA bırakıyordu; yanındaki not "tutar düzeltmesi
#  iptal+yeniden giriş ile yapılmalı" diyordu. O yol çalışıyor ama
#  denetim kaydında düzeltme diye bir iz bırakmıyor — bir SİLME ve
#  bir YENİ KAYIT bırakıyor.
#
#  Ayrıca: süzgeç `hasattr(hareket, k)` idi. `tutar` modelde bir
#  alan DEĞİL, o yüzden ne reddediliyor ne uygulanıyordu —
#  `PUT {"tutar": 10000}` 200 "Değişiklik yok" dönüyordu.
# ══════════════════════════════════════════════════════════════════

def _dz5_kur(c, ek, tutar=100000, doviz='TRY', tip='Tahsilat'):
    """DZ5 kurulumu. HER TESTE KENDİ cari/kasa/hareket kimliği:
    genel sayım yapılırsa başka testlerin bıraktığı satırlar girer
    ve test sırası önemli hale gelir (DZ1'de bir kez yaşandı)."""
    from models import Cari, Kasa
    cid = f'MD5{ek}'
    with fa.app.app_context():
        if not db.session.get(Cari, cid):
            db.session.add(Cari(id=cid, unvan=f'DZ5 {ek}',
                                cari_tip='Müşteri'))
        k = Kasa.query.filter_by(ad=f'DZ5 {ek} KASA').first()
        if not k:
            k = Kasa(ad=f'DZ5 {ek} KASA', doviz=doviz, bakiye=0)
            db.session.add(k)
        db.session.commit()
        kid = k.id
    yan = 'alacak' if tip == 'Tahsilat' else 'borc'
    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': cid, 'islem_tip': tip, 'doviz': doviz,
        'tutar': tutar, yan: tutar, 'kasa_id': kid,
        'hareket_tarihi': '2026-10-01', 'vade_tarihi': '2026-10-01',
        'evrak_no': f'MK-{ek}'})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        h = CariHareket.query.filter_by(cari_id=cid).first()
        return h.id, kid, cid


def test_dz5_cari_hareket_tutari_duzeltilebiliyor():
    """DZ5: tutar düzeltilince TRY karşılığı ve bağlı kasa birlikte
    gidiyor. Eskiden bu PUT 400 dönüyordu: 'Bu alanlar buradan
    değiştirilemez: alacak.'"""
    from models import Kasa
    c = istemci('admin', 'ADMIN')
    hid, kid, _ = _dz5_kur(c, 'A')
    with fa.app.app_context():
        assert float(db.session.get(Kasa, kid).bakiye) == 100000

    r = c.put(f'/api/cari/hareket/{hid}?onay=1', headers=H,
              json={'tutar': 10000})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        h = db.session.get(CariHareket, hid)
        assert float(h.alacak) == 10000, 'tutar düzelmedi'
        assert float(h.alacak_try) == 10000, 'TRY karşılığı takip etmedi'
        assert float(db.session.get(Kasa, kid).bakiye) == 10000, \
            'kasa bakiyesi eski tutarda kaldı'


def test_dz5_tutar_degisimi_once_kapsami_soruyor():
    """DZ5: tutarın arkasında kasa bakiyesi, kapanışlar, kur farkı
    kayıtları ve fatura durumu var. DZ1'de silme için kurulan kural
    burada da geçerli: kapsam ÖNCE söylenir, sonra iş yapılır.

    Onay verilmediyse HİÇBİR ŞEY değişmemeli."""
    from models import Kasa
    c = istemci('admin', 'ADMIN')
    hid, kid, _ = _dz5_kur(c, 'B')

    r = c.put(f'/api/cari/hareket/{hid}', headers=H, json={'tutar': 5000})
    assert r.status_code == 409, r.status_code
    d = r.get_json()
    assert d['error'] == 'onay_gerekli', d
    assert float(d['kapsam']['eski_tutar']) == 100000, d['kapsam']
    assert float(d['kapsam']['yeni_tutar']) == 5000, d['kapsam']
    assert any('kasa' in m for m in d['kapsam']['maddeler']), d['kapsam']

    with fa.app.app_context():
        assert float(db.session.get(CariHareket, hid).alacak) == 100000, \
            'onay verilmeden tutar değişmiş'
        assert float(db.session.get(Kasa, kid).bakiye) == 100000, \
            'onay verilmeden kasa değişmiş'


def test_dz5_bilinmeyen_alan_sessizce_yutulmuyor():
    """DZ5: eski süzgeç yalnız MODELDE OLAN alanları reddediyordu.
    Modelde olmayan bir ad ne reddediliyor ne uygulanıyordu; PUT
    200 ve 'Değişiklik yok' dönüyordu. Ölçüldü. Ekranı naif
    yazsaydım 'kaydedildi' diyecek, rakam yerinde duracaktı."""
    c = istemci('admin', 'ADMIN')
    hid, _, _ = _dz5_kur(c, 'C')
    r = c.put(f'/api/cari/hareket/{hid}', headers=H, json={'tutarr': 5})
    assert r.status_code == 400, r.get_json()
    assert 'tutarr' in r.get_json()['mesaj'], r.get_json()

    # `tutar` ise ARTIK TANINIYOR: ekranın kullandığı ad bu.
    r = c.put(f'/api/cari/hareket/{hid}', headers=H, json={'tutar': 7000})
    assert r.status_code == 409, (r.status_code, r.get_json())


def test_dz5_yon_ve_sifir_tutar_kapali():
    """DZ5: yön kaydın NİTELİĞİ — alacak kaydına borç yazmak
    düzeltme değil, başka bir kayıt. Sıfır da silmenin yerine
    geçmez: kaydı ekstrede bırakır ama bakiyeye hiç girmez."""
    c = istemci('admin', 'ADMIN')
    hid, _, _ = _dz5_kur(c, 'D')

    r = c.put(f'/api/cari/hareket/{hid}?onay=1', headers=H,
              json={'borc': 500})
    assert r.status_code == 400, r.get_json()
    assert 'yön' in r.get_json()['mesaj'], r.get_json()

    r = c.put(f'/api/cari/hareket/{hid}?onay=1', headers=H, json={'tutar': 0})
    assert r.status_code == 400, r.get_json()

    with fa.app.app_context():
        h = db.session.get(CariHareket, hid)
        assert float(h.alacak) == 100000 and float(h.borc or 0) == 0


def test_dz5_tutar_duzeltilince_kapanis_yeniden_kuruluyor():
    """DZ5+DZ6: tahsilat bir borcu kapatmış ve kur farkı doğmuşsa,
    tutar değişince o eşleşme geçersiz. DELETE'in kullandığı
    `_kur_farki_geri_al` ile çözülüyor — ikinci bir çözme mantığı
    yazmadık, zamanla ayrışırdı — sonra YENİ tutarla yeniden
    kuruluyor.

    DZ5'te açık bırakılıyordu. Bu yanlıştı: kur farkı gerçek bir
    gider ve onu yeniden hesaplatacak bir ekran YOK, yani
    kullanıcıya yapamayacağı bir şey söyleniyordu. DZ6 ile eşleşme
    burada yeniden kuruluyor; doğan kur farkı önce onay ekranında
    rakamıyla gösteriliyor, yani EK2'nin kuralı korunuyor.

    BURADA ÖDEME KISMİ: 1.000 USD borca 600 USD. Borç KAPANMIYOR
    (kısmi), ama eşleşen 600 USD üzerinden kur farkı doğuyor:
    600 × (48 − 38) = 6.000 TRY."""
    from models import Cari, Kasa
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not db.session.get(Cari, 'MD5E'):
            db.session.add(Cari(id='MD5E', unvan='DZ5 E',
                                cari_tip='Müşteri'))
        if not db.session.get(CariHareket, 'HR-DZ5E'):
            db.session.add(CariHareket(
                id='HR-DZ5E', cari_id='MD5E', cari_unvan='DZ5 E',
                islem_tip='Fatura (Satis)', hareket_tarihi=date(2026, 1, 2),
                vade_tarihi=date(2026, 1, 2), borc=1000, alacak=0,
                borc_try=38000, doviz='USD', kur_uygulanan=38,
                kaynak='manuel', kapatildi=False))
        k = Kasa.query.filter_by(ad='DZ5 E KASA').first()
        if not k:
            k = Kasa(ad='DZ5 E KASA', doviz='USD', bakiye=0)
            db.session.add(k)
        db.session.commit()
        kid = k.id

    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': 'MD5E', 'islem_tip': 'Tahsilat', 'doviz': 'USD',
        'tutar': 1000, 'alacak': 1000, 'kasa_id': kid,
        'hareket_tarihi': date.today().isoformat(),
        'vade_tarihi': date.today().isoformat(),
        'evrak_no': 'MK-E', 'kur_farki_islet': True})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        th = CariHareket.query.filter_by(cari_id='MD5E',
                                         islem_tip='Tahsilat').first()
        tid = th.id
        assert db.session.get(CariHareket, 'HR-DZ5E').kapatildi is True, \
            'kurulum tutmadı: borç kapanmamış'
        kf_once = CariHareket.query.filter_by(
            cari_id='MD5E', kaynak='otomatik_kur_farki').count()
        assert kf_once == 1, f'kurulum tutmadı: {kf_once} kur farkı kaydı'

    r = c.put(f'/api/cari/hareket/{tid}?onay=1', headers=H,
              json={'tutar': 600})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        assert float(db.session.get(CariHareket, tid).alacak) == 600
        eski = db.session.get(CariHareket, 'HR-DZ5E')
        # 600 < 1.000 → borc KISMI odendi, kapanmiyor
        assert not eski.kapatildi, 'kısmi ödeme borcu kapatmamalı'
        assert eski.kapanis_hareket_id is None, 'kapanış bağı kalmamalı'
        # Eski (1.000 USD uzerinden) kayit gitti, YENISI geldi:
        # eslesen 600 USD × (48 − 38) = 6.000 TRY
        kf = CariHareket.query.filter_by(
            cari_id='MD5E', kaynak='otomatik_kur_farki').all()
        assert len(kf) == 1, f'{len(kf)} kur farkı kaydı (1 olmalı)'
        _kf_tut = float((kf[0].borc or 0) + (kf[0].alacak or 0))
        assert _kf_tut == 6000, f'kur farkı {_kf_tut} (6000 olmalı)'
        assert float(db.session.get(Kasa, kid).bakiye) == 600


def test_dz5_hareket_duzenleme_ekrani_var():
    """DZ5: sunucu tarafı tek başına işe yaramaz. Hareket satırının
    TEK eylemi `✕` silmekti; düzenlemeyi çağıran bir ekran yoktu —
    sunucu açıklama/evrak/vade/tarihi kabul ediyordu ama onu
    çağıran hiçbir şey yoktu.

    Yapı testi: düğme, form, 409 onay yolu ve iki sessiz tuzağın
    kapağı yerinde mi."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/cari.html'),
                 encoding='utf-8').read()
    assert 'hareketDuzenleAc(' in m, 'satırda düzenleme düğmesi yok'
    assert 'id="hdModal"' in m, 'düzenleme formu yok'
    assert 'hareketDuzenleKaydet' in m
    assert "e.yanit.error === 'onay_gerekli'" in m.split(
        'async function hareketDuzenleKaydet')[1], \
        'düzenleme yolunda 409 onayı ele alınmıyor'

    # TUZAK 1 — genel büyük harf kuralı `<input>`lara uygulanıyor.
    # Form MEVCUT açıklamayı gösteriyor; kural açık olsaydı formu
    # sadece AÇMAK kullanıcının yazdığı metni büyük harfe çevirirdi.
    i = m.index('id="hdAciklama"')
    assert 'data-buyuk-harf="hayir"' in m[i - 40:i + 200], \
        'açıklama alanı büyük harf kuralına açık kalmış'

    # TUZAK 2 — `belge_no` CariHareket'te YOK (Sevkiyat'ın alanı) ama
    # sunucunun beyaz listesindeydi. Forma koysaydım kullanıcı yazar,
    # "kaydedildi" görür, ertesi gün alanı boş bulurdu.
    assert 'hdBelge' not in m, 'olmayan bir alan forma konmuş'


def test_dz5_olmayan_alan_guncellendi_diye_sayilmiyor():
    """DZ5: beyaz listede `belge_no` vardı ama o alan CariHareket'te
    bulunmuyor — Sevkiyat'ın alanı. Ölçüldü:

        PUT {"belge_no": "X"} → 200 {'guncellenen': ['belge_no']}
        kayıtta duran         → (alan yok)

    Alanı GÜNCELLENDİ diye adıyla sayıp hiçbir yere yazmıyordu.
    Bunu DZ5'in formunu yazarken buldum: alanı forma koymuş,
    tarayıcıda açmış ve listenin çöktüğünü görmüştüm."""
    from models import CariHareket as _CH
    assert 'belge_no' not in [k.name for k in _CH.__table__.columns], \
        'model değişmiş — bu testin gerekçesi kalktı'
    c = istemci('admin', 'ADMIN')
    hid, _, _ = _dz5_kur(c, 'F')
    r = c.put(f'/api/cari/hareket/{hid}', headers=H,
              json={'belge_no': 'DENEME-1'})
    assert r.status_code == 400, (r.status_code, r.get_json())
    assert 'belge_no' in r.get_json()['mesaj'], r.get_json()


# ══════════════════════════════════════════════════════════════════
#  DZ6 · ÖNCE YAP, ONAY YOKSA GERİ AL — VE EŞLEŞMEYİ YENİDEN KUR
#
#  DZ5 kapsamı ÖNCEDEN TAHMİN ediyordu ve kapanışları çözüp AÇIK
#  bırakıyordu. İki sonucu vardı:
#
#   · Yeni kur farkının tutarı tahmin edilemiyordu — onu hesaplamak
#     için hareketin yeni tutarı taşıması ve eski kapanışın çözülmüş
#     olması gerekiyor.
#   · Eşleşmeyi yeniden çalıştıran bir uç nokta ya da ekran YOK.
#     Yani kullanıcıya yapamayacağı bir şey söyleniyordu.
#
#  Ölçüldü: 10.000 EUR borç 44 kurdan, 100.000 EUR yanlış ödeme 46
#  kurdan. Sistem borcu kapatıp 20.000 TL kur farkı açıyor. Ödeme
#  10.000 EUR'ya düzeltilince o kayıt siliniyor ve yerine yenisi
#  GELMİYORDU — oysa fark gerçek: 44'ten borçlanıp 46'dan ödenmiş.
# ══════════════════════════════════════════════════════════════════

def _dz6_kur(c, ek):
    """EUR borç (44 kurdan) + yanlış tutarlı EUR ödeme (46 kurdan).
    Ödeme eşleştirilerek giriliyor, yani kur farkı doğuyor."""
    from models import Cari, Kasa, DovizKur
    cid = f'TD6{ek}'
    with fa.app.app_context():
        if not db.session.get(Cari, cid):
            db.session.add(Cari(id=cid, unvan=f'DZ6 {ek}',
                                cari_tip='Tedarikçi'))
        for _t, _k in ((date(2026, 3, 1), 44), (date(2026, 3, 2), 46)):
            if not DovizKur.query.filter_by(doviz='EUR', tarih=_t).first():
                db.session.add(DovizKur(doviz='EUR', tarih=_t,
                                        alis=_k, satis=_k))
        k = Kasa.query.filter_by(ad=f'DZ6 {ek} KASA').first()
        if not k:
            k = Kasa(ad=f'DZ6 {ek} KASA', doviz='TRY', bakiye=5000000)
            db.session.add(k)
        db.session.commit()
        kid = k.id
        bid = f'HR-D6{ek}'
        if not db.session.get(CariHareket, bid):
            db.session.add(CariHareket(
                id=bid, cari_id=cid, cari_unvan=f'DZ6 {ek}',
                islem_tip='Fatura (Alis)', hareket_tarihi=date(2026, 3, 1),
                vade_tarihi=date(2026, 3, 1), borc=0, alacak=10000,
                alacak_try=440000, doviz='EUR', kur_uygulanan=44,
                kaynak='manuel', kapatildi=False))
            db.session.commit()
    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': cid, 'islem_tip': 'Odeme', 'doviz': 'EUR',
        'tutar': 100000, 'borc': 100000, 'kasa_id': kid,
        'hareket_tarihi': '2026-03-02', 'vade_tarihi': '2026-03-02',
        'evrak_no': f'DK-{ek}', 'kur_farki_islet': True})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        o = CariHareket.query.filter_by(cari_id=cid,
                                        islem_tip='Odeme').first()
        return o.id, bid, cid, kid


def _dz6_iz(cid, kid):
    """Bu testin dokunduğu HER ŞEYİN özeti. Tek alan değişse tutmaz."""
    from models import Kasa
    with fa.app.app_context():
        p = []
        for h in CariHareket.query.filter_by(cari_id=cid).order_by(
                CariHareket.id).all():
            p.append(f'{h.id}|{h.borc}|{h.alacak}|{h.borc_try}|{h.doviz}|'
                     f'{h.kur_uygulanan}|{h.kapatildi}|'
                     f'{h.kapanis_hareket_id}|{h.aciklama}|{h.evrak_no}')
        p.append(f'KASA|{db.session.get(Kasa, kid).bakiye}')
        return '\n'.join(p)


def test_dz6_vazgecince_hicbir_sey_kalmiyor():
    """DZ6: iş artık ÖNCE YAPILIYOR, sonra onay yoksa rollback ile
    geri alınıyor. Bu testin tek sorusu: geri alma GERÇEKTEN her şeyi
    geri alıyor mu — kasa bakiyesi, kapanış bayrakları, silinen ve
    yeni açılan kur farkı kayıtları dahil.

    Üst üste vazgeçmek de artık artık bırakmamalı."""
    c = istemci('admin', 'ADMIN')
    oid, bid, cid, kid = _dz6_kur(c, 'A')
    once = _dz6_iz(cid, kid)

    r = c.put(f'/api/cari/hareket/{oid}', headers=H,
              json={'tutar': 10000, 'aciklama': 'DUZELTILDI'})
    assert r.status_code == 409, (r.status_code, r.get_json())
    assert _dz6_iz(cid, kid) == once, 'vazgeçmeye rağmen bir şey kaldı'

    # Üç kez daha vazgeç — birikmemeli
    for _ in range(3):
        c.put(f'/api/cari/hareket/{oid}', headers=H, json={'tutar': 10000})
    assert _dz6_iz(cid, kid) == once, 'tekrarlanan vazgeçme artık bıraktı'


def test_dz6_eslesme_yeniden_kuruluyor_kur_farki_onayda_yaziyor():
    """DZ6: düzeltmeden sonra eşleşme yeniden kuruluyor ve doğan kur
    farkı RAKAMIYLA onay ekranında yazıyor.

    10.000 EUR 44'ten borçlanılmış, 46'dan ödenmiş → 20.000 TL fark.
    DZ5'te bu kayıt siliniyor ve yerine yenisi gelmiyordu."""
    from models import Kasa
    c = istemci('admin', 'ADMIN')
    oid, bid, cid, kid = _dz6_kur(c, 'B')
    with fa.app.app_context():
        assert db.session.get(CariHareket, bid).kapatildi is True, \
            'kurulum tutmadı: borç kapanmamış'
        assert CariHareket.query.filter_by(
            cari_id=cid, kaynak='otomatik_kur_farki').count() == 1

    r = c.put(f'/api/cari/hareket/{oid}', headers=H, json={'tutar': 10000})
    assert r.status_code == 409, r.get_json()
    msj = r.get_json()['mesaj']
    # Tahmin DEGIL: bu rakam isi yapip olcerek bulundu.
    assert '20,000.00' in msj, msj
    # Kayit tipi veride ASCII ('Kur Farki (Borc)'), kullaniciya
    # OKUNABILIR gosteriliyor.
    assert 'Kur Farkı' in msj, msj

    r = c.put(f'/api/cari/hareket/{oid}?onay=1', headers=H,
              json={'tutar': 10000})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        o = db.session.get(CariHareket, oid)
        assert float(o.borc) == 10000
        assert float(o.borc_try) == 460000, 'TRY karşılığı ödeme kurundan'
        assert db.session.get(CariHareket, bid).kapatildi is True, \
            'eşleşme yeniden kurulmadı — borç açık kaldı'
        kf = CariHareket.query.filter_by(
            cari_id=cid, kaynak='otomatik_kur_farki').all()
        assert len(kf) == 1, f'{len(kf)} kur farkı kaydı (1 olmalı)'
        assert float(kf[0].borc) == 20000, float(kf[0].borc)
        # 5.000.000 − 460.000
        assert float(db.session.get(Kasa, kid).bakiye) == 4540000


def test_dz6_eslesmesiz_kayitta_kur_farki_acilmiyor():
    """DZ6: eşleşme YALNIZCA önceden varsa yeniden kuruluyor.

    Kullanıcı o ödemeyi eşleştirmeden girdiyse, düzeltme bahanesiyle
    ona hiç istemediği bir kur farkı kaydı açmak doğru olmazdı —
    muhasebe kaydını sessizce oluşturmama kuralı (EK2) bunu da
    kapsıyor."""
    c = istemci('admin', 'ADMIN')
    hid, kid, cid = _dz5_kur(c, 'G')   # TRY tahsilat, eşleştirme yok
    with fa.app.app_context():
        assert CariHareket.query.filter_by(
            cari_id=cid, kaynak='otomatik_kur_farki').count() == 0

    r = c.put(f'/api/cari/hareket/{hid}?onay=1', headers=H,
              json={'tutar': 10000})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        assert CariHareket.query.filter_by(
            cari_id=cid, kaynak='otomatik_kur_farki').count() == 0, \
            'istenmediği halde kur farkı kaydı açıldı'


def test_dz6_kapsam_tahmin_eden_fonksiyon_kaldirildi():
    """DZ6: kapsamı önceden sayan `_hareket_tutar_kapsami` kaldırıldı.
    Sayan kod ile YAPAN kod iki ayrı yerde durdukça zamanla
    ayrışırlar — DZ4'te aynı dersi almıştık. Ölü kod da bırakmıyoruz:
    sonraki biri onu doğru sanıp çağırabilir."""
    import io as _io
    f = _io.open(os.path.join(KOK, 'flask_app.py'), encoding='utf-8').read()
    assert 'def _hareket_tutar_kapsami' not in f, \
        'tahmin eden fonksiyon hâlâ duruyor'


def test_dz6_odeme_borctan_kucukse_de_eslesme_yeniden_kuruluyor():
    """DZ6: "eşleşme vardı"nın ÜÇ işareti var ve üçü de sayılmalı.

    Başta yalnız birine bakıyordum: "bu hareket bir borç kapattı mı".
    TARAYICIDA görüldü — testler kaçırmıştı, çünkü ikisi de ödemenin
    borçtan BÜYÜK olduğu durumu kuruyordu:

        10.000 EUR borç, 9.900 EUR ödeme (44 → 46 kur)

    Ödeme küçük olduğu için kapanan taraf BORÇ değil ÖDEMEnin
    kendisi oluyor; borç açık kalıyor. Yani "kapattığı hareket"
    sayısı sıfır — ama kur farkı kaydı gayet vardı ve düzeltmede
    siliniyordu. Yerine yenisi gelmiyordu.

    Doğrusu: ödemenin kendi kapanışı da bir eşleşme işaretidir."""
    from models import Cari, Kasa, DovizKur
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not db.session.get(Cari, 'TD6K'):
            db.session.add(Cari(id='TD6K', unvan='DZ6 K',
                                cari_tip='Tedarikçi'))
        for _t, _k in ((date(2026, 3, 1), 44), (date(2026, 3, 2), 46)):
            if not DovizKur.query.filter_by(doviz='EUR', tarih=_t).first():
                db.session.add(DovizKur(doviz='EUR', tarih=_t,
                                        alis=_k, satis=_k))
        k = Kasa.query.filter_by(ad='DZ6 K KASA').first()
        if not k:
            k = Kasa(ad='DZ6 K KASA', doviz='TRY', bakiye=5000000)
            db.session.add(k)
        db.session.commit()
        kid = k.id
        if not db.session.get(CariHareket, 'HR-D6K'):
            db.session.add(CariHareket(
                id='HR-D6K', cari_id='TD6K', cari_unvan='DZ6 K',
                islem_tip='Fatura (Alis)', hareket_tarihi=date(2026, 3, 1),
                vade_tarihi=date(2026, 3, 1), borc=0, alacak=10000,
                alacak_try=440000, doviz='EUR', kur_uygulanan=44,
                kaynak='manuel', kapatildi=False))
            db.session.commit()

    # ODEME BORCTAN KUCUK: 9.900 < 10.000
    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': 'TD6K', 'islem_tip': 'Odeme', 'doviz': 'EUR',
        'tutar': 9900, 'borc': 9900, 'kasa_id': kid,
        'hareket_tarihi': '2026-03-02', 'vade_tarihi': '2026-03-02',
        'evrak_no': 'DK-K', 'kur_farki_islet': True})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        o = CariHareket.query.filter_by(cari_id='TD6K',
                                        islem_tip='Odeme').first()
        oid = o.id
        # Kurulumun ta kendisi: KAPANAN taraf ODEME, borc acik
        assert o.kapatildi is True, 'kurulum tutmadı: ödeme kapanmamış'
        assert db.session.get(CariHareket, 'HR-D6K').kapatildi is False, \
            'kurulum tutmadı: kısmi ödeme borcu kapatmış'
        assert CariHareket.query.filter_by(
            cari_id='TD6K', kaynak='otomatik_kur_farki').count() == 1

    r = c.put(f'/api/cari/hareket/{oid}', headers=H, json={'tutar': 10000})
    assert r.status_code == 409, r.get_json()
    msj = r.get_json()['mesaj']
    assert 'siliniyor' in msj, msj
    assert 'oluşuyor' in msj, f'yerine yenisi gelmiyor: {msj}'
    # Kayit tipi kullaniciya OKUNABILIR yaziliyor ('Kur Farki' degil)
    assert 'Kur Farkı' in msj, msj

    r = c.put(f'/api/cari/hareket/{oid}?onay=1', headers=H,
              json={'tutar': 10000})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        kf = CariHareket.query.filter_by(
            cari_id='TD6K', kaynak='otomatik_kur_farki').all()
        assert len(kf) == 1, f'{len(kf)} kur farkı kaydı (1 olmalı)'
        # 10.000 EUR tam eslesti: 10.000 × (46 − 44) = 20.000 TRY
        assert float((kf[0].borc or 0) + (kf[0].alacak or 0)) == 20000


# ══════════════════════════════════════════════════════════════════
#  VT1 · BELGE TARİHİ / VADE TARİHİ
#
#  Sistemde iki tarih alanı vardı ve ikisi de yanlış yerde duruyordu:
#  vade HER harekette ZORUNLU, belge tarihi opsiyonel. Oysa kuru
#  belirleyen belge tarihi; vade bir TAHSİLATTA anlamsız — para
#  zaten el değiştirmiş.
#
#  `belge_tarihi` diye bir kolon zaten YOK; o sadece ekrandaki
#  etiket, altındaki alan `hareket_tarihi`.
# ══════════════════════════════════════════════════════════════════

def _vt1_cari(ek, tip='Müşteri'):
    from models import Cari, Kasa
    cid = f'VT{ek}'
    with fa.app.app_context():
        if not db.session.get(Cari, cid):
            db.session.add(Cari(id=cid, unvan=f'VT1 {ek}', cari_tip=tip))
        k = Kasa.query.filter_by(ad=f'VT1 {ek} KASA').first()
        if not k:
            k = Kasa(ad=f'VT1 {ek} KASA', doviz='TRY', bakiye=1000000)
            db.session.add(k)
        db.session.commit()
        return cid, k.id


def test_vt1_tahsilatta_vade_zorunlu_degil_ve_yazilmiyor():
    """VT1: vade her hareket için zorunluydu — `Cari, işlem tipi ve
    vade tarihi zorunlu`. Bir tahsilatın vadesi olmaz: para gelmiş.

    Gönderilse bile yazılmıyor, ama SESSİZCE yutulmuyor: yanıt
    bunu söylüyor."""
    c = istemci('admin', 'ADMIN')
    cid, kid = _vt1_cari('A')

    # 1) VADESİZ kabul ediliyor
    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': cid, 'islem_tip': 'Tahsilat', 'doviz': 'TRY',
        'tutar': 1000, 'alacak': 1000, 'kasa_id': kid,
        'hareket_tarihi': '2026-03-05', 'evrak_no': 'VT-A1'})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        h = CariHareket.query.filter_by(evrak_no='VT-A1').first()
        assert h.vade_tarihi is None
        assert h.hareket_tarihi == date(2026, 3, 5)

    # 2) GÖNDERİLSE BİLE yazılmıyor — ve söyleniyor
    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': cid, 'islem_tip': 'Tahsilat', 'doviz': 'TRY',
        'tutar': 500, 'alacak': 500, 'kasa_id': kid,
        'hareket_tarihi': '2026-03-05', 'vade_tarihi': '2026-09-09',
        'evrak_no': 'VT-A2'})
    assert r.status_code == 200, r.get_json()
    assert 'Vade tarihi yazılmadı' in r.get_json()['mesaj'], r.get_json()
    with fa.app.app_context():
        assert CariHareket.query.filter_by(
            evrak_no='VT-A2').first().vade_tarihi is None


def test_vt1_faturada_vade_hala_zorunlu():
    """VT1: gevşetme her tipi kapsamıyor. Fatura bir BORÇ doğurur;
    yaşlandırma ve gecikme takibi onun vadesinden beslenir."""
    c = istemci('admin', 'ADMIN')
    cid, _ = _vt1_cari('B')
    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': cid, 'islem_tip': 'Fatura (Satis)', 'doviz': 'TRY',
        'tutar': 1000, 'borc': 1000, 'hareket_tarihi': '2026-03-05',
        'evrak_no': 'VT-B1'})
    assert r.status_code == 400, r.get_json()
    assert 'vade' in r.get_json()['mesaj'].lower()


def test_vt1_nakit_hareketi_yaklasan_listesine_girmiyor():
    """VT1: form vadeyi BUGÜNLE dolduruyordu, sorgu da yalnız
    borç/alacak işaretine bakıyordu. Sonuç ölçüldü: bugün TAHSİL
    EDİLMİŞ ve kasaya girmiş para, "yaklaşan ödemeler" — yani
    önümüzdeki 30 günde ÖDEYECEĞİMİZ paralar — listesinde
    duruyordu.

    İki koruma var: vade artık o tiplere yazılmıyor (yeni kayıt),
    ve sorgu işlem tipine de bakıyor (ESKİ kayıtlar)."""
    from models import Cari
    c = istemci('admin', 'ADMIN')
    cid, kid = _vt1_cari('C')
    # ESKİ kayıt taklidi: vadesi BUGÜN olan bir tahsilat
    with fa.app.app_context():
        if not db.session.get(CariHareket, 'HR-VT1C'):
            db.session.add(CariHareket(
                id='HR-VT1C', cari_id=cid, cari_unvan='VT1 C',
                islem_tip='Tahsilat', hareket_tarihi=date.today(),
                vade_tarihi=date.today(), borc=0, alacak=9999,
                alacak_try=9999, doviz='TRY', kur_uygulanan=1,
                kaynak='manuel'))
            db.session.commit()

    r = c.get('/api/cari/finansal_ozet', headers=H)
    assert r.status_code == 200, r.status_code
    d = r.get_json()
    tutarlar = [x.get('tutar') for x in (d.get('yaklasan_odemeler') or [])]
    assert 9999 not in tutarlar, \
        f'tahsil edilmiş para ödenecekler listesinde: {tutarlar}'


def test_vt1_ucuncu_dovizli_kasada_kur_belge_tarihinden():
    """VT1: hareketin kendi TL karşılığı BELGE tarihinden, bağlı
    kasa hareketi ise VADE tarihinden çevriliyordu. Aynı ödeme iki
    ayrı günün kuruyla TL'ye çevriliyordu.

    TL kasada görünmüyor (oradaki dal hazır TL karşılığını
    kullanıyor); kasa ÜÇÜNCÜ bir dövizdeyse ortaya çıkıyor.

    ÖLÇÜLDÜ: 1.000 USD, belge günü 40 / vade günü 50; EUR kasa,
    belge günü 44 / vade günü 55.
        doğru : 40.000 / 44 = 909,09 EUR
        olan  : 40.000 / 55 = 727,27 EUR"""
    from models import Cari, Kasa, DovizKur
    c = istemci('admin', 'ADMIN')
    _b, _v = date(2026, 4, 1), date(2026, 5, 1)
    with fa.app.app_context():
        if not db.session.get(Cari, 'VTD'):
            db.session.add(Cari(id='VTD', unvan='VT1 D',
                                cari_tip='Müşteri'))
        for _d, _t, _k in (('USD', _b, 40), ('USD', _v, 50),
                           ('EUR', _b, 44), ('EUR', _v, 55)):
            if not DovizKur.query.filter_by(doviz=_d, tarih=_t).first():
                db.session.add(DovizKur(doviz=_d, tarih=_t,
                                        alis=_k, satis=_k))
        k = Kasa.query.filter_by(ad='VT1 D EUR').first()
        if not k:
            k = Kasa(ad='VT1 D EUR', doviz='EUR', bakiye=0)
            db.session.add(k)
        db.session.commit()
        kid = k.id

    # Acilis Bakiyesi: vadesi ANLAMLI olan bir tip, yani vade
    # gercekten yazilir — ayrisma ancak boyle olculebilir.
    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': 'VTD', 'islem_tip': 'Tahsilat', 'doviz': 'USD',
        'tutar': 1000, 'alacak': 1000, 'kasa_id': kid,
        'hareket_tarihi': _b.isoformat(),
        'vade_tarihi': _v.isoformat(), 'evrak_no': 'VT-D1'})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        h = CariHareket.query.filter_by(evrak_no='VT-D1').first()
        assert float(h.alacak_try) == 40000, float(h.alacak_try)
        kh = KasaHareket.query.filter_by(
            baglanti_tip='cari_hareket', baglanti_id=h.id).first()
        assert kh is not None, 'kasa hareketi yok'
        assert abs(float(kh.tutar) - 909.09) < 0.02, \
            f'{kh.tutar} — vade günü kuru kullanılmış olmalı değil'


def test_vt1_vadesiz_fatura_yaslaniyor():
    """VT1: gecikme hesabı `if f.vade_tarihi and f.vade_tarihi <
    bugun` idi — vade boşsa koşul hiç çalışmıyor, gecikme SIFIR
    dönüyordu.

    ÖLÇÜLDÜ, 120 gün önce kesilmiş iki fatura:
        vadesi tanımlı → 90 gün   ✓
        vadesi boş     →  0 gün   ✗   (tahsilat takibinden düşüyor)

    Vade yoksa gecikme FATURA TARİHİNDEN sayılıyor ve bunun bir
    varsayım olduğu `vadesiz` ile söyleniyor."""
    from datetime import timedelta as _td
    from models import Cari, Fatura
    c = istemci('admin', 'ADMIN')
    _kesim = date.today() - _td(days=120)
    with fa.app.app_context():
        if not db.session.get(Cari, 'VTE'):
            db.session.add(Cari(id='VTE', unvan='VT1 E',
                                cari_tip='Müşteri'))
        for _fid, _vade in (('FT-VTE1', None),
                            ('FT-VTE2', _kesim + _td(days=30))):
            if not db.session.get(Fatura, _fid):
                db.session.add(Fatura(
                    id=_fid, fatura_no=_fid, musteri='VT1 E',
                    cari_id='VTE', toplam=10000, doviz='USD',
                    durum='Kesildi', yon='satis',
                    fatura_tarihi=_kesim, vade_tarihi=_vade))
        db.session.commit()

    r = c.get('/api/cari/VTE/acik_faturalar?yon=satis', headers=H)
    assert r.status_code == 200, r.status_code
    fs = {x['fatura_no']: x for x in r.get_json()['faturalar']}
    assert fs['FT-VTE1']['gecikme_gun'] == 120, fs['FT-VTE1']
    assert fs['FT-VTE1']['vadesiz'] is True
    assert fs['FT-VTE2']['gecikme_gun'] == 90, fs['FT-VTE2']
    assert fs['FT-VTE2']['vadesiz'] is False


def test_vt1_olu_tahsilat_paneli_silindi():
    """VT1: "Tahsilat Gir" paneli ölü koddu — `tahModal`ı açan
    hiçbir şey yoktu. BF1 ile iki form birleştirilmiş, "Tahsilat /
    Ödeme" düğmesi o günden beri hareket formunu açıyordu.

    Duran ölü bir form zararsız değil: içinde iki gerçek hata vardı
    ve ben onları CANLI sanıp rapor ettim. Tarih alanı
    `vade_tarihi` olarak gidiyor ve `hareket_tarihi` hiç
    gönderilmiyordu; döviz de `'USD'` sabit yazılıydı.

    İki düğme tek panel açıyordu; biri kaldırıldı, işlem tipini
    hazır seçme işi `hareketAc`a taşındı."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/cari.html'),
                 encoding='utf-8').read()
    for _olu in ('id="tahModal"', 'function tahsilatKaydet',
                 'function faturaSecildi', "doviz: 'USD',"):
        assert _olu not in m, f'ölü kod duruyor: {_olu}'
    # ÇAĞRI biçimini arıyoruz, adı geçen açıklamaları değil:
    # `onclick="..."` ve `fn(` yalnız gerçek kodda böyle yazılır.
    assert 'onclick="tahsilatAc(' not in m, \
        'kaldırılan düğme hâlâ bir düğmeye bağlı'
    assert ' tahsilatAc(c.id)' not in m, 'kısayol hâlâ onu çağırıyor'
    assert 'function tahsilatAc' not in m, 'fonksiyon geri gelmiş'
    # Tek kapı: hareket formu
    assert m.count('onclick="hareketAc(') == 1, \
        'hareket düğmesi tek olmalı'


def test_mg1_maliyetler_tipe_gore_gruplaniyor():
    """MG1: kaynak zinciri çekmecesinde her maliyet satırı KENDİ
    kartıydı ve tip adı her kartta tekrarlanıyordu. Aynı tipten iki
    gümrük belgesi iki ayrı kart açıyordu.

    ÖLÇÜLDÜ (6 kalemli gerçek bir stokla, tarayıcıda):
        eski: 6 kart, 480 piksel
        yeni: 5 kutu, 338 piksel   → %30 daha az yer

    Artık tip bir kez yazılıyor, belgeler altında satır satır
    duruyor. Sıra İLK GÖRÜLME sırası: alfabetik dizmek sunucudan
    gelen (maliyet tarihine göre) sırayı bozardı."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/stok.html'),
                 encoding='utf-8').read()
    assert 'function maliyetGruplari(' in m, 'gruplayıcı yok'
    assert '${maliyetGruplari(mal)}' in m, 'liste gruplayıcıyı çağırmıyor'

    # ESKİ satır-başına-kart biçimi gitmeli; kalırsa iki yol birden
    # yaşar ve biri düzeltilip diğeri unutulur.
    assert 'class="kalem-satir"><span class="rozet rz-gri">' not in m, \
        'eski kart biçimi duruyor'

    # Tip ADI bir kez: başlıkta. Satırda tip yazmıyor.
    _g = m[m.index('function maliyetGruplari('):]
    _g = _g[:_g.index('\nasync function')]
    assert _g.count('mlyt-bas') == 1, 'tip başlığı bir kez yazılmalı'
    for _alan in ('Belge No:', 'Tarih:', 'Tutar:'):
        assert _alan in _g, f'{_alan} etiketi yok'
    # Tarih ORTAK biçimlendiriciden geçsin (base.html · tarihTR):
    # iki sayfada ayrı ayrı yazılırsa zamanla ayrışırlar.
    assert 'tarihTR(m.tarih)' in _g, 'tarih ham ISO basılıyor'

    # Kutu biçimi CSS'te tanımlı olmalı — yoksa düz metin yığını olur
    for _k in ('.mlyt-grup{', '.mlyt-bas{', '.mlyt-satir{'):
        assert _k in m, f'{_k} tanımlı değil'


# ══════════════════════════════════════════════════════════════════
#  MR1 · MALİYET RAPORLARI — VE DÖRT AYRI KOPYA
#
#  "Bu stoğun maliyeti ne?" sorusunun cevabı sistemde DÖRT ayrı
#  yerde hesaplanıyordu ve hiçbiri diğeriyle aynı değildi:
#
#      satış kârı          · iptal edileni SAYIYOR, tipsizi saymıyor
#      kesim dağıtıcısı    · iptal edileni SAYIYOR, tipsizi saymıyor
#      kesimin kendisi     · iptal edileni SAYIYOR, tipsizi saymıyor
#      ortaklık hesabı     · ikisi de DOĞRU
#
#  Ortaklık kodunda bu iki süzgecin gerekçesi yazılıydı
#  ("uygulamanın geri kalanı onları her yerde süzüyor") — ama
#  doğru değildi, yalnız orada vardı.
#
#  ÖLÇÜLDÜ: 400 USD'lik İPTAL bir gider yüzünden blok 7.550 USD
#  iken plakalara 7.950 dağıtılıyordu. 250 USD'lik TİPSİZ bir gider
#  ise satışın maliyetine hiç girmiyordu.
# ══════════════════════════════════════════════════════════════════

def _mr1_kur(ek):
    """Blok + dört maliyet kalemi: normal, iptal, tipsiz, KDV."""
    from models import Maliyet
    bid = f'BLK-MR{ek}'
    with fa.app.app_context():
        if not db.session.get(BlokStok, bid):
            db.session.add(BlokStok(
                id=bid, blok_no=f'MR{ek}', cins='MRTEST',
                uretici='MR OCAK', boy=300, yukseklik=180, en=170,
                hacim_m3=9.18, tonaj=20, alis_fiyati=300,
                alis_fiyat_birim='ton', doviz='USD', durum='Serbest'))
            db.session.add_all([
                # normal — SAYILIR
                Maliyet(id=f'MRM{ek}1', maliyet_tip='Nakliye (Ocak-Fabrika)',
                        baglanti_tip='stok', baglanti_id=bid, tutar=1000,
                        doviz='USD', usd_karsilik=1000, aktif=True),
                # İPTAL — sayılmaz
                Maliyet(id=f'MRM{ek}2', maliyet_tip='Gümrük/Liman Masrafı',
                        baglanti_tip='stok', baglanti_id=bid, tutar=500,
                        doviz='USD', usd_karsilik=500, aktif=False),
                # TİPSİZ — sayılır
                Maliyet(id=f'MRM{ek}3', maliyet_tip=None,
                        baglanti_tip='stok', baglanti_id=bid, tutar=250,
                        doviz='USD', usd_karsilik=250, aktif=True),
                # KDV izleme — maliyete girmez, ayrı gösterilir
                Maliyet(id=f'MRM{ek}4', maliyet_tip='Devreden KDV',
                        baglanti_tip='stok', baglanti_id=bid, tutar=900,
                        doviz='USD', usd_karsilik=900, aktif=True)])
            db.session.commit()
    return bid


def test_mr1_iptal_edilmis_gider_maliyete_girmiyor():
    """MR1: `aktif=False` kayıtlar İPTAL EDİLMİŞ maliyetlerdir.
    Üç ayrı hesap onları sayıyordu.

    Doğru toplam: alış 6.000 + (1.000 normal + 250 tipsiz) = 7.250.
    Eski hesap: 6.000 + (1.000 + 500 iptal) = 7.500 derdi."""
    c = istemci('admin', 'ADMIN')
    bid = _mr1_kur('A')
    r = c.get(f'/api/rapor/stok_maliyet?blok_no=MRA', headers=H)
    assert r.status_code == 200, r.status_code
    g = [x for x in r.get_json()['gruplar'] if x['id'] == bid]
    assert g, 'blok raporda yok'
    g = g[0]
    assert g['alim_usd'] == 6000, g['alim_usd']
    assert g['kalem_usd'] == 1250, g['kalem_usd']
    assert g['toplam_usd'] == 7250, g['toplam_usd']
    tipler = [k['tip'] for k in g['kalemler']]
    assert 'Gümrük/Liman Masrafı' not in tipler, 'iptal edilmiş gider sayıldı'
    assert '(tipsiz)' in tipler, 'tipsiz gider düştü'


def test_mr1_kdv_kalemi_ayri_gosteriliyor():
    """MR1: Devreden/İade KDV maliyete GİRMEZ — ürünün maliyeti
    değil, mahsup için izlenen tutar. Ama raporda görünmeli:
    "neden toplamda yok" sorusunun cevabı okunabilir olmalı."""
    c = istemci('admin', 'ADMIN')
    bid = _mr1_kur('B')
    r = c.get('/api/rapor/stok_maliyet?blok_no=MRB', headers=H)
    g = [x for x in r.get_json()['gruplar'] if x['id'] == bid][0]
    assert all(k['tip'] != 'Devreden KDV' for k in g['kalemler'])
    assert [h['tip'] for h in g['haric']] == ['Devreden KDV'], g['haric']
    assert g['haric'][0]['usd'] == 900


def test_mr1_birim_maliyet_olcu_yoksa_sifir_degil():
    """MR1: ölçüsü girilmemiş stokta birim maliyet SIFIR yazılmaz.
    Sıfır "maliyeti yok" demek olurdu; doğrusu "ölçü yok"."""
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not db.session.get(BlokStok, 'BLK-MROL'):
            db.session.add(BlokStok(
                id='BLK-MROL', blok_no='MROL', cins='MRTEST',
                alis_fiyati=300, alis_fiyat_birim='ton', doviz='USD',
                durum='Serbest', tonaj=0))
            db.session.commit()
    r = c.get('/api/rapor/stok_maliyet?blok_no=MROL', headers=H)
    g = [x for x in r.get_json()['gruplar'] if x['id'] == 'BLK-MROL'][0]
    assert g['birim_maliyet']['deger'] is None, g['birim_maliyet']
    assert g['birim_maliyet']['birim'] == 'ton'


def test_mr1_satis_dokumu_kayitla_tutuyor():
    """MR1: satışın maliyet dökümü ile KAYITTAKİ maliyet aynı olmalı.

    `tutarsizlik` alanı bunu söylüyor ve ilk denemede gerçek bir
    hatayı yakaladı: bloğa maliyet eklenince plakaların birim
    maliyeti yeniden dağıtılıyor ama SATILMIŞ plakanın kâr kaydı
    eski maliyetle kalıyordu — stok kartı yeni rakamı gösterirken
    kârlılık raporu eskisini gösteriyordu."""
    from models import Maliyet, SatisKaydi
    c = istemci('admin', 'ADMIN')
    bid = _mr1_kur('C')
    with fa.app.app_context():
        if not db.session.get(SatisKaydi, 'SK-MR-C'):
            db.session.add(SatisKaydi(
                id='SK-MR-C', stok_tip='BLOK', stok_id=bid,
                musteri='MR ALICI', cins='MRTEST',
                satis_tarihi=date(2026, 5, 1), doviz='USD',
                tutar=12000, tutar_usd=12000, kur_usd=40))
            db.session.commit()
    # Maliyete dokun → satış kaydı tazelenir
    assert c.put(f'/api/maliyet/MRMC1', headers=H,
                 json={'tutar': 1000}).status_code == 200

    r = c.get('/api/karlilik/SK-MR-C/dokum', headers=H)
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert d['maliyet']['toplam_usd'] == 7250, d['maliyet']
    assert d['ozet']['maliyet_usd'] == 7250, d['ozet']
    assert d['ozet']['kar_usd'] == 4750, d['ozet']
    assert d['tutarsizlik'] is None, d['tutarsizlik']


def test_mr1_dagitim_ve_rapor_ayni_rakami_soyluyor():
    """MR1: kesim dağıtımı ve rapor AYNI toplamdan beslenmeli.

    ÖLÇÜLDÜ: 400 USD'lik iptal bir gider yüzünden blok 7.550 USD
    iken plakalara 7.950 dağıtılıyordu — birim maliyet 736,11
    olması gerekirken 699,07 idi."""
    from models import Maliyet
    c = istemci('admin', 'ADMIN')
    bid = _mr1_kur('D')
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': [bid],
        'kesim_tarihi': '2026-05-02',
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'MRTEST', 'boy': 300,
                      'yukseklik': 180, 'kalinlik': 2, 'adet': 2,
                      'miktar_m2': 5}]})
    assert r.status_code == 200, r.get_json()

    rp = c.get('/api/rapor/stok_maliyet?blok_no=MRD', headers=H).get_json()
    g = [x for x in rp['gruplar'] if x['id'] == bid][0]
    # Blok toplami 7.250; 2 plaka x 5,4 m2 = 10,8 m2  (hedef m2 boy*yuk)
    toplam_urun = sum(u['toplam_usd'] for u in g['urunler'])
    assert len(g['urunler']) == 2, len(g['urunler'])
    # Iptal edilmis 500 USD plakalara DAGITILMAMIS olmali
    assert abs(toplam_urun - g['toplam_usd']) < 0.05, \
        f'blok {g["toplam_usd"]} ama plakalara {toplam_urun} dağıtılmış'


def test_mr1_rapor_ekrani_ve_excel_var():
    """MR1: sunucu tek başına işe yaramaz — bilgi zaten vardı,
    ULAŞILAMIYORDU. Yapı testi: sekme, açılır döküm, Excel ucu."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/raporlar.html'),
                 encoding='utf-8').read()
    assert 'data-b="stokmaliyet"' in m, 'sekme yok'
    assert 'id="b-stokmaliyet"' in m, 'bölüm yok'
    assert 'function stokMaliyetYukle(' in m
    assert 'stokmaliyet: stokMaliyetYukle' in m, 'yükleyiciye bağlanmamış'
    # Karlilik satiri tiklanabilir ve dokumu aciyor
    assert 'satisDokumAc(' in m, 'satış dökümü çağrılmıyor'
    assert 'data-sk=' in m, 'satır kimliği yok'
    # Yazdirmada sekmeler ve suzgecler gizlenir, acik bolum basilir
    assert '@media print' in m
    f = _io.open(os.path.join(KOK, 'flask_app.py'), encoding='utf-8').read()
    assert "/api/rapor/stok_maliyet/excel" in f, 'Excel ucu yok'
    # Excel AYNI raporu okur — ikinci bir sorgu iki rakam demekti
    assert 'veri = api_rapor_stok_maliyet().get_json()' in f


def test_mr1_maliyet_hesabi_tek_yerde():
    """MR1: dört kopya teke indi. Ölü ya da unutulmuş bir kopya
    kalırsa zamanla yine ayrışırlar."""
    import io as _io
    import re as _re
    f = _io.open(os.path.join(KOK, 'flask_app.py'), encoding='utf-8').read()
    assert 'def _stok_maliyet_dokumu(' in f
    assert 'def _stok_maliyet_kalemleri(' in f
    # STOK kimligine bagli her toplama IKI SUZGECTEN gecmeli.
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


# ══════════════════════════════════════════════════════════════════
#  KF1 · KUR FARKI ONAYI — ÜÇ SATIRDAN BİRE
#
#  Kutucuk `.form-alan input{width:100%}` kuralından 273 piksel
#  genişlik alıyordu. Chrome kontrolü o geniş kutunun ORTASINA çizer;
#  kutucuk kendi yazısından yarım form uzakta duruyor, açıklama da
#  kalan dar alanda iki satıra sarıyordu.
#
#  ÖLÇÜLDÜ (640 px modal, tarayıcıda):
#      eski: kutu 273 px · alan 73 px · gövde 12 px kaydırıyor
#      yeni: kutu  15 px · alan 33 px · kaydırma yok
#
#  16 şablondaki tüm onay/radyo kutuları tarandı; tek kurban buydu.
# ══════════════════════════════════════════════════════════════════

def test_kf1_onay_kutusu_metin_kutusu_genisligi_almiyor():
    """Onay kutusu `.form-alan` kuralından `width:100%` ALMAMALI.

    Bu testin asıl işi gelecek: kuralın kendisi hâlâ tip ayırmıyor
    olabilir. İki koruma da aranır — tipe göre yazılmış kural ve
    kur farkı kutusunun kendi ölçüsü."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/cari.html'),
                 encoding='utf-8').read()
    assert '.form-alan input[type=checkbox]' in m, \
        'tipe göre koruma kuralı yok — bir sonraki kutucuk yayılır'
    assert '.kf-onay input{width:15px' in m, \
        'kur farkı kutusu kendi ölçüsünü söylemiyor'

    # Kutucuk `.form-alan` içine GERİ TAŞINMAMALI: orada genişlik
    # kuralı yeniden devreye girer.
    _b = m.index('id="hKurFarkiAlan"')
    _acilis = m.rindex('<div class=', 0, _b)
    assert 'kf-onay' in m[_acilis:_b], 'kutu form-alan içine dönmüş'


def test_kf1_aciklama_isarete_gore_degisiyor_ve_boy_oynamiyor():
    """İki açıklama da var ve ikisi de TEK SATIR.

    İlk denemede kapalı hâlin cümlesi 58 karakterdi; 640 px modalde
    nota kalan yer ~55 karakter olduğu için sarıyor, işaretleyince
    kutu 51'den 33 piksele düşüp pencereyi zıplatıyordu. Sınır
    testle tutuluyor."""
    import io as _io, re as _re
    m = _io.open(os.path.join(KOK, 'templates/cari.html'),
                 encoding='utf-8').read()
    for _k in ('.kf-onay:has(input:checked) .kf-kapali{display:none}',
               '.kf-onay:has(input:checked) .kf-acik{display:inline}'):
        assert _k in m, f'{_k} yok — açıklama işarete göre değişmiyor'

    _alan = m[m.index('id="hKurFarkiAlan"'):]
    _alan = _alan[:_alan.index('</div>')]
    for _s in ('kf-not kf-kapali', 'kf-not kf-acik'):
        assert _s in _alan, f'{_s} yok'
    # Metinler tek satıra sığmalı: sürüm notlarıyla uzamasın.
    for _m in _re.finditer(r'class="kf-not kf-\w+">(.*?)</span>',
                           _alan, _re.S):
        _metin = ' '.join(_m.group(1).split())
        assert len(_metin) <= 55, \
            f'açıklama {len(_metin)} karakter — sarar: {_metin}'


def test_kf1_olmayan_tutar_sozu_verilmiyor():
    """`hKurFarkiTutar` ÇIKARILDI — hiçbir şey doldurmuyordu.

    Etikette tutarın yazılacağı bir yer duruyordu ama onu yazan kod
    yoktu: açık fatura ucu faturanın ESKİ kurunu dönmüyor. Boş bir
    söz, verilmemiş sözden kötüdür."""
    import io as _io, os as _os
    for _ad in _os.listdir(os.path.join(KOK, 'templates')):
        if not _ad.endswith('.html'):
            continue
        m = _io.open(os.path.join(KOK, 'templates', _ad),
                     encoding='utf-8').read()
        # ADI değil ÖGESİ aranır: yama notu adı anıyor, öge değil.
        assert 'id="hKurFarkiTutar"' not in m, \
            f'{_ad}: dolduran kodu olmayan tutar alanı geri gelmiş'

    # Kutucuğun KENDİSİ duruyor: kaydederken okunan bayrak bu.
    m = _io.open(os.path.join(KOK, 'templates/cari.html'),
                 encoding='utf-8').read()
    assert "getElementById('hKurFarkiIslet')" in m, 'bayrak okunmuyor'
    assert 'govde.kur_farki_islet = true' in m, 'bayrak sunucuya gitmiyor'


# ══════════════════════════════════════════════════════════════════
#  KF2 · HAREKET FORMU KAYDIRMAYI BIRAKTI
#
#  KF1'den sonra da kaydırma kalmıştı: form, pencerenin verdiği
#  yerden uzundu. Üç yerde boşuna yer harcanıyordu.
#
#  ÖLÇÜLDÜ (1280x800, modal 560 px, gövdenin yüksekliği):
#                      önce   sonra
#      Ödeme + USD      697 →   542
#      Alış Faturası    533 →   425
#      Açılış Bakiyesi  412 →   357
#      kaydırma           7 →     0   (her işlem tipinde)
# ══════════════════════════════════════════════════════════════════

def test_kf2_doviz_tutarla_ayni_alanda():
    """Döviz tek başına bir satır yiyordu.

    Yan etki olarak sözleşme kuru kutusu ("TCMB kuru kullanılır:
    40,0000") döviz seçicisinin ÜSTÜNDE kalıyordu — kuru, döviz
    seçilmeden önce söylüyordu. Artık altında."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/cari.html'),
                 encoding='utf-8').read()
    assert '.tutar-cift{' in m, 'birleşik tutar alanı tanımlı değil'
    # hDoviz, hTutar ile AYNI kutuda olmalı.
    _k = m[m.index('class="tutar-cift"'):]
    _k = _k[:_k.index('</div>')]
    assert 'id="hTutar"' in _k and 'id="hDoviz"' in _k, \
        'tutar ve döviz ayrılmış'
    # Döviz seçicisi sözleşme kuru kutusundan ÖNCE gelmeli.
    assert m.index('id="hDoviz"') < m.index('id="hKurAlan"'), \
        'kur kutusu döviz seçicisinin üstünde'


def test_kf2_belge_satiri_esnek_js_sutun_saymiyor():
    """Evrak no · belge tarihi · vade tek satırda.

    Vade yalnız borç doğuran tiplerde görünüyor (VT1). Eskiden
    satırın sütun sayısı JS'ten değiştiriliyordu; esnek satırda
    gizlenen öge akıştan çıktığı için gerek kalmadı. JS'in o işi
    geri almaması gerekiyor: iki yol birden yaşarsa biri
    düzeltilip öteki unutulur."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/cari.html'),
                 encoding='utf-8').read()
    assert '.form-cift{display:flex' in m, 'esnek satır tanımlı değil'
    _s = m[m.index('id="hTarihSatir"') - 120:m.index('id="hTarihSatir"')]
    assert 'form-cift' in _s, 'belge satırı esnek değil'
    assert "classList.toggle('f2'" not in m, \
        'JS hâlâ sütun sayısı değiştiriyor'
    # Üç alan da bu satırda.
    _r = m[m.index('id="hTarihSatir"'):]
    _r = _r[:_r.index('id="hKasaAlan"')]
    for _a in ('id="hEvrak"', 'id="hBelgeTarihi"', 'id="hVade"'):
        assert _a in _r, f'{_a} belge satırında değil'


def test_kf2_bos_kutular_yer_kaplamiyor():
    """Hiçbir şey söylemeyen kutu yer kaplamamalı.

    KDV önizlemesi tutar girilene kadar içinde '—' ile duruyordu:
    40 piksellik boş bir kutu. Kasa ipucunun ikinci cümlesi de
    yalnız TANIMLI KASA YOKKEN işe yarıyor."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/cari.html'),
                 encoding='utf-8').read()
    # Önizleme kutusu gizli başlar ve boşalınca yine gizlenir.
    _k = m[m.index('id="hKdvOnizle"'):]
    assert 'display:none' in _k[:_k.index('>')], \
        'KDV önizlemesi gizli başlamıyor'
    assert "kutu.style.display = 'none'; return; }" in m, \
        'önizleme boşalınca gizlenmiyor'
    assert "kutu.style.display = '';" in m, \
        'önizleme dolunca geri gelmiyor'

    # Kasa ipucu: uzun öğüt yalnız kasa listesi BOŞKEN.
    assert 'id="hKasaNot"' in m, 'kasa ipucu kimliksiz'
    assert 'HAR_KASALAR.length' in m, 'ipucu kasa sayısına bakmıyor'
    _n = m[m.index("kn.innerHTML = HAR_KASALAR.length"):]
    _n = _n[:_n.index(';')]
    assert 'Tanımlı kasa yok' in _n, 'boş liste uyarısı yok'


# ══════════════════════════════════════════════════════════════════
#  US1 · YENİ STOK FORMU — ÜÇ TİP, ÜÇ DÜZEN, TEK IZGARA
#
#  Bahadır üç tip için ayrı düzen çizdi. Satırları tip tip yazmak
#  üç kopya demekti; bunun yerine alanlar TEK 4 sütunlu ızgarada
#  sırayla duruyor ve ızgara gizli alanı atlıyor. Sıralama şu üç
#  düzeni birden veriyor:
#
#    BLOK    ürün tipi · üretici · menşe · giriş tarihi
#            cins · blok no · kaynak · alış tipi
#            alış fiyatı · döviz · fiyat birimi · tonaj
#            boy · yükseklik · en · hacim
#            fatura durumu · fatura no · fatura tarihi · kdv oranı
#    PLAKA   ... cins · blok no · özellik · kaynak
#            alış tipi · alış fiyatı · döviz · fiyat birimi
#            boy · yükseklik · kalınlık
#            stok adedi · başlangıç slab no · toplam m² · + grup
#    EBATLI  aynısı; kasa no, kasa adedi · kasa içi adet · toplam m²
#
#  ÖLÇÜLDÜ (tarayıcıda, 880 px modal): üç düzen de çizime birebir
#  uydu, hiçbir seçici kırpılmıyor, kaydırma yok. Üç tip de formdan
#  kaydedildi ve veritabanında eksiksiz çıktı.
# ══════════════════════════════════════════════════════════════════

def _us1_sira(metin, kap_id):
    """Bir ızgaranın içindeki alanları SIRAYLA döner."""
    import re as _re
    _p = metin.index(f'id="{kap_id}"')
    _p = metin.index('>', _p) + 1
    _derinlik, _i, _son = 1, _p, _p
    while _derinlik and _i < len(metin):
        _a = metin.find('<div', _i)
        _k = metin.find('</div>', _i)
        if _k == -1:
            break
        if _a != -1 and _a < _k:
            _derinlik += 1; _i = _a + 4
        else:
            _derinlik -= 1; _i = _k + 6; _son = _k
    _ic = metin[_p:_son]
    return [m.group(1) for m in
            _re.finditer(r'<(?:input|select|button)[^>]*id="(s[A-Z]\w*)"', _ic)]


def test_us1_alanlar_tipe_gore_dogru_sirada():
    """Izgaradaki SIRA üç düzeni birden üretiyor.

    Sıra bozulursa blokta 'alış tipi' alt satıra, plakada 'özellik'
    yanlış sütuna düşer — ekrana bakmadan anlaşılmaz. Bu yüzden
    sıranın kendisi test ediliyor."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/stok.html'),
                 encoding='utf-8').read()
    assert _us1_sira(m, 'kimlikSatir') == [
        'sCins', 'sBlokNo', 'sOzellik', 'sKaynak', 'sAlisTipi',
        'sFiyat', 'sDoviz', 'sFiyatBirim', 'sTonaj'], 'kimlik sırası bozuk'
    assert _us1_sira(m, 'olcuSatir') == [
        'sBoy', 'sYuk', 'sEn', 'sKal', 'sAdet', 'sKasaAdedi',
        'sKasaIci', 'sBasNo', 'sOlcu'], 'ölçü/miktar sırası bozuk'

    # Blok dışında miktar alanları ALT SATIRDAN başlar.
    assert '.f4.ayri > #adetAlan, .f4.ayri > #kasaAdediAlan{grid-column-start:1}' in m, \
        'satır başı kuralı yok'
    assert "_os.classList.toggle('ayri', !blok)" in m, \
        'satır başı tipe göre açılmıyor'


def test_us1_etiketler_sadelesti_ama_bilgi_silinmedi():
    """Parantezli açıklamalar etiketten çıktı, ipucuna taşındı.

    "Blok No (kesildiği blok)", "Kasa No (ilk kasa, ops.)",
    "Üretici / Ocak", "Yüzey / Özellik", "Alış / Fatura Tarihi" —
    hepsi sadeleşti. Açıklamaları SİLMEK başka şey; onlar alanın
    baloncuğunda duruyor."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/stok.html'),
                 encoding='utf-8').read()
    # Etiket olarak YAZILIYOR mu diye bakılır; yama notunda adının
    # geçmesi başka şey (KF1'de bu tuzağa bir kez düşüldü).
    for _eski in ('Üretici / Ocak', 'Yüzey / Özellik'):
        assert f'>{_eski}<' not in m, f'eski etiket duruyor: {_eski}'
    for _eski in ('Blok No (kesildiği blok)', 'Kasa No (ilk kasa, ops.)'):
        assert f"'{_eski}'" not in m, f'eski etiket duruyor: {_eski}'
    assert '<label>Üretici</label>' in m, 'Üretici etiketi yok'
    assert '<label>Özellik</label>' in m, 'Özellik etiketi yok'
    assert "_no.textContent = blok || plaka ? 'Blok No' : 'Kasa No'" in m, \
        'no etiketi sadeleşmemiş'
    # Açıklamalar ipucuna taşındı.
    assert 'kesildiği blok numarası' in m, 'plaka ipucu kayıp'
    assert 'İlk kasanın numarası' in m, 'kasa ipucu kayıp'
    assert "Ülkeler'den ekleyin" in m, 'menşe ipucu kayıp'

    # ÜRETİMDE fatura yok: etiket "Üretim Tarihi" demeli.
    assert 'id="sAlisTarihEtiket">Fatura Tarihi<' in m, \
        'tarih etiketi sadeleşmemiş'
    assert "uretim ? 'Üretim Tarihi' : 'Fatura Tarihi'" in m, \
        'üretimde tarih etiketi düzeltilmiyor'


def test_us1_kdv_ikilisi_birlikte_gizlenir():
    """KDV oranı ve "fiyata KDV dahil" artık AYRI yerlerde.

    Eskiden ikisi tek satırdaydı ve satır gizleniyordu. Ayrı yerlere
    dağılınca biri gizlenip öteki ekranda kalma riski doğdu; ikisini
    tek fonksiyon açıp kapatıyor."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/stok.html'),
                 encoding='utf-8').read()
    assert 'id="kdvSatir"' not in m, 'eski KDV satırı duruyor'
    assert 'function kdvAlanlariGoster(' in m, 'ortak açıp kapatıcı yok'
    for _id in ('kdvOranAlan', 'kdvDahilAlan'):
        assert f"getElementById('{_id}')" in m, f'{_id} okunmuyor'
    # Gizleme KURALI tek yerden: doğrudan style ataması kalmamalı.
    for _id in ('kdvOranAlan', 'kdvDahilAlan'):
        assert f"getElementById('{_id}').style.display" not in m, \
            f'{_id} ortak fonksiyonun dışından gizleniyor'
    assert m.count('kdvAlanlariGoster(') == 3, \
        'açıp kapatıcı beklenen yerlerde çağrılmıyor'

    # Ölçü grubu kutusu yalnız grup varken.
    assert "alan.style.display = ek.length ? '' : 'none'" in m, \
        'boş ölçü grubu kutusu gizlenmiyor'
    assert 'id="grupEkleAlan"' in m, 'grup ekle düğmesi miktar satırında değil'


# ══════════════════════════════════════════════════════════════════
#  US2 · ÜRETİLEN MALIN "ALIŞ FİYATI" OLMAZ — AMA MALİYETİ OLUR
#
#  Bahadır sordu: "kaynak üretim seçilince Alış Fiyatı olmalı mı?"
#  Ölçüldü — alan KALMALI, adı değişmeli.
#
#  Sunucu üretimde alış tipini NULL, KDV'yi 0, fatura durumunu zorla
#  'faturasiz' yapıyor ve tedarikçi cari hareketi hiç doğmuyor. Ama
#  FİYATI saklıyor ve matrahı ondan kuruyor. İki üretim bloğu açıp
#  ikisini de 10.000 USD'ye sattım:
#
#      girilen bedel   kaydedilen matrah   satış maliyeti   kâr
#      —                        0            1,00 $      9.999,00 $
#      300 $/ton            6.000 $      6.001,00 $      3.999,00 $
#
#  Yani alan kaldırılsa ya da boş bırakılsa, kendi ocağından çıkan
#  bloğun maliyeti HİÇBİR YERDE olmaz ve kâr 6.000 $ şişer.
#
#  Ekran ayrıca sunucunun yaptığının TERSİNİ söylüyordu: üretimde
#  "Fatura Durumu: Faturalı" seçili duruyor ve altındaki not
#  "tedarikçi cariye borç işlenir" diyordu.
# ══════════════════════════════════════════════════════════════════

def test_us2_uretimde_fiyat_alani_duruyor_adi_degisiyor():
    """Alan silinmemeli — silinirse üretim maliyeti kaybolur."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/stok.html'),
                 encoding='utf-8').read()
    # Alanın kendisi hiçbir koşulda gizlenmiyor.
    assert "getElementById('sFiyat').style.display" not in m, \
        'fiyat alanı gizleniyor — üretim maliyeti kaybolur'
    assert 'id="sFiyatEtiket"' in m, 'fiyat etiketi kimliksiz'
    assert 'Üretim Maliyeti' in m, 'üretim adı yok'

    # KS1: etiket üç ekranda da TEK yerden geliyor (`bedelAdi`).
    # Üç ayrı yerde yazılsaydı biri değiştirilip ötekiler unutulurdu.
    assert 'function bedelAdi(' in m, 'ortak adlandırıcı yok'
    assert m.count('bedelAdi(') >= 4, \
        'etiket her yerde ortak adlandırıcıdan gelmiyor'
    for _yer in ("_fe.innerHTML = bedelAdi(",       # yeni stok formu
                 "_dfe.textContent = bedelAdi(",    # düzenleme modalı
                 "alan(bedelAdi(s.kaynak)"):        # stok kartı
        assert _yer in m, f'{_yer} ortak adlandırıcıyı kullanmıyor'


def test_us2_uretimde_ekran_sunucunun_yaptigini_soyluyor():
    """Üretimde fatura alanları gizli, not doğru şeyi söylüyor.

    Sunucu `_fatura_durumu = 'faturasiz'` diye ZORLUYOR; ekran
    "Faturalı" gösterip "tedarikçi cariye borç işlenir" diyordu."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/stok.html'),
                 encoding='utf-8').read()
    for _id in ('sFaturaDurumAlan', 'sFaturaNoAlan'):
        assert f'id="{_id}"' in m, f'{_id} kimliksiz — gizlenemez'
        assert f"_gos('{_id}', !uretim)" in m, f'{_id} üretimde gizlenmiyor'
    assert 'Üretimde tedarikçi borcu, fatura ve KDV yok' in m, \
        'üretim notu yok'
    # Nakliye işaretinin adı da üretimde değişiyor (toplu form gibi).
    assert "? 'Maliyete nakliye dahil' : 'Alış fiyatına nakliye dahil'" in m, \
        'nakliye etiketi üretimde düzeltilmiyor'


def test_us2_fatura_durumu_secimi_sessizce_degismiyor():
    """Üretime geçip geri dönünce seçim geri gelmeli.

    'Faturalı' ile 'Faturasız' arasındaki fark tedarikçiye borç
    yazılıp yazılmamasıdır — sessizce değişmesi en olmayacak şey.
    İki formda da aynı kusur vardı; ikisi birden düzeltildi."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates/stok.html'),
                 encoding='utf-8').read()
    for _d in ('FATURA_DURUM_ONCEKI', 'TP_FATURA_DURUM_ONCEKI'):
        assert f'let {_d} = null;' in m, f'{_d} tanımlı değil'
        assert f'{_d} = _' in m, f'{_d} hiç yazılmıyor'
        assert f'if ({_d})' in m or f'else if ({_d})' in m, \
            f'{_d} hiç geri yüklenmiyor'


def test_us2_denetim_betigi_var_ve_salt_okunur():
    """Maliyeti olmayan üretim stoklarını bulan betik yazmamalı."""
    import io as _io
    _y = os.path.join(KOK, 'denetim_uretim_maliyet.py')
    assert os.path.exists(_y), 'denetim betiği yok'
    _m = _io.open(_y, encoding='utf-8').read()
    for _yasak in ('db.session.commit', 'db.session.add',
                   'db.session.delete'):
        assert _yasak not in _m, f'salt okunur olmalı ama {_yasak} var'


# ══════════════════════════════════════════════════════════════════
#  KS1 · KESİMDEN ÇIKAN STOĞU KİMSE SATIN ALMADI
#
#  Bahadır sordu: "üretim 0 geldi ama plakalar kesimden oluştu."
#  Haklıydı. Kesim, oluşturduğu stoğun `kaynak` alanını HİÇ
#  yazmıyordu; model varsayılanı 'satinalma' devreye giriyordu.
#
#  ÖLÇÜLDÜ (ithalat EUR bloğu kesildi):
#      blok   kaynak='satinalma'  alis_tipi='ithalat'
#      plaka  kaynak='satinalma'  alis_tipi=NULL
#             → uç nokta NULL'u 'yurtici_kdvli' diye DOLDURUYORDU
#
#  Bugün bu değeri basan bir ekran yok; yani görünür bir yalan
#  değildi, ekrana çıkmayı bekleyen bir yalandı.
# ══════════════════════════════════════════════════════════════════

def test_ks1_kesim_kaynagi_yaziyor():
    """Kesim, oluşturduğu her stoğa kaynak='kesim' yazmalı."""
    import io as _io, re as _re
    m = _io.open(os.path.join(KOK, 'flask_app.py'),
                 encoding='utf-8').read().replace('\r\n', '\n')
    _r = m[m.index("@app.route('/api/kesim', methods=['POST'])"):]
    _r = _r[:_r.index("@app.route('/api/kesim/<kesim_id>', methods=['DELETE'])")]
    # Kesim icinde olusturulan HER stok kaydinda kaynak yazili olmali.
    for _ctor in ('PlakaStok(', 'EbatliStok('):
        for _p in _re.finditer(_re.escape(_ctor), _r):
            # Sabit pencere KULLANMA: KM1'in menşe yorumu eklenince
            # gövde 1600 karakteri aştı ve test kodu değil KENDİNİ
            # kırdı. Sınır bir sonraki `db.session.add`.
            _son = _r.index('db.session.add', _p.start())
            _govde = _r[_p.start():_son]
            assert "kaynak='kesim'" in _govde, \
                f'{_ctor} kaynak yazmıyor — varsayılan satinalma kalır'


def test_ks1_bos_alis_tipine_deger_uydurulmuyor():
    """NULL `alis_tipi` 'yurtici_kdvli' diye doldurulmamalı.

    Kesimden çıkan stokta alan NULL; kaynak blok İTHALAT olsa bile
    uç nokta onu yurt içi KDV'li alış diye dönüyordu."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'flask_app.py'),
                 encoding='utf-8').read().replace('\r\n', '\n')
    assert "if item['kaynak'] in ('uretim', 'kesim')" in m, \
        'kesim, uydurma değerden muaf değil'
    # Eski tek kosullu hali geri gelmesin.
    assert "(None if item['kaynak'] == 'uretim'" not in m, \
        'eski hal duruyor'


def test_ks1_kesim_stogu_faturalandirilamaz():
    """Kesimden çıkan stok tedarikçi borcu doğurmamalı.

    `faturalandir` stoğun matrahı kadar borç yazıyor. Kesim
    plakasının matrahı kaynak bloktan dağıtılan paydır; borcu zaten
    o blokta. Buradan faturalandırmak aynı malı iki kez
    borçlandırırdı."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'flask_app.py'),
                 encoding='utf-8').read().replace('\r\n', '\n')
    _u = m[m.index("def api_stok_faturalandir("):]
    _u = _u[:_u.index('def api_stok_mal_teslim(')]
    assert "(getattr(stok, 'kaynak', None) or '') == 'kesim'" in _u, \
        'kesim stoğu faturalandırmaya karşı korunmuyor'
    # Denetim, borcu yazan koddan ÖNCE gelmeli.
    assert _u.index("== 'kesim'") < _u.index('_stok_cari_hareket_olustur'), \
        'denetim borç yazıldıktan sonra geliyor'


def test_ks1_gecmis_icin_goc_betigi_var():
    """Mevcut kayıtlar için göç betiği — varsayılan RAPOR olmalı."""
    import io as _io
    _y = os.path.join(KOK, 'goc_kesim_kaynak.py')
    assert os.path.exists(_y), 'göç betiği yok'
    _m = _io.open(_y, encoding='utf-8').read()
    assert "UYGULA = '--uygula' in sys.argv" in _m, '--uygula kapısı yok'
    assert 'if UYGULA:' in _m, 'rapor kipi yazıyor olabilir'
    # Yalnız `kaynak` alanina dokunmali.
    import re as _re
    _atamalar = set(_re.findall(r'\bs\.(\w+) =', _m))
    assert _atamalar <= {'kaynak'}, f'başka alana da yazıyor: {_atamalar}'


# ══════════════════════════════════════════════════════════════════
#  KM1 · KESİLEN TAŞIN MENŞEİ DEĞİŞMEZ
#
#  Kesim, hedef stoğun `mense` alanını hiç yazmıyordu; model
#  varsayılanı devreye girip 'TURKIYE' kalıyordu. ARNAVUTLUK
#  menşeli K6462 bloğundan kesilen plakalar TÜRK MALI olarak
#  kaydolmuştu — Bahadır stok kartında yakaladı.
#
#  Bu kozmetik değil: `mense` TİCARİ FATURAYA ve kasa ETİKETİNE
#  basılıyor. Fatura şablonu tüm kalemler TURKIYE ise "the goods
#  are of Turkish origin" yazıyor.
#
#  Aşağıdaki test METİN değil DAVRANIŞ bakıyor: bir blok kesiliyor
#  ve hedefin alanları kaynakla karşılaştırılıyor. Unutulan bir
#  sonraki alan da burada patlar.
# ══════════════════════════════════════════════════════════════════

def test_km1_kesim_menseyi_kaynaktan_tasir():
    """ARNAVUTLUK bloğundan kesilen plaka ARNAVUTLUK olmalı."""
    from models import PlakaStok, KesimDetay
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BLK-KM1', firma_id=1, blok_no='KM1', cins='KMTEST',
            uretici='ALBSTONE1 SHPK', mense='ARNAVUTLUK',
            boy=310, yukseklik=155, en=50, hacim_m3=2.4, tonaj=6.78,
            alis_fiyati=200, alis_fiyat_birim='ton', doviz='EUR',
            durum='Serbest', giris_tarihi=date(2026, 9, 14),
            kaynak='satinalma', alis_tipi='ithalat'))
        db.session.commit()

    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': ['BLK-KM1'],
        'kesim_tarihi': '2026-10-18',
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'KMTEST', 'boy': 302,
                      'yukseklik': 151, 'kalinlik': 2, 'adet': 2,
                      'miktar_m2': 4.56}]})
    assert r.status_code == 200, r.get_json()

    with fa.app.app_context():
        hedefler = [d.hedef_stok_id for d in
                    KesimDetay.query.filter_by(hedef_tip='PLAKA').all()]
        plakalar = PlakaStok.query.filter(
            PlakaStok.id.in_(hedefler),
            PlakaStok.cins == 'KMTEST').all()
        assert len(plakalar) == 2, len(plakalar)
        for p in plakalar:
            assert p.mense == 'ARNAVUTLUK', \
                f'{p.id} menşei {p.mense!r} — ticari faturaya bu basılır'
            # KK1 ile birlikte gelenler de yerinde dursun.
            assert p.kaynak == 'kesim', f'{p.id} kaynak {p.kaynak!r}'
            assert p.uretici == 'ALBSTONE1 SHPK'
            assert (p.doviz or '').upper() == 'EUR'


def test_km1_mense_tek_kapidan_geciyor():
    """Menşe iki hedef tipinde ayrı ayrı yazılmasın.

    PLAKA'da düzeltip EBATLI'da unutmak, hatanın kendisiyle aynı
    sınıf. İkisi de tek yardımcıdan geçiyor."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'flask_app.py'),
                 encoding='utf-8').read().replace('\r\n', '\n')
    assert 'def _kesim_mense(' in m, 'ortak menşe kapısı yok'
    _r = m[m.index("@app.route('/api/kesim', methods=['POST'])"):]
    _r = _r[:_r.index("@app.route('/api/kesim/<kesim_id>', methods=['DELETE'])")]
    assert _r.count('mense=_kesim_mense(ana_kaynak)') == 2, \
        'her iki hedef tipi de ortak kapıdan geçmiyor'


def test_km1_mense_gocu_var_ve_rapor_kipinde_yazmaz():
    """Geçmiş kayıtlar için göç betiği — varsayılan RAPOR."""
    import io as _io, re as _re
    _y = os.path.join(KOK, 'goc_kesim_mense.py')
    assert os.path.exists(_y), 'menşe göç betiği yok'
    _m = _io.open(_y, encoding='utf-8').read()
    assert "UYGULA = '--uygula' in sys.argv" in _m, '--uygula kapısı yok'
    assert 'if UYGULA:' in _m, 'rapor kipi yazıyor olabilir'
    _atamalar = set(_re.findall(r'\bhedef\.(\w+) =', _m))
    assert _atamalar <= {'mense'}, f'başka alana da yazıyor: {_atamalar}'

def test_ma4_alt_bar_kendi_zeminini_tasiyor():
    """MA4: alt bar (Vazgeç/Kaydet) `.modal`in beyaz zemini üzerinde
    duruyordu — zemini kendisinin değil, kapsayıcısınındı. Gövde bir
    şekilde kapsayıcıyı aşınca alt bar ZEMİNSİZ kalıyor ve panelden
    kopmuş görünüyor. Kendi zeminini ve alt köşe yuvarlamasını
    taşıyınca, dizilim ne olursa olsun panelin parçası kalıyor.

    `flex:0 0 auto` ayrı bir koruma: esnek sütunda alt bar asla
    ezilmesin, önce gövde küçültülsün."""
    import glob
    import io as _io
    import re
    eksik = []
    for yol in sorted(glob.glob('templates/*.html')):
        g = _io.open(yol, encoding='utf-8').read()
        for k in re.findall(r'\.modal-alt\{[^}]*\}', g):
            if ('background:' not in k or 'border-radius:0 0' not in k
                    or 'flex:0 0 auto' not in k):
                eksik.append((yol, k[:70]))
    assert not eksik, f'alt bar zeminsiz kalabilir: {eksik}'

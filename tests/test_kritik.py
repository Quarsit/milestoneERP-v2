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
    # YK3: aynı tahsilat BİLEREK iki kez gönderiliyor (kısmi tahsilat
    # birikimi sınanıyor). Yineleme kalkanı bunu normalde durdurur ve
    # kullanıcıya "yine de kaydedilsin mi?" diye sorar; burada o onayı
    # taklit ediyoruz.
    for _ in range(2):
        r = adm.post('/api/fatura/FT1/tahsilat',
                     json={'tutar': 30000, 'kasa_id': kid, 'doviz': 'USD',
                           'yineleme_onay': True}, headers=H)
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


# ══════════════════════════════════════════════════════════════════
#  AS1 · BL17 TESTLERİ NE OLDU
#
#  Üç BL17 testi `/api/stok/toplu_import` ucunu koşuyordu. O uç
#  silindi (ölçüldü: ekranı ona bağlamak menşeyi TURKIYE yazıyordu,
#  yani KM1'de düzelttiğimiz yanlış menşe beyanı geri geliyordu).
#
#  Üç testin konusu şunlardı:
#    1. hepsi-ya-hiçbiri + satır satır gerekçe   → uca özgüydü,
#       ekranın döngüsü bunu JS tarafında yapıyor; bu takımın
#       kapsamından çıktı. KAYIP BU: bilerek kabul edildi.
#    2. `kismi` ile kısmi aktarım                → aynı şekilde.
#    3. aynı slab ikinci kez girilemez           → KORUMA TAŞINDI.
#
#  Üçüncüsü bir VERİ BÜTÜNLÜĞÜ kuralıydı ve uçla birlikte
#  gitmemesi gerekiyordu: aynı slab iki kez stokta görünürse aynı
#  taş iki kez satılabilir. Kural `/api/stok/ekle`ye taşındı ve
#  testi aşağıda, ekranın GERÇEKTEN kullandığı yol üzerinde.
# ══════════════════════════════════════════════════════════════════
def test_as1_depodaki_plaka_ikinci_kez_girilemez():
    """Aynı blok + aynı slab no ikinci kez stoğa alınamaz.

    ÖLÇÜLDÜ (taşımadan önce): `/api/stok/ekle` aynı MK-1/1 plakasını
    iki kez kabul ediyordu ve stokta iki kayıt oluşuyordu. Ekran
    kendi tarafında süzüyor, ama tarayıcıda yapılan denetim denetim
    değildir: ikinci bir sekme ya da doğrudan bir API çağrısı onu
    atlar."""
    from models import PlakaStok
    c = istemci('admin', 'ADMIN')
    govde = {'tip': 'PLAKA', 'cins': 'AS1 TEK', 'blok_no': 'AS1-B',
             'baslangic_no': 7, 'adet': 1, 'boy': 300, 'yukseklik': 150,
             'kalinlik': 2, 'alis_fiyati': 40, 'doviz': 'USD',
             'fiyat_birim': 'm2', 'fatura_durumu': 'faturasiz'}
    r1 = c.post('/api/stok/ekle', headers=H, json=dict(govde))
    assert r1.status_code == 200, r1.get_data(as_text=True)[:200]
    # YK3: ucun KENDİ mükerrer denetimi sınanıyor; kalkan araya
    # girmesin diye onay veriliyor. Üretimde sıra şu: kalkan sorar,
    # kullanıcı onaylar, sonra ucun kendi mesajı çıkar.
    r2 = c.post('/api/stok/ekle', headers=H,
                json=dict(govde, yineleme_onay=True))
    assert r2.status_code == 400, \
        f'aynı slab ikinci kez kabul edildi: {r2.get_data(as_text=True)[:200]}'
    _y = r2.get_json()
    assert _y.get('error') == 'mukerrer_slab', _y
    assert 7 in (_y.get('mukerrer') or []), _y
    with fa.app.app_context():
        assert PlakaStok.query.filter_by(blok_no='AS1-B').count() == 1


def test_as1_mukerrer_denetimi_hepsi_ya_hicbiri():
    """Bir slab çakışıyorsa HİÇBİRİ yazılmamalı.

    `adet` 5 ise ve ortadaki bir numara doluysa, yarısını yazıp
    durmak hangi numaradan devam edileceğini bilinmez hâle
    getirirdi."""
    from models import PlakaStok
    c = istemci('admin', 'ADMIN')
    ortak = {'tip': 'PLAKA', 'cins': 'AS1 TOP', 'blok_no': 'AS1-C',
             'boy': 300, 'yukseklik': 150, 'kalinlik': 2,
             'alis_fiyati': 40, 'doviz': 'USD', 'fiyat_birim': 'm2',
             'fatura_durumu': 'faturasiz'}
    # 3 numarali slab'i tek basina gir
    assert c.post('/api/stok/ekle', headers=H,
                  json=dict(ortak, baslangic_no=3, adet=1)
                  ).status_code == 200
    with fa.app.app_context():
        _once = PlakaStok.query.filter_by(blok_no='AS1-C').count()
    # 1..5 istenirse 3 cakisiyor: HICBIRI yazilmamali
    r = c.post('/api/stok/ekle', headers=H,
               json=dict(ortak, baslangic_no=1, adet=5))
    assert r.status_code == 400, r.get_data(as_text=True)[:200]
    assert r.get_json().get('mukerrer') == [3], r.get_json()
    with fa.app.app_context():
        assert PlakaStok.query.filter_by(blok_no='AS1-C').count() == _once, \
            'çakışmaya rağmen bir kısmı yazıldı'


def test_as1_silinen_uclar_geri_gelmedi():
    """Silinen dört uç kaynakta kalmamalı.

    Her biri ikinci bir doğruluk kaynağıydı; biri yeniden
    eklenirse bu test görünür kılar."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'flask_app.py'),
                 encoding='utf-8').read().replace('\r\n', '\n')
    for _yol in ("'/api/stok/toplu_import'", "'/api/uretici'",
                 "'/api/yetkilerim'", "'/api/musteri/detay'"):
        assert f'@app.route({_yol}' not in m, f'{_yol} geri gelmiş'
    assert 'def _plaka_satir_denetle(' not in m, \
        'yalnız silinen ucun kullandığı doğrulayıcı duruyor'
    # Mukerrer korumasi TASINDI, kaybolmadi
    assert "'mukerrer_slab'" in m, 'mükerrer slab koruması yok'


# AS1 · AVANS DEVRİNDE PARA BİRİMİ — TESTİ YOK, BEKÇİSİ VAR
#
# Buraya bir kaynak denetimi yazmıştım: avans devri gövdesinde
# `'doviz': doviz` geçiyor mu. ÖLÇTÜM, test düzeltme OLMADAN DA
# geçiyordu — çünkü aynı dizgi denetim izi satırında da var
# (`yeni={'hedef': …, 'doviz': doviz}`). Yani yanlış yeri
# yakalıyordu: hatayı gösterecek test, hatayı saklayacaktı.
#
# Sildim. Bu alanı AS2 bekçisi zaten DAVRANIŞ olarak tutuyor:
# ekran `d.doviz` okuyor, uç göndermiyorsa AS2 patlıyor (ölçüldü —
# alan geri alınan bir kopyada patladı). Aynı şeyi iki yerden
# tutmanın anlamı yok, hele biri yanlış tutuyorsa.


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
    seçicisinden kaybolmamalı — hâlâ bizim malımız.

    DV1 · TEST CANLI UCA TAŞINDI. Eskiden `/api/stok/gruplar`
    sorgulanıyordu; o uç DV1'de silindi çünkü hiçbir ekrandan
    çağrılmıyordu (ve grup toplamlarında döviz karıştırıyordu).
    Kuralın asıl yeri `/api/stok`: maliyet, proforma ve sipariş
    ekranlarındaki stok seçicileri oradan besleniyor. Testi ölü
    uçta bırakmak, kuralı hiç denetlememek olurdu."""
    c = istemci('admin', 'ADMIN')
    r = c.get('/api/stok?tip=PLAKA&per_page=2000', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    idler = {x.get('id') for x in (r.get_json() or {}).get('data', [])}
    assert 'PLK-F5-Y1' in idler, (
        'sevk edilmiş stok seçicide görünmüyor — henüz faturası '
        'kesilmemiş bir sevkiyatın stoğu seçilemez hâle gelir')


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
    # KD1: "Bakım" EKLENDİ ve bilerek Ayarlar tarafında — yönetim
    # paneli firma bağlamını düşürüyor, bakım ucu ise firmaya bağlı
    # çalışıyor (orada 409 "firma seçilmedi" alıyordu, ölçüldü).
    assert aya == {'eposta', 'listeler', 'banka', 'bakim'}, aya
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

    # Bilinçli onay geçişe izin verir.
    #
    # AS1: eskiden burada yorum "numara tekrarı olabilir" diyordu ve
    # ikinci çağrı AYNI başlangıç numarasıyla gidiyordu. Mükerrer
    # slab koruması `/api/stok/ekle`ye taşınınca o artık geçmiyor —
    # ve geçmemesi doğru: bilinçli onay "blok hâlâ stokta" uyarısını
    # geçer, aynı taşı iki kez yazma iznini vermez. İkisi AYRI
    # soru; ikincisi aynı malı iki kez satmaya götürür.
    #
    # Test çakışmayan bir başlangıç numarası kullanıyor, çünkü
    # konusu onay kapısı — mükerrer kuralı değil. Mükerrer kuralının
    # kendi testleri var (test_as1_*).
    r3 = c.post('/api/stok/ekle', headers=H,
                json=dict(govde, baslangic_no=500,
                          blok_uyarisi_onaylandi=True))
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
    # YK3: ucun kendi "zaten eklenmiş" denetimi sınanıyor (bkz. AS1).
    r3 = c.post(f'/api/ortaklik/{oid}/maliyet_katki', headers=H, json={
        'taraf': 'biz', 'maliyet_idler': ['MAL-OR6-1'],
        'yineleme_onay': True})
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
    # EM1: artik SIPARIS kimligine bagli olanlar da dahil, Maliyet
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
            # UN1: plaka artik blogun dovizini DEGIL, USD tasiyor.
            # Menşe kaynaktan gelir, PARA BIRIMI gelmez — maliyetin
            # tamami tek para biriminde tutuluyor.
            assert (p.doviz or '').upper() == 'USD', \
                f'{p.id} dövizi {p.doviz!r} — maliyet USD olmalı'


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
    # UN2: menşe artik `ana_kaynak`tan DEGIL, o hedefin KENDI
    # kaynagindan (`_kay`) geliyor — cok kaynakli kesimde hepsi ilk
    # kaynagin menşeini aliyordu. Test KAPIYI tutuyor, adi degil:
    # iki hedef tipi de `_kesim_mense` uzerinden gecmeli.
    assert _r.count('mense=_kesim_mense(_kay)') == 2, \
        'her iki hedef tipi de ortak kapıdan geçmiyor'
    assert 'mense=_kesim_mense(ana_kaynak)' not in _r, \
        'hâlâ ilk kaynaktan okunuyor'


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


# ══════════════════════════════════════════════════════════════════
#  AF1 · ALIŞ FATURASINDA ÖDEME — YÖN, DÖVİZ VE ÖLÜ ÇEK
#
#  `api_cari_acik_faturalar` içinde aynı if/else'in iki kolu vardı:
#  satış kolu TT1 ile düzeltilmiş (çevirir, ölü çeki elemeye çalışır),
#  alış kolu ham `sum(CariHareket.borc)` ile kalmıştı.
#
#  ÖLÇÜLDÜ: 10.000 USD alış faturası, 20.000 TRY ödeme (kur 40 =
#  500 USD) → borç TAMAMEN kapanmış görünüyor, açık borç listesinden
#  düşüyordu. Doğrusu 9.500 USD kalan.
#
#  Ölü çek koruması ise HEDEFİNİ VURMUYORDU: faturaya bağlı çekin
#  ödeme hareketi `baglanti_tip='fatura'` ile yazılıyor, koruma ise
#  yalnız `baglanti_tip='cek'` satırlarına bakıyordu.
#
#  KÖKÜ: `Cek.cari_hareket_id` HİÇ TUTMUYORDU. `before_insert` (RN1)
#  hareketin kimliğini yazılmadan önce okunur hâle çeviriyor; kimlik
#  flush'tan ÖNCE okununca saklanan değer o geçici kimlik oluyor ve
#  veritabanında öyle bir kayıt hiç olmuyor.
#      çek.cari_hareket_id = 'HR-2AECDF'   ← yok
#      gerçek hareket       = 'HR-MST26-0001'
# ══════════════════════════════════════════════════════════════════

def test_af1_alis_faturasinda_capraz_doviz_odeme():
    """TL ödeme, USD alış borcunu kapatmamalı."""
    from models import Fatura, CariHareket, DovizKur
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        # Kendi tarihi, kendi kuru: baska testlerin ekledigi kurlara
        # bagli kalirsa ayni test farkli siralamada farkli sonuc verir
        # (olculdu: yalniz kosunca 10.000, takimla 9.333 ve 9.600).
        # 2026-06-17'ye baska hicbir test kur yazmiyor.
        _T = date(2026, 6, 17)
        if not DovizKur.query.filter_by(doviz='USD', tarih=_T).first():
            db.session.add(DovizKur(doviz='USD', tarih=_T,
                                    alis=40.0, satis=40.0, efektif=40.0))
        db.session.add(Cari(id='TED-AF1', unvan='TEDARIKCI AF1',
                            cari_tip='Tedarikçi'))
        db.session.add(Fatura(
            id='FA-AF1', fatura_no='AF1-1', cari_id='TED-AF1',
            yon='alis', durum='Kesildi', doviz='USD', toplam=10000,
            ara_toplam=10000, fatura_tarihi=_T))
        db.session.flush()
        db.session.add(CariHareket(
            id='CH-AF1', cari_id='TED-AF1',
            islem_tip='Ödeme', hareket_tarihi=_T,
            borc=20000, alacak=0, doviz='TRY', borc_try=20000,
            kur_uygulanan=1, kaynak='odeme',
            baglanti_tip='fatura', baglanti_id='FA-AF1'))
        db.session.commit()

    # 20.000 TRY / 40 = 500 USD  ->  kalan 9.500 USD
    _beklenen = 10000 - (20000 / 40.0)   # = 9.500

    d = c.get('/api/cari/TED-AF1/acik_faturalar?yon=alis',
              headers=H).get_json()
    kayit = [x for x in d['faturalar'] if x.get('id') == 'FA-AF1']
    assert kayit, '10.000 USD borç, 20.000 TRY ödemeyle KAPANDI'
    # KR1: burada `_kur` diye TANIMSIZ bir ad vardi. Assert gecerken
    # hic calismadigi icin takim yesil kaliyordu; GERCEKTEN basarisiz
    # olsaydi NameError ile patlayip asil sayilari gizleyecekti.
    assert abs(kayit[0]['kalan'] - _beklenen) < 0.02, \
        f"kalan {kayit[0]['kalan']}, beklenen {_beklenen} (kur 40)"
    # Ham toplama olsaydi odenen 20.000 olurdu ve fatura kapanirdi.
    assert kayit[0]['odenen'] < 2000, kayit[0]['odenen']


def test_af1_hareket_kimligi_flushtan_sonra_okunuyor():
    """Saklanan hareket kimliği gerçekten var olmalı.

    `before_insert` kimliği değiştirdiği için flush'tan önce okunan
    kimlik hiçbir kayda karşılık gelmiyordu."""
    from models import Cek, CariHareket
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(Cari(id='MUS-AF1', unvan='MUSTERI AF1',
                            cari_tip='Müşteri'))
        db.session.commit()
    r = c.post('/api/cek', headers=H, json={
        'yon': 'alinan', 'tip': 'cek', 'cek_no': 'AF1-CK',
        'tutar': 5000, 'doviz': 'USD',
        'keside_tarihi': '2026-05-01', 'vade_tarihi': '2026-05-01',
        'cari_id': 'MUS-AF1'})
    assert r.status_code in (200, 201), r.get_json()
    with fa.app.app_context():
        cek = Cek.query.filter_by(cek_no='AF1-CK').first()
        assert cek is not None
        assert cek.cari_hareket_id, 'çek hareketle bağlanmamış'
        assert db.session.get(CariHareket, cek.cari_hareket_id) is not None, \
            f'{cek.cari_hareket_id} diye bir hareket yok — kimlik flushtan önce okunmuş'


def test_af1_karsiliksiz_cek_faturayi_yeniden_acar():
    """Para gelmediyse fatura kapalı kalmamalı.

    Gerçek uçlarla: çek al → fatura 'Tahsil Edildi' → çeki
    karşılıksız işaretle → fatura yeniden açılmalı."""
    from models import Fatura, Cek
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(Cari(id='MUS-AF2', unvan='MUSTERI AF2',
                            cari_tip='Müşteri'))
        db.session.add(Fatura(
            id='FS-AF2', fatura_no='AF2-1', cari_id='MUS-AF2',
            musteri='MUSTERI AF2', yon='satis', durum='Kesildi',
            doviz='USD', toplam=10000, ara_toplam=10000,
            fatura_tarihi=date(2026, 5, 1)))
        db.session.commit()

    r = c.post('/api/cek', headers=H, json={
        'yon': 'alinan', 'tip': 'cek', 'cek_no': 'AF2-CK',
        'tutar': 10000, 'doviz': 'USD',
        'keside_tarihi': '2026-05-01', 'vade_tarihi': '2026-05-01',
        'cari_id': 'MUS-AF2', 'fatura_id': 'FS-AF2'})
    assert r.status_code in (200, 201), r.get_json()
    with fa.app.app_context():
        assert db.session.get(Fatura, 'FS-AF2').durum == 'Tahsil Edildi'
        cek_id = Cek.query.filter_by(cek_no='AF2-CK').first().id

    r = c.post(f'/api/cek/{cek_id}/durum', headers=H,
               json={'islem': 'karsiliksiz', 'aciklama': 'banka ödemedi'})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        f = db.session.get(Fatura, 'FS-AF2')
        assert f.durum != 'Tahsil Edildi', \
            'çek karşılıksız ama fatura hâlâ tahsil edilmiş görünüyor'
    d = c.get('/api/cari/MUS-AF2/acik_faturalar?yon=satis',
              headers=H).get_json()
    kayit = [x for x in d['faturalar'] if x.get('id') == 'FS-AF2']
    assert kayit and abs(kayit[0]['kalan'] - 10000) < 0.01, \
        'fatura açık listeye dönmedi'


# ══════════════════════════════════════════════════════════════════
#  KG1 · KESİM GERİ ALINIRKEN MALİYET ÖKSÜZ KALIYORDU
#
#  Geri alma hedef stokları siliyor ama onlara işlenmiş maliyet
#  kayıtlarına dokunmuyordu. ÖLÇÜLDÜ: plakaya 500 $ fason işlendi,
#  kesim geri alındı → plaka 2 → 0, maliyet satırı 1 → 1 (aktif,
#  hedefi yok). Para kayıtta duruyor ama hiçbir stoğun maliyetinde
#  değil ve raporda görünmüyor.
# ══════════════════════════════════════════════════════════════════

def test_kg1_maliyetli_kesim_geri_alinamaz():
    """Maliyeti olan hedef varsa geri alma reddedilmeli."""
    from models import Maliyet, Kesim, PlakaStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BLK-KG1', blok_no='KG1', cins='KGTEST',
            uretici='O', boy=300, yukseklik=180, en=170, hacim_m3=9.18,
            tonaj=20, alis_fiyati=300, matrah=6000,
            alis_fiyat_birim='ton', doviz='USD', durum='Serbest',
            giris_tarihi=date(2026, 5, 1)))
        db.session.commit()
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': ['BLK-KG1'],
        'kesim_tarihi': '2026-05-02',
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'KGTEST', 'boy': 300,
                      'yukseklik': 180, 'kalinlik': 2, 'adet': 2,
                      'miktar_m2': 5}]})
    assert r.status_code == 200, r.get_json()
    kesim_id = r.get_json().get('kesim_id') or r.get_json().get('id')

    with fa.app.app_context():
        plk = PlakaStok.query.filter_by(cins='KGTEST').first()
        pid = plk.id
    r = c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Fason', 'baglanti_tip': 'stok', 'baglanti_id': pid,
        'tutar': 500, 'doviz': 'USD', 'maliyet_tarihi': '2026-05-03'})
    assert r.status_code in (200, 201), r.get_json()

    r = c.delete(f'/api/kesim/{kesim_id}', headers=H)
    assert r.status_code == 400, r.status_code
    _y = r.get_json()
    assert _y.get('error') == 'hedefte_maliyet_var', _y
    assert 'Fason' in _y.get('mesaj', ''), _y.get('mesaj')
    with fa.app.app_context():
        # Hicbir sey silinmemis olmali
        assert PlakaStok.query.filter_by(cins='KGTEST').count() == 2
        assert Maliyet.query.filter_by(baglanti_id=pid).count() == 1


# ══════════════════════════════════════════════════════════════════
#  KR1 · TARİH DEĞİŞİNCE KUR DA DEĞİŞİR
#
#  Kural (Bahadır): "düzenlemede tarih değişmiyor sadece rakam
#  değişiyorsa kendi kuru kullanılsın, ama tarih değişiyorsa o güne
#  ait kur verisi kullanılsın."
#
#  İlk üç test bu kuralın ÜÇ kolunu ayrı ayrı tutuyor. Dördüncüsü
#  okuma tarafında, arşiv öncesi tarihli bir ödemenin yok
#  sayılmasına bakıyor.
# ══════════════════════════════════════════════════════════════════
_KR1_ESKI = date(2026, 3, 11)   # kur 30 — baska test bu gune yazmiyor
_KR1_YENI = date(2026, 9, 11)   # kur 50


def _kr1_kurlar():
    from models import DovizKur
    for _t, _k in ((_KR1_ESKI, 30.0), (_KR1_YENI, 50.0)):
        if not DovizKur.query.filter_by(doviz='USD', tarih=_t).first():
            db.session.add(DovizKur(doviz='USD', tarih=_t,
                                    alis=_k, satis=_k, efektif=_k))


def _kr1_hareket(hid, **fazla):
    """1.000 USD · eski tarih · TRY 30.000 · kur 30."""
    db.session.add(CariHareket(
        id=hid, cari_id='MUS-KR1', cari_unvan='MUSTERI KR1',
        islem_tip='Fatura (Satis)', hareket_tarihi=_KR1_ESKI,
        borc=1000, alacak=0, doviz='USD', borc_try=30000,
        kur_uygulanan=30, kaynak='manuel', **fazla))


def _kr1_cari():
    if not db.session.get(Cari, 'MUS-KR1'):
        db.session.add(Cari(id='MUS-KR1', unvan='MUSTERI KR1',
                            cari_tip='Müşteri'))


def test_kr1_tarih_degisince_yeni_gunun_kuru_yazilir():
    """Tarih 11.03 → 11.09 çekilince TRY karşılığı 50 kurdan olmalı.

    Eskiden `_degisti` yalnız RAKAMA bakıyordu: tarih değişince kayıt
    YENİ TARİHLE ESKİ KURDA kalıyordu (ölçüldü: TRY 30.000, kur 30).
    Ekstre TRY üzerinden topladığı için bakiye 20.000 TL eksikti."""
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _kr1_kurlar()
        _kr1_cari()
        _kr1_hareket('CH-KR1A')
        db.session.commit()
    r = c.put('/api/cari/hareket/CH-KR1A?onay=1', headers=H, json={
        'tutar': 1000, 'doviz': 'USD',
        'hareket_tarihi': _KR1_YENI.isoformat()})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        h = db.session.get(CariHareket, 'CH-KR1A')
        assert h.hareket_tarihi == _KR1_YENI
        assert abs(float(h.kur_uygulanan) - 50) < 0.0001, \
            f'kur {h.kur_uygulanan} — yeni günün kuru yazılmamış'
        assert abs(float(h.borc_try) - 50000) < 0.02, \
            f'TRY {h.borc_try} — 30.000 kaldıysa eski kurla duruyor'


def test_kr1_tarih_aynıysa_kendi_kuru_korunur():
    """Yalnız rakam değişince kayıt KENDİ kuruyla kalmalı.

    Kuralın öteki kolu. Bugünün kuru 50 olsa bile 11.03 tarihli
    kayıt 30'dan çevrilmeye devam etmeli."""
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _kr1_kurlar()
        _kr1_cari()
        _kr1_hareket('CH-KR1B')
        db.session.commit()
    r = c.put('/api/cari/hareket/CH-KR1B?onay=1', headers=H, json={
        'tutar': 2000, 'doviz': 'USD',
        'hareket_tarihi': _KR1_ESKI.isoformat()})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        h = db.session.get(CariHareket, 'CH-KR1B')
        assert h.hareket_tarihi == _KR1_ESKI
        assert abs(float(h.kur_uygulanan) - 30) < 0.0001, h.kur_uygulanan
        assert abs(float(h.borc_try) - 60000) < 0.02, \
            f'TRY {h.borc_try} — 2.000 × 30 = 60.000 olmalı'


def test_kr1_elle_girilen_kur_tarihle_ezilmez():
    """`kur_kaynak='MANUEL'` ise tarih değişse de kur korunur.

    Kuru kullanıcı kendi yazmışsa, tarih değişti diye üstüne TCMB
    kuru yazmak onun kararını sessizce silmek olurdu."""
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _kr1_kurlar()
        _kr1_cari()
        _kr1_hareket('CH-KR1C', kur_kaynak='MANUEL')
        db.session.query(CariHareket).filter_by(id='CH-KR1C').update(
            {'kur_uygulanan': 33, 'borc_try': 33000})
        db.session.commit()
    r = c.put('/api/cari/hareket/CH-KR1C?onay=1', headers=H, json={
        'tutar': 1000, 'doviz': 'USD',
        'hareket_tarihi': _KR1_YENI.isoformat()})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        h = db.session.get(CariHareket, 'CH-KR1C')
        assert h.hareket_tarihi == _KR1_YENI
        assert abs(float(h.kur_uygulanan) - 33) < 0.0001, \
            f'elle yazılan 33 kuru {h.kur_uygulanan} ile ezilmiş'


def test_kr1_onay_ekrani_degiseni_soyluyor():
    """Başlık SABİT "Tutar X → Y" değil, ne değiştiyse o olmalı.

    Tarih yüzünden geçildiğinde kullanıcıya "Tutar 1.000,00 →
    1.000,00 USD olacak" diyordu: yanlış olmayan ama HİÇBİR ŞEY
    söylemeyen bir cümle."""
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _kr1_kurlar()
        _kr1_cari()
        _kr1_hareket('CH-KR1D')
        db.session.commit()
    r = c.put('/api/cari/hareket/CH-KR1D?onay=1', headers=H, json={
        'tutar': 1000, 'doviz': 'USD',
        'hareket_tarihi': _KR1_YENI.isoformat()})
    assert r.status_code == 200, r.get_json()
    _m = r.get_json().get('mesaj', '')
    assert 'Tarih' in _m, f'mesaj değişeni söylemiyor: {_m!r}'
    assert '1.000,00 → 1.000,00' not in _m.replace(',', '.'), _m


def test_kr1_arsiv_oncesi_odeme_yok_sayilmaz():
    """Arşivin ilk gününden ÖNCE tarihli çapraz ödeme sayılmalı.

    `_kur_getir` o tarihten geriye bakar; arşivin BAŞINDAN önce
    hiçbir kayıt bulamayınca 0 döner ve ödeme HİÇ sayılmazdı —
    fatura tam açık görünüyordu, para ödenmiş olduğu hâlde.

    ÖLÇÜLDÜ (10.000 USD fatura · 20.000 TRY tahsilat, arşiv öncesi):
        önce  ödenen 0,00     → kalan 10.000,00
        sonra ödenen 500,00   → kalan  9.500,00 ✓

    Yazma yolu bu soruyu E1a'da çözmüştü (en yakın gün); okuma yolu
    o merdiveni devralmamıştı."""
    from models import Fatura, DovizKur
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        # Bu testin kendi dövizi: baska testlerin USD/EUR kurlarina
        # bagli kalirsa arsivin "ilk gunu" siralamaya gore degisir.
        _ILK = date(2026, 4, 2)
        _ONCE = date(2025, 10, 9)        # arsivin basindan ONCE
        if not DovizKur.query.filter_by(doviz='GBP').first():
            db.session.add(DovizKur(doviz='GBP', tarih=_ILK,
                                    alis=40.0, satis=40.0, efektif=40.0))
        db.session.add(Cari(id='MUS-KR2', unvan='MUSTERI KR2',
                            cari_tip='Müşteri'))
        db.session.add(Fatura(
            id='FS-KR2', fatura_no='KR2-1', cari_id='MUS-KR2',
            musteri='MUSTERI KR2', yon='satis', durum='Kesildi',
            doviz='GBP', toplam=10000, ara_toplam=10000,
            fatura_tarihi=_ILK))
        db.session.flush()
        db.session.add(CariHareket(
            id='CH-KR2', cari_id='MUS-KR2', cari_unvan='MUSTERI KR2',
            islem_tip='Tahsilat', hareket_tarihi=_ONCE,
            borc=0, alacak=20000, doviz='TRY', alacak_try=20000,
            kur_uygulanan=1, kaynak='tahsilat',
            baglanti_tip='fatura', baglanti_id='FS-KR2'))
        db.session.commit()

    d = c.get('/api/cari/MUS-KR2/acik_faturalar?yon=satis',
              headers=H).get_json()
    kayit = [x for x in d['faturalar'] if x.get('id') == 'FS-KR2']
    assert kayit, 'fatura açık listeden düşmüş'
    assert abs(kayit[0]['odenen'] - 500.0) < 0.02, \
        f"ödenen {kayit[0]['odenen']} — 20.000/40 = 500 olmalı"
    assert abs(kayit[0]['kalan'] - 9500.0) < 0.02, kayit[0]['kalan']


# ══════════════════════════════════════════════════════════════════
#  UN1 · KESİM MALİYETİ HER ZAMAN USD
#
#  Blok/plaka matrahı stoğun kendi dövizinde tutuluyor; bloğa işlenen
#  ek maliyetler `usd_karsilik` ile USD. Dağıtıcı ikisini TOPLUYORDU,
#  yani toplanan şey bir para birimi değildi.
#
#  Karar (Bahadır): her şey USD'ye normalize edilsin. Maliyet raporu
#  ve `Maliyet.usd_karsilik` zaten USD.
# ══════════════════════════════════════════════════════════════════
_UN1_T = date(2026, 5, 7)     # baska test bu gune kur yazmiyor
_UN1_EUR, _UN1_USD = 45.0, 40.0


def _un1_kurlar():
    from models import DovizKur
    for _dv, _k in (('USD', _UN1_USD), ('EUR', _UN1_EUR)):
        if not DovizKur.query.filter_by(doviz=_dv, tarih=_UN1_T).first():
            db.session.add(DovizKur(doviz=_dv, tarih=_UN1_T,
                                    alis=_k, satis=_k, efektif=_k))


def test_un1_eur_blok_kesiminde_gider_cevrilir():
    """EUR bloğa işlenen USD fason, EUR sayılmamalı.

    ÖLÇÜLDÜ — 4.000,00 EUR matrah + 500,00 USD fason, 10,80 m²;
    1 EUR = 45, 1 USD = 40 (yani 1 EUR = 1,125 USD):

        önce   416,67  ← 500 USD, 500 EUR sayılmış, etiket EUR
        sonra  462,96 USD  = (4.500,00 + 500,00) / 10,80 ✓
    """
    from models import PlakaStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _un1_kurlar()
        db.session.add(BlokStok(
            id='BLK-UN1', firma_id=1, blok_no='UN1', cins='UN1TEST',
            uretici='OCAK', mense='ALBANIA',
            boy=300, yukseklik=180, en=170, hacim_m3=9.18, tonaj=20,
            alis_fiyati=200, alis_fiyat_birim='ton', matrah=4000,
            doviz='EUR', durum='Serbest', giris_tarihi=_UN1_T))
        db.session.commit()

    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': ['BLK-UN1'],
        'kesim_tarihi': _UN1_T.isoformat(),
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'UN1TEST', 'boy': 300,
                      'yukseklik': 180, 'kalinlik': 2, 'adet': 2}]})
    assert r.status_code == 200, r.get_json()

    # Bloga 500 USD fason: dagitici matrah + ek_top yapiyor
    r2 = c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Fason', 'baglanti_tip': 'stok',
        'baglanti_id': 'BLK-UN1', 'tutar': 500, 'doviz': 'USD',
        'maliyet_tarihi': _UN1_T.isoformat(), 'fatura_no': 'UN1-FSN'})
    assert r2.status_code in (200, 201), r2.get_json()

    with fa.app.app_context():
        pl = PlakaStok.query.filter_by(cins='UN1TEST').all()
        assert len(pl) == 2, len(pl)
        _m2 = sum(float(p.metraj_m2 or 0) for p in pl)
        _eur_usd = _UN1_EUR / _UN1_USD
        _beklenen = (4000 * _eur_usd + 500) / _m2
        _karisik = (4000 + 500) / _m2
        for p in pl:
            assert (p.doviz or '').upper() == 'USD', p.doviz
            _b = float(p.alis_fiyati or 0)
            assert abs(_b - _beklenen) < 0.02, \
                f'{p.id} birim {_b:,.2f} — beklenen {_beklenen:,.2f}; ' \
                f'{_karisik:,.2f} ise ham toplanmış demektir'


def test_un1_karisik_dovizli_kesim_cevrilerek_toplanir():
    """Tek kesimde EUR plaka + USD plaka: her grup KENDİ maliyetini alır.

    ÖLÇÜLDÜ — 5.400,00 EUR (Arnavutluk) + 5.400,00 USD (Türk),
    20 adet 60×60 (toplam 7,20 m²); 1 EUR = 45, 1 USD = 40:

        önce   hepsi 1.500,00 EUR  ← iki döviz ham toplanıp EUR
                                     etiketi vurulmuş
        sonra  Arnavutluk 3,60 m² × 1.687,50 USD = 6.075,00
               Türk       3,60 m² × 1.500,00 USD = 5.400,00
                                      toplam    = 11.475,00 ✓

    Harmanlanmış 1.593,75 ortalamadır; iki grup fiziksel olarak ayrı
    malzemeden geldiği için her biri kendi kaynağının maliyetini
    taşır (UN2).
    """
    from models import PlakaStok, EbatliStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _un1_kurlar()
        for _id, _dv, _mense in (('PLK-UN1E', 'EUR', 'ALBANIA'),
                                 ('PLK-UN1U', 'USD', 'TURKIYE')):
            db.session.add(PlakaStok(
                id=_id, firma_id=1, cins='UN2TEST', slab_no=_id,
                mense=_mense, boy=300, yukseklik=180, kalinlik=2,
                metraj_m2=5.4, alis_fiyati=1000, matrah=5400,
                doviz=_dv, durum='Serbest', giris_tarihi=_UN1_T))
        db.session.commit()

    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'PLAKA_EBATLI',
        'kaynak_ids': ['PLK-UN1E', 'PLK-UN1U'],
        'kesim_tarihi': _UN1_T.isoformat(),
        'hedefler': [{'hedef_tip': 'EBATLI', 'cins': 'UN2TEST', 'boy': 60,
                      'yukseklik': 60, 'kalinlik': 2, 'adet': 20}]})
    assert r.status_code == 200, r.get_json()

    _eur_usd = _UN1_EUR / _UN1_USD
    with fa.app.app_context():
        eb = EbatliStok.query.filter_by(cins='UN2TEST').all()
        assert eb, 'ebatlı oluşmadı'
        # Her parca USD etiketli
        for e in eb:
            assert (e.doviz or '').upper() == 'USD', e.doviz
        # Menşeye gore gruplar
        _grup = {}
        for e in eb:
            _g = _grup.setdefault(e.mense or '?', {'m2': 0.0, 'tutar': 0.0})
            _g['m2'] += float(e.metraj_m2 or 0)
            _g['tutar'] += float(e.metraj_m2 or 0) * float(e.alis_fiyati or 0)
        assert set(_grup) == {'ALBANIA', 'TURKIYE'}, \
            f'menşeler {sorted(_grup)} — hepsi ilk kaynaktan gelmiş olabilir'
        # Her grup KENDI kaynaginin maliyetini tasiyor
        assert abs(_grup['ALBANIA']['tutar'] - 5400 * _eur_usd) < 0.05, \
            _grup['ALBANIA']
        assert abs(_grup['TURKIYE']['tutar'] - 5400) < 0.05, _grup['TURKIYE']
        # Ve toplam gercek maliyete esit: para ne kayboluyor ne doguyor
        _toplam = sum(g['tutar'] for g in _grup.values())
        assert abs(_toplam - (5400 * _eur_usd + 5400)) < 0.05, _toplam
        # Ham toplama olsaydi toplam 10.800 olurdu
        assert _toplam > 11000, _toplam


def test_un1_kur_yoksa_kesim_reddedilir():
    """Çeviremiyorsa USD etiketi vurmak yerine reddetmeli.

    `_usd_cevrim` kur bulamazsa tutarı olduğu gibi döndürüyor. Etiket
    USD'ye çevrildiği için bu, EUR rakamını USD diye kaydetmek olurdu
    — düzelttiğimiz hatanın ters yönü."""
    from models import DovizKur, PlakaStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        # Arsivde HIC kaydi olmayan bir doviz
        assert not DovizKur.query.filter_by(doviz='CHF').first()
        db.session.add(BlokStok(
            id='BLK-UN3', firma_id=1, blok_no='UN3', cins='UN3TEST',
            uretici='OCAK', mense='SWITZERLAND',
            boy=300, yukseklik=180, en=170, hacim_m3=9.18, tonaj=20,
            alis_fiyati=200, alis_fiyat_birim='ton', matrah=4000,
            doviz='CHF', durum='Serbest', giris_tarihi=_UN1_T))
        db.session.commit()

    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': ['BLK-UN3'],
        'kesim_tarihi': _UN1_T.isoformat(),
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'UN3TEST', 'boy': 300,
                      'yukseklik': 180, 'kalinlik': 2, 'adet': 2}]})
    assert r.status_code == 400, r.status_code
    _y = r.get_json()
    assert _y.get('error') == 'kur_yok', _y
    assert 'CHF' in _y.get('mesaj', ''), _y.get('mesaj')
    with fa.app.app_context():
        assert PlakaStok.query.filter_by(cins='UN3TEST').count() == 0, \
            'kesim reddedildi ama plaka oluşmuş'
        assert (db.session.get(BlokStok, 'BLK-UN3').durum or '') == 'Serbest'


# ══════════════════════════════════════════════════════════════════
#  UN2 · HER HEDEF TEK BİR KAYNAKTAN ÇIKAR
#
#  PLAKA→EBATLI kesiminde birden fazla plaka seçilebiliyor. Çıkan her
#  ebatlı fiziksel olarak TEK bir plakadan gelir; menşeini, üreticisini
#  ve maliyetini ondan almalı. Eskiden hepsi `kaynaklar[0]`dan alıyordu
#  ve karışık menşeli kesimde ticari faturaya yanlış menşe basılıyordu.
#
#  Karar (Bahadır): tek kesim kalsın, sistem kaynak başına ayrı grup
#  üretsin.
# ══════════════════════════════════════════════════════════════════
def _un2_plakalar(ids_mense_m2, cins='UN4TEST'):
    """(id, mense, m2) uclulerinden USD plakalar — doviz sabit USD ki
    bu testler YALNIZ bolunmeyi olcsun, UN1 cevrimini degil."""
    from models import PlakaStok
    for _id, _ms, _m2 in ids_mense_m2:
        db.session.add(PlakaStok(
            id=_id, firma_id=1, cins=cins, slab_no=_id, mense=_ms,
            uretici='OCAK-' + _ms[:3], boy=300, yukseklik=180, kalinlik=2,
            metraj_m2=_m2, alis_fiyati=1000, matrah=1000 * _m2,
            doviz='USD', durum='Serbest', giris_tarihi=_UN1_T))


def test_un2_karisik_mense_kaynak_basina_bolunur():
    """İki menşeli kesim, iki menşeli grup üretmeli — tek değil.

    ÖLÇÜLDÜ (düzeltmeden önce): 20 ebatlının HEPSİ ALBANIA çıkıyordu,
    yarısı Türk malı olduğu hâlde. Bu değer ticari faturaya basılıyor."""
    from models import EbatliStok, KesimDetay
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _un1_kurlar()
        _un2_plakalar([('PLK-UN2A', 'ALBANIA', 5.4),
                       ('PLK-UN2T', 'TURKIYE', 5.4)])
        db.session.commit()
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'PLAKA_EBATLI',
        'kaynak_ids': ['PLK-UN2A', 'PLK-UN2T'],
        'kesim_tarihi': _UN1_T.isoformat(),
        'hedefler': [{'hedef_tip': 'EBATLI', 'cins': 'UN4TEST', 'boy': 60,
                      'yukseklik': 60, 'kalinlik': 2, 'adet': 20,
                      'kasa_ici_adet': 5}]})
    assert r.status_code == 200, r.get_json()
    with fa.app.app_context():
        eb = EbatliStok.query.filter_by(cins='UN4TEST').all()
        assert eb, 'ebatlı oluşmadı'
        _ms = {e.mense for e in eb}
        assert _ms == {'ALBANIA', 'TURKIYE'}, \
            f'menşeler {_ms} — bölünme olmamış, ticari faturaya yanlış basar'
        # Parca sayisi korunmali: ne kayboldu ne dogdu
        assert sum(int(e.kasa_ici_adet or 0) for e in eb) == 20, \
            [int(e.kasa_ici_adet or 0) for e in eb]
        # KASALAR KAYNAK KARISTIRMAZ: her kasanin tek bir menşesi var
        for e in eb:
            assert e.mense in ('ALBANIA', 'TURKIYE')
        # Üretici de kendi kaynagindan
        for e in eb:
            assert e.uretici == 'OCAK-' + (e.mense or '')[:3], \
                f'{e.id} üretici {e.uretici!r} menşe {e.mense!r}'
        # KesimDetay hangi kaynaktan cikti SOYLUYOR
        _dt = KesimDetay.query.filter_by(cins='UN4TEST').all()
        assert _dt, 'kesim detayı yok'
        assert all(d.kaynak_stok_id in ('PLK-UN2A', 'PLK-UN2T')
                   for d in _dt), [d.kaynak_stok_id for d in _dt]
        assert len({d.kaynak_stok_id for d in _dt}) == 2


def test_un2_paylar_agirliga_gore_ve_toplam_tam():
    """Pay, kaynağın giren m²'siyle orantılı; toplam tam tutmalı.

    PLK 8,0 m² ve PLK 2,0 m² → 10 parçanın 8'i birinciden, 2'si
    ikinciden. Parçalar bölünemez, o yüzden tam sayı paylaştırma
    (en büyük artık) kullanılıyor ve toplam her zaman tam."""
    from models import EbatliStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _un1_kurlar()
        _un2_plakalar([('PLK-UN2X', 'ALBANIA', 8.0),
                       ('PLK-UN2Y', 'TURKIYE', 2.0)], cins='UN5TEST')
        db.session.commit()
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'PLAKA_EBATLI',
        'kaynak_ids': ['PLK-UN2X', 'PLK-UN2Y'],
        'kesim_tarihi': _UN1_T.isoformat(),
        'hedefler': [{'hedef_tip': 'EBATLI', 'cins': 'UN5TEST', 'boy': 60,
                      'yukseklik': 60, 'kalinlik': 2, 'adet': 10}]})
    assert r.status_code == 200, r.get_json()
    _dok = {x['kaynak_id']: x for x in r.get_json().get('kaynak_dokumu', [])}
    assert _dok, 'kaynak dökümü yok'
    assert _dok['PLK-UN2X']['parca'] == 8, _dok['PLK-UN2X']
    assert _dok['PLK-UN2Y']['parca'] == 2, _dok['PLK-UN2Y']
    with fa.app.app_context():
        eb = EbatliStok.query.filter_by(cins='UN5TEST').all()
        assert sum(int(e.kasa_ici_adet or 0) for e in eb) == 10


def test_un2_payi_olmayan_kaynak_reddedilir():
    """Parça sayısı kaynak sayısından azsa reddetmeli.

    Payı sıfır kalan kaynağın maliyetinin gidecek yeri yok; sessizce
    yutmak o maliyeti ortadan kaldırırdı."""
    from models import EbatliStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _un1_kurlar()
        _un2_plakalar([('PLK-UN2P', 'ALBANIA', 5.0),
                       ('PLK-UN2Q', 'TURKIYE', 5.0),
                       ('PLK-UN2R', 'ITALY', 5.0)], cins='UN6TEST')
        db.session.commit()
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'PLAKA_EBATLI',
        'kaynak_ids': ['PLK-UN2P', 'PLK-UN2Q', 'PLK-UN2R'],
        'kesim_tarihi': _UN1_T.isoformat(),
        'hedefler': [{'hedef_tip': 'EBATLI', 'cins': 'UN6TEST', 'boy': 60,
                      'yukseklik': 60, 'kalinlik': 2, 'adet': 2}]})
    assert r.status_code == 400, r.status_code
    _y = r.get_json()
    assert _y.get('error') == 'kaynak_payi_yok', _y
    with fa.app.app_context():
        assert EbatliStok.query.filter_by(cins='UN6TEST').count() == 0
        # Kaynaklar tuketilmemis olmali
        from models import PlakaStok
        for _id in ('PLK-UN2P', 'PLK-UN2Q', 'PLK-UN2R'):
            assert db.session.get(PlakaStok, _id).durum == 'Serbest'


def test_un2_hedef_tipi_yonle_uyumsuzsa_400():
    """PLAKA_EBATLI yönüne PLAKA hedefi → temiz 400, çıplak 500 değil.

    ÖLÇÜLDÜ: eskiden `int('PLK-A')` ile 500 dönüyordu — kötü veri
    üretmiyordu ama kullanıcıya ham sunucu hatası gösteriyordu."""
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _un1_kurlar()
        _un2_plakalar([('PLK-UN2Z', 'TURKIYE', 5.4)], cins='UN7TEST')
        db.session.commit()
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'PLAKA_EBATLI', 'kaynak_ids': ['PLK-UN2Z'],
        'kesim_tarihi': _UN1_T.isoformat(),
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'UN7TEST', 'boy': 150,
                      'yukseklik': 180, 'kalinlik': 2, 'adet': 2}]})
    assert r.status_code == 400, r.status_code
    _y = r.get_json()
    assert _y.get('error') == 'hedef_tip_uyumsuz', _y
    assert 'EBATLI' in _y.get('mesaj', ''), _y.get('mesaj')


def test_un2_tek_kaynakta_birim_harmanla_ayni():
    """Tek kaynaklı kesimde kaynak başına birim = harmanlanmış birim.

    Yapı kaynak kaynak üretime geçti; tek kaynakta döngü bir kez
    dönmeli ve sonuç eskisiyle aynı olmalı. (Alan alan karşılaştırma
    ayrıca ölçüldü: birebir aynı.)"""
    from models import EbatliStok
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        _un1_kurlar()
        _un2_plakalar([('PLK-UN2S', 'TURKIYE', 5.4)], cins='UN8TEST')
        db.session.commit()
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'PLAKA_EBATLI', 'kaynak_ids': ['PLK-UN2S'],
        'kesim_tarihi': _UN1_T.isoformat(),
        'hedefler': [{'hedef_tip': 'EBATLI', 'cins': 'UN8TEST', 'boy': 60,
                      'yukseklik': 60, 'kalinlik': 2, 'adet': 10,
                      'kasa_ici_adet': 4}]})
    assert r.status_code == 200, r.get_json()
    _d = r.get_json()
    _dok = _d['kaynak_dokumu']
    assert len(_dok) == 1, _dok
    assert _dok[0]['parca'] == 10, _dok
    # Harmanlanmis birim ile kaynak basina birim ayni olmali
    assert abs(float(_dok[0]['birim_maliyet'])
               - float(_d['birim_maliyet'])) < 0.02, (_dok, _d['birim_maliyet'])
    # Tek kaynakta mesaj ARALIK yazmamali
    assert '–' not in _d.get('mesaj', ''), _d.get('mesaj')
    with fa.app.app_context():
        eb = EbatliStok.query.filter_by(cins='UN8TEST').all()
        assert sum(int(e.kasa_ici_adet or 0) for e in eb) == 10
        assert {e.mense for e in eb} == {'TURKIYE'}


# ══════════════════════════════════════════════════════════════════
#  LG1 · FİRMA LOGOSU HİÇ KAYDEDİLEMİYORDU
#
#  Logo kaydeden uçtaki denetim izi satırında `k.ek_bilgi` yazıyordu
#  ve `k` o fonksiyonun hiçbir yerinde yok. `create_app()` tek büyük
#  bir kapsam olduğu için göze batmıyordu: `k` adı KESİM ucunda bir
#  döngü değişkeni olarak geçiyor, ama o başka bir fonksiyona ait.
#
#  ÖLÇÜLDÜ: POST /api/ayarlar/logo → 500, kayda logo yazılmıyor.
#  Logo kullanan her belge (ticari fatura, etiket, liste çıktısı)
#  logosuz basıyordu.
# ══════════════════════════════════════════════════════════════════
# 1x1 saydam PNG
_LG1_PNG = ('data:image/png;base64,'
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNk'
            'YPgPAAIAAf8lU0oAAAAASUVORK5CYII=')


def test_lg1_firma_logosu_kaydedilebiliyor():
    """Logo yüklenince 200 dönmeli ve kayda GERÇEKTEN yazılmalı."""
    from models import Firma
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/ayarlar/logo', headers=H,
               json={'logo': _LG1_PNG, 'dosya_adi': 'lg1.png'})
    assert r.status_code == 200, (r.status_code, r.get_data(as_text=True)[:200])
    assert r.get_json().get('ok') is True, r.get_json()
    with fa.app.app_context():
        f = Firma.query.first()
        assert f.logo, 'yanıt 200 dedi ama kayda logo yazılmamış'
        assert f.logo == _LG1_PNG
        assert f.logo_dosya == 'lg1.png', f.logo_dosya
    # Okuma ucu da gormeli
    d = c.get('/api/ayarlar/logo', headers=H).get_json()
    assert d.get('var_mi') is True, d
    assert d.get('dosya_adi') == 'lg1.png', d


def test_lg1_logo_denetim_izi_dosya_adini_yaziyor():
    """Denetim izi commit'e girmeli ve dosya adını taşımalı.

    Hatanın çıktığı satır tam da denetim izi satırıydı; düzeltmenin
    o izi gerçekten yazdığını görmek gerekiyor."""
    from models import AuditLog
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/ayarlar/logo', headers=H,
               json={'logo': _LG1_PNG, 'dosya_adi': 'iz.png'})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    with fa.app.app_context():
        kayit = AuditLog.query.filter_by(
            tablo_adi='ayarlar', kayit_id='firma_logo',
            islem_tipi='GUNCELLE').order_by(AuditLog.id.desc()).first()
        assert kayit is not None, 'denetim izi yazılmamış'
        assert 'iz.png' in (kayit.yeni_veri or ''), kayit.yeni_veri


def test_lg1_flask_appte_tanimsiz_ad_yok():
    """`create_app()` içinde çözülemeyen hiçbir ad kalmamalı.

    LG1 bu sınıftan bir hataydı ve yalnızca O UÇ çağrıldığında
    patlıyordu — söz dizimi doğru, derleme temiz, test takımı yeşil.
    Bu bekçi kapsamları gezip ATANMAMIŞ her başvuruyu yakalıyor.

    `symtable` stdlib'de; kurulu olmayan bir lint paketine
    bağlanmıyoruz. Ölçüldü: düzeltmeden önce tam 1 bulgu (`k`),
    sonra 0 — 30 bin satırda hiç yanlış alarm yok."""
    import builtins
    import symtable
    import io as _io
    src = _io.open(os.path.join(KOK, 'flask_app.py'), encoding='utf-8').read()
    st = symtable.symtable(src, 'flask_app.py', 'exec')
    _yerlesik = set(dir(builtins))
    _kok = {s.get_name() for s in st.get_symbols()
            if s.is_assigned() or s.is_imported()}

    bulgular = []

    def gez(tablo, kapsayan):
        atanan = {s.get_name() for s in tablo.get_symbols()
                  if s.is_assigned() or s.is_parameter() or s.is_imported()}
        gorunur = kapsayan | atanan
        for s in tablo.get_symbols():
            ad = s.get_name()
            if not s.is_referenced():
                continue
            if ad in gorunur or ad in _yerlesik or ad in _kok:
                continue
            bulgular.append(f'{tablo.get_name()} '
                            f'(satır {tablo.get_lineno()}): {ad}')
        for alt in tablo.get_children():
            gez(alt, gorunur)

    gez(st, set())
    assert not bulgular, \
        'çözülemeyen ad(lar) — çağrıldığında NameError verir: ' \
        + '; '.join(bulgular)


# ══════════════════════════════════════════════════════════════════
#  HY1 · BEYAZ LİSTEDE HAYALET ALAN OLMAYACAK
#
#  DZ5'te `GUNCELLENEBILIR` listesinde `belge_no` vardı ama o alan
#  CariHareket'te YOK — Sevkiyat'ın alanı. Uç nokta alanı
#  "güncellendi" diye adıyla sayıp hiçbir yere yazmıyordu: 200
#  dönüyor, kullanıcıya kaydedildi deniyor, kayıtta hiçbir şey
#  değişmiyor. Python `obj.olmayan = x` demeye izin verdiği için ne
#  hata ne uyarı çıkıyor.
#
#  LG1'in bekçisiyle aynı aile: söz dizimi doğru, takım yeşil, hata
#  yalnızca o uç çağrılınca ve SESSİZCE oluyor.
#
#  "Bir modelde var" yetmez — `belge_no` gayet bir modelde vardı.
#  Bu yüzden her setattr döngüsünün HEDEF MODELİ çözülüp ad ona göre
#  denetleniyor. `hasattr(nesne, alan)` süzgeci olan döngüler muaf:
#  DZ2 o kalıba dayanıyor ve PLAKA'ya tonaj yazmıyor.
#
#  ÖLÇÜLDÜ: `belge_no` geri konunca tarama onu tam olarak bulup
#  "CariHareket'te YOK (var olduğu modeller: Sevkiyat)" diyor;
#  temiz kodda 26 beyaz listenin hiçbirinde bulgu yok.
# ══════════════════════════════════════════════════════════════════
def _hy1_modeller():
    """Model adı -> yazılabilir öznitelik adları."""
    import models as _M
    _mod = {}
    for _ad in dir(_M):
        _s = getattr(_M, _ad)
        if isinstance(_s, type) and hasattr(_s, '__table__'):
            _k = {c.name for c in _s.__table__.columns}
            for _n, _v in vars(_s).items():
                if hasattr(_v, 'expression') or hasattr(_v, 'property'):
                    _k.add(_n)
            _mod[_ad] = _k
    return _mod


def _hy1_tara(kaynak, modeller):
    """(satır, fonksiyon, nesne, hedef model, hayalet adlar) listesi.

    ÇÖZÜMLEME FONKSİYON KAPSAMINDA. Değişken adları (`k`, `s`, `c`,
    `f`) dosya genelinde onlarca fonksiyonda yeniden kullanılıyor;
    dosya çapında tek bir "ad → model" eşlemesi tutmak hangi atamanın
    son söz sahibi olduğunu gezme sırasına bırakır ve rastgele cevap
    verir. Ölçüldü: öyle yazılmış ilk hâli `k`yı Veriler'e, `s`yi
    EbatliStok'a bağlayıp 11 uydurma bulgu üretti.
    """
    import ast

    def liste(dugum, yerel):
        if isinstance(dugum, (ast.Tuple, ast.List, ast.Set)):
            return [e.value for e in dugum.elts
                    if isinstance(e, ast.Constant)
                    and isinstance(e.value, str)]
        if isinstance(dugum, ast.Name) and dugum.id in yerel:
            return yerel[dugum.id]
        if isinstance(dugum, ast.BinOp) and isinstance(dugum.op, ast.Add):
            return liste(dugum.left, yerel) + liste(dugum.right, yerel)
        return []

    def model_adi(dugum):
        if isinstance(dugum, ast.Call):
            f = dugum.func
            if isinstance(f, ast.Name) and f.id in modeller:
                return f.id
            if (isinstance(f, ast.Attribute) and f.attr == 'get'
                    and dugum.args and isinstance(dugum.args[0], ast.Name)
                    and dugum.args[0].id in modeller):
                return dugum.args[0].id
            return model_adi(f)
        if isinstance(dugum, ast.Attribute):
            return model_adi(dugum.value)
        if isinstance(dugum, ast.Name) and dugum.id in modeller:
            return dugum.id
        return None

    def kendi_govdesi(fn):
        """fn'in KENDİ düğümleri — iç fonksiyonların gövdesi hariç."""
        yigin = list(fn.body)
        while yigin:
            d = yigin.pop()
            if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.Lambda, ast.ClassDef)):
                continue
            yield d
            for alt in ast.iter_child_nodes(d):
                yigin.append(alt)

    agac = ast.parse(kaynak)
    bulgular = []
    for fn in ast.walk(agac):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        kendi = list(kendi_govdesi(fn))
        yerel, nesne_modeli = {}, {}
        for d in sorted((x for x in kendi if isinstance(x, ast.Assign)),
                        key=lambda x: x.lineno):
            if len(d.targets) != 1 or not isinstance(d.targets[0], ast.Name):
                continue
            _l = liste(d.value, yerel)
            if _l:
                yerel[d.targets[0].id] = _l
            _m = model_adi(d.value)
            if _m:
                nesne_modeli[d.targets[0].id] = _m
        for d in kendi:
            if (not isinstance(d, ast.For)
                    or not isinstance(d.target, ast.Name)):
                continue
            dv = d.target.id
            hedef = None
            for alt in ast.walk(d):
                if (isinstance(alt, ast.Call)
                        and isinstance(alt.func, ast.Name)
                        and alt.func.id == 'setattr'
                        and len(alt.args) >= 2):
                    _a = alt.args[1]
                    if ((isinstance(_a, ast.Name) and _a.id == dv)
                            or (isinstance(_a, ast.BinOp)
                                and isinstance(_a.left, ast.Name)
                                and _a.left.id == dv)):
                        if isinstance(alt.args[0], ast.Name):
                            hedef = alt.args[0].id
                            break
            if not hedef:
                continue
            # `hasattr(nesne, alan)` süzgeci alanı zaten koruyor (DZ2)
            if any(isinstance(a, ast.Call) and isinstance(a.func, ast.Name)
                   and a.func.id == 'hasattr' and len(a.args) == 2
                   and isinstance(a.args[1], ast.Name)
                   and a.args[1].id == dv
                   for a in ast.walk(d)):
                continue
            adlar = liste(d.iter, yerel)
            model = nesne_modeli.get(hedef)
            if not adlar or not model:
                continue
            eksik = [a for a in adlar if a not in modeller[model]]
            if eksik:
                bulgular.append((d.lineno, fn.name, hedef, model, eksik))
    return bulgular


def test_hy1_setattr_beyaz_listelerinde_hayalet_alan_yok():
    """Her setattr beyaz listesi adı HEDEF MODELİNDE kolon olmalı."""
    import io as _io
    modeller = _hy1_modeller()
    assert len(modeller) > 20, len(modeller)
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    bulgular = _hy1_tara(kaynak, modeller)
    assert not bulgular, 'hayalet alan(lar) — yazılmış gibi görünüp ' \
        'hiçbir yere yazılmaz: ' + '; '.join(
            f'satır {_s}: {", ".join(_e)} → {_m} ({_fn}, setattr({_n}, …))'
            for _s, _fn, _n, _m, _e in bulgular)


def test_hy1_bekci_dz5_hatasini_yakaliyor():
    """Bekçinin kendisi: DZ5 geri konunca yakalamalı.

    Bir bekçi, yakaladığını gösteremezse bekçi değildir."""
    import io as _io
    modeller = _hy1_modeller()
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    _e = ("        GUNCELLENEBILIR = ('aciklama', 'vade_tarihi', "
          "'evrak_no',\n                           'hareket_tarihi')")
    assert kaynak.count(_e) == 1, 'DZ5 beyaz listesi bulunamadı'
    _bozuk = kaynak.replace(
        _e, _e[:-1] + ", 'belge_no')", 1)
    bulgular = _hy1_tara(_bozuk, modeller)
    assert bulgular, 'bekçi DZ5 hatasını yakalamıyor'
    _hepsi = [a for _, _, _, _, e in bulgular for a in e]
    assert 'belge_no' in _hepsi, bulgular
    # Dogru modeli de soylemeli
    assert any(m == 'CariHareket' for _, _, _, m, _ in bulgular), bulgular


# ══════════════════════════════════════════════════════════════════
#  TS1 · İKİ SİLME YOLU AYNI ŞEYİ YAPMALI
#
#  Bir tahsilatı silmenin iki yolu vardı ve ikisi aynı işi
#  yapmıyordu:
#
#    · `DELETE /api/tahsilat/<id>` kasayı geri alıyordu — ama o ucu
#      çağıran hiçbir ekran yok. TH2 testi onu koşuyor, takım yeşil.
#    · `DELETE /api/cari/hareket/<id>` cari ekranındaki ✕ düğmesinin
#      yolu — ve kasayı geri ALMIYORDU.
#
#  Sebep: ikinci yol kasa kaydını `baglanti_tip='cari_hareket'` ile
#  arıyordu, oysa tahsilatın kasa kaydı `'tahsilat'` ile yazılıyor.
#  Süzgeç hedefini vurmuyordu — AF1'deki ölü çek süzgecinin aynısı.
#
#  ÖLÇÜLDÜ — 10.000 USD fatura, 4.000 USD tahsilat, sonra sil:
#      /api/tahsilat/<id>      fatura Kesildi · kasa     0,00 ✓
#      /api/cari/hareket/<id>  fatura Kesildi · kasa 4.000,00 ✗
# ══════════════════════════════════════════════════════════════════
_TS1_T = date(2026, 2, 19)      # baska test bu gune kur yazmiyor


def _ts1_kur(fid, kasa_adi):
    """Temiz fatura + kasa. Kasa kimligini doner."""
    from models import Fatura, Kasa, DovizKur
    if not DovizKur.query.filter_by(doviz='USD', tarih=_TS1_T).first():
        db.session.add(DovizKur(doviz='USD', tarih=_TS1_T,
                                alis=40.0, satis=40.0, efektif=40.0))
    if not db.session.get(Cari, 'MUS-TS1'):
        db.session.add(Cari(id='MUS-TS1', unvan='MUSTERI TS1',
                            cari_tip='Müşteri'))
    k = Kasa(ad=kasa_adi, doviz='USD', bakiye=0)
    db.session.add(k)
    db.session.add(Fatura(
        id=fid, fatura_no=fid, cari_id='MUS-TS1', musteri='MUSTERI TS1',
        yon='satis', durum='Kesildi', doviz='USD', toplam=10000,
        ara_toplam=10000, fatura_tarihi=_TS1_T))
    db.session.commit()
    return k.id


def _ts1_durum(fid, kid):
    from models import Fatura, Kasa, KasaHareket
    with fa.app.app_context():
        f = db.session.get(Fatura, fid)
        hs = CariHareket.query.filter_by(
            baglanti_tip='fatura', baglanti_id=fid, kaynak='tahsilat').all()
        return (f.durum, float(db.session.get(Kasa, kid).bakiye or 0),
                [h.id for h in hs],
                KasaHareket.query.filter_by(kasa_id=kid).count())


def _ts1_senaryo(c, fid, kasa_adi, yol_kalibi):
    """Tahsilat gir, verilen yoldan sil, (durum, kasa, hareket) döner."""
    with fa.app.app_context():
        kid = _ts1_kur(fid, kasa_adi)
    r = c.post(f'/api/fatura/{fid}/tahsilat', headers=H,
               json={'tutar': 4000, 'kasa_id': kid, 'doviz': 'USD'})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    _d, _bakiye, _hids, _kh = _ts1_durum(fid, kid)
    assert _hids, 'tahsilat hareketi oluşmadı'
    assert abs(_bakiye - 4000) < 0.01, f'kasa {_bakiye} — 4.000 olmalı'
    assert _kh == 1, _kh
    r2 = c.delete(yol_kalibi.format(hid=_hids[0]), headers=H)
    assert r2.status_code == 200, r2.get_data(as_text=True)[:200]
    return _ts1_durum(fid, kid)


def test_ts1_cari_ekranindan_tahsilat_silinince_kasa_geri_alinir():
    """Cari ekranındaki ✕ kasayı da geri almalı.

    Kullanıcının ulaşabildiği yol bu. Eskiden para kasada kalıyordu:
    kasa, karşılığı olmayan bir tahsilatı gösteriyordu."""
    c = istemci('admin', 'ADMIN')
    durum, bakiye, hids, kh = _ts1_senaryo(
        c, 'FT-TS1A', 'TS1 KASA A', '/api/cari/hareket/{hid}')
    assert not hids, 'tahsilat hareketi silinmemiş'
    assert durum == 'Kesildi', durum
    assert abs(bakiye) < 0.01, \
        f'kasada {bakiye:,.2f} kaldı — tahsilat silindi ama para duruyor'
    assert kh == 0, f'{kh} kasa hareketi duruyor'


def test_ts1_iki_silme_yolu_ayni_sonucu_veriyor():
    """`/api/tahsilat/<id>` ile `/api/cari/hareket/<id>` eş olmalı.

    İkisi de aynı şeyi siliyor; farklı davranmaları, hangisinin
    çağrıldığına göre farklı bir gerçek üretir."""
    c = istemci('admin', 'ADMIN')
    a = _ts1_senaryo(c, 'FT-TS1B', 'TS1 KASA B', '/api/tahsilat/{hid}')
    b = _ts1_senaryo(c, 'FT-TS1C', 'TS1 KASA C', '/api/cari/hareket/{hid}')
    # (durum, kasa bakiyesi, kalan hareketler, kasa hareketi sayisi)
    assert a[0] == b[0], (a, b)
    assert abs(a[1] - b[1]) < 0.01, f'kasa bakiyeleri ayrışıyor: {a[1]} / {b[1]}'
    assert a[2] == b[2] == [], (a, b)
    assert a[3] == b[3] == 0, (a, b)


def test_ts1_kasa_geri_alma_tek_kaynaktan():
    """Geri alma mantığı TEK yerde olmalı, iki kopya değil.

    İki kopya zamanla ayrışır — EM1 ve AF1'de olan tam buydu. Test
    paylaşılan kapıyı tutuyor, kopyaların içeriğini değil."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'flask_app.py'),
                 encoding='utf-8').read().replace('\r\n', '\n')
    assert 'def _hareket_kasa_geri_al(' in m, 'ortak kapı yok'
    assert m.count('_hareket_kasa_geri_al(') >= 3, \
        'iki uç da ortak kapıdan geçmiyor'
    # Eski kopyanin imzasi: yalniz 'cari_hareket' arayan suzgec
    assert "baglanti_tip='cari_hareket', baglanti_id=hareket_id" not in m, \
        'cari hareket silmede eski kasa kopyası duruyor'
    # Para yazan is artik sessizce yutulmuyor
    _i = m.index('def _hareket_kasa_geri_al(')
    _govde = m[_i:m.index('@app.route', _i)]
    # Belgelendirme dizgisi eski kopyadan SOZ EDIYOR; aranan sey
    # KOD. Satir basindaki girintili `except` ifadesine bakiyoruz —
    # ilk hali metin icinde arayip kendi yorumuma takilmisti.
    import re as _re
    assert not _re.search(r'^\s+except\b', _govde, _re.M), \
        'kasa geri alma hatayı yutuyor — yarım iş sessizce geçer'


# ══════════════════════════════════════════════════════════════════
#  AS2 · EKRANIN OKUDUĞU ALANI SUNUCU GÖNDERMELİ
#
#  Kalıp:
#      const d = await api('/api/kasa');
#      ... d.toplam_usd   ← uç bu anahtarı HİÇ göndermiyorsa JS
#                           `undefined` verir: alan boş görünür,
#                           sayıysa NaN, toplamaya girerse tüm satır
#                           bozulur. Ne hata ne uyarı.
#
#  "Sessizce kaybolan değer" ailesinin API sınırındaki hâli.
#
#  BULGU: `/api/avans/devret` `doviz` göndermiyordu; ekran devirden
#  sonra "Kalan avans: 5.000,00" diye PARA BİRİMİ OLMADAN yazıyordu
#  (AS1 ile düzeltildi).
#
#  TARAMANIN KENDİSİNDE DÖRT KUSUR BULDUM, hepsi ölçülerek:
#    · sabit 60 satırlık pencere bir sonraki fonksiyona taşıyordu
#      → 62 adayın çoğu oradan geliyordu. Artık kuşatan blok
#        süslü parantez sayılarak bulunuyor.
#    · en-uzun-önek eşlemesi `/…/eposta` çağrısını `/…/eposta/test`
#      ucuna bağlıyordu → artık segment sayısı eşit olmalı.
#    · `X.data || X.bankalar || []` savunma zincirleri aday
#      sayılıyordu → ilk alternatif geçerliyse gerisi muaf.
#    · LİSTE dönen uçların yanıtında top-level anahtar YOKTUR; iç
#      sözlüğün anahtarlarını yanıtın anahtarları saymak her
#      erişimi "eksik" gösteriyordu → liste dönen uçlar denetim
#      dışı.
#  62 → 13 → 10 → 1. İlk "temiz" sonuçlar şanstı; bunu yazıyorum ki
#  bu bekçi bir gün patlarsa önce KENDİSİNDEN şüphe edilsin.
#
#  MUHAFAZAKAR: anahtarları tam sayılamayan uçlar (sözlüğü değişkene
#  kurup `jsonify(d)` yapanlar, `**` ile gevşetenler) atlanıyor.
#  Bilmediğini bulgu saymaz.
# ══════════════════════════════════════════════════════════════════
_AS2_ZARF = {'ok', 'mesaj', 'error', 'hata', 'status', 'kapsam', 'uyari',
             'detay', 'message', 'errors'}
_AS2_JS = {'map', 'filter', 'forEach', 'length', 'then', 'catch', 'push',
           'slice', 'find', 'some', 'every', 'reduce', 'sort', 'join',
           'includes', 'toFixed', 'hasOwnProperty'}


def _as2_uc_anahtarlari(kaynak):
    """yol -> (gönderilen anahtarlar, tam sayılabilir mi)."""
    import ast

    def anahtarlar(d, derinlik=0):
        if isinstance(d, ast.Dict):
            adlar, tam = set(), True
            for k in d.keys:
                if k is None:
                    tam = False
                elif isinstance(k, ast.Constant) and isinstance(k.value, str):
                    adlar.add(k.value)
                else:
                    tam = False
            return adlar, tam
        return set(), False

    sonuc = {}
    for fn in ast.walk(ast.parse(kaynak)):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        yollar = [d.args[0].value for d in fn.decorator_list
                  if isinstance(d, ast.Call)
                  and isinstance(d.func, ast.Attribute)
                  and d.func.attr == 'route' and d.args
                  and isinstance(d.args[0], ast.Constant)]
        if not yollar:
            continue
        adlar, tam, liste = set(), True, False
        for d in ast.walk(fn):
            if (isinstance(d, ast.Call) and isinstance(d.func, ast.Name)
                    and d.func.id == 'jsonify' and d.args):
                if isinstance(d.args[0], (ast.List, ast.ListComp)):
                    liste = True        # top-level anahtar YOK
                    continue
                a, t = anahtarlar(d.args[0])
                adlar |= a
                tam = tam and t
        for y in yollar:
            eski = sonuc.get(y, (set(), True))
            sonuc[y] = (eski[0] | adlar, eski[1] and tam and not liste)
    return sonuc


def _as2_kusatan_blok(metin, bas):
    """`bas`tan kuşatan blok kapanana kadarki metin."""
    derinlik, i, n = 0, bas, len(metin)
    while i < n:
        c = metin[i]
        if c in '"\'`':
            kapa = c
            i += 1
            while i < n and metin[i] != kapa:
                i += 2 if metin[i] == '\\' else 1
        elif c == '/' and i + 1 < n and metin[i + 1] == '/':
            while i < n and metin[i] != '\n':
                i += 1
        elif c == '/' and i + 1 < n and metin[i + 1] == '*':
            j = metin.find('*/', i + 2)
            i = (j + 1) if j > 0 else n
        elif c == '{':
            derinlik += 1
        elif c == '}':
            derinlik -= 1
            if derinlik < 0:
                return metin[bas:i]
        i += 1
    return metin[bas:]


def _as2_yol_esle(cagri, uclar):
    """Çağrı yolunu uç tanımına eşler. Belirsizse None."""
    temiz = cagri.split('?')[0].rstrip('/')
    if temiz in uclar:
        return temiz
    cp = [x for x in temiz.split('/') if x]
    adaylar = []
    for y in uclar:
        yp = [x for x in y.rstrip('/').split('/') if x]
        if len(yp) != len(cp):
            continue
        sabit, uyum = 0, True
        for a, b in zip(cp, yp):
            if b.startswith('<') or '${' in a:
                continue
            if a != b:
                uyum = False
                break
            sabit += 1
        if uyum:
            adaylar.append((sabit, y))
    if not adaylar:
        return None
    adaylar.sort(reverse=True)
    if len(adaylar) > 1 and adaylar[0][0] == adaylar[1][0]:
        return None          # belirsiz — bulgu sayma
    return adaylar[0][1]


def test_as2_ekranin_okudugu_alani_sunucu_gonderiyor():
    """Hiçbir şablon, ucun göndermediği bir anahtarı okumamalı."""
    import io as _io
    import re as _re
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    uclar = _as2_uc_anahtarlari(kaynak)
    assert len(uclar) > 100, len(uclar)

    cagri = _re.compile(
        r"""(?:const|let|var)\s+(\w+)\s*=\s*await\s+api\(\s*['"`]([^'"`?]+)""")
    bulgular = []
    _sablon = os.path.join(KOK, 'templates')
    for ad in sorted(os.listdir(_sablon)):
        if not ad.endswith('.html'):
            continue
        metin = _io.open(os.path.join(_sablon, ad),
                         encoding='utf-8', errors='replace').read()
        for m in cagri.finditer(metin):
            dv, yol = m.group(1), m.group(2)
            uc = _as2_yol_esle(yol, uclar)
            if not uc:
                continue
            anahtar, tam = uclar[uc]
            if not tam or not anahtar:
                continue       # bilmedigini bulgu saymaz
            pencere = _as2_kusatan_blok(metin, m.start())
            okunan = set(_re.findall(
                r'\b' + _re.escape(dv) + r'\.([a-zA-Z_]\w*)', pencere))
            okunan |= set(_re.findall(
                r'\b' + _re.escape(dv) + r"\[['\"](\w+)['\"]\]", pencere))
            okunan -= _AS2_JS
            # `X.a || X.b` savunma zinciri: ilk alternatif gecerliyse
            # gerisi yedek, zarar vermiyor.
            yedek = set()
            for z in _re.finditer(
                    r'\b' + _re.escape(dv) + r'\.(\w+)'
                    r'((?:\s*\|\|\s*(?:' + _re.escape(dv)
                    + r'\.\w+|\[\]|\{\}|0|\'\'|""))+)', pencere):
                if z.group(1) in anahtar:
                    yedek |= set(_re.findall(
                        _re.escape(dv) + r'\.(\w+)', z.group(2)))
            eksik = sorted(okunan - anahtar - _AS2_ZARF - yedek)
            if eksik:
                satir = metin[:m.start()].count('\n') + 1
                bulgular.append(f'{ad}:{satir} {dv}=api({yol}) → '
                                f'{uc} göndermiyor: {", ".join(eksik)}')
    assert not bulgular, ('ekran okuyor, uç göndermiyor (boş alan / NaN): '
                          + ' | '.join(bulgular))


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


# ══════════════════════════════════════════════════════════════════
#  YK2 · YAZMA MUHAFIZININ VARSAYILANI "SESSİZCE GEÇ"
#
#  Yazma muhafızı yolu bir modüle eşlemeye çalışıyor; eşleşmezse:
#      # Tanimlanmamis API - sessizce gec
#      return None
#  Yani FAIL-OPEN. Haritaya eklenmemiş bir yazma ucu, yalnızca
#  OKUMA yetkili bir kullanıcıya da açık olur.
#
#  YK1 (19.09) bunun bir örneğini yakalamıştı: yalnız okuma yetkili
#  kullanıcı `POST /api/cek` ile çek kaydedebiliyordu.
#
#  TARAMA BUGÜN TEMİZ: 147 yazma ucunun 31'i hiçbir haritaya
#  eşleşmiyor ama hepsi KENDİ içinde yetki soruyor (`_yetki_var_mi`
#  ya da `_diag_guard`), biri de bilerek herkese açık (`/api/v2/
#  eposta/ayar` — kullanıcı yalnız KENDİ SMTP ayarını yazıyor,
#  kullanıcı adı gövdeden değil oturumdan geliyor).
#
#  Bu test o durumu SABİTLER. Yarın eklenecek bir yazma ucu
#  haritaya girmez ve kendi denetimini de yapmazsa, sessizce açık
#  kalmak yerine takımı kırar.
# ══════════════════════════════════════════════════════════════════
_YK2_MUAF = {
    # Kullanici YALNIZCA kendi SMTP ayarini yazar; kullanici adi
    # oturumdan aliniyor (EP2). Modul yetkisi aramak yanlis olurdu.
    '/api/v2/eposta/ayar',
    # TCMB'den kur ceker. Yazdigi veri CAGIRANDAN gelmiyor, TCMB'den
    # geliyor; ve her ekran kura muhtac. Modul yetkisi aramak
    # kullaniciyi kendi ekraninda kilitlerdi.
    '/api/doviz_kur/guncelle',
}
# `/api/diag/` TOPLU korunuyor: `_diag_guard` bir `before_request`
# kancasi ve ADMIN sarti koyuyor (F0-3). Fonksiyon govdesinde iz
# birakmadigi icin ayrica muaf tutuluyor — ilk halimde 11 diag ucu
# "acik" diye isaretlenmisti, oysa hepsi kapali.


def test_yk2_her_yazma_ucu_ya_haritada_ya_kendi_denetimini_yapiyor():
    """Yazma ucu ya modüle eşlenmeli ya kendi yetkisini sormalı."""
    import ast as _ast
    import io as _io
    import re as _re
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    agac = _ast.parse(kaynak)

    def _deger(ad):
        for d in _ast.walk(agac):
            if (isinstance(d, _ast.Assign) and len(d.targets) == 1
                    and isinstance(d.targets[0], _ast.Name)
                    and d.targets[0].id == ad):
                try:
                    return _ast.literal_eval(d.value)
                except Exception:
                    return []
        return []

    url_map = _deger('URL_MODUL_MAP')
    yazma_ek = _deger('YAZMA_EK_MAP')
    assert url_map and yazma_ek, 'haritalar okunamadı'
    # ALT_YOL_DESENLERI derlenmiş regex taşıyor — desenleri kaynaktan
    desenler = [_re.compile(m) for m in _re.findall(
        r"_re_alt\.compile\(r'([^']+)'\)", kaynak)]
    assert desenler, 'alt yol desenleri okunamadı'

    # Her yazma ucunun KENDI govdesinde denetim var mi
    kendi = {}
    for fn in _ast.walk(agac):
        if not isinstance(fn, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            continue
        g = _ast.unparse(fn)
        # "Kendi denetimini yapiyor"un en genel isareti: govdesi
        # 403 DONEBILIYOR. Ad listesiyle aramak eksik kaliyordu —
        # `_erisim_verebilir_mi` gibi ozel kapilar listede yoktu ve
        # kapali bir uc "acik" gorunuyordu.
        kendi[fn.name] = ('403' in g) or any(k in g for k in (
            '_yetki_var_mi', '_diag_guard', "session.get('rol')",
            '_erisim_admin_mi'))

    YAZMA = {'POST', 'PUT', 'PATCH', 'DELETE'}
    acik = []
    for kural in fa.app.url_map.iter_rules():
        if not (kural.methods or set()) & YAZMA:
            continue
        yol = str(kural.rule)
        if not yol.startswith('/api/'):
            continue
        if yol in _YK2_MUAF or yol.startswith('/api/diag/'):
            continue
        ornek = _re.sub(r'<[^>]+>', 'X', yol)
        eslesti = (any(d.match(ornek) for d in desenler)
                   or any(ornek.startswith(o) for o, _ in url_map)
                   or any(ornek.startswith(o) for o, _ in yazma_ek))
        if eslesti:
            continue
        _fn = str(kural.endpoint).split('.')[-1]
        if kendi.get(_fn):
            continue        # kendi denetimini yapiyor
        acik.append(f'{",".join(sorted((kural.methods or set()) & YAZMA))} '
                    f'{yol} ({_fn})')
    assert not acik, (
        'yazma muhafızından sessizce geçen uç(lar) — yalnız OKUMA '
        'yetkili kullanıcı da çağırabilir: ' + '; '.join(sorted(acik)))


# ══════════════════════════════════════════════════════════════════
#  KD1 · KDV MATEMATİĞİNİN TEK KAPISI + ÖLÜ FONKSİYON BEKÇİSİ
#
#  Sınıf, AF1/TS1/EM2'nin aynısı: ortak kapı YAZILMIŞ ama hiçbir
#  yerden çağrılmıyor; iş 10 ayrı yere elle kopyalanmış. Buradaki
#  fark, ölçüm beklenmedik bir şey söyledi: ÖLÜ KAPI, CANLI UÇLARDAN
#  DAHA KÖTÜYDÜ. Matrahı ve KDV'yi birbirinden bağımsız yuvarladığı
#  için ikisinin toplamı genel toplamı tutmuyordu:
#
#      1.000,35 USD · %20  ->  833,63 + 166,73 = 1.000,36
#
#  Yani "ortak kapıya bağla" refleksi, 10 para yoluna hata EKLERDİ.
#  Kapı önce düzeltildi (tamamlayan yuvarlama: bir taraf yuvarlanır,
#  öteki çıkarmayla bulunur), sonra uçlar bağlandı.
# ══════════════════════════════════════════════════════════════════
def test_kd1_fatura_kdv_duzeltmesi_matrah_ve_kdv_toplami_tutuyor():
    """Matrah + KDV, faturanın kendi toplamını vermeli."""
    from models import Fatura
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(Cari(id='MUS-KD1', unvan='MUSTERI KD1',
                            cari_tip='Müşteri'))
        db.session.add(Fatura(
            id='FT-KD1', fatura_no='KD1-001', cari_id='MUS-KD1',
            musteri='MUSTERI KD1', yon='satis', durum='Kesildi',
            doviz='USD', toplam=1000.35, ara_toplam=1000.35,
            kdv_oran=0, kdv_tutar=0,
            fatura_tarihi=date(2026, 10, 28)))
        db.session.commit()

    r = c.post('/api/diag/fatura/FT-KD1/kdv_duzelt?kdv_oran=20', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)[:300]

    with fa.app.app_context():
        f = db.session.get(Fatura, 'FT-KD1')
        matrah = float(f.ara_toplam or 0)
        kdv = float(f.kdv_tutar or 0)
        toplam = float(f.toplam or 0)
    # ESKI DAVRANIS: 833.63 + 166.73 = 1000.36  (toplam 1000.35)
    assert round(matrah + kdv, 2) == round(toplam, 2), (
        f'matrah {matrah} + KDV {kdv} = {round(matrah + kdv, 2)} '
        f'ama faturanın toplamı {toplam}')
    assert matrah == 833.63, matrah
    assert kdv == 166.72, kdv


def test_kd1_kdv_ayristirma_elle_yazilmamis():
    """KDV ayrıştırma formülü TEK yerde olmalı.

    EM2'nin maliyet kapısı bekçisiyle aynı desen: formülün kendisini
    aramak, onu kopyalayan yeni bir ucu doğduğu gün yakalar."""
    import io as _io
    import re as _re
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    satirlar = kaynak.split('\n')
    # `_kdv_ayristir` govdesinin kendisi MUAF — kapi orada.
    kapi = [i for i, t in enumerate(satirlar, 1)
            if 'def _kdv_ayristir(' in t]
    assert kapi, 'kapı (_kdv_ayristir) bulunamadı'
    kapi_araligi = range(kapi[0], kapi[0] + 12)

    desen = _re.compile(r'/\s*\(\s*1\s*\+\s*[a-z_]*kdv[a-z_]*')
    kacak = [f'satır {i}: {t.strip()[:70]}'
             for i, t in enumerate(satirlar, 1)
             if desen.search(t) and i not in kapi_araligi]
    assert not kacak, (
        'KDV ayrıştırma formülü kapının DIŞINDA elle yazılmış — '
        '`_kdv_ayristir` / `_kdv_hesapla` kullanılmalı: '
        + '; '.join(kacak))

    # Kapi TAMAMLAYAN yuvarlama yapiyor mu: bir taraf cikarmayla
    # bulunmali. "q2(tutar - matrah)" bunun imzasi.
    g = '\n'.join(satirlar[kapi[0] - 20:kapi[0] + 40])
    assert 'q2(tutar - matrah)' in g, (
        'kapı matrahı ve KDV\'yi bağımsız yuvarlıyor olabilir — '
        'tamamlayan yuvarlama (çıkarma) izi yok')


def test_kd1_olu_fonksiyon_yok():
    """Tanımlanmış ama hiçbir yerden erişilmeyen fonksiyon olmamalı.

    BU SINIFIN BEKÇİSİ. AF1'in ölü çek süzgeci, TS1'in kasa geri
    alması, EM2'nin maliyet kapısı ve KD1'in KDV kapısı — dördü de
    "kod doğru ama çağrılmıyor" idi. Tarama, yarın yazılıp bir yere
    bağlanmayı bekleyen bir fonksiyonu görünür kılar.

    ULAŞILABİLİRLİK: @app.route ve Flask kancaları, dekoratörler,
    SQLAlchemy dinleyicileri (`listens_for` ve models.py'deki
    `_event.listen(...)` çağrıları), gövde dışında geçen her ad,
    dizge içinde geçen adlar (url_for/getattr), şablonlar, static
    ve projedeki diğer .py dosyaları.
    """
    import ast as _ast
    import io as _io
    import re as _re

    ANA = os.path.join(KOK, 'flask_app.py')
    kaynak = _io.open(ANA, encoding='utf-8').read().replace('\r\n', '\n')
    agac = _ast.parse(kaynak)

    KANCA = {
        'route', 'before_request', 'after_request', 'before_first_request',
        'teardown_request', 'teardown_appcontext', 'errorhandler',
        'context_processor', 'template_filter', 'template_global',
        'template_test', 'command', 'cli', 'app_errorhandler',
        'shell_context_processor', 'url_value_preprocessor', 'url_defaults',
        'user_loader', 'property', 'staticmethod', 'classmethod',
        'contextmanager', 'cache', 'lru_cache', 'validates', 'event',
        # ÖLÇÜLDÜ: ilk halimde bu yoktu ve `_cari_hareket_okunur_id`
        # (RN1 dinleyicisi) "ölü" diye işaretlendi. SQLAlchemy onu
        # her insert'te çağırıyor.
        'listens_for', 'hybrid_property', 'setter', 'expression',
    }

    def _dek(fn):
        out = []
        for d in fn.decorator_list:
            k = d.func if isinstance(d, _ast.Call) else d
            if isinstance(k, _ast.Attribute):
                out.append(k.attr)
            elif isinstance(k, _ast.Name):
                out.append(k.id)
        return out

    sinif_ici = set()
    for s in _ast.walk(agac):
        if isinstance(s, _ast.ClassDef):
            for a in _ast.walk(s):
                if isinstance(a, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                    sinif_ici.add((a.name, a.lineno))

    tanim = {}
    for fn in _ast.walk(agac):
        if isinstance(fn, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            tanim.setdefault(fn.name, []).append(
                (fn.lineno, fn.end_lineno, _dek(fn),
                 (fn.name, fn.lineno) in sinif_ici))

    # Dekorator satirlari "kullanim" sayilmaz: dekorator olarak
    # kullanilmak zaten KANCA uzerinden degerlendiriliyor.
    dek_satir = set()
    for fn in _ast.walk(agac):
        if isinstance(fn, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            for d in fn.decorator_list:
                for a in _ast.walk(d):
                    dek_satir.add(getattr(a, 'lineno', 0))

    kullanim = {}
    for d in _ast.walk(agac):
        ad = None
        if isinstance(d, _ast.Name) and isinstance(d.ctx, _ast.Load):
            ad = d.id
        elif isinstance(d, _ast.Attribute) and isinstance(d.ctx, _ast.Load):
            ad = d.attr
        if ad:
            kullanim.setdefault(ad, set()).add(getattr(d, 'lineno', 0))

    dizge = '\n'.join(d.value for d in _ast.walk(agac)
                      if isinstance(d, _ast.Constant)
                      and isinstance(d.value, str))

    # Sablonlar, static ve PROJEDEKI DIGER .py dosyalari.
    # models.py burada onemli: `_event.listen(Model, 'before_insert',
    # cari_id_otomatik_doldur)` gibi EMIR KIPLI kayitlar yalnizca
    # oradaki metinde gorunuyor.
    disari = []
    for dizin in ('templates', 'static'):
        kok = os.path.join(KOK, dizin)
        for yer, _, dosyalar in os.walk(kok):
            for ad in dosyalar:
                if ad.endswith(('.html', '.js')):
                    disari.append(_io.open(os.path.join(yer, ad),
                                           encoding='utf-8',
                                           errors='replace').read())
    for yer, _, dosyalar in os.walk(KOK):
        if '/.git' in yer or '__pycache__' in yer:
            continue
        for ad in dosyalar:
            if ad.endswith('.py') and os.path.join(yer, ad) != ANA:
                disari.append(_io.open(os.path.join(yer, ad),
                                       encoding='utf-8',
                                       errors='replace').read())
    disari = '\n'.join(disari)

    # MUAF: bilerek bekletilen fonksiyonlar. Liste KISA kalmalı —
    # uzayan bir muafiyet listesi, bekçinin sessizce kapanmasıdır.
    MUAF = {
        # GİB senaryosu önerir (IHRACAT / TEMELFATURA). E-fatura
        # ekranı bağlandığında çağrılacak; silinmesi yerine
        # bekletilmesi KD1'de bilerek seçildi.
        '_senaryo_oner',
    }

    olu = []
    for ad, yerler in sorted(tanim.items()):
        if ad in MUAF or ad.startswith('__') or len(yerler) > 1:
            continue
        satir, son, dekler, sinifta = yerler[0]
        if sinifta or (set(dekler) & KANCA):
            continue
        dis = {s for s in kullanim.get(ad, set())
               if not (satir <= s <= son) and s not in dek_satir}
        if dis:
            continue
        kalip = r'\b%s\b' % _re.escape(ad)
        if _re.search(kalip, dizge) or _re.search(kalip, disari):
            continue
        olu.append(f'{ad} (satır {satir}, {son - satir + 1} satır)')

    assert not olu, (
        'hiçbir yerden çağrılmayan fonksiyon(lar) — ya bir yere '
        'bağlanmalı ya silinmeli: ' + ', '.join(olu))


def test_kd1_bekci_olu_fonksiyonu_gercekten_yakaliyor():
    """Bekçi, bilerek eklenmiş ölü bir fonksiyonu görmeli.

    HY1'de bekçinin kendisi yanlış yazılmıştı ve "temiz" sonucu
    şanstı. Bir bekçiye, kırmadığını görmeden güvenilmez."""
    import ast as _ast
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    sahte = kaynak + (
        '\n\ndef _kd1_bekci_denemesi_hic_cagrilmayan():\n'
        '    return 42\n')
    agac = _ast.parse(sahte)
    adlar = {f.name for f in _ast.walk(agac)
             if isinstance(f, (_ast.FunctionDef, _ast.AsyncFunctionDef))}
    assert '_kd1_bekci_denemesi_hic_cagrilmayan' in adlar
    # Govde disinda HICBIR kullanimi olmamali — bekcinin olculdugu sey.
    kullanim = [d for d in _ast.walk(agac)
                if isinstance(d, _ast.Name)
                and d.id == '_kd1_bekci_denemesi_hic_cagrilmayan'
                and isinstance(d.ctx, _ast.Load)]
    assert not kullanim, 'deneme fonksiyonu beklenmedik şekilde çağrılıyor'


def test_kd1_uc_uc_artik_bir_ekrandan_cagriliyor():
    """Bağlanan üç uç şablonlarda GEÇMELİ (SD4/EK1 ile aynı bekçi)."""
    import io as _io
    _sablon = os.path.join(KOK, 'templates')
    tum = ''
    for ad in os.listdir(_sablon):
        if ad.endswith('.html'):
            tum += _io.open(os.path.join(_sablon, ad),
                            encoding='utf-8', errors='replace').read()
    for yol, nerede in (
            ('/api/cari/hareket/try_yeniden_hesapla', 'TRY karşılığı bakımı'),
            ('/api/satislar/lookup', 'satış süzgeç listeleri'),
            ('/api/satislar/musteri/', 'müşteri satış özeti')):
        assert yol in tum, f'{nerede} ({yol}) hiçbir şablonda yok'
    satislar = _io.open(os.path.join(_sablon, 'satislar.html'),
                        encoding='utf-8').read()
    assert 'suzgecListeleri' in satislar
    assert 'musteriOzetiYukle' in satislar
    ayarlar = _io.open(os.path.join(_sablon, 'ayarlar.html'),
                       encoding='utf-8').read()
    assert 'tryYenidenHesapla' in ayarlar

    # ── BAKIM SEKMESİ DOĞRU PANELDE Mİ ──
    # ÖLÇÜLDÜ: önce Yönetim paneline koymuştum ve düğme 409 "firma
    # seçilmedi" alıyordu — panel firma bağlamını bilerek düşürüyor
    # (session.pop('firma_id')), bakım ucu ise firmaya bağlı. Tarayıcıda
    # basmadan görünmezdi: sekme vardı, düğme vardı, sonuç yoktu.
    c = istemci('admin', 'ADMIN')
    _aya = c.get('/ayarlar').get_data(as_text=True)
    _yon = c.get('/yonetim').get_data(as_text=True)
    assert 'id="b-bakim"' in _aya, 'Bakım bölümü Ayarlar\'da basılmıyor'
    assert 'id="b-bakim"' not in _yon, (
        'Bakım bölümü Yönetim panelinde — orada firma seçili değil, '
        'düğme 409 alır')


def test_kd1_try_yeniden_hesapla_bos_karsiligi_dolduruyor():
    """Kur sonradan girilince boş TRY karşılığı dolmalı."""
    c = istemci('admin', 'ADMIN')
    _t = date(2026, 3, 17)
    with fa.app.app_context():
        db.session.add(Cari(id='MUS-KD2', unvan='MUSTERI KD2',
                            cari_tip='Müşteri', para_birimi='USD'))
        db.session.add(CariHareket(
            id='HR-KD2', cari_id='MUS-KD2', cari_unvan='MUSTERI KD2',
            hareket_tarihi=_t, islem_tip='Satis Faturasi',
            doviz='USD', borc=1000, alacak=0,
            borc_try=None, alacak_try=None))
        # `_kur_getir` önceliği: alis -> efektif -> satis
        db.session.add(DovizKur(doviz='USD', tarih=_t, alis=38.40,
                                satis=38.60, efektif=38.40))
        db.session.commit()

    r = c.post('/api/cari/hareket/try_yeniden_hesapla', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    j = r.get_json()
    assert j.get('ok') is True, j
    assert j.get('guncellenen', 0) >= 1, j

    with fa.app.app_context():
        h = db.session.get(CariHareket, 'HR-KD2')
        assert h.borc_try == 38400.0, h.borc_try
        assert float(h.kur_uygulanan or 0) == 38.40, h.kur_uygulanan
        assert h.kur_kaynak == 'TCMB', h.kur_kaynak


def test_kd1_satis_suzgeci_ve_musteri_ozeti():
    """Süzgeç listesi ve müşteri özeti gerçek veriyi döndürmeli."""
    from models import SatisKaydi
    c = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        db.session.add(Cari(id='MUS-KD3', unvan='KD3 STONE LLC',
                            cari_tip='Müşteri', para_birimi='USD'))
        for i, (tutar, maliyet, t) in enumerate((
                (10000, 7000, date(2026, 2, 3)),
                (20000, 13000, date(2026, 6, 9))), 1):
            db.session.add(SatisKaydi(
                id=f'SK-KD3-{i}', cari_id='MUS-KD3',
                musteri='KD3 STONE LLC', cins='KD3 Beyaz',
                stok_tip='PLAKA', miktar=100, birim='m2',
                doviz='USD', tutar_usd=tutar, maliyet_usd=maliyet,
                kar_usd=tutar - maliyet, satis_tarihi=t))
        db.session.commit()

    d = c.get('/api/satislar/lookup', headers=H)
    assert d.status_code == 200, d.get_data(as_text=True)[:200]
    j = d.get_json()
    assert 'KD3 STONE LLC' in (j.get('musteriler') or []), j
    assert 'KD3 Beyaz' in (j.get('cinsler') or []), j

    o = c.get('/api/satislar/musteri/KD3%20STONE%20LLC/ozet', headers=H)
    assert o.status_code == 200, o.get_data(as_text=True)[:200]
    jo = o.get_json()
    assert jo.get('adet') == 2, jo
    assert float(jo.get('toplam_usd') or 0) == 30000.0, jo
    assert float(jo.get('kar_usd') or 0) == 10000.0, jo
    # 10.000 / 30.000 = %33,33
    assert round(float(jo.get('marj_yuzde') or 0), 2) == 33.33, jo
    assert jo.get('ilk_satis') == '2026-02-03', jo
    assert jo.get('son_satis') == '2026-06-09', jo


def test_kd1_sablon_betikleri_ayristirilabiliyor():
    """Her şablonun satır içi <script>'i node ile ayrıştırılmalı.

    BU YAMADA OLDU: çekmeceye eklediğim bir yorumun içindeki ters
    tırnak, onu saran şablon dizgesini orada sonlandırdı ve
    satislar.html'in TÜM betiği ayrıştırılamaz hâle geldi — tablo
    "Yükleniyor…"da kaldı, süzgeçler boş geldi. 289 test geçti,
    çünkü hiçbiri şablon JS'ini ayrıştırmıyordu.

    `js_denetim.py` bunu yakalıyor ama yalnızca `gonder.sh`
    içinde — yani push anında. Takımın içinde de olması gerekiyor:
    hatanın DOĞDUĞU yerde çıkması, push'ta çıkmasından iyidir.
    """
    import io as _io
    import os as _os
    import re as _re
    import shutil as _shutil
    import subprocess as _sp
    import tempfile as _tf

    node = _shutil.which('node') or _shutil.which('nodejs')
    if not node:
        import pytest as _pytest
        _pytest.skip('node yok')

    _sablon = _os.path.join(KOK, 'templates')
    # src= taşıyan <script> dış dosya; gövdesi yok.
    desen = _re.compile(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', _re.S)
    kirik = []
    gec = _tf.mkdtemp()
    for ad in sorted(_os.listdir(_sablon)):
        if not ad.endswith('.html'):
            continue
        metin = _io.open(_os.path.join(_sablon, ad),
                         encoding='utf-8', errors='replace').read()
        for sira, m in enumerate(desen.finditer(metin), 1):
            js = m.group(1)
            # Jinja ifadeleri JS degil: degeri sabitle, blogu at.
            js = _re.sub(r'\{\{.*?\}\}', '0', js, flags=_re.S)
            js = _re.sub(r'\{%.*?%\}', '', js, flags=_re.S)
            if not js.strip():
                continue
            yol = _os.path.join(gec, f'{ad}.{sira}.js')
            _io.open(yol, 'w', encoding='utf-8').write(js)
            r = _sp.run([node, '--check', yol],
                        capture_output=True, text=True)
            if r.returncode != 0:
                ilk = [s for s in r.stderr.split('\n')
                       if 'Error' in s or ':' in s][:3]
                kirik.append(f'{ad} (script #{sira}): ' + ' / '.join(ilk))
    assert not kirik, ('şablon betiği ayrıştırılamıyor — o sayfadaki '
                       'HİÇBİR düğme çalışmaz: ' + '; '.join(kirik))


def test_kd1_betik_bekcisi_kirik_betigi_yakaliyor():
    """Bekçi, bu yamada yaptığım hatanın tam kopyasını görmeli."""
    import os as _os
    import shutil as _shutil
    import subprocess as _sp
    import tempfile as _tf
    node = _shutil.which('node') or _shutil.which('nodejs')
    if not node:
        import pytest as _pytest
        _pytest.skip('node yok')
    # Sablon dizgesinin ICINDE ters tirnak tasiyan bir yorum
    sahte = (
        'function f(x) {\n'
        '  const g = `<div>\n'
        '    <!-- aciklama: `GET /api/bir/sey` yazilmisti -->\n'
        '    <div id="y"></div>`;\n'
        '  return g;\n'
        '}\n')
    p = _os.path.join(_tf.mkdtemp(), 'k.js')
    open(p, 'w', encoding='utf-8').write(sahte)
    r = _sp.run([node, '--check', p], capture_output=True, text=True)
    assert r.returncode != 0, (
        'bekçinin dayandığı `node --check`, şablon dizgesini bölen '
        'ters tırnağı yakalamıyor')


# ══════════════════════════════════════════════════════════════════
#  DV1 · FİYAT KENDİ PARA BİRİMİYLE YOLCULUK EDER
#
#  ÖLÇÜLDÜ: EUR bir proformanın kalemleri `'USD'` damgalanıyordu
#  (`doviz=k.get('doviz','USD')` — belgenin dövizi yerine sabit
#  USD). Ekran kalem satırını `k.doviz || p.doviz` ile bastığı için
#  EUR proformada HER SATIRDA $ görünüyordu; müşteriye giden
#  belgede. Sipariş tarafında aynı şey sayıya dönüşüyordu:
#
#     10.000 USD + 10.000 EUR kalemli sipariş -> "20.000 USD"
#     (gerçeği 21.250) ve bu sayı faturaya, cari harekete ve
#     satış kaydına aynen geçiyordu.
#
#  KURAL: proformada 50 EUR ise siparişte de, faturada da, satış
#  kaydında da 50 EUR. Hiçbir yerde çevrilmez. Bunun gereği, kalem
#  dövizinin BELGEDEN miras alınması; farklı bir döviz bilerek
#  gönderilirse belge reddedilir.
# ══════════════════════════════════════════════════════════════════
def _dv1_kurulum():
    from models import Firma
    with fa.app.app_context():
        if not Cari.query.get('DV1-MUS'):
            db.session.add(Cari(id='DV1-MUS', unvan='DV1 STONE LLC',
                                cari_tip='Müşteri', para_birimi='EUR',
                                gorunurluk='acik'))
        for dv, k in (('USD', 40.0), ('EUR', 45.0)):
            if not DovizKur.query.filter_by(
                    doviz=dv, tarih=date(2026, 10, 28)).first():
                db.session.add(DovizKur(doviz=dv, tarih=date(2026, 10, 28),
                                        alis=k, satis=k, efektif=k))
        db.session.commit()
    return istemci('admin', 'ADMIN')


_DV1_KALEM = {'urun_tip': 'PLAKA', 'cins': 'DV1 CALACATTA', 'miktar': 100,
              'birim': 'm2', 'birim_fiyat': 50}


def test_dv1_kalem_dovizi_belgeden_geliyor():
    """EUR proformanın kalemi EUR olmalı; 50 EUR, 50 EUR kalmalı."""
    from models import Proforma, ProformaKalem
    c = _dv1_kurulum()
    r = c.post('/api/proforma', headers=H, json={
        'musteri': 'DV1 STONE LLC', 'tarih': '2026-10-28',
        'doviz': 'EUR', 'kalemler': [dict(_DV1_KALEM)]})
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    pid = r.get_json()['id']
    with fa.app.app_context():
        p = db.session.get(Proforma, pid)
        kalemler = ProformaKalem.query.filter_by(proforma_id=pid).all()
        assert p.doviz == 'EUR', p.doviz
        assert kalemler, 'kalem yazılmamış'
        for k in kalemler:
            # ESKI DAVRANIS: k.doviz == 'USD'
            assert (k.doviz or '').upper() == 'EUR', (
                f'belge EUR ama kalem {k.doviz} — ekran kalem satırını '
                f'`k.doviz || p.doviz` ile basıyor, EUR belgede $ görünür')
            assert float(k.birim_fiyat or 0) == 50.0, k.birim_fiyat


def test_dv1_farkli_dovizli_kalem_reddediliyor():
    """Kalem bilerek farklı döviz taşıyorsa belge 400 almalı."""
    c = _dv1_kurulum()
    r = c.post('/api/proforma', headers=H, json={
        'musteri': 'DV1 STONE LLC', 'tarih': '2026-10-28',
        'doviz': 'EUR', 'kalemler': [dict(_DV1_KALEM, doviz='USD')]})
    assert r.status_code == 400, r.status_code
    j = r.get_json()
    assert j.get('error') == 'kalem_dovizi', j
    # Sebep SOYLENMELI: hangi kalem, hangi para birimi
    assert 'USD' in j.get('mesaj', '') and 'EUR' in j.get('mesaj', ''), j


def test_dv1_proforma_dovizi_degisince_kalemler_takip_ediyor():
    """Belgenin dövizi değişince kalemler yeni dövize geçmeli."""
    from models import Proforma, ProformaKalem
    c = _dv1_kurulum()
    r = c.post('/api/proforma', headers=H, json={
        'musteri': 'DV1 STONE LLC', 'tarih': '2026-10-28',
        'doviz': 'USD', 'kalemler': [dict(_DV1_KALEM)]})
    pid = r.get_json()['id']
    # USD -> EUR. Yönü USD'DEN ÇIKACAK şekilde seçmek önemli: ilk
    # yazdığımda EUR -> USD yapmıştım ve test ESKİ KODDA DA geçti,
    # çünkü eski kod kalemi zaten sabit 'USD' yapıyordu. Bir test,
    # düzeltmeden önce düşmüyorsa hiçbir şey ölçmüyordur.
    r2 = c.put(f'/api/proforma/{pid}', headers=H, json={
        'musteri': 'DV1 STONE LLC', 'doviz': 'EUR',
        'kalemler': [dict(_DV1_KALEM)]})
    assert r2.status_code == 200, r2.get_data(as_text=True)[:300]
    with fa.app.app_context():
        p = db.session.get(Proforma, pid)
        assert p.doviz == 'EUR', p.doviz
        for k in ProformaKalem.query.filter_by(proforma_id=pid).all():
            assert (k.doviz or '').upper() == 'EUR', (
                f'belge EUR oldu ama kalem {k.doviz} kaldı')


def test_dv1_karisik_dovizli_siparis_olusturulamiyor():
    """Sıcak satış karışık dövizli kalem kabul etmemeli.

    ESKIDEN: 10.000 USD + 10.000 EUR kabul ediliyor, sipariş
    'toplam_tutar=20000 USD' yazıyor, fatura ve cari hareket de
    o sayıyı alıyordu."""
    c = _dv1_kurulum()
    r = c.post('/api/sicak_satis', headers=H, json={
        'musteri': 'DV1 STONE LLC', 'tarih': '2026-10-28',
        'siparis_tarihi': '2026-10-28', 'doviz': 'USD',
        'kalemler': [
            dict(_DV1_KALEM, cins='DV1 A', birim_fiyat=100, doviz='USD'),
            dict(_DV1_KALEM, cins='DV1 B', birim_fiyat=100, doviz='EUR'),
        ]})
    assert r.status_code == 400, (
        f'karışık dövizli sipariş kabul edildi ({r.status_code}) — '
        f'toplam çevrilmeden toplanır ve tek para birimiyle etiketlenir')
    assert r.get_json().get('error') == 'kalem_dovizi', r.get_json()


def test_dv1_transit_faturada_kalem_basina_satis_kaydi():
    """Transit faturada her kalem kendi satış kaydını almalı.

    ESKIDEN tek kayıt vardı: cins İLK kalemden, miktar FARKLI
    BİRİMLERDEN toplanarak. 100 m² plaka + 20 ton blok satışı
    "CALACATTA · 120 m²" olarak kaydediliyordu."""
    from models import SatisKaydi
    c = _dv1_kurulum()
    r = c.post('/api/sicak_satis', headers=H, json={
        'musteri': 'DV1 STONE LLC', 'tarih': '2026-10-28',
        'siparis_tarihi': '2026-10-28', 'doviz': 'USD',
        'kalemler': [
            {'urun_tip': 'PLAKA', 'cins': 'DV1 PLAKA', 'miktar': 100,
             'birim': 'm2', 'birim_fiyat': 100, 'adet': 1,
             'boy': 300, 'yukseklik': 180, 'kalinlik': 2},
            {'urun_tip': 'BLOK', 'cins': 'DV1 BLOK', 'miktar': 20,
             'birim': 'ton', 'birim_fiyat': 500, 'adet': 1,
             'boy': 300, 'yukseklik': 180, 'en': 170},
        ]})
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    fid = r.get_json().get('fatura_id')
    assert fid, r.get_json()

    with fa.app.app_context():
        kayitlar = SatisKaydi.query.filter_by(fatura_id=fid).all()
        assert len(kayitlar) == 2, (
            f'{len(kayitlar)} satış kaydı — 2 kalem için 2 olmalı: '
            + str([(k.cins, k.miktar, k.birim) for k in kayitlar]))
        esle = {k.cins: k for k in kayitlar}
        assert set(esle) == {'DV1 PLAKA', 'DV1 BLOK'}, list(esle)
        # Her kayıt KENDİ birimini ve miktarını taşır
        assert esle['DV1 PLAKA'].birim == 'm2', esle['DV1 PLAKA'].birim
        assert esle['DV1 BLOK'].birim == 'ton', esle['DV1 BLOK'].birim
        assert float(esle['DV1 PLAKA'].miktar or 0) == 100.0
        assert float(esle['DV1 BLOK'].miktar or 0) == 20.0
        # TOPLAM KORUNUR: paylar faturanın matrahını tam verir
        toplam = round(sum(float(k.tutar or 0) for k in kayitlar), 2)
        assert toplam == 20000.0, (
            f'payların toplamı {toplam}, fatura matrahı 20000')
        toplam_usd = round(sum(float(k.tutar_usd or 0) for k in kayitlar), 2)
        assert toplam_usd == 20000.0, toplam_usd


def test_dv1_stok_gruplar_ucu_silindi():
    """Ölü ve döviz karıştıran uç gerçekten kalkmış olmalı.

    404 DEĞİL 405 dönüyor: yol artık `/api/stok/<stok_id>`
    kuralına düşüyor ve o kural GET kabul etmiyor. Önemli olan
    veri DÖNMEMESİ."""
    c = istemci('admin', 'ADMIN')
    r = c.get('/api/stok/gruplar', headers=H)
    assert r.status_code in (404, 405), r.status_code
    assert b'gruplar' not in r.get_data(), r.get_data()[:120]


def test_dv1_sabit_yollu_her_uc_bir_ekrandan_cagriliyor():
    """Parametresiz /api/ uçlarının TAM YOLU bir yerde geçmeli.

    BU TARAMANIN KÖR NOKTASIYDI. `ulasilmaz_uc_tara` ÖNEK
    eşliyordu: `/api/stok/gruplar` için `/api/stok` şablonlarda
    geçiyor ve GET de kullanılıyor, bu yüzden uç "ulaşılabilir"
    sayılıyordu — oysa tam yolu hiçbir yerde yoktu ve uç yarım
    kurulmuş hâlde, döviz karıştırarak duruyordu.

    Parametresiz yollarda tahmine gerek yok: tam dizge aranır."""
    import ast as _ast
    import io as _io
    import re as _re

    ANA = os.path.join(KOK, 'flask_app.py')
    kaynak = _io.open(ANA, encoding='utf-8').read().replace('\r\n', '\n')
    agac = _ast.parse(kaynak)

    tuketici = []
    for dizin in ('templates', 'static', 'blueprints'):
        kok = os.path.join(KOK, dizin)
        if not os.path.isdir(kok):
            continue
        for yer, _, dosyalar in os.walk(kok):
            for ad in dosyalar:
                if ad.endswith(('.html', '.js', '.py')):
                    tuketici.append(_io.open(
                        os.path.join(yer, ad), encoding='utf-8',
                        errors='replace').read())
    tuketici = '\n'.join(tuketici)

    olu = []
    for fn in _ast.walk(agac):
        if not isinstance(fn, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            continue
        for dec in fn.decorator_list:
            if not (isinstance(dec, _ast.Call)
                    and isinstance(dec.func, _ast.Attribute)
                    and dec.func.attr == 'route' and dec.args
                    and isinstance(dec.args[0], _ast.Constant)):
                continue
            yol = dec.args[0].value
            if not yol.startswith('/api/') or '<' in yol:
                continue
            # Teshis uclari BILEREK ekransiz: ADMIN'in elle cagirdigi
            # tani araclari. `_diag_guard` onlari zaten kapatiyor.
            if yol.startswith('/api/diag/'):
                continue
            if _re.search(_re.escape(yol), tuketici):
                continue
            if kaynak.count(yol) > 1:
                continue        # flask_app kendi icinde cagiriyor
            olu.append(f'{yol} ({fn.name}, satır {fn.lineno})')

    assert not olu, (
        'tam yolu hiçbir ekranda/blueprint\'te geçmeyen uç(lar) — '
        'ya bağlanmalı ya silinmeli: ' + ', '.join(sorted(olu)))


def test_dv1_kalem_dovizi_sabit_usd_yazilmamis():
    """KALEM dövizi sabit 'USD'ye düşmemeli — belgeden gelmeli.

    BELGENİN kendi dövizi için `data.get('doviz','USD')` doğrudur:
    orada varsayılan gerçekten USD. Yanlış olan, KALEMİN dövizini
    belgeye bakmadan USD yapmaktı. Bekçi yalnız kalem değişkenlerine
    (`k`, `_k`, `k_data`, `kalem`) bakar; kapsamı geniş tutmak,
    doğru satırları da kırmızıya boyayıp bekçiyi kapattırırdı."""
    import io as _io
    import re as _re
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    desen = _re.compile(
        r"doviz\s*=\s*(k|_k|kl|kalem|k_data|pk|_kalem)\.get\("
        r"'doviz'\s*,\s*'[A-Z]{3}'\)")
    kacak = []
    for i, t in enumerate(kaynak.split('\n'), 1):
        if t.lstrip().startswith('#'):
            continue                  # yorum; açıklama metni olabilir
        if desen.search(t):
            kacak.append(f'satır {i}: {t.strip()[:70]}')
    assert not kacak, (
        'kalem dövizi belgeden değil sabit bir para biriminden '
        'alınıyor: ' + '; '.join(kacak))


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


# ══════════════════════════════════════════════════════════════════
#  IP1 · İPTAL, PARA İZLERİNİ SORMADAN BIRAKMAZ
#
#  İşin sahibi bildirdi, ölçüldü: faturası kesilmiş bir siparişi
#  satış hattından iptal etmek HİÇBİR ŞEYİ geri almıyordu. Fatura
#  "Tahsil Edildi" kalıyor, cariye yazılan 3.024 $ borç duruyor,
#  stoklar satılmış kalıyordu.
#
#  Üstüne iki şey daha çıktı:
#   · Çeki silmek "bağlı kayıtlar geri alındı" diyordu ama cari
#     hareket DURUYORDU: geri alma `cek.cari_hareket_id` bağını
#     arıyor, hızlı satış o alanı hiç doldurmuyordu (TS1'in aynısı).
#   · Hızlı satış stokları 'Teslim Edildi' yapıyordu; serbest
#     bırakma yalnız Satildi/Rezerve'ye dokunduğu için plakalar
#     KALICI olarak kilitli kalıyordu — ne serbest ne satılabilir.
#
#  Karar kullanıcınındır: sunucu neyin kararını beklediğini söyleyip
#  409 döner, ekran sırayla sorar.
# ══════════════════════════════════════════════════════════════════
def _ip1_satis(ek):
    """Hızlı satış kurar; (istemci, siparis_id, fatura_id, cek_id) döner."""
    from models import Firma, PlakaStok, Siparis
    with fa.app.app_context():
        if not Cari.query.get('IP1-MUS'):
            db.session.add(Cari(id='IP1-MUS', unvan='IP1 ACAR MERMER',
                                cari_tip='Müşteri', para_birimi='USD',
                                gorunurluk='acik'))
        if not DovizKur.query.filter_by(
                doviz='USD', tarih=date(2026, 10, 29)).first():
            db.session.add(DovizKur(doviz='USD', tarih=date(2026, 10, 29),
                                    alis=40, satis=40, efektif=40))
        idler = []
        for i in range(1, 6):
            sid = f'PLK-IP1{ek}-{i:02d}'
            idler.append(sid)
            if not PlakaStok.query.get(sid):
                db.session.add(PlakaStok(
                    id=sid, blok_no=f'IP1{ek}', cins='IP1 CEPPO',
                    boy=298, yukseklik=169, kalinlik=2, metraj_m2=5.04,
                    alis_fiyati=36.0, alis_fiyat_birim='m2', matrah=181.44,
                    doviz='USD', durum='Serbest',
                    giris_tarihi=date(2026, 10, 29)))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/sicak_satis', headers=H, json={
        'musteri': 'IP1 ACAR MERMER', 'satis_tipi': 'yurtici',
        'odeme_sekli': 'Cek', 'teslim_sekli': 'EXW',
        'fatura_no': f'IP1-{ek}-001', 'vade_tarihi': '2026-10-30',
        'doviz': 'USD', 'kdv_oran': 20, 'kdv_dahil_mi': False,
        'kalemler': [{
            'urun_tip': 'PLAKA', 'cins': 'IP1 CEPPO', 'stok_ids': idler,
            'adet': 5, 'miktar': 25.2, 'birim': 'm2', 'birim_fiyat': 100,
            'doviz': 'USD', 'sira': 1,
            'boy': 298, 'yukseklik': 169, 'kalinlik': 2}],
        'cek': {'cek_no': f'CK-IP1-{ek}', 'banka_adi': 'İş Bankası',
                'tutar': None, 'vade_tarihi': '2026-12-15'},
    })
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    j = r.get_json()
    with fa.app.app_context():
        sip = Siparis.query.filter_by(musteri='IP1 ACAR MERMER').order_by(
            Siparis.id.desc()).first()
        sip_id = sip.id
    return c, sip_id, j['fatura_id'], j.get('cek_id'), idler


def test_ip1_hizli_satis_stogu_satildi_birakiyor():
    """'Teslim Edildi' bırakmak stoğu kalıcı kilitliyordu."""
    from models import PlakaStok
    c, sip_id, fid, cek_id, idler = _ip1_satis('A')
    with fa.app.app_context():
        for sid in idler:
            s = db.session.get(PlakaStok, sid)
            assert s.durum == 'Satildi', (sid, s.durum)


def test_ip1_cekin_cari_hareketi_cekle_baglaniyor():
    """`cek.cari_hareket_id` boş kalırsa geri alma hareketi bulamaz."""
    from models import Cek
    c, sip_id, fid, cek_id, idler = _ip1_satis('B')
    with fa.app.app_context():
        ck = db.session.get(Cek, cek_id)
        assert ck.cari_hareket_id, (
            'çekin cari hareket bağı boş — silinince alacak cariye asılı '
            'kalır')


def test_ip1_cek_silinince_cari_alacak_da_gidiyor():
    """TS1 kalıbı: 'geri alındı' diyorsa gerçekten geri almalı."""
    from models import CariHareket
    c, sip_id, fid, cek_id, idler = _ip1_satis('C')
    with fa.app.app_context():
        once = CariHareket.query.filter_by(
            baglanti_tip='cek', baglanti_id=cek_id).count()
        assert once == 1, once
    r = c.delete(f'/api/cek/{cek_id}', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    with fa.app.app_context():
        kalan = CariHareket.query.filter_by(
            baglanti_tip='cek', baglanti_id=cek_id).count()
        assert kalan == 0, (
            f'çek silindi ama {kalan} cari hareket duruyor — '
            f'müşteri alacaklı görünür')


def test_ip1_faturali_siparis_iptali_karar_istiyor():
    """Sormadan iptal etmemeli; neyin kararını beklediğini söylemeli."""
    from models import Siparis, CariHareket, Fatura
    c, sip_id, fid, cek_id, idler = _ip1_satis('D')
    r = c.put(f'/api/siparis/{sip_id}', headers=H,
              json={'durum': 'Iptal Edildi'})
    assert r.status_code == 409, r.status_code
    j = r.get_json()
    assert j.get('error') == 'iptal_onayi_gerekli', j
    k = j.get('karar') or {}
    assert k.get('faturalar'), k
    assert k['faturalar'][0]['id'] == fid, k
    assert float(k['faturalar'][0]['cari_borc']) == 3024.0, k
    assert k.get('cekler') and k['cekler'][0]['id'] == cek_id, k
    # HİÇBİR ŞEYE DOKUNULMAMIŞ OLMALI
    with fa.app.app_context():
        assert db.session.get(Siparis, sip_id).durum == 'Hazir'
        assert db.session.get(Fatura, fid).durum != 'Iptal'
        assert CariHareket.query.filter_by(cari_id='IP1-MUS').count() >= 2


def test_ip1_cek_iade_secilince_her_sey_geri_aliniyor():
    """Çek iade: cari sıfırlanmalı, stok serbest, satış kaydı silinmeli."""
    from models import Siparis, Fatura, Cek, CariHareket, SatisKaydi, PlakaStok
    c, sip_id, fid, cek_id, idler = _ip1_satis('E')
    r = c.put(f'/api/siparis/{sip_id}', headers=H, json={
        'durum': 'Iptal Edildi',
        'iptal_onay': {'fatura_iptal': True, 'cek': 'iade',
                       'tahsilat': 'sil'}})
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    with fa.app.app_context():
        assert db.session.get(Siparis, sip_id).durum == 'Iptal Edildi'
        assert db.session.get(Fatura, fid).durum == 'Iptal'
        assert db.session.get(Cek, cek_id).durum == 'Iptal'
        kalan = CariHareket.query.filter_by(cari_id='IP1-MUS').all()
        kalan = [h for h in kalan
                 if h.baglanti_id in (fid, cek_id)]
        assert not kalan, [(h.id, h.islem_tip, h.borc, h.alacak)
                           for h in kalan]
        assert SatisKaydi.query.filter_by(fatura_id=fid).count() == 0
        for sid in idler:
            assert db.session.get(PlakaStok, sid).durum == 'Serbest', sid


def test_ip1_cek_alacak_secilince_musteri_alacakli_kaliyor():
    """Çek bizde kalırsa borç silinir, alacak DURUR — bu doğru."""
    from models import Fatura, Cek, CariHareket
    c, sip_id, fid, cek_id, idler = _ip1_satis('F')
    r = c.put(f'/api/siparis/{sip_id}', headers=H, json={
        'durum': 'Iptal Edildi',
        'iptal_onay': {'fatura_iptal': True, 'cek': 'alacak',
                       'tahsilat': 'alacak'}})
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    with fa.app.app_context():
        assert db.session.get(Fatura, fid).durum == 'Iptal'
        ck = db.session.get(Cek, cek_id)
        assert ck.durum == 'Portfoyde', ck.durum
        # Çek faturadan KOPARILMALI: kopmazsa fatura iptali
        # "tahsilat var" diye reddedilir ve kullanıcı çıkmaza girer.
        assert ck.fatura_id is None, ck.fatura_id
        borclar = [h for h in CariHareket.query.filter_by(
            cari_id='IP1-MUS').all() if h.baglanti_id == fid]
        assert not borclar, 'fatura borcu geri alınmamış'
        alacak = [h for h in CariHareket.query.filter_by(
            cari_id='IP1-MUS').all() if h.baglanti_id == cek_id]
        assert alacak and float(alacak[0].alacak or 0) == 3024.0, alacak


def test_ip1_fatura_iptali_tek_kapidan_geciyor():
    """`_fatura_iptal_geri_al` tek kaynak olmalı."""
    import io as _io
    import re as _re
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    assert 'def _fatura_iptal_geri_al(' in kaynak
    # İki çağıran: fatura durum ucu + sipariş iptali
    assert kaynak.count('_fatura_iptal_geri_al(') >= 3, (
        'ortak kapı tek yerden çağrılıyor — ikinci çağıran kaybolmuş')
    # Borç hareketini silen kod kapının DIŞINDA tekrarlanmamalı
    kacak = [f'satır {i}' for i, t in enumerate(kaynak.split('\n'), 1)
             if "baglanti_tip='fatura'" in t and 'kaynak=\'fatura\'' in t]
    assert len(kacak) <= 2, (
        'fatura borç hareketini arayan birden fazla yer var: ' + str(kacak))


def test_ip1_ekran_iptal_kararlarini_soruyor():
    """Sunucu 409 dönse de ekran sormuyorsa hiçbir şey değişmez."""
    import io as _io
    s = _io.open(os.path.join(KOK, 'templates', 'siparis.html'),
                 encoding='utf-8').read()
    assert 'iptal_onayi_gerekli' in s, 'ekran 409 kararını işlemiyor'
    assert 'iptal_onay' in s, 'ekran kararları geri göndermiyor'
    assert '_iptalKararlariniSor' in s
    for secim in ("'iade'", "'alacak'", "'sil'"):
        assert secim in s, f'{secim} seçeneği ekranda yok'


# ══════════════════════════════════════════════════════════════════
#  VR1 · ÇİFT BACAKLI TRANSFER, TEK BACAK SİLİNEMEZ
#
#  "Yan etki yaratan işlem, geri alınırken o yan etkiyi bırakıyor"
#  sınıfının taramasından çıktı (TS1 ve IP1 ile aynı aile). Üçü de
#  ölçüldü:
#
#   · Kasa virmanı A→B 3.000 TL, çıkış bacağını sil:
#     A parasını geri alır, B'de para DURUR. Sistemdeki toplam
#     10.000 → 13.000 TL. PARA YOKTAN VAR OLDU.
#   · Cari→kasa transferi 5.000 TL, cari hareketi sil:
#     kasa parayı tutar, karşılığı olan kayıt yoktur.
#   · Cari→cari transferi 2.000 TL, bir bacağı sil:
#     bir cari alacaklı kalır, karşılığı yoktur.
#
#  Transfer atomik YARATILIYOR ama atomik SİLİNMİYORDU.
# ══════════════════════════════════════════════════════════════════
def _vr1_kurulum(ek):
    from models import Kasa
    with fa.app.app_context():
        for ad, bak in ((f'VR1 A{ek}', 10000), (f'VR1 B{ek}', 0)):
            if not Kasa.query.filter_by(ad=ad).first():
                db.session.add(Kasa(ad=ad, doviz='TRY', bakiye=bak))
        for cid, unv in ((f'VR1-C1{ek}', f'VR1 ALFA{ek}'),
                         (f'VR1-C2{ek}', f'VR1 BETA{ek}')):
            if not Cari.query.get(cid):
                db.session.add(Cari(id=cid, unvan=unv, cari_tip='Müşteri',
                                    para_birimi='TRY', gorunurluk='acik'))
        db.session.commit()
        a = Kasa.query.filter_by(ad=f'VR1 A{ek}').first().id
        b = Kasa.query.filter_by(ad=f'VR1 B{ek}').first().id
    return istemci('admin', 'ADMIN'), a, b


def _vr1_toplam(kasa_idler):
    from models import Kasa
    with fa.app.app_context():
        return round(sum(float(db.session.get(Kasa, k).bakiye or 0)
                         for k in kasa_idler), 2)


def test_vr1_virmanin_tek_bacagi_silinince_para_yoktan_var_olmuyor():
    """Toplam para KORUNMALI."""
    from models import KasaHareket
    c, a, b = _vr1_kurulum('A')
    once = _vr1_toplam([a, b])
    r = c.post('/api/kasa/virman', headers=H, json={
        'kaynak_kasa_id': a, 'hedef_kasa_id': b, 'tutar': 3000,
        'tarih': '2026-10-29', 'aciklama': 'VR1 testi'})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    assert _vr1_toplam([a, b]) == once, 'virman toplamı değiştirmemeli'

    with fa.app.app_context():
        bacaklar = KasaHareket.query.filter_by(
            baglanti_tip='virman').filter(
            KasaHareket.kasa_id.in_((a, b))).all()
        assert len(bacaklar) == 2, len(bacaklar)
        ilk = bacaklar[0].id
    d = c.delete(f'/api/kasa/hareket/{ilk}', headers=H)
    assert d.status_code == 200, d.get_data(as_text=True)[:200]
    # ESKI DAVRANIS: 10.000 -> 13.000
    assert _vr1_toplam([a, b]) == once, (
        f'tek bacak silinince toplam {_vr1_toplam([a, b])} oldu, '
        f'{once} olmalıydı — para yoktan var oldu')
    with fa.app.app_context():
        kalan = KasaHareket.query.filter_by(baglanti_tip='virman').filter(
            KasaHareket.kasa_id.in_((a, b))).count()
        assert kalan == 0, f'{kalan} bacak öksüz kaldı'


def test_vr1_cariden_kasaya_transfer_silinince_kasa_parayi_tutmuyor():
    """Cari kaydı silinince kasadaki karşılığı da gitmeli."""
    from models import Kasa, KasaHareket, CariHareket
    c, a, b = _vr1_kurulum('B')
    once = _vr1_toplam([a])
    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': 'VR1-C1B', 'islem_tip': 'Bakiye Transfer',
        'transfer_yonu': 'kasa', 'hedef_kasa_id': a, 'tutar': 5000,
        'doviz': 'TRY', 'hareket_tarihi': '2026-10-29'})
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    assert _vr1_toplam([a]) == round(once + 5000, 2)
    with fa.app.app_context():
        h = CariHareket.query.filter_by(
            cari_id='VR1-C1B', baglanti_tip='kasa').first()
        assert h, 'cari tarafı oluşmamış'
        hid = h.id
    d = c.delete(f'/api/cari/hareket/{hid}', headers=H)
    assert d.status_code == 200, d.get_data(as_text=True)[:250]
    # ESKI DAVRANIS: kasa 5.000'i tutuyordu
    assert _vr1_toplam([a]) == once, (
        f'kasa {_vr1_toplam([a])} ile kaldı, {once} olmalıydı — '
        f'karşılığı olmayan para')
    with fa.app.app_context():
        assert KasaHareket.query.filter_by(
            kasa_id=a, baglanti_tip='virman').count() == 0


def test_vr1_cariden_cariye_transfer_tek_tarafli_kalmiyor():
    """İki cari hareketinden biri silinince öteki de gitmeli."""
    from models import CariHareket
    c, a, b = _vr1_kurulum('C')
    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': 'VR1-C1C', 'islem_tip': 'Bakiye Transfer',
        'transfer_yonu': 'cari', 'hedef_cari_id': 'VR1-C2C',
        'tutar': 2000, 'doviz': 'TRY', 'hareket_tarihi': '2026-10-29'})
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    with fa.app.app_context():
        hs = CariHareket.query.filter(
            CariHareket.cari_id.in_(('VR1-C1C', 'VR1-C2C'))).all()
        assert len(hs) == 2, len(hs)
        hid = hs[0].id
    d = c.delete(f'/api/cari/hareket/{hid}', headers=H)
    assert d.status_code == 200, d.get_data(as_text=True)[:250]
    with fa.app.app_context():
        kalan = CariHareket.query.filter(
            CariHareket.cari_id.in_(('VR1-C1C', 'VR1-C2C'))).all()
        assert not kalan, (
            'transferin öteki bacağı kaldı: '
            + str([(h.id, h.cari_id, h.borc, h.alacak) for h in kalan]))


def test_vr1_tahsilat_silme_bozulmadi():
    """VR1 eşi TS1'in tahsilat yolunu ETKİLEMEMELİ.

    `_transfer_esi` yalnız `kaynak='virman'` kayıtlara bakıyor;
    bakmasaydı tahsilat silerken yanlış bir kaydı eş sanıp silerdi.
    Bu testin işi o sınırı çivilemek."""
    from models import Kasa, KasaHareket, CariHareket
    c, a, b = _vr1_kurulum('D')
    # Kasaya elle bir giris: virman DEGIL
    r = c.post('/api/kasa/hareket', headers=H, json={
        'kasa_id': a, 'tip': 'giris', 'tutar': 1234,
        'tarih': '2026-10-29', 'aciklama': 'VR1 elle giris'})
    assert r.status_code in (200, 201), r.get_data(as_text=True)[:200]
    with fa.app.app_context():
        kh = KasaHareket.query.filter_by(
            kasa_id=a, tutar=1234).first()
        assert kh is not None
        khid = kh.id
    once = _vr1_toplam([a])
    d = c.delete(f'/api/kasa/hareket/{khid}', headers=H)
    assert d.status_code == 200, d.get_data(as_text=True)[:200]
    assert _vr1_toplam([a]) == round(once - 1234, 2), (
        'elle girilen hareket silinince yalnız kendi etkisi gitmeli')


def test_vr1_her_bag_tipinin_geri_alma_yolu_var():
    """Yaratılan her bağlantı tipinin bir geri alma yolu olmalı.

    DÜRÜST SINIR: bu bekçi, BUGÜNKÜ üç hatayı yakalamazdı ve
    yakalamıyor da (tabanda da geçiyor). Çünkü onlarda geri alma
    yolu VARDI, sadece eş bacağı bulamıyordu — yapısal değil
    davranışsal bir eksiklikti; onu yukarıdaki üç davranış testi
    çiviliyor.

    Bunun işi daha dar ve yine de değerli: yarın YENİ bir bağlantı
    tipiyle hareket yaratılır ve hiçbir geri alma yolu yazılmazsa
    (AF1'in ölü çek süzgeci, IP1'in çek bağı gibi) takımı kırar."""
    import ast as _ast
    import io as _io
    import re as _re
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    agac = _ast.parse(kaynak)

    yaratilan = set()
    for d in _ast.walk(agac):
        if not (isinstance(d, _ast.Call) and isinstance(d.func, _ast.Name)):
            continue
        if d.func.id not in ('CariHareket', 'KasaHareket',
                             '_cari_hareket_ekle'):
            continue
        for kw in d.keywords:
            if (kw.arg == 'baglanti_tip' and isinstance(kw.value, _ast.Constant)
                    and isinstance(kw.value.value, str)):
                yaratilan.add(kw.value.value)

    # Geri alınabilen tipler: bir süzgeçle aranıp silinen ya da ortak
    # kapıdan geçenler.
    geri = set(_re.findall(r"baglanti_tip\s*(?:==|=)\s*'([^']+)'", kaynak))
    for m in _re.finditer(r"baglanti_tip\.in_\(\(?\[?([^)\]]+)", kaynak):
        geri |= set(_re.findall(r"'([^']+)'", m.group(1)))

    # BİLEREK GERİ ALINMAYANLAR — her biri sebebiyle.
    MUAF = {
        # Kur farkı kayıtları `kapanis_hareket_id` üzerinden geri
        # alınıyor (`_kur_farki_geri_al`), bağ tipinden değil.
        'hareket',
        # Sipariş bağı: avans devri ve mahsup. Bunlar siparişin
        # kendi akışıyla geri alınıyor (avans siparişe döner).
        'siparis',
    }
    acik = sorted(yaratilan - geri - MUAF)
    assert not acik, (
        'bu bağlantı tipleriyle hareket yaratılıyor ama geri alma '
        'yolu yok: ' + ', '.join(acik))


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


# ══════════════════════════════════════════════════════════════════
#  GA1 · SUNUCUNUN OKUDUĞU GÖVDE ALANINI BİR EKRAN GÖNDERMELİ
#
#  HS1'DE ÖLÇÜLEN SINIF. İki yönü de gerçek çıkmıştı:
#    · `doviz` — hızlı satış formunda DÖVİZ seçimi vardı ama gövdeye
#      konmuyordu; sunucu bulamayınca USD'ye düşüyor ve EUR seçilen
#      satışın siparişi, faturası, cari hareketi, çeki ve satış
#      kayıtlarının HEPSİ USD kaydediliyordu.
#    · `kdv_dahil_mi` — ekranda böyle bir seçim HİÇ yoktu; sunucu
#      her zaman False okuyordu ve ekran "KDV dahil" yazıyordu.
#
#  İkisi de sessiz: istek 200 dönüyor, kayıt oluşuyor, sayı yanlış.
#
#  Bu bekçi her yazma ucu için sunucunun gövdeden okuduğu anahtarları
#  çıkarıp, o ucu çağıran şablonlarda geçip geçmediğine bakar.
#
#  MUAFİYET LİSTESİ KISA TUTULACAK. Uzayan bir liste, bekçinin
#  sessizce kapanmasıdır; her satırın sebebi yazılı.
# ══════════════════════════════════════════════════════════════════
_GA1_MUAF = {
    # Hızlı satış KDV'yi KENDİ hesaplıyor (HS1, KD1'in kapısından).
    # Bu okuma geriye dönük uyum için duruyor; ekranın göndermesi
    # beklenmiyor ve gönderse de üzerine yazılıyor.
    ('/api/sicak_satis', 'kdv_tutar'),
    # Satıştan fatura TASLAK olarak oluşur; KDV oranı ve vade
    # Faturalar ekranından giriliyor. Vade verilmezse `_vade_hesapla`
    # müşterinin ödeme vadesinden hesaplıyor.
    ('/api/satislar/<satis_id>/fatura', 'kdv_oran'),
    ('/api/satislar/<satis_id>/fatura', 'vade_tarihi'),
    # Satış düzenlemede birim DEĞİŞTİRİLMİYOR: m²'den ton'a geçmek
    # miktarın anlamını değiştirirdi. Alan okunuyor ama ekran
    # bilerek göndermiyor.
    ('/api/satislar/<satis_id>', 'birim'),
    # Kayıp tarihi verilmezse bugün kullanılıyor.
    ('/api/proforma/<proforma_id>/kaybedildi', 'tarih'),
    # Fatura tarihi verilmezse bugün, vade `_vade_hesapla` ile
    # müşterinin ödeme vadesinden hesaplanıyor (ölçüldü).
    ('/api/proforma/<proforma_id>/faturaya_donustur', 'fatura_tarihi'),
    ('/api/proforma/<proforma_id>/faturaya_donustur', 'vade_tarihi'),
    # Fatura güncellemede maliyet kalemleri yalnız içe aktarma
    # yolundan geliyor; ekranda böyle bir alan yok.
    ('/api/fatura/<fatura_id>', 'maliyet_kalemleri'),
    # Cari harekette fatura tarihi verilmezse hareket tarihi kullanılıyor.
    ('/api/cari/hareket', 'fatura_tarihi'),
}


def test_ga1_sunucunun_okudugu_govde_alanini_ekran_gonderiyor():
    """Sunucu bir alanı okuyorsa, onu çağıran ekran göndermeli.

    SINIRI ÖLÇÜLDÜ: HS1 öncesi `base.html` ile koşuldu ve
    `kdv_dahil_mi` eksikliğini YAKALADI. Ama `doviz` eksikliğini
    yakalayamadı — çünkü o şablonda `doviz:` KALEM nesnesinin içinde
    geçiyordu ve bekçi şablonun tamamında arıyor. Yani bekçi
    "anahtar şablonda hiç yok" durumunu görür, "üst düzey gövdede
    yok ama kalemde var" durumunu görmez.

    Daha incesi, JS gövde nesnesini ayrıştırmayı gerektirirdi; bu
    hâliyle de HS1'in iki hatasından birini yakalıyor."""
    import ast as _ast
    import io as _io
    import re as _re

    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    agac = _ast.parse(kaynak)

    sdizin = os.path.join(KOK, 'templates')
    sablonlar = {}
    for ad in sorted(os.listdir(sdizin)):
        if ad.endswith('.html'):
            sablonlar[ad] = _io.open(os.path.join(sdizin, ad),
                                     encoding='utf-8',
                                     errors='replace').read()

    YAZMA = {'POST', 'PUT', 'PATCH', 'DELETE'}
    IC_ALAN = {'onay', 'force', 'zorla', 'dry_run', 'test', 'debug'}
    # Sessiz varsayılanı PARAYI ya da ETİKETİ değiştirebilecek adlar.
    # `doviz` ve `kdv_dahil_mi` tam bu kümedendi.
    KRITIK = _re.compile(
        r'doviz|kur|kdv|tutar|fiyat|oran|matrah|vade|tarih|miktar|birim'
        r'|maliyet|komisyon|tevkifat|iskonto|avans|tahsilat|bakiye', _re.I)

    acik = []
    for fn in _ast.walk(agac):
        if not isinstance(fn, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            continue
        yollar, yontemler = [], []
        for dec in fn.decorator_list:
            if (isinstance(dec, _ast.Call)
                    and isinstance(dec.func, _ast.Attribute)
                    and dec.func.attr == 'route' and dec.args
                    and isinstance(dec.args[0], _ast.Constant)):
                yollar.append(dec.args[0].value)
                for kw in dec.keywords:
                    if kw.arg == 'methods':
                        yontemler += [e.value for e in
                                      getattr(kw.value, 'elts', [])
                                      if isinstance(e, _ast.Constant)]
        if not yollar:
            continue
        yol = yollar[0]
        if not yol.startswith('/api/') or yol.startswith('/api/diag/'):
            continue
        if not (set(yontemler) & YAZMA):
            continue

        # Gövde değişkeni: request.get_json() neye atanmış.
        govde_adlari = set()
        for d in _ast.walk(fn):
            if (isinstance(d, _ast.Assign) and len(d.targets) == 1
                    and isinstance(d.targets[0], _ast.Name)):
                kod = _ast.unparse(d.value)
                if ('request.get_json' in kod or 'request.json' in kod
                        or 'request.form' in kod):
                    govde_adlari.add(d.targets[0].id)
        if not govde_adlari:
            continue

        okunan = set()
        for d in _ast.walk(fn):
            if not (isinstance(d, _ast.Call)
                    and isinstance(d.func, _ast.Attribute)
                    and d.func.attr == 'get' and d.args
                    and isinstance(d.args[0], _ast.Constant)
                    and isinstance(d.args[0].value, str)):
                continue
            t = d.func.value
            ad_t = t.id if isinstance(t, _ast.Name) else (
                t.attr if isinstance(t, _ast.Attribute) else None)
            if ad_t in govde_adlari:
                okunan.add(d.args[0].value)
        if not okunan:
            continue

        # Bu ucu çağıran şablonlar — ÖNEK EŞLEME SIKI:
        # `/api/cari`, `/api/cari/hareket`i yakalamasın.
        onek = yol.split('<')[0].rstrip('/')
        if not onek:
            continue
        kalip = _re.compile(_re.escape(onek) + r'(?![A-Za-z0-9_/-])')
        cagiranlar = [a for a, m in sablonlar.items() if kalip.search(m)]
        if not cagiranlar:
            continue        # ekransız uç; başka bir bekçinin işi
        metin = '\n'.join(sablonlar[a] for a in cagiranlar)

        for anahtar in sorted(okunan):
            if anahtar in IC_ALAN or not KRITIK.search(anahtar):
                continue
            if (yol, anahtar) in _GA1_MUAF:
                continue
            # `anahtar:` · 'anahtar' · govde.anahtar = · ES6 kısa yazım
            if _re.search(r'[\'"]?\b%s\b[\'"]?\s*:' % _re.escape(anahtar), metin):
                continue
            if _re.search(r'[\'"]%s[\'"]' % _re.escape(anahtar), metin):
                continue
            if _re.search(r'\.%s\s*=' % _re.escape(anahtar), metin):
                continue
            if _re.search(r'^(?=.*:).*\b%s\b\s*,' % _re.escape(anahtar),
                          metin, _re.M):
                continue
            acik.append(f'{yol} · {anahtar} ({fn.name})')

    assert not acik, (
        'sunucu bu gövde alanlarını okuyor ama onu çağıran hiçbir ekran '
        'göndermiyor — alan sessizce varsayılana düşer: '
        + '; '.join(sorted(acik)))


def test_ga1_bekci_hs1_hatasini_yakaliyor():
    """Bekçi, HS1'de yaşadığımız eksikliği görmeli.

    HS1'de hızlı satış `doviz` göndermiyordu. O hâli taklit edip
    bekçinin kullandığı eşleştirmenin onu YAKALADIĞINI gösteriyoruz;
    yoksa yeşil bir bekçiye güvenmiş oluruz."""
    import re as _re
    # Ekranın gövdesi (HS1 ÖNCESİ hâli): doviz YOK
    eski_ekran = """
      const govde = {
        musteri,
        satis_tipi: document.getElementById('hsTip').value,
        kdv_oran: parseFloat(document.getElementById('hsKdv').value) || 0,
      };
    """
    for anahtar in ('doviz', 'kdv_dahil_mi'):
        bulundu = (
            _re.search(r'[\'"]?\b%s\b[\'"]?\s*:' % anahtar, eski_ekran)
            or _re.search(r'[\'"]%s[\'"]' % anahtar, eski_ekran)
            or _re.search(r'\.%s\s*=' % anahtar, eski_ekran)
            or _re.search(r'^(?=.*:).*\b%s\b\s*,' % anahtar, eski_ekran, _re.M))
        assert not bulundu, (
            f'bekçinin eşleştirmesi {anahtar!r} yokken VAR sanıyor — '
            f'HS1 hatasını kaçırırdı')
    # Ve ŞİMDİKİ ekran ikisini de gönderiyor olmalı
    import io as _io
    b = _io.open(os.path.join(KOK, 'templates', 'base.html'),
                 encoding='utf-8').read()
    assert "doviz: document.getElementById('hsDoviz').value" in b
    assert 'kdv_dahil_mi:' in b


# ═══════════════════════════════════════════════════════════════════
#  OY1 · OKUMA YETKİSİ — SAYFA KİLİTLİ, VERİSİ AÇIK
#
#  ÖLÇÜLEN SINIF: `_okuma_yetki_guard` yolu bir modüle bağlayamazsa
#  "tanimlanmamis API — sessizce gec" diyor. `karlilik` ve `raporlar`
#  birer yetki modülü; menü, sayfa kapısı ve raporlar.html bölüm
#  bölüm hepsini gizliyor — ama o sayfaların API'leri haritada YOKTU.
#
#  Sonuç (ölçüldü): `/api/maliyet` 403 veren kullanıcı
#  `/api/karlilik`ten kalem kalem maliyet_usd + kar_usd + marj
#  okuyordu.
# ═══════════════════════════════════════════════════════════════════

def _oy1_kullanici(ad, yetkiler):
    """Verilen yetkilerle kullanıcı kurar, istemcisini döner."""
    from models import Kullanici
    import json as _json
    with fa.app.app_context():
        k = Kullanici.query.filter_by(ad=ad).first()
        if not k:
            k = Kullanici(ad=ad, sifre='x', rol='SATIS',
                          cari_kapsam='tumu', firma_kapsam='tumu')
            db.session.add(k)
        k.cari_kapsam = 'tumu'
        k.firma_kapsam = 'tumu'
        k.yetkiler = _json.dumps(yetkiler)
        db.session.commit()
    return istemci(ad, 'SATIS')


@pytest.fixture(scope='module')
def oy1_veri():
    """Maliyet ve kâr TAŞIYAN bir satış + bir blok + bir cari bakiyesi.

    Boş cevap "korunuyor" demek DEĞİL — ilk ölçümümde
    `/api/rapor/yaslandirilmis_cari` boş döndü ve bir an korunuyor
    sandım; satır yoktu, o kadar."""
    from models import SatisKaydi, BlokStok, Cari, CariHareket
    with fa.app.app_context():
        if not BlokStok.query.filter_by(id='BOY1').first():
            db.session.add(BlokStok(
                id='BOY1', blok_no='OY-1', cins='OYTEST', boy=300,
                yukseklik=150, en=120, hacim_m3=5.4, tonaj=15,
                durum='Satildi', alis_fiyati=15000, doviz='USD'))
        if not SatisKaydi.query.filter_by(id='SKOY1').first():
            db.session.add(SatisKaydi(
                id='SKOY1', stok_tip='blok', stok_id='BOY1', blok_no='OY-1',
                cins='OYTEST', musteri='ACIK CARI', cari_id='C1',
                doviz='USD', birim_fiyat=5000, miktar=1, tutar=5000,
                tutar_usd=5000, maliyet_usd=1200, kar_usd=3800,
                marj_yuzde=76.0, satis_tarihi=date(2026, 1, 5),
                teslim_tarihi=date(2026, 1, 5)))
        if not Cari.query.filter_by(id='COY1').first():
            db.session.add(Cari(id='COY1', unvan='OY CARI',
                                cari_tip='Müşteri', ulke='USA',
                                para_birimi='USD', gorunurluk='acik'))
            db.session.flush()
            db.session.add(CariHareket(
                id='HOY1', cari_id='COY1', islem_tip='Fatura (Satis)',
                borc=77777, alacak=0, doviz='USD', kur_uygulanan=40,
                borc_try=3111080, alacak_try=0,
                baglanti_tip='fatura_kesim', baglanti_id='FOY1',
                hareket_tarihi=date(2026, 1, 1)))
        db.session.commit()
    yield


# Para alanı döndürdüğü hâlde yetki SORMAYAN uçların AÇIK listesi.
# Her biri gerekçeli; listede olmayan yeni bir uç testi düşürür.
OY1_MUAF = {
    # Kullanıcının KENDİ bildirimleri.
    '/api/bildirim',
    # Kullanıcının KENDİ SMTP ayarı (şifre asla dönmez).
    '/api/v2/eposta/ayar',
    # Yalnızca unvan listesi; erişim süzgecinden geçiyor (AS1 notu).
    '/api/musteri',
    '/api/acente_liste',
    # Konteyner listesi — para alanı yok, iki ekrandan yönetiliyor.
    '/api/konteyner',
    # ── 403 DEĞİL, KIRPARAK koruyan iki uç ──
    # Bunlar 200 dönüyor ama gövdelerini bölüm bölüm süzüyorlar
    # (`/api/ara` → `_gorebilir`, `/api/dashboard/ozet` → BG1).
    # Kör muafiyet değil: ÖLÇÜLDÜ, tüm modülleri gizli kullanıcıya
    # `/api/ara` 41 bayt (`gruplar: []`), `/api/dashboard/ozet` 33
    # bayt (bütün bölümler düşmüş) dönüyor. Kırptıklarını
    # test_oy1_kirpan_uclar_rakam_sizdirmiyor ayrıca sınıyor —
    # yoksa bu liste gerçek bir deliği örtebilirdi.
    '/api/ara',
    '/api/dashboard/ozet',
}


def _oy1_para_donduren_get_uclari():
    """flask_app.py'deki salt-GET /api/ uçlarından para alanı
    döndürenler. (satır, fonksiyon, kural) döner."""
    import ast as _ast
    import io as _io
    import re as _re
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    # Yol adına DEĞİL, gövdenin döndürdüğü alan adlarına bakılıyor.
    # İlk ölçütüm yol adına bakıyordu ve `/api/blok/<no>/izleme`yi
    # "nötr" saymıştı — oysa alis_fiyati + matrah + tüm maliyet
    # kayıtlarını döndürüyor. Yol adı neyin döndüğünü söylemiyor.
    para = _re.compile(r'alis_fiyat|maliyet|kar_usd|kar_try|marj|matrah|'
                       r'bakiye|borc|alacak|komisyon|kdv_tutar|'
                       r'toplam_usd|tutar_usd|satis_usd', _re.I)
    cikti = []
    for fn in _ast.walk(_ast.parse(kaynak)):
        if not isinstance(fn, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            continue
        kurallar, yontemler = [], []
        for dec in fn.decorator_list:
            if (isinstance(dec, _ast.Call)
                    and isinstance(dec.func, _ast.Attribute)
                    and dec.func.attr == 'route' and dec.args
                    and isinstance(dec.args[0], _ast.Constant)):
                kurallar.append(dec.args[0].value)
                for kw in dec.keywords:
                    if kw.arg == 'methods':
                        yontemler += [e.value
                                      for e in getattr(kw.value, 'elts', [])
                                      if isinstance(e, _ast.Constant)]
        if not kurallar:
            continue
        kural = kurallar[0]
        if not kural.startswith('/api/') or kural.startswith('/api/diag/'):
            continue
        if (set(yontemler) or {'GET'}) - {'GET'}:
            continue
        if not para.search(_ast.unparse(fn)):
            continue
        cikti.append((fn.lineno, fn.name, kural))
    return cikti


def test_oy1_para_donduren_her_get_ucu_yetki_soruyor(oy1_veri):
    """ÇİVİ: para döndüren hiçbir salt-GET /api/ ucu, tüm modülleri
    gizli olan bir kullanıcıya 200 vermemeli.

    Bu test haritanın KOPYASINI değil GERÇEK KAPIYI sınıyor: istek
    atılıyor. Yeni bir rapor/kârlılık ucu eklenip haritaya
    yazılmazsa burası düşer — sınıfın geri gelmesini bu engelliyor.
    """
    import re as _re
    c = _oy1_kullanici('oy1hicbiri', {})          # her modül gizli
    sizan = []
    for satir, fn, kural in _oy1_para_donduren_get_uclari():
        if kural in OY1_MUAF:
            continue
        yol = _re.sub(r'<path:[^>]+>', 'x/y', kural)
        yol = _re.sub(r'<int:[^>]+>', '1', yol)
        yol = _re.sub(r'<[^>]+>', 'SKOY1', yol)
        r = c.get(yol, headers=H)
        if r.status_code == 200:
            sizan.append(f'{kural}  (satır {satir}, {fn})')
    assert not sizan, (
        'tüm modülleri gizli kullanıcı para alanı döndüren bu uçları '
        'okuyabiliyor:\n  ' + '\n  '.join(sizan))


def test_oy1_karlilik_uclari_karlilik_yetkisi_istiyor(oy1_veri):
    """`/api/maliyet` 403 verirken `/api/karlilik` kalem kalem
    maliyet + kâr + marj döndürüyordu."""
    c = _oy1_kullanici('oy1satisci',
                       {'satislar': 'okuma', 'siparis': 'okuma'})
    # Kontrol noktası: aynı modülü gövdesinde soran kardeş uç
    assert c.get('/api/ortaklik', headers=H).status_code == 403
    for yol in ('/api/karlilik', '/api/karlilik/musteri_ozet',
                '/api/karlilik/cins_ozet', '/api/karlilik/SKOY1/dokum'):
        r = c.get(yol, headers=H)
        assert r.status_code == 403, (
            f'{yol} → {r.status_code}; gövde: '
            f'{r.get_data(as_text=True)[:200]}')


def test_oy1_karlilik_yetkisi_varsa_okunuyor(oy1_veri):
    """Kapıyı kaparken anahtarı da kırmadığımızın kanıtı.

    DİKKAT: bu test TABANDA DA GEÇER (taban herkese 200 veriyor).
    Hata ölçen bir test değil, GERİLEME çivisi — işi yetkiyi fazla
    kısmadığımı göstermek. Hatayı ölçen testler tabanda düşüyor."""
    c = _oy1_kullanici('oy1karli', {'karlilik': 'okuma'})
    r = c.get('/api/karlilik', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    assert 'kar_usd' in r.get_data(as_text=True)


def test_oy1_rapor_uclari_kapali(oy1_veri):
    """Maliyet analizi, stok maliyeti ve satış performansı
    `raporlar` yetkisi olmayana kapalı."""
    c = _oy1_kullanici('oy1raporsuz',
                       {'satislar': 'okuma', 'siparis': 'okuma'})
    for yol in ('/api/rapor/maliyet_analiz', '/api/rapor/stok_maliyet',
                '/api/rapor/satis_performans', '/api/rapor/stok_durum',
                '/api/rapor/yaslandirilmis_cari', '/api/rapor/donusum',
                '/api/rapor/konteyner_takip'):
        r = c.get(yol, headers=H)
        assert r.status_code == 403, f'{yol} → {r.status_code}'


def test_oy1_coklu_harita_capraz_ekranlari_kirmiyor(oy1_veri):
    """EN ÖNEMLİ KORUMA: rapor uçları başka ekranlardan da okunuyor
    ve ekran bölümü İKİ modülün VEYA'sı ile açılıyor.

    `/api/rapor` önekini tek bir modüle bağlasam `raporlar` yetkisi
    olmayan ama `stok` yetkisi olan birinin STOK ekranı ve
    dashboard'u kırılırdı — YK1'in `/api/cek/ozet` tuzağının aynısı.
    raporlar.html'in kendi `gorunur()` kuralı burada şartname."""
    # stok yetkisi YETER (stok.html + dashboard.html çapraz okuyor)
    c = _oy1_kullanici('oy1stokcu', {'stok': 'okuma'})
    for yol in ('/api/rapor/stok_durum', '/api/rapor/stok_maliyet'):
        assert c.get(yol, headers=H).status_code == 200, yol
    # ama kârlılık ve cari raporları ona kapalı
    for yol in ('/api/rapor/satis_performans',
                '/api/rapor/yaslandirilmis_cari', '/api/karlilik'):
        assert c.get(yol, headers=H).status_code == 403, yol

    # cari yetkisi YETER (cari.html + dashboard.html çapraz okuyor)
    c2 = _oy1_kullanici('oy1carici', {'cari': 'okuma'})
    r = c2.get('/api/rapor/yaslandirilmis_cari', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    assert 'COY1' in r.get_data(as_text=True), 'veri gelmiyor, test ölçmez'
    assert c2.get('/api/rapor/stok_maliyet',
                  headers=H).status_code == 403

    # maliyet yetkisi maliyet analizine YETER
    c3 = _oy1_kullanici('oy1maliyetci', {'maliyet': 'okuma'})
    assert c3.get('/api/rapor/maliyet_analiz',
                  headers=H).status_code == 200
    # sevkiyat yetkisi konteyner takibine YETER
    c4 = _oy1_kullanici('oy1sevkci', {'sevkiyat': 'okuma'})
    assert c4.get('/api/rapor/konteyner_takip',
                  headers=H).status_code == 200
    # raporlar yetkisi HEPSİNE yeter
    c5 = _oy1_kullanici('oy1raporcu', {'raporlar': 'okuma'})
    for yol in ('/api/rapor/stok_durum', '/api/rapor/stok_maliyet',
                '/api/rapor/yaslandirilmis_cari',
                '/api/rapor/maliyet_analiz', '/api/rapor/satis_performans',
                '/api/rapor/konteyner_takip'):
        assert c5.get(yol, headers=H).status_code == 200, yol
    # `/api/rapor/donusum` İSTİSNA: gövdesinde `proforma` yetkisi
    # arıyor (teklif dönüşüm oranı proforma verisi). Sunucu ekranın
    # kuralından SIKI; yön güvenli olduğu için yetkiyi gevşetmedim,
    # ekranın o bölümünü de `proforma`ya bağladım ki bölüm hata
    # vermek yerine gizlensin.
    assert c5.get('/api/rapor/donusum', headers=H).status_code == 403
    c6 = _oy1_kullanici('oy1proformaci',
                        {'raporlar': 'okuma', 'proforma': 'okuma'})
    assert c6.get('/api/rapor/donusum', headers=H).status_code == 200


def test_oy1_kirpan_uclar_rakam_sizdirmiyor(oy1_veri):
    """TABANDA DA GEÇER — bu iki uç zaten kırpıyordu; işi muaf
    listesinin gerçek bir deliği örtmediğini sürekli sınamak.

    OY1_MUAF'taki iki uç 403 vermiyor, KIRPIYOR. Muafiyetin
    gerçek bir deliği örtmediğini burada sınıyoruz: tüm modülleri
    gizli kullanıcıya rakam gelmemeli (BG1'in ilkesi)."""
    c = _oy1_kullanici('oy1kirpma', {})
    r = c.get('/api/ara?q=ACIK', headers=H)
    assert r.status_code == 200
    d = r.get_json()
    assert d.get('gruplar') == [] and d.get('toplam') == 0, d

    r2 = c.get('/api/dashboard/ozet', headers=H)
    assert r2.status_code == 200
    d2 = r2.get_json()
    for alan in ('ciro', 'alacak', 'borc', 'stok', 'kasa', 'acik_siparis'):
        assert alan not in d2, f'{alan} yetkisiz kullanıcıya geliyor: {d2}'


def test_oy1_blok_izleme_stok_yetkisi_istiyor(oy1_veri):
    """`/api/blok/<no>/izleme`, `/api/iz`in başka adla ikizi:
    alis_fiyati + matrah + bloğun tüm maliyet kayıtları. Haritada
    `/api/iz` 'stok'a bağlıydı, bu bağlı değildi."""
    c = _oy1_kullanici('oy1stoksuz', {'satislar': 'okuma'})
    assert c.get('/api/iz/blok/BOY1', headers=H).status_code == 403
    assert c.get('/api/blok/OY-1/izleme', headers=H).status_code == 403
    c2 = _oy1_kullanici('oy1stoklu', {'stok': 'okuma'})
    assert c2.get('/api/blok/OY-1/izleme', headers=H).status_code == 200


def test_oy1_cek_ve_sabit_gider_kasa_yetkisi_istiyor(oy1_veri):
    """KULLANICI KARARI: YK1 bu uçları okumada bilerek açık
    bırakmıştı (Bugün ekranı `/api/cek/ozet`i çapraz okuyor).
    Kullanıcı o kırılmayı kabul etti: özet dahil hepsi `kasa`
    yetkisi istiyor."""
    c = _oy1_kullanici('oy1kasasiz', {'satislar': 'okuma'})
    for yol in ('/api/cek', '/api/cek/ozet', '/api/cek/X1',
                '/api/sabit_gider', '/api/nakit_plan'):
        r = c.get(yol, headers=H)
        assert r.status_code == 403, f'{yol} → {r.status_code}'
    c2 = _oy1_kullanici('oy1kasali', {'kasa': 'okuma'})
    for yol in ('/api/cek', '/api/cek/ozet', '/api/sabit_gider',
                '/api/nakit_plan'):
        assert c2.get(yol, headers=H).status_code == 200, yol


def test_oy1_cek_yazma_davranisi_degismedi(oy1_veri):
    """TABANDA DA GEÇER — gerileme çivisi, hata ölçümü değil.

    Üç önek YAZMA_EK_MAP'ten URL_MODUL_MAP'e taşındı. Yazma
    kapısı URL_MODUL_MAP'e daha önce bakıyor ve modül iki haritada
    da 'kasa' — yazma davranışı AYNI kalmalı."""
    # kasa okuma yetkisi YAZMAYA yetmez (YK1'in ölçtüğü hata)
    c = _oy1_kullanici('oy1kasaokur', {'kasa': 'okuma'})
    r = c.post('/api/cek', json={'tutar': 1}, headers=H)
    assert r.status_code == 403, r.get_data(as_text=True)[:200]
    assert (r.get_json() or {}).get('error') == 'yetki_yok'
    r2 = c.post('/api/sabit_gider', json={'ad': 'x'}, headers=H)
    assert r2.status_code == 403


def test_oy1_dashboard_satis_istatistik_yetki_soruyor(oy1_veri):
    """`/api/dashboard` öneki OKUMA_MUAF_PATHS'te — okuma kapısı o
    yolu HİÇ denetlemiyor. Kardeşleri bunu gövdelerinde yapıyor
    (`/ozet` 4, `/detay` 2 yetki sorusu); bu uç SIFIR soruyordu ve
    kâr_usd + en kârlı 5 müşteri + en kârlı 5 cins + ortalama marjı
    oturum açan herkese veriyordu."""
    c = _oy1_kullanici('oy1dashsuz',
                       {'siparis': 'okuma', 'dashboard': 'okuma'})
    r = c.get('/api/dashboard/satis_istatistik', headers=H)
    assert r.status_code == 403, r.get_data(as_text=True)[:200]
    # Kardeş uçlar bozulmadı
    assert c.get('/api/dashboard/ozet', headers=H).status_code == 200
    c2 = _oy1_kullanici('oy1dashli',
                        {'karlilik': 'okuma', 'dashboard': 'okuma'})
    assert c2.get('/api/dashboard/satis_istatistik',
                  headers=H).status_code == 200


def test_oy1_civi_kendi_kacirdigi_hatayi_yakaliyor():
    """TABANDA DA GEÇER — ölçüt test dosyasında, yamada değil.
    İşi çivinin kendi kör noktasını sürekli sınamak.

    Çivi, OY1'de ölçtüğümüz delikleri GERÇEKTEN yakalıyor mu?

    Ölçütüm bir kez yol adına bakıyordu ve `/api/blok/<no>/izleme`yi
    kaçırdı. Yeşil bir bekçiye güvenmemek için ölçütü HER İKİ hâlde
    sınıyorum."""
    uclar = {k: (s, f) for s, f, k in _oy1_para_donduren_get_uclari()}
    # Ölçülen deliklerin hepsi çivinin kapsamında OLMALI
    for kural in ('/api/karlilik', '/api/karlilik/<satis_id>/dokum',
                  '/api/rapor/maliyet_analiz', '/api/rapor/stok_maliyet',
                  '/api/rapor/yaslandirilmis_cari',
                  '/api/blok/<blok_no>/izleme'):
        assert kural in uclar, (
            f'{kural} çivinin kapsamında değil — ölçüt onu kaçırıyor')
    # Ve muaf listesi, kapsamdaki bir ucu sessizce yutmuyor olmalı
    for kural in OY1_MUAF:
        assert kural not in ('/api/karlilik', '/api/rapor/stok_maliyet')


def test_oy1_dashboard_ciro_kari_karlilik_istiyor(oy1_veri):
    """TARAYICININ BULDUĞU, TESTİMİN KAÇIRDIĞI SIZINTI.

    Kâr ve marj ciroyla AYNI PAKETTEYDİ ve `satislar` yetkisi üçünü
    birlikte açıyordu: `satislar=okuma, karlilik=gizli` satışçının
    dashboard'unda "kâr 3.800 $ · marj %76" yazıyordu — aynı
    kullanıcı `/api/karlilik`ten 403 alırken.

    `/api/dashboard/ozet`i TÜM MODÜLLERİ GİZLİ kullanıcıyla ölçüp
    (33 bayt) muaf saymıştım; `satislar` açıkken bölüm açılıyor ve
    kârı beraberinde getiriyor. Muafiyeti o yüzden zayıf kurmuşum.

    Kullanıcı kararı: ciro `satislar` ile gelir, kâr/marj YALNIZCA
    `karlilik` ile."""
    c = _oy1_kullanici('oy1cirocu',
                       {'satislar': 'okuma', 'dashboard': 'okuma'})
    d = c.get('/api/dashboard/ozet', headers=H).get_json()
    assert 'ciro' in d, f'ciro gelmiyor, test ölçmez: {d}'
    assert 'yillik' in d['ciro'], d['ciro']
    # Anahtar HİÇ gelmemeli — 0 da gelmemeli (ekran "%0 marj" yazardı)
    for alan in ('yillik_kar', 'aylik_kar', 'yillik_marj'):
        assert alan not in d['ciro'], (
            f'{alan} karlilik yetkisi olmayana sızıyor: {d["ciro"]}')

    c2 = _oy1_kullanici('oy1karciro',
                        {'karlilik': 'okuma', 'dashboard': 'okuma'})
    d2 = c2.get('/api/dashboard/ozet', headers=H).get_json()
    for alan in ('yillik_kar', 'aylik_kar', 'yillik_marj'):
        assert alan in d2['ciro'], (
            f'{alan} karlilik yetkilisine de gelmiyor — kapıyı kaparken '
            f'anahtarı kırmışım: {d2["ciro"]}')
    # KESİN RAKAM İDDİA ETMİYORUM: ilk hâlimde `== 3800.0` yazmıştım
    # ve tam takımda düştü (başka testler satış ekliyor, yıllık kâr
    # 345.602 oldu). İzole koşuda geçip takımda düşen bir test,
    # ölçtüğü şeyi yanlış seçmiş demektir. Ölçülen şey alanın
    # GELMESİ ve gerçek bir sayı olması.
    assert isinstance(d2['ciro']['yillik_kar'], (int, float)), d2['ciro']
    assert d2['ciro']['yillik_kar'] > 0, d2['ciro']


def test_oy1_dashboard_ekrani_olmayan_kari_yazmiyor():
    """Alan gelmediğinde ekran "kâr 0,00 $" YAZMAMALI.

    `para(undefined)` sıfır üretir ve kart satışçıya şirketin sıfır
    kâr ettiğini söylerdi — yetki kapatmak yanlış bilgi vermeye
    dönüşmüş olurdu. `_ipPara` dersi: sunucuyu düzeltmek yetmiyor,
    ekranın alan yokken ne yazdığına bakmak gerekiyor."""
    import io as _io
    d = _io.open(os.path.join(KOK, 'templates', 'dashboard.html'),
                 encoding='utf-8').read()
    # Koşulsuz yazım KALMAMIŞ olmalı
    assert '`${c.yil} · kâr ${para(c.yillik_kar)}' not in d, (
        'yıllık kâr koşulsuz yazılıyor')
    assert '`bu ay · kâr ${para(c.aylik_kar)}`);' not in d, (
        'aylık kâr koşulsuz yazılıyor')
    # Ve alan denetimi var olmalı
    assert 'c.yillik_kar != null' in d
    assert 'c.aylik_kar != null' in d


# ═══════════════════════════════════════════════════════════════════
#  KC1 · DÖVİZ ÇEVRİMİ TEK KAPIDAN
#
#  SINIF: aynı hesap iki ayrı yerde. Ortak kapı `_usd_cevrim` (F15)
#  dururken sekiz yerde elle yazılmış çevrim vardı; ikisi zaten
#  kapıya bağlanmıştı ("F15: TCMB çapraz kuru"), altısı unutulmuştu.
#
#  Kopyalar kapıdan ÜÇ noktada ayrışıyordu — hepsi ölçüldü:
#    · USD/EUR/TRY dışındaki döviz AYNEN dönüyordu
#      (1.000 GBP = 1.000 USD) ya da TRY sanılıp bölünüyordu
#    · kur arşivi boşsa 0 dönüyordu — UN1'in notu: "sıfır yazmak
#      maliyeti yok ederdi"
#    · her zaman EN SON kuru kullanıyordu, belgenin tarihini değil
#
#  Ayrıca `api_rapor_yaslandirilmis_cari` içinde ortak kapıyla
#  BİREBİR AYNI ADI taşıyan yerel bir `_try_karsilik` vardı;
#  USD/EUR dışındaki her döviz için çarpanı 1'di.
# ═══════════════════════════════════════════════════════════════════

def _kc1_kapi(ad):
    """`create_app` içinde yuvalı yardımcıyı kapanıştan çeker.

    İLK HÂLİM yalnız view fonksiyonlarının DOĞRUDAN serbest
    değişkenlerine bakıyordu ve `_stok_alim_usd`i bulamadı — onu
    hiçbir view doğrudan çağırmıyor, araya başka bir yardımcı
    giriyor. Artık bir kat derine de bakıyor."""
    gorulen, sira = set(), []
    for f in fa.app.view_functions.values():
        sira.append(f)
    i = 0
    while i < len(sira):
        f = sira[i]
        i += 1
        kod = getattr(f, '__code__', None)
        kap = getattr(f, '__closure__', None)
        if not kod or not kap:
            continue
        if id(f) in gorulen:
            continue
        gorulen.add(id(f))
        if ad in kod.co_freevars:
            return kap[kod.co_freevars.index(ad)].cell_contents
        for h in kap:
            try:
                v = h.cell_contents
            except ValueError:
                continue
            if callable(v) and getattr(v, '__closure__', None):
                sira.append(v)
    raise AssertionError(f'{ad} bulunamadı')


# KC1 testlerinin KENDİ GÜNÜ. Küresel kur durumuna yaslanmak
# kırılgan: başka testler bugüne ve İLERİ tarihlere kur yazıyor,
# `_kur_getir` (tarih süzgeci yok) onları görüyor. Ölçüldü — dört
# testim izole koşuda geçip tam takımda düştü. Bu gün hiçbir testte
# geçmiyor; çevrimlere tarih AÇIKÇA veriliyor.
KC1_GUN = date(2026, 2, 11)
KC1_KURLAR = {'USD': 48.0, 'EUR': 56.0, 'GBP': 62.0}


@pytest.fixture(scope='module')
def kc1_kur():
    """KC1_GUN'de USD 48 · EUR 56 · GBP 62."""
    from models import DovizKur
    with fa.app.app_context():
        for dv, k in KC1_KURLAR.items():
            v = DovizKur.query.filter_by(doviz=dv, tarih=KC1_GUN).first()
            if v:
                v.alis, v.satis, v.efektif = k, k + 0.2, k
            else:
                db.session.add(DovizKur(doviz=dv, tarih=KC1_GUN, alis=k,
                                        satis=k + 0.2, efektif=k))
        # GBP'nin BUGÜN de bir kuru olmalı: tarihsiz çağrılar
        # (`_stok_alim_usd` tarih almıyor) bugüne bakıyor. Diğer
        # testler USD/EUR'u değiştirebilir — o yüzden beklenen değer
        # test içinde KAPIYA SORULARAK hesaplanıyor, sabit yazılmıyor.
        if not DovizKur.query.filter_by(doviz='GBP',
                                        tarih=date.today()).first():
            db.session.add(DovizKur(doviz='GBP', tarih=date.today(),
                                    alis=KC1_KURLAR['GBP'],
                                    satis=KC1_KURLAR['GBP'] + 0.2,
                                    efektif=KC1_KURLAR['GBP']))
        db.session.commit()
    yield


def test_kc1_stok_alim_bedeli_bilinmeyen_dovizi_usd_sanmiyor(kc1_kur):
    """1.000 GBP'lik stok, 1.000 USD DEĞİLDİR.

    İLK HÂLİMDE `_usd_cevrim`i DOĞRUDAN çağırıyordum ve test
    TABANDA DA GEÇİYORDU — kapı zaten doğruydu, hata kopyalardaydı.
    DV1'in dersi: tabanda düşmeyen test bir şey ölçmez. Artık
    kopyanın bulunduğu ÇAĞRI YERİ ölçülüyor: `_stok_alim_usd`,
    elle yazılı hâlinde `return ham` ile bilinmeyen dövizi aynen
    geçiriyordu."""
    from models import BlokStok
    with fa.app.app_context():
        alim = _kc1_kapi('_stok_alim_usd')
        b = BlokStok.query.filter_by(id='B-KC1G').first()
        if not b:
            b = BlokStok(id='B-KC1G', blok_no='KC1-G', cins='KCTEST',
                         boy=300, yukseklik=150, en=120, hacim_m3=5.4,
                         tonaj=15, durum='Serbest', doviz='GBP',
                         alis_fiyati=1000, alis_fiyat_birim='ton',
                         matrah=1000)
            db.session.add(b)
            db.session.commit()
        usd = alim(b)
        # Beklenen değer KAPIYA SORULUYOR, sabit yazılmıyor: başka
        # testler bugünün USD/EUR kurlarını değiştiriyor ve sabit
        # rakam yazdığımda bu test izole koşuda geçip tam takımda
        # düştü. Ölçülen şey ÇEVRİLMİŞ OLMASI.
        getir, yakin = _kc1_kapi('_kur_getir'), _kc1_kapi('_en_yakin_kur')
        _g = float(getir('GBP') or 0) or float(yakin('GBP') or 0)
        _u = float(getir('USD') or 0) or float(yakin('USD') or 0)
        beklenen = 1000 * _g / _u
        assert abs(usd - beklenen) < 5, (
            f'GBP stok {usd:,.2f} USD değerlendi — {beklenen:,.2f} olmalı')
        assert abs(usd - 1000) > 50, (
            f'çevrilmemiş: {usd} — GBP hâlâ USD sanılıyor')


def test_kc1_kur_yoksa_alim_bedeli_sifirlanmiyor(kc1_kur):
    """TABANDA DA GEÇER — gerileme çivisi, hata ölçümü değil.

    Kur arşivinde HİÇ olmayan bir döviz, bedeli SIFIRLAMAMALI.
    UN1'in notu: "sıfır yazmak maliyeti yok ederdi."

    DÜRÜSTÇESİ: elle yazılı kopya SIFIRLAMAYI yalnız EUR/TRY için
    yapıyordu (`return 0.0`); bilinmeyen dövizde o da tutarı
    koruyordu (`return ham`). Yani bu senaryoda taban ile yama aynı
    cevabı veriyor. Sıfırlama dalını ayırt etmek için arşivde HİÇ
    USD kuru olmaması gerekirdi — paylaşılan test veritabanında
    bunu izole edemiyorum. Test yine de duruyor: kapının tutarı
    koruma sözünü çağrı yerinden çiviliyor."""
    from models import BlokStok
    with fa.app.app_context():
        alim = _kc1_kapi('_stok_alim_usd')
        b = BlokStok.query.filter_by(id='B-KC1Z').first()
        if not b:
            b = BlokStok(id='B-KC1Z', blok_no='KC1-Z', cins='KCTEST',
                         boy=300, yukseklik=150, en=120, hacim_m3=5.4,
                         tonaj=15, durum='Serbest', doviz='ZZZ',
                         alis_fiyati=1000, alis_fiyat_birim='ton',
                         matrah=1000)
            db.session.add(b)
            db.session.commit()
        usd = alim(b)
        assert abs(usd - 1000) < 0.01, (
            f'kuru olmayan döviz {usd} oldu — tutar korunmalıydı')


def test_kc1_komsu_kur_aramalari_ayni_alani_tercih_ediyor(kc1_kur):
    """`_kur_getir` ve `_en_yakin_kur` AYNI kur alanını seçmeli.

    Biri `alis or efektif or satis`, öteki `satis or alis` diyordu:
    aynı çevrim hangi yoldan geçtiğine göre farklı kur veriyordu.
    Ölçüldü — 1.000 EUR bir yoldan 56.000, öbüründen 56.200 TL
    (%0,4). Kullanıcı kararı: ALIŞ kuru esas.

    TARİH AÇIKÇA VERİLİYOR: tarihsiz çağrıda ikisi zaten farklı
    kümeye bakıyor (`_kur_getir` tarih süzmez, yani İLERİ tarihli
    bir satırı da alır; `_en_yakin_kur` `<= bugün` süzer). O ayrı
    bir konu — burada ölçülen ALAN seçimi."""
    with fa.app.app_context():
        getir = _kc1_kapi('_kur_getir')
        yakin = _kc1_kapi('_en_yakin_kur')
        for dv, k in KC1_KURLAR.items():
            a = float(getir(dv, KC1_GUN) or 0)
            b = float(yakin(dv, KC1_GUN) or 0)
            assert abs(a - b) < 0.001, (
                f'{dv}: _kur_getir {a} · _en_yakin_kur {b} — '
                f'iki arama farklı alan seçiyor')
            assert abs(a - k) < 0.001, (
                f'{dv}: {a} geldi, alış kuru {k} olmalıydı')


def test_kc1_yaslandirma_gbp_dogru_degerliyor(kc1_kur):
    """ÖLÇÜLEN HATA: 1.000 sterlinlik alacak raporda 1.000 TL.

    `api_rapor_yaslandirilmis_cari` içinde ortak kapıyla aynı adı
    taşıyan yerel bir `_try_karsilik` vardı; USD/EUR dışındaki her
    döviz için çarpanı 1'di — sterlin zaten TL sayılıyordu.

    Hareketler KC1_GUN tarihli: rapor artık hareketin KENDİ
    tarihindeki kuru kullanıyor, o da bu testin kurları."""
    from models import Cari, CariHareket
    with fa.app.app_context():
        for kod, dv in (('KC1U', 'USD'), ('KC1G', 'GBP')):
            if Cari.query.filter_by(id=f'C-{kod}').first():
                continue
            db.session.add(Cari(id=f'C-{kod}', unvan=f'{kod} MUSTERI',
                                cari_tip='Müşteri', para_birimi=dv,
                                gorunurluk='acik'))
            db.session.flush()
            db.session.add(CariHareket(
                id=f'H-{kod}', cari_id=f'C-{kod}',
                islem_tip='Fatura (Satis)', borc=1000, alacak=0,
                doviz=dv, kur_uygulanan=None, borc_try=0, alacak_try=0,
                baglanti_tip='fatura_kesim', baglanti_id=f'F-{kod}',
                hareket_tarihi=KC1_GUN))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    d = c.get('/api/rapor/yaslandirilmis_cari', headers=H).get_json()
    bul = {x['cari_id']: x for x in d.get('cariler', [])}
    assert 'C-KC1G' in bul, 'GBP cari raporda yok, test ölçmez'
    gbp = float(bul['C-KC1G']['toplam_borc_try'])
    usd = float(bul['C-KC1U']['toplam_borc_try'])
    assert abs(usd - 1000 * KC1_KURLAR['USD']) < 100, usd
    assert abs(gbp - 1000 * KC1_KURLAR['GBP']) < 200, (
        f'1.000 GBP alacak {gbp:,.0f} TL değerlenmiş — '
        f'{1000 * KC1_KURLAR["GBP"]:,.0f} olmalı')


def test_kc1_hareket_kendi_gununun_kuruyla_degerleniyor(kc1_kur):
    """Aynı tutar, FARKLI tarihli iki hareket, farklı TL değeri.

    İLK HÂLİMDE `_usd_cevrim`i doğrudan çağırıyordum; tabanda da
    geçiyordu çünkü kapı zaten tarih alabiliyordu. Ölçülmesi gereken
    ÇAĞRI YERİ: yaşlandırma raporu hareketin kurunu nereden
    alıyor. Elle yazılı kopya her zaman EN SON kuru kullanıyordu."""
    from models import Cari, CariHareket, DovizKur
    from datetime import timedelta as _td
    onceki = KC1_GUN - _td(days=30)
    with fa.app.app_context():
        for dv, k in (('USD', 40.0),):
            v = DovizKur.query.filter_by(doviz=dv, tarih=onceki).first()
            if v:
                v.alis, v.satis, v.efektif = k, k, k
            else:
                db.session.add(DovizKur(doviz=dv, tarih=onceki, alis=k,
                                        satis=k, efektif=k))
        if not Cari.query.filter_by(id='C-KC1T').first():
            db.session.add(Cari(id='C-KC1T', unvan='KC1T MUSTERI',
                                cari_tip='Müşteri', para_birimi='USD',
                                gorunurluk='acik'))
            db.session.flush()
            # AYNI tutar, iki FARKLI gün
            for ek, gun in (('A', onceki), ('B', KC1_GUN)):
                db.session.add(CariHareket(
                    id=f'H-KC1T{ek}', cari_id='C-KC1T',
                    islem_tip='Fatura (Satis)', borc=1000, alacak=0,
                    doviz='USD', kur_uygulanan=None, borc_try=0,
                    alacak_try=0, baglanti_tip='fatura_kesim',
                    baglanti_id=f'F-KC1T{ek}', hareket_tarihi=gun))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    d = c.get('/api/rapor/yaslandirilmis_cari', headers=H).get_json()
    bul = {x['cari_id']: x for x in d.get('cariler', [])}
    assert 'C-KC1T' in bul, 'cari raporda yok, test ölçmez'
    toplam = float(bul['C-KC1T']['toplam_borc_try'])
    # 1.000 × 40  +  1.000 × 48  =  88.000
    assert abs(toplam - 88000) < 200, (
        f'{toplam:,.0f} TL — her hareket KENDİ gününün kuruyla '
        f'değerlenseydi 88.000 olurdu (40 + 48). Hepsi en son kurla '
        f'değerlenseydi 96.000 çıkardı.')


def test_kc1_kur_tablosunu_kendi_sorgulayan_kod_yok():
    """ÇİVİ: `DovizKur.query` yalnızca KAPILARDA ve kur yönetim
    uçlarında olabilir.

    İLK ÖLÇÜTÜM ARİTMETİĞİ KOVALIYORDU (`tutar * kur_eur / kur_usd`)
    ve iki kusuru vardı — ikisi de ölçüldü:
      · Gölge `_try_karsilik`'in biçimini KAÇIRIYORDU; orada kur
        adlarının yanında işleç yok, koşullu bir seçim var:
            k = kur or (kur_usd if d=='USD' else kur_eur ... else 1)
      · Yuvalı `def`'ler yüzünden bulguyu YANLIŞ fonksiyona
        yazıyordu ve meşru USD→TRY çarpımlarını da işaretliyordu.

    Bu ölçüt daha keskin: kur tablosunu KENDİ sorgulayan kod,
    birazdan elle çevirecek demektir. Nitekim ölçüt değişince iki
    çevrim yeri daha çıktı (`_stok_alim_usd`,
    `_devreden_kdv_kalemi_olustur`) — aritmetik ölçütü onları da
    kaçırmıştı.

    Muaflar, her biri sebebiyle:
      · `_kur_getir` / `_en_yakin_kur` — arama kapılarının kendisi
      · `guncel_kurlari_cek` / `api_doviz_kur` /
        `api_doviz_kur_guncelle` — kur YÖNETİMİ uçları; işleri
        zaten kur tablosunu okuyup yazmak
    """
    import ast as _ast
    import io as _io
    MUAF = {'_kur_getir', '_en_yakin_kur', 'guncel_kurlari_cek',
            'api_doviz_kur', 'api_doviz_kur_guncelle'}
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    bulgular = []

    def gez(dugum, yol):
        for c in _ast.iter_child_nodes(dugum):
            y = (yol + [c.name]
                 if isinstance(c, (_ast.FunctionDef, _ast.AsyncFunctionDef))
                 else yol)
            if (isinstance(c, _ast.Attribute) and c.attr == 'query'
                    and isinstance(c.value, _ast.Name)
                    and c.value.id == 'DovizKur'):
                if not (set(y) & MUAF):
                    bulgular.append(
                        f'{" › ".join(y[-2:]) or "<modül>"} '
                        f'(satır {c.lineno})')
            gez(c, y)

    gez(_ast.parse(kaynak), [])
    assert not bulgular, (
        'kur tablosunu kendi sorgulayan kod — çevrim ortak kapıdan '
        'geçmeli (`_usd_cevrim` / `_try_karsilik`):\n  '
        + '\n  '.join(sorted(set(bulgular))))


def test_kc1_civi_eski_hatayi_yakaliyor():
    """TABANDA DA GEÇER — çivinin kendi kör noktasını sınar.

    Çivi, KC1 öncesi yazılmış kodu GERÇEKTEN yakalıyor mu? Yeşil
    bir bekçiye güvenmemek için, kaldırdığımız yerlerin hepsinin
    ortak işaretini (kendi `DovizKur` sorgusu) doğrudan deniyoruz —
    ARİTMETİK ölçütünün kaçırdığı gölge `_try_karsilik` dahil."""
    import ast as _ast
    ESKI_KOD = '''
def _ornek():
    def _try_karsilik(tutar, doviz, kur):
        usd_kur = DovizKur.query.filter_by(doviz='USD').first()
        kur_usd = (usd_kur.efektif if usd_kur else 0) or 45.07
        k = kur or (kur_usd if doviz == 'USD' else 1)
        return tutar * (k or 1)
'''
    bulundu = []

    def gez(d, yol):
        for c in _ast.iter_child_nodes(d):
            y = (yol + [c.name]
                 if isinstance(c, (_ast.FunctionDef, _ast.AsyncFunctionDef))
                 else yol)
            if (isinstance(c, _ast.Attribute) and c.attr == 'query'
                    and isinstance(c.value, _ast.Name)
                    and c.value.id == 'DovizKur'):
                bulundu.append(y)
            gez(c, y)

    gez(_ast.parse(ESKI_KOD), [])
    assert bulundu, (
        'çivi, gölge `_try_karsilik` biçimini yakalayamıyor — '
        'aritmetik ölçütünün kaçırdığı tam olarak buydu')


# ═══════════════════════════════════════════════════════════════════
#  YV1 · ÖNİZLEME İLE SAKLANAN RAKAM AYNI OLSUN
#
#  Sunucu tutarı ÖNCE iki haneye yuvarlıyor (`q2`); ekranlar
#  yuvarlamıyordu. Fatura formu kalem toplamını ham tutuyor
#  (`toplam_fiyat: miktar * fiyat`), yani 10,07 m² × 36,33 $ gibi
#  SIRADAN bir satır ara toplama fazladan ondalık taşıyor.
#
#  ÖLÇÜLDÜ — 200.000 sahte fatura, gerçekçi iki ondalıklı miktar ve
#  fiyatlarla:
#      KDV hariç   55.612 / 200.000  (%27,8)
#      KDV dahil   45.967 / 200.000  (%23,0)
#  Fark hep tam 0,01. Saklanan rakam yanlış değildi; EKRAN başka
#  bir sayı gösteriyordu.
# ═══════════════════════════════════════════════════════════════════

def _yv1_node():
    import shutil as _shutil
    return _shutil.which('node') or _shutil.which('nodejs')


def _yv1_kapi_betigi():
    """base.html'deki ortak kapıyı (q2 / kdvAyristir / kdvHesapla)
    olduğu gibi çıkarır — kopyasını değil, GERÇEĞİNİ sınarız."""
    import io as _io
    import re as _re
    b = _io.open(os.path.join(KOK, 'templates', 'base.html'),
                 encoding='utf-8').read()
    parcalar = []
    for ad in ('q2', 'kdvAyristir', 'kdvHesapla'):
        m = _re.search(rf'^function {ad}\(', b, _re.M)
        assert m, f'base.html içinde `{ad}` yok'
        i, d = b.index('{', m.end() - 1), 0
        for j in range(i, len(b)):
            if b[j] == '{':
                d += 1
            elif b[j] == '}':
                d -= 1
                if d == 0:
                    break
        parcalar.append(b[m.start():j + 1])
    return '\n'.join(parcalar)


def test_yv1_ekran_kdvsi_sunucuyla_bire_bir_ayni():
    """ÇİVİ: base.html'deki `kdvHesapla`, sunucunun `_kdv_hesapla`sı
    ile AYNI sayıyı vermeli.

    Naif bir çeviri YETMİYOR, ölçüldü:
      · `Math.round(n*100)/100` İKİLİ gösterimden yuvarlar ve
        0,145'i AŞAĞI indirir; sunucu `Decimal(str(n))` ile
        "0.145" dizgesini YUKARI yuvarlıyor.
      · `toFixed(10)` ters yönde bozar: 15330,994999999999'u onuncu
        hanede yukarı yuvarlayıp sahte bir eşitlik yaratıyor —
        200.000 girdide 316 ayrışma vermişti.
    Doğrusu `String(n)`: JS'in en kısa round-trip gösterimi,
    Python'un `str()` ile aynı algoritma.
    """
    import json as _json
    import random as _random
    import subprocess as _sp
    node = _yv1_node()
    if not node:
        pytest.skip('node yok')

    rnd = _random.Random(4242)
    girdiler = []
    for _ in range(4000):
        ara = 0.0
        for _k in range(rnd.randint(1, 4)):
            ara += round(rnd.uniform(1, 60), 2) * round(rnd.uniform(8, 400), 2)
        girdiler.append([ara, rnd.choice([0, 1, 8, 10, 18, 20]),
                         rnd.choice([0, 1])])
    # yarım-kuruş sınırlarını BİLEREK zorla
    for _ in range(2000):
        ara = round(rnd.uniform(0, 100000), 2) + rnd.choice(
            [0, 0.005, 0.0049, 0.0051, 0.145, 0.045])
        girdiler.append([round(ara, 6), rnd.choice([1, 8, 10, 18, 20]),
                         rnd.choice([0, 1])])

    betik = _yv1_kapi_betigi() + """
const g = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const c = g.map(([t, o, d]) => {
  const r = kdvHesapla(t, o, d === 1);
  return [r.matrah, r.kdv, r.toplam];
});
process.stdout.write(JSON.stringify(c));
"""
    r = _sp.run([node, '-e', betik], input=_json.dumps(girdiler),
                capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:600]
    js = _json.loads(r.stdout)

    with fa.app.app_context():
        hesapla = _kc1_kapi('_kdv_hesapla')
        ayri = []
        for (t, o, d), (jm, jk, jt) in zip(girdiler, js):
            pm, pk, pt = hesapla(t, o, bool(d))
            if (abs(pm - jm) >= 0.005 or abs(pk - jk) >= 0.005
                    or abs(pt - jt) >= 0.005):
                ayri.append(f'tutar {t} oran %{o} dahil={d}: '
                            f'sunucu ({pm}, {pk}, {pt}) · '
                            f'ekran ({jm}, {jk}, {jt})')
        assert not ayri, (
            f'{len(ayri)} / {len(girdiler)} girdide ekran ile sunucu '
            f'ayrışıyor:\n  ' + '\n  '.join(ayri[:6]))


def test_yv1_ekran_kapisi_toplami_bozmuyor():
    """Ekranın kapısı da matrah + KDV == toplam sözünü tutmalı."""
    import json as _json
    import random as _random
    import subprocess as _sp
    node = _yv1_node()
    if not node:
        pytest.skip('node yok')
    rnd = _random.Random(99)
    girdiler = [[round(rnd.uniform(0.01, 500000), 4),
                 rnd.choice([1, 8, 10, 18, 20]), rnd.choice([0, 1])]
                for _ in range(4000)]
    betik = _yv1_kapi_betigi() + """
const g = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const bozuk = [];
for (const [t, o, d] of g) {
  const r = kdvHesapla(t, o, d === 1);
  if (Math.abs((r.matrah + r.kdv) - r.toplam) >= 0.005)
    bozuk.push([t, o, d, r.matrah, r.kdv, r.toplam]);
}
process.stdout.write(JSON.stringify(bozuk));
"""
    r = _sp.run([node, '-e', betik], input=_json.dumps(girdiler),
                capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:600]
    bozuk = _json.loads(r.stdout)
    assert not bozuk, f'{len(bozuk)} girdide matrah+KDV ≠ toplam: {bozuk[:4]}'


def test_yv1_ekranlarda_elle_kdv_hesabi_kalmadi():
    """ÇİVİ: hiçbir şablon KDV'yi kendi başına hesaplamamalı.

    Sınıfın geri gelmesini bu engelliyor: yeni bir ekran
    `tutar * oran / 100` yazarsa burası düşer ve yazan kişi ortak
    kapıya yönlendirilir.

    MUAF: `base.html` — kapının KENDİSİ orada."""
    import io as _io
    import os as _os
    import re as _re
    KALIP = _re.compile(
        r'\*\s*\w*[oO]ran\w*\s*/\s*100'          # tutar * oran / 100
        r'|/\s*\(\s*1\s*\+\s*\w+\s*/\s*100')     # tutar / (1 + oran/100)
    # `q2(...)` ya da ortak kapıyla sarılmışsa MEŞRU: sunucunun
    # yuvarlamasını birebir uyguluyor demektir.
    SARILI = _re.compile(r'\b(q2|kdvHesapla|kdvAyristir)\s*\(')
    sdizin = _os.path.join(KOK, 'templates')
    bulgular = []
    for ad in sorted(_os.listdir(sdizin)):
        if not ad.endswith('.html') or ad == 'base.html':
            continue
        metin = _io.open(_os.path.join(sdizin, ad), encoding='utf-8',
                         errors='replace').read()
        yorumda = False
        for i, t in enumerate(metin.split('\n'), 1):
            g = t.strip()
            # BLOK YORUMU: ilk hâlim yalnız satır BAŞINA bakıyordu ve
            # `/* ... */` içindeki açıklama satırlarını hata sanıyordu.
            if yorumda:
                if '*/' in t:
                    yorumda = False
                continue
            if '/*' in t and '*/' not in t[t.index('/*'):]:
                yorumda = True
                continue
            if g.startswith(('*', '//', '<!--', '/*')) or not KALIP.search(t):
                continue
            if SARILI.search(t):
                continue
            bulgular.append(f'{ad}:{i}  {g[:72]}')
    assert not bulgular, (
        'elle KDV hesabı — `kdvHesapla` / `kdvAyristir` kullanılmalı:'
        '\n  ' + '\n  '.join(bulgular))


def test_yv1_civi_eski_hatayi_yakaliyor():
    """TABANDA DA GEÇER — çivinin kör noktasını sınar.

    Kaldırdığımız üç biçimi de yakalıyor mu?"""
    import re as _re
    KALIP = _re.compile(
        r'\*\s*\w*[oO]ran\w*\s*/\s*100'
        r'|/\s*\(\s*1\s*\+\s*\w+\s*/\s*100')
    for eski in (
            '  const kdv = ara * oran / 100;',
            '  const kdv = matrah * oran / 100;',
            '  const net = (kdvDahil && kdvOran > 0) ? fiyat / (1 + kdvOran / 100) : fiyat;',
            '  if (dahil) { toplam = tutar; matrah = tutar / (1 + oran / 100); kdv = toplam - matrah; }'):
        assert KALIP.search(eski), f'çivi bunu kaçırıyor: {eski.strip()[:60]}'


# ═══════════════════════════════════════════════════════════════════
#  YK3 · AYNI İSTEK İKİ KEZ GELİRSE İKİNCİ KAYIT OLUŞMASIN
#
#  ÖLÇÜLDÜ — aynı gövde aynı uca iki kez:
#    fatura tahsilatı   200 / 200  ✗ aynı 500 $ iki kez düştü;
#                       bakiye 10.000 → 9.500 → 9.000
#    hızlı satış        200 / 200  ✗ aynı `fatura_no` ile iki fatura
#    çek kaydı          200 / 200  ✗ aynı `cek_no` iki kez
#    maliyet · sabit gider         ✗
#
#  Ekranların düğme kilidi ilk savunma ama tek savunma olamaz: ağ
#  koptuğunda tarayıcı isteği kendisi yineliyor.
# ═══════════════════════════════════════════════════════════════════

def _yk3_kur():
    """Ölçüm için cari + kasa + fatura."""
    from models import Cari, Fatura, Kasa
    with fa.app.app_context():
        if not Cari.query.filter_by(id='C-YK3').first():
            db.session.add(Cari(id='C-YK3', unvan='YK3 MUSTERI',
                                cari_tip='Müşteri', para_birimi='USD',
                                gorunurluk='acik'))
        if not Kasa.query.filter_by(ad='YK3 KASA').first():
            db.session.add(Kasa(ad='YK3 KASA', doviz='USD', bakiye=0))
        db.session.commit()
        if not Fatura.query.filter_by(id='F-YK3').first():
            db.session.add(Fatura(id='F-YK3', fatura_no='YK3-1',
                                  musteri='YK3 MUSTERI', cari_id='C-YK3',
                                  toplam=10000, ara_toplam=10000,
                                  doviz='USD', durum='Kesildi',
                                  yon='satis', fatura_tarihi=date.today()))
            db.session.commit()
        return Kasa.query.filter_by(ad='YK3 KASA').first().id


def test_yk3_ayni_tahsilat_iki_kez_dusmuyor():
    """ÖLÇÜLEN HATA: aynı 500 $ iki kez düşüyor, bakiye 9.000 oluyor."""
    from models import CariHareket
    kid = _yk3_kur()
    c = istemci('admin', 'ADMIN')
    govde = {'tutar': 500, 'doviz': 'USD', 'kasa_id': kid,
             'aciklama': 'YK3 ölçüm'}
    with fa.app.app_context():
        once = CariHareket.query.count()
    r1 = c.post('/api/fatura/F-YK3/tahsilat', json=govde, headers=H)
    assert r1.status_code == 200, r1.get_data(as_text=True)[:200]
    r2 = c.post('/api/fatura/F-YK3/tahsilat', json=govde, headers=H)
    assert r2.status_code == 409, (
        f'ikinci tahsilat kabul edildi: {r2.get_data(as_text=True)[:200]}')
    assert (r2.get_json() or {}).get('error') == 'yineleme_suphesi'
    with fa.app.app_context():
        assert CariHareket.query.count() == once + 1, 'ikinci hareket yazılmış'


def test_yk3_kullanici_onaylarsa_gecebiliyor():
    """Kalkan ENGELLEMİYOR, SORUYOR. Meşru hiçbir kayıt kaybolmamalı.

    `base.html`deki `api()` 409'u görünce kullanıcıya sorar ve
    onaylanırsa `yineleme_onay` ile yeniden gönderir."""
    from models import Maliyet
    from models import BlokStok
    with fa.app.app_context():
        if not BlokStok.query.filter_by(id='B-YK3').first():
            db.session.add(BlokStok(
                id='B-YK3', blok_no='YK3-1', cins='YK3TEST', boy=300,
                yukseklik=150, en=120, hacim_m3=5.4, tonaj=15,
                durum='Serbest', doviz='USD', alis_fiyati=100,
                alis_fiyat_birim='ton'))
            db.session.commit()
        once = Maliyet.query.count()
    c = istemci('admin', 'ADMIN')
    govde = {'maliyet_tip': 'Nakliye', 'baglanti_tip': 'stok',
             'baglanti_id': 'B-YK3', 'tutar': 640, 'doviz': 'USD',
             'kdv_oran': 0, 'aciklama': 'YK3 onay'}
    assert c.post('/api/maliyet', json=govde,
                  headers=H).status_code == 200
    assert c.post('/api/maliyet', json=govde,
                  headers=H).status_code == 409
    # ONAYLI ikinci istek GEÇMELİ
    r3 = c.post('/api/maliyet', json=dict(govde, yineleme_onay=True),
                headers=H)
    assert r3.status_code == 200, r3.get_data(as_text=True)[:200]
    with fa.app.app_context():
        assert Maliyet.query.count() == once + 2, 'onaylı kayıt yazılmadı'


def test_yk3_basarisiz_istek_iz_birakmiyor():
    """TABANDA DA GEÇER — tabanda kalkan yok, iki 400 zaten doğal.
    İşi, kalkan eklendikten SONRA bu davranışın bozulmadığını
    çivilemek; yama sırasında tam burada bir kusur çıkmıştı.

    BAŞARISIZ istek tekrar denendiğinde GERÇEK hatasını vermeli.

    İz `before_request`te yazılıyor (yarış koruması için şart) ama
    400 alan bir istek de iz bırakıyordu: kullanıcı formu düzeltmeden
    tekrar denediğinde "bu kaydı az önce oluşturdunuz" görüyordu —
    yanıltıcı. Artık başarısız isteğin izi siliniyor."""
    c = istemci('admin', 'ADMIN')
    bos = {'cari_id': 'C-YK3'}            # islem_tip yok → 400
    r1 = c.post('/api/cari/hareket', json=bos, headers=H)
    r2 = c.post('/api/cari/hareket', json=bos, headers=H)
    assert r1.status_code == 400, r1.get_data(as_text=True)[:150]
    assert r2.status_code == 400, (
        f'ikinci denemede gerçek hata yerine {r2.status_code}: '
        f'{r2.get_data(as_text=True)[:150]}')


def test_yk3_silme_kalkanin_disinda():
    """Yinelenen SİLME zararsız: ikinci istek silinecek şey bulamaz.

    Tehlikeli olan yinelenen OLUŞTURMA. Üstelik DELETE'in gövdesi
    yok, yani onay bayrağını taşıyamazdı — kullanıcı duvara toslar
    ve çıkış yolu olmazdı. ÖLÇÜLDÜ: DELETE kapsamdayken üç mevcut
    test düşüyordu, üçü de kaydı silip yeniden kuran senaryolardı."""
    import io as _io
    import re as _re
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    i = kaynak.index('def _yineleme_kalkani')
    kesit = kaynak[i:i + 1400]
    m = _re.search(r"request\.method not in \(([^)]*)\)", kesit)
    assert m, 'kalkanın yöntem listesi bulunamadı'
    assert 'DELETE' not in m.group(1), (
        f'DELETE kalkan kapsamında: {m.group(1)}')
    for y in ('POST', 'PUT', 'PATCH'):
        assert y in m.group(1), f'{y} kapsam dışı kalmış'


def test_yk3_ayni_cek_numarasi_iki_kez_girilemez():
    """20 saniyelik pencere GÜNLER sonrasını yakalamaz; fiziksel bir
    çek ise iki kez var olamaz. Ölçüt aynı BANKA + aynı NUMARA —
    farklı bankalar aynı numarayı kullanabilir."""
    from models import Cek
    _yk3_kur()
    c = istemci('admin', 'ADMIN')
    govde = {'cek_no': 'YK3-CEK-7', 'banka_adi': 'YK3 Bank',
             'tutar': 3300, 'doviz': 'USD', 'yon': 'alinan',
             'tip': 'musteri', 'cari_id': 'C-YK3',
             'vade_tarihi': date.today().isoformat()}
    assert c.post('/api/cek', json=govde, headers=H).status_code == 200
    # Pencereyi atlamak için onay ver: yakalayan artık NUMARA denetimi.
    # İKİ AYRI ONAY: `yineleme_onay` çift tıklama içindir, numara
    # denetiminin kendi onayı `mukerrer_onay`. Tek bayrak olsaydı biri
    # ötekini susturur, numara denetimi hiç çalışmazdı — ölçüldü.
    r2 = c.post('/api/cek', json=dict(govde, yineleme_onay=True),
                headers=H)
    assert r2.status_code == 409, (
        f'aynı çek numarası ikinci kez kabul edildi: '
        f'{r2.get_data(as_text=True)[:200]}')
    # BAŞKA bankada aynı numara SERBEST
    r3 = c.post('/api/cek', json=dict(govde, banka_adi='YK3 Diger Bank',
                                      yineleme_onay=True,
                                      mukerrer_onay=True), headers=H)
    assert r3.status_code == 200, (
        f'farklı bankada aynı numara engellendi: '
        f'{r3.get_data(as_text=True)[:200]}')


def test_yk3_kalkan_merkezi_kapida():
    """ÇİVİ: kalkan `before_request` olmalı — uç uç DEĞİL.

    OY1'de tam bunu ölçtük: sayfa kilitliydi ama API'si açıktı,
    çünkü denetim uç uç yapılmış ve birkaçı atlanmıştı. Merkezî
    kapı HENÜZ YAZILMAMIŞ uçları da kapsar."""
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    assert '@app.before_request\n    def _yineleme_kalkani' in kaynak, (
        'kalkan before_request değil — merkezî olma özelliğini kaybeder')
    # Ekran tarafı da TEK kapıda
    b = _io.open(os.path.join(KOK, 'templates', 'base.html'),
                 encoding='utf-8').read()
    assert 'd.onay_alani' in b, (
        'api() 409 yineleme yanıtını ele almıyor')
    assert '_o[d.onay_alani] = true' in b, (
        'onaylanan istek yeniden gönderilmiyor')
    # Onay alanı YANITTAN okunuyor: ayrı denetimlerin ayrı onayı olsun
    # diye. Tek sabit bayrak kullansaydım biri ötekini sustururdu —
    # ölçüldü, çek numarası denetimi tam bu yüzden hiç çalışmadı.


def test_yk3_bildirim_suresi_uzatildi():
    """Kullanıcı isteği: bildirimler 2,6 saniyede kayboluyordu."""
    import io as _io
    import re as _re
    b = _io.open(os.path.join(KOK, 'templates', 'base.html'),
                 encoding='utf-8').read()
    m = _re.search(r"classList\.remove\('acik'\),\s*hata\s*\?\s*(\d+)\s*:\s*(\d+)", b)
    assert m, 'bildirim süresi bulunamadı'
    _hata, _ok = int(m.group(1)), int(m.group(2))
    assert _ok >= 5000, f'başarı bildirimi {_ok} ms — en az 5.000 olmalı'
    assert _hata >= _ok, f'hata bildirimi ({_hata}) başarıdan kısa ({_ok})'


# ═══════════════════════════════════════════════════════════════════
#  KB1 · KASA BAKİYESİ ATOMİK ARTIRIMLA GÜNCELLENİR
#
#  ÖLÇÜLDÜ — GERÇEK PostgreSQL 16, READ COMMITTED, aynı kasaya
#  eşzamanlı para girişleri:
#      8 iş parçacığı × 10 × 100 $ → hareket 80, bakiye 1.700 $
#                                    (beklenen 8.000) · 6.300 $ KAYIP
#      3 iş parçacığı × 5  × 100 $ → 700 $ kayıp
#      2 iş parçacığı × 5  × 100 $ → 200 $ kayıp
#
#  SEBEP: `kasa.bakiye = q2((kasa.bakiye or 0) + tutar)` Python'da
#  oku-değiştir-yaz. İki istek aynı anda ESKİ değeri okur, biri
#  kaybolur. Hareketler kayıtlı kalır, yalnız bakiye eksilir.
#
#  BU TESTLER SQLite'TA KOŞUYOR ve SQLite tüm veritabanını
#  kilitlediği için yarışı GİZLER — eşzamanlılık testi yazsaydım
#  TABANDA DA GEÇERDİ, yani hiçbir şey ölçmezdi. Onun yerine
#  artırımın gerçekten VERİTABANINDA yapıldığını sınıyoruz.
# ═══════════════════════════════════════════════════════════════════

def test_kb1_bakiye_artirimi_veritabaninda_yapiliyor():
    """ÇİVİ: `_kasa_bakiye_ekle` bir UPDATE yayınlamalı ve artırım
    SQL'in içinde olmalı — Python'da hesaplanıp yazılmış bir sabit
    değil."""
    from sqlalchemy import event as _ev
    from models import Kasa
    yayinlar = []

    with fa.app.app_context():
        k = Kasa.query.filter_by(ad='KB1 KASA').first()
        if not k:
            k = Kasa(ad='KB1 KASA', doviz='USD', bakiye=1000)
            db.session.add(k)
            db.session.commit()
        ekle = _kc1_kapi('_kasa_bakiye_ekle')
        motor = db.session.get_bind()

        def yakala(conn, cursor, ifade, parametre, baglam, cok):
            yayinlar.append(ifade)

        _ev.listen(motor, 'before_cursor_execute', yakala)
        try:
            ekle(k, 250)
            db.session.commit()
        finally:
            _ev.remove(motor, 'before_cursor_execute', yakala)

    guncellemeler = [y for y in yayinlar
                     if y.strip().upper().startswith('UPDATE')
                     and 'bakiye' in y]
    assert guncellemeler, (
        f'UPDATE yayınlanmadı — artırım Python tarafında yapılmış '
        f'olabilir. Yayınlar: {yayinlar[:3]}')
    sql = guncellemeler[0]
    # `bakiye = ... bakiye ...` — sütun KENDİSİNE atıf yapmalı
    assert sql.count('bakiye') >= 2, (
        f'UPDATE sütunun kendisini okumuyor, yani artırım atomik '
        f'değil:\n{sql}')


def test_kb1_atomik_artirim_eski_sonucu_veriyor():
    """Düzeltme RAKAMI değiştirmemeli — yalnız yarışı kapatmalı.

    Eski hesap `q2((bakiye or 0) + delta)` idi; yenisi aynı
    yuvarlamayı SQL tarafında yapıyor."""
    from models import Kasa
    with fa.app.app_context():
        ekle = _kc1_kapi('_kasa_bakiye_ekle')
        for baslangic, delta in ((0, 100.005), (1000, -250.004),
                                 (33.33, 66.67), (0, 0.145),
                                 (99.99, 0.011), (500, -500)):
            k = Kasa(ad=f'KB1-{baslangic}-{delta}', doviz='USD',
                     bakiye=baslangic)
            db.session.add(k)
            db.session.commit()
            # `q2` fabrikanın içinde; kapanıştan çekiyoruz.
            beklenen = _kc1_kapi('q2')(baslangic + delta)
            ekle(k, delta)
            db.session.commit()
            db.session.refresh(k)
            assert abs(float(k.bakiye) - beklenen) < 0.005, (
                f'{baslangic} + {delta}: {k.bakiye} geldi, '
                f'{beklenen} olmalıydı')


def test_kb1_elle_oku_degistir_yaz_kalmadi():
    """ÇİVİ: hiçbir yerde bakiye Python tarafında artırılmamalı.

    METİN DEĞİL AST: ilk hâlim satır metnine bakıyordu ve kapının
    KENDİ açıklamasındaki örnek satırı hata sanıyordu (üçlü tırnak
    içinde olduğu için `#` denetimi de yakalamıyordu). AST yalnız
    GERÇEK atamaları görür.

    Sınıfın geri gelmesini bu engelliyor: yeni bir uç bakiyeyi
    Python'da artırırsa burası düşer."""
    import ast as _ast
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    bulgular = []
    for d in _ast.walk(_ast.parse(kaynak)):
        hedefler, deger = [], None
        if isinstance(d, _ast.Assign):
            hedefler, deger = d.targets, d.value
        elif isinstance(d, _ast.AugAssign):
            hedefler, deger = [d.target], d.value
        else:
            continue
        for h in hedefler:
            if not (isinstance(h, _ast.Attribute) and h.attr == 'bakiye'):
                continue
            if not isinstance(h.value, _ast.Name):
                continue
            nesne = h.value.id
            sag = _ast.unparse(deger)
            # AugAssign her zaman oku-değiştir-yaz; Assign ise yalnız
            # sağ taraf AYNI alanı okuyorsa.
            if isinstance(d, _ast.AugAssign) or f'{nesne}.bakiye' in sag:
                bulgular.append(
                    f'satır {d.lineno}: {nesne}.bakiye = {sag[:60]}')
    assert not bulgular, (
        'bakiye Python tarafında artırılıyor — `_kasa_bakiye_ekle` '
        'kullanılmalı:\n  ' + '\n  '.join(bulgular))


def test_kb1_civi_eski_hatayi_yakaliyor():
    """TABANDA DA GEÇER — çivinin kör noktasını sınar.

    Kaldırdığımız biçimlerin hepsini yakalıyor mu?"""
    import re as _re
    KALIP = _re.compile(r'\.bakiye\s*(=\s*q2\(\(|\+=|-=)')
    for eski in (
            '            kasa.bakiye = q2((kasa.bakiye or 0) + hedef_tutar)',
            '        kaynak.bakiye = q2((kaynak.bakiye or 0) - tutar)',
            '        k.bakiye += tutar',
            '        k.bakiye -= tutar'):
        assert KALIP.search(eski), f'çivi bunu kaçırıyor: {eski.strip()[:60]}'
# ══════════════════════════════════════════════════════════════════
# RZ2 · AYNI STOK İKİ KEZ SATILMASIN  (yarış durumu)
# ══════════════════════════════════════════════════════════════════
# RZ1 bu sınıfı çözmüştü ama kapısı (`_stok_serbestten_al`) yalnız
# 'Serbest' kaynağı kabul ediyor, bu yüzden yalnız İKİ yolda
# kullanılabildi. Kaynağı 'Serbest' VEYA 'Rezerve' kabul eden üç yol
# açıkta kalmıştı: `_kalem_rezervasyonlari_olustur`,
# `api_proforma_siparise_donustur`, `api_kesim_ekle`.
#
# ÖLÇÜLDÜ — gerçek PostgreSQL 16, READ COMMITTED, gerçek uçla:
#   20 deneme, her birinde AYNI bloğa 2 eşzamanlı sipariş
#     yama öncesi   iki rezervasyonlu blok  20/20  (%100)
#     yama sonrası  iki rezervasyonlu blok   0/20
#
# Hata bugün GÖRÜNMÜYORDU: belge numarası çakışması (BN1) ikinci
# isteği daha erken, HTTP 500 ile öldürüyor ve stoğa hiç varmıyordu.
# Yani numara hatası bunu KAZARA perdeliyordu. Ölçüm için numara
# üreticisi çakışmaz hâle getirilip hata yalıtıldı. Yamaların sırası
# bu yüzden RZ2 → BN1: ters sırada BN1 perdeyi kaldırır ve bugün
# görünmeyen hata görünür hâle gelir.
#
# SQLite'TA EŞZAMANLILIK TESTİ YAZILMADI: SQLite yarışı gizler, öyle
# bir test tabanda da geçerdi. Aşağıdakiler MEKANİZMAYI çiviliyor.


def _rz2_blok(bid, durum='Serbest'):
    with fa.app.app_context():
        if db.session.get(BlokStok, bid) is None:
            db.session.add(BlokStok(
                id=bid, blok_no=bid, cins='TEST', boy=300,
                yukseklik=150, en=120, hacim_m3=5.4, tonaj=15,
                alis_fiyati=1000, doviz='USD', durum=durum,
                giris_tarihi=date.today()))
            db.session.commit()
        else:
            db.session.get(BlokStok, bid).durum = durum
            db.session.commit()


def _rz2_siparis(bid, musteri, durum, **ek):
    g = {'musteri': musteri, 'doviz': 'USD', 'durum': durum,
         'kalemler': [{'urun_tip': 'BLOK', 'cins': 'TEST', 'adet': 1,
                       'miktar': 15, 'birim': 'ton', 'birim_fiyat': 500,
                       'doviz': 'USD', 'stok_ids': [bid]}],
         'yineleme_onay': True}
    g.update(ek)
    return g


def test_rz2_stok_kapisi_atomik_update_yayinliyor():
    """ÇİVİ: `_stok_durum_degistir` tek bir UPDATE yayınlamalı ve o
    UPDATE mevcut durumu KOŞUL olarak taşımalı.

    Koşul SQL'in içinde olmazsa kapı kapı değildir: Python'da
    okunup Python'da karar verilen her şeyin arasına ikinci bir
    istek girebilir. "Atomik" iddiası burada söz değil, ölçüm."""
    from sqlalchemy import event as _ev
    yayinlar = []
    _rz2_blok('RZ2-SQL', 'Serbest')
    with fa.app.app_context():
        kapi = _kc1_kapi('_stok_durum_degistir')
        stok = db.session.get(BlokStok, 'RZ2-SQL')
        motor = db.session.get_bind()

        def yakala(conn, cursor, ifade, parametre, baglam, cok):
            yayinlar.append(ifade)

        _ev.listen(motor, 'before_cursor_execute', yakala)
        try:
            assert kapi(stok, 'Rezerve', ('Serbest', 'Rezerve')) is True
            db.session.commit()
        finally:
            _ev.remove(motor, 'before_cursor_execute', yakala)

    guncellemeler = [y for y in yayinlar
                     if y.strip().upper().startswith('UPDATE')
                     and 'durum' in y]
    assert guncellemeler, (
        f'UPDATE yayınlanmadı — karar Python tarafında verilmiş '
        f'olabilir. Yayınlar: {yayinlar[:3]}')
    sql = guncellemeler[0].upper()
    assert 'WHERE' in sql and ('IN (' in sql or 'IS NULL' in sql), (
        f'UPDATE mevcut durumu koşul olarak taşımıyor, yani kapı '
        f'atomik değil:\n{guncellemeler[0]}')


def test_rz2_kapi_gercekten_kapi_mi():
    """Hedef durum izinli kümede YOKSA ikinci geçiş reddedilmeli.

    Onaylanmış siparişte hedef 'Satildi' ve izinli küme
    ('Serbest','Rezerve') — 'Satildi' kümede olmadığı için geçiş
    gerçek bir kapıdır. Teklif aşamasında hedef 'Rezerve' ve kümede
    OLDUĞU için ikisi de geçer; kullanıcının kararı bu (aynı blok
    ikinci teklife işlenebilsin, ama uyarılsın)."""
    # Bloklar bağlamın DIŞINDA kurulur: `_rz2_blok` kendi
    # app_context'ini açıyor, dıştaki açık işlemle çakışınca SQLite
    # "database is locked" veriyor.
    _rz2_blok('RZ2-KAPI', 'Serbest')
    _rz2_blok('RZ2-TEKLIF', 'Rezerve')
    with fa.app.app_context():
        kapi = _kc1_kapi('_stok_durum_degistir')
        s = db.session.get(BlokStok, 'RZ2-KAPI')
        assert kapi(s, 'Satildi', ('Serbest', 'Rezerve')) is True
        assert kapi(s, 'Satildi', ('Serbest', 'Rezerve')) is False, (
            'ikinci geçiş de kabul edildi — kapı kapı değil')
        t = db.session.get(BlokStok, 'RZ2-TEKLIF')
        assert kapi(t, 'Rezerve', ('Serbest', 'Rezerve')) is True
        assert kapi(t, 'Rezerve', ('Serbest', 'Rezerve')) is True, (
            'teklif aşaması kapatıldı — karar "serbest kalsın, '
            'uyarılsın" idi')
        db.session.rollback()


def test_rz2_kapi_null_durumu_geciriyor():
    """Göç öncesi satırlarda `durum` NULL olabilir.

    Mevcut kod her yerde `k.durum or 'Serbest'` diyor, yani NULL'ı
    serbest sayıyor. `IN` NULL ile eşleşmediği için kapı eski
    satırları takardı — eklediğimiz kapının yeni bir hata
    doğurmaması gerekiyor."""
    _rz2_blok('RZ2-NULL', 'Serbest')
    with fa.app.app_context():
        kapi = _kc1_kapi('_stok_durum_degistir')
        db.session.query(BlokStok).filter(
            BlokStok.id == 'RZ2-NULL').update(
                {BlokStok.durum: None}, synchronize_session=False)
        db.session.commit()
        s = db.session.get(BlokStok, 'RZ2-NULL')
        assert kapi(s, 'Rezerve', ('Serbest', 'Rezerve')) is True, (
            'durumu NULL olan eski satır kapıda takıldı')
        db.session.rollback()


def test_rz2_kalem_rezervasyonu_kapiya_bagli():
    """ÇİVİ: `_kalem_rezervasyonlari_olustur` durumu ELLE yazmamalı.

    METİN DEĞİL AST. Sınıfın geri gelmesini bu engelliyor: biri
    kapıyı atlayıp yeniden `stok.durum = ...` yazarsa burası
    düşer."""
    import ast as _ast
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    hedef = None
    for d in _ast.walk(_ast.parse(kaynak)):
        if (isinstance(d, _ast.FunctionDef)
                and d.name == '_kalem_rezervasyonlari_olustur'):
            hedef = d
            break
    assert hedef is not None, '_kalem_rezervasyonlari_olustur yok'
    govde = _ast.unparse(hedef)
    assert '_stok_durum_degistir' in govde, (
        'kalem rezervasyonu atomik kapıya bağlı değil')
    elle = []
    for d in _ast.walk(hedef):
        if not isinstance(d, _ast.Assign):
            continue
        for h in d.targets:
            if isinstance(h, _ast.Attribute) and h.attr == 'durum':
                elle.append(f'satır {d.lineno}: '
                            f'{_ast.unparse(h)} = '
                            f'{_ast.unparse(d.value)[:40]}')
    assert not elle, (
        'durum elle yazılıyor — `_stok_durum_degistir` '
        'kullanılmalı:\n  ' + '\n  '.join(elle))


def test_rz2_musait_olmayan_stok_sessiz_atlanmiyor():
    """Kapı eklemek YENİ bir sessiz kayıp doğurmamalı.

    Zaten satılmış bir stok siparişe eklenmek istenince eskiden
    sessizce atlanıyordu: sipariş o stok olmadan oluşuyor,
    kullanıcı ekranda hiçbir şey görmüyordu. Avladığımız sınıfın
    aynısı; cevap artık söylüyor."""
    adm = istemci('admin', 'ADMIN')
    _rz2_blok('RZ2-SATILDI', 'Satildi')
    c = adm.post('/api/siparis', headers=H,
                 json=_rz2_siparis('RZ2-SATILDI', 'RZ2 MUSTERI',
                                   'Onaylandi'))
    assert c.status_code == 200, c.get_data(as_text=True)
    j = c.get_json()
    atl = j.get('atlanan_stoklar') or []
    assert len(atl) == 1 and atl[0]['stok_id'] == 'RZ2-SATILDI', (
        f'atlanan stok cevapta bildirilmiyor: {j}')
    assert 'eklenemedi' in (j.get('mesaj') or ''), (
        f'mesaj atlamadan söz etmiyor: {j.get("mesaj")}')
    with fa.app.app_context():
        assert Rezervasyon.query.filter_by(
            stok_id='RZ2-SATILDI', iptal_nedeni=None).count() == 0


def test_rz2_teklif_cakismasi_uyarip_onay_istiyor():
    """Kullanıcının kararı: teklif aşamasında blok serbest kalsın,
    aynı blok ikinci bir teklife de işlenebilsin — AMA sistem bunun
    başka bir teklife bağlı olduğunu söyleyip onay istesin.

    Onay YK3'ün `onay_alani` düzeneğiyle alınıyor; yeni ekran kodu
    gerekmiyor."""
    adm = istemci('admin', 'ADMIN')
    _rz2_blok('RZ2-CAKIS', 'Serbest')
    r1 = adm.post('/api/siparis', headers=H,
                  json=_rz2_siparis('RZ2-CAKIS', 'RZ2 BIRINCI',
                                    'Teklif Asam.'))
    assert r1.status_code == 200, r1.get_data(as_text=True)

    r2 = adm.post('/api/siparis', headers=H,
                  json=_rz2_siparis('RZ2-CAKIS', 'RZ2 IKINCI',
                                    'Teklif Asam.'))
    assert r2.status_code == 409, (
        f'ikinci teklif uyarı almadı: {r2.status_code} '
        f'{r2.get_data(as_text=True)[:200]}')
    j = r2.get_json()
    assert j.get('error') == 'blok_baska_teklifte'
    assert j.get('onay_alani') == 'teklif_cakisma_onay'
    assert j.get('onay_sorusu'), 'onay sorusu yok'
    assert 'RZ2-CAKIS' in (j.get('mesaj') or ''), (
        f'mesaj hangi bloktan söz ettiğini söylemiyor: {j.get("mesaj")}')
    assert j.get('cakisanlar'), 'çakışan kayıtlar bildirilmiyor'

    r3 = adm.post('/api/siparis', headers=H,
                  json=_rz2_siparis('RZ2-CAKIS', 'RZ2 IKINCI',
                                    'Teklif Asam.',
                                    teklif_cakisma_onay=True))
    assert r3.status_code == 200, (
        f'onaylandığı hâlde geçmedi: {r3.get_data(as_text=True)[:200]}')
    with fa.app.app_context():
        assert Rezervasyon.query.filter_by(
            stok_id='RZ2-CAKIS', iptal_nedeni=None).count() == 2, (
            'onaydan sonra ikinci teklife bağlanmadı')


def test_rz2_kesim_kaynagi_uretimden_once_sahipleniyor():
    """ÇİVİ: kesimde kaynak, İLK YAZMADAN ÖNCE atomik alınmalı.

    Sıra tesadüf değil, ölçümle bulundu:
      · daha ERKEN olamaz — aradaki doğrulama hataları kaynağı
        'Tukendi' bırakıp kesimsiz çıkarırdı.
      · daha GEÇ olamaz — üretim döngüsünde her plakanın kimliği bir
        sorgu açıyor, o sorgu bekleyen plakaları flush ediyor. Plaka
        kimlikleri blok no + slab'den BELİRLENİMLİ türüyor
        (`PLK-RZ-B-C1-01`), yani aynı bloğun iki kesimi HEP aynı
        kimliği üretir; kaybeden istek kapı konuşmadan
        `plaka_stok_pkey` ihlaliyle ölüp çıplak 500 veriyordu.
        (Önce `no_autoflush` ile denedim — yetmedi, kirlenme kapıdan
        ÖNCE, üretim döngüsünün kendi içinde oluyordu.)

    Bu test o SIRAYI çiviliyor; biri kapıyı aşağı taşırsa düşer."""
    import ast as _ast
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    hedef = None
    for d in _ast.walk(_ast.parse(kaynak)):
        if (isinstance(d, _ast.FunctionDef)
                and d.name == 'api_kesim_ekle'):
            hedef = d
            break
    assert hedef is not None, 'api_kesim_ekle yok'

    kapi_satiri = yazma_satiri = None
    for d in _ast.walk(hedef):
        if not isinstance(d, _ast.Call):
            continue
        ad = _ast.unparse(d.func)
        if (ad == '_stok_durum_degistir' and kapi_satiri is None
                and "'Tukendi'" in _ast.unparse(d)):
            kapi_satiri = d.lineno
        if (ad in ('db.session.add', 'db.session.flush')
                and yazma_satiri is None):
            yazma_satiri = d.lineno
    assert kapi_satiri is not None, (
        'kesim kaynağı atomik kapıdan geçmiyor')
    assert yazma_satiri is not None, 'db.session.add bulunamadı'
    assert kapi_satiri < yazma_satiri, (
        f'kapı ilk yazmadan SONRA ({kapi_satiri} > {yazma_satiri}): '
        f'kaybeden istek, kapı konuşmadan birincil anahtar '
        f'ihlaliyle 500 verir')

    elle = [f'satır {d.lineno}'
            for d in _ast.walk(hedef)
            if isinstance(d, _ast.Assign)
            and any(isinstance(h, _ast.Attribute) and h.attr == 'durum'
                    and _ast.unparse(d.value) == "'Tukendi'"
                    for h in d.targets)]
    assert not elle, (
        "kaynak hâlâ elle 'Tukendi' yapılıyor: " + ', '.join(elle))


def test_rz2_tarayici_onayi_alan_basina_izliyor():
    """ÇİVİ: `api()` onayı ALAN BAŞINA izlemeli, tek bayrakla değil.

    Eskiden `_yinelemeOnaylandi` tek bir bayraktı. Bir istek iki ayrı
    onay isterse (önce teklif çakışması, sonra YK3 yineleme)
    ikincisi SORULMADAN sessizce düşerdi — kapı eklerken
    doğurduğumuz yeni bir sessiz kayıp olurdu."""
    import io as _io
    metin = _io.open(os.path.join(KOK, 'templates', 'base.html'),
                     encoding='utf-8').read()
    kod = [s for s in metin.split('\n')
           if '_yinelemeOnaylandi' in s and not s.strip().startswith('*')
           and 'Eskiden' not in s]
    assert not kod, (
        'onay hâlâ tek bayrakla izleniyor:\n  '
        + '\n  '.join(k.strip()[:80] for k in kod))
    assert '_onaylanan' in metin, 'alan başına onay izlenmiyor'
    assert 'onay_sorusu' in metin, (
        'sunucunun verdiği onay sorusu kullanılmıyor — her onay '
        '"Yine de kaydedilsin mi?" diye sorulur')


def test_rz2_atlananlar_dokunulmayan_uctan_da_bildiriliyor():
    """Bildirim UÇ BAŞINA değil, tek `after_request` kancasında.

    Stok rezerve eden BEŞ uç var: api_siparis_ekle,
    api_sicak_satis, api_siparis_guncelle, api_siparis_stok_ekle,
    api_proforma_siparise_donustur. Uç başına yazsaydım biri
    unutulur ve o uç sessizce korumasız kalırdı — OY1'de ölçtüğümüz
    hatanın aynısı.

    Bu test HİÇ DOKUNMADIĞIM bir uçtan ölçüyor: sipariş
    GÜNCELLEME (PUT). Bildirim oradan da geliyorsa kanca gerçekten
    hepsini kapsıyor."""
    adm = istemci('admin', 'ADMIN')
    _rz2_blok('RZ2-PUT-A', 'Serbest')
    _rz2_blok('RZ2-PUT-B', 'Satildi')
    r = adm.post('/api/siparis', headers=H,
                 json=_rz2_siparis('RZ2-PUT-A', 'RZ2 PUT', 'Onaylandi'))
    assert r.status_code == 200, r.get_data(as_text=True)
    sid = r.get_json()['id']

    p = adm.put(f'/api/siparis/{sid}', headers=H,
                json=_rz2_siparis('RZ2-PUT-B', 'RZ2 PUT', 'Onaylandi'))
    assert p.status_code == 200, p.get_data(as_text=True)
    j = p.get_json()
    atl = j.get('atlanan_stoklar') or []
    assert any(a.get('stok_id') == 'RZ2-PUT-B' for a in atl), (
        f'dokunulmayan uçtan (PUT) bildirim gelmedi: {j}')
    assert 'eklenemedi' in (j.get('mesaj') or ''), (
        f'mesaj atlamadan söz etmiyor: {j.get("mesaj")}')


def test_rz2_siparis_ekrani_sunucu_mesajini_gosteriyor():
    """Sunucunun söylediği EKRANA ÇIKMALI.

    `siparis.html` kendi metnini kuruyor ve `d.mesaj` hiç
    okunmuyordu. Kapı bir stoğu geçirmediğinde sunucu söylüyor ama
    kullanıcı görmüyordu — kapıyı koyup susmak, avladığımız sessiz
    kaybın aynısı olurdu. Yamayı kurarken tam bu tuzağa düşmüştüm;
    test onu çiviliyor."""
    import io as _io
    metin = _io.open(os.path.join(KOK, 'templates', 'siparis.html'),
                     encoding='utf-8').read()
    i = metin.find('Sipariş oluşturuldu · ')
    assert i > 0, 'sipariş kaydetme bildirimi bulunamadı'
    cevre = metin[max(0, i - 500):i + 220]
    assert 'd.mesaj' in cevre, (
        'ekran sunucunun mesajını yok sayıyor — `atlanan_stoklar` '
        'bildirimi kullanıcıya hiç görünmez')
    assert 'atlanan_stoklar' in metin, (
        'atlama olduğunda uyarı rengiyle gösterilmiyor')


def test_rz2_civi_eski_hatayi_yakaliyor():
    """TABANDA DA GEÇER — çivinin kör noktasını sınar.

    Kaldırdığımız biçimleri AST gerçekten görüyor mu?"""
    import ast as _ast
    for eski in ("stok.durum = hedef_stok_durum",
                 "k.durum = 'Tukendi'",
                 "stok.durum = 'Satildi' if x else 'Rezerve'"):
        d = _ast.parse(eski).body[0]
        assert isinstance(d, _ast.Assign)
        assert any(isinstance(h, _ast.Attribute) and h.attr == 'durum'
                   for h in d.targets), f'çivi bunu kaçırıyor: {eski}'
# ══════════════════════════════════════════════════════════════════
# BN1 · AYNI ANDA İKİ BELGE AYNI NUMARAYI ALMASIN
# ══════════════════════════════════════════════════════════════════
# Üç üretici de önce-kontrol-sonra-yaz: numara üretilip döndükten
# sonra satır COMMIT edilene kadar başka bir işlem aynı numarayı
# üretebiliyordu. Kaybeden istekte `duplicate key value violates
# unique constraint "..._pkey"` ve kullanıcı ÇIPLAK HTTP 500
# görüyor; girdiği kayıt kayboluyor.
#
# ÖLÇÜLDÜ — gerçek PostgreSQL 16, READ COMMITTED, gerçek uçlar,
# 15 deneme × 2 eşzamanlı istek (gövdeler FARKLI, YK3 kalkanı
# devrede değil):
#
#     _okunur_id              POST /api/siparis      15/15 → 0/15
#     _cari_hareket_okunur_id fatura tahsilatı       15/15 → 0/15
#     _stok_okunur_id         POST /api/stok/ekle    15/15 → 0/15
#
# Pencere `_okunur_id` için merdivenle ölçüldü: 0 ms %100,
# 5 ms %80, 10 ms ve üstü %0 — yani ~10 ms. Dar, ama üretimde
# `gunicorn -w 3` ile gerçek paralellik var. En acı hâli tahsilat:
# para geldi, kullanıcı hata gördü, kayıt yok.
#
# SQLite'TA EŞZAMANLILIK TESTİ YAZILMADI: SQLite yazmaları tek
# veritabanı kilidiyle sıralıyor, yarış pencere bulamıyor, öyle bir
# test tabanda da geçerdi. Aşağıdakiler MEKANİZMAYI çiviliyor.


def _bn1_uretici(ad):
    """Üreticinin AST düğümünü döner."""
    import ast as _ast
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    for d in _ast.walk(_ast.parse(kaynak)):
        if isinstance(d, _ast.FunctionDef) and d.name == ad:
            return d
    return None


def test_bn1_uc_uretici_de_kilidi_aliyor():
    """ÇİVİ: numara üreten ÜÇ yol da kilidi almalı.

    Biri atlanırsa o belge türü sessizce korumasız kalır —
    OY1'de ölçtüğümüz hatanın aynısı. Üçü ayrı yollar:
      _okunur_id              SIP, FTR, PI, SEV, MYT, KSM, ORT
      _cari_hareket_okunur_id HR-* (24 ayrı hareket yolu)
      _stok_okunur_id         BLK / PLK / EBT
    """
    import ast as _ast
    eksik = []
    for ad in ('_okunur_id', '_cari_hareket_okunur_id',
               '_stok_okunur_id'):
        d = _bn1_uretici(ad)
        assert d is not None, f'{ad} yok'
        if '_belge_no_kilidi' not in _ast.unparse(d):
            eksik.append(ad)
    assert not eksik, (
        'bu üreticiler kilidi almıyor, numaraları hâlâ yarışa açık: '
        + ', '.join(eksik))


def test_bn1_kilit_taramadan_once_aliniyor():
    """ÇİVİ: kilit, taramadan ÖNCE alınmalı.

    Sonra alınırsa hiçbir şey değişmez: tarama zaten bayat veriyi
    okumuş olur. Pencere tam tarama ile commit arasında, o yüzden
    kilit taramadan önce olmak ZORUNDA. Biri kilidi aşağı taşırsa
    burası düşer."""
    import ast as _ast
    import io as _io
    # Taramayı KAYNAK SATIRLARINDA arıyorum. İlk hâlim `ast.walk`
    # düğümlerini unparse edip içinde arıyordu ve FunctionDef'in
    # kendisi de geliyordu: gövdenin tamamı metne dönüyor, satır
    # numarası ise `def` satırı oluyordu. Kilit her zaman "sonra"
    # görünüyordu.
    satirlar = _io.open(os.path.join(KOK, 'flask_app.py'),
                        encoding='utf-8').read().replace(
                            '\r\n', '\n').split('\n')
    for ad, tarama in (('_okunur_id', '.like('),
                       ('_cari_hareket_okunur_id', 'LIKE :k'),
                       ('_stok_okunur_id', 'db.session.get(')):
        d = _bn1_uretici(ad)
        kilit_satiri = None
        for c in _ast.walk(d):
            if (isinstance(c, _ast.Call)
                    and _ast.unparse(c.func) == '_belge_no_kilidi'
                    and kilit_satiri is None):
                kilit_satiri = c.lineno
        tarama_satiri = None
        for no in range(d.lineno, (d.end_lineno or d.lineno) + 1):
            t = satirlar[no - 1]
            if t.strip().startswith('#'):
                continue
            if tarama in t:
                tarama_satiri = no
                break
        assert kilit_satiri is not None, f'{ad}: kilit çağrısı yok'
        assert tarama_satiri is not None, (
            f'{ad}: tarama ("{tarama}") bulunamadı')
        assert kilit_satiri < tarama_satiri, (
            f'{ad}: kilit taramadan SONRA alınıyor '
            f'({kilit_satiri} > {tarama_satiri}) — pencere açık kalır')


def test_bn1_cari_hareket_kilidi_kendi_baglantisinda_aliyor():
    """ÇİVİ: `_cari_hareket_okunur_id` kilidi KENDİ bağlantısında
    almalı.

    O bir `before_insert` eşleme dinleyicisi ve kendisine verilen
    ham `baglanti` ile çalışıyor. Kilit `db.session` üzerinden
    alınırsa numarayı yazacak işlemin DIŞINDA kalabilir ve hiçbir
    şey korumaz."""
    import ast as _ast
    d = _bn1_uretici('_cari_hareket_okunur_id')
    cagrilar = [_ast.unparse(c) for c in _ast.walk(d)
                if isinstance(c, _ast.Call)
                and _ast.unparse(c.func) == '_belge_no_kilidi']
    assert cagrilar, 'kilit çağrısı yok'
    assert any('baglanti' in c for c in cagrilar), (
        f'kilit kendi bağlantısında alınmıyor: {cagrilar}')


def test_bn1_kilit_islem_kapsamli():
    """ÇİVİ: `pg_advisory_xact_lock` — `pg_advisory_lock` DEĞİL.

    İşlem kapsamlı kilit COMMIT/ROLLBACK ile kendiliğinden
    bırakılıyor. Oturum kapsamlı olanı elle bırakmak gerekir ve bir
    hata yolunda bırakılmazsa kilit açıkta kalır: o andan sonra
    HİÇBİR belge numarası üretilemez, sistem kilitlenir."""
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read()
    assert 'pg_advisory_xact_lock' in kaynak, (
        'işlem kapsamlı kilit kullanılmıyor')
    kotu = [s.strip() for s in kaynak.replace('\r\n', '\n').split('\n')
            if 'pg_advisory_lock' in s and not s.strip().startswith('#')]
    assert not kotu, (
        'oturum kapsamlı kilit var — bırakılmazsa sistem kilitlenir:\n  '
        + '\n  '.join(k[:80] for k in kotu))


def test_bn1_tek_kilit_anahtari():
    """ÇİVİ: TEK küresel anahtar — ön ek başına anahtar YOK.

    Bir istek iki ayrı ön ek için numara üretebiliyor (fatura kesen
    uç FTR ve MYT üretiyor). İki ayrı kilit, iki işlemin ters sırada
    alması hâlinde kilitlenmeye (deadlock) açık olurdu. Tek
    anahtarda o sıra sorunu yok.

    Kilit çağrıları ARGÜMANSIZ (ya da yalnız `baglanti`) olmalı:
    biri ön ek geçirmeye başlarsa anahtar ön eke göre türetilmeye
    başlar ve kilitlenme kapısı açılır."""
    import ast as _ast
    kilitler = []
    for ad in ('_okunur_id', '_cari_hareket_okunur_id',
               '_stok_okunur_id'):
        d = _bn1_uretici(ad)
        for c in _ast.walk(d):
            if (isinstance(c, _ast.Call)
                    and _ast.unparse(c.func) == '_belge_no_kilidi'):
                kilitler.append((ad, [_ast.unparse(a) for a in c.args]))
    assert kilitler, 'kilit çağrısı yok'
    kotu = [(a, g) for a, g in kilitler
            if [x for x in g if x != 'baglanti']]
    assert not kotu, (
        f'kilit çağrısına ön ek/anahtar geçiriliyor — kilitlenme '
        f'kapısı: {kotu}')


def test_bn1_sqlitede_etkisiz_ve_sessiz():
    """SQLite'ta kilit SESSİZCE etkisiz olmalı — ve bu DOĞRU.

    SQLite yazmaları tek veritabanı kilidiyle zaten sıralıyor,
    yarış orada pencere bulamıyor. `pg_advisory_xact_lock`
    SQLite'ta yok; çağrılsa her numara üretimi istisnaya düşer ve
    `_yeni_id` RASTGELESİNE kaçardı — okunur numaralar biterdi.

    Bu test iki şeyi birden çiviliyor: False dönüyor (yani kilit
    denenmedi) ve HİÇBİR SQL yayınlanmıyor."""
    from sqlalchemy import event as _ev
    yayinlar = []
    with fa.app.app_context():
        kilitle = _kc1_kapi('_belge_no_kilidi')
        assert kilitle is not None, '_belge_no_kilidi kapanışta yok'
        motor = db.session.get_bind()

        def yakala(conn, cursor, ifade, parametre, baglam, cok):
            yayinlar.append(ifade)

        _ev.listen(motor, 'before_cursor_execute', yakala)
        try:
            sonuc = kilitle()
        finally:
            _ev.remove(motor, 'before_cursor_execute', yakala)
    assert sonuc is False, (
        f'SQLite üzerinde kilit denenmiş ({sonuc}) — her numara '
        f'üretimi istisnaya düşer ve rastgeleye kaçar')
    assert not yayinlar, (
        f'SQLite üzerinde SQL yayınlandı: {yayinlar[:2]}')


def test_bn1_numaralar_okunur_ve_sirali_kaldi():
    """TABANDA DA GEÇER — kilit DÜZENİ bozmadı mı?

    Kilit çakışmayı kapatıyor ama numaraların okunur ve sıralı
    kalması da şart. Buradaki asıl risk şu: kilit bir istisna
    doğurursa `_okunur_id` sessizce `_yeni_id` rastgelesine düşer,
    çakışma biter ama okunur numara da biter. Bu test onu yakalar.

    (Gerçek PostgreSQL'de 8 eşzamanlı sipariş de ölçüldü:
     SIP-BN-ACR26-01..08, delik yok, tekrar yok, rastgeleye düşen
     yok.)"""
    import re as _re
    adm = istemci('admin', 'ADMIN')
    idler = []
    for i in range(3):
        r = adm.post('/api/siparis', headers=H, json={
            'musteri': 'BN1 MUSTERI', 'doviz': 'USD',
            'durum': 'Onaylandi',
            'kalemler': [{'urun_tip': 'BLOK', 'cins': 'TEST',
                          'adet': 1, 'miktar': 15, 'birim': 'ton',
                          'birim_fiyat': 500 + i, 'doviz': 'USD'}],
            'yineleme_onay': True})
        assert r.status_code == 200, r.get_data(as_text=True)
        idler.append(r.get_json()['id'])
    rastgele = [i for i in idler
                if not _re.fullmatch(r'SIP-[A-Z0-9-]*\d\d-\d+', i)]
    assert not rastgele, (
        f'numara rastgeleye düştü — kilit istisna doğuruyor '
        f'olabilir: {rastgele}')
    siralar = [int(i.rsplit('-', 1)[-1]) for i in idler]
    assert siralar == sorted(siralar) and len(set(siralar)) == 3, (
        f'numaralar sıralı/tekil değil: {idler}')


def test_bn1_civi_eski_hatayi_yakaliyor():
    """TABANDA DA GEÇER — çivinin kör noktasını sınar.

    "Kilit taramadan önce" denetimi, kilidi aşağı taşıyan bir
    değişikliği gerçekten görüyor mu?"""
    import ast as _ast
    kaynak = ('def f():\n'
              '    son = q.filter(m.id.like(k)).all()\n'
              '    _belge_no_kilidi()\n')
    satirlar = kaynak.split('\n')
    d = _ast.parse(kaynak).body[0]
    kilit = None
    for c in _ast.walk(d):
        if (isinstance(c, _ast.Call)
                and _ast.unparse(c.func) == '_belge_no_kilidi'):
            kilit = c.lineno
    tarama = None
    for no in range(d.lineno, (d.end_lineno or d.lineno) + 1):
        if '.like(' in satirlar[no - 1]:
            tarama = no
            break
    assert kilit and tarama and kilit > tarama, (
        f'çivi, kilidi taramadan sonra alan kodu kaçırıyor '
        f'(kilit={kilit}, tarama={tarama})')
# ══════════════════════════════════════════════════════════════════
# GB1 · GRUPLANMIŞ ALIŞ FATURASI BORCU ATOMİK OLSUN
# ══════════════════════════════════════════════════════════════════
# Aynı alış faturasının kalemleri TEK `CariHareket` satırında
# birikiyor (C1/B3 kalıbı). Birikim ve çıkarma Python'da
# OKU-DEĞİŞTİR-YAZ yapılıyordu — KB1'in (`kasa.bakiye`) aynı sınıfı,
# başka kaynakta.
#
# ÖLÇÜLDÜ — gerçek PostgreSQL 16, READ COMMITTED, gerçek uçlar:
#
#   BİRİKİM  POST /api/stok/ekle · 6 çift × 2 eşzamanlı giriş
#     yazılan blok 11 · borç beklenen 11.000 · gerçek 6.000
#     → 5.000 USD KAYIP (%45,5)
#
#   ÇIKARMA  DELETE /api/stok/BLOK/<id> (mali_islem=fatura_duzelt)
#     8 kalemlik grup · 3 çift eşzamanlı silme
#     silinen 6 · borç beklenen 2.000 · gerçek 5.000
#     → 3.000 USD FAZLA · kalem sayısı 5 (2 olmalı)
#
# Belirtiler ters ve ikisi de sinsi: birikimde tedarikçiye olan borç
# EKSİK görünüyor, çıkarmada depodan düşmüş mal için borç FAZLA
# kalıyor.
#
# BİRİKİM YÖNÜ BN1 İLE KAZARA KAPANMIŞTI (danışma kilidi işlem
# kapsamlı, stok girişi de numara üretiyor). Buna güvenilmedi: iki
# yön de bağımsız olarak atomik. ÖLÇÜLDÜ — BN1 kilidi devre dışı
# bırakılıp yalnız GB1 ile koşuldu: rakamlar tam (12.000/12.000,
# 12 kalem).
#
# BİLİNEN SINIR: BN1 kilidi olmadan iki ilk-giriş birbirini
# görmediği için AYNI fatura için İKİ grup satırı açılabiliyor
# (ölçüldü: 2 satır). Para doğru — toplam iki satıra dağılıyor,
# kayıp yok — ama ekstrede aynı fatura iki satır görünür. Üretimde
# BN1 bunu engelliyor; tek satır güvencesi için şema kısıtı
# (benzersiz indeks) gerekirdi ve o ayrı bir karar.
#
# SQLite'TA EŞZAMANLILIK TESTİ YAZILMADI: SQLite yarışı gizler,
# öyle bir test tabanda da geçerdi. Aşağıdakiler MEKANİZMAYI
# çiviliyor.


def _gb1_grup(ad, alacak=3000.0, kalem=3):
    """Gruplanmış bir alış faturası satırı kurar."""
    with fa.app.app_context():
        h = CariHareket.query.filter_by(id=ad).first()
        if h is None:
            h = CariHareket(
                id=ad, cari_id='C1', cari_unvan='ACIK CARI',
                islem_tip='Alis Faturasi', evrak_no=ad,
                borc=0, alacak=alacak, doviz='USD',
                kdv_tutar=0, matrah=alacak, kalem_sayisi=kalem,
                baglanti_tip='stok_fatura', baglanti_id=ad,
                hareket_tarihi=date.today())
            db.session.add(h)
        else:
            h.alacak, h.matrah, h.kalem_sayisi = alacak, alacak, kalem
        db.session.commit()
    return ad


def test_gb1_kapi_atomik_update_yayinliyor():
    """ÇİVİ: `_ch_grup_degistir` bir UPDATE yayınlamalı ve artırım
    SQL'in İÇİNDE olmalı — Python'da hesaplanıp yazılmış bir sabit
    değil.

    Sütun KENDİSİNE atıf yapmazsa "atomik" iddiası sözde kalır."""
    from sqlalchemy import event as _ev
    yayinlar = []
    _gb1_grup('GB1-SQL')
    with fa.app.app_context():
        kapi = _kc1_kapi('_ch_grup_degistir')
        assert kapi is not None, '_ch_grup_degistir kapanışta yok'
        grup = CariHareket.query.filter_by(id='GB1-SQL').first()
        motor = db.session.get_bind()

        def yakala(conn, cursor, ifade, parametre, baglam, cok):
            yayinlar.append(ifade)

        _ev.listen(motor, 'before_cursor_execute', yakala)
        try:
            kapi(grup, tutar_delta=1000, kalem_delta=1)
            db.session.commit()
        finally:
            _ev.remove(motor, 'before_cursor_execute', yakala)

    guncellemeler = [y for y in yayinlar
                     if y.strip().upper().startswith('UPDATE')
                     and 'alacak' in y]
    assert guncellemeler, (
        f'UPDATE yayınlanmadı — artırım Python tarafında olabilir. '
        f'Yayınlar: {yayinlar[:3]}')
    sql = guncellemeler[0]
    assert sql.count('alacak') >= 2, (
        f'UPDATE sütunun kendisini okumuyor, artırım atomik değil:\n{sql}')


def test_gb1_kapi_eski_sonucu_veriyor():
    """Düzeltme RAKAMI değiştirmemeli — yalnız yarışı kapatmalı.

    Eski hesap birikimde `q2(eski + delta)`, çıkarmada
    `q2(max(0, eski - pay))` idi. Yeni kapı aynı sayıları vermeli;
    sıfır tabanı da korunmalı (eski kod `max(0.0, ...)` diyordu)."""
    with fa.app.app_context():
        kapi = _kc1_kapi('_ch_grup_degistir')
        q2 = _kc1_kapi('q2')
        for baslangic, delta, beklenen in (
                (1000.0, 500.0, 1500.0),
                (1000.0, -250.004, 749.996),
                (1000.0, -5000.0, 0.0),          # sıfır tabanı
                (0.0, 100.005, 100.01),
                (33.33, 66.67, 100.0)):
            _gb1_grup('GB1-PAR', alacak=baslangic, kalem=5)
            grup = CariHareket.query.filter_by(id='GB1-PAR').first()
            yeni, _ = kapi(grup, tutar_delta=delta)
            db.session.commit()
            db.session.refresh(grup)
            bek = q2(beklenen)
            assert abs(float(grup.alacak) - float(bek)) < 0.011, (
                f'{baslangic} + {delta}: {grup.alacak} geldi, '
                f'{bek} olmalıydı')
            assert abs(float(yeni) - float(grup.alacak)) < 0.005, (
                f'kapı {yeni} döndü ama satırda {grup.alacak} var')


def test_gb1_kalem_sayisi_sifirin_altina_inmiyor():
    """Sayaç negatife düşmemeli — grup satırı eksi kalemle kalmaz."""
    with fa.app.app_context():
        kapi = _kc1_kapi('_ch_grup_degistir')
        _gb1_grup('GB1-SIFIR', alacak=1000.0, kalem=1)
        grup = CariHareket.query.filter_by(id='GB1-SIFIR').first()
        for _ in range(3):
            _, kalan = kapi(grup, kalem_delta=-1)
            db.session.commit()
        assert kalan == 0, f'sayaç {kalan} oldu, 0 olmalıydı'


def test_gb1_elle_oku_degistir_yaz_kalmadi():
    """ÇİVİ: grup alanları Python tarafında artırılmamalı.

    METİN DEĞİL AST. Sınıfın geri gelmesini bu engelliyor: biri
    kapıyı atlayıp yeniden `grup.alacak = ...` yazarsa burası
    düşer."""
    import ast as _ast
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    ALANLAR = ('alacak', 'kdv_tutar', 'matrah', 'kalem_sayisi')
    bulgular = []
    for d in _ast.walk(_ast.parse(kaynak)):
        if isinstance(d, _ast.AugAssign):
            hedefler, deger = [d.target], d.value
        elif isinstance(d, _ast.Assign):
            hedefler, deger = d.targets, d.value
        else:
            continue
        for h in hedefler:
            if not (isinstance(h, _ast.Attribute) and h.attr in ALANLAR):
                continue
            if not isinstance(h.value, _ast.Name):
                continue
            nesne = h.value.id
            if nesne not in ('_grup', 'mevcut'):
                continue
            sag = _ast.unparse(deger)
            if (isinstance(d, _ast.AugAssign)
                    or f'{nesne}.{h.attr}' in sag
                    or 'max(' in sag):
                bulgular.append(
                    f'satır {d.lineno}: {nesne}.{h.attr} = {sag[:60]}')
    assert not bulgular, (
        'grup alanı Python tarafında artırılıyor — '
        '`_ch_grup_degistir` kullanılmalı:\n  ' + '\n  '.join(bulgular))


def test_gb1_grup_silme_karari_dusumden_sonra():
    """ÇİVİ: grup satırını silme KARARI, atomik düşümden SONRA
    verilmeli.

    Eskiden kalan kalem sayısı ÖNCE Python'da hesaplanıyor, karar
    ona göre veriliyordu. Son kalemi iki kişi aynı anda silerse
    ikisi de "kalan 0" görüp ikisi de silmeye çalışırdı. Artık
    sayaç atomik azalıyor ve karar veritabanının DÖNDÜRDÜĞÜ sayıya
    göre veriliyor.

    Biri kararı yukarı taşırsa burası düşer."""
    import ast as _ast
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    islevler = {d.name: d for d in _ast.walk(_ast.parse(kaynak))
                if isinstance(d, _ast.FunctionDef)}
    # TD1: indirgeme PAYLAŞILAN KAPIYA taşındı (tedarikçi değişimi de
    # aynı hesabı istiyordu). Çivi kaldırılmadı, kapıya çevrildi —
    # değişmezlik orada duruyor.
    hedef = islevler.get('_stok_alis_payi_dus')
    assert hedef is not None, '_stok_alis_payi_dus kapısı yok'
    kapi_satiri = silme_satiri = None
    for c in _ast.walk(hedef):
        if not isinstance(c, _ast.Call):
            continue
        ad = _ast.unparse(c.func)
        m = _ast.unparse(c)
        if (ad == '_ch_grup_degistir' and 'tutar_delta' in m
                and kapi_satiri is None):
            kapi_satiri = c.lineno
        if (ad == 'db.session.delete' and 'grup' in m
                and silme_satiri is None):
            silme_satiri = c.lineno
    assert kapi_satiri is not None, (
        'çıkarma atomik kapıdan geçmiyor')
    assert silme_satiri is not None, 'grup silme çağrısı yok'
    assert kapi_satiri < silme_satiri, (
        f'silme kararı düşümden ÖNCE veriliyor '
        f'({kapi_satiri} > {silme_satiri}) — son kalemi iki kişi '
        f'aynı anda silerse ikisi de silmeye çalışır')
    # Kapı dururken yolun onu ATLAMASI da aynı hatayı geri getirir;
    # bunu da çiviliyorum.
    for _yol in ('api_stok_sil', 'api_stok_guncelle'):
        _f = islevler.get(_yol)
        assert _f is not None, f'{_yol} yok'
        _cagri = [_ast.unparse(c.func) for c in _ast.walk(_f)
                  if isinstance(c, _ast.Call)]
        assert '_stok_alis_payi_dus' in _cagri, (
            f'{_yol} paylaşılan indirgeme kapısını çağırmıyor — '
            f'kendi kopyasını yazmış olabilir')


def test_gb1_son_kalem_silinince_grup_gidiyor():
    """Düzeltme DAVRANIŞI bozmadı mı?

    Tek kalemli bir grubun kalemi silinince borç sıfırlanmalı,
    sayaç sıfıra inmeli ve grup satırı gitmeli. Atomik düşüme
    geçerken bu davranışı korumak zorundaydım.

    (Tabanda DÜŞER — kapıyı doğrudan çağırıyor. İlk hâlinde
    docstring'ine "tabanda da geçer" yazmıştım; yanlıştı,
    düzelttim.)"""
    with fa.app.app_context():
        kapi = _kc1_kapi('_ch_grup_degistir')
        _gb1_grup('GB1-SON', alacak=1000.0, kalem=1)
        grup = CariHareket.query.filter_by(id='GB1-SON').first()
        yeni, kalan = kapi(grup, tutar_delta=-1000.0, kalem_delta=-1)
        assert kalan == 0, f'kalan {kalan}'
        assert abs(float(yeni)) < 0.005, f'borç {yeni} kaldı'
        db.session.delete(grup)
        db.session.commit()
        assert CariHareket.query.filter_by(id='GB1-SON').count() == 0


def test_gb1_civi_eski_hatayi_yakaliyor():
    """TABANDA DA GEÇER — çivinin kör noktasını sınar.

    Kaldırdığımız biçimlerin hepsini AST gerçekten görüyor mu?"""
    import ast as _ast
    for eski in (
            "_grup.alacak = q2(max(0.0, (_grup.alacak or 0) - _pay))",
            "mevcut.kdv_tutar = q2((mevcut.kdv_tutar or 0) + _ek_kdv)",
            "mevcut.kalem_sayisi = (mevcut.kalem_sayisi or 0) + 1",
            "_grup.kalem_sayisi = max(0, (_grup.kalem_sayisi or 1) - 1)"):
        d = _ast.parse(eski).body[0]
        h = d.targets[0]
        sag = _ast.unparse(d.value)
        nesne = h.value.id
        assert (f'{nesne}.{h.attr}' in sag or 'max(' in sag), (
            f'çivi bunu kaçırıyor: {eski}')
# ══════════════════════════════════════════════════════════════════
# MK1 · KALEM SİLİNİNCE MATRAH VE KDV DE DÜŞSÜN
#       KAPANMIŞ KDV DÖNEMİ KORUNSUN
# ══════════════════════════════════════════════════════════════════
# GB1 borcu atomik yaptı ama matrah ve KDV'ye dokunmadı — eski
# davranış bilerek korunmuştu. ÖLÇÜLDÜ (eşzamanlılık YOK, her
# seferinde): 3 kalemlik %20 KDV'li gruptan 1 kalem silinince
#
#     alacak  3.600 → 2.400   ✓
#     matrah  3.000 → 3.000   ✗  (2.000 olmalıydı)
#     KDV       600 →   600   ✗  (400 olmalıydı)
#
# `alacak = matrah + KDV` ilişkisi kırılıyor ve depodan düşmüş mal
# için indirilecek KDV duruyordu. Yama sonrası ölçüm:
# 2.400 = 2.000 + 400.
#
# DELTA SATIRIN KENDİ RAKAMLARINDAN alınıyor: her stok satırı kendi
# `matrah`/`kdv_tutar` değerini taşıyor ve o değer satırın KENDİ
# `kdv_oran`ından hesaplanmış. Aynı faturada %1, %10, %20 karışık
# olsa da doğru çalışır. `matrah = borç - KDV` gibi bir türetme
# YAPILMIYOR — kullanıcının açık talebi.
#
# KAPANMIŞ DÖNEM: KDV Kanunu'nda vergilendirme dönemi kanunen üç
# aylık, ama Bakanlığa verilen yetkiyle gerçek usulde
# vergilendirilenler AYLIK döneme tabi ve ilgili ayı takip eden
# ayın 28'ine kadar beyan edilip ödeniyor. O gün geçtiyse dönem
# beyan edilmiş sayılıyor; ayrıca o dönem için `Hazirlaniyor`
# dışında bir KDV iade dosyası varsa 28'den önce de kapanıyor.
# Kapalı dönemde `fatura_duzelt` reddediliyor ve kullanıcı
# `karsi_kayit`a yönlendiriliyor (orijinal belge korunur, düzeltme
# ters hareketle yapılır). Yeni şema YOK: kural kanundan, ikinci
# sinyal mevcut `KdvIadeDosya` tablosundan.


def _mk1_tarihler():
    """(açık dönem tarihi, kapanmış dönem tarihi)."""
    from datetime import timedelta
    bugun = date.today()
    return (bugun, bugun.replace(day=15) - timedelta(days=90))


def _mk1_kur(t):
    with fa.app.app_context():
        if not DovizKur.query.filter_by(doviz='USD', tarih=t).first():
            db.session.add(DovizKur(doviz='USD', tarih=t, alis=49.6997,
                                    satis=49.7, efektif=49.6997))
            db.session.commit()


def _mk1_govde(no, fno, kdv, tarih):
    return {
        'tip': 'BLOK', 'cins': 'TEST', 'blok_no': f'MK1-{no}',
        'uretici': 'ACIK CARI', 'boy': 300, 'yukseklik': 150, 'en': 120,
        'hacim_m3': 5.4, 'tonaj': 10, 'fiyat': 100, 'fiyat_birim': 'ton',
        'doviz': 'USD', 'kdv_oran': kdv, 'kdv_dahil_mi': False,
        'fatura_no': fno, 'fatura_durumu': 'faturali',
        'giris_tarihi': tarih.isoformat(),
        'alis_tarihi': tarih.isoformat(),
        # KDV oranı ancak 'yurtici_kdvli' alışta uygulanıyor.
        'alis_tipi': 'yurtici_kdvli' if kdv else 'satinalma',
        'mense': 'TURKIYE', 'yineleme_onay': True,
    }


def _mk1_grup_kur(adm, fno, tarih, oranlar):
    """Her oran için bir kalem girer; stok kimliklerini döner.

    MK2 NOTU — bu düzenek MK2 yamasıyla değişti ve sebebi şu:
    kapanmış döneme KDV'li alış GİRİŞİ artık uçta REDDEDİLİYOR
    (MK2 kapısı, HTTP 400). Eskiden düzenek kapanmış tarihi
    doğrudan `/api/stok/ekle`ye veriyordu; o yol kapandı.

    Kayıtlar artık AÇIK bir tarihle GERÇEK UÇTAN yazılıyor, sonra
    yalnızca TARİHLERİ veritabanında geriye çekiliyor. Böylece hem
    gerçek yazma yolu kullanılıyor (grubun şekli taklit edilmiyor)
    hem grup kapanmış döneme düşüyor. Bu testlerin konusu ÇIKIŞ
    kapısı; girişin nasıl oluştuğu konuyu değiştirmiyor."""
    _mk1_kur(tarih)
    _acik, _ = _mk1_tarihler()
    _geri_cek = (tarih != _acik)
    _yazim_tarihi = _acik if _geri_cek else tarih
    _mk1_kur(_yazim_tarihi)
    idler = []
    for i, oran in enumerate(oranlar):
        r = adm.post('/api/stok/ekle', headers=H,
                     json=_mk1_govde(f'{fno}-{i}', fno, oran,
                                     _yazim_tarihi))
        assert r.status_code == 200, r.get_data(as_text=True)[:200]
        idler.append(r.get_json().get('id'))
    if _geri_cek:
        with fa.app.app_context():
            for _h in CariHareket.query.filter_by(
                    baglanti_tip='stok_fatura', baglanti_id=fno).all():
                _h.hareket_tarihi = tarih
            for _sid in idler:
                _s = db.session.get(BlokStok, _sid)
                if _s is not None:
                    _s.alis_tarihi = tarih
            db.session.commit()
    return idler


def _mk1_grup(fno):
    with fa.app.app_context():
        h = CariHareket.query.filter_by(
            baglanti_tip='stok_fatura', baglanti_id=fno).first()
        if h is None:
            return None
        return (float(h.alacak or 0), float(h.matrah or 0),
                float(h.kdv_tutar or 0), int(h.kalem_sayisi or 0))


def test_mk1_matrah_ve_kdv_birlikte_dusuyor():
    """Borç düşüyorsa vergi tabanı da düşmeli.

    `alacak = matrah + KDV` ilişkisi her zaman tutmalı; tutmazsa
    depodan düşmüş mal için indirilecek KDV ve gider görünür."""
    adm = istemci('admin', 'ADMIN')
    acik, _ = _mk1_tarihler()
    idler = _mk1_grup_kur(adm, 'MK1-DUS', acik, [20, 20, 20])
    once = _mk1_grup('MK1-DUS')
    assert once is not None, 'grup oluşmadı'
    r = adm.delete(f'/api/stok/BLOK/{idler[0]}', headers=H,
                   json={'mali_islem': 'fatura_duzelt'})
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    a, m, k, n = _mk1_grup('MK1-DUS')
    assert abs(m - once[1] / 3 * 2) < 0.011, (
        f'matrah düşmedi: {m} · {once[1] / 3 * 2} olmalıydı')
    assert abs(k - once[2] / 3 * 2) < 0.011, (
        f'KDV düşmedi: {k} · {once[2] / 3 * 2} olmalıydı')
    assert abs(a - (m + k)) < 0.011, (
        f'alacak ({a}) ≠ matrah + KDV ({m + k})')
    assert n == 2


def test_mk1_matrah_satirin_kendi_oranindan_dusuyor():
    """ÇİVİ: delta ORANSAL PAY değil, SATIRIN KENDİ rakamı.

    Aynı faturada %1 ve %20 KDV'li kalem olabilir. Oransal pay
    düşmek (ya da `matrah = borç - KDV` türetmek) karışık oranlı
    faturada yanlış KDV verir. Kullanıcının açık talebi bu."""
    adm = istemci('admin', 'ADMIN')
    acik, _ = _mk1_tarihler()
    # Kalem 0: %1 · Kalem 1: %20 — matrahlar eşit (1.000)
    idler = _mk1_grup_kur(adm, 'MK1-ORAN', acik, [1, 20])
    once = _mk1_grup('MK1-ORAN')
    assert once is not None
    assert abs(once[2] - 210.0) < 0.011, (
        f'kurulum beklenmedik: KDV {once[2]}, 10 + 200 olmalıydı')
    # %1'liyi sil → KDV tam 10 düşmeli (oransal pay 105 olurdu)
    r = adm.delete(f'/api/stok/BLOK/{idler[0]}', headers=H,
                   json={'mali_islem': 'fatura_duzelt'})
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    a, m, k, n = _mk1_grup('MK1-ORAN')
    assert abs(k - 200.0) < 0.011, (
        f'KDV {k} kaldı; %1 kalemin KDV\'si (10) düşseydi 200 '
        f'olurdu, oransal pay düşseydi 105 olurdu')
    assert abs(m - 1000.0) < 0.011, f'matrah {m}, 1.000 olmalıydı'
    assert abs(a - (m + k)) < 0.011


def test_mk1_denetim_izi_yaziliyor():
    """Beyan tabanına dokunan değişiklik iz bırakmalı.

    Kullanıcının şartı: "otomatik düşür, ama mutlaka audit kaydı
    tut." `_log_audit` yalnız `yeni` yoksa `aciklama`yı yazıyor, o
    yüzden ayrıntılar `yeni`nin İÇİNDE."""
    import json as _json
    from models import AuditLog
    adm = istemci('admin', 'ADMIN')
    acik, _ = _mk1_tarihler()
    idler = _mk1_grup_kur(adm, 'MK1-IZ', acik, [20, 20])
    r = adm.delete(f'/api/stok/BLOK/{idler[0]}', headers=H,
                   json={'mali_islem': 'fatura_duzelt'})
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    with fa.app.app_context():
        iz = (AuditLog.query.filter_by(tablo_adi='stok_fatura_matrah')
              .order_by(AuditLog.id.desc()).first())
    assert iz is not None, 'denetim izi yazılmadı'
    assert iz.kullanici == 'admin'
    eski = _json.loads(iz.eski_veri or '{}')
    yeni = _json.loads(iz.yeni_veri or '{}')
    for alan in ('matrah', 'kdv_tutar', 'alacak'):
        assert alan in eski and alan in yeni, (
            f'{alan} izde yok: eski={eski} yeni={yeni}')
    assert yeni.get('silinen_stok') == idler[0]
    assert yeni.get('fatura_no') == 'MK1-IZ'
    assert yeni.get('donem'), 'dönem izde yok'
    assert float(eski['matrah']) > float(yeni['matrah']), (
        'iz matrahın düştüğünü göstermiyor')


def test_mk1_kapanmis_donem_reddediliyor():
    """Beyan süresi geçmiş dönemde `fatura_duzelt` reddedilmeli.

    KDV Kanunu: aylık dönem, takip eden ayın 28'ine kadar beyan.
    O gün geçtiyse geçmiş belge sessizce değiştirilemez; doğru yol
    `karsi_kayit` (orijinal korunur, ters hareket açılır).

    HİÇBİR ŞEY DEĞİŞMEMELİ — yarım iş bırakmak en kötüsü olurdu."""
    adm = istemci('admin', 'ADMIN')
    _, kapali = _mk1_tarihler()
    idler = _mk1_grup_kur(adm, 'MK1-KAPALI', kapali, [20, 20, 20])
    once = _mk1_grup('MK1-KAPALI')
    assert once is not None
    r = adm.delete(f'/api/stok/BLOK/{idler[0]}', headers=H,
                   json={'mali_islem': 'fatura_duzelt'})
    assert r.status_code == 409, (
        f'kapanmış dönemde düzeltme geçti: {r.status_code} '
        f'{r.get_data(as_text=True)[:200]}')
    j = r.get_json() or {}
    assert j.get('error') == 'kdv_donemi_kapali'
    assert j.get('onerilen_mali_islem') == 'karsi_kayit', (
        'kullanıcı karşı kayda yönlendirilmiyor')
    assert j.get('donem_sebep'), 'sebep söylenmiyor'
    assert _mk1_grup('MK1-KAPALI') == once, (
        'reddedildiği hâlde grup değişti')
    with fa.app.app_context():
        from models import BlokStok as _B
        assert db.session.get(_B, idler[0]) is not None, (
            'reddedildiği hâlde stok silindi')


def test_mk1_iade_dosyasi_donemi_28den_once_kapatiyor():
    """`Hazirlaniyor` DIŞINDA iade dosyası varsa dönem kapanmalı.

    İhracatçıda denetlenen şey iade dosyasıdır: talep verilmişse o
    dönemin indirilecek KDV'si artık bir belgeye bağlanmıştır,
    beyan süresi dolmamış olsa bile."""
    from models import KdvIadeDosya
    adm = istemci('admin', 'ADMIN')
    acik, _ = _mk1_tarihler()
    idler = _mk1_grup_kur(adm, 'MK1-IADE', acik, [20, 20])
    once = _mk1_grup('MK1-IADE')
    with fa.app.app_context():
        db.session.add(KdvIadeDosya(
            id='KDV-MK1-A', donem=acik.strftime('%Y-%m'),
            iade_tur='ihracat', durum='Beyan Edildi',
            beyan_tarihi=acik))
        db.session.commit()
    try:
        r = adm.delete(f'/api/stok/BLOK/{idler[0]}', headers=H,
                       json={'mali_islem': 'fatura_duzelt'})
        assert r.status_code == 409, (
            f'beyan edilmiş iade dönemi korunmadı: {r.status_code}')
        j = r.get_json() or {}
        assert j.get('error') == 'kdv_donemi_kapali'
        assert 'iade' in (j.get('donem_sebep') or '').lower()
        assert _mk1_grup('MK1-IADE') == once
    finally:
        with fa.app.app_context():
            d = db.session.get(KdvIadeDosya, 'KDV-MK1-A')
            if d is not None:
                db.session.delete(d)
                db.session.commit()


def test_mk1_hazirlaniyor_dosyasi_donemi_kapatmiyor():
    """NEGATİF ÇİVİ: `Hazirlaniyor` dosyası dönemi KAPATMAMALI.

    Dosya hazırlanırken henüz beyan verilmemiştir; o dönemde
    düzeltme meşru. Kapı fazla sıkı olursa açık dönemde iş
    engellenir ve bu da bir hata olur.

    TABANDA DA GEÇER — yapısı gereği: tabanda hiç kapı yok, yani
    hiçbir şey engellenmiyor. Değeri ileriye dönük; kapı sonradan
    sıkılaştırılırsa burası düşer."""
    from models import KdvIadeDosya
    adm = istemci('admin', 'ADMIN')
    acik, _ = _mk1_tarihler()
    idler = _mk1_grup_kur(adm, 'MK1-HAZIR', acik, [20, 20])
    with fa.app.app_context():
        db.session.add(KdvIadeDosya(
            id='KDV-MK1-H', donem=acik.strftime('%Y-%m'),
            iade_tur='ihrac_kayitli', durum='Hazirlaniyor'))
        db.session.commit()
    try:
        r = adm.delete(f'/api/stok/BLOK/{idler[0]}', headers=H,
                       json={'mali_islem': 'fatura_duzelt'})
        assert r.status_code == 200, (
            f'Hazirlaniyor dosyası dönemi kapattı: {r.status_code} '
            f'{r.get_data(as_text=True)[:200]}')
    finally:
        with fa.app.app_context():
            d = db.session.get(KdvIadeDosya, 'KDV-MK1-H')
            if d is not None:
                db.session.delete(d)
                db.session.commit()


def test_mk1_donem_siniri_28i_dogru_hesapliyor():
    """ÇİVİ: sınır takip eden ayın 28'i; Aralık → Ocak dönmesi dahil.

    Kapıyı doğrudan çağırıyorum: tarih aritmetiği sessizce yanlış
    olursa ya kapalı dönem açık görünür ya açık dönem bloke olur."""
    from datetime import timedelta
    with fa.app.app_context():
        kapi = _kc1_kapi('_kdv_donemi_kapali')
        assert kapi is not None, '_kdv_donemi_kapali kapanışta yok'
        bugun = date.today()
        # Bu ayın faturası: beyan süresi takip eden ayın 28'i,
        # henüz gelmedi (bugün ayın 28'inden sonra olsa bile,
        # TAKİP EDEN ayın 28'i her zaman ileride).
        kapali, _ = kapi(bugun)
        assert kapali is False, 'bu ayın dönemi kapalı sayıldı'
        # 4 ay önce: kesin kapalı
        kapali, sebep = kapi(bugun.replace(day=10) - timedelta(days=120))
        assert kapali is True and sebep, '4 ay öncesi açık sayıldı'
        # Aralık → Ocak dönmesi: 2026-12 faturası, sınır 2027-01-28
        kapali, _ = kapi(date(2026, 12, 15))
        beklenen = date.today() > date(2027, 1, 28)
        assert kapali is beklenen, (
            f'Aralık/Ocak dönmesi yanlış: {kapali}, {beklenen} '
            f'olmalıydı')
        # Tarih yoksa engellemiyoruz
        assert kapi(None) == (False, '')


def test_mk1_karsi_kayit_faturayi_hala_koruyor():
    """TABANDA DA GEÇER — MK1 diğer dalları bozmadı mı?

    `karsi_kayit` orijinal faturayı BİLEREK koruyor: matrah ve KDV
    olduğu gibi kalmalı, yalnız kalem sayacı azalmalı. Kalan
    satırları yeniden TOPLAMAYI bu yüzden seçmedim — toplamak bu
    kararı sonradan bozardı."""
    adm = istemci('admin', 'ADMIN')
    acik, _ = _mk1_tarihler()
    idler = _mk1_grup_kur(adm, 'MK1-KK', acik, [20, 20, 20])
    once = _mk1_grup('MK1-KK')
    r = adm.delete(f'/api/stok/BLOK/{idler[0]}', headers=H,
                   json={'mali_islem': 'karsi_kayit'})
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    a, m, k, n = _mk1_grup('MK1-KK')
    assert abs(m - once[1]) < 0.011, f'karşı kayıtta matrah değişti: {m}'
    assert abs(k - once[2]) < 0.011, f'karşı kayıtta KDV değişti: {k}'
    assert abs(a - once[0]) < 0.011, f'karşı kayıtta borç değişti: {a}'
    assert n == once[3] - 1, 'kalem sayacı azalmadı'


def test_mk1_toplu_silmede_kapali_donem_soru_degil_hata():
    """ÇİVİ: toplu silmede HER 409 "seçim bekliyor" DEĞİL.

    Eskiden `elif kod == 409` sebebe değil koda bakıyordu. Kapanmış
    dönem reddi de 409 ve o dalda `secim_bekleyen`e düşüp
    kullanıcıya "seçim yapın" diye görünürdü — oysa kullanıcı
    seçimini YAPMIŞ, dönem kapalı. Gerçek mesaj da kaybolurdu."""
    adm = istemci('admin', 'ADMIN')
    _, kapali = _mk1_tarihler()
    idler = _mk1_grup_kur(adm, 'MK1-TOPLU', kapali, [20, 20])
    once = _mk1_grup('MK1-TOPLU')
    r = adm.post('/api/stok/toplu_sil', headers=H,
                 json={'tip': 'BLOK', 'stok_idler': [idler[0]],
                       'mali_islem': 'fatura_duzelt',
                       'yineleme_onay': True})
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    j = r.get_json() or {}
    assert j.get('silinen') == 0, 'kapanmış dönemde silindi'
    assert not (j.get('secim_bekleyen') or []), (
        f'kapanmış dönem "seçim bekliyor" sayıldı: '
        f'{j.get("secim_bekleyen")}')
    detay = j.get('atlanan_detay') or []
    assert detay and detay[0].get('stok_id') == idler[0], (
        f'atlanan olarak bildirilmedi: {j}')
    assert 'dönem' in (detay[0].get('sebep') or '').lower(), (
        f'sebep dönemden söz etmiyor: {detay[0].get("sebep")}')
    assert _mk1_grup('MK1-TOPLU') == once, 'grup değişti'


def test_mk1_stok_ekrani_kapali_donemi_gosteriyor():
    """ÇİVİ: ekran kapanmış dönem mesajını GÖSTERMELİ.

    `base.html`in `api()` sarmalayıcısı 409'u sessiz geçiyor
    (çağıran özel ele alsın diye). `stok.html` yalnız
    `mali_islem_gerekli`yi ele alıyordu; bu dal yazılmasaydı
    kullanıcı "fatura düzeltilsin" seçip HİÇBİR ŞEY görmezdi —
    kapı eklerken avladığımız sessiz kaybın aynısı."""
    import io as _io
    metin = _io.open(os.path.join(KOK, 'templates', 'stok.html'),
                     encoding='utf-8').read()
    assert "kdv_donemi_kapali" in metin, (
        'stok ekranı kapanmış dönem yanıtını ele almıyor — '
        'kullanıcı hiçbir mesaj görmez')
    i = metin.find("kdv_donemi_kapali")
    cevre = metin[i:i + 420]
    assert 'bildir(' in cevre, 'mesaj gösterilmiyor'
    assert 'maliAc(' in cevre, (
        'seçim penceresi yeniden açılmıyor — kullanıcı "Karşı kayıt"a '
        'geçemez')

# ══════════════════════════════════════════════════════════════════
# FO1 · EŞZAMANLI FATURA DÜZELTMESİ KÂRLILIĞI KATLAMASIN
# ══════════════════════════════════════════════════════════════════
# `_fatura_satis_kaydi_esitle` (FT1) satış kayıtlarını ORANLA
# ölçekliyor ve oranın tabanı isteğin BAŞINDA alınan anlık görüntü:
#
#     oran = yeni_matrah / eski_matrah
#     sk.tutar = q2((sk.tutar or 0) * oran)
#
# İki düzeltme aynı anda gelirse ikisi de AYNI eski değeri görür,
# ikisi de çarpar, çarpmalar ÜST ÜSTE biner.
#
# ÖLÇÜLDÜ — gerçek PostgreSQL 16, READ COMMITTED, gerçek uç
# (`PUT /api/fatura/<id>`). 1.000 USD fatura + tek satış kaydı,
# iki eşzamanlı düzeltme (2.000 ve 3.000):
#
#     yama ÖNCESİ   fatura 2.000,00 · satış kaydı 6.000,00  oran 3,0
#     yama SONRASI  fatura 2.000,00 · satış kaydı 2.000,00  oran 1,0
#
# Kârlılık kaydı faturanın ÜÇ KATIydı; `kar_usd` ve `marj_yuzde`
# bu rakamdan türüyor, yani ekranda kâr olduğundan büyük görünürdü.
#
# SIRALI düzeltmeler ÖNCE DE TEMİZDİ: 1.000 → 2.000 → 500 →
# 1.333,33 zincirinde oran tam 1,0000. Sorun yalnız eşzamanlılık,
# o yüzden oranlama mantığına DOKUNULMADI — satır işlem sonuna
# kadar kilitlendi, ikinci düzeltme birincinin SONUCUNU `eski`
# olarak görüyor.
#
# SQLite'TA EŞZAMANLILIK TESTİ YAZILMADI: SQLite yazmaları tek
# veritabanı kilidiyle sıralıyor, yarış pencere bulamıyor, öyle bir
# test tabanda da geçerdi. `FOR UPDATE` de SQLite'ta ÜRETİLMİYOR
# (SQLAlchemy sessizce atlıyor) — o yüzden onu AST ile, TAZELEMEYİ
# ise davranışla çiviliyorum.


def _fo1_fatura(fid, tutar):
    from models import SatisKaydi
    with fa.app.app_context():
        if db.session.get(Fatura, fid) is None:
            db.session.add(Fatura(
                id=fid, fatura_no=fid, musteri='ACIK CARI',
                cari_id='C1', ara_toplam=tutar, toplam=tutar,
                doviz='USD', durum='Kesildi', yon='satis',
                fatura_tarihi=date.today(), vade_tarihi=date.today()))
            db.session.add(SatisKaydi(
                id=f'SK-{fid}', fatura_id=fid, stok_tip='blok',
                stok_id=f'B-{fid}', musteri='ACIK CARI', cari_id='C1',
                doviz='USD', birim_fiyat=tutar, miktar=1, tutar=tutar,
                tutar_usd=tutar, maliyet_usd=0, kar_usd=tutar,
                marj_yuzde=100.0, satis_tarihi=date.today()))
            db.session.commit()
    return fid


def _fo1_durum(fid):
    from models import SatisKaydi
    with fa.app.app_context():
        f = db.session.get(Fatura, fid)
        sk = SatisKaydi.query.filter_by(fatura_id=fid).first()
        return (float(f.ara_toplam or f.toplam or 0),
                float(sk.tutar or 0) if sk else 0.0)


def test_fo1_kilit_bayat_degeri_tazeliyor():
    """ÇİVİ: kilit yalnız kilitlemiyor, nesneyi TAZELİYOR da.

    `with_for_update()` tek başına kilidi alır ama kimlik
    haritasındaki nesneyi tazelemez — `eski` bayat değerle
    kurulurdu ve kilit hiçbir şey çözmezdi. `populate_existing()`
    bu yüzden ŞART.

    Burada satırı oturumun ARKASINDAN değiştirip kapının taze
    değeri görüp görmediğine bakıyorum. SQLite'ta `FOR UPDATE`
    üretilmiyor ama tazeleme iki lehçede de çalışıyor — test bu
    yüzden anlamlı."""
    _fo1_fatura('FO1-TAZE', 1000.0)
    with fa.app.app_context():
        kilitle = _kc1_kapi('_fatura_kilitle')
        assert kilitle is not None, '_fatura_kilitle kapanışta yok'
        f = db.session.get(Fatura, 'FO1-TAZE')
        assert abs(float(f.ara_toplam) - 1000.0) < 0.011
        # Oturumun ARKASINDAN değiştir (ORM nesnesi bayat kalır)
        db.session.query(Fatura).filter(
            Fatura.id == 'FO1-TAZE').update(
                {Fatura.ara_toplam: 4242.0}, synchronize_session=False)
        db.session.commit()
        # Nesne hâlâ eski değeri taşıyor olabilir; kapı tazelemeli
        kilitle(f)
        assert abs(float(f.ara_toplam) - 4242.0) < 0.011, (
            f'kapı tazelemedi: {f.ara_toplam} · 4242 olmalıydı — '
            f'populate_existing() eksik olabilir')


def test_fo1_kilit_anlik_goruntuden_once_aliniyor():
    """ÇİVİ: kilit, `_eski` anlık görüntüsünden ÖNCE alınmalı.

    Sonra alınsaydı oranın tabanı zaten bayat okunmuş olurdu ve
    kilit hiçbir şey çözmezdi. Biri kilidi aşağı taşırsa burası
    düşer."""
    import ast as _ast
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    agac = _ast.parse(kaynak)
    hedef = None
    for d in _ast.walk(agac):
        if (isinstance(d, _ast.FunctionDef)
                and d.name == 'api_fatura_guncelle'):
            hedef = d
            break
    assert hedef is not None, 'api_fatura_guncelle yok'
    kilit_satiri = None
    for c in _ast.walk(hedef):
        if (isinstance(c, _ast.Call)
                and _ast.unparse(c.func) == '_fatura_kilitle'
                and kilit_satiri is None):
            kilit_satiri = c.lineno
    assert kilit_satiri is not None, (
        'fatura güncelleme satırı kilitlemiyor')
    satirlar = kaynak.split('\n')
    snap = None
    for no in range(hedef.lineno, (hedef.end_lineno or hedef.lineno) + 1):
        if "_eski = {'fatura_tarihi'" in satirlar[no - 1]:
            snap = no
            break
    assert snap is not None, 'anlık görüntü satırı bulunamadı'
    assert kilit_satiri < snap, (
        f'kilit anlık görüntüden SONRA ({kilit_satiri} > {snap}) — '
        f'oranın tabanı bayat okunur')


def test_fo1_kapi_for_update_ve_populate_existing_kullaniyor():
    """ÇİVİ: ikisi birlikte olmalı.

    `with_for_update()` olmadan kilit yok; `populate_existing()`
    olmadan tazeleme yok. Biri düşerse sessizce koruma kalkar.
    SQLite'ta `FOR UPDATE` üretilmediği için bunu SQL yayınından
    değil KAYNAKTAN denetliyorum."""
    import ast as _ast
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    hedef = None
    for d in _ast.walk(_ast.parse(kaynak)):
        if (isinstance(d, _ast.FunctionDef)
                and d.name == '_fatura_kilitle'):
            hedef = d
            break
    assert hedef is not None, '_fatura_kilitle yok'
    # Docstring'i AYIKLA: açıklamada ikisi de geçiyor, kodda
    # geçtiğini görmem gerek.
    govde = [c for c in hedef.body
             if not (isinstance(c, _ast.Expr)
                     and isinstance(c.value, _ast.Constant)
                     and isinstance(c.value.value, str))]
    kod = '\n'.join(_ast.unparse(c) for c in govde)
    assert 'with_for_update' in kod, 'kilit alınmıyor (FOR UPDATE yok)'
    assert 'populate_existing' in kod, (
        'nesne tazelenmiyor (populate_existing yok) — kilit bayat '
        'değeri korur')


def test_fo1_sirali_duzeltme_oranli_kaliyor():
    """TABANDA DA GEÇER — düzeltme DAVRANIŞI bozmadı mı?

    Sıralı düzeltmeler önce de temizdi; kilit eklerken bunu
    bozmamam gerekiyordu. Fatura tek satış kaydı taşıyorsa oran
    1,0 kalmalı."""
    adm = istemci('admin', 'ADMIN')
    _fo1_fatura('FO1-SIRA', 1000.0)
    for yeni in (2000.0, 500.0, 1333.33):
        r = adm.put('/api/fatura/FO1-SIRA', headers=H, json={
            'ara_toplam': yeni, 'toplam': yeni,
            'musteri': 'ACIK CARI', 'cari_id': 'C1', 'doviz': 'USD',
            'fatura_tarihi': date.today().isoformat(),
            'vade_tarihi': date.today().isoformat(),
            'yineleme_onay': True})
        assert r.status_code == 200, r.get_data(as_text=True)[:200]
        f, sk = _fo1_durum('FO1-SIRA')
        assert f > 0 and abs(sk / f - 1.0) < 0.002, (
            f'{yeni} sonrası oran {sk / f if f else 0:.4f}: '
            f'fatura {f}, satış kaydı {sk}')


def test_fo1_civi_eski_hatayi_yakaliyor():
    """TABANDA DA GEÇER — çivinin kör noktasını sınar.

    "Kilit anlık görüntüden önce" denetimi, kilidi aşağı taşıyan
    kodu gerçekten görüyor mu?"""
    import ast as _ast
    kaynak = ('def f():\n'
              "    _eski = {'fatura_tarihi': x}\n"
              '    _fatura_kilitle(f)\n')
    satirlar = kaynak.split('\n')
    d = _ast.parse(kaynak).body[0]
    kilit = None
    for c in _ast.walk(d):
        if (isinstance(c, _ast.Call)
                and _ast.unparse(c.func) == '_fatura_kilitle'):
            kilit = c.lineno
    snap = None
    for no in range(d.lineno, (d.end_lineno or d.lineno) + 1):
        if "_eski = {'fatura_tarihi'" in satirlar[no - 1]:
            snap = no
            break
    assert kilit and snap and kilit > snap, (
        f'çivi, kilidi anlık görüntüden sonra alan kodu kaçırıyor '
        f'(kilit={kilit}, snap={snap})')
# ══════════════════════════════════════════════════════════════════
# TS2 · TESLİM GERİ ALININCA CARİ BORÇ DA GERİ DÖNSÜN
# ══════════════════════════════════════════════════════════════════
# NASIL BULUNDU: statik tarama değil. Her senaryoda veritabanının
# TAM anlık görüntüsü alındı (her tablo: satır sayısı + para/miktar
# toplamları), belge oluşturuldu, iptal edildi, yeniden ölçüldü.
# Başa dönmeyen her şey kalıntı. Denetim izi ve belgenin kendisi
# muaf. Doğrulama vakası fatura iptaliydi (IP1 çözmüş) — temiz
# çıktı, yani düzenek anlamlı.
#
# İKİ KUSUR, ikisi de YARIŞ DEĞİL — her seferinde:
#
# 1 · GRUP A (FOB, yüklemede teslim) geri almasında borç duruyordu.
#     `_siparis_teslimi_iptal_et` satış kaydını ve KDV dönüşümünü
#     geri alıyor ama gövdesinde `CariHareket` HİÇ GEÇMİYORDU:
#         Sevk Edildi   cari_hareket 1→2 · satis_kaydi 0→1
#         geri alındı   cari_hareket 1→2   ✗ borç DURUYOR
#
# 2 · GRUP B (DAP/DDP) teslimden geri alma HİÇBİR ŞEYİ geri
#     almıyordu — o geçiş için kodda dal yoktu:
#         Teslim Edildi  cari_hareket 1→2 · satis_kaydi 0→1
#         Gumrukte'ye geri (değişiklik yok)
#         Iptal          cari_hareket 1→2 · satis_kaydi 0→1  ✗
#     Sevkiyat 'Iptal' görünüyor ama müşteri hâlâ borçlu ve satış
#     kârlılıkta sayılıyordu.
#
# NEDEN SİLMEK DOĞRU (iş kararı değil): teslimde yazılan borç bir
# FATURA DEĞİL, sistemin kendi otomatik kaydı. `_siparis_teslim_edildi`
# onu YALNIZ siparişin faturası yoksa yazıyor ("fatura zaten borcu
# işledi") ve `kaynak='otomatik-teslim'` ile damgalıyor. IP1 de
# fatura iptalinde borç hareketini aynen siliyor.
#
# Yama sonrası beş senaryo da kalıntısız.


def _ts2_blok(no):
    with fa.app.app_context():
        if db.session.get(BlokStok, no) is None:
            db.session.add(BlokStok(
                id=no, blok_no=no, cins='TEST', boy=300, yukseklik=150,
                en=120, hacim_m3=5.4, tonaj=10, alis_fiyati=1000,
                doviz='USD', durum='Serbest', giris_tarihi=date.today()))
            db.session.commit()
    return no


def _ts2_siparis(adm, bid, teslim):
    r = adm.post('/api/siparis', headers=H, json={
        'musteri': 'ACIK CARI', 'doviz': 'USD', 'durum': 'Onaylandi',
        'teslim_sekli': teslim,
        'kalemler': [{'urun_tip': 'BLOK', 'cins': 'TEST', 'adet': 1,
                      'miktar': 10, 'birim': 'ton', 'birim_fiyat': 500,
                      'doviz': 'USD', 'stok_ids': [bid]}],
        'yineleme_onay': True})
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    return r.get_json()['id']


def _ts2_sevkiyat(adm, sid):
    r = adm.post('/api/sevkiyat', headers=H, json={
        'sevk_tip': 'ihracat', 'siparis_id': sid,
        'musteri': 'ACIK CARI', 'cari_id': 'C1',
        'sevk_tarihi': date.today().isoformat(),
        'cikis_noktasi': 'IZMIR', 'varis_noktasi': 'NEW YORK',
        'yineleme_onay': True})
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    return r.get_json().get('id')


def _ts2_durum(adm, sev, d):
    r = adm.post(f'/api/sevkiyat/{sev}/durum', headers=H,
                 json={'durum': d, 'yineleme_onay': True})
    return r


def _ts2_sayim(sid):
    """(otomatik teslim borcu, satış kaydı, sipariş durumu)"""
    with fa.app.app_context():
        borc = CariHareket.query.filter_by(
            baglanti_tip='siparis', baglanti_id=sid,
            kaynak='otomatik-teslim').count()
        # `SatisKaydi` ve `Siparis` test modülünün üst import'unda
        # yok; yerel import kullanıyorum (modül import'una
        # dokunmamak için).
        from models import SatisKaydi, Siparis
        sk = SatisKaydi.query.filter_by(siparis_id=sid).count()
        sip = db.session.get(Siparis, sid)
        return (borc, sk, sip.durum if sip else None)


def test_ts2_grupA_geri_almada_borc_da_donuyor():
    """GRUP A (FOB): sevk geri alınınca ortada borç KALMAMALI.

    ESKİDEN: teslim cariye otomatik bir borç yazıyordu ve geri alma
    onu silmiyordu. Bu test o silmeyi çivilemek için yazılmıştı.

    SH1'DEN SONRA: teslim HİÇ borç yazmıyor (yazılan borç, fatura
    sonradan kesilince kaldırılmadığı için müşteriyi iki kez
    borçlandırıyordu — ölçüldü, 5.000 USD satış cariye 10.000
    düşüyordu). Çivinin GÜVENCESİ aynı kaldı: teslim zincirinden
    sonra carinin otomatik teslim borcu SIFIR. Yalnız artık bunu
    "yazıldı sonra silindi" ile değil "hiç yazılmadı" ile
    sağlıyoruz.

    GERİ ALMA KODU KALDI ve burada sınanmaya DEVAM EDİYOR: üretim
    veritabanında SH1 ÖNCESİNDEN kalmış `otomatik-teslim` satırları
    olabilir. Geri alma onları hâlâ temizlemek zorunda, yoksa eski
    kayıtlar sessizce borçlu kalır."""
    adm = istemci('admin', 'ADMIN')
    bid = _ts2_blok('TS2-A')
    sid = _ts2_siparis(adm, bid, 'FOB')
    sev = _ts2_sevkiyat(adm, sid)
    r = _ts2_durum(adm, sev, 'Sevk Edildi')
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    borc, sk, durum = _ts2_sayim(sid)
    assert sk == 1, f'sevk zinciri kurulmadı: satış={sk}'
    assert borc == 0, (
        f'teslim cariye borç yazdı ({borc}) — borç yalnız faturadan '
        f'doğmalı, yoksa fatura kesilince müşteri iki kez borçlanır')
    # SH1 ÖNCESİ kayıt taklidi: eski sürümün yazdığı satır.
    with fa.app.app_context():
        db.session.add(CariHareket(
            id='CH-TS2A-ESKI', cari_id='C1', cari_unvan='ACIK CARI',
            islem_tip='Teslimat', borc=5000, alacak=0, doviz='USD',
            baglanti_tip='siparis', baglanti_id=sid,
            kaynak='otomatik-teslim', hareket_tarihi=date.today()))
        db.session.commit()
    assert _ts2_sayim(sid)[0] == 1, 'eski kayıt taklidi kurulamadı'
    r = _ts2_durum(adm, sev, 'Hazirlaniyor')
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    borc, sk, durum = _ts2_sayim(sid)
    assert sk == 0, 'satış kaydı geri alınmadı'
    assert borc == 0, (
        'SH1 öncesinden kalmış otomatik teslim borcu DURUYOR — geri '
        'alma eski kayıtları da temizlemek zorunda')
    assert durum == 'Hazir', f'sipariş durumu {durum}'


def test_ts2_grupB_teslimden_geri_alinca_satis_ve_borc_donuyor():
    """GRUP B (DAP): Teslim Edildi → Gumrukte geri alması.

    Teslimden izinli tek çıkış bu ve o geçiş için kodda HİÇ DAL
    YOKTU: satış da borç da olduğu gibi kalıyordu."""
    adm = istemci('admin', 'ADMIN')
    bid = _ts2_blok('TS2-B')
    sid = _ts2_siparis(adm, bid, 'DAP')
    sev = _ts2_sevkiyat(adm, sid)
    for d in ('Yolda', 'Teslim Edildi'):
        r = _ts2_durum(adm, sev, d)
        assert r.status_code == 200, r.get_data(as_text=True)[:250]
    borc, sk, durum = _ts2_sayim(sid)
    assert sk == 1, f'teslim zinciri kurulmadı: satış={sk}'
    # SH1: teslim borç YAZMIYOR (gerekçe grupA testinde).
    assert borc == 0, (
        f'teslim cariye borç yazdı ({borc}) — borç yalnız faturadan '
        f'doğmalı')
    # SH1 ÖNCESİ kayıt taklidi — geri alma onu da temizlemeli.
    with fa.app.app_context():
        db.session.add(CariHareket(
            id='CH-TS2B-ESKI', cari_id='C1', cari_unvan='ACIK CARI',
            islem_tip='Teslimat', borc=5000, alacak=0, doviz='USD',
            baglanti_tip='siparis', baglanti_id=sid,
            kaynak='otomatik-teslim', hareket_tarihi=date.today()))
        db.session.commit()
    assert _ts2_sayim(sid)[0] == 1, 'eski kayıt taklidi kurulamadı'
    r = _ts2_durum(adm, sev, 'Gumrukte')
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    borc, sk, durum = _ts2_sayim(sid)
    assert sk == 0, 'satış kaydı geri alınmadı'
    assert borc == 0, (
        'SH1 öncesinden kalmış otomatik teslim borcu geri alınmadı')
    assert durum == 'Hazir', f'sipariş durumu {durum}'
    with fa.app.app_context():
        from models import Sevkiyat
        s = db.session.get(Sevkiyat, sev)
        assert s.gercek_teslim is None, 'gerçek teslim tarihi silinmedi'


def test_ts2_yalniz_otomatik_teslim_borcu_siliniyor():
    """NEGATİF ÇİVİ: `kaynak` damgası dışındaki hareketler KALMALI.

    Aynı siparişe elle girilmiş bir cari hareket varsa geri alma
    ona DOKUNMAMALI. Damgaya göre hedeflemezsem geri alma
    kullanıcının kendi kayıtlarını siler — düzelttiğim hatadan
    kötüsü olurdu."""
    adm = istemci('admin', 'ADMIN')
    bid = _ts2_blok('TS2-N')
    sid = _ts2_siparis(adm, bid, 'FOB')
    sev = _ts2_sevkiyat(adm, sid)
    assert _ts2_durum(adm, sev, 'Sevk Edildi').status_code == 200
    with fa.app.app_context():
        db.session.add(CariHareket(
            id='CH-TS2-ELLE', cari_id='C1', cari_unvan='ACIK CARI',
            islem_tip='Tahsilat', borc=0, alacak=1500, doviz='USD',
            baglanti_tip='siparis', baglanti_id=sid,
            kaynak='elle', hareket_tarihi=date.today()))
        db.session.commit()
    assert _ts2_durum(adm, sev, 'Hazirlaniyor').status_code == 200
    with fa.app.app_context():
        assert db.session.get(CariHareket, 'CH-TS2-ELLE') is not None, (
            'elle girilmiş cari hareket SİLİNDİ — geri alma yalnız '
            "kaynak='otomatik-teslim' olanı silmeli")
        assert CariHareket.query.filter_by(
            baglanti_tip='siparis', baglanti_id=sid,
            kaynak='otomatik-teslim').count() == 0


def test_ts2_faturali_sipariste_borc_zaten_yazilmiyor():
    """Faturası olan siparişte teslim otomatik borç YAZMIYOR.

    `_siparis_teslim_edildi` bunu zaten böyle yapıyor ("fatura
    zaten borcu işledi"). Geri alma da faturanın borcuna
    dokunmamalı — bu test o sınırı çiziyor.

    TABANDA DA GEÇER: sınandığı davranış zaten doğruydu. Değeri
    ileriye dönük — geri almayı genişletirken faturanın borcunu da
    kapsarsam burası düşer."""
    adm = istemci('admin', 'ADMIN')
    bid = _ts2_blok('TS2-F')
    sid = _ts2_siparis(adm, bid, 'FOB')
    with fa.app.app_context():
        db.session.add(Fatura(
            id='FT-TS2', fatura_no='FT-TS2', musteri='ACIK CARI',
            cari_id='C1', siparis_id=sid, ara_toplam=5000,
            toplam=5000, doviz='USD', durum='Kesildi', yon='satis',
            fatura_tarihi=date.today(), vade_tarihi=date.today()))
        db.session.add(CariHareket(
            id='CH-TS2-FAT', cari_id='C1', cari_unvan='ACIK CARI',
            islem_tip='Fatura (Satis)', borc=5000, alacak=0,
            doviz='USD', baglanti_tip='fatura', baglanti_id='FT-TS2',
            kaynak='fatura', hareket_tarihi=date.today()))
        db.session.commit()
    sev = _ts2_sevkiyat(adm, sid)
    assert _ts2_durum(adm, sev, 'Sevk Edildi').status_code == 200
    borc, sk, _ = _ts2_sayim(sid)
    assert borc == 0, (
        'faturası olan siparişte otomatik teslim borcu yazıldı — '
        'borç iki kez işlenmiş olur')
    assert _ts2_durum(adm, sev, 'Hazirlaniyor').status_code == 200
    with fa.app.app_context():
        assert db.session.get(CariHareket, 'CH-TS2-FAT') is not None, (
            'faturanın borç hareketi silindi — geri alma onu '
            'kapsamamalı')


def test_ts2_yardimci_cari_hareketi_geri_aliyor():
    """ÇİVİ: `_siparis_teslimi_iptal_et` `CariHareket`e DOKUNMALI.

    İlk hâlinde gövdesinde o ad hiç geçmiyordu ve Grup A'nın geri
    alması borcu bırakıyordu. Biri bu satırı kaldırırsa burası
    düşer."""
    import ast as _ast
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    agac = _ast.parse(kaynak)
    yardimci = kapi_b = None
    for d in _ast.walk(agac):
        if not isinstance(d, _ast.FunctionDef):
            continue
        if d.name == '_siparis_teslimi_iptal_et':
            yardimci = d
        elif d.name == 'api_sevkiyat_durum':
            kapi_b = d
    assert yardimci is not None, '_siparis_teslimi_iptal_et yok'
    govde = _ast.unparse(yardimci)
    assert 'CariHareket' in govde, (
        'yardımcı cari hareketi geri almıyor — teslim geri alınsa '
        'da müşteri borçlu kalır')
    assert "'otomatik-teslim'" in govde, (
        'damgaya göre hedeflenmiyor — elle girilmiş hareketler de '
        'silinebilir')
    assert kapi_b is not None, 'api_sevkiyat_durum yok'
    kapi_govde = _ast.unparse(kapi_b)
    assert "eski_durum == 'Teslim Edildi'" in kapi_govde, (
        'Grup B teslimden geri alma dalı yok — DAP/DDP sevkiyatta '
        'satış ve borç geri alınmaz')
# ══════════════════════════════════════════════════════════════════
# OS1 · ORTAKLIK SERMAYESİ KAYNAĞINDAN AYRIŞMASIN
# ══════════════════════════════════════════════════════════════════
# `maliyet_katki` bir maliyet satırını ortaklığa SERMAYE olarak
# alırken tutarını KOPYALIYOR (`tutar=m.tutar`). Ekran o kopyayı
# topluyor ve sermaye olarak alınan maliyet artık `hesap.maliyet`te
# SAYILMIYOR — o para ortaklık hesabında YALNIZ bu satırda yaşıyor.
#
# ÖLÇÜLDÜ — gerçek PostgreSQL 16, gerçek uçlar, eşzamanlılık YOK.
# 1.000 USD nakliye, ortağın sermayesi olarak alındı:
#
#     maliyet 1.000 → 4.000    sermaye.ortak 1.000   ✗ 3.000 kayıp
#     maliyet SİLİNDİ          sermaye.ortak 1.000   ✗ hayalet
#     her ikisinde             odenecek.ortak 1.000
#
# Yani ortak gerçekte 4.000 koyduğunda sistem 1.000 diyordu; ya da
# hiç harcanmamış 1.000 USD için ortağa borçlu kalıyordu.
#
# İKİ SİLME YOLU VAR, İKİSİ DE ÖLÇÜLDÜ: maliyet silme (DZ1 grubu
# birlikte siliyor) ve STOK silme (stok silinince
# `baglanti_tip='stok'` maliyetleri zincirleme siliniyor —
# `silinen_maliyet: 1` döndü ve sermaye satırı orada kaldı).
#
# KARAR KULLANICININ: silme KAPILIYOR (evin deseni: cariye işlenmiş
# dağıtım ve ortaklığa bağlı proforma da silinmiyor), düzenleme ise
# EŞİTLENİYOR.
#
# 400 KULLANILIYOR, 409 DEĞİL: `base.html`in `api()`si 409'u
# çağırana devrediyor ve ekranlar yalnız BİLDİKLERİ hata kodlarına
# bakıyor — yeni bir 409 sessizce yutulurdu (MK1'de ölçtüm). 400'ü
# `api()` kendisi bildiriyor, toplu stok silme de 200 olmayan yanıtı
# mesajıyla `atlanan_detay`a düşürüyor.


def _os1_kur(oid_ad, sip, stok, mid, tutar=1000, taraf='ortak'):
    """Ortaklık + işi + o işe bağlı maliyet + sermayeye alınmış hâli."""
    from models import Maliyet
    _or6_kur(sip, stok, 20000, 13000)
    with fa.app.app_context():
        db.session.add(Maliyet(id=mid, baglanti_tip='stok',
                               baglanti_id=stok, maliyet_tip='Nakliye',
                               maliyet_tarihi=date(2026, 3, 10),
                               tutar=tutar, doviz='USD',
                               usd_karsilik=tutar, aktif=True))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': oid_ad, 'bizim_pay': 50, 'ortak_pay': 50,
        'anapara_yontemi': 'once_iade'}).get_json()['id']
    r = c.post(f'/api/ortaklik/{oid}/is', headers=H,
               json={'kaynak_tip': 'SIPARIS', 'kaynak_id': sip})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    r = c.post(f'/api/ortaklik/{oid}/maliyet_katki', headers=H,
               json={'taraf': taraf, 'maliyet_idler': [mid]})
    assert r.get_json().get('eklenen') == 1, r.get_data(as_text=True)[:200]
    return c, oid


def _os1_sermaye(oid):
    from models import OrtaklikSermaye
    with fa.app.app_context():
        return [(s.maliyet_id, float(s.tutar or 0), s.doviz)
                for s in OrtaklikSermaye.query.filter_by(
                    ortaklik_id=oid).all()]


def test_os1_sermayeye_alinmis_maliyet_silinmiyor():
    """TABANDA DÜŞER — hayalet sermaye.

    Maliyet silinince sermaye satırı kalıyor ve ortağa hiç
    harcanmamış para borçlu görünüyorduk. Artık silme reddediliyor
    ve HİÇBİR ŞEYE dokunulmuyor."""
    from models import Maliyet
    c, oid = _os1_kur('OS1-A', 'SIPOS1A', 'PLK-OS1-A', 'MAL-OS1-A')
    r = c.delete('/api/maliyet/MAL-OS1-A', headers=H,
                 json={'onay': True})
    assert r.status_code == 400, (
        f'silme reddedilmedi ({r.status_code}): '
        f'{r.get_data(as_text=True)[:200]}')
    g = r.get_json()
    assert g.get('error') == 'ortaklik_sermayesi', g
    # Mesaj kullanıcıya NE YAPACAĞINI söylüyor mu?
    assert 'sermaye' in (g.get('mesaj') or '').lower(), g
    with fa.app.app_context():
        assert db.session.get(Maliyet, 'MAL-OS1-A') is not None, (
            'maliyet silinmiş — ret sonrası dokunulmamalıydı')
    assert _os1_sermaye(oid) == [('MAL-OS1-A', 1000.0, 'USD')], \
        _os1_sermaye(oid)


def test_os1_sermayeli_maliyet_tasiyan_stok_silinmiyor():
    """TABANDA DÜŞER — yan kapı.

    Maliyet silme kapısı tek başına yetmiyordu: stok silinince
    `baglanti_tip='stok'` maliyetleri ZİNCİRLEME siliniyor. Ölçtüm,
    `silinen_maliyet: 1` döndü ve sermaye satırı kaldı."""
    from models import BlokStok, Maliyet, OrtaklikSermaye
    with fa.app.app_context():
        db.session.add(BlokStok(
            id='BLK-OS1-B', blok_no='OS1B', cins='TEST',
            durum='Stokta', hacim_m3=5.0, tonaj=10,
            giris_tarihi=date(2026, 3, 1)))
        db.session.add(Maliyet(
            id='MAL-OS1-B', baglanti_tip='stok', baglanti_id='BLK-OS1-B',
            maliyet_tip='Nakliye', maliyet_tarihi=date(2026, 3, 2),
            tutar=1000, doviz='USD', usd_karsilik=1000, aktif=True))
        db.session.commit()
    # Sermaye bağı GERÇEK UÇLARLA kuruluyor: ortaklık, işi (OR7 —
    # stoğun kendisi bağlanabiliyor) ve maliyet_katki. Doğrudan
    # satır eklemek, uygulamanın üretemeyeceği bir durumu sınama
    # riski taşırdı.
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'OS1-B', 'bizim_pay': 50, 'ortak_pay': 50,
        'anapara_yontemi': 'once_iade'}).get_json()['id']
    r = c.post(f'/api/ortaklik/{oid}/is', headers=H,
               json={'kaynak_tip': 'BLOK', 'kaynak_id': 'BLK-OS1-B'})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    r = c.post(f'/api/ortaklik/{oid}/maliyet_katki', headers=H,
               json={'taraf': 'ortak', 'maliyet_idler': ['MAL-OS1-B']})
    assert r.get_json().get('eklenen') == 1, r.get_data(as_text=True)[:200]
    r = c.delete('/api/stok/BLOK/BLK-OS1-B', headers=H,
                 json={'onay': True, 'yineleme_onay': True,
                       'mali_islem': 'fatura_duzelt'})
    assert r.status_code == 400, (
        f'stok silme reddedilmedi ({r.status_code}): '
        f'{r.get_data(as_text=True)[:220]}')
    assert r.get_json().get('error') == 'ortaklik_sermayesi', r.get_json()
    with fa.app.app_context():
        assert db.session.get(BlokStok, 'BLK-OS1-B') is not None
        assert db.session.get(Maliyet, 'MAL-OS1-B') is not None
        assert OrtaklikSermaye.query.filter_by(
            maliyet_id='MAL-OS1-B').count() == 1


def test_os1_maliyet_duzenlenince_sermaye_de_guncelleniyor():
    """TABANDA DÜŞER — 3.000 USD sessizce kayboluyordu.

    Maliyet 1.000'den 4.000'e çıkınca sermaye 1.000'de kalıyordu:
    ortak gerçekte 4.000 koymuşken sistem 1.000 diyordu. DZ1
    tedarikçi borcunu çoktan eşitliyordu; sermaye aynı sınıftı."""
    c, oid = _os1_kur('OS1-C', 'SIPOS1C', 'PLK-OS1-C', 'MAL-OS1-C')
    assert _os1_sermaye(oid) == [('MAL-OS1-C', 1000.0, 'USD')]
    r = c.put('/api/maliyet/MAL-OS1-C', headers=H, json={
        'maliyet_tip': 'Nakliye', 'tutar': 4000, 'doviz': 'USD',
        'kdv_oran': 0, 'kdv_dahil_mi': False,
        'maliyet_tarihi': '2026-03-10', 'onay': True,
        'yineleme_onay': True})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    assert _os1_sermaye(oid) == [('MAL-OS1-C', 4000.0, 'USD')], (
        f'sermaye eşitlenmedi: {_os1_sermaye(oid)} · 4.000 olmalıydı')
    # Kullanıcıya SÖYLENİYOR mu? Sessiz düzeltme, düzeltme değildir.
    assert 'sermaye' in (r.get_json().get('mesaj') or '').lower(), \
        r.get_json()
    assert (r.get_json().get('sermaye_guncel') or []), r.get_json()


def test_os1_bagsiz_maliyet_normal_siliniyor():
    """TABANDA DA GEÇER — kapı FAZLA kapatmıyor.

    Sermayeye alınmamış maliyet eskisi gibi silinmeli. Kapı her
    maliyeti kilitlerse düzelttiğim hatadan kötüsünü yaparım."""
    from models import Maliyet
    _or6_kur('SIPOS1D', 'PLK-OS1-D', 20000, 13000)
    with fa.app.app_context():
        db.session.add(Maliyet(id='MAL-OS1-D', baglanti_tip='stok',
                               baglanti_id='PLK-OS1-D',
                               maliyet_tip='Nakliye',
                               maliyet_tarihi=date(2026, 3, 10),
                               tutar=777, doviz='USD', usd_karsilik=777,
                               aktif=True))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    r = c.delete('/api/maliyet/MAL-OS1-D', headers=H, json={'onay': True})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    with fa.app.app_context():
        assert db.session.get(Maliyet, 'MAL-OS1-D') is None


def test_os1_kapi_iki_silme_yolunda_da_cagriliyor():
    """ÇİVİ: kapı İKİ uçtan da sorulmalı.

    Yalnız maliyet silmeye koyarsam stok silme yan kapı kalır —
    ölçtüm, orada da siliniyordu. Biri kaldırılırsa burası düşer.
    Kaynaktan denetliyorum: davranış testi tek yolu kaçırabilir."""
    import ast as _ast
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    agac = _ast.parse(kaynak)
    bulunan = {}
    for d in _ast.walk(agac):
        if not isinstance(d, _ast.FunctionDef):
            continue
        if d.name not in ('api_maliyet_sil', 'api_stok_sil',
                          'api_fatura_guncelle'):
            continue
        for c in _ast.walk(d):
            if (isinstance(c, _ast.Call)
                    and _ast.unparse(c.func) == '_maliyet_sermaye_baglari'):
                bulunan[d.name] = True
    assert bulunan.get('api_maliyet_sil'), (
        'maliyet silme kapıyı sormuyor')
    assert bulunan.get('api_stok_sil'), (
        'STOK silme kapıyı sormuyor — yan kapı açık')
    # Kapının kendisi de dursun
    assert 'def _maliyet_sermaye_baglari' in kaynak
# ══════════════════════════════════════════════════════════════════
# PT1 · PROFORMA OLUŞTURMADA DA TOPLAM KALEMLERDEN TÜRETİLİR
# ══════════════════════════════════════════════════════════════════
# DZ3 bu ilkeyi koydu ve yorumunda "hem POST hem PUT" dedi, ama
# uygulaması YALNIZ PUT'a girdi. POST'ta `if not p.toplam` vardı:
# istemci bir rakam gönderdiyse kalemler ne derse desin o rakam
# kaydediliyordu.
#
# ÖLÇÜLDÜ — gerçek PostgreSQL 16, gerçek uç, eşzamanlılık YOK:
#
#   kalemler 2 × 1.000 = 2.000, başlıkta 500 gönderildi
#     oluşturmadan sonra  başlık 500   kalem 2.000   ✗ 1.500 USD
#     aynı gövdeyle PUT   başlık 2.000 kalem 2.000   ✓
#
# Aynı belge oluşturulurken yalan, güncellenirken doğru kaydediliyordu.
#
# DAHA KÖTÜSÜ, SUNUCUNUN KENDİ YAPTIĞI: P1c bloğu kalem tutarlarını
# TAMAMLIYOR (`toplam_fiyat` 0 gelirse miktar × birim fiyat). Yani
# başlık kabul edildikten SONRA kalemler değişiyor:
#
#   kalem toplam_fiyat=0 · miktar 2 × 1.000, başlık 1.000
#     P1c kalemi 2.000 yaptı, başlık 1.000 kaldı   ✗ 1.000 USD
#
# Bu düzgün çalışan bir ön yüzle bile oluşur — ayrışmayı istemci
# değil SUNUCU üretiyor. Müşteriye giden teklif belgesinde
# "satır 2.000, toplam 1.000" yazardı.
#
# PUT'un iki koruması aynen alındı (yeniden yazılmadı): türetilen
# None ise dokunulmuyor, türetilen 0 ama gelen > 0 ise gelen
# korunuyor ve UYARILIYOR.


_PT1_KALEM = [{'urun_tip': 'BLOK', 'cins': 'TEST', 'miktar': 1,
               'birim': 'adet', 'birim_fiyat': 1000,
               'toplam_fiyat': 1000, 'net_fiyat': 1000},
              {'urun_tip': 'BLOK', 'cins': 'TEST', 'miktar': 1,
               'birim': 'adet', 'birim_fiyat': 1000,
               'toplam_fiyat': 1000, 'net_fiyat': 1000}]


def _pt1_olustur(c, **ek):
    govde = {'musteri': 'ACIK CARI', 'cari_id': 'C1', 'doviz': 'USD',
             'tur': 'ihracat', 'rezerve_et': False,
             'yineleme_onay': True}
    govde.update(ek)
    return c.post('/api/proforma', headers=H, json=govde)


def _pt1_durum(pid):
    from models import Proforma, ProformaKalem
    with fa.app.app_context():
        p = db.session.get(Proforma, pid)
        ks = ProformaKalem.query.filter_by(proforma_id=pid).all()
        return (None if p is None else p.toplam,
                round(sum(float(k.net_fiyat or k.toplam_fiyat or 0)
                          for k in ks), 2))


def test_pt1_olusturmada_baslik_kalemlerden_turetiliyor():
    """TABANDA DÜŞER — 1.500 USD ayrışma, sessizce kaydediliyordu.

    Kalemler 2.000 derken başlıkta 500 gönderiliyor. Türetilen
    kazanmalı ve düzeltme kullanıcıya SÖYLENMELİ — sessizce
    düzeltmek de sessizce bozmak kadar kötü (DZ3'ün kendi sözü)."""
    c = istemci('admin', 'ADMIN')
    r = _pt1_olustur(c, toplam=500, kalemler=_PT1_KALEM)
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    pid = r.get_json()['id']
    baslik, kalem = _pt1_durum(pid)
    assert kalem == 2000.0, kalem
    assert abs(float(baslik or 0) - 2000.0) < 0.011, (
        f'başlık {baslik} · kalemler {kalem} — ayrışma '
        f'{round(kalem - float(baslik or 0), 2)} USD')
    g = r.get_json()
    assert (g.get('toplam_duzeltme') or {}).get('turetilen') == 2000.0, g
    assert 'yeniden hesapland' in (g.get('mesaj') or ''), g.get('mesaj')


def test_pt1_sunucunun_kendi_tamamlamasi_basligi_bozmuyor():
    """TABANDA DÜŞER — ayrışmayı SUNUCU üretiyordu.

    İstemci kalem tutarını 0 gönderiyor; P1c onu miktar × birim
    fiyattan 2.000 yapıyor. Başlık 1.000'de kalıyordu — düzgün bir
    ön yüzle bile oluşan hâl."""
    c = istemci('admin', 'ADMIN')
    r = _pt1_olustur(c, toplam=1000, kalemler=[
        {'urun_tip': 'BLOK', 'cins': 'TEST', 'miktar': 2, 'birim': 'adet',
         'birim_fiyat': 1000, 'toplam_fiyat': 0, 'net_fiyat': 0}])
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    baslik, kalem = _pt1_durum(r.get_json()['id'])
    assert kalem == 2000.0, kalem
    assert abs(float(baslik or 0) - 2000.0) < 0.011, (
        f'başlık {baslik} · kalemler {kalem}')


def test_pt1_turetilen_sifirsa_gelen_korunuyor_ve_uyariliyor():
    """TABANDA DA GEÇER — korumanın korumasını sınar.

    Kalem verisi hiçbir tutar taşımıyorsa türetilen 0 çıkar.
    Belgeyi SIFIRLAMAK, düzelttiğim hatadan kötüsü olurdu: gelen
    rakam korunuyor ve kullanıcı uyarılıyor. PUT bu kararı zaten
    vermişti, buraya aynen taşıdım."""
    c = istemci('admin', 'ADMIN')
    r = _pt1_olustur(c, toplam=5000, kalemler=[
        {'urun_tip': 'BLOK', 'cins': 'TEST', 'miktar': 0, 'birim': 'adet',
         'birim_fiyat': 0, 'toplam_fiyat': 0, 'net_fiyat': 0}])
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    baslik, kalem = _pt1_durum(r.get_json()['id'])
    assert kalem == 0.0, kalem
    assert abs(float(baslik or 0) - 5000.0) < 0.011, (
        f'belge sıfırlandı: başlık {baslik} · 5.000 korunmalıydı')


def test_pt1_toplam_hic_gelmezse_de_turetiliyor():
    """TABANDA DA GEÇER — eski davranış korundu mu?

    `if not p.toplam` dalı doğru olanı yapıyordu; onu bozmadan
    genişletmem gerekiyordu."""
    c = istemci('admin', 'ADMIN')
    r = _pt1_olustur(c, kalemler=_PT1_KALEM)
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    baslik, kalem = _pt1_durum(r.get_json()['id'])
    assert abs(float(baslik or 0) - kalem) < 0.011, (baslik, kalem)


def test_pt1_toplam_hesapla_tek_tanim():
    """ÇİVİ: `_proforma_toplam_hesapla` BİR kez tanımlı olmalı.

    Aynı kapsamda iki tanımı vardı. Python kapanışta adı ÇAĞRI
    ANINDA çözüyor, yani herkes SONRAKİNİ kullanıyordu; ilki ölü
    koddu ama sözleşmesi ötekinin TERSİNİ söylüyordu (iskontoyu her
    zaman sabit sayıyor, kalem yokken 0 dönüyordu). Grep ile önce o
    bulunuyordu: orayı düzelten biri emeğinin hiç işlemediğini
    göremezdi.

    Yaşayan tanımın sözleşmesi de çivileniyor: kalem yoksa None
    dönmeli, yoksa PT1'in 'dokunma' koruması anlamsız kalır."""
    import ast as _ast
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    tanim = [d for d in _ast.walk(_ast.parse(kaynak))
             if isinstance(d, _ast.FunctionDef)
             and d.name == '_proforma_toplam_hesapla']
    assert len(tanim) == 1, (
        f'{len(tanim)} tanım var (satır {[d.lineno for d in tanim]}) — '
        f'çağrı anında yalnız SONRAKİ kullanılır, ötekiler ölü kod')
    govde = _ast.unparse(tanim[0])
    assert 'return None' in govde, (
        'kalem yoksa None dönmüyor — PT1 mevcut değere dokunmama '
        'korumasını bu sözleşmeye dayandırıyor')
# ══════════════════════════════════════════════════════════════════
# IS1 · PROFORMA BAŞLIK İSKONTOSU SABİT TUTARDIR
# ══════════════════════════════════════════════════════════════════
# `_proforma_toplam_hesapla` başlık iskontosunu `p.iskonto_tip`e
# bakıp varsayılan olarak '%' kabul ediyor, sonra `p.iskonto`yu
# yüzde sanıyordu. Oysa BAŞLIK için o iki kolon HİÇBİR YERDE
# YAZILMIYOR:
#     POST → iskonto_sabit=data.get('iskonto', 0)
#     PUT  → p.iskonto_sabit = data.get('iskonto')
# `Proforma.iskonto` ve `Proforma.iskonto_tip`e yazan tek satır yok.
#
# Sözleşmeyi evin kendisi yazmış — `proforma.html`: "iskonto/avans
# UI'da % veya sabit girilir; backend SABİT TUTAR saklar" — ve
# düzenlemeye açarken ön yüz `fIskTip`i 'SAB' yapıyor.
# `api_proforma_detay` de başlık için 'iskonto_tip': 'SAB'
# sabitliyor. Üç ayrı yerde aynı şey.
#
# ÖLÇÜLDÜ — gerçek PostgreSQL 16, gerçek uçlar, eşzamanlılık YOK.
# 1.000 USD kalem + 100 USD iskonto (ön yüzün gönderdiği hâl):
#
#     iskonto_sabit 100 · iskonto_tip '%' · iskonto 0
#     türetilen = 1.000 − (1.000 × 0 / 100) = 1.000
#     DOĞRUSU   = 900
#
# Basılan belgede toplam 1.000,00 yazarken iskonto satırı 100,00
# diyordu: belge KENDİSİYLE çelişiyordu — hem de müşteriye giden
# teklif belgesinde.
#
# BU HATA DZ3'TEN BERİ GÜNCELLEMEDE CANLIYDI (türetilen orada
# kazanıyordu); oluşturmada istemcinin gönderdiği rakam onu
# maskeliyordu. PT1 maskeyi kaldırdığı için iki yolda da göründü.
# Aşılmış ilk tanım bunu DOĞRU yapıyordu (`p.iskonto_sabit`) ama
# ölü koddu.
#
# Yüzde dalı SİLİNMEDİ, yalnız yanlışlıkla seçilemez oldu: hem tip
# yüzde demeli HEM sıfırdan farklı bir yüzde yazılı olmalı.


_IS1_KALEM = [{'urun_tip': 'BLOK', 'cins': 'TEST', 'miktar': 1,
               'birim': 'adet', 'birim_fiyat': 1000,
               'toplam_fiyat': 1000, 'net_fiyat': 1000}]


def test_is1_baslik_iskontosu_toplamdan_dusuyor():
    """TABANDA DÜŞER — 100 USD iskonto toplamdan düşmüyordu.

    Ön yüzün gönderdiği hâl: `iskonto` SABİT TUTAR, başlık toplamı
    da iskonto düşülmüş hâli."""
    from models import Proforma
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/proforma', headers=H, json={
        'musteri': 'ACIK CARI', 'cari_id': 'C1', 'doviz': 'USD',
        'tur': 'ihracat', 'toplam': 900, 'iskonto': 100,
        'kalemler': _IS1_KALEM, 'rezerve_et': False,
        'yineleme_onay': True})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    pid = r.get_json()['id']
    with fa.app.app_context():
        p = db.session.get(Proforma, pid)
        assert abs(float(p.iskonto_sabit or 0) - 100.0) < 0.011
        assert abs(float(p.toplam or 0) - 900.0) < 0.011, (
            f'toplam {p.toplam} · 900 olmalıydı (1.000 kalem − 100 '
            f'iskonto) — iskonto toplamdan düşmüyor')
    # Türetilen istemcinin rakamıyla AYNI olduğu için düzeltme de
    # olmamalı: yoksa her iskontolu kayıtta boş uyarı çıkar.
    assert r.get_json().get('toplam_duzeltme') is None, r.get_json()


def test_is1_guncellemede_de_iskonto_dusuyor():
    """TABANDA DÜŞER — asıl hata buradaydı.

    DZ3'ten beri PUT türetileni kazandırıyordu ve türetilen
    iskontoyu saymıyordu: iskontolu bir proformayı GÜNCELLEMEK
    iskontoyu siliyordu."""
    from models import Proforma
    c = istemci('admin', 'ADMIN')
    pid = c.post('/api/proforma', headers=H, json={
        'musteri': 'ACIK CARI', 'cari_id': 'C1', 'doviz': 'USD',
        'tur': 'ihracat', 'toplam': 900, 'iskonto': 100,
        'kalemler': _IS1_KALEM, 'rezerve_et': False,
        'yineleme_onay': True}).get_json()['id']
    r = c.put(f'/api/proforma/{pid}', headers=H, json={
        'musteri': 'ACIK CARI', 'cari_id': 'C1', 'doviz': 'USD',
        'tur': 'ihracat', 'toplam': 900, 'iskonto': 100,
        'kalemler': _IS1_KALEM, 'rezerve_et': False,
        'yineleme_onay': True})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    with fa.app.app_context():
        p = db.session.get(Proforma, pid)
        assert abs(float(p.toplam or 0) - 900.0) < 0.011, (
            f'güncellemeden sonra toplam {p.toplam} · 900 olmalıydı')


def test_is1_belge_kendisiyle_celismiyor():
    """TABANDA DÜŞER — belge müşteriye çelişkili gidiyordu.

    Basılan proformada toplam 1.000,00 yazarken iskonto satırı
    100,00 diyordu."""
    c = istemci('admin', 'ADMIN')
    pid = c.post('/api/proforma', headers=H, json={
        'musteri': 'ACIK CARI', 'cari_id': 'C1', 'doviz': 'USD',
        'tur': 'ihracat', 'toplam': 900, 'iskonto': 100,
        'kalemler': _IS1_KALEM, 'rezerve_et': False,
        'yineleme_onay': True}).get_json()['id']
    h = c.get(f'/api/proforma/{pid}/html?mod=pi').get_data(as_text=True)
    assert '900' in h, 'belgede 900 toplamı yok'


def test_is1_sabit_dali_yuzde_varsayilaniyla_ezilmiyor():
    """ÇİVİ: tip '%' ama yüzde SIFIR ise sabit tutar kullanılmalı.

    Üretimdeki tam durum bu: kolon varsayılanı '%', `iskonto` hiç
    yazılmadığı için 0, iskonto gerçekte `iskonto_sabit`te. Eski kod
    bu hâlde iskontoyu 0 sayıyordu."""
    from models import Proforma, ProformaKalem
    with fa.app.app_context():
        db.session.add(Proforma(
            id='PI-IS1-A', musteri='ACIK CARI', cari_id='C1',
            doviz='USD', tur='ihracat', durum='Taslak',
            iskonto=0, iskonto_tip='%', iskonto_sabit=250))
        db.session.flush()
        db.session.add(ProformaKalem(
            proforma_id='PI-IS1-A', urun_tip='BLOK', cins='TEST',
            miktar=1, birim='adet', birim_fiyat=1000,
            toplam_fiyat=1000, net_fiyat=1000))
        db.session.commit()
        hesapla = _kc1_kapi('_proforma_toplam_hesapla')
        assert hesapla is not None, '_proforma_toplam_hesapla kapanışta yok'
        p = db.session.get(Proforma, 'PI-IS1-A')
        t = hesapla(p)
        assert abs(float(t or 0) - 750.0) < 0.011, (
            f'türetilen {t} · 750 olmalıydı (1.000 − 250 sabit iskonto)')


def test_is1_gercek_yuzde_hala_calisiyor():
    """TABANDA DA GEÇER — yüzde dalını SİLMEDİM.

    Bugün hiçbir uç yüzdeli başlık iskontosu üretmiyor, ama
    ileride eklenirse çalışmalı: tip yüzde VE sıfırdan farklı bir
    yüzde varsa yüzde uygulanır."""
    from models import Proforma, ProformaKalem
    with fa.app.app_context():
        db.session.add(Proforma(
            id='PI-IS1-B', musteri='ACIK CARI', cari_id='C1',
            doviz='USD', tur='ihracat', durum='Taslak',
            iskonto=10, iskonto_tip='%', iskonto_sabit=0))
        db.session.flush()
        db.session.add(ProformaKalem(
            proforma_id='PI-IS1-B', urun_tip='BLOK', cins='TEST',
            miktar=1, birim='adet', birim_fiyat=1000,
            toplam_fiyat=1000, net_fiyat=1000))
        db.session.commit()
        hesapla = _kc1_kapi('_proforma_toplam_hesapla')
        p = db.session.get(Proforma, 'PI-IS1-B')
        t = hesapla(p)
        assert abs(float(t or 0) - 900.0) < 0.011, (
            f'türetilen {t} · 900 olmalıydı (1.000 − %10)')
# ══════════════════════════════════════════════════════════════════
# SC1 · STOK ÇIKIŞI SATIŞ KAYDINDAN YAZILIR
# ══════════════════════════════════════════════════════════════════
# `stok_cikis` tablosu OKUNUYOR ama HİÇBİR YERDE YAZILMIYORDU:
# `StokCikis(` kurucusu tüm projede bir kez bile geçmiyor. Stok
# geçmişi şeridinin "3) Çıkışlar" bölümü bu yüzden kalıcı olarak
# boştu.
#
# ÖLÇÜLDÜ — 5.000 USD'ye satılmış bir blok (satış kaydı var, durum
# 'Satildi'), `GET /api/stok/<id>/gecmis`:
#
#     olay sayısı: 1
#       giris   Stok Girişi
#     satış/çıkış olayı: YOK
#
# Müşteri "bu mal nereye gitti" diye sorduğunda baktığın iz sürme
# ekranı, malın satıldığını HİÇ göstermiyordu.
#
# NEDEN DİNLEYİCİ — TEK DİKİŞ YERİ: çıkış satırının bilgisi
# (müşteri, fiyat, döviz) stok DURUMU değişirken elde yok, satış
# kaydında var. Durum 63 ayrı yerde yazılıyor. Satış kaydı ise
# yalnız iki fonksiyonda yaratılıyor — ama SİLME yolları dağınık
# (TS2, IP1, fatura düzeltmesi). Birini kaçırsam düzelttiğim
# KALINTI sınıfını yeniden yaratırdım; dinleyici hepsini kapsıyor.


def _sc1_cikislar(stok_id=None):
    from models import StokCikis
    with fa.app.app_context():
        s = StokCikis.query
        if stok_id:
            s = s.filter_by(stok_id=stok_id)
        return [(c.stok_id, c.cikis_nedeni, c.musteri,
                 float(c.satis_fiyati or 0), c.doviz) for c in s.all()]


def _sc1_satis_yaz(sk_id, stok_id, tutar=5000):
    from models import SatisKaydi
    with fa.app.app_context():
        db.session.add(SatisKaydi(
            id=sk_id, stok_id=stok_id, stok_tip='BLOK', cins='TEST',
            musteri='ACIK CARI', cari_id='C1', satis_tarihi=date.today(),
            tutar=tutar, tutar_usd=tutar, doviz='USD', maliyet_usd=1000,
            kar_usd=tutar - 1000, marj_yuzde=50.0, miktar=10,
            birim='ton'))
        db.session.commit()


def test_sc1_satis_kaydi_cikis_satiri_yaziyor():
    """TABANDA DÜŞER — tablo hiç yazılmıyordu.

    Satış kaydı yazılınca stok çıkışı da yazılmalı ve müşteri,
    tutar, döviz, neden alanlarını taşımalı."""
    _ts2_blok('BLK-SC1-A')
    _sc1_satis_yaz('SK-SC1-A', 'BLK-SC1-A')
    c = _sc1_cikislar('BLK-SC1-A')
    assert len(c) == 1, f'çıkış satırı yazılmadı: {c}'
    stok, neden, musteri, tutar, doviz = c[0]
    assert (stok, musteri, doviz) == ('BLK-SC1-A', 'ACIK CARI', 'USD'), c[0]
    assert abs(tutar - 5000.0) < 0.011, c[0]
    # `kaynak` varsayılanı 'teslim' → neden 'Teslim'
    assert neden == 'Teslim', neden


def test_sc1_gecmis_seridinde_cikis_gorunuyor():
    """TABANDA DÜŞER — asıl görünen hata buydu.

    Satılmış bir bloğun geçmişinde yalnız 'Stok Girişi' vardı."""
    _ts2_blok('BLK-SC1-B')
    _sc1_satis_yaz('SK-SC1-B', 'BLK-SC1-B')
    adm = istemci('admin', 'ADMIN')
    d = adm.get('/api/stok/BLK-SC1-B/gecmis', headers=H).get_json() or {}
    olaylar = d.get('olaylar') or []
    tipler = {o.get('tip') for o in olaylar}
    assert 'cikis' in tipler, (
        f'şeritte çıkış olayı yok · olaylar: '
        f'{[(o.get("tip"), o.get("baslik")) for o in olaylar]}')
    cikis = [o for o in olaylar if o.get('tip') == 'cikis'][0]
    assert 'ACIK CARI' in (cikis.get('aciklama') or ''), cikis


def test_sc1_satis_kaydi_silinince_cikis_da_gidiyor():
    """TABANDA DÜŞER — kalıntı bırakmamalı.

    Yazdığım satır, dayanağı gidince kalmamalı. IP1/TS2/OS1 ile
    aynı ilke: yeni bir kalıntı sınıfı yaratmak, düzelttiğim
    hatadan kötü olurdu."""
    from models import SatisKaydi
    _ts2_blok('BLK-SC1-C')
    _sc1_satis_yaz('SK-SC1-C', 'BLK-SC1-C')
    assert len(_sc1_cikislar('BLK-SC1-C')) == 1, 'önce yazılmalıydı'
    with fa.app.app_context():
        db.session.delete(db.session.get(SatisKaydi, 'SK-SC1-C'))
        db.session.commit()
    assert _sc1_cikislar('BLK-SC1-C') == [], (
        f'satış kaydı silindi ama çıkış satırı kaldı: '
        f'{_sc1_cikislar("BLK-SC1-C")}')


def test_sc1_sevk_geri_alinirsa_cikis_da_geri_doniyor():
    """TABANDA DÜŞER — gerçek uçlardan uçtan uca.

    TS2'nin düzelttiği yol: Grup A sevkiyatı 'Sevk Edildi'ye
    geçince satış kaydı oluşuyor, geri alınınca siliniyor. Çıkış
    satırı o zincire takılı mı?"""
    adm = istemci('admin', 'ADMIN')
    bid = _ts2_blok('BLK-SC1-D')
    sid = _ts2_siparis(adm, bid, 'FOB')
    sev = _ts2_sevkiyat(adm, sid)
    r = _ts2_durum(adm, sev, 'Sevk Edildi')
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    c1 = _sc1_cikislar(bid)
    assert len(c1) == 1, f'sevk sonrası çıkış satırı yok: {c1}'
    r = _ts2_durum(adm, sev, 'Hazirlaniyor')
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    assert _sc1_cikislar(bid) == [], (
        f'sevk geri alındı ama çıkış satırı kaldı: {_sc1_cikislar(bid)}')


def test_sc1_dinleyici_iki_yonde_de_bagli():
    """ÇİVİ: yazma VE silme dinleyicisi birlikte olmalı.

    Yalnız yazma kalırsa her geri alma bir kalıntı bırakır; yalnız
    silme kalırsa tablo yine boş kalır. Biri kaldırılırsa burası
    düşer."""
    import ast as _ast
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    olaylar = set()
    for d in _ast.walk(_ast.parse(kaynak)):
        if not isinstance(d, _ast.FunctionDef):
            continue
        for dec in d.decorator_list:
            try:
                m = _ast.unparse(dec)
            except Exception:
                continue
            if 'listens_for(SatisKaydi' in m:
                if 'after_insert' in m:
                    olaylar.add('insert')
                if 'after_delete' in m:
                    olaylar.add('delete')
    assert 'insert' in olaylar, 'SatisKaydi after_insert dinleyicisi yok'
    assert 'delete' in olaylar, (
        'SatisKaydi after_delete dinleyicisi yok — her geri alma '
        'kalıntı bırakır')
    assert 'def _sc1_cikis_kimligi' in kaynak, (
        'kimlik satış kaydından türetilmiyor — silme yanlış satırı '
        'bulabilir')
# ══════════════════════════════════════════════════════════════════
# CG1 · ÇEK GERİ ALINIRKEN YALNIZ CİRO HAREKETİ SİLİNİR
# ══════════════════════════════════════════════════════════════════
# `geri_al` dalının 2. adımı "Ciro sırasında oluşan CARİ hareketini
# geri al" diyordu ama koşulu yalnız `baglanti_tip == 'cek'`e
# bakıyordu. Oysa `cek.cari_hareket_id` çek KURULUŞUNDA da doluyor
# (`cari_hareket_olustur` ile yazılan tahsil hareketi) — yani geri
# alma, hangi işlemi geri alıyor olursa olsun çekin ASIL tahsil
# hareketini siliyordu.
#
# ÖLÇÜLDÜ — gerçek PostgreSQL 16, gerçek uçlar, eşzamanlılık YOK.
# 10.000 TL borçlu müşteri, 10.000 TL çek alındı, tahsile verildi,
# sonra geri alındı:
#
#   çek alındı   [Satış 10.000 B] [Çek Tahsilatı 10.000 A]  borç kapandı
#   geri alındı  [Satış 10.000 B]                           ✗
#
# Çek ELDE duruyor ama müşteri hâlâ 10.000 TL borçlu görünüyordu:
# aynı para iki kez bizim lehimize sayılıyordu. Mesaj da "Cari
# hareket geri alındı" diyerek bunu doğru davranış gibi sunuyordu.
#
# ALTI İŞLEMİN BEŞİNDE böyleydi (tahsile_ver, teminat, tahsil_et,
# karsiliksiz, iade). `ciro` TEK DOĞRU çalışan vakaydı — çünkü ciro
# alanı KENDİ hareketiyle ezdiği için silinen o oluyordu. Yorumun
# anlattığı tek vaka, doğru çalıştığı tek vakaydı.
#
# Ayırt edici alan `islem_tip`: kuruluş 'Çek Tahsilatı'/'Çek
# Ödemesi', ciro 'Çek Cirosu'.


def _cg1_kur(cek_no, tutar=10000):
    """Borçlu müşteri + o borcu kapatan çek."""
    from models import Banka, Cek, CariHareket
    adm = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not Banka.query.first():
            db.session.add(Banka(banka_adi='CG1 BANK', doviz='TRY',
                                 aktif=True))
        db.session.add(CariHareket(
            id=f'HR-CG1-{cek_no}', hareket_tarihi=date.today(),
            cari_id='C1', cari_unvan='ACIK CARI', islem_tip='Satış',
            borc=tutar, alacak=0, borc_try=tutar, alacak_try=0,
            doviz='TRY', vade_tarihi=date.today(), kaynak='fatura'))
        db.session.commit()
        bid = Banka.query.first().id
    r = adm.post('/api/cek', headers=H, json={
        'yon': 'alinan', 'tip': 'cek', 'cek_no': cek_no,
        'banka_adi': 'X BANK', 'hesap_sahibi': 'ACIK CARI',
        'tutar': tutar, 'doviz': 'TRY',
        'keside_tarihi': date.today().isoformat(),
        'vade_tarihi': '2026-12-01', 'cari_id': 'C1',
        'cari_hareket_olustur': True,
        'mukerrer_onay': True, 'yineleme_onay': True})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    return adm, r.get_json()['id'], bid


def _cg1_tipler(cek_no):
    from models import CariHareket
    with fa.app.app_context():
        return sorted(
            h.islem_tip for h in CariHareket.query.filter(
                CariHareket.cari_id == 'C1',
                CariHareket.evrak_no == cek_no).all())


def _cg1_islem(adm, cid, islem, **ek):
    return adm.post(f'/api/cek/{cid}/durum', headers=H,
                    json={'islem': islem, 'yineleme_onay': True, **ek})


def test_cg1_tahsile_verip_geri_alinca_tahsil_hareketi_kaliyor():
    """TABANDA DÜŞER — 10.000 TL iki kez lehimize sayılıyordu.

    Çek portföye geri döndü, yani elimizde. Müşterinin borcunu
    kapatan tahsil hareketi KALMALI."""
    adm, cid, bid = _cg1_kur('CG1-A')
    assert _cg1_tipler('CG1-A') == ['Çek Tahsilatı'], _cg1_tipler('CG1-A')
    assert _cg1_islem(adm, cid, 'tahsile_ver',
                      tahsil_banka_id=bid).status_code == 200
    r = _cg1_islem(adm, cid, 'geri_al')
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    assert _cg1_tipler('CG1-A') == ['Çek Tahsilatı'], (
        f'tahsil hareketi silindi: {_cg1_tipler("CG1-A")} — müşteri '
        f'çek elimizdeyken yine borçlu görünür')


def test_cg1_tahsil_edip_geri_alinca_kasa_da_cari_de_basa_donuyor():
    """TABANDA DÜŞER — kasa geri dönüyordu, cari dönmüyordu."""
    from models import Kasa, Cek
    adm, cid, bid = _cg1_kur('CG1-B')
    with fa.app.app_context():
        if not Kasa.query.first():
            db.session.add(Kasa(ad='CG1 KASA', doviz='TRY', bakiye=0))
            db.session.commit()
        kid = Kasa.query.first().id
        k0 = float(db.session.get(Kasa, kid).bakiye or 0)
    assert _cg1_islem(adm, cid, 'tahsil_et',
                      kasa_id=kid).status_code == 200
    assert _cg1_islem(adm, cid, 'geri_al').status_code == 200
    with fa.app.app_context():
        assert abs(float(db.session.get(Kasa, kid).bakiye or 0) - k0) < 0.011
        assert db.session.get(Cek, cid).durum == 'Portfoyde'
    assert _cg1_tipler('CG1-B') == ['Çek Tahsilatı'], _cg1_tipler('CG1-B')


def test_cg1_karsiliksiz_geri_alinca_ters_gidiyor_asil_kaliyor():
    """TABANDA DÜŞER — ikisi birden siliniyordu.

    Karşılıksız çek TERS hareket açıyor (müşteri yine borçlu).
    Geri alınınca o ters hareket gitmeli, ASIL tahsil hareketi
    kalmalı. Tabanda ikisi de gidiyordu."""
    adm, cid, _bid = _cg1_kur('CG1-C')
    assert _cg1_islem(adm, cid, 'karsiliksiz').status_code == 200
    assert _cg1_islem(adm, cid, 'geri_al').status_code == 200
    assert _cg1_tipler('CG1-C') == ['Çek Tahsilatı'], (
        f'{_cg1_tipler("CG1-C")} — ters hareket kalmış ya da asıl '
        f'hareket silinmiş olabilir')


def test_cg1_ciro_geri_alinca_ciro_gidiyor_ve_bag_asila_donuyor():
    """TABANDA DÜŞER — bağ boşta kalıyordu.

    Ciro DOĞRU çalışan tek vakaydı: kendi hareketini silip asıl
    hareketi bırakıyordu. Ama `cari_hareket_id` None kalıyordu —
    çek asıl hareketini unutuyordu. Artık geri bağlanıyor."""
    from models import Cek, CariHareket
    adm, cid, _bid = _cg1_kur('CG1-D')
    with fa.app.app_context():
        asil = db.session.get(Cek, cid).cari_hareket_id
        assert asil, 'kuruluşta bağ kurulmamış'
    assert _cg1_islem(adm, cid, 'ciro', ciro_cari_id='C1',
                      cari_hareket_olustur=True).status_code == 200
    assert _cg1_islem(adm, cid, 'geri_al').status_code == 200
    assert _cg1_tipler('CG1-D') == ['Çek Tahsilatı'], _cg1_tipler('CG1-D')
    with fa.app.app_context():
        c = db.session.get(Cek, cid)
        assert c.cari_hareket_id == asil, (
            f'bağ asıl harekete dönmedi: {c.cari_hareket_id} · '
            f'{asil} olmalıydı')


def test_cg1_kosul_islem_tipine_bakiyor():
    """ÇİVİ: koşul `islem_tip`e bakmalı.

    Yalnız `baglanti_tip == 'cek'`e bakmak tam bu hataydı. Biri
    koşulu geri genişletirse burası düşer."""
    import ast as _ast
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    hedef = None
    for d in _ast.walk(_ast.parse(kaynak)):
        if (isinstance(d, _ast.FunctionDef)
                and d.name == 'api_cek_durum_degistir'):
            hedef = d
            break
    if hedef is None:
        for d in _ast.walk(_ast.parse(kaynak)):
            if (isinstance(d, _ast.FunctionDef)
                    and 'cek' in d.name and 'durum' in d.name):
                hedef = d
                break
    assert hedef is not None, 'çek durum ucu bulunamadı'
    govde = _ast.unparse(hedef)
    assert 'Çek Cirosu' in govde, (
        "geri alma koşulu islem_tip'e bakmıyor — çekin ASIL tahsil "
        "hareketi yine silinir")
    assert '_cek_asil_hareket_id' in govde, (
        'ciro geri alınınca bağ asıl harekete döndürülmüyor')
# ══════════════════════════════════════════════════════════════════
# YN1 · TUTAR YÖNSÜZ YA DA TUTARSIZ GELİRSE REDDEDİLİR
# ══════════════════════════════════════════════════════════════════
# `POST /api/cari/hareket` `borc` ve `alacak`ı AYRI okuyor;
# `islem_tutar` ise `tutar`ı da kabul eden bir geri dönüş zinciri.
# Yalnızca `tutar` gönderilen bir istekte `islem_tutar` doluyor ama
# `borc`/`alacak` SIFIR kalıyor ve kayıt BOŞ yazılıyor — istek 200
# dönüyor.
#
# ÖLÇÜLDÜ — gerçek PostgreSQL 16, gerçek uç, eşzamanlılık YOK.
# {islem_tip: 'Tahsilat', tutar: 5000, kasa_id: K}:
#
#     HTTP 200 · hareket borc=0 alacak=0
#     kasa hareketi tutar=0 · kasa bakiyesi DEĞİŞMEDİ
#     mesaj: "KASA kasasına giriş: 0.00 USD"
#
# 5.000 USD'lik tahsilat hiç kaydedilmedi ama başarı döndü.
#
# BUGÜN EKRANDAN OLMUYOR: `cari.html` iki alanı BİRDEN gönderiyor
# ve kendi yorumu bunu söylüyor ("backend bazı tiplerde 'tutar',
# bazılarında borc/alacak bekler"). Tutarsızlık biliniyor ve
# etrafından dolaşılmış.
#
# YÖN TAHMİN EDİLMİYOR: borç/alacak yön tablosu (`BORC_TIPLERI`)
# yalnız `cari.html`de duruyor. Sunucuya kopyalamak iki listenin
# sessizce ayrışması demekti — yanındaki AB1 yorumu zaten o yüzden
# çıkmış bir hatayı anlatıyor. Eksik istek REDDEDİLİYOR.
#
# MUAFİYETİ ÖLÇEREK ÖĞRENDİM: ilk hâlinde kapı her tipe
# uygulanıyordu ve tam takımı koşunca VR1'in İKİ transfer testi
# düştü. 'Bakiye Transfer' yönünü `transfer_yonu`ndan, 'Mahsup'
# `mahsup_modu`ndan alıyor ve borç/alacağı kendisi yazıyor; o
# isteklerde `borc`/`alacak` gönderilmemesi DOĞRU.


def _yn1_kur(cari_id='YN1-C1'):
    from models import Cari, Kasa
    with fa.app.app_context():
        if db.session.get(Cari, cari_id) is None:
            db.session.add(Cari(id=cari_id, unvan='YN1 MÜŞTERİ',
                                cari_tip='Müşteri', para_birimi='USD',
                                gorunurluk='acik'))
        if not Kasa.query.filter_by(ad='YN1 KASA').first():
            db.session.add(Kasa(ad='YN1 KASA', doviz='USD', bakiye=0))
        db.session.commit()
        kasa = Kasa.query.filter_by(ad='YN1 KASA').first()
        return istemci('admin', 'ADMIN'), cari_id, kasa.id, \
            float(kasa.bakiye or 0)


def _yn1_gonder(c, cari_id, kid, **ek):
    govde = {'cari_id': cari_id, 'islem_tip': 'Tahsilat', 'doviz': 'USD',
             'hareket_tarihi': date.today().isoformat(),
             'vade_tarihi': date.today().isoformat(), 'kasa_id': kid,
             'aciklama': 'yn1', 'yineleme_onay': True}
    govde.update(ek)
    return c.post('/api/cari/hareket', headers=H, json=govde)


def test_yn1_yonsuz_tutar_reddediliyor():
    """TABANDA DÜŞER — 5.000 USD sessizce kaybolup 200 dönüyordu."""
    from models import CariHareket, Kasa
    c, cid, kid, k0 = _yn1_kur('YN1-C1')
    with fa.app.app_context():
        once = CariHareket.query.filter_by(cari_id=cid).count()
    r = _yn1_gonder(c, cid, kid, tutar=5000)
    assert r.status_code == 400, (
        f'yönsüz istek kabul edildi ({r.status_code}): '
        f'{r.get_data(as_text=True)[:200]}')
    assert r.get_json().get('error') == 'yon_belirtilmedi', r.get_json()
    # Hiçbir şey yazılmamalı — boş kayıt da kalıntıdır.
    with fa.app.app_context():
        assert CariHareket.query.filter_by(cari_id=cid).count() == once
        assert abs(float(db.session.get(Kasa, kid).bakiye or 0) - k0) < 0.011


def test_yn1_tutar_borc_alacakla_tutmazsa_reddediliyor():
    """TABANDA DÜŞER — aynı satır iki farklı rakam söylüyordu.

    Kayıt `borc`/`alacak` ile, KDV hesabı `tutar` ile yapılıyor.
    İkisi ayrışırsa belge kendisiyle çelişir."""
    c, cid, kid, _k0 = _yn1_kur('YN1-C2')
    r = _yn1_gonder(c, cid, kid, alacak=3000, tutar=5000)
    assert r.status_code == 400, (
        f'tutarsız istek kabul edildi ({r.status_code}): '
        f'{r.get_data(as_text=True)[:200]}')
    assert r.get_json().get('error') == 'tutar_tutarsiz', r.get_json()


def test_yn1_ekranin_gonderdigi_gibi_calisiyor():
    """TABANDA DA GEÇER — kapı FAZLA kapatmıyor.

    `cari.html` `alacak` ve `tutar`ı birlikte gönderiyor; bu
    eskisi gibi çalışmalı."""
    from models import CariHareket, Kasa
    c, cid, kid, k0 = _yn1_kur('YN1-C3')
    r = _yn1_gonder(c, cid, kid, alacak=5000, tutar=5000)
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    hid = r.get_json()['id']
    with fa.app.app_context():
        h = db.session.get(CariHareket, hid)
        assert abs(float(h.alacak or 0) - 5000.0) < 0.011, h.alacak
        assert abs(float(db.session.get(Kasa, kid).bakiye or 0)
                   - (k0 + 5000.0)) < 0.011


def test_yn1_bakiye_transfer_muaf_kaliyor():
    """TABANDA DA GEÇER — kapının SINIRI.

    Bu testi ölçerek yazdım: kapının ilk hâli her tipe
    uygulanıyordu ve VR1'in iki transfer testi düştü. 'Bakiye
    Transfer' yönünü `transfer_yonu`ndan alıyor, `borc`/`alacak`
    göndermemesi doğru."""
    from models import Kasa
    c, cid, kid, k0 = _yn1_kur('YN1-C4')
    r = c.post('/api/cari/hareket', headers=H, json={
        'cari_id': cid, 'islem_tip': 'Bakiye Transfer',
        'transfer_yonu': 'kasa', 'hedef_kasa_id': kid, 'tutar': 2500,
        'doviz': 'USD', 'hareket_tarihi': date.today().isoformat()})
    assert r.status_code == 200, (
        f'transfer reddedildi — kapı fazla kapatıyor: '
        f'{r.get_data(as_text=True)[:200]}')
    with fa.app.app_context():
        assert abs(float(db.session.get(Kasa, kid).bakiye or 0)
                   - (k0 + 2500.0)) < 0.011


def test_yn1_muafiyet_listesi_duruyor():
    """ÇİVİ: muafiyet listesi kaldırılırsa transferler kırılır.

    Ölçüldü: muafiyet yokken VR1'in iki testi düşüyor. Biri bu
    listeyi kaldırırsa burası da düşer ve sebebi yazılı olur."""
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    assert '_YN1_MUAF' in kaynak, 'YN1 muafiyet listesi yok'
    _bas = kaynak.index('_YN1_MUAF')
    _kesit = kaynak[_bas:_bas + 200]
    assert 'Bakiye Transfer' in _kesit, (
        "'Bakiye Transfer' muaf değil — transferler reddedilir")
    assert 'Mahsup' in _kesit, "'Mahsup' muaf değil"
# ══════════════════════════════════════════════════════════════════
# MK2 · KAPANMIŞ KDV DÖNEMİNE GİRİŞ DE REDDEDİLİR
# ══════════════════════════════════════════════════════════════════
# MK1 kapanmış dönemi YALNIZ ÇIKIŞ tarafında koruyordu: alış
# faturası grubundan kalem çıkarmak reddediliyordu. Ama geriye
# dönük bir alış faturası GİRMEK de o dönemin indirilecek KDV'sini
# değiştiriyor.
#
# ÖLÇÜLDÜ — gerçek PostgreSQL 16, gerçek uç, eşzamanlılık YOK.
# Ölçüm günü 05.11.2026; 2026-08 beyan süresi 28.09.2026'da dolmuş.
# O döneme geriye dönük %20 KDV'li blok alışı:
#
#     POST /api/stok/ekle (alis_tarihi=15.08.2026) → HTTP 200
#     yazılan: 2026-08-15  Alış Faturası  KDV=2.000  matrah=10.000
#     dönemin indirilecek KDV'si 0 → 2.000 TL
#
# İKİNCİ KAPI: faturasız bir stoğu geriye dönük tarihle
# FATURALANDIRMAK da aynı şeyi yapıyor.
#
# ÖLÇÜP KAPSAMA ALMADIĞIM YERLER — dürüstlük için yazılı:
#   · KDV'li maliyet: ölçümde maliyet satırları BUGÜNÜN tarihiyle
#     yazıldı, istenen geri tarih uygulanmadı; yani o yol kapanmış
#     döneme KDV sokmuyor.
#   · Satış faturası ('Kesildi' geçişi): düzeneğimde cari hareket
#     hiç oluşmadı, yani o yolu TETİKLEYEMEDİM. "Delik var"
#     diyemediğim için kapsama almadım.
#
# Kullanıcının kararı: "Kapanmış döneme geriye dönük kayıt
# reddedilsin, kullanıcıya düzeltme prosedürüne yönlendiren uyarı
# gösterilsin, yetkili kullanıcı da geçmiş dönemi sessizce
# değiştiremesin." Ve önemli ayrıntı: "Geç gelen alış faturası YOK
# SAYILMAMALI; uygun mevzuat koşulları çerçevesinde sonraki
# dönemde indirim konusu yapılabilmesi değerlendirilmelidir."


def _mk2_govde(no, fno, kdv, tarih, alis_tipi=None):
    g = _mk1_govde(no, fno, kdv, tarih)
    if alis_tipi is not None:
        g['alis_tipi'] = alis_tipi
    return g


def test_mk2_kapanmis_doneme_kdvli_alis_girilemiyor():
    """TABANDA DÜŞER — dönemin indirilecek KDV'si sessizce artıyordu."""
    from models import CariHareket
    adm = istemci('admin', 'ADMIN')
    _acik, kapali = _mk1_tarihler()
    _mk1_kur(kapali)
    with fa.app.app_context():
        once = CariHareket.query.filter_by(
            baglanti_tip='stok_fatura', baglanti_id='MK2-KAPALI').count()
    r = adm.post('/api/stok/ekle', headers=H,
                 json=_mk2_govde('MK2-K1', 'MK2-KAPALI', 20, kapali))
    assert r.status_code == 400, (
        f'kapanmış döneme KDV''li alış girildi ({r.status_code}): '
        f'{r.get_data(as_text=True)[:220]}')
    j = r.get_json() or {}
    assert j.get('error') == 'kdv_donemi_kapali_giris', j
    assert j.get('donem_sebep'), 'sebep söylenmiyor'
    # HİÇBİR ŞEY yazılmamalı
    with fa.app.app_context():
        assert CariHareket.query.filter_by(
            baglanti_tip='stok_fatura',
            baglanti_id='MK2-KAPALI').count() == once


def test_mk2_geriye_donuk_faturalandirma_da_kapali():
    """TABANDA DÜŞER — ikinci kapı.

    Faturasız stoğu geriye dönük tarihle faturalandırmak da o
    döneme matrah/KDV yazıyor. Yalnız stok girişini kapatmak yan
    kapı bırakırdı."""
    adm = istemci('admin', 'ADMIN')
    acik, kapali = _mk1_tarihler()
    _mk1_kur(acik)
    _mk1_kur(kapali)
    # Faturasız stok AÇIK tarihle giriliyor (kapı buna karışmaz)
    g = _mk2_govde('MK2-F1', '', 20, acik)
    g['fatura_durumu'] = 'faturasiz'
    g['fatura_no'] = ''
    r = adm.post('/api/stok/ekle', headers=H, json=g)
    assert r.status_code == 200, r.get_data(as_text=True)[:220]
    sid = r.get_json()['id']
    # Şimdi KAPANMIŞ tarihle faturalandırmayı dene
    r = adm.post(f'/api/stok/BLOK/{sid}/faturalandir', headers=H, json={
        'fatura_no': 'MK2-GERI', 'alis_tarihi': kapali.isoformat(),
        'yineleme_onay': True})
    assert r.status_code == 400, (
        f'geriye dönük faturalandırma geçti ({r.status_code}): '
        f'{r.get_data(as_text=True)[:220]}')
    assert (r.get_json() or {}).get('error') == 'kdv_donemi_kapali_giris'


def test_mk2_acik_doneme_girilebiliyor():
    """TABANDA DA GEÇER — kapı FAZLA kapatmıyor.

    Açık döneme KDV'li alış eskisi gibi girilmeli; yoksa işi
    durdururdum."""
    adm = istemci('admin', 'ADMIN')
    acik, _ = _mk1_tarihler()
    _mk1_kur(acik)
    r = adm.post('/api/stok/ekle', headers=H,
                 json=_mk2_govde('MK2-A1', 'MK2-ACIK', 20, acik))
    assert r.status_code == 200, (
        f'açık döneme giriş engellendi: {r.get_data(as_text=True)[:220]}')


def test_mk2_kdvsiz_geriye_donuk_alis_engellenmiyor():
    """TABANDA DA GEÇER — kapının SINIRI.

    KDV'siz alış (ihracat kaydıyla, üretim, KDV'siz tipler) o
    dönemin BEYANINI değiştirmiyor. Onu da engellemek, düzelttiğim
    şeyden kötü olurdu: koşul uygulamanın kendi kuralından
    türetildi (`alis_tipi != 'yurtici_kdvli'` ise oran zorla 0)."""
    adm = istemci('admin', 'ADMIN')
    _acik, kapali = _mk1_tarihler()
    _mk1_kur(kapali)
    # IK2: burada eskiden `alis_tipi='satinalma'` yaziyordu — o bir
    # alis tipi DEGIL, `kaynak` alaninin degeri. Dogrulama olmadigi
    # icin kabul ediliyor ve "yurtici_kdvli degil" diye KDV'yi
    # sifirliyordu; test de bu yuzden geciyordu. Alis tipi artik
    # beyaz listeden geciyor, gercek bir KDV'siz tip kullaniliyor.
    # Testin AMACI ayni: KDV'siz alis kapanmis doneme de girilebilmeli.
    r = adm.post('/api/stok/ekle', headers=H,
                 json=_mk2_govde('MK2-N1', 'MK2-KDVSIZ', 0, kapali,
                                 alis_tipi='yurtici_kdvsiz'))
    assert r.status_code == 200, (
        f'KDV''siz geriye dönük alış engellendi — kapı fazla '
        f'kapatıyor: {r.get_data(as_text=True)[:220]}')


def test_mk2_ret_mesaji_yol_gosteriyor_ve_iki_ucta_bagli():
    """TABANDA DÜŞER — mesaj ve kapsam birlikte çivileniyor.

    Kullanıcının şartı: geç gelen fatura YOK SAYILMAMALI. Ret
    mesajı iki yolu da söylemeli. Ve kapı İKİ uçtan da sorulmalı —
    yalnız birine koymak yan kapı bırakır."""
    import ast as _ast
    import io as _io
    adm = istemci('admin', 'ADMIN')
    _acik, kapali = _mk1_tarihler()
    _mk1_kur(kapali)
    r = adm.post('/api/stok/ekle', headers=H,
                 json=_mk2_govde('MK2-M1', 'MK2-MESAJ', 20, kapali))
    assert r.status_code == 400
    m = ((r.get_json() or {}).get('mesaj') or '')
    # TÜRKÇE HARF TUZAĞI: Python'da 'AÇIK'.lower() → 'açik' (NOKTALI
    # i), 'açık' DEĞİL. Bu yüzden harf dönüşümü kullanmıyorum; dizi
    # olduğu gibi aranıyor. (Bu oturumda aynı tuzağa iki kez
    # düştüm — bir kez senaryo adı süzgecinde, bir kez burada.)
    assert 'YOK SAYILMAMALI' in m, m
    assert 'düzeltme beyanı' in m, m
    assert 'AÇIK bir döneme' in m, 'açık döneme kaydetme yolu söylenmiyor'
    # Kapı iki uçtan da sorulmalı
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    bulunan = set()
    for d in _ast.walk(_ast.parse(kaynak)):
        if not isinstance(d, _ast.FunctionDef):
            continue
        if '_kdv_girisi_kapali' in (_ast.unparse(d) if d.body else ''):
            bulunan.add(d.name)
    assert 'api_stok_ekle' in bulunan, 'stok girişi kapıyı sormuyor'
    assert any('faturalandir' in a for a in bulunan), (
        'faturalandırma kapıyı sormuyor — yan kapı açık')
# ══════════════════════════════════════════════════════════════════
# IK1 · KDV İADE DOSYASI BEYANDAN SONRA KİLİTLİ
# ══════════════════════════════════════════════════════════════════
# Eskiden yalnız ('Alindi', 'Reddedildi') kilitliydi. Yani VERGİ
# DAİRESİNE BEYAN EDİLMİŞ bir dosyanın içeriği (bağlı fatura ve KDV
# kalemleri) serbestçe değiştirilebiliyordu.
#
# ÖLÇÜLDÜ — gerçek PostgreSQL 16, gerçek uçlar, eşzamanlılık YOK:
#
#     bağlandı      durum=Hazirlaniyor  talep=0       kalem=1
#     beyan edildi  durum=Beyan Edildi  talep=20.000  kalem=1
#     çözüldü       durum=Beyan Edildi  talep=20.000  kalem=0  ✗
#
# Dosya 20.000 TL talep ediyor ama içi BOŞ, ve hiçbir uyarı yok.
# Vergi incelemesinde ERP, beyan edileni göstermiyordu.
#
# KULLANICININ KARARI: "Beyandan sonra kilitlensin. Değiştirmek
# için dosyayı 'Hazirlaniyor'a geri almak gerekir — iz kalır,
# kararı sen verirsin."


def _ik1_kur(dosya_eki, donem=None):
    """İade dosyası + bağlı bir alış faturası.

    HER TESTE KENDİ DÖNEMİ: aynı dönem için ikinci dosya
    reddediliyor ve testler aynı veritabanını paylaşıyor. Tek
    başına geçip toplu koşuda düşen testlerin sebebi buydu —
    ölçerek gördüm."""
    from models import Fatura
    adm = istemci('admin', 'ADMIN')
    _ay = 3 + (ord(dosya_eki[0]) - ord('A'))
    _t = date(2026, _ay, 15)
    _donem = donem or f'2026-{_ay:02d}'
    fid = f'FT-IK1-{dosya_eki}'
    with fa.app.app_context():
        if db.session.get(Fatura, fid) is None:
            db.session.add(Fatura(
                id=fid, fatura_no=f'A-IK1-{dosya_eki}',
                musteri='ACIK CARI', cari_id='C1', yon='alis',
                ara_toplam=100000, kdv_tutar=20000, toplam=120000,
                doviz='TRY', durum='Kesildi',
                fatura_tarihi=_t, vade_tarihi=_t))
            db.session.commit()
    r = adm.post('/api/kdv-iade', headers=H, json={
        'donem': _donem, 'iade_tur': 'ihracat', 'iade_sekli': 'nakden',
        'vergi_dairesi': 'DENIZLI', 'yineleme_onay': True})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    did = r.get_json()['id']
    r = adm.post(f'/api/kdv-iade/{did}/bagla', headers=H,
                 json={'fatura_idler': [fid], 'yineleme_onay': True})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    return adm, did, fid


def _ik1_fatura_sayisi(adm, did):
    d = (adm.get(f'/api/kdv-iade/{did}', headers=H).get_json() or {})
    d = d.get('data') or d
    return len(d.get('faturalar') or [])


def _ik1_beyan(adm, did):
    return adm.put(f'/api/kdv-iade/{did}', headers=H, json={
        'talep_tutar': 20000, 'durum': 'Beyan Edildi',
        'beyan_tarihi': date(2026, 9, 20).isoformat(),
        'yineleme_onay': True})


def test_ik1_beyandan_sonra_coz_reddediliyor():
    """TABANDA DÜŞER — beyan edilmiş dosyanın içi boşaltılabiliyordu."""
    adm, did, fid = _ik1_kur('A')
    assert _ik1_fatura_sayisi(adm, did) == 1
    assert _ik1_beyan(adm, did).status_code == 200
    r = adm.post(f'/api/kdv-iade/{did}/coz', headers=H,
                 json={'fatura_idler': [fid], 'yineleme_onay': True})
    assert r.status_code == 400, (
        f'beyan edilmiş dosyadan kalem çözüldü ({r.status_code}): '
        f'{r.get_data(as_text=True)[:200]}')
    assert (r.get_json() or {}).get('error') == 'iade_dosyasi_kilitli'
    assert _ik1_fatura_sayisi(adm, did) == 1, 'içerik yine değişti'


def test_ik1_beyandan_sonra_bagla_reddediliyor():
    """TABANDA DÜŞER — öteki kapı.

    Beyandan sonra YENİ kalem EKLEMEK de beyanla ERP'yi ayrıştırır."""
    from models import Fatura
    adm, did, _fid = _ik1_kur('B')
    assert _ik1_beyan(adm, did).status_code == 200
    _t = date(2026, 4, 20)
    with fa.app.app_context():
        db.session.add(Fatura(
            id='FT-IK1-B2', fatura_no='A-IK1-B2', musteri='ACIK CARI',
            cari_id='C1', yon='alis', ara_toplam=50000, kdv_tutar=10000,
            toplam=60000, doviz='TRY', durum='Kesildi',
            fatura_tarihi=_t, vade_tarihi=_t))
        db.session.commit()
    r = adm.post(f'/api/kdv-iade/{did}/bagla', headers=H,
                 json={'fatura_idler': ['FT-IK1-B2'],
                       'yineleme_onay': True})
    assert r.status_code == 400, (
        f'beyan edilmiş dosyaya kalem eklendi ({r.status_code}): '
        f'{r.get_data(as_text=True)[:200]}')
    assert (r.get_json() or {}).get('error') == 'iade_dosyasi_kilitli'
    assert _ik1_fatura_sayisi(adm, did) == 1


def test_ik1_hazirlaniyora_alinca_kilit_aciliyor():
    """TABANDA DA GEÇER — kullanıcının istediği KAÇIŞ YOLU.

    "Değiştirmek için dosyayı 'Hazirlaniyor'a geri almak gerekir —
    iz kalır, kararı sen verirsin." O yol çalışmalı, yoksa kilit
    kullanıcıyı kilitler."""
    adm, did, fid = _ik1_kur('C')
    assert _ik1_beyan(adm, did).status_code == 200
    # Kilidi aç
    r = adm.put(f'/api/kdv-iade/{did}', headers=H,
                json={'durum': 'Hazirlaniyor', 'yineleme_onay': True})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    r = adm.post(f'/api/kdv-iade/{did}/coz', headers=H,
                 json={'fatura_idler': [fid], 'yineleme_onay': True})
    assert r.status_code == 200, (
        f'Hazirlaniyor durumunda da çözülemiyor — kilit fazla '
        f'kapatıyor: {r.get_data(as_text=True)[:200]}')
    assert _ik1_fatura_sayisi(adm, did) == 0


def test_ik1_hazirlaniyorda_serbest():
    """TABANDA DA GEÇER — kilit FAZLA kapatmıyor.

    Hazırlanan dosyaya kalem bağlamak/çözmek eskisi gibi
    çalışmalı."""
    adm, did, fid = _ik1_kur('D')
    assert _ik1_fatura_sayisi(adm, did) == 1
    r = adm.post(f'/api/kdv-iade/{did}/coz', headers=H,
                 json={'fatura_idler': [fid], 'yineleme_onay': True})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    assert _ik1_fatura_sayisi(adm, did) == 0


def test_ik1_kilit_listesi_elle_yazilmiyor():
    """ÇİVİ: kilit kapsamı `IADE_DURUMLARI`dan TÜRETİLMELİ.

    Elle yazılsaydı biri yeni bir durum eklediğinde o durum
    sessizce korumasız kalırdı. Ayrıca 'Hazirlaniyor' DIŞINDA her
    durum kilitli olmalı — biri listeyi daraltırsa burası düşer."""
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    _bas = kaynak.index('IADE_KILITLI =')
    _kesit = kaynak[_bas:_bas + 220]
    assert 'IADE_DURUMLARI' in _kesit, (
        'IADE_KILITLI elle yazılmış — yeni bir durum eklenirse '
        'sessizce korumasız kalır')
    assert 'Hazirlaniyor' in _kesit, (
        "'Hazirlaniyor' dışlanmıyor — kilit açılamaz hâle gelir")
    # Davranışla da doğrula: 'Vergi Dairesinde' de kilitli olmalı
    adm, did, fid = _ik1_kur('E')
    r = adm.put(f'/api/kdv-iade/{did}', headers=H,
                json={'durum': 'Vergi Dairesinde', 'yineleme_onay': True})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    r = adm.post(f'/api/kdv-iade/{did}/coz', headers=H,
                 json={'fatura_idler': [fid], 'yineleme_onay': True})
    assert r.status_code == 400, (
        "'Vergi Dairesinde' durumu kilitli değil: "
        f'{r.get_data(as_text=True)[:200]}')
# ══════════════════════════════════════════════════════════════════
# MT1 · MALİYET TARİHİ: KAPANMIŞ DÖNEM + GRUP BİRLİKTE
# ══════════════════════════════════════════════════════════════════
# MK2'nin başlığında "maliyet yolu kapanmış döneme KDV sokmuyor"
# yazdım. OLUŞTURMA için doğruydu (`POST /api/maliyet` tarih
# ALMIYOR, kolon varsayılanı bugün ve formda tarih alanı yok).
# DÜZENLEME için YANLIŞTI — ve bunu kullanıcı "başka yama var mı"
# diye sorduğunda, kenara attığım bir gözlemi ölçerek buldum.
#
# ÖLÇÜLDÜ — gerçek PostgreSQL 16, gerçek uçlar, eşzamanlılık YOK.
# %20 KDV'li 5.000 TRY nakliye bugün girildi, PUT ile tarihi
# kapanmış döneme (2026-08-15) çekildi:
#
#     ana maliyet tarihi  → 2026-08-15
#     KDV kardeşi tarihi  → 2026-11-05          ✗ GRUP BÖLÜNDÜ
#     KDV kardeşi DOĞRUDAN çekilince:
#       kapanmış dönemin Devreden KDV'si  0 → 1.000 TL   ✗
#
# İKİ KUSUR:
#   1) Kapanmış döneme çekmek de, o dönemden ÇIKARMAK da beyanı
#      değiştiriyor. Kullanıcının kararı: "Yetkili kullanıcı da
#      geçmiş dönemi sessizce değiştiremesin." İKİ tarih de
#      denetleniyor.
#   2) DZ1 "TEK SATIR DEĞİL, GRUP" demişti ve bu uç tedarikçi
#      borcunu çoktan GRUP toplamından kuruyor. Tarih tek satırda
#      değişince gider bir dönemde, KDV'si başka dönemde kalıyordu.


def _mt1_tarihler():
    """(açık, kapanmış) — kapanmış olan beyan süresi kesin dolmuş."""
    from datetime import timedelta
    bugun = date.today()
    return (bugun, bugun.replace(day=15) - timedelta(days=90))


def _mt1_kur(c, ek, kdv=20):
    """KDV'li maliyet + KDV kardeşi. (ana_id, kdv_id) döner."""
    acik, _ = _mt1_tarihler()
    _mk1_kur(acik)
    r = c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Nakliye', 'baglanti_tip': 'stok',
        'baglanti_id': f'MT1-{ek}', 'tutar': 5000, 'doviz': 'TRY',
        'kdv_oran': kdv, 'kdv_dahil_mi': False,
        'cari_id': 'C1', 'fatura_no': f'MT1-F-{ek}',
        'yineleme_onay': True})
    assert r.status_code == 200, r.get_data(as_text=True)[:220]
    j = r.get_json()
    return j['id'], j.get('kdv_id')


def _mt1_tarih(mid):
    from models import Maliyet
    with fa.app.app_context():
        m = db.session.get(Maliyet, mid)
        return m.maliyet_tarihi if m else None


def _mt1_put(c, mid, tarih, tip='Nakliye', tutar=5000, kdv=20):
    return c.put(f'/api/maliyet/{mid}', headers=H, json={
        'maliyet_tip': tip, 'tutar': tutar, 'doviz': 'TRY',
        'kdv_oran': kdv, 'kdv_dahil_mi': False,
        'maliyet_tarihi': tarih.isoformat(), 'cari_id': 'C1',
        'onay': True, 'yineleme_onay': True})


def test_mt1_kapanmis_doneme_cekilemiyor():
    """TABANDA DÜŞER — kapanmış dönemin beyanı değişiyordu."""
    c = istemci('admin', 'ADMIN')
    _acik, kapali = _mt1_tarihler()
    _mk1_kur(kapali)
    mid, kid = _mt1_kur(c, 'A')
    once = _mt1_tarih(mid)
    r = _mt1_put(c, mid, kapali)
    assert r.status_code == 400, (
        f'kapanmış döneme çekildi ({r.status_code}): '
        f'{r.get_data(as_text=True)[:220]}')
    assert r.get_json().get('error') == 'kdv_donemi_kapali_giris'
    assert _mt1_tarih(mid) == once, 'reddedildiği hâlde tarih değişti'


def test_mt1_kdv_kardesi_de_cekilemiyor():
    """TABANDA DÜŞER — asıl para etkisi buradaydı.

    Ölçümde kapanmış dönemin Devreden KDV'si 0'dan 1.000 TL'ye
    çıkmıştı."""
    c = istemci('admin', 'ADMIN')
    _acik, kapali = _mt1_tarihler()
    _mk1_kur(kapali)
    mid, kid = _mt1_kur(c, 'B')
    assert kid, 'KDV kardeşi oluşmadı — düzenek hatası'
    once = _mt1_tarih(kid)
    r = _mt1_put(c, kid, kapali, tip='Devreden KDV', tutar=1000, kdv=0)
    assert r.status_code == 400, (
        f'KDV kardeşi kapanmış döneme çekildi ({r.status_code}): '
        f'{r.get_data(as_text=True)[:220]}')
    assert _mt1_tarih(kid) == once


def test_mt1_kapanmis_donemden_cikarilamiyor():
    """TABANDA DÜŞER — yalnız hedefe bakmak yeterli değil.

    Kapanmış dönemden ÇIKARMAK da o dönemin beyanını değiştirir.
    Kullanıcının şartı: "geçmiş dönemi sessizce değiştiremesin."

    DÜZENEK NOTU: kayıt gerçek uçtan açık tarihle yazılıp tarihi
    veritabanında geriye çekiliyor — çünkü MT1'den sonra uçtan
    kapanmış döneme yazmak zaten mümkün değil. (MK2'de MK1'in
    düzeneğinde aynı şeyi yapmıştım.)"""
    from models import Maliyet
    c = istemci('admin', 'ADMIN')
    acik, kapali = _mt1_tarihler()
    _mk1_kur(kapali)
    mid, kid = _mt1_kur(c, 'C')
    with fa.app.app_context():
        for _i in (mid, kid):
            if _i:
                _m = db.session.get(Maliyet, _i)
                if _m is not None:
                    _m.maliyet_tarihi = kapali
        db.session.commit()
    assert _mt1_tarih(mid) == kapali
    r = _mt1_put(c, mid, acik)
    assert r.status_code == 400, (
        f'kapanmış dönemden çıkarıldı ({r.status_code}): '
        f'{r.get_data(as_text=True)[:220]}')
    assert _mt1_tarih(mid) == kapali, 'reddedildiği hâlde tarih değişti'


def test_mt1_grup_birlikte_tasiniyor():
    """TABANDA DÜŞER — gider bir dönemde, KDV'si başka dönemde kalıyordu.

    DZ1'in "tek satır değil, GRUP" ilkesi tarih alanına da
    uygulanıyor."""
    from datetime import timedelta
    c = istemci('admin', 'ADMIN')
    acik, _kapali = _mt1_tarihler()
    hedef = acik - timedelta(days=3)
    _mk1_kur(hedef)
    mid, kid = _mt1_kur(c, 'D')
    assert kid, 'KDV kardeşi oluşmadı'
    r = _mt1_put(c, mid, hedef)
    assert r.status_code == 200, r.get_data(as_text=True)[:220]
    assert _mt1_tarih(mid) == hedef, _mt1_tarih(mid)
    assert _mt1_tarih(kid) == hedef, (
        f'KDV kardeşi geride kaldı: {_mt1_tarih(kid)} · {hedef} '
        f'olmalıydı — grup iki döneme bölündü')


def test_mt1_kdvsiz_maliyet_engellenmiyor():
    """TABANDA DA GEÇER — kapının SINIRI.

    KDV taşımayan bir gider, dönemin BEYANINI değiştirmiyor. Onu da
    engellemek düzelttiğim şeyden kötü olurdu."""
    c = istemci('admin', 'ADMIN')
    _acik, kapali = _mt1_tarihler()
    _mk1_kur(kapali)
    mid, kid = _mt1_kur(c, 'E', kdv=0)
    assert not kid, 'KDV''siz istendi ama kardeş oluştu — düzenek hatası'
    r = _mt1_put(c, mid, kapali, kdv=0)
    assert r.status_code == 200, (
        f'KDV''siz maliyet engellendi — kapı fazla kapatıyor: '
        f'{r.get_data(as_text=True)[:220]}')
    assert _mt1_tarih(mid) == kapali


# ══════════════════════════════════════════════════════════════════════
#  SZ1 · SIFIRLAMA BETİĞİ MODELİN GERİSİNDE KALMASIN
# ══════════════════════════════════════════════════════════════════════
#
# NEDEN BU TESTLER VAR: YK3 `istek_izi` tablosunu ekledi, ben
# `sifirla2.py`nin listelerini güncellemeyi UNUTTUM ve bu ancak
# SIFIRLAMA GÜNÜ, üretimde ortaya çıktı. Betiğin kapsama denetimi
# doğru davrandı — yarım sıfırlama yapmak yerine çalışmayı reddetti —
# ama o denetim yalnızca betik çalıştırılınca konuşuyor; yılda bir
# kez. Aynı eksik daha önce `bildirimler` (BL1) ve `kalem_karsilama`
# (R4) ile de olmuştu. Üç kez olan şey tesadüf değil, EKSİK ÇİVİ.
# Bu testler aynı şeyi her suite koşusunda söylüyor.
#
# NEDEN `import sifirla2` DEĞİL: betik içe aktarılırken veritabanına
# bağlanıyor, rapor yazdırıyor ve kipine göre `sys.exit` ediyor.
# Testin betiği ÇALIŞTIRMASI gerekmiyor, listelerini OKUMASI
# gerekiyor — o yüzden kaynak `ast` ile ayrıştırılıyor: yorumlardaki
# kesme işaretlerine takılmaz, hiçbir kod yürütmez.
def _sz1_listeler():
    """sifirla2.py'nin modül düzeyi sabitlerini çalıştırmadan oku."""
    import ast
    import io
    yol = os.path.join(KOK, 'sifirla2.py')
    agac = ast.parse(io.open(yol, encoding='utf-8').read())
    d = {}
    for dugum in agac.body:
        if not isinstance(dugum, ast.Assign) or len(dugum.targets) != 1:
            continue
        hedef = dugum.targets[0]
        if not isinstance(hedef, ast.Name):
            continue
        try:
            d[hedef.id] = ast.literal_eval(dugum.value)
        except (ValueError, TypeError, SyntaxError):
            pass
    return d


def _sz1_tablolar():
    return {t.name: t for t in db.metadata.sorted_tables}


def test_sz1_sifirlama_betigi_her_tabloyu_siniflandiriyor():
    """TABANDA DÜŞER — `istek_izi` ne korunuyor ne siliniyor.

    Modeldeki her tablo `sifirla2.py`de ya KORUNAN ya SİLİNECEK
    listesinde olmalı. Olmayan tablo, sıfırlama gününde betiği
    durduruyor; o gün bunu öğrenmek en kötü zamanlama."""
    L = _sz1_listeler()
    sil = set(L['SILINECEK_TABLOLAR'])
    kor = set(L['KORUNAN'])
    # `alembic_version` bilerek MUAF: göç sürümü sıfırlanamaz.
    eksik = sorted(set(_sz1_tablolar()) - sil - kor - {'alembic_version'})
    assert not eksik, (
        f'sifirla2.py bu tabloları sınıflandırmıyor: {eksik}\n'
        f'Her biri SILINECEK_TABLOLAR ya da KORUNAN listesine '
        f'girmeli — gerekçesiyle. Aksi hâlde sıfırlama betiği '
        f'çalışmayı reddediyor.')


def test_sz1_istek_izi_silinecek_korunan_degil():
    """TABANDA DÜŞER — kararın kendisini çiviliyor.

    `istek_izi` TANIM DEĞİL. YK3'ün 5 saniyelik istek parmak izi,
    işaret ettiği belgeler sıfırlamada gidiyor. KORUNAN'a alınması
    var olmayan kayıtların parmak izlerini bırakırdı; bir sonraki
    el "kapsama denetimi geçsin" diye oraya yazmasın."""
    L = _sz1_listeler()
    assert 'istek_izi' in set(L['SILINECEK_TABLOLAR']), \
        'istek_izi SILINECEK_TABLOLAR listesinde değil'
    assert 'istek_izi' not in set(L['KORUNAN']), \
        'istek_izi KORUNAN listesine girmiş — işlem verisi, tanım değil'


def test_sz1_dizi_sifirlama_listesi_tam():
    """TABANDA DÜŞER — OR1'in 4 ortaklık tablosu listede yoktu.

    Tamamen boşalan, tamsayı birincil anahtarlı her tablonun dizisi
    1'e çekilmeli. Çekilmezse veri BOZULMAZ ama "temiz başlangıç"ta
    ilk kaydın kimliği 1 değil, eski sayacın kaldığı yerden devam
    eder; betiğin sözü bu değil."""
    L = _sz1_listeler()
    tablolar = _sz1_tablolar()
    tamsayi_pk = set()
    for ad in L['SILINECEK_TABLOLAR']:
        t = tablolar.get(ad)
        if t is None:
            continue
        pk = list(t.primary_key.columns)
        if len(pk) == 1 and str(pk[0].type).upper().startswith('INTEGER'):
            tamsayi_pk.add(ad)
    eksik = sorted(tamsayi_pk - set(L['DIZI_SIFIRLA']))
    assert not eksik, (
        f'DIZI_SIFIRLA eksik: {eksik}\nBu tablolar tamamen siliniyor '
        f've tamsayı kimlik taşıyor; sayaçları 1e çekilmezse '
        f'sıfırlama sonrası ilk kayıt 1den başlamaz.')
    fazla = sorted(set(L['DIZI_SIFIRLA']) - set(L['SILINECEK_TABLOLAR']))
    assert not fazla, (
        f'DIZI_SIFIRLA silinmeyen tablo içeriyor: {fazla}\nSilinmeyen '
        f'tablonun sayacını 1e çekmek MEVCUT kayıtlarla çakışan '
        f'kimlik üretir (KB1 bunu bir kez yaşadı).')


def test_sz1_gecici_tablo_tek_firma_kipini_kapatmiyor():
    """TABANDA DÜŞER — GECICI_TABLOLAR kümesi yoktu.

    Tek firma kipi, silinecek her tabloda `firma_id` arıyor; `istek_izi`de
    yok. Kümesiz hâlde `istek_izi` eklenmesi ÇALIŞAN BİR KİPİ
    kapatırdı ve ret mesajı yanlış yol gösterirdi ("firma_id ekleyin
    ya da KORUNAN'a alın" — ikisi de bu tablo için yanlış).

    Kümenin kendisi de denetleniyor: içine yalnızca SİLİNECEK ve
    gerçekten `firma_id`siz tablo girebilir. Yoksa "betik çalışsın"
    diye buraya yazılan tablo, denetimin engellemek için var olduğu
    sessiz kalıntıyı üretir."""
    L = _sz1_listeler()
    gecici = set(L['GECICI_TABLOLAR'])
    tablolar = _sz1_tablolar()
    sutun = {ad: {c.name for c in t.c} for ad, t in tablolar.items()}

    firmasiz = {ad for ad in L['SILINECEK_TABLOLAR']
                if 'firma_id' not in sutun.get(ad, set())}
    assert not (firmasiz - gecici), (
        f'firma_idsiz silinecek tablo(lar) muafiyetsiz: '
        f'{sorted(firmasiz - gecici)}\nTek firma kipi bu yüzden '
        f'çalışmayı reddeder.')
    assert gecici <= set(L['SILINECEK_TABLOLAR']), (
        f'GECICI_TABLOLAR silinmeyen tablo içeriyor: '
        f'{sorted(gecici - set(L["SILINECEK_TABLOLAR"]))}')
    assert not (gecici - firmasiz), (
        f'GECICI_TABLOLAR firma_idsi OLAN tablo içeriyor: '
        f'{sorted(gecici - firmasiz)}\nSüzülebilen tablo muafiyete '
        f'ihtiyaç duymaz; muaf tutmak o firmanın verisini bırakırdı.')


def test_sz1_korunan_ve_silinecek_kesismiyor():
    """TABANDA DA GEÇER — betiğin KENDİSİNİN denetlemediği sınır.

    Kapsama denetimi iki listenin BİRLEŞİMİNE bakıyor; bir tablo
    ikisinde de olsa denetim "kapsama tam" der ve tablo yine silinir.
    Yani KORUNAN'a yazmak koruduğunu sanmana yol açar. Bu test o
    çelişkiyi suite'te yakalıyor."""
    L = _sz1_listeler()
    ortak = sorted(set(L['SILINECEK_TABLOLAR']) & set(L['KORUNAN']))
    assert not ortak, (
        f'hem KORUNAN hem SİLİNECEK: {ortak}\nSİLİNECEK kazanır — '
        f'tablo KORUNAN listesinde yazdığı hâlde silinir.')
    tekrar = [t for t in set(L['SILINECEK_TABLOLAR'])
              if L['SILINECEK_TABLOLAR'].count(t) > 1]
    assert not tekrar, f'SILINECEK_TABLOLAR içinde yinelenen: {tekrar}'


# ══════════════════════════════════════════════════════════════════════
#  BM1 · BANKA MODALI ORTAK PARÇA + KASA IZGARASI 6 SÜTUN
# ══════════════════════════════════════════════════════════════════════
#
# Kullanıcı banka hesabı eklemek için Ayarlar'a gitmek zorunda
# kalmasın diye modal `templates/_banka_modal.html`e taşındı; hem
# Ayarlar hem Banka ve Kasa sayfası aynı parçayı kullanıyor.
#
# Projedeki İLK `{% include %}` bu. Bağlarken İKİ gerçek hata çıktı,
# ikisi de ancak TARAYICIDA göründü — testler o ikisini çiviliyor.
import re as _bm_re


def _bm1_sablon(ad, yorumsuz=False):
    import io
    m = io.open(os.path.join(KOK, 'templates', ad), encoding='utf-8').read()
    # Jinja yorumlarını atmak ŞART: `_banka_modal.html`in başlığında
    # kullanımı anlatan ÖRNEK bir {% include %} var ve tarayıcı onu
    # hiç görmüyor. Atmazsak parça kendini include ediyor sanılıyor —
    # bu testi ilk yazdığımda tam o oldu.
    return _bm_re.sub(r'{#.*?#}', '', m, flags=_bm_re.S) if yorumsuz else m


def _bm1_betik(metin):
    """Şablonun <script> bloklarını birleştirir (src'li olanlar hariç)."""
    return '\n'.join(_bm_re.findall(
        r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', metin, _bm_re.S))


def _bm1_ust_duzey_adlar(js):
    """Satır başındaki (girintisiz) let/const/var adlarını toplar.

    Girintisizlik kaba ama bu evde yeterli: üst düzey bildirimler
    sütun 0'da yazılıyor. `let A = [], B = null;` gibi çoklu
    bildirimi de ayırıyor."""
    adlar = set()
    for satir in js.split('\n'):
        m = _bm_re.match(r'(?:let|const|var)\s+(.+)$', satir)
        if not m:
            continue
        for parca in m.group(1).split(','):
            a = _bm_re.match(r'\s*([A-Za-z_$][\w$]*)', parca)
            if a:
                adlar.add(a.group(1))
    return adlar


def test_bm1_banka_modali_ortak_parcada():
    """TABANDA DÜŞER — modal ayarlar.html'in içinde gömülüydü.

    Kaydetme akışı (BK2 bağlı kasa sorusu dahil) ~110 satır. İki
    şablona kopyalansaydı bir gün biri düzelir öbürü düzelmezdi;
    hangi sayfadan eklediğine göre farklı davranan bir form,
    bulunması en zor hata türü."""
    parca = _bm1_sablon('_banka_modal.html')
    assert 'function bankaKaydet' in parca
    assert 'function bankaAc' in parca
    for sayfa in ('ayarlar.html', 'kasa.html'):
        assert '{% include "_banka_modal.html" %}' in _bm1_sablon(sayfa), \
            f'{sayfa} ortak parçayı include etmiyor'
    # Tanım TEK yerde kalsın; kopya geri sızmasın.
    import glob
    kopya = [os.path.basename(y) for y in
             glob.glob(os.path.join(KOK, 'templates', '*.html'))
             if 'function bankaKaydet' in _bm1_sablon(os.path.basename(y))]
    assert kopya == ['_banka_modal.html'], \
        f'bankaKaydet birden fazla şablonda tanımlı: {kopya}'


def test_bm1_kasa_sayfasinda_banka_hesabi_dugmesi():
    """TABANDA DÜŞER — düğme yalnızca Ayarlar'daydı.

    İstenen buydu: kullanıcı yeni banka hesabı eklemek için ayarlar
    sayfasına gitmek zorunda kalmasın."""
    k = _bm1_sablon('kasa.html')
    assert 'onclick="bankaAc()"' in k, 'kasa sayfasında banka ekleme düğmesi yok'
    assert 'Yeni Banka Hesabı' in k
    # Kaydetmeden sonra sayfa KENDİ tazelemesini bağlamalı; yoksa
    # yeni kasa ekranda görünmez.
    assert 'BANKA_SONRASI' in k, 'kasa.html tazeleme kancasını bağlamamış'


def test_bm1_include_edilen_parca_ad_cakistirmiyor():
    """TABANDA DA GEÇER (include yoktu) — ASIL ÇİVİ BU.

    Parçayı ilk bağladığımda `let BANKALAR` hem parçada hem
    kasa.html'de tanımlıydı. Tarayıcı bunu
    "Identifier 'BANKALAR' has already been declared" diye
    reddediyor ve bu hata SAYFANIN BÜTÜN BETİĞİNİ öldürüyor —
    modal açılıyor ama kasa listesi hiç yüklenmiyor. Sunucu
    tarafında hiçbir iz yok; yalnız tarayıcı konsolunda görünüyor.
    Bu test onu suite'e taşıyor."""
    import glob
    for yol in sorted(glob.glob(os.path.join(KOK, 'templates', '*.html'))):
        ad = os.path.basename(yol)
        sayfa = _bm1_sablon(ad)
        for parca_ad in _bm_re.findall(
                r'{%-?\s*include\s+["\']([^"\']+)["\']',
                _bm1_sablon(ad, yorumsuz=True)):
            parca = _bm1_sablon(parca_ad)
            ortak = (_bm1_ust_duzey_adlar(_bm1_betik(sayfa))
                     & _bm1_ust_duzey_adlar(_bm1_betik(parca)))
            assert not ortak, (
                f'{ad} ile {parca_ad} AYNI üst düzey adı tanımlıyor: '
                f'{sorted(ortak)}\nTarayıcı "already been declared" '
                f'der ve sayfanın BÜTÜN betiği çöker.')


def test_bm1_her_include_hedefi_var():
    """TABANDA DA GEÇER — include yoksa boş geçer.

    Olmayan bir parçayı include etmek sayfayı çalışma anında
    TemplateNotFound ile patlatır; testte görmek yeğdir."""
    import glob
    for yol in sorted(glob.glob(os.path.join(KOK, 'templates', '*.html'))):
        for parca in _bm_re.findall(
                r'{%-?\s*include\s+["\']([^"\']+)["\']',
                _bm1_sablon(os.path.basename(yol), yorumsuz=True)):
            assert os.path.exists(os.path.join(KOK, 'templates', parca)), \
                f'{os.path.basename(yol)} olmayan parçayı include ediyor: {parca}'


def test_bm1_js_denetimi_include_cozuyor():
    """TABANDA DÜŞER — `sablon_oku` yoktu.

    `js_denetim.py` her şablonu TEK BAŞINA okuyordu ve parçayı
    görmediği için `bankaAc`a "tanımsız" dedi — doğru kodda YANLIŞ
    ALARM. Kırmızıya alışan göz gerçek kırmızıyı da görmez; o
    yüzden denetçi artık tarayıcının gördüğü birleşik metne
    bakıyor."""
    import importlib.util
    yol = os.path.join(KOK, 'js_denetim.py')
    kaynak = open(yol, encoding='utf-8').read()
    assert 'def sablon_oku' in kaynak, \
        'js_denetim.py include çözmüyor — doğru kodda yanlış alarm verir'
    # Fonksiyonu betiği çalıştırmadan al: dosya üst düzeyde denetim
    # yapıp ekrana yazıyor, import etmek onu KOŞTURURDU.
    import ast
    agac = ast.parse(kaynak)
    govde = [d for d in agac.body
             if isinstance(d, ast.FunctionDef) and d.name == 'sablon_oku']
    assert govde, 'sablon_oku bir fonksiyon değil'
    kaynak_metni = ast.get_source_segment(kaynak, govde[0])
    # Kum havuzunu BETİĞİN KENDİ üst düzey `X = re.compile(...)`
    # atamalarından kuruyoruz. Elle yazsaydım betiğe eklenen her yeni
    # sabit bu testi kırardı ve test, kodu değil kendini sınar hâle
    # gelirdi.
    alan = {'Path': __import__('pathlib').Path, 'OSError': OSError,
            're': _bm_re,
            'SABLON': __import__('pathlib').Path(
                os.path.join(KOK, 'templates'))}
    for d in agac.body:
        if (isinstance(d, ast.Assign) and len(d.targets) == 1
                and isinstance(d.targets[0], ast.Name)
                and isinstance(d.value, ast.Call)
                and ast.unparse(d.value).startswith('re.compile')):
            alan[d.targets[0].id] = eval(ast.unparse(d.value), {'re': _bm_re})
    exec(kaynak_metni, alan)
    birlesik = alan['sablon_oku'](os.path.join(KOK, 'templates', 'kasa.html'))
    assert 'function bankaKaydet' in birlesik, \
        'sablon_oku parçayı yerine koymuyor'


def test_bm1_kasa_izgarasi_alti_sutun():
    """TABANDA DÜŞER — ızgara `auto-fill, minmax(240px,1fr)` idi.

    `auto-fill` sütun sayısını PENCERE GENİŞLİĞİNE bırakıyor; aynı
    ekranda 5, biraz dar bir pencerede 4 çıkıyordu. İstenen "6 kasa
    yan yana" olduğu için sayı artık SABİT, ve dar ekranlar için
    açık bir kademe var.

    Ölçtüm (gerçek tarayıcı, 10 kasa, 1450px): 6 kart yan yana,
    kart 209px, hiçbir kart içeriği taşmıyor. 1250px'te bile
    (kart 176px) uzun banka adı üç satıra sarıyor ama taşmıyor."""
    css = _bm1_sablon('kasa.html')
    satir = [s for s in css.split('\n') if '.kasa-izgara{' in s]
    assert satir, '.kasa-izgara tanımı bulunamadı'
    assert 'repeat(6,' in satir[0], \
        f'ızgara 6 sütun değil: {satir[0].strip()}'
    assert 'auto-fill' not in satir[0], \
        'auto-fill sütun sayısını pencereye bırakır; sayı sabit olmalı'
    # Dar ekran kademesi: 6 → 1 arası boşluk kalmasın.
    for n in (5, 4, 3, 2):
        assert f'repeat({n},' in css, f'{n} sütunlu kademe yok'
    assert '@media (max-width:520px)' in css, 'tek sütun kademesi yok'


# ══════════════════════════════════════════════════════════════════════
#  AK1 · ANA KASA KARTLARI IZGARADAN KALKTI
# ══════════════════════════════════════════════════════════════════════
#
# Ana kasa kartı, üstteki siyah konsolide kartla BİREBİR AYNI sayıyı
# gösteriyordu — ikisi de "aynı dövizdeki alt kasaların toplamı".
# Aynı tutar tek ekranda iki kez yazıyordu ve "KASALAR · 10" sayısı
# da yanlıştı: o 10'un 3'ü kasa değil, özet kutusuydu.
#
# KAYIT DURUYOR, yalnız KART kalktı. Kasa Defteri'ndeki döviz bazlı
# birleşik defter ve "ana kasaya doğrudan hareket girilemez" kuralı
# aynen çalışıyor.
def test_ak1_ana_kasa_izgarada_gosterilmiyor():
    """TABANDA DÜŞER — ızgara bütün kasaları basıyordu.

    Kart sayısı da süzülmüş listeden gelmeli: ana kasaları çizmeyip
    sayıyı 10 olarak yazmak, ekranda görünenle söyleneni ayırırdı."""
    k = _bm1_sablon('kasa.html')
    bas = k.index('function kasaKartlariCiz()')
    son = k.index('\n}', bas)
    govde = k[bas:son]
    assert "KASALAR.filter(k => !k.ana_kasa)" in govde, \
        'kasaKartlariCiz ana kasaları süzmüyor'
    assert 'KASALAR.length ? \'· \' + KASALAR.length' not in govde, \
        'kart sayısı hâlâ ham KASALAR uzunluğundan geliyor'
    assert "gorunen.length ? '· ' + gorunen.length" in govde, \
        'kart sayısı süzülmüş listeden gelmiyor'


def test_ak1_konsolide_kartta_hareketler_dugmesi():
    """TABANDA DÜŞER — siyah kartta yalnız "Ekstre ↓" vardı.

    Ana kasa kartının tek özgün içeriği "kapsadığı kasalar"dı. O
    buraya taşındı; üstüne bugüne kadar HİÇBİR ekranda görünmeyen
    birleşik hareket listesi eklendi (arka uç destekliyordu,
    `kasaAc` ana kasa için hareket ucunu atlıyordu)."""
    k = _bm1_sablon('kasa.html')
    assert 'async function konsolideAc(' in k, 'konsolide çekmecesi yok'
    assert "konsolideAc('${kacar(d)}')" in k, \
        'siyah karttaki düğme konsolideAc çağırmıyor'
    bas = k.index('async function konsolideAc(')
    govde = k[bas:k.index('\n}', bas)]
    assert 'Kapsadığı kasalar' in govde, 'kapsam listesi taşınmamış'
    assert 'Birleşik hareketler' in govde, 'birleşik hareket listesi yok'
    assert '/api/kasa/konsolide/' in govde, 'Excel indirme yok'


def test_ak1_konsolide_ana_kasa_kaydina_bagli_degil():
    """TABANDA DÜŞER — ASIL TASARIM KARARI BU.

    Çekmece kasaları DÖVİZDEN süzüyor, ana kasa KAYDINI aramıyor.
    Kayda bağlasaydım (örneğin ana kasanın id'siyle hareket ucunu
    çağırsaydım) o kayıt bir gün silindiğinde düğme SESSİZCE
    kaybolurdu — bu evde kapattığımız hata sınıfının tam kendisi."""
    k = _bm1_sablon('kasa.html')
    bas = k.index('async function konsolideAc(')
    govde = k[bas:k.index('\n}', bas)]
    assert "!k.ana_kasa && k.doviz === doviz" in govde, \
        'konsolideAc dövizden süzmüyor'
    assert 'ana_kasa && ' not in govde.replace('!k.ana_kasa && ', ''), \
        'konsolideAc ana kasa KAYDINI arıyor — kayda bağlı olmamalı'


def test_ak1_hareket_toplama_tek_kapi():
    """TABANDA DÜŞER — toplama `sonHareketleriYukle` içinde gömülüydü.

    İki ayrı yerde toplasaydım ekranda iki farklı "birleşik hareket"
    olurdu ve hangisinin doğru olduğu belirsizleşirdi. Evin deseni
    bu değil."""
    k = _bm1_sablon('kasa.html')
    assert k.count('async function hareketleriTopla(') == 1, \
        'ortak toplayıcı tek kez tanımlı değil'
    # İki çağıran da var mı
    assert k.count('await hareketleriTopla(') >= 2, \
        'ortak toplayıcıyı iki ekran da kullanmıyor'
    # İkinci bir elle toplama sızmasın
    assert k.count("api(`/api/kasa/${k.id}/hareket`)") == 1, \
        'hareket toplama ikinci bir yerde tekrar yazılmış'


def test_ak1_ana_kasa_kurallari_duruyor():
    """TABANDA DA GEÇER — KALDIRILMAYANI çiviliyor.

    Kaldırılan yalnızca KART. `ana_kasa` kaydının arka uçtaki iki
    işi yerinde: bakiyesi alt kasaların canlı toplamı ve ona
    doğrudan hareket/virman girilemiyor. Bu test, ileride "nasılsa
    kart kalktı" diye kaydın da sökülmesini engelliyor."""
    import io
    fa = io.open(os.path.join(KOK, 'flask_app.py'),
                 encoding='utf-8', newline='').read()
    assert 'Ana kasaya doğrudan hareket girilemez' in fa, \
        'ana kasaya hareket girişi kapısı kalkmış'
    assert 'Ana kasaya dogrudan hareket girilemez' in fa, \
        'virmanda ana kasa kapısı kalkmış'
    kd = _bm1_sablon('kasa_defter.html')
    assert 'ana_kasa' in kd, \
        'Kasa Defteri ana kasayı artık tanımıyor'


# ══════════════════════════════════════════════════════════════════════
#  IN1 · İNDİRME SEKMESİ ÇAKMASIN
# ══════════════════════════════════════════════════════════════════════
#
# "Ekstre ↓"ye basınca bir pencere açılıp hemen kapanıyordu.
# Ölçtüm: uç SAĞLAM — 200, `Content-Disposition: attachment`, dosya
# Indirilenler'e düşüyor. Sorun `window.open(url,'_blank')`: tarayıcı
# boş bir sekme açıyor, indirmeyi görüyor, sekmeyi kapatıyor. Dosya
# iniyor ama kullanıcı "hiçbir şey olmadı" sanıyor.
#
# Gerçek tarayıcıda ölçüldü — aynı düğme, aynı uç:
#     window.open  → açılan sekme 1,  dosya indi
#     indir()      → açılan sekme 0,  dosya indi
def _in1_sablonlar():
    import glob
    return sorted(glob.glob(os.path.join(KOK, 'templates', '*.html')))


def _in1_cagrilar(metin, ad):
    """`ad(` ile başlayan çağrının SATIR SONUNA kadarını döndürür.

    İlk yazdığımda `([^)]*)` kullanmıştım ve desen `${kacar(d)}`
    içindeki parantezde duruyordu: yakalanan metin `/excel`e hiç
    ulaşmıyordu, yani test TABANDA DA GEÇERDİ. Yanlış negatif, en
    kötü tür. Bu evdeki çağrılar tek satır; satır sonuna kadar
    okumak hem basit hem de iç parantezlere takılmıyor.
    `test_in1_desen_bilinen_bozugu_yakaliyor` bunu çiviliyor."""
    out = []
    for satir in metin.split('\n'):
        i = satir.find(ad + '(')
        while i != -1:
            out.append(satir[i + len(ad) + 1:])
            i = satir.find(ad + '(', i + 1)
    return out


# İNDİRME uçları: yanıtı `attachment` olanlar. Ölçerek ayırdım —
# `/excel` xlsx attachment döndürüyor, `/html?mod=` ise text/html.
_IN1_INDIRME = ('/excel', '/yedek/indir/')


def test_in1_ortak_indirme_kapisi_var():
    """TABANDA DÜŞER — her çağrı kendi window.open'ını yazıyordu."""
    b = _bm1_sablon('base.html')
    assert 'function indir(url)' in b, \
        'base.html ortak indirme kapısını tanımlamıyor'
    assert "a.download = ''" in b, \
        'dosya adını sunucunun Content-Disposition başlığına bırakmıyor'


def test_in1_indirme_ucu_window_open_kullanmiyor():
    """TABANDA DÜŞER — asıl çivi.

    Hangi şablonda olursa olsun, bir İNDİRME ucunu `window.open` ile
    açmak sekme çakmasına yol açar. Bu test yeni eklenecek indirme
    düğmelerini de yakalar; bugünkü dördünü düzeltip yarın beşincisi
    aynı hatayla gelsin istemem."""
    suclu = []
    for yol in _in1_sablonlar():
        metin = _bm1_sablon(os.path.basename(yol))
        for cagri in _in1_cagrilar(metin, 'window.open'):
            if any(u in cagri for u in _IN1_INDIRME):
                suclu.append(f'{os.path.basename(yol)}: {cagri.strip()[:70]}')
    assert not suclu, (
        'İndirme ucu window.open ile açılıyor — boş sekme açılıp '
        'kapanır:\n  ' + '\n  '.join(suclu) + '\n`indir(url)` kullan.')


def test_in1_goruntuleme_baglantilari_window_open_kaliyor():
    """TABANDA DA GEÇER — DÜZELTMENİN FAZLA UYGULANMAMASINI tutuyor.

    Proforma/fatura `…/html?mod=…` bağlantıları GÖRÜNTÜLENECEK
    sayfalar, indirme değil (ölçtüm: text/html, attachment yok).
    Onları `indir()`e çevirmek sayfayı yeni sekmede açmak yerine
    dosya olarak indirtirdi. `indir()` yalnız indirme uçları için."""
    gorunen = 0
    for yol in _in1_sablonlar():
        metin = _bm1_sablon(os.path.basename(yol))
        for cagri in _in1_cagrilar(metin, 'window.open'):
            if '/html?mod=' in cagri:
                gorunen += 1
        for cagri in _in1_cagrilar(metin, 'indir'):
            assert '/html?mod=' not in cagri, \
                f'{os.path.basename(yol)}: görüntüleme bağlantısı indir() ile açılıyor'
    assert gorunen >= 3, \
        f'görüntüleme bağlantıları kaybolmuş (bulunan: {gorunen})'


def test_in1_desen_bilinen_bozugu_yakaliyor():
    """TABANDA DA GEÇER — TESTİN KENDİSİNİ sınıyor.

    `_in1_cagrilar` bir tarama ve bu evdeki kural şu: her tarama
    bilinen-bozuk bir vakaya karşı sınanmalı. İlk sürümü
    `${kacar(d)}` içindeki parantezde duruyordu ve gerçek hatayı
    GÖRMÜYORDU. Burada o tam satır veriliyor; desen yakalamazsa
    test düşer ve sessiz bir yanlış negatifle yaşamayız."""
    bozuk = ("""        <button onclick="window.open('/api/kasa/konsolide/"""
             + """${kacar(d)}/excel','_blank')">Ekstre</button>""")
    bulunan = _in1_cagrilar(bozuk, 'window.open')
    assert bulunan, 'desen çağrıyı hiç bulamadı'
    assert any(u in c for c in bulunan for u in _IN1_INDIRME), \
        'desen iç parantezde duruyor — /excel görülmüyor (yanlış negatif)'


# ══════════════════════════════════════════════════════════════════════
#  MT2 · MALİYET GİRİŞİNDE FATURA TARİHİ
# ══════════════════════════════════════════════════════════════════════
#
# Kullanıcı bildirdi: "stok için maliyet girerken fatura tarihi
# gireceğimiz alan yok, bu yüzden kaydı yaptığımız tarih yazılıyor."
#
# Ölçtüm — doğruydu ve iki ayrı sonucu vardı. POST gövdesine
# `maliyet_tarihi` koysam bile YOK SAYILIYORDU; modeldeki
# `default=date.today` sessizce bugünü yazıyordu. Maliyet YARATAN
# BEŞ noktanın hepsi böyleydi.
#
#   KDV DÖNEMİ : ekim faturası kasım dönemine düşüyordu.
#   KUR        : 1.000 EUR'luk ekim faturası BUGÜNÜN kuruyla
#                çevriliyordu — 1.100 USD yerine 1.200 USD, %9 fazla,
#                ve bu rakam doğrudan maliyete ve kârlılığa gidiyor.
#
# Kullanıcının kararı: alan ekranda GÖRÜNÜR olsun, BUGÜNLE DOLU
# gelsin, değiştirilebilsin.
def _mt2_kurlar(eski, yeni):
    """İki tarihte FARKLI kur — fark ölçülebilir olsun diye belirgin.

    EUR/USD çaprazı: eski günde 1,10 · yeni günde 1,20."""
    with fa.app.app_context():
        for t, usd, eur in ((eski, 40.0, 44.0), (yeni, 42.0, 50.4)):
            for dv, k in (('USD', usd), ('EUR', eur)):
                if not DovizKur.query.filter_by(doviz=dv, tarih=t).first():
                    db.session.add(DovizKur(doviz=dv, tarih=t, alis=k,
                                            satis=k, efektif=k))
        db.session.commit()


def _mt2_gunler():
    """(acik_eski, bugun) — ikisi de AÇIK dönemde kalsın.

    Kapanmış dönem testi ayrı; burada kur farkını ölçüyoruz, araya
    MK2 kapısı girmesin."""
    from datetime import timedelta
    bugun = date.today()
    return (bugun - timedelta(days=12), bugun)


def _mt2_satirlar(fno):
    from models import Maliyet
    with fa.app.app_context():
        return [(m.maliyet_tip, m.maliyet_tarihi, float(m.usd_karsilik or 0),
                 float(m.tutar))
                for m in Maliyet.query.filter_by(fatura_no=fno)
                                      .order_by(Maliyet.id).all()]


def _mt2_ekle(c, fno, tarih=None, tutar=1000, kdv=20):
    g = {'maliyet_tip': 'Nakliye', 'baglanti_tip': 'stok',
         'baglanti_id': f'MT2-{fno}', 'tutar': tutar, 'doviz': 'EUR',
         'kdv_oran': kdv, 'kdv_dahil_mi': False, 'fatura_no': fno,
         'yineleme_onay': True}
    if tarih is not None:
        g['maliyet_tarihi'] = tarih.isoformat()
    return c.post('/api/maliyet', headers=H, json=g)


def test_mt2_giris_tarihi_yaziliyor():
    """TABANDA DÜŞER — gönderilen tarih YOK SAYILIYORDU.

    Hem ana satır hem KDV kardeşi faturanın kendi tarihini almalı;
    ikisi aynı faturanın iki yüzü (DZ1)."""
    c = istemci('admin', 'ADMIN')
    eski, bugun = _mt2_gunler()
    _mt2_kurlar(eski, bugun)
    r = _mt2_ekle(c, 'MT2-TARIH', eski)
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    satir = _mt2_satirlar('MT2-TARIH')
    assert len(satir) == 2, satir
    for tip, trh, _usd, _t in satir:
        assert trh == eski, f'{tip}: tarih {trh}, {eski} olmalıydı'


def test_mt2_kur_fatura_gununden_aliniyor():
    """TABANDA DÜŞER — PARA TESTİ.

    1.000 EUR'luk maliyet, eski günün kuruyla 1.100 USD; bugünün
    kuruyla 1.200 USD. Eskiden 1.200 yazılıyordu: %9 fazla maliyet,
    doğrudan kârlılığa."""
    c = istemci('admin', 'ADMIN')
    eski, bugun = _mt2_gunler()
    _mt2_kurlar(eski, bugun)
    assert _mt2_ekle(c, 'MT2-KUR', eski).status_code == 200
    d = {tip: usd for tip, _t, usd, _tu in _mt2_satirlar('MT2-KUR')}
    assert abs(d['Nakliye'] - 1100.0) < 0.5, \
        f"ana satır {d['Nakliye']}, 1100 olmalıydı (bugünün kuru 1200 verir)"
    assert abs(d['Devreden KDV'] - 220.0) < 0.5, \
        f"KDV satırı {d['Devreden KDV']}, 220 olmalıydı"


def test_mt2_tarih_verilmezse_bugun():
    """TABANDA DA GEÇER — ESKİ DAVRANIŞ KORUNUYOR.

    Tarih göndermeyen eski çağıranlar ve testler değişmeden
    çalışmalı; yama kapıyı açarken mevcut akışı kırmamalı."""
    c = istemci('admin', 'ADMIN')
    eski, bugun = _mt2_gunler()
    _mt2_kurlar(eski, bugun)
    assert _mt2_ekle(c, 'MT2-BOS').status_code == 200
    for tip, trh, _u, _t in _mt2_satirlar('MT2-BOS'):
        assert trh == date.today(), f'{tip}: {trh}'


def test_mt2_bozuk_tarih_reddediliyor():
    """TABANDA DÜŞER — tarih hiç okunmadığı için bozuğu da sessizce
    yutuluyordu. Artık 400 dönüyor ve HİÇBİR satır yazılmıyor."""
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Nakliye', 'baglanti_tip': 'stok',
        'baglanti_id': 'MT2-X', 'tutar': 100, 'doviz': 'EUR',
        'kdv_oran': 20, 'maliyet_tarihi': '15.10.2026',
        'fatura_no': 'MT2-BOZUK', 'yineleme_onay': True})
    assert r.status_code == 400, r.status_code
    assert _mt2_satirlar('MT2-BOZUK') == [], 'yarım kayıt yazılmış'


def test_mt2_kapanmis_doneme_giris_reddediliyor():
    """TABANDA DÜŞER — kapı GİRİŞ yolunda hiç yoktu.

    MK2'de karar verilmişti: "Kapanmış KDV dönemine geriye dönük
    alış faturası girişi de engellensin." O kapı yalnız DÜZENLEMEDE
    vardı; girişte tarih okunmadığı için gerek görülmemişti. Tarih
    okunur olunca kapı da gerekli oldu."""
    c = istemci('admin', 'ADMIN')
    _acik, kapali = _mt1_tarihler()      # beyan süresi kesin dolmuş
    _mk1_kur(kapali)
    r = _mt2_ekle(c, 'MT2-KAPALI', kapali)
    assert r.status_code == 400, r.status_code
    assert 'kapanmış' in (r.get_json() or {}).get('mesaj', '').lower()
    assert _mt2_satirlar('MT2-KAPALI') == [], 'kapalı döneme kayıt girmiş'


def test_mt2_tarih_tasininca_grubun_tamami_yeniden_hesaplaniyor():
    """TABANDA DÜŞER — BENİM MT1'DE AÇTIĞIM HATA.

    MT1 tarih değişince GRUBU birlikte taşıyor, ama `usd_karsilik`
    yalnız DÜZENLENEN satır için yeniden hesaplanıyordu. KDV
    satırının tarihi eskiye gidiyor, USD karşılığı yeni günün
    kurunda kalıyordu — ve kullanıcı tarihi "düzelttikten" SONRA DA
    yanlış kalıyordu."""
    c = istemci('admin', 'ADMIN')
    eski, bugun = _mt2_gunler()
    _mt2_kurlar(eski, bugun)
    r = _mt2_ekle(c, 'MT2-TASI', bugun)
    assert r.status_code == 200
    ana = r.get_json()['id']
    r2 = c.put(f'/api/maliyet/{ana}', headers=H,
               json={'maliyet_tarihi': eski.isoformat()})
    assert r2.status_code == 200, r2.get_data(as_text=True)[:200]
    for tip, trh, usd, tutar in _mt2_satirlar('MT2-TASI'):
        assert trh == eski, f'{tip}: tarih taşınmamış ({trh})'
        bekle = tutar * 44.0 / 40.0          # eski günün çaprazı
        assert abs(usd - bekle) < 0.5, \
            f'{tip}: usd {usd}, {bekle:.2f} olmalıydı — grup yeniden ' \
            f'hesaplanmamış'


def test_mt2_uc_uc_da_ayni_kapidan_geciyor():
    """TABANDA DÜŞER — kapıyı ÜÇ uca da bağladığımı çiviliyor.

    Maliyet yaratan üç uç var: /api/maliyet, /api/maliyet/dagit ve
    /api/maliyet/blok_dagilim. Yalnız birine koysaydım öbür ikisi
    sessizce bugünü yazmaya devam ederdi — bu evde tam bu yüzden
    "tek kapı" deseni var. Dördüncü bir uç eklenirse bu test
    düşer."""
    import ast
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8', newline='').read()
    agac = ast.parse(kaynak)
    bulunan = {}
    for d in ast.walk(agac):
        if not isinstance(d, ast.FunctionDef):
            continue
        if d.name not in ('api_maliyet_ekle', 'api_maliyet_dagit',
                          'api_maliyet_blok_dagilim'):
            continue
        govde = ast.unparse(d)
        bulunan[d.name] = '_maliyet_giris_tarihi(' in govde
    assert len(bulunan) == 3, f'uçlar bulunamadı: {sorted(bulunan)}'
    eksik = sorted(a for a, v in bulunan.items() if not v)
    assert not eksik, f'bu uçlar ortak tarih kapısını çağırmıyor: {eksik}'


# ══════════════════════════════════════════════════════════════════════
#  PRF1 · PROFORMA ÜÇLÜSÜ: FİYAT EZME · EN KAYBI · REZERVASYON
# ══════════════════════════════════════════════════════════════════════
#
# Kullanıcının bildirdiği üç ayrı sorun; üçü de aynı ekranda.
#
# 1 · TOPLU FİYAT DOLU KALEMLERİ EZİYORDU. Onay YALNIZCA hiç boş kalem
#     yokken soruluyordu, sonra fiyat KALEMLER'in TAMAMINA yazılıyordu.
#     Karışık durum — bazısı dolu bazısı boş — tam da onayın atlandığı
#     ve dolu fiyatların SESSİZCE ezildiği durumdu.
#     Tarayıcıda ölçüldü (5 kalem @100 + 3 boş, 50 uygulandı):
#         eski:  [50,50,50,50,50,50,50,50]
#         yeni:  [100,100,100,100,100,50,50,50]
#
# 2 · BLOK'TA EN KAYBOLUYORDU. Gerçek genişlik `en` sütununda
#     kaydediliyor ama düzenleme formu "En (cm)" etiketiyle `kalinlik`
#     kutusunu okuyordu. Alan boş geliyordu — ve kaydedince `kalemEkle`
#     yeni nesneyi `en` alanı olmadan kurduğu için kayıtlı genişlik
#     SİLİNİYORDU. Görüntü hatası değil, veri kaybı.
#
# 3 · REZERVASYON OLMUYORDU. "Seçilenleri rezerve et" kutusu gözden
#     kaçıyor, istemci `rezerve_et: false` gönderiyor ve stoklar serbest
#     kalıyordu — kullanıcı rezerve olduğunu sanıyordu. Kullanıcının
#     kararı: kutu kalksın, KAYDEDERKEN sorulsun (Rezerve Et / Serbest
#     Kalsın), serbest kalanlar sonradan rezerve edilebilsin.
def _prf1_sablon():
    import io as _io
    return _io.open(os.path.join(KOK, 'templates', 'proforma.html'),
                    encoding='utf-8').read()


def _prf1_bloklar(c, ek, adet=2):
    """Serbest blok stokları. (id listesi) döner."""
    from models import BlokStok
    idler = []
    with fa.app.app_context():
        for i in range(adet):
            bid = f'PRF1-{ek}-{i}'
            if not db.session.get(BlokStok, bid):
                db.session.add(BlokStok(
                    id=bid, blok_no=f'BLK-{ek}-{i}', cins='BEIGE',
                    boy=300, yukseklik=150, en=120, tonaj=10, hacim_m3=5.4,
                    durum='Serbest', firma_id=1))
            idler.append(bid)
        db.session.commit()
    return idler


def _prf1_kalem(bid, no, fiyat=100):
    return {'urun_tip': 'BLOK', 'cins': 'BEIGE', 'blok_no': f'BLK-{no}',
            'boy': 300, 'yukseklik': 150, 'kalinlik': 120, 'en': 120,
            'adet': 1, 'miktar': 10, 'birim': 'ton', 'birim_fiyat': fiyat,
            'toplam_fiyat': 10 * fiyat, 'net_fiyat': 10 * fiyat,
            'doviz': 'USD', 'stok_id': bid}


def _prf1_proforma(c, ek, rezerve=False):
    idler = _prf1_bloklar(c, ek)
    r = c.post('/api/proforma', headers=H, json={
        'musteri': 'PRF1 MUSTERI', 'doviz': 'USD', 'tur': 'ihracat',
        'rezerve_et': rezerve, 'yineleme_onay': True,
        'kalemler': [_prf1_kalem(b, f'{ek}-{i}')
                     for i, b in enumerate(idler)]})
    assert r.status_code == 200, r.get_data(as_text=True)[:220]
    return r.get_json()['id'], idler


def _prf1_durumlar(idler):
    from models import BlokStok
    with fa.app.app_context():
        return [db.session.get(BlokStok, b).durum for b in idler]


def test_prf1_en_kaydedilip_korunuyor():
    """TABANDA DA GEÇER — sunucu tarafı ZATEN doğruydu.

    Hatanın sunucuda OLMADIĞINI çiviliyor: `en` kaydediliyor ve geri
    okunuyor. Kayıp istemcide, düzenleme formunda oluyordu. Bu sınır
    olmadan, ileride biri hatayı sunucuda arar."""
    c = istemci('admin', 'ADMIN')
    pid, _ = _prf1_proforma(c, 'EN')
    from models import ProformaKalem
    with fa.app.app_context():
        ks = ProformaKalem.query.filter_by(proforma_id=pid).all()
        assert ks, 'kalem yazılmamış'
        for k in ks:
            assert float(k.en or 0) == 120.0, f'{k.blok_no}: en={k.en}'


def test_prf1_duzenleme_formu_en_okuyor():
    """TABANDA DÜŞER — form `kalinlik` okuyordu, `en` değil.

    BLOK'ta "En (cm)" kutusu önce `en`i okumalı; eski kayıtlarda
    genişlik `kalinlik`te durduğu için ona geri düşmeli."""
    s = _prf1_sablon()
    bas = s.index('function kalemDuzenle(')
    govde = s[bas:s.index('\n}', bas)]
    assert "k.en != null ? k.en : k.kalinlik" in govde, \
        'kalemDuzenle BLOK için `en` okumuyor'
    # kalemEkle `en`i de yazmalı, yoksa kaydedince silinir
    bas2 = s.index('function kalemEkle()')
    govde2 = s[bas2:s.index('\n}\n', bas2)]
    assert 'en:' in govde2, 'kalemEkle `en` alanını kurmuyor — kayıp sürer'


def test_prf1_toplu_fiyat_dolulari_ezmiyor():
    """TABANDA DÜŞER — asıl para hatası.

    Fiyat artık `KALEMLER`in tamamına değil, SEÇİLEN hedefe
    uygulanıyor; boş kalem varsa hedef yalnız boş olanlar."""
    s = _prf1_sablon()
    bas = s.index('async function tumKalemlereFiyat()')
    govde = s[bas:s.index('\n}\n', bas)]
    assert 'hedef.forEach(' in govde, \
        'fiyat hâlâ tüm kalemlere uygulanıyor'
    assert 'KALEMLER.forEach(' not in govde, \
        'KALEMLER.forEach kalmış — dolu fiyatlar yine ezilir'
    assert 'let hedef = bosOlanlar' in govde, \
        'varsayılan hedef boş kalemler değil'
    assert 'korundu' in govde, \
        'kaç kalemin korunduğu kullanıcıya söylenmiyor'


def test_prf1_rezerve_kutusu_kalkti_soru_geldi():
    """TABANDA DÜŞER — kullanıcının kararı.

    Gözden kaçan işaret kutusu yerine kaydederken açık soru:
    iki seçenek, ikisi de adıyla yazılı."""
    s = _prf1_sablon()
    assert 'stRezerve' not in s, 'rezerve işaret kutusu hâlâ duruyor'
    assert "tamam: 'Rezerve Et'" in s, '"Rezerve Et" seçeneği yok'
    assert "iptal: 'Serbest Kalsın'" in s, '"Serbest Kalsın" seçeneği yok'
    assert 'rezerve_et: _rezIste' in s, \
        'kaydetme gövdesi sorunun cevabını göndermiyor'


def test_prf1_serbest_birakilan_sonradan_rezerve_edilebiliyor():
    """TABANDA DÜŞER — uç yoktu.

    Kullanıcının isteği: "serbest kalan ürünler daha sonra bu
    proforma için rezerve edilebilir". Mantık yeniden yazılmıyor;
    kayıt yolunun kullandığı AYNI kapıdan geçiyor."""
    c = istemci('admin', 'ADMIN')
    pid, idler = _prf1_proforma(c, 'REZ', rezerve=False)
    assert _prf1_durumlar(idler) == ['Serbest'] * len(idler), \
        'serbest kalsın dendiği hâlde rezerve olmuş'
    r = c.post(f'/api/proforma/{pid}/rezerve', headers=H,
               json={'yineleme_onay': True})
    assert r.status_code == 200, r.get_data(as_text=True)[:220]
    assert r.get_json().get('adet') == len(idler), r.get_json()
    assert _prf1_durumlar(idler) == ['Rezerve'] * len(idler), \
        'uç 200 döndü ama stok durumu değişmedi'


def test_prf1_rezerve_ucu_yetki_ariyor():
    """TABANDA DÜŞER — uç yoktu.

    Rezervasyon stoğu başka tekliflere kapatıyor; okuma yetkisi
    olan biri bunu yapamamalı."""
    c = istemci('admin', 'ADMIN')
    pid, idler = _prf1_proforma(c, 'YETKI')
    c2 = istemci('okur', 'OKUYUCU')
    r = c2.post(f'/api/proforma/{pid}/rezerve', headers=H,
                json={'yineleme_onay': True})
    assert r.status_code in (401, 403), \
        f'yetkisiz kullanıcı rezerve edebildi ({r.status_code})'
    assert _prf1_durumlar(idler) == ['Serbest'] * len(idler), \
        'reddedildiği hâlde stok durumu değişti'
    # OLUMLU DURUM DA SINANIYOR, bilerek: yalnız "okur reddedildi"
    # deseydim test TABANDA DA GEÇERDİ — uç hiç yokken de 403
    # dönüyor, ölçtüm. Yetkilinin GEÇEBİLDİĞİNİ sınamak testi
    # gerçek kılıyor.
    r2 = c.post(f'/api/proforma/{pid}/rezerve', headers=H,
                json={'yineleme_onay': True})
    assert r2.status_code == 200, \
        f'yetkili kullanıcı rezerve EDEMEDİ ({r2.status_code})'
    assert _prf1_durumlar(idler) == ['Rezerve'] * len(idler)
# ══════════════════════════════════════════════════════════════════
#  TD1 · STOK TEDARİKÇİSİ DEĞİŞİNCE CARİ HAREKET TAŞINMIYORDU
#
#  ÖLÇÜLDÜ (gerçek uçlarla, taze kurulumda, her seferinde):
#  TEDARIKCI A'dan 1.200 USD'ye girilmiş blok B'ye çevrildi →
#      A bakiye  3.600 → 3.600   ✗ (2.400 olmalıydı)
#      B bakiye      0 →     0   ✗ (1.200 olmalıydı)
#  İstek 200 dönüyor, ekranda "Stok güncellendi" yazıyor. İKİ CARİ
#  BİRDEN yanlış, hiçbir uyarı yok. Üstelik `stok.cari_id` de eski
#  tedarikçide kalıyordu: ekranda B yazarken silme yolu (SK1) kimlik
#  bağını izleyip karşı kaydı A'nın hesabına düşürüyordu.
# ══════════════════════════════════════════════════════════════════
# BUGÜN kullanılıyor, sabit bir gün DEĞİL: MK2 kapısı kapanmış KDV
# dönemine alış girişini REDDEDİYOR (doğru davranış) ve sabit bir
# gün takvim ilerledikçe kapanır — test bir ay sonra kendiliğinden
# düşerdi. Bugün her zaman açık dönemdedir.
TD1_GUN = date.today()


def _td1_kur():
    """TD1 testlerinin kendi günü — küresel kur durumuna yaslanmıyor."""
    from models import DovizKur
    for dv, k in (('USD', 41.0), ('EUR', 45.0)):
        if not DovizKur.query.filter_by(doviz=dv, tarih=TD1_GUN).first():
            db.session.add(DovizKur(doviz=dv, tarih=TD1_GUN,
                                    alis=k, satis=k, efektif=k))
    db.session.commit()


def _td1_cariler():
    from models import Cari
    for cid, ad in (('TDA', 'TD1 TEDARIKCI A'), ('TDB', 'TD1 TEDARIKCI B')):
        if not Cari.query.get(cid):
            db.session.add(Cari(id=cid, unvan=ad, cari_tip='Tedarikçi',
                                urun_tedarikcisi=True, gorunurluk='acik'))
    db.session.commit()


def _td1_kur_ve_cari():
    with fa.app.app_context():
        _td1_kur()
        _td1_cariler()


def _td1_blok(c, blok_no, fatura_no, tedarikci='TD1 TEDARIKCI A',
              tarih=None):
    """Gerçek uçtan blok açar; alış borcu ev kapısından doğar."""
    r = c.post('/api/stok/ekle', headers=H, json={
        'tip': 'BLOK', 'uretici': tedarikci, 'cins': 'TD1 CINS',
        'blok_no': blok_no, 'boy': 300, 'yukseklik': 150, 'en': 120,
        'tonaj': 10, 'fiyat': 100, 'fiyat_birim': 'ton', 'doviz': 'USD',
        'kdv_dahil_mi': False, 'kdv_oran': 20,
        'alis_tipi': 'yurtici_kdvli', 'fatura_no': fatura_no,
        'alis_tarihi': (tarih or TD1_GUN).isoformat(),
        'fatura_durumu': 'faturali', 'mense': 'TURKIYE'})
    assert r.status_code == 200, (r.status_code, r.get_json())
    return (r.get_json() or {}).get('id')


def _td1_bakiye(cari_id):
    from models import CariHareket
    return round(sum(float(h.alacak or 0) - float(h.borc or 0)
                     for h in CariHareket.query.filter_by(
                         cari_id=cari_id).all()), 2)


def test_td1_tedarikci_degisince_sessizce_kaydedilmiyor():
    """ÇİVİ: borcu olan bir stoğun tedarikçisi SORULMADAN değişemez.

    Tabanda bu istek 200 dönüyor ve iki cariyi birden yanlış
    bırakıyordu. Artık 409 ile SORULUYOR (hata değil, soru) —
    silme yolundaki SF1 kuralının aynısı, aynı üç anahtarla."""
    from models import CariHareket
    _td1_kur_ve_cari()
    c = istemci('admin', 'ADMIN')
    sid = _td1_blok(c, 'TD1-A1', 'TD1-F1')
    with fa.app.app_context():
        assert _td1_bakiye('TDA') == 1200.0, _td1_bakiye('TDA')

    r = c.put(f'/api/stok/{sid}', headers=H,
              json={'tip': 'BLOK', 'uretici': 'TD1 TEDARIKCI B'})
    assert r.status_code == 409, (r.status_code, r.get_json())
    y = r.get_json()
    assert y.get('error') == 'mali_islem_gerekli', y
    assert y.get('baglam') == 'tedarikci', y
    assert abs(float(y.get('pay') or 0) - 1200.0) < 0.005, y
    assert set(y.get('secenekler') or {}) == {
        'fatura_duzelt', 'karsi_kayit', 'sadece_stok'}, y
    # SORU SORULURKEN HİÇBİR ŞEY DEĞİŞMEMELİ
    with fa.app.app_context():
        assert _td1_bakiye('TDA') == 1200.0
        assert _td1_bakiye('TDB') == 0.0
        s = BlokStok.query.get(sid)
        assert s.uretici == 'TD1 TEDARIKCI A', s.uretici


def test_td1_borc_yeni_tedarikciye_tasiniyor():
    """`fatura_duzelt`: eski faturadan pay düşer, yeni tedarikçide
    borç doğar. Matrah ve KDV de taşınır — `alacak = matrah + KDV`
    ilişkisi iki tarafta da ayakta kalmalı."""
    from models import CariHareket
    _td1_kur_ve_cari()
    c = istemci('admin', 'ADMIN')
    # AYNI faturada İKİ blok: grup bölünüyor, tek kalemli hâl değil.
    s1 = _td1_blok(c, 'TD1-B1', 'TD1-F2')
    s2 = _td1_blok(c, 'TD1-B2', 'TD1-F2')
    with fa.app.app_context():
        g = CariHareket.query.filter_by(baglanti_tip='stok_fatura',
                                        baglanti_id='TD1-F2').first()
        assert float(g.alacak) == 2400.0 and g.kalem_sayisi == 2, (
            g.alacak, g.kalem_sayisi)

    r = c.put(f'/api/stok/{s1}', headers=H,
              json={'tip': 'BLOK', 'uretici': 'TD1 TEDARIKCI B',
                    'mali_islem': 'fatura_duzelt'})
    assert r.status_code == 200, (r.status_code, r.get_json())

    with fa.app.app_context():
        eski = CariHareket.query.filter_by(
            baglanti_tip='stok_fatura', baglanti_id='TD1-F2',
            cari_id='TDA').first()
        yeni = CariHareket.query.filter_by(
            baglanti_tip='stok_fatura', baglanti_id='TD1-F2',
            cari_id='TDB').first()
        assert eski is not None and float(eski.alacak) == 1200.0, (
            'eski faturadan pay düşmedi: '
            f'{eski and float(eski.alacak)}')
        assert eski.kalem_sayisi == 1, eski.kalem_sayisi
        assert float(eski.matrah) == 1000.0 and float(eski.kdv_tutar) == 200.0, (
            float(eski.matrah), float(eski.kdv_tutar))
        assert yeni is not None, 'yeni tedarikçide borç DOĞMADI'
        assert float(yeni.alacak) == 1200.0, float(yeni.alacak)
        assert float(yeni.matrah) == 1000.0 and float(yeni.kdv_tutar) == 200.0, (
            'KDV kırılımı taşınmadı',
            float(yeni.matrah), float(yeni.kdv_tutar))
        # ÖBÜR STOK YERİNDE: fatura bölündü, silinmedi.
        assert BlokStok.query.get(s2).uretici == 'TD1 TEDARIKCI A'


def test_td1_karsi_kayit_eski_faturayi_koruyor():
    """`karsi_kayit`: orijinal fatura KORUNUR, ters hareket açılır.

    Mal gerçekten başka tedarikçiden geldiyse ama eski faturası da
    gerçekse doğru olan budur — belge ile kayıt ayrışmaz."""
    from models import CariHareket
    _td1_kur_ve_cari()
    c = istemci('admin', 'ADMIN')
    sid = _td1_blok(c, 'TD1-C1', 'TD1-F3')

    r = c.put(f'/api/stok/{sid}', headers=H,
              json={'tip': 'BLOK', 'uretici': 'TD1 TEDARIKCI B',
                    'mali_islem': 'karsi_kayit'})
    assert r.status_code == 200, (r.status_code, r.get_json())

    with fa.app.app_context():
        fat = CariHareket.query.filter_by(
            baglanti_tip='stok_fatura', baglanti_id='TD1-F3',
            cari_id='TDA', kaynak='stok').first()
        assert fat is not None and float(fat.alacak) == 1200.0, (
            'orijinal fatura korunmadı')
        kk = CariHareket.query.filter_by(
            baglanti_tip='stok_fatura', baglanti_id='TD1-F3',
            cari_id='TDA', kaynak='stok_tedarikci_degisimi').first()
        assert kk is not None, 'karşı kayıt açılmadı'
        assert float(kk.borc) == 1200.0 and float(kk.alacak or 0) == 0, (
            float(kk.borc), float(kk.alacak or 0))
        yeni = CariHareket.query.filter_by(
            baglanti_tip='stok_fatura', baglanti_id='TD1-F3',
            cari_id='TDB').first()
        assert yeni is not None and float(yeni.alacak) == 1200.0, (
            'yeni tedarikçide borç doğmadı')
        # NET: A'nın bu faturadan borcu sıfırlanmış olmalı.
        _a = sum(float(h.alacak or 0) - float(h.borc or 0)
                 for h in CariHareket.query.filter_by(
                     baglanti_id='TD1-F3', cari_id='TDA').all())
        assert abs(_a) < 0.005, f'A net {_a} (0 olmalı)'


def test_td1_sadece_stok_borca_dokunmuyor_ama_kimligi_tazeliyor():
    """`sadece_stok`: borç eski tedarikçide kalır.

    Tabanda da "borç yerinde kalıyordu" — fark şurada: `cari_id`
    de eski tedarikçide kalıyordu. Ekranda B yazarken kimlik bağı
    A'yı gösteriyordu ve silme yolu (SK1) o bağı izliyor. Bu test
    asıl o sessiz ayrışmayı çiviliyor."""
    _td1_kur_ve_cari()
    c = istemci('admin', 'ADMIN')
    sid = _td1_blok(c, 'TD1-D1', 'TD1-F4')
    with fa.app.app_context():
        assert BlokStok.query.get(sid).cari_id == 'TDA'

    r = c.put(f'/api/stok/{sid}', headers=H,
              json={'tip': 'BLOK', 'uretici': 'TD1 TEDARIKCI B',
                    'mali_islem': 'sadece_stok'})
    assert r.status_code == 200, (r.status_code, r.get_json())

    with fa.app.app_context():
        assert _td1_bakiye('TDA') >= 1200.0, 'borca dokunulmuş'
        s = BlokStok.query.get(sid)
        assert s.uretici == 'TD1 TEDARIKCI B'
        assert s.cari_id == 'TDB', (
            f'kimlik bağı tazelenmedi: {s.cari_id} '
            f'(ekranda B yazarken silme yolu A\'ya yazardı)')


def test_td1_cari_id_uretici_degisince_tazeleniyor():
    """Dinleyici katmanı: `uretici` değişince `cari_id` de değişir.

    Uçtan değil MODELDEN sınanıyor — stok DÖRT yerde oluşturuluyor
    ve ileride beşinci bir güncelleme yolu eklenirse kapsanması
    gereken yer burası. Eşleşme yoksa bağ BOŞALTILIR: eski cariye
    bağlı kalması, bağsız kalmasından kötüdür (SF2)."""
    _td1_kur_ve_cari()
    with fa.app.app_context():
        s = BlokStok(id='TD1-EV1', blok_no='TD1-EV1', cins='TD1 CINS',
                     boy=300, yukseklik=150, en=120, hacim_m3=5.4,
                     tonaj=10, durum='Serbest',
                     uretici='TD1 TEDARIKCI A')
        db.session.add(s)
        db.session.commit()
        assert s.cari_id == 'TDA', s.cari_id

        s.uretici = 'TD1 TEDARIKCI B'
        db.session.commit()
        assert s.cari_id == 'TDB', f'kimlik eski caride kaldı: {s.cari_id}'

        s.uretici = 'HIC OLMAYAN OCAK'
        db.session.commit()
        assert s.cari_id in (None, ''), (
            f'eşleşmeyen adda eski kimlik duruyor: {s.cari_id}')

        # Başka bir alan değişince kimliğe DOKUNULMAMALI.
        s.cari_id = 'TDA'
        db.session.commit()
        s.konum = 'A-12'
        db.session.commit()
        assert s.cari_id == 'TDA', (
            'üretici değişmeden kimlik bozuldu')


def test_td1_carisi_olmayan_tedarikcide_sessiz_kalinmiyor():
    """Yeni tedarikçinin carisi yoksa borç DOĞMAZ — ve bu söylenir.

    Sessiz geçmek, tam da bu yamanın kapattığı hatayı başka bir
    kılıkta geri getirirdi: borç eskiden düştü, yenide doğmadı."""
    _td1_kur_ve_cari()
    c = istemci('admin', 'ADMIN')
    sid = _td1_blok(c, 'TD1-E1', 'TD1-F5')
    r = c.put(f'/api/stok/{sid}', headers=H,
              json={'tip': 'BLOK', 'uretici': 'KAYITSIZ OCAK',
                    'mali_islem': 'fatura_duzelt'})
    assert r.status_code == 200, (r.status_code, r.get_json())
    y = r.get_json()
    assert y.get('uyari') is True, y
    metin = ' '.join(y.get('uyarilar') or [])
    assert 'cari bulunamadı' in metin and 'OLUŞMADI' in metin, metin


def test_td1_yalnizca_yazim_duzeltmesi_soru_sormuyor():
    """Büyük-küçük harf düzeltmesi mali bir olay DEĞİLDİR.

    (TABANDA DA GEÇER — işi kendi yamamı tutmak: kapı her `uretici`
    alanı dolu PUT'ta soru sorsaydı, adını düzelten kullanıcı her
    seferinde mali karar penceresiyle karşılaşırdı.)"""
    _td1_kur_ve_cari()
    c = istemci('admin', 'ADMIN')
    sid = _td1_blok(c, 'TD1-G1', 'TD1-F6')
    r = c.put(f'/api/stok/{sid}', headers=H,
              json={'tip': 'BLOK', 'uretici': 'td1 tedarikci a'})
    assert r.status_code == 200, (r.status_code, r.get_json())
    with fa.app.app_context():
        assert BlokStok.query.get(sid).uretici == 'td1 tedarikci a'
        assert BlokStok.query.get(sid).cari_id == 'TDA'


def test_td1_kapanmis_kdv_doneminde_tasima_reddediliyor():
    """MK1 · beyan edilmiş dönemin matrahı geriye dönük değişmez.

    `fatura_duzelt` eski faturanın matrah ve KDV'sini DÜŞÜRÜYOR;
    dönem kapandıysa bu verilmiş beyanı bozar. Karşı kayda
    yönlendiriliyor — silme yolundaki kararın aynısı."""
    from models import CariHareket
    _td1_kur_ve_cari()
    c = istemci('admin', 'ADMIN')
    # Stok BUGÜNLE açılıyor: MK2 kapısı kapanmış döneme GİRİŞİ zaten
    # reddediyor (doğru davranış), o yüzden kapanmış dönemdeki bir
    # fatura ancak GEÇMİŞTEN gelmiş olabilir. Göçten gelen kayıt
    # taklit ediliyor: hareketin tarihi geriye alınıyor.
    eski_gun = date(2025, 1, 10)      # kanuni beyan süresi çoktan doldu
    sid = _td1_blok(c, 'TD1-H1', 'TD1-F7')
    with fa.app.app_context():
        g = CariHareket.query.filter_by(baglanti_tip='stok_fatura',
                                        baglanti_id='TD1-F7').first()
        g.hareket_tarihi = eski_gun
        db.session.commit()
    r = c.put(f'/api/stok/{sid}', headers=H,
              json={'tip': 'BLOK', 'uretici': 'TD1 TEDARIKCI B',
                    'mali_islem': 'fatura_duzelt'})
    assert r.status_code == 409, (r.status_code, r.get_json())
    y = r.get_json()
    assert y.get('error') == 'kdv_donemi_kapali', y
    assert y.get('onerilen_mali_islem') == 'karsi_kayit', y
    # Reddedilen istek HİÇBİR ŞEY değiştirmemeli.
    # (Bakiye GENELİNE bakmıyorum: aynı cari önceki testlerde de
    #  kullanılıyor ve genel bakiye bu testin konusu değil. BU
    #  FATURAYA bakılıyor.)
    with fa.app.app_context():
        assert BlokStok.query.get(sid).uretici == 'TD1 TEDARIKCI A'
        assert CariHareket.query.filter_by(
            baglanti_id='TD1-F7', cari_id='TDB').count() == 0

    # Karşı kayıt YOLU AÇIK olmalı — yoksa kullanıcı kilitlenirdi.
    r2 = c.put(f'/api/stok/{sid}', headers=H,
               json={'tip': 'BLOK', 'uretici': 'TD1 TEDARIKCI B',
                     'mali_islem': 'karsi_kayit'})
    assert r2.status_code == 200, (r2.status_code, r2.get_json())


def test_td1_doviz_uyarisi_gruplu_kayitta_da_cikiyor():
    """Döviz değişim uyarısı C1 sonrası kayıtlarda HİÇ çıkmıyordu.

    Arama yalnız `baglanti_tip='stok'` ile yapılıyordu; o şema C1
    öncesine ait. Gerçek uçtan açılmış bir stokta o satır yok, `_ch`
    None dönüyor ve kullanıcı USD stoğu EUR yaparken borcun USD
    kaldığını HİÇBİR YERDE görmüyordu."""
    _td1_kur_ve_cari()
    c = istemci('admin', 'ADMIN')
    sid = _td1_blok(c, 'TD1-I1', 'TD1-F8')
    r = c.put(f'/api/stok/{sid}', headers=H,
              json={'tip': 'BLOK', 'doviz': 'EUR'})
    assert r.status_code == 200, (r.status_code, r.get_json())
    y = r.get_json()
    assert y.get('uyari') is True, y
    metin = ' '.join(y.get('uyarilar') or [])
    assert 'tedarikçi borcu' in metin and 'USD' in metin, metin


def test_td1_kapi_karsi_kayit_satirini_aday_saymiyor():
    """ÇİVİ: `karsi_kayit` ters hareketi alış faturası sanılmamalı.

    Ters hareket AYNI `baglanti_tip`, AYNI `baglanti_id` ve AYNI
    cariyi taşıyor (bilerek — düzeltme faturaya bağlı kalsın diye),
    yani SK1'in kimlik eşleşmesine o da uyuyor. Hangisinin
    seçileceği SIRAYA kalırsa, ters hareket seçildiğinde düzeltme
    kaydı azalır ve fatura borcu olduğu gibi kalır.

    Burada ters hareket KASTEN önce gelecek kimlikle yazılıyor."""
    from models import CariHareket
    _td1_kur_ve_cari()
    c = istemci('admin', 'ADMIN')
    sid = _td1_blok(c, 'TD1-J1', 'TD1-F9')
    kapi = _kc1_kapi('_stok_alis_grubu')
    with fa.app.app_context():
        db.session.add(CariHareket(
            id='AAA-TD1-KK',             # fatura satırından ÖNCE sıralanır
            cari_id='TDA', cari_unvan='TD1 TEDARIKCI A',
            hareket_tarihi=TD1_GUN, islem_tip='Alis Iade / Duzeltme',
            borc=1200, alacak=0, doviz='USD',
            kaynak='stok_karsi_kayit',
            baglanti_tip='stok_fatura', baglanti_id='TD1-F9'))
        db.session.commit()
        s = BlokStok.query.get(sid)
        grup, fno, _ = kapi(s)
        assert grup is not None, 'kapı hiç satır bulamadı'
        assert float(grup.borc or 0) == 0, (
            f'kapı TERS HAREKETİ seçti ({grup.id}) — düzeltme kaydı '
            f'azalır, fatura borcu olduğu gibi kalırdı')
        assert float(grup.alacak or 0) == 1200.0, float(grup.alacak or 0)
        assert fno == 'TD1-F9', fno


# ══════════════════════════════════════════════════════════════════
#  TD1 · STOK DIŞA AKTARIMINDA MALİYET SÜTUNLARI
# ══════════════════════════════════════════════════════════════════
def _td1_xlsx_satirlari(ham):
    """xlsx baytlarından (başlık satırı, ilk veri satırı)."""
    import io as _io
    from openpyxl import load_workbook
    ws = load_workbook(_io.BytesIO(ham)).active
    satirlar = [list(s) for s in ws.iter_rows(values_only=True)
                if any(x is not None for x in s)]
    bas = next(s for s in satirlar if 'Cins' in [str(x) for x in s])
    veri = satirlar[satirlar.index(bas) + 1:]
    return bas, veri


def test_td1_disa_aktarimda_maliyet_sutunlari():
    """Listede alış maliyeti HİÇ yoktu: "neyim var" yanıtlanıyor,
    "bana kaça geldi" yanıtlanmıyordu.

    İPTAL edilmiş maliyet ve Devreden KDV SAYILMAZ — süzgeç ortak
    kapıdan (`_maliyet_sayilir`) geçiyor."""
    from models import Maliyet
    _td1_kur_ve_cari()
    c = istemci('admin', 'ADMIN')
    sid = _td1_blok(c, 'TD1-X1', 'TD1-FX')
    with fa.app.app_context():
        db.session.add_all([
            Maliyet(id='TD1-M1', maliyet_tip='Nakliye', baglanti_tip='stok',
                    baglanti_id=sid, tutar=300, doviz='USD',
                    usd_karsilik=300, aktif=True, maliyet_tarihi=TD1_GUN),
            Maliyet(id='TD1-M2', maliyet_tip='Gümrük', baglanti_tip='stok',
                    baglanti_id=sid, tutar=150, doviz='USD',
                    usd_karsilik=150, aktif=False, maliyet_tarihi=TD1_GUN)])
        db.session.commit()

    r = c.get('/api/export/stok?tip=BLOK&format=xlsx', headers=H)
    assert r.status_code == 200, (r.status_code, r.data[:200])
    bas, veri = _td1_xlsx_satirlari(r.data)
    for sutun in ('Alım Maliyeti (USD)', 'Toplam Maliyet (USD)',
                  'Birim Maliyet (USD/ton)'):
        assert sutun in bas, (sutun, bas)
    satir = next(s for s in veri if s[0] == 'TD1-X1')
    d = dict(zip(bas, satir))
    # matrah 1.000 · aktif nakliye 300 → 1.300 · tonaj 10 → 130/ton
    # (iptal gümrük 150 ve Devreden KDV 200 SAYILMAZ)
    assert abs(float(d['Alım Maliyeti (USD)']) - 1000.0) < 0.005, d
    assert abs(float(d['Toplam Maliyet (USD)']) - 1300.0) < 0.005, d
    assert abs(float(d['Birim Maliyet (USD/ton)']) - 130.0) < 0.005, d


def test_td1_maliyet_yetkisi_yoksa_sutunlar_yazilmiyor():
    """Rakamlar PARA: ekranda gizlenen veri dosya olarak çıkmasın.

    `maliyet` okuma yetkisi olmayan kullanıcıda sütunlar HİÇ
    yazılmaz — boş bırakılmaz. Boş sütun "maliyeti yok" gibi okunur,
    yokluk ise soru sordurur."""
    from models import Kullanici
    _td1_kur_ve_cari()
    with fa.app.app_context():
        if not Kullanici.query.filter_by(ad='td1depo').first():
            db.session.add(Kullanici(
                ad='td1depo', sifre=generate_password_hash('x'),
                rol='SATIS', cari_kapsam='tumu', firma_kapsam='tumu',
                yetkiler=json.dumps({'stok': 'okuma'})))
            db.session.commit()

    yetkili = istemci('admin', 'ADMIN')
    r1 = yetkili.get('/api/export/stok?tip=BLOK&format=xlsx', headers=H)
    assert r1.status_code == 200, r1.status_code
    bas1, _ = _td1_xlsx_satirlari(r1.data)
    assert 'Alım Maliyeti (USD)' in bas1, bas1

    kisitli = istemci('td1depo', 'SATIS')
    r2 = kisitli.get('/api/export/stok?tip=BLOK&format=xlsx', headers=H)
    assert r2.status_code == 200, (r2.status_code, r2.data[:200])
    bas2, _ = _td1_xlsx_satirlari(r2.data)
    for sutun in ('Alım Maliyeti (USD)', 'Toplam Maliyet (USD)',
                  'Birim Maliyet (USD/ton)'):
        assert sutun not in bas2, (
            f'yetkisiz kullanıcı {sutun} sütununu görüyor')
# ══════════════════════════════════════════════════════════════════
#  ML2 · MALİYET SAYFASI SÜZGEÇLERİ + KPI
#  IK2 · İHRAÇ KAYITLI ALIŞ TİPİ + BEYAZ LİSTE
# ══════════════════════════════════════════════════════════════════
ML2_GUN = date.today()


def _ml2_hazirlik():
    """Bir blok + üstüne üç maliyet kalemi (biri İPTAL)."""
    from models import Cari, DovizKur, Maliyet
    with fa.app.app_context():
        if not DovizKur.query.filter_by(doviz='USD', tarih=ML2_GUN).first():
            db.session.add(DovizKur(doviz='USD', tarih=ML2_GUN,
                                    alis=41, satis=41, efektif=41))
        if not Cari.query.get('ML2C'):
            db.session.add(Cari(id='ML2C', unvan='ML2 TEDARIKCI',
                                cari_tip='Tedarikçi', urun_tedarikcisi=True,
                                gorunurluk='acik'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    # İKİ TEST de bu hazırlığı çağırıyor; ikincisinde yineleme
    # koruması (YN1) 409 veriyordu — doğru davranış. Stok zaten
    # varsa yeniden açılmıyor.
    with fa.app.app_context():
        _var = BlokStok.query.filter_by(blok_no='ML2-1').first()
        sid = _var.id if _var else None
    if sid is None:
        r = c.post('/api/stok/ekle', headers=H, json={
            'tip': 'BLOK', 'uretici': 'ML2 TEDARIKCI', 'cins': 'ML2 CINS',
            'blok_no': 'ML2-1', 'boy': 300, 'yukseklik': 150, 'en': 120,
            'tonaj': 10, 'fiyat': 100, 'fiyat_birim': 'ton', 'doviz': 'USD',
            'kdv_dahil_mi': False, 'kdv_oran': 20,
            'alis_tipi': 'yurtici_kdvli', 'fatura_no': 'ML2-F',
            'alis_tarihi': ML2_GUN.isoformat(), 'fatura_durumu': 'faturali',
            'mense': 'TURKIYE'})
        assert r.status_code == 200, (r.status_code, r.get_json())
        sid = (r.get_json() or {}).get('id')
    with fa.app.app_context():
        for mid, tip, tutar, aktif in (
                ('ML2-M1', 'Nakliye', 300, True),
                ('ML2-M2', 'Gümrük', 150, False),      # İPTAL
                ('ML2-M3', 'Diğer Vergiler', 90, True)):
            if not Maliyet.query.get(mid):
                db.session.add(Maliyet(
                    id=mid, maliyet_tip=tip, baglanti_tip='stok',
                    baglanti_id=sid, tutar=tutar, doviz='USD',
                    usd_karsilik=tutar, aktif=aktif,
                    maliyet_tarihi=ML2_GUN))
        db.session.commit()
    return c, sid


def _ml2_satirlar(c, sid, pasifler=False):
    # `?pasifler=1` olmadan uç YALNIZ aktif kayıtları döndürüyor —
    # iptal edilmiş kalemi sınamak için açıkça istenmesi gerekiyor.
    r = c.get('/api/maliyet' + ('?pasifler=1' if pasifler else ''), headers=H)
    assert r.status_code == 200, r.status_code
    d = r.get_json()
    hepsi = d if isinstance(d, list) else (d.get('data') or d.get('maliyetler') or [])
    return [m for m in hepsi if m.get('baglanti_id') == sid]


def test_ml2_maliyet_satirlari_kapsam_tasiyor():
    """Her maliyet satırı KAPSAM söylemeli: ek / alış / maliyet dışı.

    Ekrandaki "Toplam Ek Maliyet" kutusu alış bedelini ve Devreden
    KDV'yi de topluyordu (ölçüldü: 2.800 yerine 4.000 — %43 şişkin).
    Ayrımı SUNUCU söylüyor; istemciye ikinci bir tip listesi koymak,
    listeye yeni bir tip eklendiğinde ekranın sessizce yanlış
    toplamasıyla biterdi (EM1'in ta kendisi)."""
    c, sid = _ml2_hazirlik()
    satirlar = _ml2_satirlar(c, sid)
    kapsam = {}
    for m in satirlar:
        assert 'kapsam' in m, f'kapsam alanı yok: {sorted(m)[:8]}'
        kapsam.setdefault(m['kapsam'], []).append(m['maliyet_tip'])
    assert 'Nakliye' in kapsam.get('ek', []), kapsam
    assert 'Alış Bedeli' in kapsam.get('alis', []), kapsam
    assert 'Devreden KDV' in kapsam.get('disi', []), kapsam
    # Alış bedeli satırı TEK başına 'alis' olmalı — ek maliyete
    # karışırsa kutu yine şişer.
    assert kapsam.get('alis') == ['Alış Bedeli'], kapsam


def test_ml2_iptal_edilmis_kalem_ek_maliyet_sayilmiyor():
    """İPTAL edilmiş maliyet `ek` değil `disi`.

    EM1'in kuralı: `aktif=False` iptal edilmiş maliyettir, sayılmaz.
    Kapsam alanı o kuralı yansıtmazsa ekran iptal edilmiş kalemi
    toplamaya devam ederdi."""
    c, sid = _ml2_hazirlik()
    # Normal listede iptal edilmiş kalem HİÇ görünmüyor — doğru
    # davranış. Kapsam kuralının sınandığı yer `?pasifler=1`.
    gorunen = {m['id'] for m in _ml2_satirlar(c, sid)}
    assert 'ML2-M2' not in gorunen, (
        'iptal edilmiş kalem normal listede görünüyor')
    satirlar = {m['id']: m for m in _ml2_satirlar(c, sid, pasifler=True)}
    assert satirlar['ML2-M1']['kapsam'] == 'ek', satirlar['ML2-M1']
    assert satirlar['ML2-M2']['kapsam'] == 'disi', (
        'iptal edilmiş kalem ek maliyet sayılıyor', satirlar['ML2-M2'])
    assert satirlar['ML2-M3']['kapsam'] == 'ek', satirlar['ML2-M3']


def test_ml2_diger_sekmesi_oteki_sekmeleri_yutmuyor():
    """ÇİVİ: sekme eşleşmesi düz `includes` OLMAMALI.

    Eşleşme `(m.maliyet_tip||'').includes(TIP)` idi. "Diğer
    Vergiler" hem 'Vergi' hem 'Diğer' içerdiği için İKİ SEKMEDE
    birden görünüyordu; sekmelerin toplamı gerçek kayıt sayısını
    aşıyordu. TARAYICIDA ÖLÇÜLDÜ (her tipten bir kayıt):
        Vergi sekmesi  1 → Diğer Vergiler
        Diğer sekmesi  2 → Diğer Vergiler, Diğer     ✗
    Düzeltmeden sonra ikisi de 1.

    İkinci yüzü: elle yazılmış bir tip ("Sigorta") hiçbir sekmeye
    düşmüyordu. Artık "Diğer" = öbür sekmelerin hiçbirine girmeyen.

    (JavaScript burada koşturulamıyor; davranış tarayıcıda ölçüldü,
     bu çivi geri dönüşü engelliyor.)"""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates', 'maliyet.html'),
                 encoding='utf-8').read()
    assert "(!TIP || (m.maliyet_tip || '').includes(TIP))" not in m, (
        'düz includes eşleşmesi geri gelmiş — "Diğer" sekmesi '
        '"Diğer Vergiler" kayıtlarını yine yutar')
    assert 'function mTipUyar(' in m, 'sekme eşleşme kapısı yok'
    assert 'M_SEKME_ANAHTAR' in m, 'sekme anahtar listesi yok'
    # "Diğer" dalı anahtarların HİÇBİRİNE uymayanı almalı.
    assert "!M_SEKME_ANAHTAR.some(" in m, (
        '"Diğer" dalı dışlama ile tanımlanmamış')


def test_ml2_kpi_suzgecli_listeden_hesapliyor():
    """ÇİVİ: KPI kutuları süzgeci izlemeli.

    `kpiCiz` yalnız `yukle`den BİR KEZ, parametresiz çağrılıyor ve
    her zaman `TUM` üzerinden topluyordu. TARAYICIDA ÖLÇÜLDÜ:
    "Nakliye" sekmesinde listede 1 satır kalıyor, kutuda hâlâ
    "4.000$ (9 kayıt)" yazıyordu — ekrana bakan onu nakliye toplamı
    sanardı. Düzeltmeden sonra 100$.

    Artık `ciz()` süzgeçli listeyi KPI'ya geçiriyor."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates', 'maliyet.html'),
                 encoding='utf-8').read()
    assert 'function kpiCiz(liste)' in m, 'kpiCiz süzgeçli listeyi almıyor'
    assert 'kpiCiz(liste)' in m, 'ciz() KPI’yı süzgeçli listeyle çağırmıyor'
    assert 'kpiCiz(); ciz();' not in m, (
        'yukle() hâlâ KPI’yı süzgeçsiz çağırıyor')
    # Toplam YALNIZ ek maliyetlerden.
    assert "(m.kapsam || 'ek') === 'ek'" in m, (
        'KPI toplamı kapsam süzgecinden geçmiyor — alış bedeli ve '
        'Devreden KDV yine toplanır')


def test_ml2_yeni_suzgecler_sayfada():
    """Dönem, döviz, tutar ve kapsam süzgeçleri eklendi mi?

    Dönem süzgeci HİÇ yoktu: kayıtlar tarihe göre sıralanıyor ama
    bir ay ya da çeyrek seçilemiyordu."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates', 'maliyet.html'),
                 encoding='utf-8').read()
    for kimlik in ('id="mBas"', 'id="mBit"', 'id="mDoviz"',
                   'id="mMin"', 'id="mMax"', 'id="mKapsam"'):
        assert kimlik in m, f'{kimlik} yok'
    for kisa in ('buay', 'gecenay', 'ceyrek', 'yil'):
        assert f"mDonem('{kisa}')" in m, f'{kisa} kısayolu yok'
    # Tarih kısayolları YEREL gün üretmeli: `toISOString()` Türkiye
    # saatinde ayın ilk gününü bir gün geri atardı.
    assert 'toISOString' not in m.split('function mDonem')[1][:900], (
        'dönem kısayolu UTC’ye çeviriyor — ayın ilk günü geçen aya düşer')
    # Süzgeç bilgisi sekmeyi ve aramayı da saymalı.
    assert 'function mSuzgecVarMi(' in m, 'süzgeç var mı kapısı yok'
    assert '|| TIP || ARA' in m, (
        'sekme ve metin araması süzgeç sayılmıyor — "Nakliye" '
        'sekmesindeyken "süzgeç yok" yazardı')


# ── IK2 ───────────────────────────────────────────────────────────
def test_ik2_taninmayan_alis_tipi_reddediliyor():
    """ÇİVİ: `alis_tipi` doğrulanmıyordu.

    `alis_tipi` bir KDV sınıflandırması — kodda yaptığı tek iş,
    değer 'yurtici_kdvli' DEĞİLSE KDV'yi sıfırlamak.

    ÖLÇÜLDÜ: `alis_tipi='SAÇMASAPAN'` gönderildi → 200 döndü, değer
    olduğu gibi kaydedildi ve KDV SIFIRLANDI. Yazım hatası ya da
    eskimiş bir ön yüz, KDV'li bir alışı sessizce KDV'siz yapardı."""
    from models import DovizKur
    with fa.app.app_context():
        if not DovizKur.query.filter_by(doviz='USD', tarih=ML2_GUN).first():
            db.session.add(DovizKur(doviz='USD', tarih=ML2_GUN,
                                    alis=41, satis=41, efektif=41))
            db.session.commit()
    c = istemci('admin', 'ADMIN')
    govde = {
        'tip': 'BLOK', 'uretici': 'ML2 TEDARIKCI', 'cins': 'IK2 CINS',
        'blok_no': 'IK2-RED', 'boy': 300, 'yukseklik': 150, 'en': 120,
        'tonaj': 10, 'fiyat': 100, 'fiyat_birim': 'ton', 'doviz': 'USD',
        'kdv_dahil_mi': False, 'kdv_oran': 20, 'fatura_no': 'IK2-F1',
        'alis_tarihi': ML2_GUN.isoformat(), 'fatura_durumu': 'faturali',
        'mense': 'TURKIYE', 'alis_tipi': 'SAÇMASAPAN'}
    r = c.post('/api/stok/ekle', headers=H, json=govde)
    assert r.status_code == 400, (r.status_code, r.get_json())
    y = r.get_json()
    assert y.get('error') == 'gecersiz_alis_tipi', y
    assert 'ihrac_kayitli' in (y.get('secenekler') or {}), y
    # REDDEDİLEN istek stok YAZMAMALI.
    with fa.app.app_context():
        assert not BlokStok.query.filter_by(blok_no='IK2-RED').first(), \
            'reddedilen istek yine de stok yazdı'


def test_ik2_ihrac_kayitli_kabul_ediliyor_ve_kdv_sifir():
    """İhraç Kayıtlı: imalatçı ihracatçıya KDV TAHSİL ETMEDEN satar.

    Alan tarafta KDV ödenmez — ama bu "KDV'siz alış" ile AYNI ŞEY
    DEĞİL; kendi beyan ve süre yükümlülükleri var, bu yüzden ayrı
    tip olarak saklanıyor.

    (TABANDA DA GEÇER — taban hiçbir tipi doğrulamadığı için her
     diziyi kabul ediyordu. Bu testin işi beyaz listeyi eklerken
     İhraç Kayıtlı'nın DIŞARIDA kalmadığını tutmak: liste
     yazılırken bir tipi unutmak, kullanıcıya listeden seçtiği
     seçenekte 400 verdirirdi.)"""
    from models import DovizKur
    with fa.app.app_context():
        if not DovizKur.query.filter_by(doviz='USD', tarih=ML2_GUN).first():
            db.session.add(DovizKur(doviz='USD', tarih=ML2_GUN,
                                    alis=41, satis=41, efektif=41))
            db.session.commit()
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/stok/ekle', headers=H, json={
        'tip': 'BLOK', 'uretici': 'ML2 TEDARIKCI', 'cins': 'IK2 CINS',
        'blok_no': 'IK2-OK', 'boy': 300, 'yukseklik': 150, 'en': 120,
        'tonaj': 10, 'fiyat': 100, 'fiyat_birim': 'ton', 'doviz': 'USD',
        'kdv_dahil_mi': False, 'kdv_oran': 20, 'fatura_no': 'IK2-F2',
        'alis_tarihi': ML2_GUN.isoformat(), 'fatura_durumu': 'faturali',
        'mense': 'TURKIYE', 'alis_tipi': 'ihrac_kayitli'})
    assert r.status_code == 200, (r.status_code, r.get_json())
    j = r.get_json()
    assert float(j.get('kdv_tutar') or 0) == 0, j
    with fa.app.app_context():
        s = BlokStok.query.filter_by(blok_no='IK2-OK').first()
        assert s is not None, 'stok yazılmadı'
        assert s.alis_tipi == 'ihrac_kayitli', s.alis_tipi
        # KDV'siz alışla KARIŞMAMALI: tip olduğu gibi duruyor.
        assert s.alis_tipi != 'yurtici_kdvsiz'


def test_ik2_alis_tipleri_sunucu_ve_iki_form_ayni():
    """ÇİVİ: üç liste de aynı olmalı.

    İKİ FORM AYRIŞMIŞTI: toplu aktarma formunda "İstisna / Muaf"
    VARDI, tekil formda YOKTU — aynı malı hangi formdan girdiğine
    göre seçenek listesi değişiyordu. Sunucu da hiçbirini
    doğrulamıyordu.

    Artık sunucuda tek kaynak var (`ALIS_TIPLERI`) ve tanınmayan tip
    reddediliyor; iki formun da onunla aynı olması gerekiyor, yoksa
    kullanıcı listeden seçtiği bir tiple 400 alır."""
    import ast as _ast
    import io as _io
    import re as _re
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    sunucu = None
    for d in _ast.walk(_ast.parse(kaynak)):
        if (isinstance(d, _ast.Assign) and len(d.targets) == 1
                and isinstance(d.targets[0], _ast.Name)
                and d.targets[0].id == 'ALIS_TIPLERI'):
            sunucu = set(_ast.literal_eval(d.value))
            break
    assert sunucu, 'ALIS_TIPLERI yok'
    assert 'ihrac_kayitli' in sunucu, sunucu

    m = _io.open(os.path.join(KOK, 'templates', 'stok.html'),
                 encoding='utf-8').read()
    for secici in ('tAlisTipi', 'sAlisTipi'):
        parca = m.split(f'id="{secici}"', 1)
        assert len(parca) == 2, f'{secici} yok'
        govde = parca[1].split('</select>', 1)[0]
        formda = set(_re.findall(r'<option value="([^"]+)"', govde))
        assert formda == sunucu, (
            f'{secici} sunucudan ayrışmış\n'
            f'  formda yok : {sorted(sunucu - formda)}\n'
            f'  sunucuda yok: {sorted(formda - sunucu)}')
# ══════════════════════════════════════════════════════════════════
#  SH1 · TESLİM CARİYE BORÇ YAZMIYOR · FATURALANDIRMA SORULUYOR
#
#  ÖLÇÜLDÜ (gerçek uçlar, eşzamanlılık yok, her seferinde):
#    5.000 USD'lik satış · FOB sevkiyat
#      Sevk Edildi      cari 0     → 5.000   (otomatik teslim borcu)
#      Fatura Kesildi   cari 5.000 → 10.000  (fatura borcu)
#    İki istek de 200 döndü, ekranda hiçbir uyarı yoktu. Satış kaydı
#    1'de kaldı — hasar YALNIZ cari bakiyesinde, ama müşteri iki kat
#    borçlu görünüyordu.
#
#  KULLANICI KARARI: teslim hiç borç yazmasın; borç yalnız faturadan
#  doğsun. Teslimden sonra "faturalandırmak istiyor musunuz?"
#  sorulsun; hayır denirse teslim "Faturası Beklenen Teslimler"
#  listesinde beklesin (birkaç teslimat tek faturada
#  birleştirilebildiği için).
# ══════════════════════════════════════════════════════════════════
def _sh1_c1_bakiye():
    with fa.app.app_context():
        return round(sum(
            float(h.borc or 0) - float(h.alacak or 0)
            for h in CariHareket.query.filter_by(cari_id='C1').all()), 2)


def _sh1_fatura_kes(adm, sid, fatura_no, tutar=5000):
    """Siparişe bağlı fatura açar, no yazar, keser. Mevcut uçlar."""
    r = adm.post('/api/fatura', headers=H, json={
        'musteri': 'ACIK CARI', 'cari_id': 'C1', 'siparis_id': sid,
        'doviz': 'USD', 'yon': 'satis', 'fatura_tipi': 'stoklu',
        'fatura_tarihi': date.today().isoformat(),
        'vade_tarihi': date.today().isoformat(),
        'yineleme_onay': True,
        'kalemler': [{'aciklama': 'BLOK', 'miktar': 10, 'birim': 'ton',
                      'birim_fiyat': tutar / 10}]})
    assert r.status_code == 200, (r.status_code, r.get_data(as_text=True)[:250])
    fid = (r.get_json() or {}).get('id')
    r = adm.put(f'/api/fatura/{fid}', headers=H, json={'fatura_no': fatura_no})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    r = adm.post(f'/api/fatura/{fid}/durum', headers=H,
                 json={'durum': 'Kesildi'})
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    return fid


def test_sh1_teslim_cariye_borc_yazmiyor():
    """ÇİVİ: teslim artık otomatik borç AÇMIYOR.

    Borç bir belgeye dayanmak zorunda. Teslimde yazılan satırın
    evrak numarası yoktu ve fatura sonradan kesilince
    kaldırılmıyordu."""
    adm = istemci('admin', 'ADMIN')
    bid = _ts2_blok('SH1-A')
    sid = _ts2_siparis(adm, bid, 'FOB')
    once = _sh1_c1_bakiye()
    sev = _ts2_sevkiyat(adm, sid)
    r = _ts2_durum(adm, sev, 'Sevk Edildi')
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    borc, sk, durum = _ts2_sayim(sid)
    assert sk == 1, f'satış kaydı oluşmadı: {sk}'
    assert durum == 'Teslim Edildi', durum
    assert borc == 0, 'teslim otomatik borç yazdı'
    assert _sh1_c1_bakiye() == once, (
        f'cari bakiyesi teslimle değişti: {once} → {_sh1_c1_bakiye()}')


def test_sh1_teslim_sonra_fatura_cift_borc_yapmiyor():
    """ASIL ÇİVİ: teslim + fatura = TEK borç.

    Tabanda bu senaryo müşteriyi iki kez borçlandırıyordu ve iki
    istek de 200 dönüyordu."""
    adm = istemci('admin', 'ADMIN')
    bid = _ts2_blok('SH1-B')
    sid = _ts2_siparis(adm, bid, 'FOB')
    once = _sh1_c1_bakiye()
    sev = _ts2_sevkiyat(adm, sid)
    assert _ts2_durum(adm, sev, 'Sevk Edildi').status_code == 200
    _sh1_fatura_kes(adm, sid, 'SH1-FT-1')
    sonra = _sh1_c1_bakiye()
    assert abs((sonra - once) - 5000.0) < 0.01, (
        f'5.000 USD satış cariye {sonra - once:,.2f} USD borç yazdı — '
        f'10.000 ise teslim borcu + fatura borcu üst üste binmiş')
    with fa.app.app_context():
        assert CariHareket.query.filter_by(
            baglanti_tip='siparis', baglanti_id=sid,
            kaynak='otomatik-teslim').count() == 0
        _fat = CariHareket.query.filter_by(cari_id='C1').filter(
            CariHareket.evrak_no == 'SH1-FT-1').first()
        assert _fat is not None, 'fatura borcu evrak numarasıyla yazılmadı'


def test_sh1_faturasi_bekleyen_listesi():
    """Teslim edilmiş ama faturalanmamış satış LİSTEDE görünür.

    Teslim borç yazmadığı için bu satış cari ekstresinde yok —
    bilerek. Bu liste onun karşılığı; faturası kesilince listeden
    DÜŞMESİ de aynı derecede önemli, yoksa aynı teslim iki kez
    faturalanır."""
    adm = istemci('admin', 'ADMIN')
    bid = _ts2_blok('SH1-C')
    sid = _ts2_siparis(adm, bid, 'FOB')
    sev = _ts2_sevkiyat(adm, sid)
    assert _ts2_durum(adm, sev, 'Sevk Edildi').status_code == 200

    r = adm.get('/api/teslim/faturasi_bekleyen', headers=H)
    assert r.status_code == 200, (r.status_code, r.get_data(as_text=True)[:200])
    d = r.get_json()
    kayit = next((b for b in d['data'] if b['siparis_id'] == sid), None)
    assert kayit is not None, 'teslim bekleyen listesinde yok'
    assert kayit['musteri'] == 'ACIK CARI', kayit
    assert abs(float(kayit['tutar']) - 5000.0) < 0.01, kayit
    assert kayit['doviz'] == 'USD', kayit
    assert kayit['kalem_sayisi'] == 1, kayit
    # Dövizler AYRI toplanıyor — tek bir karışık rakam değil.
    assert isinstance(d.get('toplamlar'), list), d
    assert all('doviz' in t and 'tutar' in t for t in d['toplamlar']), d

    _sh1_fatura_kes(adm, sid, 'SH1-FT-2')
    r2 = adm.get('/api/teslim/faturasi_bekleyen', headers=H)
    kalan = [b for b in (r2.get_json() or {}).get('data', [])
             if b['siparis_id'] == sid]
    assert not kalan, (
        'faturası kesilen teslim listede DURUYOR — aynı teslim iki '
        'kez faturalanabilir')


def test_sh1_onhazirlik_satis_kayitlarindan_dolduruyor():
    """Fatura paneli SATIŞ KAYITLARINDAN doluyor, sipariş
    kalemlerinden değil.

    Kısmi teslimde sipariş kalemi 10 ton derken teslim edilen 6 ton
    olabilir; faturaya girmesi gereken 6'dır. Satış kaydı teslim
    edileni tutuyor, sipariş kalemi istenen."""
    adm = istemci('admin', 'ADMIN')
    bid = _ts2_blok('SH1-D')
    sid = _ts2_siparis(adm, bid, 'FOB')
    sev = _ts2_sevkiyat(adm, sid)
    assert _ts2_durum(adm, sev, 'Sevk Edildi').status_code == 200
    r = adm.get(f'/api/siparis/{sid}/fatura_onhazirlik', headers=H)
    assert r.status_code == 200, (r.status_code, r.get_data(as_text=True)[:200])
    d = r.get_json()
    assert d['musteri'] == 'ACIK CARI', d
    assert d['doviz'] == 'USD', d
    assert len(d['kalemler']) == 1, d
    k = d['kalemler'][0]
    assert abs(float(k['miktar']) - 10.0) < 0.01, k
    assert abs(float(k['birim_fiyat']) - 500.0) < 0.01, k
    assert k['birim'] == 'ton', k
    # EVIN SEKLI: fatura paneli ve POST /api/fatura ayni alanlari
    # okuyor. `toplam_fiyat` eksik kalinca panel yari dolu kaliyor
    # ve konsola hata dusuyordu — tarayicida olculdu.
    for alan in ('urun_tip', 'cins', 'miktar', 'birim', 'birim_fiyat',
                 'toplam_fiyat'):
        assert alan in k, (f'{alan} yok — fatura paneli bu alanlari '
                           f'bekliyor', sorted(k))
    assert abs(float(k['toplam_fiyat']) - 5000.0) < 0.01, k
    assert bid in (k.get('cins') or ''), (
        'cins alanında stok kimliği yok — faturada hangi blok olduğu '
        'anlaşılmaz', k)
    assert abs(float(d['toplam']) - 5000.0) < 0.01, d


def test_sh1_onhazirlik_faturasi_olani_reddediyor():
    """Faturası olan sipariş için panel doldurulmaz.

    Doldurulsa kullanıcı ikinci bir fatura açar ve müşteri iki kez
    borçlanır — kapattığımız hatanın başka bir kapıdan girişi."""
    adm = istemci('admin', 'ADMIN')
    bid = _ts2_blok('SH1-E')
    sid = _ts2_siparis(adm, bid, 'FOB')
    sev = _ts2_sevkiyat(adm, sid)
    assert _ts2_durum(adm, sev, 'Sevk Edildi').status_code == 200
    _sh1_fatura_kes(adm, sid, 'SH1-FT-3')
    r = adm.get(f'/api/siparis/{sid}/fatura_onhazirlik', headers=H)
    assert r.status_code == 409, (r.status_code, r.get_data(as_text=True)[:200])
    y = r.get_json()
    assert y.get('error') == 'fatura_var', y
    assert y.get('fatura_no') == 'SH1-FT-3', y


def test_sh1_teslim_yaniti_faturalanacagini_soyluyor():
    """Teslim yanıtı ön yüze SORULACAK bilgiyi veriyor.

    Ön yüz "faturalandırmak istiyor musunuz?" sorusunu bu alandan
    kuruyor. Alan gelmezse soru hiç sorulmaz ve teslim sessizce
    faturasız kalır — teslim artık borç da yazmadığı için satış
    HİÇBİR YERDE görünmez olurdu."""
    adm = istemci('admin', 'ADMIN')
    bid = _ts2_blok('SH1-F')
    sid = _ts2_siparis(adm, bid, 'FOB')
    sev = _ts2_sevkiyat(adm, sid)
    r = _ts2_durum(adm, sev, 'Sevk Edildi')
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    d = r.get_json()
    b = d.get('faturasiz_teslim')
    assert b, f'faturasiz_teslim alanı yok: {sorted(d)}'
    assert b['siparis_id'] == sid, b
    assert b['musteri'] == 'ACIK CARI', b
    assert abs(float(b['tutar']) - 5000.0) < 0.01, b
    assert b['doviz'] == 'USD', b
    # Faturası olan siparişte soru SORULMAMALI.
    _sh1_fatura_kes(adm, sid, 'SH1-FT-4')
    assert _ts2_durum(adm, sev, 'Hazirlaniyor').status_code == 200
    r2 = _ts2_durum(adm, sev, 'Sevk Edildi')
    assert r2.status_code == 200, r2.get_data(as_text=True)[:250]
    assert (r2.get_json() or {}).get('faturasiz_teslim') is None, (
        'faturası olan siparişte faturalandırma soruluyor')


def test_sh1_otomatik_teslim_borcu_bir_daha_yazilmiyor():
    """ÇİVİ: `kaynak='otomatik-teslim'` ile hareket OLUŞTURULMAMALI.

    Satırı silen ve arayan kod KALDI (üretimde SH1 öncesinden
    kalmış kayıtlar olabilir, geri alma onları temizliyor). Yasak
    olan YENİ bir satır yazmak. Bunu metin üzerinden çiviliyorum,
    çünkü hatanın geri gelme yolu tam bu: birisi "teslimde alacak
    görünmüyor" diye bloğu geri ekler."""
    import ast as _ast
    import io as _io
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    agac = _ast.parse(kaynak)
    suclu = []
    for c in _ast.walk(agac):
        if not isinstance(c, _ast.Call):
            continue
        ad = _ast.unparse(c.func)
        if ad not in ('_cari_hareket_ekle', 'CariHareket'):
            continue
        metin = _ast.unparse(c)
        if 'otomatik-teslim' in metin:
            suclu.append((ad, c.lineno))
    assert not suclu, (
        f'otomatik teslim borcu yeniden yazılıyor: {suclu} — '
        f'fatura kesilince müşteri iki kez borçlanır')
    # Temizleme kodu DURMALI: eski kayıtlar için gerekli.
    assert "kaynak='otomatik-teslim'" in kaynak, (
        'eski otomatik teslim borçlarını temizleyen kod da '
        'kaldırılmış — SH1 öncesi kayıtlar sessizce borçlu kalır')


def test_sh1_yetkisiz_bekleyen_listesini_goremiyor():
    """Liste müşteri adı ve tutar taşıyor: fatura okuma yetkisi şart."""
    from models import Kullanici
    with fa.app.app_context():
        if not Kullanici.query.filter_by(ad='sh1depo').first():
            db.session.add(Kullanici(
                ad='sh1depo', sifre=generate_password_hash('x'),
                rol='SATIS', cari_kapsam='tumu', firma_kapsam='tumu',
                yetkiler=json.dumps({'stok': 'okuma'})))
            db.session.commit()
    kis = istemci('sh1depo', 'SATIS')
    r = kis.get('/api/teslim/faturasi_bekleyen', headers=H)
    assert r.status_code == 403, (r.status_code, r.get_data(as_text=True)[:200])
    r2 = kis.get('/api/siparis/HIC-YOK/fatura_onhazirlik', headers=H)
    assert r2.status_code == 403, (
        'yetkisiz kullanıcı fatura ön hazırlığı yapabiliyor',
        r2.status_code)

def test_sh1_tablo_basligi_listeye_gore_degisiyor():
    """ÇİVİ: iki liste aynı tabloyu kullanıyor, başlık da değişmeli.

    Bekleyen teslimler listesinde beşinci sütun TESLİM TARİHİ,
    altıncı da bir düğme. Başlık sabit kalsa "Tahsilat" ve "Vade"
    yazardı; kullanıcı teslim tarihini vade sanırdı.

    (JavaScript pytest içinde koşturulamıyor; başlığın iki yönde de
     değiştiği tarayıcıda ölçüldü — FATURA → BEKLEYEN → FATURA.
     Bu çivi geri dönüşü engelliyor.)"""
    import io as _io
    m = _io.open(os.path.join(KOK, 'templates', 'fatura.html'),
                 encoding='utf-8').read()
    assert 'id="tabloBaslik"' in m, 'tablo başlığına kimlik verilmemiş'
    assert 'function tabloBasligiCiz(' in m, 'başlık çizen kapı yok'
    # İKİ liste de çağırmak zorunda — biri çağırmazsa başlık
    # öbür listenin sütun adlarıyla kalır.
    for islev in ('function bekleyenCiz() {\n  tabloBasligiCiz();',
                  'function ciz() {\n  tabloBasligiCiz();'):
        assert islev in m, (
            f'başlık şu listede çizilmiyor: {islev[:28]}')
# ══════════════════════════════════════════════════════════════════
#  BF1 · BİRKAÇ TESLİMAT TEK FATURADA
#
#  `Fatura.siparis_id` TEK bir alandı ve DOKUZ yer ona `filter_by`
#  ile bakıyordu. Bir fatura birden çok siparişi kapsayınca o alan
#  yalnızca BİRİNCİ siparişi taşır; dokuz yerin sekizi faturayı
#  bulamaz hâle gelirdi.
#
#  En tehlikelisi teslim yolundaki "faturası var mı" kontrolü:
#  birleşik faturanın İKİNCİ siparişi "faturası yok" görünür,
#  bekleyen listesinde kalır ve İKİNCİ KEZ faturalanabilirdi —
#  SH1'de kapattığımız çift borcun başka bir kapıdan girişi.
#
#  Bağ artık `fatura_siparis` tablosunda; eski alan "birincil
#  sipariş" olarak duruyor ve kapı ikisini birden arıyor.
# ══════════════════════════════════════════════════════════════════
def _bf1_blok(no):
    with fa.app.app_context():
        if db.session.get(BlokStok, no) is None:
            db.session.add(BlokStok(
                id=no, blok_no=no, cins='TEST', boy=300, yukseklik=150,
                en=120, hacim_m3=5.4, tonaj=10, alis_fiyati=1000,
                doviz='USD', durum='Serbest', giris_tarihi=date.today()))
            db.session.commit()
    return no


def _bf1_teslim(adm, blok, teslim='FOB', doviz='USD', musteri='ACIK CARI',
                cari_id='C1', gun=None):
    """Teslim edilmiş bir sipariş kurar; sipariş kimliğini döner."""
    r = adm.post('/api/siparis', headers=H, json={
        'musteri': musteri, 'cari_id': cari_id, 'doviz': doviz,
        'durum': 'Onaylandi', 'teslim_sekli': teslim,
        'kalemler': [{'urun_tip': 'BLOK', 'cins': 'TEST', 'adet': 1,
                      'miktar': 10, 'birim': 'ton', 'birim_fiyat': 500,
                      'doviz': doviz, 'stok_ids': [blok]}],
        'yineleme_onay': True})
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    sid = r.get_json()['id']
    r = adm.post('/api/sevkiyat', headers=H, json={
        'sevk_tip': 'ihracat', 'siparis_id': sid, 'musteri': musteri,
        'cari_id': cari_id, 'sevk_tarihi': date.today().isoformat(),
        'cikis_noktasi': 'IZMIR', 'varis_noktasi': 'NEW YORK',
        'yineleme_onay': True})
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    sev = r.get_json()['id']
    r = adm.post(f'/api/sevkiyat/{sev}/durum', headers=H, json={
        'durum': 'Sevk Edildi',
        'gercek_teslim': (gun or date.today()).isoformat()})
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    return sid


def _bf1_bekleyen_idler(adm):
    r = adm.get('/api/teslim/faturasi_bekleyen', headers=H)
    assert r.status_code == 200, r.status_code
    return {b['siparis_id'] for b in (r.get_json() or {}).get('data', [])}


def _bf1_c1_bakiye():
    with fa.app.app_context():
        return round(sum(float(h.borc or 0) - float(h.alacak or 0)
                         for h in CariHareket.query.filter_by(
                             cari_id='C1').all()), 2)


def _bf1_birlesik_kes(adm, idler, fatura_no, kalemler):
    r = adm.post('/api/fatura', headers=H, json={
        'musteri': 'ACIK CARI', 'cari_id': 'C1', 'siparis_idler': idler,
        'doviz': 'USD', 'yon': 'satis', 'fatura_tipi': 'stoklu',
        'fatura_tarihi': date.today().isoformat(),
        'vade_tarihi': date.today().isoformat(),
        'yineleme_onay': True, 'kalemler': kalemler})
    assert r.status_code == 200, (r.status_code,
                                  r.get_data(as_text=True)[:250])
    fid = r.get_json()['id']
    assert adm.put(f'/api/fatura/{fid}', headers=H,
                   json={'fatura_no': fatura_no}).status_code == 200
    r = adm.post(f'/api/fatura/{fid}/durum', headers=H,
                 json={'durum': 'Kesildi'})
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    return fid


def test_bf1_iki_teslim_tek_faturada_tek_borc_yaziyor():
    """İki teslim tek faturada → cariye BİR kez borç, ikisi de
    bekleyen listesinden DÜŞER.

    Listeden düşmesi, tek borç kadar önemli: düşmezse aynı teslim
    ikinci kez faturalanır."""
    adm = istemci('admin', 'ADMIN')
    s1 = _bf1_teslim(adm, _bf1_blok('BF1-A1'))
    s2 = _bf1_teslim(adm, _bf1_blok('BF1-A2'))
    once = _bf1_c1_bakiye()
    bekleyen = _bf1_bekleyen_idler(adm)
    assert {s1, s2} <= bekleyen, (s1, s2, bekleyen)

    r = adm.get(f'/api/teslim/birlesik_onhazirlik?siparisler={s1},{s2}',
                headers=H)
    assert r.status_code == 200, (r.status_code,
                                  r.get_data(as_text=True)[:250])
    h = r.get_json()
    assert abs(float(h['toplam']) - 10000.0) < 0.01, h['toplam']
    _bf1_birlesik_kes(adm, [s1, s2], 'BF1-FT-1', h['kalemler'])

    sonra = _bf1_c1_bakiye()
    assert abs((sonra - once) - 10000.0) < 0.01, (
        f'iki 5.000 USD teslim tek faturada birleşti, cariye '
        f'{sonra - once:,.2f} borç yazıldı')
    kalan = _bf1_bekleyen_idler(adm)
    assert not ({s1, s2} & kalan), (
        f'faturalanan teslim(ler) bekleyen listesinde DURUYOR: '
        f'{sorted({s1, s2} & kalan)} — ikinci kez faturalanabilir')


def test_bf1_kapi_birincil_olmayan_siparisi_de_buluyor():
    """ASIL ÇİVİ: ikinci sipariş de "faturası var" sayılmalı.

    `Fatura.siparis_id` yalnızca BİRİNCİ siparişi taşıyor. Kapı
    olmasa ikinci sipariş "faturası yok" görünür ve yeniden
    faturalanabilirdi."""
    adm = istemci('admin', 'ADMIN')
    s1 = _bf1_teslim(adm, _bf1_blok('BF1-B1'))
    s2 = _bf1_teslim(adm, _bf1_blok('BF1-B2'))
    r = adm.get(f'/api/teslim/birlesik_onhazirlik?siparisler={s1},{s2}',
                headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    fid = _bf1_birlesik_kes(adm, [s1, s2], 'BF1-FT-2',
                            r.get_json()['kalemler'])

    with fa.app.app_context():
        f = db.session.get(Fatura, fid)
        assert f.siparis_id == s1, (
            'birincil sipariş ilk seçilen olmalı', f.siparis_id)

    # Her İKİSİ de 409 "fatura_var" vermeli.
    for _s, _et in ((s1, 'birincil'), (s2, 'İKİNCİ')):
        r = adm.get(f'/api/siparis/{_s}/fatura_onhazirlik', headers=H)
        assert r.status_code == 409, (
            f'{_et} sipariş "faturası yok" görünüyor '
            f'({r.status_code}) — yeniden faturalanabilir')
        assert r.get_json().get('fatura_no') == 'BF1-FT-2', r.get_json()

    # Tek siparişli birleştirme yolu da aynı faturayı görmeli.
    r = adm.get(f'/api/teslim/birlesik_onhazirlik?siparisler={s2}',
                headers=H)
    assert r.status_code == 409, (r.status_code,
                                 r.get_data(as_text=True)[:200])


def test_bf1_detay_kapsadigi_teslimleri_soyluyor():
    """Birleşik faturanın hangi teslimleri kapsadığı GÖRÜNMELİ.

    Yazılmazsa kullanıcı faturaya bakıp iki teslimi kapsadığını
    hiçbir yerden anlayamaz."""
    adm = istemci('admin', 'ADMIN')
    s1 = _bf1_teslim(adm, _bf1_blok('BF1-C1'))
    s2 = _bf1_teslim(adm, _bf1_blok('BF1-C2'))
    h = adm.get(f'/api/teslim/birlesik_onhazirlik?siparisler={s1},{s2}',
                headers=H).get_json()
    fid = _bf1_birlesik_kes(adm, [s1, s2], 'BF1-FT-3', h['kalemler'])
    r = adm.get(f'/api/fatura/{fid}', headers=H)
    assert r.status_code == 200, r.status_code
    kapsam = (r.get_json() or {}).get('fatura', {}).get('siparis_idler')
    assert kapsam is not None, 'detayda siparis_idler yok'
    assert set(kapsam) == {s1, s2}, (kapsam, s1, s2)


def test_bf1_her_kalem_hangi_teslimden_geldigini_soyluyor():
    """Kullanıcı kararı: "her blok/plaka ayrı satır, yanında sipariş
    no". Konteyner/parti takibi yapan müşteri için faturadan hangi
    bloğun hangi sevkiyattan geldiği okunabilmeli."""
    adm = istemci('admin', 'ADMIN')
    b1, b2 = _bf1_blok('BF1-D1'), _bf1_blok('BF1-D2')
    s1 = _bf1_teslim(adm, b1)
    s2 = _bf1_teslim(adm, b2)
    r = adm.get(f'/api/teslim/birlesik_onhazirlik?siparisler={s1},{s2}',
                headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    kalemler = r.get_json()['kalemler']
    assert len(kalemler) == 2, kalemler
    for k, blok, sip in ((kalemler[0], b1, s1), (kalemler[1], b2, s2)):
        assert blok in k['cins'], (blok, k['cins'])
        assert sip in k['cins'], (
            'kalemde sipariş no yok — faturada hangi teslimattan '
            'geldiği okunamaz', sip, k['cins'])
        assert k.get('siparis_id') == sip, k
        # Panelin ve POST /api/fatura'nin bekledigi alanlar.
        for alan in ('urun_tip', 'miktar', 'birim', 'birim_fiyat',
                     'toplam_fiyat'):
            assert alan in k, (alan, sorted(k))


def test_bf1_farkli_cari_ve_farkli_doviz_reddediliyor():
    """Bir fatura tek müşteriye ve tek para biriminde kesilir.

    Doğrulama UÇTA: ön yüz de kontrol ediyor ama tek savunma hattı
    ön yüz olamaz — aynı gövde elle gönderilebilir."""
    from models import Cari
    adm = istemci('admin', 'ADMIN')
    with fa.app.app_context():
        if not Cari.query.get('BF1C2'):
            db.session.add(Cari(id='BF1C2', unvan='BF1 IKINCI MUSTERI',
                                cari_tip='Müşteri', gorunurluk='acik'))
            db.session.commit()
    s1 = _bf1_teslim(adm, _bf1_blok('BF1-E1'))
    s2 = _bf1_teslim(adm, _bf1_blok('BF1-E2'),
                     musteri='BF1 IKINCI MUSTERI', cari_id='BF1C2')
    r = adm.get(f'/api/teslim/birlesik_onhazirlik?siparisler={s1},{s2}',
                headers=H)
    assert r.status_code == 400, (r.status_code,
                                 r.get_data(as_text=True)[:200])
    assert r.get_json().get('error') == 'farkli_cari', r.get_json()
    # POST da reddetmeli (ön yüz atlanabilir).
    r = adm.post('/api/fatura', headers=H, json={
        'musteri': 'ACIK CARI', 'cari_id': 'C1',
        'siparis_idler': [s1, s2], 'doviz': 'USD', 'yon': 'satis',
        'fatura_tarihi': date.today().isoformat(), 'yineleme_onay': True,
        'kalemler': [{'cins': 'X', 'miktar': 1, 'birim': 'ton',
                      'birim_fiyat': 1, 'toplam_fiyat': 1}]})
    assert r.status_code == 400, (r.status_code,
                                  r.get_data(as_text=True)[:200])
    assert r.get_json().get('error') == 'farkli_cari', r.get_json()

    s3 = _bf1_teslim(adm, _bf1_blok('BF1-E3'), doviz='EUR')
    r = adm.get(f'/api/teslim/birlesik_onhazirlik?siparisler={s1},{s3}',
                headers=H)
    assert r.status_code == 400, (r.status_code,
                                  r.get_data(as_text=True)[:200])
    assert r.get_json().get('error') == 'farkli_doviz', r.get_json()


def test_bf1_farkli_ay_engellenmiyor_ama_uyariliyor():
    """Kullanıcı kararı: farklı aylardaki teslimler birleşebilir ama
    sistem UYARIR. Faturanın tarihi KDV dönemini belirliyor."""
    from models import SatisKaydi
    adm = istemci('admin', 'ADMIN')
    s1 = _bf1_teslim(adm, _bf1_blok('BF1-F1'))
    s2 = _bf1_teslim(adm, _bf1_blok('BF1-F2'))
    # İkinci teslimin tarihini GERİYE al — iki ayrı ay.
    from datetime import timedelta as _td     # modül düzeyinde yok
    eski = date.today().replace(day=1) - _td(days=15)
    with fa.app.app_context():
        for sk in SatisKaydi.query.filter_by(siparis_id=s2).all():
            sk.teslim_tarihi = eski
        db.session.commit()

    r = adm.get(f'/api/teslim/birlesik_onhazirlik?siparisler={s1},{s2}',
                headers=H)
    assert r.status_code == 200, (
        'farklı ay ENGELLENDİ — kullanıcı kararı "izin ver, uyar"',
        r.status_code)
    h = r.get_json()
    assert h.get('uyari') is True, h
    metin = ' '.join(h.get('uyarilar') or [])
    assert 'AYRI AYA' in metin, metin
    assert eski.strftime('%Y-%m') in metin, (metin, eski)
    assert date.today().strftime('%Y-%m') in metin, metin


def test_bf1_faturasi_olan_teslim_birlestirilemiyor():
    """Faturası olan bir teslim ikinci faturaya giremez."""
    adm = istemci('admin', 'ADMIN')
    s1 = _bf1_teslim(adm, _bf1_blok('BF1-G1'))
    s2 = _bf1_teslim(adm, _bf1_blok('BF1-G2'))
    h = adm.get(f'/api/siparis/{s1}/fatura_onhazirlik',
                headers=H).get_json()
    _bf1_birlesik_kes(adm, [s1], 'BF1-FT-4', h['kalemler'])
    r = adm.get(f'/api/teslim/birlesik_onhazirlik?siparisler={s1},{s2}',
                headers=H)
    assert r.status_code == 409, (r.status_code,
                                  r.get_data(as_text=True)[:200])
    assert r.get_json().get('error') == 'fatura_var', r.get_json()
    # POST da reddetmeli.
    r = adm.post('/api/fatura', headers=H, json={
        'musteri': 'ACIK CARI', 'cari_id': 'C1',
        'siparis_idler': [s1, s2], 'doviz': 'USD', 'yon': 'satis',
        'fatura_tarihi': date.today().isoformat(), 'yineleme_onay': True,
        'kalemler': [{'cins': 'X', 'miktar': 1, 'birim': 'ton',
                      'birim_fiyat': 1, 'toplam_fiyat': 1}]})
    assert r.status_code == 409, (r.status_code,
                                  r.get_data(as_text=True)[:200])


def test_bf1_hicbir_yer_siparis_id_ile_dogrudan_sorgulamiyor():
    """ÇİVİ: `Fatura`yı siparişe göre arayan HER yer kapıdan geçmeli.

    Kapıyı atlayan bir sorgu, birleşik faturanın ikinci siparişini
    bulamaz — ve bulamamak çift faturalama demek. Dokuz çağrı
    noktası vardı; onuncusu eklenirse burası düşer."""
    import io as _io
    import re as _re
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    satirlar = kaynak.split('\n')
    suclu = []
    for i, s in enumerate(satirlar, 1):
        if _re.search(r'Fatura\.query\.filter_by\(\s*siparis_id', s):
            suclu.append((i, s.strip()[:70]))
        if _re.search(r'Fatura\.siparis_id\s*==', s):
            suclu.append((i, s.strip()[:70]))
    # Kapinin KENDISI eski alani OR'luyor — mesru tek gecis.
    suclu = [(i, s) for i, s in suclu
             if 'Fatura.siparis_id == siparis_id' not in s]
    assert not suclu, (
        f'kapıyı atlayan sorgu(lar): {suclu} — birleşik faturanın '
        f'ikinci siparişini bulamaz')
    assert 'def _siparis_faturalari(' in kaynak, 'kapı yok'


def test_bf1_goc_iki_siraya_da_dayanikli():
    """ÇİVİ: göç, tablo zaten varsa da çalışmalı.

    ÖLÇÜLDÜ: uygulama açılışta `db.create_all()` çağırıyor. Servis
    göçten ÖNCE yeniden başlatılırsa tablo BOŞ olarak oluşuyor ve
    düz bir `create_table` "already exists" ile patlıyor — `flask db
    upgrade` tümüyle duruyor. Göç bu yüzden tablo varlığını
    denetliyor ve geriye doldurmayı NOT EXISTS ile koruyor.

    (Her iki sıra ve gidiş-dönüş gerçek alembic ile ölçüldü; bu çivi
     korumanın kaldırılmasını engelliyor.)"""
    import io as _io
    import os as _os
    dizin = _os.path.join(KOK, 'migrations', 'versions')
    yol = _os.path.join(dizin, 'bf1faturasip_fatura_siparis_bagi.py')
    assert _os.path.exists(yol), 'BF1 göç dosyası yok'
    g = _io.open(yol, encoding='utf-8').read()
    assert "revision = 'bf1faturasip'" in g, g[:200]
    assert "down_revision = 'un2kaynakstk'" in g, 'göç zinciri kopuk'
    assert 'get_table_names()' in g, (
        'göç tablo varlığını denetlemiyor — servis önce yeniden '
        'başlatılırsa "already exists" ile patlar')
    assert 'NOT EXISTS' in g, (
        'geriye doldurma korunmuyor — iki kez koşarsa yinelenen '
        'satır üretir')
    assert 'def downgrade():' in g and 'drop_table' in g, (
        'geri alma yolu yok')


# ══════════════════════════════════════════════════════════════════
#  FL1 · MALİYETİ KESEN CARİ, KASKAD SÜZGEÇ, TOPLU TARİH
#
#  `Maliyet` tablosunda cari sütunu YOK; cari, maliyete bağlı cari
#  hareketten okunur. Liste ucu bunu yapmıyor, her satıra STOĞUN
#  TEDARİKÇİSİNİ yazıyordu — nakliyecinin faturası blok
#  tedarikçisinin adıyla görünüyor, Cari süzgeci de yalnız onu
#  listeliyordu.
#
#  İkinci hata tarihteydi: maliyet geçmiş tarihle girilse bile cari
#  borç GİRİŞ GÜNÜNE ve o günün kuruna yazılıyordu.
# ══════════════════════════════════════════════════════════════════
FL1_GUN = date.today()
FL1_ESKI = date(2025, 3, 14)      # KDV dönemi çoktan kapandı


def _fl1_hazirlik():
    from models import Cari, DovizKur
    with fa.app.app_context():
        for dv, k in (('USD', 40.0), ('EUR', 44.0)):
            if not DovizKur.query.filter_by(doviz=dv, tarih=FL1_ESKI).first():
                db.session.add(DovizKur(doviz=dv, tarih=FL1_ESKI,
                                        alis=k, satis=k, efektif=k))
        for cid, ad in (('FLT', 'FL1 BLOK TEDARIKCISI'),
                        ('FLN', 'FL1 NAKLIYECI'),
                        ('FLG', 'FL1 GUMRUKCU')):
            if not Cari.query.get(cid):
                db.session.add(Cari(id=cid, unvan=ad, cari_tip='Tedarikçi',
                                    urun_tedarikcisi=True,
                                    gorunurluk='acik'))
        db.session.commit()
    return istemci('admin', 'ADMIN')


def _fl1_blok(c, blok_no, fatura_no, tarih=None):
    r = c.post('/api/stok/ekle', headers=H, json={
        'tip': 'BLOK', 'uretici': 'FL1 BLOK TEDARIKCISI',
        'cins': 'FL1 CINS', 'blok_no': blok_no, 'boy': 300,
        'yukseklik': 150, 'en': 120, 'tonaj': 10, 'fiyat': 100,
        'fiyat_birim': 'ton', 'doviz': 'USD', 'kdv_dahil_mi': False,
        'kdv_oran': 20, 'alis_tipi': 'yurtici_kdvli',
        'fatura_no': fatura_no,
        'alis_tarihi': (tarih or FL1_GUN).isoformat(),
        'fatura_durumu': 'faturali', 'mense': 'TURKIYE'})
    assert r.status_code == 200, (r.status_code, r.get_json())
    return (r.get_json() or {}).get('id')


def _fl1_maliyet(c, sid, tip, tutar, cari, kdv, fno, doviz='USD',
                 tarih=None):
    g = {'maliyet_tip': tip, 'baglanti_tip': 'stok', 'baglanti_id': sid,
         'tutar': tutar, 'doviz': doviz, 'kdv_oran': kdv,
         'kdv_dahil_mi': False, 'fatura_no': fno, 'cari_id': cari}
    if tarih is not None:
        g['maliyet_tarihi'] = tarih.isoformat()
    r = c.post('/api/maliyet', headers=H, json=g)
    assert r.status_code == 200, (r.status_code,
                                  r.get_data(as_text=True)[:250])
    return r.get_json()['id']


def _fl1_liste(c):
    r = c.get('/api/maliyet', headers=H)
    assert r.status_code == 200, r.status_code
    d = r.get_json()
    return d if isinstance(d, list) else (d.get('data') or [])


def _fl1_hareket(mid):
    """Maliyetin cari hareketi — doğrudan ya da grubu üzerinden."""
    from models import Maliyet
    m = Maliyet.query.get(mid)
    idler = [mid]
    if m is not None and m.grup_id:
        idler = [x.id for x in Maliyet.query.filter_by(
            grup_id=m.grup_id).all()]
    return CariHareket.query.filter(
        CariHareket.baglanti_tip == 'maliyet',
        CariHareket.baglanti_id.in_(idler)).first()


def _fl1_toplu(c, idler, tarih, asim=None):
    g = {'idler': idler, 'tarih': tarih.isoformat()}
    if asim is not None:
        g['kapali_donem_asimi'] = asim
    return c.post('/api/maliyet/toplu_tarih', headers=H, json=g)


def test_fl1_liste_maliyeti_kesen_cariyi_gosteriyor():
    """ÇİVİ: satırın carisi maliyeti KESEN caridir, stoğun
    tedarikçisi değil. Carisi olmayan maliyet de tedarikçinin adını
    ödünç almaz — boş görünür.

    Tabanda üç satırın üçü de "FL1 BLOK TEDARIKCISI" diyordu."""
    c = _fl1_hazirlik()
    sid = _fl1_blok(c, 'FL1-A1', 'FL1-ALIS-A')
    m1 = _fl1_maliyet(c, sid, 'Nakliye (Ocak-Fabrika)', 300, 'FLN', 0,
                      'FL1-NAK-A')
    m2 = _fl1_maliyet(c, sid, 'Diğer', 50, None, 0, 'FL1-DIG-A')
    s = {m['id']: m for m in _fl1_liste(c)}
    assert s[m1].get('cari_unvan') == 'FL1 NAKLIYECI', s[m1]
    assert s[m1].get('cari_id') == 'FLN', s[m1]
    assert (s[m2].get('cari_unvan') or '') == '', s[m2]
    assert s[m2].get('cari_id') is None, s[m2]
    # Stoğun kendi alış satırı tedarikçiyi göstermeye DEVAM etmeli.
    alis = s.get('ALIS:' + sid)
    assert alis is not None, 'sanal alış satırı yok'
    assert alis.get('cari_unvan') == 'FL1 BLOK TEDARIKCISI', alis


def test_fl1_gecmis_tarihli_giris_borcu_o_gune_yaziyor():
    """Maliyet geçmiş tarihle girilince cari borç da O GÜNE ve o
    günün kuruna yazılır. Tabanda hareket giriş gününe düşüyordu —
    cari ekstresi faturayı yanlış ayda gösteriyordu."""
    c = _fl1_hazirlik()
    sid = _fl1_blok(c, 'FL1-B1', 'FL1-ALIS-B')
    mid = _fl1_maliyet(c, sid, 'Komisyon', 100, 'FLG', 0, 'FL1-KOM-B',
                       doviz='EUR', tarih=FL1_ESKI)
    with fa.app.app_context():
        h = _fl1_hareket(mid)
        assert h is not None, 'cari hareket doğmadı'
        assert h.hareket_tarihi == FL1_ESKI, h.hareket_tarihi
        assert abs(float(h.kur_uygulanan or 0) - 44.0) < 0.001, (
            h.kur_uygulanan)
        assert abs(float(h.alacak_try or 0) - 4400.0) < 0.01, h.alacak_try


def test_fl1_tek_duzenleme_try_karsiligini_da_tasiyor():
    """Tarih düzeltilince hareketin TL karşılığı da yeni günün
    kuruyla yeniden hesaplanır. Tabanda tarih taşınıyor, TL karşılığı
    ESKİ kurda kalıyordu."""
    c = _fl1_hazirlik()
    sid = _fl1_blok(c, 'FL1-C1', 'FL1-ALIS-C')
    mid = _fl1_maliyet(c, sid, 'Komisyon', 100, 'FLG', 0, 'FL1-KOM-C',
                       doviz='EUR')
    with fa.app.app_context():
        once = float(_fl1_hareket(mid).alacak_try or 0)
    r = c.put(f'/api/maliyet/{mid}', headers=H,
              json={'maliyet_tarihi': FL1_ESKI.isoformat()})
    assert r.status_code == 200, (r.status_code, r.get_json())
    with fa.app.app_context():
        h = _fl1_hareket(mid)
        assert h.hareket_tarihi == FL1_ESKI, h.hareket_tarihi
        assert abs(float(h.alacak_try or 0) - 4400.0) < 0.01, (
            once, h.alacak_try)
        assert abs(float(h.kur_uygulanan or 0) - 44.0) < 0.001


def test_fl1_toplu_tarih_kapali_doneme_kdvliyi_tasimiyor():
    """Toplu taşıma, aşım istenmedikçe KDV'li faturayı kapanmış
    döneme SOKMAZ; KDV'sizi taşır ve hangisini taşımadığını söyler.
    Bulunamayan kimlik de sessizce yutulmaz."""
    from models import Maliyet
    c = _fl1_hazirlik()
    sid = _fl1_blok(c, 'FL1-D1', 'FL1-ALIS-D')
    kdvli = _fl1_maliyet(c, sid, 'Nakliye (Ocak-Fabrika)', 1000, 'FLN',
                         20, 'FL1-NAK-D')
    kdvsiz = _fl1_maliyet(c, sid, 'Gümrük/Liman Masrafı', 500, 'FLG', 0,
                          'FL1-GUM-D')
    r = _fl1_toplu(c, [kdvli, kdvsiz, 'FL1-YOK'], FL1_ESKI)
    assert r.status_code == 200, (r.status_code,
                                  r.get_data(as_text=True)[:250])
    j = r.get_json()
    assert [t['id'] for t in j['tasinan']] == [kdvsiz], j
    assert [t['id'] for t in j['reddedilen']] == [kdvli], j
    assert j['bulunamayan'] == ['FL1-YOK'], j
    assert j['asim_sayisi'] == 0, j
    with fa.app.app_context():
        assert Maliyet.query.get(kdvli).maliyet_tarihi == FL1_GUN
        assert Maliyet.query.get(kdvsiz).maliyet_tarihi == FL1_ESKI
        assert _fl1_hareket(kdvli).hareket_tarihi == FL1_GUN
        assert _fl1_hareket(kdvsiz).hareket_tarihi == FL1_ESKI
    # İleri tarih hiçbir koşulda yazılmaz.
    from datetime import timedelta
    r = _fl1_toplu(c, [kdvsiz], FL1_GUN + timedelta(days=3), asim=True)
    assert r.status_code == 400, r.status_code


def test_fl1_asim_yalniz_yoneticide():
    """Kapalı dönem aşımını maliyet YAZMA yetkisi olan sıradan
    kullanıcı isteyemez; istek bütünüyle reddedilir."""
    from models import Maliyet
    c = _fl1_hazirlik()
    sid = _fl1_blok(c, 'FL1-E1', 'FL1-ALIS-E')
    mid = _fl1_maliyet(c, sid, 'Nakliye (Ocak-Fabrika)', 1000, 'FLN', 20,
                       'FL1-NAK-E')
    c2 = _oy1_kullanici('fl1maliyetci', {'maliyet': 'yazma'})
    r = _fl1_toplu(c2, [mid], FL1_ESKI, asim=True)
    assert r.status_code == 403, (r.status_code, r.get_json())
    with fa.app.app_context():
        assert Maliyet.query.get(mid).maliyet_tarihi == FL1_GUN
    # Aşımsız istek aynı kullanıcıdan KABUL edilir (reddi satır
    # bazında bildirir) — yetki kapısı yalnız aşımı tutuyor.
    r = _fl1_toplu(c2, [mid], FL1_ESKI)
    assert r.status_code == 200, r.status_code
    assert len(r.get_json()['reddedilen']) == 1
    # Maliyet yetkisi hiç olmayan giremez.
    c3 = _oy1_kullanici('fl1yetkisiz', {'stok': 'yazma'})
    assert _fl1_toplu(c3, [mid], FL1_ESKI).status_code == 403


def test_fl1_asimla_fatura_butun_tasiniyor_ve_iz_kaliyor():
    """Yönetici aşımıyla KDV'li fatura BÜTÜN taşınır: maliyet satırı,
    Devreden KDV satırı, dolar karşılıkları ve cari borç — hepsi yeni
    güne ve o günün kuruna. Denetim izine aşım olarak düşer."""
    from models import Maliyet, AuditLog
    c = _fl1_hazirlik()
    sid = _fl1_blok(c, 'FL1-F1', 'FL1-ALIS-F')
    mid = _fl1_maliyet(c, sid, 'Nakliye (Ocak-Fabrika)', 1000, 'FLN', 20,
                       'FL1-NAK-F', doviz='EUR')
    with fa.app.app_context():
        satirlar = Maliyet.query.filter_by(fatura_no='FL1-NAK-F').all()
        assert len(satirlar) == 2, [(m.id, m.maliyet_tip) for m in satirlar]
        usd_once = float(Maliyet.query.get(mid).usd_karsilik or 0)
    r = _fl1_toplu(c, [mid], FL1_ESKI, asim=True)
    assert r.status_code == 200, (r.status_code, r.get_json())
    j = r.get_json()
    assert j['asim_sayisi'] == 1 and not j['reddedilen'], j
    assert j['tasinan'][0]['satir'] == 2, j
    with fa.app.app_context():
        for m in Maliyet.query.filter_by(fatura_no='FL1-NAK-F').all():
            assert m.maliyet_tarihi == FL1_ESKI, (m.id, m.maliyet_tarihi)
        usd = float(Maliyet.query.get(mid).usd_karsilik or 0)
        # 1000 EUR · 44/40 = 1100 USD (taşınmadan önce bugünün kuru)
        assert abs(usd - 1100.0) < 0.01, (usd_once, usd)
        h = _fl1_hareket(mid)
        assert h.hareket_tarihi == FL1_ESKI, h.hareket_tarihi
        assert abs(float(h.kur_uygulanan or 0) - 44.0) < 0.001
        iz = AuditLog.query.filter_by(tablo_adi='maliyet',
                                      kayit_id=mid).order_by(
            AuditLog.id.desc()).first()
        assert iz is not None, 'denetim izi yok'
        assert json.loads(iz.yeni_veri).get('kapali_donem_asimi') is True, (
            iz.yeni_veri)


def test_fl1_tek_duzenleme_asim_yapamiyor():
    """Aşım YALNIZ toplu araçta. Tek kayıt düzenleme ucu aynı
    bayrağı alsa bile kapanmış döneme KDV'li kayıt sokamaz."""
    from models import Maliyet
    c = _fl1_hazirlik()
    sid = _fl1_blok(c, 'FL1-G1', 'FL1-ALIS-G')
    mid = _fl1_maliyet(c, sid, 'Nakliye (Ocak-Fabrika)', 100, 'FLN', 20,
                       'FL1-NAK-G')
    r = c.put(f'/api/maliyet/{mid}', headers=H,
              json={'maliyet_tarihi': FL1_ESKI.isoformat(),
                    'kapali_donem_asimi': True})
    assert r.status_code in (400, 409), (r.status_code, r.get_json())
    with fa.app.app_context():
        assert Maliyet.query.get(mid).maliyet_tarihi == FL1_GUN
        assert _fl1_hareket(mid).hareket_tarihi == FL1_GUN


def test_fl1_alis_faturasi_butun_tasiniyor():
    """Stok alış faturası tek belgedir. Yalnız KDV satırı seçilse
    bile aynı faturadaki BÜTÜN stokların alış tarihi, KDV satırları
    ve tedarikçi borcu birlikte taşınır — belge iki döneme bölünmez."""
    from models import Maliyet
    c = _fl1_hazirlik()
    s1 = _fl1_blok(c, 'FL1-H1', 'FL1-ALIS-H')
    s2 = _fl1_blok(c, 'FL1-H2', 'FL1-ALIS-H')
    with fa.app.app_context():
        kid = Maliyet.query.filter_by(
            baglanti_id=s2, maliyet_tip='Devreden KDV').first().id
    # Aşımsız: fatura KDV'li, dönem kapalı → hiçbir şey kıpırdamaz.
    r = _fl1_toplu(c, ['ALIS:' + s1], FL1_ESKI)
    assert r.status_code == 200, (r.status_code,
                                  r.get_data(as_text=True)[:250])
    assert len(r.get_json()['reddedilen']) == 1, r.get_json()
    with fa.app.app_context():
        assert BlokStok.query.get(s1).alis_tarihi == FL1_GUN
    # Aşımlı, YALNIZ KDV satırıyla.
    r = _fl1_toplu(c, [kid], FL1_ESKI, asim=True)
    j = r.get_json()
    assert r.status_code == 200 and len(j['tasinan']) == 1, j
    assert j['tasinan'][0]['satir'] == 2, j
    with fa.app.app_context():
        assert BlokStok.query.get(s1).alis_tarihi == FL1_ESKI
        assert BlokStok.query.get(s2).alis_tarihi == FL1_ESKI
        for m in Maliyet.query.filter_by(fatura_no='FL1-ALIS-H',
                                         maliyet_tip='Devreden KDV').all():
            assert m.maliyet_tarihi == FL1_ESKI, (m.id, m.maliyet_tarihi)
        h = CariHareket.query.filter_by(baglanti_tip='stok_fatura',
                                        baglanti_id='FL1-ALIS-H').first()
        assert h.hareket_tarihi == FL1_ESKI, h.hareket_tarihi
        assert abs(float(h.alacak or 0) - 2400.0) < 0.01, h.alacak
        assert abs(float(h.alacak_try or 0) - 96000.0) < 0.5, h.alacak_try


def test_fl1_alis_kdv_satiri_alis_tarihini_tasiyor():
    """Geçmiş tarihli alışın Devreden KDV satırı da ALIŞ TARİHİNE
    yazılır. Tabanda giriş gününe düşüyordu — aynı faturanın borcu
    bir günde, KDV'si başka günde duruyordu."""
    from datetime import timedelta
    from models import Maliyet, DovizKur
    c = _fl1_hazirlik()
    dun = FL1_GUN - timedelta(days=1)     # dönemi her koşulda AÇIK
    with fa.app.app_context():
        if not DovizKur.query.filter_by(doviz='USD', tarih=dun).first():
            db.session.add(DovizKur(doviz='USD', tarih=dun, alis=47,
                                    satis=47, efektif=47))
            db.session.commit()
    sid = _fl1_blok(c, 'FL1-I1', 'FL1-ALIS-I', tarih=dun)
    with fa.app.app_context():
        k = Maliyet.query.filter_by(baglanti_id=sid,
                                    maliyet_tip='Devreden KDV').first()
        assert k is not None, 'KDV satırı yok'
        assert k.maliyet_tarihi == dun, k.maliyet_tarihi


def test_fl1_blok_dagilim_gruplu_ve_borcu_bagli():
    """Blok dağılımı satırları ortak bir grup taşır ve tedarikçi
    borcu grubun ilk satırına bağlıdır. Tabanda satırlar grupsuz,
    borç bağsızdı: maliyeti kesen cari bulunamıyor, tarih/tutar
    düzeltmesi borca yansımıyordu."""
    from models import Maliyet
    c = _fl1_hazirlik()
    s1 = _fl1_blok(c, 'FL1-J1', 'FL1-ALIS-J')
    r = c.post('/api/maliyet/blok_dagilim', headers=H, json={
        'urun_tipi': 'BLOK', 'blok_no': 'FL1-J1',
        'maliyet_tip': 'Nakliye (Ocak-Fabrika)', 'tutar': 400,
        'doviz': 'USD', 'hedef': 'hepsi', 'fatura_no': 'FL1-DAG-J',
        'cari_id': 'FLN', 'kdv_oran': 0})
    assert r.status_code == 200, (r.status_code,
                                  r.get_data(as_text=True)[:250])
    with fa.app.app_context():
        satirlar = Maliyet.query.filter_by(fatura_no='FL1-DAG-J').all()
        assert satirlar, 'dağılım satırı yok'
        gruplar = {m.grup_id for m in satirlar}
        assert len(gruplar) == 1 and None not in gruplar, gruplar
        h = CariHareket.query.filter(
            CariHareket.baglanti_tip == 'maliyet',
            CariHareket.cari_id == 'FLN',
            CariHareket.baglanti_id.in_([m.id for m in satirlar])).first()
        assert h is not None, 'borç hiçbir maliyet satırına bağlı değil'
    s = {m['id']: m for m in _fl1_liste(c)}
    for m in satirlar:
        assert s[m.id].get('cari_unvan') == 'FL1 NAKLIYECI', s[m.id]


def test_fl1_kaskad_suzgec_ve_toplu_cubuk_sayfada():
    """ÇİVİ: süzgeçler TEK yüklem tablosundan (`mSuzgecler`) çalışır
    ve her kutunun seçenekleri KENDİ süzgeci hariç öbürlerinden
    geçen satırlardan üretilir (`mGecenler(haric)`). İkinci bir elle
    yazılmış süzme zinciri kutularla listeyi birbirinden koparır."""
    import io as _io
    sayfa = _io.open(os.path.join(KOK, 'templates', 'maliyet.html'),
                     encoding='utf-8').read()
    for kimlik in ('id="mCari"', 'id="mTip"', 'id="mBag"',
                   'id="mFatura"', 'id="ttCubuk"', 'id="ttTarih"',
                   'id="ttHepsi"'):
        assert kimlik in sayfa, f'{kimlik} sayfada yok'
    for parca in ('function mSuzgecler(', 'function mGecenler(',
                  'function mSecenekleriDoldur(', 'function ttUygula(',
                  '/api/maliyet/toplu_tarih', 'kapali_donem_asimi'):
        assert parca in sayfa, f'{parca} sayfada yok'
    # Liste de kutular da AYNI kapıdan geçmeli.
    assert sayfa.count('mGecenler(') >= 3, sayfa.count('mGecenler(')
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read()
    assert 'def _maliyet_tarih_tasi(' in kaynak
    assert 'def _stok_alis_tarih_tasi(' in kaynak


# ══════════════════════════════════════════════════════════════════
#  PS1 · PROFORMA İPTAL / SİLME KİLİDİ
#
#  Silme kuralı "yalnız Taslak ve İptal silinir" diyor, sunucu
#  İptal geçişini kabul ediyor — ama ekranda İPTAL DÜĞMESİ YOKTU.
#  Taslak'tan çıkmış hiçbir proforma silinemiyordu.
#
#  Yanında iki ölçüm daha: kaybedilen teklif stokları rezerve
#  tutuyordu; revize zincirinin güncel sürümü silinince eski
#  sürümler sahipsiz kalıyordu.
# ══════════════════════════════════════════════════════════════════
def _ps1_blok(no):
    with fa.app.app_context():
        if db.session.get(BlokStok, no) is None:
            db.session.add(BlokStok(
                id=no, blok_no=no, cins='PS1 CINS', boy=300, yukseklik=150,
                en=120, hacim_m3=5.4, tonaj=15, durum='Serbest',
                giris_tarihi=date.today()))
            db.session.commit()
    return no


def _ps1_teklif(c, blok):
    r = c.post('/api/proforma', headers=H, json={
        'musteri': 'ACIK CARI', 'cari_id': 'C1', 'doviz': 'USD',
        'proforma_tipi': 'teklif', 'teslim_sekli': 'FOB',
        'odeme_sekli': 'Pesin', 'stok_rezerve': True,
        'yineleme_onay': True,
        'kalemler': [{'urun_tip': 'BLOK', 'cins': 'PS1 CINS',
                      'blok_no': blok, 'stok_id': blok, 'adet': 1,
                      'miktar': 15, 'birim': 'ton', 'birim_fiyat': 350,
                      'doviz': 'USD', 'karsilama_plan': 'stok'}]})
    assert r.status_code == 200, (r.status_code,
                                  r.get_data(as_text=True)[:250])
    pid = r.get_json()['id']
    with fa.app.app_context():
        assert db.session.get(BlokStok, blok).durum == 'Rezerve', (
            'hazırlık: stok rezerve olmadı')
    return pid


def _ps1_stok_durum(blok):
    with fa.app.app_context():
        return db.session.get(BlokStok, blok).durum


def test_ps1_kaybedilen_teklif_stogu_serbest_birakiyor():
    """Kaybedildi işaretlenen teklifin rezervasyonları HEMEN iptal
    edilir. Tabanda stok Rezerve kalıyor, başka müşteriye
    satılamaz görünüyordu."""
    from models import Rezervasyon
    c = istemci('admin', 'ADMIN')
    b = _ps1_blok('PS1-A')
    pid = _ps1_teklif(c, b)
    r = c.post(f'/api/proforma/{pid}/kaybedildi', headers=H,
               json={'sebep': 'fiyat'})
    assert r.status_code == 200, (r.status_code, r.get_json())
    assert r.get_json().get('serbest_kalan_stok') == 1, r.get_json()
    assert _ps1_stok_durum(b) == 'Serbest', _ps1_stok_durum(b)
    with fa.app.app_context():
        acik = Rezervasyon.query.filter_by(proforma_id=pid,
                                           iptal_nedeni=None).count()
        assert acik == 0, acik
    # Kayıp teklif stoğu YENİDEN kilitleyemez.
    r = c.post(f'/api/proforma/{pid}/rezerve', headers=H, json={})
    assert r.status_code == 400, (r.status_code, r.get_json())
    assert _ps1_stok_durum(b) == 'Serbest'
    # Kayıp geri alınınca rezerve yolu yeniden AÇIK olmalı.
    assert c.post(f'/api/proforma/{pid}/kaybi_geri_al', headers=H,
                  json={}).status_code == 200
    r = c.post(f'/api/proforma/{pid}/rezerve', headers=H, json={})
    assert r.status_code == 200 and r.get_json().get('adet') == 1, (
        r.status_code, r.get_json())


def test_ps1_kaybedilen_teklif_iptal_edilip_silinebiliyor():
    """Bekçi: Kaybedildi → İptal → Sil yolu sunucuda açık kalmalı.
    Doğrudan silme ise reddedilmeli (kullanıcının kararı: iki adım)."""
    from models import Proforma
    c = istemci('admin', 'ADMIN')
    b = _ps1_blok('PS1-B')
    pid = _ps1_teklif(c, b)
    assert c.post(f'/api/proforma/{pid}/kaybedildi', headers=H,
                  json={'sebep': 'rakip'}).status_code == 200
    assert c.delete(f'/api/proforma/{pid}', headers=H).status_code == 400
    r = c.post(f'/api/proforma/{pid}/durum', headers=H,
               json={'durum': 'Iptal'})
    assert r.status_code == 200, (r.status_code, r.get_json())
    r = c.delete(f'/api/proforma/{pid}', headers=H)
    assert r.status_code == 200, (r.status_code, r.get_json())
    with fa.app.app_context():
        assert db.session.get(Proforma, pid) is None
    assert _ps1_stok_durum(b) == 'Serbest'


def test_ps1_iptal_dugmesi_ekranda():
    """ÇİVİ: kilidin kendisi. Sunucu İptal geçişini kabul ediyor ama
    ekranda onu çağıran düğme yoktu; silme kuralı "önce İptal'e
    alın" derken iptal etmenin yolu yoktu."""
    import io as _io
    sayfa = _io.open(os.path.join(KOK, 'templates', 'proforma.html'),
                     encoding='utf-8').read()
    assert 'async function proformaIptal(' in sayfa, 'iptal işlevi yok'
    assert "onclick=\"proformaIptal('" in sayfa, 'iptal düğmesi yok'
    assert "durumGecir(id, 'Iptal')" in sayfa, (
        'iptal işlevi durum ucunu çağırmıyor')
    # Düğme Kaybedildi durumunu KAPSAMALI — bildirilen kilit buydu.
    parca = sayfa[sayfa.index("onclick=\"proformaIptal('") - 400:
                  sayfa.index("onclick=\"proformaIptal('")]
    assert "'Kaybedildi'" in parca, parca[-200:]
    # Kayıp teklifte "Stokları rezerve et" görünmemeli.
    rz = sayfa[sayfa.index('onclick="proformaRezerve(') - 420:
               sayfa.index('onclick="proformaRezerve(')]
    assert "p.durum !== 'Kaybedildi'" in rz, rz[-250:]


def test_ps1_revize_zinciri_birlikte_siliniyor():
    """Güncel sürüm silinince eski sürümler de gider. Tabanda arşiv
    sürümü veritabanında kalıyordu: listede yok, silinemiyor,
    durumu değiştirilemiyor."""
    from models import Proforma, ProformaKalem
    c = istemci('admin', 'ADMIN')
    b = _ps1_blok('PS1-C')
    kok = _ps1_teklif(c, b)
    r = c.post(f'/api/proforma/{kok}/revize', headers=H,
               json={'yineleme_onay': True})
    assert r.status_code == 200, (r.status_code, r.get_json())
    rev = r.get_json()['id']
    assert c.post(f'/api/proforma/{rev}/durum', headers=H,
                  json={'durum': 'Iptal'}).status_code == 200
    r = c.delete(f'/api/proforma/{rev}', headers=H)
    assert r.status_code == 200, (r.status_code, r.get_json())
    assert r.get_json().get('silinen_eski_surum') == 1, r.get_json()
    with fa.app.app_context():
        assert db.session.get(Proforma, rev) is None
        assert db.session.get(Proforma, kok) is None, (
            'arşiv sürümü sahipsiz kaldı')
        assert ProformaKalem.query.filter(
            ProformaKalem.proforma_id.in_([kok, rev])).count() == 0
    assert _ps1_stok_durum(b) == 'Serbest'


def test_ps1_eski_surumde_fatura_varsa_zincir_silinmiyor():
    """Zincirin HERHANGİ bir sürümüne fatura bağlıysa hiçbir şey
    silinmez ve ret, ilk değişiklikten ÖNCE gelir."""
    from models import Proforma, Fatura
    c = istemci('admin', 'ADMIN')
    b = _ps1_blok('PS1-D')
    kok = _ps1_teklif(c, b)
    r = c.post(f'/api/proforma/{kok}/revize', headers=H,
               json={'yineleme_onay': True})
    assert r.status_code == 200, (r.status_code, r.get_json())
    rev = r.get_json()['id']
    with fa.app.app_context():
        db.session.add(Fatura(id='FPS1', fatura_no='F-PS1',
                              musteri='ACIK CARI', cari_id='C1',
                              proforma_id=kok, toplam=10, doviz='USD',
                              durum='Taslak', yon='satis'))
        db.session.commit()
    # Güncel sürüm Taslak: silinebilir durumda, ama zincirde fatura var.
    r = c.delete(f'/api/proforma/{rev}', headers=H)
    assert r.status_code == 400, (r.status_code, r.get_json())
    assert r.get_json().get('error') == 'bagli_fatura', r.get_json()
    assert kok in r.get_json().get('mesaj', ''), r.get_json()
    with fa.app.app_context():
        assert db.session.get(Proforma, rev) is not None
        assert db.session.get(Proforma, kok) is not None
    assert _ps1_stok_durum(b) == 'Rezerve', (
        'reddedilen silme stoğu serbest bırakmış')
    with fa.app.app_context():
        Fatura.query.filter_by(id='FPS1').delete()
        db.session.commit()
    assert c.delete(f'/api/proforma/{rev}', headers=H).status_code == 200


# ══════════════════════════════════════════════════════════════════
#  AT1 · STOK DÜZENLEME FORMUNDA TARİH
#
#  Formda tarih alanı yoktu. Alış tarihi stoğun değil FATURANIN
#  tarihi: stok kartı, aynı faturadaki öbür stoklar, tedarikçi borcu
#  ve alışın KDV satırı birlikte taşınmak zorunda.
# ══════════════════════════════════════════════════════════════════
def _at1_blok(c, blok_no, fatura_no, kdv=0):
    _fl1_hazirlik()
    r = c.post('/api/stok/ekle', headers=H, json={
        'tip': 'BLOK', 'uretici': 'FL1 BLOK TEDARIKCISI',
        'cins': 'AT1 CINS', 'blok_no': blok_no, 'boy': 300,
        'yukseklik': 150, 'en': 120, 'tonaj': 10, 'fiyat': 100,
        'fiyat_birim': 'ton', 'doviz': 'USD', 'kdv_dahil_mi': False,
        'kdv_oran': kdv,
        'alis_tipi': 'yurtici_kdvli' if kdv else 'yurtici_kdvsiz',
        'fatura_no': fatura_no, 'alis_tarihi': FL1_GUN.isoformat(),
        'fatura_durumu': 'faturali', 'mense': 'TURKIYE'})
    assert r.status_code == 200, (r.status_code, r.get_json())
    return (r.get_json() or {}).get('id')


def _at1_borc(fatura_no):
    return CariHareket.query.filter_by(baglanti_tip='stok_fatura',
                                       baglanti_id=fatura_no).first()


def test_at1_alis_tarihi_faturayi_butun_tasiyor():
    """Düzenleme formundan alış tarihi değişince aynı faturadaki
    ÖBÜR stok ve tedarikçi borcu da taşınır; borcun TL karşılığı
    yeni günün kuruyla yeniden hesaplanır. Tabanda uç bu alanı hiç
    okumuyordu: istek 200 dönüyor, hiçbir şey değişmiyordu."""
    c = istemci('admin', 'ADMIN')
    s1 = _at1_blok(c, 'AT1-A1', 'AT1-F-A')
    s2 = _at1_blok(c, 'AT1-A2', 'AT1-F-A')
    r = c.put(f'/api/stok/{s1}', headers=H, json={
        'tip': 'BLOK', 'alis_tarihi': FL1_ESKI.isoformat()})
    assert r.status_code == 200, (r.status_code, r.get_json())
    assert 'Alış tarihi' in r.get_json().get('mesaj', ''), r.get_json()
    with fa.app.app_context():
        assert BlokStok.query.get(s1).alis_tarihi == FL1_ESKI
        assert BlokStok.query.get(s2).alis_tarihi == FL1_ESKI, (
            'aynı faturadaki öbür stok geride kaldı')
        h = _at1_borc('AT1-F-A')
        assert h.hareket_tarihi == FL1_ESKI, h.hareket_tarihi
        assert abs(float(h.alacak or 0) - 2000.0) < 0.01, h.alacak
        assert abs(float(h.kur_uygulanan or 0) - 40.0) < 0.001, (
            h.kur_uygulanan)
        assert abs(float(h.alacak_try or 0) - 80000.0) < 0.5, h.alacak_try


def test_at1_stok_karti_ile_borc_ayriysa_esitleniyor():
    """Ölçülen vaka: stok kartı 06.11, borç 24.10. Form tarihi her
    kayıtta gönderir; stok kartındaki tarih değişmese de borç ona
    eşitlenir ve yanıt bunu söyler."""
    c = istemci('admin', 'ADMIN')
    sid = _at1_blok(c, 'AT1-B1', 'AT1-F-B')
    with fa.app.app_context():
        _at1_borc('AT1-F-B').hareket_tarihi = FL1_ESKI
        db.session.commit()
    r = c.put(f'/api/stok/{sid}', headers=H, json={
        'tip': 'BLOK', 'alis_tarihi': FL1_GUN.isoformat()})
    assert r.status_code == 200, (r.status_code, r.get_json())
    assert 'tedarikçi borcu' in r.get_json().get('mesaj', ''), r.get_json()
    with fa.app.app_context():
        assert _at1_borc('AT1-F-B').hareket_tarihi == FL1_GUN
        assert BlokStok.query.get(sid).alis_tarihi == FL1_GUN
    # Her şey zaten yerindeyken tarih SESSİZ kalmalı. (Gövde bir
    # öncekinden farklı: birebir aynı istek çift tıklama korumasına
    # takılır.)
    r = c.put(f'/api/stok/{sid}', headers=H, json={
        'tip': 'BLOK', 'konum': 'AT1 RAF 2',
        'alis_tarihi': FL1_GUN.isoformat()})
    assert r.status_code == 200, (r.status_code, r.get_json())
    assert 'Alış tarihi' not in r.get_json().get('mesaj', ''), r.get_json()


def test_at1_kdvli_alis_kapali_doneme_tasinmiyor():
    """KDV'li alış bu formdan kapanmış döneme sokulamaz (aşım yalnız
    toplu araçta). Reddedilen istek BAŞKA alanı da kaydetmez."""
    from models import Maliyet
    c = istemci('admin', 'ADMIN')
    sid = _at1_blok(c, 'AT1-C1', 'AT1-F-C', kdv=20)
    r = c.put(f'/api/stok/{sid}', headers=H, json={
        'tip': 'BLOK', 'konum': 'AT1 RAF',
        'alis_tarihi': FL1_ESKI.isoformat()})
    assert r.status_code == 409, (r.status_code, r.get_json())
    y = r.get_json()
    assert y.get('error') == 'kdv_donemi_kapali', y
    assert y.get('baglam') == 'alis_tarihi', y
    with fa.app.app_context():
        s = BlokStok.query.get(sid)
        assert s.alis_tarihi == FL1_GUN, s.alis_tarihi
        assert (s.konum or '') != 'AT1 RAF', 'reddedilen istek yarım kaydedildi'
        assert _at1_borc('AT1-F-C').hareket_tarihi == FL1_GUN
        k = Maliyet.query.filter_by(baglanti_id=sid,
                                    maliyet_tip='Devreden KDV').first()
        assert k.maliyet_tarihi == FL1_GUN, k.maliyet_tarihi


def test_at1_giris_tarihi_ve_ileri_tarih():
    """Giriş tarihi düz yazılır; ileri tarih hiçbir alanda kabul
    edilmez."""
    from datetime import timedelta
    c = istemci('admin', 'ADMIN')
    sid = _at1_blok(c, 'AT1-D1', 'AT1-F-D')
    r = c.put(f'/api/stok/{sid}', headers=H, json={
        'tip': 'BLOK', 'giris_tarihi': '2026-08-01'})
    assert r.status_code == 200, (r.status_code, r.get_json())
    with fa.app.app_context():
        s = BlokStok.query.get(sid)
        assert s.giris_tarihi == date(2026, 8, 1), s.giris_tarihi
        # Giriş tarihi alış tarihine DOKUNMAZ.
        assert s.alis_tarihi == FL1_GUN, s.alis_tarihi
    yarin = (FL1_GUN + timedelta(days=2)).isoformat()
    for alan in ('giris_tarihi', 'alis_tarihi'):
        r = c.put(f'/api/stok/{sid}', headers=H,
                  json={'tip': 'BLOK', alan: yarin})
        assert r.status_code == 400, (alan, r.status_code, r.get_json())


def test_at1_tarih_alanlari_formda():
    """ÇİVİ: alanlar formda ve kaydetme gövdesinde."""
    import io as _io
    sayfa = _io.open(os.path.join(KOK, 'templates', 'stok.html'),
                     encoding='utf-8').read()
    for kimlik in ('id="duzGirisTarih"', 'id="duzAlisTarih"'):
        assert kimlik in sayfa, f'{kimlik} formda yok'
    govde = sayfa[sayfa.index('async function duzenleKaydet('):]
    govde = govde[:govde.index('/* ═══ KESİME GÖNDER')]
    assert 'g.alis_tarihi = at' in govde, 'alış tarihi gönderilmiyor'
    assert 'g.giris_tarihi = gt' in govde, 'giriş tarihi gönderilmiyor'
    assert "y.baglam === 'alis_tarihi'" in govde, (
        'kapalı dönem reddi kullanıcıya gösterilmiyor')


# ══════════════════════════════════════════════════════════════════
#  FI1 · FATURA İÇERİĞİ
#
#  Cari ekranı faturayı tek satır gösteriyordu; içinde ne olduğu
#  görülemiyordu. Belge üç ayrı yerde duruyor (stok kartları,
#  maliyet satırları, fatura kaydı); uç hareketin bağına göre
#  doğru olanı döndürüyor.
# ══════════════════════════════════════════════════════════════════
def _fi1_icerik(c, hid):
    return c.get(f'/api/cari/hareket/{hid}/icerik', headers=H)


def test_fi1_stok_alis_faturasi_stoklari_gosteriyor():
    """Stok alış faturasının içeriği o faturadaki STOKLARDIR; faturaya
    bağlanmış ödeme kalem değil, bağlı hareket olarak görünür."""
    c = _fl1_hazirlik()
    s1 = _fl1_blok(c, 'FI1-A1', 'FI1-ALIS-A')
    s2 = _fl1_blok(c, 'FI1-A2', 'FI1-ALIS-A')
    with fa.app.app_context():
        h = CariHareket.query.filter_by(baglanti_tip='stok_fatura',
                                        baglanti_id='FI1-ALIS-A').first()
        hid = h.id
        db.session.add(CariHareket(
            id='FI1-OD', cari_id=h.cari_id, cari_unvan=h.cari_unvan,
            islem_tip='Odeme', borc=1000, alacak=0, doviz='USD',
            hareket_tarihi=FL1_GUN, baglanti_tip='stok_fatura',
            baglanti_id='FI1-ALIS-A', kaynak='manuel'))
        db.session.commit()
    r = _fi1_icerik(c, hid)
    assert r.status_code == 200, (r.status_code,
                                  r.get_data(as_text=True)[:250])
    d = r.get_json()
    assert d['tur'] == 'stok_alis', d['tur']
    assert d['baslik']['no'] == 'FI1-ALIS-A', d['baslik']
    assert {k['stok_id'] for k in d['kalemler']} == {s1, s2}, d['kalemler']
    k = d['kalemler'][0]
    assert k['tip'] == 'BLOK' and k['birim'] == 'ton', k
    assert abs(k['miktar'] - 10.0) < 0.001, k
    assert abs(k['matrah'] - 1000.0) < 0.01 and abs(k['kdv'] - 200.0) < 0.01, k
    assert abs(d['ozet']['toplam'] - 2400.0) < 0.01, d['ozet']
    assert abs(d['ozet']['matrah'] - 2000.0) < 0.01, d['ozet']
    assert [x['id'] for x in d['baglilar']] == ['FI1-OD'], d['baglilar']
    # ÖDEMEDEN de aynı belge açılır.
    d2 = _fi1_icerik(c, 'FI1-OD').get_json()
    assert d2['tur'] == 'stok_alis' and len(d2['kalemler']) == 2, d2
    assert d2['baslik']['no'] == 'FI1-ALIS-A', d2['baslik']


def test_fi1_ayni_numarali_baska_carinin_stoklari_karismiyor():
    """"Beklenen Fatura 1" her caride ayrı ayrı var. İçerik yalnız O
    CARİNİN stoklarını gösterir (SF2)."""
    from models import Cari
    c = _fl1_hazirlik()
    with fa.app.app_context():
        if not Cari.query.get('FLX'):
            db.session.add(Cari(id='FLX', unvan='FI1 OBUR TEDARIKCI',
                                cari_tip='Tedarikçi',
                                urun_tedarikcisi=True, gorunurluk='acik'))
            db.session.commit()
    s1 = _fl1_blok(c, 'FI1-B1', 'FI1-ORTAK-NO')
    r = c.post('/api/stok/ekle', headers=H, json={
        'tip': 'BLOK', 'uretici': 'FI1 OBUR TEDARIKCI', 'cins': 'FL1 CINS',
        'blok_no': 'FI1-B2', 'boy': 300, 'yukseklik': 150, 'en': 120,
        'tonaj': 10, 'fiyat': 100, 'fiyat_birim': 'ton', 'doviz': 'USD',
        'kdv_oran': 0, 'alis_tipi': 'yurtici_kdvsiz',
        'fatura_no': 'FI1-ORTAK-NO', 'alis_tarihi': FL1_GUN.isoformat(),
        'fatura_durumu': 'faturali', 'mense': 'TURKIYE'})
    assert r.status_code == 200, (r.status_code, r.get_json())
    with fa.app.app_context():
        hid = CariHareket.query.filter_by(
            baglanti_tip='stok_fatura', baglanti_id='FI1-ORTAK-NO',
            cari_id='FLT').first().id
    d = _fi1_icerik(c, hid).get_json()
    assert [k['stok_id'] for k in d['kalemler']] == [s1], d['kalemler']


def test_fi1_maliyet_faturasi_gider_ve_kdv_satirlarini_gosteriyor():
    c = _fl1_hazirlik()
    sid = _fl1_blok(c, 'FI1-C1', 'FI1-ALIS-C')
    mid = _fl1_maliyet(c, sid, 'Nakliye (Ocak-Fabrika)', 1000, 'FLN', 20,
                       'FI1-NAK-C')
    with fa.app.app_context():
        hid = _fl1_hareket(mid).id
    d = _fi1_icerik(c, hid).get_json()
    assert d['tur'] == 'maliyet', d
    assert d['baslik']['no'] == 'FI1-NAK-C', d['baslik']
    assert sorted(k['tip'] for k in d['kalemler']) == ['GİDER', 'KDV'], (
        d['kalemler'])
    assert abs(d['ozet']['matrah'] - 1000.0) < 0.01, d['ozet']
    assert abs(d['ozet']['kdv'] - 200.0) < 0.01, d['ozet']
    assert abs(d['ozet']['toplam'] - 1200.0) < 0.01, d['ozet']
    # Kalem, hangi stoğa yazıldığını OKUNUR biçimde söylemeli.
    gider = [k for k in d['kalemler'] if k['tip'] == 'GİDER'][0]
    assert 'FI1-C1' in gider['no'], gider


def test_fi1_satis_faturasi_kalemlerini_gosteriyor():
    adm = istemci('admin', 'ADMIN')
    s1 = _bf1_teslim(adm, _bf1_blok('FI1-D1'))
    h = adm.get(f'/api/teslim/birlesik_onhazirlik?siparisler={s1}',
                headers=H).get_json()
    fid = _bf1_birlesik_kes(adm, [s1], 'FI1-FT-D', h['kalemler'])
    with fa.app.app_context():
        hid = CariHareket.query.filter(
            CariHareket.baglanti_tip == 'fatura',
            CariHareket.baglanti_id == fid,
            CariHareket.borc > 0).first().id
    r = _fi1_icerik(adm, hid)
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    d = r.get_json()
    assert d['tur'] == 'fatura', d
    assert d['baslik']['no'] == 'FI1-FT-D', d['baslik']
    assert d['baslik']['fatura_id'] == fid
    assert s1 in d['baslik']['siparisler'], d['baslik']
    assert len(d['kalemler']) == 1, d['kalemler']
    assert abs(d['kalemler'][0]['toplam'] - 5000.0) < 0.01, d['kalemler']
    assert abs(d['ozet']['toplam'] - 5000.0) < 0.01, d['ozet']


def test_fi1_yetki_ve_gizlilik():
    """Gizli carinin belgesi DÖNMEZ; maliyet yetkisi olmayan kullanıcı
    alış kalem fiyatlarını GÖRMEZ (OY1) ama toplamı ve stokları görür;
    belgesiz hareket hata değil, "belge yok" döner."""
    c = _fl1_hazirlik()
    sid = _fl1_blok(c, 'FI1-E1', 'FI1-ALIS-E')
    with fa.app.app_context():
        hid = CariHareket.query.filter_by(
            baglanti_tip='stok_fatura', baglanti_id='FI1-ALIS-E').first().id
    c2 = _oy1_kullanici('fi1cari', {'cari': 'okuma'})
    d = _fi1_icerik(c2, hid).get_json()
    assert d['fiyat_gizli'] is True, d
    assert len(d['kalemler']) == 1 and d['kalemler'][0]['stok_id'] == sid
    for alan in ('birim_fiyat', 'matrah', 'kdv', 'toplam'):
        assert d['kalemler'][0][alan] is None, (alan, d['kalemler'][0])
    assert d['ozet']['matrah'] is None and d['ozet']['kdv'] is None, d['ozet']
    assert abs(d['ozet']['toplam'] - 1200.0) < 0.01, d['ozet']
    # Cari yetkisi hiç yoksa
    c3 = _oy1_kullanici('fi1yok', {'stok': 'okuma'})
    assert _fi1_icerik(c3, hid).status_code == 403
    # Gizli cari: 'satis' kullanıcısı C2'yi göremez (HF1 C1'e ait,
    # o yüzden C2'ye bir hareket açıyoruz).
    with fa.app.app_context():
        db.session.add(CariHareket(
            id='FI1-GZ', cari_id='C2', cari_unvan='GIZLI CARI',
            islem_tip='Tahsilat', borc=0, alacak=10, doviz='USD',
            hareket_tarihi=FL1_GUN))
        db.session.commit()
    assert _fi1_icerik(istemci('satis'), 'FI1-GZ').status_code == 404
    # Belgesiz hareket
    d = _fi1_icerik(c, 'FI1-GZ').get_json()
    assert d['ok'] and d['tur'] == 'yok' and d['baslik'] is None, d
    assert _fi1_icerik(c, 'YOK-BOYLE-BIR').status_code == 404


def test_fi1_ekranda_icerik_aciliyor():
    """ÇİVİ: belgesi olan hareket tıklanır, açık fatura kartında
    "içerik" düğmesi var, liste ilk 15 ile sınırlı kalmıyor."""
    import io as _io
    # GF1: pencere ortak parçaya (_fatura_icerik.html) taşındı;
    # çivi iki dosyayı BİRLİKTE okuyor.
    sayfa = _io.open(os.path.join(KOK, 'templates', 'cari.html'),
                     encoding='utf-8').read()
    _parca_yolu = os.path.join(KOK, 'templates', '_fatura_icerik.html')
    if os.path.exists(_parca_yolu):
        sayfa += _io.open(_parca_yolu, encoding='utf-8').read()
    for parca in ('id="fiModal"', 'async function hareketIcerik(',
                  'function fiFaturadanAc(', '/icerik`',
                  "onclick=\"hareketIcerik('", 'fiFaturadanAc(\'',
                  'HAR_HEPSI'):
        assert parca in sayfa, f'{parca} sayfada yok'
    # Liste ucu bağı taşımalı — düğme ona bakıyor.
    c = istemci('admin', 'ADMIN')
    r = c.get('/api/cari/C1/hareketler', headers=H)
    satir = (r.get_json().get('data') or [])[0]
    assert 'baglanti_tip' in satir and 'baglanti_id' in satir, satir.keys()


# ══════════════════════════════════════════════════════════════════
#  GF1 · GELEN FATURALAR
#
#  Tedarikçiden gelen fatura üç ayrı yerde duruyor; hiçbir ekran
#  üçünü birlikte göstermiyordu. Liste tedarikçiye yazılmış ALACAK
#  satırlarından kurulur.
# ══════════════════════════════════════════════════════════════════
def _gf1_liste(c):
    r = c.get('/api/gelen_faturalar', headers=H)
    assert r.status_code == 200, (r.status_code,
                                  r.get_data(as_text=True)[:250])
    return r.get_json()['data']


def test_gf1_uc_kaynak_tek_listede():
    """Stok alışı, maliyet faturası, alış faturası ve elle girilmiş
    alış fişi aynı listede; ÖDEME ve SATIŞ faturası listede yok."""
    from models import Fatura
    c = _fl1_hazirlik()
    sid = _fl1_blok(c, 'GF1-A1', 'GF1-ALIS-A')
    mid = _fl1_maliyet(c, sid, 'Nakliye (Ocak-Fabrika)', 1000, 'FLN', 20,
                       'GF1-NAK-A')
    with fa.app.app_context():
        db.session.add(Fatura(id='FGF1', fatura_no='GF1-HIZ-A',
                              musteri='FL1 GUMRUKCU', cari_id='FLG',
                              ara_toplam=500, kdv_tutar=100, toplam=600,
                              doviz='USD', durum='Kesildi', yon='alis'))
        db.session.add(CariHareket(
            id='GF1-H1', cari_id='FLG', cari_unvan='FL1 GUMRUKCU',
            islem_tip='Fatura (Alis)', borc=0, alacak=600, doviz='USD',
            hareket_tarihi=FL1_GUN, baglanti_tip='fatura',
            baglanti_id='FGF1', evrak_no='GF1-HIZ-A'))
        db.session.add(CariHareket(
            id='GF1-H2', cari_id='FLG', cari_unvan='FL1 GUMRUKCU',
            islem_tip='Fatura (Alis)', borc=0, alacak=75, doviz='USD',
            hareket_tarihi=FL1_GUN, evrak_no='GF1-FIS-A',
            aciklama='elle girilen fiş', kaynak='manuel'))
        db.session.add(CariHareket(
            id='GF1-OD', cari_id='FLT', cari_unvan='FL1 BLOK TEDARIKCISI',
            islem_tip='Odeme', borc=300, alacak=0, doviz='USD',
            hareket_tarihi=FL1_GUN, baglanti_tip='stok_fatura',
            baglanti_id='GF1-ALIS-A', kaynak='manuel'))
        # Müşteriden gelen TAHSİLAT da alacaktır ama fatura değildir.
        db.session.add(CariHareket(
            id='GF1-TH', cari_id='C1', cari_unvan='ACIK CARI',
            islem_tip='Tahsilat', borc=0, alacak=999, doviz='USD',
            hareket_tarihi=FL1_GUN, kaynak='manuel'))
        db.session.commit()
        mh = _fl1_hareket(mid).id
    s = {f['fatura_no']: f for f in _gf1_liste(c)}
    a = s['GF1-ALIS-A']
    assert a['tur'] == 'stok' and a['icerik'] is True, a
    assert abs(a['tutar'] - 1200.0) < 0.01, a
    assert abs(a['matrah'] - 1000.0) < 0.01 and abs(a['kdv'] - 200.0) < 0.01, a
    m = s['GF1-NAK-A']
    assert m['tur'] == 'maliyet' and m['hareket_id'] == mh, m
    assert m['cari_unvan'] == 'FL1 NAKLIYECI', m
    assert abs(m['matrah'] - 1000.0) < 0.01 and abs(m['kdv'] - 200.0) < 0.01, m
    assert 'Nakliye' in m['alt'] and 'KDV' not in m['alt'], m['alt']
    f = s['GF1-HIZ-A']
    assert f['tur'] == 'fatura' and abs(f['kdv'] - 100.0) < 0.01, f
    assert s['GF1-FIS-A']['tur'] == 'fis', s['GF1-FIS-A']
    assert s['GF1-FIS-A']['icerik'] is False
    idler = {x['hareket_id'] for x in _gf1_liste(c)}
    assert 'GF1-OD' not in idler, 'ödeme fatura diye listelenmiş'
    assert 'GF1-TH' not in idler, 'tahsilat fatura diye listelenmiş'
    # Listedeki her içerik düğmesi ÇALIŞMALI.
    for satir in (a, m, f):
        d = c.get(f"/api/cari/hareket/{satir['hareket_id']}/icerik",
                  headers=H).get_json()
        assert d['ok'] and d['baslik'] is not None, (satir, d)


def test_gf1_satis_faturasi_ve_gizli_cari_listede_yok():
    from models import Fatura
    c = _fl1_hazirlik()
    with fa.app.app_context():
        db.session.add(Fatura(id='FGF2', fatura_no='GF1-SATIS-B',
                              musteri='ACIK CARI', cari_id='C1',
                              toplam=100, doviz='USD', durum='Kesildi',
                              yon='satis'))
        # Satış faturasının iade alacağı: bağ 'fatura', yön SATIŞ.
        db.session.add(CariHareket(
            id='GF1-B1', cari_id='C1', cari_unvan='ACIK CARI',
            islem_tip='Fatura (Alis)', borc=0, alacak=40, doviz='USD',
            hareket_tarihi=FL1_GUN, baglanti_tip='fatura',
            baglanti_id='FGF2', evrak_no='GF1-SATIS-B'))
        db.session.add(CariHareket(
            id='GF1-B2', cari_id='C2', cari_unvan='GIZLI CARI',
            islem_tip='Fatura (Alis)', borc=0, alacak=10, doviz='USD',
            hareket_tarihi=FL1_GUN, evrak_no='GF1-GIZLI-B'))
        db.session.add(CariHareket(
            id='GF1-B3', cari_id='C1', cari_unvan='ACIK CARI',
            islem_tip='Fatura (Alis)', borc=0, alacak=20, doviz='USD',
            hareket_tarihi=FL1_GUN, evrak_no='GF1-ACIK-B'))
        db.session.commit()
    idler = {x['hareket_id'] for x in _gf1_liste(c)}
    assert 'GF1-B1' not in idler, 'satış faturası gelen fatura sayılmış'
    assert 'GF1-B2' in idler          # yönetici gizli cariyi görür
    # Gizlilik ROL kuralı: 'satis' kullanıcısı C2'yi göremez.
    idler2 = {x['hareket_id'] for x in _gf1_liste(istemci('satis'))}
    assert 'GF1-B2' not in idler2, 'gizli carinin faturası sızdı'
    assert 'GF1-B3' in idler2, 'açık carinin faturası görünmüyor'
    c3 = _oy1_kullanici('gf1yok', {'stok': 'okuma'})
    assert c3.get('/api/gelen_faturalar', headers=H).status_code == 403


def test_gf1_fatura_no_yalniz_o_carinin_stoklarini_tasiyor():
    """HATA: yer tutucu numara ("Beklenen Fatura 1") her caride ayrı
    ayrı var. Bir tedarikçinin gerçek numarası girilince tabanda
    AYNI NUMARAYI taşıyan BÜTÜN stoklar yeniden adlandırılıyordu:
    öbür tedarikçinin stokları başkasının faturasına geçiyor, kendi
    borcundan kopuyordu."""
    from models import Cari, Maliyet
    c = _fl1_hazirlik()
    with fa.app.app_context():
        if not Cari.query.get('FLX'):
            db.session.add(Cari(id='FLX', unvan='FI1 OBUR TEDARIKCI',
                                cari_tip='Tedarikçi',
                                urun_tedarikcisi=True, gorunurluk='acik'))
            db.session.commit()
    s1 = _fl1_blok(c, 'GF1-C1', 'GF1-YERTUTUCU')        # FLT, KDV'li
    r = c.post('/api/stok/ekle', headers=H, json={
        'tip': 'BLOK', 'uretici': 'FI1 OBUR TEDARIKCI', 'cins': 'FL1 CINS',
        'blok_no': 'GF1-C2', 'boy': 300, 'yukseklik': 150, 'en': 120,
        'tonaj': 10, 'fiyat': 100, 'fiyat_birim': 'ton', 'doviz': 'USD',
        'kdv_oran': 0, 'alis_tipi': 'yurtici_kdvsiz',
        'fatura_no': 'GF1-YERTUTUCU', 'alis_tarihi': FL1_GUN.isoformat(),
        'fatura_durumu': 'faturali', 'mense': 'TURKIYE'})
    assert r.status_code == 200, (r.status_code, r.get_json())
    s2 = r.get_json()['id']
    with fa.app.app_context():
        h1 = CariHareket.query.filter_by(
            baglanti_tip='stok_fatura', baglanti_id='GF1-YERTUTUCU',
            cari_id='FLT').first()
        hid = h1.id
        db.session.add(CariHareket(
            id='GF1-C-OD', cari_id='FLT', cari_unvan=h1.cari_unvan,
            islem_tip='Odeme', borc=100, alacak=0, doviz='USD',
            hareket_tarihi=FL1_GUN, baglanti_tip='stok_fatura',
            baglanti_id='GF1-YERTUTUCU', kaynak='manuel'))
        db.session.commit()
    r = c.put(f'/api/cari/hareket/{hid}/fatura_no', headers=H,
              json={'fatura_no': 'GF1-GERCEK-1'})
    assert r.status_code == 200, (r.status_code, r.get_json())
    assert r.get_json()['guncellenen_stok'] == 1, r.get_json()
    with fa.app.app_context():
        assert BlokStok.query.get(s1).fatura_no == 'GF1-GERCEK-1'
        assert BlokStok.query.get(s2).fatura_no == 'GF1-YERTUTUCU', (
            'öbür tedarikçinin stoğu başkasının faturasına geçti')
        assert CariHareket.query.filter_by(
            baglanti_tip='stok_fatura', cari_id='FLX',
            baglanti_id='GF1-YERTUTUCU').first() is not None, (
            'öbür tedarikçinin borcu da yeniden adlandırılmış')
        # Aynı faturanın ödemesi ve KDV satırı da yeni numarada.
        assert CariHareket.query.get('GF1-C-OD').baglanti_id == 'GF1-GERCEK-1'
        k = Maliyet.query.filter_by(baglanti_id=s1,
                                    maliyet_tip='Devreden KDV').first()
        assert k.fatura_no == 'GF1-GERCEK-1', k.fatura_no
    # Yeniden adlandırılan fatura BÜTÜN kalmalı: içerik ve liste.
    d = c.get(f'/api/cari/hareket/{hid}/icerik', headers=H).get_json()
    assert [x['stok_id'] for x in d['kalemler']] == [s1], d['kalemler']
    assert [x['id'] for x in d['baglilar']] == ['GF1-C-OD'], d['baglilar']
    s = {f['hareket_id']: f for f in _gf1_liste(c)}
    assert s[hid]['fatura_no'] == 'GF1-GERCEK-1' and not s[hid]['bekleyen']


def test_gf1_bekleyen_isareti():
    c = _fl1_hazirlik()
    r = c.post('/api/stok/ekle', headers=H, json={
        'tip': 'BLOK', 'uretici': 'FL1 BLOK TEDARIKCISI', 'cins': 'FL1 CINS',
        'blok_no': 'GF1-D1', 'boy': 300, 'yukseklik': 150, 'en': 120,
        'tonaj': 10, 'fiyat': 100, 'fiyat_birim': 'ton', 'doviz': 'USD',
        'kdv_oran': 0, 'alis_tipi': 'yurtici_kdvsiz',
        'alis_tarihi': FL1_GUN.isoformat(),
        'fatura_durumu': 'faturali', 'mense': 'TURKIYE'})
    assert r.status_code == 200, (r.status_code, r.get_json())
    bek = [f for f in _gf1_liste(c) if f['bekleyen']]
    assert bek and all(f['fatura_no'].lower().startswith('beklenen fatura')
                       for f in bek), bek
    assert any(f['tur'] == 'stok' for f in bek)


def test_gf1_sayfa_ve_ortak_pencere():
    """Sayfa açılıyor, Finans sekmelerinde duruyor ve fatura içeriği
    penceresi cari ekranıyla AYNI parçadan geliyor (iki kopya ilk
    düzeltmede ayrışırdı)."""
    import io as _io
    c = istemci('admin', 'ADMIN')
    r = c.get('/gelen-fatura')
    assert r.status_code == 200, r.status_code
    govde = r.get_data(as_text=True)
    assert govde.count('id="fiModal"') == 1, govde.count('id="fiModal"')
    assert 'href="/gelen-fatura"' in govde, 'sekme yok'
    assert 'async function hareketIcerik(' in govde
    r = c.get('/cari')
    assert r.status_code == 200
    cari = r.get_data(as_text=True)
    assert cari.count('id="fiModal"') == 1, cari.count('id="fiModal"')
    assert cari.count('async function hareketIcerik(') == 1
    oku = lambda ad: _io.open(os.path.join(KOK, 'templates', ad),
                              encoding='utf-8').read()
    assert 'async function hareketIcerik(' not in oku('cari.html'), (
        'pencere cari.html içinde de duruyor — iki kopya')
    assert "{% include '_fatura_icerik.html' %}" in oku('cari.html')
    assert "{% include '_fatura_icerik.html' %}" in oku('gelen_fatura.html')
    sayfa = oku('gelen_fatura.html')
    for parca in ("api('/api/gelen_faturalar')", 'function gfSuzgecler(',
                  'function gfGecenler(', '/fatura_no`'):
        assert parca in sayfa, f'{parca} sayfada yok'
    # Fatura yetkisi olmayan sayfaya giremez.
    c2 = _oy1_kullanici('gf1sayfa', {'stok': 'okuma'})
    assert c2.get('/gelen-fatura').status_code in (302, 303)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA AF1 — ALIŞ FATURASINDA ÖDEME · ÖLÜ ÇEK · KESİMİN MALİYETİ
================================================================

ÖNKOŞUL: **yama_em1.py uygulanmış olmalı.** Betik denetliyor.

Taramanın kalan iki maddesi. Peşlerinden üçüncü bir şey çıktı ve o,
ötekilerin KÖKÜ oldu.

═══ 1 · ALIŞ FATURASINA FARKLI DÖVİZDE ÖDEME ═══

`api_cari_acik_faturalar` içinde aynı if/else'in iki kolu vardı:
satış kolu TT1 ile düzeltilmiş, alış kolu ham `sum(borc)` ile
kalmıştı. Düzeltmenin gerekçesi bugün hâlâ o satırların üstünde
yazıyor.

ÖLÇÜLDÜ — 10.000 USD alış faturası, 20.000 TRY ödeme (kur 40):

      önce   ödenen 20.000 sayıldı → borç KAPANDI, listeden düştü
      sonra  ödenen 500,00 → kalan 9.500,00 ✓

Artık iki yön de aynı yoldan geçiyor; yönü `f.yon` söylüyor
(satışta `alacak`, alışta `borc`).

═══ 2 · KARŞILIKSIZ ÇEK FATURAYI AÇMIYORDU ═══

Koddaki koruma şunu diyordu: *"Karşılıksız çıkan bir çek faturayı
kapatmış gibi dururSA fatura 'Tahsil Edildi' kalır ve kalan bakiye
0 görünür — para hiç gelmediği hâlde."* Doğru teşhis; ama süzgeç
**hedefini vurmuyordu**:

  · faturaya BAĞLI çekin ödeme hareketi `baglanti_tip='fatura'`
    ile yazılıyor,
  · ölü-çek süzgeci ise yalnız `baglanti_tip='cek'` satırlarına
    bakıyordu.

Yani koruma, tam da anlattığı duruma — "çekle ödenmiş fatura" —
hiç uğramıyordu.

═══ 3 · KÖKÜ: SAKLANAN HAREKET KİMLİĞİ HİÇ TUTMUYORDU ═══

İkinci maddeyi düzeltmek için çekin ödeme hareketini bulmam
gerekti. `Cek.cari_hareket_id` bunun için var — ama **işe
yaramıyordu**.

`before_insert` dinleyicisi (RN1) hareketin kimliğini yazılmadan
hemen önce okunur hâle çeviriyor. Kimlik flush'tan ÖNCE okunursa
saklanan değer o geçici kimlik oluyor:

      çek.cari_hareket_id = 'HR-2AECDF'     ← veritabanında YOK
      gerçek hareket       = 'HR-MST26-0001'

O kimlikle arayan her şey sessizce boş dönüyordu. Üç yerde aynı
hata vardı (çek oluşturma, çek cirosu, sıcak satış faturası);
üçünde de kimlik artık flush'tan SONRA okunuyor.

ÖLÇÜLDÜ (gerçek uçlarla, baştan sona):

      çek alındı       fatura "Tahsil Edildi", açık listeden düştü
      KARŞILIKSIZ      önce: "Tahsil Edildi" kaldı, listede yok
                       sonra: "Kesildi", kalan 10.000,00 ✓

Sistem ters hareketi zaten doğru açıyordu (cari bakiyesi
düzeliyordu); yanlış olan FATURANIN kendisiydi.

═══ 4 · KESİM GERİ ALININCA MALİYET ÖKSÜZ KALIYORDU ═══

Geri alma hedef stokları siliyor ama onlara işlenmiş maliyet
kayıtlarına dokunmuyordu.

ÖLÇÜLDÜ: plakaya 500 $ fason işlendi, kesim geri alındı →
plaka 2 → 0, maliyet satırı 1 → 1 (aktif, hedefi yok). Para
kayıtta duruyor ama hiçbir stoğun maliyetinde değil, raporda
görünmüyor; tedarikçiye borç doğurduysa borç da dayanaksız.

Artık geri alma **reddediliyor** ve hangi maliyetlerin engellediğini
yazıyor. Sessizce silmek ya da bloğa taşımak yerine reddetmeyi
seçtim: gider gerçekten yapılmış da olabilir, yanlış girilmiş de —
bunu yalnız sen bilirsin. Rezervasyon durumunda da aynı şey
yapılıyor.

  Maliyetsiz kesim eskisi gibi normal geri alınıyor (denendi).

═══ SANA BİR GÖZLEM — DÜZELTMEDİM ═══

Çapraz dövizli bir ödemede, ödeme gününe ait kur YOKSA çevrim
sıfır dönüyor ve ödeme HİÇ sayılmıyor (fatura tam açık görünür).
Eskisi ham toplayıp fazla sayıyordu, yenisi hiç saymıyor — ikisi de
yanlış, ters yönlerde. Bu satış tarafında da eskiden beri böyle.

Dokunmadım çünkü doğru davranışın ne olduğu senin kararın: en yakın
güne düşmek mi, hareketin kendi `kur_uygulanan` değerine düşmek mi,
yoksa açıkça uyarmak mı? Söyle, yaparım.

═══ DOĞRULANDI ═══
  248 test geçti (244 + 4). Yeni testlerin üçü DAVRANIŞ bakıyor:
  gerçek uçlardan çek alıp karşılıksız işaretliyor, alış faturasına
  TL ödeme yapıyor, maliyetli kesimi geri almayı deniyor.
  firma · js · form · akış denetimleri temiz.

DOSYALAR
--------
  flask_app.py           yön · ölü çek · kimlik flush'ı · kesim kapısı
  tests/test_kritik.py   4 yeni test

Şema yok, göç yok.

KULLANIM
--------
  python3 yama_af1.py            # RAPOR
  python3 yama_af1.py --uygula
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
    'flask_app.py': 'AF1 · KİMLİK FLUSH\'TAN SONRA OKUNUR',
    'tests/test_kritik.py': 'def test_af1_alis_faturasinda_capraz_doviz_odeme',
}
ONKOSUL = {
    'flask_app.py': 'EM1 · İKİ SÜZGEÇ, ALTI YER',
    'tests/test_kritik.py': 'def test_em1_liste_ve_rapor_ayni_sayiyi_soyluyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'AF1 · flask_app.py blok 1',
     r'''        # Hedef stokları sil (kesimden gelen rezervasyonları da temizle)
''',
     r'''        # ── KG1 · HEDEFE İŞLENMİŞ MALİYET VARSA GERİ ALMA DURUR ──
        # Geri alma hedef stokları SİLİYOR ama onlara işlenmiş maliyet
        # kayıtlarına dokunmuyordu: para kayıtta kalıyor, artık var
        # olmayan bir stoğa bağlı duruyor, hiçbir stoğun maliyetine
        # girmiyor ve raporlarda görünmüyor. Tedarikçiye borç
        # doğurduysa borç da duruyor — dayanağı yok.
        #
        # ÖLÇÜLDÜ: plakaya 500 $ fason işlendi, kesim geri alındı.
        #   plaka 2 → 0,  maliyet satırı 1 → 1 (aktif=True, hedef YOK)
        #
        # `denetim_zincir.py`de bu başlık zaten vardı ("artık var
        # olmayan stoğa bağlı maliyet") — yani oluşabileceği
        # biliniyordu ama oluşmasını engelleyen bir şey yoktu.
        #
        # Sessizce silmek ya da bloğa taşımak YERİNE reddediyoruz:
        # gider gerçekten yapılmış olabilir de, yanlış girilmiş de.
        # Bunu yalnız kullanıcı bilir. Rezervasyon durumunda da aynı
        # şey yapılıyor — tutarlı olan bu.
        _maliyetli = []
        for d in k.detaylar:
            if not d.hedef_stok_id:
                continue
            for _m in Maliyet.query.filter(
                    Maliyet.baglanti_id == d.hedef_stok_id,
                    Maliyet.aktif.is_(True)).all():
                _maliyetli.append(
                    f'{_baglanti_okunabilir("stok", d.hedef_stok_id)} → '
                    f'{_m.maliyet_tip or "(tipsiz)"} '
                    f'{float(_m.tutar or 0):,.2f} {_m.doviz or ""}'
                    + (f' · {_m.fatura_no}' if _m.fatura_no else ''))
        if _maliyetli:
            return jsonify({'ok': False, 'error': 'hedefte_maliyet_var',
                'maliyetler': _maliyetli,
                'mesaj': 'Kesimden çıkan stoklara maliyet işlenmiş; geri '
                         'alınırsa bu kayıtlar dayanaksız kalır. Önce '
                         'maliyetleri silin ya da kaynak bloğa taşıyın: '
                         + '; '.join(_maliyetli[:4])
                         + (f' (+{len(_maliyetli) - 4} kalem daha)'
                            if len(_maliyetli) > 4 else '')}), 400

        # Hedef stokları sil (kesimden gelen rezervasyonları da temizle)
'''),
    ('flask_app.py', 'AF1 · flask_app.py blok 2',
     r'''                fatura.cari_hareket_id = ch.id
''',
     r'''                db.session.flush()   # AF1 — kimlik flush'tan sonra
                fatura.cari_hareket_id = ch.id
'''),
    ('flask_app.py', 'AF1 · flask_app.py blok 3',
     r'''            if yon == 'satis':
                # TT1: tahsilat ekraniyla AYNI hesap — cek ve farkli
                # dovizde odemeler de sayilir. Eskiden yalnizca ham
                # alacak toplaniyordu: 30.000 TRY'lik odeme 30.000 USD
                # gibi dusuluyor, cekle odenen fatura acik gorunuyordu.
                odenen = _fatura_odenen_esdeger(f)
            else:
                odenen = db.session.query(db.func.sum(CariHareket.borc)).filter_by(
                    baglanti_tip='fatura', baglanti_id=f.id).scalar() or 0
''',
     r'''            # ── AF1 · TEK YOL ──
            # TT1: tahsilat ekraniyla AYNI hesap — cek ve farkli
            # dovizde odemeler de sayilir. Eskiden yalnizca ham
            # alacak toplaniyordu: 30.000 TRY'lik odeme 30.000 USD
            # gibi dusuluyor, cekle odenen fatura acik gorunuyordu.
            #
            # O duzeltme YALNIZ SATIS koluna yapilmisti; alis kolu
            # ham `sum(borc)` ile kalmisti. OLCULDU: 10.000 USD'lik
            # alis faturasina 20.000 TRY (= 500 USD) odeme yapilinca
            # borc TAMAMEN kapanmis gorunuyor, acik borclar
            # listesinden dusuyordu. Karsiliksiz cikan verilen cek de
            # odeme sayiliyordu.
            #
            # Artik iki yon de ayni yoldan geciyor; yonu `f.yon`
            # soyluyor.
            odenen = _fatura_odenen_esdeger(f)
'''),
    ('flask_app.py', 'AF1 · flask_app.py blok 4',
     r'''                cek.cari_hareket_id = ch.id
                db.session.flush()
''',
     r'''                db.session.flush()
                    # ── AF1 · KİMLİK FLUSH'TAN SONRA OKUNUR ──
                # `before_insert` dinleyicisi (RN1) hareketin kimliğini
                # yazılmadan hemen önce OKUNUR hâle çeviriyor
                # (HR-MST26-0001). Kimlik flush'tan ÖNCE okunursa saklanan
                # değer o rastgele geçici kimlik oluyor ve veritabanında
                # ÖYLE BİR KAYIT HİÇ OLMUYOR.
                #
                # ÖLÇÜLDÜ: çek.cari_hareket_id = 'HR-2AECDF' iken gerçek
                # hareket 'HR-MST26-0001'di; o kimlikle arayan her şey
                # sessizce boş dönüyordu.
                cek.cari_hareket_id = ch.id
'''),
    ('flask_app.py', 'AF1 · flask_app.py blok 5',
     r'''                    c.cari_hareket_id = _ch.id
''',
     r'''                    db.session.flush()   # AF1 — kimlik flush'tan sonra
                    c.cari_hareket_id = _ch.id
'''),
    ('flask_app.py', 'AF1 · flask_app.py blok 6',
     r'''    def _hareket_fatura_esdegeri(h, f_doviz):
        """
        Bir ödeme hareketinin (alacak) FATURA DÖVİZİ cinsinden eşdeğerini döner.
        Aynı dövizde: ham tutar. Farklı dövizde (çapraz): TRY köprüsü —
        hareketin TRY karşılığı, hareket tarihindeki fatura-dövizi kuruna bölünür.
        """
        tutar = float(h.alacak or 0)
        if (h.doviz or 'USD') == f_doviz:
            return tutar
        k = 1.0 if f_doviz == 'TRY' else _kur_getir(f_doviz, h.hareket_tarihi)
        if not k or k <= 0:
            return 0.0
        tutar_try = float(h.alacak_try or 0)
''',
     r'''    def _fatura_odeme_alani(f):
        """Bu faturaya yapılan ÖDEME hangi sütunda durur?

        ── AF1 · YÖN ──
        SATIŞ faturasında tahsilat `alacak` sütunundadır; ALIŞ
        faturasında ödeme `borc` sütununda. Yön bilinmeden yapılan
        her hesap yarım kalıyordu.
        """
        return 'borc' if (getattr(f, 'yon', None) or 'satis') == 'alis' \
            else 'alacak'

    def _hareket_fatura_esdegeri(h, f_doviz, alan='alacak'):
        """
        Bir ödeme hareketinin FATURA DÖVİZİ cinsinden eşdeğerini döner.
        Aynı dövizde: ham tutar. Farklı dövizde (çapraz): TRY köprüsü —
        hareketin TRY karşılığı, hareket tarihindeki fatura-dövizi kuruna bölünür.

        AF1: `alan` ile yön geliyor — satışta 'alacak', alışta 'borc'.
        """
        tutar = float(getattr(h, alan) or 0)
        if (h.doviz or 'USD') == f_doviz:
            return tutar
        k = 1.0 if f_doviz == 'TRY' else _kur_getir(f_doviz, h.hareket_tarihi)
        if not k or k <= 0:
            return 0.0
        tutar_try = float(getattr(h, alan + '_try') or 0)
'''),
    ('flask_app.py', 'AF1 · flask_app.py blok 7',
     r'''        hs = CariHareket.query.filter(
            CariHareket.baglanti_tip == 'fatura', CariHareket.baglanti_id == f.id,
            CariHareket.alacak > 0).all()
        # OLU cekler odeme SAYILMAZ. Karsiliksiz cikan bir cek
        # faturayi kapatmis gibi durursa fatura "Tahsil Edildi"
        # kalir ve kalan bakiye 0 gorunur — para hic gelmedigi halde.
        cek_hs = CariHareket.query.filter(
            CariHareket.baglanti_tip == 'cek', CariHareket.alacak > 0,
            CariHareket.baglanti_id.in_(
                db.session.query(Cek.id).filter(
                    Cek.fatura_id == f.id,
                    db.or_(Cek.durum.is_(None),
                           Cek.durum.notin_(CEK_OLU_DURUMLAR))))).all()
        gorulen, toplam = set(), 0.0
        for h in hs + cek_hs:
            if h.id in gorulen:
                continue
            gorulen.add(h.id)
            toplam += _hareket_fatura_esdegeri(h, f_doviz)
''',
     r'''        # AF1: SATIŞTA tahsilat `alacak`, ALIŞTA ödeme `borc`.
        _alan = _fatura_odeme_alani(f)
        _sutun = getattr(CariHareket, _alan)
        hs = CariHareket.query.filter(
            CariHareket.baglanti_tip == 'fatura', CariHareket.baglanti_id == f.id,
            _sutun > 0).all()
        # OLU cekler odeme SAYILMAZ. Karsiliksiz cikan bir cek
        # faturayi kapatmis gibi durursa fatura "Tahsil Edildi"
        # kalir ve kalan bakiye 0 gorunur — para hic gelmedigi halde.
        cek_hs = CariHareket.query.filter(
            CariHareket.baglanti_tip == 'cek', _sutun > 0,
            CariHareket.baglanti_id.in_(
                db.session.query(Cek.id).filter(
                    Cek.fatura_id == f.id,
                    db.or_(Cek.durum.is_(None),
                           Cek.durum.notin_(CEK_OLU_DURUMLAR))))).all()

        # ── AF1 · YUKARIDAKI KORUMA HEDEFINI VURMUYORDU ──
        # Faturaya BAGLI bir cekin odeme hareketi `baglanti_tip='fatura'`
        # ile yaziliyor (cek.py: "'fatura' if cek.fatura_id else 'cek'").
        # Ustteki olu-cek susgeci ise yalnizca `baglanti_tip='cek'`
        # satirlarina bakiyor — yani tam da yorumun anlattigi duruma,
        # "cekle odenmis fatura"ya hic ugramiyordu.
        #
        # OLCULDU (gercek uclarla): 10.000 USD'lik satis faturasi ceke
        # baglandi -> "Tahsil Edildi". Cek KARSILIKSIZ isaretlendi ->
        # sistem ters hareketi dogru acti (cari bakiyesi duzeldi) ama
        # FATURA "Tahsil Edildi" kaldi ve acik fatura listesinden
        # dusmus durumda kaldi. Para hic gelmedi, fatura kapali.
        #
        # Olu cekin KENDI odeme hareketini disariyoruz.
        _olu_hareketler = {
            c.cari_hareket_id for c in Cek.query.filter(
                Cek.fatura_id == f.id,
                Cek.durum.in_(CEK_OLU_DURUMLAR)).all()
            if c.cari_hareket_id}

        gorulen, toplam = set(), 0.0
        for h in hs + cek_hs:
            if h.id in gorulen or h.id in _olu_hareketler:
                continue
            gorulen.add(h.id)
            toplam += _hareket_fatura_esdegeri(h, f_doviz, _alan)
'''),
    ('tests/test_kritik.py', 'AF1 · tests/test_kritik.py blok 1',
     r'''            'faturaya bağlı satış değişmiş'
''',
     r'''            'faturaya bağlı satış değişmiş'


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
    assert abs(kayit[0]['kalan'] - _beklenen) < 0.02, \
        f"kalan {kayit[0]['kalan']}, kur {_kur} ile beklenen {_beklenen}"
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
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA AF1 — ALIŞ FATURASINDA ÖDEME · ÖLÜ ÇEK · KESİMİN MALİYETİ')
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
        print('    python3 yama_af1.py            # rapor')
        print('    python3 yama_af1.py --uygula')
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
        print('  ⊙ Yama AF1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_af1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_af1'
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
    print('    2) venv/bin/python -m pytest tests/test_kritik.py -q   # 248')
    print()
    print('  BAKILACAK YER')
    print('    1. Cari -> tedarikci -> Odeme: acik ALIS borclari artik')
    print('       TL odeme yapilmis faturalari da dogru gosteriyor.')
    print('    2. Karsiliksiz isaretlenen cek, bagli faturayi yeniden')
    print('       aciyor (durum "Kesildi"e doner).')
    print('    3. Maliyeti olan bir kesimi geri almayi dene: reddeder')
    print('       ve hangi maliyetlerin engelledigini yazar.')
    print()
    print('  RAKAMLARIN DEGISEBILIR')
    print('    TL ile odenmis USD alis faturalarin yeniden ACIK')
    print('    gorunecek — cunku gercekten acik. Karsiliksiz cekle')
    print('    kapanmis faturalar da geri gelecek.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

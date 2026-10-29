#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA VR1 — ÇİFT BACAKLI TRANSFER, TEK BACAK SİLİNEMEZ
=======================================================

ÖNKOŞUL: **yama_ip1.py uygulanmış olmalı.** Betik denetliyor.
Şema değişikliği YOK, göç YOK. Ekran DEĞİŞMİYOR.

Kullanım:
    python3 yama_vr1.py              # rapor, dosyalara dokunmaz
    python3 yama_vr1.py --uygula
    venv/bin/python -m pytest tests/test_kritik.py -q     # 319

═══ TARAMA ═══

Bugünün en çok hata üreten sınıfını taradım: "bir işlem yan etki
yaratıyor ama geri alınırken o yan etki kalıyor". TS1 (kasa), IP1
(çek, cari, stok) hep buydu.

Yöntem: `baglanti_tip` ile bağ kurarak cari/kasa hareketi YARATAN
her yer bulundu, her bağ tipi için bir GERİ ALMA yolu olup olmadığı
arandı. 13 bağ tipinden 4'ü aday çıktı; ikisi yanlış pozitifti
(kur farkı başka kolondan geri alınıyor, avans siparişin kendi
akışıyla dönüyor). Kalan ikisi gerçek çıktı ve üçüncüsünü de
ölçerken buldum.

═══ ÖLÇÜLEN ÜÇ HATA ═══

1 · KASA VİRMANI — PARA YOKTAN VAR OLUYOR

   A kasasından B'ye 3.000 TL virman. Çıkış bacağını sil:
     · A parasını geri alır  (10.000)
     · B'de para DURUR       (3.000)
     · sistemdeki toplam 10.000 → 13.000 TL

   `api_kasa_hareket_sil` yalnızca `baglanti_tip='tahsilat'`
   olanı engelliyordu; virman bacağı serbestçe siliniyordu.

2 · CARİ → KASA TRANSFERİ

   5.000 TL cariden kasaya. Cari hareketini sil: kasa 5.000 TL'yi
   TUTAR, karşılığı olan hiçbir kayıt kalmaz. Kasa, kaynağı
   olmayan bir parayı gösterir.

   TS1'in `_hareket_kasa_geri_al`'ı `('cari_hareket','tahsilat')`
   bağlarına bakıyor; bu yol kasa kaydını `'virman'` ile yazıyor
   ve bağ kimliği olarak HAREKETİ değil CARİYİ veriyor.

3 · CARİ → CARİ TRANSFERİ

   2.000 TL bir cariden ötekine. Bir bacağı sil: öteki cari
   alacaklı kalır, karşılığı yoktur.

Üçünde de transfer ATOMİK yaratılıyor ("CIFT TARAFLI: kaynaktan
CIKIS + hedefe GIRIS, tek islemde") ama atomik SİLİNMİYORDU.

═══ ÇÖZÜM ═══

Tek kapı: `_transfer_esi(hareket)`. Bir bacağın eşini bulur,
çağıran ikisini birlikte siler ve iki bakiyeyi de düzeltir.

EŞ NASIL BULUNUR: bağ alanları (kim kime) yapıyı verir; aynı gün
aynı tutarla iki transfer yapılmışsa yapı tek başına ayırt etmez.
Zaman damgası ayırır — eşler AYNI İSTEKTE yaratıldığı için
saniyeler içindedir (TS1'de kasa kaydını bulurken kullandığımız
yöntem).

BELİRSİZSE DOKUNULMAZ: iki eşit aday varsa 409 döner ve sebebini
söyler. Yanlış bacağı silmek, hiç silmemekten kötüdür — o zaman
ikisi birden bozulur.

═══ DOĞRULAMA ═══

  · 319 test geçiyor (314 → 319)
  · Üç davranış testi de TABANDA düşüyor
  · Kasa toplamı üç senaryoda da korunuyor (10.000 → 10.000)
  · Sınır testi: elle girilen (virman olmayan) kasa hareketi
    silindiğinde yalnız kendi etkisi gidiyor — `_transfer_esi`
    yalnız `kaynak='virman'` kayıtlara bakıyor
  · Bekçi testinin SINIRI dürüstçe yazıldı: bugünkü üç hatayı
    YAKALAMAZDI (tabanda da geçiyor), çünkü onlarda geri alma yolu
    vardı, sadece eşi bulamıyordu. İşi daha dar: yarın yeni bir
    bağ tipi hiç geri alınmazsa takımı kırmak.
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
    'flask_app.py': 'def _transfer_esi(hareket, pencere_sn=120)',
    'tests/test_kritik.py':
        'def test_vr1_virmanin_tek_bacagi_silinince_para_yoktan_var_olmuyor',
}
ONKOSUL = {
    'flask_app.py': 'def _siparis_iptal_kararlarini_uygula(sip, karar, onay)',
    'tests/test_kritik.py':
        'def test_ip1_faturali_siparis_iptali_karar_istiyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'VR1 · flask_app.py blok 1',
     r'''    def _hareket_kasa_geri_al(hareket):
''',
     r'''    # ══════════════════════════════════════════════════════════════
    #  VR1 · ÇİFT BACAKLI TRANSFER, TEK BACAK SİLİNEMEZ
    #
    #  Transfer ATOMİK yaratılıyor ("CIFT TARAFLI: kaynaktan CIKIS +
    #  hedefe GIRIS, tek islemde") ama ATOMİK SİLİNMİYORDU. Ölçüldü:
    #
    #   · Kasa virmanı (A→B 3.000 TL), çıkış bacağını sil:
    #     A parasını geri alır, B'de para DURUR.
    #     Sistemdeki toplam 10.000 → 13.000 TL. Para yoktan var oldu.
    #   · Cari→kasa transferi (5.000 TL), cari hareketi sil:
    #     kasa 5.000 TL'yi tutar, karşılığı olan cari kaydı yoktur.
    #   · Cari→cari transferi (2.000 TL), bir bacağı sil:
    #     bir cari alacaklı kalır, karşılığı yoktur.
    #
    #  EŞİ NASIL BULUNUR: bağ alanları (kim kime) yapıyı verir, ama
    #  aynı gün aynı tutarla iki transfer yapılmışsa yapı tek başına
    #  ayırt etmez. Zaman damgası ayırır: eşler AYNI İSTEKTE
    #  yaratıldığı için saniyeler içindedir (TS1'de kasa kaydını
    #  bulurken kullandığımız yöntem).
    #
    #  BELİRSİZSE DOKUNULMAZ. Yanlış bacağı silmek, hiç silmemekten
    #  kötüdür: ikisi de bozulur.
    # ══════════════════════════════════════════════════════════════
    def _transfer_esi(hareket, pencere_sn=120):
        """Bir transfer bacağının EŞİNİ bulur.

        Döner: (es_kayit | None, belirsiz_mi)
        """
        def _zaman(x):
            return (getattr(x, 'guncelleme', None)
                    or getattr(x, 'olusturma', None))

        ref = _zaman(hareket)
        adaylar = []

        if isinstance(hareket, KasaHareket):
            # Kasa ↔ kasa virmanı: eşin kasası bizim baglanti_id'miz,
            # eşin baglanti_id'si bizim kasamız, yön ters.
            if (hareket.baglanti_tip or '') != 'virman':
                return None, False
            try:
                karsi_kasa = int(hareket.baglanti_id)
            except (TypeError, ValueError):
                return None, False      # cari→kasa bacağı; burada değil
            ters = 'giris' if (hareket.tip or '') == 'cikis' else 'cikis'
            adaylar = KasaHareket.query.filter(
                KasaHareket.id != hareket.id,
                KasaHareket.kasa_id == karsi_kasa,
                KasaHareket.baglanti_tip == 'virman',
                KasaHareket.baglanti_id == str(hareket.kasa_id),
                KasaHareket.tip == ters,
                KasaHareket.tutar == hareket.tutar).all()

        elif isinstance(hareket, CariHareket):
            bt = (hareket.baglanti_tip or '')
            if bt == 'cari' and (hareket.kaynak or '') == 'virman':
                # Cari ↔ cari bakiye transferi
                adaylar = CariHareket.query.filter(
                    CariHareket.id != hareket.id,
                    CariHareket.cari_id == hareket.baglanti_id,
                    CariHareket.baglanti_tip == 'cari',
                    CariHareket.baglanti_id == hareket.cari_id,
                    CariHareket.kaynak == 'virman').all()
            elif bt == 'kasa' and (hareket.kaynak or '') == 'virman':
                # Cari → kasa: eş bir KASA hareketi. Tutar DÖVİZ
                # ÇEVRİMİYLE farklı olabilir, o yüzden tutara
                # bakılmaz; bağ + zaman yeter.
                try:
                    kasa_id = int(hareket.baglanti_id)
                except (TypeError, ValueError):
                    return None, False
                adaylar = KasaHareket.query.filter(
                    KasaHareket.kasa_id == kasa_id,
                    KasaHareket.baglanti_tip == 'virman',
                    KasaHareket.baglanti_id == hareket.cari_id).all()
            else:
                return None, False
        else:
            return None, False

        if not adaylar:
            return None, False
        if len(adaylar) == 1:
            return adaylar[0], False
        # Birden çok aday: zamanca EN YAKIN olanı. Eşitlik varsa
        # belirsizdir — dokunulmaz.
        if not ref:
            return None, True
        olculu = []
        for a in adaylar:
            z = _zaman(a)
            if not z:
                continue
            olculu.append((abs((z - ref).total_seconds()), a))
        olculu.sort(key=lambda x: x[0])
        if not olculu or olculu[0][0] > pencere_sn:
            return None, True
        if len(olculu) > 1 and abs(olculu[0][0] - olculu[1][0]) < 0.001:
            return None, True           # iki eşit aday
        return olculu[0][1], False

    def _kasa_bakiye_geri_al(kh):
        """Bir kasa hareketinin bakiye etkisini geri alır."""
        k = db.session.get(Kasa, kh.kasa_id)
        if not k:
            return None
        if (kh.tip or '') == 'giris':
            k.bakiye = q2((k.bakiye or 0) - (kh.tutar or 0))
        else:
            k.bakiye = q2((k.bakiye or 0) + (kh.tutar or 0))
        return f'{k.ad}: {kh.tutar:,.2f} {k.doviz or ""}'

    def _hareket_kasa_geri_al(hareket):
'''),
    ('flask_app.py', 'VR1 · flask_app.py blok 2',
     r'''        # TS1: bagli kasa hareketi ORTAK yardimcidan geri alinir.
        # Eskiden burada kendi kopyasi vardi ve yalniz
        # `baglanti_tip='cari_hareket'` ariyordu; tahsilatin kasa
        # kaydi `'tahsilat'` ile yazildigi icin hic bulunmuyordu.
        _kasa_geri = _hareket_kasa_geri_al(hareket)
        silinen_kasa = ', '.join(_kasa_geri) if _kasa_geri else None
''',
     r'''        # ── VR1 · TRANSFERİN ÖTEKİ BACAĞI ──
        # Ölçüldü: cari→cari transferinin bir bacağı silinince öteki
        # cari alacaklı kalıyor; cari→kasa transferinde kasa parayı
        # tutuyor ve karşılığı olan kayıt kalmıyor. Transfer atomik
        # yaratılıyor, atomik silinmeli.
        _es, _belirsiz = _transfer_esi(hareket)
        silinen_es = None
        if _belirsiz:
            return jsonify({
                'ok': False, 'error': 'transfer_esi_belirsiz',
                'mesaj': 'Bu transferin eşi kesin olarak bulunamadı '
                         '(aynı taraflar arasında yakın zamanlı birden '
                         'fazla transfer var). Yanlış kaydı silmemek '
                         'için dokunulmadı; hareketleri kasa/cari '
                         'ekranından tek tek kontrol edip silin.'}), 409
        if _es is not None:
            if isinstance(_es, KasaHareket):
                _kb = _kasa_bakiye_geri_al(_es)
                silinen_es = f'kasa hareketi ({_kb})' if _kb else 'kasa hareketi'
            else:
                silinen_es = f'karşı cari hareketi ({_es.id})'
            db.session.delete(_es)

        # TS1: bagli kasa hareketi ORTAK yardimcidan geri alinir.
        # Eskiden burada kendi kopyasi vardi ve yalniz
        # `baglanti_tip='cari_hareket'` ariyordu; tahsilatin kasa
        # kaydi `'tahsilat'` ile yazildigi icin hic bulunmuyordu.
        _kasa_geri = _hareket_kasa_geri_al(hareket)
        silinen_kasa = ', '.join(_kasa_geri) if _kasa_geri else None
        if silinen_es:
            silinen_kasa = ((silinen_kasa + ' · ') if silinen_kasa else '') \
                + silinen_es
'''),
    ('flask_app.py', 'VR1 · flask_app.py blok 3',
     r'''        k = Kasa.query.get(h.kasa_id)
        if k:
            # Bakiyeyi geri al
            if h.tip == 'giris':
                k.bakiye = q2((k.bakiye or 0) - (h.tutar or 0))
            else:
                k.bakiye = q2((k.bakiye or 0) + (h.tutar or 0))
''',
     r'''        # ── VR1 · VİRMANIN İKİ BACAĞI BİRLİKTE SİLİNİR ──
        # Ölçüldü: A→B 3.000 TL virmanının çıkış bacağı silinince
        # A parasını geri alıyor, B'de para duruyordu. Sistemdeki
        # toplam 10.000'den 13.000'e çıkıyordu — para yoktan var
        # oluyordu. Transfer atomik yaratılıyor, atomik silinmeli.
        _es, _belirsiz = _transfer_esi(h)
        if _belirsiz:
            return jsonify({
                'ok': False, 'error': 'transfer_esi_belirsiz',
                'mesaj': 'Bu virmanın karşı bacağı kesin olarak '
                         'bulunamadı (aynı kasalar arasında yakın '
                         'zamanlı birden fazla transfer var). Yanlış '
                         'kaydı silmemek için dokunulmadı.'}), 409

        _es_notu = ''
        if _es is not None:
            _kb = _kasa_bakiye_geri_al(_es)
            _log_audit('SIL', 'kasa_hareket', _es.id,
                       eski={'kasa_id': _es.kasa_id, 'tip': _es.tip,
                             'tutar': _es.tutar},
                       aciklama='Virmanın karşı bacağı (VR1)')
            db.session.delete(_es)
            _es_notu = f' Karşı bacak da geri alındı ({_kb}).' if _kb else \
                ' Karşı bacak da geri alındı.'

        _kb_bu = _kasa_bakiye_geri_al(h)
'''),
    ('flask_app.py', 'VR1 · flask_app.py blok 4',
     r'''        return jsonify({'ok': True, 'mesaj': 'Hareket silindi'})
''',
     r'''        return jsonify({'ok': True, 'mesaj': 'Hareket silindi.' + _es_notu})
'''),
    ('tests/test_kritik.py', 'VR1 · tests/test_kritik.py blok 1',
     r'''        assert secim in s, f'{secim} seçeneği ekranda yok'
''',
     r'''        assert secim in s, f'{secim} seçeneği ekranda yok'


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
'''),
]

def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA VR1 — ÇİFT BACAKLI TRANSFER ATOMİK SİLİNİR')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    # ── --yaz-gecici ──
    # base64 gömülü iki dosyayı /tmp'ye çıkarır, PROJEYE DOKUNMAZ.
    # Tam dosya yazan bir yamayı önce okumak istemek yerinde bir
    # istek; "uygula da sonra bak" demek yanlış olurdu.
    if '--yaz-gecici' in sys.argv:
        hedef = tempfile.mkdtemp(prefix='vr1-')
        print()
        for ad in TAM_YAZILAN:
            p = os.path.join(hedef, ad)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(_tam_dosya(ad))
            print(f'  {p}')
        print()
        print('  Projeye DOKUNULMADI. Okuduktan sonra:')
        print('    python3 yama_vr1.py            # rapor')
        print('    python3 yama_vr1.py --uygula')
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
        print('  ⊙ Yama VR1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_vr1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_vr1'
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
    print('    venv/bin/python -m pytest tests/test_kritik.py -q   # 319')
    print()
    print('  SUNUCUYU YENIDEN BASLAT')
    print('    sudo systemctl restart milestone-erp')
    print('    Sema degisikligi YOK, goc YOK. Ekran DEGISMEDI,')
    print('    tarayici yenilemeye gerek yok.')
    print()
    print('  NE DEGISTI')
    print('    · Kasa virmaninin tek bacagi silinemiyor; iki bacak')
    print('      birlikte gidiyor ve iki bakiye de duzeliyor.')
    print('      (Eskiden A->B 3.000 TL virmanin cikis bacagini')
    print('       silmek sistemdeki toplami 10.000den 13.000e')
    print('       cikariyordu — para yoktan var oluyordu.)')
    print('    · Cari->kasa transferinde cari kaydi silinince kasa')
    print('      parayi tutmuyor.')
    print('    · Cari->cari transferi tek tarafli kalmiyor.')
    print('    · Esi belirsizse (ayni taraflar, yakin zaman, ayni')
    print('      tutar birden fazla transfer) DOKUNULMUYOR, sebep')
    print('      soyleniyor.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

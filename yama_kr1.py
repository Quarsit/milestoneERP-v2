#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA KR1 — TARİH DEĞİŞİNCE KUR DA DEĞİŞİR
==========================================

ÖNKOŞUL: **yama_af1.py uygulanmış olmalı.** Betik denetliyor.

Senin kuralın şuydu:

    "düzenlemede tarih değişmiyor sadece rakam değişiyorsa kendi kuru
     kullanılsın, ama düzenlemede tarih değişiyorsa o güne ait kur
     verisi kullanılsın"

Kuralı almadan önce şunu söylemem gerek: ben sana BAŞKA bir şey
sormuştum ve sen bu kuralı verdiğinde iki ayrı konuyu konuşuyorduk.
İkisini de burada ayırıp hallediyorum.

═══ 1 · SENİN KURALIN — YARISI ÇALIŞIYORDU ═══

Düzenleme yolu TRY karşılığını hareketin KENDİ tarihinden çeviriyor:

      _try_karsilik(tutar, doviz, kur, hareket.hareket_tarihi)

Yani rakamı değiştirdiğinde kendi kuru kullanılıyor — kuralın ilk
kolu zaten yerindeydi. İkinci kolu DEĞİLDİ.

Çünkü "bir şey değişti mi" kapısı yalnız RAKAMA ve DÖVİZE bakıyordu.
Tarih o kapıda hiç sayılmıyordu, dolayısıyla tarihi değiştirince
TRY karşılığı HİÇ yeniden hesaplanmıyordu.

ÖLÇÜLDÜ — 1.000 USD, 11.03 (kur 30), TRY karşılığı 30.000:

      senaryo                       tarih     tutar      TRY   kur
      ────────────────────────────────────────────────────────────
      yalnız tutar 1.000→2.000      11.03     2.000   60.000    30   ✓
      tutar + tarih (→11.09)        11.09     2.000  100.000    50   ✓
      YALNIZ tarih   (→11.09)       11.09     1.000   30.000    30   ✗

Üçüncü satır: kayıt 11.09 tarihli görünüyor ama 11.03 kuruyla
duruyor. Ekstre TRY üzerinden topladığı için bakiye 20.000 TL
eksik, çekmece ham dövizi topladığı için doğru. Yine aynı aile:
İKİ EKRAN BİRBİRİNİ TUTMUYOR.

Artık tarih de o kapıdan sayılıyor ve üç satır da kuralına uyuyor.

  ELLE GİRDİĞİN KUR KORUNUYOR. Kuru sen yazmışsan (`kur_kaynak =
  MANUEL`) tarih değişti diye üstüne TCMB kuru yazılmıyor — kendi
  kararını sessizce silmek olurdu. Fatura düzenleme yolu da aynı
  ayrımı yapıyor, oradan aldım. Ölçüldü: elle 33 yazılmış bir kayıt
  tarih değişince 33'te kalıyor.

  ONAY EKRANI ARTIK TARİHİ DE SORUYOR. Döviz hareketinde tarihi
  değiştirmek TRY karşılığını, kasa tutarını ve kur farkı kaydını
  birlikte oynatıyor — bunlar DZ6'dan beri önce sorulup sonra
  yapılıyor. Yalnız evrak no, vade ya da açıklama değiştirirsen
  soru hiç çıkmıyor, eskisi gibi.

═══ 2 · BAŞLIK HİÇBİR ŞEY SÖYLEMİYORDU ═══

Onay ekranının ilk satırı SABİT yazılmıştı: "Tutar X → Y olacak".
Tarih yüzünden geçildiğinde sana şunu diyecekti:

      Tutar 1.000,00 → 1.000,00 USD olacak.

Yanlış bir cümle değil. Hiçbir şey söylemeyen bir cümle: değişen
tarihti, ekran onu yazmıyordu. Artık ne değiştiyse onu yazıyor:

      Tarih 2026-03-11 → 2026-09-11, kuru 50,0000 olacak.

Denetim kaydı da temizlendi: tarih yüzünden geçildiğinde "borç
1.000 → 1.000" satırı yazılmıyor artık.

═══ 3 · BENİM SORDUĞUM ŞEY — VE ABARTTIĞIM YER ═══

AF1'in sonunda sana şöyle yazmıştım:

      "Çapraz dövizli bir ödemede, ödeme gününe ait kur YOKSA
       çevrim sıfır dönüyor ve ödeme HİÇ sayılmıyor."

**Bu cümle olduğundan geniş.** Ölçtüm: `_kur_getir` o tarihten
GERİYE bakıyor, yani bir ara güne kur girilmemişse zaten en son
girilen günün kurunu buluyor. Senin 08.07'de kuru olmayan bir
ödemen varsa sorun çıkmıyor — ölçtüm, 9.500,00 doğru çıkıyor.

Doğru cümle şu: ödeme, kur arşivinin İLK GÜNÜNDEN ÖNCE tarihliyse
geriye bakacak hiçbir kayıt bulamıyor ve 0 dönüyor. Arşiv 1 Ocak
2026'da başlıyor; yani 2025 ve öncesi tarihli, faturadan FARKLI
dövizde bir ödeme.

ÖLÇÜLDÜ — 10.000 GBP fatura, 20.000 TRY tahsilat (arşiv öncesi):

      önce   ödenen 0,00     → kalan 10.000,00   (para hiç sayılmadı)
      sonra  ödenen 500,00   → kalan  9.500,00 ✓

Dar bir durum ama senin geçmişe kayıt girdiğini biliyorum, o yüzden
kapattım. Nasıl kapattığım da yeni bir karar değil: yazma yolu bu
soruyu E1a'da çözmüş — gün kuru yoksa EN YAKIN gün. Okuma yolu o
merdiveni devralmamıştı. Üçüncü bir politika uydurmak yerine
aynısını kullandım. Senin "kendi kuru kullanılsın" dediğin şey de
burada zaten elimizde: hareketin `kur_uygulanan` değeri kayıtta
duruyor ve ham tutar yoksa ondan çevriliyor.

Arşivde o döviz için HİÇ kayıt yoksa (kurulum anı) ham tutar
sayılıyor ve log'a uyarı yazılıyor — E1a da aynı yerde tutarı
koruyup uyarıyor. Sıfır yazmak ödemeyi yok eder; dövizi karıştırmak
en azından fark edilir.

═══ 4 · KENDİ TESTİMDE TANIMSIZ AD ═══

AF1'de yazdığım testin hata mesajında `_kur` diye bir ad vardı ve
o ad hiçbir yerde tanımlı değildi. Assert geçtiği için hiç
çalışmadı, takım yeşil kaldı. Ama GERÇEKTEN başarısız olduğu gün
NameError ile patlayıp asıl sayıları gizleyecekti — yani hatayı
gösterecek satır, hatayı saklayacaktı. Düzeltildi.

═══ DOĞRULANDI ═══
  253 test geçti (248 + 5). Beşinin dördü DAVRANIŞ bakıyor: gerçek
  uçtan tarihi değiştirip yazılan kuru okuyor, elle girilmiş kuru
  koruyup korumadığına bakıyor, arşiv öncesi ödemeyi sayıyor.
  Biri de onay ekranının ne yazdığına bakıyor.

  Kuralın üç kolu ayrı ayrı test altında: tarih değişti → yeni gün ·
  tarih aynı → kendi kuru · elle kur → dokunulmaz.

DOSYALAR
--------
  flask_app.py           tarih kapısı · başlık · okuma merdiveni
  templates/cari.html    onay sorusunun yorumu (artık tarihi de kapsıyor)
  tests/test_kritik.py   5 yeni test + tanımsız ad

Şema yok, göç yok.

KULLANIM
--------
  python3 yama_kr1.py            # RAPOR
  python3 yama_kr1.py --uygula
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
    'flask_app.py': "KR1 · TARİH DE TUTARI DEĞİŞTİRİR",
    'templates/cari.html': 'KR1: DOVIZ hareketinde TARIH de ayni soruyu',
    'tests/test_kritik.py': 'def test_kr1_tarih_degisince_yeni_gunun_kuru_yazilir',
}
ONKOSUL = {
    'flask_app.py': "AF1 · KİMLİK FLUSH'TAN SONRA OKUNUR",
    'tests/test_kritik.py': 'def test_af1_alis_faturasinda_capraz_doviz_odeme',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'KR1 · flask_app.py blok 1',
     r'''        if set(TUTAR_ALANLARI) & set(data):
''',
     r'''        # KR1: TARİH de buraya sokuyor. Ekran tutarı her zaman
        # gönderdiği için bu kapı pratikte hep açıktı; ama uç nokta
        # dışarıdan `{"hareket_tarihi": ...}` tek başına da
        # alabiliyor ve o yol kuru hiç yenilemiyordu. Rakamı sıfır
        # olan bir kayıtta açılmıyor: orada çevrilecek tutar yok.
        _tarih_geldi = ('hareket_tarihi' in data
                        and q2((hareket.borc or 0)
                               + (hareket.alacak or 0)) > 0)
        if (set(TUTAR_ALANLARI) & set(data)) or _tarih_geldi:
'''),
    ('flask_app.py', 'KR1 · flask_app.py blok 2',
     r'''            _degisti = (_yeni_tutar != _eski_tutar
                        or _yeni_doviz != (hareket.doviz or 'TRY')
                        or (_yeni_kur is not None
                            and q_kur(_yeni_kur)
                            != q_kur(hareket.kur_uygulanan or 0)))
''',
     r'''            # ══════════════════════════════════════════════════════
            #  KR1 · TARİH DE TUTARI DEĞİŞTİRİR
            #
            #  Bir döviz hareketinin TRY karşılığı O GÜNÜN kuruyla
            #  yazılır. Tarih değişirse kur da değişir. Ama bu koşul
            #  yalnız RAKAMA ve DÖVİZE bakıyordu; dolayısıyla
            #  "yalnızca tarihi düzelt" işlemi kaydı YENİ TARİHLE
            #  ESKİ KURDA bırakıyordu.
            #
            #  ÖLÇÜLDÜ — 1.000 USD · 10.03 (kur 30) · TRY 30.000,
            #  tarih 10.09'a (kur 50) çekiliyor:
            #
            #    yalnız tutar 1.000→2.000   TRY  60.000  kur 30  ✓
            #    tutar + tarih              TRY 100.000  kur 50  ✓
            #    YALNIZ tarih               TRY  30.000  kur 30  ✗
            #
            #  Üçüncü satırda kayıt 10.09 tarihli görünüyor ama
            #  10.03 kuruyla duruyor. Ekstre TRY üzerinden topladığı
            #  için bakiye 20.000 TL eksik, çekmece ham dövizi
            #  topladığı için doğru — iki ekran yine birbirini
            #  tutmuyor. Aynı aileden bir hata daha.
            #
            #  ELLE GİRİLEN KUR KORUNUYOR. `kur_kaynak='MANUEL'` ise
            #  kuru kullanıcı kendi yazmıştır; tarih değişti diye
            #  onun üstüne TCMB kuru yazmak kendi kararını sessizce
            #  silmek olurdu. Fatura düzenleme yolu da aynı ayrımı
            #  yapıyor.
            # ══════════════════════════════════════════════════════
            _yeni_tarih = (_parse_date(data['hareket_tarihi'])
                           if data.get('hareket_tarihi') else None)
            _tarih_degisti = bool(
                _yeni_tarih
                and _yeni_tarih != hareket.hareket_tarihi
                and (_yeni_doviz or 'TRY') != 'TRY'
                and (hareket.kur_kaynak or 'TCMB') != 'MANUEL')

            _tutar_degisti = (_yeni_tutar != _eski_tutar
                              or _yeni_doviz != (hareket.doviz or 'TRY')
                              or (_yeni_kur is not None
                                  and q_kur(_yeni_kur)
                                  != q_kur(hareket.kur_uygulanan or 0)))
            _degisti = _tutar_degisti or _tarih_degisti
'''),
    ('flask_app.py', 'KR1 · flask_app.py blok 3',
     r'''                         'eski_tutar': _eski_tutar, 'maliyet': _maliyet}
''',
     r'''                         'eski_tutar': _eski_tutar, 'maliyet': _maliyet,
                         'tutar_degisti': _tutar_degisti}
'''),
    ('flask_app.py', 'KR1 · flask_app.py blok 4',
     r'''            _eski[_plan['yan']] = str(_plan['eski_tutar'])
''',
     r'''            # KR1: buraya TARİH yüzünden girdiysek rakam değişmedi;
            # denetim kaydına "1.000 → 1.000" yazmak yanıltıcı olur.
            if _plan['tutar_degisti']:
                _eski[_plan['yan']] = str(_plan['eski_tutar'])
'''),
    ('flask_app.py', 'KR1 · flask_app.py blok 5',
     r'''        # ── ONAY KAPISI ──
''',
     r'''        # KR1 · BAŞLIK NE DEĞİŞTİYSE ONU SÖYLÜYOR.
        # Bu satır "Tutar X → Y" diye SABİT yazıyordu. Tarih yüzünden
        # geçildiğinde kullanıcıya "Tutar 1.000,00 → 1.000,00 USD
        # olacak" diyordu — doğru olmayan bir cümle değil, HİÇBİR ŞEY
        # söylemeyen bir cümle: değişen tarihti, onay ekranı bunu
        # yazmıyordu.
        _baslik = ''
        if _plan:
            if _plan['tutar_degisti']:
                _baslik = (f'Tutar {_plan["eski_tutar"]:,.2f} → '
                           f'{_plan["tutar"]:,.2f} {_plan["doviz"]}')
            else:
                _baslik = (f'Tarih {_eski.get("hareket_tarihi", "?")} → '
                           f'{hareket.hareket_tarihi}, kuru '
                           f'{float(_kur_kul):,.4f}')

        # ── ONAY KAPISI ──
'''),
    ('flask_app.py', 'KR1 · flask_app.py blok 6',
     r'''                           'eski_tutar': _plan['eski_tutar'],
                           'yeni_tutar': _plan['tutar'],
                           'doviz': _plan['doviz']},
                'mesaj': f'Tutar {_plan["eski_tutar"]:,.2f} → '
                         f'{_plan["tutar"]:,.2f} {_plan["doviz"]} olacak. '
''',
     r'''                           'baslik': _baslik,
                           'tutar_degisti': _plan['tutar_degisti'],
                           'eski_tutar': _plan['eski_tutar'],
                           'yeni_tutar': _plan['tutar'],
                           'doviz': _plan['doviz']},
                'mesaj': f'{_baslik} olacak. '
'''),
    ('flask_app.py', 'KR1 · flask_app.py blok 7',
     r'''            _mesaj = (f'Tutar {_plan["eski_tutar"]:,.2f} → '
                      f'{_plan["tutar"]:,.2f} {_plan["doviz"]} olarak '
                      f'düzeltildi')
''',
     r'''            _mesaj = f'{_baslik} olarak düzeltildi'
'''),
    ('flask_app.py', 'KR1 · flask_app.py blok 8',
     r'''        k = 1.0 if f_doviz == 'TRY' else _kur_getir(f_doviz, h.hareket_tarihi)
        if not k or k <= 0:
            return 0.0
        tutar_try = float(getattr(h, alan + '_try') or 0)
        if tutar_try <= 0:
            tutar_try = tutar * float(h.kur_uygulanan or _kur_getir(h.doviz, h.hareket_tarihi) or 0)
''',
     r'''        # ══════════════════════════════════════════════════════
        #  KR1 · KUR YOKSA SIFIR YAZMA — E1a'nın AYNI merdiveni.
        #
        #  Burada `_kur_getir` tek başına duruyordu: ödeme gününe ait
        #  kur kaydı yoksa 0 dönüyor ve ödeme HİÇ sayılmıyordu —
        #  fatura tam açık görünüyordu, para ödenmiş olduğu hâlde.
        #  Eskisi ham toplayıp FAZLA sayıyordu. İkisi de yanlış, ters
        #  yönlerde.
        #
        #  Yazma yolu bu soruyu E1a'da zaten çözmüş: gün kuru yoksa
        #  EN YAKIN gün. Okuma yolu o merdiveni devralmamıştı.
        #  Üçüncü bir politika uydurmak yerine aynısı kullanılıyor.
        # ══════════════════════════════════════════════════════
        k = 1.0 if f_doviz == 'TRY' else _kur_getir(f_doviz, h.hareket_tarihi)
        if not k or k <= 0:
            k = _en_yakin_kur(f_doviz, h.hareket_tarihi) or 0
        if not k or k <= 0:
            # Arşivde o döviz için HİÇ kayıt yok (kurulum anı).
            # Ham tutarı saymak dövizleri karıştırır ama ödemeyi yok
            # etmez; sıfır yazmak sessizce yok eder. E1a da aynı
            # yerde 1.0 ile dönüp uyarıyor.
            app.logger.warning(
                f'{f_doviz} kuru arşivde hiç yok — {h.id} ödemesi ham '
                f'tutarıyla sayılıyor')
            return tutar
        tutar_try = float(getattr(h, alan + '_try') or 0)
        if tutar_try <= 0:
            # Hareketin KENDİ kuru kayıtta duruyor; yazıldığı anda
            # kullanılan kur odur, en sadık karşılık o.
            tutar_try = tutar * float(
                h.kur_uygulanan
                or _kur_getir(h.doviz, h.hareket_tarihi)
                or _en_yakin_kur(h.doviz, h.hareket_tarihi) or 0)
'''),
    ('templates/cari.html', 'KR1 · templates/cari.html blok 1',
     r'''         gosterip ikinci kez soruyoruz. Yalnizca tarih ya da
         aciklama degistiyse bu soru HIC cikmiyor. */
''',
     r'''         gosterip ikinci kez soruyoruz.

         KR1: DOVIZ hareketinde TARIH de ayni soruyu cikariyor —
         gun degisince TRY karsiligi, kasa tutari ve kur farki da
         degisiyor. Yalnizca evrak no, vade ya da aciklama
         degistiyse soru HIC cikmiyor. */
'''),
    ('tests/test_kritik.py', 'KR1 · tests/test_kritik.py blok 1',
     r'''    assert abs(kayit[0]['kalan'] - _beklenen) < 0.02, \
        f"kalan {kayit[0]['kalan']}, kur {_kur} ile beklenen {_beklenen}"
''',
     r'''    # KR1: burada `_kur` diye TANIMSIZ bir ad vardi. Assert gecerken
    # hic calismadigi icin takim yesil kaliyordu; GERCEKTEN basarisiz
    # olsaydi NameError ile patlayip asil sayilari gizleyecekti.
    assert abs(kayit[0]['kalan'] - _beklenen) < 0.02, \
        f"kalan {kayit[0]['kalan']}, beklenen {_beklenen} (kur 40)"
'''),
    ('tests/test_kritik.py', 'KR1 · tests/test_kritik.py blok 2',
     r'''        assert Maliyet.query.filter_by(baglanti_id=pid).count() == 1
''',
     r'''        assert Maliyet.query.filter_by(baglanti_id=pid).count() == 1


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
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA KR1 — TARİH DEĞİŞİNCE KUR DA DEĞİŞİR')
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
        print('    python3 yama_kr1.py            # rapor')
        print('    python3 yama_kr1.py --uygula')
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
        print('  ⊙ Yama KR1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_kr1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_kr1'
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
    print('    2) venv/bin/python -m pytest tests/test_kritik.py -q   # 253')
    print()
    print('  BAKILACAK YER')
    print('    1. Cari -> hareket satirinda Duzenle: bir DOVIZ')
    print('       hareketinin yalniz TARIHINI degistir. Onay ekrani')
    print('       artik "Tarih ... -> ..., kuru ..." diye soruyor ve')
    print('       kaydin TRY karsiligi yeni gunun kuruyla yaziliyor.')
    print('    2. Ayni kaydin yalniz RAKAMINI degistir: kuru')
    print('       degismiyor, kendi tarihinin kuru kullaniliyor.')
    print('    3. Kuru ELLE yazilmis bir kayitta tarihi degistir:')
    print('       senin yazdigin kur korunuyor.')
    print()
    print('  RAKAMLARIN DEGISEBILIR')
    print('    Tarihi sonradan duzelttigin DOVIZ hareketlerinin TRY')
    print('    karsiligi bundan sonra dogru yazilacak. GECMISTE')
    print('    boyle duzeltilmis kayitlar kendiliginden duzelmez —')
    print('    onlari tekrar kaydetmen gerekir. Hangi kayitlarin')
    print('    oyle oldugunu bilmiyorum; bir tarama istersen yazarim.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

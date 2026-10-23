#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA VT1 — BELGE TARİHİ / VADE TARİHİ
======================================

ÖNKOŞUL: yama_dz6.py uygulanmış olmalı.
         (Sıra: DZ5 → DZ6 → VT1.)

"Bu iki kontrole her yerde ihtiyaç var mı, bazı yerlerde adını da
değiştirmek uygun olur sanki" dedin. Gözden geçirdim.

── ÖNCE BİR DÜZELTME ──
  Sana rapor ettiğim "%25'lik kur hatası" CANLI DEĞİLDİ. Ölçtüğüm
  yol, "Tahsilat Gir" panelinin yoluydu — ve o panel ÖLÜ KOD:
  `tahModal`ı açan hiçbir şey yok. BF1 ile iki form birleştirilmiş,
  "Tahsilat / Ödeme" düğmesi o günden beri tam donanımlı hareket
  formunu açıyor.

  Aynı şey sabit `doviz: 'USD'` için de geçerliydi; sen ekrana
  bakıp döviz seçicinin orada olduğunu söyledin, haklıydın.

  Ölçtüğüm şeyin canlı olup olmadığını kontrol etmeden rapor
  ettim. Yamanın yaptığı ilk iş o ölü paneli SİLMEK — çünkü duran
  ölü bir form zararsız değil: içinde iki gerçek hata vardı ve ben
  onları canlı sandım.

── ENVANTER ──
  `belge_tarihi` diye bir kolon YOK; o sadece ekrandaki etiket,
  altındaki alan `hareket_tarihi`. `vade_tarihi` üç kayıtta var:

    Çek          → vade kaydın ÖZÜ (nullable=False). Dokunulmadı.
    Fatura       → vade GEREKLİ: yaşlandırma, gecikme, açık fatura
                   listesi. Cari kartındaki "Ödeme Vadesi (gün)"den
                   otomatik de hesaplanıyor. Dokunulmadı.
    Cari hareket → çoğu tipte ANLAMSIZ. Asıl iş burada.

── 1 · VADE YALNIZ BORÇ DOĞURAN TİPLERDE ──
  Vade HER harekette zorunluydu (göndermezsen 400), belge tarihi
  ise opsiyoneldi. Tam tersiydi: kuru belirleyen belge tarihi.

  Artık:
    zorunlu   → Fatura (Satış/Alış)
    istenirse → Açılış Bakiyesi, İade
    yazılmaz  → Tahsilat, Ödeme, Avans, Virman, Mahsup, Kur Farkı

  Son grupta vade GELSE BİLE yazılmıyor — ama sessizce yutulmuyor,
  yanıt bunu söylüyor: "Vade tarihi yazılmadı — Tahsilat bir borç
  doğurmuyor, vadesi de olmaz."

  Ekran da aynı kuralı izliyor: alan o tiplerde hiç görünmüyor ve
  tarih satırı tek sütuna düşüyor.

── 2 · TAHSİL EDİLMİŞ PARA "YAKLAŞAN ÖDEMELER"DE DURUYORDU ──
  Form vadeyi BUGÜNLE dolduruyordu; sorgu da yalnız borç/alacak
  işaretine ve vadeye bakıyordu, işlem tipine bakmıyordu.

  ÖLÇÜLDÜ — bugün tahsil edilmiş, kasaya girmiş iki para:

      YAKLASAN ODEMELER (odeyecegimiz): 2 kayit
        · 22.10.2026  ALICI AS  1000.0 USD — Tahsilat
        · 22.10.2026  ALICI AS  5000.0 TRY — Tahsilat

  İki koruma kondu: vade artık o tiplere yazılmıyor (yeni kayıt),
  ve sorgu işlem tipine de bakıyor (ESKİ kayıtlar). Sorgu tek bir
  fonksiyona alındı — aynı sorgu iki ayrı yerde kopyalanmıştı.

── 3 · ÜÇÜNCÜ DÖVİZLİ KASADA KUR VADEDEN ALINIYORDU ──
  Hareketin kendi TL karşılığı BELGE tarihinden, bağlı kasa
  hareketi ise VADE tarihinden çevriliyordu. TL kasada görünmüyor;
  kasa üçüncü bir dövizdeyse ortaya çıkıyor.

  ÖLÇÜLDÜ — 1.000 USD tahsilat, EUR kasaya:
      doğru : 40.000 / 44 = 909,09 EUR
      olan  : 40.000 / 55 = 727,27 EUR      (%20 fark)

  Virman ve mahsup dallarında da aynı hata vardı. Üçü de belge
  tarihine çevrildi. Bunun için belge tarihinin okunduğu yer
  yukarı taşındı — o dallar ondan ÖNCE çalışıyordu.

── 4 · VADESİZ FATURA HİÇ YAŞLANMIYORDU ──
  Hesap `if f.vade_tarihi and f.vade_tarihi < bugun` idi; vade
  boşsa koşul hiç çalışmıyor, gecikme SIFIR dönüyordu.

  ÖLÇÜLDÜ — 120 gün önce kesilmiş iki fatura:
      vadesi tanımlı → GECİKME = 90 gün   ✓
      vadesi boş     → GECİKME =  0 gün   ✗

  Vadesiz fatura açık listede kalıyor ama asla "gecikmiş"
  görünmüyor ve listenin en altına sıralanıyordu — yani tahsilat
  takibinden sessizce düşüyordu.

  Artık vade yoksa gecikme FATURA TARİHİNDEN sayılıyor. Bu bir
  VARSAYIM olduğu için yanıt `vadesiz: true` ile birlikte dönüyor;
  sıfır göstermektense varsayımı açıkça söylemek yeğlenir.
  Sıralama da artık fatura tarihini kullanıyor.

  DİKKAT: bu yamadan sonra vadesiz eski faturalarının bir kısmı
  BİRDEN gecikmiş görünecek. Hangileri olduğunu önceden görmek
  için `denetim_vade.py` ayrıca geliyor.

── 5 · İSİMLENDİRME ──
  Canlı formda alan zaten "Belge Tarihi · kur bu tarihten" diyor,
  doğru olan o. Silinen ölü panelde "Tarih" yazıyordu.

  Vade ipucu "· ödeme/tahsilat" idi — yanıltıcıydı; vade bir
  BORCUN ne zaman ödeneceğidir. "· borç ne zaman ödenecek" oldu.

── 6 · İKİ DÜĞME, TEK PANEL ──
  "Hareket ekle" ve "Tahsilat / Ödeme" aynı formu açıyordu. İkincisi
  kaldırıldı; tek farkı olan "işlem tipini hazır seç" davranışı
  `hareketAc`a taşındı — tedarikçiye Ödeme, müşteriden Tahsilat.

── ÖLÇÜLDÜ (yamadan sonra) ──
      vadesiz Tahsilat          : 200, vade_tarihi NULL        ✓
      vade gönderilen Tahsilat  : NULL + yanıtta söyleniyor    ✓
      vadesiz Fatura (Satış)    : 400, hâlâ zorunlu            ✓
      yaklaşan ödemeler         : 0 kayıt (önce 2)             ✓
      EUR kasa, USD tahsilat    : 909,09 EUR                   ✓
      vadesiz fatura, 120 gün   : GECİKME 120 gün, vadesiz:true ✓
      vadeli fatura             : GECİKME 90 gün               ✓

  Tarayıcıda baktım: Tahsilat'ta vade alanı yok ve belge tarihi
  tam genişlik; Fatura'da ikisi yan yana ve ipucu doğru. Çekmecede
  tek düğme kaldı. JS hatası yok.

  211 test geçti (205 + 6); iki ayrı koşuda da aynı.
  firma · js · form · zincir · akis denetimleri temiz.
  Tabanı DZ6'yı uygulayarak ürettim.

── AYRICA GELEN ──
  denetim_vade.py — SALT OKUNUR rapor:
    · nakit hareketinde duran anlamsız vadeler
    · vadesiz açık faturalar (yamadan sonra kaç gün gecikmiş
      görünecekler)
    · ödeme vadesi tanımsız cariler
  `--temizle` ile yalnız (1)'deki vade alanlarını boşaltır; tutara,
  kasaya, bakiyeye DOKUNMAZ ve önce JSON yedek yazar.

── SIRA ──
      DZ1…DZ4                                ✓
      DZ5  cari hareketin tutarı             ✓
      DZ6  eşleşme ve onay                   ✓
      VT1  belge tarihi / vade tarihi        ← bu yama

DOSYALAR
--------
  flask_app.py          vade tipe bağlandı · kur belge tarihinden ·
                        yaklaşan listeleri · vadesiz fatura yaşlanması
  templates/cari.html   ölü panel silindi · vade tipe göre görünür ·
                        ipuçları · tek düğme
  tests/test_kritik.py  6 yeni test

Şema yok, göç yok, yeni alan yok.

KULLANIM
--------
  python3 yama_vt1.py            # RAPOR
  python3 yama_vt1.py --uygula
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
    'flask_app.py': 'VT1 · VADE YALNIZ BORÇ DOĞURAN TİPLERDE',
    'templates/cari.html': 'VADE_ANLAMLI_TIPLER',
    'tests/test_kritik.py': 'def test_vt1_tahsilatta_vade_zorunlu_degil_ve_yazilmiyor',
}
ONKOSUL = {
    'flask_app.py': 'DZ6 · ÖNCE YAP, ONAY YOKSA GERİ AL',
    'templates/cari.html': 'function hareketDuzenleAc(',
    'tests/test_kritik.py': 'def test_dz6_vazgecince_hicbir_sey_kalmiyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'VT1 · flask_app.py blok 1',
     r'''        return q2(tutar_try / k_kur), None
''',
     r'''        return q2(tutar_try / k_kur), None

    # ══════════════════════════════════════════════════════════════
    #  VT1 · NAKİT HAREKETLERİ "YAKLAŞAN" LİSTELERİNE GİRMEZ
    #
    #  Bu tiplerde para ZATEN el değiştirmiş; bekleyen bir ödeme ya
    #  da tahsilat yok. Vade alanı artık bunlara yazılmıyor, ama
    #  ESKİ kayıtlarda vade duruyor — bu süzgeç onlar için.
    #
    #  ÖLÇÜLDÜ: bugün tahsil edilmiş, kasaya girmiş 1.000 USD ve
    #  5.000 TRY "yaklaşan ödemeler" listesinde duruyordu, yani
    #  önümüzdeki 30 günde ÖDEYECEĞİMİZ paralar arasında. Sorgu
    #  yalnız borç/alacak işaretine ve vadeye bakıyordu.
    # ══════════════════════════════════════════════════════════════
    NAKIT_TIPLERI = ('Tahsilat', 'Odeme', 'Ödeme',
                     'Avans Tahsilati', 'Avans Tahsilatı',
                     'Avans Odemesi', 'Avans Ödemesi',
                     'Kur Farki (Borc)', 'Kur Farki (Alacak)',
                     'Bakiye Transfer', 'Mahsup')

    def _yaklasan_hareketler(bas, bitis, yon):
        """Vadesi [bas, bitis] araliginda BEKLEYEN hareketler.

        `yon`: 'odeme'    → bizim odeyeceklerimiz (alacak > 0)
               'tahsilat' → bizim tahsil edeceklerimiz (borc > 0)

        Tek kural, iki cagiran. Iki ayri kopya olsaydi biri
        duzeltilip digeri unutulurdu.
        """
        q = CariHareket.query.filter(
            CariHareket.vade_tarihi >= bas,
            CariHareket.vade_tarihi <= bitis,
            # islem_tip BOS olan eski kayitlar DISARIDA BIRAKILMAZ:
            # ne oldugunu bilmedigimiz bir kaydi gizlemektense
            # gostermek yeglenir. (SQL'de NULL NOT IN (...) → NULL,
            # yani acik yazilmazsa sessizce elenirlerdi.)
            db.or_(CariHareket.islem_tip.is_(None),
                   CariHareket.islem_tip.notin_(NAKIT_TIPLERI)))
        q = (q.filter(CariHareket.alacak > 0) if yon == 'odeme'
             else q.filter(CariHareket.borc > 0))
        return q.order_by(CariHareket.vade_tarihi).all()
'''),
    ('flask_app.py', 'VT1 · flask_app.py blok 2',
     r'''        odemeler = CariHareket.query.filter(
            CariHareket.vade_tarihi >= bugun,
            CariHareket.vade_tarihi <= otuz_gun_sonra,
            CariHareket.alacak > 0
        ).order_by(CariHareket.vade_tarihi).all()
''',
     r'''        # VT1: nakit hareketleri bu listeye girmiyor
        odemeler = _yaklasan_hareketler(bugun, otuz_gun_sonra, 'odeme')
'''),
    ('flask_app.py', 'VT1 · flask_app.py blok 3',
     r'''        tahsilatlar = CariHareket.query.filter(
            CariHareket.vade_tarihi >= bugun,
            CariHareket.vade_tarihi <= otuz_gun_sonra,
            CariHareket.borc > 0
        ).order_by(CariHareket.vade_tarihi).all()
''',
     r'''        tahsilatlar = _yaklasan_hareketler(bugun, otuz_gun_sonra, 'tahsilat')
'''),
    ('flask_app.py', 'VT1 · flask_app.py blok 4',
     r'''    def _acik_fatura_dict(f, bugun):
        odenen = _fatura_odenen_esdeger(f)
        kalan = q2((f.toplam or 0) - odenen)
        gecikme = ((bugun - f.vade_tarihi).days
                   if f.vade_tarihi and f.vade_tarihi < bugun else 0)
        return {'id': f.id, 'fatura_no': f.fatura_no or f.id,
                'fatura_tarihi': f.fatura_tarihi.isoformat() if f.fatura_tarihi else None,
                'vade_tarihi': f.vade_tarihi.isoformat() if f.vade_tarihi else None,
                'toplam': q2(f.toplam or 0), 'odenen': odenen, 'kalan': kalan,
                'doviz': (f.doviz or 'USD').upper(), 'durum': f.durum,
                'gecikme_gun': gecikme}

    def _vade_sirasi(x):
        return (x.get('vade_tarihi') or '9999-12-31', x.get('fatura_tarihi') or '')
''',
     r'''    def _fatura_gecikme(f, bugun):
        """Faturanın gecikme günü, ve vadesinin varsayılıp
        varsayılmadığı.

        ── VT1 · VADESİZ FATURA HİÇ YAŞLANMIYORDU ──
        Hesap `if f.vade_tarihi and f.vade_tarihi < bugun` idi; vade
        boşsa koşul hiç çalışmıyor ve gecikme SIFIR dönüyordu.

        ÖLÇÜLDÜ — 120 gün önce kesilmiş iki fatura:
            vadesi tanımlı → GECİKME = 90 gün   ✓
            vadesi boş     → GECİKME =  0 gün   ✗
        Vadesiz fatura açık listede kalıyor ama asla "gecikmiş"
        görünmüyor, listenin en altına sıralanıyor — yani tahsilat
        takibinden sessizce düşüyor.

        Vade yoksa gecikme FATURA TARİHİNDEN sayılıyor. Bu bir
        VARSAYIM, o yüzden `vadesiz` ile birlikte dönüyor ve ekranda
        da öyle işaretleniyor: sıfır göstermektense varsayımı açıkça
        söylemek yeğlenir.

        Döner: (gecikme_gun, vadesiz_mi)
        """
        vadesiz = f.vade_tarihi is None
        _baz = f.vade_tarihi or f.fatura_tarihi
        if not _baz or _baz >= bugun:
            return 0, vadesiz
        return (bugun - _baz).days, vadesiz

    def _acik_fatura_dict(f, bugun):
        odenen = _fatura_odenen_esdeger(f)
        kalan = q2((f.toplam or 0) - odenen)
        gecikme, vadesiz = _fatura_gecikme(f, bugun)
        return {'id': f.id, 'fatura_no': f.fatura_no or f.id,
                'fatura_tarihi': f.fatura_tarihi.isoformat() if f.fatura_tarihi else None,
                'vade_tarihi': f.vade_tarihi.isoformat() if f.vade_tarihi else None,
                'toplam': q2(f.toplam or 0), 'odenen': odenen, 'kalan': kalan,
                'doviz': (f.doviz or 'USD').upper(), 'durum': f.durum,
                'gecikme_gun': gecikme, 'vadesiz': vadesiz}

    def _vade_sirasi(x):
        # VT1: vadesiz fatura artik en sona atilmiyor — FATURA
        # TARIHINDEN siralaniyor. '9999-12-31' yazmak, 120 gun once
        # kesilmis bir faturayi listenin dibine gomuyordu.
        return (x.get('vade_tarihi') or x.get('fatura_tarihi')
                or '9999-12-31', x.get('fatura_tarihi') or '')
'''),
    ('flask_app.py', 'VT1 · flask_app.py blok 5',
     r'''        if not data.get('cari_id') or not data.get('islem_tip') or not data.get('vade_tarihi'):
            return jsonify({'ok': False, 'mesaj': 'Cari, işlem tipi ve vade tarihi zorunlu'}), 400

        islem_tip = data['islem_tip']
        borc = q2(float(data.get('borc') or 0))
        alacak = q2(float(data.get('alacak') or 0))
        doviz = data.get('doviz', 'USD')
        siparis_id = data.get('siparis_id') or None
        stok_id = (data.get('stok_id') or '').strip() or None  # YENİ: stok bağlantısı
        vade = _parse_date(data['vade_tarihi'])
''',
     r'''        if not data.get('cari_id') or not data.get('islem_tip'):
            return jsonify({'ok': False,
                            'mesaj': 'Cari ve işlem tipi zorunlu'}), 400

        islem_tip = data['islem_tip']

        # ══════════════════════════════════════════════════════════
        #  VT1 · VADE YALNIZ BORÇ DOĞURAN TİPLERDE
        #
        #  Eskiden vade HER hareket için zorunluydu, belge tarihi ise
        #  opsiyoneldi. Tam tersiydi: kuru belirleyen belge tarihi;
        #  vade bir TAHSİLATTA anlamsız — para zaten el değiştirmiş.
        #
        #  ÖLÇÜLDÜ: form vadeyi bugünle dolduruyordu, bu yüzden bugün
        #  TAHSİL EDİLMİŞ ve kasaya girmiş paralar "yaklaşan ödemeler"
        #  listesinde duruyordu — yani önümüzdeki 30 günde ÖDEYECEĞİMİZ
        #  paralar arasında. İki kayıt, 1.000 USD ve 5.000 TRY.
        #
        #  Artık vade yalnız bir BORCUN vadesi olduğunda yazılıyor.
        #  Anlamsız olduğu tiplerde gelse bile NULL yazılır — ama
        #  sessizce yutulmaz, yanıtta söylenir.
        # ══════════════════════════════════════════════════════════
        VADE_ZORUNLU = ('Fatura (Satis)', 'Fatura (Alis)',
                        'Alış Faturası', 'Satış Faturası',
                        'Alis Faturasi', 'Satis Faturasi')
        # Borc/alacak doguran ama vadesi BILINMEYEBILECEK tipler:
        # istenirse yazilir, zorunlu degil. Acilista eski sistemden
        # devreden bakiyenin vadesi cogu zaman bilinmiyor; zorunlu
        # yapmak girisi tikardi.
        VADE_ANLAMLI = VADE_ZORUNLU + (
            'Acilis Bakiyesi (Borc)', 'Acilis Bakiyesi (Alacak)',
            'Iade (Satis)', 'Iade (Alis)')
        if islem_tip in VADE_ZORUNLU and not data.get('vade_tarihi'):
            return jsonify({
                'ok': False,
                'mesaj': f'{islem_tip} kaydında vade tarihi zorunlu — '
                         f'yaşlandırma ve gecikme takibi buradan '
                         f'besleniyor.'}), 400

        # ── VT1 · BELGE TARİHİ ARTIK BURADA ──
        # Eskiden çok aşağıda (kur hesabının yanında) okunuyordu.
        # Aşağıdaki VİRMAN ve MAHSUP dalları ondan önce çalıştığı
        # için kuru VADEDEN alıyorlardı; vade artık çoğu tipte NULL
        # olacağına göre o dallar tarihsiz kur çekip arşivdeki EN SON
        # kuru kullanırdı — KF1'de kapattığımız hatanın aynısı.
        _h_tarihi = date.today()
        _ht = (data.get('hareket_tarihi') or '').strip()
        if _ht:
            try:
                _h_tarihi = datetime.strptime(_ht, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'ok': False,
                                'mesaj': 'Hareket tarihi GG.AA.YYYY degil, '
                                         'YYYY-AA-GG biciminde olmali'}), 400
        borc = q2(float(data.get('borc') or 0))
        alacak = q2(float(data.get('alacak') or 0))
        doviz = data.get('doviz', 'USD')
        siparis_id = data.get('siparis_id') or None
        stok_id = (data.get('stok_id') or '').strip() or None  # YENİ: stok bağlantısı
        # VT1: vade artik opsiyonel. Anlamsiz oldugu tipte GELSE BILE
        # NULL yaziliyor; yutuldugu yanitta soyleniyor.
        _vade_yok_sayildi = False
        vade = (_parse_date(data['vade_tarihi'])
                if data.get('vade_tarihi') else None)
        if vade is not None and islem_tip not in VADE_ANLAMLI:
            vade = None
            _vade_yok_sayildi = True
'''),
    ('flask_app.py', 'VT1 · flask_app.py blok 6',
     r'''                _fatura_tarihi = _parse_date(data.get('fatura_tarihi')) or vade or date.today()
''',
     r'''                # VT1: vade artik NULL olabilir; yedek BELGE TARIHI.
                _fatura_tarihi = (_parse_date(data.get('fatura_tarihi'))
                                  or _h_tarihi)
'''),
    ('flask_app.py', 'VT1 · flask_app.py blok 7',
     r'''                return jsonify({'ok': False, 'mesaj': 'Kaynak cari bulunamadı'}), 404
            kur_t = _kur_getir(doviz, vade) if doviz != 'TRY' else 1.0
''',
     r'''                return jsonify({'ok': False, 'mesaj': 'Kaynak cari bulunamadı'}), 404
            # VT1: kur BELGE tarihinden (eskiden vadeden aliniyordu)
            kur_t = _kur_getir(doviz, _h_tarihi) if doviz != 'TRY' else 1.0
'''),
    ('flask_app.py', 'VT1 · flask_app.py blok 8',
     r'''                    kasa_kur = _kur_getir(kasa.doviz, vade)
''',
     r'''                    # VT1: kur BELGE tarihinden
                    kasa_kur = _kur_getir(kasa.doviz, _h_tarihi)
'''),
    ('flask_app.py', 'VT1 · flask_app.py blok 9',
     r'''            kur_t = _kur_getir(doviz, vade) if doviz != 'TRY' else 1.0
''',
     r'''            # VT1: kur BELGE tarihinden (eskiden vadeden aliniyordu)
            kur_t = _kur_getir(doviz, _h_tarihi) if doviz != 'TRY' else 1.0
'''),
    ('flask_app.py', 'VT1 · flask_app.py blok 10',
     r'''        _h_tarihi = date.today()
        _ht = (data.get('hareket_tarihi') or '').strip()
        if _ht:
            try:
                _h_tarihi = datetime.strptime(_ht, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'ok': False,
                                'mesaj': 'Hareket tarihi GG.AA.YYYY degil, '
                                         'YYYY-AA-GG biciminde olmali'}), 400

''',
     r'''        # VT1: okuma YUKARI tasindi (virman/mahsup dallari da
        # kullanabilsin diye); burada tekrarlanmiyor.

'''),
    ('flask_app.py', 'VT1 · flask_app.py blok 11',
     r'''                                            doviz, vade)
''',
     r'''                                            doviz, _h_tarihi)
'''),
    ('flask_app.py', 'VT1 · flask_app.py blok 12',
     r'''        msg = 'Cari hareket eklendi' + kasa_notu + _avans_notu
''',
     r'''        msg = 'Cari hareket eklendi' + kasa_notu + _avans_notu
        if _vade_yok_sayildi:
            # Sessizce yutmuyoruz: gonderilen bir deger yazilmadiysa
            # kullanici BUNU bilmeli.
            msg += (f'. Vade tarihi yazılmadı — {islem_tip} bir borç '
                    f'doğurmuyor, vadesi de olmaz')
'''),
    ('flask_app.py', 'VT1 · flask_app.py blok 13',
     r'''                'gecikme_gun': ((_bugun - f.vade_tarihi).days
                                if f.vade_tarihi and f.vade_tarihi < _bugun else 0),
''',
     r'''                # VT1: tek hesap, iki cagiran
                'gecikme_gun': _fatura_gecikme(f, _bugun)[0],
                'vadesiz': _fatura_gecikme(f, _bugun)[1],
'''),
    ('flask_app.py', 'VT1 · flask_app.py blok 14',
     r'''        odemeler = CariHareket.query.filter(
            CariHareket.vade_tarihi >= bugun, CariHareket.vade_tarihi <= otuz,
            CariHareket.alacak > 0
        ).order_by(CariHareket.vade_tarihi).all()
''',
     r'''        # VT1: nakit hareketleri bu listeye girmiyor
        odemeler = _yaklasan_hareketler(bugun, otuz, 'odeme')
'''),
    ('flask_app.py', 'VT1 · flask_app.py blok 15',
     r'''        tahsilatlar = CariHareket.query.filter(
            CariHareket.vade_tarihi >= bugun, CariHareket.vade_tarihi <= otuz,
            CariHareket.borc > 0
        ).order_by(CariHareket.vade_tarihi).all()
''',
     r'''        tahsilatlar = _yaklasan_hareketler(bugun, otuz, 'tahsilat')
'''),
    ('templates/cari.html', 'VT1 · templates/cari.html blok 1',
     r'''<div class="modal-ortu" id="tahModal" onclick="if(event.target===this)tahsilatKapat()">
  <div class="modal" style="width:520px" role="dialog" aria-label="Tahsilat">
    <div class="modal-bas">
      <h3 id="tBaslik">Tahsilat Gir</h3>
      <p id="tAlt">—</p>
    </div>
    <div class="modal-gov">
      <div class="not" id="tNot" style="display:none"></div>
      <div class="form-alan" style="margin-bottom:12px">
        <label>Kapatılacak fatura</label>
        <select id="tFatura" onchange="faturaSecildi()"><option value="">— fatura seçilmeden (serbest hareket) —</option></select>
      </div>
      <div class="form-satir f2">
        <div class="form-alan"><label>Tutar</label><input id="tTutar" type="number" step="0.01"></div>
        <div class="form-alan"><label>Kasa</label><select id="tKasa"></select></div>
      </div>
      <div class="form-satir f2">
        <div class="form-alan"><label>Tarih</label><input id="tTarih" type="date"></div>
        <div class="form-alan"><label>Evrak No</label><input id="tEvrak" placeholder="opsiyonel"></div>
      </div>
      <div class="form-alan"><label>Açıklama</label><input id="tAciklama" placeholder="opsiyonel"></div>
    </div>
    <div class="modal-alt">
      <button class="iptal-btn" onclick="tahsilatKapat()">Vazgeç</button>
      <button class="btn-yeni" id="tKaydet" onclick="tahsilatKaydet()">Kaydet</button>
    </div>
  </div>
</div>
''',
     r'''<!-- ══════════════════════════════════════════════════════════════
     VT1 — "TAHSİLAT GİR" PANELİ SİLİNDİ

     Bu panel ÖLÜ koddu: dosyada yalnız kendi markup'ında ve
     `tahsilatKapat()` içinde geçiyordu, `acik` sınıfını ekleyen
     hiçbir şey yoktu. BF1 ile iki form birleştirilmiş, "Tahsilat /
     Ödeme" düğmesi o günden beri tam donanımlı HAREKET FORMUNU
     açıyor — `tahsilatAc()` doğrudan `hareketAc()` çağırıyor.

     Duran ölü bir form zararsız değil: içinde iki gerçek hata
     vardı ve ben onları CANLI sanıp rapor ettim.
       · tarih alanı `vade_tarihi` olarak gidiyordu, `hareket_tarihi`
         hiç gönderilmiyordu — kur bugünden alınırdı
       · `doviz: 'USD'` sabit yazılıydı, döviz seçici yoktu
     İkisi de hareket formunda doğru çalışıyor. Panel silindi ki
     bir daha kimse onu gerçek sanmasın.
     ══════════════════════════════════════════════════════════════ -->
'''),
    ('templates/cari.html', 'VT1 · templates/cari.html blok 2',
     r'''      <div class="form-satir f2">
        <!-- BT1 — BELGE TARİHİ
''',
     r'''      <!-- VT1: vade yalnız BORÇ doğuran tiplerde görünür, o yüzden
           satırın sütun sayısı da tipe göre değişiyor (hTarihSatir). -->
      <div class="form-satir f2" id="hTarihSatir">
        <!-- BT1 — BELGE TARİHİ
'''),
    ('templates/cari.html', 'VT1 · templates/cari.html blok 3',
     r'''        <div class="form-alan"><label>Vade Tarihi
          <span style="font-weight:400;color:var(--soluk)">· ödeme/tahsilat</span></label>
''',
     r'''        <!-- VT1: ipucu "ödeme/tahsilat" diyordu — yanıltıcıydı.
             Vade bir BORCUN ne zaman ödeneceğidir; tahsilatın
             vadesi olmaz, para zaten gelmiştir. -->
        <div class="form-alan" id="hVadeAlan"><label>Vade Tarihi
          <span style="font-weight:400;color:var(--soluk)">· borç ne zaman ödenecek</span></label>
'''),
    ('templates/cari.html', 'VT1 · templates/cari.html blok 4',
     r'''   ?tahsilat=1 / ?hareket=1 ile gelir. Ancak tahsilatAc(id) ve
   hareketAc(cariId, unvan) bir cari gerektirir — kısayolda henüz seçili cari
   yoktur. Bu yüzden önce bir seçim penceresi açılır, seçim yapılınca asıl
   fonksiyon çağrılır.
   NOT: base.html bu iki fonksiyonu 2,4 saniye boyunca arar; veri (TUM) o
   sırada henüz yüklenmemiş olabileceği için liste dolana kadar beklenir. */
let SEC_HEDEF = null;   // 'tahsilat' | 'hareket'
''',
     r'''   ?tahsilat=1 / ?hareket=1 ile gelir. hareketAc(cariId, unvan) bir cari
   gerektirir — kısayolda henüz seçili cari yoktur. Bu yüzden önce bir
   seçim penceresi açılır, seçim yapılınca asıl fonksiyon çağrılır.

   VT1: İKİ KISAYOL DA AYNI FORMU AÇAR. BF1'de iki form birleştirilmişti;
   ayrı bir tahsilat paneli artık yok. İşlem tipi carinin türüne göre
   hazır seçili gelir (tedarikçiye Ödeme, müşteriden Tahsilat).

   NOT: base.html bu iki fonksiyonu 2,4 saniye boyunca arar; veri (TUM) o
   sırada henüz yüklenmemiş olabileceği için liste dolana kadar beklenir. */
let SEC_HEDEF = null;   // 'tahsilat' | 'hareket' — ikisi de aynı formu açar
'''),
    ('templates/cari.html', 'VT1 · templates/cari.html blok 5',
     r'''  const hedef = SEC_HEDEF;
  cariSecKapat();
  if (hedef === 'tahsilat') tahsilatAc(c.id);
  else hareketAc(c.id, c.unvan);
''',
     r'''  cariSecKapat();
  /* VT1: iki hedef de AYNI formu açıyordu (BF1'den beri). `?tahsilat=1`
     ile gelenin tek farkı işlem tipinin hazır seçili gelmesiydi;
     o da artık `hareketAc`ın içinde. */
  hareketAc(c.id, c.unvan);
'''),
    ('templates/cari.html', 'VT1 · templates/cari.html blok 6',
     r'''  if (yazabilir('cari'))
    eylem.push(`<button class="blok-btn" onclick="tahsilatAc('${kacar(id)}')">Tahsilat / Ödeme</button>`);
''',
     r'''  /* VT1: "Tahsilat / Ödeme" düğmesi KALDIRILDI. BF1'den beri aynı
     formu açıyordu — iki düğme, tek panel. Tek farkı işlem tipini
     hazır seçmesiydi; onu `hareketAc` artık kendi yapıyor
     (tedarikçiye Ödeme, müşteriden Tahsilat). */
'''),
    ('templates/cari.html', 'VT1 · templates/cari.html blok 7',
     r'''let HAR_CARI = null, HAR_KASALAR = [], HAR_SIPARISLER = [];
let TAH_CARI = null, ACIK_FATURALAR = [];

/* ═══ TAHSİLAT / ÖDEME ═══
   Fatura seçilirse → POST /api/fatura/<id>/tahsilat  (cari VE kasa birlikte güncellenir)
   Fatura seçilmezse → POST /api/cari/hareket         (yalnızca cari defteri) */
async function tahsilatAc(id) {
  /* TEK FORM (BF1).
     Eskiden ayrı bir "Tahsilat / Ödeme" formu vardı; onda fatura
     seçimi vardı ama DÖVİZ yoktu, hareket formunda ise tersi.
     İkisi de işi yarım yapıyordu. Artık tahsilat düğmesi de tam
     donanımlı hareket formunu açıyor, işlem tipi hazır seçili. */
  const c = (TUM || []).find(x => x.id === id) || {};
  await hareketAc(id, c.unvan || id);
  const sel = document.getElementById('hIslem');
  if (sel) {
    /* Tedarikçiye ÖDEME, müşteriden TAHSİLAT varsayılanı. */
    const tedarikci = String(c.cari_tip || '').toLowerCase().includes('tedarik');
    const hedef = tedarikci ? 'Ödeme' : 'Tahsilat';
    const uy = [...sel.options].find(o => o.value.includes(hedef)
      || o.value.includes(hedef.replace('Ö', 'O')));
    if (uy) { sel.value = uy.value; hareketTipiDegisti(); }
  }
}
function tahsilatKapat() { document.getElementById('tahModal').classList.remove('acik'); }

function faturaSecildi() {
  const fid = document.getElementById('tFatura').value;
  const f = ACIK_FATURALAR.find(x => x.id === fid);
  const not = document.getElementById('tNot');
  not.style.display = '';
  if (f) {
    document.getElementById('tTutar').value = f.kalan;
    not.style.background = 'var(--verde-acik)'; not.style.color = 'var(--verde)';
    not.textContent = 'Faturaya işlenecek: cari bakiyesi VE kasa birlikte güncellenir.';
  } else {
    not.style.background = 'var(--kehribar-bg)'; not.style.color = 'var(--kehribar)';
    not.textContent = 'Fatura seçilmedi: yalnızca cari defterine işlenir, kasaya yansımaz.';
  }
}

async function tahsilatKaydet() {
  const tutar = parseFloat(document.getElementById('tTutar').value);
  if (!tutar || tutar <= 0) { bildir('Geçerli bir tutar gir.', true); return; }
  const b = BAKIYE[TAH_CARI.id] || { net: 0 };
  const odeme = b.net < 0;
  const fid = document.getElementById('tFatura').value;
  const kasaId = document.getElementById('tKasa').value;
  const btn = document.getElementById('tKaydet');
  btn.disabled = true; btn.textContent = 'Kaydediliyor…';
  try {
    if (fid && fid.startsWith('STOK:')) {
      /* STOK ALIŞ BORCU (AF1): `Fatura` kaydı yok, o yüzden
         /api/fatura/<id>/tahsilat çalışmaz (404 verirdi).
         Cari hareket olarak yazılır ve `baglanti_id` ile o alışa
         bağlanır — açık borç listesi ödemeyi buradan düşer. */
      await api('/api/cari/hareket', {
        method: 'POST',
        body: JSON.stringify({
          cari_id: TAH_CARI.id,
          islem_tip: odeme ? 'Odeme' : 'Tahsilat',
          tutar, alacak: odeme ? 0 : tutar, borc: odeme ? tutar : 0,
          doviz: (ACIK_FATURALAR.find(f => 'STOK:' + (f.fatura_no || f.id) === fid) || {}).doviz || 'USD',
          kasa_id: kasaId ? parseInt(kasaId) : null,
          baglanti_tip: 'stok_fatura',
          baglanti_id: fid.slice(5),
          vade_tarihi: document.getElementById('tTarih').value || null,
          evrak_no: document.getElementById('tEvrak').value,
          aciklama: document.getElementById('tAciklama').value
        })
      });
    } else if (fid) {
      await api(`/api/fatura/${encodeURIComponent(fid)}/tahsilat`, {
        method: 'POST',
        body: JSON.stringify({
          tutar, kasa_id: kasaId ? parseInt(kasaId) : null, tahsilat_tipi: 'nakit',
          evrak_no: document.getElementById('tEvrak').value,
          aciklama: document.getElementById('tAciklama').value
        })
      });
    } else {
      await api('/api/cari/hareket', {
        method: 'POST',
        body: JSON.stringify({
          cari_id: TAH_CARI.id,
          islem_tip: odeme ? 'Odeme' : 'Tahsilat',
          tutar, alacak: odeme ? 0 : tutar, borc: odeme ? tutar : 0,
          doviz: 'USD',
          vade_tarihi: document.getElementById('tTarih').value || null,
          evrak_no: document.getElementById('tEvrak').value,
          aciklama: document.getElementById('tAciklama').value
        })
      });
    }
    bildir((odeme ? 'Ödeme' : 'Tahsilat') + ' kaydedildi · ' + para(tutar));
    tahsilatKapat();
    await yukle();
  } catch (e) { /* */ }
  finally { btn.disabled = false; btn.textContent = 'Kaydet'; }
}
''',
     r'''
/* ── VT1 · VADESİ OLAN TİPLER ──
   Vade, bir BORCUN ne zaman ödeneceğidir. Tahsilatın, ödemenin,
   virmanın, mahsubun, kur farkının vadesi olmaz — orada para zaten
   el değiştirmiş ya da ortada bir borç yok.

   Bu liste SUNUCUDAKİ `VADE_ANLAMLI` ile aynı olmalı; ekran bir
   değer gönderse bile sunucu o tiplerde yazmıyor, boşuna
   doldurtmayalım. */
const VADE_ANLAMLI_TIPLER = [
  'Fatura (Satis)', 'Fatura (Alis)',
  'Acilis Bakiyesi (Borc)', 'Acilis Bakiyesi (Alacak)',
  'Iade (Satis)', 'Iade (Alis)'];

let HAR_CARI = null, HAR_KASALAR = [], HAR_SIPARISLER = [];
/* VT1: TAH_CARI · ACIK_FATURALAR · tahsilatKapat ·
   faturaSecildi · tahsilatKaydet — silinen panele aitti. */
'''),
    ('templates/cari.html', 'VT1 · templates/cari.html blok 8',
     r'''  document.getElementById('hVade').valueAsDate = new Date();
  belgeTarihiVarsayilan();   // BT1
''',
     r'''  /* VT1: vade ARTIK BURADA DOLDURULMUYOR. Her tipte bugünle dolu
     geliyordu; tahsilatın vadesi olmaz ve o değer yüzünden bugün
     tahsil edilmiş paralar "yaklaşan ödemeler" listesine düşüyordu.
     Doldurmayı `hareketTipiDegisti()` yapıyor — yalnız borç doğuran
     tiplerde. */
  document.getElementById('hVade').value = '';
  belgeTarihiVarsayilan();   // BT1

  /* VT1: işlem tipi CARİNİN TÜRÜNE göre hazır seçili gelir —
     kaldırılan "Tahsilat / Ödeme" düğmesi bunu yapıyordu, kaybolmasın.
     Tedarikçiye ÖDEME, müşteriden TAHSİLAT. */
  const _c = (TUM || []).find(x => String(x.id) === String(cariId)) || {};
  const _sel = document.getElementById('hIslem');
  if (_sel) {
    const _ted = String(_c.cari_tip || '').toLowerCase().includes('tedarik');
    const _hedef = _ted ? 'Ödeme' : 'Tahsilat';
    const _uy = [...(_sel.options || [])].find(
      o => o.value.includes(_hedef) || o.value.includes(_hedef.replace('Ö', 'O')));
    if (_uy) _sel.value = _uy.value;
  }
'''),
    ('templates/cari.html', 'VT1 · templates/cari.html blok 9',
     r'''  if (kasali) {
''',
     r'''
  /* ── VT1 · VADE YALNIZ BORÇ DOĞURAN TİPLERDE ──
     Tahsilatın vadesi olmaz: para zaten el değiştirmiş. Alan her
     tipte görünüyor ve BUGÜNLE dolu geliyordu; sonucu ölçtüm —
     bugün tahsil edilmiş paralar "yaklaşan ödemeler" listesinde,
     yani ödeyeceğimiz paralar arasında duruyordu.
     Sunucu da bu tiplerde geleni yazmıyor; ekran onunla aynı
     kuralı izlesin ki kullanıcı boşuna doldurmasın. */
  const vadeli = VADE_ANLAMLI_TIPLER.includes(tip);
  const vAlan = document.getElementById('hVadeAlan');
  const vSatir = document.getElementById('hTarihSatir');
  if (vAlan) vAlan.style.display = vadeli ? '' : 'none';
  if (vSatir) vSatir.classList.toggle('f2', vadeli);
  if (!vadeli) document.getElementById('hVade').value = '';
  else if (!document.getElementById('hVade').value)
    document.getElementById('hVade').valueAsDate = new Date();
  if (kasali) {
'''),
    ('tests/test_kritik.py', 'VT1 · tests/test_kritik.py blok 1',
     r'''        assert float((kf[0].borc or 0) + (kf[0].alacak or 0)) == 20000
''',
     r'''        assert float((kf[0].borc or 0) + (kf[0].alacak or 0)) == 20000


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
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA DZ4 — KESIM KAYITLARI')
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
        print('    python3 yama_vt1.py            # rapor')
        print('    python3 yama_vt1.py --uygula')
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
        print('  ⊙ Yama VT1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_vt1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_vt1'
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
    print('    1) Cari -> bir cariyi ac. Cekmecede artik TEK dugme:')
    print('       "Hareket ekle". "Tahsilat / Odeme" kaldirildi —')
    print('       ayni formu aciyordu.')
    print()
    print('    2) Formda islem tipini degistir: TAHSILAT secince')
    print('       VADE TARIHI alani kayboluyor, belge tarihi tam')
    print('       genislige yayiliyor. FATURA secince geri geliyor.')
    print()
    print('    3) venv/bin/python denetim_vade.py  — eski kayitlarda')
    print('       duran anlamsiz vadeleri ve bu yamadan sonra birden')
    print('       gecikmis gorunecek vadesiz faturalari listeler.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

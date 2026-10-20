#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA UR1 — STOK KAYNAĞI: SATIN ALMA / ÜRETİM
=============================================

ÖNKOŞUL: yama_yp4.py uygulanmış olmalı.

── NE İSTENDİ ──
  Toplu içe aktarmaya "üretim" seçeneği; plaka girmeyi kolaylaştırmak.

── NEDEN "ALIŞ TİPİ"NE BEŞİNCİ SEÇENEK OLARAK KOYMADIM ──
  `alis_tipi` bir KDV sınıflandırması. Kodda yaptığı TEK iş şu:
  değer 'yurtici_kdvli' değilse KDV oranını sıfıra çekmek. "Üretim"i
  oraya koymak kazara çalışırdı — KDV sıfırlanırdı — ama alan yalan
  söylemeye başlardı: ürettiğin mal, sistemde bir ALIŞ TİPİ taşır.

  Üretim ile alış DÖRT yerde ayrışıyor, birde değil:
      · tedarikçi borcu      (üretimde yok)
      · fatura/fatura durumu (üretimde yok)
      · KDV                  (üretimde yok)
      · `alis_fiyati`nın ANLAMI — alış fiyatı mı, üretim maliyeti mi

  Tek bir açılır menü girdisi bunu taşıyamaz. Ayrı alan: `kaynak`.

── EN ÖNEMLİ KISIM: ÇİFT SAYIM KAPISI ──
  Sistemde KAYITLI bir bloktan kesilen plakalar içe aktarmayla
  girilmemeli. Kesim modülü üç şey yapıyor, içe aktarma hiçbirini
  yapamaz:

      · bloğu stoktan düşer
      · m² maliyetini bloğun maliyeti + kesim giderlerinden hesaplar
      · kesim izini (kesim_detay) yazar

  "Üretim" kipinde girilen plakanın blok numarası stokta duran bir
  bloğa aitse aktarım DURUYOR ve seni Depo → Kesim'e yolluyor. Blok
  numaraları senin kendi numaraların ve yıllar içinde
  tekrarlanabildiği için sert ret değil: ekran bir kez uyarıyor,
  gerçekten başka bir blok ise onaylayıp devam edebiliyorsun
  ("kısmi aktarım" ile aynı desen).

  Uyarı SATIR SATIR değil BİR KEZ soruluyor. Sunucudaki kapı da
  duruyor ama orada her satır ayrı ayrı reddedilirdi: 200 plakalık
  bir aktarımda 200 ayrı hata, hepsi aynı cümle.

── ÜRETİM KİPİNDE NE OLUYOR ──
  Ekran: tedarikçi, alış tipi, fatura durumu, fatura no ve KDV
  alanları GİZLENİYOR (pasifleştirilmiyor — pasif ama görünen alan
  "burada bir şey var ama dokunamıyorsun" der, oysa üretimde o
  alanların karşılığı yok). "Alış Fiyatı" → "Üretim Maliyeti",
  "Alış / Fatura Tarihi" → "Üretim Tarihi".

  Sunucu: aynı kuralı ayrıca zorluyor. Gizlemek bir görüntü tercihi,
  güvenlik önlemi değil — açık kalmış eski bir sekme 'faturali'
  yollayıp üretilen mal için tedarikçiye borç yazdırabilirdi.

── YOLDA ÖLÇÜLEN: KESİM BUGÜN YALAN SÖYLÜYOR ──
  Kesim modülü plaka/ebatlı üretirken `alis_tipi`ye dokunmuyor, yani
  model varsayılanı 'yurtici_kdvli' kalıyordu: ÜRETTİĞİN mal sistemde
  SATIN ALINMIŞ gibi duruyor. Kimse fark etmemiş çünkü KDV'si sıfır
  ve borç doğmuyor — ama bilgi yanlış.

  İki düzeltme:
    1. `alis_tipi` sütun VARSAYILANI kaldırıldı. Varsayılan dururken
       alana None yazılamıyordu (SQLAlchemy değeri verilmemiş sayıp
       varsayılanı basıyor — ölçüldü). Artık NULL = "alış tipi yok".
    2. `goc_ur1.py` geriye dönük işaretliyor: `kesim_detay` izi olan
       her plaka/ebatlı 'uretim', kalan her satır 'satinalma'.
       Ölçüt kayıt, tahmin değil.

── ÖLÇÜLDÜ ──
  üretim + tedarikçi seçili      → cari borcu YOK   (kontrol grubu:
                                    aynı gövde satın almayla → borç VAR)
  üretim, 'faturali' zorlanarak  → sunucu 'faturasiz'a çeviriyor
  üretim, KDV %20 gönderilerek   → kdv_oran 0, kdv_tutar 0
  üretim                         → alis_tipi NULL, kaynak 'uretim'
  stokta duran bloktan üretim    → 409 'blok_stokta', plaka YAZILMADI
  aynısı satın alma kipinde      → geçiyor (orada çift sayım yok)
  onaylanmış uyarıyla            → geçiyor
  liste ucu                      → kaynak 'uretim', alis_tipi null

  göç: kesimden çıkan plaka → 'uretim', elle girilen → 'satinalma',
       ikinci koşu "yapılacak iş yok"

  115 test geçti (110 + 5 yeni kalıcı test);
  firma · js · form · zincir · akis · degismezlik temiz.
  İçe aktarma penceresi iki kipte de Chromium'da basıldı.

── NE YAPMADIM ──
  Kesim ekranına Excel'den toplu hedef satırı girişi — bu B işi, bir
  sonraki adım. Blok sistemdeyse doğru yol orası; bu yamadaki kapı,
  o hazır olana kadar yanlış yolu kapatıyor.

DOSYALAR
--------
  models.py              kaynak sütunu (3 stok tablosu) · alis_tipi
                         varsayılanı kaldırıldı
  flask_app.py           kaynak kararı · üretimde cari/fatura/KDV
                         kapanıyor · çift sayım kapısı · liste ucu
  templates/stok.html    iki formda da kaynak seçimi · alan gizleme
                         · tek seferlik blok uyarısı
  tests/test_kritik.py   5 yeni test
  goc_ur1.py             YENİ — kesimden çıkanları geriye dönük
                         işaretler (tam dosya, base64)

KULLANIM
--------
  python3 yama_ur1.py            # RAPOR
  python3 yama_ur1.py --uygula
  sudo systemctl restart milestone-erp      ← `kaynak` sütunu burada kurulur
  venv/bin/python goc_ur1.py                # RAPOR
  venv/bin/python goc_ur1.py --uygula
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
    'models.py': 'UR1 · KAYNAK: SATIN ALMA mı ÜRETİM mi',
    'flask_app.py': 'UR1 · ÇİFT SAYIM KAPISI',
    'templates/stok.html': 'UR1 · KAYNAK ──',
    'tests/test_kritik.py': 'def test_ur1_uretim_tedarikci_borcu_dogurmaz',
    # Tam dosya yazilanin da imzasi OLMALI. Olmazsa her kosuda
    # yeniden yaziliyor; cerrahi dosyalar "zaten uygulanmis" derken
    # bu "yazilacak" der ve ikinci kosu YARIM DURUM sanip duruyordu
    # (olculdu).
    'goc_ur1.py': 'STOK KAYNAĞI GÖÇÜ  ·  UR1',
}
ONKOSUL = {
    'models.py': 'class PlakaStok',
    'flask_app.py': 'def _panel_firma_baglami',
    'templates/stok.html': 'function topluKdvDurum',
    'tests/test_kritik.py': 'def test_yp4_panele_girince_firma_secimi_dusuyor',
}
TAM_YAZILAN = ['goc_ur1.py']

DEGISIKLIKLER = [
    ('models.py', 'UR1 · models.py blok 1',
     r'''    alis_fiyat_birim = db.Column(db.String(5), default='ton')
    kdv_dahil_mi    = db.Column(db.Boolean, default=False)
    kdv_oran        = db.Column(Olcu, default=0)
    alis_tipi       = db.Column(db.String(20), default='yurtici_kdvli')
''',
     r'''    alis_fiyat_birim = db.Column(db.String(5), default='ton')
    kdv_dahil_mi    = db.Column(db.Boolean, default=False)
    kdv_oran        = db.Column(Olcu, default=0)
    # UR1: SUTUN VARSAYILANI KALDIRILDI. Varsayilan dururken
    # alis_tipi'ne None yazilamiyordu — SQLAlchemy degeri
    # verilmemis sayip 'yurtici_kdvli' basiyordu (olculdu).
    # Bu, URETILEN mali satin alinmis gibi gosteriyordu ve
    # kesimden cikan butun plakalar bugun oyle duruyor.
    #
    # Artik NULL = 'alis tipi yok' demek. Satin almada deger
    # ucun kendisi yaziyor; okuma tarafi zaten `kaynak`a bakip
    # satin alma satirlarinda 'yurtici_kdvli'ye dusuyor.
    alis_tipi       = db.Column(db.String(20))
    # ── UR1 · KAYNAK: SATIN ALMA mı ÜRETİM mi ──
    # `alis_tipi` bir KDV siniflandirmasi: yaptigi tek is, deger
    # 'yurtici_kdvli' degilse KDV oranini sifira cekmek. "Uretim"i
    # oraya bes'inci deger olarak koymak kazara calisirdi ama alan
    # yalan soylemeye baslardi — uretilen mal bir ALIS TIPI tasimis
    # olurdu.
    #
    # Uretim ile alis DORT yerde ayrisiyor, birde degil: tedarikci
    # borcu, fatura, KDV ve `alis_fiyati`nin ANLAMI (alis fiyati mi,
    # uretim maliyeti mi). O yuzden ayri alan.
    #
    # NULL = 'satinalma'. Otomatik migrasyon sutunu DEFAULT'suz
    # ekliyor, yani mevcut satirlar NULL kalir; eski davranis
    # korunsun diye NULL satin alma sayiliyor (`ortak_liste` ile
    # ayni desen). Okurken daima `kaynak or 'satinalma'`.
    kaynak          = db.Column(db.String(12), default='satinalma')
'''),
    ('models.py', 'UR1 · models.py blok 2',
     r'''    slab_no         = db.Column(db.Integer)
    alis_fiyati     = db.Column(Para)
    alis_fiyat_birim = db.Column(db.String(5), default='m2')
    kdv_dahil_mi    = db.Column(db.Boolean, default=False)
    kdv_oran        = db.Column(Olcu, default=0)
    alis_tipi       = db.Column(db.String(20), default='yurtici_kdvli')
''',
     r'''    slab_no         = db.Column(db.Integer)
    alis_fiyati     = db.Column(Para)
    alis_fiyat_birim = db.Column(db.String(5), default='m2')
    kdv_dahil_mi    = db.Column(db.Boolean, default=False)
    kdv_oran        = db.Column(Olcu, default=0)
    # UR1: varsayilan yok — bkz. BlokStok.alis_tipi.
    alis_tipi       = db.Column(db.String(20))
    # UR1: kaynak — bkz. BlokStok'taki gerekce.
    kaynak          = db.Column(db.String(12), default='satinalma')
'''),
    ('models.py', 'UR1 · models.py blok 3',
     r'''    alis_tipi       = db.Column(db.String(20), default='yurtici_kdvli')
''',
     r'''    # UR1: varsayilan yok — bkz. BlokStok.alis_tipi.
    alis_tipi       = db.Column(db.String(20))
    # UR1: kaynak — bkz. BlokStok'taki gerekce.
    kaynak          = db.Column(db.String(12), default='satinalma')
'''),
    ('flask_app.py', 'UR1 · flask_app.py blok 1',
     r'''            item['alis_tipi'] = getattr(s, 'alis_tipi', None) or 'yurtici_kdvli'
''',
     r'''            # UR1: ÜRETİLEN malın alış tipi YOK. `or 'yurtici_kdvli'`
            # varsayılanı satın alınanlar için doğru ama üretimde
            # yalan söylerdi — ekran üretilen plakayı 'Yurt içi
            # KDV'li alış' diye gösterirdi.
            item['kaynak'] = getattr(s, 'kaynak', None) or 'satinalma'
            item['alis_tipi'] = (None if item['kaynak'] == 'uretim'
                                 else (getattr(s, 'alis_tipi', None)
                                       or 'yurtici_kdvli'))
'''),
    ('flask_app.py', 'UR1 · flask_app.py blok 2',
     r'''        # ─── FATURA DURUMU + TARİHLER (mal/fatura zaman farkı yönetimi) ───
        # fatura_durumu: 'faturali' (mal+fatura birlikte) | 'faturasiz' (mal geldi, fatura bekliyor)
        #                | 'mal_bekliyor' (fatura kesildi, mal henüz gelmedi)
        _fatura_durumu = (data.get('fatura_durumu') or 'faturali').strip()
        if _fatura_durumu not in ('faturali', 'faturasiz', 'mal_bekliyor'):
            _fatura_durumu = 'faturali'
''',
     r'''        # ─── UR1 · KAYNAK: SATIN ALMA mı ÜRETİM mi ───
        # Üretilen mal SATIN ALINMADI: tedarikçisi, faturası, KDV'si
        # ve cari borcu yok. `alis_fiyati` de alış fiyatı değil,
        # ÜRETİM MALİYETİ anlamına geliyor.
        #
        # Karar BURADA tek sefer veriliyor; aşağıdaki üç dal
        # (BLOK/PLAKA/EBATLI) onu okuyor. Dallara ayrı ayrı yazmak,
        # birinde unutulunca o ürün tipinde sessizce tedarikçi borcu
        # doğurması demekti.
        _kaynak = (data.get('kaynak') or 'satinalma').strip()
        if _kaynak not in ('satinalma', 'uretim'):
            _kaynak = 'satinalma'
        _uretim = (_kaynak == 'uretim')

        # ─── FATURA DURUMU + TARİHLER (mal/fatura zaman farkı yönetimi) ───
        # fatura_durumu: 'faturali' (mal+fatura birlikte) | 'faturasiz' (mal geldi, fatura bekliyor)
        #                | 'mal_bekliyor' (fatura kesildi, mal henüz gelmedi)
        _fatura_durumu = (data.get('fatura_durumu') or 'faturali').strip()
        if _fatura_durumu not in ('faturali', 'faturasiz', 'mal_bekliyor'):
            _fatura_durumu = 'faturali'
        if _uretim:
            # ÜRETİMDE FATURA YOK. 'faturasiz' burada 'fatura bekliyor'
            # değil, 'fatura diye bir şey yok' demek — tedarikçi cari
            # hareketi de bu değer sayesinde hiç doğmuyor.
            #
            # Ekranda alan zaten gizli; yine de istemciye
            # güvenmiyoruz. Açık kalmış eski bir sekme ya da elle
            # atılan bir istek 'faturali' yollayabilir ve o zaman
            # üretilen mal için tedarikçiye borç yazılırdı.
            _fatura_durumu = 'faturasiz'
'''),
    ('flask_app.py', 'UR1 · flask_app.py blok 3',
     r'''        # EBATLI: referans kodu sistemi otomatik benzersiz üretir, duplicate kontrolü gereksiz
''',
     r'''
            # ── UR1 · ÇİFT SAYIM KAPISI ──
            # Üretim kipinde girilen plakanın blok numarası STOKTA
            # DURAN bir bloğa aitse, o blok kesilmiş demektir ama
            # sistemde hâlâ kesilmemiş gibi duruyor: aynı mal iki kez
            # sayılır. Üstelik plakaların maliyeti bloğun maliyetinden
            # türemez, elle yazılan rakam olur ve kesim izi (kesim_detay)
            # hiç oluşmaz.
            #
            # Doğru yol Kesim modülü. Burada DURUYORUZ.
            #
            # Neden sert ret değil de onaylanabilir ret: blok numaraları
            # kullanıcının kendi numaraları ve yıllar içinde
            # tekrarlanabiliyor. Gerçekten başka bir blok söz konusuysa
            # işi tamamen kapatmak doğru olmaz — ama sessizce geçmek de
            # olmaz. Ekran uyarıyı gösteriyor, kullanıcı bilerek
            # onaylarsa `blok_uyarisi_onaylandi` ile geliyor ('kısmi
            # aktarım' ile aynı desen).
            if _uretim and not data.get('blok_uyarisi_onaylandi'):
                _duran = BlokStok.query.filter(
                    BlokStok.blok_no == _blok_no,
                    BlokStok.durum != 'Teslim Edildi').first()
                if _duran:
                    return jsonify({
                        'ok': False, 'error': 'blok_stokta',
                        'blok_id': _duran.id, 'blok_durum': _duran.durum,
                        'mesaj': f'"{_blok_no}" bloğu stokta duruyor (ID: {_duran.id}, durum: {_duran.durum}). Bu bloktan kesilen plakaları içe aktarırsan blok stokta kesilmemiş gibi kalır ve aynı malı iki kez saymış olursun; plakaların maliyeti de bloktan türemez. Doğru yol Depo → Kesim. Blok başka bir blok ise uyarıyı onaylayıp devam edebilirsin.'}), 409
        # EBATLI: referans kodu sistemi otomatik benzersiz üretir, duplicate kontrolü gereksiz
'''),
    ('flask_app.py', 'UR1 · flask_app.py blok 4',
     r'''                    kdv_oran = 0
                    kdv_dahil_mi = False
                # Birim fiyat KDV hariç (matrah) saklanır
                if kdv_dahil_mi and kdv_oran > 0:
                    fiyat = q2(fiyat_girilen / (1 + kdv_oran/100))
''',
     r'''                    kdv_oran = 0
                    kdv_dahil_mi = False
                if _uretim:
                    # UR1: uretilen malin ALIS TIPI yok. NULL yaziliyor;
                    # 'yurtici_kdvli' birakmak (kesimin bugun yaptigi sey)
                    # uretilen mali satin alinmis gibi gosteriyordu.
                    alis_tipi = None
                    kdv_oran = 0
                    kdv_dahil_mi = False
                # Birim fiyat KDV hariç (matrah) saklanır
                if kdv_dahil_mi and kdv_oran > 0:
                    fiyat = q2(fiyat_girilen / (1 + kdv_oran/100))
'''),
    ('flask_app.py', 'UR1 · flask_app.py blok 5',
     r'''                                aciklama=data.get('aciklama', ''), alis_tipi=alis_tipi)
''',
     r'''                                aciklama=data.get('aciklama', ''), alis_tipi=alis_tipi,
                                kaynak=_kaynak)
'''),
    ('flask_app.py', 'UR1 · flask_app.py blok 6',
     r'''                # Birim fiyat KDV hariç (matrah) saklanır
                if kdv_dahil_mi and kdv_oran > 0:
                    # KDV dahil girilmis: ayristir
''',
     r'''                if _uretim:
                    # UR1: uretilen malin ALIS TIPI yok. NULL yaziliyor;
                    # 'yurtici_kdvli' birakmak (kesimin bugun yaptigi sey)
                    # uretilen mali satin alinmis gibi gosteriyordu.
                    alis_tipi = None
                    kdv_oran = 0
                    kdv_dahil_mi = False
                # Birim fiyat KDV hariç (matrah) saklanır
                if kdv_dahil_mi and kdv_oran > 0:
                    # KDV dahil girilmis: ayristir
'''),
    ('flask_app.py', 'UR1 · flask_app.py blok 7',
     r'''                                     durum='Serbest', aciklama=data.get('aciklama', ''), alis_tipi=alis_tipi)
''',
     r'''                                     durum='Serbest', aciklama=data.get('aciklama', ''), alis_tipi=alis_tipi,
                                     kaynak=_kaynak)
'''),
    ('flask_app.py', 'UR1 · flask_app.py blok 8',
     r'''                    kdv_dahil_mi = False
                fiyat_girilen = _sayi('fiyat')
''',
     r'''                    kdv_dahil_mi = False
                if _uretim:
                    # UR1: uretilen malin ALIS TIPI yok. NULL yaziliyor;
                    # 'yurtici_kdvli' birakmak (kesimin bugun yaptigi sey)
                    # uretilen mali satin alinmis gibi gosteriyordu.
                    alis_tipi = None
                    kdv_oran = 0
                    kdv_dahil_mi = False
                fiyat_girilen = _sayi('fiyat')
'''),
    ('flask_app.py', 'UR1 · flask_app.py blok 9',
     r'''                        alis_tipi=alis_tipi,
''',
     r'''                        alis_tipi=alis_tipi, kaynak=_kaynak,
'''),
    ('templates/stok.html', 'UR1 · templates/stok.html blok 1',
     r'''        <div class="form-satir f3">
          <div class="form-alan">
''',
     r'''
        <!-- ── UR1 · KAYNAK ──
             Bu seçim formun yarısını açıp kapatıyor, o yüzden EN ÜSTTE
             ve tek başına: altındaki alanların hangisinin anlamlı
             olduğunu o belirliyor.

             "Üretim"i Alış Tipi'ne beşinci seçenek olarak koymadım.
             `alis_tipi` bir KDV sınıflandırması (kodda yaptığı tek iş,
             değer 'yurtici_kdvli' değilse KDV'yi sıfırlamak); üretim
             ise bir alış DEĞİL. Aralarındaki fark dört alana yayılıyor:
             tedarikçi borcu, fatura, KDV ve fiyatın ANLAMI. -->
        <div class="form-satir f2" style="margin-bottom:4px">
          <div class="form-alan">
            <label>Kaynak</label>
            <select id="tKaynak" onchange="topluKaynakDegisti()">
              <option value="satinalma">Satın alma — tedarikçiden alındı</option>
              <option value="uretim">Üretim — kendi ürettiğimiz mal</option>
            </select>
          </div>
          <div class="form-alan" id="tKaynakNot" style="display:none">
            <!-- UR1: `.not` sınıfı bu şablonda TANIMLI DEĞİL (ayarlar
                 ekranında var). Sınıf adını yazmakla yetinseydim not
                 kutusuz, düz metin olarak akardı — ölçüldü. -->
            <div style="margin:20px 0 0;background:var(--kehribar-bg,#FDF6E3);
                 color:var(--kehribar,#8A6D1F);border-radius:var(--r-kucuk,8px);
                 padding:10px 12px;font-size:.79rem;line-height:1.5">
              Üretimde tedarikçi borcu, fatura ve KDV yok; aşağıdaki
              fiyat <b>üretim maliyeti</b> olarak yazılır.
              <b>Sistemde kayıtlı bir bloktan kesilen plakalar buraya
              girilmez</b> — onlar Depo → Kesim'den geçer, yoksa blok
              stokta kesilmemiş gibi kalır.
            </div>
          </div>
        </div>

        <div class="form-satir f3">
          <div class="form-alan" id="tCariAlan">
'''),
    ('templates/stok.html', 'UR1 · templates/stok.html blok 2',
     r'''          <div class="form-alan"><label>Alış Fiyatı (ortak)
''',
     r'''          <div class="form-alan"><label id="tFiyatEtiket">Alış Fiyatı (ortak)
'''),
    ('templates/stok.html', 'UR1 · templates/stok.html blok 3',
     r'''        <div class="form-satir f3">
          <div class="form-alan"><label>Alış Tipi</label>
''',
     r'''        <div class="form-satir f3" id="tFaturaSatir">
          <div class="form-alan"><label>Alış Tipi</label>
'''),
    ('templates/stok.html', 'UR1 · templates/stok.html blok 4',
     r'''          <div class="form-alan"><label>KDV Oranı (%)</label>
            <input id="tKdv" type="number" step="0.1" min="0" max="100" value="20"
                   data-buyuk-harf="hayir" onchange="topluOnizle()"></div>
          <div class="form-alan" style="display:flex;align-items:flex-end">
''',
     r'''          <!-- UR1: KDV alanları tek tek gizleniyor, SATIR değil —
               "Konum" üretimde de anlamlı ve bu satırda duruyor. -->
          <div class="form-alan" id="tKdvAlan"><label>KDV Oranı (%)</label>
            <input id="tKdv" type="number" step="0.1" min="0" max="100" value="20"
                   data-buyuk-harf="hayir" onchange="topluOnizle()"></div>
          <div class="form-alan" id="tKdvDahilAlan" style="display:flex;align-items:flex-end">
'''),
    ('templates/stok.html', 'UR1 · templates/stok.html blok 5',
     r'''              Alış fiyatına nakliye dahil
''',
     r'''              <span id="tNakliyeEtiket">Alış fiyatına nakliye dahil</span>
'''),
    ('templates/stok.html', 'UR1 · templates/stok.html blok 6',
     r'''          <div class="form-alan"><label>Alış / Fatura Tarihi</label>
''',
     r'''          <div class="form-alan"><label id="tAlisTarihEtiket">Alış / Fatura Tarihi</label>
'''),
    ('templates/stok.html', 'UR1 · templates/stok.html blok 7',
     r'''        <div class="form-alan"><label>Alış Tipi</label>
          <select id="sAlisTipi" onchange="alisTipiDegisti()">
''',
     r'''        <!-- UR1: kaynak, alış tipinin ÖNÜNDE. Üretim seçilirse alış
             tipi ve KDV zaten anlamını yitiriyor, gizleniyorlar. -->
        <div class="form-alan"><label>Kaynak</label>
          <select id="sKaynak" onchange="kaynakDegisti()">
            <option value="satinalma">Satın alma</option>
            <option value="uretim">Üretim</option>
          </select>
        </div>
        <div class="form-alan" id="sAlisTipiAlan"><label>Alış Tipi</label>
          <select id="sAlisTipi" onchange="alisTipiDegisti()">
'''),
    ('templates/stok.html', 'UR1 · templates/stok.html blok 8',
     r'''function alisTipiDegisti() {
''',
     r'''/* UR1: üretimde alış tipi ve KDV satırı gizlenir; tedarikçi alanı
   duruyor ama sunucu üretimde cari borcu zaten oluşturmuyor —
   "kimden/nereden ürettik" bilgisini kaydetmek isteyebilirsin. */
function kaynakDegisti() {
  const uretim = document.getElementById('sKaynak').value === 'uretim';
  const at = document.getElementById('sAlisTipiAlan');
  if (at) at.style.display = uretim ? 'none' : '';
  const kdv = document.getElementById('kdvSatir');
  if (uretim) {
    document.getElementById('sKdv').value = 0;
    document.getElementById('sKdvDahil').checked = false;
    if (kdv) kdv.style.display = 'none';
    hesapla();
  } else {
    alisTipiDegisti();
  }
}

function alisTipiDegisti() {
'''),
    ('templates/stok.html', 'UR1 · templates/stok.html blok 9',
     r'''        uretici: document.getElementById('sUretici').value,
''',
     r'''        kaynak: document.getElementById('sKaynak').value,
        uretici: document.getElementById('sUretici').value,
'''),
    ('templates/stok.html', 'UR1 · templates/stok.html blok 10',
     r'''function topluKdvDurum() {
''',
     r'''/* ── UR1 · KAYNAK DEĞİŞTİ ──
   Üretimde tedarikçi, alış tipi, fatura ve KDV alanları GİZLENİYOR,
   pasifleştirilmiyor. Pasif ama görünen alan "burada bir şey var ama
   dokunamıyorsun" der; oysa üretimde o alanların karşılığı yok.

   Gizlemek yetmez, DEĞERLERİ de temizleniyor: açık kalmış bir
   tedarikçi seçimi gizlendikten sonra da gönderilir ve üretilen mal
   için cari borç doğururdu. (Sunucu da aynı şeyi ayrıca zorluyor —
   iki taraf da güvenmiyor.) */
function topluKaynakDegisti() {
  const uretim = document.getElementById('tKaynak').value === 'uretim';
  const goster = (id, ac) => {
    const e = document.getElementById(id);
    if (e) e.style.display = ac ? '' : 'none';
  };
  goster('tCariAlan', !uretim);
  goster('tFaturaSatir', !uretim);
  goster('tKdvAlan', !uretim);
  goster('tKdvDahilAlan', !uretim);
  goster('tKaynakNot', uretim);
  if (uretim) {
    document.getElementById('tCari').value = '';
    document.getElementById('tFaturaNo').value = '';
    document.getElementById('tKdv').value = 0;
    document.getElementById('tKdvDahil').checked = false;
    document.getElementById('tFaturaDurum').value = 'faturasiz';
  }
  const at_ = document.getElementById('tAlisTarihEtiket');
  if (at_) at_.textContent = uretim ? 'Üretim Tarihi' : 'Alış / Fatura Tarihi';
  const ne_ = document.getElementById('tNakliyeEtiket');
  if (ne_) ne_.textContent = uretim
    ? 'Maliyete nakliye dahil' : 'Alış fiyatına nakliye dahil';
  const et = document.getElementById('tFiyatEtiket');
  if (et) et.innerHTML = uretim
    ? 'Üretim Maliyeti (ortak) <span style="font-weight:400;color:var(--soluk)">· birim başına</span>'
    : 'Alış Fiyatı (ortak) <span style="font-weight:400;color:var(--soluk)">· Excel\'de yoksa</span>';
  topluOnizle();
}

function topluKdvDurum() {
'''),
    ('templates/stok.html', 'UR1 · templates/stok.html blok 11',
     r'''  let uyari = `${TP_SATIRLAR.length} kayıt ${tip} olarak stoğa eklenecek.`;
  if (cari && faturaDurum !== 'faturasiz') uyari += `\n\n"${cari}" carisine alış borcu oluşturulacak.`;
  else if (!cari) uyari += `\n\nTedarikçi seçilmedi — cari borcu OLUŞMAYACAK.`;
  uyari += '\n\nDevam edilsin mi?';
  if (!await onayla(uyari)) return;

  const kdvli = document.getElementById('tAlisTipi').value === 'yurtici_kdvli';
  const ortak = {
    tip: tip,
    uretici: cari,
''',
     r'''  const _uretimKip = document.getElementById('tKaynak').value === 'uretim';
  let uyari = `${TP_SATIRLAR.length} kayıt ${tip} olarak stoğa eklenecek.`;
  if (_uretimKip) uyari += `\n\nKaynak: ÜRETİM — tedarikçi borcu, fatura ve KDV oluşmaz.`
                         + `\nGirilen fiyat üretim maliyeti olarak yazılır.`;
  else if (cari && faturaDurum !== 'faturasiz') uyari += `\n\n"${cari}" carisine alış borcu oluşturulacak.`;
  else if (!cari) uyari += `\n\nTedarikçi seçilmedi — cari borcu OLUŞMAYACAK.`;
  uyari += '\n\nDevam edilsin mi?';
  if (!await onayla(uyari)) return;

  const uretim = document.getElementById('tKaynak').value === 'uretim';
  const kdvli = !uretim && document.getElementById('tAlisTipi').value === 'yurtici_kdvli';
  const ortak = {
    tip: tip,
    kaynak: uretim ? 'uretim' : 'satinalma',
    uretici: uretim ? '' : cari,
'''),
    ('templates/stok.html', 'UR1 · templates/stok.html blok 12',
     r'''  let basarili = 0, hatali = 0;
''',
     r'''  /* ── UR1 · ÇİFT SAYIM KAPISI, SATIR SATIR DEĞİL BİR KEZ ──
     Sunucu da aynı kontrolü yapıyor ama orada satır satır çalışır:
     200 plakalık bir aktarımda 200 ayrı 409 hatası görürdün, hepsi
     aynı cümleyi tekrar ederek. Soru bir kez sorulmalı.

     Kapı yalnızca ÜRETİM kipinde anlamlı: satın alınan plakanın blok
     numarasının stoktaki bir blokla aynı olması olağan (o bloğu da
     satın almış olabilirsin). Sorun, ÜRETTİĞİNİ söylediğin plakanın
     bloğunun hâlâ kesilmemiş görünmesi. */
  let blokOnayi = false;
  if (uretim && tip === 'PLAKA') {
    document.getElementById('tIlerlemeYazi').textContent = 'Blok stoğu kontrol ediliyor…';
    try {
      const bloklar = await api('/api/stok?tip=BLOK&per_page=1000');
      const stokta = new Map();
      (bloklar.data || []).forEach(b => {
        const bn = String(b.blok_no || '').trim().toUpperCase();
        if (bn && b.durum !== 'Teslim Edildi') stokta.set(bn, b);
      });
      const carpisan = [...new Set(TP_SATIRLAR
        .map(k => String(k.blok_no || '').trim().toUpperCase())
        .filter(bn => bn && stokta.has(bn)))];
      if (carpisan.length) {
        const liste = carpisan.slice(0, 8).join(', ')
          + (carpisan.length > 8 ? ` …ve ${carpisan.length - 8} tane daha` : '');
        const devam = await onayla(
          `Şu blok(lar) stokta duruyor: ${liste}\n\n`
          + 'Bu bloklardan kesilen plakaları buradan girersen bloklar '
          + 'stokta kesilmemiş gibi kalır — aynı malı iki kez saymış '
          + 'olursun. Plakaların maliyeti de bloktan türemez, girdiğin '
          + 'rakam olur ve kesim izi oluşmaz.\n\n'
          + 'Doğru yol: Depo → Kesim.\n\n'
          + 'Bunlar başka bloklarsa (numara tekrarı) yine de devam '
          + 'edebilirsin. Devam edilsin mi?',
          { tehlike: true, tamam: 'Yine de aktar', iptal: 'Vazgeç' });
        if (!devam) {
          document.getElementById('tIlerleme').style.display = 'none';
          btn.disabled = false; btn.textContent = 'İçe Aktar';
          return;
        }
        blokOnayi = true;
      }
    } catch (e) { /* okunamazsa sunucudaki kapı yine korur */ }
  }

  let basarili = 0, hatali = 0;
'''),
    ('templates/stok.html', 'UR1 · templates/stok.html blok 13',
     r'''                  .filter(Boolean).join(' ').trim(),
''',
     r'''                  .filter(Boolean).join(' ').trim(),
      /* UR1: uyarı yukarıda BİR KEZ gösterilip onaylandıysa satırlar
         sunucudaki kapıdan geçsin. Onay yoksa gönderilmiyor — kapı
         orada ayakta kalıyor. */
      blok_uyarisi_onaylandi: blokOnayi || undefined,
'''),
    ('tests/test_kritik.py', 'UR1 · tests/test_kritik.py blok 1',
     r'''        assert isinstance(u.get('firmalar'), list), u.get('ad')
''',
     r'''        assert isinstance(u.get('firmalar'), list), u.get('ad')


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
'''),
]

# ══════════════════════════════════════════════════════════════════════
#  TAM DOSYA · goc_ur1.py
#
#  Parça değil tam dosya; iç içe tırnak yığını üretmesin diye
#  base64. Uygulandıktan sonra diskteki dosya baştan sona
#  yorumlu, okunur Python — önce okumak istersen:
#      python3 yama_kf.py --yaz-gecici
# ══════════════════════════════════════════════════════════════════════
TAM_ICERIK = {
    'goc_ur1.py': (
        'IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwojIC0qLSBjb2Rpbmc6IHV0Zi04IC0qLQojIOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkAojICBNaWxlc3RvbmUgRVJQIOKAlCBTVE9LIEtBWU5BxJ5JIEfDlsOHw5wgIMK3'
        'ICBVUjEKIwojICDDlk5LT8WeVUw6IHlhbWFfdXIxLnB5IHV5Z3VsYW5txLHFnyBWRSBT'
        'RVJWxLBTIFlFTsSwREVOIEJBxZ5MQVRJTE1JxZ4gb2xtYWzEsS4KIwojICDilIDilIAg'
        'U0lSQSBORURFTiDDlk5FTUzEsCDilIDilIAKIyAgICB5YW1hIOKGkiBzeXN0ZW1jdGwg'
        'cmVzdGFydCDihpIgQlUgQkVUxLBLCiMKIyAgICBga2F5bmFrYCBzw7x0dW51bnUgYcOn'
        'xLFsxLHFnyBrZW5kaXNpIGVrbGl5b3IgKFNEMiBvdG9tYXRpawojICAgIG1pZ3Jhc3lv'
        'bnUpLiBCdSBiZXRpayBvbnUgS1VSTUFaOyB5b2tzYSAiw7ZuY2UgeWVuaWRlbiBiYcWf'
        'bGF0IgojICAgIGRleWlwIMOnxLFrYXIuCiMKIyAg4pSA4pSAIE5FIFlBUEFSIOKUgOKU'
        'gAojICAgIDEpIEtFU8SwTURFTiDDh0lLTUnFniBzdG9rbGFyxLEgYGtheW5hayA9ICd1'
        'cmV0aW0nYCBpxZ9hcmV0bGVyLgojCiMgICAgICAgQnVnw7xuIGtlc2ltIG1vZMO8bMO8'
        'IHBsYWthL2ViYXRsxLEgw7xyZXRpcmtlbiBgYWxpc190aXBpYCBhbGFuxLFuYQojICAg'
        'ICAgIGRva3VubXV5b3IsIHlhbmkgbW9kZWwgdmFyc2F5xLFsYW7EsSBvbGFuICd5dXJ0'
        'aWNpX2tkdmxpJwojICAgICAgIGthbMSxeW9yOiDDnFJFVFTEsMSexLBNxLBaIG1hbCwg'
        'c2lzdGVtZGUgU0FUSU4gQUxJTk1JxZ4gZ2liaQojICAgICAgIGR1cnV5b3IuIEtpbXNl'
        'IGZhcmsgZXRtZWRpIMOnw7xua8O8IEtEVidzaSBzxLFmxLFyIHZlIHRlZGFyaWvDp2kK'
        'IyAgICAgICBib3JjdSBkb8SfbXV5b3Ig4oCUIGFtYSBzdG9rIGxpc3Rlc2luZGUgdmUg'
        'aWxlcmlkZSB5YXrEsWxhY2FrIGhlcgojICAgICAgIHJhcG9yZGEgeWFubMSxxZ8gYmls'
        'Z2kuCiMKIyAgICAgICDDlmzDp8O8dCBga2VzaW1fZGV0YXlgIGl6aTogaGVkZWZfc3Rv'
        'a19pZCBvIHRhYmxvZGF5c2EgbyBzdG9rCiMgICAgICAgYmlyIGtlc2ltZGVuIMOnxLFr'
        'bcSxxZ90xLFyLiBUYWhtaW4geW9rLCBrYXnEsXQgdmFyLgojCiMgICAgMikgR0VSxLAg'
        'S0FMQU4gaGVyIHNhdMSxcsSxIGBrYXluYWsgPSAnc2F0aW5hbG1hJ2AgeWFwYXIuCiMK'
        'IyAgICAgICBTw7x0dW4gTlVMTCBvbGFyYWsgZWtsZW5peW9yIHZlIGtvZCBOVUxMJ8Sx'
        'IHphdGVuICJzYXTEsW4gYWxtYSIKIyAgICAgICBzYXnEsXlvci4gWWluZSBkZSBhw6fE'
        'sWvDp2EgZG9sZHVydXlvcnVtOiB5YXLEsSBOVUxMIHlhcsSxIGRvbHUgYmlyCiMgICAg'
        'ICAgc8O8dHVuLCAiYnUgc2F0xLFyxLFuIGtheW5hxJ/EsSBiaWxpbm1peW9yIG11IHlv'
        'a3NhIHNhdMSxbiBhbG1hCiMgICAgICAgbcSxPyIgc29ydXN1bnUgaGVyIHNvcmd1ZGEg'
        'eWVuaWRlbiBkb8SfdXJ1cmR1LgojCiMgIOKUgOKUgCBORSBZQVBNQVog4pSA4pSACiMg'
        'ICAgSGnDp2JpciBzYXTEsXLEsSBzaWxtZXosIHRhxZ/EsW1heiwgdHV0YXLEsW7EsSBk'
        'ZcSfacWfdGlybWV6LiBZYWxuxLF6Y2EKIyAgICB0ZWsgYmlyIG1ldGluIHPDvHR1bnVu'
        'dSBkb2xkdXJ1ci4gWWFubMSxxZ8gZ2lkZXJzZSBnZXJpIGTDtm7DvMWfIGRlCiMgICAg'
        'dGVrIGJpciBVUERBVEUuCiMKIyAg4pSA4pSAIEfDnFZFTkzEsEsg4pSA4pSACiMgICAg'
        '4oCiIC0tdXlndWxhIE9MTUFEQU4gSMSww4dCxLBSIMWeRVkgREXEnsSwxZ5NRVo7IHlh'
        'bG7EsXpjYSByYXBvciB2ZXJpci4KIyAgICDigKIgUG9zdGdyZVNRTCdkZSDDtm5jZSBw'
        'Z19kdW1wIHllZGXEn2kgYWzEsXI7IHllZGVrIGJhxZ9hcsSxc8SxenNhIMSwUFRBTC4K'
        'IyAgICDigKIgVGVrIHRyYW5zYWN0aW9uLgojICAgIOKAoiBUZWtyYXIgw6dhbMSxxZ90'
        'xLFyxLFsYWJpbGlyOiBpa2luY2kga2/Fn3UgInlhcMSxbGFjYWsgacWfIHlvayIgZGVy'
        'LgojCiMgIEtVTExBTklNIChwcm9qZSBkaXppbmluZGUpOgojICAgICAgdmVudi9iaW4v'
        'cHl0aG9uIGdvY191cjEucHkgICAgICAgICAgICAgIyBSQVBPUgojICAgICAgdmVudi9i'
        'aW4vcHl0aG9uIGdvY191cjEucHkgLS11eWd1bGEgICAgIyBVWUdVTEFSCiMg4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        'CmltcG9ydCBvcwppbXBvcnQgc3VicHJvY2VzcwppbXBvcnQgc3lzCmZyb20gZGF0ZXRp'
        'bWUgaW1wb3J0IGRhdGV0aW1lCmZyb20gcGF0aGxpYiBpbXBvcnQgUGF0aApmcm9tIHVy'
        'bGxpYi5wYXJzZSBpbXBvcnQgdXJscGFyc2UKCmZyb20gZG90ZW52IGltcG9ydCBsb2Fk'
        'X2RvdGVudgpmcm9tIHNxbGFsY2hlbXkgaW1wb3J0IGNyZWF0ZV9lbmdpbmUsIGluc3Bl'
        'Y3QsIHRleHQKCmxvYWRfZG90ZW52KCkKClVZR1VMQSA9ICctLXV5Z3VsYScgaW4gc3lz'
        'LmFyZ3YKVlRfVVJMID0gb3MuZW52aXJvbi5nZXQoJ0RBVEFCQVNFX1VSTCcpCgppZiBu'
        'b3QgVlRfVVJMOgogICAgcHJpbnQoJ0hBVEE6IERBVEFCQVNFX1VSTCBidWx1bmFtYWTE'
        'sSAoLmVudiBva3VuYW1hZMSxKS4nKQogICAgcHJpbnQoJyAgQWRyZXMgb2xtYWRhbiB5'
        'YW5sxLHFnyB2ZXJpdGFiYW7EsW5hIGJhxJ9sYW5hYmlsaXJkaW0uJykKICAgIHN5cy5l'
        'eGl0KDEpCgptb3RvciA9IGNyZWF0ZV9lbmdpbmUoVlRfVVJMKQprYXluYWtfdXJsID0g'
        'dXJscGFyc2UoVlRfVVJMKQpwZyA9IG1vdG9yLmRpYWxlY3QubmFtZSBpbiAoJ3Bvc3Rn'
        'cmVzcWwnLCAncG9zdGdyZXMnKQpkZW5ldGNpID0gaW5zcGVjdChtb3RvcikKCnByaW50'
        'KCfilZAnICogNzApCnByaW50KCcgIE1JTEVTVE9ORSBFUlAg4oCUIFNUT0sgS0FZTkHE'
        'nkkgR8OWw4fDnCAgwrcgIFVSMScpCnByaW50KCcgIE1PRDonLCAnVVlHVUxBJyBpZiBV'
        'WUdVTEEgZWxzZSAnUkFQT1IgKGhpw6diaXIgxZ9leSBkZcSfacWfbWV6KScpCnByaW50'
        'KCfilZAnICogNzApCnByaW50KGYiIFZlcml0YWJhbsSxIDoge2theW5ha191cmwucGF0'
        'aC5sc3RyaXAoJy8nKX0gQCB7a2F5bmFrX3VybC5ob3N0bmFtZSBvciAneWVyZWwnfSIp'
        'CnByaW50KGYnIFPDvHLDvGPDvCAgICAgOiB7bW90b3IuZGlhbGVjdC5uYW1lfScpCnBy'
        'aW50KCkKCgpkZWYgeWVkZWtfYWwoKToKICAgIGlmIG5vdCBwZzoKICAgICAgICBwcmlu'
        'dCgnIOKaoCBQb3N0Z3JlU1FMIGRlxJ9pbCDigJQgb3RvbWF0aWsgeWVkZWsgYXRsYW5k'
        'xLEuJykKICAgICAgICByZXR1cm4gVHJ1ZQogICAgaGVkZWYgPSBQYXRoLmhvbWUoKSAv'
        'ICd5ZWRla2xlcicKICAgIGhlZGVmLm1rZGlyKGV4aXN0X29rPVRydWUpCiAgICBkb3N5'
        'YSA9IGhlZGVmIC8gZid1cjEtb25jZXNpLXtkYXRldGltZS5ub3coKTolWSVtJWRfJUgl'
        'TSVTfS5kdW1wJwogICAgdHJ5OgogICAgICAgIG9ydGFtID0gZGljdChvcy5lbnZpcm9u'
        'KQogICAgICAgIGlmIGtheW5ha191cmwucGFzc3dvcmQ6CiAgICAgICAgICAgIG9ydGFt'
        'WydQR1BBU1NXT1JEJ10gPSBrYXluYWtfdXJsLnBhc3N3b3JkCiAgICAgICAgcyA9IHN1'
        'YnByb2Nlc3MucnVuKAogICAgICAgICAgICBbJ3BnX2R1bXAnLCAnLUZjJywgJy1mJywg'
        'c3RyKGRvc3lhKSwKICAgICAgICAgICAgICctaCcsIGtheW5ha191cmwuaG9zdG5hbWUg'
        'b3IgJ2xvY2FsaG9zdCcsCiAgICAgICAgICAgICAnLXAnLCBzdHIoa2F5bmFrX3VybC5w'
        'b3J0IG9yIDU0MzIpLAogICAgICAgICAgICAgJy1VJywga2F5bmFrX3VybC51c2VybmFt'
        'ZSBvciAncG9zdGdyZXMnLAogICAgICAgICAgICAga2F5bmFrX3VybC5wYXRoLmxzdHJp'
        'cCgnLycpXSwKICAgICAgICAgICAgZW52PW9ydGFtLCBjYXB0dXJlX291dHB1dD1UcnVl'
        'LCB0ZXh0PVRydWUsIHRpbWVvdXQ9NjAwKQogICAgICAgIGlmIChzLnJldHVybmNvZGUg'
        'IT0gMCBvciBub3QgZG9zeWEuZXhpc3RzKCkKICAgICAgICAgICAgICAgIG9yIGRvc3lh'
        'LnN0YXQoKS5zdF9zaXplIDwgMTAyNCk6CiAgICAgICAgICAgIHByaW50KCcg4pyXIFll'
        'ZGVrIEFMSU5BTUFESSDigJQgZ8O2w6cgxLBQVEFMIGVkaWxkaS4nKQogICAgICAgICAg'
        'ICBwcmludChmJyAgIHsocy5zdGRlcnIgb3IgIiIpLnN0cmlwKClbOjIwMF19JykKICAg'
        'ICAgICAgICAgcmV0dXJuIEZhbHNlCiAgICAgICAgcHJpbnQoZicg4pyTIHtkb3N5YX0g'
        'ICh7ZG9zeWEuc3RhdCgpLnN0X3NpemUgLyAxMDI0Oi4wZn0gS0IpJykKICAgICAgICBy'
        'ZXR1cm4gVHJ1ZQogICAgZXhjZXB0IEZpbGVOb3RGb3VuZEVycm9yOgogICAgICAgIHBy'
        'aW50KCcg4pyXIHBnX2R1bXAgYnVsdW5hbWFkxLEg4oCUIGfDtsOnIMSwUFRBTCBlZGls'
        'ZGkuJykKICAgICAgICByZXR1cm4gRmFsc2UKICAgIGV4Y2VwdCBzdWJwcm9jZXNzLlRp'
        'bWVvdXRFeHBpcmVkOgogICAgICAgIHByaW50KCcg4pyXIFllZGVrIHphbWFuIGHFn8Sx'
        'bcSxbmEgdcSfcmFkxLEg4oCUIGfDtsOnIMSwUFRBTCBlZGlsZGkuJykKICAgICAgICBy'
        'ZXR1cm4gRmFsc2UKCgojIOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkAojICDDlk5LT8WeVUw6IGBrYXluYWtgIHPDvHR1'
        'bnUgYcOnxLFsxLHFn3RhIGt1cnVsbXXFnyBvbG1hbMSxCiMg4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQClRBQkxPTEFS'
        'ID0gKCdibG9rX3N0b2snLCAncGxha2Ffc3RvaycsICdlYmF0bGlfc3RvaycpCnRhYmxv'
        'bGFyID0gc2V0KGRlbmV0Y2kuZ2V0X3RhYmxlX25hbWVzKCkpCgpla3Npa190YWJsbyA9'
        'IFt0IGZvciB0IGluIFRBQkxPTEFSIGlmIHQgbm90IGluIHRhYmxvbGFyXQppZiBla3Np'
        'a190YWJsbzoKICAgIHByaW50KGYiIOKclyDFnnUgdGFibG8obGFyKSB5b2s6IHsnLCAn'
        'LmpvaW4oZWtzaWtfdGFibG8pfSIpCiAgICBwcmludCgnICAgWWFubMSxxZ8gdmVyaXRh'
        'YmFuxLFuYSBiYcSfbGFubcSxxZ8gb2xhYmlsaXJpbS4gRHVydXlvcnVtLicpCiAgICBz'
        'eXMuZXhpdCgxKQoKZWtzaWtfc3V0dW4gPSBbdCBmb3IgdCBpbiBUQUJMT0xBUgogICAg'
        'ICAgICAgICAgICBpZiAna2F5bmFrJyBub3QgaW4ge3NbJ25hbWUnXSBmb3IgcyBpbiBk'
        'ZW5ldGNpLmdldF9jb2x1bW5zKHQpfV0KaWYgZWtzaWtfc3V0dW46CiAgICBwcmludCgn'
        'IOKclyBga2F5bmFrYCBTw5xUVU5VIEhFTsOcWiBZT0s6JykKICAgIGZvciB0IGluIGVr'
        'c2lrX3N1dHVuOgogICAgICAgIHByaW50KGYnICAgICB7dH0ua2F5bmFrJykKICAgIHBy'
        'aW50KCkKICAgIHByaW50KCcgICBTw7x0dW51IHV5Z3VsYW1hbsSxbiBBw4dJTEnFnkkg'
        'ZWtsaXlvciAoU0QyIG90b21hdGlrJykKICAgIHByaW50KCcgICBtaWdyYXN5b251KS4g'
        'U8SxcmEgxZ91OicpCiAgICBwcmludCgpCiAgICBwcmludCgnICAgICBweXRob24zIHlh'
        'bWFfdXIxLnB5IC0tdXlndWxhJykKICAgIHByaW50KCcgICAgIHN1ZG8gc3lzdGVtY3Rs'
        'IHJlc3RhcnQgbWlsZXN0b25lLWVycCcpCiAgICBwcmludCgnICAgICB2ZW52L2Jpbi9w'
        'eXRob24gZ29jX3VyMS5weSAtLXV5Z3VsYSAgICAgIOKGkCBzb25yYSBiZW4nKQogICAg'
        'c3lzLmV4aXQoMSkKCmlmICdrZXNpbV9kZXRheScgbm90IGluIHRhYmxvbGFyOgogICAg'
        'cHJpbnQoJyDinJcgYGtlc2ltX2RldGF5YCB0YWJsb3N1IHlvayDigJQga2VzaW1kZW4g'
        'w6fEsWthbiBzdG9rbGFyxLEnKQogICAgcHJpbnQoJyAgIGF5xLFydCBlZGVtZW0uIFRh'
        'aG1pbmxlIGnFn2FyZXRsZW1la3RlbnNlIGR1cnV5b3J1bS4nKQogICAgc3lzLmV4aXQo'
        'MSkKCnByaW50KCcg4pyTIGBrYXluYWtgIHPDvHR1bnUgw7zDpyBzdG9rIHRhYmxvc3Vu'
        'ZGEgZGEgeWVyaW5kZScpCnByaW50KCkKCiMg4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCiMgIERVUlVNCiMg4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        'CiMgS2VzaW0gaGVkZWZpIG9sYXJhayBZQUxOSVpDQSBwbGFrYSB2ZSBlYmF0bMSxIMO8'
        'cmV0aWxpeW9yOyBibG9rCiMga2VzaW1pbiBHxLBSRMSwU8SwLCDDp8Sxa3TEsXPEsSBk'
        'ZcSfaWwuIFlpbmUgZGUgYmxvayB0YWJsb3N1bnUgZGEKIyBkb2xkdXJ1eW9ydXogKGhl'
        'cHNpIHNhdMSxbiBhbG1hKSDigJQgc8O8dHVuIHlhcsSxIGJvxZ8ga2FsbWFzxLFuLgpV'
        'UkVUSU1fU09SR1UgPSB7CiAgICAncGxha2Ffc3Rvayc6ICJTRUxFQ1QgRElTVElOQ1Qg'
        'aGVkZWZfc3Rva19pZCBGUk9NIGtlc2ltX2RldGF5ICIKICAgICAgICAgICAgICAgICAg'
        'IldIRVJFIGhlZGVmX3RpcCA9ICdQTEFLQScgQU5EIGhlZGVmX3N0b2tfaWQgSVMgTk9U'
        'IE5VTEwiLAogICAgJ2ViYXRsaV9zdG9rJzogIlNFTEVDVCBESVNUSU5DVCBoZWRlZl9z'
        'dG9rX2lkIEZST00ga2VzaW1fZGV0YXkgIgogICAgICAgICAgICAgICAgICAgIldIRVJF'
        'IGhlZGVmX3RpcCA9ICdFQkFUTEknIEFORCBoZWRlZl9zdG9rX2lkIElTIE5PVCBOVUxM'
        'IiwKfQoKcHJpbnQoJ+KUgCcgKiA3MCkKcHJpbnQoJyBEVVJVTScpCnByaW50KCfilIAn'
        'ICogNzApCgpwbGFuID0ge30Kd2l0aCBtb3Rvci5jb25uZWN0KCkgYXMgYjoKICAgIGZv'
        'ciB0IGluIFRBQkxPTEFSOgogICAgICAgIHRvcGxhbSA9IGIuZXhlY3V0ZSh0ZXh0KGYn'
        'U0VMRUNUIENPVU5UKCopIEZST00gInt0fSInKSkuc2NhbGFyKCkgb3IgMAogICAgICAg'
        'IGJvcyA9IGIuZXhlY3V0ZSh0ZXh0KAogICAgICAgICAgICBmJ1NFTEVDVCBDT1VOVCgq'
        'KSBGUk9NICJ7dH0iIFdIRVJFIGtheW5hayBJUyBOVUxMJykpLnNjYWxhcigpIG9yIDAK'
        'ICAgICAgICBpZiB0IGluIFVSRVRJTV9TT1JHVToKICAgICAgICAgICAgdXJldGltID0g'
        'Yi5leGVjdXRlKHRleHQoCiAgICAgICAgICAgICAgICBmJ1NFTEVDVCBDT1VOVCgqKSBG'
        'Uk9NICJ7dH0iIFdIRVJFIGlkIElOICh7VVJFVElNX1NPUkdVW3RdfSkgJwogICAgICAg'
        'ICAgICAgICAgZiJBTkQgKGtheW5hayBJUyBOVUxMIE9SIGtheW5hayA8PiAndXJldGlt'
        'JykiKSkuc2NhbGFyKCkgb3IgMAogICAgICAgIGVsc2U6CiAgICAgICAgICAgIHVyZXRp'
        'bSA9IDAKICAgICAgICBwbGFuW3RdID0geyd0b3BsYW0nOiB0b3BsYW0sICdib3MnOiBi'
        'b3MsICd1cmV0aW0nOiB1cmV0aW19CiAgICAgICAgcHJpbnQoZicgICB7dDo8MTJ9IHt0'
        'b3BsYW06PjZ9IGthecSxdCAgICcKICAgICAgICAgICAgICBmJ3tib3M6PjV9IGtheW5h'
        'xJ/EsSBib8WfICAge3VyZXRpbTo+NX0ga2VzaW1kZW4gw6fEsWttxLHFnycpCgp0b3Bs'
        'YW1faXMgPSBzdW0odlsnYm9zJ10gZm9yIHYgaW4gcGxhbi52YWx1ZXMoKSkgKyBzdW0o'
        'dlsndXJldGltJ10gZm9yIHYgaW4gcGxhbi52YWx1ZXMoKSkKcHJpbnQoKQppZiBub3Qg'
        'dG9wbGFtX2lzOgogICAgcHJpbnQoJ+KVkCcgKiA3MCkKICAgIHByaW50KCcg4pyTIFlB'
        'UElMQUNBSyDEsMWeIFlPSyDigJQga2F5bmFrIGFsYW5sYXLEsSB6YXRlbiBkb2x1Licp'
        'CiAgICBwcmludCgn4pWQJyAqIDcwKQogICAgc3lzLmV4aXQoMCkKCnByaW50KCfilIAn'
        'ICogNzApCnByaW50KCcgWUFQSUxBQ0FLJykKcHJpbnQoJ+KUgCcgKiA3MCkKZm9yIHQs'
        'IHYgaW4gcGxhbi5pdGVtcygpOgogICAgaWYgdlsndXJldGltJ106CiAgICAgICAgcHJp'
        'bnQoZiIgICB7dDo8MTJ9IHt2Wyd1cmV0aW0nXTo+NX0gc2F0xLFyIOKGkiAndXJldGlt'
        'JyAgICAoa2VzaW1fZGV0YXkgaXppIHZhcikiKQpmb3IgdCwgdiBpbiBwbGFuLml0ZW1z'
        'KCk6CiAgICBpZiB2Wydib3MnXToKICAgICAgICBwcmludChmIiAgIHt0OjwxMn0ge3Zb'
        'J2JvcyddOj41fSBzYXTEsXIg4oaSICdzYXRpbmFsbWEnICAoa2F5bmHEn8SxIGJvxZ8g'
        'b2xhbmxhcikiKQpwcmludCgpCnByaW50KCcgICBOb3Q6IMO2bmNlIMO8cmV0aW0gacWf'
        'YXJldGxlbml5b3IsIHNvbnJhIEtBTEFOIGJvxZ9sYXIgc2F0xLFuJykKcHJpbnQoJyAg'
        'IGFsbWEgeWFwxLFsxLF5b3IuIFRlcnMgc8SxcmFkYSBrZXNpbWRlbiDDp8Sxa2FubGFy'
        'IGRhIHNhdMSxbicpCnByaW50KCcgICBhbG1hIG9sdXJkdS4nKQpwcmludCgpCgppZiBu'
        'b3QgVVlHVUxBOgogICAgcHJpbnQoJ+KVkCcgKiA3MCkKICAgIHByaW50KCcgUkFQT1Ig'
        'TU9EVSDigJQgaGnDp2JpciDFn2V5IGRlxJ9pxZ9tZWRpLicpCiAgICBwcmludCgpCiAg'
        'ICBwcmludCgnIFV5Z3VsYW1hayBpw6dpbjogIHZlbnYvYmluL3B5dGhvbiBnb2NfdXIx'
        'LnB5IC0tdXlndWxhJykKICAgIHByaW50KCfilZAnICogNzApCiAgICBzeXMuZXhpdCgw'
        'KQoKIyDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZAKIyAgVVlHVUxBCiMg4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCnByaW50KCfilIAnICogNzApCnBy'
        'aW50KCcgWUVERUsnKQpwcmludCgn4pSAJyAqIDcwKQppZiBub3QgeWVkZWtfYWwoKToK'
        'ICAgIHN5cy5leGl0KDEpCnByaW50KCkKCnByaW50KCfilIAnICogNzApCnByaW50KCcg'
        'VVlHVUxBTklZT1InKQpwcmludCgn4pSAJyAqIDcwKQp3aXRoIG1vdG9yLmJlZ2luKCkg'
        'YXMgYjoKICAgIGZvciB0IGluIFRBQkxPTEFSOgogICAgICAgIGlmIHQgaW4gVVJFVElN'
        'X1NPUkdVOgogICAgICAgICAgICBzID0gYi5leGVjdXRlKHRleHQoCiAgICAgICAgICAg'
        'ICAgICBmJ1VQREFURSAie3R9IiBTRVQga2F5bmFrID0gXCd1cmV0aW1cJyAnCiAgICAg'
        'ICAgICAgICAgICBmJ1dIRVJFIGlkIElOICh7VVJFVElNX1NPUkdVW3RdfSkgJwogICAg'
        'ICAgICAgICAgICAgZiJBTkQgKGtheW5hayBJUyBOVUxMIE9SIGtheW5hayA8PiAndXJl'
        'dGltJykiKSkKICAgICAgICAgICAgaWYgcy5yb3djb3VudDoKICAgICAgICAgICAgICAg'
        'IHByaW50KGYiICAge3Q6PDEyfSB7cy5yb3djb3VudDo+NX0gc2F0xLFyICd1cmV0aW0n'
        'IGnFn2FyZXRsZW5kaSIpCiAgICBmb3IgdCBpbiBUQUJMT0xBUjoKICAgICAgICBzID0g'
        'Yi5leGVjdXRlKHRleHQoCiAgICAgICAgICAgIGYnVVBEQVRFICJ7dH0iIFNFVCBrYXlu'
        'YWsgPSBcJ3NhdGluYWxtYVwnIFdIRVJFIGtheW5hayBJUyBOVUxMJykpCiAgICAgICAg'
        'aWYgcy5yb3djb3VudDoKICAgICAgICAgICAgcHJpbnQoZiIgICB7dDo8MTJ9IHtzLnJv'
        'd2NvdW50Oj41fSBzYXTEsXIgJ3NhdGluYWxtYScgeWFwxLFsZMSxIikKCnByaW50KCkK'
        'cHJpbnQoJ+KUgCcgKiA3MCkKcHJpbnQoJyBET8SeUlVMQU1BJykKcHJpbnQoJ+KUgCcg'
        'KiA3MCkKc29ydW4gPSAwCndpdGggbW90b3IuY29ubmVjdCgpIGFzIGI6CiAgICBmb3Ig'
        'dCBpbiBUQUJMT0xBUjoKICAgICAgICBrYWxhbiA9IGIuZXhlY3V0ZSh0ZXh0KAogICAg'
        'ICAgICAgICBmJ1NFTEVDVCBDT1VOVCgqKSBGUk9NICJ7dH0iIFdIRVJFIGtheW5hayBJ'
        'UyBOVUxMJykpLnNjYWxhcigpIG9yIDAKICAgICAgICBpZiBrYWxhbjoKICAgICAgICAg'
        'ICAgcHJpbnQoZicgICDinJcge3Q6PDEyfSB7a2FsYW59IHNhdMSxcsSxbiBrYXluYcSf'
        'xLEgaMOibMOiIGJvxZ8nKQogICAgICAgICAgICBzb3J1biArPSAxCiAgICAgICAgZWxz'
        'ZToKICAgICAgICAgICAgcHJpbnQoZicgICDinJMge3Q6PDEyfSBrYXluYcSfxLEgYm/F'
        'nyBzYXTEsXIga2FsbWFkxLEnKQogICAgZm9yIHQsIHNvcmd1IGluIFVSRVRJTV9TT1JH'
        'VS5pdGVtcygpOgogICAgICAgIHlhbmxpcyA9IGIuZXhlY3V0ZSh0ZXh0KAogICAgICAg'
        'ICAgICBmJ1NFTEVDVCBDT1VOVCgqKSBGUk9NICJ7dH0iIFdIRVJFIGlkIElOICh7c29y'
        'Z3V9KSAnCiAgICAgICAgICAgIGYiQU5EIGtheW5hayA8PiAndXJldGltJyIpKS5zY2Fs'
        'YXIoKSBvciAwCiAgICAgICAgaWYgeWFubGlzOgogICAgICAgICAgICBwcmludChmJyAg'
        'IOKclyB7dDo8MTJ9IGtlc2ltZGVuIMOnxLFrYW4ge3lhbmxpc30gc2F0xLFyIMO8cmV0'
        'aW0gZGXEn2lsJykKICAgICAgICAgICAgc29ydW4gKz0gMQogICAgICAgIGVsc2U6CiAg'
        'ICAgICAgICAgIHByaW50KGYnICAg4pyTIHt0OjwxMn0ga2VzaW1kZW4gw6fEsWthbmxh'
        'csSxbiBoZXBzaSDDvHJldGltJykKICAgICMgU2F0xLFuIGFsbWEgc2F5xLFsYW4gaGnD'
        'p2JpciBzYXTEsXLEsW4ga2VzaW0gaXppIE9MTUFNQUxJCiAgICBmb3IgdCwgc29yZ3Ug'
        'aW4gVVJFVElNX1NPUkdVLml0ZW1zKCk6CiAgICAgICAgc2F5aSA9IGIuZXhlY3V0ZSh0'
        'ZXh0KAogICAgICAgICAgICBmIlNFTEVDVCBDT1VOVCgqKSBGUk9NIFwie3R9XCIgV0hF'
        'UkUga2F5bmFrID0gJ3VyZXRpbScgIgogICAgICAgICAgICBmJ0FORCBpZCBOT1QgSU4g'
        'KHtzb3JndX0pJykpLnNjYWxhcigpIG9yIDAKICAgICAgICBpZiBzYXlpOgogICAgICAg'
        'ICAgICBwcmludChmJyAgIOKaoCB7dDo8MTJ9IHtzYXlpfSBzYXTEsXIgw7xyZXRpbSBh'
        'bWEga2VzaW0gaXppIHlvaycpCiAgICAgICAgICAgIHByaW50KCcgICAgIChlbGxlIGdp'
        'cmlsbWnFnyDDvHJldGltIGthecSxdGxhcsSxIG9sYWJpbGlyIOKAlCBub3JtYWwpJykK'
        'CnByaW50KCkKcHJpbnQoJ+KVkCcgKiA3MCkKaWYgc29ydW46CiAgICBwcmludChmJyDi'
        'nJcge3NvcnVufSBET8SeUlVMQU1BIEJVTEdVU1Ug4oCUIHllZGVrdGVuIGTDtm5lYmls'
        'aXJzaW4uJykKICAgIHN5cy5leGl0KDEpCnByaW50KCcg4pyTIEfDlsOHIFRBTUFNTEFO'
        'REknKQpwcmludCgpCnByaW50KCcgS2VzaW1kZW4gw6fEsWthbiBzdG9rbGFyIGFydMSx'
        'ayDDnFJFVMSwTSBvbGFyYWsgacWfYXJldGxpOycpCnByaW50KCcgZ2VyaSBrYWxhbmxh'
        'ciBzYXTEsW4gYWxtYS4gU3RvayBsaXN0ZXNpbmRlIGF5xLFydCBlZGlsZWJpbGlybGVy'
        'LicpCnByaW50KCfilZAnICogNzApCg=='
    ),
}


def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA UR1 — STOK KAYNAGI: SATIN ALMA / URETIM')
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
        print('    python3 yama_ur1.py            # rapor')
        print('    python3 yama_ur1.py --uygula')
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

        # Söz dizimi doğrulaması: bozuk bir denetim aracı push
        # kapısını kilitler.
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
        print('  ⊙ Yama UR1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_ur1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_ur1'
            shutil.copy2(yol, yedek)
            _y = f'    yedek  : {os.path.relpath(yedek, KOK)}'
        else:
            _y = '    (yeni dosya — yedek yok)'
        with open(yol, 'w', encoding='utf-8', newline='') as f:
            f.write(icerik)
        if yol.endswith('.sh'):
            os.chmod(yol, 0o755)
        print(f'  ✓ yazıldı: {os.path.relpath(yol, KOK)}')
        print(_y)

    print('\n  ✓ YAMA UYGULANDI')
    print()
    print('  ══ SIRA ONEMLI ══')
    print()
    print('    1) sudo systemctl restart milestone-erp')
    print('       `kaynak` sutunu ACILISTA kuruluyor (SD2).')
    print()
    print('    2) venv/bin/python goc_ur1.py             # RAPOR')
    print('       venv/bin/python goc_ur1.py --uygula')
    print('       Kesimden cikmis plaka/ebatlilari geriye donuk')
    print('       "uretim" isaretler; kalani "satinalma" yapar.')
    print('       Goc once calistirilirsa kendisi durur ve sirayi yazar.')
    print()
    print('    3) venv/bin/python -m pytest tests/test_kritik.py -q')
    print()
    print('    4) Tarayicida Ctrl+F5, sonra')
    print('       Depo -> Stok -> Toplu Ice Aktar -> 4. adim: KAYNAK')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

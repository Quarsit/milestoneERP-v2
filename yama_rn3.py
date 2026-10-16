#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA RN3 — BELGE KODU AYARLAR'DAN DÜZENLENEBİLİR
=================================================

ÖNKOŞUL: MF1–MF7, TZ1 ve bir önceki yama (kimlik kökü) uygulanmış
olmalı.

Soru şuydu: "Milestone için Ayarlar → Firmalar → Belge Kodu kısmı
yok, sadece Kısaltma (STOK KODLARINDA) kısmı var." Bakınca iki ayrı
sorun çıktı — ikisi de ÖLÇÜLDÜ.

── 1 · BELGE KODU DÜZENLENEMİYORDU ──
   `belge_kodu` yalnızca firma AÇILIRKEN soruluyordu (`api_firma_ekle`
   zorunlu tutuyor, 4 karakter ve benzersiz olmasını doğruluyor). Bir
   daha değiştirmenin HİÇBİR YOLU yoktu.

   Göçle gelen ANA FİRMA'nın kodu ise boş: onu bu betik açmadı, göç
   açtı. Yani kodu olmayan tek firma, kodu ayarlanamayan tek firmaydı.

── 2 · EKRANDAKİ ALAN ÖLÜ ──
   Formda onun yerine "Kısaltma (stok kodlarında)" duruyordu. Etiket
   stok kodlarını etkilediğini söylüyor. `Firma.kisaltma` alanını
   tüm kaynakta aradım — Python, şablon, blueprint, dışa aktarma:

     · ayarlar.html formu YAZIYOR ve geri OKUYOR
     · /api/ayarlar/firma ucu YAZIYOR ve geri OKUYOR
     · BAŞKA HİÇBİR YER OKUMUYOR

   Yani alan hiçbir şeyi etkilemiyor. Stok ve belge kodlarını
   gerçekten belirleyen alan `belge_kodu`. Ekranda etkisi olmayan
   bir alan dururken, etkisi olan alana erişim yoktu — "MLS yazdım,
   hiçbir şey değişmedi" demenin kaçınılmaz olduğu bir düzen.

── ÇÖZÜM ──
   Formdaki alan `belge_kodu` oldu; doğrulama firma açma ucuyla AYNI
   (en çok 4 karakter, harf/rakam, başka firmada kullanılmıyor) —
   iki firma aynı kodu taşırsa kimlik kökleri çakışır ve bir önceki
   yamada düzeltilen "paylaşılan sayaç" hatası geri gelir.

   Açma ucundan tek farkı: burada BOŞ bırakmaya izin var. Göçle gelen
   ana firmanın kodu boş ve boş kod geçerli bir durum (kimlikler eski
   biçimde üretilir). Zorunlu kılmak, ayar formunu açan herkesi kod
   vermeye mecbur ederdi.

   `kisaltma` SÜTUNU veritabanında DURUYOR — göç yok, veri kaybı yok.
   Yalnızca forma dönmüyor: ölü alanı ekranda tutmak aynı karışıklığı
   yeniden doğurur.

   Ekranda ayrıca şu uyarı var: belge varken kodu değiştirirsen eski
   belgeler eski kökte kalır, yeni seri 01'den başlar. Kimlikler
   bozulmaz ama numara sürekliliği kopar. Şu an belge yok, yani kodu
   vermenin maliyeti sıfır.

── 3 · DÖRT TEST KIRILGANDI  [ÖLÇÜLDÜ] ──
   Bunu teslim etmeden önce "kodu ayarlarsa ne olur" diye denedim ve
   81 testten ikisi düştü. ÜRÜN DOĞRU ÇALIŞIYORDU; testler kimlikte
   SABİT KONUM varsayıyordu:

     assert sid1.startswith('SIP-STN')     → SIP-MLS-STN26-01
     assert rp...startswith('PI-STN')      → PI-MLS-STN26-01
     assert h.id.startswith('HR-STN26-')   → HR-MLS-STN26-0001
     assert numaralar[0][4:7] != numaralar[1][4:7]
                                           → 'MLS' != 'MLS'

   Bu önemliydi: kodu açıp bu testleri bırakmak, sen kodu doldurduğun
   gün push kapısının hatasız kodda hata vermesi olurdu — kapıya olan
   güven biter. Dördü de konumdan bağımsız hâle getirildi; sınanan
   şey kısaltmanın kimlikte GEÇMESİ, kaçıncı karakterde durduğu
   değil. Artık 81 test kod AYARLIYKEN de, BOŞKEN de geçiyor —
   ikisi de ölçüldü.

   İlk turda yalnızca ikisini düzeltmiştim; üçüncüsü aynı testin
   devamındaydı. Tek tek kovalamak yerine dosyayı sabit konum
   varsayan TÜM çapalar için taradım, dördü birden çıktı.

── 4 · ETİKET ÇAKIŞMASI (benim hatam) ──
   Bir önceki yamaya RN2 demiştim. O etiket projede ÇOKTAN KULLANILIYOR:
   RN1 okunur kimlikler, RN2 aynı isimli iki carinin farklı kısaltma
   alması — ikisi de testlerde o adla duruyor (`test_rn2_...`).
   Etiketler bu projede geçmişte gezinme aracı; aynı adı iki ayrı şeye
   vermek altı ay sonra tuzak olurdu. Kod içindeki etiket RN3'e
   çevrildi, aile düzeni korundu:

     RN1  okunur kimlikler
     RN2  cari kısaltma çakışması
     RN3  firma kodu kimlik kökünde + ayarlardan düzenlenebilir

── 5 · F3 DENETİMİ YORUMLARI SAYIYORDU (benim hatam) ──
   RN3'ü yazarken gereksiz bir `firma_atla()` açmıştım; F3 yakaladı
   (12 → 13) ve kaldırdım. Yerine "burada firma_atla() gerekmiyor,
   çünkü…" diye yorum yazınca sayı 14'e ÇIKTI — denetim kodu değil
   METNİ ölçüyordu.

   F3 artık yorumları atıyor ve yalnızca `with firma_atla()` biçimini
   sayıyor; süzgeci fiilen kapatan tek kullanım şekli bu. Tersten
   denendi: gerçek bir kapı eklenince yakalıyor (13), yorumda geçince
   yakalamıyor (12).

   Kaldırdığım kapı neden gereksizdi: okuma süzgeci yalnızca
   FirmaKapsamli, Veriler ve Cari'ye uygulanıyor; `firma` tablosu
   kapsam dışı, sorgu zaten tüm firmaları görüyor. (Komşu
   `api_firma_ekle` aynı sorguyu firma_atla() içinde yapıyor ve orada
   da etkisiz — dokunmadım, kapsam dışı.)

── ÖLÇÜMLER ──
   t_rn3.py · dokuz eksen, hepsi geçti:
     1 GET ucu belge_kodu döndürüyor, ana firmanın kodu boş
     2 POST ile ayarlanıyor, küçük harf BÜYÜĞE çevriliyor
     3 yeni belgeler kodu taşıyor: SIP-MLS-STN26-01 · HR-MLS-STN26-0001
     4 başka firmanın kodu reddediliyor, reddedilen yazılmıyor
     5 geçersiz kod reddediliyor (5 karakter, tire, boşluk)
     6 kendi kodunu yeniden kaydetmek sorun değil
     7 kod boşaltılabiliyor, sonra kimlikler kodsuz üretiliyor
     8 SATIS rolü değiştiremiyor (HTTP 403)
     9 şablonda fBelgeKodu var, ölü fKisaltma kalmadı

   Sekizinci eksene ilk turda "bu uç rol ayrımı yapmıyor" diye not
   düşmüştüm — YANLIŞTI, uç 403 dönüyor (küresel `_yazma_yetki_guard`
   'ayarlar' yazma yetkisi arıyor). Yanlış yorum, yorumsuz testten
   kötüdür; notu sildim, ölçümü gerçek bir doğrulamaya çevirdim.

   81 test (kod ayarlıyken ve boşken), altı denetim temiz.

DOSYALAR
--------
  flask_app.py           belge_kodu GET/POST + etiket RN2→RN3
  templates/ayarlar.html Kısaltma alanı → Belge Kodu + uyarı notu
  firma_denetim.py       F3 yorumları saymıyor + etiket
  tests/test_kritik.py   dört sabit konum çapası kaldırıldı

ŞEMA DEĞİŞMİYOR — göç gerekmiyor. `kisaltma` sütunu yerinde kalıyor.

KULLANIM
--------
  python3 yama_rn3.py            # RAPOR
  python3 yama_rn3.py --uygula
  sudo systemctl restart milestone-erp
  venv/bin/python firma_denetim.py

  Sonra Ayarlar → Firma → "Belge Kodu" alanına MLS yaz ve kaydet.
  Tarayıcıda Ctrl+F5 — form şablonu önbellekte kalmasın.
"""

import os
import py_compile
import shutil
import subprocess
import sys
import tempfile

UYGULA = '--uygula' in sys.argv
KOK = os.path.dirname(os.path.abspath(__file__))

# ── İMZA ──
# Her dosyada TAM ve AYIRT EDİCİ bir dize. Bu projede alt dizgi
# tuzağına üç kez düştüm ('MF2' imzası MF1'in docstring'inde MF2'den
# söz edildiği için eşleşmişti). İmza, yamanın GERÇEKTEN eklediği
# benzersiz satır.
DOSYA_IMZA = {
    'flask_app.py': 'RN3 · BELGE KODU',
    'templates/ayarlar.html': 'RN3 · BELGE KODU',
    'firma_denetim.py': 'YALNIZCA GERÇEK KULLANIM SAYILIR',
    'tests/test_kritik.py': 'RN3: eskiden `startswith',
}
ONKOSUL = {
    # Bir önceki yamanın kimlik kökü değişikliği olmadan etiket
    # düzeltmesinin çapası bulunmaz.
    'flask_app.py': 'FİRMA KODU KÖKE GİRER',
    'templates/ayarlar.html': "id=\"fKisaltma\"",
    # TZ1 ile gelen dosya + F3 ekseni.
    'firma_denetim.py': 'F3 · ÇIKIŞ KAPILARI',
    'tests/test_kritik.py': 'test_rn2_belge_numarasi_ayri_kisaltmayi_kullanir',
}

DEGISIKLIKLER = [
    ('flask_app.py', 'RN3 · flask_app.py blok 1',
     r'''            yil = (hareket.hareket_tarihi or date.today()).strftime('%y')
            # ── RN2 · FİRMA KODU KÖKE GİRER ──
''',
     r'''            yil = (hareket.hareket_tarihi or date.today()).strftime('%y')
            # ── RN3 · FİRMA KODU KÖKE GİRER ──
            # (İlk sürümde bu bloğa RN2 demiştim; o etiket projede
            #  ÇOKTAN KULLANILIYOR — RN2, aynı isimli iki carinin
            #  farklı kısaltma almasıdır, testlerde de o adla duruyor.
            #  Etiketler bu projede geçmişte gezinme aracı; aynı adı
            #  iki ayrı şeye vermek altı ay sonra tuzak olurdu.)
'''),
    ('flask_app.py', 'RN3 · flask_app.py blok 2',
     r'''                'kisaltma': f.kisaltma or '',
''',
     r'''                'kisaltma': f.kisaltma or '',
                # RN3: belge kodu BURADA DÜZENLENEBİLİR olmalı.
                # Eskiden yalnızca firma AÇILIRKEN sorulup bir daha
                # değiştirilemiyordu. Göçle gelen ana firmanın kodu
                # boştu ve doldurmanın hiçbir yolu yoktu; ekranda da
                # onun yerine `kisaltma` duruyordu — hiçbir şeyin
                # okumadığı ölü bir alan (ölçüldü).
                'belge_kodu': f.belge_kodu or '',
'''),
    ('flask_app.py', 'RN3 · flask_app.py blok 3',
     r'''            })
        return jsonify({'satici_firma': '', 'kisaltma': '',
''',
     r'''            })
        return jsonify({'satici_firma': '', 'kisaltma': '', 'belge_kodu': '',
'''),
    ('flask_app.py', 'RN3 · flask_app.py blok 4',
     r'''            f.kisaltma = (data.get('kisaltma') or '').strip()[:10]
''',
     r'''            f.kisaltma = (data.get('kisaltma') or '').strip()[:10]
        # ── RN3 · BELGE KODU ──
        # Doğrulama firma AÇMA ucuyla AYNI olmalı: iki firma aynı kodu
        # taşırsa kimlik kökleri çakışır ve sayacı yeniden paylaşırlar
        # — düzeltilen hatanın tam kendisi geri gelir.
        #
        # Açma ucu kodu ZORUNLU tutuyor; burada BOŞ BIRAKMAYA izin var:
        # göçle gelen ana firmanın kodu boş ve boş kod geçerli bir
        # durum (kimlikler eski biçimde kalır). Zorunlu kılmak, ayar
        # formunu açan herkesi kod vermeye mecbur ederdi.
        if data.get('belge_kodu') is not None:
            _kod = (data.get('belge_kodu') or '').strip().upper()
            if _kod:
                if len(_kod) > 4 or not _kod.isalnum():
                    return jsonify({'ok': False, 'mesaj':
                                    'Belge kodu en çok 4 karakter, '
                                    'yalnızca harf/rakam'}), 400
                # `firma_atla()` GEREKMİYOR: okuma süzgeci yalnızca
                # FirmaKapsamli, Veriler ve Cari'ye uygulanıyor (bkz.
                # _firma_suzgeci); `firma` tablosu kapsam dışı, sorgu
                # zaten tüm firmaları görüyor. Komşu `api_firma_ekle`
                # aynı sorguyu firma_atla() içinde yapıyor ama orada da
                # etkisiz — ona dokunmadım, kapsam dışı.
                #
                # Gereksiz bir çıkış kapısı açmamak önemli: her atlama
                # süzgecin KAPALI olduğu bir yer ve firma_denetim F3
                # her birini gerekçelendirmemi istiyor. İşe yaramayan
                # bir kapı eklemek o listeyi anlamsızlaştırır.
                _c = Firma.query.filter(
                    db.func.upper(Firma.belge_kodu) == _kod,
                    Firma.id != f.id).first()
                if _c:
                    return jsonify({'ok': False, 'mesaj':
                                    f'"{_kod}" kodu {_c.ad} firmasında '
                                    'kullanılıyor'}), 400
            f.belge_kodu = _kod or None
            # Kod kimlik köküne giriyor ve istek içinde önbellekli;
            # düşürülmezse aynı istekte ESKİ kodla kimlik üretilir.
            _firma_onbellek_dusur()
'''),
    ('templates/ayarlar.html', 'RN3 · templates/ayarlar.html blok 1',
     r'''        <input id="fFirma" placeholder="Tam ticari ünvan — belgelerde basılır">
      </div>
''',
     r'''        <input id="fFirma" placeholder="Tam ticari ünvan — belgelerde basılır">
      </div>
      <!-- ── RN3 · BELGE KODU ──
           Buradaki alan eskiden "Kısaltma (stok kodlarında)" idi.
           Etiket stok kodlarını etkilediğini söylüyordu ama `kisaltma`
           alanını HİÇBİR YER OKUMUYOR (tüm kaynakta arandı: yalnızca
           bu form yazıyor ve geri okuyor). Stok ve belge kodlarını
           gerçekten belirleyen alan `belge_kodu` ve o da yalnızca
           firma AÇILIRKEN sorulup bir daha değiştirilemiyordu.

           Yani ekranda etkisi olmayan bir alan dururken, etkisi olan
           alana erişim yoktu. Alan değiştirildi; `kisaltma` sütunu
           veritabanında duruyor (göç yok, veri kaybı yok) ama forma
           dönmüyor — ölü alanı ekranda tutmak aynı karışıklığı
           yeniden doğurur. -->
'''),
    ('templates/ayarlar.html', 'RN3 · templates/ayarlar.html blok 2',
     r'''      <div class="form-alan" style="margin-bottom:12px">
        <label>Kısaltma (stok kodlarında)</label>
        <input id="fKisaltma" placeholder="MST">
''',
     r'''      <div class="form-alan" style="margin-bottom:12px">
        <label>Belge Kodu (sipariş, fatura, stok ve cari kimliklerinde)</label>
        <input id="fBelgeKodu" placeholder="en çok 4 karakter — örn. MLS"
               maxlength="4" style="text-transform:uppercase">
        <div class="ipucu" style="font-size:12px;color:var(--soluk);margin-top:4px">
          Her firmanın belge sayacı bu koda göre ayrılır:
          <code>SIP-MLS-STN26-01</code>. Boş bırakılırsa kimlikler
          kodsuz üretilir (<code>SIP-STN26-01</code>).
          <b>Belge varken değiştirmeyin</b> — eski belgeler eski kökte
          kalır, yeni seri 01'den başlar; kimlikler bozulmaz ama
          numara sürekliliği kopar.
        </div>
'''),
    ('templates/ayarlar.html', 'RN3 · templates/ayarlar.html blok 3',
     r'''   Kullanıcı: /api/ayarlar/kullanici (GET/POST), /<id> (PUT/DELETE)
   Firma    : /api/ayarlar/firma (GET/POST) — satici_firma, kisaltma
''',
     r'''   Kullanıcı: /api/ayarlar/kullanici (GET/POST), /<id> (PUT/DELETE)
   Firma    : /api/ayarlar/firma (GET/POST) — satici_firma, belge_kodu
'''),
    ('templates/ayarlar.html', 'RN3 · templates/ayarlar.html blok 4',
     r'''  if (_bf) _bf.textContent = d.firma_ad ? '· ' + d.firma_ad : '';
    document.getElementById('fKisaltma').value = d.kisaltma || '';
''',
     r'''  if (_bf) _bf.textContent = d.firma_ad ? '· ' + d.firma_ad : '';
    document.getElementById('fBelgeKodu').value = d.belge_kodu || '';
'''),
    ('templates/ayarlar.html', 'RN3 · templates/ayarlar.html blok 5',
     r'''        satici_firma: document.getElementById('fFirma').value,
        kisaltma: document.getElementById('fKisaltma').value,
''',
     r'''        satici_firma: document.getElementById('fFirma').value,
        belge_kodu: document.getElementById('fBelgeKodu').value
                      .trim().toUpperCase(),
'''),
    ('firma_denetim.py', 'RN3 · firma_denetim.py blok 1',
     r'''print(" F3 · ÇIKIŞ KAPILARI (firma_atla)   [GÖZDEN GEÇİRİLMEMİŞ ATLAMA]")
print("─" * 70)
''',
     r'''print(" F3 · ÇIKIŞ KAPILARI (firma_atla)   [GÖZDEN GEÇİRİLMEMİŞ ATLAMA]")
print("─" * 70)
# ── YALNIZCA GERÇEK KULLANIM SAYILIR ──
# İlk sürüm 'firma_atla()' geçen HER satırı sayıyordu ve YORUMLARI
# da sayıyordu: bir çıkış kapısını kaldırıp yerine "burada
# firma_atla() gerekmiyor, çünkü…" diye iki satır yorum yazınca
# sayı 12'den 14'e ÇIKTI. Denetim, kodu değil metni ölçüyordu.
#
# Artık yorumlar atılıyor ve yalnızca `with firma_atla()` biçimi
# sayılıyor — süzgeci fiilen kapatan tek kullanım şekli bu.
def _kodsuz(satir):
    """Satırdaki yorumu atar (dizgi içindeki # için yeterince iyi:
    bu kaynakta firma_atla dizgi içinde geçmiyor)."""
    _k = satir.find('#')
    return satir if _k < 0 else satir[:_k]


'''),
    ('firma_denetim.py', 'RN3 · firma_denetim.py blok 2',
     r'''_atla = [(i + 1, s.strip()) for i, s in enumerate(KAYNAK.split('\n'))
         if 'firma_atla()' in s and 'def firma_atla' not in s]
''',
     r'''_atla = [(i + 1, s.strip()) for i, s in enumerate(KAYNAK.split('\n'))
         if re.search(r'\bwith\s+firma_atla\(\)', _kodsuz(s))]
'''),
    ('firma_denetim.py', 'RN3 · firma_denetim.py blok 3',
     r'''#
# Ölçüldü (RN2): kök `HR-{kisaltma}{yil}-` idi, firma kodu yoktu.
''',
     r'''#
# Ölçüldü (RN3): kök `HR-{kisaltma}{yil}-` idi, firma kodu yoktu.
'''),
    ('tests/test_kritik.py', 'RN3 · tests/test_kritik.py blok 1',
     r'''    sid1 = r1.get_json()['id']
    assert sid1.startswith('SIP-STN'), sid1
''',
     r'''    sid1 = r1.get_json()['id']
    # RN3: eskiden `startswith('SIP-STN')` yazıyordu — yani `SIP-` ile
    # cari kısaltması ARASINDA hiçbir şey olmadığını varsayıyordu.
    # Firma belge kodu köke girince kimlik `SIP-MLS-STN26-01` oluyor
    # ve test ÜRÜN DOĞRU ÇALIŞTIĞI HALDE kırılıyordu. Sınanacak şey
    # kısaltmanın kimlikte GEÇMESİ, kaçıncı karakterde olduğu değil.
    _p1 = sid1.split('-')
    assert _p1[0] == 'SIP', sid1
    assert any(p.startswith('STN') for p in _p1[1:]), sid1
'''),
    ('tests/test_kritik.py', 'RN3 · tests/test_kritik.py blok 2',
     r'''    assert rp.status_code == 200, rp.get_data(as_text=True)
    assert rp.get_json()['id'].startswith('PI-STN'), rp.get_json()['id']
''',
     r'''    assert rp.status_code == 200, rp.get_data(as_text=True)
    # RN3: `startswith('PI-STN')` de aynı sabit konum varsayımıydı
    # (firma kodlu hâli PI-MLS-STN26-01). Parçaya bakıyoruz.
    _pid = rp.get_json()['id']
    _pp = _pid.split('-')
    assert _pp[0] == 'PI', _pid
    assert any(p.startswith('STN') for p in _pp[1:]), _pid
'''),
    ('tests/test_kritik.py', 'RN3 · tests/test_kritik.py blok 3',
     r'''        h = CariHareket.query.filter_by(cari_id='CRN').first()
        assert h.id.startswith('HR-STN26-'), h.id
''',
     r'''        h = CariHareket.query.filter_by(cari_id='CRN').first()
        # RN3: bu üretecin kökü firma kodunu taşıyor artık
        # (HR-MLS-STN26-0001). Sabit önek varsayımı burada da kalkıyor.
        _hp = h.id.split('-')
        assert _hp[0] == 'HR', h.id
        assert any(p.startswith('STN26') for p in _hp[1:]), h.id
        assert _hp[-1].isdigit(), h.id
'''),
    ('tests/test_kritik.py', 'RN3 · tests/test_kritik.py blok 4',
     r'''    assert all(n.endswith('-01') for n in numaralar), numaralar
    assert numaralar[0][4:7] != numaralar[1][4:7], numaralar
''',
     r'''    assert all(n.endswith('-01') for n in numaralar), numaralar

    # RN3: eskiden `[4:7]` sabit dilimi karşılaştırılıyordu. Firma
    # belge kodu köke girince o dilim kodun kendisi oluyor (ikisinde
    # de aynı) ve test ürün doğru çalıştığı halde kırılıyordu:
    #   ['SIP-MLS-GRN26-01', 'SIP-MLS-GRT26-01'] → 'MLS' != 'MLS'
    # Kısaltma kimliğin SONDAN İKİNCİ parçasında ve orada yılı da
    # taşıyor; konumdan bağımsız okumak için oradan alıyoruz.
    _kis = [n.split('-')[-2] for n in numaralar]
    assert _kis[0] != _kis[1], (numaralar, _kis)
'''),
]


def main():
    print('=' * 70)
    print('  YAMA RN3 — BELGE KODU AYARLARDAN DÜZENLENEBİLİR')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    gruplar = {}
    for dosya, aciklama, eski, yerine in DEGISIKLIKLER:
        gruplar.setdefault(dosya, []).append((aciklama, eski, yerine))

    sonuclar, hata, zaten = {}, False, []

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
        print('  ⊙ Yama RN3 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_rn3.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_rn3'
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
    print('    sudo systemctl restart milestone-erp')
    print()
    print('  SONRA:')
    print('    venv/bin/python firma_denetim.py')
    print('    venv/bin/python -m pytest tests/test_kritik.py -q')
    print()
    print('  Ardından Ayarlar → Firma bölümünde "Belge Kodu" alanı')
    print('  görünecek. MLS yazıp kaydet; yeni belgeler o kodu taşır:')
    print('      SIP-MLS-STN26-01 · HR-MLS-STN26-0001')
    print()
    print('  Tarayıcıda Ctrl+F5 — eski form şablonu önbellekte kalırsa')
    print('  alan görünmez.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

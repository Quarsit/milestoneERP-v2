#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA AS1 — ÖLÜ KOPYALAR SİLİNDİ · MÜKERRER SLAB KAPISI · API SINIRI
====================================================================

ÖNKOŞUL: **yama_ts1.py uygulanmış olmalı.** Betik denetliyor.
Şema yok, göç yok.

Senin üç kararın: ölü kopyaları sil · `toplu_import` için sistemin
hata üretmesini engelleyecek yol neyse onu yap · bilinçli onay
mükerreri geçmesin. Hepsi burada, artı API sınırı taramasının
bulduğu bir şey.

═══ 1 · DÖRT ÖLÜ UÇ SİLİNDİ ═══

Hiçbir ekran çağırmıyordu, her biri ikinci bir doğruluk kaynağıydı:

  · `GET /api/uretici` — üretici listesi `/api/cari` süzülerek
    kuruluyor. İki ayrı "üretici kimdir" tanımı vardı.
  · `GET /api/musteri/detay` — TÜM carileri süzgeçsiz döndürüyordu.
  · `GET /api/yetkilerim` — yetkiler sunucudan şablona geçiyor
    (`menu_yetki`). İki muafiyet listesinden de çıkarıldı.
  · `POST /api/stok/toplu_import` — aşağısı.

═══ 2 · toplu_import: ÖLÇÜM İDDİAYI ÇÜRÜTTÜ ═══

Ekranı buna bağlayıp döngüden kurtulmayı düşündük. ÖLÇTÜM — aynı
iki plaka, iki yol:

      alan          /api/stok/ekle     toplu_import
      ─────────────────────────────────────────────
      mense         ALBANIA            TURKIYE      ✗
      alis_tipi     ithalat            —            ✗
      fatura_no     IM-FTR-1           —            ✗
      cari_id       TED-IM             —            ✗
      uretici       TEDARIKCI IM       —            ✗

Bu uç KM1 ve KK1'den ÖNCE yazılmış: üst düzey alanları hiç
okumuyor. Ekranı ona bağlamak **KM1'de düzelttiğimiz yanlış menşe
beyanını geri getirirdi** — Arnavutluk mermeri ticari faturada Türk
malı olarak çıkardı.

Sen "sistemin hata üretmesini engelleyecek yol neyse onu yapalım,
hız sorun değil" dedin. O yol silmek: duran bir kopya, ileride
birinin onu bağlaması demek. Ortak bir yardımcıya çıkarıp tek
kaynak yapmak da mümkündü ama stok oluşturma yolunun tamamına
dokunurdu ve kazanç yalnız hızdı.

═══ 3 · AMA BİR KORUMA O UÇTA YAŞIYORDU ═══

Silmeden önce testlerine baktım ve biri şunu tutuyordu: *aynı blok
+ aynı slab no ikinci kez stoğa alınamaz.* O kural `toplu_import`'un
doğrulayıcısındaydı ve **başka hiçbir yerde yoktu.**

ÖLÇÜLDÜ — ekranın kullandığı `/api/stok/ekle`:

      1. deneme → 200   PLK-MK-1-01
      2. deneme → 200   PLK-MK-1-002     ← aynı slab, ikinci kayıt

Aynı taş iki kez stokta görünüyor, yani iki kez satılabilir. Ekran
kendi tarafında süzüyor (mevcut plakaları çekip en büyük numarayı
hesaplıyor) — ama tarayıcıda yapılan bir denetim denetim değildir:
ikinci bir sekme, doğrudan bir API çağrısı ya da eşzamanlı iki
kayıt onu atlar.

Kural `/api/stok/ekle`ye taşındı. **HEPSİ YA HİÇBİRİ:** `adet`
kadar slab'ın tamamı önceden denetlenir; yarısını yazıp durmak
hangi numaradan devam edileceğini bilinmez hâle getirirdi.

  Bilinçli onay (`blok_uyarisi_onaylandi`) bu kuralı GEÇMİYOR —
  senin kararın. O onay "blok hâlâ stokta" uyarısını geçer; aynı
  taşı iki kez yazma iznini vermez. UR1 testinde "numara tekrarı
  olabilir" diye bir yorum vardı, artık doğru değil; test
  çakışmayan bir numara kullanıyor ve yorum düzeltildi.

═══ 4 · BL17 TESTLERİNE NE OLDU ═══

Üçü de silinen ucu koşuyordu. Konuları:

  1. hepsi-ya-hiçbiri + satır satır gerekçe  → uca özgüydü; ekranın
     döngüsü bunu JS tarafında yapıyor. **Bu kapsam kaybı bilerek
     kabul edildi.**
  2. `kismi` ile kısmi aktarım               → aynı şekilde.
  3. aynı slab ikinci kez girilemez          → KORUMA TAŞINDI,
     testi `/api/stok/ekle` üzerinde yeniden yazıldı.

Yani silme işlemi bir koruma kaybetmedi; iki tane uca-özgü test
kaybetti.

═══ 5 · API SINIRI TARAMASI ═══

Yeni bir sınıf taradım: ekranın okuduğu ama sunucunun hiç
göndermediği alan. JS `undefined` verir — alan boş görünür, sayıysa
NaN, toplamaya girerse satır bozulur. Ne hata ne uyarı.

BULGU: `/api/avans/devret` `doviz` göndermiyordu; ekran devirden
sonra "Kalan avans: 5.000,00" diye **para birimi olmadan** yazıyordu
(siparis.html `d.doviz` okuyor). USD ve EUR ile çalışan bir yerde o
sayı tek başına hangi para olduğunu söylemiyor. Alan eklendi.

**TARAMANIN KENDİSİNDE DÖRT KUSUR BULDUM**, hepsi ölçerek:

  · sabit 60 satırlık pencere bir sonraki fonksiyona taşıyordu ve
    orada aynı `d` adı başka bir ucu okuyordu → 62 adayın çoğu
    oradan geliyordu. Artık kuşatan blok süslü parantez sayılarak
    bulunuyor.
  · en-uzun-önek eşlemesi `/…/eposta` çağrısını `/…/eposta/test`
    ucuna bağlıyordu → segment sayısı artık eşit olmalı.
  · `X.data || X.bankalar || []` savunma zincirleri aday
    sayılıyordu → ilk alternatif geçerliyse gerisi muaf.
  · LİSTE dönen uçların yanıtında top-level anahtar yoktur; iç
    sözlüğün anahtarlarını yanıtın anahtarları saymak her erişimi
    "eksik" gösteriyordu → liste dönen uçlar denetim dışı.

62 → 13 → 10 → 1. İlk "temiz" sonuçlar şanstı. Bunu yazıyorum ki bu
bekçi bir gün patlarsa önce KENDİSİNDEN şüphe edilsin.

═══ 6 · KENDİ TESTİMİ SİLDİM ═══

Avans `doviz` alanı için bir kaynak denetimi yazmıştım. Ölçtüm:
**düzeltme olmadan da geçiyordu**, çünkü aynı dizgi denetim izi
satırında da var (`yeni={'hedef': …, 'doviz': doviz}`). Yanlış yeri
yakalıyordu — hatayı gösterecek test, hatayı saklayacaktı.

Sildim. O alanı AS2 bekçisi zaten davranış olarak tutuyor: alanı
geri aldığım bir kopyada patladı. Aynı şeyi iki yerden tutmanın
anlamı yok, hele biri yanlış tutuyorsa.

═══ DOĞRULANDI ═══
  270 test geçti (269 + 4 yeni − 3 silinen BL17). Yeni testlerin
  üçü taban üzerinde BAŞARISIZ oluyor; AS2 bekçisi `doviz` alanı
  geri alınınca patlıyor.

  pyflakes: tanımsız ad yok, uyarı sayısı tabanla aynı.

DOSYALAR
--------
  flask_app.py           4 uç silindi · mükerrer kapısı · doviz alanı
  tests/test_kritik.py   3 BL17 testi → 3 AS1 testi + AS2 bekçisi

KULLANIM
--------
  python3 yama_as1.py            # RAPOR
  python3 yama_as1.py --uygula
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
    'flask_app.py': 'AS1 · AYNI SLAB İKİ KEZ GİRİLEMEZ',
    'tests/test_kritik.py': 'def test_as2_ekranin_okudugu_alani_sunucu_gonderiyor',
}
ONKOSUL = {
    'flask_app.py': 'TS1 · İKİ SİLME YOLU, İKİ FARKLI GERÇEK',
    'tests/test_kritik.py': 'def test_ts1_iki_silme_yolu_ayni_sonucu_veriyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'AS1 · flask_app.py blok 1',
     r'''        '/api/yetkilerim',
''',
     r''''''),
    ('flask_app.py', 'AS1 · flask_app.py blok 2',
     r'''        '/api/yetkilerim',        # kullanıcının kendi yetkileri
''',
     r''''''),
    ('flask_app.py', 'AS1 · flask_app.py blok 3',
     r'''                m2 = (boy * yuk) / 10000
''',
     r'''                m2 = (boy * yuk) / 10000

                # ══════════════════════════════════════════════════
                #  AS1 · AYNI SLAB İKİ KEZ GİRİLEMEZ
                #
                #  Bir slab FİZİKSEL bir parça: aynı blok no ve slab
                #  no ile iki kayıt varsa aynı taş iki kez stokta
                #  görünür ve iki kez satılabilir.
                #
                #  Bu koruma YALNIZCA silinen `toplu_import` ucunun
                #  doğrulayıcısında yaşıyordu. ÖLÇÜLDÜ — `/api/stok/
                #  ekle` aynı MK-1/1 plakasını iki kez kabul etti ve
                #  stokta iki kayıt oluştu. Ekran kendi tarafında
                #  süzüyor (mevcut plakaları çekip en büyük numarayı
                #  hesaplıyor), ama tarayıcıda yapılan bir denetim
                #  denetim değildir: ikinci bir sekme, doğrudan bir
                #  API çağrısı ya da eşzamanlı iki kayıt onu atlar.
                #
                #  HEPSİ YA HİÇBİRİ: `adet` kadar slab'ın TAMAMI
                #  önceden denetlenir. Yarısını yazıp durmak, hangi
                #  numaradan devam edeceğini bilinmez hale getirir.
                # ══════════════════════════════════════════════════
                _blok_no = (data.get('blok_no') or '').strip()
                if _blok_no:
                    _bas = int(_sayi('baslangic_no', 1))
                    if _bas < 0:
                        _bas = 0
                    _istenen = [_bas + i for i in range(adet)]
                    _varolan = {
                        s.slab_no for s in PlakaStok.query.filter(
                            db.func.upper(PlakaStok.blok_no)
                            == _blok_no.upper(),
                            PlakaStok.slab_no.in_(_istenen)).all()}
                    if _varolan:
                        _liste = ', '.join(str(x) for x in sorted(_varolan))
                        return jsonify({
                            'ok': False, 'error': 'mukerrer_slab',
                            'mukerrer': sorted(_varolan),
                            'mesaj': f'{_blok_no} bloğunun {_liste} '
                                     f'numaralı plakası depoda zaten var. '
                                     f'Aynı slab iki kez girilirse aynı taş '
                                     f'iki kez satılabilir. Başlangıç '
                                     f'numarasını değiştirin ya da mevcut '
                                     f'kaydı düzeltin.'}), 400
'''),
    ('flask_app.py', 'AS1 · flask_app.py blok 4',
     r'''    def _plaka_satir_denetle(p, sira, gorulen_anahtarlar):
        """Tek satırı denetler. Döner: (temiz_sozluk, hata_metni)."""
        def _sayi(ad, zorunlu=True, en_az=0.0, en_cok=None):
            ham = p.get(ad)
            if ham in (None, ''):
                return (None, f'{ad} boş') if zorunlu else (None, None)
            try:
                d = float(str(ham).replace(',', '.'))
            except (TypeError, ValueError):
                return None, f'{ad} sayı değil: "{ham}"'
            if d <= en_az:
                return None, f'{ad} sıfır ya da negatif: {d}'
            if en_cok is not None and d > en_cok:
                return None, f'{ad} makul sınırın üstünde: {d}'
            return d, None

        cins = (p.get('cins') or '').strip()
        if not cins:
            return None, 'cins boş — cinssiz plaka hiçbir listede doğru görünmez'
        blok_no = (p.get('blok_no') or '').strip()
        if not blok_no:
            return None, 'blok no boş — izi sürülemez, kaynağı bilinmez'

        # Olcu sinirlari: 1000 cm = 10 m. Bundan buyugu veri hatasidir
        # (santim yerine milimetre girilmis olabilir).
        boy, h = _sayi('boy', en_cok=1000)
        if h:
            return None, h
        yuk, h = _sayi('yukseklik', en_cok=1000)
        if h:
            return None, h
        kalinlik, h = _sayi('kalinlik', zorunlu=False, en_cok=100)
        if h:
            return None, h
        fiyat, h = _sayi('alis_fiyati', zorunlu=False)
        if h and 'sıfır ya da negatif' not in h:
            return None, h
        if fiyat is None:
            fiyat = 0.0

        doviz = (p.get('doviz') or 'USD').strip().upper()
        if doviz not in ICE_AKTAR_DOVIZLER:
            return None, (f'döviz tanınmadı: "{doviz}" '
                          f'(geçerli: {", ".join(ICE_AKTAR_DOVIZLER)})')

        slab_no = p.get('slab_no')
        try:
            slab_no = int(slab_no) if slab_no not in (None, '') else None
        except (TypeError, ValueError):
            return None, f'plaka no sayı değil: "{p.get("slab_no")}"'

        # Ayni blok + ayni plaka no iki kez gelemez: hem dosya
        # icinde hem DEPODA kontrol edilir. Ayni plakayi iki kez
        # stoga almak, ayni mali iki musteriye satmaya goturur.
        if slab_no is not None:
            anahtar = (blok_no.upper(), slab_no)
            if anahtar in gorulen_anahtarlar:
                return None, (f'aynı dosyada tekrar eden plaka: '
                              f'{_plaka_kodu(blok_no, slab_no)}')
            varolan = PlakaStok.query.filter(
                db.func.upper(PlakaStok.blok_no) == blok_no.upper(),
                PlakaStok.slab_no == slab_no).first()
            if varolan:
                return None, (f'bu plaka depoda zaten var: '
                              f'{_plaka_kodu(blok_no, slab_no)} ({varolan.id})')
            gorulen_anahtarlar.add(anahtar)

        m2 = (boy * yuk) / 10000
        return {
            'cins': cins, 'blok_no': blok_no, 'boy': boy, 'yukseklik': yuk,
            'kalinlik': kalinlik, 'slab_no': slab_no,
            'uretici': (p.get('uretici') or '').strip(),
            'ozellik': (p.get('ozellik') or '').strip(),
            'konum': (p.get('konum') or '').strip(),
            'alis_fiyati': q2(fiyat), 'doviz': doviz,
            'metraj_m2': q2(m2), 'metraj_sqft': q2(m2 * 10.764),
            'aciklama': (p.get('aciklama') or '').strip(),
        }, None

    @app.route('/api/stok/toplu_import', methods=['POST'])
    def api_stok_toplu_import():
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        data = request.get_json(silent=True) or {}
        plakalar = data.get('plakalar', [])
        if not plakalar:
            return jsonify({'ok': False, 'mesaj': 'Plaka listesi boş'}), 400
        if not isinstance(plakalar, list):
            return jsonify({'ok': False, 'mesaj': 'Plaka listesi dizi olmalı'}), 400
        if len(plakalar) > 5000:
            return jsonify({'ok': False,
                'mesaj': f'Tek seferde en çok 5000 satır alınır '
                         f'(gelen: {len(plakalar)}). Dosyayı bölün.'}), 400

        kismi = bool(data.get('kismi'))
        temizler, hatalar, gorulen = [], [], set()
        for i, p in enumerate(plakalar, start=1):
            if not isinstance(p, dict):
                hatalar.append({'satir': i, 'hata': 'satır nesne değil'})
                continue
            temiz, hata = _plaka_satir_denetle(p, i, gorulen)
            if hata:
                hatalar.append({'satir': i, 'hata': hata,
                                'blok_no': (p.get('blok_no') or ''),
                                'slab_no': p.get('slab_no')})
            else:
                temizler.append((i, temiz))

        # ── HEPSİ YA HİÇBİRİ (varsayılan) ──
        if hatalar and not kismi:
            return jsonify({
                'ok': False, 'error': 'satir_hatalari',
                'toplam': len(plakalar), 'gecerli': len(temizler),
                'hatali': len(hatalar), 'hatalar': hatalar[:100],
                'mesaj': f'{len(plakalar)} satırın {len(hatalar)} tanesi hatalı — '
                         f'HİÇBİRİ eklenmedi. Hataları düzeltip tekrar '
                         f'deneyin; sağlam satırları yine de almak '
                         f'isterseniz "kısmi aktarım" seçeneğini kullanın.'}), 400

        if not temizler:
            return jsonify({'ok': False, 'error': 'gecerli_satir_yok',
                'toplam': len(plakalar), 'hatali': len(hatalar),
                'hatalar': hatalar[:100],
                'mesaj': 'Hiçbir satır geçerli değil, ekleme yapılmadı.'}), 400

        damga = datetime.now().strftime('%Y-%m-%d %H:%M')
        kullanici = session.get('kullanici') or 'sistem'
        eklenen, eklenen_idler = 0, []
        try:
            for _sira, t in temizler:
                plaka = PlakaStok(
                    id=_stok_okunur_id('PLK', PlakaStok, t['blok_no'],   # RN1
                                       t['slab_no']),
                    uretici=t['uretici'], cins=t['cins'], blok_no=t['blok_no'],
                    slab_no=t['slab_no'],
                    boy=t['boy'], yukseklik=t['yukseklik'], kalinlik=t['kalinlik'],
                    ozellik=t['ozellik'],
                    metraj_m2=t['metraj_m2'], metraj_sqft=t['metraj_sqft'],
                    alis_fiyati=t['alis_fiyati'], doviz=t['doviz'],
                    konum=t['konum'], durum='Serbest',
                    aciklama=t['aciklama'] or f'Toplu import - {damga}',
                    kullanici=kullanici)
                db.session.add(plaka)
                db.session.flush()
                eklenen += 1
                eklenen_idler.append(plaka.id)
            _log_audit('EKLE', 'stok', f'toplu:{eklenen}',
                       yeni={'eklenen': eklenen, 'atlanan': len(hatalar),
                             'kismi': kismi},
                       aciklama=f'Toplu plaka aktarimi ({damga})')
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.exception('Toplu stok aktarimi basarisiz')
            return jsonify({'ok': False, 'error': 'yazma_hatasi',
                'mesaj': f'Kayit sirasinda hata, HICBIRI eklenmedi: {e}'}), 500

        mesaj = f'{eklenen} plaka eklendi'
        if hatalar:
            mesaj += f' · {len(hatalar)} satır ATLANDI (gerekçeleri listede)'
        return jsonify({'ok': True, 'eklenen': eklenen,
                        'toplam': len(plakalar), 'atlanan': len(hatalar),
                        'hatalar': hatalar[:100], 'idler': eklenen_idler[:50],
                        'mesaj': mesaj})
''',
     r'''
    # ══════════════════════════════════════════════════════════
    #  AS1 · `POST /api/stok/toplu_import` SİLİNDİ
    #
    #  Hiçbir ekran çağırmıyordu: Excel içe aktarma modalı satır
    #  satır `/api/stok/ekle` çağırıyor. Üç testi vardı, o yüzden
    #  "çalışıyor" görünüyordu.
    #
    #  Ekranı buna bağlamayı düşündük. ÖLÇÜLDÜ — aynı iki plaka, iki
    #  yol, 5 alan ayrışıyor:
    #
    #      alan          /api/stok/ekle     toplu_import
    #      ─────────────────────────────────────────────
    #      mense         ALBANIA            TURKIYE      ✗
    #      alis_tipi     ithalat            —            ✗
    #      fatura_no     IM-FTR-1           —            ✗
    #      cari_id       TED-IM             —            ✗
    #      uretici       TEDARIKCI IM       —            ✗
    #
    #  Bu uç KM1 ve KK1'den ÖNCE yazılmış: üst düzey alanları
    #  (`uretici`, `cari_id`, `mense`, `alis_tipi`, `fatura_no`,
    #  `kdv_*`, `kaynak`) hiç okumuyor. Ekranı ona bağlamak,
    #  KM1'de düzelttiğimiz YANLIŞ MENŞE BEYANINI geri getirirdi —
    #  Arnavutluk mermeri ticari faturada Türk malı olarak çıkardı.
    #
    #  Ortak bir yardımcıya çıkarıp tek kaynak yapmak da bir
    #  seçenekti; Bahadır hızın sorun olmadığını söyledi (bir
    #  Excel'de en çok birkaç yüz satır), o yüzden ikinci ve
    #  güncelliğini yitirmiş oluşturma yolunu TUTMAK yerine
    #  SİLMEYİ seçtik. Duran bir kopya, ileride birinin onu
    #  bağlaması demek.
    #
    #  `_plaka_satir_denetle` de silindi — yalnız bu uç
    #  kullanıyordu.
    # ══════════════════════════════════════════════════════════
'''),
    ('flask_app.py', 'AS1 · flask_app.py blok 5',
     r'''        return jsonify({'ok': True,
            'mesaj': f'{tutar:,.2f} {doviz} avans {kaynak_sip_id} → {hedef_sip_id} siparişine devredildi.'})
''',
     r'''        # AS1: `doviz` ALANI DA GONDERILIYOR.
        # Ekran devirden sonra "Kalan avans: X" yaziyor ve para
        # birimini `d.doviz`den okuyor (siparis.html 1427). Uc bunu
        # hic gondermiyordu: mesaj PARA BIRIMI OLMADAN cikiyordu.
        # USD ve EUR ile calisan bir yerde "5.000,00" tek basina
        # hangi para oldugunu soylemiyor.
        return jsonify({'ok': True, 'doviz': doviz, 'tutar': q2(tutar),
            'mesaj': f'{tutar:,.2f} {doviz} avans {kaynak_sip_id} → {hedef_sip_id} siparişine devredildi.'})
'''),
    ('flask_app.py', 'AS1 · flask_app.py blok 6',
     r'''    @app.route('/api/musteri/detay')
    def api_musteri_detay():
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        return jsonify([{'unvan': c.unvan, 'adres': c.adres, 'ulke': c.ulke} for c in Cari.query.all()])

    @app.route('/api/uretici')
    def api_uretici():
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        # Ureticiler artik Cari tablosundan gelir: urun_tedarikcisi=True olan cariler
        ureticiler = Cari.query.filter_by(urun_tedarikcisi=True).order_by(Cari.unvan).all()
        return jsonify([
            {'id': c.id, 'deger': c.unvan, 'kisaltma': c.uretici_kisaltma or c.unvan[:3].upper()}
            for c in ureticiler
        ])
''',
     r'''    # AS1: `GET /api/musteri/detay` SİLİNDİ. Hiçbir ekran
    # çağırmıyordu; TÜM carilerin unvan/adres/ülkesini süzgeçsiz
    # döndürüyordu — `/api/musteri` ve `/api/cari` aynı işi erişim
    # süzgeciyle yapıyor.

    # AS1: `GET /api/uretici` SİLİNDİ. Hiçbir ekran çağırmıyordu;
    # üretici listesi `/api/cari` süzülerek kuruluyor (stok.html,
    # `cariUreticiMi`). İki ayrı "üretici kimdir" tanımı vardı —
    # burada `urun_tedarikcisi=True`, ekranda başka bir ölçüt — ve
    # ikisi zamanla ayrışabilirdi.
'''),
    ('flask_app.py', 'AS1 · flask_app.py blok 7',
     r'''    @app.route('/api/yetkilerim', methods=['GET'])
    def api_yetkilerim():
        """Aktif kullanıcının kendi yetkilerini döner (frontend menü/buton kontrolü için)."""
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        return jsonify({
            'ok': True,
            'kullanici': session.get('kullanici'),
            'rol': session.get('rol'),
            'admin': session.get('rol') in ('admin', 'ADMIN'),
            'yetkiler': _kullanici_yetkileri(),
            'proforma_onay': _proforma_onay_yetkisi_var_mi(),
            'moduller': YETKI_MODULLERI
        })
''',
     r'''    # AS1: `GET /api/yetkilerim` SİLİNDİ. Hiçbir ekran
    # çağırmıyordu: menü ve düğme görünürlüğü sunucu tarafından
    # şablona geçen `menu_yetki` ile kuruluyor (base.html). İki
    # ayrı yetki kaynağı tutmak, birinin diğerinden ayrışması
    # demekti.
'''),
    ('tests/test_kritik.py', 'AS1 · tests/test_kritik.py blok 1',
     r'''def test_bl17_toplu_import_hatali_satiri_sessizce_atlamaz():
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
''',
     r'''# ══════════════════════════════════════════════════════════════════
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
    r2 = c.post('/api/stok/ekle', headers=H, json=dict(govde))
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
'''),
    ('tests/test_kritik.py', 'AS1 · tests/test_kritik.py blok 2',
     r'''    # Bilinçli onay geçişe izin verir (numara tekrarı olabilir).
    r3 = c.post('/api/stok/ekle', headers=H,
                json=dict(govde, blok_uyarisi_onaylandi=True))
''',
     r'''    # Bilinçli onay geçişe izin verir.
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
'''),
    ('tests/test_kritik.py', 'AS1 · tests/test_kritik.py blok 3',
     r'''        'kasa geri alma hatayı yutuyor — yarım iş sessizce geçer'
''',
     r'''        'kasa geri alma hatayı yutuyor — yarım iş sessizce geçer'


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
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA AS1 — ÖLÜ KOPYALAR SİLİNDİ · MÜKERRER SLAB KAPISI · API SINIRI')
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
        print('    python3 yama_as1.py            # rapor')
        print('    python3 yama_as1.py --uygula')
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
        print('  ⊙ Yama AS1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_as1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_as1'
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
    print('    2) venv/bin/python -m pytest tests/test_kritik.py -q   # 270')
    print()
    print('  BAKILACAK YER')
    print('    1. Stok -> ayni blok + ayni slab numarasini ikinci kez')
    print('       girmeyi dene: artik reddediyor ve hangi numaralarin')
    print('       dolu oldugunu yaziyor.')
    print('    2. Excel toplu ice aktarma: HIC DEGISMEDI, ayni yoldan')
    print('       calisiyor. Yalniz kullanilmayan ikinci uc silindi.')
    print('    3. Siparis -> avans devri: devirden sonraki "Kalan')
    print('       avans" mesaji artik para birimini yaziyor.')
    print()
    print('  RAKAM DEGISMIYOR')
    print('    Mevcut kayitlara dokunulmadi. Stokta ONCEDEN olusmus')
    print('    mukerrer slab varsa kendiliginden duzelmez; bundan')
    print('    sonra yenisi olusamaz.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

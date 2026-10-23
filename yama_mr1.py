#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MR1 — MALİYET RAPORLARI
=============================

ÖNKOŞUL: VT1 ve MG1 uygulanmış olmalı — betik bunu kendisi
denetliyor, eksikse HİÇBİR dosyaya dokunmadan çıkıyor. (MG2 yalnız
stok.html'e dokunduğu için burada bir çapası yok; sırayla uyguladın,
sorun değil.)

"Bir bloğun ya da plakaların maliyet raporu, bir satışın maliyeti
ve kârlılığı… bunların bazıları sistemde farklı yerlerde mevcut
ama pratik olarak ulaşmak zor" dedin. Doğruymuş — ve ulaşmayı
kolaylaştırırken rakamların kendisinde dört ayrı sorun çıktı.

── 1 · ÖNCE BULUNANLAR ──

  "Bu stoğun maliyeti ne?" sorusu DÖRT ayrı yerde hesaplanıyordu
  ve hiçbiri diğeriyle aynı değildi:

                          iptal edilmiş   tipsiz gider
                          gideri sayıyor  sayıyor
    satış kârı                 ✗ evet        ✗ hayır
    kesim dağıtıcısı           ✗ evet        ✗ hayır
    kesimin kendisi            ✗ evet        ✗ hayır
    sipariş kârlılığı          ✗ evet        ✗ hayır
    ortaklık hesabı            ✓ hayır       ✓ evet

  Ortaklık kodunda bu iki süzgecin gerekçesi YAZILIYDI —
  "uygulamanın geri kalanı onları her yerde süzüyor" — ama doğru
  değilmiş, yalnız orada varmış.

  ÖLÇÜLDÜ:
    · 400 USD'lik İPTAL bir gider yüzünden blok 7.550 USD iken
      plakalara 7.950 dağıtılıyordu. Birim maliyet 736,11 yerine
      699,07 olmalıydı.
    · 250 USD'lik TİPSİZ bir gider satışın maliyetine hiç
      girmiyordu; o satışın kârı 250 USD fazla görünüyordu.

  Hepsi tek kaynağa bağlandı: `_stok_maliyet_dokumu`.

── 2 · SATILMIŞ PLAKANIN KÂRI TAZELENMİYORDU ──
  Bloğa maliyet eklenince plakaların birim maliyeti yeniden
  dağıtılıyor ama SATILMIŞ bir plakanın kâr kaydı eski maliyetle
  kalıyordu: stok kartı yeni rakamı gösterirken kârlılık raporu
  eskisini gösteriyordu.

  Bunu satış dökümü ucunu yazarken yakaladım — eklediğim
  `tutarsizlik` alanı ilk denemede kayıtta 0,00 USD maliyet
  dururken hesaplananın 3.774,98 USD olduğunu söyledi.

  DZ4'te aynı tazeleme ÖLÇÜ değişimi için konmuştu; maliyet
  eklenmesi için konmamıştı. Artık o da tazeleniyor.

── 3 · STOK MALİYET RAPORU (yeni sekme) ──
  Raporlar → **Stok Maliyeti**.

  Bloklar başlık, kesimden çıkanlar onların altında — bloğun
  matrahının hangi plakalara dağıldığı bir arada okunuyor. Düz
  liste olsaydı kesim ilişkisi kaybolurdu.

  Her kutuda: alış bedeli, maliyet kalemleri (belge no ve kendi
  dövizi ile), toplam, birim maliyet. Devreden/İade KDV ayrı bir
  satırda "maliyet dışı" diye gösteriliyor — "neden toplamda yok"
  sorusunun cevabı görünsün diye.

  Kesimden GELMEYEN (doğrudan girilmiş) ürünler ayrı başlıkta:
  bloğun altına koymak yanlış olurdu.

  Süzgeçler: tip · cins · üretici · durum · blok no · giriş tarihi.

  Ölçüsü girilmemiş stokta birim maliyet SIFIR yazılmıyor, "ölçü
  yok" deniyor — sıfır "maliyeti yok" demek olurdu.

── 4 · SATIŞIN MALİYET DÖKÜMÜ ──
  Kârlılık sekmesindeki satış satırına tıkla, o satışın dökümü
  altında açılıyor: stok, alış bedeli, kalem kalem maliyetler,
  toplam, satış, kâr, marj. İkinci tık kapatıyor.

  Kayıttaki maliyet ile şu an hesaplanan ayrışıyorsa bunu AÇIKÇA
  söylüyor — sessiz bırakmıyoruz.

── 5 · EXCEL VE YAZDIR ──
  Excel, raporun KENDİ ucundan besleniyor; ayrı bir sorgu yazmak
  iki rakam demekti. Yazdırmada sekmeler ve süzgeçler gizleniyor,
  yalnız açık bölüm ve tüm dökümler basılıyor.

── ÖLÇÜLDÜ (yamadan sonra) ──
      blok 7.550 USD → plakalara 7.550 dağıtıldı        ✓
      iptal edilmiş gider kalemlerde yok                ✓
      tipsiz gider kalemlerde var                       ✓
      Devreden KDV ayrı başlıkta                        ✓
      satış dökümü ile kayıt aynı (tutarsizlik: None)   ✓
      Excel 200 · geçerli xlsx                          ✓
      tarayıcı: sekme açılıyor, kutular açılıp kapanıyor,
                satış satırı dökümü açıyor, JS hatası yok

  220 test geçti (213 + 7); iki ayrı koşuda da aynı.
  firma · js · form · zincir · akis denetimleri temiz.

── DOKUNMADIĞIM İKİ ŞEY, İKİSİ DE SENİN KARARIN ──

  a) KESİM YOLU PARA BİRİMİ KARIŞTIRIYOR. Stoğun `matrah` değeri
     kendi dövizinde ama USD gibi işleniyor, üstüne USD cinsinden
     ek maliyetler ekleniyor. Oluşan plakaya da bloğun dövizi
     yazılıyor. USD blokta sorun yok; TL/EUR blokta birim maliyet
     yanlış. Düzeltmek mevcut rakamları oynatır.

  b) SİPARİŞ kimliğine bağlı maliyet toplamalarında da `aktif`
     süzgeci yok (sipariş kârlılığı, fatura kârlılığı). Bunlar
     STOK değil SİPARİŞ sorusu soruyor; düzeltmek o raporların
     rakamlarını oynatır.

DOSYALAR
--------
  flask_app.py            tek kaynak · stok maliyet raporu ·
                          satış dökümü · Excel · tazeleme
  templates/raporlar.html Stok Maliyeti sekmesi · açılır döküm ·
                          yazdırma stili
  tests/test_kritik.py    7 yeni test

Şema yok, göç yok, yeni alan yok.

KULLANIM
--------
  python3 yama_mr1.py            # RAPOR
  python3 yama_mr1.py --uygula
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
    'flask_app.py': 'MR1 · STOK MALİYET RAPORU',
    'templates/raporlar.html': 'data-b="stokmaliyet"',
    'tests/test_kritik.py': 'def test_mr1_iptal_edilmis_gider_maliyete_girmiyor',
}
ONKOSUL = {
    'flask_app.py': 'VT1 · VADE YALNIZ BORÇ DOĞURAN TİPLERDE',
    'templates/raporlar.html': 'data-b="maliyetanaliz"',
    'tests/test_kritik.py': 'def test_mg1_maliyetler_tipe_gore_gruplaniyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'MR1 · flask_app.py blok 1',
     r'''            ek_maliyet_usd += db.session.query(db.func.sum(Maliyet.usd_karsilik)).filter(
                Maliyet.baglanti_id.in_(stok_idler),
                ~Maliyet.maliyet_tip.in_(['Devreden KDV', 'Iade KDV'])
            ).scalar() or 0
            ek_maliyet_try += db.session.query(db.func.sum(Maliyet.try_karsilik)).filter(
                Maliyet.baglanti_id.in_(stok_idler),
                ~Maliyet.maliyet_tip.in_(['Devreden KDV', 'Iade KDV'])
''',
     r'''            # MR1 · IKI SUZGEC: `aktif=False` iptal edilmis maliyettir,
            # `~tip.in_` tek basina ise tipi BOS satiri da eler (SQL'de
            # NULL NOT IN (...) → NULL). Ayni soru `_stok_maliyet_kalemleri`
            # ile soruluyor; burada TRY karsiligi da gerektigi icin
            # sorgu yerinde kaldi ama SUZGECLER ayni.
            _mr1 = db.or_(Maliyet.maliyet_tip.is_(None),
                          ~Maliyet.maliyet_tip.in_(MALIYET_DISI_TIPLER))
            ek_maliyet_usd += db.session.query(db.func.sum(Maliyet.usd_karsilik)).filter(
                Maliyet.baglanti_id.in_(stok_idler),
                Maliyet.aktif.is_(True), _mr1
            ).scalar() or 0
            ek_maliyet_try += db.session.query(db.func.sum(Maliyet.try_karsilik)).filter(
                Maliyet.baglanti_id.in_(stok_idler),
                Maliyet.aktif.is_(True), _mr1
'''),
    ('flask_app.py', 'MR1 · flask_app.py blok 2',
     r'''        matrah = blok.matrah or ((blok.alis_fiyati or 0) * (blok.tonaj or 0)
                                 if blok.alis_fiyat_birim == 'ton' else
                                 (blok.alis_fiyati or 0) * (blok.hacim_m3 or 0))
        ek_top = db.session.query(db.func.sum(Maliyet.usd_karsilik)).filter(
            Maliyet.baglanti_id == blok_id,
            ~Maliyet.maliyet_tip.in_(['Devreden KDV', 'Iade KDV'])
        ).scalar() or 0
''',
     r'''        # MR1: ek maliyet toplami `_stok_maliyet_kalemleri`den geliyor.
        # Burada ucuncu bir kopya vardi ve IKI SUZGECI kaciriyordu:
        # iptal edilmis (aktif=False) gider plakalara DAGITILIYOR,
        # tipsiz gider ise hic dagitilmiyordu. Olculdu — 400 USD'lik
        # iptal bir gider yuzunden blok 7.550 USD iken plakalara
        # 7.950 dagitilmisti.
        #
        # MATRAH'a DOKUNULMADI: burada (ve kesim ucunda) matrah
        # stogun kendi dovizinde, cevrilmeden kullaniliyor. Duzeltmek
        # USD disi bloklarda mevcut birim maliyetleri oynatir; ayri
        # bir karar, Bahadir'a soruldu.
        matrah = blok.matrah or ((blok.alis_fiyati or 0) * (blok.tonaj or 0)
                                 if blok.alis_fiyat_birim == 'ton' else
                                 (blok.alis_fiyati or 0) * (blok.hacim_m3 or 0))
        ek_top = sum(float(m.usd_karsilik or 0)
                     for m in _stok_maliyet_kalemleri(blok_id))
'''),
    ('flask_app.py', 'MR1 · flask_app.py blok 3',
     r'''    def _satis_kaydi_maliyet_guncelle(stok_idler):
''',
     r'''    # ══════════════════════════════════════════════════════════════
    #  MR1 · BİR STOĞUN MALİYETİ — TEK KAYNAK
    #
    #  Satış kârı, stok ekranı ve maliyet raporu AYNI rakamı söylemek
    #  zorunda. Üç ayrı toplama zamanla ayrışır — DZ4'te aynı dersi
    #  almıştık. Hesap burada, çağıranlar buradan okuyor.
    #
    #  İKİ SÜZGEÇ, İKİSİ DE GEREKLİ:
    #    1) `aktif=False` kayıtlar İPTAL EDİLMİŞ maliyetlerdir.
    #    2) `~tip.in_(...)` tek başına, tipi BOŞ olan satırı da eler:
    #       SQL'de NULL NOT IN (...) sonucu NULL'dır, satır düşer.
    #       Tipsiz girilmiş bir fason gideri maliyete hiç girmezdi.
    #
    #  Bu iki süzgeç ortaklık hesabında vardı ve orada gerekçesi
    #  yazılıydı ("uygulamanın geri kalanı onları her yerde
    #  süzüyor") — ama SATIŞ MALİYETİNDE ikisi de yoktu.
    # ══════════════════════════════════════════════════════════════
    MALIYET_DISI_TIPLER = ('Devreden KDV', 'Iade KDV')

    def _stok_alim_usd(stok, stok_tip=None):
        """Stoğun KENDİ alış bedeli, USD. Ek maliyetler hariç.

        ── MATRAH ÖNCELİKLİ ──
        Stok faturalandıysa `matrah` o faturanın KDV hariç bedelidir
        ve birim fiyat × ölçü çarpımından daha doğrudur (yuvarlama,
        iskonto, kısmi giriş). Kesim dağıtıcısı zaten matrahı
        önceliyordu; satış maliyeti ise HİÇ bakmıyordu — ikisi aynı
        stok için farklı alış bedeli kullanıyordu.

        ── BİR DE ÇEVRİM ──
        Dağıtıcı matrahı USD'ye ÇEVİRMEDEN kullanıyordu. TL ile
        alınmış bir blokta matrah TL, ama USD gibi işleniyordu.
        Burada stoğun kendi dövizinden çevriliyor.
        """
        if not stok:
            return 0.0
        stok_doviz = getattr(stok, 'doviz', 'USD') or 'USD'
        matrah = float(getattr(stok, 'matrah', 0) or 0)
        if matrah > 0:
            ham = matrah
        else:
            alis_fiyat = getattr(stok, 'alis_fiyati', 0) or 0
            alis_birim = getattr(stok, 'alis_fiyat_birim', None) or (
                'ton' if (stok_tip or '').upper() == 'BLOK' else 'm2')
            try:
                alis_olcu = _stok_olcu(stok, alis_birim)
            except Exception:
                alis_olcu = 0
            ham = float(alis_fiyat or 0) * float(alis_olcu or 0)
        if stok_doviz == 'USD':
            return ham
        usd_k = DovizKur.query.filter_by(doviz='USD').order_by(
            DovizKur.tarih.desc()).first()
        eur_k = DovizKur.query.filter_by(doviz='EUR').order_by(
            DovizKur.tarih.desc()).first()
        ku = float((usd_k.alis if usd_k else 0) or 0)
        ke = float((eur_k.alis if eur_k else 0) or 0)
        if stok_doviz == 'EUR':
            return (ham * ke / ku) if ku else 0.0
        if stok_doviz == 'TRY':
            return (ham / ku) if ku else 0.0
        return ham

    def _stok_maliyet_kalemleri(stok_id, haric=False):
        """Stoğa işlenmiş maliyet kalemleri.

        `haric=True` ise MALİYETE GİRMEYEN kalemler (Devreden/İade
        KDV) döner — raporda ayrı bir başlıkta gösteriliyor, çünkü
        "neden toplamda yok" sorusunun cevabı görünmeli."""
        q = Maliyet.query.filter(Maliyet.baglanti_id == stok_id,
                                 Maliyet.aktif.is_(True))
        if haric:
            q = q.filter(Maliyet.maliyet_tip.in_(MALIYET_DISI_TIPLER))
        else:
            q = q.filter(db.or_(
                Maliyet.maliyet_tip.is_(None),
                ~Maliyet.maliyet_tip.in_(MALIYET_DISI_TIPLER)))
        return q.order_by(Maliyet.maliyet_tarihi.asc(),
                          Maliyet.id.asc()).all()

    def _stok_maliyet_dokumu(stok_id, stok_tip=None, stok=None):
        """Bir stoğun maliyeti, kalem kalem.

        Döner: alim_usd · kalem_usd · toplam_usd · kalemler · haric
        """
        if stok is None and stok_tip:
            stok = _stok_getir(stok_id, (stok_tip or '').upper())
        alim = _stok_alim_usd(stok, stok_tip)

        def _satir(m):
            return {'id': m.id, 'tip': m.maliyet_tip or '(tipsiz)',
                    'fatura_no': m.fatura_no,
                    'tarih': (m.maliyet_tarihi.isoformat()
                              if m.maliyet_tarihi else None),
                    'tutar': q2(m.tutar or 0), 'doviz': m.doviz,
                    'usd': q2(m.usd_karsilik or 0)}

        kalemler = [_satir(m) for m in _stok_maliyet_kalemleri(stok_id)]
        haric = [_satir(m) for m in _stok_maliyet_kalemleri(stok_id, True)]
        kalem_usd = q2(sum(k['usd'] for k in kalemler))
        return {'alim_usd': q2(alim), 'kalem_usd': kalem_usd,
                'toplam_usd': q2(alim + kalem_usd),
                'kalemler': kalemler, 'haric': haric}

    def _satis_kaydi_maliyet_guncelle(stok_idler):
'''),
    ('flask_app.py', 'MR1 · flask_app.py blok 4',
     r'''            # Bu stoga ait toplam maliyet (Maliyet tablosu)
            stok_maliyet = db.session.query(db.func.sum(Maliyet.usd_karsilik)).filter(
                Maliyet.baglanti_id == sk.stok_id,
                ~Maliyet.maliyet_tip.in_(['Devreden KDV', 'Iade KDV'])
            ).scalar() or 0
            # Stogun kendi alis maliyeti (stok kaydindan)
            alim_usd = 0
            stok = _stok_getir(sk.stok_id, sk.stok_tip)
            if stok:
                alis_fiyat = getattr(stok, 'alis_fiyati', 0) or 0
                alis_birim = getattr(stok, 'alis_fiyat_birim', None) or (
                    'ton' if sk.stok_tip == 'BLOK' else 'm2')
                try:
                    alis_olcu = _stok_olcu(stok, alis_birim)
                except Exception:
                    alis_olcu = 0
                stok_doviz = getattr(stok, 'doviz', 'USD') or 'USD'
                # USD'ye cevir
                if stok_doviz == 'USD':
                    alim_usd = alis_fiyat * alis_olcu
                else:
                    usd_k = DovizKur.query.filter_by(doviz='USD').order_by(
                        DovizKur.tarih.desc()).first()
                    eur_k = DovizKur.query.filter_by(doviz='EUR').order_by(
                        DovizKur.tarih.desc()).first()
                    ku = (usd_k.alis if usd_k else 0) or 0
                    ke = (eur_k.alis if eur_k else 0) or 0
                    ham = alis_fiyat * alis_olcu
                    if stok_doviz == 'EUR':
                        alim_usd = (ham * ke / ku) if ku else 0
                    elif stok_doviz == 'TRY':
                        alim_usd = (ham / ku) if ku else 0
                    else:
                        alim_usd = ham

            yeni_maliyet = alim_usd + stok_maliyet
''',
     r'''            # MR1: hesap `_stok_maliyet_dokumu`ya tasindi — rapor ve
            # stok ekrani da ayni yerden okuyor. Buradaki kopya iki
            # suzgeci kacirdigi icin iptal edilmis gideri sayiyor,
            # tipsiz gideri ise hic saymiyordu.
            yeni_maliyet = _stok_maliyet_dokumu(
                sk.stok_id, sk.stok_tip)['toplam_usd']
'''),
    ('flask_app.py', 'MR1 · flask_app.py blok 5',
     r'''    @app.route('/api/rapor/stok_durum', methods=['GET'])
''',
     r'''    # ══════════════════════════════════════════════════════════════
    #  MR1 · STOK MALİYET RAPORU
    #
    #  Bu bilgi sistemde vardı ama tek tek, çekmecede: bir stoğun
    #  maliyet dökümünü görmek için o stoğu bulup kaynak zincirini
    #  açmak gerekiyordu. Toplu bir yerde yoktu.
    #
    #  BLOK ALTINDA GRUPLU: bloğun matrahı ve ondan kesilmiş
    #  plaka/ebatlı ürünlerin maliyeti BİR ARADA görünüyor. Düz liste
    #  olsaydı kesim ilişkisi kaybolurdu — bloğun 6.000 USD'sinin
    #  hangi plakalara dağıldığı okunmazdı.
    #
    #  Hesap `_stok_maliyet_dokumu`dan geliyor; satış kârı da oradan
    #  okuyor. İki ayrı toplama zamanla ayrışırdı.
    # ══════════════════════════════════════════════════════════════
    @app.route('/api/rapor/stok_maliyet', methods=['GET'])
    def api_rapor_stok_maliyet():
        """Stok maliyet raporu — blok altında gruplu.

        Süzgeçler: ?tip= ?cins= ?uretici= ?durum= ?blok_no=
                   ?baslangic= ?bitis=   (giriş tarihi)
        """
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401

        tip = (request.args.get('tip') or '').upper().strip()
        cins = (request.args.get('cins') or '').strip()
        uretici = (request.args.get('uretici') or '').strip()
        durum = (request.args.get('durum') or '').strip()
        blok_no = (request.args.get('blok_no') or '').strip()
        bas = _parse_date(request.args.get('baslangic'))
        bit = _parse_date(request.args.get('bitis'))

        def _suz(q, model):
            if cins and hasattr(model, 'cins'):
                q = q.filter(model.cins == cins)
            if uretici and hasattr(model, 'uretici'):
                q = q.filter(model.uretici == uretici)
            if durum and hasattr(model, 'durum'):
                q = q.filter(model.durum == durum)
            if blok_no and hasattr(model, 'blok_no'):
                q = q.filter(model.blok_no == blok_no)
            if bas and hasattr(model, 'giris_tarihi'):
                q = q.filter(model.giris_tarihi >= bas)
            if bit and hasattr(model, 'giris_tarihi'):
                q = q.filter(model.giris_tarihi <= bit)
            return q

        def _olcu_ozet(s, t):
            if t == 'BLOK':
                return {'tonaj': q2(getattr(s, 'tonaj', 0) or 0),
                        'hacim_m3': q2(getattr(s, 'hacim_m3', 0) or 0)}
            return {'metraj_m2': q2(getattr(s, 'metraj_m2', 0) or 0)}

        def _birim(dokum, s, t):
            """Birim maliyet — BLOK'ta ton, diğerlerinde m²."""
            if t == 'BLOK':
                ol = float(getattr(s, 'tonaj', 0) or 0)
                birim_ad = 'ton'
            else:
                ol = float(getattr(s, 'metraj_m2', 0) or 0)
                birim_ad = 'm²'
            # Ölçü yoksa SIFIR DEĞİL None: sıfır yazmak "maliyeti yok"
            # demek olurdu, oysa ölçü girilmemiş demek.
            return ({'deger': q2(dokum['toplam_usd'] / ol), 'birim': birim_ad}
                    if ol else {'deger': None, 'birim': birim_ad})

        def _kart(s, t):
            d = _stok_maliyet_dokumu(s.id, t, stok=s)
            return {'id': s.id, 'tip': t,
                    'blok_no': getattr(s, 'blok_no', None),
                    'slab_no': getattr(s, 'slab_no', None),
                    'kasa_no': getattr(s, 'kasa_no', None),
                    'cins': getattr(s, 'cins', None),
                    'uretici': getattr(s, 'uretici', None),
                    'durum': getattr(s, 'durum', None),
                    'giris_tarihi': (s.giris_tarihi.isoformat()
                                     if getattr(s, 'giris_tarihi', None) else None),
                    'olcu': _olcu_ozet(s, t),
                    'alim_usd': d['alim_usd'], 'kalem_usd': d['kalem_usd'],
                    'toplam_usd': d['toplam_usd'],
                    'birim_maliyet': _birim(d, s, t),
                    'kalemler': d['kalemler'], 'haric': d['haric']}

        # ── BLOKLAR ──
        gruplar = []
        if tip in ('', 'BLOK'):
            for b in _suz(BlokStok.query, BlokStok).order_by(
                    BlokStok.giris_tarihi.desc(), BlokStok.id.desc()).all():
                g = _kart(b, 'BLOK')
                g['urunler'] = []
                gruplar.append(g)

        # ── KESİMDEN ÇIKANLAR: bloğun altına ──
        # Hangi ürün hangi bloktan: Kesim.kaynak_id → KesimDetay.
        blok_sirasi = {g['id']: g for g in gruplar}
        cocuk_anahtar = {}
        if blok_sirasi:
            for ks in Kesim.query.filter(
                    Kesim.kaynak_tip == 'BLOK',
                    Kesim.kaynak_id.in_(list(blok_sirasi))).all():
                for dt in KesimDetay.query.filter_by(kesim_id=ks.id).all():
                    if dt.hedef_stok_id:
                        cocuk_anahtar[dt.hedef_stok_id] = ks.kaynak_id

        bagimsiz = []
        for model, t in ((PlakaStok, 'PLAKA'), (EbatliStok, 'EBATLI')):
            if tip and tip != t:
                continue
            for s in _suz(model.query, model).all():
                k = _kart(s, t)
                ana = cocuk_anahtar.get(s.id)
                if ana and ana in blok_sirasi:
                    blok_sirasi[ana]['urunler'].append(k)
                else:
                    # Kesimden GELMEYEN (doğrudan girilmiş) ürün.
                    # Bloğun altına koymak yanlış olurdu.
                    bagimsiz.append(k)

        def _topla(kartlar):
            return {'adet': len(kartlar),
                    'alim_usd': q2(sum(k['alim_usd'] for k in kartlar)),
                    'kalem_usd': q2(sum(k['kalem_usd'] for k in kartlar)),
                    'toplam_usd': q2(sum(k['toplam_usd'] for k in kartlar))}

        # Blok TOPLAMI, altındaki ürünleri İÇERMEZ: bloğun maliyeti
        # kesimde plakalara DAĞITILIYOR; ikisini toplamak aynı parayı
        # iki kez saymak olurdu.
        for g in gruplar:
            g['urun_ozet'] = _topla(g['urunler'])

        tum = gruplar + bagimsiz
        return jsonify({
            'ok': True,
            'gruplar': gruplar,
            'bagimsiz': bagimsiz,
            'genel': {
                'blok': _topla(gruplar),
                'bagimsiz': _topla(bagimsiz),
                'urun': _topla([u for g in gruplar for u in g['urunler']]),
                'kayit_sayisi': len(tum) + sum(len(g['urunler']) for g in gruplar)
            }})

    @app.route('/api/rapor/stok_maliyet/excel', methods=['GET'])
    def api_rapor_stok_maliyet_excel():
        """Stok maliyet raporu — .xlsx.

        Aynı uçtan beslenir: `api_rapor_stok_maliyet` ne diyorsa
        Excel de onu der. Ayrı bir sorgu yazmak iki rakam demekti.
        """
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        import io          # modul duzeyinde YOK; kasa Excel'i de boyle aliyor
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, PatternFill
            from openpyxl.utils import get_column_letter
        except ImportError:
            return jsonify({'ok': False,
                'mesaj': 'Excel çıktısı için "openpyxl" paketi gerekli. '
                         'Kurulum: pip install openpyxl'}), 500

        # Rapor fonksiyonu DOGRUDAN cagriliyor: ayni istek baglamini
        # (ve ayni suzgecleri) kullaniyor. `test_request_context` ile
        # yeni bir baglam acsaydik oturum tasinmaz, `_auth_required`
        # icerde patlardi. Ayri bir sorgu yazmak ise iki rakam demekti.
        veri = api_rapor_stok_maliyet().get_json()

        wb = Workbook()
        sh = wb.active
        sh.title = 'Stok Maliyeti'
        bas_font = Font(bold=True, color='FFFFFF')
        bas_dolgu = PatternFill('solid', fgColor='1F6F54')
        grup_font = Font(bold=True)

        basliklar = ['Kayıt', 'Tip', 'Blok No', 'Plaka/Kasa', 'Cins',
                     'Üretici', 'Durum', 'Giriş', 'Ölçü', 'Birim',
                     'Alış (USD)', 'Ek Maliyet (USD)', 'Toplam (USD)',
                     'Birim Maliyet', 'Maliyet Dışı (USD)']
        sh.append(basliklar)
        for i in range(1, len(basliklar) + 1):
            c = sh.cell(row=1, column=i)
            c.font = bas_font; c.fill = bas_dolgu
            c.alignment = Alignment(horizontal='center')

        def _olcu_metin(k):
            o = k.get('olcu') or {}
            if o.get('metraj_m2') is not None:
                return o['metraj_m2'], 'm²'
            return o.get('tonaj'), 'ton'

        def _yaz(k, girinti=''):
            ol, birim = _olcu_metin(k)
            bm = k.get('birim_maliyet') or {}
            sh.append([
                girinti + (k.get('id') or ''), k.get('tip'),
                k.get('blok_no'), k.get('slab_no') or k.get('kasa_no'),
                k.get('cins'), k.get('uretici'), k.get('durum'),
                k.get('giris_tarihi'), ol, birim,
                k.get('alim_usd'), k.get('kalem_usd'), k.get('toplam_usd'),
                bm.get('deger'),
                q2(sum(h.get('usd') or 0 for h in (k.get('haric') or [])))])

        for g in veri.get('gruplar', []):
            _yaz(g)
            sh.cell(row=sh.max_row, column=1).font = grup_font
            for u in g.get('urunler', []):
                _yaz(u, '    ')
        for b in veri.get('bagimsiz', []):
            _yaz(b)

        for i in range(1, len(basliklar) + 1):
            sh.column_dimensions[get_column_letter(i)].width = 16
        for satir in sh.iter_rows(min_row=2, min_col=11, max_col=15):
            for c in satir:
                c.number_format = '#,##0.00'

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return send_file(
            buf,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'stok_maliyet_{date.today().isoformat()}.xlsx')

    @app.route('/api/rapor/stok_durum', methods=['GET'])
'''),
    ('flask_app.py', 'MR1 · flask_app.py blok 6',
     r'''            ek_maliyet_map = {}
            if kaynak_id_listesi:
                for _bid, _t in db.session.query(
                    Maliyet.baglanti_id, db.func.sum(Maliyet.usd_karsilik)
                ).filter(
                    Maliyet.baglanti_id.in_(kaynak_id_listesi),
                    ~Maliyet.maliyet_tip.in_(['Devreden KDV', 'Iade KDV'])
                ).group_by(Maliyet.baglanti_id).all():
                    ek_maliyet_map[_bid] = _t or 0
''',
     r'''            # MR1: IKI SUZGEC burada da eksikti — iptal edilmis
            # (aktif=False) bir gider kesimde plakalara dagitiliyor,
            # tipsiz gider ise hic dagitilmiyordu. Tek kaynak:
            # `_stok_maliyet_kalemleri`.
            ek_maliyet_map = {}
            for _kid in kaynak_id_listesi:
                ek_maliyet_map[_kid] = sum(
                    float(m.usd_karsilik or 0)
                    for m in _stok_maliyet_kalemleri(_kid))
'''),
    ('flask_app.py', 'MR1 · flask_app.py blok 7',
     r'''        """Silme/düzenleme sonrası türetilmiş değerleri yeniden üret."""
''',
     r'''        """Silme/düzenleme sonrası türetilmiş değerleri yeniden üret.

        ── MR1 · KESİMDEN ÇIKANLAR DA TAZELENİR ──
        Bloğa maliyet eklenince plakaların birim maliyeti yeniden
        dağıtılıyordu ama SATILMIŞ bir plakanın kâr kaydı eski
        maliyetle kalıyordu: stok kartı yeni rakamı gösterirken
        kârlılık raporu eskisini gösteriyordu.

        ÖLÇÜLDÜ — satış dökümü ucunu yazarken yakalandı: kayıtta
        0,00 USD maliyet dururken hesaplanan 3.774,98 USD'ydi.

        DZ4'te aynı tazeleme ÖLÇÜ değişimi için konmuştu; maliyet
        eklenmesi için konmamıştı.
        """
'''),
    ('flask_app.py', 'MR1 · flask_app.py blok 8',
     r'''        return n
''',
     r'''                db.session.flush()
                # Dagitim plakalarin alis_fiyati'ni degistirdi; o
                # plakalarin satis kayitlari da yeniden hesaplanmali.
                _cocuklar = []
                for _ks in Kesim.query.filter_by(kaynak_id=sid).all():
                    _cocuklar += [d.hedef_stok_id for d in
                                  KesimDetay.query.filter_by(
                                      kesim_id=_ks.id).all()
                                  if d.hedef_stok_id]
                if _cocuklar:
                    n += _satis_kaydi_maliyet_guncelle(_cocuklar)
        return n
'''),
    ('flask_app.py', 'MR1 · flask_app.py blok 9',
     r'''
    @app.route('/api/karlilik/musteri_ozet', methods=['GET'])
''',
     r'''
    # ══════════════════════════════════════════════════════════════
    #  MR1 · BİR SATIŞIN MALİYET DÖKÜMÜ
    #
    #  Kârlılık listesi satır başına maliyet ve kâr veriyordu ama
    #  "bu maliyet NEREDEN geliyor" sorusunun cevabı yoktu. Kalem
    #  dökümü yalnız SİPARİŞ bazlı raporda vardı; tek bir satışın
    #  dökümünü görmek için stoğu bulup kaynak zincirini açmak
    #  gerekiyordu.
    #
    #  Liste HAFİF kalsın diye ayrı uç: döküm ancak satıra
    #  tıklanınca çekiliyor.
    # ══════════════════════════════════════════════════════════════
    @app.route('/api/karlilik/<satis_id>/dokum', methods=['GET'])
    def api_karlilik_dokum(satis_id):
        """Bir satış kaydının maliyeti, kalem kalem."""
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        s = db.session.get(SatisKaydi, satis_id)
        if not s:
            return jsonify({'ok': False, 'mesaj': 'Satış kaydı bulunamadı'}), 404

        stok = _stok_getir(s.stok_id, (s.stok_tip or '').upper()) \
            if s.stok_id else None
        d = _stok_maliyet_dokumu(s.stok_id, s.stok_tip, stok=stok) \
            if s.stok_id else {'alim_usd': 0, 'kalem_usd': 0,
                               'toplam_usd': 0, 'kalemler': [], 'haric': []}

        satis_usd = q2(s.tutar_usd or s.tutar or 0)
        # Kâr, KAYITTAN okunuyor — burada yeniden hesaplamak üçüncü
        # bir formül olurdu. Kayıt `_satis_kaydi_maliyet_guncelle`
        # ile güncelleniyor ve o da aynı dökümden besleniyor.
        kayit_maliyet = q2(s.maliyet_usd or 0)
        return jsonify({
            'ok': True,
            'satis': {
                'id': s.id, 'musteri': s.musteri,
                'tarih': s.satis_tarihi.isoformat() if s.satis_tarihi else None,
                'cins': s.cins, 'stok_tip': s.stok_tip, 'stok_id': s.stok_id,
                'miktar': q2(s.miktar or 0), 'birim': s.birim,
                'doviz': s.doviz or 'USD',
                'birim_fiyat': q2(s.birim_fiyat or 0),
                'tutar': q2(s.tutar or 0), 'tutar_usd': satis_usd,
                'fatura_no': s.fatura_no, 'siparis_id': s.siparis_id},
            'stok': ({'id': stok.id,
                      'blok_no': getattr(stok, 'blok_no', None),
                      'slab_no': getattr(stok, 'slab_no', None),
                      'kasa_no': getattr(stok, 'kasa_no', None),
                      'uretici': getattr(stok, 'uretici', None),
                      'durum': getattr(stok, 'durum', None)} if stok else None),
            'maliyet': d,
            # Kayıttaki maliyet ile şu an hesaplanan AYNI olmalı.
            # Ayrışıyorsa stoğa sonradan gider eklenmiş ve satış
            # kaydı tazelenmemiş demektir — sessiz bırakmıyoruz.
            'tutarsizlik': (None if abs(kayit_maliyet - d['toplam_usd']) < 0.01
                            else {'kayitta': kayit_maliyet,
                                  'hesaplanan': d['toplam_usd'],
                                  'fark': q2(d['toplam_usd'] - kayit_maliyet)}),
            'ozet': {'satis_usd': satis_usd,
                     'maliyet_usd': kayit_maliyet,
                     'kar_usd': q2(s.kar_usd or 0),
                     'marj': q_oran(s.marj_yuzde or 0)}})

    @app.route('/api/karlilik/musteri_ozet', methods=['GET'])
'''),
    ('templates/raporlar.html', 'MR1 · templates/raporlar.html blok 1',
     r'''</style>
''',
     r'''
  /* ── MR1 · STOK MALİYETİ ── */
  .sm-suzgec{display:flex;flex-wrap:wrap;gap:8px;align-items:flex-end}
  .sm-suzgec label{display:block;font-size:.72rem;font-weight:700;letter-spacing:.04em;
    text-transform:uppercase;color:var(--soluk);margin-bottom:4px}
  .sm-suzgec input,.sm-suzgec select{min-width:120px}
  .sm-suzgec .sag{margin-left:auto;display:flex;gap:8px}
  /* Blok kutusu: başlık + altında kesimden çıkanlar */
  .sm-blok{border:1px solid var(--cizgi);border-radius:10px;margin-bottom:10px;overflow:hidden}
  .sm-blok:last-child{margin-bottom:0}
  .sm-bas{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 14px;
    padding:10px 13px;background:var(--taban);cursor:pointer}
  .sm-bas .ad{font-weight:700;font-size:.9rem}
  .sm-bas .et{color:var(--soluk);font-size:.78rem}
  .sm-bas .tut{margin-left:auto;font-family:var(--mono);font-weight:700;white-space:nowrap}
  .sm-ic{padding:0 13px 11px;display:none}
  .sm-blok.acik .sm-ic{display:block}
  /* Kalem satırı — sütunlar SABİT, MG1'deki ile aynı gerekçe */
  .sm-kalem{display:grid;grid-template-columns:minmax(0,17em) minmax(0,9em) 1fr;
    gap:2px 10px;align-items:baseline;padding:3px 0;font-size:.82rem}
  .sm-kalem .e{color:var(--soluk);font-size:.74rem}
  .sm-kalem .son{justify-self:end;font-family:var(--mono);white-space:nowrap}
  .sm-urun{display:grid;grid-template-columns:minmax(0,14em) minmax(0,8em) 1fr auto;
    gap:2px 10px;align-items:baseline;padding:5px 0;font-size:.83rem;
    border-top:1px solid var(--cizgi)}
  .sm-urun .m{font-family:var(--mono)}
  .sm-alt{margin-top:7px;padding-top:7px;border-top:1px solid var(--cizgi);
    font-size:.78rem;color:var(--soluk)}
  .sm-haric{color:var(--kehribar)}
  /* Kârlılıkta açılır döküm */
  tr.dokum > td{background:var(--taban);padding:11px 13px}
  tr.tiklanir{cursor:pointer}
  @media (max-width:760px){
    .sm-kalem{grid-template-columns:1fr auto}
    .sm-kalem > :first-child{grid-column:1 / -1}
    .sm-urun{grid-template-columns:1fr auto}
  }
  /* ── YAZDIR ──
     Ekranda sekmeler ve süzgeçler var; kâğıtta ikisi de anlamsız.
     Yalnız AÇIK bölüm basılır. */
  @media print{
    .sekmeler,.sm-suzgec,.kpiler{display:none !important}
    .bolum{display:none !important}
    .bolum.aktif{display:block !important}
    .sm-ic{display:block !important}
    .panel{break-inside:avoid;border:0;padding:0}
    .sm-blok{break-inside:avoid}
    tr.dokum{display:table-row !important}
  }
</style>
'''),
    ('templates/raporlar.html', 'MR1 · templates/raporlar.html blok 2',
     r'''  <button class="sekme" data-b="maliyetanaliz">Maliyet Analizi</button>
''',
     r'''  <button class="sekme" data-b="maliyetanaliz">Maliyet Analizi</button>
  <button class="sekme" data-b="stokmaliyet">Stok Maliyeti</button>
'''),
    ('templates/raporlar.html', 'MR1 · templates/raporlar.html blok 3',
     r'''        <tbody id="maGovde"><tr><td colspan="7" class="yukleniyor">Yükleniyor…</td></tr></tbody>
      </table>
    </div>
''',
     r'''        <tbody id="maGovde"><tr><td colspan="7" class="yukleniyor">Yükleniyor…</td></tr></tbody>
      </table>
    </div>
  </div>
</section>

<!-- ══════════════════════════════════════════════════════════════
     MR1 — STOK MALİYETİ
     Bu bilgi sistemde vardı ama tek tek, kaynak zinciri
     çekmecesinde. Toplu ve süzülebilir hâli yoktu.
     Bloklar başlık, kesimden çıkanlar onların altında: bloğun
     matrahının hangi plakalara dağıldığı bir arada okunsun.
     ══════════════════════════════════════════════════════════════ -->
<section class="bolum" id="b-stokmaliyet">
  <div class="panel" style="margin-bottom:14px">
    <div class="sm-suzgec">
      <div><label>Tip</label>
        <select id="smTip">
          <option value="">hepsi</option>
          <option value="BLOK">Blok</option>
          <option value="PLAKA">Plaka</option>
          <option value="EBATLI">Ebatlı</option>
        </select></div>
      <div><label>Cins</label><input id="smCins" placeholder="tümü"></div>
      <div><label>Üretici</label><input id="smUretici" placeholder="tümü"></div>
      <div><label>Durum</label><input id="smDurum" placeholder="tümü"></div>
      <div><label>Blok No</label><input id="smBlokNo" placeholder="tümü"></div>
      <div><label>Giriş · başlangıç</label><input id="smBas" type="date"></div>
      <div><label>Giriş · bitiş</label><input id="smBit" type="date"></div>
      <div class="sag">
        <button class="btn-yeni" onclick="stokMaliyetYukle()">Uygula</button>
        <button class="iptal-btn" onclick="smTemizle()">Temizle</button>
        <button class="iptal-btn" onclick="smExcel()">Excel</button>
        <button class="iptal-btn" onclick="window.print()">Yazdır</button>
      </div>
    </div>
  </div>
  <div class="kpiler" id="smKpi" style="grid-template-columns:repeat(4,1fr);margin-bottom:14px">
    <div class="kpi"><label>Blok</label><div class="deger" id="smBlokAdet">—</div><div class="ek" id="smBlokTut">—</div></div>
    <div class="kpi"><label>Kesimden çıkan</label><div class="deger" id="smUrunAdet">—</div><div class="ek" id="smUrunTut">—</div></div>
    <div class="kpi"><label>Bağımsız ürün</label><div class="deger" id="smBagAdet">—</div><div class="ek" id="smBagTut">—</div></div>
    <div class="kpi"><label>Ek maliyet</label><div class="deger" id="smEkTut">—</div><div class="ek">alış hariç</div></div>
  </div>
  <div class="panel">
    <h4>Blok ve ondan çıkanlar
      <span style="color:var(--soluk);font-weight:400;font-size:.83rem">· başlığa tıkla, dökümü aç</span></h4>
    <div id="smGovde"><div class="yukleniyor">Yükleniyor…</div></div>
  </div>
  <div class="panel" style="margin-top:14px">
    <h4>Kesimden gelmeyen ürünler
      <span style="color:var(--soluk);font-weight:400;font-size:.83rem">· doğrudan girilmiş</span></h4>
    <div id="smBagimsiz"><div class="yukleniyor">Yükleniyor…</div></div>
'''),
    ('templates/raporlar.html', 'MR1 · templates/raporlar.html blok 4',
     r'''      <tr style="border-left-color:var(${ray})">
''',
     r'''      <tr class="tiklanir" data-sk="${kacar(s.id)}" style="border-left-color:var(${ray})"
          onclick="satisDokumAc('${kacar(s.id)}', 7)" title="Maliyet dökümünü aç">
'''),
    ('templates/raporlar.html', 'MR1 · templates/raporlar.html blok 5',
     r'''const yuklendi = { genel: false, karlilik: false, stok: false, cari: false, sevkiyat: false,
                   performans: false, maliyetanaliz: false };
const yukleyici = { genel: genelYukle, karlilik: karlilikYukle, stok: stokYukle, cari: cariYukle,
                    sevkiyat: konteynerYukle, performans: performansYukle, maliyetanaliz: maliyetAnalizYukle };
''',
     r'''/* ═══════════════════════════════════════════════════════════════
   MR1 — STOK MALİYETİ
   ═══════════════════════════════════════════════════════════════ */
function smSorgu() {
  const al = i => (document.getElementById(i).value || '').trim();
  const p = new URLSearchParams();
  const esle = { tip: 'smTip', cins: 'smCins', uretici: 'smUretici',
                 durum: 'smDurum', blok_no: 'smBlokNo',
                 baslangic: 'smBas', bitis: 'smBit' };
  Object.entries(esle).forEach(([ad, id]) => { if (al(id)) p.set(ad, al(id)); });
  return p.toString();
}
function smTemizle() {
  ['smTip','smCins','smUretici','smDurum','smBlokNo','smBas','smBit']
    .forEach(i => document.getElementById(i).value = '');
  stokMaliyetYukle();
}
function smExcel() {
  const q = smSorgu();
  window.location = '/api/rapor/stok_maliyet/excel' + (q ? '?' + q : '');
}

/* Kalem satırı — stok maliyet raporunda ve açılır satış dökümünde
   AYNI biçim. İki ayrı yazım zamanla ayrışırdı. */
function smKalemSatir(k) {
  return `<div class="sm-kalem">
    <span><span class="e">${kacar(k.tip || '—')}</span></span>
    <span><span class="e">${k.fatura_no ? kacar(k.fatura_no) : 'belgesiz'}</span></span>
    <span class="son">${para(k.usd)}${
      k.doviz && k.doviz !== 'USD'
        ? ` <span class="e">(${para2(k.tutar, k.doviz)})</span>` : ''}</span>
  </div>`;
}

function smBirim(b) {
  /* Ölçü girilmemişse birim maliyet YOK — sıfır yazmak
     "maliyeti yok" demek olurdu. */
  return b && b.deger != null
    ? `${para(b.deger)} / ${b.birim}` : '<span class="e">ölçü yok</span>';
}

function smUrunSatir(u) {
  const ol = u.olcu || {};
  const mik = ol.metraj_m2 != null ? ol.metraj_m2 + ' m²'
            : (ol.tonaj != null ? ol.tonaj + ' ton' : '—');
  return `<div class="sm-urun">
    <span class="mono" style="font-size:.8rem">${kacar(u.slab_no ? u.blok_no + ' · ' + u.slab_no : (u.kasa_no || u.id))}</span>
    <span class="e">${kacar(mik)} · ${kacar(u.durum || '—')}</span>
    <span class="e">${smBirim(u.birim_maliyet)}</span>
    <span class="m" style="font-weight:600">${para(u.toplam_usd)}</span>
  </div>`;
}

function smKart(g, acik) {
  const u = g.urun_ozet || { adet: 0 };
  const ad = g.tip === 'BLOK'
    ? `Blok ${kacar(g.blok_no || g.id)}`
    : kacar(g.slab_no ? g.blok_no + ' · ' + g.slab_no : (g.kasa_no || g.id));
  return `<div class="sm-blok${acik ? ' acik' : ''}">
    <div class="sm-bas" onclick="this.parentElement.classList.toggle('acik')">
      <span class="ad">${ad}</span>
      <span class="et">${kacar(g.cins || '—')}</span>
      <span class="et">${kacar(g.uretici || '—')}</span>
      <span class="et">${kacar(g.durum || '—')}</span>
      ${u.adet ? `<span class="et">${u.adet} ürün</span>` : ''}
      <span class="tut">${para(g.toplam_usd)}</span>
    </div>
    <div class="sm-ic">
      <div class="sm-kalem"><span><span class="e">Alış bedeli</span></span>
        <span></span><span class="son">${para(g.alim_usd)}</span></div>
      ${(g.kalemler || []).map(smKalemSatir).join('')}
      <div class="sm-alt">
        <strong style="color:var(--murekkep)">Toplam ${para(g.toplam_usd)}</strong>
        · birim ${smBirim(g.birim_maliyet)}
        ${(g.haric || []).length ? '<span class="sm-haric"> · maliyet dışı: '
          + g.haric.map(h => kacar(h.tip) + ' ' + para(h.usd)).join(', ')
          + '</span>' : ''}
      </div>
      ${(g.urunler || []).length ? `<div style="margin-top:9px">
         <div class="e" style="font-size:.74rem;color:var(--soluk);text-transform:uppercase;letter-spacing:.04em;font-weight:700">Kesimden çıkanlar</div>
         ${g.urunler.map(smUrunSatir).join('')}</div>` : ''}
    </div>
  </div>`;
}

async function stokMaliyetYukle() {
  const govde = document.getElementById('smGovde');
  const bagKutu = document.getElementById('smBagimsiz');
  if (!gorunur('raporlar') && !gorunur('stok')) {
    govde.innerHTML = bos('Yetkin yok.'); bagKutu.innerHTML = ''; return;
  }
  govde.innerHTML = '<div class="yukleniyor">Yükleniyor…</div>';
  try {
    const q = smSorgu();
    const d = await api('/api/rapor/stok_maliyet' + (q ? '?' + q : ''));
    const gen = d.genel || {};
    const yaz = (i, v) => document.getElementById(i).textContent = v;
    yaz('smBlokAdet', (gen.blok || {}).adet || 0);
    yaz('smBlokTut', para((gen.blok || {}).toplam_usd || 0));
    yaz('smUrunAdet', (gen.urun || {}).adet || 0);
    yaz('smUrunTut', para((gen.urun || {}).toplam_usd || 0));
    yaz('smBagAdet', (gen.bagimsiz || {}).adet || 0);
    yaz('smBagTut', para((gen.bagimsiz || {}).toplam_usd || 0));
    yaz('smEkTut', para(((gen.blok || {}).kalem_usd || 0)
                      + ((gen.bagimsiz || {}).kalem_usd || 0)
                      + ((gen.urun || {}).kalem_usd || 0)));
    const gl = d.gruplar || [];
    /* Tek sonuç varsa KENDİLİĞİNDEN açık gelsin: tek bir bloğu
       süzen kullanıcı zaten dökümü görmek istiyor. */
    govde.innerHTML = gl.length
      ? gl.map(g => smKart(g, gl.length === 1)).join('')
      : bos('Süzgeçlere uyan blok yok.');
    const bl = d.bagimsiz || [];
    bagKutu.innerHTML = bl.length
      ? bl.map(b => smKart(b, bl.length === 1)).join('')
      : bos('Kesimden gelmeyen ürün yok.');
  } catch (e) { govde.innerHTML = bos('Rapor alınamadı.'); }
}

/* ═══ Kârlılıkta açılır maliyet dökümü ═══
   Liste HAFİF kalsın diye döküm ancak tıklanınca çekiliyor. */
async function satisDokumAc(satisId, sutun) {
  const tr = document.querySelector(`tr[data-sk="${satisId}"]`);
  if (!tr) return;
  const varOlan = tr.nextElementSibling;
  if (varOlan && varOlan.classList.contains('dokum')) {
    varOlan.remove(); return;            // ikinci tık kapatır
  }
  const yeni = document.createElement('tr');
  yeni.className = 'dokum';
  yeni.innerHTML = `<td colspan="${sutun}"><div class="yukleniyor">Yükleniyor…</div></td>`;
  tr.after(yeni);
  try {
    const d = await api(`/api/karlilik/${encodeURIComponent(satisId)}/dokum`);
    const mal = d.maliyet || {}, o = d.ozet || {}, st = d.stok;
    yeni.innerHTML = `<td colspan="${sutun}">
      ${st ? `<div class="sm-alt" style="margin:0 0 7px;padding:0;border:0">
        Stok ${kacar(st.id)}${st.blok_no ? ' · blok ' + kacar(st.blok_no) : ''}${
        st.uretici ? ' · ' + kacar(st.uretici) : ''}</div>` : ''}
      <div class="sm-kalem"><span><span class="e">Alış bedeli</span></span>
        <span></span><span class="son">${para(mal.alim_usd)}</span></div>
      ${(mal.kalemler || []).map(smKalemSatir).join('')}
      <div class="sm-alt">
        Maliyet <strong style="color:var(--murekkep)">${para(mal.toplam_usd)}</strong>
        · Satış <strong style="color:var(--murekkep)">${para(o.satis_usd)}</strong>
        · Kâr <strong style="color:var(--verde)">${para(o.kar_usd)}</strong>
        · Marj <strong style="color:var(--murekkep)">%${(o.marj || 0).toFixed(1).replace('.', ',')}</strong>
        ${(mal.haric || []).length ? '<span class="sm-haric"> · maliyet dışı: '
          + mal.haric.map(h => kacar(h.tip) + ' ' + para(h.usd)).join(', ')
          + '</span>' : ''}
      </div>
      ${d.tutarsizlik ? `<div class="sm-alt sm-haric">
        DİKKAT: kayıttaki maliyet ${para(d.tutarsizlik.kayitta)},
        şu an hesaplanan ${para(d.tutarsizlik.hesaplanan)} —
        stoğa sonradan gider eklenmiş ve bu satış kaydı tazelenmemiş.</div>` : ''}
    </td>`;
  } catch (e) {
    yeni.innerHTML = `<td colspan="${sutun}"><div class="bos">Döküm alınamadı.</div></td>`;
  }
}

const yuklendi = { genel: false, karlilik: false, stok: false, cari: false, sevkiyat: false,
                   performans: false, maliyetanaliz: false, stokmaliyet: false };
const yukleyici = { genel: genelYukle, karlilik: karlilikYukle, stok: stokYukle, cari: cariYukle,
                    sevkiyat: konteynerYukle, performans: performansYukle, maliyetanaliz: maliyetAnalizYukle,
                    stokmaliyet: stokMaliyetYukle };
'''),
    ('tests/test_kritik.py', 'MR1 · tests/test_kritik.py blok 1',
     r'''        assert _k in m, f'{_k} tanımlı değil'
''',
     r'''        assert _k in m, f'{_k} tanımlı değil'


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
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA MR1 — MALİYET RAPORLARI')
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
        print('    python3 yama_mr1.py            # rapor')
        print('    python3 yama_mr1.py --uygula')
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
        print('  ⊙ Yama MR1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_mr1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_mr1'
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
    print('    1. Raporlar -> STOK MALIYETI (yeni sekme).')
    print('       Blok basligina tikla: alis + maliyet kalemleri +')
    print('       toplam + birim maliyet, altinda kesimden cikanlar.')
    print('       Devreden/Iade KDV ayri satirda "maliyet disi".')
    print('    2. Raporlar -> Karlilik -> bir SATIS SATIRINA tikla:')
    print('       o satisin maliyet dokumu altinda acilir.')
    print()
    print('  DEGISEN RAKAM')
    print('    Iptal edilmis (aktif=False) gider artik maliyete')
    print('    GIRMIYOR, tipi bos gider ise artik GIRIYOR. Dort ayri')
    print('    kopya tek kaynaga baglandi. Bazi birim maliyetler ve')
    print('    kar rakamlari bu yuzden degisecek — dogru olan bu.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

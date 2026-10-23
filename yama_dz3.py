#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA DZ3 — SATIŞ · PROFORMA · SİPARİŞ DÜZENLEME
================================================

ÖNKOŞUL: yama_dz2.py uygulanmış olmalı.

── ÖNCE BİR DÜZELTME ──
  DZ3'e başlarken sana "satış kaydı düzenleme zaten çalışıyor,
  ölçtüm" demiştim. O YANLIŞTI. `/api/satislar/<id>` PUT ucu senin
  sistemde yok; benim çalışma kopyamda vardı çünkü oraya benim
  yazmadığım kod eklenmişti (bu, bu gecenin ikinci kez olan
  olayı). Eski tabanlarımın hepsinde o uç yok:

      taban_sd1 / taban_ma1 / taban_dz1 / taban_dz2 : 0 kez
      çalışma kopyam                                : 1 kez

  O kodu ve yanındaki beş testi satır satır okudum, iddialarını
  koddan bağımsız doğruladım (faturaya bağlı satış gerçekten 409
  dönüyor; kur gerçekten satış tarihinden alınıyor) ve DOĞRU
  buldum. Bu yamada "zaten vardı" diye değil, GÖZDEN GEÇİRİLMİŞ
  YENİ KOD olarak gidiyor.

  Sipariş ve proforma düzenleme uçları senin sistemde zaten vardı;
  onlarla ilgili ölçümler geçerli.

── 1 · SATIŞ KAYDI DÜZENLENEBİLİR (YENİ UÇ) ──
  Satış kaydının TUTAR tarafı hiçbir yerden düzenlenemiyordu;
  yalnız fatura no/tarih/not değişiyordu. Yanlış fiyatla girilmiş
  bir satışı düzeltmenin yolu yoktu — kayıt silinemiyordu da.
  Oysa bu kayıt KÂRIN kaynağı: ortaklık hesabı, kârlılık raporu ve
  müşteri özeti hep buradan okuyor.

  Artık tutar / birim fiyat / miktar / döviz / tarih
  düzenlenebiliyor; tutar_usd, kâr ve marj yeniden hesaplanıyor.
  Kur SATIŞ TARİHİNDEKİ kur — bugünün kuruyla çevirmek geçmiş bir
  satışı bugünün kuruyla yeniden fiyatlandırmak olurdu.

  FATURAYA BAĞLI SATIŞ DÜZENLENMEZ (409). O zaman doğrunun kaynağı
  fatura; buradan tutarı değiştirmek belge ile kaydı ayrıştırırdı.
  Sipariş ucu da aynı gerekçeyle kalemleri kilitliyor.

  Ortaklık hesabı satış kayıtlarını CANLI okuyor (OR3'te böyle
  kurmuştuk), o yüzden ciro kendiliğinden takip ediyor — ölçtüm,
  fiyat 1.500 yapılınca ortaklık cirosu 30.000'e çıktı. Mesaj,
  stok bir ortaklık işine bağlıysa bunu söylüyor.

── 2 · PROFORMA TOPLAMI ARTIK SUNUCUDA TÜRETİLİYOR ──
  Proforma toplamı HİÇBİR ZAMAN sunucuda hesaplanmıyordu: hem POST
  hem PUT `toplam=data.get('toplam')` diyordu — rakam neyse
  istemciden geleni yazıyordu.

  ÖLÇÜLDÜ: kalemin birim fiyatını 1.000 → 1.500 yapan bir PUT
  (gövdede `toplam` yok) kalemi güncelledi ama başlıktaki toplam
  20.000'de kaldı. Belge "satır 30.000, toplam 20.000" diye
  basılacaktı — müşteriye giden bir belgede.

  Formül EKRANDAKİNİN AYNISI (proforma.html · toplamlar()):
  kalem toplamı → iskonto → ara toplam → KDV (yalnız yurt içi).
  Başka bir formül yazmak ekranla belgeyi ayrıştırırdı.

  İKİ KORUMA:
    · `net_fiyat` boşsa `toplam_fiyat`, o da boşsa birim × miktar.
      Düz toplasaydım eksik veride toplam SIFIRA düşerdi —
      eskisinden kötü.
    · Türetilen sıfır çıkıp istemci sıfırdan büyük toplam
      gönderdiyse belge sıfırlanmıyor, uyarı veriliyor.

── 3 · PROFORMA ↔ SİPARİŞ AYRIŞMASI ──
  Proforma siparişe dönüştükten sonra düzenlenince ikisi sessizce
  ayrışıyordu. ÖLÇÜLDÜ: proforma 40.000 oldu, sipariş 30.000'de
  kaldı.

  Siparişi proformadan YENİDEN KURMUYORUZ: dönüştürme rezervasyon
  taşıyor, stok bağlıyor, ölçü hesaplıyor; onu geriye doğru
  tekrarlamak sevk edilmiş malı olan bir siparişte zarar verirdi.

  Yapı aynıysa (kalem sayısı ve sırası) yalnız FİYAT taşınıyor —
  satır kayıtları yerinde kalıyor, rezervasyon ve stok bağı
  bozulmuyor. Gerçek durum da bu: müşteriyle fiyat yeniden
  görüşülmüş oluyor. Ve bu da ÖNCE SORULUYOR:

      "Bu proforma SIP-ALC26-02 siparişine dönüştürülmüş.
       Siparişin 1 kaleminin fiyatı da güncellensin mi?
       (30.000,00 → 40.000,00)"

  Onay verilmezse proforma da değişmiyor — sunucu geri alıyor.

  SİPARİŞ KİLİTLİYSE dokunulmuyor: sevkiyat, satış kaydı ya da
  teslim varsa fiyat taşınmıyor, ayrışma söyleniyor. Kilit kuralı
  artık tek yerde (`_siparis_kalem_kilidi`) — iki ayrı kopya
  zamanla birbirinden ayrılırdı.

  Kalem YAPISI değiştiyse (sayı farklı) fiyat taşınamıyor, bu da
  söyleniyor.

── ÖLÇÜLDÜ ──
  API üzerinden önce/sonra:
      satış tutarı 20.000 → 30.000 : kâr 24.000, marj %80
      birim fiyat × miktar          : tutar türetildi; tutar da
                                      verilirse O kazandı
      faturaya bağlı satış          : 409, tutar değişmedi
      proforma kalemi 1.000 → 1.500 : başlık toplamı 30.000 oldu
      net_fiyat boş                 : toplam_fiyat'tan türetildi
      dönüşmüş proformada düzenleme : 409 sordu, onayda ikisi de
                                      40.000 oldu
      kilitli siparişte             : fiyat taşınmadı, uyarı çıktı

  190 test geçti (186 + 4 yeni; 5 test de gözden geçirilen kodla
  birlikte geliyor); iki ayrı koşuda da aynı. firma · js · form ·
  zincir · akis · degismezlik temiz. Tabanı DZ2'yi uygulayarak
  ürettim ve DZ3 testlerinin orada DÜŞTÜĞÜNÜ görerek doğruladım.

── SIRADA ──
      DZ1  maliyet ↔ cari hareket            ✓
      DZ2  stok kayıtları                    ✓
      DZ3  satış / proforma / sipariş        ← bu yama
      DZ4  kesim kayıtları

DOSYALAR
--------
  flask_app.py             satış düzenleme ucu (yeni) · proforma
                           toplamı türetme · sipariş ayrışması ·
                           kilit kuralı tek yerde
  templates/proforma.html  409 → onaylı fiyat taşıma
  tests/test_kritik.py     9 test (4'ü benim, 5'i gözden geçirilen)

Şema yok, göç yok, yeni alan yok.

KULLANIM
--------
  python3 yama_dz3.py            # RAPOR
  python3 yama_dz3.py --uygula
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
    'flask_app.py': 'DZ3 · PROFORMA TOPLAMI SUNUCUDA TÜRETİLİR',
    'templates/proforma.html': "e.yanit.error === 'onay_gerekli'",
    'tests/test_kritik.py': 'def test_dz3_proforma_toplami_kalemlerden_turetilir',
}
ONKOSUL = {
    'flask_app.py': 'DZ2 · ÖLÇÜLER DÜZENLENEBİLİR',
    'templates/proforma.html': 'function toplamlar() {',
    'tests/test_kritik.py': 'def test_dz2_olculer_duzenlenebiliyor_ve_kar_takip_ediyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'DZ3 · flask_app.py blok 1',
     r'''    @app.route('/api/siparis/<siparis_id>', methods=['PUT'])
''',
     r'''    # DZ3: kilit kurali TEK YERDE. Ayni kural hem siparis
    # duzenlemede hem proformadan fiyat tasimada gerekiyor;
    # iki ayri kopya, zamanla birbirinden ayrilirdi.
    def _siparis_kalem_kilidi(sip):
        """Siparisin kalemleri neden degistirilemez — yoksa None."""
        if sip is None:
            return 'sipariş bulunamadı'
        _sevk = Sevkiyat.query.filter_by(siparis_id=sip.id).count()
        _satis = SatisKaydi.query.filter_by(siparis_id=sip.id).count()
        if sip.durum == 'Teslim Edildi':
            return 'sipariş teslim edilmiş'
        if _sevk:
            return f'{_sevk} sevkiyat bağlı'
        if _satis:
            return f'{_satis} satış kaydı bağlı'
        return None

    @app.route('/api/siparis/<siparis_id>', methods=['PUT'])
'''),
    ('flask_app.py', 'DZ3 · flask_app.py blok 2',
     r'''            _sevk = Sevkiyat.query.filter_by(siparis_id=siparis_id).count()
            _satis = SatisKaydi.query.filter_by(siparis_id=siparis_id).count()
            if (sip.durum == 'Teslim Edildi') or _sevk or _satis:
                _neden = ('sipariş teslim edilmiş' if sip.durum == 'Teslim Edildi'
                          else (f'{_sevk} sevkiyat' if _sevk else f'{_satis} satış kaydı') + ' bağlı')
''',
     r'''            _neden = _siparis_kalem_kilidi(sip)
            if _neden:
'''),
    ('flask_app.py', 'DZ3 · flask_app.py blok 3',
     r'''    @app.route('/api/proforma/<proforma_id>', methods=['PUT'])
''',
     r'''    # ══════════════════════════════════════════════════════════
    #  DZ3 · PROFORMA TOPLAMI SUNUCUDA TÜRETİLİR
    #
    #  Proforma toplamı HİÇBİR ZAMAN sunucuda hesaplanmıyordu:
    #  hem POST hem PUT `toplam=data.get('toplam')` diyordu, yani
    #  rakam neyse istemciden geleni yazıyordu.
    #
    #  Ölçüldü: kalemin birim fiyatını 1.000 → 1.500 yapan bir PUT
    #  (gövdede `toplam` yok) kalemi güncelledi ama başlıktaki
    #  toplam 20.000'de kaldı. Belge "satır 30.000, toplam 20.000"
    #  diye basılacaktı — müşteriye giden bir belgede.
    #
    #  Formül EKRANDAKİNİN AYNISI (proforma.html · toplamlar()):
    #      kalemToplam = Σ kalem.net_fiyat
    #      iskonto     = SAB ? sabit : kalemToplam × yüzde/100
    #      ara         = max(0, kalemToplam − iskonto)
    #      kdv         = ara × kdv_oran/100   (yalnız yurt içi)
    #      genel       = ara + kdv
    #  Başka bir formül yazmak, ekranla belgeyi ayrıştırırdı.
    # ══════════════════════════════════════════════════════════
    def _proforma_toplam_hesapla(p):
        """Kalemlerden türetilmiş genel toplam. Kalem yoksa None
        döner — o zaman çağıran mevcut değere dokunmaz."""
        kalemler = ProformaKalem.query.filter_by(proforma_id=p.id).all()
        if not kalemler:
            return None
        # net_fiyat BOS olabilir (eski kayitlar, baska bir cagirici).
        # Dogrudan toplarsak toplam SIFIRA duser — eskisinden kotu.
        # Sirasiyla: net_fiyat -> toplam_fiyat -> birim × miktar.
        def _kalem_net(k):
            for _d in (k.net_fiyat, k.toplam_fiyat):
                if _d not in (None, ''):
                    return _d
            return (k.birim_fiyat or 0) * (k.miktar or 0)
        kalem_toplam = sum(_kalem_net(k) for k in kalemler)
        isk_tip = (getattr(p, 'iskonto_tip', None) or '%')
        if isk_tip == 'SAB':
            iskonto = getattr(p, 'iskonto_sabit', 0) or 0
        else:
            iskonto = kalem_toplam * ((getattr(p, 'iskonto', 0) or 0)) / 100
        ara = max(0, kalem_toplam - iskonto)
        # KDV yalnız yurt içi satışta — ihracatta sıfır.
        kdv_oran = (p.kdv_oran or 0) if (p.tur == 'yurt_ici') else 0
        return q2(ara + ara * kdv_oran / 100)

    @app.route('/api/proforma/<proforma_id>', methods=['PUT'])
'''),
    ('flask_app.py', 'DZ3 · flask_app.py blok 4',
     r'''            db.session.commit()
            msg = 'Proforma guncellendi'
            if rez_count > 0:
                msg += f' ({rez_count} stok rezerve edildi)'
            return jsonify({'ok': True, 'id': p.id, 'mesaj': msg})
''',
     r'''
            # DZ3: KALEMLER DEGISTIYSE TOPLAMI SUNUCU TURETIR.
            # Istemcinin gonderdigi rakama guvenmek, kalemi
            # guncelleyip toplami guncellemeyen her cagirici icin
            # yalan soyleyen bir belge uretiyordu. Istemci de bir
            # rakam gonderdiyse ve tutmuyorsa, TURETILEN kazanir
            # ve fark yanitta soylenir — sessizce duzeltmek de
            # sessizce bozmak kadar kotu.
            _toplam_duzeltme = None
            if 'kalemler' in data:
                _turetilen = _proforma_toplam_hesapla(p)
                _gelen = p.toplam
                if _turetilen is not None:
                    # IKINCI KORUMA: turetilen SIFIR cikmis ama istemci
                    # sifirdan buyuk bir toplam gonderdiyse, elimizdeki
                    # kalem verisi eksik demektir. Belgeyi sifirlamak
                    # yerine gelen rakami birakip UYARIYORUZ.
                    if _turetilen == 0 and (_gelen or 0) > 0:
                        _toplam_duzeltme = {'gelen': _gelen, 'turetilen': 0,
                                            'uygulanmadi': True}
                    elif _gelen is None or abs((_gelen or 0) - _turetilen) > 0.01:
                        _toplam_duzeltme = {'gelen': _gelen,
                                            'turetilen': _turetilen}
                        p.toplam = _turetilen

            # ══════════════════════════════════════════════════
            #  DZ3 · PROFORMA ↔ SİPARİŞ AYRIŞMASI
            #
            #  Proforma siparişe dönüştükten sonra proformayı
            #  düzenlemek ikisini sessizce ayrıştırıyordu. Ölçüldü:
            #  proforma 40.000 oldu, sipariş 30.000'de kaldı.
            #
            #  Siparişi PROFORMADAN YENİDEN KURMUYORUZ: dönüştürme
            #  rezervasyon taşıyor, stok bağlıyor, ölçü hesaplıyor;
            #  onu geriye doğru tekrarlamak sevk edilmiş malı olan
            #  bir siparişte zarar verirdi.
            #
            #  YAPILAN: yapı aynıysa (kalem sayısı ve sırası) yalnız
            #  FİYAT taşınıyor — satır kayıtları yerinde kalıyor,
            #  rezervasyon ve stok bağı bozulmuyor. Gerçek durum da
            #  bu: müşteriyle fiyat yeniden görüşülmüş oluyor.
            #
            #  Yapı değiştiyse ya da sipariş kilitliyse (sevkiyat /
            #  satış kaydı / teslim) dokunmuyoruz, söylüyoruz.
            # ══════════════════════════════════════════════════
            _siparis_uyari = None
            _siparis_guncel = None
            if 'kalemler' in data and p.siparis_id:
                _sip = Siparis.query.get(p.siparis_id)
                if _sip:
                    _sip_toplam = q2(_sip.toplam_tutar or 0)
                    _pf_toplam = q2(p.toplam or 0)
                    if abs(_sip_toplam - _pf_toplam) > 0.01:
                        _kilit = _siparis_kalem_kilidi(_sip)
                        _pk = ProformaKalem.query.filter_by(
                            proforma_id=p.id).order_by(ProformaKalem.sira).all()
                        _sk = SiparisKalem.query.filter_by(
                            siparis_id=_sip.id).order_by(SiparisKalem.sira).all()
                        if _kilit:
                            _siparis_uyari = (
                                f'Bu proforma {_sip.id} siparişine '
                                f'dönüştürülmüş. Sipariş toplamı '
                                f'{_sip_toplam:,.2f} olarak KALDI çünkü '
                                f'{_kilit}. İkisi artık ayrışmış durumda.')
                        elif len(_pk) != len(_sk):
                            _siparis_uyari = (
                                f'Bu proforma {_sip.id} siparişine '
                                f'dönüştürülmüş ama kalem yapısı artık '
                                f'farklı ({len(_pk)} ↔ {len(_sk)}). Fiyat '
                                f'taşınamadı; siparişi elle düzeltmen '
                                f'gerekiyor.')
                        elif not _onay_verildi():
                            db.session.rollback()
                            return jsonify({
                                'ok': False, 'error': 'onay_gerekli',
                                'kapsam': {'siparis_id': _sip.id,
                                           'siparis_toplam': _sip_toplam,
                                           'proforma_toplam': _pf_toplam,
                                           'kalem_sayisi': len(_sk)},
                                'mesaj': f'Bu proforma {_sip.id} siparişine '
                                         f'dönüştürülmüş. Siparişin {len(_sk)} '
                                         f'kaleminin fiyatı da güncellensin '
                                         f'mi? ({_sip_toplam:,.2f} → '
                                         f'{_pf_toplam:,.2f})'}), 409
                        else:
                            for _a, _b in zip(_pk, _sk):
                                _b.birim_fiyat = _a.birim_fiyat
                                _b.toplam_fiyat = (_a.net_fiyat
                                                   if _a.net_fiyat
                                                   else _a.toplam_fiyat)
                            _siparis_toplam_guncelle(_sip)
                            _siparis_guncel = {'id': _sip.id,
                                               'yeni_toplam': _sip.toplam_tutar}

            db.session.commit()
            msg = 'Proforma guncellendi'
            if rez_count > 0:
                msg += f' ({rez_count} stok rezerve edildi)'
            if _siparis_guncel:
                msg += (f' — {_siparis_guncel["id"]} siparişinin fiyatları da '
                        f'güncellendi ({_siparis_guncel["yeni_toplam"]:,.2f})')
            if _siparis_uyari:
                msg += ' — ' + _siparis_uyari
            if _toplam_duzeltme and _toplam_duzeltme.get('uygulanmadi'):
                msg += (' — DİKKAT: kalemlerden türetilen toplam sıfır çıktı '
                        '(kalem tutarları eksik olabilir), gönderilen toplam '
                        'korundu')
            elif _toplam_duzeltme:
                msg += (f' — toplam kalemlerden yeniden hesaplandı: '
                        f'{_toplam_duzeltme["turetilen"]:,.2f} {p.doviz or ""}')
            return jsonify({'ok': True, 'id': p.id, 'mesaj': msg,
                            'toplam': p.toplam,
                            'toplam_duzeltme': _toplam_duzeltme,
                            'siparis_guncel': _siparis_guncel,
                            'siparis_uyari': _siparis_uyari})
'''),
    ('flask_app.py', 'DZ3 · flask_app.py blok 5',
     r'''                     f'Faturalar ekranindan no girip kesin.'})
''',
     r'''                     f'Faturalar ekranindan no girip kesin.'})

    # ══════════════════════════════════════════════════════════
    #  DZ3 · SATIŞ KAYDI DÜZENLENEBİLİR
    #
    #  Satış kaydının TUTAR tarafı hiçbir yerden düzenlenemiyordu:
    #  yalnız fatura no / tarih / not değiştirilebiliyordu
    #  (`/fatura-bilgi`). Yanlış fiyatla ya da yanlış miktarla
    #  girilmiş bir satışı düzeltmenin tek yolu silip yeniden
    #  girmekti — ve satış kaydı silinemiyordu da.
    #
    #  Bu kayıt KÂRIN kaynağı: ortaklık hesabı, kârlılık raporu ve
    #  müşteri özeti hep buradan okuyor. Yanlış kalınca hepsi yanlış
    #  kalıyordu.
    #
    #  FATURAYA BAĞLI SATIŞ DÜZENLENMEZ. O zaman doğrunun kaynağı
    #  fatura; buradan tutarı değiştirmek belge ile kaydı
    #  ayrıştırırdı. Sipariş düzenleme ucu da aynı gerekçeyle
    #  kalemleri kilitliyor — aynı kuralı sürdürüyoruz.
    # ══════════════════════════════════════════════════════════
    @app.route('/api/satislar/<satis_id>', methods=['PUT'])
    def api_satis_guncelle(satis_id):
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        s = SatisKaydi.query.get(satis_id)
        if not s:
            return jsonify({'ok': False, 'mesaj': 'Bulunamadı'}), 404

        if s.fatura_id:
            _f = Fatura.query.get(s.fatura_id)
            return jsonify({'ok': False, 'error': 'faturaya_bagli',
                'mesaj': f'Bu satış {(_f.fatura_no if _f else s.fatura_id)} '
                         f'faturasından doğdu. Tutarı buradan değiştirmek '
                         f'belge ile kaydı ayrıştırır — faturayı '
                         f'düzeltirsen satış kaydı da düzelir.'}), 409

        data = request.get_json(silent=True) or {}
        eski = {'tutar': s.tutar, 'doviz': s.doviz, 'kar': s.kar_usd}

        if data.get('satis_tarihi'):
            _t = _parse_date(data.get('satis_tarihi'))
            if not _t:
                return jsonify({'ok': False,
                                'mesaj': 'Tarih GG.AA.YYYY biçiminde olmalı'}), 400
            s.satis_tarihi = _t
        if data.get('doviz'):
            _dv = str(data['doviz']).strip().upper()
            if _dv not in ('USD', 'EUR', 'TRY'):
                return jsonify({'ok': False,
                                'mesaj': 'Döviz USD, EUR veya TRY olmalı'}), 400
            s.doviz = _dv
        for _alan in ('birim_fiyat', 'miktar', 'tutar'):
            if _alan not in data:
                continue
            try:
                _d = float(data[_alan])
            except (TypeError, ValueError):
                return jsonify({'ok': False,
                                'mesaj': f'{_alan} sayı olmalı'}), 400
            if _d < 0:
                return jsonify({'ok': False,
                                'mesaj': f'{_alan} negatif olamaz'}), 400
            setattr(s, _alan, _d)
        if 'birim' in data:
            s.birim = (data.get('birim') or '').strip() or None
        if 'notlar' in data:
            s.notlar = data.get('notlar')

        # TUTAR: elle verilmediyse birim fiyat × miktardan türet.
        # Ikisi birden verilirse ELLE VERILEN TUTAR kazanir —
        # faturada yuvarlama ya da iskonto olabilir ve belgedeki
        # rakam hesaplanandan onceliklidir.
        if 'tutar' not in data and ('birim_fiyat' in data or 'miktar' in data):
            s.tutar = q2((s.birim_fiyat or 0) * (s.miktar or 0))

        # ── TÜRETİLMİŞ DEĞERLER ──
        # Kur, SATIŞ TARİHİNDEKİ kur olmalı; bugünün kuruyla
        # çevirmek geçmiş bir satışı bugünün kuruyla yeniden
        # fiyatlandırmak demekti.
        _trh = s.satis_tarihi
        s.kur_usd = _kur_getir('USD', _trh) or s.kur_usd or 0
        s.kur_eur = _kur_getir('EUR', _trh) or s.kur_eur or 0
        s.tutar_usd = q2(_usd_cevrim(s.tutar or 0, s.doviz, _trh))
        s.tutar_try = q2((s.tutar or 0) if s.doviz == 'TRY'
                         else (s.tutar or 0) * (_kur_getir(s.doviz, _trh) or 0))
        _maliyet = s.maliyet_usd or 0
        s.kar_usd = q2((s.tutar_usd or 0) - _maliyet)
        s.marj_yuzde = q_oran(((s.kar_usd or 0) / s.tutar_usd * 100)
                              if s.tutar_usd else 0)
        s.guncelleme = datetime.now()
        _log_audit('GUNCELLE', 'satis', s.id,
                   eski=eski,
                   yeni={'tutar': s.tutar, 'doviz': s.doviz,
                         'kar': s.kar_usd})
        db.session.commit()

        # ORTAKLIK: hesap motoru satis kayitlarini CANLI okuyor
        # (OR3'te boyle kurduk), o yuzden burada yeniden hesap
        # gerekmiyor — ama kullanici bilsin diye sayiyoruz.
        _ort = 0
        try:
            _isler = OrtaklikIs.query.filter(
                OrtaklikIs.kaynak_id == s.stok_id).count()
            _ort = _isler
        except Exception:
            _ort = 0
        msg = (f'Satış kaydı güncellendi — {s.tutar_usd:,.2f} USD, '
               f'kâr {s.kar_usd:,.2f} USD')
        if _ort:
            msg += (f'. Bu stok {_ort} ortaklık işine bağlı; '
                    f'ortaklık hesabı satış kayıtlarını canlı okuduğu '
                    f'için oradaki ciro da değişti.')
        return jsonify({'ok': True, 'mesaj': msg,
                        'tutar_usd': s.tutar_usd, 'kar_usd': s.kar_usd,
                        'marj_yuzde': s.marj_yuzde,
                        'ortaklik_isi': _ort})
'''),
    ('templates/proforma.html', 'DZ3 · templates/proforma.html blok 1',
     r'''    const d = DUZENLE_ID
      ? await api(`/api/proforma/${encodeURIComponent(DUZENLE_ID)}`, { method: 'PUT', body: JSON.stringify(payload) })
      : await api('/api/proforma', { method: 'POST', body: JSON.stringify(payload) });
    bildir(d.mesaj || ((DUZENLE_ID ? 'Güncellendi' : 'Oluşturuldu') + ' · ' + (d.id || '')));
    modalKapat(); await yukle();
  } catch (e) { /* */ }
''',
     r'''    let d;
    if (DUZENLE_ID) {
      /* DZ3: proforma siparise donusturulmusse ve toplam degistiyse
         sunucu 409 + kapsam donuyor. Siparisi SESSIZCE degistirmek
         dogru degil — ne olacagini gosterip soruyoruz. Onay
         verilmezse proforma da degismiyor (sunucu geri aliyor). */
      const yol = `/api/proforma/${encodeURIComponent(DUZENLE_ID)}`;
      try {
        d = await api(yol, { method: 'PUT', body: JSON.stringify(payload) });
      } catch (e) {
        if (e && e.status === 409 && e.yanit && e.yanit.error === 'onay_gerekli') {
          if (!await onayla(e.yanit.mesaj)) return;
          d = await api(yol + '?onay=1',
                        { method: 'PUT', body: JSON.stringify(payload) });
        } else { throw e; }
      }
    } else {
      d = await api('/api/proforma', { method: 'POST', body: JSON.stringify(payload) });
    }
    bildir(d.mesaj || ((DUZENLE_ID ? 'Güncellendi' : 'Oluşturuldu') + ' · ' + (d.id || '')));
    modalKapat(); await yukle();
  } catch (e) { /* api() zaten bildiriyor */ }
'''),
    ('tests/test_kritik.py', 'DZ3 · tests/test_kritik.py blok 1',
     r'''    assert 's.metraj_m2 !== undefined ? s.metraj_m2 : s.m2' in h
''',
     r'''    assert 's.metraj_m2 !== undefined ? s.metraj_m2 : s.m2' in h


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
'''),
]
TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA DZ3 — SATIS / PROFORMA / SIPARIS DUZENLEME')
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
        print('    python3 yama_dz3.py            # rapor')
        print('    python3 yama_dz3.py --uygula')
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
        print('  ⊙ Yama DZ3 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_dz3.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_dz3'
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
    print('    1) Satis -> bir satis kaydinda tutari degistir:')
    print('       kar ve marj aninda yeniden hesaplanmali.')
    print('       Faturaya bagli bir satista ise 409 ile reddetmeli.')
    print('    2) Proforma -> kalem fiyatini degistir: BASLIKTAKI')
    print('       toplam da degismeli (eskiden kalmiyordu).')
    print('    3) Siparise donusmus bir proformayi duzenle:')
    print('       siparisin de guncellenip guncellenmeyecegini SORMALI.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

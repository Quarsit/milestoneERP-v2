#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA IP1 — İPTAL, PARA İZLERİNİ SORMADAN BIRAKMAZ
===================================================

ÖNKOŞUL: **yama_hs1.py uygulanmış olmalı.** Betik denetliyor.
Şema değişikliği YOK, göç YOK.

Kullanım:
    python3 yama_ip1.py              # rapor, dosyalara dokunmaz
    python3 yama_ip1.py --uygula
    venv/bin/python -m pytest tests/test_kritik.py -q     # 314

═══ ÖLÇÜLEN DURUM ═══

Senin yaptığın sırayı birebir yeniden ürettim. Dört ayrı kusur
çıktı ve sonuçta cariye 3.024 $ HAYALET ALACAK kalıyordu —
müşteri alacaklı görünüyordu:

 1. SİPARİŞ İPTALİ HİÇBİR ŞEYİ GERİ ALMIYORDU.
    Fatura "Tahsil Edildi" kalıyor, cariye yazılan borç duruyor,
    stoklar satılmış kalıyordu. Ekran "Bağlı stoklar serbest
    bırakılır" diyordu; bırakmıyordu da.

 2. ÇEKİ SİLMEK "bağlı kayıtlar geri alındı" DİYOR AMA ALMIYORDU.
    Geri alma yalnız `cek.cari_hareket_id` bağına bakıyor; hızlı
    satış o alanı hiç doldurmuyordu. Hareket `baglanti_tip='cek'`
    ile bağlıydı ve kimse oraya bakmıyordu. TS1'de tahsilatta
    yaşadığımızın aynısı — kod doğru, bağ eksik.

 3. HIZLI SATIŞ STOKLARI 'Teslim Edildi' YAPIYORDU.
    Serbest bırakma yalnız Satildi/Rezerve'ye dokunduğu için
    plakalar KALICI olarak kilitli kalıyordu: ne serbest, ne
    satılabilir. Üstelik sipariş iptali rezervasyonları da
    kapattığı için sonradan kurtarmanın yolu yoktu.

 4. FATURA İPTALİNİN GERİ ALMA MANTIĞI TEK YERDE KİLİTLİYDİ.
    Sipariş iptali aynı işi yapmak zorundaydı; ikinci kez yazmak
    AF1/TS1/EM2/KD1'de defalarca düzelttiğimiz "iki ayrı gerçek"
    durumunu kurardı.

═══ NE YAPILDI ═══

KARAR SENİN, SİSTEMİN DEĞİL. Sunucu para kaydı görürse iptali
REDDEDİYOR (409) ve neyin kararını beklediğini söylüyor: hangi
fatura, ne kadar cari borç, hangi çek, hangi tahsilat. Ekran bunu
alıp sırayla soruyor:

  1) "Bu siparişin faturası var: MLS2026000058882 · 3.024,00 USD
      cariye yazılan 3.024,00 USD borç SİLİNECEK.
      Sipariş iptal edilirse bu fatura da İPTAL edilecek…"
      → onaylanmazsa HİÇBİR ŞEYE dokunulmaz.

  2) "Bu satış için alınmış çek var: C2100028883 · 3.024,00 USD"
      → İade edilsin — çek iptal, cari alacağı silinsin
      → Bizde kalsın — müşterinin cari ALACAĞI olsun

  3) Nakit/diğer tahsilat varsa aynı soru:
      → Geri alınsın (kasa hareketi de geri alınır)
      → Dursun — müşterinin cari ALACAĞI olsun

"Bizde kalsın" dendiğinde çek faturadan KOPARILIYOR. Koparılmazsa
fatura iptali "tahsilat var" diye reddediyor ve kullanıcı çıkmaza
giriyordu (eski H3 notunda aynı kilit anlatılıyor).

Ayrıca:
  · `_fatura_iptal_geri_al` TEK KAPI oldu; fatura durum ucu da
    sipariş iptali de onu çağırıyor.
  · `_cari_hareket_geri_al` TEK KAPI oldu; hem `cari_hareket_id`
    hem belge bağı üzerinden arıyor (TS1 kalıbı).
  · Hızlı satış stokları 'Satildi' bırakıyor.

NORMAL FATURA YOLU DEĞİŞMEDİ: orada stok hâlâ 'Teslim Edildi'
oluyor. Fatura kesmek ile teslim etmek ayrı olaylar ve sevkiyatın
kendi Sevkedildi/Teslim Edildi adımları var; bu AYRI bir karar
olduğu için sana sormadan değiştirmedim.

═══ DOĞRULAMA ═══

  · 314 test geçiyor (306 → 314)
  · 8 IP1 testinin HEPSİ tabanda düşüyor
  · Çek İADE seçilince: cari 0 hareket, 0 satış kaydı, 5 plaka
    Serbest, fatura Iptal, çek Iptal
  · Çek BİZDE KALSIN seçilince: fatura borcu silinir, çek
    Portfoyde kalır, alacağı durur → müşteri 3.024 USD alacaklı
    (doğrusu bu: parayı aldık, malı vermedik)
  · Tarayıcıda baştan sona tıklandı: üç pencere de çıkıyor,
    seçenekler okunuyor, sonuç bildirimi doğru
  · O koşuda kendi hatamı yakaladım: fatura satırı "0,00 USD"
    yazıyordu (çekte `tutar`, faturada `toplam` alanı var).
    Tarayıcıda açmasam fark etmezdim.
  · `js_denetim.py` temiz · 29 şablon ayrıştırılabiliyor
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
    'flask_app.py': 'def _siparis_iptal_kararlarini_uygula(sip, karar, onay)',
    'templates/siparis.html': '_iptalKararlariniSor',
    'tests/test_kritik.py': 'def test_ip1_faturali_siparis_iptali_karar_istiyor',
}
ONKOSUL = {
    'flask_app.py': '#  HS1 · KDV FATURAYA HİÇ YANSIMIYORDU',
    'templates/siparis.html': 'async function durumGecir(id, yeni)',
    'tests/test_kritik.py': 'def test_hs1_kdv_faturaya_ve_cariye_yansiyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'IP1 · flask_app.py blok 1',
     r'''    def _siparis_stoklarini_serbest_birak(siparis_id, neden='Siparis iptal'):
''',
     r'''    # ══════════════════════════════════════════════════════════════
    #  IP1 · SİPARİŞ İPTALİNDE KARAR GEREKEN NOKTALAR
    #
    #  Sipariş iptali bir açılır liste seçimi, ama arkasında fatura,
    #  cari borç, alınmış çek ve tahsil edilmiş para olabiliyor.
    #  Sistemin bunların ne olacağını TAHMİN etmesi doğru değil:
    #  alınan çek iade mi edilecek yoksa müşterinin bizde duran
    #  parası mı olacak — bu bir iş kararı.
    #
    #  Bu fonksiyon yalnızca DURUMU ANLATIR, hiçbir şey değiştirmez.
    # ══════════════════════════════════════════════════════════════
    def _siparis_iptal_karari(sip):
        """İptal için karar gereken noktaları toplar. Yoksa None."""
        faturalar = Fatura.query.filter(
            Fatura.siparis_id == sip.id,
            Fatura.durum.notin_(['Iptal', 'Taslak'])).all()
        if not faturalar:
            return None
        f_bilgi, cek_bilgi, tahsilat_bilgi = [], [], []
        for f in faturalar:
            _borc = CariHareket.query.filter_by(
                baglanti_tip='fatura', baglanti_id=f.id,
                kaynak='fatura').first()
            f_bilgi.append({
                'id': f.id, 'no': f.fatura_no, 'durum': f.durum,
                'toplam': q2(f.toplam or 0), 'doviz': f.doviz or 'USD',
                'cari_borc': q2(_borc.borc or 0) if _borc else 0,
            })
            for ck in Cek.query.filter_by(fatura_id=f.id).filter(
                    Cek.durum.notin_(['Iptal', 'Karsiliksiz']),
                    Cek.aktif == True).all():        # noqa: E712
                cek_bilgi.append({
                    'id': ck.id, 'no': ck.cek_no or ck.id,
                    'banka': ck.banka_adi, 'tutar': q2(ck.tutar or 0),
                    'doviz': ck.doviz or 'USD', 'durum': ck.durum,
                    'vade': ck.vade_tarihi.isoformat() if ck.vade_tarihi else None,
                })
            for h in CariHareket.query.filter(
                    CariHareket.baglanti_tip == 'fatura',
                    CariHareket.baglanti_id == f.id,
                    CariHareket.alacak > 0,
                    db.func.coalesce(CariHareket.kaynak, '') != 'avans_mahsup'
            ).all():
                tahsilat_bilgi.append({
                    'hareket_id': h.id, 'tutar': q2(h.alacak or 0),
                    'doviz': h.doviz or 'USD',
                    'aciklama': h.aciklama or h.islem_tip,
                })
        return {'faturalar': f_bilgi, 'cekler': cek_bilgi,
                'tahsilatlar': tahsilat_bilgi}

    def _siparis_iptal_kararlarini_uygula(sip, karar, onay):
        """Kullanıcının kararlarını uygular. Döner: (mesaj, hata).

        `onay`:
          fatura_iptal : True ise faturalar iptal edilir
          cek          : 'iade'   -> çek iptal, alacağı silinir
                         'alacak' -> çek durur, faturadan KOPARILIR;
                                     müşterinin cari alacağı olur
          tahsilat     : 'sil'    -> tahsilat hareketi silinir
                         'alacak' -> hareket durur, faturadan koparılır
        """
        if not onay.get('fatura_iptal'):
            return '', ('Fatura iptal edilmeden sipariş iptal edilemez: '
                        'faturanın borcu cariye yazılmış durumda.')
        mesaj = []
        cek_karar = (onay.get('cek') or 'iade').lower()
        tah_karar = (onay.get('tahsilat') or 'sil').lower()

        # ── 1) ÇEKLER ──
        for c_b in karar.get('cekler', []):
            ck = Cek.query.get(c_b['id'])
            if not ck:
                continue
            if cek_karar == 'iade':
                _cari_hareket_geri_al('cek', ck.id, ck.cari_hareket_id)
                ck.cari_hareket_id = None
                _eski = ck.durum
                ck.aktif = False
                ck.durum = 'Iptal'
                ck.fatura_id = None
                _cek_hareket_ekle(ck, 'İptal', _eski, 'Iptal',
                                  f'Sipariş {sip.id} iptali — çek iade edildi')
                mesaj.append(f"{c_b['no']} çeki iade edildi "
                             f"({c_b['tutar']:,.2f} {c_b['doviz']})")
            else:
                # Çek bizde kalıyor: artık bir faturanın tahsilatı
                # değil, müşterinin bizdeki parası. Faturadan
                # KOPARILMAZSA fatura iptali "tahsilat var" diye
                # reddedilir ve kullanıcı çıkmaza girer.
                ck.fatura_id = None
                ck.aciklama = ((ck.aciklama or '') +
                               f' · Sipariş {sip.id} iptal edildi, '
                               f'çek cari alacak olarak kaldı').strip()
                mesaj.append(f"{c_b['no']} çeki cari alacak olarak kaldı "
                             f"({c_b['tutar']:,.2f} {c_b['doviz']})")

        # ── 2) NAKİT/DİĞER TAHSİLATLAR ──
        for t_b in karar.get('tahsilatlar', []):
            h = CariHareket.query.get(t_b['hareket_id'])
            if not h:
                continue
            if tah_karar == 'sil':
                _hareket_kasa_geri_al(h)       # TS1 · kasa da geri alınır
                db.session.delete(h)
                mesaj.append(f"{t_b['tutar']:,.2f} {t_b['doviz']} tahsilat "
                             f"geri alındı")
            else:
                h.baglanti_tip = 'cari'
                h.baglanti_id = None
                h.aciklama = ((h.aciklama or '') +
                              f' · Sipariş {sip.id} iptal edildi, '
                              f'tutar cari alacak olarak kaldı').strip()
                mesaj.append(f"{t_b['tutar']:,.2f} {t_b['doviz']} tahsilat "
                             f"cari alacak olarak kaldı")
        db.session.flush()

        # ── 3) FATURALAR ──
        for f_b in karar.get('faturalar', []):
            f = Fatura.query.get(f_b['id'])
            if not f:
                continue
            _ek = _fatura_iptal_geri_al(f)     # TEK KAPI
            f.durum = 'Iptal'
            _log_audit('DURUM', 'fatura', f.id,
                       eski={'durum': f_b['durum']}, yeni={'durum': 'Iptal'},
                       aciklama=f'Siparis {sip.id} iptali')
            mesaj.append(f"{f_b['no']} faturası iptal edildi"
                         + (_ek.strip() and ' (' + _ek.strip() + ')' or ''))
        db.session.flush()
        return (' ' + ' · '.join(mesaj) + '.') if mesaj else '', None

    def _siparis_stoklarini_serbest_birak(siparis_id, neden='Siparis iptal'):
'''),
    ('flask_app.py', 'IP1 · flask_app.py blok 2',
     r'''    def _fatura_satis_kaydi_olustur(fatura_id):
        """
        Fatura 'Kesildi' olunca SatisKaydi olusturur (kar hesabi icin).
''',
     r'''    def _fatura_satis_kaydi_olustur(fatura_id, stok_durumu='Teslim Edildi'):
        """
        Fatura 'Kesildi' olunca SatisKaydi olusturur (kar hesabi icin).

        IP1 · `stok_durumu`: satılan stoğun alacağı durum. Varsayılan
        'Teslim Edildi' (eski davranış, bütün fatura yolları böyle).
        HIZLI SATIŞ 'Satildi' veriyor: ölçüldü, 'Teslim Edildi' olan
        stok sipariş iptalinde serbest bırakılamıyor (serbest bırakma
        yalnız Satildi/Rezerve'ye dokunuyor) ve plakalar kalıcı
        olarak kilitli kalıyordu.
        NOT: aynı şey normal fatura yolunda da oluyor — fatura kesmek
        ile teslim etmek ayrı olaylar ve sevkiyat akışının kendi
        Sevkedildi/Teslim Edildi adımları var. Orası AYRI bir karar
        olduğu için burada değiştirilmedi.
'''),
    ('flask_app.py', 'IP1 · flask_app.py blok 3',
     r'''                stok.durum = 'Teslim Edildi'
''',
     r'''                stok.durum = stok_durumu          # IP1
'''),
    ('flask_app.py', 'IP1 · flask_app.py blok 4',
     r'''                sk_adet, sk_hata = _fatura_satis_kaydi_olustur(fatura.id)
''',
     r'''                sk_adet, sk_hata = _fatura_satis_kaydi_olustur(
                    fatura.id, stok_durumu='Satildi')   # IP1 · hızlı satış
'''),
    ('flask_app.py', 'IP1 · flask_app.py blok 5',
     r'''                _cari_hareket_ekle(
                    cari_unvan=musteri, islem_tip='Çek Tahsilatı',
                    borc=0, alacak=cek.tutar or 0, doviz=doviz,
                    aciklama=f'Çek alındı (No: {cek.cek_no or cek.id}) — {fatura.fatura_no}',
                    kaynak='cek', baglanti_tip='cek', baglanti_id=cek.id,
                    vade_tarihi=cek.vade_tarihi, evrak_no=cek.cek_no or cek.id)
''',
     r'''                # IP1: dönen hareket ÇEKE BAĞLANIYOR. Eskiden dönüş
                # değeri atılıyordu ve `cek.cari_hareket_id` boş
                # kalıyordu; çek silindiğinde geri alma o bağı arayıp
                # bulamıyor, alacak cariye asılı kalıyordu.
                _cek_ch = _cari_hareket_ekle(
                    cari_unvan=musteri, islem_tip='Çek Tahsilatı',
                    borc=0, alacak=cek.tutar or 0, doviz=doviz,
                    aciklama=f'Çek alındı (No: {cek.cek_no or cek.id}) — {fatura.fatura_no}',
                    kaynak='cek', baglanti_tip='cek', baglanti_id=cek.id,
                    vade_tarihi=cek.vade_tarihi, evrak_no=cek.cek_no or cek.id)
                if _cek_ch:
                    db.session.flush()
                    cek.cari_hareket_id = _cek_ch.id
'''),
    ('flask_app.py', 'IP1 · flask_app.py blok 6',
     r'''            sip.durum = yeni_durum
            ekstra = locals().get('ekstra_zorla', '')
''',
     r'''            # ══════════════════════════════════════════════════════
            #  IP1 · İPTAL, PARA İZLERİNİ SORMADAN BIRAKMAZ
            #
            #  ÖLÇÜLDÜ: faturası kesilmiş bir siparişi iptal etmek
            #  HİÇBİR ŞEYİ geri almıyordu. Fatura "Tahsil Edildi"
            #  kalıyor, cariye yazılan 3.024 $ borç duruyor, stoklar
            #  satılmış kalıyordu. Kullanıcı iptal ettiğini sanıyor,
            #  cari hesapta hayalet bakiye kalıyordu.
            #
            #  Karar kullanıcınındır, sistemin değil: fatura iptal
            #  edilsin mi, alınan para/çek iade mi edilsin yoksa
            #  cariye ALACAK olarak mı kalsın. Sunucu kararı tahmin
            #  etmez — neyin kararını beklediğini söyleyerek 409
            #  döner, ekran sırayla sorar, cevapla birlikte tekrar
            #  çağırır.
            # ══════════════════════════════════════════════════════
            if yeni_durum == 'Iptal Edildi' and eski_durum != 'Iptal Edildi':
                _karar = _siparis_iptal_karari(sip)
                _onay = data.get('iptal_onay') or {}
                if _karar and not _onay:
                    return jsonify({
                        'ok': False, 'error': 'iptal_onayi_gerekli',
                        'mesaj': 'Bu siparişin para kayıtları var. '
                                 'İptal etmeden önce bunların ne olacağına '
                                 'karar vermen gerekiyor.',
                        'karar': _karar}), 409
                if _karar:
                    _ek_iptal, _hata = _siparis_iptal_kararlarini_uygula(
                        sip, _karar, _onay)
                    if _hata:
                        db.session.rollback()
                        return jsonify({'ok': False, 'error': 'iptal_uygulanamadi',
                                        'mesaj': _hata}), 400
                else:
                    _ek_iptal = ''
            else:
                _ek_iptal = ''

            sip.durum = yeni_durum
            ekstra = locals().get('ekstra_zorla', '') + _ek_iptal
'''),
    ('flask_app.py', 'IP1 · flask_app.py blok 7',
     r'''        fatura_id_etkilenen = c.fatura_id
        if c.cari_hareket_id:
            ch = CariHareket.query.get(c.cari_hareket_id)
            if ch:
                db.session.delete(ch)
                c.cari_hareket_id = None
''',
     r'''        #
        # IP1 · ÖLÇÜLDÜ: burası yalnızca `c.cari_hareket_id` bağına
        # bakıyordu ve hızlı satış o alanı hiç doldurmuyordu. Çek
        # silindiğinde "bağlı kayıtlar geri alındı" deniyor ama cari
        # hareket DURUYORDU — müşteri 3.024 $ alacaklı kalıyordu.
        # Artık belge bağı üzerinden de aranıyor (TS1 kalıbı).
        fatura_id_etkilenen = c.fatura_id
        _silinen_ch = _cari_hareket_geri_al('cek', c.id, c.cari_hareket_id)
        if _silinen_ch:
            c.cari_hareket_id = None
'''),
    ('flask_app.py', 'IP1 · flask_app.py blok 8',
     r'''    @app.route('/api/fatura/<fatura_id>/durum', methods=['POST'])
''',
     r'''    # ══════════════════════════════════════════════════════════════
    #  IP1 · BİR FATURANIN İPTALİNİ GERİ ALAN TEK KAPI
    #
    #  Bu gövde `api_fatura_durum` içindeydi. Sipariş iptali de aynı
    #  işi yapmak zorunda (işin sahibi "sipariş iptal edilirse fatura
    #  da iptal edilsin mi diye sorsun" dedi) ve mantığı ikinci kez
    #  yazmak, AF1/TS1/EM2/KD1'de defalarca düzelttiğimiz "iki ayrı
    #  gerçek" durumunu kurardı. Tek kapı, iki çağıran.
    #
    #  SORUMLULUĞU: faturanın PARA izlerini geri almak. Faturanın
    #  durumunu DEĞİŞTİRMEZ, tahsilat denetimi YAPMAZ — ikisi de
    #  çağıranın işi. Çağıran, tahsilat/çek kararlarını kendisi
    #  vermiş olmalı.
    # ══════════════════════════════════════════════════════════════
    def _fatura_iptal_geri_al(f):
        """Faturanın borç hareketini, mahsubunu ve satış kayıtlarını
        geri alır; bağlı sipariş/proformayı geri çeker.

        Döner: olanları anlatan metin (boş olabilir).
        """
        fatura_id = f.id
        ekstra = ''
        # AM1: önce mahsup geri alınır — avans siparişe döner.
        _geri, _geri_dv = _fatura_avans_mahsup_geri_al(f)
        borc_hareket = CariHareket.query.filter_by(
            baglanti_tip='fatura', baglanti_id=fatura_id, kaynak='fatura').first()
        if borc_hareket:
            db.session.delete(borc_hareket)
            ekstra = ' Borc hareketi geri alindi.'
        if _geri > 0:
            ekstra += (f' {_geri:,.2f} {_geri_dv} avans mahsubu geri alindi '
                       f'(avans siparise dondu).')
        # Bu faturadan olusan SatisKaydi'lari sil (karlilikten dus)
        sat_kayitlar = SatisKaydi.query.filter_by(fatura_id=fatura_id).all()
        for sk in sat_kayitlar:
            # Stoklu satista stok durumunu geri al
            if sk.stok_tip in ('BLOK', 'PLAKA', 'EBATLI'):
                stok = _stok_getir(sk.stok_id, sk.stok_tip)
                if stok and stok.durum == 'Teslim Edildi':
                    stok.durum = 'Satildi'
            db.session.delete(sk)
        if sat_kayitlar:
            ekstra += f' {len(sat_kayitlar)} satis kaydi geri alindi.'

        # ── DURUM SENKRONIZASYONU: Fatura Iptal -> bagli siparis geri "Onaylandi" ──
        if f.siparis_id:
            sip = Siparis.query.get(f.siparis_id)
            if sip and sip.durum in ('Hazir', 'Teslim Edildi'):
                eski_sip_durum = sip.durum
                sip.durum = 'Onaylandi'
                ekstra += f' Bagli siparis {sip.id} durumu: {eski_sip_durum} -> Onaylandi.'
                app.logger.info(f'[SENKRO] Fatura {fatura_id} Iptal -> Siparis {sip.id}: {eski_sip_durum} -> Onaylandi')

        # ── DURUM SENKRONIZASYONU: Fatura Iptal -> bagli proforma geri "Onaylandi" ──
        if f.proforma_id:
            pf = Proforma.query.get(f.proforma_id)
            if pf and pf.durum == 'Faturalandi':
                pf.durum = 'Onaylandi'
                ekstra += f' Bagli proforma {pf.id} durumu: Faturalandi -> Onaylandi.'
                app.logger.info(f'[SENKRO] Fatura {fatura_id} Iptal -> Proforma {pf.id}: Faturalandi -> Onaylandi')
        return ekstra

    # ══════════════════════════════════════════════════════════════
    #  IP1 · BİR BELGENİN CARİ HAREKETLERİNİ GERİ ALAN TEK KAPI
    #
    #  TS1'in kalıbı. ÖLÇÜLDÜ: çeki silmek "bağlı kayıtlar geri
    #  alındı" diyor ama cari hareket DURUYORDU — geri alma yalnızca
    #  `cek.cari_hareket_id` bağına bakıyor, hızlı satış ise o alanı
    #  hiç doldurmuyordu. Hareket `baglanti_tip`/`baglanti_id` ile
    #  bağlıydı ve kimse oraya bakmıyordu.
    #
    #  Artık iki yoldan da aranıyor: hangi yol kullanılmışsa hareket
    #  bulunur. Yarın üçüncü bir yol çek üretirse de çalışır.
    # ══════════════════════════════════════════════════════════════
    def _cari_hareket_geri_al(baglanti_tip, baglanti_id, hareket_id=None):
        """Bir belgeye bağlı cari hareketleri siler. Döner: silinen sayı."""
        bulunan = {}
        if hareket_id:
            h = CariHareket.query.get(hareket_id)
            if h:
                bulunan[h.id] = h
        for h in CariHareket.query.filter_by(
                baglanti_tip=baglanti_tip, baglanti_id=baglanti_id).all():
            bulunan[h.id] = h
        for h in bulunan.values():
            db.session.delete(h)
        return len(bulunan)

    @app.route('/api/fatura/<fatura_id>/durum', methods=['POST'])
'''),
    ('flask_app.py', 'IP1 · flask_app.py blok 9',
     r'''            # AM1: önce mahsup geri alınır — avans siparişe döner.
            _geri, _geri_dv = _fatura_avans_mahsup_geri_al(f)
            borc_hareket = CariHareket.query.filter_by(
                baglanti_tip='fatura', baglanti_id=fatura_id, kaynak='fatura').first()
            if borc_hareket:
                db.session.delete(borc_hareket)
                ekstra = ' Borc hareketi geri alindi.'
            if _geri > 0:
                ekstra += (f' {_geri:,.2f} {_geri_dv} avans mahsubu geri alindi '
                           f'(avans siparise dondu).')
            # Bu faturadan olusan SatisKaydi'lari sil (karlilikten dus)
            sat_kayitlar = SatisKaydi.query.filter_by(fatura_id=fatura_id).all()
            for sk in sat_kayitlar:
                # Stoklu satista stok durumunu geri al
                if sk.stok_tip in ('BLOK', 'PLAKA', 'EBATLI'):
                    stok = _stok_getir(sk.stok_id, sk.stok_tip)
                    if stok and stok.durum == 'Teslim Edildi':
                        stok.durum = 'Satildi'
                db.session.delete(sk)
            if sat_kayitlar:
                ekstra += f' {len(sat_kayitlar)} satis kaydi geri alindi.'

            # ── DURUM SENKRONIZASYONU: Fatura Iptal -> bagli siparis geri "Onaylandi" ──
            if f.siparis_id:
                sip = Siparis.query.get(f.siparis_id)
                if sip and sip.durum in ('Hazir', 'Teslim Edildi'):
                    eski_sip_durum = sip.durum
                    sip.durum = 'Onaylandi'
                    ekstra += f' Bagli siparis {sip.id} durumu: {eski_sip_durum} -> Onaylandi.'
                    app.logger.info(f'[SENKRO] Fatura {fatura_id} Iptal -> Siparis {sip.id}: {eski_sip_durum} -> Onaylandi')

            # ── DURUM SENKRONIZASYONU: Fatura Iptal -> bagli proforma geri "Onaylandi" ──
            if f.proforma_id:
                pf = Proforma.query.get(f.proforma_id)
                if pf and pf.durum == 'Faturalandi':
                    pf.durum = 'Onaylandi'
                    ekstra += f' Bagli proforma {pf.id} durumu: Faturalandi -> Onaylandi.'
                    app.logger.info(f'[SENKRO] Fatura {fatura_id} Iptal -> Proforma {pf.id}: Faturalandi -> Onaylandi')
''',
     r'''            # IP1 · geri alma TEK KAPIDAN. Sipariş iptali de aynı
            # kapıyı çağırıyor; iki yerde iki ayrı "fatura nasıl geri
            # alınır" olması, birinin eksik kalması demekti.
            ekstra += _fatura_iptal_geri_al(f)
'''),
    ('templates/siparis.html', 'IP1 · templates/siparis.html blok 1',
     r'''async function durumGecir(id, yeni) {
  if (yeni === 'Iptal Edildi' && !await onayla('Sipariş iptal edilsin mi? Bağlı stoklar serbest bırakılır.')) return;
''',
     r'''/* ══════════════════════════════════════════════════════════════════
   IP1 · İPTAL, PARA KAYITLARINI SORARAK GERİ ALIR

   ESKİDEN: "Sipariş iptal edilsin mi? Bağlı stoklar serbest
   bırakılır." diye soruyor, sonra HİÇBİR ŞEY geri almıyordu.
   Ölçüldü: fatura "Tahsil Edildi" kalıyor, cariye yazılan borç
   duruyor, stoklar satılmış kalıyordu. Kullanıcı iptal ettiğini
   sanıyor, cari hesapta hayalet bakiye kalıyordu.

   ŞİMDİ: sunucu para kaydı görürse 409 + `karar` döner; burada
   sırayla sorulur ve cevaplar `iptal_onay` ile geri gönderilir.
   Kararı sistem değil kullanıcı verir: alınan çek iade mi edilecek,
   yoksa müşterinin bizde duran parası mı olacak — bu bir iş kararı.
   ═══════════════════════════════════════════════════════════════ */
/* Fatura `toplam`, çek/tahsilat `tutar` taşıyor. İlk yazdığımda
   yalnız `tutar`a bakıyordum ve fatura satırı "0,00 USD" çıkıyordu —
   tarayıcıda açıp görmesem fark etmezdim. */
function _ipPara(x) {
  const v = Number(x.tutar != null ? x.tutar : x.toplam) || 0;
  return v.toLocaleString('tr-TR',
    { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ' + (x.doviz || '');
}

async function _iptalKararlariniSor(karar) {
  const fl = karar.faturalar || [];
  const ck = karar.cekler || [];
  const th = karar.tahsilatlar || [];

  /* 1 · FATURA — iptalin kapısı. Onaylanmazsa hiçbir şeye
     dokunulmaz; sipariş olduğu gibi kalır. */
  if (fl.length) {
    const satirlar = fl.map(f => `• ${f.no} · ${_ipPara(f)} (${f.durum})`
      + (f.cari_borc ? `\n   cariye yazılan ${_ipPara({ tutar: f.cari_borc, doviz: f.doviz })} borç SİLİNECEK` : ''));
    const onay = await onayla(
      `Bu siparişin ${fl.length > 1 ? fl.length + ' faturası' : 'faturası'} var:\n\n`
      + satirlar.join('\n') + '\n\n'
      + 'Sipariş iptal edilirse bu fatura da İPTAL edilecek ve '
      + 'faturadan doğan cari borç kaydı ile satış kayıtları geri '
      + 'alınacak.\n\nDevam edilsin mi?',
      { tamam: 'Faturayı da iptal et', tehlike: true });
    if (!onay) return null;
  }

  const onaylar = { fatura_iptal: true };

  /* 2 · ÇEK — iade mi, cari alacak mı. İkisi de geçerli: çek bizde
     kalırsa müşterinin bizdeki parası olur. */
  if (ck.length) {
    const liste = ck.map(x => `${x.no}${x.banka ? ' · ' + x.banka : ''} · ${_ipPara(x)}`
      + (x.vade ? ' · vade ' + x.vade : '')).join('\n');
    const sec = await soruSor(
      `Bu satış için alınmış ${ck.length > 1 ? ck.length + ' çek' : 'çek'} var:\n\n`
      + liste + '\n\nÇek ne olsun?',
      'iade',
      { etiket: 'Çek',
        secenekler: [
          ['iade', 'İade edilsin — çek iptal, cari alacağı silinsin'],
          ['alacak', 'Bizde kalsın — müşterinin cari ALACAĞI olsun'],
        ],
        tamam: 'Devam' });
    if (sec === null) return null;
    onaylar.cek = sec;
  }

  /* 3 · NAKİT / DİĞER TAHSİLAT */
  if (th.length) {
    const liste = th.map(x => `${x.aciklama || 'Tahsilat'} · ${_ipPara(x)}`).join('\n');
    const sec = await soruSor(
      `Bu faturaya yapılmış tahsilat var:\n\n` + liste
      + '\n\nTahsilat ne olsun?',
      'sil',
      { etiket: 'Tahsilat',
        secenekler: [
          ['sil', 'Geri alınsın — tahsilat ve kasa hareketi silinsin'],
          ['alacak', 'Dursun — müşterinin cari ALACAĞI olsun'],
        ],
        tamam: 'Devam' });
    if (sec === null) return null;
    onaylar.tahsilat = sec;
  }
  return onaylar;
}

async function durumGecir(id, yeni) {
  if (yeni === 'Iptal Edildi' && !await onayla('Sipariş iptal edilsin mi? Bağlı stoklar serbest bırakılır.')) return;
  let karar = null;
'''),
    ('templates/siparis.html', 'IP1 · templates/siparis.html blok 2',
     r'''  } catch (e) { /* api() bildirdi */ }
''',
     r'''    return;
  } catch (e) {
    /* 409 + karar: sunucu neyin kararını beklediğini söyledi.
       api() 409'da bildirim GÖSTERMEZ, hatayı yanıtla fırlatır. */
    if (e && e.status === 409 && e.yanit
        && e.yanit.error === 'iptal_onayi_gerekli') {
      karar = e.yanit.karar || {};
    } else {
      return;                       /* başka hata: api() bildirdi */
    }
  }
  const onaylar = await _iptalKararlariniSor(karar);
  if (!onaylar) { bildir('İptal edilmedi — hiçbir şeye dokunulmadı.'); return; }
  try {
    const d2 = await api(`/api/siparis/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body: JSON.stringify({ durum: yeni, iptal_onay: onaylar })
    });
    bildir(d2.mesaj || 'Sipariş iptal edildi');
    cekmeceKapat();
    await yukle();
  } catch (e2) { /* api() bildirdi */ }
'''),
    ('tests/test_kritik.py', 'IP1 · tests/test_kritik.py blok 1',
     r'''    assert 'Çek Vadesi' in b, 'çek vadesi etiketi belirsiz'
''',
     r'''    assert 'Çek Vadesi' in b, 'çek vadesi etiketi belirsiz'


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
'''),
]

def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA IP1 — İPTAL PARA İZLERİNİ GERİ ALIR')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    # ── --yaz-gecici ──
    # base64 gömülü iki dosyayı /tmp'ye çıkarır, PROJEYE DOKUNMAZ.
    # Tam dosya yazan bir yamayı önce okumak istemek yerinde bir
    # istek; "uygula da sonra bak" demek yanlış olurdu.
    if '--yaz-gecici' in sys.argv:
        hedef = tempfile.mkdtemp(prefix='ip1-')
        print()
        for ad in TAM_YAZILAN:
            p = os.path.join(hedef, ad)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(_tam_dosya(ad))
            print(f'  {p}')
        print()
        print('  Projeye DOKUNULMADI. Okuduktan sonra:')
        print('    python3 yama_ip1.py            # rapor')
        print('    python3 yama_ip1.py --uygula')
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
        print('  ⊙ Yama IP1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_ip1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_ip1'
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
    print('    venv/bin/python -m pytest tests/test_kritik.py -q   # 314')
    print()
    print('  SUNUCUYU YENIDEN BASLAT')
    print('    sudo systemctl restart milestone-erp')
    print('    Sema degisikligi YOK, goc YOK.')
    print('    TARAYICIDA SERT YENILE (Ctrl+F5): siparis.html degisti.')
    print()
    print('  NE DEGISTI')
    print('    · Siparis iptali artik para kayitlarini SORUYOR:')
    print('      fatura iptal edilsin mi, cek iade mi edilsin yoksa')
    print('      cari ALACAK olarak mi kalsin, tahsilat geri alinsin mi.')
    print('      Onaylanmazsa hicbir seye dokunulmaz.')
    print('    · Cek silinince cari alacagi da gidiyor (eskiden')
    print('      "geri alindi" diyor ama birakiyordu).')
    print('    · Hizli satis stoklari Satildi birakiyor; iptalde')
    print('      serbest kalabiliyorlar (eskiden kalici kilitliydi).')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

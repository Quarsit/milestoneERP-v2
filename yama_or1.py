#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA OR1 — İŞ ORTAKLIKLARI (KÂR PAYLAŞIMI)
===========================================

ÖNKOŞUL: yama_b4.py uygulanmış olmalı.

Sorduğun şey: müşteriyi ve talebi biz buluyoruz, finansmanı ortak
sağlıyor, kâr paylaşılıyor, vergiler kârdan düşülüyor. Bunu
yönetecek sayfa geldi: Analiz → İş Ortaklıkları.

── TEMEL KARAR: KÂR YENİDEN HESAPLANMIYOR ──
  Gelir, maliyet ve kâr zaten `satis_kaydi`'nda satır satır duruyor
  ve maliyet zincirinden türüyor — /karlilik sayfası da onu
  gösteriyor. Ortaklık O RAKAMLARIN ÜZERİNE oturuyor.

  İkinci bir kâr hesabı yazmak, iki ekranın farklı rakam
  göstermesiyle biterdi; ortakla paylaşılan bir sayıda bu, en kötü
  hata biçimi olurdu.

── HESAP, BASAMAK BASAMAK ──
  Ekranda sonucu değil, ZİNCİRİ görüyorsun:

      Ciro            (bağlı işlerin satış kayıtları)
      − Maliyet
      = Brüt kâr
      − Vergi kalemleri   (her biri ayrı satır, matrahıyla birlikte)
      = Net kâr
      → Bizim pay / Ortak pay
      (+ anapara, yönteme göre)
      = Ortağa ödenecek  −  dağıtılan  =  bakiye

  Yalnız sonucu göstermek, "bu rakam nereden çıktı" sorusunu
  cevapsız bırakırdı — bu tür hesaplarda en çok sorulan soru o.

── VERGİ: DÖRT SEÇENEĞİN DE KARŞILIĞI VAR ──
  Kalem başına matrah seçiliyor:

      kâr × oran     kurumlar vergisi gibi
      ciro × oran    stopaj gibi
      sabit tutar    iade alınamayan KDV gibi (rakamı sen yazarsın)

  Yani sabit bir vergi listesi yok; istediğin kalemi istediğin
  matrahla tanımlıyorsun.

  BİR KABULÜ AÇIKÇA SÖYLÜYORUM: kurumlar vergisi YILLIK kâr
  üzerinden hesaplanır. Onu tek bir işe pay etmek bir kabuldür,
  kesin bir hesap değil. Bu yüzden her kalem 'tahmini' başlıyor ve
  tahmini kalem varsa ekran UYARI veriyor; vergi kesinleşince
  kalemi 'kesinleşti'ye çekiyorsun ve paylar güncelleniyor.

  ZARARDA kâr vergisi hesaplanmıyor: negatif kârı oranla çarpmak
  negatif vergi üretir ve zararı kâr gibi dağıtırdı.

── ANAPARA: HER ORTAKLIKTA AYRI SEÇİLİYOR ──
      'ayri'       sermaye ayrı takip edilir, dağıtım yalnız kâr payı
      'once_iade'  ortağa önce anaparası döner, sonra kâr payı

  İKİ YÖNTEMDE DE KÂR AYNIDIR; değişen yalnız ortağa ÖDENECEK
  tutar. Sermayeyi kârdan düşmek, ortağın kendi parasını gider gibi
  saymak olurdu — test bunu sabitliyor.

── DAĞITIM: CARİYE AKTARMAK İSTEĞE BAĞLI ──
  Hesap bu sayfada yapılıyor. Dağıtım satırındaki "cariye işle"
  düğmesi ortağın cari hesabına alacak kaydı yazıyor; basmazsan
  cari hareketi OLUŞMUYOR. "Geri al" o hareketi gerçekten siliyor —
  kalsaydı cari ekranında karşılığı olmayan bir borç dururdu.

  Cariye işlenmiş dağıtımı olan ortaklık silinemiyor; önce geri
  alman gerekiyor.

── KAPILAR ──
  · Bir iş yalnız BİR ortaklığa bağlanır — aynı kâr iki kez
    paylaşılamaz (409).
  · Bağlanan sipariş/sevkiyat/proforma GERÇEKTEN var mı diye
    bakılıyor; olmayan numara cirosu hep 0 çıkan bir ortaklık
    doğururdu (404).
  · Paylar toplamı %100'ü aşamaz. Aşmayan eksiklik ise sessizce
    100'e tamamlanmıyor, UYARI olarak duruyor: üçüncü bir tarafa
    ayrılmış pay olabilir, onu görünmez yapmak istemedim.
  · Yetki `karlilik` modülüne bağlı — kâr rakamını görmeye yetkisi
    olmayan biri buradan göremesin. Cariye işlemek ayrıca `cari`
    yazma yetkisi istiyor.

── ÖLÇÜLDÜ (tarayıcıda, gerçek veriyle) ──
  48.000 ciro · 30.300 maliyet · %60/%40 pay · anapara "önce iade"

      brüt kâr            17.700,00
      kurumlar v. %25     − 4.425,00  (tahmini)
      iade alınamayan KDV   − 850,00  (ödendi)
      net kâr             12.425,00
      bizim / ortak        7.455,00 / 4.970,00
      ortağa ödenecek     35.270,00  (30.300 anapara + 4.970 pay)
      dağıtılan           10.000,00
      ortak bakiye        25.270,00
      uyarı               tahmini vergi bildirildi
      JS hatası           yok

  139 test geçti (133 + 6 yeni kalıcı test);
  firma · js · form · zincir · akis · degismezlik temiz.

── ŞEMA ──
  Beş yeni tablo açılışta KENDİLİĞİNDEN kuruluyor (`db.create_all`),
  göç betiği gerekmiyor. Mevcut hiçbir tabloya dokunulmadı.

  `sifirla2.py` de güncellendi: yeni tablolar sınıflandırılmazsa
  sıfırlama çalışmayı REDDEDİYOR (firma denetimi bunu yakaladı).
  Beşi de İŞLEM verisi olarak silinecekler listesinde; ortağın
  kendisi cari kartında ve o korunuyor.

── NE YAPMADIM ──
  · Ortaklık İKİ TARAFLI: biz + bir ortak. Üç ortaklı bir iş için
    pay alanları yetmez, ayrı bir taraf tablosu gerekir. Böyle bir
    işin olacaksa söyle.
  · Kâr USD üzerinden hesaplanıyor (satış kaydı öyle tutuyor).
    Ortaklık dövizi TRY seçilse bile rakamlar USD.
  · Dağıtımın kasadan/bankadan fiilen ödenmesi buradan
    yapılmıyor — cariye işledikten sonra normal ödeme akışını
    kullanıyorsun.

DOSYALAR
--------
  models.py                 5 yeni tablo
  flask_app.py              hesap motoru + uçlar + sayfa rotası
  sifirla2.py               yeni tablolar sınıflandırıldı
  templates/base.html       menü ve komut paleti
  templates/ortaklik.html   YENİ — sayfa (tam dosya, base64)
  tests/test_kritik.py      6 yeni test

KULLANIM
--------
  python3 yama_or1.py            # RAPOR
  python3 yama_or1.py --uygula
  sudo systemctl restart milestone-erp     ← tabloları bu kurar
  (tarayıcıda Ctrl+F5)

  Sonra: Analiz → İş Ortaklıkları
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
    'models.py': 'class Ortaklik(FirmaKapsamli, db.Model):',
    'flask_app.py': 'def _ortaklik_hesap(ort):',
    'sifirla2.py': "'ortaklik_dagitim', 'ortaklik_sermaye'",
    'templates/base.html': "('/ortaklik','İş Ortaklıkları','karlilik')",
    'templates/ortaklik.html': 'İŞ ORTAKLIKLARI — OR1',
    'tests/test_kritik.py': 'def test_or1_hesap_zinciri_basamak_basamak',
}
ONKOSUL = {
    'models.py': 'class KdvIadeDosya(FirmaKapsamli, db.Model):',
    'flask_app.py': 'def _plaka_kodu(',
    'sifirla2.py': "'kdv_iade_dosya',",
    'templates/base.html': 'function slabVar(',
    'tests/test_kritik.py': 'def test_b4_sifir_slab_hicbir_yerde_yutulmuyor',
}
TAM_YAZILAN = ['templates/ortaklik.html']

DEGISIKLIKLER = [
    ('models.py', 'OR1 · models.py blok 1',
     r'''from sqlalchemy import event as _event, text as _text
''',
     r'''# ══════════════════════════════════════════════════════════════════
#  OR1 · İŞ ORTAKLIĞI — KÂR PAYLAŞIMI
#
#  Bazı işlerde müşteriyi ve talebi biz buluyoruz, finansmanı başka
#  bir kişi/şirket sağlıyor; kâr paylaşılıyor. Bu tablolar o hesabı
#  tutuyor.
#
#  KÂR YENİDEN HESAPLANMIYOR. Gelir, maliyet ve kâr zaten
#  `satis_kaydi` içinde satır satır duruyor (maliyet zincirinden
#  türüyor). Ortaklık o rakamların ÜZERİNE oturur; ikinci bir kâr
#  hesabı yazmak, iki ekranın farklı rakam göstermesiyle biterdi.
# ══════════════════════════════════════════════════════════════════
class Ortaklik(FirmaKapsamli, db.Model):
    """Bir iş ortaklığı: bir ortak, bir ya da birden çok iş.

    Tek işte de dönemsel çalışmada da aynı kayıt kullanılır — fark
    altına kaç iş bağladığında.
    """
    __tablename__ = 'ortaklik'
    id            = db.Column(db.String(20), primary_key=True)
    ad            = db.Column(db.String(150), nullable=False)
    ortak_cari_id = db.Column(db.String(20), db.ForeignKey('cariler.id'),
                              nullable=True, index=True)
    # Cari kartı olmayan ortak da olabiliyor; ad her zaman yazılır.
    ortak_ad      = db.Column(db.String(200))
    # Paylar yüzde. İkisinin toplamı 100 olmak zorunda değil:
    # üçüncü bir tarafa ayrılan pay varsa fark açıkta kalır ve
    # ekranda UYARI olarak görünür — sessizce 100'e tamamlamak,
    # eksik payı görünmez yapardı.
    bizim_pay     = db.Column(Olcu, default=50)
    ortak_pay     = db.Column(Olcu, default=50)
    doviz         = db.Column(db.String(5), default='USD')
    # ANAPARA YÖNTEMİ — her ortaklıkta ayrı seçilir:
    #   'once_iade' : tahsilattan önce ortağın koyduğu sermaye iade
    #                 edilir, ortağa ödenecek = anapara + kâr payı
    #   'ayri'      : sermaye ayrı takip edilir, dağıtım yalnız kâr payı
    # İKİ YÖNTEMDE DE KÂR AYNIDIR; değişen, ortağa ÖDENECEK tutar.
    anapara_yontemi = db.Column(db.String(12), default='ayri')
    durum         = db.Column(db.String(12), default='Acik')   # Acik|Kapandi
    baslangic     = db.Column(db.Date, default=date.today)
    bitis         = db.Column(db.Date, nullable=True)
    aciklama      = db.Column(db.Text)
    kullanici     = db.Column(db.String(50))
    olusturma     = db.Column(db.DateTime, default=datetime.now)
    guncelleme    = db.Column(db.DateTime, default=datetime.now,
                              onupdate=datetime.now)


class OrtaklikIs(FirmaKapsamli, db.Model):
    """Ortaklığa bağlanan iş: bir sipariş ya da bir sevkiyat.

    Bağ KAYNAK ÜZERİNDEN kurulur, satış kaydı kopyalanmaz: satış
    sonradan düzeltilirse (iade, fiyat farkı) ortaklık hesabı da
    kendiliğinden düzelir.
    """
    __tablename__ = 'ortaklik_is'
    id          = db.Column(db.Integer, primary_key=True)
    ortaklik_id = db.Column(db.String(20), db.ForeignKey('ortaklik.id'),
                            nullable=False, index=True)
    kaynak_tip  = db.Column(db.String(12))    # SIPARIS | SEVKIYAT | PROFORMA
    kaynak_id   = db.Column(db.String(30), index=True)
    aciklama    = db.Column(db.Text)
    olusturma   = db.Column(db.DateTime, default=datetime.now)


class OrtaklikVergi(FirmaKapsamli, db.Model):
    """Kârdan düşülecek vergi kalemi.

    `matrah_tipi` neyin üzerinden hesaplandığını söyler:
        'kar'   → brüt kâr × oran      (kurumlar vergisi gibi)
        'ciro'  → satış tutarı × oran  (stopaj gibi)
        'sabit' → doğrudan `tutar`     (iade alınamayan KDV gibi,
                                        rakamı kendin yazarsın)

    `durum` tahmini mi kesinleşmiş mi ayırır. Kurumlar vergisi YILLIK
    kâr üzerinden hesaplanır; onu tek bir işe pay etmek bir KABULdür.
    Bu yüzden kalem önce 'tahmini' durur, vergi kesinleşince
    'kesinlesti'ye çekilir ve fark dağıtımda görünür.
    """
    __tablename__ = 'ortaklik_vergi'
    id          = db.Column(db.Integer, primary_key=True)
    ortaklik_id = db.Column(db.String(20), db.ForeignKey('ortaklik.id'),
                            nullable=False, index=True)
    ad          = db.Column(db.String(100), nullable=False)
    matrah_tipi = db.Column(db.String(8), default='kar')   # kar|ciro|sabit
    oran        = db.Column(Olcu, default=0)               # yüzde
    tutar       = db.Column(Para, default=0)               # 'sabit' için
    doviz       = db.Column(db.String(5), default='USD')
    durum       = db.Column(db.String(12), default='tahmini')  # tahmini|kesinlesti|odendi
    odeme_tarihi = db.Column(db.Date, nullable=True)
    aciklama    = db.Column(db.Text)
    olusturma   = db.Column(db.DateTime, default=datetime.now)


class OrtaklikSermaye(FirmaKapsamli, db.Model):
    """Anapara hareketi: kim ne koydu, ne zaman geri aldı."""
    __tablename__ = 'ortaklik_sermaye'
    id          = db.Column(db.Integer, primary_key=True)
    ortaklik_id = db.Column(db.String(20), db.ForeignKey('ortaklik.id'),
                            nullable=False, index=True)
    taraf       = db.Column(db.String(8), default='ortak')  # ortak|biz
    yon         = db.Column(db.String(8), default='koydu')  # koydu|geri_aldi
    tutar       = db.Column(Para, default=0)
    doviz       = db.Column(db.String(5), default='USD')
    tarih       = db.Column(db.Date, default=date.today)
    aciklama    = db.Column(db.Text)
    olusturma   = db.Column(db.DateTime, default=datetime.now)


class OrtaklikDagitim(FirmaKapsamli, db.Model):
    """Ortağa yapılan/yapılacak ödeme.

    `cari_hareket_id` BOŞ OLABİLİR: hesap bu sayfada yapılır, cariye
    aktarmak isteğe bağlı. Dolu olması, bu dağıtımın cari borç olarak
    işlendiği anlamına gelir; geri alınınca hareket silinir ve alan
    yeniden boşalır.
    """
    __tablename__ = 'ortaklik_dagitim'
    id          = db.Column(db.Integer, primary_key=True)
    ortaklik_id = db.Column(db.String(20), db.ForeignKey('ortaklik.id'),
                            nullable=False, index=True)
    taraf       = db.Column(db.String(8), default='ortak')  # ortak|biz
    tutar       = db.Column(Para, default=0)
    doviz       = db.Column(db.String(5), default='USD')
    tarih       = db.Column(db.Date, default=date.today)
    aciklama    = db.Column(db.Text)
    cari_hareket_id = db.Column(db.String(20), nullable=True, index=True)
    kullanici   = db.Column(db.String(50))
    olusturma   = db.Column(db.DateTime, default=datetime.now)


from sqlalchemy import event as _event, text as _text
'''),
    ('flask_app.py', 'OR1 · flask_app.py blok 1',
     r'''import tcmb_kur   # TK1: ortak TCMB kur cekici
''',
     r'''from models import (Ortaklik, OrtaklikIs, OrtaklikVergi,   # OR1: is ortakligi
                    OrtaklikSermaye, OrtaklikDagitim)
import tcmb_kur   # TK1: ortak TCMB kur cekici
'''),
    ('flask_app.py', 'OR1 · flask_app.py blok 2',
     r'''    def _maliyet_dagitim_olcusu(hedefler):
''',
     r'''    #  OR1 · İŞ ORTAKLIĞI — UÇLAR
    #
    #  Yetki `karlilik` modülüne bağlı: ortaklık hesabı kâr
    #  rakamını gösteriyor, onu görmeye yetkisi olmayan birinin
    #  buradan görmesi kapıyı arkadan açmak olurdu.
    # ══════════════════════════════════════════════════════════
    ORTAKLIK_ANAPARA = ('ayri', 'once_iade')
    ORTAKLIK_MATRAH = ('kar', 'ciro', 'sabit')

    def _ortaklik_dict(o, hesap=False):
        d = {'id': o.id, 'ad': o.ad, 'ortak_ad': o.ortak_ad or '',
             'ortak_cari_id': o.ortak_cari_id,
             'bizim_pay': o.bizim_pay or 0, 'ortak_pay': o.ortak_pay or 0,
             'doviz': o.doviz or 'USD',
             'anapara_yontemi': o.anapara_yontemi or 'ayri',
             'durum': o.durum or 'Acik',
             'baslangic': _iso(o.baslangic), 'bitis': _iso(o.bitis),
             'aciklama': o.aciklama or ''}
        if hesap:
            d['hesap'] = _ortaklik_hesap(o)
            d['isler'] = [{'id': i.id, 'kaynak_tip': i.kaynak_tip,
                           'kaynak_id': i.kaynak_id,
                           'aciklama': i.aciklama or ''}
                          for i in OrtaklikIs.query.filter_by(
                              ortaklik_id=o.id).order_by(OrtaklikIs.id).all()]
            d['sermaye_hareketleri'] = [
                {'id': s.id, 'taraf': s.taraf, 'yon': s.yon,
                 'tutar': s.tutar or 0, 'doviz': s.doviz or 'USD',
                 'tarih': _iso(s.tarih), 'aciklama': s.aciklama or ''}
                for s in OrtaklikSermaye.query.filter_by(
                    ortaklik_id=o.id).order_by(OrtaklikSermaye.tarih,
                                               OrtaklikSermaye.id).all()]
        return d

    def _ortaklik_bul(oid):
        return Ortaklik.query.filter_by(id=oid).first()

    @app.route('/api/ortaklik', methods=['GET'])
    def api_ortaklik_liste():
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('karlilik', 'okuma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        q = Ortaklik.query
        if request.args.get('durum'):
            q = q.filter_by(durum=request.args.get('durum'))
        kayitlar = []
        for o in q.order_by(Ortaklik.baslangic.desc(), Ortaklik.id.desc()).all():
            d = _ortaklik_dict(o)
            h = _ortaklik_hesap(o)
            # Listede ÖZET yeter; tam döküm detayda.
            d['ozet'] = {'ciro': h['ciro'], 'brut_kar': h['brut_kar'],
                         'net_kar': h['net_kar'],
                         'ortak_bakiye': h['bakiye']['ortak'],
                         'is_adedi': h['is_adedi'],
                         'uyari_adedi': len(h['uyarilar'])}
            kayitlar.append(d)
        return jsonify({'ok': True, 'data': kayitlar})

    @app.route('/api/ortaklik/<oid>', methods=['GET'])
    def api_ortaklik_detay(oid):
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('karlilik', 'okuma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        o = _ortaklik_bul(oid)
        if not o:
            return jsonify({'ok': False, 'mesaj': 'Ortaklık bulunamadı'}), 404
        return jsonify({'ok': True, 'data': _ortaklik_dict(o, hesap=True)})

    def _ortaklik_govde_oku(d, zorunlu_ad=True):
        """Ortak alan doğrulaması. Döner: (govde, hata_mesaji)."""
        ad = (d.get('ad') or '').strip()
        if zorunlu_ad and not ad:
            return None, 'Ortaklık adı zorunlu'
        try:
            bizim = float(d.get('bizim_pay') if d.get('bizim_pay') is not None else 50)
            ortak = float(d.get('ortak_pay') if d.get('ortak_pay') is not None else 50)
        except (TypeError, ValueError):
            return None, 'Paylar sayısal olmalı'
        if bizim < 0 or ortak < 0:
            return None, 'Paylar negatif olamaz'
        if bizim + ortak > 100:
            return None, 'Payların toplamı %100\'ü aşamaz'
        yon = (d.get('anapara_yontemi') or 'ayri').strip()
        if yon not in ORTAKLIK_ANAPARA:
            return None, f'Anapara yöntemi: {", ".join(ORTAKLIK_ANAPARA)}'
        return {'ad': ad, 'bizim_pay': bizim, 'ortak_pay': ortak,
                'anapara_yontemi': yon,
                'ortak_ad': (d.get('ortak_ad') or '').strip(),
                'ortak_cari_id': (d.get('ortak_cari_id') or '').strip() or None,
                'doviz': (d.get('doviz') or 'USD').strip().upper()[:5],
                'aciklama': (d.get('aciklama') or '').strip()}, None

    @app.route('/api/ortaklik', methods=['POST'])
    def api_ortaklik_ekle():
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('karlilik', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        d = request.get_json(silent=True) or {}
        govde, hata = _ortaklik_govde_oku(d)
        if hata:
            return jsonify({'ok': False, 'mesaj': hata}), 400
        o = Ortaklik(id=_okunur_id('ORT', Ortaklik),
                     baslangic=_parse_date(d.get('baslangic')) or date.today(),
                     bitis=_parse_date(d.get('bitis')),
                     kullanici=session.get('kullanici'), **govde)
        db.session.add(o)
        _log_audit('EKLE', 'ortaklik', o.id, yeni={'ad': o.ad, 'ortak': o.ortak_ad})
        db.session.commit()
        return jsonify({'ok': True, 'id': o.id})

    @app.route('/api/ortaklik/<oid>', methods=['PUT'])
    def api_ortaklik_guncelle(oid):
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('karlilik', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        o = _ortaklik_bul(oid)
        if not o:
            return jsonify({'ok': False, 'mesaj': 'Ortaklık bulunamadı'}), 404
        d = request.get_json(silent=True) or {}
        govde, hata = _ortaklik_govde_oku(d)
        if hata:
            return jsonify({'ok': False, 'mesaj': hata}), 400
        for k, v in govde.items():
            setattr(o, k, v)
        if 'durum' in d and d['durum'] in ('Acik', 'Kapandi'):
            o.durum = d['durum']
        if 'baslangic' in d:
            o.baslangic = _parse_date(d.get('baslangic')) or o.baslangic
        if 'bitis' in d:
            o.bitis = _parse_date(d.get('bitis'))
        _log_audit('GUNCELLE', 'ortaklik', o.id, yeni={'ad': o.ad})
        db.session.commit()
        return jsonify({'ok': True})

    @app.route('/api/ortaklik/<oid>', methods=['DELETE'])
    def api_ortaklik_sil(oid):
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('karlilik', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        o = _ortaklik_bul(oid)
        if not o:
            return jsonify({'ok': False, 'mesaj': 'Ortaklık bulunamadı'}), 404
        # Cariye İŞLENMİŞ dağıtımı olan ortaklık silinemez: silmek,
        # cari ekranında karşılığı olmayan bir borç bırakırdı.
        islenmis = OrtaklikDagitim.query.filter(
            OrtaklikDagitim.ortaklik_id == oid,
            OrtaklikDagitim.cari_hareket_id.isnot(None)).count()
        if islenmis:
            return jsonify({'ok': False, 'mesaj':
                            f'{islenmis} dağıtım cariye işlenmiş. Önce onları '
                            f'geri alın.'}), 409
        for model in (OrtaklikDagitim, OrtaklikSermaye,
                      OrtaklikVergi, OrtaklikIs):
            model.query.filter_by(ortaklik_id=oid).delete()
        db.session.delete(o)
        _log_audit('SIL', 'ortaklik', oid, eski={'ad': o.ad})
        db.session.commit()
        return jsonify({'ok': True})

    # ── BAĞLI İŞLER ──
    @app.route('/api/ortaklik/<oid>/is', methods=['POST'])
    def api_ortaklik_is_ekle(oid):
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('karlilik', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        if not _ortaklik_bul(oid):
            return jsonify({'ok': False, 'mesaj': 'Ortaklık bulunamadı'}), 404
        d = request.get_json(silent=True) or {}
        tip = (d.get('kaynak_tip') or '').strip().upper()
        kid = (d.get('kaynak_id') or '').strip()
        if tip not in ('SIPARIS', 'SEVKIYAT', 'PROFORMA'):
            return jsonify({'ok': False, 'mesaj':
                            'Kaynak tipi: SIPARIS, SEVKIYAT veya PROFORMA'}), 400
        if not kid:
            return jsonify({'ok': False, 'mesaj': 'Kaynak no zorunlu'}), 400
        # Kaynak GERÇEKTEN var mı: olmayan bir numarayı bağlamak,
        # cirosu hep 0 çıkan bir ortaklıkla biterdi.
        _model = {'SIPARIS': Siparis, 'SEVKIYAT': Sevkiyat,
                  'PROFORMA': Proforma}[tip]
        if not _model.query.filter_by(id=kid).first():
            return jsonify({'ok': False, 'mesaj':
                            f'{tip} {kid} bulunamadı'}), 404
        # AYNI iş iki ortaklığa bağlanamaz: aynı kârı iki kez paylaşmak
        # olurdu.
        _var = OrtaklikIs.query.filter_by(kaynak_tip=tip, kaynak_id=kid).first()
        if _var:
            if _var.ortaklik_id == oid:
                return jsonify({'ok': False, 'mesaj': 'Bu iş zaten bağlı'}), 409
            return jsonify({'ok': False, 'mesaj':
                            f'Bu iş {_var.ortaklik_id} ortaklığına bağlı. '
                            f'Aynı kâr iki kez paylaşılamaz.'}), 409
        i = OrtaklikIs(ortaklik_id=oid, kaynak_tip=tip, kaynak_id=kid,
                       aciklama=(d.get('aciklama') or '').strip())
        db.session.add(i)
        db.session.commit()
        return jsonify({'ok': True, 'id': i.id})

    @app.route('/api/ortaklik/<oid>/is/<int:is_id>', methods=['DELETE'])
    def api_ortaklik_is_sil(oid, is_id):
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('karlilik', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        i = OrtaklikIs.query.filter_by(id=is_id, ortaklik_id=oid).first()
        if not i:
            return jsonify({'ok': False, 'mesaj': 'Kayıt bulunamadı'}), 404
        db.session.delete(i)
        db.session.commit()
        return jsonify({'ok': True})

    # ── VERGİ KALEMLERİ ──
    @app.route('/api/ortaklik/<oid>/vergi', methods=['POST'])
    def api_ortaklik_vergi_ekle(oid):
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('karlilik', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        if not _ortaklik_bul(oid):
            return jsonify({'ok': False, 'mesaj': 'Ortaklık bulunamadı'}), 404
        d = request.get_json(silent=True) or {}
        ad = (d.get('ad') or '').strip()
        if not ad:
            return jsonify({'ok': False, 'mesaj': 'Vergi adı zorunlu'}), 400
        mt = (d.get('matrah_tipi') or 'kar').strip()
        if mt not in ORTAKLIK_MATRAH:
            return jsonify({'ok': False, 'mesaj':
                            f'Matrah: {", ".join(ORTAKLIK_MATRAH)}'}), 400
        try:
            oran = float(d.get('oran') or 0)
            tutar = float(d.get('tutar') or 0)
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'mesaj': 'Oran/tutar sayısal olmalı'}), 400
        # 'sabit' tutar ister, ötekiler oran — yanlış alanı doldurup
        # sıfır vergi hesaplanmasın.
        if mt == 'sabit' and tutar <= 0:
            return jsonify({'ok': False, 'mesaj':
                            'Sabit kalemde tutar sıfırdan büyük olmalı'}), 400
        if mt != 'sabit' and oran <= 0:
            return jsonify({'ok': False, 'mesaj':
                            'Oran sıfırdan büyük olmalı'}), 400
        v = OrtaklikVergi(
            ortaklik_id=oid, ad=ad, matrah_tipi=mt, oran=oran, tutar=tutar,
            doviz=(d.get('doviz') or 'USD').strip().upper()[:5],
            durum=(d.get('durum') or 'tahmini').strip(),
            odeme_tarihi=_parse_date(d.get('odeme_tarihi')),
            aciklama=(d.get('aciklama') or '').strip())
        db.session.add(v)
        db.session.commit()
        return jsonify({'ok': True, 'id': v.id})

    @app.route('/api/ortaklik/<oid>/vergi/<int:vid>', methods=['PUT', 'DELETE'])
    def api_ortaklik_vergi_duzenle(oid, vid):
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('karlilik', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        v = OrtaklikVergi.query.filter_by(id=vid, ortaklik_id=oid).first()
        if not v:
            return jsonify({'ok': False, 'mesaj': 'Kalem bulunamadı'}), 404
        if request.method == 'DELETE':
            db.session.delete(v)
            db.session.commit()
            return jsonify({'ok': True})
        d = request.get_json(silent=True) or {}
        if 'ad' in d and (d.get('ad') or '').strip():
            v.ad = d['ad'].strip()
        if d.get('matrah_tipi') in ORTAKLIK_MATRAH:
            v.matrah_tipi = d['matrah_tipi']
        for alan in ('oran', 'tutar'):
            if alan in d:
                try:
                    setattr(v, alan, float(d.get(alan) or 0))
                except (TypeError, ValueError):
                    return jsonify({'ok': False, 'mesaj':
                                    f'{alan} sayısal olmalı'}), 400
        if d.get('durum') in ('tahmini', 'kesinlesti', 'odendi'):
            v.durum = d['durum']
        if 'odeme_tarihi' in d:
            v.odeme_tarihi = _parse_date(d.get('odeme_tarihi'))
        if 'aciklama' in d:
            v.aciklama = (d.get('aciklama') or '').strip()
        db.session.commit()
        return jsonify({'ok': True})

    # ── SERMAYE HAREKETLERİ ──
    @app.route('/api/ortaklik/<oid>/sermaye', methods=['POST'])
    def api_ortaklik_sermaye_ekle(oid):
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('karlilik', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        if not _ortaklik_bul(oid):
            return jsonify({'ok': False, 'mesaj': 'Ortaklık bulunamadı'}), 404
        d = request.get_json(silent=True) or {}
        try:
            tutar = float(d.get('tutar') or 0)
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'mesaj': 'Tutar sayısal olmalı'}), 400
        if tutar <= 0:
            return jsonify({'ok': False, 'mesaj': 'Tutar sıfırdan büyük olmalı'}), 400
        taraf = (d.get('taraf') or 'ortak').strip()
        yon = (d.get('yon') or 'koydu').strip()
        if taraf not in ('ortak', 'biz') or yon not in ('koydu', 'geri_aldi'):
            return jsonify({'ok': False, 'mesaj': 'Taraf/yön geçersiz'}), 400
        s = OrtaklikSermaye(
            ortaklik_id=oid, taraf=taraf, yon=yon, tutar=tutar,
            doviz=(d.get('doviz') or 'USD').strip().upper()[:5],
            tarih=_parse_date(d.get('tarih')) or date.today(),
            aciklama=(d.get('aciklama') or '').strip())
        db.session.add(s)
        db.session.commit()
        return jsonify({'ok': True, 'id': s.id})

    @app.route('/api/ortaklik/<oid>/sermaye/<int:sid>', methods=['DELETE'])
    def api_ortaklik_sermaye_sil(oid, sid):
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('karlilik', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        s = OrtaklikSermaye.query.filter_by(id=sid, ortaklik_id=oid).first()
        if not s:
            return jsonify({'ok': False, 'mesaj': 'Kayıt bulunamadı'}), 404
        db.session.delete(s)
        db.session.commit()
        return jsonify({'ok': True})

    # ── DAĞITIM ──
    @app.route('/api/ortaklik/<oid>/dagitim', methods=['POST'])
    def api_ortaklik_dagitim_ekle(oid):
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('karlilik', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        o = _ortaklik_bul(oid)
        if not o:
            return jsonify({'ok': False, 'mesaj': 'Ortaklık bulunamadı'}), 404
        d = request.get_json(silent=True) or {}
        try:
            tutar = float(d.get('tutar') or 0)
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'mesaj': 'Tutar sayısal olmalı'}), 400
        if tutar <= 0:
            return jsonify({'ok': False, 'mesaj': 'Tutar sıfırdan büyük olmalı'}), 400
        taraf = (d.get('taraf') or 'ortak').strip()
        if taraf not in ('ortak', 'biz'):
            return jsonify({'ok': False, 'mesaj': 'Taraf geçersiz'}), 400
        dg = OrtaklikDagitim(
            ortaklik_id=oid, taraf=taraf, tutar=tutar,
            doviz=(d.get('doviz') or o.doviz or 'USD').strip().upper()[:5],
            tarih=_parse_date(d.get('tarih')) or date.today(),
            aciklama=(d.get('aciklama') or '').strip(),
            kullanici=session.get('kullanici'))
        db.session.add(dg)
        db.session.flush()
        _log_audit('EKLE', 'ortaklik_dagitim', str(dg.id),
                   yeni={'ortaklik': oid, 'taraf': taraf, 'tutar': tutar})
        db.session.commit()
        return jsonify({'ok': True, 'id': dg.id})

    @app.route('/api/ortaklik/<oid>/dagitim/<int:did>', methods=['DELETE'])
    def api_ortaklik_dagitim_sil(oid, did):
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('karlilik', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        dg = OrtaklikDagitim.query.filter_by(id=did, ortaklik_id=oid).first()
        if not dg:
            return jsonify({'ok': False, 'mesaj': 'Kayıt bulunamadı'}), 404
        if dg.cari_hareket_id:
            return jsonify({'ok': False, 'mesaj':
                            'Bu dağıtım cariye işlenmiş. Önce geri alın.'}), 409
        db.session.delete(dg)
        db.session.commit()
        return jsonify({'ok': True})

    @app.route('/api/ortaklik/<oid>/dagitim/<int:did>/cariye', methods=['POST', 'DELETE'])
    def api_ortaklik_dagitim_cariye(oid, did):
        """Dağıtımı cari borç olarak işler — ya da geri alır.

        İSTEĞE BAĞLI: hesap bu sayfada yapılıyor, cariye aktarmak
        ayrı bir karar. Geri alma, oluşturulan hareketi siler ve
        bağı boşaltır; iki kayıt arasında sessiz bir fark kalmaz.
        """
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('karlilik', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        if not _yetki_var_mi('cari', 'yazma'):
            return jsonify({'ok': False, 'mesaj':
                            'Cariye işlemek için cari yazma yetkisi gerekir'}), 403
        o = _ortaklik_bul(oid)
        dg = OrtaklikDagitim.query.filter_by(id=did, ortaklik_id=oid).first()
        if not o or not dg:
            return jsonify({'ok': False, 'mesaj': 'Kayıt bulunamadı'}), 404

        if request.method == 'DELETE':
            if not dg.cari_hareket_id:
                return jsonify({'ok': False, 'mesaj':
                                'Bu dağıtım cariye işlenmemiş'}), 400
            ch = CariHareket.query.filter_by(id=dg.cari_hareket_id).first()
            if ch:
                db.session.delete(ch)
            _log_audit('SIL', 'cari_hareket', dg.cari_hareket_id,
                       eski={'kaynak': 'ortaklik_dagitim', 'dagitim': did})
            dg.cari_hareket_id = None
            db.session.commit()
            return jsonify({'ok': True})

        if dg.cari_hareket_id:
            return jsonify({'ok': False, 'mesaj': 'Zaten işlenmiş'}), 409
        if dg.taraf != 'ortak':
            return jsonify({'ok': False, 'mesaj':
                            'Yalnızca ORTAĞA yapılan dağıtım cariye işlenir'}), 400
        if not o.ortak_cari_id:
            return jsonify({'ok': False, 'mesaj':
                            'Ortaklıkta cari kartı seçili değil'}), 400
        cari = Cari.query.filter_by(id=o.ortak_cari_id).first()
        if not cari:
            return jsonify({'ok': False, 'mesaj': 'Cari bulunamadı'}), 404

        # ALACAK: ortağa ödenecek tutar bizim için borçtur.
        ch = CariHareket(
            id=_yeni_id('CH'), hareket_tarihi=dg.tarih or date.today(),
            cari_unvan=cari.unvan, cari_id=cari.id,
            islem_tip='Ortaklık kâr payı', evrak_no=o.id,
            aciklama=(dg.aciklama or '') or f'{o.ad} — kâr payı dağıtımı',
            borc=0, alacak=dg.tutar or 0, doviz=dg.doviz or 'USD')
        db.session.add(ch)
        db.session.flush()
        dg.cari_hareket_id = ch.id
        _log_audit('EKLE', 'cari_hareket', ch.id,
                   yeni={'kaynak': 'ortaklik_dagitim', 'ortaklik': oid,
                         'tutar': dg.tutar})
        db.session.commit()
        return jsonify({'ok': True, 'cari_hareket_id': ch.id})

    @app.route('/ortaklik')
    def ortaklik_sayfa():
        """İş ortaklıkları — kâr paylaşım hesabı."""
        if _auth_required(): return _auth_required()
        if not _yetki_var_mi('karlilik', 'okuma'):
            return redirect(url_for('dashboard'))
        return render_template('ortaklik.html')

    # ══════════════════════════════════════════════════════════
    # ══════════════════════════════════════════════════════════
    #  OR1 · İŞ ORTAKLIĞI — KÂR PAYLAŞIM HESABI
    #
    #  Zincir, her basamağı ayrı ayrı görünecek şekilde döner:
    #
    #      ciro − maliyet = BRÜT KÂR
    #      brüt kâr − vergiler = NET KÂR
    #      net kâr × pay% = tarafların payı
    #      (+ anapara, yönteme göre) = ÖDENECEK
    #
    #  Ara basamakları saklamak, "bu rakam nereden çıktı" sorusunu
    #  cevapsız bırakırdı — ortakla paylaşılan bir hesapta en çok
    #  sorulan soru o.
    #
    #  KÂR BURADA YENİDEN HESAPLANMIYOR: `satis_kaydi` zaten satır
    #  satır tutuyor ve maliyet zincirinden türüyor. İkinci bir
    #  hesap, /karlilik ile bu sayfanın farklı rakam göstermesiyle
    #  biterdi.
    # ══════════════════════════════════════════════════════════
    def _iso(d):
        return d.isoformat() if d else None

    def _ortaklik_satislari(ort):
        """Ortaklığa bağlı işlerin SatisKaydi satırları."""
        isler = OrtaklikIs.query.filter_by(ortaklik_id=ort.id).all()
        if not isler:
            return [], []
        sip = [i.kaynak_id for i in isler if i.kaynak_tip == 'SIPARIS']
        sev = [i.kaynak_id for i in isler if i.kaynak_tip == 'SEVKIYAT']
        prf = [i.kaynak_id for i in isler if i.kaynak_tip == 'PROFORMA']
        kosul = []
        if sip: kosul.append(SatisKaydi.siparis_id.in_(sip))
        if sev: kosul.append(SatisKaydi.sevkiyat_id.in_(sev))
        if prf: kosul.append(SatisKaydi.proforma_id.in_(prf))
        if not kosul:
            return [], isler
        return SatisKaydi.query.filter(db.or_(*kosul)).all(), isler

    def _ortaklik_hesap(ort):
        """Ortaklığın tam hesabı. Para birimi USD (satış kaydı öyle tutuyor)."""
        satislar, isler = _ortaklik_satislari(ort)

        ciro = q2(sum((s.tutar_usd or 0) for s in satislar))
        maliyet = q2(sum((s.maliyet_usd or 0) for s in satislar))
        brut_kar = q2(sum((s.kar_usd or 0) for s in satislar))

        # ── VERGİLER ──
        # Her kalem kendi matrahından hesaplanır. Hesaplanan tutar
        # kalemin üstünde DURMAZ, burada üretilir: oran değişince
        # eski tutar geride kalmasın.
        vergiler, vergi_top, vergi_kesin = [], 0, 0
        for v in OrtaklikVergi.query.filter_by(ortaklik_id=ort.id).order_by(
                OrtaklikVergi.id).all():
            if v.matrah_tipi == 'ciro':
                matrah, tut = ciro, q2(ciro * (v.oran or 0) / 100)
            elif v.matrah_tipi == 'sabit':
                matrah, tut = None, q2(v.tutar or 0)
            else:   # 'kar'
                # Zararda kâr vergisi doğmaz; negatif oranı negatif
                # vergiye çevirmek, zararı kâr gibi dağıtırdı.
                matrah = brut_kar
                tut = q2(brut_kar * (v.oran or 0) / 100) if brut_kar > 0 else 0
            vergi_top += tut
            if v.durum in ('kesinlesti', 'odendi'):
                vergi_kesin += tut
            vergiler.append({
                'id': v.id, 'ad': v.ad, 'matrah_tipi': v.matrah_tipi,
                'oran': v.oran or 0, 'matrah': matrah, 'tutar': tut,
                'durum': v.durum, 'odeme_tarihi': _iso(v.odeme_tarihi),
                'aciklama': v.aciklama or ''})
        vergi_top = q2(vergi_top)
        net_kar = q2(brut_kar - vergi_top)

        # ── SERMAYE ──
        sermaye = {'ortak': 0, 'biz': 0}
        sermaye_iade = {'ortak': 0, 'biz': 0}
        for sm in OrtaklikSermaye.query.filter_by(ortaklik_id=ort.id).all():
            hedef = sermaye if sm.yon == 'koydu' else sermaye_iade
            hedef[sm.taraf if sm.taraf in hedef else 'ortak'] += (sm.tutar or 0)
        kalan_anapara = {t: q2(sermaye[t] - sermaye_iade[t]) for t in sermaye}

        # ── PAYLAR ──
        bizim_pay = ort.bizim_pay or 0
        ortak_pay = ort.ortak_pay or 0
        paylar = {
            'biz': q2(net_kar * bizim_pay / 100),
            'ortak': q2(net_kar * ortak_pay / 100)}

        # ── ÖDENECEK ──
        # 'once_iade': ortağa önce anaparası döner, sonra kâr payı.
        # 'ayri'     : anapara ayrı takip edilir, dağıtım yalnız kâr payı.
        # KÂR İKİ YÖNTEMDE DE AYNI; değişen yalnız ödenecek tutar.
        if ort.anapara_yontemi == 'once_iade':
            odenecek = {t: q2(paylar[t] + kalan_anapara.get(t, 0))
                        for t in paylar}
        else:
            odenecek = dict(paylar)

        # ── YAPILAN DAĞITIMLAR ──
        dagitilan = {'ortak': 0, 'biz': 0}
        dagitimlar = []
        for d in OrtaklikDagitim.query.filter_by(ortaklik_id=ort.id).order_by(
                OrtaklikDagitim.tarih, OrtaklikDagitim.id).all():
            dagitilan[d.taraf if d.taraf in dagitilan else 'ortak'] += (d.tutar or 0)
            dagitimlar.append({
                'id': d.id, 'taraf': d.taraf, 'tutar': d.tutar or 0,
                'doviz': d.doviz or 'USD', 'tarih': _iso(d.tarih),
                'aciklama': d.aciklama or '',
                'cari_hareket_id': d.cari_hareket_id,
                'cariye_islendi': bool(d.cari_hareket_id)})

        # ── UYARILAR ──
        # Sessiz kalınacak şeyler değil: ortakla paylaşılan bir hesapta
        # eksik pay ya da tahmini vergi, sonradan anlaşmazlık doğurur.
        uyarilar = []
        _pay_top = q2(bizim_pay + ortak_pay)
        if _pay_top != 100:
            uyarilar.append(
                f'Paylar toplamı %{_pay_top} — %100 değil. '
                f'Üçüncü bir tarafa ayrılan pay yoksa bu bir eksiklik.')
        _tahmini = q2(vergi_top - vergi_kesin)
        if _tahmini > 0:
            uyarilar.append(
                f'Vergilerin {_tahmini:,.2f} USD\'lik kısmı TAHMİNİ. '
                f'Kesinleşince paylar değişir.')
        if not satislar and isler:
            uyarilar.append(
                'Bağlı işlerin henüz satış kaydı yok — teslim edilmemiş '
                'olabilir. Ciro ve kâr 0 görünüyor.')
        if not isler:
            uyarilar.append('Bu ortaklığa henüz iş bağlanmadı.')

        return {
            'ciro': ciro, 'maliyet': maliyet, 'brut_kar': brut_kar,
            'vergiler': vergiler, 'vergi_toplam': vergi_top,
            'vergi_kesinlesen': q2(vergi_kesin),
            'vergi_tahmini': q2(vergi_top - vergi_kesin),
            'net_kar': net_kar,
            'bizim_pay': bizim_pay, 'ortak_pay': ortak_pay,
            'paylar': paylar,
            'sermaye': {t: q2(sermaye[t]) for t in sermaye},
            'sermaye_iade': {t: q2(sermaye_iade[t]) for t in sermaye_iade},
            'kalan_anapara': kalan_anapara,
            'anapara_yontemi': ort.anapara_yontemi,
            'odenecek': odenecek,
            'dagitilan': {t: q2(dagitilan[t]) for t in dagitilan},
            'bakiye': {t: q2(odenecek[t] - dagitilan[t]) for t in odenecek},
            'dagitimlar': dagitimlar,
            'satis_adedi': len(satislar), 'is_adedi': len(isler),
            'uyarilar': uyarilar}

    # ══════════════════════════════════════════════════════════
    def _maliyet_dagitim_olcusu(hedefler):
'''),
    ('sifirla2.py', 'OR1 · sifirla2.py blok 1',
     r'''    # Maliyet
''',
     r'''    # OR1 · İş ortaklığı — hepsi İŞLEM verisi, tanım değil. Ortağın
    # KENDİSİ cari kartında duruyor ve o korunuyor; burada silinen,
    # o ortakla yapılan işlerin hesabı. Sıra önemli: alt tablolar
    # önce, ortaklık en son.
    'ortaklik_dagitim', 'ortaklik_sermaye', 'ortaklik_vergi',
    'ortaklik_is', 'ortaklik',
    # Maliyet
'''),
    ('templates/base.html', 'OR1 · templates/base.html blok 1',
     r'''      <a href="/raporlar" class="ray-btn {% if yol.startswith('/raporlar') or yol.startswith('/karlilik') %}aktif{% endif %}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 20V10M12 20V4M19 20v-7"/></svg>
        <span>Analiz</span>
      </a>
      <div class="ray-ucan"><div class="ray-ucan-ic">
        <div class="ray-ucan-bas">Analiz</div>
        {% for hedef, ad, modul in [('/raporlar','Raporlar','raporlar'), ('/karlilik','Karlılık','karlilik')] %}
''',
     r'''      <a href="/raporlar" class="ray-btn {% if yol.startswith('/raporlar') or yol.startswith('/karlilik') or yol.startswith('/ortaklik') %}aktif{% endif %}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 20V10M12 20V4M19 20v-7"/></svg>
        <span>Analiz</span>
      </a>
      <div class="ray-ucan"><div class="ray-ucan-ic">
        <div class="ray-ucan-bas">Analiz</div>
        {% for hedef, ad, modul in [('/raporlar','Raporlar','raporlar'), ('/karlilik','Karlılık','karlilik'), ('/ortaklik','İş Ortaklıkları','karlilik')] %}
'''),
    ('templates/base.html', 'OR1 · templates/base.html blok 2',
     r'''    {% elif yol.startswith('/raporlar') or yol.startswith('/karlilik') %}
      {% set alan_sekmeleri = [('/raporlar','Raporlar','raporlar'), ('/karlilik','Karlılık','karlilik')] %}
''',
     r'''    {% elif yol.startswith('/raporlar') or yol.startswith('/karlilik')
            or yol.startswith('/ortaklik') %}
      {% set alan_sekmeleri = [('/raporlar','Raporlar','raporlar'), ('/karlilik','Karlılık','karlilik'), ('/ortaklik','İş Ortaklıkları','karlilik')] %}
'''),
    ('templates/base.html', 'OR1 · templates/base.html blok 3',
     r'''  { g:'Sayfalar', ad:'Ayarlar',      ek:'kullanıcı · firma', ik:'⚙', yol:'/ayarlar',   m:'ayarlar' },
''',
     r'''  { g:'Sayfalar', ad:'İş Ortaklıkları', ek:'kâr paylaşımı',   ik:'▥', yol:'/ortaklik',  m:'karlilik' },
  { g:'Sayfalar', ad:'Ayarlar',      ek:'kullanıcı · firma', ik:'⚙', yol:'/ayarlar',   m:'ayarlar' },
'''),
    ('tests/test_kritik.py', 'OR1 · tests/test_kritik.py blok 1',
     r'''    assert d['varBos'] is False and d['varNull'] is False
''',
     r'''    assert d['varBos'] is False and d['varNull'] is False


# ══════════════════════════════════════════════════════════════════════
#  OR1 · İŞ ORTAKLIĞI — KÂR PAYLAŞIMI
# ══════════════════════════════════════════════════════════════════════

def _or1_kur(sip_id, satislar, firma_id=1):
    """Bir sipariş + ona bağlı satış kayıtları kurar.

    satislar: [(tutar_usd, maliyet_usd)] — kâr farktan türetilir,
    tıpkı gerçek akışta olduğu gibi.
    """
    from models import Siparis, SatisKaydi
    with fa.app.app_context():
        db.session.add(Siparis(id=sip_id, musteri='ACIK CARI', doviz='USD',
                               toplam_tutar=sum(t for t, _ in satislar),
                               durum='Onaylandi',
                               siparis_tarihi=date(2026, 4, 1)))
        db.session.flush()
        for n, (tutar, maliyet) in enumerate(satislar, 1):
            db.session.add(SatisKaydi(
                id=f'{sip_id}-S{n}', siparis_id=sip_id, stok_tip='PLAKA',
                cins='TEST', musteri='ACIK CARI', satis_tarihi=date(2026, 4, 5),
                tutar=tutar, tutar_usd=tutar, doviz='USD',
                maliyet_usd=maliyet, kar_usd=tutar - maliyet,
                marj_yuzde=((tutar - maliyet) / tutar * 100) if tutar else 0))
        db.session.commit()


def test_or1_hesap_zinciri_basamak_basamak():
    """OR1: ciro → maliyet → brüt kâr → vergiler → net kâr → paylar.

    Her basamak ayrı ayrı doğrulanıyor: ortakla paylaşılan bir
    hesapta yalnız sonucu ölçmek, hatanın hangi basamakta olduğunu
    gizlerdi."""
    _or1_kur('SIPOR1', [(10000, 6000), (5000, 3000)])
    c = istemci('admin', 'ADMIN')

    r = c.post('/api/ortaklik', headers=H, json={
        'ad': 'OR1 testi', 'ortak_ad': 'FINANSOR', 'bizim_pay': 60,
        'ortak_pay': 40, 'anapara_yontemi': 'ayri'})
    assert r.status_code == 200, r.get_data(as_text=True)
    oid = r.get_json()['id']

    assert c.post(f'/api/ortaklik/{oid}/is', headers=H, json={
        'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR1'}).status_code == 200

    # Üç matrah tipi birden
    assert c.post(f'/api/ortaklik/{oid}/vergi', headers=H, json={
        'ad': 'Kurumlar', 'matrah_tipi': 'kar', 'oran': 25}).status_code == 200
    assert c.post(f'/api/ortaklik/{oid}/vergi', headers=H, json={
        'ad': 'Stopaj', 'matrah_tipi': 'ciro', 'oran': 1}).status_code == 200
    assert c.post(f'/api/ortaklik/{oid}/vergi', headers=H, json={
        'ad': 'İade alınamayan KDV', 'matrah_tipi': 'sabit',
        'tutar': 200, 'durum': 'odendi'}).status_code == 200

    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h['ciro'] == 15000, h['ciro']
    assert h['maliyet'] == 9000, h['maliyet']
    assert h['brut_kar'] == 6000, h['brut_kar']
    # 6000×25% = 1500 · 15000×1% = 150 · sabit 200 → 1850
    assert h['vergi_toplam'] == 1850, h['vergi_toplam']
    assert h['net_kar'] == 4150, h['net_kar']
    assert h['paylar']['biz'] == 2490 and h['paylar']['ortak'] == 1660, h['paylar']
    # Sabit kalem 'odendi', ötekiler 'tahmini'
    assert h['vergi_kesinlesen'] == 200 and h['vergi_tahmini'] == 1650
    assert any('TAHMİNİ' in u for u in h['uyarilar']), h['uyarilar']


def test_or1_anapara_iki_yontem_kari_degistirmez():
    """OR1: anapara yöntemi KÂRI değil, ÖDENECEĞİ değiştirir.

    Kolayca ters gidebilecek yer burası: sermayeyi kârdan düşmek,
    ortağın parasını gider gibi saymak olurdu."""
    _or1_kur('SIPOR2', [(10000, 6000)])
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Anapara testi', 'bizim_pay': 50, 'ortak_pay': 50,
        'anapara_yontemi': 'ayri'})
    oid = r.get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR2'})
    c.post(f'/api/ortaklik/{oid}/sermaye', headers=H, json={
        'taraf': 'ortak', 'yon': 'koydu', 'tutar': 6000})

    h1 = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h1['net_kar'] == 4000 and h1['paylar']['ortak'] == 2000
    assert h1['odenecek']['ortak'] == 2000, h1['odenecek']

    # Yöntemi değiştir — kâr AYNI kalmalı, ödenecek anaparayı da içermeli
    assert c.put(f'/api/ortaklik/{oid}', headers=H, json={
        'ad': 'Anapara testi', 'bizim_pay': 50, 'ortak_pay': 50,
        'anapara_yontemi': 'once_iade'}).status_code == 200
    h2 = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h2['net_kar'] == h1['net_kar'], (h1['net_kar'], h2['net_kar'])
    assert h2['paylar']['ortak'] == 2000
    assert h2['odenecek']['ortak'] == 8000, h2['odenecek']   # 6000 + 2000
    assert h2['kalan_anapara']['ortak'] == 6000


def test_or1_zararda_kar_vergisi_dogmaz():
    """OR1: zararda kâr üzerinden vergi hesaplanmaz.

    Negatif kârı orana çarpmak NEGATİF vergi üretir ve zararı kâr
    gibi dağıtırdı."""
    _or1_kur('SIPOR3', [(4000, 7000)])    # 3000 zarar
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Zarar testi', 'bizim_pay': 50, 'ortak_pay': 50}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR3'})
    c.post(f'/api/ortaklik/{oid}/vergi', headers=H, json={
        'ad': 'Kurumlar', 'matrah_tipi': 'kar', 'oran': 25})

    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h['brut_kar'] == -3000, h['brut_kar']
    assert h['vergi_toplam'] == 0, h['vergi_toplam']
    assert h['net_kar'] == -3000
    # Zarar da paylaşılır — payı sıfırlamak zararı bize yıkardı
    assert h['paylar']['ortak'] == -1500, h['paylar']


def test_or1_ayni_is_iki_ortakliga_baglanamaz():
    """OR1: bir iş tek ortaklığa bağlanır — aynı kâr iki kez
    paylaşılamaz."""
    _or1_kur('SIPOR4', [(1000, 500)])
    c = istemci('admin', 'ADMIN')
    a = c.post('/api/ortaklik', headers=H, json={'ad': 'A'}).get_json()['id']
    b = c.post('/api/ortaklik', headers=H, json={'ad': 'B'}).get_json()['id']
    assert c.post(f'/api/ortaklik/{a}/is', headers=H, json={
        'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR4'}).status_code == 200
    r = c.post(f'/api/ortaklik/{b}/is', headers=H, json={
        'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR4'})
    assert r.status_code == 409, r.get_data(as_text=True)
    # Var olmayan kaynak da bağlanamaz
    assert c.post(f'/api/ortaklik/{b}/is', headers=H, json={
        'kaynak_tip': 'SIPARIS', 'kaynak_id': 'YOK-123'}).status_code == 404


def test_or1_cariye_isleme_istege_bagli_ve_geri_alinabilir():
    """OR1: dağıtım cariye İSTEĞE BAĞLI işlenir, geri alınabilir.

    Geri alma hareketi gerçekten silmeli: kalırsa cari ekranında
    karşılığı olmayan bir borç durur."""
    from models import CariHareket, OrtaklikDagitim
    _or1_kur('SIPOR5', [(10000, 6000)])
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Cari testi', 'ortak_cari_id': 'C1', 'ortak_ad': 'ACIK CARI',
        'bizim_pay': 50, 'ortak_pay': 50}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR5'})
    did = c.post(f'/api/ortaklik/{oid}/dagitim', headers=H, json={
        'taraf': 'ortak', 'tutar': 2000}).get_json()['id']

    # Henüz cariye işlenmedi
    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h['dagitimlar'][0]['cariye_islendi'] is False
    assert h['bakiye']['ortak'] == 0, h['bakiye']   # 2000 pay − 2000 dağıtım

    r = c.post(f'/api/ortaklik/{oid}/dagitim/{did}/cariye', headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)
    chid = r.get_json()['cari_hareket_id']
    with fa.app.app_context():
        ch = CariHareket.query.filter_by(id=chid).first()
        assert ch is not None and ch.alacak == 2000, ch
        assert ch.cari_id == 'C1'

    # İkinci kez işlenemez
    assert c.post(f'/api/ortaklik/{oid}/dagitim/{did}/cariye',
                  headers=H).status_code == 409
    # İşlenmişken silinemez
    assert c.delete(f'/api/ortaklik/{oid}/dagitim/{did}',
                    headers=H).status_code == 409

    # Geri al → hareket GERÇEKTEN silinir
    assert c.delete(f'/api/ortaklik/{oid}/dagitim/{did}/cariye',
                    headers=H).status_code == 200
    with fa.app.app_context():
        assert CariHareket.query.filter_by(id=chid).first() is None
        assert OrtaklikDagitim.query.get(did).cari_hareket_id is None


def test_or1_paylar_yuzde_yuzu_asamaz_ve_eksik_pay_uyarir():
    """OR1: toplam %100'ü aşamaz; aşmayan eksiklik SESSİZ kalmaz.

    Eksik payı kendiliğinden 100'e tamamlamak, üçüncü bir tarafa
    ayrılmış payı görünmez yapardı — bu yüzden uyarı veriliyor,
    düzeltme yapılmıyor."""
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Asan', 'bizim_pay': 70, 'ortak_pay': 40})
    assert r.status_code == 400, r.get_data(as_text=True)

    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Eksik', 'bizim_pay': 50, 'ortak_pay': 30}).get_json()['id']
    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert any('%80' in u for u in h['uyarilar']), h['uyarilar']
'''),
]

# ══════════════════════════════════════════════════════════════════════
#  TAM DOSYA · templates/ortaklik.html
#
#  Parça değil tam dosya; iç içe tırnak yığını üretmesin diye
#  base64. Uygulandıktan sonra diskteki dosya baştan sona
#  yorumlu, okunur Python — yamayı uygulamadan okumak istersen:
#      python3 yama_or1.py --yaz-gecici
# ══════════════════════════════════════════════════════════════════════
TAM_ICERIK = {
    'templates/ortaklik.html': (
        'eyUgZXh0ZW5kcyAiYmFzZS5odG1sIiAlfQp7JSBibG9jayB0aXRsZSAlfcSwxZ8gT3J0'
        'YWtsxLFrbGFyxLF7JSBlbmRibG9jayAlfQoKeyUgYmxvY2sgaGVhZCAlfQo8c3R5bGU+'
        'Ci8qIOKUgOKUgCDEsMWeIE9SVEFLTElLTEFSSSAoT1IxKSDilIDilIDilIDilIDilIDi'
        'lIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDi'
        'lIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDi'
        'lIDilIAKICAgTcO8xZ90ZXJpeWkgdmUgdGFsZWJpIGJpeiBidWx1eW9ydXosIGZpbmFu'
        'c21hbsSxIG9ydGFrIHNhxJ9sxLF5b3IsIGvDonIKICAgcGF5bGHFn8SxbMSxeW9yLiBC'
        'dSBzYXlmYSBvIGhlc2FixLEgdHV0dXlvci4KCiAgIFRBU0FSSU0gS0FSQVJJOiBoZXNh'
        'YsSxbiBIRVIgQkFTQU1BxJ5JIGVrcmFuZGEgZHVydXlvcgogICAoY2lybyDihpIgbWFs'
        'aXlldCDihpIgYnLDvHQga8OiciDihpIgdmVyZ2lsZXIg4oaSIG5ldCBrw6JyIOKGkiBw'
        'YXlsYXIpLgogICBZYWxuxLF6IHNvbnVjdSBnw7ZzdGVybWVrLCBvcnRha2xhIHBheWxh'
        'xZ/EsWxhbiBiaXIgcmFrYW1kYSAiYnUKICAgbmVyZWRlbiDDp8Sxa3TEsSIgc29ydXN1'
        'bnUgY2V2YXBzxLF6IGLEsXJha8SxcmTEsSDigJQgdmUgbyBzb3J1IGJ1IHTDvHIKICAg'
        'aGVzYXBsYXJkYSBlbiDDp29rIHNvcnVsYW4gc29ydWR1ci4gKi8KICAub3ItdXN0e2Rp'
        'c3BsYXk6ZmxleDthbGlnbi1pdGVtczpjZW50ZXI7Z2FwOjEwcHg7ZmxleC13cmFwOndy'
        'YXA7bWFyZ2luOjE2cHggMCAxNHB4fQogIC5vci1zZWN7Ym9yZGVyOjFweCBzb2xpZCB2'
        'YXIoLS1jaXpnaS1rb3l1KTtib3JkZXItcmFkaXVzOnZhcigtLXIta3VjdWspOwogICAg'
        'cGFkZGluZzo4cHggMTFweDtmb250LWZhbWlseTp2YXIoLS1nb3ZkZSk7Zm9udC1zaXpl'
        'Oi44NnJlbTsKICAgIGJhY2tncm91bmQ6dmFyKC0teXV6ZXkpO2NvbG9yOnZhcigtLW11'
        'cmVra2VwKTtjdXJzb3I6cG9pbnRlcn0KICAub3Itc2VjOmZvY3Vze291dGxpbmU6bm9u'
        'ZTtib3JkZXItY29sb3I6dmFyKC0tdmVyZGUpO2JveC1zaGFkb3c6MCAwIDAgM3B4IHZh'
        'cigtLXZlcmRlLWFjaWspfQoKICAub3ItdGFibG97d2lkdGg6MTAwJTtib3JkZXItY29s'
        'bGFwc2U6Y29sbGFwc2U7Zm9udC1zaXplOi44OHJlbX0KICAub3ItdGFibG8gdGh7dGV4'
        'dC1hbGlnbjpsZWZ0O3BhZGRpbmc6OXB4IDEycHg7Zm9udC1zaXplOi43cmVtO2ZvbnQt'
        'd2VpZ2h0OjcwMDsKICAgIGxldHRlci1zcGFjaW5nOi4wNWVtO3RleHQtdHJhbnNmb3Jt'
        'OnVwcGVyY2FzZTtjb2xvcjp2YXIoLS1zb2x1ayk7CiAgICBib3JkZXItYm90dG9tOjFw'
        'eCBzb2xpZCB2YXIoLS1jaXpnaSk7d2hpdGUtc3BhY2U6bm93cmFwfQogIC5vci10YWJs'
        'byB0aC5zYWcsLm9yLXRhYmxvIHRkLnNhZ3t0ZXh0LWFsaWduOnJpZ2h0fQogIC5vci10'
        'YWJsbyB0ZHtwYWRkaW5nOjExcHggMTJweDtib3JkZXItYm90dG9tOjFweCBzb2xpZCB2'
        'YXIoLS1jaXpnaSk7dmVydGljYWwtYWxpZ246bWlkZGxlfQogIC5vci10YWJsbyB0Ym9k'
        'eSB0cntjdXJzb3I6cG9pbnRlcn0KICAub3ItdGFibG8gdGJvZHkgdHI6aG92ZXJ7YmFj'
        'a2dyb3VuZDp2YXIoLS1ub3RyLWJnKX0KICAub3ItYWR7Zm9udC13ZWlnaHQ6NzAwfQog'
        'IC5vci10dXRhcntmb250LXZhcmlhbnQtbnVtZXJpYzp0YWJ1bGFyLW51bXM7Zm9udC13'
        'ZWlnaHQ6NzAwO3doaXRlLXNwYWNlOm5vd3JhcH0KICAub3ItYm9ze3BhZGRpbmc6MzRw'
        'eDt0ZXh0LWFsaWduOmNlbnRlcjtjb2xvcjp2YXIoLS1zb2x1ayk7Zm9udC1zaXplOi45'
        'cmVtfQogIC5vci1ldGlrZXR7ZGlzcGxheTppbmxpbmUtYmxvY2s7Zm9udC1zaXplOi42'
        'OHJlbTtmb250LXdlaWdodDo3MDA7bGV0dGVyLXNwYWNpbmc6LjA0ZW07CiAgICB0ZXh0'
        'LXRyYW5zZm9ybTp1cHBlcmNhc2U7cGFkZGluZzozcHggOHB4O2JvcmRlci1yYWRpdXM6'
        'MjBweDsKICAgIGJhY2tncm91bmQ6dmFyKC0tbm90ci1iZyk7Y29sb3I6dmFyKC0tc29s'
        'dWspO3doaXRlLXNwYWNlOm5vd3JhcH0KICAub3ItZXRpa2V0LmFjaWt7YmFja2dyb3Vu'
        'ZDp2YXIoLS12ZXJkZS1hY2lrKTtjb2xvcjp2YXIoLS12ZXJkZS1rb3l1KX0KCiAgLyog'
        '4pSA4pSAIEhFU0FQIETDlkvDnE3DnCDilIDilIAgKi8KICAub3ItaGVzYXB7Ym9yZGVy'
        'OjFweCBzb2xpZCB2YXIoLS1jaXpnaSk7Ym9yZGVyLXJhZGl1czp2YXIoLS1yKTsKICAg'
        'IGJhY2tncm91bmQ6dmFyKC0teXV6ZXkpO3BhZGRpbmc6NHB4IDA7bWFyZ2luOjEwcHgg'
        'MCAxNHB4fQogIC5vci1zYXRpcntkaXNwbGF5OmZsZXg7YWxpZ24taXRlbXM6YmFzZWxp'
        'bmU7Z2FwOjEycHg7cGFkZGluZzo4cHggMTZweDsKICAgIGZvbnQtc2l6ZTouODhyZW19'
        'CiAgLm9yLXNhdGlyIC5ldHtmbGV4OjE7Y29sb3I6dmFyKC0tc29sdWspfQogIC5vci1z'
        'YXRpciAudHR7Zm9udC12YXJpYW50LW51bWVyaWM6dGFidWxhci1udW1zO2ZvbnQtd2Vp'
        'Z2h0OjYwMDt3aGl0ZS1zcGFjZTpub3dyYXB9CiAgLm9yLXNhdGlyLmthbGlue2JvcmRl'
        'ci10b3A6MXB4IHNvbGlkIHZhcigtLWNpemdpKTtmb250LXdlaWdodDo3MDB9CiAgLm9y'
        'LXNhdGlyLmthbGluIC5ldHtjb2xvcjp2YXIoLS1tdXJla2tlcCl9CiAgLm9yLXNhdGly'
        'LmthbGluIC50dHtmb250LXNpemU6MS4wMnJlbX0KICAub3Itc2F0aXIuYWx0e3BhZGRp'
        'bmctbGVmdDozMHB4O2ZvbnQtc2l6ZTouODRyZW19CiAgLm9yLXNhdGlyLmFsdCAuZXQ6'
        'OmJlZm9yZXtjb250ZW50OifilJQgJztjb2xvcjp2YXIoLS1jaXpnaS1rb3l1KX0KICAu'
        'b3ItZWtzaSAudHR7Y29sb3I6dmFyKC0ta2lybWl6aSl9CiAgLyogYC5ldGAgZGFyYWxh'
        'Ymlsc2luIGFtYSBUVVRBUiBoacOnIGvEsXLEsWxtYXPEsW46IHV6dW4gdmVyZ2kgYWTE'
        'sQogICAgIHNhdMSxcsSxIGFsdCBhbHRhIGTDtmtlcnNlIGhlc2FwIG9rdW5tYXogaMOi'
        'bGUgZ2VsaXlvcmR1LiAqLwogIC5vci1zYXRpciAuZXR7bWluLXdpZHRoOjB9CiAgLm9y'
        'LXNpbHtjdXJzb3I6cG9pbnRlcjtjb2xvcjp2YXIoLS1raXJtaXppKTtmb250LXNpemU6'
        'Ljc2cmVtOwogICAgd2hpdGUtc3BhY2U6bm93cmFwO29wYWNpdHk6Ljc1fQogIC5vci1z'
        'aWw6aG92ZXJ7b3BhY2l0eToxO3RleHQtZGVjb3JhdGlvbjp1bmRlcmxpbmV9CiAgLm9y'
        'LXNvbnVje2JhY2tncm91bmQ6dmFyKC0tdmVyZGUtYWNpayl9CiAgLm9yLXNvbnVjIC5l'
        'dCwub3Itc29udWMgLnR0e2NvbG9yOnZhcigtLXZlcmRlLWtveXUpfQoKICAub3ItdXlh'
        'cml7ZGlzcGxheTpmbGV4O2dhcDo5cHg7YWxpZ24taXRlbXM6ZmxleC1zdGFydDtwYWRk'
        'aW5nOjEwcHggMTRweDsKICAgIGJvcmRlci1yYWRpdXM6dmFyKC0tci1rdWN1ayk7YmFj'
        'a2dyb3VuZDp2YXIoLS1rZWhyaWJhci1hY2lrLCNGRkY2RTUpOwogICAgYm9yZGVyOjFw'
        'eCBzb2xpZCB2YXIoLS1rZWhyaWJhciwjRTBBNTI2KTtmb250LXNpemU6Ljg0cmVtO21h'
        'cmdpbi1ib3R0b206OHB4fQogIC5vci11eWFyaSBie2Rpc3BsYXk6YmxvY2t9CgogIC5v'
        'ci1ib2x1bXttYXJnaW46MThweCAwIDhweDtmb250LXNpemU6Ljc0cmVtO2ZvbnQtd2Vp'
        'Z2h0OjcwMDtsZXR0ZXItc3BhY2luZzouMDVlbTsKICAgIHRleHQtdHJhbnNmb3JtOnVw'
        'cGVyY2FzZTtjb2xvcjp2YXIoLS1zb2x1ayk7ZGlzcGxheTpmbGV4O2FsaWduLWl0ZW1z'
        'OmNlbnRlcjsKICAgIGdhcDoxMHB4fQogIC5vci1ib2x1bSBidXR0b257bWFyZ2luLWxl'
        'ZnQ6YXV0b30KICAub3ItYm9sdW0gLmJsb2stYnRue2ZsZXg6MCAwIGF1dG87bWluLXdp'
        'ZHRoOjA7cGFkZGluZzo2cHggMTJweDtmb250LXNpemU6Ljc4cmVtfQogIC5vci1taW5p'
        'IC5ibG9rLWJ0bntmbGV4OjAgMCBhdXRvO21pbi13aWR0aDowO3BhZGRpbmc6NXB4IDEw'
        'cHg7Zm9udC1zaXplOi43NnJlbX0KICAub3ItbWluaXt3aWR0aDoxMDAlO2JvcmRlci1j'
        'b2xsYXBzZTpjb2xsYXBzZTtmb250LXNpemU6Ljg0cmVtfQogIC5vci1taW5pIHRke3Bh'
        'ZGRpbmc6N3B4IDEwcHg7Ym9yZGVyLWJvdHRvbToxcHggc29saWQgdmFyKC0tY2l6Z2kp'
        'fQogIC5vci1taW5pIHRkLnNhZ3t0ZXh0LWFsaWduOnJpZ2h0O2ZvbnQtdmFyaWFudC1u'
        'dW1lcmljOnRhYnVsYXItbnVtc30KICAub3ItbWluaSAuc2lse2NvbG9yOnZhcigtLWtp'
        'cm1pemkpO2N1cnNvcjpwb2ludGVyO2ZvbnQtc2l6ZTouOHJlbX0KCiAgLm1vZGFsLW9y'
        'dHV7cG9zaXRpb246Zml4ZWQ7aW5zZXQ6MDtiYWNrZ3JvdW5kOnJnYmEoMjUsMjgsMjYs'
        'LjQpO2Rpc3BsYXk6bm9uZTsKICAgIHotaW5kZXg6NDU7cGxhY2UtaXRlbXM6Y2VudGVy'
        'O3BhZGRpbmc6MjBweH0KICAubW9kYWwtb3J0dS5hY2lre2Rpc3BsYXk6Z3JpZH0KICAu'
        'bW9kYWx7d2lkdGg6NjAwcHg7bWF4LXdpZHRoOjEwMCU7YmFja2dyb3VuZDp2YXIoLS15'
        'dXpleSk7Ym9yZGVyLXJhZGl1czoxNHB4OwogICAgYm94LXNoYWRvdzp2YXIoLS1nb2xn'
        'ZS1idXl1aywwIDE4cHggNTBweCByZ2JhKDAsMCwwLC4xOCkpOwogICAgbWF4LWhlaWdo'
        'dDo4OHZoO292ZXJmbG93OmF1dG99CiAgLm1vZGFsLWJhc3twYWRkaW5nOjE4cHggMjJw'
        'eCAxMHB4fQogIC5tb2RhbC1iYXMgaDN7Zm9udC1mYW1pbHk6dmFyKC0tYmFzbGlrKTtm'
        'b250LXNpemU6MS4xcmVtO21hcmdpbjowfQogIC5tb2RhbC1iYXMgcHtmb250LXNpemU6'
        'LjgycmVtO2NvbG9yOnZhcigtLXNvbHVrKTttYXJnaW46NHB4IDAgMH0KICAubW9kYWwt'
        'YWx0e3BhZGRpbmc6MTRweCAyMnB4IDE4cHg7ZGlzcGxheTpmbGV4O2dhcDoxMHB4O2p1'
        'c3RpZnktY29udGVudDpmbGV4LWVuZDsKICAgIGJvcmRlci10b3A6MXB4IHNvbGlkIHZh'
        'cigtLWNpemdpKX0KICAuZm9ybS1zYXRpcntkaXNwbGF5OmdyaWQ7Z2FwOjEycHg7bWFy'
        'Z2luLWJvdHRvbToxMnB4fQogIC5mb3JtLXNhdGlyLmYye2dyaWQtdGVtcGxhdGUtY29s'
        'dW1uczoxZnIgMWZyfQogIC5mb3JtLXNhdGlyLmYze2dyaWQtdGVtcGxhdGUtY29sdW1u'
        'czoxZnIgMWZyIDFmcn0KICAuZm9ybS1hbGFuIGxhYmVse2Rpc3BsYXk6YmxvY2s7Zm9u'
        'dC1zaXplOi43MnJlbTtmb250LXdlaWdodDo3MDA7bGV0dGVyLXNwYWNpbmc6LjA0ZW07'
        'CiAgICB0ZXh0LXRyYW5zZm9ybTp1cHBlcmNhc2U7Y29sb3I6dmFyKC0tc29sdWspO21h'
        'cmdpbi1ib3R0b206NXB4fQogIC5mb3JtLWFsYW4gaW5wdXQsLmZvcm0tYWxhbiBzZWxl'
        'Y3QsLmZvcm0tYWxhbiB0ZXh0YXJlYXt3aWR0aDoxMDAlOwogICAgYm9yZGVyOjFweCBz'
        'b2xpZCB2YXIoLS1jaXpnaS1rb3l1KTtib3JkZXItcmFkaXVzOnZhcigtLXIta3VjdWsp'
        'OwogICAgcGFkZGluZzo5cHggMTFweDtmb250LWZhbWlseTp2YXIoLS1nb3ZkZSk7Zm9u'
        'dC1zaXplOi44OHJlbTsKICAgIGJhY2tncm91bmQ6dmFyKC0teXV6ZXkpO2NvbG9yOnZh'
        'cigtLW11cmVra2VwKX0KICAuZm9ybS1hbGFuIGlucHV0OmZvY3VzLC5mb3JtLWFsYW4g'
        'c2VsZWN0OmZvY3VzLC5mb3JtLWFsYW4gdGV4dGFyZWE6Zm9jdXN7CiAgICBvdXRsaW5l'
        'Om5vbmU7Ym9yZGVyLWNvbG9yOnZhcigtLXZlcmRlKTtib3gtc2hhZG93OjAgMCAwIDNw'
        'eCB2YXIoLS12ZXJkZS1hY2lrKX0KICAueWFyZGlte2ZvbnQtc2l6ZTouNzZyZW07Y29s'
        'b3I6dmFyKC0tc29sdWspO21hcmdpbi10b3A6NHB4O2xpbmUtaGVpZ2h0OjEuNDV9Cjwv'
        'c3R5bGU+CnslIGVuZGJsb2NrICV9Cgp7JSBibG9jayBjb250ZW50ICV9CjxoMSBjbGFz'
        'cz0iZy1iYXNsaWsiPsSwxZ8gT3J0YWtsxLFrbGFyxLE8L2gxPgo8cCBjbGFzcz0iZy1h'
        'bHQiPk9ydGFrbGEgecO8csO8dMO8bGVuIGnFn2xlcmluIGvDonIgcGF5bGHFn8SxbSBo'
        'ZXNhYsSxLiBLw6JyIHJha2FtxLEKICBzYXTEscWfIGthecSxdGxhcsSxbmRhbiBnZWxp'
        'ciDigJQgYnVyYWRhIHllbmlkZW4gaGVzYXBsYW5tYXosIG8gecO8emRlbiBLYXJsxLFs'
        'xLFrCiAgZWtyYW7EsXlsYSBoZXIgemFtYW4gYXluxLEgcmFrYW3EsSBnw7ZzdGVyaXIu'
        'PC9wPgo8c3ZnIGNsYXNzPSJkYW1hciIgdmlld0JveD0iMCAwIDE5MCAxMCIgYXJpYS1o'
        'aWRkZW49InRydWUiPgogIDxwYXRoIGQ9Ik0wIDYgQyAyNSAyLCA0NSA5LCA3MCA1IFMg'
        'MTIwIDEsIDE1MCA2IFMgMTgwIDgsIDE5MCA0Ii8+CiAgPHBhdGggY2xhc3M9ImQyIiBk'
        'PSJNMCA4IEMgMzAgNSwgNjAgMTAsIDk1IDYgUyAxNjAgMywgMTkwIDciLz4KPC9zdmc+'
        'Cgo8ZGl2IGNsYXNzPSJvci11c3QiPgogIDxzZWxlY3QgaWQ9ImZEdXJ1bSIgY2xhc3M9'
        'Im9yLXNlYyIgb25jaGFuZ2U9Inl1a2xlKCkiPgogICAgPG9wdGlvbiB2YWx1ZT0iIj5U'
        'w7xtw7w8L29wdGlvbj4KICAgIDxvcHRpb24gdmFsdWU9IkFjaWsiIHNlbGVjdGVkPkHD'
        'p8Sxazwvb3B0aW9uPgogICAgPG9wdGlvbiB2YWx1ZT0iS2FwYW5kaSI+S2FwYW5kxLE8'
        'L29wdGlvbj4KICA8L3NlbGVjdD4KICA8YnV0dG9uIGNsYXNzPSJidG4teWVuaSIgc3R5'
        'bGU9Im1hcmdpbi1sZWZ0OmF1dG8iIG9uY2xpY2s9InllbmlBYygpIj4rIFllbmkgT3J0'
        'YWtsxLFrPC9idXR0b24+CjwvZGl2PgoKPGRpdiBjbGFzcz0idGFibG8ta3V0dSI+CiAg'
        'PHRhYmxlIGNsYXNzPSJvci10YWJsbyI+CiAgICA8dGhlYWQ+PHRyPgogICAgICA8dGg+'
        'T3J0YWtsxLFrPC90aD48dGg+T3J0YWs8L3RoPjx0aD5QYXk8L3RoPgogICAgICA8dGgg'
        'Y2xhc3M9InNhZyI+Q2lybzwvdGg+PHRoIGNsYXNzPSJzYWciPkJyw7x0IEvDonI8L3Ro'
        'PgogICAgICA8dGggY2xhc3M9InNhZyI+TmV0IEvDonI8L3RoPjx0aCBjbGFzcz0ic2Fn'
        'Ij5PcnRhayBCYWtpeWU8L3RoPgogICAgICA8dGg+RHVydW08L3RoPgogICAgPC90cj48'
        'L3RoZWFkPgogICAgPHRib2R5IGlkPSJnb3ZkZSI+PC90Ym9keT4KICA8L3RhYmxlPgog'
        'IDxkaXYgaWQ9ImJvcyIgY2xhc3M9Im9yLWJvcyIgc3R5bGU9ImRpc3BsYXk6bm9uZSI+'
        'SGVuw7x6IG9ydGFrbMSxayBrYXlkxLEgeW9rLjwvZGl2Pgo8L2Rpdj4KCjwhLS0g4pSA'
        '4pSAIFlFTsSwIC8gRMOcWkVOTEUg4pSA4pSAIC0tPgo8ZGl2IGNsYXNzPSJtb2RhbC1v'
        'cnR1IiBpZD0ib3J0TW9kYWwiPgogIDxkaXYgY2xhc3M9Im1vZGFsIj4KICAgIDxkaXYg'
        'Y2xhc3M9Im1vZGFsLWJhcyI+CiAgICAgIDxoMyBpZD0ibUJhc2xpayI+WWVuaSBPcnRh'
        'a2zEsWs8L2gzPgogICAgICA8cD5Lw6JyLCBiYcSfbGFuYW4gacWfbGVyaW4gc2F0xLHF'
        'nyBrYXnEsXRsYXLEsW5kYW4gdMO8cmVyLjwvcD4KICAgIDwvZGl2PgogICAgPGRpdiBj'
        'bGFzcz0ibW9kYWwtZ292Ij4KICAgICAgPGRpdiBjbGFzcz0iZm9ybS1zYXRpciI+CiAg'
        'ICAgICAgPGRpdiBjbGFzcz0iZm9ybS1hbGFuIj48bGFiZWw+T3J0YWtsxLFrIGFkxLEg'
        'KjwvbGFiZWw+CiAgICAgICAgICA8aW5wdXQgaWQ9Im1BZCIgcGxhY2Vob2xkZXI9IkFC'
        'QyBNZXJtZXIg4oCUIGtvbnRleW5lciBpxZ9pIj48L2Rpdj4KICAgICAgPC9kaXY+CiAg'
        'ICAgIDxkaXYgY2xhc3M9ImZvcm0tc2F0aXIgZjIiPgogICAgICAgIDxkaXYgY2xhc3M9'
        'ImZvcm0tYWxhbiI+PGxhYmVsPk9ydGFrIChjYXJpKTwvbGFiZWw+CiAgICAgICAgICA8'
        'c2VsZWN0IGlkPSJtQ2FyaSI+PC9zZWxlY3Q+CiAgICAgICAgICA8ZGl2IGNsYXNzPSJ5'
        'YXJkaW0iPkNhcml5ZSBpxZ9sZW1layBpc3RlcnNlbiBzZcOnaWxpIG9sbWFsxLEuPC9k'
        'aXY+PC9kaXY+CiAgICAgICAgPGRpdiBjbGFzcz0iZm9ybS1hbGFuIj48bGFiZWw+T3J0'
        'YWsgYWTEsTwvbGFiZWw+CiAgICAgICAgICA8aW5wdXQgaWQ9Im1PcnRha0FkIiBwbGFj'
        'ZWhvbGRlcj0iQ2FyaSBrYXJ0xLEgeW9rc2EgZWxsZSB5YXoiPjwvZGl2PgogICAgICA8'
        'L2Rpdj4KICAgICAgPGRpdiBjbGFzcz0iZm9ybS1zYXRpciBmMyI+CiAgICAgICAgPGRp'
        'diBjbGFzcz0iZm9ybS1hbGFuIj48bGFiZWw+Qml6aW0gcGF5ICU8L2xhYmVsPgogICAg'
        'ICAgICAgPGlucHV0IGlkPSJtQml6UGF5IiB0eXBlPSJudW1iZXIiIHN0ZXA9IjAuMDEi'
        'IG1pbj0iMCIgdmFsdWU9IjUwIj48L2Rpdj4KICAgICAgICA8ZGl2IGNsYXNzPSJmb3Jt'
        'LWFsYW4iPjxsYWJlbD5PcnRhayBwYXkgJTwvbGFiZWw+CiAgICAgICAgICA8aW5wdXQg'
        'aWQ9Im1PcnRha1BheSIgdHlwZT0ibnVtYmVyIiBzdGVwPSIwLjAxIiBtaW49IjAiIHZh'
        'bHVlPSI1MCI+PC9kaXY+CiAgICAgICAgPGRpdiBjbGFzcz0iZm9ybS1hbGFuIj48bGFi'
        'ZWw+RMO2dml6PC9sYWJlbD4KICAgICAgICAgIDxzZWxlY3QgaWQ9Im1Eb3ZpeiI+PG9w'
        'dGlvbj5VU0Q8L29wdGlvbj48b3B0aW9uPkVVUjwvb3B0aW9uPjxvcHRpb24+VFJZPC9v'
        'cHRpb24+PC9zZWxlY3Q+PC9kaXY+CiAgICAgIDwvZGl2PgogICAgICA8ZGl2IGNsYXNz'
        'PSJmb3JtLXNhdGlyIj4KICAgICAgICA8ZGl2IGNsYXNzPSJmb3JtLWFsYW4iPjxsYWJl'
        'bD5BbmFwYXJhIHnDtm50ZW1pPC9sYWJlbD4KICAgICAgICAgIDxzZWxlY3QgaWQ9Im1B'
        'bmFwYXJhIj4KICAgICAgICAgICAgPG9wdGlvbiB2YWx1ZT0iYXlyaSI+QW5hcGFyYSBh'
        'eXLEsSB0YWtpcCBlZGlsaXIg4oCUIGRhxJ/EsXTEsW0geWFsbsSxeiBrw6JyIHBhecSx'
        'PC9vcHRpb24+CiAgICAgICAgICAgIDxvcHRpb24gdmFsdWU9Im9uY2VfaWFkZSI+w5Zu'
        'Y2UgYW5hcGFyYSBpYWRlIGVkaWxpciDigJQgZGHEn8SxdMSxbSA9IGFuYXBhcmEgKyBr'
        'w6JyIHBhecSxPC9vcHRpb24+CiAgICAgICAgICA8L3NlbGVjdD4KICAgICAgICAgIDxk'
        'aXYgY2xhc3M9InlhcmRpbSI+xLBraSB5w7ZudGVtZGUgZGUgS8OCUiBheW7EsWTEsXI7'
        'IGRlxJ9pxZ9lbiwgb3J0YcSfYQogICAgICAgICAgICDDtmRlbmVjZWsgdHV0YXIuPC9k'
        'aXY+PC9kaXY+CiAgICAgIDwvZGl2PgogICAgICA8ZGl2IGNsYXNzPSJmb3JtLXNhdGly'
        'IGYyIj4KICAgICAgICA8ZGl2IGNsYXNzPSJmb3JtLWFsYW4iPjxsYWJlbD5CYcWfbGFu'
        'Z8Sxw6c8L2xhYmVsPgogICAgICAgICAgPGlucHV0IGlkPSJtQmFzbGFuZ2ljIiB0eXBl'
        'PSJkYXRlIj48L2Rpdj4KICAgICAgICA8ZGl2IGNsYXNzPSJmb3JtLWFsYW4iPjxsYWJl'
        'bD5CaXRpxZ88L2xhYmVsPgogICAgICAgICAgPGlucHV0IGlkPSJtQml0aXMiIHR5cGU9'
        'ImRhdGUiPjwvZGl2PgogICAgICA8L2Rpdj4KICAgICAgPGRpdiBjbGFzcz0iZm9ybS1z'
        'YXRpciI+CiAgICAgICAgPGRpdiBjbGFzcz0iZm9ybS1hbGFuIj48bGFiZWw+QcOnxLFr'
        'bGFtYTwvbGFiZWw+CiAgICAgICAgICA8dGV4dGFyZWEgaWQ9Im1BY2lrbGFtYSIgcm93'
        'cz0iMiI+PC90ZXh0YXJlYT48L2Rpdj4KICAgICAgPC9kaXY+CiAgICA8L2Rpdj4KICAg'
        'IDxkaXYgY2xhc3M9Im1vZGFsLWFsdCI+CiAgICAgIDxidXR0b24gY2xhc3M9ImJsb2st'
        'YnRuIiBvbmNsaWNrPSJvcnRLYXBhdCgpIj5WYXpnZcOnPC9idXR0b24+CiAgICAgIDxi'
        'dXR0b24gY2xhc3M9ImJ0bi15ZW5pIiBpZD0ibUtheWRldCIgb25jbGljaz0ib3J0S2F5'
        'ZGV0KCkiPktheWRldDwvYnV0dG9uPgogICAgPC9kaXY+CiAgPC9kaXY+CjwvZGl2PgoK'
        'PCEtLSDilIDilIAgS0FMRU0gRUtMRSAodmVyZ2kgLyBpxZ8gLyBzZXJtYXllIC8gZGHE'
        'n8SxdMSxbSkg4pSA4pSAIC0tPgo8ZGl2IGNsYXNzPSJtb2RhbC1vcnR1IiBpZD0ia2Fs'
        'ZW1Nb2RhbCI+CiAgPGRpdiBjbGFzcz0ibW9kYWwiIHN0eWxlPSJ3aWR0aDo1MjBweCI+'
        'CiAgICA8ZGl2IGNsYXNzPSJtb2RhbC1iYXMiPjxoMyBpZD0ia0Jhc2xpayI+RWtsZTwv'
        'aDM+PHAgaWQ9ImtBbHQiPjwvcD48L2Rpdj4KICAgIDxkaXYgY2xhc3M9Im1vZGFsLWdv'
        'diIgaWQ9ImtHb3ZkZSI+PC9kaXY+CiAgICA8ZGl2IGNsYXNzPSJtb2RhbC1hbHQiPgog'
        'ICAgICA8YnV0dG9uIGNsYXNzPSJibG9rLWJ0biIgb25jbGljaz0ia2FsZW1LYXBhdCgp'
        'Ij5WYXpnZcOnPC9idXR0b24+CiAgICAgIDxidXR0b24gY2xhc3M9ImJ0bi15ZW5pIiBv'
        'bmNsaWNrPSJrYWxlbUtheWRldCgpIj5Fa2xlPC9idXR0b24+CiAgICA8L2Rpdj4KICA8'
        'L2Rpdj4KPC9kaXY+CnslIGVuZGJsb2NrICV9Cgp7JSBibG9jayBzY3JpcHRzICV9Cjxz'
        'Y3JpcHQ+Ci8qIOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkAogICDEsMWeIE9SVEFLTElLTEFSSSDigJQgT1IxCgogICBVw6dsYXI6CiAgICAg'
        'L2FwaS9vcnRha2xpayAgICAgICAgICAgICAgICAgICAgICBsaXN0ZSAow7Z6ZXRsaSkK'
        'ICAgICAvYXBpL29ydGFrbGlrLzxpZD4gICAgICAgICAgICAgICAgIGRldGF5ICh0YW0g'
        'aGVzYXAgZMO2a8O8bcO8KQogICAgIC9hcGkvb3J0YWtsaWsvPGlkPi9pc3x2ZXJnaXxz'
        'ZXJtYXllfGRhZ2l0aW0KICAgICAvYXBpL29ydGFrbGlrLzxpZD4vZGFnaXRpbS88bj4v'
        'Y2FyaXllICAgaXN0ZcSfZSBiYcSfbMSxIGNhcmkga2F5ZMSxCiAgIOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkCAqLwpsZXQgVFVNID0gW10s'
        'IEFDSUsgPSBudWxsLCBEVVpFTkxFID0gbnVsbCwgS0FMRU1fVElQID0gbnVsbCwgQ0FS'
        'SUxFUiA9IFtdOwoKZnVuY3Rpb24gcGFyYTIobiwgZCkgewogIGNvbnN0IHMgPSAoTnVt'
        'YmVyKG4pIHx8IDApLnRvTG9jYWxlU3RyaW5nKCd0ci1UUicsCiAgICB7bWluaW11bUZy'
        'YWN0aW9uRGlnaXRzOiAyLCBtYXhpbXVtRnJhY3Rpb25EaWdpdHM6IDJ9KTsKICByZXR1'
        'cm4gcyArICcgJyArIChkIHx8ICdVU0QnKTsKfQoKYXN5bmMgZnVuY3Rpb24geXVrbGUo'
        'KSB7CiAgY29uc3QgZHVydW0gPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnZkR1cnVt'
        'JykudmFsdWU7CiAgbGV0IGQ7CiAgdHJ5IHsgZCA9IGF3YWl0IGFwaSgnL2FwaS9vcnRh'
        'a2xpaycgKyAoZHVydW0gPyAnP2R1cnVtPScgKyBkdXJ1bSA6ICcnKSk7IH0KICBjYXRj'
        'aCAoZSkgeyBiaWxkaXIoZS5tZXNzYWdlIHx8ICdMaXN0ZSBhbMSxbmFtYWTEsScsIHRy'
        'dWUpOyByZXR1cm47IH0KICBUVU0gPSBkLmRhdGEgfHwgW107CiAgY2l6KCk7Cn0KCmZ1'
        'bmN0aW9uIGNpeigpIHsKICBjb25zdCBnID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQo'
        'J2dvdmRlJyk7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2JvcycpLnN0eWxlLmRp'
        'c3BsYXkgPSBUVU0ubGVuZ3RoID8gJ25vbmUnIDogJyc7CiAgZy5pbm5lckhUTUwgPSBU'
        'VU0ubWFwKG8gPT4gewogICAgY29uc3QgeiA9IG8ub3pldCB8fCB7fTsKICAgIHJldHVy'
        'biBgPHRyIG9uY2xpY2s9ImRldGF5QWMoJyR7a2FjYXIoby5pZCl9JykiPgogICAgICA8'
        'dGQ+PGRpdiBjbGFzcz0ib3ItYWQiPiR7a2FjYXIoby5hZCl9PC9kaXY+CiAgICAgICAg'
        'ICA8ZGl2IHN0eWxlPSJjb2xvcjp2YXIoLS1zb2x1ayk7Zm9udC1zaXplOi43OHJlbSI+'
        'JHtrYWNhcihvLmlkKX0gwrcgJHt6LmlzX2FkZWRpIHx8IDB9IGnFnyR7CiAgICAgICAg'
        'ICAgIHoudXlhcmlfYWRlZGkgPyBgIMK3IDxzcGFuIHN0eWxlPSJjb2xvcjp2YXIoLS1r'
        'ZWhyaWJhciwjQjg4NjBCKSI+JHt6LnV5YXJpX2FkZWRpfSB1eWFyxLE8L3NwYW4+YCA6'
        'ICcnfTwvZGl2PjwvdGQ+CiAgICAgIDx0ZD4ke2thY2FyKG8ub3J0YWtfYWQgfHwgJ+KA'
        'lCcpfTwvdGQ+CiAgICAgIDx0ZCBjbGFzcz0ibW9ubyI+JSR7by5iaXppbV9wYXl9IC8g'
        'JSR7by5vcnRha19wYXl9PC90ZD4KICAgICAgPHRkIGNsYXNzPSJzYWcgb3ItdHV0YXIi'
        'PiR7cGFyYTIoei5jaXJvLCBvLmRvdml6KX08L3RkPgogICAgICA8dGQgY2xhc3M9InNh'
        'ZyBvci10dXRhciI+JHtwYXJhMih6LmJydXRfa2FyLCBvLmRvdml6KX08L3RkPgogICAg'
        'ICA8dGQgY2xhc3M9InNhZyBvci10dXRhciIgc3R5bGU9ImNvbG9yOnZhcigtLXZlcmRl'
        'KSI+JHtwYXJhMih6Lm5ldF9rYXIsIG8uZG92aXopfTwvdGQ+CiAgICAgIDx0ZCBjbGFz'
        'cz0ic2FnIG9yLXR1dGFyIj4ke3BhcmEyKHoub3J0YWtfYmFraXllLCBvLmRvdml6KX08'
        'L3RkPgogICAgICA8dGQ+PHNwYW4gY2xhc3M9Im9yLWV0aWtldCAke28uZHVydW0gPT09'
        'ICdBY2lrJyA/ICdhY2lrJyA6ICcnfSI+JHtrYWNhcihvLmR1cnVtKX08L3NwYW4+PC90'
        'ZD4KICAgIDwvdHI+YDsKICB9KS5qb2luKCcnKTsKfQoKLyog4pSA4pSAIERFVEFZOiBo'
        'ZXNhYsSxbiBoZXIgYmFzYW1hxJ/EsSDilIDilIAgKi8KYXN5bmMgZnVuY3Rpb24gZGV0'
        'YXlBYyhpZCkgewogIGxldCBkOwogIHRyeSB7IGQgPSBhd2FpdCBhcGkoJy9hcGkvb3J0'
        'YWtsaWsvJyArIGVuY29kZVVSSUNvbXBvbmVudChpZCkpOyB9CiAgY2F0Y2ggKGUpIHsg'
        'YmlsZGlyKGUubWVzc2FnZSB8fCAnRGV0YXkgYWzEsW5hbWFkxLEnLCB0cnVlKTsgcmV0'
        'dXJuOyB9CiAgQUNJSyA9IGQuZGF0YTsKICBjb25zdCBvID0gQUNJSywgaCA9IG8uaGVz'
        'YXAsIGR2ID0gby5kb3ZpejsKCiAgY29uc3QgdXlhcmlsYXIgPSAoaC51eWFyaWxhciB8'
        'fCBbXSkubWFwKHUgPT4KICAgIGA8ZGl2IGNsYXNzPSJvci11eWFyaSI+PHNwYW4+4pqg'
        'PC9zcGFuPjxzcGFuPiR7a2FjYXIodSl9PC9zcGFuPjwvZGl2PmApLmpvaW4oJycpOwoK'
        'ICBjb25zdCB2ZXJnaVNhdGlyID0gKGgudmVyZ2lsZXIgfHwgW10pLm1hcCh2ID0+IGAK'
        'ICAgIDxkaXYgY2xhc3M9Im9yLXNhdGlyIGFsdCBvci1la3NpIj4KICAgICAgPHNwYW4g'
        'Y2xhc3M9ImV0Ij4ke2thY2FyKHYuYWQpfSR7CiAgICAgICAgdi5tYXRyYWhfdGlwaSA9'
        'PT0gJ3NhYml0JyA/ICcgKHNhYml0KScKICAgICAgICAgIDogYCAoJSR7di5vcmFufSDD'
        'lyAke3YubWF0cmFoX3RpcGkgPT09ICdjaXJvJyA/ICdjaXJvJyA6ICdicsO8dCBrw6Jy'
        'J30pYH0kewogICAgICAgIHYuZHVydW0gPT09ICd0YWhtaW5pJyA/ICcgwrcgPGIgc3R5'
        'bGU9ImNvbG9yOnZhcigtLWtlaHJpYmFyLCNCODg2MEIpIj50YWhtaW5pPC9iPicgOiAn'
        'J308L3NwYW4+CiAgICAgIDxzcGFuIGNsYXNzPSJ0dCI+4oiSICR7cGFyYTIodi50dXRh'
        'ciwgZHYpfTwvc3Bhbj4KICAgICAgPHNwYW4gY2xhc3M9Im9yLXNpbCIgb25jbGljaz0i'
        'dmVyZ2lTaWwoJHt2LmlkfSkiPnNpbDwvc3Bhbj4KICAgIDwvZGl2PmApLmpvaW4oJycp'
        'OwoKICBjb25zdCBoZXNhcEhUTUwgPSBgCiAgICA8ZGl2IGNsYXNzPSJvci1oZXNhcCI+'
        'CiAgICAgIDxkaXYgY2xhc3M9Im9yLXNhdGlyIj48c3BhbiBjbGFzcz0iZXQiPkNpcm8g'
        'KCR7aC5zYXRpc19hZGVkaX0gc2F0xLHFnyBrYXlkxLEpPC9zcGFuPgogICAgICAgIDxz'
        'cGFuIGNsYXNzPSJ0dCI+JHtwYXJhMihoLmNpcm8sIGR2KX08L3NwYW4+PC9kaXY+CiAg'
        'ICAgIDxkaXYgY2xhc3M9Im9yLXNhdGlyIG9yLWVrc2kiPjxzcGFuIGNsYXNzPSJldCI+'
        'TWFsaXlldDwvc3Bhbj4KICAgICAgICA8c3BhbiBjbGFzcz0idHQiPuKIkiAke3BhcmEy'
        'KGgubWFsaXlldCwgZHYpfTwvc3Bhbj48L2Rpdj4KICAgICAgPGRpdiBjbGFzcz0ib3It'
        'c2F0aXIga2FsaW4iPjxzcGFuIGNsYXNzPSJldCI+QnLDvHQga8Oicjwvc3Bhbj4KICAg'
        'ICAgICA8c3BhbiBjbGFzcz0idHQiPiR7cGFyYTIoaC5icnV0X2thciwgZHYpfTwvc3Bh'
        'bj48L2Rpdj4KICAgICAgJHt2ZXJnaVNhdGlyIHx8ICc8ZGl2IGNsYXNzPSJvci1zYXRp'
        'ciBhbHQiPjxzcGFuIGNsYXNzPSJldCI+dmVyZ2kga2FsZW1pIHlvazwvc3Bhbj48c3Bh'
        'biBjbGFzcz0idHQiPuKAlDwvc3Bhbj48L2Rpdj4nfQogICAgICA8ZGl2IGNsYXNzPSJv'
        'ci1zYXRpciBrYWxpbiBvci1zb251YyI+PHNwYW4gY2xhc3M9ImV0Ij5OZXQga8Oicjwv'
        'c3Bhbj4KICAgICAgICA8c3BhbiBjbGFzcz0idHQiPiR7cGFyYTIoaC5uZXRfa2FyLCBk'
        'dil9PC9zcGFuPjwvZGl2PgogICAgICA8ZGl2IGNsYXNzPSJvci1zYXRpciBhbHQiPjxz'
        'cGFuIGNsYXNzPSJldCI+Qml6aW0gcGF5ICglJHtoLmJpemltX3BheX0pPC9zcGFuPgog'
        'ICAgICAgIDxzcGFuIGNsYXNzPSJ0dCI+JHtwYXJhMihoLnBheWxhci5iaXosIGR2KX08'
        'L3NwYW4+PC9kaXY+CiAgICAgIDxkaXYgY2xhc3M9Im9yLXNhdGlyIGFsdCI+PHNwYW4g'
        'Y2xhc3M9ImV0Ij5PcnRhayBwYXkgKCUke2gub3J0YWtfcGF5fSk8L3NwYW4+CiAgICAg'
        'ICAgPHNwYW4gY2xhc3M9InR0Ij4ke3BhcmEyKGgucGF5bGFyLm9ydGFrLCBkdil9PC9z'
        'cGFuPjwvZGl2PgogICAgICAke2guYW5hcGFyYV95b250ZW1pID09PSAnb25jZV9pYWRl'
        'JyA/IGAKICAgICAgPGRpdiBjbGFzcz0ib3Itc2F0aXIgYWx0Ij48c3BhbiBjbGFzcz0i'
        'ZXQiPk9ydGHEn8SxbiBpYWRlIGVkaWxlY2VrIGFuYXBhcmFzxLE8L3NwYW4+CiAgICAg'
        'ICAgPHNwYW4gY2xhc3M9InR0Ij4ke3BhcmEyKGgua2FsYW5fYW5hcGFyYS5vcnRhaywg'
        'ZHYpfTwvc3Bhbj48L2Rpdj5gIDogJyd9CiAgICAgIDxkaXYgY2xhc3M9Im9yLXNhdGly'
        'IGthbGluIj48c3BhbiBjbGFzcz0iZXQiPk9ydGHEn2Egw7ZkZW5lY2VrPC9zcGFuPgog'
        'ICAgICAgIDxzcGFuIGNsYXNzPSJ0dCI+JHtwYXJhMihoLm9kZW5lY2VrLm9ydGFrLCBk'
        'dil9PC9zcGFuPjwvZGl2PgogICAgICA8ZGl2IGNsYXNzPSJvci1zYXRpciBhbHQiPjxz'
        'cGFuIGNsYXNzPSJldCI+xZ5pbWRpeWUga2FkYXIgZGHEn8SxdMSxbGFuPC9zcGFuPgog'
        'ICAgICAgIDxzcGFuIGNsYXNzPSJ0dCI+JHtwYXJhMihoLmRhZ2l0aWxhbi5vcnRhaywg'
        'ZHYpfTwvc3Bhbj48L2Rpdj4KICAgICAgPGRpdiBjbGFzcz0ib3Itc2F0aXIga2FsaW4i'
        'PjxzcGFuIGNsYXNzPSJldCI+T3J0YWsgYmFraXllIChrYWxhbik8L3NwYW4+CiAgICAg'
        'ICAgPHNwYW4gY2xhc3M9InR0Ij4ke3BhcmEyKGguYmFraXllLm9ydGFrLCBkdil9PC9z'
        'cGFuPjwvZGl2PgogICAgPC9kaXY+YDsKCiAgY29uc3QgaXNsZXIgPSAoby5pc2xlciB8'
        'fCBbXSkubWFwKGkgPT4gYDx0cj4KICAgICAgPHRkIGNsYXNzPSJtb25vIj4ke2thY2Fy'
        'KGkua2F5bmFrX3RpcCl9ICR7a2FjYXIoaS5rYXluYWtfaWQpfTwvdGQ+CiAgICAgIDx0'
        'ZD4ke2thY2FyKGkuYWNpa2xhbWEgfHwgJycpfTwvdGQ+CiAgICAgIDx0ZCBjbGFzcz0i'
        'c2FnIj48c3BhbiBjbGFzcz0ic2lsIiBvbmNsaWNrPSJpc1NpbCgke2kuaWR9KSI+w6fD'
        'tno8L3NwYW4+PC90ZD4KICAgIDwvdHI+YCkuam9pbignJykgfHwgJzx0cj48dGQgY29s'
        'c3Bhbj0iMyIgc3R5bGU9ImNvbG9yOnZhcigtLXNvbHVrKSI+acWfIGJhxJ9sYW5tYWTE'
        'sTwvdGQ+PC90cj4nOwoKICBjb25zdCBzZXJtID0gKG8uc2VybWF5ZV9oYXJla2V0bGVy'
        'aSB8fCBbXSkubWFwKHMgPT4gYDx0cj4KICAgICAgPHRkPiR7cy50YXJhZiA9PT0gJ29y'
        'dGFrJyA/ICdPcnRhaycgOiAnQml6J30gwrcgJHtzLnlvbiA9PT0gJ2tveWR1JyA/ICdr'
        'b3lkdScgOiAnZ2VyaSBhbGTEsSd9PC90ZD4KICAgICAgPHRkIGNsYXNzPSJtb25vIj4k'
        'e2thY2FyKHMudGFyaWggfHwgJycpfTwvdGQ+CiAgICAgIDx0ZCBjbGFzcz0ic2FnIj4k'
        'e3BhcmEyKHMudHV0YXIsIHMuZG92aXopfTwvdGQ+CiAgICAgIDx0ZCBjbGFzcz0ic2Fn'
        'Ij48c3BhbiBjbGFzcz0ic2lsIiBvbmNsaWNrPSJzZXJtYXllU2lsKCR7cy5pZH0pIj5z'
        'aWw8L3NwYW4+PC90ZD4KICAgIDwvdHI+YCkuam9pbignJykgfHwgJzx0cj48dGQgY29s'
        'c3Bhbj0iNCIgc3R5bGU9ImNvbG9yOnZhcigtLXNvbHVrKSI+c2VybWF5ZSBoYXJla2V0'
        'aSB5b2s8L3RkPjwvdHI+JzsKCiAgY29uc3QgZGFnID0gKGguZGFnaXRpbWxhciB8fCBb'
        'XSkubWFwKHggPT4gYDx0cj4KICAgICAgPHRkPiR7eC50YXJhZiA9PT0gJ29ydGFrJyA/'
        'ICdPcnRhaycgOiAnQml6J308L3RkPgogICAgICA8dGQgY2xhc3M9Im1vbm8iPiR7a2Fj'
        'YXIoeC50YXJpaCB8fCAnJyl9PC90ZD4KICAgICAgPHRkIGNsYXNzPSJzYWciPiR7cGFy'
        'YTIoeC50dXRhciwgeC5kb3Zpeil9PC90ZD4KICAgICAgPHRkIGNsYXNzPSJzYWciPiR7'
        'eC5jYXJpeWVfaXNsZW5kaQogICAgICAgID8gYDxzcGFuIGNsYXNzPSJvci1ldGlrZXQg'
        'YWNpayI+Y2FyaWRlPC9zcGFuPgogICAgICAgICAgIDxzcGFuIGNsYXNzPSJzaWwiIG9u'
        'Y2xpY2s9ImNhcml5ZUdlcmlBbCgke3guaWR9KSI+Z2VyaSBhbDwvc3Bhbj5gCiAgICAg'
        'ICAgOiBgPGJ1dHRvbiBjbGFzcz0iYmxvay1idG4iIG9uY2xpY2s9ImNhcml5ZUlzbGUo'
        'JHt4LmlkfSkiPmNhcml5ZSBpxZ9sZTwvYnV0dG9uPgogICAgICAgICAgIDxzcGFuIGNs'
        'YXNzPSJzaWwiIG9uY2xpY2s9ImRhZ2l0aW1TaWwoJHt4LmlkfSkiPnNpbDwvc3Bhbj5g'
        'fTwvdGQ+CiAgICA8L3RyPmApLmpvaW4oJycpIHx8ICc8dHI+PHRkIGNvbHNwYW49IjQi'
        'IHN0eWxlPSJjb2xvcjp2YXIoLS1zb2x1aykiPmRhxJ/EsXTEsW0geW9rPC90ZD48L3Ry'
        'Pic7CgogIGNvbnN0IGdvdmRlID0gYAogICAgJHt1eWFyaWxhcn0KICAgICR7aGVzYXBI'
        'VE1MfQogICAgPGRpdiBjbGFzcz0ib3ItYm9sdW0iPkJhxJ9sxLEgacWfbGVyCiAgICAg'
        'IDxidXR0b24gY2xhc3M9ImJsb2stYnRuIiBvbmNsaWNrPSJrYWxlbUFjKCdpcycpIj4r'
        'IMSwxZ8gYmHEn2xhPC9idXR0b24+PC9kaXY+CiAgICA8dGFibGUgY2xhc3M9Im9yLW1p'
        'bmkiPjx0Ym9keT4ke2lzbGVyfTwvdGJvZHk+PC90YWJsZT4KICAgIDxkaXYgY2xhc3M9'
        'Im9yLWJvbHVtIj5WZXJnaSBrYWxlbWxlcmkKICAgICAgPGJ1dHRvbiBjbGFzcz0iYmxv'
        'ay1idG4iIG9uY2xpY2s9ImthbGVtQWMoJ3ZlcmdpJykiPisgVmVyZ2k8L2J1dHRvbj48'
        'L2Rpdj4KICAgIDxkaXYgY2xhc3M9InlhcmRpbSIgc3R5bGU9Im1hcmdpbi1ib3R0b206'
        'NnB4Ij5LdXJ1bWxhciB2ZXJnaXNpIHnEsWxsxLFrIGvDonIKICAgICAgw7x6ZXJpbmRl'
        'biBoZXNhcGxhbsSxcjsgdGVrIGJpciBpxZ9lIHBheSBldG1layBiaXIga2FidWxkw7xy'
        'LiBLYWxlbQogICAgICBrZXNpbmxlxZ9lbmUga2FkYXIgPGI+dGFobWluaTwvYj4ga2Fs'
        'c8Sxbi48L2Rpdj4KICAgIDxkaXYgY2xhc3M9Im9yLWJvbHVtIj5TZXJtYXllCiAgICAg'
        'IDxidXR0b24gY2xhc3M9ImJsb2stYnRuIiBvbmNsaWNrPSJrYWxlbUFjKCdzZXJtYXll'
        'JykiPisgSGFyZWtldDwvYnV0dG9uPjwvZGl2PgogICAgPHRhYmxlIGNsYXNzPSJvci1t'
        'aW5pIj48dGJvZHk+JHtzZXJtfTwvdGJvZHk+PC90YWJsZT4KICAgIDxkaXYgY2xhc3M9'
        'Im9yLWJvbHVtIj5EYcSfxLF0xLFtbGFyCiAgICAgIDxidXR0b24gY2xhc3M9ImJsb2st'
        'YnRuIiBvbmNsaWNrPSJrYWxlbUFjKCdkYWdpdGltJykiPisgRGHEn8SxdMSxbTwvYnV0'
        'dG9uPjwvZGl2PgogICAgPHRhYmxlIGNsYXNzPSJvci1taW5pIj48dGJvZHk+JHtkYWd9'
        'PC90Ym9keT48L3RhYmxlPmA7CgogIGNvbnN0IGV5bGVtID0gYDxidXR0b24gY2xhc3M9'
        'ImJsb2stYnRuIiBvbmNsaWNrPSJkdXplbmxlQWMoKSI+RMO8emVubGU8L2J1dHRvbj4K'
        'ICAgIDxidXR0b24gY2xhc3M9ImJsb2stYnRuIiBzdHlsZT0iY29sb3I6dmFyKC0ta2ly'
        'bWl6aSkiIG9uY2xpY2s9Im9ydFNpbCgpIj5TaWw8L2J1dHRvbj5gOwogIGNla21lY2VB'
        'YyhvLmFkLCBgJHtvLmlkfSDCtyAke28ub3J0YWtfYWQgfHwgJ29ydGFrIGJlbGlydGls'
        'bWVkaSd9IMK3ICUke28uYml6aW1fcGF5fS8lJHtvLm9ydGFrX3BheX1gLAogICAgICAg'
        'ICAgICBnb3ZkZSwgZXlsZW0pOwp9CgovKiDilIDilIAgWUVOxLAgLyBEw5xaRU5MRSDi'
        'lIDilIAgKi8KYXN5bmMgZnVuY3Rpb24gY2FyaWxlcmlZdWtsZSgpIHsKICBpZiAoQ0FS'
        'SUxFUi5sZW5ndGgpIHJldHVybjsKICB0cnkgewogICAgY29uc3QgZCA9IGF3YWl0IGFw'
        'aSgnL2FwaS9jYXJpP3Blcl9wYWdlPTMwMCcpOwogICAgQ0FSSUxFUiA9IGQuZGF0YSB8'
        'fCBbXTsKICB9IGNhdGNoIChlKSB7IENBUklMRVIgPSBbXTsgfQp9Cgphc3luYyBmdW5j'
        'dGlvbiB5ZW5pQWMoKSB7CiAgRFVaRU5MRSA9IG51bGw7CiAgYXdhaXQgY2FyaWxlcmlZ'
        'dWtsZSgpOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdtQmFzbGlrJykudGV4dENv'
        'bnRlbnQgPSAnWWVuaSBPcnRha2zEsWsnOwogIFsnbUFkJywgJ21PcnRha0FkJywgJ21B'
        'Y2lrbGFtYScsICdtQml0aXMnXS5mb3JFYWNoKGkgPT4KICAgIGRvY3VtZW50LmdldEVs'
        'ZW1lbnRCeUlkKGkpLnZhbHVlID0gJycpOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlk'
        'KCdtQml6UGF5JykudmFsdWUgPSA1MDsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgn'
        'bU9ydGFrUGF5JykudmFsdWUgPSA1MDsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgn'
        'bURvdml6JykudmFsdWUgPSAnVVNEJzsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgn'
        'bUFuYXBhcmEnKS52YWx1ZSA9ICdheXJpJzsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJ'
        'ZCgnbUJhc2xhbmdpYycpLnZhbHVlID0gbmV3IERhdGUoKS50b0lTT1N0cmluZygpLnNs'
        'aWNlKDAsIDEwKTsKICBjYXJpU2VjaW1DaXooJycpOwogIGRvY3VtZW50LmdldEVsZW1l'
        'bnRCeUlkKCdvcnRNb2RhbCcpLmNsYXNzTGlzdC5hZGQoJ2FjaWsnKTsKfQoKYXN5bmMg'
        'ZnVuY3Rpb24gZHV6ZW5sZUFjKCkgewogIGlmICghQUNJSykgcmV0dXJuOwogIERVWkVO'
        'TEUgPSBBQ0lLLmlkOwogIGF3YWl0IGNhcmlsZXJpWXVrbGUoKTsKICBkb2N1bWVudC5n'
        'ZXRFbGVtZW50QnlJZCgnbUJhc2xpaycpLnRleHRDb250ZW50ID0gJ09ydGFrbMSxxJ/E'
        'sSBEw7x6ZW5sZSc7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ21BZCcpLnZhbHVl'
        'ID0gQUNJSy5hZCB8fCAnJzsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnbU9ydGFr'
        'QWQnKS52YWx1ZSA9IEFDSUsub3J0YWtfYWQgfHwgJyc7CiAgZG9jdW1lbnQuZ2V0RWxl'
        'bWVudEJ5SWQoJ21CaXpQYXknKS52YWx1ZSA9IEFDSUsuYml6aW1fcGF5OwogIGRvY3Vt'
        'ZW50LmdldEVsZW1lbnRCeUlkKCdtT3J0YWtQYXknKS52YWx1ZSA9IEFDSUsub3J0YWtf'
        'cGF5OwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdtRG92aXonKS52YWx1ZSA9IEFD'
        'SUsuZG92aXogfHwgJ1VTRCc7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ21BbmFw'
        'YXJhJykudmFsdWUgPSBBQ0lLLmFuYXBhcmFfeW9udGVtaSB8fCAnYXlyaSc7CiAgZG9j'
        'dW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ21CYXNsYW5naWMnKS52YWx1ZSA9IEFDSUsuYmFz'
        'bGFuZ2ljIHx8ICcnOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdtQml0aXMnKS52'
        'YWx1ZSA9IEFDSUsuYml0aXMgfHwgJyc7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQo'
        'J21BY2lrbGFtYScpLnZhbHVlID0gQUNJSy5hY2lrbGFtYSB8fCAnJzsKICBjYXJpU2Vj'
        'aW1DaXooQUNJSy5vcnRha19jYXJpX2lkIHx8ICcnKTsKICBkb2N1bWVudC5nZXRFbGVt'
        'ZW50QnlJZCgnb3J0TW9kYWwnKS5jbGFzc0xpc3QuYWRkKCdhY2lrJyk7Cn0KCmZ1bmN0'
        'aW9uIGNhcmlTZWNpbUNpeihzZWNpbGkpIHsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJ'
        'ZCgnbUNhcmknKS5pbm5lckhUTUwgPQogICAgJzxvcHRpb24gdmFsdWU9IiI+4oCUIGNh'
        'cmkga2FydMSxIHlvayDigJQ8L29wdGlvbj4nICsKICAgIENBUklMRVIubWFwKGMgPT4g'
        'YDxvcHRpb24gdmFsdWU9IiR7a2FjYXIoYy5pZCl9IiR7CiAgICAgIGMuaWQgPT09IHNl'
        'Y2lsaSA/ICcgc2VsZWN0ZWQnIDogJyd9PiR7a2FjYXIoYy51bnZhbil9PC9vcHRpb24+'
        'YCkuam9pbignJyk7Cn0KCmZ1bmN0aW9uIG9ydEthcGF0KCkgeyBkb2N1bWVudC5nZXRF'
        'bGVtZW50QnlJZCgnb3J0TW9kYWwnKS5jbGFzc0xpc3QucmVtb3ZlKCdhY2lrJyk7IH0K'
        'CmFzeW5jIGZ1bmN0aW9uIG9ydEtheWRldCgpIHsKICBjb25zdCBnID0gewogICAgYWQ6'
        'IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdtQWQnKS52YWx1ZS50cmltKCksCiAgICBv'
        'cnRha19jYXJpX2lkOiBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnbUNhcmknKS52YWx1'
        'ZSwKICAgIG9ydGFrX2FkOiBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnbU9ydGFrQWQn'
        'KS52YWx1ZS50cmltKCksCiAgICBiaXppbV9wYXk6IHBhcnNlRmxvYXQoZG9jdW1lbnQu'
        'Z2V0RWxlbWVudEJ5SWQoJ21CaXpQYXknKS52YWx1ZSkgfHwgMCwKICAgIG9ydGFrX3Bh'
        'eTogcGFyc2VGbG9hdChkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnbU9ydGFrUGF5Jyku'
        'dmFsdWUpIHx8IDAsCiAgICBkb3ZpejogZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ21E'
        'b3ZpeicpLnZhbHVlLAogICAgYW5hcGFyYV95b250ZW1pOiBkb2N1bWVudC5nZXRFbGVt'
        'ZW50QnlJZCgnbUFuYXBhcmEnKS52YWx1ZSwKICAgIGJhc2xhbmdpYzogZG9jdW1lbnQu'
        'Z2V0RWxlbWVudEJ5SWQoJ21CYXNsYW5naWMnKS52YWx1ZSB8fCBudWxsLAogICAgYml0'
        'aXM6IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdtQml0aXMnKS52YWx1ZSB8fCBudWxs'
        'LAogICAgYWNpa2xhbWE6IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdtQWNpa2xhbWEn'
        'KS52YWx1ZS50cmltKCkKICB9OwogIGlmICghZy5hZCkgeyBiaWxkaXIoJ09ydGFrbMSx'
        'ayBhZMSxIHpvcnVubHUnLCB0cnVlKTsgcmV0dXJuOyB9CiAgLyogQ2FyaSBzZcOnaWxp'
        'eXNlIG9ydGFrIGFkxLFuxLEgb25kYW4gdGFtYW1sYSDigJQgaWtpIHllcmRlIGlraSBh'
        'ZAogICAgIHR1dG1haywgaGFuZ2lzaW5pbiBkb8SfcnUgb2xkdcSfdW51IGJlbGlyc2l6'
        'bGXFn3RpcmlyZGkuICovCiAgaWYgKGcub3J0YWtfY2FyaV9pZCAmJiAhZy5vcnRha19h'
        'ZCkgewogICAgY29uc3QgYyA9IENBUklMRVIuZmluZCh4ID0+IHguaWQgPT09IGcub3J0'
        'YWtfY2FyaV9pZCk7CiAgICBpZiAoYykgZy5vcnRha19hZCA9IGMudW52YW47CiAgfQog'
        'IHRyeSB7CiAgICBpZiAoRFVaRU5MRSkgewogICAgICBhd2FpdCBhcGkoJy9hcGkvb3J0'
        'YWtsaWsvJyArIGVuY29kZVVSSUNvbXBvbmVudChEVVpFTkxFKSwKICAgICAgICAgICAg'
        'ICAgIHttZXRob2Q6ICdQVVQnLCBib2R5OiBKU09OLnN0cmluZ2lmeShnKX0pOwogICAg'
        'ICBiaWxkaXIoJ0fDvG5jZWxsZW5kaScpOwogICAgfSBlbHNlIHsKICAgICAgYXdhaXQg'
        'YXBpKCcvYXBpL29ydGFrbGlrJywge21ldGhvZDogJ1BPU1QnLCBib2R5OiBKU09OLnN0'
        'cmluZ2lmeShnKX0pOwogICAgICBiaWxkaXIoZy5hZCArICcgZWtsZW5kaScpOwogICAg'
        'fQogIH0gY2F0Y2ggKGUpIHsgYmlsZGlyKGUubWVzc2FnZSB8fCAnS2F5ZGVkaWxlbWVk'
        'aScsIHRydWUpOyByZXR1cm47IH0KICBvcnRLYXBhdCgpOyBjZWttZWNlS2FwYXQoKTsg'
        'eXVrbGUoKTsKfQoKYXN5bmMgZnVuY3Rpb24gb3J0U2lsKCkgewogIGlmICghQUNJSykg'
        'cmV0dXJuOwogIGlmICghYXdhaXQgb25heWxhKGAiJHtBQ0lLLmFkfSIgb3J0YWtsxLHE'
        'n8SxIHZlIGLDvHTDvG4ga2FsZW1sZXJpIHNpbGluZWNlay5cblxuRGV2YW0gZWRpbHNp'
        'biBtaT9gLAogICAgICAgICAgICAgICAgICAgIHt0ZWhsaWtlOiB0cnVlfSkpIHJldHVy'
        'bjsKICB0cnkgeyBhd2FpdCBhcGkoJy9hcGkvb3J0YWtsaWsvJyArIGVuY29kZVVSSUNv'
        'bXBvbmVudChBQ0lLLmlkKSwge21ldGhvZDogJ0RFTEVURSd9KTsgfQogIGNhdGNoIChl'
        'KSB7IGJpbGRpcihlLm1lc3NhZ2UgfHwgJ1NpbGluZW1lZGknLCB0cnVlKTsgcmV0dXJu'
        'OyB9CiAgYmlsZGlyKCdTaWxpbmRpJyk7IGNla21lY2VLYXBhdCgpOyB5dWtsZSgpOwp9'
        'CgovKiDilIDilIAgS0FMRU0gRUtMRU1FIOKUgOKUgCAqLwpjb25zdCBLQUxFTV9BTEFO'
        'ID0gewogIGlzOiB7YmFzbGlrOiAnxLDFnyBiYcSfbGEnLCBhbHQ6ICdTaXBhcmnFnywg'
        'c2V2a2l5YXQgeWEgZGEgcHJvZm9ybWEgbnVtYXJhc8SxLicsIGh0bWw6IGAKICAgIDxk'
        'aXYgY2xhc3M9ImZvcm0tc2F0aXIgZjIiPgogICAgICA8ZGl2IGNsYXNzPSJmb3JtLWFs'
        'YW4iPjxsYWJlbD5UaXA8L2xhYmVsPjxzZWxlY3QgaWQ9ImtUaXAiPgogICAgICAgIDxv'
        'cHRpb24gdmFsdWU9IlNJUEFSSVMiPlNpcGFyacWfPC9vcHRpb24+CiAgICAgICAgPG9w'
        'dGlvbiB2YWx1ZT0iU0VWS0lZQVQiPlNldmtpeWF0PC9vcHRpb24+CiAgICAgICAgPG9w'
        'dGlvbiB2YWx1ZT0iUFJPRk9STUEiPlByb2Zvcm1hPC9vcHRpb24+PC9zZWxlY3Q+PC9k'
        'aXY+CiAgICAgIDxkaXYgY2xhc3M9ImZvcm0tYWxhbiI+PGxhYmVsPk51bWFyYSAqPC9s'
        'YWJlbD48aW5wdXQgaWQ9ImtObyIgcGxhY2Vob2xkZXI9IlNJUC0yNi0wMSI+PC9kaXY+'
        'CiAgICA8L2Rpdj4KICAgIDxkaXYgY2xhc3M9ImZvcm0tc2F0aXIiPjxkaXYgY2xhc3M9'
        'ImZvcm0tYWxhbiI+PGxhYmVsPkHDp8Sxa2xhbWE8L2xhYmVsPgogICAgICA8aW5wdXQg'
        'aWQ9ImtBY2lrbGFtYSI+PC9kaXY+PC9kaXY+YH0sCiAgdmVyZ2k6IHtiYXNsaWs6ICdW'
        'ZXJnaSBrYWxlbWknLCBhbHQ6ICdLw6JyZGFuIGTDvMWfw7xsZWNlayBrYWxlbS4nLCBo'
        'dG1sOiBgCiAgICA8ZGl2IGNsYXNzPSJmb3JtLXNhdGlyIj48ZGl2IGNsYXNzPSJmb3Jt'
        'LWFsYW4iPjxsYWJlbD5BZCAqPC9sYWJlbD4KICAgICAgPGlucHV0IGlkPSJrQWQiIHBs'
        'YWNlaG9sZGVyPSJLdXJ1bWxhciB2ZXJnaXNpIj48L2Rpdj48L2Rpdj4KICAgIDxkaXYg'
        'Y2xhc3M9ImZvcm0tc2F0aXIgZjMiPgogICAgICA8ZGl2IGNsYXNzPSJmb3JtLWFsYW4i'
        'PjxsYWJlbD5NYXRyYWg8L2xhYmVsPjxzZWxlY3QgaWQ9ImtNYXRyYWgiIG9uY2hhbmdl'
        'PSJ2ZXJnaUFsYW5EZWdpcygpIj4KICAgICAgICA8b3B0aW9uIHZhbHVlPSJrYXIiPkJy'
        'w7x0IGvDonIgw5cgb3Jhbjwvb3B0aW9uPgogICAgICAgIDxvcHRpb24gdmFsdWU9ImNp'
        'cm8iPkNpcm8gw5cgb3Jhbjwvb3B0aW9uPgogICAgICAgIDxvcHRpb24gdmFsdWU9InNh'
        'Yml0Ij5TYWJpdCB0dXRhcjwvb3B0aW9uPjwvc2VsZWN0PjwvZGl2PgogICAgICA8ZGl2'
        'IGNsYXNzPSJmb3JtLWFsYW4iIGlkPSJrT3JhbkFsYW4iPjxsYWJlbD5PcmFuICU8L2xh'
        'YmVsPgogICAgICAgIDxpbnB1dCBpZD0ia09yYW4iIHR5cGU9Im51bWJlciIgc3RlcD0i'
        'MC4wMSIgbWluPSIwIiB2YWx1ZT0iMjUiPjwvZGl2PgogICAgICA8ZGl2IGNsYXNzPSJm'
        'b3JtLWFsYW4iIGlkPSJrVHV0YXJBbGFuIiBzdHlsZT0iZGlzcGxheTpub25lIj48bGFi'
        'ZWw+VHV0YXI8L2xhYmVsPgogICAgICAgIDxpbnB1dCBpZD0ia1R1dGFyIiB0eXBlPSJu'
        'dW1iZXIiIHN0ZXA9IjAuMDEiIG1pbj0iMCI+PC9kaXY+CiAgICA8L2Rpdj4KICAgIDxk'
        'aXYgY2xhc3M9ImZvcm0tc2F0aXIgZjIiPgogICAgICA8ZGl2IGNsYXNzPSJmb3JtLWFs'
        'YW4iPjxsYWJlbD5EdXJ1bTwvbGFiZWw+PHNlbGVjdCBpZD0ia0R1cnVtIj4KICAgICAg'
        'ICA8b3B0aW9uIHZhbHVlPSJ0YWhtaW5pIj5UYWhtaW5pPC9vcHRpb24+CiAgICAgICAg'
        'PG9wdGlvbiB2YWx1ZT0ia2VzaW5sZXN0aSI+S2VzaW5sZcWfdGk8L29wdGlvbj4KICAg'
        'ICAgICA8b3B0aW9uIHZhbHVlPSJvZGVuZGkiPsOWZGVuZGk8L29wdGlvbj48L3NlbGVj'
        'dD4KICAgICAgICA8ZGl2IGNsYXNzPSJ5YXJkaW0iPlRhaG1pbmkga2FsZW1sZXIgZGHE'
        'n8SxdMSxbWRhIHV5YXLEsSBvbGFyYWsgZ8O2csO8bsO8ci48L2Rpdj48L2Rpdj4KICAg'
        'ICAgPGRpdiBjbGFzcz0iZm9ybS1hbGFuIj48bGFiZWw+w5ZkZW1lIHRhcmloaTwvbGFi'
        'ZWw+PGlucHV0IGlkPSJrVGFyaWgiIHR5cGU9ImRhdGUiPjwvZGl2PgogICAgPC9kaXY+'
        'YH0sCiAgc2VybWF5ZToge2Jhc2xpazogJ1Nlcm1heWUgaGFyZWtldGknLCBhbHQ6ICdL'
        'aW0ga295ZHUsIGtpbSBnZXJpIGFsZMSxLicsIGh0bWw6IGAKICAgIDxkaXYgY2xhc3M9'
        'ImZvcm0tc2F0aXIgZjIiPgogICAgICA8ZGl2IGNsYXNzPSJmb3JtLWFsYW4iPjxsYWJl'
        'bD5UYXJhZjwvbGFiZWw+PHNlbGVjdCBpZD0ia1RhcmFmIj4KICAgICAgICA8b3B0aW9u'
        'IHZhbHVlPSJvcnRhayI+T3J0YWs8L29wdGlvbj48b3B0aW9uIHZhbHVlPSJiaXoiPkJp'
        'ejwvb3B0aW9uPjwvc2VsZWN0PjwvZGl2PgogICAgICA8ZGl2IGNsYXNzPSJmb3JtLWFs'
        'YW4iPjxsYWJlbD5Zw7ZuPC9sYWJlbD48c2VsZWN0IGlkPSJrWW9uIj4KICAgICAgICA8'
        'b3B0aW9uIHZhbHVlPSJrb3lkdSI+S295ZHU8L29wdGlvbj48b3B0aW9uIHZhbHVlPSJn'
        'ZXJpX2FsZGkiPkdlcmkgYWxkxLE8L29wdGlvbj48L3NlbGVjdD48L2Rpdj4KICAgIDwv'
        'ZGl2PgogICAgPGRpdiBjbGFzcz0iZm9ybS1zYXRpciBmMiI+CiAgICAgIDxkaXYgY2xh'
        'c3M9ImZvcm0tYWxhbiI+PGxhYmVsPlR1dGFyICo8L2xhYmVsPgogICAgICAgIDxpbnB1'
        'dCBpZD0ia1R1dGFyIiB0eXBlPSJudW1iZXIiIHN0ZXA9IjAuMDEiIG1pbj0iMCI+PC9k'
        'aXY+CiAgICAgIDxkaXYgY2xhc3M9ImZvcm0tYWxhbiI+PGxhYmVsPlRhcmloPC9sYWJl'
        'bD48aW5wdXQgaWQ9ImtUYXJpaCIgdHlwZT0iZGF0ZSI+PC9kaXY+CiAgICA8L2Rpdj4K'
        'ICAgIDxkaXYgY2xhc3M9ImZvcm0tc2F0aXIiPjxkaXYgY2xhc3M9ImZvcm0tYWxhbiI+'
        'PGxhYmVsPkHDp8Sxa2xhbWE8L2xhYmVsPgogICAgICA8aW5wdXQgaWQ9ImtBY2lrbGFt'
        'YSI+PC9kaXY+PC9kaXY+YH0sCiAgZGFnaXRpbToge2Jhc2xpazogJ0RhxJ/EsXTEsW0n'
        'LCBhbHQ6ICdPcnRhxJ9hIHlhcMSxbGFuL3lhcMSxbGFjYWsgw7ZkZW1lLicsIGh0bWw6'
        'IGAKICAgIDxkaXYgY2xhc3M9ImZvcm0tc2F0aXIgZjIiPgogICAgICA8ZGl2IGNsYXNz'
        'PSJmb3JtLWFsYW4iPjxsYWJlbD5UYXJhZjwvbGFiZWw+PHNlbGVjdCBpZD0ia1RhcmFm'
        'Ij4KICAgICAgICA8b3B0aW9uIHZhbHVlPSJvcnRhayI+T3J0YWs8L29wdGlvbj48b3B0'
        'aW9uIHZhbHVlPSJiaXoiPkJpejwvb3B0aW9uPjwvc2VsZWN0PjwvZGl2PgogICAgICA8'
        'ZGl2IGNsYXNzPSJmb3JtLWFsYW4iPjxsYWJlbD5UdXRhciAqPC9sYWJlbD4KICAgICAg'
        'ICA8aW5wdXQgaWQ9ImtUdXRhciIgdHlwZT0ibnVtYmVyIiBzdGVwPSIwLjAxIiBtaW49'
        'IjAiPjwvZGl2PgogICAgPC9kaXY+CiAgICA8ZGl2IGNsYXNzPSJmb3JtLXNhdGlyIGYy'
        'Ij4KICAgICAgPGRpdiBjbGFzcz0iZm9ybS1hbGFuIj48bGFiZWw+VGFyaWg8L2xhYmVs'
        'PjxpbnB1dCBpZD0ia1RhcmloIiB0eXBlPSJkYXRlIj48L2Rpdj4KICAgICAgPGRpdiBj'
        'bGFzcz0iZm9ybS1hbGFuIj48bGFiZWw+QcOnxLFrbGFtYTwvbGFiZWw+PGlucHV0IGlk'
        'PSJrQWNpa2xhbWEiPjwvZGl2PgogICAgPC9kaXY+CiAgICA8ZGl2IGNsYXNzPSJ5YXJk'
        'aW0iPktheWRldHRpa3RlbiBzb25yYSBpc3RlcnNlbiAiY2FyaXllIGnFn2xlIiBpbGUg'
        'Y2FyaSBib3LDpwogICAgICBvbHXFn3R1cmFiaWxpcnNpbiDigJQgem9ydW5sdSBkZcSf'
        'aWwuPC9kaXY+YH0KfTsKCmZ1bmN0aW9uIGthbGVtQWModGlwKSB7CiAgS0FMRU1fVElQ'
        'ID0gdGlwOwogIGNvbnN0IGsgPSBLQUxFTV9BTEFOW3RpcF07CiAgZG9jdW1lbnQuZ2V0'
        'RWxlbWVudEJ5SWQoJ2tCYXNsaWsnKS50ZXh0Q29udGVudCA9IGsuYmFzbGlrOwogIGRv'
        'Y3VtZW50LmdldEVsZW1lbnRCeUlkKCdrQWx0JykudGV4dENvbnRlbnQgPSBrLmFsdDsK'
        'ICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgna0dvdmRlJykuaW5uZXJIVE1MID0gay5o'
        'dG1sOwogIGNvbnN0IHQgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgna1RhcmloJyk7'
        'CiAgaWYgKHQgJiYgIXQudmFsdWUpIHQudmFsdWUgPSBuZXcgRGF0ZSgpLnRvSVNPU3Ry'
        'aW5nKCkuc2xpY2UoMCwgMTApOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdrYWxl'
        'bU1vZGFsJykuY2xhc3NMaXN0LmFkZCgnYWNpaycpOwp9CgpmdW5jdGlvbiBrYWxlbUth'
        'cGF0KCkgeyBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgna2FsZW1Nb2RhbCcpLmNsYXNz'
        'TGlzdC5yZW1vdmUoJ2FjaWsnKTsgfQoKZnVuY3Rpb24gdmVyZ2lBbGFuRGVnaXMoKSB7'
        'CiAgY29uc3QgbSA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdrTWF0cmFoJykudmFs'
        'dWU7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2tPcmFuQWxhbicpLnN0eWxlLmRp'
        'c3BsYXkgPSBtID09PSAnc2FiaXQnID8gJ25vbmUnIDogJyc7CiAgZG9jdW1lbnQuZ2V0'
        'RWxlbWVudEJ5SWQoJ2tUdXRhckFsYW4nKS5zdHlsZS5kaXNwbGF5ID0gbSA9PT0gJ3Nh'
        'Yml0JyA/ICcnIDogJ25vbmUnOwp9CgpmdW5jdGlvbiBfZGVnZXIoaWQpIHsKICBjb25z'
        'dCBlID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoaWQpOwogIHJldHVybiBlID8gZS52'
        'YWx1ZSA6ICcnOwp9Cgphc3luYyBmdW5jdGlvbiBrYWxlbUtheWRldCgpIHsKICBpZiAo'
        'IUFDSUspIHJldHVybjsKICBjb25zdCBrb2sgPSAnL2FwaS9vcnRha2xpay8nICsgZW5j'
        'b2RlVVJJQ29tcG9uZW50KEFDSUsuaWQpICsgJy8nOwogIGxldCB5b2wsIGdvdmRlOwog'
        'IGlmIChLQUxFTV9USVAgPT09ICdpcycpIHsKICAgIHlvbCA9IGtvayArICdpcyc7CiAg'
        'ICBnb3ZkZSA9IHtrYXluYWtfdGlwOiBfZGVnZXIoJ2tUaXAnKSwga2F5bmFrX2lkOiBf'
        'ZGVnZXIoJ2tObycpLnRyaW0oKSwKICAgICAgICAgICAgIGFjaWtsYW1hOiBfZGVnZXIo'
        'J2tBY2lrbGFtYScpfTsKICAgIGlmICghZ292ZGUua2F5bmFrX2lkKSB7IGJpbGRpcign'
        'TnVtYXJhIHpvcnVubHUnLCB0cnVlKTsgcmV0dXJuOyB9CiAgfSBlbHNlIGlmIChLQUxF'
        'TV9USVAgPT09ICd2ZXJnaScpIHsKICAgIHlvbCA9IGtvayArICd2ZXJnaSc7CiAgICBn'
        'b3ZkZSA9IHthZDogX2RlZ2VyKCdrQWQnKS50cmltKCksIG1hdHJhaF90aXBpOiBfZGVn'
        'ZXIoJ2tNYXRyYWgnKSwKICAgICAgICAgICAgIG9yYW46IHBhcnNlRmxvYXQoX2RlZ2Vy'
        'KCdrT3JhbicpKSB8fCAwLAogICAgICAgICAgICAgdHV0YXI6IHBhcnNlRmxvYXQoX2Rl'
        'Z2VyKCdrVHV0YXInKSkgfHwgMCwKICAgICAgICAgICAgIGR1cnVtOiBfZGVnZXIoJ2tE'
        'dXJ1bScpLCBvZGVtZV90YXJpaGk6IF9kZWdlcigna1RhcmloJykgfHwgbnVsbH07CiAg'
        'ICBpZiAoIWdvdmRlLmFkKSB7IGJpbGRpcignVmVyZ2kgYWTEsSB6b3J1bmx1JywgdHJ1'
        'ZSk7IHJldHVybjsgfQogIH0gZWxzZSBpZiAoS0FMRU1fVElQID09PSAnc2VybWF5ZScp'
        'IHsKICAgIHlvbCA9IGtvayArICdzZXJtYXllJzsKICAgIGdvdmRlID0ge3RhcmFmOiBf'
        'ZGVnZXIoJ2tUYXJhZicpLCB5b246IF9kZWdlcigna1lvbicpLAogICAgICAgICAgICAg'
        'dHV0YXI6IHBhcnNlRmxvYXQoX2RlZ2VyKCdrVHV0YXInKSkgfHwgMCwKICAgICAgICAg'
        'ICAgIHRhcmloOiBfZGVnZXIoJ2tUYXJpaCcpIHx8IG51bGwsIGFjaWtsYW1hOiBfZGVn'
        'ZXIoJ2tBY2lrbGFtYScpfTsKICB9IGVsc2UgewogICAgeW9sID0ga29rICsgJ2RhZ2l0'
        'aW0nOwogICAgZ292ZGUgPSB7dGFyYWY6IF9kZWdlcigna1RhcmFmJyksIHR1dGFyOiBw'
        'YXJzZUZsb2F0KF9kZWdlcigna1R1dGFyJykpIHx8IDAsCiAgICAgICAgICAgICB0YXJp'
        'aDogX2RlZ2VyKCdrVGFyaWgnKSB8fCBudWxsLCBhY2lrbGFtYTogX2RlZ2VyKCdrQWNp'
        'a2xhbWEnKX07CiAgfQogIHRyeSB7IGF3YWl0IGFwaSh5b2wsIHttZXRob2Q6ICdQT1NU'
        'JywgYm9keTogSlNPTi5zdHJpbmdpZnkoZ292ZGUpfSk7IH0KICBjYXRjaCAoZSkgeyBi'
        'aWxkaXIoZS5tZXNzYWdlIHx8ICdFa2xlbmVtZWRpJywgdHJ1ZSk7IHJldHVybjsgfQog'
        'IGthbGVtS2FwYXQoKTsKICBkZXRheUFjKEFDSUsuaWQpOwogIHl1a2xlKCk7Cn0KCmFz'
        'eW5jIGZ1bmN0aW9uIF9rYWxlbVNpbCh5b2wsIHNvcnUpIHsKICBpZiAoIUFDSUspIHJl'
        'dHVybjsKICBpZiAoIWF3YWl0IG9uYXlsYShzb3J1LCB7dGVobGlrZTogdHJ1ZX0pKSBy'
        'ZXR1cm47CiAgdHJ5IHsKICAgIGF3YWl0IGFwaSgnL2FwaS9vcnRha2xpay8nICsgZW5j'
        'b2RlVVJJQ29tcG9uZW50KEFDSUsuaWQpICsgeW9sLAogICAgICAgICAgICAgIHttZXRo'
        'b2Q6ICdERUxFVEUnfSk7CiAgfSBjYXRjaCAoZSkgeyBiaWxkaXIoZS5tZXNzYWdlIHx8'
        'ICdTaWxpbmVtZWRpJywgdHJ1ZSk7IHJldHVybjsgfQogIGRldGF5QWMoQUNJSy5pZCk7'
        'IHl1a2xlKCk7Cn0KCmNvbnN0IGlzU2lsID0gaWQgPT4gX2thbGVtU2lsKCcvaXMvJyAr'
        'IGlkLCAnQnUgacWfaW4gYmHEn8SxIMOnw7Z6w7xsZWNlay4gRGV2YW0/Jyk7CmNvbnN0'
        'IHZlcmdpU2lsID0gaWQgPT4gX2thbGVtU2lsKCcvdmVyZ2kvJyArIGlkLCAnVmVyZ2kg'
        'a2FsZW1pIHNpbGluZWNlay4gRGV2YW0/Jyk7CmNvbnN0IHNlcm1heWVTaWwgPSBpZCA9'
        'PiBfa2FsZW1TaWwoJy9zZXJtYXllLycgKyBpZCwgJ1Nlcm1heWUgaGFyZWtldGkgc2ls'
        'aW5lY2VrLiBEZXZhbT8nKTsKY29uc3QgZGFnaXRpbVNpbCA9IGlkID0+IF9rYWxlbVNp'
        'bCgnL2RhZ2l0aW0vJyArIGlkLCAnRGHEn8SxdMSxbSBzaWxpbmVjZWsuIERldmFtPycp'
        'OwoKYXN5bmMgZnVuY3Rpb24gY2FyaXllSXNsZShpZCkgewogIGlmICghQUNJSykgcmV0'
        'dXJuOwogIHRyeSB7CiAgICBhd2FpdCBhcGkoYC9hcGkvb3J0YWtsaWsvJHtlbmNvZGVV'
        'UklDb21wb25lbnQoQUNJSy5pZCl9L2RhZ2l0aW0vJHtpZH0vY2FyaXllYCwKICAgICAg'
        'ICAgICAgICB7bWV0aG9kOiAnUE9TVCd9KTsKICB9IGNhdGNoIChlKSB7IGJpbGRpcihl'
        'Lm1lc3NhZ2UgfHwgJ8SwxZ9sZW5lbWVkaScsIHRydWUpOyByZXR1cm47IH0KICBiaWxk'
        'aXIoJ0Nhcml5ZSBpxZ9sZW5kaScpOwogIGRldGF5QWMoQUNJSy5pZCk7Cn0KCmFzeW5j'
        'IGZ1bmN0aW9uIGNhcml5ZUdlcmlBbChpZCkgewogIGlmICghQUNJSykgcmV0dXJuOwog'
        'IGlmICghYXdhaXQgb25heWxhKCdDYXJpIGhhcmVrZXRpIHNpbGluZWNlaywgZGHEn8Sx'
        'dMSxbSBrYXlkxLEga2FsYWNhay5cblxuRGV2YW0/JywKICAgICAgICAgICAgICAgICAg'
        'ICB7dGVobGlrZTogdHJ1ZX0pKSByZXR1cm47CiAgdHJ5IHsKICAgIGF3YWl0IGFwaShg'
        'L2FwaS9vcnRha2xpay8ke2VuY29kZVVSSUNvbXBvbmVudChBQ0lLLmlkKX0vZGFnaXRp'
        'bS8ke2lkfS9jYXJpeWVgLAogICAgICAgICAgICAgIHttZXRob2Q6ICdERUxFVEUnfSk7'
        'CiAgfSBjYXRjaCAoZSkgeyBiaWxkaXIoZS5tZXNzYWdlIHx8ICdHZXJpIGFsxLFuYW1h'
        'ZMSxJywgdHJ1ZSk7IHJldHVybjsgfQogIGJpbGRpcignR2VyaSBhbMSxbmTEsScpOwog'
        'IGRldGF5QWMoQUNJSy5pZCk7Cn0KCnl1a2xlKCk7Cjwvc2NyaXB0Pgp7JSBlbmRibG9j'
        'ayAlfQo='
    ),
}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA OR1 — IS ORTAKLIKLARI (KAR PAYLASIMI)')
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
        print('    python3 yama_or1.py            # rapor')
        print('    python3 yama_or1.py --uygula')
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
        print('  ⊙ Yama OR1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_or1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_or1'
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
    print('  ══ SIRA ONEMLI ══')
    print()
    print('    1) sudo systemctl restart milestone-erp')
    print('       BES YENI TABLO bu adimda kuruluyor. Once yeniden')
    print('       baslatmadan sayfayi acarsan hata alirsin.')
    print()
    print('    2) Tarayicida Ctrl+F5')
    print()
    print('    3) venv/bin/python -m pytest tests/test_kritik.py -q')
    print()
    print('  NEREDE')
    print('    Analiz -> Is Ortakliklari')
    print()
    print('  GOC YOK, mevcut veriye dokunulmadi.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

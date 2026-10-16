#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MF1 — ÇOKLU FİRMA, 1/4: ŞEMA
==================================

Bu, dört adımlık işin BİRİNCİSİ. Tek başına uygulandığında sistem
aynen bugünkü gibi çalışmaya devam eder — yalnızca veri modeli çoklu
firmaya hazır hale gelir. Süzgeç, arayüz ve sıfırlama modları sonraki
adımlarda.

    MF1  şema          ← buradasın
    MF2  küresel süzgeç
    MF3  arayüz (firma seçici)
    MF4  sıfırlama modları + sızıntı testleri

NE EKLENİYOR
------------
1) `firma` tablosu — yönetilen tüzel kişilikler. Unvan, vergi no,
   adres, logo ve BELGE KODU.

2) `cari_firma` tablosu — hangi carinin hangi firmada GÖRÜNDÜĞÜ.
   Cari kartı ORTAK kalır (aynı müşteri iki firmayla da çalışabilir,
   vergi no ve kişiler tek yerde durur) ama yalnızca bağlandığı
   firmalarda listelenir. Firmaların kendi müşterileri birbirinde
   görünmez.

3) `FirmaKapsamli` mixin — 28 işlem tablosuna `firma_id` ekler:
   stok (blok/plaka/ebatlı/çıkış), sipariş + kalem + karşılama,
   rezervasyon, proforma + kalem, fatura, satış kaydı, sevkiyat,
   konteyner, kesim + detay, maliyet, çek + hareket, kasa + hareket,
   banka, cari hareket, KDV iade, sabit gider, nakit planı,
   cari aktivite, bildirimler.

4) `veriler.firma_id` (NULL olabilir) — NULL ise ortak liste
   (cins, yüzey, ülke); dolu ise o firmaya ait ayar (logo, unvan,
   SMTP, KDV oranı).

5) Yazarken DAMGA — flush öncesi tek kanca, yeni kayıtlara firma_id
   basar. Şemayla aynı yamada olmak zorunda: damgasız zorunlu sütun
   bütün yazma yollarını kırıyor (ölçüldü: 81 testin 81'i).

6) `audit_log.firma_id` (NULL olabilir, BİLGİ amaçlı) — denetim izi
   süzülmez; admin bütün firmaların hareketini görebilmeli ve giriş
   gibi firma öncesi olaylar da buraya düşer.

ORTAK KALANLAR (firma_id ALMAZ)
-------------------------------
  kullanicilar   kullanıcı bir kişi; hangi firmalarda çalışabildiği
                 MF3'te ayrı tutulacak
  doviz_kur      TCMB arşivi — firmaya göre değişmez
  cariler        kart ortak, görünürlük cari_firma üzerinden
  cari_kisi      cari kartının parçası
  cari_erisim    kullanıcı × cari istisnası

BELGE NUMARALARI
----------------
Her firmanın kendi sayacı olacak, yani ikisi de 01'den başlayacak.
Kimlik sütunu birincil anahtar olduğu için çakışmayı önleyen bir
ayraç gerekiyor: `firma.belge_kodu`. ANA firmada BOŞ bırakılır ki
mevcut kimlikler (SIP-STN26-03) olduğu gibi kalsın ve 30'a yakın
yabancı anahtar taşınmasın. İkinci firma kod alır: SIP-K-STN26-01.
Kodu kullanan kimlik üreteci MF3'te değişecek.

BU YAMA VERİ YAZMAZ
-------------------
Yalnızca models.py'yi değiştirir. Tabloların oluşturulması ve mevcut
verinin 1 numaralı firmaya damgalanması AYRI bir göç betiğiyle
yapılır (goc_mf1.py — bu yamayla birlikte geliyor).

KULLANIM
--------
  python3 yama_mf1.py            # RAPOR — hiçbir dosyaya dokunmaz
  python3 yama_mf1.py --uygula   # uygular, yanına .yedek_mf1 bırakır

  SONRA (sırayla):
  venv/bin/python goc_mf1.py              # rapor
  venv/bin/python goc_mf1.py --uygula     # tabloları kurar, damgalar
"""

import os
import sys
import shutil
import py_compile
import tempfile

UYGULA = '--uygula' in sys.argv
IMZA = 'MF1'
KOK = os.path.dirname(os.path.abspath(__file__))


# ── Firma kapsamına girecek 28 model ──
# Sıra önemsiz; her biri `class X(db.Model):` → `class X(FirmaKapsamli, db.Model):`
KAPSAMLI = [
    # stok
    'BlokStok', 'PlakaStok', 'EbatliStok', 'StokCikis',
    # satış zinciri
    'Siparis', 'SiparisKalem', 'KalemKarsilama', 'Rezervasyon',
    'Proforma', 'ProformaKalem', 'Fatura', 'SatisKaydi',
    # sevkiyat
    'Sevkiyat', 'Konteyner',
    # üretim
    'Kesim', 'KesimDetay',
    # finans
    'Maliyet', 'Cek', 'CekHareket', 'Banka', 'Kasa', 'KasaHareket',
    'CariHareket', 'KdvIadeDosya', 'SabitGider', 'NakitPlan',
    # diğer
    'CariAktivite', 'Bildirim',
]


YENI_TABLOLAR = '''# ══════════════════════════════════════════════════════════════════════
#  ÇOKLU FİRMA  (MF1)
# ══════════════════════════════════════════════════════════════════════
# Sistem tek firmayı yönetmek üzere yazılmıştı. Artık birden çok tüzel
# kişilik taşıyor; her birinin stoğu, siparişi, kasası ve defteri AYRI.
#
# ── NEDEN SÜTUN, NEDEN AYRI VERİTABANI DEĞİL ──
#   Ayrı veritabanı en güvenli yol olurdu ama ortak olması gereken
#   şeyleri (TCMB kur arşivi, kullanıcılar, cari kartları) ikizlerdi ve
#   her göçü firma sayısı kadar çalıştırmak gerekirdi. Tek veritabanı +
#   `firma_id` + KÜRESEL SÜZGEÇ seçildi: süzgeç tek yerde durur ve
#   699 sorgunun hiçbirine dokunulmaz.
#
# ── ÜÇ SINIF TABLO ──
#   1. FirmaKapsamli taşıyanlar → firma_id ZORUNLU, süzgeç uygulanır
#   2. Ortak tablolar           → kullanicilar, doviz_kur, cariler,
#                                 cari_kisi, cari_erisim
#   3. Özel                     → veriler   (NULL=ortak liste)
#                                 audit_log (bilgi amaçlı, süzülmez)

class Firma(db.Model):
    """Sistemin yönettiği tüzel kişilikler."""
    __tablename__ = 'firma'
    id            = db.Column(db.Integer, primary_key=True)
    ad            = db.Column(db.String(100), nullable=False)   # ekranda
    unvan         = db.Column(db.String(200))                   # belgede
    # ── BELGE KODU — kimliklere girer: SIP-K-STN26-03 ──
    # Her firmanın kendi sayacı olsun isteniyor, yani ikisi de 01'den
    # başlıyor. Kimlik sütunu birincil anahtar olduğu için çakışmayı
    # önleyen bir ayraç gerekiyor; kod o ayraç.
    #
    # ANA firmada BOŞ bırakılır: mevcut kimlikler (SIP-STN26-03) olduğu
    # gibi kalsın, 30'a yakın yabancı anahtar taşınmasın. İkinci ve
    # sonraki firmalar kod almak ZORUNDA — kodsuz ikinci firma ana
    # firmayla numara çakıştırırdı.
    belge_kodu    = db.Column(db.String(4))
    vergi_dairesi = db.Column(db.String(100))
    vergi_no      = db.Column(db.String(20))
    adres         = db.Column(db.Text)
    telefon       = db.Column(db.String(30))
    eposta        = db.Column(db.String(100))
    web           = db.Column(db.String(120))
    logo          = db.Column(db.Text)                          # base64
    # Admin olmayan kullanıcının çalıştığı firma; firma seçici
    # kapalıyken sistem buraya düşer.
    varsayilan    = db.Column(db.Boolean, default=False, index=True)
    aktif         = db.Column(db.Boolean, default=True, index=True)
    sira          = db.Column(db.Integer, default=0)
    olusturma     = db.Column(db.DateTime, default=datetime.now)


class CariFirma(db.Model):
    """Hangi cari HANGİ FİRMADA görünür.

    Cari kartı ORTAK: aynı müşteri iki firmayla da çalışabilir ve
    vergi no, adres, kişiler tek yerde durur. Ama firmaların kendi
    müşterileri de var ve onlar diğerinde GÖRÜNMEMELİ. Bunu kartı
    ikizlemeden çözen şey üyelik: cari yalnızca bağlandığı firmalarda
    listelenir.

    Hareketler, bakiye ve risk limiti zaten `cari_hareket` üzerinden
    firma bazlı — bu tablo yalnızca GÖRÜNÜRLÜĞÜ belirler.
    """
    __tablename__ = 'cari_firma'
    id        = db.Column(db.Integer, primary_key=True)
    cari_id   = db.Column(db.String(20), db.ForeignKey('cariler.id'),
                          nullable=False, index=True)
    firma_id  = db.Column(db.Integer, db.ForeignKey('firma.id'),
                          nullable=False, index=True)
    olusturma = db.Column(db.DateTime, default=datetime.now)
    __table_args__ = (db.UniqueConstraint('cari_id', 'firma_id',
                                          name='uq_cari_firma'),)


class FirmaKapsamli:
    """Bu mixin'i alan tablo FİRMA KAPSAMINDADIR.

    Tek işlevi `firma_id` sütununu eklemek; süzgeci uygulayan kanca
    (MF2) TİPİ bu sınıfa bakarak tanır. Yeni bir model eklerken
    mixin'i yazmayı unutmak o tablonun SÜZÜLMEMESİ demektir — bu
    yüzden hem sifirla2.py hem denetim betiği her tablonun kapsamlı ya
    da ortak olarak AÇIKÇA sınıflandırıldığını doğrular.
    """
    @declared_attr
    def firma_id(cls):
        return db.Column(db.Integer, db.ForeignKey('firma.id'),
                         index=True, nullable=False)


'''

DAMGA_BLOK = '\n\n# ══════════════════════════════════════════════════════════════════════\n#  ÇOKLU FİRMA — YAZARKEN DAMGA  (MF1)\n# ══════════════════════════════════════════════════════════════════════\n# firma_id ZORUNLU bir sütun. Onu her INSERT\'te elle yazmak 300\'ü aşkın\n# noktaya dokunmak demekti; bunun yerine flush öncesi tek bir kanca\n# damgayı basıyor.\n#\n# KANCA ŞEMAYLA AYNI YAMADA OLMAK ZORUNDA: ölçüldü, kancasız şema\n# bütün yazma yollarını kırıyor ("NOT NULL constraint failed:\n# blok_stok.firma_id" — 81 testin 81\'i).\n#\n# OKUMA SÜZGECİ burada DEĞİL (MF2 ile gelecek). Bu yama uygulandığında\n# sistem bugünküyle birebir aynı davranır: tek firma, her şey ona\n# damgalı.\n\n_firma_cozucu = None               # MF2/MF3: oturumdaki aktif firmayı verir\n_varsayilan_firma_onbellek = None\n\n\ndef firma_cozucu_ayarla(fn):\n    """Aktif firmayı veren işleyiciyi takar (flask_app tarafı, MF2)."""\n    global _firma_cozucu\n    _firma_cozucu = fn\n\n\ndef varsayilan_firma_unut():\n    """Firma kaydı eklenip değişince önbelleği düşürür."""\n    global _varsayilan_firma_onbellek\n    _varsayilan_firma_onbellek = None\n\n\ndef _varsayilan_firma_id():\n    """Varsayılan firmanın kimliği.\n\n    HAM SQL kullanır: before_flush içinde ORM sorgusu açmak aynı\n    oturuma yeniden girmek demek olurdu.\n\n    `ORDER BY varsayilan DESC` iki lehçede de çalışır (PostgreSQL\'de\n    TRUE, SQLite\'ta 1 önce gelir); `WHERE varsayilan = 1` SQLite\'a,\n    `WHERE varsayilan` PostgreSQL\'e özgü olurdu.\n    """\n    global _varsayilan_firma_onbellek\n    if _varsayilan_firma_onbellek is not None:\n        return _varsayilan_firma_onbellek\n    try:\n        with db.engine.connect() as b:\n            r = b.execute(_text(\n                \'SELECT id FROM firma ORDER BY varsayilan DESC, id \'\n                \'LIMIT 1\')).fetchone()\n        if r is None:\n            # ── BOŞ KURULUM KENDİNİ ONARIR ──\n            # Taze veritabanında (yeni kurulum, testler) firma tablosu\n            # boştur ve damga basacak kimlik bulunamaz; o hâlde HİÇBİR\n            # kayıt yazılamaz. Ölçüldü: 81 testin 81\'i\n            # "RuntimeError: Aktif firma yok" veriyordu.\n            # Burada bir ANA FİRMA açılır; göç betiği adını, unvanını ve\n            # logosunu Ayarlar\'dan okuyup ÜSTÜNE yazar.\n            with db.engine.begin() as b:\n                b.execute(_text(\n                    \'INSERT INTO firma (ad, unvan, varsayilan, aktif, sira)\'\n                    " VALUES (\'ANA FİRMA\', \'ANA FİRMA\', :e, :e, 0)"),\n                    {\'e\': True})\n                r = b.execute(_text(\n                    \'SELECT id FROM firma ORDER BY id LIMIT 1\')).fetchone()\n    except Exception:\n        return None                # firma tablosu henüz yok (göç öncesi)\n    _varsayilan_firma_onbellek = r[0] if r else None\n    return _varsayilan_firma_onbellek\n\n\ndef aktif_firma_id():\n    """Şu an hangi firmada çalışılıyor."""\n    if _firma_cozucu is not None:\n        try:\n            v = _firma_cozucu()\n        except Exception:\n            v = None\n        if v:\n            return v\n    return _varsayilan_firma_id()\n\n\ndef _firma_damgasi(oturum, baglam, ornekler):\n    """Yeni kayıtlara firma_id basar."""\n    fid = None\n    for n in oturum.new:\n        if isinstance(n, Veriler):\n            # Ortak referans listeleri (cins, yüzey, ülke) firmasız\n            # kalır. Firmaya özel AYAR satırını yazan yer firma_id\'yi\n            # kendisi verir.\n            continue\n        if not isinstance(n, (FirmaKapsamli, AuditLog)):\n            continue\n        if getattr(n, \'firma_id\', None) is not None:\n            continue\n        if fid is None:\n            fid = aktif_firma_id()\n        if fid is None:\n            if isinstance(n, AuditLog):\n                continue       # denetim izi firmasız da yazılabilir\n            raise RuntimeError(\n                \'Aktif firma yok — firma tanımlanmadan kayıt yazılamaz. \'\n                \'goc_mf1.py çalıştırıldı mı?\')\n        n.firma_id = fid\n\n\n_event.listen(db.session, \'before_flush\', _firma_damgasi)\n'


def degisiklikleri_kur():
    d = [
        ('MF1-a · declared_attr içe aktarımı',
         "from flask_sqlalchemy import SQLAlchemy\n"
         "from datetime import datetime, date",
         "from flask_sqlalchemy import SQLAlchemy\n"
         "from sqlalchemy.orm import declared_attr   # MF1\n"
         "from datetime import datetime, date"),
        ('MF1-b · Firma / CariFirma / FirmaKapsamli tanımları',
         "class Kullanici(db.Model):",
         YENI_TABLOLAR + "class Kullanici(db.Model):"),
    ]
    for i, ad in enumerate(KAPSAMLI, 1):
        d.append((f'MF1-{i:02d} · {ad}',
                  f"class {ad}(db.Model):",
                  f"class {ad}(FirmaKapsamli, db.Model):"))
    d.append((
        'MF1-y · audit_log.firma_id (bilgi amaçlı, süzülmez)',
        "class AuditLog(db.Model):\n    __tablename__ = 'audit_log'",
        "class AuditLog(db.Model):\n    __tablename__ = 'audit_log'\n"
        "    # MF1: hangi firmada yapıldı — BİLGİ amaçlı. Denetim izi\n"
        "    # SÜZÜLMEZ: admin bütün firmaların hareketini görebilmeli,\n"
        "    # ayrıca giriş gibi firma öncesi olaylar da buraya düşer\n"
        "    # (o satırlarda NULL kalır).\n"
        "    firma_id    = db.Column(db.Integer, db.ForeignKey('firma.id'),\n"
        "                            index=True, nullable=True)"))
    d.append((
        'MF1-x · yazarken firma damgasi (before_flush kancasi)',
        "_event.listen(Siparis, 'before_insert', siparis_durum_damgasi_yeni)\n"
        "_event.listen(Siparis, 'before_update', siparis_durum_damgasi)",
        "_event.listen(Siparis, 'before_insert', siparis_durum_damgasi_yeni)\n"
        "_event.listen(Siparis, 'before_update', siparis_durum_damgasi)\n"
        + DAMGA_BLOK))
    d.append((
        'MF1-z · veriler.firma_id (NULL = ortak liste)',
        "    uzun_deger  = db.Column(db.Text)",
        "    uzun_deger  = db.Column(db.Text)\n"
        "    # MF1: NULL ise ORTAK (cins, yüzey, ülke, ödeme listeleri —\n"
        "    # hepsi her firmada aynı). Dolu ise O FİRMAYA ait ayar:\n"
        "    # logo, unvan, SMTP, KDV oranı. Böylece referans listeleri\n"
        "    # ikizlemeden firma başına kimlik tutulabiliyor.\n"
        "    firma_id    = db.Column(db.Integer, db.ForeignKey('firma.id'),\n"
        "                            index=True, nullable=True)"))
    return d


def main():
    print('=' * 70)
    print(f'  YAMA {IMZA} — ÇOKLU FİRMA 1/4: ŞEMA')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    yol = os.path.join(KOK, 'models.py')
    print('\n── models.py ' + '─' * 50)
    if not os.path.exists(yol):
        print(f'  ✗ DOSYA YOK: {yol}')
        return 1

    with open(yol, 'rb') as f:
        ham = f.read()
    crlf = b'\r\n' in ham
    icerik = ham.decode('utf-8')
    if crlf:
        icerik = icerik.replace('\r\n', '\n')
        print('  · CRLF satır sonu algılandı, korunacak')

    if IMZA in icerik:
        print(f'  ⊙ İmza "{IMZA}" zaten var — yama uygulanmış. İş yok.')
        return 0

    yeni, hata = icerik, False
    kapsamli_ok = 0
    for aciklama, eski, yerine in degisiklikleri_kur():
        n = yeni.count(eski)
        if n != 1:
            print(f'  ✗ {aciklama}')
            print(f'     kalıp {n} kez eşleşti (tam 1 olmalı)')
            hata = True
            continue
        yeni = yeni.replace(eski, yerine, 1)
        if aciklama.startswith('MF1-') and aciklama[4:6].isdigit():
            kapsamli_ok += 1
        else:
            print(f'  ✓ {aciklama}')
    print(f'  ✓ {kapsamli_ok} tablo firma kapsamına alındı')

    if hata:
        print('\n' + '=' * 70)
        print('  ✗ HATA VAR → Dosyaya DOKUNULMADI')
        return 1

    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False,
                                     encoding='utf-8') as tf:
        tf.write(yeni)
        gec = tf.name
    try:
        py_compile.compile(gec, doraise=True, cfile=gec + 'c')
        print('  ✓ söz dizimi doğrulandı (py_compile)')
    except py_compile.PyCompileError as e:
        print(f'  ✗ SÖZDİZİMİ HATASI:\n{e}')
        return 1
    finally:
        for p in (gec, gec + 'c'):
            if os.path.exists(p):
                os.unlink(p)

    print('\n' + '=' * 70)
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_mf1.py --uygula')
        print('=' * 70)
        return 0

    yedek = yol + '.yedek_mf1'
    shutil.copy2(yol, yedek)
    with open(yol, 'w', encoding='utf-8', newline='') as f:
        f.write(yeni.replace('\n', '\r\n') if crlf else yeni)
    print(f'  ✓ yazıldı: models.py')
    print(f'    yedek  : models.py.yedek_mf1')
    print()
    print('  ✓ YAMA UYGULANDI — ama VERİTABANI HENÜZ DEĞİŞMEDİ.')
    print()
    print('  ⚠ Servisi ŞİMDİ yeniden başlatma: model yeni sütunları')
    print('    bekliyor, tablolar ise eski. Önce göçü çalıştır:')
    print()
    print('      venv/bin/python goc_mf1.py            # rapor')
    print('      venv/bin/python goc_mf1.py --uygula   # kurar ve damgalar')
    print('      sudo systemctl restart milestone-erp')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

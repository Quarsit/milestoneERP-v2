#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — ÇOKLU FİRMA GÖÇÜ  ·  MF1
#
#  ÖNKOŞUL: yama_mf1.py uygulanmış olmalı (models.py'de MF1 imzası).
#
#  NE YAPAR
#    1) `firma` ve `cari_firma` tablolarını kurar
#    2) Eksik `firma_id` sütunlarını ekler (30 tablo)
#    3) ANA FİRMA'yı oluşturur — adı, unvanı, adresi ve LOGOSU mevcut
#       Ayarlar → Firma kaydından alınır. Belge kodu BOŞ bırakılır ki
#       eldeki kimlikler (SIP-STN26-03) olduğu gibi kalsın.
#    4) Bütün mevcut kayıtları ana firmaya damgalar
#    5) Bütün carileri ana firmaya bağlar (görünürlük üyeliği)
#    6) Sütunları NOT NULL'a çeker — firmasız satır yazılamasın
#
#  NEDEN NOT NULL ÖNEMLİ
#    firma_id'si NULL kalan bir satır HİÇBİR firmada görünmez: ne A'da
#    ne B'de. Sessizce kaybolur. Süzgeç (MF2) zaten yazarken damga
#    basıyor ama veritabanı seviyesinde de kapatmak, betikle ya da elle
#    yazılan satırları da kapsar.
#
#  GÜVENLİK
#    • --uygula OLMADAN HİÇBİR ŞEY DEĞİŞMEZ; yalnızca rapor verir.
#    • PostgreSQL'de önce pg_dump yedeği alır; yedek başarısızsa İPTAL.
#    • Tekrar çalıştırılabilir (idempotent): ikinci koşu "yapılacak iş
#      yok" der, ikinci firma OLUŞTURMAZ.
#
#  KULLANIM (proje dizininde):
#      venv/bin/python goc_mf1.py             # RAPOR
#      venv/bin/python goc_mf1.py --uygula    # UYGULAR
#      venv/bin/python goc_mf1.py --uygula --ad "MILESTONE MERMER"
# ══════════════════════════════════════════════════════════════════════
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

UYGULA = '--uygula' in sys.argv
AD_PARAM = None
for _i, _a in enumerate(sys.argv):
    if _a == '--ad' and _i + 1 < len(sys.argv):
        AD_PARAM = sys.argv[_i + 1]

VT_URL = os.environ.get('DATABASE_URL')
if not VT_URL:
    print('HATA: DATABASE_URL bulunamadı (.env okunamadı).')
    sys.exit(1)

sys.path.insert(0, os.getcwd())
os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')

import flask_app as fa                                    # noqa: E402
from models import db, Firma, CariFirma, Cari, Veriler, FirmaKapsamli  # noqa: E402
from sqlalchemy import inspect as sa_inspect, text as sa_text          # noqa: E402

CIZGI = '─' * 70

# `veriler` tablosunda FİRMAYA ÖZEL olan kategoriler. Gerisi (cins,
# yüzey, ülke, ödeme şekli…) ORTAK referans listesidir ve firma_id'si
# NULL kalır — her firmada aynı listeler görünür.
FIRMAYA_OZEL_AYAR = ('firma', 'firma_logo', 'smtp')


def ana_firma_bilgisi():
    """Ayarlar → Firma kaydından ana firmanın bilgilerini toplar.

    HAM SQL kullanır, ORM değil: rapor modunda `veriler.firma_id`
    sütunu HENÜZ YOKTUR ve ORM onu SELECT'e koyup "no such column"
    verir. Göçü anlatması gereken betik, anlattığı göç yapılmadığı
    için çalışamazdı.
    """
    bilgi = {'ad': AD_PARAM or '', 'unvan': '', 'adres': '',
             'telefon': '', 'eposta': '', 'logo': None}
    with db.engine.connect() as b:
        r = b.execute(sa_text(
            "SELECT deger, kisaltma, uzun_deger FROM veriler "
            "WHERE kategori = 'firma' LIMIT 1")).fetchone()
        if r:
            bilgi['unvan'] = r[0] or ''
            if not bilgi['ad']:
                bilgi['ad'] = (r[1] or r[0] or '')[:100]
            try:
                ek = json.loads(r[2] or '{}') or {}
            except Exception:
                ek = {}
            bilgi['adres'] = ek.get('adres', '')
            bilgi['telefon'] = ek.get('tel', '')
            bilgi['eposta'] = ek.get('email', '')
        r = b.execute(sa_text(
            "SELECT uzun_deger FROM veriler "
            "WHERE kategori = 'firma_logo' AND deger = 'logo' "
            "LIMIT 1")).fetchone()
        if r:
            bilgi['logo'] = r[0]
    if not bilgi['ad']:
        bilgi['ad'] = 'ANA FİRMA'
    if not bilgi['unvan']:
        bilgi['unvan'] = bilgi['ad']
    return bilgi


def kapsamli_tablolar():
    """firma_id taşıyan tablolar; (tablo, zorunlu_mu)."""
    zorunlu = {c.__tablename__ for c in db.Model.__subclasses__()
               if issubclass(c, FirmaKapsamli)}
    hepsi = []
    for ad, t in sorted(db.metadata.tables.items()):
        if ad in ('firma', 'cari_firma'):
            continue
        if 'firma_id' in t.c:
            hepsi.append((ad, ad in zorunlu))
    return hepsi


def yedek_al(pg, kaynak):
    if not pg:
        print(' ⚠ PostgreSQL değil — otomatik yedek atlandı.')
        return True
    hedef = Path.home() / 'yedekler'
    hedef.mkdir(exist_ok=True)
    dosya = hedef / f'mf1-oncesi-{datetime.now():%Y%m%d_%H%M%S}.dump'
    try:
        ortam = dict(os.environ)
        if kaynak.password:
            ortam['PGPASSWORD'] = kaynak.password
        s = subprocess.run(
            ['pg_dump', '-Fc', '-f', str(dosya),
             '-h', kaynak.hostname or 'localhost',
             '-p', str(kaynak.port or 5432),
             '-U', kaynak.username or 'postgres',
             kaynak.path.lstrip('/')],
            env=ortam, capture_output=True, text=True, timeout=600)
        if s.returncode != 0 or not dosya.exists() or dosya.stat().st_size < 1024:
            print(' ✗ Yedek ALINAMADI — göç İPTAL edildi.')
            print(f'   {(s.stderr or "").strip()[:200]}')
            return False
        print(f' ✓ {dosya}  ({dosya.stat().st_size / 1024:.0f} KB)')
        return True
    except FileNotFoundError:
        print(' ✗ pg_dump bulunamadı — göç İPTAL edildi.')
        return False
    except subprocess.TimeoutExpired:
        print(' ✗ Yedek zaman aşımına uğradı — göç İPTAL edildi.')
        return False


def main():
    kaynak = urlparse(VT_URL)
    print('═' * 70)
    print('  MILESTONE ERP — ÇOKLU FİRMA GÖÇÜ (MF1)')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (hiçbir şey değişmez)')
    print('═' * 70)
    print(f'  Veritabanı : {kaynak.path.lstrip("/")} @ {kaynak.hostname or "yerel"}')

    with fa.app.app_context():
        pg = db.engine.dialect.name in ('postgresql', 'postgres')
        print(f'  Sürücü     : {db.engine.dialect.name}')

        # ── ÖNKOŞUL ──
        import models as _m
        if not hasattr(_m, 'Firma'):
            print('\n ✗ models.py MF1 yamasını taşımıyor.')
            print('   Önce: python3 yama_mf1.py --uygula')
            return 1

        mufettis = sa_inspect(db.engine)
        mevcut_tablolar = set(mufettis.get_table_names())
        yeni_tablo = [t for t in ('firma', 'cari_firma')
                      if t not in mevcut_tablolar]

        kapsam = kapsamli_tablolar()
        eksik_sutun = []
        for ad, _z in kapsam:
            if ad not in mevcut_tablolar:
                continue
            if 'firma_id' not in {s['name'] for s in mufettis.get_columns(ad)}:
                eksik_sutun.append(ad)

        print()
        print(CIZGI)
        print(' ŞEMA')
        print(CIZGI)
        print(f'   kurulacak tablo   : {", ".join(yeni_tablo) or "yok (zaten var)"}')
        print(f'   firma_id eklenecek: {len(eksik_sutun)} tablo'
              + (f'  ({", ".join(eksik_sutun[:6])}'
                 + (' …' if len(eksik_sutun) > 6 else '') + ')'
                 if eksik_sutun else ''))
        print(f'   firma kapsamı     : {len(kapsam)} tablo'
              f'  ({sum(1 for _, z in kapsam if z)} zorunlu,'
              f' {sum(1 for _, z in kapsam if not z)} serbest)')

        # ── ANA FİRMA ──
        var_olan = []
        if 'firma' in mevcut_tablolar:
            with db.engine.connect() as b:
                var_olan = b.execute(sa_text(
                    'SELECT id, ad, belge_kodu, varsayilan '
                    'FROM firma ORDER BY id')).fetchall()
        print()
        print(CIZGI)
        print(' ANA FİRMA')
        print(CIZGI)
        if var_olan:
            for fid, fad, fkod, fvar in var_olan:
                print(f'   #{fid}  {fad}   kod={fkod or "(yok)"}  '
                      f'{"VARSAYILAN" if fvar else ""}')
            print('   → firma kaydı zaten var, yenisi OLUŞTURULMAZ')
        else:
            b = ana_firma_bilgisi()
            print(f'   ad        : {b["ad"]}')
            print(f'   unvan     : {b["unvan"] or "(boş)"}')
            print(f'   adres     : {(b["adres"] or "(boş)")[:50]}')
            print(f'   telefon   : {b["telefon"] or "(boş)"}')
            print(f'   e-posta   : {b["eposta"] or "(boş)"}')
            print(f'   logo      : {"var" if b["logo"] else "yok"}')
            print(f'   belge kodu: (boş — mevcut kimlikler korunsun diye)')
            print('   Ayarlar → Firma kaydından alındı. Yanlışsa --ad ile')
            print('   düzelt ya da göçten sonra Firma ekranından değiştir.')

        # ── DAMGALANACAK SATIRLAR ──
        print()
        print(CIZGI)
        print(' DAMGALANACAK KAYITLAR  (firma_id boş olanlar)')
        print(CIZGI)
        toplam, satirlar = 0, []
        with db.engine.connect() as b:
            for ad, zorunlu in kapsam:
                if ad not in mevcut_tablolar:
                    continue
                _sutun_var = 'firma_id' in {s['name']
                                            for s in mufettis.get_columns(ad)}
                if ad == 'veriler':
                    # Yalnızca firmaya özel ayar satırları damgalanır.
                    _k = "kategori IN :kk"
                    _sorgu = (f'SELECT COUNT(*) FROM "veriler" WHERE kategori IN '
                              f'({", ".join(repr(x) for x in FIRMAYA_OZEL_AYAR)})')
                    if _sutun_var:
                        _sorgu += ' AND firma_id IS NULL'
                    n = b.execute(sa_text(_sorgu)).scalar() or 0
                elif not _sutun_var:
                    n = b.execute(sa_text(f'SELECT COUNT(*) FROM "{ad}"')).scalar() or 0
                else:
                    n = b.execute(sa_text(
                        f'SELECT COUNT(*) FROM "{ad}" WHERE firma_id IS NULL')).scalar() or 0
                if n:
                    satirlar.append((ad, n, zorunlu))
                    toplam += n
        for ad, n, zorunlu in satirlar:
            print(f'   {ad:<20} {n:>8,}' + ('' if zorunlu else '   (serbest)'))
        if not satirlar:
            print('   (hepsi damgalı — yapılacak iş yok)')
        print(f'\n   TOPLAM {toplam:,} kayıt')

        # ── CARİ ÜYELİĞİ ──
        with db.engine.connect() as b:
            cari_n = b.execute(sa_text('SELECT COUNT(*) FROM cariler')).scalar() or 0
            bagli = (b.execute(sa_text('SELECT COUNT(*) FROM cari_firma')).scalar() or 0
                     ) if 'cari_firma' in mevcut_tablolar else 0
        print()
        print(CIZGI)
        print(' CARİ GÖRÜNÜRLÜK ÜYELİĞİ')
        print(CIZGI)
        print(f'   cari sayısı       : {cari_n:,}')
        print(f'   zaten bağlı       : {bagli:,}')
        print(f'   bağlanacak        : {max(0, cari_n - bagli):,}')
        print('   Hepsi ana firmaya bağlanır. İkinci firma açıldığında')
        print('   hangi carilerin orada da görüneceğini sen seçersin.')

        if not UYGULA:
            print()
            print('═' * 70)
            print('  RAPOR MODU — hiçbir şey değişmedi.')
            print()
            print('  Uygulamak için:')
            print('    venv/bin/python goc_mf1.py --uygula')
            print('═' * 70)
            return 0

        # ══ UYGULAMA ══
        print()
        print(CIZGI)
        print(' YEDEK')
        print(CIZGI)
        if not yedek_al(pg, kaynak):
            return 1

        print()
        print(CIZGI)
        print(' UYGULANIYOR')
        print(CIZGI)

        # 1 · tablolar ve sütunlar
        db.create_all()
        print('   ✓ tablolar kuruldu (firma, cari_firma)')
        mufettis = sa_inspect(db.engine)
        for ad, _z in kapsam:
            if ad not in set(mufettis.get_table_names()):
                continue
            if 'firma_id' in {s['name'] for s in mufettis.get_columns(ad)}:
                continue
            with db.engine.begin() as b:
                b.execute(sa_text(
                    f'ALTER TABLE "{ad}" ADD COLUMN firma_id INTEGER'))
            print(f'   ✓ {ad}.firma_id eklendi')

        # 2 · ana firma
        firma = Firma.query.order_by(Firma.id).first()
        if not firma:
            b = ana_firma_bilgisi()
            firma = Firma(ad=b['ad'], unvan=b['unvan'], adres=b['adres'],
                          telefon=b['telefon'], eposta=b['eposta'],
                          logo=b['logo'], belge_kodu=None,
                          varsayilan=True, aktif=True, sira=0)
            db.session.add(firma)
            db.session.commit()
            print(f'   ✓ ana firma oluşturuldu: #{firma.id} {firma.ad}')
        else:
            # Damga kancası (MF1) boş kurulumda kendi kendine bir
            # 'ANA FİRMA' açmış olabilir — kayıt yazılabilsin diye.
            # O yer tutucuysa Ayarlar'daki gerçek bilgiyle doldurulur;
            # elle düzenlenmiş bir firmaya DOKUNULMAZ.
            if (firma.ad or '').strip() in ('ANA FİRMA', 'ANA FIRMA'):
                b = ana_firma_bilgisi()
                firma.ad = b['ad']
                firma.unvan = b['unvan']
                firma.adres = firma.adres or b['adres']
                firma.telefon = firma.telefon or b['telefon']
                firma.eposta = firma.eposta or b['eposta']
                firma.logo = firma.logo or b['logo']
                print(f'   ✓ yer tutucu firma dolduruldu: #{firma.id} {firma.ad}')
            else:
                print(f'   ⊙ ana firma zaten var: #{firma.id} {firma.ad}')
            if not Firma.query.filter_by(varsayilan=True).first():
                firma.varsayilan = True
            db.session.commit()

        # 3 · damgalama
        damgalanan = 0
        with db.engine.begin() as b:
            for ad, _z in kapsam:
                if ad not in set(mufettis.get_table_names()):
                    continue
                if ad == 'veriler':
                    continue            # aşağıda, hedefli olarak
                s = b.execute(sa_text(
                    f'UPDATE "{ad}" SET firma_id = :f WHERE firma_id IS NULL'),
                    {'f': firma.id})
                n = getattr(s, 'rowcount', 0) or 0
                if n:
                    print(f'   ✓ {ad:<20} {n:>8,} kayıt damgalandı')
                    damgalanan += n

            # `veriler` AYRI: yalnızca firmaya özel ayarlar damgalanır.
            # Önce hepsini damgalayıp sonra geri almak çalışıyordu ama
            # ikinci koşuda "3 kayıt damgalanacak" diye yanıltıcı rapor
            # veriyordu — ortak satırlar her seferinde NULL'a dönüyordu.
            _liste = ', '.join(repr(x) for x in FIRMAYA_OZEL_AYAR)
            s = b.execute(sa_text(
                f'UPDATE veriler SET firma_id = :f '
                f'WHERE firma_id IS NULL AND kategori IN ({_liste})'),
                {'f': firma.id})
            n = getattr(s, 'rowcount', 0) or 0
            if n:
                print(f'   ✓ {"veriler":<20} {n:>8,} ayar damgalandı '
                      f'(ortak listeler NULL kaldı)')
                damgalanan += n

        # 4 · cari üyeliği
        eklendi = 0
        var = {c.cari_id for c in CariFirma.query.filter_by(firma_id=firma.id)}
        for c in Cari.query.all():
            if c.id in var:
                continue
            db.session.add(CariFirma(cari_id=c.id, firma_id=firma.id))
            eklendi += 1
        db.session.commit()
        print(f'   ✓ cari üyeliği       {eklendi:>8,} bağlantı')

        # 5 · NOT NULL
        print()
        if pg:
            cevrilen = 0
            for ad, zorunlu in kapsam:
                if not zorunlu or ad not in set(mufettis.get_table_names()):
                    continue
                try:
                    with db.engine.begin() as b:
                        b.execute(sa_text(
                            f'ALTER TABLE "{ad}" '
                            'ALTER COLUMN firma_id SET NOT NULL'))
                    cevrilen += 1
                except Exception as e:
                    print(f'   ⚠ {ad}: NOT NULL yapılamadı — {str(e)[:70]}')
            print(f'   ✓ {cevrilen} tabloda firma_id NOT NULL yapıldı')
        else:
            print('   ⚠ SQLite: ALTER COLUMN desteklenmiyor, NOT NULL atlandı.')
            print('     (Üretim PostgreSQL; orada uygulanır.)')

        # ── DOĞRULAMA ──
        print()
        print(CIZGI)
        print(' DOĞRULAMA')
        print(CIZGI)
        hatali = False
        mufettis = sa_inspect(db.engine)
        with db.engine.connect() as b:
            for ad, zorunlu in kapsam:
                if ad == 'veriler' or not zorunlu:
                    continue
                if ad not in set(mufettis.get_table_names()):
                    continue
                n = b.execute(sa_text(
                    f'SELECT COUNT(*) FROM "{ad}" WHERE firma_id IS NULL')).scalar() or 0
                if n:
                    print(f'   ✗ {ad:<20} {n:,} satırda firma_id BOŞ')
                    hatali = True
        eksik_cari = Cari.query.count() - CariFirma.query.filter_by(
            firma_id=firma.id).count()
        if eksik_cari > 0:
            print(f'   ✗ {eksik_cari} cari ana firmaya bağlanmamış')
            hatali = True
        if not hatali:
            print('   ✓ firmasız kayıt yok, bütün cariler bağlı')

        print()
        print('═' * 70)
        if hatali:
            print('  ✗ DOĞRULAMA BAŞARISIZ — yedekten dönmeyi değerlendirin.')
            return 1
        print('  ✓ GÖÇ TAMAMLANDI')
        print()
        print(f'  Ana firma : #{firma.id}  {firma.ad}')
        print(f'  Damgalanan: {damgalanan:,} kayıt')
        print()
        print('  Sistem şu an TEK firmayla, bugünkü gibi çalışır.')
        print('  Firma seçici ve ikinci firma MF2–MF3 ile geliyor.')
        print()
        print('  SONRAKİ ADIMLAR:')
        print('    sudo systemctl restart milestone-erp')
        print('    venv/bin/python degismezlik_denetim.py')
        print('═' * 70)
        return 0


if __name__ == '__main__':
    sys.exit(main())

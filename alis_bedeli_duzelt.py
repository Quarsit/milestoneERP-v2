#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALIŞ BEDELİ DÜZELTME — stok kartı doğru, kayıtlı bedel/borç eski
====================================================================

NE İÇİN: Stok kartındaki fiyat × ölçü DOĞRU ama arka planda kayıtlı
alış bedeli (matrah) ve tedarikçi borcu ESKİ ölçüyle duruyor
(tutarlılık taramasındaki C6 satırları). HD1'den önce kartta ölçü
düzeltilince bedel ve borç güncellenmiyordu; bu kayıtlar o günden
kalma.

NASIL: Kendi hesabını YAPMAZ, veritabanına elle YAZMAZ. Programın
stok kartı "Kaydet" ucunu çağırır; yani senin elle yapacağın işin
aynısını yapar:
    1) fiyatı 0,01 artırıp kaydeder   (bedel yeniden kurulur)
    2) fiyatı eski hâline getirip kaydeder
Matrah, KDV, tedarikçi borcu ve alışın KDV satırı programın kendi
kuralıyla (HD1) birlikte düzelir. Sonra sonucu okuyup BEKLENEN
rakamla karşılaştırır.

GÜVENLİK:
  · `--uygula` YAZMADAN hiçbir şey değiştirmez; yalnız ne yapacağını
    gösterir.
  · Kartı ile bedeli zaten tutan stoğa DOKUNMAZ.
  · Yalnız BLOK stok. Üretim/kesimden gelen mala dokunmaz.
  · Fiyat sonunda kuruşu kuruşuna eski değerine döner; dönmezse
    büyük harfle söyler.

Kullanım (PROJE DİZİNİNDE):
    cd ~/milestoneERP-v2
    venv/bin/python alis_bedeli_duzelt.py                 # yalnız göster
    venv/bin/python alis_bedeli_duzelt.py --uygula        # düzelt

Blok vermezsen CTC-MI2702 ve CTC-MI2703'e bakar. Başka blok için:
    venv/bin/python alis_bedeli_duzelt.py K1234 K1235 [--uygula]
"""
import os
import sys

KOK = os.path.dirname(os.path.abspath(__file__)) or '.'
VARSAYILAN = ['CTC-MI2702', 'CTC-MI2703']
KURUS = 0.005


def _f(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _p(v, dv=''):
    return f'{_f(v):,.2f} {dv or ""}'.strip()


def _y2(v):
    from decimal import Decimal, ROUND_HALF_UP
    return float(Decimal(str(v)).quantize(Decimal('0.01'),
                                          rounding=ROUND_HALF_UP))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    uygula = '--uygula' in argv
    istenen = [a for a in argv if not a.startswith('--')] or VARSAYILAN

    os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
    if KOK not in sys.path:
        sys.path.insert(0, KOK)
    try:
        os.chdir(KOK)
        import flask_app as fa
        from models import db, BlokStok, CariHareket, Kullanici
    except Exception as e:  # noqa: BLE001
        print(f'✗ Program içe aktarılamadı: {e}')
        print('  Bu betik PROJE DİZİNİNDE durmalı ve venv/bin/python ile '
              'çalıştırılmalı.')
        return 1
    try:
        from models import Firma
    except Exception:  # noqa: BLE001
        Firma = None

    def stok_bul(ad):
        ad = ad.strip()
        for kimlik in (ad, 'BLK-MS-' + ad, 'BLK-' + ad):
            s = db.session.get(BlokStok, kimlik)
            if s is not None:
                return s
        return BlokStok.query.filter_by(blok_no=ad).first()

    def borc_bul(s):
        fno = (s.fatura_no or '').strip()
        if not fno:
            return None
        q = CariHareket.query.filter(
            CariHareket.baglanti_tip == 'stok_fatura',
            CariHareket.baglanti_id == fno,
            CariHareket.kaynak == 'stok',
            CariHareket.alacak > 0)
        cid = (getattr(s, 'cari_id', None) or '').strip()
        if cid:
            q = q.filter(CariHareket.cari_id == cid)
        adaylar = q.all()
        return adaylar[0] if len(adaylar) == 1 else None

    def durum(s):
        fb = (s.alis_fiyat_birim or '').strip()
        mik = _f(s.tonaj if fb == 'ton' else s.hacim_m3)
        fiyat = _f(s.alis_fiyati)
        oran = _f(s.kdv_oran)
        dogru_m = _y2(fiyat * mik)
        dogru_k = _y2(dogru_m * oran / 100) if oran > 0 else 0.0
        b = borc_bul(s)
        return {
            'id': s.id, 'fiyat': fiyat, 'birim': fb or 'm3', 'mik': mik,
            'doviz': s.doviz or '', 'matrah': _f(s.matrah),
            'kdv': _f(s.kdv_tutar), 'dogru_m': dogru_m, 'dogru_k': dogru_k,
            'fatura_no': s.fatura_no or '', 'uretici': s.uretici or '',
            'kaynak': (getattr(s, 'kaynak', None) or 'satinalma'),
            'faturali': (getattr(s, 'fatura_durumu', None)
                         or 'faturali') != 'faturasiz',
            'borc_id': b.id if b is not None else None,
            'borc': _f(b.alacak) if b is not None else None,
            'firma_id': getattr(s, 'firma_id', None),
        }

    print()
    print('=' * 78)
    print('  ALIŞ BEDELİ DÜZELTME' + ('' if uygula else '  —  YALNIZ GÖSTERİM'))
    print('=' * 78)

    with fa.app.app_context():
        yonetici = Kullanici.query.filter_by(rol='ADMIN').order_by(
            Kullanici.id).first()
        if yonetici is None:
            print('✗ ADMIN rolünde kullanıcı bulunamadı; işlem yapılmadı.')
            return 1
        yonetici_ad = yonetici.ad
        ilk_firma = None
        if Firma is not None:
            _fr = Firma.query.filter_by(aktif=True).order_by(Firma.id).first()
            ilk_firma = _fr.id if _fr is not None else None

        isler = []
        for ad in istenen:
            s = stok_bul(ad)
            print()
            if s is None:
                print(f'  ✗ {ad}: böyle bir BLOK stok yok — atlandı.')
                continue
            d = durum(s)
            print(f'  {d["id"]} · {d["uretici"]} · fatura: '
                  f'{d["fatura_no"] or "—"}')
            print(f'    kart            : {_p(d["fiyat"], d["doviz"])}/'
                  f'{d["birim"]} × {d["mik"]:g} = '
                  f'{_p(d["dogru_m"], d["doviz"])}')
            print(f'    kayıtlı bedel   : {_p(d["matrah"], d["doviz"])}'
                  f'  (KDV {_p(d["kdv"], d["doviz"])})')
            if d['kaynak'] in ('uretim', 'kesim'):
                print('    → üretim/kesimden gelen mal; alışı yok, atlandı.')
                continue
            if (abs(d['matrah'] - d['dogru_m']) < KURUS
                    and abs(d['kdv'] - d['dogru_k']) < KURUS):
                print('    ✓ kart ile kayıtlı bedel tutuyor; dokunulmayacak.')
                continue
            fark = (d['dogru_m'] + d['dogru_k']) - (d['matrah'] + d['kdv'])
            d['beklenen_borc'] = None
            if not d['faturali']:
                print('    (faturasız stok: yalnız kayıtlı bedel düzelir, '
                      'borç yok)')
            elif d['borc'] is None:
                print('    ⚠ tedarikçi borcu TEK satır olarak bulunamadı; '
                      'bedel düzelir, borcu program kendi kuralıyla arar.')
            else:
                d['beklenen_borc'] = _y2(d['borc'] + fark)
                print(f'    tedarikçi borcu : {_p(d["borc"], d["doviz"])} → '
                      f'{_p(d["beklenen_borc"], d["doviz"])}'
                      f'  (fark {fark:+,.2f})')
            print(f'    YAPILACAK       : kayıtlı bedel '
                  f'{_p(d["matrah"], d["doviz"])} → '
                  f'{_p(d["dogru_m"], d["doviz"])}')
            isler.append(d)

    if not isler:
        print()
        print('Düzeltilecek kayıt yok. Hiçbir şey değiştirilmedi.')
        return 0
    if not uygula:
        print()
        print('Hiçbir şey değiştirilmedi. Rakamlar doğruysa:')
        print('    venv/bin/python alis_bedeli_duzelt.py '
              + ' '.join(a for a in argv if not a.startswith('--'))
              + (' ' if [a for a in argv if not a.startswith('--')] else '')
              + '--uygula')
        return 0

    hata = 0
    for d in isler:
        print()
        print(f'  {d["id"]}')
        c = fa.app.test_client()
        with c.session_transaction() as o:
            o['kullanici'] = yonetici_ad
            o['rol'] = 'ADMIN'
            o['_csrf'] = 'abd'
            o['firma_id'] = d['firma_id'] or ilk_firma
        baslik = {'X-CSRF-Token': 'abd'}
        # Aynı faturada birden çok blok düzeliyorsa borç her adımda
        # iner: beklenen borç, bu stoğa başlamadan HEMEN ÖNCEKİ
        # borçtan hesaplanır (baştaki gösterimdeki rakamdan değil).
        if d.get('beklenen_borc') is not None:
            with fa.app.app_context():
                db.session.expire_all()
                _simdi = durum(stok_bul(d['id']))
            if _simdi['borc'] is not None:
                _fark = ((d['dogru_m'] + d['dogru_k'])
                         - (_simdi['matrah'] + _simdi['kdv']))
                d['borc'] = _simdi['borc']
                d['beklenen_borc'] = _y2(_simdi['borc'] + _fark)
        gecici = _y2(d['fiyat'] + 0.01)
        r1 = c.put(f'/api/stok/{d["id"]}', headers=baslik,
                   json={'tip': 'BLOK', 'alis_fiyati': gecici})
        if r1.status_code != 200:
            print(f'    ✗ 1. adım reddedildi ({r1.status_code}): '
                  f'{(r1.get_json(silent=True) or {})}')
            print('      Bu stokta HİÇBİR ŞEY değişmedi.')
            hata += 1
            continue
        r2 = c.put(f'/api/stok/{d["id"]}', headers=baslik,
                   json={'tip': 'BLOK', 'alis_fiyati': d['fiyat']})
        if r2.status_code != 200:
            print(f'    ✗✗ 2. ADIM REDDEDİLDİ ({r2.status_code}): '
                  f'{(r2.get_json(silent=True) or {})}')
            print(f'      DİKKAT: FİYAT ŞU AN {gecici:,.2f} DURUYOR. Stok '
                  f'kartını açıp fiyatı {d["fiyat"]:,.2f} yapıp kaydet.')
            hata += 1
            continue
        with fa.app.app_context():
            db.session.expire_all()
            y = durum(stok_bul(d['id']))
        tamam = (abs(y['fiyat'] - d['fiyat']) < KURUS
                 and abs(y['matrah'] - d['dogru_m']) < KURUS
                 and abs(y['kdv'] - d['dogru_k']) < KURUS)
        print(f'    fiyat           : {_p(y["fiyat"], y["doviz"])}/{y["birim"]}')
        print(f'    kayıtlı bedel   : {_p(d["matrah"], d["doviz"])} → '
              f'{_p(y["matrah"], y["doviz"])}')
        if d.get('beklenen_borc') is not None:
            print(f'    tedarikçi borcu : {_p(d["borc"], d["doviz"])} → '
                  f'{_p(y["borc"], y["doviz"])}')
            if y['borc'] is None or abs(y['borc'] - d['beklenen_borc']) >= KURUS:
                tamam = False
        if tamam:
            print('    ✓ beklenen rakamlarla tutuyor.')
        else:
            print('    ✗✗ SONUÇ BEKLENENLE TUTMUYOR — bu çıktıyı gönder, '
                  'başka bir şey yapma.')
            hata += 1

    print()
    if hata:
        print(f'{hata} stokta sorun var; yukarıdaki satırlara bak.')
        return 1
    print('Bitti. Doğrulamak için:  venv/bin/python tutarlilik_tara.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())

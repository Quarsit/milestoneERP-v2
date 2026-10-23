#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONARIM — öksüz kalmış KOPYA KDV satırını siler
===============================================

`denetim_zincir.py` tek bir tutarsızlık buldu:

    MYT-MS-26-0038  Devreden KDV  1246.03 TRY
    → PLK-MS-K6462-01   fatura MAR2026000001016   grup MGR-63C1E8

Bu satır, aynı plakanın aynı faturadaki KDV'sinin İKİNCİ bir
kopyası. Gerçeği MYT-MS-26-0040; o, 18 plakalık dağıtım grubunun
(MGR-061051) içinde ve net karşılığı (MYT-MS-26-0039) duruyor.
0038 ise kendi grubunda yapayalnız — net karşılığı yok.

Yarım kalmış ya da eksik silinmiş bir ilk denemenin artığı;
büyük olasılıkla DZ1'in düzelttiği hatadan (eski silme, grubun
bir kısmını bırakıyordu).

ETKİSİ: Devreden KDV 1.246,03 TRY FAZLA görünüyor. Stok
maliyetine ve kâra girmiyor (o hesap KDV satırlarını süzüyor),
ama KDV iadesi tarafına giriyor.

GÜVENLİK ADIMLARI — hepsi sağlanmazsa HİÇBİR ŞEY yapılmaz:
  1 satır var ve Devreden KDV
  2 kendi grubunda tek
  3 net karşılığı yok
  4 aynı stok + fatura + tutar ile BAŞKA bir KDV satırı var
    (yani gerçekten kopya)
  5 o kopyanın net karşılığı VAR
  6 bu satıra bağlı cari hareket YOK
  7 bu satır bir KDV İADE DOSYASINA bağlı DEĞİL
  8 bu satır bir dönüşüme bağlı DEĞİL

Silmeden önce satırın tamamı `silinen_MYT-...json` dosyasına
yazılır; geri koymak istersen içinde her alan duruyor.

    cd ~/milestoneERP-v2
    venv/bin/python onarim_kdv_kopya.py              # RAPOR
    venv/bin/python onarim_kdv_kopya.py --uygula
"""
import json
import os
import sys

HEDEF = 'MYT-MS-26-0038'
UYGULA = '--uygula' in sys.argv

os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _venv_uyar(hata):
    print('=' * 70)
    print('  HATA: ' + str(hata))
    print('=' * 70)
    print('  Bu betik veritabanina baglaniyor, yani sanal ortam gerekli:')
    print()
    print('      venv/bin/python ' + os.path.basename(__file__))
    print('=' * 70)
    sys.exit(1)


try:
    import flask_app as fa                             # noqa: E402
    from models import db, Maliyet, CariHareket        # noqa: E402
except ModuleNotFoundError as _h:
    _venv_uyar(_h)

CIZGI = '=' * 70
KDV = 'Devreden KDV'


def ana():
    with fa.app.app_context():
        m = db.session.get(Maliyet, HEDEF)
        print(CIZGI)
        print(f'  ONARIM — {HEDEF}')
        print(CIZGI)

        if m is None:
            print('  Satır bulunamadı. Zaten silinmiş olabilir.')
            return 0

        print(f'  tip      : {m.maliyet_tip}')
        print(f'  tutar    : {m.tutar} {m.doviz}')
        print(f'  stok     : {m.baglanti_id}')
        print(f'  fatura   : {m.fatura_no}')
        print(f'  grup     : {m.grup_id}')
        print(f'  tarih    : {m.maliyet_tarihi}')

        kosullar = []

        def kontrol(ad, sonuc, ayrinti=''):
            kosullar.append(sonuc)
            print(f'  {"✓" if sonuc else "✗"} {ad}'
                  + (f'  — {ayrinti}' if ayrinti else ''))

        print()
        print('  GÜVENLİK ADIMLARI')
        kontrol('Devreden KDV satırı', m.maliyet_tip == KDV, m.maliyet_tip)

        grup = Maliyet.query.filter_by(grup_id=m.grup_id).all() \
            if m.grup_id else [m]
        kontrol('kendi grubunda tek', len(grup) == 1, f'{len(grup)} satır')

        net_kardes = [x for x in grup if x.maliyet_tip != KDV]
        kontrol('net karşılığı yok', not net_kardes,
                ', '.join(x.id for x in net_kardes) or '—')

        ikizler = Maliyet.query.filter(
            Maliyet.id != m.id,
            Maliyet.maliyet_tip == KDV,
            Maliyet.baglanti_id == m.baglanti_id,
            Maliyet.fatura_no == m.fatura_no).all()
        ikizler = [x for x in ikizler
                   if abs((x.tutar or 0) - (m.tutar or 0)) < 0.01]
        kontrol('aynı stok+fatura+tutar ile başka KDV satırı var',
                len(ikizler) == 1,
                ', '.join(x.id for x in ikizler) or 'yok')

        ikiz_net = []
        if len(ikizler) == 1 and ikizler[0].grup_id:
            ikiz_net = [x for x in
                        Maliyet.query.filter_by(
                            grup_id=ikizler[0].grup_id).all()
                        if x.maliyet_tip != KDV
                        and x.baglanti_id == m.baglanti_id]
        kontrol('o kopyanın net karşılığı var', bool(ikiz_net),
                ', '.join(x.id for x in ikiz_net) or 'yok')

        hareketler = CariHareket.query.filter_by(
            baglanti_tip='maliyet', baglanti_id=m.id).all()
        kontrol('bağlı cari hareket yok', not hareketler,
                ', '.join(h.id for h in hareketler) or '—')

        kontrol('KDV iade dosyasına bağlı değil',
                not getattr(m, 'iade_dosya_id', None),
                str(getattr(m, 'iade_dosya_id', None) or '—'))

        kontrol('dönüşüme bağlı değil',
                not getattr(m, 'donusum_id', None),
                str(getattr(m, 'donusum_id', None) or '—'))

        print()
        if not all(kosullar):
            print(CIZGI)
            print('  ✗ Adımlardan biri sağlanmadı → HİÇBİR ŞEY YAPILMADI.')
            print('  Çıktıyı gönder, duruma göre bakalım.')
            print(CIZGI)
            return 1

        toplam = db.session.query(db.func.sum(Maliyet.tutar)).filter(
            Maliyet.maliyet_tip == KDV,
            Maliyet.fatura_no == m.fatura_no).scalar() or 0
        print(f'  Bu faturanın toplam Devreden KDV\'si : {round(toplam, 2)}'
              f' {m.doviz}')
        print(f'  Silinince                            : '
              f'{round(toplam - (m.tutar or 0), 2)} {m.doviz}')

        if not UYGULA:
            print()
            print(CIZGI)
            print('  RAPOR — hiçbir şey yazılmadı. Uygulamak için:')
            print('      venv/bin/python onarim_kdv_kopya.py --uygula')
            print(CIZGI)
            return 0

        yedek = {c.name: (str(getattr(m, c.name))
                          if getattr(m, c.name) is not None else None)
                 for c in Maliyet.__table__.columns}
        yol = f'silinen_{HEDEF}.json'
        with open(yol, 'w', encoding='utf-8') as f:
            json.dump(yedek, f, ensure_ascii=False, indent=2)
        db.session.delete(m)
        db.session.commit()
        print()
        print(CIZGI)
        print(f'  ✓ {HEDEF} silindi.')
        print(f'  Yedeği: {yol}  (her alan içinde)')
        print('  Doğrulamak için: venv/bin/python denetim_zincir.py')
        print(CIZGI)
        return 0


if __name__ == '__main__':
    sys.exit(ana())

#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — "İZLİ KDV KALEMİ YOK" TANISI  ·  T1
#
#  NE İŞE YARAR:
#    KDV İade ekranında bir ihracat faturasının yanında "izli KDV
#    kalemi yok" yazıyorsa, bunun ALTI FARKLI sebebi olabilir. Üçü
#    tamamen normaldir, üçü ise düzeltilmesi gereken bir durumdur.
#    Bu betik her fatura için zinciri adım adım yürüyüp hangi halkanın
#    koptuğunu söyler.
#
#  İZLENEN ZİNCİR:
#    Fatura.siparis_id
#      └→ SatisKaydi(siparis_id).stok_id
#           └→ Maliyet(baglanti_tip='stok', baglanti_id=stok_id,
#                      maliyet_tip='Iade KDV', aktif=True)
#
#  BU BETİK HİÇBİR ŞEYİ DEĞİŞTİRMEZ — yalnızca okur ve raporlar.
#
#  KULLANIM (proje dizininde):
#      venv/bin/python tani_izli_kdv.py
#      venv/bin/python tani_izli_kdv.py --donem 2026-06
#      venv/bin/python tani_izli_kdv.py --fatura FTR0042
# ══════════════════════════════════════════════════════════════════════
import os
import sys
from collections import Counter

from dotenv import load_dotenv

load_dotenv()

if not os.environ.get('DATABASE_URL'):
    print("HATA: DATABASE_URL bulunamadı (.env dosyası okunamadı).")
    sys.exit(1)

sys.path.insert(0, os.getcwd())

DONEM = None
FATURA = None
for i, a in enumerate(sys.argv[1:]):
    if a == '--donem' and i + 2 <= len(sys.argv[1:]):
        DONEM = sys.argv[i + 2]
    if a == '--fatura' and i + 2 <= len(sys.argv[1:]):
        FATURA = sys.argv[i + 2]

import flask_app  # noqa: E402
from models import (db, Fatura, Maliyet, SatisKaydi, Siparis,  # noqa: E402
                    Rezervasyon, BlokStok, PlakaStok, EbatliStok)

app = flask_app.app

IADE_KAPSAMI = ('ihracat', 'ihrac_kayitli')
KESILMIS = ('Kesildi', 'Kismi Tahsil', 'Tahsil Edildi')

SEBEP_ACIKLAMA = {
    'TAMAM': ('İzli KDV kalemi bulundu', 'normal'),
    'SIPARIS_YOK': (
        'Fatura bir siparişe bağlı değil (siparis_id boş). Zincir daha '
        'ilk adımda kopuyor — kalemleri elle seçmeniz gerekir.', 'duzeltilebilir'),
    'SATIS_KAYDI_YOK': (
        'Siparişin satış kaydı yok — sipariş "Teslim Edildi" yapılmamış. '
        'Teslim işaretlenince KDV dönüşümü de tetiklenir.', 'duzeltilebilir'),
    'STOKSUZ': (
        'Satış kaydı STOKSUZ (stok_id "STOKSUZ-" ile başlıyor). Bu satış '
        'stoktan çıkmadığı için yüklenilen KDV de yok. NORMAL.', 'normal'),
    'KDV_KALEMI_YOK': (
        'Stoklar var ama hiç KDV maliyet kalemi yok. Alış KDV\'siz '
        'yapılmış (ihraç kayıtlı/faturasız alım) ya da stok girişinde '
        'KDV oranı 0 girilmiş. Alış gerçekten KDV\'liyse VERİ EKSİK.', 'incele'),
    'DEVREDEN_KALDI': (
        'Stoğun "Devreden KDV" kalemi var ama "Iade KDV"ye DÖNÜŞMEMİŞ. '
        'Genellikle sipariş rezervasyonsuz teslim edilmiştir — dönüşüm '
        'rezervasyona bakar, satış kaydına değil. DÜZELTİLMELİ.', 'sorun'),
    'PASIF': (
        'Iade KDV kalemi var ama PASİF. Sipariş teslimi geri alınmış. '
        'İade hakkı düşmüş sayılır.', 'incele'),
    'DOSYAYA_BAGLI': (
        'Zincir SAĞLAM — Iade KDV kalemleri bulunmuş ve bir iade dosyasına '
        'bağlanmış. Aday listesinde çıkmamasının sebebi budur; iş bitmiş '
        'demektir. Hangi dosyada olduğu aşağıda yazıyor.', 'normal'),
}


def stok_var_mi(stok_id):
    for M in (BlokStok, PlakaStok, EbatliStok):
        if db.session.get(M, stok_id):
            return True
    return False


def teshis(f):
    """Tek fatura için zinciri yürür. Döner: (kod, ayrinti_dict)."""
    ay = {'fatura_no': f.fatura_no or f.id, 'musteri': f.musteri,
          'tarih': f.fatura_tarihi.isoformat() if f.fatura_tarihi else '—',
          'siparis_id': f.siparis_id}

    if not f.siparis_id:
        return 'SIPARIS_YOK', ay

    skler = SatisKaydi.query.filter_by(siparis_id=f.siparis_id).all()
    ay['satis_kaydi'] = len(skler)
    if not skler:
        sip = db.session.get(Siparis, f.siparis_id)
        ay['siparis_durum'] = sip.durum if sip else 'sipariş kaydı yok'
        return 'SATIS_KAYDI_YOK', ay

    stok_idler = [sk.stok_id for sk in skler if sk.stok_id]
    gercek = [s for s in stok_idler if not str(s).startswith('STOKSUZ-')]
    ay['stok'] = len(gercek)
    if not gercek:
        return 'STOKSUZ', ay

    kalemler = Maliyet.query.filter(
        db.func.lower(Maliyet.baglanti_tip) == 'stok',
        Maliyet.baglanti_id.in_(gercek),
        Maliyet.maliyet_tip.in_(['Iade KDV', 'Devreden KDV'])).all()

    iade = [m for m in kalemler if m.maliyet_tip == 'Iade KDV']
    devreden = [m for m in kalemler if m.maliyet_tip == 'Devreden KDV']
    iade_aktif = [m for m in iade if m.aktif]
    ay['iade'] = len(iade)
    ay['iade_aktif'] = len(iade_aktif)
    ay['devreden_aktif'] = len([m for m in devreden if m.aktif])

    if iade_aktif:
        bagsiz = [m for m in iade_aktif if not m.iade_dosya_id]
        ay['bagsiz'] = len(bagsiz)
        ay['tutar'] = round(sum(m.tutar or 0 for m in bagsiz), 2)
        if bagsiz:
            return 'TAMAM', ay
        # Hepsi bağlı — hangi dosya(lar)da olduğunu göster.
        dosyalar = sorted({m.iade_dosya_id for m in iade_aktif if m.iade_dosya_id})
        ay['dosyalar'] = ', '.join(dosyalar)
        ay['bagli_tutar'] = round(sum(m.tutar or 0 for m in iade_aktif), 2)
        return 'DOSYAYA_BAGLI', ay

    if ay['devreden_aktif']:
        sip = db.session.get(Siparis, f.siparis_id)
        rez = Rezervasyon.query.filter_by(siparis_id=f.siparis_id,
                                          iptal_nedeni=None).count()
        ay['siparis_durum'] = sip.durum if sip else '—'
        ay['satis_tipi'] = sip.satis_tipi if sip else '—'
        ay['rezervasyon'] = rez
        ay['tutar'] = round(sum(m.tutar or 0 for m in devreden if m.aktif), 2)
        return 'DEVREDEN_KALDI', ay

    if iade:
        return 'PASIF', ay
    return 'KDV_KALEMI_YOK', ay


with app.app_context():
    q = Fatura.query.filter(Fatura.satis_tipi.in_(IADE_KAPSAMI),
                            Fatura.durum.in_(KESILMIS))
    if FATURA:
        q = Fatura.query.filter(
            db.or_(Fatura.id == FATURA, Fatura.fatura_no == FATURA))
    faturalar = q.order_by(Fatura.fatura_tarihi).all()
    if DONEM:
        faturalar = [f for f in faturalar
                     if f.fatura_tarihi and f.fatura_tarihi.isoformat()[:7] == DONEM]

    print("═" * 72)
    print(" T1 · 'İZLİ KDV KALEMİ YOK' TANISI")
    print("═" * 72)
    kapsam = f"dönem {DONEM}" if DONEM else (f"fatura {FATURA}" if FATURA else "tüm dönemler")
    print(f" {len(faturalar)} kesilmiş ihracat/ihraç kayıtlı fatura · {kapsam}")
    print()

    if not faturalar:
        print(" Ölçüte uyan fatura yok.")
        sys.exit(0)

    gruplar = {}
    for f in faturalar:
        kod, ay = teshis(f)
        gruplar.setdefault(kod, []).append(ay)

    sira = ['DEVREDEN_KALDI', 'KDV_KALEMI_YOK', 'PASIF', 'SATIS_KAYDI_YOK',
            'SIPARIS_YOK', 'STOKSUZ', 'DOSYAYA_BAGLI', 'TAMAM']
    isaret = {'sorun': '✗', 'incele': '!', 'duzeltilebilir': '·', 'normal': '✓'}

    for kod in sira:
        if kod not in gruplar:
            continue
        aciklama, seviye = SEBEP_ACIKLAMA[kod]
        kayitlar = gruplar[kod]
        print("─" * 72)
        print(f" {isaret[seviye]} {kod}  —  {len(kayitlar)} fatura")
        print("─" * 72)
        hat = ''
        for k in aciklama.split():
            if len(hat) + len(k) + 1 > 68:
                print(f"   {hat}")
                hat = k
            else:
                hat = (hat + ' ' + k).strip()
        if hat:
            print(f"   {hat}")
        print()
        for ay in kayitlar[:15]:
            ek = ''
            if kod == 'DEVREDEN_KALDI':
                ek = (f" · sipariş {ay.get('siparis_durum')} · "
                      f"rezervasyon {ay.get('rezervasyon')} · "
                      f"{ay.get('devreden_aktif')} kalem / {ay.get('tutar')} TL")
            elif kod == 'TAMAM':
                ek = f" · {ay.get('bagsiz')} kalem / {ay.get('tutar')} TL"
            elif kod == 'SATIS_KAYDI_YOK':
                ek = f" · sipariş durumu: {ay.get('siparis_durum')}"
            elif kod == 'DOSYAYA_BAGLI':
                ek = (f" · dosya {ay.get('dosyalar')} · "
                      f"{ay.get('iade_aktif')} kalem / {ay.get('bagli_tutar')} TL")
            elif kod == 'KDV_KALEMI_YOK':
                ek = f" · {ay.get('stok')} stok"
            print(f"     {ay['fatura_no']:<20s} {ay['tarih']}  "
                  f"{(ay['musteri'] or '')[:22]:<22s}{ek}")
        if len(kayitlar) > 15:
            print(f"     … +{len(kayitlar) - 15} fatura")
        print()

    print("═" * 72)
    ozet = Counter({k: len(v) for k, v in gruplar.items()})
    sorunlu = ozet.get('DEVREDEN_KALDI', 0)
    if sorunlu:
        print(f" ✗ {sorunlu} faturada KDV DÖNÜŞÜMÜ YAPILMAMIŞ — bu tutarlar")
        print("   iade dosyasına giremez. Aşağıdaki nota bakın.")
    else:
        print(" ✓ Dönüşüm bekleyen fatura yok.")
    print("═" * 72)

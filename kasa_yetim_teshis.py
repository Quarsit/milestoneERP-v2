#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — KASADA TAKILI TAHSİLAT TEŞHİSİ
#
#  ── NE İÇİN ──
#    19.09.2026'ya kadar fatura tahsilatı silindiğinde fatura yeniden
#    açılıyor ama tahsilatla oluşan KASA GİRİŞİ silinmiyordu (TH2).
#    Kasa ekranı da bu girişi "önce tahsilatı silin" diyerek silmeye
#    izin vermiyordu: para kasada kalıcı olarak takılı kalıyordu.
#
#    Bu betik, dayanağı (tahsilat kaydı) artık olmayan kasa girişlerini
#    bulur.
#
#  ── İKİ GÜVEN SEVİYESİ ──
#    KESİN     Bağlı tahsilat / fatura kaydı hiç yok.
#    MUHTEMEL  Eski biçim (kasa girişi faturaya bağlı): fatura hâlâ
#              duruyor ama bu kasa girişiyle AYNI ANDA oluşmuş bir
#              tahsilat bulunamadı. Tahsilatı silinmiş olabilir;
#              elle kontrol edin.
#
#  ── VARSAYILAN: HİÇBİR ŞEY DEĞİŞTİRMEZ ──  Yalnızca SELECT.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python kasa_yetim_teshis.py              # rapor
#      venv/bin/python kasa_yetim_teshis.py --duzelt     # yalnızca KESİN
#                                                         # olanları geri alır
#    --duzelt: kasa girişini siler ve kasa bakiyesinden düşer.
#    Önce yedek alın:  sudo /usr/local/bin/milestone-yedek.sh
#    MUHTEMEL olanlara DOKUNMAZ. Kontrol edip emin olduklarınızı
#    numarasıyla tek tek geri alın (kasa ekranı bunlara izin vermiyor):
#      venv/bin/python kasa_yetim_teshis.py --sil=12,15
# ══════════════════════════════════════════════════════════════════════
import os
import sys
from datetime import datetime
from pathlib import Path

if not Path('flask_app.py').exists():
    print("HATA: flask_app.py bu klasörde yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

for _a in sys.argv[1:]:
    if _a.startswith('--url='):
        os.environ['DATABASE_URL'] = _a.split('=', 1)[1]

if not os.environ.get('DATABASE_URL'):
    print("HATA: DATABASE_URL bulunamadı (.env okunamadı).")
    print("  Adres olmadan boş bir SQLite'a bağlanıp yanlışlıkla")
    print("  'sorun yok' raporu verirdim. Çalışmayı reddediyorum.")
    sys.exit(1)

DUZELT = '--duzelt' in sys.argv
SIL = set()
for _a in sys.argv[1:]:
    if _a.startswith('--sil='):
        SIL |= {int(x) for x in _a.split('=', 1)[1].split(',') if x.strip().isdigit()}
os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
sys.path.insert(0, str(Path('.').resolve()))

import flask_app  # noqa: E402
from models import db, CariHareket, KasaHareket, Kasa, Fatura  # noqa: E402

YAKIN_SN = 120   # tahsilat ile kasa girişi aynı istekte oluşur


def cizgi(k='─'):
    print(k * 74)


def main():
    kesin, muhtemel = [], []
    khs = KasaHareket.query.filter_by(baglanti_tip='tahsilat').all()
    kasalar = {k.id: k for k in Kasa.query.all()}

    eski_bicim = {}          # fatura_id -> [KasaHareket]
    for kh in khs:
        bid = (kh.baglanti_id or '').strip()
        if bid and db.session.get(CariHareket, bid):
            continue                                   # yeni biçim, dayanağı var
        if bid and db.session.get(Fatura, bid):
            eski_bicim.setdefault(bid, []).append(kh)  # eski biçim, aşağıda
            continue
        kesin.append((kh, 'bağlı tahsilat/fatura kaydı yok'))

    yeni_bagli = {kh.baglanti_id for kh in khs}
    for fid, liste in eski_bicim.items():
        # Kendi (yeni biçim) kasa girişi olan tahsilatlar eşleşmeye
        # katılmaz — onların kasa kaydı zaten ayrı.
        tahsilatlar = [t for t in CariHareket.query.filter_by(
            kaynak='tahsilat', baglanti_tip='fatura', baglanti_id=fid).all()
            if t.id not in yeni_bagli]
        if not tahsilatlar:
            for kh in liste:
                kesin.append((kh, f'fatura {fid} için eşleşecek tahsilat kalmamış'))
            continue
        # Her kasa girişi, aynı istekte (±{YAKIN_SN} sn) oluşmuş bir
        # tahsilatla eşleşmeli. Eşleşmeyen = tahsilatı silinmiş olabilir.
        kalan_t = list(tahsilatlar)
        for kh in sorted(liste, key=lambda k: k.olusturma or datetime.min):
            if not kh.olusturma:
                continue
            yakin = [t for t in kalan_t if t.guncelleme and
                     abs((kh.olusturma - t.guncelleme).total_seconds()) <= YAKIN_SN]
            if yakin:
                kalan_t.remove(min(yakin, key=lambda t: abs((kh.olusturma - t.guncelleme).total_seconds())))
            else:
                muhtemel.append((kh, f'fatura {fid}: aynı anda oluşmuş tahsilat bulunamadı '
                                     f'(faturada {len(tahsilatlar)} tahsilat var)'))

    cizgi('═')
    print(' MILESTONE ERP — KASADA TAKILI TAHSİLAT TEŞHİSİ'
          + ('   [DÜZELTME KİPİ]' if DUZELT else '   (salt okunur)'))
    cizgi('═')
    print(f' İncelenen tahsilat kaynaklı kasa girişi: {len(khs)}')

    def yaz(baslik, liste):
        print()
        cizgi()
        print(f' {baslik}: {len(liste)}')
        cizgi()
        if not liste:
            print('   ✓ yok')
            return
        toplam = {}
        for kh, neden in sorted(liste, key=lambda x: (x[0].kasa_id, x[0].tarih or x[0].olusturma)):
            k = kasalar.get(kh.kasa_id)
            dv = k.doviz if k else '?'
            isaret = 1 if kh.tip == 'giris' else -1
            toplam[(k.ad if k else kh.kasa_id, dv)] = toplam.get((k.ad if k else kh.kasa_id, dv), 0) + isaret * float(kh.tutar or 0)
            tarih = (kh.tarih or kh.olusturma)
            print(f'   #{kh.id:<6} {tarih.strftime("%d.%m.%Y") if tarih else "—":<11}'
                  f' {k.ad if k else kh.kasa_id!s:<18.18} {("+" if isaret > 0 else "-")}{float(kh.tutar or 0):>13,.2f} {dv}')
            print(f'           {(kh.aciklama or "")[:60]}')
            print(f'           → {neden}')
        print()
        for (ad, dv), t in toplam.items():
            print(f'   Toplam  {ad!s:<20.20} {t:>+15,.2f} {dv}')

    yaz('KESİN (dayanağı yok)', kesin)
    yaz('MUHTEMEL (elle kontrol edin)', muhtemel)

    hedef = []
    if DUZELT:
        hedef += [kh for kh, _ in kesin]
    if SIL:
        bulunan = {kh.id: kh for kh, _ in kesin + muhtemel}
        yok = SIL - set(bulunan)
        if yok:
            print(f"\n ✗ Şu numaralar listede yok, dokunulmadı: {', '.join(map(str, sorted(yok)))}")
        hedef += [bulunan[i] for i in sorted(SIL & set(bulunan)) if bulunan[i] not in hedef]
    if hedef:
        print()
        cizgi()
        print(' DÜZELTİLİYOR')
        cizgi()
        for kh in hedef:
            k = db.session.get(Kasa, kh.kasa_id)
            t = float(kh.tutar or 0)
            if k:
                k.bakiye = round(float(k.bakiye or 0) + (-t if kh.tip == 'giris' else t), 3)
            print(f'   ✓ #{kh.id} silindi, {k.ad if k else "?"} bakiyesi '
                  f'{"-" if kh.tip == "giris" else "+"}{t:,.2f} düzeltildi')
            db.session.delete(kh)
        db.session.commit()
        print('\n   Kontrol için: venv/bin/python degismezlik_denetim.py')

    print()
    cizgi('═')
    if not kesin and not muhtemel:
        print(' ✓ Kasada takılı tahsilat girişi yok.')
    elif not hedef and kesin:
        print(' KESİN olanları geri almak için (önce yedek alın):')
        print('   sudo /usr/local/bin/milestone-yedek.sh')
        print('   venv/bin/python kasa_yetim_teshis.py --duzelt')
    if not hedef and muhtemel:
        print(' MUHTEMEL olanları kontrol ettikten sonra numarasıyla geri alın:')
        print('   venv/bin/python kasa_yetim_teshis.py --sil=' + ','.join(str(kh.id) for kh, _ in muhtemel))
    cizgi('═')


with flask_app.app.app_context():
    main()

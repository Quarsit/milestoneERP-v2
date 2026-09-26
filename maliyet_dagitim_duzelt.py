#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — EŞİT BÖLÜNMÜŞ MALİYETLERİ ORANTILIYA ÇEVİR  (MD1)
#
#  ── NE İÇİN ──
#    Maliyet ekranında birden çok kayıt seçip tutar girildiğinde,
#    tutar KAYIT SAYISINA bölünüyordu. Navlun, gümrük, liman gideri
#    ise AĞIRLIKLA ölçeklenir. Ölçülen sonuç, aynı faturayla aynı
#    fiyata alınmış dört blokta:
#
#        18,06 ton → 303,72 $/ton      6,42 ton → 441,24 $/ton
#        18,33 ton → 302,60 $/ton      6,69 ton → 432,63 $/ton
#
#    Küçük blok, büyük bloğun navlununu sırtlanıyor. Kârlılık bu
#    rakamdan beslendiği için küçük parçalar olduğundan pahalı,
#    büyükler olduğundan ucuz görünüyor.
#
#    Bu betik, eşit bölündüğü anlaşılan maliyet gruplarını bulur ve
#    payları ölçüye (blokta tonaj, plaka/ebatlıda m²) göre yeniden
#    hesaplar. TOPLAM TUTAR DEĞİŞMEZ — yalnızca kayıtlar arasındaki
#    paylaşım düzelir.
#
#  ── NASIL GRUPLUYOR ──
#    Aynı anda yazılmış (60 sn içinde), aynı maliyet tipi, aynı
#    fatura no, aynı döviz ve BİRBİRİNE EŞİT tutarlı, en az iki
#    stok kaydına bağlı maliyetler tek grup sayılır. Zaten orantılı
#    yazılmış gruplar (tutarlar farklı) ATLANIR.
#
#  ── GÜVENLİ ──
#    • Varsayılan SALT OKUNUR; --uygula demeden hiçbir şey yazılmaz.
#    • Yalnızca `tutar` ve `usd_karsilik` güncellenir; kayıt
#      silinmez, eklenmez, bağlantı değişmez.
#    • Ölçüsü olmayan ya da oranlanamayan grup ATLANIR ve raporlanır.
#    • Tekrar çalıştırılabilir — düzeltilmiş grup artık eşit
#      görünmediği için ikinci kez ele alınmaz.
#
#  ── KULLANIM (proje klasöründe) ──
#      venv/bin/python maliyet_dagitim_duzelt.py            # rapor
#      venv/bin/python maliyet_dagitim_duzelt.py --uygula   # yaz
# ══════════════════════════════════════════════════════════════════════
import os
import sys
from collections import defaultdict
from pathlib import Path

if not Path('flask_app.py').exists():
    print('HATA: flask_app.py bu klasörde yok. Proje klasöründe çalıştırın.')
    sys.exit(1)

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

UYGULA = '--uygula' in sys.argv
for _a in sys.argv[1:]:
    if _a.startswith('--url='):
        os.environ['DATABASE_URL'] = _a.split('=', 1)[1]

if not os.environ.get('DATABASE_URL'):
    print('HATA: DATABASE_URL bulunamadı (.env okunamadı).')
    sys.exit(1)

os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
sys.path.insert(0, str(Path('.').resolve()))

import flask_app  # noqa: E402
from models import db, Maliyet, BlokStok, PlakaStok, EbatliStok  # noqa: E402

PENCERE_SN = 60          # aynı kaydetme işlemi sayılan süre
KURUS = 0.02             # eşitlik toleransı


def para(v):
    return f'{float(v or 0):,.2f}'.replace(',', '#').replace('.', ',').replace('#', '.')


def stok_bul(stok_id):
    for tip, sinif in (('BLOK', BlokStok), ('PLAKA', PlakaStok), ('EBATLI', EbatliStok)):
        st = sinif.query.get(stok_id)
        if st is not None:
            return tip, st
    return None, None


def olcu_sec(kayitlar):
    """(olcu_listesi, not) — oranlanamıyorsa (None, sebep)."""
    tipler = {t for t, _ in kayitlar}
    if tipler == {'BLOK'}:
        tonajlar = [float(getattr(s, 'tonaj', 0) or 0) for _, s in kayitlar]
        if all(t > 0 for t in tonajlar):
            return tonajlar, 'tonaj'
        hacimler = [float(getattr(s, 'hacim_m3', 0) or 0) for _, s in kayitlar]
        if all(h > 0 for h in hacimler):
            return hacimler, 'hacim m³ (tonaj girilmemiş)'
        return None, 'blokların tonaj/m³ ölçüsü yok'
    if tipler <= {'PLAKA', 'EBATLI'}:
        m2 = [float(getattr(s, 'metraj_m2', 0) or 0) for _, s in kayitlar]
        if all(x > 0 for x in m2):
            return m2, 'metraj m²'
        return None, 'kayıtların m² ölçüsü yok'
    return None, 'grupta hem blok hem plaka var — ton ile m² oranlanamaz'


print('═' * 78)
print(' EŞİT BÖLÜNMÜŞ MALİYETLER (MD1) — paylar ölçüye göre yeniden hesaplanır')
print('═' * 78)

with flask_app.app.app_context():
    hepsi = Maliyet.query.filter(
        Maliyet.baglanti_tip == 'stok',
        Maliyet.aktif.is_(True)).order_by(Maliyet.olusturma).all()

    # ── Gruplama: aynı anda + aynı tip/fatura/döviz ──
    kovalar = defaultdict(list)
    for m in hepsi:
        if not m.olusturma:
            continue
        anahtar_ust = (m.maliyet_tip or '', m.fatura_no or '', m.doviz or '')
        yerlesti = False
        for (ust, ilk_zaman), liste in kovalar.items():
            if ust != anahtar_ust:
                continue
            if abs((m.olusturma - ilk_zaman).total_seconds()) <= PENCERE_SN:
                liste.append(m)
                yerlesti = True
                break
        if not yerlesti:
            kovalar[(anahtar_ust, m.olusturma)].append(m)

    duzeltilecek, atlanan, zaten_iyi = [], [], 0

    for (ust, _z), grup in kovalar.items():
        if len(grup) < 2:
            continue
        tutarlar = [float(x.tutar or 0) for x in grup]
        if max(tutarlar) - min(tutarlar) > KURUS:
            zaten_iyi += 1          # zaten farklı paylar — orantılı yazılmış
            continue

        kayitlar, eksik = [], False
        for m in grup:
            tip, st = stok_bul(m.baglanti_id)
            if st is None:
                eksik = True
                break
            kayitlar.append((tip, st))
        if eksik:
            atlanan.append((ust, len(grup), 'bağlı stok bulunamadı'))
            continue

        olculer, notu = olcu_sec(kayitlar)
        if olculer is None:
            atlanan.append((ust, len(grup), notu))
            continue

        toplam_tutar = round(sum(tutarlar), 2)
        toplam_olcu = sum(olculer)
        yeni = [round(toplam_tutar * o / toplam_olcu, 2) for o in olculer]
        fark = round(toplam_tutar - sum(yeni), 2)
        if abs(fark) >= 0.01:
            en_buyuk = yeni.index(max(yeni))
            yeni[en_buyuk] = round(yeni[en_buyuk] + fark, 2)
        if all(abs(y - e) < 0.01 for y, e in zip(yeni, tutarlar)):
            zaten_iyi += 1
            continue
        duzeltilecek.append((ust, grup, kayitlar, olculer, yeni, notu, toplam_tutar))

    print(f' {len(hepsi)} stok maliyeti · {len(kovalar)} kayıt grubu')
    print(f' düzeltilecek grup: {len(duzeltilecek)} · zaten doğru: {zaten_iyi}'
          + (f' · atlanan: {len(atlanan)}' if atlanan else ''))
    print()

    if atlanan:
        print(' ── ATLANAN GRUPLAR (dokunulmadı) ──')
        for (tip, fno, dv), adet, sebep in atlanan[:10]:
            print(f'   {tip[:24]:<24} {fno[:14]:<14} {adet:>3} kayıt — {sebep}')
        if len(atlanan) > 10:
            print(f'   … ve {len(atlanan) - 10} grup daha')
        print()

    if not duzeltilecek:
        print(' ✓ Eşit bölünmüş maliyet grubu yok — yapacak bir şey yok.')
        sys.exit(0)

    for (tip, fno, dv), grup, kayitlar, olculer, yeni, notu, toplam in duzeltilecek:
        print(f' ── {tip}  ·  fatura: {fno or "belgesiz"}  ·  '
              f'toplam {para(toplam)} {dv}  ·  ölçü: {notu}')
        for m, (stip, st), olcu, y in zip(grup, kayitlar, olculer, yeni):
            ad = (getattr(st, 'blok_no', None) or getattr(st, 'kasa_no', None)
                  or m.baglanti_id)
            onceki = float(m.tutar or 0)
            yuzde = f'{(y - onceki) / onceki * 100:+.0f}%' if onceki else '—'
            print(f'    {str(ad)[:16]:<16} {olcu:>9.2f}   '
                  f'{para(onceki):>12} → {para(y):>12}   ({yuzde})')
        print()

    if not UYGULA:
        print(' Bu bir ÖN İZLEME. Yazmak için:')
        print('   venv/bin/python maliyet_dagitim_duzelt.py --uygula')
        sys.exit(0)

    # ── YAZ ──
    yazilan, etkilenen_stoklar = 0, set()
    for grup_sira, ((tip, fno, dv), grup, kayitlar, olculer, yeni, notu,
                    toplam) in enumerate(duzeltilecek, start=1):
        toplam_olcu = sum(olculer)
        # usd_karsilik: grubun ESKI USD TOPLAMI olcuye gore yeniden
        # paylastirilir. Bugunun kuruyla yeniden cevirmek, gecmis
        # maliyeti bugune tasirdi — kur farki kar gibi gorunurdu.
        eski_usd_toplam = sum(float(m.usd_karsilik or 0) for m in grup)
        for m, olcu, y in zip(grup, olculer, yeni):
            m.tutar = y
            if eski_usd_toplam > 0 and toplam_olcu > 0:
                m.usd_karsilik = round(eski_usd_toplam * olcu / toplam_olcu, 2)
            m.toplam_miktar = olcu
            if not m.grup_id:
                m.grup_id = f'MDG{grup_sira:04d}'
            _not = f'MD1: pay {notu} ile yeniden hesaplandı'
            if _not not in (m.aciklama or ''):
                m.aciklama = ((m.aciklama or '') + ' · ' + _not).strip(' ·')
            etkilenen_stoklar.add(m.baglanti_id)
            yazilan += 1

    db.session.commit()
    print(f' ✓ {yazilan} maliyet kaydının payı yeniden hesaplandı '
          f'({len(duzeltilecek)} grup).')
    print(f'   Etkilenen stok: {len(etkilenen_stoklar)}')
    print()
    print(' Kârlılık kayıtlarının da güncellenmesi için uygulamayı yeniden')
    print(' başlatıp ilgili stokların bulunduğu siparişleri açmanız yeterli;')
    print(' giydirilmiş maliyet stok ekranında hemen doğru görünür.')

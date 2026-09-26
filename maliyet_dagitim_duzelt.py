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
#  ── HEDEFLİ MOD (--stoklar) ──
#    Otomatik gruplama ZAMANA bakar: aynı anda yazılmamış ya da farklı
#    fatura no ile girilmiş maliyetleri tek grup saymaz — bu yüzden bir
#    kısmı eşit kalabilir. Hangi kayıtların birlikte alındığını EN İYİ
#    SİZ bilirsiniz; o zaman stokları doğrudan verin:
#
#      venv/bin/python maliyet_dagitim_duzelt.py --stoklar K6461,K6462,K6463,K6464
#
#    Bu modda zaman penceresi YOKTUR. Verilen stokların bütün ek
#    maliyetleri, maliyet tipi + fatura no'ya göre gruplanır ve her grup
#    ölçüye göre yeniden paylaştırılır. Önce hepsi tek tek listelenir.
#
#  ── KULLANIM (proje klasöründe) ──
#      venv/bin/python maliyet_dagitim_duzelt.py            # otomatik rapor
#      venv/bin/python maliyet_dagitim_duzelt.py --uygula   # otomatik yaz
#      venv/bin/python maliyet_dagitim_duzelt.py --stoklar A,B,C           # hedefli rapor
#      venv/bin/python maliyet_dagitim_duzelt.py --stoklar A,B,C --uygula  # hedefli yaz
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
HEDEF_STOKLAR = []
for _a in sys.argv[1:]:
    if _a.startswith('--url='):
        os.environ['DATABASE_URL'] = _a.split('=', 1)[1]
    elif _a.startswith('--stoklar='):
        HEDEF_STOKLAR = [x.strip() for x in _a.split('=', 1)[1].split(',') if x.strip()]
# "--stoklar A,B,C" (esittir isareti olmadan) da kabul edilir
if '--stoklar' in sys.argv:
    _i = sys.argv.index('--stoklar')
    if _i + 1 < len(sys.argv) and not sys.argv[_i + 1].startswith('--'):
        HEDEF_STOKLAR = [x.strip() for x in sys.argv[_i + 1].split(',') if x.strip()]

if not os.environ.get('DATABASE_URL'):
    print('HATA: DATABASE_URL bulunamadı (.env okunamadı).')
    sys.exit(1)

os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
sys.path.insert(0, str(Path('.').resolve()))

import flask_app  # noqa: E402
from models import db, Maliyet, BlokStok, PlakaStok, EbatliStok  # noqa: E402

# Fatura no'su BOS olan kayitlar icin "ayni kaydetme islemi" sayilan sure.
# Ilk surumde 60 sn idi: kayitlar tek tek, dakikalar arayla girildiginde
# grup olusmuyor ve hicbiri duzeltilmiyordu. 15 dakika, elle girisi
# kapsayacak kadar genis; ayri gunlerde girilen maliyetleri birlestirecek
# kadar degil.
PENCERE_SN = 900
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
print(' MALİYET PAYLARI (MD1) — paylar ölçüye göre yeniden hesaplanır')
print('═' * 78)

with flask_app.app.app_context():
    # ── VERİLEN AD NE OLURSA OLSUN BUL ──
    # Stok ekranında görünen "K6461" KİMLİK DEĞİL, blok numarasıdır;
    # kayıt kimliği BLK-9A3F21 gibidir. İlk sürümde kimlik bekleniyordu
    # ve kullanıcı ekranda gördüğü numarayı yazınca betik "bu stokta
    # maliyet yok" diyordu — doğru ama işe yaramaz bir cevap.
    # Artık kimlik, blok no ve kasa no'nun üçü de kabul edilir.
    if HEDEF_STOKLAR:
        GIRILEN = list(HEDEF_STOKLAR)   # kullanicinin yazdigi hali (mesaj icin)
        cozulen, cozum_notu = [], []
        for ad in HEDEF_STOKLAR:
            eslesen = []
            for sinif in (BlokStok, PlakaStok, EbatliStok):
                st = sinif.query.get(ad)
                if st is not None:
                    eslesen = [st.id]
                    break
            if not eslesen:
                for sinif, alan in ((BlokStok, 'blok_no'), (PlakaStok, 'blok_no'),
                                    (EbatliStok, 'kasa_no')):
                    sutun = getattr(sinif, alan, None)
                    if sutun is None:
                        continue
                    for st in sinif.query.filter(
                            db.func.upper(sutun) == ad.upper()).all():
                        eslesen.append(st.id)
                if eslesen:
                    cozum_notu.append(f'{ad} → {len(eslesen)} kayıt '
                                      f'({", ".join(eslesen[:4])}'
                                      + (' …' if len(eslesen) > 4 else '') + ')')
            if eslesen:
                cozulen.extend(eslesen)
            else:
                cozum_notu.append(f'{ad} → BULUNAMADI (kimlik, blok no '
                                  f'ya da kasa no olarak eşleşmedi)')
        if cozum_notu:
            print(' ── VERİLEN NUMARALAR ──')
            for c in cozum_notu:
                print(f'   {c}')
            print()
        HEDEF_STOKLAR = list(dict.fromkeys(cozulen))   # sıra korunur, tekrar yok

    sorgu = Maliyet.query.filter(
        Maliyet.baglanti_tip == 'stok',
        Maliyet.aktif.is_(True))
    if HEDEF_STOKLAR:
        sorgu = sorgu.filter(Maliyet.baglanti_id.in_(HEDEF_STOKLAR))
    hepsi = sorgu.order_by(Maliyet.olusturma).all()

    # ── HEDEFLİ MODDA ÖNCE HER ŞEYİ GÖSTER ──
    # Otomatik mod bir grubu atladıysa nedenini ancak ham kayıtlara
    # bakarak anlarsınız: farklı maliyet tipi mi, farklı fatura no mu,
    # ayrı ayrı mı girilmiş. Tahmin etmek yerine yazdırıyoruz.
    if HEDEF_STOKLAR:
        print(f' Hedef stoklar: {", ".join(HEDEF_STOKLAR)}')
        bulunan = {m.baglanti_id for m in hepsi}
        yok = [x for x in HEDEF_STOKLAR if x not in bulunan]
        if yok:
            print(f' ⚠ Bu stoklarda hiç ek maliyet kaydı yok: {", ".join(yok)}')
        print()
        print(' ── MEVCUT EK MALİYET KAYITLARI ──')
        print(f'   {"blok/kasa":<12} {"kimlik":<16} {"maliyet tipi":<24} '
              f'{"fatura":<12} {"tutar":>13}  tarih')
        for m in sorted(hepsi, key=lambda x: (x.baglanti_id or '',
                                              x.maliyet_tip or '')):
            _t, _st = stok_bul(m.baglanti_id)
            _ad = (getattr(_st, 'blok_no', None) or getattr(_st, 'kasa_no', None)
                   or '—') if _st is not None else '—'
            print(f'   {str(_ad)[:12]:<12} {(m.baglanti_id or "")[:16]:<16} '
                  f'{(m.maliyet_tip or "")[:24]:<24} '
                  f'{(m.fatura_no or "—")[:12]:<12} '
                  f'{para(m.tutar):>13} {m.doviz or ""}  '
                  f'{m.olusturma.strftime("%d.%m %H:%M") if m.olusturma else "—"}')
        print()

    # ── Gruplama ──
    # Hedefli modda ZAMAN PENCERESİ YOK: kullanıcı hangi stokların
    # birlikte alındığını söylemiştir, tipi ve faturası aynı olan her
    # kayıt tek gruptur. Otomatik modda zaman penceresi kullanılır.
    kovalar = defaultdict(list)
    if HEDEF_STOKLAR:
        for m in hepsi:
            kovalar[((m.maliyet_tip or '', m.fatura_no or '', m.doviz or ''),
                     None)].append(m)
    else:
        for m in hepsi:
            anahtar_ust = (m.maliyet_tip or '', m.fatura_no or '', m.doviz or '')
            # AYNI FATURA NO = AYNI BELGE. Zaman penceresi aramaya gerek
            # yok: kayitlar gunler sonra girilmis olsa da tek faturadir.
            # Bu, ilk surumun en buyuk korlugu idi — tek tek girilen
            # maliyetler hic gruplanmiyordu.
            if m.fatura_no and m.fatura_no.strip():
                kovalar[(anahtar_ust, None)].append(m)
                continue
            if not m.olusturma:
                continue
            yerlesti = False
            for (ust, ilk_zaman), liste in kovalar.items():
                if ust != anahtar_ust or ilk_zaman is None:
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
        # Ayni stoga ayni tip+fatura ile iki kayit varsa gruplanamaz:
        # hangi payin hangisine ait oldugu belirsizdir.
        if len({m.baglanti_id for m in grup}) != len(grup):
            atlanan.append((ust, len(grup),
                            'aynı stokta aynı tip/faturadan birden çok kayıt'))
            continue
        tutarlar = [float(x.tutar or 0) for x in grup]
        # Hedefli modda EŞİTLİK ŞARTI ARANMAZ: kullanıcı bu stokların
        # birlikte alındığını söyledi; pay ölçüye göre olmalı, kayıt
        # şu an nasıl bölünmüş olursa olsun.
        if not HEDEF_STOKLAR and max(tutarlar) - min(tutarlar) > KURUS:
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
        if HEDEF_STOKLAR:
            print(' ✓ Bu stokların payları zaten ölçüyle uyumlu — '
                  'yapacak bir şey yok.')
        else:
            print(' ✓ Eşit bölünmüş maliyet grubu yok — yapacak bir şey yok.')
            print()
            print(' Buna rağmen ton başı maliyetler tutmuyorsa, birlikte alınan')
            print(' stokları doğrudan verin (zaman penceresi uygulanmaz):')
            print('   venv/bin/python maliyet_dagitim_duzelt.py --stoklar K1,K2,K3')
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
        print('   venv/bin/python maliyet_dagitim_duzelt.py'
              + (f' --stoklar {",".join(GIRILEN)}' if HEDEF_STOKLAR else '')
              + ' --uygula')
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

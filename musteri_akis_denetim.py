#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — MÜŞTERİ AKIŞ HARİTASI ve CARİ TUTARLILIK DENETİMİ
#
#  ── NE YAPAR ──
#    1) HARİTA: her müşteri için siparişleri, o siparişlere gelen
#       avansları, kesilen faturaları ve tahsilat durumunu tek ekranda
#       yan yana yazar. "Hangi müşterinin hangi siparişi var, hangisine
#       avans gelmiş, hangisine fatura kesilmiş" sorusunun cevabı.
#
#    2) DENETİM: cari kayıtların kendi içinde tutarlı olup olmadığını
#       ölçer. Aranan şey çöken kod değil, SESSİZ tutarsızlık:
#       faturası kesilmiş ama cariye borç işlenmemiş kayıt, tutarı
#       faturadan farklı hareket, fatura tarihi değişmiş ama cari
#       hareketi eski tarihte kalmış kayıt (25.09 öncesi düzenlemeler),
#       TL karşılığı kuruyla çarpışmayan hareket, iptal siparişte asılı
#       kalmış avans, kasaya girmemiş tahsilat…
#
#  ── HİÇBİR ŞEY DEĞİŞTİRMEZ ──  Yalnızca SELECT. Düzeltme önerir,
#     uygulamaz: her bulgunun altında ne yapılacağı yazar.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python musteri_akis_denetim.py                # harita + denetim
#      venv/bin/python musteri_akis_denetim.py --ozet         # yalnız denetim
#      venv/bin/python musteri_akis_denetim.py --musteri=STONE
#      venv/bin/python musteri_akis_denetim.py --tam          # hareketsiz cariler de
#      venv/bin/python musteri_akis_denetim.py --url="postgresql://..."
# ══════════════════════════════════════════════════════════════════════
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

if not Path('flask_app.py').exists():
    print("HATA: flask_app.py bu klasörde yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

SADECE_OZET = '--ozet' in sys.argv
TAM_LISTE = '--tam' in sys.argv
MUSTERI_SUZ = ''
for _a in sys.argv[1:]:
    if _a.startswith('--url='):
        os.environ['DATABASE_URL'] = _a.split('=', 1)[1]
    elif _a.startswith('--musteri='):
        MUSTERI_SUZ = _a.split('=', 1)[1]

_URL = os.environ.get('DATABASE_URL')
if not _URL:
    print("HATA: DATABASE_URL bulunamadı (.env okunamadı).")
    print("  Adres olmadan boş bir veritabanına bağlanıp yanlışlıkla")
    print("  'her şey yolunda' raporu verirdim. Çalışmayı reddediyorum.")
    sys.exit(1)

os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
sys.path.insert(0, str(Path('.').resolve()))

import flask_app  # noqa: E402,F401
from models import (db, Cari, CariHareket, Siparis, Proforma, Fatura,  # noqa: E402
                    KasaHareket, DovizKur, Cek)

# ── biçimlendirme ──────────────────────────────────────────────────────
KIRMIZI, SARI, MAVI, GRI, BITIR = '\033[91m', '\033[93m', '\033[96m', '\033[90m', '\033[0m'
if not sys.stdout.isatty():
    KIRMIZI = SARI = MAVI = GRI = BITIR = ''


def para(v, dv=''):
    try:
        s = f'{float(v or 0):,.2f}'.replace(',', '#').replace('.', ',').replace('#', '.')
    except (TypeError, ValueError):
        s = '0,00'
    return f'{s} {dv}'.strip()


def trh(d):
    return d.strftime('%d.%m.%Y') if d else '—'


def sade(s):
    s = (s or '').strip().lower()
    for a, b in (('ı', 'i'), ('İ', 'i'), ('ğ', 'g'), ('ü', 'u'),
                 ('ş', 's'), ('ö', 'o'), ('ç', 'c'), ('â', 'a')):
        s = s.replace(a, b)
    return ' '.join(s.split())


BULGULAR = []          # (seviye, kod, musteri, satir, oneri)
SEVIYE_SIRA = {'KRİTİK': 0, 'UYARI': 1, 'BİLGİ': 2}


def bulgu(seviye, kod, musteri, satir, oneri=''):
    BULGULAR.append((seviye, kod, musteri or '—', satir, oneri))


# ══════════════════════════════════════════════════════════════════════
#  VERİ
# ══════════════════════════════════════════════════════════════════════
with flask_app.app.app_context():
    cariler = Cari.query.all()
    siparisler = Siparis.query.all()
    proformalar = Proforma.query.all()
    faturalar = Fatura.query.all()
    hareketler = CariHareket.query.all()
    kasa_hrk = KasaHareket.query.filter(
        KasaHareket.baglanti_tip.in_(['cari_hareket', 'tahsilat'])).all()
    cekler = Cek.query.all()
    kurlar = defaultdict(dict)                       # {doviz: {tarih: alis}}
    for k in DovizKur.query.all():
        if k.alis:
            kurlar[(k.doviz or 'USD').upper()][k.tarih] = float(k.alis)

# ── kimlik çözümü: cari_id yoksa unvandan ──────────────────────────────
cari_id_ile = {c.id: c for c in cariler}
cari_unvan_ile = {}
for c in cariler:
    cari_unvan_ile.setdefault(sade(c.unvan), c)


def cari_coz(cari_id, unvan):
    if cari_id and cari_id in cari_id_ile:
        return cari_id_ile[cari_id]
    return cari_unvan_ile.get(sade(unvan))


def anahtar(cari_id, unvan):
    c = cari_coz(cari_id, unvan)
    return c.id if c else f'?{sade(unvan) or "bilinmeyen"}'


def ad(cari_id, unvan):
    c = cari_coz(cari_id, unvan)
    return c.unvan if c else (unvan or '(carisi olmayan kayıt)')


def kur_bul(doviz, tarih):
    """O tarihin TCMB alış kuru; o gün yoksa 7 gün geriye bakar."""
    dv = (doviz or 'USD').upper()
    if dv == 'TRY':
        return 1.0
    tablo = kurlar.get(dv) or {}
    if not tablo or not tarih:
        return None
    for i in range(0, 8):
        g = tarih.fromordinal(tarih.toordinal() - i)
        if g in tablo:
            return tablo[g]
    return None


# ── indeksler ─────────────────────────────────────────────────────────
sip_ile = {s.id: s for s in siparisler}
ftr_ile = {f.id: f for f in faturalar}
pf_ile = {p.id: p for p in proformalar}
kasa_bagli = {h.baglanti_id for h in kasa_hrk if h.baglanti_id}
cek_fatura = defaultdict(list)
for ck in cekler:
    if getattr(ck, 'fatura_id', None):
        cek_fatura[ck.fatura_id].append(ck)
cek_hareketleri = defaultdict(list)       # cek_id -> [hareket]

AVANS_TIPLERI = ('avans tahsilati', 'avans tahsilatı', 'avans odemesi',
                 'avans ödemesi', 'avans devri (giriş)', 'avans devri (çıkış)',
                 'avans devri (giris)', 'avans devri (cikis)')
# Kasaya bağlanması BEKLENEN tipler: para gerçekten el değiştirir.
# Avans DEVRİ bilerek dışarıda: devir, avansı bir siparişten diğerine
# taşır; kasaya para girip çıkmaz. Onu "kasasız" diye raporlamak
# doğru çalışan bir işlemi hata gibi gösterirdi.
NAKIT_TIPLERI = ('tahsilat', 'odeme', 'ödeme', 'avans tahsilati',
                 'avans tahsilatı', 'avans odemesi', 'avans ödemesi')

ftr_hareketleri = defaultdict(list)       # fatura_id -> [hareket]
avans_hrk = defaultdict(list)             # (cari_key, siparis_id) -> [hareket]
cari_hrk = defaultdict(list)              # cari_key -> [hareket]
yetim_hareket = []

for h in hareketler:
    ck = anahtar(h.cari_id, h.cari_unvan)
    cari_hrk[ck].append(h)
    tip = sade(h.islem_tip)
    if (h.baglanti_tip or '') == 'cek' and h.baglanti_id:
        cek_hareketleri[h.baglanti_id].append(h)
    if (h.baglanti_tip or '') == 'fatura' and h.baglanti_id:
        ftr_hareketleri[h.baglanti_id].append(h)
        if h.baglanti_id not in ftr_ile:
            yetim_hareket.append(h)
    # AVANS MAHSUBU DA AVANS HAREKETİDİR.
    # Ölçüldü: avansı faturaya mahsup edilmiş bir sipariş için betik
    # "avans hâlâ açık" uyarısı veriyordu — doğru çalışan bir işlemi
    # hata gibi gösteriyordu. Mahsup İKİ BACAKLI yazılır:
    #   • siparişe BORÇ  (avansı kapatır)   → siparis_id DOLU
    #   • faturaya ALACAK (borcu kapatır)   → siparis_id BOŞ
    # Yalnızca sipariş bacağı avans hesabına girer; fatura bacağı
    # girseydi net sıfırlanır ve mahsup hiç görünmezdi. Ayrım
    # islem_tip'ten değil KAYNAK'tan yapılır — islem_tip ileride
    # değişse de bağ kopmaz.
    _mahsup = (getattr(h, 'kaynak', '') or '').strip().lower() == 'avans_mahsup'
    if tip in AVANS_TIPLERI or (_mahsup and h.siparis_id):
        avans_hrk[(ck, h.siparis_id or None)].append(h)

sip_faturalari = defaultdict(list)
pf_faturalari = defaultdict(list)
for f in faturalar:
    if f.siparis_id:
        sip_faturalari[f.siparis_id].append(f)
    if f.proforma_id:
        pf_faturalari[f.proforma_id].append(f)

sip_proformalari = defaultdict(list)
for p in proformalar:
    if p.siparis_id:
        sip_proformalari[p.siparis_id].append(p)

musteri_siparisleri = defaultdict(list)
for s in siparisler:
    musteri_siparisleri[anahtar(s.cari_id, s.musteri)].append(s)

musteri_faturalari = defaultdict(list)
for f in faturalar:
    musteri_faturalari[anahtar(f.cari_id, f.musteri)].append(f)


def fatura_tahsilati(f):
    """Faturaya işlenmiş ödemelerin toplamı — tahsilat ekranıyla aynı
    mantık: faturaya bağlı alacak hareketleri + o faturaya bağlanmış
    çeklerin hareketleri.

    Döner: (toplam, capraz_doviz_var_mi). Fatura dövizinden FARKLI
    dövizde ödeme varsa çevrim yapılmaz ve o fatura için tutar
    karşılaştırması yapılmaz — yaklaşık bir kurla "fazla tahsilat"
    uyarısı üretmek, uyarı üretmemekten kötüdür.
    """
    f_dv = (f.doviz or 'USD').upper()
    top, capraz = 0.0, False
    gorulen = set()
    for h in ftr_hareketleri.get(f.id, []):
        if (h.alacak or 0) > 0:
            gorulen.add(h.id)
            if (h.doviz or f_dv).upper() == f_dv:
                top += float(h.alacak or 0)
            else:
                capraz = True
    for ck in cek_fatura.get(f.id, []):
        for h in cek_hareketleri.get(ck.id, []):
            if (h.alacak or 0) > 0 and h.id not in gorulen:
                if (h.doviz or f_dv).upper() == f_dv:
                    top += float(h.alacak or 0)
                else:
                    capraz = True
    return top, capraz


def borc_hareketleri(f):
    return [h for h in ftr_hareketleri.get(f.id, [])
            if (h.borc or 0) > 0 and sade(h.kaynak) in
            ('fatura', 'sicak_satis', 'fatura_kesim', 'manuel', '')]


def avans_net(ck, sip_id):
    """Sipariş için net avans (alacak − borç). + = müşteri avansı duruyor."""
    net, dv = 0.0, None
    for h in avans_hrk.get((ck, sip_id), []):
        net += float(h.alacak or 0) - float(h.borc or 0)
        dv = h.doviz or dv
    return net, (dv or 'USD')


# ══════════════════════════════════════════════════════════════════════
#  1 — MÜŞTERİ AKIŞ HARİTASI
# ══════════════════════════════════════════════════════════════════════
print('═' * 78)
print(' MÜŞTERİ AKIŞ HARİTASI ve CARİ TUTARLILIK DENETİMİ   (salt okunur)')
print('═' * 78)
print(f' {len(cariler)} cari · {len(siparisler)} sipariş · {len(proformalar)} proforma · '
      f'{len(faturalar)} fatura · {len(hareketler)} cari hareket')
print()

anahtarlar = set(list(musteri_siparisleri) + list(musteri_faturalari) + list(cari_hrk))
if MUSTERI_SUZ:
    s = sade(MUSTERI_SUZ)
    anahtarlar = {k for k in anahtarlar
                  if s in sade(cari_id_ile[k].unvan if k in cari_id_ile else k)}


def unvan_of(k):
    return cari_id_ile[k].unvan if k in cari_id_ile else k.lstrip('?').upper()


for k in sorted(anahtarlar, key=lambda x: sade(unvan_of(x))):
    c = cari_id_ile.get(k)
    sips = sorted(musteri_siparisleri.get(k, []),
                  key=lambda s: (s.siparis_tarihi or date.min))
    ftrs = musteri_faturalari.get(k, [])
    hrks = cari_hrk.get(k, [])
    if not (sips or ftrs or hrks) and not TAM_LISTE:
        continue

    # bakiye (döviz bazında)
    bakiye = defaultdict(lambda: [0.0, 0.0])
    for h in hrks:
        dv = (h.doviz or 'USD').upper()
        bakiye[dv][0] += float(h.borc or 0)
        bakiye[dv][1] += float(h.alacak or 0)

    if not SADECE_OZET:
        bas = unvan_of(k)
        ek = []
        if c:
            ek.append(c.cari_tip or '—')
            if c.ulke:
                ek.append(c.ulke)
            ek.append(c.para_birimi or 'USD')
        print(f'{MAVI}▌{bas}{BITIR}  {GRI}{" · ".join(ek)}{BITIR}')
        for dv, (b, a) in sorted(bakiye.items()):
            net = b - a
            yon = 'bizden alacaklı' if net < 0 else 'bize borçlu'
            print(f'   bakiye {dv}: borç {para(b)} · alacak {para(a)} · '
                  f'net {para(net)} ({yon})')
        if not c:
            print(f'   {KIRMIZI}cari kartı yok{BITIR} — bu kayıtlar bir cari hesaba bağlı değil')

    # ── siparişler ──
    for s in sips:
        net_avans, av_dv = avans_net(k, s.id)
        pfs = sip_proformalari.get(s.id, [])
        fts = sip_faturalari.get(s.id, [])
        if not SADECE_OZET:
            print(f'   ├ SİPARİŞ {s.id}  {trh(s.siparis_tarihi)} · {s.durum or "—"} · '
                  f'{para(s.toplam_tutar, s.doviz or "USD")}')
            av_say = len(avans_hrk.get((k, s.id), []))
            print(f'   │   avans   : {para(net_avans, av_dv)}'
                  f'{f" ({av_say} hareket)" if av_say else " — avans yok"}')
            print(f'   │   proforma: ' + (', '.join(f'{p.id} [{p.durum or "—"}]' for p in pfs)
                                          if pfs else '—'))
            if fts:
                for f in fts:
                    th, _cp = fatura_tahsilati(f)
                    print(f'   │   fatura  : {f.fatura_no or f.id} · {trh(f.fatura_tarihi)} · '
                          f'{f.durum} · {para(f.toplam, f.doviz)} · tahsil {para(th)}')
            else:
                print('   │   fatura  : —')

        # ── sipariş/avans denetimleri ──
        durum = (s.durum or '')
        if durum in ('Hazir', 'Teslim Edildi') and not fts:
            bulgu('UYARI', 'S1', unvan_of(k),
                  f'{s.id} siparişi "{durum}" ama faturası yok '
                  f'({para(s.toplam_tutar, s.doviz)})',
                  'Fatura kesilmediyse gelir kaydı ve cari borç da oluşmamıştır.')
        if durum == 'Iptal Edildi' and net_avans > 0.01:
            bulgu('KRİTİK', 'A2', unvan_of(k),
                  f'{s.id} siparişi iptal ama üzerinde {para(net_avans, av_dv)} avans duruyor',
                  'Avansı başka siparişe devredin ya da iade edin; yoksa cari '
                  'bakiyesi olmayan bir işe bağlı kalır.')
        if net_avans > 0.01 and float(s.toplam_tutar or 0) > 0 and \
                net_avans > float(s.toplam_tutar or 0) * 1.005:
            bulgu('UYARI', 'A3', unvan_of(k),
                  f'{s.id} avansı ({para(net_avans, av_dv)}) sipariş tutarını '
                  f'({para(s.toplam_tutar, s.doviz)}) aşıyor',
                  'Fazla tahsilat ya da yanlış siparişe işlenmiş avans olabilir.')
        if fts and net_avans > 0.01 and all(f.durum in ('Kesildi', 'Kismi Tahsil',
                                                        'Tahsil Edildi') for f in fts):
            bulgu('UYARI', 'A4', unvan_of(k),
                  f'{s.id} faturalandı ama {para(net_avans, av_dv)} avans hâlâ açık',
                  'Avansı faturaya mahsup edin; aksi halde hem avans hem borç '
                  'aynı anda bakiyede görünür.')
        if not cari_coz(s.cari_id, s.musteri):
            bulgu('UYARI', 'S3', unvan_of(k),
                  f'{s.id} siparişinin müşterisi cari kartlarında yok: "{s.musteri}"',
                  'Cari kartı açın ya da unvanı düzeltin; ekstre ve bakiye bu bağdan okunur.')

    # ── siparişe bağlı olmayan faturalar ──
    bagsiz = [f for f in ftrs if not f.siparis_id]
    if bagsiz and not SADECE_OZET:
        for f in bagsiz:
            th, _cp = fatura_tahsilati(f)
            print(f'   ├ FATURA (siparişsiz) {f.fatura_no or f.id} · {trh(f.fatura_tarihi)} · '
                  f'{f.durum} · {para(f.toplam, f.doviz)} · tahsil {para(th)}')

    # ── siparişe bağlı olmayan açık avans ──
    net_bagsiz, dv_bagsiz = avans_net(k, None)
    if abs(net_bagsiz) > 0.01:
        if not SADECE_OZET:
            print(f'   ├ AVANS (siparişe bağsız): {para(net_bagsiz, dv_bagsiz)}')
        bulgu('UYARI', 'A1', unvan_of(k),
              f'{para(net_bagsiz, dv_bagsiz)} avans hiçbir siparişe bağlı değil',
              'Avansı ilgili siparişe bağlayın; sipariş bazlı avans takibi ve '
              'devir bu alandan çalışıyor.')

    if not SADECE_OZET:
        print()

# ══════════════════════════════════════════════════════════════════════
#  2 — FATURA ↔ CARİ HAREKET TUTARLILIĞI
# ══════════════════════════════════════════════════════════════════════
for f in faturalar:
    mus = ad(f.cari_id, f.musteri)
    etiket = f'{f.fatura_no or f.id} ({f.id})'
    borclar = borc_hareketleri(f)
    kesilmis = f.durum in ('Kesildi', 'Kismi Tahsil', 'Tahsil Edildi')

    if kesilmis and not borclar:
        # Bağ kurulmamış ama ELLE girilmiş olabilir: aynı carideki
        # borç hareketlerinde evrak no fatura numarasıyla eşleşiyor mu?
        # Eşleşiyorsa bakiye doğrudur, yalnızca bağ eksiktir — bunu
        # "borç işlenmemiş" diye raporlamak yanlış alarm olur.
        elle = [h for h in cari_hrk.get(anahtar(f.cari_id, f.musteri), [])
                if (h.borc or 0) > 0 and not h.baglanti_id
                and f.fatura_no and sade(h.evrak_no) == sade(f.fatura_no)]
        if elle:
            bulgu('BİLGİ', 'F1b', mus,
                  f'{etiket} borcu elle girilmiş görünüyor ({elle[0].id}) — '
                  'faturayla bağı yok',
                  'Bakiye doğru ama fatura ekranındaki tahsilat takibi bu '
                  'hareketi görmez.')
        else:
            bulgu('KRİTİK', 'F1', mus,
                  f'{etiket} kesilmiş ama cariye borç işlenmemiş '
                  f'({para(f.toplam, f.doviz)})',
                  'Cari bakiyesi bu fatura kadar eksik. Faturayı iptal edip yeniden '
                  'kesmek ya da cariye elle borç hareketi girmek gerekir.')
    if f.durum == 'Iptal' and borclar:
        bulgu('KRİTİK', 'F8', mus,
              f'{etiket} İPTAL ama cari hareketi duruyor ({para(f.toplam, f.doviz)})',
              'İptal borcu geri almalıydı; hareket silinmeli, yoksa müşteri '
              'olmayan bir borçla görünür.')
    if len(borclar) > 1:
        bulgu('KRİTİK', 'F7', mus,
              f'{etiket} için {len(borclar)} ayrı borç hareketi var '
              f'({", ".join(h.id for h in borclar)})',
              'Çift kayıt: cari bakiyesi fatura tutarının katı kadar şişmiş.')

    for h in borclar:
        f_top = float(f.toplam or 0)
        h_top = float(h.borc or 0)
        if abs(f_top - h_top) > 0.02:
            bulgu('KRİTİK', 'F2', mus,
                  f'{etiket} tutarı {para(f_top, f.doviz)} ama cari hareketi '
                  f'{para(h_top, h.doviz)} ({h.id})',
                  'Fatura 25.09 öncesinde düzenlenmiş olabilir. Faturayı açıp '
                  'kaydedin: yeni sürüm tutarı cariye de işler.')
        if f.fatura_tarihi and h.hareket_tarihi and f.fatura_tarihi != h.hareket_tarihi:
            bulgu('UYARI', 'F3', mus,
                  f'{etiket} fatura tarihi {trh(f.fatura_tarihi)} ama cari hareketi '
                  f'{trh(h.hareket_tarihi)} tarihinde',
                  'Ekstre ve yaşlandırma eski tarihi gösterir; TL karşılığı da o '
                  'günün kurundan hesaplanmıştır. Faturayı açıp kaydedin.')
        if (f.vade_tarihi or None) != (h.vade_tarihi or None):
            bulgu('UYARI', 'F4', mus,
                  f'{etiket} vadesi {trh(f.vade_tarihi)} ama cari hareketinde '
                  f'{trh(h.vade_tarihi)}',
                  'Vadesi geçen raporu hareketteki vadeden okunur.')
        # TL karşılığı kuruyla tutuyor mu
        kur = float(h.kur_uygulanan or 0)
        tl = float(h.borc_try or 0)
        if kur > 0 and h_top > 0:
            beklenen = h_top * kur if (h.doviz or 'USD').upper() != 'TRY' else h_top
            if abs(beklenen - tl) > max(1.0, beklenen * 0.001):
                bulgu('KRİTİK', 'F5', mus,
                      f'{etiket} TL karşılığı tutmuyor: {para(h_top, h.doviz)} × '
                      f'{kur:,.4f} = {para(beklenen)} ₺ ama kayıtta {para(tl)} ₺',
                      'Ekstrenin TL sütunu ve TL bakiyesi yanlış çıkar.')
        if kur <= 0 and (h.doviz or 'USD').upper() != 'TRY':
            bulgu('UYARI', 'F6', mus, f'{etiket} cari hareketinde kur yok (0)',
                  'TL karşılığı hesaplanamaz; kur arşivini doldurup hareketi güncelleyin.')
        elif (h.kur_kaynak or 'TCMB') != 'MANUEL' and f.fatura_tarihi:
            tcmb = kur_bul(f.doviz, f.fatura_tarihi)
            if tcmb and kur > 0 and abs(tcmb - kur) > max(0.01, tcmb * 0.002):
                bulgu('UYARI', 'F6', mus,
                      f'{etiket} kuru {kur:,.4f} ama {trh(f.fatura_tarihi)} TCMB '
                      f'alışı {tcmb:,.4f} (kaynak: {h.kur_kaynak or "TCMB"})',
                      'Sözleşme kuruysa faturaya "Sözleşme Kuru" olarak girin; '
                      'böylece neden farklı olduğu kayıtta durur.')

    # tahsilat ↔ durum
    th, capraz = fatura_tahsilati(f)
    top = float(f.toplam or 0)
    if capraz:
        bulgu('BİLGİ', 'F13', mus,
              f'{etiket} faturasına farklı dövizde ödeme işlenmiş — tahsilat '
              'karşılaştırması bu fatura için atlandı',
              'Çapraz dövizli kapatma sistemde destekleniyor; burada yaklaşık '
              'kurla yanlış uyarı üretmemek için ölçülmedi.')
    if not capraz and th > top + 0.02 and f.durum != 'Iptal':
        bulgu('KRİTİK', 'F10', mus,
              f'{etiket} tahsilatı ({para(th, f.doviz)}) fatura tutarını '
              f'({para(top, f.doviz)}) aşıyor',
              'Fazla tahsilat avans olarak ayrılmalı ya da yanlış faturaya '
              'işlenmiş ödeme düzeltilmeli.')
    if not capraz and f.durum == 'Tahsil Edildi' and th + 0.02 < top:
        bulgu('UYARI', 'F11', mus,
              f'{etiket} "Tahsil Edildi" ama {para(top - th, f.doviz)} açık görünüyor',
              'Durum ile tahsilat kayıtları ayrışmış.')
    if not capraz and f.durum == 'Kesildi' and top > 0 and th >= top - 0.02:
        bulgu('BİLGİ', 'F11', mus,
              f'{etiket} tamamı tahsil edilmiş ama durumu hâlâ "Kesildi"',
              'Durumu "Tahsil Edildi" yapabilirsiniz.')
    if not cari_coz(f.cari_id, f.musteri):
        bulgu('KRİTİK', 'F12', mus,
              f'{etiket} faturasının müşterisi cari kartlarında yok: "{f.musteri}"',
              'Bu fatura hiçbir cari ekstresinde görünmez.')

for h in yetim_hareket:
    bulgu('KRİTİK', 'F9', ad(h.cari_id, h.cari_unvan),
          f'{h.id} hareketi silinmiş/olmayan bir faturaya bağlı '
          f'({h.baglanti_id}) · {para(h.borc or h.alacak, h.doviz)}',
          'Bakiyeyi etkiliyor ama dayanağı yok — incelenip silinmeli.')

# ── nakit hareketleri kasaya bağlı mı ──
for h in hareketler:
    if sade(h.islem_tip) in NAKIT_TIPLERI and h.id not in kasa_bagli:
        bulgu('UYARI', 'K1', ad(h.cari_id, h.cari_unvan),
              f'{h.id} · {trh(h.hareket_tarihi)} · {h.islem_tip} · '
              f'{para(h.borc or h.alacak, h.doviz)} kasaya bağlı değil',
              'Cari bakiyesi değişti ama para hiçbir kasada görünmüyor.')

# ── avans devirleri dengeli mi ──
devir = defaultdict(float)
for h in hareketler:
    t = sade(h.islem_tip)
    if t.startswith('avans devri'):
        devir[anahtar(h.cari_id, h.cari_unvan)] += float(h.alacak or 0) - float(h.borc or 0)
for k, net in devir.items():
    if abs(net) > 0.02:
        bulgu('KRİTİK', 'A5', unvan_of(k),
              f'avans devirleri dengesiz: net {para(net)} '
              '(giriş ve çıkış birbirini götürmeli)',
              'Devrin bir bacağı eksik ya da elle silinmiş; bakiye bu kadar kaymış.')

# ── proforma ↔ fatura ──
for p in proformalar:
    fts = pf_faturalari.get(p.id, [])
    aktif = [f for f in fts if f.durum != 'Iptal']
    if (p.durum or '') == 'Faturalandi' and not aktif:
        bulgu('UYARI', 'P1', ad(p.cari_id, p.musteri),
              f'{p.id} proforması "Faturalandı" ama bağlı aktif fatura yok',
              'Fatura iptal edilmiş olabilir; proforma durumu geri alınmalı.')
    if len(aktif) > 1:
        bulgu('KRİTİK', 'P2', ad(p.cari_id, p.musteri),
              f'{p.id} proformasından {len(aktif)} aktif fatura kesilmiş '
              f'({", ".join(f.fatura_no or f.id for f in aktif)})',
              'Aynı mal iki kez faturalanmış olabilir — cari borcu iki katı.')

# ── cari kartındaki para birimi ile hareketlerin dövizi ──
for c in cariler:
    hrk_dv = {(h.doviz or '').upper() for h in cari_hrk.get(c.id, []) if h.doviz}
    kart_dv = (c.para_birimi or '').upper()
    if kart_dv and hrk_dv and kart_dv not in hrk_dv:
        bulgu('BİLGİ', 'G1', c.unvan,
              f'cari kartı {kart_dv} ama hareketleri {", ".join(sorted(hrk_dv))}',
              'Formlarda varsayılan döviz kart üzerinden geliyor; kartı '
              'gerçekte çalıştığınız dövize çekmek yanlış girişleri azaltır.')

# ── risk limiti ──
for c in cariler:
    limit = float(getattr(c, 'risk_limiti', 0) or 0)
    if limit <= 0:
        continue
    net = sum(float(h.borc or 0) - float(h.alacak or 0) for h in cari_hrk.get(c.id, []))
    if net > limit:
        bulgu('BİLGİ', 'R1', c.unvan,
              f'bakiyesi {para(net)} · risk limiti {para(limit)} — limit aşılmış',
              'Yeni sevkiyat öncesi tahsilat ya da limit güncellemesi.')

# ══════════════════════════════════════════════════════════════════════
#  3 — BULGULAR
# ══════════════════════════════════════════════════════════════════════
print('═' * 78)
print(' TUTARLILIK BULGULARI')
print('═' * 78)

if MUSTERI_SUZ:
    s = sade(MUSTERI_SUZ)
    BULGULAR[:] = [b for b in BULGULAR if s in sade(b[2])]

if not BULGULAR:
    print(' ✓ Tutarsızlık bulunamadı — fatura, avans ve cari hareketler örtüşüyor.')
else:
    BULGULAR.sort(key=lambda b: (SEVIYE_SIRA.get(b[0], 3), b[1], sade(b[2])))
    sayac = defaultdict(int)
    for sev, kod, mus, satir, oneri in BULGULAR:
        sayac[sev] += 1
    print(' ' + ' · '.join(f'{s}: {sayac[s]}' for s in ('KRİTİK', 'UYARI', 'BİLGİ')
                           if sayac[s]))
    print()
    onceki = None
    for sev, kod, mus, satir, oneri in BULGULAR:
        renk = {'KRİTİK': KIRMIZI, 'UYARI': SARI}.get(sev, GRI)
        if (sev, kod) != onceki:
            print(f'{renk}── {sev} · {kod}{BITIR}')
            onceki = (sev, kod)
        print(f'   {mus}')
        print(f'     {satir}')
        if oneri:
            print(f'     {GRI}→ {oneri}{BITIR}')
    print()
    print(' Kodlar: F=fatura/cari · A=avans · S=sipariş · P=proforma · '
          'K=kasa · R=risk')

print('═' * 78)
print(' Bu betik hiçbir kaydı değiştirmedi.')
print('═' * 78)

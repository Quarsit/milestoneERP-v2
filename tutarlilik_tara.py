#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUTARLILIK TARAMASI — SALT OKUNUR
====================================================================

Maliyet, stok alışı ve tedarikçi cari hareketleri BİRBİRİNİ TUTUYOR
MU diye bakar. Her denetim ya "✓" der ya da tutmayan satırları
tek tek listeler.

  A · MALİYET FATURASI KENDİ İÇİNDE
      A1  aynı faturanın (grubun) satırları aynı tarihte mi
      A2  dolar karşılığı var mı; USD satırda tutara eşit mi
      A3  bağlandığı stok / sipariş gerçekten var mı
  B · MALİYET ↔ CARİ BORÇ
      B1  borcun tarihi = maliyetin tarihi
      B2  borcun tutarı = faturanın satır toplamı (gider + KDV)
      B3  borcun dövizi = faturanın dövizi
      B4  hiçbir maliyete bağlı olmayan borç (BAĞSIZ)
  C · STOK ALIŞ FATURASI
      C1  aynı faturadaki stokların alış tarihi = borcun tarihi
      C2  alışın KDV satırının tarihi = alış tarihi
      C3  borcun tutarı = stokların matrah + KDV toplamı
      C4  borçtaki kalem sayısı = stok sayısı
      C6  stok kartındaki fiyat × ölçü = kayıtlı matrah
  D · TL KARŞILIĞI VE KUR
      D1  TL karşılığı = tutar × yazılan kur
      D2  yazılan kur, o günün (ya da bir önceki günün) arşiv
          kuruyla uyuşuyor mu
  E · PROFORMA / REZERVASYON
      E1  güncel sürümü kalmamış revize arşivi
      E2  kaybedilmiş / iptal tekliflere bağlı AÇIK rezervasyon
  F · BİLGİ: 06.11.2026 tarihinde kalan kayıtlar

NE YAPMAZ: HİÇBİR ŞEY YAZMAZ, SİLMEZ, DEĞİŞTİRMEZ. Yalnız okur.
"⚠" bir HATA KANITI değil, bakılması gereken satırdır; açıklaması
yanında yazar.

Kullanım (PROJE DİZİNİNDE — `.env`i burada arıyor):
    cd ~/milestoneERP-v2 && venv/bin/python tutarlilik_tara.py
"""
import io
import os
import sys
from collections import defaultdict

KOK = os.path.dirname(os.path.abspath(__file__)) or '.'

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(KOK, '.env'))
except Exception:
    yol = os.path.join(KOK, '.env')
    if os.path.exists(yol):
        for satir in io.open(yol, encoding='utf-8'):
            satir = satir.strip()
            if not satir or satir.startswith('#') or '=' not in satir:
                continue
            ad, _, deger = satir.partition('=')
            os.environ.setdefault(ad.strip(), deger.strip().strip('"\''))

URL = os.environ.get('DATABASE_URL')
if not URL:
    print('✗ DATABASE_URL okunamadı.')
    print('  Bu betik .env dosyasını KENDİ BULUNDUĞU klasörde arıyor;')
    print('  proje dizinine kopyalayıp oradan çalıştır.')
    sys.exit(1)
try:
    from sqlalchemy import create_engine, text
except ImportError:
    print('✗ sqlalchemy bulunamadı — venv/bin/python ile çalıştır.')
    sys.exit(1)

motor = create_engine(URL)
KDV_TIPLERI = ('Devreden KDV', 'Iade KDV')
ESKI_GUN = '2026-11-06'
KURUS = 0.05          # yuvarlama payı


def f(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def gun(v):
    return str(v or '')[:10]


def s(v, n):
    v = '' if v is None else str(v)
    return (v[:n - 1] + '…') if len(v) > n else v.ljust(n)


def para(v, dv=''):
    return f'{f(v):,.2f} {dv or ""}'.strip()


def oku(b, sorgu, **p):
    return [dict(r) for r in b.execute(text(sorgu), p).mappings().all()]


with motor.connect() as b:
    mal = oku(b, "SELECT id, maliyet_tip, baglanti_tip, baglanti_id, tutar, "
                 "doviz, usd_karsilik, fatura_no, grup_id, maliyet_tarihi "
                 "FROM maliyetler WHERE aktif = :t", t=True)
    har = oku(b, "SELECT id, cari_id, cari_unvan, islem_tip, baglanti_tip, "
                 "baglanti_id, evrak_no, borc, alacak, doviz, hareket_tarihi, "
                 "kur_uygulanan, borc_try, alacak_try, kalem_sayisi, kaynak "
                 "FROM cari_hareket")
    stok = []
    for tablo, ad in (('blok_stok', 'BLOK'), ('plaka_stok', 'PLAKA'),
                      ('ebatli_stok', 'EBATLI')):
        _olcu = ("tonaj, hacim_m3, 0 AS metraj_m2" if ad == 'BLOK'
                 else "0 AS tonaj, 0 AS hacim_m3, metraj_m2")
        for r in oku(b, f"SELECT id, uretici, cari_id, fatura_no, alis_tarihi, "
                        f"matrah, kdv_tutar, doviz, durum, kaynak, alis_fiyati, "
                        f"alis_fiyat_birim, {_olcu} FROM {tablo}"):
            r['tip'] = ad
            stok.append(r)
    kurlar = oku(b, "SELECT tarih, doviz, alis, satis, efektif FROM doviz_kur")
    siparis_id = {r['id'] for r in oku(b, "SELECT id FROM siparis_kayit")}
    prof = oku(b, "SELECT id, durum, ana_pi_id, aktif_surum, siparis_id "
                  "FROM proforma")
    rez = oku(b, "SELECT id, proforma_id, stok_id, stok_tip, iptal_nedeni "
                 "FROM rezervasyon")

stok_id = {r['id']: r for r in stok}
mal_id = {m['id']: m for m in mal}
grup = defaultdict(list)
for m in mal:
    grup[m['grup_id'] or m['id']].append(m)
h_mal = defaultdict(list)          # grup anahtarı → cari hareketler
bagsiz = []
for h in har:
    if h['baglanti_tip'] != 'maliyet':
        continue
    m = mal_id.get(h['baglanti_id'])
    if m is None:
        bagsiz.append(h)
    else:
        h_mal[m['grup_id'] or m['id']].append(h)

sorun = 0


def bolum(ad):
    print('\n' + ad)
    print('─' * 78)


def sonuc(kod, baslik, satirlar, aciklama=''):
    global sorun
    if not satirlar:
        print(f'  ✓ {kod} {baslik}')
        return
    sorun += len(satirlar)
    print(f'  ⚠ {kod} {baslik}: {len(satirlar)}')
    if aciklama:
        print(f'       {aciklama}')
    for x in satirlar[:40]:
        print('       · ' + x)
    if len(satirlar) > 40:
        print(f'       … ve {len(satirlar) - 40} satır daha')


def fatura_adi(g):
    m = g[0]
    return f'{s(m["fatura_no"] or "(faturasız)", 20)} {s(m["maliyet_tip"], 24)}'


print('=' * 78)
print('  TUTARLILIK TARAMASI · salt okunur')
print(f'  {len(mal)} maliyet satırı · {len(grup)} maliyet faturası · '
      f'{len(stok)} stok · {len(har)} cari hareket')
print('=' * 78)

# ══ A ═════════════════════════════════════════════════════════════
bolum('A · MALİYET FATURASI KENDİ İÇİNDE')
a1 = []
for gk, g in grup.items():
    t = sorted({gun(m['maliyet_tarihi']) for m in g})
    if len(t) > 1:
        a1.append(f'{fatura_adi(g)} tarihler: {", ".join(t)}')
sonuc('A1', 'faturanın satırları aynı tarihte', a1,
      'Aynı belgenin gideri ile KDV satırı farklı günlerde.')
a2 = []
for m in mal:
    if f(m['tutar']) and not f(m['usd_karsilik']):
        a2.append(f'{s(m["id"], 18)} {s(m["maliyet_tip"], 24)} '
                  f'{para(m["tutar"], m["doviz"])} → dolar karşılığı BOŞ')
    elif (m['doviz'] == 'USD'
          and abs(f(m['tutar']) - f(m['usd_karsilik'])) > KURUS):
        a2.append(f'{s(m["id"], 18)} {s(m["maliyet_tip"], 24)} '
                  f'{para(m["tutar"], "USD")} ≠ {para(m["usd_karsilik"], "USD")}')
sonuc('A2', 'dolar karşılıkları dolu', a2,
      'Stok maliyeti dolar karşılığından hesaplanır.')
a3 = []
for m in mal:
    bt, bid = (m['baglanti_tip'] or '').lower(), m['baglanti_id']
    if bt == 'stok' and bid and bid not in stok_id:
        a3.append(f'{s(m["id"], 18)} {s(m["maliyet_tip"], 24)} stok {bid} YOK')
    elif bt == 'siparis' and bid and bid not in siparis_id:
        a3.append(f'{s(m["id"], 18)} {s(m["maliyet_tip"], 24)} sipariş {bid} YOK')
sonuc('A3', 'bağlandığı stok / sipariş duruyor', a3,
      'Maliyet, silinmiş bir kayda bağlı kalmış.')

# ══ B ═════════════════════════════════════════════════════════════
bolum('B · MALİYET ↔ CARİ BORÇ')
b1, b2, b3 = [], [], []
borclu_fatura = 0
for gk, hl in h_mal.items():
    g = grup[gk]
    borclu_fatura += 1
    mt = sorted({gun(m['maliyet_tarihi']) for m in g})
    for h in hl:
        if gun(h['hareket_tarihi']) not in mt:
            b1.append(f'{fatura_adi(g)} maliyet {", ".join(mt)} · borç '
                      f'{gun(h["hareket_tarihi"])} · {s(h["cari_unvan"], 22)}')
    net = sum(f(h['alacak']) - f(h['borc']) for h in hl)
    top = sum(f(m['tutar']) for m in g)
    if abs(net - top) > KURUS:
        b2.append(f'{fatura_adi(g)} satırlar {para(top, g[0]["doviz"])} · '
                  f'borç {para(net, hl[0]["doviz"])} · '
                  f'{s(hl[0]["cari_unvan"], 22)}')
    dv = {m['doviz'] for m in g} | {h['doviz'] for h in hl}
    if len(dv) > 1:
        b3.append(f'{fatura_adi(g)} dövizler: {", ".join(sorted(map(str, dv)))}')
sonuc('B1', f'borcun tarihi = maliyetin tarihi ({borclu_fatura} fatura)', b1,
      'Cari ekstresi faturayı başka günde gösteriyor.')
sonuc('B2', 'borcun tutarı = faturanın satır toplamı', b2,
      'Tedarikçiye yazılan borç, maliyet satırlarının toplamını tutmuyor.')
sonuc('B3', 'borcun dövizi = faturanın dövizi', b3)
sonuc('B4', 'her maliyet borcu bir maliyete bağlı',
      [f'{s(h["cari_unvan"], 26)} {s(h["evrak_no"] or "—", 18)} '
       f'{para(f(h["alacak"]) - f(h["borc"]), h["doviz"])} · '
       f'{gun(h["hareket_tarihi"])} · {h["id"]}' for h in bagsiz],
      'Eski "Bloğa Dağıt" kayıtları ya da maliyeti silinmiş borçlar. '
      'Maliyet düzeltmeleri bunlara yansımaz.')

# ══ C ═════════════════════════════════════════════════════════════
bolum('C · STOK ALIŞ FATURASI')
sf = defaultdict(list)             # (fatura_no, cari_id) → hareketler
for h in har:
    # Yalnız ALIŞIN KENDİ kayıtları: alış faturası ve stok çıkışının
    # karşı kaydı. Faturaya bağlanmış ÖDEME de aynı bağı taşıyor;
    # onu saymak "borç tutmuyor" diye yanlış alarm veriyordu
    # (ALB20260905: 9.898,52 alış + 9.900 ödeme = −1,48).
    if (h['baglanti_tip'] == 'stok_fatura' and h['baglanti_id']
            and (h['kaynak'] or '') in ('stok', 'stok_karsi_kayit')):
        sf[(h['baglanti_id'], h['cari_id'])].append(h)
stok_f = defaultdict(list)
for r in stok:
    if r['fatura_no']:
        stok_f[(r['fatura_no'], r['cari_id'])].append(r)
c1, c3, c4, c0 = [], [], [], []
for (fno, cid), hl in sf.items():
    sl = stok_f.get((fno, cid), [])
    if not sl and sum(1 for (f2, _c) in sf if f2 == fno) == 1:
        # Eski stok kartlarında cari kimliği boş olabilir; fatura
        # numarası tek bir cariye aitse numarayla eşle.
        sl = [r for r in stok if r['fatura_no'] == fno and not r['cari_id']]
    ad = f'{s(fno, 20)} {s(hl[0]["cari_unvan"], 26)}'
    net = sum(f(h['alacak']) - f(h['borc']) for h in hl)
    if not sl:
        if abs(net) > KURUS:
            c0.append(f'{ad} borç {para(net, hl[0]["doviz"])} · stok YOK')
        continue
    ht = sorted({gun(h['hareket_tarihi']) for h in hl
                 if f(h['alacak']) > 0}) or sorted(
        {gun(h['hareket_tarihi']) for h in hl})
    st = sorted({gun(r['alis_tarihi']) for r in sl})
    if st != ht and not (len(ht) > 1 and set(st) <= set(ht)):
        c1.append(f'{ad} stok alış {", ".join(st)} · borç {", ".join(ht)}')
    top = sum(f(r['matrah']) + f(r['kdv_tutar']) for r in sl)
    if top > 0 and abs(net - top) > max(KURUS, 0.0005 * top):
        c3.append(f'{ad} stoklar {para(top, sl[0]["doviz"])} · '
                  f'borç {para(net, hl[0]["doviz"])}')
    ks = sum(int(h['kalem_sayisi'] or 0) for h in hl if f(h['alacak']) > 0)
    if len(hl) == 1 and ks and ks != len(sl):
        c4.append(f'{ad} borçta {ks} kalem · {len(sl)} stok')
sonuc('C1', f'stok alış tarihi = borcun tarihi ({len(sf)} alış faturası)', c1,
      'Alış tarihi stok kartında bir gün, cari ekstresinde başka gün.')
c2 = []
for m in mal:
    if (m['maliyet_tip'] in KDV_TIPLERI and not m['grup_id']
            and (m['baglanti_tip'] or '').lower() == 'stok'):
        r = stok_id.get(m['baglanti_id'])
        if r and (r['fatura_no'] or '') == (m['fatura_no'] or '') \
                and gun(r['alis_tarihi']) != gun(m['maliyet_tarihi']):
            c2.append(f'{s(m["fatura_no"] or "—", 20)} {s(r["id"], 22)} alış '
                      f'{gun(r["alis_tarihi"])} · KDV satırı '
                      f'{gun(m["maliyet_tarihi"])}')
sonuc('C2', 'alışın KDV satırı alış tarihinde', c2,
      'KDV başka döneme, alış başka döneme düşüyor.')
sonuc('C3', 'borcun tutarı = stokların matrah + KDV toplamı', c3,
      'Sonradan tedarikçi/fiyat düzeltmesi yapılmış faturalarda fark '
      'olağan olabilir; karşı kayıt varsa ekstrede görünür.')
sonuc('C4', 'borçtaki kalem sayısı = stok sayısı', c4)
sonuc('C5', 'alış borcunun stoğu duruyor', c0,
      'Stoklar silinmiş ya da fatura numarası değişmiş; borç açıkta.')
c6 = []
for r in stok:
    if (r.get('kaynak') or 'satinalma') in ('uretim', 'kesim'):
        continue
    fy, fb = f(r['alis_fiyati']), (r['alis_fiyat_birim'] or '')
    if r['tip'] == 'BLOK':
        mik = f(r['tonaj']) if fb == 'ton' else f(r['hacim_m3'])
    else:
        mik = f(r['metraj_m2']) * (1 if fb in ('', 'm2') else 10.7639)
    beklenen = round(fy * mik, 2)
    if not fy or not mik or not f(r['matrah']):
        continue
    if abs(beklenen - f(r['matrah'])) > max(0.05, 0.0005 * beklenen):
        c6.append(f'{s(r["id"], 24)} kartta {fy:g} × {mik:g} = '
                  f'{para(beklenen, r["doviz"])} · kayıtlı matrah '
                  f'{para(r["matrah"], r["doviz"])}')
sonuc('C6', 'stok kartındaki fiyat × ölçü = kayıtlı matrah', c6,
      'Fiyat ya da ölçü sonradan değişmiş ama alış bedeli ve '
      'tedarikçi borcu eski rakamda kalmış olabilir (HD1 öncesi).')

# ══ D ═════════════════════════════════════════════════════════════
bolum('D · TL KARŞILIĞI VE KUR (maliyet ve stok alış borçları)')
kur_gunleri = defaultdict(dict)    # doviz → {gun: (alis, satis, efektif)}
for k in kurlar:
    kur_gunleri[k['doviz']][gun(k['tarih'])] = [
        f(k['alis']), f(k['satis']), f(k['efektif'])]
sirali = {dv: sorted(g) for dv, g in kur_gunleri.items()}


def arsiv_kurlari(dv, g):
    """O günün ve ondan önceki son günün kurları."""
    gunler = sirali.get(dv, [])
    aday = [x for x in gunler if x <= g][-2:]
    return [v for x in aday for v in kur_gunleri[dv][x] if v]


d1, d2, d_arsivsiz = [], [], 0
for h in har:
    if h['baglanti_tip'] not in ('maliyet', 'stok_fatura'):
        continue
    tutar = f(h['alacak']) or f(h['borc'])
    tl = f(h['alacak_try']) or f(h['borc_try'])
    kur = f(h['kur_uygulanan'])
    dv = h['doviz'] or ''
    if not tutar:
        continue
    ad = (f'{s(h["cari_unvan"], 24)} {s(h["evrak_no"] or "—", 18)} '
          f'{gun(h["hareket_tarihi"])} {para(tutar, dv)}')
    if dv in ('TRY', 'TL'):
        if tl and abs(tl - tutar) > KURUS:
            d1.append(f'{ad} · TL karşılığı {para(tl)} (TL faturada eşit olmalı)')
        continue
    if not tl or not kur:
        d1.append(f'{ad} · TL karşılığı / kur BOŞ')
        continue
    if abs(tl - tutar * kur) > max(1.0, 0.001 * tl):
        d1.append(f'{ad} · {para(tl)} TL ≠ tutar × {kur:.4f}')
    arsiv = arsiv_kurlari(dv, gun(h['hareket_tarihi']))
    if not arsiv:
        d_arsivsiz += 1
    elif min(abs(kur - a) / a for a in arsiv) > 0.003:
        d2.append(f'{ad} · yazılan kur {kur:.4f} · arşiv '
                  f'{min(arsiv):.4f}–{max(arsiv):.4f}')
sonuc('D1', 'TL karşılığı = tutar × yazılan kur', d1)
sonuc('D2', 'yazılan kur o günün arşiv kuruyla uyuşuyor', d2,
      'Tarihi sonradan değişmiş ama TL karşılığı eski günün kurunda '
      'kalmış olabilir. Elle kur girilmiş hareketlerde olağandır.')
if d_arsivsiz:
    print(f'       (bilgi: {d_arsivsiz} hareketin günü için kur arşivinde '
          f'kayıt yok; karşılaştırılamadı)')

# ══ E ═════════════════════════════════════════════════════════════
bolum('E · PROFORMA / REZERVASYON')
prof_id = {p['id']: p for p in prof}
aktif_kok = {(p['ana_pi_id'] or p['id']) for p in prof
             if p['aktif_surum'] is not False and p['aktif_surum'] != 0}
e1 = [f'{s(p["id"], 28)} kök {p["ana_pi_id"] or p["id"]}' for p in prof
      if (p['aktif_surum'] is False or p['aktif_surum'] == 0)
      and (p['ana_pi_id'] or p['id']) not in aktif_kok]
sonuc('E1', 'her revize arşivinin güncel sürümü var', e1,
      'Güncel sürümü silinmiş eski sürümler; listede görünmezler.')
e2 = []
for r in rez:
    if r['iptal_nedeni'] or not r['proforma_id']:
        continue
    p = prof_id.get(r['proforma_id'])
    if p is None:
        e2.append(f'{s(r["id"], 18)} stok {s(r["stok_id"], 22)} '
                  f'proforma {r["proforma_id"]} YOK')
    elif p['durum'] in ('Kaybedildi', 'Iptal') and not p['siparis_id']:
        st = stok_id.get(r['stok_id'])
        e2.append(f'{s(r["id"], 18)} stok {s(r["stok_id"], 22)} '
                  f'({(st or {}).get("durum", "?")}) · {p["id"]} '
                  f'{p["durum"]}')
sonuc('E2', 'kaybedilmiş / iptal teklif stok tutmuyor', e2,
      'Teklif sonuçlanmış ama rezervasyonu açık; stok satılamaz görünür.')

# ══ F ═════════════════════════════════════════════════════════════
bolum(f'F · BİLGİ: {ESKI_GUN} TARİHİNDE KALANLAR')
fm = [m for m in mal if gun(m['maliyet_tarihi']) == ESKI_GUN]
fs = [r for r in stok if gun(r['alis_tarihi']) == ESKI_GUN]
fh = [h for h in har if gun(h['hareket_tarihi']) == ESKI_GUN
      and h['baglanti_tip'] in ('maliyet', 'stok_fatura')]
print(f'  maliyet satırı: {len(fm)} · alış tarihi o gün olan stok: {len(fs)} '
      f'· tedarikçi borcu: {len(fh)}')
for m in fm[:20]:
    print(f'       · maliyet {s(m["maliyet_tip"], 24)} '
          f'{s(m["fatura_no"] or "—", 18)} {para(m["tutar"], m["doviz"])}')
for (fno, cid) in sorted({(r['fatura_no'], r['cari_id']) for r in fs},
                         key=lambda x: str(x)):
    n = sum(1 for r in fs if (r['fatura_no'], r['cari_id']) == (fno, cid))
    ur = next(r['uretici'] for r in fs
              if (r['fatura_no'], r['cari_id']) == (fno, cid))
    print(f'       · stok alışı {s(fno or "(faturasız)", 20)} {s(ur, 30)} '
          f'{n} stok')

print('\n' + '=' * 78)
if sorun:
    print(f'  ⚠ {sorun} satır bakılmayı bekliyor. Çıktıyı bana gönder.')
else:
    print('  ✓ Bütün denetimler tuttu.')
print('  Hiçbir şey değiştirilmedi.')
print('=' * 78)

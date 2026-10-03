#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — KUR VE TRY KARŞILIĞI DENETİMİ  (GT1)
#
#  ── NE ARIYOR ──
#    Cari hareketin `borc_try` / `alacak_try` alanı, tutarın ANA PARA
#    BİRİMİ (TRY) karşılığıdır. Cari ekstresinin özeti, yaşlandırma
#    raporu ve kasa mutabakatı bu alandan beslenir; satırlar ise ham
#    tutardan. İkisi ayrışırsa aynı belgede iki farklı rakam çıkar ve
#    hangisinin doğru olduğu belli olmaz.
#
#    Ölçülen vaka (GT1): gider faturası cariye işlenirken `alacak_try`
#    üç ayrı yerde üç farklı şekilde hesaplanıyordu. TRY faturada
#    tutarın USD KARŞILIĞI yazılıyordu:
#
#        5.235,00 ₺  →  alacak_try = 107,16      (olması gereken 5.235,00)
#
#    PINAR GÜMRÜK'ün 166.895,62 ₺ tutarındaki hesabı, ekstrenin
#    "Net Özet" kutusunda 3.413,48 TRY görünüyordu.
#
#  ── DENETİMLER ──
#    K1 · USD KÖPRÜSÜ      `*_try` alanı `_usd(...)` ile hesaplanmış.
#                          TRY tutar da çevrileceği için bozulur.
#    K2 · SABİT KUR 1.0    `kur_uygulanan=1.0` yazılmış ama `doviz`
#                          sabit 'TRY' değil. Yabancı dövizde ekstre
#                          "1 EUR = 1,0000 ₺" basar.
#    K3 · TRY ALANI YOK    Tutarlı bir hareket yazılıyor ama `*_try`
#                          hiç verilmemiş. Alan NULL kalır; okuyan
#                          her yer kendi tahminini yapar.
#
#  ── DOĞRU YOL ──
#    `_try_karsilik(tutar, doviz, kur=None, tarih=None)` → (try, kur)
#    Kur arşivi boşluklarını da o yönetir. Gider faturaları için
#    `_gider_cari_alanlari()` bunu sarmalar.
#
#  Salt okunur; hiçbir dosyayı değiştirmez.
# ══════════════════════════════════════════════════════════════════════
import ast
import io
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
HEDEF = KOK / 'flask_app.py'

kaynak = io.open(HEDEF, encoding='utf-8').read()
agac = ast.parse(kaynak)
satirlar = kaynak.splitlines()

TRY_ALANLARI = ('borc_try', 'alacak_try')
USD_ISARETLERI = ('_usd', '_usd_cevrim')

bulgu = 0


def metin(dugum):
    """Düğümün kaynak metni (ast.get_source_segment CRLF'de de çalışır)."""
    try:
        return ast.get_source_segment(kaynak, dugum) or ''
    except Exception:
        return ''


def usd_gecer(dugum):
    """İfade içinde USD çevrimi çağrısı var mı."""
    for alt in ast.walk(dugum):
        if isinstance(alt, ast.Call):
            ad = alt.func
            if isinstance(ad, ast.Name) and ad.id in USD_ISARETLERI:
                return True
            if isinstance(ad, ast.Attribute) and ad.attr in USD_ISARETLERI:
                return True
    return False


def sabit_bir(dugum):
    return isinstance(dugum, ast.Constant) and dugum.value in (1, 1.0)


def sabit_try(dugum):
    return isinstance(dugum, ast.Constant) and dugum.value == 'TRY'


# ── Hareket yazan çağrıları topla ────────────────────────────────────
cagrilar = []
for d in ast.walk(agac):
    if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) \
            and d.func.id == 'CariHareket':
        cagrilar.append(d)

# ── Serbest atamalar: h.alacak_try = ... ─────────────────────────────
atamalar = []
for d in ast.walk(agac):
    if isinstance(d, ast.Assign):
        for hedef in d.targets:
            if isinstance(hedef, ast.Attribute) and hedef.attr in TRY_ALANLARI:
                atamalar.append((hedef.attr, d.value, d.lineno))
            elif isinstance(hedef, ast.Tuple):
                for p in hedef.elts:
                    if isinstance(p, ast.Attribute) and p.attr in TRY_ALANLARI:
                        atamalar.append((p.attr, d.value, d.lineno))

print('═' * 70)
print(' MILESTONE ERP — KUR / TRY KARŞILIĞI DENETİMİ')
print('═' * 70)
print(f' Dosya          : {HEDEF.name}')
print(f' CariHareket    : {len(cagrilar)} yazım noktası')
print(f' Serbest atama  : {len(atamalar)} adet')
print()


def bas(baslik, etiket):
    print('─' * 70)
    print(f' {baslik}   [{etiket}]')
    print('─' * 70)


# ══ K1 · USD KÖPRÜSÜ ═════════════════════════════════════════════════
bas('K1 · TRY ALANI USD ÜZERİNDEN HESAPLANMIŞ', 'TRY TUTAR BOZULUR')
_k1 = 0
for c in cagrilar:
    for kw in c.keywords:
        if kw.arg in TRY_ALANLARI and usd_gecer(kw.value):
            print(f'   ✗ satır {kw.value.lineno}: {kw.arg}={metin(kw.value)[:60]}')
            _k1 += 1
for ad, deger, ln in atamalar:
    if usd_gecer(deger):
        print(f'   ✗ satır {ln}: {ad} = {metin(deger)[:60]}')
        _k1 += 1
if _k1:
    print()
    print('   → `_try_karsilik(tutar, doviz, tarih=...)` kullanın. `_usd`')
    print('     TRY tutarı da çevirir; sonradan kurla çarpmak bunu geri')
    print('     almaz, TRY faturada USD değeri kaydedilir.')
    bulgu += _k1
else:
    print('   ✓ temiz — hiçbir TRY alanı USD üzerinden hesaplanmıyor')
print()

# ══ K2 · SABİT KUR ═══════════════════════════════════════════════════
bas('K2 · kur_uygulanan SABİT 1.0 AMA DÖVİZ TRY DEĞİL', 'EKSTREDE YANLIŞ KUR')
_k2 = 0
for c in cagrilar:
    kw = {k.arg: k.value for k in c.keywords if k.arg}
    if 'kur_uygulanan' not in kw or not sabit_bir(kw['kur_uygulanan']):
        continue
    dv = kw.get('doviz')
    if dv is not None and sabit_try(dv):
        continue                      # 'TRY' sabiti — 1.0 doğru
    print(f'   ✗ satır {c.lineno}: doviz={metin(dv)[:34] if dv else "(verilmemiş)"}'
          f' · kur_uygulanan=1.0')
    _k2 += 1
if _k2:
    print()
    print('   → Kuru `_try_karsilik` döndürsün. Sabit 1.0, yabancı dövizli')
    print('     harekette ekstreye "1 EUR = 1,0000 ₺" yazdırır.')
    bulgu += _k2
else:
    print('   ✓ temiz — sabit kur yalnızca TRY hareketlerde')
print()

# ══ K3 · TRY ALANI HİÇ YAZILMAMIŞ ════════════════════════════════════
bas('K3 · TUTAR YAZILIYOR AMA TRY KARŞILIĞI YOK', 'ALAN NULL KALIR')
_k3 = 0
for c in cagrilar:
    adlar = {k.arg for k in c.keywords if k.arg}
    if not ({'borc', 'alacak'} & adlar):
        continue
    if TRY_ALANLARI[0] in adlar or TRY_ALANLARI[1] in adlar:
        continue
    # Tutarların ikisi de sabit 0 ise TRY alanı gerekmez
    kw = {k.arg: k.value for k in c.keywords if k.arg}
    sifir = all(isinstance(kw.get(a), ast.Constant) and kw[a].value in (0, 0.0)
                for a in ('borc', 'alacak') if a in kw)
    if sifir:
        continue
    print(f'   ✗ satır {c.lineno}: borc/alacak var, borc_try/alacak_try yok')
    _k3 += 1
if _k3:
    print()
    print('   → Hareketi yazarken TRY karşılığını da yazın; sonradan')
    print('     hesaplayan her okuyucu kendi kuralını uydurur.')
    bulgu += _k3
else:
    print('   ✓ temiz — tutarlı her hareket TRY karşılığını da yazıyor')

print()

# ══ K4 · PARA YAZAN BLOKTA SESSİZ YUTMA ══════════════════════════════
bas('K4 · PARA YAZAN try BLOĞU SESSİZCE YUTULUYOR', 'KAYIT DÜŞER, KİMSE BİLMEZ')
# Ölçülen vaka: çek cirosunda `except Exception: pass` vardı. Çek
# "Ciro Edildi" işaretleniyor, borcu kapatan cari hareket yazılmıyor,
# kullanıcıya hiçbir şey söylenmiyordu. Aynı hata kasa bloğunda bir
# kez düzeltilmiş (F13) ama hemen üstteki ciro bloğu atlanmıştı.
PARA_SINIFLARI = ('CariHareket', 'KasaHareket', 'Maliyet', 'Cek',
                  'CekHareket', 'SatisKaydi', 'Fatura')


def para_yazar(dugum):
    for alt in ast.walk(dugum):
        if isinstance(alt, ast.Call) and isinstance(alt.func, ast.Name) \
                and alt.func.id in PARA_SINIFLARI:
            return alt.func.id
    return None


def sessiz(isleyici):
    """except gövdesi yalnızca pass / continue mi."""
    govde = [x for x in isleyici.body if not isinstance(x, ast.Expr)
             or not isinstance(x.value, ast.Constant)]      # docstring at
    return all(isinstance(x, (ast.Pass, ast.Continue)) for x in govde) and bool(govde)


_k4 = 0
for d in ast.walk(agac):
    if not isinstance(d, ast.Try):
        continue
    sinif = para_yazar(ast.Module(body=d.body, type_ignores=[]))
    if not sinif:
        continue
    for h in d.handlers:
        if sessiz(h):
            print(f'   ✗ satır {d.lineno}: {sinif} yazıyor, '
                  f'satır {h.lineno} hatayı sessizce yutuyor')
            _k4 += 1
if _k4:
    print()
    print('   → Hatayı yutmayın: rollback yapıp kullanıcıya dönün.')
    print('     Kaydın yazılmaması, durumun değişmiş görünmesiyle')
    print('     birleşince hesap aylar sonra tutmaz.')
    bulgu += _k4
else:
    print('   ✓ temiz — para yazan hiçbir blok hatayı sessizce yutmuyor')

print()
print('═' * 70)
if bulgu:
    print(f' ✗ {bulgu} şüpheli nokta')
else:
    print(' ✓ TEMİZ — TRY karşılığı her yerde tek kuraldan hesaplanıyor')
print('═' * 70)
sys.exit(1 if bulgu else 0)

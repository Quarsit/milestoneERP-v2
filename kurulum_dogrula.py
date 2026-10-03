#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — KURULUM VE VERİ DOĞRULAMA  (GT1)
#
#  ── NE İÇİN ──
#    "Paketi kurdum, doğru oldu mu?" sorusuna TEK CEVAP verir. İki
#    ayrı şeyi ölçer:
#
#      1. KOD   — düzeltmeler gerçekten yerinde mi
#      2. VERİ  — geçmiş kayıtlar onarıldı mı
#
#    İkisi ayrıdır: kod güncel olsa bile eski kayıtlar bozuk kalabilir
#    (onarım betiği çalıştırılmadıysa), ya da tersi.
#
#  ── VERİ ÖLÇÜMÜ ──
#    TRY hareketinde `alacak_try` tutarın KENDİSİ olmalıdır. Değilse
#    cari ekstresinin "Net Özet" kutusu satırlarla tutmaz — PINAR
#    GÜMRÜK'te 166.895,62 ₺ hesap özette 3.413,48 TRY görünüyordu.
#
#    Yabancı dövizde `alacak_try ≈ alacak × kur_uygulanan` olmalıdır.
#
#  Salt okunur; hiçbir kaydı değiştirmez.
#
#  ── KULLANIM ──
#      venv/bin/python kurulum_dogrula.py
# ══════════════════════════════════════════════════════════════════════
import io
import os
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))

try:
    from dotenv import load_dotenv
    load_dotenv(KOK / '.env')
except Exception:
    pass

os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')

sorun = 0


def tr(x):
    return f'{x:,.2f}'.replace(',', '~').replace('.', ',').replace('~', '.')


print('═' * 70)
print(' MILESTONE ERP — KURULUM VE VERİ DOĞRULAMA')
print('═' * 70)
print()

# ══ 1) KOD ═══════════════════════════════════════════════════════════
print('─' * 70)
print(' 1 · KOD — düzeltmeler yerinde mi')
print('─' * 70)

ISARETLER = [
    ('flask_app.py', '_gider_cari_alanlari',
     'Gider faturası TRY karşılığı tek yerden hesaplanıyor'),
    ('flask_app.py', "'error': 'ciro_hatasi'",
     'Çek cirosu hatası artık sessizce yutulmuyor'),
    ('flask_app.py', 'borc_try=q2(_c_try)',
     'Çek cirosu TRY karşılığını yazıyor'),
    ('flask_app.py', 'app.try_karsilik = _try_karsilik',
     'Onarım betiği uygulamanın kendi hesabını kullanıyor'),
]
for dosya, isaret, aciklama in ISARETLER:
    p = KOK / dosya
    var = p.exists() and isaret in io.open(p, encoding='utf-8').read()
    print(f'   {"✓" if var else "✗"} {aciklama}')
    if not var:
        sorun += 1

for betik in ('gider_try_duzelt.py', 'kur_denetim.py'):
    var = (KOK / betik).exists()
    print(f'   {"✓" if var else "✗"} {betik} yerinde')
    if not var:
        sorun += 1
print()

# ══ 2) VERİ ══════════════════════════════════════════════════════════
print('─' * 70)
print(' 2 · VERİ — geçmiş kayıtlar onarıldı mı')
print('─' * 70)

import flask_app                                   # noqa: E402
from models import CariHareket                     # noqa: E402

with flask_app.app.app_context():
    hepsi = CariHareket.query.all()
    try_bozuk, dvz_bozuk, kursuz = [], [], []
    for h in hepsi:
        dv = (h.doviz or 'TRY').upper()
        for alan in ('borc', 'alacak'):
            ham = float(getattr(h, alan) or 0)
            if ham <= 0:
                continue
            saklanan = getattr(h, alan + '_try')
            if saklanan is None:
                kursuz.append((h, alan))
                continue
            saklanan = float(saklanan)
            if dv == 'TRY':
                # TRY'de TRY karşılığı tutarın KENDİSİ olmalı
                if abs(saklanan - ham) > 0.02:
                    try_bozuk.append((h, alan, ham, saklanan))
            else:
                kur = float(h.kur_uygulanan or 0)
                if kur <= 0:
                    kursuz.append((h, alan))
                elif abs(saklanan - ham * kur) > max(0.05, ham * kur * 0.001):
                    dvz_bozuk.append((h, alan, ham, kur, saklanan))

    print(f'   İncelenen hareket : {len(hepsi)}')
    print()
    if try_bozuk:
        print(f'   ✗ TRY karşılığı tutmayan TRY hareketi: {len(try_bozuk)}')
        for h, alan, ham, sak in try_bozuk[:8]:
            ad = (h.cari_unvan or h.cari_id or '?')[:26]
            print(f'       {ad:<28}{tr(ham):>14} ₺  →  kayıtlı {tr(sak):>12}')
        if len(try_bozuk) > 8:
            print(f'       … ve {len(try_bozuk) - 8} kayıt daha')
        print()
        print('       → venv/bin/python gider_try_duzelt.py --uygula')
        sorun += 1
    else:
        print('   ✓ Bütün TRY hareketlerinde TRY karşılığı tutarın kendisi')

    if dvz_bozuk:
        print(f'   ✗ Kuruyla tutmayan dövizli hareket: {len(dvz_bozuk)}')
        for h, alan, ham, kur, sak in dvz_bozuk[:6]:
            ad = (h.cari_unvan or h.cari_id or '?')[:26]
            print(f'       {ad:<28}{tr(ham)} {h.doviz} × {kur}'
                  f'  →  kayıtlı {tr(sak)}')
        sorun += 1
    else:
        print('   ✓ Dövizli hareketlerin TRY karşılığı kuruyla tutarlı')

    if kursuz:
        print(f'   ⚠ TRY karşılığı ya da kuru boş hareket: {len(kursuz)}')
        print('       (okuyan taraf tarihten kurla dolduruyor — rakam')
        print('        genelde doğru, ama kaynak tek değil)')

print()
print('═' * 70)
if sorun:
    print(f' ✗ {sorun} başlıkta eksik var — yukarıdaki adımları uygulayın')
else:
    print(' ✓ KURULUM VE VERİ DOĞRU — yapacak bir şey yok')
print('═' * 70)
sys.exit(1 if sorun else 0)

#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — SİPARİŞ DURUM DAMGASI GÖÇÜ  (DT1)
#
#  ── NE İÇİN ──
#    Sipariş ekranı "Bu durumda N gündür" yazıyordu ama ölçtüğü şey
#    SİPARİŞİN YAŞIYDI: 23.09'da açılıp 26.09'da onaylanan bir sipariş
#    "4 gündür onaylandı" görünüyordu. Takılma uyarısı da buradan
#    besleniyor; durumu yeni değişmiş bir sipariş yalnızca eski olduğu
#    için "takıldı" diye yanabiliyordu.
#
#    Artık `siparis_kayit.durum_tarihi` durumun en son ne zaman
#    değiştiğini tutuyor ve her değişiklikte kendiliğinden damgalanıyor.
#    Bu betik GEÇMİŞ siparişlerin damgasını doldurur.
#
#  ── NEREDEN OKUR ──
#    1) Denetim kaydı (AuditLog): o sipariş için kayıtlı SON durum
#       değişikliğinin tarihi. En doğru kaynak.
#    2) Kayıt yoksa: siparişin kendi tarihi. Ekranın bugünkü davranışı
#       zaten bu — yani hiçbir şey kötüleşmez, sadece elde veri olan
#       siparişler düzelir.
#
#  ── GÜVENLİ ──
#    • Yalnızca BOŞ `durum_tarihi` doldurulur; dolu olan ellenmez.
#    • Durum, tutar, tarih — hiçbiri değişmez. Tek yazılan alan bu.
#    • Tekrar çalıştırılabilir.
#
#  ── KULLANIM (proje klasöründe) ──
#      venv/bin/python durum_tarihi_goc.py            # rapor
#      venv/bin/python durum_tarihi_goc.py --uygula   # yaz
# ══════════════════════════════════════════════════════════════════════
import json
import os
import sys
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

from datetime import datetime, time  # noqa: E402

import flask_app  # noqa: E402
from models import db, Siparis, AuditLog  # noqa: E402

print('═' * 76)
print(' SİPARİŞ DURUM DAMGASI (DT1) — "bu durumda kaç gündür" doğru ölçülsün')
print('═' * 76)

with flask_app.app.app_context():
    bos = Siparis.query.filter(Siparis.durum_tarihi.is_(None)).all()
    dolu = Siparis.query.filter(Siparis.durum_tarihi.isnot(None)).count()

    print(f' {dolu + len(bos)} sipariş · damgası olan: {dolu} · boş: {len(bos)}')
    print()
    if not bos:
        print(' ✓ Her siparişin durum damgası var — yapacak bir şey yok.')
        sys.exit(0)

    # Denetim kaydından son durum değişikliklerini topla
    kayitlar = AuditLog.query.filter(
        AuditLog.tablo_adi == 'siparis',
        AuditLog.islem_tipi == 'DURUM').order_by(AuditLog.tarih).all()
    son_degisim = {}
    for k in kayitlar:
        if not k.kayit_id or not k.tarih:
            continue
        try:
            yeni = json.loads(k.yeni_veri or '{}')
        except Exception:
            yeni = {}
        if 'durum' in yeni:
            son_degisim[k.kayit_id] = (k.tarih, yeni.get('durum'))

    plan, kaynak_sayac = [], {'denetim': 0, 'siparis_tarihi': 0, 'atlandi': 0}
    for s in bos:
        damga, kaynak = None, None
        kayit = son_degisim.get(s.id)
        # Denetim kaydı YALNIZCA siparişin ŞU ANKİ durumuyla eşleşiyorsa
        # kullanılır. Eşleşmiyorsa durum başka bir yoldan (sevkiyat,
        # teslim) değişmiş demektir; o tarihi kullanmak yanlış bir süre
        # gösterirdi — sipariş tarihine düşmek dürüst olanı.
        if kayit and kayit[1] and kayit[1] == s.durum:
            damga, kaynak = kayit[0], 'denetim'
        elif s.siparis_tarihi:
            damga, kaynak = datetime.combine(s.siparis_tarihi, time.min), 'siparis_tarihi'
        if damga is None:
            kaynak_sayac['atlandi'] += 1
            continue
        kaynak_sayac[kaynak] += 1
        plan.append((s, damga, kaynak))

    print(f' denetim kaydından   : {kaynak_sayac["denetim"]}')
    print(f' sipariş tarihinden  : {kaynak_sayac["siparis_tarihi"]}')
    if kaynak_sayac['atlandi']:
        print(f' tarihi hiç olmayan  : {kaynak_sayac["atlandi"]}  (atlandı)')
    print()

    ornek = plan[:12]
    print(f'   {"sipariş":<18} {"durum":<16} {"damga":<17} kaynak')
    for s, damga, kaynak in ornek:
        print(f'   {s.id[:18]:<18} {(s.durum or "")[:16]:<16} '
              f'{damga.strftime("%d.%m.%Y %H:%M"):<17} {kaynak}')
    if len(plan) > len(ornek):
        print(f'   … ve {len(plan) - len(ornek)} sipariş daha')

    if not UYGULA:
        print()
        print(' Bu bir ÖN İZLEME. Yazmak için:')
        print('   venv/bin/python durum_tarihi_goc.py --uygula')
        sys.exit(0)

    for s, damga, _k in plan:
        s.durum_tarihi = damga
    db.session.commit()
    print()
    print(f' ✓ {len(plan)} siparişin durum damgası yazıldı.')
    print(' Bundan sonraki her durum değişikliği kendiliğinden damgalanır.')

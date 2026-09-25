#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — YETKİ GÖÇÜ  (F12)
#
#  ── NE İÇİN ──
#    Eskiden yetki JSON'u BOŞ olan kullanıcı "eski kullanıcı" sayılıp
#    TÜM modüllere YAZMA yetkisi alıyordu. Yetki kutularını
#    işaretlemeden açılan her yeni kullanıcı da bu yoldan tam yetkili
#    oluyordu.
#
#    Yeni davranış: yetki tanımsızsa erişim YOK. Bu betik, ESKİ
#    kullanıcıların erişimini kaybetmemesi için onların fiilî
#    yetkisini (tam yazma) AÇIK yetki olarak kaydeder.
#
#    Sonrasında Ayarlar > Kullanıcılar ekranından kimin neye
#    erişeceğini daraltabilirsiniz — artık gerçekten uygulanır.
#
#  ── KULLANIM (proje klasöründe) ──
#      venv/bin/python yetki_goc.py            # yalnızca rapor
#      venv/bin/python yetki_goc.py --uygula   # yaz
#      venv/bin/python yetki_goc.py --uygula --okuma   # yazma yerine okuma ver
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
SEVIYE = 'okuma' if '--okuma' in sys.argv else 'yazma'
for _a in sys.argv[1:]:
    if _a.startswith('--url='):
        os.environ['DATABASE_URL'] = _a.split('=', 1)[1]

if not os.environ.get('DATABASE_URL'):
    print('HATA: DATABASE_URL bulunamadı (.env okunamadı).')
    sys.exit(1)

os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
sys.path.insert(0, str(Path('.').resolve()))

import flask_app  # noqa: E402
from models import db, Kullanici  # noqa: E402

# flask_app.YETKI_MODULLERI uygulama fabrikasinin ICINDE tanimli
# (modul duzeyinde gorunmuyor), o yuzden ayni liste burada tutulur.
# Fazladan/eksik anahtar zarar vermez: tanimsiz modul zaten 'gizli'.
MODULLER = ['dashboard', 'stok', 'siparis', 'rezervasyon', 'proforma',
            'fatura', 'cari', 'maliyet', 'sevkiyat', 'karlilik',
            'satislar', 'raporlar', 'kasa', 'kesim', 'ayarlar', 'denetim', 'crm']

print('═' * 70)
print(' YETKİ GÖÇÜ (F12) — yetki tanımsız kullanıcılara AÇIK yetki yazılır')
print('═' * 70)

with flask_app.app.app_context():
    kullanicilar = Kullanici.query.all()
    hedef = []
    for k in kullanicilar:
        try:
            mevcut = json.loads(k.yetkiler or '{}')
        except Exception:
            mevcut = {}
        if not mevcut:
            hedef.append(k)

    print(f' {len(kullanicilar)} kullanıcı · yetkisi tanımsız olan: {len(hedef)}')
    print()
    if not hedef:
        print(' ✓ Yapacak bir şey yok — herkesin açık yetkisi var.')
        sys.exit(0)

    for k in hedef:
        rol = (k.rol or '').upper()
        not_ = ' (ADMIN — zaten tam yetkili, kayıt yine de açık yazılır)' if rol == 'ADMIN' else ''
        print(f'   {k.ad:20} rol: {k.rol or "—":10} → tüm modüller: {SEVIYE}{not_}')

    if not UYGULA:
        print()
        print(' Bu bir ÖN İZLEME. Yazmak için: venv/bin/python yetki_goc.py --uygula')
        sys.exit(0)

    for k in hedef:
        k.yetkiler = json.dumps({m: SEVIYE for m in MODULLER}, ensure_ascii=False)
    db.session.commit()
    print()
    print(f' ✓ {len(hedef)} kullanıcının yetkisi açık olarak kaydedildi ({SEVIYE}).')
    print(' Ayarlar > Kullanıcılar ekranından daraltabilirsiniz; artık uygulanır.')

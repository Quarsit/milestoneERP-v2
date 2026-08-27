#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — BANKALARA KASA OLUŞTUR  ·  BK3
#
#  Kasasi olmayan banka hesaplari icin bagli kasa acar.
#
#  ── NEDEN GEREKLİ ──
#    Banka hesabi tek basina para hareketi tasiyamaz; tahsilat ve
#    odemeler KASA uzerinden isleniyor. Kasasi olmayan banka
#    sistemde gorunur ama kullanilamaz — odeme ekraninda secilemez.
#
#  ── AÇILAN KASA ──
#    Ad     : "BANKA ADI · ŞUBE"  (sube varsa)
#    Döviz  : bankanin dovizi (yoksa TRY)
#    Bakiye : 0 — acilis bakiyesini kullanici girer, sistem o an
#             duzgun bir `giris` hareketi acar. Buradan bakiye
#             yazmak "hayalet para" olurdu (D1 ihlali).
#
#  ── ZATEN KASASI OLAN ATLANIR ──
#    Ayni bankaya ikinci kasa acmak, hangisine para yatirildigini
#    belirsizlestirirdi.
#
#  ── VARSAYILAN: RAPOR ──
#    --uygula demeden hicbir kayit olusturulmaz.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python banka_kasa_olustur.py
#      venv/bin/python banka_kasa_olustur.py --uygula
# ══════════════════════════════════════════════════════════════════════
import os
import sys
from pathlib import Path

if not Path('flask_app.py').exists():
    print("HATA: flask_app.py bu klasörde yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv('.env')
except ImportError:
    pass
os.environ['MILESTONE_ACILIS_ATLA'] = '1'
sys.path.insert(0, str(Path('.').resolve()))

import flask_app  # noqa: E402
from models import Banka, Kasa, db  # noqa: E402

UYGULA = '--uygula' in sys.argv

print("═" * 70)
print(" BANKALARA KASA OLUŞTUR")
print("═" * 70)
print()

with flask_app.app.app_context():
    bankalar = Banka.query.order_by(Banka.banka_adi).all()
    if not bankalar:
        print(" Kayıtlı banka yok — yapılacak iş yok.")
        sys.exit(0)

    # Hangi bankalarin kasasi VAR
    kasali = {k.banka_id for k in Kasa.query.filter(
        Kasa.banka_id.isnot(None)).all()}

    acilacak, atlanan = [], []
    for b in bankalar:
        if b.id in kasali:
            atlanan.append(b)
            continue
        ad = (b.banka_adi or f'BANKA {b.id}').strip()
        if b.sube:
            ad = f"{ad} · {str(b.sube).strip()}"
        acilacak.append((b, ad[:100], (b.doviz or 'TRY').upper()))

    print(f" Toplam banka : {len(bankalar)}")
    print(f" Kasası olan  : {len(atlanan)}")
    print(f" Açılacak     : {len(acilacak)}")
    print()

    if atlanan:
        print(" ── ZATEN KASASI VAR (atlanacak) ──")
        for b in atlanan:
            print(f"   {(b.banka_adi or '')[:40]}")
        print()

    if acilacak:
        print(" ── AÇILACAK KASALAR ──")
        for _b, ad, dv in acilacak:
            print(f"   {ad[:46]:<46} {dv}   bakiye 0")
        print()

    if not acilacak:
        print(" ✓ Her bankanın kasası var — yapılacak iş yok.")
        sys.exit(0)

    if not UYGULA:
        print("─" * 70)
        print(" RAPOR MODU — hiçbir kasa oluşturulmadı.")
        print()
        print(" Uygulamak için:")
        print("   venv/bin/python banka_kasa_olustur.py --uygula")
        print()
        print(" ⚠ Önce yedek alın:")
        print("   sudo /usr/local/bin/milestone-yedek.sh")
        print("─" * 70)
        sys.exit(0)

    eklendi = 0
    for b, ad, dv in acilacak:
        try:
            db.session.add(Kasa(ad=ad, doviz=dv, bakiye=0, banka_id=b.id,
                                ana_kasa=False, aktif=True,
                                varsayilan=False))
            eklendi += 1
        except Exception as exc:
            print(f"   ✗ {ad[:40]}: {str(exc)[:60]}")
    db.session.commit()

    print("═" * 70)
    print(f" ✓ {eklendi} kasa oluşturuldu (bakiyeler 0).")
    print()
    print(" SONRAKİ ADIM: Kasa ekranından açılış bakiyelerini girin.")
    print(" Sistem o an düzgün bir giriş hareketi açar; buradan bakiye")
    print(" yazmak hareketi olmayan bakiye (hayalet para) üretirdi.")
    print("═" * 70)

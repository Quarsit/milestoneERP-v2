#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — SF2 TEMİZLİK: yanlış cariye yazılmış karşı kayıtlar
#
#  SF2 hatasi yuzunden bir stogun karsi kaydi BASKA bir tedarikcinin
#  hesabina dusmus olabilir. Bu betik onlari BULUR ve isterseniz
#  siler.
#
#  ── NASIL TESPİT EDİLİR ──
#    Karsi kayitlar `kaynak='stok_karsi_kayit'` ile isaretli ve
#    aciklamalarinda kaynak stok kimligi yazili. Her birinin
#    cari_unvan'i, o stogun `uretici` alaniyla ESLESMELI. Eslesmiyorsa
#    yanlis cariye yazilmis demektir.
#
#    Stok SILINMIS oldugu icin uretici bilgisine dogrudan
#    ulasilamaz; bu yuzden ayni fatura numarasindaki hareketlere
#    bakilir. Kesin karar veremedigimiz kayitlar SILINMEZ, listelenir.
#
#  ── VARSAYILAN: RAPOR ──
#    --uygula demeden hicbir sey silinmez.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python sf2_temizlik.py            # rapor
#      venv/bin/python sf2_temizlik.py --uygula
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
from models import CariHareket, PlakaStok, BlokStok, EbatliStok, db  # noqa: E402

UYGULA = '--uygula' in sys.argv

print("═" * 70)
print(" SF2 TEMİZLİK · yanlış cariye yazılmış karşı kayıtlar")
print("═" * 70)
print()

with flask_app.app.app_context():
    kayitlar = CariHareket.query.filter_by(kaynak='stok_karsi_kayit').all()
    if not kayitlar:
        print(" ✓ Hiç karşı kayıt yok — yapılacak iş yok.")
        sys.exit(0)

    print(f" Toplam karşı kayıt: {len(kayitlar)}")
    print()

    supheli, temiz, belirsiz = [], [], []
    for k in kayitlar:
        _fno = k.baglanti_id or ''
        # Ayni fatura numarasini kullanan TUM alis hareketleri
        adaylar = CariHareket.query.filter_by(
            baglanti_tip='stok_fatura', baglanti_id=_fno).all()
        if len(adaylar) <= 1:
            # Tek aday varsa yanlis cariye yazilmis olamaz
            temiz.append(k)
            continue
        # Aciklamadaki stok kimligiyle stogu bulmaya calis
        _stok_id = None
        _ac = k.aciklama or ''
        if '(' in _ac and ')' in _ac:
            _stok_id = _ac[_ac.rfind('(') + 1:_ac.rfind(')')].strip()
        _stok = None
        if _stok_id:
            for _M in (PlakaStok, BlokStok, EbatliStok):
                _stok = db.session.get(_M, _stok_id)
                if _stok:
                    break
        if _stok is None:
            # Stok silinmis — uretici bilinmiyor, KESIN karar veremeyiz
            belirsiz.append((k, len(adaylar)))
            continue
        _uret = (getattr(_stok, 'uretici', '') or '').strip().upper()
        if _uret and (k.cari_unvan or '').strip().upper() != _uret:
            supheli.append((k, _uret))
        else:
            temiz.append(k)

    if temiz:
        print(f" ✓ Doğru görünen : {len(temiz)}")
    if belirsiz:
        print(f" ? Karar verilemeyen : {len(belirsiz)}  (stok silinmiş)")
        for k, n in belirsiz:
            print(f"     {k.id}  {k.cari_unvan}  {float(k.borc or 0):,.2f} "
                  f"{k.doviz}  · '{k.baglanti_id}' ({n} aday cari)")
    if supheli:
        print(f" ✗ YANLIŞ CARİ    : {len(supheli)}")
        for k, u in supheli:
            print(f"     {k.id}  yazıldığı: {k.cari_unvan}  →  olması gereken: {u}")

    print()
    if not supheli and not belirsiz:
        print(" ✓ Yanlış cariye yazılmış kayıt yok.")
        sys.exit(0)

    print("─" * 70)
    print(" Karar verilemeyen kayıtlar SİLİNMEZ; ekranda inceleyip")
    print(" cari kartından tek tek kaldırabilirsiniz (× düğmesi).")
    print("─" * 70)

    if not supheli:
        sys.exit(0)
    if not UYGULA:
        print()
        print(" RAPOR MODU — hiçbir şey silinmedi.")
        print(" Yanlış cariye yazılmışları silmek için:")
        print("   venv/bin/python sf2_temizlik.py --uygula")
        sys.exit(0)

    for k, _ in supheli:
        db.session.delete(k)
    db.session.commit()
    print(f" ✓ {len(supheli)} yanlış kayıt silindi.")
    print()
    print(" NOT: Doğru cariye karşı kayıt OLUŞTURULMADI. Gerekiyorsa")
    print(" stok ekranından işlemi tekrarlayın ya da cari kartından")
    print(" elle hareket girin.")

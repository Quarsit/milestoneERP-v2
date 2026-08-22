#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — STOK FATURASI YANLIŞ CARİYİ BULUYOR  ·  SF2
#
#  ── ÖLÇÜLEN HATA (üretimde görüldü) ──
#    Stok silinirken bagli alis faturasi SADECE FATURA NUMARASIYLA
#    araniyor, cari HIC kontrol edilmiyor:
#
#        CariHareket.query.filter_by(
#            baglanti_tip='stok_fatura', baglanti_id=_fno).first()
#
#    "Beklenen Fatura 1" gibi YER TUTUCU fatura numaralari BIRDEN
#    COK tedarikcide kullaniliyor. `.first()` hangisi once gelirse
#    onu aliyor.
#
#    Gercek olay: LUCENTE'ye ait CEPPO plakasi silindi, "karsi kayit"
#    secildi; iki karsi kayit ANKA NATURAL STONE carisine dustu.
#    LUCENTE'nin borcu oldugu gibi kaldi, ANKA'nin hesabi 622,44 $
#    yanlis borclandi.
#
#  ── BU HATA YENİ DEĞİL ──
#    Ayni arama `fatura_duzelt` yolunda da kullaniliyordu; yani SF1
#    oncesinde de stok silmek YANLIS TEDARIKCININ borcunu
#    dusurebiliyordu. SF1 hatayi gorunur hale getirdi, yaratmadi.
#
#  ── DÜZELTME ──
#    Arama artik CARIYE de bakiyor. Stogun tedarikcisi `uretici`
#    alaninda ADLA duruyor; once o addan cari cozuluyor, sonra
#    (baglanti_id + cari_id) ciftiyle aranıyor.
#
#    Cari cozulemezse ya da eslesen hareket bulunamazsa MALI ISLEM
#    YAPILMAZ — yanlis cariye yazmaktansa hic yazmamak yeglenir.
#
#  ── İSİMLE BAĞLAMA UYARISI ──
#    `uretici` bir AD; bu projede isimle baglamanin kirilgan oldugunu
#    defalarca gorduk. Ama stok tablosunda cari_id YOK, elimizdeki
#    tek bag bu. En azindan ad ESLESMEZSE islem yapilmiyor; sessizce
#    baskasina yazmiyor.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python yama_sf2_cari_eslesme.py            # rapor
#      venv/bin/python yama_sf2_cari_eslesme.py --uygula
#
#  Şema değişikliği YOK.
# ══════════════════════════════════════════════════════════════════════
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
APP = Path('flask_app.py')

if not APP.exists():
    print("HATA: flask_app.py bu klasörde yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

ESKI = """        _grup = CariHareket.query.filter_by(
            baglanti_tip='stok_fatura', baglanti_id=_fno).first() if _fno else None"""

YENI = '''        # ── CARİ DE EŞLEŞMELİ (SF2) ──
        # Onceden yalnizca fatura numarasi araniyordu. "Beklenen
        # Fatura 1" gibi YER TUTUCU numaralar birden cok tedarikcide
        # kullanildigi icin `.first()` YANLIS CARIYI seciyordu.
        #
        # Uretimde olculdu: LUCENTE'ye ait plaka silindi, karsi
        # kayitlar ANKA carisine dustu.
        _grup = None
        if _fno:
            _uret = (getattr(stok, 'uretici', '') or '').strip()
            _aday = CariHareket.query.filter_by(
                baglanti_tip='stok_fatura', baglanti_id=_fno).all()
            if len(_aday) == 1 and not _uret:
                # Tek aday ve tedarikci bilgisi yok — belirsizlik yok.
                _grup = _aday[0]
            elif _uret:
                # Tedarikci ADIYLA eslestir. Stok tablosunda cari_id
                # YOK; elimizdeki tek bag bu. Eslesme bulunamazsa
                # MALI ISLEM YAPILMAZ — yanlis cariye yazmaktansa
                # hic yazmamak yeglenir.
                _ust = _uret.upper()
                for _a in _aday:
                    if (_a.cari_unvan or '').strip().upper() == _ust:
                        _grup = _a
                        break
                if _grup is None:
                    _c = Cari.query.filter(
                        func.upper(Cari.unvan) == _ust).first()
                    if _c:
                        for _a in _aday:
                            if _a.cari_id == _c.id:
                                _grup = _a
                                break
            if _grup is None and len(_aday) > 1:
                app.logger.warning(
                    f'[SF2] {stok_id}: "{_fno}" için {len(_aday)} aday hareket '
                    f'var, üretici "{_uret}" ile eşleşen yok — mali işlem '
                    f'YAPILMADI.')'''

IMZA = '# ── CARİ DE EŞLEŞMELİ (SF2) ──'

print("═" * 70)
print(" SF2 · STOK FATURASI YANLIŞ CARİYİ BULUYOR")
print("═" * 70)
print()

ham = APP.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


if uyarla(IMZA) in ham or IMZA in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

e = uyarla(ESKI)
adet = ham.count(e)
if adet != 1:
    print(f" ✗ Kalıp {adet} kez bulundu (1 bekleniyordu). DOSYAYA DOKUNULMADI.")
    sys.exit(1)

icerik = ham.replace(e, uyarla(YENI), 1)

try:
    compile(icerik, 'flask_app.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print("  ✓ uygulanacak          fatura araması cariye de bakıyor")
print("  ✓ uygulanacak          eşleşme yoksa mali işlem YAPILMAZ")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   venv/bin/python yama_sf2_cari_eslesme.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = APP.with_name(f'flask_app.py.yedek-{damga}')
shutil.copy2(APP, yedek)
APP.write_bytes(icerik.encode('utf-8'))
print()
print(f" ✓ flask_app.py  (yedek: {yedek.name})")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print(" ⚠ YANLIŞ OLUŞMUŞ KAYITLARI TEMİZLEYİN:")
print("   venv/bin/python /tmp/sf2_temizlik.py")
print("═" * 70)

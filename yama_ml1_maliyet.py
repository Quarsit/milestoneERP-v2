#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — MALİYET: ALIŞ BEDELİ VE TOPLAMLAR  ·  ML1
#
#  ── ÜÇ İSTEK ──
#    1) Disa aktarmada ALIS BEDELI yok
#    2) Ust filtrelere "Alis Bedeli" eklenmeli
#    3) Urun bazinda TOPLAM MALIYET ve TOPLAM BIRIM MALIYET
#       dogrudan gorulemiyor; kullanici elle topluyor
#
#  ── ALIŞ BEDELİ NEREDE ──
#    Maliyet kaydinda DEGIL, bagli STOKTA (`matrah` alani). Maliyet
#    yalnizca `baglanti_tip` + `baglanti_id` ile stoga baglaniyor.
#    Disa aktarimda her satir icin stok cozulup matrah okunuyor.
#
#    Cozum TEK SORGUYLA yapiliyor: satir basina sorgu atmak 500
#    maliyet kaydinda sayfayi kilitlerdi.
#
#  ── TOPLAM MALİYET ≠ MALİYETLERİN TOPLAMI ──
#    Bir urunun toplam maliyeti = ALIS BEDELI + uzerine eklenen
#    maliyetler (nakliye, gumruk, isleme...). Yalnizca maliyet
#    kalemlerini toplamak, mali "bedava alinmis" gibi gosterirdi.
#
#    Birim maliyet = toplam / miktar. Miktar stok tipine gore
#    degisiyor (m², m³, ton) — bu yuzden birim de birlikte
#    yaziliyor, ciplak sayi yaniltici olurdu.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python yama_ml1_maliyet.py            # rapor
#      venv/bin/python yama_ml1_maliyet.py --uygula
#
#  ⚠ templates/maliyet.html güncellenmeli.
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

ESKI = """            headers = ['Maliyet No', 'Tarih', 'Tip', 'Bağlantı', 'Kayıt', 'Tutar', 'Döviz', 'USD Karşılık', 'Fatura No']
            sayisal = [5, 7]
            q = Maliyet.query.filter(Maliyet.aktif == True).order_by(Maliyet.maliyet_tarihi.desc()).all()
            for m in q:
                rows.append([m.id, _tarih(m.maliyet_tarihi), m.maliyet_tip or '',
                             m.baglanti_tip or '', m.baglanti_id or '',
                             _f(m.tutar, True), m.doviz or '', _f(m.usd_karsilik, True),
                             m.fatura_no or ''])"""

YENI = '''            # ALIS BEDELI maliyet kaydinda DEGIL, bagli STOKTA
            # (`matrah`). Disa aktarima eklenmesi istendi.
            headers = ['Maliyet No', 'Tarih', 'Tip', 'Bağlantı', 'Kayıt',
                       'Alış Bedeli', 'Tutar', 'Döviz', 'USD Karşılık',
                       'Fatura No']
            sayisal = [5, 6, 8]
            q = Maliyet.query.filter(Maliyet.aktif == True).order_by(Maliyet.maliyet_tarihi.desc()).all()

            # STOK MATRAHLARI TEK SORGUDA.
            # Satir basina sorgu atmak 500 maliyet kaydinda sayfayi
            # kilitlerdi; bu projede ayni tuzagi CRM listesinde de
            # gormustuk.
            _ids = {(m.baglanti_tip or '').upper(): set() for m in q}
            for m in q:
                if m.baglanti_id:
                    _ids.setdefault((m.baglanti_tip or '').upper(), set()).add(
                        m.baglanti_id)
            _matrah = {}
            for _tip, _M in (('BLOK', BlokStok), ('PLAKA', PlakaStok),
                             ('EBATLI', EbatliStok)):
                _kume = _ids.get(_tip) or set()
                if not _kume:
                    continue
                for _s in _M.query.filter(_M.id.in_(list(_kume))).all():
                    _matrah[(_tip, _s.id)] = _s.matrah or 0

            for m in q:
                _ab = _matrah.get(((m.baglanti_tip or '').upper(),
                                   m.baglanti_id))
                rows.append([m.id, _tarih(m.maliyet_tarihi), m.maliyet_tip or '',
                             m.baglanti_tip or '', m.baglanti_id or '',
                             _f(_ab, True) if _ab else '',
                             _f(m.tutar, True), m.doviz or '',
                             _f(m.usd_karsilik, True),
                             m.fatura_no or ''])'''

# ── B) Liste ucu ALIS BEDELINI de dondursun ──
#  Ekrandaki filtre ve toplamlar bu alandan beslenecek. Stok
#  bilgisi zaten cozuluyor (`_stok_bilgi`), yalnizca disari
#  verilmiyordu.
B_ESKI = """                'stok_tip': _maliyet_stok_tip(m),
                'cins': _maliyet_cins(m),"""
B_YENI = """                'stok_tip': _maliyet_stok_tip(m),
                'cins': _maliyet_cins(m),
                # ML1: ALIS BEDELI (bagli stogun matrahi). Ekrandaki
                # "Alis Bedeli" suzgeci ve toplam maliyet hesabi
                # bundan besleniyor. Stok disi baglantilarda None.
                'alis_bedeli': _maliyet_alis_bedeli(m),"""

C_ESKI = """        def _maliyet_stok_tip(m):"""
C_YENI = """        def _maliyet_alis_bedeli(m):
            \"\"\"Bagli stogun ALIS BEDELI (matrah). Stok disi
            baglantilarda None doner — 0 dondurmek "bedava alinmis"
            gibi gorunurdu.\"\"\"
            # Sozluk adi `stok_bilgi_map` — ilk surumde `_stok_bilgi`
            # yazmistim, oyle bir degisken yok ve uc nokta NameError
            # ile 500 veriyordu. Gercek uc noktayla test yakaladi.
            _b = stok_bilgi_map.get(m.baglanti_id) if m.baglanti_id else None
            return (_b or {}).get('matrah') if _b else None

        def _maliyet_stok_tip(m):"""

IMZA = "'Alış Bedeli', 'Tutar', 'Döviz', 'USD Karşılık',"

print("═" * 70)
print(" ML1 · MALİYET: ALIŞ BEDELİ VE TOPLAMLAR")
print("═" * 70)
print()

ham = APP.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


if uyarla(IMZA) in ham or IMZA in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

icerik = ham
for _ad, _e, _y in (("dışa aktarım", ESKI, YENI),
                    ("alış bedeli çözücü", C_ESKI, C_YENI),
                    ("liste yanıtı", B_ESKI, B_YENI)):
    _eu = uyarla(_e)
    _n = icerik.count(_eu)
    if _n != 1:
        print(f" ✗ '{_ad}' kalıbı {_n} kez bulundu. DOSYAYA DOKUNULMADI.")
        sys.exit(1)
    icerik = icerik.replace(_eu, uyarla(_y), 1)

try:
    compile(icerik, 'flask_app.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print("  ✓ uygulanacak          dışa aktarıma Alış Bedeli sütunu")
print("  ✓ uygulanacak          matrahlar tek sorguda")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   venv/bin/python yama_ml1_maliyet.py --uygula")
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
print(" ⚠ templates/maliyet.html güncellenmeli (filtre + toplamlar).")
print("═" * 70)

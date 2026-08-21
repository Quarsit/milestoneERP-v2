#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — ÇAPRAZ DÖVİZ KAPATMA  ·  NK7
#
#  ── ÖLÇÜLEN DURUM ──
#    FIFO kapatma (cari, DOVIZ, yon) uclusune gore gruplaniyor.
#    Sonuc: TRY tahsilat, USD alacagi KAPATAMIYOR.
#
#    Olculdu (gercek uc noktayla, kur 40):
#        10.000 USD fatura + 200.000 TRY tahsilat
#          → USD beklenen giris  10.000  (degismedi)
#          → TRY tarafinda       200.000 alacak BOSTA
#
#    Musteri 5.000 USD borclu iken projeksiyon 10.000 USD alacak
#    gosteriyor; odenen 200.000 TRY hicbir yukumlulugu dusurmuyor.
#
#  ── KARAR (kullanici) ──
#    "TRY ödeme USD borca ÖDEME GÜNÜ KURU ile mahsup edilsin."
#
#  ── NEDEN ÖDEME GÜNÜ KURU ──
#    Musteri o gun eline gecen parayla borcunu kapatiyor; kac USD'ye
#    denk geldigi o gunku kurla belli olur. Fatura gunu kuruyla
#    mahsup etmek, aradaki kur hareketini yok saymak olurdu —
#    zaten `_kur_farki_hesapla_ve_olustur` o farki AYRI bir hareket
#    olarak yaziyor. Ikisini birlestirmek farki iki kez saymak
#    olurdu.
#
#  ── SIRA ÖNEMLİ: ÖNCE KENDİ DÖVİZİ ──
#    Bir yukumluluk once KENDI dovizindeki tahsilatlarla kapanir;
#    artan varsa capraz kapatmaya gecilir. Tersi olsaydi USD
#    tahsilat dururken TRY ile kapatip gereksiz kur cevrimi
#    yapardik.
#
#  ── KUR BULUNAMAZSA ÇEVRİM YAPILMAZ ──
#    `_kur_getir` bulamazsa 0 doner. 0 ile carpmak/bolmek tutari
#    sessizce sifirlar — bu projede NK6'da ayni tuzagi gorduk.
#    Kur yoksa capraz kapatma ATLANIR; yukumluluk oldugu gibi
#    gorunur. Yanlis rakam gostermektense eksik kapatma yeglenir.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python yama_nk7_capraz_kapatma.py            # rapor
#      venv/bin/python yama_nk7_capraz_kapatma.py --uygula
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

_h = APP.read_text(encoding='utf-8', errors='replace')
if '_nakit_rol' not in _h:
    print("✗ ÖN KOŞUL: önce yama_nk5_elle_hareket.py uygulanmalı.")
    sys.exit(1)

ESKI = """        for _anahtar, _hs in _yuk.items():
            _grup, _dv, _yon = _anahtar
            _kalan_kapatma = _kap.get(_anahtar, 0.0)"""

YENI = '''        # ── ÇAPRAZ DÖVİZ KAPATMA (NK7) ──
        # Kapatma havuzu (cari, DOVIZ, yon) uclusune gore
        # gruplaniyordu; TRY tahsilat USD alacagi kapatamiyordu.
        # Olculdu: 10.000 USD fatura + 200.000 TRY tahsilat sonrasi
        # USD alacak 10.000 kaliyor, 200.000 TRY bosta duruyordu.
        #
        # Artik kendi dovizinde artan kapatma, BASKA dovizdeki
        # yukumluluklere ODEME GUNU KURUYLA aktarilabiliyor.
        # Musteri o gun eline gecen parayla borcunu kapatir; kac
        # USD'ye denk geldigi o gunku kurla bellidir.
        _bugun_kur = {}

        def _kur_ile(tutar, kaynak_dv, hedef_dv):
            """kaynak_dv cinsinden tutari hedef_dv'ye cevirir.

            Kur bulunamazsa None doner — 0 ile carpmak tutari
            SESSIZCE sifirlardi (NK6'da ayni tuzagi gorduk).
            """
            if kaynak_dv == hedef_dv:
                return float(tutar)
            for _d in (kaynak_dv, hedef_dv):
                if _d not in _bugun_kur:
                    _bugun_kur[_d] = (1.0 if _d == 'TRY'
                                      else float(_kur_getir(_d) or 0))
            _k, _hd = _bugun_kur[kaynak_dv], _bugun_kur[hedef_dv]
            if _k <= 0 or _hd <= 0:
                return None
            return float(tutar) * _k / _hd

        for _anahtar, _hs in _yuk.items():
            _grup, _dv, _yon = _anahtar
            _kalan_kapatma = _kap.get(_anahtar, 0.0)

            # ÖNCE KENDİ DÖVİZİ, sonra çapraz.
            # Tersi olsaydi USD tahsilat dururken TRY ile kapatip
            # gereksiz kur cevrimi yapardik.
            _capraz = []
            for _k_anahtar, _k_tutar in _kap.items():
                if _k_anahtar == _anahtar or _k_tutar <= 0.005:
                    continue
                _kg, _kdv, _kyon = _k_anahtar
                if _kg != _grup or _kyon != _yon or _kdv == _dv:
                    continue
                _capraz.append(_k_anahtar)'''

# ── B) Yükümlülük döngüsünde çapraz havuzu kullan ──────────────────
B_ESKI = """                _tutar = float(h.borc or 0) if _yon == 'giris' else float(h.alacak or 0)
                if _kalan_kapatma > 0:
                    _dus = min(_tutar, _kalan_kapatma)
                    _tutar -= _dus
                    _kalan_kapatma -= _dus
                if _tutar <= 0.005:   # kurus artigi — kapanmis say
                    continue"""

B_YENI = """                _tutar = float(h.borc or 0) if _yon == 'giris' else float(h.alacak or 0)
                if _kalan_kapatma > 0:
                    _dus = min(_tutar, _kalan_kapatma)
                    _tutar -= _dus
                    _kalan_kapatma -= _dus

                # KENDI dovizi bittiyse CAPRAZ havuzlardan kapat.
                # Kapatilan tutar kaynak dovizinden DUSULUR ki ayni
                # para iki yukumlulugu kapatmasin.
                for _ca in _capraz:
                    if _tutar <= 0.005:
                        break
                    _havuz = _kap.get(_ca, 0.0)
                    if _havuz <= 0.005:
                        continue
                    _kdv = _ca[1]
                    _esdeger = _kur_ile(_havuz, _kdv, _dv)
                    if _esdeger is None:
                        continue      # kur yok — capraz kapatma ATLANIR
                    _dus = min(_tutar, _esdeger)
                    _tutar -= _dus
                    _geri = _kur_ile(_dus, _dv, _kdv)
                    _kap[_ca] = q3(max(0.0, _havuz - (_geri if _geri
                                                      is not None else 0.0)))

                if _tutar <= 0.005:   # kurus artigi — kapanmis say
                    continue"""

BLOKLAR = [
    ("çapraz kapatma havuzu", ESKI, YENI, '# ── ÇAPRAZ DÖVİZ KAPATMA (NK7) ──'),
    ("yükümlülük döngüsü",    B_ESKI, B_YENI, '# KENDI dovizi bittiyse CAPRAZ havuzlardan kapat.'),
]

print("═" * 70)
print(" NK7 · ÇAPRAZ DÖVİZ KAPATMA")
print("═" * 70)
print()

ham = APP.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


icerik = ham
plan, atlanan, sorunlu = [], [], []
for aciklama, eski, yeni, imza in BLOKLAR:
    if uyarla(imza) in icerik or imza in icerik:
        atlanan.append(aciklama)
        continue
    e = uyarla(eski)
    adet = icerik.count(e)
    if adet != 1:
        sorunlu.append((aciklama, adet))
        continue
    icerik = icerik.replace(e, uyarla(yeni), 1)
    plan.append(aciklama)

for a in atlanan:
    print(f"  ↷ atlandı (zaten var)  {a}")
for a in plan:
    print(f"  ✓ uygulanacak          {a}")
for a, n in sorunlu:
    print(f"  ✗ KALIP BULUNAMADI     {a}  (eşleşme: {n})")

print()
if sorunlu:
    print(f" ✗ {len(sorunlu)} blok yerleştirilemedi — DOSYAYA DOKUNULMADI.")
    sys.exit(1)
if not plan:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

try:
    compile(icerik, 'flask_app.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)
print(" ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   venv/bin/python yama_nk7_capraz_kapatma.py --uygula")
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
print(" TRY tahsilat artık USD alacağı ödeme günü kuruyla kapatıyor.")
print("═" * 70)

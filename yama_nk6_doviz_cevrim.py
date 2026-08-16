#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — DÖVİZ SÜZGECİ + ÇEVRİM  ·  NK6
#
#  ── ÖN KOŞUL ──
#      yama_nk5_elle_hareket.py --uygula
#
#  ── İKİ AYRI ŞEY ──
#
#    1) SÜZGEÇ (doviz=USD)
#       Yalnızca o dövizin satırlarını gösterir. Rakamlara
#       dokunmaz, sadece diğerlerini gizler. Risksiz.
#
#    2) ÇEVRİM (cevir=TRY)
#       TÜM dövizleri tek para birimine çevirip BİRLEŞTİRİR.
#       "Toplamda ne kadar param olacak" sorusunun cevabı.
#
#  ── ÇEVRİM NEDEN DİKKATLİ SUNULUYOR ──
#    Nakit akışı ekranı baştan beri üç dövizi AYRI gösteriyor,
#    çünkü toplamak kur riskini gizler: 100.000 USD alacak ile
#    100.000 TL gideri aynı satırda toplarsanız, kur %10 oynadığında
#    ne olacağını göremezsiniz.
#
#    Çevrim bu riski ORTADAN KALDIRMAZ, yalnızca tek bir ana göre
#    dondurur. Bu yüzden yanıt `cevrim` bloğunda hangi kurun
#    kullanıldığını ve tarihini AÇIKÇA döner; ekran da bunu yazar.
#    Rakam, kur bugünkü seviyede kalırsa geçerlidir.
#
#  ── KUR BULUNAMAZSA ──
#    _kur_getir bulamazsa 0 döner. 0'la çarpmak ya da bölmek tüm
#    tutarları sessizce sıfırlar — bu, yanlış rakam göstermenin en
#    kötü biçimi. O yüzden kur eksikse ÇEVRİM YAPILMAZ; istek
#    açık bir hata ile reddedilir.
#
#  KULLANIM (proje klasöründe):
#      python yama_nk6_doviz_cevrim.py            # rapor
#      python yama_nk6_doviz_cevrim.py --uygula
#
#  ⚠ templates/nakit.html'in GÜNCEL sürümü de kopyalanmalı.
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

# ── A) Süzgeç + çevrim ─────────────────────────────────────────────
A_ESKI = """        kalemler = _nakit_kalemleri(bas, son)

        # ── Vadesiz olanlari AYIR ──"""

A_YENI = '''        kalemler = _nakit_kalemleri(bas, son)

        # ── DOVIZ SUZGECI ve CEVRIM ──
        #
        # SUZGEC: yalnizca o dovizin satirlarini gosterir. Rakamlara
        #         dokunmaz; risksiz.
        # CEVRIM: tum dovizleri tek para birimine cevirip BIRLESTIRIR.
        #
        # Cevrim kur riskini ORTADAN KALDIRMAZ, bugunku kura gore
        # dondurur. Bu yuzden hangi kurun kullanildigi yanitta
        # aciklanir; ekran da bunu yazar.
        _suz = (request.args.get('doviz') or '').upper().strip()
        if _suz in ('', 'HEPSI', 'TUMU'):
            _suz = None
        _cev = (request.args.get('cevir') or '').upper().strip()
        if _cev in ('', 'HEPSI', 'TUMU'):
            _cev = None

        cevrim = None
        if _cev:
            # Cevrim icin gereken TUM kurlar bulunabiliyor mu?
            # _kur_getir bulamazsa 0 doner; 0 ile carpmak/bolmek tum
            # tutarlari SESSIZCE sifirlardi. Eksik kurla cevirmektense
            # acik hata vermek dogru.
            _dovizler = {x['doviz'] for x in kalemler} | set(acilis.keys()) | {_cev}
            _kurlar, _eksik = {}, []
            for _d in _dovizler:
                _k = float(_kur_getir(_d) or 0)
                if _k <= 0:
                    _eksik.append(_d)
                else:
                    _kurlar[_d] = _k
            if _eksik:
                # DIKKAT: bu fonksiyon Flask Response DONDURMEZ, duz
                # dict doner (cagiran jsonify ediyor). Buradan
                # `jsonify(...), 400` dondurmek cagirani cokertirdi.
                return {
                    'ok': False,
                    'hata': 'kur_eksik',
                    'mesaj': f"Çevrim yapılamadı: {', '.join(sorted(_eksik))} kuru "
                             f"bulunamadı. Kur güncellendikten sonra tekrar deneyin."
                }

            _hedef_kur = _kurlar[_cev]

            def _cevir(tutar, kaynak_doviz):
                # X birim A = X * kur(A) TL = X * kur(A) / kur(B) birim B
                return q3(float(tutar) * _kurlar[kaynak_doviz] / _hedef_kur)

            for x in kalemler:
                if x['doviz'] != _cev:
                    x['ozgun_tutar'] = x['tutar']
                    x['ozgun_doviz'] = x['doviz']
                    x['tutar'] = _cevir(x['tutar'], x['doviz'])
                    x['doviz'] = _cev
            _yeni_acilis = {}
            for _d, _v in acilis.items():
                _yeni_acilis[_cev] = q3(float(_yeni_acilis.get(_cev, 0))
                                        + float(_cevir(_v, _d)))
            acilis = _yeni_acilis or {_cev: q3(0)}
            cevrim = {
                'hedef': _cev,
                'kurlar': {_d: q3(_k) for _d, _k in _kurlar.items()},
                'tarih': date.today().isoformat(),
                'not': 'Tutarlar bugünkü kurla çevrildi; kur değişirse rakamlar değişir.',
            }

        if _suz:
            kalemler = [x for x in kalemler if x['doviz'] == _suz]
            acilis = {_d: _v for _d, _v in acilis.items() if _d == _suz}
            if _suz not in acilis:
                acilis[_suz] = q3(0)

        # ── Vadesiz olanlari AYIR ──'''

# ── B) Yanıta çevrim bilgisi ───────────────────────────────────────
B_ESKI = """            'kirilim': kirilim, 'ay': ay_sayisi,
            'acilis': acilis,"""
B_YENI = """            'kirilim': kirilim, 'ay': ay_sayisi,
            'doviz_suzgec': _suz, 'cevrim': cevrim,
            'acilis': acilis,"""

# ── C) Ekran rotası hatayı 400'e çevirsin ──────────────────────────
C_ESKI = """        return jsonify(_nakit_projeksiyon())"""
C_YENI = """        _sonuc = _nakit_projeksiyon()
        # Hesap basarisiz olduysa (or. cevrim kuru yok) 200 ile
        # donmek hatayi basari gibi gosterirdi.
        if not _sonuc.get('ok'):
            return jsonify(_sonuc), 400
        return jsonify(_sonuc)"""

# ── D) Dışa aktarma da aynı hatayı yutmasın ────────────────────────
D_ESKI = """            p = _nakit_projeksiyon(tam=(modul == 'nakit_detay'))
            kirilim = p['kirilim']"""
D_YENI = """            p = _nakit_projeksiyon(tam=(modul == 'nakit_detay'))
            if not p.get('ok'):
                return jsonify(p), 400
            kirilim = p['kirilim']"""

BLOKLAR = [
    ("döviz süzgeci + çevrim", A_ESKI, A_YENI, '# ── DOVIZ SUZGECI ve CEVRIM ──'),
    ("yanıta çevrim bilgisi",  B_ESKI, B_YENI, "'doviz_suzgec': _suz, 'cevrim': cevrim,"),
    ("ekran rotası hata yolu",  C_ESKI, C_YENI, "if not _sonuc.get('ok'):"),
    ("dışa aktarma hata yolu",  D_ESKI, D_YENI, "if not p.get('ok'):"),
]

print("═" * 70)
print(" NK6 · DÖVİZ SÜZGECİ + ÇEVRİM")
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
    print("   python yama_nk6_doviz_cevrim.py --uygula")
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
print("   ?doviz=USD   → yalnızca USD satırları")
print("   ?cevir=TRY   → hepsi TRY'ye çevrilmiş, tek çizgi")
print("═" * 70)

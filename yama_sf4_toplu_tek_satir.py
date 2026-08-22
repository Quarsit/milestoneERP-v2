#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — TOPLU KARŞI KAYIT TEK SATIR  ·  SF4
#
#  ── SORUN ──
#    Toplu silmede her stok icin AYRI karsi kayit aciliyor. 21
#    plaka silinince cari ekstresine 21 satir dusuyor ve gercek
#    hareketleri bogyor.
#
#  ── NEDEN TEK SATIR DOĞRU ──
#    Alis faturasi tarafinda bu kalip ZATEN kullaniliyor: 21 plakalik
#    alis, tek hareket + aciklamada "21 kalem". Karsi kayitta farkli
#    davranmak icin bir sebep yok — ayni fatura, ayni cari, ayni
#    islem.
#
#    Muhasebeten de dogrusu bu: tek bir duzeltme islemi, tek bir
#    yevmiye kaydi.
#
#  ── GRUPLAMA ANAHTARI ──
#    (cari_id, fatura_no, doviz). Ayni toplu islemde farkli
#    faturalara ait stoklar varsa HER FATURA icin ayri satir acilir
#    — birlestirmek, hangi faturanin ne kadar duzeltildigini
#    kaybetmek olurdu.
#
#  ── TEKLİ SİLME DEĞİŞMEZ ──
#    Tek stok silindiginde zaten tek satir olusuyordu; bu yama
#    yalnizca TOPLU yolu etkiler.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python yama_sf4_toplu_tek_satir.py            # rapor
#      venv/bin/python yama_sf4_toplu_tek_satir.py --uygula
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
if 'secim_bekleyen = []' not in _h:
    print("✗ ÖN KOŞUL: önce yama_sf3_toplu_mali.py uygulanmalı.")
    sys.exit(1)

# ── A) api_stok_sil: karşı kaydı BİRİKTİRME kipinde çalışabilsin ──
A_ESKI = """        elif _grup and _mali == 'karsi_kayit':
            _kk_t, _kk_k = _try_karsilik(_pay, _grup.doviz or 'TRY',
                                         tarih=date.today())
            db.session.add(CariHareket("""

A_YENI = """        elif _grup and _mali == 'karsi_kayit':
            # ── TOPLU İŞLEMDE BİRİKTİR (SF4) ──
            # Toplu silmede her stok icin ayri satir acmak, 21 plaka
            # silinince ekstreye 21 satir dusuruyor ve gercek
            # hareketleri boguyordu. Alis faturasi tarafinda zaten
            # "tek hareket + N kalem" kalibi var; karsi kayitta
            # farkli davranmanin sebebi yok.
            #
            # `kk_biriktir` verilmisse kayit ACILMAZ, cagirana
            # bildirilir; toplu silme sonunda TEK satir acar.
            if kk_biriktir is not None:
                kk_biriktir.append({
                    'cari_id': _grup.cari_id, 'cari_unvan': _grup.cari_unvan,
                    'doviz': _grup.doviz or 'TRY', 'fatura_no': _fno,
                    'pay': _pay, 'stok_id': stok_id})
                _grup.kalem_sayisi = max(
                    0, (getattr(_grup, 'kalem_sayisi', 1) or 1) - 1)
                _grup = None
            else:
                _kk_t, _kk_k = _try_karsilik(_pay, _grup.doviz or 'TRY',
                                             tarih=date.today())
                db.session.add(CariHareket("""

# ── B) İmzaya parametre ──
B_ESKI = """    def api_stok_sil(tip, stok_id, mali_islem=None):"""
B_YENI = """    def api_stok_sil(tip, stok_id, mali_islem=None, kk_biriktir=None):"""

# ── C) Girinti düzeltmesi: eski blok else altına indi ──
C_ESKI = """                aciklama=f'{_fno} · stok çıkışı karşı kaydı '
                         f'({getattr(stok, "id", "")})',
                kullanici=session.get('kullanici')))
            # Orijinal harekete DOKUNULMAZ; yalnizca kalem sayaci
            # azalir ki son kalemde grup yanlislikla silinmesin.
            _grup.kalem_sayisi = max(0, (getattr(_grup, 'kalem_sayisi', 1) or 1) - 1)
            _grup = None"""

C_YENI = """                    aciklama=f'{_fno} · stok çıkışı karşı kaydı '
                             f'({getattr(stok, "id", "")})',
                    kullanici=session.get('kullanici')))
                # Orijinal harekete DOKUNULMAZ; yalnizca kalem sayaci
                # azalir ki son kalemde grup yanlislikla silinmesin.
                _grup.kalem_sayisi = max(
                    0, (getattr(_grup, 'kalem_sayisi', 1) or 1) - 1)
                _grup = None"""

# ── D) Toplu silme: biriktir ve sonda tek satır aç ──
D_ESKI = """        secim_bekleyen = []
        for sid in idler:
            try:
                sonuc = api_stok_sil(tip, sid, mali_islem=_toplu_mali)"""

D_YENI = """        secim_bekleyen = []
        # SF4: karsi kayitlar biriktirilir, sonda TEK satir acilir.
        _kk_havuz = [] if _toplu_mali == 'karsi_kayit' else None
        for sid in idler:
            try:
                sonuc = api_stok_sil(tip, sid, mali_islem=_toplu_mali,
                                     kk_biriktir=_kk_havuz)"""

# ── E) Havuzu tek satıra çevir ──
E_ESKI = """        mesaj = f'{len(silinen)} stok silindi'"""

E_YENI = """        # ── BİRİKTİRİLEN KARŞI KAYITLARI TEK SATIRA TOPLA (SF4) ──
        # Gruplama anahtari (cari_id, fatura_no, doviz): ayni toplu
        # islemde FARKLI faturalar varsa her biri AYRI satir olur —
        # birlestirmek, hangi faturanin ne kadar duzeltildigini
        # kaybetmek olurdu.
        if _kk_havuz:
            _gruplu = {}
            for _k in _kk_havuz:
                _a = (_k['cari_id'], _k['fatura_no'], _k['doviz'])
                _g = _gruplu.setdefault(_a, {'tutar': 0.0, 'adet': 0,
                                             'unvan': _k['cari_unvan']})
                _g['tutar'] += float(_k['pay'] or 0)
                _g['adet'] += 1
            for (_cid, _fn, _dv), _g in _gruplu.items():
                _tut = q3(_g['tutar'])
                _t, _k2 = _try_karsilik(_tut, _dv, tarih=date.today())
                db.session.add(CariHareket(
                    id=_yeni_id('HR'), hareket_tarihi=date.today(),
                    cari_id=_cid, cari_unvan=_g['unvan'],
                    islem_tip='Alis Iade / Duzeltme',
                    borc=_tut, alacak=0, doviz=_dv,
                    borc_try=_t, kur_uygulanan=_k2,
                    vade_tarihi=date.today(),
                    kaynak='stok_karsi_kayit',
                    baglanti_tip='stok_fatura', baglanti_id=_fn,
                    aciklama=f'{_fn} · stok çıkışı karşı kaydı '
                             f'· {_g["adet"]} kalem',
                    kullanici=session.get('kullanici')))
            _safe_commit(f'Toplu karsi kayit: {len(_gruplu)} satir')

        mesaj = f'{len(silinen)} stok silindi'"""

BLOKLAR = [
    ("imzaya kk_biriktir",        B_ESKI, B_YENI, 'kk_biriktir=None'),
    ("karşı kayıt biriktirme",    A_ESKI, A_YENI, '# ── TOPLU İŞLEMDE BİRİKTİR (SF4) ──'),
    ("girinti düzeltmesi",        C_ESKI, C_YENI, "                    kullanici=session.get('kullanici')))"),
    ("toplu silme havuzu",        D_ESKI, D_YENI, '_kk_havuz = [] if _toplu_mali'),
    ("havuzu tek satıra topla",   E_ESKI, E_YENI, '# ── BİRİKTİRİLEN KARŞI KAYITLARI TEK SATIRA TOPLA (SF4) ──'),
]

print("═" * 70)
print(" SF4 · TOPLU KARŞI KAYIT TEK SATIR")
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
    print("   venv/bin/python yama_sf4_toplu_tek_satir.py --uygula")
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
print("═" * 70)

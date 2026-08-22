#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — STOK ALIŞ BORCU TAHSİLAT EKRANINDA  ·  AF1
#
#  ── ÖLÇÜLEN HATA (üretimde görüldü) ──
#    Stok kaydi yapilinca cariye borc olusuyor, ama tahsilat/odeme
#    ekraninda o borc LISTELENMIYOR — kullanici odemeyi hangi
#    faturaya mahsup edecegini secemiyor.
#
#    Sebep: stok alisi `Fatura` tablosunda kayit ACMIYOR; borcu
#    dogrudan `CariHareket` olarak yaziyor (baglanti_tip=
#    'stok_fatura'). `/acik_faturalar` ucu ise YALNIZCA `Fatura`
#    tablosuna bakiyordu.
#
#    Olculdu: 6.535,60 USD borc var, uc nokta 0 kayit donuyor.
#
#  ── DÜZELTME ──
#    Uc nokta artik stok alis borclarini da dondurüyor. Bunlar
#    `kaynak='stok_fatura'` ile isaretli cari hareketler; her biri
#    bir alis faturasini temsil ediyor (aciklamada "N kalem").
#
#    Kalan tutar = alacak − o harekete yapilmis odemeler. Odemeler
#    `baglanti_id` ile ayni fatura numarasina bagli.
#
#  ── NEDEN 'Fatura' KAYDI AÇMIYORUZ ──
#    Acmak daha temiz gorunurdu ama stok alisinda fatura numarasi
#    cogu zaman HENUZ BELLI DEGIL ("Beklenen Fatura 1"). Sahte
#    fatura kaydi uretmek, fatura listesini gercek olmayan
#    belgelerle doldurmak olurdu. Borcu cari harekette tutmak
#    dogru; eksik olan yalnizca TAHSILAT EKRANINDA GORUNMEMESIYDI.
#
#  ── YÖN ──
#    Stok alisi TEDARIKCIYE borctur; yalnizca yon='alis' istendiginde
#    donuyor. Satis tahsilatinda gostermek yanlis olurdu.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python yama_af1_stok_borcu.py            # rapor
#      venv/bin/python yama_af1_stok_borcu.py --uygula
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

ESKI = """        yon = request.args.get('yon', 'satis')  # satis | alis
        # Cari unvanına göre açık faturalar (Kesildi veya Kısmi Tahsil)
        faturalar = Fatura.query.filter("""

YENI = '''        yon = request.args.get('yon', 'satis')  # satis | alis

        # ── STOK ALIŞ BORÇLARI (AF1) ──
        # Stok kaydi `Fatura` tablosunda kayit ACMAZ; borcu dogrudan
        # CariHareket olarak yazar (kaynak='stok_fatura'). Bu uc
        # nokta yalnizca Fatura tablosuna baktigi icin o borclar
        # tahsilat ekraninda GORUNMUYORDU — kullanici odemeyi hangi
        # alisa mahsup edecegini secemiyordu.
        #
        # Fatura kaydi uretmek daha temiz gorunurdu ama stok
        # alisinda fatura numarasi cogu zaman HENUZ BELLI DEGIL
        # ("Beklenen Fatura 1"); sahte kayit fatura listesini
        # gercek olmayan belgelerle doldururdu.
        stok_borclari = []
        if yon == 'alis':
            for h in CariHareket.query.filter(
                    CariHareket.cari_id == cari_id,
                    # DIKKAT: `kaynak` degeri 'stok'tur, 'stok_fatura'
                    # DEGIL — 'stok_fatura' olan `baglanti_tip`.
                    # Ilk surumde kaynak'a gore filtreledim ve liste
                    # BOS geldi; uretimde goruldu.
                    CariHareket.baglanti_tip == 'stok_fatura',
                    CariHareket.alacak > 0).order_by(
                        CariHareket.hareket_tarihi).all():
                _fno = h.baglanti_id or h.id
                # Bu alisa yapilmis ODEMELER: ayni fatura numarasina
                # bagli borc hareketleri (odeme = bizim borcumuzu
                # azaltir).
                _odenen = db.session.query(
                    db.func.sum(CariHareket.borc)).filter(
                    CariHareket.cari_id == cari_id,
                    CariHareket.baglanti_tip == 'stok_fatura',
                    CariHareket.baglanti_id == _fno,
                    # Alis hareketinin KENDISI haric; odemeler
                    # borc sutununda ve kaynak 'stok' degil.
                    CariHareket.kaynak != 'stok').scalar() or 0
                _kalan = q3(float(h.alacak or 0) - float(_odenen))
                if _kalan <= 0.01:
                    continue
                stok_borclari.append({
                    'id': h.id, 'fatura_no': _fno,
                    'toplam': q3(h.alacak or 0), 'odenen': q3(_odenen),
                    'kalan': _kalan, 'doviz': h.doviz or 'USD',
                    'tarih': (h.hareket_tarihi.strftime('%d.%m.%Y')
                              if h.hareket_tarihi else ''),
                    'durum': 'Stok Alışı',
                    'kaynak': 'stok_fatura',
                    'aciklama': h.aciklama or ''})

        # Cari unvanına göre açık faturalar (Kesildi veya Kısmi Tahsil)
        faturalar = Fatura.query.filter('''

# ── D) api_hareket_ekle stok alis borcuna BAGLAYABILSIN ──
#  Ekran odemeyi `baglanti_tip='stok_fatura'` ile gonderiyor ama uc
#  nokta bu alanlari OKUMUYORDU; odeme borca baglanmiyor ve acik
#  borc listesinden dusmuyordu.
D_ESKI = """        # Fatura olusturulduysa cari hareketi ona bagla (cift kayit korumasi icin)
        if fatura_id:
            hareket.baglanti_tip = 'fatura'"""
D_YENI = """        # AF1: STOK ALIS BORCUNA MAHSUP.
        # Odeme ekrani stok alis borcunu secince bu alanlari
        # gonderiyor; okunmazsa odeme borca baglanmaz ve acik borc
        # listesinden DUSMEZDI.
        _bg_tip = (data.get('baglanti_tip') or '').strip()
        if _bg_tip == 'stok_fatura' and data.get('baglanti_id'):
            hareket.baglanti_tip = 'stok_fatura'
            hareket.baglanti_id = str(data.get('baglanti_id')).strip()

        # Fatura olusturulduysa cari hareketi ona bagla (cift kayit korumasi icin)
        if fatura_id:
            hareket.baglanti_tip = 'fatura'"""

# Sonuca ekle
B_ESKI = """            sonuc.append({
                'id': f.id, 'fatura_no': f.fatura_no or f.id,"""
B_YENI = """            sonuc.append({
                'kaynak': 'fatura',
                'id': f.id, 'fatura_no': f.fatura_no or f.id,"""

IMZA = '# ── STOK ALIŞ BORÇLARI (AF1) ──'

print("═" * 70)
print(" AF1 · STOK ALIŞ BORCU TAHSİLAT EKRANINDA")
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
for _ad, _e, _y in (("stok alış borçları", ESKI, YENI),
                    ("fatura satırına kaynak", B_ESKI, B_YENI),
                    ("ödemeyi stok borcuna bağla", D_ESKI, D_YENI)):
    _eu = uyarla(_e)
    _n = icerik.count(_eu)
    if _n != 1:
        print(f" ✗ '{_ad}' kalıbı {_n} kez bulundu. DOSYAYA DOKUNULMADI.")
        sys.exit(1)
    icerik = icerik.replace(_eu, uyarla(_y), 1)

# Dönüş: iki listeyi birleştir
C_ESKI = uyarla("""        return jsonify({'ok': True, 'faturalar': sonuc""")
C_YENI = uyarla("""        # Stok alis borclari EN ONE: genelde daha eski ve
        # kullanicinin aradigi kayit bu.
        sonuc = stok_borclari + sonuc
        return jsonify({'ok': True, 'faturalar': sonuc""")
if icerik.count(C_ESKI) != 1:
    print(f" ✗ Dönüş kalıbı {icerik.count(C_ESKI)} kez bulundu. DOSYAYA DOKUNULMADI.")
    sys.exit(1)
icerik = icerik.replace(C_ESKI, C_YENI, 1)

try:
    compile(icerik, 'flask_app.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print("  ✓ uygulanacak          stok alış borçları listeye eklendi")
print("  ✓ uygulanacak          kaynak alanı (fatura / stok_fatura)")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   venv/bin/python yama_af1_stok_borcu.py --uygula")
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

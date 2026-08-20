#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — KAYIP AKIŞI VE DÖNÜŞÜM ORANI  ·  PF3
#
#  ── ÖN KOŞUL ──
#      yama_pf2_kayip.py --uygula  +  goc.py uygula
#
#  ── EKLENENLER ──
#    'Kaybedildi' durumu + kayip kaydi ucu:
#        POST /api/proforma/<id>/kaybedildi   {sebep, not}
#        POST /api/proforma/<id>/geri_al      (yanlislikla isaretlendiyse)
#        GET  /api/rapor/donusum              kazanma orani
#
#  ── SEBEP ZORUNLU ──
#    Sebepsiz kayip kaydi, kaybedildigini bilmekten baska bir sey
#    ogretmez. Asil deger "neden": fiyat mi, termin mi, rakip mi.
#    Sebep girilmeden kaybedildi isaretlenemez.
#
#  ── NEDEN ELLE DURUM DEĞİL, AYRI UÇ NOKTA ──
#    'Kaybedildi' de PF1'deki gibi SISTEM DURUMU sayilip elle
#    atanamiyor. Sebebi: sebep alani zorunlu ve durum ucu serbest
#    metin kabul etseydi sebepsiz kayit girebilirdi. Ayri uc nokta
#    sebebi zorunlu kilar.
#
#  ── DÖNÜŞÜM ORANI ──
#    kazanilan = 'Siparise Donustu' + 'Faturalandi'
#    kaybedilen = 'Kaybedildi'
#    oran = kazanilan / (kazanilan + kaybedilen)
#
#    'Iptal' PAYDAYA GIRMEZ: iptal, teklifi GERI CEKMEK demek —
#    musteri baskasini secmedi, biz vazgectik. Kayipla ayni kutuya
#    koymak orani yanlis dusururdu.
#
#    Bekleyen teklifler de paydaya girmez: henuz sonuclanmadilar,
#    kayip sayilamazlar.
#
#  KULLANIM (proje klasöründe):
#      python yama_pf3_kayip_akis.py            # rapor
#      python yama_pf3_kayip_akis.py --uygula
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
if 'SISTEM_DURUMLARI' not in _h:
    print("✗ ÖN KOŞUL: önce yama_pf1_akis.py uygulanmalı.")
    sys.exit(1)

# ── A) Geçerli durumlar + geçiş haritası ───────────────────────────
A_ESKI = """        gecerli_durumlar = ['Taslak', 'Ic Onay', 'Gonderildi', 'Onaylandi',
                            'Siparise Donustu', 'Faturalandi', 'Iptal', 'Revize']"""
A_YENI = """        gecerli_durumlar = ['Taslak', 'Ic Onay', 'Gonderildi', 'Onaylandi',
                            'Siparise Donustu', 'Faturalandi', 'Kaybedildi',
                            'Iptal', 'Revize']"""

B_ESKI = """            'Onaylandi':       ['Gonderildi', 'Ic Onay', 'Iptal'],
            'Gonderildi':      ['Onaylandi', 'Iptal'],"""
B_YENI = """            # 'Kaybedildi' ELLE HEDEF DEGIL — /kaybedildi ucu yazar
            # (sebep zorunlu oldugu icin).
            'Onaylandi':       ['Gonderildi', 'Ic Onay', 'Iptal'],
            'Gonderildi':      ['Onaylandi', 'Iptal'],
            # Kaybedilen teklif geri acilabilir: musteri fikir
            # degistirebilir. /geri_al ucu kullanilir.
            'Kaybedildi':      ['Iptal'],"""

C_ESKI = """            'Siparise Donustu': 'Bu durum siparişe dönüştürüldüğünde sistem '
                                'tarafından atanır. "Siparişe Dönüştür" '
                                'düğmesini kullanın.',
        }"""
C_YENI = """            'Siparise Donustu': 'Bu durum siparişe dönüştürüldüğünde sistem '
                                'tarafından atanır. "Siparişe Dönüştür" '
                                'düğmesini kullanın.',
            # Sebepsiz kayip kaydi, kaybedildigini bilmekten baska bir
            # sey ogretmez. Ayri uc nokta sebebi ZORUNLU kilar.
            'Kaybedildi': 'Kayıp kaydı için "Kaybedildi" düğmesini kullanın; '
                          'sebep girilmesi zorunludur.',
        }"""

# ── D) Uç noktalar ─────────────────────────────────────────────────
D_ESKI = """    @app.route('/api/proforma/<proforma_id>/siparise_donustur'"""

D_YENI = '''    KAYIP_SEBEPLERI = ('fiyat', 'termin', 'rakip', 'musteri_vazgecti',
                       'stok_yok', 'diger')

    @app.route('/api/proforma/<proforma_id>/kaybedildi', methods=['POST'])
    def api_proforma_kaybedildi(proforma_id):
        """Teklifi KAYBEDILDI olarak isaretler. Sebep ZORUNLU.

        'Iptal' ile ayni sey DEGIL: iptal teklifi GERI CEKMEK,
        kayip MUSTERININ BASKASINI SECMESI. Ayni kutuya koymak
        kazanma oranini olculemez yapar.
        """
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('proforma', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        p = db.session.get(Proforma, proforma_id)
        if not p:
            return jsonify({'ok': False, 'mesaj': 'Proforma bulunamadı'}), 404

        # Kazanilmis teklif kaybedilmis olamaz.
        if p.durum in ('Siparise Donustu', 'Faturalandi'):
            return jsonify({'ok': False,
                            'mesaj': f'Bu teklif kazanılmış ({p.durum}); '
                                     f'kayıp olarak işaretlenemez.'}), 400
        if p.durum in ('Iptal', 'Revize'):
            return jsonify({'ok': False,
                            'mesaj': f'"{p.durum}" durumundaki teklif kayıp '
                                     f'olarak işaretlenemez.'}), 400

        d = request.json or {}
        sebep = (d.get('sebep') or '').strip().lower()
        if sebep not in KAYIP_SEBEPLERI:
            return jsonify({
                'ok': False,
                'mesaj': f"Kayıp sebebi zorunlu. Geçerli: "
                         f"{', '.join(KAYIP_SEBEPLERI)}"}), 400

        eski = p.durum
        p.durum = 'Kaybedildi'
        p.kayip_sebep = sebep
        p.kayip_not = (d.get('not') or d.get('kayip_not') or '').strip() or None
        p.kayip_tarihi = _parse_date(d.get('tarih')) or date.today()

        ok, hata = _safe_commit(f'Proforma kaybedildi: {proforma_id}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        app.logger.info(f'[KAYIP] {proforma_id}: {eski} -> Kaybedildi ({sebep})')
        return jsonify({'ok': True, 'durum': p.durum, 'sebep': sebep,
                        'mesaj': f'Teklif kayıp olarak işaretlendi ({sebep})'})

    @app.route('/api/proforma/<proforma_id>/kaybi_geri_al', methods=['POST'])
    def api_proforma_kaybi_geri_al(proforma_id):
        """Yanlislikla kaybedildi isaretlenmis teklifi geri acar.

        Musteri fikir degistirebilir; kayip kaydi geri alinamaz
        olsaydi kullanici yeni teklif acmak zorunda kalir ve
        gecmis kopardi.
        """
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('proforma', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        p = db.session.get(Proforma, proforma_id)
        if not p:
            return jsonify({'ok': False, 'mesaj': 'Proforma bulunamadı'}), 404
        if p.durum != 'Kaybedildi':
            return jsonify({'ok': False,
                            'mesaj': f'Bu teklif kayıp değil (durum: {p.durum})'}), 400
        p.durum = 'Onaylandi' if p.siparis_id else 'Gonderildi'
        p.kayip_sebep = None
        p.kayip_not = None
        p.kayip_tarihi = None
        ok, hata = _safe_commit(f'Proforma kayip geri alindi: {proforma_id}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True, 'durum': p.durum,
                        'mesaj': f'Kayıp kaydı geri alındı; durum: {p.durum}'})

    @app.route('/api/rapor/donusum', methods=['GET'])
    def api_rapor_donusum():
        """Teklif donusum orani ve kayip sebepleri.

        PAYDA KASITLI OLARAK DAR:
          · 'Iptal' girmez — iptal teklifi GERI CEKMEK demek;
            musteri baskasini secmedi, biz vazgectik. Kayipla ayni
            saymak orani yanlis dusururdu.
          · Bekleyen teklifler girmez — henuz sonuclanmadilar.
        """
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('proforma', 'okuma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403

        bas = _parse_date(request.args.get('baslangic'))
        son = _parse_date(request.args.get('bitis'))
        q = Proforma.query.filter(Proforma.aktif_surum.isnot(False))
        if bas:
            q = q.filter(Proforma.olusturma >= bas)
        if son:
            q = q.filter(Proforma.olusturma <= son)
        temsilci = (request.args.get('temsilci') or '').strip()
        if temsilci:
            q = q.filter(Proforma.temsilci == temsilci)
        hepsi = q.all()

        KAZANILAN = ('Siparise Donustu', 'Faturalandi')
        kazanilan = [p for p in hepsi if p.durum in KAZANILAN]
        kaybedilen = [p for p in hepsi if p.durum == 'Kaybedildi']
        iptal = [p for p in hepsi if p.durum == 'Iptal']
        bekleyen = [p for p in hepsi
                    if p.durum not in KAZANILAN + ('Kaybedildi', 'Iptal', 'Revize')]

        sonuclanan = len(kazanilan) + len(kaybedilen)
        oran = round(100.0 * len(kazanilan) / sonuclanan, 1) if sonuclanan else None

        sebepler = {}
        for p in kaybedilen:
            s = p.kayip_sebep or 'belirtilmemis'
            sebepler[s] = sebepler.get(s, 0) + 1

        temsilciler = {}
        for p in hepsi:
            t = p.temsilci or '(atanmamış)'
            k = temsilciler.setdefault(t, {'kazanilan': 0, 'kaybedilen': 0,
                                           'bekleyen': 0})
            if p.durum in KAZANILAN:
                k['kazanilan'] += 1
            elif p.durum == 'Kaybedildi':
                k['kaybedilen'] += 1
            elif p in bekleyen:
                k['bekleyen'] += 1

        return jsonify({
            'ok': True,
            'kazanilan': len(kazanilan), 'kaybedilen': len(kaybedilen),
            'bekleyen': len(bekleyen), 'iptal': len(iptal),
            'sonuclanan': sonuclanan,
            'donusum_orani': oran,
            'kayip_sebepleri': dict(sorted(sebepler.items(),
                                           key=lambda x: -x[1])),
            'temsilciler': temsilciler,
            'not': "İptal edilen teklifler orana KATILMAZ: iptal, teklifi "
                   "geri çekmektir; kayıp, müşterinin başkasını seçmesidir.",
        })

    @app.route('/api/proforma/<proforma_id>/siparise_donustur\''''

# ── E) Oluştururken temsilciyi yaz ─────────────────────────────────
# Temsilci, Proforma(...) cagrisina DOGRUDAN eklenir.
# Ilk surum `GECERLI_URUN_TIP` capasini kullaniyordu ama o kalip
# IKI uc noktada var (ekle + guncelle) ve guncellemede temsilciyi
# EZMEK yanlis olurdu: teklifi hazirlayan kisi, sonradan duzenleyen
# kisi degildir.
E_ESKI = """        p = Proforma(id=_yeni_id('PI'), musteri=data['musteri'], musteri_adres=data.get('musteri_adres'),"""
E_YENI = """        p = Proforma(id=_yeni_id('PI'), musteri=data['musteri'],
                     # Teklifi HAZIRLAYAN oturumdan yazilir; istemciden
                     # almak baskasi adina teklif kaydedilmesine izin
                     # verirdi. GUNCELLEMEDE ezilmez — hazirlayan ile
                     # sonradan duzenleyen ayri kisilerdir.
                     temsilci=session.get('kullanici'),
                     musteri_adres=data.get('musteri_adres'),"""

BLOKLAR = [
    ("geçerli durumlar",     A_ESKI, A_YENI, "'Kaybedildi',\n                            'Iptal'"),
    ("geçiş haritası",       B_ESKI, B_YENI, "'Kaybedildi':      ['Iptal'],"),
    ("elle atanamaz",        C_ESKI, C_YENI, "'Kaybedildi': 'Kayıp kaydı için"),
    ("kayıp + dönüşüm uçları", D_ESKI, D_YENI, 'def api_proforma_kaybedildi('),
    ("temsilci oturumdan",   E_ESKI, E_YENI, "temsilci=session.get('kullanici'),"),
]

print("═" * 70)
print(" PF3 · KAYIP AKIŞI VE DÖNÜŞÜM ORANI")
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
    print("   python yama_pf3_kayip_akis.py --uygula")
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

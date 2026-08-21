#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — MÜŞTERİ 360  ·  M360 (veri)
#
#  ── NE VERİR ──
#    Bir musteri hakkinda satis ekibinin sormasi gereken sorular:
#      · Bu musteri NE aliyor?        (cins/yuzey dagilimi)
#      · KACA veriyoruz?              (urun bazli fiyat gecmisi)
#      · EN SON ne zaman aldi?        (sessizlesme)
#      · Teklif → siparis oraniniz?   (musteri bazli donusum)
#
#  ── HİÇBİRİ SAKLANMIYOR — HEPSİ HESAPLANIYOR ──
#    Kaynak: SatisKaydi (cins, ozellik, birim_fiyat, doviz, tarih,
#    cari_id) ve Proforma (durum, kayip_sebep).
#
#    Bu KASITLI. Ozet tabloya yazsaydik, kaynak degistiginde kopya
#    eskirdi — bu projede tam olarak o sinifin bes ayri hatasini
#    duzelttik: fatura/tahsilat cift sayimi, `kapatildi` celiskisi,
#    olu cekte iki bakiye, isimle bagli musteri gecmisi, ana kasa
#    bakiyesi. Ozet, veri degil GORUNUMDUR.
#
#  ── FİYAT GEÇMİŞİ DÖVİZ AYRIMLI ──
#    Ayni cinsi bir musteriye USD, digerine EUR vermis olabilirsiniz.
#    Ortalama almak icin dovizleri toplamak, bu projede defalarca
#    duzelttigimiz hatanin aynisi olurdu. Her doviz AYRI.
#
#  ── ERİŞİM ──
#    'crm' yetkisi. Finansal alan (bakiye, borc, risk) DONMEZ —
#    /api/crm/musteri ile ayni kural.
#
#  KULLANIM (proje klasöründe):
#      python yama_m360_veri.py            # rapor
#      python yama_m360_veri.py --uygula
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
if 'def api_crm_musteri(' not in _h:
    print("✗ ÖN KOŞUL: önce yama_crm_h_musteri.py uygulanmalı.")
    sys.exit(1)
if 'kayip_sebep' not in _h:
    print("✗ ÖN KOŞUL: önce yama_pf3_kayip_akis.py uygulanmalı.")
    sys.exit(1)

ESKI = """    @app.route('/musteri')"""

YENI = '''    @app.route('/api/crm/musteri/<cari_id>/ozet', methods=['GET'])
    def api_crm_musteri_ozet(cari_id):
        """Musteri 360 — urun tercihi, fiyat gecmisi, donusum.

        HICBIRI SAKLANMIYOR, hepsi mevcut veriden hesaplaniyor.
        Ozet tabloya yazsaydik kaynak degistiginde kopya eskirdi;
        bu projede tam olarak o sinifin bes ayri hatasini duzelttik.

        FINANSAL ALAN DONMEZ — /api/crm/musteri ile ayni kural.
        """
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('crm', 'okuma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        c = db.session.get(Cari, cari_id)
        if not c or not _cari_gorulebilir_mi(cari_id):
            return jsonify({'ok': False, 'mesaj': 'Müşteri bulunamadı'}), 404

        bugun = date.today()
        satislar = SatisKaydi.query.filter_by(cari_id=cari_id).all()

        # ── ÜRÜN TERCİHİ ──
        # Neyi ne kadar aliyor. Miktar birimi urune gore degistigi
        # icin (m2 / m3 / ton) ADET ve TUTAR ayri tutuluyor;
        # farkli birimleri toplamak anlamsiz olurdu.
        urunler = {}
        for s in satislar:
            anahtar = ((s.cins or '—').strip(),
                       (s.ozellik or '').strip() or '—')
            u = urunler.setdefault(anahtar, {
                'cins': anahtar[0], 'ozellik': anahtar[1],
                'adet': 0, 'tutar': {}, 'son_tarih': None})
            u['adet'] += 1
            dv = (s.doviz or 'USD').upper()
            u['tutar'][dv] = q3(float(u['tutar'].get(dv, 0))
                                + float(s.tutar or 0))
            if s.satis_tarihi and (u['son_tarih'] is None
                                   or s.satis_tarihi > u['son_tarih']):
                u['son_tarih'] = s.satis_tarihi

        urun_listesi = []
        for (cins, ozellik), u in urunler.items():
            urun_listesi.append({
                'cins': cins, 'ozellik': ozellik, 'adet': u['adet'],
                'tutar': u['tutar'],
                'son_tarih': u['son_tarih'].isoformat() if u['son_tarih'] else None,
            })
        urun_listesi.sort(key=lambda x: -x['adet'])

        # ── FİYAT GEÇMİŞİ ──
        # DOVIZLER AYRI. Ayni cinsi bir musteriye USD, digerine EUR
        # vermis olabilirsiniz; ortalama icin toplamak bu projede
        # defalarca duzelttigimiz hatanin aynisi olurdu.
        fiyatlar = {}
        for s in satislar:
            if not s.birim_fiyat:
                continue
            dv = (s.doviz or 'USD').upper()
            anahtar = f"{(s.cins or '—').strip()}|{(s.ozellik or '').strip() or '—'}|{dv}"
            f = fiyatlar.setdefault(anahtar, {
                'cins': (s.cins or '—').strip(),
                'ozellik': (s.ozellik or '').strip() or '—',
                'doviz': dv, 'birim': s.birim or '',
                'fiyatlar': [], 'son_fiyat': None, 'son_tarih': None})
            f['fiyatlar'].append(float(s.birim_fiyat))
            if s.satis_tarihi and (f['son_tarih'] is None
                                   or s.satis_tarihi > f['son_tarih']):
                f['son_tarih'] = s.satis_tarihi
                f['son_fiyat'] = q3(float(s.birim_fiyat))

        fiyat_listesi = []
        for f in fiyatlar.values():
            fl = f['fiyatlar']
            fiyat_listesi.append({
                'cins': f['cins'], 'ozellik': f['ozellik'],
                'doviz': f['doviz'], 'birim': f['birim'],
                'satis_sayisi': len(fl),
                'en_dusuk': q3(min(fl)), 'en_yuksek': q3(max(fl)),
                'ortalama': q3(sum(fl) / len(fl)),
                'son_fiyat': f['son_fiyat'],
                'son_tarih': f['son_tarih'].isoformat() if f['son_tarih'] else None,
            })
        fiyat_listesi.sort(key=lambda x: (x['cins'], x['doviz']))

        # ── DÖNÜŞÜM (müşteri bazlı) ──
        # PF3'teki kural birebir: 'Iptal' paydaya GIRMEZ (teklifi
        # geri cekmek, kaybetmek degil), bekleyen de girmez.
        proformalar = Proforma.query.filter(
            Proforma.cari_id == cari_id,
            Proforma.aktif_surum.isnot(False)).all()
        KAZANILAN = ('Siparise Donustu', 'Faturalandi')
        kazanilan = [p for p in proformalar if p.durum in KAZANILAN]
        kaybedilen = [p for p in proformalar if p.durum == 'Kaybedildi']
        sonuclanan = len(kazanilan) + len(kaybedilen)
        sebepler = {}
        for p in kaybedilen:
            s = p.kayip_sebep or 'belirtilmemis'
            sebepler[s] = sebepler.get(s, 0) + 1

        son_satis = max((s.satis_tarihi for s in satislar if s.satis_tarihi),
                        default=None)
        ilk_satis = min((s.satis_tarihi for s in satislar if s.satis_tarihi),
                        default=None)

        return jsonify({
            'ok': True,
            'cari': {'id': c.id, 'unvan': c.unvan, 'ulke': c.ulke,
                     'sorumlu': c.sorumlu},
            'ozet': {
                'satis_sayisi': len(satislar),
                'ilk_satis': ilk_satis.isoformat() if ilk_satis else None,
                'son_satis': son_satis.isoformat() if son_satis else None,
                'temassiz_gun': (bugun - son_satis).days if son_satis else None,
                'farkli_urun': len(urun_listesi),
            },
            'urunler': urun_listesi[:20],
            'fiyatlar': fiyat_listesi[:20],
            'donusum': {
                'kazanilan': len(kazanilan), 'kaybedilen': len(kaybedilen),
                'sonuclanan': sonuclanan,
                'oran': (round(100.0 * len(kazanilan) / sonuclanan, 1)
                         if sonuclanan else None),
                'kayip_sebepleri': dict(sorted(sebepler.items(),
                                               key=lambda x: -x[1])),
            },
        })

    @app.route('/musteri')'''

IMZA = 'def api_crm_musteri_ozet('

print("═" * 70)
print(" M360 · MÜŞTERİ 360 (veri)")
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

# Finansal alan sizmasin.
_bas = icerik.find('def api_crm_musteri_ozet(')
_son = icerik.find("@app.route('/musteri')", _bas)
_kod, _ds = [], False
for _l in icerik[_bas:_son].split('\n'):
    _t = _l.strip()
    if _t.count('"""') == 1:
        _ds = not _ds
        continue
    if _ds or _t.startswith('#') or _t.startswith('"""'):
        continue
    _kod.append(_l)
for _y in ('bakiye', 'borc', 'alacak', 'risk_limiti'):
    if _y in '\n'.join(_kod):
        print(f" ✗ Uç nokta KODUNDA finansal alan var: {_y}")
        print(" DOSYAYA DOKUNULMADI.")
        sys.exit(1)

print("  ✓ uygulanacak          ürün tercihi + fiyat geçmişi + dönüşüm")
print("  ✓ finansal alan sızmıyor")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_m360_veri.py --uygula")
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
print(" GET /api/crm/musteri/<cari_id>/ozet")
print("═" * 70)

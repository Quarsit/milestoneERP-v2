#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — SATIŞ MÜŞTERİ EKRANI  ·  CRM-H (veri)
#
#  ── SORUN ──
#    Takipler sayfasindaki "Musteriler" dugmesi /cari'ye gidiyordu —
#    yani FINANS ekranina. Oradan bir cariye tiklayinca acilan
#    pencerede bakiye, hareket, tahsilat/odeme dugmeleri var.
#
#    Satis ekibi finans bolumune HIC girmemeli. Dugmeyi ben
#    birakmistim; CRM'i finanstan ayirirken (CRM-G) yetkileri
#    ayirdim ama YOLU ayirmadim.
#
#  ── ÇÖZÜM ──
#    /api/crm/musteri — CRM mercegiyle musteri listesi.
#
#    Donen alanlar KASITLI olarak sinirli: unvan, ulke, sorumlu,
#    kisi sayisi, son temas, bekleyen takip. BAKIYE, BORC, ALACAK,
#    RISK LIMITI DONMEZ. Satisci finansal veriyi gormemeli;
#    gormemesi gereken veriyi "nasilsa ekranda gostermeyiz" diyip
#    API'den dondurmek, tarayici konsolunu acan herkese sizdirmak
#    demektir.
#
#  ── SÜZGEÇLER ──
#    kapsam=bana   yalnizca sorumlusu oldugum musteriler
#    kapsam=tumu   gorebildiklerimin hepsi (varsayilan)
#    durum=geciken takibi gecikmis olanlar
#    durum=sessiz  uzun suredir temas kurulmamis olanlar
#
#    "Sessiz" musteri, satista en kolay kaybedilen musteridir;
#    kimse aramadigi icin sessizdir, sessiz oldugu icin de akla
#    gelmez. Listede gorunur olmasi bu dongusu kirar.
#
#  KULLANIM (proje klasöründe):
#      python yama_crm_h_musteri.py            # rapor
#      python yama_crm_h_musteri.py --uygula
#
#  ⚠ templates/musteri.html ve templates/takipler.html gerekli.
#  Şema değişikliği YOK.
# ══════════════════════════════════════════════════════════════════════
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
APP = Path('flask_app.py')
BASE = Path('templates/base.html')
SAYFA = Path('templates/musteri.html')

for _d in (APP, BASE):
    if not _d.exists():
        print(f"HATA: {_d} bulunamadı. Proje klasöründe çalıştırın.")
        sys.exit(1)
if not SAYFA.exists():
    print("✗ ÖN KOŞUL: templates/musteri.html yok.")
    print("  Bu dosya olmadan rota TemplateNotFound ile çöker.")
    sys.exit(1)
if 'CRM_YOL_DESENLERI' not in APP.read_text(encoding='utf-8', errors='replace'):
    print("✗ ÖN KOŞUL: önce yama_crm_g_ayir.py uygulanmalı.")
    sys.exit(1)

# ── A) /api/crm yolunu crm modülüne bağla ──────────────────────────
A_ESKI = """        (_re_modul.compile(r'^/api/takipler(/|$)'), 'crm'),"""
A_YENI = """        (_re_modul.compile(r'^/api/takipler(/|$)'), 'crm'),
        (_re_modul.compile(r'^/api/crm(/|$)'), 'crm'),"""

# ── B) Uç nokta + sayfa ────────────────────────────────────────────
B_ESKI = """    @app.route('/takipler')"""

B_YENI = '''    @app.route('/api/crm/musteri', methods=['GET'])
    def api_crm_musteri():
        """CRM mercegiyle musteri listesi.

        FINANSAL VERI DONMEZ — bakiye, borc, alacak, risk limiti yok.
        "Nasilsa ekranda gostermeyiz" deyip API'den dondurmek,
        tarayici konsolunu acan herkese sizdirmak olurdu.
        """
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('crm', 'okuma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403

        kapsam = (request.args.get('kapsam') or 'tumu').lower()
        durum = (request.args.get('durum') or '').lower()
        ara = (request.args.get('ara') or '').strip().lower()
        bugun = date.today()
        try:
            sessiz_gun = max(7, min(365, int(request.args.get('sessiz_gun', 60))))
        except (TypeError, ValueError):
            sessiz_gun = 60

        # Kuresel suzgec zaten gorunmeyenleri eliyor; kapsam=bana
        # bunun UZERINE "yalnizca benim sorumlulugumdakiler" ekler.
        q = Cari.query
        if kapsam == 'bana':
            q = q.filter(Cari.sorumlu == session.get('kullanici'))
        cariler = q.order_by(Cari.unvan).all()
        if not cariler:
            return jsonify({'ok': True, 'data': [], 'sessiz_gun': sessiz_gun})

        idler = [c.id for c in cariler]

        # Kisi sayilari — TEK sorgu. Musteri basina sorgu atmak
        # 200 musteride sayfayi kilitlerdi.
        kisi_say = {}
        for k in CariKisi.query.filter(CariKisi.cari_id.in_(idler)).all():
            kisi_say[k.cari_id] = kisi_say.get(k.cari_id, 0) + 1

        son_temas, bekleyen, en_yakin = {}, {}, {}
        for a in CariAktivite.query.filter(
                CariAktivite.cari_id.in_(idler)).all():
            if a.tarih and (a.cari_id not in son_temas
                            or a.tarih > son_temas[a.cari_id][0]):
                son_temas[a.cari_id] = (a.tarih, a.ozet)
            if a.sonraki_tarih and not a.tamamlandi:
                bekleyen[a.cari_id] = bekleyen.get(a.cari_id, 0) + 1
                if (a.cari_id not in en_yakin
                        or a.sonraki_tarih < en_yakin[a.cari_id]):
                    en_yakin[a.cari_id] = a.sonraki_tarih

        cikti = []
        for c in cariler:
            if ara and ara not in (c.unvan or '').lower():
                continue
            st = son_temas.get(c.id)
            yk = en_yakin.get(c.id)
            gecen = (bugun - st[0]).days if st else None
            satir = {
                'id': c.id, 'unvan': c.unvan, 'ulke': c.ulke,
                'cari_tip': c.cari_tip, 'sorumlu': c.sorumlu,
                'gorunurluk': c.gorunurluk or 'kapali',
                'kisi_sayisi': kisi_say.get(c.id, 0),
                'son_temas': st[0].isoformat() if st else None,
                'son_temas_ozet': st[1] if st else None,
                'temassiz_gun': gecen,
                'bekleyen_takip': bekleyen.get(c.id, 0),
                'en_yakin_takip': yk.isoformat() if yk else None,
                'gecikmis': bool(yk and yk < bugun),
            }
            # "Sessiz" musteri satista en kolay kaybedilendir: kimse
            # aramadigi icin sessizdir, sessiz oldugu icin akla
            # gelmez. Hic temas kurulmamis olanlar da sessiz sayilir.
            satir['sessiz'] = (gecen is None) or (gecen >= sessiz_gun)
            cikti.append(satir)

        if durum == 'geciken':
            cikti = [x for x in cikti if x['gecikmis']]
        elif durum == 'sessiz':
            cikti = [x for x in cikti if x['sessiz']]

        return jsonify({'ok': True, 'sessiz_gun': sessiz_gun,
                        'bugun': bugun.isoformat(), 'data': cikti})

    @app.route('/musteri')
    def musteri_sayfa():
        """Satis mercegiyle musteri ekrani — finansal veri yok."""
        if _auth_required(): return _auth_required()
        if not _yetki_var_mi('crm', 'okuma'):
            return redirect(url_for('dashboard'))
        return render_template('musteri.html')

    @app.route('/takipler')'''

# ── C) Menü ────────────────────────────────────────────────────────
C_ESKI = """('/satislar','Satışlar','satislar'), ('/takipler','Takipler','crm')] %}"""
C_YENI = """('/satislar','Satışlar','satislar'), ('/musteri','Müşteriler','crm'), ('/takipler','Takipler','crm')] %}"""

D_ESKI = """or yol.startswith('/sevkiyat') or yol.startswith('/takipler') %}aktif{% endif %}\">"""
D_YENI = """or yol.startswith('/sevkiyat') or yol.startswith('/takipler') or yol.startswith('/musteri') %}aktif{% endif %}\">"""

E_ESKI = """    {% if yol.startswith('/takipler') or yol.startswith('/siparis')"""
E_YENI = """    {% if yol.startswith('/musteri') or yol.startswith('/takipler') or yol.startswith('/siparis')"""

BLOKLAR = [
    (APP,  "/api/crm yol eşlemesi",   A_ESKI, A_YENI, "^/api/crm(/|$)"),
    (APP,  "müşteri uç noktası + sayfa", B_ESKI, B_YENI, 'def api_crm_musteri('),
    (BASE, "menü · Satış listesi",    C_ESKI, C_YENI, "('/musteri','Müşteriler','crm')"),
    (BASE, "menü · sol ray vurgusu",  D_ESKI, D_YENI, "or yol.startswith('/musteri') %}aktif"),
    (BASE, "menü · alt sekme koşulu", E_ESKI, E_YENI, "{% if yol.startswith('/musteri')"),
]

print("═" * 70)
print(" CRM-H · SATIŞ MÜŞTERİ EKRANI")
print("═" * 70)
print()

icerik, crlf = {}, {}
for yol in (APP, BASE):
    _t = yol.read_bytes().decode('utf-8')
    icerik[yol] = _t
    crlf[yol] = '\r\n' in _t


def uyarla(t, yol):
    return t.replace('\n', '\r\n') if crlf[yol] else t


plan, atlanan, sorunlu = [], [], []
for yol, aciklama, eski, yeni, imza in BLOKLAR:
    metin = icerik[yol]
    if uyarla(imza, yol) in metin or imza in metin:
        atlanan.append(aciklama)
        continue
    e = uyarla(eski, yol)
    adet = metin.count(e)
    if adet != 1:
        sorunlu.append((aciklama, adet))
        continue
    icerik[yol] = metin.replace(e, uyarla(yeni, yol), 1)
    plan.append(aciklama)

for a in atlanan:
    print(f"  ↷ atlandı (zaten var)  {a}")
for a in plan:
    print(f"  ✓ uygulanacak          {a}")
for a, n in sorunlu:
    print(f"  ✗ KALIP BULUNAMADI     {a}  (eşleşme: {n})")

print()
if sorunlu:
    print(f" ✗ {len(sorunlu)} blok yerleştirilemedi — HİÇBİR DOSYAYA DOKUNULMADI.")
    sys.exit(1)
if not plan:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

try:
    compile(icerik[APP], 'flask_app.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" HİÇBİR DOSYAYA DOKUNULMADI.")
    sys.exit(1)

# Finansal alan sizmasin — uc nokta govdesini denetle.
_bas = icerik[APP].find('def api_crm_musteri(')
_son = icerik[APP].find('def musteri_sayfa(', _bas)
_govde = icerik[APP][_bas:_son]
# YORUM ve DOCSTRING AYIKLANIR: aciklama metninde gecen "bakiye"
# kelimesi kod degildir. (Ilk surumde bu ayrim yoktu ve yama kendi
# aciklamasina takildi — NK2'de de ayni hatayi yapmistim.)
_kod = []
_ds = False
for _l in _govde.split('\n'):
    _t = _l.strip()
    if _t.startswith('"""') or _t.endswith('"""'):
        _ds = not _ds if _t.count('"""') == 1 else _ds
        continue
    if _ds or _t.startswith('#'):
        continue
    _kod.append(_l)
_kod = '\n'.join(_kod)
for _yasak in ('bakiye', 'borc', 'alacak', 'risk_limiti'):
    if _yasak in _kod:
        print(f" ✗ Uç nokta KODUNDA finansal alan var: {_yasak}")
        print(" HİÇBİR DOSYAYA DOKUNULMADI.")
        sys.exit(1)
print(" ✓ finansal alan sızmıyor (bakiye/borç/alacak/risk yok)")
print(" ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_crm_h_musteri.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
for yol in (APP, BASE):
    yedek = yol.with_name(f'{yol.name}.yedek-{damga}')
    shutil.copy2(yol, yedek)
    yol.write_bytes(icerik[yol].encode('utf-8'))
    print(f" ✓ {yol.name}")

print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print(" Satış menüsünde 'Müşteriler' — finans bölümüne gitmeden.")
print("═" * 70)

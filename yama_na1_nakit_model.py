#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — NAKİT AKIŞI  ·  NA1  (1/3: model + sabit gider API)
#
#  ── NEDEN ──
#    Sistem alacak/borç verisini zaten tutuyor ama ZAMAN EKSENİNDE
#    göstermiyor: "üç hafta sonra kasamda para kalıyor mu?" sorusunun
#    cevabı hiçbir ekranda yok.
#
#    Veri kaynakları HAZIR:
#      CariHareket  vade_tarihi · borc/alacak · kapatildi
#      Cek          vade_tarihi · yon · durum
#      Fatura       vade_tarihi · yon · durum
#      Kasa         mevcut bakiye (başlangıç noktası)
#
#    EKSİK OLAN TEK ŞEY: sabit giderler. Kira, maaş, elektrik
#    sistemde hiç takip edilmiyor — onlar olmadan projeksiyon
#    gerçekçi olmaz, hep iyimser çıkar.
#
#  ── İKİ YENİ TABLO ──
#
#  1. SabitGider — ŞABLON
#     "Kira · 45.000 TL · her ayın 5'i" gibi bir kayıt; projeksiyona
#     otomatik yayılır. Tutar TAHMİNİDİR (elektrik her ay değişir);
#     gerçekleşince NakitPlan üzerinden güncellenir.
#
#  2. NakitPlan — TEKİL KALEM
#     Projeksiyonda görünen her satır. Üç kaynaktan doğar:
#       • sabit gider şablonundan üretilen
#       • elle eklenen (vadesi olmayan cari hareketine vade atama)
#       • cari/çek/faturadan türeyen (kayıt açılmaz, anlık okunur)
#
#     `gerceklesti` alanı ELLE işaretlenir. Kasa hareketiyle otomatik
#     eşleştirme denenmedi: yanlış eşleşme, olmayan bir tahsilatı
#     "olmuş" göstermekten daha kötü sonuç verir.
#
#  ── VADESİZ HAREKETE VADE ATAMA ──
#    Vadesi boş bir cari hareketi için NakitPlan kaydı açılır; ASIL
#    KAYDA DOKUNULMAZ. Böylece muhasebe kaydı ile nakit tahmini
#    birbirine karışmaz — biri gerçek, öteki öngörü.
#
#  KULLANIM (proje klasöründe):
#      python yama_na1_nakit_model.py            # rapor
#      python yama_na1_nakit_model.py --uygula   # uygula
#
#  ⚠ ŞEMA DEĞİŞİKLİĞİ VAR — sonra:
#      venv/bin/python goc.py olustur "nakit akisi tablolari"
#      venv/bin/python goc.py uygula
#
#  SONRA: yama_na2 (projeksiyon ekranı)
# ══════════════════════════════════════════════════════════════════════
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv

MODELS = Path('models.py')
APP = Path('flask_app.py')

for d in (MODELS, APP):
    if not d.exists():
        print(f"HATA: {d} bulunamadı. Proje klasöründe çalıştırın.")
        sys.exit(1)


def dogrula(kaynak, ad):
    try:
        compile(kaynak, ad, 'exec')
        return None
    except SyntaxError as exc:
        return f"satır {exc.lineno}: {exc.msg}"


# ── A) Modeller ────────────────────────────────────────────────────
A_ESKI = """class AuditLog(db.Model):"""

A_YENI = '''# ── NAKİT AKIŞI (NA1) ─────────────────────────────────────────────────
class SabitGider(db.Model):
    """Tekrarlayan gider SABLONU — kira, maas, elektrik…

    Projeksiyona otomatik yayilir. `tutar` TAHMINIDIR: elektrik her ay
    degisir, kira yilda bir artar. Gerceklesince NakitPlan uzerinden
    guncellenir, sablon oldugu gibi kalir.
    """
    __tablename__ = 'sabit_gider'
    id          = db.Column(db.String(20), primary_key=True)
    ad          = db.Column(db.String(100), nullable=False)
    kategori    = db.Column(db.String(50))      # Personel/Kira/Enerji/Vergi/Diger
    tutar       = db.Column(Para, nullable=False)
    doviz       = db.Column(db.String(5), default='TRY')
    # Periyot: aylik | haftalik | yillik
    periyot     = db.Column(db.String(10), default='aylik')
    ayin_gunu   = db.Column(db.Integer, default=1)    # aylik/yillik icin (1-31)
    haftanin_gunu = db.Column(db.Integer)             # haftalik icin (0=Pzt)
    ay          = db.Column(db.Integer)               # yillik icin (1-12)
    baslangic   = db.Column(db.Date, default=date.today)
    bitis       = db.Column(db.Date, nullable=True)   # bos = suresiz
    aktif       = db.Column(db.Boolean, default=True)
    aciklama    = db.Column(db.Text)
    olusturma   = db.Column(db.DateTime, default=datetime.now)


class NakitPlan(db.Model):
    """Projeksiyondaki TEKIL kalem.

    Uc kaynaktan dogar:
      'sabit'  — SabitGider sablonundan uretilen
      'elle'   — kullanicinin ekledigi (vadesiz harekete vade atama)
      'cari'/'cek'/'fatura' — mevcut kayitlardan turetilen

    ONEMLI: cari/cek/fatura kalemleri icin BU TABLOYA KAYIT ACILMAZ;
    projeksiyon onlari anlik okur. Tablo yalnizca 'sabit' ve 'elle'
    kalemleri tutar. Aksi halde ayni borc iki kez sayilirdi.

    `gerceklesti` ELLE isaretlenir. Kasa hareketiyle otomatik
    eslestirme denenmedi: yanlis eslestirme, olmayan bir tahsilati
    "olmus" gostermekten daha kotu sonuc verir.
    """
    __tablename__ = 'nakit_plan'
    id          = db.Column(db.String(20), primary_key=True)
    tarih       = db.Column(db.Date, nullable=False, index=True)
    yon         = db.Column(db.String(6), nullable=False)   # giris | cikis
    tutar       = db.Column(Para, nullable=False)
    doviz       = db.Column(db.String(5), default='TRY')
    aciklama    = db.Column(db.String(200))
    kaynak      = db.Column(db.String(20), default='elle')  # sabit | elle
    kaynak_id   = db.Column(db.String(20))    # SabitGider.id ya da CariHareket.id
    cari_id     = db.Column(db.String(20))
    gerceklesti = db.Column(db.Boolean, default=False)
    gerceklesme_tarihi = db.Column(db.Date)
    kullanici   = db.Column(db.String(50))
    olusturma   = db.Column(db.DateTime, default=datetime.now)


class AuditLog(db.Model):'''

# ── B) API ─────────────────────────────────────────────────────────
B_ESKI = """    @app.route('/api/maliyet', methods=['GET'])"""

B_YENI = '''    # ══════════════════════════════════════════════════════════
    #  NAKİT AKIŞI — SABİT GİDERLER  (NA1)
    # ══════════════════════════════════════════════════════════
    GIDER_KATEGORI = ('Personel', 'Kira', 'Enerji', 'Vergi/SGK',
                      'Nakliye', 'Finansman', 'Diğer')
    GIDER_PERIYOT = ('aylik', 'haftalik', 'yillik')

    def _sabit_gider_dict(g):
        return {
            'id': g.id, 'ad': g.ad, 'kategori': g.kategori,
            'tutar': g.tutar, 'doviz': g.doviz,
            'periyot': g.periyot, 'ayin_gunu': g.ayin_gunu,
            'haftanin_gunu': g.haftanin_gunu, 'ay': g.ay,
            'baslangic': g.baslangic.isoformat() if g.baslangic else None,
            'bitis': g.bitis.isoformat() if g.bitis else None,
            'aktif': g.aktif, 'aciklama': g.aciklama,
        }

    @app.route('/api/sabit_gider', methods=['GET'])
    def api_sabit_gider_liste():
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        q = SabitGider.query
        if request.args.get('aktif') == '1':
            q = q.filter_by(aktif=True)
        gl = q.order_by(SabitGider.kategori, SabitGider.ad).all()
        return jsonify({'ok': True, 'data': [_sabit_gider_dict(g) for g in gl],
                        'kategoriler': list(GIDER_KATEGORI)})

    @app.route('/api/sabit_gider', methods=['POST'])
    def api_sabit_gider_ekle():
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('kasa', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        d = request.json or {}
        ad = (d.get('ad') or '').strip()
        if not ad:
            return jsonify({'ok': False, 'mesaj': 'Gider adi zorunlu'}), 400
        try:
            tutar = float(d.get('tutar') or 0)
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'mesaj': 'Tutar sayisal olmali'}), 400
        if tutar <= 0:
            return jsonify({'ok': False, 'mesaj': 'Tutar sifirdan buyuk olmali'}), 400

        periyot = (d.get('periyot') or 'aylik').lower()
        if periyot not in GIDER_PERIYOT:
            return jsonify({'ok': False, 'mesaj':
                            f'Periyot: {", ".join(GIDER_PERIYOT)}'}), 400

        # Gun dogrulama — periyoda gore FARKLI alan zorunlu
        _gun = d.get('ayin_gunu')
        _hg = d.get('haftanin_gunu')
        if periyot in ('aylik', 'yillik'):
            try:
                _gun = int(_gun or 1)
            except (TypeError, ValueError):
                return jsonify({'ok': False, 'mesaj': 'Ayin gunu sayisal olmali'}), 400
            if not (1 <= _gun <= 31):
                return jsonify({'ok': False, 'mesaj': 'Ayin gunu 1-31 arasinda olmali'}), 400
        elif periyot == 'haftalik':
            try:
                _hg = int(_hg if _hg is not None else 0)
            except (TypeError, ValueError):
                return jsonify({'ok': False, 'mesaj': 'Haftanin gunu sayisal olmali'}), 400
            if not (0 <= _hg <= 6):
                return jsonify({'ok': False, 'mesaj':
                                'Haftanin gunu 0-6 arasinda olmali (0=Pazartesi)'}), 400

        g = SabitGider(
            id=_yeni_id('SG'), ad=ad,
            kategori=(d.get('kategori') or 'Diğer').strip(),
            tutar=q3(tutar), doviz=(d.get('doviz') or 'TRY').upper(),
            periyot=periyot,
            ayin_gunu=_gun if periyot in ('aylik', 'yillik') else None,
            haftanin_gunu=_hg if periyot == 'haftalik' else None,
            ay=int(d['ay']) if (periyot == 'yillik' and d.get('ay')) else None,
            baslangic=_parse_date(d.get('baslangic')) or date.today(),
            bitis=_parse_date(d.get('bitis')),
            aciklama=(d.get('aciklama') or '').strip() or None,
            aktif=bool(d.get('aktif', True)))
        db.session.add(g)
        _log_audit('EKLE', 'sabit_gider', g.id, yeni={'ad': ad, 'tutar': tutar})
        ok, hata = _safe_commit(f'Sabit gider: {ad}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True, 'id': g.id, 'gider': _sabit_gider_dict(g),
                        'mesaj': f'{ad} eklendi'})

    @app.route('/api/sabit_gider/<gider_id>', methods=['PUT'])
    def api_sabit_gider_guncelle(gider_id):
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('kasa', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        g = SabitGider.query.get(gider_id)
        if not g:
            return jsonify({'ok': False, 'mesaj': 'Gider bulunamadi'}), 404
        d = request.json or {}
        for alan in ('ad', 'kategori', 'aciklama'):
            if alan in d:
                setattr(g, alan, (d.get(alan) or '').strip() or None)
        if 'tutar' in d:
            try:
                _t = float(d['tutar'])
            except (TypeError, ValueError):
                return jsonify({'ok': False, 'mesaj': 'Tutar sayisal olmali'}), 400
            if _t <= 0:
                return jsonify({'ok': False, 'mesaj': 'Tutar sifirdan buyuk olmali'}), 400
            g.tutar = q3(_t)
        if 'doviz' in d:
            g.doviz = (d['doviz'] or 'TRY').upper()
        if 'periyot' in d and d['periyot'] in GIDER_PERIYOT:
            g.periyot = d['periyot']
        for alan in ('ayin_gunu', 'haftanin_gunu', 'ay'):
            if alan in d:
                setattr(g, alan, int(d[alan]) if d[alan] not in (None, '') else None)
        for alan in ('baslangic', 'bitis'):
            if alan in d:
                setattr(g, alan, _parse_date(d[alan]))
        if 'aktif' in d:
            g.aktif = bool(d['aktif'])
        _log_audit('GUNCELLE', 'sabit_gider', g.id, yeni={'ad': g.ad, 'tutar': g.tutar})
        ok, hata = _safe_commit(f'Sabit gider guncelleme: {gider_id}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True, 'gider': _sabit_gider_dict(g),
                        'mesaj': 'Guncellendi'})

    @app.route('/api/sabit_gider/<gider_id>', methods=['DELETE'])
    def api_sabit_gider_sil(gider_id):
        """Sablonu siler. Uretilmis NakitPlan kalemleri KALIR.

        Gecmis aylarin projeksiyonu bozulmasin diye: gider artik
        yok ama gecen ay odendiyse o kayit durmali.
        """
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('kasa', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        g = SabitGider.query.get(gider_id)
        if not g:
            return jsonify({'ok': False, 'mesaj': 'Gider bulunamadi'}), 404
        # Gerceklesmemis plan kalemleri temizlenir; gerceklesenler KALIR
        silinen = NakitPlan.query.filter_by(
            kaynak='sabit', kaynak_id=gider_id, gerceklesti=False).delete()
        _ad = g.ad
        db.session.delete(g)
        _log_audit('SIL', 'sabit_gider', gider_id, eski={'ad': _ad})
        ok, hata = _safe_commit(f'Sabit gider silme: {gider_id}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True, 'silinen_plan': silinen,
                        'mesaj': f'{_ad} silindi'
                                 + (f' · {silinen} planlanan kalem kaldirildi'
                                    if silinen else '')})

    @app.route('/api/maliyet', methods=['GET'])'''

# ── C) IMPORT — modeller ice aktarilmazsa NameError ──────────────
# Ilk surumde atlandi: API yazildi ama SabitGider import edilmedigi
# icin ilk POST'ta "NameError: name 'SabitGider' is not defined" verdi.
C_ESKI = "from models import Cek, CekHareket"
C_YENI = ("from models import Cek, CekHareket\n"
          "from models import SabitGider, NakitPlan   # NA1: nakit akisi")

BLOKLAR = [
    (MODELS, 'class SabitGider(db.Model)', A_ESKI, A_YENI, 'model: SabitGider + NakitPlan'),
    (APP, 'from models import SabitGider, NakitPlan', C_ESKI, C_YENI, 'import: yeni modeller'),
    (APP, 'def api_sabit_gider_liste(', B_ESKI, B_YENI, 'API: sabit gider CRUD'),
]

print("═" * 70)
print(" NA1 · NAKİT AKIŞI  (1/3: model + sabit gider API)")
print("═" * 70)
print()

icerik, crlf = {}, {}
for yol in (MODELS, APP):
    ham = yol.read_bytes().decode('utf-8')
    icerik[yol] = ham
    crlf[yol] = '\r\n' in ham


def uyarla(t, yol):
    return t.replace('\n', '\r\n') if crlf[yol] else t


plan, atlanan, sorunlu = [], [], []
for yol, imza, eski, yeni, aciklama in BLOKLAR:
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
    print(" ✓ Tüm bloklar zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

for yol in (MODELS, APP):
    hata = dogrula(icerik[yol], yol.name)
    if hata:
        print(f" ✗ {yol.name} SÖZDİZİMİ HATASI → {hata}")
        print(" Hiçbir dosyaya DOKUNULMADI.")
        sys.exit(1)
print(" ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_na1_nakit_model.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
for yol in (MODELS, APP):
    yedek = yol.with_name(f'{yol.name}.yedek-{damga}')
    shutil.copy2(yol, yedek)
    yol.write_bytes(icerik[yol].encode('utf-8'))
    print(f" ✓ {yol.name}")

print()
print("═" * 70)
print(" ✓ TAMAMLANDI  (1/3)")
print()
print(" ⚠ ŞEMA DEĞİŞTİ:")
print("   venv/bin/python goc.py olustur \"nakit akisi tablolari\"")
print("   venv/bin/python goc.py uygula")
print()
print(" SIRADAKİ: yama_na2 — projeksiyon hesabı ve ekran")
print("═" * 70)

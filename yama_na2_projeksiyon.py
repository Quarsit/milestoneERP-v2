#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — NAKİT AKIŞI  ·  NA2  (2/3: projeksiyon motoru)
#
#  ── ÖN KOŞUL ──
#      yama_na1_nakit_model.py uygulanmış olmalı (SabitGider + NakitPlan)
#
#  ── NE YAPAR ──
#    Dört kaynağı ZAMAN EKSENİNE dizer ve "hangi tarihte kasamda ne
#    kadar para olur" sorusunu cevaplar:
#
#      1. Kasa bakiyeleri  → başlangıç noktası
#      2. CariHareket      → vadesi gelmemiş alacak/borç
#      3. Cek              → portföydeki + verilen çekler
#      4. SabitGider       → şablondan yayılan kira/maaş/vergi
#      5. NakitPlan        → elle eklenen kalemler
#
#  ── ÜÇ DÖVİZ AYRI ──
#    TRY/USD/EUR tek çizgide toplanmaz. İhracatçıda döviz girişi ve TL
#    gideri aynı anda olur; toplamak kur riskini GİZLER. Her döviz
#    kendi satırında izlenir.
#
#  ── ÇİFT SAYIM KORUMASI (kodda doğrulandı) ──
#    Bu kaynaklardan gelen cari hareketler ATLANIR:
#
#      'cek'        → çek kendi tablosundan sayılıyor
#      'tahsilat'   → flask_app.py:10399 — bu hareket ÇEK ALINIRKEN
#                     açılıyor, yani çekin ta kendisi. Sayılsaydı aynı
#                     tahsilat hem Cek hem CariHareket'ten iki kez
#                     görünürdü.
#      'virman'     → parayı zaten kasaya taşımış; kasa.bakiye içinde
#      'mahsup'     → hesap denkleştirme, nakit hareketi yok
#      'avans_devir'→ hesaplar arası avans aktarımı, nakit hareketi yok
#
#    Fatura tablosu HİÇ okunmuyor: fatura kesilince cari hareket zaten
#    açılıyor. İkisini de okumak her borcu iki kez sayardı.
#
#  ── KAPANMIŞ KAYITLAR ──
#    kapatildi=True cari hareketler ve tahsil edilmiş çekler
#    projeksiyona GİRMEZ — onlar kasaya yansımıştır.
#
#  KULLANIM (proje klasöründe):
#      python yama_na2_projeksiyon.py            # rapor
#      python yama_na2_projeksiyon.py --uygula   # uygula
#
#  SONRA: yama_na3_nakit_sayfa.py (ekran)
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

if 'SabitGider' not in APP.read_text(encoding='utf-8', errors='replace'):
    print("✗ ÖN KOŞUL: önce yama_na1_nakit_model.py uygulanmalı.")
    sys.exit(1)


def dogrula(kaynak):
    try:
        compile(kaynak, 'flask_app.py', 'exec')
        return None
    except SyntaxError as exc:
        return f"satır {exc.lineno}: {exc.msg}"


A_ESKI = """    @app.route('/api/sabit_gider', methods=['GET'])"""

A_YENI = '''    # ══════════════════════════════════════════════════════════
    #  NAKİT AKIŞI — PROJEKSİYON  (NA2)
    # ══════════════════════════════════════════════════════════

    # Cari hareketin nakit projeksiyonuna GIRMEYECEGI kaynaklar.
    # Gerekce icin dosya basindaki acikliamaya bakin — ozetle: ya
    # parasi zaten kasaya girmis, ya baska bir tablodan sayiliyor,
    # ya da hic nakit hareketi yok.
    NAKIT_HARIC_KAYNAK = ('cek', 'tahsilat', 'virman', 'mahsup', 'avans_devir')

    # Cek durumlari — /api/cek/ozet ile AYNI liste olmali.
    NAKIT_ACIK_CEK_ALINAN = ('Portfoyde', 'TahsildeBanka', 'Teminatta')
    NAKIT_ACIK_CEK_VERILEN = ('Verildi',)

    def _gider_tarihleri(g, bas, son):
        """Sabit gider sablonunu tarih listesine yayar.

        Ayin 31'i secilmis ama ay 30 cekiyorsa AYIN SON GUNU kullanilir
        — 31 Subat diye bir gun yok, gider kaybolmamali.
        """
        import calendar
        sonuc = []
        if not g.aktif:
            return sonuc
        _bas = max(bas, g.baslangic or bas)
        _son = min(son, g.bitis) if g.bitis else son
        if _bas > _son:
            return sonuc

        if g.periyot == 'haftalik':
            hg = g.haftanin_gunu if g.haftanin_gunu is not None else 0
            t = _bas
            while t.weekday() != hg:
                t += timedelta(days=1)
                if t > _son:
                    return sonuc
            while t <= _son:
                sonuc.append(t)
                t += timedelta(days=7)
            return sonuc

        # aylik / yillik
        gun = g.ayin_gunu or 1
        y, a = _bas.year, _bas.month
        # Guvenlik siniri: 24 ay * 12 = kacak dongu olmaz
        for _ in range(400):
            if date(y, a, 1) > _son:
                break
            atla = (g.periyot == 'yillik' and g.ay and a != g.ay)
            if not atla:
                son_gun = calendar.monthrange(y, a)[1]
                t = date(y, a, min(gun, son_gun))
                if _bas <= t <= _son:
                    sonuc.append(t)
            a += 1
            if a > 12:
                a = 1
                y += 1
        return sonuc

    def _nakit_kalemleri(bas, son):
        """Tarih araligindaki TUM beklenen nakit hareketlerini toplar.

        Doner: [{'tarih','yon','tutar','doviz','kaynak','aciklama',
                 'kayit_id','vadesiz'}]
        """
        kalemler = []

        # ── 1) CARİ HAREKETLER ────────────────────────────────
        for h in CariHareket.query.filter(
                CariHareket.kapatildi.isnot(True)).all():
            if (h.kaynak or '') in NAKIT_HARIC_KAYNAK:
                continue
            borc = float(h.borc or 0)
            alacak = float(h.alacak or 0)
            if borc <= 0 and alacak <= 0:
                continue
            # borc   = musteri bize borclu       → GIRIS
            # alacak = biz tedarikciye borcluyuz → CIKIS
            yon = 'giris' if borc > 0 else 'cikis'
            tutar = borc if borc > 0 else alacak
            vade = h.vade_tarihi
            _ad = (h.cari_unvan or h.cari_id or '').strip()
            _tip = (h.islem_tip or '').strip()
            kalemler.append({
                'tarih': vade.isoformat() if vade else None,
                'yon': yon, 'tutar': q3(tutar),
                'doviz': (h.doviz or 'TRY').upper(),
                'kaynak': 'cari', 'kayit_id': h.id,
                'aciklama': f"{_ad} — {_tip}".strip(' —') or 'Cari hareket',
                'vadesiz': vade is None,
            })

        # ── 2) ÇEKLER ─────────────────────────────────────────
        for ck in Cek.query.filter(Cek.aktif.isnot(False)).all():
            if ck.yon == 'alinan':
                acik = ck.durum in NAKIT_ACIK_CEK_ALINAN
            else:
                acik = ck.durum in NAKIT_ACIK_CEK_VERILEN
            if not acik:
                continue
            _no = ck.cek_no or ck.id
            _ad = (ck.cari_unvan or '').strip()
            kalemler.append({
                'tarih': ck.vade_tarihi.isoformat() if ck.vade_tarihi else None,
                'yon': 'giris' if ck.yon == 'alinan' else 'cikis',
                'tutar': q3(float(ck.tutar or 0)),
                'doviz': (ck.doviz or 'TRY').upper(),
                'kaynak': 'cek', 'kayit_id': ck.id,
                'aciklama': f"Çek {_no} — {_ad}".strip(' —'),
                'vadesiz': ck.vade_tarihi is None,
            })

        # ── 3) SABİT GİDERLER (sablondan yayilir) ─────────────
        for g in SabitGider.query.filter_by(aktif=True).all():
            for t in _gider_tarihleri(g, bas, son):
                kalemler.append({
                    'tarih': t.isoformat(), 'yon': 'cikis',
                    'tutar': q3(float(g.tutar or 0)),
                    'doviz': (g.doviz or 'TRY').upper(),
                    'kaynak': 'sabit', 'kayit_id': g.id,
                    'aciklama': f"{g.ad} ({g.kategori or 'Diğer'})",
                    'vadesiz': False,
                })

        # ── 4) ELLE EKLENEN PLAN KALEMLERİ ────────────────────
        for p in NakitPlan.query.filter(
                NakitPlan.gerceklesti.isnot(True),
                NakitPlan.kaynak == 'elle').all():
            kalemler.append({
                'tarih': p.tarih.isoformat() if p.tarih else None,
                'yon': p.yon, 'tutar': q3(float(p.tutar or 0)),
                'doviz': (p.doviz or 'TRY').upper(),
                'kaynak': 'elle', 'kayit_id': p.id,
                'aciklama': p.aciklama or 'Elle eklenen',
                'vadesiz': p.tarih is None,
            })

        return kalemler

    @app.route('/api/nakit_akis', methods=['GET'])
    def api_nakit_akis():
        """Nakit akisi projeksiyonu.

        Parametreler:
            ay=6                kac ay ileriye (1-24, varsayilan 6)
            kirilim=ay|hafta|gun
            baslangic=YYYY-MM-DD

        UC DOVIZ AYRI doner — toplanmaz.
        """
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('kasa', 'okuma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403

        try:
            ay_sayisi = max(1, min(24, int(request.args.get('ay', 6))))
        except (TypeError, ValueError):
            ay_sayisi = 6
        kirilim = (request.args.get('kirilim') or 'ay').lower()
        if kirilim not in ('ay', 'hafta', 'gun'):
            kirilim = 'ay'
        bas = _parse_date(request.args.get('baslangic')) or date.today()
        son = bas + timedelta(days=ay_sayisi * 31)

        # ── Acilis kasa bakiyeleri (doviz bazinda) ──
        acilis = {}
        for k in Kasa.query.filter(Kasa.aktif.isnot(False)).all():
            d = (k.doviz or 'TRY').upper()
            acilis[d] = q3(float(acilis.get(d, 0)) + float(k.bakiye or 0))

        kalemler = _nakit_kalemleri(bas, son)

        # ── Vadesiz olanlari AYIR ──
        # Gizlemek projeksiyonu iyimser yapar; ayri gostermek dogru.
        vadesiz = [x for x in kalemler if x['vadesiz']]
        vadeli = [x for x in kalemler if not x['vadesiz']]

        gecmis = [x for x in vadeli if x['tarih'] < bas.isoformat()]
        gelecek = [x for x in vadeli
                   if bas.isoformat() <= x['tarih'] <= son.isoformat()]

        def donem_anahtari(tarih_str):
            t = date.fromisoformat(tarih_str)
            if kirilim == 'gun':
                return t.isoformat()
            if kirilim == 'hafta':
                return (t - timedelta(days=t.weekday())).isoformat()
            return f'{t.year}-{t.month:02d}'

        donemler = {}
        for x in gelecek:
            a = donem_anahtari(x['tarih'])
            g = donemler.setdefault(a, {})
            s = g.setdefault(x['doviz'], {'giris': 0.0, 'cikis': 0.0, 'kalemler': []})
            s['giris' if x['yon'] == 'giris' else 'cikis'] += float(x['tutar'])
            s['kalemler'].append(x)

        # ── Kumulatif bakiye (doviz bazinda) ──
        # KRITIK SUTUN: hangi donemde para BITIYOR onu gosterir.
        # Vadesi gecmis kalemler acilisa DAHIL EDILMEZ — henuz tahsil
        # edilmemisler; ayri grupta uyari olarak gosterilir.
        yurur = dict(acilis)
        sirali = []
        for a in sorted(donemler.keys()):
            satir = {'donem': a, 'dovizler': {}}
            for d in sorted(set(list(donemler[a].keys()) + list(yurur.keys()))):
                s = donemler[a].get(d, {'giris': 0.0, 'cikis': 0.0, 'kalemler': []})
                net = q3(s['giris'] - s['cikis'])
                yurur[d] = q3(float(yurur.get(d, 0)) + float(net))
                satir['dovizler'][d] = {
                    'giris': q3(s['giris']), 'cikis': q3(s['cikis']),
                    'net': net, 'kumulatif': yurur[d],
                    'kalem_sayisi': len(s['kalemler']),
                    'kalemler': sorted(s['kalemler'], key=lambda x: x['tarih'])[:40],
                }
            sirali.append(satir)

        def ozet(liste):
            o = {}
            for x in liste:
                d = o.setdefault(x['doviz'], {'giris': 0.0, 'cikis': 0.0, 'adet': 0})
                d['giris' if x['yon'] == 'giris' else 'cikis'] += float(x['tutar'])
                d['adet'] += 1
            return {k: {'giris': q3(v['giris']), 'cikis': q3(v['cikis']),
                        'adet': v['adet']} for k, v in o.items()}

        return jsonify({
            'ok': True,
            'baslangic': bas.isoformat(), 'bitis': son.isoformat(),
            'kirilim': kirilim, 'ay': ay_sayisi,
            'acilis': acilis,
            'donemler': sirali,
            'vadesi_gecmis': {'ozet': ozet(gecmis),
                              'kalemler': sorted(gecmis, key=lambda x: x['tarih'])[:100]},
            'vadesiz': {'ozet': ozet(vadesiz), 'kalemler': vadesiz[:100]},
        })

    @app.route('/api/nakit_plan', methods=['GET'])
    def api_nakit_plan_liste():
        """Elle eklenmis plan kalemleri."""
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('kasa', 'okuma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        q = NakitPlan.query.filter_by(kaynak='elle')
        if request.args.get('bekleyen') == '1':
            q = q.filter(NakitPlan.gerceklesti.isnot(True))
        pl = q.order_by(NakitPlan.tarih).all()
        return jsonify({'ok': True, 'data': [{
            'id': p.id,
            'tarih': p.tarih.isoformat() if p.tarih else None,
            'yon': p.yon, 'tutar': p.tutar, 'doviz': p.doviz,
            'aciklama': p.aciklama, 'cari_id': p.cari_id,
            'gerceklesti': bool(p.gerceklesti),
            'gerceklesme_tarihi': (p.gerceklesme_tarihi.isoformat()
                                   if p.gerceklesme_tarihi else None),
        } for p in pl]})

    @app.route('/api/nakit_plan', methods=['POST'])
    def api_nakit_plan_ekle():
        """Elle nakit kalemi ekler.

        Asil kullanim: VADESIZ bir cari hareketine tahmini vade atamak.
        Asil kayda DOKUNULMAZ — muhasebe kaydi gercek, nakit tahmini
        ongorudur; ikisi karismamali.
        """
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('kasa', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        d = request.json or {}
        t = _parse_date(d.get('tarih'))
        if not t:
            return jsonify({'ok': False, 'mesaj': 'Tarih zorunlu (YYYY-AA-GG)'}), 400
        yon = (d.get('yon') or '').lower()
        if yon not in ('giris', 'cikis'):
            return jsonify({'ok': False,
                            'mesaj': "Yon 'giris' ya da 'cikis' olmali"}), 400
        try:
            tutar = float(d.get('tutar') or 0)
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'mesaj': 'Tutar sayisal olmali'}), 400
        if tutar <= 0:
            return jsonify({'ok': False, 'mesaj': 'Tutar sifirdan buyuk olmali'}), 400

        p = NakitPlan(
            id=_yeni_id('NP'), tarih=t, yon=yon, tutar=q3(tutar),
            doviz=(d.get('doviz') or 'TRY').upper(),
            aciklama=(d.get('aciklama') or '').strip() or None,
            kaynak='elle', kaynak_id=(d.get('kaynak_id') or '').strip() or None,
            cari_id=(d.get('cari_id') or '').strip() or None,
            kullanici=session.get('kullanici'))
        db.session.add(p)
        ok, hata = _safe_commit('Nakit plan ekleme')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True, 'id': p.id, 'mesaj': 'Nakit kalemi eklendi'})

    @app.route('/api/nakit_plan/<plan_id>/gerceklesti', methods=['POST'])
    def api_nakit_plan_gerceklesti(plan_id):
        """Plan kalemini GERCEKLESTI olarak isaretler.

        ELLE isaretleme — kasa hareketiyle otomatik eslestirme
        denenmedi: yanlis eslestirme, olmayan bir tahsilati "olmus"
        gostermekten daha kotu sonuc verir.
        """
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('kasa', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        p = NakitPlan.query.get(plan_id)
        if not p:
            return jsonify({'ok': False, 'mesaj': 'Kalem bulunamadi'}), 404
        d = request.json or {}
        p.gerceklesti = bool(d.get('gerceklesti', True))
        if p.gerceklesti:
            p.gerceklesme_tarihi = _parse_date(d.get('tarih')) or date.today()
        else:
            p.gerceklesme_tarihi = None
        ok, hata = _safe_commit(f'Nakit plan gerceklesme: {plan_id}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True, 'gerceklesti': p.gerceklesti,
                        'mesaj': 'İşaretlendi' if p.gerceklesti else 'Geri alındı'})

    @app.route('/api/nakit_plan/<plan_id>', methods=['DELETE'])
    def api_nakit_plan_sil(plan_id):
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('kasa', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        p = NakitPlan.query.get(plan_id)
        if not p:
            return jsonify({'ok': False, 'mesaj': 'Kalem bulunamadi'}), 404
        db.session.delete(p)
        ok, hata = _safe_commit(f'Nakit plan silme: {plan_id}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True, 'mesaj': 'Silindi'})

    @app.route('/api/sabit_gider', methods=['GET'])'''

print("═" * 70)
print(" NA2 · NAKİT AKIŞI  (2/3: projeksiyon motoru)")
print("═" * 70)
print()

ham = APP.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


if 'def api_nakit_akis(' in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

e = uyarla(A_ESKI)
adet = ham.count(e)
if adet != 1:
    print(f" ✗ Kalıp {adet} kez bulundu (1 bekleniyordu). DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print("  ✓ uygulanacak          projeksiyon motoru + 5 uç nokta")
print()
print("     GET  /api/nakit_akis?ay=6&kirilim=ay|hafta|gun")
print("     GET  /api/nakit_plan")
print("     POST /api/nakit_plan                    (elle kalem)")
print("     POST /api/nakit_plan/<id>/gerceklesti   (elle işaretleme)")
print("     DEL  /api/nakit_plan/<id>")
print()

icerik = ham.replace(e, uyarla(A_YENI), 1)

hata = dogrula(icerik)
if hata:
    print(f" ✗ SÖZDİZİMİ HATASI → {hata}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)
print(" ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_na2_projeksiyon.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = APP.with_name(f'flask_app.py.yedek-{damga}')
shutil.copy2(APP, yedek)
APP.write_bytes(icerik.encode('utf-8'))
print(f" ✓ flask_app.py  (yedek: {yedek.name})")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI  (2/3)")
print()
print(" SIRADAKİ: yama_na3_nakit_sayfa.py — ekran")
print("═" * 70)

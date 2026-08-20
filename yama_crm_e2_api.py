#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — CRM UÇ NOKTALARI  ·  CRM-E2
#
#  ── ÖN KOŞUL ──
#      yama_crm_e_aktivite.py --uygula  +  goc.py uygula
#
#  ── EKLENENLER ──
#    Aktivite
#      GET    /api/cari/<id>/aktivite        temas gecmisi
#      POST   /api/cari/<id>/aktivite        yeni temas
#      PUT    /api/aktivite/<id>             duzenle
#      POST   /api/aktivite/<id>/tamamla     takibi kapat / geri al
#      DELETE /api/aktivite/<id>
#      GET    /api/takipler                  VADESI GELEN/GECEN takipler
#
#    Kisiler (CRM-B'de tablo acilmisti, ucu yoktu)
#      GET/POST /api/cari/<id>/kisi
#      PUT/DELETE /api/kisi/<id>
#
#    Erisim istisnalari (kapali musteriye ek kullanici)
#      GET/POST /api/cari/<id>/erisim
#      DELETE   /api/erisim/<id>
#
#  ── GÖRÜNÜRLÜK ──
#    CariAktivite, CariKisi ve CariErisim kuresel suzgece EKLENMEDI:
#    o suzgec `cari_id` sutunu olan modelleri suzuyor ve bu tablolar
#    da cari_id tasiyor — ama suzgec listesine eklemek yerine her
#    uc noktada ACIK kontrol tercih edildi.
#
#    Sebep: bu uclar zaten cari_id'yi YOLDAN aliyor
#    (/api/cari/<id>/aktivite). Acik kontrol hem daha okunur hem de
#    403 ile "yetkin yok" diyor; kuresel suzgec olsaydi bos liste
#    donerdi ve kullanici veri yok mu yetki mi yok anlamazdi.
#
#  ── ERİŞİM İSTİSNASI VERME ──
#    Yalnizca ADMIN ya da musterinin SORUMLUSU baskasina erisim
#    verebilir. Herkes verebilseydi kapali gorunurluk anlamsizlasirdi.
#
#  KULLANIM (proje klasöründe):
#      python yama_crm_e2_api.py            # rapor
#      python yama_crm_e2_api.py --uygula
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
if '_cari_gorulebilir_mi' not in _h:
    print("✗ ÖN KOŞUL: önce yama_crm_c_erisim.py uygulanmalı.")
    sys.exit(1)

# ── A) Import ──────────────────────────────────────────────────────
A_ESKI = """from models import CariErisim, CariKisi   # CRM-B: erisim ve kisiler"""
A_YENI = """from models import CariErisim, CariKisi   # CRM-B: erisim ve kisiler
from models import CariAktivite              # CRM-E: temas kaydi"""

# ── B) Uç noktalar ─────────────────────────────────────────────────
B_ESKI = """    # ---------- API: CARİ VE HAREKETLER ----------"""

B_YENI = '''    # ══════════════════════════════════════════════════════════
    #  CRM: AKTİVİTE, KİŞİLER, ERİŞİM  (CRM-E2)
    # ══════════════════════════════════════════════════════════

    AKTIVITE_TIPLERI = ('telefon', 'eposta', 'ziyaret', 'fuar',
                        'numune', 'teklif', 'diger')

    def _crm_cari_al(cari_id):
        """Cariyi getirir; gorunmuyorsa None doner.

        Kuresel suzgec zaten gizliyor ama ACIK kontrol tercih
        edildi: bos liste donmek yerine 403 demek, kullaniciya
        "veri yok mu yetki mi yok" sorusunu yasatmaz.
        """
        c = db.session.get(Cari, cari_id)
        if not c or not _cari_gorulebilir_mi(cari_id):
            return None
        return c

    def _aktivite_json(a):
        return {
            'id': a.id, 'cari_id': a.cari_id, 'kisi_id': a.kisi_id,
            'tarih': a.tarih.isoformat() if a.tarih else None,
            'tip': a.tip, 'ozet': a.ozet, 'detay': a.detay,
            'sonraki_adim': a.sonraki_adim,
            'sonraki_tarih': a.sonraki_tarih.isoformat() if a.sonraki_tarih else None,
            'tamamlandi': bool(a.tamamlandi),
            'tamamlanma': a.tamamlanma.isoformat() if a.tamamlanma else None,
            'kullanici': a.kullanici,
        }

    @app.route('/api/cari/<cari_id>/aktivite', methods=['GET'])
    def api_aktivite_liste(cari_id):
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('cari', 'okuma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        if not _crm_cari_al(cari_id):
            return jsonify({'ok': False, 'mesaj': 'Müşteri bulunamadı'}), 404
        al = CariAktivite.query.filter_by(cari_id=cari_id).order_by(
            CariAktivite.tarih.desc(), CariAktivite.id.desc()).all()
        return jsonify({'ok': True, 'data': [_aktivite_json(a) for a in al]})

    @app.route('/api/cari/<cari_id>/aktivite', methods=['POST'])
    def api_aktivite_ekle(cari_id):
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('cari', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        if not _crm_cari_al(cari_id):
            return jsonify({'ok': False, 'mesaj': 'Müşteri bulunamadı'}), 404
        d = request.json or {}
        ozet = (d.get('ozet') or '').strip()
        if not ozet:
            return jsonify({'ok': False, 'mesaj': 'Özet zorunlu'}), 400
        tip = (d.get('tip') or 'diger').strip().lower()
        if tip not in AKTIVITE_TIPLERI:
            return jsonify({'ok': False,
                            'mesaj': f"Tip: {', '.join(AKTIVITE_TIPLERI)}"}), 400
        sonraki = _parse_date(d.get('sonraki_tarih'))
        adim = (d.get('sonraki_adim') or '').strip()
        # Tarihsiz bir "sonraki adim" hatirlatilamaz; takip listesine
        # girmez ve sessizce unutulur. Ikisi birlikte istenir.
        if adim and not sonraki:
            return jsonify({'ok': False,
                            'mesaj': 'Sonraki adım girdiyseniz tarihini de '
                                     'belirtin; tarihsiz takip hatırlatılamaz'}), 400
        a = CariAktivite(
            cari_id=cari_id, kisi_id=d.get('kisi_id') or None,
            tarih=_parse_date(d.get('tarih')) or date.today(),
            tip=tip, ozet=ozet, detay=(d.get('detay') or '').strip() or None,
            sonraki_adim=adim or None, sonraki_tarih=sonraki,
            tamamlandi=False, kullanici=session.get('kullanici'))
        db.session.add(a)
        ok, hata = _safe_commit(f'Aktivite ekleme: {cari_id}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True, 'id': a.id, 'mesaj': 'Temas kaydedildi'})

    @app.route('/api/aktivite/<int:aktivite_id>', methods=['PUT'])
    def api_aktivite_guncelle(aktivite_id):
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('cari', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        a = db.session.get(CariAktivite, aktivite_id)
        if not a or not _cari_gorulebilir_mi(a.cari_id):
            return jsonify({'ok': False, 'mesaj': 'Kayıt bulunamadı'}), 404
        d = request.json or {}
        if 'ozet' in d:
            _o = (d.get('ozet') or '').strip()
            if not _o:
                return jsonify({'ok': False, 'mesaj': 'Özet boş olamaz'}), 400
            a.ozet = _o
        if 'tip' in d:
            _t = (d.get('tip') or '').strip().lower()
            if _t not in AKTIVITE_TIPLERI:
                return jsonify({'ok': False,
                                'mesaj': f"Tip: {', '.join(AKTIVITE_TIPLERI)}"}), 400
            a.tip = _t
        for alan in ('detay', 'sonraki_adim'):
            if alan in d:
                setattr(a, alan, (d.get(alan) or '').strip() or None)
        if 'tarih' in d:
            a.tarih = _parse_date(d.get('tarih')) or a.tarih
        if 'sonraki_tarih' in d:
            a.sonraki_tarih = _parse_date(d.get('sonraki_tarih'))
        if 'kisi_id' in d:
            a.kisi_id = d.get('kisi_id') or None
        if a.sonraki_adim and not a.sonraki_tarih:
            return jsonify({'ok': False,
                            'mesaj': 'Sonraki adım girdiyseniz tarihini de '
                                     'belirtin'}), 400
        ok, hata = _safe_commit(f'Aktivite guncelleme: {aktivite_id}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True, 'mesaj': 'Güncellendi'})

    @app.route('/api/aktivite/<int:aktivite_id>/tamamla', methods=['POST'])
    def api_aktivite_tamamla(aktivite_id):
        """Takibi kapatir ya da geri alir.

        ELLE isaretleme: sistemin "herhalde yapilmistir" diye
        varsaymasi, yapilmamis bir takibi yapilmis gostermekten
        daha kotu sonuc verir.
        """
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('cari', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        a = db.session.get(CariAktivite, aktivite_id)
        if not a or not _cari_gorulebilir_mi(a.cari_id):
            return jsonify({'ok': False, 'mesaj': 'Kayıt bulunamadı'}), 404
        d = request.json or {}
        a.tamamlandi = bool(d.get('tamamlandi', True))
        a.tamamlanma = date.today() if a.tamamlandi else None
        ok, hata = _safe_commit(f'Aktivite tamamlama: {aktivite_id}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True, 'tamamlandi': a.tamamlandi,
                        'mesaj': 'Takip kapatıldı' if a.tamamlandi else 'Geri alındı'})

    @app.route('/api/aktivite/<int:aktivite_id>', methods=['DELETE'])
    def api_aktivite_sil(aktivite_id):
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('cari', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        a = db.session.get(CariAktivite, aktivite_id)
        if not a or not _cari_gorulebilir_mi(a.cari_id):
            return jsonify({'ok': False, 'mesaj': 'Kayıt bulunamadı'}), 404
        db.session.delete(a)
        ok, hata = _safe_commit(f'Aktivite silme: {aktivite_id}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True, 'mesaj': 'Silindi'})

    @app.route('/api/takipler', methods=['GET'])
    def api_takipler():
        """Vadesi gelen/gecen takipler.

        Bir CRM'i not defterinden ayiran sey burasi: gecmisi degil
        GELECEGI hatirlatmasi.

        gun=7  → onumuzdeki 7 gun (varsayilan)
        Vadesi GECMIS olanlar her zaman dahil ve basta.
        """
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('cari', 'okuma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        try:
            gun = max(0, min(90, int(request.args.get('gun', 7))))
        except (TypeError, ValueError):
            gun = 7
        bugun = date.today()
        sinir = bugun + timedelta(days=gun)

        q = CariAktivite.query.filter(
            CariAktivite.tamamlandi.isnot(True),
            CariAktivite.sonraki_tarih.isnot(None),
            CariAktivite.sonraki_tarih <= sinir)
        # Kuresel suzgec CariAktivite'yi kapsamiyor; erisimi burada
        # ACIKCA uyguluyoruz.
        izin = _gorulebilir_cari_idler()
        if izin is not None:
            q = q.filter(CariAktivite.cari_id.in_(list(izin)) if izin
                         else db.false())
        kayitlar = q.order_by(CariAktivite.sonraki_tarih).all()

        unvanlar = {}
        if kayitlar:
            _idler = {a.cari_id for a in kayitlar}
            for c in Cari.query.filter(Cari.id.in_(list(_idler))).all():
                unvanlar[c.id] = c.unvan

        cikti = []
        for a in kayitlar:
            j = _aktivite_json(a)
            j['cari_unvan'] = unvanlar.get(a.cari_id, a.cari_id)
            j['gecikmis'] = a.sonraki_tarih < bugun
            j['kalan_gun'] = (a.sonraki_tarih - bugun).days
            cikti.append(j)
        return jsonify({'ok': True, 'bugun': bugun.isoformat(),
                        'gecikmis': sum(1 for x in cikti if x['gecikmis']),
                        'data': cikti})

    # ── KİŞİLER ──
    def _kisi_json(k):
        return {'id': k.id, 'cari_id': k.cari_id, 'ad': k.ad,
                'gorev': k.gorev, 'telefon': k.telefon, 'email': k.email,
                'dil': k.dil, 'birincil': bool(k.birincil),
                'aktif': k.aktif is not False, 'aciklama': k.aciklama}

    @app.route('/api/cari/<cari_id>/kisi', methods=['GET'])
    def api_kisi_liste(cari_id):
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('cari', 'okuma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        if not _crm_cari_al(cari_id):
            return jsonify({'ok': False, 'mesaj': 'Müşteri bulunamadı'}), 404
        kl = CariKisi.query.filter_by(cari_id=cari_id).order_by(
            CariKisi.birincil.desc(), CariKisi.ad).all()
        return jsonify({'ok': True, 'data': [_kisi_json(k) for k in kl]})

    @app.route('/api/cari/<cari_id>/kisi', methods=['POST'])
    def api_kisi_ekle(cari_id):
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('cari', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        if not _crm_cari_al(cari_id):
            return jsonify({'ok': False, 'mesaj': 'Müşteri bulunamadı'}), 404
        d = request.json or {}
        ad = (d.get('ad') or '').strip()
        if not ad:
            return jsonify({'ok': False, 'mesaj': 'Kişi adı zorunlu'}), 400
        birincil = bool(d.get('birincil'))
        if birincil:
            # Tek birincil kisi olmali; yoksa "kime yazayim"
            # sorusunun cevabi belirsizlesir.
            for k in CariKisi.query.filter_by(cari_id=cari_id, birincil=True).all():
                k.birincil = False
        k = CariKisi(cari_id=cari_id, ad=ad,
                     gorev=(d.get('gorev') or '').strip() or None,
                     telefon=(d.get('telefon') or '').strip() or None,
                     email=(d.get('email') or '').strip() or None,
                     dil=(d.get('dil') or '').strip() or None,
                     birincil=birincil, aktif=True,
                     aciklama=(d.get('aciklama') or '').strip() or None)
        db.session.add(k)
        ok, hata = _safe_commit(f'Kisi ekleme: {cari_id}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True, 'id': k.id, 'mesaj': f'{ad} eklendi'})

    @app.route('/api/kisi/<int:kisi_id>', methods=['PUT'])
    def api_kisi_guncelle(kisi_id):
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('cari', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        k = db.session.get(CariKisi, kisi_id)
        if not k or not _cari_gorulebilir_mi(k.cari_id):
            return jsonify({'ok': False, 'mesaj': 'Kişi bulunamadı'}), 404
        d = request.json or {}
        if 'ad' in d:
            _a = (d.get('ad') or '').strip()
            if not _a:
                return jsonify({'ok': False, 'mesaj': 'Kişi adı boş olamaz'}), 400
            k.ad = _a
        for alan in ('gorev', 'telefon', 'email', 'dil', 'aciklama'):
            if alan in d:
                setattr(k, alan, (d.get(alan) or '').strip() or None)
        if 'aktif' in d:
            k.aktif = bool(d.get('aktif'))
        if d.get('birincil'):
            for x in CariKisi.query.filter_by(cari_id=k.cari_id, birincil=True).all():
                x.birincil = False
            k.birincil = True
        elif 'birincil' in d:
            k.birincil = False
        ok, hata = _safe_commit(f'Kisi guncelleme: {kisi_id}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True, 'mesaj': 'Güncellendi'})

    @app.route('/api/kisi/<int:kisi_id>', methods=['DELETE'])
    def api_kisi_sil(kisi_id):
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('cari', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        k = db.session.get(CariKisi, kisi_id)
        if not k or not _cari_gorulebilir_mi(k.cari_id):
            return jsonify({'ok': False, 'mesaj': 'Kişi bulunamadı'}), 404
        db.session.delete(k)
        ok, hata = _safe_commit(f'Kisi silme: {kisi_id}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True, 'mesaj': 'Silindi'})

    # ── ERİŞİM İSTİSNALARI ──
    def _erisim_verebilir_mi(c):
        """Yalnizca ADMIN ya da musterinin SORUMLUSU erisim verebilir.

        Herkes verebilseydi 'kapali' gorunurluk anlamsizlasirdi:
        erisimi olan biri kendine ait olmayan musteriyi baskasina
        acabilirdi.
        """
        if (session.get('rol') or '').upper() == 'ADMIN':
            return True
        return c.sorumlu and c.sorumlu == session.get('kullanici')

    @app.route('/api/cari/<cari_id>/erisim', methods=['GET'])
    def api_erisim_liste(cari_id):
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        c = _crm_cari_al(cari_id)
        if not c:
            return jsonify({'ok': False, 'mesaj': 'Müşteri bulunamadı'}), 404
        el = CariErisim.query.filter_by(cari_id=cari_id).order_by(
            CariErisim.kullanici).all()
        return jsonify({'ok': True, 'yonetebilir': bool(_erisim_verebilir_mi(c)),
                        'data': [{'id': e.id, 'kullanici': e.kullanici,
                                  'veren': e.veren} for e in el]})

    @app.route('/api/cari/<cari_id>/erisim', methods=['POST'])
    def api_erisim_ekle(cari_id):
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        c = _crm_cari_al(cari_id)
        if not c:
            return jsonify({'ok': False, 'mesaj': 'Müşteri bulunamadı'}), 404
        if not _erisim_verebilir_mi(c):
            return jsonify({'ok': False,
                            'mesaj': 'Erişim yalnızca müşterinin sorumlusu ya '
                                     'da yönetici tarafından verilebilir'}), 403
        d = request.json or {}
        kim = (d.get('kullanici') or '').strip()
        if not kim:
            return jsonify({'ok': False, 'mesaj': 'Kullanıcı zorunlu'}), 400
        if not Kullanici.query.filter_by(ad=kim).first():
            return jsonify({'ok': False, 'mesaj': f'Kullanıcı bulunamadı: {kim}'}), 400
        if CariErisim.query.filter_by(cari_id=cari_id, kullanici=kim).first():
            return jsonify({'ok': True, 'mevcut': True,
                            'mesaj': f'{kim} zaten erişebiliyor'})
        e = CariErisim(cari_id=cari_id, kullanici=kim,
                       veren=session.get('kullanici'))
        db.session.add(e)
        ok, hata = _safe_commit(f'Erisim verme: {cari_id} -> {kim}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True, 'id': e.id, 'mesaj': f'{kim} erişebilir'})

    @app.route('/api/erisim/<int:erisim_id>', methods=['DELETE'])
    def api_erisim_sil(erisim_id):
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        e = db.session.get(CariErisim, erisim_id)
        if not e:
            return jsonify({'ok': False, 'mesaj': 'Kayıt bulunamadı'}), 404
        c = _crm_cari_al(e.cari_id)
        if not c or not _erisim_verebilir_mi(c):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        kim = e.kullanici
        db.session.delete(e)
        ok, hata = _safe_commit(f'Erisim kaldirma: {erisim_id}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True, 'mesaj': f'{kim} erişimi kaldırıldı'})

    # ---------- API: CARİ VE HAREKETLER ----------'''

BLOKLAR = [
    ("CariAktivite import", A_ESKI, A_YENI, 'from models import CariAktivite'),
    ("CRM uç noktaları",    B_ESKI, B_YENI, 'def api_aktivite_liste('),
]

print("═" * 70)
print(" CRM-E2 · CRM UÇ NOKTALARI")
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
    print("   python yama_crm_e2_api.py --uygula")
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

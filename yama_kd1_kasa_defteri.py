#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — KASA DEFTERİ  ·  KD1  (1/2: veri)
#
#  ── NEDEN YENİ TABLO YOK ──
#    `KasaHareket` zaten defterin kendisi: tarih, tip, tutar,
#    açıklama, belge bağlantısı, cari, sipariş, evrak no, kullanıcı.
#    Dokuz ayrı yerden yazılıyor — her nakit hareketi oradan geçiyor.
#    D1 değişmezlik denetimi de `Kasa.bakiye = Σ hareketler`
#    eşitliğini zaten kontrol ediyor.
#
#    İkinci bir tablo açmak PARALEL GERÇEK üretirdi. Bu oturumda
#    düzelttiğimiz hataların hepsi (fatura/tahsilat çift sayımı,
#    kapatildi çelişkisi, karşılıksız çekte iki bakiye) tam olarak
#    o kökten çıktı. Defter, veri değil GÖRÜNÜM eksikliğiydi.
#
#  ── EKSİK OLAN DÖRT ŞEY ──
#    1) Yürüyen bakiye — bir defteri defter yapan sütun. Yoktu.
#    2) Devir + tarih aralığı — mevcut uç nokta `.all()` ile TÜM
#       hareketleri döndürüyor, sınır bile yok.
#    3) `cari_id` modelde var, API yanıtında YOK — "hangi cariye
#       ait" bilgisi ekranda kullanılamıyordu.
#    4) Mutabakat — defterin kapanışı kasa bakiyesini tutuyor mu.
#
#  ── DEVİR NASIL HESAPLANIYOR ──
#    Başlangıç tarihinden ÖNCEKİ tüm hareketlerin toplamı.
#    Güvenilir, çünkü kasa açılış bakiyesi de `giris` hareketi
#    olarak yazılıyor (api_kasa_ekle) — yani bakiyenin her bileşeni
#    bir harekettir. `Kasa.bakiye` alanından geriye doğru çıkarma
#    yapılmıyor; o alan bozuksa defter de bozuk çıkardı.
#
#  ── MUTABAKAT ──
#    Dönem sonu bugün ya da sonrasıysa, hesaplanan kapanış
#    `Kasa.bakiye` ile karşılaştırılır. Tutmuyorsa yanıt bunu
#    AÇIKÇA söyler. Sessizce yanlış bakiye göstermektense
#    uyuşmazlığı bildirmek yeğdir.
#
#  ── ANA KASA ──
#    Mevcut hareket listesindeki mantık birebir korunuyor: ana kasa
#    seçilirse aynı dövizdeki alt kasaların hareketleri birleşir.
#
#  KULLANIM (proje klasöründe):
#      python yama_kd1_kasa_defteri.py            # rapor
#      python yama_kd1_kasa_defteri.py --uygula
#
#  SONRA: yama_kd2_defter_sayfa.py (ekran)
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

ESKI = """    @app.route('/api/kasa/hareket', methods=['POST'])"""

YENI = '''    # ══════════════════════════════════════════════════════════
    #  KASA DEFTERİ  (KD1)
    # ══════════════════════════════════════════════════════════

    def _kasa_defter_filtre(k):
        """Ana kasa ise alt kasalarini kapsar — mevcut hareket
        listesiyle AYNI mantik, iki yerde farkli davranmasin diye."""
        if bool(getattr(k, 'ana_kasa', False)):
            alt_q = Kasa.query.filter_by(doviz=k.doviz)
            if hasattr(Kasa, 'ana_kasa'):
                alt_q = alt_q.filter_by(ana_kasa=False)
            alt = alt_q.all()
            ids = [a.id for a in alt]
            adlar = {a.id: a.ad for a in alt}
            return (KasaHareket.kasa_id.in_(ids) if ids
                    else (KasaHareket.kasa_id == -1)), adlar
        return (KasaHareket.kasa_id == k.id), {k.id: k.ad}

    @app.route('/api/kasa/defter', methods=['GET'])
    def api_kasa_defter():
        """Kasa defteri: devir + yuruyen bakiyeli hareket dokumu.

        Parametreler:
            kasa_id=<int>          zorunlu
            baslangic=YYYY-MM-DD   varsayilan: ayin 1'i
            bitis=YYYY-MM-DD       varsayilan: bugun
        """
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('kasa', 'okuma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403

        try:
            kasa_id = int(request.args.get('kasa_id') or 0)
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'mesaj': 'Geçersiz kasa'}), 400
        k = db.session.get(Kasa, kasa_id)
        if not k:
            return jsonify({'ok': False, 'mesaj': 'Kasa bulunamadı'}), 404

        bugun = date.today()
        bas = _parse_date(request.args.get('baslangic')) or bugun.replace(day=1)
        son = _parse_date(request.args.get('bitis')) or bugun
        if son < bas:
            return jsonify({'ok': False,
                            'mesaj': 'Bitiş tarihi başlangıçtan önce olamaz'}), 400

        filtre, kasa_adlari = _kasa_defter_filtre(k)

        def _yon(h):
            t = (h.tip or '').lower()
            if t in ('giris', 'giriş'):
                return 1
            if t in ('cikis', 'çıkış', 'cikiş'):
                return -1
            return 0        # bilinmeyen tip — D1 bunu ihlal sayar

        # ── DEVIR: baslangictan ONCEKI her seyin toplami ──
        # Kasa.bakiye'den geriye cikarma YAPILMIYOR: o alan bozuksa
        # defter de sessizce bozuk cikardi. Hareketlerden hesaplamak
        # defteri kendi kendini dogrulayabilir kilar.
        devir = 0.0
        bilinmeyen = 0
        for h in KasaHareket.query.filter(filtre, KasaHareket.tarih < bas).all():
            y = _yon(h)
            if y == 0:
                bilinmeyen += 1
            devir += y * float(h.tutar or 0)

        hs = KasaHareket.query.filter(
            filtre, KasaHareket.tarih >= bas, KasaHareket.tarih <= son).order_by(
            KasaHareket.tarih.asc(), KasaHareket.id.asc()).all()

        # Cari unvanlarini TEK sorguda coz — satir basina sorgu
        # atmak uzun defterlerde sayfayi kilitlerdi.
        cari_idler = {h.cari_id for h in hs if h.cari_id}
        unvanlar = {}
        if cari_idler:
            for c in Cari.query.filter(Cari.id.in_(list(cari_idler))).all():
                unvanlar[c.id] = c.unvan

        yuruyen = devir
        toplam_g = toplam_c = 0.0
        satirlar = []
        for h in hs:
            y = _yon(h)
            if y == 0:
                bilinmeyen += 1
            tutar = float(h.tutar or 0)
            yuruyen += y * tutar
            if y > 0:
                toplam_g += tutar
            elif y < 0:
                toplam_c += tutar
            satirlar.append({
                'id': h.id,
                'tarih': h.tarih.isoformat() if h.tarih else None,
                'tip': h.tip,
                'yon': 'giris' if y > 0 else ('cikis' if y < 0 else 'bilinmiyor'),
                'tutar': q3(tutar),
                'giris': q3(tutar) if y > 0 else None,
                'cikis': q3(tutar) if y < 0 else None,
                'bakiye': q3(yuruyen),
                'aciklama': h.aciklama or '',
                'evrak_no': getattr(h, 'evrak_no', '') or '',
                'baglanti_tip': getattr(h, 'baglanti_tip', None),
                'baglanti_id': getattr(h, 'baglanti_id', None),
                'cari_id': h.cari_id,
                'cari_unvan': unvanlar.get(h.cari_id) if h.cari_id else None,
                'siparis_id': getattr(h, 'siparis_id', '') or '',
                'kasa_id': h.kasa_id,
                'kasa_adi': kasa_adlari.get(h.kasa_id, ''),
                'kullanici': getattr(h, 'kullanici', '') or '',
            })

        kapanis = q3(yuruyen)

        # ── MUTABAKAT ──
        # "Donem sonu bugunu gectiyse kapanis = Kasa.bakiye olmali"
        # demek YANLIS olurdu: ileri tarihli hareketler (vadeli
        # kayitlar) donem disinda kalir ama bakiyeye dahildir.
        #
        # Dogru esitlik HER ARALIK icin gecerli:
        #     kapanis + donemden SONRAKI hareketler = Kasa.bakiye
        #
        # Boylece mutabakat hangi tarih araligina bakilirsa bakilsin
        # anlamli kalir. Tutmuyorsa sessizce gecilmez — yanlis bakiye
        # gostermek, uyusmazligi bildirmekten kotudur.
        sonraki = 0.0
        for h in KasaHareket.query.filter(filtre, KasaHareket.tarih > son).all():
            sonraki += _yon(h) * float(h.tutar or 0)
        kayitli = q3(float(k.bakiye or 0))
        beklenen = q3(float(kapanis) + sonraki)
        fark = q3(float(beklenen) - float(kayitli))
        mutabakat = {
            'kayitli_bakiye': kayitli,
            'hesaplanan': kapanis,
            'sonraki_hareketler': q3(sonraki),
            'beklenen': beklenen,
            'fark': fark,
            'tutuyor': abs(float(fark)) < 0.01,
        }

        return jsonify({
            'ok': True,
            'kasa': {'id': k.id, 'ad': k.ad, 'doviz': k.doviz,
                     'ana_kasa': bool(getattr(k, 'ana_kasa', False)),
                     'bakiye': q3(float(k.bakiye or 0))},
            'baslangic': bas.isoformat(), 'bitis': son.isoformat(),
            'devir': q3(devir),
            'hareketler': satirlar,
            'ozet': {'giris': q3(toplam_g), 'cikis': q3(toplam_c),
                     'net': q3(toplam_g - toplam_c), 'kapanis': kapanis,
                     'adet': len(satirlar)},
            'mutabakat': mutabakat,
            'bilinmeyen_tip': bilinmeyen,
        })

    @app.route('/api/kasa/hareket', methods=['POST'])'''

IMZA = 'def api_kasa_defter('

print("═" * 70)
print(" KD1 · KASA DEFTERİ  (1/2: veri)")
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

print("  ✓ uygulanacak          GET /api/kasa/defter")
print("     devir · yürüyen bakiye · dönem özeti · mutabakat")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_kd1_kasa_defteri.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = APP.with_name(f'flask_app.py.yedek-{damga}')
shutil.copy2(APP, yedek)
APP.write_bytes(icerik.encode('utf-8'))
print()
print(f" ✓ flask_app.py  (yedek: {yedek.name})")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI  (1/2)")
print()
print(" SIRADAKİ: yama_kd2_defter_sayfa.py — ekran")
print("═" * 70)

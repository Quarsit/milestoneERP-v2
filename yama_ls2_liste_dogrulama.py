#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — LİSTE EKLEME DOĞRULAMASI  ·  LS2
#
#  ── SÜRÜM NOTU ──
#    Bu yamanın ilk sürümü mükerrer kontrolünü SQL lower() ile
#    Python .lower() karşılaştırarak yapıyordu; Türkçe 'İ' harfinde
#    ikisi farklı sonuç verdiği için koruma o değerlerde çalışmıyordu
#    (üretimde görüldü). Betik eski sürümü TANIR ve yükseltir.
#
#  ── ÖLÇÜLEN İKİ SORUN ──
#
#    1) MÜKERRER KAYIT SERBEST
#       Aynı değeri iki kez eklemek iki satır oluşturuyor:
#           ilk 200 · ikinci 200  →  TEKRAR kaydı: 2 adet
#       "Önerilen değerleri ekle" düğmesine iki kez basmak listeyi
#       ikizliyor. Açılır listelerde aynı cins iki kez görünür.
#
#    2) EKSİK ALAN → 500
#           v = Veriler(kategori=data['kategori'], deger=data['deger'])
#       Alan gelmezse KeyError, istemciye 500 döner. Doğrulanmış
#       bir 400 yerine sunucu hatası.
#
#  ── DÜZELTME ──
#    · kategori ve deger zorunlu, boşluk kırpılıyor
#    · aynı kategoride aynı değer varsa YENİ KAYIT AÇILMAZ;
#      200 + {'mevcut': True} döner (hata değil — "önerileri ekle"
#      düğmesi tekrar basıldığında gürültü çıkarmasın)
#    · karşılaştırma BÜYÜK/KÜÇÜK HARF DUYARSIZ: ekran zaten her
#      değeri büyük harfe çeviriyor, ama API'ye doğrudan gelen
#      istek 'nero' yazabilir ve 'NERO' ile ikizlenirdi
#
#  KULLANIM (proje klasöründe):
#      python yama_ls2_liste_dogrulama.py            # rapor
#      python yama_ls2_liste_dogrulama.py --uygula
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

ESKI = """        data = request.json
        v = Veriler(kategori=data['kategori'], deger=data['deger'], kisaltma=data.get('kisaltma'))
        db.session.add(v)
        db.session.commit()
        return jsonify({'ok': True})"""

YENI = '''        data = request.json or {}
        # Eksik alan onceden KeyError -> 500 veriyordu. Dogrulanmis
        # 400 hem daha dogru hem istemcide anlasilir mesaj verir.
        kategori = (data.get('kategori') or '').strip()
        deger = (data.get('deger') or '').strip()
        if not kategori or not deger:
            return jsonify({'ok': False,
                            'mesaj': 'Kategori ve değer zorunlu'}), 400

        # MUKERRER KORUMASI — onceden yoktu: ayni degeri iki kez
        # eklemek iki satir aciyordu, "onerilenleri ekle" dugmesine
        # iki kez basmak listeyi ikizliyordu.
        #
        # Kiyaslama BUYUK/KUCUK HARF DUYARSIZ: ekran degerleri buyuk
        # harfe cevirse de API'ye dogrudan gelen istek 'nero'
        # yazabilir ve 'NERO' ile ikizlenirdi.
        # KIYASLAMA PYTHON'DA, TURKCE KURALLARIYLA.
        #
        # Ilk surumde sol taraf SQL lower(), sag taraf Python
        # .lower() idi ve Turkce 'İ' harfinde ikisi FARKLI sonuc
        # veriyordu:
        #     Python  'İ'.lower() -> 'i' + U+0307 (IKI kod noktasi)
        #     SQL     lower('İ')  -> 'i'          (TEK kod noktasi)
        # Uretimde gorulen belirti: 'İşlenmiş mermer' GTIP kodu
        # dugmeye her basista yeniden ekleniyor, digerleri dogru
        # atlaniyordu — cunku o, oneriler icinde 'İ' iceren TEK
        # degerdi.
        #
        # Iki tarafi da SQL lower()'a vermek PostgreSQL'de calisir
        # ama SQLite'in lower()'i yalnizca ASCII bilir; ayni kod
        # veritabanina gore farkli davranirdi. Bu yuzden kiyaslama
        # tamamen Python'a alindi: IKI TARAF DA ayni fonksiyondan
        # gectigi surece 'İ' harfinin nasil kuculdugu onemli degil.
        #
        # TURKCE'YE OZEL ESLEME YAPILMIYOR — denendi ve YANLISTI:
        # 'I' -> 'ı' cevirimi, 'YENI CINS' ile 'yeni cins'i AYRI
        # kayit yapiyordu. Sistem bilincli olarak INGILIZCE buyuk
        # harf kurali kullaniyor (ayarlar.html: toUpperCase(), yorumu
        # "PIETRA -> PİETRA olmasin"). Kiyaslama da ayni kurala
        # uymali.
        #
        # 'PIETRA GREY' ile 'PİETRA GREY' yine AYRI kalir; bunlar
        # gercekten farkli yazimlar.
        #
        # Liste kategorileri kucuk (en buyugu ~200 kayit), tam
        # tarama maliyeti onemsiz.
        def _liste_anahtar(_s):
            return (_s or '').strip().lower()

        _hedef = _liste_anahtar(deger)
        mevcut = next(
            (v for v in Veriler.query.filter_by(kategori=kategori).all()
             if _liste_anahtar(v.deger) == _hedef), None)
        if mevcut:
            # Hata DEGIL: "onerilenleri ekle" tekrar basildiginda
            # gurultu cikarmasin, ekran "zaten vardi" desin.
            return jsonify({'ok': True, 'mevcut': True, 'id': mevcut.id,
                            'mesaj': f'{deger} zaten listede'})

        v = Veriler(kategori=kategori, deger=deger,
                    kisaltma=(data.get('kisaltma') or None))
        db.session.add(v)
        db.session.commit()
        return jsonify({'ok': True, 'mevcut': False, 'id': v.id})'''

# v2 imzasi — v1'de YOK, boylece eski surum yukseltilebiliyor.
IMZA = '_liste_anahtar'

# v1'de kalan kiyaslama blogu. Yalnizca bu parca degistirilir;
# gerisi (dogrulama, mevcut yaniti) v1'de zaten dogruydu.
V1_ESKI = """        # MUKERRER KORUMASI — onceden yoktu: ayni degeri iki kez
        # eklemek iki satir aciyordu, "onerilenleri ekle" dugmesine
        # iki kez basmak listeyi ikizliyordu.
        #
        # Kiyaslama BUYUK/KUCUK HARF DUYARSIZ: ekran degerleri buyuk
        # harfe cevirse de API'ye dogrudan gelen istek 'nero'
        # yazabilir ve 'NERO' ile ikizlenirdi.
        mevcut = Veriler.query.filter(
            Veriler.kategori == kategori,
            db.func.lower(Veriler.deger) == deger.lower()).first()"""

V1_YENI = YENI.split('        # MUKERRER KORUMASI')[1]
V1_YENI = '        # MUKERRER KORUMASI' + V1_YENI.split('        if mevcut:')[0].rstrip()

print("═" * 70)
print(" LS2 · LİSTE EKLEME DOĞRULAMASI")
print("═" * 70)
print()

ham = APP.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


if uyarla(IMZA) in ham or IMZA in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

_v1 = uyarla(V1_ESKI)
if ham.count(_v1) == 1:
    # ESKI SURUM VAR -> yalnizca kiyaslama blogunu yukselt.
    print("  ↑ eski sürüm (v1) bulundu — yükseltiliyor")
    icerik = ham.replace(_v1, uyarla(V1_YENI), 1)
    _asama = 'yükseltme'
else:
    e = uyarla(ESKI)
    adet = ham.count(e)
    if adet != 1:
        print(f" ✗ Kalıp {adet} kez bulundu (1 bekleniyordu). DOSYAYA DOKUNULMADI.")
        sys.exit(1)
    icerik = ham.replace(e, uyarla(YENI), 1)
    _asama = 'ilk uygulama'

try:
    compile(icerik, 'flask_app.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print(f"  ✓ uygulanacak          Türkçe duyarlı mükerrer koruması ({_asama})")
print("  ✓ sözdizimi doğrulandı (compile)")

if 'db.func.lower(Veriler.deger) == deger.lower()' in icerik:
    print(" ✗ Eski karşılaştırma hâlâ duruyor — DOSYAYA DOKUNULMADI.")
    sys.exit(1)
print("  ✓ eski (bozuk) karşılaştırma kalmadı")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_ls2_liste_dogrulama.py --uygula")
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

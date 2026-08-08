#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — HAREKET TARİHİ KURU + KUR FARKI  ·  KF1
#
#  ── SORUN: GEÇMİŞ TARİHLİ HAREKET BUGÜNÜN KURUNU ALIYOR ──
#    Cari hareket eklerken:
#        kullanilan_kur = _kur_getir(doviz)     ← TARİH YOK
#
#    `_kur_getir` tarihsiz çağrılınca arşivdeki EN SON kuru döndürür.
#    Yani 08.08 tarihli bir faturaya 07.09 kuru uygulanır.
#
#    ÇALIŞTIRARAK DOĞRULANDI:
#        Fatura 10.000 EUR · hareket_tarihi 2026-08-08
#        Arşiv: 08.08 → 48,50   ·   07.09 → 50,00
#        Sonuç: kur 50,00 · TL 500.000     ← 48,50 / 485.000 OLMALIYDI
#
#    Bu, E1'de ekstrede düzelttiğimiz hatanın kardeşi. Orada kur
#    bulunamayınca sıfırlanıyordu; burada YANLIŞ GÜNÜN kuru geliyor.
#
#  ── VERGİSEL SONUCU ──
#    VUK ve GİB özelgelerine göre dövizli işlemin TL karşılığı
#    İŞLEM (fatura) TARİHİNDEKİ TCMB döviz alış kuru ile hesaplanır.
#    Bugünün kuruyla hesaplamak beyanı yanlış yapar.
#
#    10.000 EUR'luk bir faturada 1,50 TL'lik kur sapması = 15.000 TL.
#
#  ── İKİNCİ SONUÇ: KUR FARKI HİÇ OLUŞMUYORDU ──
#    Fatura ve tahsilat AYNI (en son) kuru aldığı için aralarında
#    fark çıkmıyordu. `_kur_farki_hesapla_ve_olustur` yazılmış ve
#    çağrılıyor ama hesaplayacak fark bulamıyordu:
#
#        tahsilat: 200 · kur_farki_id: None
#        KUR FARKI KAYDI: 0 adet
#
#    Yani kur farkı altyapısı çalışmıyor değildi — BESLENMİYORDU.
#    Bu yama tarihi düzeltince kur farkı da kendiliğinden işler.
#
#  ── ÇÖZÜM ──
#    kullanilan_kur = _kur_getir(doviz, hareket_tarihi)
#
#    Elle kur girilmişse (manuel_kur) o öncelikli kalır — sözleşmede
#    özel kur belirlenmiş işlemler için gerekli.
#
#  KULLANIM (proje klasöründe):
#      python yama_kf1_hareket_kuru.py            # rapor
#      python yama_kf1_hareket_kuru.py --uygula   # uygula
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


def dogrula(kaynak):
    try:
        compile(kaynak, 'flask_app.py', 'exec')
        return None
    except SyntaxError as exc:
        return f"satır {exc.lineno}: {exc.msg}"


# ── B) HAREKET TARİHİ HİÇ OKUNMUYOR ────────────────────────────────
# Daha derin bir sorun: uc nokta `hareket_tarihi`ni istemciden HIC
# almiyor, her hareketi `date.today()` ile yaziyor. Yani gecmis
# tarihli fatura girilemiyor. Once tarihi okumaliyiz, sonra o tarihin
# kurunu kullanabiliriz.
B_ESKI = """        hareket = CariHareket(
            id=_yeni_id('HR'), hareket_tarihi=date.today(),"""

B_YENI = """        hareket = CariHareket(
            id=_yeni_id('HR'), hareket_tarihi=_h_tarihi,"""

C_ESKI = """        if doviz == 'TRY':
            kullanilan_kur = 1.0"""

C_YENI = """        # YAMA KF1: hareket tarihi ISTEMCIDEN alinir.
        # Eskiden okunmuyordu; her hareket bugune yaziliyordu ve
        # gecmis tarihli fatura girmek mumkun degildi.
        _h_tarihi = date.today()
        _ht = (data.get('hareket_tarihi') or '').strip()
        if _ht:
            try:
                _h_tarihi = datetime.strptime(_ht, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'ok': False,
                                'mesaj': 'Hareket tarihi GG.AA.YYYY degil, '
                                         'YYYY-AA-GG biciminde olmali'}), 400

        if doviz == 'TRY':
            kullanilan_kur = 1.0"""

A_ESKI = """        else:
            kullanilan_kur = _kur_getir(doviz)
            # TCMB kuru bulunamadıysa hata - kullanıcı manuel girmeli ya da Doviz Kur'a kayıt eklemeli
            if not kullanilan_kur or kullanilan_kur <= 0:"""

A_YENI = """        else:
            # YAMA KF1: HAREKET TARIHINDEKI kur kullanilir.
            #
            # Eskiden `_kur_getir(doviz)` tarihsiz cagriliyordu ve
            # arsivdeki EN SON kur geliyordu. Yani 08.08 tarihli bir
            # faturaya 07.09 kuru uygulaniyordu.
            #
            # VUK/GIB uygulamasinda dovizli islemin TL karsiligi ISLEM
            # TARIHINDEKI TCMB doviz alis kuru ile hesaplanir. Bugunun
            # kuruyla hesaplamak beyani yanlis yapar; 10.000 EUR'luk
            # bir faturada 1,50 TL sapma = 15.000 TL.
            #
            # AYRICA: fatura ve tahsilat ayni kuru aldigi icin aralarinda
            # fark cikmiyordu ve KUR FARKI HIC OLUSMUYORDU. Altyapi
            # calismiyor degildi — beslenmiyordu.
            kullanilan_kur = _kur_getir(doviz, _h_tarihi)
            # TCMB kuru bulunamadıysa hata - kullanıcı manuel girmeli ya da Doviz Kur'a kayıt eklemeli
            if not kullanilan_kur or kullanilan_kur <= 0:"""

print("═" * 70)
print(" KF1 · HAREKET TARİHİ KURU + KUR FARKI")
print("═" * 70)
print()

ham = APP.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


BLOKLAR = [
    ('YAMA KF1: hareket tarihi ISTEMCIDEN', C_ESKI, C_YENI, 'hareket tarihini oku'),
    ('hareket_tarihi=_h_tarihi', B_ESKI, B_YENI, 'harekete o tarihi yaz'),
    ('YAMA KF1: HAREKET TARIHINDEKI kur', A_ESKI, A_YENI, 'o tarihin kurunu kullan  [ASIL]'),
]

yeni = ham
plan, atlanan, sorunlu = [], [], []
for imza, eski, yeni_m, aciklama in BLOKLAR:
    if uyarla(imza) in yeni or imza in yeni:
        atlanan.append(aciklama)
        continue
    e = uyarla(eski)
    adet = yeni.count(e)
    if adet != 1:
        sorunlu.append((aciklama, adet))
        continue
    yeni = yeni.replace(e, uyarla(yeni_m), 1)
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
    print(" ✓ Tüm bloklar zaten uygulanmış.")
    sys.exit(0)

hata = dogrula(yeni)
if hata:
    print(f" ✗ SÖZDİZİMİ HATASI → {hata}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)
print(" ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_kf1_hareket_kuru.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = APP.with_name(f'flask_app.py.yedek-{damga}')
shutil.copy2(APP, yedek)
APP.write_bytes(yeni.encode('utf-8'))
print(f" ✓ flask_app.py  (yedek: {yedek.name})")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print(" MEVCUT KAYITLAR düzelmez — bu yama YENİ hareketleri etkiler.")
print(" Test verisiyle çalıştığınız için sorun değil.")
print("═" * 70)

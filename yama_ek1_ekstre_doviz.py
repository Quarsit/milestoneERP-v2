#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — EKSTRE KENDİ DÖVİZİNİ BOZMASIN  ·  EK1
#
#  ── ÖLÇÜLEN HATA ──
#    Ekstre TUM hareketleri once TRY'ye kopruluyor, sonra hedef
#    dovize geri ceviriyor — hareket ZATEN hedef dovizde olsa bile.
#
#    Olculdu (7 Tem 2026 alim kur 40, 21 Agu ekstre kur 46,8):
#        kur_modu='islem'   400.000 TRY / 40   = 10.000 USD  ✓
#        kur_modu='guncel'  400.000 TRY / 46,8 =  8.547 USD  ✗
#
#    10.000 USD'lik hareket, USD ekstrede 8.547 USD gorunuyordu.
#
#  ── NEDEN YANLIŞ ──
#    1 USD her zaman 1 USD'dir. Bir USD hareketini USD ekstrede
#    gosterirken kur uygulamak, olmayan bir degisim yaratir.
#    Kur cevrimi yalnizca FARKLI dovizler arasinda anlamlidir.
#
#    Eski davranis "bugun kapatsam kac eder" sorusunu cevaplamak
#    icin yazilmis; ama o soru CAPRAZ dovizde anlamli, kendi
#    dovizinde degil.
#
#  ── DÜZELTME ──
#    Kumulatif bakiye artik HEDEF DOVIZDE birikiyor:
#      · hareket dovizi == hedef doviz  → HAM tutar, kur YOK
#      · farkli doviz                   → TRY koprusuyle cevrilir
#                                          (secilen kur esasiyla)
#
#    Tek dovizli ekstrede (en yaygin durum) hicbir kur uygulanmaz;
#    'islem' ve 'guncel' AYNI sonucu verir — dogrusu da budur.
#
#  ── KUR FARKI KAYDI BU YAMANIN KONUSU DEĞİL ──
#    Otomatik kur farki KAYDI ayri bir sorun; EK2'de ele alinacak.
#    Bu yama yalnizca GOSTERIMI duzeltir, hicbir kayit olusturmaz
#    ya da silmez.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python yama_ek1_ekstre_doviz.py            # rapor
#      venv/bin/python yama_ek1_ekstre_doviz.py --uygula
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

ESKI = """            if hedef_doviz == 'TRY':
                h.bakiye = kumulatif_try
                # 'islem' kipinde her hareketin kendi dovizindeki
                # katkisini da biriktir (asagida toplam icin)
            else:
                if kur_modu == 'guncel':
                    _b_kur = _kur_getir(hedef_doviz, date.today()) or 1
                else:
                    _b_kur = _kur_getir(hedef_doviz, h.hareket_tarihi) or 1
                h.bakiye = kumulatif_try / _b_kur if _b_kur else 0"""

YENI = '''            # ── KENDİ DÖVİZİ KÖPRÜYE GİRMEZ (EK1) ──
            #
            # Onceden TUM hareketler TRY'ye kopruluyor, sonra hedef
            # dovize geri ceviriliyordu — hareket ZATEN hedef dovizde
            # olsa bile. Olculdu: 10.000 USD'lik hareket, USD
            # ekstrede 'guncel' kipinde 8.547 USD gorunuyordu
            # (400.000 TRY / 46,8).
            #
            # 1 USD her zaman 1 USD'dir; kur cevrimi yalnizca FARKLI
            # dovizler arasinda anlamlidir. Kumulatif artik HEDEF
            # DOVIZDE birikiyor:
            #   · ayni doviz  -> HAM tutar, kur yok
            #   · farkli doviz-> TRY koprusuyle, secilen kur esasiyla
            _h_dv = (h.doviz or 'TRY').upper()
            if _h_dv == hedef_doviz:
                _katki = float(h.borc or 0) - float(h.alacak or 0)
            elif hedef_doviz == 'TRY':
                _katki = float(b_try) - float(a_try)
            else:
                if kur_modu == 'guncel':
                    _b_kur = _kur_getir(hedef_doviz, date.today()) or 0
                else:
                    _b_kur = _kur_getir(hedef_doviz, h.hareket_tarihi) or 0
                # Kur bulunamazsa 0'a BOLMEK yerine katkiyi atla;
                # sessizce sifirlamak yanlis bakiye uretirdi.
                _katki = ((float(b_try) - float(a_try)) / _b_kur
                          if _b_kur > 0 else 0.0)
            _kumulatif_hedef += _katki
            h.bakiye = _kumulatif_hedef

            # TOPLAMLAR da bakiye sutunuyla AYNI esasi kullanmali.
            # Ilk surumde toplamlar eski koprulu yola dusuyordu ve
            # KARISIK dovizli ekstrede USD hareketi yine bozuluyordu
            # (10.000 -> 8.547). Olculdu ve duzeltildi.
            if _h_dv == hedef_doviz:
                _ham_borc += float(h.borc or 0)
                _ham_alacak += float(h.alacak or 0)
            else:
                _tek_doviz_hedef = False
                if hedef_doviz == 'TRY':
                    _ham_borc += float(b_try)
                    _ham_alacak += float(a_try)
                else:
                    _k = (_kur_getir(hedef_doviz, date.today()) if kur_modu == 'guncel'
                          else _kur_getir(hedef_doviz, h.hareket_tarihi)) or 0
                    if _k > 0:
                        _ham_borc += float(b_try) / _k
                        _ham_alacak += float(a_try) / _k'''

# Kümülatif değişkenini döngü öncesinde başlat
# Capa BENZERSIZ olmali: `for h in hareketler:` dosyada 13 yerde
# geciyor. Ekstre fonksiyonundaki kumulatif baslatmasina sabitlendi.
B_ESKI = """        toplam_borc_try = 0
        toplam_alacak_try = 0
        kumulatif_try = 0
        for h in hareketler:"""
B_YENI = """        toplam_borc_try = 0
        toplam_alacak_try = 0
        kumulatif_try = 0
        # Hedef dovizde biriken kumulatif (EK1). TRY kumulatifi
        # toplamlar icin ayrica tutulmaya devam ediyor.
        #
        # _tek_doviz_hedef: TUM hareketler hedef dovizde mi? Oyleyse
        # hicbir kur uygulanmaz ve 'islem' ile 'guncel' AYNI sonucu
        # verir. Hareket yoksa True kalir; bos ekstre zaten 0 gosterir.
        _kumulatif_hedef = 0.0
        _ham_borc = _ham_alacak = 0.0
        _tek_doviz_hedef = True
        for h in hareketler:"""

# Toplamlar da aynı esası kullanmalı
# Zincirin TAMAMI degistirilir. Ilk surumde yalnizca 'guncel' dali
# hedeflenmis ve `else` bir `elif`ten ONCE kalmisti -> sozdizimi
# hatasi. Yamanin compile kontrolu yakaladi, dosyaya dokunulmadi.
C_ESKI = """        elif kur_modu == 'guncel':
            son_kur = _kur_getir(hedef_doviz, date.today()) or 1
            toplam_borc = toplam_borc_try / son_kur if son_kur else 0
            toplam_alacak = toplam_alacak_try / son_kur if son_kur else 0
            net_bakiye = (toplam_borc_try - toplam_alacak_try) / son_kur if son_kur else 0
        else:
            # 'islem' kipi: her hareket kendi gunundeki kurla cevrilip
            # toplanir. Boylece toplam, ham tutarlarin toplamiyla AYNI
            # cikar ve bakiye sutununun son satiriyla TUTAR.
            toplam_borc = toplam_alacak = 0.0
            for h in hareketler:
                _k = _kur_getir(hedef_doviz, h.hareket_tarihi) or 1
                if not _k:
                    continue
                _bt = h.borc_try if h.borc_try is not None else 0
                _at = h.alacak_try if h.alacak_try is not None else 0
                toplam_borc += _bt / _k
                toplam_alacak += _at / _k
            net_bakiye = toplam_borc - toplam_alacak"""

C_YENI = """        else:
            # TOPLAMLAR BAKIYE SUTUNUYLA AYNI ESASTA (EK1).
            # Dongude hedef doviz cinsinden biriktirildi:
            #   · ayni doviz  -> HAM tutar, kur YOK
            #   · farkli doviz-> TRY koprusuyle, secilen kur esasiyla
            # Boylece tek dovizli ekstrede 'islem' ve 'guncel' AYNI
            # sonucu verir; karisik dovizde yalnizca YABANCI hareket
            # cevrilir, kendi dovizindeki bozulmaz.
            toplam_borc = _ham_borc
            toplam_alacak = _ham_alacak
            net_bakiye = _ham_borc - _ham_alacak"""

BLOKLAR = [
    ("kendi dövizi köprüsüz", ESKI, YENI, '# ── KENDİ DÖVİZİ KÖPRÜYE GİRMEZ (EK1) ──'),
    # Imza, C_YENI'nin URETTIGI metinden secilmeli. Ilk surumde
    # artik uretilmeyen bir satir imza yapilmis ve yama uygulanmis
    # dosyayi tanimiyordu.
    ("toplamlar tek dövizde", C_ESKI, C_YENI,
     'TOPLAMLAR BAKIYE SUTUNUYLA AYNI ESASTA (EK1)'),
]

print("═" * 70)
print(" EK1 · EKSTRE KENDİ DÖVİZİNİ BOZMASIN")
print("═" * 70)
print()

ham = APP.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


icerik = ham
plan, atlanan, sorunlu = [], [], []

# ── KÜMÜLATİF BAŞLATMA: yalnızca api_ekstre_pdf'e ──
# Kalip IKI ekstre fonksiyonunda da var (api_ekstre_pdf ve
# api_siparis_ekstre_pdf) ama duzeltilecek DONUSUM BLOGU yalnizca
# ilkinde. Dosya sirasinda ilk gelen api_ekstre_pdf oldugu icin
# ilk eslesme degistiriliyor; ikincisine DOKUNULMUYOR.
if uyarla('_kumulatif_hedef = 0.0') in icerik:
    atlanan.append("kümülatif başlatma")
else:
    _b = uyarla(B_ESKI)
    _nb = icerik.count(_b)
    if _nb < 1:
        sorunlu.append(("kümülatif başlatma", _nb))
    else:
        # DOGRULAMA: ilk eslesme gercekten api_ekstre_pdf icinde mi?
        _poz = icerik.find(_b)
        _fn = icerik.rfind('def api_ekstre_pdf', 0, _poz)
        _fn2 = icerik.rfind('def api_siparis_ekstre_pdf', 0, _poz)
        if _fn < 0 or _fn2 > _fn:
            sorunlu.append(("kümülatif başlatma (yanlış fonksiyon)", _nb))
        else:
            icerik = icerik.replace(_b, uyarla(B_YENI), 1)
            plan.append("kümülatif başlatma (api_ekstre_pdf)")

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
    print("   venv/bin/python yama_ek1_ekstre_doviz.py --uygula")
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

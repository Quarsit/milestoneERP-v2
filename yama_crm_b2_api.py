#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — SAHİPLİK ALANLARI · API  ·  CRM-B2
#
#  ── ÖN KOŞUL ──
#      yama_crm_b_sahiplik.py --uygula  +  goc.py uygula
#
#  ── NEDEN GEREKLİ ──
#    CRM-B alanlari modele ekledi ama API'ye eklemedi:
#      · api_cari_guncelle beyaz listesinde 'sorumlu'/'gorunurluk' yok
#      · form_denetim D2 bunu yakaladi: "modelde var, formda yok"
#
#    Muaf listesine saklamak YANLIS olurdu — gorunurluk kullanicinin
#    ayarlamasi GEREKEN bir alan. Denetim hakliydi; alan API'ye ve
#    forma girmeli.
#
#  ── DOĞRULAMA ──
#    gorunurluk yalnizca 'ortak' ya da 'kapali' olabilir. Serbest
#    metin kabul etmek, yazim hatasiyla ('Kapali', 'kapalı') suzgecin
#    hicbir dala uymamasina ve musterinin SESSIZCE herkese acik
#    kalmasina yol acardi.
#
#    sorumlu, var olan bir kullanici adi olmali. Olmayan bir ada
#    atanan musteri, hicbir satiscinin gormedigi yetim kayit olur.
#
#  KULLANIM (proje klasöründe):
#      python yama_crm_b2_api.py            # rapor
#      python yama_crm_b2_api.py --uygula
#
#  ⚠ templates/cari.html'in GÜNCEL sürümü de kopyalanmalı.
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

# ── A) Güncelleme beyaz listesi + doğrulama ───────────────────────
A_ESKI = """        for alan in ('unvan', 'cari_tip', 'ulke', 'telefon', 'email', 'adres',
                     'para_birimi', 'vergi_dairesi', 'vergi_no', 'yetkili', 'iban',
                     'uretici_kisaltma', 'aciklama', 'odeme_vadesi_gun'):"""

A_YENI = """        # GORUNURLUK DOGRULAMASI
        # Serbest metin kabul etmek tehlikeli: 'Kapali' ya da 'kapalı'
        # yazilirsa erisim suzgeci hicbir dala uymaz ve musteri
        # SESSIZCE herkese acik kalir. Sadece iki deger gecerli.
        if 'gorunurluk' in data:
            _g = (data.get('gorunurluk') or '').strip().lower()
            if _g not in ('ortak', 'kapali'):
                return jsonify({'ok': False,
                                'mesaj': "Görünürlük 'ortak' ya da 'kapali' "
                                         "olmalı"}), 400
            data['gorunurluk'] = _g

        # SORUMLU DOGRULAMASI
        # Olmayan bir kullaniciya atanan musteri, hicbir satiscinin
        # gormedigi yetim kayda donusur.
        if 'sorumlu' in data:
            _s = (data.get('sorumlu') or '').strip()
            if _s and not Kullanici.query.filter_by(ad=_s).first():
                return jsonify({'ok': False,
                                'mesaj': f'Kullanıcı bulunamadı: {_s}'}), 400
            data['sorumlu'] = _s or None

        for alan in ('unvan', 'cari_tip', 'ulke', 'telefon', 'email', 'adres',
                     'para_birimi', 'vergi_dairesi', 'vergi_no', 'yetkili', 'iban',
                     'uretici_kisaltma', 'aciklama', 'odeme_vadesi_gun',
                     'sorumlu', 'gorunurluk'):"""

# ── B) Liste yanıtına sahiplik alanları ───────────────────────────
#  DIKKAT: yardimci fonksiyonu "def api_cari_liste():" capasinin
#  ONUNE koymak, rota dekoratoru ile fonksiyon arasina girdigi icin
#  ROTAYI YARDIMCIYA baglar ve /api/cari coker. (Ilk surumde bu
#  hata yapildi ve test yakaladi.) Alanlar dogrudan serilestirmeye
#  ekleniyor.
#
#  gorunurluk NULL olabilir (eski kayit); o durumda GUVENLI taraf
#  olan 'kapali' varsayilir — bos deger 'herkes gorsun' anlamina
#  gelmemeli.
B_ESKI = """                                  'aciklama': c.aciklama} for c in paginated.items],"""
B_YENI = """                                  'aciklama': c.aciklama,
                                  'sorumlu': c.sorumlu,
                                  'gorunurluk': c.gorunurluk or 'kapali'}
                                 for c in paginated.items],"""

BLOKLAR = [
    ("güncelleme beyaz listesi + doğrulama", A_ESKI, A_YENI, "'sorumlu', 'gorunurluk'):"),
    ("liste yanıtına sahiplik alanları",     B_ESKI, B_YENI, "'gorunurluk': c.gorunurluk or 'kapali'}"),
]

print("═" * 70)
print(" CRM-B2 · SAHİPLİK ALANLARI (API)")
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
    print("   python yama_crm_b2_api.py --uygula")
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

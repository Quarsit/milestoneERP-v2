#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — LİSTE TOHUMLAMA DÜZELTMESİ  ·  LS1
#
#  ── SORUN ──
#    Ayarlar → Listeler'den sildiğiniz bir kalem, uygulamanın bir
#    sonraki açılışında GERİ GELİYOR.
#
#    Sebep `_seed_data()` içindeki kontrol:
#
#        for kat, deger in _lookup:
#            if not Veriler.query.filter_by(kategori=kat,
#                                           deger=deger).first():
#                db.session.add(Veriler(...))
#
#    Kontrol SATIR bazında. "Bu değer yoksa ekle" diyor — oysa
#    silinmiş olması tam da "bunu istemiyorum" demek. Sildiğiniz
#    her kalem her açılışta diriliyor.
#
#  ── DÜZELTME ──
#    Kontrol KATEGORİ bazına alındı: bir kategoride hiç kayıt yoksa
#    varsayılanlar yüklenir (ilk kurulum), en az bir kayıt varsa o
#    kategoriye HİÇ DOKUNULMAZ.
#
#    Böylece:
#      · Yeni kurulum      → listeler eskisi gibi dolu gelir
#      · Sizin düzenlemeniz → aynen korunur, silinen geri gelmez
#      · Kategoriyi tamamen boşaltırsanız → varsayılanlar döner
#        (kasıtlı: liste tamamen boş kalırsa formlar çalışmaz)
#
#  ── ÜLKE LİSTESİ ──
#    Aynı mantık ülkelere de uygulandı. 190+ ülkeden çalışmadığınız
#    olanları silmişseniz geri gelmez.
#
#  KULLANIM (proje klasöründe):
#      python yama_ls1_liste_tohum.py            # rapor
#      python yama_ls1_liste_tohum.py --uygula
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

ESKI = """        # Ulkeler: kisaltma = ISO3 kodu
        for _ad, _kod in _ulkeler:
            if not Veriler.query.filter_by(kategori='ulke', deger=_ad).first():
                db.session.add(Veriler(kategori='ulke', deger=_ad, kisaltma=_kod))

        for kat, deger in _lookup:
            if not Veriler.query.filter_by(kategori=kat, deger=deger).first():
                db.session.add(Veriler(kategori=kat, deger=deger))
        db.session.commit()"""

YENI = '''        # ── TOHUMLAMA: KATEGORI BAZINDA ──
        #
        # Onceden kontrol SATIR bazindaydi ("bu deger yoksa ekle").
        # Sonucu: Ayarlar > Listeler'den silinen her kalem bir
        # sonraki acilista GERI GELIYORDU. Oysa silinmis olmasi tam
        # olarak "bunu istemiyorum" demek.
        #
        # Artik: kategoride HIC kayit yoksa varsayilanlar yuklenir
        # (ilk kurulum); en az bir kayit varsa o kategoriye HIC
        # DOKUNULMAZ.
        #
        # Kategoriyi tamamen bosaltirsaniz varsayilanlar geri doner —
        # bu KASITLI: bos liste formlari calismaz hale getirir.
        def _kategori_bos_mu(kat):
            return Veriler.query.filter_by(kategori=kat).first() is None

        # Ulkeler: kisaltma = ISO3 kodu
        if _kategori_bos_mu('ulke'):
            for _ad, _kod in _ulkeler:
                db.session.add(Veriler(kategori='ulke', deger=_ad, kisaltma=_kod))

        _bos_kategoriler = {}
        for kat, deger in _lookup:
            if kat not in _bos_kategoriler:
                _bos_kategoriler[kat] = _kategori_bos_mu(kat)
            if _bos_kategoriler[kat]:
                db.session.add(Veriler(kategori=kat, deger=deger))
        db.session.commit()'''

IMZA = 'def _kategori_bos_mu('

print("═" * 70)
print(" LS1 · LİSTE TOHUMLAMA — silinen kalem geri gelmesin")
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

print("  ✓ uygulanacak          kategori bazlı tohumlama")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_ls1_liste_tohum.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = APP.with_name(f'flask_app.py.yedek-{damga}')
shutil.copy2(APP, yedek)
APP.write_bytes(icerik.encode('utf-8'))
print()
print(f" ✓ flask_app.py  (yedek: {yedek.name})")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI — silinen liste kalemleri artık geri gelmiyor")
print("═" * 70)

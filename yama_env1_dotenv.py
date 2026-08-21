#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — UYGULAMA .env OKUSUN  ·  ENV1
#
#  ── ÖLÇÜLEN AÇIK ──
#    Depoda ON BES yardimci betik `load_dotenv()` cagiriyor
#    (sema_denetim, sifirla2, crm_bag_denetim, degismezlik_denetim...).
#    `flask_app.py` CAGIRMIYOR — dosyada 'dotenv' kelimesi hic
#    gecmiyor.
#
#    Sonuc: uygulama `.env` dosyasini HIC OKUMUYOR.
#
#  ── NEDEN ŞİMDİYE KADAR GÖRÜNMEDİ ──
#    Pardus'ta systemd DATABASE_URL ve SECRET_KEY'i ortam degiskeni
#    olarak veriyor; `.env`e ihtiyac duyulmuyor. Windows denemesinde
#    ortaya cikti.
#
#  ── İKİ SONUCU VAR, İKİSİ DE SESSİZ ──
#
#    1) SECRET_KEY okunmuyor -> kod sabit gelistirme anahtarina
#       dusuyor. `.env.ornek` bunu ACIKCA guvenlik sorunu olarak
#       yaziyor:
#         "O anahtar herkese acik depoda yazili oldugu icin saldirgan
#          kendi oturum cerezini uretip ADMIN olarak girebilir."
#
#    2) DATABASE_URL okunmuyor -> uygulama `sqlite:///milestone.db`
#       varsayilanina dusuyor. Windows'ta OLCULDU: `db.create_all()`
#       PostgreSQL'e yazdigini sanip SQLite'a 33 tablo kurdu; sema
#       denetimi PostgreSQL'de "33 eksik tablo" raporladi. Uygulama
#       calisiyor gorunuyordu ama YANLIS VERITABANINA yaziyordu.
#
#    Ikisi de UYARI VERMEDEN oluyor — en tehlikeli hata bicimi.
#
#  ── NEDEN EN ÜSTTE ──
#    `load_dotenv()` os.environ okunmadan ONCE calismali. SECRET_KEY
#    kontrolu create_app() icinde (flask_app.py:31) ve DATABASE_URL
#    okumasi 218. satirda; ikisi de import sirasinda degil cagri
#    sirasinda calisiyor, ama garanti olsun diye dosyanin en basina
#    konuyor.
#
#  ── ORTAM DEĞİŞKENİ ÖNCELİKLİ ──
#    `load_dotenv()` varsayilan olarak MEVCUT ortam degiskenlerini
#    EZMEZ. Yani systemd'nin verdigi degerler gecerli kalir; `.env`
#    yalnizca eksikleri tamamlar. Pardus'taki uretim davranisi
#    DEGISMEZ.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python yama_env1_dotenv.py            # rapor
#      venv/bin/python yama_env1_dotenv.py --uygula
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

ESKI = """from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file"""

YENI = '''# ══════════════════════════════════════════════════════════════════
#  .env DOSYASINI OKU  (ENV1)
#
#  EN USTTE, digger her seyden ONCE. Asagidaki kod os.environ'dan
#  SECRET_KEY ve DATABASE_URL okuyor; bunlar okunmadan once .env
#  yuklenmis olmali.
#
#  ONCEDEN CAGRILMIYORDU. Depodaki on bes yardimci betik
#  (sema_denetim, sifirla2, crm_bag_denetim...) cagiriyordu ama
#  uygulama cagirmiyordu. Pardus'ta systemd degiskenleri sagladigi
#  icin fark edilmedi; servis DISINDA calistirildiginda iki sessiz
#  hata olusuyordu:
#
#    · SECRET_KEY okunmuyor -> depoda yazili sabit gelistirme
#      anahtari kullaniliyor (.env.ornek bunu guvenlik sorunu
#      olarak isaretlemis)
#    · DATABASE_URL okunmuyor -> sqlite:///milestone.db'ye dusuyor;
#      Windows'ta OLCULDU: db.create_all() PostgreSQL sanip SQLite'a
#      yazdi, uygulama "calisiyor" gorunurken YANLIS VERITABANINA
#      yaziyordu
#
#  override=False (varsayilan): MEVCUT ortam degiskenleri EZILMEZ.
#  systemd'nin verdigi degerler gecerli kalir, .env yalnizca
#  eksikleri tamamlar — uretim davranisi degismez.
# ══════════════════════════════════════════════════════════════════
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv()
except ImportError:  # python-dotenv kurulu degilse uygulama yine calissin
    pass

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file'''

IMZA = '#  .env DOSYASINI OKU  (ENV1)'

print("═" * 70)
print(" ENV1 · UYGULAMA .env OKUSUN")
print("═" * 70)
print()

ham = APP.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


if uyarla(IMZA) in ham or IMZA in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

if 'load_dotenv' in ham:
    print(" ✗ Dosyada zaten bir load_dotenv çağrısı var —")
    print("   elle eklenmiş olabilir. DOSYAYA DOKUNULMADI.")
    sys.exit(1)

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

# load_dotenv, os.environ'dan SECRET_KEY okunmadan ONCE gelmeli.
_ld = icerik.find('_load_dotenv()')
_sk = icerik.find("os.environ.get('SECRET_KEY')")
_du = icerik.find("os.environ.get('DATABASE_URL'")
if _ld < 0 or (_sk > 0 and _ld > _sk) or (_du > 0 and _ld > _du):
    print(" ✗ load_dotenv, ortam okumalarından SONRA kalıyor.")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print("  ✓ uygulanacak          load_dotenv() — dosyanın en üstünde")
print("  ✓ sıra doğrulandı      SECRET_KEY ve DATABASE_URL okumalarından önce")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   venv/bin/python yama_env1_dotenv.py --uygula")
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
print()
print(" Üretim davranışı DEĞİŞMEZ: systemd'nin verdiği değerler")
print(" ezilmez, .env yalnızca eksikleri tamamlar.")
print("═" * 70)

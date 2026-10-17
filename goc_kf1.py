#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — KULLANICI↔FİRMA GÖÇÜ  ·  KF1
#
#  ÖNKOŞUL: yama_kf1.py uygulanmış VE SERVİS YENİDEN BAŞLATILMIŞ olmalı.
#
#  ── SIRA NEDEN ÖNEMLİ ──
#    yama → systemctl restart → BU BETİK
#
#    `kullanici_firma` tablosunu ve `kullanicilar.firma_kapsam`
#    sütununu açılış kendisi kuruyor (db.create_all yeni TABLO,
#    SD2 yeni SÜTUN ekliyor). Bu betik onları KURMAZ; yoksa
#    "önce yeniden başlat" deyip çıkar.
#
#    Daha önemlisi: betik `firma.varsayilan` sütununu DÜŞÜRÜYOR.
#    Yeniden başlatılmamış bir sistemde ESKİ KOD hâlâ çalışıyor ve o
#    sütunu okuyor — düşürmek çalışan uygulamayı kırardı. O yüzden
#    önce yeniden başlat.
#
#  ── NE YAPAR ──
#    1) MEVCUT KULLANICILARA `firma_kapsam = 'tumu'` verir.
#
#       EN ÖNEMLİ ADIM BU. Modeldeki varsayılan 'secili' ve
#       `kullanici_firma` tablosu boş. Hiçbir şey yapılmazsa
#       yükseltmeden sonra ADMIN OLMAYAN HERKES sisteme giremez:
#       kapsamı 'secili', atanmış firması yok. Pazartesi sabahı
#       ekip kapıda kalır.
#
#       Yükseltme kimsenin erişimini SESSİZCE kesmemeli. Bugün
#       herkes tek firmada çalışıyor; 'tumu' bu davranışı aynen
#       korur. Daraltma kararı yöneticinin: Ayarlar → Kullanıcılar'dan
#       kapsamı 'seçili firmalar'a çevirip kutuları işaretler (KF3).
#
#       ADMIN'e dokunmak gerekmiyor: rolü gereği her firmayı görüyor.
#       Yine de kapsamı 'tumu' yazılıyor; rol değişirse erişimi
#       sessizce daralmasın.
#
#    2) `firma.varsayilan` sütununu DÜŞÜRÜR.
#
#       Bayrak kaldırıldı: giriş akışında kullanıcıyı sessizce bir
#       firmaya düşürüyordu ve kimse onu bilinçli ayarlamıyordu.
#       Kullanıcısız yolların çapası artık en küçük kimlikli firma
#       (_sistem_firma_id).
#
#       Sütunu veritabanında BIRAKMAK istemedim: modelde olmayıp
#       veritabanında kalan sütun `kisaltma` tuzağının aynısı olurdu
#       ve sema_denetim FAZLA sütunu göremiyor, yalnızca eksiği
#       görüyor — yani sessiz kalırdı.
#
#  ── GÜVENLİK ──
#    • --uygula OLMADAN HİÇBİR ŞEY DEĞİŞMEZ; yalnızca rapor verir.
#    • PostgreSQL'de önce pg_dump yedeği alır; yedek başarısızsa İPTAL.
#    • Tek transaction.
#    • Tekrar çalıştırılabilir: ikinci koşu "yapılacak iş yok" der.
#    • Sütun düşürme GERİ ALINAMAZ — yedek o yüzden zorunlu.
#
#  ── NOT: goc_mf1.py artık yeniden KOŞTURULAMAZ ──
#    O betik `Firma(varsayilan=True)` yazıyor; alan kalktı. İşi
#    bitmiş tek seferlik bir göç, yeniden koşturulması gerekmiyor.
#    Yine de denenirse açık bir TypeError verip durur — sessiz yanlış
#    iş yapmaz, o yüzden dokunmuyorum.
#
#  KULLANIM (proje dizininde):
#      venv/bin/python goc_kf1.py             # RAPOR
#      venv/bin/python goc_kf1.py --uygula    # UYGULAR
# ══════════════════════════════════════════════════════════════════════
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

load_dotenv()

UYGULA = '--uygula' in sys.argv
VT_URL = os.environ.get('DATABASE_URL')

if not VT_URL:
    print('HATA: DATABASE_URL bulunamadı (.env okunamadı).')
    print('  Adres olmadan yanlış veritabanına bağlanabilirdim.')
    sys.exit(1)

motor = create_engine(VT_URL)
kaynak = urlparse(VT_URL)
pg = motor.dialect.name in ('postgresql', 'postgres')
denetci = inspect(motor)

print('═' * 70)
print('  MILESTONE ERP — KULLANICI↔FİRMA GÖÇÜ  ·  KF1')
print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (hiçbir şey değişmez)')
print('═' * 70)
print(f" Veritabanı : {kaynak.path.lstrip('/')} @ {kaynak.hostname or 'yerel'}")
print(f' Sürücü     : {motor.dialect.name}')
print()


def yedek_al():
    if not pg:
        print(' ⚠ PostgreSQL değil — otomatik yedek atlandı.')
        return True
    hedef = Path.home() / 'yedekler'
    hedef.mkdir(exist_ok=True)
    dosya = hedef / f'kf1-oncesi-{datetime.now():%Y%m%d_%H%M%S}.dump'
    try:
        ortam = dict(os.environ)
        if kaynak.password:
            ortam['PGPASSWORD'] = kaynak.password
        s = subprocess.run(
            ['pg_dump', '-Fc', '-f', str(dosya),
             '-h', kaynak.hostname or 'localhost',
             '-p', str(kaynak.port or 5432),
             '-U', kaynak.username or 'postgres',
             kaynak.path.lstrip('/')],
            env=ortam, capture_output=True, text=True, timeout=600)
        if (s.returncode != 0 or not dosya.exists()
                or dosya.stat().st_size < 1024):
            print(' ✗ Yedek ALINAMADI — göç İPTAL edildi.')
            print(f'   {(s.stderr or "").strip()[:200]}')
            return False
        print(f' ✓ {dosya}  ({dosya.stat().st_size / 1024:.0f} KB)')
        return True
    except FileNotFoundError:
        print(' ✗ pg_dump bulunamadı — göç İPTAL edildi.')
        return False
    except subprocess.TimeoutExpired:
        print(' ✗ Yedek zaman aşımına uğradı — göç İPTAL edildi.')
        return False


# ══════════════════════════════════════════════════════════════════════
#  ÖNKOŞUL: yeni şema açılışta kurulmuş olmalı
# ══════════════════════════════════════════════════════════════════════
tablolar = set(denetci.get_table_names())
if 'kullanicilar' not in tablolar or 'firma' not in tablolar:
    print(' ✗ `kullanicilar` ya da `firma` tablosu yok — yanlış')
    print('   veritabanına bağlanmış olabilirim. Duruyorum.')
    sys.exit(1)

k_sutun = {s['name'] for s in denetci.get_columns('kullanicilar')}
f_sutun = {s['name'] for s in denetci.get_columns('firma')}

eksik = []
if 'kullanici_firma' not in tablolar:
    eksik.append('kullanici_firma tablosu')
if 'firma_kapsam' not in k_sutun:
    eksik.append('kullanicilar.firma_kapsam sütunu')
if eksik:
    print(' ✗ YENİ ŞEMA HENÜZ KURULMAMIŞ:')
    for e in eksik:
        print(f'     {e}')
    print()
    print('   Bunları uygulamanın AÇILIŞI kuruyor (db.create_all yeni')
    print('   tabloyu, SD2 yeni sütunu ekliyor). Sıra şu:')
    print()
    print('     python3 yama_kf1.py --uygula')
    print('     sudo systemctl restart milestone-erp')
    print('     venv/bin/python goc_kf1.py --uygula      ← sonra ben')
    print()
    print('   Bu betik onları KURMUYOR, bilerek: `varsayilan`')
    print('   sütununu düşürüyor ve yeniden başlatılmamış sistemde')
    print('   ESKİ KOD o sütunu hâlâ okuyor — düşürmek çalışan')
    print('   uygulamayı kırardı.')
    sys.exit(1)

print(' ✓ yeni şema yerinde (kullanici_firma + firma_kapsam)')
print()

# ══════════════════════════════════════════════════════════════════════
#  DURUM
# ══════════════════════════════════════════════════════════════════════
with motor.connect() as b:
    kullanicilar = b.execute(text(
        'SELECT id, ad, rol, firma_kapsam FROM kullanicilar ORDER BY id'
    )).fetchall()
    firmalar = b.execute(text(
        'SELECT id, ad FROM firma ORDER BY id')).fetchall()
    izin_n = b.execute(text(
        'SELECT COUNT(*) FROM kullanici_firma')).scalar() or 0

varsayilan_var = 'varsayilan' in f_sutun
kapsamsiz = [k for k in kullanicilar if (k[3] or '') != 'tumu']

print('─' * 70)
print(' DURUM')
print('─' * 70)
print(f'   firma            : {len(firmalar)}')
for f in firmalar:
    print(f'       [{f[0]}] {f[1]}')
print(f'   kullanıcı        : {len(kullanicilar)}')
for k in kullanicilar:
    print(f"       [{k[0]}] {k[1]:<14} {k[2] or '—':<10} "
          f"kapsam: {k[3] or '(boş)'}")
print(f'   firma izni satırı: {izin_n}')
print(f"   firma.varsayilan : {'VAR → düşürülecek' if varsayilan_var else 'yok (düşürülmüş)'}")

print()
print('─' * 70)
print(' YAPILACAK')
print('─' * 70)
is_var = False

if kapsamsiz:
    is_var = True
    print(f'   1) {len(kapsamsiz)} kullanıcıya firma_kapsam = "tumu" yazılacak:')
    for k in kapsamsiz:
        print(f"        [{k[0]}] {k[1]}  ({k[3] or 'boş'} → tumu)")
    print()
    print('      SEBEP: modeldeki varsayılan "secili" ve izin tablosu')
    print('      boş. Dokunulmazsa yükseltmeden sonra admin olmayan')
    print('      HİÇ KİMSE sisteme giremez — kapsamı "secili", atanmış')
    print('      firması yok. Yükseltme kimsenin erişimini sessizce')
    print('      kesmemeli; daraltma kararı senin (Ayarlar →')
    print('      Kullanıcılar → firma kapsamı).')
else:
    print('   1) ✓ bütün kullanıcıların kapsamı zaten "tumu"')

if varsayilan_var:
    is_var = True
    print()
    print('   2) `firma.varsayilan` sütunu DÜŞÜRÜLECEK  ⚠ geri alınamaz')
    print('      Bayrak kaldırıldı; kullanıcısız yolların çapası artık')
    print('      en küçük kimlikli firma. Sütunu veritabanında')
    print('      bırakmak, modelde olmayan bir sütun bırakmak olurdu')
    print('      ve sema_denetim fazla sütunu göremiyor.')
else:
    print('   2) ✓ `firma.varsayilan` zaten düşürülmüş')

if not is_var:
    print()
    print('═' * 70)
    print(' ⊙ Yapılacak iş yok — göç KF1 zaten uygulanmış.')
    print('═' * 70)
    sys.exit(0)

if not UYGULA:
    print()
    print('═' * 70)
    print(' RAPOR MODU — hiçbir şey değişmedi.')
    print()
    print(' Uygulamak için:')
    print('   venv/bin/python goc_kf1.py --uygula')
    print('═' * 70)
    sys.exit(0)

# ══════════════════════════════════════════════════════════════════════
#  YEDEK
# ══════════════════════════════════════════════════════════════════════
print()
print('─' * 70)
print(' YEDEK')
print('─' * 70)
if not yedek_al():
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════════
#  UYGULA (tek transaction)
# ══════════════════════════════════════════════════════════════════════
print()
print('─' * 70)
print(' UYGULANIYOR')
print('─' * 70)
try:
    with motor.begin() as b:
        if kapsamsiz:
            s = b.execute(text(
                "UPDATE kullanicilar SET firma_kapsam = 'tumu' "
                "WHERE firma_kapsam IS NULL OR firma_kapsam <> 'tumu'"))
            print(f"   ✓ {getattr(s, 'rowcount', 0)} kullanıcı → 'tumu'")
        if varsayilan_var:
            # SQLite 3.35+ ve PostgreSQL ikisi de DROP COLUMN destekler.
            b.execute(text('ALTER TABLE firma DROP COLUMN varsayilan'))
            print('   ✓ firma.varsayilan düşürüldü')
except Exception as e:
    print(f'   ✗ GÖÇ BAŞARISIZ — hiçbir şey değişmedi:\n     {e}')
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════════
#  DOĞRULAMA
# ══════════════════════════════════════════════════════════════════════
print()
print('─' * 70)
print(' DOĞRULAMA')
print('─' * 70)
hatali = False
denetci2 = inspect(create_engine(VT_URL))
with motor.connect() as b:
    _kapsamsiz = b.execute(text(
        "SELECT COUNT(*) FROM kullanicilar "
        "WHERE firma_kapsam IS NULL OR firma_kapsam <> 'tumu'")).scalar() or 0
    _n = b.execute(text('SELECT COUNT(*) FROM kullanicilar')).scalar() or 0
    if _kapsamsiz:
        print(f'   ✗ {_kapsamsiz} kullanıcının kapsamı hâlâ "tumu" değil')
        hatali = True
    else:
        print(f'   ✓ {_n} kullanıcının hepsi "tumu" — kimse kilitlenmedi')

_f2 = {s['name'] for s in denetci2.get_columns('firma')}
if 'varsayilan' in _f2:
    print('   ✗ firma.varsayilan hâlâ duruyor')
    hatali = True
else:
    print('   ✓ firma.varsayilan düşürülmüş')

# Firma sayısı değişmemeli: bu göç firma kaydına DOKUNMUYOR.
with motor.connect() as b:
    _fn = b.execute(text('SELECT COUNT(*) FROM firma')).scalar() or 0
if _fn != len(firmalar):
    print(f'   ✗ firma sayısı değişti: {len(firmalar)} → {_fn}')
    hatali = True
else:
    print(f'   ✓ {_fn} firma korundu (bu göç firmaya dokunmaz)')

print()
print('═' * 70)
if hatali:
    print(' ✗ DOĞRULAMA BAŞARISIZ — yedekten dönmeyi değerlendirin.')
    sys.exit(1)
print(' ✓ GÖÇ KF1 TAMAMLANDI')
print()
print(' Şu an HERKESİN kapsamı "tüm firmalar" — yükseltme kimsenin')
print(' erişimini kesmedi. Daraltmak için:')
print('   Ayarlar → Kullanıcılar → kullanıcıyı düzenle →')
print('   firma kapsamı "seçili firmalar" → kutuları işaretle')
print()
print(' SONRAKİ ADIM:')
print('   venv/bin/python firma_denetim.py')
print('═' * 70)

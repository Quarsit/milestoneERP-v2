#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — ŞEMA GÖÇÜ SARMALAYICISI  ·  G
#
#  NEDEN VAR:
#    Alembic komutları İKİ ortam değişkeni gerektiriyor:
#        FLASK_APP=flask_app.py          → uygulamayı bulmak için
#        MILESTONE_ACILIS_ATLA=1         → açılış işlerini atlamak için
#
#    İkisinden biri unutulunca alınan hatalar birbirine benzemiyor
#    ve yanıltıcı:
#        FLASK_APP yoksa    → "Could not locate a Flask application"
#                              ardından "No such command 'db'"
#        ACILIS_ATLA yoksa  → "no such column: ..." (model degistiyse)
#
#    Bu betik ikisini de ayarlar. Komutu yanlış çalıştırma ihtimali
#    ortadan kalkar.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python goc.py durum                  # neredeyiz
#      venv/bin/python goc.py olustur "aciklama"     # yeni revizyon
#      venv/bin/python goc.py uygula                 # upgrade
#      venv/bin/python goc.py geri                   # downgrade
#      venv/bin/python goc.py gecmis                 # revizyon listesi
#
#  Doğrudan alembic komutu da geçirilebilir:
#      venv/bin/python goc.py ham history --verbose
# ══════════════════════════════════════════════════════════════════════
import os
import subprocess
import sys
from pathlib import Path

if not Path('flask_app.py').exists():
    print("HATA: flask_app.py bu klasörde yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

if not Path('migrations').exists():
    print("HATA: migrations/ klasörü yok — altyapı kurulmamış.")
    print("  venv/bin/python migration_kur.py --uygula")
    sys.exit(1)

ORTAM = dict(
    os.environ,
    FLASK_APP='flask_app.py',
    # Alembic uygulamayi ICE AKTARIR; acilis isleri (db.create_all,
    # seed, TCMB kur cekme) o anda calisirsa HENUZ EKLENMEMIS sutunu
    # sorgulayip coker. Bkz. yama_m2_acilis_atla.py
    MILESTONE_ACILIS_ATLA='1',
)

KOMUTLAR = {
    'durum':   (['db', 'current'], 'Hangi revizyondayız'),
    'gecmis':  (['db', 'history'], 'Revizyon geçmişi'),
    'uygula':  (['db', 'upgrade'], 'Bekleyen revizyonları uygula'),
    'geri':    (['db', 'downgrade'], 'Son revizyonu GERİ AL'),
}


def yardim():
    print("═" * 66)
    print(" MILESTONE ERP — ŞEMA GÖÇÜ")
    print("═" * 66)
    print()
    for ad, (_, acik) in KOMUTLAR.items():
        print(f"   goc.py {ad:9s} {acik}")
    print(f"   goc.py {'olustur':9s} Model değişikliğinden yeni revizyon üret")
    print(f"   goc.py {'ham':9s} Ham alembic komutu (ileri kullanım)")
    print()
    print(" TİPİK AKIŞ:")
    print("   1) models.py'yi düzenleyin")
    print("   2) venv/bin/python goc.py olustur \"ne yaptigini yaz\"")
    print("   3) ⚠ migrations/versions/ altındaki YENİ dosyayı OKUYUN")
    print("      Autogenerate sütun ADI değişikliğini 'sil + ekle' sanar")
    print("      ve VERİ KAYBETTİRİR. Gözden geçirmeden uygulamayın.")
    print("   4) venv/bin/python goc.py uygula")
    print("   5) venv/bin/python sema_denetim.py        ← şema doğrulama")
    print("   6) venv/bin/python degismezlik_denetim.py ← hesap doğrulama")
    print("═" * 66)


def calistir(argumanlar):
    return subprocess.run(
        [sys.executable, '-m', 'flask'] + argumanlar, env=ORTAM).returncode


def _veritabani_bos_mu():
    """Şema hiç kurulmamış mı? (alembic_version dışında tablo yok)

    Boş veritabanında `uygula` çalıştırmak anlamsız bir hataya
    yol açıyordu:

        relation "blok_stok" does not exist

    Sebebi: ilk göç ("baseline: mevcut sema") `pass` — var olan bir
    şemayı damgalamak için yazılmış, tablo OLUŞTURMUYOR. Sonraki
    göçler o tabloların varlığını varsayıyor. Tablolar normalde
    uygulama açılışındaki `db.create_all()` ile kuruluyor ama
    `goc.py` o adımı bilerek atlıyor (MILESTONE_ACILIS_ATLA).

    Hata mesajı kullanıcıya ne yapacağını söylemiyordu; bu kontrol
    onu söylüyor.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    url = os.environ.get('DATABASE_URL')
    if not url:
        return False          # adres yoksa karar veremeyiz, karışma
    try:
        from sqlalchemy import create_engine, inspect
        tablolar = set(inspect(create_engine(url)).get_table_names())
    except Exception:
        return False          # bağlanamadıysa asıl hata zaten çıkacak
    return not (tablolar - {'alembic_version'})


if len(sys.argv) < 2:
    yardim()
    sys.exit(0)

eylem = sys.argv[1].lower()

# BOŞ VERİTABANI KORUMASI — yalnızca şema değiştiren eylemlerde.
if eylem in ('uygula', 'geri') and _veritabani_bos_mu():
    print("═" * 66)
    print(" ✗ VERİTABANI BOŞ — göç uygulanamaz")
    print("═" * 66)
    print()
    print(" Hiç tablo yok. İlk göç ('baseline: mevcut sema') var olan")
    print(" bir şemayı damgalamak için yazılmış; tablo OLUŞTURMAZ.")
    print(" Şimdi 'uygula' derseniz sonraki göç olmayan bir tabloyu")
    print(' değiştirmeye çalışır: relation "blok_stok" does not exist')
    print()
    print(" YENİ KURULUMDA doğru sıra — önce şemayı kurun, sonra damgalayın:")
    print()
    print("   venv/bin/python -c \"import flask_app; from models import db; \\")
    print("       app=flask_app.app; ctx=app.app_context(); ctx.push(); \\")
    print("       db.create_all(); print('sema kuruldu')\"")
    print()
    print("   venv/bin/python goc.py ham db stamp head")
    print("   venv/bin/python goc.py durum")
    print()
    print(" `db.create_all()` modelden EN GÜNCEL şemayı kurar; ardından")
    print(" tüm göçleri uygulanmış saymak tutarlıdır.")
    print("═" * 66)
    sys.exit(1)

if eylem in ('yardim', '--help', '-h', 'help'):
    yardim()
    sys.exit(0)

if eylem == 'olustur':
    if len(sys.argv) < 3:
        print("HATA: açıklama gerekli.")
        print('  venv/bin/python goc.py olustur "hs_kodu genisletildi"')
        sys.exit(1)
    aciklama = sys.argv[2]
    kod = calistir(['db', 'migrate', '-m', aciklama])
    if kod == 0:
        print()
        print("─" * 66)
        print(" ⚠ UYGULAMADAN ÖNCE ÜRETİLEN DOSYAYI OKUYUN")
        print("   migrations/versions/ altındaki en yeni .py")
        print()
        print("   Özellikle şuna bakın: sütun ADI değiştirdiyseniz")
        print("   autogenerate bunu 'drop_column + add_column' olarak")
        print("   üretir — o sütundaki VERİ SİLİNİR. Öyleyse dosyayı")
        print("   elle 'alter_column' olacak şekilde düzeltin.")
        print()
        print("   Sonra:  venv/bin/python goc.py uygula")
        print("─" * 66)
    sys.exit(kod)

if eylem == 'ham':
    sys.exit(calistir(sys.argv[2:]))

if eylem in KOMUTLAR:
    argumanlar, _ = KOMUTLAR[eylem]
    if eylem == 'geri':
        print("⚠ Son revizyon GERİ ALINACAK.")
        print("  Yedek aldınız mı? (sudo /usr/local/bin/milestone-yedek.sh)")
        if input("  Devam? (evet/hayir): ").strip().lower() not in ('evet', 'e'):
            print("  İptal edildi.")
            sys.exit(0)
    sys.exit(calistir(argumanlar))

print(f"Bilinmeyen komut: {eylem}")
yardim()
sys.exit(1)

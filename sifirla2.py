#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — SEÇİCİ SIFIRLAMA  ·  R5  (ÇOKLU FİRMA)
#
#  ── R4'TEN FARKI ──
#    R4 tek firmalı sisteme göre yazılmıştı. Çoklu firma (MF1–MF7)
#    gelince iki şey oldu:
#
#      1. `firma` ve `cari_firma` tabloları eklendi. İkisi de ne
#         KORUNAN ne SİLİNECEK listesindeydi; kapsama denetimi
#         doğru davrandı ve betik ÇALIŞMAYI REDDETTİ. Sessizce
#         yarım sıfırlama yapmak yerine durması iyiydi.
#
#      2. Tek bir "sıfırla" artık yetmiyor. Üç ayrı istek var ve
#         üçü başka şey yapar.
#
#  ══ ÜÇ KİP ══
#
#    1) TÜM FİRMALARI SIFIRLA            (varsayılan)
#         Her firmanın işlem verisi gider; FİRMA TANIMLARI,
#         kimlikleri, logoları, kasa/banka tanımları KALIR.
#         "Hepsiyle temiz başlangıç yapacağım" durumu.
#
#    2) SADECE BİR FİRMAYI SIFIRLA       --firma=<id|ad>
#         Yalnızca o firmanın işlem verisi gider. DİĞER FİRMALARIN
#         VERİSİ ZERRE KADAR DEĞİŞMEZ — betik bunu silmeden önce
#         sayar, sildikten sonra tekrar sayar ve tutmazsa HATA verir.
#
#    3) TÜM VERİLERİ SİL                 --tumunu-sil
#         İşlem verisi + FİRMALARIN KENDİSİ. Bir firma kalır ve
#         HANGİSİ olduğunu --kalan= ile sen söylersin (KF1: eskiden
#         `varsayilan` bayrağı karar veriyordu, bayrak kaldırıldı;
#         geri alınamaz bir kararı kimlik sırasına bırakmıyorum):
#         sistem firmasız çalışmaz ve firma
#         kimliği R2'den beri korunan "firma bilgileri, LOGO"nun
#         yaşadığı yer. Cari kartları korunur ve KALAN FİRMAYA
#         BAĞLANIR — bağlanmazsa kart diskte durur ama hiçbir
#         firmada görünmez; sessiz veri kaybından beter olur,
#         çünkü veri "var" görünür.
#
#  ══ KORUNUR (10 tablo) ══
#    cariler       Cari firma kayıtları. Önbellek bakiye alanı YOK;
#                  bakiye hareketlerden hesaplandığı için hareketleri
#                  silmek bakiyeyi kendiliğinden sıfırlar.
#    cari_firma    Hangi cari hangi firmada görünür (MF2). Sıfırlama
#                  görünürlüğü BOZMAZ: her firma için carileri yeniden
#                  işaretlemek saatler alır ve hataya açıktır.
#    cari_kisi     Müşterideki kişiler (satın alma, lojistik, muhasebe)
#    cari_erisim   Kapalı müşterilere verilmiş istisna erişimler
#    firma         Firma tanımları, kimlik, logo, belge kodu (MF5)
#    kasa / banka  Tanımlar korunur; KASA BAKİYELERİ SIFIRLANIR
#    kullanicilar  Kullanıcılar, şifreler, yetkiler
#    veriler       Listeler (cins, yüzey, ödeme, ülke), firma kimliği,
#                  LOGO, SMTP, KDV oranları
#    doviz_kur     TCMB kur arşivi (yeniden çekmek uzun sürer)
#
#  ══ SİLİNİR (27 tablo) ══
#    Tüm işlem verisi: stok, sipariş (kalem karşılama kırılımı dahil),
#    proforma, fatura, sevkiyat, kesim, maliyet, çek, kasa hareketleri,
#    cari hareketleri, KDV iade, konteyner, sabit gider, nakit planı,
#    bildirimler, denetim izi.
#
#  ══ TAM KAPSAMA DENETİMİ ══
#    Her tablo ya KORUNAN ya SİLİNECEK listesinde olmalı. Biri ikisinde
#    de yoksa betik ÇALIŞMAYI REDDEDER — ileride model eklendiğinde bu
#    dosyayı güncellemeyi unutmak sessiz kalıntı bırakmasın.
#
#    R5 EK DENETİMİ: tek firma kipinde, silinecek her tabloda
#    `firma_id` sütunu OLMALI. Olmayan bir tablo "bir firmaya ait"
#    sayılamaz; o tabloyu tümden silmek diğer firmaların verisini
#    götürürdü, bırakmak da artık kayıt bırakırdı. İkisi de yanlış,
#    o yüzden o kipte çalışmayı reddediyoruz.
#
#  ══ GÜVENLİK ══
#    • --onayla OLMADAN HİÇBİR ŞEY SİLMEZ; yalnızca rapor verir.
#    • Silmeden önce pg_dump yedeği alır; yedek başarısızsa İPTAL.
#    • Tek transaction: bir tablo hata verirse HİÇBİRİ silinmez.
#    • Yabancı anahtar sırasına göre siler (çocuk tablo önce).
#    • Silme sonrası DOKUNULMAYAN firmaların sayıları değişmedi mi
#      ve korunan tablolar yerinde mi diye kontrol eder.
#    • Diziler YALNIZCA tablo tamamen boşaldığında sıfırlanır.
#      Tek firma kipinde sıfırlanmaz: başka firmanın 500'e gelmiş
#      kayıtları dururken sayacı 1'e çekmek, ilerleyen eklemelerde
#      birincil anahtar çakışması üretirdi.
#
#  KULLANIM (proje dizininde):
#      venv/bin/python sifirla2.py                       # RAPOR
#      venv/bin/python sifirla2.py --firmalar            # firma listesi
#      venv/bin/python sifirla2.py --firma=2             # RAPOR, tek firma
#
#      venv/bin/python sifirla2.py --onayla              # TÜM FİRMALAR
#      venv/bin/python sifirla2.py --firma=2 --onayla    # SADECE o firma
#      venv/bin/python sifirla2.py --tumunu-sil --kalan=1 --onayla
#
#  ⚠ GERİ ALINAMAZ.
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

ONAY = '--onayla' in sys.argv
TUMUNU_SIL = '--tumunu-sil' in sys.argv
FIRMA_LISTESI = '--firmalar' in sys.argv
TEK_FIRMA_ARG = None
KALAN_ARG = None
for _a in sys.argv[1:]:
    if _a.startswith('--firma='):
        TEK_FIRMA_ARG = _a.split('=', 1)[1].strip()
    # KF1: --tumunu-sil kipinde hangi firmanın KALACAĞI.
    elif _a.startswith('--kalan='):
        KALAN_ARG = _a.split('=', 1)[1].strip()

# İki kip birbirini dışlar. "Tüm verileri sil ama yalnızca şu
# firmada" diye bir şey yok; sessizce birini seçmek yerine soruyoruz.
if TUMUNU_SIL and TEK_FIRMA_ARG:
    print("HATA: --tumunu-sil ile --firma= birlikte kullanılamaz.")
    print("  --tumunu-sil  bütün sistemi siler (firmalar dahil)")
    print("  --firma=N     yalnızca o firmanın işlem verisini siler")
    sys.exit(1)

VT_URL = os.environ.get('DATABASE_URL')
if not VT_URL:
    print("HATA: DATABASE_URL bulunamadı (.env okunamadı).")
    print("  Adres olmadan yanlış veritabanına bağlanabilirdim.")
    sys.exit(1)

# ── Silinecek tablolar ──
#
# SIRA ELLE TUTULMUYOR — aşağıda modelin topolojik sırasından
# TÜRETİLİYOR. Bu liste yalnızca "hangi tablolar silinecek"i söyler.
#
# NEDEN: elle sıralanan sürüm üretimde patladı. `konteyner`
# tablosu `proforma`ya yabancı anahtarla bağlıydı ama listede
# proformadan SONRA geliyordu:
#     ForeignKeyViolation: "konteyner_proforma_id_fkey"
# Tek transaction sayesinde hiçbir şey silinmedi, ama elle
# sıralama her yeni yabancı anahtarda aynı hatayı üretir.
# SQLAlchemy bağımlılık sırasını zaten biliyor; ondan alalım.
SILINECEK_TABLOLAR = [
    # Denetim izi
    'audit_log',
    # Bildirimler (BL1) — 21.09'da eklendi; eksikken kapsama denetimi
    # betiği çalıştırmayı REDDEDİYORDU.
    'bildirimler',
    # Çek
    'cek_hareket', 'cek',
    # Kesim
    'kesim_detay', 'kesim',
    # Satış zinciri
    'satis_kaydi', 'rezervasyon',
    'proforma_kalem', 'proforma',
    # R4: F1 ile gelen kalem kaynak kirilimi (stok/uretim/dis alim).
    # Betige yazilmadigi icin kapsama denetimi calismayi REDDEDIYORDU.
    'kalem_karsilama',
    'siparis_kalem',
    'faturalar',
    'konteyner',
    'sevkiyat_kayit',
    'siparis_kayit',
    # KDV iade
    'kdv_iade_dosya',
    # OR1 · İş ortaklığı — hepsi İŞLEM verisi, tanım değil. Ortağın
    # KENDİSİ cari kartında duruyor ve o korunuyor; burada silinen,
    # o ortakla yapılan işlerin hesabı. Sıra önemli: alt tablolar
    # önce, ortaklık en son.
    'ortaklik_dagitim', 'ortaklik_sermaye', 'ortaklik_vergi',
    'ortaklik_is', 'ortaklik',
    # Maliyet
    'maliyetler',
    # Stok
    'stok_cikis', 'blok_stok', 'plaka_stok', 'ebatli_stok',
    # Nakit akışı
    'nakit_plan', 'sabit_gider',
    # CRM — cari_kisi ve cari_erisim KORUNUYOR (aşağıda), yalnızca
    # aktivite siliniyor.
    'cari_aktivite',
    # Finans — cariler, KASA ve BANKA korunuyor; yalnızca
    # hareketleri siliniyor.
    'kasa_hareket', 'cari_hareket',
]

KORUNAN = {
    'cariler': 'Cari firma kayıtları (hareketleri silinir)',
    # ── ÇOKLU FİRMA (R5) ──
    #
    #   firma       Firma tanımları: ünvan, vergi no, LOGO, belge kodu.
    #               MF5'ten beri firma KİMLİĞİ burada yaşıyor; silmek
    #               R2'nin "firma bilgileri ve LOGO korunur" sözünü
    #               bozardı. --tumunu-sil kipinde biri hariç silinir.
    #
    #   cari_firma  Hangi cari hangi firmada GÖRÜNÜR (MF2). Sıfırlama
    #               işlem verisini siler, görünürlüğü BOZMAZ. Her
    #               firmada carileri yeniden işaretlemek saatler alır
    #               ve asıl risk şu: işaretlenmeyen cari diskte durur
    #               ama ekranda yok — kullanıcı "veri gitmiş" sanır.
    'firma': 'Firma tanımları, kimlik, LOGO, belge kodu',
    'cari_firma': 'Cari görünürlük üyelikleri (hangi cari hangi firmada)',
    #   kullanici_firma  Hangi kullanıcı hangi firmada çalışabilir (KF1).
    #               YETKİ kaydıdır, işlem verisi değil. Sıfırlamada
    #               silinmesi, yöneticinin tek tek verdiği firma
    #               izinlerini yok etmek olurdu: sıfırlama sonrası
    #               kimse hiçbir firmaya giremezdi ve sebebi
    #               ekranda görünmezdi. `kullanicilar` korunuyorsa
    #               onların erişimi de korunmalı.
    #
    #               --tumunu-sil kipinde SİLİNEN firmaların
    #               satırları gider (aşağıda, FIRMA_BAGLI ile):
    #               olmayan firmaya bakan izin kaydı artık kalıntı.
    'kullanici_firma': 'Kullanıcı firma izinleri (yetki kaydı)',
    # KASA/BANKA KORUNUYOR (KB1).
    # Eskiden siliniyordu; her sıfırlamada 8 kasa yeniden
    # tanımlanmak zorunda kalıyordu ve kasa yokken ödeme
    # kaydedilemiyordu. Tanımlar kalıcıdır, para hareketleri değil.
    #
    # BAKİYELER SIFIRLANIR (aşağıda): hareketler silinip bakiye
    # kalsaydı "hayalet para" olurdu — D1 değişmezliği ihlal
    # edilirdi. Açılış bakiyelerini kullanıcı yeniden girer.
    'kasa': 'Kasa/banka tanımları (BAKİYELER SIFIRLANIR)',
    'banka': 'Banka hesap tanımları (bakiye tutmaz)',
    'kullanicilar': 'Kullanıcılar, şifreler, yetkiler',
    'veriler': 'Listeler, firma bilgisi, LOGO, SMTP, KDV ayarları',
    'doviz_kur': 'TCMB kur arşivi',

    # ── CRM (R3) ──
    # Bu ikisi CARİ KAYDININ PARÇASI, işlem verisi değil:
    #
    #   cari_kisi   Müşterideki kişiler — satın almacı, lojistik,
    #               muhasebe. Cari kartını koruyup kişilerini silmek,
    #               kartın yarısını atmak olurdu. Üstelik göç bunları
    #               eski `yetkili` alanından taşıdı; silinirse o bilgi
    #               bir daha geri gelmez.
    #
    #   cari_erisim Kapalı müşterilere verilmiş istisna erişimler.
    #               Silinirse satış ekibi sessizce müşteri kaybeder;
    #               kimse "erişimim kalktı" diye uyarı almaz.
    #
    # cari_aktivite ise SİLİNİR: temas geçmişi işlem verisidir ve
    # sıfırlanan siparişlere/tekliflere atıfta bulunur. Tutmak,
    # olmayan belgelerden söz eden notlar bırakırdı.
    'cari_kisi': 'Müşteri kişileri (satın alma, lojistik, muhasebe)',
    'cari_erisim': 'Kapalı müşterilere verilmiş istisna erişimler',
}

# Tamsayı birincil anahtarlı tablolar — dizileri 1'e çekilir.
#
# KASA/BANKA BURADA YOK (KB1): tablolar artik silinmiyor, id
# sayacini sifirlamak MEVCUT kayitlarla cakisan id uretirdi.
#
# R4: bildirimler / proforma_kalem / siparis_kalem de tamsayi id
# tasiyor ve siliniyor. Dizi sifirlanmazsa "temiz baslangic"ta ilk
# kalem id'si 1 degil, eski sayacin kaldigi yerden devam ederdi.
# kalem_karsilama METIN id kullaniyor (KRS...), dizisi yok.
#
# R5: bu liste YALNIZCA tablo tamamen bosaldiginda uygulanir
# (asagidaki `dizileri_sifirla` cagrisina bak). Tek firma kipinde
# tablo bosalmiyor; sayaci 1'e cekmek baska firmanin mevcut
# id'leriyle cakisirdi.
DIZI_SIFIRLA = ['kasa_hareket', 'kesim_detay',
                'cek_hareket', 'audit_log', 'konteyner', 'cari_aktivite',
                'bildirimler', 'proforma_kalem', 'siparis_kalem']

# ── SİLME SIRASI: modelin topolojik sırasından, TERS ──
# metadata.sorted_tables ebeveynden çocuğa sıralı; silmek için
# tersi gerekiyor (çocuk önce).
try:
    os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')
    sys.path.insert(0, str(Path('.').resolve()))
    import flask_app as _fa  # noqa: F401
    from models import db as _db
    _sirali = [t.name for t in _db.metadata.sorted_tables]
    _sirali.reverse()
    _hedef = set(SILINECEK_TABLOLAR)
    # Modelde bilinen tablolar doğru sırayla; modelde olmayanlar
    # (varsa) sona.
    SIL_SIRASI = [t for t in _sirali if t in _hedef]
    SIL_SIRASI += [t for t in SILINECEK_TABLOLAR if t not in _sirali]
    if set(SIL_SIRASI) != _hedef:
        print(" ✗ Sıra türetilemedi — DOSYAYA DOKUNULMADI.")
        sys.exit(1)
    # Modeldeki sütunlar — firma kapsamı denetimi için.
    MODEL_SUTUN = {t.name: {c.name for c in t.c}
                   for t in _db.metadata.sorted_tables}
    # --tumunu-sil kipinde firma SİLİNİRKEN ona bağlı KORUNAN
    # tablolardan da (kasa, banka, veriler) o firmanın satırları
    # gitmeli; yoksa yabancı anahtar kırılır.
    FIRMA_BAGLI = [t.name for t in reversed(_db.metadata.sorted_tables)
                   if 'firma_id' in MODEL_SUTUN.get(t.name, set())
                   and t.name not in ('firma', 'audit_log')]
except SystemExit:
    raise
except Exception as _e:
    print(f" ✗ Silme sırası modelden türetilemedi: {_e}")
    print("   Elle sıralamaya düşmek yabancı anahtar hatası riski")
    print("   taşır; çalışmayı reddediyorum.")
    sys.exit(1)

# Tek firma kipinde süzülemeyen tablo var mı?
FIRMASIZ_SILINECEK = [t for t in SILINECEK_TABLOLAR
                      if 'firma_id' not in MODEL_SUTUN.get(t, set())]

motor = create_engine(VT_URL)
denetci = inspect(motor)
mevcut = set(denetci.get_table_names())
pg = motor.dialect.name in ('postgresql', 'postgres')


def tr(n):
    return f'{n:,}'.replace(',', '.')


# ══════════════════════════════════════════════════════════════════════
#  YARDIMCILAR
# ══════════════════════════════════════════════════════════════════════
def firmalari_oku(b):
    if 'firma' not in mevcut:
        return []
    # KF1: `varsayilan` sütunu KALDIRILDI. Firma sırası artık
    # kimliğe göre; "hangi firma kalacak" kararı bayraktan değil
    # --kalan= seçeneğinden geliyor (aşağıda).
    satirlar = b.execute(text(
        'SELECT id, ad, unvan, belge_kodu, aktif '
        'FROM firma ORDER BY id')).fetchall()
    return [{'id': r[0], 'ad': r[1] or '', 'unvan': r[2] or '',
             'kod': r[3] or '', 'aktif': bool(r[4])}
            for r in satirlar]


def firma_sayim(b, fid):
    """Bir firmanın silinecek tablolardaki kayıt sayısı."""
    d, toplam = {}, 0
    for t in SIL_SIRASI:
        if t not in mevcut or 'firma_id' not in MODEL_SUTUN.get(t, set()):
            continue
        n = b.execute(text(f'SELECT COUNT(*) FROM "{t}" WHERE firma_id = :f'),
                      {'f': fid}).scalar() or 0
        d[t] = n
        toplam += n
    return d, toplam


def kilitlenecekler(b, silinecek_idler, kalan_id):
    """Bu firmalar silinince SİSTEME GİREMEYECEK kullanıcılar (KF6).

    Kapsamı 'secili' olan ve ayakta kalan firmalardan HİÇBİRİNE
    atanmamış kullanıcı, sıfırlama sonrası giriş yapamaz: izin
    listesi boşalır. Ekran bu silmeyi zaten reddediyor ve kimi
    kilitleyeceğini adıyla söylüyor; BU BETİK söylemiyordu.

    İki yol arasındaki bu fark sessiz bir tuzaktı: arayüzden
    yapamadığın şeyi komut satırından farkında olmadan yapmak.
    Burada ENGELLEMİYORUZ — sıfırlama zaten bilinçli ve geri
    alınamaz bir iş — ama kimin kilitleneceğini SÖYLÜYORUZ, ki
    --onayla'dan önce görülsün.
    """
    if 'kullanici_firma' not in mevcut or 'kullanicilar' not in mevcut:
        return []
    try:
        # ADMIN ve PASİF kullanıcılar DIŞARIDA:
        #   · ADMIN rolü kapsamdan bağımsız olarak bütün firmaları
        #     görüyor (_kullanici_firma_idleri) — kilitlenemez.
        #     İlk sürümde onu da listeliyordum ve uyarı "admin
        #     giremeyecek" diyordu; yanlış alarm, uyarının tamamını
        #     güvenilmez yapar.
        #   · Pasif kullanıcı zaten giriş yapamıyor; onu saymak
        #     gürültü olurdu.
        return [r[0] for r in b.execute(text(
            'SELECT k.ad FROM kullanicilar k '
            "WHERE COALESCE(k.firma_kapsam, 'secili') <> 'tumu' "
            "  AND UPPER(COALESCE(k.rol, '')) <> 'ADMIN' "
            '  AND COALESCE(k.aktif, :e) = :e '
            '  AND NOT EXISTS (SELECT 1 FROM kullanici_firma kf '
            '                  WHERE kf.kullanici_id = k.id '
            '                    AND kf.firma_id = :kalan) '
            'ORDER BY k.ad'), {'kalan': kalan_id, 'e': True}).fetchall()]
    except Exception:
        return []


def tablo_sayim(b, tablolar):
    d = {}
    for t in tablolar:
        if t in mevcut:
            d[t] = b.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() or 0
    return d


def dizileri_sifirla(b):
    """YALNIZCA tablo tamamen boşaldığında çağrılır."""
    if not pg:
        return
    for t in DIZI_SIFIRLA:
        if t in mevcut:
            try:
                b.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('\"{t}\"','id'), 1, false)"))
            except Exception:
                pass


def kasa_bakiye_sifirla(b, fid=None):
    """Hareketler silindi; bakiye alanı eski değerinde kalamaz.

    DİKKAT: bu iş `if pg:` DIŞINDA olmalı. İlk sürümde içinde kalmıştı
    ve yalnızca PostgreSQL'de çalışıyordu; SQLite'ta bakiyeler olduğu
    gibi kalıyordu.

    YALNIZCA `kasa` — `banka` tablosunda BAKİYE SÜTUNU YOK. İlk
    sürümde ('kasa','banka') yazmıştım; olmayan sütuna yazmaya
    kalkmak PostgreSQL'de UndefinedColumn attı, başarısız sorgu
    işlemi ZEHİRLEDİ ve o ana kadarki TÜM SİLMELER geri alındı.
    Ekranda "41 kayıt silindi" yazıp doğrulamada "hâlâ 41 kayıt var"
    çıkmasının sebebi buydu. try/except yetmez: PostgreSQL'de hatalı
    sorgudan sonra işlem ancak ROLLBACK ile kurtulur. Doğru çözüm
    hatayı hiç doğurmamak.
    """
    if 'kasa' not in mevcut:
        return 0
    if fid is None:
        s = b.execute(text('UPDATE kasa SET bakiye = 0 WHERE bakiye <> 0'))
    else:
        s = b.execute(text('UPDATE kasa SET bakiye = 0 '
                           'WHERE bakiye <> 0 AND firma_id = :f'), {'f': fid})
    return getattr(s, 'rowcount', 0) or 0


def yedek_al():
    """pg_dump — başarısızsa çağıran İPTAL eder."""
    if not pg:
        print(" ⚠ PostgreSQL değil — otomatik yedek atlandı.")
        return True
    hedef = Path.home() / 'yedekler'
    hedef.mkdir(exist_ok=True)
    dosya = hedef / f"sifirlama-oncesi-{datetime.now():%Y%m%d_%H%M%S}.dump"
    try:
        ortam = dict(os.environ)
        if kaynak.password:
            ortam['PGPASSWORD'] = kaynak.password
        sonuc = subprocess.run(
            ['pg_dump', '-Fc', '-f', str(dosya),
             '-h', kaynak.hostname or 'localhost',
             '-p', str(kaynak.port or 5432),
             '-U', kaynak.username or 'postgres',
             kaynak.path.lstrip('/')],
            env=ortam, capture_output=True, text=True, timeout=600)
        if (sonuc.returncode != 0 or not dosya.exists()
                or dosya.stat().st_size < 1024):
            print(" ✗ Yedek ALINAMADI — silme İPTAL edildi.")
            print(f"   {(sonuc.stderr or '').strip()[:200]}")
            return False
        print(f" ✓ {dosya}  ({dosya.stat().st_size / 1024:.0f} KB)")
        return True
    except FileNotFoundError:
        print(" ✗ pg_dump bulunamadı — silme İPTAL edildi.")
        return False
    except subprocess.TimeoutExpired:
        print(" ✗ Yedek zaman aşımına uğradı — silme İPTAL edildi.")
        return False


# ══════════════════════════════════════════════════════════════════════
#  BAŞLIK
# ══════════════════════════════════════════════════════════════════════
kaynak = urlparse(VT_URL)
print("═" * 70)
print(" MILESTONE ERP — SEÇİCİ SIFIRLAMA  (R5: çoklu firma)")
print("═" * 70)
print(f" Veritabanı : {kaynak.path.lstrip('/')} @ {kaynak.hostname or 'yerel'}")
print(f" Sürücü     : {motor.dialect.name}")
print()

# ── TAM KAPSAMA DENETİMİ ──
# Her tablo ya korunmalı ya silinmeli. Ucu acik tablo kalirsa
# sessizce test verisi kalir; bunu HATA sayiyoruz.
bilinen = set(SILINECEK_TABLOLAR) | set(KORUNAN)
gozden_kacan = sorted(t for t in mevcut
                      if t not in bilinen and t != 'alembic_version')
if gozden_kacan:
    print(" ✗ KAPSAM DIŞI TABLO(LAR) VAR — çalışmayı reddediyorum:")
    for t in gozden_kacan:
        print(f"     {t}")
    print()
    print("   Bu tablolar ne korunuyor ne siliniyor. Sessizce test")
    print("   verisi bırakmamak için betiği güncelleyin.")
    sys.exit(1)
# KF4 · SAYI DOĞRU OLSUN
# Burada `len(mevcut)` yazıyordu ve `alembic_version`'ı da sayıyordu.
# Oysa o tablo SINIFLANDIRILMIŞ değil, kapsama denetiminden MUAF
# TUTULMUŞ (yukarıdaki `t != 'alembic_version'`). "38 tablonun hepsi
# sınıflandırılmış" cümlesi 37 doğru, 1 yanlıştı. Küçük bir sapma ama
# bu betiğin bütün değeri raporunun doğruluğundan geliyor.
_muaf = sorted(t for t in mevcut if t == 'alembic_version')
_siniflanan = len(mevcut) - len(_muaf)
print(f" ✓ kapsama tam — {_siniflanan} tablonun hepsi sınıflandırılmış"
      + (f" ({', '.join(_muaf)} muaf)" if _muaf else ""))

# ══════════════════════════════════════════════════════════════════════
#  FİRMALAR
# ══════════════════════════════════════════════════════════════════════
with motor.connect() as b:
    firmalar = firmalari_oku(b)
    firma_sayimlari = {f['id']: firma_sayim(b, f['id'])[1] for f in firmalar}

if not firmalar:
    print()
    print(" ⚠ Hiç firma kaydı yok.")
    print("   Çoklu firma göçü (goc_mf1.py) çalıştırılmamış olabilir;")
    print("   ya da veritabanı bomboş. Tek firma kipi kullanılamaz.")
    if TEK_FIRMA_ARG or TUMUNU_SIL:
        sys.exit(1)
else:
    print(f" ✓ {len(firmalar)} firma kayıtlı")

print()
print("─" * 70)
print(" FİRMALAR")
print("─" * 70)
# KF1: ★ (varsayılan) işareti KALKTI — bayrak kaldırıldı.
for f in firmalar:
    kapali = '' if f['aktif'] else '  (kapalı)'
    print(f"     [{f['id']:>2}] {f['ad']:<18} {f['kod']:<5} "
          f"{tr(firma_sayimlari.get(f['id'], 0)):>9} kayıt{kapali}")

if FIRMA_LISTESI:
    print("═" * 70)
    sys.exit(0)

# ── KİP SEÇİMİ ──
TEK_FIRMA = None
if TEK_FIRMA_ARG:
    adaylar = [f for f in firmalar
               if str(f['id']) == TEK_FIRMA_ARG
               or f['ad'].strip().upper() == TEK_FIRMA_ARG.upper()]
    if not adaylar:
        print()
        print(f" ✗ Firma bulunamadı: {TEK_FIRMA_ARG}")
        print("   Yukarıdaki listeden kimlik ya da adı yazın.")
        sys.exit(1)
    if len(adaylar) > 1:
        print()
        print(f" ✗ '{TEK_FIRMA_ARG}' birden çok firmaya uyuyor — kimlik yazın.")
        sys.exit(1)
    TEK_FIRMA = adaylar[0]

    # Süzülemeyen tablo varsa tek firma kipi GÜVENLİ DEĞİL.
    if FIRMASIZ_SILINECEK:
        print()
        print(" ✗ TEK FİRMA KİPİ KULLANILAMAZ — firma_id'si olmayan")
        print("   silinecek tablo(lar) var:")
        for t in FIRMASIZ_SILINECEK:
            print(f"     {t}")
        print()
        print("   Bu tabloyu tümden silmek DİĞER firmaların verisini")
        print("   götürür, bırakmak da artık kayıt bırakır. İkisi de")
        print("   yanlış; tabloya firma_id ekleyin (FirmaKapsamli) ya da")
        print("   KORUNAN listesine alın.")
        sys.exit(1)

if TUMUNU_SIL:
    KIP = 'tumunu'
    # ── HANGİ FİRMA KALACAK? ──
    # Sistem firmasız çalışmaz; üstelik firma kaydı R2'den beri
    # korunan "firma bilgileri ve LOGO"nun yaşadığı yer (MF5). Yani
    # bu kipte bir firma KALMAK ZORUNDA.
    #
    # KF1'den önce bu karar `varsayilan` bayrağından geliyordu.
    # Bayrak kaldırıldı ve yerine EN KÜÇÜK KİMLİĞİ koymadım: hangi
    # firmanın yaşayacağı GERİ ALINAMAZ bir karar ve kimlik sırası
    # bunun için bir gerekçe değil. Birden çok firma varsa betik
    # artık SORUYOR.
    if len(firmalar) > 1 and not KALAN_ARG:
        print()
        print(" ✗ HANGİ FİRMA KALACAK? --kalan= ile söyle.")
        print()
        print("   Bu kip diğer firmaları SİLER; hangisinin kalacağı")
        print("   geri alınamaz bir karar, tahmin etmiyorum.")
        print()
        for f in firmalar:
            print(f"     venv/bin/python sifirla2.py --tumunu-sil "
                  f"--kalan={f['id']} --onayla      # {f['ad']}")
        print()
        sys.exit(1)
    if KALAN_ARG:
        _ad = [f for f in firmalar
               if str(f['id']) == KALAN_ARG
               or f['ad'].strip().upper() == KALAN_ARG.upper()]
        if not _ad:
            print(f"\n ✗ Kalacak firma bulunamadı: {KALAN_ARG}")
            sys.exit(1)
        if len(_ad) > 1:
            print(f"\n ✗ '{KALAN_ARG}' birden çok firmaya uyuyor — kimlik yaz.")
            sys.exit(1)
        _kalan = _ad[0]
    else:
        _kalan = firmalar[0]          # tek firma var, seçilecek bir şey yok
    KALAN_FIRMA = _kalan
    SILINEN_FIRMALAR = [f for f in firmalar if f['id'] != _kalan['id']]
    KIP_ADI = 'TÜM VERİLERİ SİL'
elif TEK_FIRMA:
    KIP = 'tek'
    KIP_ADI = f"SADECE {TEK_FIRMA['ad']} FİRMASINI SIFIRLA"
else:
    KIP = 'tum_firmalar'
    KIP_ADI = 'TÜM FİRMALARI SIFIRLA (firma tanımları kalır)'

print()
print("─" * 70)
print(f" KİP: {KIP_ADI}")
print("─" * 70)

with motor.connect() as b:
    korunan_sayim = tablo_sayim(b, KORUNAN.keys())
    if KIP == 'tek':
        sayim, toplam = firma_sayim(b, TEK_FIRMA['id'])
        eksik = []
    else:
        sayim, eksik, toplam = {}, [], 0
        for t in SIL_SIRASI:
            if t not in mevcut:
                eksik.append(t)
                continue
            n = b.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() or 0
            sayim[t] = n
            toplam += n
    # audit_log'da firmaya bağlanmamış satırlar: tek firma kipinde
    # SİLİNMEZ (hangi firmaya ait olduğu bilinmiyor). Sessiz kalmasın.
    audit_bagsiz = 0
    if 'audit_log' in mevcut:
        audit_bagsiz = b.execute(text(
            'SELECT COUNT(*) FROM audit_log WHERE firma_id IS NULL')).scalar() or 0

print()
print(" KORUNACAK")
for t, aciklama in KORUNAN.items():
    n = korunan_sayim.get(t, 0)
    not_ = ''
    if KIP == 'tumunu' and t in ('firma',):
        not_ = f'  → {len(SILINEN_FIRMALAR)} firma SİLİNECEK, 1 kalacak'
    elif KIP == 'tumunu' and t in ('kasa', 'banka', 'veriler', 'cari_firma'):
        not_ = '  → silinen firmaların satırları gider'
    print(f"   {t:<16s} {tr(n):>7} kayıt   {aciklama}{not_}")

print()
print(" SİLİNECEK")
for t in SIL_SIRASI:
    if sayim.get(t):
        print(f"   {t:<16s} {tr(sayim[t]):>7} kayıt")
bos = [t for t in SIL_SIRASI if sayim.get(t) == 0]
if bos:
    print(f"   (zaten boş: {', '.join(bos)})")
if eksik:
    print(f"   (tabloda yok: {', '.join(eksik)})")
print()
print(f"   TOPLAM {tr(toplam)} kayıt silinecek")

if KIP == 'tek':
    print()
    print(" DOKUNULMAYACAK FİRMALAR")
    for f in firmalar:
        if f['id'] == TEK_FIRMA['id']:
            continue
        print(f"   [{f['id']:>2}] {f['ad']:<18} "
              f"{tr(firma_sayimlari.get(f['id'], 0)):>9} kayıt — DEĞİŞMEYECEK")
    if audit_bagsiz:
        print()
        print(f"   NOT: audit_log'da firmaya bağlanmamış {tr(audit_bagsiz)} satır")
        print("        var; hangi firmaya ait olduğu bilinmediği için")
        print("        SİLİNMEYECEK. (Göç öncesi kayıtlar ve silinmiş")
        print("        firmalardan kopan izler.)")

if KIP == 'tumunu':
    print()
    print(" FİRMA TANIMLARI")
    print(f"   KALACAK : [{KALAN_FIRMA['id']}] {KALAN_FIRMA['ad']} "
          f"— kimliği, ünvanı, logosu korunur")
    for f in SILINEN_FIRMALAR:
        print(f"   SİLİNİR : [{f['id']}] {f['ad']}")
    print()
    print("   Cari kartları korunur ve KALAN FİRMAYA BAĞLANIR.")
    print("   Bağlanmazsa kart diskte durur ama hiçbir firmada")
    print("   görünmez — kullanıcı 'verim gitti' sanar.")
    # ── KF6 · KİM KİLİTLENİYOR ──
    with motor.connect() as _b:
        _kilit = kilitlenecekler(_b, [f['id'] for f in SILINEN_FIRMALAR],
                                 KALAN_FIRMA['id'])
    if _kilit:
        print()
        print("   ⚠ BU KULLANICILAR SİSTEME GİREMEYECEK:")
        for _ad in _kilit:
            print(f"       {_ad}")
        print()
        print("   Kapsamları 'seçili firmalar' ve kalan firmaya")
        print("   atanmamışlar; sıfırlamadan sonra izin listeleri boş")
        print("   kalıyor. Arayüzdeki firma silme bunu REDDEDİYOR,")
        print("   burada engellemiyorum — ama bilerek devam et.")
        print()
        print("   Çözüm (sıfırlamadan SONRA da olur):")
        print("     Ayarlar → Kullanıcılar → kullanıcıyı düzenle →")
        print(f"     firma kapsamı → [{KALAN_FIRMA['id']}] "
              f"{KALAN_FIRMA['ad']} işaretle")

# ══════════════════════════════════════════════════════════════════════
#  RAPOR MODU
# ══════════════════════════════════════════════════════════════════════
if not ONAY:
    print()
    print("═" * 70)
    print(" RAPOR MODU — hiçbir şey silinmedi.")
    print()
    print(" SEÇENEKLER")
    print()
    print("   1) TÜM FİRMALARI SIFIRLA — işlem verisi gider,")
    print("      firma tanımları/kimlikleri/kasaları kalır:")
    print("        venv/bin/python sifirla2.py --onayla")
    print()
    print("   2) SADECE BİR FİRMAYI SIFIRLA — diğerlerine dokunulmaz:")
    for f in firmalar:
        print(f"        venv/bin/python sifirla2.py --firma={f['id']} "
              f"--onayla      # {f['ad']}")
    print()
    print("   3) TÜM VERİLERİ SİL — firmalar da gider, biri kalır.")
    print("      Hangisinin KALACAĞINI sen söylüyorsun (KF1):")
    if len(firmalar) > 1:
        for f in firmalar:
            print(f"        venv/bin/python sifirla2.py --tumunu-sil "
                  f"--kalan={f['id']} --onayla   # {f['ad']} kalır")
    else:
        print("        venv/bin/python sifirla2.py --tumunu-sil --onayla")
        print("        (tek firma var, seçilecek bir şey yok)")
    print()
    print(" ⚠ Önce elle yedek alın:")
    print("   sudo /usr/local/bin/milestone-yedek.sh")
    print("═" * 70)
    sys.exit(0)

# ══════════════════════════════════════════════════════════════════════
#  YEDEK
# ══════════════════════════════════════════════════════════════════════
print()
print("─" * 70)
print(" YEDEK")
print("─" * 70)
if not yedek_al():
    sys.exit(1)

# ── Silme öncesi FİRMA BAŞINA fotoğraf ──
# Tek firma kipinin tek sözü bu: diğer firmalar DEĞİŞMEZ. Sözü
# tutup tutmadığımızı ölçmenin yolu, silmeden önce ve sonra
# saymaktan geçiyor.
with motor.connect() as b:
    once_firma = {f['id']: firma_sayim(b, f['id'])[1] for f in firmalar}
    once_korunan = tablo_sayim(b, KORUNAN.keys())

# ══════════════════════════════════════════════════════════════════════
#  SİLME (tek transaction)
# ══════════════════════════════════════════════════════════════════════
print()
print("─" * 70)
print(" SİLİNİYOR")
print("─" * 70)
with motor.begin() as b:
    if KIP == 'tek':
        fid = TEK_FIRMA['id']
        for t in SIL_SIRASI:
            if t not in mevcut:
                continue
            n = sayim.get(t, 0)
            b.execute(text(f'DELETE FROM "{t}" WHERE firma_id = :f'), {'f': fid})
            if n:
                print(f"   {t:<16s} {tr(n):>7} kayıt silindi")
        # DİZİ SIFIRLAMA YOK: tablolar boşalmadı. Sayacı 1'e çekmek
        # diğer firmanın mevcut id'leriyle çakışan id üretirdi.
        _n = kasa_bakiye_sifirla(b, fid)
        if _n:
            print(f"   kasa             {_n} kaydın bakiyesi sıfırlandı")
    else:
        for t in SIL_SIRASI:
            if t not in mevcut:
                continue
            n = sayim.get(t, 0)
            b.execute(text(f'DELETE FROM "{t}"'))
            if n:
                print(f"   {t:<16s} {tr(n):>7} kayıt silindi")
        dizileri_sifirla(b)
        _n = kasa_bakiye_sifirla(b, None)
        if _n:
            print(f"   kasa             {_n} kaydın bakiyesi sıfırlandı")

    if KIP == 'tumunu':
        print()
        for f in SILINEN_FIRMALAR:
            # Firmaya bağlı KORUNAN tablolardan da (kasa, banka,
            # veriler, cari_firma) bu firmanın satırları gitmeli;
            # yoksa `firma` silinirken yabancı anahtar kırılır.
            for t in FIRMA_BAGLI:
                if t in mevcut:
                    b.execute(text(f'DELETE FROM "{t}" WHERE firma_id = :f'),
                              {'f': f['id']})
            # Denetim izi SİLİNMEZ, yalnızca bağı koparılır: silinmiş
            # firmada ne yapıldığı da görünebilmeli (MF4 ile aynı
            # davranış).
            if 'audit_log' in mevcut:
                b.execute(text('UPDATE audit_log SET firma_id = NULL '
                               'WHERE firma_id = :f'), {'f': f['id']})
            b.execute(text('DELETE FROM firma WHERE id = :f'), {'f': f['id']})
            print(f"   firma [{f['id']}] {f['ad']} silindi")

        # Kalan firma AÇIK olsun: kapalı tek firma, girilemeyen bir
        # sistem demek olurdu. (KF1: `varsayilan` kalktı, yalnızca
        # `aktif` yazılıyor.)
        b.execute(text('UPDATE firma SET aktif = :e WHERE id = :f'),
                  {'e': True, 'f': KALAN_FIRMA['id']})

        # ── CARİ GÖRÜNÜRLÜĞÜ ──
        # Üyeliği kalmayan cari hiçbir firmada LİSTELENMEZ. Kart
        # diskte durur ama ekranda yok; bu, veriyi silmekten beter:
        # kullanıcı kaybı görür, sebebini bulamaz. Hepsini kalan
        # firmaya bağlıyoruz.
        _simdi = datetime.now()
        _artik = [r[0] for r in b.execute(text(
            'SELECT c.id FROM cariler c WHERE NOT EXISTS '
            '(SELECT 1 FROM cari_firma cf WHERE cf.cari_id = c.id '
            ' AND cf.firma_id = :f)'), {'f': KALAN_FIRMA['id']}).fetchall()]
        for _cid in _artik:
            b.execute(text('INSERT INTO cari_firma (cari_id, firma_id, olusturma) '
                           'VALUES (:c, :f, :o)'),
                      {'c': _cid, 'f': KALAN_FIRMA['id'], 'o': _simdi})
        if _artik:
            print(f"   {len(_artik)} cari [{KALAN_FIRMA['id']}] "
                  f"{KALAN_FIRMA['ad']} firmasına bağlandı")

# ══════════════════════════════════════════════════════════════════════
#  DOĞRULAMA
# ══════════════════════════════════════════════════════════════════════
print()
print("─" * 70)
print(" DOĞRULAMA")
print("─" * 70)
hatali = False
with motor.connect() as b:
    # 1 · Silinmesi gerekenler gitti mi?
    if KIP == 'tek':
        _, kalan_toplam = firma_sayim(b, TEK_FIRMA['id'])
        if kalan_toplam:
            print(f"   ✗ {TEK_FIRMA['ad']}: hâlâ {tr(kalan_toplam)} kayıt var")
            hatali = True
        else:
            print(f"   ✓ {TEK_FIRMA['ad']} sıfırlandı")
    else:
        kalinti = 0
        for t in SIL_SIRASI:
            if t not in mevcut:
                continue
            n = b.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() or 0
            if n:
                print(f"   ✗ {t:<16s} hâlâ {tr(n)} kayıt var")
                kalinti += n
                hatali = True
        if not kalinti:
            print("   ✓ silinecek tabloların hepsi boş")

    # 2 · DOKUNULMAYAN FİRMALAR — tek firma kipinin asıl sözü
    if KIP == 'tek':
        for f in firmalar:
            if f['id'] == TEK_FIRMA['id']:
                continue
            _, simdi = firma_sayim(b, f['id'])
            beklenen = once_firma.get(f['id'], 0)
            if simdi != beklenen:
                print(f"   ✗ [{f['id']}] {f['ad']}: {tr(beklenen)} kayıt "
                      f"beklenirken {tr(simdi)} var — VERİ KAYBI")
                hatali = True
            else:
                print(f"   ✓ [{f['id']}] {f['ad']:<18} "
                      f"{tr(simdi):>9} kayıt — değişmedi")

    # 3 · Korunan tablolar
    simdi_korunan = tablo_sayim(b, KORUNAN.keys())
    for t in KORUNAN:
        if t not in mevcut:
            continue
        simdi = simdi_korunan.get(t, 0)
        beklenen = once_korunan.get(t, 0)

        # ── cari_firma, --tumunu-sil kipinde ARTABİLİR ──
        # İlk sürümde bu tabloyu "yalnızca azalır" sayan gruba
        # koymuştum ve doğrulama tek firmalı sistemde HATA verdi:
        # silinen üyelik yoktu ama artık carileri kalan firmaya
        # bağlamak satır EKLİYOR. Sayı karşılaştırması bu tabloda
        # anlamsız; doğru ölçüt şu: her cari TAM BİR üyelikle kalan
        # firmada görünsün. O da aşağıda sayılıyor.
        if KIP == 'tumunu' and t == 'cari_firma':
            _cari_adet = simdi_korunan.get('cariler', 0)
            _yabanci = b.execute(text(
                'SELECT COUNT(*) FROM cari_firma WHERE firma_id <> :f'),
                {'f': KALAN_FIRMA['id']}).scalar() or 0
            if _yabanci:
                print(f"   ✗ cari_firma      silinmiş firmaya bakan "
                      f"{tr(_yabanci)} üyelik kaldı")
                hatali = True
            elif simdi != _cari_adet:
                print(f"   ✗ cari_firma      {tr(_cari_adet)} cari için "
                      f"{tr(simdi)} üyelik var (bire bir olmalı)")
                hatali = True
            else:
                print(f"   ✓ cari_firma     {tr(simdi):>7} üyelik — "
                      f"her cari kalan firmada görünüyor")
            continue

        # KF1: `kullanici_firma` da bu gruba girer. Korunan bir tablo
        # ama --tumunu-sil kipinde SİLİNEN firmalara bakan satırları
        # bilerek gidiyor; eşitlik beklemek, doğru çalışan silmeyi
        # HATA diye raporlamak olurdu. (cari_firma'da aynı tuzağa bir
        # kez düşmüştüm — orada sayı ARTABİLDİĞİ için.)
        if KIP == 'tumunu' and t in ('firma', 'kasa', 'banka', 'veriler',
                                     'kullanici_firma'):
            # Bu kipte bilerek azalıyorlar (silinen firmaların
            # satırları). Sayı eşitliği beklenmez; ARTMAMALARI ve
            # firma'nın 1'e inmesi beklenir.
            if t == 'firma' and simdi != 1:
                print(f"   ✗ firma: 1 firma beklenirken {simdi} var")
                hatali = True
            elif simdi > beklenen:
                print(f"   ✗ {t:<16s} artmış: {beklenen} → {simdi}")
                hatali = True
            else:
                _not = (f" (önce {tr(beklenen)}, silinen firmalarla azaldı)"
                        if simdi < beklenen else '')
                print(f"   ✓ {t:<16s} {tr(simdi):>7} kayıt{_not}")
            continue
        isaret = '✓' if simdi == beklenen else '✗'
        if simdi != beklenen:
            hatali = True
        print(f"   {isaret} {t:<16s} {tr(simdi):>7} kayıt korundu "
              f"(önce {tr(beklenen)})")

    # 4a · KF6 · firmasız kalan kullanıcı
    if KIP == 'tumunu' and 'kullanici_firma' in mevcut:
        _k2 = kilitlenecekler(b, [], KALAN_FIRMA['id'])
        if _k2:
            print(f"   ⚠ {len(_k2)} kullanıcı hiçbir firmada: "
                  f"{', '.join(_k2)}")
            print("     Giriş yapamazlar — Ayarlar → Kullanıcılar'dan")
            print("     firma ataması yapılmalı. (Hata değil, uyarı:")
            print("     sıfırlamanın beklenen sonucu olabilir.)")
        else:
            print("   ✓ her kullanıcı en az bir firmada çalışabiliyor")

    # 4 · Görünürlüğü kalmayan cari var mı?
    # Kartı olup hiçbir firmada listelenmeyen cari, "veri var ama
    # yok" durumudur; sessiz geçilmemeli.
    if 'cari_firma' in mevcut and 'cariler' in mevcut:
        _gorunmez = b.execute(text(
            'SELECT COUNT(*) FROM cariler c WHERE NOT EXISTS '
            '(SELECT 1 FROM cari_firma cf WHERE cf.cari_id = c.id)')).scalar() or 0
        if _gorunmez:
            print(f"   ⚠ {tr(_gorunmez)} cari hiçbir firmada görünmüyor")
            print("     (kart duruyor; Cari ekranında firma kutularından")
            print("      işaretleyerek geri getirebilirsin)")
        else:
            print("   ✓ her cari en az bir firmada görünüyor")

print()
print("═" * 70)
if hatali:
    print(" ✗ DOĞRULAMA BAŞARISIZ — yedekten dönmeyi değerlendirin.")
    sys.exit(1)
print(" ✓ SIFIRLAMA TAMAMLANDI")
print()
print(" Cari firma kayıtlarınız duruyor; hareketleri sıfırlandı.")
print(" Bakiyeler hareketlerden hesaplandığı için hepsi 0 görünür.")
print()
print(" SONRAKİ ADIMLAR:")
# Oturumdaki firma seçimi `session`'da duruyor. Silinen bir firma
# seçiliyse ekranlar boş/hatalı gelir; servisi yeniden başlatmak ve
# yeniden giriş yapmak seçimi tazeler.
print("   1) sudo systemctl restart milestone-erp")
print("      sonra çıkış yapıp yeniden giriş yap (firma seçimi tazelenir)")
# R4: KB1'den beri kasa/banka TANIMLARI korunuyor, yalnizca bakiye
# sifirlaniyor. Mesaj "yeniden tanimlayin" diyordu; yeniden tanimlamak
# mukerrer kasa acardi.
print("   2) Kasa açılış bakiyelerini girin (tanımlar duruyor)")
print("   3) Ayarlar → Listeler'i gözden geçirin")
print("   4) Sabit giderleri girin (kira, maaş, SGK...)")
print("   5) venv/bin/python degismezlik_denetim.py")
print("═" * 70)

#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — ÇEK KAPANIŞI  ·  CK2  (B adımı)
#
#  ── SORUN ──
#    Çekle tahsilatta sistem faturayı kapatan bir cari hareket açıyor
#    (alacak). Çek sonradan KARŞILIKSIZ çıkar ya da İADE edilirse
#    yalnızca çekin durumu değişiyor — cari hareket olduğu gibi
#    duruyor.
#
#    Ölçülen sonuç (50.000 TRY'lik fatura, çekle tahsil, sonra
#    karşılıksız):
#        fatura durumu      : Tahsil Edildi   ← edilmedi
#        cari net bakiye    : 0               ← müşteri 50.000 borçlu
#        açık risk          : 0               ← 50.000 risk açık
#        kullanılabilir limit: TAMAMI serbest ← en tehlikelisi
#
#    Yani karşılıksız çek veren müşteriye ertesi gün yeni yükleme
#    onaylanabiliyor.
#
#  ── MUHASEBE GEREKÇESİ ──
#    Çek bir ÖDEME VAADİDİR, ödemenin kendisi değil. Kapanma
#    şartlıdır; şart bozulunca alacak yeniden doğar. Tekdüzen hesap
#    planında da böyle işler: 101 Alınan Çekler → karşılıksızda
#    120 Alıcılar'a (şüpheli hale gelmişse 128'e) döner.
#
#  ── NE YAPIYOR ──
#    1) 'karsiliksiz' ve 'iade' dallarına TERS cari hareket ekler.
#       Alınan çekte borç (müşteri yine borçlu), verilen çekte
#       alacak (biz yine borçluyuz).
#    2) _fatura_odenen_esdeger() ölü çekleri ödeme saymasın —
#       yoksa fatura "Tahsil Edildi" kalır ve kalan bakiye 0
#       görünür.
#    3) Ölü çek durumlarını TEK YERDE tanımlar (CEK_OLU_DURUMLAR),
#       böylece nakit akışı ve fatura mantığı aynı listeyi kullanır.
#
#  ── NE YAPMIYOR ──
#    Nakit akışı projeksiyonunu DÜZELTMEZ. Bu yama muhasebe
#    katmanını onarır; nakit tarafı ayrı (NK1 yaması). Ters hareket
#    açılsa bile projeksiyon hâlâ faturayı ve çeki ayrı sayıyor.
#
#    GEÇMİŞ kayıtları da düzeltmez. Önce cek_kapanis_teshis.py
#    çalıştırın; etkilenen kayıt varsa ayrı düzeltme gerekir.
#
#  ── GERİ ALMA ──
#    'geri_al' dalı çeki portföye döndürüyor. Bu yamanın açtığı ters
#    hareket de o dalda siliniyor — yoksa geri alınan çek kalıcı
#    borç bırakırdı.
#
#  KULLANIM (proje klasöründe):
#      python yama_ck2_olu_cek.py            # rapor
#      python yama_ck2_olu_cek.py --uygula   # uygula
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


# ══ A) Ölü çek durumları + ters hareket yardımcısı ═════════════════
A_ESKI = """    def _fatura_odenen_esdeger(f):"""

A_YENI = '''    # Cekin OLDUGU durumlar: para hic gelmedi ya da geri gitti.
    # Nakit akisi ve fatura kapanis mantigi AYNI listeyi kullanmali,
    # yoksa iki farkli gercek ortaya cikar.
    CEK_OLU_DURUMLAR = ('Karsiliksiz', 'Iade Edildi', 'Iade Alindi')

    def _cek_ters_hareket_id(cek):
        """Bu cek icin acilmis ters hareketin kimligi (deterministik).

        Sabit kalip: ayni cek icin iki kez ters hareket acilmasini
        engeller ve 'geri_al' dalinda kaydi bulup silmeyi saglar.
        """
        return f'HX-{cek.id}'

    def _cek_olu_ters_hareket(cek, sebep):
        """Olen cek icin TERS cari hareket acar — alacagi geri getirir.

        Cek bir odeme VAADIDIR. Vaat bozulunca kapanma da bozulur:
        alinan cekte musteri yine borclu (borc), verilen cekte biz
        yine borcluyuz (alacak).

        Idempotent: ayni cek icin ikinci kez cagrilirsa yeni kayit
        acmaz.
        """
        if not cek.cari_id:
            # Cariye bagli olmayan cek — ters hareket acacak hesap yok.
            return None
        hid = _cek_ters_hareket_id(cek)
        if db.session.get(CariHareket, hid):
            return None

        tutar = q3(float(cek.tutar or 0))
        if tutar <= 0:
            return None
        doviz = (cek.doviz or 'TRY').upper()
        kur = _kur_getir(doviz) or 1.0
        try_karsilik = q3(tutar * kur) if doviz != 'TRY' else tutar
        alinan = (cek.yon == 'alinan')

        h = CariHareket(
            id=hid,
            hareket_tarihi=date.today(),
            cari_id=cek.cari_id,
            cari_unvan=cek.cari_unvan,
            islem_tip=f'Çek {sebep} — alacak iadesi',
            aciklama=f'{cek.cek_no or cek.id} nolu çek {sebep.lower()}',
            borc=tutar if alinan else 0,
            alacak=0 if alinan else tutar,
            borc_try=try_karsilik if alinan else 0,
            alacak_try=0 if alinan else try_karsilik,
            doviz=doviz,
            kur_uygulanan=kur,
            # Vade BUGUN: alacak artik muaccel, beklemede degil.
            vade_tarihi=date.today(),
            kaynak='cek_olu',
            baglanti_tip='cek',
            baglanti_id=cek.id,
            kullanici=session.get('kullanici'))
        db.session.add(h)
        return h

    def _fatura_odenen_esdeger(f):'''

# ══ B) Ölü çekler ödeme sayılmasın ═════════════════════════════════
B_ESKI = """        cek_hs = CariHareket.query.filter(
            CariHareket.baglanti_tip == 'cek', CariHareket.alacak > 0,
            CariHareket.baglanti_id.in_(
                db.session.query(Cek.id).filter_by(fatura_id=f.id))).all()"""

B_YENI = """        # OLU cekler odeme SAYILMAZ. Karsiliksiz cikan bir cek
        # faturayi kapatmis gibi durursa fatura "Tahsil Edildi"
        # kalir ve kalan bakiye 0 gorunur — para hic gelmedigi halde.
        cek_hs = CariHareket.query.filter(
            CariHareket.baglanti_tip == 'cek', CariHareket.alacak > 0,
            CariHareket.baglanti_id.in_(
                db.session.query(Cek.id).filter(
                    Cek.fatura_id == f.id,
                    db.or_(Cek.durum.is_(None),
                           Cek.durum.notin_(CEK_OLU_DURUMLAR))))).all()"""

# ══ C) Karşılıksız dalı ════════════════════════════════════════════
C_ESKI = """        elif islem == 'karsiliksiz':
            c.durum = 'Karsiliksiz'
            _cek_hareket_ekle(c, 'Karşılıksız', onceki, c.durum, d.get('aciklama', ''))
            mesaj = 'Çek karşılıksız olarak işaretlendi'"""

C_YENI = """        elif islem == 'karsiliksiz':
            c.durum = 'Karsiliksiz'
            _cek_hareket_ekle(c, 'Karşılıksız', onceki, c.durum, d.get('aciklama', ''))
            # Cek olduyse kapanma da bozulur: alacagi geri getir.
            _ters = _cek_olu_hareket_ve_fatura(c, 'karşılıksız')
            mesaj = 'Çek karşılıksız olarak işaretlendi'
            if _ters:
                mesaj += ' — cari hesaba borç yeniden yansıtıldı'"""

# ══ D) İade dalı ═══════════════════════════════════════════════════
D_ESKI = """        elif islem == 'iade':
            # Çeki iade et (müşteriye geri ver / tedarikçiden geri al)
            c.durum = 'Iade Edildi' if c.yon == 'alinan' else 'Iade Alindi'
            _cek_hareket_ekle(c, 'İade', onceki, c.durum, d.get('aciklama', ''))
            mesaj = 'Çek iade edildi'"""

D_YENI = """        elif islem == 'iade':
            # Çeki iade et (müşteriye geri ver / tedarikçiden geri al)
            c.durum = 'Iade Edildi' if c.yon == 'alinan' else 'Iade Alindi'
            _cek_hareket_ekle(c, 'İade', onceki, c.durum, d.get('aciklama', ''))
            # Iade edilen cek de odeme saglamaz — alacak geri doner.
            _ters = _cek_olu_hareket_ve_fatura(c, 'iade edildi')
            mesaj = 'Çek iade edildi'
            if _ters:
                mesaj += ' — cari hesaba borç yeniden yansıtıldı'"""

# ══ E) Geri alma: ters hareketi de temizle ═════════════════════════
E_ESKI = """        elif islem == 'geri_al':
            # Önceki duruma döndür (portföye geri al) + yan etkileri geri al
            geri_mesaj = ''"""

E_YENI = """        elif islem == 'geri_al':
            # Önceki duruma döndür (portföye geri al) + yan etkileri geri al
            geri_mesaj = ''
            # 0) Olu cek ters hareketini SIL. Yoksa portfoye geri
            #    alinan cek cari hesapta kalici borc birakirdi.
            _tx = db.session.get(CariHareket, _cek_ters_hareket_id(c))
            if _tx:
                db.session.delete(_tx)
                geri_mesaj += ' Alacak iadesi kaydı kaldırıldı.'
            # Fatura durumu BURADA tazelenmez: cekin durumu henuz
            # 'Karsiliksiz'. Once portfoye donmesi, sonra tazelenmesi
            # gerekiyor — bkz. asagidaki blok."""

# ══ G) Geri almada fatura durumu — SIRA ÖNEMLİ ═════════════════════
#  Fatura tazelemesi, cekin durumu 'Portfoyde'ye DONDUKTEN SONRA
#  yapilmali. Once yapilirsa cek hala 'Karsiliksiz' gorunur, olu
#  sayilir ve fatura "Tahsil Edildi"e geri donmez.
G_ESKI = """            c.durum = 'Portfoyde' if c.yon == 'alinan' else 'Verildi'
            c.tahsil_banka_id = None"""

G_YENI = """            c.durum = 'Portfoyde' if c.yon == 'alinan' else 'Verildi'
            c.tahsil_banka_id = None
            # Cek yeniden GECERLI: fatura durumunu simdi tazele.
            # Sira onemli — bu satirlar durum sifirlandiktan sonra.
            try:
                if getattr(c, 'fatura_id', None):
                    db.session.flush()
                    _fatura_tahsilat_durumu(c.fatura_id)
            except Exception:
                pass"""


BLOKLAR = [
    ("ölü çek listesi + ters hareket yardımcısı", A_ESKI, A_YENI, 'CEK_OLU_DURUMLAR = ('),
    ("ölü çek ödeme sayılmasın",                  B_ESKI, B_YENI, 'Cek.durum.notin_(CEK_OLU_DURUMLAR)'),
    ("karşılıksız dalı",                          C_ESKI, C_YENI, "_cek_olu_hareket_ve_fatura(c, 'karşılıksız')"),
    ("iade dalı",                                 D_ESKI, D_YENI, "_cek_olu_hareket_ve_fatura(c, 'iade edildi')"),
    ("geri alma temizliği",                       E_ESKI, E_YENI, 'Alacak iadesi kaydı kaldırıldı'),
    ("geri almada fatura tazeleme (sıra)",        G_ESKI, G_YENI, 'Cek yeniden GECERLI: fatura durumunu simdi tazele'),
]

# ══ F) Sarmalayıcı: ters hareket + fatura durumu birlikte ══════════
F_ESKI = """    def _fatura_odenen_esdeger(f):"""

F_YENI = '''    def _cek_olu_hareket_ve_fatura(cek, sebep):
        """Ters hareketi acar ve bagli faturanin durumunu tazeler.

        Ikisi BIRLIKTE olmali: ters hareket cari bakiyeyi duzeltir,
        fatura durumu tazelemesi de faturayi "Tahsil Edildi"
        olmaktan cikarir. Biri yapilip oteki atlanirsa yine iki
        celiskili gercek olusur.
        """
        h = _cek_olu_ters_hareket(cek, sebep)
        try:
            if getattr(cek, 'fatura_id', None):
                db.session.flush()
                _fatura_tahsilat_durumu(cek.fatura_id)
        except Exception:
            pass
        return h

    def _fatura_odenen_esdeger(f):'''

print("═" * 70)
print(" CK2 · ÖLÜ ÇEK — alacağı geri getir  (B adımı)")
print("═" * 70)
print()

ham = APP.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


icerik = ham
plan, atlanan, sorunlu = [], [], []

# A ve F ayni capaya (F_ESKI == A_ESKI) yaziyor; once A, sonra F.
for aciklama, eski, yeni, imza in BLOKLAR + [
        ("ters hareket + fatura sarmalayıcısı", F_ESKI, F_YENI,
         'def _cek_olu_hareket_ve_fatura(')]:
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

hata = dogrula(icerik)
if hata:
    print(f" ✗ SÖZDİZİMİ HATASI → {hata}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)
print(" ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_ck2_olu_cek.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = APP.with_name(f'flask_app.py.yedek-{damga}')
shutil.copy2(APP, yedek)
APP.write_bytes(icerik.encode('utf-8'))
print(f" ✓ flask_app.py  (yedek: {yedek.name})")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI  (B adımı)")
print()
print(" Karşılıksız / iade edilen çek artık cari hesaba borcu")
print(" geri yansıtıyor, fatura durumu tazeleniyor.")
print()
print(" ⚠ NAKİT AKIŞI HÂLÂ YANLIŞ — sıradaki: yama_nk1_nakit_zincir.py")
print("═" * 70)

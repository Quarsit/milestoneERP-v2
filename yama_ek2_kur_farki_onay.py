#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — KUR FARKI AÇIK ONAY İSTER  ·  EK2
#
#  ── ÖLÇÜLEN DURUM ──
#    `_kur_farki_hesapla_ve_olustur()` iki yerden KOŞULSUZ cagriliyor:
#      · api_hareket_ekle      (her tahsilat/odeme sonrasi)
#      · api_fatura_tahsilat   (her fatura tahsilatinda)
#
#    Kullanici hicbir sey isaretlemeden cari hesabina kayit
#    dusuyor. Olculdu: 10.000 USD fatura (kur 40) → 10.000 USD
#    tahsilat (kur 46,8) sonrasi 1 adet 'Kur Farki (Borc)' kaydi
#    OTOMATIK olustu. Kodda `kur_farki_islet` benzeri HICBIR
#    secenek yok.
#
#  ── KULLANICI KURALI ──
#    "Kullanici acikca kur farki kaydi olusturulmasini istemedigi
#     surece sistem otomatik kur farki kaydi olusturmamalidir."
#
#    Ayrica: ekstrede BILGI AMACLI gostermek ile cari hesaba
#    ISLEMEK ayri seylerdir. Gostermek serbest, islemek onay ister.
#
#  ── DÜZELTME ──
#    Istekte `kur_farki_islet: true` YOKSA kayit olusturulmaz.
#    Varsayilan KAPALI: bir muhasebe kaydini sessizce olusturmak,
#    olusturmamaktan daha zararlidir — sonradan fark edilmesi zor,
#    geri alinmasi zahmetlidir.
#
#  ── HESAP DEVAM EDER, KAYIT DURUR ──
#    Fonksiyon hesabi yine yapar ve sonucu DONER; yalnizca
#    veritabanina YAZMAZ. Boylece cagiran taraf "su kadar kur
#    farki olusurdu" bilgisini kullaniciya gosterebilir.
#
#  ── MEVCUT KAYITLAR ──
#    Bu yama gecmiste olusmus kayitlara DOKUNMAZ. Onlari gormek
#    icin:
#        SELECT * FROM cari_hareket WHERE kaynak='otomatik_kur_farki';
#    Silmek isterseniz once listeleyip karar verin; bu yama karar
#    vermez.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python yama_ek2_kur_farki_onay.py            # rapor
#      venv/bin/python yama_ek2_kur_farki_onay.py --uygula
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

_h = APP.read_text(encoding='utf-8', errors='replace')
if '_kur_farki_hesapla_ve_olustur' not in _h:
    print("✗ Kur farkı fonksiyonu bulunamadı — beklenmedik sürüm.")
    sys.exit(1)

# ── A) Fonksiyon imzasına onay parametresi ─────────────────────────
A_ESKI = """    def _kur_farki_hesapla_ve_olustur(yeni_hareket):
        \"\"\"
        Tahsilat/odeme hareketi olusturulduktan sonra cagrilir.
        Ayni cari + ayni doviz icin kapanmamis (en eski) borc/alacak hareketini bulur,
        kur farkini hesaplar, otomatik 'Kur Farki' hareketi acar.
        \"\"\""""

A_YENI = '''    def _kur_farki_hesapla_ve_olustur(yeni_hareket, islet=False):
        """
        Tahsilat/odeme hareketi olusturulduktan sonra cagrilir.
        Ayni cari icin kapanmamis (en eski) borc/alacak hareketini bulur
        ve kur farkini HESAPLAR.

        ── AÇIK ONAY (EK2) ──
        `islet=False` (VARSAYILAN) ise hesap yapilir ama KAYIT
        OLUSTURULMAZ; sonuc yalnizca doner.

        Onceden kosulsuz kayit aciliyordu: kullanici hicbir sey
        isaretlemeden cari hesabina 'Kur Farki' hareketi dusuyordu.
        Bir muhasebe kaydini sessizce olusturmak, olusturmamaktan
        daha zararlidir — sonradan fark edilmesi zor, geri alinmasi
        zahmetlidir.

        Cagiran taraf `islet=True` gecerse kayit olusur.
        """'''

# ── B) Kayıt oluşturmadan önce onay kontrolü ───────────────────────
B_ESKI = """        kf_hareket = CariHareket("""

B_YENI = """        # ── AÇIK ONAY YOKSA KAYIT YOK (EK2) ──
        # Hesap yapildi; kullanici istemediyse yalnizca BILGI olarak
        # donuyoruz. Ekstrede gostermek serbest, cari hesaba islemek
        # onay ister — ikisi ayri seydir.
        # Degisken adi `fark` (fark_try DEGIL) — ilk surumde yanlis
        # ad kullanilmis ve NameError uretmisti; gercek uc noktayla
        # test ederken yakalandi.
        if not islet:
            return {'islendi': False, 'tutar': q3(abs(fark)),
                    'islem_tip': kf_islem,
                    'mesaj': f'{q3(abs(fark))} TRY kur farkı hesaplandı '
                             f'(kayıt OLUŞTURULMADI — işlemek için '
                             f'"kur farkı işlet" seçeneğini kullanın)'}

        kf_hareket = CariHareket("""

# ── C) Çağrı noktaları: istekten onay oku ──────────────────────────
# Gercek cagri bicimi: `kur_farki = _kur_farki_hesapla_ve_olustur(hareket)`
# Girinti IKI cagride farkli (12 ve 8 bosluk), o yuzden girintisiz
# eslesme kullanilip sonuc adi korunuyor.
C_ESKI = """kur_farki = _kur_farki_hesapla_ve_olustur(hareket)"""
C_YENI = """kur_farki = _kur_farki_hesapla_ve_olustur(
                hareket, islet=bool((request.json or {}).get('kur_farki_islet')))"""

# ── D) Cagiran taraf SOZLUK donusunu de anlasin ──
# api_hareket_ekle donen degeri NESNE sanip `.islem_tip`, `.borc`,
# `.id` okuyordu. Onaysiz durumda artik SOZLUK donuyor ve
# AttributeError uretiyordu — gercek uc noktayla test ederken
# yakalandi.
D_ESKI = """        if kur_farki:
            msg += f', otomatik kur farki kaydedildi ({kur_farki.islem_tip}: {kur_farki.borc + kur_farki.alacak:,.2f} TRY)'
        return jsonify({'ok': True, 'id': hareket.id, 'fatura_id': fatura_id,
                       'kur_farki_id': kur_farki.id if kur_farki else None,
                       'mesaj': msg})"""

D_YENI = """        # EK2: onaysiz durumda SOZLUK doner (kayit olusmadi),
        # onayli durumda CariHareket NESNESI doner.
        _kf_bilgi = None
        if isinstance(kur_farki, dict):
            # Kayit OLUSMADI — yalnizca bilgi.
            _kf_bilgi = kur_farki
            msg += f", {kur_farki.get('mesaj', '')}"
        elif kur_farki:
            msg += (f', kur farki kaydedildi ({kur_farki.islem_tip}: '
                    f'{kur_farki.borc + kur_farki.alacak:,.2f} TRY)')
        return jsonify({'ok': True, 'id': hareket.id, 'fatura_id': fatura_id,
                       'kur_farki_id': (kur_farki.id
                                        if kur_farki and not isinstance(kur_farki, dict)
                                        else None),
                       'kur_farki_bilgi': _kf_bilgi,
                       'mesaj': msg})"""

BLOKLAR = [
    ("fonksiyon imzası (islet)",   A_ESKI, A_YENI, 'def _kur_farki_hesapla_ve_olustur(yeni_hareket, islet=False)'),
    ("onay yoksa kayıt yok",       B_ESKI, B_YENI, '# ── AÇIK ONAY YOKSA KAYIT YOK (EK2) ──'),
    ("çağıran sözlüğü anlasın",    D_ESKI, D_YENI, '_kf_bilgi = None'),
]

print("═" * 70)
print(" EK2 · KUR FARKI AÇIK ONAY İSTER")
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

# ── Çağrı noktaları ──
# İki yerden çağrılıyor; ikisi de istekten onay okumalı.
# Imza C_YENI'nin urettigi metinden: `islet=bool((request.json`
if uyarla("islet=bool((request.json") in icerik:
    atlanan.append("çağrı noktaları")
else:
    _c = uyarla(C_ESKI)
    _n = icerik.count(_c)
    if _n < 1:
        sorunlu.append(("çağrı noktaları", _n))
    else:
        icerik = icerik.replace(_c, uyarla(C_YENI))
        plan.append(f"çağrı noktaları ({_n} yer)")

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
    print("   venv/bin/python yama_ek2_kur_farki_onay.py --uygula")
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
print(" Geçmişte oluşmuş kayıtlara DOKUNULMADI. Görmek için:")
print("   SELECT * FROM cari_hareket WHERE kaynak='otomatik_kur_farki';")
print("═" * 70)

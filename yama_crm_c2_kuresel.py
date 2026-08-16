#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — KÜRESEL SATIR SÜZGECİ  ·  CRM-C2
#
#  ── ÖN KOŞUL ──
#      yama_crm_c_erisim.py --uygula
#      Tüm carilere sorumlu atanmış olmalı.
#
#  ── NEDEN KÜRESEL ──
#    crm_erisim_denetim.py ölçtü: 122 uç nokta müşteri verisine
#    dokunuyor, 58'i süzgeçsiz OKUMA. Hepsini elle düzenlemek
#    haftalar sürer ve BİRİ atlanırsa sızıntı olur — üstelik siz
#    kapalı sandığınız için fark etmezsiniz.
#
#    Bunun yerine SQLAlchemy'nin `do_orm_execute` olayı: süzgeç TÜM
#    SELECT sorgularına tek yerden uygulanır. İleride eklenecek uç
#    noktalar da kendiliğinden kapsanır.
#
#  ── LAMBDA TUZAĞI (ölçüldü) ──
#    `with_loader_criteria`'ya lambda vermek YANLIŞ sonuç üretiyor:
#    SQLAlchemy lambdaları KOD NESNESİNE göre önbelleğe alıyor ve
#    bir döngüde aynı satırdan üretilen iki lambda birbirine
#    karışıyor. Prototipte fatura listesi 2 yerine 0 dönüyordu —
#    yani sessizce fazla süzüyordu. Bu yüzden DÜZ İFADE kullanılıyor.
#
#  ── YALNIZCA OKUMA ──
#    `do_orm_execute` SELECT'leri süzer. YAZMA (UPDATE/DELETE)
#    korunmaz: kimliği bilen biri başkasının müşterisini
#    güncelleyebilir. Yazma uçlarında AYRICA `_cari_gorulebilir_mi()`
#    kontrolü gerekir; crm_erisim_denetim.py bunları ayrı bölümde
#    listeliyor. Bunu gizlemiyorum — kapsam buraya kadar.
#
#  ── SİSTEM İŞLEMLERİ ──
#    Fatura keserken cariyi arayan iç sorgu, kur güncelleme, denetim
#    betikleri süzülmemeli. Tek ve açık kapı: `erisim_atla()` bağlam
#    yöneticisi. Her kullanımı gerekçesiyle yazılmalı.
#
#  ── cari_id BOŞ KAYITLAR ──
#    Bağsız kayıtlar admin dışında GİZLENİR. Güvenli taraf: bağı
#    olmayan kaydı herkese açmak, kapalı bir müşterinin belgesini
#    sızdırabilirdi. Bu kayıtları bulmak için crm_bag_denetim.py.
#
#  KULLANIM (proje klasöründe):
#      python yama_crm_c2_kuresel.py            # rapor
#      python yama_crm_c2_kuresel.py --uygula
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
if '_gorulebilir_cari_idler' not in _h:
    print("✗ ÖN KOŞUL: önce yama_crm_c_erisim.py uygulanmalı.")
    sys.exit(1)

# ── A0) Eksik flask importlari ─────────────────────────────────────
#  Kuresel suzgec `g` (istek kapsamli onbellek) ve
#  `has_request_context` (CLI/gorev ayrimi) kullaniyor; ikisi de
#  import edilmemisti. Yamanin kendi korumasi bunu yakaladi.
A0_ESKI = """from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file"""
A0_YENI = """from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file
from flask import g, has_request_context   # CRM-C2: kuresel erisim suzgeci"""

ESKI = """    # ---------- API: CARİ VE HAREKETLER ----------"""

YENI = '''    # ══════════════════════════════════════════════════════════
    #  KÜRESEL SATIR SÜZGECİ  (CRM-C2)
    #
    #  Suzgec TUM SELECT sorgularina tek yerden uygulanir. 122 uc
    #  noktayi elle duzenlemek yerine ORM katmaninda; ileride
    #  eklenecek uc noktalar da kendiliginden kapsanir.
    # ══════════════════════════════════════════════════════════

    from contextlib import contextmanager as _contextmanager

    from sqlalchemy import event as _sa_event, false as _sa_false
    from sqlalchemy.orm import Session as _SaSession
    from sqlalchemy.orm import with_loader_criteria as _wlc

    # (model, musteri kimligini tutan sutun adi)
    ERISIM_MODELLERI = [
        (Cari, 'id'), (Proforma, 'cari_id'), (Fatura, 'cari_id'),
        (SatisKaydi, 'cari_id'), (Sevkiyat, 'cari_id'),
        (Rezervasyon, 'cari_id'), (CariHareket, 'cari_id'),
        (Cek, 'cari_id'), (Siparis, 'cari_id'),
    ]

    @_contextmanager
    def erisim_atla():
        """Suzgeci GECICI olarak kapatir — SISTEM islemleri icin.

        Fatura keserken cariyi arayan ic sorgu, kur guncelleme,
        toplu islemler ve denetim betikleri suzulmemeli; aksi halde
        sistem kendi isini goremez.

        Tek ve acik kapi olmasi kasitli: dagilirsa suzgec sessizce
        devre disi kalir. Her kullanimi GEREKCESIYLE yazilmali.
        """
        onceki = getattr(g, 'erisim_atla_bayrak', False)
        g.erisim_atla_bayrak = True
        try:
            yield
        finally:
            g.erisim_atla_bayrak = onceki

    @_sa_event.listens_for(_SaSession, 'do_orm_execute')
    def _erisim_suzgeci(durum):
        # Yalnizca ust duzey SELECT. Sutun/iliski yuklemeleri zaten
        # suzulmus bir kayittan gelir; tekrar suzmek gereksiz ve
        # bazi durumlarda hatali olur.
        if not durum.is_select or durum.is_column_load or durum.is_relationship_load:
            return
        if not has_request_context():
            return                      # CLI, gorev, denetim betigi
        if getattr(g, 'erisim_atla_bayrak', False):
            return                      # sistem islemi
        if (session.get('rol') or '').upper() == 'ADMIN':
            return                      # admin her seyi gorur
        ben = session.get('kullanici')
        if not ben:
            return                      # oturum yok; _auth_required zaten engeller

        izin = getattr(g, 'erisim_izin', None)
        if izin is None:
            # Izin listesini hesaplarken SUZGEC KAPALI olmali,
            # yoksa kendini sorgulayip ozyinelemeye girer.
            g.erisim_atla_bayrak = True
            try:
                izin = {c.id for c in
                        Cari.query.filter(Cari.gorunurluk == 'ortak').all()}
                izin |= {c.id for c in Cari.query.filter(Cari.sorumlu == ben).all()}
                izin |= {e.cari_id for e in
                         CariErisim.query.filter_by(kullanici=ben).all()}
            finally:
                g.erisim_atla_bayrak = False
            g.erisim_izin = izin

        idler = list(izin)
        for _model, _sutun in ERISIM_MODELLERI:
            # DUZ IFADE — lambda DEGIL.
            # with_loader_criteria lambdalari KOD NESNESINE gore
            # onbellekliyor; bir dongude ayni satirdan uretilen iki
            # lambda birbirine karisiyor ve suzgec yanlis modele
            # uygulaniyor. Olculdu: fatura listesi 2 yerine 0
            # donuyordu (sessizce fazla suzme).
            _kosul = (getattr(_model, _sutun).in_(idler) if idler
                      else _sa_false())
            durum.statement = durum.statement.options(
                _wlc(_model, _kosul, include_aliases=True))

    # ---------- API: CARİ VE HAREKETLER ----------'''

IMZA = 'def _erisim_suzgeci('

print("═" * 70)
print(" CRM-C2 · KÜRESEL SATIR SÜZGECİ")
print("═" * 70)
print()

ham = APP.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


if uyarla(IMZA) in ham or IMZA in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

icerik = ham
for _ad, _e, _y in (("flask importları", A0_ESKI, A0_YENI),
                    ("küresel süzgeç", ESKI, YENI)):
    _ee = uyarla(_e)
    if _ee not in icerik:
        print(f" ✗ KALIP BULUNAMADI: {_ad}. DOSYAYA DOKUNULMADI.")
        sys.exit(1)
    if icerik.count(_ee) != 1:
        print(f" ✗ {_ad} kalıbı {icerik.count(_ee)} kez bulundu. DOSYAYA DOKUNULMADI.")
        sys.exit(1)
    icerik = icerik.replace(_ee, uyarla(_y), 1)

try:
    compile(icerik, 'flask_app.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

# has_request_context / g kullaniliyor mu, import edilmis mi?
for _ad in ('has_request_context', 'import g,', 'from flask import'):
    if _ad not in icerik:
        print(f" ✗ Gerekli import eksik görünüyor: {_ad}")
        print(" DOSYAYA DOKUNULMADI.")
        sys.exit(1)

print("  ✓ uygulanacak          küresel süzgeç (9 model)")
print("  ✓ uygulanacak          erisim_atla() sistem kapısı")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_crm_c2_kuresel.py --uygula")
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
print(" ⚠ SÜZGEÇ YALNIZCA OKUMAYI kapsar. Yazma uçlarında ayrıca")
print("   _cari_gorulebilir_mi() kontrolü gerekir:")
print("     venv/bin/python crm_erisim_denetim.py")
print("═" * 70)

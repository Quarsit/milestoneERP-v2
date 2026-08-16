#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — ERİŞİM SÜZGECİ  ·  CRM-C
#
#  ── ÖN KOŞUL ──
#      yama_crm_b_sahiplik.py + yama_crm_b2_api.py + goc.py uygula
#
#  ── KURAL ──
#    Bir kullanici su musterileri gorur:
#      · rol ADMIN                       → HEPSI
#      · gorunurluk = 'ortak'            → herkes gorur
#      · gorunurluk = 'kapali'           → yalnizca sorumlusu
#      · CariErisim'de kaydi olan        → o musteriyi de gorur
#
#  ── NEDEN TEK FONKSİYON ──
#    Kural 55+ uc noktada tekrarlanacak. Her birine elle yazmak,
#    birinin farkli yazilmasi ve sessizce sizinti demek. Tek
#    fonksiyon (`_gorulebilir_cari_idler`) + tek suzgec yardimcisi
#    (`_cari_suz`) kullaniliyor; hepsi ayni kurala uyuyor.
#
#  ── EKSİK KAPSAM SESSİZ KALMAZ ──
#    Bu yama cekirdek cari uc noktalarini kapatir. Kalanlar icin
#    `crm_erisim_denetim.py` yazildi: musteri verisi donduren ama
#    suzgec uygulamayan her uc noktayi listeler. Yarim uygulanmis
#    satir guvenligi, hic olmamasindan KOTUDUR — cunku kapali
#    sanirsiniz. Denetim araci bu yuzden isin parcasi.
#
#  ── GORUNURLUK NULL ISE ──
#    Eski kayitlarda NULL olabilir; GUVENLI taraf olan 'kapali'
#    sayilir. Bos deger "herkes gorsun" anlamina gelmemeli.
#
#  KULLANIM (proje klasöründe):
#      python yama_crm_c_erisim.py            # rapor
#      python yama_crm_c_erisim.py --uygula
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
if "'gorunurluk': c.gorunurluk or 'kapali'}" not in _h:
    print("✗ ÖN KOŞUL: önce yama_crm_b2_api.py uygulanmalı.")
    sys.exit(1)

# ── A0) Yeni modelleri içeri al ────────────────────────────────────
#  CRM-B tablolari models.py'de tanimlandi ama flask_app.py'ye
#  import EDILMEMISTI. Erisim motoru CariErisim'i kullandigi anda
#  NameError ile cokuyordu — ilk surumde bu atlandi, test yakaladi.
A0_ESKI = """from models import Cek, CekHareket"""
A0_YENI = """from models import Cek, CekHareket
from models import CariErisim, CariKisi   # CRM-B: erisim ve kisiler"""

# ── A) Erişim motoru ───────────────────────────────────────────────
A_ESKI = """    # ---------- API: CARİ VE HAREKETLER ----------"""

A_YENI = '''    # ══════════════════════════════════════════════════════════
    #  MÜŞTERİ ERİŞİM SÜZGECİ  (CRM-C)
    #
    #  Kural TEK YERDE. 55+ uc noktada tekrarlansaydi birinin farkli
    #  yazilmasi sessiz sizinti demekti.
    # ══════════════════════════════════════════════════════════

    def _erisim_admin_mi():
        return (session.get('rol') or '').upper() == 'ADMIN'

    def _gorulebilir_cari_idler():
        """Gecerli kullanicinin gorebilecegi cari kimlikleri.

        None donerse SINIRLAMA YOK (admin) — cagiran bunu boyle
        yorumlamali. Bos KUME donerse hicbir musteri gorunmez;
        ikisi FARKLI seydir ve karistirilmasi ya her seyi acar ya
        her seyi kapatir.
        """
        if _erisim_admin_mi():
            return None
        ben = session.get('kullanici')
        idler = set()
        # 'ortak' olanlar herkese acik. gorunurluk NULL ise GUVENLI
        # taraf 'kapali' sayilir — bos deger "herkes gorsun"
        # anlamina gelmemeli.
        for c in Cari.query.filter(Cari.gorunurluk == 'ortak').all():
            idler.add(c.id)
        if ben:
            for c in Cari.query.filter(Cari.sorumlu == ben).all():
                idler.add(c.id)
            for e in CariErisim.query.filter_by(kullanici=ben).all():
                idler.add(e.cari_id)
        return idler

    def _cari_gorulebilir_mi(cari_id):
        """Tek bir musteri icin erisim kontrolu."""
        izin = _gorulebilir_cari_idler()
        return izin is None or (cari_id in izin)

    def _cari_suz(sorgu, sutun):
        """Sorguya erisim suzgecini uygular.

        `sutun` musteri kimligini tutan model sutunu (Cari.id,
        Proforma.cari_id ...). Admin'de sorgu degismeden doner.
        """
        izin = _gorulebilir_cari_idler()
        if izin is None:
            return sorgu
        if not izin:
            # Hicbir musteri yok: bos sonuc. `in_([])` bazi
            # surumlerde uyari uretir, acikca yanlis kosul veriyoruz.
            return sorgu.filter(db.false())
        return sorgu.filter(sutun.in_(list(izin)))

    # ---------- API: CARİ VE HAREKETLER ----------'''

# ── B) Cari listesine süzgeç ───────────────────────────────────────
B_ESKI = """        query = Cari.query.order_by(Cari.unvan)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)"""
B_YENI = """        # ERISIM SUZGECI (CRM-C) — admin'de sorgu degismez.
        query = _cari_suz(Cari.query, Cari.id).order_by(Cari.unvan)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)"""

BLOKLAR = [
    ("CariErisim/CariKisi import",  A0_ESKI, A0_YENI, 'from models import CariErisim'),
    ("erişim motoru",        A_ESKI, A_YENI, 'def _gorulebilir_cari_idler('),
    ("cari listesi süzgeci", B_ESKI, B_YENI, '_cari_suz(Cari.query, Cari.id)'),
]

print("═" * 70)
print(" CRM-C · MÜŞTERİ ERİŞİM SÜZGECİ")
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
    print("   python yama_crm_c_erisim.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = APP.with_name(f'flask_app.py.yedek-{damga}')
shutil.copy2(APP, yedek)
APP.write_bytes(icerik.encode('utf-8'))
print()
print(f" ✓ flask_app.py  (yedek: {yedek.name})")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI  (çekirdek)")
print()
print(" ⚠ KAPSAM HENÜZ TAM DEĞİL. Kalan uç noktaları görmek için:")
print("     venv/bin/python crm_erisim_denetim.py")
print("═" * 70)

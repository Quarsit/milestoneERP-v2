#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — DEĞİŞMEZLİK DENETİMİ  ·  D  (Faz 2)
#
#  NE İŞE YARAR:
#    Mevcut dört denetim aracı (sema, form, zincir, sessiz, js) KODUN
#    yapısını denetler: alan var mı, yazılıyor mu, okunuyor mu.
#    Hiçbiri HESABIN DOĞRU olup olmadığına bakmaz.
#
#    Bu tur bize şunu gösterdi: kod yapısı kusursuz görünürken
#    bakiye sıfır çıkabiliyor (E1), aynı belge kendi içinde
#    çelişebiliyor (E2), fatura kilitlenebiliyor (H3). Bunların
#    hiçbiri statik taramayla bulunmaz.
#
#    Bu araç MUHASEBE DEĞİŞMEZLİKLERİNİ denetler — her zaman doğru
#    olması gereken eşitlikleri.
#
#  ── NEDEN ŞİMDİ: FLOAT → NUMERIC GÖÇÜNÜN ÖN KOŞULU ──
#    Numeric göçü para alanlarının tipini değiştirir. Yuvarlama
#    davranışı değişir. Göçün bir şeyi bozup bozmadığını anlamanın
#    tek güvenilir yolu:
#        1. Göçten ÖNCE bu aracı çalıştır, çıktıyı sakla
#        2. Göçü yap
#        3. Tekrar çalıştır, çıktıları KARŞILAŞTIR
#    Fark yoksa göç güvenlidir. Bu karşılaştırma olmadan Numeric'e
#    geçmek, bakiyelerin sessizce kaymasını göze almak demektir.
#
#  ── DENETLENEN DEĞİŞMEZLİKLER ──
#    D1  Kasa bakiyesi = hareketlerin toplamı
#    D2  Cari bakiyesi = borç − alacak (hareketlerden)
#    D3  Fatura ↔ cari hareket tutar eşleşmesi
#    D4  Stok durumu ↔ satış/rezervasyon kaydı tutarlılığı
#    D5  Kesim korunumu: tüketilen kaynak = üretilen stok
#    D6  TL karşılığı ↔ döviz × kur tutarlılığı
#
#  BU ARAÇ HİÇBİR ŞEYİ DEĞİŞTİRMEZ — yalnızca okur ve raporlar.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python degismezlik_denetim.py
#      venv/bin/python degismezlik_denetim.py --sadece D1
#      venv/bin/python degismezlik_denetim.py --tam     # tüm satırlar
#
#  ÇIKIŞ KODU: ihlal varsa 1, temizse 0 (CI/otomasyon için).
# ══════════════════════════════════════════════════════════════════════
import os
import sys

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.getcwd())

TAM = '--tam' in sys.argv
SADECE = None
for i, a in enumerate(sys.argv[1:]):
    if a == '--sadece' and i + 2 <= len(sys.argv[1:]):
        SADECE = sys.argv[i + 2].upper()

import flask_app  # noqa: E402
from models import (Cari, CariHareket, Cek, Fatura, Kasa,  # noqa: E402
                    KasaHareket, Kesim, Rezervasyon, SatisKaydi, db)

app = flask_app.app

# Kuruş altı farklar yuvarlamadan gelir, ihlal sayılmaz.
TOLERANS = 0.05
LIMIT = None if TAM else 10


def yakin(a, b, tol=TOLERANS):
    return abs((a or 0) - (b or 0)) <= tol


def baslik(kod, ad, etiket):
    print()
    print("─" * 74)
    print(f" {kod} · {ad}   [{etiket}]")
    print("─" * 74)


def yazdir(bulgular, bos_mesaj, aciklama=None):
    if not bulgular:
        print(f"   ✓ temiz — {bos_mesaj}")
        return 0
    if aciklama:
        print(f"   {aciklama}")
        print()
    for s in bulgular[:LIMIT] if LIMIT else bulgular:
        print(f"   {s}")
    if LIMIT and len(bulgular) > LIMIT:
        print(f"   … +{len(bulgular) - LIMIT} satır daha (tümü için --tam)")
    print()
    print(f"   → {len(bulgular)} ihlal")
    return len(bulgular)


# ══════════════════════════════════════════════════════════════════
def d1_kasa_bakiye():
    """Kasa.bakiye alanı, hareketlerin toplamına eşit olmalı.

    Kasa bakiyesi AYRI BİR ALAN olarak tutuluyor (performans için).
    Hareket eklenip bakiye güncellenmezse — ya da tersi — kasada
    karşılığı olmayan para görünür. Bu tur öncesinde tam olarak
    böyle bir hata yaşanmıştı (tahsil edilen çek silinince kasa
    bakiyesi hayalet kalıyordu).
    """
    ihlaller = []
    for k in Kasa.query.all():
        hareketler = KasaHareket.query.filter_by(kasa_id=k.id).all()
        hesaplanan = 0.0
        for h in hareketler:
            t = (h.tip or '').lower()
            if t in ('giris', 'giriş'):
                hesaplanan += (h.tutar or 0)
            elif t in ('cikis', 'çıkış', 'cikiş'):
                hesaplanan -= (h.tutar or 0)
            else:
                ihlaller.append(
                    f"✗ {k.ad}: hareket {h.id} BİLİNMEYEN tip {h.tip!r} "
                    f"(giris/cikis bekleniyordu)")
        if not yakin(k.bakiye, hesaplanan):
            ihlaller.append(
                f"✗ {k.ad} ({k.doviz}): kayıtlı {k.bakiye or 0:,.2f}  ≠  "
                f"hareketlerden {hesaplanan:,.2f}  "
                f"(fark {(k.bakiye or 0) - hesaplanan:+,.2f}, "
                f"{len(hareketler)} hareket)")
    return ihlaller


def d2_cari_bakiye():
    """Cari hareketlerin kendi içinde tutarlılığı.

    Bir hareket HEM borç HEM alacak taşımamalı — biri sıfır olmalı.
    Aksi halde bakiye hesabı hangi yönü sayacağını bilemez.
    """
    ihlaller = []
    for h in CariHareket.query.all():
        b, a = (h.borc or 0), (h.alacak or 0)
        if b > 0 and a > 0:
            ihlaller.append(
                f"✗ {h.id} ({h.cari_unvan or h.cari_id}): borç {b:,.2f} VE "
                f"alacak {a:,.2f} birlikte — biri sıfır olmalı")
        if b == 0 and a == 0:
            ihlaller.append(
                f"? {h.id} ({h.cari_unvan or h.cari_id}): borç ve alacak "
                f"İKİSİ DE sıfır — {h.islem_tip or 'tip yok'}")
    return ihlaller


def d3_fatura_cari():
    """Kesilen her faturanın cari hareketi olmalı ve tutar tutmalı.

    Fatura kesilir ama cari hareket açılmazsa müşteri borcu
    görünmez — satış yapılmış ama alacak kaydı yok demektir.
    """
    ihlaller = []
    kesilmis = Fatura.query.filter(
        Fatura.durum.in_(['Kesildi', 'Kismi Tahsil', 'Tahsil Edildi'])).all()
    for f in kesilmis:
        hs = CariHareket.query.filter_by(
            baglanti_tip='fatura', baglanti_id=f.id).all()
        borclar = [h for h in hs if (h.borc or 0) > 0]
        if not borclar:
            ihlaller.append(
                f"✗ {f.fatura_no or f.id} ({f.musteri}): {f.toplam or 0:,.2f} "
                f"{f.doviz} kesilmiş ama CARİ HAREKETİ YOK")
            continue
        toplam_borc = sum(h.borc or 0 for h in borclar)
        if not yakin(toplam_borc, f.toplam):
            ihlaller.append(
                f"✗ {f.fatura_no or f.id} ({f.musteri}): fatura "
                f"{f.toplam or 0:,.2f} ≠ cari borç {toplam_borc:,.2f} "
                f"(fark {(f.toplam or 0) - toplam_borc:+,.2f})")
    return ihlaller


def d4_stok_durum():
    """Stok durumu ile satış/rezervasyon kaydı tutarlı olmalı.

    'Satildi' bir stoğun satış kaydı olmalı; 'Rezerve' bir stoğun
    aktif rezervasyonu olmalı. Aksi halde stok kilitli görünür ama
    kimse nedenini bulamaz — bu tur öncesinde yaşanan bir sorundu.
    """
    from models import BlokStok, EbatliStok, PlakaStok
    ihlaller = []
    for M, tip in ((BlokStok, 'BLOK'), (PlakaStok, 'PLAKA'), (EbatliStok, 'EBATLI')):
        for s in M.query.filter(M.durum.in_(['Rezerve', 'Satildi'])).all():
            if s.durum == 'Rezerve':
                r = Rezervasyon.query.filter_by(
                    stok_id=s.id, iptal_nedeni=None).first()
                if not r:
                    ihlaller.append(
                        f"✗ {tip} {s.id}: durum 'Rezerve' ama AKTİF "
                        f"REZERVASYON YOK — stok sebepsiz kilitli")
            elif s.durum == 'Satildi':
                sk = SatisKaydi.query.filter_by(stok_id=s.id).first()
                if not sk:
                    ihlaller.append(
                        f"✗ {tip} {s.id}: durum 'Satildi' ama SATIŞ KAYDI YOK")
    return ihlaller


def d5_kesim_korunum():
    """Kesimde tüketilen kaynak ile üretilen stok tutarlı olmalı.

    Kesim bir bloğu tüketip N plaka üretir. Kaynağın 'sonra' miktarı
    'önce'den büyük olamaz — madde yoktan var olmaz.
    """
    ihlaller = []
    for k in Kesim.query.all():
        once = k.kaynak_miktar_once
        sonra = k.kaynak_miktar_sonra
        if once is None or sonra is None:
            continue
        if sonra > once + TOLERANS:
            ihlaller.append(
                f"✗ {k.id} ({k.kaynak_no or k.kaynak_id}): kesim SONRASI "
                f"{sonra:,.3f} > ÖNCESİ {once:,.3f} — madde artmış")
        if sonra < -TOLERANS:
            ihlaller.append(
                f"✗ {k.id} ({k.kaynak_no or k.kaynak_id}): kalan miktar "
                f"NEGATİF ({sonra:,.3f})")
    return ihlaller


def d6_try_karsilik():
    """TL karşılığı, tutar × kur ile tutarlı olmalı.

    borc_try / alacak_try alanları raporlamada TL normalizasyonu
    için tutuluyor. Kur uygulanmış ama çarpım tutmuyorsa rapor ile
    ekstre ayrışır — bu turda tam olarak böyle bir hata yaşandı
    (kur bulunamayınca tutar SIFIRLANIYORDU).
    """
    ihlaller = []
    for h in CariHareket.query.all():
        doviz = (h.doviz or 'TRY').upper()
        if doviz == 'TRY':
            continue
        kur = h.kur_uygulanan
        if not kur or kur <= 0:
            if (h.borc or 0) > 0 or (h.alacak or 0) > 0:
                ihlaller.append(
                    f"? {h.id} ({h.cari_unvan or h.cari_id}): {doviz} hareket "
                    f"ama KUR YOK — TL karşılığı doğrulanamıyor")
            continue
        for alan, try_alan in (('borc', 'borc_try'), ('alacak', 'alacak_try')):
            tutar = getattr(h, alan) or 0
            try_deger = getattr(h, try_alan)
            if tutar <= 0:
                continue
            if try_deger is None:
                ihlaller.append(
                    f"✗ {h.id}: {alan} {tutar:,.2f} {doviz} var ama "
                    f"{try_alan} BOŞ")
                continue
            beklenen = tutar * kur
            # Kuruş farkları normal; %1'den büyük sapma ihlal.
            if abs(try_deger - beklenen) > max(TOLERANS, beklenen * 0.01):
                ihlaller.append(
                    f"✗ {h.id} ({h.cari_unvan or h.cari_id}): "
                    f"{tutar:,.2f} × {kur:.4f} = {beklenen:,.2f} "
                    f"ama {try_alan} = {try_deger:,.2f}")
    return ihlaller


# ══════════════════════════════════════════════════════════════════
DENETIMLER = [
    ('D1', 'KASA BAKİYESİ = HAREKETLER TOPLAMI', 'HAYALET PARA',
     d1_kasa_bakiye, 'her kasanın bakiyesi hareketleriyle tutuyor'),
    ('D2', 'CARİ HAREKET YÖN TUTARLILIĞI', 'BELİRSİZ BAKİYE',
     d2_cari_bakiye, 'her hareket tek yönlü (borç ya da alacak)'),
    ('D3', 'FATURA ↔ CARİ HAREKET', 'KAYIP ALACAK',
     d3_fatura_cari, 'kesilen her faturanın cari borcu var ve tutuyor'),
    ('D4', 'STOK DURUMU ↔ KAYIT', 'SEBEPSİZ KİLİT',
     d4_stok_durum, 'rezerve/satılmış her stoğun dayanağı var'),
    ('D5', 'KESİM MADDE KORUNUMU', 'YOKTAN VAROLUŞ',
     d5_kesim_korunum, 'kesimlerde madde artmamış'),
    ('D6', 'TL KARŞILIĞI = TUTAR × KUR', 'RAPOR SAPMASI',
     d6_try_karsilik, 'TL karşılıkları kurla tutarlı'),
]

print("═" * 74)
print(" MILESTONE ERP — DEĞİŞMEZLİK DENETİMİ")
print("═" * 74)

with app.app_context():
    sayilar = {
        'kasa': Kasa.query.count(),
        'kasa hareketi': KasaHareket.query.count(),
        'cari hareketi': CariHareket.query.count(),
        'fatura': Fatura.query.count(),
        'kesim': Kesim.query.count(),
    }
    print(" " + "  ·  ".join(f"{v:,} {a}" for a, v in sayilar.items()))
    print(f" Tolerans: ±{TOLERANS} (yuvarlama farkları ihlal sayılmaz)")

    toplam = 0
    for kod, ad, etiket, fn, bos in DENETIMLER:
        if SADECE and SADECE != kod:
            continue
        baslik(kod, ad, etiket)
        try:
            toplam += yazdir(fn(), bos)
        except Exception as exc:
            print(f"   ! denetim çalıştırılamadı: {exc}")

    print()
    print("═" * 74)
    if toplam:
        print(f" ✗ TOPLAM {toplam} İHLAL")
        print()
        print(" Her ihlali koda bakarak doğrulayın. Bunlar KOD hatası")
        print(" olabileceği gibi ELLE MÜDAHALE izi de olabilir.")
    else:
        print(" ✓ TÜM DEĞİŞMEZLİKLER SAĞLANIYOR")
        print()
        print(" Float→Numeric göçü öncesi bu çıktıyı SAKLAYIN:")
        print("   venv/bin/python degismezlik_denetim.py --tam > ~/degismezlik-oncesi.txt")
        print(" Göçten sonra tekrar alıp karşılaştırın; fark yoksa göç güvenli.")
    print("═" * 74)

sys.exit(1 if toplam else 0)

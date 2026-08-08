#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — FATURA / CARİ HAREKET KİLİDİ TANISI  ·  T2
#
#  BELİRTİ (kilitlenme):
#    • Cari bakiyesini silmek istiyorsunuz  → "faturayı iptal edin"
#    • Faturayı iptal etmek istiyorsunuz    → "bu faturaya tahsilat
#      yapılmış, önce tahsilatları geri alın"
#    • Çeki zaten sildiniz, satışı da sildiniz
#    → Çıkış yolu yok. Kayıt sistemde asılı kalıyor.
#
#  BU BETİK NE YAPAR:
#    Faturayı iptal etmeyi ENGELLEYEN kayıtları TEK TEK bulur ve
#    gösterir. Kod iki şeye bakıyor:
#
#      1. CariHareket(baglanti_tip='fatura', baglanti_id=<fatura>,
#                     alacak > 0)                    ← tahsilat hareketi
#      2. Cek(fatura_id=<fatura>, durum ∉ ('Iptal','Karsiliksiz'))
#
#    Çek silindiğinde kod, çekin cari_hareket_id'sine bakıp bağlı
#    hareketi de siler. Ama çek o alana YAZILMADAN oluşturulduysa
#    (ya da hareket başka yoldan açıldıysa) geriye HAYALET bir
#    alacak hareketi kalır — ve fatura sonsuza dek kilitlenir.
#
#  BU BETİK HİÇBİR ŞEYİ DEĞİŞTİRMEZ — yalnızca okur ve raporlar.
#  Ne yapılması gerektiğini söyler; kararı siz verirsiniz.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python tani_fatura_kilit.py                 # tüm kilitliler
#      venv/bin/python tani_fatura_kilit.py --fatura FTR-1  # tek fatura
#      venv/bin/python tani_fatura_kilit.py --cari CR-123   # bir carinin
# ══════════════════════════════════════════════════════════════════════
import os
import sys

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.getcwd())

FATURA = CARI = None
for i, a in enumerate(sys.argv[1:]):
    if a == '--fatura' and i + 2 <= len(sys.argv[1:]):
        FATURA = sys.argv[i + 2]
    if a == '--cari' and i + 2 <= len(sys.argv[1:]):
        CARI = sys.argv[i + 2]

import flask_app  # noqa: E402
from models import Cari, CariHareket, Cek, Fatura, db  # noqa: E402

app = flask_app.app

KESILMIS = ('Kesildi', 'Kismi Tahsil', 'Tahsil Edildi')

print("═" * 74)
print(" T2 · FATURA / CARİ HAREKET KİLİDİ TANISI")
print("═" * 74)

with app.app_context():
    q = Fatura.query.filter(Fatura.durum.in_(KESILMIS))
    if FATURA:
        q = Fatura.query.filter(db.or_(Fatura.id == FATURA,
                                       Fatura.fatura_no == FATURA))
    elif CARI:
        c = db.session.get(Cari, CARI)
        if c:
            q = q.filter(Fatura.musteri == c.unvan)
    faturalar = q.order_by(Fatura.fatura_tarihi).all()

    print(f" İncelenen fatura : {len(faturalar)}")
    print()

    if not faturalar:
        print(" Ölçüte uyan fatura yok.")
        sys.exit(0)

    kilitli = []
    for f in faturalar:
        # Kodun baktığı iki engel (flask_app.py, fatura durum akışı)
        tahsilatlar = CariHareket.query.filter(
            CariHareket.baglanti_tip == 'fatura',
            CariHareket.baglanti_id == f.id,
            CariHareket.alacak > 0).all()
        cekler = Cek.query.filter_by(fatura_id=f.id).filter(
            Cek.durum.notin_(['Iptal', 'Karsiliksiz'])).all()
        if tahsilatlar or cekler:
            kilitli.append((f, tahsilatlar, cekler))

    if not kilitli:
        print(" ✓ Kilitli fatura yok — hepsi iptal edilebilir durumda.")
        sys.exit(0)

    for f, tahsilatlar, cekler in kilitli:
        print("─" * 74)
        print(f" ✗ {f.fatura_no or f.id}   {f.musteri or ''}")
        print(f"   {f.fatura_tarihi}  ·  {f.toplam or 0:,.2f} {f.doviz or ''}"
              f"  ·  durum: {f.durum}")
        print("─" * 74)

        if tahsilatlar:
            print(f"   ENGEL 1 — {len(tahsilatlar)} tahsilat hareketi:")
            for h in tahsilatlar:
                _cek = 'evet' if (h.kaynak or '') == 'cek' else 'hayır'
                print(f"     • {h.id}  {h.hareket_tarihi}  "
                      f"alacak {h.alacak or 0:,.2f} {h.doviz or ''}")
                print(f"       islem_tip={h.islem_tip!r}  kaynak={h.kaynak!r}  "
                      f"çekten mi={_cek}")
                if h.aciklama:
                    print(f"       {h.aciklama[:70]}")
                # Bu hareketi işaret eden bir çek hâlâ var mı?
                sahip = Cek.query.filter_by(cari_hareket_id=h.id).first()
                if sahip:
                    print(f"       → sahibi çek: {sahip.id} ({sahip.durum})")
                else:
                    print(f"       → ⚠ SAHİPSİZ: bu hareketi işaret eden çek YOK.")
                    print(f"         Çek silinmiş ama hareket kalmış olabilir.")

        if cekler:
            print(f"   ENGEL 2 — {len(cekler)} açık çek:")
            for ck in cekler:
                print(f"     • {ck.id}  {ck.cek_no or '—'}  "
                      f"{ck.tutar or 0:,.2f} {ck.doviz or ''}  durum: {ck.durum}")

        print()
        print("   ÇÖZÜM YOLU:")
        if cekler:
            print("     1) Çek/Senet ekranından bu çekleri SİLİN ya da")
            print("        durumlarını 'Iptal' yapın.")
        if tahsilatlar:
            sahipsiz = [h for h in tahsilatlar
                        if not Cek.query.filter_by(cari_hareket_id=h.id).first()]
            if sahipsiz:
                print("     2) SAHİPSİZ tahsilat hareketleri var — bunlar")
                print("        Cari ekranında hareketin yanındaki ✕ ile")
                print("        silinebilir (tahsilat hareketi silinebilir,")
                print("        engellenen yalnızca FATURA BORCU hareketidir).")
                for h in sahipsiz:
                    print(f"          → {h.id}")
            else:
                print("     2) Tahsilatlar çeke bağlı — önce çekleri temizleyin.")
        print("     3) Sonra faturayı 'Iptal' yapın; borç hareketi de")
        print("        otomatik geri alınır.")
        print()

    print("═" * 74)
    print(f" {len(kilitli)} fatura kilitli")
    print()
    print(" NOT: Cari ekranında BORÇ hareketi (fatura borcu) doğrudan")
    print(" silinemez — bilerek. Silinseydi fatura ile cari bakiye")
    print(" birbirini tutmazdı. Doğru yol faturayı iptal etmektir;")
    print(" iptal borcu da geri alır.")
    print("═" * 74)

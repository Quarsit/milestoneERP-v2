import os, sys
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.getcwd())
import flask_app
from models import db, Fatura, Maliyet, Siparis, SatisKaydi
app = flask_app.app
with app.app_context():
    print("═" * 60)
    print(" KDV İADE — VERİ ENVANTERİ")
    print("═" * 60)
    print("\n FATURALAR (durum × satış tipi)")
    for d, t, n in db.session.query(Fatura.durum, Fatura.satis_tipi,
                                    db.func.count(Fatura.id)).group_by(
                                        Fatura.durum, Fatura.satis_tipi).all():
        print(f"   {d or '—':<16s} {t or '—':<16s} {n}")

    print("\n KDV MALİYET KALEMLERİ")
    for t, a, n, top in db.session.query(
            Maliyet.maliyet_tip, Maliyet.aktif, db.func.count(Maliyet.id),
            db.func.sum(Maliyet.tutar)).filter(
                Maliyet.maliyet_tip.in_(['Devreden KDV', 'Iade KDV'])).group_by(
                    Maliyet.maliyet_tip, Maliyet.aktif).all():
        print(f"   {t:<16s} {'aktif' if a else 'pasif':<8s} {n:>4} kalem  "
              f"{round(top or 0, 2)} TL")
    if not Maliyet.query.filter(Maliyet.maliyet_tip.in_(
            ['Devreden KDV', 'Iade KDV'])).count():
        print("   (hiç KDV kalemi yok)")

    bagsiz = Maliyet.query.filter(Maliyet.maliyet_tip == 'Iade KDV',
                                  Maliyet.aktif == True,
                                  Maliyet.iade_dosya_id.is_(None)).all()
    print(f"\n DOSYAYA BAĞLANMAYI BEKLEYEN 'Iade KDV': {len(bagsiz)} kalem "
          f"({round(sum(m.tutar or 0 for m in bagsiz), 2)} TL)")
    for m in bagsiz[:10]:
        print(f"   {m.id}  {m.maliyet_tarihi}  {m.doviz} {m.tutar}  "
              f"{(m.aciklama or '')[:40]}")

    print(f"\n SİPARİŞ: {Siparis.query.count()} · "
          f"teslim edilen: {Siparis.query.filter_by(durum='Teslim Edildi').count()}")
    print(f" SATIŞ KAYDI: {SatisKaydi.query.count()}")
    print("═" * 60)

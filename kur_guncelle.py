#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — ZAMANLANMIŞ KUR GÜNCELLEME  ·  K3
#
#  NE YAPAR:
#    Kur arşivindeki eksik günleri TCMB'den çeker. Uygulamayı
#    başlatmadan, tek başına çalışır. systemd timer bunu günde iki
#    kez tetikler.
#
#  NEDEN GÜNDE İKİ KEZ:
#    TCMB gösterge kurunu her iş günü 15:30'da yayınlar.
#      08:00 → dünün/haftasonunun kuru kesin gelmiştir; gün başında
#              sistem güncel kurla açılır
#      15:35 → bugünün kuru yayınlanmıştır; aynı gün içinde girilen
#              işlemler doğru kurla kaydedilir
#
#  KURSUZ GÜNLER:
#    TCMB tatilde kur yayınlamaz. Bu betik (yama_k2 ile birlikte) o
#    günleri 'KUR_YOK' olarak işaretler; bir daha sorulmazlar.
#    Son 4 gün işaretlenmez — henüz yayınlanmamış olabilir.
#
#  KULLANIM:
#      venv/bin/python kur_guncelle.py           # eksikleri çek
#      venv/bin/python kur_guncelle.py --sessiz  # yalnızca hata yaz
#
#  SYSTEMD KURULUMU: betiğin sonundaki açıklamaya bakın.
# ══════════════════════════════════════════════════════════════════════
import os
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta

import requests
import tcmb_kur   # TK1
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

SESSIZ = '--sessiz' in sys.argv
GERI_GUN = 10          # kaç gün geriye bakılsın
ISARET_SINIRI = 4      # bundan yeni günler 'kur yok' diye işaretlenmez


def yaz(*a):
    if not SESSIZ:
        print(*a)


def tcmb_gun_kuru_cek(gun):
    """Bir günün TCMB kuru. Döner: (usd, eur) ya da (None, None).

    NOT: flask_app.py içindeki _tcmb_gun_kuru_cek() ile aynı mantık.
    Oradaki fonksiyon create_app() gövdesinde yuvalandığı için
    dışarıdan çağrılamıyor. Mantık değişirse iki yeri de güncelleyin.
    """
    try:
        url = (f"https://www.tcmb.gov.tr/kurlar/{gun.strftime('%Y%m')}/"
               f"{gun.strftime('%d%m%Y')}.xml")
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return None, None
        root = ET.fromstring(r.content)
        # YAMA TK1: ayristirma tcmb_kur.py'de. Ayni mantigin dort
        # kopyasi vardi; K9'da ucu duzeltilip biri kacirilmisti.
        return tcmb_kur._xml_ayristir(r.content)
    except Exception:
        return None, None


import flask_app  # noqa: E402
from models import DovizKur, db  # noqa: E402

app = flask_app.app

with app.app_context():
    bugun = date.today()
    basla = bugun - timedelta(days=GERI_GUN)
    isaret_siniri = bugun - timedelta(days=ISARET_SINIRI)

    # Hangi günler zaten kayıtlı? ('KUR_YOK' işaretleri de sayılır —
    # amaç zaten onları tekrar sormamak.)
    kayitli = set(t[0] for t in db.session.query(DovizKur.tarih)
                  .filter(DovizKur.doviz == 'USD',
                          DovizKur.tarih >= basla).all())

    eksik = []
    g = basla
    while g <= bugun:
        if g.weekday() < 5 and g not in kayitli:
            eksik.append(g)
        g += timedelta(days=1)

    if not eksik:
        yaz(f"[{datetime.now():%Y-%m-%d %H:%M}] Kur güncel — eksik gün yok.")
        sys.exit(0)

    yaz(f"[{datetime.now():%Y-%m-%d %H:%M}] {len(eksik)} eksik gün kontrol ediliyor…")
    eklenen = isaretlenen = 0
    for g in eksik:
        usd, eur = tcmb_gun_kuru_cek(g)
        if usd:
            _a, _s, _e, _ea = usd   # EA1
            db.session.add(DovizKur(doviz='USD', alis=_a, satis=_s,
                                    efektif=_e, efektif_alis=_ea,
                                    tarih=g, kaynak='TCMB'))
            eklenen += 1
            yaz(f"   + {g}  USD {usd}" + (f"  EUR {eur}" if eur else ''))
        elif g < isaret_siniri:
            # Yeterince eski ve hâlâ kur yok → resmî tatil, kalıcı işaret
            db.session.add(DovizKur(doviz='USD', tarih=g, kaynak='KUR_YOK'))
            isaretlenen += 1
        if eur:
            _a, _s, _e, _ea = eur   # EA1
            db.session.add(DovizKur(doviz='EUR', alis=_a, satis=_s,
                                    efektif=_e, efektif_alis=_ea,
                                    tarih=g, kaynak='TCMB'))
        elif not eur and g < isaret_siniri:
            db.session.add(DovizKur(doviz='EUR', tarih=g, kaynak='KUR_YOK'))

    db.session.commit()
    ozet = f"{eklenen} kur eklendi"
    if isaretlenen:
        ozet += f", {isaretlenen} gün 'kur yok' işaretlendi (tatil)"
    yaz(f"   {ozet}")

# ══════════════════════════════════════════════════════════════════════
#  SYSTEMD KURULUMU (Pardus)
#
#  1) Servis dosyası:
#     sudo nano /etc/systemd/system/milestone-kur.service
#
#     [Unit]
#     Description=Milestone ERP — TCMB kur güncelleme
#     After=network-online.target postgresql.service
#
#     [Service]
#     Type=oneshot
#     User=mermer
#     WorkingDirectory=/home/mermer/milestoneERP-v2
#     ExecStart=/home/mermer/milestoneERP-v2/venv/bin/python kur_guncelle.py
#
#  2) Zamanlayıcı:
#     sudo nano /etc/systemd/system/milestone-kur.timer
#
#     [Unit]
#     Description=Milestone ERP — kur güncelleme (08:00 ve 15:35)
#
#     [Timer]
#     OnCalendar=Mon..Fri 08:00
#     OnCalendar=Mon..Fri 15:35
#     Persistent=true
#
#     [Install]
#     WantedBy=timers.target
#
#     NOT: Persistent=true — makine kapalıyken kaçan çalıştırma
#     açılışta telafi edilir.
#     NOT: 15:35 seçildi, 15:30 değil — TCMB'nin yayını tamamlaması
#     için 5 dakika pay bırakıldı.
#
#  3) Etkinleştir:
#     sudo systemctl daemon-reload
#     sudo systemctl enable --now milestone-kur.timer
#     systemctl list-timers | grep milestone
#
#  4) Elle dene:
#     sudo systemctl start milestone-kur.service
#     journalctl -u milestone-kur.service -n 20 --no-pager
# ══════════════════════════════════════════════════════════════════════

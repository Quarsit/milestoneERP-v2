"""
/api/v2/eposta/* — Kullanıcı bazlı e-posta (SMTP) ayarları.

NEDEN VAR:
    Sistemde tek bir şirket SMTP hesabı tanımlıydı ve tüm e-postalar aynı
    adresten gidiyordu. Her satışçının kendi posta kutusu olduğu için bu
    karışıklık yaratıyordu: müşteri kime yanıt vereceğini bilemiyor,
    yazışma geçmişi tek kutuda birikiyordu.

    Artık her kullanıcı kendi SMTP hesabını tanımlayabilir. Tanımlamışsa
    e-postalar onun adresinden çıkar; tanımlamamışsa şirketin ortak
    hesabına düşülür (eski davranış korunur).

NEDEN KENDİ HESABI, "sadece From değiştirme" DEĞİL:
    Ortak hesaptan bağlanıp başka bir adres adına göndermek SPF/DMARC
    uyuşmazlığı yaratır; posta reddedilir veya spam'e düşer. Kullanıcı
    kendi kutusuyla kimlik doğruladığında böyle bir sorun olmaz.

SAKLAMA:
    Veriler tablosu — kategori='smtp_kullanici', deger=<kullanıcı adı>,
    uzun_deger=JSON. Ayrı tablo/sütun gerektirmez.

GÜVENLİK:
    Şifre tarayıcıya ASLA geri gönderilmez; yalnızca "kayıtlı mı" bilgisi
    döner. Kullanıcı sadece kendi ayarını görebilir ve değiştirebilir.
"""
from __future__ import annotations

import json

from flask import Blueprint, jsonify, request, session

from models import db, Veriler

bp = Blueprint("eposta_ayar", __name__, url_prefix="/api/v2/eposta")

KATEGORI = "smtp_kullanici"
ALANLAR = ("sunucu", "port", "kullanici", "sifre", "gonderen_ad",
           "gonderen_email", "guvenlik")


def _oturum_kullanici():
    return session.get("kullanici")


def _kayit_getir(kullanici_adi):
    return Veriler.query.filter_by(kategori=KATEGORI, deger=kullanici_adi).first()


def _ayar_oku(kullanici_adi):
    """Kullanıcının kayıtlı ayarlarını dict olarak döner; yoksa {}."""
    k = _kayit_getir(kullanici_adi)
    if not k or not k.uzun_deger:
        return {}
    try:
        d = json.loads(k.uzun_deger)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


@bp.get("/ayar")
def ayar_getir():
    """Oturumdaki kullanıcının kendi e-posta ayarları (şifre hariç)."""
    ad = _oturum_kullanici()
    if not ad:
        return jsonify(error="Unauthorized"), 401

    d = _ayar_oku(ad)
    return jsonify(
        ok=True,
        tanimli=bool(d.get("sunucu") and d.get("kullanici")),
        sunucu=d.get("sunucu", ""),
        port=d.get("port", 587),
        kullanici=d.get("kullanici", ""),
        gonderen_ad=d.get("gonderen_ad", ""),
        gonderen_email=d.get("gonderen_email", ""),
        guvenlik=d.get("guvenlik", "tls"),
        sifre_kayitli=bool(d.get("sifre")),   # şifrenin kendisi ASLA dönmez
    )


@bp.post("/ayar")
def ayar_kaydet():
    """Kendi ayarlarını kaydeder. Şifre boş bırakılırsa mevcut şifre korunur."""
    ad = _oturum_kullanici()
    if not ad:
        return jsonify(error="Unauthorized"), 401

    gelen = request.get_json(silent=True) or {}
    mevcut = _ayar_oku(ad)

    yeni = {}
    for alan in ALANLAR:
        deger = gelen.get(alan)
        if alan == "sifre":
            # Boş gelirse eskisini koru — kullanıcı her düzenlemede
            # şifresini yeniden yazmak zorunda kalmasın.
            yeni["sifre"] = (deger or "").strip() or mevcut.get("sifre", "")
        elif alan == "port":
            try:
                yeni["port"] = int(deger or mevcut.get("port") or 587)
            except (TypeError, ValueError):
                yeni["port"] = 587
        else:
            yeni[alan] = (str(deger).strip() if deger is not None
                          else mevcut.get(alan, ""))

    yeni["guvenlik"] = (yeni.get("guvenlik") or "tls").lower()
    if yeni["guvenlik"] not in ("tls", "ssl", "yok"):
        yeni["guvenlik"] = "tls"
    # Gönderen adresi boşsa SMTP kullanıcı adını kullan (genelde e-postadır)
    if not yeni.get("gonderen_email"):
        yeni["gonderen_email"] = yeni.get("kullanici", "")
    if not yeni.get("gonderen_ad"):
        yeni["gonderen_ad"] = ad

    eksik = [a for a in ("sunucu", "kullanici", "sifre") if not yeni.get(a)]
    if eksik:
        return jsonify(ok=False,
                       mesaj="Eksik alan: " + ", ".join(eksik)), 400

    k = _kayit_getir(ad)
    if not k:
        k = Veriler(kategori=KATEGORI, deger=ad)
        db.session.add(k)
    k.uzun_deger = json.dumps(yeni, ensure_ascii=False)
    k.ek_bilgi = yeni.get("gonderen_email", "")[:200]   # hızlı bakış için
    db.session.commit()

    return jsonify(ok=True, mesaj="E-posta ayarlarınız kaydedildi.")


@bp.delete("/ayar")
def ayar_sil():
    """Kişisel ayarı kaldırır — kullanıcı şirket hesabına geri döner."""
    ad = _oturum_kullanici()
    if not ad:
        return jsonify(error="Unauthorized"), 401

    k = _kayit_getir(ad)
    if k:
        db.session.delete(k)
        db.session.commit()
    return jsonify(ok=True, mesaj="Kişisel e-posta ayarı kaldırıldı. "
                                  "Gönderimler şirket hesabından yapılacak.")


@bp.post("/test")
def test_gonder():
    """Kayıtlı ayarlarla kullanıcının kendi adresine deneme e-postası yollar."""
    ad = _oturum_kullanici()
    if not ad:
        return jsonify(error="Unauthorized"), 401

    d = _ayar_oku(ad)
    if not (d.get("sunucu") and d.get("kullanici") and d.get("sifre")):
        return jsonify(ok=False, mesaj="Önce ayarları kaydedin."), 400

    hedef = (request.get_json(silent=True) or {}).get("alici") \
        or d.get("gonderen_email") or d.get("kullanici")

    import smtplib
    import ssl as _ssl
    from email.mime.text import MIMEText
    from email.utils import formataddr

    msg = MIMEText(
        "Bu bir deneme mesajıdır.\n\n"
        "Milestone ERP e-posta ayarlarınız çalışıyor. Bundan sonra "
        "gönderdiğiniz proforma ve belgeler bu adresten çıkacak.\n",
        "plain", "utf-8")
    msg["From"] = formataddr((d.get("gonderen_ad") or ad,
                              d.get("gonderen_email") or d["kullanici"]))
    msg["To"] = hedef
    msg["Subject"] = "Milestone ERP — e-posta ayarı denemesi"

    port = int(d.get("port") or 587)
    guvenlik = (d.get("guvenlik") or "tls").lower()

    try:
        if guvenlik == "ssl":
            ctx = _ssl.create_default_context()
            with smtplib.SMTP_SSL(d["sunucu"], port, timeout=25, context=ctx) as s:
                s.login(d["kullanici"], d["sifre"])
                s.send_message(msg)
        else:
            with smtplib.SMTP(d["sunucu"], port, timeout=25) as s:
                if guvenlik == "tls":
                    s.starttls(context=_ssl.create_default_context())
                s.login(d["kullanici"], d["sifre"])
                s.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        return jsonify(ok=False,
                       mesaj="Kimlik doğrulama başarısız — kullanıcı adı "
                             "veya şifre hatalı."), 400
    except Exception as e:                                    # noqa: BLE001
        return jsonify(ok=False, mesaj=f"Gönderilemedi: {e}"), 400

    return jsonify(ok=True, mesaj=f"Deneme e-postası gönderildi: {hedef}")

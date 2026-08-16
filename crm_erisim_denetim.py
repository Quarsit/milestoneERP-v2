#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — MÜŞTERİ ERİŞİM KAPSAMI DENETİMİ
#
#  ── NE İÇİN ──
#    CRM-C, müşteri erişim süzgecini getirdi. Ama süzgeç 55+ uç
#    noktaya elle uygulanmak zorunda ve BİRİ ATLANIRSA satışçı,
#    görmemesi gereken müşteriyi o kapıdan görür — üstelik siz
#    sistemin kapalı olduğunu sanırsınız.
#
#    Yarım uygulanmış satır güvenliği, hiç olmamasından KÖTÜDÜR:
#    sahte güven üretir. Bu betik kapsamı ÖLÇER.
#
#  ── NE ARAR ──
#    Müşteriye bağlı modelleri (Cari, Proforma, Fatura, SatisKaydi,
#    Sevkiyat, Rezervasyon, CariHareket, Cek, Siparis) sorgulayan
#    her uç nokta fonksiyonunu bulur ve içinde erişim süzgecinin
#    (`_cari_suz` / `_gorulebilir_cari_idler` / `_cari_gorulebilir_mi`)
#    çağrılıp çağrılmadığına bakar.
#
#  ── YANLIŞ POZİTİFLER ──
#    Yazma uç noktaları (POST/PUT/DELETE) ve yalnızca admin'e açık
#    olanlar listelenir ama AYRI bölümde — onlarda süzgeç
#    gerekmeyebilir. Karar sizin; betik iddia etmez, gösterir.
#
#  ── HİÇBİR ŞEY DEĞİŞTİRMEZ ──  Yalnızca kaynak kodu okur.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python crm_erisim_denetim.py
#      venv/bin/python crm_erisim_denetim.py --tam
# ══════════════════════════════════════════════════════════════════════
import re
import sys
from pathlib import Path

APP = Path('flask_app.py')
if not APP.exists():
    print("HATA: flask_app.py bu klasörde yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

TAM = '--tam' in sys.argv

# Musteriye bagli modeller — bunlari sorgulayan uc nokta suzgec
# uygulamali.
MODELLER = ('Cari', 'Proforma', 'Fatura', 'SatisKaydi', 'Sevkiyat',
            'Rezervasyon', 'CariHareket', 'Cek', 'Siparis')

SUZGEC = ('_cari_suz', '_gorulebilir_cari_idler', '_cari_gorulebilir_mi')

# CRM-C2 ile KURESEL suzgec geldi: SELECT'ler ORM katmaninda
# otomatik suzuluyor, uc nokta basina kod GEREKMIYOR. Bu yuzden
# okuma uclari artik bulgu degil bilgi; asil risk YAZMA uclarinda.
KURESEL_VAR = '_erisim_suzgeci' in Path('flask_app.py').read_text(
    encoding='utf-8', errors='replace')

kaynak = APP.read_text(encoding='utf-8', errors='replace').replace('\r\n', '\n')
satirlar = kaynak.split('\n')

# ── Uç noktaları çıkar: @app.route(...) + ardından gelen def ──
uclar = []
for i, s in enumerate(satirlar):
    m = re.match(r"\s*@app\.route\('([^']+)'(?:,\s*methods=\[([^\]]*)\])?", s)
    if not m:
        continue
    yol, metotlar = m.group(1), (m.group(2) or "'GET'")
    # Ardindaki ilk 'def'
    j = i + 1
    while j < len(satirlar) and not re.match(r"\s*def ", satirlar[j]):
        j += 1
        if j - i > 6:
            break
    if j >= len(satirlar) or not re.match(r"\s*def ", satirlar[j]):
        continue
    ad = re.match(r"\s*def (\w+)", satirlar[j]).group(1)
    girinti = len(satirlar[j]) - len(satirlar[j].lstrip())
    # Govde: girinti geri dusene kadar
    k = j + 1
    while k < len(satirlar):
        t = satirlar[k]
        if t.strip() and (len(t) - len(t.lstrip())) <= girinti and not t.lstrip().startswith('#'):
            break
        k += 1
    uclar.append({
        'yol': yol,
        'metotlar': [x.strip().strip("'\"") for x in metotlar.split(',')],
        'ad': ad,
        'govde': '\n'.join(satirlar[j:k]),
        'satir': j + 1,
    })

print("═" * 74)
print(" MÜŞTERİ ERİŞİM KAPSAMI DENETİMİ")
print("═" * 74)
print(f" Taranan uç nokta : {len(uclar)}")
print(f" İzlenen model    : {', '.join(MODELLER)}")
print()

acik_okuma, acik_yazma, admin_ozel, kapali = [], [], [], []

for u in uclar:
    g = u['govde']
    kullanilan = [m for m in MODELLER if re.search(rf"\b{m}\.query\b", g)]
    if not kullanilan:
        continue
    suzuldu = any(f in g for f in SUZGEC)
    sadece_admin = bool(re.search(r"session\.get\('rol'\)[^\n]*ADMIN", g))
    yazma = any(x in u['metotlar'] for x in ('POST', 'PUT', 'DELETE', 'PATCH'))

    kayit = (u, kullanilan)
    if suzuldu:
        kapali.append(kayit)
    elif sadece_admin:
        admin_ozel.append(kayit)
    elif yazma:
        acik_yazma.append(kayit)
    else:
        acik_okuma.append(kayit)

toplam = len(acik_okuma) + len(acik_yazma) + len(admin_ozel) + len(kapali)


def _yaz(baslik, liste, aciklama):
    print("─" * 74)
    print(f" {baslik}")
    print("─" * 74)
    if not liste:
        print("   ✓ yok")
        print()
        return
    print(f"   {len(liste)} uç nokta — {aciklama}")
    for u, modeller in (liste if TAM else liste[:15]):
        yontem = '/'.join(m for m in u['metotlar'] if m)
        print(f"     {yontem:<12} {u['yol']:<34} {u['ad']}")
        print(f"       {' ' * 11} model: {', '.join(modeller)}  (satır {u['satir']})")
    if not TAM and len(liste) > 15:
        print(f"     … {len(liste) - 15} tane daha (--tam ile hepsi)")
    print()


print(f"  Müşteri verisine dokunan uç nokta : {toplam}")
print(f"    süzgeç uygulanmış               : {len(kapali)}")
print(f"    yalnızca admin                  : {len(admin_ozel)}")
print(f"    YAZMA, süzgeçsiz                : {len(acik_yazma)}")
print(f"    OKUMA, SÜZGEÇSİZ                : {len(acik_okuma)}")
print()

if KURESEL_VAR:
    print("─" * 74)
    print(" A · OKUMA UÇLARI   [küresel süzgeç devrede]")
    print("─" * 74)
    print(f"   {len(acik_okuma)} uç noktada yerel süzgeç yok, ama CRM-C2'nin")
    print("   küresel süzgeci tüm SELECT'leri ORM katmanında süzüyor.")
    print("   Yerel kod gerekmiyor.")
    print()
else:
    _yaz("A · OKUMA UÇLARI — SÜZGEÇ YOK   [SIZINTI]", acik_okuma,
         "kapalı müşteri bu kapıdan görünür")

_yaz("B · YAZMA UÇLARI — KONTROL YOK   [ASIL RİSK]", acik_yazma,
     "küresel süzgeç YALNIZCA SELECT'i kapsar; UPDATE/DELETE korunmaz")

_yaz("C · YALNIZCA ADMİN   [bilgi]", admin_ozel,
     "admin'e kapalı müşteri diye bir şey yok, sorun değil")

if TAM:
    _yaz("D · SÜZGEÇ UYGULANMIŞ   [bilgi]", kapali, "kural uygulanıyor")

print("═" * 74)
if not KURESEL_VAR and acik_okuma:
    print(f" ✗ {len(acik_okuma)} OKUMA ucunda süzgeç yok — kapalı müşteriler")
    print("   bu kapılardan görünüyor.")
    sys.exit(1)
print(" ✓ OKUMA tarafı kapalı" + (" (küresel süzgeç)" if KURESEL_VAR else ""))
if acik_yazma:
    print()
    print(f" ⚠ {len(acik_yazma)} YAZMA ucunda erişim kontrolü YOK.")
    print("   Küresel süzgeç SELECT'i kapsar; UPDATE/DELETE'i KAPSAMAZ.")
    print("   Kimliği bilen biri başkasının müşterisini güncelleyebilir.")
    print()
    print("   Eklenecek kontrol:")
    print("     if not _cari_gorulebilir_mi(kayit.cari_id):")
    print("         return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403")
print("═" * 74)

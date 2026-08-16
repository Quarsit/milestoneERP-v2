#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — KAYDA GİT BAĞLANTILARI  ·  KD4
#
#  ── SORUN ──
#    Kasa defteri satırlarındaki cari bağlantısı `/cari?id=...`
#    adresine gidiyordu. Ama HİÇBİR sayfa URL'den kayıt seçmeyi
#    desteklemiyor: `/cari?id=X` yalnızca listeyi açıyor, `id`
#    sessizce yok sayılıyor.
#
#    Yani bağlantı çalışıyormuş gibi görünüp hiçbir şey yapmıyordu.
#    Bunu ben yazmıştım (KD2) ve hedef sayfayı kontrol etmemiştim.
#
#  ── DEPODAKİ KALIP KULLANILDI ──
#    Yöntem uydurulmadı; `kesim.html` ve `base.html` zaten
#    URLSearchParams ile gelen parametreye göre ekran açıyor.
#    Aynı kalıp izlendi.
#
#  ── EKLENENLER ──
#    /cari?ac=<cari_id>     → o carinin detay çekmecesi açılır
#    /kasa?kasa=<kasa_id>   → o kasanın hareket listesi açılır
#    /kasa?yeni=1&kasa=<id> → elle hareket girişi modalı açılır
#
#    Kasa defterinde:
#      · cari adı → cari detayına
#      · "Kasa hareketlerine git" → /kasa'da seçili kasa
#      · "+ Hareket gir" → doğrudan giriş modalı
#
#  ── DEFTER HÂLÂ SALT OKUNUR ──
#    Veri girişi defterden YAPILMIYOR, sadece giriş ekranına
#    yönlendiriliyor. İkinci bir yazma yolu açmak, bu oturumda
#    tekrar tekrar düzelttiğimiz "paralel gerçek" sorununu
#    yeniden üretirdi: defterden girilen hareket cari bakiyesini
#    güncellemez, belge bağlantısı boş kalır ve mutabakat kendi
#    yazdığını doğrular hale gelir.
#
#  ⚠ Şablonlar da kopyalanmalı: cari.html, kasa.html, kasa_defter.html
#  Şema değişikliği YOK. Bu yama yalnızca ön koşulu doğrular.
# ══════════════════════════════════════════════════════════════════════
import sys
from pathlib import Path

GEREKLI = {
    'templates/cari.html': ('cariUrlIleAc', "?ac=<cari_id> ile detay açma"),
    'templates/kasa.html': ('kasaUrlIleAc', "?kasa=<id> ile hareket listesi"),
    'templates/kasa_defter.html': ('kdKasayaGit', "kasa/kayıt bağlantıları"),
}

print("═" * 70)
print(" KD4 · KAYDA GİT BAĞLANTILARI")
print("═" * 70)
print()

eksik = []
for yol, (imza, aciklama) in GEREKLI.items():
    p = Path(yol)
    if not p.exists():
        eksik.append(f"{yol} — dosya yok")
        continue
    if imza not in p.read_text(encoding='utf-8', errors='replace'):
        eksik.append(f"{yol} — {aciklama} eksik")
    else:
        print(f"  ✓ {yol:<30} {aciklama}")

print()
if eksik:
    print(" ✗ Şu şablon(lar) güncellenmemiş:")
    for e in eksik:
        print(f"     {e}")
    print()
    print("   Bu değişiklik yama ile değil, DOSYA KOPYALAMA ile")
    print("   uygulanıyor. Verilen üç şablonu templates/ altına")
    print("   kopyalayıp bu betiği tekrar çalıştırın.")
    sys.exit(1)

_bozuk = Path('templates/kasa_defter.html').read_text(encoding='utf-8')
if "href=\'/cari?id=" in _bozuk or '/cari?id=' in _bozuk:
    print(" ✗ kasa_defter.html'de eski '/cari?id=' bağlantısı duruyor.")
    print("   O adres çalışmıyor; güncel şablonu kopyalayın.")
    sys.exit(1)
print("  ✓ eski çalışmayan '/cari?id=' bağlantısı kalmadı")
print()
print(" ✓ Üç şablon da yerinde — bağlantılar çalışır durumda.")
print()
print("   /cari?ac=<cari_id>      cari detayı")
print("   /kasa?kasa=<kasa_id>    kasa hareket listesi")
print("   /kasa?yeni=1&kasa=<id>  elle hareket girişi")
print("═" * 70)

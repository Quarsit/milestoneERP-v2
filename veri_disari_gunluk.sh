#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — GÜNLÜK REFERANS VERİ DIŞA AKTARMA  ·  VD2
#
#  Her gun cariler/kasalar/bankalar/listeler Excel'e yazilir ve
#  5 GUNDEN ESKI ciktilar silinir.
#
#  ── İKİ HEDEF ──
#    ~/yedekler                       (pg_dump ciktilarinin yaninda)
#    ~/milestoneERP-v2/veri_disari    (proje klasoru, elden erisim)
#
#  ── SİLME ÜRETİMDEN SONRA ──
#    Once uretilir, BASARILI olursa silinir. Tersi olsaydi uretim
#    hata verdigi bir gun eski dosyalar da silinip elde HICBIR SEY
#    kalmazdi — yedeklemede en kotu senaryo budur.
#
#  ── SİLME KAPSAMI DAR ──
#    Yalnizca `milestone_referans_*.xlsx` kalibi, yalnizca bu iki
#    klasorde, `-maxdepth 1` ile alt klasorlere inmeden. Genis bir
#    `*.xlsx` kalibi kullanicinin oraya koydugu baska dosyalari da
#    silerdi.
#
#  KULLANIM:
#      ./veri_disari_gunluk.sh
#
#  CRON (her gun 20:05):
#      5 20 * * * /home/mermer/milestoneERP-v2/veri_disari_gunluk.sh \
#                 >> /home/mermer/veri_disari.log 2>&1
# ══════════════════════════════════════════════════════════════════════
set -uo pipefail

PROJE="/home/mermer/milestoneERP-v2"
HEDEFLER=("/home/mermer/yedekler" "$PROJE/veri_disari")
GUN=5
KALIP="milestone_referans_*.xlsx"

cd "$PROJE" || { echo "HATA: $PROJE yok"; exit 1; }

echo "──────────────────────────────────────────────────────────"
echo " $(date '+%Y-%m-%d %H:%M') · referans veri dışa aktarma"

if [ ! -x venv/bin/python ]; then
  echo " ✗ venv/bin/python bulunamadı — ÜRETİM YAPILMADI, silme de yok."
  exit 1
fi

hata=0
for dizin in "${HEDEFLER[@]}"; do
  mkdir -p "$dizin"
  # ÜRETİM
  if venv/bin/python veri_disari.py --klasor "$dizin" > /tmp/vd_cikti.txt 2>&1; then
    yeni=$(grep -oE '/[^ ]+\.xlsx' /tmp/vd_cikti.txt | tail -1)
    echo " ✓ üretildi: ${yeni:-$dizin}"
  else
    echo " ✗ ÜRETİM BAŞARISIZ: $dizin"
    sed -n '1,6p' /tmp/vd_cikti.txt | sed 's/^/     /'
    hata=1
    # Bu dizinde silme YAPILMAZ; elde eski dosya kalsın.
    continue
  fi

  # ROTASYON — yalnızca üretim başarılıysa
  silinen=$(find "$dizin" -maxdepth 1 -name "$KALIP" -mtime +$GUN -print -delete 2>/dev/null | wc -l)
  kalan=$(find "$dizin" -maxdepth 1 -name "$KALIP" 2>/dev/null | wc -l)
  echo "   ${GUN} günden eski: $silinen silindi · kalan: $kalan dosya"
done

if [ "$hata" -ne 0 ]; then
  echo " ⚠ En az bir hedefte üretim başarısız — o dizinde silme yapılmadı."
  exit 1
fi
echo " ✓ tamamlandı"

#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — YERLEŞTİR
#
#  Ana dizine yanlışlıkla kopyalanan dosyaları doğru klasöre taşır,
#  eski/kopya olanları siler.
#
#  NEDEN VAR: 19.09'da excel_import.py blueprints/ yerine ana dizine
#  kopyalandı. Sistem blueprints/ içindeki ESKİ sürümü kullanmaya
#  devam etti; düzeltme push edildiği halde çalışmadı ve hiçbir
#  denetim fark etmedi.
#
#  KURALLAR (yalnızca ana dizindeki dosyalara bakılır):
#    *.html                 → templates/
#    test_*.py              → tests/
#    blueprints/ içinde aynı adlı dosya varsa        → blueprints/
#    migrations/versions/ içinde aynı adlı varsa
#      ya da dosya bir Alembic göçüyse (down_revision) → migrations/versions/
#    Diğer .py dosyaları (flask_app.py, denetimler…) ana dizinde kalır.
#
#  HANGİSİ KALIR:
#    · Hedefte yoksa                 → taşınır
#    · Hedefteyle birebir aynıysa    → ana dizindeki silinir
#    · Farklıysa DAHA YENİ olan kalır:
#        kaydedilmemiş değişiklik varsa dosya saati,
#        yoksa son commit saati karşılaştırılır.
#      Ana dizindeki yeniyse hedefin üzerine taşınır;
#      eskiyse ana dizindeki silinir.
#    Silinen/üzerine yazılan her şey git geçmişinde durur.
#
#  KULLANIM:
#      ./yerlestir.sh              # RAPOR — hiçbir şeye dokunmaz
#      ./yerlestir.sh --uygula     # uygular
#      ./yerlestir.sh --kontrol    # sessiz; iş varsa çıkış kodu 1
#                                  #  (gonder.sh bunu kullanır)
# ══════════════════════════════════════════════════════════════════════
set -uo pipefail
cd "$(dirname "$0")" || exit 1

KIP="${1:-rapor}"
case "$KIP" in rapor|--uygula|--kontrol) ;; *)
    echo "KULLANIM: ./yerlestir.sh [--uygula | --kontrol]"; exit 2 ;;
esac

# Dosyanın "tazelik" zamanı (saniye). Değiştirilmiş ya da git'te
# olmayan dosya için dosya saati; temiz dosya için son commit saati.
# (git clone/pull dosya saatlerini checkout anına çeker, o yüzden
# temiz dosyada dosya saatine güvenilmez.)
tazelik() {
    local f="$1"
    if [ -n "$(git status --porcelain -- "$f" 2>/dev/null)" ]; then
        stat -c %Y "$f"
    else
        local t
        t=$(git log -1 --format=%ct -- "$f" 2>/dev/null)
        [ -n "$t" ] && echo "$t" || stat -c %Y "$f"
    fi
}

hedef_bul() {
    local f="$1"
    case "$f" in
        *.html)    echo "templates/$f"; return ;;
        test_*.py) echo "tests/$f"; return ;;
    esac
    if [[ "$f" == *.py ]]; then
        if [ -f "blueprints/$f" ]; then echo "blueprints/$f"; return; fi
        if [ -f "migrations/versions/$f" ]; then echo "migrations/versions/$f"; return; fi
        if grep -qE '^down_revision\s*=' "$f" 2>/dev/null; then
            echo "migrations/versions/$f"; return
        fi
    fi
    echo ""
}

IS=0
for f in *; do
    [ -f "$f" ] || continue
    case "$f" in *.html|*.py) ;; *) continue ;; esac
    h=$(hedef_bul "$f")
    [ -n "$h" ] || continue

    if [ ! -f "$h" ]; then
        islem="TAŞI      $f → $h"
        eylem() { mkdir -p "$(dirname "$h")" && mv -f "$f" "$h"; }
    elif cmp -s "$f" "$h"; then
        islem="SİL       $f   (${h} ile birebir aynı)"
        eylem() { rm -f "$f"; }
    else
        tf=$(tazelik "$f"); th=$(tazelik "$h")
        if [ "$tf" -gt "$th" ]; then
            islem="ÜZERİNE   $f → $h   (ana dizindeki daha yeni)"
            eylem() { mv -f "$f" "$h"; }
        else
            islem="SİL       $f   (eski kopya; güncel olan $h)"
            eylem() { rm -f "$f"; }
        fi
    fi

    IS=$((IS + 1))
    case "$KIP" in
        --kontrol) ;;
        --uygula)  if eylem; then echo " ✓ $islem"; else echo " ✗ $islem — BAŞARISIZ"; fi ;;
        *)         echo "   $islem" ;;
    esac
done

if [ "$KIP" = "--kontrol" ]; then
    [ "$IS" -eq 0 ] && exit 0 || exit 1
fi

echo
if [ "$IS" -eq 0 ]; then
    echo " ✓ Yerinde olmayan dosya yok."
elif [ "$KIP" = "rapor" ]; then
    echo " $IS dosya. Uygulamak için:  ./yerlestir.sh --uygula"
else
    echo " $IS dosya yerleştirildi. Sonra: sudo systemctl restart milestone-erp"
fi

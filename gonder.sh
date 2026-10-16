#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — GÖNDER
#
#  Yedek al → denetimleri çalıştır → commit → push
#
#  DENETİMLER ENGELLEYİCİDİR: biri bulgu verirse push YAPILMAZ.
#  Amaç, bozuk kodun depoya girmesini önlemek. Denetimi geçmek
#  istiyorsanız önce bulguyu düzeltin ya da ilgili aracın
#  BEKLENEN_* listesine GEREKÇESİYLE yazın.
#
#  KULLANIM:
#      ./gonder.sh "commit mesaji"
#      ./gonder.sh "mesaj" --atla      # denetimleri atla (acil durum)
# ══════════════════════════════════════════════════════════════════════
set -uo pipefail
cd "$(dirname "$0")" || exit 1

# ── PYTHON YORUMLAYICI ──
# venv yoksa her yama "uygulanmamış" görünür ve rapor SESSİZCE
# yanlış olur. Bulunamazsa durulur.
if   [ -x venv/bin/python ];   then PY=venv/bin/python
elif [ -x .venv/bin/python ];  then PY=.venv/bin/python
elif [ -x /home/claude/venv/bin/python ]; then PY=/home/claude/venv/bin/python
else
    echo " ✗ Python sanal ortamı bulunamadı (venv/bin/python)."
    echo "   Betik doğru rapor veremez; çalışmayı reddediyorum."
    exit 1
fi

MESAJ="${1:-}"
ATLA="${2:-}"

if [ -z "$MESAJ" ]; then
    echo "KULLANIM: ./gonder.sh \"commit mesaji\""
    echo
    echo "Mesaj ZORUNLU. 'guncelleme' gibi bir mesaj altı ay sonra"
    echo "hiçbir şey anlatmaz; ne değişti ve NEDEN değişti yazın."
    exit 1
fi

cizgi() { printf '%.0s─' {1..70}; echo; }
baslik() { echo; cizgi; echo " $1"; cizgi; }

# ── DOSYA YERLEŞİMİ (YR1) ──
# 19.09: excel_import.py blueprints/ yerine ana dizine kopyalandı ve
# push edildi. Sistem ESKİ sürümü kullanmaya devam etti, hiçbir
# denetim fark etmedi. Yanlış yerdeki dosya varsa push yapılmaz.
if [ -x ./yerlestir.sh ] && ! ./yerlestir.sh --kontrol; then
    echo
    echo " ✗ Ana dizinde yanlış yere kopyalanmış dosya var — push İPTAL."
    echo
    ./yerlestir.sh | sed '/Uygulamak için/d'
    echo
    echo "   Düzeltmek için:  ./yerlestir.sh --uygula"
    echo "   sonra:           sudo systemctl restart milestone-erp"
    echo "   ve tekrar:       ./gonder.sh \"$MESAJ\""
    exit 1
fi

baslik "1/5 · YEDEK"
if [ -x /usr/local/bin/milestone-yedek.sh ]; then
    sudo /usr/local/bin/milestone-yedek.sh || {
        echo " ✗ Yedek alınamadı — push İPTAL."
        exit 1; }
else
    echo " ⚠ milestone-yedek.sh bulunamadı, yedek atlandı."
fi

baslik "2/5 · DENETİMLER"
if [ "$ATLA" = "--atla" ]; then
    echo " ⚠ ATLANDI (--atla). Bozuk kod push edilebilir."
else
    # "BULGU VAR" ile "ÇALIŞTIRILAMADI" AYRI şeylerdir.
    #   · Bulgu     → kodda sorun var, push ENGELLENİR.
    #   · Çalışmadı → ortam sorunu (veritabanı yok, bağımlılık eksik).
    #                 Engellemek yanlış olur; ama SESSİZ de geçilmez.
    HATA=0
    UYARI=0
    # TZ1: firma_denetim eklendi. Çoklu firmanın tek dayanağı her
    # sorgunun aktif firmaya süzülmesi; süzgeç de damga da otomatik
    # ve otomatik olan şey SESSİZ bozulur. Mixin'i almayan bir
    # model tüm firmalarda görünür ve hiçbir hata vermez.
    for D in js_denetim form_denetim zincir_denetim akis_denetim sema_denetim firma_denetim; do
        [ -f "$D.py" ] || continue
        printf "  %-18s " "$D"
        CIKTI=$("$PY" "$D.py" 2>&1); KOD=$?
        # ── TZ1: ESAS SİNYAL ÇIKIŞ KODU ──
        # Eski sürüm başarıyı METİNDE KELİME ARAYARAK ölçüyordu
        # ("TEMİZ|temiz$|uyumlu"). Bu tasarım bir kez çoktan
        # patladı: sema_denetim "Şema modellerle uyumlu" diyor,
        # kelime listesinde yoktu ve iki tur boyunca
        # "çalıştırılamadı" sanıldı — "şema doğrulanmadı" diye
        # uyardık, oysa doğrulanmıştı.
        #
        # Çare kelime eklemek değil: her denetim aracı çıkış kodunu
        # DOĞRU veriyor (0 temiz / 1 bulgu) — altısında da ölçüldü.
        # Metne yalnızca ÇÖKTÜ mü BULDU mu ayrımı için bakılıyor;
        # ikisi ayrı şeydir:
        #   · Bulgu     → kodda sorun var, push ENGELLENİR.
        #   · Çöktü     → ortam sorunu (veritabanı yok, modül
        #                 eksik). Engellemek yanlış olur; ama
        #                 SESSİZ de geçilmez.
        if [ "$KOD" -eq 0 ]; then
            echo "temiz"
        elif echo "$CIKTI" | grep -qE "Traceback \(most recent|^HATA:|ModuleNotFoundError|No module named|OperationalError|could not connect"; then
            echo "⚠ çalıştırılamadı (ortam)"
            UYARI=1
        else
            echo "✗ BULGU"
            HATA=1
        fi
    done
    if [ "$UYARI" -ne 0 ]; then
        echo
        echo " ⚠ Bir denetim ÇALIŞTIRILAMADI (büyük olasılıkla veritabanı"
        echo "   bağlantısı yok). Bu bir kod bulgusu değil, push engellenmiyor"
        echo "   — ama o denetim bu turda YAPILMADI, bilerek devam edin."
    fi
    if [ "$HATA" -ne 0 ]; then
        echo
        echo " ✗ Denetim bulgusu var — push YAPILMADI."
        echo "   Ayrıntı için ilgili aracı tek başına çalıştırın."
        echo "   Bulgu kasıtlıysa BEKLENEN_* listesine gerekçesiyle yazın."
        echo "   Gerçekten acilse: ./gonder.sh \"mesaj\" --atla"
        exit 1
    fi
fi

baslik "3/5 · DEĞİŞENLER"
git status --short
DEGISEN=$(git status --porcelain | wc -l)
if [ "$DEGISEN" -eq 0 ]; then
    echo " Değişiklik yok — push edilecek bir şey yok."
    exit 0
fi
echo
git diff --stat | tail -12

baslik "4/5 · COMMIT"
# Yedek ve derleme artıkları ASLA eklenmez.
# `git add -A -- ':!...'` sozdizimi bazi git surumlerinde
# "Unimplemented pathspec magic" hatasi veriyor; once hepsini
# ekleyip sonra reset etmek her surumde calisiyor.
git add -A
# TZ1: '*.yedek_*' eklendi (ALT ÇİZGİ). .gitignore onu zaten yok
# sayıyor, yani sızmıyordu; ama bu liste "neyi bilerek dışarıda
# tutuyoruz"un okunur kaydı ve iki desenden birini atlamış olması
# okuyana yanlış bilgi veriyordu.
for DESEN in '*.yedek-*' '*.yedek_*' '__pycache__/*' '__pycache__' '*.pyc' '*.db' '.env' 'venv'; do
    git reset -q -- "$DESEN" 2>/dev/null || true
done

EKLENEN=$(git diff --cached --name-only | wc -l)
if [ "$EKLENEN" -eq 0 ]; then
    echo " Eklenecek dosya yok (hepsi yoksayılmış olabilir)."
    exit 0
fi
echo " $EKLENEN dosya hazırlandı:"
git diff --cached --name-only | sed 's/^/   /'

git commit -m "$MESAJ" || { echo " ✗ Commit başarısız."; exit 1; }

baslik "5/5 · PUSH"
git push || { echo " ✗ Push başarısız."; exit 1; }

echo
cizgi
echo " ✓ GÖNDERİLDİ"
git log --oneline -1 | sed 's/^/   /'
echo
echo " Uygulanmış yama betiklerini temizlemek için:  ./temizle.sh"
cizgi

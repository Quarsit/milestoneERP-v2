#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — TEMİZLE
#
#  Uygulanmış yama betiklerini depodan ve diskten kaldırır,
#  yedek dosyalarını siler.
#
#  ── EN ÖNEMLİ KURAL ──
#    UYGULANMAMIŞ BİR YAMA SİLİNMEZ.
#
#    Her yama rapor kipinde çalıştırılır. Yalnızca "Zaten uygulanmış"
#    diyenler silinir. Diğerleri DURUR ve uyarı verilir.
#
#    Sebebi: bu proje yarım uygulanmış yama gördü (CRM-D: models.py
#    yamalanmış, flask_app.py atlanmıştı). Körü körüne silmek
#    uygulanmamış bir düzeltmeyi sessizce kaybetmek olurdu.
#
#  ── KALICI ARAÇLAR SİLİNMEZ ──
#    *_denetim.py, *_teshis.py, sifirla*.py, goc.py — bunlar tekrar
#    çalıştırılabilir araçlar, `yama_` desenine uymuyorlar.
#
#  KULLANIM:
#      ./temizle.sh            # RAPOR — hiçbir şey silinmez
#      ./temizle.sh --uygula   # siler, commit eder, push eder
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

UYGULA="${1:-}"
cizgi() { printf '%.0s─' {1..70}; echo; }

echo "══════════════════════════════════════════════════════════════════════"
echo " MILESTONE ERP — TEMİZLİK"
echo "══════════════════════════════════════════════════════════════════════"
echo

SILINECEK=()
KALACAK=()
ASILMIS=()

# ── COMMIT EDİLMEMİŞ DEĞİŞİKLİK KORUMASI ──
# Bu betik gonder.sh'nin BAŞARIYLA çalıştığını varsayıyordu.
# Üretimde gonder.sh izin hatası verdi, temizlik yine de çalıştı
# ve HİÇ COMMIT EDİLMEMİŞ bir yamayı sildi: etkisi flask_app.py'de
# kaldı ama gerekçesini anlatan betik depoya hiç girmeden kayboldu.
#
# Artık depoda bekleyen değişiklik varsa silme YAPILMAZ.
if [ -d .git ] && [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    echo "══════════════════════════════════════════════════════════════════════"
    echo " ✗ COMMIT EDİLMEMİŞ DEĞİŞİKLİK VAR — temizlik YAPILMADI"
    echo "══════════════════════════════════════════════════════════════════════"
    echo
    git status --short | sed 's/^/   /'
    echo
    echo "   Yamaları silmek, henüz push edilmemiş bir düzeltmenin"
    echo "   gerekçesini kaybetmek olurdu. Önce gönderin:"
    echo
    echo "     ./gonder.sh \"ne degisti ve neden\""
    echo
    echo "   Sonra tekrar:  ./temizle.sh --uygula"
    echo "══════════════════════════════════════════════════════════════════════"
    exit 1
fi

shopt -s nullglob
YAMALAR=(yama_*.py)
shopt -u nullglob

if [ ${#YAMALAR[@]} -eq 0 ]; then
    echo " Yama betiği yok."
else
    cizgi
    echo " YAMA DURUMU"
    cizgi
    for Y in "${YAMALAR[@]}"; do
        CIKTI=$("$PY" "$Y" 2>&1)
        if echo "$CIKTI" | grep -q "Zaten uygulanmış"; then
            printf "   ✓ %-34s uygulanmış → silinecek\n" "$Y"
            SILINECEK+=("$Y")
        elif echo "$CIKTI" | grep -qE "bağlantılar çalışır durumda|Üç şablon da yerinde"; then
            printf "   ✓ %-34s doğrulandı → silinecek\n" "$Y"
            SILINECEK+=("$Y")
        elif echo "$CIKTI" | grep -q "atlandı (zaten var)"; then
            # AŞILMIŞ YAMA: blokların bir kısmı "zaten var" diyor ama
            # biri bulunamıyor. Tipik sebep, SONRAKİ bir yamanın bu
            # yamanın çıktısını değiştirmesi — örn. CRM-G, CRM-F'nin
            # menü satırını Finans'tan Satış'a taşıdı ve F artık kendi
            # imzasını bulamıyor.
            #
            # Uygulanmamış DEĞİL, aşılmış. Yine de otomatik silinmiyor:
            # karar kullanıcının.
            printf "   ↷ %-34s AŞILMIŞ (sonraki yama değiştirmiş)\n" "$Y"
            ASILMIS+=("$Y")
        else
            printf "   ⚠ %-34s UYGULANMAMIŞ → korunuyor\n" "$Y"
            KALACAK+=("$Y")
        fi
    done
fi

echo
if [ ${#ASILMIS[@]} -gt 0 ]; then
    cizgi
    echo " ↷ AŞILMIŞ YAMA(LAR)"
    cizgi
    echo "   Blokların bir kısmı uygulanmış görünüyor ama bir çapa"
    echo "   bulunamıyor — büyük olasılıkla SONRAKİ bir yama bu yamanın"
    echo "   çıktısını değiştirdi. Uygulanmamış değil, aşılmış."
    echo
    echo "   Doğrulayın (çoğu blok 'atlandı' diyorsa aşılmıştır):"
    for Y in "${ASILMIS[@]}"; do
        echo "     $PY $Y"
    done
    echo
    echo "   Aşılmışsa elle silin:"
    for Y in "${ASILMIS[@]}"; do
        echo "     git rm --cached $Y 2>/dev/null; rm -f $Y"
    done
    echo
fi

if [ ${#KALACAK[@]} -gt 0 ]; then
    cizgi
    echo " ⚠ UYGULANMAMIŞ YAMA VAR — SİLİNMEYECEK"
    cizgi
    echo "   Bunlar henüz uygulanmamış görünüyor. Silmek, düzeltmeyi"
    echo "   kaybetmek olurdu. Önce uygulayın:"
    for Y in "${KALACAK[@]}"; do
        echo "     $PY $Y --uygula"
    done
    echo
fi

shopt -s nullglob
YEDEKLER=(*.yedek-* templates/*.yedek-*)
shopt -u nullglob
echo " Yedek dosyası     : ${#YEDEKLER[@]}"
echo " Silinecek yama    : ${#SILINECEK[@]}"
echo " Aşılmış yama      : ${#ASILMIS[@]}"
echo " Korunacak yama    : ${#KALACAK[@]}"

if [ ${#SILINECEK[@]} -eq 0 ] && [ ${#YEDEKLER[@]} -eq 0 ]; then
    echo
    echo " ✓ Zaten temiz — yapılacak iş yok."
    exit 0
fi

if [ "$UYGULA" != "--uygula" ]; then
    echo
    echo "══════════════════════════════════════════════════════════════════════"
    echo " RAPOR MODU — hiçbir şey silinmedi."
    echo
    echo " Silmek için:  ./temizle.sh --uygula"
    echo "══════════════════════════════════════════════════════════════════════"
    exit 0
fi

echo
cizgi
echo " SİLİNİYOR"
cizgi

if [ ${#SILINECEK[@]} -gt 0 ]; then
    # Depoda izleniyorsa önce oradan çıkar.
    for Y in "${SILINECEK[@]}"; do
        if git ls-files --error-unmatch "$Y" >/dev/null 2>&1; then
            git rm --cached -q "$Y"
        fi
        rm -f "$Y"
        echo "   $Y"
    done
    if ! git diff --cached --quiet; then
        git commit -q -m "temizlik: uygulanmis yama betikleri kaldirildi" \
            && git push -q \
            && echo "   → commit + push tamam"
    fi
fi

if [ ${#YEDEKLER[@]} -gt 0 ]; then
    rm -f -- "${YEDEKLER[@]}"
    echo "   ${#YEDEKLER[@]} yedek dosyası silindi"
fi

echo
echo "══════════════════════════════════════════════════════════════════════"
echo " ✓ TEMİZLİK TAMAMLANDI"
if [ ${#KALACAK[@]} -gt 0 ]; then
    echo
    echo " ⚠ ${#KALACAK[@]} uygulanmamış yama KORUNDU (yukarıda listelendi)."
fi
if [ ${#ASILMIS[@]} -gt 0 ]; then
    echo
    echo " ↷ ${#ASILMIS[@]} aşılmış yama KORUNDU — doğrulayıp elle silin."
fi
echo "══════════════════════════════════════════════════════════════════════"

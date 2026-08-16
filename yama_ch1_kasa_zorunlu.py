#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — TAHSİLAT/ÖDEMEDE KASA ZORUNLU  ·  CH1
#
#  ── SORUN ──
#    Cari hesaba 'Tahsilat' / 'Ödeme' girilirken kasa seçmek zorunlu
#    değildi ve formun VARSAYILAN seçeneği boştu. Forma dokunmadan
#    kaydeden herkes parayı kaybediyordu: cari bakiyesi değişiyor,
#    hiçbir kasaya para girmiyor/çıkmıyor.
#
#    Üretimde ölçüldü: üç tahsilat/ödeme kaydından biri (25.341 USD)
#    hiçbir kasaya bağlı değildi.
#
#  ── NEDEN SUNUCU TARAFI ──
#    Ekranda varsayılanı düzeltmek ve onay sormak yeterli değil:
#    kural yalnızca tarayıcıda yaşarsa API'ye doğrudan gelen istek
#    ya da ileride yazılacak başka bir ekran onu atlar. Veri
#    bütünlüğü kuralları sunucuda durmalı.
#
#  ── KAÇIŞ YOLU YOK, KASITLI ──
#    Para takip edilmeyen bir hesaba geliyorsa doğru çözüm o hesabı
#    KASA olarak tanımlamaktır — "hiçbir yere girmedi" demek değil.
#    Böylece kasa defteri ve nakit akışı bütün parayı görür.
#
#  ── ETKİ ──
#    Yalnızca yeni kayıtlar. Mevcut kasasız kayıtlar olduğu gibi
#    kalır; tahsilat_kasa_teshis.py ile bulunup elle düzeltilmeli.
#
#  KULLANIM (proje klasöründe):
#      python yama_ch1_kasa_zorunlu.py            # rapor
#      python yama_ch1_kasa_zorunlu.py --uygula
#
#  ⚠ templates/cari.html'in GÜNCEL sürümü de kopyalanmalı.
#  Şema değişikliği YOK.
# ══════════════════════════════════════════════════════════════════════
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
APP = Path('flask_app.py')

if not APP.exists():
    print("HATA: flask_app.py bu klasörde yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

ESKI = """        islem_tutar = q3(float(data.get('tutar') or data.get('borc') or data.get('alacak') or 0))"""

YENI = '''        islem_tutar = q3(float(data.get('tutar') or data.get('borc') or data.get('alacak') or 0))

        # ── TAHSILAT/ODEMEDE KASA ZORUNLU ──
        # Bu tipler tanimi geregi "para el degistirdi" demek. Nereye
        # gittigi soylenmezse cari bakiyesi degisir ama para hicbir
        # kasada gorunmez — iki ekran arasinda kaybolur.
        #
        # Kural SUNUCUDA: yalnizca formda dursaydi API'ye dogrudan
        # gelen istek ya da baska bir ekran onu atlardi.
        #
        # Takip edilmeyen bir banka hesabi varsa cozum onu KASA
        # olarak tanimlamaktir; "hicbir yere girmedi" demek degil.
        KASA_ZORUNLU_TIPLER = ('Tahsilat', 'Odeme', 'Ödeme',
                               'Avans Tahsilati', 'Avans Tahsilatı',
                               'Avans Odemesi', 'Avans Ödemesi')
        if islem_tip in KASA_ZORUNLU_TIPLER and not data.get('kasa_id'):
            return jsonify({
                'ok': False,
                'mesaj': f'{islem_tip} kaydında kasa seçimi zorunludur. '
                         'Seçilmezse cari bakiyesi değişir ama para hiçbir '
                         'kasaya girmez/çıkmaz. Para takip etmediğiniz bir '
                         'hesaba geldiyse önce o hesabı kasa olarak tanımlayın.'
            }), 400'''

IMZA = 'KASA_ZORUNLU_TIPLER = ('

print("═" * 70)
print(" CH1 · TAHSİLAT/ÖDEMEDE KASA ZORUNLU")
print("═" * 70)
print()

ham = APP.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


if uyarla(IMZA) in ham or IMZA in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

e = uyarla(ESKI)
adet = ham.count(e)
if adet != 1:
    print(f" ✗ Kalıp {adet} kez bulundu (1 bekleniyordu). DOSYAYA DOKUNULMADI.")
    sys.exit(1)

icerik = ham.replace(e, uyarla(YENI), 1)

try:
    compile(icerik, 'flask_app.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print("  ✓ uygulanacak          kasa zorunluluğu (sunucu tarafı)")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_ch1_kasa_zorunlu.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = APP.with_name(f'flask_app.py.yedek-{damga}')
shutil.copy2(APP, yedek)
APP.write_bytes(icerik.encode('utf-8'))
print()
print(f" ✓ flask_app.py  (yedek: {yedek.name})")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print(" ⚠ MEVCUT kasasız kayıtlar düzelmez — elle düzeltin:")
print("     venv/bin/python tahsilat_kasa_teshis.py")
print("═" * 70)

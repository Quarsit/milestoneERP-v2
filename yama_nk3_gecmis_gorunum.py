#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — GEÇMİŞ GÖRÜNÜMÜ  ·  NK3
#
#  ── İHTİYAÇ ──
#    Sabit gider sürümlemesi (SG1) geçmiş tutarları koruyor ama
#    ekranda görülemiyordu: /nakit her zaman BUGÜNDEN başlıyor,
#    `baslangic` parametresi API'de var, arayüz hiç göndermiyor.
#
#  ── TUZAK ──
#    Ekrana düz bir tarih seçici koymak YANLIŞ KÜMÜLATİF üretir.
#    Ölçüldü (bugünkü kasa 1.000.000, Nisan'dan beri aylık 1.000 kira):
#
#        2026-04  çıkış 1.000  kümülatif   999.000
#        2026-05  çıkış 1.000  kümülatif   998.000
#        ...
#
#    Oysa Nisan–Ağustos ödemeleri ZATEN yapıldı ve bugünkü
#    1.000.000 bakiyeye yansıdı. Kümülatiften bir daha düşülüyor —
#    yani geçmiş iki kez sayılıyor. Bu, oturum boyunca düzelttiğimiz
#    hataların aynı sınıfı.
#
#  ── ÇÖZÜM ──
#    Geçmiş dönemler GÖSTERİLİR ama kümülatife KATILMAZ:
#      · dönem bugünden önce bitiyorsa  gecmis=True
#      · kümülatif None döner (ekranda "—")
#      · yürüyen bakiye bu dönemlerde İLERLEMEZ
#    Kümülatif, açılış bakiyesinden bugünkü dönemde başlar.
#
#    Böylece geçmiş "ne olmuştu" bilgisi olarak okunur, nakit
#    planlaması ise bugünden ileriye doğru bozulmadan çalışır.
#
#  ── VARSAYILAN DEĞİŞMİYOR ──
#    baslangic verilmezse bugünden başlar; hiçbir dönem geçmiş
#    sayılmaz ve davranış eskisiyle birebir aynı kalır.
#
#  KULLANIM (proje klasöründe):
#      python yama_nk3_gecmis_gorunum.py            # rapor
#      python yama_nk3_gecmis_gorunum.py --uygula
#
#  ⚠ templates/nakit.html'in GÜNCEL sürümü de kopyalanmalı.
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

if '_nakit_projeksiyon' not in APP.read_text(encoding='utf-8', errors='replace'):
    print("✗ ÖN KOŞUL: nakit akışı modülü kurulu değil.")
    sys.exit(1)

ESKI = """        yurur = dict(acilis)
        sirali = []
        for a in sorted(donemler.keys()):
            satir = {'donem': a, 'dovizler': {}}
            for d in sorted(set(list(donemler[a].keys()) + list(yurur.keys()))):
                s = donemler[a].get(d, {'giris': 0.0, 'cikis': 0.0, 'kalemler': []})
                net = q3(s['giris'] - s['cikis'])
                yurur[d] = q3(float(yurur.get(d, 0)) + float(net))
                satir['dovizler'][d] = {
                    'giris': q3(s['giris']), 'cikis': q3(s['cikis']),
                    'net': net, 'kumulatif': yurur[d],
                    'kalem_sayisi': len(s['kalemler']),
                    'kalemler': sorted(s['kalemler'], key=lambda x: x['tarih'])[:40],
                }
            sirali.append(satir)"""

YENI = '''        def _donem_bitisi(anahtar):
            """Donemin SON gunu — gecmis mi diye bakmak icin."""
            import calendar as _cal
            if kirilim == 'ay':
                _y, _a = (int(x) for x in anahtar.split('-'))
                return date(_y, _a, _cal.monthrange(_y, _a)[1])
            _t = date.fromisoformat(anahtar)
            return _t + timedelta(days=6) if kirilim == 'hafta' else _t

        _bugun = date.today()
        yurur = dict(acilis)
        sirali = []
        for a in sorted(donemler.keys()):
            # GECMIS DONEM: bugunden once bitmis.
            # Gosterilir ama kumulatife KATILMAZ — o donemdeki para
            # hareketleri zaten gerceklesti ve bugunku kasa
            # bakiyesine (acilis) yansidi. Kumulatiften bir daha
            # dusmek geçmisi IKI KEZ saymak olurdu.
            # DIKKAT: `gecmis` adi disaridaki "vadesi gecmis kalemler"
            # listesine ait. Ayni adi kullanmak onu ezerdi.
            _gd = _donem_bitisi(a) < _bugun
            satir = {'donem': a, 'gecmis': _gd, 'dovizler': {}}
            for d in sorted(set(list(donemler[a].keys()) + list(yurur.keys()))):
                s = donemler[a].get(d, {'giris': 0.0, 'cikis': 0.0, 'kalemler': []})
                net = q3(s['giris'] - s['cikis'])
                if _gd:
                    kum = None            # ekranda "—"
                else:
                    yurur[d] = q3(float(yurur.get(d, 0)) + float(net))
                    kum = yurur[d]
                satir['dovizler'][d] = {
                    'giris': q3(s['giris']), 'cikis': q3(s['cikis']),
                    'net': net, 'kumulatif': kum, 'gecmis': _gd,
                    'kalem_sayisi': len(s['kalemler']),
                    'kalemler': sorted(s['kalemler'], key=lambda x: x['tarih'])[:40],
                }
            sirali.append(satir)'''

# ══ B) Dışa aktarma: kumulatif artık None olabilir ═════════════════
#  NA4'un kritik donem tespiti `kumulatif < 0` kiyaslamasi yapiyordu.
#  Gecmis donemlerde kumulatif None dondugu icin bu satir TypeError
#  firlatiyor ve TUM nakit disa aktarmasi 500 veriyor.
B_ESKI = """                kritik = next((s for s in p['donemler']
                               if (s['dovizler'].get(dv) or {}).get('kumulatif', 0) < 0), None)"""

B_YENI = """                # Gecmis donemlerin kumulatifi None — kiyaslamadan ONCE
                # elenmeli, yoksa TypeError ile tum cikti 500 verir.
                def _kritik_mi(s):
                    v = s['dovizler'].get(dv) or {}
                    k = v.get('kumulatif')
                    return (not v.get('gecmis')) and k is not None and k < 0

                kritik = next((s for s in p['donemler'] if _kritik_mi(s)), None)"""

# ══ C) Dışa aktarmada geçmiş dönem işaretlensin ════════════════════
C_ESKI = """                        rows.append([dv, _nakit_donem_adi(s['donem'], kirilim),"""
C_YENI = """                        _et = ' (geçmiş)' if s.get('gecmis') else ''
                        rows.append([dv, _nakit_donem_adi(s['donem'], kirilim) + _et,"""

IMZA = "GECMIS DONEM: bugunden once bitmis"

print("═" * 70)
print(" NK3 · GEÇMİŞ GÖRÜNÜMÜ — kümülatifi bozmadan")
print("═" * 70)
print()

ham = APP.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


if uyarla(IMZA) in ham or IMZA in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

icerik = ham
for _ad, _e, _y in (("projeksiyon", ESKI, YENI),
                    ("dışa aktarma · kritik dönem", B_ESKI, B_YENI),
                    ("dışa aktarma · geçmiş etiketi", C_ESKI, C_YENI)):
    _ee = uyarla(_e)
    _n = icerik.count(_ee)
    if _n != 1:
        print(f" ✗ KALIP BULUNAMADI: {_ad} (eşleşme: {_n}). DOSYAYA DOKUNULMADI.")
        sys.exit(1)
    icerik = icerik.replace(_ee, uyarla(_y), 1)

try:
    compile(icerik, 'flask_app.py', 'exec')
except SyntaxError as exc:
    print(f" ✗ SÖZDİZİMİ HATASI → satır {exc.lineno}: {exc.msg}")
    print(" DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print("  ✓ uygulanacak          geçmiş dönem işareti + kümülatif koruması")
print("  ✓ uygulanacak          dışa aktarma None güvenliği + geçmiş etiketi")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_nk3_gecmis_gorunum.py --uygula")
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
print(" ⚠ templates/nakit.html'in GÜNCEL sürümünü de kopyalayın.")
print("═" * 70)

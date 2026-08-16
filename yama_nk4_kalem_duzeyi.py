#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — NK3 DÜZELTMESİ  ·  NK4
#
#  ── ÖN KOŞUL ──
#      yama_nk3_gecmis_gorunum.py --uygula
#
#  ── HATA (NK3'te benim yaptığım) ──
#    NK3 "geçmiş" ayrımını DÖNEM düzeyinde kurdu:
#
#        gecmis = donem_bitisi < bugun
#
#    İçinde bulunduğumuz ay bugün bitmediği için "gelecek" sayılıyor
#    ve AYIN TAMAMI kümülatife giriyor — ayın başında çoktan ödenmiş
#    kalemler dahil.
#
#    Ölçüldü (bugün 15 Ağustos, kira ayın 5'inde ödeniyor):
#        Varsayılan görünüm : 5 Ağustos ödemesi hiç sayılmıyor  ✓
#        Geçmişli görünüm   : 2026-08 çıkış 11.000, küm. 989.000 ✗
#
#    O 11.000 kasadan çıktı ve açılış bakiyesine zaten yansıdı;
#    kümülatiften bir daha düşülüyor. Aynı görünümün iki farklı
#    cevap vermesi de ayrıca yanlış.
#
#  ── DÜZELTME ──
#    Ayrım KALEM düzeyine indi. Kümülatif yalnızca tarihi BUGÜN ve
#    sonrası olan kalemlerden hesaplanır. Ödenmiş kalemler ekranda
#    kalır (dönem toplamında görünür, detayda "ödendi" işaretlidir)
#    ama yürüyen bakiyeyi hareket ettirmez.
#
#    Böylece geçmişli görünüm ile varsayılan görünüm AYNI kümülatifi
#    üretir — tek fark, geçmişin ek bilgi olarak gösterilmesi.
#
#  ── VARSAYILAN DEĞİŞMİYOR ──
#    Bugünden başlatıldığında zaten geçmiş tarihli kalem üretilmiyor;
#    yeni hesap aynı sonucu verir.
#
#  KULLANIM (proje klasöründe):
#      python yama_nk4_kalem_duzeyi.py            # rapor
#      python yama_nk4_kalem_duzeyi.py --uygula
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

if 'GECMIS DONEM: bugunden once bitmis' not in APP.read_text(encoding='utf-8', errors='replace'):
    print("✗ ÖN KOŞUL: önce yama_nk3_gecmis_gorunum.py uygulanmalı.")
    sys.exit(1)

ESKI = """            _gd = _donem_bitisi(a) < _bugun
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
                }"""

YENI = '''            _gd = _donem_bitisi(a) < _bugun
            satir = {'donem': a, 'gecmis': _gd, 'dovizler': {}}
            for d in sorted(set(list(donemler[a].keys()) + list(yurur.keys()))):
                s = donemler[a].get(d, {'giris': 0.0, 'cikis': 0.0, 'kalemler': []})
                net = q3(s['giris'] - s['cikis'])

                # GERCEKLESMIS KALEMLER — tarihi bugunden ONCE olanlar.
                #
                # Icinde bulundugumuz ay "gecmis" sayilmaz (henuz
                # bitmedi) ama ayin basindaki odemeler coktan yapildi
                # ve acilis bakiyesine yansidi. Kumulatiften bir daha
                # dusmek onlari IKI KEZ saymak olur.
                #
                # Bu yuzden ayrim DONEM degil KALEM duzeyinde:
                # kumulatif yalnizca bugun ve sonrasindan hesaplanir.
                _bi = _bugun.isoformat()
                _gg = _cg = 0.0
                for _x in s['kalemler']:
                    _x['gerceklesmis'] = bool(_x['tarih'] and _x['tarih'] < _bi)
                    if not _x['gerceklesmis']:
                        continue
                    if _x['yon'] == 'giris':
                        _gg += float(_x['tutar'])
                    else:
                        _cg += float(_x['tutar'])

                net_bekleyen = q3((s['giris'] - _gg) - (s['cikis'] - _cg))
                if _gd:
                    kum = None            # ekranda "—"
                else:
                    yurur[d] = q3(float(yurur.get(d, 0)) + float(net_bekleyen))
                    kum = yurur[d]

                satir['dovizler'][d] = {
                    'giris': q3(s['giris']), 'cikis': q3(s['cikis']),
                    'net': net, 'kumulatif': kum, 'gecmis': _gd,
                    # Donem icinde COKTAN gerceklesmis kisim. Ekran
                    # bunu ayri gosterir; kumulatife katilmaz.
                    'gerceklesmis_giris': q3(_gg), 'gerceklesmis_cikis': q3(_cg),
                    'net_bekleyen': net_bekleyen,
                    'kalem_sayisi': len(s['kalemler']),
                    'kalemler': sorted(s['kalemler'], key=lambda x: x['tarih'])[:40],
                }'''

IMZA = "ayrim DONEM degil KALEM duzeyinde"

print("═" * 70)
print(" NK4 · NK3 DÜZELTMESİ — kalem düzeyinde geçmiş ayrımı")
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

print("  ✓ uygulanacak          kümülatif artık kalem tarihine bakıyor")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_nk4_kalem_duzeyi.py --uygula")
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
print(" Geçmişli görünüm ile varsayılan görünüm artık AYNI")
print(" kümülatifi veriyor.")
print("═" * 70)

#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — CARİ HAREKET GÜNCELLEME KORUMASI  ·  CH2
#
#  ── ÖLÇÜLEN İKİ AÇIK ──
#
#    1) SİLME KORUMALI, GÜNCELLEME DEĞİL
#       DELETE, faturanin otomatik borc hareketini korur:
#         "Bu hareket FT-1 faturasinin otomatik borc kaydi." -> 400
#       Ama PUT ayni kaydi serbestce degistiriyordu. Olculdu:
#         PUT {"borc": 0}  -> HTTP 200, cari borc 0
#       Silmekle ayni sonuc, koruma yok. Fatura "Kesildi" gorunurken
#       musterinin borcu yok — DELETE korumasinin tam olarak
#       engellemek icin var oldugu sessiz tutarsizlik.
#
#    2) KÜTLESEL ATAMA
#         for key, val in data.items():
#             if hasattr(hareket, key): setattr(hareket, key, val)
#       Istemciden gelen HER alan adi dogrudan yaziliyor. Olculdu:
#         PUT {"kaynak":"HACK","kapatildi":true,
#              "cari_id":"BASKASI","doviz":"XXX"} -> hepsi yazildi
#
#       Her biri ayri bir zinciri bozar:
#         · cari_id  → hareket BASKA MUSTERIYE tasinir, D3 degismezligi
#                      kirilir
#         · kaynak   → nakit akisi siniflandirmasi bozulur; taninmayan
#                      kaynak SESSIZCE yok sayilir (NK5'te ogrendik)
#         · doviz    → kur hesaplari anlamsizlasir
#         · kapatildi→ stok silme korumasi ve kur farki hesabi etkilenir
#
#  ── EKRAN BU UCU KULLANMIYOR ──
#    Sablonlarda yalnizca DELETE cagriliyor; PUT hic kullanilmiyor.
#    Bu yuzden SIKI bir beyaz liste risksiz: mevcut hicbir ekran
#    bozulmaz.
#
#  ── DÜZELTME ──
#    · Beyaz liste: yalnizca aciklama, vade_tarihi, evrak_no,
#      belge_no, hareket_tarihi
#    · Faturanin otomatik borc kaydinda DELETE ile AYNI koruma
#    · Tutar/doviz/kaynak/cari_id degistirilemez — bunlar kaydin
#      kimligi; degistirilmesi gerekiyorsa hareket iptal edilip
#      yenisi acilmali
#    · Degisiklikler denetim kaydina yazilir
#
#  KULLANIM (proje klasöründe):
#      python yama_ch2_hareket_koruma.py            # rapor
#      python yama_ch2_hareket_koruma.py --uygula
#
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

ESKI = """        data = request.json
        for key, val in data.items():
            if key == 'vade_tarihi': val = _parse_date(val)
            if hasattr(hareket, key): setattr(hareket, key, val)
        db.session.commit()
        return jsonify({'ok': True})"""

YENI = '''        data = request.json or {}

        # ── FATURA KAYDI KORUMASI ──
        # DELETE bu kaydi koruyor ama PUT korumuyordu. Olculdu:
        # `PUT {"borc": 0}` cari borcu sifirliyordu — silmekle AYNI
        # sonuc. Fatura "Kesildi" gorunurken musterinin borcu yok.
        # Ayni koruma buraya da kondu.
        if (hareket.baglanti_tip == 'fatura' and hareket.kaynak == 'fatura'
                and (hareket.borc or 0) > 0):
            _f = Fatura.query.get(hareket.baglanti_id)
            _no = (_f.fatura_no or _f.id) if _f else hareket.baglanti_id
            return jsonify({
                'ok': False,
                'mesaj': f'Bu hareket {_no} faturasının otomatik borç kaydı; '
                         f'buradan değiştirilemez. Tutarı düzeltmek için '
                         f'faturayı iptal edip yeniden kesin.'}), 400

        # ── BEYAZ LİSTE ──
        # Onceden `for key, val in data.items(): setattr(...)` vardi
        # ve istemciden gelen HER alan yaziliyordu. Olculdu:
        # kaynak, kapatildi, cari_id ve doviz disaridan
        # degistirilebiliyordu.
        #
        # Asagidakiler DISARIDA birakildi, cunku kaydin KIMLIGINI
        # olusturuyorlar:
        #   cari_id  → degisirse hareket baska musteriye tasinir,
        #              D3 degismezligi kirilir
        #   borc/alacak/doviz/kur → tutar duzeltmesi iptal+yeniden
        #              giris ile yapilmali; sessizce degistirilirse
        #              kasa ve fatura ile ayrisir
        #   kaynak   → nakit akisi siniflandirmasi buna bagli;
        #              taninmayan kaynak SESSIZCE yok sayilir (NK5)
        #   kapatildi→ stok silme korumasi ve kur farki hesabi kullanir
        GUNCELLENEBILIR = ('aciklama', 'vade_tarihi', 'evrak_no',
                           'belge_no', 'hareket_tarihi')
        reddedilen = [k for k in data
                      if k not in GUNCELLENEBILIR and hasattr(hareket, k)]
        if reddedilen:
            return jsonify({
                'ok': False,
                'mesaj': f"Bu alanlar buradan değiştirilemez: "
                         f"{', '.join(sorted(reddedilen))}. "
                         f"Değiştirilebilir: {', '.join(GUNCELLENEBILIR)}."}), 400

        _eski = {}
        for key in GUNCELLENEBILIR:
            if key not in data:
                continue
            val = data[key]
            if key in ('vade_tarihi', 'hareket_tarihi'):
                val = _parse_date(val)
                if val is None and data[key]:
                    return jsonify({'ok': False,
                                    'mesaj': f'Geçersiz tarih: {key}'}), 400
            _onceki = getattr(hareket, key, None)
            if _onceki != val:
                _eski[key] = str(_onceki)
                setattr(hareket, key, val)

        if not _eski:
            return jsonify({'ok': True, 'mesaj': 'Değişiklik yok'})

        # DENETIM KAYDI — bu uc nokta hicbir iz birakmiyordu.
        try:
            db.session.add(AuditLog(
                kullanici=session.get('kullanici'),
                islem_tipi='GUNCELLEME', tablo_adi='cari_hareket',
                kayit_id=hareket.id,
                eski_veri=json.dumps(_eski, ensure_ascii=False),
                yeni_veri=json.dumps(
                    {k: str(getattr(hareket, k)) for k in _eski},
                    ensure_ascii=False)))
        except Exception as _e:
            app.logger.warning(f'Denetim kaydi yazilamadi: {_e}')

        ok, hata = _safe_commit(f'Cari hareket guncelleme: {hareket_id}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True, 'guncellenen': sorted(_eski)})'''

IMZA = 'GUNCELLENEBILIR = ('

print("═" * 70)
print(" CH2 · CARİ HAREKET GÜNCELLEME KORUMASI")
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

print("  ✓ uygulanacak          fatura kaydı koruması")
print("  ✓ uygulanacak          beyaz liste (5 alan)")
print("  ✓ uygulanacak          denetim kaydı")
print("  ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_ch2_hareket_koruma.py --uygula")
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
print("═" * 70)

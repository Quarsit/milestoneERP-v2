#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — DIŞA AKTARMA DÜZELTMESİ  ·  EX1
#
#  ── BELİRTİ ──
#    PDF çıktıları UZANTISIZ iniyor. Windows dosyayı tanıyamıyor,
#    Word ile açmaya çalışıyor, içerik bozuk görünüyor.
#
#  ── GERÇEK SEBEP ──
#    Dosya BOZUK DEĞİL — ilk dört baytı `%PDF`, geçerli bir PDF.
#    Sorun yalnızca dosya adında: uzantı yok.
#
#    `liste_pdf`in İKİ yolu var:
#      • WeasyPrint (birincil, logolu HTML şablonu)
#      • reportlab  (yedek, sade tablo)
#
#    reportlab yolu dosya adına '.pdf' EKLİYOR:
#        if not dosya_adi.endswith('.pdf'): dosya_adi += '.pdf'
#    WeasyPrint yolu EKLEMİYOR — unutulmuş:
#        return _make_response(pdf, dosya_adi, 'application/pdf')
#
#    Sunucuda (Pardus) WeasyPrint KURULU olduğu için hep birincil yol
#    çalışıyor → uzantı hiç eklenmiyor. WeasyPrint'in kurulu olmadığı
#    bir ortamda yedeğe düşülür ve sorun GÖRÜNMEZ; hatanın bu kadar
#    gec fark edilmesinin sebebi bu.
#
#    Ayrıca WeasyPrint yolu `inline` bayrağını da geçmiyordu; reportlab
#    yolu PDF'i tarayıcıda açarken (inline=True) birincil yol dosya
#    olarak indiriyordu. İki yol aynı isteğe farklı davranıyordu.
#
#  ── NEDEN _make_response İÇİNDE ÇÖZÜLDÜ ──
#    Uzantıyı her çağıranın kendisi eklemek zorunda olması, tam da bu
#    hatanın kaynağı. Tek yere alınınca hiçbir çağıran bir daha
#    unutamaz — bundan sonra eklenecek dışa aktarma modülleri de
#    otomatik doğru davranır.
#
#  ── ETKİ ──
#    TÜM dışa aktarma modülleri (fatura, çek, stok, cari, maliyet,
#    sevkiyat, nakit …). Yalnızca export_utils.py değişir.
#    Şema değişikliği YOK, API sözleşmesi değişmez.
#
#  KULLANIM (proje klasöründe):
#      python yama_ex1_pdf_uzanti.py            # rapor
#      python yama_ex1_pdf_uzanti.py --uygula   # uygula
# ══════════════════════════════════════════════════════════════════════
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
UTIL = Path('export_utils.py')
APP = Path('flask_app.py')

for _d in (UTIL, APP):
    if not _d.exists():
        print(f"HATA: {_d} bu klasörde yok. Proje klasöründe çalıştırın.")
        sys.exit(1)


def dogrula(kaynak, ad):
    try:
        compile(kaynak, ad, 'exec')
        return None
    except SyntaxError as exc:
        return f"satır {exc.lineno}: {exc.msg}"


# ══ A) Uzantıyı tek yerde garantile ════════════════════════════════
A_ESKI = '''def _make_response(data_bytes, dosya_adi, content_type, inline=False):
    from flask import make_response
    resp = make_response(data_bytes)
    resp.headers['Content-Type'] = content_type
    # inline=True → tarayıcıda aç (PDF için); inline=False → indir (Excel için)
    yerlesim = 'inline' if inline else 'attachment'
    resp.headers['Content-Disposition'] = f'{yerlesim}; filename="{dosya_adi}"'
    return resp'''

A_YENI = '''# Icerik tipi → dosya uzantisi. Uzanti burada, TEK YERDE ekleniyor.
# Onceden her cagiran kendisi eklemek zorundaydi; liste_pdf'in
# WeasyPrint yolu bunu unutmustu ve PDF'ler uzantisiz iniyordu.
# Windows dosyayi taniyamayip Word'e veriyor, icerik gecerli PDF
# oldugu halde "bozuk" gorunuyordu.
_UZANTILAR = {
    'application/pdf': '.pdf',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
    'text/csv': '.csv',
}


def _make_response(data_bytes, dosya_adi, content_type, inline=False):
    from flask import make_response
    resp = make_response(data_bytes)
    resp.headers['Content-Type'] = content_type

    dosya_adi = (dosya_adi or 'dosya').strip() or 'dosya'
    uzanti = _UZANTILAR.get((content_type or '').split(';')[0].strip().lower())
    if uzanti and not dosya_adi.lower().endswith(uzanti):
        dosya_adi += uzanti

    # inline=True → tarayıcıda aç (PDF için); inline=False → indir (Excel için)
    yerlesim = 'inline' if inline else 'attachment'

    # Dosya adinda ASCII disi karakter varsa (Turkce ad, firma unvani)
    # duz filename= basligi bazi tarayicilarda bozulur. RFC 6266/5987
    # geregi ASCII yedek + filename* birlikte veriliyor.
    ascii_ad = dosya_adi.encode('ascii', 'replace').decode('ascii').replace('?', '_')
    from urllib.parse import quote
    resp.headers['Content-Disposition'] = (
        f'{yerlesim}; filename="{ascii_ad}"; '
        f"filename*=UTF-8''{quote(dosya_adi)}")
    return resp'''

# ══ B) WeasyPrint yolu da reportlab gibi davransın ═════════════════
B_ESKI = """        return _make_response(pdf, dosya_adi, 'application/pdf')"""
B_YENI = """        # inline=True: reportlab yedegiyle AYNI davranis. Onceden
        # birincil yol dosya olarak indiriyor, yedek yol tarayicida
        # aciyordu — ayni istek, iki farkli sonuc.
        return _make_response(pdf, dosya_adi, 'application/pdf', inline=True)"""

# ══ C) "Aralık" etiketi ay adıyla karışıyor ════════════════════════
#  Nakit PDF'inin ozetinde "Aralık: 14.08.2026 – 16.02.2027" yaziyor;
#  hemen altindaki tabloda ise "TRY Aralık 2026" satiri var. Ayni
#  kelime bir yerde ZAMAN ARALIGI, bir yerde AY ADI. Turkce mali
#  raporda kafa karistirici — etiket netlestirildi.
#  (Yalnizca NA4 uygulanmissa var; yoksa sessizce atlanir.)
C_ESKI = """            ozet_satirlari.append(('Aralık',"""
C_YENI = """            ozet_satirlari.append(('Tarih aralığı',"""

BLOKLAR = [
    (UTIL, "uzantı garantisi (_make_response)", A_ESKI, A_YENI, '_UZANTILAR = {'),
    (UTIL, "WeasyPrint yolu inline",            B_ESKI, B_YENI, "'application/pdf', inline=True)\n\n    except"),
    (APP,  "özet etiketi: Aralık → Tarih aralığı", C_ESKI, C_YENI, "ozet_satirlari.append(('Tarih aralığı',"),
]

print("═" * 70)
print(" EX1 · DIŞA AKTARMA — PDF uzantısı düzeltmesi")
print("═" * 70)
print()

icerik, crlf = {}, {}
for yol in (UTIL, APP):
    _h = yol.read_bytes().decode('utf-8')
    icerik[yol] = _h
    crlf[yol] = '\r\n' in _h


def uyarla(t, yol):
    return t.replace('\n', '\r\n') if crlf[yol] else t


plan, atlanan, sorunlu = [], [], []
for yol, aciklama, eski, yeni, imza in BLOKLAR:
    metin = icerik[yol]
    if uyarla(imza, yol) in metin or imza in metin:
        atlanan.append(aciklama)
        continue
    e = uyarla(eski, yol)
    adet = metin.count(e)
    if adet == 0 and yol is APP:
        # NA4 uygulanmamis — bu blok gecerli degil, sorun degil.
        atlanan.append(f'{aciklama} (NA4 yok)')
        continue
    if adet != 1:
        sorunlu.append((aciklama, adet))
        continue
    icerik[yol] = metin.replace(e, uyarla(yeni, yol), 1)
    plan.append(aciklama)

for a in atlanan:
    print(f"  ↷ atlandı (zaten var)  {a}")
for a in plan:
    print(f"  ✓ uygulanacak          {a}")
for a, n in sorunlu:
    print(f"  ✗ KALIP BULUNAMADI     {a}  (eşleşme: {n})")

print()
if sorunlu:
    print(f" ✗ {len(sorunlu)} blok yerleştirilemedi — DOSYAYA DOKUNULMADI.")
    sys.exit(1)
if not plan:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

for yol in (UTIL, APP):
    hata = dogrula(icerik[yol], yol.name)
    if hata:
        print(f" ✗ {yol.name} SÖZDİZİMİ HATASI → {hata}")
        print(" HİÇBİR DOSYAYA DOKUNULMADI.")
        sys.exit(1)
print(" ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_ex1_pdf_uzanti.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
for yol in (UTIL, APP):
    if icerik[yol] == yol.read_bytes().decode('utf-8'):
        continue
    yedek = yol.with_name(f'{yol.name}.yedek-{damga}')
    shutil.copy2(yol, yedek)
    yol.write_bytes(icerik[yol].encode('utf-8'))
    print(f" ✓ {yol.name}")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print(" TÜM modüllerin PDF çıktısı artık '.pdf' uzantılı ve")
print(" tarayıcıda açılıyor. Excel çıktıları '.xlsx' olarak iniyor.")
print("═" * 70)

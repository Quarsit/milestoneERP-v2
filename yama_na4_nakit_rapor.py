#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — NAKİT AKIŞI  ·  NA4  (raporlama + dışa aktarma)
#
#  ── ÖN KOŞUL ──
#      yama_na1_nakit_model.py --uygula
#      goc.py uygula
#      yama_na2_projeksiyon.py --uygula
#      yama_na3_nakit_sayfa.py --uygula
#
#  ── NE YAPAR ──
#
#  1) HESABI TEK YERE TOPLAR
#     NA2'de projeksiyon hesabi dogrudan /api/nakit_akis'in govdesinde
#     duruyordu. Disa aktarma da ayni hesaba ihtiyac duyuyor. Kopyala-
#     yapistir yerine hesap `_nakit_projeksiyon()` fonksiyonuna
#     tasindi; API artik ince bir sarmalayici.
#
#     Bu SART: iki kopya olsaydi biri duzeltilip oteki unutuldugunda
#     ekranda gorunen rakamla Excel'e inen rakam sessizce ayrisirdi —
#     muhasebede en kotu hata turu.
#
#  2) UC YENİ DIŞA AKTARMA MODÜLÜ
#       /api/export/nakit         → donem donem projeksiyon ozeti
#       /api/export/nakit_detay   → kalem kalem tum hareketler
#       /api/export/sabit_gider   → sabit gider tanimlari
#     Ucu de hem Excel hem PDF (PDF logolu liste_print sablonuyla).
#
#  3) PDF'e ÖZET BLOĞU
#     `liste_pdf` zaten `ozet=` parametresi aliyordu ama genel
#     dagitici hic kullanmiyordu. Simdi `ozet_satirlari` degiskeni
#     eklendi — nakit ciktisinin basinda acilis bakiyeleri, kritik
#     donem uyarisi ve vadesi gecmis tutarlar gorunuyor. Diger
#     modullerde davranis degismiyor (bos liste → None).
#
#  ── YETKİ ──
#    /api/export/<modul> genel dagiticisi YALNIZCA oturum kontrolu
#    yapiyor, modul yetkisine BAKMIYOR (mevcut durum, bu yama onu
#    genel olarak degistirmiyor). Nakit ciktilari kasa bakiyelerini ve
#    tum borc/alacaklari icerdigi icin uc yeni modulun her birine
#    ACIK 'kasa' yetki kontrolu kondu.
#
#  KULLANIM (proje klasöründe):
#      python yama_na4_nakit_rapor.py            # rapor
#      python yama_na4_nakit_rapor.py --uygula   # uygula
#
#  ⚠ templates/nakit.html ve templates/sabit_gider.html'in GÜNCEL
#    sürümleri de kopyalanmali (Dışa Aktar düğmesi onlarda).
#
#  Şema değişikliği YOK.
# ══════════════════════════════════════════════════════════════════════
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
APP = Path('flask_app.py')
UTIL = Path('export_utils.py')

for _d in (APP, UTIL):
    if not _d.exists():
        print(f"HATA: {_d} bu klasörde yok. Proje klasöründe çalıştırın.")
        sys.exit(1)

_ham = APP.read_text(encoding='utf-8', errors='replace')
if 'api_nakit_akis' not in _ham:
    print("✗ ÖN KOŞUL: önce yama_na2_projeksiyon.py uygulanmalı.")
    sys.exit(1)
if 'def nakit_sayfa(' not in _ham:
    print("✗ ÖN KOŞUL: önce yama_na3_nakit_sayfa.py uygulanmalı.")
    sys.exit(1)


def dogrula(kaynak, ad):
    try:
        compile(kaynak, ad, 'exec')
        return None
    except SyntaxError as exc:
        return f"satır {exc.lineno}: {exc.msg}"


# ══ A) Hesabı fonksiyona çıkar — başlangıç ═════════════════════════
A_ESKI = '''    @app.route('/api/nakit_akis', methods=['GET'])
    def api_nakit_akis():
        """Nakit akisi projeksiyonu.

        Parametreler:
            ay=6                kac ay ileriye (1-24, varsayilan 6)
            kirilim=ay|hafta|gun
            baslangic=YYYY-MM-DD

        UC DOVIZ AYRI doner — toplanmaz.
        """
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('kasa', 'okuma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403

        try:'''

A_YENI = '''    def _nakit_projeksiyon(tam=False):
        """Nakit akisi projeksiyonunu HESAPLAR — dict doner.

        YETKI KONTROLU YOK: cagiran taraf kendisi denetler. Bu
        fonksiyonu hem /api/nakit_akis hem /api/export/nakit
        kullaniyor; ikisi de kendi yetkisini basta kontrol ediyor.

        Hesabin TEK KOPYA olmasi sart. Iki kopya olsaydi biri
        duzeltilip oteki unutuldugunda ekrandaki rakamla Excel'e
        inen rakam sessizce ayrisirdi.

        tam=True ise `tum_kalemler` de doner (kalem kalem disa
        aktarma icin, donem ozetindeki 40'lik kirpma olmadan).

        Parametreler request.args'tan okunur:
            ay=6                kac ay ileriye (1-24, varsayilan 6)
            kirilim=ay|hafta|gun
            baslangic=YYYY-MM-DD

        UC DOVIZ AYRI doner — toplanmaz.
        """
        try:'''

# ══ B) Hesabı fonksiyona çıkar — bitiş + ince rota ═════════════════
B_ESKI = '''        return jsonify({
            'ok': True,
            'baslangic': bas.isoformat(), 'bitis': son.isoformat(),
            'kirilim': kirilim, 'ay': ay_sayisi,
            'acilis': acilis,
            'donemler': sirali,
            'vadesi_gecmis': {'ozet': ozet(gecmis),
                              'kalemler': sorted(gecmis, key=lambda x: x['tarih'])[:100]},
            'vadesiz': {'ozet': ozet(vadesiz), 'kalemler': vadesiz[:100]},
        })'''

B_YENI = '''        sonuc = {
            'ok': True,
            'baslangic': bas.isoformat(), 'bitis': son.isoformat(),
            'kirilim': kirilim, 'ay': ay_sayisi,
            'acilis': acilis,
            'donemler': sirali,
            'vadesi_gecmis': {'ozet': ozet(gecmis),
                              'kalemler': sorted(gecmis, key=lambda x: x['tarih'])[:100]},
            'vadesiz': {'ozet': ozet(vadesiz), 'kalemler': vadesiz[:100]},
        }
        if tam:
            # Kirpilmamis tam liste — yalnizca disa aktarma icin.
            # API yanitina konmuyor: ekran zaten donem ozetini
            # gosteriyor, bosuna yuk olurdu.
            sonuc['tum_kalemler'] = (
                sorted(gecmis + gelecek, key=lambda x: x['tarih']) + vadesiz)
        return sonuc

    @app.route('/api/nakit_akis', methods=['GET'])
    def api_nakit_akis():
        """Nakit akisi projeksiyonu (ekran icin)."""
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('kasa', 'okuma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        return jsonify(_nakit_projeksiyon())

    # ── Disa aktarma yardimcilari (NA4) ───────────────────────
    NAKIT_KAYNAK_ETIKET = {
        'cari': 'Cari hesap', 'cek': 'Çek / Senet',
        'sabit': 'Sabit gider', 'elle': 'Elle eklenen',
    }

    def _nakit_gun_adi(i):
        return ('Pazartesi', 'Salı', 'Çarşamba', 'Perşembe',
                'Cuma', 'Cumartesi', 'Pazar')[i % 7]

    def _nakit_ay_adi(i):
        return ('Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
                'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım',
                'Aralık')[(i - 1) % 12]

    def _nakit_donem_adi(anahtar, kirilim):
        """'2026-08' → 'Ağustos 2026' gibi okunur bicime cevirir."""
        try:
            if kirilim == 'ay':
                y, a = anahtar.split('-')
                return f'{_nakit_ay_adi(int(a))} {y}'
            t = date.fromisoformat(anahtar)
            if kirilim == 'hafta':
                return f'{t.strftime("%d.%m.%Y")} haftası'
            return t.strftime('%d.%m.%Y')
        except Exception:
            return anahtar

    def _sabit_gider_periyot_yazi(g):
        if g.periyot == 'haftalik':
            return f'Her {_nakit_gun_adi(g.haftanin_gunu or 0)}'
        if g.periyot == 'yillik':
            return f'Her yıl {_nakit_ay_adi(g.ay or 1)} {g.ayin_gunu or 1}'
        return f"Her ayın {g.ayin_gunu or 1}'i"

    def _sabit_gider_aylik(g):
        """Periyodu aylik olcege getirir. Doviz cevrimi YAPILMAZ."""
        t = float(g.tutar or 0)
        if g.periyot == 'haftalik':
            return t * 52 / 12
        if g.periyot == 'yillik':
            return t / 12
        return t'''

# ══ C) Genel dağıtıcıya özet değişkeni ═════════════════════════════
C_ESKI = """        baslik = 'Liste'
        headers = []
        rows = []
        sayisal = []
        dosya = modul"""

C_YENI = """        baslik = 'Liste'
        headers = []
        rows = []
        sayisal = []
        dosya = modul
        # PDF ciktisinin basindaki ozet bloğu — [(etiket, deger), ...].
        # liste_pdf bunu zaten destekliyordu ama dagitici hic
        # doldurmuyordu. Bos birakilirsa davranis eskisi gibi.
        ozet_satirlari = []"""

# ══ D) Üç yeni modül ═══════════════════════════════════════════════
D_ESKI = """        else:
            return jsonify({'ok': False, 'mesaj': f'Bilinmeyen modül: {modul}'}), 400"""

D_YENI = '''        elif modul in ('nakit', 'nakit_detay'):
            # YETKI: genel dagitici modul yetkisine bakmiyor; nakit
            # ciktilari kasa bakiyelerini ve tum borc/alacaklari
            # icerdigi icin burada ACIKCA denetleniyor.
            if not _yetki_var_mi('kasa', 'okuma'):
                return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403

            p = _nakit_projeksiyon(tam=(modul == 'nakit_detay'))
            kirilim = p['kirilim']

            # Ozet blogu — her iki cikti icin ayni
            for dv in sorted(p['acilis']):
                ozet_satirlari.append((f'{dv} açılış bakiyesi',
                                       _f(p['acilis'][dv], True)))
            ozet_satirlari.append(('Aralık',
                                   f"{_tarih(date.fromisoformat(p['baslangic']))}"
                                   f" – {_tarih(date.fromisoformat(p['bitis']))}"))
            # Kumulatif negatife dusen ilk donem: raporun asil uyarisi
            for dv in sorted(p['acilis']):
                kritik = next((s for s in p['donemler']
                               if (s['dovizler'].get(dv) or {}).get('kumulatif', 0) < 0), None)
                if kritik:
                    ozet_satirlari.append((
                        f'⚠ {dv} bakiyesi eksiye düşüyor',
                        f"{_nakit_donem_adi(kritik['donem'], kirilim)}"
                        f" ({_f(kritik['dovizler'][dv]['kumulatif'], True)})"))
            for dv, o in sorted((p['vadesi_gecmis']['ozet'] or {}).items()):
                if o.get('giris'):
                    ozet_satirlari.append((f'Vadesi geçmiş {dv} alacak',
                                           f"{_f(o['giris'], True)} ({o['adet']} kayıt)"))
                if o.get('cikis'):
                    ozet_satirlari.append((f'Vadesi geçmiş {dv} borç',
                                           f"{_f(o['cikis'], True)} ({o['adet']} kayıt)"))
            _vsz = sum(o['adet'] for o in (p['vadesiz']['ozet'] or {}).values())
            if _vsz:
                ozet_satirlari.append(('Vadesi belirsiz hareket',
                                       f'{_vsz} adet — projeksiyona dahil değil'))

            if modul == 'nakit':
                baslik = 'Nakit Akışı Projeksiyonu'
                headers = ['Döviz', 'Dönem', 'Giriş', 'Çıkış', 'Net', 'Kümülatif']
                sayisal = [2, 3, 4, 5]
                # Doviz doviz gruplanir — tek cizgide toplanmaz.
                dovizler = sorted(set(list(p['acilis'].keys())
                                      + [d for s in p['donemler'] for d in s['dovizler']]))
                for dv in dovizler:
                    _yazildi = False
                    for s in p['donemler']:
                        v = s['dovizler'].get(dv)
                        if not v or (not v['giris'] and not v['cikis']):
                            continue
                        rows.append([dv, _nakit_donem_adi(s['donem'], kirilim),
                                     _f(v['giris'], True), _f(v['cikis'], True),
                                     _f(v['net'], True), _f(v['kumulatif'], True)])
                        _yazildi = True
                    if not _yazildi and p['acilis'].get(dv):
                        rows.append([dv, 'hareket yok', '', '', '',
                                     _f(p['acilis'][dv], True)])
                dosya = f"nakit_akisi_{p['ay']}ay"

            else:
                baslik = 'Nakit Akışı — Kalem Listesi'
                headers = ['Vade', 'Döviz', 'Yön', 'Tutar', 'Kaynak', 'Açıklama']
                sayisal = [3]
                for k in p.get('tum_kalemler', []):
                    rows.append([
                        _tarih(date.fromisoformat(k['tarih'])) if k['tarih'] else 'VADESİZ',
                        k['doviz'],
                        'Giriş' if k['yon'] == 'giris' else 'Çıkış',
                        _f(k['tutar'], True),
                        NAKIT_KAYNAK_ETIKET.get(k['kaynak'], k['kaynak']),
                        k['aciklama'] or ''])
                dosya = f"nakit_kalemleri_{p['ay']}ay"

        elif modul == 'sabit_gider':
            if not _yetki_var_mi('kasa', 'okuma'):
                return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
            baslik = 'Sabit Giderler'
            headers = ['Gider', 'Kategori', 'Periyot', 'Tutar', 'Döviz',
                       'Aylık karşılık', 'Başlangıç', 'Bitiş', 'Durum']
            sayisal = [3, 5]
            gl = SabitGider.query.order_by(SabitGider.kategori, SabitGider.ad).all()
            aylik = {}
            for g in gl:
                if g.aktif:
                    _d = (g.doviz or 'TRY').upper()
                    aylik[_d] = aylik.get(_d, 0) + _sabit_gider_aylik(g)
                rows.append([g.ad, g.kategori or '', _sabit_gider_periyot_yazi(g),
                             _f(g.tutar, True), g.doviz or 'TRY',
                             _f(_sabit_gider_aylik(g), True),
                             _tarih(g.baslangic), _tarih(g.bitis) or 'süresiz',
                             'Aktif' if g.aktif else 'Pasif'])
            for dv in sorted(aylik):
                ozet_satirlari.append((f'{dv} aylık yük', _f(aylik[dv], True)))
                ozet_satirlari.append((f'{dv} yıllık yük', _f(aylik[dv] * 12, True)))
            dosya = 'sabit_giderler'

        else:
            return jsonify({'ok': False, 'mesaj': f'Bilinmeyen modül: {modul}'}), 400'''

# ══ E) PDF çağrısına özet ══════════════════════════════════════════
E_ESKI = """            return liste_pdf(baslik, headers, rows, dosya_adi=dosya, sayisal_sutunlar=sayisal)"""
E_YENI = """            return liste_pdf(baslik, headers, rows, dosya_adi=dosya,
                             sayisal_sutunlar=sayisal,
                             ozet=ozet_satirlari or None)"""

# ══ F) reportlab YEDEK yolu da özeti bassın ════════════════════════
#
#  BULGU: liste_pdf'in birincil yolu WeasyPrint ile HTML sablonunu
#  basiyor ve `ozet` oraya dogru gidiyor. Ama WeasyPrint kurulu
#  degilse ya da patlar ise reportlab yedegine dusuluyor — ve o
#  fonksiyon `ozet` parametresini HIC ALMIYORDU. Yani ozet blogu
#  SESSIZCE kayboluyordu; kimse fark etmezdi.
#
#  Bu, nakit ciktisinda ozellikle kotu: "TRY bakiyesi Eylul'de
#  eksiye dusuyor" uyarisi raporun en onemli satiri.
#
F_ESKI = """def _liste_pdf_reportlab(baslik, headers, rows, dosya_adi='liste', sayisal_sutunlar=None):"""
F_YENI = """def _liste_pdf_reportlab(baslik, headers, rows, dosya_adi='liste', sayisal_sutunlar=None,
                         ozet=None):"""

G_ESKI = """        return _liste_pdf_reportlab(baslik, headers, rows, dosya_adi, sayisal_sutunlar)"""
G_YENI = """        return _liste_pdf_reportlab(baslik, headers, rows, dosya_adi, sayisal_sutunlar,
                                    ozet=ozet)"""

H_ESKI = """    elemanlar = [
        Paragraph(baslik or 'Liste', baslik_stil),
        Paragraph(f'Oluşturma: {date.today().strftime("%d.%m.%Y")}', tarih_stil),
        Spacer(1, 4),
    ]"""

H_YENI = """    elemanlar = [
        Paragraph(baslik or 'Liste', baslik_stil),
        Paragraph(f'Oluşturma: {date.today().strftime("%d.%m.%Y")}', tarih_stil),
        Spacer(1, 4),
    ]

    # ÖZET — HTML yolundaki blokla ayni bilgi. Yedege dusuldugunde
    # ozetin sessizce kaybolmamasi icin burada da basiliyor.
    if ozet:
        ozet_stil = ParagraphStyle('Ozet', parent=styles['Normal'], fontSize=8.5,
                                   leading=12, fontName=font_normal,
                                   textColor=colors.HexColor('#333333'))
        for _etiket, _deger in ozet:
            elemanlar.append(Paragraph(f'<b>{_etiket}:</b> {_deger}', ozet_stil))
        elemanlar.append(Spacer(1, 8))"""


BLOKLAR = [
    (APP,  "hesap → fonksiyon (giriş)",   A_ESKI, A_YENI, 'def _nakit_projeksiyon('),
    (APP,  "hesap → fonksiyon (çıkış)",   B_ESKI, B_YENI, 'NAKIT_KAYNAK_ETIKET'),
    (APP,  "dağıtıcıya özet değişkeni",   C_ESKI, C_YENI, 'ozet_satirlari = []'),
    (APP,  "3 yeni modül (nakit, nakit_detay, sabit_gider)", D_ESKI, D_YENI, "elif modul in ('nakit', 'nakit_detay')"),
    (APP,  "PDF çağrısına özet",          E_ESKI, E_YENI, 'ozet=ozet_satirlari or None'),
    (UTIL, "yedek PDF: ozet parametresi",  F_ESKI, F_YENI, 'sayisal_sutunlar=None,\n                         ozet=None)'),
    (UTIL, "yedek PDF: özeti aktar",       G_ESKI, G_YENI, 'sayisal_sutunlar,\n                                    ozet=ozet)'),
    (UTIL, "yedek PDF: özeti bas",         H_ESKI, H_YENI, "ozet_stil = ParagraphStyle('Ozet'"),
]

print("═" * 70)
print(" NA4 · NAKİT AKIŞI — raporlama + dışa aktarma")
print("═" * 70)
print()

icerik, crlf = {}, {}
for yol in (APP, UTIL):
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
    print(" ✓ Tüm bloklar zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

for yol in (APP, UTIL):
    hata = dogrula(icerik[yol], yol.name)
    if hata:
        print(f" ✗ {yol.name} SÖZDİZİMİ HATASI → {hata}")
        print(" HİÇBİR DOSYAYA DOKUNULMADI.")
        sys.exit(1)
print(" ✓ sözdizimi doğrulandı (compile)")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_na4_nakit_rapor.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
for yol in (APP, UTIL):
    yedek = yol.with_name(f'{yol.name}.yedek-{damga}')
    shutil.copy2(yol, yedek)
    yol.write_bytes(icerik[yol].encode('utf-8'))
    print(f" ✓ {yol.name}")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print("   /api/export/nakit?format=xlsx|pdf&ay=6&kirilim=ay")
print("   /api/export/nakit_detay?format=xlsx|pdf&ay=6")
print("   /api/export/sabit_gider?format=xlsx|pdf")
print()
print(" ⚠ templates/nakit.html ve templates/sabit_gider.html'in")
print("   GÜNCEL sürümlerini de kopyalayın (Dışa Aktar düğmesi).")
print("═" * 70)

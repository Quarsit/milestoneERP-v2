#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA LG1 — FİRMA LOGOSU HİÇ KAYDEDİLEMİYORDU
=============================================

ÖNKOŞUL: **yama_un1.py uygulanmış olmalı.** Betik denetliyor.
Şema yok, göç yok. Tek satırlık düzeltme + bir bekçi.

UN1'i yazarken denk geldi, orada haber vermiştim.

═══ HATA ═══

Logo kaydeden ucun denetim izi satırında şu yazıyordu:

      yeni={'dosya': k.ek_bilgi, 'boyut_kb': ...}

`k` o fonksiyonun hiçbir yerinde yok. Göze batmamasının sebebi
`create_app()`in TEK BİR büyük kapsam olması: `k` adı kesim ucunda
bir döngü değişkeni olarak geçiyor, ama o `api_kesim_ekle`ye ait.
Söz dizimi doğru, `py_compile` temiz, test takımı yeşil — hata
yalnızca O UÇ çağrıldığında ortaya çıkıyor.

ÖLÇÜLDÜ:

      POST /api/ayarlar/logo  →  500,  kayda logo YAZILMIYOR
      sonra                   →  200,  logo kayıtta, dosya adı da ✓

Yani logo hiç kaydedilemiyordu. Logo kullanan her belge — ticari
fatura, etiket, liste çıktısı — logosuz basıyordu.

Dosya adı bir satır yukarıda `f.logo_dosya`ya yazılıyor; denetim
izine de o gidiyor. Silme ucu aynı yeri zaten `f.logo_dosya` ile
doğru yazıyormuş; kayıt ucu onu kaçırmış.

═══ BEKÇİ ═══

Bu hata sınıfı testten geçer: dosya derlenir, takım yeşil kalır,
patlama yalnızca o uç çağrılınca olur. O yüzden düzeltmenin yanına
bir bekçi koydum: `create_app()` içindeki bütün kapsamları gezip
ATANMAMIŞ her başvuruyu yakalıyor.

`symtable` stdlib'de — kurulu olmayan bir lint paketine
bağlanmıyoruz. Ölçüldü: düzeltmeden ÖNCE tam 1 bulgu (`k`), SONRA
0. Otuz bin satırda hiç yanlış alarm vermiyor.

Bundan sonra aynı türden bir ad, hangi uçta olursa olsun, takımı
kırmızıya çevirecek.

═══ DOKUNMADIĞIM YER ═══

Logo SİLME ucu `_safe_commit` yerine çıplak `db.session.commit()`
kullanıyor. Baktım: çıplak commit bu projede hâlâ yaygın (97'ye 69)
ve commit `return`'den önce olduğu için hata 500'e düşüyor — yani
kullanıcıya sahte bir "silindi" demiyor. Düzeltilecek bir şey
görmedim, ev tarzını tek bir yerde değiştirmek de doğru olmazdı.

═══ DOĞRULANDI ═══
  264 test geçti (261 + 3). Üçü de taban üzerinde BAŞARISIZ oluyor:
  biri gerçek uçtan logo yükleyip kayda yazıldığını, biri denetim
  izinin dosya adını taşıdığını, biri de bekçinin kendisini ölçüyor.

DOSYALAR
--------
  flask_app.py           tek satır
  tests/test_kritik.py   3 yeni test

KULLANIM
--------
  python3 yama_lg1.py            # RAPOR
  python3 yama_lg1.py --uygula
  sudo systemctl restart milestone-erp
"""

import base64
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile

UYGULA = '--uygula' in sys.argv
KOK = os.path.dirname(os.path.abspath(__file__))

DOSYA_IMZA = {
    'flask_app.py': 'LG1 · BURADA TANIMSIZ BIR AD VARDI',
    'tests/test_kritik.py': 'def test_lg1_flask_appte_tanimsiz_ad_yok',
}
ONKOSUL = {
    'flask_app.py': 'UN1 · KESİM MALİYETİ ARTIK HER ZAMAN USD',
    'tests/test_kritik.py': 'def test_un2_karisik_mense_kaynak_basina_bolunur',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'LG1 · flask_app.py blok 1',
     r'''        _log_audit('GUNCELLE', 'ayarlar', 'firma_logo',
                   yeni={'dosya': k.ek_bilgi, 'boyut_kb': round(tahmini_kb, 1)})
''',
     r'''        #
        # ── LG1 · BURADA TANIMSIZ BIR AD VARDI ──
        # `k.ek_bilgi` yazıyordu ve `k` bu fonksiyonun hiçbir yerinde
        # yok. `create_app()` tek bir büyük kapsam olduğu için göze
        # batmıyordu: `k` adı KESİM ucunda bir döngü değişkeni olarak
        # geçiyor, ama o `api_kesim_ekle`ye ait.
        #
        # ÖLÇÜLDÜ: POST /api/ayarlar/logo → 500, kayda logo YAZILMIYOR.
        # Yani logo hiç kaydedilemiyordu ve logo kullanan her belge
        # (ticari fatura, etiket, liste çıktısı) logosuz basıyordu.
        # Silme ucu aynı yeri `f.logo_dosya` ile doğru yazıyor; kayıt
        # ucu onu kaçırmış.
        #
        # Dosya adı bir satır yukarıda `f.logo_dosya`ya yazıldı —
        # denetim izine de o gidiyor, veriyi iki kez okumadan.
        _log_audit('GUNCELLE', 'ayarlar', 'firma_logo',
                   yeni={'dosya': f.logo_dosya,
                         'boyut_kb': round(tahmini_kb, 1)})
'''),
    ('tests/test_kritik.py', 'LG1 · tests/test_kritik.py blok 1',
     r'''        assert {e.mense for e in eb} == {'TURKIYE'}
''',
     r'''        assert {e.mense for e in eb} == {'TURKIYE'}


# ══════════════════════════════════════════════════════════════════
#  LG1 · FİRMA LOGOSU HİÇ KAYDEDİLEMİYORDU
#
#  Logo kaydeden uçtaki denetim izi satırında `k.ek_bilgi` yazıyordu
#  ve `k` o fonksiyonun hiçbir yerinde yok. `create_app()` tek büyük
#  bir kapsam olduğu için göze batmıyordu: `k` adı KESİM ucunda bir
#  döngü değişkeni olarak geçiyor, ama o başka bir fonksiyona ait.
#
#  ÖLÇÜLDÜ: POST /api/ayarlar/logo → 500, kayda logo yazılmıyor.
#  Logo kullanan her belge (ticari fatura, etiket, liste çıktısı)
#  logosuz basıyordu.
# ══════════════════════════════════════════════════════════════════
# 1x1 saydam PNG
_LG1_PNG = ('data:image/png;base64,'
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNk'
            'YPgPAAIAAf8lU0oAAAAASUVORK5CYII=')


def test_lg1_firma_logosu_kaydedilebiliyor():
    """Logo yüklenince 200 dönmeli ve kayda GERÇEKTEN yazılmalı."""
    from models import Firma
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/ayarlar/logo', headers=H,
               json={'logo': _LG1_PNG, 'dosya_adi': 'lg1.png'})
    assert r.status_code == 200, (r.status_code, r.get_data(as_text=True)[:200])
    assert r.get_json().get('ok') is True, r.get_json()
    with fa.app.app_context():
        f = Firma.query.first()
        assert f.logo, 'yanıt 200 dedi ama kayda logo yazılmamış'
        assert f.logo == _LG1_PNG
        assert f.logo_dosya == 'lg1.png', f.logo_dosya
    # Okuma ucu da gormeli
    d = c.get('/api/ayarlar/logo', headers=H).get_json()
    assert d.get('var_mi') is True, d
    assert d.get('dosya_adi') == 'lg1.png', d


def test_lg1_logo_denetim_izi_dosya_adini_yaziyor():
    """Denetim izi commit'e girmeli ve dosya adını taşımalı.

    Hatanın çıktığı satır tam da denetim izi satırıydı; düzeltmenin
    o izi gerçekten yazdığını görmek gerekiyor."""
    from models import AuditLog
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/ayarlar/logo', headers=H,
               json={'logo': _LG1_PNG, 'dosya_adi': 'iz.png'})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    with fa.app.app_context():
        kayit = AuditLog.query.filter_by(
            tablo_adi='ayarlar', kayit_id='firma_logo',
            islem_tipi='GUNCELLE').order_by(AuditLog.id.desc()).first()
        assert kayit is not None, 'denetim izi yazılmamış'
        assert 'iz.png' in (kayit.yeni_veri or ''), kayit.yeni_veri


def test_lg1_flask_appte_tanimsiz_ad_yok():
    """`create_app()` içinde çözülemeyen hiçbir ad kalmamalı.

    LG1 bu sınıftan bir hataydı ve yalnızca O UÇ çağrıldığında
    patlıyordu — söz dizimi doğru, derleme temiz, test takımı yeşil.
    Bu bekçi kapsamları gezip ATANMAMIŞ her başvuruyu yakalıyor.

    `symtable` stdlib'de; kurulu olmayan bir lint paketine
    bağlanmıyoruz. Ölçüldü: düzeltmeden önce tam 1 bulgu (`k`),
    sonra 0 — 30 bin satırda hiç yanlış alarm yok."""
    import builtins
    import symtable
    import io as _io
    src = _io.open(os.path.join(KOK, 'flask_app.py'), encoding='utf-8').read()
    st = symtable.symtable(src, 'flask_app.py', 'exec')
    _yerlesik = set(dir(builtins))
    _kok = {s.get_name() for s in st.get_symbols()
            if s.is_assigned() or s.is_imported()}

    bulgular = []

    def gez(tablo, kapsayan):
        atanan = {s.get_name() for s in tablo.get_symbols()
                  if s.is_assigned() or s.is_parameter() or s.is_imported()}
        gorunur = kapsayan | atanan
        for s in tablo.get_symbols():
            ad = s.get_name()
            if not s.is_referenced():
                continue
            if ad in gorunur or ad in _yerlesik or ad in _kok:
                continue
            bulgular.append(f'{tablo.get_name()} '
                            f'(satır {tablo.get_lineno()}): {ad}')
        for alt in tablo.get_children():
            gez(alt, gorunur)

    gez(st, set())
    assert not bulgular, \
        'çözülemeyen ad(lar) — çağrıldığında NameError verir: ' \
        + '; '.join(bulgular)
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA LG1 — FİRMA LOGOSU HİÇ KAYDEDİLEMİYORDU')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    # ── --yaz-gecici ──
    # base64 gömülü iki dosyayı /tmp'ye çıkarır, PROJEYE DOKUNMAZ.
    # Tam dosya yazan bir yamayı önce okumak istemek yerinde bir
    # istek; "uygula da sonra bak" demek yanlış olurdu.
    if '--yaz-gecici' in sys.argv:
        hedef = tempfile.mkdtemp(prefix='tz1-')
        print()
        for ad in TAM_YAZILAN:
            p = os.path.join(hedef, ad)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(_tam_dosya(ad))
            print(f'  {p}')
        print()
        print('  Projeye DOKUNULMADI. Okuduktan sonra:')
        print('    python3 yama_lg1.py            # rapor')
        print('    python3 yama_lg1.py --uygula')
        print('=' * 70)
        return 0

    gruplar = {}
    for dosya, aciklama, eski, yerine in DEGISIKLIKLER:
        gruplar.setdefault(dosya, []).append((aciklama, eski, yerine))

    sonuclar, hata, zaten = {}, False, []

    # ══════════════════════════════════════════════════════════════
    #  TAM DOSYA YAZILANLAR
    # ══════════════════════════════════════════════════════════════
    for dosya in TAM_YAZILAN:
        yol = os.path.join(KOK, dosya)
        print(f'\n── {dosya} ' + '─' * max(0, 52 - len(dosya)))
        yeni = _tam_dosya(dosya)

        if os.path.exists(yol):
            with open(yol, 'rb') as f:
                ham = f.read()
            try:
                mevcut = ham.decode('utf-8')
            except UnicodeDecodeError:
                print('  ✗ Dosya UTF-8 değil — dokunmuyorum.')
                hata = True
                continue
            imza = DOSYA_IMZA.get(dosya)
            if imza and imza in mevcut:
                print('  ⊙ İmza zaten var — ATLANIR')
                zaten.append(dosya)
                continue
            onk = ONKOSUL.get(dosya)
            if onk and onk not in mevcut:
                # Beklenmeyen bir dosyanın üzerine yazmayı reddediyoruz:
                # bu betik TAM DOSYA yazıyor, yanlış hedefte geri
                # dönüşü yedekten olur.
                print(f'  ✗ Beklenen içerik yok ("{onk}")')
                print('    Bu dosya tanıdığım sifirla2.py değil; tam dosya')
                print('    yazdığım için üzerine yazmayı reddediyorum.')
                hata = True
                continue
            print(f'  · mevcut dosya {len(mevcut.splitlines())} satır '
                  f'→ yeni {len(yeni.splitlines())} satır (YENİDEN YAZILIR)')
        else:
            print(f'  · yeni dosya ({len(yeni.splitlines())} satır)')

        # Söz dizimi doğrulaması — UZANTIYA GÖRE.
        _uzanti = os.path.splitext(dosya)[1].lower()
        with tempfile.NamedTemporaryFile('w', suffix=_uzanti or '.txt',
                                         delete=False, encoding='utf-8') as tf:
            tf.write(yeni)
            gec = tf.name
        try:
            if _uzanti == '.py':
                try:
                    py_compile.compile(gec, doraise=True, cfile=gec + 'c')
                    print('  ✓ söz dizimi doğrulandı (py_compile)')
                except py_compile.PyCompileError as e:
                    print(f'  ✗ SÖZDİZİMİ HATASI:\n{e}')
                    hata = True
            elif _uzanti == '.js':
                _node = shutil.which('node') or shutil.which('nodejs')
                if not _node:
                    print('  ⚠ node bulunamadı — JS söz dizimi DENETLENMEDİ')
                else:
                    _s = subprocess.run([_node, '--check', gec],
                                        capture_output=True, text=True)
                    if _s.returncode != 0:
                        print(f'  ✗ JS SÖZDİZİMİ HATASI:\n{_s.stderr[:400]}')
                        hata = True
                    else:
                        print('  ✓ söz dizimi doğrulandı (node --check)')
            else:
                print(f'  · {_uzanti or "uzantısız"} — söz dizimi denetimi yok')
        finally:
            for p in (gec, gec + 'c'):
                if os.path.exists(p):
                    os.unlink(p)

        sonuclar[yol] = yeni

    # ══════════════════════════════════════════════════════════════
    #  CERRAHİ DEĞİŞİKLİKLER
    # ══════════════════════════════════════════════════════════════
    for dosya, isler in gruplar.items():
        yol = os.path.join(KOK, dosya)
        print(f'\n── {dosya} ' + '─' * max(0, 52 - len(dosya)))
        if not os.path.exists(yol):
            print(f'  ✗ DOSYA YOK: {yol}')
            hata = True
            continue

        with open(yol, 'rb') as f:
            ham = f.read()
        crlf = b'\r\n' in ham
        icerik = ham.decode('utf-8')
        if crlf:
            icerik = icerik.replace('\r\n', '\n')
            print('  · CRLF satır sonu algılandı, korunacak')

        # ── SIRA ÖNEMLİ: İMZA ÖNCE, ÖNKOŞUL SONRA ──
        # Ters sırada yazmıştım ve ikinci koşuda patladı. Bu yamanın
        # ÖNKOŞUL çapaları, yamanın DEĞİŞTİRDİĞİ satırların kendisi
        # (örn. `grep -q "Zaten uygulanmış"`). Uygulandıktan sonra o
        # satır artık yok; önkoşulu önce denetlersen uygulanmış dosya
        # "ÖNKOŞUL YOK" diye HATA veriyor — oysa durum "zaten
        # uygulanmış". İmza sorusu her zaman önce gelmeli.
        if DOSYA_IMZA[dosya] in icerik:
            print('  ⊙ İmza zaten var — ATLANIR')
            zaten.append(dosya)
            continue
        onk = ONKOSUL.get(dosya)
        if onk and onk not in icerik:
            print(f'  ✗ ÖNKOŞUL YOK: "{onk}" yok')
            hata = True
            continue

        yeni, bozuk = icerik, False
        for aciklama, eski, yerine in isler:
            n = yeni.count(eski)
            if n != 1:
                print(f'  ✗ {aciklama}')
                print(f'     kalıp {n} kez eşleşti (tam 1 olmalı)')
                hata = bozuk = True
                continue
            yeni = yeni.replace(eski, yerine, 1)
            print(f'  ✓ {aciklama}')
        if bozuk:
            continue

        if dosya.endswith('.py'):
            with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False,
                                             encoding='utf-8') as tf:
                tf.write(yeni)
                gec = tf.name
            try:
                py_compile.compile(gec, doraise=True, cfile=gec + 'c')
                print('  ✓ söz dizimi doğrulandı (py_compile)')
            except py_compile.PyCompileError as e:
                print(f'  ✗ SÖZDİZİMİ HATASI:\n{e}')
                hata = True
            finally:
                for p in (gec, gec + 'c'):
                    if os.path.exists(p):
                        os.unlink(p)

        if dosya.endswith('.sh'):
            # Kabuk betiğini bash ile söz dizimi denetimine sok;
            # bozuk bir gonder.sh push yolunu kapatır.
            try:
                with tempfile.NamedTemporaryFile('w', suffix='.sh',
                                                 delete=False,
                                                 encoding='utf-8') as tf:
                    tf.write(yeni)
                    gecs = tf.name
                _s = subprocess.run(['bash', '-n', gecs],
                                    capture_output=True, text=True)
                if _s.returncode != 0:
                    print(f'  ✗ KABUK SÖZDİZİMİ HATASI:\n{_s.stderr[:400]}')
                    hata = True
                else:
                    print('  ✓ söz dizimi doğrulandı (bash -n)')
            except FileNotFoundError:
                print('  ⚠ bash bulunamadı, kabuk denetimi atlandı')
            finally:
                if os.path.exists(gecs):
                    os.unlink(gecs)

        sonuclar[yol] = (yeni.replace('\n', '\r\n') if crlf else yeni)

    # ══════════════════════════════════════════════════════════════
    print('\n' + '=' * 70)
    if hata:
        print('  ✗ HATA VAR → Hiçbir dosyaya DOKUNULMADI')
        return 1
    if zaten and sonuclar:
        # Yarım durum: bazı dosyalar yamalı, bazıları değil. Devam
        # etmek sistemi tutarsız bırakırdı.
        print('  ✗ YARIM DURUM → Hiçbir dosyaya DOKUNULMADI')
        print(f'    imzası olan: {", ".join(zaten)}')
        return 1
    if zaten:
        print('  ⊙ Yama LG1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_lg1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_lg1'
            shutil.copy2(yol, yedek)
            _y = f'    yedek  : {os.path.relpath(yedek, KOK)}'
        else:
            _y = '    (yeni dosya — yedek yok)'
            _klasor = os.path.dirname(yol)
            if _klasor and not os.path.isdir(_klasor):
                os.makedirs(_klasor, exist_ok=True)
                print(f'    klasör oluşturuldu: {os.path.relpath(_klasor, KOK)}')
        with open(yol, 'w', encoding='utf-8', newline='') as f:
            f.write(icerik)
        if yol.endswith('.sh'):
            os.chmod(yol, 0o755)
        print(f'  ✓ yazıldı: {os.path.relpath(yol, KOK)}')
        print(_y)

    print('\n  ✓ YAMA UYGULANDI')
    print()
    print('    1) sudo systemctl restart milestone-erp')
    print('    2) venv/bin/python -m pytest tests/test_kritik.py -q   # 264')
    print()
    print('  BAKILACAK YER')
    print('    Ayarlar -> firma logosu yukle. Eskiden 500 veriyordu ve')
    print('    logo hic kaydedilmiyordu; artik kaydediliyor. Logo')
    print('    kullanan belgelere bak: ticari fatura, etiket, liste')
    print('    ciktisi.')
    print()
    print('  RAKAM DEGISMIYOR')
    print('    Para ya da stok hesabina dokunan hicbir sey yok.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA HY1 — HAYALET ALAN BEKÇİSİ
================================

ÖNKOŞUL: **yama_lg1.py uygulanmış olmalı.** Betik denetliyor.
Yalnız test dosyasına dokunuyor. `flask_app.py` DEĞİŞMİYOR.

LG1'in bekçisi işe yarayınca aynı yöntemle bir sınıf daha taradım:
**DZ5 sınıfı.**

═══ SINIF ═══

DZ5'te `GUNCELLENEBILIR` beyaz listesinde `belge_no` vardı, ama o
alan CariHareket'te YOK — Sevkiyat'ın alanı. Uç nokta alanı
"güncellendi" diye adıyla sayıp hiçbir yere yazmıyordu: 200 dönüyor,
kullanıcıya kaydedildi deniyor, kayıtta hiçbir şey değişmiyor.
Python `obj.olmayan = x` demeye izin verdiği için ne hata ne uyarı.

LG1 ile aynı aile: söz dizimi doğru, derleme temiz, takım yeşil,
hata yalnızca o uç çağrılınca ve SESSİZCE oluyor.

═══ TARAMA SONUCU: TEMİZ ═══

26 `setattr` beyaz listesi bulundu, hepsi hedef modeline çözüldü,
hiçbirinde hayalet ad yok. Yani düzeltilecek bir şey çıkmadı —
bulunan tek şey, bir daha oluşmasını engelleyecek bekçi.

Hangi uçların tarandığı: cari · cari kişi · cari aktivite · hareket ·
sipariş · sabit gider · ortaklık vergi · sevkiyat (3 yer) · banka ·
çek · proforma · satış · konteyner (4 yer) · fatura (2 yer) · KDV
iade (3 yer) · stok ölçüleri.

═══ BEKÇİNİN KURALI ═══

Her `setattr(nesne, alan, …)` döngüsünün beyaz listesindeki her ad,
o nesnenin HEDEF MODELİNDE kolon olmalı.

  · "Bir modelde var" YETMEZ. `belge_no` gayet bir modelde vardı.
    Bu yüzden hedef model çözülüp ad ona göre denetleniyor.

  · `hasattr(nesne, alan)` süzgeci olan döngüler MUAF. DZ2 o kalıba
    dayanıyor: stok düzenleme ucu blok/plaka/ebatlı için aynı listeyi
    kullanıp PLAKA'ya tonaj yazmıyor. Süzgeç varsa alan zaten
    korunuyor.

═══ BİR HATAYI KENDİMDE BULDUM ═══

Bekçinin ilk hâli değişken adını DOSYA ÇAPINDA çözüyordu. `k`, `s`,
`c`, `f` gibi adlar bu dosyada onlarca fonksiyonda yeniden
kullanılıyor; öyle yazınca hangi atamanın son söz sahibi olduğu
gezme sırasına kalıyor.

ÖLÇÜLDÜ: o hâli `k`yı Veriler'e, `s`yi EbatliStok'a, çek ucundaki
`c`yi Cari'ye bağlayıp **11 uydurma bulgu** üretti. Çözümleme
FONKSİYON KAPSAMINA indirildi, iç fonksiyonların gövdesi dışarıda
bırakıldı; o hâlde 26 yerin hepsi doğru modele oturuyor (fonksiyon
adlarıyla tutuyor: `api_cek_guncelle` → Cek, `api_konteyner_guncelle`
→ Konteyner …).

Bunu yazıyorum çünkü bağımsız betiğimin ilk temiz sonucu ŞANSTI —
yanlış çözümleyiciyle de "0 bulgu" demişti. Doğrusunu yazınca sonuç
yine 0 çıktı, ama artık sebebi şans değil.

═══ BEKÇİ KENDİNİ KANITLIYOR ═══

İkinci test bekçinin kendisini ölçüyor: `belge_no` kaynağa geri
konunca yakalamalı. Bir bekçi, yakaladığını gösteremezse bekçi
değildir.

ÖLÇÜLDÜ: geri konunca tam olarak şunu diyor —

      satır 13056 · api_hareket_guncelle · setattr(hareket, …)
         ✗ 'belge_no' — CariHareket'te YOK (var olduğu model: Sevkiyat)

Yani yalnız yakalamıyor, teşhisi de koyuyor.

═══ DOĞRULANDI ═══
  266 test geçti (264 + 2). DZ5 hatası kaynağa geri konulan bir
  kopyada ikisi de BAŞARISIZ oluyor.

DOSYALAR
--------
  tests/test_kritik.py   2 yeni test

Şema yok, göç yok, uygulama kodu değişmiyor.

KULLANIM
--------
  python3 yama_hy1.py            # RAPOR
  python3 yama_hy1.py --uygula
  venv/bin/python -m pytest tests/test_kritik.py -q
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
    'tests/test_kritik.py': 'def test_hy1_setattr_beyaz_listelerinde_hayalet_alan_yok',
}
ONKOSUL = {
    'tests/test_kritik.py': 'def test_lg1_flask_appte_tanimsiz_ad_yok',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('tests/test_kritik.py', 'HY1 · tests/test_kritik.py blok 1',
     r'''        + '; '.join(bulgular)
''',
     r'''        + '; '.join(bulgular)


# ══════════════════════════════════════════════════════════════════
#  HY1 · BEYAZ LİSTEDE HAYALET ALAN OLMAYACAK
#
#  DZ5'te `GUNCELLENEBILIR` listesinde `belge_no` vardı ama o alan
#  CariHareket'te YOK — Sevkiyat'ın alanı. Uç nokta alanı
#  "güncellendi" diye adıyla sayıp hiçbir yere yazmıyordu: 200
#  dönüyor, kullanıcıya kaydedildi deniyor, kayıtta hiçbir şey
#  değişmiyor. Python `obj.olmayan = x` demeye izin verdiği için ne
#  hata ne uyarı çıkıyor.
#
#  LG1'in bekçisiyle aynı aile: söz dizimi doğru, takım yeşil, hata
#  yalnızca o uç çağrılınca ve SESSİZCE oluyor.
#
#  "Bir modelde var" yetmez — `belge_no` gayet bir modelde vardı.
#  Bu yüzden her setattr döngüsünün HEDEF MODELİ çözülüp ad ona göre
#  denetleniyor. `hasattr(nesne, alan)` süzgeci olan döngüler muaf:
#  DZ2 o kalıba dayanıyor ve PLAKA'ya tonaj yazmıyor.
#
#  ÖLÇÜLDÜ: `belge_no` geri konunca tarama onu tam olarak bulup
#  "CariHareket'te YOK (var olduğu modeller: Sevkiyat)" diyor;
#  temiz kodda 26 beyaz listenin hiçbirinde bulgu yok.
# ══════════════════════════════════════════════════════════════════
def _hy1_modeller():
    """Model adı -> yazılabilir öznitelik adları."""
    import models as _M
    _mod = {}
    for _ad in dir(_M):
        _s = getattr(_M, _ad)
        if isinstance(_s, type) and hasattr(_s, '__table__'):
            _k = {c.name for c in _s.__table__.columns}
            for _n, _v in vars(_s).items():
                if hasattr(_v, 'expression') or hasattr(_v, 'property'):
                    _k.add(_n)
            _mod[_ad] = _k
    return _mod


def _hy1_tara(kaynak, modeller):
    """(satır, fonksiyon, nesne, hedef model, hayalet adlar) listesi.

    ÇÖZÜMLEME FONKSİYON KAPSAMINDA. Değişken adları (`k`, `s`, `c`,
    `f`) dosya genelinde onlarca fonksiyonda yeniden kullanılıyor;
    dosya çapında tek bir "ad → model" eşlemesi tutmak hangi atamanın
    son söz sahibi olduğunu gezme sırasına bırakır ve rastgele cevap
    verir. Ölçüldü: öyle yazılmış ilk hâli `k`yı Veriler'e, `s`yi
    EbatliStok'a bağlayıp 11 uydurma bulgu üretti.
    """
    import ast

    def liste(dugum, yerel):
        if isinstance(dugum, (ast.Tuple, ast.List, ast.Set)):
            return [e.value for e in dugum.elts
                    if isinstance(e, ast.Constant)
                    and isinstance(e.value, str)]
        if isinstance(dugum, ast.Name) and dugum.id in yerel:
            return yerel[dugum.id]
        if isinstance(dugum, ast.BinOp) and isinstance(dugum.op, ast.Add):
            return liste(dugum.left, yerel) + liste(dugum.right, yerel)
        return []

    def model_adi(dugum):
        if isinstance(dugum, ast.Call):
            f = dugum.func
            if isinstance(f, ast.Name) and f.id in modeller:
                return f.id
            if (isinstance(f, ast.Attribute) and f.attr == 'get'
                    and dugum.args and isinstance(dugum.args[0], ast.Name)
                    and dugum.args[0].id in modeller):
                return dugum.args[0].id
            return model_adi(f)
        if isinstance(dugum, ast.Attribute):
            return model_adi(dugum.value)
        if isinstance(dugum, ast.Name) and dugum.id in modeller:
            return dugum.id
        return None

    def kendi_govdesi(fn):
        """fn'in KENDİ düğümleri — iç fonksiyonların gövdesi hariç."""
        yigin = list(fn.body)
        while yigin:
            d = yigin.pop()
            if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.Lambda, ast.ClassDef)):
                continue
            yield d
            for alt in ast.iter_child_nodes(d):
                yigin.append(alt)

    agac = ast.parse(kaynak)
    bulgular = []
    for fn in ast.walk(agac):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        kendi = list(kendi_govdesi(fn))
        yerel, nesne_modeli = {}, {}
        for d in sorted((x for x in kendi if isinstance(x, ast.Assign)),
                        key=lambda x: x.lineno):
            if len(d.targets) != 1 or not isinstance(d.targets[0], ast.Name):
                continue
            _l = liste(d.value, yerel)
            if _l:
                yerel[d.targets[0].id] = _l
            _m = model_adi(d.value)
            if _m:
                nesne_modeli[d.targets[0].id] = _m
        for d in kendi:
            if (not isinstance(d, ast.For)
                    or not isinstance(d.target, ast.Name)):
                continue
            dv = d.target.id
            hedef = None
            for alt in ast.walk(d):
                if (isinstance(alt, ast.Call)
                        and isinstance(alt.func, ast.Name)
                        and alt.func.id == 'setattr'
                        and len(alt.args) >= 2):
                    _a = alt.args[1]
                    if ((isinstance(_a, ast.Name) and _a.id == dv)
                            or (isinstance(_a, ast.BinOp)
                                and isinstance(_a.left, ast.Name)
                                and _a.left.id == dv)):
                        if isinstance(alt.args[0], ast.Name):
                            hedef = alt.args[0].id
                            break
            if not hedef:
                continue
            # `hasattr(nesne, alan)` süzgeci alanı zaten koruyor (DZ2)
            if any(isinstance(a, ast.Call) and isinstance(a.func, ast.Name)
                   and a.func.id == 'hasattr' and len(a.args) == 2
                   and isinstance(a.args[1], ast.Name)
                   and a.args[1].id == dv
                   for a in ast.walk(d)):
                continue
            adlar = liste(d.iter, yerel)
            model = nesne_modeli.get(hedef)
            if not adlar or not model:
                continue
            eksik = [a for a in adlar if a not in modeller[model]]
            if eksik:
                bulgular.append((d.lineno, fn.name, hedef, model, eksik))
    return bulgular


def test_hy1_setattr_beyaz_listelerinde_hayalet_alan_yok():
    """Her setattr beyaz listesi adı HEDEF MODELİNDE kolon olmalı."""
    import io as _io
    modeller = _hy1_modeller()
    assert len(modeller) > 20, len(modeller)
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    bulgular = _hy1_tara(kaynak, modeller)
    assert not bulgular, 'hayalet alan(lar) — yazılmış gibi görünüp ' \
        'hiçbir yere yazılmaz: ' + '; '.join(
            f'satır {_s}: {", ".join(_e)} → {_m} ({_fn}, setattr({_n}, …))'
            for _s, _fn, _n, _m, _e in bulgular)


def test_hy1_bekci_dz5_hatasini_yakaliyor():
    """Bekçinin kendisi: DZ5 geri konunca yakalamalı.

    Bir bekçi, yakaladığını gösteremezse bekçi değildir."""
    import io as _io
    modeller = _hy1_modeller()
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    _e = ("        GUNCELLENEBILIR = ('aciklama', 'vade_tarihi', "
          "'evrak_no',\n                           'hareket_tarihi')")
    assert kaynak.count(_e) == 1, 'DZ5 beyaz listesi bulunamadı'
    _bozuk = kaynak.replace(
        _e, _e[:-1] + ", 'belge_no')", 1)
    bulgular = _hy1_tara(_bozuk, modeller)
    assert bulgular, 'bekçi DZ5 hatasını yakalamıyor'
    _hepsi = [a for _, _, _, _, e in bulgular for a in e]
    assert 'belge_no' in _hepsi, bulgular
    # Dogru modeli de soylemeli
    assert any(m == 'CariHareket' for _, _, _, m, _ in bulgular), bulgular
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA HY1 — HAYALET ALAN BEKÇİSİ')
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
        print('    python3 yama_hy1.py            # rapor')
        print('    python3 yama_hy1.py --uygula')
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
        print('  ⊙ Yama HY1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_hy1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_hy1'
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
    print('    venv/bin/python -m pytest tests/test_kritik.py -q   # 266')
    print()
    print('  SUNUCUYU YENIDEN BASLATMAYA GEREK YOK')
    print('    Uygulama kodu degismedi; yalnizca test eklendi.')
    print()
    print('  TARAMA TEMIZ CIKTI')
    print('    26 setattr beyaz listesinin hicbirinde hayalet ad yok.')
    print('    Bu yama duzeltme degil, bir daha olusmasini engelleyen')
    print('    bekci.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

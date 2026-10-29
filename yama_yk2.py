#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA YK2 — YAZMA MUHAFIZI İÇİN BEKÇİ (tarama TEMİZ çıktı)
===========================================================

ÖNKOŞUL: **yama_em2.py uygulanmış olmalı.** Betik denetliyor.
Yalnız test dosyasına dokunuyor. `flask_app.py` DEĞİŞMİYOR.
Şema yok, göç yok.

═══ TARANAN SINIF ═══

Yazma muhafızı, yolu bir modüle eşlemeye çalışıyor. Eşleşmezse:

      # Tanimlanmamis API - sessizce gec
      return None

Yani **fail-open**: haritaya girmemiş bir yazma ucu, yalnızca OKUMA
yetkili bir kullanıcıya da açık olur. YK1 (19.09) bunun bir
örneğini yakalamış: yalnız okuma yetkili kullanıcı `POST /api/cek`
ile çek kaydedebiliyormuş — cariye alacak hareketi de oluşuyormuş.

═══ SONUÇ: TEMİZ ═══

271 `/api/` ucunun hepsinde bir kapı var. 147 yazma ucunun 31'i
hiçbir haritaya eşleşmiyor ama hiçbiri açık değil:

  · `/api/diag/*` — `_diag_guard` bir `before_request` kancası ve
    ADMIN şartı koyuyor (F0-3). Tek kapı, 22 route.
  · `/api/ortaklik/*`, `/api/aktivite/*`, `/api/erisim/*` — kendi
    içlerinde `_yetki_var_mi` / `_erisim_verebilir_mi` sorup 403
    dönüyorlar.
  · `/api/v2/eposta/ayar` — BİLEREK herkese açık: kullanıcı yalnız
    KENDİ SMTP ayarını yazıyor ve kullanıcı adı gövdeden değil
    OTURUMDAN alınıyor (EP2). Modül yetkisi aramak yanlış olurdu.
  · `/api/doviz_kur/guncelle` — yazdığı veri çağırandan değil
    TCMB'den geliyor ve her ekran kura muhtaç.

Yani düzeltilecek bir şey çıkmadı. Çıkan tek şey bekçi.

═══ BEKÇİ ═══

Muhafızın varsayılanı "sessizce geç" olduğu sürece bu sonuç
BUGÜNE ait. Yarın eklenecek bir yazma ucu haritaya girmezse ve
kendi denetimini de yapmazsa, sessizce açık kalır — kimse fark
etmez. Test onu sesli hâle getiriyor: fail-open varsayılan,
test zamanında fail-loud oluyor.

KANITLANDI: haritasız ve denetimsiz bir deneme ucu ekledim, bekçi
tam onu gösterdi —

      POST /api/yk2deneme/sil (api_yk2_deneme)

═══ KENDİ BEKÇİMDE İKİ KUSUR BULDUM ═══

İlk hâli 12 ucu "açık" diye işaretledi. İkisi de benim hatamdı:

  · `/api/diag/*` toplu korunuyor ama koruma fonksiyon gövdesinde
    iz bırakmıyor (`before_request`). 11 diag ucu yanlışlıkla
    işaretlendi.
  · "Kendi denetimini yapıyor"u AD LİSTESİYLE arıyordum;
    `_erisim_verebilir_mi` listede yoktu ve kapalı bir uç açık
    göründü. Artık en genel işarete bakıyor: gövde 403
    dönebiliyor mu.

Bunu yazıyorum çünkü bir bekçi bir gün patlarsa önce KENDİSİNDEN
şüphe edilmeli — bu oturumda üç kez o oldu.

═══ DOĞRULANDI ═══
  282 test geçti (281 + 1). Uygulama kodu değişmedi, sunucuyu
  yeniden başlatmaya gerek yok.

DOSYALAR
--------
  tests/test_kritik.py   1 yeni test

KULLANIM
--------
  python3 yama_yk2.py            # RAPOR
  python3 yama_yk2.py --uygula
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
    'tests/test_kritik.py': 'def test_yk2_her_yazma_ucu_ya_haritada_ya_kendi_denetimini_yapiyor',
}
ONKOSUL = {
    'tests/test_kritik.py': 'def test_em2_stok_listesinin_satiri_ve_ozeti_ayni_sayiyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('tests/test_kritik.py', 'YK2 · tests/test_kritik.py blok 1',
     r'''        'ekran kısaltmayı kendisi türetiyor — kural iki yerde olur'
''',
     r'''        'ekran kısaltmayı kendisi türetiyor — kural iki yerde olur'


# ══════════════════════════════════════════════════════════════════
#  YK2 · YAZMA MUHAFIZININ VARSAYILANI "SESSİZCE GEÇ"
#
#  Yazma muhafızı yolu bir modüle eşlemeye çalışıyor; eşleşmezse:
#      # Tanimlanmamis API - sessizce gec
#      return None
#  Yani FAIL-OPEN. Haritaya eklenmemiş bir yazma ucu, yalnızca
#  OKUMA yetkili bir kullanıcıya da açık olur.
#
#  YK1 (19.09) bunun bir örneğini yakalamıştı: yalnız okuma yetkili
#  kullanıcı `POST /api/cek` ile çek kaydedebiliyordu.
#
#  TARAMA BUGÜN TEMİZ: 147 yazma ucunun 31'i hiçbir haritaya
#  eşleşmiyor ama hepsi KENDİ içinde yetki soruyor (`_yetki_var_mi`
#  ya da `_diag_guard`), biri de bilerek herkese açık (`/api/v2/
#  eposta/ayar` — kullanıcı yalnız KENDİ SMTP ayarını yazıyor,
#  kullanıcı adı gövdeden değil oturumdan geliyor).
#
#  Bu test o durumu SABİTLER. Yarın eklenecek bir yazma ucu
#  haritaya girmez ve kendi denetimini de yapmazsa, sessizce açık
#  kalmak yerine takımı kırar.
# ══════════════════════════════════════════════════════════════════
_YK2_MUAF = {
    # Kullanici YALNIZCA kendi SMTP ayarini yazar; kullanici adi
    # oturumdan aliniyor (EP2). Modul yetkisi aramak yanlis olurdu.
    '/api/v2/eposta/ayar',
    # TCMB'den kur ceker. Yazdigi veri CAGIRANDAN gelmiyor, TCMB'den
    # geliyor; ve her ekran kura muhtac. Modul yetkisi aramak
    # kullaniciyi kendi ekraninda kilitlerdi.
    '/api/doviz_kur/guncelle',
}
# `/api/diag/` TOPLU korunuyor: `_diag_guard` bir `before_request`
# kancasi ve ADMIN sarti koyuyor (F0-3). Fonksiyon govdesinde iz
# birakmadigi icin ayrica muaf tutuluyor — ilk halimde 11 diag ucu
# "acik" diye isaretlenmisti, oysa hepsi kapali.


def test_yk2_her_yazma_ucu_ya_haritada_ya_kendi_denetimini_yapiyor():
    """Yazma ucu ya modüle eşlenmeli ya kendi yetkisini sormalı."""
    import ast as _ast
    import io as _io
    import re as _re
    kaynak = _io.open(os.path.join(KOK, 'flask_app.py'),
                      encoding='utf-8').read().replace('\r\n', '\n')
    agac = _ast.parse(kaynak)

    def _deger(ad):
        for d in _ast.walk(agac):
            if (isinstance(d, _ast.Assign) and len(d.targets) == 1
                    and isinstance(d.targets[0], _ast.Name)
                    and d.targets[0].id == ad):
                try:
                    return _ast.literal_eval(d.value)
                except Exception:
                    return []
        return []

    url_map = _deger('URL_MODUL_MAP')
    yazma_ek = _deger('YAZMA_EK_MAP')
    assert url_map and yazma_ek, 'haritalar okunamadı'
    # ALT_YOL_DESENLERI derlenmiş regex taşıyor — desenleri kaynaktan
    desenler = [_re.compile(m) for m in _re.findall(
        r"_re_alt\.compile\(r'([^']+)'\)", kaynak)]
    assert desenler, 'alt yol desenleri okunamadı'

    # Her yazma ucunun KENDI govdesinde denetim var mi
    kendi = {}
    for fn in _ast.walk(agac):
        if not isinstance(fn, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            continue
        g = _ast.unparse(fn)
        # "Kendi denetimini yapiyor"un en genel isareti: govdesi
        # 403 DONEBILIYOR. Ad listesiyle aramak eksik kaliyordu —
        # `_erisim_verebilir_mi` gibi ozel kapilar listede yoktu ve
        # kapali bir uc "acik" gorunuyordu.
        kendi[fn.name] = ('403' in g) or any(k in g for k in (
            '_yetki_var_mi', '_diag_guard', "session.get('rol')",
            '_erisim_admin_mi'))

    YAZMA = {'POST', 'PUT', 'PATCH', 'DELETE'}
    acik = []
    for kural in fa.app.url_map.iter_rules():
        if not (kural.methods or set()) & YAZMA:
            continue
        yol = str(kural.rule)
        if not yol.startswith('/api/'):
            continue
        if yol in _YK2_MUAF or yol.startswith('/api/diag/'):
            continue
        ornek = _re.sub(r'<[^>]+>', 'X', yol)
        eslesti = (any(d.match(ornek) for d in desenler)
                   or any(ornek.startswith(o) for o, _ in url_map)
                   or any(ornek.startswith(o) for o, _ in yazma_ek))
        if eslesti:
            continue
        _fn = str(kural.endpoint).split('.')[-1]
        if kendi.get(_fn):
            continue        # kendi denetimini yapiyor
        acik.append(f'{",".join(sorted((kural.methods or set()) & YAZMA))} '
                    f'{yol} ({_fn})')
    assert not acik, (
        'yazma muhafızından sessizce geçen uç(lar) — yalnız OKUMA '
        'yetkili kullanıcı da çağırabilir: ' + '; '.join(sorted(acik)))
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA YK2 — YAZMA MUHAFIZI İÇİN BEKÇİ (tarama TEMİZ çıktı)')
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
        print('    python3 yama_yk2.py            # rapor')
        print('    python3 yama_yk2.py --uygula')
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
        print('  ⊙ Yama YK2 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_yk2.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_yk2'
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
    print('    venv/bin/python -m pytest tests/test_kritik.py -q   # 282')
    print()
    print('  SUNUCUYU YENIDEN BASLATMAYA GEREK YOK')
    print('    Uygulama kodu degismedi; yalnizca test eklendi.')
    print()
    print('  TARAMA TEMIZ CIKTI')
    print('    147 yazma ucunun hicbiri acik degil. Bu yama duzeltme')
    print('    degil: muhafizin "haritada yoksa sessizce gec"')
    print('    varsayilanini test zamaninda SESLI hale getiriyor.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

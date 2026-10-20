#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA OR4 — "istek_hatasi" GERÇEK HATAYI GİZLİYORDU
===================================================

ÖNKOŞUL: yama_or3.py uygulanmış olmalı.

Gönderdiğin ekran görüntüsündeki `istek_hatasi` bir hata MESAJI
değil, bir İŞARET. Ve onu ekrana basan bendim.

── NE OLUYORDU ──
  `api()` yardımcısı sunucudan gelen hatayı ZATEN kullanıcıya
  gösteriyor, sonra `istek_hatasi` adında bir işaret fırlatıyor ki
  çağıran fonksiyon işlemi durdurabilsin.

  Ortaklık sayfasında sekiz yerde şunu yazmışım:

      catch (e) { bildir(e.message || '...', true); }

  Yani sunucunun söylediği gerçek sebep bir an görünüyor, hemen
  ardından onun üstüne `istek_hatasi` basılıyordu. Hata teşhis
  edilemez hâle geliyordu — senin yaşadığın tam olarak bu.

  Projedeki ev kuralı zaten şöyleymiş:

      catch (e) { /* api() zaten bildiriyor */ }

  Sekiz yerin hepsi o kurala çekildi ve test sabitledi.

── ASIL HATA NE? HENÜZ BİLMİYORUM ──
  Sermaye ucunu birebir senin gönderdiğin gövdeyle denedim
  (taraf=ortak, yön=geri_aldi, 5000 USD, 20.10.2026) — 200 döndü,
  anapara −5000 olarak hesaba girdi. Yani uç çalışıyor; sorun
  senin verinde ya da ortamında.

  Bu yamadan sonra ekran GERÇEK mesajı gösterecek. Tekrar dene;
  ne yazdığını bana ilet. Görünmezse sunucu günlüğünde duruyor:

      sudo journalctl -u milestone-erp -n 60 --no-pager

── NE YAPMADIM ──
  Sebebini bilmeden sermaye ucuna dokunmadım. Çalıştığını ölçtüğüm
  bir kodu "ihtimale karşı" değiştirmek, asıl sorunu başka bir
  yere taşımak olurdu.

DOSYALAR
--------
  templates/ortaklik.html  8 catch bloğu
  tests/test_kritik.py     1 yeni test

Şema yok, göç yok.

KULLANIM
--------
  python3 yama_or4.py            # RAPOR
  python3 yama_or4.py --uygula
  sudo systemctl restart milestone-erp
  (tarayıcıda Ctrl+F5 — şablon değişti)
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
    'templates/ortaklik.html': 'api() zaten bildirdi',
    'tests/test_kritik.py': 'def test_or4_sunucunun_hata_mesaji_ustu_ortulmuyor',
}
ONKOSUL = {
    'templates/ortaklik.html': 'async function isListesiYukle()',
    'tests/test_kritik.py': 'def test_or3_baglanabilir_liste_bagli_isleri_elemeli',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('templates/ortaklik.html', 'OR4 · templates/ortaklik.html blok 1',
     r'''  catch (e) { bildir(e.message || 'Liste alınamadı', true); return; }
''',
     r'''  catch (e) { return; }                 /* api() zaten bildirdi */
'''),
    ('templates/ortaklik.html', 'OR4 · templates/ortaklik.html blok 2',
     r'''  catch (e) { bildir(e.message || 'Detay alınamadı', true); return; }
''',
     r'''  catch (e) { return; }                 /* api() zaten bildirdi */
'''),
    ('templates/ortaklik.html', 'OR4 · templates/ortaklik.html blok 3',
     r'''  } catch (e) { bildir(e.message || 'Kaydedilemedi', true); return; }
''',
     r'''  } catch (e) { return; }               /* api() zaten bildirdi */
'''),
    ('templates/ortaklik.html', 'OR4 · templates/ortaklik.html blok 4',
     r'''  catch (e) { bildir(e.message || 'Silinemedi', true); return; }
''',
     r'''  catch (e) { return; }                 /* api() zaten bildirdi */
'''),
    ('templates/ortaklik.html', 'OR4 · templates/ortaklik.html blok 5',
     r'''  catch (e) { bildir(e.message || 'Eklenemedi', true); return; }
''',
     r'''  catch (e) { return; }                 /* api() zaten bildirdi */
'''),
    ('templates/ortaklik.html', 'OR4 · templates/ortaklik.html blok 6',
     r'''  } catch (e) { bildir(e.message || 'Silinemedi', true); return; }
''',
     r'''  } catch (e) { return; }               /* api() zaten bildirdi */
'''),
    ('templates/ortaklik.html', 'OR4 · templates/ortaklik.html blok 7',
     r'''  } catch (e) { bildir(e.message || 'İşlenemedi', true); return; }
''',
     r'''  } catch (e) { return; }               /* api() zaten bildirdi */
'''),
    ('templates/ortaklik.html', 'OR4 · templates/ortaklik.html blok 8',
     r'''  } catch (e) { bildir(e.message || 'Geri alınamadı', true); return; }
''',
     r'''  } catch (e) { return; }               /* api() zaten bildirdi */
'''),
    ('tests/test_kritik.py', 'OR4 · tests/test_kritik.py blok 1',
     r'''               for u in h2['uyarilar']), h2['uyarilar']
''',
     r'''               for u in h2['uyarilar']), h2['uyarilar']


def test_or4_sunucunun_hata_mesaji_ustu_ortulmuyor():
    """OR4: `api()` hatayı zaten bildiriyor; üstüne yazma.

    `api()` hata mesajını kullanıcıya gösterip `istek_hatasi` adlı
    bir İŞARET fırlatıyor. Onu `e.message` diye basmak, sunucunun
    söylediği gerçek sebebin üstünü örtüyordu: ekranda yalnız
    'istek_hatasi' kalıyor ve hata teşhis edilemiyordu (ölçüldü —
    sermaye hareketi eklerken tam bu oldu).

    Ev kuralı: `catch (e) { /* api() zaten bildiriyor */ }`."""
    import io as _io, re as _re
    h = _io.open('templates/ortaklik.html', encoding='utf-8').read()
    kotu = _re.findall(r'catch \(e\) \{[^}]*bildir\(e\.message', h)
    assert not kotu, f'{len(kotu)} yerde api() hatasının üstüne yazılıyor'
    # İşaretin kendisi hiçbir yerde kullanıcıya gösterilmemeli
    assert 'istek_hatasi' not in h
'''),
]

TAM_ICERIK = {}

def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA OR4 — GERCEK HATA MESAJI GORUNSUN')
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
        print('    python3 yama_or4.py            # rapor')
        print('    python3 yama_or4.py --uygula')
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
        print('  ⊙ Yama OR4 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_or4.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_or4'
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
    print('    2) Tarayicida Ctrl+F5')
    print('    3) venv/bin/python -m pytest tests/test_kritik.py -q')
    print()
    print('  BAKILACAK YER')
    print('    Analiz -> Is Ortakliklari -> bir ortaklik ac')
    print('    Sermaye hareketini TEKRAR DENE. Hata cikarsa artik')
    print('    sunucunun gercek mesaji gorunecek — onu bana ilet.')
    print('    Gorunmezse:  sudo journalctl -u milestone-erp -n 60 --no-pager')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

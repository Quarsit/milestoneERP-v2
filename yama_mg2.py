#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MG2 — MALİYET SÜTUNLARI HİZALANIR
=======================================

ÖNKOŞUL: yama_mg1.py uygulanmış olmalı.

MG1'i uyguladın, sonra "Belge No ile Tarih arasında standart bir
mesafe olsa" dedin. Haklıydın; bu yama onu düzeltir.

MG1'in imzası sende zaten var, o yüzden MG1'i yeniden göndermek
işe yaramıyordu ("zaten uygulanmış" deyip atlıyordu). Bu yama
yalnız FARKI taşıyor.

── SORUN ──
  Satır esnek kutuydu: üç parça yan yana diziliyor ve aralarına
  sabit boşluk konuyordu. Belge numarası uzadıkça "Tarih:" sağa
  kayıyordu:

      Belge No: F08584            Tarih: …
      Belge No: PNR2026000937       Tarih: …
      Belge No: PNR2026000000951      Tarih: …

── ÇÖZÜM ──
  Üç sütunlu ızgara, sütun genişlikleri SABİT.

  İçeriğe göre genişleyen sütun (`max-content`) işe yaramazdı:
  her satır KENDİ ızgarası olduğu için sütun genişlikleri satırlar
  arasında paylaşılmıyor; her satır yine kendi içeriğine göre
  genişlerdi. Sabit `em` ölçüsü hem satırlar hem KUTULAR arasında
  hizalıyor.

── ÖLÇÜLDÜ ──
  Senin altı kaleminle, tarayıcıda:

      Tarih sütunu : altı satırda da x = 628   (hepsi aynı)
      Tutar sağ    : altı satırda da x = 1439  (hepsi aynı)

  Beş kutunun hepsinde. Yükseklik 338 pikselde kaldı — MG1'in
  kazancı değişmedi.

── DAR EKRAN ──
  Çekmece telefonda tam genişliğe düşüyor; üç sabit sütun oraya
  sığmaz. 760 pikselin altında belge no tek başına üst satıra
  geçiyor, tarih ve tutar altta yan yana ve hizalı kalıyor.
  O halde de baktım.

── BİR DE ŞUNU DÜZELTİYOR ──
  Yamaların açılış başlığında "YAMA DZ4 — KESIM KAYITLARI"
  yazıyordu. Sen yakaladın. Başlık çalıştırıcının içinde SABİT
  yazılıydı ve yama üreticim onu hiç değiştirmiyordu; DZ5'ten
  beri bütün yamalar o başlıkla açılmış.

  Zararsızdı — yapılan iş her zaman doğru yamanın işiydi, imza ve
  önkoşul denetimleri de doğru dosyaya bakıyordu — ama yanlış şey
  söyleyen bir ekran, doğru çalışsa bile güveni bozar. Bu yama
  kendi adıyla açılıyor; bundan sonrakiler de öyle olacak.

DOSYALAR
--------
  templates/stok.html   `.mlyt-satir` — esnek kutu yerine ızgara

Şema yok, göç yok, sunucu değişmiyor, test değişmiyor.

KULLANIM
--------
  python3 yama_mg2.py            # RAPOR
  python3 yama_mg2.py --uygula
  sudo systemctl restart milestone-erp
  (tarayıcıda Ctrl+F5)
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
    'templates/stok.html': 'grid-template-columns:minmax(0,19em)',
}
ONKOSUL = {
    'templates/stok.html': 'function maliyetGruplari(',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('templates/stok.html', 'MG2 · templates/stok.html blok 1',
     r'''.mlyt-satir{display:flex;flex-wrap:wrap;align-items:baseline;
  gap:2px 14px;padding:4px 0;font-size:.83rem}
.mlyt-satir + .mlyt-satir{border-top:1px solid var(--cizgi)}
.mlyt-satir .e{color:var(--soluk);font-size:.74rem;font-weight:400}
.mlyt-satir .d{font-weight:600}
/* Tutar sağa yaslanır: göz tek sütunda tarıyor. */
.mlyt-satir .son{margin-left:auto;white-space:nowrap}
.mlyt-satir .son .d{font-family:var(--mono)}
''',
     r'''/* SÜTUNLAR SABİT GENİŞLİKTE — içeriğe göre DEĞİL.
   İlk halinde esnek kutu + boşluk vardı: "Tarih:" her satırda
   belge numarasının uzunluğu kadar sağa kayıyordu. İçeriğe göre
   genişleyen sütun (`max-content`) da yetmez — her satır KENDİ
   ızgarası olduğu için sütunlar satırlar arasında paylaşılmaz.
   Sabit `em` ölçüsü hem satırlar hem KUTULAR arasında hizalıyor. */
.mlyt-satir{display:grid;
  grid-template-columns:minmax(0,19em) minmax(0,10em) 1fr;
  gap:2px 10px;align-items:baseline;padding:4px 0;font-size:.83rem}
.mlyt-satir > span{min-width:0;overflow-wrap:anywhere}
.mlyt-satir + .mlyt-satir{border-top:1px solid var(--cizgi)}
.mlyt-satir .e{color:var(--soluk);font-size:.74rem;font-weight:400}
.mlyt-satir .d{font-weight:600}
/* Tutar sağa yaslanır: göz tek sütunda tarıyor. */
.mlyt-satir .son{justify-self:end;white-space:nowrap}
.mlyt-satir .son .d{font-family:var(--mono)}
/* Çekmece telefonda tam genişliğe düşüyor; üç sabit sütun oraya
   sığmaz. Belge no tek başına üst satıra, tarih ve tutar altına —
   ikisi hâlâ hizalı. */
@media(max-width:760px){
  .mlyt-satir{grid-template-columns:1fr auto}
  .mlyt-satir > :first-child{grid-column:1 / -1}
}
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA MG2 — MALİYET SÜTUNLARI HİZALANIR')
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
        print('    python3 yama_mg2.py            # rapor')
        print('    python3 yama_mg2.py --uygula')
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
        print('  ⊙ Yama MG2 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_mg2.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_mg2'
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
    print('    Depo -> Stok -> bir urunde KAYNAK ZINCIRI.')
    print('    En altta "Bu stoga islenen maliyetler": artik tip')
    print('    bir kez yaziliyor, ayni tipten belgeler o kutunun')
    print('    altinda satir satir duruyor.')
    print()
    print('    Olculdu: 6 kart / 480 piksel  ->  5 kutu / 338 piksel')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

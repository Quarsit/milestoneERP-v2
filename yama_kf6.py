#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA KF6 — SIFIRLAMA KİMİ KİLİTLEYECEĞİNİ SÖYLESİN
===================================================

ÖNKOŞUL: yama_kf.py uygulanmış olmalı.

── SORUN ──
  KF2 ile arayüzdeki firma silmeye bir denetim koydum: bir firma
  herhangi bir kullanıcının TEK firmasıysa silinmiyor ve kimi
  kilitleyeceği ADIYLA söyleniyor.

  `sifirla2.py --tumunu-sil` ise aynı işi yapıyor — firma siliyor —
  ama o denetimden HABERSİZ. Yani arayüzden yapamadığın şeyi komut
  satırından farkında olmadan yapabiliyordun: sıfırlamadan sonra bir
  kullanıcının izin listesi boşalır, giriş yapamaz ve sebebi hiçbir
  yerde yazmaz.

  İki yol arasındaki bu fark sessiz bir tuzak. Bu projede aynı
  sınıftan hatalar çok çıktı: bir kapı kapalı, komşusu açık.

── ÇÖZÜM ──
  Sıfırlama artık --onayla'dan ÖNCE kimin kilitleneceğini listeliyor,
  sildikten SONRA da firmasız kalan varsa tekrar söylüyor.

  ENGELLEMİYOR, bilerek. Sıfırlama zaten bilinçli ve geri alınamaz
  bir iş; "şu kullanıcıyı sonra yeniden atarım" demek geçerli bir
  karar. Ama görmeden karar verilmemeli.

  ADMIN ve PASİF kullanıcılar listeye GİRMEZ:
    · ADMIN rolü kapsamdan bağımsız olarak bütün firmaları görüyor
      (_kullanici_firma_idleri) — kilitlenemez. İlk sürümde onu da
      listeliyordum ve uyarı "admin giremeyecek" diyordu; ÖLÇÜLDÜ.
      Yanlış alarm, uyarının tamamını güvenilmez yapar.
    · Pasif kullanıcı zaten giriş yapamıyor; saymak gürültü olurdu.

── ÖLÇÜLDÜ ──
  Üç firma, üç personel (her biri tek firmada), --kalan=1:
    rapor      → "personel2, personel3 giremeyecek" (admin YOK)
    uygulama   → doğrulamada "2 kullanıcı hiçbir firmada"
    hepsi 'tumu' yapılınca → uyarı HİÇ çıkmıyor
  94 test geçti; altı denetim temiz.

DOSYALAR
--------
  sifirla2.py

Şema yok, göç yok, arayüz değişmiyor.

KULLANIM
--------
  python3 yama_kf6.py            # RAPOR
  python3 yama_kf6.py --uygula
"""

import os
import py_compile
import shutil
import subprocess
import sys
import tempfile

UYGULA = '--uygula' in sys.argv
KOK = os.path.dirname(os.path.abspath(__file__))

DOSYA_IMZA = {'sifirla2.py': 'def kilitlenecekler'}
ONKOSUL = {'sifirla2.py': "'kullanici_firma':"}

DEGISIKLIKLER = [
    ('sifirla2.py', 'KF6 blok 1',
     r'''    return d, toplam


''',
     r'''    return d, toplam


def kilitlenecekler(b, silinecek_idler, kalan_id):
    """Bu firmalar silinince SİSTEME GİREMEYECEK kullanıcılar (KF6).

    Kapsamı 'secili' olan ve ayakta kalan firmalardan HİÇBİRİNE
    atanmamış kullanıcı, sıfırlama sonrası giriş yapamaz: izin
    listesi boşalır. Ekran bu silmeyi zaten reddediyor ve kimi
    kilitleyeceğini adıyla söylüyor; BU BETİK söylemiyordu.

    İki yol arasındaki bu fark sessiz bir tuzaktı: arayüzden
    yapamadığın şeyi komut satırından farkında olmadan yapmak.
    Burada ENGELLEMİYORUZ — sıfırlama zaten bilinçli ve geri
    alınamaz bir iş — ama kimin kilitleneceğini SÖYLÜYORUZ, ki
    --onayla'dan önce görülsün.
    """
    if 'kullanici_firma' not in mevcut or 'kullanicilar' not in mevcut:
        return []
    try:
        # ADMIN ve PASİF kullanıcılar DIŞARIDA:
        #   · ADMIN rolü kapsamdan bağımsız olarak bütün firmaları
        #     görüyor (_kullanici_firma_idleri) — kilitlenemez.
        #     İlk sürümde onu da listeliyordum ve uyarı "admin
        #     giremeyecek" diyordu; yanlış alarm, uyarının tamamını
        #     güvenilmez yapar.
        #   · Pasif kullanıcı zaten giriş yapamıyor; onu saymak
        #     gürültü olurdu.
        return [r[0] for r in b.execute(text(
            'SELECT k.ad FROM kullanicilar k '
            "WHERE COALESCE(k.firma_kapsam, 'secili') <> 'tumu' "
            "  AND UPPER(COALESCE(k.rol, '')) <> 'ADMIN' "
            '  AND COALESCE(k.aktif, :e) = :e '
            '  AND NOT EXISTS (SELECT 1 FROM kullanici_firma kf '
            '                  WHERE kf.kullanici_id = k.id '
            '                    AND kf.firma_id = :kalan) '
            'ORDER BY k.ad'), {'kalan': kalan_id, 'e': True}).fetchall()]
    except Exception:
        return []


'''),
    ('sifirla2.py', 'KF6 blok 2',
     r'''    print("   görünmez — kullanıcı 'verim gitti' sanar.")
''',
     r'''    print("   görünmez — kullanıcı 'verim gitti' sanar.")
    # ── KF6 · KİM KİLİTLENİYOR ──
    with motor.connect() as _b:
        _kilit = kilitlenecekler(_b, [f['id'] for f in SILINEN_FIRMALAR],
                                 KALAN_FIRMA['id'])
    if _kilit:
        print()
        print("   ⚠ BU KULLANICILAR SİSTEME GİREMEYECEK:")
        for _ad in _kilit:
            print(f"       {_ad}")
        print()
        print("   Kapsamları 'seçili firmalar' ve kalan firmaya")
        print("   atanmamışlar; sıfırlamadan sonra izin listeleri boş")
        print("   kalıyor. Arayüzdeki firma silme bunu REDDEDİYOR,")
        print("   burada engellemiyorum — ama bilerek devam et.")
        print()
        print("   Çözüm (sıfırlamadan SONRA da olur):")
        print("     Ayarlar → Kullanıcılar → kullanıcıyı düzenle →")
        print(f"     firma kapsamı → [{KALAN_FIRMA['id']}] "
              f"{KALAN_FIRMA['ad']} işaretle")
'''),
    ('sifirla2.py', 'KF6 blok 3',
     r'''              f"(önce {tr(beklenen)})")

''',
     r'''              f"(önce {tr(beklenen)})")

    # 4a · KF6 · firmasız kalan kullanıcı
    if KIP == 'tumunu' and 'kullanici_firma' in mevcut:
        _k2 = kilitlenecekler(b, [], KALAN_FIRMA['id'])
        if _k2:
            print(f"   ⚠ {len(_k2)} kullanıcı hiçbir firmada: "
                  f"{', '.join(_k2)}")
            print("     Giriş yapamazlar — Ayarlar → Kullanıcılar'dan")
            print("     firma ataması yapılmalı. (Hata değil, uyarı:")
            print("     sıfırlamanın beklenen sonucu olabilir.)")
        else:
            print("   ✓ her kullanıcı en az bir firmada çalışabiliyor")

'''),
]


def main():
    print('=' * 70)
    print('  YAMA KF6 — SIFIRLAMA KILITLENMEYI SOYLESIN')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    gruplar = {}
    for dosya, aciklama, eski, yerine in DEGISIKLIKLER:
        gruplar.setdefault(dosya, []).append((aciklama, eski, yerine))

    sonuclar, hata, zaten = {}, False, []

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
        print('  ⊙ Yama KF6 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_kf6.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_kf6'
            shutil.copy2(yol, yedek)
            _y = f'    yedek  : {os.path.relpath(yedek, KOK)}'
        else:
            _y = '    (yeni dosya — yedek yok)'
        with open(yol, 'w', encoding='utf-8', newline='') as f:
            f.write(icerik)
        if yol.endswith('.sh'):
            os.chmod(yol, 0o755)
        print(f'  ✓ yazıldı: {os.path.relpath(yol, KOK)}')
        print(_y)

    print('\n  ✓ YAMA UYGULANDI')
    print()
    print('  Servisi yeniden baslatmak GEREKMIYOR — yalnizca CLI')
    print('  betigi degisti.')
    print()
    print('  Sifirlama raporunu goruntule (hicbir sey silmez):')
    print('    venv/bin/python sifirla2.py --tumunu-sil --kalan=1')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

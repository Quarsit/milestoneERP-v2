#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MF3C — FİRMA SEÇİM EKRANI: CSRF + HER ZAMAN AÇILSIN
=========================================================

ÖNKOŞUL: MF3B uygulanmış olmalı.

İKİ İŞ
------

1) ENGELLEYİCİ HATA · "Güvenlik dogrulamasi basarisiz"
   Firma seçilemiyor, sisteme girilemiyordu.

   SEBEP: `firma_sec.html` bağımsız bir sayfa — base.html'in `api()`
   yardımcısını kullanmıyor, düz `fetch` çağırıyor. `api()` CSRF
   token'ını başlığa KENDİSİ ekliyor; düz fetch eklemiyor.
   `_csrf_dogrula` da her POST'ta token arıyor ve 403 veriyor.

   BENİM TEST HATAM: MF3B'yi doğrularken `/api/firma/sec` ucunu
   başlığı ELLE koyarak çağırdım. Uç çalıştı, sayfanın kendi JS yolu
   hiç denenmedi. Bu yamanın testi artık ekranı RENDER EDİP token'ı
   sayfadan okuyor — tarayıcının yaptığı neyse o.

   ÇÖZÜM: şablona `{{ csrf_token() }}` geçirilir (bağlam işleyicisi
   zaten var) ve fetch başlığına konur.

2) TEK FİRMADA DA EKRAN AÇILSIN
   MF3B ekranı yalnızca iki ve daha çok firma varken gösteriyordu.
   Oysa yeni firmayı BİR FİRMANIN İÇİNE GİRMEDEN açabilmek gerekiyor —
   tek firma varken de. Artık admin her girişte ekranı görür;
   tek firma varsa tek kart ve "yeni firma ekle" düğmesi çıkar.

   Admin OLMAYAN kullanıcı ekranı yine görmez, doğrudan varsayılan
   firmaya girer.

DOSYALAR
--------
  templates/firma_sec.html  (CSRF başlığı)
  flask_app.py              (tek firma koşulları kalkar)

KULLANIM
--------
  python3 yama_mf3c.py            # RAPOR
  python3 yama_mf3c.py --uygula
  sudo systemctl restart milestone-erp
"""

import os
import sys
import shutil
import py_compile
import tempfile

UYGULA = '--uygula' in sys.argv
KOK = os.path.dirname(os.path.abspath(__file__))

DOSYA_IMZA = {
    'flask_app.py': 'MF3C',
    'templates/firma_sec.html': 'MF3C',
}
ONKOSUL = {
    'flask_app.py': 'def firma_sec_ekran',
    'templates/firma_sec.html': 'async function gonder',
}


DEGISIKLIKLER = [
    # ── 1 · CSRF ──
    ('templates/firma_sec.html', 'MF3C-a · CSRF token sablondan okunur',
     "<script>\nfunction hataGoster(m) {",
     """<script>
/* ── CSRF (MF3C) ──
   Bu sayfa BAĞIMSIZ: base.html'in api() yardımcısı yok, düz fetch
   kullanıyor. api() token'ı başlığa kendisi ekliyordu; düz fetch
   eklemeyince sunucu her POST'a 403 "Güvenlik dogrulamasi basarisiz"
   döndü ve firma seçilemedi. Token bağlam işleyicisinden geliyor. */
const CSRF = '{{ csrf_token() }}';

function hataGoster(m) {"""),
    ('templates/firma_sec.html', 'MF3C-b · fetch basligina token',
     """    headers: { 'Content-Type': 'application/json' },""",
     """    headers: { 'Content-Type': 'application/json',
               'X-CSRF-Token': CSRF },"""),
    # ── 2 · tek firmada da ekran ──
    ('flask_app.py', 'MF3C-c · giriste ekran HER ZAMAN (admin)',
     """                # ── MF3B · GİRİŞTE FİRMA SEÇİMİ ──
                # Birden çok firma varsa admin önce hangisinde
                # çalışacağını seçer (Logo/Mikro/Netsis'teki yerleşik
                # akış). TEK firma varsa ekran hiç gösterilmez —
                # bugünkü giriş aynen kalır.
                try:
                    if (k.rol or '').upper() == 'ADMIN':
                        with firma_atla():
                            _n = Firma.query.filter_by(aktif=True).count()
                        if _n > 1:
                            session.pop('firma_id', None)
                            return redirect(url_for('firma_sec_ekran'))
                except Exception as _e:""",
     """                # ── MF3B/MF3C · GİRİŞTE FİRMA SEÇİMİ ──
                # Admin önce hangi firmada çalışacağını seçer
                # (Logo/Mikro/Netsis'teki yerleşik akış).
                #
                # MF3C: eskiden ekran yalnızca İKİ ve daha çok firma
                # varken çıkıyordu. Oysa yeni firmayı BİR FİRMANIN
                # İÇİNE GİRMEDEN açabilmek gerekiyor — tek firma
                # varken de. Artık koşulsuz.
                #
                # Admin OLMAYAN kullanıcı ekranı görmez: firma seçimi
                # şimdilik admin yetkisinde, onlar varsayılan firmaya
                # girer.
                try:
                    if (k.rol or '').upper() == 'ADMIN':
                        session.pop('firma_id', None)
                        return redirect(url_for('firma_sec_ekran'))
                except Exception as _e:"""),
    ('flask_app.py', 'MF3C-d · tek firmada da ekran acilir',
     """        # Tek firma varsa seçtirecek bir şey yok — doğrudan içeri.
        if len(kayitlar) <= 1:
            return redirect(url_for('dashboard'))""",
     """        # MF3C: tek firma varken de açılır. Ekranın işi yalnızca
        # seçtirmek değil; YENİ FİRMA buradan açılıyor ve bunu bir
        # firmanın içine girmeden yapabilmek gerekiyor. Hiç firma
        # yoksa da sorun değil: liste boş gelir, "yeni firma ekle"
        # durur."""),
]


def main():
    print('=' * 70)
    print('  YAMA MF3C — FİRMA SEÇİM EKRANI: CSRF + HER ZAMAN AÇILSIN')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    gruplar = {}
    for dosya, aciklama, eski, yerine in DEGISIKLIKLER:
        gruplar.setdefault(dosya, []).append((aciklama, eski, yerine))

    sonuclar, hata, zaten = {}, False, []
    for dosya, isler in gruplar.items():
        yol = os.path.join(KOK, dosya)
        print(f'\n── {dosya} ' + '─' * max(0, 52 - len(dosya)))
        if not os.path.exists(yol):
            print(f'  ✗ DOSYA YOK: {yol}')
            print('    Önce: python3 yama_mf3b.py --uygula')
            hata = True
            continue

        with open(yol, 'rb') as f:
            ham = f.read()
        crlf = b'\r\n' in ham
        icerik = ham.decode('utf-8')
        if crlf:
            icerik = icerik.replace('\r\n', '\n')
            print('  · CRLF satır sonu algılandı, korunacak')

        onk = ONKOSUL.get(dosya)
        if onk and onk not in icerik:
            print(f'  ✗ ÖNKOŞUL YOK: "{onk}" yok — önce MF3B uygulanmalı')
            hata = True
            continue
        if DOSYA_IMZA[dosya] in icerik:
            print('  ⊙ İmza zaten var — ATLANIR')
            zaten.append(dosya)
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

        sonuclar[yol] = (yeni.replace('\n', '\r\n') if crlf else yeni)

    print('\n' + '=' * 70)
    if hata:
        print('  ✗ HATA VAR → Hiçbir dosyaya DOKUNULMADI')
        return 1
    if zaten and sonuclar:
        print('  ✗ YARIM DURUM → Hiçbir dosyaya DOKUNULMADI')
        print(f'    imzası olan: {", ".join(zaten)}')
        return 1
    if zaten:
        print('  ⊙ Yama MF3C zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_mf3c.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        yedek = yol + '.yedek_mf3c'
        shutil.copy2(yol, yedek)
        with open(yol, 'w', encoding='utf-8', newline='') as f:
            f.write(icerik)
        print(f'  ✓ yazıldı: {os.path.relpath(yol, KOK)}')
        print(f'    yedek  : {os.path.relpath(yedek, KOK)}')

    print('\n  ✓ YAMA UYGULANDI')
    print()
    print('    sudo systemctl restart milestone-erp')
    print()
    print('  Yeniden başlattıktan sonra tarayıcıda Ctrl+F5 yap —')
    print('  eski sayfa önbellekte kalmışsa token yine eksik gelir.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

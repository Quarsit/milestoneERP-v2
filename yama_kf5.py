#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA KF5 — FİRMA SEÇİM LİSTESİ: GÖRÜNÜM VE ÖLÇEKLENME
======================================================

ÖNKOŞUL: yama_kf.py uygulanmış olmalı.

── SORUN  [EKRAN GÖRÜNTÜSÜNDE] ──
   Yetki penceresindeki firma kutuları dağılmıştı: onay kutusu satır
   boyunca yayılmış, firma adı sağ uca itilmiş, ikinci satırda kutunun
   etrafında kocaman bir çerçeve çıkmıştı.

   SEBEP — `ayarlar.html`'in kendi stil bloğundaki iki kural benim
   işaretleme kutularıma da uyguluyordu:

       .form-alan input { width:100%; border:1px solid; padding:9px 11px }
       .form-alan label { display:block; font-weight:700;
                          text-transform:uppercase; font-size:.72rem }

   Yani kutu "metin girişi" sanılıp tam genişliğe çekilmiş, etiket de
   form başlığı sanılıp küçük gri BÜYÜK HARFE dönmüştü.

   BU HATAYI İKİNCİ KEZ YAPTIM. MF7'de `.kutu` sınıfıyla birebir aynı
   çakışmayı yaşamış ve "bundan sonra şablona sınıf eklerken adın
   kullanılıp kullanılmadığına bakacağım" demiştim. Yine düştüm.

── İLK DÜZELTMEM DE YETMEDİ  [EKRANDA GÖRÜLDÜ] ──
   Ancestor kurallarını geri almak için `.kf-fir label{...}` yazdım.
   Çalışmadı: `.form-alan label` ile AYNI özgüllükte (0,0,1,1) ve
   benim bloğum stil sayfasında ÖNCE geliyordu — eşitlikte SONRAKİ
   kazanır. Ekran görüntüsünde görüldü: kutuyla ad arasında boşluk
   yok (flex uygulanmamış), yazı hâlâ kalın.

   Şimdi İKİSİ BİRDEN: etiketin kendi sınıfı var
   (`label.kf-satir` → 0,0,2,1) ve blok `.form-alan` tanımlarından
   SONRA duruyor. Biri bozulsa öteki tutar.

── ÖLÇEKLENME ──
   "Daha fazla firma eklendikçe daha da kötü olacaktır" — doğruydu;
   liste pencereyi uzatıp Kaydet'i aşağı itiyordu. Artık:

     · kaydırmalı gövde (en çok 208px ≈ 6 satır), pencere büyümüyor
     · başlıkta sayaç: "2 / 12 firma seçili"
     · hiçbiri seçili değilken KIRMIZI: "Hiçbiri seçili değil —
       giriş yapamaz". O kullanıcı gerçekten giremez; bunu kaydetmeden
       önce görmesi gerekiyor.
     · "Tümü" / "Temizle"
     · 8'den fazla firmada arama kutusu (altında kalabalık değil,
       üstünde göz gezdirmek yetmiyor)
     · uzun firma adı satırı taşırmıyor, "…" ile kesiliyor
     · belge kodu sağ uçta rozet, kapalı firma işaretli

   "Tümü" YALNIZCA GÖRÜNEN satırları işaretliyor: arama açıkken
   gizli firmaları da işaretlemek, görmediğin bir yetkiyi vermek
   olurdu. Buna karşılık KAYDEDERKEN görünürlüğe değil `checked`e
   bakılıyor — arama süzgeci görseldir, gizlenmiş ama işaretli bir
   firma hâlâ verilmiş bir yetkidir.

── NASIL DOĞRULANDI ──
   Tahmin etmedim: bileşen GERÇEK CSS'i ve GERÇEK çizim işleviyle
   Chromium'da basıldı, ekran görüntüsü alındı. Harness, bileşeni
   gerçek kapsayıcısının (`<div class="form-alan">`) içine koyuyor —
   yani çakışma aynen yeniden üretiliyor; düzeltmenin işe yaradığı
   sayfada görülerek anlaşıldı, kodun "doğru görünmesiyle" değil.

   Ölçülenler (2 / 3 / 12 firma):
     onay kutusu genişliği   15px   (eskiden satır boyu yayılıyordu)
     satır yüksekliği        33px
     gövde yüksekliği   65 / 98 / 208px — 12 firmada kaydırmaya geçti
     arama kutusu       yalnızca 12 firmada çıktı
     sayaç              "2 / 12 firma seçili" · boşta kırmızı uyarı
     arama "mer"        12 firmadan 4'ünü bıraktı

   94 test geçti; js · form · zincir · akis · sema · firma temiz.

DOSYALAR
--------
  templates/ayarlar.html    CSS + çizim işlevi + yardımcılar

Şema yok, göç yok, sunucu tarafı değişmiyor.

KULLANIM
--------
  python3 yama_kf5.py            # RAPOR
  python3 yama_kf5.py --uygula
  sudo systemctl restart milestone-erp

  Sonra tarayıcıda Ctrl+F5 — eski CSS önbellekte kalırsa liste yine
  bozuk görünür.
"""

import os
import py_compile
import shutil
import subprocess
import sys
import tempfile

UYGULA = '--uygula' in sys.argv
KOK = os.path.dirname(os.path.abspath(__file__))

DOSYA_IMZA = {'templates/ayarlar.html': 'FİRMA SEÇİM LİSTESİ (KF5)'}
ONKOSUL = {'templates/ayarlar.html': 'FİRMA KAPSAMI (KF3)'}

DEGISIKLIKLER = [
    ('templates/ayarlar.html', 'KF5 blok 1',
     r'''  .form-alan input:focus,.form-alan select:focus{outline:none;border-color:var(--verde);box-shadow:0 0 0 3px var(--verde-acik)}
''',
     r'''  .form-alan input:focus,.form-alan select:focus{outline:none;border-color:var(--verde);box-shadow:0 0 0 3px var(--verde-acik)}
  /* ── FİRMA SEÇİM LİSTESİ (KF5) ──
     KENDİ SINIFLARIYLA ÇİZİLİR — sebebi acı:

       .form-alan input { width:100%; border:1px solid; padding:9px 11px }
       .form-alan label { display:block; text-transform:uppercase;
                          font-size:.72rem; color:var(--soluk) }

     Bu iki kural onay kutusuna da uyguluyordu. Kutu tam genişliğe
     yayılıp çerçeve ve dolgu alıyor, firma adı satırın sağ ucuna
     itiliyor, etiket küçücük gri BÜYÜK HARFE dönüyordu. MF7'de
     `.kutu` ile birebir aynı çakışmayı yaşamış ve "bundan sonra
     sınıf adının kullanılıp kullanılmadığına bakacağım" demiştim;
     yine düştüm. Bu sefer kurtulmanın yolu ad seçmek değil,
     ANCESTOR KURALLARINI AÇIKÇA GERİ ALMAK: aşağıdaki
     `.kf-fir input` ve `.kf-fir label` sıfırlamaları o yüzden var.

     Ölçeklenmesi de gerekiyordu: firma sayısı arttıkça pencere
     uzayıp kaydet düğmesini aşağı itiyordu. Gövde kaydırmalı,
     8'den fazla firmada arama kutusu çıkıyor. */
  .kf-fir{border:1px solid var(--cizgi-koyu);border-radius:var(--r-kucuk);
          background:var(--yuzey);overflow:hidden}
  .kf-fir-ust{display:flex;align-items:center;gap:8px;padding:7px 10px;
              border-bottom:1px solid var(--cizgi);background:var(--taban)}
  .kf-fir-sayi{font-size:.74rem;font-weight:600;color:var(--soluk);
               letter-spacing:.02em}
  .kf-fir-ust .kf-mini{margin-left:auto;display:flex;gap:4px}
  .kf-mini button{border:1px solid var(--cizgi-koyu);background:var(--yuzey);
                  border-radius:5px;padding:3px 8px;font-size:.72rem;
                  font-weight:600;color:var(--soluk);cursor:pointer;
                  font-family:var(--govde)}
  .kf-mini button:hover{color:var(--verde);border-color:var(--verde)}
  .kf-fir-ara{padding:7px 10px;border-bottom:1px solid var(--cizgi)}
  /* Arama kutusu .form-alan input kuralından payını alabilir; burada
     açıkça yeniden tanımlıyoruz ki yükseklik satırlara uysun. */
  .kf-fir .kf-fir-ara input{width:100%;border:1px solid var(--cizgi-koyu);
                    border-radius:5px;padding:5px 8px;font-size:.82rem;
                    font-family:var(--govde);background:var(--yuzey)}
  .kf-fir-govde{max-height:208px;overflow-y:auto}
  /* ── ANCESTOR SIFIRLAMASI ──
     ÖZGÜLLÜK VE SIRA, İKİSİ BİRDEN. İlk denemede yalnızca
     `.kf-fir label` yazmıştım: `.form-alan label` ile AYNI
     özgüllükte (0,0,1,1) ve benim bloğum stil sayfasında ÖNCE
     geliyordu — eşitlikte sonraki kazanır, yani sıfırlamam
     kaybetti. Ekranda görüldü: kutuyla ad arasında boşluk yok
     (flex uygulanmamış), yazı kalın ve BÜYÜK HARF.

     Artık etiketin kendi sınıfı var (`label.kf-satir` → 0,0,2,1)
     ve kurallar `.form-alan` tanımlarından SONRA geliyor. Biri
     bozulsa öteki tutar. */
  .kf-fir label.kf-satir{display:flex;align-items:center;gap:9px;
                margin:0;padding:7px 10px;font-size:.86rem;
                font-weight:400;letter-spacing:normal;
                text-transform:none;color:var(--murekkep);
                cursor:pointer;border-bottom:1px solid var(--cizgi)}
  .kf-fir label.kf-satir:last-child{border-bottom:0}
  .kf-fir label.kf-satir:hover{background:var(--verde-acik)}
  .kf-fir label.kf-satir input[type=checkbox]{width:15px;height:15px;
                               flex:0 0 15px;margin:0;padding:0;
                               border:0;border-radius:3px;
                               accent-color:var(--verde);cursor:pointer}
  .kf-fir .kf-ad{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;
                 white-space:nowrap}
  .kf-fir .kf-kod{font-family:var(--mono,monospace);font-size:.72rem;
                  color:var(--soluk);background:var(--taban);
                  border:1px solid var(--cizgi);border-radius:4px;
                  padding:1px 5px;flex:0 0 auto}
  .kf-fir .kf-kapali{font-size:.72rem;color:var(--soluk);flex:0 0 auto}
  .kf-fir-bos{padding:14px 10px;font-size:.8rem;color:var(--soluk);
              text-align:center}
'''),
    ('templates/ayarlar.html', 'KF5 blok 2',
     r'''let SECILI_FIRMALAR = [];

''',
     r'''let SECILI_FIRMALAR = [];

/* Arama kutusu 8 firmadan sonra çıkıyor: altında kalabalık değil,
   üstünde listede göz gezdirmek yetmiyor. */
const KF_ARAMA_ESIGI = 8;

'''),
    ('templates/ayarlar.html', 'KF5 blok 3',
     r'''  if (!FIRMALAR_KF.length) {
    kap.innerHTML = '<div style="font-size:.76rem;color:var(--soluk)">' +
      'Henüz firma yok.</div>';
''',
     r'''  if (!FIRMALAR_KF.length) {
    kap.innerHTML = '<div class="kf-fir"><div class="kf-fir-bos">' +
      'Henüz firma yok — Ayarlar → Firmalar bölümünden açabilirsin.' +
      '</div></div>';
'''),
    ('templates/ayarlar.html', 'KF5 blok 4',
     r'''  }
  kap.innerHTML = FIRMALAR_KF.map(f => `
    <label style="display:flex;align-items:center;gap:8px;padding:4px 0;
                  font-size:.84rem;cursor:pointer">
      <input type="checkbox" value="${f.id}"
             ${SECILI_FIRMALAR.includes(f.id) ? 'checked' : ''}>
      <span><b>${kacar(f.ad)}</b>${f.belge_kodu
        ? ` <span class="rozet rz-gri">${kacar(f.belge_kodu)}</span>` : ''}
        ${f.aktif === false ? ' <span style="color:var(--soluk)">(kapalı)</span>' : ''}
      </span>
    </label>`).join('');
''',
     r'''  }
  const ara = FIRMALAR_KF.length > KF_ARAMA_ESIGI;
  kap.innerHTML = `
    <div class="kf-fir">
      <div class="kf-fir-ust">
        <span class="kf-fir-sayi" id="uFirmaSayi"></span>
        <span class="kf-mini">
          <button type="button" onclick="uFirmaTopluSec(true)">Tümü</button>
          <button type="button" onclick="uFirmaTopluSec(false)">Temizle</button>
        </span>
      </div>
      ${ara ? `<div class="kf-fir-ara">
        <input type="text" id="uFirmaAra" placeholder="Firma ara…"
               oninput="uFirmaSuz()" autocomplete="off">
      </div>` : ''}
      <div class="kf-fir-govde" id="uFirmaGovde">
        ${FIRMALAR_KF.map(f => `
        <label class="kf-satir" data-ad="${kacar((f.ad || '').toLocaleLowerCase('tr'))}">
          <input type="checkbox" value="${f.id}"
                 onchange="uFirmaSayiTazele()"
                 ${SECILI_FIRMALAR.includes(f.id) ? 'checked' : ''}>
          <span class="kf-ad">${kacar(f.ad)}</span>
          ${f.belge_kodu ? `<span class="kf-kod">${kacar(f.belge_kodu)}</span>` : ''}
          ${f.aktif === false ? '<span class="kf-kapali">kapalı</span>' : ''}
        </label>`).join('')}
      </div>
    </div>`;
  uFirmaSayiTazele();
}

function uFirmaKutular() {
  return Array.from(document.querySelectorAll(
    '#uFirmaKutular input[type=checkbox]'));
}

function uFirmaSayiTazele() {
  const k = uFirmaKutular();
  const n = k.filter(x => x.checked).length;
  const e = document.getElementById('uFirmaSayi');
  if (!e) return;
  /* Hiçbiri işaretli değilken bunu SÖYLEMEK gerekiyor: o kullanıcı
     sisteme giremez ve sebebi sayıdan okunmalı. */
  e.textContent = n ? `${n} / ${k.length} firma seçili`
                    : 'Hiçbiri seçili değil — giriş yapamaz';
  e.style.color = n ? 'var(--soluk)' : 'var(--kirmizi, #B4332B)';
}

function uFirmaTopluSec(deger) {
  /* Yalnızca GÖRÜNEN satırlar: arama süzgeci açıkken "Tümü"nün
     gizli firmaları da işaretlemesi, görmediğin bir yetkiyi vermek
     olurdu. */
  uFirmaKutular().forEach(x => {
    if (x.closest('label').style.display !== 'none') x.checked = deger;
  });
  uFirmaSayiTazele();
}

function uFirmaSuz() {
  const q = (document.getElementById('uFirmaAra') || {}).value || '';
  const t = q.trim().toLocaleLowerCase('tr');
  document.querySelectorAll('#uFirmaGovde label').forEach(l => {
    l.style.display = (!t || (l.dataset.ad || '').includes(t)) ? '' : 'none';
  });
'''),
    ('templates/ayarlar.html', 'KF5 blok 5',
     r'''    (document.getElementById('uFirmaKapsam') || {}).value || 'secili';
  govde.firmalar = Array.from(
    document.querySelectorAll('#uFirmaKutular input[type=checkbox]'))
''',
     r'''    (document.getElementById('uFirmaKapsam') || {}).value || 'secili';
  /* Arama süzgeci GÖRSEL: gizlenmiş ama işaretli bir firma hâlâ
     verilmiş bir yetkidir, kaydederken korunmalı. O yüzden
     görünürlüğe değil `checked`e bakıyoruz. */
  govde.firmalar = uFirmaKutular()
'''),
]


def main():
    print('=' * 70)
    print('  YAMA KF5 — FIRMA SECIM LISTESI GORUNUMU')
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
        print('  ⊙ Yama KF5 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_kf5.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_kf5'
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
    print('    sudo systemctl restart milestone-erp')
    print()
    print('  Tarayicida Ctrl+F5 — eski CSS onbellekte kalirsa liste')
    print('  yine bozuk gorunur.')
    print()
    print('  Ayarlar -> Kullanicilar -> bir kullaniciyi duzenle:')
    print('  firma listesi artik kaydirmali, sayacli ve 8 firmadan')
    print('  sonra aramali.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

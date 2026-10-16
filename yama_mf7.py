#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MF7 — FİRMA SEÇ EKRANI DÜZELİR + KONSOLİDE EKSTRE
=======================================================

ÖNKOŞUL: MF6 uygulanmış olmalı.

ÜÇ İŞ
-----

1) HATA · Firma seç ekranının düzeni bozuldu (BENİM HATAM, MF6).
   MF6'da onay kutuları için `.kutu` sınıfını kullandım. Ama `.kutu`
   o sayfanın ANA KAPSAYICISI:

       .kutu{width:100%;max-width:560px}      (satır 25)
       <main class="kutu">                    (satır 121)

   Sonradan yazdığım `.kutu{display:flex; …}` kuralı sonra geldiği
   için kazandı ve `<main>` yatay bir satıra dönüştü: başlık, açıklama
   ve kartlar yan yana sıkıştı.

   Kutulara kendi adı verildi (`.onay-kutu`).

   DERS: bir şablona yeni bir sınıf eklerken o adın zaten kullanılıp
   kullanılmadığına bakmak lazım. J5 (aynı adla iki fonksiyon) ve J7
   (aynı id iki kez) eksenlerinin aynı ailesinden — ama CSS'te, ve
   sessiz: hiçbir şey hata vermiyor, sadece sayfa dağılıyor.

2) HATA · Ekstre başlığında firma adı SABİT yazılmış.
   `render_template(... firma_adi='Milestone Mermer' ...)` — ikinci
   firmanın ekstresinde de "Milestone Mermer" basılıyordu. Artık
   aktif firmanın ünvanından geliyor (MF5'teki tek kaynak).

3) KONSOLİDE EKSTRE
   Bir cari birden çok firmada işlem görüyorsa, ekstresi seçilen
   firmaların hareketlerini BİRLEŞTİREREK çıkar.

   · Ekstre penceresinde "Konsolide ekstre" kutusu — yalnızca o cari
     birden çok firmaya bağlıysa görünür.
   · İşaretlenince hangi firmaların dahil edileceği seçilir.
   · Belgede FİRMA sütunu çıkar; hangi satırın hangi firmadan geldiği
     görünür. Sütun olmadan konsolide ekstre okunamaz — aynı müşteri
     iki ayrı defterde, satırlar birbirine karışırdı.
   · Başlıkta "Konsolide" ve dahil edilen firmalar yazar.
   · Bakiye ve toplamlar seçilen firmaların TAMAMI üzerinden.

   YALNIZCA ADMIN: konsolide ekstre, kullanıcının o an içinde
   olmadığı firmaların rakamlarını gösterir.

DOSYALAR
--------
  templates/firma_sec.html    (sınıf adı düzeltmesi)
  flask_app.py                (konsolide ekstre + firma adı)
  templates/ekstre_print.html (firma sütunu ve başlık)
  templates/cari.html         (ekstre penceresinde seçim)

ŞEMA DEĞİŞMİYOR — göç gerekmiyor.

KULLANIM
--------
  python3 yama_mf7.py            # RAPOR
  python3 yama_mf7.py --uygula
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
    'templates/firma_sec.html': 'onay-kutu',
    'flask_app.py': '_konsolide_firmalar',
    'templates/ekstre_print.html': 'konsolide',
    'templates/cari.html': 'eksKonsolide',
}
ONKOSUL = {
    'templates/firma_sec.html': 'nOrtakCari',       # MF6
    'flask_app.py': 'def _firma_kayit():',          # MF5
    'templates/ekstre_print.html': None,
    'templates/cari.html': 'cFirmalar',             # MF6
}


# ══════════════════════════════════════════════════════════════════
#  flask_app.py — konsolide ekstre
# ══════════════════════════════════════════════════════════════════

KONSOLIDE = '''    def _konsolide_firmalar():
        """Ekstre hangi firmaların hareketlerini içersin.

        `?firmalar=1,3` verilmişse o firmalar; verilmemişse None
        (aktif firma — süzgeç zaten halleder).

        YALNIZCA ADMIN: konsolide ekstre, kullanıcının o an içinde
        OLMADIĞI firmaların rakamlarını gösterir.
        """
        _ham = (request.args.get('firmalar') or '').strip()
        if not _ham:
            return None
        if (session.get('rol') or '').upper() != 'ADMIN':
            return None
        try:
            _istenen = {int(x) for x in _ham.split(',') if x.strip().isdigit()}
        except Exception:
            return None
        if not _istenen:
            return None
        with firma_atla():
            _gecerli = {f.id for f in Firma.query.filter_by(aktif=True).all()}
        _sonuc = sorted(_istenen & _gecerli)
        # Tek firma seçildiyse konsolide değil, sıradan ekstre.
        return _sonuc if len(_sonuc) > 1 else None

    def _firma_adlari(idler):
        """{firma_id: ad} — ekstrede FİRMA sütunu bunu basar."""
        if not idler:
            return {}
        with firma_atla():
            return {f.id: (f.ad or str(f.id))
                    for f in Firma.query.filter(Firma.id.in_(idler)).all()}

'''


def degisiklikler():
    return [
        # ── 1 · firma_sec.html sınıf çakışması ──
        ('templates/firma_sec.html', 'MF7-a · onay kutusu kendi sinifina alinir',
         """.kutu{display:flex;gap:9px;align-items:flex-start;padding:8px 0;cursor:pointer;
  font-size:.84rem;font-weight:400;color:var(--murekkep);text-transform:none;
  letter-spacing:0}
.kutu input{margin-top:2px;width:15px;height:15px;cursor:pointer;flex:0 0 auto}
.kutu span{line-height:1.45}""",
         """/* MF7: bu kurallar ÖNCE `.kutu` adıyla yazılmıştı — ama `.kutu`
   sayfanın ANA KAPSAYICISI (yukarıda .kutu{max-width:560px},
   <main class="kutu">). Sonra geldiği için kazandı ve <main> yatay
   satıra döndü: başlık, açıklama ve kartlar yan yana sıkıştı.
   Yeni sınıfa yeni ad. */
.onay-kutu{display:flex;gap:9px;align-items:flex-start;padding:8px 0;cursor:pointer;
  font-size:.84rem;font-weight:400;color:var(--murekkep);text-transform:none;
  letter-spacing:0}
.onay-kutu input{margin-top:2px;width:15px;height:15px;cursor:pointer;flex:0 0 auto}
.onay-kutu span{line-height:1.45}"""),
        ('templates/firma_sec.html', 'MF7-b · ortak cari kutusu',
         """        <label class="kutu"><input type="checkbox" id="nOrtakCari" checked>""",
         """        <label class="onay-kutu"><input type="checkbox" id="nOrtakCari" checked>"""),
        ('templates/firma_sec.html', 'MF7-c · ortak liste kutusu',
         """        <label class="kutu"><input type="checkbox" id="nOrtakListe" checked>""",
         """        <label class="onay-kutu"><input type="checkbox" id="nOrtakListe" checked>"""),

        # ── 2 · konsolide ekstre: yardımcılar ──
        ('flask_app.py', 'MF7-d · konsolide yardimcilari',
         "    def _firma_kayit():", KONSOLIDE + "    def _firma_kayit():"),

        # ── 3 · ekstre sorgusu ──
        ('flask_app.py', 'MF7-e · ekstre sorgusu secilen firmalari kapsar',
         """        cari = Cari.query.get(cari_id)
        if not cari: return "Cari bulunamadı", 404
        hareketler = CariHareket.query.filter_by(cari_id=cari_id).order_by(CariHareket.hareket_tarihi, CariHareket.guncelleme).all()

        # ── İŞLEM TÜRÜ SÜZGECİ (ET1) ──""",
         """        cari = Cari.query.get(cari_id)
        if not cari: return "Cari bulunamadı", 404
        # ── MF7 · KONSOLİDE EKSTRE ──
        # Aynı müşteri birden çok firmada işlem görüyorsa, seçilen
        # firmaların hareketleri BİRLEŞTİRİLİR. Süzgeç aktif firmaya
        # bakar; burada bilerek atlanıyor ve firma şartı ELLE konuyor.
        _kons = _konsolide_firmalar()
        if _kons:
            with firma_atla():
                hareketler = (CariHareket.query
                              .filter(CariHareket.cari_id == cari_id,
                                      CariHareket.firma_id.in_(_kons))
                              .order_by(CariHareket.hareket_tarihi,
                                        CariHareket.guncelleme).all())
        else:
            hareketler = CariHareket.query.filter_by(cari_id=cari_id).order_by(CariHareket.hareket_tarihi, CariHareket.guncelleme).all()

        # ── İŞLEM TÜRÜ SÜZGECİ (ET1) ──"""),

        # ── 4 · render: firma adı + konsolide bilgisi ──
        ('flask_app.py', 'MF7-f · ekstre basliginda gercek firma adi',
         """render_template('ekstre_print.html', cari=cari, hareketler=hareketler,
                               dil=_belge_dili(getattr(cari, 'ulke', None)),
                               baslik='Cari Ekstre', bugun=date.today(),
                               firma_adi='Milestone Mermer', toplam_borc=toplam_borc, toplam_alacak=toplam_alacak,
                               net_bakiye=net_bakiye, hedef_doviz=hedef_doviz, kur_modu=kur_modu)""",
         """render_template('ekstre_print.html', cari=cari, hareketler=hareketler,
                               dil=_belge_dili(getattr(cari, 'ulke', None)),
                               baslik='Cari Ekstre', bugun=date.today(),
                               # MF7: SABİT 'Milestone Mermer' yazıyordu —
                               # ikinci firmanın ekstresinde de o basılıyordu.
                               firma_adi=((_fk.unvan or _fk.ad) if (_fk := _firma_kayit()) else ''),
                               toplam_borc=toplam_borc, toplam_alacak=toplam_alacak,
                               net_bakiye=net_bakiye, hedef_doviz=hedef_doviz, kur_modu=kur_modu,
                               # MF7: konsolideyse FİRMA sütunu açılır.
                               konsolide=bool(_kons),
                               firma_adlari=_firma_adlari(_kons or []))"""),

        # ── 5 · ekstre şablonu: firma sütunu ──
        ('templates/ekstre_print.html', 'MF7-g · firma sutunu basligi',
         """      <th style="width: 75px;">{{ _ceviri('tarih', dil) }}</th>""",
         """      {# MF7: konsolide ekstrede hangi satır hangi firmadan —
         sütun olmadan iki defter birbirine karışır, belge okunmaz. #}
      {% if konsolide %}<th style="width: 80px;">Firma</th>{% endif %}
      <th style="width: 75px;">{{ _ceviri('tarih', dil) }}</th>"""),
        ('templates/ekstre_print.html', 'MF7-h · firma sutunu hucresi',
         """      <td>{{ h.hareket_tarihi.strftime('%d.%m.%Y') if h.hareket_tarihi else '—' }}</td>""",
         """      {% if konsolide %}<td style="font-size:10px;color:#444">{{ firma_adlari.get(h.firma_id, '—') }}</td>{% endif %}
      <td>{{ h.hareket_tarihi.strftime('%d.%m.%Y') if h.hareket_tarihi else '—' }}</td>"""),
        ('templates/ekstre_print.html', 'MF7-i · baslikta konsolide notu',
         """    <h1>{{ firma_adi }}</h1>""",
         """    <h1>{{ firma_adi }}</h1>
    {% if konsolide %}
    {# MF7: belgeyi okuyan, rakamların hangi defterlerden toplandığını
       görmeli. Yazmadan basmak yanıltıcı bir toplam olurdu. #}
    <div style="font-size:11px;color:#444;margin-top:2px">
      KONSOLİDE EKSTRE — {{ firma_adlari.values()|join(' · ') }}
    </div>
    {% endif %}"""),

        # ── 6 · cari.html · ekstre penceresinde seçim ──
        ('templates/cari.html', 'MF7-j · konsolide secimi isaretlemesi',
         """        <div id="eksTipler" class="sec-izgara"></div>""",
         """        <div id="eksTipler" class="sec-izgara"></div>"""),
        ('templates/cari.html', 'MF7-k · konsolide bolumu',
         """      <div id="eksAciklama" style="font-size:.79rem;color:var(--soluk);
           line-height:1.5;background:var(--notr-bg);border-radius:8px;padding:10px 12px"></div>""",
         """      <!-- MF7: KONSOLİDE EKSTRE — yalnızca cari birden çok
           firmaya bağlıysa görünür; tek firmadaysa seçecek bir şey
           yok ve pencere bugünküyle aynı kalır. -->
      <div id="eksKonsolideAlan" style="display:none">
        <label style="display:flex;align-items:center;gap:7px;cursor:pointer;
                      font-weight:600;font-size:.86rem;padding:4px 0">
          <input type="checkbox" id="eksKonsolide" onchange="eksKonsolideDegisti()"
                 style="width:15px;height:15px;cursor:pointer">
          Konsolide ekstre — birden çok firmanın hareketlerini birleştir
        </label>
        <div id="eksFirmalar" class="sec-izgara" style="display:none;margin-top:6px"></div>
      </div>
      <div id="eksAciklama" style="font-size:.79rem;color:var(--soluk);
           line-height:1.5;background:var(--notr-bg);border-radius:8px;padding:10px 12px"></div>"""),
        ('templates/cari.html', 'MF7-l · konsolide secim mantigi',
         """function ekstreKapat() {""",
         """/* ── MF7 · KONSOLİDE EKSTRE SEÇİMİ ──
   Cari birden çok firmaya bağlıysa, ekstre o firmaların
   hareketlerini birleştirebilir. Firma listesi MF6'da zaten
   çekiliyor (FIRMALAR); cari kartındaki bağlar da listede. */
function eksKonsolideHazirla(cari) {
  const alan = document.getElementById('eksKonsolideAlan');
  const kap = document.getElementById('eksFirmalar');
  if (!alan || !kap) return;
  const bagli = (cari && cari.firmalar) || [];
  /* Admin değilse ya da cari tek firmadaysa bölüm hiç görünmez —
     sunucu da admin olmayanın isteğini yok sayar. */
  if (!window.ADMIN || bagli.length < 2) {
    alan.style.display = 'none';
    document.getElementById('eksKonsolide').checked = false;
    kap.style.display = 'none';
    return;
  }
  alan.style.display = '';
  document.getElementById('eksKonsolide').checked = false;
  kap.style.display = 'none';
  const adlar = {};
  (FIRMALAR || []).forEach(f => { adlar[f.id] = f.ad; });
  kap.innerHTML = bagli.map(fid => `
    <label class="sec-ogesi">
      <input type="checkbox" class="eks-firma" value="${fid}" checked>
      <span>${kacar(adlar[fid] || ('#' + fid))}</span>
    </label>`).join('');
}

function eksKonsolideDegisti() {
  const acik = document.getElementById('eksKonsolide').checked;
  document.getElementById('eksFirmalar').style.display = acik ? '' : 'none';
}

function eksSeciliFirmalar() {
  if (!document.getElementById('eksKonsolide').checked) return [];
  return [...document.querySelectorAll('.eks-firma:checked')].map(x => x.value);
}

function ekstreKapat() {"""),
        ('templates/cari.html', 'MF7-m · pencere acilinca konsolide hazirlanir',
         """  ekstreKipGoster();
  document.getElementById('ekstreModal').classList.add('acik');""",
         """  ekstreKipGoster();
  eksKonsolideHazirla(c);                       // MF7
  document.getElementById('ekstreModal').classList.add('acik');"""),
        ('templates/cari.html', 'MF7-n · secilen firmalar adrese eklenir',
         """              + (eksSeciliTipler().length
                 ? `&tip=${encodeURIComponent(eksSeciliTipler().join(','))}` : ''),
              '_blank');""",
         """              + (eksSeciliTipler().length
                 ? `&tip=${encodeURIComponent(eksSeciliTipler().join(','))}` : '')
              /* MF7: tek firma seçiliyse sunucu konsolide SAYMAZ —
                 sıradan ekstre çıkar, firma sütunu da basılmaz. */
              + (eksSeciliFirmalar().length > 1
                 ? `&firmalar=${encodeURIComponent(eksSeciliFirmalar().join(','))}` : ''),
              '_blank');"""),
    ]


def main():
    print('=' * 70)
    print('  YAMA MF7 — FİRMA SEÇ DÜZELİR + KONSOLİDE EKSTRE')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    gruplar = {}
    for dosya, aciklama, eski, yerine in degisiklikler():
        if eski == yerine:
            continue                       # no-op kalıpları atla
        gruplar.setdefault(dosya, []).append((aciklama, eski, yerine))

    sonuclar, hata, zaten = {}, False, []
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

        onk = ONKOSUL.get(dosya)
        if onk and onk not in icerik:
            print(f'  ✗ ÖNKOŞUL YOK: "{onk}" yok — önce MF6 uygulanmalı')
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
        print('  ⊙ Yama MF7 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_mf7.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        yedek = yol + '.yedek_mf7'
        shutil.copy2(yol, yedek)
        with open(yol, 'w', encoding='utf-8', newline='') as f:
            f.write(icerik)
        print(f'  ✓ yazıldı: {os.path.relpath(yol, KOK)}')
        print(f'    yedek  : {os.path.relpath(yedek, KOK)}')

    print('\n  ✓ YAMA UYGULANDI')
    print()
    print('  Şema değişmedi — göç gerekmiyor.')
    print()
    print('    sudo systemctl restart milestone-erp')
    print('    (tarayıcıda Ctrl+F5 — eski CSS önbellekte kalmasın)')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA OR10 — HESAP DÖKÜMÜ YENİ SIRADA
=====================================

ÖNKOŞUL: yama_or9.py uygulanmış olmalı.

Senin sıralaman uygulandı. Döküm artık dört başlık altında ve
ekran ile ekstre BİREBİR aynı sırada — ikisi aynı hesabın iki
ayrı yüzü gibi okunmasın diye.

── DÖKÜMÜN YENİ HÂLİ ──

  HESAP
    Ciro                         (kaç satış kaydından geldiği yazılı)
    Maliyet                      −
    Brüt kâr
      ∟ vergi kalemi             −   (kaç kalem varsa hepsi)
    Net kâr

  KATKILAR
    Ortağın katkısı
    Bizim katkımız
    Ortağa iade edilecek tutar
    Bize iade edilecek tutar

  KÂR PAYLARI
    Ortağın kâr payı (%..)
    Bizim kâr payımız (%..)

  HESAPLAŞMA
    Ortağın alacağı toplam       = iade + kâr payı
      ∟ Ortağa ödenen toplam
    Ortağa kalan bakiye
    Bizim alacağımız toplam
      ∟ Bize ödenen toplam
    Bize kalan bakiye

── SENİN LİSTENDEN TEK SAPMA: BRÜT KÂR ──
  Sen saymamıştın, ben bıraktım. Sebebi şu: vergi satırının
  etiketi "%25 × brüt kâr". Üstünde brüt kâr yazmazsa o çarpımın
  neyle yapıldığı belgede görünmüyor; okuyan 4.980'in nereden
  çıktığını hesaplayamıyor. İstemezsen tek satır, söyle, kaldırırım.

── İKİ KÜÇÜK DÜZELTME ──
  · Bizim tarafımız KOŞULSUZ görünüyor artık. Önceden yalnız
    bizim katkımız veya dağıtımımız varsa çıkıyordu; ortaklığın
    başında "bizim tarafımız yok" diye okunabiliyordu. Artık
    sıfırsa bile sıfır olarak yazıyor — simetri belgenin kendisi.
  · "Bize ödenecek" → "Bizim alacağımız toplam", "Bizim bakiye
    (kalan)" → "Bize kalan bakiye". Ortak tarafındaki satırla
    aynı kalıpta; iki taraf yan yana okunuyor.

── ANAPARA "AYRI" SEÇİLİYSE ──
  O ortaklıklarda iade diye bir şey yok (katkı geri gelmiyor,
  doğrudan kâra giriyor). KATKILAR bölümünde iade satırları
  yerine bunu söyleyen tek satırlık bir not çıkıyor — boş satır
  bırakıp "acaba sıfır mı" dedirtmesin.

── ÖLÇÜLDÜ (tarayıcıda, iki yerde de) ──
  ekranda satır sırası  : Ciro · Maliyet · Brüt kâr · vergi ·
                          Net kâr | Katkılar | Kâr payları |
                          Hesaplaşma
  ekstre (ortak) sırası : AYNI
  ekstre (iç) sırası    : AYNI + bağlı işler/satış/maliyet
  hesap kimliği         : net kâr + katkılar = iki tarafın alacağı
                          (14.940 + 14.080 = 17.550 + 11.470)
  JS hatası             : yok

  159 test geçti; firma · js · form · zincir · akis · degismezlik
  temiz.

── TESTTE DEĞİŞEN ──
  OR6'da yazdığım test "bizim taraf yalnız katkımız varsa
  görünsün" kuralını sabitliyordu — bu yama onu bilerek
  değiştiriyor. Test geri alınmadı, yeni ve daha dar kurala
  çekildi: iki taraf da KOŞULSUZ görünecek, üstelik ekranla
  ekstre aynı satırları taşıyacak. İkinci şart yeni: ileride
  birinde satır değişip ötekinde değişmezse test düşer.

DOSYALAR
--------
  templates/ortaklik.html                döküm (ekran)
  templates/ortaklik_ekstre_print.html   döküm (ekstre, iki kip)
  tests/test_kritik.py                   1 test yeni kurala çekildi

Şema yok, göç yok, yeni alan yok. Yalnız görünen sıra değişti —
hesabın kendisi değişmedi, rakamlar aynı.

KULLANIM
--------
  python3 yama_or10.py            # RAPOR
  python3 yama_or10.py --uygula
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
    'templates/ortaklik.html': 'Bizim alacağımız toplam',
    'templates/ortaklik_ekstre_print.html': 'Bizim alacağımız toplam',
    'tests/test_kritik.py': 'OR10: iki taraf artık KOŞULSUZ görünüyor',
}
ONKOSUL = {
    'templates/ortaklik.html': 'function ekstreAc(kip)',
    'templates/ortaklik_ekstre_print.html': 'ORTAKLIK EKSTRESİ',
    'tests/test_kritik.py': 'def test_or9_ekstre_iki_kipte_calisiyor',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('templates/ortaklik.html', 'OR10 · templates/ortaklik.html blok 1',
     r'''  .or-sonuc .et,.or-sonuc .tt{color:var(--verde-koyu)}
''',
     r'''  /* Blok başlığı: dökümü HESAP / KATKILAR / PAYLAR / HESAPLAŞMA
     diye ayırıyor — düz bir liste hangi rakamın neye ait olduğunu
     okutmuyordu. */
  .or-baslik .et{font-size:.72rem;font-weight:700;letter-spacing:.05em;
    text-transform:uppercase;color:var(--soluk)}
  .or-baslik{border-top:1px solid var(--cizgi);padding-top:10px;margin-top:2px}
  .or-sonuc .et,.or-sonuc .tt{color:var(--verde-koyu)}
'''),
    ('templates/ortaklik.html', 'OR10 · templates/ortaklik.html blok 2',
     r'''  const hesapHTML = `
    <div class="or-hesap">
      <div class="or-satir" style="border-bottom:1px solid var(--cizgi)">
        <span class="et" style="font-size:.74rem;text-transform:uppercase;
              letter-spacing:.05em;font-weight:700">Hesap para birimi</span>
        <span class="tt">${h.para_birimi || 'USD'}</span></div>
''',
     r'''  /* ── DÖKÜM DÜZENİ (OR10) ──
     Dört blok: HESAP (ciro → net kâr), KATKILAR, PAYLAR,
     HESAPLAŞMA. Önceki düzende bizim tarafımız en alttaydı ve
     yalnız katkımız varsa çıkıyordu; iki taraf artık simetrik ve
     "kim ne alacak" tek blokta toplanıyor.

     BRÜT KÂR satırı duruyor: vergi kalemleri onun üzerinden
     hesaplanıyor (%25 × brüt kâr), o satır olmazsa vergi rakamı
     havada kalır. */
  const _iade = h.anapara_yontemi === 'once_iade';
  const bolum = (ad) => `<div class="or-satir or-baslik"><span class="et">${ad}</span>
      <span class="tt"></span></div>`;

  const hesapHTML = `
    <div class="or-hesap">
      <div class="or-satir" style="border-bottom:1px solid var(--cizgi)">
        <span class="et" style="font-size:.74rem;text-transform:uppercase;
              letter-spacing:.05em;font-weight:700">Hesap para birimi</span>
        <span class="tt">${h.para_birimi || 'USD'}</span></div>

'''),
    ('templates/ortaklik.html', 'OR10 · templates/ortaklik.html blok 3',
     r'''      <div class="or-satir alt"><span class="et">Bizim pay (%${h.bizim_pay})</span>
        <span class="tt">${para2(h.paylar.biz, dv)}</span></div>
      <div class="or-satir alt"><span class="et">Ortak pay (%${h.ortak_pay})</span>
        <span class="tt">${para2(h.paylar.ortak, dv)}</span></div>
      ${h.anapara_yontemi === 'once_iade' ? `
      <div class="or-satir alt"><span class="et">Ortağın iade edilecek katkısı</span>
        <span class="tt">${para2(h.kalan_anapara.ortak, dv)}</span></div>` : ''}
      <div class="or-satir kalin"><span class="et">Ortağa ödenecek</span>
        <span class="tt">${para2(h.odenecek.ortak, dv)}</span></div>
      <div class="or-satir alt"><span class="et">Şimdiye kadar dağıtılan</span>
        <span class="tt">${para2(h.dagitilan.ortak, dv)}</span></div>
      <div class="or-satir kalin"><span class="et">Ortak bakiye (kalan)</span>
        <span class="tt">${para2(h.bakiye.ortak, dv)}</span></div>
      ${/* OR6: BİZİM tarafımız da görünmeli. Fason bedelini biz
             ödediğimizde bu satırlar olmadan "biz ne alacağız"
             sorusunun cevabı ekranda hiç yoktu — motor hesaplıyordu
             ama kimse göremiyordu. Katkımız yoksa gürültü olmasın
             diye yalnız katkı ya da dağıtım varsa çıkıyor. */ ''}
      ${(h.sermaye.biz || h.dagitilan.biz) ? `
      <div class="or-satir" style="border-top:1px solid var(--cizgi)">
        <span class="et" style="font-size:.74rem;text-transform:uppercase;
              letter-spacing:.05em;font-weight:700">Bizim tarafımız</span>
        <span class="tt"></span></div>
      ${h.anapara_yontemi === 'once_iade' ? `
      <div class="or-satir alt"><span class="et">Bizim iade edilecek katkımız</span>
        <span class="tt">${para2(h.kalan_anapara.biz, dv)}</span></div>` : ''}
      <div class="or-satir kalin"><span class="et">Bize ödenecek</span>
        <span class="tt">${para2(h.odenecek.biz, dv)}</span></div>
      <div class="or-satir alt"><span class="et">Şimdiye kadar alınan</span>
        <span class="tt">${para2(h.dagitilan.biz, dv)}</span></div>
      <div class="or-satir kalin"><span class="et">Bizim bakiye (kalan)</span>
        <span class="tt">${para2(h.bakiye.biz, dv)}</span></div>` : ''}
''',
     r'''
      ${bolum('Katkılar')}
      <div class="or-satir alt"><span class="et">Ortağın katkısı</span>
        <span class="tt">${para2(h.sermaye.ortak, dv)}</span></div>
      <div class="or-satir alt"><span class="et">Bizim katkımız</span>
        <span class="tt">${para2(h.sermaye.biz, dv)}</span></div>
      ${_iade ? `
      <div class="or-satir alt"><span class="et">Ortağa iade edilecek tutar</span>
        <span class="tt">${para2(h.kalan_anapara.ortak, dv)}</span></div>
      <div class="or-satir alt"><span class="et">Bize iade edilecek tutar</span>
        <span class="tt">${para2(h.kalan_anapara.biz, dv)}</span></div>`
      : `<div class="or-satir alt" style="color:var(--soluk)">
          <span class="et">Anapara AYRI takip ediliyor — iade dağıtıma girmiyor</span>
          <span class="tt"></span></div>`}

      ${bolum('Kâr payları')}
      <div class="or-satir alt"><span class="et">Ortağın kâr payı (%${h.ortak_pay})</span>
        <span class="tt">${para2(h.paylar.ortak, dv)}</span></div>
      <div class="or-satir alt"><span class="et">Bizim kâr payımız (%${h.bizim_pay})</span>
        <span class="tt">${para2(h.paylar.biz, dv)}</span></div>

      ${bolum('Hesaplaşma')}
      <div class="or-satir kalin"><span class="et">Ortağın alacağı toplam</span>
        <span class="tt">${para2(h.odenecek.ortak, dv)}</span></div>
      <div class="or-satir alt"><span class="et">Ortağa ödenen toplam</span>
        <span class="tt">${para2(h.dagitilan.ortak, dv)}</span></div>
      <div class="or-satir kalin or-sonuc"><span class="et">Ortağa kalan bakiye</span>
        <span class="tt">${para2(h.bakiye.ortak, dv)}</span></div>
      <div class="or-satir kalin"><span class="et">Bizim alacağımız toplam</span>
        <span class="tt">${para2(h.odenecek.biz, dv)}</span></div>
      <div class="or-satir alt"><span class="et">Bize ödenen toplam</span>
        <span class="tt">${para2(h.dagitilan.biz, dv)}</span></div>
      <div class="or-satir kalin or-sonuc"><span class="et">Bize kalan bakiye</span>
        <span class="tt">${para2(h.bakiye.biz, dv)}</span></div>
'''),
    ('templates/ortaklik_ekstre_print.html', 'OR10 · templates/ortaklik_ekstre_print.html blok 1',
     r'''    .hesap .eksi .tt { color:var(--danger); }
''',
     r'''    .hesap .satir.baslik { border-top:1px solid var(--border); margin-top:2px;
                           padding-top:10px; }
    .hesap .satir.baslik .et { font-size:10px; font-weight:bold; letter-spacing:.5px;
                               text-transform:uppercase; color:#777; }
    .hesap .eksi .tt { color:var(--danger); }
'''),
    ('templates/ortaklik_ekstre_print.html', 'OR10 · templates/ortaklik_ekstre_print.html blok 2',
     r'''<div class="hesap">
''',
     r'''{# OR10: ekrandaki dökümle AYNI sıra. İki yerde iki ayrı sıralama,
   aynı hesabın iki ayrı yüzü gibi okunurdu. #}
<div class="hesap">
'''),
    ('templates/ortaklik_ekstre_print.html', 'OR10 · templates/ortaklik_ekstre_print.html blok 3',
     r'''  <div class="satir alt"><span class="et">Bizim pay (%{{ hesap.bizim_pay }})</span>
    <span class="tt">{{ '%.2f'|format(hesap.paylar.biz) }}</span></div>
  <div class="satir alt"><span class="et">Ortak pay (%{{ hesap.ortak_pay }})</span>
    <span class="tt">{{ '%.2f'|format(hesap.paylar.ortak) }}</span></div>
  {% if hesap.anapara_yontemi == 'once_iade' %}
  <div class="satir alt"><span class="et">Ortağın iade edilecek katkısı</span>
    <span class="tt">{{ '%.2f'|format(hesap.kalan_anapara.ortak) }}</span></div>
  {% endif %}
  <div class="satir kalin"><span class="et">Ortağa ödenecek</span>
    <span class="tt">{{ '%.2f'|format(hesap.odenecek.ortak) }}</span></div>
  <div class="satir alt"><span class="et">Şimdiye kadar dağıtılan</span>
    <span class="tt">{{ '%.2f'|format(hesap.dagitilan.ortak) }}</span></div>
  <div class="satir kalin"><span class="et">Ortak bakiye (kalan)</span>
    <span class="tt">{{ '%.2f'|format(hesap.bakiye.ortak) }}</span></div>
  {% if hesap.sermaye.biz or hesap.dagitilan.biz %}
  <div class="satir kalin"><span class="et">Bizim tarafımız</span><span class="tt"></span></div>
  {% if hesap.anapara_yontemi == 'once_iade' %}
  <div class="satir alt"><span class="et">Bizim iade edilecek katkımız</span>
    <span class="tt">{{ '%.2f'|format(hesap.kalan_anapara.biz) }}</span></div>
  {% endif %}
  <div class="satir alt"><span class="et">Bize ödenecek</span>
    <span class="tt">{{ '%.2f'|format(hesap.odenecek.biz) }}</span></div>
  <div class="satir alt"><span class="et">Bizim bakiye</span>
    <span class="tt">{{ '%.2f'|format(hesap.bakiye.biz) }}</span></div>
  {% endif %}
''',
     r'''
  <div class="satir baslik"><span class="et">Katkılar</span><span class="tt"></span></div>
  <div class="satir alt"><span class="et">Ortağın katkısı</span>
    <span class="tt">{{ '%.2f'|format(hesap.sermaye.ortak) }}</span></div>
  <div class="satir alt"><span class="et">Bizim katkımız</span>
    <span class="tt">{{ '%.2f'|format(hesap.sermaye.biz) }}</span></div>
  {% if hesap.anapara_yontemi == 'once_iade' %}
  <div class="satir alt"><span class="et">Ortağa iade edilecek tutar</span>
    <span class="tt">{{ '%.2f'|format(hesap.kalan_anapara.ortak) }}</span></div>
  <div class="satir alt"><span class="et">Bize iade edilecek tutar</span>
    <span class="tt">{{ '%.2f'|format(hesap.kalan_anapara.biz) }}</span></div>
  {% else %}
  <div class="satir alt" style="color:#777"><span class="et">Anapara ayrı takip
    ediliyor — iade dağıtıma girmiyor</span><span class="tt"></span></div>
  {% endif %}

  <div class="satir baslik"><span class="et">Kâr payları</span><span class="tt"></span></div>
  <div class="satir alt"><span class="et">Ortağın kâr payı (%{{ hesap.ortak_pay }})</span>
    <span class="tt">{{ '%.2f'|format(hesap.paylar.ortak) }}</span></div>
  <div class="satir alt"><span class="et">Bizim kâr payımız (%{{ hesap.bizim_pay }})</span>
    <span class="tt">{{ '%.2f'|format(hesap.paylar.biz) }}</span></div>

  <div class="satir baslik"><span class="et">Hesaplaşma</span><span class="tt"></span></div>
  <div class="satir kalin"><span class="et">Ortağın alacağı toplam</span>
    <span class="tt">{{ '%.2f'|format(hesap.odenecek.ortak) }}</span></div>
  <div class="satir alt"><span class="et">Ortağa ödenen toplam</span>
    <span class="tt">{{ '%.2f'|format(hesap.dagitilan.ortak) }}</span></div>
  <div class="satir kalin sonuc"><span class="et">Ortağa kalan bakiye</span>
    <span class="tt">{{ '%.2f'|format(hesap.bakiye.ortak) }}</span></div>
  <div class="satir kalin"><span class="et">Bizim alacağımız toplam</span>
    <span class="tt">{{ '%.2f'|format(hesap.odenecek.biz) }}</span></div>
  <div class="satir alt"><span class="et">Bize ödenen toplam</span>
    <span class="tt">{{ '%.2f'|format(hesap.dagitilan.biz) }}</span></div>
  <div class="satir kalin sonuc"><span class="et">Bize kalan bakiye</span>
    <span class="tt">{{ '%.2f'|format(hesap.bakiye.biz) }}</span></div>
'''),
    ('tests/test_kritik.py', 'OR10 · tests/test_kritik.py blok 1',
     r'''    for parca in ('Bize ödenecek', 'Bizim bakiye (kalan)',
                  'h.odenecek.biz', 'h.bakiye.biz'):
        assert parca in h, parca
    # Katkımız da dağıtımımız da yoksa gürültü çıkarmasın
    assert '(h.sermaye.biz || h.dagitilan.biz)' in h
''',
     r'''    # OR10: iki taraf artık KOŞULSUZ görünüyor. Önceden yalnız
    # katkımız varsa çıkıyordu; döküm "Hesaplaşma" bloğunda iki
    # tarafı simetrik gösterince o koşul gereksizleşti — ve
    # koşullu olması "bizim tarafımız yok" diye okunabiliyordu.
    for parca in ('Bizim alacağımız toplam', 'Bize kalan bakiye',
                  'h.odenecek.biz', 'h.bakiye.biz', 'h.dagitilan.biz'):
        assert parca in h, parca
    # Ekstre de AYNI satırları taşımalı: iki yerde iki ayrı sıralama,
    # aynı hesabın iki ayrı yüzü gibi okunurdu.
    e = _io.open('templates/ortaklik_ekstre_print.html', encoding='utf-8').read()
    for parca in ('Bizim alacağımız toplam', 'Bize kalan bakiye'):
        assert parca in e, ('ekstre', parca)
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA OR10 — HESAP DOKUMU YENI SIRADA')
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
        print('    python3 yama_or10.py            # rapor')
        print('    python3 yama_or10.py --uygula')
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
        print('  ⊙ Yama OR10 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_or10.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_or10'
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
    print('    Dokum dort baslik: HESAP / KATKILAR / KAR PAYLARI /')
    print('    HESAPLASMA. Ustteki Ekstre dugmesi AYNI sirayi')
    print('    tasiyor; iki yeri yan yana koyup bak.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

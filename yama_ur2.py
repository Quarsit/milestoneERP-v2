#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA UR2 — ORTAK CİNS/YÜZEY · BLOKTA YÜZEY YOK · MENŞE LİSTEDEN
================================================================

ÖNKOŞUL: yama_ur1.py uygulanmış olmalı.

Üç madde, üçü de aynı yerde: stok giriş ekranları.

── 1 · CİNS VE YÜZEY ZORUNLU EŞLEŞME OLMAKTAN ÇIKTI ──
  Dışarıdan gelen çeki listelerinde bu iki sütun ya hiç yok ya da
  tedarikçinin kendi adlandırmasıyla geliyor. Zorunlu tutmak, listeyi
  önce Excel'de düzenlemeye zorluyordu.

  İkisi de 4. adıma, ORTAK alanlara taşındı. Kural fiyatla aynı (X2):
  satırın kendi değeri varsa O kazanır, ortak değer yalnızca boşluğu
  doldurur. Sıra şöyle:

      eşleşen sütun → birleştirilmiş hücre doldurması → ortak alan

  Ortak değer en sonda, çünkü en zayıf bilgi o.

  VERİDEKİ zorunluluk KALKMADI: ortak alan da boşsa ürünün tanımı yok
  demektir. Ekran bunu önizlemede yakalıyor, sunucu da kendi kapısını
  koruyor (uç doğrudan çağrılabiliyor — test ikisini de ölçüyor).

  Ortak alanlar Ayarlar → Listeler'den besleniyor; tekil formdaki
  gibi yazarken öneri çıkıyor.

── 2 · HAM BLOKTA YÜZEY İŞLEMİ YOK ──
  Alan üç yerde birden gizleniyor: yeni stok formu, düzenleme modalı
  ve içe aktarmadaki ortak alan. Gizlerken DEĞERİ de siliniyor —
  tip BLOK'a çevrilince önceki seçim gönderilmeye devam ederdi.

── 3 · MENŞE ARTIK LİSTEDEN ──
  Bu değer ticari faturaya, packing list'e ve bundle etiketine
  BASILIYOR. Serbest metin olduğu sürece aynı ülke üç ayrı yazımla
  kaydedilebiliyordu (TURKIYE / TÜRKİYE / Turkiye) ve belgede ne
  yazdığı girildiği güne kalıyordu.

  Liste `ulke` tanımlarından geliyor (Ayarlar → Listeler → Ülkeler).
  İki şey bilerek yapıldı:

    · TURKIYE her zaman seçenek. Ülke listesi boşsa — yeni kurulum —
      alan bomboş kalır ve menşe hiç seçilemezdi.
    · Listede OLMAYAN mevcut değer korunuyor. Eski bir kaydı
      düzenlerken menşesi listede yoksa seçenek olarak ekleniyor;
      yoksa Kaydet'e basmak, dokunmadığın bir alanı sessizce
      değiştirirdi.

  Hem yeni stok formunda hem düzenleme modalında. İkincisini de
  yaptım: yalnız birini liste yapmak, aynı hatalı veriyi öbür
  kapıdan içeri almak olurdu.

── ÖLÇÜLDÜ ──
  içe aktarma · PLAKA  → Cins (ortak) ve Yüzey (ortak) alanları VAR
  içe aktarma · BLOK   → ortak yüzey alanı gizli
  yeni stok   · BLOK   → yüzey alanı gizli, menşe açılır kutu
  yeni stok   · PLAKA  → yüzey alanı var, menşe açılır kutu
  menşe seçenekleri    → TURKIYE, ITALYA, ISPANYA, YUNANISTAN,
                         MISIR, IRAN  (ülke listesinden)
  cinssiz kayıt        → sunucu 400 'cins_zorunlu' (ekran değişti,
                         veri kuralı değişmedi)
  mense='  italya  '   → 'ITALYA' olarak normalleniyor

  120 test geçti (115 + 5 yeni kalıcı test);
  firma · js · form · zincir · akis · degismezlik temiz.
  Üç ekran Chromium'da basıldı.

── NE YAPMADIM ──
  İçe aktarmaya MENŞE alanı eklemedim. Bugün aktarılan her satır
  TURKIYE sayılıyor ve bu, ithal mal aktarırken belgeye yanlış menşe
  basar. Senin listendeki CEPPO DI GRE buna örnek. Ayrı bir madde
  olarak duruyor — istersen ortak alanlara onu da koyarım.

DOSYALAR
--------
  templates/stok.html    ortak cins/yüzey · blokta yüzey gizli ·
                         menşe açılır kutu (iki formda da)
  tests/test_kritik.py   5 yeni test

Şema yok, göç yok. Veri dokunulmuyor.

KULLANIM
--------
  python3 yama_ur2.py            # RAPOR
  python3 yama_ur2.py --uygula
  sudo systemctl restart milestone-erp
  (tarayıcıda Ctrl+F5)
"""

import os
import py_compile
import shutil
import subprocess
import sys
import tempfile

UYGULA = '--uygula' in sys.argv
KOK = os.path.dirname(os.path.abspath(__file__))

DOSYA_IMZA = {
    'templates/stok.html': 'UR2 · ORTAK CİNS VE YÜZEY',
    'tests/test_kritik.py': 'def test_ur2_mense_listeden_seciliyor',
}
ONKOSUL = {
    'templates/stok.html': 'UR1 · KAYNAK ──',
    'tests/test_kritik.py': 'def test_ur1_uretim_tedarikci_borcu_dogurmaz',
}

DEGISIKLIKLER = [
    ('templates/stok.html', 'UR2 · templates/stok.html blok 1',
     r'''        <div class="form-alan"><label>Yüzey / Özellik</label><input id="duzOzellik"></div>
        <div class="form-alan"><label>Menşe</label><input id="duzMense"></div>
''',
     r'''        <div class="form-alan" id="duzOzellikAlan"><label>Yüzey / Özellik</label><input id="duzOzellik"></div>
        <div class="form-alan"><label>Menşe</label><select id="duzMense"></select></div>
'''),
    ('templates/stok.html', 'UR2 · templates/stok.html blok 2',
     r'''        </div>

''',
     r'''        </div>

        <!-- ── UR2 · ORTAK CİNS VE YÜZEY ──
             Dışarıdan gelen listelerde bu iki sütun ya yok ya da
             tedarikçinin kendi adlandırmasıyla geliyor. Eşleştirme
             adımında zorunluydu; artık burada tek seferde
             verilebiliyor. Excel'de sütun VARSA o satırın değeri
             kazanır — ortak değer yalnızca boşluğu doldurur. -->
        <div class="form-satir f2" style="margin-bottom:4px">
          <div class="form-alan"><label>Cins (ortak)
            <span style="font-weight:400;color:var(--soluk)">· Excel'de yoksa</span></label>
            <input id="tCins" placeholder="CEPPO DI GRE" oninput="topluOnizle()"></div>
          <div class="form-alan" id="tOzellikAlan"><label>Yüzey / Özellik (ortak)
            <span style="font-weight:400;color:var(--soluk)">· Excel'de yoksa</span></label>
            <input id="tOzellik" placeholder="HONLU / CİLALI" oninput="topluOnizle()"></div>
        </div>

'''),
    ('templates/stok.html', 'UR2 · templates/stok.html blok 3',
     r'''        <div class="form-alan"><label>Yüzey / Özellik</label><input id="sOzellik" placeholder="Ham / Cilalı"></div>
        <div class="form-alan"><label>Menşe</label><input id="sMense" value="TURKIYE" title="Malın menşei — bundle/crate etiketinde ve ticari faturada basılır"></div>
''',
     r'''        <!-- UR2: BLOK'ta yüzey/özellik gizlenir — ham blokta yüzey
             işlemi yok, alanı göstermek doldurulacak bir şey varmış
             gibi gösteriyordu. -->
        <div class="form-alan" id="ozellikAlan"><label>Yüzey / Özellik</label><input id="sOzellik" placeholder="Ham / Cilalı"></div>
        <!-- UR2: menşe artık LİSTEDEN. Elle yazılınca aynı ülke üç
             ayrı yazımla kaydediliyordu (TURKIYE / TÜRKİYE / Turkiye)
             ve bu değer ticari faturaya, packing list'e ve etikete
             BASILIYOR. Liste Ayarlar → Listeler → Ülkeler'den gelir. -->
        <div class="form-alan"><label>Menşe</label>
          <select id="sMense" title="Malın menşei — bundle/crate etiketinde ve ticari faturada basılır"></select>
          <div style="font-size:.72rem;color:var(--soluk);margin-top:3px">
            Listede yoksa Ayarlar → Listeler → Ülkeler'den ekle</div>
        </div>
'''),
    ('templates/stok.html', 'UR2 · templates/stok.html blok 4',
     r'''async function yeniAc() {
''',
     r'''/* ── UR2 · MENŞE LİSTESİ ──
   Değer ticari faturaya, packing list'e ve etikete BASILIYOR; elle
   yazılınca aynı ülke üç ayrı yazımla kaydediliyordu.

   Listede OLMAYAN bir değer de korunur: mevcut kaydı düzenlerken
   menşesi listede yoksa seçenek olarak eklenir. Yoksa kaydet'e
   basmak, dokunmadığın bir alanı sessizce değiştirirdi.

   TURKIYE her zaman var: ülke listesi boşsa (yeni kurulum) alan
   bomboş kalıp menşe seçilemez hale gelirdi. */
async function menseDoldur(id, deger) {
  const el = document.getElementById(id);
  if (!el) return;
  const simdi = String(deger || 'TURKIYE').trim().toUpperCase() || 'TURKIYE';
  let liste = [];
  try { liste = await lookupGetir('ulke'); } catch (e) { liste = []; }
  const kume = [...new Set(['TURKIYE',
    ...liste.map(x => String(x).trim().toUpperCase()).filter(Boolean), simdi])];
  el.innerHTML = kume.map(u =>
    `<option value="${kacar(u)}">${kacar(u)}</option>`).join('');
  el.value = simdi;
}

async function yeniAc() {
'''),
    ('templates/stok.html', 'UR2 · templates/stok.html blok 5',
     r'''  document.getElementById('sMense').value = 'TURKIYE';   // MS1 varsayılan
''',
     r'''  menseDoldur('sMense', 'TURKIYE');   // MS1 varsayılan · UR2 liste
'''),
    ('templates/stok.html', 'UR2 · templates/stok.html blok 6',
     r'''  document.getElementById('kasaAdediAlan').style.display = ebatli ? '' : 'none';
''',
     r'''  /* UR2: ham blokta yüzey işlemi YOK. Alanı göstermek
     doldurulacak bir şey varmış gibi gösteriyordu; gizlenirken
     değeri de siliniyor, yoksa tipi BLOK'a çevirince önceki
     seçim gönderilmeye devam ederdi. */
  const oz = document.getElementById('ozellikAlan');
  if (oz) {
    oz.style.display = blok ? 'none' : '';
    if (blok) document.getElementById('sOzellik').value = '';
  }
  document.getElementById('kasaAdediAlan').style.display = ebatli ? '' : 'none';
'''),
    ('templates/stok.html', 'UR2 · templates/stok.html blok 7',
     r'''const TP_ALANLAR = {
  PLAKA: [
    ['cins',      'Cins',            true],
''',
     r'''/* UR2: `cins` ve `ozellik` artık ZORUNLU EŞLEŞME DEĞİL.
   Dışarıdan gelen çeki listelerinde bu iki sütun ya hiç yok ya da
   tedarikçinin kendi adlandırmasıyla geliyor ("CEPPO DI GRE" yerine
   "Ceppo Grey Vein" gibi). Zorunlu tutmak, listeyi önce Excel'de
   düzenlemeye zorluyordu. İkisi de 4. adımdaki ORTAK alandan
   verilebiliyor; satırın kendi değeri varsa o kazanır (fiyatta
   X2 ile aynı kural). */
const TP_ALANLAR = {
  PLAKA: [
    ['cins',      'Cins',            false],
'''),
    ('templates/stok.html', 'UR2 · templates/stok.html blok 8',
     r'''    ['cins',      'Cins',           true],
''',
     r'''    ['cins',      'Cins',           false],
'''),
    ('templates/stok.html', 'UR2 · templates/stok.html blok 9',
     r'''    ['cins',          'Cins',            true],
''',
     r'''    ['cins',          'Cins',            false],
'''),
    ('templates/stok.html', 'UR2 · templates/stok.html blok 10',
     r'''  topluTipDegisti();
''',
     r'''  /* UR2: ortak cins/yüzey her açılışta temizlenir — önceki
     aktarımın cinsi yeni listeye sessizce sızmasın. Alanlar
     Ayarlar → Listeler'den besleniyor (tekil formdaki gibi). */
  ['tCins', 'tOzellik'].forEach(i => {
    const el = document.getElementById(i); if (el) el.value = '';
  });
  listeyeBagla('tCins', 'cins');
  listeyeBagla('tOzellik', 'ozellik');
  document.getElementById('tKaynak').value = 'satinalma';
  topluKaynakDegisti();
  topluTipDegisti();
'''),
    ('templates/stok.html', 'UR2 · templates/stok.html blok 11',
     r'''  /* Başlangıç plaka no yalnızca PLAKA için anlamlı */
''',
     r'''  /* UR2: ham blokta yüzey işlemi yok — ortak alan da gizlenir. */
  const _oz = document.getElementById('tOzellikAlan');
  if (_oz) {
    _oz.style.display = (_t === 'BLOK') ? 'none' : '';
    if (_t === 'BLOK') document.getElementById('tOzellik').value = '';
  }
  /* Başlangıç plaka no yalnızca PLAKA için anlamlı */
'''),
    ('templates/stok.html', 'UR2 · templates/stok.html blok 12',
     r'''function _ortakFiyat() {
''',
     r'''function _ortakMetin(id) {
  const el = document.getElementById(id);
  return el ? (el.value || '').trim() : '';
}

function _ortakFiyat() {
'''),
    ('templates/stok.html', 'UR2 · templates/stok.html blok 13',
     r'''    if (!kayit.cins) { hatalar.push(`Satır ${kayit._satir}: cins boş`); return; }
''',
     r'''    /* UR2: satırın kendi değeri yoksa ORTAK alandan doldur.
       Sıra önemli: eşleşen sütun → birleştirilmiş hücre doldurması
       → ortak alan. Ortak değer en sonda, çünkü en zayıf bilgi o. */
    if (!kayit.cins) kayit.cins = _ortakMetin('tCins');
    if (!kayit.ozellik) kayit.ozellik = _ortakMetin('tOzellik');

    if (!kayit.cins) {
      hatalar.push(`Satır ${kayit._satir}: cins yok — Excel'de sütun `
                 + `eşleşmedi ve ortak cins girilmedi`);
      return;
    }
'''),
    ('templates/stok.html', 'UR2 · templates/stok.html blok 14',
     r'''  document.getElementById('duzMense').value = s.mense || 'TURKIYE';
''',
     r'''  menseDoldur('duzMense', s.mense);   // UR2: liste + mevcut değer
'''),
    ('templates/stok.html', 'UR2 · templates/stok.html blok 15',
     r'''  listeyeBagla('duzCins', 'cins');
''',
     r'''  const dOz = document.getElementById('duzOzellikAlan');
  if (dOz) dOz.style.display = (s.tip === 'BLOK') ? 'none' : '';
  listeyeBagla('duzCins', 'cins');
'''),
    ('tests/test_kritik.py', 'UR2 · tests/test_kritik.py blok 1',
     r'''    assert "kaynak: document.getElementById('sKaynak').value" in h
''',
     r'''    assert "kaynak: document.getElementById('sKaynak').value" in h


# ══════════════════════════════════════════════════════════════════════
#  UR2 · ORTAK CİNS/YÜZEY · BLOKTA YÜZEY YOK · MENŞE LİSTEDEN
# ══════════════════════════════════════════════════════════════════════

def test_ur2_ice_aktarmada_cins_zorunlu_eslesme_degil():
    """UR2: dışarıdan gelen çeki listesinde cins sütunu olmayabilir.

    Zorunlu eşleşme, kullanıcıyı listeyi önce Excel'de düzenlemeye
    zorluyordu. Artık 4. adımdaki ortak alandan verilebiliyor."""
    import io as _io, re as _re
    h = _io.open('templates/stok.html', encoding='utf-8').read()
    # Üç ürün tipinde de cins ZORUNLU olmamalı
    for kalip in (r"\['cins',\s+'Cins',\s+true\]",
                  r"\['cins',\s+'Cins',\s+true\]"):
        assert not _re.search(kalip, h), 'cins hâlâ zorunlu eşleşme'
    assert 'id="tCins"' in h
    assert 'id="tOzellik"' in h
    assert "kayit.cins = _ortakMetin('tCins')" in h
    assert "kayit.ozellik = _ortakMetin('tOzellik')" in h


def test_ur2_sunucu_cinssiz_kaydi_hala_reddediyor():
    """UR2: ekrandaki zorunluluk kalktı, VERİDEKİ kalkmadı.

    Ortak alan da boş bırakılırsa ürünün tanımı yok demektir. Ekran
    bunu önizlemede yakalıyor; sunucu da kendi kapısını koruyor —
    uç doğrudan da çağrılabiliyor."""
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/stok/ekle', headers=H, json={
        'tip': 'PLAKA', 'cins': '', 'blok_no': 'UR2-CINSSIZ',
        'boy': 300, 'yukseklik': 180, 'kalinlik': 2, 'adet': 1,
        'fiyat': 10, 'fiyat_birim': 'm2', 'doviz': 'USD'})
    assert r.status_code == 400, r.status_code
    assert r.get_json().get('error') == 'cins_zorunlu'


def test_ur2_blokta_yuzey_alani_gosterilmez():
    """UR2: ham blokta yüzey işlemi yok.

    Alanı göstermek, doldurulacak bir şey varmış gibi gösteriyordu.
    Gizlerken DEĞERİ de siliniyor: tip BLOK'a çevrilince önceki
    seçim gönderilmeye devam ederdi."""
    import io as _io
    h = _io.open('templates/stok.html', encoding='utf-8').read()
    assert 'id="ozellikAlan"' in h            # tekil form
    assert 'id="duzOzellikAlan"' in h         # düzenleme modalı
    assert 'id="tOzellikAlan"' in h           # içe aktarma ortak alanı
    assert "oz.style.display = blok ? 'none' : ''" in h
    assert "document.getElementById('sOzellik').value = ''" in h


def test_ur2_mense_listeden_seciliyor():
    """UR2: menşe ticari faturaya, packing list'e ve etikete basılıyor.

    Elle yazılınca aynı ülke üç ayrı yazımla kaydediliyordu. Liste
    `ulke` tanımlarından geliyor; listede olmayan MEVCUT değer de
    korunuyor, yoksa kaydet'e basmak dokunulmayan bir alanı sessizce
    değiştirirdi."""
    import io as _io
    h = _io.open('templates/stok.html', encoding='utf-8').read()
    assert '<select id="sMense"' in h, 'menşe hâlâ serbest metin'
    assert '<select id="duzMense"' in h, 'düzenlemede menşe serbest metin'
    assert 'function menseDoldur' in h
    assert "lookupGetir('ulke')" in h
    # TURKIYE her zaman seçenek: ülke listesi boşsa alan bomboş
    # kalıp menşe seçilemez hale gelirdi.
    assert "['TURKIYE'," in h
    # Mevcut değer listede yoksa bile seçenek olarak ekleniyor
    assert 'simdi])]' in h


def test_ur2_mense_sunucuda_normalleniyor():
    """UR2: ekran listeden seçtiriyor ama uç yine de normalliyor —
    API doğrudan çağrılabilir."""
    from models import PlakaStok
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/stok/ekle', headers=H, json={
        'tip': 'PLAKA', 'cins': 'UR2 MENSE', 'blok_no': 'UR2-MNS',
        'boy': 300, 'yukseklik': 180, 'kalinlik': 2, 'adet': 1,
        'fiyat': 10, 'fiyat_birim': 'm2', 'doviz': 'USD',
        'mense': '  italya  '})
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        p = PlakaStok.query.filter_by(blok_no='UR2-MNS').first()
        assert p.mense == 'ITALYA', p.mense
'''),
]



def main():
    print('=' * 70)
    print('  YAMA UR2 — ORTAK CINS/YUZEY · MENSE LISTEDEN')
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
        print('  ⊙ Yama UR2 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_ur2.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_ur2'
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
    print('    1) sudo systemctl restart milestone-erp')
    print('    2) Tarayicida Ctrl+F5')
    print()
    print('  BAKILACAK YERLER')
    print('    · Toplu Ice Aktar -> 4. adim: CINS (ORTAK) ve')
    print('      YUZEY / OZELLIK (ORTAK) alanlari.')
    print('    · 3. adimda Cins artik yildizli DEGIL.')
    print('    · Yeni Stok -> tip BLOK: Yuzey / Ozellik alani YOK.')
    print('    · Mense artik acilir kutu; listesi')
    print('      Ayarlar -> Listeler -> Ulkeler.')
    print()
    print('    3) venv/bin/python -m pytest tests/test_kritik.py -q')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

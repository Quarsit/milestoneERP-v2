#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA B3 — PLAKA KODU SADELEŞTİ · BAŞLANGIÇ NO 0'I KABUL EDİYOR
===============================================================

ÖNKOŞUL: yama_b2.py uygulanmış olmalı.

Senin sorduğun iki şey. İkisi de haklı çıktı.

── 1 · KOD NEDEN O KADAR UZUNDU ──
  Listede gördüğün `K6461-U1-01#1` aslında iki parça: ÜRETİM BLOK
  NO + `#` + PLAKA NO. Uzun olan kısım `K6461-U1-01` ve o bir
  DİLİMLEME KAZASI.

  Sunucu üretim no'yu şöyle kuruyordu:

      uretim_blok_no = blok_no + '-U' + kesim_id[-4:]

  Kesim numarası `KSM-K6461-01`. Son DÖRT karakter `1-01` — yani
  K6461'in son hanesi de dilime giriyor. Hemen üstündeki yorum
  satırı "son 3 hane" diyor; kod 4 alıyor.

  Üstelik 20 karakterlik KİMLİK BÜTÇESİNİ yiyordu. İkinci firmanın
  belge kodu devreye girince `PLK-MS-K6461-U1-01-01` 21 karakter
  oluyor ve sistem okunur kimlikten rastgele kimliğe düşüyordu.
  Kısaltınca `PLK-MS-K6461-01` — ölçüldü, aşağıda.

  Bir de üç ayrı kural dolaşıyordu: formdaki "öner" düğmesi
  `K6461-U261`, sunucu `K6461-U1-01`, yorum satırı bambaşka.
  Üçü de AYNI alanı dolduruyordu. Artık tek kural var.

  SENİN SEÇTİĞİN BİÇİM:

      K6461-00 · K6461-01 · K6461-12

  Üretim eki yok, ayraç tire, plaka no iki hane.

── 2 · BAŞLANGIÇ NO 0 ──
  Bu bilerek yapılmıştı ama SESSİZCE. Hem Kesim hem içe aktarma
  formunda alanın `min="1"` değeri vardı ve sunucuda ÜÇ ayrı yerde
  `0 → 1`'e çekiliyordu (`int(...) or 1`). Sistem bozulmadı — ama
  yazdığın değeri haber vermeden değiştirdi. Asıl kusur buydu.

  Artık 0 aynen gidiyor: 0, 1, 2, 3, 4.

── SEÇİMİNİN BİR BEDELİ VARDI, ONU DA ÇÖZDÜM ──
  `-U` eki yalnızca süs değildi: aynı blok no'lu plakaları
  birbirinden ayırıyordu. Kaldırınca, aynı blok no iki kez
  kesilirse ikinci kesim birincinin numaralarını TEKRAR ederdi.

  Çare: Kesim'deki "Başlangıç No" alanı artık BOŞ bırakılabiliyor
  ve boşsa o blok no'da kayıtlı EN BÜYÜK numaradan devam ediyor —
  toplu içe aktarmadaki kuralın aynısı. İki ekranda iki ayrı kural
  bırakmak, tam da çakışmanın doğduğu yer olurdu.

  Yazdığın değer (0 dahil) her zaman kazanır; boş bırakmak "kalınan
  yerden devam et" demek.

── KOD ARTIK TEK YERDEN ÜRETİLİYOR ──
  `blok#slab` dizesi SEKİZ ayrı yerde elle kuruluyordu: stok
  listesi, global arama, maliyet ekranı, proforma, Excel dışa
  aktarma, içe aktarmanın İKİ ayrı uyarı metni, denetim kaydı.

  Sekizinciyi ben de kaçırdım — testi yazınca ortaya çıktı. Yedi
  tanesini düzeltip birini unutmak, aynı plakanın iki ekranda iki
  ayrı kodla görünmesiyle biterdi; bu projede en kötü hata biçimi
  bu (MF4'te iki `yedekGovde`, YP3'te iki firma formu).

  Şimdi sunucuda `_plaka_kodu`, ekranlarda `plakaKodu` — iki kopya
  değil, iki tarafın birer kopyası, aynı kural.

── PACKING LIST ETKİLENMİYOR ──
  Orada blok no ve plaka no ZATEN ayrı sütunlarda. Birleşik kod
  bir ekran/arama/dışa aktarma meselesi; belge düzeni değişmedi.

── MEVCUT KAYITLAR: goc_b3.py ──
  Şu anda depondaki beş plakanın blok_no'su `K6461-U1-01`. Yama
  sonrası onlar `K6461-U1-01-01` diye görünür — daha da uzun.
  `goc_b3.py` onları kısaltıyor.

  Göç TAHMİN ETMİYOR. Bir değeri ancak üç şart birden tutarsa
  düzeltiyor: (1) kalıp sunucunun ürettiği kazanın şekline uyuyor,
  (2) o üretim no'lu kesimin kaynak_no'su köke eşit, (3) kısa hâli
  başka bir plakayla çakışmıyor. Tutmayan her kayıt ATLANIYOR ve
  raporda NEDEN atlandığı yazıyor.

  KİMLİKLER (PLK-…) bilerek DEĞİŞTİRİLMİYOR: onlara sipariş
  kalemleri, proforma satırları ve kesim detayları bağlı. Görünen
  bir kodu düzeltmek için veri zincirini kesmem.

── ÖLÇÜLDÜ (gerçek kesim, tarayıcıda) ──
  Üretim no ve başlangıç no BOŞ bırakılarak 5 plakalık kesim:

      "öner" düğmesi     K6461          (eskiden K6461-U261)
      üretim blok no     K6461          (eskiden K6461-U1-01)
      stok listesi       K6461-01 … K6461-05
      kimlikler          PLK-MS-K6461-01 … -05
                         (firma koduyla birlikte 20 karaktere SIĞDI)
      başlangıç alanı    min=0 · "boş = otomatik devam"
      JS hatası          yok

  Göç altı ayrı durumla sınandı: düzelen, kesim kaydı olmayan,
  kaynak no'su uyuşmayan, çakışacağı için atlanan, "öner"
  biçimindeki (-U261) ve zaten sade olan. Beşi doğru atlandı,
  biri düzeldi, ikinci koşu "yapılacak iş yok" dedi.

  131 test geçti (126 + 5 yeni kalıcı test);
  firma · js · form · zincir · akis · degismezlik temiz.

DOSYALAR
--------
  flask_app.py             _plaka_kodu · üretim no · başlangıç 0
  templates/base.html      plakaKodu (ortak)
  templates/stok.html      liste kodu · başlangıç alanları
  templates/kesim.html     başlangıç alanı · "öner" düğmesi
  templates/proforma.html  satır kodu
  tests/test_kritik.py     5 yeni test
  goc_b3.py                YENİ — mevcut kayıtlar için göç

Şema değişikliği YOK. Göç ayrı ve isteğe bağlı.

KULLANIM
--------
  python3 yama_b3.py            # RAPOR
  python3 yama_b3.py --uygula
  sudo systemctl restart milestone-erp
  venv/bin/python goc_b3.py            # önce RAPOR — ne değişecek
  venv/bin/python goc_b3.py --uygula
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
    'flask_app.py': 'def _plaka_kodu(',
    'templates/base.html': 'function plakaKodu(',
    'templates/stok.html': 'function _basNoOku(',
    'templates/kesim.html': 'boş = otomatik devam',
    'templates/proforma.html': 'plakaKodu(x.blok_no, x.slab_no)',
    'tests/test_kritik.py': 'def test_b3_plaka_kodu_tek_kaynaktan',
    'goc_b3.py': 'ÜRETİM BLOK NO SADELEŞTİRME',
}
ONKOSUL = {
    'flask_app.py': 'def _stok_okunur_id(',
    'templates/base.html': 'async function _listeYeniEkle',
    'templates/stok.html': "const TP_YENI = '__yeni__';",
    'templates/kesim.html': "const KX_YENI = '__yeni__';",
    'templates/proforma.html': 'slab_no',
    'tests/test_kritik.py': 'def test_b2_ortak_cins_ve_ozellik_listeden',
}
TAM_YAZILAN = ['goc_b3.py']

DEGISIKLIKLER = [
    ('flask_app.py', 'B3 · flask_app.py blok 1',
     r'''                    return f"{s.blok_no or ''}#{s.slab_no}".lstrip('#')
''',
     r'''                    return _plaka_kodu(s.blok_no, s.slab_no) or baglanti_id
'''),
    ('flask_app.py', 'B3 · flask_app.py blok 2',
     r'''            app.logger.warning(f'Cari hareket numarası üretilemedi: {e}')
''',
     r'''            app.logger.warning(f'Cari hareket numarası üretilemedi: {e}')

    def _plaka_kodu(blok_no, slab_no):
        """B3 — plakanın depoda okunan kodu: K6461-01

        Bu dize YEDİ ayrı yerde elle kuruluyordu (stok listesi, global
        arama, maliyet ekranı, proforma, Excel dışa aktarma, içe
        aktarma uyarısı, denetim kaydı) ve hepsi `blok#slab` diyordu.
        Biçim değişince altısını düzeltip birini unutmak, aynı
        plakanın iki ekranda iki ayrı kodla görünmesiyle biterdi — bu
        projede en kötü hata biçimi bu (MF4'te iki `yedekGovde`,
        YP3'te iki firma formu).

        Plaka no İKİ HANE yazılır: K6461-00, K6461-01, K6461-12.
        Numara yoksa yalnız blok no döner.
        """
        b = str(blok_no or '').strip()
        if slab_no is None or str(slab_no).strip() == '':
            return b
        try:
            s = f'{int(slab_no):02d}'
        except (TypeError, ValueError):
            s = str(slab_no).strip()
        return f'{b}-{s}' if b else s
'''),
    ('flask_app.py', 'B3 · flask_app.py blok 3',
     r'''                bas_no = int(_sayi('baslangic_no', 1)) or 1
''',
     r'''                # B3: 0 geçerli bir plaka numarasıdır; `or 1` onu
                # sessizce 1'e çeviriyordu.
                bas_no = int(_sayi('baslangic_no', 1))
                if bas_no < 0:
                    bas_no = 0
'''),
    ('flask_app.py', 'B3 · flask_app.py blok 4',
     r'''                              f'{blok_no} #{slab_no}')
            varolan = PlakaStok.query.filter(
                db.func.upper(PlakaStok.blok_no) == blok_no.upper(),
                PlakaStok.slab_no == slab_no).first()
            if varolan:
                return None, (f'bu plaka depoda zaten var: '
                              f'{blok_no} #{slab_no} ({varolan.id})')
''',
     r'''                              f'{_plaka_kodu(blok_no, slab_no)}')
            varolan = PlakaStok.query.filter(
                db.func.upper(PlakaStok.blok_no) == blok_no.upper(),
                PlakaStok.slab_no == slab_no).first()
            if varolan:
                return None, (f'bu plaka depoda zaten var: '
                              f'{_plaka_kodu(blok_no, slab_no)} ({varolan.id})')
'''),
    ('flask_app.py', 'B3 · flask_app.py blok 5',
     r'''                # Otomatik üretim no = orijinal_blok_no + '-U' (üretim) + kesim_id son 3 hane
                if kaynak_tip_db == 'BLOK' and ana_kaynak.blok_no:
                    uretim_blok_no = f"{ana_kaynak.blok_no}-U{kesim_id[-4:]}"
                else:
                    uretim_blok_no = ana_kaynak.blok_no or ana_kaynak.id

            # SLAB NUMARALANDIRMA: başlangıç no'dan başla, atlanan (eksik) no'ları atla.
            # Örn. başlangıç=1, atlanan=[3,5] → 1,2,4,6,7...
            try:
                _slab_sira = int(data.get('baslangic_slab') or 1)
                if _slab_sira < 1:
                    _slab_sira = 1
            except (ValueError, TypeError):
                _slab_sira = 1
''',
     r'''                # B3 — ÜRETİM NO ARTIK ORİJİNAL BLOK NO.
                #
                # Eskiden `blok_no + '-U' + kesim_id[-4:]` idi ve o dilim
                # token ortasından kesiyordu: KSM-K6461-01 → '1-01', yani
                # K6461'in son hanesi de içeri giriyordu ve kod
                # K6461-U1-01-01 gibi okunmaz hâle geliyordu. Üstelik
                # 20 karakterlik kimlik bütçesini yiyordu: firma belge
                # kodu devreye girince okunur kimlik üretilemiyordu.
                #
                # Kesilen blok TAMAMEN tükeniyor, yani aynı blok ikinci
                # kez kesilemez; ayırt edici bir üretim eki gerekmiyor.
                # Aynı blok no'lu plakalar yine de yan yana gelirse
                # ayrımı SLAB NUMARASI yapar — bu yüzden başlangıç no
                # boşsa mevcut en büyük numaradan devam ediliyor
                # (aşağıda).
                uretim_blok_no = ana_kaynak.blok_no or ana_kaynak.id

            # SLAB NUMARALANDIRMA: başlangıç no'dan başla, atlanan (eksik) no'ları atla.
            # Örn. başlangıç=1, atlanan=[3,5] → 1,2,4,6,7...
            # B3 — YAZILAN DEĞER AYNEN KULLANILIR, 0 DAHİL.
            # `or 1` sıfırı sessizce 1 yapıyordu: kullanıcının yazdığı
            # numarayı haber vermeden değiştirmek, bu formdaki en kötü
            # davranış.
            #
            # Alan BOŞ bırakılırsa o blok no'da kayıtlı EN BÜYÜK
            # numaradan devam edilir — toplu içe aktarmadaki kuralın
            # aynısı. Üretim no artık orijinal blok no olduğu için
            # (yukarı bak) bu kural çakışmayı önleyen şeyin kendisi:
            # aynı blok no'lu plakalar yan yana gelse bile numaraları
            # ardışık ilerler.
            _bas_ham = data.get('baslangic_slab')
            _bas_ham = '' if _bas_ham is None else str(_bas_ham).strip()
            if _bas_ham == '':
                _enb = db.session.query(db.func.max(PlakaStok.slab_no)).filter(
                    db.func.upper(PlakaStok.blok_no) ==
                    str(uretim_blok_no or '').upper()).scalar()
                _slab_sira = int(_enb) + 1 if _enb is not None else 1
            else:
                try:
                    _slab_sira = int(float(_bas_ham))
                except (ValueError, TypeError):
                    _slab_sira = 1
                if _slab_sira < 0:
                    _slab_sira = 0
'''),
    ('flask_app.py', 'B3 · flask_app.py blok 6',
     r'''                    _pno = f"{s.blok_no or ''}#{s.slab_no}".strip('#')
''',
     r'''                    _pno = _plaka_kodu(s.blok_no, s.slab_no) or s.id
'''),
    ('flask_app.py', 'B3 · flask_app.py blok 7',
     r'''                _no = f"{s.blok_no or ''}#{s.slab_no}".lstrip('#') if s.slab_no else (s.blok_no or s.id)
''',
     r'''                _no = _plaka_kodu(s.blok_no, s.slab_no) or s.id
'''),
    ('flask_app.py', 'B3 · flask_app.py blok 8',
     r'''                    blok_slab = f"{s.blok_no or ''}#{s.slab_no or ''}" if s.blok_no else (s.slab_no or '')
''',
     r'''                    blok_slab = _plaka_kodu(s.blok_no, s.slab_no)
'''),
    ('templates/base.html', 'B3 · templates/base.html blok 1',
     r'''/* ══ BANKA/KASA ETİKETİ (BK4) ══
''',
     r'''/* ══ PLAKA KODU (B3) ══
   Plakanın depoda okunan kodu: K6461-01

   Sunucudaki `_plaka_kodu` ile AYNI kural. Ekranlarda da tek
   kopya duruyor: stok listesi ve proforma ikisi de `blok#slab`
   diye elle kuruyordu ve biçim değişince birini unutmak, aynı
   plakanın iki ekranda iki ayrı kodla görünmesiyle biterdi.

   Plaka no İKİ HANE: K6461-00, K6461-01, K6461-12. */
function plakaKodu(blokNo, slabNo) {
  const b = String(blokNo == null ? '' : blokNo).trim();
  if (slabNo === null || slabNo === undefined || String(slabNo).trim() === '')
    return b;
  const n = parseInt(slabNo, 10);
  const s = Number.isFinite(n) ? String(n).padStart(2, '0')
                               : String(slabNo).trim();
  return b ? `${b}-${s}` : s;
}

/* ══ BANKA/KASA ETİKETİ (BK4) ══
'''),
    ('templates/stok.html', 'B3 · templates/stok.html blok 1',
     r'''            <input id="tBaslangicNo" type="number" min="1" step="1" data-buyuk-harf="hayir"
                   placeholder="boş = otomatik devam"
                   title="Plaka numaralandırması bu numaradan başlar. Örneğin ilk 15 plakayı almadıysanız 16 yazın. Boş bırakılırsa o blokta kayıtlı en büyük numaradan devam eder.">
''',
     r'''            <input id="tBaslangicNo" type="number" min="0" step="1" data-buyuk-harf="hayir"
                   placeholder="boş = otomatik devam"
                   title="Plaka numaralandırması bu numaradan başlar. Örneğin ilk 15 plakayı almadıysanız 16 yazın. 0 da geçerlidir. Boş bırakılırsa o blokta kayıtlı en büyük numaradan devam eder.">
'''),
    ('templates/stok.html', 'B3 · templates/stok.html blok 2',
     r'''        <div class="form-alan" id="basNoAlan" style="display:none"><label id="basNoLabel">Başlangıç Slab No</label><input id="sBasNo" type="number" value="1"></div>
''',
     r'''        <div class="form-alan" id="basNoAlan" style="display:none"><label id="basNoLabel">Başlangıç Slab No</label><input id="sBasNo" type="number" min="0" value="1"
               title="İlk plakanın numarası. 0 da geçerlidir."></div>
'''),
    ('templates/stok.html', 'B3 · templates/stok.html blok 3',
     r'''  if (x.tip === 'PLAKA')  return x.slab_no ? `${x.blok_no || ''}#${x.slab_no}`.replace(/^#/, '')
''',
     r'''  if (x.tip === 'PLAKA')  return x.slab_no ? plakaKodu(x.blok_no, x.slab_no)
'''),
    ('templates/stok.html', 'B3 · templates/stok.html blok 4',
     r'''/* Tüm grupları sırayla oku; numaraları ve toplamları hesapla. */
function olcuGruplariOku() {
  const bas = parseInt(document.getElementById('sBasNo').value) || 1;
''',
     r'''/* ── BAŞLANGIÇ PLAKA NO (B3) ──
   `parseInt(...) || 1` sıfırı 1'e çeviriyordu: yazdığın numara
   haber verilmeden değişiyordu. 0 geçerli bir plaka numarası.
   Alan boşsa 1 varsayılır (tekil formda "devam et" kuralı yok —
   orada blok no'yu da elle giriyorsun). */
function _basNoOku(id) {
  const el = document.getElementById(id);
  const n = parseInt(el ? el.value : '', 10);
  if (!Number.isFinite(n) || n < 0) return 1;
  return n;
}

/* Tüm grupları sırayla oku; numaraları ve toplamları hesapla. */
function olcuGruplariOku() {
  const bas = _basNoOku('sBasNo');
'''),
    ('templates/stok.html', 'B3 · templates/stok.html blok 5',
     r'''        baslangic_no: parseInt(document.getElementById('sBasNo').value) || 1,
''',
     r'''        baslangic_no: _basNoOku('sBasNo'),
'''),
    ('templates/stok.html', 'B3 · templates/stok.html blok 6',
     r'''  const baslangicVar = Number.isFinite(elleBaslangic) && elleBaslangic > 0;
''',
     r'''  /* B3: 0 GEÇERLİ bir başlangıç. Eskiden `> 0` olduğu için 0 yazmak
     "girilmedi" sayılıyor ve sessizce otomatik devama düşüyordu. */
  const baslangicVar = Number.isFinite(elleBaslangic) && elleBaslangic >= 0;
'''),
    ('templates/kesim.html', 'B3 · templates/kesim.html blok 1',
     r'''          <input id="fUretimNo" placeholder="Boş bırakılırsa otomatik üretilir — örn. A-2026-001-U1"
''',
     r'''          <input id="fUretimNo" placeholder="Boş bırakılırsa kaynağın blok no'su kullanılır"
'''),
    ('templates/kesim.html', 'B3 · templates/kesim.html blok 2',
     r'''          <div class="form-alan"><label>Başlangıç No</label><input id="fSlabBas" type="number" min="1" value="1"></div>
''',
     r'''          <div class="form-alan"><label>Başlangıç No</label><input id="fSlabBas" type="number" min="0"
                 placeholder="boş = otomatik devam"
                 title="İlk plakanın numarası. 0 da geçerlidir. Boş bırakılırsa bu blok no'da kayıtlı en büyük numaradan devam edilir."></div>
'''),
    ('templates/kesim.html', 'B3 · templates/kesim.html blok 3',
     r'''/* Üretim blok no önerisi: orijinal no + -U + yıl kısaltması + sıra */
function uretimNoOner() {
  const k = KAYNAKLAR.find(x => x.id === SECILI_KAYNAK[0]);
  if (!k) { bildir('Önce kaynak seç.', true); return; }
  const orijinal = k.no || k.id;
  const yy = String(new Date().getFullYear()).slice(-2);
  document.getElementById('fUretimNo').value = `${orijinal}-U${yy}1`;
''',
     r'''/* Üretim blok no önerisi: ORİJİNAL BLOK NO (B3).

   Burada üç ayrı kural dolaşıyordu: bu düğme `-U261`, sunucu
   `-U1-01`, yorum satırı bambaşka bir şey diyordu. Üçü de aynı
   alanı dolduruyordu ve hangisinin çalıştığı alanı elle doldurup
   doldurmadığına bağlıydı.

   Kesilen blok tamamen tükendiği için ayırt edici ek gerekmiyor;
   plakaları birbirinden ayıran şey SLAB NUMARASI. */
function uretimNoOner() {
  const k = KAYNAKLAR.find(x => x.id === SECILI_KAYNAK[0]);
  if (!k) { bildir('Önce kaynak seç.', true); return; }
  document.getElementById('fUretimNo').value = k.no || k.id;
'''),
    ('templates/kesim.html', 'B3 · templates/kesim.html blok 4',
     r'''      baslangic_slab: parseInt(document.getElementById('fSlabBas').value) || 1,
''',
     r'''      /* B3: boş GÖNDERİLİR — sunucu o blokta kalınan yerden devam
         eder. 0 da aynen gider; `|| 1` onu sessizce 1 yapıyordu. */
      baslangic_slab: document.getElementById('fSlabBas').value.trim(),
'''),
    ('templates/proforma.html', 'B3 · templates/proforma.html blok 1',
     r'''    return x.blok_no ? `${x.blok_no}#${x.slab_no || ''}` : (x.id || '');
''',
     r'''    return x.blok_no ? plakaKodu(x.blok_no, x.slab_no) : (x.id || '');
'''),
    ('tests/test_kritik.py', 'B3 · tests/test_kritik.py blok 1',
     r'''        assert "api('/api/lookup" not in h, yol
''',
     r'''        assert "api('/api/lookup" not in h, yol


# ══════════════════════════════════════════════════════════════════════
#  B3 · PLAKA KODU TEK YERDEN · ÜRETİM NO SADE · BAŞLANGIÇ 0
# ══════════════════════════════════════════════════════════════════════

def test_b3_plaka_kodu_tek_kaynaktan():
    """B3: `blok#slab` dizesi artık elle kurulmuyor.

    Yedi ayrı yerde kuruluyordu (stok listesi, global arama, maliyet,
    proforma, Excel dışa aktarma, içe aktarma uyarısı, denetim
    kaydı). Biçim değişince altısını düzeltip birini unutmak, aynı
    plakanın iki ekranda iki ayrı kodla görünmesiyle biterdi."""
    import io as _io, re as _re
    fa_ = _io.open('flask_app.py', encoding='utf-8').read()
    assert 'def _plaka_kodu(' in fa_
    # Elle kurulan hiçbir kalıp kalmamış
    assert not _re.search(r"#\{s\.slab_no", fa_), 'flask_app: elle kurulan kod'
    assert not _re.search(r"\{blok_no\} #\{slab_no\}", fa_), 'flask_app: uyarı metni'

    base = _io.open('templates/base.html', encoding='utf-8').read()
    assert 'function plakaKodu(' in base
    for yol in ('templates/stok.html', 'templates/proforma.html'):
        h = _io.open(yol, encoding='utf-8').read()
        assert 'plakaKodu(' in h, yol
        assert not _re.search(r"\}#\$\{.*slab_no", h), (yol, 'elle kurulan kod')
        assert 'function plakaKodu' not in h, (yol, 'ikinci kopya')


def test_b3_plaka_kodu_bicimi():
    """B3: kod `blok-İKİ HANE`; 0 da geçerli bir numara."""
    import shutil as _shutil, subprocess as _sp, os as _os, json as _json
    # Sunucudaki ikizi `create_app` kapsamında; onun davranışı aşağıdaki
    # uçtan uca testlerde ölçülüyor. Burada EKRAN tarafı node ile
    # koşuluyor — `js_denetim` yalnız ayrıştırılabilirliğe bakıyor.
    node = _shutil.which('node') or '/opt/node22/bin/node'
    if not _os.path.exists(node):
        import pytest as _pytest
        _pytest.skip('node yok')
    betik = r"""
const fs = require('fs'), vm = require('vm');
const h = fs.readFileSync('templates/base.html', 'utf8');
const bas = h.indexOf('function plakaKodu(');
const son = h.indexOf('/* ══ BANKA/KASA ETİKETİ', bas);
const kum = {}; vm.createContext(kum);
vm.runInContext(h.slice(bas, son), kum);
console.log(JSON.stringify({
  bir: kum.plakaKodu('K6461', 1),
  sifir: kum.plakaKodu('K6461', 0),
  oniki: kum.plakaKodu('K6461', 12),
  yuz: kum.plakaKodu('K6461', 100),
  noYok: kum.plakaKodu('K6461', null),
  blokYok: kum.plakaKodu('', 3),
}));
"""
    r = _sp.run([node, '-e', betik], capture_output=True, text=True, cwd='.')
    assert r.returncode == 0, r.stderr[:400]
    d = _json.loads(r.stdout.strip().splitlines()[-1])
    assert d['bir'] == 'K6461-01', d['bir']
    assert d['sifir'] == 'K6461-00', d['sifir']
    assert d['oniki'] == 'K6461-12' and d['yuz'] == 'K6461-100'
    assert d['noYok'] == 'K6461' and d['blokYok'] == '03'


def test_b3_uretim_no_orijinal_blok_no():
    """B3: üretim blok no artık dilimlenmiş kesim numarası DEĞİL.

    Eskiden `blok_no + '-U' + kesim_id[-4:]` idi; o dilim token
    ortasından kesip K6461-U1-01 üretiyordu."""
    from models import BlokStok, PlakaStok, Kesim
    with fa.app.app_context():
        db.session.add(BlokStok(id='BLKB3A', blok_no='K7001', cins='TEST',
                                boy=300, yukseklik=150, en=120, hacim_m3=5.4,
                                tonaj=14.5, alis_fiyati=400,
                                alis_fiyat_birim='ton', doviz='USD',
                                durum='Serbest', uretici='ALBSTONE'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': ['BLKB3A'],
        'kesim_tarihi': '2026-03-05',
        # uretim_blok_no GÖNDERİLMİYOR — otomatik kural ölçülüyor
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'TEST', 'boy': 250,
                      'yukseklik': 160, 'kalinlik': 2, 'adet': 3}]})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    with fa.app.app_context():
        kesim = Kesim.query.get(d['kesim_id'])
        assert kesim.uretim_blok_no == 'K7001', kesim.uretim_blok_no
        assert '-U' not in kesim.uretim_blok_no
        for o in d['olusan_stoklar']:
            p = PlakaStok.query.get(o['id'])
            assert p.blok_no == 'K7001', p.blok_no


def test_b3_baslangic_no_sifir_aynen_gider():
    """B3: 0 geçerli bir plaka numarası — sessizce 1'e çekilmemeli."""
    from models import BlokStok, PlakaStok
    with fa.app.app_context():
        db.session.add(BlokStok(id='BLKB3B', blok_no='K7002', cins='TEST',
                                boy=300, yukseklik=150, en=120, hacim_m3=5.4,
                                tonaj=14.5, alis_fiyati=400,
                                alis_fiyat_birim='ton', doviz='USD',
                                durum='Serbest', uretici='ALBSTONE'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    r = c.post('/api/kesim', headers=H, json={
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': ['BLKB3B'],
        'kesim_tarihi': '2026-03-05', 'baslangic_slab': 0,
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'TEST', 'boy': 250,
                      'yukseklik': 160, 'kalinlik': 2, 'adet': 3}]})
    assert r.status_code == 200, r.get_data(as_text=True)
    with fa.app.app_context():
        nolar = sorted(p.slab_no for p in
                       PlakaStok.query.filter_by(blok_no='K7002').all())
        assert nolar == [0, 1, 2], nolar

    # Tekil stok formu da 0'ı kabul etmeli
    r2 = c.post('/api/stok/ekle', headers=H, json={
        'tip': 'PLAKA', 'cins': 'TEST', 'blok_no': 'K7003', 'boy': 250,
        'yukseklik': 160, 'kalinlik': 2, 'adet': 2, 'baslangic_no': 0,
        'fiyat': 20, 'fiyat_birim': 'm2', 'doviz': 'USD',
        'uretici': 'ALBSTONE', 'alis_tipi': 'ithalat'})
    assert r2.status_code == 200, r2.get_data(as_text=True)
    with fa.app.app_context():
        nolar = sorted(p.slab_no for p in
                       PlakaStok.query.filter_by(blok_no='K7003').all())
        assert nolar == [0, 1], nolar


def test_b3_baslangic_bos_kalinan_yerden_devam():
    """B3: üretim no artık orijinal blok no olduğu için aynı blok
    no'lu plakalar yan yana gelebilir. Başlangıç BOŞ bırakılırsa
    numara kalınan yerden devam etmeli — yoksa ikinci kesim birinci
    kesimin numaralarını tekrar ederdi."""
    from models import BlokStok, PlakaStok
    with fa.app.app_context():
        for _i, _id in enumerate(('BLKB3C1', 'BLKB3C2')):
            db.session.add(BlokStok(id=_id, blok_no='K7004', cins='TEST',
                                    boy=300, yukseklik=150, en=120,
                                    hacim_m3=5.4, tonaj=14.5, alis_fiyati=400,
                                    alis_fiyat_birim='ton', doviz='USD',
                                    durum='Serbest', uretici='ALBSTONE'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    govde = lambda kid: {
        'kesim_yon': 'BLOK_PLAKA', 'kaynak_ids': [kid],
        'kesim_tarihi': '2026-03-05', 'baslangic_slab': '',
        'hedefler': [{'hedef_tip': 'PLAKA', 'cins': 'TEST', 'boy': 250,
                      'yukseklik': 160, 'kalinlik': 2, 'adet': 3}]}
    assert c.post('/api/kesim', headers=H, json=govde('BLKB3C1')).status_code == 200
    assert c.post('/api/kesim', headers=H, json=govde('BLKB3C2')).status_code == 200
    with fa.app.app_context():
        nolar = sorted(p.slab_no for p in
                       PlakaStok.query.filter_by(blok_no='K7004').all())
        assert nolar == [1, 2, 3, 4, 5, 6], nolar
'''),
]

# ══════════════════════════════════════════════════════════════════════
#  TAM DOSYA · goc_b3.py
#
#  Parça değil tam dosya; iç içe tırnak yığını üretmesin diye
#  base64. Uygulandıktan sonra diskteki dosya baştan sona
#  yorumlu, okunur Python — yamayı uygulamadan okumak istersen:
#      python3 yama_b3.py --yaz-gecici
# ══════════════════════════════════════════════════════════════════════
TAM_ICERIK = {
    'goc_b3.py': (
        'IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwojIC0qLSBjb2Rpbmc6IHV0Zi04IC0qLQojIOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkAojICBNaWxlc3RvbmUgRVJQIOKAlCDDnFJFVMSwTSBCTE9LIE5PIFNBREVMRcWe'
        'VMSwUk1FICDCtyAgQjMKIwojICDDlk5LT8WeVUw6IHlhbWFfYjMucHkgdXlndWxhbm3E'
        'scWfIG9sbWFsxLEuICjFnmVtYSBkZcSfacWfaWtsacSfaSBZT0s7IGJ1CiMgIGJldGlr'
        'IHlhbG7EsXpjYSBtZXRpbiBkw7x6ZWx0aXlvciwgc2VydmlzaW4geWVuaWRlbiBiYcWf'
        'bGFtYXPEsW7EsQojICBiZWtsZW1layB6b3J1bmRhIGRlxJ9pbC4pCiMKIyAg4pSA4pSA'
        'IFNPUlVOIOKUgOKUgAojICAgIEtlc2ltIGtheWRlZGVya2VuIMO8cmV0aW0gYmxvayBu'
        'byBib8WfIGLEsXJha8SxbMSxcnNhIHN1bnVjdSDFn3VudQojICAgIMO8cmV0aXlvcmR1'
        'OgojCiMgICAgICAgIHVyZXRpbV9ibG9rX25vID0gYmxva19ubyArICctVScgKyBrZXNp'
        'bV9pZFstNDpdCiMKIyAgICBLZXNpbSBudW1hcmFzxLEgS1NNLUs2NDYxLTAxIGJpw6dp'
        'bWluZGUuIFNvbiBEw5ZSVCBrYXJha3RlcgojICAgICcxLTAxJyDigJQgeWFuaSBLNjQ2'
        'MSdpbiBzb24gaGFuZXNpIGRlIGRpbGltZSBnaXJpeW9yOgojCiMgICAgICAgIEs2NDYx'
        'ICDihpIgIEs2NDYxLVUxLTAxICAgICAgICAoYmVrbGVuZW46IEs2NDYxLVUwMSkKIwoj'
        'ICAgIFBsYWthbsSxbiBrb2R1IGJ1IG5vJ2RhbiB0w7xyZWRpxJ9pIGnDp2luIGRlcG9k'
        'YQojICAgIEs2NDYxLVUxLTAxIzEgZGl5ZSBva3VudXlvcmR1LgojCiMgIOKUgOKUgCBZ'
        'QU1BIE5FIFlBUFRJIOKUgOKUgAojICAgIFllbmkga2VzaW1sZXJkZSDDvHJldGltIG5v'
        'IGFydMSxayBPUsSwSsSwTkFMIEJMT0sgTk8uIEFtYSBFU0vEsAojICAgIGthecSxdGxh'
        'ciBkw7x6ZWxtZXo6IHlhbWFkYW4gc29ucmEgb25sYXIgeWVuaSBiacOnaW1sZSBiaXJs'
        'ZcWfaXAKIyAgICBLNjQ2MS1VMS0wMS0wMSBkaXllIGfDtnLDvG7DvHIuIEJ1IGJldGlr'
        'IG9ubGFyxLEga8Sxc2FsdMSxeW9yLgojCiMgIOKUgOKUgCDDlkzDh8OcVDogVEFITcSw'
        'TiBZT0ssIEtBWUlUIFZBUiDilIDilIAKIyAgICBCaXIgZGXEn2VyIFlBTE5JWkNBIMO8'
        'w6cgxZ9hcnTEsW4gaGVwc2kgdHV0YXJzYSBkw7x6ZWx0aWxpcjoKIwojICAgICAgMSkg'
        'S2FsxLFiYSB1eXV5b3I6ICA8a8O2az4tVTxyYWthbT4tPGlraSBoYW5lPgojICAgICAg'
        'ICAgKHlhbG7EsXogc3VudWN1bnVuIMO8cmV0dGnEn2kga2F6YW7EsW4gxZ9la2xpLiBT'
        'ZW5pbiBlbGxlCiMgICAgICAgICAgeWF6ZMSxxJ/EsW4geWEgZGEgIsO2bmVyIiBkw7zE'
        'n21lc2l5bGUgZ2VsZW4gLVUyNjEgZ2liaQojICAgICAgICAgIGRlxJ9lcmxlciBCVSBL'
        'QUxJQkEgVVlNQVogdmUgZG9rdW51bG1hei4pCiMgICAgICAyKSBPIGRlxJ9lcmUgc2Fo'
        'aXAgYmlyIEtFU8SwTSB2YXIgdmUgbyBrZXNpbWluIGtheW5ha19ubydzdQojICAgICAg'
        'ICAgdGFtIG9sYXJhayA8a8O2az4nZSBlxZ9pdC4KIyAgICAgIDMpIEvEsXNhbHTEsWxt'
        'xLHFnyBow6JsaSwgYXluxLEgYmxva3RhIEJBxZ5LQSBiaXIgcGxha2F5bGEKIyAgICAg'
        'ICAgIMOnYWvEscWfbcSxeW9yIChibG9rX25vICsgc2xhYl9ubyDDp2lmdGkgc2VyYmVz'
        'dCkuCiMKIyAgICDDnMOnw7xuZGVuIGJpcmkgdHV0bWF6c2EgbyBrYXnEsXQgQVRMQU5J'
        'UiB2ZSByYXBvcmRhIG5lZGVuCiMgICAgYXRsYW5kxLHEn8SxIHlhemFyLgojCiMgIOKU'
        'gOKUgCBORSBERcSexLDFnsSwUiDilIDilIAKIyAgICBwbGFrYV9zdG9rLmJsb2tfbm8g'
        'ICAgICB2ZSAgICAgIGtlc2ltLnVyZXRpbV9ibG9rX25vCiMKIyAg4pSA4pSAIE5FIERF'
        'xJ7EsMWeTUVaIOKUgOKUgAojICAgIMK3IEtpbWxpa2xlciAocGxha2Ffc3Rvay5pZCA9'
        'IFBMSy1LNjQ2MS1VMS0wMS0wMSkgT0xEVcSeVSBHxLBCxLAKIyAgICAgIEtBTElSLiBL'
        'aW1sacSfZSBzaXBhcmnFnyBrYWxlbWxlcmksIHByb2Zvcm1hIHNhdMSxcmxhcsSxLCBr'
        'ZXNpbQojICAgICAgZGV0YXlsYXLEsSB2ZSBkZW5ldGltIGthecSxdGxhcsSxIGJhxJ9s'
        'xLE7IG9ubGFyxLEgeWVuaWRlbgojICAgICAgeWF6bWFrLCBnw7Zyw7xuZW4gYmlyIGtv'
        'ZHUgZMO8emVsdG1layBpw6dpbiB2ZXJpIHppbmNpcmluaQojICAgICAga2VzbWVrIG9s'
        'dXJkdS4gS2ltbGlrIGnDpyBudW1hcmE7IGRlcG9kYSBva3VkdcSfdW4ga29kCiMgICAg'
        'ICBibG9rX25vJ2RhbiB0w7xyw7x5b3IgdmUgbyBkw7x6ZWxpeW9yLgojICAgIMK3IEhp'
        'w6diaXIgc2F0xLFyIHNpbGlubWV6LCB0dXRhcmxhciBkZcSfacWfbWV6LCBzbGFiIG51'
        'bWFyYWxhcsSxCiMgICAgICBkZcSfacWfbWV6LgojCiMgIOKUgOKUgCBHw5xWRU5MxLBL'
        'IOKUgOKUgAojICAgIOKAoiAtLXV5Z3VsYSBPTE1BREFOIEjEsMOHQsSwUiDFnkVZIERF'
        'xJ7EsMWeTUVaOyB5YWxuxLF6Y2EgcmFwb3IgdmVyaXIuCiMgICAg4oCiIFBvc3RncmVT'
        'UUwnZGUgw7ZuY2UgcGdfZHVtcCB5ZWRlxJ9pIGFsxLFyOyB5ZWRlayBiYcWfYXLEsXPE'
        'sXpzYSDEsFBUQUwuCiMgICAg4oCiIFRlayB0cmFuc2FjdGlvbi4KIyAgICDigKIgVGVr'
        'cmFyIMOnYWzEscWfdMSxcsSxbGFiaWxpcjogaWtpbmNpIGtvxZ91ICJ5YXDEsWxhY2Fr'
        'IGnFnyB5b2siIGRlci4KIwojICBLVUxMQU5JTSAocHJvamUgZGl6aW5pbmRlKToKIyAg'
        'ICAgIHZlbnYvYmluL3B5dGhvbiBnb2NfYjMucHkgICAgICAgICAgICAgIyBSQVBPUgoj'
        'ICAgICAgdmVudi9iaW4vcHl0aG9uIGdvY19iMy5weSAtLXV5Z3VsYSAgICAjIFVZR1VM'
        'QVIKIyDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDilZDi'
        'lZDilZDilZDilZAKaW1wb3J0IG9zCmltcG9ydCByZQppbXBvcnQgc3VicHJvY2Vzcwpp'
        'bXBvcnQgc3lzCmZyb20gZGF0ZXRpbWUgaW1wb3J0IGRhdGV0aW1lCmZyb20gcGF0aGxp'
        'YiBpbXBvcnQgUGF0aApmcm9tIHVybGxpYi5wYXJzZSBpbXBvcnQgdXJscGFyc2UKCmZy'
        'b20gZG90ZW52IGltcG9ydCBsb2FkX2RvdGVudgpmcm9tIHNxbGFsY2hlbXkgaW1wb3J0'
        'IGNyZWF0ZV9lbmdpbmUsIGluc3BlY3QsIHRleHQKCmxvYWRfZG90ZW52KCkKClVZR1VM'
        'QSA9ICctLXV5Z3VsYScgaW4gc3lzLmFyZ3YKVlRfVVJMID0gb3MuZW52aXJvbi5nZXQo'
        'J0RBVEFCQVNFX1VSTCcpCgppZiBub3QgVlRfVVJMOgogICAgcHJpbnQoJ0hBVEE6IERB'
        'VEFCQVNFX1VSTCBidWx1bmFtYWTEsSAoLmVudiBva3VuYW1hZMSxKS4nKQogICAgcHJp'
        'bnQoJyAgQWRyZXMgb2xtYWRhbiB5YW5sxLHFnyB2ZXJpdGFiYW7EsW5hIGJhxJ9sYW5h'
        'YmlsaXJkaW0uJykKICAgIHN5cy5leGl0KDEpCgptb3RvciA9IGNyZWF0ZV9lbmdpbmUo'
        'VlRfVVJMKQprYXluYWtfdXJsID0gdXJscGFyc2UoVlRfVVJMKQpwZyA9IG1vdG9yLmRp'
        'YWxlY3QubmFtZSBpbiAoJ3Bvc3RncmVzcWwnLCAncG9zdGdyZXMnKQpkZW5ldGNpID0g'
        'aW5zcGVjdChtb3RvcikKCnByaW50KCfilZAnICogNzApCnByaW50KCcgIE1JTEVTVE9O'
        'RSBFUlAg4oCUIMOcUkVUxLBNIEJMT0sgTk8gU0FERUxFxZ5UxLBSTUUgIMK3ICBCMycp'
        'CnByaW50KCcgIE1PRDonLCAnVVlHVUxBJyBpZiBVWUdVTEEgZWxzZSAnUkFQT1IgKGhp'
        'w6diaXIgxZ9leSBkZcSfacWfbWV6KScpCnByaW50KCfilZAnICogNzApCnByaW50KGYi'
        'IFZlcml0YWJhbsSxIDoge2theW5ha191cmwucGF0aC5sc3RyaXAoJy8nKX0gQCB7a2F5'
        'bmFrX3VybC5ob3N0bmFtZSBvciAneWVyZWwnfSIpCnByaW50KGYnIFPDvHLDvGPDvCAg'
        'ICAgOiB7bW90b3IuZGlhbGVjdC5uYW1lfScpCnByaW50KCkKCiMgU3VudWN1bnVuIMO8'
        'cmV0dGnEn2kga2F6YW7EsW4gxZ5FS0zEsDoga8O2ayArICctVScgKyA8cmFrYW0+ICsg'
        'Jy0nICsgPGlraSBoYW5lPgpLQUxJUCA9IHJlLmNvbXBpbGUocideKD9QPGtvaz4uKykt'
        'VVxkLVxkezJ9JCcpCgpUQUJMT0xBUiA9ICgncGxha2Ffc3RvaycsICdrZXNpbScpCnRh'
        'YmxvbGFyID0gc2V0KGRlbmV0Y2kuZ2V0X3RhYmxlX25hbWVzKCkpCmVrc2lrID0gW3Qg'
        'Zm9yIHQgaW4gVEFCTE9MQVIgaWYgdCBub3QgaW4gdGFibG9sYXJdCmlmIGVrc2lrOgog'
        'ICAgcHJpbnQoZiIg4pyXIMWedSB0YWJsbyhsYXIpIHlvazogeycsICcuam9pbihla3Np'
        'ayl9IikKICAgIHByaW50KCcgICBZYW5sxLHFnyB2ZXJpdGFiYW7EsW5hIGJhxJ9sYW5t'
        'xLHFnyBvbGFiaWxpcmltLiBEdXJ1eW9ydW0uJykKICAgIHN5cy5leGl0KDEpCgoKZGVm'
        'IHllZGVrX2FsKCk6CiAgICBpZiBub3QgcGc6CiAgICAgICAgcHJpbnQoJyDimqAgUG9z'
        'dGdyZVNRTCBkZcSfaWwg4oCUIG90b21hdGlrIHllZGVrIGF0bGFuZMSxLicpCiAgICAg'
        'ICAgcmV0dXJuIFRydWUKICAgIGhlZGVmID0gUGF0aC5ob21lKCkgLyAneWVkZWtsZXIn'
        'CiAgICBoZWRlZi5ta2RpcihleGlzdF9vaz1UcnVlKQogICAgZG9zeWEgPSBoZWRlZiAv'
        'IGYnYjMtb25jZXNpLXtkYXRldGltZS5ub3coKTolWSVtJWRfJUglTSVTfS5kdW1wJwog'
        'ICAgdHJ5OgogICAgICAgIG9ydGFtID0gZGljdChvcy5lbnZpcm9uKQogICAgICAgIGlm'
        'IGtheW5ha191cmwucGFzc3dvcmQ6CiAgICAgICAgICAgIG9ydGFtWydQR1BBU1NXT1JE'
        'J10gPSBrYXluYWtfdXJsLnBhc3N3b3JkCiAgICAgICAgcyA9IHN1YnByb2Nlc3MucnVu'
        'KAogICAgICAgICAgICBbJ3BnX2R1bXAnLCAnLUZjJywgJy1mJywgc3RyKGRvc3lhKSwK'
        'ICAgICAgICAgICAgICctaCcsIGtheW5ha191cmwuaG9zdG5hbWUgb3IgJ2xvY2FsaG9z'
        'dCcsCiAgICAgICAgICAgICAnLXAnLCBzdHIoa2F5bmFrX3VybC5wb3J0IG9yIDU0MzIp'
        'LAogICAgICAgICAgICAgJy1VJywga2F5bmFrX3VybC51c2VybmFtZSBvciAncG9zdGdy'
        'ZXMnLAogICAgICAgICAgICAga2F5bmFrX3VybC5wYXRoLmxzdHJpcCgnLycpXSwKICAg'
        'ICAgICAgICAgZW52PW9ydGFtLCBjYXB0dXJlX291dHB1dD1UcnVlLCB0ZXh0PVRydWUs'
        'IHRpbWVvdXQ9NjAwKQogICAgICAgIGlmIChzLnJldHVybmNvZGUgIT0gMCBvciBub3Qg'
        'ZG9zeWEuZXhpc3RzKCkKICAgICAgICAgICAgICAgIG9yIGRvc3lhLnN0YXQoKS5zdF9z'
        'aXplIDwgMTAyNCk6CiAgICAgICAgICAgIHByaW50KCcg4pyXIFllZGVrIEFMSU5BTUFE'
        'SSDigJQgZ8O2w6cgxLBQVEFMIGVkaWxkaS4nKQogICAgICAgICAgICBwcmludChmJyAg'
        'IHsocy5zdGRlcnIgb3IgIiIpLnN0cmlwKClbOjIwMF19JykKICAgICAgICAgICAgcmV0'
        'dXJuIEZhbHNlCiAgICAgICAgcHJpbnQoZicg4pyTIHtkb3N5YX0gICh7ZG9zeWEuc3Rh'
        'dCgpLnN0X3NpemUgLyAxMDI0Oi4wZn0gS0IpJykKICAgICAgICByZXR1cm4gVHJ1ZQog'
        'ICAgZXhjZXB0IEZpbGVOb3RGb3VuZEVycm9yOgogICAgICAgIHByaW50KCcg4pyXIHBn'
        'X2R1bXAgYnVsdW5hbWFkxLEg4oCUIGfDtsOnIMSwUFRBTCBlZGlsZGkuJykKICAgICAg'
        'ICByZXR1cm4gRmFsc2UKICAgIGV4Y2VwdCBzdWJwcm9jZXNzLlRpbWVvdXRFeHBpcmVk'
        'OgogICAgICAgIHByaW50KCcg4pyXIFllZGVrIHphbWFuIGHFn8SxbcSxbmEgdcSfcmFk'
        'xLEg4oCUIGfDtsOnIMSwUFRBTCBlZGlsZGkuJykKICAgICAgICByZXR1cm4gRmFsc2UK'
        'CgojIOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkAojICAxIMK3IEFEQVlMQVJJIEJVTAojIOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKV'
        'kOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkAp3aXRoIG1vdG9y'
        'LmNvbm5lY3QoKSBhcyBiOgogICAga2VzaW1sZXIgPSB7fQogICAgZm9yIGtpZCwgdWJu'
        'LCBrbm8gaW4gYi5leGVjdXRlKHRleHQoCiAgICAgICAgICAgICdTRUxFQ1QgaWQsIHVy'
        'ZXRpbV9ibG9rX25vLCBrYXluYWtfbm8gRlJPTSBrZXNpbSAnCiAgICAgICAgICAgICdX'
        'SEVSRSB1cmV0aW1fYmxva19ubyBJUyBOT1QgTlVMTCcpKToKICAgICAgICBrZXNpbWxl'
        'ci5zZXRkZWZhdWx0KHN0cih1Ym4pLCBbXSkuYXBwZW5kKChraWQsIGtubykpCgogICAg'
        'cGxha2FsYXIgPSBbKHBpZCwgc3RyKGJuIG9yICcnKSwgc24pIGZvciBwaWQsIGJuLCBz'
        'biBpbiBiLmV4ZWN1dGUodGV4dCgKICAgICAgICAnU0VMRUNUIGlkLCBibG9rX25vLCBz'
        'bGFiX25vIEZST00gcGxha2Ffc3RvayAnCiAgICAgICAgJ1dIRVJFIGJsb2tfbm8gSVMg'
        'Tk9UIE5VTEwnKSldCgojIMOHYWvEscWfbWEgZGVuZXRpbWkgacOnaW4gbWV2Y3V0IChi'
        'bG9rX25vLCBzbGFiX25vKSDDp2lmdGxlcmkKbWV2Y3V0X2NpZnQgPSB7KGJuLnVwcGVy'
        'KCksIHNuKSBmb3IgXywgYm4sIHNuIGluIHBsYWthbGFyfQoKZHV6ZWx0aWxlY2VrID0g'
        'e30gICAgICAjIGVza2lfbm8gLT4geWVuaV9ubwphdGxhbmFuID0gW10gICAgICAgICAg'
        'ICMgKGVza2lfbm8sIHNlYmVwKQoKZm9yIGVza2kgaW4gc29ydGVkKHNldChsaXN0KGtl'
        'c2ltbGVyLmtleXMoKSkgKyBbYm4gZm9yIF8sIGJuLCBfIGluIHBsYWthbGFyXSkpOgog'
        'ICAgbSA9IEtBTElQLm1hdGNoKGVza2kpCiAgICBpZiBub3QgbToKICAgICAgICBjb250'
        'aW51ZQogICAga29rID0gbS5ncm91cCgna29rJykKCiAgICAjIMWeQVJUIDI6IGtlc2lt'
        'IGtheWTEsSBkb8SfcnVsdXlvciBtdQogICAga2F5aXRsYXIgPSBrZXNpbWxlci5nZXQo'
        'ZXNraSkgb3IgW10KICAgIGlmIG5vdCBrYXlpdGxhcjoKICAgICAgICBhdGxhbmFuLmFw'
        'cGVuZCgoZXNraSwgJ2J1IMO8cmV0aW0gbm8gaWxlIGJpciBrZXNpbSBrYXlkxLEgeW9r'
        'JykpCiAgICAgICAgY29udGludWUKICAgIGlmIG5vdCBhbnkoc3RyKGtubyBvciAnJykg'
        'PT0ga29rIGZvciBfLCBrbm8gaW4ga2F5aXRsYXIpOgogICAgICAgIGF0bGFuYW4uYXBw'
        'ZW5kKChlc2tpLCBmJ2tlc2ltaW4ga2F5bmFrIG5vXCdzdSAie2tva30iIGRlxJ9pbCAn'
        'CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGYnKHtrYXlpdGxhclswXVsxXX0p'
        'JykpCiAgICAgICAgY29udGludWUKCiAgICAjIMWeQVJUIDM6IGvEsXNhbHTEsWxtxLHF'
        'nyBow6JsaSBiYcWfa2EgYmlyIHBsYWtheWxhIMOnYWvEscWfxLF5b3IgbXUKICAgIGNh'
        'a2lzYW4gPSBbc24gZm9yIF8sIGJuLCBzbiBpbiBwbGFrYWxhcgogICAgICAgICAgICAg'
        'ICBpZiBibiA9PSBlc2tpIGFuZCAoa29rLnVwcGVyKCksIHNuKSBpbiBtZXZjdXRfY2lm'
        'dF0KICAgIGlmIGNha2lzYW46CiAgICAgICAgYXRsYW5hbi5hcHBlbmQoKGVza2ksIGYn'
        'e2tva30gYmxvxJ91bmRhIHtjYWtpc2FuWzBdfSBudW1hcmFsxLEgJwogICAgICAgICAg'
        'ICAgICAgICAgICAgICAgICAgICBmJ3BsYWthIFpBVEVOIFZBUiDigJQgw6dha8SxxZ/E'
        'sXJkxLEnKSkKICAgICAgICBjb250aW51ZQoKICAgIGR1emVsdGlsZWNla1tlc2tpXSA9'
        'IGtvawoKcHJpbnQoJyDilIDilIAgQURBWUxBUiAnICsgJ+KUgCcgKiA1NikKaWYgbm90'
        'IGR1emVsdGlsZWNlayBhbmQgbm90IGF0bGFuYW46CiAgICBwcmludCgnICAgRMO8emVs'
        'dGlsZWNlayBrYXnEsXQgeW9rIOKAlCBiw7x0w7xuIMO8cmV0aW0gbm9cJ2xhciB6YXRl'
        'biBzYWRlLicpCiAgICBwcmludCgpCiAgICBwcmludCgn4pWQJyAqIDcwKQogICAgcHJp'
        'bnQoJyAg4pyTIFlBUElMQUNBSyDEsMWeIFlPSycpCiAgICBwcmludCgn4pWQJyAqIDcw'
        'KQogICAgc3lzLmV4aXQoMCkKCmZvciBlc2tpLCB5ZW5pIGluIGR1emVsdGlsZWNlay5p'
        'dGVtcygpOgogICAgcGwgPSBbcCBmb3IgcCBpbiBwbGFrYWxhciBpZiBwWzFdID09IGVz'
        'a2ldCiAgICBrcyA9IGxlbihrZXNpbWxlci5nZXQoZXNraSkgb3IgW10pCiAgICBwcmlu'
        'dChmJyAgIHtlc2tpOjwyNH0g4oaSIHt5ZW5pfScpCiAgICBwcmludChmJyAgICAgIHts'
        'ZW4ocGwpfSBwbGFrYSDCtyB7a3N9IGtlc2ltIGtheWTEsScpCiAgICBpZiBwbDoKICAg'
        'ICAgICBvcm5layA9IHNvcnRlZChwbCwga2V5PWxhbWJkYSB4OiAoeFsyXSBpcyBOb25l'
        'LCB4WzJdKSlbOjNdCiAgICAgICAgZm9yIF8sIGJuLCBzbiBpbiBvcm5lazoKICAgICAg'
        'ICAgICAgZXNrID0gZid7Ym59LXtpbnQoc24pOjAyZH0nIGlmIHNuIGlzIG5vdCBOb25l'
        'IGVsc2UgYm4KICAgICAgICAgICAgeWVuID0gZid7eWVuaX0te2ludChzbik6MDJkfScg'
        'aWYgc24gaXMgbm90IE5vbmUgZWxzZSB5ZW5pCiAgICAgICAgICAgIHByaW50KGYnICAg'
        'ICAgICAge2Vza30gIOKGkiAge3llbn0nKQoKaWYgYXRsYW5hbjoKICAgIHByaW50KCkK'
        'ICAgIHByaW50KCcg4pSA4pSAIEFUTEFOQU5MQVIgJyArICfilIAnICogNTMpCiAgICBm'
        'b3IgZXNraSwgc2ViZXAgaW4gYXRsYW5hbjoKICAgICAgICBwcmludChmJyAgIHtlc2tp'
        'OjwyNH0ge3NlYmVwfScpCgpwcmludCgpCmlmIG5vdCBkdXplbHRpbGVjZWs6CiAgICBw'
        'cmludCgn4pWQJyAqIDcwKQogICAgcHJpbnQoJyAg4oqZIETDvHplbHRpbGViaWxlY2Vr'
        'IGthecSxdCB5b2sgKGhlcHNpIGF0bGFuZMSxKS4nKQogICAgcHJpbnQoJ+KVkCcgKiA3'
        'MCkKICAgIHN5cy5leGl0KDApCgppZiBub3QgVVlHVUxBOgogICAgcHJpbnQoJ+KVkCcg'
        'KiA3MCkKICAgIHByaW50KCcgIFJBUE9SIE1PRFUg4oCUIGhpw6diaXIgxZ9leSBkZcSf'
        'acWfbWVkaS4nKQogICAgcHJpbnQoJyAgVXlndWxhbWFrIGnDp2luOiAgdmVudi9iaW4v'
        'cHl0aG9uIGdvY19iMy5weSAtLXV5Z3VsYScpCiAgICBwcmludCgn4pWQJyAqIDcwKQog'
        'ICAgc3lzLmV4aXQoMCkKCiMg4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCiMgIDIgwrcgVVlHVUxBCiMg4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ'
        '4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCnBy'
        'aW50KCcg4pSA4pSAIFlFREVLICcgKyAn4pSAJyAqIDU4KQppZiBub3QgeWVkZWtfYWwo'
        'KToKICAgIHN5cy5leGl0KDEpCnByaW50KCkKCndpdGggbW90b3IuYmVnaW4oKSBhcyBi'
        'OgogICAgcGxfdG9wID0ga3NfdG9wID0gMAogICAgZm9yIGVza2ksIHllbmkgaW4gZHV6'
        'ZWx0aWxlY2VrLml0ZW1zKCk6CiAgICAgICAgcjEgPSBiLmV4ZWN1dGUodGV4dCgnVVBE'
        'QVRFIHBsYWthX3N0b2sgU0VUIGJsb2tfbm8gPSA6eSAnCiAgICAgICAgICAgICAgICAg'
        'ICAgICAgICAgICAnV0hFUkUgYmxva19ubyA9IDplJyksIHsneSc6IHllbmksICdlJzog'
        'ZXNraX0pCiAgICAgICAgcjIgPSBiLmV4ZWN1dGUodGV4dCgnVVBEQVRFIGtlc2ltIFNF'
        'VCB1cmV0aW1fYmxva19ubyA9IDp5ICcKICAgICAgICAgICAgICAgICAgICAgICAgICAg'
        'ICdXSEVSRSB1cmV0aW1fYmxva19ubyA9IDplJyksIHsneSc6IHllbmksICdlJzogZXNr'
        'aX0pCiAgICAgICAgcGxfdG9wICs9IHIxLnJvd2NvdW50IG9yIDAKICAgICAgICBrc190'
        'b3AgKz0gcjIucm93Y291bnQgb3IgMAogICAgICAgIHByaW50KGYnICAge2Vza2l9IOKG'
        'kiB7eWVuaX06IHtyMS5yb3djb3VudH0gcGxha2EsIHtyMi5yb3djb3VudH0ga2VzaW0n'
        'KQoKcHJpbnQoKQpwcmludCgn4pWQJyAqIDcwKQpwcmludChmJyAg4pyTIEfDlsOHIFRB'
        'TUFNIOKAlCB7cGxfdG9wfSBwbGFrYSwge2tzX3RvcH0ga2VzaW0ga2F5ZMSxIGfDvG5j'
        'ZWxsZW5kaScpCnByaW50KCfilZAnICogNzApCnByaW50KCkKcHJpbnQoJyAgS2ltbGlr'
        'bGVyIChQTEst4oCmKSBiaWxlcmVrIERFxJ7EsMWeVMSwUsSwTE1FRMSwOiBvbmxhcmEg'
        'c2lwYXJpxZ8sJykKcHJpbnQoJyAgcHJvZm9ybWEgdmUga2VzaW0gZGV0YXlsYXLEsSBi'
        'YcSfbMSxLiBEZXBvZGEgb2t1ZHXEn3VuIGtvZCcpCnByaW50KCcgIGJsb2tfbm9cJ2Rh'
        'biB0w7xyw7x5b3IgdmUgbyBkw7x6ZWxkaS4nKQo='
    ),
}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA B3 — PLAKA KODU SADE, BASLANGIC NO 0')
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
        print('    python3 yama_b3.py            # rapor')
        print('    python3 yama_b3.py --uygula')
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
        print('  ⊙ Yama B3 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_b3.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_b3'
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
    print('  ══ SIRA ONEMLI ══')
    print()
    print('    1) sudo systemctl restart milestone-erp')
    print()
    print('    2) venv/bin/python goc_b3.py        <- once RAPOR')
    print('       Mevcut K6461-U1-01 kayitlarini kisaltir. Rapor')
    print('       neyin degisecegini ve neyin ATLANACAGINI yazar.')
    print()
    print('    3) venv/bin/python goc_b3.py --uygula')
    print()
    print('    4) Tarayicida Ctrl+F5')
    print()
    print('    5) venv/bin/python -m pytest tests/test_kritik.py -q')
    print()
    print('  BAKILACAK YERLER')
    print('    · Depo -> Stok -> Plaka: kod K6461-01 bicimi')
    print('    · Depo -> Kesim -> Yeni Kesim: Baslangic No bos')
    print('      birakilabiliyor (bos = kalinan yerden devam)')
    print('    · Baslangic No 0 yazinca plakalar 0,1,2... olmali')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

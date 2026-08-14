#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — MALİYETLER: SÜZGEÇLER VE EKSİK TÜRLER  ·  M1
#
#  ── İKİ EKSİK ──
#
#  1. TÜR SEKMELERİ EKSİK
#     Sekmeler: Tümü · Nakliye · Gümrük · Kesim/Fason · Komisyon
#     Ama sistemde BUNLAR DIŞINDA da maliyet kaydı üretiliyor:
#         maliyet_tip='Devreden KDV'   (flask_app.py)
#         maliyet_tip='Iade KDV'
#         'Diğer'                       (dağıtım kipinde seçilebiliyor)
#
#     Bu kayıtlar YALNIZCA "Tümü"nde görünüyordu; süzülemiyorlardı.
#     KDV izleme yaparken tam da bu kayıtlara bakmak gerekiyor.
#
#  2. SÜZGEÇ YOK
#     Yalnızca serbest metin araması var. Stok sayfasındaki gibi
#     açılır süzgeç yok: hangi stok tipine, hangi cinse, hangi
#     tedarikçiye ait olduğunu süzemiyorsunuz.
#
#  ── EKLENENLER ──
#     • Sekmeler: KDV · Diğer
#     • Süzgeçler: Stok Tipi · Cins · Cari (tedarikçi)
#
#  ── SEÇENEKLER LİSTEDEN ÜRETİLİR ──
#     Stok süzgeçlerinde (F1) olduğu gibi, seçenekler O ANDA
#     LİSTELENEN kayıtlardan çıkarılır ve yanlarında kaç kayıt
#     olduğu yazar. Olmayan seçeneği tıklayıp boş sonuç almazsınız.
#
#  ── CİNS VE STOK TİPİ NEREDEN GELİYOR ──
#     Maliyet kaydı stoğa `baglanti_id` ile bağlı. Cins doğrudan
#     maliyet tablosunda YOK; sunucu serializer'ının döndürdüğü
#     `baglanti_ad` alanından okunur. Bu alan yoksa süzgeç seçeneği
#     de oluşmaz — sessizce boş kalmaz, kutu görünmez.
#
#  KULLANIM (proje klasöründe):
#      python yama_m1_maliyet_suzgec.py            # rapor
#      python yama_m1_maliyet_suzgec.py --uygula   # uygula
#
#  SONRA:  python js_denetim.py
#  Şema değişikliği YOK.
# ══════════════════════════════════════════════════════════════════════
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
ML = Path('templates/maliyet.html')

if not ML.exists():
    print("HATA: templates/maliyet.html bulunamadı. Proje klasöründe çalıştırın.")
    sys.exit(1)

# ── A) Eksik tür sekmeleri + süzgeç kutuları ───────────────────────
A_ESKI = """  <button class="cip" data-t="Komisyon">Komisyon</button>
  <div class="suz"><input id="ara" placeholder="Fatura no, açıklama ara…" autocomplete="off"></div>
</div>"""

A_YENI = """  <button class="cip" data-t="Komisyon">Komisyon</button>
  <!-- M1: sistemde 'Devreden KDV' ve 'Iade KDV' kayitlari uretiliyor
       (flask_app.py) ama sekmesi yoktu — yalnizca "Tumu"nde
       gorunuyorlardi. KDV izleme yaparken tam bu kayitlara bakiliyor. -->
  <button class="cip" data-t="KDV">KDV</button>
  <button class="cip" data-t="Diğer">Diğer</button>
  <div class="suz"><input id="ara" placeholder="Fatura no, açıklama ara…" autocomplete="off"></div>
</div>

<!-- M1 — AÇILIR SÜZGEÇLER
     Seçenekler SABİT DEĞİL: o anda listelenen kayıtlardan üretilir
     ve yanlarında kaç kayıt olduğu yazar (stok sayfasındaki F1 ile
     aynı yaklaşım). Olmayan seçeneği tıklayıp boş sonuç almazsınız. -->
<div style="margin-bottom:8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap">
  <select id="mStokTip" onchange="mSuzgecDegisti()" class="msuz"
          title="Stok tipine göre süz"></select>
  <select id="mCins" onchange="mSuzgecDegisti()" class="msuz"
          title="Cinse göre süz"></select>
  <select id="mCari" onchange="mSuzgecDegisti()" class="msuz"
          title="Tedarikçiye göre süz"></select>
  <button class="blok-btn" id="mSuzSifirla" onclick="mSuzgecleriSifirla()"
          style="display:none;padding:4px 10px;font-size:.78rem">Süzgeçleri temizle</button>
  <span id="mSuzBilgi" style="font-size:.78rem;color:var(--soluk)"></span>
</div>"""

# ── B) Stil ────────────────────────────────────────────────────────
B_ESKI = """<div class="tablo-kutu">
  <table>
    <thead><tr><th>Tip</th><th>Bağlantı</th><th>Fatura No</th><th class="sag">Tutar</th><th class="sag">Tarih</th></tr></thead>"""

B_YENI = """<style>
/* M1 — süzgeç açılır kutuları */
.msuz{border:1px solid var(--cizgi-koyu);border-radius:7px;padding:5px 9px;
  font-size:.82rem;background:var(--kagit);color:var(--murekkep);cursor:pointer;
  max-width:200px}
.msuz:focus{outline:2px solid var(--verde);outline-offset:1px}
.msuz.dolu{border-color:var(--verde);background:var(--verde-acik);font-weight:600}
</style>
<div class="tablo-kutu">
  <table>
    <thead><tr><th>Tip</th><th>Bağlantı</th><th>Fatura No</th><th class="sag">Tutar</th><th class="sag">Tarih</th></tr></thead>"""

# ── C) Değişkenler ─────────────────────────────────────────────────
C_ESKI = """let TUM = [], TIP = '', ARA = '', HEDEFLER = [], SECILI_HEDEF = null, CARILER = [];"""
C_YENI = """let TUM = [], TIP = '', ARA = '', HEDEFLER = [], SECILI_HEDEF = null, CARILER = [];
/* M1 — açılır süzgeçler. Tür sekmesi ve metin aramasıyla AYNI
   katmanda (istemci) çalışır; üçü birlikte uygulanır. */
let M_STOKTIP = '', M_CINS = '', M_CARI = '';"""

# ── D) Süzme mantığı ───────────────────────────────────────────────
D_ESKI = """    (!TIP || (m.maliyet_tip || '').includes(TIP)) &&"""

D_YENI = """    /* M1: KDV sekmesi 'Devreden KDV' ve 'Iade KDV' kayitlarinin
       IKISINI de kapsar — ikisi de 'KDV' iceriyor. */
    (!TIP || (m.maliyet_tip || '').includes(TIP)) &&
    (!M_STOKTIP || (m.baglanti_tip || '') === M_STOKTIP) &&
    (!M_CINS    || String(m.baglanti_ad || '').toLocaleUpperCase('tr')
                     .includes(M_CINS.toLocaleUpperCase('tr'))) &&
    (!M_CARI    || (m.cari_unvan || m.cari_id || '') === M_CARI) &&"""

# ── E) JavaScript ──────────────────────────────────────────────────
E_ESKI = """function ciz() {"""

E_YENI = """/* ═══ MALİYET SÜZGEÇLERİ (M1) ═══
   Seçenekler o anda listelenen kayıtlardan üretilir; sabit liste
   kullanılmaz. Yanlarında kaç kayıt olduğu yazar. */
function mSecenekleriDoldur(kayitlar) {
  const kur = (cikar, id, etiket, secili) => {
    const el = document.getElementById(id);
    if (!el) return;
    const sayac = {};
    kayitlar.forEach(m => {
      const v = cikar(m);
      if (v) sayac[v] = (sayac[v] || 0) + 1;
    });
    const degerler = Object.keys(sayac).sort((a, b) => a.localeCompare(b, 'tr'));
    /* Seçili değer artık listede yoksa yine de seçenek olarak kalsın —
       aksi halde süzgeç sessizce sıfırlanır ve kullanıcı neden hepsini
       gördüğünü anlamaz. */
    if (secili && !degerler.includes(secili)) degerler.unshift(secili);
    /* Kutu HER ZAMAN görünür. Ilk surumde "secenek yoksa gizle"
       yapmistim; bos liste kafa karistirir diye dusunmustum ama
       KAYBOLAN KUTU daha kotu: kullanici ozelligin var oldugunu bile
       bilmiyor. Stok bosken hicbir suzgec gorunmuyordu, urun
       eklenince yalnizca "Stok tipi" beliriyordu.
       Seçenek yoksa kutu pasif görünür ve nedenini yazar. */
    el.disabled = !degerler.length;
    el.style.opacity = degerler.length ? '' : '.55';
    el.innerHTML = (degerler.length
        ? `<option value="">${etiket} (tümü)</option>`
        : `<option value="">${etiket} — kayıt yok</option>`) +
      degerler.map(v => `<option value="${kacar(v)}"${v === secili ? ' selected' : ''}>` +
        `${kacar(v)}${sayac[v] ? ' (' + sayac[v] + ')' : ''}</option>`).join('');
    el.value = secili || '';
    el.classList.toggle('dolu', !!secili);
  };
  kur(m => m.baglanti_tip || '', 'mStokTip', 'Stok tipi', M_STOKTIP);
  /* Cins doğrudan maliyet tablosunda YOK; bağlantı adından okunur.
     "CEPPO K-77 #12" gibi bir metnin İLK kelimesi cinstir.

     YALNIZCA STOK bağlantılarında anlamlı: sevkiyat/sipariş
     kayıtlarının cinsi yoktur, onlarda bağlantı adı "SEVK-1" gibi
     bir numaradır ve cins listesinde görünmemeli. */
  kur(m => (['blok', 'plaka', 'ebatli'].includes(m.baglanti_tip || '')
            ? String(m.baglanti_ad || '').trim().split(/[\\s·#]+/)[0] : '') || '',
      'mCins', 'Cins', M_CINS);
  kur(m => m.cari_unvan || m.cari_id || '', 'mCari', 'Cari', M_CARI);
}

function mSuzgecDegisti() {
  M_STOKTIP = (document.getElementById('mStokTip') || {}).value || '';
  M_CINS    = (document.getElementById('mCins')    || {}).value || '';
  M_CARI    = (document.getElementById('mCari')    || {}).value || '';
  ciz();
}

function mSuzgecleriSifirla() {
  M_STOKTIP = M_CINS = M_CARI = '';
  ciz();
}

function mSuzBilgiGuncelle(toplam, gosterilen) {
  const btn = document.getElementById('mSuzSifirla');
  const bilgi = document.getElementById('mSuzBilgi');
  const varMi = !!(M_STOKTIP || M_CINS || M_CARI);
  if (btn) btn.style.display = varMi ? '' : 'none';
  if (bilgi) {
    bilgi.textContent = varMi ? `${gosterilen} / ${toplam} kayıt` : '';
    bilgi.style.color = 'var(--verde)';
  }
}

function ciz() {"""

BLOKLAR = [
    ('data-t="KDV"', A_ESKI, A_YENI, 'KDV/Diğer sekmeleri + süzgeç kutuları'),
    ('.msuz{', B_ESKI, B_YENI, 'stil'),
    ('let M_STOKTIP', C_ESKI, C_YENI, 'süzgeç değişkenleri'),
    ('M_STOKTIP || (m.baglanti_tip', D_ESKI, D_YENI, 'süzme mantığı  [ASIL]'),
    ('function mSecenekleriDoldur(', E_ESKI, E_YENI, 'süzgeç JavaScript'),
]

print("═" * 70)
print(" M1 · MALİYETLER: SÜZGEÇLER VE EKSİK TÜRLER")
print("═" * 70)
print()

ham = ML.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


icerik = ham
plan, atlanan, sorunlu = [], [], []
for imza, eski, yeni, aciklama in BLOKLAR:
    if uyarla(imza) in icerik or imza in icerik:
        atlanan.append(aciklama)
        continue
    e = uyarla(eski)
    adet = icerik.count(e)
    if adet != 1:
        sorunlu.append((aciklama, adet))
        continue
    icerik = icerik.replace(e, uyarla(yeni), 1)
    plan.append(aciklama)

# mSuzBilgiGuncelle CAGRISI — tanimlidir ama cagrilmazsa
# "Suzgecleri temizle" dugmesi ve sayac ASLA gorunmez.
if 'mSuzBilgiGuncelle(TUM.length' not in icerik:
    _h = uyarla("  const g = document.getElementById('govde');")
    if icerik.count(_h) == 1:
        icerik = icerik.replace(
            _h,
            uyarla("  mSuzBilgiGuncelle(TUM.length, liste.length);   // M1\n") + _h, 1)
        plan.append('bilgi/temizle düğmesi bağlandı')
    else:
        print("  ⚠ mSuzBilgiGuncelle bağlanamadı — temizle düğmesi görünmez")

# Seçenek üretimi + bilgi çağrısını ciz() içine bağla
if 'mSecenekleriDoldur(TUM)' not in icerik:
    hedef = uyarla("  const s = ARA.toLocaleLowerCase('tr');")
    if icerik.count(hedef) == 1:
        icerik = icerik.replace(
            hedef,
            uyarla("  mSecenekleriDoldur(TUM);   // M1: seçenekleri tazele\n") + hedef, 1)
        plan.append('seçenekleri ciz() içinde tazele')
    else:
        print("  ⚠ Seçenek üretimi bağlanamadı — süzgeç kutuları BOŞ kalır")

for a in atlanan:
    print(f"  ↷ atlandı (zaten var)  {a}")
for a in plan:
    print(f"  ✓ uygulanacak          {a}")
for a, n in sorunlu:
    print(f"  ✗ KALIP BULUNAMADI     {a}  (eşleşme: {n})")

print()
if sorunlu:
    print(f" ✗ {len(sorunlu)} blok yerleştirilemedi — DOSYAYA DOKUNULMADI.")
    sys.exit(1)
if not plan:
    print(" ✓ Tüm bloklar zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

if not UYGULA:
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_m1_maliyet_suzgec.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = ML.with_name(f'maliyet.html.yedek-{damga}')
shutil.copy2(ML, yedek)
ML.write_bytes(icerik.encode('utf-8'))
print(f" ✓ templates/maliyet.html  (yedek: {yedek.name})")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print(" SONRA:  python js_denetim.py     → J2 ekseni de temiz olmalı")
print("═" * 70)

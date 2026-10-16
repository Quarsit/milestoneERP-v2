#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MF3B — GİRİŞTE FİRMA SEÇİMİ + "Yükleniyor…" HATASI
========================================================

ÖNKOŞUL: MF1, MF2, MF3 uygulanmış olmalı.

İKİ İŞ
------

1) HATA · Ayarlar → Firma'da "Firmalar" tablosu "Yükleniyor…"da
   takılı kalıyor ve "+ Yeni Firma" düğmesi hiç çıkmıyor.

   SEBEP: ayarlar.html sekme yükleyicilerini bir haritadan çağırıyor

       const yukleyici = { kullanici: kullaniciYukle,
                           firma: firmaYukle, ... }

   MF3 `firmaListesiYukle()` fonksiyonunu EKLEDİ ama bu haritaya
   BAĞLAMADI. Fonksiyon tanımlı, hiç çağrılmıyor; tablo ilk hâlinde
   kalıyor ve "+ Yeni Firma" düğmesi de o fonksiyon tarafından
   basıldığı için hiç görünmüyor.

   js_denetim bunu yakalayamaz: J2/J3 eksenleri "çağrılan fonksiyon
   TANIMLI MI" diye bakar, "tanımlı fonksiyon ÇAĞRILIYOR MU" diye
   değil.

2) TASARIM · Girişte firma seçimi.

   Şu anki akışta admin doğrudan varsayılan firmaya giriyor ve yeni
   firmayı MEVCUT firmanın ayarlarından açıyor. İki sorunu var:

   · Logo, Mikro, ETA, Netsis — Türkiye'de kullanılan muhasebe
     yazılımlarında girişte FİRMA SEÇİLİR. Beklenen davranış bu.

   · Daha somut: A firmasının ayarlarındayken B'yi ekliyorsun, ama
     hemen altındaki "Firma Bilgileri" formu hâlâ A'yı düzenliyor.
     Yeni firmanın unvanını oraya yazmak çok kolay — ve sessizce
     A'nın unvanı değişir.

   ÇÖZÜM: girişten sonra FİRMA SEÇİM EKRANI. Yeni firma da oradan
   açılır — artık bir firmanın içinden değil.

   TEK FİRMA VARSA EKRAN HİÇ GÖSTERİLMEZ. Bugünkü giriş akışı
   aynen kalır; ikinci firma açılınca devreye girer. Tek firmayla
   çalışan birine her girişte seçim ekranı göstermek, hiç
   kullanılmayan bir özellik için günlük sürtünme olurdu.

   Admin olmayan kullanıcı seçim ekranını GÖRMEZ — firma seçimi
   şimdilik admin yetkisinde; onlar varsayılan firmaya girer.

   Üst bardaki firma çipi duruyor: oturum ortasında geçiş için
   hâlâ en hızlı yol.

DOSYALAR
--------
  templates/firma_sec.html   (YENİ — seçim ekranı)
  templates/ayarlar.html     (yükleyici bağlanır)
  flask_app.py               (/firma-sec ucu + giriş yönlendirmesi)

KULLANIM
--------
  python3 yama_mf3b.py            # RAPOR
  python3 yama_mf3b.py --uygula
  sudo systemctl restart milestone-erp
"""

import os
import sys
import shutil
import py_compile
import tempfile

UYGULA = '--uygula' in sys.argv
KOK = os.path.dirname(os.path.abspath(__file__))

# IMZA dosyaya OZEL ve YAMANIN EKLEDIGI metne bakar.
# 'firmaListesiYukle();' denemesi YANILTTI: MF3 o cagriyi zaten
# firmaKaydet/firmaGec icine yazmisti, dosya "uygulanmis" sayildi.
DOSYA_IMZA = {
    'flask_app.py': 'def firma_sec_ekran',
    'templates/ayarlar.html': 'MF3B',
}
ONKOSUL = {
    'flask_app.py': 'api_firma_sec',            # MF3
    'templates/ayarlar.html': 'firmaListesiYukle',
}

YENI_DOSYA = 'templates/firma_sec.html'


# ══════════════════════════════════════════════════════════════════
#  flask_app.py
# ══════════════════════════════════════════════════════════════════

GIRIS_YONLENDIRME = '''                threading.Thread(target=yedek_modul.yedek_al, args=('auto',), daemon=True).start()
                # ── MF3B · GİRİŞTE FİRMA SEÇİMİ ──
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
                except Exception as _e:
                    app.logger.warning(f'[MF3B] firma secim ekrani atlandi: {_e}')
                return redirect(url_for('dashboard'))'''

FIRMA_SEC_UC = '''    @app.route('/firma-sec')
    def firma_sec_ekran():
        """Girişten sonra hangi firmada çalışılacağını seçtirir.

        Yeni firma da BURADAN açılır — bir firmanın ayarlarının
        içinden değil. Eski düzende A'nın ayarlarındayken B ekleniyor,
        hemen altındaki "Firma Bilgileri" formu ise hâlâ A'yı
        düzenliyordu; yeni firmanın unvanını oraya yazmak A'nın
        unvanını sessizce değiştirirdi.
        """
        if _auth_required():
            return _auth_required()
        # Firma seçimi şimdilik admin yetkisinde; diğerleri varsayılan
        # firmada çalışır ve bu ekranı hiç görmez.
        if (session.get('rol') or '').upper() != 'ADMIN':
            return redirect(url_for('dashboard'))
        with firma_atla():
            kayitlar = (Firma.query.filter_by(aktif=True)
                        .order_by(Firma.sira, Firma.id).all())
        # Tek firma varsa seçtirecek bir şey yok — doğrudan içeri.
        if len(kayitlar) <= 1:
            return redirect(url_for('dashboard'))
        return render_template('firma_sec.html', firmalar=[{
            'id': f.id, 'ad': f.ad, 'unvan': f.unvan or '',
            'kod': f.belge_kodu or '', 'vergi_no': f.vergi_no or '',
            'varsayilan': bool(f.varsayilan),
        } for f in kayitlar], secili=session.get('firma_id'))

    @app.route('/cikis')'''


# ══════════════════════════════════════════════════════════════════
#  templates/ayarlar.html
# ══════════════════════════════════════════════════════════════════

AYARLAR_YUKLEYICI = '''const yukleyici = { kullanici: kullaniciYukle,
                    // MF3B: "firma" sekmesi İKİ şey yükler — firma
                    // bilgisi formu ve FİRMALAR listesi. MF3'te
                    // firmaListesiYukle yazılmış ama buraya
                    // bağlanmamıştı: tablo "Yükleniyor…"da kalıyor,
                    // "+ Yeni Firma" düğmesi hiç basılmıyordu.
                    firma: () => { firmaYukle(); firmaListesiYukle(); },
                    listeler: lookupYukle,'''


# ══════════════════════════════════════════════════════════════════
#  templates/firma_sec.html  (YENİ)
# ══════════════════════════════════════════════════════════════════

FIRMA_SEC_HTML = '''<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Firma seç · Milestone</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800&family=Instrument+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --taban:#F6F6F3; --yuzey:#FFFFFF; --murekkep:#191C1A; --soluk:#68706C;
  --cizgi:#E5E5DF; --cizgi-koyu:#D6D6CE;
  --verde:#0C4F38; --verde-koyu:#093D2B; --verde-acik:#E3EFE8;
  --kirmizi:#B23A2E; --kirmizi-bg:#FAEAE7;
  --govde:'Instrument Sans',system-ui,sans-serif;
  --baslik:'Archivo',system-ui,sans-serif;
  --mono:ui-monospace,SFMono-Regular,Menlo,monospace;
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--govde);background:var(--taban);color:var(--murekkep);
  min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:32px 16px;-webkit-font-smoothing:antialiased}
:focus-visible{outline:2px solid var(--verde);outline-offset:2px}
.kutu{width:100%;max-width:560px}
.ust{display:flex;align-items:baseline;justify-content:space-between;
  gap:12px;margin-bottom:6px}
h1{font-family:var(--baslik);font-size:1.6rem;font-weight:800;letter-spacing:-.02em}
.cik{font-size:.86rem;color:var(--soluk);text-decoration:none}
.cik:hover{color:var(--kirmizi)}
.alt{color:var(--soluk);font-size:.9rem;margin-bottom:22px}
.firma{display:flex;align-items:center;gap:14px;width:100%;text-align:left;
  background:var(--yuzey);border:1px solid var(--cizgi);border-radius:12px;
  padding:16px 18px;margin-bottom:10px;cursor:pointer;
  font-family:inherit;font-size:1rem;color:var(--murekkep);
  transition:border-color .14s,box-shadow .14s}
.firma:hover{border-color:var(--verde);box-shadow:0 2px 10px rgba(12,79,56,.09)}
.firma:disabled{opacity:.55;cursor:wait}
.firma .simge{flex:0 0 38px;height:38px;border-radius:9px;background:var(--verde-acik);
  color:var(--verde);display:flex;align-items:center;justify-content:center}
.firma .govde{flex:1;min-width:0}
.firma .ad{font-weight:700;font-size:1rem;display:block}
.firma .not{color:var(--soluk);font-size:.8rem;display:block;margin-top:2px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.firma .kod{font-family:var(--mono);font-size:.75rem;color:var(--soluk);
  border:1px solid var(--cizgi);border-radius:6px;padding:2px 7px}
.rozet{font-size:.7rem;font-weight:700;letter-spacing:.03em;text-transform:uppercase;
  color:var(--verde);background:var(--verde-acik);border-radius:5px;padding:2px 7px}
.ayrac{display:flex;align-items:center;gap:12px;color:var(--soluk);
  font-size:.8rem;margin:22px 0 14px}
.ayrac::before,.ayrac::after{content:"";flex:1;height:1px;background:var(--cizgi)}
.ekle-btn{width:100%;background:transparent;border:1px dashed var(--cizgi-koyu);
  border-radius:12px;padding:14px;font-family:inherit;font-size:.92rem;
  font-weight:600;color:var(--soluk);cursor:pointer;transition:all .14s}
.ekle-btn:hover{border-color:var(--verde);color:var(--verde);background:var(--yuzey)}
.form{background:var(--yuzey);border:1px solid var(--cizgi);border-radius:12px;padding:18px}
.form h2{font-family:var(--baslik);font-size:1.05rem;margin-bottom:6px}
.form p{color:var(--soluk);font-size:.83rem;margin-bottom:14px;line-height:1.5}
.ikili{display:grid;grid-template-columns:1fr 110px;gap:12px}
.alan{margin-bottom:12px}
.alan label{display:block;font-size:.76rem;font-weight:600;letter-spacing:.04em;
  text-transform:uppercase;color:var(--soluk);margin-bottom:5px}
.alan input{width:100%;padding:10px 12px;border:1px solid var(--cizgi-koyu);
  border-radius:8px;font-family:inherit;font-size:.95rem;background:var(--taban);
  color:var(--murekkep)}
.alan input:focus{outline:0;border-color:var(--verde);background:var(--yuzey)}
.dugmeler{display:flex;gap:8px;margin-top:4px}
.bas{background:var(--verde);color:#fff;border:0;border-radius:8px;padding:11px 18px;
  font-family:inherit;font-size:.92rem;font-weight:600;cursor:pointer}
.bas:hover{background:var(--verde-koyu)}
.bas:disabled{opacity:.6;cursor:wait}
.vaz{background:transparent;color:var(--soluk);border:1px solid var(--cizgi-koyu);
  border-radius:8px;padding:11px 18px;font-family:inherit;font-size:.92rem;cursor:pointer}
.hata{background:var(--kirmizi-bg);color:var(--kirmizi);border-radius:8px;
  padding:10px 13px;font-size:.87rem;margin-bottom:12px}
.gizli{display:none}
@media (max-width:480px){.ikili{grid-template-columns:1fr}}
</style>
</head>
<body>
  <main class="kutu">
    <div class="ust">
      <h1>Firma seç</h1>
      <a class="cik" href="/cikis">Çıkış</a>
    </div>
    <p class="alt">Hangi firmada çalışacaksın? Her firmanın stoğu,
       siparişi, kasası ve defteri ayrıdır.</p>

    <div id="hata" class="hata gizli"></div>

    {% for f in firmalar %}
    <button class="firma" onclick="sec({{ f.id }}, this)">
      <span class="simge">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2"><path d="M3 21h18"/>
          <path d="M5 21V7l7-4 7 4v14"/><path d="M10 21v-6h4v6"/></svg>
      </span>
      <span class="govde">
        <span class="ad">{{ f.ad }}</span>
        <span class="not">{{ f.unvan or '—' }}{% if f.vergi_no %} · VKN {{ f.vergi_no }}{% endif %}</span>
      </span>
      {% if f.varsayilan %}<span class="rozet">varsayılan</span>{% endif %}
      <span class="kod">{{ f.kod or '—' }}</span>
    </button>
    {% endfor %}

    <div class="ayrac">ya da</div>
    <button class="ekle-btn" id="ekleBtn" onclick="formAc()">+ Yeni firma ekle</button>

    <div class="form gizli" id="form">
      <h2>Yeni firma</h2>
      <p><b>Belge kodu</b> zorunlu ve kısa olmalı (örn. K). Bu kod belge
         kimliklerinin köküne girer — <span style="font-family:var(--mono)">SIP-K-STN26-01</span>
         — ve her firmanın numarasının kendi başına ilerlemesini sağlar.
         Kodsuz iki firmanın numaraları çakışır.</p>
      <div class="ikili">
        <div class="alan"><label for="nAd">Firma adı *</label>
          <input id="nAd" placeholder="İkinci Mermer A.Ş."></div>
        <div class="alan"><label for="nKod">Belge kodu *</label>
          <input id="nKod" maxlength="4" placeholder="K" style="text-transform:uppercase"></div>
      </div>
      <div class="alan"><label for="nUnvan">Ticari ünvan</label>
        <input id="nUnvan" placeholder="Belgelerde görünen tam ünvan"></div>
      <div class="alan"><label for="nVno">Vergi no</label>
        <input id="nVno" placeholder="1234567890"></div>
      <div class="dugmeler">
        <button class="bas" id="kaydetBtn" onclick="kaydet()">Ekle ve bu firmaya geç</button>
        <button class="vaz" onclick="formKapat()">Vazgeç</button>
      </div>
    </div>
  </main>

<script>
function hataGoster(m) {
  const h = document.getElementById('hata');
  h.textContent = m; h.classList.remove('gizli');
}
function formAc() {
  document.getElementById('form').classList.remove('gizli');
  document.getElementById('ekleBtn').classList.add('gizli');
  document.getElementById('nAd').focus();
}
function formKapat() {
  document.getElementById('form').classList.add('gizli');
  document.getElementById('ekleBtn').classList.remove('gizli');
  document.getElementById('hata').classList.add('gizli');
}

async function gonder(yol, govde) {
  const y = await fetch(yol, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(govde)
  });
  return y.json();
}

async function sec(id, btn) {
  if (btn) { btn.disabled = true; }
  try {
    const d = await gonder('/api/firma/sec', { firma_id: id });
    if (d && d.ok) { location.href = '/dashboard'; return; }
    hataGoster((d && d.mesaj) || 'Firma seçilemedi');
  } catch (e) { hataGoster('Firma seçilemedi'); }
  if (btn) { btn.disabled = false; }
}

async function kaydet() {
  const ad = (document.getElementById('nAd').value || '').trim();
  const kod = (document.getElementById('nKod').value || '').trim().toUpperCase();
  if (!ad) { hataGoster('Firma adı gir.'); return; }
  if (!kod) { hataGoster('Belge kodu gir — yoksa belge numaraları çakışır.'); return; }
  const b = document.getElementById('kaydetBtn');
  b.disabled = true; b.textContent = 'Ekleniyor…';
  try {
    const d = await gonder('/api/firma', {
      ad: ad, belge_kodu: kod,
      unvan: (document.getElementById('nUnvan').value || '').trim(),
      vergi_no: (document.getElementById('nVno').value || '').trim()
    });
    if (d && d.ok && d.id) {
      /* Eklenen firmaya DOĞRUDAN geçilir: yeni firmanın unvanını,
         adresini ve logosunu girecek olan kişi zaten o firmada
         olmalı. Eski düzende A'nın ayarlarında kalıp B'nin bilgisi
         sanarak A'yı düzenlemek çok kolaydı. */
      await sec(d.id, null);
      return;
    }
    hataGoster((d && d.mesaj) || 'Firma eklenemedi');
  } catch (e) { hataGoster('Firma eklenemedi'); }
  b.disabled = false; b.textContent = 'Ekle ve bu firmaya geç';
}
</script>
</body>
</html>
'''


def degisiklikler():
    return [
        ('flask_app.py', 'MF3B-a · giriste firma secim yonlendirmesi',
         """                threading.Thread(target=yedek_modul.yedek_al, args=('auto',), daemon=True).start()
                return redirect(url_for('dashboard'))""",
         GIRIS_YONLENDIRME),
        ('flask_app.py', 'MF3B-b · /firma-sec ucu',
         "    @app.route('/cikis')", FIRMA_SEC_UC),
        ('templates/ayarlar.html', 'MF3B-c · firma sekmesi listeyi de yukler',
         "const yukleyici = { kullanici: kullaniciYukle, firma: firmaYukle, listeler: lookupYukle,",
         AYARLAR_YUKLEYICI),
    ]


def main():
    print('=' * 70)
    print('  YAMA MF3B — GİRİŞTE FİRMA SEÇİMİ + "Yükleniyor…" HATASI')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    gruplar = {}
    for dosya, aciklama, eski, yerine in degisiklikler():
        gruplar.setdefault(dosya, []).append((aciklama, eski, yerine))

    sonuclar, hata, zaten = {}, False, []
    for dosya, isler in gruplar.items():
        yol = os.path.join(KOK, dosya)
        print(f'\n── {dosya} ' + '─' * max(0, 54 - len(dosya)))
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
            print(f'  ✗ ÖNKOŞUL YOK: "{onk}" yok — önce MF3 uygulanmalı')
            hata = True
            continue
        if DOSYA_IMZA[dosya] in icerik:
            print(f'  ⊙ İmza zaten var — ATLANIR')
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

    # ── yeni sablon ──
    yeni_yol = os.path.join(KOK, YENI_DOSYA)
    print(f'\n── {YENI_DOSYA} (YENİ) ' + '─' * 32)
    if os.path.exists(yeni_yol):
        print('  ⊙ dosya zaten var — ATLANIR')
        zaten.append(YENI_DOSYA)
    else:
        print('  ✓ oluşturulacak — firma seçim ekranı')

    print('\n' + '=' * 70)
    if hata:
        print('  ✗ HATA VAR → Hiçbir dosyaya DOKUNULMADI')
        return 1
    if zaten and sonuclar:
        print('  ✗ YARIM DURUM → Hiçbir dosyaya DOKUNULMADI')
        print(f'    imzası olan: {", ".join(zaten)}')
        return 1
    if zaten:
        print('  ⊙ Yama MF3B zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_mf3b.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        yedek = yol + '.yedek_mf3b'
        shutil.copy2(yol, yedek)
        with open(yol, 'w', encoding='utf-8', newline='') as f:
            f.write(icerik)
        print(f'  ✓ yazıldı: {os.path.relpath(yol, KOK)}')
        print(f'    yedek  : {os.path.relpath(yedek, KOK)}')
    with open(yeni_yol, 'w', encoding='utf-8', newline='\n') as f:
        f.write(FIRMA_SEC_HTML)
    print(f'  ✓ oluşturuldu: {YENI_DOSYA}')

    print('\n  ✓ YAMA UYGULANDI')
    print()
    print('  Şema değişmedi — göç GEREKMİYOR.')
    print()
    print('    sudo systemctl restart milestone-erp')
    print('    venv/bin/python js_denetim.py')
    print()
    print('  TEK firma varken giriş akışı DEĞİŞMEZ — seçim ekranı')
    print('  yalnızca iki ve daha çok firma varken çıkar.')
    print('  İlk ikinci firmayı Ayarlar → Firma → + Yeni Firma ile aç;')
    print('  sonraki girişte seçim ekranı kendiliğinden gelir.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MF4 — FİRMA SİLME + YEDEK LİSTESİ HATASI
==============================================

ÖNKOŞUL: MF3C uygulanmış olmalı.

ÜÇ İŞ
-----

1) HATA · "Yedekler" listesi hep "Yükleniyor…"da kalıyor
   Diskte 30 yedek var, tanı kutusu da `yedek_sayisi: 30` diyor ama
   tablo boş.

   SEBEP: ayarlar.html'de "Yedekler" paneli İKİ KEZ var — biri
   E-posta sekmesinin sonunda (eski bir düzenlemeden kalmış), biri
   Yedekleme sekmesinde. İkisinin de id'si `yedekGovde`.
   `getElementById` İLKİNİ döndürüyor; JS e-posta sekmesindeki
   GÖRÜNMEYEN kopyayı dolduruyor, ekrandaki tablo ilk hâlinde
   kalıyor.

   Bu MF yamalarından önce de vardı. E-posta sekmesindeki fazla
   panel kaldırılıyor.

   js_denetim'e J7 ekseni eklendi: aynı id'nin bir şablonda iki kez
   geçmesi. Bu hata sessiz — hiçbir şey patlamıyor, yalnızca yanlış
   öğe doluyor.

2) FİRMA SİLME
   · Firmada HİÇ kayıt yoksa doğrudan silinir.
   · Kayıt VARSA önce tam veritabanı yedeği alınır, sonra silinir.
     Yedek alınamazsa silme İPTAL edilir — kurtarılamayacak bir
     silme yapılmaz.
   · Yedek `firma_silme` tipiyle etiketlenir ve otomatik temizliğe
     TAKILMAZ. Normal yedekler 30 taneyi geçince en eskisi siliniyor;
     bir firmanın tek kurtarma noktası öyle sessizce kaybolmamalı.

   SİLİNEMEYENLER:
     · içinde bulunduğun firma   (ayağının altındaki halı)
     · varsayılan firma          (admin olmayanlar oraya düşüyor)
     · son kalan firma           (firmasız sistem kayıt yazamaz)

   Silme ekranı GİRİŞTEKİ firma seçim ekranında — bir firmanın
   içinden değil. Zaten içinde bulunduğun firmayı silemezsin.

   AUDIT LOG SİLİNMEZ: o satırların `firma_id`'si NULL'lanır.
   Denetim izi silinen firmanın da ne yapıldığını göstermeli.

   ARTIK CARİLER: yalnızca silinen firmada görünen bir cari artık
   hiçbir yerde görünmez. Başka hiçbir kaydı kalmamışsa kart da
   silinir; kaydı varsa DOKUNULMAZ ve raporlanır. Veri sessizce yok
   edilmez.

3) Yedek listesinde `firma_silme` tipi görünür (kehribar rozet).

DOSYALAR
--------
  templates/ayarlar.html    (mükerrer panel kalkar + tip etiketi)
  yedek.py                  (firma_silme tipi korunur ve tanınır)
  flask_app.py              (özet + silme uçları)
  templates/firma_sec.html  (sil düğmesi ve onay akışı)
  js_denetim.py             (J7 · mükerrer element id)

KULLANIM
--------
  python3 yama_mf4.py            # RAPOR
  python3 yama_mf4.py --uygula
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
    'templates/ayarlar.html': 'firma_silme',
    'yedek.py': 'firma_silme',
    'flask_app.py': 'api_firma_sil',
    'templates/firma_sec.html': 'firmaSil',
    'js_denetim.py': 'J7',
}
ONKOSUL = {
    'flask_app.py': 'api_firma_sec',
    'templates/firma_sec.html': 'const CSRF',
    'templates/ayarlar.html': None,
    'yedek.py': None,
    'js_denetim.py': None,
}


# ══════════════════════════════════════════════════════════════════
#  flask_app.py — özet ve silme uçları
# ══════════════════════════════════════════════════════════════════

SILME_UC = '''    def _firma_kayit_sayim(fid):
        """Firmaya bağlı kayıtları tablo tablo sayar.

        HAM SQL: süzgeç zaten aktif firmaya bakıyor, biz BAŞKA bir
        firmayı sayıyoruz. ORM ile sorgulamak yanlış firmayı sayardı.
        """
        sayim, toplam = {}, 0
        with db.engine.connect() as _b:
            for _t in db.metadata.sorted_tables:
                if 'firma_id' not in _t.c:
                    continue
                if _t.name in ('firma', 'audit_log', 'veriler'):
                    continue            # aşağıda ayrı ele alınıyor
                _n = _b.execute(sa_text(
                    f'SELECT COUNT(*) FROM "{_t.name}" WHERE firma_id = :f'),
                    {'f': fid}).scalar() or 0
                if _n:
                    sayim[_t.name] = _n
                    toplam += _n
            _c = _b.execute(sa_text(
                'SELECT COUNT(*) FROM cari_firma WHERE firma_id = :f'),
                {'f': fid}).scalar() or 0
        return sayim, toplam, _c

    @app.route('/api/firma/<int:fid>/ozet', methods=['GET'])
    def api_firma_ozet(fid):
        """Silmeden önce: bu firmada ne var, silinebilir mi?"""
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if (session.get('rol') or '').upper() != 'ADMIN':
            return jsonify({'ok': False, 'mesaj': 'Yalnızca admin'}), 403
        with firma_atla():
            f = db.session.get(Firma, fid)
            _toplam_firma = Firma.query.count()
        if not f:
            return jsonify({'ok': False, 'mesaj': 'Firma bulunamadı'}), 404
        sayim, toplam, cari_n = _firma_kayit_sayim(fid)
        engel = None
        if f.id == aktif_firma_id():
            engel = 'İçinde bulunduğun firmayı silemezsin. Önce başka bir firmaya geç.'
        elif f.varsayilan:
            engel = 'Varsayılan firma silinemez. Önce başka bir firmayı varsayılan yap.'
        elif _toplam_firma <= 1:
            engel = 'Son firma silinemez — firmasız sistem kayıt yazamaz.'
        return jsonify({'ok': True, 'id': f.id, 'ad': f.ad,
                        'belge_kodu': f.belge_kodu or '',
                        'kayit_sayisi': toplam, 'cari_baglantisi': cari_n,
                        'dagilim': sayim, 'engel': engel,
                        'silinebilir': engel is None})

    @app.route('/api/firma/<int:fid>', methods=['DELETE'])
    def api_firma_sil(fid):
        """Firmayı ve ona bağlı HER ŞEYİ siler.

        Kayıt varsa ÖNCE tam veritabanı yedeği alınır. Yedek
        alınamazsa silme İPTAL edilir: kurtarılamayacak bir silme
        yapmaktansa hiç yapmamak doğrudur.
        """
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if (session.get('rol') or '').upper() != 'ADMIN':
            return jsonify({'ok': False, 'mesaj':
                            'Firma silmek yalnızca admin yetkisindedir'}), 403
        with firma_atla():
            f = db.session.get(Firma, fid)
            _toplam_firma = Firma.query.count()
        if not f:
            return jsonify({'ok': False, 'mesaj': 'Firma bulunamadı'}), 404
        if f.id == aktif_firma_id():
            return jsonify({'ok': False, 'mesaj':
                            'İçinde bulunduğun firmayı silemezsin. '
                            'Önce başka bir firmaya geç.'}), 400
        if f.varsayilan:
            return jsonify({'ok': False, 'mesaj':
                            'Varsayılan firma silinemez.'}), 400
        if _toplam_firma <= 1:
            return jsonify({'ok': False, 'mesaj':
                            'Son firma silinemez.'}), 400

        _ad = f.ad
        sayim, toplam, _ = _firma_kayit_sayim(fid)

        # ── YEDEK ──
        # Kayıt varsa zorunlu. `firma_silme` tipi otomatik temizliğe
        # takılmaz (yedek.py): normal yedekler 30'u geçince en eski
        # silinir, bir firmanın TEK kurtarma noktası öyle kaybolmamalı.
        yedek_dosya = None
        if toplam > 0:
            try:
                yol = yedek_modul.yedek_al('firma_silme')
            except Exception as _e:
                app.logger.exception('[MF4] firma silme yedegi alinamadi')
                yol = None
            if not yol:
                return jsonify({'ok': False, 'mesaj':
                                'Yedek ALINAMADI — silme iptal edildi. '
                                'Kurtarılamayacak bir silme yapmıyorum. '
                                'Ayarlar → Yedekleme bölümündeki tanıya bak.'}), 500
            yedek_dosya = os.path.basename(str(yol))

        # ── SİLME (tek transaction) ──
        try:
            with db.engine.begin() as _b:
                # Çocuk tablo önce: metadata topolojik sıralı, tersi
                # silme sırası. Elle sıralamak her yeni yabancı
                # anahtarda kırılırdı (sifirla2'de ölçülmüştü).
                for _t in reversed(db.metadata.sorted_tables):
                    if 'firma_id' not in _t.c or _t.name in ('firma', 'audit_log'):
                        continue
                    _b.execute(sa_text(
                        f'DELETE FROM "{_t.name}" WHERE firma_id = :f'), {'f': fid})
                _b.execute(sa_text(
                    'DELETE FROM cari_firma WHERE firma_id = :f'), {'f': fid})
                # Denetim izi SİLİNMEZ — silinen firmada ne yapıldığı
                # da görünebilmeli. Yalnızca bağ koparılır.
                _b.execute(sa_text(
                    'UPDATE audit_log SET firma_id = NULL WHERE firma_id = :f'),
                    {'f': fid})
                _b.execute(sa_text('DELETE FROM firma WHERE id = :f'), {'f': fid})
        except Exception as _e:
            app.logger.exception('[MF4] firma silinemedi')
            return jsonify({'ok': False, 'mesaj': f'Silinemedi: {_e}'}), 500

        # ── ARTIK CARİLER ──
        # Üyeliği kalmayan cari hiçbir firmada görünmez. Başka hiçbir
        # kaydı yoksa kart da gider; kaydı varsa DOKUNULMAZ ve
        # raporlanır — veri sessizce yok edilmez.
        silinen_cari, kalan_artik = 0, 0
        try:
            _izli = ('cari_hareket', 'faturalar', 'siparis_kayit', 'proforma',
                     'cek', 'rezervasyon', 'satis_kaydi', 'cari_aktivite')
            with db.engine.begin() as _b:
                _artik = [r[0] for r in _b.execute(sa_text(
                    'SELECT c.id FROM cariler c WHERE NOT EXISTS '
                    '(SELECT 1 FROM cari_firma cf WHERE cf.cari_id = c.id)'
                )).fetchall()]
                for _cid in _artik:
                    _var = False
                    for _tn in _izli:
                        if _b.execute(sa_text(
                            f'SELECT 1 FROM "{_tn}" WHERE cari_id = :c LIMIT 1'),
                                {'c': _cid}).fetchone():
                            _var = True
                            break
                    if _var:
                        kalan_artik += 1
                        continue
                    _b.execute(sa_text(
                        'DELETE FROM cari_kisi WHERE cari_id = :c'), {'c': _cid})
                    _b.execute(sa_text(
                        'DELETE FROM cari_erisim WHERE cari_id = :c'), {'c': _cid})
                    _b.execute(sa_text(
                        'DELETE FROM cariler WHERE id = :c'), {'c': _cid})
                    silinen_cari += 1
        except Exception as _e:
            app.logger.warning(f'[MF4] artik cari temizligi atlandi: {_e}')

        # Onbellekler: silinen firma varsayilan degildi ama models
        # tarafindaki onbellek yine de tazelensin — firma tablosu
        # degisti. MF2'nin ice aktarim satirinda bu ad YOKTU,
        # NameError veriyordu (olculdu).
        from models import varsayilan_firma_unut as _vfu
        _vfu()
        _firma_onbellek_dusur()
        _log_audit('SIL', 'firma', fid,
                   eski={'ad': _ad, 'kayit': toplam, 'yedek': yedek_dosya})
        db.session.commit()

        _m = f'{_ad} silindi'
        if toplam:
            _m += f' · {toplam:,} kayıt'
        if silinen_cari:
            _m += f' · {silinen_cari} artık cari kaldırıldı'
        if kalan_artik:
            _m += f' · {kalan_artik} cari kaydı olduğu için BIRAKILDI'
        if yedek_dosya:
            _m += f' · yedek: {yedek_dosya}'
        return jsonify({'ok': True, 'mesaj': _m, 'yedek': yedek_dosya,
                        'silinen_kayit': toplam, 'silinen_cari': silinen_cari,
                        'kalan_artik_cari': kalan_artik})

    @app.route('/api/firma/sec', methods=['POST'])'''


# ══════════════════════════════════════════════════════════════════
#  templates/firma_sec.html — sil düğmesi
# ══════════════════════════════════════════════════════════════════

SEC_MARKUP = '''      {% if f.varsayilan %}<span class="rozet">varsayılan</span>{% endif %}'''

SEC_SIL_JS = '''let SIL_HEDEF = null;

function silKapat() {
  document.getElementById('silOrtu').classList.add('gizli');
  SIL_HEDEF = null;
}

async function firmaSil(id, ad, e) {
  /* Düğme kartın İÇİNDE: tıklama kartın onclick'ine de giderdi ve
     silinecek firmaya GEÇİLİRDİ. */
  if (e) { e.stopPropagation(); e.preventDefault(); }
  document.getElementById('hata').classList.add('gizli');
  let o;
  try {
    const y = await fetch('/api/firma/' + id + '/ozet');
    o = await y.json();
  } catch (err) { hataGoster('Firma bilgisi okunamadı'); return; }
  if (!o || !o.ok) { hataGoster((o && o.mesaj) || 'Firma bilgisi okunamadı'); return; }
  if (o.engel) { hataGoster(o.engel); return; }

  SIL_HEDEF = id;
  document.getElementById('silAd').textContent = ad;
  const g = document.getElementById('silGovde');
  if (o.kayit_sayisi > 0) {
    const d = Object.entries(o.dagilim || {})
      .sort((a, b) => b[1] - a[1])
      .map(([t, n]) => `<tr><td>${t}</td><td class="s">${n.toLocaleString('tr-TR')}</td></tr>`)
      .join('');
    g.innerHTML = `
      <p>Bu firmada <b>${o.kayit_sayisi.toLocaleString('tr-TR')}</b> kayıt var:</p>
      <div class="dokum"><table>${d}</table></div>
      <p class="iyi">Silmeden önce <b>tam veritabanı yedeği</b> alınacak.
         Yanlışlıkla silersen Ayarlar → Yedekleme'den o yedeğe
         dönebilirsin. Yedek alınamazsa silme yapılmaz.</p>`;
  } else {
    g.innerHTML = '<p>Bu firmada hiç kayıt yok. Doğrudan silinecek.</p>';
  }
  document.getElementById('silOrtu').classList.remove('gizli');
}

async function silOnayla() {
  if (!SIL_HEDEF) return;
  const b = document.getElementById('silBtn');
  b.disabled = true; b.textContent = 'Siliniyor…';
  try {
    const y = await fetch('/api/firma/' + SIL_HEDEF, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': CSRF }
    });
    const d = await y.json();
    if (d && d.ok) { location.reload(); return; }
    silKapat(); hataGoster((d && d.mesaj) || 'Silinemedi');
  } catch (err) { silKapat(); hataGoster('Silinemedi'); }
  b.disabled = false; b.textContent = 'Yedekle ve sil';
}

async function sec(id, btn) {'''


def degisiklikler():
    return [
        # ── 1 · mükerrer "Yedekler" paneli ──
        ('templates/ayarlar.html', 'MF4-a · E-postadaki MUKERRER Yedekler paneli kalkar',
         """  <div class="panel" style="margin-top:14px">
    <h4>Yedekler <span id="yedekAdet" style="color:var(--soluk);font-weight:400"></span></h4>
    <div class="tablo-kutu" style="border:0">
      <table>
        <thead><tr><th>Dosya</th><th>Tip</th><th>Tarih</th><th class="sag">Boyut</th><th class="sag" style="width:230px"></th></tr></thead>
        <tbody id="yedekGovde"><tr><td colspan="5" class="yukleniyor">Yükleniyor…</td></tr></tbody>
      </table>
    </div>
  </div>
</section>

<section class="bolum" id="b-listeler">""",
         """  <!-- MF4: BURADA bir "Yedekler" paneli DAHA vardı — Yedekleme
       sekmesindekiyle AYNI id'leri taşıyordu (yedekGovde, yedekAdet).
       getElementById İLKİNİ döndürdüğü için JS bu GÖRÜNMEYEN kopyayı
       dolduruyor, Yedekleme sekmesindeki tablo "Yükleniyor…"da
       kalıyordu. Diskte 30 yedek varken liste boş görünmesinin
       sebebi buydu. Panelin yeri Yedekleme sekmesi; burada işi yok. -->
</section>

<section class="bolum" id="b-listeler">"""),
        ('templates/ayarlar.html', 'MF4-b · firma_silme yedek tipi etiketi',
         "const YTIP = { auto: 'Otomatik', manual: 'Elle', pre_restore: 'Geri yükleme öncesi' };\n"
         "const YRZ  = { auto: 'rz-gri', manual: 'rz-yesil', pre_restore: 'rz-kehribar' };",
         "const YTIP = { auto: 'Otomatik', manual: 'Elle',\n"
         "               pre_restore: 'Geri yükleme öncesi',\n"
         "               // MF4: firma silinmeden önce alınır, otomatik\n"
         "               // temizliğe TAKILMAZ — tek kurtarma noktası.\n"
         "               firma_silme: 'Firma silme öncesi' };\n"
         "const YRZ  = { auto: 'rz-gri', manual: 'rz-yesil',\n"
         "               pre_restore: 'rz-kehribar', firma_silme: 'rz-kehribar' };"),
        # ── 2 · yedek.py ──
        ('yedek.py', 'MF4-c · firma_silme yedegi temizlige TAKILMAZ',
         """        [p for p in BACKUP_DIR.glob(f'milestone_*{YEDEK_UZANTI}')
         if '_pre_restore_' not in p.name],""",
         """        # MF4: `firma_silme` de korunur. Bir firma silinmeden
        # once alinan yedek, o firmanin TEK kurtarma noktasi;
        # 30 yedek siniri yuzunden sessizce silinmemeli.
        [p for p in BACKUP_DIR.glob(f'milestone_*{YEDEK_UZANTI}')
         if '_pre_restore_' not in p.name
         and '_firma_silme_' not in p.name],"""),
        ('yedek.py', 'MF4-d · firma_silme tipi listede taninir',
         """        elif '_pre_restore_' in p.name:
            tip = 'pre_restore'""",
         """        elif '_pre_restore_' in p.name:
            tip = 'pre_restore'
        elif '_firma_silme_' in p.name:
            tip = 'firma_silme'"""),
        # ── 3 · flask_app.py ──
        ('flask_app.py', 'MF4-e · firma ozet ve silme uclari',
         "    @app.route('/api/firma/sec', methods=['POST'])", SILME_UC),
        # ── 4 · firma_sec.html ──
        ('templates/firma_sec.html', 'MF4-f · kartta sil dugmesi',
         SEC_MARKUP,
         SEC_MARKUP + """
      {% if not f.varsayilan %}
      <span class="sil" role="button" tabindex="0" title="Firmayı sil"
            onclick="firmaSil({{ f.id }}, '{{ f.ad|replace("'", "\\\\'") }}', event)">Sil</span>
      {% endif %}"""),
        ('templates/firma_sec.html', 'MF4-g · sil bicemi ve onay penceresi',
         ".gizli{display:none}",
         """.gizli{display:none}
/* Sil — kartın içinde ama kartın tıklamasını YUTAR (firmaSil'de
   stopPropagation); yoksa silinecek firmaya geçilirdi. */
.sil{font-size:.78rem;font-weight:600;color:var(--soluk);border:1px solid var(--cizgi);
  border-radius:6px;padding:3px 9px;cursor:pointer;transition:all .14s}
.sil:hover{color:var(--kirmizi);border-color:var(--kirmizi);background:var(--kirmizi-bg)}

/* ── ONAY PENCERESİ ──
   Tarayıcının confirm/alert'i KULLANILMIYOR: js_denetim J4 ekseni
   bunları "sessiz hayır" sayıyor — tarayıcı engelleyebiliyor ve
   dökümü düzgün gösteremiyor. Bu sayfa bağımsız olduğu için
   base.html'deki onayla() de yok; penceresi kendi içinde. */
.ortu{position:fixed;inset:0;background:rgba(25,28,26,.45);display:flex;
  align-items:center;justify-content:center;padding:20px;z-index:80}
.ortu.gizli{display:none}
.pencere{background:var(--yuzey);border-radius:14px;max-width:460px;width:100%;
  box-shadow:0 24px 60px rgba(25,28,26,.3);overflow:hidden}
.pencere .bas{padding:18px 20px 12px}
.pencere .bas h2{font-family:var(--baslik);font-size:1.1rem;margin-bottom:4px}
.pencere .bas .hedef{color:var(--kirmizi);font-weight:700}
.pencere .gov{padding:0 20px 4px;font-size:.88rem;line-height:1.55;color:var(--murekkep)}
.pencere .gov p{margin-bottom:10px}
.pencere .gov .iyi{color:var(--soluk);font-size:.83rem}
.dokum{max-height:190px;overflow:auto;border:1px solid var(--cizgi);
  border-radius:8px;margin-bottom:10px}
.dokum table{width:100%;border-collapse:collapse;font-size:.83rem}
.dokum td{padding:5px 11px;border-bottom:1px solid var(--cizgi)}
.dokum tr:last-child td{border-bottom:0}
.dokum td.s{text-align:right;font-family:var(--mono);color:var(--soluk)}
.pencere .ayak{display:flex;gap:8px;justify-content:flex-end;
  padding:14px 20px 18px}
.teh{background:var(--kirmizi);color:#fff;border:0;border-radius:8px;
  padding:10px 17px;font-family:inherit;font-size:.9rem;font-weight:600;cursor:pointer}
.teh:hover{filter:brightness(.92)}
.teh:disabled{opacity:.6;cursor:wait}"""),
        ('templates/firma_sec.html', 'MF4-j · onay penceresi isaretlemesi',
         "  </main>\n\n<script>",
         """  </main>

  <div class="ortu gizli" id="silOrtu" onclick="if(event.target===this)silKapat()">
    <div class="pencere" role="dialog" aria-label="Firma sil">
      <div class="bas">
        <h2>Firmayı sil</h2>
        <div class="hedef" id="silAd"></div>
      </div>
      <div class="gov" id="silGovde"></div>
      <div class="ayak">
        <button class="vaz" onclick="silKapat()">Vazgeç</button>
        <button class="teh" id="silBtn" onclick="silOnayla()">Yedekle ve sil</button>
      </div>
    </div>
  </div>

<script>"""),
        ('templates/firma_sec.html', 'MF4-h · silme akisi',
         "async function sec(id, btn) {", SEC_SIL_JS),
        # ── 5 · js_denetim J7 ──
        ('js_denetim.py', 'MF4-i · J7 · mukerrer element id ekseni',
         """print()
print("═" * 70)
if bulgu:""",
         'print()\nprint("─" * 70)\nprint(" J7 · AYNI id İKİ KEZ   [YANLIŞ ÖĞE DOLAR, HATA VERMEZ]")\nprint("─" * 70)\n# getElementById İLKİNİ döndürür. İki panel aynı id\'yi taşıyorsa JS\n# görünmeyen kopyayı doldurur, ekrandaki hiç değişmez. Hiçbir şey\n# patlamaz, konsola hata da düşmez — tam bu yüzden aylarca durur.\n#\n# ÖLÇÜLDÜ (16.10): ayarlar.html\'de "Yedekler" paneli İKİ kez vardı\n# (e-posta ve yedekleme sekmelerinde), ikisi de `yedekGovde`. Diskte\n# 30 yedek varken liste "Yükleniyor…"da kalıyordu.\n_j7 = 0\nfor p7 in sorted(SABLON.glob(\'*.html\')):\n    ham7 = p7.read_text(encoding=\'utf-8\', errors=\'replace\')\n    gorulen, tekrar = set(), {}\n    for m7 in re.finditer(r\'\\\\sid="([^"]+)"\', ham7):\n        ad7 = m7.group(1)\n        if \'{{\' in ad7 or \'{%\' in ad7 or \'${\' in ad7:\n            continue            # şablon/JS ifadesi — üretimde farklı olur\n        if ad7 in gorulen:\n            tekrar[ad7] = tekrar.get(ad7, 1) + 1\n        gorulen.add(ad7)\n    if tekrar:\n        _j7 += len(tekrar)\n        print(f"   ✗ {p7.name}: " + \', \'.join(\n            f\'id="{a}" ({n}×)\' for a, n in sorted(tekrar.items())))\nif _j7:\n    print()\n    print("   → Bir id bir sayfada TEK olmalı. Fazla olanı kaldırın ya da")\n    print("     ayırt edici bir ad verin; JS şu an yanlış öğeyi dolduruyor.")\n    bulgu += _j7\nelse:\n    print("   ✓ temiz — her element id\'si şablonunda bir kez geçiyor")\n\nprint()\nprint("═" * 70)\nif bulgu:'),
    ]


def main():
    print('=' * 70)
    print('  YAMA MF4 — FİRMA SİLME + YEDEK LİSTESİ HATASI')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    gruplar = {}
    for dosya, aciklama, eski, yerine in degisiklikler():
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
            print(f'  ✗ ÖNKOŞUL YOK: "{onk}" yok — önce MF3C uygulanmalı')
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
        print('  ⊙ Yama MF4 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_mf4.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        yedek = yol + '.yedek_mf4'
        shutil.copy2(yol, yedek)
        with open(yol, 'w', encoding='utf-8', newline='') as f:
            f.write(icerik)
        print(f'  ✓ yazıldı: {os.path.relpath(yol, KOK)}')
        print(f'    yedek  : {os.path.relpath(yedek, KOK)}')

    print('\n  ✓ YAMA UYGULANDI')
    print()
    print('  Şema değişmedi — göç GEREKMİYOR.')
    print()
    print('    sudo systemctl restart milestone-erp')
    print('    venv/bin/python js_denetim.py     # J7 ekseni de koşar')
    print()
    print('  Firma silme: çıkış yap, giriş ekranındaki firma listesinde')
    print('  silmek istediğin firmanın yanındaki "Sil"e bas. İçinde')
    print('  bulunduğun firma ve varsayılan firma silinemez.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

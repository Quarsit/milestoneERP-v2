#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MF3 — ÇOKLU FİRMA, 3/4: FİRMA SEÇİCİ VE YÖNETİMİ
======================================================

ÖNKOŞUL: MF1 ve MF2 uygulanmış olmalı.

    MF1  şema + yazarken damga        ✓
    MF2  okuma süzgeci                ✓
    MF3  arayüz + belge kodlu kimlik  ← buradasın
    MF4  sıfırlama modları + testler

GÖRÜNÜR KISIM BU. Bu yamadan sonra ikinci firma açabilir ve aralarında
geçiş yapabilirsin.

NE GELİYOR
----------
1) BANNER'DA FİRMA ÇİPİ
   Birden fazla firma varsa üst barda görünür. Admin tıklayıp firma
   değiştirir; admin olmayan yalnızca hangi firmada olduğunu görür
   (seçim admin yetkisinde — senin kararın).
   TEK firma varken çip HİÇ görünmez: bugünkü ekran aynen kalır.

2) AYARLAR → FİRMA sekmesinde "Firmalar" paneli
   Firmaları listeler, yeni firma açar. Bir firmanın unvanı, adresi,
   logosu aynı sekmedeki mevcut formdan düzenlenir — o form artık
   AKTİF FİRMAYI düzenliyor (MF2'den beri ayar satırları firma
   bazlı). İkinci firmanın bilgilerini girmek için önce ona geç.

3) BELGE KODLU KİMLİKLER
   `firma.belge_kodu` kimliğin köküne girer:
       ana firma   SIP-STN26-03     (kod boş — eski kimlikler korunur)
       ikinci firma SIP-K-STN26-01  (kendi sayacı, 01'den)
   Kök farklı olduğu için `LIKE` taraması da ayrışır; her firmanın
   sayacı kendi başına ilerler. İstediğin "her firma kendi belge
   numarasını tutsun" tam olarak bu.

   YENİ FİRMA KOD ALMAK ZORUNDA. Kodsuz ikinci firma ana firmayla
   AYNI kökü üretir, kimlik birincil anahtar olduğu için numaralar
   çakışır ve sayaç ikisini birden sayar. Sunucu kodsuz firma
   oluşturmayı reddeder.

GÜVENLİK
--------
  · Firma oluşturma ve geçiş YALNIZCA admin.
  · Geçişte firma kimliği doğrulanır (var mı, aktif mi).
  · Geçişte istek içi önbellekler düşürülür; yoksa aynı istekte
    eski firmanın süzgeci sürerdi.
  · Belge kodu benzersiz; büyük harfe çevrilir, en çok 4 karakter.

DOSYALAR
--------
  flask_app.py          (kimlik üreteci, bağlam, 3 API ucu, yetki)
  templates/base.html   (banner çipi + biçem)
  templates/ayarlar.html (Firmalar paneli)

KULLANIM
--------
  python3 yama_mf3.py            # RAPOR
  python3 yama_mf3.py --uygula
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
    'flask_app.py': '_firma_belge_kodu',
    'templates/base.html': 'firmaMenuAc',
    'templates/ayarlar.html': 'firmaListesiYukle',
}
ONKOSUL = {
    'flask_app.py': '_firma_suzgeci',          # MF2
    'templates/base.html': None,
    'templates/ayarlar.html': None,
}


# ══════════════════════════════════════════════════════════════════
#  flask_app.py
# ══════════════════════════════════════════════════════════════════

KOD_YARDIMCI = '''        return {'firma_logo': _logo, 'firma_adi_ayar': _firma_adi,
                # MF3: banner çipi ve firma seçici bunları okur.
                'aktif_firma': _aktif_firma_ozet(),
                'firma_listesi': _firma_listesi_ozet()}

    # ══════════════════════════════════════════════════════════
    #  ÇOKLU FİRMA — ŞABLON VERİSİ ve BELGE KODU  (MF3)
    # ══════════════════════════════════════════════════════════

    def _firma_listesi_ozet():
        """Aktif firmaların kısa listesi — banner ve ayarlar için."""
        if not has_request_context():
            return []
        _o = getattr(g, '_mf3_liste', None)
        if _o is not None:
            return _o
        _l = []
        try:
            with firma_atla():          # firma listesi SÜZÜLMEZ
                for f in (Firma.query.filter_by(aktif=True)
                          .order_by(Firma.sira, Firma.id).all()):
                    _l.append({'id': f.id, 'ad': f.ad,
                               'kod': (f.belge_kodu or '')})
        except Exception:
            _l = []
        g._mf3_liste = _l
        return _l

    def _aktif_firma_ozet():
        """Şu an çalışılan firma — şablonda {{ aktif_firma.ad }}."""
        _fid = aktif_firma_id()
        if not _fid:
            return None
        for f in _firma_listesi_ozet():
            if f['id'] == _fid:
                return f
        return None

    def _firma_belge_kodu():
        """Aktif firmanın belge kodu — KİMLİĞİN KÖKÜNE girer.

        ANA firmada BOŞ: mevcut kimlikler (SIP-STN26-03) korunur ve
        sayaç kaldığı yerden devam eder. İkinci firma kod aldığı için
        kökü farklı olur (SIP-K-STN26-…) ve `LIKE` taraması o köke
        bakar — sayacı kendiliğinden 01'den başlar.

        HAM SQL: bu fonksiyon kimlik üretirken çağrılıyor, yani yazma
        yolunun ortasında. ORM sorgusu açmak süzgeç kancasını yeniden
        tetiklerdi.
        """
        if not has_request_context():
            return ''
        _o = getattr(g, '_mf3_kod', None)
        if _o is not None:
            return _o
        kod = ''
        try:
            _f = aktif_firma_id()
            if _f:
                with db.engine.connect() as _b:
                    _r = _b.execute(sa_text(
                        'SELECT belge_kodu FROM firma WHERE id = :i'),
                        {'i': _f}).fetchone()
                kod = ((_r[0] if _r else '') or '').strip().upper()
        except Exception:
            kod = ''
        g._mf3_kod = kod
        return kod

    def _firma_onbellek_dusur():
        """Firma değişince istek içi önbellekleri temizler.

        Düşürülmezse aynı istekte ESKİ firmanın süzgeci sürerdi:
        kullanıcı B'ye geçtiğini sanıp A'nın verisini görürdü.
        """
        for _a in ('_mf2_firma', '_mf3_kod', '_mf3_liste',
                   'erisim_izin', '_kp1_kapsam'):
            if hasattr(g, _a):
                delattr(g, _a)
'''


API_BLOK = '''    # ══════════════════════════════════════════════════════════
    #  ÇOKLU FİRMA — YÖNETİM VE SEÇİM  (MF3)
    # ══════════════════════════════════════════════════════════

    @app.route('/api/firma', methods=['GET'])
    def api_firma_liste():
        """Firmalar + hangisinde çalışıldığı."""
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        _admin = (session.get('rol') or '').upper() == 'ADMIN'
        with firma_atla():
            kayitlar = (Firma.query.order_by(Firma.sira, Firma.id).all())
        return jsonify({
            'ok': True,
            'aktif': aktif_firma_id(),
            'admin': _admin,
            'firmalar': [{
                'id': f.id, 'ad': f.ad, 'unvan': f.unvan or '',
                'belge_kodu': f.belge_kodu or '',
                'vergi_no': f.vergi_no or '',
                'varsayilan': bool(f.varsayilan), 'aktif': bool(f.aktif),
            } for f in kayitlar]})

    @app.route('/api/firma', methods=['POST'])
    def api_firma_ekle():
        """Yeni firma açar. YALNIZCA ADMIN."""
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if (session.get('rol') or '').upper() != 'ADMIN':
            return jsonify({'ok': False, 'mesaj':
                            'Firma eklemek yalnızca admin yetkisindedir'}), 403
        data = request.get_json(silent=True) or {}
        ad = (data.get('ad') or '').strip()
        kod = (data.get('belge_kodu') or '').strip().upper()
        if not ad:
            return jsonify({'ok': False, 'mesaj': 'Firma adı zorunlu'}), 400
        # ── KOD NEDEN ZORUNLU ──
        # Belge kimlikleri birincil anahtar. Kodsuz ikinci firma ana
        # firmayla AYNI kökü üretir (SIP-STN26-), sayaç ikisini birden
        # sayar ve numaralar iç içe geçer. Kod, her firmanın sayacını
        # kendi başına tutan tek şey.
        if not kod:
            return jsonify({'ok': False, 'mesaj':
                            'Belge kodu zorunlu — bu kod olmadan iki firmanın '
                            'belge numaraları çakışır. Örnek: K'}), 400
        if len(kod) > 4 or not kod.isalnum():
            return jsonify({'ok': False, 'mesaj':
                            'Belge kodu en çok 4 karakter, yalnızca harf/rakam'}), 400
        with firma_atla():
            if Firma.query.filter(db.func.upper(Firma.belge_kodu) == kod).first():
                return jsonify({'ok': False, 'mesaj':
                                f'"{kod}" kodu başka bir firmada kullanılıyor'}), 400
            _son = db.session.query(db.func.max(Firma.sira)).scalar() or 0
            f = Firma(ad=ad, unvan=(data.get('unvan') or ad).strip(),
                      belge_kodu=kod,
                      vergi_dairesi=(data.get('vergi_dairesi') or '').strip() or None,
                      vergi_no=(data.get('vergi_no') or '').strip() or None,
                      adres=(data.get('adres') or '').strip() or None,
                      telefon=(data.get('telefon') or '').strip() or None,
                      eposta=(data.get('eposta') or '').strip() or None,
                      varsayilan=False, aktif=True, sira=_son + 1)
            db.session.add(f)
            _log_audit('EKLE', 'firma', ad, yeni={'ad': ad, 'kod': kod})
            ok, hata = _safe_commit(f'Firma ekle: {ad}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        _firma_onbellek_dusur()
        return jsonify({'ok': True, 'id': f.id,
                        'mesaj': f'{ad} eklendi. Bilgilerini girmek için '
                                 f'o firmaya geçin.'})

    @app.route('/api/firma/sec', methods=['POST'])
    def api_firma_sec():
        """Çalışılan firmayı değiştirir. YALNIZCA ADMIN."""
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if (session.get('rol') or '').upper() != 'ADMIN':
            return jsonify({'ok': False, 'mesaj':
                            'Firma değiştirmek yalnızca admin yetkisindedir'}), 403
        data = request.get_json(silent=True) or {}
        try:
            fid = int(data.get('firma_id') or 0)
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'mesaj': 'Firma kimliği sayı olmalı'}), 400
        with firma_atla():
            f = db.session.get(Firma, fid)
        if not f or not f.aktif:
            return jsonify({'ok': False, 'mesaj': 'Firma bulunamadı ya da pasif'}), 404
        session['firma_id'] = f.id
        _firma_onbellek_dusur()
        _log_audit('DURUM', 'firma', f.id, aciklama=f'{f.ad} firmasina gecildi')
        db.session.commit()
        return jsonify({'ok': True, 'id': f.id, 'ad': f.ad,
                        'mesaj': f'{f.ad} firmasına geçildi'})

'''


# ══════════════════════════════════════════════════════════════════
#  templates/base.html
# ══════════════════════════════════════════════════════════════════

BASE_CSS = '''.kur-cip:empty{display:none}

/* ── FİRMA ÇİPİ (MF3) ──
   Birden fazla firma varsa üst barda görünür; tek firmada hiç
   basılmaz, bugünkü ekran aynen kalır. Admin tıklayıp değiştirir,
   diğerleri yalnızca hangi firmada olduklarını görür. */
.firma-cip{display:flex;align-items:center;gap:7px;font-size:.8rem;font-weight:600;
  color:var(--murekkep);background:var(--yuzey);border:1px solid var(--cizgi-koyu);
  border-radius:20px;padding:5px 13px;white-space:nowrap;transition:border-color .15s}
.firma-cip[data-secilebilir]{cursor:pointer}
.firma-cip[data-secilebilir]:hover{border-color:var(--verde);color:var(--verde)}
.firma-cip .kod{font-family:var(--mono);font-size:.72rem;color:var(--soluk);
  border:1px solid var(--cizgi);border-radius:5px;padding:0 5px}
.firma-menu{display:none;position:absolute;right:0;top:38px;min-width:240px;
  background:var(--yuzey);border:1px solid var(--cizgi);border-radius:11px;
  box-shadow:0 16px 44px rgba(25,28,26,.22);z-index:60;padding:6px}
.firma-menu.acik{display:block}
.firma-menu .baslik{font-size:.72rem;letter-spacing:.05em;text-transform:uppercase;
  color:var(--soluk);padding:7px 10px 5px}
.firma-menu button{display:flex;align-items:center;justify-content:space-between;gap:10px;
  width:100%;text-align:left;padding:9px 10px;border:0;background:transparent;
  border-radius:7px;font-size:.86rem;color:var(--murekkep);cursor:pointer}
.firma-menu button:hover{background:var(--taban)}
.firma-menu button.secili{color:var(--verde);font-weight:700}
@media (max-width:1100px){.ust .firma-cip .ad{display:none}}'''

BASE_MARKUP = '''        {# ── FİRMA ÇİPİ (MF3) ──
           Tek firma varsa HİÇ basılmaz: bugünkü üst bar aynen kalır.
           Admin seçici görür, diğerleri yalnızca etiket — firma
           değiştirmek admin yetkisinde. #}
        {% if firma_listesi and firma_listesi|length > 1 %}
        <div style="position:relative">
          <button class="firma-cip" {% if menu_admin %}data-secilebilir="1"
                  onclick="firmaMenuAc(event)" title="Çalışılan firma — değiştir"
                  {% else %}disabled title="Çalışılan firma"{% endif %}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2"><path d="M3 21h18"/>
              <path d="M5 21V7l7-4 7 4v14"/><path d="M10 21v-6h4v6"/></svg>
            <span class="ad">{{ aktif_firma.ad if aktif_firma else '—' }}</span>
            {% if aktif_firma and aktif_firma.kod %}
            <span class="kod">{{ aktif_firma.kod }}</span>{% endif %}
          </button>
          {% if menu_admin %}
          <div class="firma-menu" id="firmaMenu">
            <div class="baslik">Firma değiştir</div>
            {% for f in firma_listesi %}
            <button onclick="firmaSec({{ f.id }})"
                    class="{{ 'secili' if aktif_firma and f.id == aktif_firma.id else '' }}">
              <span>{{ f.ad }}</span>
              <span class="kod">{{ f.kod or '—' }}</span>
            </button>
            {% endfor %}
          </div>
          {% endif %}
        </div>
        {% endif %}
        <span class="kur-cip" id="ustKur" onclick="kurSorguAc()" title="Kur sorgula — geçmiş tarihler dahil"></span>'''

BASE_JS = '''
/* ── FİRMA SEÇİCİ (MF3) ── */
function firmaMenuAc(e) {
  if (e) e.stopPropagation();
  const m = document.getElementById('firmaMenu');
  if (m) m.classList.toggle('acik');
}
document.addEventListener('click', e => {
  const m = document.getElementById('firmaMenu');
  if (m && m.classList.contains('acik') && !m.contains(e.target)) {
    m.classList.remove('acik');
  }
});
async function firmaSec(id) {
  try {
    const d = await api('/api/firma/sec', {
      method: 'POST', body: JSON.stringify({ firma_id: id }) });
    if (d && d.ok) {
      /* TAM YENİLEME ŞART: açık listeler, çekmeceler ve önbellekli
         sayılar hâlâ ESKİ firmanın verisini taşıyor. Kısmi tazeleme
         iki firmanın verisini aynı ekranda gösterirdi. */
      location.reload();
    } else {
      bildir((d && d.mesaj) || 'Firma değiştirilemedi', true);
    }
  } catch (err) { bildir('Firma değiştirilemedi', true); }
}
'''


# ══════════════════════════════════════════════════════════════════
#  templates/ayarlar.html
# ══════════════════════════════════════════════════════════════════

AYARLAR_PANEL = '''<section class="bolum" id="b-firma">
  <!-- ── FİRMALAR (MF3) ──
       Sistem birden çok tüzel kişilik taşıyabilir. Aşağıdaki "Firma
       Bilgileri" formu AKTİF FİRMAYI düzenler; başka bir firmanın
       bilgisini girmek için önce üst bardan o firmaya geç. -->
  <div class="panel" id="firmalarPanel" style="margin-bottom:18px">
    <h4>Firmalar</h4>
    <p style="color:var(--soluk);font-size:.83rem;margin-bottom:14px">
      Her firmanın stoğu, siparişi, kasası ve defteri ayrıdır.
      Aşağıdaki form <b>aktif firmayı</b> düzenler.</p>
    <div class="tablo-kutu">
      <table>
        <thead><tr><th>Firma</th><th>Belge Kodu</th><th>Vergi No</th>
          <th class="sag" style="width:120px"></th></tr></thead>
        <tbody id="firmaGovde"><tr><td colspan="4" class="yukleniyor">Yükleniyor…</td></tr></tbody>
      </table>
    </div>
    <div id="firmaEkleKutu" style="margin-top:14px"></div>
  </div>
  <div class="izgara-2">'''

AYARLAR_JS = '''
/* ── FİRMALAR (MF3) ── */
let FIRMA_VERI = null;
async function firmaListesiYukle() {
  const govde = document.getElementById('firmaGovde');
  if (!govde) return;
  try {
    FIRMA_VERI = await api('/api/firma');
  } catch (e) {
    govde.innerHTML = '<tr><td colspan="4" class="bos">Firmalar okunamadı</td></tr>';
    return;
  }
  const fl = (FIRMA_VERI && FIRMA_VERI.firmalar) || [];
  govde.innerHTML = fl.length ? fl.map(f => `
    <tr>
      <td><b>${kacar(f.ad)}</b>${f.varsayilan ? ' <span class="rozet rz-gri">varsayılan</span>' : ''}
          ${f.id === FIRMA_VERI.aktif ? ' <span class="rozet rz-yesil">aktif</span>' : ''}
          ${f.unvan && f.unvan !== f.ad ? `<div style="color:var(--soluk);font-size:.78rem">${kacar(f.unvan)}</div>` : ''}</td>
      <td class="mono">${kacar(f.belge_kodu || '—')}</td>
      <td class="mono">${kacar(f.vergi_no || '—')}</td>
      <td class="sag">${(FIRMA_VERI.admin && f.id !== FIRMA_VERI.aktif)
        ? `<button class="mini-btn" onclick="firmaGec(${f.id})">Bu firmaya geç</button>` : ''}</td>
    </tr>`).join('')
    : '<tr><td colspan="4" class="bos">Firma kaydı yok</td></tr>';

  const kutu = document.getElementById('firmaEkleKutu');
  if (!kutu) return;
  if (!FIRMA_VERI.admin) { kutu.innerHTML = ''; return; }
  kutu.innerHTML = `<button class="btn-yeni" onclick="firmaEkleAc()">+ Yeni Firma</button>`;
}

function firmaEkleAc() {
  const kutu = document.getElementById('firmaEkleKutu');
  kutu.innerHTML = `
    <div class="panel" style="background:var(--taban)">
      <h4 style="margin-bottom:10px">Yeni Firma</h4>
      <p style="color:var(--soluk);font-size:.82rem;margin-bottom:12px">
        <b>Belge kodu</b> zorunlu ve kısa olmalı (örn. K). Bu kod belge
        kimliklerinin köküne girer — <span class="mono">SIP-K-STN26-01</span> —
        ve her firmanın numarasının kendi başına ilerlemesini sağlar.
        Kodsuz iki firmanın numaraları çakışır.</p>
      <div class="izgara-2">
        <div class="form-alan"><label>Firma Adı *</label>
          <input id="nfAd" placeholder="İkinci Mermer A.Ş."></div>
        <div class="form-alan"><label>Belge Kodu * (en çok 4)</label>
          <input id="nfKod" maxlength="4" placeholder="K" style="text-transform:uppercase"></div>
        <div class="form-alan"><label>Ticari Ünvan</label>
          <input id="nfUnvan" placeholder="Belgelerde görünen tam ünvan"></div>
        <div class="form-alan"><label>Vergi No</label>
          <input id="nfVno" placeholder="1234567890"></div>
      </div>
      <div style="display:flex;gap:8px;margin-top:12px">
        <button class="btn-yeni" id="nfKaydet" onclick="yeniFirmaKaydet()">Firmayı Ekle</button>
        <button class="iptal-btn" onclick="firmaListesiYukle()">Vazgeç</button>
      </div>
    </div>`;
}

async function yeniFirmaKaydet() {
  const ad = (document.getElementById('nfAd').value || '').trim();
  const kod = (document.getElementById('nfKod').value || '').trim().toUpperCase();
  if (!ad) { bildir('Firma adı gir.', true); return; }
  if (!kod) { bildir('Belge kodu gir — numaralar çakışmasın.', true); return; }
  const b = document.getElementById('nfKaydet');
  b.disabled = true; b.textContent = 'Ekleniyor…';
  try {
    const d = await api('/api/firma', { method: 'POST', body: JSON.stringify({
      ad, belge_kodu: kod,
      unvan: (document.getElementById('nfUnvan').value || '').trim(),
      vergi_no: (document.getElementById('nfVno').value || '').trim() }) });
    if (d && d.ok) { bildir(d.mesaj || 'Firma eklendi'); await firmaListesiYukle(); }
    else { bildir((d && d.mesaj) || 'Eklenemedi', true); b.disabled = false;
           b.textContent = 'Firmayı Ekle'; }
  } catch (e) {
    bildir('Eklenemedi', true); b.disabled = false; b.textContent = 'Firmayı Ekle';
  }
}

async function firmaGec(id) {
  try {
    const d = await api('/api/firma/sec', {
      method: 'POST', body: JSON.stringify({ firma_id: id }) });
    if (d && d.ok) location.reload();
    else bildir((d && d.mesaj) || 'Geçilemedi', true);
  } catch (e) { bildir('Geçilemedi', true); }
}
'''


def degisiklikler():
    return [
        # ── flask_app.py ──
        ('flask_app.py', 'MF3-a · Firma modeli içe aktarımı',
         "from models import Konteyner",
         "from models import Konteyner\nfrom models import Firma, CariFirma   # MF3"),
        ('flask_app.py', 'MF3-b · şablon verisi + belge kodu yardımcıları',
         "        return {'firma_logo': _logo, 'firma_adi_ayar': _firma_adi}",
         KOD_YARDIMCI),
        ('flask_app.py', 'MF3-c · kimlik köküne belge kodu',
         "            kok = f'{on_ek}-{kok_ic}-'",
         "            # MF3: firma kodu köke girer — her firmanın sayacı\n"
         "            # kendi başına ilerlesin diye. Ana firmada kod boş.\n"
         "            _fk = _firma_belge_kodu()\n"
         "            _on = f'{on_ek}-{_fk}' if _fk else on_ek\n"
         "            kok = f'{_on}-{kok_ic}-'"),
        ('flask_app.py', 'MF3-d · kisaltmada da kod korunur',
         "                kok = f'{on_ek}-{kok_ic[:max(1, len(kok_ic) - kesilecek)]}-'",
         "                kok = f'{_on}-{kok_ic[:max(1, len(kok_ic) - kesilecek)]}-'"),
        ('flask_app.py', 'MF3-e · stok kimliginde belge kodu',
         "            aday = f'{on_ek}-{temiz}' + (f'-{int(sira):02d}' if sira not in (None, '') else '')",
         "            # MF3: ayni blok numarasi iki firmada da olabilir.\n"
         "            _fk = _firma_belge_kodu()\n"
         "            _on = f'{on_ek}-{_fk}' if _fk else on_ek\n"
         "            aday = f'{_on}-{temiz}' + (f'-{int(sira):02d}' if sira not in (None, '') else '')"),
        ('flask_app.py', 'MF3-f · /api/firma yetki haritasina',
         "        ('/api/banka', 'ayarlar'),",
         "        ('/api/banka', 'ayarlar'),\n        ('/api/firma', 'ayarlar'),   # MF3"),
        ('flask_app.py', 'MF3-g · firma yonetim ve secim uclari',
         "    @app.route('/api/ayarlar/firma', methods=['GET'])",
         API_BLOK + "    @app.route('/api/ayarlar/firma', methods=['GET'])"),
        # ── base.html ──
        ('templates/base.html', 'MF3-h · firma cipi bicemi',
         ".kur-cip:empty{display:none}", BASE_CSS),
        ('templates/base.html', 'MF3-i · banner firma cipi',
         '        <span class="kur-cip" id="ustKur" onclick="kurSorguAc()" '
         'title="Kur sorgula — geçmiş tarihler dahil"></span>',
         BASE_MARKUP),
        ('templates/base.html', 'MF3-j · firma secici betigi',
         "</body>", "<script>" + BASE_JS + "</script>\n</body>"),
        # ── ayarlar.html ──
        ('templates/ayarlar.html', 'MF3-k · Firmalar paneli',
         '<section class="bolum" id="b-firma">\n  <div class="izgara-2">',
         AYARLAR_PANEL),
        ('templates/ayarlar.html', 'MF3-l · firma yonetim betigi',
         "</script>", AYARLAR_JS + "</script>"),
    ]


def main():
    print('=' * 70)
    print('  YAMA MF3 — ÇOKLU FİRMA 3/4: FİRMA SEÇİCİ VE YÖNETİMİ')
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
            print(f'  ✗ ÖNKOŞUL YOK: "{onk}" bulunamadı — önce MF2 uygulanmalı')
            hata = True
            continue

        if DOSYA_IMZA[dosya] in icerik:
            print(f'  ⊙ İmza "{DOSYA_IMZA[dosya]}" zaten var — ATLANIR')
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
        print('  ⊙ Yama MF3 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_mf3.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        yedek = yol + '.yedek_mf3'
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
    print('    venv/bin/python js_denetim.py')
    print()
    print('  TEK firma varken üst barda hiçbir şey değişmez.')
    print('  İkinci firmayı Ayarlar → Firma → Firmalar bölümünden aç;')
    print('  çip o zaman görünür.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

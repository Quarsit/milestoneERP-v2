#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA OR3 — İŞ LİSTEDEN SEÇİLİYOR + BAĞLI PROFORMA KORUNUYOR
============================================================

ÖNKOŞUL: yama_or2.py uygulanmış olmalı.

İki soru sordun; ikisi de aynı pencereye çıktı.

── 1 · "BAĞLADIĞIMIZ DEĞERLER GÜNCELLENECEK Mİ?" ──
  EVET, ve bunun sebebi tasarımda: `ortaklik_is` kopya değil
  REFERANS tutuyor — yalnız tip ve numara. Ciro her açılışta satış
  kayıtlarından yeniden okunuyor, hiçbir yerde dondurulmuş bir
  rakam yok.

  Sistem tehlikeli durumu da zaten engelliyormuş:
    · Siparişe satış kaydı bağlandıktan sonra KALEMLERİ
      değiştirilemiyor (SG1 kapısı).
    · Satış kaydı olan sipariş SİLİNEMİYOR.
  Yani ortaklık ya güncel rakamı gösterir ya da henüz rakam yoktur;
  arada "eski değerle donmuş" bir hâl yok.

  AMA BİR DELİK VARDI — aşağıda.

── 2 · İŞ ARTIK LİSTEDEN SEÇİLİYOR ──
  Numarayı elle yazdırmak iki yükü birden sana bırakıyordu:
  numarayı hatırlamak ve o işin BAŞKA bir ortaklığa bağlı olup
  olmadığını bilmek. İkincisini ancak Ekle'ye basınca, 409 hatası
  olarak öğreniyordun.

  Artık pencere sistemden çekiyor: numara, müşteri, tarih ve tutar
  bir arada. Üstünde arama kutusu var.

  ZATEN BAĞLI İŞLER LİSTEDE ÇIKMIYOR — seçebildiğin her satır
  gerçekten bağlanabilir. Doğrulama kaydetme anından SEÇİM anına
  taşındı.

  Satış kaydı olmayan işler listede duruyor ama "· satış kaydı yok"
  diye işaretli: bağlamak yanlış değil (teslim edilmemiş olabilir)
  ama cirosunun 0 çıkacağını seçerken bilmelisin.

── 3 · BULDUĞUM DELİK: BAĞLI PROFORMA SİLİNEBİLİYORDU ──
  Proforma silinince satış kaydı KALIYOR ama `proforma_id`
  boşaltılıyor — kâr izi kaybolmasın diye, doğru bir karar. Ne var
  ki ortaklık ciroyu o bağ üzerinden okuyor: proformayı silmek,
  ortaklığın cirosunu SEBEBİ GÖRÜNMEDEN sıfıra düşürürdü. Satış
  kaydı duruyor, bağ yok, ekranda "satış kaydı yok" yazıyor.

  Siparişte bu kapı zaten vardı, proformada yoktu. Kapandı:
  ortaklığa bağlı proforma silinemiyor, hangi ortaklık olduğunu
  söylüyor.

  Ayrıca motor artık bağlı kaynağın hâlâ var olup olmadığına
  bakıyor; yoksa "satış kaydı yok" demek yerine "bağlı iş artık
  sistemde yok: PROFORMA PRF-26-04" diyor. Eski verilerde
  kopmuş bir bağ varsa onu da yakalar.

── ÖLÇÜLDÜ (tarayıcıda) ──
  Seçici penceresi: serbest metin kutusu KALMADI (`input#kNo` yok),
  listede numara · müşteri · tarih · tutar bir arada; bu ortaklığa
  bağlı sipariş listede ÇIKMIYOR; satış kaydı olmayan iş
  işaretli geliyor. JS hatası yok.

  144 test geçti (141 + 3 yeni kalıcı test);
  firma · js · form · zincir · akis · degismezlik temiz.

── NE YAPMADIM ──
  Liste son 300 kayıtla sınırlı. Arama kutusu YALNIZCA yüklenen
  listeyi süzüyor, sunucuda arama yapmıyor. Bugünkü kayıt
  sayısında fark etmez; binlere çıkınca sunucu tarafı aramaya
  çevirmek gerekir.

DOSYALAR
--------
  flask_app.py             bağlanabilir işler ucu · proforma kapısı ·
                           kayıp kaynak uyarısı
  templates/ortaklik.html  iş seçici (arama + liste)
  tests/test_kritik.py     3 yeni test

Şema yok, göç yok.

KULLANIM
--------
  python3 yama_or3.py            # RAPOR
  python3 yama_or3.py --uygula
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
    'flask_app.py': 'def api_ortaklik_baglanabilir(oid):',
    'templates/ortaklik.html': 'async function isListesiYukle()',
    'tests/test_kritik.py': 'def test_or3_baglanabilir_liste_bagli_isleri_elemeli',
}
ONKOSUL = {
    'flask_app.py': 'def _ortaklik_usd(tutar, doviz, tarih=None):',
    'templates/ortaklik.html': 'Hesap para birimi',
    'tests/test_kritik.py': 'def test_or2_farkli_dovizler_kendi_tarihinin_kuruyla_cevrilir',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'OR3 · flask_app.py blok 1',
     r'''    @app.route('/api/ortaklik/<oid>/is', methods=['POST'])
''',
     r'''    @app.route('/api/ortaklik/<oid>/baglanabilir', methods=['GET'])
    def api_ortaklik_baglanabilir(oid):
        """OR3 — bağlanabilecek işler, SEÇİLEBİLİR hâlde.

        Numarayı elle yazdırmak iki şeyi birden kullanıcıya
        yıkıyordu: numarayı hatırlamak ve o işin zaten başka bir
        ortaklığa bağlı olup olmadığını bilmek. İkincisi ancak
        kaydet'e basınca 409 olarak ortaya çıkıyordu.

        Burada ZATEN BAĞLI işler listeden düşüyor: seçilebilen her
        satır gerçekten bağlanabilir.
        """
        if _auth_required(): return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('karlilik', 'okuma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
        if not _ortaklik_bul(oid):
            return jsonify({'ok': False, 'mesaj': 'Ortaklık bulunamadı'}), 404
        tip = (request.args.get('tip') or 'SIPARIS').strip().upper()
        if tip not in ('SIPARIS', 'SEVKIYAT', 'PROFORMA'):
            return jsonify({'ok': False, 'mesaj': 'Geçersiz tip'}), 400

        # Hangi işler zaten bağlı (HERHANGİ bir ortaklığa)
        bagli = {b.kaynak_id for b in OrtaklikIs.query.filter_by(
            kaynak_tip=tip).all()}

        kayitlar = []
        if tip == 'SIPARIS':
            for s in Siparis.query.order_by(
                    Siparis.siparis_tarihi.desc(), Siparis.id.desc()
                    ).limit(300).all():
                if s.id in bagli:
                    continue
                kayitlar.append({
                    'id': s.id, 'musteri': s.musteri or '',
                    'tarih': _iso(s.siparis_tarihi),
                    'tutar': s.toplam_tutar or 0, 'doviz': s.doviz or 'USD',
                    'durum': s.durum or ''})
        elif tip == 'PROFORMA':
            for p in Proforma.query.order_by(
                    Proforma.olusturma.desc(), Proforma.id.desc()
                    ).limit(300).all():
                if p.id in bagli:
                    continue
                kayitlar.append({
                    # Proforma'da `tarih` sütunu yok; oluşturma damgası var.
                    'id': p.id, 'musteri': p.musteri or '',
                    'tarih': _iso(p.olusturma.date() if p.olusturma else None),
                    'tutar': getattr(p, 'toplam', 0) or 0,
                    'doviz': p.doviz or 'USD', 'durum': p.durum or ''})
        else:
            for v in Sevkiyat.query.order_by(
                    Sevkiyat.sevk_tarihi.desc(), Sevkiyat.id.desc()
                    ).limit(300).all():
                if v.id in bagli:
                    continue
                kayitlar.append({
                    'id': v.id, 'musteri': v.musteri or '',
                    'tarih': _iso(v.sevk_tarihi), 'tutar': 0,
                    'doviz': '', 'durum': v.durum or ''})

        # Her kayda SATIŞ KAYDI olup olmadığını da söyle: cirosu
        # olmayan bir işi bağlamak yanlış değil (teslim edilmemiş
        # olabilir) ama seçerken bilmek gerekir.
        for k in kayitlar:
            if tip == 'SIPARIS':
                k['satis_var'] = SatisKaydi.query.filter_by(
                    siparis_id=k['id']).count() > 0
            elif tip == 'PROFORMA':
                k['satis_var'] = SatisKaydi.query.filter_by(
                    proforma_id=k['id']).count() > 0
            else:
                k['satis_var'] = SatisKaydi.query.filter_by(
                    sevkiyat_id=k['id']).count() > 0

        return jsonify({'ok': True, 'data': kayitlar,
                        'bagli_adedi': len(bagli)})

    @app.route('/api/ortaklik/<oid>/is', methods=['POST'])
'''),
    ('flask_app.py', 'OR3 · flask_app.py blok 2',
     r'''        if not satislar and isler:
''',
     r'''        # OR3: bağlı kaynak hâlâ duruyor mu? Yoksa "satış kaydı yok"
        # demek yanıltıcı olur — iş ortadan kalkmıştır.
        _kayip = []
        for i in isler:
            _m = {'SIPARIS': Siparis, 'SEVKIYAT': Sevkiyat,
                  'PROFORMA': Proforma}.get(i.kaynak_tip)
            if _m is not None and not _m.query.filter_by(id=i.kaynak_id).first():
                _kayip.append(f'{i.kaynak_tip} {i.kaynak_id}')
        if _kayip:
            uyarilar.append(
                'Bağlı iş(ler) artık sistemde yok: ' + ', '.join(_kayip) +
                '. Ciro bu işlerden gelmiyor; bağı çözün ya da kaydı '
                'geri getirin.')
        elif not satislar and isler:
'''),
    ('flask_app.py', 'OR3 · flask_app.py blok 3',
     r'''        # Satis kaydi (kar/zarar izi) KALIR, yalnizca bag kopar.
''',
     r'''        # ── OR3 · ORTAKLIĞA BAĞLI PROFORMA SİLİNEMEZ ──
        # Aşağıda satış kaydının `proforma_id`'si boşaltılıyor (kâr
        # izi kalsın diye, doğru). Ama o proforma bir ortaklığa
        # bağlıysa ortaklığın cirosu SEBEBİ GÖRÜNMEDEN sıfıra
        # düşerdi: satış kaydı duruyor, bağ yok. Siparişte bu kapı
        # zaten var (satış kaydı varsa silme reddediliyor).
        _ort = OrtaklikIs.query.filter_by(
            kaynak_tip='PROFORMA', kaynak_id=proforma_id).first()
        if _ort:
            return jsonify({'ok': False, 'error': 'ortakliga_bagli',
                'mesaj': f'Bu proforma {_ort.ortaklik_id} ortaklığına bağlı; '
                         f'silinemez. Önce ortaklıktaki bağı çözün.'}), 400
        # Satis kaydi (kar/zarar izi) KALIR, yalnizca bag kopar.
'''),
    ('templates/ortaklik.html', 'OR3 · templates/ortaklik.html blok 1',
     r'''  is: {baslik: 'İş bağla', alt: 'Sipariş, sevkiyat ya da proforma numarası.', html: `
    <div class="form-satir f2">
      <div class="form-alan"><label>Tip</label><select id="kTip">
        <option value="SIPARIS">Sipariş</option>
        <option value="SEVKIYAT">Sevkiyat</option>
        <option value="PROFORMA">Proforma</option></select></div>
      <div class="form-alan"><label>Numara *</label><input id="kNo" placeholder="SIP-26-01"></div>
    </div>
''',
     r'''  is: {baslik: 'İş bağla', alt: 'Sistemdeki kayıtlardan seç.', html: `
    <div class="form-satir f2">
      <div class="form-alan"><label>Tip</label>
        <select id="kTip" onchange="isListesiYukle()">
        <option value="SIPARIS">Sipariş</option>
        <option value="SEVKIYAT">Sevkiyat</option>
        <option value="PROFORMA">Proforma</option></select></div>
      <div class="form-alan"><label>Ara</label>
        <input id="kAra" placeholder="no, müşteri…" oninput="isListesiCiz()"></div>
    </div>
    <div class="form-satir"><div class="form-alan"><label>İş *</label>
      <select id="kNo" size="8" style="height:auto;font-family:var(--mono,monospace);
              font-size:.82rem"></select>
      <div class="yardim" id="kListeNot">Yükleniyor…</div></div></div>
'''),
    ('templates/ortaklik.html', 'OR3 · templates/ortaklik.html blok 2',
     r'''  document.getElementById('kalemModal').classList.add('acik');
''',
     r'''  document.getElementById('kalemModal').classList.add('acik');
  if (tip === 'is') isListesiYukle();
}

/* ── BAĞLANABİLİR İŞLER (OR3) ──
   Numarayı elle yazdırmak iki yükü birden kullanıcıya bırakıyordu:
   numarayı hatırlamak ve o işin BAŞKA bir ortaklığa bağlı olup
   olmadığını bilmek. İkincisi ancak kaydet'e basınca 409 olarak
   ortaya çıkıyordu. Uç, bağlı işleri zaten eliyor. */
let IS_LISTE = [];

async function isListesiYukle() {
  if (!ACIK) return;
  const tip = document.getElementById('kTip').value;
  const not = document.getElementById('kListeNot');
  IS_LISTE = [];
  if (not) not.textContent = 'Yükleniyor…';
  isListesiCiz();
  try {
    const d = await api(`/api/ortaklik/${encodeURIComponent(ACIK.id)}` +
                        `/baglanabilir?tip=${tip}`);
    IS_LISTE = d.data || [];
    if (not) {
      not.textContent = IS_LISTE.length
        ? `${IS_LISTE.length} kayıt · başka ortaklığa bağlı olanlar listede yok`
        : 'Bağlanabilecek kayıt yok (hepsi başka bir ortaklıkta olabilir).';
    }
  } catch (e) {
    if (not) not.textContent = e.message || 'Liste alınamadı';
  }
  isListesiCiz();
}

function isListesiCiz() {
  const sec = document.getElementById('kNo');
  if (!sec) return;
  const ara = (document.getElementById('kAra') || {}).value || '';
  const s = ara.trim().toLocaleLowerCase('tr');
  const gorunen = s
    ? IS_LISTE.filter(x => (x.id + ' ' + (x.musteri || ''))
        .toLocaleLowerCase('tr').includes(s))
    : IS_LISTE;
  sec.innerHTML = gorunen.map(x => {
    const parcalar = [x.id];
    if (x.musteri) parcalar.push(x.musteri);
    if (x.tarih) parcalar.push(x.tarih);
    if (x.tutar) parcalar.push(para2(x.tutar, x.doviz));
    /* Satış kaydı yoksa bağlamak YANLIŞ değil (teslim edilmemiş
       olabilir) ama seçerken görünmeli: cirosu 0 çıkacak. */
    if (!x.satis_var) parcalar.push('satış kaydı yok');
    return `<option value="${kacar(x.id)}">${kacar(parcalar.join('  ·  '))}</option>`;
  }).join('');
'''),
    ('templates/ortaklik.html', 'OR3 · templates/ortaklik.html blok 3',
     r'''    if (!govde.kaynak_id) { bildir('Numara zorunlu', true); return; }
''',
     r'''    if (!govde.kaynak_id) { bildir('Listeden bir iş seç', true); return; }
'''),
    ('tests/test_kritik.py', 'OR3 · tests/test_kritik.py blok 1',
     r'''    assert h['net_kar'] == 5800, h['net_kar']    # 6000 − 200
    assert h['cevrim_yapildi'] is True
''',
     r'''    assert h['net_kar'] == 5800, h['net_kar']    # 6000 − 200
    assert h['cevrim_yapildi'] is True


def test_or3_baglanabilir_liste_bagli_isleri_elemeli():
    """OR3: iş numarası elle yazılmıyor, listeden seçiliyor.

    Liste ZATEN BAĞLI işleri eliyor: eskiden seçilebilen bir
    numara kaydet'e basınca 409 dönüyordu — hatayı seçim anında
    değil, kaydetme anında öğreniyordun."""
    _or1_kur('SIPOR8', [(5000, 3000)])
    _or1_kur('SIPOR9', [(7000, 4000)])
    c = istemci('admin', 'ADMIN')
    a = c.post('/api/ortaklik', headers=H,
               json={'ad': 'Seçici A'}).get_json()['id']
    b = c.post('/api/ortaklik', headers=H,
               json={'ad': 'Seçici B'}).get_json()['id']

    d = c.get(f'/api/ortaklik/{a}/baglanabilir?tip=SIPARIS').get_json()
    idler = [x['id'] for x in d['data']]
    assert 'SIPOR8' in idler and 'SIPOR9' in idler, idler
    # Satış kaydı olan işler işaretli geliyor
    s8 = [x for x in d['data'] if x['id'] == 'SIPOR8'][0]
    assert s8['satis_var'] is True and s8['musteri'] == 'ACIK CARI'

    # SIPOR8'i A'ya bağla → B'nin listesinden DÜŞMELİ
    assert c.post(f'/api/ortaklik/{a}/is', headers=H, json={
        'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR8'}).status_code == 200
    d2 = c.get(f'/api/ortaklik/{b}/baglanabilir?tip=SIPARIS').get_json()
    idler2 = [x['id'] for x in d2['data']]
    assert 'SIPOR8' not in idler2, idler2
    assert 'SIPOR9' in idler2, idler2

    # Geçersiz tip reddedilir
    assert c.get(f'/api/ortaklik/{a}/baglanabilir?tip=HEBELE').status_code == 400


def test_or3_ortakliga_bagli_proforma_silinemez():
    """OR3: bağlı proforma silinirse ortaklığın cirosu SEBEPSİZ düşer.

    Proforma silinince satış kaydı KALIYOR ama `proforma_id`
    boşaltılıyor (kâr izi kaybolmasın diye, doğru). Ortaklık o bağ
    üzerinden okuduğu için ciro sessizce sıfırlanırdı. Siparişte bu
    kapı zaten vardı, proformada yoktu."""
    from models import Proforma, SatisKaydi
    with fa.app.app_context():
        db.session.add(Proforma(id='PROR3', musteri='ACIK CARI', cari_id='C1',
                                toplam=9000, doviz='USD', durum='Taslak'))
        db.session.flush()
        db.session.add(SatisKaydi(
            id='PROR3-S1', proforma_id='PROR3', stok_tip='PLAKA', cins='TEST',
            musteri='ACIK CARI', satis_tarihi=date(2026, 4, 5),
            tutar=9000, tutar_usd=9000, doviz='USD',
            maliyet_usd=5000, kar_usd=4000))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Proforma bağı', 'bizim_pay': 50,
        'ortak_pay': 50}).get_json()['id']
    assert c.post(f'/api/ortaklik/{oid}/is', headers=H, json={
        'kaynak_tip': 'PROFORMA', 'kaynak_id': 'PROR3'}).status_code == 200

    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h['ciro'] == 9000 and h['brut_kar'] == 4000, h

    r = c.delete('/api/proforma/PROR3', headers=H)
    assert r.status_code == 400, r.get_data(as_text=True)
    assert r.get_json().get('error') == 'ortakliga_bagli'
    # Ciro yerinde duruyor
    h2 = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert h2['ciro'] == 9000

    # Bağ çözülünce silinebilir
    isler = c.get(f'/api/ortaklik/{oid}').get_json()['data']['isler']
    assert c.delete(f"/api/ortaklik/{oid}/is/{isler[0]['id']}",
                    headers=H).status_code == 200
    assert c.delete('/api/proforma/PROR3', headers=H).status_code == 200


def test_or3_kaybolan_kaynak_acikca_soyleniyor():
    """OR3: bağlı iş sistemden kalkmışsa 'satış kaydı yok' demek
    yanıltıcıdır — iş ortadan kalkmıştır, bunu söylemeli."""
    from models import Sevkiyat
    with fa.app.app_context():
        db.session.add(Sevkiyat(id='SVOR3', musteri='ACIK CARI',
                                sevk_tarihi=date(2026, 4, 1),
                                durum='Hazirlaniyor'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H,
                 json={'ad': 'Kayıp kaynak'}).get_json()['id']
    assert c.post(f'/api/ortaklik/{oid}/is', headers=H, json={
        'kaynak_tip': 'SEVKIYAT', 'kaynak_id': 'SVOR3'}).status_code == 200

    h = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert any('satış kaydı yok' in u for u in h['uyarilar']), h['uyarilar']

    # Sevkiyat ortadan kalkarsa mesaj DEĞİŞMELİ
    with fa.app.app_context():
        db.session.delete(Sevkiyat.query.filter_by(id='SVOR3').first())
        db.session.commit()
    h2 = c.get(f'/api/ortaklik/{oid}').get_json()['data']['hesap']
    assert any('artık sistemde yok' in u and 'SVOR3' in u
               for u in h2['uyarilar']), h2['uyarilar']
'''),
]

TAM_ICERIK = {}

def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA OR3 — IS LISTEDEN SECILIYOR')
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
        print('    python3 yama_or3.py            # rapor')
        print('    python3 yama_or3.py --uygula')
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
        print('  ⊙ Yama OR3 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_or3.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_or3'
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
    print('    "+ Is bagla": numara artik ELLE yazilmiyor, listeden')
    print('    seciliyor. Baska ortakliga bagli isler listede yok.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

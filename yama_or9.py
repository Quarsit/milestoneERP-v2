#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA OR9 — ORTAKLIK RAPORU VE EKSTRESİ
=======================================

ÖNKOŞUL: yama_or8.py uygulanmış olmalı.

── 1 · RAPOR (Dışa Aktar) ──
  Ortaklık sayfasının başlığına "Dışa Aktar" geldi — öteki
  modüllerdeki düğmenin aynısı, Excel ve PDF.

  Sütunlar: ortaklık, ortak, durum, iş sayısı, ciro, maliyet, brüt
  kâr, vergi, net kâr, iki tarafın payı, iki tarafın katkısı,
  ortağa ödenecek, ortak bakiye. Altta toplam ciro / brüt kâr /
  net kâr ve ortaklara kalan bakiye.

── 2 · EKSTRE — İKİ KİP ──
  Çekmecede iki düğme: "Ekstre" ve "Ekstre (iç)". Yeni sekmede
  açılıyor, tarayıcıdan PDF'e basılıyor — cari ekstresiyle aynı
  yol. Ayrı bir PDF makinesi kurmak, aynı belgenin iki yerde iki
  ayrı biçimde üretilmesiyle biterdi.

  ORTAĞA GÖNDERİLECEK HÂLİ: hesabın tamamı — ciro, maliyet, vergi
  kalemleri, net kâr, iki tarafın payı ve katkısı, dağıtımlar,
  bakiye.

  İÇ KULLANIM HÂLİ: üstüne bağlı işler, satış kayıtları ve maliyet
  kayıtları (fatura no'larıyla, hangisi katkıya alınmış işaretiyle).
  Sayfanın köşesinde "İÇ KULLANIM" damgası var — yanlışlıkla
  gönderirsen belli olsun.

  SIZDIRMAYA YER BIRAKMADIM: iç kipin verisi şablonda gizlenmiyor,
  sunucu ortak kipinde onu HİÇ GÖNDERMİYOR. Şablonda bir koşul
  unutulsa bile müşteri adı ortağın belgesine basılamaz. Geçersiz
  bir kip adı da ortak kipine düşüyor.

── TEST BİR SIZINTI YAKALADI ──
  Maliyetten alınan katkının açıklaması iç referans taşıyordu:
  "Kesim / Fason / Üretim · MYT-26-01 · FSN-114". Katkılar tablosu
  her iki kipte de basıldığı için FATURA NO ortağın belgesine
  giriyordu. Ortak kipinde artık yalnız kalemin NE OLDUĞU yazıyor.

── ÖLÇÜLDÜ (tarayıcıda) ──
  ortak kipi bölümleri : Hesap · Katkılar · Dağıtımlar
  iç kip bölümleri     : + Bağlı işler · Satış kayıtları ·
                           Maliyet kayıtları
  ortak kipinde müşteri adı ve fatura no YOK (test ölçüyor)
  Excel raporu         : ciro/kâr sütunları dolu
  JS hatası            : yok

  159 test geçti (156 + 3 yeni kalıcı test);
  firma · js · form · zincir · akis · degismezlik temiz.

── YOL ÜSTÜNDE ──
  · `EXPORT_YETKI` tablosu FAIL-CLOSED: yeni modül yazılmazsa dışa
    aktarma 400 veriyor. Doğru davranış — 'ortaklik' yazıldı,
    yetkisi `karlilik`. Yetkisiz kullanıcı ne ekstreyi ne raporu
    alabiliyor; test ikisini de ölçüyor.
  · PDF çıktısı weasyprint/reportlab istiyor; sende kurulu. Test,
    kurulu değilse o adımı ATLIYOR — ortamın eksiğini modülün
    hatası gibi göstermesin.
  · Testlerimden biri OR3'ün kullandığı sipariş numarasıyla
    çakışıyordu (tek başına geçiyor, takımda düşüyordu). Kendi
    kimliklerine ayrıldı.

DOSYALAR
--------
  flask_app.py                    rapor dalı · ekstre rotası · yetki
  templates/ortaklik.html         Dışa Aktar · ekstre düğmeleri
  templates/ortaklik_ekstre_print.html   YENİ — ekstre sayfası
                                  (tam dosya, base64)
  tests/test_kritik.py            3 yeni test

Şema yok, göç yok.

KULLANIM
--------
  python3 yama_or9.py            # RAPOR
  python3 yama_or9.py --uygula
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
    'flask_app.py': "elif modul == 'ortaklik':",
    'templates/ortaklik.html': "function ekstreAc(kip)",
    'templates/ortaklik_ekstre_print.html': 'ORTAKLIK EKSTRESİ',
    'tests/test_kritik.py': 'def test_or9_ekstre_iki_kipte_calisiyor',
}
ONKOSUL = {
    'flask_app.py': 'def _ortaklik_kapsanan_stoklar():',
    'templates/ortaklik.html': 'ürün ortaklığa dahil',
    'tests/test_kritik.py': 'def test_or8_zincirle_kapsanan_stok_secilebilir_gorunmez',
}
TAM_YAZILAN = ['templates/ortaklik_ekstre_print.html']

DEGISIKLIKLER = [
    ('flask_app.py', 'OR9 · flask_app.py blok 1',
     r'''            d['sermaye_hareketleri'] = [
''',
     r'''            # OR9: ekstrede "bu maliyet katkıya alındı mı" sütunu.
            d['alinan_maliyetler'] = [
                s.maliyet_id for s in OrtaklikSermaye.query.filter(
                    OrtaklikSermaye.ortaklik_id == o.id,
                    OrtaklikSermaye.maliyet_id.isnot(None)).all()]
            d['sermaye_hareketleri'] = [
'''),
    ('flask_app.py', 'OR9 · flask_app.py blok 2',
     r'''        return jsonify({'ok': True, 'cari_hareket_id': ch.id})
''',
     r'''        return jsonify({'ok': True, 'cari_hareket_id': ch.id})

    @app.route('/ortaklik/<oid>/ekstre')
    def ortaklik_ekstre(oid):
        """OR9 · ORTAKLIK EKSTRESİ — yazdırılabilir hesap dökümü.

        İki kip:
          kip=ortak (varsayılan) — ortağa gönderilecek hâli. Hesabın
              tamamı: ciro, maliyet, vergi kalemleri, net kâr, iki
              tarafın payı ve katkısı, dağıtımlar, bakiye.
          kip=ic — yukarıdakinin üstüne bağlı işler, satış kayıtları
              ve maliyet kayıtları (fatura no'larıyla). Dışarı
              vermek için değil, kendi kontrolün için.

        Cari ekstresiyle aynı yol: yazdırılabilir sayfa, tarayıcıdan
        PDF'e basılıyor. Ayrı bir PDF makinesi kurmak, aynı belgenin
        iki ayrı yerde iki ayrı biçimde üretilmesiyle biterdi.
        """
        if _auth_required(): return _auth_required()
        if not _yetki_var_mi('karlilik', 'okuma'):
            return redirect(url_for('dashboard'))
        o = _ortaklik_bul(oid)
        if not o:
            return 'Ortaklık bulunamadı', 404
        kip = (request.args.get('kip') or 'ortak').lower().strip()
        if kip not in ('ortak', 'ic'):
            kip = 'ortak'
        hesap = _ortaklik_hesap(o)
        veri = _ortaklik_dict(o, hesap=True)
        if kip == 'ortak':
            # Maliyetten alinan katkinin aciklamasi ic referans
            # tasiyor: "Kesim / Fason / Üretim · MYT-26-01 · FSN-114".
            # Ortagin belgesinde maliyet kimligi ve FATURA NO isi
            # yok — kalemin NE OLDUGU yeter. (Test yakaladi.)
            for _s in veri.get('sermaye_hareketleri', []):
                _a = _s.get('aciklama') or ''
                if ' · ' in _a:
                    _s['aciklama'] = _a.split(' · ', 1)[0]
        satislar, isler = _ortaklik_satislari(o)
        return render_template(
            'ortaklik_ekstre_print.html', o=o, hesap=hesap, veri=veri,
            kip=kip, bugun=date.today(),
            firma_adi=((_fk.unvan or _fk.ad) if (_fk := _firma_kayit()) else ''),
            # İÇ KİPTE: ham kayıtlar. Ortak kipinde hiç gönderilmiyor —
            # şablonda gizlemek yerine veriyi hiç vermemek, yanlışlıkla
            # sızdırmayı imkânsız kılar.
            satislar=(satislar if kip == 'ic' else []),
            maliyetler=(_ortaklik_maliyet_kayitlari(o) if kip == 'ic' else []))
'''),
    ('flask_app.py', 'OR9 · flask_app.py blok 3',
     r'''        'maliyet': 'maliyet',
''',
     r'''        # OR9: ortaklik listesi kâr rakami tasiyor — `karlilik` yetkisi.
        'ortaklik': 'karlilik',
        'maliyet': 'maliyet',
'''),
    ('flask_app.py', 'OR9 · flask_app.py blok 4',
     r'''        else:
            return jsonify({'ok': False, 'mesaj': f'Bilinmeyen modül: {modul}'}), 400
''',
     r'''        elif modul == 'ortaklik':
            # OR9 · İŞ ORTAKLIKLARI RAPORU
            # Yetki `karlilik`e bağlı: liste kâr rakamı taşıyor.
            if not _yetki_var_mi('karlilik', 'okuma'):
                return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403
            baslik = 'İş Ortaklıkları'
            headers = ['Ortaklık', 'Ortak', 'Durum', 'İş', 'Ciro (USD)',
                       'Maliyet (USD)', 'Brüt kâr', 'Vergi', 'Net kâr',
                       'Bizim pay', 'Ortak pay', 'Ortak katkı', 'Bizim katkı',
                       'Ortağa ödenecek', 'Ortak bakiye']
            sayisal = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
            _top = {}
            for o in Ortaklik.query.order_by(
                    Ortaklik.baslangic.desc(), Ortaklik.id.desc()).all():
                h = _ortaklik_hesap(o)
                rows.append([
                    f'{o.id} · {o.ad}', o.ortak_ad or '', o.durum or '',
                    h['is_adedi'],
                    _f(h['ciro'], True), _f(h['maliyet'], True),
                    _f(h['brut_kar'], True), _f(h['vergi_toplam'], True),
                    _f(h['net_kar'], True),
                    _f(h['paylar']['biz'], True), _f(h['paylar']['ortak'], True),
                    _f(h['sermaye']['ortak'], True), _f(h['sermaye']['biz'], True),
                    _f(h['odenecek']['ortak'], True),
                    _f(h['bakiye']['ortak'], True)])
                for _k in ('ciro', 'brut_kar', 'net_kar'):
                    _top[_k] = _top.get(_k, 0) + h[_k]
                _top['ortak_bakiye'] = (_top.get('ortak_bakiye', 0)
                                        + h['bakiye']['ortak'])
            # Hesap USD üzerinden yapılıyor; özet de öyle.
            ozet_satirlari.append(('Toplam ciro (USD)', _f(_top.get('ciro', 0), True)))
            ozet_satirlari.append(('Toplam brüt kâr', _f(_top.get('brut_kar', 0), True)))
            ozet_satirlari.append(('Toplam net kâr', _f(_top.get('net_kar', 0), True)))
            ozet_satirlari.append(('Ortaklara kalan bakiye',
                                   _f(_top.get('ortak_bakiye', 0), True)))
            dosya = 'is_ortakliklari'

        else:
            return jsonify({'ok': False, 'mesaj': f'Bilinmeyen modül: {modul}'}), 400
'''),
    ('templates/ortaklik.html', 'OR9 · templates/ortaklik.html blok 1',
     r'''{% block title %}İş Ortaklıkları{% endblock %}
''',
     r'''{% block title %}İş Ortaklıkları{% endblock %}

{% block header_right %}
<div class="disa">
  <button class="disa-btn" onclick="disaAc(event, 'ortaklik')" title="Dışa aktar">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M12 3v12M8 11l4 4 4-4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2"/></svg>
    Dışa Aktar
  </button>
  <div class="disa-menu" id="disaMenu-ortaklik">
    <button onclick="disaAktar('ortaklik','xlsx')"><span style="background:#1D6F42">XLS</span> Excel indir</button>
    <button onclick="disaAktar('ortaklik','pdf')"><span style="background:#B23A2E">PDF</span> PDF indir</button>
  </div>
</div>
{% endblock %}
'''),
    ('templates/ortaklik.html', 'OR9 · templates/ortaklik.html blok 2',
     r'''  const eylem = `<button class="blok-btn" onclick="duzenleAc()">Düzenle</button>
    <button class="blok-btn" style="color:var(--kirmizi)" onclick="ortSil()">Sil</button>`;
  cekmeceAc(o.ad, `${o.id} · ${o.ortak_ad || 'ortak belirtilmedi'} · %${o.bizim_pay}/%${o.ortak_pay}`,
            govde, eylem);
''',
     r'''  const eylem = `<button class="blok-btn" onclick="ekstreAc('ortak')">Ekstre</button>
    <button class="blok-btn" onclick="ekstreAc('ic')">Ekstre (iç)</button>
    <button class="blok-btn" onclick="duzenleAc()">Düzenle</button>
    <button class="blok-btn" style="color:var(--kirmizi)" onclick="ortSil()">Sil</button>`;
  cekmeceAc(o.ad, `${o.id} · ${o.ortak_ad || 'ortak belirtilmedi'} · %${o.bizim_pay}/%${o.ortak_pay}`,
            govde, eylem);
}

/* Ekstre YENİ SEKMEDE açılır: çekmecedeki hesabı kaybetmeden
   yazdırabilesin diye. İki kip — ortağa gönderilecek hâli ve
   bağlı iş/kayıt dökümünü de gösteren iç kullanım hâli. */
function ekstreAc(kip) {
  if (!ACIK) return;
  window.open(`/ortaklik/${encodeURIComponent(ACIK.id)}/ekstre?kip=${kip}`,
              '_blank');
'''),
    ('tests/test_kritik.py', 'OR9 · tests/test_kritik.py blok 1',
     r'''    assert h['ciro'] == 3000 and h['satis_adedi'] == 1, h
''',
     r'''    assert h['ciro'] == 3000 and h['satis_adedi'] == 1, h


# ══════════════════════════════════════════════════════════════════════
#  OR9 · ORTAKLIK RAPORU VE EKSTRESİ
# ══════════════════════════════════════════════════════════════════════

def test_or9_ortaklik_raporu_excel_ve_pdf():
    """OR9: ortaklık listesi Excel/PDF olarak dışa aktarılabilmeli."""
    import io as _io, openpyxl as _ox
    _or1_kur('SIPOR9R', [(20000, 12000)])
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Rapor testi', 'ortak_ad': 'FINANSOR', 'bizim_pay': 60,
        'ortak_pay': 40}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR9R'})

    r = c.get('/api/export/ortaklik?format=xlsx')
    assert r.status_code == 200, r.status_code
    ws = _ox.load_workbook(_io.BytesIO(r.data)).active
    satirlar = [[x for x in row] for row in ws.iter_rows(values_only=True)]
    bizim = [s for s in satirlar if s and s[0] and oid in str(s[0])]
    assert bizim, satirlar[:4]
    # Ciro / brüt kâr sütunları dolu geliyor
    assert '20.000' in str(bizim[0][4]) or '20000' in str(bizim[0][4]), bizim[0]

    # PDF yolu weasyprint/reportlab ister. Kurulu değilse bu
    # ORTAMIN eksiği — modülün değil; yanlış alarm vermesin.
    try:
        import weasyprint  # noqa: F401
    except Exception:
        try:
            import reportlab  # noqa: F401
        except Exception:
            import pytest as _pytest
            _pytest.skip('PDF kütüphanesi kurulu değil')
    assert c.get('/api/export/ortaklik?format=pdf').status_code == 200


def test_or9_ekstre_iki_kipte_calisiyor():
    """OR9: ekstre iki kipte — ortağa gönderilecek ve iç kullanım.

    İç kipin verisi şablonda GİZLENMİYOR; sunucu ortak kipinde onu
    hiç göndermiyor. Gizlemek, şablonda bir koşul unutulduğunda
    müşteri adını ortağın belgesine basmakla biterdi."""
    from models import Maliyet
    _or1_kur('SIPOR9E', [(30000, 18000)])
    with fa.app.app_context():
        db.session.add(Maliyet(
            id='MYT-OR9', firma_id=1, baglanti_tip='siparis',
            baglanti_id='SIPOR9E', maliyet_tip='Kesim / Fason / Üretim',
            maliyet_tarihi=date(2026, 10, 5), tutar=2500, doviz='USD',
            usd_karsilik=2500, aktif=True, fatura_no='FSN-OR9'))
        db.session.commit()
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H, json={
        'ad': 'Ekstre testi', 'ortak_ad': 'FINANSOR', 'bizim_pay': 50,
        'ortak_pay': 50, 'anapara_yontemi': 'once_iade'}).get_json()['id']
    c.post(f'/api/ortaklik/{oid}/is', headers=H,
           json={'kaynak_tip': 'SIPARIS', 'kaynak_id': 'SIPOR9E'})
    c.post(f'/api/ortaklik/{oid}/maliyet_katki', headers=H, json={
        'taraf': 'biz', 'maliyet_idler': ['MYT-OR9']})

    # ── ORTAK KİPİ ──
    r = c.get(f'/ortaklik/{oid}/ekstre')
    assert r.status_code == 200, r.status_code
    g = r.get_data(as_text=True)
    assert 'ORTAKLIK EKSTRESİ' in g
    assert 'Brüt kâr' in g and 'Net kâr' in g
    assert '12000.00' in g.replace(',', '') or '12.000' in g  # brüt kâr
    # Müşteri adı ve fatura no ortağın belgesinde YOK
    assert 'ACIK CARI' not in g, 'müşteri adı ortak kipinde görünüyor'
    assert 'FSN-OR9' not in g, 'fatura no ortak kipinde görünüyor'
    assert 'İÇ KULLANIM' not in g

    # ── İÇ KİP ──
    r2 = c.get(f'/ortaklik/{oid}/ekstre?kip=ic')
    assert r2.status_code == 200
    g2 = r2.get_data(as_text=True)
    assert 'İÇ KULLANIM' in g2
    assert 'ACIK CARI' in g2, 'iç kipte satış kaydı yok'
    assert 'FSN-OR9' in g2, 'iç kipte maliyet kaydı yok'
    assert 'Bağlı işler' in g2

    # Geçersiz kip ortak kipine düşer (sızdırmaya yer bırakmaz)
    g3 = c.get(f'/ortaklik/{oid}/ekstre?kip=hebele').get_data(as_text=True)
    assert 'ACIK CARI' not in g3 and 'İÇ KULLANIM' not in g3


def test_or9_ekstre_yetki_ve_bulunamadi():
    """OR9: ekstre kâr rakamı taşıyor — yetkisiz göremez."""
    c = istemci('admin', 'ADMIN')
    oid = c.post('/api/ortaklik', headers=H,
                 json={'ad': 'Yetki'}).get_json()['id']
    assert c.get('/ortaklik/YOK-123/ekstre').status_code == 404

    d = istemci('depocu', 'DEPO')
    r = d.get(f'/ortaklik/{oid}/ekstre')
    assert r.status_code in (302, 403), r.status_code
    assert c.get('/api/export/ortaklik?format=xlsx').status_code == 200
    assert d.get('/api/export/ortaklik?format=xlsx').status_code == 403
'''),
]

TAM_ICERIK = {}

# ════════════════════════════════════════════════════════════════════
#  TAM DOSYA · templates/ortaklik_ekstre_print.html
#  Parça değil tam dosya; iç içe tırnak yığını üretmesin diye base64.
# ════════════════════════════════════════════════════════════════════
TAM_ICERIK = {
    'templates/ortaklik_ekstre_print.html': (
        'PCFET0NUWVBFIGh0bWw+CjxodG1sIGxhbmc9InRyIj4KPGhlYWQ+CiAgPG1ldGEgY2hh'
        'cnNldD0iVVRGLTgiPgogIDx0aXRsZT5PcnRha2zEsWsgRWtzdHJlc2kgLSB7eyBvLmFk'
        'IH19PC90aXRsZT4KICA8c3R5bGU+Ci8qIOKUgOKUgCBPUlRBS0xJSyBFS1NUUkVTxLAg'
        'KE9SOSkg4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA'
        '4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA'
        '4pSA4pSA4pSA4pSA4pSA4pSA4pSACiAgIENhcmkgZWtzdHJlc2l5bGUgYXluxLEgeW9s'
        'OiB5YXpkxLFyxLFsYWJpbGlyIHNheWZhLCB0YXJhecSxY8SxZGFuIFBERidlCiAgIGJh'
        'c8SxbMSxeW9yLiBBeXLEsSBiaXIgUERGIG1ha2luZXNpIGt1cm1haywgYXluxLEgYmVs'
        'Z2VuaW4gaWtpIHllcmRlCiAgIGlraSBheXLEsSBiacOnaW1kZSDDvHJldGlsbWVzaXls'
        'ZSBiaXRlcmRpLgoKICAgxLBLxLAgS8SwUDogYG9ydGFrYCBvcnRhxJ9hIGfDtm5kZXJp'
        'bGlyLCBgaWNgIGtlbmRpIGtvbnRyb2zDvG4gacOnaW4KICAgYmHEn2zEsSBpxZ9sZXJp'
        'IHZlIGhhbSBrYXnEsXRsYXLEsSBkYSBnw7ZzdGVyaXIuIMSww6cga2lwaW4gdmVyaXNp'
        'CiAgIMWfYWJsb25kYSBHxLBaTEVOTcSwWU9SIOKAlCBzdW51Y3Ugb3J0YWsga2lwaW5k'
        'ZSBvbnUgaGnDpyBnw7ZuZGVybWl5b3IsCiAgIGLDtnlsZWNlIHlhbmzEscWfbMSxa2xh'
        'IHPEsXpkxLFybWFrIGlta8OibnPEsXouICovCiAgICA6cm9vdCB7IC0tdGV4dC1tYWlu'
        'OiMyMzI4MjQ7IC0tYm9yZGVyOiNiZGMzYzc7IC0tZGFuZ2VyOiNBOTQ0Mzg7CiAgICAg'
        'ICAgICAgIC0tc3VjY2VzczojNEE1RDRFOyAtLWFjY2VudDojQzA1QTM2OyB9CiAgICBi'
        'b2R5IHsgZm9udC1mYW1pbHk6J1NlZ29lIFVJJyxUYWhvbWEsR2VuZXZhLFZlcmRhbmEs'
        'c2Fucy1zZXJpZjsKICAgICAgICAgICBjb2xvcjp2YXIoLS10ZXh0LW1haW4pOyBmb250'
        'LXNpemU6MTJweDsgbGluZS1oZWlnaHQ6MS40NTsKICAgICAgICAgICBiYWNrZ3JvdW5k'
        'OiNmZmY7IG1hcmdpbjowOyBwYWRkaW5nOjMwcHg7IH0KICAgIEBtZWRpYSBwcmludCB7'
        'CiAgICAgIGJvZHkgeyBwYWRkaW5nOjA7IH0KICAgICAgLm5vLXByaW50IHsgZGlzcGxh'
        'eTpub25lICFpbXBvcnRhbnQ7IH0KICAgICAgdGFibGUgeyBwYWdlLWJyZWFrLWluc2lk'
        'ZTphdXRvOyB9CiAgICAgIHRyIHsgcGFnZS1icmVhay1pbnNpZGU6YXZvaWQ7IHBhZ2Ut'
        'YnJlYWstYWZ0ZXI6YXV0bzsgfQogICAgICB0aGVhZCB7IGRpc3BsYXk6dGFibGUtaGVh'
        'ZGVyLWdyb3VwOyB9CiAgICAgIC50ZXh0LWRhbmdlciB7IGNvbG9yOiNBOTQ0MzggIWlt'
        'cG9ydGFudDsgLXdlYmtpdC1wcmludC1jb2xvci1hZGp1c3Q6ZXhhY3Q7IHByaW50LWNv'
        'bG9yLWFkanVzdDpleGFjdDsgfQogICAgICAudGV4dC1zdWNjZXNzIHsgY29sb3I6IzRB'
        'NUQ0RSAhaW1wb3J0YW50OyAtd2Via2l0LXByaW50LWNvbG9yLWFkanVzdDpleGFjdDsg'
        'cHJpbnQtY29sb3ItYWRqdXN0OmV4YWN0OyB9CiAgICAgIHRoIHsgYmFja2dyb3VuZC1j'
        'b2xvcjojZjJmMmYyICFpbXBvcnRhbnQ7IC13ZWJraXQtcHJpbnQtY29sb3ItYWRqdXN0'
        'OmV4YWN0OyBwcmludC1jb2xvci1hZGp1c3Q6ZXhhY3Q7IH0KICAgICAgLmhlc2FwIC5z'
        'b251YyB7IGJhY2tncm91bmQ6I0YwRjRGMCAhaW1wb3J0YW50OyAtd2Via2l0LXByaW50'
        'LWNvbG9yLWFkanVzdDpleGFjdDsgcHJpbnQtY29sb3ItYWRqdXN0OmV4YWN0OyB9CiAg'
        'ICB9CiAgICAuaGVhZGVyIHsgZGlzcGxheTpmbGV4OyBqdXN0aWZ5LWNvbnRlbnQ6c3Bh'
        'Y2UtYmV0d2VlbjsgYWxpZ24taXRlbXM6ZmxleC1zdGFydDsKICAgICAgICAgICAgICBi'
        'b3JkZXItYm90dG9tOjJweCBzb2xpZCB2YXIoLS1hY2NlbnQpOyBwYWRkaW5nLWJvdHRv'
        'bToxMHB4OyBtYXJnaW4tYm90dG9tOjIwcHg7IH0KICAgIC5maXJtYS1pbmZvIGgxIHsg'
        'bWFyZ2luOjAgMCA1cHggMDsgZm9udC1zaXplOjIycHg7IHRleHQtdHJhbnNmb3JtOnVw'
        'cGVyY2FzZTsKICAgICAgICAgICAgICAgICAgICAgbGV0dGVyLXNwYWNpbmc6MXB4OyB9'
        'CiAgICAuZmlybWEtaW5mbyBwIHsgbWFyZ2luOjA7IGNvbG9yOiM1NTU7IH0KICAgIC5i'
        'ZWxnZS1pbmZvIHsgdGV4dC1hbGlnbjpyaWdodDsgfQogICAgLmJlbGdlLWluZm8gaDIg'
        'eyBtYXJnaW46MCAwIDVweCAwOyBmb250LXNpemU6MThweDsgfQogICAgLmJlbGdlLWlu'
        'Zm8gcCB7IG1hcmdpbjowOyBjb2xvcjojNTU1OyBmb250LXdlaWdodDo2MDA7IH0KICAg'
        'IC5pbmZvLWdyaWQgeyBkaXNwbGF5OmZsZXg7IGp1c3RpZnktY29udGVudDpzcGFjZS1i'
        'ZXR3ZWVuOyBtYXJnaW4tYm90dG9tOjIwcHg7IGdhcDoyMHB4OyB9CiAgICAuaW5mby1i'
        'b3ggeyBmbGV4OjE7IGJvcmRlcjoxcHggc29saWQgdmFyKC0tYm9yZGVyKTsgYm9yZGVy'
        'LXJhZGl1czo2cHg7IHBhZGRpbmc6MTJweDsgfQogICAgLmluZm8tYm94IGgzIHsgbWFy'
        'Z2luOjAgMCAxMHB4IDA7IGZvbnQtc2l6ZToxNHB4OyBib3JkZXItYm90dG9tOjFweCBz'
        'b2xpZCAjZWVlOwogICAgICAgICAgICAgICAgICAgcGFkZGluZy1ib3R0b206NXB4OyBj'
        'b2xvcjp2YXIoLS1zdWNjZXNzKTsgfQogICAgLmluZm8tcm93IHsgZGlzcGxheTpmbGV4'
        'OyBtYXJnaW4tYm90dG9tOjVweDsgfQogICAgLmluZm8tbGFiZWwgeyBmb250LXdlaWdo'
        'dDpib2xkOyBjb2xvcjojNTU1OyB3aWR0aDoxMzBweDsgfQogICAgLmluZm8tdmFsdWUg'
        'eyBmbGV4OjE7IGZvbnQtd2VpZ2h0OjYwMDsgfQogICAgLm96ZXQtYm94IHsgZmxleDow'
        'IDAgMjgwcHg7IGJhY2tncm91bmQ6I0ZBRjdGMjsgYm9yZGVyOjFweCBzb2xpZCB2YXIo'
        'LS1ib3JkZXIpOwogICAgICAgICAgICAgICAgYm9yZGVyLXJhZGl1czo2cHg7IHBhZGRp'
        'bmc6MTJweDsgfQogICAgLm96ZXQtYm94IGgzIHsgbWFyZ2luOjAgMCAxMHB4IDA7IGZv'
        'bnQtc2l6ZToxNHB4OyBib3JkZXItYm90dG9tOjFweCBzb2xpZCAjZTBlMGUwOwogICAg'
        'ICAgICAgICAgICAgICAgcGFkZGluZy1ib3R0b206NXB4OyB0ZXh0LWFsaWduOmNlbnRl'
        'cjsgY29sb3I6dmFyKC0tc3VjY2Vzcyk7IH0KICAgIC5vemV0LXJvdyB7IGRpc3BsYXk6'
        'ZmxleDsganVzdGlmeS1jb250ZW50OnNwYWNlLWJldHdlZW47IG1hcmdpbi1ib3R0b206'
        'OHB4OwogICAgICAgICAgICAgICAgZm9udC1zaXplOjEzcHg7IGZvbnQtd2VpZ2h0OmJv'
        'bGQ7IH0KCiAgICBoMy5ib2x1bSB7IGZvbnQtc2l6ZToxM3B4OyB0ZXh0LXRyYW5zZm9y'
        'bTp1cHBlcmNhc2U7IGxldHRlci1zcGFjaW5nOi41cHg7CiAgICAgICAgICAgICAgIGNv'
        'bG9yOnZhcigtLXN1Y2Nlc3MpOyBib3JkZXItYm90dG9tOjFweCBzb2xpZCAjZWVlOyBw'
        'YWRkaW5nLWJvdHRvbTo0cHg7CiAgICAgICAgICAgICAgIG1hcmdpbjoyMnB4IDAgOHB4'
        'OyB9CiAgICB0YWJsZSB7IHdpZHRoOjEwMCU7IGJvcmRlci1jb2xsYXBzZTpjb2xsYXBz'
        'ZTsgbWFyZ2luLWJvdHRvbToxOHB4OyBmb250LXNpemU6MTFweDsgfQogICAgdGgsIHRk'
        'IHsgcGFkZGluZzo2cHggOHB4OyBib3JkZXI6MXB4IHNvbGlkIHZhcigtLWJvcmRlcik7'
        'IHRleHQtYWxpZ246bGVmdDsgfQogICAgdGggeyBiYWNrZ3JvdW5kOiNmMmYyZjI7IGZv'
        'bnQtd2VpZ2h0OmJvbGQ7IHRleHQtdHJhbnNmb3JtOnVwcGVyY2FzZTsgY29sb3I6IzMz'
        'MzsgfQogICAgdGQubnVtIHsgdGV4dC1hbGlnbjpyaWdodDsgZm9udC13ZWlnaHQ6Ym9s'
        'ZDsgZm9udC12YXJpYW50LW51bWVyaWM6dGFidWxhci1udW1zOyB9CgogICAgLyogSGVz'
        'YXAgemluY2lyaSDigJQgZWtyYW5kYWtpIGTDtmvDvG3DvG4gYXluxLFzxLEgKi8KICAg'
        'IC5oZXNhcCB7IGJvcmRlcjoxcHggc29saWQgdmFyKC0tYm9yZGVyKTsgYm9yZGVyLXJh'
        'ZGl1czo2cHg7IG1hcmdpbi1ib3R0b206MThweDsgfQogICAgLmhlc2FwIC5zYXRpciB7'
        'IGRpc3BsYXk6ZmxleDsgcGFkZGluZzo3cHggMTRweDsgfQogICAgLmhlc2FwIC5zYXRp'
        'ciAuZXQgeyBmbGV4OjE7IH0KICAgIC5oZXNhcCAuc2F0aXIgLnR0IHsgZm9udC13ZWln'
        'aHQ6Ym9sZDsgZm9udC12YXJpYW50LW51bWVyaWM6dGFidWxhci1udW1zOwogICAgICAg'
        'ICAgICAgICAgICAgICAgICB3aGl0ZS1zcGFjZTpub3dyYXA7IH0KICAgIC5oZXNhcCAu'
        'c2F0aXIuYWx0IHsgcGFkZGluZy1sZWZ0OjMwcHg7IGZvbnQtc2l6ZToxMXB4OyBjb2xv'
        'cjojNTU1OyB9CiAgICAuaGVzYXAgLnNhdGlyLmthbGluIHsgYm9yZGVyLXRvcDoxcHgg'
        'c29saWQgdmFyKC0tYm9yZGVyKTsgZm9udC13ZWlnaHQ6Ym9sZDsgfQogICAgLmhlc2Fw'
        'IC5zYXRpci5zb251YyB7IGJhY2tncm91bmQ6I0YwRjRGMDsgZm9udC13ZWlnaHQ6Ym9s'
        'ZDsgfQogICAgLmhlc2FwIC5la3NpIC50dCB7IGNvbG9yOnZhcigtLWRhbmdlcik7IH0K'
        'ICAgIC51eWFyaSB7IGJvcmRlcjoxcHggc29saWQgI0UwQTUyNjsgYmFja2dyb3VuZDoj'
        'RkZGNkU1OyBib3JkZXItcmFkaXVzOjZweDsKICAgICAgICAgICAgIHBhZGRpbmc6OXB4'
        'IDEycHg7IG1hcmdpbi1ib3R0b206MTBweDsgZm9udC1zaXplOjExcHg7IH0KICAgIC5k'
        'aXBub3QgeyBtYXJnaW4tdG9wOjI2cHg7IHBhZGRpbmctdG9wOjEwcHg7IGJvcmRlci10'
        'b3A6MXB4IHNvbGlkICNlZWU7CiAgICAgICAgICAgICAgZm9udC1zaXplOjEwcHg7IGNv'
        'bG9yOiM3Nzc7IGxpbmUtaGVpZ2h0OjEuNjsgfQogICAgLnByaW50LWJ0biB7IHBhZGRp'
        'bmc6MTBweCAyMHB4OyBiYWNrZ3JvdW5kOiMyMzI4MjQ7IGNvbG9yOiNmZmY7IGJvcmRl'
        'cjpub25lOwogICAgICAgICAgICAgICAgIGJvcmRlci1yYWRpdXM6NHB4OyBjdXJzb3I6'
        'cG9pbnRlcjsgZm9udC1zaXplOjE0cHg7IGZvbnQtd2VpZ2h0OmJvbGQ7CiAgICAgICAg'
        'ICAgICAgICAgcG9zaXRpb246Zml4ZWQ7IGJvdHRvbToyMHB4OyByaWdodDoyMHB4Owog'
        'ICAgICAgICAgICAgICAgIGJveC1zaGFkb3c6MCA0cHggNnB4IHJnYmEoMCwwLDAsLjEp'
        'OyB9CiAgICAvKiBZYXpkxLFyIGTDvMSfbWVzaW5pbiDDnFNUw5xOREU6IHlhbiB5YW5h'
        'IGtveXVuY2Egw7xzdCDDvHN0ZSBiaW5peW9yZHUKICAgICAgIChkw7zEn21lIGdlbmnF'
        'nywgc2FiaXQgYmlyIHNhxJ8gYm/Fn2x1ayB5ZXRtaXlvcikuICovCiAgICAua2lwLXNl'
        'YyB7IHBvc2l0aW9uOmZpeGVkOyBib3R0b206NjhweDsgcmlnaHQ6MjBweDsgZm9udC1z'
        'aXplOjEycHg7CiAgICAgICAgICAgICAgIGJhY2tncm91bmQ6I2ZmZjsgYm9yZGVyOjFw'
        'eCBzb2xpZCB2YXIoLS1ib3JkZXIpOyBib3JkZXItcmFkaXVzOjRweDsKICAgICAgICAg'
        'ICAgICAgcGFkZGluZzo5cHggMTRweDsgfQogICAgLmtpcC1zZWMgYSB7IGNvbG9yOnZh'
        'cigtLWFjY2VudCk7IGZvbnQtd2VpZ2h0OmJvbGQ7IHRleHQtZGVjb3JhdGlvbjpub25l'
        'OyB9CiAgPC9zdHlsZT4KPC9oZWFkPgo8Ym9keT4KPGJ1dHRvbiBjbGFzcz0icHJpbnQt'
        'YnRuIG5vLXByaW50IiBvbmNsaWNrPSJ3aW5kb3cucHJpbnQoKSI+U2F5ZmF5xLEgWWF6'
        'ZMSxciAvIFBERiBPbGFyYWsgS2F5ZGV0PC9idXR0b24+CjxkaXYgY2xhc3M9ImtpcC1z'
        'ZWMgbm8tcHJpbnQiPgogIHslIGlmIGtpcCA9PSAnaWMnICV9CiAgICDEsMOnIGt1bGxh'
        'bsSxbSBraXBpIMK3IDxhIGhyZWY9Ij9raXA9b3J0YWsiPm9ydGHEn2EgZ8O2bmRlcmls'
        'ZWNlayBow6JsaTwvYT4KICB7JSBlbHNlICV9CiAgICBPcnRhayBraXBpIMK3IDxhIGhy'
        'ZWY9Ij9raXA9aWMiPmnDpyBrdWxsYW7EsW0gaMOibGk8L2E+CiAgeyUgZW5kaWYgJX0K'
        'PC9kaXY+Cgo8ZGl2IGNsYXNzPSJoZWFkZXIiPgogIDxkaXYgY2xhc3M9ImZpcm1hLWlu'
        'Zm8iPgogICAgPGgxPnt7IGZpcm1hX2FkaSBvciAnTWlsZXN0b25lJyB9fTwvaDE+CiAg'
        'ICA8cD7EsMWfIE9ydGFrbMSxxJ/EsSBIZXNhcCBEw7Zrw7xtw7w8L3A+CiAgPC9kaXY+'
        'CiAgPGRpdiBjbGFzcz0iYmVsZ2UtaW5mbyI+CiAgICA8aDI+T1JUQUtMSUsgRUtTVFJF'
        'U8SwPC9oMj4KICAgIDxwPnt7IG8uaWQgfX08L3A+CiAgICA8cCBzdHlsZT0iZm9udC13'
        'ZWlnaHQ6bm9ybWFsIj57eyBidWd1bi5zdHJmdGltZSgnJWQuJW0uJVknKSB9fTwvcD4K'
        'ICAgIHslIGlmIGtpcCA9PSAnaWMnICV9PHAgc3R5bGU9ImNvbG9yOnZhcigtLWRhbmdl'
        'cikiPsSww4cgS1VMTEFOSU08L3A+eyUgZW5kaWYgJX0KICA8L2Rpdj4KPC9kaXY+Cgo8'
        'ZGl2IGNsYXNzPSJpbmZvLWdyaWQiPgogIDxkaXYgY2xhc3M9ImluZm8tYm94Ij4KICAg'
        'IDxoMz5PcnRha2zEsWs8L2gzPgogICAgPGRpdiBjbGFzcz0iaW5mby1yb3ciPjxzcGFu'
        'IGNsYXNzPSJpbmZvLWxhYmVsIj5BZDo8L3NwYW4+CiAgICAgIDxzcGFuIGNsYXNzPSJp'
        'bmZvLXZhbHVlIj57eyBvLmFkIH19PC9zcGFuPjwvZGl2PgogICAgPGRpdiBjbGFzcz0i'
        'aW5mby1yb3ciPjxzcGFuIGNsYXNzPSJpbmZvLWxhYmVsIj5PcnRhazo8L3NwYW4+CiAg'
        'ICAgIDxzcGFuIGNsYXNzPSJpbmZvLXZhbHVlIj57eyBvLm9ydGFrX2FkIG9yICfigJQn'
        'IH19PC9zcGFuPjwvZGl2PgogICAgPGRpdiBjbGFzcz0iaW5mby1yb3ciPjxzcGFuIGNs'
        'YXNzPSJpbmZvLWxhYmVsIj5QYXkgZGHEn8SxbMSxbcSxOjwvc3Bhbj4KICAgICAgPHNw'
        'YW4gY2xhc3M9ImluZm8tdmFsdWUiPkJpeiAle3sgaGVzYXAuYml6aW1fcGF5IH19IMK3'
        'IE9ydGFrICV7eyBoZXNhcC5vcnRha19wYXkgfX08L3NwYW4+PC9kaXY+CiAgICA8ZGl2'
        'IGNsYXNzPSJpbmZvLXJvdyI+PHNwYW4gY2xhc3M9ImluZm8tbGFiZWwiPkFuYXBhcmEg'
        'ecO2bnRlbWk6PC9zcGFuPgogICAgICA8c3BhbiBjbGFzcz0iaW5mby12YWx1ZSI+e3sg'
        'J8OWbmNlIGlhZGUsIHNvbnJhIGvDonIgcGF5bGHFn8SxbcSxJwogICAgICAgIGlmIGhl'
        'c2FwLmFuYXBhcmFfeW9udGVtaSA9PSAnb25jZV9pYWRlJyBlbHNlICdBeXLEsSB0YWtp'
        'cCcgfX08L3NwYW4+PC9kaXY+CiAgICA8ZGl2IGNsYXNzPSJpbmZvLXJvdyI+PHNwYW4g'
        'Y2xhc3M9ImluZm8tbGFiZWwiPkJhxZ9sYW5nxLHDpzo8L3NwYW4+CiAgICAgIDxzcGFu'
        'IGNsYXNzPSJpbmZvLXZhbHVlIiBzdHlsZT0iZm9udC13ZWlnaHQ6bm9ybWFsIj4KICAg'
        'ICAgICB7eyBvLmJhc2xhbmdpYy5zdHJmdGltZSgnJWQuJW0uJVknKSBpZiBvLmJhc2xh'
        'bmdpYyBlbHNlICfigJQnIH19PC9zcGFuPjwvZGl2PgogICAgPGRpdiBjbGFzcz0iaW5m'
        'by1yb3ciPjxzcGFuIGNsYXNzPSJpbmZvLWxhYmVsIj5QYXJhIGJpcmltaTo8L3NwYW4+'
        'CiAgICAgIDxzcGFuIGNsYXNzPSJpbmZvLXZhbHVlIj57eyBoZXNhcC5wYXJhX2Jpcmlt'
        'aSBvciAnVVNEJyB9fTwvc3Bhbj48L2Rpdj4KICA8L2Rpdj4KICA8ZGl2IGNsYXNzPSJv'
        'emV0LWJveCI+CiAgICA8aDM+w5Z6ZXQ8L2gzPgogICAgPGRpdiBjbGFzcz0ib3pldC1y'
        'b3ciPjxzcGFuPk5ldCBrw6JyOjwvc3Bhbj4KICAgICAgPHNwYW4gY2xhc3M9InRleHQt'
        'c3VjY2VzcyI+e3sgJyUuMmYnfGZvcm1hdChoZXNhcC5uZXRfa2FyKSB9fTwvc3Bhbj48'
        'L2Rpdj4KICAgIDxkaXYgY2xhc3M9Im96ZXQtcm93Ij48c3Bhbj5PcnRhxJ/EsW4gcGF5'
        'xLE6PC9zcGFuPgogICAgICA8c3Bhbj57eyAnJS4yZid8Zm9ybWF0KGhlc2FwLnBheWxh'
        'ci5vcnRhaykgfX08L3NwYW4+PC9kaXY+CiAgICA8ZGl2IGNsYXNzPSJvemV0LXJvdyI+'
        'PHNwYW4+T3J0YcSfxLFuIGthdGvEsXPEsTo8L3NwYW4+CiAgICAgIDxzcGFuPnt7ICcl'
        'LjJmJ3xmb3JtYXQoaGVzYXAua2FsYW5fYW5hcGFyYS5vcnRhaykgfX08L3NwYW4+PC9k'
        'aXY+CiAgICA8ZGl2IGNsYXNzPSJvemV0LXJvdyI+PHNwYW4+RGHEn8SxdMSxbGFuOjwv'
        'c3Bhbj4KICAgICAgPHNwYW4+e3sgJyUuMmYnfGZvcm1hdChoZXNhcC5kYWdpdGlsYW4u'
        'b3J0YWspIH19PC9zcGFuPjwvZGl2PgogICAgPGRpdiBjbGFzcz0ib3pldC1yb3ciIHN0'
        'eWxlPSJib3JkZXItdG9wOjJweCBzb2xpZCAjY2NjO3BhZGRpbmctdG9wOjhweDsKICAg'
        'ICAgICAgbWFyZ2luLXRvcDo4cHg7Zm9udC1zaXplOjE0cHgiPgogICAgICA8c3Bhbj5P'
        'cnRhxJ9hIGthbGFuOjwvc3Bhbj4KICAgICAgPHNwYW4gY2xhc3M9Int7ICd0ZXh0LWRh'
        'bmdlcicgaWYgaGVzYXAuYmFraXllLm9ydGFrID4gMCBlbHNlICd0ZXh0LXN1Y2Nlc3Mn'
        'IH19Ij4KICAgICAgICB7eyAnJS4yZid8Zm9ybWF0KGhlc2FwLmJha2l5ZS5vcnRhaykg'
        'fX0ge3sgaGVzYXAucGFyYV9iaXJpbWkgb3IgJ1VTRCcgfX08L3NwYW4+PC9kaXY+CiAg'
        'PC9kaXY+CjwvZGl2PgoKeyUgZm9yIHUgaW4gaGVzYXAudXlhcmlsYXIgJX08ZGl2IGNs'
        'YXNzPSJ1eWFyaSI+4pqgIHt7IHUgfX08L2Rpdj57JSBlbmRmb3IgJX0KCjxoMyBjbGFz'
        'cz0iYm9sdW0iPkhlc2FwPC9oMz4KPGRpdiBjbGFzcz0iaGVzYXAiPgogIDxkaXYgY2xh'
        'c3M9InNhdGlyIj48c3BhbiBjbGFzcz0iZXQiPkNpcm8gKHt7IGhlc2FwLnNhdGlzX2Fk'
        'ZWRpIH19IHNhdMSxxZ8ga2F5ZMSxKTwvc3Bhbj4KICAgIDxzcGFuIGNsYXNzPSJ0dCI+'
        'e3sgJyUuMmYnfGZvcm1hdChoZXNhcC5jaXJvKSB9fTwvc3Bhbj48L2Rpdj4KICA8ZGl2'
        'IGNsYXNzPSJzYXRpciBla3NpIj48c3BhbiBjbGFzcz0iZXQiPk1hbGl5ZXQ8L3NwYW4+'
        'CiAgICA8c3BhbiBjbGFzcz0idHQiPuKIkiB7eyAnJS4yZid8Zm9ybWF0KGhlc2FwLm1h'
        'bGl5ZXQpIH19PC9zcGFuPjwvZGl2PgogIDxkaXYgY2xhc3M9InNhdGlyIGthbGluIj48'
        'c3BhbiBjbGFzcz0iZXQiPkJyw7x0IGvDonI8L3NwYW4+CiAgICA8c3BhbiBjbGFzcz0i'
        'dHQiPnt7ICclLjJmJ3xmb3JtYXQoaGVzYXAuYnJ1dF9rYXIpIH19PC9zcGFuPjwvZGl2'
        'PgogIHslIGZvciB2IGluIGhlc2FwLnZlcmdpbGVyICV9CiAgPGRpdiBjbGFzcz0ic2F0'
        'aXIgYWx0IGVrc2kiPjxzcGFuIGNsYXNzPSJldCI+e3sgdi5hZCB9fXslIGlmIHYubWF0'
        'cmFoX3RpcGkgPT0gJ3NhYml0JyAlfQogICAgICAoc2FiaXQpeyUgZWxzZSAlfSAoJXt7'
        'IHYub3JhbiB9fSDDlyB7eyAnY2lybycgaWYgdi5tYXRyYWhfdGlwaSA9PSAnY2lybycg'
        'ZWxzZSAnYnLDvHQga8OicicgfX0peyUgZW5kaWYgJX17JQogICAgICBpZiB2LmR1cnVt'
        'ID09ICd0YWhtaW5pJyAlfSDCtyB0YWhtaW5peyUgZW5kaWYgJX08L3NwYW4+CiAgICA8'
        'c3BhbiBjbGFzcz0idHQiPuKIkiB7eyAnJS4yZid8Zm9ybWF0KHYudHV0YXIpIH19PC9z'
        'cGFuPjwvZGl2PgogIHslIGVsc2UgJX0KICA8ZGl2IGNsYXNzPSJzYXRpciBhbHQiPjxz'
        'cGFuIGNsYXNzPSJldCI+dmVyZ2kga2FsZW1pIHlvazwvc3Bhbj48c3BhbiBjbGFzcz0i'
        'dHQiPuKAlDwvc3Bhbj48L2Rpdj4KICB7JSBlbmRmb3IgJX0KICA8ZGl2IGNsYXNzPSJz'
        'YXRpciBrYWxpbiBzb251YyI+PHNwYW4gY2xhc3M9ImV0Ij5OZXQga8Oicjwvc3Bhbj4K'
        'ICAgIDxzcGFuIGNsYXNzPSJ0dCI+e3sgJyUuMmYnfGZvcm1hdChoZXNhcC5uZXRfa2Fy'
        'KSB9fTwvc3Bhbj48L2Rpdj4KICA8ZGl2IGNsYXNzPSJzYXRpciBhbHQiPjxzcGFuIGNs'
        'YXNzPSJldCI+Qml6aW0gcGF5ICgle3sgaGVzYXAuYml6aW1fcGF5IH19KTwvc3Bhbj4K'
        'ICAgIDxzcGFuIGNsYXNzPSJ0dCI+e3sgJyUuMmYnfGZvcm1hdChoZXNhcC5wYXlsYXIu'
        'Yml6KSB9fTwvc3Bhbj48L2Rpdj4KICA8ZGl2IGNsYXNzPSJzYXRpciBhbHQiPjxzcGFu'
        'IGNsYXNzPSJldCI+T3J0YWsgcGF5ICgle3sgaGVzYXAub3J0YWtfcGF5IH19KTwvc3Bh'
        'bj4KICAgIDxzcGFuIGNsYXNzPSJ0dCI+e3sgJyUuMmYnfGZvcm1hdChoZXNhcC5wYXls'
        'YXIub3J0YWspIH19PC9zcGFuPjwvZGl2PgogIHslIGlmIGhlc2FwLmFuYXBhcmFfeW9u'
        'dGVtaSA9PSAnb25jZV9pYWRlJyAlfQogIDxkaXYgY2xhc3M9InNhdGlyIGFsdCI+PHNw'
        'YW4gY2xhc3M9ImV0Ij5PcnRhxJ/EsW4gaWFkZSBlZGlsZWNlayBrYXRrxLFzxLE8L3Nw'
        'YW4+CiAgICA8c3BhbiBjbGFzcz0idHQiPnt7ICclLjJmJ3xmb3JtYXQoaGVzYXAua2Fs'
        'YW5fYW5hcGFyYS5vcnRhaykgfX08L3NwYW4+PC9kaXY+CiAgeyUgZW5kaWYgJX0KICA8'
        'ZGl2IGNsYXNzPSJzYXRpciBrYWxpbiI+PHNwYW4gY2xhc3M9ImV0Ij5PcnRhxJ9hIMO2'
        'ZGVuZWNlazwvc3Bhbj4KICAgIDxzcGFuIGNsYXNzPSJ0dCI+e3sgJyUuMmYnfGZvcm1h'
        'dChoZXNhcC5vZGVuZWNlay5vcnRhaykgfX08L3NwYW4+PC9kaXY+CiAgPGRpdiBjbGFz'
        'cz0ic2F0aXIgYWx0Ij48c3BhbiBjbGFzcz0iZXQiPsWeaW1kaXllIGthZGFyIGRhxJ/E'
        'sXTEsWxhbjwvc3Bhbj4KICAgIDxzcGFuIGNsYXNzPSJ0dCI+e3sgJyUuMmYnfGZvcm1h'
        'dChoZXNhcC5kYWdpdGlsYW4ub3J0YWspIH19PC9zcGFuPjwvZGl2PgogIDxkaXYgY2xh'
        'c3M9InNhdGlyIGthbGluIj48c3BhbiBjbGFzcz0iZXQiPk9ydGFrIGJha2l5ZSAoa2Fs'
        'YW4pPC9zcGFuPgogICAgPHNwYW4gY2xhc3M9InR0Ij57eyAnJS4yZid8Zm9ybWF0KGhl'
        'c2FwLmJha2l5ZS5vcnRhaykgfX08L3NwYW4+PC9kaXY+CiAgeyUgaWYgaGVzYXAuc2Vy'
        'bWF5ZS5iaXogb3IgaGVzYXAuZGFnaXRpbGFuLmJpeiAlfQogIDxkaXYgY2xhc3M9InNh'
        'dGlyIGthbGluIj48c3BhbiBjbGFzcz0iZXQiPkJpemltIHRhcmFmxLFtxLF6PC9zcGFu'
        'PjxzcGFuIGNsYXNzPSJ0dCI+PC9zcGFuPjwvZGl2PgogIHslIGlmIGhlc2FwLmFuYXBh'
        'cmFfeW9udGVtaSA9PSAnb25jZV9pYWRlJyAlfQogIDxkaXYgY2xhc3M9InNhdGlyIGFs'
        'dCI+PHNwYW4gY2xhc3M9ImV0Ij5CaXppbSBpYWRlIGVkaWxlY2VrIGthdGvEsW3EsXo8'
        'L3NwYW4+CiAgICA8c3BhbiBjbGFzcz0idHQiPnt7ICclLjJmJ3xmb3JtYXQoaGVzYXAu'
        'a2FsYW5fYW5hcGFyYS5iaXopIH19PC9zcGFuPjwvZGl2PgogIHslIGVuZGlmICV9CiAg'
        'PGRpdiBjbGFzcz0ic2F0aXIgYWx0Ij48c3BhbiBjbGFzcz0iZXQiPkJpemUgw7ZkZW5l'
        'Y2VrPC9zcGFuPgogICAgPHNwYW4gY2xhc3M9InR0Ij57eyAnJS4yZid8Zm9ybWF0KGhl'
        'c2FwLm9kZW5lY2VrLmJpeikgfX08L3NwYW4+PC9kaXY+CiAgPGRpdiBjbGFzcz0ic2F0'
        'aXIgYWx0Ij48c3BhbiBjbGFzcz0iZXQiPkJpemltIGJha2l5ZTwvc3Bhbj4KICAgIDxz'
        'cGFuIGNsYXNzPSJ0dCI+e3sgJyUuMmYnfGZvcm1hdChoZXNhcC5iYWtpeWUuYml6KSB9'
        'fTwvc3Bhbj48L2Rpdj4KICB7JSBlbmRpZiAlfQo8L2Rpdj4KCjxoMyBjbGFzcz0iYm9s'
        'dW0iPkthdGvEsWxhcjwvaDM+Cjx0YWJsZT4KICA8dGhlYWQ+PHRyPjx0aD5UYXJhZjwv'
        'dGg+PHRoPkhhcmVrZXQ8L3RoPjx0aD5UYXJpaDwvdGg+PHRoPkHDp8Sxa2xhbWE8L3Ro'
        'PgogICAgPHRoIHN0eWxlPSJ0ZXh0LWFsaWduOnJpZ2h0Ij5UdXRhcjwvdGg+PHRoIHN0'
        'eWxlPSJ0ZXh0LWFsaWduOnJpZ2h0Ij5VU0Q8L3RoPjwvdHI+PC90aGVhZD4KICA8dGJv'
        'ZHk+CiAgeyUgZm9yIHMgaW4gdmVyaS5zZXJtYXllX2hhcmVrZXRsZXJpICV9CiAgICA8'
        'dHI+CiAgICAgIDx0ZD57eyAnT3J0YWsnIGlmIHMudGFyYWYgPT0gJ29ydGFrJyBlbHNl'
        'ICdCaXonIH19PC90ZD4KICAgICAgPHRkPnt7ICdLb3lkdScgaWYgcy55b24gPT0gJ2tv'
        'eWR1JyBlbHNlICdHZXJpIGFsZMSxJyB9fTwvdGQ+CiAgICAgIDx0ZD57eyBzLnRhcmlo'
        'IG9yICcnIH19PC90ZD4KICAgICAgPHRkPnt7IHMuYWNpa2xhbWEgb3IgJycgfX08L3Rk'
        'PgogICAgICA8dGQgY2xhc3M9Im51bSI+e3sgJyUuMmYnfGZvcm1hdChzLnR1dGFyKSB9'
        'fSB7eyBzLmRvdml6IH19PC90ZD4KICAgICAgPHRkIGNsYXNzPSJudW0iPnt7ICclLjJm'
        'J3xmb3JtYXQocy51c2QpIH19PC90ZD4KICAgIDwvdHI+CiAgeyUgZWxzZSAlfQogICAg'
        'PHRyPjx0ZCBjb2xzcGFuPSI2IiBzdHlsZT0iY29sb3I6Izc3NyI+a2F0a8SxIGhhcmVr'
        'ZXRpIHlvazwvdGQ+PC90cj4KICB7JSBlbmRmb3IgJX0KICA8L3Rib2R5Pgo8L3RhYmxl'
        'PgoKPGgzIGNsYXNzPSJib2x1bSI+RGHEn8SxdMSxbWxhcjwvaDM+Cjx0YWJsZT4KICA8'
        'dGhlYWQ+PHRyPjx0aD5UYXJhZjwvdGg+PHRoPlRhcmloPC90aD48dGg+QcOnxLFrbGFt'
        'YTwvdGg+CiAgICA8dGggc3R5bGU9InRleHQtYWxpZ246cmlnaHQiPlR1dGFyPC90aD48'
        'dGg+Q2FyaTwvdGg+PC90cj48L3RoZWFkPgogIDx0Ym9keT4KICB7JSBmb3IgeCBpbiBo'
        'ZXNhcC5kYWdpdGltbGFyICV9CiAgICA8dHI+CiAgICAgIDx0ZD57eyAnT3J0YWsnIGlm'
        'IHgudGFyYWYgPT0gJ29ydGFrJyBlbHNlICdCaXonIH19PC90ZD4KICAgICAgPHRkPnt7'
        'IHgudGFyaWggb3IgJycgfX08L3RkPgogICAgICA8dGQ+e3sgeC5hY2lrbGFtYSBvciAn'
        'JyB9fTwvdGQ+CiAgICAgIDx0ZCBjbGFzcz0ibnVtIj57eyAnJS4yZid8Zm9ybWF0KHgu'
        'dHV0YXIpIH19eyUKICAgICAgICBpZiB4LmNldnJpbGRpICV9IDxzcGFuIHN0eWxlPSJm'
        'b250LXdlaWdodDpub3JtYWw7Y29sb3I6Izc3NyI+KHt7CiAgICAgICAgJyUuMmYnfGZv'
        'cm1hdCh4LmhhbV90dXRhcikgfX0ge3sgeC5kb3ZpeiB9fSl7JSBlbmRpZiAlfTwvc3Bh'
        'bj48L3RkPgogICAgICA8dGQ+e3sgJ2nFn2xlbmRpJyBpZiB4LmNhcml5ZV9pc2xlbmRp'
        'IGVsc2UgJ+KAlCcgfX08L3RkPgogICAgPC90cj4KICB7JSBlbHNlICV9CiAgICA8dHI+'
        'PHRkIGNvbHNwYW49IjUiIHN0eWxlPSJjb2xvcjojNzc3Ij5kYcSfxLF0xLFtIHlvazwv'
        'dGQ+PC90cj4KICB7JSBlbmRmb3IgJX0KICA8L3Rib2R5Pgo8L3RhYmxlPgoKeyUgaWYg'
        'a2lwID09ICdpYycgJX0KPGgzIGNsYXNzPSJib2x1bSI+QmHEn2zEsSBpxZ9sZXI8L2gz'
        'Pgo8dGFibGU+CiAgPHRoZWFkPjx0cj48dGg+VGlwPC90aD48dGg+Tm88L3RoPjx0aD5L'
        'YXBzYW08L3RoPjx0aD5Bw6fEsWtsYW1hPC90aD48L3RyPjwvdGhlYWQ+CiAgPHRib2R5'
        'PgogIHslIGZvciBpIGluIHZlcmkuaXNsZXIgJX0KICAgIDx0cj48dGQ+e3sgaS5rYXlu'
        'YWtfdGlwIH19PC90ZD48dGQ+e3sgaS5ubyBvciBpLmtheW5ha19pZCB9fTwvdGQ+CiAg'
        'ICAgIDx0ZD57JSBpZiBpLmthcHNhbmFuICV9a2VzaWxkaSDihpIge3sgaS5rYXBzYW5h'
        'biB9fSDDvHLDvG4gZGFoaWx7JSBlbHNlICV94oCUeyUgZW5kaWYgJX08L3RkPgogICAg'
        'ICA8dGQ+e3sgaS5hY2lrbGFtYSBvciAnJyB9fTwvdGQ+PC90cj4KICB7JSBlbHNlICV9'
        'CiAgICA8dHI+PHRkIGNvbHNwYW49IjQiIHN0eWxlPSJjb2xvcjojNzc3Ij5pxZ8gYmHE'
        'n2xhbm1hZMSxPC90ZD48L3RyPgogIHslIGVuZGZvciAlfQogIDwvdGJvZHk+CjwvdGFi'
        'bGU+Cgo8aDMgY2xhc3M9ImJvbHVtIj5TYXTEscWfIGthecSxdGxhcsSxPC9oMz4KPHRh'
        'YmxlPgogIDx0aGVhZD48dHI+PHRoPlRhcmloPC90aD48dGg+TcO8xZ90ZXJpPC90aD48'
        'dGg+Q2luczwvdGg+PHRoPlN0b2s8L3RoPgogICAgPHRoIHN0eWxlPSJ0ZXh0LWFsaWdu'
        'OnJpZ2h0Ij5UdXRhcjwvdGg+PHRoIHN0eWxlPSJ0ZXh0LWFsaWduOnJpZ2h0Ij5NYWxp'
        'eWV0PC90aD4KICAgIDx0aCBzdHlsZT0idGV4dC1hbGlnbjpyaWdodCI+S8OicjwvdGg+'
        'PC90cj48L3RoZWFkPgogIDx0Ym9keT4KICB7JSBmb3IgcyBpbiBzYXRpc2xhciAlfQog'
        'ICAgPHRyPjx0ZD57eyBzLnNhdGlzX3RhcmloaS5zdHJmdGltZSgnJWQuJW0uJVknKSBp'
        'ZiBzLnNhdGlzX3RhcmloaSBlbHNlICcnIH19PC90ZD4KICAgICAgPHRkPnt7IHMubXVz'
        'dGVyaSBvciAnJyB9fTwvdGQ+PHRkPnt7IHMuY2lucyBvciAnJyB9fTwvdGQ+CiAgICAg'
        'IDx0ZD57eyBzLnN0b2tfaWQgb3IgJycgfX08L3RkPgogICAgICA8dGQgY2xhc3M9Im51'
        'bSI+e3sgJyUuMmYnfGZvcm1hdChzLnR1dGFyX3VzZCBvciAwKSB9fTwvdGQ+CiAgICAg'
        'IDx0ZCBjbGFzcz0ibnVtIj57eyAnJS4yZid8Zm9ybWF0KHMubWFsaXlldF91c2Qgb3Ig'
        'MCkgfX08L3RkPgogICAgICA8dGQgY2xhc3M9Im51bSI+e3sgJyUuMmYnfGZvcm1hdChz'
        'Lmthcl91c2Qgb3IgMCkgfX08L3RkPjwvdHI+CiAgeyUgZWxzZSAlfQogICAgPHRyPjx0'
        'ZCBjb2xzcGFuPSI3IiBzdHlsZT0iY29sb3I6Izc3NyI+c2F0xLHFnyBrYXlkxLEgeW9r'
        'PC90ZD48L3RyPgogIHslIGVuZGZvciAlfQogIDwvdGJvZHk+CjwvdGFibGU+Cgo8aDMg'
        'Y2xhc3M9ImJvbHVtIj5NYWxpeWV0IGthecSxdGxhcsSxPC9oMz4KPHRhYmxlPgogIDx0'
        'aGVhZD48dHI+PHRoPlRhcmloPC90aD48dGg+VGlwPC90aD48dGg+QmHEn2zEsTwvdGg+'
        'PHRoPkZhdHVyYSBubzwvdGg+CiAgICA8dGggc3R5bGU9InRleHQtYWxpZ246cmlnaHQi'
        'PlR1dGFyPC90aD48dGg+S2F0a8SxZGE8L3RoPjwvdHI+PC90aGVhZD4KICA8dGJvZHk+'
        'CiAgeyUgZm9yIG0gaW4gbWFsaXlldGxlciAlfQogICAgPHRyPjx0ZD57eyBtLm1hbGl5'
        'ZXRfdGFyaWhpLnN0cmZ0aW1lKCclZC4lbS4lWScpIGlmIG0ubWFsaXlldF90YXJpaGkg'
        'ZWxzZSAnJyB9fTwvdGQ+CiAgICAgIDx0ZD57eyBtLm1hbGl5ZXRfdGlwIG9yICfigJQn'
        'IH19PC90ZD48dGQ+e3sgbS5iYWdsYW50aV9pZCBvciAnJyB9fTwvdGQ+CiAgICAgIDx0'
        'ZD57eyBtLmZhdHVyYV9ubyBvciAnJyB9fTwvdGQ+CiAgICAgIDx0ZCBjbGFzcz0ibnVt'
        'Ij57eyAnJS4yZid8Zm9ybWF0KG0udHV0YXIgb3IgMCkgfX0ge3sgbS5kb3ZpeiBvciAn'
        'JyB9fTwvdGQ+CiAgICAgIDx0ZD57eyAnZXZldCcgaWYgbS5pZCBpbiB2ZXJpLmFsaW5h'
        'bl9tYWxpeWV0bGVyIGVsc2UgJ+KAlCcgfX08L3RkPjwvdHI+CiAgeyUgZWxzZSAlfQog'
        'ICAgPHRyPjx0ZCBjb2xzcGFuPSI2IiBzdHlsZT0iY29sb3I6Izc3NyI+bWFsaXlldCBr'
        'YXlkxLEgeW9rPC90ZD48L3RyPgogIHslIGVuZGZvciAlfQogIDwvdGJvZHk+CjwvdGFi'
        'bGU+CnslIGVuZGlmICV9Cgo8ZGl2IGNsYXNzPSJkaXBub3QiPgogIEhlc2FwIDxiPnt7'
        'IGhlc2FwLnBhcmFfYmlyaW1pIG9yICdVU0QnIH19PC9iPiDDvHplcmluZGVuIHlhcMSx'
        'bG3EscWfdMSxcjsgVVNEIGTEscWfxLFuZGEKICBnaXJpbGVuIGthbGVtbGVyIGtlbmRp'
        'IGnFn2xlbSB0YXJpaGluZGVraSBUQ01CIGt1cnV5bGEgw6dldnJpbG1pxZ90aXIuCiAg'
        'S8OiciByYWthbcSxIHNhdMSxxZ8ga2F5xLF0bGFyxLFuZGFuIHTDvHJlciwgYnUgYmVs'
        'Z2VkZSB5ZW5pZGVuIGhlc2FwbGFubWF6LgogIHslIGlmIGhlc2FwLnZlcmdpX3RhaG1p'
        'bmkgJX1WZXJnaWxlcmluCiAge3sgJyUuMmYnfGZvcm1hdChoZXNhcC52ZXJnaV90YWht'
        'aW5pKSB9fSB7eyBoZXNhcC5wYXJhX2JpcmltaSBvciAnVVNEJyB9fSdsaWsga8Sxc23E'
        'sQogIFRBSE3EsE7EsETEsFI7IGtlc2lubGXFn3RpxJ9pbmRlIHBheWxhciBkZcSfacWf'
        'aXIueyUgZW5kaWYgJX0KICB7JSBpZiBraXAgPT0gJ29ydGFrJyAlfTxicj5CdSBiZWxn'
        'ZSBvcnRha2zEsWsgaGVzYWLEsW7EsW4gw7Z6ZXRpZGlyOwogIGJhxJ9sxLEgacWfIHZl'
        'IGthecSxdCBkw7Zrw7xtw7wgacOnaW4gacOnIGt1bGxhbsSxbSBraXBpbmUgYmFrxLFu'
        'xLF6LnslIGVuZGlmICV9CjwvZGl2Pgo8L2JvZHk+CjwvaHRtbD4K'
    ),
}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA OR9 — ORTAKLIK RAPORU VE EKSTRESI')
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
        print('    python3 yama_or9.py            # rapor')
        print('    python3 yama_or9.py --uygula')
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
        print('  ⊙ Yama OR9 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_or9.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_or9'
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
    print('    1) sudo systemctl restart milestone-erp  <- sutun burada')
    print('    2) Ctrl+F5')
    print('    3) Analiz -> Is Ortakliklari -> ortakligi ac')
    print('       KATKILAR bolumunde "Maliyetten al" dugmesi.')
    print('       Fason model icin ortakligi "once iade" yap.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

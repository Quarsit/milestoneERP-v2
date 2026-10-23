#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA DZ1 — MALİYET ↔ CARİ HAREKET ZİNCİRİ
==========================================

ÖNKOŞUL: yok, bağımsız. (Maliyet yamalarından sonra da önce de
uygulanabilir; dokunduğu yerler ayrı.)

Bildirdiğin iki şeyi ölçtüm. İkisi de benim kurduğum düzende
tutmadı — ama yerine DÖRT gerçek kusur çıktı, hepsi aynı kökten.

── KÖK SEBEP ──
  Maliyet ile cari hareket arasındaki bağ BİRE BİR kimlikle
  kurulmuş: `CariHareket.baglanti_id = tek maliyet id`.

  Gerçek ilişki bire çok:
    · bir gider faturası NET satırı + DEVREDEN KDV satırı doğurur
    · dağıtım N stok için N satır (+ N KDV satırı) açar

  Tek kimlik bunu taşıyamıyor. Ölçülenler (hepsi tarayıcı/API
  üzerinden, uydurma değil):

  ┌──────────────────────────────┬─────────────────────────────┐
  │ ne yaptım                    │ ne oldu                     │
  ├──────────────────────────────┼─────────────────────────────┤
  │ tekil maliyet → cari hareketi│ net satır gitti, KDV satırı │
  │ sil                          │ ÖKSÜZ kaldı                 │
  │ dağıtılmış (2 stok) → cari   │ YALNIZ İLK satır gitti,     │
  │ hareketi sil                 │ öteki stoğun maliyeti şişik │
  │                              │ kaldı                       │
  │ dağıtımın 2. satırını sil    │ cari borç 600 USD durdu,    │
  │                              │ karşılığı 300'e düştü       │
  │ maliyet tutarını değiştir    │ stok ve kâr güncellendi,    │
  │                              │ cari borç ESKİ tutarda kaldı│
  └──────────────────────────────┴─────────────────────────────┘

  Senin "maliyet silinmiyor" dediğin durum büyük ihtimalle
  dağıtılmış ya da KDV'li bir kayıttı. Tekil ve KDV'siz bir
  maliyette zincir zaten çalışıyordu — onu da ölçtüm.

── ÇÖZÜM: TEK GRUPLAMA ANAHTARI ──
  `grup_id` alanı zaten vardı ve dağıtımda dolduruluyordu. Artık
  TEKİL maliyette de doluyor: net satır ve KDV satırı aynı grupta.

  Silme ve düzenleme artık satıra değil GRUBA bakıyor:
    · hangi satırdan silersen sil, grubun tamamı gider
    · cari hareketten silersen de grubun tamamı gider
    · tutarı değiştirirsen cari borç grup TOPLAMINDAN yeniden
      kurulur
    · her iki yönde de etkilenen stokların birim maliyeti ve
      satış kârı yeniden hesaplanır

  Eski kayıtlarda `grup_id` boş. Onlar için fatura no + stok
  eşleşmesine düşüyoruz (eski davranışın aynısı, kayıp yok) ve
  `goc_dz1.py` geriye dönük dolduruyor.

── ONAY ADIMI (senin seçimin) ──
  Kapsam tek satırdan genişse sunucu 409 + kapsam dönüyor, ekran
  onu gösterip soruyor:

      "Bu kayıt tek başına değil: 2 maliyet satırı (2 kayda
       dağıtılmış) · 2 KDV satırı · 1 cari hareket (tedarikçi
       borcu) birlikte silinecek."

  Onay verilmeden HİÇBİR ŞEY silinmiyor — test bunu ayrıca
  ölçüyor.

  SADE KAYITTA İKİNCİ SORU ÇIKMIYOR. Cariye bağlanmamış, KDV'siz
  tek bir satır tek soruyla siliniyor. Her silmede ikinci bir kutu
  çıksaydı onu okumadan onaylamaya alışırdın; o zaman onay kutusu
  koruma olmaktan çıkar.

  (Not: gruplu bir kayıtta arka arkaya İKİ kutu görüyorsun —
  önce genel soru, sonra kapsam. İkisini tek kutuda birleştirmemi
  istersen söyle, bir satırlık iş.)

── YENİ DOSYA: goc_dz1.py ──
  Eski kayıtlardaki net+KDV çiftlerine geriye dönük grup kimliği
  verir. Eşleştirme ölçütü bilerek DAR:
    · aynı stok + aynı fatura no + biri KDV öteki değil
    · ve o ölçütlere uyan TEK aday olmalı
  Birden çok aday varsa DOKUNMAZ, raporda listeler. Yanlış iki
  kaydı birleştirmek, birini silerken ötekini de götürmek
  demekti; şüphede kalmayı yeğledim.

      python3 goc_dz1.py              # RAPOR — hiçbir şey yazmaz
      python3 goc_dz1.py --uygula

  Fatura no'su boş eski kayıtlar eşleştirilemez; onları da
  raporluyor, silerken tek tek gitmen gerek. DZ1'den sonra
  girilenlerde bu sorun yok.

── ÖLÇÜLDÜ ──
  Beş silme senaryosu + düzenleme, API üzerinden önce/sonra:
      tekil+KDV → cari sil   : 2 satır → 0, borç → 0
      dağıtım(2) → cari sil  : 2 satır → 0, iki stok da düzeldi
      KDV'den sil            : grubun tamamı gitti
      dağıtımın 2. satırı    : grubun tamamı gitti
      tutar 1000 → 2000      : cari borç 1000 → 2000
  Tarayıcıda da yürüdü: onay kutusu kapsamı yazıyor, JS hatası yok.

  175 test geçti (170 + 5 yeni kalıcı test); dört ayrı koşuda da
  aynı — sayımlar her teste özel kimliklerle yapılıyor, sıra
  bağımlılığı yok. firma · js · form · zincir · akis · degismezlik
  temiz. Grup çözücüyü devre dışı bırakıp testlerin DÜŞTÜĞÜNÜ
  gördüm.

── BU SIRANIN BİRİNCİSİ ──
  "Her kayıt düzenlenebilsin" dediğin iş dörde bölündü:
      DZ1  maliyet ↔ cari hareket            ← bu yama
      DZ2  stok kayıtları (ölçü, tonaj, alış)
      DZ3  satış / proforma / sipariş kalemleri
      DZ4  kesim kayıtları
  Sırayla geliyorlar.

DOSYALAR
--------
  flask_app.py            grup çözücü · 4 uç nokta gruba bağlandı
  templates/cari.html     409 → kapsamlı onay
  templates/maliyet.html  409 → kapsamlı onay
  tests/test_kritik.py    5 yeni test
  goc_dz1.py              YENİ — eski kayıtları gruplar (tam dosya)

Şema yok, yeni alan yok — `grup_id` zaten vardı.

KULLANIM
--------
  python3 yama_dz1.py            # RAPOR
  python3 yama_dz1.py --uygula
  sudo systemctl restart milestone-erp
  python3 goc_dz1.py             # önce rapor
  python3 goc_dz1.py --uygula
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
    'flask_app.py': 'DZ1 · MALİYET GRUBU',
    'templates/cari.html': "e.yanit.error === 'onay_gerekli'",
    'templates/maliyet.html': "e.yanit.error === 'onay_gerekli'",
    'tests/test_kritik.py': 'def test_dz1_cari_hareket_silinince_kdv_satiri_oksuz_kalmaz',
    'goc_dz1.py': 'GÖÇ DZ1',
}
ONKOSUL = {
    'flask_app.py': 'def api_maliyet_sil(maliyet_id):',
    'templates/cari.html': 'async function hareketSil(hareketId, cariId) {',
    'templates/maliyet.html': 'async function maliyetSil(id) {',
    'tests/test_kritik.py': 'def istemci(',
}
TAM_YAZILAN = ['goc_dz1.py']

DEGISIKLIKLER = [
    ('flask_app.py', 'DZ1 · flask_app.py blok 1',
     r'''        # Bağlı Maliyet varsa onu da sil (kaynak='maliyet')
        if hareket.baglanti_tip == 'maliyet' and hareket.baglanti_id and hareket.kaynak == 'maliyet':
            m = Maliyet.query.get(hareket.baglanti_id)
            if m:
                silinen_maliyet = m.id
                etkilenen_stok  = m.baglanti_id
                db.session.delete(m)
                db.session.flush()
                _satis_kaydi_maliyet_guncelle([etkilenen_stok] if etkilenen_stok else [])
''',
     r'''        # DZ1 · BAGLI MALIYET GRUBU
        # Eskiden yalniz `baglanti_id`nin isaret ettigi TEK satir
        # siliniyordu. Oysa bir cari hareket bir FATURAYI temsil
        # ediyor: net satir + KDV satiri, dagitimda da N stok icin
        # N satir. Olculdu — dagitilmis bir maliyetin cari hareketi
        # silindiginde N-1 satir oksuz kaliyor ve o stoklarin
        # maliyeti sisik gorunmeye devam ediyordu.
        if hareket.baglanti_tip == 'maliyet' and hareket.baglanti_id and hareket.kaynak == 'maliyet':
            m = Maliyet.query.get(hareket.baglanti_id)
            if m:
                _grup = _maliyet_grubu(m)
                _kapsam = _maliyet_kapsam(_grup, [hareket])
                if not _onay_verildi() and len(_grup) > 1:
                    return jsonify({
                        'ok': False, 'error': 'onay_gerekli', 'kapsam': _kapsam,
                        'mesaj': f'Bu hareket bir faturanın karşılığı: '
                                 f'{_kapsam["metin"]} birlikte silinecek.'}), 409
                silinen_maliyet = ', '.join(s.id for s in _grup)
                _etkilenen = [s.baglanti_id for s in _grup]
                for s in _grup:
                    db.session.delete(s)
                db.session.flush()
                _maliyet_etkilenen_stoklari_tazele(_etkilenen)
'''),
    ('flask_app.py', 'DZ1 · flask_app.py blok 2',
     r'''        m = Maliyet(id=_okunur_id('MYT', Maliyet, basamak=4), maliyet_tip=maliyet_tip,
                    baglanti_tip=baglanti_tip, baglanti_id=baglanti_id,
''',
     r'''        # DZ1: TEKIL maliyette de grup kimligi. Net satir ve KDV
        # satiri ayni faturanin iki yuzu; biri silinirken otekinin
        # oksuz kalmamasi icin tek anahtara bagliyorlar.
        _grup = _yeni_id('MGR')   # dagitimla ayni kimlik uzayi
        m = Maliyet(id=_okunur_id('MYT', Maliyet, basamak=4), maliyet_tip=maliyet_tip,
                    baglanti_tip=baglanti_tip, baglanti_id=baglanti_id, grup_id=_grup,
'''),
    ('flask_app.py', 'DZ1 · flask_app.py blok 3',
     r'''                            tutar=kdv_tutar, doviz=doviz, usd_karsilik=_usd(kdv_tutar, doviz),
''',
     r'''                            grup_id=_grup,
                            tutar=kdv_tutar, doviz=doviz, usd_karsilik=_usd(kdv_tutar, doviz),
'''),
    ('flask_app.py', 'DZ1 · flask_app.py blok 4',
     r'''    @app.route('/api/maliyet/<maliyet_id>', methods=['PUT'])
''',
     r'''    # ══════════════════════════════════════════════════════════
    #  DZ1 · MALİYET GRUBU — BİR FATURA, ÇOK SATIR
    #
    #  Maliyet ile cari hareket arasındaki bağ BİRE BİR kimlikle
    #  kurulmuştu (`CariHareket.baglanti_id = tek maliyet id`).
    #  Gerçek ilişki bire çok:
    #    · bir fatura NET satırı + DEVREDEN KDV satırı doğurur
    #    · dağıtım N stok için N satır (+ N KDV satırı) açar
    #  Tek kimlik bunu taşıyamıyor. Ölçülen sonuçlar:
    #    · cari hareketi silince KDV satırı ÖKSÜZ kalıyordu
    #    · dağıtımda yalnız İLK satır siliniyor, gerisi kalıyor ve
    #      o stokların maliyeti şişik görünmeye devam ediyordu
    #    · bir satır silinince cari borç eski tutarda kalıyordu
    #
    #  Tek gruplama anahtarı `grup_id`. Dağıtımda zaten doluydu;
    #  artık TEKİL maliyette de dolduruluyor (net + KDV aynı grup).
    #  Eski kayıtlarda boş — onlar için fatura no/stok eşleşmesine
    #  düşüyoruz (eski davranış), goc_dz1.py de geriye dönük
    #  dolduruyor.
    # ══════════════════════════════════════════════════════════
    def _maliyet_grubu(m):
        """`m` ile AYNI FATURA OLAYINA ait bütün maliyet satırları.

        Her zaman en az [m] döner. Sıra: net satırlar önce, KDV
        satırları sonra — mesajda okunur dursun diye."""
        if m is None:
            return []
        if m.grup_id:
            satirlar = Maliyet.query.filter_by(grup_id=m.grup_id).all()
        else:
            # ESKİ KAYIT: grup_id yok. Fatura no + bağlantı eşleşmesi
            # tek elimizdeki ip. Fatura no boşsa kardeş aranamaz —
            # o zaman yalnız kendisi (eski davranışın aynısı).
            satirlar = [m]
            if m.fatura_no and m.baglanti_id:
                kardesler = Maliyet.query.filter(
                    Maliyet.fatura_no == m.fatura_no,
                    Maliyet.baglanti_tip == m.baglanti_tip,
                    Maliyet.baglanti_id == m.baglanti_id,
                    Maliyet.id != m.id).all()
                satirlar += kardesler
        return sorted(satirlar, key=lambda x: (x.maliyet_tip == 'Devreden KDV',
                                               x.id or ''))

    def _maliyet_grup_hareketleri(satirlar):
        """Gruptaki HERHANGİ bir satıra bağlı cari hareketler.
        Dağıtımda hareket yalnız ilk satırı işaret ediyor; gruptaki
        her kimliği sorduğumuz için yine de buluyoruz."""
        idler = [s.id for s in satirlar if s.id]
        if not idler:
            return []
        return CariHareket.query.filter(
            CariHareket.baglanti_tip == 'maliyet',
            CariHareket.baglanti_id.in_(idler)).all()

    def _maliyet_kapsam(satirlar, hareketler):
        """Onay kutusunda gösterilecek kapsam — ne silinecek."""
        stoklar = sorted({s.baglanti_id for s in satirlar if s.baglanti_id})
        net = [s for s in satirlar if s.maliyet_tip != 'Devreden KDV']
        kdv = [s for s in satirlar if s.maliyet_tip == 'Devreden KDV']
        parcalar = []
        if len(net) > 1:
            parcalar.append(f'{len(net)} maliyet satırı '
                            f'({len(stoklar)} kayda dağıtılmış)')
        elif net:
            parcalar.append('1 maliyet satırı')
        if kdv:
            parcalar.append(f'{len(kdv)} KDV satırı')
        if hareketler:
            parcalar.append(f'{len(hareketler)} cari hareket '
                            f'(tedarikçi borcu)')
        return {
            'satir_sayisi': len(satirlar),
            'stok_sayisi': len(stoklar),
            'hareket_sayisi': len(hareketler),
            'metin': ' · '.join(parcalar),
            'stoklar': stoklar[:8],
        }

    def _maliyet_etkilenen_stoklari_tazele(stoklar):
        """Silme/düzenleme sonrası türetilmiş değerleri yeniden üret."""
        stoklar = [s for s in dict.fromkeys(stoklar) if s]
        if not stoklar:
            return 0
        n = _satis_kaydi_maliyet_guncelle(stoklar)
        for sid in stoklar:
            if str(sid).startswith('BLK'):
                _kesilmis_blok_maliyet_yeniden_dagit(sid)
        return n

    def _onay_verildi():
        """Onay hem sorgu dizesinden hem gövdeden kabul edilir."""
        if (request.args.get('onay') or '').lower() in ('1', 'true', 'evet'):
            return True
        g = request.get_json(silent=True) or {}
        return bool(g.get('onay'))

    @app.route('/api/maliyet/<maliyet_id>', methods=['PUT'])
'''),
    ('flask_app.py', 'DZ1 · flask_app.py blok 5',
     r'''        sk_guncel = _satis_kaydi_maliyet_guncelle([m.baglanti_id])
        if m.baglanti_id and str(m.baglanti_id).startswith('BLK'):
            _kesilmis_blok_maliyet_yeniden_dagit(m.baglanti_id)
        db.session.commit()
        return jsonify({'ok': True, 'satis_kaydi_guncel': sk_guncel})
''',
     r'''        sk_guncel = _maliyet_etkilenen_stoklari_tazele([m.baglanti_id])

        # DZ1 · TEDARIKCI BORCUNU DA ESITLE
        # Tutari degistirmek maliyeti ve satis karini guncelliyordu
        # ama CARI HAREKET eski tutarda kaliyordu: stokta 2.000 USD
        # gider gorunurken tedarikcide 1.000 USD borc duruyordu.
        # Borc, grubun TAMAMININ karsiligi (net + KDV) — tek satirin
        # degil; o yuzden grup toplamindan yeniden kuruluyor.
        hareket_guncel = None
        _grup = _maliyet_grubu(m)
        _hareketler = _maliyet_grup_hareketleri(_grup)
        if len(_hareketler) == 1:
            _h = _hareketler[0]
            _toplam = q2(sum((s.tutar or 0) for s in _grup))
            if (_h.alacak or 0) != _toplam:
                _a_try, _a_kur = _gider_cari_alanlari(_toplam, m.doviz)
                _h.alacak = _toplam
                _h.alacak_try = _a_try
                _h.kur_uygulanan = _a_kur
                hareket_guncel = {'id': _h.id, 'yeni_tutar': _toplam}
            _h.doviz = m.doviz
            if m.fatura_no is not None:
                _h.evrak_no = m.fatura_no
            if getattr(m, 'maliyet_tarihi', None):
                _h.hareket_tarihi = m.maliyet_tarihi
        db.session.commit()
        msg = 'Maliyet güncellendi'
        if hareket_guncel:
            msg += (f', tedarikçi borcu da {hareket_guncel["yeni_tutar"]:,.2f} '
                    f'{m.doviz} olarak düzeltildi')
        return jsonify({'ok': True, 'satis_kaydi_guncel': sk_guncel,
                        'hareket_guncel': hareket_guncel, 'mesaj': msg})
'''),
    ('flask_app.py', 'DZ1 · flask_app.py blok 6',
     r'''        etkilenen_stok = m.baglanti_id

        # KDV kardeş kaydını bul: aynı fatura_no + aynı stok + Devreden KDV tipi
        kardes_ids = []
        if m.fatura_no and m.baglanti_id:
            kardesler = Maliyet.query.filter(
                Maliyet.fatura_no == m.fatura_no,
                Maliyet.baglanti_id == m.baglanti_id,
                Maliyet.id != maliyet_id,
                Maliyet.maliyet_tip == 'Devreden KDV'
            ).all()
            for k in kardesler:
                kardes_ids.append(k.id)
                # Kardeşin cari hareketini de sil
                CariHareket.query.filter_by(
                    baglanti_tip='maliyet', baglanti_id=k.id
                ).delete()
                db.session.delete(k)

        # Ana maliyetin cari hareketlerini sil
        silinen_ch = CariHareket.query.filter_by(
            baglanti_tip='maliyet', baglanti_id=maliyet_id
        ).delete()

        db.session.delete(m)
        db.session.flush()
        sk_guncel = _satis_kaydi_maliyet_guncelle([etkilenen_stok] if etkilenen_stok else [])
        db.session.commit()
        msg = 'Maliyet silindi'
        if kardes_ids: msg += f', KDV kaydı da silindi ({", ".join(kardes_ids)})'
        if silinen_ch: msg += f', {silinen_ch} cari hareket de silindi'
        return jsonify({'ok': True, 'silinen_kdv': kardes_ids,
                        'silinen_cari_hareket': silinen_ch,
''',
     r'''
        # DZ1: TEK SATIR DEGIL, GRUP. Eskiden yalniz bu satir ve
        # (fatura no doluysa) KDV kardesi siliniyordu; dagitilmis bir
        # maliyetin obur satirlari kaliyor, cari borc da eski tutarda
        # duruyordu. Artik grubun tamami birlikte gidiyor.
        satirlar = _maliyet_grubu(m)
        hareketler = _maliyet_grup_hareketleri(satirlar)
        kapsam = _maliyet_kapsam(satirlar, hareketler)

        # ONAY: kapsam tek satirdan genisse once soruyoruz. 409,
        # `api()`nin cagirana devrettigi durum — ekran kapsami
        # gosterip tekrar cagiriyor.
        if not _onay_verildi() and (len(satirlar) > 1 or hareketler):
            return jsonify({
                'ok': False, 'error': 'onay_gerekli', 'kapsam': kapsam,
                'mesaj': f'Bu kayıt tek başına değil: {kapsam["metin"]} '
                         f'birlikte silinecek.'}), 409

        etkilenen = [s.baglanti_id for s in satirlar]
        silinen_ch = [h.id for h in hareketler]
        for h in hareketler:
            db.session.delete(h)
        silinen_satir = [s.id for s in satirlar]
        for s in satirlar:
            db.session.delete(s)
        db.session.flush()
        sk_guncel = _maliyet_etkilenen_stoklari_tazele(etkilenen)
        db.session.commit()

        msg = f'{len(silinen_satir)} maliyet satırı silindi'
        if silinen_ch:
            msg += f', {len(silinen_ch)} cari hareket de silindi'
        if sk_guncel:
            msg += f', {sk_guncel} satış kaydının kârı yeniden hesaplandı'
        return jsonify({'ok': True, 'silinen': silinen_satir,
                        'silinen_cari_hareket': silinen_ch,
                        'kapsam': kapsam,
'''),
    ('templates/cari.html', 'DZ1 · templates/cari.html blok 1',
     r'''  try {
    const d = await api(`/api/cari/hareket/${encodeURIComponent(hareketId)}`, { method: 'DELETE' });
    bildir(d.mesaj || 'Hareket silindi');
    await yukle();
    detayAc(cariId);
  } catch (e) { /* */ }
''',
     r'''  /* DZ1: hareket bir GIDER FATURASININ karsiligi olabilir; o zaman
     ardinda bir maliyet GRUBU durur (net satir + KDV, dagitimda N
     satir). Sunucu boyle bir durumda 409 + kapsam donuyor; kapsami
     gosterip ikinci kez soruyoruz. Tek satirlik sade hareketlerde
     ikinci soru hic cikmiyor. */
  const yol = `/api/cari/hareket/${encodeURIComponent(hareketId)}`;
  try {
    let d;
    try {
      d = await api(yol, { method: 'DELETE' });
    } catch (e) {
      if (e && e.status === 409 && e.yanit && e.yanit.error === 'onay_gerekli') {
        if (!await onayla(e.yanit.mesaj, { tehlike: true })) return;
        d = await api(yol + '?onay=1', { method: 'DELETE' });
      } else { throw e; }
    }
    bildir(d.mesaj || 'Hareket silindi');
    await yukle();
    detayAc(cariId);
  } catch (e) { /* api() zaten bildiriyor */ }
'''),
    ('templates/maliyet.html', 'DZ1 · templates/maliyet.html blok 1',
     r'''  try {
    const d = await api(`/api/maliyet/${encodeURIComponent(id)}`, { method: 'DELETE' });
    bildir(d.mesaj || 'Maliyet silindi');
    cekmeceKapat(); await yukle();
  } catch (e) { /* */ }
''',
     r'''  /* DZ1: bu satir tek basina olmayabilir — ayni faturanin KDV
     satiri ya da dagitimdan gelen kardes satirlar olabilir ve
     tedarikci borcu da onlarin TOPLAMININ karsiligi. Sunucu
     kapsami 409 ile bildiriyor; once gosterip soruyoruz. */
  const yol = `/api/maliyet/${encodeURIComponent(id)}`;
  try {
    let d;
    try {
      d = await api(yol, { method: 'DELETE' });
    } catch (e) {
      if (e && e.status === 409 && e.yanit && e.yanit.error === 'onay_gerekli') {
        if (!await onayla(e.yanit.mesaj, { tehlike: true })) return;
        d = await api(yol + '?onay=1', { method: 'DELETE' });
      } else { throw e; }
    }
    bildir(d.mesaj || 'Maliyet silindi');
    cekmeceKapat(); await yukle();
  } catch (e) { /* api() zaten bildiriyor */ }
'''),
    ('tests/test_kritik.py', 'DZ1 · tests/test_kritik.py blok 1',
     r'''    assert not bozuk, f'alt bar .modal dışında kalmış: {bozuk}'
''',
     r'''    assert not bozuk, f'alt bar .modal dışında kalmış: {bozuk}'


def _dz1_kur(c, ek, tonlar=(20, 10)):
    """DZ1 testleri icin kurulum. HER TESTE KENDI KIMLIKLERI:
    sayimlar genel yapilirsa takim halinde calisirken baska
    testlerin birakti maliyet/hareket satirlari girer ve test
    sirasi onemli hale gelir — bir kez yasadik, bir daha degil."""
    from models import Cari
    with fa.app.app_context():
        if not db.session.get(Cari, 'TEDDZ'):
            db.session.add(Cari(id='TEDDZ', unvan='NAKLIYECI DZ',
                                cari_tip='Tedarikçi', urun_tedarikcisi=True))
        idler = []
        for n, ton in enumerate(tonlar, 1):
            sid = f'BLK-{ek}{n}'
            idler.append(sid)
            if not db.session.get(BlokStok, sid):
                db.session.add(BlokStok(
                    id=sid, blok_no=f'{ek}{n}', cins='TEST', boy=300,
                    yukseklik=180, en=170, hacim_m3=9.18, tonaj=ton,
                    alis_fiyati=300, alis_fiyat_birim='ton', doviz='USD',
                    durum='Serbest'))
        db.session.commit()
    return idler


def _dz1_sayim(stok_idler):
    """Yalniz BU stoklara bagli maliyet ve hareket sayisi."""
    from models import CariHareket, Maliyet
    with fa.app.app_context():
        satirlar = Maliyet.query.filter(
            Maliyet.baglanti_id.in_(stok_idler)).all()
        idler = [s.id for s in satirlar] or ['-']
        hareketler = CariHareket.query.filter(
            CariHareket.baglanti_tip == 'maliyet',
            CariHareket.baglanti_id.in_(idler)).count()
        return len(satirlar), hareketler


def test_dz1_cari_hareket_silinince_kdv_satiri_oksuz_kalmaz():
    """DZ1: bir gider faturası İKİ maliyet satırı doğuruyor — net ve
    Devreden KDV. Cari hareket silinince eskiden yalnız net satır
    gidiyor, KDV satırı stoğa bağlı olarak ÖKSÜZ kalıyordu.

    Bağ `baglanti_id` ile bire bir kurulmuştu; gerçek ilişki bire
    çok. Artık `grup_id` tek anahtar."""
    from models import CariHareket, Maliyet
    c = istemci('admin', 'ADMIN')
    (sid,) = _dz1_kur(c, 'KDVA', (20,))
    r = c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Nakliye (Ocak-Fabrika)', 'baglanti_tip': 'stok',
        'baglanti_id': sid, 'tutar': 1000, 'doviz': 'USD',
        'kdv_oran': 20, 'cari_id': 'TEDDZ'})
    assert r.status_code == 200, r.get_json()
    mid = r.get_json()['id']
    assert _dz1_sayim([sid]) == (2, 1), _dz1_sayim([sid])
    with fa.app.app_context():
        hid = CariHareket.query.filter_by(
            baglanti_tip='maliyet', baglanti_id=mid).first().id

    # ONAY olmadan: 409 + kapsam, ve hicbir sey silinmemis
    r = c.delete(f'/api/cari/hareket/{hid}', headers=H)
    assert r.status_code == 409, r.status_code
    d = r.get_json()
    assert d['error'] == 'onay_gerekli'
    assert d['kapsam']['satir_sayisi'] == 2, d['kapsam']
    assert _dz1_sayim([sid]) == (2, 1), 'onay verilmeden silinmiş'

    assert c.delete(f'/api/cari/hareket/{hid}?onay=1',
                    headers=H).status_code == 200
    assert _dz1_sayim([sid]) == (0, 0), 'KDV satırı öksüz kaldı'
    with fa.app.app_context():
        assert db.session.get(CariHareket, hid) is None


def test_dz1_dagitilmis_maliyetin_tamami_birlikte_gider():
    """DZ1: dağıtım N stok için N satır açıyor ama cari harekete
    yalnız İLK satırın kimliği yazılıyordu. Hareketi silince N-1
    satır kalıyor ve o stokların maliyeti şişik görünmeye devam
    ediyordu — ölçüldü."""
    from models import CariHareket, Maliyet
    c = istemci('admin', 'ADMIN')
    a, b = _dz1_kur(c, 'DAG', (20, 10))
    r = c.post('/api/maliyet/dagit', headers=H, json={
        'maliyet_tip': 'Navlun', 'baglanti_tip': 'stok',
        'hedefler': [a, b], 'tutar': 3000, 'doviz': 'USD',
        'kdv_oran': 0, 'dagitim': 'oransal', 'cari_id': 'TEDDZ'})
    assert r.status_code == 200, r.get_json()
    assert _dz1_sayim([a, b]) == (2, 1), _dz1_sayim([a, b])
    with fa.app.app_context():
        satirlar = Maliyet.query.filter(Maliyet.baglanti_id.in_([a, b])).all()
        assert len({s.grup_id for s in satirlar}) == 1, 'tek grupta değiller'
        hid = CariHareket.query.filter(
            CariHareket.baglanti_tip == 'maliyet',
            CariHareket.baglanti_id.in_([s.id for s in satirlar])).first().id

    d = c.delete(f'/api/cari/hareket/{hid}', headers=H).get_json()
    assert d['kapsam']['stok_sayisi'] == 2, d['kapsam']
    assert c.delete(f'/api/cari/hareket/{hid}?onay=1',
                    headers=H).status_code == 200
    assert _dz1_sayim([a, b]) == (0, 0), 'dağıtımın bir kısmı öksüz kaldı'


def test_dz1_maliyet_silinince_cari_hareket_de_gider():
    """DZ1: ters yön. Hangi satırdan silinirse silinsin — net, KDV,
    ya da dağıtımın ortasındaki bir satır — grubun tamamı ve
    tedarikçi borcu birlikte gider."""
    c = istemci('admin', 'ADMIN')
    (sid,) = _dz1_kur(c, 'TERS', (10,))
    r = c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Komisyon', 'baglanti_tip': 'stok',
        'baglanti_id': sid, 'tutar': 500, 'doviz': 'USD',
        'kdv_oran': 20, 'cari_id': 'TEDDZ'})
    kdv_id = r.get_json()['kdv_id']
    assert _dz1_sayim([sid]) == (2, 1)

    # KDV satirindan silmek bile grubun tamamini goturur
    assert c.delete(f'/api/maliyet/{kdv_id}', headers=H).status_code == 409
    assert c.delete(f'/api/maliyet/{kdv_id}?onay=1',
                    headers=H).status_code == 200
    assert _dz1_sayim([sid]) == (0, 0)


def test_dz1_maliyet_duzenlenince_tedarikci_borcu_esitlenir():
    """DZ1: tutarı değiştirmek maliyeti ve satış kârını
    güncelliyordu ama CARİ HAREKET eski tutarda kalıyordu —
    stokta 2.000 USD gider görünürken tedarikçide 1.000 USD borç.

    Borç grubun TAMAMININ karşılığı (net + KDV), tek satırın
    değil; o yüzden grup toplamından yeniden kuruluyor."""
    from models import CariHareket
    c = istemci('admin', 'ADMIN')
    (sid,) = _dz1_kur(c, 'DUZ', (20,))
    mid = c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Gümrük/Liman Masrafı', 'baglanti_tip': 'stok',
        'baglanti_id': sid, 'tutar': 1000, 'doviz': 'USD',
        'kdv_oran': 0, 'cari_id': 'TEDDZ'}).get_json()['id']
    with fa.app.app_context():
        h = CariHareket.query.filter_by(
            baglanti_tip='maliyet', baglanti_id=mid).first()
        assert h.alacak == 1000, h.alacak
        hid = h.id

    r = c.put(f'/api/maliyet/{mid}', headers=H, json={'tutar': 2000})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()['hareket_guncel']['yeni_tutar'] == 2000
    with fa.app.app_context():
        assert db.session.get(CariHareket, hid).alacak == 2000, \
            'tedarikçi borcu eski tutarda kaldı'


def test_dz1_sade_kayitta_fazladan_onay_sorulmaz():
    """DZ1: onay adımı yalnız kapsam genişken çıkmalı. Cariye
    bağlanmamış, KDV'siz tek bir maliyet satırı tek soruyla
    silinmeli — her silmede ikinci bir kutu çıkarsa kullanıcı
    onu okumadan onaylamaya alışır."""
    from models import Maliyet
    c = istemci('admin', 'ADMIN')
    (sid,) = _dz1_kur(c, 'SADE', (10,))
    mid = c.post('/api/maliyet', headers=H, json={
        'maliyet_tip': 'Diğer', 'baglanti_tip': 'stok',
        'baglanti_id': sid, 'tutar': 100, 'doviz': 'USD',
        'kdv_oran': 0}).get_json()['id']
    r = c.delete(f'/api/maliyet/{mid}', headers=H)
    assert r.status_code == 200, (r.status_code, r.get_json())
    with fa.app.app_context():
        assert db.session.get(Maliyet, mid) is None
'''),
]

# ====================================================================
#  TAM DOSYA · goc_dz1.py  (YENI)
# ====================================================================
TAM_ICERIK = {
    'goc_dz1.py': (
        'IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwojIC0qLSBjb2Rpbmc6IHV0Zi04IC0qLQoiIiIK'
        'R8OWw4cgRFoxIOKAlCBlc2tpIG1hbGl5ZXQga2F5xLF0bGFyxLFuYSBncnVwIGtpbWxp'
        'xJ9pCj09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09'
        'PQoKRFoxJ2RlbiDDtm5jZSBgZ3J1cF9pZGAgeWFsbsSxeiBEQcSeSVRJTE1JxZ4gbWFs'
        'aXlldGxlcmRlIGRvbHV5ZHUuClRla2lsIG1hbGl5ZXRpbiBuZXQgc2F0xLFyxLEgaWxl'
        'IEtEViBzYXTEsXLEsSBhcmFzxLFuZGEgaGnDp2JpciBiYcSfCnlva3R1OyBiaXJpIHNp'
        'bGluaW5jZSDDtnRla2kgw7Zrc8O8eiBrYWzEsXlvcmR1LgoKQnUgYmV0aWsgZ2VyaXll'
        'IGTDtm7DvGsgbyDDp2lmdGxlcmkgYmlyIGdydWJhIGFsxLFyLgoKRcWeTEXFnlTEsFJN'
        'RSDDlkzDh8OcVMOcIOKAlCBiaWxlcmVrIERBUiB0dXR1bGR1OgogIMK3IGF5bsSxIGBi'
        'YWdsYW50aV90aXBgICsgYGJhZ2xhbnRpX2lkYCAoYXluxLEgc3Rvay9zaXBhcmnFnykK'
        'ICDCtyBheW7EsSBgZmF0dXJhX25vYCAoaWtpc2kgZGUgZG9sdSkKICDCtyBiaXJpICdE'
        'ZXZyZWRlbiBLRFYnLCDDtnRla2kgZGXEn2lsCiAgwrcgdmUgbyDDtmzDp8O8dGxlcmUg'
        'dXlhbiBURUsgYmlyIGFkYXkgb2xtYWzEsQoKQmlyZGVuIMOnb2sgYWRheSB2YXJzYSBE'
        'T0tVTlVMTUFaIHZlIHJhcG9yZGEgbGlzdGVsZW5pci4gWWFubMSxxZ8KaWtpIGtheWTE'
        'sSBiaXJsZcWfdGlybWVrLCBiaXJpbmkgc2lsZXJrZW4gw7Z0ZWtpbmkgZGUgZ8O2dMO8'
        'cm1lawpkZW1la3RpOyDFn8O8cGhlZGUga2FsbWF5xLEgeWXEn2xpeW9ydW0uCgpGYXR1'
        'cmEgbm8nc3UgYm/FnyBlc2tpIGthecSxdGxhciBlxZ9sZcWfdGlyaWxlbWV6IOKAlCBv'
        'bmxhciBpw6dpbgplbGltaXpkZSBhecSxcnQgZWRpY2kgYmlyIGlwIHlvay4gT25sYXIg'
        'ZGEgcmFwb3JkYSBnw7Zyw7xuw7xyOwpEWjEnZGVuIHNvbnJhIGdpcmlsZW4ga2F5xLF0'
        'bGFyZGEgYnUgc29ydW4geW9rLgoKICBweXRob24zIGdvY19kejEucHkgICAgICAgICAg'
        'ICAgICMgUkFQT1Ig4oCUIGhpw6diaXIgxZ9leSB5YXrEsWxtYXoKICBweXRob24zIGdv'
        'Y19kejEucHkgLS11eWd1bGEKIiIiCmltcG9ydCBvcwppbXBvcnQgc3lzCgpVWUdVTEEg'
        'PSAnLS11eWd1bGEnIGluIHN5cy5hcmd2Cm9zLmVudmlyb24uc2V0ZGVmYXVsdCgnTUlM'
        'RVNUT05FX0FDSUxJU19BVExBJywgJzEnKQpzeXMucGF0aC5pbnNlcnQoMCwgb3MucGF0'
        'aC5kaXJuYW1lKG9zLnBhdGguYWJzcGF0aChfX2ZpbGVfXykpKQoKZGVmIF92ZW52X3V5'
        'YXIoaGF0YSk6CiAgICAiIiJGbGFzayB5b2tzYSBuZSB5YXBhY2FnaW5pIFNPWUxFLiBZ'
        'YW1hbGFyIGR1eiBweXRob24zIGlsZQogICAgY2FsaXNpeW9yICh5YWxuaXogZG9zeWEg'
        'ZHV6ZW5saXlvcmxhcik7IHZlcml0YWJhbmluYSBiYWdsYW5hbgogICAgYmV0aWtsZXIg'
        'dmVudiBpc3RpeW9yLiBJa2lzaW5pbiBrYXJpc21hc2kgZG9nYWwuIiIiCiAgICBwcmlu'
        'dCgnPScgKiA3MCkKICAgIHByaW50KCcgIEhBVEE6ICcgKyBzdHIoaGF0YSkpCiAgICBw'
        'cmludCgnPScgKiA3MCkKICAgIHByaW50KCcgIEJ1IGJldGlrIHZlcml0YWJhbmluYSBi'
        'YWdsYW5peW9yLCB5YW5pIHNhbmFsIG9ydGFtIGdlcmVrbGkuJykKICAgIHByaW50KCcg'
        'IER1eiBgcHl0aG9uM2AgaWxlIGRlZ2lsLCBzb3lsZSBjYWxpc3RpcjonKQogICAgcHJp'
        'bnQoKQogICAgcHJpbnQoJyAgICAgIGNkIH4vbWlsZXN0b25lRVJQLXYyJykKICAgIHBy'
        'aW50KCcgICAgICB2ZW52L2Jpbi9weXRob24gJyArIG9zLnBhdGguYmFzZW5hbWUoX19m'
        'aWxlX18pKQogICAgcHJpbnQoKQogICAgcHJpbnQoJyAgKFlhbWFsYXIgYHB5dGhvbjNg'
        'IGlsZSBjYWxpc2l5b3IgY3Vua3Ugb25sYXIgeWFsbml6JykKICAgIHByaW50KCcgICBk'
        'b3N5YSBkdXplbmxpeW9yLCBGbGFza1wnYSBkb2t1bm11eW9ybGFyLiknKQogICAgcHJp'
        'bnQoJz0nICogNzApCiAgICBzeXMuZXhpdCgxKQoKCnRyeToKICAgIGltcG9ydCBmbGFz'
        'a19hcHAgYXMgZmEgICAgICAgICAgIyBub3FhOiBFNDAyCiAgICBmcm9tIG1vZGVscyBp'
        'bXBvcnQgZGIsIE1hbGl5ZXQgICMgbm9xYTogRTQwMgpleGNlcHQgTW9kdWxlTm90Rm91'
        'bmRFcnJvciBhcyBfaDoKICAgIF92ZW52X3V5YXIoX2gpCgoKZGVmIGFuYSgpOgogICAg'
        'd2l0aCBmYS5hcHAuYXBwX2NvbnRleHQoKToKICAgICAgICBncnVwbGFuYWNhayA9IFtd'
        'CiAgICAgICAgY29rbHUgPSBbXQogICAgICAgIGlwc2l6ID0gW10KCiAgICAgICAga2R2'
        'bGVyID0gTWFsaXlldC5xdWVyeS5maWx0ZXIoCiAgICAgICAgICAgIE1hbGl5ZXQubWFs'
        'aXlldF90aXAgPT0gJ0RldnJlZGVuIEtEVicsCiAgICAgICAgICAgIE1hbGl5ZXQuZ3J1'
        'cF9pZC5pc18oTm9uZSkpLmFsbCgpCgogICAgICAgIGZvciBrIGluIGtkdmxlcjoKICAg'
        'ICAgICAgICAgaWYgbm90IChrLmZhdHVyYV9ubyBhbmQgay5iYWdsYW50aV9pZCk6CiAg'
        'ICAgICAgICAgICAgICBpcHNpei5hcHBlbmQoay5pZCkKICAgICAgICAgICAgICAgIGNv'
        'bnRpbnVlCiAgICAgICAgICAgIGFkYXlsYXIgPSBNYWxpeWV0LnF1ZXJ5LmZpbHRlcigK'
        'ICAgICAgICAgICAgICAgIE1hbGl5ZXQuZmF0dXJhX25vID09IGsuZmF0dXJhX25vLAog'
        'ICAgICAgICAgICAgICAgTWFsaXlldC5iYWdsYW50aV90aXAgPT0gay5iYWdsYW50aV90'
        'aXAsCiAgICAgICAgICAgICAgICBNYWxpeWV0LmJhZ2xhbnRpX2lkID09IGsuYmFnbGFu'
        'dGlfaWQsCiAgICAgICAgICAgICAgICBNYWxpeWV0Lm1hbGl5ZXRfdGlwICE9ICdEZXZy'
        'ZWRlbiBLRFYnLAogICAgICAgICAgICAgICAgTWFsaXlldC5pZCAhPSBrLmlkKS5hbGwo'
        'KQogICAgICAgICAgICBpZiBsZW4oYWRheWxhcikgPT0gMToKICAgICAgICAgICAgICAg'
        'IGdydXBsYW5hY2FrLmFwcGVuZCgoYWRheWxhclswXSwgaykpCiAgICAgICAgICAgIGVs'
        'aWYgbGVuKGFkYXlsYXIpID4gMToKICAgICAgICAgICAgICAgIGNva2x1LmFwcGVuZCgo'
        'ay5pZCwgW2EuaWQgZm9yIGEgaW4gYWRheWxhcl0pKQogICAgICAgICAgICBlbHNlOgog'
        'ICAgICAgICAgICAgICAgaXBzaXouYXBwZW5kKGsuaWQpCgogICAgICAgIHByaW50KCc9'
        'JyAqIDY4KQogICAgICAgIHByaW50KCcgIEfDlsOHIERaMSDigJQgbWFsaXlldCBncnVw'
        'bGFtYScpCiAgICAgICAgcHJpbnQoJz0nICogNjgpCiAgICAgICAgcHJpbnQoZicgIGdy'
        'dXAga2ltbGnEn2kgb2xtYXlhbiBLRFYgc2F0xLFyxLEgOiB7bGVuKGtkdmxlcil9JykK'
        'ICAgICAgICBwcmludChmJyAgZcWfbGXFn2VuIMOnaWZ0IChncnVwbGFuYWNhaykgICAg'
        'ICA6IHtsZW4oZ3J1cGxhbmFjYWspfScpCiAgICAgICAgcHJpbnQoZicgIGJpcmRlbiDD'
        'p29rIGFkYXkgKERPS1VOVUxNQVopICAgIDoge2xlbihjb2tsdSl9JykKICAgICAgICBw'
        'cmludChmJyAgZcWfbGXFn3RpcmlsZW1leWVuICAgICAgICAgICAgICAgIDoge2xlbihp'
        'cHNpeil9JykKCiAgICAgICAgaWYgZ3J1cGxhbmFjYWs6CiAgICAgICAgICAgIHByaW50'
        'KCkKICAgICAgICAgICAgcHJpbnQoJyAgR1JVUExBTkFDQUs6JykKICAgICAgICAgICAg'
        'Zm9yIG5ldCwga2R2IGluIGdydXBsYW5hY2FrWzoyMF06CiAgICAgICAgICAgICAgICBw'
        'cmludChmJyAgICB7bmV0LmlkfSAoe25ldC5tYWxpeWV0X3RpcH0pICsge2tkdi5pZH0g'
        'KEtEViknCiAgICAgICAgICAgICAgICAgICAgICBmJyAg4oaSICB7bmV0LmJhZ2xhbnRp'
        'X2lkfSAgZmF0dXJhIHtuZXQuZmF0dXJhX25vfScpCiAgICAgICAgICAgIGlmIGxlbihn'
        'cnVwbGFuYWNhaykgPiAyMDoKICAgICAgICAgICAgICAgIHByaW50KGYnICAgIOKApiB2'
        'ZSB7bGVuKGdydXBsYW5hY2FrKSAtIDIwfSDDp2lmdCBkYWhhJykKCiAgICAgICAgaWYg'
        'Y29rbHU6CiAgICAgICAgICAgIHByaW50KCkKICAgICAgICAgICAgcHJpbnQoJyAgQsSw'
        'UkRFTiDDh09LIEFEQVkg4oCUIGVsbGUgYmFrbWFuIGdlcmVrOicpCiAgICAgICAgICAg'
        'IGZvciBrZHZfaWQsIGFkYXlsYXIgaW4gY29rbHVbOjEwXToKICAgICAgICAgICAgICAg'
        'IHByaW50KGYnICAgIHtrZHZfaWR9IOKGkiB7YWRheWxhcn0nKQoKICAgICAgICBpZiBp'
        'cHNpejoKICAgICAgICAgICAgcHJpbnQoKQogICAgICAgICAgICBwcmludCgnICBFxZ5M'
        'RcWeVMSwUsSwTEVNRVlFTiAoZmF0dXJhIG5vIGJvxZ8geWEgZGEga2FyxZ/EsWzEscSf'
        'xLEgeW9rKTonKQogICAgICAgICAgICBwcmludChmJyAgICB7IiwgIi5qb2luKGlwc2l6'
        'WzoxNV0pfScKICAgICAgICAgICAgICAgICAgKyAoZicg4oCmICgre2xlbihpcHNpeikg'
        'LSAxNX0pJyBpZiBsZW4oaXBzaXopID4gMTUgZWxzZSAnJykpCiAgICAgICAgICAgIHBy'
        'aW50KCcgICAgQnVubGFyIMO2a3PDvHoga2FsYWJpbGlyOyBzaWxlcmtlbiB0ZWsgdGVr'
        'IGdpdC4nKQoKICAgICAgICBpZiBub3QgVVlHVUxBOgogICAgICAgICAgICBwcmludCgp'
        'CiAgICAgICAgICAgIHByaW50KCc9JyAqIDY4KQogICAgICAgICAgICBwcmludCgnICBS'
        'QVBPUiDigJQgaGnDp2JpciDFn2V5IHlhesSxbG1hZMSxLiBVeWd1bGFtYWsgacOnaW46'
        'JykKICAgICAgICAgICAgcHJpbnQoJyAgICAgIHB5dGhvbjMgZ29jX2R6MS5weSAtLXV5'
        'Z3VsYScpCiAgICAgICAgICAgIHByaW50KCc9JyAqIDY4KQogICAgICAgICAgICByZXR1'
        'cm4gMAoKICAgICAgICBpZiBub3QgZ3J1cGxhbmFjYWs6CiAgICAgICAgICAgIHByaW50'
        'KCkKICAgICAgICAgICAgcHJpbnQoJyAgWWFwYWNhayBiaXIgxZ9leSB5b2suJykKICAg'
        'ICAgICAgICAgcmV0dXJuIDAKCiAgICAgICAgaW1wb3J0IHV1aWQKICAgICAgICBmb3Ig'
        'bmV0LCBrZHYgaW4gZ3J1cGxhbmFjYWs6CiAgICAgICAgICAgIGdydXAgPSBuZXQuZ3J1'
        'cF9pZCBvciAoJ01HUi0nICsgdXVpZC51dWlkNCgpLmhleFs6Nl0udXBwZXIoKSkKICAg'
        'ICAgICAgICAgbmV0LmdydXBfaWQgPSBncnVwCiAgICAgICAgICAgIGtkdi5ncnVwX2lk'
        'ID0gZ3J1cAogICAgICAgIGRiLnNlc3Npb24uY29tbWl0KCkKICAgICAgICBwcmludCgp'
        'CiAgICAgICAgcHJpbnQoJz0nICogNjgpCiAgICAgICAgcHJpbnQoZicgIOKckyB7bGVu'
        'KGdydXBsYW5hY2FrKX0gw6dpZnQgZ3J1cGxhbmTEsS4nKQogICAgICAgIHByaW50KCcg'
        'IFRla3JhciDDp2FsxLHFn3TEsXLEsXJzYW4gInlhcGFjYWsgYmlyIMWfZXkgeW9rIiBk'
        'ZW1lbGkuJykKICAgICAgICBwcmludCgnPScgKiA2OCkKICAgICAgICByZXR1cm4gMAoK'
        'CmlmIF9fbmFtZV9fID09ICdfX21haW5fXyc6CiAgICBzeXMuZXhpdChhbmEoKSkK'
    ),
}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA DZ1 — MALIYET <-> CARI ZINCIRI')
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
        print('    python3 yama_dz1.py            # rapor')
        print('    python3 yama_dz1.py --uygula')
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
        print('  ⊙ Yama DZ1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_dz1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_dz1'
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
    print('    2) python3 goc_dz1.py           <- ONCE RAPOR')
    print('    3) python3 goc_dz1.py --uygula')
    print('    4) Tarayicida Ctrl+F5')
    print('    5) venv/bin/python -m pytest tests/test_kritik.py -q')
    print()
    print('  BAKILACAK YER')
    print('    Finans -> Maliyetler: dagitilmis bir maliyeti sil.')
    print('    Ikinci onay kutusu KAPSAMI yazmali, ornegin:')
    print('      "2 maliyet satiri (2 kayda dagitilmis) - 2 KDV')
    print('       satiri - 1 cari hareket birlikte silinecek."')
    print('    Sonra Finans -> Cari: ayni seyi oradan dene.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

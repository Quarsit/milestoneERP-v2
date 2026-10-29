#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA TS1 — TAHSİLATI SİLİNCE PARA KASADA KALIYORDU
===================================================

ÖNKOŞUL: **yama_hy1.py uygulanmış olmalı.** Betik denetliyor.
Şema yok, göç yok. **Bu bir PARA hatası.**

HY1'in ardından bir sınıf daha taradım: SD4 sınıfı — yazılmış ama
hiçbir ekranın çağırmadığı uç. Tarama 275 `/api/` ucunu gezdi ve
oradan bu çıktı.

═══ HATA ═══

Bir tahsilatı silmenin İKİ yolu vardı ve ikisi aynı işi yapmıyordu:

  · `DELETE /api/tahsilat/<id>` kasayı geri alıyordu — ama o ucu
    **çağıran hiçbir ekran yok.**
  · `DELETE /api/cari/hareket/<id>` cari ekranındaki ✕ düğmesinin
    çağırdığı yol — ve kasayı geri **almıyordu.**

Test takımı yeşildi, çünkü TH2 testi birinciyi koşuyor. Yani
doğrulanan yol ile senin ulaşabildiğin yol aynı şey değildi.

ÖLÇÜLDÜ — 10.000 USD fatura, 4.000 USD tahsilat, sonra sil:

      silme yolu                  fatura      kasa
      ──────────────────────────────────────────────────
      /api/tahsilat/<id>          Kesildi     0,00       ✓
      /api/cari/hareket/<id>      Kesildi     4.000,00   ✗
      ← ekrandaki ✕

İkincisinde tahsilat kaydı silindi, fatura yeniden açıldı, ama
**para kasada kaldı** ve kasa hareketi de duruyor. Kasa, karşılığı
olmayan bir tahsilatı gösteriyor.

Düzeltmeden sonra ikisi de: fatura Kesildi · kasa 0,00 · kasa
hareketi 0.

═══ SEBEP — BU SINIFIN ÜÇÜNCÜ ÖRNEĞİ ═══

Cari hareket silme, kasa kaydını `baglanti_tip='cari_hareket'` ile
arıyordu. Oysa tahsilatın kasa kaydı `baglanti_tip='tahsilat'` ile
yazılıyor. Süzgeç **hedefini vurmuyordu.**

AF1'deki ölü çek süzgecinin aynısı: koruma yazılmış, doğru anlatılmış,
ama yanlış bağlantı tipine bakıyor. Üçüncü kez aynı şey.

═══ DÜZELTME ═══

Geri alma mantığı tek bir yardımcıya taşındı
(`_hareket_kasa_geri_al`) ve **iki uç da ondan geçiyor.** İki ayrı
kopya zamanla yine ayrışırdı — EM1 ve AF1'de öğrendiğimiz şey.

Yardımcı iki bağlantı tipini de arıyor, eski kayıtlar için faturaya
bağlı ±120 sn penceresini de koruyor (o mantık TH2'den geliyor,
olduğu gibi taşındı).

**HATAYI ARTIK YUTMUYOR.** Cari hareket silmedeki eski kopya
`try/except Exception: pass` içindeydi: bakiye düzeltmesi patlasa
hareket yine silinecekti ve kimse bilmeyecekti. Artık hata yukarı
çıkıyor — istek 500 döner ve hiçbir şey silinmez. Sessizce yarım iş
yapmaktansa hiç yapmamak.

═══ KASADA FAZLALIK VARSA ═══

Bu hatayla silinmiş tahsilatların parası kasada kalmış olabilir.
Düzeltme geçmişe dokunmuyor — bundan sonrası doğru. Kasa bakiyeni
tutturamadığın bir yer varsa sebebi bu olabilir; istersen hangi kasa
hareketlerinin karşılığı olmayan bir tahsilata bağlı olduğunu bulan
salt-okunur bir tarama yazarım.

═══ TARAMANIN GERİ KALANI — DÜZELTMEDİM ═══

275 `/api/` ucundan 7'si hiçbir ekrandan çağrılmıyor. Bunlar
**yazılmış ama bağlanmamış özellikler** — düzeltme değil, karar
gerektiriyorlar:

  · `GET /api/blok/<blok_no>/izleme` — bir bloğun tüm yaşam
    döngüsü: kesimler, maliyetler, kârlılık. Hem orijinal hem
    üretim blok numarasından arıyor. Yerine başka yol yok.
  · `GET /api/rapor/donusum` — teklif dönüşüm oranı ve kayıp
    sebepleri. Paydası özenle düşünülmüş (iptal ve bekleyen
    girmiyor), sonra bağlanmamış.
  · `GET /api/fatura/ettn/<ettn>` — GİB portalındaki UUID'den
    faturayı bulma. Mutabakat için yazılmış.
  · `PUT /api/kasa/<id>` — kasa adı/dövizi/açılış bakiyesi
    düzenleme. Ekranda düzenle düğmesi yok: yanlış kurulmuş bir
    kasayı düzeltemiyorsun. SD4'teki şikâyetin aynısı.
  · `PATCH /api/satislar/<id>/fatura-bilgi` — satışın fatura no /
    tarih / not alanları.

Hangisini bağlamak istersin? Ekran işi, karar senin.

Ayrıca üç **ölü kopya** var: `POST /api/stok/toplu_import` (ekran
satır satır `/api/stok/ekle` çağırıyor), `GET /api/uretici` (ekran
`/api/cari`yi süzüyor), `GET /api/yetkilerim` (yetkiler sunucu
tarafından şablona geliyor) ve `GET /api/musteri/detay`. Zararsız
duruyorlar ama her biri ikinci bir doğruluk kaynağı — bu yamanın
hatası tam olarak öyle doğdu.

`/api/diag/*` uçları sayılmadı: elle çağrılmak üzere yazılmışlar.

═══ DOĞRULANDI ═══
  269 test geçti (266 + 3). Üçü de taban üzerinde BAŞARISIZ oluyor.
  TH2 (eski test) hâlâ geçiyor — eski yol bozulmadı.

DOSYALAR
--------
  flask_app.py           ortak kasa geri alma kapısı, iki çağrı yeri
  tests/test_kritik.py   3 yeni test

KULLANIM
--------
  python3 yama_ts1.py            # RAPOR
  python3 yama_ts1.py --uygula
  sudo systemctl restart milestone-erp
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
    'flask_app.py': 'TS1 · İKİ SİLME YOLU, İKİ FARKLI GERÇEK',
    'tests/test_kritik.py': 'def test_ts1_iki_silme_yolu_ayni_sonucu_veriyor',
}
ONKOSUL = {
    'flask_app.py': 'LG1 · BURADA TANIMSIZ BIR AD VARDI',
    'tests/test_kritik.py': 'def test_hy1_setattr_beyaz_listelerinde_hayalet_alan_yok',
}
TAM_YAZILAN = []

DEGISIKLIKLER = [
    ('flask_app.py', 'TS1 · flask_app.py blok 1',
     r'''    @app.route('/api/cari/hareket/<hareket_id>', methods=['DELETE'])
''',
     r'''    def _hareket_kasa_geri_al(hareket):
        """Bir cari hareketin bağlı kasa hareketlerini geri alır.

        ══════════════════════════════════════════════════════════
         TS1 · İKİ SİLME YOLU, İKİ FARKLI GERÇEK
        ══════════════════════════════════════════════════════════

        Bir tahsilatı silmenin İKİ yolu vardı ve ikisi aynı işi
        yapmıyordu:

          · `DELETE /api/tahsilat/<id>` kasayı geri alıyordu —
            ama o ucu ÇAĞIRAN hiçbir ekran yok. TH2 testi onu
            koşuyor, o yüzden takım yeşil.
          · `DELETE /api/cari/hareket/<id>` cari ekranındaki ✕
            düğmesinin çağırdığı yol — ve kasayı geri ALMIYORDU.

        Sebep: bu yol kasa kaydını `baglanti_tip='cari_hareket'`
        ile arıyordu, oysa tahsilatın kasa kaydı
        `baglanti_tip='tahsilat'` ile yazılıyor (28419). Süzgeç
        hedefini vurmuyordu — AF1'deki ölü çek süzgecinin aynısı,
        bu sınıfın üçüncü örneği.

        ÖLÇÜLDÜ — 10.000 USD fatura, 4.000 USD tahsilat, sonra sil:

            /api/tahsilat/<id>       fatura Kesildi · kasa     0,00 ✓
            /api/cari/hareket/<id>   fatura Kesildi · kasa 4.000,00 ✗

        İkincisinde tahsilat kaydı silindi, fatura açıldı, ama para
        kasada kaldı ve kasa hareketi de duruyor: kasa, karşılığı
        olmayan bir tahsilatı gösteriyor.

        Artık tek yardımcı var, iki uç da ondan geçiyor. İki ayrı
        kopya zamanla yine ayrışırdı — EM1 ve AF1'de öğrendiğimiz
        şey.

        HATAYI YUTMUYOR. Eski kopya `try/except Exception: pass`
        içindeydi: bakiye düzeltmesi patlasa hareket yine
        silinecekti ve kimse bilmeyecekti. Artık hata yukarı
        çıkıyor; istek 500 döner ve hiçbir şey silinmez — sessizce
        yarım iş yapmaktansa hiç yapmamak.

        Döner: geri alınan kasalar için okunur açıklama listesi.
        """
        hid = hareket.id
        bagli = KasaHareket.query.filter(
            KasaHareket.baglanti_tip.in_(('cari_hareket', 'tahsilat')),
            KasaHareket.baglanti_id == hid).all()

        # ── ESKI KAYITLAR FATURAYA BAGLIYDI ──
        # Ayni faturanin birden cok tahsilati olabilir: tahsilatla
        # ayni istekte (+-120 sn) olusan ve zamanca EN YAKIN olan
        # kayit alinir. Esitlik varsa ya da aday yoksa dokunulmaz —
        # yanlis kasa kaydini silmek, hic silmemekten kotu.
        if (not bagli and hareket.baglanti_tip == 'fatura'
                and hareket.baglanti_id):
            adaylar = KasaHareket.query.filter_by(
                baglanti_tip='tahsilat',
                baglanti_id=hareket.baglanti_id).all()
            ref = getattr(hareket, 'guncelleme', None)
            if ref and adaylar:
                yakin = sorted(
                    ((abs((a.olusturma - ref).total_seconds()), a)
                     for a in adaylar
                     if a.olusturma
                     and abs((a.olusturma - ref).total_seconds()) <= 120),
                    key=lambda x: x[0])
                if yakin and (len(yakin) == 1 or yakin[0][0] < yakin[1][0]):
                    bagli = [yakin[0][1]]

        geri = []
        for bkh in bagli:
            bk = Kasa.query.get(bkh.kasa_id)
            if bk:
                t = q2(bkh.tutar or 0)
                bk.bakiye = q2((bk.bakiye or 0)
                               + (-t if bkh.tip == 'giris' else t))
                geri.append(f'{bk.ad} '
                            f'{"-" if bkh.tip == "giris" else "+"}'
                            f'{t:,.2f} {bk.doviz}')
            db.session.delete(bkh)
        return geri

    @app.route('/api/cari/hareket/<hareket_id>', methods=['DELETE'])
'''),
    ('flask_app.py', 'TS1 · flask_app.py blok 2',
     r'''        # Bağlı KASA hareketi varsa geri al (bakiyeyi düzelt + kaydı sil)
        silinen_kasa = None
        try:
            bagli_khs = KasaHareket.query.filter_by(
                baglanti_tip='cari_hareket', baglanti_id=hareket_id).all()
            for bkh in bagli_khs:
                bk = Kasa.query.get(bkh.kasa_id)
                if bk:
                    fark = q2(bkh.tutar or 0)
                    bk.bakiye = q2((bk.bakiye or 0) + (-fark if bkh.tip == 'giris' else fark))
                    silinen_kasa = bk.ad
                db.session.delete(bkh)
        except Exception:
            pass
''',
     r'''        # TS1: bagli kasa hareketi ORTAK yardimcidan geri alinir.
        # Eskiden burada kendi kopyasi vardi ve yalniz
        # `baglanti_tip='cari_hareket'` ariyordu; tahsilatin kasa
        # kaydi `'tahsilat'` ile yazildigi icin hic bulunmuyordu.
        _kasa_geri = _hareket_kasa_geri_al(hareket)
        silinen_kasa = ', '.join(_kasa_geri) if _kasa_geri else None
'''),
    ('flask_app.py', 'TS1 · flask_app.py blok 3',
     r'''        bagli = KasaHareket.query.filter_by(
            baglanti_tip='tahsilat', baglanti_id=hareket_id).all()
        if not bagli and fatura_id:
            # Eski kayitlar faturaya bagliydi. Ayni faturanin birden
            # cok tahsilati olabilir: tahsilatla ayni istekte (+-120 sn)
            # olusan ve zamanca EN YAKIN olan kayit alinir. Esitlik
            # varsa ya da aday yoksa dokunulmaz — yanlis kasa kaydini
            # silmek, hic silmemekten kotu.
            adaylar = KasaHareket.query.filter_by(
                baglanti_tip='tahsilat', baglanti_id=fatura_id).all()
            ref = getattr(h, 'guncelleme', None)
            if ref and adaylar:
                yakin = sorted(
                    ((abs((a.olusturma - ref).total_seconds()), a) for a in adaylar
                     if a.olusturma and abs((a.olusturma - ref).total_seconds()) <= 120),
                    key=lambda x: x[0])
                if yakin and (len(yakin) == 1 or yakin[0][0] < yakin[1][0]):
                    bagli = [yakin[0][1]]
        kasa_geri = []
        for bkh in bagli:
            bk = Kasa.query.get(bkh.kasa_id)
            if bk:
                t = q2(bkh.tutar or 0)
                bk.bakiye = q2((bk.bakiye or 0) + (-t if bkh.tip == 'giris' else t))
                kasa_geri.append(f'{bk.ad} {"-" if bkh.tip == "giris" else "+"}{t:,.2f} {bk.doviz}')
            db.session.delete(bkh)
''',
     r'''        #
        # TS1: bu hesap artik `_hareket_kasa_geri_al`da — ayni isi
        # yapan ikinci bir kopya cari hareket silmede duruyordu ve
        # YANLIS baglanti_tip ariyordu. Tek kaynak.
        kasa_geri = _hareket_kasa_geri_al(h)
'''),
    ('tests/test_kritik.py', 'TS1 · tests/test_kritik.py blok 1',
     r'''    assert any(m == 'CariHareket' for _, _, _, m, _ in bulgular), bulgular
''',
     r'''    assert any(m == 'CariHareket' for _, _, _, m, _ in bulgular), bulgular


# ══════════════════════════════════════════════════════════════════
#  TS1 · İKİ SİLME YOLU AYNI ŞEYİ YAPMALI
#
#  Bir tahsilatı silmenin iki yolu vardı ve ikisi aynı işi
#  yapmıyordu:
#
#    · `DELETE /api/tahsilat/<id>` kasayı geri alıyordu — ama o ucu
#      çağıran hiçbir ekran yok. TH2 testi onu koşuyor, takım yeşil.
#    · `DELETE /api/cari/hareket/<id>` cari ekranındaki ✕ düğmesinin
#      yolu — ve kasayı geri ALMIYORDU.
#
#  Sebep: ikinci yol kasa kaydını `baglanti_tip='cari_hareket'` ile
#  arıyordu, oysa tahsilatın kasa kaydı `'tahsilat'` ile yazılıyor.
#  Süzgeç hedefini vurmuyordu — AF1'deki ölü çek süzgecinin aynısı.
#
#  ÖLÇÜLDÜ — 10.000 USD fatura, 4.000 USD tahsilat, sonra sil:
#      /api/tahsilat/<id>      fatura Kesildi · kasa     0,00 ✓
#      /api/cari/hareket/<id>  fatura Kesildi · kasa 4.000,00 ✗
# ══════════════════════════════════════════════════════════════════
_TS1_T = date(2026, 2, 19)      # baska test bu gune kur yazmiyor


def _ts1_kur(fid, kasa_adi):
    """Temiz fatura + kasa. Kasa kimligini doner."""
    from models import Fatura, Kasa, DovizKur
    if not DovizKur.query.filter_by(doviz='USD', tarih=_TS1_T).first():
        db.session.add(DovizKur(doviz='USD', tarih=_TS1_T,
                                alis=40.0, satis=40.0, efektif=40.0))
    if not db.session.get(Cari, 'MUS-TS1'):
        db.session.add(Cari(id='MUS-TS1', unvan='MUSTERI TS1',
                            cari_tip='Müşteri'))
    k = Kasa(ad=kasa_adi, doviz='USD', bakiye=0)
    db.session.add(k)
    db.session.add(Fatura(
        id=fid, fatura_no=fid, cari_id='MUS-TS1', musteri='MUSTERI TS1',
        yon='satis', durum='Kesildi', doviz='USD', toplam=10000,
        ara_toplam=10000, fatura_tarihi=_TS1_T))
    db.session.commit()
    return k.id


def _ts1_durum(fid, kid):
    from models import Fatura, Kasa, KasaHareket
    with fa.app.app_context():
        f = db.session.get(Fatura, fid)
        hs = CariHareket.query.filter_by(
            baglanti_tip='fatura', baglanti_id=fid, kaynak='tahsilat').all()
        return (f.durum, float(db.session.get(Kasa, kid).bakiye or 0),
                [h.id for h in hs],
                KasaHareket.query.filter_by(kasa_id=kid).count())


def _ts1_senaryo(c, fid, kasa_adi, yol_kalibi):
    """Tahsilat gir, verilen yoldan sil, (durum, kasa, hareket) döner."""
    with fa.app.app_context():
        kid = _ts1_kur(fid, kasa_adi)
    r = c.post(f'/api/fatura/{fid}/tahsilat', headers=H,
               json={'tutar': 4000, 'kasa_id': kid, 'doviz': 'USD'})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    _d, _bakiye, _hids, _kh = _ts1_durum(fid, kid)
    assert _hids, 'tahsilat hareketi oluşmadı'
    assert abs(_bakiye - 4000) < 0.01, f'kasa {_bakiye} — 4.000 olmalı'
    assert _kh == 1, _kh
    r2 = c.delete(yol_kalibi.format(hid=_hids[0]), headers=H)
    assert r2.status_code == 200, r2.get_data(as_text=True)[:200]
    return _ts1_durum(fid, kid)


def test_ts1_cari_ekranindan_tahsilat_silinince_kasa_geri_alinir():
    """Cari ekranındaki ✕ kasayı da geri almalı.

    Kullanıcının ulaşabildiği yol bu. Eskiden para kasada kalıyordu:
    kasa, karşılığı olmayan bir tahsilatı gösteriyordu."""
    c = istemci('admin', 'ADMIN')
    durum, bakiye, hids, kh = _ts1_senaryo(
        c, 'FT-TS1A', 'TS1 KASA A', '/api/cari/hareket/{hid}')
    assert not hids, 'tahsilat hareketi silinmemiş'
    assert durum == 'Kesildi', durum
    assert abs(bakiye) < 0.01, \
        f'kasada {bakiye:,.2f} kaldı — tahsilat silindi ama para duruyor'
    assert kh == 0, f'{kh} kasa hareketi duruyor'


def test_ts1_iki_silme_yolu_ayni_sonucu_veriyor():
    """`/api/tahsilat/<id>` ile `/api/cari/hareket/<id>` eş olmalı.

    İkisi de aynı şeyi siliyor; farklı davranmaları, hangisinin
    çağrıldığına göre farklı bir gerçek üretir."""
    c = istemci('admin', 'ADMIN')
    a = _ts1_senaryo(c, 'FT-TS1B', 'TS1 KASA B', '/api/tahsilat/{hid}')
    b = _ts1_senaryo(c, 'FT-TS1C', 'TS1 KASA C', '/api/cari/hareket/{hid}')
    # (durum, kasa bakiyesi, kalan hareketler, kasa hareketi sayisi)
    assert a[0] == b[0], (a, b)
    assert abs(a[1] - b[1]) < 0.01, f'kasa bakiyeleri ayrışıyor: {a[1]} / {b[1]}'
    assert a[2] == b[2] == [], (a, b)
    assert a[3] == b[3] == 0, (a, b)


def test_ts1_kasa_geri_alma_tek_kaynaktan():
    """Geri alma mantığı TEK yerde olmalı, iki kopya değil.

    İki kopya zamanla ayrışır — EM1 ve AF1'de olan tam buydu. Test
    paylaşılan kapıyı tutuyor, kopyaların içeriğini değil."""
    import io as _io
    m = _io.open(os.path.join(KOK, 'flask_app.py'),
                 encoding='utf-8').read().replace('\r\n', '\n')
    assert 'def _hareket_kasa_geri_al(' in m, 'ortak kapı yok'
    assert m.count('_hareket_kasa_geri_al(') >= 3, \
        'iki uç da ortak kapıdan geçmiyor'
    # Eski kopyanin imzasi: yalniz 'cari_hareket' arayan suzgec
    assert "baglanti_tip='cari_hareket', baglanti_id=hareket_id" not in m, \
        'cari hareket silmede eski kasa kopyası duruyor'
    # Para yazan is artik sessizce yutulmuyor
    _i = m.index('def _hareket_kasa_geri_al(')
    _govde = m[_i:m.index('@app.route', _i)]
    # Belgelendirme dizgisi eski kopyadan SOZ EDIYOR; aranan sey
    # KOD. Satir basindaki girintili `except` ifadesine bakiyoruz —
    # ilk hali metin icinde arayip kendi yorumuma takilmisti.
    import re as _re
    assert not _re.search(r'^\s+except\b', _govde, _re.M), \
        'kasa geri alma hatayı yutuyor — yarım iş sessizce geçer'
'''),
]

TAM_ICERIK = {}
def _tam_dosya(ad):
    """TAM_ICERIK'ten çözülmüş dosya metni."""
    return base64.b64decode(TAM_ICERIK[ad]).decode('utf-8')


def main():
    print('=' * 70)
    print('  YAMA TS1 — TAHSİLATI SİLİNCE PARA KASADA KALIYORDU')
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
        print('    python3 yama_ts1.py            # rapor')
        print('    python3 yama_ts1.py --uygula')
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
        print('  ⊙ Yama TS1 zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_ts1.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        if os.path.exists(yol):
            yedek = yol + '.yedek_ts1'
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
    print('    2) venv/bin/python -m pytest tests/test_kritik.py -q   # 269')
    print()
    print('  BAKILACAK YER')
    print('    Cari -> bir tahsilat satirini ✕ ile sil. Artik kasa')
    print('    bakiyesi de geri aliniyor ve mesaj hangi kasadan ne')
    print('    kadar dustugunu yaziyor.')
    print()
    print('  GECMISE DOKUNULMADI')
    print('    Bu hatayla silinmis tahsilatlarin parasi kasada kalmis')
    print('    olabilir. Kasa bakiyeni tutturamadigin bir yer varsa')
    print('    sebebi bu olabilir — soyle, taramasini yazarim.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

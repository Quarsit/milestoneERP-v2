#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAMA MF2 — ÇOKLU FİRMA, 2/4: OKUMA SÜZGECİ
===========================================

ÖNKOŞUL: MF1 uygulanmış ve goc_mf1.py çalıştırılmış olmalı.

    MF1  şema + yazarken damga        ✓
    MF2  okuma süzgeci                ← buradasın
    MF3  arayüz (firma seçici)
    MF4  sıfırlama modları + testler

NE YAPAR
--------
Her SELECT'e aktif firmanın şartını ekler. 699 sorgunun HİÇBİRİNE
dokunulmaz; süzgeç tek yerde durur, yeni ekran yazarken eklemeyi
unutmak diye bir şey olmaz.

Bu yamadan sonra da sistem TEK firmayla, bugünküyle aynı görünür —
çünkü tek firma var ve her şey ona damgalı. Değişen şey, ikinci firma
açıldığında verinin AYRILACAK olması. Firma seçici MF3'te.

ÜÇ AYRI SÜZGEÇ
--------------
1) FirmaKapsamli taşıyan 28 tablo → `firma_id = aktif`

2) `veriler` → `firma_id = aktif VEYA firma_id IS NULL`
   Ortak referans listeleri (cins, yüzey, ülke) her firmada görünür;
   logo/unvan/SMTP yalnızca kendi firmasında.

3) `cariler` → `cari_firma` üyeliğinden
   Kart ortak ama GÖRÜNÜRLÜK üyelikten geliyor: aynı müşteri iki
   firmaya da bağlanabilir, firmanın kendi müşterisi ötekinde
   görünmez.

NEDEN MIXIN LAMBDA'SI — CRM-C2'nin DERSİ BURADA GEÇERLİ DEĞİL
-------------------------------------------------------------
Mevcut erişim süzgeci (CRM-C2) şunu yazıyor:

    # DUZ IFADE — lambda DEGIL.
    # with_loader_criteria lambdalari KOD NESNESINE gore
    # onbellekliyor; bir dongude ayni satirdan uretilen iki lambda
    # birbirine karisiyor ve suzgec yanlis MODELE uygulaniyor.

O tuzak bir DÖNGÜDE farklı MODELLER için lambda üretmekten doğuyor.
Burada tek satırda tek lambda var ve değişen şey model değil, firma
DEĞERİ. Ölçüldü: 3 firma arasında 300 rastgele geçişte 0 yanlış
sonuç. Alternatifi (28 modele ayrı düz ifade) de doğru çalışıyor ama
sorgu başına iki katı maliyetli:

    mixin lambda : 1000 sorgu 0,84 s
    28 düz ifade : 1000 sorgu 1,76 s
    süzgeçsiz    : 1000 sorgu 0,42 s

Mixin biçimi ayrıca YENİ MODELİ kendiliğinden kapsar; liste tutmak
unutma riski taşırdı.

ÇIKIŞ KAPISI
------------
`firma_atla()` bağlam yöneticisi süzgeci geçici kapatır — firma
yönetim ekranı, göç ve sıfırlama betikleri için. CRM-C2'deki
`erisim_atla()` ile aynı desen: tek ve açık kapı, her kullanımı
gerekçesiyle yazılır.

İstek bağlamı YOKSA süzgeç hiç çalışmaz (CLI, arka plan görevi,
denetim betiği) — bunlar zaten yönetici işlemleri.

KAPSAM DIŞI
-----------
  kullanicilar, doviz_kur   ortak veri
  cari_kisi, cari_erisim    cari kartının parçası, kart ortak
  audit_log                 admin bütün firmaların izini görmeli

DOSYALAR
--------
  flask_app.py  (süzgeç kancası)
  models.py     (yeni cari aktif firmaya bağlanır)

CARİ ÜYELİĞİ — ÖLÇÜLEN AÇIK
---------------------------
Süzgeç devreye girince 27 test düştü, hepsi aynı kök nedenden: yeni
açılan cari `cari_firma` üyeliği almıyordu, dolayısıyla hiçbir
firmada görünmüyordu. Kaydediliyor ama kayboluyordu. Artık yazma
kancası üyeliği de kuruyor.

KULLANIM
--------
  python3 yama_mf2.py            # RAPOR
  python3 yama_mf2.py --uygula   # uygular, yanına .yedek_mf2 bırakır
  sudo systemctl restart milestone-erp
"""

import os
import sys
import shutil
import py_compile
import tempfile

UYGULA = '--uygula' in sys.argv
IMZA = 'MF2'
ONKOSUL = 'MF1'

# DOSYA BASINA IMZA — duz "MF2" aramak YANILTIYOR: MF1 yamasinin
# aciklamalari zaten "MF2'de gelecek" diye MF2'den soz ediyor ve
# models.py "zaten uygulanmis" sayiliyordu. Imza, yamanin GERCEKTEN
# ekledigi fonksiyon adi.
DOSYA_IMZA = {
    'flask_app.py': '_firma_suzgeci',
    'models.py': '_cari_firma_uyeligi',
}
KOK = os.path.dirname(os.path.abspath(__file__))


BLOK = '''    # ══════════════════════════════════════════════════════════
    #  ÇOKLU FİRMA — OKUMA SÜZGECİ  (MF2)
    # ══════════════════════════════════════════════════════════
    #  Her SELECT'e aktif firmanın şartını ekler. 699 sorgunun
    #  hiçbirine dokunulmadı; süzgeç tek yerde duruyor.
    #
    #  Yukarıdaki CRM-C2 süzgeciyle BİRLİKTE çalışır ve ikisi VE ile
    #  birleşir: satışçı yalnızca KENDİ carilerini, onların da
    #  yalnızca AKTİF FİRMADA görünenlerini görür. Ölçüldü.
    #
    #  Mixin lambda'sı kullanılıyor. CRM-C2'deki "düz ifade kullan"
    #  uyarısı bir DÖNGÜDE farklı MODELLER için lambda üretmeye
    #  dair; burada tek satırda tek lambda var ve değişen şey model
    #  değil firma DEĞERİ. 3 firma arasında 300 rastgele geçişte 0
    #  yanlış sonuç. 28 modele ayrı düz ifade de doğru çalışıyor ama
    #  sorgu başına iki kat maliyetli (1,76 s / 0,84 s / 1000 sorgu).

    from models import (FirmaKapsamli as _FirmaKapsamli,
                        CariFirma as _CariFirma,
                        firma_cozucu_ayarla as _firma_cozucu_ayarla,
                        _varsayilan_firma_id as _varsayilan_firma)
    from sqlalchemy import select as _sa_select

    @_contextmanager
    def firma_atla():
        """Firma süzgecini GEÇİCİ kapatır — YÖNETİCİ işlemleri için.

        Firma yönetim ekranı bütün firmaları listelemek zorunda;
        sıfırlama ve göç betikleri de firma ayrımı gözetmez.
        CRM-C2'deki `erisim_atla()` ile aynı desen: tek ve açık kapı.
        Her kullanımı GEREKÇESİYLE yazılmalı — dağılırsa süzgeç
        sessizce devre dışı kalır.
        """
        onceki = getattr(g, 'firma_atla_bayrak', False)
        g.firma_atla_bayrak = True
        try:
            yield
        finally:
            g.firma_atla_bayrak = onceki

    def aktif_firma_id():
        """Şu an hangi firmada çalışılıyor.

        İstek bağlamı yoksa None döner ve süzgeç devreye girmez:
        CLI, arka plan görevi ve denetim betikleri yönetici
        işlemleridir, firma ayrımı gözetmezler.

        Sonuç istek başına `g` üzerinde saklanır. CRM-C2'de ölçülen
        tuzak burada da geçerliydi: her sorguda yeni bir sorgu
        doğurmak kancayı tekrar tetikler.
        """
        if not has_request_context():
            return None
        if getattr(g, 'firma_atla_bayrak', False):
            return None
        _onbellek = getattr(g, '_mf2_firma', None)
        if _onbellek is not None:
            return _onbellek
        _f = session.get('firma_id')
        if not _f:
            # Firma seçici MF3'te geliyor; o zamana kadar (ve seçim
            # yapılmamışsa) varsayılan firma. HAM SQL okur, ORM değil
            # — ORM sorgusu bu kancayı yeniden tetiklerdi.
            _f = _varsayilan_firma()
        g._mf2_firma = _f
        return _f

    # models.py'deki YAZMA damgası da aynı kaynaktan beslensin:
    # okuma ve yazma iki ayrı "aktif firma" hesabı yaparsa, A
    # firmasında açılan kayıt B'ye damgalanabilirdi.
    _firma_cozucu_ayarla(aktif_firma_id)

    @_sa_event.listens_for(_SaSession, 'do_orm_execute')
    def _firma_suzgeci(durum):
        if not durum.is_select or durum.is_column_load or durum.is_relationship_load:
            return
        _f = aktif_firma_id()
        if not _f:
            return
        durum.statement = durum.statement.options(
            # 1 · firma kapsamındaki 28 tablo
            _wlc(_FirmaKapsamli, lambda _s: _s.firma_id == _f,
                 include_aliases=True),
            # 2 · ayarlar: NULL = ortak liste (cins, yüzey, ülke)
            _wlc(Veriler,
                 (Veriler.firma_id == _f) | (Veriler.firma_id.is_(None)),
                 include_aliases=True),
            # 3 · cari: kart ortak, GÖRÜNÜRLÜK üyelikten
            _wlc(Cari, Cari.id.in_(
                _sa_select(_CariFirma.cari_id).where(
                    _CariFirma.firma_id == _f)),
                include_aliases=True),
        )

'''


DEGISIKLIKLER = [
    ('flask_app.py',
     'MF2-a · okuma süzgeci (do_orm_execute kancası)',
     "    # ── YAZMA KORUMASI KANCASI  (CRM-D) ──",
     BLOK + "    # ── YAZMA KORUMASI KANCASI  (CRM-D) ──"),
    ('models.py',
     'MF2-b · yeni cari aktif firmaya baglanir',
     """        n.firma_id = fid""",
     '        n.firma_id = fid\n\n\ndef _cari_firma_uyeligi(oturum, baglam, ornekler):\n    """MF2 — Yeni cari AKTİF FİRMAYA bağlanır.\n\n    Cari kartı ORTAK bir tablo; hangi firmada GÖRÜNECEĞİ `cari_firma`\n    üyeliğinden geliyor. Üyelik satırı yazılmazsa cari hiçbir firmada\n    görünmez: kaydedilir ama kaybolur.\n\n    ÖLÇÜLDÜ: okuma süzgeci (MF2) devreye girince 27 test düştü, hepsi\n    aynı kök nedenden — cari kaydı var, üyeliği yok, listede yok.\n\n    İstek bağlamı yoksa (içe aktarma betiği, test kurulumu) varsayılan\n    firmaya bağlanır; `aktif_firma_id` zaten oraya düşüyor.\n    """\n    yeni = [n for n in oturum.new if isinstance(n, Cari) and n.id]\n    if not yeni:\n        return\n    fid = aktif_firma_id()\n    if fid is None:\n        return\n    # Aynı flush\'ta elle eklenmiş üyelik varsa ikizlemeyelim —\n    # uq_cari_firma kısıtı patlardı.\n    eldeki = {(x.cari_id, x.firma_id) for x in oturum.new\n              if isinstance(x, CariFirma)}\n    for c in yeni:\n        if (c.id, fid) in eldeki:\n            continue\n        oturum.add(CariFirma(cari_id=c.id, firma_id=fid))\n\n\n_event.listen(db.session, \'before_flush\', _cari_firma_uyeligi)'),
]


def main():
    print('=' * 70)
    print(f'  YAMA {IMZA} — ÇOKLU FİRMA 2/4: OKUMA SÜZGECİ')
    print('  MOD:', 'UYGULA' if UYGULA else 'RAPOR (dosyalara dokunulmaz)')
    print('=' * 70)

    # ── Önkoşul: models.py MF1 taşıyor mu ──
    mp = os.path.join(KOK, 'models.py')
    if os.path.exists(mp):
        with open(mp, encoding='utf-8') as f:
            if ONKOSUL not in f.read():
                print(f'\n  ✗ ÖNKOŞUL YOK: models.py "{ONKOSUL}" imzasını taşımıyor.')
                print('    Önce: python3 yama_mf1.py --uygula')
                print('          venv/bin/python goc_mf1.py --uygula')
                return 1

    gruplar = {}
    for dosya, aciklama, eski, yerine in DEGISIKLIKLER:
        gruplar.setdefault(dosya, []).append((aciklama, eski, yerine))

    sonuclar, hata, zaten = {}, False, []
    for dosya, isler in gruplar.items():
        yol = os.path.join(KOK, dosya)
        print(f'\n── {dosya} ' + '─' * max(0, 56 - len(dosya)))
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

        _imza = DOSYA_IMZA[dosya]
        if _imza in icerik:
            print(f'  ⊙ İmza "{_imza}" zaten var — ATLANIR')
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
        print(f'  ⊙ Yama {IMZA} zaten uygulanmış.')
        return 0
    if not UYGULA:
        print('  ✓ Tüm kalıplar eşleşti. Uygulamak için:')
        print('      python3 yama_mf2.py --uygula')
        print('=' * 70)
        return 0

    for yol, icerik in sonuclar.items():
        yedek = yol + '.yedek_mf2'
        shutil.copy2(yol, yedek)
        with open(yol, 'w', encoding='utf-8', newline='') as f:
            f.write(icerik)
        print(f'  ✓ yazıldı: {os.path.relpath(yol, KOK)}')
        print(f'    yedek  : {os.path.relpath(yedek, KOK)}')
    print()
    print('  ✓ YAMA UYGULANDI')
    print()
    print('  Şema değişmedi — göç GEREKMİYOR.')
    print()
    print('    sudo systemctl restart milestone-erp')
    print('    venv/bin/python degismezlik_denetim.py')
    print()
    print('  Ekranda bir şeyin DEĞİŞMEMESİ gerekiyor: tek firma var,')
    print('  her şey ona damgalı. Stok, cari, fatura sayıları eskisi')
    print('  gibi görünmüyorsa haber ver.')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — ÇOKLU FİRMA DENETİMİ  ·  F1–F4
#
#  NEDEN VAR:
#    Çoklu firma (MF1–MF7) tek bir şeye dayanıyor: her sorgunun
#    AKTİF FİRMAYA süzülmesi. Süzgeç `do_orm_execute` kancasında,
#    yazma damgası `before_flush`'ta — ikisi de OTOMATİK. Otomatik
#    olan şey SESSİZ bozulur:
#
#      • Yeni bir model `FirmaKapsamli` mixin'ini almazsa, o tablo
#        HER FİRMADA GÖRÜNÜR. Hata vermez; A firmasının müşterisi
#        B firmasının ekranında çıkar. Bunu fark etmenin tek yolu
#        birinin ekrana bakıp "bu benim kaydım değil" demesi.
#
#      • Yeni bir tablo `sifirla2.py`'ye yazılmazsa, sıfırlama
#        betiği ÇALIŞMAYI REDDEDER. Bu iyi haber — ama reddi
#        öğrendiğin an, sıfırlamak istediğin andır. İki kez yaşandı
#        (R4: kalem_karsilama, R5: firma + cari_firma). Push
#        anında öğrenmek, sıfırlama anında öğrenmekten iyidir.
#
#      • `firma_atla()` süzgeci KAPATIR. Yerinde bir çıkış kapısı
#        (firma listesinin kendisi süzülemez), ama her yeni
#        kullanımı bilinçli bir karar olmalı; sessizce eklenen bir
#        tanesi tüm firmaların verisini tek ekrana döker.
#
#  DÖRT EKSEN:
#    F1  Sıfırlama kapsamı   — her tablo sifirla2.py'de sınıflı mı
#    F2  Firma kapsamı       — her tabloda firma_id var mı
#    F3  Çıkış kapıları      — firma_atla() kullanımları gözden geçirildi mi
#    F4  Ham SQL süzgeci     — text() sorguları firma_id'yi atlıyor mu
#
#  Salt okunur. Veritabanı GEREKMEZ — model tanımı ve kaynak kod
#  üzerinden çalışır, bu yüzden push kapısında (gonder.sh) güvenle
#  koşturulabilir.
#
#  KULLANIM (proje klasöründe):
#      venv/bin/python firma_denetim.py
#
#  ÇIKIŞ KODU: bulgu varsa 1, temizse 0.
# ══════════════════════════════════════════════════════════════════════
import io
import os
import re
import sys
from pathlib import Path

KOK = Path('.').resolve()
if not (KOK / 'flask_app.py').exists():
    print("HATA: flask_app.py bu klasörde yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')

# ── VERİTABANINI KASTEN DEVRE DIŞI BIRAKIYORUZ ──
# Bu araç MODEL TANIMINI ve KAYNAK KODU okur; tek satır veri
# okumaz. `.env`deki gerçek adrese bağlanmasına izin verirsek,
# PostgreSQL kapalıyken ya da sürücü eksikken import patlar ve
# push kapısı (gonder.sh) bu denetimi "çalıştırılamadı" sayıp
# atlar. Oysa atlanmaması gereken tam da bu: kod denetimi,
# veritabanının durumuyla ilgisi olmayan bir şey.
#
# setdefault YETMEZ — ortamda DATABASE_URL zaten dolu olur.
# Üzerine yazıyoruz.
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.insert(0, str(KOK))

try:
    import flask_app as _fa  # noqa: F401
    from models import db as _db
except Exception as _e:
    print(f"HATA: model yüklenemedi: {_e}")
    sys.exit(1)

TABLOLAR = {t.name: {c.name for c in t.c} for t in _db.metadata.sorted_tables}
KAYNAK = io.open(KOK / 'flask_app.py', encoding='utf-8').read()
SIFIRLA = KOK / 'sifirla2.py'

bulgu = 0
print("═" * 70)
print(" MILESTONE ERP — ÇOKLU FİRMA DENETİMİ")
print("═" * 70)
print(f" Model      : {len(TABLOLAR)} tablo")
print()

# ══════════════════════════════════════════════════════════════════════
#  F1 · SIFIRLAMA KAPSAMI
# ══════════════════════════════════════════════════════════════════════
print("─" * 70)
print(" F1 · SIFIRLAMA KAPSAMI   [SESSİZ KALINTI / REDDEDİLEN SIFIRLAMA]")
print("─" * 70)
if not SIFIRLA.exists():
    print("   ⚠ sifirla2.py yok — bu eksen atlandı")
else:
    _s = io.open(SIFIRLA, encoding='utf-8').read()

    def _liste_cikar(ad):
        """`AD = [ ... ]` ya da `AD = { ... }` içindeki tırnaklı adlar."""
        m = re.search(ad + r'\s*=\s*[\[{](.*?)^[\]}]', _s, re.S | re.M)
        if not m:
            return None
        govde = m.group(1)
        # Yorum satırlarını at: tablo adı yorum içinde geçiyorsa
        # sınıflandırılmış SAYILMAZ.
        govde = '\n'.join(s for s in govde.split('\n')
                          if not s.lstrip().startswith('#'))
        return set(re.findall(r"'([a-z_][a-z0-9_]*)'", govde))

    _sil = _liste_cikar('SILINECEK_TABLOLAR')
    _kor = _liste_cikar('KORUNAN')
    if _sil is None or _kor is None:
        print("   ✗ sifirla2.py'de SILINECEK_TABLOLAR / KORUNAN listesi")
        print("     okunamadı — biçim değişmiş olabilir.")
        bulgu += 1
    else:
        _bilinen = _sil | _kor
        _kacan = sorted(t for t in TABLOLAR if t not in _bilinen)
        _hayalet = sorted(t for t in _bilinen if t not in TABLOLAR)
        if _kacan:
            for t in _kacan:
                print(f"   ✗ {t} — sifirla2.py'de ne KORUNAN ne SİLİNECEK")
            print()
            print("   → Sıfırlama bu tabloyu görünce ÇALIŞMAYI REDDEDER.")
            print("     Modeli ekleyen yama sifirla2.py'yi de güncellemeli:")
            print("       işlem verisi    → SILINECEK_TABLOLAR")
            print("       ana veri/tanım  → KORUNAN (gerekçesiyle)")
            bulgu += len(_kacan)
        if _hayalet:
            print(f"   ⚠ modelde olmayan tablo adı: {', '.join(_hayalet)}")
            print("     (zararsız; tablo kaldırılmışsa listeden de düşsün)")
        if not _kacan:
            print(f"   ✓ temiz — {len(TABLOLAR)} tablonun hepsi sınıflandırılmış")

# ══════════════════════════════════════════════════════════════════════
#  F2 · FİRMA KAPSAMI
# ══════════════════════════════════════════════════════════════════════
#
# firma_id'si OLMAYAN tablo her firmada görünür. Bu bazen DOĞRU:
# cari kartı ortak (vergi no, adres tek yerde durur; görünürlüğü
# cari_firma belirler), kur arşivi ortak, kullanıcılar ortak, firma
# tablosunun kendisi de doğal olarak firmasız.
#
# Ama bu listeye bilmeden eklenen bir tablo SESSİZ SIZINTI olur.
# O yüzden liste BURADA, açıkça yazılı: yeni bir tablo firmasız
# kalacaksa buraya gerekçesiyle yazılmalı.
FIRMASIZ_BEKLENEN = {
    'firma': 'firmaların kendisi',
    'cari_firma': 'üyelik tablosu — firma_id taşır ama kapsam dışı sayılmaz',
    'cariler': 'cari kartı ORTAK; görünürlüğü cari_firma belirler (MF2)',
    'cari_kisi': 'cari kartının parçası — kart ortaksa kişileri de ortak',
    'cari_erisim': 'kullanıcı↔cari erişim istisnası, firmadan bağımsız',
    'doviz_kur': 'TCMB kur arşivi — herkes için aynı',
    'kullanicilar': 'kullanıcılar tüm firmalarda aynı kişiler',
    'alembic_version': 'şema sürüm damgası',
}
print()
print("─" * 70)
print(" F2 · FİRMA KAPSAMI   [SESSİZ SIZINTI]")
print("─" * 70)
_firmasiz = sorted(t for t, s in TABLOLAR.items() if 'firma_id' not in s)
_beklenmeyen = [t for t in _firmasiz if t not in FIRMASIZ_BEKLENEN]
if _beklenmeyen:
    for t in _beklenmeyen:
        print(f"   ✗ {t} — firma_id YOK, her firmada görünür")
    print()
    print("   → Tablo işlem verisi tutuyorsa `FirmaKapsamli` mixin'ini")
    print("     almalı (models.py). Gerçekten ortaksa bu dosyadaki")
    print("     FIRMASIZ_BEKLENEN listesine GEREKÇESİYLE yazın —")
    print("     ortaklık bilinçli bir karar olmalı, varsayılan değil.")
    bulgu += len(_beklenmeyen)
else:
    print(f"   ✓ temiz — firmasız {len(_firmasiz)} tablonun hepsi beklenen")
    for t in _firmasiz:
        print(f"       {t:<16s} {FIRMASIZ_BEKLENEN[t]}")

# Damga tarafı: firma_id NOT NULL olmalı. Nullable kalırsa damga
# atlandığında satır HİÇBİR firmaya ait olmaz ve hiçbir ekranda
# görünmez — "kaydettim, kayboldu" şikâyeti.
NULLABLE_BEKLENEN = {
    'audit_log': 'denetim izi: silinen firmanın izi NULL\'a çekilir, iz kalır',
    'veriler': 'NULL = ORTAK liste satırı (cins, yüzey, ülke)',
}
_nullable = []
for t in _db.metadata.sorted_tables:
    if 'firma_id' in TABLOLAR.get(t.name, set()) and t.c['firma_id'].nullable:
        if t.name not in NULLABLE_BEKLENEN:
            _nullable.append(t.name)
if _nullable:
    print()
    for t in sorted(_nullable):
        print(f"   ✗ {t} — firma_id nullable; damga atlanırsa satır")
        print("     hiçbir firmada görünmez (sessiz kayıp)")
    bulgu += len(_nullable)

# ══════════════════════════════════════════════════════════════════════
#  F3 · ÇIKIŞ KAPILARI
# ══════════════════════════════════════════════════════════════════════
#
# `with firma_atla():` süzgeci KAPATIR. Her kullanımı gerekli — ama
# her kullanımı da gözden geçirilmiş olmalı. Sayı artarsa denetim
# uyarır; yeni kullanım bilinçliyse bu sayıyı güncelleyin.
ATLA_BEKLENEN = 12
print()
print("─" * 70)
print(" F3 · ÇIKIŞ KAPILARI (firma_atla)   [GÖZDEN GEÇİRİLMEMİŞ ATLAMA]")
print("─" * 70)
# ── YALNIZCA GERÇEK KULLANIM SAYILIR ──
# İlk sürüm 'firma_atla()' geçen HER satırı sayıyordu ve YORUMLARI
# da sayıyordu: bir çıkış kapısını kaldırıp yerine "burada
# firma_atla() gerekmiyor, çünkü…" diye iki satır yorum yazınca
# sayı 12'den 14'e ÇIKTI. Denetim, kodu değil metni ölçüyordu.
#
# Artık yorumlar atılıyor ve yalnızca `with firma_atla()` biçimi
# sayılıyor — süzgeci fiilen kapatan tek kullanım şekli bu.
def _kodsuz(satir):
    """Satırdaki yorumu atar (dizgi içindeki # için yeterince iyi:
    bu kaynakta firma_atla dizgi içinde geçmiyor)."""
    _k = satir.find('#')
    return satir if _k < 0 else satir[:_k]


_atla = [(i + 1, s.strip()) for i, s in enumerate(KAYNAK.split('\n'))
         if re.search(r'\bwith\s+firma_atla\(\)', _kodsuz(s))]
print(f"   {len(_atla)} kullanım (beklenen {ATLA_BEKLENEN})")
if len(_atla) > ATLA_BEKLENEN:
    print()
    for n, s in _atla:
        print(f"     {n:>6}  {s[:62]}")
    print()
    print("   ✗ Beklenenden fazla. Yeni her atlama süzgeci kapatır:")
    print("     o blok içindeki sorgular TÜM firmaların verisini görür.")
    print("     Bilinçliyse firma_denetim.py'de ATLA_BEKLENEN'i güncelleyin.")
    bulgu += 1
elif len(_atla) < ATLA_BEKLENEN:
    print(f"   ⚠ Beklenenden az — bir çıkış kapısı kalkmış olabilir.")
    print("     Firma listesi/üyelik ekranları hâlâ çalışıyor mu bakın,")
    print("     sonra ATLA_BEKLENEN'i düşürün.")
else:
    print("   ✓ temiz — kullanım sayısı gözden geçirilmiş listeyle aynı")

# ══════════════════════════════════════════════════════════════════════
#  F4 · HAM SQL SÜZGECİ
# ══════════════════════════════════════════════════════════════════════
#
# ORM süzgeci `do_orm_execute` kancasında — YALNIZCA ORM sorgularını
# yakalar. `text(...)` ile yazılan ham SQL kancadan GEÇMEZ; firma
# süzgecini elle koymak gerekir. Koyulmazsa sorgu tüm firmaları
# okur/yazar ve hiçbir hata vermez.
#
# Firma tablosunun KENDİSİNİ okuyan ham SQL beklenen: kimlik üretimi
# ve varsayılan firma araması zaten süzgecin DIŞINDA olmak zorunda
# (ORM sorgusu açmak kancayı yeniden tetiklerdi).
HAM_SQL_BEKLENEN = {
    # desen parçası → NEDEN süzgeçsiz olması DOĞRU
    'FROM firma': 'firma tablosunun kendisi — süzgecin dışı olmalı',
    'FROM cariler': 'cari kartı ortak; görünürlük cari_firma ile',
    'FROM cari_firma': 'üyelik tablosu, firma_id zaten koşulda',
    'FROM cari_hareket WHERE id LIKE': 'kimlik sayacı: benzersizlik '
                                       'TÜM firmalar için aranır',
    'FROM audit_log': 'denetim izi yönetimi',
    'UPDATE proforma SET': 'açılış göçü (SD2) geriye dönük doldurma — '
                           'her firmanın satırına uygulanmalı',
    'WHERE cari_id = :c LIMIT 1': 'artık cari taraması (MF4): cari BAŞKA '
                                  'firmada kayıtlıysa silinmemeli, '
                                  'o yüzden kasten süzgeçsiz',
}
print()
print("─" * 70)
print(" F4 · HAM SQL SÜZGECİ   [SÜZGEÇ ATLAYAN SORGU]")
print("─" * 70)
_firma_kapsamli = {t for t, s in TABLOLAR.items()
                   if 'firma_id' in s and t != 'cari_firma'}
_bloklar = re.findall(
    r"text\(\s*(?:f?r?'''(.*?)'''|f?r?\"\"\"(.*?)\"\"\"|f?r?'([^']*)'"
    r"|f?r?\"([^\"]*)\")", KAYNAK, re.S)
_supheli = []
for _g in _bloklar:
    _q = next((x for x in _g if x), '')
    _tek = ' '.join(_q.split())
    if not re.search(r'\b(SELECT|UPDATE|DELETE)\b', _tek, re.I):
        continue
    if 'firma_id' in _tek:
        continue                                   # süzgeç elle konmuş
    if any(k in _tek for k in HAM_SQL_BEKLENEN):
        continue                                   # gerekçesi yazılı
    # Firma kapsamındaki bir tabloya mı dokunuyor?
    _dokundugu = [t for t in _firma_kapsamli
                  if re.search(r'\b' + re.escape(t) + r'\b', _tek)
                  or '{_t.name}' in _tek or '{_tn}' in _tek]
    if _dokundugu:
        _supheli.append((_tek[:90], sorted(_dokundugu)[:3]))
if _supheli:
    for _q, _t in _supheli:
        print(f"   ✗ {_q}")
        print(f"      → {', '.join(_t)} firma kapsamında, koşulda firma_id yok")
    print()
    print("   → Ham SQL ORM süzgecinden GEÇMEZ. WHERE'e firma_id ekleyin")
    print("     ya da gerekçesini bu dosyadaki HAM_SQL_BEKLENEN'e yazın.")
    bulgu += len(_supheli)
else:
    print("   ✓ temiz — firma kapsamlı tabloya süzgeçsiz dokunan ham SQL yok")
    print(f"     ({len(HAM_SQL_BEKLENEN)} desen bilerek muaf:)")
    for _d, _n in HAM_SQL_BEKLENEN.items():
        print(f"       {_d:<34} {_n}")

# ══════════════════════════════════════════════════════════════════════
#  F5 · KİMLİK SAYAÇLARI
# ══════════════════════════════════════════════════════════════════════
#
# Okunur kimlikler (SIP-STN26-03, HR-STN26-0007) sayaçla üretiliyor:
# üreteç kökü `LIKE` ile tarayıp en büyük numarayı bulur, bir ekler.
# Kök FİRMA KODUNU TAŞIMAZSA iki firma AYNI SAYACI paylaşır.
#
# Ölçüldü (RN3): kök `HR-{kisaltma}{yil}-` idi, firma kodu yoktu.
# STONEHUB'ın hareketi HR-STN26-0001, MILESTONE'un HR-STN26-0002
# oldu. Kimlikler çakışmıyor — tarama tüm firmalarda benzersizlik
# arıyor — ama her firmanın defteri DELİKLİ görünüyor: MILESTONE'un
# ekstresinde 0002 var, 0001 yok. Denetimde "silinmiş kayıt" diye
# okunur. Sessiz, çünkü hiçbir hata vermiyor.
#
# Kural: `id LIKE` ile sayaç tarayan her fonksiyon firma kodunu da
# çözmeli. İki yolla olur — `_firma_belge_kodu()` (oturumdan) ya da
# satırın firma_id'sinden `belge_kodu` okumak.
KOD_BELIRTILERI = ('_firma_belge_kodu', 'belge_kodu FROM firma')
print()
print("─" * 70)
print(" F5 · KİMLİK SAYAÇLARI   [FİRMALARIN PAYLAŞTIĞI SAYAÇ]")
print("─" * 70)
_satirlar = KAYNAK.split('\n')
_tarama = [i for i, s in enumerate(_satirlar)
           if re.search(r'id LIKE|id\.like\(', s)]
_eksik, _tamam = [], []
for _i in _tarama:
    # Kapsayan `def`i geriye doğru arayıp gövdesini çıkar: girintisi
    # def'ten büyük olan satırlar o fonksiyonun gövdesi.
    _d = None
    for _j in range(_i, -1, -1):
        _m = re.match(r'^(\s*)def\s+(\w+)', _satirlar[_j])
        if _m:
            _d = (_j, len(_m.group(1)), _m.group(2))
            break
    if not _d:
        _eksik.append((_i + 1, '<fonksiyon dışı>'))
        continue
    _bas, _gir, _ad = _d
    _govde = []
    for _k in range(_bas + 1, len(_satirlar)):
        _s = _satirlar[_k]
        if _s.strip() and (len(_s) - len(_s.lstrip())) <= _gir:
            break
        _govde.append(_s)
    _metin = '\n'.join(_govde)
    if any(b in _metin for b in KOD_BELIRTILERI):
        _tamam.append((_ad, _i + 1))
    else:
        _eksik.append((_i + 1, _ad))
if _eksik:
    for _n, _ad in _eksik:
        print(f"   ✗ {_ad}  (satır {_n}) — sayaç tarıyor ama firma kodunu")
        print("     çözmüyor: iki firma aynı numara dizisini paylaşır")
    print()
    print("   → Köke firma kodunu ekleyin. Satırın kendi firmasından")
    print("     okumak yeğdir (`SELECT belge_kodu FROM firma WHERE id`):")
    print("     `_firma_belge_kodu()` istek bağlamına bakıyor ve CLI'da,")
    print("     betiklerde, testlerde boş döner.")
    bulgu += len(_eksik)
else:
    print(f"   ✓ temiz — {len(_tamam)} sayaç tarayıcısının hepsi firma")
    print("     kodunu çözüyor")
    for _ad, _n in _tamam:
        print(f"       {_ad:<28} satır {_n}")

print()
print("═" * 70)
if bulgu:
    print(f" ✗ {bulgu} ÇOKLU FİRMA BULGUSU")
else:
    print(" ✓ TEMİZ — çoklu firma kapsamı tutarlı")
print("═" * 70)
sys.exit(1 if bulgu else 0)

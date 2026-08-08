#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — SESSİZ BAŞARI DENETİMİ  ·  S1
#
#  NEDEN VAR:
#    H1'de yaşandı: POST /api/satislar/<id>/fatura uç noktası
#    {'ok': True} dönüyordu ama HİÇBİR ŞEY yapmıyordu. Adı "fatura"ydı,
#    gövdesi ise SatisKaydi'nin alanlarını güncelleyen bir fonksiyondu;
#    ön yüz boş gövde gönderdiği için hiçbir alan değişmiyor, commit
#    boşa çalışıyor, kullanıcı yeşil mesaj görüyordu.
#
#    Bu hata sınıfı DİĞER denetimlerin körnoktası:
#      • form_denetim.py katmanlar arası TUTARLILIĞA bakar — burada
#        katmanlar tutarlıydı, sorun DAVRANIŞTAYDI.
#      • sema_denetim.py şemaya bakar — şema doğruydu.
#      • HTTP 200 döndüğü için günlükte hiçbir iz yok.
#    Sessiz başarıyı yalnızca "bu uç nokta gerçekten yazıyor mu?"
#    sorusunu sorarak yakalayabilirsiniz. Bu betik onu sorar.
#
#  DÖRT DENETİM:
#    S1 · YAZMA YOK       Değiştiren HTTP yöntemi (POST/PUT/PATCH/
#         DELETE) tanımlı ama gövdede hiçbir yazma izi yok
#         (db.session.add/delete/commit, .update(, _safe_commit).
#         → İstek başarılı döner, hiçbir şey olmaz.
#
#    S2 · AD/İŞ UYUŞMAZLIĞI   Yol "fatura/siparis/stok..." diyor ama
#         gövde o modeli hiç oluşturmuyor; başka bir modeli
#         güncelliyor. H1 tam olarak buydu.
#
#    S3 · KOŞULSUZ BAŞARI   Fonksiyon her durumda 'ok': True dönüyor
#         ama yazma işlemi bir `if` içinde — gövde boş gelirse hiçbir
#         şey yazılmadan başarı döner.
#
#    S4 · YETKİ YOK       Değiştiren uç nokta _yetki_var_mi/_yetki_kontrol
#         çağırmıyor. (URL_MODUL_MAP guard'ı çoğunu kapsar; bu liste
#         yalnızca hatırlatmadır, bulgu sayılmaz.)
#
#  BU BETİK HİÇBİR ŞEYİ DEĞİŞTİRMEZ — yalnızca okur.
#  Statik analizdir: her bulgu insan gözüyle doğrulanmalıdır.
#
#  KULLANIM (proje dizininde):
#      venv/bin/python sessiz_denetim.py
#      venv/bin/python sessiz_denetim.py --sadece S1
#      venv/bin/python sessiz_denetim.py --tam      # muaf olanları da göster
#
#  ÇIKIŞ KODU: S1/S2/S3 bulgusu varsa 1, temizse 0.
# ══════════════════════════════════════════════════════════════════════
import re
import sys
from pathlib import Path

APP = Path('flask_app.py')
if not APP.exists():
    print("HATA: flask_app.py bu dizinde yok. Proje klasöründe çalıştırın.")
    sys.exit(1)

TAM = '--tam' in sys.argv
SADECE = None
if '--sadece' in sys.argv:
    i = sys.argv.index('--sadece')
    if i + 1 < len(sys.argv):
        SADECE = sys.argv[i + 1].upper()

KAYNAK = APP.read_text(encoding='utf-8')
SATIRLAR = KAYNAK.split('\n')

DEGISTIREN = ('POST', 'PUT', 'PATCH', 'DELETE')

# Gövdede bunlardan biri varsa "yazıyor" sayılır.
YAZMA_IZLERI = (
    'db.session.add', 'db.session.delete', 'db.session.commit',
    '_safe_commit', '.update(', 'db.session.merge', 'db.session.bulk',
    'db.session.execute',
)

# Yol parçası → beklenen model adı. S2 bu eşlemeyle çalışır.
YOL_MODEL = {
    'fatura': 'Fatura', 'siparis': 'Siparis', 'stok': ('BlokStok', 'PlakaStok', 'EbatliStok'),
    'proforma': 'Proforma', 'cari': 'Cari', 'sevkiyat': 'Sevkiyat',
    'kasa': 'Kasa', 'kesim': 'Kesim', 'cek': 'Cek', 'maliyet': 'Maliyet',
    'rezervasyon': 'Rezervasyon', 'banka': 'Banka',
    'kdv-iade': 'KdvIadeDosya',
}

# Bilinçli olarak yazma yapmayan / farklı desendeki uç noktalar.
# Her giriş GEREKÇE ile yazılır; "sustur ve unut" listesi değildir.
MUAF = {
    # Dışa aktarma ve belge üretimi: POST alır ama dosya döner.
    'api_disa_aktar', 'api_toplu_disa', 'api_rapor_uret',
    # Doğrulama/önizleme uç noktaları: hesaplar, kaydetmez.
    'api_fatura_onizleme', 'api_proforma_onizleme',
    # E-posta gönderimi: dış servise gider, kayıt yazmaz.
    'api_proforma_eposta', 'api_eposta_test',
    # Oturum: session'a yazar, veritabanına değil.
    'giris', 'cikis',
}


def uc_noktalari():
    """(satir_no, yollar, yontemler, fonksiyon_adi, govde) listesi."""
    sonuc = []
    i = 0
    while i < len(SATIRLAR):
        s = SATIRLAR[i]
        if '@app.route(' not in s:
            i += 1
            continue
        # Üst üste birden fazla @app.route olabilir
        yollar, yontemler, j = [], set(), i
        while j < len(SATIRLAR) and '@app.route(' in SATIRLAR[j]:
            m = re.search(r"@app\.route\(\s*'([^']+)'", SATIRLAR[j])
            if m:
                yollar.append(m.group(1))
            ym = re.search(r"methods\s*=\s*\[([^\]]*)\]", SATIRLAR[j])
            if ym:
                yontemler |= {x.strip().strip("'\"").upper()
                              for x in ym.group(1).split(',') if x.strip()}
            else:
                yontemler.add('GET')
            j += 1
        # dekoratörden sonraki def
        while j < len(SATIRLAR) and not SATIRLAR[j].strip().startswith('def '):
            if SATIRLAR[j].strip().startswith('@'):
                j += 1
                continue
            break
        if j >= len(SATIRLAR) or not SATIRLAR[j].strip().startswith('def '):
            i += 1
            continue
        fn = re.search(r'def (\w+)', SATIRLAR[j]).group(1)
        girinti = len(SATIRLAR[j]) - len(SATIRLAR[j].lstrip())
        # gövde: girintisi daha büyük veya boş satırlar
        k = j + 1
        govde = []
        while k < len(SATIRLAR):
            t = SATIRLAR[k]
            if t.strip() and (len(t) - len(t.lstrip())) <= girinti:
                break
            govde.append(t)
            k += 1
        sonuc.append((j + 1, yollar, yontemler, fn, '\n'.join(govde)))
        i = k
    return sonuc


UCLAR = uc_noktalari()
DEG_UCLAR = [u for u in UCLAR if u[2] & set(DEGISTIREN)]


def yaziyor_mu(govde):
    return any(iz in govde for iz in YAZMA_IZLERI)


# Veritabanına yazmayan ama GERÇEK iş yapan uç noktalar: yedek dosyası
# üretir, SMTP'ye bağlanır, TCMB'den kur çeker, dosya siler...
# Bunlar "sessiz başarı" değildir; ayrı raporlanır.
DIS_IS_IZLERI = (
    'yedek_modul', 'subprocess', 'smtplib', 'requests.', 'os.remove',
    'os.unlink', 'shutil.', 'open(', 'send_file', 'guncel_kurlari_cek',
    'kur_arsivi', 'pg_dump', 'psql',
)


def dis_is_yapiyor_mu(govde):
    return any(iz in govde for iz in DIS_IS_IZLERI)


# ══ S1 · Yazma yok ════════════════════════════════════════════════════
def denetim_s1():
    """Döner: (bulgular, dis_is_yapanlar)"""
    b, dis = [], []
    for satir, yollar, yont, fn, govde in DEG_UCLAR:
        if fn in MUAF or yaziyor_mu(govde):
            continue
        kayit = (satir, yollar[0], sorted(yont & set(DEGISTIREN)), fn)
        (dis if dis_is_yapiyor_mu(govde) else b).append(kayit)
    return b, dis


# ══ S2 · Ad / iş uyuşmazlığı ══════════════════════════════════════════
def denetim_s2():
    b = []
    for satir, yollar, yont, fn, govde in DEG_UCLAR:
        if fn in MUAF or not yaziyor_mu(govde):
            continue
        yol = yollar[0]
        # YALNIZCA ALT KAYNAK yolları denetlenir — H1'in deseni buydu:
        #   /api/satislar/<id>/fatura   → ana kaynak "satislar",
        #                                  alt parça "fatura" bir Fatura
        #                                  oluşturmayı VAAT EDER.
        # /api/cari/<id> gibi doğrudan yollarda PUT/DELETE'in o modeli
        # güncellemesi zaten DOĞRU davranıştır; onlar denetlenmez.
        parcalar = [p for p in yol.strip('/').split('/')
                    if p and not p.startswith('<')]
        if len(parcalar) < 3:
            continue
        son = parcalar[-1]
        if son not in YOL_MODEL or son == parcalar[-2]:
            continue
        beklenen = YOL_MODEL[son]
        adaylar = beklenen if isinstance(beklenen, tuple) else (beklenen,)
        # Bu uç nokta o modeli oluşturuyor mu? (ModelAdi( çağrısı)
        olusturuyor = any(f'{ad}(' in govde and 'query' not in govde.split(f'{ad}(')[1][:12]
                          for ad in adaylar)
        if olusturuyor:
            continue
        # Oluşturmuyorsa: en azından o modeli okuyor/güncelliyor mu?
        dokunuyor = any(f'{ad}.query' in govde for ad in adaylar)
        b.append((satir, yol, fn, '/'.join(adaylar),
                  'yalnizca okuyor/guncelliyor' if dokunuyor else 'HIC DOKUNMUYOR'))
    return b


# ══ S3 · Koşulsuz başarı ══════════════════════════════════════════════
def denetim_s3():
    """Yazma `if` içinde, başarı koşulsuz VE hiç girdi doğrulaması yok.

    Koşullu güncelleme tek başına sorun değildir — PATCH tarzı uç
    noktalarda normaldir ("alan gönderildiyse yaz"). Sorun, gövde boş
    geldiğinde uç noktanın bunu FARK ETMEDEN 'ok' dönmesidir. Girdi
    doğrulaması yapan (400 dönebilen) uç noktalar bu tuzağa düşmez,
    o yüzden elenirler. H1 tam olarak doğrulamasız olandı.
    """
    b = []
    for satir, yollar, yont, fn, govde in DEG_UCLAR:
        if fn in MUAF or not yaziyor_mu(govde):
            continue
        # Girdi doğrulaması var mı? (400 dönüşü = boş/hatalı gövdeyi eler)
        if '400' in govde:
            continue
        satirlar = govde.split('\n')
        # add/delete çağrılarının hepsi bir if bloğunda mı?
        yazma_satirlari = [(k, s) for k, s in enumerate(satirlar)
                           if any(iz in s for iz in
                                  ('db.session.add', 'db.session.delete', '.update('))]
        if not yazma_satirlari:
            continue
        # commit dışındaki yazmaların tümü girintili (koşul içi) mi?
        taban = min((len(s) - len(s.lstrip())) for _, s in yazma_satirlari)
        commit_satiri = next((k for k, s in enumerate(satirlar)
                              if 'commit' in s or '_safe_commit' in s), None)
        if commit_satiri is None:
            continue
        commit_girinti = len(satirlar[commit_satiri]) - len(satirlar[commit_satiri].lstrip())
        # Yazma daha derin girintide (koşul içinde), commit dışarıda:
        # gövde boş gelirse hiçbir şey yazılmadan başarı döner.
        if taban > commit_girinti:
            b.append((satir, yollar[0], fn))
    return b


# ══ S4 · Yetki kontrolü yok (hatırlatma) ══════════════════════════════
def denetim_s4():
    b = []
    for satir, yollar, yont, fn, govde in DEG_UCLAR:
        if fn in MUAF:
            continue
        if '_yetki_var_mi' not in govde and '_yetki_kontrol' not in govde:
            b.append((satir, yollar[0], fn))
    return b


print("═" * 74)
print(" MILESTONE ERP — SESSİZ BAŞARI DENETİMİ")
print("═" * 74)
print(f" {len(UCLAR)} uç nokta · {len(DEG_UCLAR)} tanesi veri değiştiriyor "
      f"(POST/PUT/PATCH/DELETE)")
print()

bulgu = 0

if SADECE in (None, 'S1'):
    b, dis = denetim_s1()
    print("─" * 74)
    print(" S1 · DEĞİŞTİREN UÇ NOKTA HİÇ YAZMIYOR   [SESSİZ BAŞARI]")
    print("─" * 74)
    if b:
        for satir, yol, yont, fn in b:
            print(f"   ✗ {'/'.join(yont):<12s} {yol}")
            print(f"     {fn}() — flask_app.py:{satir}")
            print(f"     Gövdede db.session.add/delete/commit yok. İstek başarılı")
            print(f"     döner ama hiçbir kayıt oluşmaz/değişmez.")
        print(f"\n   {len(b)} bulgu. Her birini elle doğrulayın.")
        bulgu += len(b)
    else:
        print("   ✓ temiz — veritabanına yazmayan sessiz uç nokta yok")
    if dis:
        print()
        print(f"   ℹ {len(dis)} uç nokta veritabanına yazmıyor ama DIŞ İŞ yapıyor")
        print("     (yedek dosyası, SMTP, TCMB kuru, dosya silme). Bulgu sayılmaz:")
        for satir, yol, yont, fn in dis:
            print(f"     · {yol}")
    print()

if SADECE in (None, 'S2'):
    b = denetim_s2()
    print("─" * 74)
    print(" S2 · YOL BİR ŞEY VAAT EDİYOR, GÖVDE BAŞKASINI YAPIYOR")
    print("─" * 74)
    if b:
        for satir, yol, fn, model, durum in b:
            print(f"   ! {yol}")
            print(f"     {fn}() — flask_app.py:{satir}")
            print(f"     '{model}' modelini {durum}. Yol adı yanıltıcı olabilir.")
        print(f"\n   {len(b)} uyarı. H1 tam olarak bu desendi — inceleyin.")
        bulgu += len(b)
    else:
        print("   ✓ temiz — yol adları yaptıkları işle uyumlu")
    print()

if SADECE in (None, 'S3'):
    b = denetim_s3()
    print("─" * 74)
    print(" S3 · YAZMA KOŞULA BAĞLI, BAŞARI KOŞULSUZ")
    print("─" * 74)
    if b:
        for satir, yol, fn in b:
            print(f"   ! {yol}")
            print(f"     {fn}() — flask_app.py:{satir}")
            print(f"     Yazma bir if içinde; boş gövde gelirse hiçbir şey")
            print(f"     yazılmadan 'ok' dönebilir. Doğrulama ekleyin.")
        print(f"\n   {len(b)} uyarı.")
        bulgu += len(b)
    else:
        print("   ✓ temiz")
    print()

if SADECE in (None, 'S4'):
    b = denetim_s4()
    print("─" * 74)
    print(" S4 · YETKİ KONTROLÜ GÖVDEDE YOK   [hatırlatma, bulgu değil]")
    print("─" * 74)
    if b:
        print(f"   {len(b)} uç nokta gövdesinde _yetki_var_mi/_yetki_kontrol yok.")
        print("   Çoğu URL_MODUL_MAP guard'ı ile korunuyor olabilir; yeni")
        print("   eklenen yollar o listeye girmediyse KORUMASIZDIR.")
        if TAM:
            for satir, yol, fn in b:
                print(f"     · {yol}  ({fn}, satır {satir})")
        else:
            for satir, yol, fn in b[:8]:
                print(f"     · {yol}")
            if len(b) > 8:
                print(f"     … +{len(b) - 8} (tümü için --tam)")
    else:
        print("   ✓ hepsi gövdede yetki kontrol ediyor")
    print()

print("═" * 74)
if bulgu:
    print(f" {bulgu} BULGU/UYARI — her biri elle doğrulanmalı")
else:
    print(" ✓ SESSİZ BAŞARI BULGUSU YOK")
print("═" * 74)
sys.exit(1 if bulgu else 0)

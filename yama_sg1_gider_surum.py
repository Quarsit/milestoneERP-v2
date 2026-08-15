#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — SABİT GİDER SÜRÜMLEME  ·  SG1
#
#  ── SORUN 1: TUTAR DEĞİŞİKLİĞİ ──
#    Sabit giderin tutarını düzenlemek GEÇMİŞİ de değiştiriyor.
#    Ölçüldü: Ocak'ta açılmış 10.000'lik gider 14.000 yapılınca
#    Ocak–Temmuz arası projeksiyon da 14.000 gösteriyor.
#
#    Sebep: SabitGider bir ŞABLON. Projeksiyon her istekte şablondan
#    yayılıyor, hiçbir dönem kaydı saklanmıyor. Tutarı değiştirmek
#    geçmişi de değiştirmek demek. Ayrıca "kira Ocak'ta artacak"
#    gibi İLERİ TARİHLİ bir değişiklik hiç ifade edilemiyor.
#
#  ── SORUN 2: YANLIŞ VAAT ──
#    api_sabit_gider_sil şunu yazıyor:
#        "Uretilmis NakitPlan kalemleri KALIR."
#    Ama öyle kalemler HİÇ üretilmiyor — tek NakitPlan oluşturma
#    noktası kaynak='elle'. O filtre her zaman 0 kayıt siliyor.
#    Docstring düzeltildi.
#
#  ── ÇÖZÜM: SÜRÜM ZİNCİRİ ──
#    Tutar değişince kayıt DÜZENLENMEZ; eskisine bitiş konur, yeni
#    tutarla yeni kayıt açılır:
#
#        HİZMET BEDELİ  10.000  01.01.2026 → 31.07.2026
#        HİZMET BEDELİ  14.000  01.08.2026 → (süresiz)
#
#    Ölçüldü: geçmiş aylar 10.000, sonrası 14.000. Doğru.
#
#  ── NEDEN grup_id ──
#    Sürümleri ada göre gruplamak kırılgan: bir sürümün adı
#    düzeltilince zincir kopar. grup_id sabit kalır; ilk kayıtta
#    kendi id'sine eşitlenir, sonraki sürümler onu devralır.
#
#  ── NEDEN aktif DEĞİL, bitis ──
#    Eski sürümü aktif=False yapmak GEÇMİŞİ SİLER: projeksiyon
#    SabitGider.query.filter_by(aktif=True) ile çalışıyor, pasif
#    kaydı hiç okumuyor. Ölçüldü: pasif yapılınca Mart ayı 10.000
#    yerine 0 oluyor. bitis ise kaydı okur, sadece o tarihte
#    durdurur. Bu yüzden sürümleme ve sonlandırma bitis kullanır.
#
#  ── ŞEMA DEĞİŞİKLİĞİ VAR ──
#      sabit_gider.grup_id  (String(20), nullable, indeksli)
#    Göç dosyası da yazılır. Mevcut kayıtlar grup_id = id ile
#    doldurulur, yani her biri kendi zincirinin köküdür.
#
#  KULLANIM (proje klasöründe):
#      python yama_sg1_gider_surum.py            # rapor
#      python yama_sg1_gider_surum.py --uygula
#      venv/bin/python goc.py uygula             # ŞART
# ══════════════════════════════════════════════════════════════════════
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
APP = Path('flask_app.py')
MOD = Path('models.py')
GOC = Path('migrations/versions')

for _d in (APP, MOD):
    if not _d.exists():
        print(f"HATA: {_d} bu klasörde yok. Proje klasöründe çalıştırın.")
        sys.exit(1)
if not GOC.exists():
    print("HATA: migrations/versions yok — göç altyapısı kurulu değil.")
    sys.exit(1)


def dogrula(kaynak, ad):
    try:
        compile(kaynak, ad, 'exec')
        return None
    except SyntaxError as exc:
        return f"satır {exc.lineno}: {exc.msg}"


# ══ A) Model: grup_id ══════════════════════════════════════════════
A_ESKI = """    aciklama    = db.Column(db.Text)
    olusturma   = db.Column(db.DateTime, default=datetime.now)"""

A_YENI = """    aciklama    = db.Column(db.Text)
    # Surum zinciri: tutar degisince kayit DUZENLENMEZ, eskisine bitis
    # konup yeni tutarla yeni kayit acilir. Ayni giderin tum surumleri
    # bu alani paylasir. Ilk kayitta kendi id'sine esitlenir.
    # Ada gore gruplamak kirilgan olurdu: bir surumun adi duzeltilince
    # zincir kopardi.
    grup_id     = db.Column(db.String(20), index=True)
    olusturma   = db.Column(db.DateTime, default=datetime.now)"""

# ══ B) Serileştirici: grup_id + surum bilgisi ══════════════════════
B_ESKI = """    def _sabit_gider_dict(g):
        return {
            'id': g.id, 'ad': g.ad, 'kategori': g.kategori,
            'tutar': g.tutar, 'doviz': g.doviz,
            'periyot': g.periyot, 'ayin_gunu': g.ayin_gunu,
            'haftanin_gunu': g.haftanin_gunu, 'ay': g.ay,
            'baslangic': g.baslangic.isoformat() if g.baslangic else None,
            'bitis': g.bitis.isoformat() if g.bitis else None,
            'aktif': g.aktif, 'aciklama': g.aciklama,
        }"""

B_YENI = """    def _sabit_gider_grup(g):
        \"\"\"Giderin ait oldugu surum zincirinin kimligi.

        Eski kayitlarda grup_id bos olabilir; o durumda kayit kendi
        zincirinin koku sayilir.
        \"\"\"
        return g.grup_id or g.id

    def _sg_tarih(d):
        \"\"\"Kullaniciya gosterilecek tarih. (api_export icindeki
        _tarih yereldir, burada kullanilamaz.)\"\"\"
        try:
            return d.strftime('%d.%m.%Y')
        except Exception:
            return str(d) if d else ''

    def _sg_para(v, doviz='TRY'):
        try:
            return f"{float(v or 0):,.2f} {doviz}"
        except Exception:
            return f"{v} {doviz}"

    def _sabit_gider_dict(g):
        _bugun = date.today()
        # Sonlanmis mi: bitis gecmiste kaldiysa bu surum artik
        # projeksiyona girmiyor demektir.
        _sonlandi = bool(g.bitis and g.bitis < _bugun)
        return {
            'id': g.id, 'ad': g.ad, 'kategori': g.kategori,
            'tutar': g.tutar, 'doviz': g.doviz,
            'periyot': g.periyot, 'ayin_gunu': g.ayin_gunu,
            'haftanin_gunu': g.haftanin_gunu, 'ay': g.ay,
            'baslangic': g.baslangic.isoformat() if g.baslangic else None,
            'bitis': g.bitis.isoformat() if g.bitis else None,
            'aktif': g.aktif, 'aciklama': g.aciklama,
            'grup_id': _sabit_gider_grup(g),
            'sonlandi': _sonlandi,
            'yururlukte': bool(g.aktif and not _sonlandi),
        }"""

# ══ C) Yaşam döngüsü uç noktaları ══════════════════════════════════
C_ESKI = """    @app.route('/api/sabit_gider/<gider_id>', methods=['DELETE'])"""

C_YENI = '''    @app.route('/api/sabit_gider/<gider_id>/tutar_guncelle', methods=['POST'])
    def api_sabit_gider_tutar_guncelle(gider_id):
        """Tutari YENI SURUM acarak gunceller — gecmisi bozmadan.

        Kaydi duzenlemek gecmisi de degistirirdi (sablon her istekte
        yeniden yayiliyor). Bunun yerine:
            eski kayit → bitis = gecerlilik - 1 gun
            yeni kayit → baslangic = gecerlilik, yeni tutar

        Sinir hesabini SISTEM yapar. Elle yapilirsa bir gun kayarsa o
        ay ya hic gorunmez ya iki kez sayilir.
        """
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('kasa', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403

        g = db.session.get(SabitGider, gider_id)
        if not g:
            return jsonify({'ok': False, 'mesaj': 'Gider bulunamadı'}), 404

        d = request.json or {}
        try:
            yeni_tutar = float(d.get('tutar'))
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'mesaj': 'Tutar sayısal olmalı'}), 400
        if yeni_tutar <= 0:
            return jsonify({'ok': False, 'mesaj': 'Tutar sıfırdan büyük olmalı'}), 400

        gecerlilik = _parse_date(d.get('gecerlilik'))
        if not gecerlilik:
            return jsonify({'ok': False,
                            'mesaj': 'Geçerlilik tarihi zorunlu (YYYY-AA-GG)'}), 400
        if g.baslangic and gecerlilik <= g.baslangic:
            return jsonify({'ok': False,
                            'mesaj': 'Geçerlilik tarihi, giderin başlangıcından '
                                     'sonra olmalı'}), 400
        if g.bitis and gecerlilik > g.bitis:
            return jsonify({'ok': False,
                            'mesaj': 'Bu gider zaten '
                                     f'{_sg_tarih(g.bitis)} tarihinde sonlanmış'}), 400

        eski_tutar = float(g.tutar or 0)
        grup = _sabit_gider_grup(g)

        # Eski surumu bir gun oncesinde kapat — bosluk da bindirme de olmaz.
        g.grup_id = grup
        g.bitis = gecerlilik - timedelta(days=1)

        yeni = SabitGider(
            id=_yeni_id('SG'), ad=g.ad, kategori=g.kategori,
            tutar=q3(yeni_tutar), doviz=g.doviz, periyot=g.periyot,
            ayin_gunu=g.ayin_gunu, haftanin_gunu=g.haftanin_gunu, ay=g.ay,
            baslangic=gecerlilik, bitis=None, aktif=True,
            aciklama=(d.get('aciklama') or g.aciklama), grup_id=grup)
        db.session.add(yeni)
        _log_audit('GUNCELLE', 'sabit_gider', gider_id,
                   eski={'tutar': eski_tutar},
                   yeni={'tutar': yeni_tutar, 'gecerlilik': gecerlilik.isoformat(),
                         'yeni_id': yeni.id})
        ok, hata = _safe_commit(f'Sabit gider tutar guncelleme: {gider_id}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({
            'ok': True, 'yeni_id': yeni.id, 'grup_id': grup,
            'mesaj': f'{g.ad}: {_sg_para(eski_tutar, g.doviz)} → '
                     f'{_sg_para(yeni_tutar, g.doviz)} '
                     f'({_sg_tarih(gecerlilik)} itibarıyla). Önceki tutar '
                     f'{_sg_tarih(g.bitis)} tarihine kadar korundu.'})

    @app.route('/api/sabit_gider/<gider_id>/sonlandir', methods=['POST'])
    def api_sabit_gider_sonlandir(gider_id):
        """Gideri bir tarihte SONLANDIRIR — silmez, pasiflestirmez.

        Personel ayrildi, sozlesme bitti gibi durumlar icin. Gecmis
        aylar oldugu gibi kalir; yalnizca o tarihten sonrasi
        projeksiyona girmez.

        aktif=False YAPILMAZ: projeksiyon pasif kaydi hic okumuyor,
        o yuzden pasiflestirmek gecmisi de silerdi.
        """
        if _auth_required():
            return jsonify({'error': 'Unauthorized'}), 401
        if not _yetki_var_mi('kasa', 'yazma'):
            return jsonify({'ok': False, 'mesaj': 'Yetkiniz yok'}), 403

        g = db.session.get(SabitGider, gider_id)
        if not g:
            return jsonify({'ok': False, 'mesaj': 'Gider bulunamadı'}), 404

        d = request.json or {}
        bitis = _parse_date(d.get('tarih'))
        if not bitis:
            return jsonify({'ok': False,
                            'mesaj': 'Bitiş tarihi zorunlu (YYYY-AA-GG)'}), 400
        if g.baslangic and bitis < g.baslangic:
            return jsonify({'ok': False,
                            'mesaj': 'Bitiş tarihi, başlangıçtan önce olamaz'}), 400

        g.bitis = bitis
        g.grup_id = _sabit_gider_grup(g)
        _log_audit('GUNCELLE', 'sabit_gider', gider_id,
                   yeni={'bitis': bitis.isoformat()})
        ok, hata = _safe_commit(f'Sabit gider sonlandirma: {gider_id}')
        if not ok:
            return jsonify({'ok': False, 'mesaj': f'Hata: {hata}'}), 500
        return jsonify({'ok': True,
                        'mesaj': f'{g.ad} {_sg_tarih(bitis)} tarihinde sonlandırıldı. '
                                 f'Geçmiş dönemler korundu.'})

    @app.route('/api/sabit_gider/<gider_id>', methods=['DELETE'])'''

# ══ D) Yanlış vaat eden docstring ══════════════════════════════════
D_ESKI = '''        """Sablonu siler. Uretilmis NakitPlan kalemleri KALIR.

        Gecmis aylarin projeksiyonu bozulmasin diye: gider artik
        yok ama gecen ay odendiyse o kayit durmali.
        """'''

D_YENI = '''        """Sablonu TAMAMEN siler — gecmisi de dahil.

        DIKKAT: SabitGider bir SABLON'dur; donem kaydi saklanmaz,
        projeksiyon her istekte sablondan yayilir. Silinince gecmis
        aylar da projeksiyondan kaybolur.

        Bu yuzden "artik bu gideri odemiyorum" durumunda SILME
        kullanilmamali — /sonlandir kullanilmali (bitis tarihi
        koyar, gecmisi korur). Silme yalnizca "bu kaydi yanlislikla
        girdim" icindir.

        (Onceki surumde bu docstring "uretilmis NakitPlan kalemleri
        KALIR" diyordu; oyle kalemler HIC uretilmiyor — tek
        NakitPlan olusturma noktasi kaynak='elle'. Asagidaki filtre
        her zaman 0 kayit siler, geriye donuk uyumluluk icin durdu.)
        """'''

# ══ E) Yeni kayıtta grup_id ════════════════════════════════════════
E_ESKI = """            aktif=bool(d.get('aktif', True)))
        db.session.add(g)"""

E_YENI = """            aktif=bool(d.get('aktif', True)))
        # Ilk kayit kendi surum zincirinin kokudur. Sonraki surumler
        # (tutar_guncelle) bu degeri devralir.
        g.grup_id = g.id
        db.session.add(g)"""

BLOKLAR = [
    (MOD, "model: grup_id sütunu",        A_ESKI, A_YENI, 'grup_id     = db.Column'),
    (APP, "grup yardımcısı",              B_ESKI, B_YENI, 'def _sabit_gider_grup('),
    (APP, "tutar_guncelle + sonlandir",   C_ESKI, C_YENI, 'def api_sabit_gider_tutar_guncelle('),
    (APP, "silme docstring düzeltmesi",   D_ESKI, D_YENI, 'Sablonu TAMAMEN siler'),
    (APP, "yeni kayıtta grup_id",         E_ESKI, E_YENI, 'g.grup_id = g.id'),
]

print("═" * 70)
print(" SG1 · SABİT GİDER SÜRÜMLEME")
print("═" * 70)
print()

icerik, crlf = {}, {}
for yol in (APP, MOD):
    _t = yol.read_bytes().decode('utf-8')
    icerik[yol] = _t
    crlf[yol] = '\r\n' in _t


def uyarla(t, yol):
    return t.replace('\n', '\r\n') if crlf[yol] else t


plan, atlanan, sorunlu = [], [], []
for yol, aciklama, eski, yeni, imza in BLOKLAR:
    metin = icerik[yol]
    if uyarla(imza, yol) in metin or imza in metin:
        atlanan.append(aciklama)
        continue
    e = uyarla(eski, yol)
    adet = metin.count(e)
    if adet != 1:
        sorunlu.append((aciklama, adet))
        continue
    icerik[yol] = metin.replace(e, uyarla(yeni, yol), 1)
    plan.append(aciklama)

for a in atlanan:
    print(f"  ↷ atlandı (zaten var)  {a}")
for a in plan:
    print(f"  ✓ uygulanacak          {a}")
for a, n in sorunlu:
    print(f"  ✗ KALIP BULUNAMADI     {a}  (eşleşme: {n})")

print()
if sorunlu:
    print(f" ✗ {len(sorunlu)} blok yerleştirilemedi — HİÇBİR DOSYAYA DOKUNULMADI.")
    sys.exit(1)
if not plan:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

for yol in (APP, MOD):
    hata = dogrula(icerik[yol], yol.name)
    if hata:
        print(f" ✗ {yol.name} SÖZDİZİMİ HATASI → {hata}")
        print(" HİÇBİR DOSYAYA DOKUNULMADI.")
        sys.exit(1)
print(" ✓ sözdizimi doğrulandı (compile)")

# ── Göç dosyası ────────────────────────────────────────────────────
mevcut = sorted(GOC.glob('*.py'))
zincir = {}
for f in mevcut:
    m = f.read_text(encoding='utf-8', errors='replace')
    import re as _re
    _r = _re.search(r"^revision = '([^']+)'", m, _re.M)
    _d = _re.search(r"^down_revision = '([^']+)'", m, _re.M)
    if _r:
        zincir[_r.group(1)] = _d.group(1) if _d else None
uclar = [r for r in zincir if r not in set(v for v in zincir.values() if v)]
if len(uclar) != 1:
    print(f" ✗ Göç zincirinde {len(uclar)} uç bulundu: {uclar}")
    print("   Tek uç bekleniyordu. HİÇBİR DOSYAYA DOKUNULMADI.")
    sys.exit(1)
bas = uclar[0]
YENI_REV = 'sg1grupid0001'
GOC_DOSYA = GOC / f'{YENI_REV}_sabit_gider_grup_id.py'
GOC_ICERIK = f'''"""sabit gider surum zinciri (grup_id)

Revision ID: {YENI_REV}
Revises: {bas}
Create Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '{YENI_REV}'
down_revision = '{bas}'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('sabit_gider', schema=None) as batch_op:
        batch_op.add_column(sa.Column('grup_id', sa.String(length=20), nullable=True))
        batch_op.create_index(batch_op.f('ix_sabit_gider_grup_id'),
                              ['grup_id'], unique=False)

    # Mevcut kayitlar: her biri kendi zincirinin kokudur.
    op.execute("UPDATE sabit_gider SET grup_id = id WHERE grup_id IS NULL")


def downgrade():
    with op.batch_alter_table('sabit_gider', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_sabit_gider_grup_id'))
        batch_op.drop_column('grup_id')
'''

print(f" ✓ göç zinciri tek uçlu ({bas})")
print(f" ✓ yeni revizyon: {YENI_REV}")

if not UYGULA:
    print()
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_sg1_gider_surum.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
for yol in (APP, MOD):
    yedek = yol.with_name(f'{yol.name}.yedek-{damga}')
    shutil.copy2(yol, yedek)
    yol.write_bytes(icerik[yol].encode('utf-8'))
    print(f" ✓ {yol.name}")
GOC_DOSYA.write_text(GOC_ICERIK, encoding='utf-8')
print(f" ✓ {GOC_DOSYA}")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print(" ⚠ ŞEMA DEĞİŞTİ — göçü uygulamayı UNUTMAYIN:")
print("     venv/bin/python goc.py uygula")
print("═" * 70)

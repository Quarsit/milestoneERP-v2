#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — SİPARİŞ MİKTARI ile STOK METRAJI AYRIŞMASI  ·  OS1
#
#  NE İŞE YARAR:
#    Sipariş kalemine yazılan miktar ile o kaleme bağlanan plakaların
#    stoktaki metraj toplamı neden tutmuyor — onu söyler.
#
#  SİSTEMDE TEK ÖLÇÜ KAYNAĞI VAR:
#    Plakanın metrajı ayrıca ölçülüp girilmiyor; girilen ebattan
#    hesaplanıyor (flask_app `m2 = (boy * yuk) / 10000`, hem elle
#    girişte hem toplu içe aktarmada). Yani "kesim payı" ya da
#    "nominal ölçü" diye bir ikinci sayı YOK. Buna rağmen iki toplam
#    ayrışıyorsa sebebi şu ikisinden biridir:
#
#    ── A · YUVARLAMA SIRASI ──────────────────────────────────────
#      Plaka metrajı stoğa 2 haneyle yazılıyor (models.Olcu →
#      NUMERIC(18,2)). Sipariş kalemi ise önce çarpıp sonra
#      yuvarlıyor. 320×207 plakada:
#
#          tam alan                = 6,624 m²
#          stoğa yazılan           = 6,62   (plaka başına 0,004 kayıp)
#          kalem  : 6,624 × 32     = 211,97
#          stoklar: 6,62  × 32     = 211,84
#          fark                    =   0,13
#
#      Veri tamamen doğru; fark yalnızca yuvarlamanın hangi adımda
#      yapıldığından geliyor ve PLAKA SAYISIYLA büyüyor.
#
#    ── B · KARIŞIK EBATLI KALEM ──────────────────────────────────
#      Bir sipariş kalemi tek bir boy×yükseklik taşır. Kaleme farklı
#      ebatta plakalar bağlanmışsa (6,59 + 6,62 gibi) kalemin miktarı
#      TEK ebattan hesaplanır, plakalar ise kendi ebatlarını toplar.
#      Bu fark yuvarlamadan BÜYÜK olabilir ve gerçek bir tutarsızlıktır.
#
#  AYRICA BAKAR:
#    Kalemin `adet` alanı ile bağlı plaka sayısı tutuyor mu? Çeki
#    listesi parça sayısını `adet × kasa_ici_adet` ile basıyor
#    (packing_list_print.html:265); tutmuyorsa belgede yanlış parça
#    sayısı çıkar — gümrük parça sayar.
#
#  BU BETİK HİÇBİR ŞEYİ DEĞİŞTİRMEZ — yalnızca okur ve raporlar.
#
#  KULLANIM (proje dizininde):
#      venv/bin/python tani_olcu_sapmasi.py
#      venv/bin/python tani_olcu_sapmasi.py --tam
#      venv/bin/python tani_olcu_sapmasi.py --siparis SIP-D54D4B
# ══════════════════════════════════════════════════════════════════════
import os
import sys

from dotenv import load_dotenv

load_dotenv()

if not os.environ.get('DATABASE_URL'):
    print('HATA: DATABASE_URL bulunamadı (.env dosyası okunamadı).')
    sys.exit(1)

sys.path.insert(0, os.getcwd())
os.environ.setdefault('MILESTONE_ACILIS_ATLA', '1')

TAM = '--tam' in sys.argv
SIPARIS = None
for i, a in enumerate(sys.argv):
    if a == '--siparis' and i + 1 < len(sys.argv):
        SIPARIS = sys.argv[i + 1]

import flask_app as fa                                        # noqa: E402
from models import (db, SiparisKalem, KalemKarsilama,         # noqa: E402
                    PlakaStok, EbatliStok)

CIZGI = '─' * 74


def q2(v):
    return round(float(v or 0) + 1e-9, 2)


def main():
    with fa.app.app_context():
        sor = SiparisKalem.query
        if SIPARIS:
            sor = sor.filter(SiparisKalem.siparis_id == SIPARIS)
        kalemler = sor.order_by(SiparisKalem.siparis_id,
                                SiparisKalem.sira).all()
        if not kalemler:
            print('Kalem bulunamadı.')
            return 0

        # Karşılama satırları — kalem kimliğine göre
        krs = {}
        for k in KalemKarsilama.query.all():
            if k.siparis_kalem_id:
                krs.setdefault(k.siparis_kalem_id, []).append(k)

        satirlar = []
        for k in kalemler:
            if (k.urun_tip or '').upper() == 'BLOK':
                continue                      # ton/m³ — bu tanının dışı
            rows = krs.get(k.id) or []
            if not rows:
                continue
            hedef = q2(k.miktar)
            gercek = q2(sum(float(r.miktar or 0) for r in rows))

            # Bağlı plakaların GERÇEK ebatları: kaç farklı ebat var,
            # yuvarlanmamış toplamları ne?
            ebatlar, ham_toplam, bulunan = set(), 0.0, 0
            for r in rows:
                if (r.kaynak_tip or '') != 'STOK' or not r.kaynak_ref:
                    continue
                st = (db.session.get(PlakaStok, r.kaynak_ref)
                      or db.session.get(EbatliStok, r.kaynak_ref))
                if not st:
                    continue
                b = float(getattr(st, 'boy', 0) or 0)
                y = float(getattr(st, 'yukseklik', 0) or 0)
                if not (b and y):
                    continue
                kat = int(getattr(st, 'kasa_ici_adet', 1) or 1)
                ebatlar.add((b, y))
                ham_toplam += (b * y / 10000.0) * kat
                bulunan += 1

            satirlar.append({
                'sip': k.siparis_id, 'sira': k.sira or 0,
                'cins': (k.cins or '')[:22],
                'hedef': hedef, 'gercek': gercek, 'n': len(rows),
                'adet': int(k.adet or 1) * int(k.kasa_ici_adet or 1),
                'ebat_sayisi': len(ebatlar), 'olculen': bulunan,
                'ham': q2(ham_toplam),
                'birim_fiyat': float(k.birim_fiyat or 0),
                'doviz': k.doviz or 'USD',
            })

        # ══ OS1 · AYRIŞMA VAR MI ══
        print('\n' + '═' * 74)
        print(' OS1 · SİPARİŞ MİKTARI ile BAĞLI PLAKALARIN METRAJ TOPLAMI')
        print('═' * 74)
        sapan = [s for s in satirlar if abs(s['hedef'] - s['gercek']) >= 0.01]
        if not sapan:
            print(f'   ✓ temiz — {len(satirlar)} kalemin hepsinde iki toplam tutuyor')
        else:
            print(f'   {len(sapan)} / {len(satirlar)} kalemde fark var\n')
            print('   {:<14}{:>3} {:<22}{:>9}{:>9}{:>8}{:>4}'.format(
                'siparis', 'sr', 'cins', 'kalem', 'plakalar', 'fark', 'n'))
            print('   ' + CIZGI)
            for s in (sapan if TAM else sapan[:25]):
                print('   {:<14}{:>3} {:<22}{:>9.2f}{:>9.2f}{:>8.2f}{:>4}'.format(
                    s['sip'][:14], s['sira'], s['cins'],
                    s['hedef'], s['gercek'], s['hedef'] - s['gercek'], s['n']))
            if not TAM and len(sapan) > 25:
                print(f'   … +{len(sapan) - 25} (tümü için --tam)')
            print()
            para = {}
            for s in sapan:
                para[s['doviz']] = (para.get(s['doviz'], 0)
                                    + (s['hedef'] - s['gercek']) * s['birim_fiyat'])
            for dv, t in sorted(para.items()):
                yon = 'FAZLA faturalanır' if t > 0 else 'EKSİK faturalanır'
                print(f'   Tutar karşılığı: {abs(t):,.2f} {dv} {yon}')

        # ══ OS2 · FARKIN SEBEBİ ══
        print('\n' + '═' * 74)
        print(' OS2 · FARK NEREDEN GELİYOR')
        print('═' * 74)
        if not sapan:
            print('   (OS1 temiz — bakılacak bir şey yok)')
        else:
            yuvarlama, karisik, baska = [], [], []
            for s in sapan:
                if s['olculen'] == 0:
                    baska.append(s)
                elif s['ebat_sayisi'] > 1:
                    karisik.append(s)
                elif abs(s['hedef'] - s['ham']) < 0.02:
                    # kalem miktarı, plakaların YUVARLANMAMIŞ toplamına eşit
                    yuvarlama.append(s)
                else:
                    baska.append(s)

            print(f'   A · yuvarlama sırası : {len(yuvarlama):>4} kalem'
                  '   (veri doğru, aksiyon yok)')
            print(f'   B · karışık ebat     : {len(karisik):>4} kalem'
                  '   (kalem tek ebat taşıyor)')
            print(f'   ? · açıklanamayan    : {len(baska):>4} kalem'
                  '   (elle bakılmalı)')

            if karisik:
                print('\n   ── B · KARIŞIK EBATLI KALEMLER ' + '─' * 32)
                print('   {:<14}{:>3} {:<22}{:>6}{:>9}{:>9}'.format(
                    'siparis', 'sr', 'cins', 'ebat', 'kalem', 'plakalar'))
                print('   ' + CIZGI)
                for s in (karisik if TAM else karisik[:15]):
                    print('   {:<14}{:>3} {:<22}{:>6}{:>9.2f}{:>9.2f}'.format(
                        s['sip'][:14], s['sira'], s['cins'],
                        s['ebat_sayisi'], s['hedef'], s['gercek']))
                if not TAM and len(karisik) > 15:
                    print(f'   … +{len(karisik) - 15} (tümü için --tam)')

            if baska:
                print('\n   ── ? · AÇIKLANAMAYAN ' + '─' * 42)
                print('   {:<14}{:>3} {:<22}{:>9}{:>9}{:>9}'.format(
                    'siparis', 'sr', 'cins', 'kalem', 'plakalar', 'ham'))
                print('   ' + CIZGI)
                for s in (baska if TAM else baska[:15]):
                    print('   {:<14}{:>3} {:<22}{:>9.2f}{:>9.2f}{:>9.2f}'.format(
                        s['sip'][:14], s['sira'], s['cins'],
                        s['hedef'], s['gercek'], s['ham']))
                if not TAM and len(baska) > 15:
                    print(f'   … +{len(baska) - 15} (tümü için --tam)')

        # ══ OS3 · ÇEKİ LİSTESİ PARÇA SAYISI ══
        print('\n' + '═' * 74)
        print(' OS3 · KALEMİN `adet` ALANI ile BAĞLI PLAKA SAYISI')
        print('═' * 74)
        print('   Çeki listesi parça sayısını `adet × kasa_ici_adet` ile basar.')
        uyusmaz = [s for s in satirlar if s['adet'] != s['n']]
        if not uyusmaz:
            print(f'   ✓ {len(satirlar)} kalemde adet, bağlı plaka sayısıyla tutuyor')
        else:
            print(f'   {len(uyusmaz)} / {len(satirlar)} kalemde TUTMUYOR —'
                  ' belgede yanlış parça sayısı çıkar.\n')
            print('   {:<14}{:>3} {:<22}{:>7}{:>8}'.format(
                'siparis', 'sr', 'cins', 'adet', 'plaka'))
            print('   ' + CIZGI)
            for s in (uyusmaz if TAM else uyusmaz[:20]):
                print('   {:<14}{:>3} {:<22}{:>7}{:>8}'.format(
                    s['sip'][:14], s['sira'], s['cins'], s['adet'], s['n']))
            if not TAM and len(uyusmaz) > 20:
                print(f'   … +{len(uyusmaz) - 20} (tümü için --tam)')

        print('\n' + '═' * 74)
        print(' Bu betik hiçbir şeyi değiştirmedi.')
        print('═' * 74 + '\n')
        return 0


if __name__ == '__main__':
    sys.exit(main())

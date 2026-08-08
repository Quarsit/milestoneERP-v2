#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════
#  Milestone ERP — KUR EKRANI: HESAPLANAN KURU GÖSTER  ·  K11
#
#  SORUN:
#    Kur kipinde büyük punto ile 47,6799 yazıyordu — ama sistem
#    hesaplarda 47,5229 kullanıyor. Yani ekrandaki sayı, faturanızın
#    TL karşılığını belirleyen sayı DEĞİLDİ.
#
#      47,6799  efektif = BanknoteSelling  (nakit döviz satış)  ← gösteriliyordu
#      47,5229  alis    = ForexBuying      (döviz alış)         ← KULLANILIYOR
#      47,6085  satis   = ForexSelling     (döviz satış)
#
#    _kur_getir():  val = k.alis or k.efektif or k.satis
#                         ^^^^^^ öncelik ALIŞ'ta
#
#    100.000 $'lık bir işlemde aradaki fark 15.700 TL. Kullanıcı
#    ekranda gördüğü kurla hesap yapıp tutmadığını görürdü.
#
#  ── NEDEN "DÖVİZ ALIŞ" DOĞRU (mevzuat) ──
#    VUK ve GİB özelgelerine göre, sözleşmede özel bir kur
#    belirlenmemişse dövizli işlemlerin TL değerlemesinde
#    TCMB DÖVİZ ALIŞ KURU esas alınır. KDV Kanunu m.26 da bedelin
#    dövizle hesaplanması halinde vergiyi doğuran olay anındaki cari
#    kurun kullanılacağını düzenler.
#
#    Yani hesap tabanı DOĞRU; yanlış olan EKRANDI. Bu yama hesaba
#    dokunmaz, yalnızca gösterimi dürüst hale getirir.
#
#  ── DEĞİŞENLER ──
#    • Büyük punto artık ALIŞ kurunu gösterir
#    • Altında "hesaplarda kullanılan kur" etiketi
#    • Döviz satış ve efektif satış bilgi olarak listelenir
#    • Kipin altına mevzuat notu
#
#  KULLANIM (proje klasöründe):
#      python yama_k11_kur_gosterim.py            # rapor
#      python yama_k11_kur_gosterim.py --uygula   # uygula
#
#  SONRA:  python js_denetim.py
#  Şema değişikliği YOK. Hesaplama değişikliği YOK.
# ══════════════════════════════════════════════════════════════════════
import shutil
import sys
from datetime import datetime
from pathlib import Path

UYGULA = '--uygula' in sys.argv
BASE = Path('templates/base.html')

if not BASE.exists():
    print("HATA: templates/base.html bulunamadı. Proje klasöründe çalıştırın.")
    sys.exit(1)

A_ESKI = """    const satir = (ad, d) => {
      const yok = !d || !d.efektif;
      /* Sorulan tarih ile dönen tarih farklıysa SÖYLE: hafta sonu ya
         da resmî tatil sorulmuş, kur bir önceki iş gününden geliyor.
         Sessizce farklı bir günün kurunu göstermek yanıltıcı olur. */
      const farkli = d && d.tarih && d.tarih !== tarih;
      return `<div class="kalem-satir">
        <span class="rozet ${yok ? 'rz-gri' : 'rz-yesil'}">${ad}</span>
        <div>
          <div><strong style="font-size:1.05rem">${yok ? '—' :
            Number(d.efektif).toLocaleString('tr-TR', {minimumFractionDigits: 4})}</strong>
            <span style="color:var(--soluk)"> ₺</span></div>
          ${!yok && d.alis && d.satis ? `<div style="color:var(--soluk);font-size:.76rem">
            Alış ${Number(d.alis).toLocaleString('tr-TR', {minimumFractionDigits: 4})} ·
            Satış ${Number(d.satis).toLocaleString('tr-TR', {minimumFractionDigits: 4})}</div>` : ''}
          ${farkli ? `<div style="color:var(--kehribar);font-size:.76rem">
            ⚠ ${tarih} için kur yok (hafta sonu / tatil) — ${d.tarih} kuru gösteriliyor</div>` : ''}
          ${yok ? `<div style="color:var(--kirmizi);font-size:.76rem">
            Bu tarih için arşivde kayıt yok</div>` : ''}
        </div>
      </div>`;
    };
    kutu.innerHTML = satir('USD', usd) + satir('EUR', eur);"""

A_YENI = """    const bicim = v => Number(v).toLocaleString('tr-TR', {minimumFractionDigits: 4});
    const satir = (ad, d) => {
      /* K11 — BÜYÜK PUNTO = HESAPLARDA KULLANILAN KUR.
         Eskiden `efektif` (BanknoteSelling) gösteriliyordu ama
         _kur_getir() `alis`i kullanıyor:
             val = k.alis or k.efektif or k.satis
         Ekrandaki sayı, faturanın TL karşılığını belirleyen sayı
         değildi. 100.000 $'da 15.700 TL fark eden bir yanılgı.

         Döviz alış esas alınması MEVZUAT GEREĞİ: sözleşmede özel
         kur yoksa VUK/GİB uygulamasında TCMB döviz alış kuru
         kullanılır (KDV K. m.26 — vergiyi doğuran olay anındaki
         cari kur). Yani hesap doğruydu, ekran yanlıştı. */
      const hesapKuru = d ? (d.alis || d.efektif || d.satis) : null;
      const yok = !hesapKuru;
      /* Sorulan tarih ile dönen tarih farklıysa SÖYLE: hafta sonu ya
         da resmî tatil sorulmuş, kur bir önceki iş gününden geliyor.
         Sessizce farklı bir günün kurunu göstermek yanıltıcı olur. */
      const farkli = d && d.tarih && d.tarih !== tarih;
      return `<div class="kalem-satir">
        <span class="rozet ${yok ? 'rz-gri' : 'rz-yesil'}">${ad}</span>
        <div>
          <div><strong style="font-size:1.15rem">${yok ? '—' : bicim(hesapKuru)}</strong>
            <span style="color:var(--soluk)"> ₺</span>
            ${yok ? '' : `<span style="color:var(--verde);font-size:.72rem;
              font-weight:600;margin-left:6px">DÖVİZ ALIŞ</span>`}</div>
          ${yok ? '' : `<div style="color:var(--soluk);font-size:.73rem;margin-top:1px">
            hesaplarda kullanılan kur</div>`}
          ${!yok && (d.satis || d.efektif) ? `<div style="color:var(--soluk);
            font-size:.75rem;margin-top:4px;padding-top:4px;border-top:1px solid var(--cizgi)">
            ${d.satis ? 'Döviz satış ' + bicim(d.satis) : ''}${d.satis && d.efektif ? ' · ' : ''}${
              d.efektif && d.efektif !== d.satis ? 'Efektif satış ' + bicim(d.efektif) : ''}</div>` : ''}
          ${farkli ? `<div style="color:var(--kehribar);font-size:.76rem;margin-top:3px">
            ⚠ ${tarih} için kur yok (hafta sonu / tatil) — ${d.tarih} kuru gösteriliyor</div>` : ''}
          ${yok ? `<div style="color:var(--kirmizi);font-size:.76rem">
            Bu tarih için arşivde kayıt yok</div>` : ''}
        </div>
      </div>`;
    };
    kutu.innerHTML = satir('USD', usd) + satir('EUR', eur) +
      `<div style="margin-top:8px;font-size:.72rem;color:var(--soluk);line-height:1.5">
         Dövizli işlemlerin TL karşılığı <strong>TCMB döviz alış kuru</strong> ile
         hesaplanır. Sözleşmede özel bir kur belirlenmişse fatura üzerinde
         ayrıca belirtilmelidir.
       </div>`;"""

print("═" * 70)
print(" K11 · KUR EKRANI: HESAPLANAN KURU GÖSTER")
print("═" * 70)
print()

ham = BASE.read_bytes().decode('utf-8')
crlf = '\r\n' in ham


def uyarla(t):
    return t.replace('\n', '\r\n') if crlf else t


if uyarla('K11 — BÜYÜK PUNTO') in ham or 'K11 — BÜYÜK PUNTO' in ham:
    print(" ✓ Zaten uygulanmış — yapılacak iş yok.")
    sys.exit(0)

e = uyarla(A_ESKI)
adet = ham.count(e)
if adet != 1:
    print(f" ✗ Kalıp {adet} kez bulundu (1 bekleniyordu). DOSYAYA DOKUNULMADI.")
    sys.exit(1)

print("  ✓ kalıp bulundu")
print()
print("   ÖNCE : 47,6799 (efektif satış)  ← hesapta kullanılmıyor")
print("   SONRA: 47,5229 (döviz alış)     ← hesapta KULLANILAN")
print("          + 'hesaplarda kullanılan kur' etiketi")
print("          + döviz satış ve efektif satış bilgi olarak")
print("          + mevzuat notu")
print()

yeni = ham.replace(e, uyarla(A_YENI), 1)

if not UYGULA:
    print(" Rapor modu. Uygulamak için:")
    print("   python yama_k11_kur_gosterim.py --uygula")
    sys.exit(0)

damga = datetime.now().strftime('%Y%m%d_%H%M%S')
yedek = BASE.with_name(f'base.html.yedek-{damga}')
shutil.copy2(BASE, yedek)
BASE.write_bytes(yeni.encode('utf-8'))
print(f" ✓ templates/base.html  (yedek: {yedek.name})")
print()
print("═" * 70)
print(" ✓ TAMAMLANDI")
print()
print(" HESAPLAMA DEĞİŞMEDİ — yalnızca gösterim düzeltildi.")
print(" SONRA:  python js_denetim.py")
print("═" * 70)

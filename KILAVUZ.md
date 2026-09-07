# Milestone ERP — Kullanım Kılavuzu

Bu kılavuz sistemi günlük kullanacak kişiler için yazıldı. Her bölümde
önce **ne işe yaradığı**, sonra **nasıl yapıldığı**, sonra da gerçek bir
**örnek** var.

---

## İçindekiler

1. [Giriş ve ekranı tanıma](#1-giriş-ve-ekranı-tanıma)
2. [Yetkiler ve kimin neyi göreceği](#2-yetkiler-ve-kimin-neyi-göreceği)
3. [Cari hesaplar](#3-cari-hesaplar)
4. [Banka ve kasa](#4-banka-ve-kasa)
5. [Stok](#5-stok)
6. [Maliyetler](#6-maliyetler)
7. [Satış hattı: teklif → sipariş → fatura](#7-satış-hattı)
8. [Tahsilat ve ödeme](#8-tahsilat-ve-ödeme)
9. [Çek ve senet](#9-çek-ve-senet)
10. [Belgeler: ekstre, proforma, fatura](#10-belgeler)
11. [Nakit akışı ve sabit giderler](#11-nakit-akışı-ve-sabit-giderler)
12. [Sık karşılaşılan durumlar](#12-sık-karşılaşılan-durumlar)

---

## 1. Giriş ve ekranı tanıma

Tarayıcıdan sistem adresine gidip kullanıcı adı ve şifrenizle girersiniz.

### Kenar menü

Sol tarafta beş alan var. Hangilerini gördüğünüz yetkinize bağlıdır.

| Alan | İçindekiler |
|---|---|
| **Bugün** | Günün iş kuyruğu — dikkat bekleyen işler |
| **Satış** | Satış Hattı, Proforma, Sevkiyat, Satışlar, Müşteriler, Takipler |
| **Depo** | Stok, Rezervasyonlar, Kesim, Maliyetler |
| **Finans** | Banka ve Kasa, Cari Hesaplar, Faturalar, KDV İade, Çek/Senet, Kasa Defteri, Nakit Akışı, Sabit Giderler |
| **Analiz** | Raporlar, Karlılık |

### Üst çubuk

**Arama kutusu** — blok no, kasa no, müşteri, fatura no veya sipariş
numarası yazın. `Ctrl+K` ile de açılır.

**Kur göstergesi** — o günün TCMB dolar ve euro kuru. Sistem kurları her
gün otomatik çeker.

**Hızlı Satış** — depodan doğrudan satış için kısayol.

### Bugün sayfası

Bu bir **bilgilendirme** ekranıdır; buradan işlem yapılmaz. Gösterdikleri:

- Bu ay ciro ve kâr
- Açık siparişler
- Stok değeri
- Vadesi geçen alacaklar
- Vadesi yaklaşan çekler
- Takılı siparişler, yolda olan sevkiyatlar

Bir kalemle ilgilenmek için ilgili modüle gidersiniz. Örneğin vadesi
geçen bir alacak için **Cari Hesaplar**'a gidip o cariyi açarsınız.

---

## 2. Yetkiler ve kimin neyi göreceği

Sistemde **iki ayrı** kavram var. Karıştırılması en sık sorun çıkaran
konu budur.

### Yetki — ne yapabilirsiniz

Her modül için üç seviye:

- **Gizli** — modül menüde görünmez
- **Okuma** — görür, değiştiremez
- **Yazma** — görür ve değiştirir

Bazı modüllerde alt yetkiler de var. Örneğin `fatura` altında:
fatura oluşturma, tahsilat girişi, fatura iptali ayrı ayrı verilebilir.

### Kapsam — hangi carilerde yapabilirsiniz

- **Atanan cariler** — yalnızca size atanmış olanlar ve "ortak" işaretli
  olanlar
- **Tüm cariler** — bütün cariler

**Kapsam yetkiyi genişletmez.** Kapsamı "tüm cariler" olan bir muhasebeci
bütün carileri görür, ama yalnızca kendisine verilen yetkilerin işlemlerini
yapabilir.

### Örnek

Şirkette üç kişi var:

**Kübra (satış)** — kapsam "atanan". ABC firması ona atanmış, görür ve
işlem yapar. XYZ firması Hulisi'ye atanmışsa Kübra XYZ'yi göremez.

**Hulisi (satış)** — kapsam "atanan". ABC'ye atanmadığı için ABC'yi
göremez.

**Mahmut (muhasebe)** — kapsam "tüm cariler", yetkileri fatura ve kasa
yazma. Hem ABC'yi hem XYZ'yi görür, ikisine de fatura ve tahsilat girer.
Ama müşteri kartını düzenleyemez, ayarlara giremez.

### Sorumlu ve görünürlük atama

Bu ayarları yalnızca yönetici yapar. Cari kartında:

- **Satış Sorumlusu** — cariyi kime atadığınız
- **Görünürlük** — "Ortak" (herkes görür) veya "Kapalı" (yalnızca sorumlu
  ve yönetici)

Kapalı bir cariyi istisnaen başka birine açmak için cari detayındaki
**Erişim** bölümünü kullanın.

---

## 3. Cari hesaplar

Cari, alışveriş yaptığınız her firma demektir: müşteri, tedarikçi,
üretici, acente. Bir firma birden çok rolde olabilir.

### Yeni cari açma

**Cari Hesaplar → Yeni Cari**

Zorunlu tek alan **Ünvan**. Diğerleri belgeleri ve hesaplamaları etkiler:

| Alan | Neyi etkiler |
|---|---|
| **Rol** | Müşteri/Tedarikçi/Üretici/Acente — birden çok seçilebilir |
| **Ülke** | Belge dilini belirler. Türkiye → Türkçe, diğerleri → İngilizce |
| **Vergi No / Dairesi** | Faturada basılır |
| **Para Birimi** | Bakiyenin gösterileceği döviz |
| **Risk Limiti** | Müşterinin borçlanabileceği üst sınır |
| **Ödeme Vadesi** | Fatura vadesi bu güne göre hesaplanır |
| **Üretici Kısaltması** | Stok kodlarında kullanılır (örn. AKD) |

> **Dikkat:** Ülkeyi boş bırakırsanız belgeler **İngilizce** hazırlanır.
> Yurt içi müşteride ülkeyi mutlaka "Türkiye" seçin.

### Cari kartı

Listeden bir cariye tıklayınca sağda çekmece açılır:

- **Bakiye** — her döviz kendi birimiyle
- **Vadesi geçen** — gecikmiş alacak
- **Risk limiti** — kullanılabilir tutar ve doluluk çubuğu
- **Tahsil edilmemiş çek** — varsa ayrı gösterilir
- **Son hareketler**

### Risk limiti nasıl okunur

```
Risk Limiti  10.000 $
kullanılabilir 2.000 $ · 8.000 $ kullanımda (5.000 $ çek)
```

Bu müşteriden 5.000 dolarlık çek aldınız, borcu düştü ama **çek tahsil
edilene kadar risk devam ediyor**. Bu yüzden çek de limite dahil edilir.

Siz o cariye borçluysanız şunu görürsünüz:

```
limit dolu değil · bu caride biz borçluyuz
```

### Açılış bakiyesi girme

Eski sistemden devir yaparken:

**Cari kartı → Hareket ekle → İşlem tipi:**

- Müşteri size borçluysa → **Açılış Bakiyesi (Borç)**
- Siz ona borçluysanız → **Açılış Bakiyesi (Alacak)**

> **Tarih önemli:** Eski sistemin kesim tarihini girin (örneğin
> 31.12.2025), bugünü değil. Yoksa nakit akışı projeksiyonu kayar.

---

## 4. Banka ve kasa

**Kasa** para hareketlerinin geçtiği yerdir. Nakit kasası olabilir,
bir banka hesabına bağlı olabilir.

**Banka** ise hesap bilgisidir: banka adı, şube, hesap no, IBAN. Tek
başına para taşımaz — para hareketi için ona bağlı bir kasa gerekir.

### Banka ekleme

**Ayarlar → Bankalar → Yeni**

Kaydettiğinizde sistem sorar: *"Bu banka için bir kasa oluşturulsun mu?"*
Genellikle **evet** demelisiniz — kasası olmayan banka hesabı ödeme
ekranında seçilemez.

### Kasa açılış bakiyesi

Kasa listesinde kasaya tıklayın, **Hareket ekle → Giriş** yapın ve
mevcut tutarı girin. Sistem bakiyeyi hareketlerden hesaplar; doğrudan
bakiye yazılmaz.

### Virman

İki kasa arasında para aktarımı. **Kasa → Virman**. Kaynak ve hedef
kasayı seçip tutarı girersiniz. Farklı dövizlerde kur sorulur.

---

## 5. Stok

Üç tip stok var:

| Tip | Ölçü | Kullanım |
|---|---|---|
| **Blok** | m³ / ton | Ocaktan çıkan ham blok |
| **Plaka** | m² | Blok kesilerek elde edilen levha |
| **Ebatlı** | m² | Belirli ölçüye kesilmiş ürün |

### Tek tek stok girişi

**Stok → Yeni Stok**. Tipi seçip ölçüleri girin. Sistem metrajı otomatik
hesaplar.

Alış bilgilerini girerseniz (tedarikçi, fiyat, fatura no) sistem cari
borcunu da oluşturur.

> **Üretici adı** cari ünvanıyla **birebir aynı** olmalı. Sistem stoğu
> cariye ada göre bağlar; farklı yazılırsa bağ kurulmaz ve mahsup
> çalışmaz.

### Toplu içe aktarma (Excel)

**Stok → Toplu Ekle**

1. **Ürün tipini** seçin (Blok / Plaka / Ebatlı)
2. Excel dosyanızı yükleyin
3. Sütunları eşleştirin
4. Önizlemeyi kontrol edin
5. Aktarın

Önizlemede uyarı çıkarsa okuyun. Örneğin:

> ⚠ 7 satırın tamamı aynı blok numarasına sahip ("K5452"). Blok numarası
> benzersizdir — ilki dışındakiler reddedilir. Bunlar aynı bloktan çıkan
> **plakalar** olabilir; ürün tipini kontrol edin.

Bu uyarı genellikle **tip seçiminin yanlış** olduğunu gösterir.

### Süzgeçler ve kutular

Üretici, cins ve özellik süzgeçleri **birbirine bağlıdır**: bir üretici
seçince cins listesi yalnızca o üreticinin cinslerini gösterir.

Üstteki beş kutu (Toplam Stok Değeri, Serbest Stok, Rezerve Stok, Stok
Adedi, Stok Miktarı) **süzgece göre güncellenir**. Süzgeç yoksa tüm
stoğu gösterir.

### Stok durumları

- **Serbest** — satışa hazır
- **Rezerve** — bir siparişe ayrılmış
- **Satıldı** — satılmış
- **Sevkedildi / Teslim Edildi**

---

## 6. Maliyetler

Bir ürünün maliyeti iki parçadan oluşur:

**Alış bedeli** — tedarikçiye ödediğiniz
**Ek maliyetler** — nakliye, fason, komisyon, gümrük

Toplamı **giydirilmiş maliyet**tir ve kârlılık hesabı buna göre yapılır.

### Maliyet ekleme

**Maliyetler → Yeni Maliyet**

1. Maliyet tipini seçin (Nakliye, Fason, Komisyon…)
2. Bağlantı tipini seçin (Stok, Sipariş, Sevkiyat)
3. Süzgeçlerle ürünü bulun — üretici, cins, blok no ile daraltın
4. Bir veya **birden çok** ürün seçin
5. Tutarı ve tedarikçiyi girin

### Birden çok ürüne maliyet dağıtma

Bir nakliye faturası 30 plakayı kapsıyorsa hepsini seçin. Sistem tutarı
**eşit böler** ve kaydetmeden önce gösterir:

```
30 kayıt seçili · tutar eşit bölünür: 100,00 USD / kayıt
```

"Tümünü seç" düğmesi süzgeçten geçen tüm kayıtları seçer.

### Ürün maliyetini görme

Maliyet listesinde bir kaleme tıklayın. Çekmecenin altında o ürünün
toplam maliyeti çıkar:

```
Alış bedeli           672,00 $
Ek maliyetler         120,00 $
─────────────────────────────
TOPLAM                792,00 $
Giydirilmiş birim     132,00 $ / m²
```

---

## 7. Satış hattı

Akış: **Proforma → Sipariş → Sevkiyat → Fatura**

### Proforma (teklif)

**Proforma → Yeni**

Müşteriyi seçin, ürünleri ekleyin, fiyat ve vade girin. Durumlar:

- **Taslak** — hazırlanıyor
- **Onaylandı** — iç onay verildi
- **Gönderildi** — müşteriye iletildi
- **Kaybedildi** — gerekçesiyle kapatıldı

Onay sırasında müşterinin risk limiti kontrol edilir. Limit aşılıyorsa
uyarı çıkar ve nedeni ayrıştırılır:

> Açık risk **40.000 USD** = 0 USD açık borç + **40.000 USD tahsil
> edilmemiş çek**

Onaylamak isterseniz bilerek onaylarsınız; sistem engellemez ama
kayıt altına alır.

### Sipariş

Kabul edilen proforma siparişe dönüştürülür. Sipariş kalemlerine stok
**rezerve** edilir; o stoklar artık başkasına satılamaz.

### Sevkiyat

Hazır siparişler için sevkiyat oluşturulur. Konteyner bilgisi, çeki
listesi ve ticari fatura buradan üretilir.

### Fatura

**Faturalar → Yeni** ya da sipariş üzerinden. Fatura kesildiğinde:

- Cari borcu oluşur
- Stok "satıldı" olur
- Satış kaydı düşer

---

## 8. Tahsilat ve ödeme

### Cari kartından

**Cari kartı → Tahsilat / Ödeme**

Form açılır, cari hazır gelir. İşlem tipini seçin:

| Tip | Anlamı |
|---|---|
| **Tahsilat** | Müşteriden para aldınız |
| **Ödeme** | Tedarikçiye para verdiniz |
| **Avans Tahsilatı / Ödemesi** | Peşin alınan/verilen |

Kasa seçimi zorunludur — para bir kasaya girer ya da bir kasadan çıkar.

### Faturaya bağlama

Açık faturalar listelenir; tahsilatı belirli bir faturaya bağlayabilir
ya da genel bakiyeye işleyebilirsiniz.

### Farklı dövizde ödeme

Müşteri 10.000 dolarlık borcunu TL ile ödeyebilir. Tutarı TL girin,
sistem **ödeme günü kuruyla** çevirip borçtan düşer.

> Borcun oluştuğu günün kuru değil, **ödemenin yapıldığı günün** kuru
> kullanılır. Aradaki fark kur farkı olarak ayrıca işlenebilir.

### Örnek

ANKA'ya 40.000 USD fatura kestiniz. Müşteri 500.000 TL ödedi, o günkü
kur 48,50.

1. Cari kartı → Tahsilat
2. Tutar: 500.000, Döviz: TRY
3. Kasa: TL Kasası
4. Fatura: FTR-785448

Sistem 500.000 ÷ 48,50 = **10.309,28 USD** olarak borçtan düşer.
Kalan borç 29.690,72 USD.

---

## 9. Çek ve senet

### Cari kartından çek girme

**Cari kartı → Hareket ekle → İşlem tipi → Alınan Çek** (veya Verilen
Çek)

Çek formu açılır ve cari **sabit** gelir — değiştirmeniz gerekmez.
Başka bir cari için girmek isterseniz "Başka cari seç" düğmesi var.

Çek no, banka, tutar ve **vade tarihini** girin. Kaydedince cari kartına
dönersiniz.

### Çek durumları

| Durum | Anlamı | Riske dahil mi |
|---|---|---|
| **Portföyde** | Elimizde, vadesi gelmemiş | Evet |
| **Tahsilde** | Bankaya tahsile verildi | Evet |
| **Teminatta** | Teminat olarak verildi | Evet |
| **Tahsil Edildi** | Para geldi | Hayır |
| **Ciro Edildi** | Başkasına devredildi | Hayır |
| **Karşılıksız** | Ödenmedi, borç geri yüklendi | Hayır |

### Neden risk devam ediyor

Çek aldığınızda müşterinin cari borcu düşer. Ama para henüz gelmedi.
Bu yüzden sistem tahsil edilmemiş çekleri **risk limitine dahil eder**
ve cari kartında ayrı gösterir.

Çek tahsil edilince risk kendiliğinden düşer.

---

## 10. Belgeler

Sistem şu belgeleri üretir:

- **Cari Ekstre** — hesap dökümü
- **Proforma** — teklif
- **Ticari Fatura** — ihracat faturası
- **Çeki Listesi** — packing list

### Belge dili

Belgenin dili **carinin ülkesinden** belirlenir:

- Ülke **Türkiye** → Türkçe
- Başka bir ülke veya **boş** → İngilizce

Yurt içi müşteride ülkeyi boş bırakırsanız İngilizce belge çıkar.

### Ekstre alma

**Cari kartı → Ekstre yazdır**

Seçenekler:

**Döviz** — hangi para biriminde
**Kur modu** — işlem günü kuru veya güncel kur
**İşlem türü** — belirli türleri süzebilirsiniz (örneğin yalnızca
tahsilatlar)

Süzgeç uygularsanız bakiye sütunu da yalnızca gösterilen hareketlerin
kümülatifini gösterir.

### Ekstredeki kısaltmalar

Türkçe belgede:
- **(B)** — Müşteri borçlu, biz alacaklıyız
- **(A)** — Müşteri alacaklı, biz borçluyuz

İngilizce belgede:
- **(DR)** — Debit, customer owes us
- **(CR)** — Credit, we owe customer

Her dövizli harekette kullanılan kur da satırın altında yazar:
`1 USD = 48,2326 ₺ · TCMB`

---

## 11. Nakit akışı ve sabit giderler

### Sabit giderler

**Sabit Giderler → Yeni**

Kira, maaş, SGK gibi düzenli ödemeler. Aylık, üç aylık veya yıllık
tanımlanabilir. Nakit akışı projeksiyonu bunları hesaba katar.

### Nakit akışı

**Nakit Akışı** sayfası gelecek dönemdeki para giriş ve çıkışlarını
gösterir:

- Vadesi gelen alacaklar
- Ödenecek borçlar
- Vadesi gelen çekler
- Sabit giderler

Üç dövizi ayrı gösterir; tek bir TL toplamına indirmez, çünkü bu kur
riskini gizler.

---

## 12. Sık karşılaşılan durumlar

### "Bu modülü görüntüleme yetkiniz yok"

Yetkiniz olmayan bir modüle erişmeye çalışıyorsunuz. Yöneticinizden
ilgili modül yetkisi isteyin.

### Cari listesinde aradığım firma yok

Üç ihtimal:

1. Cari başka birine atanmış ve size kapalı → yöneticiden erişim isteyin
2. Süzgeç açık kalmış → süzgeçleri temizleyin
3. Cari henüz açılmamış → yeni cari ekleyin

### Bakiye beklediğimden farklı

Cari kartındaki bakiye **carinin para biriminde** gösterilir. Hareketler
farklı dövizlerdeyse her biri kendi kuruyla çevrilir.

Ekstre alıp **işlem günü kuru** seçerseniz her hareketin hangi kurla
çevrildiğini satır satır görürsünüz.

### Tutar çok büyük göründü

Ondalık ayracını kontrol edin. `2.167.218,34` yerine `216721834`
yazılırsa tutar 100 katına çıkar. Kaydı silip yeniden girin.

### Toplu aktarımda "0 kayıt aktarıldı"

Hata mesajını okuyun. En sık iki sebep:

**Blok no zaten kayıtlı** — ürün tipi yanlış seçilmiş olabilir; plakaları
blok olarak aktarmaya çalışıyor olabilirsiniz.

**Alan çok uzun** — bir değer sütun sınırını aşıyor. Hangi alan olduğu
mesajda yazar.

### Çek aldım ama müşterinin riski düşmedi

Bu doğru davranıştır. Çek tahsil edilene kadar risk devam eder. Cari
kartında "Tahsil Edilmemiş Çek" satırında görürsünüz. Çek tahsil edilince
risk düşer.

### Sayfa yavaş açılıyor

Yönetici hesabıyla deneyin. Fark varsa yetki/kapsam ayarlarıyla ilgili
olabilir; sistem yöneticinize bildirin.

---

## Günlük iş akışı örneği

Bir günün tipik akışı:

**Sabah**

1. **Bugün** sayfasını açın — vadesi geçen alacaklar ve yaklaşan çekler
2. Vadesi geçen müşterileri arayın, görüşmeyi **Müşteriler → Temas
   kaydet** ile not edin

**Gün içi**

3. Yeni teklif için **Proforma → Yeni**
4. Kabul edilen teklifi siparişe dönüştürün
5. Depoya giren malı **Stok → Yeni** ya da toplu aktarımla girin
6. Nakliye faturası gelince **Maliyetler**'den ilgili ürünlere dağıtın

**Akşam**

7. Gelen tahsilatları **Cari kartı → Tahsilat** ile işleyin
8. **Kasa Defteri**'nden gün sonu bakiyelerini kontrol edin

---

## Yardım

Beklemediğiniz bir rakam veya davranış görürseniz **ekran görüntüsü
alın** ve sistem yöneticinize iletin. Ekran görüntüsü, sorunun hangi
adımda çıktığını anlamayı çok kolaylaştırır.

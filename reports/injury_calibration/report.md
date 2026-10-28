# Tarihsel availability ve spillover deneyi

İki sezonun resmî raporları indirildi: 2024–25 için **163**, 2025–26 için
**164** maç günü; toplam **327** günlük kayıt. Çıkarılan metin, satırlar,
gerçek başlık zamanı, URL ve PDF SHA256'sı gzip JSON'da tutulur.
PDF'ler bellekte işlenip bırakılır; kalıcı tarihsel PDF kopyası yoktur.
Rapor arşivi **1.290.222 bayt**, tamamlanmış kadro etiketi arşivi
**337.254 bayt**; ikisi toplam yaklaşık **1,63 MB**'tır.

## Zaman ve ayrıştırma denetimleri

Kesim öğlen 12:00 Eastern'dır. Eski dosya adında `12PM` bulunması yeterli
değildir: bazı dosyaların iç başlığı 12:30'dur. Böyle bir dosya yerine
kesimden önceki rapor alınır. Örneğin 1 Kasım 2024 için 11:30 başlıklı
`11AM` dosyası kullanılmıştır. Her kayıtta gerçek rapor zamanı bulunur.

Eski PDF'lerde kelimelerin tek tek konumlanması ve dar boşluklar için
pdfplumber'ın metin boşluk eşiği düzeltildi. Dikey ortalanmış çok satırlı
nedenin oyuncu adından önce başlaması da ele alındı. Neden metinlerini
satıra bağlamak hâlâ metin düzenine dayalı bir heuristiktir; availability
kalibrasyonu neden sınıfını kullanmaz. Ham çıkarılmış metin korunmuştur.

Maç başlangıcının kesimden sonra olduğu, etiket kaynağının tipoff zamanı
ile ayrıca doğrulanır. Gelecek maçın final `Out/Available` durumu öğlen
öngörüsünün yerine geçirilmez. Rapor olmayan veya henüz göndermemiş takım
sağlıklı sayılmaz. Güncel kadro veya pozisyonlar geçmişe taşınmaz.

## Availability

Oyuncu maç günlükleri büyük ölçüde sadece oynanan maçları içerir. Bu nedenle
“logda yok” DNP etiketi yapılmadı. Tamamlanmış ESPN boxscore kadrolarından
yalnızca açık `didNotPlay` etiketleri alındı. Veri hacmini sınırlamak için
etiket indirmesinden önce pazartesi ve perşembe günleri sabitlendi:
iki sezonda **94 gün**. İstatistiksel aday seçimi 2024–25, değerlendirme
2025–26 olarak ayrıldı.

Başlangıç olasılıkları BayesianPlayer'ın mevcut availability/status
filtresinin geçmiş takım maçlarıyla nedensel tekrarından gelir. Tarihsel
takım üyeliği önceki gözlemlere dayalı bir vekildir; tam kadro doğruluğu
iddiası yoktur. Alternatifler durum başına 20 ve 60 önsel örnek gücüyle
geçmiş gözlemlere yumuşatmadır. Aynı günün hiçbir sonucu o günün başka
öğlen tahminini etkileyemez.

| Ölçüt | Sonuç |
|---|---:|
| Seçim dönemi doğrulanmış örnek | 720 |
| Değerlendirme dönemi doğrulanmış örnek | 620 |
| Değerlendirmede açık oynamama etiketi | 239 |
| Başlangıç Brier, değerlendirme | 0,153306 |
| Kabul edilen yeni ayar | Yok |

Önceden belirlenen 1.000 gözlem alt sınırı sağlanmadı. Eşik sonradan
düşürülmedi. Oyuncunun hem raporda hem final kadrosunda doğrulanması
gerektiğinden örneklem seçilimlidir; bütün lig için kalibrasyon sonucu
çıkarılamaz. Bu nedenle mevcut canlı availability katsayıları değiştirilmedi.

## Spillover

Pozisyonların ve transfer/kadro durumunun tam tarihsel kaydı olmadığı için
bu deney **keşif amaçlı bir vekil modeldir**. Kadro o ana kadar gözlenen
takım arkadaşlarından kurulur; en az üç geçmiş maç, son 21 günde görünme
ve takımda en az sekiz bilinen oyuncu şartı aranır. Pozisyonlar pooled'dır.
Hedef maçın boxscore'u kadro kurmak için kullanılmaz.

Rol için sabit `recent_blend` kullanılır. Geçmiş teammate yokluğunun zaten
role gömülmüş bölümü çıkarılır; availability ancak gözlemden sonra
güncellenir. İlk teknik tekrarda eksik olan bu çıkarım fark edilip düzeltildi
ve deney yeniden çalıştırıldı. Bu nedenle sonuçlar görülmemiş test olarak
sunulmaz. Ölçek adayları 0, 0,5 ve 1 olarak korunmuştur.

Başlangıç, mevcut yeniden dağıtım heuristiğinin bu vekil kadroya uygulanmış
halidir. Ölçek 0'da yeniden dağıtım kapalıdır; 240 dakika bütçesi etkisi
karşılaştırmada korunur. Ana ölçüt oynama koşuluyla dakika MAE'si,
eşlik eden koruma PTS MAE'sidir. Aynı %0,25 kazanç, haftalık bootstrap,
iki yarıda tutarlılık ve alt grup korumaları kullanıldı.

| Ölçüt | Sonuç |
|---|---:|
| Seçim oyuncu-maç | 5.087 |
| Değerlendirme oyuncu-maç | 4.410 |
| Seçilen yeniden dağıtım ölçeği | 0 |
| Başlangıç dakika MAE | 5,700278 |
| Yeniden dağıtım kapalı dakika MAE | 4,996141 |
| Göreli iyileşme | %12,35 |

Bu fark, heuristiğin bazı durumlarda fazla dakika dağıtabileceğine işaret
eder. **Canlı pozisyonlu motoru kapatmanın %12,35 iyileştireceği anlamına
gelmez.** Vekil kadro eksikleri, seçilen maçlar ve gözlenmeyen rotasyonlar
bu farkı etkileyebilir. Tarihsel sonuca dayanarak canlı spillover ayarı
değiştirilmedi; gerçek motorun `spillover_off` kolu prospektif kayda eklendi.

## Yeniden üretim

```powershell
python -m src.injury_backtest --backfill
python -m src.injury_backtest --labels
python -m src.injury_backtest --experiments
```

İlk iki komut ağ kullanır; son komut yerel verilerle çalışır. `protocol.json`
ve `label_protocol.json` aday ve örneklem kurallarını; `experiments.json`
sonuçları; `provenance.json` kaynak, veri ve protokol SHA256'larını tutar.
`coverage.json` yalnızca ham oyuncu-log eşleşmesi kapsamını denetler;
kalibrasyon sonucunun yerine geçmez. İki sezon da retrospektiftir.

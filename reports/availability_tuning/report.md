# Genişletilmiş availability kalibrasyonu

Artık yalnızca birkaç günlük arşive veya 720/620 örneğe dayanmıyoruz.
Tüm maç günleri ve açık final DNP etiketleriyle, G League satırları
çıkarıldıktan sonra **2024–25'te 2.749**, **2025–26'da 2.577** doğrulanmış
oyuncu-maç var. Değerlendirmede 948 açık oynamama etiketi bulunur.

Başlangıç, mevcut BayesianPlayer oynama geçmişi/status filtresinin
nedensel tekrarıdır. İki aday, durum başına 20 ve 60 örnek gücünde
geçmiş gözlemlere yumuşatmadır. Aynı günün sonuçları öğlen tahminlerini
güncellemez; öğrenme ancak o günün bütün tahminlerinden sonra yapılır.

2024–25'te 60 seçildi ve sabitlendi. Diğer adayın 2025–26 sonucuna
bakılarak yeniden seçim yapılmadı.

| 2025–26 | Başlangıç | Aday |
|---|---:|---:|
| Brier | 0,135674 | 0,103580 |
| Log loss | 0,414508 | 0,335502 |

Brier yaklaşık %23,66 iyileşir; haftalık bootstrap ve iki dönem yarısı
da genel kazancı destekler. Fakat **OUT grubunda 557 örnekte Brier
yaklaşık %2,30 kötüleşir**. Önceden belirlenen %1 grup koruması geçilmedi.
Bu nedenle yeni availability ayarı ana motora alınmadı. Bu kez sorun
genel örnek sayısının kabul eşiğinin altında kalması değildir.

Ayrıca bu deney **aynı gün öğlen Eastern raporu**, raporda listelenmiş
ve final kadrosunda doğrulanmış oyuncular içindir. Sonucun bütün gün
saatlerine, raporda olmayan oyunculara veya ertesi gün tahminlerine
otomatik taşınması doğru değildir. Mevcut prospektif arşiv, gerçek
çalışma kesimlerini ve sonraki gün sonuçlarını ayrı tutarak bu sınamaya
veri biriktirir.

Deney retrospektiftir. DNP, sadece oyuncu logunda görünmemekten
üretilmez. Tarihsel takım üyeliği önceki gözlemlerden kurulan bir
vekil olduğundan sonuç tam canlı sağlık/kadro sisteminin doğrulaması
olarak sunulmaz.

Yeniden üretim: `python -m src.tune_availability`. Adaylar ve kurallar
`protocol.json`, seçilen tek aday `frozen_selection.json`, değerlendirme
ve kaynak/veri hash'leri `decision.json`, satır tahminleri sıkıştırılmış
`assessment_predictions.csv.gz` içindedir. OUT korumasını kaldırmak
veya başka aday seçmek için bu değerlendirme dönemi yeniden kullanılmadı.

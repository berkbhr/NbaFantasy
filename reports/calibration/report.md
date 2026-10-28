# Sınırlı önsel ve rol kalibrasyonu — 28 Ekim 2026

**Güncel kullanım durumu:** Kabul edilen dakika değişikliği geçici kabulde
tutuluyor. Yıldız grubunda yeni sonuçlar birikene kadar kalıcı üstünlük
iddiası yok; eski yöntem paralel kaydediliyor. İzleme protokolü
`config/prospective_protocol.json`, açıklaması `docs/PROSPECTIVE.md` içindedir.

Doğrulanmış matematik düzeltmeleri korundu. Küçük aday kümesinde sezon
ağırlığını veya ESS'yi değiştirmek için yeterli kanıt bulunmadı. Canlı
dakika güncellemesinde önsel ankrajını zamanla azaltan `adaptive_anchor`
kabul edildi. Kazanç küçüktür; bütün oyuncu grupları veya istatistikler
iyileşmedi. Bu çalışma daha fazla fantasy kategorisi kazanılacağını kanıtlamaz.

## Deney tasarımı

2024–25'te **26.206** oynanmış oyuncu-maç ile seçim yapıldı. Başlangıç
politikası ve 13 alternatif, önceden yazılan beş aşamada değerlendirildi.
Her aşama, önceki aşamada kabul edilmiş politika üzerine kuruldu; bütün
kombinasyonların tarandığı veya global optimumun bulunduğu iddiası yoktur.
Şut ESS deneyi, seçilen dakika adayını da içeren küçük ortak bir yapıydı.

Seçilen tek politika donduruldu; 2025–26'daki **26.568** oynanmış
oyuncu-maç üzerinde yalnızca başlangıç ile karşılaştırıldı. Başka bir aday
bu değerlendirme sonucuna bakılarak seçilmedi. İki sezon önceki çalışmalarda
da incelendiğinden bu bir **retrospektif değerlendirmedir**, görülmemiş
bağımsız test değildir. Sonraki sezon için prospektif arşiv gereklidir.

Seçimde 2023–24 ve 2022–23; değerlendirmede 2024–25 ve 2023–24
tamamlanmış sezonları önsel olarak kullanıldı. Tek sezon adayında ikinci
sezon yoktu. Önsel dosyaların son tarihi hedef dönemin başlangıcından
önce olmalıdır; kod bunu denetler. Güncel sakatlık, kadro ve pozisyon
dosyaları geçmişe taşınmadı. Pozisyon yerine pooled popülasyon kullanıldı.

Tahmin her satır güncellenmeden önce üretildi. Dakika güncellemesi canlı
motorla aynı yordamı kullanır. Ticaret ancak yeni takımın ilk gözlemiyle
öğrenilir. Gerçek dakika tahmin girdisi yapılmaz; gerçek şut denemeleri
yalnızca isabet oranının koşullu skorunu hesaplamakta kullanılır.

## Önceden sabitlenen kabul kuralları

- Ana ölçütte en az %0,25 iyileşme.
- Takvim haftalarıyla eşli bootstrap: 2.000 örnek, seed42, %95 kazanç
  aralığının alt sınırı sıfırın üzerinde.
- Sezonun iki kronolojik yarısında da ana ölçüt kötüleşmemeli.
- Sayma NLL, şut NLL ve dakika MAE'si en fazla %0,5; her sayma
  istatistiğinin MAE'si en fazla %1 kötüleşebilir.
- En az 500 gözlemli rol ve deneyim alt gruplarında ana ölçüt en fazla
  %1 kötüleşebilir. Alt gruplar önsele göre 25+, 15–25, <15/yeni MPG;
  ayrıca hedef sezonda ilk 10 gözlem ve sonrasıydı.

Bu eşikler pratik tasarım tercihleridir; matematiksel güvenlik garantisi
değildir. Bir haftadan uzun bağımlılık, aday seçimi ve daha önce görülen
sezonlar nedeniyle bootstrap aralıkları kesin genellenme kanıtı sayılmaz.
Seçimden sonra eşikler değiştirilmedi.

Önsel/ESS için ana ölçüt, yedi sayma istatistiğinde tahmin ortalama ve
varyansına eşleştirilmiş Negative Binomial dağılımının ortalama NLL'sidir.
Bu, seçilen tek değişkenli dağılımların uygun olasılık skorudur; modelin
tam eşlenik ortak likelihood'u değildir. Dakika adayı dakika MAE'siyle,
şut güveni Beta-Binomial koşullu NLL ile seçildi. Hepsinde düşük daha iyidir.

## Seçim sonuçları

Pozitif değer ilgili aşamanın başlangıcına göre ana ölçütte iyileşmedir.

| Aday | Göreli iyileşme | Kabul |
|---|---:|---|
| Tek sezon | −%0,0279 | Hayır |
| Sabit %60 / %40 | −%0,0129 | Hayır |
| Sabit %80 / %20 | +%0,0116 | Hayır, pratik eşik altında |
| Sabit %90 / %10 | +%0,0055 | Hayır |
| Sabit ESS 120 dakika | −%0,1487 | Hayır |
| Sabit ESS 360 dakika | −%0,0841 | Hayır |
| Sabit ESS 650 dakika | −%0,1457 | Hayır |
| Eski sabit shrinkage kappa | −%0,0727 | Hayır |
| Eski toplam bazlı sezon oranı harmanı | +%0,0039 | Hayır |
| EWMA dakika | +%0,6367 | Hayır, dönem/alt grup ve belirsizlik kontrolleri |
| Zamanla azalan dakika önsel ankrajı | +%0,4416 | Evet |
| Şut önsel güveni ×0,5 | −%0,0891 | Hayır |
| Şut önsel güveni ×1,5 | −%0,0045 | Hayır |

EWMA'nın ortalama hatası daha düşük olsa da erken sezon ve düşük dakika
gruplarındaki bozulma kabul edilmedi. Tek bir toplu metrikle seçim yapılmadı.
Eski bileşenler denendi; sırf eski ve yeniyi birleştirmek için eklenmedi.

## Dondurulmuş adayın 2025–26 değerlendirmesi

| Ölçüt | Başlangıç | Aday | Değişim |
|---|---:|---:|---|
| Dakika MAE | 5,061096 | 5,041767 | %0,3819 iyileşme |
| PTS MAE | 4,606128 | 4,601985 | %0,0899 iyileşme |
| REB MAE | 1,886417 | 1,889816 | %0,1802 kötüleşme |
| AST MAE | 1,346441 | 1,344732 | %0,1270 iyileşme |
| STL MAE | 0,719328 | 0,719446 | %0,0164 kötüleşme |
| BLK MAE | 0,511782 | 0,511898 | %0,0228 kötüleşme |
| FG3M MAE | 0,890531 | 0,890467 | %0,0071 iyileşme |
| TOV MAE | 0,892881 | 0,892537 | %0,0385 iyileşme |
| Sayma NLL | 1,660103 | 1,660788 | %0,0412 kötüleşme |
| Şut NLL | 1,081548 | 1,081548 | Aynı |

Dakika kazancı maç başına **0,01933 dakika**, yaklaşık **1,16 saniyedir**.
%95 haftalık bootstrap aralığı **[0,00000750; 0,041849] dakika**;
alt sınır sıfıra çok yakındır. İki yarının kazancı 0,01666 ve 0,02185
dakikadır. Bu küçük farkı büyük bir performans sıçraması olarak yorumlamıyoruz.

25+ önsel MPG grubunda dakika MAE'si **%0,4085 kötüleşti**;
15–25 grubunda %0,1619, <15/yeni grubunda %1,2557 iyileşti.
İlk 10 gözlemde %0,2244, sonrasında %0,4252 iyileşti.
Kötüleşmeler önceden belirlenen toleransları aşmadığından aday kabul edildi.
Özellikle fantasy yıldızlarında üstünlük sonucuna varılamaz.

## Canlı kodda değişen davranış

Son beş maç ortalaması ve `k=1/3` seçimi korunur. Eskiden önsel ağırlığı
beş maçtan sonra sabit kalıyordu. Yeni yöntemde `n`, takas sonrası toplam
gözlenen maç sayısıdır: `w=n/(n+k)`. Örneğin `k=3` iken beşinci maçta
önsel payı %37,5, 20. maçta %13,04, 50. maçta %5,66 olur. İlk beş maçta
iki yöntem aynıdır. Yakın dönem ortalaması hâlâ beş maçtır; bu pencerenin
gürültüsü ortadan kalkmış değildir.

Sezon harmanı `clip(GP/65,.35,.80)`, ampirik shrinkage, mevcut ESS ve
FG/FT güveni korunmuştur. %80/%20 artık evrensel olarak optimal kabul
edilmez; yalnızca bu sınırlı deneyde değiştirmeye yeterli kanıt çıkmamıştır.
Gamma/Beta güncellemeleri ve doğrulanmış varyans/kategori hesapları korunur.
Sakatlık, rol spillover, dakika varyansı, unutma hızları ve playoff politikası
bu deneyde kalibre edilmemiştir. Haftalık varyansa kör bir çarpan eklenmedi.

## Dosyalar ve doğrulama

- `protocol.json`: Sonuçlardan önce sabitlenen adaylar ve kabul kuralları.
- `selection_results.json`, `selection_metrics.csv`: Bütün adaylar ve seçim skorları.
- `frozen_selection.json`: Değerlendirmeden önce dondurulan tek aday.
- `decision.json`: Değerlendirme, alt gruplar, karar ve veri/kaynak SHA256'ları.
- `config/model_policy.json`: Canlı motorun okuduğu kabul edilmiş ayar.

`python -m src.calibrate` JSON/CSV sonuçlarını ve canlı ayarı yeniden üretir.
Bu açıklama raporu kayıtlı koşunun yorumudur. Önceki çekirdek raporları,
farklı dakika güncellemesi ve kendi kaynak hash'leriyle tarihsel kayıtlardır.

Yeni kontroller gelecekteki boxscore değişikliklerinin geçmiş tahminleri
etkilemediğini; üç dakika politikasında da, takas dahil, canlı gözlem işleme
ile deney tahminlerinin eşleştiğini doğrular. Toplam 64 ağsız test geçmiştir.
Bu kontroller bütün olası hataları veya overfit riskini ortadan kaldırmaz.

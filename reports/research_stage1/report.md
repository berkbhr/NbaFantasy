# İlk altyapı ve pilot sonucu — 28 Ekim 2026

Bu, geliştirme planının ilk kontrol noktasıdır. Tam tuning, sakatlık/
availability deneyi veya farklı kadrolarda başarı değerlendirmesi değildir.
Ana model ve rotasyon ayarları değiştirilmedi; bildirim gönderilmedi.

## Yapılan işler

- `src.research` ile yeni, ayrı araştırma çıktı alanı kuruldu. Eski kalibrasyon
  raporları veya üretim politika dosyaları üzerine yazılmaz.
- Deney protokolü sonuçlar hesaplanmadan dosyaya yazılır. Kaynak kodu,
  kullanılan önseller ve hedef verinin SHA256'ları saklanır; işlem sonunda
  bunların değişmediği kontrol edilir. Git commit'i tek başına sürüm kanıtı
  değildir; commit edilmemiş kaynakların hash'leri de tutulur.
- 2022–23, 2023–24, 2024–25, 2025–26 günlükleri kontrol edildi: toplam
  105.253 satır, sezon başına 1.230 farklı NBA maç kimliği. Yinelenen
  oyuncu-maç, geçersiz tarih, negatif/sonlu olmayan istatistik, isabetin
  denemeyi aşması ve PTS kimliği hatası bulunmadı. Bu temel kontroller,
  kaynaktaki bütün istatistiklerin gerçek hayatta hatasız olduğunu kanıtlamaz.
- Sezon önselleri ile hedef dönemlerin zaman aralıkları çakışmıyor.
- Mevcut tarihli canlı skor kontrolü geçti. Ancak kesin tipoff ve skorun
  kapsadığı maçlar için sözleşme henüz yok; gün içi kısmi maç güvenliği bu
  ilk altyapının açık işi olarak kaydedildi.

## Küçük pilot

Nihai pilot kaydı: `20261028T164234Z/`. Önceki `20261028T164108Z/` koşusu,
veri kontrolü ek alanları ve test düzeltmesinden önceki sürümdür; silinmedi.

2024–25'in ilk 14 takvim günü: 22 Ekim–4 Kasım 2024, **2.387 oynanmış
oyuncu-maç**. Önsel 2023–24; mevcut iki sezonlu politikada 2022–23 de
kullanıldı. Sakatlık/oynama ihtimali veya fantasy aktif kadro bu pilotta
skorlanmadı. Mevcut oyuncu/rol fonksiyonları tekrar kullanıldı.

| Ölçüm | Mevcut rol yöntemi | Aynı ayarlar, eski recent_blend rolü |
|---|---:|---:|
| Dakika MAE | 5,0113 | 5,0130 |
| PTS MAE | 4,6649 | 4,6662 |
| BLK MAE | 0,53567 | 0,53565 |
| Sayma NLL tanısı | 1,63459 | 1,63464 |

Farklar çok küçüktür ve bu pilot aday seçmek için kullanılmadı. Sayma NLL'si
moment eşleştirilmiş Negative Binomial tanısıdır; şut NLL'si gerçekleşen
deneme sayısına koşulludur. Tam ortak üretici model veya haftalık kazanım
doğrulaması diye yorumlanamaz.

Son günün BLK etiketlerine yalnızca bellekte +100 eklenerek tekrar hesaplandı.
Bu etiketler görülmeden üretilen bütün oyuncu ortalamaları/varyansları ve
şut hassasiyetleri değişmedi. Bu test, incelenen oyuncu hattında gelecekteki
etiketin önceki tahmine sızmadığını gösterir; diğer kaynakların tamamı için
genel veri sızması garantisi değildir.

## Süre ve kullanım

Nihai pilotun motor süreleri:

- Mevcut politika: 0,617 saniye.
- Eski rol karşılaştırması: 0,595 saniye.
- Gelecek etiketini bozma kontrolü: 0,481 saniye.
- Denetimler ve kayıtlarla toplam: 2,041 saniye; Python başlangıcı hariç.

Oyuncu replay hesabı hızlıdır; tam sezon az sayıdaki aday için hesaplama
bekleyişinin dakikalar düzeyinde olması beklenebilir. Henüz ölçülmeyen
fantasy add/drop ve 40 lig senaryosunun maliyeti bu ölçümden çıkarılamaz.
Geliştirme, hata inceleme ve canlı sonuç bekleme süreleri ayrıca kalır.

Hesap kullanım göstergesi başlangıçta beş saatlik %0 / haftalık %13,
pilot ve testlerden sonraki ölçümde %3 / %13 idi. Bunlar yuvarlanmış,
hesap genelindeki göstergelerdir; bu işin kesin token faturası değildir.

## Doğrulama ve sonraki iş

97 unittest ve Ruff kontrol/biçim denetimi başarılı. Yeni testler bozuk
verinin sessizce temizlenmeden reddedilmesini, boş veri ve eksik kimliği,
pilot sınırını ve geliştirme/değerlendirme seed ayrımını kontrol eder.
20 + 20 lig seed'i manifeste yazıldı; bu lig deneyleri henüz çalıştırılmadı.

Sıradaki iş, gün içi skor/maç kapsamı ve kalıcı Yahoo kimliği sözleşmelerini
tamamlayıp gerçekçi küçük bir kadro/hamle performans pilotunu ölçmektir.
Bunlar kapatılmadan yeni ayar seçimi veya ana modele aday terfisi yapılmaz.

Yeniden üretim: `python -m src.research --pilot-days 14`. Her çalıştırma
yeni bir zaman damgalı klasör açar; `--output` verilirse mevcut klasörü
ezmek yerine hata verir. Çalışma ağ erişimi, Telegram veya üretim ayarı
değişikliği gerektirmez.


## Ek çalışma: maç saati, Yahoo kimliği ve kadro/hamle pilotu

28 Ekim 2026. Önceki bölümler korunarak aynı rapora eklendi; yeni bir
rapor dosyası açılmadı. Ana Bayesian/rotasyon politika dosyaları değiştirilmedi.

**Gün içi zaman güvenliği.** Resmî NBA ScheduleLeagueV2 yanıtındaki
`gameDateTimeUTC` alanı, mevcut fikstürün 1.206 farklı maç kimliği ve
Eastern tarihleriyle eşleştirildi. Bütün mevcut satırlar eşleşti; fikstüre
maç eklenmedi veya çıkarılmadı. Bu sayı sezonun 1.230 maçının tamamının
önceden tanımlı olduğu anlamına gelmez; eşleşen mevcut önbellek kapsamıdır.
Her satıra `TIPOFF_UTC` ve `CLOCK_OBSERVED_AT` eklendi. `src.game_clock`
yalnızca tam kimlik/tarih doğrulamasından sonra önbelleği değiştirir.
Bulut çalışması saatleri yeniler; yerel ağsız tahmin internet çağrısı yapmaz.

Günlük model, başlamış maçın kalan süresini henüz modellemiyor. Bu nedenle
bugünkü NBA maçlarından biri başlamışsa, saat/gözlem bilgisi eksikse veya
saat kaydı önceki Eastern günündense tam haftalık canlı birleştirme ve
hamleler bekletilir. Aynı gün bütün maçlar bitmiş olsa bile Yahoo skorunun
hangi maçları kapsadığı kanıtlanmadan yeniden projeksiyon yapılmaz.
Bu, kısmi skorun üzerine tam maçı ekleme riskini kapatan muhafazakâr bir
maç öncesi modudur; tam gerçek zamanlı maç motoru değildir.
Güncel önbellekle yapılan ağsız kontrolde tarihli skor ve maç öncesi
kontrolü geçti. Yeni bir bildirim veya otomatik kullanıcı hamlesi yapılmadı.

**Yahoo kimliği ve sürüm uyumu.** Yahoo takım numarası ile model slotu
arasındaki eşleştirme kalıcı saklanıyor. İlk geçişte kanonik takım adı veya
tekil, yeterli draft örtüşmesi gerekir; belirsiz eşleştirme reddedilir.
Bu örtüşme koruması bir model katsayısı değil, eski verinin taşınması için
kimlik kontrolüdür. Sonraki çalışmalarda takım yeniden adlandırılsa veya
bütün oyuncuları değişse de saklanan Yahoo kimliği kullanılır. Eski tekrar
örtüşme yordamı kaldırıldı. OAuth kadroları, skorları ve final eşleşme
slotları da aynı eşleştirme üzerinden geçirilir.

Tarayıcı ve OAuth oyuncunun Yahoo kimliğini taşır; bu kimlik NBA player_id
sanılmaz. Aynı Yahoo ID'nin iki takımda bulunması reddedilir. FA kanıtındaki
isim farklı yazılsa bile sahipli Yahoo ID öneriye giremez. Kadro/skor/FA
kaydına ortak `sync_id` eklenir; farklı sürümler karıştırılmaz. Tarayıcıdaki
eski görünür skor DOM'u yeniden zaman damgalanmaz, skor yeniden istenir.
Eski yerel veriler bu yeni kimlikleri kendiliğinden kazanmış sayılmadı:
canlı hesap doğrulamasının tamamlanması güncel köprüyle yeniden senkron
sonrasında mümkün. Mevcut FA kanıtı bulunmadığı için gerçek öneriler
bekletiliyor; boşta oyuncu listesi uydurulmadı. OAuth ile yeni kadro alınıp
FA kanıtı eski sürümde kalırsa da bu koruma öneriyi bekletir.

**Küçük kadro/hamle pilotu.** Bu adım performans ve uygulanabilirlik
pilotuydu; başarı oranı veya gerçekleşmiş kategori kazancı testi değildi.
2024-11-05 kesiminden önceki maçlar ve önceki günlere ait pozisyon
etiketleriyle 361 oyunculuk havuz kuruldu. 2023–24/2022–23 önselleri
kullanıldı; sıralama sezon sonu performansından gelmedi. NBA G/F/C uygunluğu
Yahoo'nun kesin uygunluğu yerine yaklaşık kabul edildi.
İki ayrı varsayımsal ligde 14x13=182 farklı sahipli oyuncu, çakışmayan 12
aday FA ve sıfır gerçek IL stash vardı. Sağlıklı oyuncuya sahte IL yeri
verilmedi. Her ligden bir eşleşme ve tek-hamle alternatifleri hesaplandı.
Sakatlık fırsat motoru kapalıydı; gelecekteki sonuçlar oyuncu güncellemesine
girmedi. Haftanın gerçekleşeni henüz skorlanmadı.
Zamanlama için kullanılan 9000/9001 seed'leri planın 20+20 geliştirme/
değerlendirme liglerinden ayrıdır. Ön mühendislik denemesinde 1000/2000
ile de yalnızca zamanlama ve model beklentisi bakıldı; gerçek hedef
sonuçları kullanılmadı ve hiçbir politika seçilmedi.

| Seed | Eşleşme hesabı | 12 adayla hamle hesabı | Dönen alternatif |
|---|---:|---:|---:|
| 9000 | 0.075 sn | 0.413 sn | 5 |
| 9001 | 0.068 sn | 0.576 sn | 5 |

Veri hazırlama dahil toplam 1.834 saniye. Bu, 40 lig,
tüm eşleşmeler/haftalar, geniş FA havuzu, sakatlık ve çok sayıda politika
çalışmasının tamamının aynı sürede biteceğini göstermez. Küçük pilotta
hesap yükü düşük; temel maliyetin tüm işin geliştirilmesi/doğrulanması ve
daha geniş deneyler olduğu görülüyor.

Tekrar üretim: `python -m src.roster_pilot`. Komut dosyaya rapor yazmaz,
ağ erişimi ve bildirim yapmaz; JSON'u stdout'a verir. Kullanılan bütün
veri/kod hash'leri çalışmanın başında alınır, sonunda sabitlik doğrulanır.
Bu koşunun sıralı JSON hash-manifest özeti (SHA256): `701747a623f0c17ab1dd43cafebba022f0551d8ae3f36150dbaecf5b15e40be9`.
Kaynak ve sonuçlar sonraki commit içinde bu raporla birlikte korunacak.

**Doğrulama:** 105 unittest, Ruff kod ve biçim kontrolü geçti. Yeni testler
ilk tipoff anında engelleme, eksik/eski/gelecek saat kaydı, UTC/Eastern
tarih eşleştirmesi, takımın tamamen değişmesine rağmen kimliği koruma,
çift sahipli Yahoo ID, karışık sync sürümü ve final slot eşleştirmesini kapsıyor.

Açık kalanlar: hesap üzerinden yeni Yahoo kimliklerinin ilk canlı senkronu;
tam gün içi kısmi maç motoru; 20+20 ligde gerçek sonuçlu dayanıklılık ve
net hamle kazancı; availability/rotasyon tuning'i ve adayın canlı kabulü.
Bu işler bu pilotun tamamlanmasıyla yapılmış sayılmadı.


## Ek çalışma: gerçek NBA sonuçlarıyla kadro dayanıklılığı ve rol karşılaştırması

28 Ekim 2026. Bu bölüm aynı rapora eklenmiştir. Koşu kimliği:
`roster_20261028T172809Z`; protokol ve teknik sonuçlar
`data/archive/experiments/` altında sıkıştırılarak saklanır.

Deneyden önce sabitlenen kapsam: 2024–25'te 20, 2025–26'da ayrı 20 seed;
14 takım x13 sahipli oyuncu. İlk 14 günlük geçmişten sonraki ilk pazartesiden
sezon sonuna kadar tam pazartesi–pazar pencereleri. Her lig-haftada 7 farklı
eşleşme; bir odak takım için tek hamleli model ve basit fikstür karşılaştırması.
Dengeli/uzun ağırlıklı/kısa ağırlıklı takım profilleri önsel MPG katmanları
içinde oluşturulur. Aynı oyuncu bir ligde iki takımda bulunamaz.

Tahmin anından önceki oyuncu ve pozisyon kayıtları kullanılır. Hafta için
aktif kadrolar hedef sonuçlar görülmeden dondurulur; bu başlangıçlarla gerçek
NBA üretimi puanlanır. Bench üretimi eklenmez. Alınan oyuncu kadar bırakılan
oyuncunun kaybedilen kullanılabilir üretimi de sonuçta yer alır.

Bu ilk referansta sakatlık dağıtımı kapalı, IL stash sayısı sıfırdır.
Kullanılan eligibility geçmiş NBA G/F/C bilgisidir; tam Yahoo pozisyonları
değildir. Önsel GP>=10, tahmin öncesi görülmüş takım ve pozisyon şartı
çaylakları ve henüz görülmemiş bazı oyuncuları dışarıda bırakır. Haftalık
sahiplikler varsayımsaldır; bir sezonun kesintisiz işlem geçmişi oynatılmıyor.
Gerçek Yahoo FA havuzu/waiver süreleri ve rakibin hamle tepkileri bilinmiyor.
Hamleler bu kontrollü ligde anında yapılabilen tek FA işlemi varsayımıyla
karşılaştırılır; sınırsız işlem hakkı verilmez.

Tarihsel fikstür son gerçekleşmiş takvimden geliyor. Hangi ertelemenin
hangi kesimde bilindiğinin tam arşivi yok; bu nedenle takvimin baştan
bilindiği varsayımı tarihsel sonuçlara iyimserlik katabilir. Bu sınırlılık
yeni canlı kesim arşivinin yerini alamaz.

Bağımsız örnek sayısı lig/seed sayısı değildir. Kazanç belirsizliği gerçek
NBA takvim haftaları eşli yeniden örneklenerek hesaplanır.

Rol deneyi bu kadro referansından ayrıdır: 2024–25 üzerinde mevcut
adaptive_anchor, recent_blend ve ewma dakika MSE'siyle karşılaştırılır.
MAE, üretim, dönem ve alt grup korumaları aynı anda uygulanır. Seçim
dondurulduktan sonra yalnızca tek aday 2025–26'da değerlendirilir.
Kadro referansı ana motorun mevcut ayarında tutulur; rol adayına farklı
kadro sonuçlarına bakılarak gizli geçiş yapılmaz. Hiçbir politika dosyasına
ana modele terfi yazılmaz.

Küçük uçtan uca smoke koşusu ayrı kimlikle korunmuştur:
`roster_20261028T172519Z` (2 seed x2 hafta/sezon). Tam deneyin örneklemine
eklenmez. Protokoldeki parametreler veya kabul eşikleri smoke sonucuna göre
değiştirilmedi; tam çıktı için eylem kimlikleri ve kategori olasılıkları
daha ayrıntılı saklandı.


### Tam referans koşusunun sonuçları

40 varsayımsal lig, sezon başına 22 tam NBA haftası: toplam **880 odak takım-hafta
hamle durumu**, **6.160 eşleşme**, **55.440 kategori sonucu**. Bunlar 880 bağımsız
NBA haftası değildir; bağımsız zaman ekseni sezon başına 22 takvim haftasıdır.

| Sezon | Modelin tek hamlesi: ortalama net kategori puanı | Haftalık blok %95 aralık | Yalnız maç sayılı basit hamle |
|---|---:|---:|---:|
| 2024–25 | +0.407 | [0.303; 0.503] | -0.006 |
| 2025–26 | +0.524 | [0.403; 0.645] | +0.022 |

Net katkı, hamle yapmama referansına göredir; bırakılanın ve aktif kadro
değişiminin etkisi dahil edilmiştir. Basit kontrol yalnızca kalan maç sayısını
önceler; eşitlikte dakika/oyuncu kalitesi kullanmaz. Bu kolay kontrolün yenilmesi
tek başına daha güçlü streaming yöntemlerine üstünlük kanıtı değildir.
Bu nedenle aşağıda iki daha güçlü kontrol için sonradan eklenen duyarlılık
analizi ayrıca raporlanacaktır; bağımsız yeni test diye adlandırılmaz.

| Sezon | Model daha iyi | Daha kötü | Aynı |
|---|---:|---:|---:|
| 2024–25 | 189 | 53 | 198 |
| 2025–26 | 205 | 51 | 184 |

Bütün 880 durumda motor pozitif beklenen kazançlı bir hamle buldu. Telegram'ın
gösterim eşiği bu referansta ayrıca uygulanmadı. Bunlar gerçek hesapta
uygulanmış 880 işlem değildir.

| Sezon / lig profili | Modelin ortalama net katkısı | Haftalık blok %95 aralık |
|---|---:|---:|
| 2024_25:balanced | +0.405 | [0.265; 0.568] |
| 2024_25:center_heavy | +0.289 | [0.143; 0.451] |
| 2024_25:guard_heavy | +0.526 | [0.351; 0.708] |
| 2025_26:balanced | +0.549 | [0.403; 0.701] |
| 2025_26:center_heavy | +0.432 | [0.261; 0.587] |
| 2025_26:guard_heavy | +0.578 | [0.425; 0.747] |

Bu sınırlı profil değişimlerinde katkı her iki sezonda pozitiftir. Profiller
önsel MPG katmanları içinde oyuncu değişimiyle üretilir; bütün olası punt,
sakatlık, IL ve 210 sahipli oyuncu yapılarını kapsamaz. Sakatlık bilgilerinin
bu referansa katılmaması, gerçek üretimdeki sakatlıkların ortadan kalktığı
anlamına gelmez; bunların tahmin hatasına etkisi burada ayrıştırılmış değildir.

### Haftalık kategori olasılığı tanıları

| Sezon | Eşleşme | Üç sonuçlu kategori Brier | Kategori puanı MAE | Ortalama puan hatası |
|---|---:|---:|---:|---:|
| 2024_25 | 3080 | 0.4459 | 1.414 | -0.000 |
| 2025_26 | 3080 | 0.4530 | 1.458 | -0.017 |

Brier kazanım/beraberlik/mağlubiyet üçlüsündeki kare hataların toplamının
kategori ortalamasıdır; düşük daha iyi. İki sezon farklı olaylar olduğundan
bu seviyeler doğrudan sürüm kazancı olarak yorumlanmaz. Ortalama puan
hatasının sıfıra yakın olması tüm olasılık aralıklarının iyi kalibre olduğu
anlamına gelmez. Kategori bazlı ondalık olasılık dilimlerinin tahmin/gerçekleşme
tablosu teknik `reliability.json.gz` çıktısında saklanmıştır.

### Sınırlı rol karşılaştırması

Bu tur mevcut kalibratörün geliştirme sezonu seçimi + sonraki sezon
karşılaştırmasıdır; planın bütün bileşenleri kapsayan iç/dış zaman bloğu
tuning altyapısının tamamlanması değildir. 2024–25 sonuçları geliştirme
kanıtıdır; 2025–26 daha önce incelendiği için geçmişe dönük doğrulamadır.

2024–25 dakika MSE'si: mevcut yöntem 44,3253; recent_blend 43,8045;
ewma 43,3517. EWMA daha düşük genel hatasına rağmen ilk 10 gözlem
korumasından kaldı ve 2025–26'da ikinci aday olarak denenmedi.
recent_blend seçilip donduruldu. 2025–26'da 26.568 oynanmış oyuncu-maç:

| Ölçüm | Mevcut adaptive_anchor | Dondurulmuş recent_blend |
|---|---:|---:|
| Dakika MSE | 43.3043 | 42.9634 |
| Dakika MAE | 5.0418 | 5.0611 |

MSE yaklaşık %0,79 iyileşirken MAE yaklaşık %0,38 kötüleşir. Kayıtlı
mevcut MSE/üretim/dönem/alt grup kabul kontrolü geçti. Bunun anlamı
her grupta daha iyi olduğu veya dağılım kalibrasyonunun tamamlandığı değildir.
Seçimden bağımsız açıklayıcı alt grup MAE tablosu:

| Önsel rol / gözlem grubu | n | Mevcut MAE | Aday MAE |
|---|---:|---:|---:|
| cohort:15-25 | 7804 | 5.0260 | 5.0342 |
| cohort:25+ | 10243 | 4.3895 | 4.3717 |
| cohort:<15/new | 8521 | 5.8403 | 5.9145 |
| experience:first10 | 5442 | 5.3138 | 5.3258 |
| experience:later | 21126 | 4.9717 | 4.9929 |

25+ MPG grubunda iki ölçüt de iyileşir; <15/yeni grubunda MAE yaklaşık
%1,27 kötüleşir. Bu tabloya bakılarak yeni kazanan veya oyuncu grubuna özel
kural seçilmedi. Ana ayar değiştirilmedi. Yukarıdaki kadro/hamle sonuçları
mevcut motorla üretildi; recent_blend'in aynı katkıyı verdiği test edilmedi.
Eski rolün bazı yönlerini kullanma fikri aday olarak anlamlıdır; bütün
eski sürüme dönme veya her oyuncuda aynı rolü seçme kanıtı yoktur.

### Süre, bütünlük ve sınırlar

Tam koşu 34.0 dakika sürdü. Sonunda başlangıçtaki bütün
veri/kod hash'leri tekrar kontrol edildi ve değişmemişti. Her iki sezonun
fikstüründeki 1.230 maçın tamamı NBA sonuçlarında mevcut; oyuncu-tarih
çiftlerinde de tekrar yok. Hedef tarihten sonraki oyuncu sonuçları karar
girdisi yapılmadı; yalnızca sabitlenmiş aktif kadroları skorlamak için kullanıldı.

Başlıca sınırlar: 182 sahipli oyuncu ve sıfır IL; pozisyonu/takımı geçmişte
görülmüş ve önsel GP>=10 oyuncular; sakatlık dağıtımı kapalı; tek anlık
hamle; varsayımsal FA/waiver; sabit rakip günlük kadro politikası; son
gerçekleşmiş tarihsel fikstür. Bu sonuçlar, tam canlı 210 oyunculu
Yahoo liginde veya sakatlık/transfer dönemlerinde aynı kazancı kanıtlamaz.
Ana Bayesian ve rotasyon politika dosyaları değiştirilmedi.


### Daha güçlü streaming kontrolleri: sonradan eklenen duyarlılık analizi

İlk referansın eşit maçlı oyuncularda kaliteyi kullanmaması nedeniyle iki
kontrol daha tanımlandı. Bu gereksinim ilk genel sonuç görüldükten sonra
belirlendiği için **posthoc duyarlılık analizi** olarak kaydedildi; yeni
görülmemiş test diye sunulmaz. İki kural sonuçları hesaplanmadan kendi
protokolüne yazıldı; sonuçlara bakıp yeni kazanan veya katsayı seçilmedi.

1. Önce kalan maç sayısı, eşitlikte yüksek temel dakika beklentisi.
2. Kalan maç x temel dakika x oynama olasılığı en yüksek oyuncu.

İki kontrol de önceki basit yöntemin aynı yasal bırakılabilir oyuncusunu
kullandı. Sonuç bilmeden seçilen yeni aktif kadro skorlandı. Her 880
durumda eski hamlesiz referans sonucu yeniden üretildi ve birebir eşleşti.

| Sezon | Hamlesiz duruma göre model | Maç + dakika eşitlik çözümü | Toplam beklenen dakika |
|---|---:|---:|---:|
| 2024_25 | +0.407 | +0.347 | +0.427 |
| 2025_26 | +0.524 | +0.408 | +0.517 |

| Sezon / karşılaştırma | Model eksi kontrol | Haftalık blok %95 aralık |
|---|---:|---:|
| 2024_25 / quality_tie | +0.0602 | [-0.0841; 0.2068] |
| 2024_25 / total_minutes | -0.0205 | [-0.1670; 0.1227] |
| 2025_26 / quality_tie | +0.1159 | [-0.0375; 0.2762] |
| 2025_26 / total_minutes | +0.0068 | [-0.1694; 0.2102] |

**Yorum:** Model hamle yapmamaktan daha fazla kategori puanı topluyor; fakat
iyi bir dakika/fikstür kontrolüne ek katkısı bu veriyle doğrulanmadı. Her iki
sezonda, iki güçlü kontrole karşı da model farkının aralığı sıfırı içeriyor.
Bu, yöntemlerin eşdeğer olduğunun kanıtı değildir; güvenilir üstünlük için
kanıt yetersizdir. Yalnızca kolay bir fikstür kontrolünün yenilmesi, karmaşık
karar motorunu haklı çıkarmaya yetmez.

Toplam dakika kontrolü de modelin aynı temel dakika/oynama tahminlerini
kullanır. Dolayısıyla sonuç, Bayesian oyuncu tahminlerinin gereksiz olduğunu
göstermez; bu tahminlerin üstüne eklenen kategori odaklı hamle sıralamasının
ilave değerini henüz gösteremediğimizi söyler.

2024_25: model ile toplam-dakika kontrolünün birebir aynı ekleme/bırakması 49/440 durumda gerçekleşti.

2025_26: model ile toplam-dakika kontrolünün birebir aynı ekleme/bırakması 67/440 durumda gerçekleşti.

Ek kontrol 3.0 dakika sürdü. Kayıtlar aynı deney klasöründeki
`streaming_sensitivity_protocol.json.gz`, `streaming_sensitivity.csv.gz` ve
`streaming_sensitivity_summary.json.gz` dosyalarında.

### Bu aşamanın kararı

- Ana model/rotasyon ayarlarında değişiklik yok.
- Eski rolün bazı ortalama dakika hatalarını azaltabildiği bulundu; düşük
  rol grubunda MAE bozulması ve henüz tamamlanmamış belirsizlik/karar
  değerlendirmesi nedeniyle bütün oyunculara otomatik uygulanmadı.
- Farklı kadrolarda hamlesiz referansa göre kazanç bulundu; güçlü streaming
  kontrolüne üstünlük bulunamadı.
- Sonraki geliştirmede güçlü toplam-dakika kontrolü kalıcı referans olmalı.
  Sakatlık/IL ile derin havuz, gerçekçi rakip politikaları, pozisyon uygunluğu
  ve daha küçük kategorik farkların katkısı ayrıca sınanmalı. Bu daha zorlu
  koşullarda karmaşık yöntem yine artı sağlamazsa basit yöntem tercih edilebilir.
- Bu sonuçlardan sonra yalnızca kazanan bir örneklem veya yeni kontrol
  seçerek üstünlük aranmayacak. Yeni aday/kurallar yeni sürüm ve sabit
  değerlendirme protokolüyle araştırılacak.

105 eski test + bu aşamadaki 3 yeni test, toplam108 test başarılı. Yeni
testler bench'teki sonradan çok iyi oynayan oyuncuyu skora sızdırmama,
tekilleştirilmiş13 kişilik kadro/tier sahipliği ve beraberlik içeren üç
sonuçlu Brier hesabını kapsıyor. Ruff kod/biçim kontrolleri başarılı.
Bildirim gönderilmedi, kullanıcı kadrosunda işlem yapılmadı.

Ek yorum sınırları: Kadro profili değişimi son üç önsel MPG draft
katmanında yapıldı; bu tam punt veya tamamen uzmanlaşmış takım testi değildir.
Güven aralıkları takvim haftası blokları içindir; bir haftadan uzun sakatlık/
oyuncu bağımlılığının tamamını modelledikleri varsayılmamalıdır. Kaynak
hash'leri koşunun gerçek dosya baytlarını kaydeder; platformlar arası
satır sonu farkları da raw SHA256'yı değiştirebilir.

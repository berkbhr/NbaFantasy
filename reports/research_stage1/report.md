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

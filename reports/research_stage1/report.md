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

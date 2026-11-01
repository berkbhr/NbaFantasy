# Yerel ana panel

Proje kökünde tek komut:

```powershell
.\.venv\Scripts\python.exe -m src.report_panel
```

Ana ekran `http://127.0.0.1:8767` adresinde açılır. Aynı süreç Yahoo köprüsünü
8765, mevcut takas panelini 8766 portunda başlatır. Önceki ayrı Yahoo/takas
sunucuları açıksa terminalde Ctrl+C ile kapatın; ana panel bilinmeyen bir
süreci durdurmaz veya var olan portu devralmaz.

1. Yahoo Matchup sekmesinde mevcut NBA Fantasy Sync yer imine tıklayın.
2. Kadro/skor kaydı bilgisayara gelir. Mevcut canlı yenileme ve ayarlı bildirim
   pipeline'ı yerelde çalışır; Git add/commit/push yapılmaz.
3. Ana panelde kayıt, işlem ve Telegram API kabul durumunu izleyin.
4. **Raporu hesapla** mevcut önbelleklerden mevcut forecast fonksiyonunu çağırır.
   Yeni veri indirmez, bildirim göndermez veya forecast arşivine kayıt yazmaz.
5. **Excel indir** ekrandaki raporun ham sayılarını gerçek XLSX olarak indirir.
   Yüzdeler Excel'de 0–1 kesir olarak etiketlidir; model hesaplaması yeniden yapılmaz.
6. **Takas analizi** mevcut takas ekranını yeni sekmede açar. Eski komutu ayrıca
   çalıştırmanız gerekmez. Takas hesaplamaları ve ekranı değiştirilmedi.

Yerel canlı pipeline NBA verilerini indirebilir, önbellek/raporları günceller ve
ayarlanmış Telegram/Discord alıcısına gönderir. Bu, Yahoo yer imiyle başlatılan
bilinçli senkronun devamıdır; saatli görev yoktur. Telegram ayarları hâlâ
`config/telegram.json` veya mevcut ortam ayarlarından okunur. Başarılı pipeline
durumu, Telegram teslim kanıtı değildir; panel ayrı API kabul durumunu gösterir.

Panel eski kayıtlı raporu açabilir; güncel kadroyla eşleşmesi kanıtlanmadığında
uyarı verir. Yeni hesaplama ile kadro kimliği eşleştirilir; yeni bir senkron eski
panel raporunu güncelmiş gibi göstermez. Excel'e rapor zamanı ve kayıt durumu
da eklenir. Eşzamanlı senkron/rapor işlemleri ortak kilitle sıralanır.

Panel ve Excel, Telegram'ın `notification_snapshot` doğrulama kuralını kullanır.
Model canlı haftalık hesabı durdurmuşsa, ham kalan-maç hesapları haftalık
olasılık/puan diye gösterilmez. Uygun, aynı eşleşmeye ait son geçerli arşiv
varsa tarihi açıkça belirtilir ve eski hamleler kullanılmaz; yoksa tahminin
durdurulduğu açıklanır. Oynanan/toplam/kalan maçlar son raporun doğrulanmış
Yahoo skor kaydından ayrıca gösterilir; aktif kadro planından türetilmez.
Arşiv tahmininin eski maç sayıları güncel sayıların yanında ayrı etiketlenir.
Hamle seçenekleri bölümü her raporda görünür: güncel/geçerli raporda ekle-bırak
satırları, aday yoksa bunun açıklaması, durdurulmuş veya arşiv raporunda ise
güncel hamlelerin neden kullanılamadığı gösterilir. Bu görünüm için Node testleri
`node --test tests/report_panel.test.cjs` ile de çalıştırılabilir.

Kapatmak için ana panelin terminalinde Ctrl+C kullanın. Bilgisayar ve süreç
açık olmalıdır. Bu özellik GitHub workflow'u, repo görünürlüğü, Git indeksi
veya mevcut veri dosyalarının Git takibini değiştirmez. Geçmiş public kayıtlar
için önceki gizlilik raporu ayrıca geçerlidir.

## Doğrulama

Bu değişiklikte matematik/model kaynakları, mevcut `trade_panel.py` ve
`trade_panel.html` korunmuştur. 781 önsel, 102 injury kaydıyla canlı istatistikler,
z skorları ve örnek 13 oyunculuk haftalık dağılım önceki sonuçlarla eşittir.
136 korunan kaynak/veri/config/rapor dosyasının hash'i değişmemiştir.

Python 3.11 kök suite 209 test, yerel research 157 test, Node suite
19 test ile geçti. Panel testleri yanlış haftalık puanın gizlenmesini,
doğrulanmış maç sayılarını ve hamle seçeneklerinin durumlarını kapsar.
Ruff check ve format check temiz. İlk sandbox panel koşusu,
geçici dizin ve yerel socket izinleri nedeniyle başarısız olmuş; aynı testler
izinli ortamda tekrar geçmiştir. Browser üzerinden gerçek Excel indirmesi
ve ham sayısal değer eşitliği kontrol edildi. Canlı veri yenileme, Telegram
gönderimi veya Yahoo'da gerçek senkron testi çalıştırılmadı.

Kurulum sırasında bu makinede `config/telegram.json` ve Telegram ortam ayarları
yoktu. Bu durumda panel “Telegram: yerel ayar gerekli” gösterir; rapor/Excel ve
takas ekranı kullanılabilir. Bot bilgileri sohbet veya public Git'e yazılmamalı;
mevcut `config/telegram.template.json` şablonuna göre yalnız yerelde ayarlanmalıdır.

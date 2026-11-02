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
   Yeni veri indirmez, bildirim göndermez veya prospektif forecast arşivine kayıt yazmaz.
   Geçerli sonucu yalnız görünüm için `reports/panel_forecasts/` altında saklar.
5. **Haftalık Excel indir** seçili haftayı tek çalışma sayfası olarak indirir.
   Hafta seçicisinden biten haftalara da erişilir. Yüzdeler yüzde biçiminde,
   beklenen kategori puanı iki ondalıkla görünür; ham sayısal değerler korunur.
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
Maç öncesi panelde hesaplanmış geçerli tahmin bu yerel görünüm önbelleğinde
yeniden başlatma sonrasında da bulunur. Maç sırasında aynı eşleşmenin en fazla
24 saatlik son geçerli tahmini tarihiyle açılır; canlı kalan dakika hesabı
yapılmaz ve eski hamleler uygulanabilir öneri olarak sunulmaz. Yeni kadro/skor
kaynaklarıyla eşleşmeyen eski ana rapor panelde ve Excel'de gösterilmez.

Hafta geçişinde Yahoo'nun `-/-` ve `-` değerleri yalnız oynanan maç sayısı
sıfır olan tamamen boş istatistik satırında sıfır kabul edilir. Skorun tarih
aralığı Eastern gününü kapsamalıdır. Fikstür okuyucusu aynı doğrulanmış sayfayı
kullanır; genel Yahoo adresinin eski haftayı döndürmesi skoru eski haftaya
çeviremez. Kod değişikliğinden sonra panel süreci yeniden başlatılmalıdır.
Hamle seçenekleri bölümü her raporda görünür: güncel/geçerli raporda ekle-bırak
satırları, aday yoksa bunun açıklaması, durdurulmuş veya arşiv raporunda ise
güncel hamlelerin neden kullanılamadığı gösterilir. Bu görünüm için Node testleri
`node --test tests/report_panel.test.cjs` ile de çalıştırılabilir.

Kapatmak için ana panelin terminalinde Ctrl+C kullanın. Bilgisayar ve süreç
açık olmalıdır. Bu özellik GitHub workflow'u, repo görünürlüğü, Git indeksi
veya mevcut veri dosyalarının Git takibini değiştirmez. Geçmiş public kayıtlar
için önceki gizlilik raporu ayrıca geçerlidir.

## Haftalık takip

Yahoo'yu yer imiyle günlük güncelleyin. Başarılı yerel pipeline'ın güncel kaynaklarla
eşleşen raporu otomatik kaydedilir; panelden hesaplanan geçerli rapor da aynı
kayıt yolunu kullanır. Gün başına yalnız **son geçerli tahmin** tutulur. Gün içindeki
yeni tahmin aynı satırı günceller; hatalı/geçersiz hesap eski geçerli kaydı silmez.
Maçlar başlamadan, oynanan maç sayıları sıfırken yakalanan ilk hafta başı tahmini
ayrıca korunur. Günler Yahoo'nun Eastern takvimine göredir. Geçmiş kayıt olmayan
günler boş kalır; önceden gerçekten saklanmış panel kayıtları başlangıçta aktarılır.

Hafta kapandıktan sonraki Yahoo senkronu bir önceki haftanın skorunu ayrıca
almayı dener. Tamamlanmış kayıt bulunursa Excel'de son skor, günlük tahminlerin
bu skordan farkı ve kategori karşılaştırması görünür. Bu okuma başarısızsa
güncel senkron devam eder ve sonuç bölümü eksik olarak işaretlenir. Yakalanan
skorun zamanı belirtilir; sonraki Yahoo stat düzeltmeleri yeni yakalamada güncellenir.
FG/FT kategori sonuçları isabet/deneme oranlarından türetilir; Yahoo yuvarlaması
çok yakın sonuçlarda farklılık oluşturabilir. Bu karşılaştırma resmi Yahoo
etiketi veya tek haftalık bilimsel kalibrasyon kanıtı olarak sunulmaz.

Yerel takip `reports/weekly_history/` altında kalır, Git'e eklenmez. Haftanın
başlangıç tahminini, günlük son tahminlerini ve son skorunu görmek için her gün
dosya indirmeniz gerekmez. Hafta bitince hafta seçicisinden ilgili dönemi seçip
bir kez indirin. Güncel rapor, maç sayıları, kategoriler, hamleler ve kadro
uyarıları aynı sayfadadır; uzun veri notları varsayılan olarak daraltılmıştır.
Günlük takipte senin ve rakibinin oynanan/toplam maç sayıları da görünür.
Bu sayılar son doğrulanmış skor yakalamasından ayrı güncellenir; maç sırasında
yeni geçerli tahmin yoksa önceki geçerli tahmin korunur, maç sayıları yenilenir.
Hamlelerin altında yalnız eklenecek oyuncunun mevcut `exp_stats_pg` maç başı
PTS, REB, AST, STL, BLK ve 3PT ortalamaları bir kez gösterilir; tekrar hesaplanmaz.

## Doğrulama

Bu değişiklikte matematik/model kaynakları, mevcut `trade_panel.py` ve
`trade_panel.html` korunmuştur. 781 önsel, 102 injury kaydıyla canlı istatistikler,
z skorları ve örnek 13 oyunculuk haftalık dağılım önceki sonuçlarla eşittir.
136 korunan kaynak/veri/config/rapor dosyasının hash'i değişmemiştir.

Haftalık takip/Excel teslimi izole Python 3.11 kaynak ağacında 216 kök test,
23 Node testi ve Ruff check/format ile doğrulandı. Tek sayfalık dosya ayrıca
Excel'de salt okunur açılarak sayısal yüzde/puan biçimleri ve görünüm kontrol
edildi. Önceki panel doğrulamasında yerel research 157 testle geçmişti;
bu son görünüm/kayıt değişikliğinde research suite yeniden çalıştırılmadı.
Panel testleri yanlış haftalık puanın gizlenmesini,
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

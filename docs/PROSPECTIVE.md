# Tahmin ve sonuç arşivi

Canlı tahmin bütün haftanın dokuz kategori sonucunu değerlendirir. Hafta
başındaki kayıt korunur; hafta içindeki güncellemeler yeni skor, kadro,
sakatlık ve fikstür bilgisiyle ayrıca kaydedilir. Güncelleme, önceki tahmini
geriye dönük değiştirmez. Günlük oyuncu sonuçları yardımcı hata tanısıdır.

`data/archive/predictions/` kesim zamanı, kayıt zamanı, kaynak/veri hash'leri,
Yahoo kadro ve skorları, bilinen sakatlıklar, haftalık olasılıklar ve önerileri
sıkıştırılmış eklemeli dosyalarda tutar. Tahmin dosyası yeniden yazılmaz.
Sonuçlar `outcomes/` ve `weekly_outcomes/` altında ayrı saklanır. Eksik oyuncu
kaydı DNP sayılmaz; haftalık sonuç için doğrulanmış final gerekir.

Haftalık güncellemelerin açıklaması önceki aktif kadro planına dayanır:
tamamlanan maçların belirsizlikten çıkması, skorun eski beklentiden sapması ve
kalan haftanın beklentisinin değişmesi ayrı gösterilir. Bu sıralı hesap
ayrıştırması nedensellik kanıtı değildir. Oyuncu örnekleri planlanan aktif
kadroyla NBA boxscore'unu karşılaştırır; gerçek Yahoo günlük başlangıç
kadrosu farklı olabilir. Önceki ayrıntı veya uyumlu model sürümü yoksa
ayrıştırma yapılmaz.

Günlük bulut otomasyonu arşivi `nba-fantasy-bot` dalında korur. Gönderilen
bildirimin tahmin ve mesaj hash'i `notifications/` altında saklanır; token ve
chat kimliği saklanmaz. Telegram API yanıtı `ok=true` ve `message_id`
içermelidir. Bildirim başarısız olsa da tahmin arşivi korunur.

Araştırma modelleri, özel kabul protokolleri, testler ve eski sonuçlar yerel
`research/legacy/` ve `research/current/` altındadır. Bu klasörler yayımlanan
uygulamanın çalışma bağımlılığı değildir. Ana politika dosyaları araştırma
sonuçlarına göre otomatik değiştirilmez. Olasılıkların doğruluğu, farklı
oyuncu grupları ve haftalık karar katkısı ayrı değerlendirilir.

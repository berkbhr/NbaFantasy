# Prospektif tahmin ve sonuç arşivi

Başlangıç: 28 Ekim 2026, Berlin tarihi. Kesim ve kayıt zamanları gerçek
UTC saatinden üretilir; ilk kayıt Berlin'de 28 Ekim iken UTC'de hâlâ
27 Ekim olabilir. Geçmişe tarih atılarak görülmemiş tahmin üretilmez.

## Ne saklanır?

`python -m src.forecast` ve buluttaki `src.cloud_sync`,
`data/archive/predictions/<UTC-zaman>.json.gz` dosyası oluşturur.
Dosya aynı adla yeniden yazılamaz. İçerik:

- Kesim zamanı, hesaplamanın tamamlandığı kayıt zamanı ve tahmin kimliği.
- Tahmin anındaki Yahoo kadroları, IL/waiver durumu, skor ve öneriler.
- Aktif sakatlıklar, rapor zamanı, kaynak/veri SHA256'ları ve resmî rapor arşiv bağlantısı.
- Oyuncunun takım/pozisyon eşlemesi, öğrenilmiş rolü, oynama olasılığı,
  dakika ve kategori tahmin ortalama/varyansları.
- Ana `adaptive_anchor`, eski `recent_blend` ve ana durumdan üretilen
  `spillover_off` oyuncu tahminleri. Eski rol için ayrı motor kurulur;
  sadece tahminin üzerine sonradan bir çarpan eklenmez.
- Kullanılan protokolün tam kopyası ve model ayarı.

Oyuncu arşivinde puanlama için gereken marjinal momentler sekiz anlamlı
basamakla saklanır; çok küçük varyanslar sıfıra yuvarlanmaz. Canlı karar
hesabı tam duyarlıkla çalışır. Haftalık ortak kovaryansın bütün ara
terimleri her oyuncu kaydında tekrar çoğaltılmaz.

Ana ve eski rol hesaplamaları arasında girdi dosyalarının hash'leri
değişirse kayıt reddedilir. Önsellerin kaynak maç günlükleri veri
deposunda korunur; her çalışmada büyük ham dosyalar çoğaltılmaz.

`data/archive/injury_reports/` resmî raporların ayrıştırılmış, hash ile
tekilleştirilmiş anlık kayıtlarını tutar. Her koşunun aktif sakatlık listesi
ayrıca kendi tahmin girdisinin içindedir. Güncel motor için tek dönen PDF
önbelleği vardır; tarihsel indirme PDF biriktirmez.

## Kesim ve gerçekleşen sonuç

Yerel fikstürde kesin tipoff zamanları bulunmadığı için, ilk puanlanan
oyuncu ufku **kesimden sonraki Eastern takvim günüdür**. Aynı günün
başlamış maçları görülmemiş teste katılmaz. Oynanmış gözlemler tahminden
önceki tamamlanmış günlerden alınır. Haftalık rapor daha geniş bir öngörü
olsa da oyuncu doğrulama ufkuyla karıştırılmaz.

`src.prospective.settle` sonraki koşularda sonuçları eşler. Sonuçlar
`data/archive/outcomes/<tahmin-kimliği>/` altında ayrı, eklemeli kayıtlardır.
Veri düzeltmesi gelirse yeni içerik hash'iyle sonuç revizyonu eklenir;
eski tahmin veya sonuç silinmez. Ertelenip başka tarihte oynanan maç,
bu sabit günlük ufukta puanlanmaz. Eksik oyuncu günlüğü DNP sayılmaz.

Availability için resmî NBA final boxscore veya ESPN'in açık tamamlanmış
boxscore kadrosundaki `didNotPlay` bilgisi gerekir. Bulut bunu indirir ve
yalnızca küçük kadro/etiket bilgisini saklar. Kadroda doğrulanamayan
oyuncunun oynama sonucu bilinmiyor kabul edilir; zorla sıfır yazılmaz.
Yerel `forecast` ağ erişimi yapmaz, mevcut etiket önbelleğini kullanır.

Haftalık gerçekleşen kategori puanları yalnızca Yahoo `postevent` durumu,
eşleşen takım slotları ve aynı hafta bitiş tarihiyle kaydedilir.
OAuth yoksa veya resmî final bilgisi gelmiyorsa sonuç bekler. Tarayıcıdan
doğrulanmış bir final dosyası da verilebilir:

```powershell
python -m src.prospective --weekly-final path/to/final.json
```

Dosyada `final: true`, `week`, `week_end`, `team_a`, `team_b` gerekir;
takımlarda `slot` ve 11 ham boxscore toplamı bulunmalıdır. Devam eden
hafta veya farklı rakip kabul edilmez. Sonuçlar `weekly_outcomes/` altında
tahminden ayrı saklanır. Bu bir add/drop nedensel etki deneyi değildir:
önerilen hamlenin uygulanıp uygulanmadığı ve uygulanmayan alternatifin
karşı-olgusal sonucu ayrıca izlenmeden “daha fazla kategori kazandırdı” denemez.

## Dakika değişikliği geçici kabulde

`config/prospective_protocol.json` geçici kabulü açıkça tanımlar.
“Yıldız” grubu tahmin anındaki tamamlanmış sezon önsel MPG'si >=25 olan
oyunculardır. Sonradan iyi oynayan oyuncuları bu gruba eklemeyiz.

En az 42 tamamlanmış maç tarihi ve 1.000 yıldız oyuncu-maç sonucu olmadan
kalıcı kabul incelemesi başlamaz. Ana ölçüt yıldız dakika MAE'sidir;
asgari göreli kazanç %0,25, haftalık eşli bootstrap %95 kazanç alt sınırı
sıfırın üzerinde ve sayma MAE bozulma toleransı %1 olarak sabitlenmiştir.
Günlük anlamlılık testiyle uygun gün seçilmez. Otomatik terfi/geri alma yoktur.

`reports/prospective_status.json` günlük tanısal özeti verir. Aynı oyuncu-maç
için tekrar koşular bağımsız örnek sayılmaz; aynı ufuktaki en erken kayıt
seçilir. Spillover kolu için o kolun mevcut olduğu en erken kayıt kullanılır.
İlk kayıtların gerçekleşeni henüz yoktur; sonuç uydurulmaz.

## Saklama ve otomasyon

Mevcut günlük bulut koşuları, önce `nba-fantasy-bot` dalındaki arşivi geri
yükler, sonra yeni tahmin ve etiketleri ekler. Kalıcılık ayrı bir çalışma
ağacında yapılır; kaynak çalışma ağacını temizlemek için `reset/clean`
kullanılmaz. Tam arşiv her koşuda Actions artifact'ine yeniden yüklenmez;
artifact yalnızca küçük güncel raporları 14 gün tutar. Asıl arşiv bot
dalında eklemeli Git dosyalarıdır.

Telegram özeti haftalık oynanan/toplam/kalan maçları, dokuz kategori
olasılığını, kadro uyarılarını ve altıya kadar alternatif hamleyi gösterir.
Hamlelerde puan beklentisinin önce/sonra değeri, gözlenen ve model dakikası,
sakatlık artışı varsayımı ve temel maç başı model istatistikleri yer alır.
`reports/telegram_preview.html` gönderim yapmadan görünümü gösterir.

Eski +2 düşük-rol artış sınırı `low_role_cap2` adıyla ayrı deney koludur;
ana modelde varsayılan olarak etkinleştirilmez. Fazla ve eksik dakika
tahmini ayrı izlenir; bu iki risk tek bir oyuncuya göre ayarlanmaz.

Kontrollü tuning'in seçtiği ama bütün belirsizlik denetimlerini geçemeyen
aday `rotation_candidate` adıyla ayrıca saklanır. `rotation_untuned`
sabit başlangıcı korur. Aynı tahminler tekrar çoğaltılmasın diye dosyada
`arm_aliases` bulunabilir; `read_record` bunları açar. Araştırma kolunda
ilk 10 gözlemin NLL ve aralık kapsamı da izlenir. Ana ayar kendiliğinden
araştırma adayına dönüşmez. Yıldız incelemesi rotasyon politikası sürümüne
göre ayrılır; farklı politikaların sonuçları tek bir sabit modelmiş gibi
terfi hesabına katılmaz.

Bulut bildirimi artık arşivlenen tek kanonik tahminden üretilir. Telegram
HTTP200 tek başına başarı sayılmaz: API `ok=true` ve `message_id`
döndürmelidir. Güvenli alındı kaydı `notifications/` altında tahmin dosyası
ve mesaj hash'leriyle tutulur; token/chat kimliği saklanmaz. Bildirim
başarısız olsa da arşiv kalıcılık adımı çalışır. Telegram'da saat Berlin
saatidir; bilimsel kesim ve arşiv zamanları UTC kalır.

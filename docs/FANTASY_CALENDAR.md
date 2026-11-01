# Ana modelde gerçek fantasy fikstürü

## 31 Ekim: 1/7 okuma hatasının gerçek sayfa üzerinden düzeltmesi

Canlı Chrome erişilebilirlik ağacında League sayfasındaki `#matchupweek`
alanının `Week 2 Matchups` başlığı ve yedi liste kartı doğrulandı. Her kartta
iki farklı `/nba/64691/{takim}` bağlantısı var; logo ve ad bağlantıları aynı
kimliği tekrarlayabiliyor. Hafta okları gerçek sayfada
`?matchup_week=3&module=matchups&lhst=matchups` biçiminde. Ayrıntı Matchup
sayfası bütün lig eşleşmelerinin kaynağı değildir; yalnız seçili çifti içerebilir.

Okuyucu artık doğrulanmış League hafta bağlantısını izler ve kartları takım
kimliğiyle tekilleştirir. Yedi çift/14 benzersiz takım ve yanıtın gerçek hafta
başlığı eşleşmeden kabul etmez. Dönem tarihleri ayrıca dated Matchup
bağlantılarından doğrulanır. Schedule sekmesinin açık olması gerekmez;
Schedule takım sayfalarını dolaşan ek istekler kaldırıldı. Eski kaynak yeterliyse
League isteği yapılmaz. Böylece tek haftada yedi takım sayfası taranmaz.

Eksik Schedule tablosu ve tek çift içeren ayrıntı sayfasıyla yapılan uçtan uca
sahte-yanıt regresyonu geçiyor; toplam 14 JavaScript testi geçti. Mevcut gerçek
sayfa yapısı incelendi, ancak canlı tam sezon yakalama/kalıcılık işlemi bu
düzeltme sırasında çalıştırılmadı. Eski kaydı tamamlanmış saymamak gerekir.

NBA maç takvimi ile Yahoo ligindeki hafta/rakip fikstürü ayrı veri kaynaklarıdır.
Bu değişiklik ikincisini ana tahmin akışına ve takas analizine ortak kaynak olarak
ekler. Kadroların güncel olması, gelecek fantasy eşleşmelerinin daha önce
kaydedildiği anlamına gelmez.

## Modelin kullandığı kapsam

Ana raporun `future_fixture_outlook` bölümü, varsayılan olarak mevcut haftadan
sonraki **bütün doğrulanmış tam normal sezon haftalarını** değerlendirir. Her
hafta yalnız o haftanın gerçek fantasy rakibine karşı, o tarihlerin NBA maçları,
günlük pozisyon sınırları ve mevcut oyuncu tahminleri kullanılır. Ölçüt yine
`Σ[P(kategori galibiyeti) + 0.5 × P(kategori beraberliği)]` olur. Raporda hafta
bazında rakip adı ve kategori puanı, toplam/haftalık ortalama ve kategori bazında
ortalama başarı görünür; ilk dört tam haftanın toplamı da JSON'da ayrı tutulur.

Örneğin 8. haftadan sonra karşılaşılmayacak bir fantasy takımı, 9. haftadan sezon
sonuna uzanan değerlendirmeye rakip olarak katılmaz. Bir takımla iki kere
oynanacaksa o iki hafta ayrı ayrı hesaplanır. Bununla birlikte o takımın NBA
oyuncuları başka oyuncuların NBA rotasyonunu etkileyebilir; fantasy rakibi
olmaması NBA düzeyindeki rol ilişkilerini silmez.

Mevcut haftanın kalan bölümü ve haftalık add/drop sıralaması ayrı kalır. Yeni
bölüm uzun vadeli kadro görünümüdür; günlük hamleleri kendiliğinden sezonluk
sıralamaya çevirmez. Gelecek kadrolar bugünkü halleriyle sabit tutulur, gelecekteki
FA/streaming tüketimleri sıfırmış gibi bir hamle planı üretilmez. Sakatlık/dönüş
ve rol beklentilerinin bilgi tarihi bugündür; gelecekteki haftanın başlangıcına
taşınmaz. Uzak haftalardaki sonuçlar bu varsayımlara koşulludur.

`config/league.json` içindeki `future_fixture_weeks`:

- `null`: Kalan tam normal sezon haftalarının tamamı (varsayılan).
- Pozitif sayı: Yalnız istenen sayıda gelecek tam hafta; rapor bunu sezonun tamamı
  olarak etiketlemez.

Playoff'a katılım olasılığı bu değişikliğe dahil değildir. Bunun için güncel
puan durumu ve beraberlik bozma kurallarıyla ayrı bir entegrasyon gerekir.
Henüz belli olmayan playoff rakipleri normal sezon fikstürüne eklenmez.

## Veri toplama ve doğrulama

Güncel tarayıcı köprüsü, mevcut kadro/skor senkronizasyonuna Yahoo'daki fikstür
sayfalarını da ekler. Sayfalarda bulunan takım schedule bağlantılarını ve hafta
seçimlerini izler. Sezon, hafta tarih aralığı, normal sezon bitişi ve 14 takımın
yedi eşleşmesi doğrulanabiliyorsa kaydeder. Tarih etiketlerindeki yıl geçişi
Yahoo'dan okunan sezona göre çözülür; bilgisayarın yılına göre tamamlanmaz.
İki haftalık bir Yahoo dönemi yedi güne kırpılmaz.

OAuth erişimi yapılandırıldığında bulut senkronizasyonu da Yahoo'nun
[belgelenmiş lig/haftalık scoreboard kaynaklarını](https://sports.yahoo.com/developer/docs/)
okur. Her eşleşmenin `week_start`/`week_end` tarihleri alınır; playoff başlangıcı
lig ayarlarından okunur. Güncel ve tam bir kayıt varsa gereksiz yeniden tarama
yapılmaz. Bu ortamda OAuth erişimi yapılandırılmış değildir.

Ortak kayıt `data/processed/league_state.json` içindeki `fantasy_calendar`
alanıdır. Yahoo takım numaraları, kaydedilmiş `yahoo_team_slots` üzerinden
kanonik kimliğe çevrilir; isim/draft benzerliğinden yeniden eşleştirilmez. Sezon,
lig ve kimlik eşlemesi kaydın parçasıdır. Her haftanın kendi `captured_at` zamanı
korunur. `fantasy_calendar_audit` yeni okumada kabul edilen haftaları ve hataları
gösterir.

Eksik/bozuk yakalama, önceki doğrulanmış haftayı silmez ve eski zamanı
yenilemez. Yedi günden eski haftalar yeni hesapta kullanılmaz. Arada eksik hafta
varsa yalnız kesintisiz doğrulanmış başlangıç bölümü hesaplanır ve kapsam eksik
olarak gösterilir; sonraki haftalara atlanıp tam sezon sonucu verilmez.
NBA takviminin kapsamadığı tarihlere de projeksiyon uzatılmaz. Fikstür yoksa
ligdeki bütün rakipler onun yerine geçirilmez. Güncel rakip de bilinmiyorsa ana
model artık sabit bir takım seçerek tahmin üretmez.

## Kullanım

Çalışan eski köprü süreci yeni Python kodunu otomatik yüklemez. Köprüyü yeniden
başlatın ve mevcut Yahoo bookmarklet'ini tekrar çalıştırın:

```powershell
.\.venv\Scripts\python.exe -m src.yahoo_browser_sync
```

Başarı bandında doğrulanmış fikstür haftası sayısı görünür. Sayı sıfırsa
`fantasy_calendar_audit.errors` nedenini gösterir; kadro/skorun başarıyla
yenilenmiş olması fikstürün de okunabildiğini kanıtlamaz. Yahoo HTML düzeni
canlı oturumda henüz doğrulanamadığından bu ilk gerçek yakalama ayrıca kontrol
edilmelidir. Sezon veya playoff sınırı açıkça okunamıyorsa tahmin edilmez.

Mevcut verilerle, bildirim göndermeden rapor üretmek:

```powershell
.\.venv\Scripts\python.exe -m src.forecast --no-recommendations
```

Takas girdisinde `weeks: []` bırakılırsa aynı ortak kaynak kullanılır.
`fixture_horizon_weeks` varsayılan dört tam haftadır; sezonda daha az hafta
kaldıysa tamamı alınır. İstenen ufuk eksikse analiz durur; bir haftalık veriyle
dört hafta varmış gibi sonuç verilmez. `--inspect` ortak takvim durumunu da
gösterir. Elle girilmiş `weeks` hâlâ desteklenir ve raporda `manual_input` olarak
ayrı belirtilir. Gelecek hamle tüketimleri takvimden türetilmez; streaming için
ilgili takım/hafta sayıları ayrıca gerekir.

## Doğrulama ve mevcut veri durumu

Son doğrulama: **75 Python testi + 5 JavaScript testi geçti**. Ruff kontrolü,
biçim kontrolü ve Python derleme kontrolü de geçti.

Tarih ve kaynak testleri; lig/takım kimliği uyuşmazlığı, yıl geçişi, iki haftalık
dönem, eksik/eski yakalama, playoff sınırı, ortak takvimin takas motorunda
kullanılması ve bilgi tarihinin sabit kalmasını kapsar. Kalan fikstürde hiç
oynanmayacak bir fantasy takımının kadrosunu değiştirmenin sonucu değiştirmediği
de doğrulanır. Tarayıcı kaydının dış işlem/bildirim olmadan kalıcılaştırılması
ayrıca test edilir.

30 Ekim 2026'da mevcut gerçek yerel kadrolarla ana rapor üretildi. Eski kayıt
gelecek fantasy fikstürü içermediği için yeni bölüm şu sonucu verdi:

```text
## Gelecek fantasy fikstürüne göre kategori görünümü

Hesaplanamadı: Yahoo future fantasy fixtures have not been captured.
```

Bu çıktı doğru eksik veri davranışıdır; gerçek gelecek eşleşmelerle tamamlanmış
bir sezon tahmini değildir. Canlı tarayıcı aracı mevcut URL'yi güvenle
doğrulayamadığından gerçek Yahoo fikstürü bu oturumda alınamadı. Yerel testler
canlı Yahoo HTML uyumluluğunun yerini tutmaz. Aşama 4'ün daha önce durdurulan
geniş taramasının performans sorunu da bu değişiklikle çözülmüş sayılmaz.

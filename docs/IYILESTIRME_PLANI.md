# NBAFantasy — son geliştirme ve doğrulama planı

Tarih: 28 Ekim 2026, Europe/Berlin.
Durum: **Yalnızca plan. Uygulama, deney veya tuning başlatılmadı.**
Başlangıç kod referansı: `0addcad`. Çalışmaya başlama komutunda kaynak,
ayar ve veri hash'leriyle gerçek başlangıç ayrıca sabitlenecek.

## 1. Amaç ve iki metodolojik açıklama

Normal sezon hedefi değişmez:

`U = sum[P(kategori kazanımı) + 0.5 * P(kategori beraberliği)]`.

Hamleler bu haftaki rakibe, kalan kullanılabilir maçlara ve günlük aktif
yerlere göre değerlendirilir. Yıldız oyuncu yetiştirmek veya yalnızca genel
oyuncu sıralamasını yükseltmek ayrı amaç yapılmaz. Haftalık W/L/D ikincildir.
Playoff amacı gerçek beraberlik/ilerleme kuralları bilindiğinde ayrı ele alınır.

**Farklı kadrolarla simülasyon gereklidir ve faydalıdır.** Aynı yöntemin
dengeli, kategori odaklı, sakatlık baskısı altındaki ve fikstürü sıkışık
kadrolarda ne kadar dayanıklı olduğunu gösterir. Aynı NBA maçlarını yeniden
kullanan 40 lig, 40 bağımsız NBA sezonu değildir. Bu nedenle senaryo sayısı
ve gerçek bağımsız zaman blokları ayrı raporlanır.

**2025–26 kullanılabilir.** Sonuçlarını daha önce incelemiş olmak sezonu
kullanmayı yasaklamaz. Ancak seçilmiş katsayılar, aday aileleri ve karar
kuralları o incelemelerden etkilenmiş olabilir. Bir sohbetin hafızasını
sıfırlamak bu etkiyi koddan veya tasarımdan kaldırmaz. Bu sezon geçmişe
dönük geliştirme/doğrulama kanıtı olarak kullanılır; gerçek yeni sınama,
ayarlar dondurulduktan sonra gelen sonuçlarla yapılır.

Üç deney birbirinden ayrılır:

| Deney | Gerçekleşen sonuç nereden gelir? | Cevapladığı soru |
|---|---|---|
| Oyuncu backtest'i | Gerçek geçmiş NBA maçları ve açık DNP etiketleri | Dakika, oynama ve üretim tahmini doğru mu? |
| Farklı lig/kadro senaryoları | Varsayımsal sahiplik + gerçek geçmiş NBA üretimi | Karar yöntemi farklı kadrolarda işe yarıyor mu? |
| Monte Carlo | Açıkça tanımlanan tahmin dağılımından örnekler | Olasılık hesabı ve senaryoya duyarlılık nasıl? |

Modelin kendi ürettiği sonuçlarda başarılı olması gerçek veriyle doğrulama
yerine geçmez. Yüksek varyans da tek başına kalıcı gelişme beklentisi değildir.

## 2. Önce veri ve zaman bütünlüğü

Bu aşama bitmeden yeni parametre seçimi yapılmaz.

- Önceki Eastern gününün skorunu bugünün fikstürüyle birleştirmeme ve
  pozitif Yahoo FA/waiver kanıtı isteme düzeltmeleri korunur.
- Kesin tipoff, maç kimliği ve durum bilgisiyle her maçın tahmin anında
  başlamamış / devam eden / bitmiş olma durumu ayrılır. Skorun hangi
  maçları kapsadığı ayrıca doğrulanır; yakalama saati tek başına kapsam
  kanıtı sayılmaz. Kısmi maç skoru üzerine aynı maçın tam beklentisi eklenmez.
- Kapsam doğrulanamıyorsa güvenli maç öncesi/ertesi gün modu kullanılır;
  tam canlı haftalık tahmin varmış gibi sunulmaz. Eski Yahoo skorunu NBA
  toplamlarıyla doldururken geçmiş aktif/bench tercihleri uydurulmaz.
- Yahoo takım/oyuncu kimlikleri kalıcı anahtar yapılır. Takım kimliği,
  başlangıç draft kadrosuna benzerlikten kalıcı olarak çıkarılmaz.
- Kadro, IL/IL+, skor, boşta oyuncu listesi ve işlemler uyumlu yakalama
  sürümleriyle saklanır. FA taraması eksikse yalnızca doğrulanan alt küme
  kullanılabilir; eksik kadrodan boşta oyuncu türetilmez.
- 13 aktif/bench kadro yeri + en fazla 2 gerçekten kullanılabilir IL yeri
  uygulanır. İki IL yeri, iki sağlıklı oyuncuya ek kadro hakkı değildir.
  Tahmini stash ile Yahoo'da gerçekten yapılmış stash ayrı tutulur.
- Tek hesaplama sonucu arşive, rapora ve Telegram'a gider. Kalan eski
  mükerrer hesaplar ancak sonuç eşitliği doğrulanarak kaldırılır.
- Hatalı geçmiş tahminler silinmez; kalite işaretiyle değerlendirmeden
  ayrılır. Yeni bir doğrulama raporunda geçerli örnek sayılmazlar.

Çıktı: veri sözleşmesi, kapsama/eksik veri tablosu ve Wembanyama/eksik
sahiplik/gün içi kısmi maç regresyon testleri. Kaynak dosyalar ve kullanıcının
güncel veri önbellekleri keyfî olarak sıfırlanmaz.

## 3. Karşılaştırma tabanı ve kronolojik deney düzeni

Başlangıçlar: mevcut motor, eski rol yöntemi, eldeki öğrenilmiş rotasyon
adayı ve gerekli basit yöntemler. Doğrulanmış FG/FT, beraberlik ve haftalık
ortak belirsizlik düzeltmeleri bütün adaylarda korunur.

Yerelde 2022–23, 2023–24, 2024–25 ve 2025–26 için normal sezon günlükleri
bulunuyor; her dosyada 1.230 farklı maç kimliği var. Bu, bütün kaynakların
kusursuz olduğu iddiası değildir; kapsam ilk aşamada ayrıca kontrol edilir.

| Dönem | Rolü | O dönem başındaki önsel |
|---|---|---|
| 2024–25 | Geliştirme ve ilerleyen zaman bloklarıyla aday seçimi | 2023–24; iki sezonlu adayda ayrıca 2022–23 |
| 2025–26 | Seçimi dondurulmuş adayın geçmişe dönük karşılaştırması | 2024–25; iki sezonlu adayda ayrıca 2023–24 |
| Plan sonrası yeni 2026–27 sonuçları | Önceden kaydedilen canlı doğrulama | Yalnızca tahmin kesiminde bilinen veri |

Tek sezon önseli de karşılaştırma adayıdır; iki sezonun oranları otomatik
olarak doğru kabul edilmez. 2024–25'in tamamı, aynı sezon içindeki erken
tarihli tahminlerin önseli yapılmaz.

Kurallar:

1. Her kesimde önce tahmin kaydedilir; hedef sonuç ancak gerçekleştikten
   sonra posterior güncellemesine katılır.
2. 2024–25 içinde erken bloklarda seçim, daha sonraki bloklarda değerlendirme
   yapılır. Sonraki bloğun sonucu önceki seçime geri taşınmaz. Haftalık
   hedeflerin sonuç penceresi kesimi aşıyorsa eğitimden çıkarılır.
3. Oyuncu satırları rastgele eğitim/test diye bölünmez. Takvim blokları,
   adaylar, ufuklar, seed'ler ve ölçütler çalıştırmadan önce manifeste yazılır.
4. Shrinkage/KAPPA, pozisyon havuzu, varyans ölçeği ve availability tabloları
   dahil bütün öğrenilen bileşenler aynı kesime uyar. Güncel kadro/pozisyon
   veya sezon sonu oyuncu sıralaması geçmişe taşınmaz.
5. 2025–26 başarısız olursa aynı sonuçlara bakıp ikinci adayı kazanan ilan
   etmeyiz. Yeni araştırma turu açılırsa açıkça yeni sürüm sayılır; önceki
   sonuç saklanır.

Çıktı: tekrar üretilebilir manifest, baseline raporu ve veri sızması testleri.
Yeni büyük PDF arşivi indirmek başlangıç gereksinimi değildir; mevcut
sıkıştırılmış sakatlık arşivi kullanılır.

## 4. Oyuncu modeli: sınırlı ve katmanlı tuning

Her katman ayrı değerlendirilir; yalnızca umut verenler küçük bir ortak
aday grubunda birleştirilir. Başlangıç araştırma bütçesi en fazla 24 tek
bileşen politikası ve 4 birleşik adaydır; bütçe sonuçlara göre gizlice
genişletilmez. Belirti göstermeyen modüllere yeni parametre eklenmez.

| Katman | Yapılacak iş | Temel ölçüm |
|---|---|---|
| Önsel/istatistik oranı | Mevcut politika, tek sezon ve az sayıda harman/güven adayı | Üretim hatası ve uygun olasılık skoru |
| Dakika/rol | Güncel rolü güçlü önselden ayırma; geçici seri ile rol kaybını yumuşatarak işleme | Oynanan maçlarda dakika MSE; MAE ve yanlılık korumaları |
| Sakatlıktan açılan fırsat | Mevcut dağıtım, öğrenilmiş aday ve dağıtım kapalı karşılaştırması | Dakika/üretim hatası; fırsatı fazla ve eksik tahmin maliyeti |
| Availability | OUT ve dönüş dahil, durum + tahmin ufku başına havuzlanmış kalibrasyon | Brier, log loss, kapsama ve sınıf yaygınlığı |
| Belirsizlik | Genel varyans ölçeğine karşı az sayıda, gözlem gücüne göre yumuşatılmış seçenek | Olasılık/aralık skoru, %80/%95 kapsam ve aralık genişliği |

Aynı gün öğlen Eastern, ertesi gün ve haftanın sonraki günleri ayrı
ufuklardır. Bir ufukta öğrenilen OUT olasılığı diğerine otomatik taşınmaz.
Eksik maç satırı DNP değildir; açık etiket yoksa sonuç bilinmiyor sayılır.
Oynama olasılığı ile oynadığı koşuldaki dakika birbirinden ayrılır; toplam
üretim değerlendirmesi doğrulanmış oynamama sonuçlarını da içerir.

Alt gruplar sonuçlara bakmadan sabitlenir: ilk 10 gözlem, önseli güçlü/rolü
düşük, 25+ önsel MPG, düşük dakika, takım değiştiren, sakatlıktan dönen ve
fırsat açılan oyuncular. Transfer/rol bilgisi ancak bilindiği tarihten
itibaren kullanılabilir. Vučević veya Wembanyama'ya özel istisna eklenmez.

Belirsizlikte yalnızca kapsamı yükseltmek amaç değildir. Mevcut normal
moment NLL kontrolü tam Bayesian üretici model doğrulaması diye sunulmaz.
Yeni skor için kullanılan tahmin dağılımı açıkça tanımlanır. Mevcut adayın
eski erken-sezon kontrolünden kalmış olduğu kaydı korunur; yeni kabul
protokolü eski sonuca geriye dönük başarı etiketi vermek için kullanılmaz.

Çıktı: hangi değişikliğin ne kazandırdığını gösteren ablation tablosu,
alt grup raporu ve dondurulmuş az sayıda birleşik aday.

## 5. Farklı kadrolarla dayanıklılık ve hamle backtest'i

Bu aşama planın zorunlu parçasıdır. İlk bütçe: seed'leri önceden kaydedilen
20 geliştirme ve 20 ayrı değerlendirme ligi. Ligler 14 takım içerir;
senaryo üreticisi takım profillerini dengeli, kategori odaklı, uzun/kısa
ağırlıklı, sakatlık baskısı altında ve fikstürü sıkışık olacak biçimde
çeşitlendirir. Oyuncu sahipliği lig içinde çakışmaz.

- Kadrolar ve oyuncu değerleri o tarihte bilinen önsellerden üretilir;
  gerçekleşmiş sıçramalar veya gelecek sakatlıklar seçim girdisi olmaz.
- 13 aktif/bench + uygunluk varsa en fazla 2 IL; günlük slotlar,
  pozisyonlar, waiver zamanı ve gerçek haftalık işlem sınırı uygulanır.
  Sırf 210 oyuncuya ulaşmak için sahte IL uygunluğu verilmez.
- Tarihsel Yahoo sahipliği/uygunluğu yoksa bu kısım açıkça varsayımsal
  lig olarak etiketlenir. Kesin Yahoo uygunluğu ile NBA G/F/C yaklaşımı
  birbirine karıştırılmaz.
- Öneriler sonuçlar görülmeden üretilir; haftanın gerçekleşeni gerçek NBA
  maçlarından gelir. Referanslar: hamle yapmama, basit fikstür odaklı
  streaming ve mevcut motor. Her karşılaştırma aynı bilgiye ve aynı
  işlem/aktif kadro sınırlarına sahip olur.
- Net katkı hesaplanır: alınanın kullanılabilen üretimi eksi bırakılanın
  kaybedilen kullanılabilir üretimi. Bench'e sığmayan maç skor getirmez.
- Rakip için standart ve matchup'a duyarlı aktif kadro politikaları ayrı
  sınanır. Daha zayıf varsayılan rakip yönetimi model başarısı sayılmaz.
- En fazla 25 oyunculuk kısa liste küçük örneklerde tüm doğrulanmış FA
  havuzuyla karşılaştırılır. Otomatik korunan oyuncular ve değiştirilebilir
  yerler açık olur; iyi hamlenin filtreden düşüp düşmediği ölçülür.
- Ana sonuç gerçekleşen kategori puanı ve referansa karşı net kazançtır.
  Haftalık W/L/D, en kötü senaryolar, kadro türü, sakatlık ve sezon bölümleri
  de raporlanır. Aynı NBA haftasını tekrar kullanan seed'ler bağımsız
  gözlemler sayılmaz; belirsizlik gerçek takvim bloklarından hesaplanır.

Değerlendirme seed'lerinde tuning yapılmaz. İlk etapta mevcut tek hamle
alternatiflerinin değeri sınanır; çok adımlı tüm hafta transfer planlayıcısı
ancak bu taban doğrulandıktan sonra ayrı geliştirme konusu olabilir.

Çıktı: kadro türleri ve haftalar boyunca dayanıklılık raporu; gerçek lig
sonucu ile varsayımsal lig sonucunun açık ayrımı.

## 6. Monte Carlo ve haftalık olasılık doğrulaması

Monte Carlo, önceki aşamadaki gerçek sonuçlu kadro deneyiyle aynı şey değildir.
Kategori olasılıklarının sayısal hesabını ve belirsizlik varsayımlarını sınar.

- Aynı oyuncunun farklı maçlarındaki ortak beceri belirsizliği korunur;
  her maç için bağımsız yeni beceri çekilmez. Oynama, dakika ve şut
  hacmi belirsizliği açıkça tanımlanır.
- Üreteç ile mevcut moment yaklaşımının beklenen değer ve varyansları
  karşılaştırılır. Yeni üreteç yapısal olarak farklıysa ayrı model adayıdır;
  mevcut modelin bağımsız gerçeklik kanıtı olarak kullanılamaz.
- FG/FT hacimleri, beraberlikler, TOV yönü ve mümkün istatistik ilişkileri
  kontrol edilir. Tam ortak üretici model kurmak, gerekli olduğu gösterilmeden
  bütün Bayesian çekirdeği yeniden yazma gerekçesi yapılmaz.
- Sabit 100 bin tekrar hedefi yerine sayısal hata izlenir: ilk hedef
  kategori olasılığında en fazla 0,25 yüzde puanı Monte Carlo standart
  hatasıdır. Gerekli tekrar sayısı buna göre belirlenir; bu gerçek veri
  belirsizliğiyle karıştırılmaz.
- Haftalık kategoriler gerçek finallerle skorlanır: kazanım/beraberlik/
  mağlubiyet için Brier veya çok sınıflı olasılık skoru, kalibrasyon ve
  beklenen kategori puanı hatası. %70 denilen tahminler benzer çok sayıda
  olayda değerlendirilir; tek hafta başarı/başarısızlık hükmü vermez.
- Kategori puanı beklentisi kategori bağımsızlığı istemez. Kategoriler
  arası bağımlılığın haftalık ikili galibiyet hesabına etkisi ayrı raporlanır.

## 7. Yeni canlı değerlendirme protokolü

Araştırma adayı için mevcut yıldız-rol protokolünden ayrı, sürümlü protokol
oluşturulur. 42 tarih / 1.000 yıldız gözlemi kuralı başka deneye otomatik
kopyalanmaz. Eski rol karşılaştırması kendi koşullarıyla devam eder.

Yeni adayın canlı puanlaması, aday ve protokol dondurulduktan sonraki ilk
uygun maç gününden başlar. Bu sınırdan önceki sonuçlar yeni adayın gerçek
görülmemiş doğrulaması sayılmaz. Şu alanlar önceden sabitlenir:

- Ana aday ve baseline sürümleri, ufuk, alt gruplar ve tekil örnek anahtarı.
- Ana ölçüt, pratik asgari kazanç ve kabul edilebilir zarar payları.
- Tarihsel blok varyansına göre hesaplanan örnek yeterliliği, tek planlı
  inceleme zamanı ve veri eksikse uygulanacak uzatma kuralı. Bu hesap adayın
  gelecekteki performansına bakılmadan tamamlanır.
- Aynı oyuncu-maç-ufkun ilk geçerli kaydı; aynı maçın tekrar koşuları yeni
  örnek değildir. Korelasyonlu haftalar/oyuncular dikkate alınır.
- Yalnızca %95 kapsam nokta tahminindeki çok küçük bir eşik aşımıyla karar
  vermek yerine, olasılık skoru, aralık genişliği, kapsam ve bunların örnekleme
  belirsizliği birlikte değerlendirilir. Kurallar baseline'a da uygulanır.

Tahmin, kesim, gerçek sonuç ve düzeltmeler ayrı kaydedilir. Hafta başı
tahmini ile hafta içi güncelleme karıştırılmaz. Haftalık final Yahoo
`postevent` veya doğrulanmış final kaydı gerektirir; tarayıcı senkronu tek
başına otomatik final garantisi sayılmaz.

Önerinin uygulanma zamanı, alınan/bırakılan oyuncu, aktif kullanım ve işlem
tüketimi ayrıca kaydedilir. Bu kayıtlar olmadan gerçek ligde önerinin net
katkısı tamamlanmış sayılmaz. Varsayımsal alternatifin sonucu, rakibin
tepkilerini bildiğimiz anlamına gelmez; nedensel kazanç iddiası sınırlı tutulur.

## 8. Ana modele geçiş, teslimatlar ve çalışma sırası

Kabul için veri sözleşmeleri ve matematiksel regresyonlar geçmeli; seçilen
ana ölçütte pratik kazanç ve blok belirsizlik hesabı desteklenmeli; önemli
gruplar ve zaman dönemleri korunmalı. Geçmişe dönük kadro dayanıklılığı ile
yeni canlı doğrulama ayrı gösterilmeli. Kanıt yetersizse mevcut ana ayar
korunur; aday izleme kolunda kalır. Sonuçlara bakarak eşik yumuşatılmaz veya
başarısız adayı geçirecek yeni alt grup seçilmez.

Başlama komutundan sonra sıra:

1. Veri/zaman/sahiplik sözleşmesi ve karşılaştırma manifesti.
2. Mevcut motorun tekrarlanabilir baseline ölçümü ve kronolojik altyapı.
3. Oyuncu katmanlarında sınırlı tuning ve birleşik aday seçimi.
4. Farklı kadrolarla gerçek sonuçlu dayanıklılık/hamle deneyi; gerekli
   Monte Carlo sayısal ve dağılımsal kontrolleri.
5. Tek adayın/protokolün dondurulması ve yeni canlı kayıtlarla sınama.
6. Kabul koşullarına göre ana modele geçiş veya mevcut ayarı koruma;
   açıklamaların ve raporların güncellenmesi.

Teslimatlar: manifest, baseline/aday/alt grup karşılaştırması, zaman kesimi
ve veri sızması denetimi, kadro dayanıklılığı tablosu, haftalık olasılık
kalibrasyonu, uygulanmış hamle net katkısı, açık kabul/ret/yetersiz veri
kararı. Yalnızca ortalama kazandıran ama kritik grupta bozulan değişiklik
"iyileştirilmiş sürüm" diye sunulmaz.

Bu plan hazırlanırken yalnızca mevcut kaynaklar, raporlar ve dosya kapsamı
incelendi. Model kodu/ayarları değiştirilmedi, deney veya simülasyon
çalıştırılmadı, bildirim gönderilmedi ve push yapılmadı.

Yöntem kaynakları:

- [Hyndman ve Athanasopoulos — zaman serilerinde çapraz doğrulama](https://otexts.com/fpp3/toolbox.html#time-series-cross-validation)
- [Cawley ve Talbot — model seçimindeki aşırı uyum ve değerlendirme yanlılığı](https://www.jmlr.org/papers/v11/cawley10a.html)

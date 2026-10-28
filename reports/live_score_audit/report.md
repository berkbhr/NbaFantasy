# BLK olasılığı ve Yahoo sahiplik denetimi — 28 Ekim 2026

## BLK: gerçekleşen skor farkı

Yerel tahmin arşivinde karşılaştırılan kayıtlar:
`20261028T123426057498Z` ve `20261028T131113634468Z`.
İlkinde BLK kazanma olasılığı %43,04, ikincisinde %5,08. Bunlar kullanıcının
ilettiği %47 ve %7 ile birebir aynı koşular değildir; aynı skor değişimini
taşıyan, erişilebilen zaman damgalı kayıtlardır. Eski tahminler değiştirilmedi.

| BLK | İlk kayıt | Güncel kayıt |
|---|---:|---:|
| Gerçekleşen: sen / rakip | 6 / 5 | 6 / 16 |
| Kalan beklenti: sen / rakip | 16,87 / 18,60 | 17,58 / 18,68 |
| Final beklentisi: sen / rakip | 22,87 / 23,60 | 23,58 / 34,68 |
| Farkın standart sapması | 7,01 | 7,08 |

Son skor farkı +1'den -10'a dönüyor: 11 blokluk değişim. Kalan beklentilerin
farkı ise -1,73'ten -1,10'a iyileşiyor. Dolayısıyla düşüş, yeni maçların
oyuncu becerisi önselini aşırı değiştirmesinden kaynaklanmıyor.

27 Ekim tarihli yerel NBA maç kayıtlarında rakibin ek 11 bloğu:
Victor Wembanyama 5, John Collins 3, OG Anunoby 2, Robert Williams III 1.
Senin aynı günkü beş oyuncu-maçının blok toplamı 0.
Bu, güncel Yahoo 6–16 toplamıyla tutarlı. Kadro içindeki geçmiş oyuncu
değişimleri tüm haftanın aktif kadroları yerine konmuş değildir; burada
eklenen günün skor farkı doğrulanmıştır.

Güncel kalan dağılım sabit tutulup yalnızca gerçekleşen skor değiştirildi:
6–5 için kazanma %46,65; 6–16 için %5,08. Hesapta tamsayı beraberliği için
yarım blok devamlılık düzeltmesi vardır. Tamamlanmış maçların skorları
sabit eklenir; onlar için tekrar gelecek maç varyansı eklenmez.
Bu örnekte büyük düşüş beklenen matematiksel davranıştır; olasılığı
yapay biçimde sınırlayacak bir katsayı eklenmedi.

`blk_comparison.json` sayısal tanıları içerir. Eski standart sapma, arşivde
varyans alanı bulunmadığı için kayıtlı Normal kategori olasılığından ters
hesaplandı; bağımsız bir eski-varyans doğrulaması değildir. Güncel 7,08281
standart sapması motorun varyansından doğrudan hesaplanarak doğrulandı.
Yeni raporlar bu ayrımı ve doğrudan hesaplanan standart sapmayı saklar.

## Alexander-Walker: sahiplik doğrulaması eksikti

Güncel `league_state.json` içinde Nickeil Alexander-Walker hiçbir takımın
listesinde görünmüyor, fakat `dropped_free_agents` listesinde bulunuyor.
Bu isim için açık bir bırakma işlemi bulunmuyor. Önceki kod, draft edildiği
takımda en az 13 oyuncu görünmesini bırakıldığına kanıt sayıyordu. IL/IL+
nedeniyle kadro 14–15 kişiye çıkabildiğinden bu çıkarım geçerli değildir.

Düzeltme oyuncuya özel değildir: tarayıcı ve bulut hattındaki bu çıkarım
ve keyfî olarak 13'e tamamlama kaldırıldı. Adaylar, güncel Yahoo boşta oyuncu
sayfalarında açık FA/waiver kanıtı bulunanlarla sınırlandı; bilinen sahiplik
her zaman üstün gelir. Eksik sayfalama sadece doğrulanmış alt kümeyi sağlar.
Eski bırakma işleminden sonra tekrar alınmış oyuncu da otomatik FA sayılmaz.

Mevcut eski senkronizasyon kaydında bu pozitif kanıt olmadığı için öneriler
yeniden senkronizasyona kadar bekletilir. Bu, oyuncunun gerçek sahibinin
hangi takım olduğunun yeni Yahoo verisi olmadan çözüldüğü iddiası değildir.
Kategori tahminleri çalışmaya devam eder; kartta önerilerin bekleme nedeni
açıkça gösterilir.

## Kontroller

- Gerçek JavaScript skor ayrıştırıcısıyla oyuncu tablosunu atlama, gerçek
  takım kimliğini ve 6/16 BLK sütunlarını koruma testi.
- Eksik/tutarsız maç sayısı veya yanlış takım kimliğini reddetme.
- Eksik kadrodan FA uydurmama; eski veya güvenilmeyen kanıtı reddetme;
  doğrulanmış listede olsa bile sahipli oyuncuyu dışlama.
- Kalan tahminler sabitken 11 gerçekleşen bloğun etkisi; tamamlanmış
  skorun varyansa eklenmemesi ve ham Yahoo maç sayısıyla tahminlerin
  tekrar çarpılmaması.

Bu denetim için canlı veri indirilmedi veya Telegram mesajı gönderilmedi.
Tam yerel test paketi: 93 test başarılı. Ruff kod ve biçim kontrolleri başarılı.
Yeni ağsız tahmin de çalıştırıldı: BLK %5,08 aynı kaldı, doğrulanmamış hamle
listesi boş ve kartta yeniden senkronizasyon nedeni görünür.

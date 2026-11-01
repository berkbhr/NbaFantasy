# Takas modülü geri bildirim incelemesi

## Güncel performans durumu — 31 Ekim 2026

**Gerçek fikstürlü geniş ölçüm tamamlandı:** 4 hafta / 40 paket / 3 nihai aday.
Arama **170.1706 saniye (2 dakika 50 saniye)**; yükleme **3.5183 saniye**;
birlikte yaklaşık **173.69 saniye (2 dakika 54 saniye)**. Hata listesi boş.
Bu kapsamda eski 15 dakika 47 saniyelik sonuçsuz koşu sorunu tekrarlanmadı.

| Aşama | Süre |
|---|---:|
| Hızlı aday üretme/kısa liste | 3.27 sn |
| 40 paketin ön elemesi | 111.85 sn |
| 3 nihai adayın ayrıntılı değerlendirmesi | 54.95 sn |

106.470 paket hızlı aşamada ele alındı; 40'ı tam ön elemeden geçti; 3'ünün
streaming durumu `planned` olarak tamamlandı. Bunlar onaylanmış üç fırsat
değildir: nihai adayların üçü de fırsat elemesini geçmedi. Hiçbir takas,
Yahoo isteği veya bildirim gönderilmedi; otomasyon bağlantısı açılmadı.

Veri kapsamı: yerel 14 kadro ve doğrulanmış Yahoo fikstürü. Kullanılan tam
haftalar **2–8, 9–15, 16–22, 23–29 Kasım 2026**; her birinde 7 eşleşme ve
14 benzersiz takım var. Kalan sezon kaydı 2–18. haftaları kapsıyor; 1. hafta
yok ve gelecek hesapta gerekmiyor. Performans senaryosunda gelecekteki hamle
tüketimi sıfır varsayıldı; piyasa snapshot'ı sağlanmadı. Bu bir takas tavsiyesi
veya gelecekteki her veri kümesi için süre garantisi değildir.

Komut:

```powershell
.\.venv\Scripts\python.exe -m src.trade_benchmark --weeks 4 --shortlist 40 --finalists 3 --max-seconds 600 --cache on --no-cprofile --output reports/trade_search/perf_real_4w40p.json
```

`--no-cprofile` deterministik çağrı profili ek yükünü kapatır; iç aşama duvar
süreleri yine ölçülür. Aynı anda başka bir benchmark/test yükü çalıştırılmadı.
JSON sonuç/girdi ve kaynak hashleri yerel `reports/trade_search/` altında.
Önceki sonuçsuz koşuda varsayımsal fantasy fikstürü kullanıldığından bu iki
geniş koşudan kontrollü bir hızlanma katsayısı hesaplanmaz.

Sonucu koruyan eşleşme/dağılım önbelleği, günlük takvim sorgularının yeniden
kullanılması ve streaming aday hazırlığı iyileştirildi. Aynı güncel kadro
sürümünde 1 hafta / 4 paket / 1 nihai aday profili **74.695 sn → 27.698 sn**
indi (**2.70 kat**). İş sonuçları, seçilen paketler ve streaming planları,
zaman/kaynak hashleri ile yeni tanısal sayaçlar çıkarılınca birebir aynıydı.

Bu koşuda fantasy eşleşmeleri ve gelecek hamle tüketimleri performans amaçlı
varsayımsaldı; gerçek lig fırsatı olarak kullanılamaz. Artefaktlar:
`reports/trade_search/perf_before_1w4p.json` ve
`reports/trade_search/perf_after_1w4p.json`.

İlk iyileştirme sonrasında başlatılan 4 hafta / 40 paket / 3 aday denemesi,
kullanıcı fikstürü yenilemek istediği için durdurulmuştu. Yukarıdaki tamamlanan
gerçek veri koşusu, sonraki pickle tabanlı önbellek ve kadro kopyalama
iyileştirmelerini de içerir. Aşağıdaki 15 dakika 47 saniyelik ölçüm tarihsel kayıttır.

30 Ekim 2026. Geri bildirim, kod ve üretilmiş sonuçlarla karşılaştırıldı.
Sayısal örnekler mevcut temsili testlerden gelir; gerçek takas tavsiyesi değildir.

## 1. Ön eleme +0.746, nihai +0.527

Bu fark hata değildir. Örnekte iki katılımcı takımda da **iki oyuncu** vardır;
12 veya 13 kişilik gerçek kadro kullanılmamıştır. Luke Kennard her iki yolda
da mevcut boş yere alınır. Raporda gizlenmiş oyuncu bırakma yoktur.

Yeniden hesaplanan kategori farkları:

| Kategori | FA'siz takas katkısı | İki kadro da FA kullanırken katkı |
|---|---:|---:|
| REB | +0.748345 | +0.527540 |
| PTS | -0.002586 | -0.000944 |
| Toplam | +0.745759 | +0.526597 |

Bu örnekte FA, takassız kadronun ribaund açığını azaltır; Garland'ın ek katkısı
küçülür. Streaming her durumda takas farkını azaltır genellemesi yapılmaz.
Üretim ve kazanma olasılığı arasındaki ilişki doğrusal değildir.

Rapor iyileştirildi: aktif/bench sayısı ve açık yer önce/sonra tablosu eklendi.
Drop yoksa “mevcut boş kadro yeri kullanılır”; varsa bırakılan oyuncunun gerçek
adı yazılır. Belirsiz “boş yer bırakılır/kullanılır” ifadesi kaldırıldı.

## 2. Karşı takımın açılan yerinin değerlendirilmesi

Bu gerçek bir eksikti. Önceden karşı taraf için bazı tek FA alternatifleri
hesaplanabilse de bu alternatifler Aşama 4'ün nihai karşı taraf kazancına
bağlanmıyordu. Bu, her 1'e 2 takasın kesin yanlış elendiğini kanıtlamaz;
fakat geçerli paketleri kaçırma riski yaratıyordu.

Düzeltme:

- Karşı tarafın takasla açılan yeri için bilinen FA/waiver ve hamle bütçesiyle
  tek FA tamamlama artık ön elemede ve nihai karşılaştırmada kullanılır.
- Karşı tarafın takassız kadrosu da aynı kullanılabilir havuzla yasal tek ekleme
  yapabilir. Olumsuz bir takası daha az olumsuz yapan FA da değerlendirilir;
  karşı tarafın en baştan pozitif kazanç üretmesi zorunlu tutulmaz.
- Seçilen iki kadro **birlikte yeniden projekte edilir**. Rakip bizim haftalık
  rakibimizse onun FA eklemesinin bize kaybettirdiği katkı da hesaba katılır.
- Bizim yönetim planlarında kullanılan FA'lar karşı tarafa aynı anda verilmez.
  Bu muhafazakâr rezervasyon, bütün ortak FA dağılımlarının optimumu değildir.
- Eksik FA veya gelecek hamle tüketimi sıfır varsayılmaz. Veri yetersizse
  `needs_data` / `replacement_data_required` gösterilir; boş koltuk üzerinden
  kesin ret ilan edilmez.

Karşı menajerin bütün sıralı streaming tercihlerini tahmin etmek hâlâ kapsam
dışıdır. Eklenen model, açılan yer için tek FA tamamlamasıdır.

## 3. Rank 120 + 130 karşılığında rank 25

Risk doğruydu; “balanced geçiyor” ifadesi doğru değildi. Eski rank modu tam
piyasa dengesi iddiası yerine `rank_screen_only` ve elle inceleme gösteriyordu.
Yine de yalnız ilk 20'ye uygulanan sert kontrol, verilen örneği kaçırabiliyordu.

Kontrol rank modunda genelleştirildi: paketlerin en iyi kaynaklı sıraları
arasındaki fark varsayılan 50 sınırını aşarsa, ilk 20 koşulu aranmadan uç
dengesizlik işaretlenir. Rank 120 + 130 → rank 25 regresyonu bunu doğrular.

Sıralar toplanmadı ve `exp(-0.025 × rank)` ile fiyat üretilmedi. Böyle bir eğri,
kanıt olmadan ordinal sıraya kardinal fiyat anlamı yükler. Genel fark kuralı da
yalnız yapılandırılmış kaba filtredir; paketin gerçek piyasa fiyatı değildir.
Tam değer kıyası için kaynaklı replacement-adjusted trade value gerekir.

## 4. FA'siz ön eleme ve 0.25 tolerans

Bu da gerçek bir kaçırma riskiydi. Salt takas kaybı -0.20 sınırının altında
kalan fakat tamamlayıcı FA ile yararlı olan paketler erken elenebiliyordu.

Yeni varsayılan `screen_with_fa="asymmetric"`: 2'ye 1 ve 1'e 2 paketlerde
gerçek, erişimi doğrulanmış tek FA hesabı eşik uygulanmadan önce yapılır.
Hızlı aşamada varsayılan bir FA adayı; nihai aşamada daha geniş aday bütçesi
kullanılır. Geçici ortalama/medyan oyuncu üretilip kadroya yazılmaz.

Eklenen regresyonda ham takas katkısı -0.20'nin altında olduğu hâlde doğrulanmış
tamamlama ile olumlu paket ön elemeden geçer. Açıkça `screen_with_fa=false`
seçilmesi desteklenir; bu durumda kaçırma riski bilinçli bir arama tercihidir.
Sınırlı aday havuzu ve kısa liste için global optimum garantisi yoktur.

## 5. Güncel 14 takımda süre denemesi

Kullanıcının yeni browser senkronu doğrulandı:

- Yakalama: **30 Ekim 2026, 21:35 Berlin** (20:35 UTC).
- 14 kadro, FA/waiver havuzu ve mevcut 1. hafta skoru aynı `sync_id` sürümünde.
- Benchmark bu güncel sürümü kullandı; eski kadroyla ölçüm yapılmadı.
- Mevcut kayıt gelecek dört haftanın gerçek fantasy eşleşmelerini içermiyor.
  NBA fikstürü ayrı olarak mevcut. Güncel kadro ile eksik gelecek rakip
  takvimi birbirinden farklı veri kapsamlarıdır.

Gerçek önbellek kadroları ve NBA takvimiyle CLI `--mode opportunities`
çalıştırıldı: dört hafta, 40 ön eleme paketi, en fazla üç nihai streaming
paketi. Gelecek fantasy eşleşmeleri ve her takımın gelecek haftalarda sıfır
hamle tüketimi **yalnız performans denemesi için varsayımsal** kuruldu; gerçek
lig fırsatı olarak sunulmadı. Piyasa snapshot'ı sağlanmadı.

Çalışma, **yaklaşık 15 dakika 47 saniye sonra sonuç üretmeden elle durduruldu**.
Bu nedenle tamamlanmış `timings`, nihai paket sayısı veya üç gerçek fırsat
raporlanamaz. Son gözlemde süreç CPU kullanıyordu; bu bir ağ beklemesi olarak
teşhis edilmedi. Yaklaşık süre başlangıç/son gözlemden ölçülür; alt aşama
süreleri elde edilmediği için hangi alt aşamanın baskın olduğu iddia edilmez.

Tekrar üretim girdisi ve gözlem (yerel, Git dışında):

- `reports/trade_search/review_benchmark_input.json`
- `reports/trade_search/review_benchmark_observation.json`

Küçük temsili örnekten 2–3 dakika tahmini yapmak güvenilir çıkmadı. “Yerel
kullanım ve otomasyon için tamamen hazır” sonucunu bu ölçümle desteklemiyorum.
Tek teklif analizi çalışıyor; geniş aramayı Aşama 5 otomasyonuna bağlamadan
önce alt aşama profili, zorunlu bırakma/FA referanslarının maliyeti ve arama
bütçeleri ayrıca iyileştirilmelidir. Otomasyon veya bildirim akışı açılmadı.

## Doğrulama

**56 test geçti.** Yeni altı regresyon; açık kadronun raporlanmasını, ortak
karşı taraf tamamlamasını, eksik bütçe belirsizliğini, aynı FA'nın iki takıma
atanmamasını, rank 25 sınırını ve negatif ham takasın FA ile kurtulmasını
kapsar. Lint, biçim ve derleme kontrolleri de geçti.

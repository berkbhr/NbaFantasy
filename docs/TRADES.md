# Yerel takas analizi — Aşama 0–5

## Aşama 5: Yahoo teklifleri, rapor akışı ve playoff etkisi

Ana raporda varsayılan politika **yalnız güncel bekleyen gerçek tekliflerdir**.
`src.trade_automation` doğrulanmış Yahoo teklif snapshot'ını kontrol eder;
başarısız okumayı “teklif yok” saymaz. Kadro kimliği/sürümü, sahiplik, gerçek
fikstür, sakatlık/model verisi ve analiz ayarları değiştiğinde hesap yenilenir.
Aynı girdili teklifler kalıcı önbellekten okunur. Yeni teklifler için varsayılan
çalıştırma bütçesi üç teklif ve 90 saniyedir; kalanı ertelenir. Değerlendirme
ana tahmin arşivlenmeden önce eklenir; sonradan gösterilen eski geçerli haftalık
tahmin, güncel teklif bölümünün yerine geçirilmez.

OAuth varsa Yahoo'nun pending-trade ve standings GET kaynakları kullanılır.
Tarayıcı yolu mevcut League okumasından tamamlanmış kategori W/L/T kayıtlarını
yeniden kullanır; bekleyen teklif bağlantısı bulunursa yalnız bir teklif sayfası
okur. Kimlik/durum kanıtı bulunamayan HTML'de boş teklif listesi üretilmez.
Yahoo'ya teklif gönderme, kabul/ret veya iptal işlemi uygulanmaz.

Varsayılan teklif hesabı sıradaki dört tam haftayı kullanır. Yahoo yürürlük
tarihi vermezse **ilk tam gelecek haftanın başlangıcı için koşullu senaryo**
kurulur; bu bir işlem tarihi tahmini değildir. `effective_date_policy` değeri
`provider_only` yapılırsa eksik tarihte hesap bekletilir. Gelecek hamle tüketimi
benchmark'taki gibi sıfır varsayılmaz. Varsayılan gerçek teklif izleme,
streaming'i kapalı tutar; FA tamamlaması ancak doğrulanmış hak/tarih bilgisiyle
hesaplanır. Ayrıntılar ve yaklaşık pozisyon/rol koşulları raporda korunur.

Playoff etkisi tamamlanmış gerçek kategori W/L/T kayıtları, **mevcut haftanın
tüm 14 takım için ham skorları** ve kalan sezonun bütün gerçek eşleşmelerini
ister. Mevcut hafta atlanmaz veya iki kere sayılmaz; gözlenen skorlar sabit
tutulup kalan maçlar projekte edilir. Bilgi tarihi bugündür. Saf takasın sabit
kadro etkisi, takassız senaryoyla ortak rastgele sayılarla karşılaştırılır;
olasılık farkı ve Monte Carlo standart hatası raporlanır. İki sakatlık yayılımı
senaryosu ayrı tutulur. Streaming planı bütün sezona uzatılmaz. Kesin beraberlik
bozma kuralı yoksa eşitlik yaklaşımı açıkça belirtilir. Eksik/güncelliğini
yitirmiş skor, puan durumu, fikstür veya maç öncesi kapsama koşulunda
`needs_data` döner; gerçek playoff yüzdesi uydurulmaz.

### Çalıştırma ve periyot

```powershell
Copy-Item config/trade_automation.template.json config/trade_automation.json
.\.venv\Scripts\python.exe -m src.trade_automation --mode pending
```

`config/trade_automation.json` isteğe bağlı yerel ayardır; yoksa güvenli
varsayılanlar kullanılır. Yeni Yahoo alanlarını almak için güncel köprüyle
senkronizasyon gerekir. OAuth olmayan ortamda rapor döngüsü Yahoo sekmesini
kendiliğinden açmaz; son doğrulanmış browser kaydını kullanır. Gerçek bekleyen
teklif HTML'i ilk kez yakalandığında kimlik eşlemesi ayrıca doğrulanmalıdır.

Geniş fırsat taraması **her ana raporda çalışmaz**. Varsayılan periyot `off`.
İsteğe bağlı günlük/haftalık çalıştırma için GitHub repo değişkeni
`TRADE_SCAN_CADENCE=daily` veya `weekly` seçilir; mevcut sabah 06:30 UTC
tetiklemesinde dönem kontrolü yapılır. Tamamlanma kaydı Berlin takvim günü /
ISO haftası üzerinden tutulur; geciken bir önceki koşu ertesi günü atlatmaz.
Manuel Actions çalıştırmasında `trade_scan=true` veya aşağıdaki komut tek
seferlik geniş taramayı açar. Sonuç ayrı rapor artefaktıdır; ek otomatik mesaj
göndermez. Gelecek hamle hakları bilinmiyorsa streaming katkısı varsayılmaz.

```powershell
.\.venv\Scripts\python.exe -m src.trade_automation --mode opportunities --force
```

Mevcut workflow üç değil **dört UTC cron** içeriyor: 06:30, 12:30, 18:30,
23:15. Bu zamanlar değiştirilmedi. Her raporda pending-only politika geçerli;
geniş tarama yalnız açıkça etkinleştirilmiş ayrı adımda çalışır. Bu geliştirmede
canlı bildirim, trade işlemi veya GitHub workflow tetiklemesi yapılmadı.

### Performans ölçümündeki üç aday neden elendi?

`perf_real_4w40p.json` sonuçları, dört haftalık toplam kategori puanı farkıdır.
Bizim alt eşiğimiz `+0.200`, karşı taraf için izin verilen en düşük fark
`−0.200` idi. Her iki rol/sakatlık yayılımı senaryosunun daha kötüsü kullanıldı.

| Verilen | Alınan | Bizim muhafazakâr Δ | Karşı taraf normal Δ | Karşı taraf muhafazakâr Δ | Eleme |
|---|---|---:|---:|---:|---|
| Precious Achiuwa | Tyler Herro | +1.086 | −0.911 | −0.911 | Karşı taraf kaybı −0.200 sınırından kötü |
| Jarrett Allen + Precious Achiuwa | LeBron James + Tyler Herro | +0.839 | −0.491 | −1.174 | Karşı taraf kaybı −0.200 sınırından kötü |
| Jarrett Allen + Precious Achiuwa | Duncan Robinson + Austin Reaves | +0.786 | −0.682 | −0.913 | Karşı taraf kaybı −0.200 sınırından kötü |

Bizim üç kazancımız da alt eşiği geçti. Ayrı bir “senaryo farkı” kesme eşiği
yoktu; fark yalnız muhafazakâr kazancı belirledi. Kaynakta piyasa snapshot'ı
yoktu ve gelecek hamle tüketimi yalnız benchmark amacıyla sıfır varsayılmıştı;
bu tablo gerçek teklif önerisi değildir. 106.470 hızlı adaydan 40 ayrıntılı
paket, bunlardan üç nihai aday değerlendirilmiştir; global optimum iddiası yok.

Ölçüm dosyasındaki aynı görünen takım adları, eski okuyucunun lig başlığını
takım adı olarak kaydetmesinden kaynaklanıyordu. Yeni okuyucu takım kartı adını
önceliklendirir; tekrarlanan genel lig etiketleri raporda gerçek kanonik adların
üstüne yazılmaz. Eski ölçüm dosyası sonradan değiştirilmedi.

30 Ekim geri bildirim incelemesi: [kanıtlar, düzeltmeler ve büyük tarama ölçümü](TRADE_REVIEW.md).
Fikstür entegrasyonu dahil güncel doğrulama: 75 Python + 5 JavaScript testi geçti.
Güncel 14 kadroyla dört haftalık / 40 paketlik
eski performans denemesi yaklaşık 15 dakika 47 saniye sonunda sonuç üretmeden
durdurulmuştu. Son gerçek fikstürlü 4 hafta / 40 paket / 3 nihai aday koşusu
170.17 saniyede hatasız tamamlandı; yükleme dahil 173.69 saniye.
Ölçüm kapsamı ve varsayımlar `TRADE_REVIEW.md` içinde kayıtlıdır.

Bu bağımsız komut, güncel yerel Yahoo kadrolarıyla elle girilen 1'e 1,
2'ye 2, 2'ye 1 ve 1'e 2 teklifleri değerlendirir. Zorunlu bırakmaları, açık
IL yerleşimini, anlamlı FA tamamlama alternatiflerini ve isteğe bağlı tarihli
streaming planlarını hesaplar. Aşama 4, aynı bağlamda fırsat taraması,
kaynaklı piyasa kontrolü ve mevcut teklife yakın karşı teklifler üretir.
Ağ isteği, Yahoo işlemi veya bildirim yoktur.
Ana tahminle ortak gerçek fantasy fikstürü kaynağı eklendi:
[ana model entegrasyonu ve ilk veri yakalama](FANTASY_CALENDAR.md).
Playoff'a katılım etkisi Aşama 5'te yukarıda belirtilen veri koşullarıyla eklendi.

## Kullanım

Önce mevcut kanonik takım kimliklerini, Yahoo oyuncu kimliklerini ve kadro
`sync_id` değerini görün. Bu kimlikler Yahoo takım numarası/draft sırası değildir:

```powershell
.\.venv\Scripts\python.exe -m src.trades --inspect
Copy-Item config/trade.template.json config/trade.local.json
```

Şablonu gerçek teklif ve lig bilgileriyle doldurun, sonra:

```powershell
.\.venv\Scripts\python.exe -m src.trades config/trade.local.json --output reports/trades
```

Teklifin iki oyuncu listesi Yahoo oyuncu kimliklerini kullanır. `snapshot_id`
güncel kadro sürümüyle eşleşmelidir; kadro yenilenince teklif tekrar doğrulanır.
`effective_date`, inceleme süresi bittikten sonraki gerçek yürürlük günüdür.
Varsayılan kadro yapısı 10 aktif yer + toplam 13 aktif/bench + 2 IL'dir.
Farklı yapı bu sürümde reddedilir. `rules.verified=true` yalnızca bütün alanlar
gerçek ligden doğrulanınca kullanılmalıdır; inceleme süresi için sıfır da açık
bir değerdir. Son tarih yoksa `trade_deadline=null` kalabilir.

`weeks: []` bırakıldığında ana modelin ortak Yahoo fikstürü kullanılır;
`fixture_horizon_weeks` varsayılan dört tam haftadır. Ortak kayıt yoksa veya
istenen ufuk eksikse analiz durur. `--inspect` takvim durumunu da gösterir.

Elle sağlanan `weeks`, ardışık tam gelecek fantasy haftalarının gerçek başlangıç/bitiş
tarihlerini ve **14 takımın tamamının** eşleşmelerini içerir. Her takım her
haftada bir kez yer almalıdır. Her öğenin biçimi:

```json
{
  "start": "YYYY-MM-DD",
  "end": "YYYY-MM-DD",
  "fixtures": [["kanonik_ev_takimi", "kanonik_deplasman_takimi"]]
}
```

`fixtures` listesine o haftanın yedi gerçek eşleşmesi girilir. Tarihler ve
rakipler uydurulmaz. `calendar_verified` gerçek takvim kontrol edilince true
yapılır. `regular_season_end`, gerçek son normal sezon haftasının bitişidir.
Girdi gelecek haftadan sezon sonuna kadar tüm haftaları kapsamıyorsa sonuç
yalnız sağlanan haftalar için etiketlenir. Mevcut haftanın kalan bölümü bu
kapsam etiketine dahil değildir.

`eligible_positions`, Yahoo kimliğinden **tüm uygun pozisyonlara** eşlemedir:
örneğin `"oyuncu_kimligi": ["PG", "SG"]`. Seçili BN/UTIL yeri uygunluk
değildir. Tam uygunluk girilmezse NBA pozisyonlarıyla yaklaşık analiz yapılır;
rapor bunu koşul olarak belirtir. `do_not_trade_yahoo_ids`, add/drop
korumasından bağımsız takas yasaklarıdır.

İsteğe bağlı `playoff_periods` öğeleri `start` ve `end` alanları taşır.
Gerçek fantasy playoff tarihleri verilirse takastaki oyuncuların tur bazında
ham NBA maç sayıları gösterilir. Bu, aktif kadroya sığan maç sayısı veya
playoff'a katılma ihtimali değildir.

## Hesap ve sonuç

Her hafta gerçek rakibe karşı aynı politika altında önce/sonra günlük kadrolar
seçilir. Karşı taraf bizim rakibimizse iki değişen kadro birlikte hesaplanır.
Normal sezon hedefi beklenen kategori galibiyeti + yarım beraberliktir.
Kategori olasılıkları, üretim, haftalık W/L/T ve günlük seçimler JSON'da;
iki tarafın kategori kazanç/kayıpları Markdown raporda saklanır.

İlk dört sağlanan hafta ve tüm sağlanan haftalar ayrı özetlenir. Dört eşit
maçlık paket üretimi ayrıca gösterilir; bu yardımcı görünüm günlük kadro
kısıtlarını içermez ve takım kazanma ihtimali olarak yorumlanmaz.
FG/FT için isabet ve deneme toplamları ayrı tutulur.

Sakatlık dakika dağıtımı açık/kapalı senaryolar kendi takassız referanslarıyla
karşılaştırılır. İşareti değişen veya ufuklar arasında çelişen fayda inceleme/
karşı teklif olarak işaretlenir. Olumlu tahminler koşullu kabul olarak sunulur;
kalibre edilmiş kabul eşiği veya menajer kabul yüzdesi iddiası yoktur.
Kaynak dosya hash'leri, teklif hash'i, veri anı ve kadro sürümü kaydedilir.

## Sınırlar ve sonraki işler

- Kısmi/canlı hafta ve hafta ortasında yürürlüğe giren takas, geçmiş skorun
  yanlış aktarılmasını önlemek için henüz desteklenmez. Yürürlük tarihi ilk
  analiz haftasının başlangıcından geç olamaz. Gelecek haftalar ayrı çalışır.
- Piyasa snapshot'ı kullanıcı tarafından sağlanır; otomatik Yahoo teklif/piyasa
  aktarımı henüz yoktur. Arama sonucu otomatik takas göndermez veya kabul etmez.
  Aşama 2 FA önerileri tek ekleme alternatifleridir; Aşama 3'ün ayrı streaming
  bölümünde ise sıralı hamleler aynı kadro ve bütçe üzerinde hesaplanır.
- Güncel önbellek tarihsel replay değildir. Oyuncu rolleri ileriye sabit bilgi
  anıyla taşınır; uzun vadeli sonuçlar koşulludur. Takım bazında yakalama
  zamanları mevcut kaynakta eksiktir; tek güncel tarih tüm kadroların aynı
  anda doğrulandığını kanıtlamaz. Rapor bunu belirtir.
- Ana modelin gelecek eşleşme entegrasyonu ve playoff katılım entegrasyonu
  kullanıcı kararı doğrultusunda bu değişikliğin dışındadır.

Doğrulama:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_trades.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_streaming.py -v
.\.venv\Scripts\python.exe -m ruff check src tests/test_trades.py tests/test_streaming.py
```

## Aşama 2: farklı büyüklükte paketler ve boşalan kadro yeri

Verilen/alınan listelerindeki bir veya iki oyuncu aynı komutla değerlendirilir.
İşlem sonrası 13 aktif/bench kapasitesi iki takımda da uygulanır. Yer açması
gereken takım için izinli tek oyuncu bırakma seçenekleri tam motorla karşılaştırılır;
seçim o takımın kendi kategori katkısına göre yapılır. Bırakmanın maliyeti
saf takas sonucuna dahildir. JSON `drop_alternatives` bütün değerlendirilen
seçenekleri saklar; Markdown seçilen oyuncuyu gerçek adıyla gösterir.

`drop_yahoo_ids` ile takım bazında zorunlu bırakmayı kendiniz belirleyebilirsiniz:
`{"kanonik_takim": ["oyuncu_yahoo_kimligi"]}`. Yalnızca gereken sayıda oyuncu
bırakılabilir. İki takımın da otomatik bırakma seçimine ihtiyacı varsa en az
bir tarafın seçimi açık girilmelidir. Birden fazla zorunlu bırakma da açık girdi
ister. `do_not_drop_yahoo_ids` ve mevcut lig ayarlarındaki açık oyuncu korumaları
aşılmaz; add/drop motorunun otomatik ilk 11 koruması bu aramada uygulanmaz.

IL oyuncusu takas edilirse **iki taraf için de** `post_trade_il_yahoo_ids`
girilir: örneğin `{"7": [], "0": ["aliciya_giden_il_oyuncusunun_yahoo_kimligi"]}`.
Listeler işlem sonrası tam IL yerleşimidir. Yeni yerleşim için güncel Yahoo
kaydında pozitif IL uygunluğu gerekir; mevcut kaynakta yalnız gerçekten
IL/IL+ yerinde bulunan oyuncular bu kanıtı sağlar. Aktif bir oyuncunun yalnız
OUT görünmesi ek IL hakkı yaratmaz. İki yer sınırı aşılmaz. Model açık yerleşimi
analiz boyunca korur; dönüş günü otomatik IL aktivasyonu/yeniden yer açma henüz yoktur.

FA tamamlama yalnız işlemle yeni aktif/bench boşluğu oluşan takım için açılır.
Başka oyuncu bırakmadan, bir doğrulanmış adayın eklenip analiz sonuna kadar
elde tutulması hesaplanır. Takassız referans aynı FA kısa listesinden bir
ekleme yapabilir; doluysa izinli oyuncularından birini bırakabilir. Böylece
zaten yapılabilecek eklemenin katkısı takasa yazılmaz. Referans hiç hamle
yapmamayı da seçebilir. Gerekli bırakmalar ve her iki tarafın değişen kadrosu
bütün karşılaştırmalarda korunur.

`completion` ayarları:

- `enabled`: Varsayılan true. Eksik FA kanıtı saf takas analizini engellemez.
- `candidate_limit`: Varsayılan 8, 1–25 arası. Hızlı üretim/fikstür puanıyla
  kısa liste oluşturulur, sonuç tam motorla değerlendirilir. Global en iyi
  FA garantisi yoktur; incelenen aday sayıları JSON'da saklanır.
- `min_gain_per_week`: Varsayılan 0.05 beklenen kategori puanı. Hem saf takasa
  ek katkı hem adil takassız referansa göre kazanç, sakatlık dakika dağıtımı
  açık/kapalı karşılaştırmalarında bu eşiği aşmalıdır. Bu bir kullanıcı
  politikasıdır, öğrenilmiş istatistiksel anlamlılık eşiği değildir.
- `adds_used_by_week`: Eklemenin yapılacağı **gelecek haftanın** başlangıç
  tarihinden takım/harcanmış hamle sayısına eşleme. Örnek biçim:
  `{"2026-11-02": {"7": 0}}`. Bu örnekteki sıfırı gerçek planlanan tüketimle
  değiştirin. Bilinmeyen sayıya sıfır atanmaz; mevcut haftanın kullanımı gelecek
  haftaya taşınmaz. İlgili hafta/takım eksikse FA önerisi verilmez.

`rules.max_weekly_adds` ligdeki gerçek limittir; yoksa mevcut lig ayarından
alınır. `rules.trade_add_cost`, takasın ilgili ekleme haftasında tükettiği
ekleme hakkıdır (varsayılan 0; gerçek kuralla doğrulayın). Karşılaştırma aynı
tek ekleme bütçesini kullanır; çok günlük streaming Aşama 3'e aittir.

FA kanıtı aynı `sync_id` ile, en fazla 24 saat önce Yahoo boşta oyuncu
sayfasından yakalanmış olmalıdır. Eksik taramada yalnız doğrulanan alt küme
kullanılır; yeni bırakılan oyuncular havuza kendiliğinden eklenmez. W için
bilinen açılma tarihi gerekir; FA görünse bile kayıtlı bekleyen waiver
kısıtı korunur. Katkı açılma/ekleme gününden önce başlamaz. Takassız referansın
bıraktığı oyuncu o güne kadarki maçlarını korur. İleri tarihteki erişim ve claim
başarısı garanti değildir; işlem günü tekrar doğrulanmalıdır.

Anlamlı seçenek bulunursa kararın referansı `trade_plus_fa` olarak işaretlenir;
hangi oyuncunun alınması gerektiği, saf takasa ek katkı ve aynı FA havuzuyla
yönetilen takassız kadroya göre katkı ayrı gösterilir. Saf takas tabloları
ayrıca korunur. Birden çok FA seçeneği veya iki takımın seçenekleri alternatif
senaryolardır; aynı FA iki takıma birlikte atanmaz.

## Aşama 3: tarihli streaming ve haftalık hamle bütçesi

`streaming.enabled=true`, teklifin `our_team` alanındaki takım için takassız
ve takaslı kadrolarda iki bağımsız plan üretir. Diğer takımların kadroları
zorunlu takas düzenlemelerinden sonra sabit tutulur; günlük aktif oyuncuları
mevcut motor politikasıyla seçilir. Karşı menajerlerin gelecekte yapacağı
ekleme/bırakmalar tahmin edilmez. Ayar hiç yoksa streaming kapalıdır; güncel
şablonda açık olarak bulunur. Ana günlük tahmin, bulut senkronizasyonu ve
bildirim akışlarına bağlantı eklenmemiştir.

Plan, oyuncuyu alıp birkaç gün sonra başka oyuncuyla değiştirebilir. Takvim
günü başına en fazla bir atomik ekleme/bırakma yapılır. Her adımda oyuncu
sahipliği, 13 aktif/bench kapasitesi, açık bırakma korumaları ve IL yerleşimi
kontrol edilir. Bırakılan oyuncunun önceki günlerde kazandığı katkı korunur;
yeni oyuncunun katkısı ekleme/waiver açılma gününden önce başlamaz. Analiz
boyunca bırakılan oyuncu tekrar alınamaz; yeni bırakılan oyuncu da kendiliğinden
FA havuzuna girmez. Bu sürüm sabit IL yerleşimini korur; dönüş gününde otomatik
IL aktivasyonu veya yeniden yer açma planlamaz.

Hafta değiştiğinde kadro taşınır, yeni haftanın hamle bütçesine geçilir. Hafta
sınırları `weeks` girdisindeki gerçek fantasy haftalarından alınır; takvimde
her pazartesi otomatik sıfırlama yapılmaz. `streaming.adds_used_by_week`, her
hafta başlangıcı için takımın plan dışındaki tüketimini açıkça belirtir:

```json
{
  "streaming": {
    "enabled": true,
    "candidate_limit": 8,
    "beam_width": 6,
    "finalists": 6,
    "min_gain_per_week": 0.05,
    "adds_used_by_week": {
      "2026-11-02": {"7": 0},
      "2026-11-09": {"7": 1}
    }
  }
}
```

Bu tarih ve sayılar biçim örneğidir; gerçek fikstür ve planlanan tüketimle
değiştirilmelidir. Eksik hafta/takım tüketimi sıfır sayılmaz: o hafta yeni
ekleme yapılmaz, mevcut kadroyla devam edilir. Limit `rules.max_weekly_adds`
veya mevcut lig ayarından gelir. `trade_add_cost`, yalnız takaslı planda ve
takasın gerçek yürürlük gününü içeren fantasy haftasında tüketilir. Takas
analiz penceresinden önceyse maliyeti sonraki haftaya taşınmaz. Takassız
referans takas maliyeti ödemez. Streaming açıkken Aşama 2 tamamlamaları da
streaming için verilen haftalık tüketim bilgisiyle değerlendirilir.

İki plan aynı doğrulanmış FA havuzunu, koruma kurallarını ve arama sınırlarını
kullanır. FA kanıtı aynı kadro `sync_id` değerinde ve en fazla 24 saatlik
olmalıdır. W için bilinen açılma tarihi gerekir; FA görünse bile bekleyen
waiver kısıtı korunur. Eksik taramada yalnız doğrulanan alt küme kullanılır.
Gelecekte oyuncunun hâlâ boşta olması veya claim'in başarılı olması koşulludur;
her hamleden önce yeniden doğrulama gerekir. Komut Yahoo'da işlem yapmaz.

Arama, her gün gerçek maç programı ve pozisyon kısıtlarıyla seçilen kadronun
hızlı katkı puanını kullanarak sınırlı sayıda olası geçmişi tutar. Varsayılan
`candidate_limit=8`, `beam_width=6` ve `finalists=6` değerleri arama bütçesidir;
global optimum garantisi vermez. Geçerli Aşama 2 tek ekleme alternatifleri
de korunan başlangıç adayları olabilir. Son kadrosu aynı olsa bile farklı
geçmiş üretime sahip planlar birleştirilmez. Hamlesiz plan her zaman ayrıca
korunur.

Son adaylar mevcut tam haftalık kategori motoruyla, sakatlık dakika dağıtımı
açık ve kapalı olarak yeniden değerlendirilir. Günlük varyanslar toplanarak
yeni bir haftalık belirsizlik hesabı kurulmaz; aynı oyuncunun hafta içindeki
maçları mevcut ortak belirsizlik hesabından geçer. Hamlesiz duruma göre
temkinli iyileşme, `min_gain_per_week × hafta sayısı` politikasını karşılamazsa
hamle yapılmaz. Bu eşik istatistiksel güven veya öğrenilmiş anlamlılık iddiası
değildir.

JSON `streaming.before` ve `streaming.after`, tarih/`add_id`/`drop_id` içeren
`actions`, son kadro ve her hafta için limit, önceki tüketim, takas maliyeti,
planlanan ekleme ve kalan hakkı saklar. Markdown bunları oyuncu ve takım
adlarıyla gösterir; iki plan arasındaki kategori değişimleri ayrıca sunulur.
İki taraftan birinde hamle varsa ana kararın referansı `trade_plus_streaming`
olur. Takassız planın da kazancı hesaba katıldığı için streaming, takasın
sonucunu iyileştirebileceği gibi daha zayıf gösterebilir. Mevcut kısmi/canlı
hafta sınırı bu aşamada da geçerlidir.

## Aşama 4: fırsat taraması, piyasa kontrolü ve karşı teklifler

Aynı girdi dosyasıyla iki ayrı komut kullanılabilir:

```powershell
.\.venv\Scripts\python.exe -m src.trade_search config/trade.local.json --mode opportunities
.\.venv\Scripts\python.exe -m src.trade_search config/trade.local.json --mode counter
```

`opportunities`, `proposal.our_team`, `snapshot_id`, `effective_date` ve gerçek
gelecek haftaları kullanır. Verilen/alınan oyuncu listeleri bu modda başlangıç
paketini sınırlamaz. `counter` ise tam ve geçerli mevcut teklifi ister; yalnız
aynı karşı takımla küçük paket değişikliklerini arar. Mevcut teklif piyasa
filtresine takılsa bile ayrıca değerlendirilir. Sonuçlar varsayılan olarak
`reports/trade_search/` altında ayrı Markdown ve JSON dosyalarına yazılır.

Arama sırası:

1. Gerçek gelecek fantasy rakipleri ve NBA maç günleriyle kategori ihtiyacı
   gradyanları hesaplanır. Oyuncu paketlerinin marjinal katkıları vektörel
   olarak karşılaştırılır. Bu yerel, sabit varyanslı kısa liste yaklaşımıdır;
   günlük kadro çakışmaları ve paket tamamlayıcılığı nihai motorla doğrulanır.
2. Takım ve paket türü çeşitliliği korunarak en fazla 40 paket tam motorla
   değerlendirilir. Bu aşamada **streaming kapalıdır**. İsteğe bağlı tekli FA
   tamamlama kullanılabilir. Açılan koltuğu streaming ile değerlendirebilecek
   başabaş paketleri hemen elememek için ön elemede sınırlı tolerans vardır.
3. En iyi en fazla 3 aday, özgün nihai ayarlarla yeniden hesaplanır. Streaming
   girdide açıksa yalnız bu son adaylarda çalışır. Nihai sıralama, aynı analiz
   düzeyinde değerlendirilmiş bu adaylar arasında yapılır; ön eleme puanı ile
   streaming sonucu aynı listede karıştırılmaz. Bütün son adaylar başarısızsa
   daha düşük analiz düzeyinden sessizce öneri seçilmez.

Karşı teklif modunda mevcut teklif de aynı nihai ayarlarla bir kez hesaplanır;
bu nedenle varsayılan en fazla üç adayın yanında bir mevcut teklif için daha
streaming çalışabilir. `search.streaming_finalists`, **paket sayısıdır**;
`streaming.finalists` her paketin içindeki plan bütçesidir. Sabit bir “12 motor
koşusu” veya “10–15 kat yavaşlama” varsayılmaz; gerçek süreler `timings`, sayaçlar
`counts` içinde raporlanır. Tek veri anında değişmeyen NBA oyuncu momentleri
adaylar arasında yeniden kullanılır; bu önbellek başka veri/ayar bağlamıyla
paylaşılmaz. Oyuncu modeli, sahiplik ve sakatlık kayıtları değiştirilmez.

`search` ayarları:

- `team_ids`: İsteğe bağlı kanonik karşı takım listesi. Yoksa bilinen diğer
  takımlar taranır. Raporda gerçek takım adları kullanılır.
- `package_types`: `1x1`, `2x2`, `2x1`, `1x2`; varsayılan hepsi.
- `shortlist_size`: Tam ön eleme bütçesi; varsayılan 40, en fazla 50.
- `per_shape_candidates`: Her karşı takım/paket türü için hızlı havuz; varsayılan 8.
- `streaming_finalists`: Nihai paket bütçesi; varsayılan 3, en fazla 5.
- `screen_with_fa`: Varsayılan `"asymmetric"`; 2'ye 1 ve 1'e 2 paketlerde
  doğrulanmış tek FA tamamlama ön elemede hesaba katılır. `true` bütün türlerde
  açar; açıkça `false` verilirse bizim FA tamamlamamız kapatılır.
- `screen_fa_candidates`: Hızlı aşamadaki FA aday bütçesi; varsayılan 1, en fazla 5.
  Bu tek FA'yı bütün senaryolara otomatik eklemek değildir: erişim, tarih,
  hamle bütçesi, takassız alternatif ve kategori katkısı motorla hesaplanır.
- `min_gain_per_week`: Nihai temkinli katkı eşiği; varsayılan 0.05 kategori puanı.
- `max_partner_loss_per_week`: Karşı takımın tolere edilen temkinli kaybı;
  varsayılan 0.05. Bu menajerin kabul olasılığı değildir.
- `refinement_slack_per_week`: Ön elemede nihai eşiklere ek tolerans; varsayılan
  0.25. Finalde bu tolerans kaldırılır. Asimetrik paketlerde varsayılan tekli
  FA hesabı önce yapılır; eksik FA/hamle verisi boş koltuktan kesin kayıp
  türetmez. Bütçe/FA bilinmiyorsa nihai durum veri gerekli olarak işaretlenir.
  Sınırlı kısa liste dışında kalan paketler için optimum garantisi yoktur.
- `counter_improvement_per_week`: Mevcut teklife göre asgari temkinli iyileşme;
  varsayılan 0.01. Nihai katkı/karşı taraf eşikleri ayrıca uygulanır.
- `max_counter_edits`: Varsayılan 2. Bir oyuncu eklemek/çıkarmak bir, değiştirmek
  iki düzenleme sayılır. En az bir mevcut paket oyuncusu korunur; tüm teklifi
  başka oyuncularla değiştirip “karşı teklif” denmez.
- `require_market`: Varsayılan false. True ise yalnız tam, güncel ve dengeli
  replacement-adjusted piyasa değeri bulunan paketler otomatik taramaya girer.

Bu eşikler kullanıcı politikasıdır; öğrenilmiş kabul/başarı yüzdeleri değildir.
Gerçek kadronun tüm oyuncuları otomatik korunmaz. `do_not_drop` dışındaki oyuncular,
gerekirse takassız referansta da bırakılabilir. Her iki planın üç hakka sahip
olması üç hamle yapacağı anlamına gelmez; yalnız katkı sağlayan plan seçilir.
`do_not_trade` koruması ayrıca uygulanır. Otomatik arama IL oyuncularını taşımaz;
IL içeren açık teklifler Aşama 2 değerlendirmesiyle incelenebilir. Eski teklifin
pakete özgü bırakma/IL talimatları yeni paketlere kopyalanmaz; yeni bırakmalar
motorla seçilir, mevcut IL yerleşimi korunur.

### Kaynaklı piyasa verisi

Piyasa dosyasını şablondan hazırlayıp açıkça verin:

```powershell
Copy-Item config/trade_market.template.json config/trade_market.local.json
.\.venv\Scripts\python.exe -m src.trade_search config/trade.local.json --market config/trade_market.local.json
```

Veri aynı dosyada `market_snapshot` alanıyla da sağlanabilir. `source` gerçek
kaynağı; `captured_at` saat dilimli ISO yakalama zamanını; `players` ise Yahoo
oyuncu kimliğinden kaynak kaydına eşlemeyi belirtir. Şablon boş alanları
doldurulmadan geçerli piyasa verisi değildir. İki metrik desteklenir:

- `metric="rank"`: Her oyuncuda pozitif tam sayı `rank`. **Sıra numaraları
  toplanmaz.** Varsayılan olarak iki paketin en iyi sıraları arasında 50'den
  büyük fark varsa, oyuncular ilk 20'de olmasa da uç dengesizlik olarak elenir. Bu
  yalnız kaba ordinal kontroldür; çok oyunculu paketin fiyatını doğrulamaz.
- `metric="replacement_adjusted_trade_value"`: Her oyuncuda sonlu, negatif
  olmayan `trade_value`. Bunlar aynı kaynaktan, aynı ölçekte, replacement
  seviyesine göre düzeltilmiş toplanabilir takas değerleri olmalıdır. Paket
  toplamlarının büyük/küçük oranı varsayılan 1.75'i aşarsa elenir. Herhangi
  bir ranking/Z skorunu bu adla etiketlemek piyasa verisi sağlamaz.

`market_policy.max_age_days=7`, `max_value_ratio=1.75`, `elite_rank=20`,
`extreme_rank_gap=50` değerleri yapılandırılabilir. Bayat, gelecek tarihli,
geçersiz veya eksik veri makullük kanıtı sayılmaz. Kaynak olmadığında sonuç
`conditional_market_review` olarak açıkça elle inceleme ister; modelin kendi
`ADP_Z` veya oyuncu sıralaması Yahoo verisi yerine kullanılmaz. Piyasa puanı
kategori katkısına veya yıldız primi olarak nihai skora eklenmez.

İsteğe bağlı `projected_rank`, `recent_rank_14d`, `recent_rank_30d` aynı kaynaktan
gelirse görünür form/projeksiyon farkları açıklanır. Bunlar olası algı farkıdır;
“Bayesian gerçek değer” veya otomatik buy-low/sell-high kazanç garantisi değildir.
Menajer kabul/ret geçmişiyle doğrulanmış bir davranış modeli bulunmadığından
insanın kabul etme olasılığı üretilmez.

Nihai rapor iki tarafın kategori katkısını, piyasa kaynağı ve zamanını, karşı
teklifin mevcut teklife farkını, gerekiyorsa tarihli streaming planını gösterir.
JSON bütün ön eleme/son adayları, geçersiz paket gerekçelerini ve kaynak
hash'lerini saklar. Fırsatlar birbirinin alternatifidir. Karşı takımın kendi
gelecekteki tam streaming tercihleri modellenmez. Ancak karşı takımın 1'e 2
pakette açılan yeri için kendi tek FA tamamlaması hem ön elemede hem nihai
hesapta değerlendirilir. Bizim planlarımızda kullanılan FA'lar diğer takıma
atanmaz; bu muhafazakâr rezervasyonla ortak iki kadro tekrar projekte edilir.
Aynı FA'nın farklı takımlara tahsis edilebileceği bütün ortak planların global
optimumu aranmaz. Karşı takımın kendi takassız tek FA alternatifi de karşılaştırılır;
bu varsayım fırsatın insan tarafından kabul edilme olasılığı değildir.
Tam lig fikstürünün yerini eşit
rakip ortalaması almaz; yeni veri olmadan playoff yüzdesi üretilmez.

## Aşama 1 tarafından üretilen örnek takas raporu

> Aşağıdaki rapor, yerel önbellekteki gerçek oyuncu tahminleri, mevcut 14 takım
> kadrosu ve NBA maç takvimiyle `evaluate_trade` ve `render_trade_report`
> çalıştırılarak üretilmiştir. Oyuncu ve takım adları proje kayıtlarından gelir.
> **Desmond Bane ↔ Evan Mobley takası ve bu örnekte kullanılan gelecek fantasy
> eşleşmeleri varsayımsaldır; Yahoo'dan alınmış gerçek bir teklif veya
> doğrulanmış gelecek lig fikstürü değildir.** Kurallar ve tam Yahoo pozisyon
> uygunlukları doğrulanmamıştır. Sonuç, yalnızca belirtilen bir haftaya aittir;
> kalan sezon kararı olarak kullanılmamalıdır. Sayısal sonuçlar elle yazılmamış,
> yalnızca raporun başlık seviyeleri bu dokümana uyarlanmıştır.

### Takas analizi

Veri anı: 2026-10-30T17:15:37.306098+00:00
Karar: **Ret önerisi**
Kapsam: Yalnızca sağlanan haftalar

**Berk's Best Team ↔ MuCa Tandır**

Berk's Best Team veriyor: **Desmond Bane**

Berk's Best Team alıyor: **Evan Mobley**

Yürürlük tarihi: 2026-11-02

#### Berk's Best Team

Beklenen kategori puanı (1 hafta): 6.662 → 6.503 (Δ -0.159)
İlk dört sağlanan hafta: Δ -0.159
Sakatlık dakika dağıtımı kapalı: Δ -0.051

| Kategori | Önce kazanma | Sonra kazanma | Δ yüzde puan | Δ kategori puanı |
|---|---:|---:|---:|---:|
| PTS | %85.12 | %83.76 | -1.35 | -0.013 |
| REB | %96.17 | %99.52 | +3.35 | +0.032 |
| AST | %86.64 | %83.11 | -3.54 | -0.034 |
| STL | %89.92 | %86.03 | -3.88 | -0.036 |
| BLK | %78.34 | %94.95 | +16.61 | +0.154 |
| TOV | %24.51 | %30.95 | +6.44 | +0.066 |
| FG3M | %76.23 | %64.92 | -11.32 | -0.111 |
| FG_PCT | %57.88 | %71.16 | +13.28 | +0.133 |
| FT_PCT | %65.40 | %30.56 | -34.84 | -0.348 |

##### Haftalık üretim ve rakip

2026-11-02 – 2026-11-08, rakip: MuCa Tandır

| Kategori | Önce üretim | Sonra üretim |
|---|---:|---:|
| PTS | 513.739 | 507.866 |
| REB | 203.042 | 210.286 |
| AST | 113.508 | 112.359 |
| STL | 37.872 | 37.202 |
| BLK | 24.105 | 26.163 |
| TOV | 55.407 | 54.193 |
| FG3M | 56.551 | 55.010 |
| FG_PCT | 0.488 | 0.492 |
| FT_PCT | 0.800 | 0.776 |

#### MuCa Tandır

Beklenen kategori puanı (1 hafta): 2.338 → 2.497 (Δ +0.159)
İlk dört sağlanan hafta: Δ +0.159
Sakatlık dakika dağıtımı kapalı: Δ +0.051

| Kategori | Önce kazanma | Sonra kazanma | Δ yüzde puan | Δ kategori puanı |
|---|---:|---:|---:|---:|
| PTS | %14.56 | %15.90 | +1.33 | +0.013 |
| REB | %3.56 | %0.43 | -3.12 | -0.032 |
| AST | %12.31 | %15.67 | +3.36 | +0.034 |
| STL | %8.32 | %11.73 | +3.41 | +0.036 |
| BLK | %17.98 | %3.79 | -14.19 | -0.154 |
| TOV | %72.94 | %66.22 | -6.72 | -0.066 |
| FG3M | %21.43 | %32.26 | +10.83 | +0.111 |
| FG_PCT | %42.12 | %28.84 | -13.28 | -0.133 |
| FT_PCT | %34.60 | %69.44 | +34.84 | +0.348 |

##### Haftalık üretim ve rakip

2026-11-02 – 2026-11-08, rakip: Berk's Best Team

| Kategori | Önce üretim | Sonra üretim |
|---|---:|---:|
| PTS | 438.818 | 437.257 |
| REB | 149.757 | 133.773 |
| AST | 90.673 | 92.481 |
| STL | 25.467 | 26.564 |
| BLK | 17.688 | 13.630 |
| TOV | 47.169 | 48.382 |
| FG3M | 46.859 | 49.551 |
| FG_PCT | 0.480 | 0.470 |
| FT_PCT | 0.776 | 0.807 |

#### Eşit maç hacminde paket üretimi

Four games per player at current availability; package production only. Excludes daily lineup constraints and is not a team win probability.

| İstatistik | Verilen | Alınan | Δ |
|---|---:|---:|---:|
| PTS | 71.194 | 59.815 | -11.379 |
| REB | 16.717 | 29.929 | +13.213 |
| AST | 14.716 | 11.260 | -3.457 |
| STL | 3.987 | 2.565 | -1.422 |
| BLK | 1.753 | 5.543 | +3.790 |
| TOV | 8.058 | 5.855 | -2.203 |
| FG3M | 8.117 | 3.883 | -4.235 |
| FGM | 24.740 | 22.784 | -1.956 |
| FGA | 53.066 | 41.855 | -11.211 |
| FTM | 12.876 | 9.516 | -3.361 |
| FTA | 14.790 | 14.714 | -0.076 |

#### Playoff takvimi: ham NBA maç sayısı

Doğrulanmış playoff tarihleri girilmedi.

#### Koşullar ve varsayımlar

- Current player roles projected forward; long-range estimates are conditional.
- Per-team capture times are unavailable; merged roster freshness is not proven.
- Exact Yahoo eligibility is incomplete; NBA positions are approximate.
- Trade rules have not been confirmed.
- Fantasy fixtures have not been confirmed.
- Supplied weeks do not establish complete remaining-season coverage.
- No acquisitions or manager acceptance probability modeled.
- Completed/live partial fantasy weeks excluded.
- Neutral package totals exclude lineup constraints; playoff counts are raw games.
- Sensitivity is a scenario comparison, not a confidence interval.
- No calibrated acceptance margin; positive estimates remain conditional.

## Aşama 2 tarafından üretilen örnek takas raporu

> Bu örnek gerçek yerel oyuncu tahminleri, mevcut 14 takım kadrosu, NBA fikstürü
> ve doğrulanmış Yahoo FA/waiver önbelleğiyle Aşama 2 motorundan üretilmiştir.
> **Desmond Bane + Jarrett Allen ↔ Lauri Markkanen teklifi ve gelecek fantasy
> eşleşmeleri varsayımsaldır.** Kurallar ve tam Yahoo pozisyon uygunlukları
> doğrulanmamıştır. Örnek için gelecek hafta üç ekleme hakkı, sıfır kullanılmış
> hak ve takasın ekleme hakkı tüketmediği varsayılmıştır; gerçek kullanım verisi
> olarak yorumlanmamalıdır. İki tarafın hamlesiz kadrosu, zorunlu bırakma ve
> tek FA eklemeli alternatifler aynı bir haftalık pencerede karşılaştırılır.
> İleri tarihte FA erişimi/waiver claim başarısı garanti değildir. Sekiz adaylık
> kısa listenin en fazla üç anlamlı alternatifi gösterilir; global en iyi FA
> garantisi yoktur. Sonuçlar elle yazılmamış, yalnız başlık seviyeleri uyarlanmıştır.

### Takas analizi

Veri anı: 2026-10-30T17:41:14.680825+00:00
Karar: **Ret önerisi**
Kapsam: Yalnızca sağlanan haftalar

**Berk's Best Team ↔ Philadelphia Sikers**

Berk's Best Team veriyor: **Desmond Bane, Jarrett Allen**

Berk's Best Team alıyor: **Lauri Markkanen**

Yürürlük tarihi: 2026-11-02

#### Zorunlu kadro düzenlemesi

Philadelphia Sikers bırakıyor: **Joan Beringer**

Aşağıdaki saf takas sonuçları bu bırakmaların maliyetini içerir.

İşlem sonrası IL yerleşimi:

- Berk's Best Team: Kawhi Leonard, Brandon Ingram
- Philadelphia Sikers: Ivica Zubac

#### Berk's Best Team — saf takas ve zorunlu bırakmalar

Beklenen kategori puanı (1 hafta): 5.667 → 4.165 (Δ -1.502)
İlk dört sağlanan hafta: Δ -1.502
Sakatlık dakika dağıtımı kapalı: Δ -1.107

| Kategori | Önce kazanma | Sonra kazanma | Δ yüzde puan | Δ kategori puanı |
|---|---:|---:|---:|---:|
| PTS | %37.81 | %3.65 | -34.17 | -0.344 |
| REB | %96.42 | %57.21 | -39.21 | -0.387 |
| AST | %32.98 | %7.26 | -25.72 | -0.262 |
| STL | %81.95 | %55.15 | -26.81 | -0.261 |
| BLK | %85.17 | %59.39 | -25.78 | -0.247 |
| TOV | %69.48 | %93.53 | +24.04 | +0.233 |
| FG3M | %24.84 | %17.80 | -7.04 | -0.072 |
| FG_PCT | %77.74 | %57.98 | -19.76 | -0.198 |
| FT_PCT | %54.12 | %57.61 | +3.49 | +0.035 |

##### Haftalık üretim ve rakip

2026-11-02 – 2026-11-08, rakip: Philadelphia Sikers

| Kategori | Önce üretim | Sonra üretim |
|---|---:|---:|
| PTS | 513.370 | 448.789 |
| REB | 200.986 | 179.031 |
| AST | 113.954 | 101.749 |
| STL | 38.448 | 35.028 |
| BLK | 23.516 | 21.099 |
| TOV | 55.514 | 48.148 |
| FG3M | 57.306 | 53.988 |
| FG_PCT | 0.486 | 0.477 |
| FT_PCT | 0.801 | 0.800 |

#### Philadelphia Sikers — saf takas ve zorunlu bırakmalar

Beklenen kategori puanı (1 hafta): 3.333 → 4.835 (Δ +1.502)
İlk dört sağlanan hafta: Δ +1.502
Sakatlık dakika dağıtımı kapalı: Δ +1.107

| Kategori | Önce kazanma | Sonra kazanma | Δ yüzde puan | Δ kategori puanı |
|---|---:|---:|---:|---:|
| PTS | %61.72 | %96.25 | +34.53 | +0.344 |
| REB | %3.32 | %41.47 | +38.15 | +0.387 |
| AST | %65.50 | %92.14 | +26.65 | +0.262 |
| STL | %15.45 | %40.81 | +25.36 | +0.261 |
| BLK | %11.89 | %35.47 | +23.58 | +0.247 |
| TOV | %28.09 | %5.62 | -22.46 | -0.233 |
| FG3M | %72.94 | %80.32 | +7.38 | +0.072 |
| FG_PCT | %22.26 | %42.02 | +19.76 | +0.198 |
| FT_PCT | %45.88 | %42.39 | -3.49 | -0.035 |

##### Haftalık üretim ve rakip

2026-11-02 – 2026-11-08, rakip: Berk's Best Team

| Kategori | Önce üretim | Sonra üretim |
|---|---:|---:|
| PTS | 538.204 | 591.592 |
| REB | 146.929 | 173.126 |
| AST | 124.003 | 136.076 |
| STL | 29.133 | 33.273 |
| BLK | 15.386 | 18.839 |
| TOV | 63.226 | 69.999 |
| FG3M | 66.759 | 66.719 |
| FG_PCT | 0.457 | 0.470 |
| FT_PCT | 0.795 | 0.789 |

#### Boşalan yer için FA seçenekleri

Berk's Best Team: tarih ve bütçesi uygun 456 adaydan 8 oyuncu tam motorla incelendi.

Doğrulanmış bütçeyle anlamlı ek katkı sağlayan bir seçenek sunulmadı.

Anlamlılık eşiği: haftada 0.050 kategori puanı; bu bir karar ayarıdır, kalibre edilmiş güven ölçüsü değildir.

- FA/waiver erişimi işlem gününde yeniden doğrulanmalı; alternatifler birlikte uygulanmaz.

#### Eşit maç hacminde paket üretimi

Four games per player at current availability; package production only. Excludes daily lineup constraints and is not a team win probability.

| İstatistik | Verilen | Alınan | Δ |
|---|---:|---:|---:|
| PTS | 126.054 | 38.950 | -87.105 |
| REB | 48.422 | 11.300 | -37.122 |
| AST | 20.907 | 3.356 | -17.551 |
| STL | 7.292 | 1.381 | -5.911 |
| BLK | 5.455 | 0.770 | -4.685 |
| TOV | 12.955 | 2.576 | -10.379 |
| FG3M | 8.409 | 4.814 | -3.596 |
| FGM | 45.267 | 12.746 | -32.521 |
| FGA | 86.336 | 27.570 | -58.766 |
| FTM | 24.267 | 7.484 | -16.783 |
| FTA | 30.619 | 8.762 | -21.857 |

#### Playoff takvimi: ham NBA maç sayısı

Doğrulanmış playoff tarihleri girilmedi.

#### Koşullar ve varsayımlar

- Current player roles projected forward; long-range estimates are conditional.
- Per-team capture times are unavailable; merged roster freshness is not proven.
- Exact Yahoo eligibility is incomplete; NBA positions are approximate.
- Trade rules have not been confirmed.
- Fantasy fixtures have not been confirmed.
- A traded player has an injury designation; return-date assumptions matter.
- Supplied weeks do not establish complete remaining-season coverage.
- FA options are alternative single pickups held for the remaining window; no streaming or manager acceptance probability modeled.
- FA shortlist uses a fast proxy; the reported options do not guarantee a global optimum.
- Completed/live partial fantasy weeks excluded.
- Neutral package totals exclude lineup constraints; playoff counts are raw games.
- Sensitivity is a scenario comparison, not a confidence interval.
- No calibrated acceptance margin; positive estimates remain conditional.

## Aşama 2 ek testi: korumalı kadroda trade_plus_fa

> **Bu bölüm kontrollü bir yazılım/raporlama testidir; gerçek lig tavsiyesi
> değildir.** Dört temsili takımın kadroları, oyuncu tahminleri, haftalık maç
> günleri, pozisyon uygunlukları ve FA kanıtı `tests/test_trades.py` içindeki
> `protected_slot_scenario` yordamıyla kurgulanmıştır. Gerçek kişi/takım adları
> yalnız okunabilirlik için kullanılmıştır; sayılar gerçek performans tahmini
> veya Yahoo'dan alınmış bir teklif/FA kaydı olarak yorumlanmamalıdır.
>
> Testte Desmond Bane + Jarrett Allen'ın toplam üretimi Lauri Markkanen'in
> üretimine eşit kurulmuştur. Böylece saf takasın kategori puanı farkı
> +0.000000000 olur. Oyuncu oranları gerçek ligden fit edilmemiştir.
> Luke Kennard için de FA katkısını görünür kılan temsili üretim kullanılır.
> Sakatlık dakika dağıtımı kapalıdır; bu test sakatlık modelini doğrulamaz.

Takassız Berk's Best Team kadrosunda 13 aktif/bench oyuncunun **tamamı**
`do_not_drop_yahoo_ids` ile korunmuştur. Bu, takas edilmelerini engellemez;
`do_not_trade` ayrı bir tercihtir. Yalnızca 13. oyuncuyu korumak diğer 12
oyuncunun bırakılmasını engellemez. IL alanı kullanılmamıştır. Philadelphia
Sikers'ın işlem sonrası zorunlu bırakması Joan Beringer olarak açık verilmiş,
bu oyuncu test haftasında maçsız kurulmuştur; maliyeti yine motor hesabındadır.
Bir haftada üç ekleme hakkı, sıfır kullanım ve tek FA adayı varsayılmıştır.

Aynı motor iki kontrol için çalıştırıldı:

| Kontrol | Takassız referansın hamlesi | Saf takas Δ | Takas + FA'nın adil referansa göre Δ |
|---|---|---:|---:|
| 13 oyuncunun tamamı korumalı | Oyuncu bırakamıyor; FA ekleyemiyor | +0.000 | +0.829 |
| Yalnız 13. oyuncu korumalı | Tyrese Maxey bırakılıyor, Luke Kennard alınıyor | +0.000 | +0.537 |

Üretilen ana sonuç: **Koşullu kabul (`trade_plus_fa`)**.
Koruma kaldırılınca FA avantajının tamamı takasa yazılmaz; takassız referansın
aynı FA ile elde ettiği katkı karşılaştırmadan düşülür. Aşağıdaki rapor
`evaluate_trade` ve `render_trade_report` çıktısıdır; yalnız başlık seviyeleri
bu dokümana uyarlanmıştır.

### Takas analizi

Veri anı: 2026-10-30T12:00:00+00:00
Karar: **Koşullu kabul**
Kapsam: Yalnızca sağlanan haftalar

**Berk's Best Team ↔ Philadelphia Sikers**

Berk's Best Team veriyor: **Desmond Bane, Jarrett Allen**

Berk's Best Team alıyor: **Lauri Markkanen**

Yürürlük tarihi: 2026-11-01

Kararın referansı: **takas + aşağıda adı verilen FA eklemesi**; aynı FA havuzunu kullanabilen takassız kadroyla karşılaştırıldı.

#### Zorunlu kadro düzenlemesi

Philadelphia Sikers bırakıyor: **Joan Beringer**

Aşağıdaki saf takas sonuçları bu bırakmaların maliyetini içerir.

#### Berk's Best Team — saf takas ve zorunlu bırakmalar

Beklenen kategori puanı (1 hafta): 4.500 → 4.500 (Δ +0.000)
İlk dört sağlanan hafta: Δ +0.000
Sakatlık dakika dağıtımı kapalı: Δ +0.000

| Kategori | Önce kazanma | Sonra kazanma | Δ yüzde puan | Δ kategori puanı |
|---|---:|---:|---:|---:|
| PTS | %49.54 | %49.54 | +0.00 | +0.000 |
| REB | %49.33 | %49.33 | +0.00 | +0.000 |
| AST | %48.73 | %48.73 | +0.00 | +0.000 |
| STL | %47.04 | %47.04 | +0.00 | +0.000 |
| BLK | %46.50 | %46.50 | +0.00 | +0.000 |
| TOV | %48.17 | %48.17 | +0.00 | +0.000 |
| FG3M | %47.73 | %47.73 | +0.00 | +0.000 |
| FG_PCT | %50.00 | %50.00 | +0.00 | +0.000 |
| FT_PCT | %50.00 | %50.00 | +0.00 | +0.000 |

##### Haftalık üretim ve rakip

2026-11-02 – 2026-11-08, rakip: Philadelphia Sikers

| Kategori | Önce üretim | Sonra üretim |
|---|---:|---:|
| PTS | 222.170 | 222.170 |
| REB | 168.693 | 168.693 |
| AST | 70.289 | 70.289 |
| STL | 17.973 | 17.973 |
| BLK | 13.085 | 13.085 |
| TOV | 40.099 | 40.099 |
| FG3M | 27.000 | 27.000 |
| FG_PCT | 0.494 | 0.494 |
| FT_PCT | 0.794 | 0.794 |

#### Philadelphia Sikers — saf takas ve zorunlu bırakmalar

Beklenen kategori puanı (1 hafta): 4.500 → 4.500 (Δ +0.000)
İlk dört sağlanan hafta: Δ +0.000
Sakatlık dakika dağıtımı kapalı: Δ +0.000

| Kategori | Önce kazanma | Sonra kazanma | Δ yüzde puan | Δ kategori puanı |
|---|---:|---:|---:|---:|
| PTS | %49.54 | %49.54 | +0.00 | +0.000 |
| REB | %49.33 | %49.33 | +0.00 | +0.000 |
| AST | %48.73 | %48.73 | +0.00 | +0.000 |
| STL | %47.04 | %47.04 | +0.00 | +0.000 |
| BLK | %46.50 | %46.50 | +0.00 | +0.000 |
| TOV | %48.17 | %48.17 | +0.00 | +0.000 |
| FG3M | %47.73 | %47.73 | +0.00 | +0.000 |
| FG_PCT | %50.00 | %50.00 | +0.00 | +0.000 |
| FT_PCT | %50.00 | %50.00 | +0.00 | +0.000 |

##### Haftalık üretim ve rakip

2026-11-02 – 2026-11-08, rakip: Berk's Best Team

| Kategori | Önce üretim | Sonra üretim |
|---|---:|---:|
| PTS | 222.170 | 222.170 |
| REB | 168.693 | 168.693 |
| AST | 70.289 | 70.289 |
| STL | 17.973 | 17.973 |
| BLK | 13.085 | 13.085 |
| TOV | 40.099 | 40.099 |
| FG3M | 27.000 | 27.000 |
| FG_PCT | 0.494 | 0.494 |
| FT_PCT | 0.794 | 0.794 |

#### Boşalan yer için FA seçenekleri

Berk's Best Team: tarih ve bütçesi uygun 1 adaydan 1 oyuncu tam motorla incelendi.

##### Berk's Best Team: Luke Kennard

Ekleme günü: 2026-11-02 · Yahoo durumu: FA

İncelenen takassız referans: 4.500; takas + FA: 5.329 kategori puanı.

Adil referansa göre Δ: **+0.829**; sakatlık dakika dağıtımı kapalı: +0.829. Saf takasa ek katkı: +0.829.

Takassız referans mevcut kadrosunu koruyor.

| Kategori | Adil referansa göre Δ kategori puanı |
|---|---:|
| PTS | +0.215 |
| REB | +0.231 |
| AST | +0.189 |
| STL | +0.117 |
| BLK | +0.101 |
| TOV | -0.158 |
| FG3M | +0.134 |
| FG_PCT | -0.000 |
| FT_PCT | +0.000 |

Anlamlılık eşiği: haftada 0.050 kategori puanı; bu bir karar ayarıdır, kalibre edilmiş güven ölçüsü değildir.

- FA/waiver erişimi işlem gününde yeniden doğrulanmalı; alternatifler birlikte uygulanmaz.

#### Eşit maç hacminde paket üretimi

Four games per player at current availability; package production only. Excludes daily lineup constraints and is not a team win probability.

| İstatistik | Verilen | Alınan | Δ |
|---|---:|---:|---:|
| PTS | 68.360 | 68.360 | +0.000 |
| REB | 51.906 | 51.906 | +0.000 |
| AST | 21.627 | 21.627 | +0.000 |
| STL | 5.530 | 5.530 | +0.000 |
| BLK | 4.026 | 4.026 | +0.000 |
| TOV | 12.338 | 12.338 | +0.000 |
| FG3M | 8.308 | 8.308 | +0.000 |
| FGM | 51.579 | 51.579 | +0.000 |
| FGA | 104.317 | 104.317 | +0.000 |
| FTM | 19.098 | 19.098 | +0.000 |
| FTA | 24.044 | 24.044 | +0.000 |

#### Playoff takvimi: ham NBA maç sayısı

Doğrulanmış playoff tarihleri girilmedi.

#### Koşullar ve varsayımlar

- Controlled test: real names, synthetic ownership, forecasts, fixtures and FA evidence.
- Trade rules have not been confirmed.
- Fantasy fixtures have not been confirmed.
- FA-assisted decision is conditional on the named pickup and acquisition budget.
- Supplied weeks do not establish complete remaining-season coverage.
- FA options are alternative single pickups held for the remaining window; no streaming or manager acceptance probability modeled.
- FA shortlist uses a fast proxy; the reported options do not guarantee a global optimum.
- Completed/live partial fantasy weeks excluded.
- Neutral package totals exclude lineup constraints; playoff counts are raw games.
- Sensitivity is a scenario comparison, not a confidence interval.
- No calibrated acceptance margin; positive estimates remain conditional.

## Aşama 3 tarafından üretilen örnek streaming raporu

> **Kontrollü yazılım testi; gerçek lig tavsiyesi değildir.** Gerçek oyuncu ve
> takım adları okunabilirlik için kullanılmıştır. Kadrolar, üretim oranları,
> NBA/fantasy maç günleri, pozisyonlar ve FA kanıtı `tests/test_streaming.py`
> içindeki `streaming_fixture` verisidir; Yahoo'dan alınmış gerçek teklif veya
> güncel oyuncu tahmini olarak yorumlanmamalıdır. Önceki korumalı kadro testindeki
> başabaş 2'ye 1 takas kullanılır. Takassız 13 oyuncu bırakmaya karşı korunur;
> takas sonrası açılan yerde alınan FA'lar korunmaz ve değiştirilebilir.
>
> Luke Kennard testte 2 ve 4 Kasım'da; Norman Powell 6 ve 8 Kasım'da oynar.
> Plan Kennard'ın önceki katkısını silmeden onu Powell ile değiştirir. İki
> ekleme, üç haklık haftalık limitten düşer. Eşik, varsayılan haftada 0.05
> kategori puanıdır. Sakatlık dakika dağıtımı kapalı bu örnek, sakatlık
> varsayımlarının doğruluğunu sınamaz. Sayılar doğrudan `evaluate_trade` ve
> `render_trade_report` çıktısıdır; yalnız başlık seviyeleri uyarlanmıştır.

Üretilen karar referansı: **`trade_plus_streaming`**.
Yönetilen takassız kadroya göre katkı: **+2.075 kategori puanı**.
Sonraki tablo, hamlelerin birlikte uygulanacağı sıralı plandır; Aşama 2'nin
birbirinin alternatifi olan tek ekleme önerilerinden farklıdır.

### Takas analizi

Veri anı: 2026-10-30T12:00:00+00:00
Karar: **Koşullu kabul**
Kapsam: Yalnızca sağlanan haftalar

**Berk's Best Team ↔ Philadelphia Sikers**

Berk's Best Team veriyor: **Desmond Bane, Jarrett Allen**

Berk's Best Team alıyor: **Lauri Markkanen**

Yürürlük tarihi: 2026-11-01

Kararın referansı: **takaslı ve takassız kadroların ayrı streaming planları**; aynı FA havuzu, koruma ve haftalık hamle kurallarıyla karşılaştırıldı.

#### Zorunlu kadro düzenlemesi

Philadelphia Sikers bırakıyor: **Joan Beringer**

Aşağıdaki saf takas sonuçları bu bırakmaların maliyetini içerir.

#### Berk's Best Team — saf takas ve zorunlu bırakmalar

Beklenen kategori puanı (1 hafta): 4.500 → 4.500 (Δ +0.000)
İlk dört sağlanan hafta: Δ +0.000
Sakatlık dakika dağıtımı kapalı: Δ +0.000

| Kategori | Önce kazanma | Sonra kazanma | Δ yüzde puan | Δ kategori puanı |
|---|---:|---:|---:|---:|
| PTS | %49.54 | %49.54 | +0.00 | +0.000 |
| REB | %49.33 | %49.33 | +0.00 | +0.000 |
| AST | %48.73 | %48.73 | +0.00 | +0.000 |
| STL | %47.04 | %47.04 | +0.00 | +0.000 |
| BLK | %46.50 | %46.50 | +0.00 | +0.000 |
| TOV | %48.17 | %48.17 | +0.00 | +0.000 |
| FG3M | %47.73 | %47.73 | +0.00 | +0.000 |
| FG_PCT | %50.00 | %50.00 | +0.00 | +0.000 |
| FT_PCT | %50.00 | %50.00 | +0.00 | +0.000 |

##### Haftalık üretim ve rakip

2026-11-02 – 2026-11-08, rakip: Philadelphia Sikers

| Kategori | Önce üretim | Sonra üretim |
|---|---:|---:|
| PTS | 222.170 | 222.170 |
| REB | 168.693 | 168.693 |
| AST | 70.289 | 70.289 |
| STL | 17.973 | 17.973 |
| BLK | 13.085 | 13.085 |
| TOV | 40.099 | 40.099 |
| FG3M | 27.000 | 27.000 |
| FG_PCT | 0.494 | 0.494 |
| FT_PCT | 0.794 | 0.794 |

#### Philadelphia Sikers — saf takas ve zorunlu bırakmalar

Beklenen kategori puanı (1 hafta): 4.500 → 4.500 (Δ +0.000)
İlk dört sağlanan hafta: Δ +0.000
Sakatlık dakika dağıtımı kapalı: Δ +0.000

| Kategori | Önce kazanma | Sonra kazanma | Δ yüzde puan | Δ kategori puanı |
|---|---:|---:|---:|---:|
| PTS | %49.54 | %49.54 | +0.00 | +0.000 |
| REB | %49.33 | %49.33 | +0.00 | +0.000 |
| AST | %48.73 | %48.73 | +0.00 | +0.000 |
| STL | %47.04 | %47.04 | +0.00 | +0.000 |
| BLK | %46.50 | %46.50 | +0.00 | +0.000 |
| TOV | %48.17 | %48.17 | +0.00 | +0.000 |
| FG3M | %47.73 | %47.73 | +0.00 | +0.000 |
| FG_PCT | %50.00 | %50.00 | +0.00 | +0.000 |
| FT_PCT | %50.00 | %50.00 | +0.00 | +0.000 |

##### Haftalık üretim ve rakip

2026-11-02 – 2026-11-08, rakip: Berk's Best Team

| Kategori | Önce üretim | Sonra üretim |
|---|---:|---:|
| PTS | 222.170 | 222.170 |
| REB | 168.693 | 168.693 |
| AST | 70.289 | 70.289 |
| STL | 17.973 | 17.973 |
| BLK | 13.085 | 13.085 |
| TOV | 40.099 | 40.099 |
| FG3M | 27.000 | 27.000 |
| FG_PCT | 0.494 | 0.494 |
| FT_PCT | 0.794 | 0.794 |

#### Streaming: tarihli kadro ve hamle planı

Yönetilen takassız kadroya göre Δ: **+2.075**; sakatlık dakika dağıtımı kapalı: +2.075.

Takaslı kadroda streaming'in saf takasa ek katkısı: +2.075 kategori puanı.

##### Takassız kadro

Hamle yok; kadro korunuyor.

| Hafta başlangıcı | Limit | Önceden kullanılan | Takas maliyeti | Planlanan ekleme | Kalan |
|---|---:|---:|---:|---:|---:|
| 2026-11-02 | 3 | 0 | 0 | 0 | 3 |

Son kadro: Desmond Bane, Jarrett Allen, Tyrese Maxey, Ayo Dosunmu, Jake LaRavia, Precious Achiuwa, Josh Hart, Jabari Smith Jr., Neemias Queta, Julian Champagnie, Dean Wade, James Harden, Jaxson Hayes

##### Takaslı kadro

| Tarih | Alınacak oyuncu | Bırakılacak oyuncu |
|---|---|---|
| 2026-11-02 | Luke Kennard | Yok — boş yer kullanılıyor |
| 2026-11-05 | Norman Powell | Luke Kennard |

| Hafta başlangıcı | Limit | Önceden kullanılan | Takas maliyeti | Planlanan ekleme | Kalan |
|---|---:|---:|---:|---:|---:|
| 2026-11-02 | 3 | 0 | 0 | 2 | 1 |

Son kadro: Tyrese Maxey, Ayo Dosunmu, Jake LaRavia, Precious Achiuwa, Josh Hart, Jabari Smith Jr., Neemias Queta, Julian Champagnie, Dean Wade, James Harden, Jaxson Hayes, Lauri Markkanen, Norman Powell

| Kategori | İki streaming planı arasında Δ kategori puanı |
|---|---:|
| PTS | +0.477 |
| REB | +0.485 |
| AST | +0.461 |
| STL | +0.361 |
| BLK | +0.326 |
| TOV | -0.430 |
| FG3M | +0.394 |
| FG_PCT | -0.000 |
| FT_PCT | +0.000 |

Arama sınırları: 2 aday, beam genişliği 6, son değerlendirme bütçesi 6. Arama yaklaşık sonuç verir; global optimum garantisi yoktur.

- Streaming uses bounded search; global optimality is not guaranteed.
- Future FA availability and waiver claims must be reverified before each action.
- At most one atomic acquisition/drop per day; no reacquisition within the horizon.
- IL placement stays fixed; future IL activation is not planned.

#### Eşit maç hacminde paket üretimi

Four games per player at current availability; package production only. Excludes daily lineup constraints and is not a team win probability.

| İstatistik | Verilen | Alınan | Δ |
|---|---:|---:|---:|
| PTS | 68.360 | 68.360 | +0.000 |
| REB | 51.906 | 51.906 | +0.000 |
| AST | 21.627 | 21.627 | +0.000 |
| STL | 5.530 | 5.530 | +0.000 |
| BLK | 4.026 | 4.026 | +0.000 |
| TOV | 12.338 | 12.338 | +0.000 |
| FG3M | 8.308 | 8.308 | +0.000 |
| FGM | 51.579 | 51.579 | +0.000 |
| FGA | 104.317 | 104.317 | +0.000 |
| FTM | 19.098 | 19.098 | +0.000 |
| FTA | 24.044 | 24.044 | +0.000 |

#### Playoff takvimi: ham NBA maç sayısı

Doğrulanmış playoff tarihleri girilmedi.

#### Koşullar ve varsayımlar

- Controlled test: real names, synthetic ownership, forecasts, fixtures and FA evidence.
- Trade rules have not been confirmed.
- Fantasy fixtures have not been confirmed.
- Streaming-assisted decision is conditional on the full dated action plan.
- Streaming uses bounded search; global optimality is not guaranteed.
- Future FA availability and waiver claims must be reverified before each action.
- At most one atomic acquisition/drop per day; no reacquisition within the horizon.
- IL placement stays fixed; future IL activation is not planned.
- Supplied weeks do not establish complete remaining-season coverage.
- Single FA options are alternatives; the separately reported streaming plan carries dated ownership and weekly budgets.
- No manager acceptance probability modeled.
- FA shortlist uses a fast proxy; the reported options do not guarantee a global optimum.
- Completed/live partial fantasy weeks excluded.
- Neutral package totals exclude lineup constraints; playoff counts are raw games.
- Sensitivity is a scenario comparison, not a confidence interval.
- No calibrated acceptance margin; positive estimates remain conditional.

## Aşama 4 tarafından üretilen örnek fırsat ve karşı teklif raporları

> **Kontrollü yazılım testi; gerçek lig tavsiyesi veya Yahoo piyasa verisi
> değildir.** Gerçek kişi ve takım adları yalnız okunabilirlik içindir.
> Kadrolar, üretim, maç takvimi, FA kanıtı ve piyasa değerleri
> `tests/test_trade_search.py` içindeki `bilateral_fixture` ile kurgulanmıştır.
> Berk's Best Team ile Philadelphia Sikers bu örnekte birbirleriyle değil,
> farklı fantasy rakipleriyle eşleşir; farklı kategorilerdeki fazlalarını
> takas ederek iki tarafın da katkısı artabilir. Piyasa değerleri aynı ölçekte
> temsili replacement-adjusted değerlerdir; gerçek fiyat/ADP değildir.
>
> Dar test evreninde bir karşı takım, dört 1'e 1 paket ve iki nihai aday vardır.
> Ön elemede streaming kapalı, nihai adaylarda açıktır. Takassız kadro da aynı
> doğrulanmış temsili FA'yi alabilir; tüm oyuncuları yapay olarak koruma altına
> almak gerekmemiştir. Üç hamle hakkı ve sıfır tüketim açık test varsayımıdır;
> yararlı tek ekleme yeterliyse üç hak zorla kullanılmaz. Süreler yalnız bu
> küçük test koşusunun ölçümüdür; 14 takımlı tam tarama için hız garantisi değildir.
> Sonuçlar elle yazılmamış, yalnız başlık seviyeleri dokümana uyarlanmıştır.

Bu örnekte iki katılımcı takımda da **iki oyuncu** vardır. Bir oyuncu kesilmeden
FA alınabilmesi bu temsili açık yerlerden gelir; gerçek 13 kişilik kadrodan
gizlenmiş bir bırakma yoktur. Raporun aktif/bench ve açık yer tablosu bu
ayrımı gösterir. 13 kişilik kadroda bırakma varsa gerçek oyuncu adı yazılır.

### Takas fırsatı taraması

Takım: **Berk's Best Team**
Veri anı: 2026-10-30T12:00:00+00:00

4 paket hızlı modelde ele alındı; 4 paket streaming olmadan, 2 son aday nihai ayarlarla değerlendirildi.

Piyasa sınırına takılan hızlı aday: 0.

Koşullu fırsat sayısı: **2**.

#### 1. Berk's Best Team ↔ Philadelphia Sikers

Verilen: **Desmond Bane**

Alınan: **Darius Garland**

Sonuç: **Koşullu fırsat**

| Değerlendirme | Bizim Δ | Karşı takımın Δ |
|---|---:|---:|
| Ön eleme | +0.746 | +0.783 |
| Nihai | +0.527 | +0.783 |
| Nihai, iki sakatlık senaryosunun küçüğü | +0.527 | +0.783 |

Nihai karar referansı: `trade_plus_streaming`.

| Takım | Takas öncesi aktif/bench | Saf takas sonrası | Açık yer önce → sonra |
|---|---:|---:|---:|
| Berk's Best Team | 2 | 2 | 11 → 11 |
| Philadelphia Sikers | 2 | 2 | 11 → 11 |

##### Piyasa kontrolü

Durum: balanced_value

Kaynak (kullanıcı snapshot'ı): Controlled test market; not Yahoo data; yakalama zamanı: 2026-10-30T12:00:00+00:00.

Kaynaklı paket değerleri — verilen: 10.000; alınan: 10.000.


##### Berk's Best Team — kategori değişimi

| Kategori | Önce kazanma | Sonra kazanma | Δ kategori puanı |
|---|---:|---:|---:|
| PTS | %100.00 | %99.90 | -0.001 |
| REB | %42.67 | %96.43 | +0.528 |
| AST | %81.78 | %81.78 | +0.000 |
| STL | %66.62 | %66.62 | +0.000 |
| BLK | %62.74 | %62.74 | +0.000 |
| TOV | %19.01 | %19.01 | +0.000 |
| FG3M | %70.92 | %70.92 | +0.000 |
| FG_PCT | %50.00 | %50.00 | +0.000 |
| FT_PCT | %50.00 | %50.00 | +0.000 |

##### Philadelphia Sikers — kategori değişimi

| Kategori | Önce kazanma | Sonra kazanma | Δ kategori puanı |
|---|---:|---:|---:|
| PTS | %4.15 | %84.53 | +0.805 |
| REB | %99.97 | %97.59 | -0.022 |
| AST | %47.32 | %47.32 | +0.000 |
| STL | %43.86 | %43.86 | +0.000 |
| BLK | %42.76 | %42.76 | +0.000 |
| TOV | %46.19 | %46.19 | +0.000 |
| FG3M | %45.26 | %45.26 | +0.000 |
| FG_PCT | %50.00 | %50.00 | +0.000 |
| FT_PCT | %50.00 | %50.00 | +0.000 |

##### Nihai streaming hamleleri

Takassız:

- 2026-11-02: Luke Kennard alınır; mevcut boş kadro yeri kullanılır.

Takaslı:

- 2026-11-02: Luke Kennard alınır; mevcut boş kadro yeri kullanılır.

- Controlled fixture: names are real; ownership, forecasts, fixtures and market values are synthetic.
- Trade rules have not been confirmed.
- Streaming-assisted decision is conditional on the full dated action plan.
- Streaming uses bounded search; global optimality is not guaranteed.
- Future FA availability and waiver claims must be reverified before each action.
- At most one atomic acquisition/drop per day; no reacquisition within the horizon.
- IL placement stays fixed; future IL activation is not planned.
- Supplied weeks do not establish complete remaining-season coverage.

#### 2. Berk's Best Team ↔ Philadelphia Sikers

Verilen: **Desmond Bane**

Alınan: **Lauri Markkanen**

Sonuç: **Koşullu fırsat**

| Değerlendirme | Bizim Δ | Karşı takımın Δ |
|---|---:|---:|
| Ön eleme | +0.628 | +0.845 |
| Nihai | +0.503 | +0.845 |
| Nihai, iki sakatlık senaryosunun küçüğü | +0.503 | +0.845 |

Nihai karar referansı: `trade_plus_streaming`.

| Takım | Takas öncesi aktif/bench | Saf takas sonrası | Açık yer önce → sonra |
|---|---:|---:|---:|
| Berk's Best Team | 2 | 2 | 11 → 11 |
| Philadelphia Sikers | 2 | 2 | 11 → 11 |

##### Piyasa kontrolü

Durum: balanced_value

Kaynak (kullanıcı snapshot'ı): Controlled test market; not Yahoo data; yakalama zamanı: 2026-10-30T12:00:00+00:00.

Kaynaklı paket değerleri — verilen: 10.000; alınan: 10.000.


##### Berk's Best Team — kategori değişimi

| Kategori | Önce kazanma | Sonra kazanma | Δ kategori puanı |
|---|---:|---:|---:|
| PTS | %100.00 | %99.79 | -0.002 |
| REB | %42.67 | %94.03 | +0.504 |
| AST | %81.78 | %81.78 | +0.000 |
| STL | %66.62 | %66.62 | +0.000 |
| BLK | %62.74 | %62.74 | +0.000 |
| TOV | %19.01 | %19.01 | +0.000 |
| FG3M | %70.92 | %70.92 | +0.000 |
| FG_PCT | %50.00 | %50.00 | +0.000 |
| FT_PCT | %50.00 | %50.00 | +0.000 |

##### Philadelphia Sikers — kategori değişimi

| Kategori | Önce kazanma | Sonra kazanma | Δ kategori puanı |
|---|---:|---:|---:|
| PTS | %4.15 | %89.87 | +0.857 |
| REB | %99.97 | %98.64 | -0.012 |
| AST | %47.32 | %47.32 | +0.000 |
| STL | %43.86 | %43.86 | +0.000 |
| BLK | %42.76 | %42.76 | +0.000 |
| TOV | %46.19 | %46.19 | +0.000 |
| FG3M | %45.26 | %45.26 | +0.000 |
| FG_PCT | %50.00 | %50.00 | +0.000 |
| FT_PCT | %50.00 | %50.00 | +0.000 |

##### Nihai streaming hamleleri

Takassız:

- 2026-11-02: Luke Kennard alınır; mevcut boş kadro yeri kullanılır.

Takaslı:

- 2026-11-02: Luke Kennard alınır; mevcut boş kadro yeri kullanılır.

- Controlled fixture: names are real; ownership, forecasts, fixtures and market values are synthetic.
- Trade rules have not been confirmed.
- Streaming-assisted decision is conditional on the full dated action plan.
- Streaming uses bounded search; global optimality is not guaranteed.
- Future FA availability and waiver claims must be reverified before each action.
- At most one atomic acquisition/drop per day; no reacquisition within the horizon.
- IL placement stays fixed; future IL activation is not planned.
- Supplied weeks do not establish complete remaining-season coverage.

#### Kapsam ve ölçüm

Ön eleme: 0.272 sn; son değerlendirme: 0.275 sn; toplam: 0.590 sn.

- Controlled fixture: names are real; ownership, forecasts, fixtures and market values are synthetic.
- Arama sınırlıdır; negatif hızlı puanlar ve kısa liste dışında kalan paketler için optimum iddiası yoktur.
- Ön eleme streaming kullanmaz; yalnız son adaylar aynı nihai ayarlarla karşılaştırılır.
- Piyasa göstergeleri kategori puanına eklenmez; menajer kabul olasılığı değildir.
- Otomatik arama IL oyuncularını taşımaz; mevcut IL yerleşimini korur.
- Karşı takımın gelecekteki streaming hamleleri tahmin edilmez.
- Paketler birbirinin alternatifidir; birlikte uygulanacak takas listesi değildir.


### Karşı teklif araması

Takım: **Berk's Best Team**
Veri anı: 2026-10-30T12:00:00+00:00

2 paket hızlı modelde ele alındı; 2 paket streaming olmadan, 2 son aday nihai ayarlarla değerlendirildi.

Piyasa sınırına takılan hızlı aday: 0.

#### Mevcut teklif

Berk's Best Team veriyor: **Desmond Bane**; alıyor: **Lauri Markkanen**.

Mevcut teklifin nihai katkısı: +0.503 kategori puanı.

Mevcut teklif piyasa kontrolü: balanced_value


Koşullu fırsat sayısı: **1**.

#### 1. Berk's Best Team ↔ Philadelphia Sikers

Verilen: **Desmond Bane**

Alınan: **Darius Garland**

Sonuç: **Koşullu fırsat**

| Değerlendirme | Bizim Δ | Karşı takımın Δ |
|---|---:|---:|
| Ön eleme | +0.746 | +0.783 |
| Nihai | +0.527 | +0.783 |
| Nihai, iki sakatlık senaryosunun küçüğü | +0.527 | +0.783 |

Nihai karar referansı: `trade_plus_streaming`.

| Takım | Takas öncesi aktif/bench | Saf takas sonrası | Açık yer önce → sonra |
|---|---:|---:|---:|
| Berk's Best Team | 2 | 2 | 11 → 11 |
| Philadelphia Sikers | 2 | 2 | 11 → 11 |

Mevcut teklife göre temkinli iyileşme: +0.024.

##### Piyasa kontrolü

Durum: balanced_value

Kaynak (kullanıcı snapshot'ı): Controlled test market; not Yahoo data; yakalama zamanı: 2026-10-30T12:00:00+00:00.

Kaynaklı paket değerleri — verilen: 10.000; alınan: 10.000.


##### Berk's Best Team — kategori değişimi

| Kategori | Önce kazanma | Sonra kazanma | Δ kategori puanı |
|---|---:|---:|---:|
| PTS | %100.00 | %99.90 | -0.001 |
| REB | %42.67 | %96.43 | +0.528 |
| AST | %81.78 | %81.78 | +0.000 |
| STL | %66.62 | %66.62 | +0.000 |
| BLK | %62.74 | %62.74 | +0.000 |
| TOV | %19.01 | %19.01 | +0.000 |
| FG3M | %70.92 | %70.92 | +0.000 |
| FG_PCT | %50.00 | %50.00 | +0.000 |
| FT_PCT | %50.00 | %50.00 | +0.000 |

##### Philadelphia Sikers — kategori değişimi

| Kategori | Önce kazanma | Sonra kazanma | Δ kategori puanı |
|---|---:|---:|---:|
| PTS | %4.15 | %84.53 | +0.805 |
| REB | %99.97 | %97.59 | -0.022 |
| AST | %47.32 | %47.32 | +0.000 |
| STL | %43.86 | %43.86 | +0.000 |
| BLK | %42.76 | %42.76 | +0.000 |
| TOV | %46.19 | %46.19 | +0.000 |
| FG3M | %45.26 | %45.26 | +0.000 |
| FG_PCT | %50.00 | %50.00 | +0.000 |
| FT_PCT | %50.00 | %50.00 | +0.000 |

##### Nihai streaming hamleleri

Takassız:

- 2026-11-02: Luke Kennard alınır; mevcut boş kadro yeri kullanılır.

Takaslı:

- 2026-11-02: Luke Kennard alınır; mevcut boş kadro yeri kullanılır.

- Controlled fixture: names are real; ownership, forecasts, fixtures and market values are synthetic.
- Trade rules have not been confirmed.
- Streaming-assisted decision is conditional on the full dated action plan.
- Streaming uses bounded search; global optimality is not guaranteed.
- Future FA availability and waiver claims must be reverified before each action.
- At most one atomic acquisition/drop per day; no reacquisition within the horizon.
- IL placement stays fixed; future IL activation is not planned.
- Supplied weeks do not establish complete remaining-season coverage.

#### 2. Berk's Best Team ↔ Philadelphia Sikers

Verilen: **Jarrett Allen**

Alınan: **Lauri Markkanen**

Sonuç: **Öneri dışında**

| Değerlendirme | Bizim Δ | Karşı takımın Δ |
|---|---:|---:|
| Ön eleme | +0.469 | +0.889 |
| Nihai | +0.452 | +0.889 |
| Nihai, iki sakatlık senaryosunun küçüğü | +0.452 | +0.889 |

Nihai karar referansı: `trade_plus_streaming`.

| Takım | Takas öncesi aktif/bench | Saf takas sonrası | Açık yer önce → sonra |
|---|---:|---:|---:|
| Berk's Best Team | 2 | 2 | 11 → 11 |
| Philadelphia Sikers | 2 | 2 | 11 → 11 |

Mevcut teklife göre temkinli iyileşme: -0.050.

##### Piyasa kontrolü

Durum: balanced_value

Kaynak (kullanıcı snapshot'ı): Controlled test market; not Yahoo data; yakalama zamanı: 2026-10-30T12:00:00+00:00.

Kaynaklı paket değerleri — verilen: 10.000; alınan: 10.000.


##### Berk's Best Team — kategori değişimi

| Kategori | Önce kazanma | Sonra kazanma | Δ kategori puanı |
|---|---:|---:|---:|
| PTS | %100.00 | %99.69 | -0.003 |
| REB | %42.67 | %88.91 | +0.455 |
| AST | %81.78 | %81.78 | +0.000 |
| STL | %66.62 | %66.62 | +0.000 |
| BLK | %62.74 | %62.74 | +0.000 |
| TOV | %19.01 | %19.01 | +0.000 |
| FG3M | %70.92 | %70.92 | +0.000 |
| FG_PCT | %50.00 | %50.00 | +0.000 |
| FT_PCT | %50.00 | %50.00 | +0.000 |

##### Philadelphia Sikers — kategori değişimi

| Kategori | Önce kazanma | Sonra kazanma | Δ kategori puanı |
|---|---:|---:|---:|
| PTS | %4.15 | %93.54 | +0.893 |
| REB | %99.97 | %99.49 | -0.004 |
| AST | %47.32 | %47.32 | +0.000 |
| STL | %43.86 | %43.86 | +0.000 |
| BLK | %42.76 | %42.76 | +0.000 |
| TOV | %46.19 | %46.19 | +0.000 |
| FG3M | %45.26 | %45.26 | +0.000 |
| FG_PCT | %50.00 | %50.00 | +0.000 |
| FT_PCT | %50.00 | %50.00 | +0.000 |

##### Nihai streaming hamleleri

Takassız:

- 2026-11-02: Luke Kennard alınır; mevcut boş kadro yeri kullanılır.

Takaslı:

- 2026-11-02: Luke Kennard alınır; mevcut boş kadro yeri kullanılır.

- Karşı teklif mevcut teklifi yeterince iyileştirmiyor.
- Controlled fixture: names are real; ownership, forecasts, fixtures and market values are synthetic.
- Trade rules have not been confirmed.
- Streaming-assisted decision is conditional on the full dated action plan.
- Streaming uses bounded search; global optimality is not guaranteed.
- Future FA availability and waiver claims must be reverified before each action.
- At most one atomic acquisition/drop per day; no reacquisition within the horizon.
- IL placement stays fixed; future IL activation is not planned.
- Supplied weeks do not establish complete remaining-season coverage.

#### Kapsam ve ölçüm

Ön eleme: 0.132 sn; son değerlendirme: 0.434 sn; toplam: 0.732 sn.

- Controlled fixture: names are real; ownership, forecasts, fixtures and market values are synthetic.
- Arama sınırlıdır; negatif hızlı puanlar ve kısa liste dışında kalan paketler için optimum iddiası yoktur.
- Ön eleme streaming kullanmaz; yalnız son adaylar aynı nihai ayarlarla karşılaştırılır.
- Piyasa göstergeleri kategori puanına eklenmez; menajer kabul olasılığı değildir.
- Otomatik arama IL oyuncularını taşımaz; mevcut IL yerleşimini korur.
- Karşı takımın gelecekteki streaming hamleleri tahmin edilmez.
- Paketler birbirinin alternatifidir; birlikte uygulanacak takas listesi değildir.

## Takas paneli

Proje klasöründe `.\.venv\Scripts\python.exe -m src.trade_panel` komutunu çalıştırıp tarayıcıda http://127.0.0.1:8766 adresini açın. Takımları ve bir veya iki oyuncuyu gerçek adlarıyla seçin; yürürlük tarihini belirtip **Takası analiz et** düğmesine basın. Tarih boşsa ilk tam gelecek hafta koşullu senaryosu kullanılır. **Bekleyen teklifler** güncel Yahoo kaydını değerlendirir; **Fırsatları tara** isteğe bağlı geniş taramayı başlatır. Rapor Markdown olarak indirilebilir. Terminali Ctrl+C ile kapatabilirsiniz.

Panel yalnız yerel bilgisayarda dinler; Yahoo senkronunu kendiliğinden çalıştırmaz. Mevcut teklif analizi kaynakları eksikse nedenini gösterir. Canlı Yahoo teklif HTML yapısı henüz gerçek bir bekleyen teklif üzerinde doğrulanmadı; doğrulanamayan liste boş kabul edilmez.

Aşama 5 entegrasyon doğrulaması: 118 Python ve 15 JavaScript testi geçti. Panel için sözdizimi ve Ruff kontrolleri geçti; tarayıcı etkileşim doğrulaması henüz yapılmadı.


## Yenilenen panel ve uclu takas

Panelde **Takas olustur** sekmesinden **2 takim** veya **3 takim** secilir. Oyuncular arama alanindan bulunup onay kutusuyla eklenir; uc takimli senaryoda her oyuncunun hedef takimi ayrica secilir. Sag tarafta anlik paket ozeti gorunur. Gereken kadro birakmalari takim kartindaki acilir bolumden secilir. Sonuclar takim kartlari ve kategori tablosuyla gosterilir; ayrintili rapor indirilebilir.

Iki takim arasinda her taraf 1-4 oyuncu verebilir. Uc takimli analizde her takim 1-4 oyuncu verir ve alir; tum hareketler ayni anda uygulanir. Sahiplik, tekrar eden oyuncu, kadro kapasitesi, koruma ve gercek fikstur kontrol edilir. Uc takimli ilk surum saf takas ve zorunlu birakmalari hesaplar; FA/streaming, playoff katilim etkisi ve otomatik uclu firsat taramasi dahil degildir. IL oyunculari, acik takas sonrasi yerlesim secimiyle tasinabilir.

CLI icin proposal.transfers listesi kullanilir. Her hareketin alanlari: from_team, to_team ve yahoo_player_id. snapshot_id ve effective_date yine zorunludur. Ornek dongu: A oyuncusunu B'ye, B oyuncusunu C'ye, C oyuncusunu A'ya gonderir. Kanonik takim/oyuncu kimlikleri mevcut --inspect cikti kaynagindan alinir.

Panel sunucusu zaten aciksa Ctrl+C ile kapatip yeniden `python -m src.trade_panel` calistirin; ardindan tarayiciyi yenileyin. Python testlerinin tamami (122) gecti; son uclu senaryo/panel regresyonlari ayrica dogrulandi. JavaScript sozdizimi kontrol edildi. Yerel tarayici onizlemesi baglanti/aktif kullanici etkilisimi nedeniyle tamamlanamadi.

### Fırsat elemesi, kadro yenileme ve etki notu

Kartlar, tüm kontrolleri geçen `opportunities` ile yalnız iki taraflı model
eşiklerini geçen `review_opportunities` listelerini ayrı etiketlerle gösterir.
Elenen `finalists` paketleri karta dönüştürülmez; gerekçeleri ayrıntılı raporda
tutulur. Kaynaklı piyasa kontrolü eksik uygun paketler **model adayı — piyasa
incelemesi gerekli** olarak görünür. Sayısal katkı, başka menajerin kabul olasılığı değildir.
Tarama, gizli kalan manuel takım seçimini kullanmaz; yapılandırılmış kendi takımına
(`trade_automation.json` içindeki `our_team`, varsayılan kanonik 7) bağlıdır ve
ekranda takım adı görünür. Sunucu başka takım adına gelen tarama isteğini reddeder.

Başarılı Yahoo Browser senkronu yerel kadro kaydını değiştirdiğinde panel 30 saniyelik
yerel sürüm kontrolünde veya pencere yeniden odaklandığında kadroları yeniler.
**Kadroları yenile** düğmesi de kullanılabilir. Bu kontroller Yahoo'ya istek yapmaz.
Kadro değişirse eski seçimler/sonuçlar temizlenir. Analiz başlangıcında ve sonuç
gösterilmeden önce sürüm kontrol edilir; eski kadroyla üretilen sonuç güncelmiş gibi
gösterilmez. Yeni kodu ilk kez kullanmak için panel sunucusunu yeniden başlatmak gerekir.

Sakatlık etiketi takasa engel değildir. IL oyuncusu seçildiğinde **IL'de kalsın**
veya **Aktif kadroya geçsin** seçilir. Bu, karşılaştırılan senaryonun kadro
yerleşimidir; Yahoo kadrosunu değiştirmez. İki ve üç takımlı senaryolarda sahiplik,
pozitif IL uygunluğu, iki IL yeri ve 13 aktif/bench sınırı korunur.

Kategori puanının yanında gösterilen **etki notu**, saf takasın muhafazakâr haftalık
ortalama farkından hesaplanır: `not = sınırla(5 + 5 × Δ / hafta, 0, 10)`.
5/10 nötrdür; dört haftada +0.8 kategori puanı 6/10, −0.8 puan 4/10 eder.
Bu açıklayıcı bir ölçek olup kalibre edilmiş güven, draft sıralaması veya kabul
olasılığı değildir. FA/streaming içeren nihai kararın referansı ayrıca gösterilir.

### 1 Kasım: manuel analiz ve fırsat taramasının tutarlılığı

Düzeltmeler bütün oyuncular/paketler için geçerlidir; oyuncu adına özel filtre yoktur.
Seçilen bir ile dört oyuncu **tam giden paket** kabul edilir. Seçim tekli alt
paketlere bölünmez veya sessizce başka oyuncularla genişletilmez. Geçersiz,
başka takıma ait, korumalı veya otomatik aramanın kapsamı dışındaki IL seçimi
açık hata verir. Takım başına dörtten fazla oyuncu verilemez veya alınamaz.
Oyuncu seçilmeden yapılan standart otomatik tarama 1–2 oyunculuk paketleri
araştırır. Üç veya dört oyuncu seçildiğinde bu tam paket ve en fazla bir
oyunculuk kadro farkı olan karşı paketler aranır; kapsam ekranda belirtilir.

Tam giden paket ve tek hedef seçildiğinde en fazla 200 karşı paketin tamamı
streaming kapalı ön değerlendirmeye girer. Üç nihai aday seçilirken önce iki
taraflı eşikleri geçen paketlere öncelik verilir; salt bizim kazancımızla
sıralama yapılmaz. Lig genelindeki sınırlı tarama bütün olasılıkları tükettiğini
iddia etmez; kapsam ve sayılar ekranda gösterilir. Piyasa kaydı yokluğu model
faydasını sıfırlamaz: yalnız model eşiklerini geçen paketler ayrı inceleme
listesine girer. Karşı tarafın kayıp toleransı ve veri yeterliliği korunur.

Manuel sütun sırası değişse de Berk'in dahil olduğu takasın karar bakış açısı
Berk'e sabitlenir; hangi takım açısından karar verildiği ekranda belirtilir.
Arama oyuncu seçimleri ve hedefi sekme değişiminde korunur; gerçek kadro değişimi
olunca temizlenir.

Gerçek 14 kadro ve 2–29 Kasım 2026 dört haftalık fikstürle kontrol:

| Verilen tam paket | Alınan | Berk Δ | SILE BULLS Δ | Sonuç |
|---|---|---:|---:|---|
| James Harden + Jabari Smith Jr. | Donovan Mitchell + Derrick White | +0.634 | −0.091 | Model adayı; piyasa incelemesi gerekli |
| James Harden + Jabari Smith Jr. | Donovan Mitchell + Payton Pritchard | +0.207 | +0.314 | Model adayı; piyasa incelemesi gerekli |

İlk paketin manuel, ön eleme ve nihai arama puanları birebir eşleşti. Eşikler
bizim için +0.200, karşı taraf için −0.200 idi. 91 karşı paket ön değerlendirme,
3 paket nihai değerlendirme gördü; hesap 202.83 saniyede tamamlandı. Bu süre
tek hedef ve sabit paket kapsamına aittir; bütün ligin tüm paketleri için süre
veya optimum garantisi değildir. Kaynak kayıt/hash ve sayısal kontrol:
`reports/trade_search/panel_consistency_review.json`. Tüm 137 Python testi ve
genişletilen panel JavaScript regresyonu geçti; Ruff kontrolleri temiz.

### Eşik, arama kapsamı ve matematik denetimi

`0.200` bir oran veya istatistiksel anlamlılık sınırı değildir. Haftalık `0.05`
kategori puanı tercihinin dört haftalık toplamıdır. Küçük etkileri varsayılan
listeden ayıran ürün tercihidir; geçmiş sonuçlardan kalibre edilmemiştir.
Panelde **Haftalık en az kazancım** ve **Rakibin haftalık kayıp toleransı**
alanlarından değiştirilebilir. Oyuncu seçmemek bu sayısal filtreleri kaldırmaz.
Kazanç filtresi `0` olduğunda çok küçük pozitif etkiler de değerlendirilir.

**Standart** arama 40 tam ön değerlendirme / 3 nihai plan; **Geniş** arama
80 / 8 bütçesi kullanır. Sabit giden paket + tek hedefte küçük havuzlar ayrıca
tam ön değerlendirmeye alınabilir. Nihai hesap sayısı gösterilecek bütün
sonuçlara üst sınır değildir: eşikleri geçen ama nihai planı hesaplanmamış
paketler ayrı **ön aday** listesinde, incelenen bütün paketler ise puanları,
aşamaları ve gerekçeleriyle açılır tabloda ve Markdown raporunda gösterilir.
Ön aday, tamamlanmış FA/streaming önerisi sayılmaz.

Gerçek kadroyla seçimsiz standart lig taraması da yeniden çalıştırıldı:
104.104 hızlı aday, 40 tam ön değerlendirme, 3 nihai hesap, 1 nihai model
adayı, 0 ek ön aday. Bu 40 paket içinde tek uygun aday vardı; ligdeki bütün
olası paketlerin tam modelle değerlendirildiği anlamına gelmez. Çalışma yaklaşık
130 saniyede tamamlandı. Çıktı: `reports/trade_search/panel_audit.md`; sayısal
kontroller mevcut `panel_consistency_review.json` kaydının `unrestricted_audit`
alanındadır.

Rapordaki ortak teknik koşullar bir kez, Türkçe gösterilir. Bilinmeyen hamle
bütçesinin önce/sonra ve hafta bazlı tekrarları tek cümleye indirildi. Bu koşul
gerçekte eklemeleri engelliyorsa bilgi saklanmaz. Ham notlar JSON çıktısında kalır.
Gerçek koşuda 24 İngilizce bütçe satırı, Türkçe tek açıklamaya dönüştü.

Gemini değişiklikleri ayrıca denetlendi ve şu somut hatalar düzeltildi:

- Yerel NBA sakatlık durumu tek başına Yahoo IL hakkı vermiyor. Mevcut IL
  yerleşimi ve sağlayıcıdan alınmış uygunluk kanıtı kullanılıyor; QUESTIONABLE
  oyuncu kendiliğinden IL'ye yerleştirilmiyor. IL/IL+ türleri ayrı modellenmediği
  için gerçek lig kuralı doğrulaması hâlâ ayrıca gereklidir.
- Doğrulanmış Yahoo pozisyonlarına yanlış yaklaşık-pozisyon uyarısı yazılmıyor.
- İki ve üç takımlı manuel motor aynı dört oyuncu tavanını kullanıyor; üç
  takımlı döngüde toplam 12 hareket destekleniyor. Beşinci oyuncu reddediliyor.
- Üç takımlı manuel karardaki gizli haftalık `0.05` eşiği kaldırıldı. Arama
  tercihiyle manuel takasın işaret temelli karar mantığı birbirine karıştırılmıyor.
- “Sakatlık kaynaklı ek dakika dağıtımı kapalı” senaryosu sakatlıkları veya
  dönüş tarihlerini kaldırmaz; takım arkadaşlarına dağıtılan ek rol/dakika
  varsayımını kapatır. Paneldeki eski belirsiz ifade düzeltildi.

Beklenen kategori puanı `Σ(P(galibiyet)+0.5P(beraberlik))`, top kaybında ters
yön, yüzde kategorilerinde hacim ağırlığı, kategori farklarının toplamı ve aynı
eşleşmedeki iki takımın puan toplamının 9 olması regresyonlarla kontrol edildi.
İki takas tarafı farklı fantasy rakipleriyle oynadığı için ikisinin birden
kazanması matematiksel çelişki değildir. Bu kontroller hesap tutarlılığını
doğrular; olasılıkların ampirik kalibrasyonu veya tahmin isabeti iddiası değildir.

### 1 Kasım: geniş arama kapsamı ve oyuncu verisinin kaynağı

Kullanıcının iki 80/8 raporu incelendi. Genel rapordaki 80 tam ön değerlendirmede
Jarrett Allen 42 pakette (%52,5), Precious Achiuwa 46 pakette yer alıyordu;
Harden, Maxey, Bane ve Hart ise bu aşamaya girmemişti. Bunun nedeni oyunculara
sıranın gelmemesi değildi: hızlı sıralamanın dar aday havuzu benzer paketleri
üstte topluyordu. Harden + Jabari / SILE BULLS raporunda ise sabit giden paketin
91 karşı seçeneğinin tamamı ön değerlendirmeye alınmıştı.

Genel tarama artık yüksek hızlı puan ile giden oyuncu/paket çeşitliliği arasında
bütçe paylaştırır. Rakip ve paket türü dağılımı korunur; oyuncu adına özel kural
yoktur. Aynı gerçek kayıtta 104.104 hızlı adaydan seçilen 80 paketin 41'i kalite,
39'u kapsam önceliğiyle geldi. Aktif kadrodaki 13 oyuncunun tamamı kapsandı:
Allen 30, Achiuwa 22, Harden ve Jabari yedişer pakette yer aldı. Ardından aynı
80/8 koşusu tüm hesaplarıyla 202,43 saniyede tamamlandı: 80 tam ön değerlendirme,
8 nihai hesap, 3 model adayı, 0 hata. Kullanıcının raporuyla aynı haftalık
0,05 kazanç ve 0,08 karşı taraf kayıp toleransı kullanıldı. Nihai sonuçlarda
eşit oyuncu dağılımı veya tüm ligde optimum garantisi verilmez. Panel gerçekte
incelenen paketlerin oyuncu dağılımını da gösterir.

| Verilen | Alınan | Karşı takım | Bizim muhafazakâr Δ | Karşı takımın muhafazakâr Δ |
|---|---|---|---:|---:|
| Neemias Queta | Keyonte George | FatihTerimSpor | +0.515 | +0.321 |
| Jarrett Allen + Precious Achiuwa | Derrick White + Payton Pritchard | SILE BULLS | +0.334 | −0.229 |
| Jarrett Allen + Precious Achiuwa | CJ McCollum + LaMelo Ball | abu dhabi camels | +0.300 | +0.716 |

Bu üç sonuç mevcut eski kaynaklarla hesaplanan model adaylarıdır; piyasa
makullüğü doğrulanmış teklif değildir. Yeni sağlık/pozisyon senkronu puanları
değiştirebilir. Yeniden üretilen rapor: `reports/trade_search/panel_audit.md`.

Ana tahmin ve takas motoru aynı Yahoo sağlık/pozisyon çözümleyicisini kullanır.
Güncel ve doğrulanmış Yahoo sağlık gözlemi eski sakatlık kaydını geçersiz kılabilir;
daha yeni sakatlık gözlemi korunur. Eski okuyucunun varsayılan `HEALTHY` alanı
tek başına sağlık kanıtı sayılmaz. Güncel Yahoo oynatılabilir pozisyonları günlük
kadro çözücüsüne aktarılır; NBA rol pozisyonları dakika/rotasyon hesabında ayrı
tutulur. Seçili `C` veya `UTIL` kadro slotu, pozisyon uygunluğu olarak kullanılmaz.
Browser ve OAuth okuyucuları pozisyonu, durum kanıtını ve okuma zamanını saklar.

İlk denetimde kullanılan eski kayıtta Hayes'in pozisyon uygunluğu yok ve `HEALTHY` bilgisi kanıtsızdı;
eski sakatlık veritabanında 28 Ekim tarihli `QUESTIONABLE` gözlemi bulunuyor.
Bu nedenle o veriden yalnız `C`/sağlıklı sonucu uydurulmadı. Yeni okuyucuyla
senkron gerekiyordu; aşağıdaki denetimde yeni kayıt doğrulandı. Panel kaynakları/tarihleri ve gerektiğinde **Yahoo kaydı
yenilenmeli** bilgisini gösterir; aynı değerleri kullanan ana model ve takas motoru
gerçek yerel veride karşılaştırıldı. Kadro dışında sakatlık/pozisyon kaynağı
değişirse de panel sürümü değişir; eski seçim ve sonuçlar güncelmiş gibi korunmaz.
Kaydın 24 saatlik geçerlilik süresi dolduğunda da sürüm değişir; yalnız saat
ilerlediği için her dakika gereksiz yenileme yapılmaz. Panel ve motor aynı
başlangıç zamanı ve aynı güncellik kuralıyla yüklenir.

İlk sadeleştirmedeki sözel önizleme, kullanıcı geri bildirimiyle aşağıda açıklanan
sayısal sunumla değiştirildi. Kategori farkı ve 10 üzerinden not yeniden ana
çıktıda; arama derinliğinin sayısal açıklaması da sürekli görünür.

Kaynak ve kapsam doğrulaması mevcut
`reports/trade_search/panel_consistency_review.json` dosyasının
`source_and_coverage_audit` ve `diversified_wide_audit` bölümlerindedir. Mevcut
kullanıcı kayıtları değiştirilmedi; Yahoo senkronu veya bildirim gönderimi çalıştırılmadı.

Doğrulama: 159 testlik Python paketi geçti; sonradan eklenen IL ve süre dolumu
regresyonlarıyla birlikte ilgili 74 test yeniden geçti (toplam 161 testlik
kapsam). 15 JavaScript fixture testi, panelin JavaScript çalışma kontrolleri ve
Ruff temiz. Canlı görsel önizleme iki tarayıcı/masaüstü aracında da
`failed to write kernel assets` hatası nedeniyle açılamadı; görsel doğrulama
yapılmış sayılmıyor. Yeni kaynak kanıtlarını toplamak için çalışan Yahoo Browser
köprüsü ve panelin yeniden başlatılması gerekiyordu; bu işlem kullanıcı tarafından
tamamlandı ve yeni kayıt aşağıda doğrulandı.

### 1 Kasım: doğrulanmış yeni Yahoo kaydı ve sayısal önizleme

09:56 UTC Yahoo senkronu sonrasında 14 takım / 201 oyuncunun tamamında güncel
sağlık kanıtı, kesin Yahoo pozisyonu ve oyuncu bazlı okuma zamanı doğrulandı.
Dağılım: 166 sağlıklı, 3 questionable, 31 out, 1 probable. Aynı başlangıç
zamanıyla yüklenen ana model ve takas modelinde sağlık, pozisyon, NBA rolü,
kadro sahipliği ve IL açısından **sıfır tutarsızlık** bulundu. Hayes iki modelde
de `HEALTHY` / yalnız `C`; NBA rol pozisyonu ayrı `C-F` olarak korunuyor.
Kaynak dosyalarına dokunulmadı; ayrıntı mevcut denetim JSON dosyasının
`refreshed_source_audit` alanında. Yeniden Yahoo okuması gerekmiyor.

Kartlarda beklenen kategori puanı birimi açıklanır:
`Σ[P(kazanma) + 0.5 × P(beraberlik)]`. Her kategori haftada 0–1, dokuz kategori
toplamı haftada 0–9 puandır. Toplam fark, hafta başına ortalama fark ve etki
notu birlikte gösterilir. Örneğin dört haftada `+0.634`, haftada ortalama
`+0.159` kategori puanı ve `5.8/10` etki notu eder. Not bir açıklama ölçeğidir;
istatistiksel güven veya kabul olasılığı değildir.

Normal senaryonun önce → sonra toplamları ve normal farkı ayrı, muhafazakâr
fark `min(normal Δ, sakatlık kaynaklı ek dakika dağıtımı kapalı Δ)` olarak ayrı
gösterilir. Muhafazakâr fark normal başlangıç puanına eklenip sahte bir son
toplam oluşturulmaz. FA/streaming kararında iki taraf da kararın kullandığı
aynı karşılaştırmadan alınır; saf takas toplamlarıyla karıştırılmaz. Panelin
notları da artık bu karar referansına bağlıdır. Ön adaylarda yalnız doğrulanmış
hafta sayısı varsa haftalık değer hesaplanır; bekleyen/eksik analizlere varsayılan
sıfır veya 5/10 notu yazılmaz.

**80 / 8** seçiminin altında sürekli görünen küçük açıklama:
80 paket hızlı sıralamadan sonra gerçek fikstür, günlük kadro ve kategori
etkileriyle karşılaştırılır. Bu 80 içinden en fazla sekizi boş kadro yeri ve
varsa FA/streaming planlarıyla ayrıntılı incelenir. Sekiz öneri çıkması
gerekmez. Sabit giden paket + tek hedefte en fazla 200 uygun karşı paket varsa
tamamının ön değerlendirmeye alınabilmesi istisnası korunur. Aynı açıklama
standart 40 / 3 seçimine göre güncellenir.

Sakatlık değerlendirmesi değişmedi: OUT günlerde katkı sıfır; QUESTIONABLE
maç katkısı mevcut politikada %52 oynama olasılığıyla ağırlıklıdır. Bilinen
dönüş tarihi varsa dönüşten itibaren kademeli katkı kullanılır. OUT durumunda
dönüş tarihi bilinmiyorsa analiz ufku boyunca katkı sıfır kalabilir; bu kısa
dönem takım katkısı, oyuncunun sezonluk veya piyasa değerinin tamamı değildir.

Doğrulama: 162 Python testi, 15 JavaScript fixture testi, panelin sayısal
önizleme çalışma kontrolü ve Ruff geçti. FA/streaming referansı, iki tarafın
aynı karşılaştırmadan alınması, normal toplam/muhafazakâr fark ayrımı ve
hafta bilgisi olmayan analizlerde not üretilmemesi kontrol edildi. Canlı
tarayıcı önizleme aracı aynı `failed to write kernel assets` hatasıyla açılamadı.
Yeni sunum için yalnız panel sunucusunu yeniden başlatmak yeterli; Yahoo
köprüsünü veya bookmarklet senkronunu tekrar çalıştırmak gerekmiyor.

Yeni senkronla 2–29 Kasım dönemi için 80/8 genel tarama tekrar tamamlandı:
104.104 hızlı aday, 80 ön değerlendirme, 8 nihai hesap, 1 model adayı, 0 hata.
411,35 saniyelik süre testlerle eşzamanlı ölçüldü; izole performans karşılaştırması
değildir. Aktif 13 oyuncunun tamamı incelendi; Allen 23, Queta 21, Harden ve
Jabari yedişer pakette yer aldı. Önceki üç adaylı rapor eski sağlık/pozisyon
kaydına aittir; yeni çıktının yerine kullanılamaz.

| Verilen | Alınan | Karşı takım | Bizim muhafazakâr Δ | Karşı takımın muhafazakâr Δ |
|---|---|---|---:|---:|
| Jaxson Hayes + Neemias Queta | Grayson Allen + Tyler Herro | Samurai Strikers | +0.254 | −0.076 |

Bu model adayı piyasa incelemesi gerektirir. Bizim normal toplamımız
24.559 → 24.814; haftalık muhafazakâr fark +0.064 ve etki notu 5.3/10.
Karşı takımda normal fark +0.084 iken ek dakika dağıtımı kapalı fark −0.076
olduğu için muhafazakâr değer −0.076, haftalık ortalama −0.019, not 4.9/10.
Kart, olumlu normal sonuçla bu daha düşük değeri birbirine karıştırmaz.
Sekiz nihai paketin tümünde önizleme puanları karar motoruyla eşleşti.

Yeni çıktı mevcut `reports/trade_search/panel_audit.md` dosyasında; sayısal
denetim JSON dosyasındaki `refreshed_wide_audit` alanında tutulur. Gerçek
adayın önizlemesi JavaScript üzerinden de toplam, haftalık fark ve etki notu
açısından doğrulandı.

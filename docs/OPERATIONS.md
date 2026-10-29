# Veri ve işletim

## Ağsız rapor ve canlı senkronizasyon

`python -m src.forecast` mevcut Parquet/JSON/SQLite önbelleklerini okur;
sakatlık veritabanını salt okunur açar. API çağrısı veya bildirim göndermez.
Tarihli fikstür zorunludur. Canlı skor 24 saatten eskiyse, farklı Eastern
günündeyse veya isabet/deneme alanları geçersizse reddedilir. Bu durumda
yalnızca kalan maç projeksiyonu verilir; hafta içi add/drop önerileri bekletilir.

Günlük motorun canlı birleştirmesi maç öncesi modundadır: bugünün ilk NBA
maçı başladıysa kısmi skor üzerine tam maç eklememek için bekletilir. Kesin
saat ve aynı Eastern gününe ait saat gözlemi gerekir. Bulut bunu yeniler;
yerelde yalnızca fikstür saatlerini yenilemek için
`python -m src.game_clock` kullanılır. Bu komut bildirim göndermez ve
kimliği/tarihi uyuşmayan fikstürün üzerine yazmaz.

`python -m src.cloud_sync` canlı veri indirir, runtime önbelleklerini günceller
ve ayarlı Telegram/Discord bildirimlerini gönderir. Kod kontrolü için bu komut
yerine `forecast` ve testleri kullanın.

Kaynaklar: NBA Stats maç günlükleri/fikstür, resmi NBA sakatlık PDF'leri, ESPN
sakatlık yanıtı ve Yahoo kadro/skor ekranları veya OAuth API'si. ESPN yanıtında
yer almayan takımların sakatlıkları otomatik temizlenmez. Eksik PDF raporları
health check ile karantinaya alınır. Önbellek güncelliği model güveni değildir.

Geçmiş veri `src.data_fetcher.fetch_and_process_season("2025-26")` ile alınabilir.
`python -m src.data_fetcher` mevcut 2026–27 kadro/fikstür/preseason verilerini
yeniler. Yeni sezon için bu adaptörün sezonu açıkça güncellenmelidir.

## Yahoo ve kimlik bilgileri

`python -m src.yahoo_browser_sync` localhost:8765 üzerinde çalışır. Sayfadaki
bookmarklet giriş yapılmış Yahoo sekmesinden kadro, IL, işlem ve skoru yerel
köprüye iletir. Bu işlem canlı pipeline ve ayarlı bildirimleri tetikleyebilir.

Add/drop adayları artık yalnızca Yahoo boşta oyuncu sayfasında açıkça
FA/waiver olarak doğrulanan oyunculardır. Kadroda görünmemek, 13 oyuncu
sayılması veya eski bir bırakma işlemi boşta olma kanıtı değildir. Köprü,
sayfaları tarayıp `availability_snapshot` kaydını tutar; eksik taramada
yalnızca doğrulanan oyuncular kullanılabilir. Kanıt 24 saatten eskiyse veya
yoksa hamle önerileri bekletilir; kategori tahmini devam eder. Eski köprüden
geçişte sunucuyu yeniden başlatıp arayüzdeki güncel bookmarklet ile tekrar
senkronize edin. Kullanıcı girdisi ve eski tahmin arşivleri otomatik
değiştirilmez.

Yeni köprü Yahoo takım numaralarının kanonik slot eşlemesini ve oyuncu
Yahoo kimliklerini saklar. İlk eşleştirme belirsizse kabul edilmez;
sonraki çalışmalarda takım adı veya kadro değişikliği kimliği değiştirmez.
Kadro, skor ve FA kanıtının `sync_id` değerleri uyuşmalıdır. OAuth yeni
kadroyu alırken FA kanıtı eski sürümde kalırsa hamleler bekler; eski pozitif
kanıt yeni yakalanmış gibi zaman damgalanmaz.

Skor ayrıştırıcısı gerçek Yahoo takım kimliği ve tutarlı oynanan/kalan/toplam
sayılarını ister; eksik alanlara uydurma maç sayısı veya rakip atamaz.
`latest_cloud_summary.md` ve `latest_forecast.json` içindeki kategori
tanıları gerçekleşen skor, kalan beklenti ve farkın standart sapmasını
ayrı gösterir. Yahoo'nun ham maç sayısı, seçilecek aktif kadronun kesin
oyuncu-maç sayısı değildir.

OAuth için `config/yahoo_oauth.template.json` dosyasını `config/yahoo_oauth.json`
olarak kopyalayıp `python -m src.auth_yahoo` kullanın. Bildirim ayarları
`config/telegram.template.json` şablonundan oluşturulur. Gerçek kimlik bilgileri
Git tarafından yok sayılır.

`src/draft_data.py` tarihsel 14×13 draft için tek fallback kaynağıdır. Canlı
`league_state.json` kadroları bunun yerini alır. İsim çözümleme 1:1 olmalıdır;
çözülemeyen veya iki takıma atanan oyuncu sessizce kabul edilmez. Genel NBA
G/F/C pozisyonları tam Yahoo uygunluğunun yerine geçmez.

## Lig ayarları

`config/league.template.json` dosyasını isteğe bağlı `config/league.json`
olarak kopyalayın. Ayar yoksa normal sezon kategori puanı hedefi kullanılır.

- `phase`: `regular_season` veya `playoffs`.
- `playoff_tie_credit`: Normal sezonda kullanılmaz. Playoff'ta gerçek eşitlik
  kuralına göre 0–1 arasında değer zorunludur; null ile playoff açılmaz.
- `playoff_spots`: Bu ligde 4.
- `max_weekly_adds`: Varsayılan 3; gerçek lig limitiyle eşleşmelidir.
- `adds_used_this_week`: Varsayılan 0. Her hafta ve işlem sonrası güncelleyin;
  tüketim sayısı doğrulanmamış işlem geçmişinden uydurulmaz.
- `protected_player_names`: Hiçbir öneride düşürülemeyecek isimler.

Normal sezonda kategori beraberliği her zaman yarım puandır; haftalık
beraberliğin değeriyle karıştırılmaz.

## İlk dört hesabı

`python -m src.playoffs league_outlook.json --simulations 20000` kullanılır.
Girdinin `standings` alanı takım kimliğinden kategori `W`, `L`, `T` toplamlarına
giden sözlüktür. `fixtures`, kalan eşleşmelerin listesidir. Her eşleşmede
`week`, `home`, `away` ve dokuz kategorili `categories` bulunur. Örnek tek
kategori: `"PTS": {"win": 0.6, "tie": 0.01}`. Bütün ihtimaller ev sahibi
perspektifindedir; mağlubiyet `1-win-tie` olarak hesaplanır.

Tam girdi gerçek 14 takımın bütün kalan eşleşmelerini içermelidir. W/L/T
haftalık sonuç sayıları değildir. Sıralama `(W+.5T)/(W+L+T)` ile yapılır.
Gerçek bir `tiebreak_priority` listesi verilmezse kesim noktasında tarafsız
kura varsayılır. Bu Yahoo tiebreak kuralının doğrulandığı anlamına gelmez.
Monte Carlo standart hatası yalnızca örnekleme hatasıdır. Gelecek kategori
sonuçları ve haftalar bağımsız varsayılır. Veri sağlanmadan ilk dört yüzdesi
üretilmez; haftalık kazanma yüzdesi sezon sıralamasının yerine kullanılmaz.

## Otomasyon ve geliştirme

Yahoo köprüsünde kadro ve skor aynı senkronizasyon kimliğine ait olmalıdır.
Yeni kadro kaydıyla eski skor eşleşirse öneriler bekletilir; bildirim bunun
nedenini ayrıca yazar. Güncel bookmarklet, matchup adresinin sorgu
parametrelerini korur ve yeni alınan HTML'i ayrıştırır; gerekirse aynı
origin içinde yeni yüklenen bir belgeyi bekler. Skor yakalanamazsa yeni
tarayıcı isteği mevcut kadro/skor kaydını değiştirmeden reddedilir.
Eski skorun zamanını veya kimliğini elle yenileyerek bu kontrol aşılmamalıdır.

Köprü kodu güncellendiğinde çalışan Python süreci yeniden başlatılır.
Güncel kurulumdaki yer imi `sync.js` dosyasını her tıklamada köprüden yükler;
bu yer imini her kod değişiminde yeniden kaydetmek gerekmez. Eski gömülü
JavaScript kullanan yer imleri için kurulum bağlantısı bir kez yenilenmelidir.
Ardından güncel Yahoo Matchup sayfasından çalıştırılır. Başarı bandı verinin
kaydedilip rapor işleminin başlatıldığını bildirir; Telegram teslim alındısı
anlamına gelmez. Maç başladıysa kısmi süre kontrolü ayrıca önerileri engelleyebilir.

FA sayfaları Yahoo'nun sayfada sunduğu ileri bağlantılar üzerinden en fazla
dört eşzamanlı istekle taranır. Skor ve sahiplik doğrulaması korunur.
Yakalama aşamalarının süreleri `league_state.json` içindeki `capture_metrics`
alanına yazılır. Başarılı Git push'ından sonra bildirim yalnızca Actions'ta
üretilir; bütün veri/tahmin hattı önce yerelde tekrar çalıştırılmaz. Push
başarısızsa yerel üretim denenir. Tam senkronizasyon süresi ve Python süresi
ayrı ölçülmelidir; bulut aşama süreleri `[TIMING]` satırlarında yer alır.

Actions'ın manuel `dry_run=true` girdisi gerçek veri/tahmin/arşiv hattını
çalıştırır; Telegram ve Discord gönderimini kapatır. Normal zamanlanmış ve
push koşularında bildirim davranışı sürer. NBA oyuncu log isteği bulutta
tek 10 saniyelik denemeyle, saat kaydı isteği 6 saniyeyle sınırlıdır;
başarısız istekte önbellek kullanılır veya mevcut doğruluk kontrolleri öneriyi
engeller. Zaman aşımında önbellek tarihi güncelmiş gibi değiştirilmez.

Waiver tarihi ISO biçimine normalize edilir; `30/10`, `10/30`, `Oct 30` ve
`October 30, 2026` gibi anlaşılır tarihler desteklenir. `03/04` gibi locale'i belirsiz tarihlerde
gün uydurulmaz; tarih bilinmeyen waiver öneriden çıkarılır. Güncel Yahoo W
statüsü, tarih kaydı eksik diye FA'ya dönüşmez. Rapor ve Telegram claim
durumunu ve açılış tarihini gösterir; açılıştan önceki maçlar katkıya eklenmez.

Add düğmesi veya satırdaki FA sınıflandırması, kayıtlı gelecek waiver
tarihini silmez. Add, waiver claim için de kullanılabilir. Tarih geçince
FA kaydı kısıtı kaldırabilir; daha önce kaldırması için Yahoo'nun seçili
`Free Agents` filtresinden açık kanıt gerekir. Yakalamanın `status_evidence`
alanı bu ayrımı korur. Tooltip içindeki HTML ve İngilizce ay adları okunur.

Canlı hamle sıralaması geçici olarak aynı ekleme/bırakmanın sakatlık dakika
dağıtımı açık ve kapalı katkılarının küçüğünü kullanır. Her senaryonun kendi
hamlesiz referansı vardır; ana kategori puanı, olasılıklar ve Bayesian
parametreleri değiştirilmez. Yalnızca iyimser dağıtım senaryosunda artı
sağlayan hamleler sunulmaz. Bu bir temkinli karar kuralıdır, fit edilmiş
posterior veya doğrulanmış kategori başarısı artışı değildir; gerçek fırsatları
kaçırma bedeli tarihsel ve canlı karşılaştırmada ölçülmelidir.

Geliştirme testleri, deney çalıştırıcıları ve geçmiş sonuçlar yalnızca
yerel `research/legacy/` ve `research/current/` altında tutulur. Günlük
otomasyonun bu klasörlere bağımlılığı yoktur. Canlı model ayarları
`config/model_policy.json` ve `config/rotation_policy.json` içindedir.
Bir araştırma adayının bulunması bu ayarları otomatik değiştirmez.

GitHub kaynak kontrolü yalnızca yayımlanan `src/` kodunu derler, temel
karar hedefini ve deterministik beraberlik hesabını denetler, lint ve biçim
kontrolü yapar. Ayrıntılı özel testler yerelde çalıştırılır.

# Model ve karar hedefleri

## Normal sezon ve playoff ayrımı

Normal sezon amacı `E[kategori galibiyeti] + 0.5 E[kategori beraberliği]`.
Bu beklenti kategori bağımsızlığına ihtiyaç duymaz. Rakibin beklenen kategori
puanı `9 - bizim puanımız` olur. Beklenen puan kesin tahmin edilmiş skor değildir.

Draft'ta tamamlanmış kadroların rakiplere karşı ortalama kategori puanı kullanılır.
Z skorları kısa liste içindir; final skora manuel punt, kategori tabanı veya
yıldız primi eklenmez. `ADP_Z` arayüz alanı BASE_Z sıralamasıdır; gerçek Yahoo
ADP verisi olduğu iddia edilmez. Rakip draft politikası bir varsayımdır.

Playoff'ta açıkça `objective="matchup"` seçilebilir. Amaç
`P(hafta kazanılır) + playoff_tie_credit P(hafta berabere)` olur. Beraberlikte
ilerleme avantajı kesin bizdeyse kredi 1, rakipteyse 0; belirsizliğe göre ara
değer kullanılabilir. Bu ayar gerçek playoff kuralından gelmelidir. Normal
sezonda kategori beraberliği her zaman yarım puandır.

## Oyuncu oranları ve dakika

Sayma kategorilerinde `lambda ~ Gamma(alpha,beta)`; beta dakika cinsinden rate
parametresidir. Gözlemle `alpha += sayı`, `beta += dakika`. Geçmiş güven üstel
olarak unutulur; ticarette oran ortalaması korunarak güven azaltılır. Etkin
örneklem alt sınırları bir filtre tasarım tercihidir; tam bir dinamik süreç
türetimi olarak sunulmaz.

Shrinkage hedefleri pozisyon bazlıdır. Sayma istatistiklerinde geçmiş oyuncu
oranları varyansından Poisson örnekleme varyansı çıkarılır; kalan varyansla
moment yöntemi shrinkage kuvveti tahmin edilir. Yetersiz veride sabit fallback
kullanılır. Unutma hızları, EWMA ve aşırı saçılım katsayıları halen varsayımdır.

Geçmiş sezonlar **dakika başına oranlar** üzerinden birleştirilir; toplamları
ağırlıklandırarak daha uzun sezona gizli ek ağırlık verilmez. Çaylakta tahmin
edilen rol dakikası ile preseason'da gözlenen kanıt miktarı ayrıdır.

Canlı model politikası `config/model_policy.json` içindedir; dosya yoksa
`ModelPolicy()` varsayılanı kullanılır. Varsayılan iki sezon ağırlığı
`clip(GP_primary/65, .35, .80)` olup yeni sezon gözlemlerinin payı değildir.
Sayma ve deneme önsel güveni `clip(120+.25*evidence_minutes,120,650)` dakika;
şut isabeti güveni ayrı olarak deneme cinsindendir. Bunlar farklı birimlerdir.

Canlı dakika tahmini, gözlemden sonra son beş maç ortalamasını sezon başı
rol önseliyle harmanlar. Etkin config politikası `adaptive_anchor`:
`w=n/(n+k)`, `n=takas sonrası toplam gözlenen maç`. Ortalama penceresi
her iki politikada da son beş maçtır. `recent_blend` gölge/referans kolu ise
`n=min(gözlenen_maç,5)` kullanır;
fark 6.5 dakikaya ulaşınca `k=1`, diğer durumlarda `k=3`.
Ticarette geçmiş pencere sıfırlanır. `ewma` deneysel alternatiftir; bütün
politikalar aynı `update_role` yordamını kullanır. Config yoksa dataclass
fallback'i `recent_blend` olur; bu fallback etkin config ile karıştırılmaz.
Rol değişimi sinyali gözlemden önce bilinmiş
sayılmaz. Bu eşikler kalıcı rol değişimini kesin teşhis eden kurallar değildir.

Kalibrasyon yalnızca önsel/rol politikalarını değiştirir. FG/FT momentleri,
haftalık ortak belirsizlik ve kategori beraberliği düzeltmeleri bütün
adaylarda korunur. Seçilmiş canlı katsayılar `config/model_policy.json` içindedir; özel deney sonuçları yerel araştırma alanında tutulur.

Bağımsız dakika M ve oran lambda için tahmin varyansı:

\[
V(X)=\phi E[\lambda]E[M]+V(\lambda)(E[M]^2+V(M))
+E[\lambda]^2V(M).
\]

`phi=1` Poisson çekirdeğidir. `phi>1` ek saçılım moment düzeltmesidir; bununla
tüm model tam eşlenik Negative Binomial üretici model haline gelmez. Sabit
verilen dakika için dakika varyansı sıfırdır.

## Şut yüzdeleri

İsabet olasılığı `p ~ Beta(alpha,beta)` ve deneme N ayrı izlenir.
`q=E[p]`, `s=alpha+beta`, `n=E[N]`, `v=V[N]` için:

\[
E[K]=nq,\qquad V(K)=\frac{q(1-q)}{s+1}\{n(s+n)+v\}+q^2v.
\]

Bu formül rastgele denemenin koşullu varyans katkısını da içerir. N ile p
bağımsız varsayılır. Sabit verilen denemede v sıfırdır.

Takım yüzdesi toplam isabet / toplam denemedir. Her takımın kendi beklenen
yüzdesi `q_A=mu_M/mu_N` ile delta yöntemi uygulanır:

\[
V(M/N)\approx V(M-q_A N)/\mu_N^2.
\]

İki takımın varyansları toplanır ve yüzde farkı karşılaştırılır. Farklı hacimlerde
ağırlıksız net-impact farkını aynı varyansla karşılaştırmak kullanılmaz. Sıfır
denemede yüzde 0 kabul edilir; iki taraf da kesin sıfırsa beraberedir. Çok
küçük hacimlerde normal/delta yaklaşımı yine yaklaşık kalır.

## Haftalık belirsizlik ve beraberlik

Aynı oyuncunun maçları ortak bilinmeyen oranı paylaşır. Sabit dakika ve oynama
ihtimali 1 olan g maçta `g V(X_game) + g(g-1) m^2 V(lambda)` kullanılır.
Şutlarda ortak accuracy ve attempt-rate belirsizliği de oyuncu düzeyinde
taşınır. Gerçekleşmiş istatistikler sabittir; yeniden varyans eklenmez.

Sayma farklarında normal yaklaşımının kazanma eşiği +0.5, kaybetme eşiği -0.5;
aradaki hücre beraberliktir. Sıfır varyansta sonuç kesindir, yapay varyans tabanı
yoktur. Haftalık W/L/D, kategori galibiyet eksi mağlubiyet dengesini tam dinamik
programla birleştirir; 4–3–2 galibiyettir. Birleştirme bağımsız kategori
varsayımı altında tamdır; girdi olasılıkları yine yaklaşık olabilir.

İsteğe bağlı rho duyarlılığı tek faktörlü Gaussian copula kullanır. Rho gizli
Gaussian korelasyonudur; ham NBA istatistiği veya kazanma göstergesi korelasyonu
değildir. Varsayılan sıfırdır; doğrulanmış bir NBA korelasyonu iddia edilmez.

## Sakatlık ve rotasyon

Oynama geçmişi Beta-Bernoulli filtreyle izlenir. Durum kodları ve DNP etkileri
açık varsayımlardır. İki DNP varsayılan olarak bütün haftadan kesin dışlama
yapmaz. Gelecek dönüş tarihinde %52'den sağlıklı tabana bir haftalık geçiş
kullanılır; bu henüz sakatlık geçmişine göre fit edilmiş bir iyileşme modeli
değildir. Dönüş tarihi bilinmeyen OUT için sıfır beklenti konservatif politikadır.

Ek dakika hesabında yeni sakatlığın son gözlenen role zaten gömülü bölümü
çıkarılır. Rol tavanları ve `sum P(oynar)*E[dakika|oynar] <= 240` beklenen
dakika bütçesi uygulanır. Eksik rotasyonda 240 dakikanın tamamı uydurulmaz.
Fazla oyunculu önsel havuzunda baseline da bütçeye göre kısılabilir. Bütçenin
altındaki takımda sakatlık kalkınca bonuslar baseline'a döner. Bu bir nedensel
usage veya koç kararı modeli değildir.

## Kararlar ve sınırlar

Hungarian ataması boş slot seçeneği içerir. Eşleşmeye göre marjinal ağırlıklarla
iki geçiş yapılır; yalnızca amaç değerini iyileştiren kadro korunur. Global
haftalık optimum garantisi yoktur; rakibin kadro politikası sabittir.

Add/drop önerileri birbirinin alternatifidir. Kadroya sessizce FA eklenmez;
aynı FA iki takımda varsayılmaz. Gerçek Yahoo IL stashes bağlayıcıdır. Tam
Yahoo uygunluğu yoksa NBA G/F/C pozisyonları yaklaşık kalır. Waiver tarihi
Yahoo'dan gelir; evrensel iki gün kuralı varsayılmaz. Bilinen waiver'ın tarihi
bilinmiyorsa önerilmez. Kullanılmış hamle sayısı ayardan alınır. Varsayılan
aktif kadronun en iyi 11 oyuncusu korunur; açık korumalar hiçbir fallback ile
aşılmaz.

Tarihli fikstür esastır. Fikstürsüz 3.35/2.35 maç yaklaşımı yalnızca draft
fallback'idir. Tamamlanmış maçlar tekrar projekte edilmez. Oyun içindeki maçlar
için tam kalan dakika modeli yoktur; güvenilir kullanım maç başlamadan veya
bittikten sonra güncel skorla çalışmaktır. Varsayımlar doğrulama raporundan
bağımsız şekilde “kalibre edilmiş” diye sunulmaz.

## Doğrulama ve aday model sınırları

- **Yapısal rol kovaryansı ile olasılık kalibrasyonu ayrımı:** Haftalık toplamda
  aynı oyuncunun maçları arasındaki yapısal rol/dakika kovaryansı (`role_covariance_correlation`,
  varsayılan `0.0`) örnek ayarı ve alt seviye override ile deneysel olarak
  kullanılabilir; eşleşme, simülasyon ve add/drop aynı örnek ayarını taşır.
  A1B olasılık kalibrasyonu henüz uygulanmış bir katman değildir:
  `WEEKLY_VAR_INFLATION_BY_CAT` yalnız nötr bir yer tutucudur ve değiştirilmesi
  çıktıyı değiştirmez. Yeni kalibrasyon aktive edilmedi. İki aday birbirinin
  mekanizma doğruluğuna kanıt oluşturmaz.
- **Oynama önseli ve sezon içi güncelleme:** 82 maç oynayan bir oyuncunun başlangıç
  ham Beta-Bernoulli filtre ortalaması `61/66 = %92,4242` olur. Sağlıklı etkin
  olasılık `0.35*0.92 + 0.65*61/66 = %92,2758` değerindedir. Sezon içi
  `availability_rate` ham tavanı `%98`, etkin sağlıklı olasılık tavanı ise
  `0.35*0.92 + 0.65*0.98 = %95,9` olur. Bunlar ayrı büyüklüklerdir.
  İki sezonlu önsellerde `eff_gp` MPG ölçeklemesinde kullanılırken
  `AVAIL_GP` birincil sezonu (`gp1`) korur; sağlıklı taban veya `eff_gp` alternatifleri
  doğrudan canlı varsayılan yapılmadan önce aday politika olarak test edilir.
- **Geçici kabul ve kanıt borcu:** `adaptive_anchor` dakika politikası önceden tanımlı
  seçim/değerlendirme kapılarını geçerek geçici (`provisional`) kabul almıştır ve
  `recent_blend` gölge koluyla birlikte izlenir; buna karşın kazanımın küçük olması ve
  mevcut sezgisel eşiklerin (sakatlıktan dönüş eğrisi, B2B indirimi, şut deneme/isabet
  unutma hızları `FGA`/`FTA` vs `FG`/`FT`) bileşen bazlı ablasyon gerektirmesi açık araştırma
  konusudur.
- **Sakatlık spillover ve duyarlılık filtresi:** Canlı raporda (`src/forecast.py`)
  `opportunity_sensitivity=True` aktiftir ve her add/drop adayını hem spillover açık hem
  spillover kapalı kendi baz senaryolarına göre değerlendirip `min(delta_with_spillover, delta_without_spillover)`
  ile sıralar. Bu kural kalibre edilmiş bir güven aralığı değil, muhafazakâr bir karar
  duyarlılık filtresidir.
- **Karar testi kapsamı ve tek haftalık ufuk:** `recommend_add_drop_moves` tek haftalık
  ufukta alternatif tekil hamleleri sıralar; kalan haftalık ekleme hakkının gölge fiyatı
  ve çok haftalık sıralı bütçe ayrımı yerel araştırma kontrollerinde (`roster_backtest`,
  `weekly_controls`, `sequential`) ayrı değerlendirilir ve canlı motorda kanıtsız
  varsayılan olarak sunulmaz.

## Sezon kanıtının sınırı

`LiveDraftAssistant` canlı hazırlıkta hedef sezon roster/preseason dosyalarını
sezon adından yükler; `historical_replay=True` bu kanıtı devre dışı bırakır.
Alt seviye `load_prior_season(..., include_target_evidence=False)` ve
`MatchupEngine(..., include_target_evidence=False)` tarihsel replay sözleşmesidir.
Gelecek sezonun açık canlı hazırlığında bu parametre `True` verilir; loader'ın
`target_season` değeri önselin hemen sonraki sezonu olmalıdır. Tarihsel motorun
as-of takım haritası ayrıca `team_map` ile verilmelidir. Repository'deki mevcut
replay yükleyicileri target evidence'i açıkça kapatır. Eski doğrudan çağrıların
2025–26 önsel / 2026–27 hedef varsayılanı yalnız geriye uyumluluk içindir;
tarihsel deneyler bu varsayılana güvenmemelidir. Bir tam-sezon roster/preseason
dosyası gün içi/as-of kanıt değildir; bu bayrak yalnız canlı sezon hazırlığı
içindir, geçmiş kesime geri taşınamaz. Eksik dosyada veri uydurulmaz.

## Mevcut tarihsel karar kanıtının kapsamı

Yeni bir deney çalıştırılmadı. Aşağıdaki sayılar mevcut yerel arşivlerden gelir:

| Deney | Kontrol / sağlık kapsamı | Kadro-haftası ve takvim haftası | Kanıt sınırı |
|---|---|---|---|
| `roster_20261028T172809Z` | Kaliteyi gözetmeyen schedule add kontrolü; canlı sakatlık/spillover kapalı | Sezon başına 440 hamle durumu / 22 takvim haftası; ayrıca 3.080 eşleşme olasılık kaydı | Sentetik lig/kadrolar, gerçek tarihsel oyuncu üretimi. Olasılık kayıtları bağımsız haftalar değildir. |
| `weekly_controls_20261029T085904Z` | Aynı yasal hamle havuzunda beklenen toplam maç dakikası kontrolü; sakatlık/IL vekili dahil | Sezon başına 63 kadro-haftası / 21 takvim haftası | Değerlendirme sezonunda motor eksi kontrol %95 aralığı [+0,182; +0,738]; geliştirmede [-0,087; +0,230]. Evrensel üstünlük yok. |
| `sequential_expanded_20261029T105309Z` | Üç haklı greedy/reserve, günlük bilgi kesimi, sentetik waiver ve IL varsayımları | 2024–25: 14 eşli kadro-haftası / 7 hafta; 2025–26: 16 / 8; toplam 30 tam-verili eşli durum | 32 planlı durumdan eksik raporlu 2 durum dışlandı. Reserve farkının aralıkları [-0,1071; +0,4643] ve [0; +0,0938]; kesin üstünlük yok. |

63 sayısı bütün sequential deneylerine genellenmez. Takvim bloklarının,
ortak oyuncuların ve yeniden kullanılan tarihsel sezonların bağımlılığı
korunmalıdır. Bunlar gerçek Yahoo sahiplik/işlem geçmişi değildir; sağlık
etiketi, tarihsel fikstür ve kadro vekillerinin seçilim sınırları vardır.
Yeni seed yeni bağımsız NBA haftası değildir. Önceden incelenen sezonlar
yeni bağımsız son test diye sunulamaz. Yerel kaynaklar:
`research/current/data/archive/experiments/roster_20261028T172809Z/`,
`research/current/runs/weekly_controls_20261029T085904Z/` ve
`research/current/reports/research_stage1/report.md`.

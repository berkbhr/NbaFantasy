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
rol önseliyle harmanlar. `w=n/(n+k)`, `n=min(gözlenen_maç,5)`;
fark 6.5 dakikaya ulaşınca `k=1`, diğer durumlarda `k=3`.
Ticarette geçmiş pencere sıfırlanır. `ewma` ve zamanla önsel ankrajını
azaltan `adaptive_anchor` alternatifleri aynı `update_role` yordamıyla
kalibrasyonda değerlendirilir. Rol değişimi sinyali gözlemden önce bilinmiş
sayılmaz. Bu eşikler kalıcı rol değişimini kesin teşhis eden kurallar değildir.

Kalibrasyon yalnızca önsel/rol politikalarını değiştirir. FG/FT momentleri,
haftalık ortak belirsizlik ve kategori beraberliği düzeltmeleri bütün
adaylarda korunur. Sonuçlar ve kabul kararı `reports/calibration/` altındadır.

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

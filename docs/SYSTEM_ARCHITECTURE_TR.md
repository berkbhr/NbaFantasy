# NBA Fantasy Yapay Zeka Simülasyonu - Sistem Mimarisi

Bu doküman, projenin güncellenmiş **Olasılıksal Karar Teorisi (Probabilistic Decision Theory)** ve **Eşlenik Bayes (Conjugate Bayesian)** tabanlı veri ve yapay zeka mimarisini detaylandırmak amacıyla hazırlanmıştır.

## 1. Proje Özeti
Bu proje, NBA Fantasy H2H (Head-to-Head) 9-Kategori formatı için sıradan bir geçmiş istatistik hesaplayıcısı değil; sakatlıkları, takasları, dakika değişimlerini ve oyuncuların "gece-gece dalgalanma (prediktif varyans)" ihtimallerini doğrudan **Kategori Kazanma Olasılığına ($\Phi$)** dönüştüren **Tahminsel (Predictive) ve Adaptif bir Yapay Zeka** motorudur.

Geleneksel parçalı Z-Skoru, yapay "punt" eşikleri ve manuel doygunluk (saturation) yamaları yerine; tüm kararlar (Draft, Günlük Kadro Dizilimi ve Sezon İçi Waiver/Streaming) tek bir birleşik matematiksel amaç fonksiyonuna dayanır: **Beklenen Kazanılan Kategori Sayısını ($\sum_{c=1}^{9} \mathbb{P}(\text{Win}_c)$) Maksimize Etmek.**

---

## 2. Veri Mimarisi (Data Engineering)

Projenin veri boru hattı (Data Pipeline), `src/data_fetcher.py` üzerinden tamamen otomatikleştirilmiştir. Veriler NBA'in resmi API'sinden çekilir ve "Medallion Architecture" mantığıyla saklanır.

### Veri Akışı
1.  **Raw (Ham) Veri:** NBA API'den çekilen oyuncu ve takım maç logları (Game Logs) doğrudan `.parquet` formatında `data/raw/` klasörüne kaydedilir.
2.  **Processed (İşlenmiş) Veri:** Ham veriler işlenerek yapay zekanın kullanacağı 6 ana tabloya ayrılır ve `data/processed/` klasöründe saklanır:
    *   **Player_Stats:** Maç bazlı oyuncu istatistikleri.
    *   **Team_Stats:** Maç bazlı takım istatistikleri.
    *   **Schedule:** Tam sezon fikstürü.
    *   **Trades:** Günlük takım değişikliklerini (ID değişimleri) takip ederek çıkarılan takas listesi.
    *   **Injuries_DNP:** Takımın maçı olduğu halde oyuncunun sahada olmamasından türetilen Sakatlık/Oynamadı bilgisi.
    *   **Player_Positions:** Oyuncuların Yahoo Fantasy esnek pozisyon uygunluklarını (`PG, SG, G, SF, PF, F, C, UTIL, BN`) belirleyen pozisyon tablosu.

---

## 3. Yapay Zeka ve Karar Mimarisi (Bayesian Inference & Decision Theory)

Yapay zeka, oyuncuların performansını tekil nokta tahminlerle (point estimates) değil, **Öngörücü Olasılık Dağılımlarıyla (Predictive Distributions)** değerlendirir.

### 3.1. Hacim Bazlı Yüzdeler (Beta-Binom Modeli)
* **Kategoriler:** FG% (Saha İçi), FT% (Serbest Atış).
* **Mantık:** Yüzdeler sadece bir oran değil, şut hacmidir. Dağılım $\text{Beta}(\alpha, \beta)$ ($\alpha=\text{İsabet}, \beta=\text{Kaçan}$) olarak kurulur. Az şut atan oyuncunun yüzdesi yüksek bile olsa, Beta-Binom prediktif varyansı yüksek olacağı için yapay zeka bunu karar fonksiyonuna doğrudan yansıtır.
* **Net Etki (Impact) Dönüşümü:** Oranların doğrusal toplanabilmesi için şut yüzdeleri rakip/lig referans oranına ($p_{\text{ref}}$) göre **Net İsabet Etkisi** ($Y = \text{M} - p_{\text{ref}} \cdot \text{A}$) üzerinden değerlendirilir.

### 3.2. Dakika (Exposure) Bazlı Sayılabilir Veriler (Gamma-Poisson Modeli)
* **Kategoriler:** PTS, REB, AST, STL, BLK, 3PM, TOV.
* **Mantık:** Oyuncunun maça çıkması (1 Maç) değil, sahada kaldığı **Süre (Dakika)** maruziyet (exposure) olarak baz alınır. Dağılım $\text{Gamma}(\alpha, \beta)$ olarak kurulur.
* **Güncelleme:** $\alpha_{\text{yeni}} = \delta \alpha + \text{Stat}$, $\beta_{\text{yeni}} = \delta \beta + \text{Dakika}$
* **Prediktif Dağılım (Negatif Binom):** Beklenen değer $\mu = m \cdot \frac{\alpha}{\beta}$ ve prediktif varyans $\sigma^2 = \mu + \frac{\mu^2}{\alpha}$ olarak analitik formda hesaplanır.

### 3.3. Unutma Mekanizması (Discounted Conjugate Filtering)
Oyuncuların geçmiş istatistiklerinin bugünü zehirlememesi için sonsuz hafıza iptal edilmiştir:
*   **Soft Decay (Günlük):** Her maç güncellemesinde eski verilerin ağırlığı üstel olarak sönümlenir ($\delta = e^{-\lambda \Delta t}$).
*   **Hard Reset (Takas/Rol Değişimi):** Bir oyuncu takaslandığında ($\delta_{\text{event}} = 0.2$), oyuncunun dakika başı yetenek oranı ($\alpha/\beta$) korunur ancak modelin geçmişe olan **güveni (Effective Sample Size - $\beta$)** 5'te 1'e indirilir. Böylece yeni takımdaki ilk birkaç maç, eski takımdaki 50 maçtan daha baskın hale gelir.

---

## 4. Mantıksal Karar Katmanları (Unified Decision Layers)

### 4.1. Birleşik Hedef Fonksiyonu: Analitik H2H Kategori Kazanma Olasılığı ($\sum \Phi$)
Parçalı Z-skoru toplamları, keyfi doygunluk sınırları (`z > 2.5`) ve keskin punt kuralları (`mean_z - 1.5`) yerine, hem Draft hem de Sezon İçi değerlendirmede **Analitik Normal Kümülatif Dağılım Fonksiyonu (Gaussian CDF - $\Phi$)** kullanılır:

$$\mathcal{V}(\text{Kadro}) = \sum_{c=1}^{9} \mathbb{P}(\text{Win}_c) = \sum_{c=1}^{9} \Phi\!\left(\frac{\mu_{\text{ben}, c} - \mu_{\text{rakip}, c}}{\sqrt{\sigma^2_{\text{ben}, c} + \sigma^2_{\text{rakip}, c}}}\right)$$

Bu tek denklem üç temel stratejiyi **kendiliğinden (doğal olarak)** gerçekleştirir:
1.  **Doğal Doygunluk (Natural Saturation):** Kazanma olasılığı %95+ ($\approx +2\sigma$) olan bir kategoride $\Phi$ eğrisi yataylaşır (marjinal fayda $\phi(z) \to 0$). Yapay zeka zaten kazandığı kategoriye gereksiz yatırım yapmayı bırakır.
2.  **Doğal Punt (Natural Punting):** Kazanma olasılığı %5'in altına ($\approx -2\sigma$) düşen bir kategoride de $\Phi$ eğrisinin alt kuyruğu yataylaşır. Yapay zeka tek bir oyuncuyla kurtarılamayacak kategoriyi doğal olarak feda eder ve başa baş ($Z \approx 0$, marjinal eğim $\phi(z)$ maksimum) kategorilere odaklanır.
3.  **Varyans Duyarlılığı (Risk-Seeking vs. Risk-Averse):** Geride olunan ($\mu_{\text{ben}} < \mu_{\text{rakip}}$) kategorilerde yüksek varyanslı ($\sigma^2$ yüksek) oyuncular paydadaki kök değerini büyütüp negatif kesri sıfıra yaklaştırarak kazanma ihtimalini artırır (kumara girer). Önde olunan ($\mu_{\text{ben}} > \mu_{\text{rakip}}$) kategorilerde ise düşük varyanslı (stabil) oyuncular tercih edilir.

### 4.2. Draft Motoru: Yılan Draft İleriye Bakış (Lookahead Rollout)
`src/live_draft_assistant.py` içinde aday oyuncular değerlendirilirken:
*   Rakiplerin kalan turlardaki olası seçimleri pozisyon kısıtları (10 aktif + 3 bench slotu) gözetilerek ileriye doğru simüle edilir (**Lookahead Rollout**).
*   Böylece **Pozisyon Kıtlığı (Positional Scarcity)** (örneğin pivotların erken tükenmesi) ve takımın kalan turlarda oluşturacağı nihai 13 kişilik kadronun $\sum_{c=1}^9 \Phi_c$ kazanma olasılığı birlikte optimize edilir.

### 4.3. Günlük Kadro Optimizasyonu: Maksimum Ağırlıklı Bipartit Eşleştirme (Linear Assignment)
`src/matchup_engine.py` içinde günlük aktif 10 oyuncunun (`PG, SG, G, SF, PF, F, C, C, UTIL, UTIL`) seçimi için kaba kuvvet alt küme kombinasyonları (`combinations`) yerine **Linear Assignment (Maksimum Ağırlıklı Bipartit Eşleştirme)** kullanılır:
*   Her oyuncunun o günkü marjinal kategori ağırlıklarına ($\phi(z_c)$) göre beklenen katkısı hesaplanır.
*   Oyuncu-Slot uygunluk matrisi üzerinden optimal eşleşme tek adımda çözülür; 10'dan fazla oyuncusu olan kadrolarda kalan oyuncular doğal olarak yedek (`BN`) koltuğuna yerleşir.

### 4.4. Sezon İçi Öğrenme ve Core-Protected Waiver (Streaming) Döngüsü
`league_simulator.py` ve `src/model_ai.py` tam entegre çalışır:
*   **Günlük Bayes Güncellemesi:** Sezonun her gününde oynanan gerçek maçlar ve gerçekleşen takaslar `BayesianPlayer.update_stats` ile tüm oyuncu havuzunun posterior dağılımlarını günceller.
*   **Çekirdek Korumalı Waiver (Core-Protected Streaming):** Haftalık serbest oyuncu (waiver) hamlelerinde kadrodaki en değerli 11 oyuncu ("Core") korunur; yalnızca son 2 koltuk ("Streaming Slots") gelecek haftanın maç sayısı (fikstür avantajı) ve takımın başa baş olduğu kategorilerin marjinal ağırlıklarına ($\phi(z_c)$) göre serbest oyuncu havuzundaki en uygun oyuncularla sirküle edilir.

---

## 5. Dosya Hiyerarşisi
```text
D:\Github Projects\NbaFantasy\
│
├── data/
│   ├── processed/              # Parquet ve PivotTable uyumlu Excel veri tabanları
│   └── raw/                    # NBA API'den gelen işlenmemiş ham Parquet dosyaları
│
├── src/
│   ├── bayesian_model.py       # Eşlenik Bayes (Gamma-Poisson & Beta-Binom) çekirdeği
│   ├── matchup_engine.py       # Analitik H2H (Φ), Linear Assignment Lineup & Eşleşme motoru
│   ├── live_draft_assistant.py # Lookahead Rollout & Φ(Z) tabanlı canlı draft asistanı
│   ├── model_ai.py             # Bayesçi Core-Protected Waiver/Streaming karar motoru
│   ├── opponent_ai.py          # Rakiplerin (Naive Z-Score) waiver ve davranış modelleri
│   ├── simulator.py            # Sezon öncesi prior yükleme ve tekil Bayes simülasyon araçları
│   └── data_fetcher.py         # Veri çekme ve işleme (Data Pipeline) motoru
│
├── league_simulator.py         # Tam entegre (Draft + Günlük Bayes + Waiver + H2H) Lig Simülatörü
└── SYSTEM_ARCHITECTURE.md      # Bu doküman
```

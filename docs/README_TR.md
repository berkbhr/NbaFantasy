# NBA Fantasy AI Engine & Simulation Suite (H2H 9-Category)

Gelişmiş **Olasılıksal Karar Teorisi (Probabilistic Decision Theory)** ve **Eşlenik Bayes (Conjugate Bayesian)** istatistiksel modellerine dayalı, NBA Fantasy Head-to-Head (H2H) 9-Kategori formatı için tasarlanmış yeni nesil draft, simülasyon ve sezon içi yönetim motoru.

---

## 🌟 Öne Çıkan Özellikler

1. **Eşlenik Bayes Dağılımları (Conjugate Bayesian Inference):**
   - **Sayılabilir İstatistikler (PTS, REB, AST, STL, BLK, 3PM, TOV):** Dakika bazlı maruziyet (exposure) ile modellenen **Gamma-Poisson / Negatif Binom** öngörücü dağılımları.
   - **Hacim Bazlı Yüzdeler (FG%, FT%):** Şut denemesi ve isabet hacmini dikkate alan **Beta-Binom** dağılımı ve rakip/lig referans oranına göre **Net İsabet Etkisi (Impact)** hesabı.

2. **Dinamik Bellek & Sönümleme (Discounted Filtering):**
   - **Soft Decay:** Günlük maç güncellemelerinde geçmiş maçların ağırlığını üstel olarak sönümleme.
   - **Hard Reset (Takas/Rol Değişimi):** Bir oyuncu takaslandığında veya sakatlıktan sonra rol değiştirdiğinde, yetenek oranı korunurken geçmişe olan güven çarpanı adapte edilir.

3. **Birleşik Karar Fonksiyonu (Gaussian CDF H2H Win Probability):**
   - Keyfi Z-skoru toplamları veya manuel punt/saturation kuralları yerine; doğrudan beklenen kategori kazanma olasılığını ($\sum \Phi$) maksimize eden analitik optimizasyon.
   - **Doğal Doygunluk (Saturation):** Zaten kazanılan kategorilere gereksiz yatırım yapmayı engeller.
   - **Doğal Punt:** Geri dönülemez kategorileri otomatik olarak feda edip başa baş kategorilere odaklanır.
   - **Varyans Duyarlılığı:** Önde olunan kategorilerde stabil, geride olunan kategorilerde yüksek varyanslı oyuncuları tercih eder.

4. **Canlı Draft & Yahoo Fantasy Entegrasyonu:**
   - **Yahoo Draft Bridge (`src/yahoo_draft_bridge.user.js`):** Tampermonkey/Violentmonkey betiği ile Yahoo Draft odasındaki seçimleri gerçek zamanlı yakalar.
   - **Yahoo Draft Sync (`src/yahoo_draft_sync.py`):** Yahoo API veya webhook üzerinden canlı seçimleri yerel motora aktarır.
   - **Canlı Draft Asistanı (`src/live_draft_assistant.py`):** Kalan sıra, oyuncu havuzu ve kadro ihtiyaçlarına göre anlık en optimal öneriyi sunar.

5. **Tam Lig & Senaryo Simülatörü:**
   - 12 takımlı ligde 8. sıra (veya herhangi bir sıra) draft stratejilerini, haftalık fikstür eşleşmelerini ve sezon sonu playoff senaryolarını Monte Carlo yöntemiyle simüle eder.

---

## 📁 Proje Yapısı

```
NbaFantasy/
├── config/
│   └── yahoo_oauth.template.json     # Yahoo OAuth2 kimlik doğrulama şablonu
├── data/
│   ├── raw/                          # NBA API maç logları (Parquet)
│   ├── processed/                    # İşlenmiş oyuncu, takım, takas, fikstür tabloları
│   └── simulations/                  # Monte Carlo draft & sezon simülasyon çıktıları
├── docs/
│   ├── README_TR.md                  # Türkçe kullanım kılavuzu
│   └── SYSTEM_ARCHITECTURE_TR.md     # Türkçe sistem mimarisi dokümanı
├── reports/
│   ├── league_draft_overview_and_projections.md     # 14 Takımlı draft & model projeksiyon raporu (İngilizce)
│   └── league_draft_overview_and_projections.tr.md  # 14 Takımlı draft & model projeksiyon raporu (Türkçe)
├── src/
│   ├── bayesian_model.py             # Gamma-Poisson ve Beta-Binom Bayes motoru
│   ├── matchup_engine.py             # Analitik H2H Gaussian CDF & Lineup optimizasyon motoru
│   ├── live_draft_assistant.py       # Canlı draft öneri ve simülasyon motoru
│   ├── model_ai.py                   # Çekirdek korumalı waiver ve karar kuralları
│   ├── simulator.py                  # Sezon öncesi baseline yükleyicisi ve simülatör
│   ├── simulate_slot8_scenarios.py   # Çoklu senaryo simülasyon aracı
│   ├── data_fetcher.py               # NBA API veri çekme boru hattı
│   ├── verify_yahoo_names.py         # Oyuncu adı eşleme testleri
│   ├── yahoo_draft_bridge.user.js    # Yahoo draft odası için canlı Userscript
│   └── yahoo_draft_sync.py           # Yerel HTTP senkronizasyon sunucusu & paneli
├── league_simulator.py               # 12/14 takımlı lig sezon simülatörü
├── requirements.txt                  # Python bağımlılıkları
├── README.md                         # Ana proje tanıtımı (İngilizce)
└── SYSTEM_ARCHITECTURE.md            # Matematiksel sistem mimarisi dokümanı (İngilizce)
```

---

## 🚀 Kurulum

### 1. Depoyu Klonlayın
```bash
git clone https://github.com/<KULLANICI_ADINIZ>/NbaFantasy.git
cd NbaFantasy
```

### 2. Sanal Ortam Oluşturun ve Bağımlılıkları Yükleyin
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Yahoo OAuth Yapılandırması (Opsiyonel - Canlı Draft İçin)
`config/yahoo_oauth.template.json` dosyasını `config/yahoo_oauth.json` olarak kopyalayın ve Yahoo Developer API bilgilerinizi girin:
```bash
cp config/yahoo_oauth.template.json config/yahoo_oauth.json
```
*(Not: `config/yahoo_oauth.json` dosyası `.gitignore` ile gizlenmiştir ve depoya eklenmez.)*

---

## 📊 Kullanım

### Veri Güncelleme
```bash
python -m src.data_fetcher
```

### Canlı Draft Asistanını Çalıştırma
```bash
python -m src.live_draft_assistant
```

### 12 Takımlı Lig Sezon Simülasyonunu Çalıştırma
```bash
python league_simulator.py
```

---

## 📐 Matematiksel Formülasyon

Eşleşme kazanma beklentisi aşağıdaki analitik Normal Dağılım Kümülatif Fonksiyonu ($\Phi$) ile hesaplanır:

$$\mathcal{V}(\text{Kadro}) = \sum_{c=1}^{9} \mathbb{P}(\text{Win}_c) = \sum_{c=1}^{9} \Phi\!\left(\frac{\mu_{\text{ben}, c} - \mu_{\text{rakip}, c}}{\sqrt{\sigma^2_{\text{ben}, c} + \sigma^2_{\text{rakip}, c}}}\right)$$

Detaylı matematiksel çıkarımlar, Bayes güncelleme kuralları ve karar teorisi için [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) dosyasına göz atabilirsiniz.

---

## 📄 Lisans

Bu proje MIT Lisansı ile lisanslanmıştır.

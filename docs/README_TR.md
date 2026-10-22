# 🏀 NBA Fantasy Olasılıksal Karar ve Simülasyon Paketi (H2H 9-Kategori)

NBA Fantasy Head-to-Head (H2H) 9-Kategori formatı için tasarlanmış; **Eşlenik Bayes Çıkarımı (Conjugate Bayesian Inference)**, **Analitik Karar Teorisi (Analytical Decision Theory)** ve **Otonom Bulut CI/CD Boru Hatları** ile güçlendirilmiş, endüstriyel standartta bir nicel modelleme, simülasyon ve sezon içi canlı karar motoru.

> 🇬🇧 *For the English documentation, please refer to [README.md](../README.md).*

---

## 🌟 Öne Çıkan Yetenekler ve Sistem Mimarisi

### 1. Eşlenik Bayes Çıkarımı ve Sezon İçi Dinamik Öğrenme
- **Sayılabilir Kategoriler (PTS, REB, AST, STL, BLK, 3PM, TOV):** Statik maç başı ortalamalar yerine, oyuncunun sahada kaldığı gerçek **Süre Maruziyeti ($m$ dakika)** ile parametrelendirilen **Gamma-Poisson / Negatif Binom** öngörücü olasılık dağılımları.
- **Şut Yüzdeleri (FG%, FT%):** Ayrık deneme ve başarı mantığına dayalı **Beta-Binom** eşlenik çiftleri. Lig ve rakip referans oranına göre doğrudan toplanabilir **Net Hacim Etkisi ($Y = \text{İsabet} - p_{\text{ref}} \cdot \text{Deneme}$)** üzerinden hesaplanır.
- **Sezon İçi Dinamik Öğrenme (`BayesianPlayer.update_stats`):** Normal sezon maçları oynandıkça gelen yeni kutu içi (box score) veriler, oyuncunun posterior dağılımını anlık olarak günceller. Oyuncunun form patlaması veya düşüşü, manuel müdahaleye gerek kalmadan projeksiyonlara yansır.
- **Sönümlü Eşlenik Filtreleme (Dinamik Bellek):**
  - **Üstel Sönümleme (Soft Decay):** Geçmiş maç verileri zaman içinde üstel olarak hafifler ($\delta = e^{-\lambda \Delta t}$).
  - **Rol Değişimi ve Takas Sıfırlaması (Hard Reset):** Sezon içi takaslarda modelin geçmişe olan güveni 5'te 1'e düşürülür ($\delta_{\text{event}} = 0.2$); böylece yeni takımdaki ilk 3–5 maç yeni rolü hızla yansıtır.

### 2. Analitik Karar Fonksiyonu (Gaussian CDF $\sum \Phi$)
Geleneksel parçalı Z-skorları ve kırılgan manuel "punt" kuralları yerine, doğrudan kapalı formlu Gauss Kümülatif Dağılım Fonksiyonu ile çalışır:
$$\mathcal{V}(\text{Kadro}) = \sum_{c=1}^{9} \mathbb{P}(\text{Win}_c) = \sum_{c=1}^{9} \Phi\!\left(\frac{\mu_{\text{takım}, c} - \mu_{\text{rakip}, c}}{\sqrt{\sigma^2_{\text{takım}, c} + \sigma^2_{\text{rakip}, c}}}\right)$$
- **Doğal Doygunluk (Natural Saturation):** Kazanma olasılığı %95+ ($Z \ge +2$) olan kategorilerde eğri yataylaşır ($\phi(Z) \to 0$); sistem garantilenmiş kategorilere gereksiz yatırım yapmayı kendiliğinden durdurur.
- **Doğal Punt (Natural Punting):** Kazanma olasılığı %5'in altına ($Z \le -2$) inen kategoriler feda edilir; sermaye başa baş geçen ortadaki kritik kategorilere ($Z \approx 0$) yönlendirilir.
- **Varyans Optimizasyonu:** Geride olunan kategorilerde yüksek tavanlı (volatil) oyuncular, önde olunan kategorilerde ise tabanı sağlam (düşük varyanslı) oyuncular tercih edilir.
- **Eşik Korelasyon Düzeltmesi ($\rho \in [0.10, 0.20]$):** Maç sayısı ve tempo korelasyonu analitik olarak hesaba katılır; lig içi sıralama gücü %100 korunur (Sıralama Değişmezliği).

### 3. Resmi NBA Sakatlık Raporu Ayrıştırıcısı v2 (PDF Ingestion)
- **Sıfır Kimlik Bilgisiyle Doğrudan Veri Çekme:** NBA'in resmi CDN'inden (`https://ak-static.cms.nba.com/referee/injury/...`) her 15 dakikada bir yayımlanan resmi PDF raporlarını otomatik çeker.
- **7 Sütunlu Sayfa Düzeni Motoru:** `pdfplumber` / `pypdf` kütüphaneleriyle saf Python metin ayıklaması. Alt satıra taşan sakatlık gerekçelerini, ortak maç/tarih hücrelerini ve ters isimleri (`"Porter Jr., Kevin"` $\to$ `"Kevin Porter Jr."`) eksiksiz eşleştirir.
- **Veri Sağlık Denetimi ve Karantina:** Rapor tamamlanma ve oyuncu eşleşme oranlarını denetler. Bozuk veya eksik satırlar ana veri tabanını kirletmeden karantinaya alınır.

### 4. SQLite Durum Takibi ve Otomatik İyileşme Tespiti
- **İlişkisel Kalıcılık (`data/processed/injuries.db`):** Oyuncuların sakatlık durumunu, sakatlık bölgesini ve zaman damgalarını `injuries` ve `injury_history` tablolarında saklar.
- **Otomatik İyileşme (Clearance) Algoritması:** Sakat bir oyuncu bir sonraki resmi NBA raporunda yer almadığında, sistem oyuncunun iyileştiğini anında tespit eder, durumunu `AVAILABLE` olarak işaretler ve aktif kadro hesaplarına geri dahil eder.

### 5. IL+ Yuvaları, Yedek Matematiği ve Sağlık Filtreli Transfer (Streaming)
- **Yahoo 2x IL+ (Sakat Yuvası) Optimizasyonu:** Bir oyuncu resmi olarak OUT olduğunda sistem oyuncuyu 2 adet IL+ yuvasından birine yerleştirir.
- **Yedek Terfi Matematiği (Bench Promotion):** İlk 10'daki bir oyuncu IL+'a alındığında, yedekteki en iyi oyuncu ilk 10'a yükseltilir; haftalık oynanan maç sayısı ve sayma istatistikleri kadro kuralı ihlal edilmeden matematiksel olarak artırılır.
- **Sağlık Filtreli Serbest Oyuncu (Waiver) Taraması:** Haftalık serbest oyuncu önerilerinde adaylar canlı sakatlık veri tabanıyla denetlenir. Aşil tendonu kopması veya omuz ameliyatı gibi uzun süreli sakatlığı olan oyuncular karantinaya alınarak haftalık transfer hakkının (maksimum 3) boşa harcanması engellenir.

### 6. Otonom Bulut Senkronizasyonu ve Ayrılmış Bot Dalı
- **GitHub Actions Zamanlanmış İş Akışı (`.github/workflows/daily_fantasy_sync.yml`):** NBA takvimine göre günde 3 kez tam senkronize çalışır:
  - `10:30 TR / 07:30 UTC / 03:30 ET`: Gece maçlarının kapanışı ve Yahoo serbest oyuncu (waiver) iddialarının sonuçlanması.
  - `21:30 TR / 18:30 UTC / 14:30 ET`: NBA resmi öğleden sonra sakatlık raporunun açıklanması.
  - `01:15 TR / 22:15 UTC / 18:15 ET`: İlk maçların başlamasından 45 dakika önce kadro kilitlenmesi (son dakika GTD/OUT durumları).
- **Ayrılmış `nba-fantasy-bot` Dalı (Branch):** Botun oluşturduğu tüm otomatik commit'ler (veri tabanı anlık görüntüleri, lig durumları, raporlar) yalnızca `nba-fantasy-bot` dalına yazılır. `main` dalı tamamen insan yazımı ve tertemiz kalır.
- **Anlık Mobil Telegram Bildirimleri:** Bilgisayar başında olmasanız dahi Telegram Botu üzerinden kadro sağlık durumları, IL+ yerleşim tavsiyeleri ve en iyi serbest oyuncu önerileri doğrudan telefonunuza zengin HTML formatında iletilir.

### 7. Kanonik 14 Takımlı 182 Seçimlik Draft Veri Tabanı (`src/draft_data.py`)
- Canlı snake draft'tan elde edilen tüm 14 takımın ve 182 seçimin doğrulanmış resmi veri tabanı.
- Sezon içi oyuncu ekleme, bırakma (add/drop) ve takasları dinamik olarak kadrolara yansıtır.

---

## 📁 Dizin Yapısı

```text
NbaFantasy/
├── .github/
│   └── workflows/
│       └── daily_fantasy_sync.yml     # Günde 3 kez çalışan otonom GitHub Actions iş akışı
├── config/
│   ├── yahoo_oauth.template.json     # Yahoo OAuth2 yapılandırma şablonu
│   └── yahoo_oauth.json              # Yerel OAuth kimlik bilgileri (.gitignore ile korunur)
├── data/
│   ├── processed/
│   │   ├── active_roster_2026_27.parquet    # Kadro ve oyuncu pozisyon bilgileri
│   │   ├── injuries.db                      # SQLite sakatlık takip ve iyileşme veri tabanı
│   │   ├── player_positions.parquet         # Çoklu pozisyon Yahoo uygunluk tablosu
│   │   ├── schedule_2026_27.parquet         # Resmi sezon maç takvimi
│   │   └── Master_Database_*.xlsx           # Geçmiş sezon oyuncu performans veri tabanları
│   ├── raw/                                 # Ham maç logları ve kutu içi veriler (Parquet)
│   │   └── injuries/                        # İndirilen sakatlık PDF'leri dizini (.gitkeep)
│   └── simulations/                         # Monte Carlo lig simülasyon çıktıları
├── docs/
│   ├── README_TR.md                         # Ayrıntılı Türkçe kullanım ve tanıtım kılavuzu
│   ├── SYSTEM_ARCHITECTURE_TR.md            # Ayrıntılı Türkçe matematiksel mimari dökümanı
│   └── injury_system_architecture_and_peer_review.md # Akran denetimi ve doğrulama raporu
├── reports/
│   ├── league_draft_overview_and_projections.md    # 14 Takımlı draft ve projeksiyon raporu (EN)
│   └── league_draft_overview_and_projections.tr.md # 14 Takımlı draft ve projeksiyon raporu (TR)
├── src/
│   ├── auth_yahoo.py                # Yahoo OAuth2 yetkilendirme ve token yöneticisi
│   ├── bayesian_model.py            # Gamma-Poisson, Beta-Binom ve sezon içi dinamik güncelleyici
│   ├── cloud_sync.py                # Otonom bulut iş akışı çalıştırıcısı ve Telegram bildiricisi
│   ├── data_fetcher.py              # NBA API kadro, takvim ve log çekme boru hattı
│   ├── draft_data.py                # Kanonik 182 seçimlik 14 takım kadro ve draft verisi
│   ├── injury_tracker.py            # SQLite sakatlık kalıcılığı, iyileşme tespiti ve CRUD motoru
│   ├── live_draft_assistant.py      # İleriye bakışlı canlı draft öneri motoru
│   ├── matchup_engine.py            # H2H Gauss CDF, IL+ stashing, yedek matematiği ve waiver filtresi
│   ├── model_ai.py                  # Yapay zeka waiver ve Bayesçi çekirdek kadro koruma mantığı
│   ├── nba_injury_scraper.py        # Resmi 7 sütunlu NBA sakatlık PDF ayrıştırıcısı v2
│   ├── simulate_slot8_scenarios.py  # 8. Sıra Monte Carlo senaryo değerlendiricisi
│   ├── simulator.py                 # Sezon öncesi temel veri yükleyicileri ve araçlar
│   ├── verify_yahoo_names.py        # Oyuncu adı normalizasyonu ve doğrulama testi
│   ├── yahoo_draft_bridge.user.js   # Canlı Yahoo draft odası için Tampermonkey userscript'i
│   └── yahoo_draft_sync.py          # Canlı draft WebSocket/HTTP yerel köprü sunucusu
├── tests/
│   ├── test_ab_validation.py        # A/B karşılaştırmaları, kadro bütünlüğü, yedek matematiği
│   └── test_injury_system.py        # 22 birim testi: Scraper, SQLite CRUD, iyileşme, karantina
├── league_simulator.py              # 14 takımlı çoklu sezon H2H lig simülasyon motoru
├── requirements.txt                 # Python kütüphane bağımlılıkları
├── README.md                        # Ana proje dökümantasyonu (İngilizce)
├── SYSTEM_ARCHITECTURE.md           # Ana matematiksel mimari dökümantasyonu (İngilizce)
└── .gitignore                       # Temiz depo kuralları (PDF'ler, kimlikler, loglar hariç)
```

---

## 🚀 Hızlı Başlangıç

### 1. Depoyu Klonlayın ve Python Ortamını Kurun
```bash
git clone https://github.com/berkbhr/NbaFantasy.git
cd NbaFantasy

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Birim Testlerini Doğrulayın
Tüm sistemi (ayrıştırıcılar, veri tabanı işlemleri, kadro bütünlüğü, Macar algoritması dizilimi ve karşı-olgusal senaryoları doğrulayan 33 birim testi) tek komutla çalıştırın:
```bash
python -m unittest discover tests
```

### 3. Otonom Bulut Senkronizasyonunu Yerelde Test Edin
Son resmi NBA sakatlık raporunu çekmek, `injuries.db` veri tabanını güncellemek, MatchupEngine simülasyonunu çalıştırmak ve özet raporu yazdırmak için:
```bash
python src/cloud_sync.py
```

---

## ☁️ Bulut Otomasyonu Kurulumu (GitHub Actions + Telegram)

Sistem, bilgisayarınızın açık kalmasına gerek kalmadan bulutta günde 3 kez otonom olarak çalışacak şekilde tasarlanmıştır.

### 1. GitHub Repository Secrets Tanımlaması
GitHub Deponuzda **Settings** $\to$ **Secrets and variables** $\to$ **Actions** yolunu izleyin ve şu gizli anahtarları ekleyin:

| Secret Adı | Zorunlu mu? | Açıklama |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Önerilen | Telefona anlık bildirim almak için `@BotFather` bot token'ı. |
| `TELEGRAM_CHAT_ID` | Önerilen | `@userinfobot` botundan alacağınız şahsi Telegram ID'niz. |
| `YAHOO_COOKIE` | Opsiyonel | Yahoo API inceleme aşamasındayken özel lig verileri için oturum çerezi. |

### 2. Otonom Dal İzolasyonu (`nba-fantasy-bot`)
- GitHub Actions iş akışı (`daily_fantasy_sync.yml`) yalıtılmış bir Ubuntu sunucusunda çalışır.
- Her çalışma sonrasında güncellenen veri tabanı (`injuries.db`), kadro durumu ve özet raporlar **yalnızca `nba-fantasy-bot` dalına** commit edilir.
- `main` dalınızdaki commit geçmişi tertemiz kalır; bot hareketleri ana geliştirme geçmişini kirletmez.

---

## 📐 Matematiksel Karar Çerçevesi

### Haftalık Beklenen Kategori Skoru
İki kadronun haftalık eşleşmesinde beklenen kazanılan kategori sayısı:
$$\mathcal{V}(\text{Kadro}) = \sum_{c=1}^{9} \mathbb{P}(\text{Win}_c) = \sum_{c=1}^{9} \Phi\!\left(\frac{\mu_{\text{takım}, c} - \mu_{\text{rakip}, c}}{\sqrt{\sigma^2_{\text{takım}, c} + \sigma^2_{\text{rakip}, c}}}\right)$$

### Lig Geneli Korelasyon Yapısı ve Sıralama Değişmezliği
NBA sayma kategorileri (sayı, ribaund, asist, üçlük) takım temposu ve maç sayısı nedeniyle ortak bir korelasyona ($\rho \in [0.10, 0.20]$) sahiptir. Gerçekleştirdiğimiz ampirik analiz, $\rho$ parametresinin kazanma oranlarını %50 merkezine doğru yumuşatırken lig içi sıralamayı birebir koruduğunu doğrulamıştır:

| Sıra | Slot | Takım Adı | $\rho = 0.00$ Kazanma% | $\rho = 0.10$ Kazanma% | $\rho = 0.20$ Kazanma% | Beklenen Kat. / 9 |
|---|---|---|---|---|---|---|
| **#1** | **S8** | **Berk's Best Team** | **%78.6** | **%72.5** | **%69.2** | **5.63** |
| #2 | S4 | Houston Buckets | %59.9 | %57.5 | %56.3 | 4.87 |
| #3 | S2 | Mordor Tulums | %59.6 | %57.3 | %56.2 | 4.83 |
| #4 | S7 | Samurai Strikers | %57.0 | %55.3 | %54.4 | 4.75 |
| #5 | S13 | SILE BULLS | %55.5 | %54.1 | %53.4 | 4.70 |

Tüm matematiksel ispatlar, Dirichlet/Gamma eşlenik formülleri ve yedek optimizasyon teoremleri için [SYSTEM_ARCHITECTURE_TR.md](SYSTEM_ARCHITECTURE_TR.md) dökümanını inceleyebilirsiniz.

---

## 📄 Lisans
Bu proje MIT Lisansı altında lisanslanmıştır - ayrıntılar için [LICENSE](LICENSE) dosyasına bakabilirsiniz.

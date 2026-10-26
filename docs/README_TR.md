# 🏀 NBA Fantasy Olasılıksal Karar ve Simülasyon Paketi (H2H 9-Kategori)

NBA Fantasy Head-to-Head (H2H) 9-Kategori formatı için tasarlanmış; **Eşlenik Bayes Çıkarımı (Conjugate Bayesian Inference)**, **Analitik Karar Teorisi (Analytical Decision Theory)**, **Kalite-Ağırlıklı Çapraz Pozisyonel Sakatlık Dağıtımı (Quality-Elastic Teammate Injury Redistribution)** ve **Otonom Bulut CI/CD Boru Hatları** ile güçlendirilmiş, endüstriyel standartta bir nicel modelleme, simülasyon ve sezon içi canlı karar motoru.

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

### 3. Kalite-Ağırlıklı Çapraz Pozisyonel Sakatlık Dağıtımı ve Tersinir İyileşme
- **Pozisyonel Derinlik Şemaları ($k = 1, 2, 3, \dots$):** 30 NBA takımının tamamını birincil pozisyon havuzlarına (`G`, `F`, `C`) ayırır; oyuncuları yetenek puanı ve baz beklenen dakikalarına göre sıralar.
- **Kalite-Esnek Çapraz Pozisyonel Taşma (Quality-Elastic Cross-Positional Spillover):** Bir ilk-5 oyuncusu OUT olduğunda (örneğin pivot Maxime Raynaud OUT) ve aynı pozisyondaki doğrudan yedek düşük yetenekliyse ($S_{\text{same}}$ düşük), oluşan yetenek farkı $\Delta S = \max(0, S_{\text{adj}} - S_{\text{same}})$ komşu forvet/kanat rotasyonuna çapraz dakika aktarımı tetikler (örneğin forvet Precious Achiuwa kısa beşler / small-ball sayesinde $+2.0$ ila $+4.0$ dakika ek süre alır).
- **Role Bağlı Dakika Tavanları:** Genişletilen dakikaları gerçekçi fiziksel limitlerle sınırlar (ilk-5 oyuncuları için maks 35.5 dk, rotasyon oyuncuları için maks 31.0 dk) ve genişleyen rolün belirsizliğini modellemek için varyansı artırır ($+0.35 \cdot \Delta M^2$).
- **Kesin Matematiksel Tersinirlik (Strict Reversibility):** Sakat oyuncular iyileştiğinde, tüm kadro dakikaları ve istatistiksel dağılımlar tek bir sapma olmadan baz değerlerine geri döner:
  $$M_{\text{base}} < M_{\text{one\_out}} < M_{\text{both\_out}} \quad \text{ve} \quad M_{\text{recovered}} \equiv M_{\text{base}}$$

### 4. Çift Sakatlık Motoru: Resmi NBA Hakem PDF'leri + 30 Takımlı ESPN API
- **Resmi NBA Hakem Raporu Ayrıştırıcısı v2:** NBA resmi CDN'inden (`https://ak-static.cms.nba.com/referee/injury/...`) her 15 dakikada bir yayımlanan resmi PDF'leri sıfır kimlik bilgisiyle çeker. 7 sütunlu saf Python düzen ayrıştırıcısı, sağlık denetimi ve karantina mekanizması içerir.
- **30 Takımlı ESPN / Rotowire Canlı Beslemesi (`sync_espn_injuries`):** Maç günü olmayan veya hakem raporlarında henüz listelenmeyen haftalık/uzun vadeli sakatlıkları yakalayan genel, sıfır kimlik bilgili REST API beslemesi.
- **Otomatik İyileşme ve Mutabakat Denetimi (`reconcile_recovered=True`):** Sakat bir oyuncu bir sonraki API yanıtında veya hakem raporunda yer almadığında, motor oyuncunun kaydını `injuries.db` aktif tablosundan otomatik temizler, `injury_snapshots` tablosuna `CLEARED` denetim kaydı düşer ve oyuncuyu aktif kadro projeksiyonlarına geri döndürür.

### 5. 1-Tıkla Yahoo Tarayıcı Senkronizasyon Köprüsü (`src/yahoo_browser_sync.py`)
- **Sıfır Cookie / Sıfır Şifre / Sıfır OAuth Onayı:** `http://127.0.0.1:8765` üzerinde çalışan son derece hafif yerel bir köprü sunucusu.
- **1-Tıkla Yer İmi (Bookmarklet):** Yahoo Fantasy sekmeniz açıkken yer imi çubuğundaki **`🏀 NBA Fantasy Sync`** butonuna tıkladığınızda, tarayıcınız kendi içinde (`same-origin`) yaklaşık ~2 saniyede paralel olarak şunları tarar:
  1. **14 Takımın Canlı Kadroları ve Yuva Dağılımları:** `/nba/64691/1` .. `/14` sayfalarını okuyarak aktif yuvaları (`PG`..`UTIL`, `BN`), `IL`/`IL+` yerleşimlerini ve yuvasız sakatları eksiksiz çıkarır.
  2. **Canlı Lig İşlemleri:** `/nba/64691/transactions` sayfasındaki son ekleme, bırakma, waiver ve takas geçmişini çeker.
  3. **Canlı Skor Tablosu & Kalan Maçlar:** `/nba/64691/matchup` sayfasından her iki takımın 11 kategorideki canlı gerçekleşen istatistiklerini (`FGM`, `FGA`, `FTM`, `FTA`, `3PTM`, `PTS`, `REB`, `AST`, `ST`, `BLK`, `TO`) ve kalan maç sayılarını içeri aktarır.
  4. **Kesin Boştaki Oyuncu (Free Agent) Havuzunun Tespiti:** 14 takımın kadrosunu tarayarak boştaki havuzu matematiksel olarak kesinleştirir:
     $$\text{Gerçek Serbest Oyuncu Havuzu (FA)} = \text{Tüm NBA Havuzu} \setminus \bigcup_{t=1}^{14} \text{Kadro}_t$$

### 6. Koşullu Projeksiyonlar ve Dinamik Add/Drop Optimizasyonu
- **Canlı Skor Koşullaması (`combine_live_and_remaining_dist`):** Haftalık öngörücü dağılımları gerçekleşen istatistikler $X_{\text{actual}}$ ve kalan maç oranı $f_{\text{rem}}$ ile koşullandırır:
  $$\mu_{\text{final}} = X_{\text{actual}} + f_{\text{rem}} \cdot \mu_{\text{rem}}, \qquad \sigma^2_{\text{final}} = f_{\text{rem}} \cdot \sigma^2_{\text{rem}}$$
- **Marjinal Beklenen Galibiyet Maksimizasyonu ($\Delta \sum_{c=1}^9 \Phi_c$):** Serbest oyuncu adaylarını genel maç başı ortalamalara göre değil, o haftaki canlı eşleşmeyi kazanma olasılığına yapacağı doğrudan net marjinal katkıya göre sıralar.
- **Otomatik IL+ Yuva Tespiti:** Sakat bir oyuncu IL+'a kaydırıldığında oluşan boş kadro kontenjanını (`has_open_slot = True`) algılar ve mevcut kadrodan kimseyi bırakmadan doğrudan `ADD (Boş Yuva / IL+)` önerir.
- **Çekirdek Korumalı Takas Değerlendirmesi:** Kadro tamamen doluyken yedek oyuncuları karşı-olgusal olarak simüle eder; ancak takımın dokunulmaz yıldız çekirdeğini (Core Stars) kesinlikle korur.

### 7. Çok Kanallı Zengin Bildirimler (Telegram + Discord)
- Telegram Bot API (HTML) ve Discord Webhook (Markdown) üzerinden mobil cihazınıza veya sunucunuza anlık özet kartları iletir:
  - **Canlı Eşleşme Skoru ve Kazanma Olasılığı:** örn. `Berk's Best Team: 4.70 - 4.30 vs SILE BULLS (%52 Kazanma)`.
  - **Kategori Ayrımı:** Güçlü olunan kategoriler, ortadaki kritik swing kategorileri ve rakibin önde olduğu alanlar.
  - **Sağlık ve IL+ Uyarıları:** IL+'a taşınması gereken `OUT` oyuncular ve maç saati belirsiz `GTD` riskleri.
  - **En İyi Add/Drop Önerileri:** $\Delta E[\text{Wins}]$ ve kalan takvim maçlarına göre sıralı en değerli serbest oyuncular.
  - **Karşılaştırmalı Eşleşme Tablosu:** Canlı gerçekleşen istatistikler ile hafta sonu beklenen final projeksiyonlarını yan yana gösteren karşılaştırma tablosu.
  - **Son Lig İşlemleri:** 14 menajerin son transfer hareketlerinin denetim dökümü.

### 8. Otonom Bulut CI/CD İş Akışı (`.github/workflows/daily_fantasy_sync.yml`)
- NBA takviminin kritik operasyonel saatlerine göre günde 3 kez GitHub Actions üzerinde otonom çalışır:
  - `10:30 TR / 07:30 UTC / 03:30 ET`: Gece maçlarının tamamlanması, skor tablosu güncellemesi ve waiver sonuçları.
  - `21:30 TR / 18:30 UTC / 14:30 ET`: NBA resmi öğleden sonra sakatlık raporu ve pozisyonel derinlik güncellemeleri.
  - `01:15 TR / 22:15 UTC / 18:15 ET`: İlk maçların başlamasından 45 dakika önce kadro kilitlenmesi (son dakika GTD/OUT tespiti).
- **Ayrılmış `nba-fantasy-bot` Dalı:** Otomatik bulut işlemleri güncellenen veri tabanlarını (`injuries.db`), lig durumlarını (`league_state.json`) ve özet raporları yalnızca `nba-fantasy-bot` dalına commit eder (`[skip ci]`). `main` dalı tamamen temiz ve insan yapımı kalır.
- Yönetici raporları 14 gün boyunca indirilebilir GitHub Actions artefaktı olarak saklanır.

---

## 📁 Dizin Yapısı

```text
NbaFantasy/
├── .github/
│   └── workflows/
│       └── daily_fantasy_sync.yml     # Günde 3 kez çalışan otonom GitHub Actions iş akışı
├── config/
│   ├── telegram.template.json        # Telegram / Discord bildirim yapılandırma şablonu
│   ├── telegram.json                 # Yerel bot kimlik bilgileri (.gitignore ile korunur)
│   ├── yahoo_oauth.template.json     # Yahoo OAuth2 yapılandırma şablonu
│   └── yahoo_oauth.json              # Yerel OAuth kimlik bilgileri (.gitignore ile korunur)
├── data/
│   ├── processed/
│   │   ├── active_roster_2026_27.parquet    # Kadro ve oyuncu pozisyon bilgileri
│   │   ├── injuries.db                      # SQLite sakatlık takip, iyileşme ve mutabakat veri tabanı
│   │   ├── league_state.json                # Canlı 14 takım kadroları ve IL yuva atamaları (JSON)
│   │   ├── live_matchup.json                # Canlı skor tablosu ve kalan maçlar (JSON)
│   │   ├── player_positions.parquet         # Çoklu pozisyon Yahoo uygunluk tablosu
│   │   └── schedule_2026_27.parquet         # Resmi sezon maç takvimi
│   └── raw/                                 # Ham maç logları ve kutu içi veriler (Parquet)
│       └── injuries/                        # İndirilen sakatlık PDF'leri dizini (.gitkeep)
├── docs/
│   ├── README_TR.md                         # Ayrıntılı Türkçe kullanım ve tanıtım kılavuzu
│   ├── SYSTEM_ARCHITECTURE_TR.md            # Ayrıntılı Türkçe matematiksel mimari dökümanı
│   └── injury_system_architecture_and_peer_review.md # Akran denetimi ve doğrulama raporu
├── reports/
│   ├── latest_cloud_summary.md              # Yönetici senkronizasyon özeti ve canlı projeksiyonlar
│   ├── league_draft_overview_and_projections.md    # 14 Takımlı draft ve projeksiyon raporu (EN)
│   └── league_draft_overview_and_projections.tr.md # 14 Takımlı draft ve projeksiyon raporu (TR)
├── src/
│   ├── auth_yahoo.py                # Yahoo OAuth2 yetkilendirme ve otomatik lig keşfi
│   ├── bayesian_model.py            # Gamma-Poisson, Beta-Binom, dinamik öğrenme ve derinlik takviyeleri
│   ├── cloud_sync.py                # Otonom bulut iş akışı çalıştırıcısı ve bildirim dağıtıcısı
│   ├── data_fetcher.py              # NBA API kadro, takvim ve log çekme boru hattı
│   ├── draft_data.py                # Kanonik 182 seçimlik 14 takım kadro ve draft verisi
│   ├── injury_tracker.py            # SQLite sakatlık kalıcılığı, ESPN senkronu, mutabakat ve denetim
│   ├── live_draft_assistant.py      # Canlı asistan, sakatlık senkronu ve derinlik ayarlamaları
│   ├── matchup_engine.py            # Gauss CDF, kalite-esnek taşma, canlı skor matematiği ve waiver
│   ├── model_ai.py                  # Çekirdek korumalı Bayesçi karar ve add/drop optimizasyonu
│   ├── nba_injury_scraper.py        # Resmi 7 sütunlu NBA sakatlık PDF ayrıştırıcısı v2
│   ├── simulator.py                 # Sezon öncesi temel veri yükleyicileri ve araçlar
│   ├── yahoo_browser_sync.py        # 1-Tıkla yer imi yerel köprü sunucusu (Canlı Yahoo senkronu)
│   └── yahoo_draft_sync.py          # Yahoo OAuth2 REST API istemcisi ve draft odası köprüsü
├── tests/
│   ├── test_ab_validation.py        # 29 test: A/B doğrulama, yedek matematiği, 14 takım simetrisi
│   ├── test_browser_sync_and_scoreboard.py # 2 test: Tarayıcı senkronu, FA havuzu ve canlı skor tablosu
│   ├── test_injury_system.py        # 4 test: Scraper, SQLite CRUD, iyileşme, B2B dinlendirme
│   ├── test_notifications_and_workflow.py # 3 test: Workflow sentaksı, cron ve bildirim ayrıştırıcıları
│   └── test_reversible_and_spillover.py   # 3 test: Tersinir iyileşme, ESPN mutabakatı, çapraz pozisyonel taşma
├── requirements.txt                 # Python kütüphane bağımlılıkları
├── README.md                        # Ana proje dökümantasyonu (İngilizce)
├── SYSTEM_ARCHITECTURE.md           # Ana matematiksel mimari dökümantasyonu (İngilizce)
└── .gitignore                       # Temiz depo kuralları (PDF'ler, kimlikler, loglar hariç)
```

---

## 🚀 Hızlı Başlangıç

### 1. Depoyu Klonlayın ve Python Ortamını Kurun
```powershell
git clone https://github.com/berkbhr/NbaFantasy.git
cd NbaFantasy

python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

> **Windows PowerShell Kullanıcıları İçin Önemli Not:** Windows Store alias sorununu (`Python was not found...`) engellemek için komutları doğrudan `.\.venv\Scripts\python.exe` (ve pip komutlarını `.\.venv\Scripts\pip.exe`) ile çalıştırın. Türkçe karakterlerin ve emojilerin düzgün görüntülenmesi için UTF-8 kodlamasını ayarlayın:
> ```powershell
> $env:PYTHONIOENCODING="utf-8"
> ```

### 2. Birim Testlerini Doğrulayın
Tüm modülleri (ayrıştırıcılar, SQLite mutabakatı, kadro simetrisi, tersinir iyileşme ve bildirim modelleri) kapsayan kapsamlı test paketini çalıştırın:
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```
*(Tüm 41 birim ve entegrasyon testi 0 hata ile başarıyla tamamlanmalıdır).*

---

## 🔄 Sezon İçi Canlı Senkronizasyon Yöntemleri

### Yöntem A: 1-Tıkla Yahoo Tarayıcı Senkronizasyon Köprüsü (En Hızlı, Sıfır Kimlik Bilgisi)
Yahoo Developer API izinleri ve token yenilemeleri ile uğraşmadan canlı kadroları, IL+ yuvalarını ve canlı skorları senkronize etmenin en pratik yolu:

1. **Yerel köprü sunucusunu başlatın:**
   ```powershell
   .\.venv\Scripts\python.exe src/yahoo_browser_sync.py
   ```
2. Tarayıcınızda otomatik olarak `http://127.0.0.1:8765/` kontrol paneli açılacaktır.
3. Paneldeki yeşil **`🏀 NBA Fantasy Sync`** butonunu farenizle tutup tarayıcınızın **Yer İmleri Çubuğuna (Bookmarks Bar)** sürükleyip bırakın *(bunu sadece ilk kurulumda 1 kez yapmanız yeterlidir)*.
4. Tarayıcınızda oturum açmış olduğunuz **Yahoo Fantasy Matchup** sayfanıza gidin.
5. Yer imi çubuğundaki **`🏀 NBA Fantasy Sync`** butonuna tıklayın!
   - Yaklaşık ~2 saniye içinde 14 takımın kadrosunu, IL+ atamalarını ve canlı skorları tarar.
   - `data/processed/league_state.json` ve `live_matchup.json` dosyalarını günceller.
   - Karar motorunu tetikler ve Telegram / Discord bildirimlerinizi anında cep telefonunuza iletir.

### Yöntem B: Yahoo OAuth2 REST API (Otomatik)
Resmi bir Yahoo Developer App kaydınız varsa:
1. `config/yahoo_oauth.template.json` dosyasını `config/yahoo_oauth.json` olarak kopyalayın; `client_id` ve `client_secret` bilgilerinizi girin.
2. Otomatik yetkilendirme ve lig keşif betiğini çalıştırın:
   ```powershell
   .\.venv\Scripts\python.exe src/auth_yahoo.py
   ```
   - Yetkilendirme kodunu otomatik token'a çevirir veya mevcut token'ı yeniler.
   - Lig anahtarınızı (örn. `454.l.64691`) ve takım anahtarınızı (örn. `454.l.64691.t.8`) otomatik bulur.
   - Tüm parametreleri `config/yahoo_oauth.json` dosyasına kaydeder.

### Yöntem C: Bulut Senkronizasyonunu Yerelde Manuel Çalıştırma
Tüm sakatlıkları, derinlik takviyelerini, skor matematiğini ve bildirimleri yerel makinenizde tek seferde çalıştırmak için:
```powershell
.\.venv\Scripts\python.exe src/cloud_sync.py
```

---

## 📱 Anlık Bildirim Kurulumu (Telegram & Discord)

Motor, zengin biçimlendirilmiş özet kartlarını doğrudan telefonunuza veya Discord sunucunuza iletebilir.

1. `config/telegram.template.json` dosyasını `config/telegram.json` olarak kopyalayın:
   ```json
   {
     "bot_token": "TELEGRAM_BOT_TOKEN_BURAYA",
     "chat_id": "TELEGRAM_CHAT_ID_BURAYA",
     "discord_webhook_url": "OPSIYONEL_DISCORD_WEBHOOK_URL_BURAYA"
   }
   ```
2. **Telegram Kurulumu:**
   - `@BotFather` üzerinden bot oluşturup `bot_token` bilginizi alın.
   - `@userinfobot` botuna mesaj atarak şahsi sayısal `chat_id` bilginizi öğrenin.
3. **Discord Kurulumu (Opsiyonel):**
   - Discord kanalınızda Webhook oluşturun (`Kanal Ayarları -> Entegrasyonlar -> Webhook'lar`) ve URL'yi yapıştırın.

---

## ☁️ GitHub Actions Bulut Otomasyonu Kurulumu

Sistem, kişisel bilgisayarınızın açık kalmasına gerek kalmadan bulutta günde 3 kez otonom olarak çalışacak şekilde tasarlanmıştır.

### 1. GitHub Repository Secrets Tanımlaması
GitHub Deponuzda **Settings** $\to$ **Secrets and variables** $\to$ **Actions** yolunu izleyin ve şu gizli anahtarları ekleyin:

| Secret Adı | Zorunlu mu? | Açıklama |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Önerilen | Telefona anlık bildirim almak için `@BotFather` bot token'ı. |
| `TELEGRAM_CHAT_ID` | Önerilen | `@userinfobot` botundan alacağınız şahsi Telegram ID'niz. |
| `DISCORD_WEBHOOK_URL` | Opsiyonel | Discord kanalına bildirim göndermek için webhook URL'si. |
| `YAHOO_OAUTH_JSON` | Önerilen | Yerel `config/yahoo_oauth.json` dosyanızın tam JSON metni. |
| `YAHOO_CLIENT_ID` | Opsiyonel | Ayrı ayrı girilmek istenirse Yahoo Developer App Client ID. |
| `YAHOO_CLIENT_SECRET` | Opsiyonel | Ayrı ayrı girilmek istenirse Yahoo Developer App Client Secret. |
| `YAHOO_REFRESH_TOKEN` | Opsiyonel | Ayrı ayrı girilmek istenirse Yahoo OAuth2 Refresh Token. |

### 2. Otonom Dal İzolasyonu (`nba-fantasy-bot`)
- GitHub Actions iş akışı (`daily_fantasy_sync.yml`) yalıtılmış bir Ubuntu sunucusunda çalışır.
- Her çalışma sonrasında güncellenen veri tabanı (`injuries.db`), lig kadroları (`league_state.json`) ve özet raporlar (`reports/latest_cloud_summary.md`) **yalnızca `nba-fantasy-bot` dalına** commit edilir (`[skip ci]`).
- `main` dalınızdaki commit geçmişi tertemiz ve insan yapımı kalır; bot hareketleri geliştirme geçmişini kirletmez.
- Detaylı yönetici raporları 14 gün boyunca indirilebilir GitHub Actions artefaktı olarak saklanır.

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
Bu proje MIT Lisansı altında lisanslanmıştır - ayrıntılar için [LICENSE](../LICENSE) dosyasına bakabilirsiniz.

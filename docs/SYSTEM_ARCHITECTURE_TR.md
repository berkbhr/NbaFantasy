# 🏀 NBA Fantasy Karar ve Simülasyon Motoru - Sistem Mimarisi

Bu döküman; NBA Fantasy Head-to-Head (H2H) 9-Kategori formatı için geliştirilmiş, **Olasılıksal Karar Teorisi (Probabilistic Decision Theory)**, **Eşlenik Bayes Çıkarımı (Conjugate Bayesian Inference)** ve **Otonom Bulut CI/CD Boru Hatları** temellerine dayanan karar ve simülasyon sisteminin resmi matematiksel, istatistiksel ve yazılım mimarisi şartnamesidir.

---

## 1. Yönetici Özeti ve Temel İlke

Geleneksel fantezi basketbol analizleri üç temel zaafiyete sahiptir:
1. **Doğrusal Nokta Tahminleri (Point Estimates):** Maç içi dakika esnekliğini, oyuncunun gece-gece sergilediği varyansı ve ikili eşleşme dalgalanmalarını tamamen yok sayan statik maç başı ortalamalara ($\bar{x}$) dayanmak.
2. **Keyfi Sezgisel Kurallar (Arbitrary Heuristics):** Matematiksel tutarlılığı olmayan Z-skoru toplamları, elle belirlenen yapay "punt" tercihleri ve keyfi doygunluk tavanları ($Z > 2.5$).
3. **Statik Körlük:** Resmi sakatlık raporlarına, sezon içi rol değişimlerine ve serbest oyuncu (waiver) fırsatlarına dinamik olarak anında adapte olamamak.

Bu platform, sezgisel yamalar yerine **Analitik Karar Teorisi**ne dayanan **Tekil ve Birleşik bir Amaç Fonksiyonu** kullanır:

$$\max_{\mathcal{R}} \mathcal{V}(\mathcal{R}) = \sum_{c=1}^{9} \mathbb{P}(\text{Win}_c) = \sum_{c=1}^{9} \Phi\!\left(\frac{\mu_{\text{takım}, c} - \mu_{\text{rakip}, c}}{\sqrt{\sigma^2_{\text{takım}, c} + \sigma^2_{\text{rakip}, c}}}\right)$$

Sistemin tüm yaşam döngüsü—draft öncesi ileriye bakışlı simülasyonlardan canlı draft oyuncu değerlemesine, Macar algoritması tabanlı günlük kadro diziliminden sezon içi Bayesçi öğrenmeye, resmi sakatlık PDF ayrıştırmasından 2 IL+ yuvası yönetimine ve sağlık filtreli serbest oyuncu transferine kadar—yalnızca bu tekil matematiksel hedefi maksimize eder.

---

## 2. Veri Mühendisliği ve Depolama Mimarisi

Veri boru hattı, tam tekrarlanabilirlik, denetlenebilirlik ve yüksek hız sağlamak amacıyla Medalyon Mimarisi (Medallion Architecture) ilkelerine göre tasarlanmıştır:

```
+-----------------------------------------------------------------------------+
|                           VERİ BORU HATTI MİMARİSİ                          |
+-----------------------------------------------------------------------------+
|                                                                             |
|  [NBA API / CDN]          [Yahoo Fantasy API]        [Resmi NBA PDF]        |
|         │                         │                           │             |
|         ▼                         ▼                           ▼             |
|   data_fetcher.py         auth_yahoo.py / sync       nba_injury_scraper.py  |
|         │                         │                           │             |
|         ▼                         ▼                           ▼             |
|  [Ham Parquet]            [draft_data.py]            [injury_tracker.py]    |
|  - player_logs_*.parquet  - 182 Draft Seçimi         - injuries.db (SQLite) |
|  - team_logs_*.parquet    - 14 Takım Kadrosu         - Otomatik İyileşme    |
|         │                         │                           │             |
|         └─────────────────────────┼───────────────────────────┘             |
|                                   │                                         |
|                                   ▼                                         |
|                       [bayesian_model.py]                                   |
|                       - Gamma-Poisson (Sayma İstatistikleri)                |
|                       - Beta-Binom (Şut Yüzdeleri)                          |
|                       - Sezon İçi Dinamik Maç Güncellemeleri                |
|                                   │                                         |
|                                   ▼                                         |
|                       [matchup_engine.py]                                   |
|                       - Gauss Kümülatif Dağılımı (Sum Phi)                  |
|                       - Macar Algoritması (10 Aktif + 3 Yedek)              |
|                       - 2x IL+ Sakat Yuvası ve Yedek Terfisi                |
|                       - Sağlık Filtreli Waiver Streaming                    |
|                                   │                                         |
|                                   ▼                                         |
|                       [Otonom Bulut Senkronizasyonu]                        |
|                       - GitHub Actions (Günde 3 Kez)                        |
|                       - 'nba-fantasy-bot' Dalı İzolasyonu                   |
|                       - Telegram Bot Anlık Bildirimleri                     |
|                                                                             |
+-----------------------------------------------------------------------------+
```

### Depolama Katmanları Şartnamesi
1. **Ham Veri Katmanı (`data/raw/`):**
   - NBA API'den çekilen maç bazlı oyuncu ve takım kutu içi verileri (Box Scores) yüksek performanslı sütunsal Apache Parquet formatında (`player_logs_*.parquet`) saklanır.
   - NBA resmi CDN'inden indirilen geçici sakatlık PDF'leri `data/raw/injuries/` dizininde toplanır (depo boyutunu şişirmemek için `.gitignore` ile repo dışı tutulur).
2. **İşlenmiş İlişkisel Katman (`data/processed/`):**
   - `injuries.db`: Aktif sakatlıkları, tarihsel kayıtları, iyileşme zaman damgalarını ve karantina loglarını tutan ilişkisel SQLite veri tabanı.
   - `active_roster_2026_27.parquet`: Aktif kadro, oyuncu ID'leri ve pozisyon eşleşmeleri.
   - `player_positions.parquet`: Çoklu pozisyon Yahoo Fantasy uygunluk tablosu (`PG, SG, G, SF, PF, F, C, UTIL, BN`).
   - `schedule_2026_27.parquet`: 82 maçlık resmi sezon takvimi, maç ID'leri ve hafta numaraları.
3. **Simülasyon Çıktıları (`data/simulations/`):**
   - Monte Carlo lig simülasyonları ve senaryo analiz sonuçları (`slot8_2026_27_scenarios_final.json`).

---

## 3. Eşlenik Bayes Çıkarımı ve Sezon İçi Dinamik Öğrenme

Oyuncu performansı tekil bir ortalama olarak değil, **Öngörücü Olasılık Dağılımları (Predictive Probability Distributions)** ile modellenir.

### 3.1. Sayılabilir Kategoriler: Gamma-Poisson Eşlenik Modeli
- **Kategoriler:** Sayı (PTS), Ribaund (REB), Asist (AST), Top Çalma (STL), Blok (BLK), İsabetli Üçlük (3PM), Top Kaybı (TOV).
- **Maruziyet (Exposure) Parametrizasyonu:** Oyuncu verisi soyut maç sayısı yerine sahada kaldığı **Süre ($m$ dakika)** ile koşullandırılır.
- **Formülasyon:**
  - Dakika başına oran $\lambda \sim \text{Gamma}(\alpha, \beta)$, burada $\alpha$ birikmiş sanal olayları, $\beta$ ise birikmiş sanal dakikaları temsil eder.
  - $m$ dakika süre verildiğinde gözlemlenen sayım: $X \mid \lambda, m \sim \text{Poisson}(\lambda \cdot m)$.
- **Eşlenik Posterior Güncellemesi:**
  Yeni bir maçta $x_i$ istatistiği ve $m_i$ dakikası gözlemlendiğinde:
  $$\alpha_{t} = \delta \, \alpha_{t-1} + x_i, \quad \beta_{t} = \delta \, \beta_{t-1} + m_i$$
- **Öngörücü Dağılım (Negatif Binom):**
  $\lambda$ üzerinden integral alındığında Negatif Binom öngörücü dağılımı elde edilir:
  $$\mathbb{E}[X \mid m] = m \cdot \frac{\alpha}{\beta}, \quad \text{Var}(X \mid m) = m \cdot \frac{\alpha}{\beta} \left(1 + \frac{m}{\beta}\right) = \mu + \frac{\mu^2}{\alpha}$$

### 3.2. Şut Yüzdeleri: Beta-Binom Eşlenik Modeli
- **Kategoriler:** Saha İçi Yüzdesi (FG%), Serbest Atış Yüzdesi (FT%).
- **Formülasyon:**
  - Şut isabet başarısı $p \sim \text{Beta}(\alpha, \beta)$, burada $\alpha = \text{İsabet}$ ve $\beta = \text{Kaçan}$ şutlardır.
  - $N$ denemede gözlemlenen isabet $K$: $K \mid p, N \sim \text{Binom}(N, p)$.
- **Doğrusal Net Hacim Etkisi Dönüşümü (Net Volume Impact):**
  Yüzdeler kadrodaki oyuncular arasında doğrudan toplanamaz. Yüzdeleri doğrusal olarak toplanabilir kılmak ve şut hacmini yansıtmak amacıyla her oyuncunun katkısı lig referans oranına ($p_{\text{ref}}$) göre **Net İsabet Etkisi**ne dönüştürülür ($p_{\text{ref, FG}} \approx 0.470$, $p_{\text{ref, FT}} \approx 0.780$):
  $$Y = \text{İsabet} - p_{\text{ref}} \cdot \text{Deneme} = \text{Deneme} \cdot (p - p_{\text{ref}})$$
  Bu sayede maç başına 2 serbest atış atan %90'lık bir bench oyuncusunun, maç başına 10 serbest atış atan %82'lik bir ana skorerden daha az net fayda sağladığı doğal olarak hesaba katılır.

### 3.3. Sönümlü Eşlenik Filtreleme (Dinamik Bellek)
Geçmiş sezon verileriyle mevcut form arasındaki dengeyi kurmak için:
- **Hafif Günlük Sönümleme (Soft Daily Decay):** Eski gözlemler zamanla üstel olarak sönümlenir:
  $$\delta = e^{-\lambda \Delta t}, \quad \lambda = \frac{\ln 2}{t_{1/2}}$$
- **Olay Bazlı Rol Sıfırlaması (Hard Reset - Takaslar):**
  Bir oyuncu takaslandığında veya ilk 5'e yükseldiğinde:
  $$\delta_{\text{olay}} = 0.20$$
  Dakika başı yetenek oranı ($\frac{\alpha}{\beta}$) korunurken modelin geçmişe olan güveni (efektif örneklem hacmi $\beta$) 5'te 1'e düşürülür. Yeni takımdaki ilk 3–5 maç hızla posteriorda baskın hale gelir.

### 3.4. Sezon İçi Dinamik Maç Güncellemesi (`BayesianPlayer.update_stats`)
Normal sezon ilerledikçe her yeni maç logunda `update_stats` devreye girer:
1. Önceki parametreleri üstel olarak sönümler.
2. Maçın istatistik ve süre verilerini ekler.
3. Beklenen süreyi Üstel Ağırlıklı Hareketli Ortalama (EWMA) ile günceller:
   $$m_{\text{proj}, t} = \alpha_m \cdot m_{\text{maç}} + (1 - \alpha_m) \cdot m_{\text{proj}, t-1}$$
4. 9 kategorinin tamamında yeni öngörücü ortalama $\mu_c$ ve varyansları $\sigma^2_c$ hesaplar.

---

## 4. Analitik Karar Teorisi ve H2H Gauss Kümülatif Dağılımı ($\sum \Phi$)

### 4.1. Birleşik Amaç Fonksiyonu
Haftalık bir eşleşmede $A$ kadrosunun rakip $B$ kadrosuna karşı $c$ kategorisini kazanma olasılığı, Standart Normal Kümülatif Dağılım Fonksiyonu ($\Phi$) ile kapalı formda hesaplanır:

$$\mathbb{P}(\text{Win}_c) = \Phi\!\left(\frac{\mu_{A, c} - \mu_{B, c}}{\sqrt{\sigma^2_{A, c} + \sigma^2_{B, c}}}\right) = \Phi(z_c)$$

$$\mathcal{V}(\mathcal{R}) = \sum_{c=1}^{9} \Phi(z_c)$$

### 4.2. Kendiliğinden Ortaya Çıkan Üç Stratejik Davranış
1. **Doğal Doygunluk (Natural Saturation):**
   $z_c \ge +2.0$ ($\mathbb{P} > %97.7$) olduğunda normal yoğunluk eğrisi yataylaşır ($\phi(z) \to 0$). O kategoriye eklenecek ilave istatistiğin marjinal faydası sıfıra yaklaşır. Sistem garantilenmiş kategorilere boşuna kaynak harcamaz.
2. **Doğal Punt (Natural Punting):**
   $z_c \le -2.0$ ($\mathbb{P} < %2.3$) olduğunda alt kuyruk da yataylaşır ($\phi(z) \to 0$). Sistem tek bir oyuncuyla kurtarılamayacak kategorileri feda eder ve kaynaklarını ortadaki başa baş kategorilere ($z_c \approx 0$, marjinal eğim $\phi(0) \approx 0.3989$ maksimumdur) yönlendirir.
3. **Varyans Optimizasyonu (Risk Tercihi):**
   $\Phi(z)$'nin standart sapmaya ($\sigma$) göre türevi alındığında:
   $$\frac{\partial \Phi(z)}{\partial \sigma} = -\frac{\mu_A - \mu_B}{\sigma^2} \phi(z)$$
   - Gerideyken ($\mu_A < \mu_B$), $-\frac{\mu_A - \mu_B}{\sigma^2} > 0$ olur: varyansı artırmak **kazanma olasılığını artırır**. Sistem gerideyken volatil ve patlayıcı oyuncuları tercih eder.
   - Öndeyken ($\mu_A > \mu_B$), varyansı artırmak **kazanma olasılığını düşürür**. Sistem öndeyken istikrarlı ve düşük varyanslı oyuncuları tercih eder.

### 4.3. Eşik Korelasyon Düzeltmesi ($\rho \in [0.10, 0.20]$) ve Sıralama Değişmezliği
NBA sayma kategorileri takım temposu ve fikstür yoğunluğu nedeniyle ortak bir korelasyona ($\rho$) sahiptir:
$$\text{Cov}(X_i, X_j) = \rho \, \sigma_i \, \sigma_j$$
14 takım üzerinde yürüttüğümüz ampirik testler, $\rho \in [0.00, 0.20]$ aralığında kazanma oranlarının %50 merkezine doğru dengelendiğini, ancak takımların lig sıralamasındaki yerinin **%100 Değişmez (Rank Invariant)** kaldığını kanıtlamıştır:

$$\text{Sıra}(\text{Takım}_i \mid \rho = 0.00) \equiv \text{Sıra}(\text{Takım}_i \mid \rho = 0.10) \equiv \text{Sıra}(\text{Takım}_i \mid \rho = 0.20)$$

---

## 5. Sezon İçi Sakatlık, Kadro ve Transfer Motoru

### 5.1. Resmi NBA Sakatlık Raporu Ayrıştırıcısı v2 (`src/nba_injury_scraper.py`)
- **Doğrudan PDF Metin Akışı Ayrıştırması:** NBA CMS hakem portalından her 15 dakikada bir yayımlanan resmi PDF'leri çözer.
- **7 Sütunlu Durum Makinesi:**
  - Sütunlar: `Game Date`, `Game Time`, `Matchup`, `Team`, `Player Name`, `Current Status`, `Reason`.
  - Alt satıra devreden maç/tarih hücrelerini miras alır.
  - Birkaç satıra yayılan sakatlık gerekçelerini birleştirir.
  - Ters isimleri düzeltir (`"Vučević, Nikola"` $\to$ `"Nikola Vučević"`).
  - Sakatlık dışı satırları eler (`"G League - Two-Way"`, `"NOT YET SUBMITTED"`).
- **Veri Sağlığı ve Karantina:** Rapor tamamlanma oranını denetler; ayrıştırılamayan satır oranı %5'i aşarsa veriyi karantinaya alarak veri tabanı bütünlüğünü korur.

### 5.2. SQLite Kalıcı Sakatlık Takip Sistemi (`src/injury_tracker.py`)
- **Veri Tabanı Şeması:**
  ```sql
  CREATE TABLE injuries (
      player_id INTEGER,
      player_name TEXT PRIMARY KEY,
      team TEXT,
      status TEXT,
      reason TEXT,
      report_date TEXT,
      report_time TEXT,
      cleared_at TEXT,
      updated_at TIMESTAMP
  );
  CREATE TABLE injury_history (...);
  CREATE TABLE quarantine_log (...);
  ```
- **Otomatik İyileşme (Clearance) Algoritması:**
  1. $\mathcal{I}_{\text{aktif}}$: Veri tabanında sakat olarak işaretli oyuncular.
  2. $\mathcal{I}_{\text{rapor}}$: Yeni çekilen resmi NBA raporunda sakat olarak listelenen oyuncular.
  3. Takımı raporda yer aldığı halde rapordan çıkan her $p \in \mathcal{I}_{\text{aktif}} \setminus \mathcal{I}_{\text{rapor}}$ oyuncusu için:
     - Durum `AVAILABLE` yapılır.
     - `cleared_at = CURRENT_TIMESTAMP` atanır.
     - Değişim `injury_history` tablosuna arşivlenir.
     - Oyuncu aktif sakatlık listesinden çıkarılarak tam kapasite kadroya geri döner.

### 5.3. Yahoo 2x IL+ Yuvası ve Macar Algoritması Dizilimi (`src/matchup_engine.py`)
- **Optimal Kadro Çözücüsü:** Günlük 10 aktif slot (`PG, SG, G, SF, PF, F, C, C, UTIL, UTIL`), oyuncuların o günkü kategori kaldıraçlarına ($\phi(z_c)$) göre **Macar Algoritması (Linear Sum Assignment)** ile $\mathcal{O}(V^3)$ sürede çözülür.
- **IL+ Sakat Yuvasına Kaydırma:** Resmi olarak OUT olan oyuncular için:
  $$\text{IL+\_kaydırılan} = \min(|\{p \in \mathcal{R} \mid p.\text{durum} = \text{'OUT'}\}|, 2)$$
- **Yedek Terfi Matematiği (Bench Promotion):**
  İlk 10'daki bir oyuncu IL+'a alındığında, yedekteki en iyi oyuncu ilk 10'a yükselir:
  $$\mathbb{E}[\text{İstatistik}_{\text{aktif}}] = \sum_{i \in \text{İlk10} \setminus \{\text{Sakat}\}} \mu_i + \mu_{\text{Yedek Terfisi}}$$
  Bu sayede hiçbir kadro boşluğu oluşmaz; haftalık maç sayısı ve toplam sayma istatistikleri matematiksel olarak maksimize edilir.

### 5.4. Sağlık Filtreli Serbest Oyuncu Transferi (Waiver Streaming)
H2H formatında haftalık maksimum 3 transfer hakkı tanınır. Bu hakların heba olmasını önlemek için:
1. Serbest oyuncu havuzundaki adaylar anlık olarak `injuries.db` ile çapraz denetlenir.
2. Aşil tendonu kopması, omuz ameliyatı gibi uzun vadeli veya ağır sakatlığı olan oyuncular karantinaya alınır.
3. Sağlıklı adayların takıma katacağı marjinal kazanma olasılığı farkı hesaplanır: $\Delta \mathcal{V} = \mathcal{V}(\mathcal{R} \cup \{p_{\text{al}}\} \setminus \{p_{\text{bırak}}\}) - \mathcal{V}(\mathcal{R})$.

### 5.5. Canlı Sağlık Durumu Eşlemesi ve Bayesçi Koşullandırma
Haftalık simülasyonlarda oyuncunun yaklaşan maça çıkma olasılığı, oyuncunun geçmiş sezonluk dayanıklılık önseli ile canlı NBA sakatlık raporundaki güncel durumunu birleştirir:
- **Temel Sağlıklı Önsel Harmanlama (Baseline Prior Blending):**
  $$\text{eff\_avail} = \text{clip}(w \cdot \text{anchor} + (1 - w) \cdot \text{availability\_rate}, 0.35, 0.96)$$
  Burada varsayılan değerler parametre duyarlılık ızgarasında doğrulanmış $w = 0.35$ ve $\text{anchor} = 0.92$'dir.
- **Resmi NBA Rapor Statü Çarpanları:**
  Bir oyuncu resmi NBA sakatlık raporunda listelendiğinde maç katılım olasılığı $P(\text{Aktif})$ dinamik olarak eşlenir:
  | Resmi Statü | Koşullu Katılım Olasılığı $P(\text{Aktif})$ | Eşleşme Motoru (Matchup Engine) Aksiyonu |
  |---|:---:|---|
  | `OUT` / `SUSPENDED` | **0.00** | 2x IL+ Yuvasına kaydırma adayı; Yedek Terfisini tetikler |
  | `DOUBTFUL` | **0.25** | Yüksek risk; yedek kulübesi önceliği |
  | `QUESTIONABLE` / `GTD` | **0.50** | %50 süre maruziyetiyle (dakika) ağırlıklandırma |
  | `PROBABLE` | **0.75** | Sahaya çıkma ihtimali yüksek; ilk 10 başlatma |
  | `AVAILABLE` | **1.00** | Tam kapasite maç projeksiyonu |

---

## 6. Otonom Bulut Mimarisi ve CI/CD Boru Hatları

```
                                  [Cron Tetikleyicileri]
                       ┌─────────────────────┼─────────────────────┐
                       ▼                     ▼                     ▼
                   07:30 UTC             18:30 UTC             22:15 UTC
                   (10:30 TR)            (21:30 TR)            (01:15 TR)
                       │                     │                     │
                       └─────────────────────┼─────────────────────┘
                                             ▼
                            [GitHub Actions Ubuntu Runner]
                                             │
                                             ▼
                                    [src/cloud_sync.py]
                        1. Resmi NBA PDF Raporunu Çek
                        2. SQLite injuries.db Veri Tabanını Güncelle
                        3. 14 Kadroyu ve IL+ Yuvalarını Denetle
                        4. Serbest Oyuncuları Filtrele ve Eşleşmeleri Simüle Et
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
             [Git Commit & Push]                         [Telegram Bot API]
         Dal: 'nba-fantasy-bot'                      Telefona Doğrudan Anlık Bildirim
       ('main' dalı tertemiz kalır)                  (HTML Formatlı Kadro ve IL+ Özeti)
```

### 6.1. Stratejik Çalışma Saatleri
- **1. Çalışma: 10:30 TR / 07:30 UTC / 03:30 ET:** Gece maçlarının tamamlanması ve Yahoo serbest oyuncu (waiver) iddialarının sabaha karşı sonuçlanması.
- **2. Çalışma: 21:30 TR / 18:30 UTC / 14:30 ET:** NBA resmi öğleden sonra sakatlık raporunun yayımlanması ve gün ortası kadro hamleleri.
- **3. Çalışma: 01:15 TR / 22:15 UTC / 18:15 ET:** İlk maçların başlamasına 45 dakika kala kadro kilitlenmesi (son dakika GTD/OUT değişikliklerinin yakalanması).

### 6.2. Yalıtılmış Bot Dalı (`nba-fantasy-bot`)
Bulut üzerindeki tüm otomatik güncellemeler (veri tabanı, lig durumları, analiz özetleri) yalnızca `nba-fantasy-bot` dalına yazılır. `main` dalı tamamen insan yazımı ve temiz kalır.

### 6.3. Anlık Mobil Bildirimler
Telegram Bot API üzerinden iletilen zengin HTML mesajları:
- Kadrodaki oyuncuların sakatlık durum değişimlerini (örn. Kawhi Leonard, Brandon Ingram).
- Yapılması gereken IL+ kaydırma hamlelerini.
- Haftalık fikstüre göre önerilen en iyi 3 sağlıklı serbest oyuncu alternatifini doğrudan cep telefonunuza iletir.

---

## 7. Test, Doğrulama ve Akran İncelemesi

Tüm sistem, Python `unittest` ile çalışan kapsamlı bir test süiti ile doğrulanmıştır:

```text
Ran 33 tests in 7.258s
OK (skipped=2)
```

### Doğrulanan Modüller
1. **`tests/test_injury_system.py` (22 Birim Testi):**
   - PDF metin ayıklama, regex tokenizasyonu, 7 sütunlu sayfa birleştirme.
   - SQLite tablo oluşturma, ekleme, güncelleme ve zaman damgası doğrulaması.
   - Otomatik iyileşme tespiti: Rapordan çıkan oyuncuların `AVAILABLE` yapılması.
   - Bozuk raporlarda karantina tetiklenmesi.
2. **`tests/test_ab_validation.py` (11 Birim Testi):**
   - **Karşı-Olgusal Senaryolar:** C1 (Tam Sağlıklı), C2 (Tarihsel Önsel), C3 (Canlı Sakatlık + IL+ + Waiver Streaming).
   - **Cebirsel Yedek Terfi Kimliği:** Yedek oyuncu terfisi matematiğinin teorik beklentiyle birebir uyuştuğunun kanıtı.
   - **Draft Kadro Bütünlüğü:** `draft_data.py` içindeki tüm 14 takımın ve 182 seçimin eksiksiz ve hatasız eşleştiğinin doğrulanması.
   - **14 Takımlı Simetri ve Sıralama Değişmezliği:** $\rho \in [0.00, 0.20]$ parametresinde sıralamanın bozulmadığının doğrulanması.

Ayrıntılı akran denetimi raporu, duyarlılık ızgaraları ve ampirik kovaryans matrisleri için [docs/injury_system_architecture_and_peer_review.md](injury_system_architecture_and_peer_review.md) belgesini inceleyebilirsiniz.

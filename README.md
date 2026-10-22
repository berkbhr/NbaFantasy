# 🏀 NBA Fantasy Probabilistic Decision & Simulation Suite (H2H 9-Category)

A production-grade quantitative modeling, autonomous simulation, and live in-season decision engine for NBA Fantasy Head-to-Head (H2H) 9-Category leagues, powered by **Conjugate Bayesian Inference**, **Analytical Decision Theory**, and **Autonomous Cloud CI/CD Pipelines**.

> 🇹🇷 *Dökümantasyonun Türkçe versiyonu için [docs/README_TR.md](docs/README_TR.md) sayfasına bakabilirsiniz.*

---

## 🌟 Key Highlights & System Capabilities

### 1. Conjugate Bayesian Inference & Dynamic In-Season Learning
- **Counting Categories (PTS, REB, AST, STL, BLK, 3PM, TOV):** Modeled with **Gamma-Poisson / Negative Binomial** predictive distributions parameterized by actual playing time exposure ($m$ minutes) rather than static per-game averages.
- **Shooting Percentages (FG%, FT%):** Discrete trial modeling using **Beta-Binomial** conjugate pairs, evaluated as **Net Volume Impact** ($Y = \text{Makes} - p_{\text{ref}} \cdot \text{Attempts}$) relative to league benchmarks.
- **Dynamic In-Season Updating (`BayesianPlayer.update_stats`):** As regular season games are played, new box scores update rate posteriors dynamically. A hot streak or slump shifts expectations smoothly without manual overrides.
- **Discounted Conjugate Filtering (Dynamic Memory):**
  - **Exponential Decay:** Historical box scores decay over time ($\delta = e^{-\lambda \Delta t}$).
  - **Role Expansion & Trade Reset:** Mid-season trades reduce prior confidence fivefold ($\delta_{\text{event}} = 0.2$), adapting within 3–5 games to new team roles.

### 2. Analytical Decision Function (Gaussian CDF $\sum \Phi$)
Replaces arbitrary Z-scores and rigid manual punting heuristics with an exact closed-form Gaussian Cumulative Distribution Function:
$$\mathcal{V}(\text{Roster}) = \sum_{c=1}^{9} \mathbb{P}(\text{Win}_c) = \sum_{c=1}^{9} \Phi\!\left(\frac{\mu_{\text{team}, c} - \mu_{\text{opp}, c}}{\sqrt{\sigma^2_{\text{team}, c} + \sigma^2_{\text{opp}, c}}}\right)$$
- **Natural Saturation:** Diminishing returns in dominant categories ($Z \ge +2$, where $\phi(Z) \to 0$).
- **Natural Punting:** Rational concession of unwinnable categories ($Z \le -2$) to optimize swing categories ($Z \approx 0$).
- **Variance Optimization:** Pursues high-upside volatility when trailing and consistent floors when protecting a lead.
- **Equicorrelation Adjustment ($\rho \in [0.10, 0.20]$):** Compensates for shared schedule and pace variance across counting metrics, maintaining 100% league rank invariance.

### 3. Official NBA Injury Scraper v2 (PDF Ingestion)
- **Zero-Credential Direct Ingestion:** Parses official NBA injury PDF reports directly from the NBA CDN (`https://ak-static.cms.nba.com/referee/injury/...`) published every 15 minutes.
- **7-Column Layout Engine:** Pure-Python text extraction using `pdfplumber` / `pypdf`. Handles multi-line reason wrapping, inherited game date/matchup cells, and inverted names (`"Porter Jr., Kevin"` $\to$ `"Kevin Porter Jr."`).
- **Data Integrity & Quarantine:** Automated health checks verify row completion and player ID resolution rates. Malformed rows are quarantined without aborting execution.

### 4. SQLite State Tracking & Automated Clearance
- **Relational Persistence (`data/processed/injuries.db`):** Tracks player injury status, injury location, return timeline, and timestamp logs in `injuries` and `injury_history` tables.
- **Automated Clearance Detection:** When an injured player disappears from subsequent official NBA injury reports, the engine automatically records their clearance, marks status as `AVAILABLE`, and restores them to active lineup calculations.

### 5. Matchup Engine with IL+ Stashing & Health-Filtered Streaming
- **Yahoo 2x IL+ (Injured Reserve) Optimization:** When players are ruled OUT, the engine stashes up to 2 players into IL+ slots.
- **Bench Promotion Math:** When a starter is stashed to IL+, the top bench player is promoted to active slots, mathematically boosting weekly games played and counting statistics without roster penalty.
- **Health-Filtered Waiver Wire Streaming:** Actively filters candidate free agents against the live injury database. Quarantines injured candidates (e.g., Achilles tears, shoulder surgery) to prevent wasting weekly transaction limits (max 3/week).

### 6. Autonomous Cloud Sync & Dedicated Bot Branch
- **GitHub Actions Scheduled Pipeline (`.github/workflows/daily_fantasy_sync.yml`):** Runs 3x daily synchronized to NBA real-world workflows:
  - `10:30 TR / 07:30 UTC / 03:30 ET`: Overnight scores & Yahoo waiver add/drop resolution.
  - `21:30 TR / 18:30 UTC / 14:30 ET`: NBA afternoon official injury report release.
  - `01:15 TR / 22:15 UTC / 18:15 ET`: Pre-game lock 45 minutes prior to tip-offs (catches last-minute GTD/OUT).
- **Dedicated `nba-fantasy-bot` Branch:** All automated cloud commits (database state, league state, markdown reports) are committed solely to `nba-fantasy-bot`. The `main` branch remains 100% clean and human-authored.
- **Instant Mobile Push Notifications:** Pushes rich HTML matchup summaries, roster health alerts, IL+ movements, and waiver streaming recommendations directly to your phone via Telegram Bot API.

### 7. Canonical 14-Team 182-Pick Draft Database (`src/draft_data.py`)
- Official source-of-truth for all 14 teams and 182 picks from the live snake draft.
- Real-time roster resolution and dynamic transaction support (adds, drops, trades).

---

## 📁 Repository Structure

```text
NbaFantasy/
├── .github/
│   └── workflows/
│       └── daily_fantasy_sync.yml     # 3x daily automated GitHub Actions cloud sync workflow
├── config/
│   ├── yahoo_oauth.template.json     # Yahoo OAuth2 configuration template
│   └── yahoo_oauth.json              # Local OAuth credentials (git-ignored)
├── data/
│   ├── processed/
│   │   ├── active_roster_2026_27.parquet    # Roster & player credentials
│   │   ├── injuries.db                      # SQLite injury tracker & clearance database
│   │   ├── player_positions.parquet         # Multi-position Yahoo eligibility mapping
│   │   ├── schedule_2026_27.parquet         # Official regular season schedule
│   │   └── Master_Database_*.xlsx           # Historical player performance databases
│   ├── raw/                                 # Raw box scores & logs (Parquet)
│   │   └── injuries/                        # Directory for downloaded injury PDFs (.gitkeep)
│   └── simulations/                         # Monte Carlo simulation results
├── docs/
│   ├── README_TR.md                         # Detailed Turkish user documentation
│   ├── SYSTEM_ARCHITECTURE_TR.md            # Detailed Turkish system architecture blueprint
│   └── injury_system_architecture_and_peer_review.md # Complete peer review & validation report
├── reports/
│   ├── league_draft_overview_and_projections.md    # 14-Team draft & projection report (EN)
│   └── league_draft_overview_and_projections.tr.md # 14-Team draft & projection report (TR)
├── src/
│   ├── auth_yahoo.py                # Yahoo OAuth2 authorization helper & token manager
│   ├── bayesian_model.py            # Gamma-Poisson, Beta-Binomial & in-season updater
│   ├── cloud_sync.py                # Autonomous cloud pipeline runner & Telegram dispatcher
│   ├── data_fetcher.py              # NBA API data ingest for rosters, schedules & logs
│   ├── draft_data.py                # Canonical 182-pick 14-team draft rosters & picks
│   ├── injury_tracker.py            # SQLite injury persistence, clearance & state management
│   ├── live_draft_assistant.py      # Live draft assistant with lookahead rollouts
│   ├── matchup_engine.py            # H2H Gaussian CDF, IL+ stashing, bench math, waiver filter
│   ├── model_ai.py                  # AI waiver moves & Bayesian core-protected decision logic
│   ├── nba_injury_scraper.py        # Official 7-column NBA injury report PDF parser v2
│   ├── simulate_slot8_scenarios.py  # Slot 8 Monte Carlo scenario evaluator
│   ├── simulator.py                 # Prior season baseline loaders & utilities
│   ├── verify_yahoo_names.py        # Player name normalization & verification test
│   ├── yahoo_draft_bridge.user.js   # Tampermonkey script for live Yahoo draft room sync
│   └── yahoo_draft_sync.py          # WebSocket/HTTP synchronization bridge daemon
├── tests/
│   ├── test_ab_validation.py        # A/B validation, roster integrity, bench math, 14-team symmetry
│   └── test_injury_system.py        # 22 unit tests for scraper, SQLite CRUD, clearance, quarantine
├── league_simulator.py              # Full 14-team multi-season H2H league simulation engine
├── requirements.txt                 # Project dependencies
├── README.md                        # Master project documentation (English)
├── SYSTEM_ARCHITECTURE.md           # Master mathematical & technical specification (English)
└── .gitignore                       # Clean repo rules (ignores PDFs, credentials, logs)
```

---

## 🚀 Getting Started

### 1. Clone & Set Up Python Environment
```bash
git clone https://github.com/berkbhr/NbaFantasy.git
cd NbaFantasy

python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Verify System with Unit Tests
Run the complete unit test suite (33 tests verifying scrapers, database transactions, roster integrity, Hungarian lineup math, and counterfactuals):
```bash
python -m unittest discover tests
```

### 3. Run Autonomous Cloud Sync Locally
Test the cloud sync pipeline locally to ingest the latest official NBA injury report, update `injuries.db`, run MatchupEngine simulations, and print summary analytics:
```bash
python src/cloud_sync.py
```

---

## ☁️ Setting Up Cloud Automation (GitHub Actions + Telegram)

The system is designed to run autonomously in the cloud 3 times a day without requiring your computer to remain powered on.

### 1. Configure GitHub Repository Secrets
Navigate to **GitHub Repository** $\to$ **Settings** $\to$ **Secrets and variables** $\to$ **Actions** and add the following repository secrets:

| Secret Name | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Recommended | Token from `@BotFather` to receive instant push alerts. |
| `TELEGRAM_CHAT_ID` | Recommended | Your personal Telegram chat ID from `@userinfobot`. |
| `YAHOO_COOKIE` | Optional | Session cookie fallback for private league data if API is pending. |

### 2. Autonomous Branch Isolation (`nba-fantasy-bot`)
- The GitHub Actions workflow (`daily_fantasy_sync.yml`) runs on an isolated Ubuntu runner.
- Every sync run pushes updated database records (`injuries.db`), simulation outputs, and markdown summaries strictly to the `nba-fantasy-bot` branch.
- Your `main` branch remains clean and untouched by automated bot commits.

---

## 📐 Mathematical Decision Framework

### Expected Weekly Category Outcome
For two competing rosters over a given week, the expected number of winning categories is:
$$\mathcal{V}(\text{Roster}) = \sum_{c=1}^{9} \mathbb{P}(\text{Win}_c) = \sum_{c=1}^{9} \Phi\!\left(\frac{\mu_{\text{team}, c} - \mu_{\text{opp}, c}}{\sqrt{\sigma^2_{\text{team}, c} + \sigma^2_{\text{opp}, c}}}\right)$$

### Benchmark League Correlation Structure
Real-world NBA counting stats share game-volume and pace correlation ($\rho \in [0.10, 0.20]$). Our empirical covariance analysis confirms that incorporating $\rho$ suppresses win probabilities gracefully toward 50% without altering relative team power rankings (100% Rank Invariance).

| Rank | Slot | Team Name | $\rho = 0.00$ Win% | $\rho = 0.10$ Win% | $\rho = 0.20$ Win% | ExpCat / 9 |
|---|---|---|---|---|---|---|
| **#1** | **S8** | **Berk's Best Team** | **78.6%** | **72.5%** | **69.2%** | **5.63** |
| #2 | S4 | Houston Buckets | 59.9% | 57.5% | 56.3% | 4.87 |
| #3 | S2 | Mordor Tulums | 59.6% | 57.3% | 56.2% | 4.83 |
| #4 | S7 | Samurai Strikers | 57.0% | 55.3% | 54.4% | 4.75 |
| #5 | S13 | SILE BULLS | 55.5% | 54.1% | 53.4% | 4.70 |

For full mathematical derivations, Dirichlet/Gamma conjugate equations, and bench replacement theorems, see [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md).

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

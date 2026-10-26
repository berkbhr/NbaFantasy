# 🏀 NBA Fantasy Probabilistic Decision & Simulation Suite (H2H 9-Category)

A production-grade quantitative modeling, autonomous simulation, and live in-season decision engine for NBA Fantasy Head-to-Head (H2H) 9-Category leagues, powered by **Conjugate Bayesian Inference**, **Analytical Decision Theory**, **Quality-Elastic Teammate Injury Redistribution**, and **Autonomous Cloud CI/CD Pipelines**.

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

### 3. Quality-Elastic Teammate Injury Redistribution & Positional Spillover
- **Positional Depth Charts ($k = 1, 2, 3, \dots$):** Groups all 30 NBA teams by primary positional buckets (`G`, `F`, `C`) ranked by talent score and base expected minutes.
- **Quality-Elastic Cross-Positional Spillover:** When a starter is ruled OUT (e.g., Center Maxime Raynaud OUT) and the immediate same-position backup has low talent ($S_{\text{same}}$ is low), a quality gap $\Delta S = \max(0, S_{\text{adj}} - S_{\text{same}})$ triggers cross-positional minute absorption to adjacent high-quality wings/forwards (e.g., Forward Precious Achiuwa absorbs $+2.0$ to $+4.0$ minutes via small-ball lineups).
- **Role-Dependent Minute Ceilings:** Automatically caps expanded minutes at realistic thresholds (starters up to 35.5 mins, rotation players up to 31.0 mins) and inflates variance ($+0.35 \cdot \Delta M^2$) to reflect expanded role uncertainty.
- **Strict Mathematical Reversibility:** When injured players recover, minutes and distributions return bit-for-bit to their baseline:
  $$M_{\text{base}} < M_{\text{one\_out}} < M_{\text{both\_out}} \quad \text{and} \quad M_{\text{recovered}} \equiv M_{\text{base}}$$

### 4. Dual Injury Engine: Official NBA Referee PDFs + 30-Team ESPN API
- **Official NBA Referee Report Scraper v2:** Zero-credential parsing of official NBA injury report PDFs published every 15 minutes on the NBA CDN (`https://ak-static.cms.nba.com/referee/injury/...`). Pure-Python 7-column layout parser with health checks and quarantine.
- **30-Team ESPN / Rotowire Live Feed (`sync_espn_injuries`):** Public, zero-credential REST API feed capturing multi-week, long-term, and off-day injuries that game-day referee reports omit.
- **Automated Clearance & Recovery Reconciliation (`reconcile_recovered=True`):** When an injured player disappears from subsequent feeds, the engine automatically clears their record in `injuries.db`, writes a `CLEARED` snapshot audit trail, and restores them to active lineup calculations.

### 5. 1-Click Yahoo Browser Sync Bridge (`src/yahoo_browser_sync.py`)
- **Zero-Cookie / Zero-Credential Instant Sync:** Runs a lightweight local bridge on `http://127.0.0.1:8765`.
- **1-Click Bookmarklet:** Clicking the `🏀 NBA Fantasy Sync` bookmarklet on your active Yahoo Fantasy browser tab performs a same-origin parallel scan in ~2 seconds:
  1. **All 14 Team Live Rosters & Slot Assignments:** Reads `/nba/64691/1` through `/14`, identifying active slots (`PG`..`UTIL`, `BN`), `IL`/`IL+` placements, and unslotted injured players.
  2. **Live Transactions Log:** Captures all recent adds, drops, waivers, and trades from `/nba/64691/transactions`.
  3. **Live Matchup Scoreboard & Remaining Games:** Ingests live box score totals for all 11 categories (`FGM`, `FGA`, `FTM`, `FTA`, `FG3M`, `PTS`, `REB`, `AST`, `STL`, `BLK`, `TOV`) and remaining game counts from `/nba/64691/matchup`.
  4. **True Free Agent Pool Reconstruction:** Automatically reconstructs the exact free agent pool:
     $$\text{True Free Agents} = \text{All Players} \setminus \bigcup_{t=1}^{14} \text{Roster}_t$$

### 6. Conditioned Projections & Dynamic Add/Drop Optimizer
- **Live Scoreboard Conditioning (`combine_live_and_remaining_dist`):** Conditions weekly predictive distributions on realized stats $X_{\text{actual}}$ and remaining fraction $f_{\text{rem}}$:
  $$\mu_{\text{final}} = X_{\text{actual}} + f_{\text{rem}} \cdot \mu_{\text{rem}}, \qquad \sigma^2_{\text{final}} = f_{\text{rem}} \cdot \sigma^2_{\text{rem}}$$
- **Marginal Expected Wins Maximization ($\Delta \sum_{c=1}^9 \Phi_c$):** Ranks candidate free agent pickups by their direct impact on weekly matchup win probability rather than generic per-game averages.
- **Automatic IL+ Slot Detection:** When an injured player is stashed to IL+, detects open roster spots (`has_open_slot = True`) and suggests `ADD (Boş Yuva / IL+)` without dropping any active player.
- **Core-Protected Swaps:** When the roster is full, evaluates counterfactual bench drop/add swaps while strictly shielding core stars from being dropped.

### 7. Multi-Channel Rich Notifications (Telegram + Discord)
- Pushes executive matchup intelligence cards directly to your mobile device via Telegram Bot API (HTML) and Discord Webhook (Markdown):
  - **Live Matchup Score & Win Probability:** e.g., `Berk's Best Team: 4.70 - 4.30 vs SILE BULLS (%52 Win)`.
  - **Category Breakdown:** Strong categories, critical swing toss-ups, and opponent-favored metrics.
  - **Health & IL+ Alerts:** Highlights `OUT` players needing immediate IL+ stashing and `GTD` game-time risks.
  - **Top Add/Drop Recommendations:** Ranked by $\Delta E[\text{Wins}]$ and remaining games schedule.
  - **Comparative Matchup Table:** Side-by-side ASCII box score comparing live performance against projected final outcomes.
  - **Recent League Transactions:** Add/drop and waiver audit trail across all 14 managers.

### 8. Autonomous Cloud CI/CD Pipeline (`.github/workflows/daily_fantasy_sync.yml`)
- Runs 3x daily in GitHub Actions aligned with NBA operational milestones:
  - `10:30 TR / 07:30 UTC / 03:30 ET`: Overnight game wrap, scoreboard update & waiver resolution.
  - `21:30 TR / 18:30 UTC / 14:30 ET`: NBA official afternoon injury report release & depth boosts.
  - `01:15 TR / 22:15 UTC / 18:15 ET`: Pre-game lock 45 minutes prior to tip-offs (catches last-minute GTD/OUT).
- **Dedicated `nba-fantasy-bot` Branch:** Automated cloud commits push updated database states and summary reports exclusively to `nba-fantasy-bot` (`[skip ci]`), keeping `main` 100% clean.

---

## 📁 Repository Structure

```text
NbaFantasy/
├── .github/
│   └── workflows/
│       └── daily_fantasy_sync.yml     # 3x daily autonomous GitHub Actions pipeline
├── config/
│   ├── telegram.template.json        # Telegram / Discord notification template
│   ├── telegram.json                 # Local bot credentials (git-ignored)
│   ├── yahoo_oauth.template.json     # Yahoo OAuth2 configuration template
│   └── yahoo_oauth.json              # Local OAuth credentials (git-ignored)
├── data/
│   ├── processed/
│   │   ├── active_roster_2026_27.parquet    # Roster & player metadata
│   │   ├── injuries.db                      # SQLite injury tracker & clearance database
│   │   ├── league_state.json                # Live 14-team rosters & IL assignments (JSON)
│   │   ├── live_matchup.json                # Live scoreboard & remaining games (JSON)
│   │   ├── player_positions.parquet         # Multi-position Yahoo eligibility mapping
│   │   └── schedule_2026_27.parquet         # Official regular season schedule
│   └── raw/                                 # Raw box scores & logs (Parquet)
│       └── injuries/                        # Directory for downloaded injury PDFs (.gitkeep)
├── docs/
│   ├── README_TR.md                         # Comprehensive Turkish user guide
│   ├── SYSTEM_ARCHITECTURE_TR.md            # Comprehensive Turkish technical blueprint
│   └── injury_system_architecture_and_peer_review.md # Peer review & validation report
├── reports/
│   ├── latest_cloud_summary.md              # Executive sync summary & matchup projections
│   ├── league_draft_overview_and_projections.md    # 14-Team draft overview (EN)
│   └── league_draft_overview_and_projections.tr.md # 14-Team draft overview (TR)
├── src/
│   ├── auth_yahoo.py                # Yahoo OAuth2 authorization & automatic league discovery
│   ├── bayesian_model.py            # Gamma-Poisson, Beta-Binomial, in-season updates & depth boosts
│   ├── cloud_sync.py                # Autonomous cloud pipeline runner & notification dispatcher
│   ├── data_fetcher.py              # NBA API data ingest for rosters, schedules & logs
│   ├── draft_data.py                # Canonical 182-pick 14-team draft rosters & picks
│   ├── injury_tracker.py            # SQLite injury persistence, ESPN sync, clearance & audit
│   ├── live_draft_assistant.py      # Live assistant with injury syncing & depth adjustments
│   ├── matchup_engine.py            # Gaussian CDF, quality-elastic spillover, live scoreboard math
│   ├── model_ai.py                  # Core-protected Bayesian decision logic
│   ├── nba_injury_scraper.py        # Official 7-column NBA injury report PDF parser v2
│   ├── simulator.py                 # Prior season baseline loaders & utilities
│   ├── yahoo_browser_sync.py        # 1-Click bookmarklet local bridge for live Yahoo sync
│   └── yahoo_draft_sync.py          # Yahoo OAuth2 REST API client & draft room bridge
├── tests/
│   ├── test_ab_validation.py        # 29 tests: A/B validation, bench math, 14-team symmetry
│   ├── test_injury_system.py        # 4 tests: Scraper, SQLite CRUD, clearance, B2B rest
│   ├── test_notifications_and_workflow.py # 3 tests: Workflow syntax, cron schedules, notification parsers
│   └── test_reversible_and_spillover.py   # 3 tests: Reversible recovery, ESPN reconciliation, cross-position spillover
├── requirements.txt                 # Project dependencies
├── README.md                        # Master project documentation (English)
├── SYSTEM_ARCHITECTURE.md           # Master mathematical & technical specification (English)
└── .gitignore                       # Clean repo rules (ignores databases, credentials, reports)
```

---

## 🚀 Getting Started

### 1. Set Up Python Environment
Clone the repository and configure the virtual environment:
```powershell
git clone https://github.com/berkbhr/NbaFantasy.git
cd NbaFantasy

python -m venv .venv

# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

> **Windows PowerShell Tip:** Always invoke Python via `.\.venv\Scripts\python.exe` (and pip via `.\.venv\Scripts\pip.exe`) to bypass the Windows Store alias. Set UTF-8 encoding for clean terminal output:
> ```powershell
> $env:PYTHONIOENCODING="utf-8"
> ```

### 2. Verify System with Unit Tests
Execute the complete test discovery suite across all modules:
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```
*(All 36 unit and integration tests should pass with 0 failures and 0 errors).*

---

## 🔄 Live In-Season Synchronization

### Method A: 1-Click Yahoo Browser Sync Bridge (Fastest, Zero Credentials)
The easiest way to synchronize live rosters, IL+ slots, and match scoreboards without setting up Yahoo API developer credentials:

1. **Start the local bridge server:**
   ```powershell
   .\.venv\Scripts\python.exe src/yahoo_browser_sync.py
   ```
2. Your browser will automatically open `http://127.0.0.1:8765/`.
3. Drag the green **`🏀 NBA Fantasy Sync`** button into your browser's **Bookmarks Bar** *(one-time setup)*.
4. Navigate to your **Yahoo Fantasy Matchup** page in your browser where you are logged in.
5. Click the **`🏀 NBA Fantasy Sync`** bookmarklet!
   - In ~2 seconds, it scans all 14 rosters, IL+ allocations, and box scores.
   - Saves `data/processed/league_state.json` and `live_matchup.json`.
   - Triggers the decision engine and dispatches mobile push notifications immediately.

### Method B: Yahoo OAuth2 REST API (Automated)
If you have registered a Yahoo Developer App:
1. Copy `config/yahoo_oauth.template.json` to `config/yahoo_oauth.json` and insert your `client_id` and `client_secret`.
2. Run the automatic authorization and league discovery script:
   ```powershell
   .\.venv\Scripts\python.exe src/auth_yahoo.py
   ```
   - Automatically exchanges your authorization code or refreshes existing tokens.
   - Discovers your `league_key` (e.g. `454.l.64691`) and `team_key` (e.g. `454.l.64691.t.8`).
   - Automatically saves all discovered parameters to `config/yahoo_oauth.json`.

### Method C: Run Full Cloud Sync Locally
To manually run the complete cloud sync workflow (injuries, depth adjustments, matchup math, notifications):
```powershell
.\.venv\Scripts\python.exe src/cloud_sync.py
```

---

## 📱 Configuring Push Notifications (Telegram & Discord)

The engine can push rich, formatted executive summaries directly to your phone or server.

1. Copy `config/telegram.template.json` to `config/telegram.json`:
   ```json
   {
     "bot_token": "YOUR_TELEGRAM_BOT_TOKEN_HERE",
     "chat_id": "YOUR_TELEGRAM_CHAT_ID_HERE",
     "discord_webhook_url": "YOUR_OPTIONAL_DISCORD_WEBHOOK_URL_HERE"
   }
   ```
2. **Telegram Setup:**
   - Create a bot via `@BotFather` to receive your `bot_token`.
   - Obtain your chat ID by messaging `@userinfobot` to get your `chat_id`.
3. **Discord Setup (Optional):**
   - Create a webhook in your Discord channel (`Server Settings -> Integrations -> Webhooks`) and paste the URL.

---

## ☁️ Setting Up GitHub Actions Cloud Automation

The repository includes a production-ready GitHub Actions workflow that executes 3x daily in the cloud without requiring your local computer to be on.

### 1. Configure GitHub Repository Secrets
Navigate to **GitHub Repository** $\to$ **Settings** $\to$ **Secrets and variables** $\to$ **Actions** and add the following repository secrets:

| Secret Name | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Recommended | Token from `@BotFather` for mobile notifications. |
| `TELEGRAM_CHAT_ID` | Recommended | Personal chat ID from `@userinfobot`. |
| `DISCORD_WEBHOOK_URL` | Optional | Discord webhook for server channel notifications. |
| `YAHOO_OAUTH_JSON` | Recommended | Complete JSON string from your local `config/yahoo_oauth.json`. |
| `YAHOO_CLIENT_ID` | Optional | Individual Yahoo Developer App Client ID. |
| `YAHOO_CLIENT_SECRET` | Optional | Individual Yahoo Developer App Client Secret. |
| `YAHOO_REFRESH_TOKEN` | Optional | Individual Yahoo OAuth2 Refresh Token. |

### 2. Autonomous Branch Isolation (`nba-fantasy-bot`)
- The GitHub Actions workflow (`daily_fantasy_sync.yml`) runs on an isolated Ubuntu runner.
- Every sync run commits updated database state (`injuries.db`), league rosters (`league_state.json`), and markdown reports (`reports/latest_cloud_summary.md`) strictly to the `nba-fantasy-bot` branch (`[skip ci]`).
- The `main` branch remains 100% clean and human-authored.
- Detailed executive reports are preserved as downloadable GitHub artifacts for 14 days.

---

## 📐 Mathematical Decision Framework

### Expected Weekly Category Outcome
For two competing rosters over a given week, the expected number of winning categories is:
$$\mathcal{V}(\text{Roster}) = \sum_{c=1}^{9} \mathbb{P}(\text{Win}_c) = \sum_{c=1}^{9} \Phi\!\left(\frac{\mu_{\text{team}, c} - \mu_{\text{opp}, c}}{\sqrt{\sigma^2_{\text{team}, c} + \sigma^2_{\text{opp}, c}}}\right)$$

### Benchmark League Correlation Structure
Real-world NBA counting stats share game-volume and pace correlation ($\rho \in [0.10, 0.20]$). Empirical covariance analysis confirms that incorporating $\rho$ suppresses win probabilities gracefully toward 50% without altering relative team power rankings (100% Rank Invariance).

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

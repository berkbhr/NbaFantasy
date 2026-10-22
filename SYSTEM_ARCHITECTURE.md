# 🏀 NBA Fantasy Decision & Simulation Engine - System Architecture

This document provides the formal mathematical, statistical, and software architectural specification for the NBA Fantasy Head-to-Head (H2H) 9-Category Decision and Simulation Suite, founded upon **Probabilistic Decision Theory**, **Conjugate Bayesian Inference**, and **Autonomous Cloud CI/CD Pipelines**.

---

## 1. Executive Summary & Foundational Tenet

Traditional fantasy basketball analytics suffer from three fundamental flaws:
1. **Linear Point Estimates:** Relying on static per-game averages ($\bar{x}$) that completely ignore game-to-game volatility, minutes elasticity, and matchup variance.
2. **Arbitrary Heuristic Rules:** Ad-hoc Z-scores, manual "punt" selections, and subjective saturation caps ($Z > 2.5$) that lack mathematical coherence.
3. **Static Stagnation:** Inability to adapt dynamically to daily official injury updates, mid-season role changes, and real-time waiver wire opportunities.

This platform replaces ad-hoc rules with a **Unified Analytical Objective Function** rooted in **Analytical Decision Theory**:

$$\max_{\mathcal{R}} \mathcal{V}(\mathcal{R}) = \sum_{c=1}^{9} \mathbb{P}(\text{Win}_c) = \sum_{c=1}^{9} \Phi\!\left(\frac{\mu_{\text{team}, c} - \mu_{\text{opp}, c}}{\sqrt{\sigma^2_{\text{team}, c} + \sigma^2_{\text{opp}, c}}}\right)$$

Every decision across the lifecycle—from pre-draft lookahead simulation, live draft pick valuation, and daily Hungarian roster assignment, to in-season Bayesian learning, official injury report PDF scraping, 2x IL+ stashing, and health-filtered waiver streaming—optimizes this exact objective.

---

## 2. Data Engineering & Storage Architecture

The data pipeline implements Medallion Architecture principles to guarantee reproducibility, auditability, and speed:

```
+-----------------------------------------------------------------------------+
|                           DATA PIPELINE ARCHITECTURE                        |
+-----------------------------------------------------------------------------+
|                                                                             |
|  [NBA API / CDN]          [Yahoo Fantasy API]        [Official NBA PDF]    |
|         │                         │                           │             |
|         ▼                         ▼                           ▼             |
|   data_fetcher.py         auth_yahoo.py / sync       nba_injury_scraper.py  |
|         │                         │                           │             |
|         ▼                         ▼                           ▼             |
|  [Raw Parquet]            [draft_data.py]            [injury_tracker.py]    |
|  - player_logs_*.parquet  - 182 Draft Picks          - injuries.db (SQLite) |
|  - team_logs_*.parquet    - 14 Team Rosters          - Auto-Clearance       |
|         │                         │                           │             |
|         └─────────────────────────┼───────────────────────────┘             |
|                                   │                                         |
|                                   ▼                                         |
|                       [bayesian_model.py]                                   |
|                       - Gamma-Poisson (Count)                               |
|                       - Beta-Binomial (Shooting %)                          |
|                       - In-Season Dynamic Game Updates                      |
|                                   │                                         |
|                                   ▼                                         |
|                       [matchup_engine.py]                                   |
|                       - Gaussian CDF (Sum Phi)                              |
|                       - Hungarian Assignment (10 Active + 3 BN)             |
|                       - 2x IL+ Stashing & Bench Promotion                   |
|                       - Health-Filtered Waiver Streaming                    |
|                                   │                                         |
|                                   ▼                                         |
|                       [Autonomous Cloud Sync]                               |
|                       - GitHub Actions (3x Daily)                           |
|                       - 'nba-fantasy-bot' Branch Isolation                  |
|                       - Telegram Bot Push Alerts                            |
|                                                                             |
+-----------------------------------------------------------------------------+
```

### Data Storage Specifications
1. **Raw Storage Layer (`data/raw/`):**
   - Game-by-game player and team logs stored in high-performance columnar Apache Parquet format (`player_logs_*.parquet`).
   - NBA Official Injury Report PDFs downloaded ephemerally to `data/raw/injuries/` (quarantined and excluded from version control via `.gitignore`).
2. **Processed Relational Layer (`data/processed/`):**
   - `injuries.db`: Relational SQLite database tracking active injuries, historical entries, clearance timestamps, and quarantine logs.
   - `active_roster_2026_27.parquet`: Active rosters, draft credentials, and preseason roles.
   - `player_positions.parquet`: Multi-position Yahoo Fantasy eligibility mappings (`PG, SG, G, SF, PF, F, C, UTIL, BN`).
   - `schedule_2026_27.parquet`: Complete 82-game regular season schedule with game IDs and week numbers.
3. **Simulation Artifacts (`data/simulations/`):**
   - Multi-season Monte Carlo results and scenario evaluations (`slot8_2026_27_scenarios_final.json`).

---

## 3. Conjugate Bayesian Inference & In-Season Learning

Player outputs are not treated as fixed constants; they are governed by **Predictive Probability Distributions**.

### 3.1. Counting Categories: Gamma-Poisson Conjugate Model
- **Categories:** Points (PTS), Rebounds (REB), Assists (AST), Steals (STL), Blocks (BLK), Three-Pointers Made (3PM), Turnovers (TOV).
- **Exposure Parameterization:** Output is modeled conditionally on playing time exposure ($m$ minutes) rather than static per-game counts.
- **Formulation:**
  - Per-minute rate $\lambda \sim \text{Gamma}(\alpha, \beta)$, where $\alpha$ represents accumulated virtual events and $\beta$ represents accumulated virtual minutes.
  - Observed count given minutes $m$: $X \mid \lambda, m \sim \text{Poisson}(\lambda \cdot m)$.
- **Conjugate Posterior Update:**
  Given a new game observation with stats $x_i$ and minutes $m_i$:
  $$\alpha_{t} = \delta \, \alpha_{t-1} + x_i, \quad \beta_{t} = \delta \, \beta_{t-1} + m_i$$
- **Predictive Distribution (Negative Binomial):**
  Marginalizing over $\lambda$ yields a Negative Binomial predictive distribution with expected value and predictive variance:
  $$\mathbb{E}[X \mid m] = m \cdot \frac{\alpha}{\beta}, \quad \text{Var}(X \mid m) = m \cdot \frac{\alpha}{\beta} \left(1 + \frac{m}{\beta}\right) = \mu + \frac{\mu^2}{\alpha}$$

### 3.2. Shooting Percentages: Beta-Binomial Conjugate Model
- **Categories:** Field Goal Percentage (FG%), Free Throw Percentage (FT%).
- **Formulation:**
  - Shooting accuracy $p \sim \text{Beta}(\alpha, \beta)$, where $\alpha = \text{Makes}$ and $\beta = \text{Misses}$.
  - Observed makes $K$ given attempts $N$: $K \mid p, N \sim \text{Binomial}(N, p)$.
- **Linear Net Volume Impact Transformation:**
  Ratios cannot be summed linearly across players. To evaluate shooting percentages in a unified additive framework, each player's contribution is transformed into **Net Volume Impact** relative to league reference benchmark $p_{\text{ref}}$ ($p_{\text{ref, FG}} \approx 0.470$, $p_{\text{ref, FT}} \approx 0.780$):
  $$Y = \text{Makes} - p_{\text{ref}} \cdot \text{Attempts} = \text{Attempts} \cdot (p - p_{\text{ref}})$$
  This naturally accounts for volume: a high-percentage player shooting 2 free throws per game produces far less impact than an 85% shooter on 10 attempts per game.

### 3.3. Discounted Conjugate Filtering (Dynamic Memory)
To balance long-term baseline talent against recent in-season form:
- **Soft Daily Decay:** Prior observations decay exponentially:
  $$\delta = e^{-\lambda \Delta t}, \quad \text{with } \lambda = \frac{\ln 2}{t_{1/2}}$$
- **Event-Driven Reset (Trades & Role Expansion):**
  When a player undergoes a major role transition (e.g., trade or starter promotion):
  $$\delta_{\text{event}} = 0.20$$
  The estimated rate parameter $\frac{\alpha}{\beta}$ is strictly preserved, while the effective sample size $\beta$ is deflated fivefold. Consequently, the player's initial 3–5 games with their new team dominate the posterior.

### 3.4. Dynamic In-Season Game-Log Updating (`BayesianPlayer.update_stats`)
Throughout the live season, each newly completed game log triggers `update_stats`:
1. Exponentially decays previous posterior parameters.
2. Incorporates observed stats and minutes.
3. Updates playing-time projection via Exponential Weighted Moving Average (EWMA):
   $$m_{\text{proj}, t} = \alpha_m \cdot m_{\text{game}} + (1 - \alpha_m) \cdot m_{\text{proj}, t-1}$$
4. Re-computes updated predictive means $\mu_c$ and variances $\sigma^2_c$ for all 9 categories instantly.

---

## 4. Analytical Decision Theory & H2H Gaussian CDF

### 4.1. The Unified Objective Function
Pairwise victory probability for category $c$ between roster $A$ and opponent $B$ over a weekly matchup is given by the Standard Normal Cumulative Distribution Function $\Phi$:

$$\mathbb{P}(\text{Win}_c) = \Phi\!\left(\frac{\mu_{A, c} - \mu_{B, c}}{\sqrt{\sigma^2_{A, c} + \sigma^2_{B, c}}}\right) = \Phi(z_c)$$

$$\mathcal{V}(\mathcal{R}) = \sum_{c=1}^{9} \Phi(z_c)$$

### 4.2. Three Emergent Strategic Behaviors
1. **Natural Saturation:**
   As $z_c \ge +2.0$ ($\mathbb{P} > 97.7\%$), the normal density $\phi(z) \to 0$. The marginal gain of drafting or streaming additional stats in that category approaches zero. The engine automatically stops wasting capital on surplus stats.
2. **Natural Punting:**
   As $z_c \le -2.0$ ($\mathbb{P} < 2.3\%$), the lower tail flattens ($\phi(z) \to 0$). The optimizer rationally concedes lost categories and channels streaming and lineup slots into close swing categories ($z_c \approx 0$), where marginal density $\phi(0) \approx 0.3989$ is maximal.
3. **Variance Optimization (Risk Preference):**
   Taking the derivative with respect to variance $\sigma^2$:
   $$\frac{\partial \Phi(z)}{\partial \sigma} = -\frac{\mu_A - \mu_B}{\sigma^2} \phi(z)$$
   - When trailing ($\mu_A < \mu_B$), $-\frac{\mu_A - \mu_B}{\sigma^2} > 0$: increasing variance **increases** win probability. The engine selects high-volatility players when underdogs.
   - When leading ($\mu_A > \mu_B$), increasing variance **decreases** win probability. The engine selects high-floor, reliable veterans when favorites.

### 4.3. Equicorrelation Adjustment ($\rho \in [0.10, 0.20]$) & Rank Invariance
NBA counting stats share common schedule and pace shocks. Under an equicorrelated Gaussian copula with correlation $\rho$:
$$\text{Cov}(X_i, X_j) = \rho \, \sigma_i \, \sigma_j$$
Our empirical tests across all 14 league teams verified that adjusting for $\rho \in [0.00, 0.20]$ compresses win percentages smoothly toward 50% while preserving **100% Rank Invariance**:

$$\text{Rank}(Team_i \mid \rho = 0.00) \equiv \text{Rank}(Team_i \mid \rho = 0.10) \equiv \text{Rank}(Team_i \mid \rho = 0.20)$$

---

## 5. In-Season Injury, Roster & Transaction Engine

### 5.1. Official NBA Injury Report Parser v2 (`src/nba_injury_scraper.py`)
- **Direct PDF Text Parsing:** Extracts structured text streams from official NBA CMS referee PDFs published every 15 minutes.
- **Line State Machine:**
  - Matches 7-column headers: `Game Date`, `Game Time`, `Matchup`, `Team`, `Player Name`, `Current Status`, `Reason`.
  - Handles inherited date, time, and matchup cells across subsequent rows.
  - Reconstructs multi-line wrapped injury descriptions.
  - Inverts reversed name tokens (`"Vučević, Nikola"` $\to$ `"Nikola Vučević"`).
  - Filters non-injury notations (`"G League - Two-Way"`, `"NOT YET SUBMITTED"`).
- **Health Checks & Quarantine:** Evaluates report completeness. If unparsed lines exceed 5% or player ID resolution falls below 85%, data is held in quarantine to prevent database corruption.

### 5.2. SQLite Persistent Injury Tracking (`src/injury_tracker.py`)
- **Database Schema:**
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
- **Automated Clearance Algorithm:**
  1. Let $\mathcal{I}_{\text{active}}$ be the set of players currently marked as injured in `injuries.db`.
  2. Let $\mathcal{I}_{\text{report}}$ be the set of players reported as injured in the latest official NBA report.
  3. For each player $p \in \mathcal{I}_{\text{active}} \setminus \mathcal{I}_{\text{report}}$ whose team participated in the report:
     - Mark status as `AVAILABLE`.
     - Record `cleared_at = CURRENT_TIMESTAMP`.
     - Archive transition to `injury_history`.
     - Remove $p$ from active injury exclusions.

### 5.3. Yahoo 2x IL+ Stashing & Hungarian Assignment (`src/matchup_engine.py`)
- **Optimal Lineup Solver:** Active 10 roster slots (`PG, SG, G, SF, PF, F, C, C, UTIL, UTIL`) are assigned via the **Hungarian Algorithm (Maximum Weight Bipartite Matching)** in $\mathcal{O}(V^3)$ time based on daily category leverage $\phi(z_c)$.
- **IL+ Stashing:** When active players are listed as OUT:
  $$\text{stashed} = \min(|\{p \in \mathcal{R} \mid p.\text{status} = \text{'OUT'}\}|, 2)$$
- **Bench Promotion Math:**
  When a starter is moved to IL+, the top bench player is promoted:
  $$\mathbb{E}[\text{Stats}_{\text{active}}] = \sum_{i \in \text{Starters} \setminus \{\text{Injured}\}} \mu_i + \mu_{\text{Bench Promo}}$$
  This algebraically ensures zero dead roster spots and maximizes active weekly games played.

### 5.4. Health-Filtered Waiver Wire Streaming
H2H leagues permit a strict maximum of 3 waiver transactions per week. To prevent wasting streaming claims:
1. Candidate free agents are cross-referenced with `injuries.db`.
2. Any player with severe structural injuries (e.g., Achilles tear, rotator cuff, fracture) is strictly quarantined.
3. Healthy candidate marginal value is computed via $\Delta \mathcal{V} = \mathcal{V}(\mathcal{R} \cup \{p_{\text{add}}\} \setminus \{p_{\text{drop}}\}) - \mathcal{V}(\mathcal{R})$.

### 5.5. Live Availability Mapping & Bayesian Conditioning
For in-season weekly simulations, a player's probability of suiting up for an upcoming game combines their long-term historical baseline with real-time health reports:
- **Baseline Healthy Prior Blending:**
  $$\text{eff\_avail} = \text{clip}(w \cdot \text{anchor} + (1 - w) \cdot \text{availability\_rate}, 0.35, 0.96)$$
  where default $w = 0.35$ and $\text{anchor} = 0.92$ (calibrated via grid search).
- **Official NBA Report Status Multipliers:**
  When a player appears on the official NBA injury report, their conditional participation probability $P(\text{Active})$ is mapped dynamically:
  | Official Status | Conditional Participation $P(\text{Active})$ | Matchup Engine Action |
  |---|:---:|---|
  | `OUT` / `SUSPENDED` | **0.00** | Candidate for 2x IL+ Stash; triggers Bench Promotion |
  | `DOUBTFUL` | **0.25** | High-risk; bench preference |
  | `QUESTIONABLE` / `GTD` | **0.50** | Toss-up; 50% minutes exposure weighting |
  | `PROBABLE` | **0.75** | Favorable; standard start |
  | `AVAILABLE` | **1.00** | Full participation projection |

---

## 6. Autonomous Cloud Architecture & CI/CD Pipelines

```
                                  [Cron Triggers]
                       ┌─────────────────┼─────────────────┐
                       ▼                 ▼                 ▼
                   07:30 UTC         18:30 UTC         22:15 UTC
                   (10:30 TR)        (21:30 TR)        (01:15 TR)
                       │                 │                 │
                       └─────────────────┼─────────────────┘
                                         ▼
                        [GitHub Actions Ubuntu Runner]
                                         │
                                         ▼
                                 [src/cloud_sync.py]
                        1. Ingest Official NBA PDF
                        2. Sync SQLite injuries.db
                        3. Audit 14 Rosters & IL+ Slots
                        4. Filter Waivers & Simulate Matchups
                                         │
                       ┌─────────────────┴─────────────────┐
                       ▼                                   ▼
             [Git Commit & Push]                 [Telegram Bot API]
         Branch: 'nba-fantasy-bot'              Direct Mobile Push Alert
         (Preserves clean 'main')               (HTML Matchup & IL+ Summary)
```

### 6.1. Strategic Execution Timetable
- **Run 1: 10:30 TR / 07:30 UTC / 03:30 ET:** Wrap-up of overnight games and Yahoo waiver claim resolution.
- **Run 2: 21:30 TR / 18:30 UTC / 14:30 ET:** Ingestion of the official afternoon NBA injury report and mid-day IL+ movements.
- **Run 3: 01:15 TR / 22:15 UTC / 18:15 ET:** Pre-game lock 45 minutes prior to 19:00 ET tip-offs, capturing last-minute GTD/OUT status changes.

### 6.2. Dedicated Bot Branch (`nba-fantasy-bot`)
Automated cloud executions commit database states (`injuries.db`), league states (`league_state.json`), and markdown logs exclusively to the `nba-fantasy-bot` branch. The `main` branch remains untouched and strictly human-authored.

### 6.3. Push Notifications
Rich HTML alerts dispatched via Telegram Bot API provide immediate mobile visibility into:
- Roster health status changes (e.g. Kawhi Leonard, Brandon Ingram).
- Actionable IL+ stashing recommendations.
- Top 3 health-vetted waiver streaming candidates for the upcoming matchups.

---

## 7. Testing, Verification & Peer Review

The repository includes a comprehensive unit testing suite verified with Python `unittest`:

```text
Ran 33 tests in 7.258s
OK (skipped=2)
```

### Verified Test Modules
1. **`tests/test_injury_system.py` (22 Unit Tests):**
   - PDF extraction, regex tokenization, 7-column layout line assembly.
   - SQLite table creation, insertion, updates, and timestamp accuracy.
   - Automated clearance validation: omits produce `AVAILABLE` records.
   - Quarantine triggers for malformed reports.
2. **`tests/test_ab_validation.py` (11 Unit Tests):**
   - **Counterfactual Scenarios:** Validates C1 (All Healthy), C2 (Historical Prior), and C3 (Live Status + IL+ Stash + Waiver Streaming).
   - **Algebraic Bench Replacement Identity:** Confirms bench promotion math matches exact theoretical expectations.
   - **Draft Roster Integrity:** Confirms all 14 teams and 182 picks in `draft_data.py` are mapped to valid players without missing or duplicate slots.
   - **14-Team Symmetry & Rank Invariance:** Proves ranking stability across $\rho \in [0.00, 0.20]$.

For full peer review documentation, sensitivity grids, and empirical covariance matrices, refer to [docs/injury_system_architecture_and_peer_review.md](docs/injury_system_architecture_and_peer_review.md).

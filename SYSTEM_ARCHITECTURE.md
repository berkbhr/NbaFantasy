# NBA Fantasy Decision & Simulation Engine - System Architecture

This document details the mathematical and statistical architecture of the NBA Fantasy Head-to-Head (H2H) 9-Category Decision and Simulation Suite, built upon **Probabilistic Decision Theory** and **Conjugate Bayesian Inference**.

---

## 1. Executive Summary

This platform is not a static historical stat calculator; it is an adaptive, predictive decision engine that models injuries, trades, minute fluctuations, and night-to-night variance directly into an **Analytical Category Win Probability ($\Phi$)**.

Rather than relying on piecewise Z-scores, arbitrary punting rules, or heuristic saturation thresholds, every strategic decision—across Draft Selection, Daily Roster Optimization, and Season-Long Waivers/Streaming—optimizes a single unified objective function:

$$\max \mathcal{V}(\text{Roster}) = \sum_{c=1}^{9} \mathbb{P}(\text{Win}_c)$$

---

## 2. Data Engineering Architecture

The automated data pipeline (`src/data_fetcher.py`) fetches official NBA API data and organizes it using Medallion Architecture principles:

### Data Flow & Storage
1. **Raw Layer (`data/raw/`):** Game-by-game player and team logs pulled directly from the NBA API saved as columnar `.parquet` files.
2. **Processed Layer (`data/processed/`):** Cleaned, relational analytical tables:
   - `player_logs_*.parquet`: Game-by-game box scores with playing time and standard categories.
   - `schedule_*.parquet`: Official 82-game regular season schedules with team matchups and week numbers.
   - `trades_*.parquet`: Inferred intra-season player movement and roster changes tracked via team ID transitions.
   - `injuries_dnps_*.parquet`: Inferred DNP (Did Not Play) and injury logs derived from team schedules and actual on-court presence.
   - `player_positions.parquet`: Multi-position Yahoo Fantasy eligibility mappings (`PG, SG, G, SF, PF, F, C, UTIL, BN`).
   - `active_roster_2026_27.parquet`: Active rosters, draft credentials, and preseason roles for the upcoming campaign.

---

## 3. Bayesian Inference & Decision Theory

Player performance is modeled via **Predictive Probability Distributions** rather than single-point estimates.

### 3.1. Shooting Percentages: Beta-Binomial Model
* **Categories:** Field Goal Percentage (FG%), Free Throw Percentage (FT%).
* **Formulation:** Shooting percentages represent discrete trials and successes. The prior and posterior follow $\text{Beta}(\alpha, \beta)$ where $\alpha = \text{Makes}$ and $\beta = \text{Misses}$. Low-volume shooters maintain high predictive uncertainty, which naturally prevents overvaluing erratic high-percentage bench players.
* **Impact Transformation:** To permit linear aggregation and comparison against league benchmarks ($p_{\text{ref}}$), shooting metrics are transformed into **Net Impact**:
  
  $$Y = \text{Makes} - p_{\text{ref}} \cdot \text{Attempts}$$

### 3.2. Counting Statistics: Gamma-Poisson Model
* **Categories:** PTS, REB, AST, STL, BLK, 3PM, TOV.
* **Formulation:** Player output is governed by playing time exposure ($m$ minutes) rather than arbitrary game counts. Per-minute rates follow a Gamma prior $\text{Gamma}(\alpha, \beta)$, generating a **Poisson** likelihood for observed stats.
* **Conjugate Posterior Update:**
  
  $$\alpha_{\text{new}} = \delta \alpha + \text{Stat}, \quad \beta_{\text{new}} = \delta \beta + \text{Minutes}$$

* **Predictive Distribution (Negative Binomial):** Analytically solved with expected value $\mu = m \cdot \frac{\alpha}{\beta}$ and predictive variance:
  
  $$\sigma^2 = \mu + \frac{\mu^2}{\alpha}$$

### 3.3. Discounted Conjugate Filtering (Dynamic Memory)
To reflect recent player form without suffering from infinite memory bias:
* **Soft Daily Decay:** Historical observations decay exponentially with time ($\delta = e^{-\lambda \Delta t}$).
* **Hard Reset on Trade or Role Expansion:** When a player is traded ($\delta_{\text{event}} = 0.2$), the estimated rate parameter ($\alpha/\beta$) is preserved while the effective sample size ($\beta$) is reduced fivefold. Consequently, the first few games with the new team dominate the posterior faster than 50 games with the previous team.

---

## 4. Unified Strategic Decision Layers

### 4.1. The Unified Objective Function: Analytical Gaussian CDF ($\sum \Phi$)
Pairwise category victory against an opponent is computed using the **Standard Normal Cumulative Distribution Function (Gaussian CDF - $\Phi$)**:

$$\mathcal{V}(\text{Roster}) = \sum_{c=1}^{9} \mathbb{P}(\text{Win}_c) = \sum_{c=1}^{9} \Phi\!\left(\frac{\mu_{\text{team}, c} - \mu_{\text{opp}, c}}{\sqrt{\sigma^2_{\text{team}, c} + \sigma^2_{\text{opp}, c}}}\right)$$

This objective function naturally exhibits three critical fantasy properties without manual tuning:
1. **Natural Saturation:** When winning probability exceeds 95% ($Z \ge +2$), the CDF flattens ($\phi(Z) \to 0$). The optimizer automatically stops drafting or streaming surplus stats in safe categories.
2. **Natural Punting:** When winning probability falls below 5% ($Z \le -2$), the lower tail also flattens. The model automatically concedes unrecoverable deficits and redirects capital to swing categories ($Z \approx 0$).
3. **Variance Sensitivity:** When trailing ($\mu_{\text{team}} < \mu_{\text{opp}}$), high-variance options ($\sigma^2 \uparrow$) expand the denominator and pull the negative quotient closer to 0, increasing win probability (rational upside risk). When leading, low-variance players protect the lead.

### 4.2. Live Draft Engine: Lookahead Rollout
During live snake drafts (`src/live_draft_assistant.py`):
* Candidate picks are evaluated not just in isolation, but by projecting future competitor selections across upcoming snake rounds under position constraints (10 active + 3 bench spots).
* **Positional Scarcity** (e.g., center runs or premium playmakers) is naturally internalized through projected roster completion values.

### 4.3. Daily Lineup Optimization: Maximum Weight Bipartite Matching
In `src/matchup_engine.py`, selecting the active 10 starters (`PG, SG, G, SF, PF, F, C, C, UTIL, UTIL`) is solved using **Linear Sum Assignment (Hungarian Algorithm)**:
* Each eligible player's expected marginal utility is weighted by daily matchup category leverage $\phi(z_c)$.
* The bipartite assignment solves globally in $\mathcal{O}(V^3)$ without heuristic approximations, automatically placing surplus players on the bench (`BN`).

### 4.4. Core-Protected In-Season Streaming & Waiver Engine
`league_simulator.py` and `src/model_ai.py` operate in unison throughout the season:
* **Daily Bayesian Updates:** Real match results update posteriors daily via `BayesianPlayer.update_stats`.
* **Core-Protected Streaming:** The top 11 foundational roster spots ("Core") are protected from waiver drops. Only the bottom 2 slots ("Streaming Slots") are cycled based on weekly fixture volume and target categories.

---

## 5. Repository Structure

```text
NbaFantasy/
├── config/
│   └── yahoo_oauth.template.json     # Yahoo OAuth2 API credentials template
├── data/
│   ├── raw/                          # NBA API raw parquet logs
│   ├── processed/                    # Processed relational analytics tables
│   └── simulations/                  # Monte Carlo league & draft simulation artifacts
├── docs/
│   ├── README_TR.md                  # Turkish documentation
│   └── SYSTEM_ARCHITECTURE_TR.md     # Turkish architectural blueprint
├── reports/
│   ├── league_draft_overview_and_projections.md     # 14-Team live draft & model projection report
│   └── league_draft_overview_and_projections.tr.md  # Turkish edition of draft projection report
├── src/
│   ├── bayesian_model.py             # Gamma-Poisson & Beta-Binomial conjugate Bayesian engine
│   ├── matchup_engine.py             # Analytical H2H CDF & Linear Assignment lineup solver
│   ├── live_draft_assistant.py       # Live draft assistant with lookahead rollouts
│   ├── model_ai.py                   # Core-protected streaming & Bayesian decision rules
│   ├── simulator.py                  # Prior season baseline loaders & simulation utilities
│   ├── simulate_slot8_scenarios.py   # Multi-scenario Monte Carlo draft evaluator
│   ├── data_fetcher.py               # NBA API pipeline for rosters, schedules & logs
│   ├── verify_yahoo_names.py         # Player name resolution test suite
│   ├── yahoo_draft_bridge.user.js    # Browser Userscript for Yahoo live draft room integration
│   └── yahoo_draft_sync.py           # Local HTTP synchronization daemon & dashboard
├── league_simulator.py               # Full 12/14-team multi-season H2H league simulation engine
├── requirements.txt                  # Python dependencies
├── README.md                         # Main project overview (English)
└── SYSTEM_ARCHITECTURE.md            # Technical system architecture (English)
```

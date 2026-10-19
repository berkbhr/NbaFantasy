# NBA Fantasy Probabilistic Decision & Simulation Suite (H2H 9-Category)

A quantitative modeling, simulation, and live draft engine for NBA Fantasy Head-to-Head (H2H) 9-Category leagues, powered by **Conjugate Bayesian Inference** and **Analytical Decision Theory**.

> *Dökümantasyonun Türkçe versiyonu için [docs/README_TR.md](docs/README_TR.md) sayfasına bakabilirsiniz.*

---

## 🌟 Key Highlights

1. **Conjugate Bayesian Inference Engine:**
   - **Counting Metrics (PTS, REB, AST, STL, BLK, 3PM, TOV):** Modeled with **Gamma-Poisson / Negative Binomial** predictive distributions with playing-time exposure ($m$ minutes) rather than static per-game averages.
   - **Shooting Percentages (FG%, FT%):** Discrete trial modeling using **Beta-Binomial** conjugate pairs, evaluated as **Net Volume Impact** ($Y = \text{Makes} - p_{\text{ref}} \cdot \text{Attempts}$) relative to league benchmarks.

2. **Discounted Conjugate Filtering (Dynamic Memory):**
   - **Exponential Decay:** Dampens historical samples softly over time ($\delta = e^{-\lambda \Delta t}$).
   - **Event-Driven Reset:** Automatically re-weights prior distributions upon mid-season trades or major role changes ($\delta_{\text{event}} = 0.2$), reducing prior confidence fivefold while preserving player skill efficiency.

3. **Unified Analytical Objective Function (Gaussian CDF $\sum \Phi$):**
   - Replaces ad-hoc Z-scores and brittle manual punt heuristics with an exact closed-form Gaussian Cumulative Distribution Function:
     $$\mathcal{V}(\text{Roster}) = \sum_{c=1}^{9} \Phi\!\left(\frac{\mu_{\text{team}, c} - \mu_{\text{opp}, c}}{\sqrt{\sigma^2_{\text{team}, c} + \sigma^2_{\text{opp}, c}}}\right)$$
   - **Natural Saturation:** Diminishing returns in dominant categories ($Z \ge +2$).
   - **Natural Punting:** Rational concession of unwinnable categories ($Z \le -2$) to optimize close swing categories.
   - **Variance Optimization:** Preference for high-upside players when trailing, and consistent floors when leading.

4. **Real-Time Yahoo Fantasy Draft Integration:**
   - **Browser Bridge (`src/yahoo_draft_bridge.user.js`):** Tampermonkey/Violentmonkey script that captures live draft room picks, board selections, and manager rosters in real time with zero latency.
   - **Local Sync Daemon (`src/yahoo_draft_sync.py`):** Multi-threaded local server bridging browser webhooks or OAuth2 endpoints with the backend.
   - **Live Draft Assistant (`src/live_draft_assistant.py`):** Pairwise H2H rollouts and lookahead simulations delivering real-time pick recommendations.

5. **Monte Carlo League Simulation:**
   - Full 12/14-team multi-season league simulator (`league_simulator.py`) replicating weekly head-to-head schedules, injury absences, and streaming waiver transactions.

---

## 📁 Repository Structure

```text
NbaFantasy/
├── config/
│   └── yahoo_oauth.template.json     # Yahoo OAuth2 configuration template
├── data/
│   ├── raw/                          # Raw NBA API box scores & logs (Parquet)
│   ├── processed/                    # Processed relational analytics tables (Parquet)
│   └── simulations/                  # Monte Carlo league & draft simulation outputs
├── docs/
│   ├── README_TR.md                  # Türkçe dokümantasyon
│   └── SYSTEM_ARCHITECTURE_TR.md     # Türkçe sistem mimarisi dokümanı
├── reports/
│   ├── league_draft_overview_and_projections.md     # 14-Team live draft & model projection report (EN)
│   └── league_draft_overview_and_projections.tr.md  # 14 Takımlı canlı draft & model projeksiyon raporu (TR)
├── src/
│   ├── bayesian_model.py             # Gamma-Poisson & Beta-Binomial conjugate engine
│   ├── matchup_engine.py             # Analytical H2H CDF & Linear Assignment lineup solver
│   ├── live_draft_assistant.py       # Live draft assistant with lookahead rollouts
│   ├── model_ai.py                   # Bayesian core-protected waiver & decision engine
│   ├── simulator.py                  # Prior season baseline loaders & utilities
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

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/berkbhr/NbaFantasy.git
cd NbaFantasy
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Yahoo OAuth Setup (Optional - for Live Draft Sync)
Copy `config/yahoo_oauth.template.json` to `config/yahoo_oauth.json` and insert your developer credentials:
```bash
cp config/yahoo_oauth.template.json config/yahoo_oauth.json
```
*(Note: `config/yahoo_oauth.json` is protected by `.gitignore` and never committed.)*

---

## 📊 Usage Examples

### Update NBA Data & Pre-Draft Assets
```bash
python -m src.data_fetcher
```

### Launch Live Draft Assistant & Sync Daemon
```bash
python -m src.live_draft_assistant
```

### Run Full League Monte Carlo Simulation
```bash
python league_simulator.py
```

### Run Name Matching & Integration Tests
```bash
python -m src.verify_yahoo_names
```

---

## 📐 Mathematical Framework

Weekly category expected outcome is computed analytically as:

$$\mathcal{V}(\text{Roster}) = \sum_{c=1}^{9} \mathbb{P}(\text{Win}_c) = \sum_{c=1}^{9} \Phi\!\left(\frac{\mu_{\text{team}, c} - \mu_{\text{opp}, c}}{\sqrt{\sigma^2_{\text{team}, c} + \sigma^2_{\text{opp}, c}}}\right)$$

For full mathematical proofs, Dirichlet/Gamma conjugate derivations, and optimization algorithms, refer to [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) (or [docs/SYSTEM_ARCHITECTURE_TR.md](docs/SYSTEM_ARCHITECTURE_TR.md) for the Turkish edition).

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

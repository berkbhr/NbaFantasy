# 🏀 NBA Fantasy Autonomous Cloud Sync Report
**Sync Timestamp:** `2026-10-25 21:00:16 UTC`  
**Official NBA Ingestion:** `https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-10-25_05_00PM.pdf`  
**Yahoo League Status:** `OAuth2 configured, but league discovery returned False (Yahoo HTTP 403: Forbidden)`  

---

## 1. 🛡️ Berk's Best Team Roster, IL+ & Slot Audit
| Player | Active/IL+ Slot | Status | Play Probability | Notes / Reason |
| :--- | :---: | :---: | :---: | :--- |
| ✅ **Tyrese Maxey** | `Active/BN` | Healthy | `0.86` | Expected to play |
| ✅ **James Harden** | `Active/BN` | Healthy | `0.88` | Expected to play |
| ⚠️ **Kawhi Leonard** | `Active/BN` | **HEALTHY** | `0.84` | Expected to play |
| ✅ **Desmond Bane** | `Active/BN` | Healthy | `0.92` | Expected to play |
| ⚠️ **Jarrett Allen** | `Active/BN` | **HEALTHY** | `0.85` | Expected to play |
| ✅ **Jabari Smith Jr.** | `Active/BN` | Healthy | `0.90` | Expected to play |
| ✅ **Josh Hart** | `Active/BN` | Healthy | `0.87` | Expected to play |
| ✅ **Neemias Queta** | `Active/BN` | Healthy | `0.89` | Expected to play |
| ❌ **Brandon Ingram** | `⚠️ Move to IL+` | **OUT** | `0.00` | Ingram won't be ready for the start of the season due to a partially torn Achilles, per Joey Linn of SI.com. |
| ✅ **Ayo Dosunmu** | `Active/BN` | Healthy | `0.86` | Expected to play |
| ✅ **Nikola Vučević** | `Active/BN` | Healthy | `0.85` | Expected to play |
| ✅ **Julian Champagnie** | `Active/BN` | Healthy | `0.92` | Expected to play |
| ✅ **Jay Huff** | `Active/BN` | Healthy | `0.92` | Expected to play |

### 🔍 League-Wide IL+ Stashes & Open Roster Slots
| Slot & Team | Players in IL/IL+ | Injured in Active/BN (Needs IL) | Empty Active Roster Spots |
| :--- | :--- | :--- | :---: |
| **#1 MuCa Tandır** | — | Kon Knueppel (OUT) | `0` |
| **#2 Mordor Tulums** | — | Tobias Harris (OUT) | `0` |
| **#4 Houston Buckets** | — | Nic Claxton (OUT) | `0` |
| **#5 Kuvâ-yi Milfiye** | — | Mikel Brown Jr. (OUT) | `0` |
| **#6 abu dhabi camels** | — | Joel Embiid (OUT), AJ Dybantsa (OUT) | `0` |
| **#8 Berk's Best Team** | — | Brandon Ingram (OUT) | `0` |
| **#9 FatihTerimSpor** | — | Jalen Duren (OUT), Paolo Banchero (OUT) | `0` |
| **#10 Redeem Team** | — | Ben Simmons (OUT) | `0` |
| **#11 Fikirtepe Warriors** | — | Cooper Flagg (OUT), Coby White (OUT) | `0` |
| **#12 Istanbul Brickmakers** | — | Zach Edey (OUT), Yves Missi (OUT) | `0` |
| **#13 SILE BULLS** | — | Jimmy Butler III (OUT) | `0` |

---

## 2. 🔄 Recent League Transactions (Who Added / Dropped Whom)
* *No live transactions recorded yet (or awaiting Yahoo OAuth token refresh).*

---

## 3. 🎯 Dynamic Add/Drop Recommendations (Remaining Games & Live Scoreboard Weighted)
Optimized via $\Delta \sum_{c=1}^{9} \Phi_c$ conditioned on live category margins and remaining games this week:

| Rank | Action | Add Target (FA) | Drop Candidate | Rem Games (Add/Drop) | $\Delta E[\text{Wins}]$ | Key Category Gains |
| :---: | :---: | :--- | :--- | :---: | :---: | :--- |
| #1 | `ADD (Boş Yuva / IL+)` | **Kyle Filipowski** | Boş Yuva (IL+ Stash) | `3.4 / 0.0` | **`+0.424`** | REB (+18.2%), PTS (+9.3%) |
| #2 | `ADD (Boş Yuva / IL+)` | **Precious Achiuwa** | Boş Yuva (IL+ Stash) | `3.4 / 0.0` | **`+0.384`** | REB (+15.7%), STL (+9.4%) |
| #3 | `ADD (Boş Yuva / IL+)` | **Duncan Robinson** | Boş Yuva (IL+ Stash) | `3.4 / 0.0` | **`+0.383`** | FG3M (+14.6%), PTS (+10.4%) |
| #4 | `ADD (Boş Yuva / IL+)` | **Kris Dunn** | Boş Yuva (IL+ Stash) | `3.4 / 0.0` | **`+0.382`** | STL (+13.3%), AST (+11.0%) |
| #5 | `ADD (Boş Yuva / IL+)` | **Gary Payton II** | Boş Yuva (IL+ Stash) | `3.4 / 0.0` | **`+0.366`** | STL (+10.7%), REB (+10.0%) |

### 📋 Available Healthy Free Agents Pool (Top 8)
| Rank | Free Agent | Source | Exp Min (Boost) | Base Z | Eff Availability |
| :---: | :--- | :---: | :---: | :---: | :---: |
| #1 | **Kyle Filipowski** | `Unrostered FA` | `28.8m (+5.4m)` | `0.59` | `0.90` |
| #2 | **Kris Dunn** | `Unrostered FA` | `31.0m (+5.6m)` | `0.45` | `0.92` |
| #3 | **Gary Payton II** | `Unrostered FA` | `25.0m (+7.7m)` | `0.21` | `0.88` |
| #4 | **Precious Achiuwa** | `Unrostered FA` | `31.0m (+6.6m)` | `-0.14` | `0.88` |
| #5 | **Duncan Robinson** | `Unrostered FA` | `31.0m (+5.4m)` | `-0.92` | `0.90` |
| #6 | **Kevin Huerter** | `Unrostered FA` | `27.7m (+5.1m)` | `-1.30` | `0.86` |
| #7 | **Max Christie** | `Unrostered FA` | `31.9m (+4.5m)` | `-1.57` | `0.90` |
| #8 | **Jordan Goodwin** | `Unrostered FA` | `24.0m (+2.4m)` | `-1.62` | `0.86` |

---

## 4. ⚔️ Live Matchup Scoreboard & Updated Projections: Berk's Best Team vs SILE BULLS
* **IL+ Stash:** `Brandon Ingram`
* **Top Auto-Streamer:** `Kyle Filipowski`
* **Remaining Games Multiplier:** `Berk: 100% remaining | SILE BULLS: 100% remaining`
* **Expected Matchup Outcome:** **5.17 - 3.83** | **Matchup Win Prob $P(\ge 5\text{ cats})$:** **`%67.8`** (Berk favori)

| Category | Berk's Expected | SILE BULLS Expected | Berk Win Prob | Projected Winner |
| :--- | :---: | :---: | :---: | :---: |
| **PTS** | `587.5` | `552.5` | `%61.4` | 🏆 Berk |
| **REB** | `222.7` | `202.1` | `%66.2` | 🏆 Berk |
| **AST** | `125.2` | `135.4` | `%36.8` | SILE BULLS |
| **STL** | `37.0` | `37.0` | `%50.0` | ⚖️ Toss-up |
| **BLK** | `24.0` | `24.0` | `%50.1` | ⚖️ Toss-up |
| **FG3M** | `62.8` | `59.8` | `%56.9` | 🏆 Berk |
| **TOV** | `62.0` | `66.7` | `%60.8` | 🏆 Berk |
| **FG%** | `.489` | `.470` | `%68.2` | 🏆 Berk |
| **FT%** | `.820` | `.794` | `%67.0` | 🏆 Berk |
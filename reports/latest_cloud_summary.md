# 🏀 NBA Fantasy Autonomous Cloud Sync Report
**Sync Timestamp:** `2026-10-25 19:37:05 UTC`  
**Official NBA Ingestion:** `https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-10-25_03_30PM.pdf`  
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
| #1 | `ADD (Boş Yuva / IL+)` | **Kyle Filipowski** | Boş Yuva (IL+ Stash) | `3.4 / 0.0` | **`+0.438`** | REB (+15.9%), PTS (+11.2%) |
| #2 | `ADD (Boş Yuva / IL+)` | **Naji Marshall** | Boş Yuva (IL+ Stash) | `3.4 / 0.0` | **`+0.405`** | PTS (+14.4%), AST (+11.4%) |
| #3 | `ADD (Boş Yuva / IL+)` | **Duncan Robinson** | Boş Yuva (IL+ Stash) | `3.4 / 0.0` | **`+0.390`** | FG3M (+15.5%), PTS (+10.8%) |
| #4 | `ADD (Boş Yuva / IL+)` | **Precious Achiuwa** | Boş Yuva (IL+ Stash) | `3.4 / 0.0` | **`+0.385`** | REB (+15.9%), PTS (+9.5%) |
| #5 | `ADD (Boş Yuva / IL+)` | **Kris Dunn** | Boş Yuva (IL+ Stash) | `3.4 / 0.0` | **`+0.380`** | STL (+13.2%), AST (+9.9%) |

### 📋 Available Healthy Free Agents Pool (Top 8)
| Rank | Free Agent | Source | Exp Min (Boost) | Base Z | Eff Availability |
| :---: | :--- | :---: | :---: | :---: | :---: |
| #1 | **Kyle Filipowski** | `Unrostered FA` | `28.8m (+5.5m)` | `0.59` | `0.90` |
| #2 | **Naji Marshall** | `Unrostered FA` | `35.5m (+7.6m)` | `0.49` | `0.88` |
| #3 | **Kris Dunn** | `Unrostered FA` | `31.0m (+5.6m)` | `0.45` | `0.92` |
| #4 | **Gary Payton II** | `Unrostered FA` | `25.0m (+7.7m)` | `0.21` | `0.88` |
| #5 | **Precious Achiuwa** | `Unrostered FA` | `31.0m (+6.6m)` | `-0.14` | `0.88` |
| #6 | **Duncan Robinson** | `Unrostered FA` | `31.0m (+5.4m)` | `-0.92` | `0.90` |
| #7 | **Max Christie** | `Unrostered FA` | `33.6m (+6.2m)` | `-1.00` | `0.90` |
| #8 | **Kevin Huerter** | `Unrostered FA` | `27.7m (+5.1m)` | `-1.30` | `0.86` |

---

## 4. ⚔️ Live Matchup Scoreboard & Updated Projections: Berk's Best Team vs SILE BULLS
* **IL+ Stash:** `Brandon Ingram`
* **Top Auto-Streamer:** `Kyle Filipowski`
* **Remaining Games Multiplier:** `Berk: 100% remaining | SILE BULLS: 100% remaining`
* **Expected Matchup Outcome:** **4.91 - 4.09** | **Matchup Win Prob $P(\ge 5\text{ cats})$:** **`%61.0`** (Berk favori)

| Category | Berk's Expected | SILE BULLS Expected | Berk Win Prob | Projected Winner |
| :--- | :---: | :---: | :---: | :---: |
| **PTS** | `587.5` | `572.6` | `%55.0` | 🏆 Berk |
| **REB** | `222.8` | `209.0` | `%61.0` | 🏆 Berk |
| **AST** | `125.2` | `140.7` | `%30.1` | SILE BULLS |
| **STL** | `37.0` | `38.8` | `%43.9` | SILE BULLS |
| **BLK** | `24.0` | `24.6` | `%47.3` | SILE BULLS |
| **FG3M** | `62.8` | `62.3` | `%51.2` | ⚖️ Toss-up |
| **TOV** | `62.0` | `69.0` | `%66.0` | 🏆 Berk |
| **FG%** | `.489` | `.469` | `%69.3` | 🏆 Berk |
| **FT%** | `.820` | `.794` | `%66.7` | 🏆 Berk |
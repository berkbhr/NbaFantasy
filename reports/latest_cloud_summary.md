# 🏀 NBA Fantasy Autonomous Cloud Sync Report
**Sync Timestamp:** `2026-10-26 19:02:03 UTC`  
**Official NBA Ingestion:** `https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-10-26_03_00PM.pdf`  
**Yahoo League Status:** `Tarayıcı Köprüsü Aktif (14 Takım Canlı Kadro & Skor)`  

---

## 1. 🛡️ Berk's Best Team Roster, IL+ & Slot Audit
| Player | Active/IL+ Slot | Status | Play Probability | Notes / Reason |
| :--- | :---: | :---: | :---: | :--- |
| ✅ **Tyrese Maxey** | `Active/BN` | Healthy | `0.87` | Expected to play |
| ✅ **Ayo Dosunmu** | `Active/BN` | Healthy | `0.86` | Expected to play |
| ✅ **James Harden** | `Active/BN` | Healthy | `0.88` | Expected to play |
| ⚠️ **Bilal Coulibaly** | `Active/BN` | **HEALTHY** | `0.81` | Expected to play |
| ✅ **Jabari Smith Jr.** | `Active/BN` | Healthy | `0.90` | Expected to play |
| ✅ **Josh Hart** | `Active/BN` | Healthy | `0.87` | Expected to play |
| ⚠️ **Jaxson Hayes** | `Active/BN` | **QUESTIONABLE** | `0.52` | Injury/Illness - Right Soreness |
| ⚠️ **Jarrett Allen** | `Active/BN` | **HEALTHY** | `0.85` | Expected to play |
| ✅ **Julian Champagnie** | `Active/BN` | Healthy | `0.92` | Expected to play |
| ✅ **Neemias Queta** | `Active/BN` | Healthy | `0.90` | Expected to play |
| ✅ **Desmond Bane** | `Active/BN` | Healthy | `0.92` | Expected to play |
| ✅ **Precious Achiuwa** | `Active/BN` | Healthy | `0.88` | Expected to play |
| ⚠️ **Kawhi Leonard** | `Active/BN` | **QUESTIONABLE** | `0.52` | Leonard is out for Sunday's game against the Timberwolves due to left knee swelling, Blake Murphy of Sportsnet.ca reports. |
| ❌ **Brandon Ingram** | `IL+` | **OUT** | `0.00` | Ingram won't be ready for the start of the season due to a partially torn Achilles, per Joey Linn of SI.com. |

### 🔍 League-Wide IL+ Stashes & Open Roster Slots
| Slot & Team | Players in IL/IL+ | Injured in Active/BN (Needs IL) | Empty Active Roster Spots |
| :--- | :--- | :--- | :---: |
| **#1 MuCa Tandır** | Naji Marshall, Kon Knueppel | — | `0` |
| **#2 Mordor Tulums** | Cameron Johnson, Tobias Harris | — | `0` |
| **#3 Philadelphia Sikers** | — | Ivica Zubac (OUT) | `0` |
| **#4 Houston Buckets** | — | Jalen Williams (O), Nic Claxton (O) | `0` |
| **#6 abu dhabi camels** | — | AJ Dybantsa (O) | `0` |
| **#7 Samurai Strikers** | Mark Williams | — | `0` |
| **#8 Berk's Best Team** | Brandon Ingram | — | `0` |
| **#9 FatihTerimSpor** | Jalen Duren, Paolo Banchero | — | `0` |
| **#11 Fikirtepe Warriors** | Jusuf Nurkić, Coby White | — | `0` |
| **#12 Istanbul Brickmakers** | Kristaps Porziņģis, Yves Missi | — | `0` |
| **#13 SILE BULLS** | VJ Edgecombe, Jimmy Butler III | — | `0` |
| **#14 YearOne Tyrants** | — | Jalen Suggs (OUT) | `0` |

---

## 2. 🔄 Recent League Transactions (Who Added / Dropped Whom)
| Transaction | Team | Added Player(s) | Dropped Player(s) |
| :---: | :--- | :--- | :--- |
| `ADD/DROP` | **SILE BULLS** | ➕ **Ja'Kobe Walter** | — |
| `ADD/DROP` | **FatihTerimSpor** | ➕ **Trevon Brazile** | ➖ Noah Clowney |
| `ADD/DROP` | **MuCa Tandırs** | ➕ **Reed Sheppard** | — |
| `ADD/DROP` | **Samurai Strikers** | ➕ **Jay Huff** | ➖ Miles McBride |
| `ADD/DROP` | **Kuvâ-yi Milfiye** | ➕ **Alex Caruso** | ➖ Ziaire Williams |
| `ADD/DROP` | **Samurai Strikers** | ➕ **Jeremiah Fears** | — |
| `ADD/DROP` | **FatihTerimSpor** | ➕ **Kyle Kuzma** | ➖ Ryan Kalkbrenner |
| `ADD/DROP` | **Kuvâ-yi Milfiye** | ➕ **Ziaire Williams** | — |
| `ADD/DROP` | **Redeem Team** | ➕ **Marcus Smart** | — |
| `ADD/DROP` | **Samurai Strikers** | ➕ **Miles McBride** | — |
| `ADD/DROP` | **MuCa Tandırs** | ➕ **Derrick Jones Jr.** | ➖ Herbert Jones |
| `ADD/DROP` | **Istanbul Brickmakers 🧱** | ➕ **Khaman Maluach** | — |

---

## 3. 🎯 Dynamic Add/Drop Recommendations (Remaining Games & Live Scoreboard Weighted)
Optimized via $\Delta \sum_{c=1}^{9} \Phi_c$ conditioned on live category margins and remaining games this week:

| Rank | Action | Add Target (FA) | Drop Candidate | Rem Games (Add/Drop) | $\Delta E[\text{Wins}]$ | Key Category Gains |
| :---: | :---: | :--- | :--- | :---: | :---: | :--- |
| #1 | `ADD / DROP` | **Ryan Kalkbrenner** | Jaxson Hayes | `4.0 / 3.0` | **`+0.271`** | PTS (%49 ➔ %53), REB (%37 ➔ %46) |
| #2 | `ADD / DROP` | **Moussa Diabaté** | Jaxson Hayes | `4.0 / 3.0` | **`+0.209`** | REB (%37 ➔ %51), STL (%49 ➔ %55) |
| #3 | `ADD / DROP` | **Dean Wade** | Jaxson Hayes | `3.0 / 3.0` | **`+0.174`** | STL (%49 ➔ %57), PTS (%49 ➔ %50) |
| #4 | `ADD / DROP` | **Jock Landale** | Jaxson Hayes | `4.0 / 3.0` | **`+0.144`** | PTS (%49 ➔ %53), REB (%37 ➔ %43) |
| #5 | `ADD / DROP` | **Ziaire Williams** | Jaxson Hayes | `4.0 / 3.0` | **`+0.121`** | STL (%49 ➔ %55), PTS (%49 ➔ %53) |
| #6 | `ADD / DROP` | **Sam Merrill** | Jaxson Hayes | `4.0 / 3.0` | **`+0.103`** | PTS (%49 ➔ %52), STL (%49 ➔ %51) |
| #7 | `ADD / DROP` | **Royce O'Neale** | Jaxson Hayes | `4.0 / 3.0` | **`+0.072`** | STL (%49 ➔ %52), FT_PCT (%54 ➔ %56) |
| #8 | `ADD / DROP` | **Luguentz Dort** | Jaxson Hayes | `4.0 / 3.0` | **`+0.070`** | STL (%49 ➔ %53), PTS (%49 ➔ %51) |
| #9 | `ADD / DROP` | **Jake LaRavia** | Jaxson Hayes | `4.0 / 3.0` | **`+0.069`** | STL (%49 ➔ %55), FT_PCT (%54 ➔ %56) |
| #10 | `ADD / DROP` | **Jarace Walker** | Jaxson Hayes | `4.0 / 3.0` | **`+0.063`** | PTS (%49 ➔ %53), STL (%49 ➔ %52) |
| #11 | `ADD / DROP` | **Justin Champagnie** | Jaxson Hayes | `3.0 / 3.0` | **`+0.038`** | STL (%49 ➔ %50), FT_PCT (%54 ➔ %56) |
| #12 | `ADD / DROP` | **Max Christie** | Bilal Coulibaly | `3.0 / 3.0` | **`+0.025`** | PTS (%49 ➔ %50), FT_PCT (%54 ➔ %55) |

### 📋 Available Healthy Free Agents Pool (Top 8)
| Rank | Free Agent | Source | Exp Min (Boost) | Base Z | Eff Availability |
| :---: | :--- | :---: | :---: | :---: | :---: |
| #1 | **Moussa Diabaté** | `🔥 Dropped by Team` | `27.4m (+2.6m)` | `-0.82` | `0.88` |
| #2 | **Dean Wade** | `Unrostered FA` | `29.0m` | `-1.33` | `0.81` |
| #3 | **Justin Champagnie** | `Unrostered FA` | `22.3m` | `-2.00` | `0.86` |
| #4 | **Max Christie** | `Unrostered FA` | `32.6m (+3.4m)` | `-2.27` | `0.90` |
| #5 | **Ryan Kalkbrenner** | `Unrostered FA` | `21.6m (+2.1m)` | `-2.44` | `0.86` |
| #6 | **Ziaire Williams** | `Unrostered FA` | `26.0m` | `-2.84` | `0.82` |
| #7 | **Jordan Goodwin** | `Unrostered FA` | `21.9m (+0.6m)` | `-2.93` | `0.87` |
| #8 | **Kevin Huerter** | `Unrostered FA` | `25.6m (+3.7m)` | `-2.96` | `0.86` |

---

## 4. ⚔️ Live Matchup Scoreboard & Updated Projections: Berk's Best Team vs Mordor Tulums
* **IL+ Stash:** `Brandon Ingram`
* **Top Auto-Streamer:** `Moussa Diabaté`
* **Remaining Games Multiplier:** `Berk: 100% remaining | Mordor Tulums: 100% remaining`
* **Expected Matchup Outcome:** **4.48 - 4.52** | **Matchup Win Prob $P(\ge 5\text{ cats})$:** **`%49.4`** (Mordor Tulums favori)

| Category | Live Score | Berk Proj Final | Mordor Tulums Proj Final | Berk Win Prob | Projected Winner |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **PTS** | `0 - 0` | `580.0` | `564.4` | `%55.0` | 🏆 Berk |
| **REB** | `0 - 0` | `238.9` | `229.5` | `%57.0` | 🏆 Berk |
| **AST** | `0 - 0` | `122.4` | `94.8` | `%84.4` | 🏆 Berk |
| **STL** | `0 - 0` | `42.1` | `39.6` | `%58.3` | 🏆 Berk |
| **BLK** | `0 - 0` | `28.7` | `31.0` | `%41.6` | Mordor Tulums |
| **FG3M** | `0 - 0` | `56.0` | `68.3` | `%25.3` | Mordor Tulums |
| **TOV** | `0 - 0` | `63.3` | `54.6` | `%29.7` | Mordor Tulums |
| **FG%** | `.494 - .496` | `.494` | `.496` | `%47.8` | Mordor Tulums |
| **FT%** | `.791 - .794` | `.791` | `.794` | `%48.5` | Mordor Tulums |
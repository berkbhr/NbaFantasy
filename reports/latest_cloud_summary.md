# 🏀 NBA Fantasy Autonomous Cloud Sync Report
**Sync Timestamp:** `2026-10-25 21:29:08 UTC`  
**Official NBA Ingestion:** `https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-10-25_05_15PM.pdf`  
**Yahoo League Status:** `Tarayıcı Köprüsü Aktif (14 Takım Canlı Kadro & Skor)`  

---

## 1. 🛡️ Berk's Best Team Roster, IL+ & Slot Audit
| Player | Active/IL+ Slot | Status | Play Probability | Notes / Reason |
| :--- | :---: | :---: | :---: | :--- |
| ✅ **Tyrese Maxey** | `Active/BN` | Healthy | `0.86` | Expected to play |
| ✅ **Ayo Dosunmu** | `Active/BN` | Healthy | `0.86` | Expected to play |
| ✅ **James Harden** | `Active/BN` | Healthy | `0.88` | Expected to play |
| ✅ **Desmond Bane** | `Active/BN` | Healthy | `0.92` | Expected to play |
| ⚠️ **Kawhi Leonard** | `Active/BN` | **HEALTHY** | `0.84` | Expected to play |
| ✅ **Josh Hart** | `Active/BN` | Healthy | `0.87` | Expected to play |
| ✅ **Precious Achiuwa** | `Active/BN` | Healthy | `0.88` | Expected to play |
| ⚠️ **Jaxson Hayes** | `Active/BN` | **HEALTHY** | `0.84` | Expected to play |
| ✅ **Julian Champagnie** | `Active/BN` | Healthy | `0.92` | Expected to play |
| ✅ **Neemias Queta** | `Active/BN` | Healthy | `0.89` | Expected to play |
| ⚠️ **Bilal Coulibaly** | `Active/BN` | **HEALTHY** | `0.80` | Expected to play |
| ✅ **Jabari Smith Jr.** | `Active/BN` | Healthy | `0.90` | Expected to play |
| ⚠️ **Jarrett Allen** | `Active/BN` | **HEALTHY** | `0.85` | Expected to play |
| ❌ **Brandon Ingram** | `IL+` | **OUT** | `0.00` | Ingram won't be ready for the start of the season due to a partially torn Achilles, per Joey Linn of SI.com. |

### 🔍 League-Wide IL+ Stashes & Open Roster Slots
| Slot & Team | Players in IL/IL+ | Injured in Active/BN (Needs IL) | Empty Active Roster Spots |
| :--- | :--- | :--- | :---: |
| **#1 MuCa Tandır** | Kon Knueppel | Naji Marshall (O) | `0` |
| **#2 Mordor Tulums** | Cameron Johnson, Tobias Harris | — | `0` |
| **#4 Houston Buckets** | — | Nic Claxton (O) | `0` |
| **#5 Kuvâ-yi Milfiye** | — | — | `1` |
| **#6 abu dhabi camels** | — | Joel Embiid (O), AJ Dybantsa (O) | `0` |
| **#7 Samurai Strikers** | Mark Williams, Brandin Podziemski | — | `0` |
| **#8 Berk's Best Team** | Brandon Ingram | — | `0` |
| **#9 FatihTerimSpor** | Jalen Duren, Paolo Banchero | — | `0` |
| **#10 Redeem Team** | Draymond Green, Fred VanVleet | — | `2` |
| **#11 Fikirtepe Warriors** | Jusuf Nurkić, Coby White | Cooper Flagg (O) | `0` |
| **#12 Istanbul Brickmakers** | Zach Edey, Yves Missi | Kristaps Porziņģis (O) | `0` |
| **#13 SILE BULLS** | Jimmy Butler III | — | `0` |

---

## 2. 🔄 Recent League Transactions (Who Added / Dropped Whom)
| Transaction | Team | Added Player(s) | Dropped Player(s) |
| :---: | :--- | :--- | :--- |
| `ADD/DROP` | **FatihTerimSpor** | ➕ **Kyle Kuzma** | ➖ Ryan Kalkbrenner |
| `ADD/DROP` | **Kuvâ-yi Milfiye** | ➕ **Ziaire Williams** | — |
| `ADD/DROP` | **Redeem Team** | ➕ **Marcus Smart** | — |
| `ADD/DROP` | **Samurai Strikers** | ➕ **Miles McBride** | — |
| `ADD/DROP` | **MuCa Tandır** | ➕ **Derrick Jones Jr.** | ➖ Herbert Jones |
| `ADD/DROP` | **Istanbul Brickmakers** | ➕ **Khaman Maluach** | — |
| `ADD/DROP` | **Kuvâ-yi Milfiye** | ➕ **Moussa Diabaté** | — |
| `ADD/DROP` | **Kuvâ-yi Milfiye** | ➕ **Gui Santos** | — |
| `ADD/DROP` | **YearOne Tyrants** | ➕ **Tristan da Silva** | ➖ Scoot Henderson |
| `ADD/DROP` | **FatihTerimSpor** | ➕ **Noah Clowney** | — |
| `ADD/DROP` | **SILE BULLS** | ➕ **Kasparas Jakučionis** | ➖ Pelle Larsson |

---

## 3. 🎯 Dynamic Add/Drop Recommendations (Remaining Games & Live Scoreboard Weighted)
Optimized via $\Delta \sum_{c=1}^{9} \Phi_c$ conditioned on live category margins and remaining games this week:

| Rank | Action | Add Target (FA) | Drop Candidate | Rem Games (Add/Drop) | $\Delta E[\text{Wins}]$ | Key Category Gains |
| :---: | :---: | :--- | :--- | :---: | :---: | :--- |
| #1 | `ADD / DROP` | **Nikola Vučević** | Jaxson Hayes | `0.6 / 0.6` | **`+0.113`** | REB (+4.5%), PTS (+3.6%) |
| #2 | `ADD / DROP` | **Kyle Filipowski** | Jaxson Hayes | `0.6 / 0.6` | **`+0.101`** | REB (+4.9%), PTS (+3.3%) |
| #3 | `ADD / DROP` | **Nickeil Alexander-Walker** | Jaxson Hayes | `0.6 / 0.6` | **`+0.088`** | FG3M (+5.2%), PTS (+4.3%) |
| #4 | `ADD / DROP` | **Moussa Diabaté** | Jaxson Hayes | `0.6 / 0.6` | **`+0.065`** | REB (+6.5%), PTS (+0.6%) |
| #5 | `ADD / DROP` | **Brice Sensabaugh** | Jaxson Hayes | `0.6 / 0.6` | **`+0.063`** | FG3M (+3.7%), PTS (+3.1%) |

### 📋 Available Healthy Free Agents Pool (Top 8)
| Rank | Free Agent | Source | Exp Min (Boost) | Base Z | Eff Availability |
| :---: | :--- | :---: | :---: | :---: | :---: |
| #1 | **Nickeil Alexander-Walker** | `🔥 Dropped by Team` | `30.6m` | `1.76` | `0.91` |
| #2 | **Nikola Vučević** | `🔥 Dropped by Team` | `28.9m (+3.0m)` | `1.34` | `0.85` |
| #3 | **Reed Sheppard** | `🔥 Dropped by Team` | `26.9m (+3.7m)` | `1.16` | `0.92` |
| #4 | **Kyle Filipowski** | `Unrostered FA` | `28.8m (+5.4m)` | `0.59` | `0.90` |
| #5 | **Moussa Diabaté** | `🔥 Dropped by Team` | `28.8m (+4.8m)` | `-0.47` | `0.88` |
| #6 | **Kevin Porter Jr.** | `🔥 Dropped by Team` | `26.9m` | `-0.79` | `0.83` |
| #7 | **Jay Huff** | `🔥 Dropped by Team` | `19.7m` | `-1.19` | `0.92` |
| #8 | **Gary Payton II** | `Unrostered FA` | `22.2m (+4.9m)` | `-1.23` | `0.88` |

---

## 4. ⚔️ Live Matchup Scoreboard & Updated Projections: Berk's Best Team vs SILE BULLS
* **IL+ Stash:** `Brandon Ingram`
* **Top Auto-Streamer:** `Nickeil Alexander-Walker`
* **Remaining Games Multiplier:** `Berk: 19% remaining | SILE BULLS: 17% remaining`
* **Expected Matchup Outcome:** **6.16 - 2.84** | **Matchup Win Prob $P(\ge 5\text{ cats})$:** **`%95.3`** (Berk favori)

| Category | Live Score | Berk Proj Final | SILE BULLS Proj Final | Berk Win Prob | Projected Winner |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **PTS** | `420 - 437` | `532.5` | `530.7` | `%51.4` | ⚖️ Toss-up |
| **REB** | `147 - 164` | `186.3` | `195.3` | `%32.4` | SILE BULLS |
| **AST** | `70 - 103` | `93.7` | `126.2` | `%0.5` | SILE BULLS |
| **STL** | `41 - 28` | `48.5` | `34.6` | `%99.8` | 🏆 Berk |
| **BLK** | `30 - 24` | `34.3` | `27.9` | `%95.4` | 🏆 Berk |
| **FG3M** | `44 - 41` | `55.9` | `51.9` | `%70.3` | 🏆 Berk |
| **TOV** | `43 - 80` | `54.8` | `91.2` | `%100.0` | 🏆 Berk |
| **FG%** | `.459 - .452` | `.464` | `.454` | `%70.1` | 🏆 Berk |
| **FT%** | `.811 - .770` | `.813` | `.775` | `%95.7` | 🏆 Berk |
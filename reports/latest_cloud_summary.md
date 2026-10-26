# 🏀 NBA Fantasy Autonomous Cloud Sync Report
**Sync Timestamp:** `2026-10-26 00:24:13 UTC`  
**Official NBA Ingestion:** `https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-10-25_08_15PM.pdf`  
**Yahoo League Status:** `Tarayıcı Köprüsü Aktif (14 Takım Canlı Kadro & Skor)`  

---

## 1. 🛡️ Berk's Best Team Roster, IL+ & Slot Audit
| Player | Active/IL+ Slot | Status | Play Probability | Notes / Reason |
| :--- | :---: | :---: | :---: | :--- |
| ✅ **Tyrese Maxey** | `Active/BN` | Healthy | `0.86` | Expected to play |
| ✅ **Ayo Dosunmu** | `Active/BN` | Healthy | `0.86` | Expected to play |
| ✅ **James Harden** | `Active/BN` | Healthy | `0.88` | Expected to play |
| ✅ **Desmond Bane** | `Active/BN` | Healthy | `0.92` | Expected to play |
| ❌ **Kawhi Leonard** | `⚠️ Move to IL+` | **OUT** | `0.00` | Leonard is out for Sunday's game against the Timberwolves due to left knee swelling, Blake Murphy of Sportsnet.ca reports. |
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
| #1 | `ADD / DROP` | **Nikola Vučević** | Kawhi Leonard | `0.6 / 0.6` | **`+0.172`** | REB (+6.7%), PTS (+5.7%) |
| #2 | `ADD / DROP` | **Kyle Filipowski** | Kawhi Leonard | `0.6 / 0.6` | **`+0.158`** | REB (+7.2%), PTS (+5.3%) |
| #3 | `ADD / DROP` | **Nickeil Alexander-Walker** | Kawhi Leonard | `0.6 / 0.6` | **`+0.150`** | PTS (+6.4%), FG3M (+6.2%) |
| #4 | `ADD / DROP` | **Brice Sensabaugh** | Kawhi Leonard | `0.6 / 0.6` | **`+0.122`** | PTS (+5.1%), FG3M (+4.4%) |
| #5 | `ADD / DROP` | **De'Andre Hunter** | Kawhi Leonard | `0.6 / 0.6` | **`+0.120`** | PTS (+5.8%), FG3M (+3.7%) |

### 📋 Available Healthy Free Agents Pool (Top 8)
| Rank | Free Agent | Source | Exp Min (Boost) | Base Z | Eff Availability |
| :---: | :--- | :---: | :---: | :---: | :---: |
| #1 | **Nickeil Alexander-Walker** | `🔥 Dropped by Team` | `30.6m` | `1.76` | `0.91` |
| #2 | **Nikola Vučević** | `🔥 Dropped by Team` | `28.7m (+2.8m)` | `1.25` | `0.85` |
| #3 | **Kyle Filipowski** | `Unrostered FA` | `28.8m (+5.4m)` | `0.59` | `0.90` |
| #4 | **Jay Huff** | `🔥 Dropped by Team` | `21.5m (+2.1m)` | `-0.14` | `0.92` |
| #5 | **Reed Sheppard** | `🔥 Dropped by Team` | `23.9m (+0.7m)` | `-0.34` | `0.92` |
| #6 | **Kevin Huerter** | `Unrostered FA` | `30.1m (+7.5m)` | `-0.37` | `0.86` |
| #7 | **Moussa Diabaté** | `🔥 Dropped by Team` | `28.8m (+4.8m)` | `-0.47` | `0.88` |
| #8 | **Kevin Porter Jr.** | `🔥 Dropped by Team` | `26.9m` | `-0.79` | `0.83` |

---

## 4. ⚔️ Live Matchup Scoreboard & Updated Projections: Berk's Best Team vs SILE BULLS
* **IL+ Stash:** `Brandon Ingram`
* **Top Auto-Streamer:** `Nickeil Alexander-Walker`
* **Remaining Games Multiplier:** `Berk: 19% remaining | SILE BULLS: 17% remaining`
* **Expected Matchup Outcome:** **5.99 - 3.01** | **Matchup Win Prob $P(\ge 5\text{ cats})$:** **`%93.4`** (Berk favori)

| Category | Live Score | Berk Proj Final | SILE BULLS Proj Final | Berk Win Prob | Projected Winner |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **PTS** | `420 - 437` | `521.4` | `529.3` | `%43.3` | SILE BULLS |
| **REB** | `147 - 164` | `184.6` | `195.1` | `%29.3` | SILE BULLS |
| **AST** | `70 - 103` | `92.2` | `126.3` | `%0.3` | SILE BULLS |
| **STL** | `41 - 28` | `47.8` | `34.6` | `%99.7` | 🏆 Berk |
| **BLK** | `30 - 24` | `34.3` | `27.8` | `%95.6` | 🏆 Berk |
| **FG3M** | `44 - 41` | `54.9` | `51.8` | `%66.6` | 🏆 Berk |
| **TOV** | `43 - 80` | `54.0` | `91.2` | `%100.0` | 🏆 Berk |
| **FG%** | `.459 - .452` | `.464` | `.455` | `%69.3` | 🏆 Berk |
| **FT%** | `.811 - .770` | `.811` | `.775` | `%95.1` | 🏆 Berk |
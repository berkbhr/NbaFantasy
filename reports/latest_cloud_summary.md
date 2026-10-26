# 🏀 NBA Fantasy Autonomous Cloud Sync Report
**Sync Timestamp:** `2026-10-26 08:30:21 UTC`  
**Official NBA Ingestion:** `https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-10-26_04_30AM.pdf`  
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
| ⚠️ **Jaxson Hayes** | `Active/BN` | **HEALTHY** | `0.85` | Expected to play |
| ⚠️ **Jarrett Allen** | `Active/BN` | **HEALTHY** | `0.85` | Expected to play |
| ✅ **Julian Champagnie** | `Active/BN` | Healthy | `0.92` | Expected to play |
| ✅ **Neemias Queta** | `Active/BN` | Healthy | `0.90` | Expected to play |
| ✅ **Desmond Bane** | `Active/BN` | Healthy | `0.92` | Expected to play |
| ❌ **Kawhi Leonard** | `⚠️ Move to IL+` | **OUT** | `0.00` | Leonard is out for Sunday's game against the Timberwolves due to left knee swelling, Blake Murphy of Sportsnet.ca reports. |
| ✅ **Precious Achiuwa** | `Active/BN` | Healthy | `0.88` | Expected to play |
| ❌ **Brandon Ingram** | `IL+` | **OUT** | `0.00` | Ingram won't be ready for the start of the season due to a partially torn Achilles, per Joey Linn of SI.com. |

### 🔍 League-Wide IL+ Stashes & Open Roster Slots
| Slot & Team | Players in IL/IL+ | Injured in Active/BN (Needs IL) | Empty Active Roster Spots |
| :--- | :--- | :--- | :---: |
| **#1 MuCa Tandır** | Kon Knueppel | Naji Marshall (O) | `0` |
| **#2 Mordor Tulums** | Cameron Johnson, Tobias Harris | — | `0` |
| **#4 Houston Buckets** | — | Keegan Murray (O), Nic Claxton (O) | `0` |
| **#6 abu dhabi camels** | — | AJ Dybantsa (O), Joel Embiid (O) | `0` |
| **#7 Samurai Strikers** | Mark Williams | Ausar Thompson (O) | `0` |
| **#8 Berk's Best Team** | Brandon Ingram | Kawhi Leonard (O) | `0` |
| **#9 FatihTerimSpor** | Jalen Duren, Paolo Banchero | — | `0` |
| **#10 Redeem Team** | Draymond Green, Fred VanVleet | — | `0` |
| **#11 Fikirtepe Warriors** | Jusuf Nurkić, Coby White | Cooper Flagg (O) | `0` |
| **#12 Istanbul Brickmakers** | Zach Edey, Yves Missi | Kristaps Porziņģis (O) | `0` |
| **#13 SILE BULLS** | Jimmy Butler III | VJ Edgecombe (O) | `0` |

---

## 2. 🔄 Recent League Transactions (Who Added / Dropped Whom)
| Transaction | Team | Added Player(s) | Dropped Player(s) |
| :---: | :--- | :--- | :--- |
| `ADD/DROP` | **Samurai Strikers** | ➕ **Jay Huff** | ➖ Miles McBride |
| `ADD/DROP` | **Kuvâ-yi Milfiye** | ➕ **Alex Caruso** | ➖ Ziaire Williams |
| `ADD/DROP` | **Samurai Strikers** | ➕ **Jeremiah Fears** | — |
| `ADD/DROP` | **FatihTerimSpor** | ➕ **Kyle Kuzma** | ➖ Ryan Kalkbrenner |
| `ADD/DROP` | **Kuvâ-yi Milfiye** | ➕ **Ziaire Williams** | — |
| `ADD/DROP` | **Redeem Team** | ➕ **Marcus Smart** | — |
| `ADD/DROP` | **Samurai Strikers** | ➕ **Miles McBride** | — |
| `ADD/DROP` | **MuCa Tandırs** | ➕ **Derrick Jones Jr.** | ➖ Herbert Jones |
| `ADD/DROP` | **Istanbul Brickmakers 🧱** | ➕ **Khaman Maluach** | — |
| `ADD/DROP` | **Kuvâ-yi Milfiye** | ➕ **Moussa Diabaté** | — |
| `ADD/DROP` | **Kuvâ-yi Milfiye** | ➕ **Gui Santos** | — |
| `ADD/DROP` | **YearOne Tyrants** | ➕ **Tristan da Silva** | ➖ Scoot Henderson |

---

## 3. 🎯 Dynamic Add/Drop Recommendations (Remaining Games & Live Scoreboard Weighted)
Optimized via $\Delta \sum_{c=1}^{9} \Phi_c$ conditioned on live category margins and remaining games this week:

| Rank | Action | Add Target (FA) | Drop Candidate | Rem Games (Add/Drop) | $\Delta E[\text{Wins}]$ | Key Category Gains |
| :---: | :---: | :--- | :--- | :---: | :---: | :--- |
| #1 | `ADD / DROP` | **Moussa Diabaté** | Kawhi Leonard | `4.0 / 3.0` | **`+0.514`** | REB (+22.0%), STL (+12.5%) |
| #2 | `ADD / DROP` | **Nickeil Alexander-Walker** | Kawhi Leonard | `4.0 / 3.0` | **`+0.488`** | PTS (+14.7%), STL (+13.0%) |
| #3 | `ADD / DROP` | **Ryan Kalkbrenner** | Kawhi Leonard | `4.0 / 3.0` | **`+0.432`** | BLK (+15.6%), REB (+14.4%) |
| #4 | `ADD / DROP` | **Dean Wade** | Kawhi Leonard | `3.0 / 3.0` | **`+0.431`** | STL (+14.8%), REB (+10.7%) |
| #5 | `ADD / DROP` | **Ziaire Williams** | Kawhi Leonard | `4.0 / 3.0` | **`+0.397`** | STL (+14.1%), PTS (+10.2%) |

### 📋 Available Healthy Free Agents Pool (Top 8)
| Rank | Free Agent | Source | Exp Min (Boost) | Base Z | Eff Availability |
| :---: | :--- | :---: | :---: | :---: | :---: |
| #1 | **Nickeil Alexander-Walker** | `🔥 Dropped by Team` | `30.1m` | `1.58` | `0.91` |
| #2 | **Dean Wade** | `Unrostered FA` | `34.6m (+5.7m)` | `0.78` | `0.81` |
| #3 | **Reed Sheppard** | `🔥 Dropped by Team` | `23.5m` | `-1.18` | `0.92` |
| #4 | **Moussa Diabaté** | `🔥 Dropped by Team` | `25.6m (+0.8m)` | `-1.57` | `0.88` |
| #5 | **Max Christie** | `Unrostered FA` | `33.9m (+4.7m)` | `-1.87` | `0.90` |
| #6 | **Justin Champagnie** | `Unrostered FA` | `22.3m` | `-1.97` | `0.86` |
| #7 | **Ja'Kobe Walter** | `Unrostered FA` | `25.2m (+1.3m)` | `-2.10` | `0.88` |
| #8 | **Kevin Huerter** | `Unrostered FA` | `27.4m (+5.4m)` | `-2.31` | `0.86` |

---

## 4. ⚔️ Live Matchup Scoreboard & Updated Projections: Berk's Best Team vs Mordor Tulums
* **IL+ Stash:** `Brandon Ingram`
* **Top Auto-Streamer:** `Nickeil Alexander-Walker`
* **Remaining Games Multiplier:** `Berk: 100% remaining | Mordor Tulums: 100% remaining`
* **Expected Matchup Outcome:** **3.97 - 5.03** | **Matchup Win Prob $P(\ge 5\text{ cats})$:** **`%35.4`** (Mordor Tulums favori)

| Category | Live Score | Berk Proj Final | Mordor Tulums Proj Final | Berk Win Prob | Projected Winner |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **PTS** | `0 - 0` | `576.8` | `620.2` | `%36.3` | Mordor Tulums |
| **REB** | `0 - 0` | `214.9` | `222.8` | `%43.7` | Mordor Tulums |
| **AST** | `0 - 0` | `120.7` | `101.8` | `%75.6` | 🏆 Berk |
| **STL** | `0 - 0` | `40.4` | `38.3` | `%57.1` | 🏆 Berk |
| **BLK** | `0 - 0` | `27.5` | `32.8` | `%31.2` | Mordor Tulums |
| **FG3M** | `0 - 0` | `60.7` | `77.1` | `%19.7` | Mordor Tulums |
| **TOV** | `0 - 0` | `61.9` | `59.9` | `%45.2` | Mordor Tulums |
| **FG%** | `.488 - .491` | `.488` | `.491` | `%46.9` | Mordor Tulums |
| **FT%** | `.797 - .810` | `.797` | `.810` | `%41.3` | Mordor Tulums |
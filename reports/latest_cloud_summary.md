# 🏀 NBA Fantasy Autonomous Cloud Sync Report
**Sync Timestamp:** `2026-10-26 18:47:35 UTC`  
**Official NBA Ingestion:** `https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-10-26_02_45PM.pdf`  
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
| #1 | `ADD / DROP` | **Nickeil Alexander-Walker** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.289`** | FG3M (+10.6%), PTS (+10.0%) |
| #2 | `ADD / DROP` | **Moussa Diabaté** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.210`** | REB (+15.3%), FG_PCT (+6.2%) |
| #3 | `ADD / DROP` | **Ryan Kalkbrenner** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.147`** | BLK (+10.2%), REB (+6.7%) |
| #4 | `ADD / DROP` | **Ziaire Williams** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.093`** | FG3M (+3.1%), STL (+3.1%) |
| #5 | `ADD / DROP` | **Sam Merrill** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.073`** | FG3M (+5.7%), PTS (+2.3%) |
| #6 | `ADD / DROP` | **Jake LaRavia** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.054`** | STL (+2.5%), REB (+1.6%) |
| #7 | `ADD / DROP` | **Royce O'Neale** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.042`** | FG3M (+4.1%), REB (+1.6%) |
| #8 | `ADD / DROP` | **Luguentz Dort** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.040`** | FG3M (+3.6%), REB (+1.4%) |
| #9 | `ADD / DROP` | **Dean Wade** | Bilal Coulibaly | `3.0 / 3.0` | **`+0.039`** | TOV (+4.8%), STL (+3.1%) |
| #10 | `ADD / DROP` | **Jarace Walker** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.036`** | REB (+4.7%), FG3M (+2.8%) |
| #11 | `ADD / DROP` | **Justin Champagnie** | Bilal Coulibaly | `3.0 / 3.0` | **`+0.023`** | REB (+2.9%), TOV (+2.4%) |
| #12 | `ADD / DROP` | **Max Christie** | Bilal Coulibaly | `3.0 / 3.0` | **`+0.015`** | FG3M (+3.2%), FT_PCT (+1.6%) |

### 📋 Available Healthy Free Agents Pool (Top 8)
| Rank | Free Agent | Source | Exp Min (Boost) | Base Z | Eff Availability |
| :---: | :--- | :---: | :---: | :---: | :---: |
| #1 | **Nickeil Alexander-Walker** | `🔥 Dropped by Team` | `30.1m` | `1.54` | `0.91` |
| #2 | **Moussa Diabaté** | `🔥 Dropped by Team` | `27.4m (+2.6m)` | `-0.82` | `0.88` |
| #3 | **Dean Wade** | `Unrostered FA` | `29.0m` | `-1.33` | `0.81` |
| #4 | **Justin Champagnie** | `Unrostered FA` | `22.3m` | `-2.00` | `0.86` |
| #5 | **Max Christie** | `Unrostered FA` | `32.6m (+3.4m)` | `-2.27` | `0.90` |
| #6 | **Ryan Kalkbrenner** | `Unrostered FA` | `21.6m (+2.1m)` | `-2.44` | `0.86` |
| #7 | **Ziaire Williams** | `Unrostered FA` | `26.0m` | `-2.84` | `0.82` |
| #8 | **Jordan Goodwin** | `Unrostered FA` | `21.9m (+0.6m)` | `-2.93` | `0.87` |

---

## 4. ⚔️ Live Matchup Scoreboard & Updated Projections: Berk's Best Team vs Mordor Tulums
* **IL+ Stash:** `Brandon Ingram`
* **Top Auto-Streamer:** `Nickeil Alexander-Walker`
* **Remaining Games Multiplier:** `Berk: 100% remaining | Mordor Tulums: 100% remaining`
* **Expected Matchup Outcome:** **4.41 - 4.59** | **Matchup Win Prob $P(\ge 5\text{ cats})$:** **`%47.6`** (Mordor Tulums favori)

| Category | Live Score | Berk Proj Final | Mordor Tulums Proj Final | Berk Win Prob | Projected Winner |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **PTS** | `0 - 0` | `618.9` | `610.2` | `%52.7` | 🏆 Berk |
| **REB** | `0 - 0` | `225.8` | `230.6` | `%46.3` | Mordor Tulums |
| **AST** | `0 - 0` | `126.8` | `104.2` | `%79.1` | 🏆 Berk |
| **STL** | `0 - 0` | `43.4` | `40.4` | `%59.7` | 🏆 Berk |
| **BLK** | `0 - 0` | `28.3` | `30.9` | `%40.6` | Mordor Tulums |
| **FG3M** | `0 - 0` | `64.9` | `75.0` | `%30.5` | Mordor Tulums |
| **TOV** | `0 - 0` | `65.4` | `60.2` | `%37.9` | Mordor Tulums |
| **FG%** | `.488 - .492` | `.488` | `.492` | `%45.3` | Mordor Tulums |
| **FT%** | `.802 - .803` | `.802` | `.803` | `%49.3` | Mordor Tulums |
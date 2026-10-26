# 🏀 NBA Fantasy Autonomous Cloud Sync Report
**Sync Timestamp:** `2026-10-26 17:41:58 UTC`  
**Official NBA Ingestion:** `https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-10-26_01_30PM.pdf`  
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
| #1 | `ADD / DROP` | **Nickeil Alexander-Walker** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.276`** | FG3M (+9.9%), PTS (+9.9%) |
| #2 | `ADD / DROP` | **Moussa Diabaté** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.209`** | REB (+15.4%), FG_PCT (+6.2%) |
| #3 | `ADD / DROP` | **Ryan Kalkbrenner** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.145`** | BLK (+9.5%), REB (+6.8%) |
| #4 | `ADD / DROP` | **Ziaire Williams** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.091`** | STL (+3.0%), FG3M (+2.9%) |
| #5 | `ADD / DROP` | **Sam Merrill** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.071`** | FG3M (+5.3%), PTS (+2.2%) |
| #6 | `ADD / DROP` | **Jake LaRavia** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.054`** | STL (+2.5%), REB (+1.6%) |
| #7 | `ADD / DROP` | **Jock Landale** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.042`** | REB (+4.6%), FG_PCT (+3.0%) |
| #8 | `ADD / DROP` | **Royce O'Neale** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.041`** | FG3M (+3.7%), REB (+1.6%) |
| #9 | `ADD / DROP` | **Luguentz Dort** | Bilal Coulibaly | `4.0 / 3.0` | **`+0.039`** | FG3M (+3.4%), REB (+1.5%) |
| #10 | `ADD / DROP` | **Dean Wade** | Bilal Coulibaly | `3.0 / 3.0` | **`+0.039`** | TOV (+4.8%), STL (+3.1%) |
| #11 | `ADD / DROP` | **Justin Champagnie** | Bilal Coulibaly | `3.0 / 3.0` | **`+0.026`** | REB (+2.9%), TOV (+2.4%) |
| #12 | `ADD / DROP` | **Max Christie** | Bilal Coulibaly | `3.0 / 3.0` | **`+0.014`** | FG3M (+3.0%), FT_PCT (+1.6%) |

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
| #8 | **Jordan Goodwin** | `Unrostered FA` | `21.9m (+0.6m)` | `-2.94` | `0.87` |

---

## 4. ⚔️ Live Matchup Scoreboard & Updated Projections: Berk's Best Team vs Mordor Tulums
* **IL+ Stash:** `Brandon Ingram`
* **Top Auto-Streamer:** `Nickeil Alexander-Walker`
* **Remaining Games Multiplier:** `Berk: 100% remaining | Mordor Tulums: 100% remaining`
* **Expected Matchup Outcome:** **4.41 - 4.59** | **Matchup Win Prob $P(\ge 5\text{ cats})$:** **`%47.6`** (Mordor Tulums favori)

| Category | Live Score | Berk Proj Final | Mordor Tulums Proj Final | Berk Win Prob | Projected Winner |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **PTS** | `0 - 0` | `618.9` | `616.9` | `%50.6` | ⚖️ Toss-up |
| **REB** | `0 - 0` | `225.8` | `222.9` | `%52.3` | 🏆 Berk |
| **AST** | `0 - 0` | `126.8` | `101.1` | `%82.3` | 🏆 Berk |
| **STL** | `0 - 0` | `43.4` | `38.2` | `%66.8` | 🏆 Berk |
| **BLK** | `0 - 0` | `28.3` | `32.9` | `%33.6` | Mordor Tulums |
| **FG3M** | `0 - 0` | `64.9` | `76.7` | `%27.5` | Mordor Tulums |
| **TOV** | `0 - 0` | `65.4` | `59.7` | `%36.8` | Mordor Tulums |
| **FG%** | `.488 - .491` | `.488` | `.491` | `%46.8` | Mordor Tulums |
| **FT%** | `.802 - .810` | `.802` | `.810` | `%44.7` | Mordor Tulums |
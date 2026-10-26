# 🏀 NBA Fantasy Autonomous Cloud Sync Report
**Sync Timestamp:** `2026-10-26 11:39:56 UTC`  
**Official NBA Ingestion:** `https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-10-26_07_30AM.pdf`  
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
| ❌ **Kawhi Leonard** | `IL+` | **OUT** | `0.00` | Leonard is out for Sunday's game against the Timberwolves due to left knee swelling, Blake Murphy of Sportsnet.ca reports. |
| ❌ **Brandon Ingram** | `IL+` | **OUT** | `0.00` | Ingram won't be ready for the start of the season due to a partially torn Achilles, per Joey Linn of SI.com. |

### 🔍 League-Wide IL+ Stashes & Open Roster Slots
| Slot & Team | Players in IL/IL+ | Injured in Active/BN (Needs IL) | Empty Active Roster Spots |
| :--- | :--- | :--- | :---: |
| **#1 MuCa Tandır** | Naji Marshall, Kon Knueppel | — | `0` |
| **#2 Mordor Tulums** | Cameron Johnson, Tobias Harris | — | `0` |
| **#4 Houston Buckets** | — | Keegan Murray (O), Nic Claxton (O) | `0` |
| **#6 abu dhabi camels** | — | AJ Dybantsa (O), Joel Embiid (O) | `0` |
| **#7 Samurai Strikers** | Mark Williams | Ausar Thompson (O) | `0` |
| **#8 Berk's Best Team** | Kawhi Leonard, Brandon Ingram | — | `0` |
| **#9 FatihTerimSpor** | Jalen Duren, Paolo Banchero | — | `0` |
| **#10 Redeem Team** | Draymond Green, Fred VanVleet | — | `0` |
| **#11 Fikirtepe Warriors** | Jusuf Nurkić, Coby White | Cooper Flagg (O) | `0` |
| **#12 Istanbul Brickmakers** | Kristaps Porziņģis, Yves Missi | Zach Edey (O) | `0` |
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
| #1 | `ADD (Boş Yuva / IL+)` | **Moussa Diabaté** | Boş Yuva (IL+ Boş Yuva) | `4.0 / 0.0` | **`+0.511`** | REB (+21.8%), STL (+12.3%) |
| #2 | `ADD (Boş Yuva / IL+)` | **Dean Wade** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.445`** | STL (+14.6%), REB (+10.6%) |
| #3 | `ADD (Boş Yuva / IL+)` | **Ryan Kalkbrenner** | Boş Yuva (IL+ Boş Yuva) | `4.0 / 0.0` | **`+0.434`** | BLK (+15.3%), REB (+14.2%) |
| #4 | `ADD (Boş Yuva / IL+)` | **Ziaire Williams** | Boş Yuva (IL+ Boş Yuva) | `4.0 / 0.0` | **`+0.423`** | STL (+13.9%), PTS (+11.9%) |
| #5 | `ADD (Boş Yuva / IL+)` | **Justin Champagnie** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.363`** | REB (+12.4%), STL (+7.9%) |
| #6 | `ADD (Boş Yuva / IL+)` | **Jake LaRavia** | Boş Yuva (IL+ Boş Yuva) | `4.0 / 0.0` | **`+0.360`** | STL (+13.2%), REB (+9.2%) |
| #7 | `ADD (Boş Yuva / IL+)` | **Kevin Huerter** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.348`** | PTS (+9.6%), STL (+9.3%) |
| #8 | `ADD (Boş Yuva / IL+)` | **Jock Landale** | Boş Yuva (IL+ Boş Yuva) | `4.0 / 0.0` | **`+0.345`** | REB (+13.1%), PTS (+9.4%) |
| #9 | `ADD (Boş Yuva / IL+)` | **Royce O'Neale** | Boş Yuva (IL+ Boş Yuva) | `4.0 / 0.0` | **`+0.336`** | FG3M (+9.2%), STL (+8.9%) |
| #10 | `ADD (Boş Yuva / IL+)` | **Sam Merrill** | Boş Yuva (IL+ Boş Yuva) | `4.0 / 0.0` | **`+0.292`** | FG3M (+8.8%), PTS (+8.3%) |
| #11 | `ADD (Boş Yuva / IL+)` | **Luguentz Dort** | Boş Yuva (IL+ Boş Yuva) | `4.0 / 0.0` | **`+0.260`** | STL (+7.9%), PTS (+6.9%) |
| #12 | `ADD (Boş Yuva / IL+)` | **Max Christie** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.132`** | FG3M (+4.8%), PTS (+4.7%) |

### 📋 Available Healthy Free Agents Pool (Top 8)
| Rank | Free Agent | Source | Exp Min (Boost) | Base Z | Eff Availability |
| :---: | :--- | :---: | :---: | :---: | :---: |
| #1 | **Dean Wade** | `Unrostered FA` | `34.6m (+5.7m)` | `0.77` | `0.81` |
| #2 | **Moussa Diabaté** | `🔥 Dropped by Team` | `25.6m (+0.8m)` | `-1.58` | `0.88` |
| #3 | **Max Christie** | `Unrostered FA` | `33.9m (+4.7m)` | `-1.92` | `0.90` |
| #4 | **Justin Champagnie** | `Unrostered FA` | `22.3m` | `-2.00` | `0.86` |
| #5 | **Kevin Huerter** | `Unrostered FA` | `27.4m (+5.4m)` | `-2.34` | `0.86` |
| #6 | **Kentavious Caldwell-Pope** | `Unrostered FA` | `30.4m (+5.2m)` | `-2.66` | `0.83` |
| #7 | **Ziaire Williams** | `Unrostered FA` | `26.0m` | `-2.84` | `0.82` |
| #8 | **Jordan Goodwin** | `Unrostered FA` | `21.9m (+0.6m)` | `-2.94` | `0.87` |

---

## 4. ⚔️ Live Matchup Scoreboard & Updated Projections: Berk's Best Team vs Mordor Tulums
* **IL+ Stash:** `Kawhi Leonard, Brandon Ingram`
* **Top Auto-Streamer:** `Dean Wade, Moussa Diabaté`
* **Remaining Games Multiplier:** `Berk: 100% remaining | Mordor Tulums: 100% remaining`
* **Expected Matchup Outcome:** **4.48 - 4.52** | **Matchup Win Prob $P(\ge 5\text{ cats})$:** **`%49.3`** (Mordor Tulums favori)

| Category | Live Score | Berk Proj Final | Mordor Tulums Proj Final | Berk Win Prob | Projected Winner |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **PTS** | `0 - 0` | `568.9` | `578.0` | `%47.0` | Mordor Tulums |
| **REB** | `0 - 0` | `242.9` | `223.9` | `%64.1` | 🏆 Berk |
| **AST** | `0 - 0` | `120.9` | `93.1` | `%84.9` | 🏆 Berk |
| **STL** | `0 - 0` | `44.1` | `38.2` | `%68.5` | 🏆 Berk |
| **BLK** | `0 - 0` | `30.1` | `33.3` | `%38.9` | Mordor Tulums |
| **FG3M** | `0 - 0` | `56.7` | `71.1` | `%22.1` | Mordor Tulums |
| **TOV** | `0 - 0` | `61.4` | `54.5` | `%33.4` | Mordor Tulums |
| **FG%** | `.493 - .494` | `.493` | `.494` | `%49.2` | Mordor Tulums |
| **FT%** | `.784 - .801` | `.784` | `.801` | `%39.5` | Mordor Tulums |
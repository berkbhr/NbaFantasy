# 🏀 NBA Fantasy Autonomous Cloud Sync Report
**Sync Timestamp:** `2026-10-27 02:05:03 UTC`  
**Official NBA Ingestion:** `https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-10-26_10_00PM.pdf`  
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
| ❌ **Jaxson Hayes** | `⚠️ Move to IL+` | **OUT** | `0.00` | Hayes (shoulder) is out for Monday's game against the Grizzlies. |
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
| **#1 MuCa Tandır** | Naji Marshall, Kon Knueppel | Cason Wallace (O) | `0` |
| **#2 Mordor Tulums** | Chet Holmgren, Tobias Harris | — | `0` |
| **#3 Philadelphia Sikers** | — | Ivica Zubac (O) | `0` |
| **#4 Houston Buckets** | — | Jalen Williams (O), Keegan Murray (O), Nic Claxton (O) | `0` |
| **#6 abu dhabi camels** | AJ Dybantsa | — | `0` |
| **#7 Samurai Strikers** | Mark Williams | — | `0` |
| **#8 Berk's Best Team** | Brandon Ingram | — | `0` |
| **#9 FatihTerimSpor** | Jalen Duren, Paolo Banchero | — | `0` |
| **#11 Fikirtepe Warriors** | Jusuf Nurkić, Coby White | — | `0` |
| **#12 Istanbul Brickmakers** | Kristaps Porziņģis, Yves Missi | — | `0` |
| **#13 SILE BULLS** | VJ Edgecombe, Jimmy Butler III | — | `0` |
| **#14 YearOne Tyrants** | Jalen Suggs | — | `0` |

---

## 2. 🔄 Recent League Transactions (Who Added / Dropped Whom)
| Transaction | Team | Added Player(s) | Dropped Player(s) |
| :---: | :--- | :--- | :--- |
| `ADD/DROP` | **abu dhabi camels** | ➕ **Luke Kennard** | — |
| `ADD/DROP` | **YearOne Tyrants** | ➕ **Justin Champagnie** | — |
| `ADD/DROP` | **Fikirtepe Warriors** | ➕ **Daniss Jenkins** | ➖ Egor Dëmin |
| `ADD/DROP` | **SILE BULLS** | ➕ **Ja'Kobe Walter** | — |
| `ADD/DROP` | **FatihTerimSpor** | ➕ **Trevon Brazile** | ➖ Noah Clowney |
| `ADD/DROP` | **MuCa Tandırs** | ➕ **Reed Sheppard** | — |
| `ADD/DROP` | **Samurai Strikers** | ➕ **Jay Huff** | ➖ Miles McBride |
| `ADD/DROP` | **Kuvâ-yi Milfiye** | ➕ **Alex Caruso** | ➖ Ziaire Williams |
| `ADD/DROP` | **Samurai Strikers** | ➕ **Jeremiah Fears** | — |
| `ADD/DROP` | **FatihTerimSpor** | ➕ **Kyle Kuzma** | ➖ Ryan Kalkbrenner |
| `ADD/DROP` | **Kuvâ-yi Milfiye** | ➕ **Ziaire Williams** | — |
| `ADD/DROP` | **Redeem Team** | ➕ **Marcus Smart** | — |

---

## 3. 🎯 Dynamic Add/Drop Recommendations (Remaining Games & Live Scoreboard Weighted)
Optimized via $\Delta \sum_{c=1}^{9} \Phi_c$ conditioned on live category margins and remaining games this week:

| Rank | Action | Add Target (FA) | Drop Candidate | Rem Games (Add/Drop) | $\Delta E[\text{Wins}]$ | Key Category Gains |
| :---: | :---: | :--- | :--- | :---: | :---: | :--- |
| #1 | `ADD (Boş Yuva / IL+)` | **Dean Wade** | Boş Yuva (Jaxson Hayes IL+'a) | `3.0 / 0.0` | **`+0.387`** | STL (%48 ➔ %60), PTS (%47 ➔ %53) |
| #2 | `ADD (Boş Yuva / IL+)` | **Jock Landale** | Boş Yuva (Jaxson Hayes IL+'a) | `4.0 / 0.0` | **`+0.357`** | PTS (%47 ➔ %57), STL (%48 ➔ %53) |
| #3 | `ADD (Boş Yuva / IL+)` | **Sam Merrill** | Boş Yuva (Jaxson Hayes IL+'a) | `4.0 / 0.0` | **`+0.314`** | PTS (%47 ➔ %56), STL (%48 ➔ %54) |
| #4 | `ADD (Boş Yuva / IL+)` | **Gui Santos** | Boş Yuva (Jaxson Hayes IL+'a) | `4.0 / 0.0` | **`+0.295`** | PTS (%47 ➔ %55), STL (%48 ➔ %55) |
| #5 | `ADD (Boş Yuva / IL+)` | **Jarace Walker** | Boş Yuva (Jaxson Hayes IL+'a) | `4.0 / 0.0` | **`+0.288`** | PTS (%47 ➔ %56), STL (%48 ➔ %55) |
| #6 | `ADD (Boş Yuva / IL+)` | **Luguentz Dort** | Boş Yuva (Jaxson Hayes IL+'a) | `4.0 / 0.0` | **`+0.283`** | STL (%48 ➔ %55), PTS (%47 ➔ %54) |
| #7 | `ADD (Boş Yuva / IL+)` | **Jake LaRavia** | Boş Yuva (Jaxson Hayes IL+'a) | `4.0 / 0.0` | **`+0.280`** | STL (%48 ➔ %57), PTS (%47 ➔ %53) |
| #8 | `ADD (Boş Yuva / IL+)` | **Royce O'Neale** | Boş Yuva (Jaxson Hayes IL+'a) | `4.0 / 0.0` | **`+0.272`** | STL (%48 ➔ %54), PTS (%47 ➔ %53) |
| #9 | `ADD (Boş Yuva / IL+)` | **Moussa Diabaté** | Boş Yuva (Jaxson Hayes IL+'a) | `3.0 / 0.0` | **`+0.254`** | STL (%48 ➔ %54), REB (%34 ➔ %47) |
| #10 | `ADD (Boş Yuva / IL+)` | **Kevin Huerter** | Boş Yuva (Jaxson Hayes IL+'a) | `3.0 / 0.0` | **`+0.231`** | PTS (%47 ➔ %53), STL (%48 ➔ %54) |
| #11 | `ADD (Boş Yuva / IL+)` | **Ziaire Williams** | Boş Yuva (Jaxson Hayes IL+'a) | `3.0 / 0.0` | **`+0.222`** | STL (%48 ➔ %55), PTS (%47 ➔ %53) |
| #12 | `ADD (Boş Yuva / IL+)` | **Keldon Johnson** | Boş Yuva (Jaxson Hayes IL+'a) | `3.0 / 0.0` | **`+0.220`** | PTS (%47 ➔ %54), STL (%48 ➔ %52) |
| #13 | `ADD (Boş Yuva / IL+)` | **Jordan Poole** | Boş Yuva (Jaxson Hayes IL+'a) | `3.0 / 0.0` | **`+0.218`** | PTS (%47 ➔ %55), STL (%48 ➔ %53) |
| #14 | `ADD (Boş Yuva / IL+)` | **Gary Payton II** | Boş Yuva (Jaxson Hayes IL+'a) | `4.0 / 0.0` | **`+0.167`** | STL (%48 ➔ %52), PTS (%47 ➔ %52) |
| #15 | `ADD (Boş Yuva / IL+)` | **Max Christie** | Boş Yuva (Jaxson Hayes IL+'a) | `3.0 / 0.0` | **`+0.136`** | PTS (%47 ➔ %52), FT_PCT (%56 ➔ %58) |

### 📋 Available Healthy Free Agents Pool (Top 8)
| Rank | Free Agent | Source | Exp Min (Boost) | Base Z | Eff Availability |
| :---: | :--- | :---: | :---: | :---: | :---: |
| #1 | **Dean Wade** | `Unrostered FA` | `29.0m` | `-1.33` | `0.81` |
| #2 | **Moussa Diabaté** | `🔥 Dropped by Team` | `25.6m (+0.8m)` | `-1.58` | `0.88` |
| #3 | **Max Christie** | `Unrostered FA` | `32.3m (+3.0m)` | `-2.37` | `0.90` |
| #4 | **Ziaire Williams** | `Unrostered FA` | `26.0m` | `-2.84` | `0.82` |
| #5 | **Jordan Goodwin** | `Unrostered FA` | `21.9m (+0.6m)` | `-2.93` | `0.87` |
| #6 | **Kevin Huerter** | `Unrostered FA` | `25.6m (+3.7m)` | `-2.96` | `0.86` |
| #7 | **Malik Beasley** | `Unrostered FA` | `26.7m` | `-3.17` | `0.82` |
| #8 | **Keldon Johnson** | `Unrostered FA` | `22.3m` | `-3.23` | `0.92` |

---

## 4. ⚔️ Live Matchup Scoreboard & Updated Projections: Berk's Best Team vs Mordor Tulums
* **IL+ Stash:** `Brandon Ingram, Jaxson Hayes`
* **Top Auto-Streamer:** `Dean Wade, Moussa Diabaté`
* **Remaining Games Multiplier:** `Berk: 100% remaining | Mordor Tulums: 100% remaining`
* **Expected Matchup Outcome:** **4.73 - 4.27** | **Matchup Win Prob $P(\ge 5\text{ cats})$:** **`%56.6`** (Berk favori)

| Category | Live Score | Berk Proj Final | Mordor Tulums Proj Final | Berk Win Prob | Projected Winner |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **PTS** | `0 - 0` | `578.2` | `550.4` | `%59.0` | 🏆 Berk |
| **REB** | `0 - 0` | `239.7` | `224.7` | `%61.2` | 🏆 Berk |
| **AST** | `0 - 0` | `121.9` | `91.9` | `%86.8` | 🏆 Berk |
| **STL** | `0 - 0` | `44.4` | `38.7` | `%67.9` | 🏆 Berk |
| **BLK** | `0 - 0` | `28.6` | `30.5` | `%42.9` | Mordor Tulums |
| **FG3M** | `0 - 0` | `58.6` | `66.5` | `%33.5` | Mordor Tulums |
| **TOV** | `0 - 0` | `62.4` | `53.4` | `%28.8` | Mordor Tulums |
| **FG%** | `.490 - .496` | `.490` | `.496` | `%43.7` | Mordor Tulums |
| **FT%** | `.792 - .793` | `.792` | `.793` | `%49.5` | Mordor Tulums |
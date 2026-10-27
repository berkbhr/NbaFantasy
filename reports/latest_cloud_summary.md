# 🏀 NBA Fantasy Autonomous Cloud Sync Report
**Sync Timestamp:** `2026-10-27 06:20:43 UTC`  
**Official NBA Ingestion:** `https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-10-27_02_15AM.pdf`  
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
| ⚠️ **Jaxson Hayes** | `Active/BN` | **QUESTIONABLE** | `0.52` | Hayes (shoulder) is out for Monday's game against the Grizzlies. |
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
| #1 | `ADD / DROP` | **Dean Wade** | Jaxson Hayes | `3.0 / 2.0` | **`+0.239`** | STL (%54 ➔ %63), REB (%41 ➔ %45) |
| #2 | `ADD / DROP` | **De'Andre Hunter** | Bilal Coulibaly | `3.0 / 2.0` | **`+0.224`** | PTS (%45 ➔ %54), REB (%41 ➔ %48) |
| #3 | `ADD / DROP` | **Ryan Kalkbrenner** | Jaxson Hayes | `3.0 / 2.0` | **`+0.185`** | REB (%41 ➔ %47), PTS (%45 ➔ %47) |
| #4 | `ADD / DROP` | **Jake LaRavia** | Bilal Coulibaly | `4.0 / 2.0` | **`+0.181`** | STL (%54 ➔ %60), REB (%41 ➔ %45) |
| #5 | `ADD / DROP` | **Moussa Diabaté** | Bilal Coulibaly | `3.0 / 2.0` | **`+0.157`** | REB (%41 ➔ %53), FG_PCT (%44 ➔ %48) |
| #6 | `ADD / DROP` | **Kevin Huerter** | Bilal Coulibaly | `3.0 / 2.0` | **`+0.128`** | PTS (%45 ➔ %48), REB (%41 ➔ %43) |
| #7 | `ADD / DROP` | **Keldon Johnson** | Bilal Coulibaly | `3.0 / 2.0` | **`+0.119`** | REB (%41 ➔ %45), PTS (%45 ➔ %49) |
| #8 | `ADD / DROP` | **Jordan Poole** | Bilal Coulibaly | `3.0 / 2.0` | **`+0.115`** | PTS (%45 ➔ %49), FT_PCT (%50 ➔ %53) |
| #9 | `ADD / DROP` | **Jeremiah Fears** | Bilal Coulibaly | `3.0 / 2.0` | **`+0.102`** | PTS (%45 ➔ %50), STL (%54 ➔ %57) |
| #10 | `ADD / DROP` | **Kentavious Caldwell-Pope** | Bilal Coulibaly | `3.0 / 2.0` | **`+0.102`** | STL (%54 ➔ %56), PTS (%45 ➔ %47) |
| #11 | `ADD / DROP` | **Sam Merrill** | Bilal Coulibaly | `3.0 / 2.0` | **`+0.102`** | PTS (%45 ➔ %47), FG3M (%24 ➔ %30) |
| #12 | `ADD / DROP` | **Gui Santos** | Bilal Coulibaly | `3.0 / 2.0` | **`+0.092`** | REB (%41 ➔ %44), PTS (%45 ➔ %47) |
| #13 | `ADD / DROP` | **Javonte Green** | Bilal Coulibaly | `3.0 / 2.0` | **`+0.092`** | STL (%54 ➔ %56), REB (%41 ➔ %42) |
| #14 | `ADD / DROP` | **Anfernee Simons** | Bilal Coulibaly | `3.0 / 2.0` | **`+0.091`** | PTS (%45 ➔ %49), FG3M (%24 ➔ %30) |
| #15 | `ADD / DROP` | **Luguentz Dort** | Bilal Coulibaly | `3.0 / 2.0` | **`+0.078`** | REB (%41 ➔ %42), PTS (%45 ➔ %46) |

### 📋 Available Healthy Free Agents Pool (Top 8)
| Rank | Free Agent | Source | Exp Min (Boost) | Base Z | Eff Availability |
| :---: | :--- | :---: | :---: | :---: | :---: |
| #1 | **Dean Wade** | `Unrostered FA` | `29.0m` | `-1.33` | `0.81` |
| #2 | **Moussa Diabaté** | `🔥 Dropped by Team` | `25.6m (+0.8m)` | `-1.58` | `0.88` |
| #3 | **Max Christie** | `Unrostered FA` | `31.3m (+2.1m)` | `-2.63` | `0.90` |
| #4 | **Ziaire Williams** | `Unrostered FA` | `26.0m` | `-2.84` | `0.82` |
| #5 | **Jordan Goodwin** | `Unrostered FA` | `21.9m (+0.6m)` | `-2.94` | `0.87` |
| #6 | **Kevin Huerter** | `Unrostered FA` | `25.6m (+3.6m)` | `-2.96` | `0.86` |
| #7 | **Malik Beasley** | `Unrostered FA` | `26.7m` | `-3.17` | `0.82` |
| #8 | **Keldon Johnson** | `Unrostered FA` | `22.3m` | `-3.23` | `0.92` |

---

## 4. ⚔️ Live Matchup Scoreboard & Updated Projections: Berk's Best Team vs Mordor Tulums
* **IL+ Stash:** `Brandon Ingram`
* **Top Auto-Streamer:** `Dean Wade`
* **Remaining Games Multiplier:** `Berk: 100% remaining | Mordor Tulums: 100% remaining`
* **Expected Matchup Outcome:** **4.33 - 4.67** | **Matchup Win Prob $P(\ge 5\text{ cats})$:** **`%45.1`** (Mordor Tulums favori)

| Category | Live Score | Berk Proj Final | Mordor Tulums Proj Final | Berk Win Prob | Projected Winner |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **PTS** | `64 - 74` | `553.8` | `556.0` | `%49.2` | ⚖️ Toss-up |
| **REB** | `37 - 30` | `223.8` | `226.6` | `%47.6` | Mordor Tulums |
| **AST** | `18 - 15` | `119.2` | `95.5` | `%83.5` | 🏆 Berk |
| **STL** | `6 - 5` | `43.1` | `38.9` | `%64.6` | 🏆 Berk |
| **BLK** | `6 - 5` | `28.5` | `32.4` | `%34.4` | Mordor Tulums |
| **FG3M** | `6 - 8` | `57.8` | `66.4` | `%30.9` | Mordor Tulums |
| **TOV** | `8 - 4` | `58.7` | `51.1` | `%30.4` | Mordor Tulums |
| **FG%** | `.421 - .429` | `.477` | `.484` | `%42.4` | Mordor Tulums |
| **FT%** | `.769 - .800` | `.796` | `.797` | `%49.5` | Mordor Tulums |
# 🏀 NBA Fantasy Autonomous Cloud Sync Report
**Sync Timestamp:** `2026-10-27 22:27:00 UTC`  
**Official NBA Ingestion:** `https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-10-27_06_15PM.pdf`  
**Yahoo League Status:** `Tarayıcı Köprüsü Aktif (14 Takım Canlı Kadro & Skor)`  

---

## 1. 🛡️ Berk's Best Team Roster, IL+ & Slot Audit
| Player | Active/IL+ Slot | Status | Play Probability | Notes / Reason |
| :--- | :---: | :---: | :---: | :--- |
| ✅ **Tyrese Maxey** | `Active/BN` | Healthy | `0.87` | Expected to play |
| ✅ **Ayo Dosunmu** | `Active/BN` | Healthy | `0.86` | Expected to play |
| ✅ **James Harden** | `Active/BN` | Healthy | `0.88` | Expected to play |
| ⚠️ **Bilal Coulibaly** | `Active/BN` | **HEALTHY** | `0.81` | Expected to play |
| ✅ **Precious Achiuwa** | `Active/BN` | Healthy | `0.88` | Expected to play |
| ✅ **Josh Hart** | `Active/BN` | Healthy | `0.87` | Expected to play |
| ⚠️ **Jaxson Hayes** | `Active/BN` | **QUESTIONABLE** | `0.52` | Hayes (shoulder) is out for Monday's game against the Grizzlies. |
| ⚠️ **Jarrett Allen** | `Active/BN` | **HEALTHY** | `0.85` | Expected to play |
| ✅ **Julian Champagnie** | `Active/BN` | Healthy | `0.92` | Expected to play |
| ✅ **Neemias Queta** | `Active/BN` | Healthy | `0.90` | Expected to play |
| ✅ **Jabari Smith Jr.** | `Active/BN` | Healthy | `0.90` | Expected to play |
| ✅ **Desmond Bane** | `Active/BN` | Healthy | `0.92` | Expected to play |
| ❌ **Kawhi Leonard** | `IL+` | **OUT** | `0.00` | Leonard (knee) is expected to miss multiple weeks due to swelling in his left knee, Shams Charania of ESPN reports. |
| ❌ **Brandon Ingram** | `IL+` | **OUT** | `0.00` | Ingram won't be ready for the start of the season due to a partially torn Achilles, per Joey Linn of SI.com. |

### 🔍 League-Wide IL+ Stashes & Open Roster Slots
| Slot & Team | Players in IL/IL+ | Injured in Active/BN (Needs IL) | Empty Active Roster Spots |
| :--- | :--- | :--- | :---: |
| **#1 MuCa Tandır** | Cason Wallace, Kon Knueppel | — | `0` |
| **#2 Mordor Tulums** | Tobias Harris, Chet Holmgren | — | `0` |
| **#3 Philadelphia Sikers** | — | Ivica Zubac (OUT) | `0` |
| **#4 Houston Buckets** | — | Jalen Williams (O), Keegan Murray (O), Nic Claxton (O) | `0` |
| **#5 Kuvâ-yi Milfiye** | — | Alex Caruso (OUT) | `0` |
| **#6 abu dhabi camels** | AJ Dybantsa | — | `0` |
| **#7 Samurai Strikers** | Mark Williams | — | `0` |
| **#8 Berk's Best Team** | Kawhi Leonard, Brandon Ingram | — | `0` |
| **#9 FatihTerimSpor** | Jalen Duren, Paolo Banchero | — | `0` |
| **#11 Fikirtepe Warriors** | Jusuf Nurkić, Coby White | — | `0` |
| **#12 Istanbul Brickmakers** | Kristaps Porziņģis, Yves Missi | — | `0` |
| **#13 SILE BULLS** | VJ Edgecombe, Jimmy Butler III | — | `0` |
| **#14 YearOne Tyrants** | Jalen Suggs | — | `0` |

---

## 2. 🔄 Recent League Transactions (Who Added / Dropped Whom)
| Transaction | Team | Added Player(s) | Dropped Player(s) |
| :---: | :--- | :--- | :--- |
| `ADD/DROP` | **MuCa Tandırs** | ➕ **Josh Minott** | ➖ Kelly Oubre Jr. |
| `ADD/DROP` | **Samurai Strikers** | ➕ **Pelle Larsson** | ➖ Jay Huff |
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

---

## 3. 🎯 Dynamic Add/Drop Recommendations (Remaining Games & Live Scoreboard Weighted)
Optimized via $\Delta \sum_{c=1}^{9} \Phi_c$ conditioned on live category margins and remaining games this week:

| Rank | Action | Add Target (FA) | Drop Candidate | Rem Games (Add/Drop) | $\Delta E[\text{Wins}]$ | Key Category Gains |
| :---: | :---: | :--- | :--- | :---: | :---: | :--- |
| #1 | `ADD (Boş Yuva / IL+)` | **Moussa Diabaté** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.418`** | REB (%39 ➔ %57), STL (%60 ➔ %69) |
| #2 | `ADD (Boş Yuva / IL+)` | **Jake LaRavia** | Boş Yuva (IL+ Boş Yuva) | `4.0 / 0.0` | **`+0.400`** | STL (%60 ➔ %73), REB (%39 ➔ %49) |
| #3 | `ADD (Boş Yuva / IL+)` | **Dean Wade** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.394`** | STL (%60 ➔ %72), REB (%39 ➔ %48) |
| #4 | `ADD (Boş Yuva / IL+)` | **Kevin Huerter** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.378`** | REB (%39 ➔ %48), STL (%60 ➔ %69) |
| #5 | `ADD (Boş Yuva / IL+)` | **Keldon Johnson** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.373`** | REB (%39 ➔ %51), STL (%60 ➔ %66) |
| #6 | `ADD (Boş Yuva / IL+)` | **Jay Huff** | Boş Yuva (IL+ Boş Yuva) | `2.0 / 0.0` | **`+0.360`** | REB (%39 ➔ %47), PTS (%38 ➔ %46) |
| #7 | `ADD (Boş Yuva / IL+)` | **De'Andre Hunter** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.355`** | PTS (%38 ➔ %51), REB (%39 ➔ %49) |
| #8 | `ADD (Boş Yuva / IL+)` | **Ryan Kalkbrenner** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.353`** | REB (%39 ➔ %51), FG_PCT (%43 ➔ %48) |
| #9 | `ADD (Boş Yuva / IL+)` | **Gui Santos** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.339`** | REB (%39 ➔ %49), STL (%60 ➔ %68) |
| #10 | `ADD (Boş Yuva / IL+)` | **Jarace Walker** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.328`** | REB (%39 ➔ %51), STL (%60 ➔ %68) |
| #11 | `ADD (Boş Yuva / IL+)` | **Jeremiah Fears** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.242`** | STL (%60 ➔ %68), REB (%39 ➔ %45) |
| #12 | `ADD (Boş Yuva / IL+)` | **Sam Merrill** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.232`** | STL (%60 ➔ %64), REB (%39 ➔ %43) |
| #13 | `ADD (Boş Yuva / IL+)` | **Javonte Green** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.109`** | STL (%60 ➔ %63), REB (%39 ➔ %41) |
| #14 | `ADD (Boş Yuva / IL+)` | **Kentavious Caldwell-Pope** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.107`** | STL (%60 ➔ %63), REB (%39 ➔ %41) |
| #15 | `ADD (Boş Yuva / IL+)` | **Anfernee Simons** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.104`** | PTS (%38 ➔ %42), STL (%60 ➔ %62) |

### 📋 Available Healthy Free Agents Pool (Top 8)
| Rank | Free Agent | Source | Exp Min (Boost) | Base Z | Eff Availability |
| :---: | :--- | :---: | :---: | :---: | :---: |
| #1 | **Jay Huff** | `🔥 Dropped by Team` | `23.9m (+7.0m)` | `0.93` | `0.92` |
| #2 | **Moussa Diabaté** | `🔥 Dropped by Team` | `25.6m (+0.8m)` | `-1.58` | `0.88` |
| #3 | **Dean Wade** | `Unrostered FA` | `27.7m (-1.1m)` | `-1.80` | `0.81` |
| #4 | **Max Christie** | `Unrostered FA` | `31.9m (+2.7m)` | `-2.47` | `0.90` |
| #5 | **Ziaire Williams** | `Unrostered FA` | `26.0m` | `-2.84` | `0.82` |
| #6 | **Jordan Goodwin** | `Unrostered FA` | `21.9m (+0.6m)` | `-2.94` | `0.87` |
| #7 | **Kevin Huerter** | `Unrostered FA` | `25.6m (+3.7m)` | `-2.96` | `0.86` |
| #8 | **Malik Beasley** | `Unrostered FA` | `26.7m` | `-3.17` | `0.82` |

---

## 4. ⚔️ Live Matchup Scoreboard & Updated Projections: Berk's Best Team vs Mordor Tulums
* **IL+ Stash:** `Kawhi Leonard, Brandon Ingram`
* **Top Auto-Streamer:** `Jay Huff, Moussa Diabaté`
* **Remaining Games Multiplier:** `Berk: 100% remaining | Mordor Tulums: 100% remaining`
* **Expected Matchup Outcome:** **4.72 - 4.28** | **Matchup Win Prob $P(\ge 5\text{ cats})$:** **`%56.2`** (Berk favori)

| Category | Live Score | Berk Proj Final | Mordor Tulums Proj Final | Berk Win Prob | Projected Winner |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **PTS** | `64 - 74` | `557.9` | `543.5` | `%55.3` | 🏆 Berk |
| **REB** | `37 - 30` | `239.5` | `221.5` | `%65.0` | 🏆 Berk |
| **AST** | `18 - 15` | `122.3` | `93.7` | `%88.0` | 🏆 Berk |
| **STL** | `6 - 5` | `41.4` | `34.9` | `%72.9` | 🏆 Berk |
| **BLK** | `6 - 5` | `33.6` | `35.1` | `%44.2` | Mordor Tulums |
| **FG3M** | `6 - 8` | `56.3` | `63.3` | `%33.9` | Mordor Tulums |
| **TOV** | `8 - 4` | `61.5` | `51.0` | `%24.0` | Mordor Tulums |
| **FG%** | `.421 - .429` | `.482` | `.486` | `%46.0` | Mordor Tulums |
| **FT%** | `.769 - .800` | `.788` | `.800` | `%42.4` | Mordor Tulums |
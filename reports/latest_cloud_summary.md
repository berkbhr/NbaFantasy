# 🏀 NBA Fantasy Autonomous Cloud Sync Report
**Sync Timestamp:** `2026-10-27 18:09:47 UTC`  
**Official NBA Ingestion:** `https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-10-27_02_00PM.pdf`  
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
| **#4 Houston Buckets** | — | Jalen Williams (O), Keegan Murray (O), Nic Claxton (O) | `0` |
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
| #1 | `ADD (Boş Yuva / IL+)` | **Moussa Diabaté** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.435`** | REB (%41 ➔ %60), STL (%50 ➔ %60) |
| #2 | `ADD (Boş Yuva / IL+)` | **Dean Wade** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.419`** | REB (%41 ➔ %52), STL (%50 ➔ %63) |
| #3 | `ADD (Boş Yuva / IL+)` | **Jake LaRavia** | Boş Yuva (IL+ Boş Yuva) | `4.0 / 0.0` | **`+0.410`** | REB (%41 ➔ %52), STL (%50 ➔ %64) |
| #4 | `ADD (Boş Yuva / IL+)` | **Kevin Huerter** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.378`** | REB (%41 ➔ %51), STL (%50 ➔ %60) |
| #5 | `ADD (Boş Yuva / IL+)` | **Keldon Johnson** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.371`** | REB (%41 ➔ %53), STL (%50 ➔ %57) |
| #6 | `ADD (Boş Yuva / IL+)` | **Ryan Kalkbrenner** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.370`** | REB (%41 ➔ %53), FG_PCT (%46 ➔ %51) |
| #7 | `ADD (Boş Yuva / IL+)` | **De'Andre Hunter** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.348`** | REB (%41 ➔ %52), STL (%50 ➔ %57) |
| #8 | `ADD (Boş Yuva / IL+)` | **Gui Santos** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.327`** | REB (%41 ➔ %52), STL (%50 ➔ %59) |
| #9 | `ADD (Boş Yuva / IL+)` | **Jordan Poole** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.236`** | STL (%50 ➔ %56), REB (%41 ➔ %45) |
| #10 | `ADD (Boş Yuva / IL+)` | **Jeremiah Fears** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.227`** | STL (%50 ➔ %58), REB (%41 ➔ %47) |
| #11 | `ADD (Boş Yuva / IL+)` | **Sam Merrill** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.223`** | STL (%50 ➔ %55), REB (%41 ➔ %45) |
| #12 | `ADD (Boş Yuva / IL+)` | **Luguentz Dort** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.200`** | STL (%50 ➔ %56), REB (%41 ➔ %47) |
| #13 | `ADD (Boş Yuva / IL+)` | **Kentavious Caldwell-Pope** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.113`** | STL (%50 ➔ %54), REB (%41 ➔ %44) |
| #14 | `ADD (Boş Yuva / IL+)` | **Javonte Green** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.108`** | STL (%50 ➔ %54), REB (%41 ➔ %44) |
| #15 | `ADD (Boş Yuva / IL+)` | **Anfernee Simons** | Boş Yuva (IL+ Boş Yuva) | `3.0 / 0.0` | **`+0.104`** | STL (%50 ➔ %52), REB (%41 ➔ %43) |

### 📋 Available Healthy Free Agents Pool (Top 8)
| Rank | Free Agent | Source | Exp Min (Boost) | Base Z | Eff Availability |
| :---: | :--- | :---: | :---: | :---: | :---: |
| #1 | **Dean Wade** | `Unrostered FA` | `29.0m` | `-1.33` | `0.81` |
| #2 | **Jay Huff** | `🔥 Dropped by Team` | `19.5m (+2.6m)` | `-1.47` | `0.92` |
| #3 | **Moussa Diabaté** | `🔥 Dropped by Team` | `25.6m (+0.8m)` | `-1.58` | `0.88` |
| #4 | **Max Christie** | `Unrostered FA` | `31.3m (+2.1m)` | `-2.63` | `0.90` |
| #5 | **Ziaire Williams** | `Unrostered FA` | `26.0m` | `-2.84` | `0.82` |
| #6 | **Jordan Goodwin** | `Unrostered FA` | `21.9m (+0.6m)` | `-2.94` | `0.87` |
| #7 | **Kevin Huerter** | `Unrostered FA` | `25.6m (+3.6m)` | `-2.96` | `0.86` |
| #8 | **Malik Beasley** | `Unrostered FA` | `26.7m` | `-3.17` | `0.82` |

---

## 4. ⚔️ Live Matchup Scoreboard & Updated Projections: Berk's Best Team vs Mordor Tulums
* **IL+ Stash:** `Kawhi Leonard, Brandon Ingram`
* **Top Auto-Streamer:** `Dean Wade, Jay Huff`
* **Remaining Games Multiplier:** `Berk: 100% remaining | Mordor Tulums: 100% remaining`
* **Expected Matchup Outcome:** **4.50 - 4.50** | **Matchup Win Prob $P(\ge 5\text{ cats})$:** **`%49.9`** (Mordor Tulums favori)

| Category | Live Score | Berk Proj Final | Mordor Tulums Proj Final | Berk Win Prob | Projected Winner |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **PTS** | `64 - 74` | `542.0` | `551.7` | `%46.4` | Mordor Tulums |
| **REB** | `37 - 30` | `225.2` | `215.7` | `%58.3` | 🏆 Berk |
| **AST** | `18 - 15` | `118.2` | `92.5` | `%86.0` | 🏆 Berk |
| **STL** | `6 - 5` | `41.6` | `37.0` | `%66.5` | 🏆 Berk |
| **BLK** | `6 - 5` | `32.0` | `32.4` | `%48.4` | ⚖️ Toss-up |
| **FG3M** | `6 - 8` | `57.7` | `67.2` | `%28.8` | Mordor Tulums |
| **TOV** | `8 - 4` | `58.1` | `49.8` | `%28.2` | Mordor Tulums |
| **FG%** | `.421 - .429` | `.478` | `.482` | `%45.0` | Mordor Tulums |
| **FT%** | `.769 - .800` | `.790` | `.802` | `%42.1` | Mordor Tulums |
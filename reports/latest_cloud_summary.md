# NBA Fantasy — cached-data forecast

Generated: 2026-10-28T22:44:15.166676+00:00
Matchup: **Berk's Best Team vs Mordor Tulums**
Window: 2026-10-28 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **4.859**.
Expected category points: **4.86 / 9**.
Expected category wins: 4.80; ties: 0.12.
Secondary weekly W/L/D: 60.4% / 36.3% / 3.3%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 59.5% | 0.6% | 39.9% |
| REB | 49.1% | 1.5% | 49.4% |
| AST | 98.3% | 0.2% | 1.4% |
| STL | 87.7% | 2.3% | 10.0% |
| BLK | 7.5% | 2.2% | 90.3% |
| TOV | 7.4% | 1.4% | 91.2% |
| FG3M | 52.4% | 3.5% | 44.1% |
| FG_PCT | 56.6% | 0.0% | 43.4% |
| FT_PCT | 61.3% | 0.0% | 38.7% |

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 112 / 171 | 397.80 / 322.94 | 63.61 |
| REB | 49 / 80 | 150.81 / 119.90 | 25.93 |
| AST | 28 / 25 | 86.36 / 53.88 | 16.45 |
| STL | 14 / 12 | 28.44 / 20.59 | 8.07 |
| BLK | 6 / 16 | 18.20 / 17.86 | 7.06 |
| TOV | 14 / 10 | 43.81 / 32.82 | 10.72 |
| FG3M | 17 / 16 | 40.58 / 40.38 | 11.48 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| Jay Huff | Bilal Coulibaly | FA | +0.370 | +0.263 |
| Dean Wade | Bilal Coulibaly | FA | +0.176 | +0.176 |
| Jarace Walker | Bilal Coulibaly | FA | +0.194 | +0.152 |
| Ryan Kalkbrenner | Bilal Coulibaly | FA | +0.150 | +0.150 |
| Isaiah Jackson | Bilal Coulibaly | FA | +0.143 | +0.143 |
| Graham Ike | Bilal Coulibaly | FA | +0.139 | +0.139 |
| Collin Sexton | Bilal Coulibaly | FA | +0.158 | +0.115 |
| Kelly Oubre Jr. | Bilal Coulibaly | FA | +0.112 | +0.112 |

## Forecast active lineups

- 2026-10-28: Jarrett Allen, Josh Hart, Jaxson Hayes, Tyrese Maxey, Desmond Bane, Ayo Dosunmu, Julian Champagnie, Jabari Smith Jr., Jake LaRavia, James Harden
- 2026-10-29: Jarrett Allen, Precious Achiuwa, James Harden
- 2026-10-30: Josh Hart, Neemias Queta, Tyrese Maxey, Desmond Bane, Ayo Dosunmu, Jabari Smith Jr., Jake LaRavia, Bilal Coulibaly
- 2026-10-31: Jarrett Allen, Jaxson Hayes, Precious Achiuwa, Tyrese Maxey, Ayo Dosunmu, Julian Champagnie, Jabari Smith Jr., James Harden
- 2026-11-01: Neemias Queta, Desmond Bane, Jake LaRavia

## Assumptions and data quality

- Local caches only; no data fetched and no notifications sent.
- Category marginals use moment/normal approximations. Weekly W/L/D assumes category independence.
- Return dates, rotations and future lineup choices remain model assumptions.
- Live moves are ranked by the lower category-point gain with and without teammate injury spillover; both scenarios must improve their own no-move baseline. This is a conservative sensitivity rule, not a fitted posterior or proven performance improvement.

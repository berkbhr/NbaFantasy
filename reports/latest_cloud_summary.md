# NBA Fantasy — cached-data forecast

Generated: 2026-10-28T20:16:42.420077+00:00
Matchup: **Berk's Best Team vs Mordor Tulums**
Window: 2026-10-28 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **4.701**.
Expected category points: **4.70 / 9**.
Expected category wins: 4.64; ties: 0.12.
Secondary weekly W/L/D: 55.0% / 41.5% / 3.5%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 54.5% | 0.6% | 44.9% |
| REB | 44.1% | 1.5% | 54.3% |
| AST | 98.0% | 0.3% | 1.7% |
| STL | 86.4% | 2.5% | 11.1% |
| BLK | 7.2% | 2.1% | 90.7% |
| TOV | 8.4% | 1.5% | 90.1% |
| FG3M | 48.2% | 3.5% | 48.3% |
| FG_PCT | 56.1% | 0.0% | 43.9% |
| FT_PCT | 61.3% | 0.0% | 38.7% |

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 112 / 171 | 399.83 / 333.29 | 63.03 |
| REB | 49 / 80 | 151.28 / 123.58 | 25.77 |
| AST | 28 / 25 | 86.78 / 55.50 | 16.46 |
| STL | 14 / 12 | 28.55 / 21.17 | 8.10 |
| BLK | 6 / 16 | 18.24 / 18.10 | 7.09 |
| TOV | 14 / 10 | 44.04 / 33.71 | 10.75 |
| FG3M | 17 / 16 | 40.81 / 41.83 | 11.48 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| Jay Huff | Bilal Coulibaly | FA | +0.325 | +0.263 |
| Dean Wade | Bilal Coulibaly | FA | +0.184 | +0.184 |
| Jarace Walker | Bilal Coulibaly | FA | +0.163 | +0.153 |
| Ryan Kalkbrenner | Bilal Coulibaly | FA | +0.149 | +0.149 |
| Isaiah Jackson | Bilal Coulibaly | FA | +0.147 | +0.142 |
| Graham Ike | Bilal Coulibaly | FA | +0.141 | +0.141 |
| Collin Sexton | Bilal Coulibaly | FA | +0.166 | +0.121 |
| Jeremiah Fears | Bilal Coulibaly | FA | +0.113 | +0.113 |

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

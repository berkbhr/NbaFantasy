# NBA Fantasy — cached-data forecast

Generated: 2026-10-30T21:36:55.542403+00:00
Matchup: **Berk's Best Team vs Mordor Tulums**
Window: 2026-10-30 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **5.923**.
Expected category points: **5.92 / 9**.
Expected category wins: 5.86; ties: 0.13.
Secondary weekly W/L/D: 91.5% / 7.0% / 1.6%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 43.5% | 0.8% | 55.7% |
| REB | 80.8% | 1.3% | 17.9% |
| AST | 99.5% | 0.1% | 0.4% |
| STL | 99.7% | 0.1% | 0.2% |
| BLK | 24.4% | 6.1% | 69.5% |
| TOV | 1.5% | 0.6% | 97.9% |
| FG3M | 58.5% | 4.5% | 37.1% |
| FG_PCT | 79.5% | 0.0% | 20.5% |
| FT_PCT | 98.1% | 0.0% | 1.9% |

## Why the weekly forecast changed

Sequential attribution from the previous archived forecast; not causal identification.

Player examples are NBA boxscores for the old planned lineup; actual Yahoo starters can differ.

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 268 / 347 | 237.71 / 165.99 | 47.74 |
| REB | 131 / 139 | 93.36 / 67.11 | 20.36 |
| AST | 61 / 53 | 50.41 / 26.71 | 11.95 |
| STL | 30 / 20 | 17.70 / 10.37 | 6.02 |
| BLK | 17 / 22 | 11.63 / 9.92 | 5.46 |
| TOV | 31 / 23 | 24.53 / 16.35 | 7.70 |
| FG3M | 34 / 36 | 25.45 / 21.11 | 8.63 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| Jay Huff | Jaxson Hayes | FA | +0.356 | +0.279 |
| Ryan Kalkbrenner | Jaxson Hayes | FA | +0.152 | +0.152 |
| Jarace Walker | Jaxson Hayes | FA | +0.171 | +0.139 |
| Jakob Poeltl | Jaxson Hayes | FA | +0.116 | +0.116 |
| Collin Sexton | Jaxson Hayes | FA | +0.117 | +0.104 |
| Anfernee Simons | Jaxson Hayes | FA | +0.100 | +0.100 |
| Adem Bona | Jaxson Hayes | FA | +0.148 | +0.093 |
| De'Anthony Melton | Jaxson Hayes | FA | +0.088 | +0.088 |

## Forecast active lineups

- 2026-10-30: Josh Hart, Neemias Queta, Dean Wade, Tyrese Maxey, Desmond Bane, Ayo Dosunmu, Jabari Smith Jr., Jake LaRavia
- 2026-10-31: Jarrett Allen, Jaxson Hayes, Dean Wade, Precious Achiuwa, Tyrese Maxey, Ayo Dosunmu, Julian Champagnie, Jabari Smith Jr., James Harden
- 2026-11-01: Neemias Queta, Desmond Bane, Jake LaRavia

## Assumptions and data quality

- Local caches only; no data fetched and no notifications sent.
- Category marginals use moment/normal approximations. Weekly W/L/D assumes category independence.
- Return dates, rotations and future lineup choices remain model assumptions.
- Live moves are ranked by the lower category-point gain with and without teammate injury spillover; both scenarios must improve their own no-move baseline. This is a conservative sensitivity rule, not a fitted posterior or proven performance improvement.

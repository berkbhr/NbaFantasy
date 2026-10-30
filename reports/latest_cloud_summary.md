# NBA Fantasy — cached-data forecast

Generated: 2026-10-30T20:36:14.563398+00:00
Matchup: **Berk's Best Team vs Mordor Tulums**
Window: 2026-10-30 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **5.932**.
Expected category points: **5.93 / 9**.
Expected category wins: 5.86; ties: 0.13.
Secondary weekly W/L/D: 91.6% / 6.9% / 1.5%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 43.8% | 0.8% | 55.4% |
| REB | 80.8% | 1.3% | 17.8% |
| AST | 99.6% | 0.1% | 0.3% |
| STL | 99.8% | 0.1% | 0.1% |
| BLK | 24.4% | 6.1% | 69.5% |
| TOV | 1.4% | 0.6% | 98.0% |
| FG3M | 59.2% | 4.4% | 36.4% |
| FG_PCT | 79.3% | 0.0% | 20.7% |
| FT_PCT | 98.2% | 0.0% | 1.8% |

## Why the weekly forecast changed

Sequential attribution from the previous archived forecast; not causal identification.

Player examples are NBA boxscores for the old planned lineup; actual Yahoo starters can differ.

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 268 / 347 | 236.55 / 164.45 | 47.47 |
| REB | 131 / 139 | 92.80 / 66.64 | 20.25 |
| AST | 61 / 53 | 50.21 / 26.45 | 11.90 |
| STL | 30 / 20 | 17.63 / 10.26 | 6.00 |
| BLK | 17 / 22 | 11.57 / 9.83 | 5.44 |
| TOV | 31 / 23 | 24.40 / 16.17 | 7.66 |
| FG3M | 34 / 36 | 25.41 / 20.91 | 8.60 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| Jay Huff | Jaxson Hayes | FA | +0.357 | +0.279 |
| Ryan Kalkbrenner | Jaxson Hayes | FA | +0.153 | +0.153 |
| Jarace Walker | Jaxson Hayes | FA | +0.171 | +0.139 |
| Jakob Poeltl | Jaxson Hayes | FA | +0.117 | +0.117 |
| Collin Sexton | Jaxson Hayes | FA | +0.117 | +0.104 |
| Anfernee Simons | Jaxson Hayes | FA | +0.098 | +0.098 |
| Adem Bona | Jaxson Hayes | FA | +0.148 | +0.093 |
| De'Anthony Melton | Jaxson Hayes | FA | +0.087 | +0.087 |

## Forecast active lineups

- 2026-10-30: Josh Hart, Neemias Queta, Dean Wade, Tyrese Maxey, Desmond Bane, Ayo Dosunmu, Jabari Smith Jr., Jake LaRavia
- 2026-10-31: Jarrett Allen, Jaxson Hayes, Dean Wade, Precious Achiuwa, Tyrese Maxey, Ayo Dosunmu, Julian Champagnie, Jabari Smith Jr., James Harden
- 2026-11-01: Neemias Queta, Desmond Bane, Jake LaRavia

## Assumptions and data quality

- Local caches only; no data fetched and no notifications sent.
- Category marginals use moment/normal approximations. Weekly W/L/D assumes category independence.
- Return dates, rotations and future lineup choices remain model assumptions.
- Live moves are ranked by the lower category-point gain with and without teammate injury spillover; both scenarios must improve their own no-move baseline. This is a conservative sensitivity rule, not a fitted posterior or proven performance improvement.

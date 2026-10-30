# NBA Fantasy — cached-data forecast

Generated: 2026-10-30T18:08:38.348953+00:00
Matchup: **Berk's Best Team vs Mordor Tulums**
Window: 2026-10-30 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **5.761**.
Expected category points: **5.76 / 9**.
Expected category wins: 5.69; ties: 0.14.
Secondary weekly W/L/D: 88.5% / 9.5% / 2.0%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 37.3% | 0.8% | 61.9% |
| REB | 76.7% | 1.5% | 21.8% |
| AST | 99.4% | 0.1% | 0.5% |
| STL | 99.7% | 0.1% | 0.2% |
| BLK | 22.8% | 5.9% | 71.2% |
| TOV | 1.8% | 0.7% | 97.5% |
| FG3M | 54.4% | 4.6% | 41.0% |
| FG_PCT | 79.0% | 0.0% | 21.0% |
| FT_PCT | 98.1% | 0.0% | 1.9% |

## Why the weekly forecast changed

Sequential attribution from the previous archived forecast; not causal identification.

Player examples are NBA boxscores for the old planned lineup; actual Yahoo starters can differ.

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 268 / 347 | 232.85 / 168.64 | 47.27 |
| REB | 131 / 139 | 91.49 / 68.26 | 20.21 |
| AST | 61 / 53 | 49.36 / 27.10 | 11.85 |
| STL | 30 / 20 | 17.23 / 10.47 | 5.97 |
| BLK | 17 / 22 | 11.40 / 9.94 | 5.43 |
| TOV | 31 / 23 | 24.03 / 16.52 | 7.65 |
| FG3M | 34 / 36 | 24.94 / 21.49 | 8.59 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| Jay Huff | Jaxson Hayes | FA | +0.356 | +0.281 |
| Ryan Kalkbrenner | Jaxson Hayes | FA | +0.174 | +0.174 |
| Jarace Walker | Jaxson Hayes | FA | +0.178 | +0.143 |
| Jakob Poeltl | Jaxson Hayes | FA | +0.125 | +0.125 |
| Collin Sexton | Jaxson Hayes | FA | +0.115 | +0.105 |
| Royce O'Neale | Jaxson Hayes | FA | +0.103 | +0.103 |
| De'Anthony Melton | Jaxson Hayes | FA | +0.100 | +0.100 |
| Graham Ike | Jaxson Hayes | FA | +0.101 | +0.099 |

## Forecast active lineups

- 2026-10-30: Josh Hart, Neemias Queta, Dean Wade, Tyrese Maxey, Desmond Bane, Ayo Dosunmu, Jabari Smith Jr., Jake LaRavia
- 2026-10-31: Jarrett Allen, Jaxson Hayes, Dean Wade, Precious Achiuwa, Tyrese Maxey, Ayo Dosunmu, Julian Champagnie, Jabari Smith Jr., James Harden
- 2026-11-01: Neemias Queta, Desmond Bane, Jake LaRavia

## Assumptions and data quality

- Local caches only; no data fetched and no notifications sent.
- Category marginals use moment/normal approximations. Weekly W/L/D assumes category independence.
- Return dates, rotations and future lineup choices remain model assumptions.
- Live moves are ranked by the lower category-point gain with and without teammate injury spillover; both scenarios must improve their own no-move baseline. This is a conservative sensitivity rule, not a fitted posterior or proven performance improvement.

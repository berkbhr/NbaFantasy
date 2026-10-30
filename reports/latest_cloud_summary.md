# NBA Fantasy — cached-data forecast

Generated: 2026-10-30T22:32:26.739653+00:00
Matchup: **Berk's Best Team vs Mordor Tulums**
Window: 2026-10-30 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **6.148**.
Expected category points: **6.15 / 9**.
Expected category wins: 6.08; ties: 0.14.
Secondary weekly W/L/D: 94.6% / 4.3% / 1.1%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 50.7% | 0.9% | 48.5% |
| REB | 86.4% | 1.1% | 12.5% |
| AST | 99.7% | 0.1% | 0.3% |
| STL | 99.8% | 0.1% | 0.1% |
| BLK | 30.3% | 7.0% | 62.7% |
| TOV | 1.0% | 0.4% | 98.5% |
| FG3M | 60.9% | 4.4% | 34.7% |
| FG_PCT | 80.7% | 0.0% | 19.3% |
| FT_PCT | 98.3% | 0.0% | 1.7% |

## Why the weekly forecast changed

Sequential attribution from the previous archived forecast; not causal identification.

Player examples are NBA boxscores for the old planned lineup; actual Yahoo starters can differ.

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 268 / 347 | 238.76 / 158.44 | 46.78 |
| REB | 131 / 139 | 93.65 / 63.70 | 19.52 |
| AST | 61 / 53 | 50.64 / 25.80 | 11.94 |
| STL | 30 / 20 | 17.79 / 10.06 | 6.00 |
| BLK | 17 / 22 | 11.67 / 8.85 | 5.20 |
| TOV | 31 / 23 | 24.62 / 15.57 | 7.60 |
| FG3M | 34 / 36 | 25.59 / 20.71 | 8.60 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| Jay Huff | Jaxson Hayes | FA | +0.360 | +0.282 |
| Ryan Kalkbrenner | Jaxson Hayes | FA | +0.153 | +0.153 |
| Jarace Walker | Jaxson Hayes | FA | +0.158 | +0.130 |
| Noah Clowney | Jaxson Hayes | FA | +0.118 | +0.118 |
| Jakob Poeltl | Jaxson Hayes | FA | +0.105 | +0.105 |
| Anfernee Simons | Jaxson Hayes | FA | +0.101 | +0.101 |
| Collin Sexton | Jaxson Hayes | FA | +0.109 | +0.099 |
| Adem Bona | Jaxson Hayes | FA | +0.155 | +0.093 |

## Forecast active lineups

- 2026-10-30: Josh Hart, Neemias Queta, Dean Wade, Tyrese Maxey, Desmond Bane, Ayo Dosunmu, Jabari Smith Jr., Jake LaRavia
- 2026-10-31: Jarrett Allen, Jaxson Hayes, Dean Wade, Precious Achiuwa, Tyrese Maxey, Ayo Dosunmu, Julian Champagnie, Jabari Smith Jr., James Harden
- 2026-11-01: Neemias Queta, Desmond Bane, Jake LaRavia

## Assumptions and data quality

- Local caches only; no data fetched and no notifications sent.
- Category marginals use moment/normal approximations. Weekly W/L/D assumes category independence.
- Return dates, rotations and future lineup choices remain model assumptions.
- Live moves are ranked by the lower category-point gain with and without teammate injury spillover; both scenarios must improve their own no-move baseline. This is a conservative sensitivity rule, not a fitted posterior or proven performance improvement.

# NBA Fantasy — cached-data forecast

Generated: 2026-10-29T18:36:27.075278+00:00
Matchup: **Berk's Best Team vs Mordor Tulums**
Window: 2026-10-29 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **4.961**.
Expected category points: **4.96 / 9**.
Expected category wins: 4.89; ties: 0.14.
Secondary weekly W/L/D: 63.7% / 31.9% / 4.4%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 22.4% | 0.6% | 77.0% |
| REB | 69.9% | 1.6% | 28.5% |
| AST | 98.8% | 0.2% | 1.0% |
| STL | 97.6% | 0.7% | 1.7% |
| BLK | 26.8% | 5.9% | 67.3% |
| TOV | 3.5% | 1.0% | 95.5% |
| FG3M | 47.7% | 4.2% | 48.1% |
| FG_PCT | 32.8% | 0.0% | 67.2% |
| FT_PCT | 89.5% | 0.0% | 10.5% |

## Why the weekly forecast changed

Sequential attribution from the previous archived forecast; not causal identification.

Player examples are NBA boxscores for the old planned lineup; actual Yahoo starters can differ.

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 206 / 285 | 268.34 / 228.79 | 52.71 |
| REB | 109 / 119 | 108.14 / 86.28 | 21.80 |
| AST | 54 / 39 | 56.80 / 40.59 | 13.70 |
| STL | 26 / 17 | 19.53 / 14.79 | 6.68 |
| BLK | 15 / 19 | 13.22 / 12.33 | 5.84 |
| TOV | 26 / 16 | 28.46 / 23.17 | 8.71 |
| FG3M | 30 / 28 | 26.89 / 28.94 | 9.51 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| Jay Huff | Jaxson Hayes | Waiver: Oct 30 | +0.320 | +0.265 |
| Ryan Kalkbrenner | Jaxson Hayes | FA | +0.159 | +0.159 |
| Isaiah Jackson | Jaxson Hayes | Waiver: Oct 30 | +0.136 | +0.136 |
| Jarace Walker | Jaxson Hayes | FA | +0.152 | +0.134 |
| Sam Merrill | Jaxson Hayes | FA | +0.120 | +0.120 |
| Jeremiah Fears | Jaxson Hayes | FA | +0.116 | +0.116 |
| Isaiah Stewart | Jaxson Hayes | FA | +0.115 | +0.115 |
| Noah Clowney | Jaxson Hayes | FA | +0.101 | +0.101 |

## Forecast active lineups

- 2026-10-29: Jarrett Allen, Precious Achiuwa, James Harden
- 2026-10-30: Josh Hart, Neemias Queta, Dean Wade, Tyrese Maxey, Desmond Bane, Ayo Dosunmu, Jabari Smith Jr., Jake LaRavia
- 2026-10-31: Jarrett Allen, Jaxson Hayes, Dean Wade, Precious Achiuwa, Tyrese Maxey, Ayo Dosunmu, Julian Champagnie, Jabari Smith Jr., James Harden
- 2026-11-01: Neemias Queta, Desmond Bane, Jake LaRavia

## Assumptions and data quality

- Local caches only; no data fetched and no notifications sent.
- Category marginals use moment/normal approximations. Weekly W/L/D assumes category independence.
- Return dates, rotations and future lineup choices remain model assumptions.
- Live moves are ranked by the lower category-point gain with and without teammate injury spillover; both scenarios must improve their own no-move baseline. This is a conservative sensitivity rule, not a fitted posterior or proven performance improvement.

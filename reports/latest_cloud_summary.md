# NBA Fantasy — cached-data forecast

Generated: 2026-10-31T18:20:53.019313+00:00
Matchup: **Berk's Best Team vs Mordor Tulums**
Window: 2026-10-31 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **6.675**.
Expected category points: **6.67 / 9**.
Expected category wins: 6.62; ties: 0.11.
Secondary weekly W/L/D: 99.5% / 0.4% / 0.1%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 86.5% | 0.6% | 13.0% |
| REB | 64.0% | 2.3% | 33.7% |
| AST | 99.8% | 0.0% | 0.1% |
| STL | 100.0% | 0.0% | 0.0% |
| BLK | 25.3% | 7.7% | 67.0% |
| TOV | 0.0% | 0.0% | 100.0% |
| FG3M | 98.6% | 0.5% | 1.0% |
| FG_PCT | 87.9% | 0.0% | 12.1% |
| FT_PCT | 99.8% | 0.0% | 0.2% |

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 390 / 382 | 143.38 / 108.80 | 38.19 |
| REB | 163 / 171 | 57.08 / 42.91 | 15.82 |
| AST | 79 / 59 | 28.74 / 19.67 | 9.67 |
| STL | 38 / 22 | 10.35 / 6.80 | 4.69 |
| BLK | 22 / 25 | 7.54 / 7.00 | 4.45 |
| TOV | 48 / 27 | 14.52 / 11.06 | 6.10 |
| FG3M | 53 / 39 | 14.53 / 13.34 | 6.71 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| Ryan Kalkbrenner | Jake LaRavia | FA | +0.115 | +0.115 |
| Jay Huff | Jake LaRavia | FA | +0.146 | +0.100 |
| Isaiah Stewart | Jake LaRavia | FA | +0.104 | +0.098 |
| Keldon Johnson | Jake LaRavia | FA | +0.055 | +0.055 |
| Luke Kornet | Jake LaRavia | FA | +0.054 | +0.054 |
| Clint Capela | Jake LaRavia | FA | +0.132 | +0.045 |
| Jock Landale | Jake LaRavia | FA | +0.037 | +0.037 |
| Goga Bitadze | Jake LaRavia | FA | +0.110 | +0.037 |

## Forecast active lineups

- 2026-10-31: Jarrett Allen, Jaxson Hayes, Dean Wade, Precious Achiuwa, Tyrese Maxey, Ayo Dosunmu, Julian Champagnie, Jabari Smith Jr., James Harden
- 2026-11-01: Neemias Queta, Desmond Bane, Jake LaRavia

## Assumptions and data quality

- Local caches only; no data fetched and no notifications sent.
- Category marginals use moment/normal approximations. Weekly W/L/D assumes category independence.
- Return dates, rotations and future lineup choices remain model assumptions.
- Live moves are ranked by the lower category-point gain with and without teammate injury spillover; both scenarios must improve their own no-move baseline. This is a conservative sensitivity rule, not a fitted posterior or proven performance improvement.

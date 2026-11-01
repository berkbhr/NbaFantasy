# NBA Fantasy — cached-data forecast

Generated: 2026-11-01T18:02:24.492222+00:00
Matchup: **Berk's Best Team vs Mordor Tulums**
Window: 2026-11-01 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **7.000**.
Expected category points: **7.00 / 9**.
Expected category wins: 7.00; ties: 0.00.
Secondary weekly W/L/D: 100.0% / 0.0% / 0.0%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 100.0% | 0.0% | 0.0% |
| REB | 100.0% | 0.0% | 0.0% |
| AST | 100.0% | 0.0% | 0.0% |
| STL | 100.0% | 0.0% | 0.0% |
| BLK | 0.0% | 0.0% | 100.0% |
| TOV | 0.0% | 0.0% | 100.0% |
| FG3M | 100.0% | 0.0% | 0.0% |
| FG_PCT | 100.0% | 0.0% | 0.0% |
| FT_PCT | 100.0% | 0.0% | 0.0% |

## Why the weekly forecast changed

Sequential attribution from the previous archived forecast; not causal identification.

Player examples are NBA boxscores for the old planned lineup; actual Yahoo starters can differ.

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 552 / 480 | 30.87 / 15.91 | 15.45 |
| REB | 222 / 195 | 13.12 / 6.11 | 6.58 |
| AST | 116 / 80 | 6.24 / 2.46 | 3.70 |
| STL | 51 / 29 | 2.41 / 0.84 | 1.99 |
| BLK | 27 / 37 | 1.85 / 0.40 | 1.65 |
| TOV | 65 / 41 | 3.63 / 1.06 | 2.51 |
| FG3M | 71 / 49 | 2.74 / 3.19 | 3.08 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| Jay Huff | Jaxson Hayes | FA | +0.002 | +0.001 |
| Goga Bitadze | Jaxson Hayes | FA | +0.000 | +0.000 |
| Al Horford | Jaxson Hayes | FA | +0.000 | +0.000 |
| Charles Bassey | Jaxson Hayes | FA | +0.000 | +0.000 |
| Keon Ellis | Jaxson Hayes | FA | +0.000 | +0.000 |
| Allen Graves | Jaxson Hayes | FA | +0.000 | +0.000 |
| Jalen Slawson | Jaxson Hayes | FA | +0.000 | +0.000 |
| Noah Clowney | Jaxson Hayes | FA | +0.000 | +0.000 |

## Forecast active lineups

- 2026-11-01: Neemias Queta, Desmond Bane, Jake LaRavia

## Assumptions and data quality

- Local caches only; no data fetched and no notifications sent.
- Category marginals use moment/normal approximations. Weekly W/L/D assumes category independence.
- Return dates, rotations and future lineup choices remain model assumptions.
- Live moves are ranked by the lower category-point gain with and without teammate injury spillover; both scenarios must improve their own no-move baseline. This is a conservative sensitivity rule, not a fitted posterior or proven performance improvement.

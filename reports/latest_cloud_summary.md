# NBA Fantasy — cached-data forecast

Generated: 2026-11-01T13:40:43.556824+00:00
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
| PTS | 552 / 480 | 30.47 / 18.22 | 15.77 |
| REB | 222 / 195 | 12.80 / 9.62 | 7.80 |
| AST | 116 / 80 | 6.17 / 2.85 | 3.77 |
| STL | 51 / 29 | 2.39 / 1.21 | 2.12 |
| BLK | 27 / 37 | 1.79 / 0.94 | 1.88 |
| TOV | 65 / 41 | 3.58 / 1.40 | 2.59 |
| FG3M | 71 / 49 | 2.74 / 3.11 | 3.05 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| Jay Huff | Jaxson Hayes | FA | +0.002 | +0.001 |
| Goga Bitadze | Jaxson Hayes | FA | +0.000 | +0.000 |
| Al Horford | Jaxson Hayes | FA | +0.000 | +0.000 |
| Charles Bassey | Jaxson Hayes | FA | +0.000 | +0.000 |
| Noah Clowney | Jaxson Hayes | FA | +0.000 | +0.000 |
| Allen Graves | Jaxson Hayes | FA | +0.000 | +0.000 |
| Gui Santos | Jaxson Hayes | FA | +0.000 | +0.000 |
| Danny Wolf | Jaxson Hayes | FA | +0.000 | +0.000 |

## Forecast active lineups

- 2026-11-01: Neemias Queta, Desmond Bane, Jake LaRavia

## Assumptions and data quality

- Local caches only; no data fetched and no notifications sent.
- Category marginals use moment/normal approximations. Weekly W/L/D assumes category independence.
- Return dates, rotations and future lineup choices remain model assumptions.
- Live moves are ranked by the lower category-point gain with and without teammate injury spillover; both scenarios must improve their own no-move baseline. This is a conservative sensitivity rule, not a fitted posterior or proven performance improvement.

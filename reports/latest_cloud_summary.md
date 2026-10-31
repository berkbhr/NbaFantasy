# NBA Fantasy — cached-data forecast

Generated: 2026-10-31T12:54:24.057243+00:00
Matchup: **Berk's Best Team vs SILE BULLS**
Window: 2026-10-31 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **5.341**.
Expected category points: **5.34 / 9**.
Expected category wins: 5.17; ties: 0.34.
Secondary weekly W/L/D: 70.1% / 23.5% / 6.4%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 74.8% | 0.9% | 24.3% |
| REB | 81.7% | 1.7% | 16.6% |
| AST | 28.9% | 3.4% | 67.8% |
| STL | 49.7% | 7.9% | 42.3% |
| BLK | 75.9% | 7.4% | 16.7% |
| TOV | 49.0% | 6.3% | 44.8% |
| FG3M | 50.9% | 6.3% | 42.9% |
| FG_PCT | 64.9% | 0.0% | 35.1% |
| FT_PCT | 41.5% | 0.0% | 58.5% |

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 0 / 0 | 140.87 / 116.97 | 35.02 |
| REB | 0 / 0 | 56.41 / 42.19 | 15.15 |
| AST | 0 / 0 | 28.25 / 33.57 | 10.44 |
| STL | 0 / 0 | 10.13 / 9.66 | 4.99 |
| BLK | 0 / 0 | 7.44 / 4.28 | 3.80 |
| TOV | 0 / 0 | 14.36 / 14.70 | 6.36 |
| FG3M | 0 / 0 | 14.15 / 13.51 | 6.34 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| No eligible recommendation | — | — | — | — |

## Forecast active lineups

- 2026-10-31: Jarrett Allen, Jaxson Hayes, Dean Wade, Precious Achiuwa, Tyrese Maxey, Ayo Dosunmu, Julian Champagnie, Jabari Smith Jr., James Harden
- 2026-11-01: Neemias Queta, Desmond Bane, Jake LaRavia

## Assumptions and data quality

- Live scoreboard predates the current Eastern game date; synchronize Yahoo again before combining scores with remaining games
- No valid live scoreboard: totals describe remaining games only; in-week add/drop recommendations withheld.
- Local caches only; no data fetched and no notifications sent.
- Category marginals use moment/normal approximations. Weekly W/L/D assumes category independence.
- Return dates, rotations and future lineup choices remain model assumptions.
- Live moves are ranked by the lower category-point gain with and without teammate injury spillover; both scenarios must improve their own no-move baseline. This is a conservative sensitivity rule, not a fitted posterior or proven performance improvement.

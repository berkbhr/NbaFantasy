# NBA Fantasy — cached-data forecast

Generated: 2026-10-30T02:37:40.029174+00:00
Matchup: **Berk's Best Team vs SILE BULLS**
Window: 2026-10-29 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **5.383**.
Expected category points: **5.38 / 9**.
Expected category wins: 5.27; ties: 0.23.
Secondary weekly W/L/D: 72.3% / 23.0% / 4.8%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 73.9% | 0.6% | 25.5% |
| REB | 89.5% | 0.8% | 9.7% |
| AST | 27.5% | 2.3% | 70.3% |
| STL | 49.9% | 5.6% | 44.5% |
| BLK | 75.3% | 5.5% | 19.1% |
| TOV | 54.1% | 4.3% | 41.7% |
| FG3M | 43.6% | 4.3% | 52.1% |
| FG_PCT | 71.5% | 0.0% | 28.5% |
| FT_PCT | 41.3% | 0.0% | 58.7% |

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 0 / 0 | 273.21 / 240.80 | 49.84 |
| REB | 0 / 0 | 109.82 / 83.03 | 21.02 |
| AST | 0 / 0 | 57.92 / 66.39 | 14.97 |
| STL | 0 / 0 | 19.93 / 19.44 | 7.13 |
| BLK | 0 / 0 | 13.41 / 9.26 | 5.33 |
| TOV | 0 / 0 | 28.92 / 30.37 | 9.24 |
| FG3M | 0 / 0 | 27.52 / 28.50 | 9.15 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| No eligible recommendation | — | — | — | — |

## Forecast active lineups

- 2026-10-29: Jarrett Allen, Precious Achiuwa, James Harden
- 2026-10-30: Josh Hart, Neemias Queta, Dean Wade, Tyrese Maxey, Desmond Bane, Ayo Dosunmu, Jabari Smith Jr., Jake LaRavia
- 2026-10-31: Jarrett Allen, Jaxson Hayes, Dean Wade, Precious Achiuwa, Tyrese Maxey, Ayo Dosunmu, Julian Champagnie, Jabari Smith Jr., James Harden
- 2026-11-01: Neemias Queta, Desmond Bane, Jake LaRavia

## Assumptions and data quality

- Today's NBA games have started; partial-game score coverage is unverified, refresh next Eastern pregame day
- No valid live scoreboard: totals describe remaining games only; in-week add/drop recommendations withheld.
- Local caches only; no data fetched and no notifications sent.
- Category marginals use moment/normal approximations. Weekly W/L/D assumes category independence.
- Return dates, rotations and future lineup choices remain model assumptions.
- Live moves are ranked by the lower category-point gain with and without teammate injury spillover; both scenarios must improve their own no-move baseline. This is a conservative sensitivity rule, not a fitted posterior or proven performance improvement.

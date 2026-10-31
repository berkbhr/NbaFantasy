# NBA Fantasy — cached-data forecast

Generated: 2026-10-31T21:46:14.336288+00:00
Matchup: **Berk's Best Team vs Mordor Tulums**
Window: 2026-10-31 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **5.623**.
Expected category points: **5.62 / 9**.
Expected category wins: 5.47; ties: 0.31.
Secondary weekly W/L/D: 77.8% / 16.9% / 5.2%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 81.2% | 0.7% | 18.1% |
| REB | 83.1% | 1.5% | 15.4% |
| AST | 81.1% | 2.7% | 16.2% |
| STL | 75.1% | 6.3% | 18.6% |
| BLK | 52.4% | 8.8% | 38.8% |
| TOV | 25.4% | 5.5% | 69.1% |
| FG3M | 52.8% | 5.9% | 41.4% |
| FG_PCT | 54.4% | 0.0% | 45.6% |
| FT_PCT | 41.2% | 0.0% | 58.8% |

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 0 / 0 | 142.78 / 108.36 | 38.27 |
| REB | 0 / 0 | 57.08 / 41.32 | 15.94 |
| AST | 0 / 0 | 28.58 / 19.56 | 9.66 |
| STL | 0 / 0 | 10.30 / 6.63 | 4.66 |
| BLK | 0 / 0 | 7.55 / 6.78 | 4.44 |
| TOV | 0 / 0 | 14.48 / 10.95 | 6.09 |
| FG3M | 0 / 0 | 14.44 / 13.48 | 6.72 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| No eligible recommendation | — | — | — | — |

## Forecast active lineups

- 2026-10-31: Jarrett Allen, Jaxson Hayes, Dean Wade, Precious Achiuwa, Tyrese Maxey, Ayo Dosunmu, Julian Champagnie, Jabari Smith Jr., James Harden
- 2026-11-01: Neemias Queta, Desmond Bane, Jake LaRavia

## Assumptions and data quality

- Today's NBA games have started; partial-game score coverage is unverified, refresh next Eastern pregame day
- No valid live scoreboard: totals describe remaining games only; in-week add/drop recommendations withheld.
- Local caches only; no data fetched and no notifications sent.
- Category marginals use moment/normal approximations. Weekly W/L/D assumes category independence.
- Return dates, rotations and future lineup choices remain model assumptions.
- Live moves are ranked by the lower category-point gain with and without teammate injury spillover; both scenarios must improve their own no-move baseline. This is a conservative sensitivity rule, not a fitted posterior or proven performance improvement.

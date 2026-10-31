# NBA Fantasy — cached-data forecast

Generated: 2026-10-31T17:19:34.689688+00:00
Matchup: **Berk's Best Team vs SILE BULLS**
Window: 2026-10-31 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **5.431**.
Expected category points: **5.43 / 9**.
Expected category wins: 5.26; ties: 0.33.
Secondary weekly W/L/D: 72.5% / 21.5% / 6.0%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 77.1% | 0.8% | 22.0% |
| REB | 83.0% | 1.6% | 15.4% |
| AST | 30.8% | 3.4% | 65.8% |
| STL | 51.4% | 7.8% | 40.8% |
| BLK | 76.8% | 7.2% | 16.1% |
| TOV | 47.6% | 6.2% | 46.2% |
| FG3M | 53.3% | 6.1% | 40.5% |
| FG_PCT | 64.7% | 0.0% | 35.3% |
| FT_PCT | 41.8% | 0.0% | 58.2% |

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 0 / 0 | 144.91 / 117.97 | 35.56 |
| REB | 0 / 0 | 57.69 / 42.59 | 15.32 |
| AST | 0 / 0 | 29.03 / 33.83 | 10.56 |
| STL | 0 / 0 | 10.44 / 9.76 | 5.05 |
| BLK | 0 / 0 | 7.62 / 4.31 | 3.83 |
| TOV | 0 / 0 | 14.69 / 14.81 | 6.42 |
| FG3M | 0 / 0 | 14.69 / 13.65 | 6.44 |

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

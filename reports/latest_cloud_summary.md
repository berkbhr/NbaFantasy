# NBA Fantasy — cached-data forecast

Generated: 2026-11-01T02:15:14.053849+00:00
Matchup: **Berk's Best Team vs Mordor Tulums**
Window: 2026-10-31 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **5.929**.
Expected category points: **5.93 / 9**.
Expected category wins: 5.79; ties: 0.29.
Secondary weekly W/L/D: 85.7% / 10.4% / 3.9%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 89.8% | 0.5% | 9.7% |
| REB | 86.7% | 1.3% | 12.0% |
| AST | 89.6% | 1.8% | 8.5% |
| STL | 79.9% | 5.6% | 14.5% |
| BLK | 54.1% | 8.8% | 37.1% |
| TOV | 19.4% | 5.0% | 75.7% |
| FG3M | 61.0% | 5.8% | 33.2% |
| FG_PCT | 55.2% | 0.0% | 44.8% |
| FT_PCT | 42.9% | 0.0% | 57.1% |

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 0 / 0 | 143.76 / 97.27 | 36.22 |
| REB | 0 / 0 | 57.45 / 39.41 | 15.78 |
| AST | 0 / 0 | 28.84 / 16.85 | 9.11 |
| STL | 0 / 0 | 10.36 / 6.03 | 4.56 |
| BLK | 0 / 0 | 7.58 / 6.63 | 4.42 |
| TOV | 0 / 0 | 14.63 / 9.99 | 5.94 |
| FG3M | 0 / 0 | 14.49 / 12.18 | 6.47 |

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

# NBA Fantasy — cached-data forecast

Generated: 2026-10-31T02:24:13.297314+00:00
Matchup: **Berk's Best Team vs Mordor Tulums**
Window: 2026-10-30 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **6.517**.
Expected category points: **6.52 / 9**.
Expected category wins: 6.44; ties: 0.15.
Secondary weekly W/L/D: 97.1% / 2.0% / 0.9%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 98.5% | 0.1% | 1.4% |
| REB | 97.2% | 0.3% | 2.5% |
| AST | 99.0% | 0.2% | 0.8% |
| STL | 91.5% | 2.3% | 6.1% |
| BLK | 70.3% | 6.3% | 23.4% |
| TOV | 7.0% | 2.0% | 91.0% |
| FG3M | 79.3% | 3.3% | 17.4% |
| FG_PCT | 52.3% | 0.0% | 47.7% |
| FT_PCT | 49.4% | 0.0% | 50.6% |

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 0 / 0 | 239.88 / 142.07 | 44.84 |
| REB | 0 / 0 | 94.14 / 57.71 | 18.87 |
| AST | 0 / 0 | 50.77 / 23.23 | 11.67 |
| STL | 0 / 0 | 17.85 / 9.24 | 5.90 |
| BLK | 0 / 0 | 11.73 / 8.48 | 5.16 |
| TOV | 0 / 0 | 24.71 / 14.22 | 7.44 |
| FG3M | 0 / 0 | 25.75 / 18.47 | 8.29 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| No eligible recommendation | — | — | — | — |

## Forecast active lineups

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

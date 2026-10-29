# NBA Fantasy — cached-data forecast

Generated: 2026-10-29T02:28:18.124367+00:00
Matchup: **Berk's Best Team vs SILE BULLS**
Window: 2026-10-28 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **5.623**.
Expected category points: **5.62 / 9**.
Expected category wins: 5.53; ties: 0.19.
Secondary weekly W/L/D: 78.3% / 18.1% / 3.5%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 85.6% | 0.4% | 14.0% |
| REB | 88.6% | 0.7% | 10.6% |
| AST | 35.9% | 2.1% | 62.1% |
| STL | 48.4% | 4.5% | 47.0% |
| BLK | 75.9% | 4.5% | 19.6% |
| TOV | 48.1% | 3.5% | 48.4% |
| FG3M | 52.8% | 3.6% | 43.6% |
| FG_PCT | 71.9% | 0.0% | 28.1% |
| FT_PCT | 45.6% | 0.0% | 54.4% |

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 0 / 0 | 405.69 / 340.77 | 60.61 |
| REB | 0 / 0 | 155.20 / 123.80 | 25.61 |
| AST | 0 / 0 | 87.44 / 93.59 | 18.35 |
| STL | 0 / 0 | 29.00 / 28.85 | 8.77 |
| BLK | 0 / 0 | 19.18 / 14.08 | 6.55 |
| TOV | 0 / 0 | 44.38 / 44.34 | 11.50 |
| FG3M | 0 / 0 | 40.64 / 39.37 | 11.03 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| No eligible recommendation | — | — | — | — |

## Forecast active lineups

- 2026-10-28: Jarrett Allen, Josh Hart, Jaxson Hayes, Tyrese Maxey, Desmond Bane, Ayo Dosunmu, Julian Champagnie, Jabari Smith Jr., Jake LaRavia, James Harden
- 2026-10-29: Jarrett Allen, Precious Achiuwa, James Harden
- 2026-10-30: Josh Hart, Neemias Queta, Tyrese Maxey, Desmond Bane, Ayo Dosunmu, Jabari Smith Jr., Jake LaRavia, Bilal Coulibaly
- 2026-10-31: Jarrett Allen, Jaxson Hayes, Precious Achiuwa, Tyrese Maxey, Ayo Dosunmu, Julian Champagnie, Jabari Smith Jr., James Harden
- 2026-11-01: Neemias Queta, Desmond Bane, Jake LaRavia

## Assumptions and data quality

- Today's NBA games have started; partial-game score coverage is unverified, refresh next Eastern pregame day
- No valid live scoreboard: totals describe remaining games only; in-week add/drop recommendations withheld.
- Local caches only; no data fetched and no notifications sent.
- Category marginals use moment/normal approximations. Weekly W/L/D assumes category independence.
- Return dates, rotations and future lineup choices remain model assumptions.
- Live moves are ranked by the lower category-point gain with and without teammate injury spillover; both scenarios must improve their own no-move baseline. This is a conservative sensitivity rule, not a fitted posterior or proven performance improvement.

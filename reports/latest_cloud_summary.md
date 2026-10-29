# NBA Fantasy — cached-data forecast

Generated: 2026-10-29T10:20:47.781177+00:00
Matchup: **Berk's Best Team vs SILE BULLS**
Window: 2026-10-29 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **5.282**.
Expected category points: **5.28 / 9**.
Expected category wins: 5.16; ties: 0.24.
Secondary weekly W/L/D: 69.6% / 25.4% / 5.0%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 70.7% | 0.7% | 28.6% |
| REB | 88.3% | 0.9% | 10.8% |
| AST | 25.7% | 2.2% | 72.1% |
| STL | 48.0% | 5.6% | 46.4% |
| BLK | 74.4% | 5.7% | 19.9% |
| TOV | 55.6% | 4.2% | 40.2% |
| FG3M | 41.0% | 4.3% | 54.6% |
| FG_PCT | 71.4% | 0.0% | 28.6% |
| FT_PCT | 41.1% | 0.0% | 58.9% |

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 0 / 0 | 268.53 / 241.00 | 49.53 |
| REB | 0 / 0 | 108.14 / 82.80 | 20.85 |
| AST | 0 / 0 | 57.11 / 66.33 | 14.92 |
| STL | 0 / 0 | 19.53 / 19.39 | 7.08 |
| BLK | 0 / 0 | 13.21 / 9.23 | 5.30 |
| TOV | 0 / 0 | 28.58 / 30.37 | 9.21 |
| FG3M | 0 / 0 | 26.95 / 28.51 | 9.10 |

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

- NBA schedule clock predates current Eastern day; refresh schedule
- No valid live scoreboard: totals describe remaining games only; in-week add/drop recommendations withheld.
- Local caches only; no data fetched and no notifications sent.
- Category marginals use moment/normal approximations. Weekly W/L/D assumes category independence.
- Return dates, rotations and future lineup choices remain model assumptions.
- Live moves are ranked by the lower category-point gain with and without teammate injury spillover; both scenarios must improve their own no-move baseline. This is a conservative sensitivity rule, not a fitted posterior or proven performance improvement.

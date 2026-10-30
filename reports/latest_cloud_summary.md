# NBA Fantasy — cached-data forecast

Generated: 2026-10-30T08:29:46.935179+00:00
Matchup: **Berk's Best Team vs SILE BULLS**
Window: 2026-10-30 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **4.923**.
Expected category points: **4.92 / 9**.
Expected category wins: 4.79; ties: 0.26.
Secondary weekly W/L/D: 59.4% / 34.7% / 5.9%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 60.2% | 0.8% | 38.9% |
| REB | 72.4% | 1.7% | 25.9% |
| AST | 17.0% | 1.9% | 81.2% |
| STL | 40.6% | 5.8% | 53.6% |
| BLK | 64.8% | 7.0% | 28.2% |
| TOV | 66.6% | 4.1% | 29.3% |
| FG3M | 42.1% | 4.5% | 53.3% |
| FG_PCT | 69.3% | 0.0% | 30.7% |
| FT_PCT | 46.4% | 0.0% | 53.6% |

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 0 / 0 | 232.85 / 220.38 | 46.18 |
| REB | 0 / 0 | 91.49 / 79.37 | 19.52 |
| AST | 0 / 0 | 49.36 / 62.33 | 14.11 |
| STL | 0 / 0 | 17.23 / 18.34 | 6.77 |
| BLK | 0 / 0 | 11.40 / 8.98 | 5.04 |
| TOV | 0 / 0 | 24.03 / 28.22 | 8.62 |
| FG3M | 0 / 0 | 24.94 / 26.17 | 8.71 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| No eligible recommendation | — | — | — | — |

## Forecast active lineups

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

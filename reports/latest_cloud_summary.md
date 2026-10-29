# NBA Fantasy — cached-data forecast

Generated: 2026-10-29T10:32:40.827473+00:00
Matchup: **Berk's Best Team vs Mordor Tulums**
Window: 2026-10-29 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **4.995**.
Expected category points: **5.00 / 9**.
Expected category wins: 4.92; ties: 0.14.
Secondary weekly W/L/D: 65.0% / 30.7% / 4.3%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 23.4% | 0.6% | 76.0% |
| REB | 70.8% | 1.6% | 27.6% |
| AST | 98.9% | 0.2% | 0.9% |
| STL | 97.8% | 0.7% | 1.6% |
| BLK | 27.5% | 6.0% | 66.5% |
| TOV | 3.2% | 0.9% | 95.9% |
| FG3M | 48.7% | 4.2% | 47.1% |
| FG_PCT | 32.6% | 0.0% | 67.4% |
| FT_PCT | 89.6% | 0.0% | 10.4% |

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 206 / 285 | 268.53 / 227.12 | 52.55 |
| REB | 109 / 119 | 108.14 / 85.73 | 21.71 |
| AST | 54 / 39 | 57.11 / 40.32 | 13.72 |
| STL | 26 / 17 | 19.53 / 14.67 | 6.67 |
| BLK | 15 / 19 | 13.21 / 12.19 | 5.82 |
| TOV | 26 / 16 | 28.58 / 22.95 | 8.69 |
| FG3M | 30 / 28 | 26.95 / 28.77 | 9.50 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| Jay Huff | Jaxson Hayes | Waiver: Oct 30 | +0.322 | +0.265 |
| Ryan Kalkbrenner | Jaxson Hayes | FA | +0.160 | +0.160 |
| Isaiah Jackson | Jaxson Hayes | Waiver: Oct 30 | +0.136 | +0.136 |
| Jarace Walker | Jaxson Hayes | FA | +0.153 | +0.134 |
| Isaiah Stewart | Jaxson Hayes | FA | +0.116 | +0.116 |
| Jeremiah Fears | Jaxson Hayes | FA | +0.106 | +0.106 |
| Collin Sexton | Jaxson Hayes | FA | +0.105 | +0.098 |
| Adem Bona | Jaxson Hayes | FA | +0.117 | +0.095 |

## Forecast active lineups

- 2026-10-29: Jarrett Allen, Precious Achiuwa, James Harden
- 2026-10-30: Josh Hart, Neemias Queta, Dean Wade, Tyrese Maxey, Desmond Bane, Ayo Dosunmu, Jabari Smith Jr., Jake LaRavia
- 2026-10-31: Jarrett Allen, Jaxson Hayes, Dean Wade, Precious Achiuwa, Tyrese Maxey, Ayo Dosunmu, Julian Champagnie, Jabari Smith Jr., James Harden
- 2026-11-01: Neemias Queta, Desmond Bane, Jake LaRavia

## Assumptions and data quality

- Local caches only; no data fetched and no notifications sent.
- Category marginals use moment/normal approximations. Weekly W/L/D assumes category independence.
- Return dates, rotations and future lineup choices remain model assumptions.
- Live moves are ranked by the lower category-point gain with and without teammate injury spillover; both scenarios must improve their own no-move baseline. This is a conservative sensitivity rule, not a fitted posterior or proven performance improvement.

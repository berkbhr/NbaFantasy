# NBA Fantasy — cached-data forecast

Generated: 2026-10-29T22:53:28.195661+00:00
Matchup: **Berk's Best Team vs Mordor Tulums**
Window: 2026-10-29 – 2026-11-01

Decision objective: `category_points` (regular_season).
Objective value: **5.345**.
Expected category points: **5.35 / 9**.
Expected category wins: 5.27; ties: 0.14.
Secondary weekly W/L/D: 76.4% / 20.0% / 3.6%.

| Category | Win | Tie | Loss |
|---|---:|---:|---:|
| PTS | 30.0% | 0.7% | 69.3% |
| REB | 83.7% | 1.1% | 15.2% |
| AST | 99.2% | 0.2% | 0.7% |
| STL | 98.4% | 0.5% | 1.1% |
| BLK | 38.4% | 6.9% | 54.7% |
| TOV | 2.4% | 0.7% | 96.9% |
| FG3M | 50.5% | 4.2% | 45.3% |
| FG_PCT | 35.5% | 0.0% | 64.5% |
| FT_PCT | 89.3% | 0.0% | 10.7% |

## Why the weekly forecast changed

Sequential attribution from the previous archived forecast; not causal identification.

REB %70 → %84: skor +0, kalan beklenti +14, maçların tamamlanması +0 yüzde puan.
Eklenen skor sen/rakip: 0/0; önceki aktif kadro planının beklentisi: 0.0/0.0.
BLK %27 → %38: skor +0, kalan beklenti +12, maçların tamamlanması +0 yüzde puan.
Eklenen skor sen/rakip: 0/0; önceki aktif kadro planının beklentisi: 0.0/0.0.
- Remaining opponent plan: Robert Williams III, REB expectation change -8.7; active games 2 → 2; status HEALTHY → DOUBTFUL.
- Remaining mine plan: Dean Wade, REB expectation change +0.5; active games 2 → 2; status HEALTHY → HEALTHY.
- Remaining opponent plan: Robert Williams III, BLK expectation change -1.8; active games 2 → 2; status HEALTHY → DOUBTFUL.
- Remaining mine plan: Tyrese Maxey, BLK expectation change +0.1; active games 2 → 2; status HEALTHY → HEALTHY.
Player examples are NBA boxscores for the old planned lineup; actual Yahoo starters can differ.

## Realized scores and remaining projections

Scores are fixed observations; uncertainty belongs to future games. Remaining values reflect projected active lineups, not Yahoo's raw game counts.

| Category | Actual: you / opponent | Remaining mean: you / opponent | Final difference SD |
|---|---:|---:|---:|
| PTS | 206 / 285 | 272.64 / 220.79 | 52.85 |
| REB | 109 / 119 | 109.64 / 77.84 | 21.69 |
| AST | 54 / 39 | 57.75 / 39.34 | 13.72 |
| STL | 26 / 17 | 19.88 / 14.15 | 6.67 |
| BLK | 15 / 19 | 13.39 / 10.57 | 5.69 |
| TOV | 26 / 16 | 28.84 / 22.12 | 8.67 |
| FG3M | 30 / 28 | 27.45 / 28.83 | 9.56 |

## Alternative add/drop recommendations

| Add | Drop | Eligibility | Δ category_points | Conservative ranking gain |
|---|---|---|---:|---:|
| Jay Huff | Jaxson Hayes | Waiver: Oct 30 | +0.337 | +0.267 |
| Ryan Kalkbrenner | Jaxson Hayes | FA | +0.166 | +0.166 |
| Jeremiah Fears | Jaxson Hayes | FA | +0.167 | +0.147 |
| Isaiah Stewart | Jaxson Hayes | FA | +0.122 | +0.122 |
| Isaiah Jackson | Jaxson Hayes | Waiver: Oct 30 | +0.121 | +0.121 |
| Jarace Walker | Jaxson Hayes | FA | +0.146 | +0.119 |
| Sam Merrill | Jaxson Hayes | FA | +0.117 | +0.117 |
| Noah Clowney | Jaxson Hayes | FA | +0.113 | +0.113 |

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

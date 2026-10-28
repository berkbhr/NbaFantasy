# Automated tests

Run from the repository root:

```powershell
python -m unittest discover -s tests -t . -v
python -m ruff check src tests research
python -m ruff format --check src tests research
```

`-t .` keeps `tests.research` distinct from the top-level `research` package.

| Folder | Purpose |
|---|---|
| `unit/` | Probability math, player model, lineup decisions, injury storage, score/time contracts |
| `integration/` | Yahoo synchronization, live ingestion, notifications and immutable archive round trips |
| `research/` | Calibration, chronological validation and historical backtest contracts |
| `helpers.py` | Shared in-memory fixtures; tests do not import helpers from other test modules |

Tests use temporary fixtures or local historical caches. They do not send
Telegram messages, modify the user's roster, or launch long tuning runs.
Keep regression tests in Git so GitHub Actions can catch regressions.

Experiment runners and output retention rules are documented in
[`research/README.md`](../research/README.md). The continuing analysis stays in
[`reports/research_stage1/report.md`](../reports/research_stage1/report.md).

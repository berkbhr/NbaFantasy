# Research workspace

Offline experiment entry points are separate from the live `src` package:

| Command | Purpose |
|---|---|
| `python -m research.common --pilot-days 14` | Historical data audit and bounded player pilot |
| `python -m research.pilot` | Small synthetic-roster timing pilot; prints JSON without sending messages |
| `python -m research.roster_backtest` | Frozen-protocol historical roster experiment |
| `python -m research.streaming_sensitivity RUN_ID` | Stronger streaming controls for a recorded experiment |
| `python -m research.injury_depth` | Pre-cutoff medical/IL legality and timing pilot; no outcome-performance claim |

New generated runs go to **`research/runs/`**, ignored by Git. The
streaming command looks there first, then in the pinned historical archive.
Promote only a selected run's small protocol, summary and necessary compressed
evidence to the published archive. Do not add every retry or temporary log.
`evidence/` holds selected small records from this workspace; `runs/` remains
local. The injury/IL pilot's retained protocol and results total about 3 KB.

Existing pinned evidence remains at `data/archive/experiments/` and
`reports/research_stage1/` to preserve prior references and immutable records.
Older calibration summaries remain in their documented report folders.
The single continuing report is
[`reports/research_stage1/report.md`](../reports/research_stage1/report.md).
This index is not a second results report.

The previous entry points `src.research`, `src.roster_pilot`,
`src.roster_backtest`, and `src.streaming_sensitivity` moved here. Historical
manifests deliberately keep their original paths and byte hashes. Reproducing
those exact runs requires their original code revision (for example `eeba686`),
not silently substituting today's changed files. New manifests hash both
`src/` and `research/` sources.

Shared mathematical routines remain in `src`; research calls the same player
and matchup implementation as serving. Research output does not automatically
promote a policy or change live configuration.

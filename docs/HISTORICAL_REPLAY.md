# Historical replay source boundary

`LiveDraftAssistant(historical_replay=True)` never constructs `InjuryTracker`
and never reads the live `player_positions.parquet`, including when
`use_live_injuries=True` or an `injury_db_path` was also passed. Live mode retains
its current injury and position loaders.

Without historical sources, replay uses no explicit injury evidence and pooled
position priors. Missing fantasy positions remain generic `UTIL` in the matchup
engine; this does **not** reconstruct historical roster eligibility. A default
in-memory `HEALTHY` status means no admitted injury evidence, not verified health.
The existing learned availability/DNP policy still applies to game forecasts.

To admit historical evidence, explicitly pass `replay_as_of` and records (a list
of dictionaries or a DataFrame) as `historical_injuries` / `historical_positions`:

```python
assistant = LiveDraftAssistant(
    prior_season="2024_25",
    historical_replay=True,
    replay_as_of="2025-10-20T12:00:00Z",
    historical_injuries=[{
        "player_id": 123, "status": "OUT",
        "effective_at": "2025-10-19T18:00:00Z",
        "observed_at": "2025-10-19T18:15:00Z",
    }],
    historical_positions=[{
        "PLAYER_ID": 123, "POSITION": "G",
        "effective_at": "2025-10-01T00:00:00Z",
        "observed_at": "2025-10-01T09:00:00Z",
    }],
)
```

`effective_at` identifies when the fact applies; `observed_at` identifies its
documented capture/availability time. Both must be valid and no later than the
cutoff (inclusive). Naive timestamps mean UTC. Rows missing either timestamp,
invalid rows, future records and ambiguous conflicting versions are ignored.
The latest eligible effective version, then capture version, wins per player.
Empty eligible sources use the same fallback. Explicit sources without a valid
cutoff raise `ValueError`; historical sources passed to live mode also fail.
The engine rejects a forecast cutoff or game date earlier than its admitted
evidence. Build a new assistant to replay an earlier time.

No current database snapshot is automatically promoted into historical evidence.
A current row's `updated_at`, a season in a filename, or a backdated publisher
date does not establish historical availability. Callers must retain a trusted
archive/capture trail; the code checks chronology, not provenance authenticity.
This change does not supply a complete historical injury/position archive, audit
every other historical input, or make the live `build_local_forecast(now=...)`
API a historical replay API. Completed-season priors, team mapping, schedules,
ownership and outcomes still require their own point-in-time evidence.

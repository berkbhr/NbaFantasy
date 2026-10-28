"""Read-only historical audit and bounded pilot; never writes serving policies."""

import argparse
import hashlib
import json
import platform
import subprocess
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from src.calibrate import metrics, replay
from src.model_policy import load_model_policy
from src.snapshots import validate_live_snapshot

ROOT = Path(__file__).resolve().parents[1]
SEASONS = ("2022_23", "2023_24", "2024_25", "2025_26")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_logs(frame):
    """Report integrity before any silent deduplication or training."""
    required = [
        "PLAYER_ID",
        "GAME_ID",
        "GAME_DATE",
        "TEAM_ID",
        "MIN",
        "PTS",
        "REB",
        "AST",
        "STL",
        "BLK",
        "TOV",
        "FG3M",
        "FGM",
        "FGA",
        "FTM",
        "FTA",
    ]
    missing = sorted(set(required) - set(frame))
    if missing:
        return {"valid": False, "missing_columns": missing}
    numeric = frame[required[4:]].apply(pd.to_numeric, errors="coerce")
    dates = pd.to_datetime(frame.GAME_DATE, errors="coerce")
    issues = {
        "empty_cache": int(frame.empty),
        "missing_identity_rows": int(
            frame[["PLAYER_ID", "GAME_ID", "TEAM_ID"]].isna().any(axis=1).sum()
        ),
        "duplicate_player_games": int(frame.duplicated(["PLAYER_ID", "GAME_ID"]).sum()),
        "invalid_dates": int(dates.isna().sum()),
        "nonfinite_or_negative_stat_rows": int(
            (~np.isfinite(numeric) | (numeric < 0)).any(axis=1).sum()
        ),
        "invalid_shooting_rows": int(
            (
                (numeric.FGM > numeric.FGA)
                | (numeric.FTM > numeric.FTA)
                | (numeric.FG3M > numeric.FGM)
            ).sum()
        ),
        "points_identity_errors": int(
            (numeric.PTS != 2 * numeric.FGM + numeric.FG3M + numeric.FTM).sum()
        ),
    }
    return {
        "valid": not any(issues.values()),
        "rows": len(frame),
        "games": int(frame.GAME_ID.nunique()),
        "players": int(frame.PLAYER_ID.nunique()),
        "first_date": str(dates.min().date()),
        "last_date": str(dates.max().date()),
        "issues": issues,
    }


def protocol(days):
    if not 1 <= days <= 28:
        raise ValueError("Pilot must be between 1 and28 calendar days")
    return {
        "version": 1,
        "purpose": "Infrastructure, integrity and timing pilot; no tuning or promotion",
        "scope": "Played-game player rates/role only; no availability, injuries, fantasy decisions or Monte Carlo",
        "objective": "sum(P(category win)+0.5P(category tie))",
        "development": {"target": "2024_25", "prior": "2023_24", "older_blend_prior": "2022_23"},
        "assessment": {
            "target": "2025_26",
            "prior": "2024_25",
            "status": "Previously inspected, retrospective",
        },
        "pilot": {
            "season": "2024_25",
            "calendar_days": days,
            "policies": ["active", "same_policy_recent_blend"],
            "selection": "None; comparison is descriptive only",
        },
        "roster_seeds": {
            "development": list(range(1000, 1020)),
            "assessment": list(range(2000, 2020)),
            "executed": False,
        },
        "future_confirmation": "Only outcomes after a separately frozen candidate and prospective protocol",
        "blocks": "Future training targets must end before validation cutoff; no random player-row split",
    }


def pilot(frame, policy):
    """Reuse production player/role math; isolate a future-label perturbation."""
    start = perf_counter()
    primary = replay("2024_25", policy, logs=frame)
    primary_seconds = perf_counter() - start
    start = perf_counter()
    shadow = replay("2024_25", replace(policy, role="recent_blend"), logs=frame)
    shadow_seconds = perf_counter() - start
    last = pd.to_datetime(frame.GAME_DATE).max()
    altered = frame.copy()
    altered.loc[pd.to_datetime(altered.GAME_DATE) == last, "BLK"] += 100
    start = perf_counter()
    perturbed = replay("2024_25", policy, logs=altered)
    forecast_columns = ["pid", "gid", "date", "FG_a", "FG_b", "FT_a", "FT_b"]
    forecast_columns += [
        s + suffix
        for s in ("PTS", "REB", "AST", "STL", "BLK", "FG3M", "TOV")
        for suffix in ("_mu", "_var")
    ]
    # All forecasts, including those preceding the mutated same-day labels,
    # must be unchanged. Only scoring targets have been changed here.
    pd.testing.assert_frame_equal(primary[forecast_columns], perturbed[forecast_columns])
    return (
        primary,
        shadow,
        {
            "scored_player_games": len(primary),
            "dates": int(primary.date.nunique()),
            "active": metrics(primary),
            "recent_blend": metrics(shadow),
            "seconds": {
                "active": primary_seconds,
                "recent_blend": shadow_seconds,
                "future_label_probe": perf_counter() - start,
            },
            "leakage_probe": {
                "passed": True,
                "changed_label_date": str(last.date()),
                "change": "Add100 BLK to final pilot day in memory only",
                "scope": "Player means, variances and shooting precision; does not certify all pipelines",
            },
            "selection_or_deployment": False,
        },
    )


def run(days=14, output=None):
    started = perf_counter()
    now = datetime.now(timezone.utc)
    output = Path(output) if output else ROOT / "research/runs" / now.strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True, exist_ok=False)
    policy = load_model_policy()
    sources = sorted((ROOT / "src").glob("*.py")) + sorted((ROOT / "research").glob("*.py"))
    sources += [
        ROOT / "config" / n
        for n in (
            "model_policy.json",
            "rotation_policy.json",
            "rotation_candidate.json",
            "prospective_protocol.json",
        )
    ]
    sources += [ROOT / "data/raw" / f"player_logs_{s}.parquet" for s in SEASONS]
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in sources if p.exists()}
    manifest = {
        "created_at": now.isoformat(),
        "code_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "python": platform.python_version(),
        "source_and_data_sha256": hashes,
        "source_version_note": "Hashes include uncommitted source changes; Git revision alone is insufficient",
        "policy": policy.to_dict(),
        "protocol": protocol(days),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    audits, frames = {}, {}
    for season in SEASONS:
        frames[season] = pd.read_parquet(ROOT / "data/raw" / f"player_logs_{season}.parquet")
        audits[season] = audit_logs(frames[season])
    for earlier, later in zip(SEASONS, SEASONS[1:]):
        if audits[earlier].get("last_date", "") >= audits[later].get("first_date", ""):
            raise ValueError("Prior and target cache periods overlap")
    (output / "data_audit.json").write_text(json.dumps(audits, indent=2), encoding="utf-8")
    if not all(a["valid"] for a in audits.values()):
        raise ValueError("Data integrity audit failed; pilot withheld, see data_audit.json")
    live = ROOT / "data/processed/live_matchup.json"
    live_audit = {"present": live.exists()}
    if live.exists():
        try:
            validate_live_snapshot(json.loads(live.read_text(encoding="utf-8")), now)
            live_audit["dated_score_guard"] = "passed"
        except ValueError as exc:
            live_audit["dated_score_guard"] = str(exc)
    # The daily schedule cannot establish intraday remaining game time.
    live_audit["intraday_game_coverage"] = (
        "Not validated: current caches have no explicit covered-game/tipoff contract"
    )
    (output / "live_contract_audit.json").write_text(
        json.dumps(live_audit, indent=2), encoding="utf-8"
    )
    frame = frames["2024_25"]
    dates = pd.to_datetime(frame.GAME_DATE)
    frame = frame[dates < dates.min() + pd.Timedelta(days=days)].copy()
    primary, shadow, report = pilot(frame, policy)
    if any(sha(ROOT / p) != value for p, value in hashes.items()):
        raise RuntimeError("Sources/data changed during pilot; results cannot be accepted")
    report["total_wall_seconds"] = perf_counter() - started
    report["limitations"] = [
        "Early-season2024 sample is not a full-season performance estimate",
        "No full Yahoo, injury or roster-robustness validation performed",
        "Count NLL is a moment-matched NB diagnostic; shot NLL conditions on actual attempts",
    ]
    primary.to_csv(output / "active.csv.gz", index=False)
    shadow.to_csv(output / "recent_blend.csv.gz", index=False)
    (output / "pilot.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), **report}, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-days", type=int, default=14)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    run(args.pilot_days, args.output)

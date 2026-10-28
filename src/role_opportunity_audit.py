"""Two fixed role-opportunity heuristics, not a player-specific rule fit.

Both historical periods have been inspected. This audit cannot establish a
causal or probability-calibrated minute uplift for live injuries.
"""

import hashlib
import json
from pathlib import Path

import numpy as np

from .injury_experiments import load_reports, paired_gate, spillover_replay

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/role_opportunity"
PROTOCOL = {
    "arms": {
        "current": "no special low-role cap; existing total +10 heuristic ceiling",
        "legacy_cap2": "if observed GP>=2 and observed MPG<10, total uplift capped at2",
    },
    "periods": {"selection": "2024_25", "assessment": "2025_26"},
    "cohorts_fixed_before_run": [
        "all",
        "low_role_GP2plus_MPG_under10",
        "same_low_role_and_prior_MPG25plus",
    ],
    "metrics": ["minute MAE", "overprediction mean", "underprediction mean", "PTS MAE"],
    "decision": "Same historical paired-week gates; >=1000 rows required. No automatic live policy change.",
    "scope": "Retrospective pooled-position past-roster proxy; conditional on playing. Not a new holdout.",
    "not_estimated": "Probability a low role is temporary vs persistent, player-specific injury return ramps, causal spillover",
}


def summary(frame):
    if frame.empty:
        return {
            "n": 0,
            "minute_mae": None,
            "overprediction": None,
            "underprediction": None,
            "pts_mae": None,
        }
    error = frame.predicted_minutes - frame.actual_minutes
    return {
        "n": len(frame),
        "minute_mae": float(abs(error).mean()),
        "overprediction": float(np.maximum(error, 0).mean()),
        "underprediction": float(np.maximum(-error, 0).mean()),
        "pts_mae": float(frame.companion.mean()),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "protocol.json").write_text(json.dumps(PROTOCOL, indent=2), encoding="utf-8")
    sources = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
        for p in (ROOT / "src").glob("*.py")
    }
    inputs = json.loads(
        (ROOT / "reports/injury_calibration/provenance.json").read_text(encoding="utf-8")
    )["inputs"]
    if any(
        hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != checksum
        for path, checksum in inputs.items()
    ):
        raise ValueError("Historical inputs changed; rebuild input provenance first")
    results = {"deployed_change": False, "periods": {}}
    for season in ("2024_25", "2025_26"):
        reports = load_reports(ROOT, season)
        base = spillover_replay(ROOT, season, reports)[1.0]
        capped = spillover_replay(ROOT, season, reports, low_role_boost_cap=2)[1.0]
        if not base[["date", "pid", "game_id"]].equals(capped[["date", "pid", "game_id"]]):
            raise ValueError("Counterfactual populations differ")
        masks = {
            "all": base.observed_gp >= 0,
            "low_role": (base.observed_gp >= 2) & (base.observed_mpg < 10),
        }
        masks["strong_prior_low_role"] = masks["low_role"] & (base.prior_mpg >= 25)
        results["periods"][season] = {}
        for cohort, mask in masks.items():
            a, b = base[mask].reset_index(drop=True), capped[mask].reset_index(drop=True)
            results["periods"][season][cohort] = {
                "current": summary(a),
                "legacy_cap2": summary(b),
                "gate": paired_gate(a, b),
            }
        base.to_csv(OUT / f"current_{season}.csv.gz", index=False)
        capped.to_csv(OUT / f"legacy_cap2_{season}.csv.gz", index=False)
    # Report both periods; the affected cohort must pass both, not just the
    # whole-pool mean dominated by players to whom the cap does not apply.
    results["affected_cohort_passes_both"] = all(
        results["periods"][s]["low_role"]["gate"]["accepted"] for s in results["periods"]
    )
    final_sources = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
        for p in (ROOT / "src").glob("*.py")
    }
    if sources != final_sources:
        raise ValueError("Source changed during audit; rerun")
    results["source_sha256_LF"] = sources
    results["input_sha256"] = inputs
    results["protocol_sha256_LF"] = hashlib.sha256(
        (OUT / "protocol.json").read_text(encoding="utf-8").encode()
    ).hexdigest()
    (OUT / "results.json").write_text(
        json.dumps(results, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(json.dumps(results["periods"], indent=2), flush=True)


if __name__ == "__main__":
    main()

"""Noon ET availability calibration on expanded, explicit final-roster labels.

A noon same-day calibration is not silently deployed at other horizons.
"""

import hashlib
import json
from pathlib import Path

from .injury_experiments import (
    attach_causal_availability,
    availability_labels,
    load_reports,
    online_availability,
    paired_gate,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/availability_tuning"
PROTOCOL = {
    "selection_season": "2024_25",
    "assessment_season": "2025_26",
    "strength_candidates": [20, 60],
    "cutoff": "Noon America/New_York, same-day games after cutoff only",
    "baseline": "Causal BayesianPlayer availability/status replay, no future game outcomes",
    "primary": "Brier",
    "guard": "Log loss <=0.5% worse, both time halves, paired weekly95%CI, min1000 rows",
    "selection": "Freeze one passing selection winner before assessing it; no runner-up search",
    "deployment": "Research candidate only: live 1-day forecasts and other report times require their own horizon validation",
    "scope": "Retrospective, report-listed and final-roster-confirmed players; not a whole-league prevalence estimate",
}


def metrics(frame):
    return {
        "n": len(frame),
        "negative_n": int((frame.actual == 0).sum()),
        "brier": float(frame.primary.mean()),
        "log_loss": float(frame.companion.mean()),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "protocol.json").write_text(json.dumps(PROTOCOL, indent=2), encoding="utf-8")
    sources = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
        for p in (ROOT / "src").glob("*.py")
    }
    inputs = [
        p
        for folder in ("historical_labels_v2", "historical_injuries")
        for p in (ROOT / "data/archive" / folder).rglob("*.json.gz")
    ]
    inputs += sorted((ROOT / "data/raw").glob("player_logs_202[2345]*.parquet"))
    input_hashes = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs
    }
    labels = {}
    for season in ("2024_25", "2025_26"):
        frame = availability_labels(
            ROOT, season, load_reports(ROOT, season), "historical_labels_v2"
        )
        frame = frame[frame.reason_type != "GLEAGUE"].reset_index(drop=True)
        labels[season] = attach_causal_availability(ROOT, season, frame)
    baseline, state = online_availability(labels["2024_25"], 0)
    selected, options, selection = 0, [], []
    for strength in (20, 60):
        frame, _ = online_availability(labels["2024_25"], strength)
        check = paired_gate(baseline, frame)
        selection.append({"strength": strength, "metrics": metrics(frame), "gate": check})
        if check["accepted"]:
            options.append((frame.primary.mean(), strength))
    if options:
        selected = min(options)[1]
    (OUT / "frozen_selection.json").write_text(json.dumps({"strength": selected}), encoding="utf-8")
    test_base, _ = online_availability(labels["2025_26"], 0, state)
    test, _ = online_availability(labels["2025_26"], selected, state)
    report = {
        "selected_strength": selected,
        "selection_baseline": metrics(baseline),
        "selection": selection,
        "assessment_baseline": metrics(test_base),
        "assessment_candidate": metrics(test),
        "assessment_gate": paired_gate(test_base, test),
        "deployed_change": False,
        "deployment_block": "Noon same-day conditional cohort cannot be transported to arbitrary live times/next-day horizons without validation",
        "source_sha256_LF": sources,
        "protocol": PROTOCOL,
    }
    test.to_csv(OUT / "assessment_predictions.csv.gz", index=False)
    report["inputs_sha256"] = input_hashes
    if sources != {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
        for p in (ROOT / "src").glob("*.py")
    }:
        raise ValueError("Source changed during calibration; rerun")
    if input_hashes != {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs
    }:
        raise ValueError("Inputs changed during calibration; rerun")
    (OUT / "decision.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()

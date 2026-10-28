"""Additional uncertainty safety check on the already-frozen tuning winner.

No alternative winner is chosen here. A failure reverts deployment to baseline.
"""

import hashlib
import json
import platform
from pathlib import Path

import numpy as np

from .rotation_policy import RotationPolicy
from .tune_rotation import BASELINE, metrics, replay

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/rotation_tuning"
PROTOCOL = {
    "version": 2,
    "mean_policy": "Existing frozen mean-policy winner; no new mean-policy selection",
    "variance_fit": "One global per-game minute variance scale for each mean policy, using2024_25 only",
    "estimator": "(10 + sum(squared residual / forecast variance))/(10+n), clipped[1,2]; weak10-observation shrinkage to1",
    "interpretation_estimator": "Inverse-Gamma residual-scale shrinkage under a Normal approximation; dependence means no posterior-certainty claim",
    "assessment": "2025_26; compare calibrated candidate with both raw and equally calibrated baseline",
    "normal_nll_max_relative_harm": 0.01,
    "coverage95_error_max_increase": 0.005,
    "cohort_min_rows": 200,
    "cohort_nll_max_relative_harm": 0.02,
    "cohort_coverage95_error_max_increase": 0.01,
    "decision": "All mean-policy and uncertainty gates must pass; otherwise baseline, no runner-up",
    "scope": "Per-game minute process variance only; Gamma/Beta precision and shared weekly rate covariance are not multiplied",
}


def score(frame):
    if frame.empty:
        return {"n": 0}
    variance = frame.variance.to_numpy().clip(1e-9)
    residual = frame.actual.to_numpy() - frame["mean"].to_numpy()
    return {
        "n": len(frame),
        "nll": float(np.mean(0.5 * (np.log(2 * np.pi * variance) + residual**2 / variance))),
        "coverage95": float(np.mean(abs(residual) <= 1.95996398454 * np.sqrt(variance))),
        "coverage80": float(np.mean(abs(residual) <= 1.28155156554 * np.sqrt(variance))),
    }


def main():
    from dataclasses import replace

    (OUT / "uncertainty_protocol.json").write_text(json.dumps(PROTOCOL, indent=2), encoding="utf-8")
    if (OUT / "uncertainty_safety.json").exists() and not (
        OUT / "uncertainty_raw_policy_safety.json"
    ).exists():
        (OUT / "uncertainty_raw_policy_safety.json").write_bytes(
            (OUT / "uncertainty_safety.json").read_bytes()
        )
    before = json.loads(
        (
            OUT / "mean_policy_decision.json"
            if (OUT / "mean_policy_decision.json").exists()
            else OUT / "decision.json"
        ).read_text(encoding="utf-8")
    )
    frozen = json.loads((OUT / "frozen_selection.json").read_text(encoding="utf-8"))
    winner = frozen["winner"]
    raw_policies = {
        "raw_baseline": RotationPolicy(),
        "raw_candidate": RotationPolicy(**frozen["policy"]),
    }
    sources = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
        for p in (ROOT / "src").glob("*.py")
    }
    training = replay("2024_25", raw_policies)
    fits, policies = {}, dict(raw_policies)
    for name, frame in training.items():
        ratio = (frame.actual - frame["mean"]) ** 2 / frame.variance.clip(lower=1e-9)
        raw_scale = float((10 + ratio.sum()) / (10 + len(frame)))
        scale = float(np.clip(raw_scale, 1, 2))
        fits[name] = {
            "training_n": len(frame),
            "raw_scale": raw_scale,
            "scale": scale,
            "clipped": scale != raw_scale,
        }
        policies[name.replace("raw_", "calibrated_")] = replace(
            raw_policies[name], minute_variance_scale=scale
        )
    # Freeze scale estimates before assessing any calibrated2025 prediction.
    (OUT / "frozen_variance_scales.json").write_text(json.dumps(fits, indent=2), encoding="utf-8")
    frames = replay("2025_26", policies)
    for name, previous in (
        ("raw_baseline", before["baseline_metrics"]),
        ("raw_candidate", before["candidate_metrics"]),
    ):
        current = metrics(frames[name])
        if current["n"] != previous["n"] or abs(current["mse"] - previous["mse"]) > 1e-9:
            raise ValueError("Safety replay differs from frozen mean assessment")
    results, reasons = {}, []
    base = frames["raw_baseline"]
    for cohort in ("all", "low_role", "strong_prior_low_role", "early"):
        mask = np.ones(len(base), dtype=bool) if cohort == "all" else base[cohort].to_numpy()
        values = {name: score(frame[mask]) for name, frame in frames.items()}
        results[cohort] = values
        if values["raw_baseline"]["n"] >= (1 if cohort == "all" else 200):
            nll_harm = 0.01 if cohort == "all" else 0.02
            coverage_harm = 0.005 if cohort == "all" else 0.01
            for reference in ("raw_baseline", "calibrated_baseline"):
                a, b = values[reference], values["calibrated_candidate"]
                if b["nll"] > a["nll"] * (1 + nll_harm):
                    reasons.append("nll_" + cohort + "_vs_" + reference)
                if abs(b["coverage95"] - 0.95) > abs(a["coverage95"] - 0.95) + coverage_harm:
                    reasons.append("coverage95_" + cohort + "_vs_" + reference)
    if sources != {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
        for p in (ROOT / "src").glob("*.py")
    }:
        raise ValueError("Source changed during safety check")
    accepted = before["assessment_gate"]["accepted"] and not reasons and winner != BASELINE
    deployed = policies["calibrated_candidate"] if accepted else RotationPolicy()
    (ROOT / "config/rotation_policy.json").write_text(
        json.dumps(deployed.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    report = {
        "accepted": accepted,
        "reasons": reasons,
        "scores": results,
        "variance_fits": fits,
        "source_sha256_LF": sources,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "protocol": PROTOCOL,
    }
    (OUT / "uncertainty_safety.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    before["deployed_change"] = accepted
    research = {
        "policy": policies["calibrated_candidate"].to_dict(),
        "accepted_for_primary": accepted,
        "reasons": reasons,
        "fit_season": "2024_25",
        "assessment_season": "2025_26",
    }
    (ROOT / "config/rotation_candidate.json").write_text(
        json.dumps(research, indent=2) + "\n", encoding="utf-8"
    )
    before["deployed_policy"] = deployed.to_dict()
    before["mean_source_sha256_LF"] = before["source_sha256_LF"]
    before["source_sha256_LF"] = sources
    before["uncertainty_safety"] = {"accepted": accepted, "reasons": reasons}
    before["activation_status"] = (
        "provisional_prospective_monitoring" if accepted else "baseline_retained"
    )
    (OUT / "decision.json").write_text(json.dumps(before, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()

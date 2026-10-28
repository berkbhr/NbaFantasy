"""Bounded chronological calibration, with frozen gates and live role parity.

Run: python -m src.calibrate. No network, injuries, or current rosters are read.
Assessment seasons were previously inspected: this is retrospective validation.
"""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import betaln, gammaln
from scipy.stats import nbinom

from .bayesian_model import COUNT_STATS, BayesianPlayer
from .model_policy import ModelPolicy, update_role
from .priors import get_positional_averages, load_prior_season
from .validation import previous_season

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "calibration"
PROTOCOL = {
    "selection_season": "2024_25",
    "assessment_season": "2025_26",
    "status": "Retrospective: both seasons have been inspected in earlier comparisons",
    "scope": "Per played game; no availability, weekly roster utility or playoff claim",
    "baseline": ModelPolicy().to_dict(),
    "stages": [
        {
            "name": "blend",
            "metric": "count_nll",
            "candidates": [
                {"blend": "single"},
                *[{"blend": "fixed", "primary_weight": w} for w in (0.6, 0.8, 0.9)],
            ],
        },
        {
            "name": "count_ess",
            "metric": "count_nll",
            "candidates": [{"exposure_minutes": n} for n in (120.0, 360.0, 650.0)],
        },
        {
            "name": "legacy",
            "metric": "count_nll",
            "candidates": [
                {"fixed_kappa": True},
                {"legacy_total_rates": True},
            ],
        },
        {
            "name": "role",
            "metric": "minute_mae",
            "candidates": [
                {"role": "ewma"},
                {"role": "adaptive_anchor"},
            ],
        },
        {
            "name": "shot_ess",
            "metric": "shot_nll",
            "candidates": [{"shot_precision_multiplier": n} for n in (0.5, 1.5)],
        },
    ],
    "acceptance": {
        "relative_primary_gain_min": 0.0025,
        "paired_calendar_week_bootstrap": "2000 draws, seed42; lower95% gain >0",
        "temporal_halves": "Neither half worse on primary metric",
        "guards": "count NLL, shot NLL and minute MAE <=0.5% worse; each stat MAE <=1% worse",
        "cohorts": "Prior >=25 MPG, 15-25, <15/new; observed games1-10/11+; n>=500: primary <=1% worse",
        "final": "Freeze one selection winner; compare to original baseline on assessment once. No runner-up search.",
        "deployment": "All selected primary targets must pass assessment gates. Otherwise retain baseline.",
    },
    "uncertainty": "Count/attempt exposure and Beta shot precision only; corrected predictive moments retained. No weekly variance multipliers fitted.",
    "search_budget": "Baseline +13 stage candidates + final two-policy assessment; no Cartesian sweep",
    "predictors": "Pooled completed-season population, no contemporary positions. Predict BEFORE updating each row.",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(season, policy, logs=None):
    prior = load_prior_season(previous_season(season), policy=policy)
    averages = get_positional_averages(prior, pos_dict={})
    if logs is None:
        logs = pd.read_parquet(ROOT / "data" / "raw" / f"player_logs_{season}.parquet")
    logs = logs.copy()
    logs["GAME_DATE"] = pd.to_datetime(logs.GAME_DATE)
    logs = logs.sort_values(["GAME_DATE", "GAME_ID", "PLAYER_ID"]).drop_duplicates(
        ["PLAYER_ID", "GAME_ID"]
    )
    players, teams, histories, anchors, rows = {}, {}, {}, {}, []
    target_start = logs.GAME_DATE.min()
    # Verify every cache used to build a prior precedes the prediction period.
    for year in [previous_season(season), previous_season(previous_season(season))]:
        cached = pd.read_parquet(
            ROOT / "data" / "raw" / f"player_logs_{year}.parquet", columns=["GAME_DATE"]
        )
        if pd.to_datetime(cached.GAME_DATE).max() >= target_start:
            raise ValueError("Prior cache overlaps forecast period")
    for row in logs.to_dict("records"):
        pid, tid = int(row["PLAYER_ID"]), int(row["TEAM_ID"])
        if pid not in players:
            bp = BayesianPlayer(pid, str(pid), policy=policy)
            bp.initialize_priors(prior.get(pid), averages)
            players[pid], histories[pid], anchors[pid] = bp, [], bp.base_expected_minutes
        bp, hist = players[pid], histories[pid]
        pred = bp.predict_next_game(current_date=row["GAME_DATE"])
        if row["MIN"] > 0:
            old = prior.get(pid, {})
            mpg = old.get("MIN", 0) / max(1, old.get("GP", 0))
            rec = {
                "date": row["GAME_DATE"],
                "pid": pid,
                "gid": str(row["GAME_ID"]),
                "cohort": "25+" if mpg >= 25 else "15-25" if mpg >= 15 else "<15/new",
                "experience": "first10" if getattr(bp, "calibration_gp", 0) < 10 else "later",
                "minute_mae": abs(row["MIN"] - pred["MIN"]["mean"]),
            }
            for stat in COUNT_STATS:
                mu, var = pred[stat]["mean"], pred[stat]["variance"]
                rec[stat + "_mae"] = abs(row[stat] - mu)
                rec[stat + "_mu"], rec[stat + "_var"] = mu, var
                rec[stat + "_actual"] = row[stat]
            for stat in ("FG", "FT"):
                # Use the forecast's idle-decayed precision, exactly as live prediction.
                probability = pred[stat]["rate"]
                precision = probability * (1 - probability) / pred[stat]["rate_variance"] - 1
                rec[stat + "_a"] = probability * precision
                rec[stat + "_b"] = (1 - probability) * precision
                rec[stat + "_made"], rec[stat + "_att"] = row[stat + "M"], row[stat + "A"]
            rows.append(rec)
            bp.calibration_gp = getattr(bp, "calibration_gp", 0) + 1
        trade = pid in teams and teams[pid] != tid
        bp.update_stats(
            row["GAME_DATE"], float(row["MIN"]), row, is_event_reset=trade, game_id=row["GAME_ID"]
        )
        teams[pid] = tid
        if row["MIN"] > 0:
            if trade:
                hist.clear()
                anchors[pid] = bp.base_expected_minutes
            hist.append((str(row["GAME_ID"]), float(row["MIN"]), row["GAME_DATE"], tid))
            update_role(bp, hist, anchors[pid], policy)
    frame = pd.DataFrame(rows)
    nll = []
    for stat in COUNT_STATS:
        mu = frame[stat + "_mu"].to_numpy().clip(1e-9)
        var = np.maximum(frame[stat + "_var"], mu + 1e-9)
        shape = mu**2 / (var - mu)
        nll.append(-nbinom.logpmf(frame[stat + "_actual"], shape, shape / (shape + mu)))
    frame["count_nll"] = np.mean(nll, axis=0)
    shots = []
    for stat in ("FG", "FT"):
        a, b, k, n = [frame[stat + suffix].to_numpy() for suffix in ("_a", "_b", "_made", "_att")]
        # Actual attempts are used ONLY to score accuracy conditional on attempts.
        logp = (
            gammaln(n + 1)
            - gammaln(k + 1)
            - gammaln(n - k + 1)
            + betaln(k + a, n - k + b)
            - betaln(a, b)
        )
        shots.append(-logp)
    frame["shot_nll"] = np.mean(shots, axis=0)
    frame["week"] = frame.date.dt.to_period("W").astype(str)
    return frame


def metrics(frame):
    keys = ["count_nll", "shot_nll", "minute_mae"] + [s + "_mae" for s in COUNT_STATS]
    return {key: float(frame[key].mean()) for key in keys}


def gate(base, candidate, metric):
    if not base[["pid", "gid", "date"]].equals(candidate[["pid", "gid", "date"]]):
        raise ValueError("Candidate populations differ")
    gain = base[metric].to_numpy() - candidate[metric].to_numpy()
    relative = float(gain.mean() / base[metric].mean())
    weeks = (
        pd.DataFrame({"week": base.week, "gain": gain}).groupby("week").gain.agg(["sum", "count"])
    )
    rng = np.random.default_rng(42)
    index = rng.integers(0, len(weeks), (2000, len(weeks)))
    samples = weeks["sum"].to_numpy()[index].sum(axis=1) / weeks["count"].to_numpy()[index].sum(
        axis=1
    )
    ci = np.quantile(samples, [0.025, 0.975]).tolist()
    reasons = []
    if relative < 0.0025:
        reasons.append("gain_below_0.25_percent")
    if ci[0] <= 0:
        reasons.append("weekly_ci_includes_zero")
    dates = sorted(base.date.unique())
    midpoint = dates[len(dates) // 2]
    halves = [float(gain[base.date < midpoint].mean()), float(gain[base.date >= midpoint].mean())]
    if min(halves) < 0:
        reasons.append("temporal_half_regression")
    bm, cm = metrics(base), metrics(candidate)
    for key in bm:
        tolerance = 0.01 if key.endswith("_mae") and key != "minute_mae" else 0.005
        if cm[key] > bm[key] * (1 + tolerance):
            reasons.append("guard_" + key)
    cohorts = {}
    for field in ("cohort", "experience"):
        for label in sorted(base[field].unique()):
            mask = base[field] == label
            value = float(gain[mask].mean() / base.loc[mask, metric].mean())
            cohorts[field + ":" + label] = {"n": int(mask.sum()), "relative_gain": value}
            if mask.sum() >= 500 and value < -0.01:
                reasons.append("cohort_" + label)
    return {
        "accepted": not reasons,
        "relative_gain": relative,
        "gain_ci95": ci,
        "half_absolute_gains": halves,
        "cohorts": cohorts,
        "reasons": reasons,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # Written before computing any candidate. Gates are not adjusted after results.
    protocol_text = json.dumps(PROTOCOL, indent=2)
    (OUT / "protocol.json").write_text(protocol_text, encoding="utf-8")
    baseline_policy = current = ModelPolicy()
    baseline = replay("2024_25", baseline_policy)
    current_frame = baseline
    results = [{"stage": "baseline", "policy": current.to_dict(), "metrics": metrics(baseline)}]
    targets = []
    for stage in PROTOCOL["stages"]:
        alternatives = []
        for change in stage["candidates"]:
            policy = replace(current, **change)
            frame = replay("2024_25", policy)
            decision = gate(current_frame, frame, stage["metric"])
            results.append(
                {
                    "stage": stage["name"],
                    "policy": policy.to_dict(),
                    "metrics": metrics(frame),
                    "gate": decision,
                }
            )
            print(stage["name"], change, decision, flush=True)
            if decision["accepted"]:
                alternatives.append((frame[stage["metric"]].mean(), policy, frame))
        if alternatives:
            _, current, current_frame = min(alternatives, key=lambda x: x[0])
            targets.append(stage["metric"])
        (OUT / "selection_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    frozen = {"policy": current.to_dict(), "assessment_targets": sorted(set(targets))}
    (OUT / "frozen_selection.json").write_text(json.dumps(frozen, indent=2), encoding="utf-8")
    assessment_base = replay("2025_26", baseline_policy)
    assessment = replay("2025_26", current) if current != baseline_policy else assessment_base
    checks = {target: gate(assessment_base, assessment, target) for target in sorted(set(targets))}
    deploy = bool(checks) and all(check["accepted"] for check in checks.values())
    final = current if deploy else baseline_policy
    (ROOT / "config" / "model_policy.json").write_text(
        json.dumps(final.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    report = {
        "selection": frozen,
        "assessment_gates": checks,
        "deployed_change": deploy,
        "deployed_policy": final.to_dict(),
        "baseline_metrics": metrics(assessment_base),
        "candidate_metrics": metrics(assessment),
        "protocol_sha256": hashlib.sha256(protocol_text.encode()).hexdigest(),
        "sources": {
            str(p.relative_to(ROOT)): digest(p)
            for p in [
                ROOT / "src" / name
                for name in (
                    "calibrate.py",
                    "model_policy.py",
                    "priors.py",
                    "bayesian_model.py",
                    "live_draft_assistant.py",
                )
            ]
        },
        "data": {
            p.name: digest(p)
            for p in sorted((ROOT / "data" / "raw").glob("player_logs_202[2345]*.parquet"))
        },
    }
    (OUT / "decision.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    records = []
    for stage_result in results:
        records.append(
            {
                "stage": stage_result["stage"],
                "policy": json.dumps(stage_result["policy"]),
                **stage_result["metrics"],
                "accepted": stage_result.get("gate", {}).get("accepted", False),
            }
        )
    pd.DataFrame(records).to_csv(OUT / "selection_metrics.csv", index=False)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()

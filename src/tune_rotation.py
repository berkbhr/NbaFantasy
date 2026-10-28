"""Bounded, chronological tuning of opportunity allocation with lagged rosters.

The archive is retrospective. Missing final rosters/positions are never filled
from the target game's boxscore before predicting. No player blacklist.
"""

import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from .bayesian_model import BayesianPlayer
from .injury_experiments import load_reports
from .injury_tracker import normalize_name
from .model_policy import load_model_policy, update_role
from .priors import get_positional_averages, load_prior_season
from .rotation import adjust_rotations
from .rotation_policy import RotationPolicy, load_rotation_policy
from .validation import previous_season

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/rotation_tuning"
BASELINE = "fraction1_evidence_none"
CANDIDATES = {"fraction0_evidence_none": RotationPolicy(0)}
for fraction in (0.25, 0.5, 0.75, 1.0):
    for strength in (None, 3.0, 8.0):
        name = f"fraction{fraction:g}_evidence_{'none' if strength is None else int(strength)}"
        CANDIDATES[name] = RotationPolicy(fraction, strength)
PROTOCOL = {
    "selection_season": "2024_25",
    "assessment_season": "2025_26",
    "candidate_budget": len(CANDIDATES),
    "candidates": {k: v.to_dict() for k, v in CANDIDATES.items()},
    "baseline": BASELINE,
    "role_policy": load_model_policy().to_dict(),
    "objective": "Minute MSE targets the conditional mean; MAE targets the median and is a guard",
    "features": "Previous final-roster membership/positions, prior seasons, past game logs, same-day pre-noon report",
    "evaluation": "All archived regular-season days; target final roster only gates/scorers, never predictor eligibility",
    "eligibility": "At least8 past/current-report known teammates, >=3 previous played games for scored players, final tipoff strictly after noon cutoff",
    "selection_gate": {
        "min_rows": 1000,
        "relative_mse_gain": 0.0025,
        "paired_week_ci95_lower": ">0, 2000 draws seed42",
        "both_chronological_halves": "nonnegative MSE gain",
        "mae_max_harm": 0.01,
        "pts_mse_max_harm": 0.01,
        "mean_underprediction_max_increase_minutes": 0.25,
        "cohort_mse_max_harm": 0.01,
        "cohort_min_rows": 200,
    },
    "quality_gate": {"mean_past_position_coverage_min": 0.9, "observed_weeks_min": 20},
    "assessment": "Freeze a single selection winner; assess it and baseline only. No runner-up selection on assessment.",
    "deployment": "Only if selection and assessment gates pass, using the same rotation function. Otherwise baseline.",
    "limits": "Retrospective, played-game conditional; historical Yahoo eligibility and transactions unavailable. No claim of causal injury effects or category-win lift.",
    "rare_strong_prior_guard": "Even below200 rows, reject >5% MSE harm in observed strong-prior low-role cohort; conservative point-estimate guard, not statistical proof",
}


def read_labels(root, season):
    return {
        path.name[:10]: json.loads(gzip.decompress(path.read_bytes()))
        for path in sorted((root / "data/archive/historical_labels_v2" / season).glob("*.json.gz"))
    }


def replay(season, policies, root=ROOT):
    role_policy = load_model_policy()
    prior = load_prior_season(previous_season(season), policy=role_policy)
    averages = get_positional_averages(prior, pos_dict={})
    prior_logs = pd.read_parquet(
        root / "data/raw" / f"player_logs_{previous_season(season)}.parquet"
    )
    logs = pd.read_parquet(root / "data/raw" / f"player_logs_{season}.parquet")
    logs["GAME_DATE"] = pd.to_datetime(logs.GAME_DATE)
    if pd.to_datetime(prior_logs.GAME_DATE).max() >= logs.GAME_DATE.min():
        raise ValueError("Prior overlaps prediction period")
    reports, label_days = load_reports(root, season), read_labels(root, season)
    code_to_id = prior_logs.set_index("TEAM_ABBREVIATION").TEAM_ID.to_dict()
    players, names, teams, positions, roster_dates, histories, anchors = {}, {}, {}, {}, {}, {}, {}
    for row in (
        prior_logs.sort_values("GAME_DATE")
        .drop_duplicates("PLAYER_ID", keep="last")
        .to_dict("records")
    ):
        pid = int(row["PLAYER_ID"])
        bp = BayesianPlayer(pid, row["PLAYER_NAME"], policy=role_policy)
        bp.initialize_priors(prior.get(pid), averages)
        players[pid], names[normalize_name(bp.name)] = bp, pid
        teams[pid], histories[pid], anchors[pid] = int(row["TEAM_ID"]), [], bp.base_expected_minutes
    observed_teams = dict(teams)
    known_games = {}
    output = {name: [] for name in policies}
    for day, daily in logs.sort_values(["GAME_DATE", "GAME_ID", "PLAYER_ID"]).groupby(
        "GAME_DATE", sort=True
    ):
        date = str(day.date())
        report, finals = reports.get(date), label_days.get(date, {}).get("rows", [])
        if report and finals:
            eligible = {
                pid: bp
                for pid, bp in players.items()
                if pid in roster_dates and (day - roster_dates[pid]).days <= 21
            }
            for bp in players.values():
                bp.update_injury_status("HEALTHY")
            unsub = {
                r["team_code"]
                for r in report.get("unsubmitted_teams", [])
                if pd.Timestamp(r["game_date"]).strftime("%Y-%m-%d") == date
            }
            submitted = set()
            for row in report["rows"]:
                if (
                    pd.Timestamp(row["game_date"]).strftime("%Y-%m-%d") != date
                    or row["team_code"] in unsub
                ):
                    continue
                if row.get("reason_type") == "GLEAGUE":
                    continue  # Match live health-feed filtering; no fake injury vacancy.
                pid, tid = names.get(normalize_name(row["name"])), code_to_id.get(row["team_code"])
                if pid in players and tid:
                    teams[pid] = int(tid)  # Today's report is legitimate pregame team evidence.
                    eligible[pid] = players[pid]
                    players[pid].update_injury_status(
                        row["status"], report_date=report["report_at"]
                    )
                    submitted.add(int(tid))
            pools = defaultdict(list)
            for pid in eligible:
                pools[teams[pid]].append(pid)
            valid_teams = {tid for tid, ids in pools.items() if len(ids) >= 8 and tid in submitted}
            final_lookup = {(r["norm"], r["team_code"]): r for r in finals}
            cases = []
            for row in daily.to_dict("records"):
                pid, tid = int(row["PLAYER_ID"]), int(row["TEAM_ID"])
                if (
                    pid not in eligible
                    or teams[pid] != tid
                    or tid not in valid_teams
                    or len(histories[pid]) < 3
                    or histories[pid][-1][3] != tid
                    or row["MIN"] <= 0
                ):
                    continue
                final = final_lookup.get(
                    (normalize_name(row["PLAYER_NAME"]), row["TEAM_ABBREVIATION"])
                )
                if (
                    final is None
                    or not final.get("tipoff_at")
                    or pd.Timestamp(final["tipoff_at"]) <= pd.Timestamp(report["cutoff_at"])
                ):
                    continue
                coverage = sum(i in positions for i in pools[tid]) / len(pools[tid])
                cases.append((row, pid, coverage))
            for name, policy in policies.items():
                adjust_rotations(
                    eligible, teams, positions, game_date=day, as_of_date=day, policy=policy
                )
                for row, pid, coverage in cases:
                    bp = eligible[pid]
                    pred = bp.predict_next_game(current_date=day)
                    minute, actual = pred["MIN"]["mean"], float(row["MIN"])
                    pts = pred["PTS"]["mean"]
                    mpg = prior.get(pid, {}).get("MIN", 0) / max(
                        1.0, prior.get(pid, {}).get("GP", 0)
                    )
                    output[name].append(
                        {
                            "date": date,
                            "pid": pid,
                            "game_id": str(row["GAME_ID"]),
                            "mean": minute,
                            "variance": float(pred["MIN"]["variance"]),
                            "actual": actual,
                            "mse": (minute - actual) ** 2,
                            "mae": abs(minute - actual),
                            "under": max(actual - minute, 0.0),
                            "pts_mse": (pts - row["PTS"]) ** 2,
                            "position_coverage": coverage,
                            "low_role": bp.current_season_gp >= 2 and bp.current_season_mpg < 10,
                            "strong_prior_low_role": mpg >= 25 and bp.current_season_mpg < 10,
                            "early": bp.current_season_gp < 10,
                        }
                    )
        # Learning occurs only AFTER all noon candidates have predicted.
        for row in daily.to_dict("records"):
            pid, tid = int(row["PLAYER_ID"]), int(row["TEAM_ID"])
            if pid not in players:
                bp = BayesianPlayer(pid, row["PLAYER_NAME"], policy=role_policy)
                bp.initialize_priors(prior.get(pid), averages)
                players[pid], histories[pid], anchors[pid] = bp, [], bp.base_expected_minutes
            bp = players[pid]
            trade = observed_teams.get(pid) is not None and observed_teams[pid] != tid
            bp.update_stats(day, row["MIN"], row, is_event_reset=trade, game_id=row["GAME_ID"])
            names[normalize_name(row["PLAYER_NAME"])] = pid
            teams[pid] = tid
            observed_teams[pid] = tid
            if row["MIN"] > 0:
                if trade:
                    histories[pid].clear()
                    anchors[pid] = bp.base_expected_minutes
                histories[pid].append((str(row["GAME_ID"]), float(row["MIN"]), day, tid))
                update_role(bp, histories[pid], anchors[pid], role_policy)
        # Final rosters/positions from this day become available only tomorrow.
        for row in finals:
            pid, tid = names.get(row["norm"]), code_to_id.get(row["team_code"])
            if pid not in players or not tid:
                continue
            teams[pid], roster_dates[pid] = int(tid), day
            if row.get("position") in ("G", "F", "C", "PG", "SG", "SF", "PF"):
                positions[pid] = row["position"]
            players[pid].record_team_game_availability(row["played"])
        for (tid, gid), box in daily.groupby(["TEAM_ID", "GAME_ID"]):
            if box.PLAYER_ID.nunique() >= 5:
                known_games[(int(tid), str(gid))] = set(
                    box.loc[box.MIN > 0, "PLAYER_ID"].astype(int)
                )
        team_members = defaultdict(list)
        for pid in players:
            team_members[teams.get(pid)].append(pid)
        for pid, bp in players.items():
            known = [
                known_games[(r[3], r[0])]
                for r in histories[pid][-5:]
                if (r[3], r[0]) in known_games and r[3] == teams.get(pid)
            ]
            bp.baseline_absences = {}
            if known:
                bp.baseline_absences = {
                    other: getattr(bp, "role_observation_weight", 0)
                    * sum(other not in g for g in known)
                    / len(known)
                    for other in team_members[teams.get(pid)]
                    if other != pid
                }
    return {name: pd.DataFrame(rows) for name, rows in output.items()}


def metrics(frame):
    if frame.empty:
        return {"n": 0}
    return {
        "n": len(frame),
        **{
            k: float(frame[k].mean())
            for k in ("mse", "mae", "under", "pts_mse", "position_coverage")
        },
    }


def gate(base, candidate):
    if not base[["date", "pid", "game_id"]].equals(candidate[["date", "pid", "game_id"]]):
        raise ValueError("Paired populations differ")
    reasons, cohort_metrics = [], {}
    if len(base) < 1000:
        return {"accepted": False, "reasons": ["fewer_than_1000_rows"]}
    gain = base.mse.to_numpy() - candidate.mse.to_numpy()
    relative = float(gain.mean() / base.mse.mean())
    weeks = (
        pd.DataFrame({"week": pd.to_datetime(base.date).dt.to_period("W"), "gain": gain})
        .groupby("week")
        .gain.agg(["sum", "count"])
    )
    indices = np.random.default_rng(42).integers(0, len(weeks), (2000, len(weeks)))
    samples = weeks["sum"].to_numpy()[indices].sum(axis=1) / weeks["count"].to_numpy()[indices].sum(
        axis=1
    )
    ci = np.quantile(samples, [0.025, 0.975]).tolist()
    midpoint = sorted(base.date.unique())[len(base.date.unique()) // 2]
    halves = [float(gain[base.date < midpoint].mean()), float(gain[base.date >= midpoint].mean())]
    if relative < 0.0025:
        reasons.append("gain_below_0.25_percent")
    if ci[0] <= 0:
        reasons.append("weekly_ci_includes_zero")
    if min(halves) < 0:
        reasons.append("half_regression")
    if len(weeks) < 20:
        reasons.append("fewer_than20weeks")
    if base.position_coverage.mean() < 0.9:
        reasons.append("insufficient_past_positions")
    for key in ("mae", "pts_mse"):
        if candidate[key].mean() > base[key].mean() * 1.01:
            reasons.append("guard_" + key)
    if candidate.under.mean() > base.under.mean() + 0.25:
        reasons.append("underprediction_guard")
    for cohort in ("low_role", "strong_prior_low_role", "early"):
        mask = base[cohort]
        cohort_metrics[cohort] = {
            "baseline": metrics(base[mask]),
            "candidate": metrics(candidate[mask]),
        }
        if (
            mask.sum() >= 200
            and candidate.loc[mask, "mse"].mean() > base.loc[mask, "mse"].mean() * 1.01
        ):
            reasons.append("cohort_" + cohort)
        if (
            cohort == "strong_prior_low_role"
            and mask.sum() > 0
            and candidate.loc[mask, "mse"].mean() > base.loc[mask, "mse"].mean() * 1.05
        ):
            reasons.append("rare_strong_prior_guard")
    return {
        "accepted": not reasons,
        "relative_mse_gain": relative,
        "mse_gain_ci95": ci,
        "half_gains": halves,
        "reasons": reasons,
        "cohorts": cohort_metrics,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "protocol.json").write_text(json.dumps(PROTOCOL, indent=2), encoding="utf-8")
    sources = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
        for p in (ROOT / "src").glob("*.py")
    }
    input_paths = [
        p
        for folder in ("historical_labels_v2", "historical_injuries")
        for p in sorted((ROOT / "data/archive" / folder).rglob("*.json.gz"))
    ]
    input_paths += sorted((ROOT / "data/raw").glob("player_logs_202[2345]*.parquet"))
    input_paths.append(ROOT / "config/model_policy.json")
    input_hashes = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in input_paths
    }
    print("Selection replay: 13 candidates, same causal states", flush=True)
    validation = replay("2024_25", CANDIDATES)
    base = validation[BASELINE]
    results, accepted = [], []
    for name, frame in validation.items():
        check = gate(base, frame)
        results.append(
            {
                "candidate": name,
                "policy": CANDIDATES[name].to_dict(),
                "metrics": metrics(frame),
                "gate": check,
            }
        )
        if check["accepted"]:
            accepted.append((frame.mse.mean(), name))
    winner = min(accepted)[1] if accepted else BASELINE
    (OUT / "selection.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (OUT / "frozen_selection.json").write_text(
        json.dumps({"winner": winner, "policy": CANDIDATES[winner].to_dict()}), encoding="utf-8"
    )
    print("Frozen winner:", winner, flush=True)
    assessment = replay(
        "2025_26", {name: CANDIDATES[name] for name in dict.fromkeys([BASELINE, winner])}
    )
    check = gate(assessment[BASELINE], assessment[winner])
    deploy = winner != BASELINE and check["accepted"]
    policy = CANDIDATES[winner] if deploy else RotationPolicy()
    report = {
        "selected": winner,
        "mean_candidate_passed": deploy,
        "mean_candidate_policy": policy.to_dict(),
        "deployed_change": False,
        "deployed_policy": load_rotation_policy().to_dict(),
        "deployment_pending": "check_rotation_safety must pass before activation",
        "assessment_gate": check,
        "baseline_metrics": metrics(assessment[BASELINE]),
        "candidate_metrics": metrics(assessment[winner]),
        "source_sha256_LF": sources,
        "protocol": PROTOCOL,
    }
    if sources != {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
        for p in (ROOT / "src").glob("*.py")
    }:
        raise ValueError("Source changed during experiment; rerun for valid provenance")
    if input_hashes != {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in input_paths
    }:
        raise ValueError("Input changed during experiment; rerun")
    # Mean tuning alone never bypasses the separate uncertainty gate.
    for name, frame in assessment.items():
        frame.to_csv(OUT / f"assessment_{name}.csv.gz", index=False)
    report["inputs_sha256"] = input_hashes
    (OUT / "decision.json").write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding="utf-8"
    )
    (OUT / "mean_policy_decision.json").write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()

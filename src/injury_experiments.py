"""Causal, bounded availability calibration and exploratory spillover replay."""

import gzip
import hashlib
import json
from collections import defaultdict
from copy import deepcopy

import numpy as np
import pandas as pd

from .bayesian_model import BayesianPlayer
from .injury_tracker import normalize_name
from .model_policy import ModelPolicy, update_role
from .priors import get_positional_averages, load_prior_season
from .rotation import adjust_rotations
from .validation import previous_season

STATUS_P = {"OUT": 0.0, "DOUBTFUL": 0.15, "QUESTIONABLE": 0.52, "PROBABLE": 0.9, "AVAILABLE": 0.9}


def load_reports(root, season):
    reports = {}
    for path in sorted((root / "data/archive/historical_injuries" / season).glob("*.json.gz")):
        item = json.loads(gzip.decompress(path.read_bytes()))
        if item["status"] == "usable":
            reports[item["date"]] = item
    return reports


def availability_labels(root, season, reports):
    rows, seen = [], set()
    for path in sorted((root / "data/archive/historical_labels" / season).glob("*.json.gz")):
        label_file = json.loads(gzip.decompress(path.read_bytes()))
        day = label_file["date"]
        report = reports.get(day)
        if not report:
            continue
        labels = {(r["norm"], r["team_code"]): r for r in label_file["rows"]}
        for row in report["rows"]:
            if pd.Timestamp(row["game_date"]).strftime("%Y-%m-%d") != day:
                continue
            label = labels.get((normalize_name(row["name"]), row["team_code"]))
            if label is None or not label.get("tipoff_at"):
                continue
            if pd.Timestamp(label["tipoff_at"]) <= pd.Timestamp(report["cutoff_at"]):
                continue
            key = (day, normalize_name(row["name"]), row["team_code"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "date": day,
                    "name": row["name"],
                    "team": row["team_code"],
                    "status": row["status"],
                    "actual": int(label["played"]),
                    "reason_type": row.get("reason_type"),
                    "cutoff_at": report["cutoff_at"],
                    "report_sha256": report["sha256"],
                }
            )
    return pd.DataFrame(rows)


def online_availability(frame, strength, initial=None):
    state = deepcopy(initial) if initial else defaultdict(lambda: [0, 0])
    rows = []
    if frame.empty:
        return pd.DataFrame(), state
    for _, daily in frame.sort_values(["date", "name"]).groupby("date", sort=True):
        for row in daily.to_dict("records"):
            base = row.get("base_probability", STATUS_P.get(row["status"], 0.85))
            wins, count = state[row["status"]]
            p = (wins + strength * base) / (count + strength) if strength else base
            error = row["actual"] - p
            mass = p if row["actual"] else 1 - p
            rows.append(
                {
                    **row,
                    "prediction": p,
                    "primary": error**2,
                    "companion": -float(np.log(max(mass, 1e-9))),
                }
            )
        # No same-noon outcomes may influence any other noon prediction.
        for row in daily.to_dict("records"):
            state[row["status"]][0] += row["actual"]
            state[row["status"]][1] += 1
    return pd.DataFrame(rows), state


def attach_causal_availability(root, season, labels):
    """Replay the live availability filter using only past games and prior teams.

    Team membership is a historical proxy, so this still cannot establish
    calibration of the full live roster/injury system.
    """
    if labels.empty:
        return labels
    priors = load_prior_season(previous_season(season))
    prior_logs = pd.read_parquet(
        root / "data/raw" / f"player_logs_{previous_season(season)}.parquet"
    )
    prior_logs = prior_logs.sort_values("GAME_DATE").drop_duplicates("PLAYER_ID", keep="last")
    players, teams = {}, {}
    for row in prior_logs.to_dict("records"):
        name = normalize_name(row["PLAYER_NAME"])
        bp = BayesianPlayer(int(row["PLAYER_ID"]), row["PLAYER_NAME"])
        bp.initialize_priors(priors.get(int(row["PLAYER_ID"])))
        players[name], teams[name] = bp, int(row["TEAM_ID"])
    logs = pd.read_parquet(root / "data/raw" / f"player_logs_{season}.parquet")
    logs["GAME_DATE"] = pd.to_datetime(logs.GAME_DATE)
    result = []
    for day, daily in logs.sort_values(["GAME_DATE", "GAME_ID", "PLAYER_ID"]).groupby(
        "GAME_DATE", sort=True
    ):
        date = str(day.date())
        for row in labels[labels.date == date].to_dict("records"):
            name = normalize_name(row["name"])
            if name not in players:
                bp = BayesianPlayer(-len(players) - 1, row["name"])
                bp.initialize_priors(None)
                players[name] = bp
            bp = players[name]
            bp.update_injury_status(row["status"], report_date=row["cutoff_at"])
            result.append(
                {
                    **row,
                    "base_probability": bp.get_effective_game_availability(
                        game_date=day, as_of_date=day
                    ),
                }
            )
        # Team assignment and labels are observed only after noon predictions.
        for row in daily.to_dict("records"):
            name = normalize_name(row["PLAYER_NAME"])
            if name not in players:
                bp = BayesianPlayer(int(row["PLAYER_ID"]), row["PLAYER_NAME"])
                bp.initialize_priors(priors.get(int(row["PLAYER_ID"])))
                players[name] = bp
            teams[name] = int(row["TEAM_ID"])
        for (tid, _), box in daily.groupby(["TEAM_ID", "GAME_ID"]):
            if box.PLAYER_ID.nunique() < 5:
                continue
            played = {normalize_name(n) for n in box.loc[box.MIN > 0, "PLAYER_NAME"]}
            for name, bp in players.items():
                if teams.get(name) == int(tid):
                    bp.record_team_game_availability(name in played)
    return pd.DataFrame(result)


def paired_gate(base, candidate, cohort="status"):
    keys = [c for c in ("date", "name", "team", "pid", "game_id", "status") if c in base]
    if len(base) != len(candidate) or not base[keys].equals(candidate[keys]):
        raise ValueError("Paired experiment populations/order differ")
    if len(base) < 1000:
        return {"accepted": False, "reason": "fewer_than_1000_rows", "n": len(base)}
    gain = base.primary.to_numpy() - candidate.primary.to_numpy()
    relative = float(gain.mean() / max(base.primary.mean(), 1e-12))
    frame = pd.DataFrame({"week": pd.to_datetime(base.date).dt.to_period("W"), "gain": gain})
    weeks = frame.groupby("week").gain.agg(["sum", "count"])
    indices = np.random.default_rng(42).integers(0, len(weeks), (2000, len(weeks)))
    samples = weeks["sum"].to_numpy()[indices].sum(axis=1) / weeks["count"].to_numpy()[indices].sum(
        axis=1
    )
    ci = np.quantile(samples, [0.025, 0.975]).tolist()
    midpoint = sorted(base.date.unique())[len(base.date.unique()) // 2]
    halves = [float(gain[base.date < midpoint].mean()), float(gain[base.date >= midpoint].mean())]
    reasons = []
    if relative < 0.0025:
        reasons.append("gain_below_0.25_percent")
    if ci[0] <= 0:
        reasons.append("weekly_ci_includes_zero")
    if min(halves) < 0:
        reasons.append("half_regression")
    if candidate.companion.mean() > base.companion.mean() * 1.005:
        reasons.append("companion_guard")
    cohorts = {}
    for value, group in base.groupby(cohort):
        mask = base[cohort] == value
        rel = float(gain[mask].mean() / max(group.primary.mean(), 1e-12))
        cohorts[str(value)] = {"n": len(group), "relative_gain": rel}
        if len(group) >= 500 and rel < -0.01:
            reasons.append("cohort_" + str(value))
    return {
        "accepted": not reasons,
        "relative_gain": relative,
        "ci95": ci,
        "half_gains": halves,
        "cohorts": cohorts,
        "reasons": reasons,
    }


def spillover_replay(root, season, reports):
    """Known past teammates only, pooled positions; target boxscore never builds roster.

    This proxy cannot establish performance of live position-aware spillover.
    Candidate scales leave the no-spillover team-budget normalization identical.
    """
    policy = ModelPolicy()  # Fixed recent_blend baseline; no fitted role cherry picking.
    prior = load_prior_season(previous_season(season), policy=policy)
    averages = get_positional_averages(prior, pos_dict={})
    logs = pd.read_parquet(root / "data/raw" / f"player_logs_{season}.parquet")
    logs["GAME_DATE"] = pd.to_datetime(logs.GAME_DATE)
    players, teams, last_seen, names, histories, anchors, counts = (
        {},
        {},
        {},
        {},
        {},
        {},
        defaultdict(int),
    )
    team_codes = {}
    known_games = {}
    samples = {scale: [] for scale in (0, 0.5, 1.0)}
    for day, daily in logs.sort_values(["GAME_DATE", "GAME_ID", "PLAYER_ID"]).groupby(
        "GAME_DATE", sort=True
    ):
        date = str(day.date())
        report = reports.get(date) if day.weekday() in (0, 3) else None
        if report:
            eligible = {
                pid: bp
                for pid, bp in players.items()
                if counts[pid] >= 3 and (day - last_seen[pid]).days <= 21
            }
            for bp in eligible.values():
                bp.update_injury_status("HEALTHY")
            unsubmitted = {
                r["team_code"]
                for r in report.get("unsubmitted_teams", [])
                if pd.Timestamp(r["game_date"]).strftime("%Y-%m-%d") == date
            }
            covered = set()
            for row in report["rows"]:
                if (
                    pd.Timestamp(row["game_date"]).strftime("%Y-%m-%d") != date
                    or row["team_code"] in unsubmitted
                ):
                    continue
                pid = names.get(normalize_name(row["name"]))
                if pid in players and team_codes.get(pid) == row["team_code"]:
                    eligible[pid] = players[pid]
                    players[pid].update_injury_status(
                        row["status"], report_date=report["report_at"]
                    )
                    covered.add(teams[pid])
            pools = defaultdict(list)
            for pid in eligible:
                pools[teams[pid]].append(pid)
            # At least 8 previously known teammates, no inference from today's lineup.
            valid_teams = {tid for tid, ids in pools.items() if len(ids) >= 8 and tid in covered}
            base_minutes = {pid: bp.base_expected_minutes for pid, bp in eligible.items()}
            adjust_rotations(eligible, teams, {}, game_date=day, as_of_date=day)
            budget_minutes = {}
            for tid, ids in pools.items():
                total = sum(
                    base_minutes[i]
                    * eligible[i].get_effective_game_availability(game_date=day, as_of_date=day)
                    for i in ids
                )
                factor = min(1, 240 / total) if total else 1
                budget_minutes.update({i: base_minutes[i] * factor for i in ids})
            for row in daily.to_dict("records"):
                pid, tid = int(row["PLAYER_ID"]), int(row["TEAM_ID"])
                if (
                    pid not in eligible
                    or teams[pid] != tid
                    or tid not in valid_teams
                    or row["MIN"] <= 0
                ):
                    continue
                # Require final-label tipoff validation for the team's game.
                label_path = root / "data/archive/historical_labels" / season / f"{date}.json.gz"
                if not label_path.exists():
                    continue
                label_rows = json.loads(gzip.decompress(label_path.read_bytes()))["rows"]
                valid_label = next(
                    (r for r in label_rows if r["norm"] == normalize_name(row["PLAYER_NAME"])), None
                )
                if (
                    valid_label is None
                    or not valid_label.get("tipoff_at")
                    or pd.Timestamp(valid_label["tipoff_at"]) <= pd.Timestamp(report["cutoff_at"])
                ):
                    continue
                for scale in samples:
                    minute = budget_minutes[pid] + scale * (
                        eligible[pid].expected_minutes - budget_minutes[pid]
                    )
                    rate = eligible[pid].alphas["PTS"] / eligible[pid].betas["PTS"]
                    samples[scale].append(
                        {
                            "date": date,
                            "pid": pid,
                            "game_id": str(row["GAME_ID"]),
                            "status": "25+" if base_minutes[pid] >= 25 else "<25",
                            "primary": abs(row["MIN"] - minute),
                            "companion": abs(row["PTS"] - rate * minute),
                        }
                    )
        for row in daily.to_dict("records"):
            pid, tid = int(row["PLAYER_ID"]), int(row["TEAM_ID"])
            if pid not in players:
                bp = BayesianPlayer(pid, str(row["PLAYER_NAME"]), policy=policy)
                bp.initialize_priors(prior.get(pid), averages)
                players[pid], histories[pid], anchors[pid] = bp, [], bp.base_expected_minutes
            bp = players[pid]
            trade = pid in teams and teams[pid] != tid
            bp.update_stats(day, row["MIN"], row, is_event_reset=trade, game_id=row["GAME_ID"])
            teams[pid] = tid
            team_codes[pid] = row["TEAM_ABBREVIATION"]
            names[normalize_name(row["PLAYER_NAME"])] = pid
            if row["MIN"] > 0:
                if trade:
                    histories[pid].clear()
                    anchors[pid] = bp.base_expected_minutes
                histories[pid].append((str(row["GAME_ID"]), float(row["MIN"]), day, tid))
                update_role(bp, histories[pid], anchors[pid], policy)
                counts[pid] += 1
                last_seen[pid] = day
        for (tid, gid), box in daily.groupby(["TEAM_ID", "GAME_ID"]):
            if box.PLAYER_ID.nunique() < 5:
                continue
            played = set(box.loc[box.MIN > 0, "PLAYER_ID"].astype(int))
            known_games[(int(tid), str(gid))] = played
            for pid, bp in players.items():
                if teams.get(pid) == int(tid):
                    bp.record_team_game_availability(pid in played)
        for pid, bp in players.items():
            known = [
                known_games[(r[3], r[0])]
                for r in histories[pid][-5:]
                if (r[3], r[0]) in known_games and r[3] == teams[pid]
            ]
            bp.baseline_absences = {}
            if known:
                bp.baseline_absences = {
                    other: getattr(bp, "role_observation_weight", 0)
                    * sum(other not in game for game in known)
                    / len(known)
                    for other in players
                    if other != pid and teams.get(other) == teams[pid]
                }
    return {scale: pd.DataFrame(rows) for scale, rows in samples.items()}


def run(root, output):
    provenance = {
        "sources": {},
        "inputs": {},
        "interpretation": "Retrospective; no virgin holdout or live causal spillover claim",
    }
    for path in sorted((root / "src").glob("*.py")):
        provenance["sources"][str(path.relative_to(root))] = hashlib.sha256(
            path.read_text(encoding="utf-8").encode("utf-8")
        ).hexdigest()
    files = list((root / "data/archive/historical_injuries").rglob("*.json.gz")) + list(
        (root / "data/archive/historical_labels").rglob("*.json.gz")
    )
    files += list((root / "data/raw").glob("player_logs_202[2345]*.parquet"))
    for path in sorted(files):
        provenance["inputs"][str(path.relative_to(root))] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    protocol = output / "protocol.json"
    provenance["text_hash_encoding"] = "UTF-8, LF-normalized newlines"
    provenance["protocol_sha256"] = hashlib.sha256(
        protocol.read_text(encoding="utf-8").encode("utf-8")
    ).hexdigest()
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    reports = {season: load_reports(root, season) for season in ("2024_25", "2025_26")}
    labels = {s: availability_labels(root, s, r) for s, r in reports.items()}
    labels = {s: attach_causal_availability(root, s, frame) for s, frame in labels.items()}
    result = {
        "scope": "Retrospective report-listed, explicitly confirmed final roster sample; not whole-league availability",
        "availability": {},
        "spillover": {},
    }
    val = labels["2024_25"]
    if val.empty or labels["2025_26"].empty:
        result["availability"]["status"] = "insufficient_labels"
    else:
        base, state = online_availability(val, 0)
        candidates, winner = [], 0
        for strength in (20, 60):
            candidate, _ = online_availability(val, strength)
            gate = paired_gate(base, candidate)
            result["availability"][str(strength)] = {"selection_gate": gate}
            if gate["accepted"]:
                candidates.append((candidate.primary.mean(), strength))
        if candidates:
            winner = min(candidates)[1]
        (output / "frozen_availability.json").write_text(
            json.dumps({"strength": winner}), encoding="utf-8"
        )
        test_base, _ = online_availability(labels["2025_26"], 0, state)
        test, _ = online_availability(labels["2025_26"], winner, state)
        result["availability"].update(
            {
                "selected_strength": winner,
                "assessment_gate": paired_gate(test_base, test),
                "selection_n": len(base),
                "assessment_n": len(test),
                "assessment_negative_n": int((test.actual == 0).sum()),
                "baseline_brier": float(test_base.primary.mean()),
                "candidate_brier": float(test.primary.mean()),
                "deployment": "No live deployment; reported/roster-confirmed selection bias remains",
            }
        )
        val.to_csv(output / "availability_selection_labels.csv", index=False)
        test.to_csv(output / "availability_assessment_predictions.csv", index=False)
    validation = spillover_replay(root, "2024_25", reports["2024_25"])
    accepted = []
    for scale in (0, 0.5):
        if validation[1.0].empty:
            result["spillover"][str(scale)] = {
                "accepted": False,
                "reason": "insufficient_roster_replay",
            }
            continue
        gate = paired_gate(validation[1.0], validation[scale])
        result["spillover"][str(scale)] = {"selection_gate": gate}
        if gate["accepted"]:
            accepted.append((validation[scale].primary.mean(), scale))
    winner = min(accepted)[1] if accepted else 1.0
    (output / "frozen_spillover.json").write_text(json.dumps({"scale": winner}), encoding="utf-8")
    assessment = spillover_replay(root, "2025_26", reports["2025_26"])
    if not assessment[1.0].empty:
        result["spillover"].update(
            {
                "selected_scale": winner,
                "selection_n": len(validation[1.0]),
                "assessment_n": len(assessment[1.0]),
                "assessment_gate": paired_gate(assessment[1.0], assessment[winner]),
                "baseline_minute_mae": float(assessment[1.0].primary.mean()),
                "candidate_minute_mae": float(assessment[winner].primary.mean()),
            }
        )
    result["spillover"]["deployment"] = (
        "Exploratory only: past-observation roster proxy and pooled positions; not live-engine calibration"
    )
    (output / "experiments.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

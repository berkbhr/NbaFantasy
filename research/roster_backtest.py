"""Frozen-protocol synthetic leagues scored on actual historical production."""

import json
from dataclasses import replace
from datetime import datetime, timezone
from time import perf_counter

import numpy as np
import pandas as pd

from src.calibrate import gate, replay
from src.matchup_engine import ALL_CATEGORIES, MatchupEngine
from src.model_policy import load_model_policy
from src.prospective import weekly_category_outcome, write_once
from src.validation import previous_season

from .common import ROOT, sha
from .pilot import run as build_state


def score_lineups(lineups, actual):
    """Only frozen pre-outcome active starts count; bench stats never enter."""
    total = dict.fromkeys(ALL_CATEGORIES, 0.0)
    for day, ids in lineups.items():
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate player in daily active lineup")
        for pid in ids:
            row = actual.get((str(day), int(pid)), {})
            for stat in total:
                total[stat] += float(row.get(stat, 0))
    return total


def calibration(probabilities, outcome):
    brier = []
    points = 0.0
    for cat, win in probabilities.items():
        tie = probabilities.ties[cat]
        pred = (win, tie, 1 - win - tie)
        state = outcome["categories"][cat]
        target = (state == "win", state == "draw", state == "loss")
        brier.append(sum((p - y) ** 2 for p, y in zip(pred, target)))
        points += win + 0.5 * tie
    return float(np.mean(brier)), points - outcome["category_points"]


def make_rosters(pool, positions, seed):
    rng = np.random.default_rng(seed)
    rosters = [[] for _ in range(14)]
    for rnd in range(13):
        tier = pool[14 * rnd : 14 * (rnd + 1)].copy()
        rng.shuffle(tier)
        for i, pid in enumerate(tier):
            rosters[i].append(pid)
    profile = ("balanced", "center_heavy", "guard_heavy")[seed % 3]
    wanted = "C" if profile == "center_heavy" else "G"
    if profile != "balanced":
        for rnd in (10, 11, 12):
            if wanted in positions[rosters[0][rnd]]:
                continue
            other = next((i for i in range(1, 14) if wanted in positions[rosters[i][rnd]]), None)
            if other is not None:
                rosters[0][rnd], rosters[other][rnd] = rosters[other][rnd], rosters[0][rnd]
    occupied = {pid for team in rosters for pid in team}
    if len(occupied) != 182:
        raise ValueError("Roster ownership collision")
    return rosters, profile


def paired_summary(frame):
    summary = {"team_weeks": len(frame), "calendar_weeks": int(frame.week.nunique())}
    for strategy in ("model", "schedule"):
        gains = frame[strategy + "_points"] - frame.base_points
        weeks = pd.DataFrame({"week": frame.week, "gain": gains}).groupby("week").gain.mean()
        samples = (
            np.random.default_rng(42).choice(weeks.to_numpy(), (2000, len(weeks))).mean(axis=1)
        )
        summary[strategy] = {
            "mean_category_point_gain": float(gains.mean()),
            "weekly_block_ci95": np.quantile(samples, [0.025, 0.975]).tolist(),
            "improved": int((gains > 0).sum()),
            "worsened": int((gains < 0).sum()),
            "unchanged": int((gains == 0).sum()),
        }
    return summary


def run(seeds=20, max_weeks=None):
    if not 1 <= seeds <= 20 or (max_weeks is not None and max_weeks < 1):
        raise ValueError("Use1..20 seeds and a positive week limit")
    start = perf_counter()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "research/runs" / ("roster_" + run_id)
    output.mkdir(parents=True, exist_ok=False)
    baseline = load_model_policy()
    paths = sorted((ROOT / "src").glob("*.py")) + sorted((ROOT / "research").glob("*.py"))
    paths += [ROOT / "config" / name for name in ("model_policy.json", "rotation_policy.json")]
    paths += sorted((ROOT / "data/raw").glob("player_logs_202[2345]*.parquet"))
    paths += [ROOT / "data/processed" / f"schedule_{s}.parquet" for s in ("2024_25", "2025_26")]
    paths += sorted((ROOT / "data/archive/historical_labels_v2").rglob("*.gz"))
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
    protocol = {
        "version": 1,
        "baseline": baseline.to_dict(),
        "seeds_per_season": seeds,
        "max_weeks": max_weeks,
        "warmup": "First Monday after14 calendar days of logs",
        "role_candidates": ["recent_blend", "ewma"],
        "role_selection": "2024_25 minute MSE with existing chronological gate; freeze winner then assess2025 once",
        "rosters": "14x13, prior-MPG tiers, balanced/center-heavy/guard-heavy; weekly synthetic ownership; no invented IL stashes",
        "eligibility": "Past observed team and position, completed-prior GP>=10; excludes unseen/unknown-position players and many rookies",
        "injuries": "Off in this controlled reference; no injury/spillover or healthy-status validation claim",
        "schedule": "Fixed final historical calendar, not an archived as-of schedule; postponement timing optimism possible",
        "lineups": "Freeze whole remaining-week active starts before reading realized production; opponent default daily policy",
        "actions": "One focal team per league-week; max1 immediate synthetic add/drop; no other manager reactions; current core protection",
        "scope": "Conditional NBA outcome robustness reference; synthetic FA/eligibility, no actual Yahoo ownership or causal gain claim",
        "primary": "Realized category points net of dropped player and active-slot effects",
        "uncertainty": "Paired calendar-week bootstrap2000 draws, seed42; leagues are not independent NBA seasons",
        "promotion": "None; serving configs unchanged",
    }
    write_once(output / "protocol.json.gz", {"protocol": protocol, "source_sha256": hashes})
    print("Frozen protocol", output, flush=True)
    first = replay("2024_25", baseline)
    first["minute_mse"] = first.minute_mae**2
    options, selection = [], []
    for role in protocol["role_candidates"]:
        policy = replace(baseline, role=role)
        candidate = replay("2024_25", policy)
        candidate["minute_mse"] = candidate.minute_mae**2
        check = gate(first, candidate, "minute_mse")
        selection.append(
            {"role": role, "minute_mse": float(candidate.minute_mse.mean()), "gate": check}
        )
        if check["accepted"]:
            options.append((candidate.minute_mse.mean(), role, policy))
    winner = min(options, key=lambda x: (x[0], x[1]))[2] if options else baseline
    write_once(
        output / "frozen_role.json.gz",
        {
            "baseline_minute_mse": float(first.minute_mse.mean()),
            "candidates": selection,
            "winner": winner.to_dict(),
        },
    )
    print("Frozen role winner", winner.role, flush=True)
    second = replay("2025_26", baseline)
    second["minute_mse"] = second.minute_mae**2
    assessment = {"candidate_differs": winner != baseline}
    assessment["baseline"] = {
        "n": len(second),
        "minute_mse": float(second.minute_mse.mean()),
        "minute_mae": float(second.minute_mae.mean()),
    }
    if winner != baseline:
        alternative = replay("2025_26", winner)
        alternative["minute_mse"] = alternative.minute_mae**2
        assessment["gate"] = gate(second, alternative, "minute_mse")
        assessment["candidate"] = {
            "n": len(alternative),
            "minute_mse": float(alternative.minute_mse.mean()),
            "minute_mae": float(alternative.minute_mae.mean()),
        }
    write_once(output / "role_assessment.json.gz", assessment)
    # Roster reference stays on serving baseline; it cannot choose a new role
    # policy using synthetic-league outcomes from the assessment season.
    rows, calibration_rows = [], []
    for season, seed_start in (("2024_25", 1000), ("2025_26", 2000)):
        logs = pd.read_parquet(ROOT / "data/raw" / f"player_logs_{season}.parquet")
        dates = pd.to_datetime(logs.GAME_DATE)
        # This dictionary is scoring-only and never passed to build_state or engine.
        actual = {
            (str(pd.Timestamp(r["GAME_DATE"]).date()), int(r["PLAYER_ID"])): r
            for r in logs.to_dict("records")
        }
        # Zero contribution on a planned start requires a complete NBA day,
        # not an inference about the player's injury/DNP reason.
        for _, game in logs.groupby("GAME_ID"):
            if game.TEAM_ID.nunique() != 2 or game.groupby("TEAM_ID").PLAYER_ID.nunique().min() < 5:
                raise ValueError(
                    "Incomplete NBA game cache; cannot zero missing active contributions"
                )
        first_week = dates.min() + pd.Timedelta(days=14)
        first_week += pd.Timedelta(days=(7 - first_week.weekday()) % 7)
        weeks = list(pd.date_range(first_week, dates.max() - pd.Timedelta(days=6), freq="7D"))
        if max_weeks:
            weeks = weeks[:max_weeks]
        for wi, week in enumerate(weeks):
            state = build_state(
                cutoff=str(week.date()), season=season, policy=baseline, return_context=True
            )
            players, positions, teams, pool = [
                state[k] for k in ("players", "positions", "teams", "pool")
            ]
            engine = MatchupEngine(
                players,
                state["schedule"],
                pd.DataFrame([{"PLAYER_ID": p, "POSITION": positions[p]} for p in players]),
                season=season,
                prior_season=previous_season(season),
                team_map=teams,
                use_positional_depth_and_injury_boost=False,
            )
            end = week + pd.Timedelta(days=6)
            with engine.projection_session():
                for seed in range(seed_start, seed_start + seeds):
                    rosters, profile = make_rosters(pool, positions, seed)
                    occupied = {p for team in rosters for p in team}
                    candidates = [p for p in pool if p not in occupied]
                    # 7 disjoint pairings; cyclic own-side ensures no fixed manager advantage.
                    opponent = 1 + wi % 13
                    rest = [i for i in range(1, 14) if i != opponent]
                    np.random.default_rng(seed + wi * 100000).shuffle(rest)
                    order = [0, opponent] + rest
                    for pair in range(7):
                        mine, theirs = rosters[order[pair * 2]], rosters[order[pair * 2 + 1]]
                        a, b, _, probs, _ = engine.project_matchup(mine, theirs, week, end)
                        observed_a = score_lineups(a["meta"]["lineups"], actual)
                        observed_b = score_lineups(b["meta"]["lineups"], actual)
                        truth = weekly_category_outcome(observed_a, observed_b)
                        brier, error = calibration(probs, truth)
                        calibration_rows.append(
                            {
                                "season": season,
                                "week": str(week.date()),
                                "seed": seed,
                                "profile": profile,
                                "pair": pair,
                                "brier": brier,
                                "category_point_error": error,
                                "actual_points": truth["category_points"],
                                **{cat + "_win": float(p) for cat, p in probs.items()},
                                **{cat + "_tie": float(p) for cat, p in probs.ties.items()},
                                **{
                                    cat + "_result": result
                                    for cat, result in truth["categories"].items()
                                },
                            }
                        )
                        if pair:
                            continue
                        moves = engine.recommend_add_drop_moves(
                            mine, theirs, candidates, week, end, top_k=1
                        )
                        model_total = observed_a
                        if moves:
                            move = moves[0]
                            changed = [p for p in mine if p != move["drop_id"]] + [move["add_id"]]
                            trial = engine.project_matchup(changed, theirs, week, end)[0]
                            model_total = score_lineups(trial["meta"]["lineups"], actual)
                        values = {
                            p: engine._player_value(
                                {
                                    "PROJ": engine._build_player_game_projection(
                                        p, target_minutes=players[p].base_expected_minutes
                                    )[0]
                                },
                                engine.default_norm_weights,
                            )
                            for p in mine
                        }
                        protected = set(sorted(mine, key=lambda p: (-values[p], str(p)))[:11])
                        drops = [p for p in mine if p not in protected]

                        def games(p):
                            return len(engine._get_player_schedule(teams[p], week, end))

                        add = min(candidates, key=lambda p: (-games(p), str(p)))
                        drop = min(drops, key=lambda p: (games(p), values[p], str(p)))
                        stream_roster = [p for p in mine if p != drop] + [add]
                        trial = engine.project_matchup(stream_roster, theirs, week, end)[0]
                        stream_total = score_lineups(trial["meta"]["lineups"], actual)
                        rows.append(
                            {
                                "season": season,
                                "week": str(week.date()),
                                "seed": seed,
                                "profile": profile,
                                "base_points": truth["category_points"],
                                "model_points": weekly_category_outcome(model_total, observed_b)[
                                    "category_points"
                                ],
                                "schedule_points": weekly_category_outcome(
                                    stream_total, observed_b
                                )["category_points"],
                                "move": bool(moves),
                                "fa_candidates": len(candidates),
                                "model_add": moves[0]["add_id"] if moves else None,
                                "model_drop": moves[0]["drop_id"] if moves else None,
                                "schedule_add": add,
                                "schedule_drop": drop,
                            }
                        )
            print(season, str(week.date()), "done", len(rows), "action cases", flush=True)
    action_frame, probability_frame = pd.DataFrame(rows), pd.DataFrame(calibration_rows)
    if any(sha(ROOT / p) != h for p, h in hashes.items()):
        raise RuntimeError("Experiment input/code changed; results are provisional")
    summary = {
        s: paired_summary(action_frame[action_frame.season == s]) for s in ("2024_25", "2025_26")
    }
    summary["calibration"] = (
        probability_frame.groupby("season")
        .agg(
            cases=("brier", "size"),
            brier=("brier", "mean"),
            point_mae=("category_point_error", lambda x: x.abs().mean()),
            bias=("category_point_error", "mean"),
        )
        .to_dict("index")
    )
    summary["seconds"] = perf_counter() - start
    summary["profiles"] = {
        s + ":" + profile: paired_summary(group)
        for (s, profile), group in action_frame.groupby(["season", "profile"])
    }
    reliability = []
    for s, group in probability_frame.groupby("season"):
        for cat in ("PTS", "REB", "AST", "STL", "BLK", "TOV", "FG3M", "FG_PCT", "FT_PCT"):
            bins = (group[cat + "_win"] * 10).astype(int).clip(0, 9)
            for bucket in sorted(bins.unique()):
                chosen = group[bins == bucket]
                reliability.append(
                    {
                        "season": s,
                        "category": cat,
                        "bin": int(bucket),
                        "n": len(chosen),
                        "predicted_win": float(chosen[cat + "_win"].mean()),
                        "observed_win": float((chosen[cat + "_result"] == "win").mean()),
                    }
                )
    action_frame.to_csv(output / "actions.csv.gz", index=False)
    probability_frame.to_csv(output / "probabilities.csv.gz", index=False)
    write_once(output / "reliability.json.gz", reliability)
    write_once(output / "summary.json.gz", summary)
    print(json.dumps({"output": str(output), "summary": summary}, indent=2), flush=True)
    return output, summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--weeks", type=int)
    args = parser.parse_args()
    run(args.seeds, args.weeks)

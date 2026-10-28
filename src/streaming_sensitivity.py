"""Posthoc stronger-streaming controls; never tune on realized target scores."""

import gzip
import json
from time import perf_counter

import pandas as pd

from .matchup_engine import MatchupEngine
from .model_policy import ModelPolicy
from .prospective import weekly_category_outcome, write_once
from .research import ROOT, sha
from .roster_backtest import make_rosters, paired_summary, score_lineups
from .roster_pilot import run as build_state
from .validation import previous_season


def run(experiment):
    output = ROOT / "data/archive/experiments" / experiment
    original = json.loads(gzip.decompress((output / "protocol.json.gz").read_bytes()))
    if (output / "streaming_sensitivity_protocol.json.gz").exists():
        raise FileExistsError("Sensitivity already recorded; use a new explicit version")
    for path, digest in original["source_sha256"].items():
        if sha(ROOT / path) != digest:
            raise ValueError("Original baseline data/source changed")
    hashes = {
        **original["source_sha256"],
        "src/streaming_sensitivity.py": sha(ROOT / "src/streaming_sensitivity.py"),
    }
    write_once(
        output / "streaming_sensitivity_protocol.json.gz",
        {
            "status": "Posthoc diagnostic; original season results already inspected, not a new unseen test",
            "strategies": [
                "games_then_base_minutes",
                "games_times_base_minutes_times_availability",
            ],
            "drop": "Same recorded legal drop as original simple streaming control",
            "selection": "Exactly these two controls; no selecting/tuning on their realized results",
            "source_sha256": hashes,
        },
    )
    started = perf_counter()
    actions = pd.read_csv(output / "actions.csv.gz")
    policy = ModelPolicy(**original["protocol"]["baseline"])
    rows = []
    for season, cases in actions.groupby("season"):
        logs = pd.read_parquet(ROOT / "data/raw" / f"player_logs_{season}.parquet")
        actual = {
            (str(pd.Timestamp(r["GAME_DATE"]).date()), int(r["PLAYER_ID"])): r
            for r in logs.to_dict("records")
        }
        for wi, (week, weekly) in enumerate(cases.groupby("week", sort=True)):
            state = build_state(cutoff=week, season=season, policy=policy, return_context=True)
            players, positions, teams, pool = [
                state[k] for k in ("players", "positions", "teams", "pool")
            ]
            start = pd.Timestamp(week)
            end = start + pd.Timedelta(days=6)
            engine = MatchupEngine(
                players,
                state["schedule"],
                pd.DataFrame([{"PLAYER_ID": p, "POSITION": positions[p]} for p in players]),
                season=season,
                prior_season=previous_season(season),
                team_map=teams,
                use_positional_depth_and_injury_boost=False,
            )
            with engine.projection_session():
                for case in weekly.to_dict("records"):
                    seed = int(case["seed"])
                    rosters, _ = make_rosters(pool, positions, seed)
                    mine, theirs = rosters[0], rosters[1 + wi % 13]
                    occupied = {p for team in rosters for p in team}
                    candidates = [p for p in pool if p not in occupied]
                    base, opp = engine.project_matchup(mine, theirs, start, end)[:2]
                    opponent = score_lineups(opp["meta"]["lineups"], actual)
                    truth = weekly_category_outcome(
                        score_lineups(base["meta"]["lineups"], actual), opponent
                    )
                    if truth["category_points"] != case["base_points"]:
                        raise ValueError("Frozen baseline does not reproduce")
                    drop = int(case["schedule_drop"])

                    def games(p):
                        return len(engine._get_player_schedule(teams[p], start, end))

                    additions = {
                        "quality_tie": min(
                            candidates,
                            key=lambda p: (-games(p), -players[p].base_expected_minutes, str(p)),
                        ),
                        "total_minutes": min(
                            candidates,
                            key=lambda p: (
                                -games(p)
                                * players[p].base_expected_minutes
                                * players[p].get_effective_game_availability(),
                                str(p),
                            ),
                        ),
                    }
                    row = dict(case)
                    for strategy, add in additions.items():
                        roster = [p for p in mine if p != drop] + [add]
                        trial = engine.project_matchup(roster, theirs, start, end)[0]
                        outcome = weekly_category_outcome(
                            score_lineups(trial["meta"]["lineups"], actual), opponent
                        )
                        row[strategy + "_points"] = outcome["category_points"]
                        row[strategy + "_add"] = add
                    rows.append(row)
            print(season, week, "strong controls", len(rows), flush=True)
    frame = pd.DataFrame(rows)
    summary = {}
    for season, group in frame.groupby("season"):
        summary[season] = {}
        for strategy in ("quality_tie", "total_minutes"):
            comparison = group.copy()
            comparison["schedule_points"] = comparison[strategy + "_points"]
            compared = paired_summary(comparison)
            # Paired model-minus-control interval, preserving calendar blocks.
            comparison["base_points"] = comparison[strategy + "_points"]
            summary[season][strategy] = {
                "against_no_move": compared["schedule"],
                "model_minus_control": paired_summary(comparison)["model"],
            }
    if any(sha(ROOT / path) != digest for path, digest in hashes.items()):
        raise RuntimeError("Sensitivity sources changed")
    frame.to_csv(output / "streaming_sensitivity.csv.gz", index=False)
    write_once(
        output / "streaming_sensitivity_summary.json.gz",
        {"seconds": perf_counter() - started, "summary": summary},
    )
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment")
    run(parser.parse_args().experiment)

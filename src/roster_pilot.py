"""Small synthetic-ownership timing pilot, using only pre-cutoff player data.

This is neither a historical Yahoo league nor a decision-performance test.
"""

import gzip
import json
from time import perf_counter

import pandas as pd

from .bayesian_model import BayesianPlayer
from .injury_tracker import normalize_name
from .matchup_engine import MatchupEngine
from .model_policy import load_model_policy, update_role
from .priors import get_positional_averages, load_prior_season
from .research import ROOT, sha
from .validation import previous_season


def run(
    seeds=(9000, 9001),
    cutoff="2024-11-05",
    candidate_count=12,
    season="2024_25",
    policy=None,
    return_context=False,
):
    started = perf_counter()
    cutoff = pd.Timestamp(cutoff)
    policy = policy or load_model_policy()
    paths = [
        ROOT / "data/raw" / f"player_logs_{s}.parquet"
        for s in (previous_season(previous_season(season)), previous_season(season), season)
    ]
    paths += [ROOT / f"data/processed/schedule_{season}.parquet", ROOT / "config/model_policy.json"]
    label_paths = sorted(
        p
        for p in (ROOT / "data/archive/historical_labels_v2" / season).glob("*.gz")
        if pd.Timestamp(p.name.split(".")[0]) < cutoff
    )
    paths += label_paths + sorted((ROOT / "src").glob("*.py"))
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    logs = pd.read_parquet(paths[2])
    logs = logs[pd.to_datetime(logs.GAME_DATE) < cutoff].sort_values(
        ["GAME_DATE", "GAME_ID", "PLAYER_ID"]
    )
    positions_by_name = {}
    for path in label_paths:
        for row in json.loads(gzip.decompress(path.read_bytes()))["rows"]:
            if row.get("position"):
                positions_by_name[normalize_name(row["name"])] = row["position"]
    priors = load_prior_season(previous_season(season), policy=policy)
    averages = get_positional_averages(priors, pos_dict={})
    players, histories, anchors, teams, positions = {}, {}, {}, {}, {}
    for row in logs.to_dict("records"):
        pid = int(row["PLAYER_ID"])
        if pid not in players:
            players[pid] = BayesianPlayer(pid, row["PLAYER_NAME"], policy=policy)
            players[pid].initialize_priors(priors.get(pid), averages)
            histories[pid], anchors[pid] = [], players[pid].base_expected_minutes
        bp = players[pid]
        trade = pid in teams and teams[pid] != row["TEAM_ID"]
        bp.update_stats(
            row["GAME_DATE"], float(row["MIN"]), row, is_event_reset=trade, game_id=row["GAME_ID"]
        )
        if trade:
            histories[pid].clear()
            anchors[pid] = bp.base_expected_minutes
        if row["MIN"] > 0:
            histories[pid].append(
                (str(row["GAME_ID"]), float(row["MIN"]), row["GAME_DATE"], row["TEAM_ID"])
            )
            update_role(bp, histories[pid], anchors[pid], policy)
        teams[pid] = int(row["TEAM_ID"])
        positions[pid] = positions_by_name.get(normalize_name(row["PLAYER_NAME"]))
    pool = sorted(
        (pid for pid in players if positions[pid] and priors.get(pid, {}).get("GP", 0) >= 10),
        key=lambda pid: (-priors[pid]["MIN"] / priors[pid]["GP"], pid),
    )
    if len(pool) < 182 + candidate_count:
        raise ValueError("Insufficient causally known pool for pilot")
    schedule = pd.read_parquet(paths[3])
    if return_context:
        if any(sha(ROOT / p) != h for p, h in hashes.items()):
            raise RuntimeError("State-building inputs changed")
        return {
            "players": players,
            "teams": teams,
            "positions": positions,
            "pool": pool,
            "schedule": schedule,
            "hashes": hashes,
        }
    results = []
    import numpy as np

    for seed in seeds:
        rng = np.random.default_rng(seed)
        rosters = [[] for _ in range(14)]
        for rnd in range(13):
            tier = pool[rnd * 14 : (rnd + 1) * 14].copy()
            rng.shuffle(tier)
            for slot, pid in enumerate(tier):
                rosters[slot].append(pid)
        occupied = {p for roster in rosters for p in roster}
        candidates = pool[182 : 182 + candidate_count]
        assert len(occupied) == 182 and not occupied.intersection(candidates)
        engine = MatchupEngine(
            players,
            schedule,
            pd.DataFrame([{"PLAYER_ID": p, "POSITION": positions[p]} for p in players]),
            season=season,
            prior_season=previous_season(season),
            team_map=teams,
            use_positional_depth_and_injury_boost=False,
        )
        end = cutoff + pd.Timedelta(days=6 - cutoff.weekday())
        start = perf_counter()
        base = engine.project_matchup(rosters[0], rosters[1], cutoff, end)
        base_seconds = perf_counter() - start
        start = perf_counter()
        moves = engine.recommend_add_drop_moves(rosters[0], rosters[1], candidates, cutoff, end)
        move_seconds = perf_counter() - start
        results.append(
            {
                "seed": seed,
                "teams": 14,
                "roster_size": 13,
                "occupied": 182,
                "actual_il_stashes": 0,
                "hypothetical_fa_candidates": len(candidates),
                "remaining_start": str(cutoff.date()),
                "remaining_end": str(end.date()),
                "matchup_seconds": base_seconds,
                "recommendation_seconds": move_seconds,
                "evaluated_matchups": 1,
                "returned_moves": len(moves),
                "baseline_expected_category_points": base[2],
            }
        )
    if any(sha(ROOT / p) != h for p, h in hashes.items()):
        raise RuntimeError("Pilot inputs changed during execution")
    return {
        "scope": "Timing/legality only; hypothetical ownership, historical NBA G/F/C eligibility, injuries off; not a performance estimate",
        "cutoff": str(cutoff.date()),
        "last_observation": str(pd.to_datetime(logs.GAME_DATE).max().date()),
        "available_pool": len(pool),
        "source_sha256": hashes,
        "results": results,
        "total_seconds": perf_counter() - started,
        "future_outcomes_used_in_predictions": False,
        "policy_selection": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

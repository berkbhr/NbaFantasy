"""Bounded injury/IL legality pilot. No realized decision-performance claim."""

import gzip
import json
from time import perf_counter

import numpy as np
import pandas as pd

from src.injury_tracker import normalize_name
from src.matchup_engine import MatchupEngine
from src.model_policy import load_model_policy
from src.rotation_policy import RotationPolicy

from .common import ROOT, sha
from .pilot import run as build_state
from .roster_backtest import make_rosters


def allocate_il(rosters, pool, out_ids, seed):
    """Move eligible owned OUTs first; never invent two stashes per team."""
    teams = [list(r) for r in rosters]
    rank = {pid: i for i, pid in enumerate(pool)}
    stashes = []
    for team in teams:
        stashes.append(sorted((p for p in team if p in out_ids), key=rank.get)[:2])
    occupied = {p for team in teams for p in team}
    free_active = [p for p in pool if p not in occupied and p not in out_ids]
    order = list(np.random.default_rng(seed).permutation(len(teams)))
    for i in order:
        needed = len(stashes[i])
        if len(free_active) < needed:
            raise ValueError("Insufficient legal active players")
        teams[i].extend(free_active[:needed])
        del free_active[:needed]
    occupied = {p for team in teams for p in team}
    free_out = [p for p in pool if p in out_ids and p not in occupied]
    for _ in range(2):
        for i in order:
            if len(stashes[i]) < 2 and free_out:
                pid = free_out.pop(0)
                teams[i].append(pid)
                stashes[i].append(pid)
    for team, stash in zip(teams, stashes):
        if len(team) - len(stash) != 13 or len(stash) > 2 or not set(stash) <= out_ids:
            raise ValueError("Illegal IL allocation")
    if len({p for t in teams for p in t}) != sum(map(len, teams)):
        raise ValueError("Duplicate ownership")
    return teams, {p for stash in stashes for p in stash}


def asof_report(season, cutoff):
    choices = []
    for path in (ROOT / "data/archive/historical_injuries" / season).glob("*.gz"):
        if pd.Timestamp(path.name.split(".")[0]).date() > cutoff.date():
            continue
        record = json.loads(gzip.decompress(path.read_bytes()))
        if record.get("status") != "usable":
            continue
        stamp = pd.Timestamp(record["report_at"])
        if stamp <= cutoff and cutoff - stamp <= pd.Timedelta(hours=48):
            choices.append((stamp, path, record))
    if not choices:
        raise ValueError("No usable pre-cutoff injury report within48h")
    return max(choices, key=lambda item: item[0])


def run():
    results = []
    role = load_model_policy()
    candidate_path = ROOT / "config/rotation_candidate.json"
    research = json.loads(candidate_path.read_text(encoding="utf-8"))
    policies = {"active": RotationPolicy(), "research_only": RotationPolicy(**research["policy"])}
    for season, date in (("2024_25", "2024-11-11"), ("2025_26", "2025-11-10")):
        cutoff = pd.Timestamp(date + " 09:00", tz="America/New_York")
        stamp, path, report = asof_report(season, cutoff)
        state = build_state(season=season, cutoff=date, policy=role, return_context=True)
        players, teams, positions, pool = [
            state[k] for k in ("players", "teams", "positions", "pool")
        ]
        names = {normalize_name(bp.name): pid for pid, bp in players.items()}
        skipped = 0
        for row in report["rows"]:
            pid = names.get(normalize_name(row["name"]))
            if row.get("reason_type") == "GLEAGUE" or pid not in players:
                skipped += 1
                continue
            players[pid].update_injury_status(row["status"], report_date=report["report_at"])
        out_ids = {p for p in pool if players[p].injury_status == "OUT"}
        # Same lagged absence correction as the existing historical rotation
        # replay. Do not distribute opportunities already embedded in role.
        logs = pd.read_parquet(ROOT / "data/raw" / f"player_logs_{season}.parquet")
        logs = logs[pd.to_datetime(logs.GAME_DATE) < pd.Timestamp(date)]
        played = {
            (int(t), str(g)): set(box.loc[box.MIN > 0, "PLAYER_ID"].astype(int))
            for (t, g), box in logs.groupby(["TEAM_ID", "GAME_ID"])
            if box.PLAYER_ID.nunique() >= 5
        }
        for pid, bp in players.items():
            own = (
                logs[(logs.PLAYER_ID == pid) & (logs.TEAM_ID == teams[pid]) & (logs.MIN > 0)]
                .sort_values("GAME_DATE")
                .tail(5)
            )
            games = [
                played[(teams[pid], str(g))] for g in own.GAME_ID if (teams[pid], str(g)) in played
            ]
            bp.baseline_absences = (
                {
                    other: getattr(bp, "role_observation_weight", 0)
                    * sum(other not in g for g in games)
                    / len(games)
                    for other in players
                    if other != pid and teams[other] == teams[pid]
                }
                if games
                else {}
            )
        for seed in (9000, 9001):
            base, _ = make_rosters(pool, positions, seed)
            rosters, stashes = allocate_il(base, pool, out_ids, seed)
            occupied = {p for r in rosters for p in r}
            candidates = [p for p in pool if p not in occupied][:12]
            for label, policy in policies.items():
                started = perf_counter()
                engine = MatchupEngine(
                    players,
                    state["schedule"],
                    pd.DataFrame([{"PLAYER_ID": p, "POSITION": positions[p]} for p in players]),
                    season=season,
                    team_map=teams,
                    rotation_policy=policy,
                    use_positional_depth_and_injury_boost=True,
                )
                engine.yahoo_already_stashed_ids = stashes.copy()
                moves = engine.recommend_add_drop_moves(
                    rosters[0],
                    rosters[1],
                    candidates,
                    date,
                    pd.Timestamp(date) + pd.Timedelta(days=6),
                    top_k=1,
                )
                if any(m["add_id"] in occupied for m in moves):
                    raise ValueError("Owned player recommended")
                results.append(
                    {
                        "season": season,
                        "seed": seed,
                        "policy": label,
                        "report_at": stamp.isoformat(),
                        "cutoff": cutoff.isoformat(),
                        "report_sha256": sha(path),
                        "report_out_ids_in_known_pool": len(out_ids),
                        "unmatched_or_gleague_rows": skipped,
                        "occupied": len(occupied),
                        "il_stashes": len(stashes),
                        "focal_team_size": len(rosters[0]),
                        "fa_candidates": len(candidates),
                        "returned_moves": len(moves),
                        "seconds": perf_counter() - started,
                    }
                )
    return {
        "scope": "Legality/timing pilot only: medical OUT approximates IL eligibility; incomplete report coverage, unknown future returns, no outcomes scored; no policy promotion",
        "notes": "Unknown report players and never-observed players are not silently fabricated; all2IL slots need not be filled",
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

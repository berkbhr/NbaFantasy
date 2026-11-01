"""Bounded offline trade profiler; never submits trades or sends notifications."""

import argparse
import cProfile
import hashlib
import json
import time
from pathlib import Path

import pandas as pd

from .fantasy_calendar import resolve_trade_calendar
from .trade_context import load_context
from .trade_profiling import BenchmarkTimeout, TradeProfiler, instrument
from .trade_search import search_trades


def benchmark_bundle(context, weeks=1, shortlist=4, finalists=1, allow_synthetic=False):
    data = {
        "proposal": {
            "our_team": "7",
            "other_team": None,
            "snapshot_id": context.sync_id,
            "give_yahoo_ids": [],
            "receive_yahoo_ids": [],
        },
        "fixture_horizon_weeks": weeks,
        "rules": {"verified": False, "max_weekly_adds": context.weekly_add_limit},
        "completion": {"enabled": True, "candidate_limit": 8, "min_gain_per_week": 0.05},
        "streaming": {
            "enabled": True,
            "candidate_limit": 8,
            "beam_width": 6,
            "finalists": 6,
            "min_gain_per_week": 0.05,
        },
        "search": {
            "shortlist_size": shortlist,
            "streaming_finalists": finalists,
            "screen_with_fa": "asymmetric",
            "screen_fa_candidates": 1,
        },
    }
    try:
        data = resolve_trade_calendar(context, data)
        fixture_scope = "confirmed_yahoo"
    except ValueError:
        if not allow_synthetic:
            raise
        teams = sorted(context.rosters, key=int)
        today = (
            pd.Timestamp(context.as_of).tz_convert("America/New_York").tz_localize(None).normalize()
        )
        first = today + pd.Timedelta(days=7 - today.weekday())
        data["weeks"] = []
        for index in range(weeks):
            start = first + pd.Timedelta(days=7 * index)
            data["weeks"].append(
                {
                    "start": start.date().isoformat(),
                    "end": (start + pd.Timedelta(days=6)).date().isoformat(),
                    "fixtures": [[teams[i], teams[-1 - i]] for i in range(len(teams) // 2)],
                }
            )
            teams = [teams[0], teams[-1], *teams[1:-1]]
        fixture_scope = "synthetic_performance_only"
    data["proposal"]["effective_date"] = data["weeks"][0]["start"]
    usage = {w["start"]: {t: 0 for t in context.rosters} for w in data["weeks"]}
    for mode in ("completion", "streaming"):
        data[mode]["adds_used_by_week"] = usage
    data["benchmark_scope"] = (
        f"Performance only: fixtures={fixture_scope}; future add usage=assumed zero; no market snapshot. Not trade advice."
    )
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weeks", type=int, default=1, choices=range(1, 5))
    parser.add_argument("--shortlist", type=int, default=4, choices=range(1, 51))
    parser.add_argument("--finalists", type=int, default=1, choices=range(1, 6))
    parser.add_argument("--max-seconds", type=float, default=180)
    parser.add_argument("--allow-synthetic-fixtures", action="store_true")
    parser.add_argument("--input", type=Path, help="Replay the identical saved benchmark bundle")
    parser.add_argument("--cache", choices=("on", "off"), default="on")
    parser.add_argument(
        "--no-cprofile",
        action="store_true",
        help="Wall-clock stage timing without deterministic call-profiler overhead",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    loaded = time.perf_counter()
    context = load_context()
    bundle = (
        json.loads(args.input.read_text(encoding="utf-8"))
        if args.input
        else benchmark_bundle(
            context, args.weeks, args.shortlist, args.finalists, args.allow_synthetic_fixtures
        )
    )
    if bundle["proposal"]["snapshot_id"] != context.sync_id:
        raise ValueError("Benchmark input belongs to a different roster capture")
    bundle.setdefault("search", {})["reuse_projections"] = args.cache == "on"
    input_path = args.output.with_suffix(".input.json")
    input_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    load_seconds = time.perf_counter() - loaded
    print(
        json.dumps(
            {
                "event": "profile_started",
                "load_seconds": load_seconds,
                "scope": bundle.get("benchmark_scope"),
                "output": str(args.output),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    profiler, cpu_profile = TradeProfiler(args.max_seconds), cProfile.Profile()
    result, error = None, None
    try:
        with instrument(profiler):
            if not args.no_cprofile:
                cpu_profile.enable()
            result = search_trades(context, bundle)
    except BenchmarkTimeout as exc:
        error = str(exc)
    finally:
        cpu_profile.disable()
        if not args.no_cprofile:
            cpu_profile.dump_stats(str(args.output.with_suffix(".prof")))
        payload = {
            "status": "completed" if result is not None else "timed_out",
            "error": error,
            "load_seconds": load_seconds,
            "input_sha256": hashlib.sha256(json.dumps(bundle, sort_keys=True).encode()).hexdigest(),
            "sync_id": context.sync_id,
            "source_hashes": context.source_hashes,
            "scope": bundle.get("benchmark_scope"),
            "profile": profiler.report(),
            "result": result,
        }
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "event": "profile_finished",
                    "status": payload["status"],
                    "profile": payload["profile"],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()

"""Opt-in, nested wall-clock accounting for offline trade benchmarks."""

import time
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from unittest.mock import patch

ACTIVE = ContextVar("trade_profiler", default=None)


class BenchmarkTimeout(TimeoutError):
    pass


class TradeProfiler:
    def __init__(self, max_seconds=180):
        self.started = time.perf_counter()
        self.deadline = self.started + max_seconds
        self.rows, self.stack = {}, []

    def checkpoint(self):
        if time.perf_counter() >= self.deadline:
            raise BenchmarkTimeout("Trade benchmark time budget exhausted")

    @contextmanager
    def measure(self, name):
        self.checkpoint()
        frame = [name, time.perf_counter(), 0.0]
        self.stack.append(frame)
        try:
            yield
        finally:
            elapsed = time.perf_counter() - frame[1]
            self.stack.pop()
            row = self.rows.setdefault(
                name, {"calls": 0, "inclusive_seconds": 0.0, "exclusive_seconds": 0.0}
            )
            row["calls"] += 1
            row["inclusive_seconds"] += elapsed
            row["exclusive_seconds"] += elapsed - frame[2]
            if self.stack:
                self.stack[-1][2] += elapsed

    def report(self):
        wall = time.perf_counter() - self.started
        return {
            "wall_seconds": wall,
            "accounting": "Nested inclusive times overlap; exclusive times do not.",
            "stages": {
                name: {
                    **row,
                    "inclusive_percent": 100 * row["inclusive_seconds"] / wall,
                    "exclusive_percent": 100 * row["exclusive_seconds"] / wall,
                }
                for name, row in sorted(self.rows.items())
            },
        }


@contextmanager
def span(name):
    profiler = ACTIVE.get()
    if profiler is None:
        yield
    else:
        with profiler.measure(name):
            yield


def _timed(function, name):
    @wraps(function)
    def wrapper(*args, **kwargs):
        with span(name):
            return function(*args, **kwargs)

    return wrapper


@contextmanager
def instrument(profiler):
    """Run only in a dedicated benchmark process; restore every patched function."""
    from contextlib import ExitStack

    from . import matchup_engine, streaming, trade_completions, trade_search, trades

    token = ACTIVE.set(profiler)
    original_packages = trades.trade_packages
    original_completion = trades.completion_options

    class TimedPackages(list):
        def sort(self, *args, **kwargs):
            with span("required_drop_search" if len(self) > 1 else "trade_only_scoring"):
                return super().sort(*args, **kwargs)

    def packages(*args, **kwargs):
        with span("required_drop_enumeration"):
            choices, team = original_packages(*args, **kwargs)
        return TimedPackages(choices), team

    def completion(*args, **kwargs):
        parameters = list(args)
        base, score = parameters[2], parameters[4]
        pickup = trade_completions.with_pickup
        paths = {}

        def marked_pickup(scenario, *a, **kw):
            result = pickup(scenario, *a, **kw)
            paths[id(result)] = (
                "fair_fa_baseline_drop_search" if scenario is base else "trade_fa_scoring"
            )
            return result

        def scored(scenario):
            with span(paths.get(id(scenario), "completion_base_scoring")):
                return score(scenario)

        parameters[4] = scored
        with span("fa_completion"), patch.object(trade_completions, "with_pickup", marked_pickup):
            return original_completion(*parameters, **kwargs)

    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(trades, "trade_packages", packages))
            stack.enter_context(patch.object(trades, "completion_options", completion))
            for module, name, label in (
                (matchup_engine, "get_optimal_daily_lineup", "lineup_assignment"),
                (streaming, "get_optimal_daily_lineup", "lineup_assignment"),
                (
                    matchup_engine.MatchupEngine,
                    "get_expected_weekly_distribution",
                    "weekly_projection",
                ),
                (matchup_engine.MatchupEngine, "_daily_projections", "daily_player_moments"),
                (trades, "streaming_comparison", "streaming_total"),
                (trade_search, "_shortlist", "shortlist"),
            ):
                stack.enter_context(
                    patch.object(module, name, _timed(getattr(module, name), label))
                )
            yield
    finally:
        ACTIVE.reset(token)

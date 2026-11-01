"""Exact memoization must preserve opponent adaptation and ownership timing."""

import copy
import pickle
import unittest
from unittest.mock import patch

import pandas as pd

from src.trade_projection_cache import TradeProjectionCache
from src.trades import _pair, evaluate_trade
from tests.test_trades import bundle, context


class TradeProjectionCacheTest(unittest.TestCase):
    def test_fantasy_position_override_does_not_change_nba_role_minutes(self):
        engine = context().engine
        engine.team_map = dict.fromkeys(engine.players, 1)
        engine.use_positional_depth_and_injury_boost = True
        engine.pos_dict = dict.fromkeys(engine.players, "PG")
        engine.rotation_pos_dict = dict(engine.pos_dict)
        engine.players[8].update_injury_status(
            "OUT", expected_return="2026-11-30", report_date="2026-10-30T12:00:00Z"
        )
        with engine.projection_session():
            before = engine.get_expected_weekly_distribution(
                [1, 2], "2026-11-02", "2026-11-08", as_of_date="2026-10-30"
            )
        engine.pos_dict[1] = "C"
        with engine.projection_session():
            after = engine.get_expected_weekly_distribution(
                [1, 2], "2026-11-02", "2026-11-08", as_of_date="2026-10-30"
            )
        self.assertEqual(before["mean"], after["mean"])
        first = TradeProjectionCache.engine_key(engine)
        engine.rotation_pos_dict[1] = "C"
        self.assertNotEqual(first, TradeProjectionCache.engine_key(engine))

    def test_cross_package_cache_is_exact_and_context_remains_unchanged(self):
        ctx, data = context(), bundle()
        before = pickle.dumps(ctx)
        cache, moments = TradeProjectionCache(), {}
        first = evaluate_trade(ctx, data, projection_cache=moments, matchup_cache=cache)
        self.assertEqual(first, evaluate_trade(ctx, data))
        changed = copy.deepcopy(data)
        changed["proposal"]["receive_yahoo_ids"] = [104]
        self.assertEqual(
            evaluate_trade(ctx, changed, projection_cache=moments, matchup_cache=cache),
            evaluate_trade(ctx, changed),
        )
        self.assertGreater(cache.stats()["pair_hits"], 0)
        self.assertEqual(cache.stats()["context_resets"], 0)
        self.assertEqual(pickle.dumps(ctx), before)

    def test_identical_second_package_needs_no_weekly_lineup_projection(self):
        ctx, data = context(), bundle()
        cache = TradeProjectionCache()
        first = evaluate_trade(ctx, data, matchup_cache=cache)
        method = type(ctx.engine).get_expected_weekly_distribution
        calls = []

        def record(engine, *args, **kwargs):
            calls.append(1)
            return method(engine, *args, **kwargs)

        with patch.object(type(ctx.engine), "get_expected_weekly_distribution", record):
            second = evaluate_trade(ctx, data, matchup_cache=cache)
        self.assertEqual(second, first)
        self.assertEqual(calls, [])

    def test_mutating_a_returned_report_cannot_poison_projection_cache(self):
        ctx, data = context(), bundle()
        cache = TradeProjectionCache()
        first = evaluate_trade(ctx, data, matchup_cache=cache)
        expected = copy.deepcopy(first)
        weekly = first["teams"]["0"]["weekly"][0]
        weekly["before"]["lineups"].clear()
        weekly["after"]["categories"]["PTS"]["production"] = -999
        self.assertEqual(evaluate_trade(ctx, data, matchup_cache=cache), expected)

    def test_original_model_mutation_invalidates_cache_instead_of_returning_old_scores(self):
        ctx, data = context(), bundle()
        cache, moments = TradeProjectionCache(), {}
        evaluate_trade(ctx, data, matchup_cache=cache, projection_cache=moments)
        ctx.engine.players[1].alphas["PTS"] *= 5
        actual = evaluate_trade(ctx, data, matchup_cache=cache, projection_cache=moments)
        self.assertEqual(actual, evaluate_trade(ctx, data))
        self.assertEqual(cache.stats()["context_resets"], 1)

    def test_bundle_eligibility_override_has_a_separate_cache_namespace(self):
        ctx, data = context(), bundle()
        cache, moments = TradeProjectionCache(), {}
        evaluate_trade(ctx, data, matchup_cache=cache, projection_cache=moments)
        previous = cache.stats()["pair_misses"]
        changed = copy.deepcopy(data)
        changed["eligible_positions"]["101"] = ["C"]
        self.assertEqual(
            evaluate_trade(ctx, changed, matchup_cache=cache, projection_cache=moments),
            evaluate_trade(ctx, changed),
        )
        self.assertGreater(cache.stats()["pair_misses"], previous)

    def test_injury_spillover_and_sensitivity_are_not_mixed(self):
        ctx, data = context(), bundle()
        ctx.engine.use_positional_depth_and_injury_boost = True
        ctx.engine.team_map = {pid: 1 for pid in ctx.engine.players}
        ctx.engine.players[2].injury_status = "OUT"
        cache = TradeProjectionCache()
        first = evaluate_trade(ctx, data, matchup_cache=cache)
        self.assertEqual(first, evaluate_trade(ctx, data))
        second = copy.deepcopy(data)
        second["proposal"]["receive_yahoo_ids"] = [104]
        self.assertEqual(
            evaluate_trade(ctx, second, matchup_cache=cache), evaluate_trade(ctx, second)
        )
        normal = cache.engine_key(ctx.engine)
        sensitivity = copy.deepcopy(ctx.engine)
        sensitivity.use_positional_depth_and_injury_boost = False
        self.assertNotEqual(normal, cache.engine_key(sensitivity))

    def test_other_roster_changes_recompute_opponent_adaptation_but_reuse_exact_raw_distribution(
        self,
    ):
        ctx = context()
        cache = TradeProjectionCache()
        cache.bind(ctx)
        args = ("2026-11-02", "2026-11-08", pd.Timestamp("2026-10-30"))
        _pair(ctx.engine, [1, 2], [5, 6], *args, cache=cache)
        old_misses = cache.stats()["pair_misses"]
        changed = _pair(ctx.engine, [3, 4], [5, 6], *args, cache=cache)
        exact = _pair(copy.deepcopy(ctx.engine), [3, 4], [5, 6], *args)
        self.assertEqual(changed, exact)
        self.assertGreater(cache.stats()["pair_misses"], old_misses)
        self.assertGreater(cache.stats()["distribution_hits"], 0)

    def test_starts_ends_and_il_are_part_of_the_exact_projection_key(self):
        ctx = context()
        cache = TradeProjectionCache()
        cache.bind(ctx)
        args = ("2026-11-02", "2026-11-08", pd.Timestamp("2026-10-30"))
        original = _pair(ctx.engine, [1, 2], [3, 4], *args, cache=cache)
        for starts, ends, stashed in (
            ({1: pd.Timestamp("2026-11-04")}, {}, set()),
            ({}, {1: pd.Timestamp("2026-11-04")}, set()),
            ({}, {}, {1}),
        ):
            ctx.engine.yahoo_already_stashed_ids = stashed
            actual = _pair(ctx.engine, [1, 2], [3, 4], *args, starts, ends, cache=cache)
            exact = _pair(copy.deepcopy(ctx.engine), [1, 2], [3, 4], *args, starts, ends)
            self.assertEqual(actual, exact)
            self.assertNotEqual(actual[0]["mean"], original[0]["mean"])

    def test_unrelated_team_history_does_not_invalidate_an_unchanged_pair(self):
        ctx = context()
        cache = TradeProjectionCache()
        cache.bind(ctx)
        args = ("2026-11-02", "2026-11-08", pd.Timestamp("2026-10-30"))
        original = _pair(ctx.engine, [1, 2], [3, 4], *args, cache=cache)
        ctx.engine.yahoo_already_stashed_ids = {8}
        second = _pair(
            ctx.engine, [1, 2], [3, 4], *args, {8: pd.Timestamp("2026-11-06")}, cache=cache
        )
        self.assertEqual(second, original)
        self.assertEqual(cache.stats()["pair_hits"], 1)

    def test_lru_capacities_are_enforced(self):
        ctx = context()
        cache = TradeProjectionCache(max_pairs=1, max_distributions=2)
        cache.bind(ctx)
        args = ("2026-11-02", "2026-11-08", pd.Timestamp("2026-10-30"))
        for home in ([1, 2], [3, 4], [7, 8]):
            _pair(ctx.engine, home, [5, 6], *args, cache=cache)
        self.assertLessEqual(cache.stats()["pair_entries"], 1)
        self.assertLessEqual(cache.stats()["distribution_entries"], 2)
        self.assertGreater(cache.stats()["pair_evictions"], 0)
        self.assertGreater(cache.stats()["distribution_evictions"], 0)

    def test_combined_payload_budget_evicts_least_recent_across_both_caches(self):
        value = {"mean": [1.25] * 50}
        size = len(pickle.dumps(value, protocol=5))
        cache = TradeProjectionCache(max_pairs=10, max_distributions=10, max_payload_bytes=2 * size)
        cache.put_pair("pair", value)
        cache.put_distribution("old-roster", value)
        self.assertEqual(cache.stats()["payload_bytes"], 2 * size)
        self.assertEqual(cache.get_pair("pair"), value)
        cache.put_distribution("new-roster", value)
        self.assertIsNone(cache.get_distribution("old-roster"))
        self.assertEqual(cache.get_pair("pair"), value)
        self.assertEqual(cache.get_distribution("new-roster"), value)
        self.assertEqual(cache.stats()["payload_evictions"], 1)
        self.assertEqual(cache.stats()["pair_payload_bytes"], size)
        self.assertEqual(cache.stats()["distribution_payload_bytes"], size)
        self.assertLessEqual(cache.stats()["peak_payload_bytes"], cache.max_payload_bytes)

    def test_payload_replacement_reset_and_oversized_skip_keep_byte_accounting_exact(self):
        ctx = context()
        cache = TradeProjectionCache(max_payload_bytes=300)
        cache.bind(ctx)
        cache.put_pair("key", {"small": 1})
        first = cache.stats()["payload_bytes"]
        cache.put_pair("key", {"larger": [1, 2, 3]})
        self.assertNotEqual(cache.stats()["payload_bytes"], first)
        cache.put_pair("key", {"huge": list(range(1000))})
        self.assertIsNone(cache.get_pair("key"))
        self.assertEqual(cache.stats()["payload_bytes"], 0)
        self.assertEqual(cache.stats()["oversized_payload_skips"], 1)
        cache.put_distribution("key", {"small": 2})
        self.assertGreater(cache.stats()["payload_bytes"], 0)
        ctx.sync_id = "new-context"
        cache.bind(ctx)
        self.assertEqual(cache.stats()["payload_bytes"], 0)
        self.assertEqual(cache.stats()["distribution_entries"], 0)


if __name__ == "__main__":
    unittest.main()

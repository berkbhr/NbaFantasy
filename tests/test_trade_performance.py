"""Exact schedule reuse and truthful nested benchmark accounting."""

import unittest
from unittest.mock import patch

import pandas as pd

from src.trade_packages import RosterScenario, with_pickup
from src.trade_profiling import BenchmarkTimeout, TradeProfiler
from tests.test_trades import context


class TradePerformanceTest(unittest.TestCase):
    def test_fast_branch_copy_preserves_other_teams_history_and_nested_metadata(self):
        original = RosterScenario(
            {"0": [1, 2], "1": [3, 4]},
            set(),
            adds={"1": {"note": {"values": [1]}}},
            transactions=[
                {"team": "1", "date": "2026-11-01", "add_id": 4, "drop_id": None, "meta": [1]}
            ],
        )
        branch = with_pickup(original, "0", 5, pd.Timestamp("2026-11-02"), drop=2)
        branch.rosters["1"].append(6)
        branch.adds["1"]["note"]["values"].append(2)
        branch.transactions[0]["meta"].append(2)
        self.assertEqual(original.rosters, {"0": [1, 2], "1": [3, 4]})
        self.assertEqual(original.adds["1"]["note"]["values"], [1])
        self.assertEqual(original.transactions[0]["meta"], [1])
        self.assertEqual(original.ends, {})
        self.assertEqual(branch.ends[2], pd.Timestamp("2026-11-01"))

    def test_schedule_filter_runs_once_per_nba_team_and_respects_completed_games(self):
        ctx = context()
        engine = ctx.engine
        with patch.object(
            engine, "_get_player_schedule", wraps=engine._get_player_schedule
        ) as lookup:
            before = engine.get_expected_weekly_distribution([1, 2], "2026-11-02", "2026-11-08")
            self.assertEqual(lookup.call_count, 2)
        engine.completed_game_ids.add("1-2026-11-02")
        after = engine.get_expected_weekly_distribution([1, 2], "2026-11-02", "2026-11-08")
        self.assertIn(1, before["meta"]["lineups"]["2026-11-02"])
        self.assertNotIn(1, after["meta"]["lineups"]["2026-11-02"])
        self.assertIn(1, after["meta"]["lineups"]["2026-11-04"])
        engine.completed_game_ids.clear()
        restored = engine.get_expected_weekly_distribution([1, 2], "2026-11-02", "2026-11-08")
        self.assertEqual(before, restored)

    def test_nested_wall_accounting_separates_inclusive_and_exclusive_time(self):
        with patch("src.trade_profiling.time.perf_counter") as clock:
            clock.return_value = 0
            profile = TradeProfiler(20)
            clock.return_value = 1
            with profile.measure("streaming"):
                clock.return_value = 2
                with profile.measure("lineup"):
                    clock.return_value = 5
                clock.return_value = 7
            self.assertEqual(profile.rows["streaming"]["inclusive_seconds"], 6)
            self.assertEqual(profile.rows["streaming"]["exclusive_seconds"], 3)
            self.assertEqual(profile.rows["lineup"]["exclusive_seconds"], 3)
            clock.return_value = 21
            with self.assertRaises(BenchmarkTimeout):
                with profile.measure("expired"):
                    self.fail("Expired benchmark continued")
            self.assertEqual(profile.stack, [])


if __name__ == "__main__":
    unittest.main()

import unittest

import pandas as pd

from src.matchup_engine import MatchupEngine, get_optimal_daily_lineup, map_position_to_slots
from tests.helpers import player


class TestDecisions(unittest.TestCase):
    def test_empty_slot_is_better_than_turnovers_only(self):
        self.assertEqual(
            get_optimal_daily_lineup([{"ID": 1, "POS": "UTIL", "PROJ": {"TOV": 5}}], {"TOV": 1}), []
        )

    def test_precise_position_does_not_gain_other_positions(self):
        self.assertNotIn("SG", map_position_to_slots("PG"))
        self.assertNotIn("C", map_position_to_slots("UTIL"))
        self.assertIn("PF", map_position_to_slots("SF,PF"))

    def test_no_automatic_free_agent_ownership_for_either_team(self):
        players = {i: player(i) for i in (1, 2, 3)}
        players[1].update_injury_status("OUT")
        players[2].update_injury_status("OUT")
        engine = MatchupEngine(
            players, pd.DataFrame(), pd.DataFrame(), free_agent_pool=[3], team_map={}
        )
        for roster in ([1], [2]):
            result = engine.get_expected_weekly_distribution(roster)
            self.assertEqual(result["meta"]["streamer_ids"], [])
            self.assertEqual(result["mean"]["PTS"], 0)

    def test_all_protected_means_no_drop_recommendation(self):
        players = {i: player(i) for i in range(1, 16)}
        engine = MatchupEngine(players, pd.DataFrame(), pd.DataFrame(), team_map={})
        self.assertEqual(
            engine.recommend_add_drop_moves(
                list(range(1, 14)), [14], [15], protected_ids=set(range(1, 14))
            ),
            [],
        )

    def test_used_add_budget_stops_recommendations(self):
        engine = MatchupEngine({1: player()}, pd.DataFrame(), pd.DataFrame(), team_map={})
        self.assertEqual(engine.recommend_add_drop_moves([1], [], [], adds_used=3), [])

    def test_opportunity_sensitivity_uses_same_move_and_restores_rotation(self):
        players = {i: player(i) for i in range(1, 6)}
        players[3].base_expected_minutes = players[3].expected_minutes = 12
        players[4].base_expected_minutes = players[4].expected_minutes = 20
        players[5].update_injury_status("OUT")
        engine = MatchupEngine(
            players,
            pd.DataFrame(),
            pd.DataFrame(),
            team_map={1: 10, 2: 20, 3: 30, 4: 40, 5: 30},
            use_positional_depth_and_injury_boost=True,
        )
        ordinary = engine.recommend_add_drop_moves([1], [2], [3, 4], top_k=2)
        cautious = engine.recommend_add_drop_moves(
            [1], [2], [3, 4], top_k=2, opportunity_sensitivity=True
        )
        self.assertTrue(cautious)
        self.assertTrue(engine.use_positional_depth_and_injury_boost)
        ordinary_by_id = {r["add_id"]: r for r in ordinary}
        for row in cautious:
            self.assertAlmostEqual(
                row["delta_objective_value"], ordinary_by_id[row["add_id"]]["delta_objective_value"]
            )
            self.assertLessEqual(row["robust_delta_objective_value"], row["delta_objective_value"])
            self.assertGreater(row["delta_without_spillover"], 0)
        self.assertEqual(
            [r["robust_delta_objective_value"] for r in cautious],
            sorted((r["robust_delta_objective_value"] for r in cautious), reverse=True),
        )

    def test_waiver_player_cannot_play_before_clear_date(self):
        players = {i: player(i) for i in (1, 2, 3)}
        schedule = pd.DataFrame(
            {
                "TEAM_ID": [10, 10, 10],
                "GAME_DATE": pd.date_range("2026-10-20", periods=3),
                "GAME_ID": ["1", "2", "3"],
            }
        )
        engine = MatchupEngine(players, schedule, pd.DataFrame(), team_map={1: 10, 2: 10, 3: 10})
        full = engine.get_expected_weekly_distribution([3], "2026-10-20", "2026-10-22")
        late = engine.get_expected_weekly_distribution(
            [3], "2026-10-20", "2026-10-22", player_start_dates={3: "2026-10-22"}
        )
        self.assertAlmostEqual(late["mean"]["PTS"] * 3, full["mean"]["PTS"])
        recs = engine.recommend_add_drop_moves(
            [1],
            [2],
            [3],
            start_date="2026-10-20",
            end_date="2026-10-22",
            waivers_dict={3: {"date": "2026-10-23"}},
        )
        self.assertEqual(recs, [])

    def test_completed_games_are_not_projected_twice(self):
        schedule = pd.DataFrame(
            {
                "TEAM_ID": [10, 10],
                "GAME_DATE": pd.date_range("2026-10-20", periods=2),
                "GAME_ID": ["1", "2"],
            }
        )
        engine = MatchupEngine({1: player()}, schedule, pd.DataFrame(), team_map={1: 10})
        engine.completed_game_ids = {"1"}
        result = engine.get_expected_weekly_distribution([1], "2026-10-20", "2026-10-21")
        self.assertEqual(result["meta"]["lineups"]["2026-10-20"], [])
        self.assertEqual(result["meta"]["lineups"]["2026-10-21"], [1])

    def test_confirmed_yahoo_stash_is_binding_even_when_player_returns(self):
        bp = player()
        bp.update_injury_status("PROBABLE")
        engine = MatchupEngine(
            {1: bp}, pd.DataFrame(), pd.DataFrame(), team_map={}, yahoo_il_eligible_ids=set()
        )
        engine.yahoo_already_stashed_ids = {1}
        result = engine.get_expected_weekly_distribution([1])
        self.assertEqual(result["mean"]["PTS"], 0)
        self.assertEqual(result["meta"]["il_stashed_ids"], [1])

    def test_zero_remaining_fraction_preserves_realized_stats(self):
        engine = MatchupEngine({1: player()}, pd.DataFrame(), pd.DataFrame(), team_map={})
        future = engine.get_expected_weekly_distribution([1])
        result = engine.combine_live_and_remaining_dist({"PTS": 123}, future, 0)
        self.assertEqual(result["mean"]["PTS"], 123)
        self.assertTrue(all(v == 0 for v in result["var"].values()))


if __name__ == "__main__":
    unittest.main()

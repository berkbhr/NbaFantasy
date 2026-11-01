"""Verification tests for consensus decisions (Group 1 & A1-A6)."""

import unittest
from unittest.mock import patch

import pandas as pd

from src.bayesian_model import COUNT_STATS, DECAY_LAMBDA_BY_STAT, PERCENTAGE_STATS, BayesianPlayer
from src.matchup_engine import ALL_CATEGORIES, MatchupEngine, get_optimal_daily_lineup
from src.model_policy import ModelPolicy, load_model_policy, update_role
from src.priors import _next_season, _previous_season, load_prior_season
from src.probability import CategoryProbabilities, category_points, decision_value, matchup_outcome


def _make_player(pid=1, minutes=30.0):
    bp = BayesianPlayer(pid, f"Player {pid}")
    bp.initialize_priors(
        {
            "MIN": 2100.0,
            "GP": 70.0,
            "PTS": 1400.0,
            "REB": 600.0,
            "AST": 250.0,
            "STL": 70.0,
            "BLK": 50.0,
            "TOV": 150.0,
            "FG3M": 100.0,
            "FGM": 550.0,
            "FGA": 1100.0,
            "FTM": 200.0,
            "FTA": 250.0,
        }
    )
    bp.expected_minutes = bp.base_expected_minutes = float(minutes)
    return bp


class ConsensusContractTests(unittest.TestCase):
    def test_a1_zero_role_covariance_matches_baseline_exactly(self):
        bp = _make_player(1, 30.0)
        schedule = pd.DataFrame(
            {
                "TEAM_ID": [10, 10, 10],
                "GAME_DATE": pd.date_range("2026-10-20", periods=3),
                "GAME_ID": ["g1", "g2", "g3"],
            }
        )
        engine = MatchupEngine(
            {1: bp}, schedule, pd.DataFrame(), team_map={1: 10}, availability_correlation=0.0
        )
        base = engine.get_expected_weekly_distribution([1], "2026-10-20", "2026-10-22")
        zero_corr = engine.get_expected_weekly_distribution(
            [1], "2026-10-20", "2026-10-22", role_covariance_correlation=0.0
        )
        self.assertEqual(base["mean"], zero_corr["mean"])
        self.assertEqual(base["var"], zero_corr["var"])

    def test_a1_synthetic_weekly_role_covariance_formula_and_no_marginal_double_count(self):
        bp = _make_player(1, 30.0)
        bp.avail_alpha, bp.avail_beta, bp.availability_rate = 100.0, 0.0, 1.0
        schedule = pd.DataFrame(
            {
                "TEAM_ID": [10, 10, 10, 10],
                "GAME_DATE": pd.date_range("2026-10-20", periods=4, freq="2D"),
                "GAME_ID": ["g1", "g2", "g3", "g4"],
            }
        )
        engine = MatchupEngine(
            {1: bp}, schedule, pd.DataFrame(), team_map={1: 10}, availability_correlation=0.0
        )
        single = engine.get_expected_weekly_distribution(
            [1],
            "2026-10-20",
            "2026-10-20",
            use_live_injuries=False,
            role_covariance_correlation=0.5,
        )
        single_base = engine.get_expected_weekly_distribution(
            [1],
            "2026-10-20",
            "2026-10-20",
            use_live_injuries=False,
            role_covariance_correlation=0.0,
        )
        # Single-game marginal variance must not be inflated by cross-game role covariance
        for cat in ALL_CATEGORIES:
            self.assertAlmostEqual(single["var"][cat], single_base["var"][cat], places=10)

        g = 4
        rho_role = 0.5
        multi_base = engine.get_expected_weekly_distribution(
            [1],
            "2026-10-20",
            "2026-10-26",
            use_live_injuries=False,
            role_covariance_correlation=0.0,
        )
        multi_corr = engine.get_expected_weekly_distribution(
            [1],
            "2026-10-20",
            "2026-10-26",
            use_live_injuries=False,
            role_covariance_correlation=rho_role,
        )
        pred = bp.predict_next_game(current_date=pd.Timestamp("2026-10-20"))
        for stat in COUNT_STATS:
            v = pred[stat]["variance"]
            c_shared = pred[stat]["shared_covariance"]
            c_role = rho_role * pred[stat]["role_variance"]
            self.assertAlmostEqual(
                multi_base["var"][stat], g * v + g * (g - 1) * c_shared, places=8
            )
            self.assertAlmostEqual(
                multi_corr["var"][stat], g * v + g * (g - 1) * (c_shared + c_role), places=8
            )

        with self.assertRaises(ValueError):
            engine.get_expected_weekly_distribution(
                [1], "2026-10-20", "2026-10-22", role_covariance_correlation=1.5
            )

    def test_a2_availability_prior_precedence_and_in_season_ceiling(self):
        # 1. Rookie availability precedence: ROOKIE_AVAIL_GP > AVAIL_GP > GP
        bp_rookie = BayesianPlayer(10, "Rookie")
        bp_rookie.initialize_priors(
            {"MIN": 300.0, "GP": 10.0, "AVAIL_GP": 20.0, "ROOKIE_AVAIL_GP": 68.0}
        )
        expected_rookie_alpha = 20.0 + 0.5 * 68.0
        expected_rookie_beta = 5.0 + 0.5 * (82.0 - 68.0)
        self.assertAlmostEqual(bp_rookie.avail_alpha, expected_rookie_alpha)
        self.assertAlmostEqual(bp_rookie.avail_beta, expected_rookie_beta)

        # 2. Two-season AVAIL_GP precedence over effective GP
        bp_vet = BayesianPlayer(11, "Veteran")
        bp_vet.initialize_priors({"MIN": 1800.0, "GP": 60.0, "AVAIL_GP": 45.0})
        self.assertAlmostEqual(bp_vet.avail_alpha, 20.0 + 0.5 * 45.0)
        self.assertAlmostEqual(bp_vet.avail_beta, 5.0 + 0.5 * (82.0 - 45.0))

        # 3. 82 GP starts at 61/66 (~92.42%), and in-season play can exceed 92.42% up to 98%
        bp_iron = BayesianPlayer(12, "Ironman")
        bp_iron.initialize_priors({"MIN": 2600.0, "GP": 82.0})
        self.assertAlmostEqual(bp_iron.availability_rate, 61.0 / 66.0)
        for _ in range(80):
            bp_iron.record_team_game_availability(True)
        self.assertGreater(bp_iron.availability_rate, 0.95)
        self.assertLessEqual(bp_iron.availability_rate, 0.98)

    def test_a2_two_season_prior_preserves_gp1_in_avail_gp_and_eff_gp_in_gp(self):
        p1 = {col: 100.0 for col in ALL_CATEGORIES}
        p1.update({"MIN": 1200.0, "GP": 40.0, "ROLE_MPG": 30.0})
        p0 = {col: 200.0 for col in ALL_CATEGORIES}
        p0.update({"MIN": 2100.0, "GP": 70.0, "ROLE_MPG": 30.0})

        def fake_totals(season):
            if season == "2025_26":
                return {1: p1}, {1: 30.0}
            if season == "2024_25":
                return {1: p0}, {1: 30.0}
            return {}, {}

        with (
            patch("src.priors._load_single_season_totals", side_effect=fake_totals),
            patch("src.priors.os.path.exists", return_value=False),
        ):
            blended = load_prior_season("2025_26", blend_prev_season=True)
        entry = blended[1]
        self.assertEqual(entry["AVAIL_GP"], 40.0)
        self.assertAlmostEqual(entry["GP"], max(40.0, 0.60 * 40.0 + 0.40 * 70.0))

    def test_a3_model_policy_adaptive_anchor_and_role_update(self):
        policy = load_model_policy()
        self.assertEqual(policy.role, "adaptive_anchor")
        bp_adapt = _make_player(1, 30.0)
        bp_recent = _make_player(2, 30.0)
        history = [
            (f"g{i}", 24.0, pd.Timestamp("2026-10-20") + pd.Timedelta(days=i), 10)
            for i in range(10)
        ]
        update_role(bp_adapt, history, 30.0, ModelPolicy(role="adaptive_anchor"))
        update_role(bp_recent, history, 30.0, ModelPolicy(role="recent_blend"))
        # With 10 games (< 6.5 min diff so k=3), adaptive_anchor uses n=10/(10+3), recent_blend uses n=5/(5+3)
        self.assertAlmostEqual(bp_adapt.role_observation_weight, 10.0 / 13.0)
        self.assertAlmostEqual(bp_recent.role_observation_weight, 5.0 / 8.0)

    def test_a5_opportunity_sensitivity_evaluates_both_baselines_and_restores_state(self):
        players = {i: _make_player(i, 24.0) for i in range(1, 6)}
        players[3].base_expected_minutes = players[3].expected_minutes = 12.0
        players[4].base_expected_minutes = players[4].expected_minutes = 22.0
        players[5].update_injury_status("OUT")
        engine = MatchupEngine(
            players,
            pd.DataFrame(),
            pd.DataFrame(),
            team_map={1: 10, 2: 20, 3: 30, 4: 40, 5: 30},
            use_positional_depth_and_injury_boost=True,
        )
        cautious = engine.recommend_add_drop_moves(
            [1], [2], [3, 4], top_k=2, opportunity_sensitivity=True
        )
        self.assertTrue(cautious)
        self.assertTrue(engine.use_positional_depth_and_injury_boost)
        for row in cautious:
            self.assertEqual(
                row["robust_delta_objective_value"],
                min(row["delta_objective_value"], row["delta_without_spillover"]),
            )
            self.assertEqual(row["ranking_basis"], "minimum_gain_with_and_without_spillover")

    def test_a6_fga_fta_attempt_decay_key_separation_is_behavior_preserving_by_default(self):
        self.assertEqual(DECAY_LAMBDA_BY_STAT["FGA"], DECAY_LAMBDA_BY_STAT["FG"])
        self.assertEqual(DECAY_LAMBDA_BY_STAT["FTA"], DECAY_LAMBDA_BY_STAT["FT"])
        bp = _make_player(1, 30.0)
        bp.update_stats(
            pd.Timestamp("2026-10-20"),
            32.0,
            {"PTS": 20, "FGM": 7, "FGA": 15, "FTM": 4, "FTA": 5},
            game_id="g1",
        )
        baseline_pred = bp.predict_next_game(current_date=pd.Timestamp("2026-10-30"))

        # Verify that overriding FGA/FTA volume decay keys affects attempt precision without changing FG%/FT% accuracy beta
        with patch.dict(DECAY_LAMBDA_BY_STAT, {"FGA": 0.025, "FTA": 0.020}):
            bp_cand = _make_player(1, 30.0)
            bp_cand.update_stats(
                pd.Timestamp("2026-10-20"),
                32.0,
                {"PTS": 20, "FGM": 7, "FGA": 15, "FTM": 4, "FTA": 5},
                game_id="g1",
            )
            cand_pred = bp_cand.predict_next_game(current_date=pd.Timestamp("2026-10-30"))
            self.assertEqual(cand_pred["FG"]["rate"], baseline_pred["FG"]["rate"])
            self.assertEqual(cand_pred["FG"]["rate_variance"], baseline_pred["FG"]["rate_variance"])
            self.assertGreater(cand_pred["FG"]["attempts_var"], baseline_pred["FG"]["attempts_var"])
            self.assertGreater(cand_pred["FT"]["attempts_var"], baseline_pred["FT"]["attempts_var"])

    def test_a6_season_helpers_preserve_2025_26_and_generalize_future_seasons(self):
        self.assertEqual(_previous_season("2025_26"), "2024_25")
        self.assertEqual(_previous_season("2026_27"), "2025_26")
        self.assertEqual(_previous_season("2027_28"), "2026_27")
        self.assertEqual(_next_season("2025_26"), "2026_27")
        self.assertEqual(_next_season("2026_27"), "2027_28")

    def test_g1_core_probability_and_lineup_invariants(self):
        # Empty slot beats pure turnover player
        self.assertEqual(
            get_optimal_daily_lineup([{"ID": 1, "POS": "UTIL", "PROJ": {"TOV": 4}}], {"TOV": 1.0}),
            [],
        )
        # 4-3-2 is a weekly matchup win and 5.0 expected category points
        probs = CategoryProbabilities(
            {i: float(i < 4) for i in range(9)},
            {i: float(i >= 7) for i in range(9)},
        )
        self.assertAlmostEqual(category_points(probs), 5.0)
        self.assertAlmostEqual(decision_value(probs, "category_points"), 5.0)
        outcome = matchup_outcome(probs)
        self.assertEqual((outcome.win, outcome.loss, outcome.draw), (1.0, 0.0, 0.0))
        for s in PERCENTAGE_STATS:
            self.assertIn(s, ("FG", "FT"))


if __name__ == "__main__":
    unittest.main()

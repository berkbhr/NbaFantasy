import unittest

import numpy as np
import pandas as pd

from src.bayesian_model import BayesianPlayer
from src.matchup_engine import MatchupEngine
from src.rotation import adjust_rotations


def player(pid=1, minutes=30):
    bp = BayesianPlayer(pid, str(pid))
    bp.initialize_priors(
        {
            "MIN": 2100,
            "GP": 70,
            "PTS": 1400,
            "REB": 600,
            "AST": 250,
            "STL": 70,
            "BLK": 50,
            "TOV": 150,
            "FG3M": 100,
            "FGM": 550,
            "FGA": 1100,
            "FTM": 200,
            "FTA": 250,
        }
    )
    bp.expected_minutes = bp.base_expected_minutes = minutes
    return bp


class TestModel(unittest.TestCase):
    def test_gamma_poisson_with_random_minutes_matches_simulation(self):
        bp = player()
        bp.minutes_var = 9
        rng = np.random.default_rng(42)
        rate = rng.gamma(bp.alphas["STL"], 1 / bp.betas["STL"], size=300000)
        mins = rng.normal(30, 3, size=len(rate))
        samples = rng.poisson(rate * mins)
        prediction = bp.predict_next_game()["STL"]
        self.assertAlmostEqual(samples.mean(), prediction["mean"], delta=0.015)
        self.assertAlmostEqual(samples.var(), prediction["variance"], delta=0.035)

    def test_random_attempt_beta_mixture_matches_simulation(self):
        bp = player()
        prediction = bp.predict_next_game()["FG"]
        mean, variance = prediction["attempts"], prediction["attempts_var"]
        rng = np.random.default_rng(11)
        shape = mean**2 / (variance - mean)
        attempts = rng.negative_binomial(shape, mean / variance, size=300000)
        accuracy = rng.beta(bp.alphas["FG"], bp.betas["FG"], size=len(attempts))
        makes = rng.binomial(attempts, accuracy)
        self.assertAlmostEqual(makes.mean(), prediction["mean"], delta=0.04)
        self.assertAlmostEqual(makes.var(), prediction["variance"], delta=0.22)

    def test_fixed_attempts_have_no_attempt_variance(self):
        p = player().predict_next_game(projected_attempts={"FG": 10})["FG"]
        self.assertEqual(p["attempts_var"], 0)
        self.assertAlmostEqual(p["variance"], p["cond_variance"])

    def test_updates_are_idempotent_and_chronological(self):
        bp = player()
        self.assertTrue(bp.update_stats(pd.Timestamp("2026-10-20"), 30, {"PTS": 15}, game_id="1"))
        alpha = bp.alphas["PTS"]
        self.assertFalse(bp.update_stats(pd.Timestamp("2026-10-20"), 30, {"PTS": 15}, game_id="1"))
        self.assertEqual(alpha, bp.alphas["PTS"])
        with self.assertRaises(ValueError):
            bp.update_stats(pd.Timestamp("2026-10-19"), 30, {}, game_id="0")

    def test_impossible_shooting_is_rejected_without_mutation(self):
        bp = player()
        before = bp.alphas.copy()
        with self.assertRaises(ValueError):
            bp.update_stats(pd.Timestamp("2026-10-20"), 30, {"FGM": 5, "FGA": 4})
        self.assertEqual(before, bp.alphas)

    def test_return_date_changes_game_specific_availability(self):
        bp = player()
        bp.update_injury_status("OUT", expected_return="2026-10-25")
        self.assertEqual(bp.get_effective_game_availability(game_date="2026-10-24"), 0)
        self.assertGreater(bp.get_effective_game_availability(game_date="2026-10-25"), 0)
        self.assertGreater(
            bp.get_effective_game_availability(game_date="2026-11-01"),
            bp.get_effective_game_availability(game_date="2026-10-25"),
        )

    def test_dnp_is_probability_not_default_week_exclusion(self):
        bp = player()
        bp.consecutive_dnps = 2
        engine = MatchupEngine({1: bp}, pd.DataFrame(), pd.DataFrame(), team_map={})
        result = engine.get_expected_weekly_distribution([1])
        self.assertGreater(result["mean"]["PTS"], 0)
        self.assertEqual(result["meta"]["dnp_excluded_ids"], [])

    def test_expired_return_estimate_cannot_override_new_out_report(self):
        bp = player()
        bp.update_injury_status("OUT", expected_return="2026-10-23", report_date="2026-10-27")
        self.assertEqual(bp.get_effective_game_availability(game_date="2026-10-28"), 0)

    def test_same_day_out_report_overrides_tentative_return_date(self):
        bp = player()
        bp.update_injury_status(
            "OUT", expected_return="2026-10-27", report_date="2026-10-27T12:00Z"
        )
        self.assertEqual(bp.get_effective_game_availability(game_date="2026-10-27"), 0)

    def test_rotation_recovery_and_repeated_calls_are_reversible(self):
        players = {1: player(1, 37), 2: player(2, 25)}
        players[2].update_injury_status("OUT")
        adjust_rotations(players, {1: 10, 2: 10}, {1: "C", 2: "C"})
        first = players[1].expected_minutes
        adjust_rotations(players, {1: 10, 2: 10}, {1: "C", 2: "C"})
        self.assertEqual(players[1].expected_minutes, first)
        players[2].update_injury_status("HEALTHY")
        adjust_rotations(players, {1: 10, 2: 10}, {1: "C", 2: "C"})
        self.assertEqual(players[1].expected_minutes, 37)

    def test_rotation_obeys_expected_240_minute_budget(self):
        players = {i: player(i, 32) for i in range(12)}
        adjust_rotations(players, dict.fromkeys(players, 10), dict.fromkeys(players, "G-F-C"))
        total = sum(
            p.expected_minutes * p.get_effective_game_availability() for p in players.values()
        )
        self.assertLessEqual(total, 240.000001)

    def test_low_observed_role_limits_total_boost_across_multiple_injuries(self):
        players = {1: player(1, 12.5), 2: player(2, 30), 3: player(3, 30), 4: player(4, 30)}
        players[1].current_season_gp = 3
        players[1].current_season_mpg = 8.0
        for pid in (2, 3, 4):
            players[pid].update_injury_status("OUT")
        adjust_rotations(players, dict.fromkeys(players, 10), dict.fromkeys(players, "C"))
        self.assertGreater(players[1].expected_minutes, 14.5)  # No automatic adoption.
        for _ in range(2):
            adjust_rotations(
                players,
                dict.fromkeys(players, 10),
                dict.fromkeys(players, "C"),
                low_role_boost_cap=2,
            )
            self.assertLessEqual(players[1].expected_minutes, 14.5)
        players[1].current_season_mpg = 20
        adjust_rotations(
            players, dict.fromkeys(players, 10), dict.fromkeys(players, "C"), low_role_boost_cap=2
        )
        self.assertGreater(players[1].expected_minutes, 14.5)

    def test_shared_rate_uncertainty_survives_week_aggregation(self):
        bp = player()
        bp.availability_rate = 1
        dates = pd.date_range("2026-10-20", periods=3)
        schedule = pd.DataFrame(
            {"TEAM_ID": [10] * 3, "GAME_DATE": dates, "GAME_ID": ["1", "2", "3"]}
        )
        engine = MatchupEngine({1: bp}, schedule, pd.DataFrame(), team_map={1: 10})
        daily = bp.predict_next_game()["PTS"]
        weekly = engine.get_expected_weekly_distribution(
            [1], dates[0], dates[-1], use_live_injuries=False
        )
        self.assertAlmostEqual(
            weekly["var"]["PTS"], 3 * daily["variance"] + 6 * daily["shared_covariance"]
        )


if __name__ == "__main__":
    unittest.main()

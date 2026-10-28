import itertools
import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd

from src.compare_versions import compare
from src.matchup_engine import MatchupEngine
from src.mathematical_audit import fixed_attempt_audit, sample_team


class TestComparisonProtocol(unittest.TestCase):
    def test_paired_metrics_use_correct_improvement_direction(self):
        old = pd.DataFrame(
            {
                "date": ["2025-10-20", "2025-10-21"],
                "player_id": [1, 1],
                "game_id": ["1", "2"],
                "stat": ["PTS", "PTS"],
                "actual": [10.0, 20.0],
                "mean": [8.0, 16.0],
                "variance": [4.0, 4.0],
                "games_seen": [0, 1],
            }
        )
        new = old.copy()
        new["mean"] = [9.0, 18.0]
        result = compare(old, new, "2025_26", "single_prior", {1: 30})
        row = next(r for r in result if r["population"] == "all")
        self.assertEqual(row["old_MAE"], 3.0)
        self.assertEqual(row["new_MAE"], 1.5)
        self.assertEqual(row["MAE_improvement_percent"], 50.0)
        self.assertEqual(row["weekly_bootstrap_low"], 1.5)
        self.assertEqual(row["weekly_bootstrap_high"], 1.5)
        with self.assertRaises(ValueError):
            compare(old, new.iloc[:1], "2025_26", "single_prior")

    def test_exact_binomial_truth_matches_enumerating_individual_shots(self):
        stub = SimpleNamespace(MatchupEngine=MatchupEngine, WEEKLY_VAR_INFLATION_BY_CAT={"FG": 1.0})
        grid = fixed_attempt_audit(stub)
        row = grid[
            (grid.attempts_a == 2)
            & (grid.attempts_b == 2)
            & (grid.accuracy_a == 0.6)
            & (grid.accuracy_b == 0.5)
        ].iloc[0]
        exact = 0.0
        for outcomes in itertools.product((0, 1), repeat=4):
            mass = 1.0
            for made, p in zip(outcomes, (0.6, 0.6, 0.5, 0.5)):
                mass *= p if made else 1 - p
            a, b = sum(outcomes[:2]), sum(outcomes[2:])
            exact += mass * (float(a > b) + 0.5 * float(a == b))
        self.assertAlmostEqual(row.exact_category_credit, exact, places=12)

    def test_correlated_absence_generator_matches_independent_closed_form(self):
        _, _, steals = sample_team(np.random.default_rng(777), 1, 4, 650, 0.8, 0.65, 100000, 0.55)
        mean_rate = 0.04
        rate_var = mean_rate / 650
        game_mean = 30 * mean_rate
        game_variance = game_mean + rate_var * (30**2 + 36) + mean_rate**2 * 36
        covariance_play = 0.65 * 0.8 * 0.2
        exact_variance = 4 * (0.8 * game_variance + 0.8 * 0.2 * game_mean**2) + 12 * (
            (0.8**2 + covariance_play) * 30**2 * rate_var + covariance_play * game_mean**2
        )
        self.assertAlmostEqual(steals.mean(), 4 * 0.8 * game_mean, delta=0.04)
        self.assertAlmostEqual(steals.var(), exact_variance, delta=0.2)


if __name__ == "__main__":
    unittest.main()

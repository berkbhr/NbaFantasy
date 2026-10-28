import unittest

from research.roster_backtest import calibration, make_rosters, score_lineups
from src.matchup_engine import ALL_CATEGORIES
from src.probability import CategoryProbabilities


class RosterBacktestTests(unittest.TestCase):
    def test_actual_scoring_uses_frozen_starts_not_best_hindsight_players(self):
        actual = {
            ("2024-11-04", 1): {"PTS": 4, "FGM": 2},
            ("2024-11-04", 2): {"PTS": 99, "FGM": 40},
        }
        result = score_lineups({"2024-11-04": [1]}, actual)
        self.assertEqual(result["PTS"], 4)
        self.assertEqual(result["FGM"], 2)
        actual[("2024-11-04", 2)]["PTS"] = 200
        self.assertEqual(score_lineups({"2024-11-04": [1]}, actual), result)
        self.assertEqual(score_lineups({}, actual), dict.fromkeys(ALL_CATEGORIES, 0.0))
        with self.assertRaises(ValueError):
            score_lineups({"2024-11-04": [1, 1]}, actual)

    def test_roster_profiles_preserve_unique_legal_ownership_and_prior_tiers(self):
        pool = list(range(240))
        positions = {p: "C" if p % 4 == 0 else "G" if p % 4 == 1 else "F" for p in pool}
        for seed in (1000, 1001, 1002):
            rosters, _ = make_rosters(pool, positions, seed)
            self.assertEqual(len(rosters), 14)
            self.assertTrue(all(len(r) == 13 for r in rosters))
            self.assertEqual({p for r in rosters for p in r}, set(range(182)))
            for rnd in range(13):
                self.assertEqual({r[rnd] for r in rosters}, set(range(rnd * 14, (rnd + 1) * 14)))

    def test_multiclass_probability_score_includes_ties(self):
        p = CategoryProbabilities({"BLK": 0.4}, {"BLK": 0.2})
        brier, error = calibration(p, {"categories": {"BLK": "draw"}, "category_points": 0.5})
        self.assertAlmostEqual(brier, 0.96)
        self.assertAlmostEqual(error, 0)


if __name__ == "__main__":
    unittest.main()

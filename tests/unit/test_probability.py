import itertools
import unittest

from src.matchup_engine import ALL_CATEGORIES, MatchupEngine
from src.probability import CategoryProbabilities, category_points, decision_value, matchup_outcome


def distribution(**values):
    return {
        "mean": {**dict.fromkeys(ALL_CATEGORIES, 0.0), **values},
        "var": dict.fromkeys(ALL_CATEGORIES + ["FGM_cond", "FTM_cond"], 0.0),
    }


class TestProbability(unittest.TestCase):
    def test_exact_outcomes_match_exhaustive_enumeration(self):
        wins = {"a": 0.1, "b": 0.8, "c": 0.4, "d": 0.7}
        ties = {"a": 0.2, "b": 0.1, "c": 0.3, "d": 0}
        expected = [0.0, 0.0, 0.0]
        for states in itertools.product((-1, 0, 1), repeat=4):
            mass = 1.0
            for category, state in zip(wins, states):
                mass *= (
                    wins[category]
                    if state == 1
                    else (ties[category] if state == 0 else 1 - wins[category] - ties[category])
                )
            balance = sum(states)
            expected[0 if balance > 0 else (1 if balance < 0 else 2)] += mass
        actual = matchup_outcome(CategoryProbabilities(wins, ties))
        for a, b in zip((actual.win, actual.loss, actual.draw), expected):
            self.assertAlmostEqual(a, b)

    def test_certain_results_and_four_three_two_win(self):
        for w, losses, t in [(5, 4, 0), (4, 5, 0), (4, 3, 2), (3, 3, 3), (0, 0, 9)]:
            probabilities = CategoryProbabilities(
                {i: float(i < w) for i in range(9)}, {i: float(i >= w + losses) for i in range(9)}
            )
            outcome = matchup_outcome(probabilities)
            self.assertEqual(outcome.win, float(w > losses))
            self.assertEqual(outcome.loss, float(losses > w))
            self.assertEqual(outcome.draw, float(w == losses))

    def test_regular_season_prefers_category_points(self):
        concentrated = CategoryProbabilities(dict(enumerate([1] * 4 + [0.9] + [0] * 4)))
        balanced = CategoryProbabilities(dict(enumerate([0.6] * 9)))
        self.assertGreater(decision_value(balanced), decision_value(concentrated))
        self.assertGreater(
            decision_value(concentrated, "matchup"), decision_value(balanced, "matchup")
        )
        self.assertAlmostEqual(decision_value(concentrated), 4.9)

    def test_category_ties_are_half_a_point(self):
        p = CategoryProbabilities({"PTS": 0.4, "REB": 0.2}, {"PTS": 0.2, "REB": 0.6})
        self.assertAlmostEqual(category_points(p), 1.0)

    def test_finished_matchup_uses_actual_ties(self):
        a = distribution(
            PTS=100, REB=50, AST=20, STL=3, BLK=2, TOV=12, FG3M=9, FGM=50, FGA=100, FTM=8, FTA=10
        )
        b = distribution(
            PTS=90, REB=50, AST=25, STL=3, BLK=1, TOV=15, FG3M=10, FGM=40, FGA=80, FTM=8, FTA=10
        )
        points, probs, _ = MatchupEngine.evaluate_h2h_matchup(a, b)
        self.assertAlmostEqual(points, 5.0)  # 3 wins, 2 losses, 4 ties.
        self.assertEqual(matchup_outcome(probs).win, 1.0)
        self.assertEqual(probs.ties["FG_PCT"], 1.0)

    def test_unequal_shooting_volume_ratio_variance(self):
        a, b = distribution(FGM=55, FGA=100), distribution(FGM=500, FGA=1000)
        a["var"]["FGM"] = a["var"]["FGM_cond"] = 100 * 0.55 * 0.45
        b["var"]["FGM"] = b["var"]["FGM_cond"] = 1000 * 0.5 * 0.5
        _, probs, _ = MatchupEngine.evaluate_h2h_matchup(a, b)
        self.assertAlmostEqual(probs["FG_PCT"], 0.83063356795, delta=0.003)

    def test_swap_symmetry_including_ties_and_copula(self):
        p = CategoryProbabilities({"a": 0.8, "b": 0.1, "c": 0.4}, {"a": 0.1, "b": 0.3, "c": 0.2})
        reverse = CategoryProbabilities({c: 1 - p[c] - p.ties[c] for c in p}, p.ties)
        for rho in (0, 0.15):
            a, b = matchup_outcome(p, rho=rho), matchup_outcome(reverse, rho=rho)
            self.assertAlmostEqual(a.win, b.loss, places=8)
            self.assertAlmostEqual(a.draw, b.draw, places=8)
            self.assertAlmostEqual(a.win + a.loss + a.draw, 1.0)

    def test_invalid_marginals_are_rejected(self):
        with self.assertRaises(ValueError):
            matchup_outcome(CategoryProbabilities({"a": 0.9}, {"a": 0.2}))


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.matchup_engine import ALL_CATEGORIES
from src.playoffs import estimate_playoff_probabilities
from src.settings import LeagueSettings
from src.snapshots import validate_live_snapshot
from src.validation import score_matchups, walk_forward


class TestValidation(unittest.TestCase):
    def test_regular_season_and_playoff_policies_are_explicit(self):
        self.assertEqual(LeagueSettings().objective, "category_points")
        with self.assertRaises(ValueError):
            LeagueSettings(phase="playoffs")
        settings = LeagueSettings(phase="playoffs", playoff_tie_credit=0)
        self.assertEqual(settings.objective, "matchup")
        self.assertEqual(settings.draw_value, 0)

    def test_playoff_cutoff_uses_category_records(self):
        standings = {str(i): {"W": 90 - i * 10, "L": i * 10, "T": 0} for i in range(6)}
        result = estimate_playoff_probabilities(standings, [], simulations=100)
        self.assertEqual(sum(r["playoff_probability"] for r in result["teams"].values()), 4)
        for i in range(6):
            self.assertEqual(result["teams"][str(i)]["playoff_probability"], float(i < 4))

    def test_playoff_fixture_accumulates_eight_one_not_one_weekly_win(self):
        standings = {"a": {"W": 1, "L": 8}, "b": {"W": 1, "L": 8}}
        fixture = {
            "week": 2,
            "home": "a",
            "away": "b",
            "categories": {str(i): {"win": float(i < 8), "tie": 0} for i in range(9)},
        }
        result = estimate_playoff_probabilities(
            standings, [fixture], playoff_spots=1, simulations=20
        )
        self.assertEqual(result["teams"]["a"]["playoff_probability"], 1)
        self.assertAlmostEqual(result["teams"]["a"]["expected_final_category_percentage"], 0.5)
        self.assertAlmostEqual(result["teams"]["b"]["expected_final_category_percentage"], 2 / 18)

    def test_playoff_cutoff_ties_do_not_depend_on_alphabetical_order(self):
        standings = {str(i): {"W": 10, "L": 10} for i in range(6)}
        result = estimate_playoff_probabilities(standings, [], simulations=10000)
        for record in result["teams"].values():
            self.assertAlmostEqual(record["playoff_probability"], 4 / 6, delta=0.02)

    def test_playoff_rejects_duplicate_fixtures_and_weekly_only_inputs(self):
        standings = {"a": {"W": 1}, "b": {"W": 1}}
        fixture = {
            "week": 1,
            "home": "a",
            "away": "b",
            "categories": {str(i): {"win": 0.5} for i in range(9)},
        }
        with self.assertRaises(ValueError):
            estimate_playoff_probabilities(standings, [fixture, fixture], playoff_spots=1)
        with self.assertRaises(ValueError):
            estimate_playoff_probabilities(
                standings, [{"week": 1, "home": "a", "away": "b", "win": 0.7}], playoff_spots=1
            )

    def test_probability_scoring_and_temporal_guard(self):
        forecast = {
            "id": "week1",
            "forecast_at": "2026-10-20T10:00Z",
            "win": 0.8,
            "loss": 0.1,
            "draw": 0.1,
        }
        truth = {"id": "week1", "completed_at": "2026-10-26T04:00Z", "result": "win"}
        result = score_matchups([forecast], [truth])
        self.assertAlmostEqual(result["brier"], 0.06)
        forecast["forecast_at"] = "2026-10-27T10:00Z"
        with self.assertRaises(ValueError):
            score_matchups([forecast], [truth])

    def test_live_snapshot_freshness_week_and_shooting_checks(self):
        team = {k: 0 for k in ALL_CATEGORIES}
        snapshot = {
            "updated_at": "2026-10-27T10:00Z",
            "matchup": {"team_a": team.copy(), "team_b": team.copy()},
        }
        self.assertTrue(validate_live_snapshot(snapshot, "2026-10-27T11:00Z"))
        with self.assertRaises(ValueError):
            validate_live_snapshot(snapshot, "2026-10-29T11:00Z")
        snapshot["matchup"]["team_a"]["FGM"] = 2
        with self.assertRaises(ValueError):
            validate_live_snapshot(snapshot, "2026-10-27T11:00Z")

    def test_future_box_score_cannot_change_earlier_predictions(self):
        # All temporary files are contained inside the repository test directory.
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmp:
            root = Path(tmp)
            (root / "raw").mkdir()
            (root / "processed").mkdir()
            base = {k: 0 for k in ALL_CATEGORIES}
            prior = {
                **base,
                "PLAYER_ID": 1,
                "PLAYER_NAME": "Example",
                "TEAM_ID": 10,
                "GAME_ID": "prior",
                "GAME_DATE": "2025-01-01",
                "MIN": 1000,
                "PTS": 500,
            }
            pd.DataFrame([prior]).to_parquet(root / "raw" / "player_logs_2024_25.parquet")
            first = {
                **base,
                "PLAYER_ID": 1,
                "PLAYER_NAME": "Example",
                "TEAM_ID": 10,
                "GAME_ID": "one",
                "GAME_DATE": "2025-10-20",
                "MIN": 30,
                "PTS": 10,
            }
            second = {**first, "GAME_ID": "two", "GAME_DATE": "2025-10-22", "PTS": 20}
            path = root / "raw" / "player_logs_2025_26.parquet"
            pd.DataFrame([first, second]).to_parquet(path)
            a, _ = walk_forward("2025_26", root)
            second["PTS"] = 100
            pd.DataFrame([first, second]).to_parquet(path)
            b, _ = walk_forward("2025_26", root)
            pd.testing.assert_series_equal(a.bayesian, b.bayesian)


if __name__ == "__main__":
    unittest.main()

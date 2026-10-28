import copy
import unittest

from src.matchup_engine import ALL_CATEGORIES, MatchupEngine
from src.snapshots import validate_live_snapshot


def future(blocks, variance):
    return {
        "mean": {**dict.fromkeys(ALL_CATEGORIES, 0.0), "BLK": blocks},
        "var": {**dict.fromkeys(ALL_CATEGORIES, 0.0), "BLK": variance},
    }


class TestScoreUpdates(unittest.TestCase):
    def test_shifted_score_columns_fail_even_when_all_values_are_nonnegative(self):
        stats = dict.fromkeys(ALL_CATEGORIES, 0)
        stats.update(FGM=10, FGA=20, FTM=2, FTA=3, FG3M=3, PTS=25)
        snapshot = {
            "updated_at": "2026-10-28T12:00Z",
            "matchup": {"team_a": stats.copy(), "team_b": stats.copy()},
        }
        validate_live_snapshot(snapshot, "2026-10-28T13:00Z")
        snapshot["matchup"]["team_a"]["PTS"] = 26
        with self.assertRaisesRegex(ValueError, "identity"):
            validate_live_snapshot(snapshot, "2026-10-28T13:00Z")

    def test_yesterdays_score_is_rejected_even_when_less_than_24_hours_old(self):
        stats = dict.fromkeys(ALL_CATEGORIES, 0)
        snapshot = {
            "updated_at": "2026-10-27T15:57:51+00:00",
            "matchup": {"team_a": stats.copy(), "team_b": stats.copy()},
        }
        validate_live_snapshot(snapshot, "2026-10-27T23:42:28+00:00")
        # Same week and only 20.6 hours later, but yesterday's evening games
        # would vanish if this score were combined with an Oct28 window.
        with self.assertRaisesRegex(ValueError, "Eastern game date"):
            validate_live_snapshot(snapshot, "2026-10-28T12:34:26+00:00")

    def test_utc_midnight_does_not_invalidate_same_eastern_date(self):
        stats = dict.fromkeys(ALL_CATEGORIES, 0)
        snapshot = {
            "updated_at": "2026-10-27T23:00:00+00:00",
            "matchup": {"team_a": stats.copy(), "team_b": stats.copy()},
        }
        self.assertTrue(validate_live_snapshot(snapshot, "2026-10-28T01:00:00+00:00"))

    def test_eleven_realized_blocks_can_change_a_close_category_sharply(self):
        # Fixed future means and uncertainty isolate the actual-score change.
        # The observed 6-5 -> 6-16 score is not 11 extra future blocks.
        mine, theirs = future(17.58, 25), future(18.68, 25)
        original = copy.deepcopy((mine, theirs))
        old_a, old_b = {"BLK": 6}, {"BLK": 5}
        new_b = {"BLK": 16}
        a = MatchupEngine.combine_live_and_remaining_dist(old_a, mine)
        before = MatchupEngine.combine_live_and_remaining_dist(old_b, theirs)
        after = MatchupEngine.combine_live_and_remaining_dist(new_b, theirs)
        p_before = MatchupEngine.evaluate_h2h_matchup(a, before)[1]
        p_after = MatchupEngine.evaluate_h2h_matchup(a, after)[1]
        self.assertAlmostEqual(p_before["BLK"], 0.466, delta=0.002)
        self.assertAlmostEqual(p_after["BLK"], 0.050, delta=0.002)
        self.assertEqual(before["var"], after["var"])
        self.assertEqual(after["mean"]["BLK"] - before["mean"]["BLK"], 11)
        self.assertEqual((mine, theirs), original)
        details = MatchupEngine.category_diagnostics(a, after, old_a, new_b)["BLK"]
        self.assertAlmostEqual(details["my_remaining_mean"], 17.58)
        self.assertAlmostEqual(details["opponent_remaining_mean"], 18.68)
        self.assertEqual(details["opponent_actual"], 16)

    def test_scoreboard_game_counters_do_not_multiply_remaining_projections(self):
        remaining = future(12, 16)
        one = MatchupEngine.combine_live_and_remaining_dist(
            {"BLK": 6, "games_played": 7, "games_remaining": 37}, remaining
        )
        two = MatchupEngine.combine_live_and_remaining_dist(
            {"BLK": 6, "games_played": 14, "games_remaining": 28}, remaining
        )
        self.assertEqual(one, two)
        self.assertEqual(two["mean"]["BLK"], 18)


if __name__ == "__main__":
    unittest.main()

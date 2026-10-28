import unittest
from copy import deepcopy

import pandas as pd

from src.game_clock import enrich_schedule
from src.snapshots import validate_pregame_window
from src.yahoo_identity import canonical_scoreboard, roster_player_evidence, team_slots


class TimeIdentityTests(unittest.TestCase):
    def schedule(self):
        return pd.DataFrame(
            [
                {
                    "GAME_ID": "g",
                    "GAME_DATE": pd.Timestamp("2026-10-28"),
                    "TIPOFF_UTC": "2026-10-29T00:00Z",
                    "CLOCK_OBSERVED_AT": "2026-10-28T12:00Z",
                }
            ]
        )

    def test_pregame_allowed_but_partial_or_completed_same_day_not_reprojected(self):
        frame = self.schedule()
        validate_pregame_window(frame, "2026-10-28T23:59Z")
        with self.assertRaisesRegex(ValueError, "started"):
            validate_pregame_window(frame, "2026-10-29T00:00Z")
        with self.assertRaisesRegex(ValueError, "started"):
            validate_pregame_window(frame, "2026-10-29T03:00Z")

    def test_missing_unknown_stale_or_future_clock_fails_closed(self):
        frame = self.schedule()
        for field, value in (
            ("TIPOFF_UTC", None),
            ("CLOCK_OBSERVED_AT", "2026-10-27T12:00Z"),
            ("CLOCK_OBSERVED_AT", "2026-10-30T12:00Z"),
        ):
            changed = frame.copy()
            changed[field] = value
            with self.assertRaises(ValueError):
                validate_pregame_window(changed, "2026-10-28T20:00Z")
        with self.assertRaises(ValueError):
            validate_pregame_window(frame.drop(columns="TIPOFF_UTC"), "2026-10-28T20:00Z")

    def test_official_clock_matches_game_ids_and_eastern_dates(self):
        cached = self.schedule().drop(columns="TIPOFF_UTC")
        official = pd.DataFrame([{"gameId": "g", "gameDateTimeUTC": "2026-10-29T00:00Z"}])
        enriched = enrich_schedule(cached, official)
        self.assertEqual(enriched.TIPOFF_UTC.iloc[0], pd.Timestamp("2026-10-29T00:00Z"))
        wrong = official.copy()
        wrong["gameId"] = "unknown"
        with self.assertRaises(ValueError):
            enrich_schedule(cached, wrong)
        wrong = official.copy()
        wrong["gameDateTimeUTC"] = "2026-10-30T00:00Z"
        with self.assertRaises(ValueError):
            enrich_schedule(cached, wrong)

    def test_persisted_team_id_survives_rename_and_total_roster_turnover(self):
        roster = {"13": [{"name": "Completely New Player"}]}
        mapping, evidence = team_slots(roster, {"14": "7"}, {"13": "Renamed Team"})
        self.assertEqual(mapping, {"14": "7"})
        self.assertEqual(evidence["14"], "saved_id")
        with self.assertRaises(ValueError):
            team_slots(roster, {})
        with self.assertRaises(ValueError):
            team_slots({}, {"14": "7", "2": "7"})

    def test_yahoo_player_id_cannot_be_owned_twice(self):
        with self.assertRaises(ValueError):
            roster_player_evidence(
                {
                    "0": [{"name": "A", "yahoo_player_id": "20"}],
                    "1": [{"name": "Alias A", "yahoo_player_id": "20"}],
                },
                {"1": "0", "2": "1"},
            )

    def test_scoreboard_and_final_slots_map_together_without_mutating_provider_payload(self):
        board = {"matchups": [[{"slot": 14}, {"slot": 2}]], "matchup_states": [{"slots": [14, 2]}]}
        original = deepcopy(board)
        mapped = canonical_scoreboard(board, {"14": "7", "2": "1"})
        self.assertEqual(mapped["matchup_states"][0]["slots"], [8, 2])
        self.assertEqual(mapped["matchups"][0][0]["yahoo_team_id"], 14)
        self.assertEqual(board, original)


if __name__ == "__main__":
    unittest.main()

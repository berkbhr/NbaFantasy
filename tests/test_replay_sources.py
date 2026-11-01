"""Point-in-time source boundaries through the real assistant and forecast engine."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.live_draft_assistant import LiveDraftAssistant
from src.priors import get_positional_averages
from src.trade_projection_cache import TradeProjectionCache

CUTOFF = "2025-10-20T12:00:00Z"
PAST = "2025-10-19T10:00:00Z"
FUTURE = "2026-11-01T10:00:00Z"


class ReplaySourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name)
        self.raw, self.processed = self.data / "raw", self.data / "processed"
        self.raw.mkdir()
        self.processed.mkdir()
        logs = pd.DataFrame(
            [
                {
                    "PLAYER_ID": pid,
                    "PLAYER_NAME": f"Player {pid}",
                    "TEAM_ID": 10,
                    "GAME_DATE": day,
                    "GAME_ID": f"{pid}-{day}",
                    "MIN": 30,
                    "PTS": 6 if pid <= 16 else 30,
                    "REB": 5,
                    "AST": 3,
                    "STL": 1,
                    "BLK": 1,
                    "TOV": 2,
                    "FG3M": 1,
                    "FGM": 5,
                    "FGA": 12,
                    "FTM": 2,
                    "FTA": 3,
                }
                for pid in range(1, 33)
                for day in pd.date_range("2025-01-01", periods=20)
            ]
        )
        logs.to_parquet(self.raw / "player_logs_2024_25.parquet", index=False)
        pd.DataFrame({"TEAM_ID": [10], "GAME_DATE": ["2025-10-20"], "GAME_ID": ["g"]}).to_parquet(
            self.processed / "schedule_2025_26.parquet", index=False
        )
        for target, value in [
            ("src.live_draft_assistant.DATA_DIR", str(self.data)),
            ("src.live_draft_assistant.PROCESSED_DIR", str(self.processed)),
            ("src.priors.RAW_DIR", str(self.raw)),
            ("src.priors.PROCESSED_DIR", str(self.processed)),
            ("src.matchup_engine.DATA_DIR", self.data),
        ]:
            p = patch(target, value)
            p.start()
            self.addCleanup(p.stop)
        self.tracker_patch = patch("src.live_draft_assistant.InjuryTracker")
        self.tracker = self.tracker_patch.start()
        self.addCleanup(self.tracker_patch.stop)
        self.tracker.return_value.get_all_active_injuries.return_value = []

    def assistant(self, replay=True, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return LiveDraftAssistant(
                prior_season="2024_25",
                historical_replay=replay,
                use_positional_depth_and_injury_boost=False,
                **kwargs,
            )

    def positions(self, value):
        pd.DataFrame({"PLAYER_ID": range(1, 33), "POSITION": value}).to_parquet(
            self.processed / "player_positions.parquet", index=False
        )

    def distribution(self, assistant, **kwargs):
        return assistant.engine.get_expected_weekly_distribution(
            [1, 2, 3], "2025-10-20", "2025-10-20", **kwargs
        )

    def injury(self, effective=PAST, observed=PAST, status="OUT"):
        return {
            "player_id": 1,
            "status": status,
            "effective_at": effective,
            "observed_at": observed,
        }

    def test_replay_ignores_live_out_even_when_explicitly_requested(self):
        base = self.assistant()
        self.tracker.return_value.get_all_active_injuries.return_value = [
            {"player_id": 1, "status": "OUT", "updated_at": FUTURE}
        ]
        changed = self.assistant(use_live_injuries=True)
        self.tracker.assert_not_called()
        self.assertFalse(changed.use_live_injuries)
        self.assertEqual(changed.players[1].injury_status, "HEALTHY")
        self.assertEqual(base.projected_stats, changed.projected_stats)
        self.assertEqual(self.distribution(base), self.distribution(changed))

    def test_live_constructor_still_loads_current_out(self):
        self.positions("C")
        self.tracker.return_value.get_all_active_injuries.return_value = [
            {"player_id": 1, "status": "OUT", "updated_at": FUTURE}
        ]
        live = self.assistant(replay=False)
        self.tracker.assert_called_once()
        self.assertTrue(live.use_live_injuries)
        self.assertEqual(live.players[1].get_effective_game_availability(), 0)
        self.assertEqual(live.engine.pos_dict[1], "C")

    def test_historical_injuries_require_both_dates_at_or_before_cutoff(self):
        base = self.assistant(replay_as_of=CUTOFF)
        for effective, observed in [
            (PAST, FUTURE),
            (FUTURE, PAST),
            (None, PAST),
            (PAST, None),
            (PAST, "bad"),
        ]:
            with self.subTest(effective=effective, observed=observed):
                replay = self.assistant(
                    replay_as_of=CUTOFF, historical_injuries=[self.injury(effective, observed)]
                )
                self.assertEqual(replay.projected_stats, base.projected_stats)
                self.assertEqual(self.distribution(replay), self.distribution(base))
        known = self.assistant(replay_as_of=CUTOFF, historical_injuries=[self.injury()])
        self.assertEqual(known.players[1].get_effective_game_availability(), 0)
        self.assertEqual(known.projected_stats[1]["PTS"], 0)
        self.assertLess(
            known.engine.get_expected_weekly_distribution([1])["mean"]["PTS"],
            base.engine.get_expected_weekly_distribution([1])["mean"]["PTS"],
        )
        boundary = self.assistant(
            replay_as_of=CUTOFF, historical_injuries=[self.injury(CUTOFF, CUTOFF)]
        )
        self.assertEqual(boundary.players[1].injury_status, "OUT")
        self.tracker.assert_not_called()

    def test_historical_clearance_and_future_update_do_not_replace_known_state(self):
        known = self.injury()
        cleared = self.injury("2025-10-20T09:00Z", "2025-10-20T09:30Z", "HEALTHY")
        future = self.injury(FUTURE, FUTURE)
        replay = self.assistant(replay_as_of=CUTOFF, historical_injuries=[future, known, cleared])
        self.assertEqual(replay.players[1].injury_status, "HEALTHY")

    def test_replay_positions_and_forecast_ignore_current_snapshot_perturbation(self):
        self.positions("UTIL")
        first = self.assistant()
        self.positions("C")
        second = self.assistant()
        self.assertEqual(first.pos_dict, {})
        self.assertEqual(second.engine.pos_dict, {})
        self.assertEqual(first.pos_averages, second.pos_averages)
        self.assertEqual(first.projected_stats, second.projected_stats)
        self.assertEqual(self.distribution(first), self.distribution(second))
        # Explicitly prove the perturbation matters to the live eligibility path.
        self.positions("UTIL")
        live_util = self.assistant(replay=False)
        self.positions("C")
        live_c = self.assistant(replay=False)
        self.assertGreater(
            self.distribution(live_c)["mean"]["PTS"], self.distribution(live_util)["mean"]["PTS"]
        )

    def test_dated_position_history_controls_prior_bucket_and_eligibility(self):
        history = [
            {
                "PLAYER_ID": pid,
                "POSITION": "G" if pid <= 16 else "C",
                "effective_at": PAST,
                "observed_at": PAST,
            }
            for pid in range(1, 33)
        ]
        future = {"PLAYER_ID": 1, "POSITION": "C", "effective_at": FUTURE, "observed_at": FUTURE}
        first = self.assistant(replay_as_of=CUTOFF, historical_positions=history)
        changed = self.assistant(replay_as_of=CUTOFF, historical_positions=[future, *history])
        self.assertEqual(first.pos_dict[1], "G")
        self.assertEqual(changed.engine.pos_dict[1], "G")
        self.assertIn("PG", first.get_eligible_slots(first.pos_dict[1]))
        self.assertNotIn("C", first.get_eligible_slots(first.pos_dict[1]))
        self.assertNotEqual(
            first.pos_averages["BY_POS"]["G"]["PTS"], first.pos_averages["BY_POS"]["C"]["PTS"]
        )
        self.assertEqual(first.projected_stats, changed.projected_stats)
        self.assertEqual(self.distribution(first), self.distribution(changed))
        # The same player's later legitimate position is used only at a later cutoff.
        later = self.assistant(replay_as_of=FUTURE, historical_positions=[*history, future])
        self.assertEqual(later.engine.pos_dict[1], "C")
        self.assertNotEqual(later.players[1].alphas["PTS"], first.players[1].alphas["PTS"])

    def test_missing_undated_future_positions_use_pooled_prior_and_generic_slots(self):
        base = self.assistant()
        for row in [
            {"PLAYER_ID": 1, "POSITION": "C"},
            {"PLAYER_ID": 1, "POSITION": "C", "effective_at": PAST, "observed_at": FUTURE},
            {"PLAYER_ID": 1, "POSITION": "C", "effective_at": FUTURE, "observed_at": PAST},
        ]:
            replay = self.assistant(replay_as_of=CUTOFF, historical_positions=[row])
            self.assertEqual(replay.engine.pos_dict, {})
            self.assertEqual(replay.pos_averages, base.pos_averages)
            self.assertEqual(replay.projected_stats, base.projected_stats)
        pooled = get_positional_averages(base.priors, use_live_positions=False)
        self.assertEqual(pooled, base.pos_averages)
        self.assertEqual(pooled["BY_POS"]["G"]["PTS"], pooled["PTS"])

    def test_explicit_historical_sources_require_cutoff_and_cannot_enter_live_mode(self):
        for source in [{"historical_injuries": [self.injury()]}, {"historical_positions": []}]:
            for cutoff in [None, "bad"]:
                with self.assertRaises(ValueError):
                    self.assistant(replay_as_of=cutoff, **source)
            with self.assertRaises(ValueError):
                self.assistant(replay=False, replay_as_of=CUTOFF, **source)

    def test_fixed_evidence_cannot_be_reused_for_an_earlier_forecast(self):
        replay = self.assistant(replay_as_of=CUTOFF, historical_injuries=[self.injury()])
        with self.assertRaisesRegex(ValueError, "predates replay"):
            self.distribution(replay, as_of_date="2025-10-20T09:00Z")
        with self.assertRaisesRegex(ValueError, "predate.* replay"):
            replay.engine.get_expected_weekly_distribution([1], "2025-10-19", "2025-10-19")

    def test_replay_cutoff_is_part_of_projection_cache_identity(self):
        first = self.assistant(replay_as_of=CUTOFF)
        later = self.assistant(replay_as_of="2025-10-21T12:00Z")
        self.assertNotEqual(
            TradeProjectionCache.engine_key(first.engine),
            TradeProjectionCache.engine_key(later.engine),
        )

    def test_timestamped_replay_forecast_accepts_naive_completed_game_dates(self):
        replay = self.assistant(replay_as_of=CUTOFF)
        replay.apply_current_season_logs(
            pd.DataFrame(
                [
                    {
                        "PLAYER_ID": 1,
                        "TEAM_ID": 10,
                        "GAME_ID": "observed",
                        "GAME_DATE": "2025-10-19",
                        "MIN": 30,
                        "PTS": 12,
                        "FGM": 4,
                        "FGA": 10,
                        "FTM": 4,
                        "FTA": 5,
                    }
                ]
            )
        )
        result = self.distribution(replay)
        self.assertGreater(result["mean"]["PTS"], 0)


if __name__ == "__main__":
    unittest.main()

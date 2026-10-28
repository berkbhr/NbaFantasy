import unittest
from dataclasses import replace
from unittest.mock import patch

import pandas as pd

from src.bayesian_model import COUNT_STATS, BayesianPlayer
from src.calibrate import gate, replay
from src.model_policy import ModelPolicy
from src.priors import get_positional_averages
from tests.helpers import assistant, logs


class CalibrationTests(unittest.TestCase):
    def frame(self):
        frame = logs(12)
        frame["GAME_DATE"] = frame.GAME_DATE - pd.DateOffset(years=2)
        frame.loc[frame.GAME_ID.astype(int) >= 7, "TEAM_ID"] = 20
        return frame

    def run_frame(self, frame, policy):
        with patch("src.calibrate.load_prior_season", return_value={}):
            return replay("2024_25", policy, logs=frame)

    def test_future_boxscore_cannot_change_earlier_forecasts(self):
        original = self.frame()
        changed = original.copy()
        changed.loc[changed.GAME_ID.astype(int) >= 6, ["MIN", "PTS"]] = [39, 45]
        for role in ("recent_blend", "ewma", "adaptive_anchor"):
            policy = replace(ModelPolicy(), role=role)
            before, after = self.run_frame(original, policy), self.run_frame(changed, policy)
            pd.testing.assert_frame_equal(before.iloc[:30], after.iloc[:30])

    def test_harness_predictions_equal_live_ingestion_with_trade(self):
        frame = self.frame()
        for role in ("recent_blend", "ewma", "adaptive_anchor"):
            policy = replace(ModelPolicy(), role=role, exposure_minutes=360)
            live = assistant()
            live.model_policy = policy
            live.engine.team_map = {}
            live.pos_averages = get_positional_averages({}, pos_dict={})
            for pid in live.players:
                bp = BayesianPlayer(pid, str(pid), policy=policy)
                bp.initialize_priors({}, live.pos_averages)
                live.players[pid] = bp
            observed = []
            for day, daily in frame.groupby("GAME_DATE", sort=True):
                for row in daily.sort_values("PLAYER_ID").to_dict("records"):
                    pred = live.players[row["PLAYER_ID"]].predict_next_game(current_date=day)
                    observed.append([pred[s]["mean"] for s in COUNT_STATS] + [pred["MIN"]["mean"]])
                live.apply_current_season_logs(daily)
            calibrated = self.run_frame(frame, policy)
            expected = calibrated[[s + "_mu" for s in COUNT_STATS]].to_numpy()
            for idx, values in enumerate(observed):
                for j, stat in enumerate(COUNT_STATS):
                    self.assertAlmostEqual(values[j], expected[idx, j], msg=role + stat)
                actual_minutes = float(frame.iloc[idx].MIN)
                self.assertAlmostEqual(
                    abs(values[-1] - actual_minutes), calibrated.iloc[idx].minute_mae
                )

    def test_gate_rejects_no_change_and_population_mismatch(self):
        frame = self.run_frame(self.frame(), ModelPolicy())
        self.assertFalse(gate(frame, frame, "count_nll")["accepted"])
        with self.assertRaises(ValueError):
            gate(frame, frame.iloc[:-1], "count_nll")

    def test_invalid_policy_rejected(self):
        for change in ({"primary_weight": 1.1}, {"exposure_minutes": 0}, {"role": "oracle"}):
            with self.assertRaises(ValueError):
                ModelPolicy(**change)


if __name__ == "__main__":
    unittest.main()

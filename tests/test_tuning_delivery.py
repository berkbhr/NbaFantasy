import json
import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.notifications import DeliveryError, render_telegram, send_telegram
from src.probability import CategoryProbabilities
from src.rotation import adjust_rotations
from src.rotation_policy import RotationPolicy
from src.tune_rotation import replay
from tests.test_model import player


class TuningDeliveryTests(unittest.TestCase):
    def test_telegram_text_is_stable_when_archive_sorts_json_keys(self):
        values = {"PTS": 0.6, "REB": 0.5, "AST": 0.4, "FG_PCT": 0.51}
        archived = json.loads(json.dumps(values, sort_keys=True))

        def message(data):
            return render_telegram(
                now=datetime(2026, 10, 28, 12, tzinfo=timezone.utc),
                opponent="Opponent",
                points=4.5,
                probabilities=CategoryProbabilities(data),
                health=[],
                recommendations=[],
                live=None,
            )

        self.assertEqual(message(values), message(archived))
        self.assertIn("13:00 CET", message(values))

    def test_minute_variance_calibration_is_not_compounded_or_applied_to_shared_rate(self):
        players = {1: player(1, 20), 2: player(2, 30)}
        players[2].update_injury_status("OUT")
        mapping, positions = {1: 10, 2: 10}, {1: "C", 2: "C"}
        adjust_rotations(players, mapping, positions)
        original = players[1].predict_next_game()["PTS"]
        base_variance = players[1].base_minutes_var
        original_minute_variance = players[1].minutes_var
        calibrated = RotationPolicy(minute_variance_scale=1.2)
        for _ in range(2):
            adjust_rotations(players, mapping, positions, policy=calibrated)
            now = players[1].predict_next_game()["PTS"]
            self.assertEqual(now["mean"], original["mean"])
            self.assertEqual(now["shared_covariance"], original["shared_covariance"])
            self.assertGreater(now["variance"], original["variance"])
            self.assertAlmostEqual(players[1].minutes_var, original_minute_variance * 1.2)
            self.assertEqual(players[1].base_minutes_var, base_variance)

    def fixture(self):
        reports, labels, rows = {}, {}, []
        for index, day in enumerate(pd.date_range("2024-11-01", periods=10)):
            date = str(day.date())
            reports[date] = {
                "cutoff_at": date + "T12:00:00-05:00",
                "report_at": date + "T16:00:00Z",
                "rows": [
                    {
                        "game_date": date,
                        "name": "P1",
                        "team_code": "AAA",
                        "status": "OUT" if index >= 3 else "AVAILABLE",
                        "reason_type": "INJURY",
                    }
                ],
                "unsubmitted_teams": [],
            }
            labels[date] = {"rows": []}
            for pid in range(1, 10):
                minutes = 0 if pid == 1 and index >= 3 else 20
                rows.append(
                    {
                        "GAME_DATE": day,
                        "GAME_ID": date,
                        "PLAYER_ID": pid,
                        "PLAYER_NAME": f"P{pid}",
                        "TEAM_ID": 10,
                        "TEAM_ABBREVIATION": "AAA",
                        "MIN": minutes,
                        "PTS": minutes // 2,
                        "REB": 2,
                        "AST": 1,
                        "STL": 0,
                        "BLK": 0,
                        "FG3M": 0,
                        "TOV": 0,
                        "FGM": minutes // 4,
                        "FGA": minutes // 2,
                        "FTM": 0,
                        "FTA": 0,
                    }
                )
                labels[date]["rows"].append(
                    {
                        "norm": f"p{pid}",
                        "team_code": "AAA",
                        "position": "C",
                        "played": minutes > 0,
                        "tipoff_at": date + "T23:00:00Z",
                    }
                )
        logs = pd.DataFrame(rows)
        previous = logs.iloc[:9].copy()
        previous["GAME_DATE"] = pd.Timestamp("2023-11-01")
        priors = {
            pid: {
                "MIN": 1000,
                "GP": 40,
                "PTS": 500,
                "REB": 100,
                "AST": 50,
                "FGM": 200,
                "FGA": 400,
                "FTM": 100,
                "FTA": 140,
            }
            for pid in range(1, 10)
        }
        return logs, previous, priors, reports, labels

    def run_replay(self, logs, previous, priors, reports, labels, policies):
        with (
            patch("src.tune_rotation.load_prior_season", return_value=priors),
            patch("src.tune_rotation.load_reports", return_value=reports),
            patch("src.tune_rotation.read_labels", return_value=labels),
            patch(
                "src.tune_rotation.pd.read_parquet",
                side_effect=lambda p: previous if "2023_24" in str(p) else logs,
            ),
        ):
            return replay("2024_25", policies, root=Path("unused"))

    def test_tuning_candidate_order_does_not_change_learning(self):
        logs, previous, priors, reports, labels = self.fixture()
        policies = {"base": RotationPolicy(), "half": RotationPolicy(0.5, 3)}
        forward = self.run_replay(logs, previous, priors, reports, labels, policies)
        backward = self.run_replay(
            logs, previous, priors, reports, labels, dict(reversed(list(policies.items())))
        )
        self.assertFalse(forward["base"].empty)
        for key in policies:
            pd.testing.assert_frame_equal(forward[key], backward[key])
        self.assertFalse(forward["base"]["mean"].equals(forward["half"]["mean"]))

    def test_future_boxscores_and_positions_cannot_change_past_tuning_predictions(self):
        logs, previous, priors, reports, labels = self.fixture()
        altered = logs.copy()
        altered.loc[altered.GAME_DATE >= pd.Timestamp("2024-11-08"), "MIN"] = 39
        policies = {"base": RotationPolicy(), "evidence": RotationPolicy(0.75, 8)}
        first = self.run_replay(logs, previous, priors, reports, labels, policies)
        altered_labels = deepcopy(labels)
        for date, payload in altered_labels.items():
            if date >= "2024-11-08":
                for row in payload["rows"]:
                    row["position"] = "G"
        second = self.run_replay(altered, previous, priors, reports, altered_labels, policies)
        for key in policies:
            pd.testing.assert_frame_equal(
                first[key][first[key].date < "2024-11-08"],
                second[key][second[key].date < "2024-11-08"],
            )

    def test_smooth_evidence_policy_has_no_low_minutes_cutoff(self):
        player = type(
            "Player",
            (),
            {
                "base_expected_minutes": 25,
                "prior_expected_minutes": 25,
                "current_season_gp": 3,
                "current_season_mpg": 8,
            },
        )()
        policy = RotationPolicy(0.75, 3)
        factor = policy.evidence_factor(player)
        self.assertGreater(factor, 0)
        self.assertLess(factor, 1)
        player.current_season_gp = 30
        self.assertLess(policy.evidence_factor(player), factor)
        self.assertEqual(replace(policy, role_evidence_prior_games=None).evidence_factor(player), 1)

    def test_today_final_position_is_not_available_for_today_noon_forecast(self):
        logs, previous, priors, reports, labels = self.fixture()
        altered = deepcopy(labels)
        for day, payload in altered.items():
            if day >= "2024-11-08":
                for row in payload["rows"]:
                    if row["norm"] == "p2":
                        row["position"] = "G"
        policies = {"base": RotationPolicy()}
        first = self.run_replay(logs, previous, priors, reports, labels, policies)["base"]
        second = self.run_replay(logs, previous, priors, reports, altered, policies)["base"]
        pd.testing.assert_frame_equal(
            first[first.date <= "2024-11-08"], second[second.date <= "2024-11-08"]
        )
        self.assertFalse(
            first[first.date == "2024-11-09"]["mean"].equals(
                second[second.date == "2024-11-09"]["mean"]
            )
        )

    def test_http200_without_telegram_acknowledgement_is_failure(self):
        response = type("Response", (), {"status_code": 200, "json": lambda self: {"ok": False}})()
        with self.assertRaises(DeliveryError):
            send_telegram("private-token", "private-chat", "hello", post=lambda *a, **k: response)

    def test_partial_delivery_retains_first_receipt_without_leaking_secrets(self):
        accepted = type(
            "Response",
            (),
            {"status_code": 200, "json": lambda self: {"ok": True, "result": {"message_id": 123}}},
        )()
        calls = []

        def post(url, **kwargs):
            calls.append(kwargs)
            if len(calls) > 1:
                raise RuntimeError(url)
            return accepted

        with self.assertRaises(DeliveryError) as caught:
            send_telegram(
                "private-token", "private-chat", ("x" * 2000) + "\n" + ("y" * 2000), post=post
            )
        self.assertEqual(len(caught.exception.receipts), 1)
        self.assertNotIn("private-token", str(caught.exception))
        self.assertNotIn("private-chat", str(caught.exception.receipts))


if __name__ == "__main__":
    unittest.main()

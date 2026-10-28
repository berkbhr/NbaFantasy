import gzip
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.boxscores import roster_labels
from src.injury_experiments import online_availability, spillover_replay
from src.nba_injury_scraper import parse_report_text
from src.notifications import render_telegram
from src.probability import CategoryProbabilities
from src.prospective import read_record, realized_rows, weekly_category_outcome, write_once


class ProspectiveTests(unittest.TestCase):
    def test_spillover_replay_does_not_read_future_boxscores(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root = Path(folder)
            records, reports = [], {}
            for day in pd.date_range("2024-11-01", periods=10):
                date = str(day.date())
                reports[date] = {
                    "date": date,
                    "cutoff_at": date + "T12:00:00-05:00",
                    "report_at": date + "T16:00:00Z",
                    "unsubmitted_teams": [],
                    "rows": [
                        {"game_date": date, "team_code": "AAA", "name": "P1", "status": "OUT"}
                    ],
                }
                labels = []
                for pid in range(1, 10):
                    records.append(
                        {
                            "PLAYER_ID": pid,
                            "PLAYER_NAME": f"P{pid}",
                            "TEAM_ID": 10,
                            "TEAM_ABBREVIATION": "AAA",
                            "GAME_ID": date,
                            "GAME_DATE": day,
                            "MIN": 20,
                            "PTS": 10,
                            **dict.fromkeys(
                                [
                                    "REB",
                                    "AST",
                                    "STL",
                                    "BLK",
                                    "FG3M",
                                    "TOV",
                                    "FGM",
                                    "FGA",
                                    "FTM",
                                    "FTA",
                                ],
                                0,
                            ),
                        }
                    )
                    labels.append({"norm": f"p{pid}", "tipoff_at": date + "T23:00:00Z"})
                path = root / "data/archive/historical_labels/2024_25" / f"{date}.json.gz"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(gzip.compress(json.dumps({"rows": labels}).encode()))
            frame = pd.DataFrame(records)
            changed = frame.copy()
            changed.loc[changed.GAME_DATE >= pd.Timestamp("2024-11-08"), "MIN"] = 39
            results = []
            for data in (frame, changed):
                with (
                    patch("src.injury_experiments.load_prior_season", return_value={}),
                    patch("src.injury_experiments.pd.read_parquet", return_value=data),
                ):
                    results.append(spillover_replay(root, "2024_25", reports))
            self.assertFalse(results[0][1.0].empty)
            for scale in results[0]:
                before, after = results[0][scale], results[1][scale]
                pd.testing.assert_frame_equal(
                    before[before.date < "2024-11-08"], after[after.date < "2024-11-08"]
                )

    def test_reason_above_centered_name_does_not_attach_to_previous_player(self):
        text = """Injury Report: 11/01/24 11:30 AM
11/01/2024 07:00 (ET) BOS@CHA Boston Celtics Horford, Al Out Rest
Injury/Illness - Left Foot; Tendon
Porzingis, Kristaps Out
Strain"""
        rows = parse_report_text(text)["rows"]
        self.assertEqual(rows[0]["desc"], "Rest")
        self.assertEqual(rows[1]["desc"], "Injury/Illness - Left Foot; Tendon Strain")

    def test_forecast_archive_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            path = Path(folder) / "forecast.json.gz"
            write_once(path, {"value": 1})
            with self.assertRaises(FileExistsError):
                write_once(path, {"value": 2})
            self.assertEqual(read_record(path), {"value": 1})

    def bundle(self, day="2026-10-28"):
        return {
            "cutoff_at": "2026-10-27T18:00:00+00:00",
            "player_predictions": {
                "primary": [{"player_id": 1, "team_id": 10, "game_id": "g", "game_date": day}]
            },
        }

    def test_missing_log_is_unknown_explicit_final_dnp_is_negative(self):
        logs = pd.DataFrame()
        now = datetime(2026, 10, 30, tzinfo=timezone.utc)
        self.assertEqual(realized_rows(self.bundle(), logs, now), [])
        labels = realized_rows(
            self.bundle(), logs, now, {(1, "g"): {"team_id": 10, "played": False}}
        )
        self.assertEqual(len(labels), 1)
        self.assertFalse(labels[0]["played"])
        self.assertTrue(labels[0]["availability_evaluable"])

    def test_same_day_forecast_cannot_be_scored_as_future(self):
        with self.assertRaises(ValueError):
            realized_rows(
                self.bundle("2026-10-27"),
                pd.DataFrame(),
                datetime(2026, 10, 30, tzinfo=timezone.utc),
            )

    def test_nonfinal_boxscore_refused(self):
        with self.assertRaises(ValueError):
            roster_labels({"game": {"gameStatus": 2}})

    def test_online_calibration_cannot_read_same_day_outcome(self):
        frame = pd.DataFrame(
            [
                {"date": "2024-11-01", "name": "A", "status": "QUESTIONABLE", "actual": 0},
                {"date": "2024-11-01", "name": "B", "status": "QUESTIONABLE", "actual": 1},
                {"date": "2024-11-02", "name": "C", "status": "QUESTIONABLE", "actual": 1},
            ]
        )
        changed = frame.copy()
        changed.loc[0, "actual"] = 1
        before, _ = online_availability(frame, 20)
        after, _ = online_availability(changed, 20)
        self.assertEqual(list(before.prediction[:2]), list(after.prediction[:2]))
        self.assertNotEqual(before.prediction.iloc[2], after.prediction.iloc[2])

    def test_category_labels_respect_ties_and_low_turnovers(self):
        a = dict.fromkeys(
            ["PTS", "REB", "AST", "STL", "BLK", "FG3M", "TOV", "FGM", "FGA", "FTM", "FTA"], 0
        )
        b = dict(a, TOV=1)
        result = weekly_category_outcome(a, b)
        self.assertEqual(result["category_points"], 5)
        self.assertEqual(result["result"], "win")

    def test_mobile_message_escapes_names_and_limits_alternatives(self):
        probabilities = CategoryProbabilities({"PTS": 0.6, "REB": 0.5, "AST": 0.4})
        recs = [
            {"add_name": "A < B", "drop_name": "C & D", "delta_objective_value": 0.1}
            for _ in range(10)
        ]
        message = render_telegram(
            now=datetime.now(timezone.utc),
            opponent="<b>Fake</b>",
            points=5,
            probabilities=probabilities,
            health=[],
            recommendations=recs,
            live=True,
        )
        self.assertIn("&lt;b&gt;Fake&lt;/b&gt;", message)
        self.assertEqual(message.count("Al:"), 6)
        self.assertLess(len(message), 3900)
        self.assertNotIn("<pre>", message)
        self.assertIn("alternatifidir", message)

    def test_notification_explains_games_and_marginal_category_points(self):
        probs = CategoryProbabilities({"PTS": 0.5, "REB": 0.65})
        live = {
            "team_a": {"games_played": 7, "total_scheduled": 41, "games_remaining": 34},
            "team_b": {"games_played": 9, "total_scheduled": 39, "games_remaining": 30},
        }
        message = render_telegram(
            now=datetime.now(timezone.utc),
            opponent="Opponent",
            points=4.18,
            probabilities=probs,
            health=[],
            live=live,
            recommendations=[
                {
                    "add_name": "Example",
                    "drop_name": "Boş Yuva",
                    "drop_id": None,
                    "base_objective_value": 4.18,
                    "new_objective_value": 4.661,
                    "delta_objective_value": 0.481,
                    "observed_games": 3,
                    "observed_minutes": 8.0,
                    "projected_minutes": 20.2,
                    "role_base_minutes": 12.5,
                }
            ],
        )
        self.assertIn("7 / 41 oynandı · 34 kalan", message)
        self.assertIn("9 / 39 oynandı · 30 kalan", message)
        self.assertIn("4.18 → 4.66 (+0.481)", message)
        self.assertIn("beraberlik ½", message)
        self.assertIn("doğrulanmış süre artışı değil", message)


if __name__ == "__main__":
    unittest.main()

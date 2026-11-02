"""Weekly review keeps one latest daily prediction and never fabricates missing days."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.report_excel import forecast_sheets
from src.report_history import load_week, record_closed_score, record_forecast, weeks
from src.report_panel import ReportService
from tests.test_report_panel import result


def prediction(stamp="2026-11-02T09:00:00Z", points=6.17):
    report = result()
    report.update(
        id="2026-11-02:7:1",
        week_start="2026-11-02",
        week_end="2026-11-08",
        forecast_at=stamp,
        expected_category_points=points,
    )
    report["live_score"].update(period_start="2026-11-02", period_end="2026-11-08", week=3)
    for team in (report["live_score"]["team_a"], report["live_score"]["team_b"]):
        team.update(games_played=0, games_remaining=44, total_scheduled=44)
        team.update(
            dict.fromkeys(
                ("PTS", "REB", "AST", "STL", "BLK", "TOV", "FG3M", "FGM", "FGA", "FTM", "FTA"), 0
            )
        )
    return report


class WeeklyReviewTests(unittest.TestCase):
    def test_latest_daily_forecast_replaces_same_day_but_opening_is_frozen(self):
        with tempfile.TemporaryDirectory() as folder:
            first = prediction()
            original = copy.deepcopy(first)
            key = record_forecast(folder, first)
            record_forecast(folder, prediction("2026-11-02T15:00:00Z", 7.2))
            record_forecast(folder, prediction("2026-11-02T10:00:00Z", 6.1))
            invalid = prediction("2026-11-02T19:00:00Z", 8.9)
            invalid["live_score_valid"] = False
            record_forecast(folder, invalid)
            record_forecast(folder, prediction("2026-11-03T09:00:00Z", 6.5))
            saved = load_week(folder, key)
            self.assertEqual(len(saved["days"]), 2)
            self.assertEqual(saved["days"]["2026-11-02"]["expected_category_points"], 7.2)
            self.assertEqual(saved["opening"]["expected_category_points"], 6.17)
            self.assertEqual(first, original)
            self.assertEqual(len(weeks(folder)), 1)

    def test_invalid_reports_and_other_opponents_never_overwrite_a_day(self):
        with tempfile.TemporaryDirectory() as folder:
            report = prediction()
            report["live_score_valid"] = False
            self.assertIsNone(record_forecast(folder, report))
            self.assertFalse(weeks(folder))
            report["live_score_valid"] = True
            key = record_forecast(folder, report)
            report["live_score"]["team_b"]["yahoo_team_id"] = 99
            self.assertNotEqual(key, record_forecast(folder, report))
            with self.assertRaises(ValueError):
                load_week(folder, "../latest_forecast")

    def test_closed_score_updates_results_without_rewriting_predictions(self):
        with tempfile.TemporaryDirectory() as folder:
            report = prediction()
            key = record_forecast(folder, report)
            board = copy.deepcopy(report["live_score"])
            for side in ("team_a", "team_b"):
                board[side].update(games_played=44, games_remaining=0)
            board["team_a"].update(PTS=20, FGM=10, FGA=20)
            record_closed_score(folder, board, "2026-11-08T18:00:00Z")
            self.assertIsNone(load_week(folder, key)["score"])
            record_closed_score(folder, board, "2026-11-09T14:00:00Z")
            saved = load_week(folder, key)
            self.assertIsNotNone(saved["score"])
            self.assertEqual(saved["days"]["2026-11-02"]["expected_category_points"], 6.17)
            rows = forecast_sheets(report, history=saved)["Haftalık rapor"]
            header = next(i for i, r in enumerate(rows) if r and r[0] == "Gün (Eastern)")
            daily = rows[header + 1 : header + 8]
            self.assertEqual(len(daily), 7)
            self.assertIsNone(daily[1][1])
            self.assertAlmostEqual(daily[0][5], 6.17 - 5.5)

    def test_evening_game_counts_update_without_replacing_valid_prediction(self):
        with tempfile.TemporaryDirectory() as folder:
            report = prediction()
            key = record_forecast(folder, report)
            evening = prediction("2026-11-02T23:30:00Z", 8.9)
            evening["live_score_valid"] = False
            evening["verified_scoreboard"] = evening.pop("live_score")
            board = evening["verified_scoreboard"]
            board["team_a"].update(games_played=10, games_remaining=34)
            board["team_b"].update(games_played=3, games_remaining=35, total_scheduled=38)
            record_forecast(folder, evening)
            saved = load_week(folder, key)
            self.assertEqual(len(saved["days"]), 1)
            self.assertEqual(saved["days"]["2026-11-02"]["expected_category_points"], 6.17)
            rows = forecast_sheets(report, history=saved)["Haftalık rapor"]
            header = next(i for i, r in enumerate(rows) if r and r[0] == "Gün (Eastern)")
            self.assertEqual(rows[header + 1][3:5], ["10/44", "3/38"])
            self.assertIsNone(rows[header + 2][3])

    def test_move_averages_are_exported_without_recalculation_in_review(self):
        report = prediction()
        means = {"PTS": 10.6, "REB": 3.4, "AST": 1.9, "STL": 2.4, "BLK": 0.9, "3PT": 2.2}
        report.update(
            display_mode="weekly_review",
            recommendations=[{"add_name": "A", "drop_name": "B", "exp_stats_pg": means}],
        )
        original = copy.deepcopy(report)
        rows = forecast_sheets(report)["Haftalık rapor"]
        header = next(i for i, r in enumerate(rows) if r == list(means))
        self.assertEqual(rows[header + 1], list(means.values()))
        self.assertEqual(report, original)

    def test_week_with_only_verified_score_observations_is_downloadable(self):
        with tempfile.TemporaryDirectory() as folder, patch("src.report_panel.ROOT", Path(folder)):
            report = prediction()
            report["live_score_valid"] = False
            report["verified_scoreboard"] = report.pop("live_score")
            key = record_forecast(folder, report)
            self.assertEqual(load_week(folder, key)["days"], {})
            service = ReportService()
            try:
                self.assertEqual(service.export(key)[:2], b"PK")
            finally:
                service.pool.shutdown()

    def test_historical_week_can_be_downloaded_without_current_report(self):
        with tempfile.TemporaryDirectory() as folder, patch("src.report_panel.ROOT", Path(folder)):
            key = record_forecast(folder, prediction())
            service = ReportService()
            try:
                payload = service.export(key)
                self.assertEqual(payload[:2], b"PK")
            finally:
                service.pool.shutdown()

    def test_existing_daily_file_survives_new_service_instance(self):
        with tempfile.TemporaryDirectory() as folder, patch("src.report_panel.ROOT", Path(folder)):
            state = Path(folder) / "data/processed/league_state.json"
            state.parent.mkdir(parents=True)
            state.write_text(json.dumps({"league_id": "example"}))
            service = ReportService()
            try:
                key = service._remember_valid(prediction())
            finally:
                service.pool.shutdown()
            restarted = ReportService()
            try:
                self.assertEqual(restarted.state()["weeks"][0]["key"], key)
            finally:
                restarted.pool.shutdown()

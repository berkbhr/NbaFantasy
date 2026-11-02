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
            self.assertAlmostEqual(daily[0][3], 6.17 - 5.5)

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

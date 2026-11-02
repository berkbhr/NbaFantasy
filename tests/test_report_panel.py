"""Local orchestration and exact-value export contracts; no live services."""

import copy
import gzip
import hashlib
import io
import json
import tempfile
import threading
import unittest
from datetime import datetime
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from src import report_panel
from src import yahoo_browser_sync as bridge
from src.notification_state import notification_snapshot
from src.notifications import render_telegram
from src.probability import CategoryProbabilities
from src.report_excel import forecast_sheets, workbook_bytes
from src.report_presentation import game_rows, present_forecast
from tests.test_fantasy_calendar import state_fixture


def result():
    return {
        "forecast_at": "2026-11-01T10:00:00Z",
        "my_team": "=1+1",
        "opponent": "Rakip <A>",
        "expected_category_points": 4.123456789012345,
        "win": 0.123456789012345,
        "categories": {"PTS": {"win": 0.123456789012345, "tie": 0.01, "loss": 0.866543210987655}},
        "my_projected_stats": {"PTS": 123.1234567890123},
        "opponent_projected_stats": {"PTS": 125.25},
        "recommendations": [],
        "my_lineups": {"2026-11-02": ["Oyuncu A"]},
        "notes": ["Örnek"],
        "id": "2026-10-26:7:1",
        "live_score_valid": True,
        "live_score": {
            "team_a": {
                "slot": 8,
                "yahoo_team_id": 14,
                "games_played": 42,
                "total_scheduled": 45,
                "games_remaining": 3,
            },
            "team_b": {
                "slot": 2,
                "yahoo_team_id": 2,
                "games_played": 40,
                "total_scheduled": 43,
                "games_remaining": 3,
            },
        },
    }


class ExportTests(unittest.TestCase):
    def test_xlsx_keeps_exact_values_literal_text_and_original_result(self):
        report = result()
        before = copy.deepcopy(report)
        with ZipFile(io.BytesIO(workbook_bytes(forecast_sheets(report)))) as z:
            self.assertIsNone(z.testzip())
            for name in z.namelist():
                ET.fromstring(z.read(name))
            ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
            cells = sheet.findall(".//s:c", ns)
            numbers = [
                float(c.find("s:v", ns).text) for c in cells if c.find("s:v", ns) is not None
            ]
            self.assertIn(report["categories"]["PTS"]["win"], numbers)
            self.assertIn(report["expected_category_points"], numbers)
            self.assertEqual(
                len(ET.fromstring(z.read("xl/workbook.xml")).findall("s:sheets/s:sheet", ns)), 1
            )
            styles = ET.fromstring(z.read("xl/styles.xml"))
            self.assertIn(
                "0.0%", [f.attrib["formatCode"] for f in styles.findall("s:numFmts/s:numFmt", ns)]
            )
            self.assertEqual(
                float(sheet.find('.//s:c[@r="C7"]/s:v', ns).text),
                report["win"],
            )
            summary = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
            self.assertTrue(any("=1+1" in (t.text or "") for t in summary.findall(".//s:t", ns)))
            self.assertFalse(summary.findall(".//s:f", ns))
        self.assertEqual(report, before)


class ServiceTests(unittest.TestCase):
    def test_forecast_reuses_existing_builder_and_does_not_send_or_write(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(report_panel, "ROOT", Path(temp)):
            state_path = Path(temp) / "data/processed/league_state.json"
            state_path.parent.mkdir(parents=True)
            state_path.write_text(json.dumps({"sync_id": "abc", "rosters": {"0": []}}))
            service = report_panel.ReportService()
            try:
                report = result()
                with (
                    patch.object(
                        report_panel, "build_local_forecast", return_value=report
                    ) as build,
                    patch.object(bridge, "run_cloud_sync") as cloud,
                ):
                    self.assertTrue(service.compute())
                    service.job.result(timeout=5)
                    build.assert_called_once_with()
                    cloud.assert_not_called()
                self.assertEqual(service.state()["report"]["categories"], report["categories"])
                self.assertTrue(service.state()["report_matches_snapshot"])
                state_path.write_text(json.dumps({"sync_id": "changed"}))
                self.assertFalse(service.state()["report_matches_snapshot"])
                self.assertIsNone(service.state()["report"])
                self.assertFalse((Path(temp) / "reports/latest_forecast.json").exists())
                self.assertEqual(
                    len(list((Path(temp) / "reports/panel_forecasts/predictions").glob("*.gz"))),
                    1,
                )
            finally:
                service.pool.shutdown()


class PresentationRegressionTests(unittest.TestCase):
    def test_panel_cache_survives_restart_and_supplies_dated_intraday_forecast(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(report_panel, "ROOT", Path(folder)),
        ):
            root = Path(folder)
            service = report_panel.ReportService()
            try:
                service._remember_valid(result())
            finally:
                service.pool.shutdown()
            displayed = present_forecast(
                self.blocked(), root / "data/archive", root / "reports/panel_forecasts"
            )
            self.assertEqual(displayed["display_mode"], "last_valid_forecast")
            self.assertEqual(
                displayed["expected_category_points"], result()["expected_category_points"]
            )
            self.assertEqual(displayed["recommendations"], [])

    def test_old_report_is_hidden_when_new_sync_sources_do_not_match(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(report_panel, "ROOT", Path(folder)),
        ):
            root = Path(folder)
            (root / "data/processed").mkdir(parents=True)
            (root / "data/processed/league_state.json").write_text(json.dumps({"sync_id": "new"}))
            (root / "reports").mkdir()
            old = result()
            old["source_sha256"] = {"data/processed/league_state.json": "old-hash"}
            (root / "reports/latest_forecast.json").write_text(json.dumps(old))
            service = report_panel.ReportService()
            try:
                self.assertIsNone(service.state()["report"])
                with self.assertRaises(ValueError):
                    service.export()
            finally:
                service.pool.shutdown()

    def blocked(self):
        r = result()
        r.update(
            forecast_at="2026-11-01T21:39:37Z",
            live_score_valid=False,
            verified_scoreboard=copy.deepcopy(r["live_score"]),
            live_score=None,
            live_score_block_reason="Today's NBA games have started; partial-game score coverage is unverified, refresh next Eastern pregame day",
            expected_category_points=6.3936164799224455,
        )
        for side, remaining in (("team_a", 1), ("team_b", 0)):
            team = r["verified_scoreboard"][side]
            team["games_remaining"] = remaining
            team["total_scheduled"] = team["games_played"] + remaining
        return r

    def test_blocked_639_is_hidden_just_like_telegram_but_latest_game_counts_remain(self):
        r = self.blocked()
        before = copy.deepcopy(r)
        with tempfile.TemporaryDirectory() as folder:
            displayed = present_forecast(r, Path(folder))
            self.assertEqual(notification_snapshot(r, folder), (r, None))
        self.assertEqual(displayed["display_mode"], "blocked")
        self.assertFalse(displayed["weekly_forecast_available"])
        self.assertIsNone(displayed["expected_category_points"])
        self.assertEqual(displayed["categories"], {})
        self.assertEqual([x["remaining"] for x in displayed["game_counts"]], [1, 0])
        self.assertEqual([x["total"] for x in displayed["game_counts"]], [43, 40])
        self.assertIn("maçları başladı", displayed["display_message"])
        msg = render_telegram(
            now=datetime.fromisoformat(r["forecast_at"].replace("Z", "+00:00")),
            opponent="Opponent",
            points=r["expected_category_points"],
            probabilities=CategoryProbabilities({"PTS": 0.972}),
            health=[],
            recommendations=[],
            live=None,
            scoreboard=r["verified_scoreboard"],
            live_score_block_reason=r["live_score_block_reason"],
        )
        self.assertIn("Haftalık tahmin geçici olarak durduruldu", msg)
        self.assertNotIn("6.39", msg)
        self.assertIn("42 / 43 oynandı · 1 kalan", msg)
        sheets = forecast_sheets(displayed)
        self.assertFalse(any(6.3936164799224455 in row for rows in sheets.values() for row in rows))
        self.assertEqual(list(sheets), ["Haftalık rapor"])
        self.assertFalse(any(row and row[0] == "PTS" for row in sheets["Haftalık rapor"]))
        self.assertEqual(r, before)

    def test_valid_telegram_values_are_preserved_without_rounding_or_recalculation(self):
        r = result()
        with tempfile.TemporaryDirectory() as folder:
            displayed = present_forecast(r, folder)
        self.assertTrue(displayed["weekly_forecast_available"])
        for key in ("expected_category_points", "categories", "recommendations", "win"):
            self.assertEqual(displayed[key], r[key])
        self.assertEqual([x["remaining"] for x in displayed["game_counts"]], [3, 3])

    def test_archive_uses_same_telegram_snapshot_dated_values_without_actionable_moves(self):
        current = self.blocked()
        candidate = result()
        candidate["forecast_at"] = "2026-11-01T18:02:00Z"
        candidate["expected_category_points"] = 7.0
        candidate["recommendations"] = [{"add_name": "OLD MOVE"}]
        original = copy.deepcopy(candidate)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "predictions").mkdir()
            path = root / "predictions/20261101T180200Z.json.gz"
            path.write_bytes(
                gzip.compress(
                    json.dumps({"primary": candidate, "forecast_id": "previous"}).encode()
                )
            )
            selected, context = notification_snapshot(current, root)
            displayed = present_forecast(current, root)
            self.assertEqual(displayed["display_context"], context)
            self.assertEqual(
                displayed["expected_category_points"], selected["expected_category_points"]
            )
            self.assertEqual(displayed["forecast_at"], candidate["forecast_at"])
            self.assertEqual(displayed["evaluated_at"], current["forecast_at"])
            self.assertEqual(displayed["recommendations"], [])
            self.assertEqual([x["remaining"] for x in displayed["game_counts"]], [1, 0])
            self.assertEqual([x["remaining"] for x in displayed["forecast_game_counts"]], [3, 3])
            (root / "prediction_exclusions").mkdir()
            (root / "prediction_exclusions" / path.name).touch()
            self.assertEqual(present_forecast(current, root)["display_mode"], "blocked")
        self.assertEqual(candidate, original)

    def test_wrong_matchup_and_expired_archive_never_resurrect_predictions(self):
        for stamp, identity in [
            ("2026-10-30T18:02Z", "2026-10-26:7:1"),
            ("2026-11-01T18:02Z", "2026-10-26:7:2"),
        ]:
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / "predictions").mkdir()
                old = result()
                old.update(forecast_at=stamp, id=identity)
                (root / "predictions/20261101T180200Z.json.gz").write_bytes(
                    gzip.compress(json.dumps({"primary": old}).encode())
                )
                self.assertFalse(
                    present_forecast(self.blocked(), root)["weekly_forecast_available"]
                )

    def test_provider_game_counts_are_not_invented_or_truncated(self):
        for team in [
            {"games_remaining": 3},
            {"games_played": 42, "total_scheduled": 45, "games_remaining": 2},
            {"games_played": 42, "total_scheduled": 45, "games_remaining": 3.5},
        ]:
            self.assertFalse(game_rows({"team_a": team})[0]["valid"])

    def test_new_canonical_sync_replaces_panel_memory_and_windows_hash_paths_match(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(report_panel, "ROOT", Path(folder)),
        ):
            root = Path(folder)
            state = root / "data/processed/league_state.json"
            state.parent.mkdir(parents=True)
            state.write_text(json.dumps({"sync_id": "new"}))
            cached = self.blocked()
            cached["source_sha256"] = {
                "data\\processed\\league_state.json": hashlib.sha256(state.read_bytes()).hexdigest()
            }
            path = root / "reports/latest_forecast.json"
            path.parent.mkdir()
            path.write_text(json.dumps(cached))
            service = report_panel.ReportService()
            service.report = result()
            service.report_sync = "old"
            try:
                view = service.state()
                self.assertEqual(view["report"]["display_mode"], "blocked")
                self.assertEqual(view["report"]["forecast_at"], cached["forecast_at"])
                self.assertTrue(view["report_matches_snapshot"])
            finally:
                service.pool.shutdown()

    def test_http_requires_token_for_actions_and_download(self):
        service = report_panel.ReportService()
        server = ThreadingHTTPServer(("127.0.0.1", 0), report_panel.handler_for(service))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = HTTPConnection("127.0.0.1", server.server_port)
            client.request("POST", "/run")
            response = client.getresponse()
            response.read()
            self.assertEqual(response.status, 403)
            client.request("GET", "/export.xlsx")
            response = client.getresponse()
            response.read()
            self.assertEqual(response.status, 403)
            with patch.object(service, "state", return_value={"busy": False}):
                client.request("GET", "/state", headers={"X-Panel-Token": service.token})
                response = client.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read()), {"busy": False})
            client.close()
        finally:
            server.shutdown()
            server.server_close()
            service.pool.shutdown()

    def test_dispatch_runs_local_pipeline_without_git_commands(self):
        _, state, capture = state_fixture()
        payload = {
            "league_id": "64691",
            "fantasy_calendar_capture": capture,
            "rosters_by_slot": {
                str(int(provider) - 1): [
                    {"name": f"Player {int(team) + 1}", "yahoo_player_id": str(101 + int(team))}
                ]
                for provider, team in state["yahoo_team_slots"].items()
            },
        }
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(bridge, "PROCESSED_DIR", folder),
            patch.object(bridge, "LOCAL_REPORT_STATE", {"status": "idle", "sync_id": None}),
            patch.object(bridge, "run_cloud_sync") as local,
            patch("subprocess.run") as command,
        ):
            (Path(folder) / "league_state.json").write_text(json.dumps(state))
            saved = bridge.apply_browser_sync_payload(payload, run_async_cloud=False)
            self.assertTrue(saved["ok"])
            local.assert_called_once_with()
            command.assert_not_called()
            self.assertEqual(bridge.LOCAL_REPORT_STATE["status"], "complete")

    def test_cached_report_is_never_marked_current_without_snapshot_proof(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(report_panel, "ROOT", Path(temp)):
            p = Path(temp) / "reports/latest_forecast.json"
            p.parent.mkdir()
            p.write_text(json.dumps(result()))
            service = report_panel.ReportService()
            try:
                self.assertFalse(service.state()["report_matches_snapshot"])
            finally:
                service.pool.shutdown()

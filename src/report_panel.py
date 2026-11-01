"""Local home for Yahoo synchronization, forecast exports and the unchanged trade UI."""

import argparse
import hashlib
import json
import os
import secrets
import threading
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import trade_panel
from . import yahoo_browser_sync as bridge
from .forecast import build_local_forecast
from .report_excel import forecast_sheets, workbook_bytes
from .report_presentation import present_forecast

ROOT = Path(__file__).resolve().parents[1]


class ReportService:
    def __init__(self):
        self.token = secrets.token_urlsafe(24)
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.guard = threading.Lock()
        self.job = None
        self.report = None
        self.report_sync = None
        self.hash_cache = {}

    def _source_matches(self, report):
        sources = report.get("source_sha256") or {}
        if not sources:
            return False
        for name, expected in sources.items():
            path = (ROOT / name.replace("\\", "/")).resolve()
            if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
                return False
            stat = path.stat()
            version = (stat.st_mtime_ns, stat.st_size)
            cached = self.hash_cache.get(path)
            if not cached or cached[0] != version:
                cached = (version, hashlib.sha256(path.read_bytes()).hexdigest())
                self.hash_cache[path] = cached
            if cached[1] != expected:
                return False
        return True

    @staticmethod
    def _timestamp(report):
        try:
            stamp = datetime.fromisoformat(report["forecast_at"].replace("Z", "+00:00"))
            return (stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)).timestamp()
        except (KeyError, ValueError, TypeError):
            return float("-inf")

    def _read(self, relative):
        path = ROOT / relative
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def state(self):
        # Do not read partially written snapshots, or block UI polling while
        # the local refresh/notification pipeline owns the write lock.
        if not bridge.STATE_WRITE_LOCK.acquire(blocking=False):
            return {"busy": True, "pipeline": dict(bridge.LOCAL_REPORT_STATE)}
        try:
            state = self._read("data/processed/league_state.json")
            cached = self._read("reports/latest_forecast.json")
            with self.guard:
                if (
                    self.report is None
                    or self.report_sync != state.get("sync_id")
                    or (cached and self._timestamp(cached) > self._timestamp(self.report))
                ):
                    report, report_sync = cached or None, None
                else:
                    report, report_sync = self.report, self.report_sync
                computing = self.job is not None and not self.job.done()
                error = None
                if self.job is not None and self.job.done():
                    error = str(self.job.exception()) if self.job.exception() else None
            matches = bool(
                report
                and (
                    self._source_matches(report)
                    if report.get("source_sha256")
                    else report_sync and report_sync == state.get("sync_id")
                )
            )
            displayed = present_forecast(report, ROOT / "data/archive") if report else None
            if displayed and displayed["display_mode"] == "last_valid_forecast":
                matches = False
            receipt = self._read("reports/delivery_receipt.json")
            telegram = self._read("config/telegram.json")
            credentials = [
                os.environ.get("TELEGRAM_BOT_TOKEN") or telegram.get("bot_token"),
                os.environ.get("TELEGRAM_CHAT_ID") or telegram.get("chat_id"),
            ]
            telegram_configured = all(
                value
                and not any(
                    marker in str(value).upper() for marker in ("YOUR_", "BURAYA", "PLACEHOLDER")
                )
                for value in credentials
            )
            return {
                "busy": False,
                "pipeline": dict(bridge.LOCAL_REPORT_STATE),
                "captured": state.get("roster_captured_at", state.get("updated_at")),
                "sync_id": state.get("sync_id"),
                "teams": len(state.get("rosters", {})),
                "report": displayed,
                "computing": computing,
                "error": error,
                "report_matches_snapshot": matches,
                "delivery": receipt.get("status", "not_configured"),
                "telegram_configured": bool(telegram_configured),
            }
        finally:
            bridge.STATE_WRITE_LOCK.release()

    def compute(self):
        with self.guard:
            if self.job is not None and not self.job.done():
                return False
            self.job = self.pool.submit(self._compute)
            return True

    def _compute(self):
        with bridge.STATE_WRITE_LOCK:
            sync_id = self._read("data/processed/league_state.json").get("sync_id")
            result = build_local_forecast()
            with self.guard:
                self.report = json.loads(json.dumps(result, default=str))
                self.report_sync = sync_id

    def export(self):
        state = self.state()
        if state.get("busy") or state.get("computing"):
            raise ValueError("İşlem sürüyor; tamamlandıktan sonra tekrar indirin.")
        if not state.get("report"):
            raise ValueError("Önce bir rapor oluşturun.")
        sheets = forecast_sheets(state["report"])
        sheets["Kayıt durumu"] = [
            ["Alan", "Değer"],
            ["Güncel kadroyla eşleşme", state["report_matches_snapshot"]],
            ["Uyarı", "Rapor zamanı ve veri notları dikkate alınmalıdır."],
        ]
        return workbook_bytes(sheets)


def handler_for(service):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, data, status=200, kind="application/json; charset=utf-8"):
            payload = (
                data
                if isinstance(data, bytes)
                else json.dumps(data, ensure_ascii=False, default=str).encode()
            )
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            if kind == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                self.send_header(
                    "Content-Disposition", 'attachment; filename="nba-haftalik-rapor.xlsx"'
                )
            self.end_headers()
            self.wfile.write(payload)

        def authorized(self):
            return self.headers.get("X-Panel-Token") == service.token and self.headers.get(
                "Host", ""
            ).split(":")[0] in ("127.0.0.1", "localhost")

        def do_GET(self):
            if self.path == "/":
                page = Path(__file__).with_suffix(".html").read_text(encoding="utf-8")
                return self.reply(
                    page.replace("__TOKEN__", service.token).encode(),
                    kind="text/html; charset=utf-8",
                )
            if not self.authorized():
                return self.reply({"error": "Yetkisiz istek"}, 403)
            try:
                if self.path == "/state":
                    return self.reply(service.state())
                if self.path == "/export.xlsx":
                    return self.reply(
                        service.export(),
                        kind="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                return self.reply({"error": "Sayfa bulunamadı"}, 404)
            except Exception as exc:
                self.reply({"error": str(exc)}, 400)

        def do_POST(self):
            if not self.authorized():
                return self.reply({"error": "Yetkisiz istek"}, 403)
            if self.path != "/run":
                return self.reply({"error": "İşlem bulunamadı"}, 404)
            if bridge.LOCAL_REPORT_STATE.get("status") == "running":
                return self.reply(
                    {"error": "Yahoo güncellemesi sürüyor; tamamlanmasını bekleyin."}, 409
                )
            self.reply({"started": service.compute()})

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    service = ReportService()
    servers = []
    started = []
    try:
        # Keep the original trade handler and UI intact on their original port.
        for port, handler in [
            (8765, bridge.BrowserSyncHandler),
            (8766, trade_panel.Handler),
            (8767, handler_for(service)),
        ]:
            try:
                server = ThreadingHTTPServer(("127.0.0.1", port), handler)
            except OSError as exc:
                raise SystemExit(
                    f"{port} portu kullanımda. Önceden açtığınız Yahoo/takas panelini Ctrl+C ile kapatıp tekrar başlatın."
                ) from exc
            servers.append(server)
        for server in servers:
            threading.Thread(target=server.serve_forever, daemon=True).start()
            started.append(server)
        print("NBA Fantasy ana panel: http://127.0.0.1:8767", flush=True)
        print("Yahoo bağlantısı ve takas paneli hazır. Kapatmak için Ctrl+C.", flush=True)
        if not args.no_browser:
            webbrowser.open("http://127.0.0.1:8767")
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        for server in servers:
            if server in started:
                server.shutdown()
            server.server_close()
        service.pool.shutdown(wait=True)
        with bridge.STATE_WRITE_LOCK:
            pass  # Allow an in-flight snapshot/report write to finish.


if __name__ == "__main__":
    main()

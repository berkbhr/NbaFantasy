"""Local read-only trade panel. Run python -m src.trade_panel."""

import copy
import hashlib
import json
import math
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .trade_automation import _bundle, load_config, run_pending_monitor
from .trade_context import ROOT, load_context
from .trade_report import render_trade_monitor, render_trade_report
from .trade_search import effective_team_summaries, search_trades
from .trade_search_report import render_search_report
from .trades import evaluate_trade
from .yahoo_player_evidence import roster_observation

TOKEN = secrets.token_urlsafe(24)
POOL = ThreadPoolExecutor(max_workers=1)
JOBS = {}


def roster_version(now=None):
    now = now or datetime.now(timezone.utc)
    state = json.loads((ROOT / "data/processed/league_state.json").read_text(encoding="utf-8"))
    fields = (
        "sync_id",
        "rosters",
        "yahoo_roster_players",
        "il_slots",
        "team_names",
        "roster_captured_at",
        "yahoo_team_slots",
        "league_id",
    )
    sources = {}
    for name in (
        "injuries.db",
        "injuries.db-wal",
        "player_positions.parquet",
        "active_roster_2026_27.parquet",
    ):
        path = ROOT / "data/processed" / name
        try:
            sources[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        except FileNotFoundError:
            sources[name] = None
    freshness = [
        [
            str(team),
            item.get("yahoo_player_id"),
            item.get("name"),
            roster_observation(item, state, now)[1],
        ]
        for team, items in sorted(state.get("yahoo_roster_players", {}).items())
        for item in items
    ]
    return hashlib.sha256(
        json.dumps(
            {
                "roster": {k: state.get(k) for k in fields},
                "player_sources": sources,
                "freshness": freshness,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()


def impact_grade(delta, weeks):
    """An explanatory scale, never a calibrated probability or player valuation."""
    if not math.isfinite(delta) or weeks <= 0:
        raise ValueError("Invalid trade grade inputs")
    weekly = delta / weeks
    return {"score": round(max(0, min(10, 5 + 5 * weekly)), 1), "weekly_delta": weekly}


def preview_metrics(analysis):
    """Keep normal totals separate from sensitivity-adjusted decision differences."""
    teams = {}
    for team, summary in effective_team_summaries(analysis).items():
        total = summary["all_supplied_weeks"]
        conservative = min(total["delta"], summary["without_spillover_delta"])
        teams[team] = {
            "before": total["before"],
            "after": total["after"],
            "normal_delta": total["delta"],
            "without_spillover_delta": summary["without_spillover_delta"],
            "conservative_delta": conservative,
            "weeks": total["weeks"],
            "weekly_delta": conservative / total["weeks"],
            "grade": impact_grade(conservative, total["weeks"]),
        }
    return {
        "basis": analysis["decision"]["basis"],
        "our_team": str(analysis["proposal"]["our_team"]),
        "teams": teams,
    }


def panel_player_record(context, pid, yahoo_id):
    evidence = context.player_evidence.get(pid, {})
    player = context.engine.players[pid]
    return {
        "id": yahoo_id,
        "name": player.name,
        "positions": context.engine.pos_dict.get(pid, ""),
        "injury": player.injury_status,
        "display_positions": context.engine.pos_dict.get(pid, ""),
        "display_injury": player.injury_status,
        "injury_source": evidence.get("model_status_source", "model_baseline"),
        "positions_source": evidence.get("positions_source", "nba_fallback"),
        "injury_captured_at": evidence.get("model_status_observed_at"),
        "positions_captured_at": evidence.get("positions_observed_at"),
        "metadata_warning": "Yahoo kaydı yenilenmeli"
        if evidence.get("needs_yahoo_refresh")
        else "",
        "stashed": pid in context.engine.yahoo_already_stashed_ids,
        "il_eligible": pid in context.il_eligible_ids,
    }


def resolve_our_team(context):
    configured = str(load_config()["our_team"])
    if configured in context.rosters:
        return configured
    state_path = ROOT / "data/processed/league_state.json"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            berk_names = set(state.get("berk_roster_names", []))
            if berk_names:
                for tid, names in state.get("rosters", {}).items():
                    if len(set(names) & berk_names) >= 8:
                        return str(tid)
        except Exception:
            pass
    for tid, name in context.team_names.items():
        if "berk" in str(name).lower():
            return str(tid)
    return str(load_config().get("our_team", "7"))


def analyze(data):
    data = copy.deepcopy(data)
    as_of = datetime.now(timezone.utc)
    if data.get("roster_version") and data["roster_version"] != roster_version(now=as_of):
        raise ValueError("Kadro kaydı değişti. Kadroları yenileyip oyuncuları tekrar seç.")
    if data["mode"] == "pending":
        result = run_pending_monitor()
        for offer in result.get("offers", []):
            if offer.get("analysis_status") == "evaluated" and offer.get("analysis"):
                offer["preview_metrics"] = preview_metrics(offer["analysis"])
        return dict(report=render_trade_monitor(result), kind="pending", result=result)
    context = load_context(now=as_of)
    config = load_config()
    our_team_id = resolve_our_team(context)
    if data["mode"] == "search":
        if str(data.get("mine", our_team_id)) != our_team_id:
            raise ValueError("Fırsat taraması yalnız kendi takımın için çalışır.")
        data["mine"] = our_team_id
        config["our_team"] = our_team_id
    elif data["mode"] == "manual":
        if data.get("transfers"):
            participants = {str(m[k]) for m in data["transfers"] for k in ("from_team", "to_team")}
            if our_team_id in participants:
                data["mine"] = our_team_id
                data["other"] = next(t for t in sorted(participants) if t != our_team_id)
        elif str(data.get("other")) == our_team_id and str(data.get("mine")) != our_team_id:
            data["mine"], data["other"] = data["other"], data["mine"]
            data["give"], data["receive"] = data.get("receive", []), data.get("give", [])
        config["our_team"] = our_team_id
    if data.get("snapshot_id") and data["snapshot_id"] != context.sync_id:
        raise ValueError("Kadro sürümü değişti; panelde kadroları yenile.")
    offer = dict(
        our_team=data["mine"],
        other_team=data.get("other") if data.get("other") not in ("all", None) else None,
        give_yahoo_ids=data.get("give", []),
        receive_yahoo_ids=data.get("receive", []),
        effective_date=data.get("date") or None,
    )
    bundle, conditions = _bundle(context, config, offer)
    if data["mode"] == "search":
        bundle.update(copy.deepcopy(config["opportunity_analysis"]))
        supplied = data.get("search_options", {})
        if not isinstance(supplied, dict) or set(supplied) - {
            "min_gain_per_week",
            "max_partner_loss_per_week",
            "depth",
        }:
            raise ValueError("Geçersiz arama ayarı")
        for key in ("min_gain_per_week", "max_partner_loss_per_week"):
            if key in supplied:
                value = supplied[key]
                if (
                    type(value) not in (int, float)
                    or not math.isfinite(value)
                    or not 0 <= value <= 1
                ):
                    raise ValueError("Haftalık eşik 0–1 arasında olmalı")
                bundle.setdefault("search", {})[key] = value
        depth = supplied.get("depth", "standard")
        if depth not in ("standard", "wide"):
            raise ValueError("Bilinmeyen arama derinliği")
        if depth == "wide":
            bundle.setdefault("search", {}).update(shortlist_size=80, streaming_finalists=8)
        if data.get("other") and str(data["other"]) != "all":
            bundle.setdefault("search", {})["team_ids"] = [str(data["other"])]
            bundle["proposal"]["other_team"] = str(data["other"])
        else:
            bundle["proposal"]["other_team"] = None
        result = search_trades(context, bundle)
        weeks = len(bundle.get("weeks", [])) or bundle.get("fixture_horizon_weeks", 4)
        for c in result.get("finalists", []) + result.get("preliminary_candidates", []):
            if c.get("analysis"):
                c["preview_metrics"] = preview_metrics(c["analysis"])
            f = c.get("final") or c.get("screening") or {}
            ours_d = f.get("ours_conservative", f.get("ours", 0.0))
            partner_d = f.get("partner_conservative", f.get("partner", 0.0))
            c["grades"] = {
                "ours": impact_grade(ours_d, weeks),
                "partner": impact_grade(partner_d, weeks),
            }
        return dict(report=render_search_report(result), kind="search", result=result)
    if data["mode"] != "manual":
        raise ValueError("Bilinmeyen analiz türü")
    if data.get("transfers") is not None:
        bundle["proposal"]["transfers"] = data["transfers"]
        bundle["drop_yahoo_ids"] = data.get("drops", {})
    else:
        bundle["drop_yahoo_ids"] = data.get("drops", {})
    if "post_trade_il_yahoo_ids" in data:
        bundle["post_trade_il_yahoo_ids"] = data["post_trade_il_yahoo_ids"]
    result = evaluate_trade(context, bundle, complete_partner=True)
    result["conditions"].extend(conditions)
    result["preview_metrics"] = preview_metrics(result)
    result["impact_grades"] = {
        team: values["grade"] for team, values in result["preview_metrics"]["teams"].items()
    }
    report = render_trade_report(result)
    return dict(report=report, kind="manual", result=result)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, data, status=200, html=False):
        payload = data.encode() if html else json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8" if html else "application/json; charset=utf-8",
        )
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        page = (Path(__file__).with_name("trade_panel.html")).read_text(encoding="utf-8")
        if urlparse(self.path).path == "/":
            return self.reply(page.replace("__TOKEN__", TOKEN), html=True)
        if self.headers.get("X-Panel-Token") != TOKEN:
            return self.reply({"error": "Yetkisiz istek"}, 403)
        try:
            if self.path == "/version":
                return self.reply({"roster_version": roster_version()})
            if self.path == "/state":
                as_of = datetime.now(timezone.utc)
                version = roster_version(now=as_of)
                c = load_context(now=as_of)
                if version != roster_version():
                    raise ValueError("Yahoo senkronu sürüyor; kadroları tekrar yenile.")
                inverse = {pid: key for key, pid in c.yahoo_ids.items()}
                return self.reply(
                    dict(
                        captured=c.captured_at.isoformat(),
                        snapshot_id=c.sync_id,
                        roster_version=version,
                        our_team=resolve_our_team(c),
                        calendar=c.fantasy_calendar.get("status", "unavailable"),
                        player_source_audit=c.player_evidence_audit,
                        teams={
                            t: dict(
                                name=c.team_names.get(t, t),
                                players=[panel_player_record(c, p, inverse[p]) for p in roster],
                            )
                            for t, roster in c.rosters.items()
                        },
                    )
                )
            from urllib.parse import parse_qs

            job = JOBS[parse_qs(urlparse(self.path).query)["id"][0]]
            if not job.done():
                return self.reply({"done": False})
            return self.reply({"done": True, **job.result()})
        except Exception as exc:
            self.reply({"done": True, "error": str(exc)}, 400)

    def do_POST(self):
        if self.path != "/run" or self.headers.get("X-Panel-Token") != TOKEN:
            return self.reply({"error": "Yetkisiz istek"}, 403)
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 16384:
                raise ValueError("Geçersiz istek boyutu")
            if any(not j.done() for j in JOBS.values()):
                raise ValueError("Önce mevcut analizin tamamlanmasını bekle")
            JOBS.clear()
            key = secrets.token_urlsafe(12)
            JOBS[key] = POOL.submit(analyze, json.loads(self.rfile.read(length)))
            self.reply({"id": key})
        except Exception as exc:
            self.reply({"error": str(exc)}, 400)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8766), Handler)
    print("Takas paneli: http://127.0.0.1:8766 (kapatmak için Ctrl+C)")
    server.serve_forever()


if __name__ == "__main__":
    main()

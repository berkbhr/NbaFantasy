"""Read-only pending-offer monitoring; broad discovery is a separate opt-in job."""

import argparse
import copy
import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .fantasy_calendar import resolve_trade_calendar
from .trade_context import load_context
from .trade_market import assess_market
from .trade_packages import trade_packages
from .trade_projection_cache import TradeProjectionCache
from .trade_search import effective_gains
from .trades import evaluate_trade

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {
    "enabled": True,
    "our_team": "7",
    "offer_max_age_hours": 6,
    "max_offers_per_run": 3,
    "max_seconds": 90,
    "fixture_horizon_weeks": 4,
    "effective_date_policy": "next_full_week_scenario",
    "playoff_enabled": True,
    "playoff_simulations": 5000,
    "opportunity_cadence": "off",
    "analysis": {
        "rules": {"verified": False},
        "completion": {"enabled": True},
        "streaming": {"enabled": False},
    },
    "opportunity_analysis": {
        "completion": {"enabled": True, "adds_used_by_week": {}},
        "streaming": {"enabled": True, "adds_used_by_week": {}},
        "search": {"shortlist_size": 40, "streaming_finalists": 3, "reuse_projections": True},
    },
}


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=path.parent, suffix=".tmp", encoding="utf-8", delete=False
        ) as handle:
            name = handle.name
            json.dump(value, handle, ensure_ascii=False, indent=2, default=str)
            handle.write("\n")
        os.replace(name, path)
    finally:
        if name and Path(name).exists():
            Path(name).unlink()


def load_config(path=None):
    path = Path(path or ROOT / "config/trade_automation.json")
    supplied = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(supplied, dict):
        raise ValueError("Trade automation configuration must be an object")
    config = {**copy.deepcopy(DEFAULTS), **supplied}
    if os.environ.get("NBA_TRADE_SCAN_CADENCE"):
        config["opportunity_cadence"] = os.environ["NBA_TRADE_SCAN_CADENCE"]
    for key in ("enabled", "playoff_enabled"):
        if type(config[key]) is not bool:
            raise ValueError(f"{key} must be boolean")
    for key, low, high in (
        ("max_offers_per_run", 1, 20),
        ("fixture_horizon_weeks", 1, 18),
        ("playoff_simulations", 100, 100000),
    ):
        if type(config[key]) is not int or not low <= config[key] <= high:
            raise ValueError(f"Invalid {key}")
    for key in ("offer_max_age_hours", "max_seconds"):
        if type(config[key]) not in (int, float) or not 0 < config[key] <= 86400:
            raise ValueError(f"Invalid {key}")
    if config["effective_date_policy"] not in ("provider_only", "next_full_week_scenario"):
        raise ValueError("Unknown effective date policy")
    if config["opportunity_cadence"] not in ("off", "daily", "weekly"):
        raise ValueError("Unknown opportunity cadence")
    return config


def _semantic(value):
    if isinstance(value, dict):
        return {k: _semantic(v) for k, v in value.items() if k not in ("captured_at", "updated_at")}
    if isinstance(value, list):
        return [_semantic(v) for v in value]
    return value


def _source_check(state, now, max_age):
    snapshot = state.get("pending_offers_snapshot") or {}
    if state.get("yahoo_trade_audit", {}).get("offers") not in (None, "ready"):
        raise ValueError(
            "Son Yahoo teklif okuması doğrulanamadı; önceki liste güncelmiş gibi sunulmadı."
        )
    if (
        snapshot.get("source") not in ("yahoo_browser_league", "yahoo_api_league")
        or snapshot.get("complete") is not True
    ):
        raise ValueError("Yahoo bekleyen teklif sayfası tam ve doğrulanmış olarak alınmadı.")
    stamp = datetime.fromisoformat(snapshot["captured_at"].replace("Z", "+00:00"))
    if stamp.tzinfo is None or not -timedelta(minutes=5) <= now - stamp <= timedelta(hours=max_age):
        raise ValueError(
            "Bekleyen teklif kaydı eski veya zaman bilgisi geçersiz; Yahoo senkronunu yenileyin."
        )
    if str(snapshot.get("league_id")) != str(state.get("league_id")) or snapshot.get(
        "team_slots"
    ) != state.get("yahoo_team_slots"):
        raise ValueError("Teklif kaydı farklı lig/takım kimliklerine ait.")
    offers = snapshot.get("offers")
    if (
        not isinstance(offers, list)
        or len(offers) > 100
        or any(not isinstance(offer, dict) for offer in offers)
    ):
        raise ValueError("Bekleyen teklif listesi geçersiz veya sınırı aşıyor.")
    return snapshot


def _bundle(context, config, offer):
    bundle = copy.deepcopy(config.get("analysis", {}))
    bundle["proposal"] = {
        "our_team": str(offer["our_team"]),
        "other_team": str(offer["other_team"]) if offer.get("other_team") is not None else None,
        "give_yahoo_ids": list(offer["give_yahoo_ids"]),
        "receive_yahoo_ids": list(offer["receive_yahoo_ids"]),
        "snapshot_id": context.sync_id,
        "effective_date": offer.get("effective_date"),
    }
    bundle["fixture_horizon_weeks"] = config["fixture_horizon_weeks"]
    bundle = resolve_trade_calendar(context, bundle)
    conditions = []
    if not bundle["proposal"]["effective_date"]:
        if config["effective_date_policy"] == "provider_only":
            raise ValueError("Yahoo işlem tarihi yok; senaryo tarihi seçilmedi.")
        bundle["proposal"]["effective_date"] = bundle["weeks"][0]["start"]
        conditions.append(
            "Varsayımsal yürürlük: ilk tam gelecek hafta. Bu Yahoo işlem tarihi veya gerçekleşme garantisi değildir."
        )
    # Missing future add consumption remains missing. Never import benchmark zeros.
    bundle.setdefault("rules", {"verified": False})
    bundle.setdefault("completion", {"enabled": True})
    bundle.setdefault("streaming", {"enabled": False})
    return bundle, conditions


def _after_scenario(context, bundle, analysis):
    fixed = copy.deepcopy(bundle)
    inverse = {pid: yahoo for yahoo, pid in context.yahoo_ids.items()}
    fixed["drop_yahoo_ids"] = {
        team: [inverse[pid] for pid in ids]
        for team, ids in analysis["roster_actions"]["drops"].items()
    }
    scenarios, _ = trade_packages(
        context,
        fixed,
        [context.yahoo_ids[str(p)] for p in bundle["proposal"]["give_yahoo_ids"]],
        [context.yahoo_ids[str(p)] for p in bundle["proposal"]["receive_yahoo_ids"]],
    )
    if len(scenarios) != 1:
        raise ValueError("Playoff senaryosu için bırakma seçimi belirsiz")
    return scenarios[0]


def monitor_pending_offers(state, *, now=None, context=None, config=None, runtime=None):
    """Pure orchestration: no files, network, trade actions or notifications."""
    now = now or datetime.now(timezone.utc)
    config = {**copy.deepcopy(DEFAULTS), **(config or {})}
    runtime = copy.deepcopy(runtime or {"schema_version": 1, "cache": {}})
    if not isinstance(runtime, dict):
        runtime = {"schema_version": 1, "cache": {}}
    runtime.setdefault("cache", {})
    if not isinstance(runtime["cache"], dict):
        runtime["cache"] = {}
    report = {
        "status": "needs_data",
        "policy": "pending_only",
        "as_of": now.isoformat(),
        "offers": [],
        "reasons": [],
        "wide_scan_ran": False,
        "evaluated": 0,
        "cache_hits": 0,
    }
    if not config["enabled"]:
        report["status"] = "disabled"
        return report, runtime
    try:
        snapshot = _source_check(state, now, config["offer_max_age_hours"])
        report.update(source=snapshot["source"], captured_at=snapshot["captured_at"])
    except (ValueError, KeyError, TypeError) as exc:
        report["reasons"].append(str(exc))
        return report, runtime
    offers = snapshot["offers"]
    if not offers:
        report["status"] = "no_pending_offers"
        return report, runtime
    context = context or load_context(now=now)
    if abs((now - context.as_of).total_seconds()) > 5 or state.get("sync_id") != context.sync_id:
        raise ValueError("Offer monitor and model must use the same frozen snapshot/time")
    if (now - context.captured_at).total_seconds() > 86400:
        report["reasons"].append("Kadro kaydı 24 saatten eski; teklif kararı üretilmedi.")
        return report, runtime
    deadline = time.perf_counter() + config["max_seconds"]
    cache, moments = TradeProjectionCache(), {}
    seen = set()
    for offer in sorted(
        offers, key=lambda o: (o.get("direction") != "received", str(o.get("offer_id")))
    ):
        row = {
            "offer_id": str(offer.get("offer_id", "")),
            "status": offer.get("status"),
            "direction": offer.get("direction"),
            "analysis_status": "needs_data",
            "conditions": [],
            "errors": [],
        }
        report["offers"].append(row)
        try:
            if (
                not row["offer_id"]
                or row["offer_id"] in seen
                or offer.get("status") not in ("pending", "proposed", "accepted", "offered")
            ):
                raise ValueError("Teklif kimliği yinelenmiş veya bekleyen durumunda değil")
            seen.add(row["offer_id"])
            if str(offer.get("our_team")) != str(config["our_team"]):
                raise ValueError("Teklif yapılandırılmış takıma ait değil")
            bundle, row["conditions"] = _bundle(context, config, offer)
            proposal = bundle["proposal"]
            row["display"] = {
                "our_team": context.team_names.get(proposal["our_team"], proposal["our_team"]),
                "other_team": context.team_names.get(
                    proposal["other_team"], proposal["other_team"]
                ),
                "give": [
                    context.engine.players[context.yahoo_ids[str(p)]].name
                    for p in proposal["give_yahoo_ids"]
                ],
                "receive": [
                    context.engine.players[context.yahoo_ids[str(p)]].name
                    for p in proposal["receive_yahoo_ids"]
                ],
            }
            key = _hash(
                {
                    "offer": offer,
                    "bundle": _semantic(bundle),
                    "as_of_day": now.astimezone(ZoneInfo("America/New_York")).date().isoformat(),
                    "state": _semantic(
                        {
                            k: state.get(k)
                            for k in (
                                "rosters",
                                "yahoo_roster_players",
                                "il_slots",
                                "availability_snapshot",
                                "waivers",
                                "fantasy_calendar",
                                "team_names",
                            )
                        }
                    ),
                    "available_players": context.available_players,
                    "availability_audit": _semantic(context.availability_audit),
                    "sources": {
                        k: v
                        for k, v in context.source_hashes.items()
                        if not k.endswith("league_state.json")
                    },
                }
            )
            row["analysis_key"] = key
            cached = runtime["cache"].get(key)
            if cached:
                row.update(
                    analysis=copy.deepcopy(cached["analysis"]),
                    evaluated_at=cached["evaluated_at"],
                    cache_hit=True,
                )
                report["cache_hits"] += 1
            else:
                if (
                    report["evaluated"] >= config["max_offers_per_run"]
                    or time.perf_counter() >= deadline
                ):
                    row["analysis_status"] = "deferred"
                    continue
                analysis = evaluate_trade(
                    context,
                    bundle,
                    projection_cache=moments,
                    matchup_cache=cache,
                    complete_partner=True,
                    deadline=deadline,
                )
                row.update(analysis=analysis, evaluated_at=now.isoformat(), cache_hit=False)
                runtime["cache"][key] = {
                    "analysis": copy.deepcopy(analysis),
                    "evaluated_at": now.isoformat(),
                }
                report["evaluated"] += 1
            row["analysis_status"] = "evaluated"
            row["bilateral"] = effective_gains(row["analysis"])
            row["market"] = assess_market(context, bundle, proposal)
            if config["playoff_enabled"]:
                from .trade_playoffs import evaluate_playoff_impact

                if time.perf_counter() >= deadline:
                    row["playoff_impact"] = {
                        "status": "needs_data",
                        "reasons": ["Bu çalıştırmanın süre bütçesi doldu."],
                    }
                else:
                    row["playoff_impact"] = evaluate_playoff_impact(
                        context,
                        bundle,
                        state.get("playoff_snapshot") or {},
                        after=_after_scenario(context, bundle, row["analysis"]),
                        simulations=config["playoff_simulations"],
                        matchup_cache=cache,
                        deadline=deadline,
                    )
        except TimeoutError as exc:
            row.update(analysis_status="deferred", errors=[str(exc)])
        except (ValueError, KeyError, TypeError) as exc:
            row["analysis_status"] = "needs_data"
            row["errors"].append(str(exc))
    runtime["cache"] = dict(list(runtime["cache"].items())[-20:])
    report["status"] = (
        "analyzed"
        if all(r["analysis_status"] == "evaluated" for r in report["offers"])
        else "partial"
    )
    return report, runtime


def run_pending_monitor(now=None, *, root=None):
    root = Path(root or ROOT)
    state = json.loads((root / "data/processed/league_state.json").read_text(encoding="utf-8"))
    config = load_config(root / "config/trade_automation.json")
    path = root / "data/processed/trade_runtime.json"
    try:
        runtime = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        runtime = {}
    report, runtime = monitor_pending_offers(state, now=now, config=config, runtime=runtime)
    if report["evaluated"]:
        atomic_json(path, runtime)
    return report


def opportunity_due(cadence, last, now):
    """Calendar periods avoid skipping alternate days when a scan ends late."""
    if cadence == "off":
        return False
    if cadence not in ("daily", "weekly"):
        raise ValueError("Unknown opportunity cadence")
    if last is None:
        return True
    if last.tzinfo is None or now.tzinfo is None or last > now:
        raise ValueError("Opportunity timestamps must be valid timezone-aware observations")
    zone = ZoneInfo("Europe/Berlin")
    before, current = last.astimezone(zone), now.astimezone(zone)
    return (
        current.date() > before.date()
        if cadence == "daily"
        else current.isocalendar()[:2] > before.isocalendar()[:2]
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("pending", "opportunities"), default="pending")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/trade_search/stage5")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Explicit manual opportunity scan even when periodic scanning is off",
    )
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    if args.mode == "pending":
        from .trade_report import render_trade_monitor

        result = run_pending_monitor(now)
        atomic_json(args.output.with_suffix(".json"), result)
        args.output.with_suffix(".md").write_text(render_trade_monitor(result), encoding="utf-8")
    else:
        from .trade_search import search_trades
        from .trade_search_report import render_search_report

        config = load_config()
        cadence = config["opportunity_cadence"]
        path = ROOT / "data/processed/trade_scan_state.json"
        previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        last = (
            datetime.fromisoformat(previous["completed_at"])
            if previous.get("completed_at")
            else None
        )
        due = opportunity_due(cadence, last, now)
        if not due and not args.force:
            print("Broad trade scan skipped: disabled or cadence not due.")
            return
        context = load_context(now=now)
        data = copy.deepcopy(config["analysis"])
        data.update(copy.deepcopy(config["opportunity_analysis"]))
        data.update(
            proposal={"our_team": config["our_team"], "snapshot_id": context.sync_id},
            fixture_horizon_weeks=config["fixture_horizon_weeks"],
        )
        data = resolve_trade_calendar(context, data)
        data["proposal"]["effective_date"] = data["weeks"][0]["start"]
        data["scenario_note"] = (
            "İlk tam gelecek hafta yürürlük senaryosu; Yahoo işlem tarihi değildir. Gelecek hamle tüketimleri yalnız açık girdilerden alınır."
        )
        result = search_trades(context, data)
        atomic_json(args.output.with_suffix(".json"), result)
        args.output.with_suffix(".md").write_text(render_search_report(result), encoding="utf-8")
        atomic_json(
            path,
            {
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "sync_id": context.sync_id,
                "input_sha256": result["input_sha256"],
            },
        )
    print(f"Saved read-only trade report: {args.output.with_suffix('.md')}")


if __name__ == "__main__":
    main()

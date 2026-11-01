"""Read-only trade context sharing the main model's confirmed fantasy fixtures."""

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .draft_data import resolve_rosters
from .fantasy_calendar import calendar_view
from .live_draft_assistant import LiveDraftAssistant
from .matchup_engine import MAX_ROSTER_SIZE, REQUIRED_SLOTS, MatchupEngine
from .ownership import free_agent_ids
from .settings import load_settings
from .waivers import waiver_constraints
from .yahoo_player_evidence import apply_yahoo_roster_evidence
from .yahoo_player_evidence import verified_yahoo_positions as verified_yahoo_positions

ROOT = Path(__file__).resolve().parents[1]


def day(value):
    result = pd.Timestamp(value)
    if pd.isna(result) or result.tzinfo is not None or result != result.normalize():
        raise ValueError("Dates must be timezone-free calendar dates (YYYY-MM-DD)")
    return result


@dataclass
class TradeContext:
    engine: MatchupEngine
    rosters: dict
    yahoo_ids: dict
    as_of: datetime
    sync_id: str
    captured_at: datetime
    warnings: list
    source_hashes: dict
    team_names: dict = field(default_factory=dict)
    available_players: dict = field(default_factory=dict)
    availability_audit: dict = field(default_factory=dict)
    protected_drop_ids: set = field(default_factory=set)
    il_eligible_ids: set = field(default_factory=set)
    weekly_add_limit: int = 3
    fantasy_calendar: dict = field(default_factory=dict)
    league_id: str = ""
    team_slots: dict = field(default_factory=dict)
    verified_position_ids: set = field(default_factory=set)
    player_evidence: dict = field(default_factory=dict)
    player_evidence_audit: dict = field(default_factory=dict)


def provider_il_eligible_ids(assistant, state, stashes, observations=None):
    """Only explicit Yahoo evidence can authorize a new IL placement."""
    eligible = set(stashes)
    if observations is not None:
        eligible.update(
            pid
            for pid, item in observations.items()
            if item.get("yahoo_status_verified") and item.get("yahoo_status") == "OUT"
        )
        return eligible
    for items in state.get("yahoo_roster_players", {}).values():
        for item in items:
            if str(item.get("status", "")).upper() in ("O", "INJ", "OUT", "IL", "IL+"):
                pid = assistant.resolve_player_id(item.get("name", ""), only_available=False)
                if pid is not None and pid in assistant.players:
                    eligible.add(pid)
    return eligible


def validate_calendar(bundle, teams, as_of):
    """Only complete, future fantasy weeks; never invent opponent fixtures."""
    today = pd.Timestamp(as_of).tz_convert("America/New_York").tz_localize(None).normalize()
    weeks = bundle.get("weeks", [])
    if not weeks:
        raise ValueError("At least one real future fantasy week is required")
    previous_end = None
    for week in weeks:
        start, end = day(week["start"]), day(week["end"])
        if start <= today or end < start:
            raise ValueError("Stage 1 requires future weeks; partial/live weeks are unsupported")
        if previous_end is not None and start != previous_end + pd.Timedelta(days=1):
            raise ValueError("Fantasy weeks must be consecutive and ordered")
        seen = []
        for home, away in week["fixtures"]:
            home, away = str(home), str(away)
            if home == away or home not in teams or away not in teams:
                raise ValueError("Fixture must contain distinct known canonical team IDs")
            seen.extend((home, away))
        if len(seen) != len(set(seen)) or set(seen) != set(teams):
            raise ValueError("Each fantasy week must cover every team exactly once")
        previous_end = end
    for period in bundle.get("playoff_periods", []):
        if day(period["end"]) < day(period["start"]):
            raise ValueError("Invalid playoff period")
    return weeks


def load_context(now=None, state_path=None):
    """Load current caches without APIs, notifications, draft fallback or DB writes."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Analysis timestamp must include timezone")
    state_path = Path(state_path or ROOT / "data/processed/league_state.json")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if not state.get("live_synced") or not state.get("sync_id"):
        raise ValueError("A live Yahoo roster snapshot is required; no draft fallback")
    captured = datetime.fromisoformat(
        state.get("roster_captured_at", state["updated_at"]).replace("Z", "+00:00")
    )
    if captured.tzinfo is None or captured > now:
        raise ValueError("Invalid or future roster timestamp")
    # Current cache loading is not a historical replay API.
    if state_path.stat().st_mtime > now.timestamp() + 5:
        raise ValueError("Historical analysis requires archived inputs, not current caches")
    assistant = LiveDraftAssistant(use_live_injuries=False)
    paths = [state_path]
    logs_path = ROOT / "data/raw/player_logs_2026_27.parquet"
    if logs_path.exists():
        logs = pd.read_parquet(logs_path)
        cutoff = pd.Timestamp(now).tz_convert("America/New_York").tz_localize(None).normalize()
        assistant.apply_current_season_logs(logs[pd.to_datetime(logs.GAME_DATE) < cutoff])
        paths.append(logs_path)
    db = ROOT / "data/processed/injuries.db"
    if db.exists():
        with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute("SELECT * FROM active_injuries"):
                item = dict(row)
                pid = assistant.resolve_player_id(item.get("player_name", ""), only_available=False)
                if pid in assistant.players:
                    assistant.players[pid].update_injury_status(
                        item["status"],
                        desc=item.get("injury_desc", ""),
                        is_b2b_rest=bool(item.get("is_b2b_rest")),
                        expected_return=item.get("expected_return"),
                        report_date=item.get("updated_at"),
                    )
        paths.append(db)
    raw_rosters = state.get("rosters", {})
    if len(raw_rosters) != 14:
        raise ValueError("All 14 live rosters are required")
    rosters = {
        str(k): v
        for k, v in resolve_rosters(assistant, {int(k): v for k, v in raw_rosters.items()}).items()
    }
    source_evidence = apply_yahoo_roster_evidence(assistant, state, now)
    yahoo_ids, positions, stashes = {}, source_evidence["positions"], set()
    verified_positions = source_evidence["verified_position_ids"]
    for team, roster in rosters.items():
        evidence = state.get("yahoo_roster_players", {}).get(team, [])
        matched = set()
        for item in evidence:
            pid = assistant.resolve_player_id(item["name"], only_available=False)
            yahoo_id = str(item.get("yahoo_player_id", ""))
            if (
                pid not in roster
                or pid in matched
                or not yahoo_id.isdigit()
                or yahoo_id in yahoo_ids
            ):
                raise ValueError("Incomplete, duplicate or conflicting Yahoo player identity")
            yahoo_ids[yahoo_id] = pid
            matched.add(pid)
            if item.get("selected_position") in ("IL", "IL+"):
                stashes.add(pid)
        if matched != set(roster):
            raise ValueError("Each roster player needs explicit Yahoo identity evidence")
        for name in state.get("il_slots", {}).get(team, []):
            pid = assistant.resolve_player_id(name, only_available=False)
            if pid not in roster:
                raise ValueError("IL player missing from roster")
            stashes.add(pid)
        if len(set(roster) - stashes) > MAX_ROSTER_SIZE:
            raise ValueError("Snapshot exceeds supported active/bench capacity")
    engine = MatchupEngine(
        assistant.players,
        assistant.schedule_df,
        pd.DataFrame([{"PLAYER_ID": p, "POSITION": pos} for p, pos in positions.items()]),
        team_map=dict(assistant.engine.team_map),
        yahoo_il_eligible_ids=set(),
        use_positional_depth_and_injury_boost=True,
    )
    engine.yahoo_already_stashed_ids = stashes
    engine.rotation_pos_dict = dict(assistant.pos_dict)
    paths += [
        ROOT / "data/processed/schedule_2026_27.parquet",
        ROOT / "data/processed/player_positions.parquet",
        ROOT / "data/processed/active_roster_2026_27.parquet",
        ROOT / "config/league.json",
    ]
    paths += list((ROOT / "src").glob("*.py"))
    paths += list((ROOT / "config").glob("*policy.json"))
    paths += list((ROOT / "data/raw").glob("player_logs_202[45]_*.parquet"))
    paths += list((ROOT / "data/raw").glob("preseason_logs_2026_27.parquet"))
    hashes = {
        str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for p in paths
        if p.exists()
    }
    hashes["resolved_yahoo_player_evidence"] = source_evidence["sha256"]
    warnings = [
        "Current player roles projected forward; long-range estimates are conditional.",
    ]
    if not source_evidence["per_player_timestamps_complete"]:
        warnings.append(
            "Per-team capture times are unavailable; merged roster freshness is not proven."
        )
    warnings.extend(source_evidence["warnings"])
    if (now - captured).total_seconds() > 86400:
        warnings.append("Roster snapshot is older than 24 hours.")
    from .yahoo_trade_sync import resolved_team_names

    team_names = {
        team: name for team, name in resolved_team_names(state).items() if team in rosters
    }
    candidates, audit = free_agent_ids(assistant, state, rosters, now=now)
    if audit.get("source") == "yahoo_available_players":
        warnings.append(
            f"FA havuzu: {audit['observed_players']} gözlenen oyuncu "
            f"({'tam tarama' if audit['scan_complete'] else 'kısmi tarama'}; "
            f"{audit.get('pages_scanned') or 0} sayfa). "
            "Kısmi havuz dışında anlamlı adaylar bulunabilir."
        )
    audit.update(
        updated_at=state.get("availability_snapshot", {}).get("updated_at"),
        sync_id=state.get("availability_snapshot", {}).get("sync_id"),
    )
    waivers = waiver_constraints(assistant, state, now)
    available = {}
    for item in state.get("availability_snapshot", {}).get("players", []):
        pid = assistant.resolve_player_id(item.get("name", ""), only_available=False)
        yahoo_id = str(item.get("yahoo_player_id", ""))
        if pid not in candidates or not yahoo_id.isdigit():
            continue
        if yahoo_id in yahoo_ids and yahoo_ids[yahoo_id] != pid:
            raise ValueError("Conflicting available-player Yahoo identity")
        if pid in available and available[pid]["yahoo_player_id"] != yahoo_id:
            raise ValueError("Available player resolved from conflicting Yahoo identities")
        yahoo_ids[yahoo_id] = pid
        available[pid] = {
            "status": item["status"],
            "waiver": waivers.get(pid),
            "yahoo_player_id": yahoo_id,
        }
    settings = load_settings()
    protected = {
        assistant.resolve_player_id(name, only_available=False)
        for name in settings.protected_player_names
    } - {None}
    il_eligible = provider_il_eligible_ids(assistant, state, stashes, source_evidence["players"])
    result = TradeContext(
        engine, rosters, yahoo_ids, now, state["sync_id"], captured, warnings, hashes, team_names
    )
    result.available_players, result.availability_audit = available, audit
    result.protected_drop_ids, result.il_eligible_ids = protected, il_eligible
    result.weekly_add_limit = settings.max_weekly_adds
    result.fantasy_calendar = calendar_view(state, now)
    result.league_id = str(state.get("league_id", ""))
    result.team_slots = dict(state.get("yahoo_team_slots", {}))
    result.verified_position_ids = verified_positions
    result.player_evidence = source_evidence["players"]
    result.player_evidence_audit = {
        k: v
        for k, v in source_evidence.items()
        if k not in ("positions", "players", "verified_position_ids")
    }
    return result


def validate_rules(bundle):
    rules = bundle.get("rules", {})
    if rules.get("verified"):
        required = {
            "active_slots",
            "roster_capacity",
            "il_capacity",
            "review_days",
            "trade_deadline",
        }
        if not required <= rules.keys():
            raise ValueError(
                "Confirmed rules require explicit slots, capacities, review and deadline"
            )
        if type(rules["review_days"]) is not int or rules["review_days"] < 0:
            raise ValueError("Confirmed rules need a known, nonnegative review_days value")
    if rules.get("active_slots", REQUIRED_SLOTS) != REQUIRED_SLOTS:
        raise ValueError("This version supports only the current league's ten active slots")
    if rules.get("roster_capacity", 13) != 13 or rules.get("il_capacity", 2) != 2:
        raise ValueError("This version supports 13 active/bench and two IL slots")
    for name in ("max_weekly_adds", "trade_add_cost"):
        if name in rules and (type(rules[name]) is not int or rules[name] < 0):
            raise ValueError(f"{name} must be a nonnegative integer")
    return rules

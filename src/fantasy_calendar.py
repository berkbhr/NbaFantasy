"""One dated, provider-identified regular-season fantasy calendar for all analyses."""

import copy
from datetime import datetime, timezone

import pandas as pd

SOURCES = {"yahoo_browser_schedule", "yahoo_api_scoreboard"}
MAX_AGE_DAYS = 7


def _date(value):
    day = pd.Timestamp(value)
    if pd.isna(day) or day.tzinfo is not None or day != day.normalize():
        raise ValueError("Fantasy dates must be explicit YYYY-MM-DD calendar dates")
    return day


def _time(value):
    stamp = pd.Timestamp(value)
    if pd.isna(stamp) or stamp.tzinfo is None:
        raise ValueError("Fantasy capture time must include a timezone")
    return stamp


def validate_week(week, teams):
    """Validate full league coverage, including reciprocal team-schedule evidence."""
    if not isinstance(week, dict) or not isinstance(week.get("fixtures"), list):
        raise ValueError("Fantasy week must contain a fixture list")
    number = week.get("week")
    if type(number) is not int or not 1 <= number <= 60:
        raise ValueError("Invalid fantasy week number")
    start, end = _date(week["start"]), _date(week["end"])
    if not 0 <= (end - start).days <= 20:
        raise ValueError("Invalid fantasy scoring period")
    seen = []
    for pair in week["fixtures"]:
        if len(pair) != 2:
            raise ValueError("A fixture needs two teams")
        a, b = map(str, pair)
        if a == b or a not in teams or b not in teams:
            raise ValueError("Fixture contains an unknown or identical team")
        seen.extend((a, b))
    if len(seen) != len(set(seen)) or set(seen) != set(teams):
        raise ValueError("Each fantasy week must cover every league team exactly once")


def _identity(calendar, league_id, slots):
    if not isinstance(calendar, dict) or not isinstance(calendar.get("weeks"), list):
        raise ValueError("Fantasy calendar must contain a week list")
    if (
        calendar.get("schema_version") != 1
        or calendar.get("source") not in SOURCES
        or calendar.get("league_id") != str(league_id)
        or calendar.get("team_slots") != slots
    ):
        raise ValueError("Fantasy calendar league/team identity does not match the roster snapshot")
    season = calendar.get("season", "")
    try:
        year, suffix = season.split("_")
        year = int(year)
        if suffix != str(year + 1)[-2:]:
            raise ValueError
    except (ValueError, AttributeError):
        raise ValueError("Fantasy calendar needs an explicit Yahoo season, e.g. 2026_27") from None
    cutoff = calendar.get("regular_season_end_week")
    if type(cutoff) is not int or not 1 <= cutoff <= 60:
        raise ValueError("Yahoo regular-season boundary is required; playoff opponents are unknown")
    return year, cutoff


def validate_calendar_source(calendar, league_id, slots):
    year, cutoff = _identity(calendar, league_id, slots)
    teams = set(slots.values())
    previous, seen = None, set()
    for week in calendar.get("weeks", []):
        validate_week(week, teams)
        if week["week"] in seen or week["week"] > cutoff:
            raise ValueError("Duplicate or postseason fantasy week")
        seen.add(week["week"])
        if (
            not pd.Timestamp(year, 7, 1)
            <= _date(week["start"])
            <= _date(week["end"])
            < pd.Timestamp(year + 1, 7, 1)
        ):
            raise ValueError("Fantasy dates disagree with the captured season")
        _time(week["captured_at"])
        if previous and (
            week["week"] <= previous["week"]
            or _date(week["start"]) <= _date(previous["end"])
            or (
                week["week"] == previous["week"] + 1
                and _date(week["start"]) != _date(previous["end"]) + pd.Timedelta(days=1)
            )
        ):
            raise ValueError("Fantasy weeks overlap or consecutive weeks have inconsistent dates")
        previous = week
    return calendar


def merge_capture(prior, capture, league_id, slots, captured_at):
    """A failed/partial fetch never refreshes timestamps on previously observed weeks.

    Browser/API inputs contain Yahoo team IDs; persistence uses canonical IDs and
    the exact mapping used to translate them. No draft/name matching is done here.
    """
    slots = {str(k): str(v) for k, v in slots.items()}
    if not slots or len(set(slots.values())) != len(slots):
        raise ValueError("A complete, unique Yahoo team mapping is required")
    saved = None
    if prior:
        try:
            saved = copy.deepcopy(validate_calendar_source(prior, league_id, slots))
        except (ValueError, KeyError, TypeError):
            pass
    audit = {"received_weeks": 0, "accepted_weeks": 0, "errors": []}
    if not capture:
        audit["errors"].append(
            "No new Yahoo fantasy schedule capture; earlier timestamps preserved"
        )
        return saved, audit
    if not isinstance(capture, dict) or not isinstance(capture.get("weeks", []), list):
        audit["errors"].append("Malformed Yahoo calendar capture")
        return saved, audit
    audit["errors"].extend(str(e) for e in capture.get("errors", []))
    base = {
        "schema_version": 1,
        "source": capture.get("source"),
        "league_id": str(capture.get("league_id")),
        "season": capture.get("season"),
        "regular_season_end_week": capture.get("regular_season_end_week"),
        "team_slots": slots,
        "weeks": [],
    }
    try:
        _identity(base, league_id, slots)
        _time(captured_at)
    except (ValueError, TypeError) as exc:
        audit["errors"].append(str(exc))
        return saved, audit
    if saved and saved["season"] != base["season"]:
        saved = None
    rows = {
        w["week"]: copy.deepcopy(w)
        for w in (saved or {}).get("weeks", [])
        if w["week"] <= base["regular_season_end_week"]
    }
    received = set()
    for raw in capture.get("weeks", []):
        audit["received_weeks"] += 1
        try:
            if not isinstance(raw, dict):
                raise ValueError("Malformed fantasy week")
            row = copy.deepcopy(raw)
            if row.get("week") in received:
                raise ValueError("Duplicate week in Yahoo capture")
            received.add(row.get("week"))
            if row.get("week", 0) > base["regular_season_end_week"]:
                continue  # Do not guess future playoff brackets.
            row["fixtures"] = [[slots[str(a)], slots[str(b)]] for a, b in row["fixtures"]]
            row["captured_at"] = str(captured_at)
            row["source"] = base["source"]
            validate_week(row, set(slots.values()))
            candidate = {
                **base,
                "weeks": sorted(
                    [v for k, v in rows.items() if k != row["week"]] + [row],
                    key=lambda w: w["week"],
                ),
            }
            validate_calendar_source(candidate, league_id, slots)
            rows[row["week"]] = row
            audit["accepted_weeks"] += 1
        except (ValueError, KeyError, TypeError) as exc:
            audit["errors"].append(
                f"Week {raw.get('week') if isinstance(raw, dict) else '?'}: {exc}"
            )
    if not audit["accepted_weeks"]:
        return saved, audit
    base["weeks"] = sorted(rows.values(), key=lambda w: w["week"])
    return base, audit


def calendar_view(state, as_of=None, horizon=None):
    """Return only a contiguous, fresh, real future schedule; no all-league fallback."""
    now = _time(as_of or datetime.now(timezone.utc))
    today = now.tz_convert("America/New_York").tz_localize(None).normalize()
    result = {"status": "unavailable", "reason": None, "weeks": [], "missing_weeks": []}
    calendar = state.get("fantasy_calendar")
    if not calendar:
        return {**result, "reason": "Yahoo future fantasy fixtures have not been captured"}
    try:
        validate_calendar_source(
            calendar, state.get("league_id"), state.get("yahoo_team_slots", {})
        )
        if horizon is not None and (type(horizon) is not int or horizon < 1):
            raise ValueError("Future fixture horizon must be a positive integer or null")
        rows = calendar["weeks"]
        for row in rows:
            if _time(row["captured_at"]) > now:
                raise ValueError("Fantasy capture is later than the analysis timestamp")
        anchor = next((w for w in rows if _date(w["start"]) <= today <= _date(w["end"])), None)
        if anchor is None:
            raise ValueError(
                "Current Yahoo scoring period is missing; next week cannot be inferred"
            )
        if (now - _time(anchor["captured_at"])).total_seconds() > MAX_AGE_DAYS * 86400:
            raise ValueError("Current Yahoo scoring period is stale; refresh fantasy schedule")
        cutoff = calendar["regular_season_end_week"]
        expected = list(range(anchor["week"] + 1, cutoff + 1))
        if horizon is not None:
            expected = expected[:horizon]
        by_number = {w["week"]: w for w in rows}
        previous = anchor
        for number in expected:
            row = by_number.get(number)
            if (
                row is None
                or (now - _time(row["captured_at"])).total_seconds() > MAX_AGE_DAYS * 86400
            ):
                result["missing_weeks"].append(number)
                continue
            if result["missing_weeks"] or _date(row["start"]) != _date(
                previous["end"]
            ) + pd.Timedelta(days=1):
                result["missing_weeks"].append(number)
                continue
            result["weeks"].append(copy.deepcopy(row))
            previous = row
        result.update(
            status="partial"
            if result["missing_weeks"]
            else "ready"
            if expected
            else "season_complete",
            reason="Missing/stale weeks; only the contiguous confirmed prefix is usable"
            if result["missing_weeks"]
            else None,
            source=calendar["source"],
            sources=sorted({w.get("source", calendar["source"]) for w in result["weeks"]}),
            season=calendar["season"],
            current_week=copy.deepcopy(anchor),
            regular_season_end_week=cutoff,
            complete_remaining_season=not result["missing_weeks"]
            and len(expected) == cutoff - anchor["week"],
        )
    except (ValueError, KeyError, TypeError) as exc:
        result.update(status="unavailable", reason=str(exc), weeks=[])
    return result


def resolve_trade_calendar(context, bundle):
    """Explicit manual calendars remain possible; the default uses the main-model source."""
    bundle = copy.deepcopy(bundle)
    if bundle.get("weeks"):
        bundle.setdefault("calendar_source", {"source": "manual_input"})
        return bundle
    view = copy.deepcopy(context.fantasy_calendar)
    horizon = bundle.get("fixture_horizon_weeks", 4)
    if type(horizon) is not int or not 1 <= horizon <= 60:
        raise ValueError("fixture_horizon_weeks must be between 1 and 60")
    if not view.get("weeks"):
        raise ValueError(view.get("reason") or "No confirmed future fantasy fixtures available")
    effective = bundle.get("proposal", {}).get("effective_date")
    if effective:
        view["weeks"] = [week for week in view["weeks"] if _date(week["start"]) >= _date(effective)]
        if not view["weeks"]:
            raise ValueError("No complete fantasy week remains after the trade effective date")
    if len(view["weeks"]) < horizon and not view.get("complete_remaining_season"):
        raise ValueError("Shared fantasy schedule does not cover the requested trade horizon")
    bundle["weeks"] = view["weeks"][:horizon]
    bundle["calendar_verified"] = True
    bundle["calendar_source"] = {
        k: v for k, v in view.items() if k not in ("weeks", "current_week")
    }
    if view.get("complete_remaining_season"):
        if not bundle.get("regular_season_end"):
            bundle["regular_season_end"] = view["weeks"][-1]["end"]
    return bundle

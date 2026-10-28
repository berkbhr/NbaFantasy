"""Preserve Yahoo claim restrictions; an unknown clearance date is not free agency."""

import re
from datetime import date

import pandas as pd


def normalize_waiver(value, captured_at):
    display = str(
        value.get("display", value.get("date", "Waiver")) if isinstance(value, dict) else value
    )
    raw = (value.get("date") or value.get("display")) if isinstance(value, dict) else value
    today = pd.Timestamp(captured_at).tz_convert("America/New_York").date()
    clear = None
    match = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", str(raw or ""))
    try:
        if match:
            clear = date(*map(int, match.groups()))
        else:
            match = re.search(r"\b(\d{1,2})[/.](\d{1,2})(?:[/.](\d{4}))?\b", str(raw or ""))
            if match:
                a, b = int(match[1]), int(match[2])
                # 30/10 and 10/30 are unambiguous. Do not guess 03/04's locale.
                day, month = (a, b) if a > 12 else ((b, a) if b > 12 else (None, None))
                if day is not None:
                    year = int(match[3]) if match[3] else today.year
                    clear = date(year, month, day)
                    if not match[3] and today.month == 12 and month == 1:
                        clear = date(year + 1, month, day)
    except ValueError:
        clear = None
    return {"date": clear.isoformat() if clear else None, "display": display}


def waiver_constraints(assistant, state, captured_at):
    result = {}
    raw = state.get("waivers", {})
    for name, value in raw.items():
        pid = assistant.resolve_player_id(name, only_available=False)
        if pid is not None:
            result[pid] = normalize_waiver(value, captured_at)
    for item in state.get("availability_snapshot", {}).get("players", []):
        pid = assistant.resolve_player_id(item.get("name", ""), only_available=False)
        if pid is None:
            continue
        if item.get("status") == "W":
            result[pid] = normalize_waiver(
                item.get("waiver") or raw.get(item["name"], "Waiver"), captured_at
            )
        elif item.get("status") == "FA":
            result.pop(pid, None)  # Current positive FA evidence supersedes an old claim date.
    return result

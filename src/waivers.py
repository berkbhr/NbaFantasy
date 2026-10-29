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
            else:
                months = {
                    name: i + 1
                    for i, name in enumerate(
                        (
                            "jan",
                            "feb",
                            "mar",
                            "apr",
                            "may",
                            "jun",
                            "jul",
                            "aug",
                            "sep",
                            "oct",
                            "nov",
                            "dec",
                        )
                    )
                }
                month_pattern = r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
                named = re.search(
                    r"\b(" + month_pattern + r")\.?\s*(\d{1,2})(?:,?\s+(20\d{2}))?\b",
                    str(raw or ""),
                    re.I,
                )
                reverse = re.search(
                    r"\b(\d{1,2})\s+(" + month_pattern + r")(?:\s+(20\d{2}))?\b",
                    str(raw or ""),
                    re.I,
                )
                if named or reverse:
                    token = named[1] if named else reverse[2]
                    month = months.get(token[:3].lower())
                    day = int(named[2] if named else reverse[1])
                    year_text = named[3] if named else reverse[3]
                    year = int(year_text) if year_text else today.year
                    if month:
                        if not year_text and today.month == 12 and month == 1:
                            year += 1
                        clear = date(year, month, day)
    except ValueError:
        clear = None
    return {"date": clear.isoformat() if clear else None, "display": display}


def waiver_constraints(assistant, state, captured_at):
    today = pd.Timestamp(captured_at).tz_convert("America/New_York").date().isoformat()
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
            previous = result.get(pid)
            strong_fa = item.get("status_evidence") == "free_agent_filter"
            pending = previous is not None and (not previous["date"] or previous["date"] > today)
            if pending and not strong_fa:
                # Yahoo's Add action is also used for waiver claims. A weak
                # FA classification must not erase a known future clear date.
                previous["evidence_conflict"] = (
                    "FA classification conflicts with pending waiver; clearance preserved"
                )
            else:
                result.pop(pid, None)
    return result

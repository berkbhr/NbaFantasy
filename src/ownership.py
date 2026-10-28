"""Positive Yahoo availability evidence; missing roster rows never imply free agency."""

from datetime import datetime, timedelta, timezone


def free_agent_ids(assistant, state, rosters, now=None):
    """Return verified available IDs and an audit, even when the page scan is partial.

    A roster with 13 rows may still omit an IL/IL+ or active player. Neither
    roster length nor draft absence nor a historical drop proves availability.
    """
    now = now or datetime.now(timezone.utc)
    snapshot = state.get("availability_snapshot", {})
    audit = {
        "source": snapshot.get("source"),
        "verified_candidates": 0,
        "reason": None,
        "scan_complete": bool(snapshot.get("scan_complete")),
    }
    try:
        stamp = datetime.fromisoformat(snapshot["updated_at"].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("Availability timestamp must be timezone-aware")
        age = now - stamp
        valid = snapshot.get("source") == "yahoo_available_players" and -timedelta(
            minutes=5
        ) <= age <= timedelta(hours=24)
    except (KeyError, TypeError, ValueError, AttributeError):
        valid = False
    if not valid:
        audit["reason"] = (
            "Fresh Yahoo free-agent/waiver evidence unavailable; add recommendations withheld. "
            "Sync the browser bridge again. Missing roster names do not prove free agency."
        )
        return set(), audit
    occupied = {pid for roster in rosters.values() for pid in roster}
    candidates = set()
    for item in snapshot.get("players", []):
        if not isinstance(item, dict) or item.get("status") not in ("FA", "W"):
            continue
        pid = assistant.resolve_player_id(item.get("name", ""), only_available=False)
        if pid in assistant.players and pid not in occupied:
            candidates.add(pid)
    audit["verified_candidates"] = len(candidates)
    if not candidates:
        audit["reason"] = (
            "No resolved, unrostered players with current Yahoo availability evidence."
        )
    return candidates, audit

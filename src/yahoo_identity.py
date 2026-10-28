"""Persist Yahoo identities; draft overlap is a one-time migration aid only."""

from . import draft_data
from .injury_tracker import normalize_name


def team_slots(rosters, prior, names=None):
    mapping = {str(k): str(v) for k, v in prior.items()}
    if any(
        not k.isdigit() or not 1 <= int(k) <= 14 or not v.isdigit() or not 0 <= int(v) < 14
        for k, v in mapping.items()
    ):
        raise ValueError("Invalid saved Yahoo team identity")
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("Saved Yahoo team identities collide")
    drafted = draft_data.build_rosters()
    canonical = {normalize_name(n): str(i) for i, n in enumerate(draft_data.TEAM_NAMES)}
    evidence = {}
    for raw, players in rosters.items():
        yahoo_id = str(int(raw) + 1)
        if not 1 <= int(yahoo_id) <= 14:
            raise ValueError("Invalid Yahoo team number")
        if yahoo_id in mapping:
            evidence[yahoo_id] = "saved_id"
            continue
        label = normalize_name((names or {}).get(str(raw), (names or {}).get(raw, "")))
        slot = canonical.get(label)
        if slot is None:
            observed = {normalize_name(p["name"]) for p in players if p.get("name")}
            scores = sorted(
                (
                    (len(observed & {normalize_name(n) for n in ns}), str(i))
                    for i, ns in drafted.items()
                ),
                reverse=True,
            )
            # Explicit migration confidence guard; no arbitrary fallback slot.
            if scores[0][0] < 3 or scores[0][0] <= scores[1][0]:
                raise ValueError("Yahoo team identity ambiguous; explicit team mapping required")
            slot = scores[0][1]
            evidence[yahoo_id] = "one_time_draft_bootstrap"
        else:
            evidence[yahoo_id] = "canonical_team_name"
        if slot in mapping.values():
            raise ValueError("Two Yahoo IDs resolve to the same team")
        mapping[yahoo_id] = slot
    return mapping, evidence


def roster_player_evidence(rosters, mapping):
    result, seen = {}, {}
    for raw, players in rosters.items():
        slot = mapping[str(int(raw) + 1)]
        result[slot] = []
        for item in players:
            if not item.get("name"):
                continue
            pid = item.get("yahoo_player_id")
            if pid is not None:
                pid = str(pid)
                if not pid.isdigit() or int(pid) <= 0 or pid in seen:
                    raise ValueError("Invalid or multiply owned Yahoo player ID")
                seen[pid] = slot
            result[slot].append(
                {
                    "name": item["name"],
                    "yahoo_player_id": pid,
                    "selected_position": item.get("selected_position"),
                    "status": item.get("status"),
                }
            )
    return result


def canonical_scoreboard(board, mapping):
    """Map provider IDs once, including final-result matchup metadata."""
    from copy import deepcopy

    result = deepcopy(board)
    if not mapping:
        return result  # Legacy archives retain their original ID convention.
    for pair in result.get("matchups", []):
        for team in pair:
            yahoo_id = str(team.get("yahoo_team_id", team["slot"]))
            if yahoo_id not in mapping:
                raise ValueError("Scoreboard Yahoo identity is not in the saved mapping")
            team["yahoo_team_id"] = int(yahoo_id)
            team["slot"] = int(mapping[yahoo_id]) + 1
    for state, pair in zip(result.get("matchup_states", []), result.get("matchups", [])):
        state["slots"] = [p["slot"] for p in pair]
    return result

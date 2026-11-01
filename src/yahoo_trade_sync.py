"""Read-only Yahoo offers and completed category standings, with stable identities.

GET resources documented at https://sports.yahoo.com/developer/docs/ .
No trade submission, acceptance, rejection or cancellation is implemented.
"""

import copy
import re
from collections import Counter
from datetime import datetime, timezone


def resolved_team_names(state):
    """Reject duplicate league titles accidentally captured as fourteen team names."""
    from .draft_data import TEAM_NAMES

    result = {str(i): name for i, name in enumerate(TEAM_NAMES)}
    supplied = {str(k): str(v).strip() for k, v in state.get("team_names", {}).items() if v}
    counts = Counter(name.casefold() for name in supplied.values())
    for team, name in supplied.items():
        if (
            team in result
            and counts[name.casefold()] == 1
            and not re.fullmatch(r"NBA Fantasy(?:\s+\d{4}(?:[-–]\d{2,4})?)?", name, re.I)
        ):
            result[team] = name
    return result


def _provider_team(value, league_id):
    value = str(value)
    match = re.fullmatch(r"(?:[^.]+\.l\.(\d+)\.t\.)?(\d+)", value)
    if not match or (match[1] and match[1] != str(league_id)):
        raise ValueError("Yahoo team key belongs to an unknown league")
    return match[2]


def _record(value):
    result = {}
    for key in ("W", "L", "T"):
        number = float(value[key])
        if not number.is_integer() or number < 0:
            raise ValueError("Standings need nonnegative integer category W/L/T")
        result[key] = int(number)
    return result


def normalize_stage5_capture(state, capture, captured_at=None, our_team="7"):
    """Return state updates; failed reads preserve the original observation time."""
    now = captured_at or datetime.now(timezone.utc).isoformat()
    mapping = {str(k): str(v) for k, v in state.get("yahoo_team_slots", {}).items()}
    league_id = str(state.get("league_id"))
    updates = {}
    audit = {"offers": "unavailable", "standings": "unavailable", "errors": []}
    if not isinstance(capture, dict) or not capture:
        updates["yahoo_trade_audit"] = audit
        return updates
    if str(capture.get("league_id")) != league_id or not mapping:
        raise ValueError("Stage 5 Yahoo capture identity disagrees with saved league")
    source = capture.get("source")
    if source not in ("yahoo_browser_league", "yahoo_api_league"):
        raise ValueError("Unsupported Stage 5 source")
    offers = capture.get("pending_offers", {})
    if not isinstance(offers, dict) or not isinstance(offers.get("offers", []), list):
        audit["errors"].append("Malformed pending-offer collection; previous snapshot preserved")
        offers = {}
    if offers.get("scan_complete") is True:
        try:
            normalized, seen = [], set()
            for item in offers.get("offers", []):
                offer_id = str(item["offer_id"])
                if not offer_id or offer_id in seen:
                    raise ValueError("Duplicate/missing provider offer ID")
                seen.add(offer_id)
                sender = mapping[_provider_team(item["trader_team_key"], league_id)]
                recipient = mapping[_provider_team(item["tradee_team_key"], league_id)]
                if sender == recipient or our_team not in (sender, recipient):
                    raise ValueError("Offer does not involve our configured Yahoo team")
                other = recipient if sender == our_team else sender
                give, receive = [], []
                for player in item["players"]:
                    pid = str(player["yahoo_player_id"])
                    if not pid.isdigit() or int(pid) <= 0:
                        raise ValueError("Offer needs an explicit Yahoo player ID")
                    origin = mapping[_provider_team(player["source_team_key"], league_id)]
                    destination = mapping[_provider_team(player["destination_team_key"], league_id)]
                    if {origin, destination} != {sender, recipient}:
                        raise ValueError("Offer player direction is unverified")
                    (give if origin == our_team else receive).append(pid)
                if not give or not receive or len(set(give + receive)) != len(give + receive):
                    raise ValueError("Offer player package is empty or duplicated")
                status = str(item["status"]).lower()
                if status not in ("proposed", "pending", "accepted", "offered"):
                    raise ValueError("Unsupported pending offer status")
                normalized.append(
                    {
                        "offer_id": offer_id,
                        "status": status,
                        "our_team": our_team,
                        "other_team": other,
                        "give_yahoo_ids": give,
                        "receive_yahoo_ids": receive,
                        "initiator_team": sender,
                        "recipient_team": recipient,
                        "direction": "received" if recipient == our_team else "sent",
                        "proposed_at": item.get("proposed_at"),
                        "created_at": item.get("proposed_at"),
                        "effective_date": item.get("effective_date"),
                    }
                )
            updates["pending_offers_snapshot"] = {
                "schema_version": 1,
                "source": source,
                "captured_at": now,
                "league_id": league_id,
                "team_slots": mapping,
                "scan_complete": True,
                "complete": True,
                "offers": normalized,
            }
            audit["offers"] = "ready"
        except (ValueError, KeyError, TypeError) as exc:
            audit["errors"].append(f"Pending offers: {exc}")
    else:
        audit["errors"].append(offers.get("reason", "Pending trade page was not verified"))
    standings = capture.get("standings")
    if standings is not None and not isinstance(standings, dict):
        audit["errors"].append("Malformed standings capture; previous snapshot preserved")
        standings = None
    if standings:
        try:
            week = standings["current_week"]
            through = standings["completed_through_week"]
            if type(week) is not int or type(through) is not int or week < 1 or through != week - 1:
                raise ValueError("Completed standings boundary must exclude the current week")
            records = {
                mapping[_provider_team(team, league_id)]: _record(record)
                for team, record in standings["records"].items()
            }
            if set(records) != set(mapping.values()) or any(
                sum(row.values()) != 9 * through for row in records.values()
            ):
                raise ValueError(
                    "Category standings are incomplete or include live current-week categories"
                )
            snapshot = {
                "schema_version": 1,
                "source": source,
                "captured_at": now,
                "league_id": league_id,
                "team_slots": mapping,
                "standings": records,
                "current_week": week,
                "completed_through_week": through,
                "tiebreak_rule": standings.get("tiebreak_rule", "unverified"),
            }
            if capture.get("current_scoreboard"):
                from .yahoo_identity import canonical_scoreboard

                snapshot["current_scoreboard"] = canonical_scoreboard(
                    capture["current_scoreboard"], mapping
                )
                snapshot["current_scoreboard"]["updated_at"] = now
            updates["playoff_snapshot"] = snapshot
            audit["standings"] = "ready"
        except (ValueError, KeyError, TypeError) as exc:
            audit["errors"].append(f"Standings: {exc}")
    updates["yahoo_trade_audit"] = audit
    return updates


def capture_api_stage5(client, current_board=None):
    """Fetch only authenticated user's pending trade collection and standings."""
    from .yahoo_draft_sync import _find_subresource, _merge_yahoo_meta

    if not client.league_key or not client.team_key:
        return None
    league_id = client.league_key.split(".l.")[-1]
    data = client._api_get(
        f"league/{client.league_key}/transactions;types=pending_trade;team_key={client.team_key}",
        timeout=5.0,
    )
    transactions = _find_subresource(data, "transactions")
    capture = {
        "source": "yahoo_api_league",
        "league_id": league_id,
        "pending_offers": {"scan_complete": False, "reason": "Yahoo pending trade API unavailable"},
    }
    if isinstance(transactions, dict) and "count" in transactions:
        offers = []
        try:
            for key, value in transactions.items():
                if key == "count":
                    continue
                node = value["transaction"]
                meta = _merge_yahoo_meta(node[0] if isinstance(node, list) else node)
                if meta.get("type") != "pending_trade":
                    raise ValueError("Unexpected Yahoo transaction type")
                players = _find_subresource(node, "players") or {}
                rows = []
                for pkey, pvalue in players.items():
                    if pkey == "count":
                        continue
                    player = pvalue["player"]
                    pmeta = _merge_yahoo_meta(player[0] if isinstance(player, list) else player)
                    direction = _merge_yahoo_meta(_find_subresource(player, "transaction_data"))
                    rows.append(
                        {
                            "yahoo_player_id": pmeta["player_id"],
                            "source_team_key": direction["source_team_key"],
                            "destination_team_key": direction["destination_team_key"],
                        }
                    )
                proposed = meta.get("trade_proposed_time")
                offers.append(
                    {
                        "offer_id": meta["transaction_key"],
                        "status": meta["status"],
                        "trader_team_key": meta["trader_team_key"],
                        "tradee_team_key": meta["tradee_team_key"],
                        "proposed_at": datetime.fromtimestamp(
                            int(proposed), timezone.utc
                        ).isoformat()
                        if proposed
                        else None,
                        "players": rows,
                    }
                )
            if len(offers) != int(transactions["count"]):
                raise ValueError("Incomplete pending transaction collection")
            capture["pending_offers"] = {"scan_complete": True, "offers": offers}
        except (KeyError, ValueError, TypeError):
            pass
    data = client._api_get(f"league/{client.league_key}/standings", timeout=5.0)
    teams = _find_subresource(data, "teams")
    week = (current_board or {}).get("week")
    if isinstance(teams, dict) and type(week) is int:
        try:
            records = {}
            for key, value in teams.items():
                if key == "count":
                    continue
                node = value["team"]
                meta = _merge_yahoo_meta(node[0] if isinstance(node, list) else node)
                outcome = _merge_yahoo_meta(_find_subresource(node, "outcome_totals"))
                records[meta["team_key"]] = {
                    "W": outcome["wins"],
                    "L": outcome["losses"],
                    "T": outcome["ties"],
                }
            capture["standings"] = {
                "current_week": week,
                "completed_through_week": week - 1,
                "records": records,
            }
            if current_board.get("week_verified"):
                capture["current_scoreboard"] = copy.deepcopy(current_board)
        except (KeyError, TypeError):
            pass
    return capture

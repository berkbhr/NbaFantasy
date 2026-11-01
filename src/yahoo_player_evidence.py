"""Timestamped Yahoo roster evidence shared by forecasts and trade analysis.

NBA injury observations remain authoritative when newer. A missing injury badge
only clears an old injury when the reader positively recognized a player row.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone


def verified_yahoo_positions(raw):
    if not isinstance(raw, (list, tuple)) or any(not isinstance(p, str) for p in raw):
        return None
    supplied = {p.strip().upper() for p in raw}
    specific = supplied & {"PG", "SG", "SF", "PF", "C"}
    if specific and supplied <= {"PG", "SG", "SF", "PF", "C", "G", "F", "UTIL", "BN", "IL", "IL+"}:
        return tuple(sorted(specific))
    return None


def _stamp(value):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (TypeError, ValueError):
        return None


def _status(value):
    raw = str(value or "").strip().upper()
    return (
        {
            "Q": "QUESTIONABLE",
            "GTD": "QUESTIONABLE",
            "DTD": "QUESTIONABLE",
            "O": "OUT",
            "INJ": "OUT",
            "IL": "OUT",
            "IL+": "OUT",
            "D": "DOUBTFUL",
            "P": "PROBABLE",
            "SUSP": "SUSPENDED",
        }.get(raw, raw)
        if raw
        in {
            "Q",
            "GTD",
            "DTD",
            "O",
            "INJ",
            "IL",
            "IL+",
            "D",
            "P",
            "SUSP",
            "SUSPENDED",
            "QUESTIONABLE",
            "OUT",
            "DOUBTFUL",
            "PROBABLE",
            "HEALTHY",
            "REST",
            "B2B_REST",
        }
        else None
    )


def roster_observation(item, state, now):
    """Return observation time and the shared validity decision for one row."""
    stamp = _stamp(
        item.get("captured_at") or state.get("roster_captured_at") or state.get("updated_at")
    )
    fresh = stamp is not None and -timedelta(minutes=5) <= now - stamp <= timedelta(hours=24)
    return stamp, fresh


def apply_yahoo_roster_evidence(assistant, state, now):
    """Apply fresh verified observations in memory; never write source caches."""
    positions = dict(assistant.pos_dict)
    metadata, verified = {}, set()
    counts = {
        "position_fallback": 0,
        "unverified_status": 0,
        "stale_rows": 0,
        "newer_model_status": 0,
    }
    stamps_complete = True
    healthy_proofs = {
        "yahoo_row_no_injury_badge",
        "yahoo_api_no_status",
        "yahoo_injury_badge",
        "yahoo_api_status",
    }
    for team, items in state.get("yahoo_roster_players", {}).items():
        owned_names = set(state.get("rosters", {}).get(str(team), []))
        for item in items:
            if item.get("name") not in owned_names:
                continue
            pid = assistant.resolve_player_id(item.get("name", ""), only_available=False)
            if pid not in assistant.players:
                continue
            player = assistant.players[pid]
            stamp, fresh = roster_observation(item, state, now)
            stamps_complete &= bool(item.get("captured_at"))
            model_stamp = _stamp(getattr(player, "injury_report_date", None))
            model_source = "injury_cache" if model_stamp else "model_baseline"
            status = _status(item.get("status"))
            status_verified = status is not None and (
                status != "HEALTHY" or item.get("status_evidence") in healthy_proofs
            )
            exact = verified_yahoo_positions(item.get("eligible_positions"))
            if fresh and exact:
                positions[pid] = ",".join(exact)
                verified.add(pid)
            else:
                counts["position_fallback"] += 1
            if not fresh:
                counts["stale_rows"] += 1
            if not status_verified:
                counts["unverified_status"] += 1
            if fresh and status_verified:
                if model_stamp is None or stamp >= model_stamp:
                    healthy = status == "HEALTHY"
                    player.update_injury_status(
                        status,
                        desc="" if healthy else getattr(player, "injury_desc", ""),
                        is_b2b_rest=False if healthy else getattr(player, "is_b2b_rest", False),
                        expected_return=None
                        if healthy
                        else getattr(player, "expected_return", None),
                        report_date=stamp.isoformat(),
                    )
                    model_stamp, model_source = stamp, "yahoo_roster"
                else:
                    counts["newer_model_status"] += 1
            metadata[pid] = {
                "yahoo_status": status,
                "yahoo_status_verified": bool(fresh and status_verified),
                "yahoo_status_observed_at": stamp.isoformat() if stamp else None,
                "model_status": player.injury_status,
                "model_status_source": model_source,
                "model_status_observed_at": model_stamp.isoformat() if model_stamp else None,
                "positions": positions.get(pid, ""),
                "positions_source": "yahoo_roster" if pid in verified else "nba_fallback",
                "positions_observed_at": stamp.isoformat() if pid in verified else None,
                "needs_yahoo_refresh": bool(not fresh or not exact or not status_verified),
            }
    warnings = []
    if counts["position_fallback"]:
        warnings.append(
            f"{counts['position_fallback']} oyuncuda güncel kesin Yahoo pozisyonu yok; NBA pozisyonu kullanıldı. Yeni okuyucuyla Yahoo senkronunu yenileyin."
        )
    if counts["unverified_status"]:
        warnings.append(
            f"{counts['unverified_status']} oyuncunun Yahoo sağlık durumu kanıtı eksik; eski sakatlık kaydı sessizce sağlıklıya çevrilmedi."
        )
    if counts["newer_model_status"]:
        warnings.append(
            f"{counts['newer_model_status']} oyuncuda Yahoo kaydından daha yeni sakatlık gözlemi modelde korundu."
        )
    digest = hashlib.sha256(json.dumps(metadata, sort_keys=True, default=str).encode()).hexdigest()
    return {
        "positions": positions,
        "verified_position_ids": verified,
        "players": metadata,
        "counts": counts,
        "warnings": warnings,
        "per_player_timestamps_complete": bool(metadata) and stamps_complete,
        "sha256": digest,
    }

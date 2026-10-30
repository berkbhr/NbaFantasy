"""Choose a clearly dated display snapshot without relabeling it as a new forecast."""

import gzip
import hashlib
import json
from pathlib import Path

import pandas as pd


def notification_snapshot(current, archive, max_age_hours=24):
    """A blocked intraday forecast may display a valid, same-matchup archive.

    This is presentation only: no cached recommendations are actionable and
    the new blocked prediction remains blocked for prospective evaluation.
    """
    if current.get("live_score_valid"):
        return current, None
    board = current.get("verified_scoreboard")
    if not board:
        return current, None
    now = pd.to_datetime(current["forecast_at"], utc=True)
    root = Path(archive)
    week = current["id"].split(":", 1)[0].replace("-", "")
    for path in sorted((root / "predictions").glob("*.json.gz"), reverse=True):
        if path.name[:8] < week:
            break
        if (root / "prediction_exclusions" / path.name).exists():
            continue
        try:
            raw = path.read_bytes()
            bundle = json.loads(gzip.decompress(raw))
            candidate = bundle.get("primary", {})
            stamp = pd.to_datetime(candidate.get("forecast_at"), utc=True, errors="coerce")
            if (
                not candidate.get("live_score_valid")
                or not candidate.get("live_score")
                or candidate.get("id") != current.get("id")
                or pd.isna(stamp)
                or not pd.Timedelta(0) <= now - stamp <= pd.Timedelta(hours=max_age_hours)
            ):
                continue
            for side in ("team_a", "team_b"):
                old = candidate["live_score"][side]
                if old.get("slot") != board[side].get("slot"):
                    break
                if old.get("yahoo_team_id") != board[side].get("yahoo_team_id"):
                    break
            else:
                metadata = {
                    "mode": "last_valid_forecast",
                    "forecast_id": bundle.get("forecast_id", path.name.removesuffix(".json.gz")),
                    "forecast_at": candidate["forecast_at"],
                    "prediction_sha256": hashlib.sha256(raw).hexdigest(),
                    "current_block_reason": current.get("live_score_block_reason"),
                }
                return candidate, metadata
        except (ValueError, OSError, KeyError, TypeError):
            continue
    return current, None

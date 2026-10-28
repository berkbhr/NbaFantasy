"""Validate dated live snapshots before combining them with future projections."""

import math

import pandas as pd

BOX_SCORE_KEYS = ("PTS", "REB", "AST", "STL", "BLK", "FG3M", "TOV", "FGM", "FGA", "FTM", "FTA")


def validate_live_snapshot(snapshot, now, max_age_hours=24):
    timestamp = pd.to_datetime(snapshot.get("updated_at"), utc=True, errors="coerce")
    current = pd.to_datetime(now, utc=True)
    if pd.isna(timestamp) or timestamp > current + pd.Timedelta(minutes=5):
        raise ValueError("Live scoreboard requires a valid capture timestamp")
    if current - timestamp > pd.Timedelta(hours=max_age_hours):
        raise ValueError("Live scoreboard is stale; synchronize Yahoo again")
    captured_et = timestamp.tz_convert("America/New_York").normalize()
    now_et = current.tz_convert("America/New_York").normalize()
    if captured_et - pd.Timedelta(days=captured_et.weekday()) != now_et - pd.Timedelta(
        days=now_et.weekday()
    ):
        raise ValueError("Live scoreboard belongs to a different fantasy week")
    matchup = snapshot.get("matchup", {})
    for side in ("team_a", "team_b"):
        team = matchup.get(side, {})
        for key in BOX_SCORE_KEYS:
            if key not in team or not math.isfinite(float(team[key])) or float(team[key]) < 0:
                raise ValueError(f"Missing/invalid scoreboard field: {side}.{key}")
        for stat in ("FG", "FT"):
            if float(team[stat + "M"]) > float(team[stat + "A"]):
                raise ValueError("Makes cannot exceed attempts")
    return matchup


def fantasy_week_window(now_utc, live_week_started=True):
    """Monday-Sunday in US/Eastern, with DST handled by the timezone database."""
    today = (
        pd.to_datetime(now_utc, utc=True)
        .tz_convert("America/New_York")
        .tz_localize(None)
        .normalize()
    )
    monday = today - pd.Timedelta(days=today.weekday())
    return (today if live_week_started else monday), monday + pd.Timedelta(days=6)

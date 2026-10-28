"""Validate dated live snapshots before combining them with future projections."""

import math

import pandas as pd

BOX_SCORE_KEYS = ("PTS", "REB", "AST", "STL", "BLK", "FG3M", "TOV", "FGM", "FGA", "FTM", "FTA")


def validate_pregame_window(schedule, now):
    """Daily model cannot estimate residual production for games already started.

    Fail closed after tipoff, even after a same-day final: Yahoo game coverage
    is not available to prove which realized games are in the captured score.
    """
    current = pd.to_datetime(now, utc=True)
    day = current.tz_convert("America/New_York").tz_localize(None).normalize()
    today = schedule[pd.to_datetime(schedule.GAME_DATE).dt.normalize() == day]
    if today.empty:
        return
    if "TIPOFF_UTC" not in today:
        raise ValueError(
            "Exact NBA tipoff times unavailable; weekly live decisions withheld until schedule refresh"
        )
    tipoffs = pd.to_datetime(today.TIPOFF_UTC, utc=True, errors="coerce")
    if tipoffs.isna().any():
        raise ValueError("Incomplete NBA tipoff times; weekly live decisions withheld")
    if "CLOCK_OBSERVED_AT" not in today:
        raise ValueError("NBA schedule clock has no observation timestamp; refresh schedule")
    stamps = pd.to_datetime(today.CLOCK_OBSERVED_AT, utc=True, errors="coerce")
    if stamps.isna().any() or (stamps > current + pd.Timedelta(minutes=5)).any():
        raise ValueError("NBA schedule clock timestamp invalid")
    if (stamps.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize() != day).any():
        raise ValueError("NBA schedule clock predates current Eastern day; refresh schedule")
    if (tipoffs <= current).any():
        raise ValueError(
            "Today's NBA games have started; partial-game score coverage is unverified, refresh next Eastern pregame day"
        )


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
    # Remaining projections start on today's Eastern schedule date. A score
    # captured yesterday can omit yesterday evening's games, even if it is
    # less than 24 hours old. Combining it with today's window silently drops
    # those games from BOTH the actual score and the future projection.
    if captured_et != now_et:
        raise ValueError(
            "Live scoreboard predates the current Eastern game date; "
            "synchronize Yahoo again before combining scores with remaining games"
        )
    matchup = snapshot.get("matchup", {})
    for side in ("team_a", "team_b"):
        team = matchup.get(side, {})
        for key in BOX_SCORE_KEYS:
            if key not in team or not math.isfinite(float(team[key])) or float(team[key]) < 0:
                raise ValueError(f"Missing/invalid scoreboard field: {side}.{key}")
        for stat in ("FG", "FT"):
            if float(team[stat + "M"]) > float(team[stat + "A"]):
                raise ValueError("Makes cannot exceed attempts")
        if float(team["FG3M"]) > float(team["FGM"]):
            raise ValueError("Live scoreboard three-pointers exceed field goals")
        if float(team["PTS"]) != 2 * float(team["FGM"]) + float(team["FG3M"]) + float(team["FTM"]):
            raise ValueError("Live scoreboard points identity invalid; possible shifted columns")
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

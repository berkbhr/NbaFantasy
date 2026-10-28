"""Enrich the existing schedule with official UTC tipoffs, without other sync side effects."""

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def enrich_schedule(schedule, official):
    if not {"gameId", "gameDateTimeUTC"} <= set(official):
        raise ValueError("Official schedule lacks game ID or exact UTC datetime")
    rows = official[["gameId", "gameDateTimeUTC"]].copy()
    rows["gameId"] = rows.gameId.astype(str)
    if rows.gameId.duplicated().any():
        raise ValueError("Official schedule has duplicate game IDs")
    times = dict(zip(rows.gameId, pd.to_datetime(rows.gameDateTimeUTC, utc=True, errors="coerce")))
    result = schedule.copy()
    result["TIPOFF_UTC"] = pd.to_datetime(result.GAME_ID.astype(str).map(times), utc=True)
    if result.TIPOFF_UTC.isna().any():
        raise ValueError("Some cached games have no official exact tipoff; schedule left unchanged")
    local_dates = (
        result.TIPOFF_UTC.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    )
    if not local_dates.equals(pd.to_datetime(result.GAME_DATE).dt.normalize()):
        raise ValueError(
            "Cached schedule dates disagree with official Eastern dates; refusing a clock-only patch"
        )
    return result


def refresh_schedule(season="2026_27"):
    from nba_api.stats.endpoints import scheduleleaguev2

    path = ROOT / "data/processed" / f"schedule_{season}.parquet"
    original = pd.read_parquet(path)
    raw = scheduleleaguev2.ScheduleLeagueV2(
        season=season.replace("_", "-"), timeout=20
    ).get_data_frames()[0]
    enriched = enrich_schedule(original, raw)
    enriched["CLOCK_OBSERVED_AT"] = pd.Timestamp.now(tz="UTC")
    temporary = path.with_suffix(".clock.tmp.parquet")
    enriched.to_parquet(temporary, index=False)
    temporary.replace(path)
    return {"games": int(enriched.GAME_ID.nunique()), "path": str(path)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", default="2026_27")
    args = parser.parse_args()
    print(refresh_schedule(args.season))

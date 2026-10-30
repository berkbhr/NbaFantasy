"""Enrich the existing schedule with official UTC tipoffs, without other sync side effects."""

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

ESPN_CODES = {"GS": "GSW", "NY": "NYK", "NO": "NOP", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS"}


def enrich_day_from_espn(schedule, payload, day, observed_at):
    """Match both NBA teams AND the Eastern date; never infer tipoffs from IDs."""
    day = pd.Timestamp(day).normalize()
    result = schedule.copy()
    target = pd.to_datetime(result.GAME_DATE).dt.normalize() == day
    if not target.any():
        raise ValueError("No cached games on the requested ESPN clock date")
    matches = {}
    for event in payload.get("events", []):
        stamp = pd.to_datetime(event.get("date"), utc=True, errors="coerce")
        if (
            pd.isna(stamp)
            or stamp.tz_convert("America/New_York").tz_localize(None).normalize() != day
        ):
            continue
        competitions = event.get("competitions", [])
        if len(competitions) != 1:
            continue
        teams = competitions[0].get("competitors", [])
        if len(teams) != 2 or {t.get("homeAway") for t in teams} != {"home", "away"}:
            continue
        codes = frozenset(
            ESPN_CODES.get(
                t.get("team", {}).get("abbreviation"), t.get("team", {}).get("abbreviation")
            )
            for t in teams
        )
        if None in codes or len(codes) != 2 or codes in matches:
            raise ValueError("Ambiguous ESPN clock matchup")
        matches[codes] = stamp
    rows = result.loc[target]
    for _, game in rows.groupby("GAME_ID"):
        codes = frozenset(game.TEAM_ABBREVIATION)
        if len(game) != 2 or len(codes) != 2 or codes not in matches:
            raise ValueError("ESPN clock does not cover every scheduled NBA matchup")
        result.loc[game.index, "TIPOFF_UTC"] = matches[codes]
        result.loc[game.index, "CLOCK_OBSERVED_AT"] = pd.Timestamp(observed_at)
        result.loc[game.index, "CLOCK_SOURCE"] = "ESPN_scoreboard"
    result["TIPOFF_UTC"] = pd.to_datetime(result.TIPOFF_UTC, utc=True, errors="coerce")
    result["CLOCK_OBSERVED_AT"] = pd.to_datetime(
        result.CLOCK_OBSERVED_AT, utc=True, errors="coerce"
    )
    return result


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


def refresh_schedule(season="2026_27", timeout=6, now=None):
    from nba_api.stats.endpoints import scheduleleaguev2

    path = ROOT / "data/processed" / f"schedule_{season}.parquet"
    original = pd.read_parquet(path)
    observed = pd.Timestamp(now or pd.Timestamp.now(tz="UTC"))
    if observed.tzinfo is None:
        raise ValueError("Clock observation must be timezone-aware")
    source = "NBA_stats"
    try:
        raw = scheduleleaguev2.ScheduleLeagueV2(
            season=season.replace("_", "-"), timeout=timeout
        ).get_data_frames()[0]
        enriched = enrich_schedule(original, raw)
    except Exception:
        # The stats endpoint can time out on hosted runners. The official CDN
        # is an independent transport; the same ID/date checks remain binding.
        import requests

        try:
            response = requests.get(
                "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json",
                timeout=timeout,
            )
            response.raise_for_status()
            rows = [
                game
                for day in response.json()["leagueSchedule"]["gameDates"]
                for game in day["games"]
            ]
            enriched = enrich_schedule(original, pd.DataFrame(rows))
            source = "NBA_CDN"
        except Exception:
            day = observed.tz_convert("America/New_York").tz_localize(None).normalize()
            response = requests.get(
                "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
                params={"dates": day.strftime("%Y%m%d"), "limit": 100},
                timeout=timeout,
            )
            response.raise_for_status()
            enriched = enrich_day_from_espn(original, response.json(), day, observed)
            source = "ESPN_scoreboard"
    if source != "ESPN_scoreboard":
        enriched["CLOCK_OBSERVED_AT"] = observed
        enriched["CLOCK_SOURCE"] = source
    temporary = path.with_suffix(".clock.tmp.parquet")
    enriched.to_parquet(temporary, index=False)
    temporary.replace(path)
    return {"games": int(enriched.GAME_ID.nunique()), "path": str(path), "source": source}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", default="2026_27")
    args = parser.parse_args()
    print(refresh_schedule(args.season))

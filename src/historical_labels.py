"""Small final roster labels from ESPN's own completed-game boxscores.

NBA historical CDN boxscores may be unavailable. Do not treat absent player
game logs as DNP. Keep explicit didNotPlay labels and source provenance only.
"""

import gzip
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

from .injury_tracker import normalize_name

ALIASES = {"GS": "GSW", "NY": "NYK", "NO": "NOP", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS"}


def fetch_day(day, directory):
    path = directory / f"{day}.json.gz"
    if path.exists():
        cached = json.loads(gzip.decompress(path.read_bytes()))
        if cached.get("sources") and not cached.get("errors"):
            return
    rows, sources, errors = [], [], []
    url = (
        "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates="
        + day.replace("-", "")
    )
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        scoreboard = response.json()
        for event in scoreboard.get("events", []):
            if not event.get("status", {}).get("type", {}).get("completed"):
                continue
            endpoint = (
                "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event="
                + str(event["id"])
            )
            data = requests.get(endpoint, timeout=15)
            data.raise_for_status()
            summary = data.json()
            sources.append({"url": endpoint, "sha256": hashlib.sha256(data.content).hexdigest()})
            for team in summary.get("boxscore", {}).get("players", []):
                code = team["team"]["abbreviation"]
                code = ALIASES.get(code, code)
                for table in team.get("statistics", []):
                    for athlete in table.get("athletes", []):
                        if not isinstance(athlete.get("didNotPlay"), bool):
                            continue
                        name = athlete["athlete"]["displayName"]
                        rows.append(
                            {
                                "date": day,
                                "name": name,
                                "norm": normalize_name(name),
                                "team_code": code,
                                "played": not athlete["didNotPlay"],
                                "event_id": event["id"],
                                "tipoff_at": event.get("date"),
                            }
                        )
    except (requests.RequestException, ValueError, KeyError) as exc:
        errors.append(type(exc).__name__)
    directory.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        gzip.compress(
            json.dumps({"date": day, "rows": rows, "sources": sources, "errors": errors}).encode(),
            mtime=0,
        )
    )


def backfill(root, output):
    output.mkdir(parents=True, exist_ok=True)
    protocol = {
        "sampling": "Monday and Thursday game dates, fixed before fetching labels",
        "scope": "Explicit completed ESPN final boxscore roster members; missing is unknown",
        "seasons": ["2024_25", "2025_26"],
    }
    (output / "label_protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    tasks = []
    for season in protocol["seasons"]:
        frame = pd.read_parquet(root / "data" / "processed" / f"schedule_{season}.parquet")
        days = sorted(pd.to_datetime(frame.GAME_DATE).unique())
        tasks.extend(
            (
                pd.Timestamp(day).strftime("%Y-%m-%d"),
                root / "data" / "archive" / "historical_labels" / season,
            )
            for day in days
            if pd.Timestamp(day).weekday() in (0, 3)
        )
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda args: fetch_day(*args), tasks))

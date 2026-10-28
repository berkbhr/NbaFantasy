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


def fetch_day(day, directory, schema_version=1):
    path = directory / f"{day}.json.gz"
    cached = json.loads(gzip.decompress(path.read_bytes())) if path.exists() else {}
    if (
        cached.get("sources")
        and not cached.get("errors")
        and cached.get("schema_version", 1) >= schema_version
    ):
        return
    reuse = cached.get("schema_version", 1) >= schema_version
    rows = list(cached.get("rows", [])) if reuse else []
    sources = list(cached.get("sources", [])) if reuse else []
    done = {r["url"].rsplit("=", 1)[-1] for r in sources}
    errors = []
    url = (
        "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates="
        + day.replace("-", "")
    )
    with requests.Session() as client:
        try:
            response = client.get(url, timeout=25)
            response.raise_for_status()
            events = response.json().get("events", [])
        except (requests.RequestException, ValueError) as exc:
            events = []
            errors.append(type(exc).__name__)
        for event in events:
            if (
                not event.get("status", {}).get("type", {}).get("completed")
                or str(event["id"]) in done
            ):
                continue
            endpoint = (
                "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event="
                + str(event["id"])
            )
            try:
                data = client.get(endpoint, timeout=25)
                data.raise_for_status()
                summary = data.json()
                event_rows = []
                for team in summary.get("boxscore", {}).get("players", []):
                    code = ALIASES.get(team["team"]["abbreviation"], team["team"]["abbreviation"])
                    for table in team.get("statistics", []):
                        for athlete in table.get("athletes", []):
                            if not isinstance(athlete.get("didNotPlay"), bool):
                                continue
                            name = athlete["athlete"]["displayName"]
                            event_rows.append(
                                {
                                    "date": day,
                                    "name": name,
                                    "norm": normalize_name(name),
                                    "team_code": code,
                                    "played": not athlete["didNotPlay"],
                                    "event_id": event["id"],
                                    "tipoff_at": event.get("date"),
                                    "position": athlete["athlete"]
                                    .get("position", {})
                                    .get("abbreviation"),
                                }
                            )
                if not event_rows:
                    errors.append("Empty_final_roster:" + str(event["id"]))
                    continue
                sources.append(
                    {"url": endpoint, "sha256": hashlib.sha256(data.content).hexdigest()}
                )
                rows.extend(event_rows)
            except (requests.RequestException, ValueError, KeyError) as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                errors.append(type(exc).__name__ + ":" + str(status) + ":" + str(event["id"]))
    directory.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        gzip.compress(
            json.dumps(
                {
                    "schema_version": schema_version,
                    "date": day,
                    "rows": rows,
                    "sources": sources,
                    "errors": errors,
                }
            ).encode(),
            mtime=0,
        )
    )


def backfill(root, output, full=False):
    output.mkdir(parents=True, exist_ok=True)
    protocol = {
        "sampling": "All cached regular-season game dates"
        if full
        else "Monday and Thursday game dates, fixed before fetching labels",
        "scope": "Explicit completed ESPN final boxscore roster members; missing is unknown",
        "seasons": ["2024_25", "2025_26"],
    }
    (output / ("label_protocol_full.json" if full else "label_protocol.json")).write_text(
        json.dumps(protocol, indent=2), encoding="utf-8"
    )
    tasks = []
    for season in protocol["seasons"]:
        frame = pd.read_parquet(root / "data" / "processed" / f"schedule_{season}.parquet")
        days = sorted(pd.to_datetime(frame.GAME_DATE).unique())
        tasks.extend(
            (
                pd.Timestamp(day).strftime("%Y-%m-%d"),
                root
                / "data"
                / "archive"
                / ("historical_labels_v2" if full else "historical_labels")
                / season,
            )
            for day in days
            if full or pd.Timestamp(day).weekday() in (0, 3)
        )
    with ThreadPoolExecutor(max_workers=4) as pool:
        for index, _ in enumerate(
            pool.map(lambda args: fetch_day(*args, schema_version=2 if full else 1), tasks)
        ):
            if index % 25 == 0:
                print(f"Final-roster labels {index + 1}/{len(tasks)}", flush=True)

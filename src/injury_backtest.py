"""Official historical reports at a fixed noon ET cutoff; bounded experiments.

Backfill is isolated from the live injury DB. Missing reports are unknown.
Availability is evaluated only for explicitly reported players with final
boxscore roster confirmation. Spillover is exploratory conditional on playing.
"""

import argparse
import gzip
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from .injury_tracker import normalize_name
from .nba_injury_scraper import extract_text_from_pdf, parse_report_text

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "injury_calibration"
DATA = ROOT / "data" / "archive" / "historical_injuries"
PROTOCOL = {
    "selection": "2024_25",
    "assessment": "2025_26",
    "cutoff": "12:00 America/New_York",
    "availability_candidates": ["current_status", "beta_status_shrink20", "beta_status_shrink60"],
    "availability_baseline": "BayesianPlayer status/availability filter replayed from completed prior and past team games; historical team membership proxy; no live deployment",
    "spillover_candidates": [0, 0.5, 1.0],
    "label_sampling": "Monday and Thursday dates fixed before label download; explicit ESPN completed boxscore DNP labels",
    "spillover_scope": "Exploratory roster from past appearances >=3 games and <=21 days, at least8 known teammates, pooled positions; no live deployment",
    "spillover_learning": "recent_blend role and observed teammate-absence subtraction; availability updated only after each completed-day observation",
    "selection_metric": "availability Brier; spillover conditional-minute MAE",
    "acceptance": "Same gate function as prior calibration: >=.25% gain, weekly paired95%CI>0, both halves nonnegative; cohorts and companion metrics guarded",
    "minimum_selection_rows": 1000,
    "minimum_assessment_rows": 1000,
    "prior_status_probabilities": {
        "OUT": 0.0,
        "DOUBTFUL": 0.15,
        "QUESTIONABLE": 0.52,
        "PROBABLE": 0.9,
        "AVAILABLE": 0.9,
    },
    "missingness": "No report or unsubmitted team != healthy. Unconfirmed boxscore membership != DNP.",
    "causality": "Use only reports with header <=noon ET and games starting after cutoff. No final status substitution.",
    "deployment": "Never automatically deploy historical injury experiments. Missing historical positions/rosters make spillover exploratory.",
}


def download_day(item):
    season, day = item
    path = DATA / season / f"{day}.json.gz"
    if path.exists():
        cached = json.loads(gzip.decompress(path.read_bytes()))
        if cached.get("cache_schema") == 3:
            if cached.get("extracted_text") and cached.get("status") == "usable":
                parsed = parse_report_text(cached["extracted_text"])
                cached["rows"] = parsed["rows"]
                cached["unsubmitted_teams"] = parsed["unsubmitted_teams"]
                path.write_bytes(gzip.compress(json.dumps(cached, default=str).encode(), mtime=0))
            return cached
    cutoff = datetime.fromisoformat(day + "T12:00:00").replace(tzinfo=ZoneInfo("America/New_York"))
    record = {
        "cache_schema": 3,
        "date": day,
        "cutoff_at": cutoff.isoformat(),
        "rows": [],
        "status": "missing",
    }
    errors = []
    for clock in ("12PM", "12_00PM", "11AM", "11_00AM"):
        url = f"https://ak-static.cms.nba.com/referee/injury/Injury-Report_{day}_{clock}.pdf"
        try:
            response = requests.get(url, timeout=12)
            if response.status_code != 200 or not response.content.startswith(b"%PDF-"):
                errors.append(str(response.status_code))
                continue
            text = extract_text_from_pdf(response.content)
            parsed = parse_report_text(text)
            header = parsed["report_time_utc"]
            record.update(
                {
                    "url": url,
                    "extracted_text": text,
                    "downloaded_pdf_bytes": len(response.content),
                    "sha256": hashlib.sha256(response.content).hexdigest(),
                    "report_at": header.isoformat() if header else None,
                    "unparsed_count": len(parsed["unparsed_lines"]),
                    "candidate_count": parsed["candidate_count"],
                    "unsubmitted_teams": parsed["unsubmitted_teams"],
                }
            )
            if header is not None and header > cutoff:
                # Older hourly filenames can point to a report stamped :30.
                # Fall back to an earlier file; do not mislabel it as noon data.
                continue
            # Do not tune parser health thresholds after looking at outcomes.
            healthy = (
                header is not None
                and header <= cutoff
                and (len(parsed["unparsed_lines"]) / max(1, parsed["candidate_count"]) <= 0.05)
            )
            record["status"] = "usable" if healthy else "quarantined"
            record["rows"] = parsed["rows"] if healthy else []
            break
        except (requests.RequestException, ValueError) as exc:
            errors.append(type(exc).__name__)
    record["errors"] = errors
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(record, default=str).encode(), mtime=0))
    return record


def backfill():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "protocol.json").write_text(json.dumps(PROTOCOL, indent=2), encoding="utf-8")
    tasks = []
    for season in ("2024_25", "2025_26"):
        schedule = pd.read_parquet(ROOT / "data" / "processed" / f"schedule_{season}.parquet")
        days = sorted(pd.to_datetime(schedule.GAME_DATE).dt.strftime("%Y-%m-%d").unique())
        tasks.extend((season, day) for day in days)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i, record in enumerate(pool.map(download_day, tasks)):
            if i % 25 == 0:
                print(f"{i + 1}/{len(tasks)} {record['date']} {record['status']}", flush=True)
    run_experiments()


def rows_for_season(season):
    logs = pd.read_parquet(ROOT / "data" / "raw" / f"player_logs_{season}.parquet")
    logs["date"] = pd.to_datetime(logs.GAME_DATE).dt.strftime("%Y-%m-%d")
    # Names are label joins only, not a reconstruction of future roster eligibility.
    logs["norm"] = logs.PLAYER_NAME.map(normalize_name)
    box = {(r["date"], r["norm"]): r for r in logs.to_dict("records")}
    rows, coverage = [], {"usable": 0, "quarantined": 0, "missing": 0, "matched_positive_only": 0}
    for path in sorted((DATA / season).glob("*.json.gz")):
        report = json.loads(gzip.decompress(path.read_bytes()))
        coverage[report["status"]] += 1
        if report["status"] != "usable":
            continue
        for row in report["rows"]:
            if pd.to_datetime(row["game_date"]).strftime("%Y-%m-%d") != report["date"]:
                continue
            time = str(row.get("game_time", ""))
            try:
                hour = int(time.split(":")[0])
                # Official table uses 12-hour afternoon/evening clocks without AM/PM.
                # Noon games are conservatively excluded; malformed/ambiguous clocks skipped.
                if hour < 1 or hour >= 12:
                    continue
            except ValueError:
                continue
            actual = box.get((report["date"], normalize_name(row["name"])))
            if actual is None:
                # Player game logs omit most DNPs. Cannot use absence as a negative label.
                continue
            coverage["matched_positive_only"] += 1
            rows.append(
                {
                    "date": report["date"],
                    "name": row["name"],
                    "status": row["status"],
                    "played": int(actual["MIN"] > 0),
                    "minutes": float(actual["MIN"]),
                    "team_id": int(actual["TEAM_ID"]),
                    "player_id": int(actual["PLAYER_ID"]),
                    "game_id": str(actual["GAME_ID"]),
                    "report_sha256": report["sha256"],
                }
            )
    return pd.DataFrame(rows), coverage


def run_experiments():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "protocol.json").write_text(json.dumps(PROTOCOL, indent=2), encoding="utf-8")
    result = {"protocol": PROTOCOL, "coverage": {}, "availability": {}, "spillover": {}}
    for season in ("2024_25", "2025_26"):
        frame, coverage = rows_for_season(season)
        result["coverage"][season] = coverage
        if not frame.empty:
            frame.to_csv(OUT / f"matched_{season}.csv", index=False)
        # A cohort conditioned on appearing in player-game logs cannot calibrate
        # availability: positives dominate by construction. Refuse fake results.
        result["availability"][season] = {
            "status": "requires_final_boxscore_rosters",
            "matched_rows": len(frame),
            "explicit_negative_rows": int((frame.played == 0).sum()) if not frame.empty else 0,
        }
        result["spillover"][season] = {
            "status": "requires_causal_roster_replay",
            "reason": "Report-listed labels are not a complete pregame rotation. No current roster/position snapshot substituted.",
        }
    (OUT / "coverage.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backfill", action="store_true")
    parser.add_argument("--labels", action="store_true")
    parser.add_argument("--experiments", action="store_true")
    args = parser.parse_args()
    if args.backfill:
        backfill()
    elif args.labels:
        from .historical_labels import backfill as backfill_labels

        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "protocol.json").write_text(json.dumps(PROTOCOL, indent=2), encoding="utf-8")
        backfill_labels(ROOT, OUT)
        from .injury_experiments import run

        print(json.dumps(run(ROOT, OUT), indent=2), flush=True)
    elif args.experiments:
        from .injury_experiments import run

        run_experiments()
        print(json.dumps(run(ROOT, OUT), indent=2), flush=True)
    else:
        run_experiments()

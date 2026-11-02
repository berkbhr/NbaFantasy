"""Local weekly review: latest valid daily forecasts and a frozen opening forecast."""

import gzip
import hashlib
import json
import re
import threading
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

LOCK = threading.RLock()
KEYS = (
    "id",
    "forecast_at",
    "week_start",
    "week_end",
    "my_team",
    "opponent",
    "expected_category_points",
    "win",
    "draw",
    "loss",
    "categories",
    "live_score",
    "live_score_valid",
    "recommendations",
    "roster_health",
    "notes",
    "model_source_sha256",
)


def _folder(root):
    return Path(root) / "reports/weekly_history"


def _save(root, key, data):
    folder = _folder(root)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (key + ".json")
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    temp.replace(path)


def load_week(root, key):
    if not re.fullmatch(r"[a-f0-9]{64}", key or ""):
        raise ValueError("Geçersiz hafta kaydı")
    return json.loads((_folder(root) / (key + ".json")).read_text(encoding="utf-8"))


def _identity(board, start, end, league):
    a, b = board["team_a"]["yahoo_team_id"], board["team_b"]["yahoo_team_id"]
    identity = [str(league), start, end, a, b]
    return hashlib.sha256(json.dumps(identity).encode()).hexdigest()


def record_forecast(root, report, league="local"):
    """One latest-valid prediction per Eastern scoring day; opening stays frozen."""
    if not report.get("live_score_valid") or not report.get("live_score"):
        return None
    board = report["live_score"]
    start = board.get("period_start") or report.get("id", "").split(":")[0]
    end = board.get("period_end") or report.get("week_end")
    try:
        day = (
            datetime.fromisoformat(report["forecast_at"].replace("Z", "+00:00"))
            .astimezone(ZoneInfo("America/New_York"))
            .date()
            .isoformat()
        )
        date.fromisoformat(start)
        date.fromisoformat(end)
        if not start <= day <= end:
            return None
        key = _identity(board, start, end, league)
    except (KeyError, ValueError, TypeError):
        return None
    with LOCK:
        path = _folder(root) / (key + ".json")
        data = (
            load_week(root, key)
            if path.exists()
            else {
                "key": key,
                "start": start,
                "end": end,
                "league": league,
                "my_team": report.get("my_team"),
                "opponent": report.get("opponent"),
                "team_ids": [board["team_a"]["yahoo_team_id"], board["team_b"]["yahoo_team_id"]],
                "days": {},
                "opening": None,
                "score": None,
            }
        )
        previous = data["days"].get(day)
        if previous is None or datetime.fromisoformat(
            report["forecast_at"].replace("Z", "+00:00")
        ) > datetime.fromisoformat(previous["forecast_at"].replace("Z", "+00:00")):
            saved = {k: deepcopy(report[k]) for k in KEYS if k in report}
            data["days"][day] = saved
            if data["opening"] is None and all(
                board[s].get("games_played") == 0 for s in ("team_a", "team_b")
            ):
                data["opening"] = deepcopy(saved)
            _save(root, key, data)
    return key


def record_closed_score(root, board, captured_at, league="local"):
    """Keep an observed closed-period score separate from frozen predictions.

    This is the Yahoo score as captured, which can receive later stat corrections.
    Never equate zero remaining games during an active week with a final result.
    """
    try:
        start, end = board["period_start"], board["period_end"]
        day = (
            datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
            .astimezone(ZoneInfo("America/New_York"))
            .date()
            .isoformat()
        )
        if day <= end or any(board[s]["games_remaining"] != 0 for s in ("team_a", "team_b")):
            return
        key = _identity(board, start, end, league)
        with LOCK:
            if not (_folder(root) / (key + ".json")).exists():
                return
            data = load_week(root, key)
            old = data.get("score")
            if old and old["captured_at"] >= captured_at:
                return
            data["score"] = {"captured_at": captured_at, "board": deepcopy(board)}
            _save(root, key, data)
    except (KeyError, ValueError, TypeError):
        return


def weeks(root):
    result = []
    with LOCK:
        for path in _folder(root).glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            result.append({k: data.get(k) for k in ("key", "start", "end", "opponent")})
    return sorted(result, key=lambda r: (r["start"], r["key"]), reverse=True)


def record_latest(root):
    root = Path(root)
    path = root / "reports/latest_forecast.json"
    if not path.exists():
        return None
    report = json.loads(path.read_text(encoding="utf-8"))
    sources = report.get("source_sha256") or {}
    if not sources:
        return None
    for name, expected in sources.items():
        source = (root / name.replace("\\", "/")).resolve()
        if not source.is_relative_to(root.resolve()) or not source.is_file():
            return None
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            return None
    state = json.loads((root / "data/processed/league_state.json").read_text(encoding="utf-8"))
    return record_forecast(root, report, state.get("league_id", "local"))


def import_saved(root):
    """Migrate actual, already saved panel forecasts; never manufacture past days."""
    root = Path(root)
    state_path = root / "data/processed/league_state.json"
    league = (
        json.loads(state_path.read_text(encoding="utf-8")).get("league_id", "local")
        if state_path.exists()
        else "local"
    )
    for path in sorted((root / "reports/panel_forecasts/predictions").glob("*.json.gz")):
        try:
            report = json.loads(gzip.decompress(path.read_bytes()))["primary"]
            record_forecast(root, report, league)
        except (ValueError, KeyError, OSError, TypeError):
            continue
    record_latest(root)


def category_results(board):
    """Derived from the captured shot counts; this is not an official Yahoo label."""
    a, b = board["team_a"], board["team_b"]
    result = {}
    for category in ("PTS", "REB", "AST", "STL", "BLK", "TOV", "FG3M", "FG_PCT", "FT_PCT"):
        if category.endswith("_PCT"):
            stat = category[:2]
            left = a[stat + "M"] * (b[stat + "A"] or 1)
            right = b[stat + "M"] * (a[stat + "A"] or 1)
        else:
            left, right = a[category], b[category]
        result[category] = (
            0.5 if left == right else float((left < right) if category == "TOV" else (left > right))
        )
    return result

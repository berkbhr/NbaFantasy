"""Final NBA CDN boxscores provide explicit roster/DNP labels."""

import gzip
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "archive" / "final_boxscores"


def final_boxscore(game_id, fetch=False):
    path = CACHE / f"{game_id}.json.gz"
    if path.exists():
        return json.loads(gzip.decompress(path.read_bytes()))
    if not fetch:
        return None
    try:
        response = requests.get(
            f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json", timeout=12
        )
        if response.status_code != 200:
            return None
        payload = response.json()
        if payload.get("game", {}).get("gameStatus") != 3:
            return None
        game = payload["game"]
        compact = {"game": {k: game.get(k) for k in ("gameId", "gameStatus", "gameTimeUTC")}}
        for side in ("homeTeam", "awayTeam"):
            team = game[side]
            compact["game"][side] = {
                "teamId": team["teamId"],
                "players": [
                    {
                        **{k: p.get(k) for k in ("personId", "name", "played", "notPlayingReason")},
                        "statistics": {"minutes": p.get("statistics", {}).get("minutes")},
                    }
                    for p in team["players"]
                ],
            }
        payload = compact
        CACHE.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(gzip.compress(json.dumps(payload).encode(), mtime=0))
        return payload
    except (requests.RequestException, ValueError, FileExistsError):
        return None


def roster_labels(payload):
    game = payload["game"]
    if game.get("gameStatus") != 3:
        raise ValueError("Final boxscore required")
    rows = []
    for side in ("homeTeam", "awayTeam"):
        team = game[side]
        for player in team["players"]:
            # Explicit played flag is required; do not interpret missing as DNP.
            if player.get("played") not in ("1", "0", 1, 0):
                continue
            stats = player.get("statistics", {})
            played = str(player["played"]) == "1"
            rows.append(
                {
                    "player_id": int(player["personId"]),
                    "team_id": int(team["teamId"]),
                    "game_id": str(game["gameId"]),
                    "name": player.get("name", ""),
                    "played": played,
                    "tipoff_at": game.get("gameTimeUTC"),
                    "minutes": stats.get("minutes"),
                    "not_playing_reason": player.get("notPlayingReason"),
                }
            )
    return rows

"""Read actual Yahoo periods/opponents; do not derive them from the NBA schedule."""


def capture_api_calendar(client, current_board=None):
    """Yahoo's documented league/settings and per-week scoreboard resources.

    Callers persist through fantasy_calendar.merge_capture so missing weeks do not
    overwrite previously confirmed observations. This function never sends messages.
    """
    from .yahoo_draft_sync import _find_subresource, _merge_yahoo_meta

    if not client.league_key:
        return None
    data = client._api_get(f"league/{client.league_key}", timeout=5.0)
    meta = _merge_yahoo_meta(_find_subresource(data, "league"))
    if (
        str(meta.get("league_id", client.league_key.split(".l.")[-1]))
        != client.league_key.split(".l.")[-1]
    ):
        return None
    data = client._api_get(f"league/{client.league_key}/settings", timeout=5.0)
    settings = _merge_yahoo_meta(_find_subresource(data, "settings"))
    try:
        year = int(meta["season"])
        current = int((current_board or {}).get("week") or meta["current_week"])
        if str(settings.get("uses_playoff")) == "0":
            cutoff = int(meta["end_week"])
        else:
            cutoff = int(settings["playoff_start_week"]) - 1
        if not 1 <= current <= 60 or not 1 <= cutoff <= 60:
            return None
    except (KeyError, ValueError, TypeError):
        return None
    capture = {
        "source": "yahoo_api_scoreboard",
        "league_id": client.league_key.split(".l.")[-1],
        "season": f"{year}_{str(year + 1)[-2:]}",
        "regular_season_end_week": cutoff,
        "weeks": [],
    }
    for number in range(current, cutoff + 1):
        board = (
            current_board
            if number == current and current_board
            else client.fetch_live_scoreboard(number)
        )
        if not board or not board.get("week_verified") or board.get("week") != number:
            continue
        pairs, states = board.get("matchups", []), board.get("matchup_states", [])
        if not pairs or len(pairs) != len(states):
            continue
        dates = {(s.get("week_start"), s.get("week_end")) for s in states}
        if len(dates) != 1:
            continue
        start, end = dates.pop()
        if not start or not end:
            continue
        capture["weeks"].append(
            {
                "week": number,
                "start": start,
                "end": end,
                "fixtures": [
                    [str(t.get("yahoo_team_id", t["slot"])) for t in pair] for pair in pairs
                ],
            }
        )
    return capture

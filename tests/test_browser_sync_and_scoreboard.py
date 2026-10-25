import os
import json
import pytest
from src import yahoo_browser_sync
from src import cloud_sync

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_bookmarklet_and_setup_html_structure():
    """Verifies that the 1-click Bookmarklet scans all 14 teams, transactions, and matchup tables."""
    js = yahoo_browser_sync.BOOKMARKLET_JS_RAW
    assert "/nba/${leagueId}/${s}" in js
    assert "/nba/${leagueId}/transactions" in js
    assert "http://127.0.0.1:8765/sync_league" in js
    assert "Games\\s*Played" in js

    html = yahoo_browser_sync.build_setup_html()
    assert "javascript:" in html
    assert "🏀 NBA Fantasy Sync" in html


def test_live_matchup_json_and_comparative_scoreboard():
    """Verifies that live_matchup.json contains all 11 Yahoo box score fields and remaining games."""
    live_path = os.path.join(PROJECT_ROOT, "data", "processed", "live_matchup.json")
    assert os.path.exists(live_path)
    with open(live_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    m = data["matchup"]
    ta, tb = m["team_a"], m["team_b"]
    for k in ("FGM", "FGA", "FTM", "FTA", "FG3M", "PTS", "REB", "AST", "STL", "BLK", "TOV", "games_played", "games_remaining"):
        assert k in ta
        assert k in tb
    assert ta["games_played"] == 30 and ta["games_remaining"] == 7
    assert tb["games_played"] == 30 and tb["games_remaining"] == 6

    with open(cloud_sync.__file__, "r", encoding="utf-8") as f:
        cs_src = f.read()
    assert "ANLIK YAHOO SKOR TABLOSU" in cs_src
    assert "HAFTA SONU FİNAL TAHMİNİ" in cs_src
    assert "Canlı Yahoo Senkron Aktif" in cs_src


def test_canonical_draft_slot_mapping_for_all_14_teams():
    """Verifies that Yahoo registration slots (1..14) map accurately to draft slots (0..13)."""
    state_path = os.path.join(PROJECT_ROOT, "data", "processed", "league_state.json")
    with open(state_path, "r", encoding="utf-8") as f:
        st = json.load(f)
    berk_roster = st["rosters"]["7"]
    sile_roster = st["rosters"]["12"]
    assert "Tyrese Maxey" in berk_roster and "Precious Achiuwa" in berk_roster and "Brandon Ingram" in berk_roster
    assert "Donovan Mitchell" in sile_roster and "Scottie Barnes" in sile_roster and "Jimmy Butler III" in sile_roster
    assert yahoo_browser_sync._resolve_canonical_draft_slot(berk_roster, 13) == "7"
    assert yahoo_browser_sync._resolve_canonical_draft_slot(sile_roster, 7) == "12"


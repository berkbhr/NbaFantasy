import os
import json
import unittest
from src import yahoo_browser_sync
from src import cloud_sync

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestBrowserSyncAndScoreboard(unittest.TestCase):
    def test_bookmarklet_and_setup_html_structure(self):
        """Verifies that the 1-click Bookmarklet scans all 14 teams, transactions, and matchup tables."""
        js = yahoo_browser_sync.BOOKMARKLET_JS_RAW
        self.assertIn("/nba/${leagueId}/${s}", js)
        self.assertIn("/nba/${leagueId}/transactions", js)
        self.assertIn("http://127.0.0.1:8765/sync_league", js)
        self.assertIn("Games\\s*Played", js)

        html = yahoo_browser_sync.build_setup_html()
        self.assertIn("javascript:", html)
        self.assertIn("🏀 NBA Fantasy Sync", html)

    def test_live_matchup_json_and_comparative_scoreboard(self):
        """Verifies that live_matchup.json contains all 11 Yahoo box score fields and remaining games."""
        live_path = os.path.join(PROJECT_ROOT, "data", "processed", "live_matchup.json")
        self.assertTrue(os.path.exists(live_path))
        with open(live_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        m = data["matchup"]
        ta, tb = m["team_a"], m["team_b"]
        for k in ("FGM", "FGA", "FTM", "FTA", "FG3M", "PTS", "REB", "AST", "STL", "BLK", "TOV", "games_played", "games_remaining"):
            self.assertIn(k, ta)
            self.assertIn(k, tb)
        self.assertIsInstance(ta["games_played"], int)
        self.assertGreaterEqual(ta["games_remaining"], 0)
        self.assertIsInstance(tb["games_played"], int)
        self.assertGreaterEqual(tb["games_remaining"], 0)

        with open(cloud_sync.__file__, "r", encoding="utf-8") as f:
            cs_src = f.read()
        self.assertIn("ANLIK YAHOO SKOR TABLOSU", cs_src)
        self.assertIn("HAFTA SONU FİNAL TAHMİNİ", cs_src)
        self.assertIn("Canlı Yahoo Senkron Aktif", cs_src)

    def test_canonical_draft_slot_mapping_for_all_14_teams(self):
        """Verifies that Yahoo registration slots (1..14) map accurately to draft slots (0..13)."""
        state_path = os.path.join(PROJECT_ROOT, "data", "processed", "league_state.json")
        with open(state_path, "r", encoding="utf-8") as f:
            st = json.load(f)
        berk_roster = st["rosters"]["7"]
        sile_roster = st["rosters"]["12"]
        self.assertTrue("Tyrese Maxey" in berk_roster and "Precious Achiuwa" in berk_roster and "Brandon Ingram" in berk_roster)
        self.assertTrue("Donovan Mitchell" in sile_roster and "Scottie Barnes" in sile_roster and "Jimmy Butler III" in sile_roster)
        self.assertEqual(yahoo_browser_sync._resolve_canonical_draft_slot(berk_roster, 13), "7")
        self.assertEqual(yahoo_browser_sync._resolve_canonical_draft_slot(sile_roster, 7), "12")

    def test_in_season_bayesian_update_and_week_schedule_window(self):
        """Verifies that current-season game logs update role minutes & per-minute rates and week window is Mon-Sun."""
        from datetime import datetime, timezone
        import pandas as pd
        from src.live_draft_assistant import LiveDraftAssistant

        w_start, w_end = cloud_sync.current_fantasy_week_window(
            datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc), live_week_started=True
        )
        self.assertEqual(str(w_start.date()), "2026-10-26")
        self.assertEqual(str(w_end.date()), "2026-11-01")

        assistant = LiveDraftAssistant(prior_season="2025_26", num_teams=14)
        vuc_id = assistant.resolve_player_id("Nikola Vucevic", only_available=False)
        hay_id = assistant.resolve_player_id("Jaxson Hayes", only_available=False)
        vuc_team = assistant.engine.team_map.get(vuc_id, 1610612741)
        uta_team = 1610612762

        rows = []
        for idx, gdate in enumerate(["2026-10-20", "2026-10-22", "2026-10-24"]):
            rows.append({
                "PLAYER_ID": vuc_id, "PLAYER_NAME": "Nikola Vucevic",
                "TEAM_ID": vuc_team, "TEAM_ABBREVIATION": "CHI",
                "GAME_ID": f"00226000{idx}1", "GAME_DATE": gdate,
                "MIN": 5.0, "PTS": 1.5, "REB": 0.5, "AST": 0.0, "STL": 0.0, "BLK": 0.0,
                "FG3M": 0.0, "TOV": 0.0, "FGM": 1.0, "FGA": 2.0, "FTM": 0.0, "FTA": 0.0,
            })
            rows.append({
                "PLAYER_ID": hay_id, "PLAYER_NAME": "Jaxson Hayes",
                "TEAM_ID": uta_team, "TEAM_ABBREVIATION": "UTA",
                "GAME_ID": f"00226000{idx}2", "GAME_DATE": gdate,
                "MIN": 26.0, "PTS": 11.0, "REB": 5.0, "AST": 2.5, "STL": 1.0, "BLK": 3.5,
                "FG3M": 0.0, "TOV": 1.0, "FGM": 5.0, "FGA": 7.0, "FTM": 1.0, "FTA": 2.0,
            })

        assistant.apply_current_season_logs(pd.DataFrame(rows))
        self.assertLess(assistant.players[vuc_id].expected_minutes, 14.0)
        self.assertGreater(assistant.players[hay_id].expected_minutes, 21.0)
        self.assertGreater(
            assistant.df_base.loc[hay_id, "BASE_Z"],
            assistant.df_base.loc[vuc_id, "BASE_Z"],
        )


if __name__ == "__main__":
    unittest.main()

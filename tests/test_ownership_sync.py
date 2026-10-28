import json
import shutil
import subprocess
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src import draft_data
from src.ownership import free_agent_ids
from src.yahoo_browser_sync import (
    BOOKMARKLET_JS_RAW,
    apply_browser_sync_payload,
    validate_browser_matchup,
)


class OwnershipSyncTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 28, 14, tzinfo=timezone.utc)
        self.assistant = SimpleNamespace(
            players={1: object(), 2: object(), 3: object()},
            resolve_player_id=lambda name, **kwargs: {
                "Owned Player": 1,
                "Verified Free Agent": 2,
                "Verified Waiver": 3,
            }.get(name),
        )

    def snapshot(self):
        return {
            "availability_snapshot": {
                "source": "yahoo_available_players",
                "updated_at": self.now.isoformat(),
                "scan_complete": False,
                "players": [
                    {"name": "Owned Player", "status": "FA"},
                    {"name": "Verified Free Agent", "status": "FA"},
                    {"name": "Verified Waiver", "status": "W"},
                ],
            }
        }

    def test_positive_availability_required_even_when_roster_missing_and_drop_inferred(self):
        state = {"live_synced": True, "dropped_free_agents": ["Owned Player"]}
        ids, audit = free_agent_ids(self.assistant, state, {}, self.now)
        self.assertFalse(ids)
        self.assertIn("withheld", audit["reason"])

    def test_partial_available_page_is_usable_but_current_ownership_wins(self):
        ids, audit = free_agent_ids(self.assistant, self.snapshot(), {0: [1]}, self.now)
        self.assertEqual(ids, {2, 3})
        self.assertFalse(audit["scan_complete"])

    def test_stale_or_untrusted_available_evidence_is_rejected(self):
        for change in (
            {"updated_at": (self.now - timedelta(hours=25)).isoformat()},
            {"updated_at": (self.now + timedelta(minutes=10)).isoformat()},
            {"source": "inferred_from_rosters"},
        ):
            state = self.snapshot()
            state["availability_snapshot"].update(change)
            self.assertFalse(free_agent_ids(self.assistant, state, {}, self.now)[0])

    def test_mixed_sync_versions_withhold_candidates(self):
        state = self.snapshot()
        state["sync_id"] = "new"
        state["availability_snapshot"]["sync_id"] = "old"
        self.assertFalse(free_agent_ids(self.assistant, state, {}, self.now)[0])

    def test_owned_yahoo_id_wins_even_when_roster_name_is_an_alias(self):
        state = self.snapshot()
        state["availability_snapshot"]["players"] = [
            {"name": "Verified Free Agent", "status": "FA", "yahoo_player_id": "123"}
        ]
        state["yahoo_roster_players"] = {"0": [{"name": "Other Alias", "yahoo_player_id": "123"}]}
        self.assertFalse(free_agent_ids(self.assistant, state, {}, self.now)[0])

    def test_browser_does_not_pad_missing_roster_rows_or_invent_free_agents(self):
        names = draft_data.build_rosters()[4]
        names = [n for n in names if n != "Nickeil Alexander-Walker"]
        payload = {"rosters_by_slot": {"4": [{"name": n} for n in names]}}
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            with patch("src.yahoo_browser_sync.PROCESSED_DIR", tmp), patch("threading.Thread"):
                apply_browser_sync_payload(payload)
            state = json.loads((Path(tmp) / "league_state.json").read_text())
        self.assertEqual(state["rosters"]["4"], names)
        self.assertNotIn("dropped_free_agents", state)
        self.assertFalse(state["availability_snapshot"]["players"])

    def matchup(self):
        stats = {
            "FGM": 12,
            "FGA": 30,
            "FTM": 6,
            "FTA": 8,
            "FG3M": 3,
            "PTS": 33,
            "REB": 20,
            "AST": 9,
            "STL": 3,
            "BLK": 2,
            "TOV": 4,
            "games_played": 7,
            "games_remaining": 34,
            "total_scheduled": 41,
        }
        return {
            "team_a": {**stats, "yahoo_team_id": 2, "name": "Other Team"},
            "team_b": {**stats, "yahoo_team_id": 10, "name": "My Renamed Team"},
        }

    def test_matchup_yahoo_registration_order_is_mapped_and_own_team_oriented(self):
        matchup = self.matchup()
        result = validate_browser_matchup(matchup, {"1": "12", "9": "7"}, self.now)
        self.assertEqual(result["team_a"]["slot"], 8)
        self.assertEqual(result["team_b"]["slot"], 13)
        self.assertEqual(result["team_a"]["name"], "My Renamed Team")
        self.assertNotIn("slot", matchup["team_a"])

    def test_matchup_missing_counter_or_identity_does_not_get_fabricated_defaults(self):
        for key, value in (
            ("games_played", None),
            ("total_scheduled", 40),
            ("yahoo_team_id", 0),
            ("BLK", None),
            ("BLK", float("nan")),
        ):
            matchup = deepcopy(self.matchup())
            matchup["team_a"][key] = value
            with self.assertRaises(ValueError):
                validate_browser_matchup(matchup, {"1": "12", "9": "7"}, self.now)

    @unittest.skipUnless(shutil.which("node"), "Node unavailable for JavaScript parser fixture")
    def test_actual_bookmarklet_parser_skips_player_tables_and_preserves_columns(self):
        parser = BOOKMARKLET_JS_RAW.split("    function parseMatchupDoc(doc) {", 1)[1]
        parser = (
            "function parseMatchupDoc(doc) {"
            + parser.split("    function parseTransactionsDoc", 1)[0]
        )
        # Minimal DOM surface fixture: the production JavaScript, not a Python
        # translation, chooses between a player table and a matchup team table.
        fixture = r"""
const leagueId = '64691';
const location = {origin: 'https://basketball.fantasysports.yahoo.com'};
function row(name, teamId, blocks) {
  const cells = [name,'20/50','.400','8/10','.800','5','53','22','12','3',String(blocks),'4'];
  return {
    querySelectorAll: () => cells.map(textContent => ({textContent})),
    querySelector: () => teamId ? {
      textContent: name, getAttribute: () => '/nba/64691/' + teamId
    } : null
  };
}
function table(rows) {
  return {querySelectorAll: selector => selector.includes('thead') ?
    ['FGM/A','FG%','FTM/A','FT%','3PTM','PTS','REB','AST','ST','BLK','TO'].map(textContent => ({textContent})) : rows};
}
const tables = [table([row('Player One', null, 99), row('Player Two', null, 88)]),
                table([row('My Renamed Team', 10, 6), row('Other Team', 2, 16)])];
function doc(text) { return {body:{innerText:text}, querySelectorAll:()=>tables}; }
const valid = parseMatchupDoc(doc('32 Remaining 12 / 44 Games Played 14 / 42 Remaining 28'));
const missing = parseMatchupDoc(doc('Counters are not present'));
process.stdout.write(JSON.stringify({valid, missing}));
"""
        result = subprocess.run(
            [shutil.which("node"), "-e", parser + fixture],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        result = json.loads(result.stdout)
        self.assertEqual(result["valid"]["team_a"]["BLK"], 6)
        self.assertEqual(result["valid"]["team_b"]["BLK"], 16)
        self.assertEqual(result["valid"]["team_a"]["yahoo_team_id"], 10)
        self.assertEqual(result["valid"]["team_a"]["games_played"], 12)
        self.assertIsNone(result["missing"]["team_a"]["games_played"])


if __name__ == "__main__":
    unittest.main()

import json
import shutil
import subprocess
import unittest

import pandas as pd

from src.live_draft_assistant import LiveDraftAssistant
from src.matchup_engine import MatchupEngine
from src.notifications import render_telegram
from src.probability import CategoryProbabilities
from src.waivers import normalize_waiver, waiver_constraints
from src.yahoo_browser_sync import BOOKMARKLET_JS_RAW
from tests.helpers import player


class LiveRegressionTests(unittest.TestCase):
    def test_name_index_preserves_exact_partial_suffix_and_available_order(self):
        assistant = LiveDraftAssistant.__new__(LiveDraftAssistant)
        names = {1: "Gary Trent Jr.", 2: "Gary Harris", 3: "Nikola Vučević", 4: "Jalen Williams"}
        assistant.players = {i: player(i) for i in names}
        assistant.df_base = pd.DataFrame({"NAME": names})
        assistant.available_player_ids = {2, 3, 4}
        for query, available, expected in (
            ("Gary", False, 1),
            ("Gary", True, 2),
            ("Gary Trent", True, None),
            ("Gary Trent", False, 1),
            ("Nikola Vucevic", True, 3),
            ("4", True, 4),
            ("Jalen Williams\nPlayer Note", True, 4),
            ("Unknown", False, None),
        ):
            self.assertEqual(assistant.resolve_player_id(query, available), expected)
        assistant.available_player_ids.add(1)
        self.assertEqual(assistant.resolve_player_id("Gary", True), 1)
        assistant.df_base = assistant.df_base.iloc[::-1].copy()
        self.assertEqual(assistant.resolve_player_id("Gary", False), 2)

    def test_waiver_dates_normalize_without_guessing_ambiguous_locale(self):
        now = "2026-10-28T19:00Z"
        for raw in (
            "Off Waivers 30/10",
            "10/30",
            "2026-10-30",
            {"date": "2026-10-30", "display": "30/10"},
        ):
            self.assertEqual(normalize_waiver(raw, now)["date"], "2026-10-30")
        self.assertIsNone(normalize_waiver("Waiver", now)["date"])
        self.assertIsNone(normalize_waiver("03/04", now)["date"])
        self.assertEqual(normalize_waiver("13/01", "2026-12-30T19:00Z")["date"], "2027-01-13")

    def test_current_waiver_status_cannot_become_fa_when_date_missing(self):
        assistant = type("Assistant", (), {"resolve_player_id": lambda *a, **k: 1})()
        state = {"availability_snapshot": {"players": [{"name": "Jay Huff", "status": "W"}]}}
        info = waiver_constraints(assistant, state, "2026-10-28T19:00Z")
        self.assertIn(1, info)
        self.assertIsNone(info[1]["date"])
        state["waivers"] = {"Jay Huff": {"date": "2026-10-30"}}
        state["availability_snapshot"]["players"][0]["status"] = "FA"
        self.assertNotIn(1, waiver_constraints(assistant, state, "2026-10-28T19:00Z"))

    def test_telegram_keeps_waiver_clearance_visible(self):
        message = render_telegram(
            now=pd.Timestamp("2026-10-28T19:00Z"),
            opponent="Opponent",
            points=4.5,
            probabilities=CategoryProbabilities({"PTS": 0.5}),
            health=[],
            live={"team_a": {}, "team_b": {}},
            recommendations=[
                {
                    "add_name": "Jay Huff",
                    "drop_name": "Player",
                    "drop_id": 2,
                    "delta_objective_value": 0.1,
                    "is_waiver": True,
                    "waiver_display": "30/10",
                }
            ],
        )
        self.assertIn("Waiver talebi", message)
        self.assertIn("30/10", message)

    def test_waiver_evidence_restricts_engine_schedule_and_unknown_date_blocks_claim(self):
        players = {i: player(i) for i in (1, 2, 3)}
        engine = MatchupEngine(
            players,
            pd.DataFrame(
                {
                    "TEAM_ID": [10] * 4,
                    "GAME_DATE": pd.date_range("2026-10-28", periods=4),
                    "GAME_ID": ["g1", "g2", "g3", "g4"],
                }
            ),
            pd.DataFrame(),
            team_map={1: 10, 2: 10, 3: 10},
        )
        assistant = type("Assistant", (), {"resolve_player_id": lambda *a, **k: 3})()
        state = {
            "availability_snapshot": {
                "players": [{"name": "Claim Player", "status": "W", "waiver": "Off Waivers 30/10"}]
            }
        }
        constraints = waiver_constraints(assistant, state, "2026-10-28T19:00Z")
        moves = engine.recommend_add_drop_moves(
            [1], [2], [3], "2026-10-28", "2026-10-31", waivers_dict=constraints
        )
        self.assertEqual(len(moves), 1)
        self.assertEqual(moves[0]["rem_games_add"], 2)
        self.assertTrue(moves[0]["is_waiver"])
        state["availability_snapshot"]["players"][0]["waiver"] = "Waiver"
        self.assertEqual(
            engine.recommend_add_drop_moves(
                [1],
                [2],
                [3],
                "2026-10-28",
                "2026-10-31",
                waivers_dict=waiver_constraints(assistant, state, "2026-10-28T19:00Z"),
            ),
            [],
        )

    @unittest.skipUnless(shutil.which("node"), "Node unavailable")
    def test_production_parser_prioritizes_off_waivers_tooltip_over_add_button(self):
        parser = (
            "function parseAvailablePlayersDoc(doc, pageUrl=location.href) {"
            + BOOKMARKLET_JS_RAW.split(
                "function parseAvailablePlayersDoc(doc, pageUrl=location.href) {", 1
            )[1].split("// 1. Check current page", 1)[0]
        )
        fixture = r"""
const leagueId='64691', location={origin:'https://basketball.fantasysports.yahoo.com',href:'https://basketball.fantasysports.yahoo.com/nba/64691/players?status=A'};
function row(name, title) { return {
 textContent:name+' FA',
 querySelectorAll:()=>[{getAttribute:k=>k==='aria-label'?title:null}],
 querySelector:s=>s.startsWith('a[href*="/players/"')?{textContent:name,getAttribute:()=>'/nba/players/6617'}:s.includes('addplayer')?{}:null
}; }
const rows=[row('Jay Huff','Off Waivers 30/10'),row('Unknown Date','Off Waivers'),row('Free Player','Add player')];
const doc={querySelectorAll:s=>s==='table tbody tr'?rows:[]};
process.stdout.write(JSON.stringify(parseAvailablePlayersDoc(doc)));
"""
        result = subprocess.run(
            [shutil.which("node"), "-e", parser + fixture],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        parsed = json.loads(result.stdout)
        self.assertEqual([p["status"] for p in parsed["players"]], ["W", "W", "FA"])
        self.assertEqual(parsed["waivers"]["Jay Huff"], "30/10")

    @unittest.skipUnless(shutil.which("node"), "Node unavailable")
    def test_page_scheduler_is_bounded_and_failed_page_keeps_scan_partial(self):
        code = BOOKMARKLET_JS_RAW.split("    let waivers = {}, availablePlayers", 1)[1]
        code = "let waivers = {}, availablePlayers" + code.split("// 4. Send", 1)[0]
        fixture = r"""
async function run(fail) {
 const location={origin:'https://basketball.fantasysports.yahoo.com'}, leagueId='64691';
 const parser={parseFromString:JSON.parse}, captureMetrics={rosters_ms:0,matchup_ms:0}, syncStarted=performance.now();
 let active=0, maximum=0;
 const link=n=>location.origin+'/nba/64691/players?status=A&sort=OR&start='+n;
 async function fetch(url) {
   active++;maximum=Math.max(maximum,active);
   await new Promise(r=>setTimeout(r,2)); active--;
   const start=Number(new URL(url).searchParams.get('start')||0);
   return {ok:!(fail && start===50),text:async()=>JSON.stringify({
     waivers:{},players:[{name:'P'+start,status:'FA'}],rowCount:start===75?1:25,
     next:start===0?link(25):null, forward:start===0?[link(25),link(50),link(75),'https://evil.example/players?start=100']:[]})};
 }
 function parseAvailablePlayersDoc(doc){return doc;}
 BODY
 return {maximum,complete:availableScanComplete,pages:seenAvailablePages.size,players:availablePlayers.length};
}
Promise.all([run(false),run(true)]).then(result=>process.stdout.write(JSON.stringify(result)));
""".replace("BODY", code)
        result = subprocess.run(
            [shutil.which("node"), "-e", fixture],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        complete, failed = json.loads(result.stdout)
        self.assertGreaterEqual(complete["maximum"], 2)
        self.assertLessEqual(complete["maximum"], 4)
        self.assertEqual(complete["pages"], 4)
        self.assertTrue(complete["complete"])
        self.assertFalse(failed["complete"])
        self.assertEqual(failed["players"], 3)


if __name__ == "__main__":
    unittest.main()

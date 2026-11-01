"""Actual-opponent integration, source identity and missing-capture regressions."""

import copy
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd

from src.fantasy_calendar import calendar_view, merge_capture, resolve_trade_calendar
from src.future_outlook import build_future_outlook, report_lines
from src.settings import LeagueSettings
from src.trades import evaluate_trade
from src.yahoo_fixtures import capture_api_calendar
from src.yahoo_trade_sync import capture_api_stage5, normalize_stage5_capture, resolved_team_names
from tests.test_trades import bundle, context


def state_fixture():
    ctx = context()
    # Deliberately not Yahoo number minus one: provider 14 is canonical zero.
    mapping = {"14": "0", "2": "1", "9": "2", "7": "3"}
    capture = {
        "source": "yahoo_browser_schedule",
        "league_id": "64691",
        "season": "2026_27",
        "regular_season_end_week": 3,
        "weeks": [
            {
                "week": 1,
                "start": "2026-10-26",
                "end": "2026-11-01",
                "fixtures": [["14", "2"], ["9", "7"]],
            },
            {
                "week": 2,
                "start": "2026-11-02",
                "end": "2026-11-08",
                "fixtures": [["14", "2"], ["9", "7"]],
            },
            {
                "week": 3,
                "start": "2026-11-09",
                "end": "2026-11-15",
                "fixtures": [["14", "9"], ["2", "7"]],
            },
        ],
    }
    calendar, audit = merge_capture(None, capture, "64691", mapping, ctx.as_of.isoformat())
    assert audit["accepted_weeks"] == 3
    state = {"league_id": "64691", "yahoo_team_slots": mapping, "fantasy_calendar": calendar}
    return ctx, state, capture


class FantasyCalendarTest(unittest.TestCase):
    def evidence_fixture(self):
        from types import SimpleNamespace

        ctx = context()
        assistant = SimpleNamespace(
            players=ctx.engine.players,
            pos_dict={1: "PF,C"},
            resolve_player_id=lambda name, **_: next(
                (p for p, v in ctx.engine.players.items() if v.name == name), None
            ),
        )
        item = {
            "name": "Player 1",
            "yahoo_player_id": "101",
            "status": "HEALTHY",
            "status_evidence": "yahoo_row_no_injury_badge",
            "eligible_positions": ["C"],
            "captured_at": (ctx.as_of - timedelta(hours=1)).isoformat(),
        }
        state = {
            "rosters": {"0": ["Player 1"]},
            "yahoo_roster_players": {"0": [item]},
            "roster_captured_at": item["captured_at"],
        }
        return ctx, assistant, state, item

    def test_verified_yahoo_healthy_clears_older_injury_and_preserves_nba_role_positions(self):
        from src.yahoo_player_evidence import apply_yahoo_roster_evidence

        ctx, assistant, state, _ = self.evidence_fixture()
        player = assistant.players[1]
        player.update_injury_status(
            "QUESTIONABLE",
            expected_return="2026-11-03",
            report_date=(ctx.as_of - timedelta(hours=2)).isoformat(),
        )
        result = apply_yahoo_roster_evidence(assistant, state, ctx.as_of)
        self.assertEqual(player.injury_status, "HEALTHY")
        self.assertIsNone(player.expected_return)
        self.assertEqual(result["positions"][1], "C")
        self.assertEqual(assistant.pos_dict[1], "PF,C")
        self.assertEqual(result["players"][1]["model_status_source"], "yahoo_roster")
        self.assertTrue(result["players"][1]["yahoo_status_verified"])

    def test_newer_injury_observation_wins_and_legacy_missing_health_proof_does_not_clear(self):
        from src.yahoo_player_evidence import apply_yahoo_roster_evidence

        ctx, assistant, state, item = self.evidence_fixture()
        player = assistant.players[1]
        player.update_injury_status(
            "QUESTIONABLE", report_date=(ctx.as_of - timedelta(minutes=10)).isoformat()
        )
        result = apply_yahoo_roster_evidence(assistant, state, ctx.as_of)
        self.assertEqual(player.injury_status, "QUESTIONABLE")
        self.assertEqual(result["players"][1]["model_status_source"], "injury_cache")
        player.update_injury_status(
            "QUESTIONABLE", report_date=(ctx.as_of - timedelta(hours=2)).isoformat()
        )
        item.pop("status_evidence")
        result = apply_yahoo_roster_evidence(assistant, state, ctx.as_of)
        self.assertEqual(player.injury_status, "QUESTIONABLE")
        self.assertFalse(result["players"][1]["yahoo_status_verified"])
        self.assertTrue(result["players"][1]["needs_yahoo_refresh"])

    def test_stale_or_unknown_roster_status_never_becomes_healthy_and_digest_tracks_model(self):
        from src.yahoo_player_evidence import apply_yahoo_roster_evidence

        ctx, assistant, state, item = self.evidence_fixture()
        assistant.players[1].update_injury_status(
            "OUT", report_date=(ctx.as_of - timedelta(hours=3)).isoformat()
        )
        item["captured_at"] = (ctx.as_of - timedelta(hours=25)).isoformat()
        result = apply_yahoo_roster_evidence(assistant, state, ctx.as_of)
        self.assertEqual(result["positions"][1], "PF,C")
        self.assertEqual(assistant.players[1].injury_status, "OUT")
        first = result["sha256"]
        assistant.players[1].update_injury_status(
            "QUESTIONABLE", report_date=(ctx.as_of - timedelta(minutes=2)).isoformat()
        )
        self.assertNotEqual(
            first, apply_yahoo_roster_evidence(assistant, state, ctx.as_of)["sha256"]
        )
        item.update(
            captured_at=ctx.as_of.isoformat(),
            status="UNKNOWN",
            status_evidence="unrecognized_badge",
        )
        self.assertEqual(
            apply_yahoo_roster_evidence(assistant, state, ctx.as_of)["players"][1]["model_status"],
            "QUESTIONABLE",
        )

    def test_roster_identity_normalizer_preserves_source_proofs_and_player_positions(self):
        from src.yahoo_identity import roster_player_evidence

        _, _, _, item = self.evidence_fixture()
        saved = roster_player_evidence({"0": [item]}, {"1": "0"})["0"][0]
        for field in ("status_evidence", "captured_at", "eligible_positions"):
            self.assertEqual(saved[field], item[field])

    def test_main_forecast_and_trade_require_provider_il_proof_but_preserve_stashes(self):
        from src.forecast import _apply_confirmed_il_evidence
        from src.trade_context import provider_il_eligible_ids
        from src.yahoo_player_evidence import apply_yahoo_roster_evidence

        ctx, assistant, state, item = self.evidence_fixture()
        state["rosters"]["0"] = [f"Player {pid}" for pid in range(1, 6)]
        fresh_out = {**item, "status": "OUT", "status_evidence": "yahoo_injury_badge"}
        model_only_out = {**item, "name": "Player 2", "yahoo_player_id": "102"}
        stale_out = {
            **fresh_out,
            "name": "Player 3",
            "yahoo_player_id": "103",
            "captured_at": (ctx.as_of - timedelta(hours=25)).isoformat(),
        }
        existing_stash = {
            **item,
            "name": "Player 5",
            "yahoo_player_id": "105",
            "selected_position": "IL+",
        }
        state["il_slots"] = {"0": ["Player 4"]}
        state["yahoo_roster_players"]["0"] = [
            fresh_out,
            model_only_out,
            stale_out,
            existing_stash,
        ]
        assistant.players[2].update_injury_status(
            "OUT", report_date=(ctx.as_of - timedelta(minutes=2)).isoformat()
        )
        observations = apply_yahoo_roster_evidence(assistant, state, ctx.as_of)["players"]
        self.assertEqual(assistant.players[2].injury_status, "OUT")
        _apply_confirmed_il_evidence(ctx.engine, assistant, state, observations)
        self.assertEqual(ctx.engine.yahoo_already_stashed_ids, {4, 5})
        self.assertEqual(ctx.engine.yahoo_il_eligible_ids, {1, 4, 5})
        self.assertEqual(
            ctx.engine.yahoo_il_eligible_ids,
            provider_il_eligible_ids(assistant, state, {4, 5}, observations),
        )
        for pid in range(1, 6):
            self.assertEqual(ctx.engine._is_il_eligible({"ID": pid}), pid in {1, 4, 5})

    def test_browser_parser_reads_player_centre_not_util_slot_and_does_not_miss_q(self):
        import ast
        import shutil
        import subprocess

        node = shutil.which("node")
        if not node:
            self.skipTest("Node required for reader parser regression")
        source = (Path(__file__).resolve().parents[1] / "src/yahoo_browser_sync.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        raw = next(
            n.value
            for n in tree.body
            if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "BOOKMARKLET_JS_RAW" for t in n.targets)
        )
        if (
            isinstance(raw, ast.Call)
            and isinstance(raw.func, ast.Attribute)
            and raw.func.attr == "strip"
        ):
            raw = raw.func.value
        script = ast.literal_eval(raw)
        function = script[
            script.index("    function parseRosterDoc") : script.index(
                "    function parseMatchupDoc"
            )
        ]
        harness = r"""
const assert=require('node:assert/strict'),fs=require('node:fs');eval(fs.readFileSync(0,'utf8'));
function doc(badge,meta=true){
 const label={textContent:'LAL - C',getAttribute:()=>null};
 const cell={textContent:meta?'Jaxson Hayes LAL - C':'Jaxson Hayes',getAttribute:()=>null,querySelectorAll:()=>meta?[label]:[]};
 const slot={textContent:'UTIL',getAttribute:()=> 'UTIL'};
 const tr={querySelector:s=>s.startsWith('td.pos')?slot:badge===null?null:{textContent:badge}};
 const link={textContent:'Jaxson Hayes',getAttribute:()=>'/nba/players/123',closest:s=>s==='tr'?tr:cell};
 return {querySelector:()=>null,querySelectorAll:()=>[link]};
}
let p=parseRosterDoc(doc(null),1).players[0];assert.deepEqual(p.eligible_positions,['C']);assert.equal(p.selected_position,'UTIL');assert.equal(p.status,'HEALTHY');assert.equal(p.status_evidence,'yahoo_row_no_injury_badge');
p=parseRosterDoc(doc('Q'),1).players[0];assert.equal(p.status,'Q');assert.equal(p.status_evidence,'yahoo_injury_badge');
p=parseRosterDoc(doc('unknown badge'),1).players[0];assert.equal(p.status,'UNKNOWN');
p=parseRosterDoc(doc(null,false),1).players[0];assert.equal(p.status,'UNKNOWN');assert.deepEqual(p.eligible_positions,[]);
"""
        result = subprocess.run(
            [node, "-e", harness], input=function, text=True, encoding="utf-8", capture_output=True
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_oauth_roster_retains_player_positions_and_positive_health_proof(self):
        from src.yahoo_draft_sync import YahooFantasyOAuthClient

        client = YahooFantasyOAuthClient.__new__(YahooFantasyOAuthClient)
        client.league_key = "466.l.64691"
        player = {
            "player_id": "101",
            "name": {"full": "Player 1"},
            "eligible_positions": [{"position": "C"}, {"position": "Util"}],
        }
        data = {
            "teams": {
                "count": 1,
                "0": {
                    "team": [
                        {"team_id": "1", "team_key": "466.l.64691.t.1", "name": "Team"},
                        {
                            "roster": {
                                "players": {
                                    "count": 1,
                                    "0": {
                                        "player": [
                                            player,
                                            {"selected_position": {"position": "UTIL"}},
                                        ]
                                    },
                                }
                            }
                        },
                    ]
                },
            }
        }
        client._api_get = Mock(return_value=data)
        result = client.fetch_league_rosters_and_il()["rosters_by_slot"][0][0]
        self.assertEqual(result["eligible_positions"], ["C", "UTIL"])
        self.assertEqual(result["selected_position"], "UTIL")
        self.assertEqual(result["status_evidence"], "yahoo_api_no_status")
        self.assertTrue(result["captured_at"])

    def test_stage5_pending_offer_uses_explicit_ownership_and_keeps_sent_received_direction(self):
        ctx, state, _ = state_fixture()
        raw = {
            "source": "yahoo_api_league",
            "league_id": "64691",
            "pending_offers": {
                "scan_complete": True,
                "offers": [
                    {
                        "offer_id": "466.l.64691.pt.3",
                        "status": "proposed",
                        "trader_team_key": "466.l.64691.t.2",
                        "tradee_team_key": "466.l.64691.t.14",
                        "players": [
                            {
                                "yahoo_player_id": "101",
                                "source_team_key": "466.l.64691.t.14",
                                "destination_team_key": "466.l.64691.t.2",
                            },
                            {
                                "yahoo_player_id": "103",
                                "source_team_key": "466.l.64691.t.2",
                                "destination_team_key": "466.l.64691.t.14",
                            },
                        ],
                    }
                ],
            },
        }
        saved = normalize_stage5_capture(state, raw, ctx.as_of.isoformat(), our_team="0")
        offer = saved["pending_offers_snapshot"]["offers"][0]
        self.assertEqual((offer["our_team"], offer["other_team"]), ("0", "1"))
        self.assertEqual(offer["give_yahoo_ids"], ["101"])
        self.assertEqual(offer["receive_yahoo_ids"], ["103"])
        self.assertEqual(offer["direction"], "received")
        raw["pending_offers"]["offers"][0]["players"][0]["source_team_key"] = "466.l.111.t.14"
        self.assertNotIn(
            "pending_offers_snapshot", normalize_stage5_capture(state, raw, our_team="0")
        )

    def test_stage5_failed_capture_does_not_freshen_or_erase_old_offers(self):
        ctx, state, _ = state_fixture()
        state["pending_offers_snapshot"] = {
            "captured_at": "2026-10-29T12:00:00Z",
            "offers": [{"offer_id": "old"}],
        }
        before = copy.deepcopy(state)
        updates = normalize_stage5_capture(
            state,
            {
                "source": "yahoo_browser_league",
                "league_id": "64691",
                "pending_offers": {"scan_complete": False, "reason": "unrecognized HTML"},
            },
        )
        self.assertNotIn("pending_offers_snapshot", updates)
        self.assertEqual(state, before)
        updates = normalize_stage5_capture(
            state,
            {
                "source": "yahoo_api_league",
                "league_id": "64691",
                "pending_offers": {"scan_complete": True, "offers": []},
            },
        )
        self.assertEqual(updates["pending_offers_snapshot"]["offers"], [])
        self.assertTrue(updates["pending_offers_snapshot"]["complete"])

    def test_stage5_category_standings_exclude_current_week(self):
        ctx, state, _ = state_fixture()
        raw = {
            "source": "yahoo_browser_league",
            "league_id": "64691",
            "standings": {
                "current_week": 2,
                "completed_through_week": 1,
                "records": {
                    provider: {"W": 5, "L": 3, "T": 1} for provider in state["yahoo_team_slots"]
                },
            },
        }
        saved = normalize_stage5_capture(state, raw, ctx.as_of.isoformat())
        self.assertEqual(saved["playoff_snapshot"]["standings"]["0"], {"W": 5, "L": 3, "T": 1})
        self.assertNotIn("current_scoreboard", saved["playoff_snapshot"])
        raw["standings"]["records"]["14"]["W"] += 1
        self.assertNotIn("playoff_snapshot", normalize_stage5_capture(state, raw))

    def test_stage5_generic_duplicate_team_titles_fall_back_to_actual_canonical_names(self):
        names = resolved_team_names({"team_names": {str(i): "NBA Fantasy 2025" for i in range(14)}})
        self.assertEqual(names["7"], "Berk's Best Team")
        self.assertEqual(len(set(names.values())), 14)
        self.assertEqual(
            resolved_team_names({"team_names": {"7": "Berk renamed"}})["7"], "Berk renamed"
        )

    def test_stage5_api_empty_verified_collection_differs_from_failure(self):
        client = Mock(league_key="466.l.64691", team_key="466.l.64691.t.14")
        client._api_get.side_effect = [{"transactions": {"count": 0}}, None]
        result = capture_api_stage5(client)
        self.assertEqual(result["pending_offers"], {"scan_complete": True, "offers": []})
        self.assertIn(
            "types=pending_trade;team_key=466.l.64691.t.14",
            client._api_get.call_args_list[0].args[0],
        )
        client._api_get.side_effect = [None, None]
        self.assertFalse(capture_api_stage5(client)["pending_offers"]["scan_complete"])

    def test_browser_persists_calendar_without_dispatch_and_legacy_capture_keeps_it(self):
        from src import yahoo_browser_sync as bridge

        ctx, state, capture = state_fixture()
        payload = {
            "league_id": "64691",
            "fantasy_calendar_capture": capture,
            "rosters_by_slot": {
                str(int(provider) - 1): [
                    {"name": f"Player {int(team) + 1}", "yahoo_player_id": str(101 + int(team))}
                ]
                for provider, team in state["yahoo_team_slots"].items()
            },
            "team_names_by_slot": {"13": "Berk's Best Team"},
        }
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(bridge, "PROCESSED_DIR", folder),
            patch.object(bridge, "run_cloud_sync") as cloud,
            patch("subprocess.run") as command,
        ):
            path = Path(folder) / "league_state.json"
            path.write_text(json.dumps(state), encoding="utf-8")
            outcome = bridge.apply_browser_sync_payload(payload, dispatch=False)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(outcome["fantasy_calendar_weeks"], 3)
            self.assertEqual(saved["fantasy_calendar"]["weeks"][1]["fixtures"][0], ["0", "1"])
            self.assertEqual(saved["team_names"]["0"], "Berk's Best Team")
            previous = copy.deepcopy(saved["fantasy_calendar"])
            del payload["fantasy_calendar_capture"]
            bridge.apply_browser_sync_payload(payload, dispatch=False)
            refreshed = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(refreshed["fantasy_calendar"], previous)
            cloud.assert_not_called()
            command.assert_not_called()

    def test_provider_mapping_and_current_partial_week_exclusion(self):
        ctx, state, _ = state_fixture()
        view = calendar_view(state, ctx.as_of)
        self.assertEqual(view["status"], "ready")
        self.assertEqual(view["current_week"]["week"], 1)
        self.assertEqual([w["week"] for w in view["weeks"]], [2, 3])
        self.assertEqual(view["weeks"][0]["fixtures"][0], ["0", "1"])
        self.assertTrue(view["complete_remaining_season"])

    def test_missing_capture_preserves_original_observation_times(self):
        ctx, state, _ = state_fixture()
        original = copy.deepcopy(state["fantasy_calendar"])
        saved, audit = merge_capture(
            original,
            None,
            "64691",
            state["yahoo_team_slots"],
            (ctx.as_of + timedelta(days=1)).isoformat(),
        )
        self.assertEqual(saved, original)
        self.assertEqual(audit["accepted_weeks"], 0)

    def test_bad_week_preserves_confirmed_version(self):
        ctx, state, capture = state_fixture()
        capture["weeks"] = [capture["weeks"][1]]
        capture["weeks"][0]["fixtures"] = [["14", "2"], ["14", "7"]]
        saved, audit = merge_capture(
            state["fantasy_calendar"],
            capture,
            "64691",
            state["yahoo_team_slots"],
            ctx.as_of.isoformat(),
        )
        self.assertEqual(saved, state["fantasy_calendar"])
        self.assertTrue(audit["errors"])

    def test_partial_update_does_not_freshen_unfetched_week(self):
        ctx, state, capture = state_fixture()
        old = state["fantasy_calendar"]["weeks"][2]["captured_at"]
        capture["weeks"] = capture["weeks"][:2]
        later = ctx.as_of + timedelta(days=1)
        saved, _ = merge_capture(
            state["fantasy_calendar"],
            capture,
            "64691",
            state["yahoo_team_slots"],
            later.isoformat(),
        )
        self.assertEqual(saved["weeks"][2]["captured_at"], old)
        self.assertEqual(saved["weeks"][1]["captured_at"], later.isoformat())

    def test_league_or_identity_change_is_rejected(self):
        ctx, state, _ = state_fixture()
        for mutation in ("league", "team"):
            wrong = copy.deepcopy(state)
            if mutation == "league":
                wrong["league_id"] = "111"
            else:
                wrong["yahoo_team_slots"]["14"] = "1"
            self.assertEqual(calendar_view(wrong, ctx.as_of)["status"], "unavailable")

    def test_no_calendar_has_no_synthetic_opponents(self):
        ctx = context()
        view = calendar_view({}, ctx.as_of)
        self.assertEqual(view["weeks"], [])
        self.assertEqual(view["status"], "unavailable")

    def test_gap_is_not_silently_skipped(self):
        ctx, state, _ = state_fixture()
        del state["fantasy_calendar"]["weeks"][1]
        view = calendar_view(state, ctx.as_of)
        self.assertEqual(view["status"], "partial")
        self.assertFalse(view["complete_remaining_season"])
        self.assertEqual(view["weeks"], [])

    def test_stale_or_future_capture_is_not_usable(self):
        ctx, state, _ = state_fixture()
        self.assertEqual(
            calendar_view(state, ctx.as_of - timedelta(hours=1))["status"], "unavailable"
        )
        state["fantasy_calendar"]["weeks"][1]["captured_at"] = (
            ctx.as_of - timedelta(days=8)
        ).isoformat()
        view = calendar_view(state, ctx.as_of)
        self.assertEqual(view["weeks"], [])
        self.assertIn(2, view["missing_weeks"])

    def test_two_week_period_uses_yahoo_boundary(self):
        ctx, state, capture = state_fixture()
        capture["weeks"][1]["end"] = "2026-11-15"
        capture["weeks"][2].update(start="2026-11-16", end="2026-11-22")
        saved, audit = merge_capture(
            None, capture, "64691", state["yahoo_team_slots"], ctx.as_of.isoformat()
        )
        self.assertEqual(audit["accepted_weeks"], 3)
        state["fantasy_calendar"] = saved
        self.assertEqual(calendar_view(state, ctx.as_of)["weeks"][0]["end"], "2026-11-15")

    def test_postseason_is_excluded_and_unknown_cutoff_is_unavailable(self):
        ctx, state, capture = state_fixture()
        capture["regular_season_end_week"] = 2
        saved, _ = merge_capture(
            None, capture, "64691", state["yahoo_team_slots"], ctx.as_of.isoformat()
        )
        self.assertEqual([w["week"] for w in saved["weeks"]], [1, 2])
        del capture["regular_season_end_week"]
        saved, audit = merge_capture(
            None, capture, "64691", state["yahoo_team_slots"], ctx.as_of.isoformat()
        )
        self.assertIsNone(saved)
        self.assertTrue(audit["errors"])

    def test_explicit_horizon_is_not_reported_as_full_season(self):
        ctx, state, _ = state_fixture()
        view = calendar_view(state, ctx.as_of, horizon=1)
        self.assertEqual(len(view["weeks"]), 1)
        self.assertFalse(view["complete_remaining_season"])
        for bad in (0, -1, True):
            with self.assertRaises(ValueError):
                LeagueSettings(future_fixture_weeks=bad)

    def test_trade_reuses_main_source_without_mutating_input(self):
        ctx, state, _ = state_fixture()
        ctx.fantasy_calendar = calendar_view(state, ctx.as_of)
        data = bundle()
        del data["weeks"]
        original = copy.deepcopy(data)
        resolved = resolve_trade_calendar(ctx, data)
        self.assertEqual(data, original)
        self.assertEqual(len(resolved["weeks"]), 2)  # Less than four remain in this season.
        self.assertEqual(resolved["calendar_source"]["source"], "yahoo_browser_schedule")
        result = evaluate_trade(ctx, data)
        self.assertEqual(result["calendar_source"]["season"], "2026_27")

    def test_trade_cannot_silently_shorten_incomplete_horizon(self):
        ctx, state, _ = state_fixture()
        del state["fantasy_calendar"]["weeks"][-1]
        ctx.fantasy_calendar = calendar_view(state, ctx.as_of)
        data = bundle()
        del data["weeks"]
        with self.assertRaisesRegex(ValueError, "requested trade horizon"):
            resolve_trade_calendar(ctx, data)

    def test_long_term_only_projects_real_remaining_opponents(self):
        ctx, state, _ = state_fixture()
        view = calendar_view(state, ctx.as_of)
        before = copy.deepcopy(ctx.engine.players[1].alphas)
        outlook = build_future_outlook(
            ctx.engine,
            ctx.rosters,
            "0",
            view,
            ctx.as_of,
            {"1": "Mordor Tulums", "2": "Philadelphia Sikers"},
        )
        self.assertEqual([w["opponent"] for w in outlook["weeks"]], ["1", "2"])
        self.assertNotIn("3", outlook["opponent_frequency"])
        self.assertEqual(ctx.engine.players[1].alphas, before)
        total = sum(w["expected_category_points"] for w in outlook["weeks"])
        self.assertAlmostEqual(outlook["aggregate"]["expected_category_points"], total)
        self.assertIn("Mordor Tulums", "\n".join(report_lines(outlook)))

    def test_change_to_unscheduled_team_cannot_change_long_term_value(self):
        ctx, state, _ = state_fixture()
        view = calendar_view(state, ctx.as_of)
        first = build_future_outlook(ctx.engine, ctx.rosters, "0", view, ctx.as_of)
        # Same NBA roster/roles; change only the fantasy ownership of a team we never face.
        changed = copy.deepcopy(ctx.rosters)
        changed["3"] = []
        second = build_future_outlook(ctx.engine, changed, "0", view, ctx.as_of)
        self.assertEqual(first["aggregate"], second["aggregate"])

    def test_future_injury_information_date_is_frozen_today(self):
        ctx, state, _ = state_fixture()
        view = calendar_view(state, ctx.as_of)
        seen = []
        real = type(ctx.engine).get_expected_weekly_distribution

        def record(engine, *args, **kwargs):
            seen.append(kwargs.get("as_of_date"))
            return real(engine, *args, **kwargs)

        with patch.object(type(ctx.engine), "get_expected_weekly_distribution", record):
            build_future_outlook(ctx.engine, ctx.rosters, "0", view, ctx.as_of)
        self.assertTrue(seen)
        self.assertEqual(set(seen), {pd.Timestamp("2026-10-30")})

    def test_api_capture_uses_provider_dates_and_stops_before_playoffs(self):
        client = Mock()
        client.league_key = "466.l.64691"
        client._api_get.side_effect = [
            {"league": [{"season": "2026", "current_week": "1"}]},
            {"settings": [{"uses_playoff": "1", "playoff_start_week": "3"}]},
        ]

        def board(week):
            return {
                "week": week,
                "week_verified": True,
                "matchups": [[{"slot": 14}, {"slot": 2}]],
                "matchup_states": [
                    {
                        "week_start": "2026-10-26" if week == 1 else "2026-11-02",
                        "week_end": "2026-11-01" if week == 1 else "2026-11-08",
                    }
                ],
            }

        client.fetch_live_scoreboard.side_effect = board
        capture = capture_api_calendar(client)
        self.assertEqual([w["week"] for w in capture["weeks"]], [1, 2])
        self.assertEqual(capture["weeks"][1]["fixtures"], [["14", "2"]])
        self.assertEqual(client.fetch_live_scoreboard.call_count, 2)

    def test_api_does_not_relabel_unverified_week_or_invent_missing_dates(self):
        for verified, end in ((False, "2026-11-08"), (True, None)):
            client = Mock(league_key="466.l.64691")
            client._api_get.side_effect = [
                {"league": [{"season": "2026", "current_week": "2"}]},
                {"settings": [{"uses_playoff": "1", "playoff_start_week": "3"}]},
            ]
            client.fetch_live_scoreboard.return_value = {
                "week": 2,
                "week_verified": verified,
                "matchups": [[{"slot": 14}, {"slot": 2}]],
                "matchup_states": [{"week_start": "2026-11-02", "week_end": end}],
            }
            self.assertEqual(capture_api_calendar(client)["weeks"], [])


if __name__ == "__main__":
    unittest.main()

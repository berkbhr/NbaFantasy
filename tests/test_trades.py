"""Trade counterfactual and calendar regressions, with no network or user caches."""

import copy
import pickle
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.bayesian_model import BayesianPlayer
from src.matchup_engine import MatchupEngine
from src.trade_context import TradeContext
from src.trade_report import render_trade_report
from src.trades import evaluate_trade, main


def context(equal=False):
    players = {}
    for pid in range(1, 9):
        p = BayesianPlayer(pid, f"Player {pid}")
        p.initialize_priors(
            {
                "MIN": 2100,
                "GP": 70,
                "PTS": 1400 if equal else 700 + 100 * pid,
                "REB": 600,
                "AST": 250,
                "STL": 70,
                "BLK": 50,
                "TOV": 150,
                "FG3M": 100,
                "FGM": 550,
                "FGA": 1100,
                "FTM": 200,
                "FTA": 250,
            }
        )
        p.expected_minutes = p.base_expected_minutes = 30
        players[pid] = p
    schedule = pd.DataFrame(
        [
            {"TEAM_ID": pid, "GAME_DATE": pd.Timestamp(date), "GAME_ID": f"{pid}-{date}"}
            for pid in players
            for date in (
                "2026-11-02",
                "2026-11-04",
                "2026-11-08",
                "2026-11-09",
                "2026-11-11",
                "2026-11-15",
            )
        ]
    )
    engine = MatchupEngine(
        players,
        schedule,
        pd.DataFrame([{"PLAYER_ID": p, "POSITION": "PG,SG,SF,PF,C"} for p in players]),
        team_map={p: p for p in players},
        use_positional_depth_and_injury_boost=False,
        yahoo_il_eligible_ids=set(),
    )
    now = datetime(2026, 10, 30, 12, tzinfo=timezone.utc)
    return TradeContext(
        engine,
        {"0": [1, 2], "1": [3, 4], "2": [5, 6], "3": [7, 8]},
        {str(100 + p): p for p in players},
        now,
        "test-sync",
        now,
        [],
        {},
    )


def bundle():
    return {
        "proposal": {
            "our_team": "0",
            "other_team": "1",
            "snapshot_id": "test-sync",
            "give_yahoo_ids": [101],
            "receive_yahoo_ids": [103],
            "effective_date": "2026-11-01",
        },
        "rules": {"verified": False},
        "calendar_verified": True,
        "eligible_positions": {str(100 + p): ["PG", "SG", "SF", "PF", "C"] for p in range(1, 9)},
        "regular_season_end": "2026-11-15",
        "weeks": [
            {"start": "2026-11-02", "end": "2026-11-08", "fixtures": [["0", "1"], ["2", "3"]]},
            {"start": "2026-11-09", "end": "2026-11-15", "fixtures": [["0", "2"], ["1", "3"]]},
        ],
    }


def full_context():
    ctx = context()
    prototype = ctx.engine.players[1]
    for pid in range(1, 31):
        player = copy.deepcopy(prototype)
        player.name = f"Real roster slot {pid}"
        # A productive trade target and FA make pickup comparisons observable.
        multiplier = 1 + pid / 100
        if pid in (14, 29):
            multiplier = 3
        for cat in ("PTS", "REB", "AST", "STL", "BLK", "FG3M"):
            player.alphas[cat] *= multiplier
        ctx.engine.players[pid] = player
        ctx.engine.team_map[pid] = 1
        ctx.engine.pos_dict[pid] = "PG,SG,SF,PF,C"
    ctx.rosters = {"0": list(range(1, 14)), "1": list(range(14, 27)), "2": [27], "3": [28]}
    ctx.yahoo_ids = {str(100 + p): p for p in ctx.engine.players}
    ctx.available_players = {29: {"status": "FA", "waiver": None, "yahoo_player_id": "129"}}
    ctx.availability_audit = {
        "source": "yahoo_available_players",
        "sync_id": ctx.sync_id,
        "updated_at": ctx.as_of.isoformat(),
        "scan_complete": True,
    }
    return ctx


def uneven_bundle():
    data = bundle()
    data["proposal"].update(give_yahoo_ids=[101, 102], receive_yahoo_ids=[114])
    data["eligible_positions"] = {str(100 + p): ["PG", "SG", "SF", "PF", "C"] for p in range(1, 31)}
    data["completion"] = {
        "enabled": True,
        "min_gain_per_week": 0.001,
        "adds_used_by_week": {"2026-11-02": {"0": 0}},
    }
    return data


def protected_slot_scenario(protect_all=True):
    """Controlled 2-for-1: equal production, locked roster, one off-day pickup.

    Names are real; ownership, schedules, rate parameters and FA evidence are
    synthetic test fixtures. This is not a replay of the user's league.
    """
    ctx, data = full_context(), uneven_bundle()
    our_names = [
        "Desmond Bane",
        "Jarrett Allen",
        "Tyrese Maxey",
        "Ayo Dosunmu",
        "Jake LaRavia",
        "Precious Achiuwa",
        "Josh Hart",
        "Jabari Smith Jr.",
        "Neemias Queta",
        "Julian Champagnie",
        "Dean Wade",
        "James Harden",
        "Jaxson Hayes",
    ]
    partner_names = [
        "Lauri Markkanen",
        "Darius Garland",
        "Immanuel Quickley",
        "Trae Young",
        "Jalen Green",
        "Jonathan Kuminga",
        "De'Andre Hunter",
        "Alex Sarr",
        "Toumani Camara",
        "Luka Dončić",
        "Bennedict Mathurin",
        "Jerami Grant",
        "Joan Beringer",
    ]
    prototype = copy.deepcopy(ctx.engine.players[1])
    players, rows = {}, []
    for pid in range(1, 31):
        p = copy.deepcopy(prototype)
        p.name = (
            our_names[pid - 1]
            if pid <= 13
            else partner_names[pid - 14]
            if pid <= 26
            else {
                27: "Victor Wembanyama",
                28: "Nikola Jokić",
                29: "Luke Kennard",
                30: "Norman Powell",
            }[pid]
        )
        multiplier = 2 if pid == 14 else 3 if pid == 29 else 1
        for cat in ("PTS", "REB", "AST", "STL", "BLK", "TOV", "FG3M"):
            p.alphas[cat] *= multiplier
        for cat in ("FG", "FT"):
            p.att_alphas[cat] *= multiplier
        players[pid] = p
        if pid in (1, 2, 14):
            dates = ("2026-11-02", "2026-11-04", "2026-11-06")
        elif 3 <= pid <= 12 or 15 <= pid <= 24:
            dates = ("2026-11-03", "2026-11-05")
        elif pid in (27, 28):
            dates = ("2026-11-02", "2026-11-08")
        elif pid == 29:
            dates = ("2026-11-08",)
        else:
            dates = ()
        rows += [
            {
                "TEAM_ID": 1000 + pid,
                "GAME_DATE": pd.Timestamp(date),
                "GAME_ID": f"controlled-{pid}-{date}",
            }
            for date in dates
        ]
    ctx.engine = MatchupEngine(
        players,
        pd.DataFrame(rows),
        pd.DataFrame([{"PLAYER_ID": pid, "POSITION": "PG,SG,SF,PF,C"} for pid in players]),
        team_map={pid: 1000 + pid for pid in players},
        yahoo_il_eligible_ids=set(),
        use_positional_depth_and_injury_boost=False,
    )
    ctx.team_names = {
        "0": "Berk's Best Team",
        "1": "Philadelphia Sikers",
        "2": "Mordor Tulums",
        "3": "MuCa Tandır",
    }
    ctx.sync_id = "synthetic-protected-slot"
    ctx.availability_audit["sync_id"] = ctx.sync_id
    ctx.warnings = [
        "Controlled test: real names, synthetic ownership, forecasts, fixtures and FA evidence."
    ]
    data["proposal"]["snapshot_id"] = ctx.sync_id
    data["regular_season_end"] = None
    data["weeks"] = data["weeks"][:1]
    data["calendar_verified"] = False
    data["do_not_drop_yahoo_ids"] = [100 + p for p in ctx.rosters["0"]] if protect_all else [113]
    data["drop_yahoo_ids"] = {"1": [126]}
    data["completion"]["min_gain_per_week"] = 0.05
    return ctx, data


class TradesTest(unittest.TestCase):
    def test_cli_writes_roundtrip_artifacts_only_to_requested_folder(self):
        import json

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "proposal.json"
            input_path.write_text(json.dumps(bundle()), encoding="utf-8")
            with (
                patch("sys.argv", ["trades", str(input_path), "--output", str(root / "out")]),
                patch("src.trades.load_context", return_value=context()),
                patch("builtins.print"),
            ):
                main()
            artifact = next((root / "out").glob("*.json"))
            result = json.loads(artifact.read_text(encoding="utf-8"))
            self.assertEqual(result["sync_id"], "test-sync")
            self.assertEqual(len(list((root / "out").glob("*.md"))), 1)
            self.assertEqual(json.loads(input_path.read_text(encoding="utf-8")), bundle())

    def test_percentages_use_volume_and_turnovers_keep_favorable_direction(self):
        ctx = context(equal=True)
        ctx.engine.players[1].alphas["TOV"] *= 3
        # Same make percentage, unequal shot volume: the team ratio must not be
        # the unweighted average of its players' percentages.
        ctx.engine.players[3].alphas["FG"] *= 3
        ctx.engine.players[3].att_alphas["FG"] *= 3
        result = evaluate_trade(ctx, bundle())
        week = result["teams"]["0"]["weekly"][0]
        self.assertGreater(
            week["after"]["categories"]["TOV"]["win"], week["before"]["categories"]["TOV"]["win"]
        )
        self.assertGreater(
            week["after"]["categories"]["FG_PCT"]["production"],
            week["before"]["categories"]["FG_PCT"]["production"],
        )
        diagnostic = result["normalized_package"]["incoming"]
        self.assertGreater(diagnostic["FGM"] / diagnostic["FGA"], 0.5)

    def test_confirmed_rules_require_explicit_fields(self):
        data = bundle()
        data["rules"]["verified"] = True
        with self.assertRaises(ValueError):
            evaluate_trade(context(), data)

    def test_identical_players_zero_delta_and_immutable_context(self):
        ctx = context(equal=True)
        original = pickle.dumps(ctx)
        result = evaluate_trade(ctx, bundle())
        self.assertAlmostEqual(result["teams"]["0"]["all_supplied_weeks"]["delta"], 0)
        self.assertEqual(pickle.dumps(ctx), original)
        self.assertEqual(result, evaluate_trade(ctx, bundle()))

    def test_both_sides_and_categories_reconcile(self):
        ctx = context()
        ctx.team_names = {"0": "Berk's Best Team", "1": "MuCa Tandır", "2": "Mordor Tulums"}
        ctx.engine.players[1].name = "Desmond Bane"
        ctx.engine.players[3].name = "Evan Mobley"
        result = evaluate_trade(ctx, bundle())
        a = result["teams"]["0"]["weekly"][0]
        b = result["teams"]["1"]["weekly"][0]
        for state in ("before", "after"):
            self.assertAlmostEqual(a[state]["points"] + b[state]["points"], 9)
        for team in result["teams"].values():
            aggregate = team["all_supplied_weeks"]
            self.assertAlmostEqual(
                sum(c["delta_points"] for c in aggregate["categories"].values()), aggregate["delta"]
            )
        self.assertEqual(result["teams"]["0"]["weekly"][1]["opponent"], "2")
        self.assertIn("FG_PCT", render_trade_report(result))
        report = render_trade_report(result)
        self.assertIn("Berk's Best Team", report)
        self.assertIn("MuCa Tandır", report)
        self.assertIn("rakip: Mordor Tulums", report)
        self.assertIn("Desmond Bane", report)
        self.assertIn("Evan Mobley", report)
        self.assertNotIn("Yahoo", report)
        self.assertNotIn("Takım 0", report)

    def test_reversing_perspective_preserves_team_results(self):
        original = evaluate_trade(context(), bundle())
        reverse = bundle()
        reverse["proposal"].update(
            our_team="1", other_team="0", give_yahoo_ids=[103], receive_yahoo_ids=[101]
        )
        flipped = evaluate_trade(context(), reverse)
        self.assertEqual(original["teams"], flipped["teams"])

    def test_future_opponent_roster_changes_affect_us(self):
        ctx = context()
        same = copy.deepcopy(ctx)
        same.engine.players[5].alphas["PTS"] *= 4
        a = evaluate_trade(ctx, bundle())["teams"]["0"]["weekly"]
        b = evaluate_trade(same, bundle())["teams"]["0"]["weekly"]
        self.assertEqual(a[0], b[0])
        self.assertNotEqual(a[1], b[1])

    def test_rejects_wrong_owner_duplicates_and_unsupported_package(self):
        for change in (
            {"give_yahoo_ids": [105]},
            {"give_yahoo_ids": [101, 101], "receive_yahoo_ids": [103, 104]},
            {"give_yahoo_ids": [101, 102, 103]},
            {"snapshot_id": "stale"},
        ):
            data = bundle()
            data["proposal"].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                evaluate_trade(context(), data)

    def test_calendar_and_timing_gates(self):
        variants = []
        data = bundle()
        data["weeks"][0]["fixtures"] = [["0", "1"], ["0", "2"]]
        variants.append(data)
        data = bundle()
        data["proposal"]["effective_date"] = "2026-11-03"
        variants.append(data)
        data = bundle()
        data["weeks"][0]["start"] = "2026-10-30"
        variants.append(data)
        data = bundle()
        data["rules"]["review_days"] = 5
        variants.append(data)
        for data in variants:
            with self.subTest(data=data), self.assertRaises(ValueError):
                evaluate_trade(context(), data)

    def test_two_for_two_protection_and_stash(self):
        data = bundle()
        data["proposal"].update(give_yahoo_ids=[101, 102], receive_yahoo_ids=[103, 104])
        evaluate_trade(context(), data)
        data["do_not_trade_yahoo_ids"] = [101]
        with self.assertRaises(ValueError):
            evaluate_trade(context(), data)
        ctx = context()
        ctx.engine.yahoo_already_stashed_ids.add(1)
        with self.assertRaises(ValueError):
            evaluate_trade(ctx, bundle())

    def test_unknown_inputs_stay_conditional_and_playoff_counts(self):
        data = bundle()
        data.pop("eligible_positions")
        data.pop("regular_season_end")
        data["rules"]["verified"] = False
        data["playoff_periods"] = [{"start": "2026-11-09", "end": "2026-11-15"}]
        result = evaluate_trade(context(), data)
        self.assertTrue(any("eligibility" in c for c in result["conditions"]))
        self.assertTrue(any("rules" in c for c in result["conditions"]))
        self.assertEqual(result["coverage"], "supplied_weeks_only")
        self.assertEqual(result["playoff_schedule"][0]["scheduled_games"]["1"], 3)
        self.assertNotIn("playoff_probability", result)


class TradePackagesTest(unittest.TestCase):
    def test_protected_slot_trade_plus_fa_report(self):
        ctx, data = protected_slot_scenario()
        original = pickle.dumps(ctx)
        result = evaluate_trade(ctx, data)
        self.assertEqual(pickle.dumps(ctx), original)
        self.assertAlmostEqual(result["teams"]["0"]["all_supplied_weeks"]["delta"], 0, places=9)
        self.assertEqual(result["decision"]["basis"], "trade_plus_fa")
        self.assertEqual(result["verdict"], "conditional_accept")
        option = result["completion"]["options"][0]
        self.assertIsNone(option["baseline_actions"])
        self.assertEqual(option["baseline_drops"], [])
        self.assertGreater(option["robust_delta"], 0.05)
        self.assertAlmostEqual(
            option["baseline_category_points"], result["teams"]["0"]["all_supplied_weeks"]["before"]
        )
        self.assertAlmostEqual(result["decision"]["delta"], option["delta"])
        report = render_trade_report(result)
        for text in (
            "Koşullu kabul",
            "Luke Kennard",
            "Berk's Best Team",
            "Philadelphia Sikers",
            "Takassız referans mevcut kadrosunu koruyor.",
            "takas + aşağıda adı verilen FA",
        ):
            self.assertIn(text, report)
        self.assertNotIn("Yahoo ID", report)

    def test_protected_slot_only_thirteenth_player_does_not_block_other_drops(self):
        ctx, data = protected_slot_scenario(protect_all=False)
        result = evaluate_trade(ctx, data)
        option = result["completion"]["options"][0]
        self.assertIsNotNone(option["baseline_actions"])
        self.assertTrue(option["baseline_drops"])
        self.assertNotIn(13, option["baseline_drops"])

    def test_two_for_one_required_drop_is_explicit_and_directly_reproducible(self):
        ctx, data = full_context(), uneven_bundle()
        data["completion"]["enabled"] = False
        result = evaluate_trade(ctx, data)
        dropped = result["roster_actions"]["drops"]["1"]
        self.assertEqual(len(dropped), 1)
        self.assertNotIn(14, dropped)  # The player traded away cannot also be dropped.
        data["drop_yahoo_ids"] = {"1": [100 + dropped[0]]}
        explicit = evaluate_trade(ctx, data)
        self.assertEqual(result["teams"], explicit["teams"])
        report = render_trade_report(result)
        self.assertIn(ctx.engine.players[dropped[0]].name, report)
        self.assertIn("Zorunlu kadro", report)

    def test_one_for_two_and_protected_drop(self):
        ctx, data = full_context(), uneven_bundle()
        data["completion"]["enabled"] = False
        data["proposal"].update(
            give_yahoo_ids=[114], receive_yahoo_ids=[101, 102], our_team="1", other_team="0"
        )
        result = evaluate_trade(ctx, data)
        self.assertEqual(len(result["roster_actions"]["drops"]["1"]), 1)
        data["do_not_drop_yahoo_ids"] = [100 + p for p in list(range(15, 27)) + [1, 2]]
        with self.assertRaises(ValueError):
            evaluate_trade(ctx, data)

    def test_il_transfer_needs_verified_eligibility_and_no_duplicate_stash(self):
        ctx, data = full_context(), uneven_bundle()
        ctx.rosters["0"].append(27)
        ctx.rosters["2"] = []
        ctx.engine.yahoo_already_stashed_ids.add(27)
        ctx.il_eligible_ids.add(27)
        data["proposal"].update(give_yahoo_ids=[127], receive_yahoo_ids=[114])
        data["post_trade_il_yahoo_ids"] = {"0": [], "1": [127]}
        result = evaluate_trade(ctx, data)
        self.assertEqual(result["roster_actions"]["post_trade_il"]["1"], [27])
        for week in result["teams"]["1"]["weekly"]:
            self.assertTrue(all(27 not in ids for ids in week["after"]["lineups"].values()))
        data["post_trade_il_yahoo_ids"]["1"] = [101]
        with self.assertRaises(ValueError):
            evaluate_trade(ctx, data)

    def test_il_capacity_and_explicit_drop_ownership(self):
        ctx, data = full_context(), uneven_bundle()
        data["drop_yahoo_ids"] = {"1": [101, 102]}
        with self.assertRaises(ValueError):
            evaluate_trade(ctx, data)
        data.pop("drop_yahoo_ids")
        data["post_trade_il_yahoo_ids"] = {"0": [103, 104, 105]}
        ctx.il_eligible_ids.update((3, 4, 5))
        with self.assertRaises(ValueError):
            evaluate_trade(ctx, data)

    def test_completion_has_fair_baseline_and_preserves_context(self):
        ctx, data = full_context(), uneven_bundle()
        original = pickle.dumps(ctx)
        result = evaluate_trade(ctx, data)
        self.assertEqual(pickle.dumps(ctx), original)
        self.assertTrue(result["completion"]["options"])
        option = result["completion"]["options"][0]
        self.assertEqual(option["baseline_actions"]["player_id"], 29)
        self.assertEqual(len(option["baseline_drops"]), 1)
        self.assertAlmostEqual(
            option["delta"], option["after_category_points"] - option["baseline_category_points"]
        )
        self.assertAlmostEqual(option["teams"]["0"]["all_supplied_weeks"]["delta"], option["delta"])
        self.assertEqual(result["decision"]["basis"], "trade_plus_fa")
        self.assertIn("Takassız referans ekliyor", render_trade_report(result))

    def test_missing_stale_conflicting_fa_evidence_blocks_only_completion(self):
        for change in (
            {"updated_at": (full_context().as_of - timedelta(hours=25)).isoformat()},
            {"sync_id": "different"},
            {"reason": "unverified"},
        ):
            ctx = full_context()
            ctx.availability_audit.update(change)
            result = evaluate_trade(ctx, uneven_bundle())
            self.assertEqual(result["completion"]["status"], "unavailable")
            self.assertTrue(result["teams"])

    def test_add_limit_unknown_budget_and_materiality_gate(self):
        for completion in (
            {"adds_used_by_week": {}},
            {"adds_used_by_week": {"2026-11-02": {"0": 3}}},
            {"min_gain_per_week": 100},
        ):
            data = uneven_bundle()
            data["completion"].update(completion)
            result = evaluate_trade(full_context(), data)
            self.assertFalse(result["completion"]["options"])
            self.assertEqual(result["decision"]["basis"], "trade_only")

    def test_waiver_date_retains_pre_drop_games_and_excludes_pre_acquisition_games(self):
        ctx = full_context()
        engine = copy.deepcopy(ctx.engine)
        dist = engine.get_expected_weekly_distribution(
            [1, 29],
            "2026-11-02",
            "2026-11-08",
            as_of_date="2026-10-30",
            player_start_dates={29: "2026-11-04"},
            player_end_dates={1: "2026-11-03"},
        )
        self.assertEqual(dist["meta"]["lineups"]["2026-11-02"], [1])
        self.assertEqual(dist["meta"]["lineups"]["2026-11-04"], [29])
        data = uneven_bundle()
        ctx.available_players[29].update(status="W", waiver={"date": "2026-11-04"})
        result = evaluate_trade(ctx, data)
        option = result["completion"]["options"][0]
        self.assertEqual(option["date"], "2026-11-04")
        before = option["teams"]["0"]["weekly"][0]["before"]["lineups"]
        after = option["teams"]["0"]["weekly"][0]["after"]["lineups"]
        self.assertNotIn(29, before["2026-11-02"])
        self.assertNotIn(29, after["2026-11-02"])
        self.assertEqual(len(before["2026-11-02"]), 10)

    def test_unknown_waiver_and_owned_candidates_never_become_free(self):
        for info in (
            {"status": "W", "waiver": {"date": None}},
            {"status": "FA", "waiver": {"date": "2026-11-20"}},
        ):
            ctx = full_context()
            ctx.available_players[29].update(info)
            result = evaluate_trade(ctx, uneven_bundle())
            self.assertFalse(result["completion"]["options"])
        ctx = full_context()
        ctx.available_players[14] = {"status": "FA", "waiver": None}
        result = evaluate_trade(ctx, uneven_bundle())
        self.assertNotIn(14, [o["player_id"] for o in result["completion"]["options"]])


class Stage5RenderingTest(unittest.TestCase):
    def monitor(self):
        return {
            "status": "analyzed",
            "policy": "pending_only",
            "captured_at": "2026-10-30T12:00:00+00:00",
            "offers": [
                {
                    "offer_id": "offer-1",
                    "status": "proposed",
                    "direction": "received",
                    "analysis_status": "evaluated",
                    "display": {
                        "give": ["<script>unsafe</script>"],
                        "receive": ["[click](https://bad.example)"],
                    },
                    "analysis": {
                        "verdict": "conditional_accept",
                        "decision": {"delta": 0.12, "basis": "trade_only"},
                        "proposal": {"our_team": "0"},
                        "team_names": {"0": "Berk's Best Team"},
                    },
                    "playoff_impact": {
                        "status": "conditional_estimate",
                        "teams": {
                            "0": {
                                "before": 0.51,
                                "after": 0.53,
                                "delta": 0.02,
                                "delta_mc_standard_error": 0.001,
                            },
                        },
                        "assumptions": ["Tiebreak remains conditional"],
                    },
                }
            ],
        }

    def telegram(self, monitor):
        from src.notifications import render_telegram

        return render_telegram(
            now=context().as_of,
            opponent="Current opponent",
            points=4.5,
            probabilities={},
            health=[],
            recommendations=[],
            provisional=False,
            trade_analysis=monitor,
        )

    def test_monitor_escapes_imported_names_and_labels_conditional_playoff_pp(self):
        from src.trade_report import render_trade_monitor

        result = render_trade_monitor(self.monitor())
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)
        self.assertNotIn("[click](https://bad.example)", result)
        self.assertIn("+2.00 yüzde puan", result)
        self.assertIn("0.100 yüzde puan", result)
        self.assertIn("Streaming planının playoff etkisi bu hesaba dahil değildir", result)
        message = self.telegram(self.monitor())
        self.assertNotIn("<script>", message)
        self.assertIn("&lt;script&gt;", message)
        self.assertIn("Koşullu playoff etkisi: 51.0% → 53.0%", message)
        self.assertNotIn("<a href=", message)

    def test_stale_monitor_does_not_present_old_evaluated_offers(self):
        from src.trade_report import render_trade_monitor

        monitor = self.monitor()
        monitor.update(status="needs_data", reasons=["Yahoo capture stale"])
        for rendered in (render_trade_monitor(monitor), self.telegram(monitor)):
            self.assertNotIn("unsafe", rendered)
            self.assertNotIn("+0.120", rendered)
            self.assertIn("doğrulanamadı", rendered)

    def test_no_pending_is_distinct_from_missing_data_and_deferred_analysis(self):
        from src.trade_report import render_trade_monitor

        empty = {"status": "no_pending_offers", "offers": []}
        self.assertIn("bekleyen teklif yok", render_trade_monitor(empty))
        self.assertIn("bekleyen teklif yok", self.telegram(empty))
        monitor = self.monitor()
        monitor["offers"][0]["analysis_status"] = "deferred"
        for rendered in (render_trade_monitor(monitor), self.telegram(monitor)):
            self.assertIn("karar", rendered.lower())
            self.assertNotIn("+0.120", rendered)

    def test_individual_report_includes_qualification_missing_data_without_fabricated_zero(self):
        result = evaluate_trade(context(), bundle())
        result["playoff_impact"] = {
            "status": "needs_data",
            "reasons": ["Current week score missing"],
        }
        report = render_trade_report(result)
        self.assertIn("Playoff'a katılım etkisi", report)
        self.assertIn("Current week score missing", report)
        self.assertNotIn("+0.00 yüzde puan", report)


class ThreeTeamTradeTest(unittest.TestCase):
    def proposal(self):
        data = bundle()
        data["proposal"]["transfers"] = [
            dict(from_team="0", to_team="1", yahoo_player_id="101"),
            dict(from_team="1", to_team="2", yahoo_player_id="103"),
            dict(from_team="2", to_team="0", yahoo_player_id="105"),
        ]
        return data

    def test_equal_cycle_is_neutral_and_context_immutable(self):
        ctx, data = context(equal=True), self.proposal()
        original = pickle.dumps(ctx)
        result = evaluate_trade(ctx, data)
        self.assertEqual(set(result["teams"]), {"0", "1", "2"})
        for row in result["teams"].values():
            self.assertAlmostEqual(row["all_supplied_weeks"]["delta"], 0, places=10)
        self.assertEqual(original, pickle.dumps(ctx))
        self.assertIn("Player 5", render_trade_report(result))

    def test_invalid_ownership_and_duplicate_players_rejected(self):
        for mutation in ("duplicate", "owner", "missing"):
            data = self.proposal()
            if mutation == "duplicate":
                data["proposal"]["transfers"][2]["yahoo_player_id"] = "101"
            elif mutation == "owner":
                data["proposal"]["transfers"][0]["from_team"] = "2"
            else:
                data["proposal"]["transfers"][2]["to_team"] = "1"
            with self.assertRaises(ValueError):
                evaluate_trade(context(), data)

    def test_third_team_matches_simultaneous_roster_projection(self):
        from src.trades import _pair, _summary

        ctx, data = context(), self.proposal()
        result = evaluate_trade(ctx, data)
        engine = copy.deepcopy(ctx.engine)
        engine.use_positional_depth_and_injury_boost = True
        expected = 0
        for week in data["weeks"]:
            a, b = next(pair for pair in week["fixtures"] if "2" in pair)
            rosters = {"0": [2, 5], "1": [4, 1], "2": [6, 3], "3": [7, 8]}
            before = _pair(
                engine,
                ctx.rosters[a],
                ctx.rosters[b],
                week["start"],
                week["end"],
                pd.Timestamp("2026-10-30"),
            )
            after = _pair(
                engine,
                rosters[a],
                rosters[b],
                week["start"],
                week["end"],
                pd.Timestamp("2026-10-30"),
            )
            index = 0 if a == "2" else 1
            expected += (
                _summary(engine, after[index], after[1 - index])["points"]
                - _summary(engine, before[index], before[1 - index])["points"]
            )
        self.assertAlmostEqual(expected, result["teams"]["2"]["all_supplied_weeks"]["delta"])

    def test_three_players_each_in_two_team_trade(self):
        ctx = context(equal=True)
        ctx.rosters = {"0": [1, 2, 5], "1": [3, 4, 6], "2": [7], "3": [8]}
        data = bundle()
        data["proposal"]["give_yahoo_ids"] = [101, 102, 105]
        data["proposal"]["receive_yahoo_ids"] = [103, 104, 106]
        result = evaluate_trade(ctx, data)
        self.assertAlmostEqual(result["teams"]["0"]["all_supplied_weeks"]["delta"], 0)

    def test_uneven_cycle_requires_explicit_drop_and_counts_its_cost(self):
        ctx = full_context()
        data = self.proposal()
        data["proposal"]["transfers"] = [
            dict(from_team="0", to_team="1", yahoo_player_id="101"),
            dict(from_team="1", to_team="2", yahoo_player_id="114"),
            dict(from_team="2", to_team="0", yahoo_player_id="127"),
            dict(from_team="0", to_team="1", yahoo_player_id="102"),
        ]
        with self.assertRaises(ValueError):
            evaluate_trade(ctx, data)
        data["drop_yahoo_ids"] = {"1": ["115"]}
        result = evaluate_trade(ctx, data)
        self.assertEqual(result["drops"]["1"], ["Real roster slot 15"])
        self.assertEqual(len(result["teams"]), 3)

    def test_panel_returns_structured_three_team_result_and_downloadable_report(self):
        import json

        from src.trade_automation import DEFAULTS
        from src.trade_panel import analyze

        config = copy.deepcopy(DEFAULTS)
        config["analysis"] = bundle()
        payload = dict(
            mode="manual",
            mine="0",
            other="1",
            give=["101"],
            receive=["105"],
            date="2026-11-01",
            transfers=self.proposal()["proposal"]["transfers"],
        )
        with (
            patch("src.trade_panel.load_context", return_value=context()),
            patch("src.trade_panel.load_config", return_value=config),
        ):
            result = analyze(payload)
        self.assertEqual(result["result"]["kind"], "three_team")
        self.assertIn("Player 5", result["report"])
        json.dumps(result, allow_nan=False)


class PanelFeedbackTest(unittest.TestCase):
    def test_preview_totals_and_grades_use_the_actual_fa_or_streaming_comparison(self):
        from src.trade_panel import preview_metrics
        from src.trade_search import effective_gains

        def summary(before, delta, sensitivity):
            return {
                "all_supplied_weeks": {
                    "before": before,
                    "after": before + delta,
                    "delta": delta,
                    "weeks": 4,
                },
                "without_spillover_delta": sensitivity,
            }

        pure = {"0": summary(20, -0.4, -0.8), "1": summary(21, -0.2, -0.3)}
        assisted = {"0": summary(20, 1.2, 0.6), "1": summary(21, 0.3, 0.1)}
        for basis in ("trade_only", "trade_plus_fa", "trade_plus_streaming", "trade_plus_joint_fa"):
            selected = pure if basis == "trade_only" else assisted
            total = selected["0"]["all_supplied_weeks"]
            analysis = {
                "proposal": {"our_team": "0", "other_team": "1"},
                "teams": pure,
                "decision": {
                    "basis": basis,
                    "delta": total["delta"],
                    "delta_without_spillover": selected["0"]["without_spillover_delta"],
                },
                "completion": {
                    "options": [{"team": "1", "teams": pure}, {"team": "0", "teams": assisted}]
                },
                "streaming": {"teams": assisted},
                "partner_completion": {"teams": assisted},
            }
            with self.subTest(basis=basis):
                metrics = preview_metrics(analysis)
                gains = effective_gains(analysis)
                own, partner = metrics["teams"]["0"], metrics["teams"]["1"]
                self.assertEqual(metrics["basis"], basis)
                self.assertEqual(own["after"], total["after"])
                self.assertAlmostEqual(own["after"] - own["before"], own["normal_delta"])
                self.assertEqual(own["conservative_delta"], gains["ours_conservative"])
                self.assertEqual(partner["conservative_delta"], gains["partner_conservative"])
                self.assertEqual(own["weekly_delta"], own["conservative_delta"] / 4)
                self.assertNotAlmostEqual(own["before"] + own["conservative_delta"], own["after"])
                self.assertEqual(own["grade"]["score"], 4.0 if basis == "trade_only" else 5.8)

    def test_panel_player_metadata_matches_the_model_and_labels_fallback(self):
        from src.trade_panel import panel_player_record

        ctx = context()
        ctx.engine.players[1].update_injury_status("HEALTHY")
        ctx.engine.pos_dict[1] = "C"
        ctx.player_evidence[1] = {
            "model_status_source": "yahoo_roster",
            "positions_source": "yahoo_roster",
            "needs_yahoo_refresh": False,
            "model_status_observed_at": "2026-10-30T12:00:00Z",
        }
        item = panel_player_record(ctx, 1, "101")
        self.assertEqual(item["injury"], item["display_injury"])
        self.assertEqual(item["positions"], "C")
        self.assertEqual(item["injury_source"], "yahoo_roster")
        ctx.player_evidence[1].update(positions_source="nba_fallback", needs_yahoo_refresh=True)
        item = panel_player_record(ctx, 1, "101")
        self.assertTrue(item["metadata_warning"])
        self.assertEqual(item["positions_source"], "nba_fallback")

    def test_player_source_change_invalidates_panel_version_without_roster_change(self):
        import json

        from src.trade_panel import roster_version

        sources = {"injuries.db": b"old", "player_positions.parquet": b"positions"}

        def source_bytes(path):
            if path.name not in sources:
                raise FileNotFoundError(path)
            return sources[path.name]

        with (
            patch.object(Path, "read_text", return_value=json.dumps({"sync_id": "same"})),
            patch.object(Path, "read_bytes", source_bytes),
        ):
            first = roster_version()
            sources["injuries.db-wal"] = b"new injury observation"
            self.assertNotEqual(first, roster_version())

    def test_player_evidence_expiry_invalidates_panel_without_file_change(self):
        import json
        from datetime import timedelta

        from src.trade_panel import roster_version

        captured = context().as_of
        state = {
            "sync_id": "same",
            "yahoo_roster_players": {
                "0": [
                    {
                        "name": "Player 1",
                        "yahoo_player_id": "101",
                        "captured_at": captured.isoformat(),
                    }
                ]
            },
        }
        with (
            patch.object(Path, "read_text", return_value=json.dumps(state)),
            patch.object(Path, "read_bytes", side_effect=FileNotFoundError),
        ):
            fresh = roster_version(now=captured + timedelta(hours=23))
            self.assertEqual(fresh, roster_version(now=captured + timedelta(hours=24)))
            self.assertNotEqual(
                fresh, roster_version(now=captured + timedelta(hours=24, seconds=1))
            )

    def test_search_preferences_are_explicit_and_do_not_mutate_config(self):
        from src.trade_automation import DEFAULTS
        from src.trade_panel import analyze

        config = copy.deepcopy(DEFAULTS)
        config.update(our_team="0", analysis=bundle())
        original = copy.deepcopy(config)
        data = dict(
            mode="search",
            mine="0",
            other="1",
            give=[101],
            date="2026-11-01",
            search_options=dict(min_gain_per_week=0, max_partner_loss_per_week=0.1, depth="wide"),
        )
        with (
            patch("src.trade_panel.load_context", return_value=context()),
            patch("src.trade_panel.load_config", return_value=config),
            patch("src.trade_panel.render_search_report", return_value="report"),
            patch(
                "src.trade_panel.search_trades",
                return_value={"finalists": [], "preliminary_candidates": []},
            ) as search,
        ):
            analyze(data)
        settings = search.call_args.args[1]["search"]
        self.assertEqual(settings["min_gain_per_week"], 0)
        self.assertEqual(settings["max_partner_loss_per_week"], 0.1)
        self.assertEqual(settings["shortlist_size"], 80)
        self.assertEqual(settings["streaming_finalists"], 8)
        self.assertEqual(original, config)

    def test_manual_column_order_does_not_flip_our_trade_verdict(self):
        from src.trade_automation import DEFAULTS
        from src.trade_panel import analyze

        config = copy.deepcopy(DEFAULTS)
        config.update(our_team="0", analysis=bundle())
        forward = dict(
            mode="manual", mine="0", other="1", give=[101], receive=[103], date="2026-11-01"
        )
        reversed_columns = dict(
            mode="manual", mine="1", other="0", give=[103], receive=[101], date="2026-11-01"
        )
        original = copy.deepcopy(reversed_columns)
        with (
            patch("src.trade_panel.load_context", return_value=context()),
            patch("src.trade_panel.load_config", return_value=config),
        ):
            first = analyze(forward)["result"]
            second = analyze(reversed_columns)["result"]
        self.assertEqual(second["proposal"]["our_team"], "0")
        self.assertEqual(first["teams"], second["teams"])
        self.assertEqual(first["verdict"], second["verdict"])
        self.assertEqual(first["decision"], second["decision"])
        self.assertEqual(reversed_columns, original)

    def test_frontend_hides_rejected_packages_refreshes_rosters_and_uses_own_team(self):
        import shutil
        import subprocess

        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for panel JavaScript regressions")
        html = (Path(__file__).resolve().parents[1] / "src/trade_panel.html").read_text(
            encoding="utf-8"
        )
        script = html.split("<script>")[1].split("</script>")[0]
        harness = r"""
const vm=require('node:vm'),assert=require('node:assert/strict'),fs=require('node:fs');
const elements=new Map();
function element(id){if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',hidden:false,value:'',parentElement:{},classList:{add(){},remove(){},toggle(){}},querySelectorAll:()=>[],scrollIntoView(){}});return elements.get(id)}
const sandbox={console,document:{getElementById:element,querySelectorAll:()=>[],hidden:false},window:{addEventListener(){}},fetch:()=>new Promise(()=>{}),setInterval(){},setTimeout:fn=>fn()};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(0,'utf8'),sandbox);
vm.runInContext(`
state={our_team:'0',snapshot_id:'s',roster_version:'v1',captured:'2026-10-30T12:00:00Z',teams:{
 '0':{name:'Our team',players:[{id:'101',name:'Injured Player',positions:'PG',injury:'INJ',stashed:true}]},
 '1':{name:'Partner',players:[{id:'103',name:'Target',positions:'C',injury:'HEALTHY',stashed:false}]},
 '12':{name:'Other team',players:[{id:'112',name:'Kris Dunn',positions:'PG',injury:'HEALTHY',stashed:false}]}}};
owners=['0','1'];count=2;
show({kind:'search',report:'audit',result:{opportunities:[],finalists:[{display:{give:['Kris Dunn'],receive:['Wembanyama']}}]}});
`,sandbox);
assert(!element('cards').innerHTML.includes('Kris Dunn'));
vm.runInContext(`
show({kind:'search',report:'audit',result:{opportunities:[],review_opportunities:[{model_qualified:true,qualified:false,display:{give:['Kris Dunn'],receive:['Donovan Mitchell']},final:{ours_conservative:0.3,partner_conservative:-0.02},review_reasons:['Market unverified']}],finalists:[]}});
`,sandbox);
assert(element('cards').innerHTML.includes('Donovan Mitchell'));
assert(element('cards').innerHTML.includes('Kris Dunn'));
assert(element('cards').innerHTML.includes('Model'));
assert(element('cards').innerHTML.includes('+0.300'));
assert(element('cards').innerHTML.includes('-0.020'));
assert(element('cards').innerHTML.includes('kategori puanı farkı'));
assert(!element('cards').innerHTML.includes('kategori puanı / hafta'));
vm.runInContext(`
var preview={basis:'trade_plus_fa',our_team:'0',teams:{
 '0':{before:22.1,after:23,normal_delta:0.9,without_spillover_delta:0.634,conservative_delta:0.634,weeks:4,grade:{score:5.8}},
 '1':{before:20,after:19.9,normal_delta:-0.1,without_spillover_delta:-0.2,conservative_delta:-0.2,weeks:4,grade:{score:4.8}}
}};
show({kind:'search',report:'audit',result:{thresholds:{weeks:4},review_opportunities:[{display:{give:['Player A'],receive:['Player B']},final:{ours_conservative:0.634,partner_conservative:-0.2,basis:'trade_plus_fa'},preview_metrics:preview}]}});
`,sandbox);
assert(element('cards').innerHTML.includes('22.100 → 23.000'));
assert(element('cards').innerHTML.includes('Normal senaryo farkı: +0.900'));
assert(element('cards').innerHTML.includes('+0.634'));
assert(element('cards').innerHTML.includes('+0.159 kategori puanı / hafta'));
assert(element('cards').innerHTML.includes('5.8/10'));
assert(element('cards').innerHTML.includes('Takas + FA tamamlama'));
assert(!element('cards').innerHTML.includes('22.734'));
element('searchDepth').value='wide';vm.runInContext('updateDepthHelp()',sandbox);
assert(element('searchDepthHelp').textContent.includes('80 paket karşılaştırılır'));
assert(element('searchDepthHelp').textContent.includes('8 paket'));
assert(element('searchDepthHelp').textContent.includes('gerçek fikstür, günlük kadro'));
assert(!vm.runInContext(`pendingCard({analysis_status:'needs_data',bilateral:{ours:99},display:{}})`,sandbox).includes('Etki notu'));
assert.equal(vm.runInContext(`manualConditionSummary(['Berk bırakıyor: Player A','Trade rules have not been confirmed.']).join('|')`,sandbox),'Berk bırakıyor: Player A|Lig kuralları doğrulanmadığı için sonuç koşullu.');
assert(vm.runInContext(`playerMeta({positions:'C',injury:'HEALTHY',positions_source:'yahoo_roster',injury_source:'yahoo_roster'})`,sandbox).includes('Sağlıklı'));
assert(vm.runInContext(`playerMeta({positions:'C-F',injury:'QUESTIONABLE',positions_source:'nba_fallback',injury_source:'injury_cache',metadata_warning:'Yahoo kaydı yenilenmeli'})`,sandbox).includes('Pozisyon: NBA tahmini'));
vm.runInContext(`searchOutgoing.add('101');searchTarget='12';setMode('pending');setMode('search')`,sandbox);
assert.equal(vm.runInContext("searchOutgoing.has('101')",sandbox),true);
assert.equal(vm.runInContext('searchTarget',sandbox),'12');
vm.runInContext(`moves={'101':{from_team:'0',to_team:'1',yahoo_player_id:'101',slot:'IL'}};renderRoster(0)`,sandbox);
assert(!element('roster0').innerHTML.includes('disabled'));
assert.equal(vm.runInContext(`ilAssignments()['1'][0]`,sandbox),'101');
vm.runInContext(`owners=['12','1'];mode='search';moves={};api=async(path,body)=>{
 if(path==='/version')return {roster_version:'v1'};
 if(path==='/run'){if(body.mine!=='0')throw Error('Wrong search team');return {id:'job'}};
 return {done:true,kind:'search',report:'audit',result:{opportunities:[]}};
}`,sandbox);
(async()=>{
 await vm.runInContext('run()',sandbox);
 assert.equal(element('error').textContent,'');
 await vm.runInContext(`moves={'112':{from_team:'12',to_team:'1'}};api=async(path)=>path==='/version'?{roster_version:'v2'}:{...state,roster_version:'v2'};refreshState()`,sandbox);
 assert.equal(vm.runInContext('Object.keys(moves).length',sandbox),0);
 assert.equal(vm.runInContext('searchOutgoing.size',sandbox),0);
 assert.equal(element('result').hidden,true);
})().catch(e=>{console.error(e);process.exitCode=1});
"""
        result = subprocess.run(
            [node, "-e", harness], input=script, text=True, encoding="utf-8", capture_output=True
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_search_cannot_silently_use_another_team(self):
        from src.trade_automation import DEFAULTS
        from src.trade_panel import analyze

        config = copy.deepcopy(DEFAULTS)
        config["our_team"] = "0"
        with (
            patch("src.trade_panel.load_context", return_value=context()),
            patch("src.trade_panel.load_config", return_value=config),
            patch("src.trade_panel.search_trades") as search,
        ):
            with self.assertRaises(ValueError):
                analyze(dict(mode="search", mine="1"))
            search.assert_not_called()

    def test_stale_panel_selection_requires_refresh(self):
        from src.trade_panel import analyze

        with (
            patch("src.trade_panel.roster_version", return_value="new"),
            patch("src.trade_panel.load_context") as model,
        ):
            with self.assertRaises(ValueError):
                analyze(dict(mode="manual", roster_version="old"))
            model.assert_not_called()

    def test_effect_grade_is_neutral_monotonic_bounded_and_horizon_normalized(self):
        from src.trade_panel import impact_grade

        self.assertEqual(impact_grade(0, 4)["score"], 5)
        self.assertEqual(impact_grade(0.8, 4)["score"], 6)
        self.assertEqual(impact_grade(0.2, 1)["score"], 6)
        self.assertEqual(impact_grade(-0.8, 4)["score"], 4)
        self.assertEqual(impact_grade(100, 4)["score"], 10)
        self.assertEqual(impact_grade(-100, 4)["score"], 0)

    def test_il_player_can_move_in_bilateral_and_three_team_packages(self):
        from src.trade_packages import trade_packages

        ctx = context()
        ctx.engine.yahoo_already_stashed_ids = {1}
        ctx.il_eligible_ids = {1}
        data = bundle()
        data["post_trade_il_yahoo_ids"] = {"0": [], "1": ["101"]}
        scenarios, _ = trade_packages(ctx, data, [1], [3])
        self.assertIn(1, scenarios[0].stashed)
        self.assertIn(1, scenarios[0].rosters["1"])
        data = ThreeTeamTradeTest().proposal()
        data["post_trade_il_yahoo_ids"] = {"0": [], "1": ["101"], "2": []}
        result = evaluate_trade(ctx, data)
        self.assertEqual(result["kind"], "three_team")
        data["post_trade_il_yahoo_ids"]["1"] = []
        activated = evaluate_trade(ctx, data)
        self.assertGreater(
            activated["teams"]["1"]["all_supplied_weeks"]["after"],
            result["teams"]["1"]["all_supplied_weeks"]["after"],
        )

    def test_il_overflow_and_unverified_eligibility_still_rejected(self):
        from src.trade_packages import trade_packages

        ctx = context()
        data = bundle()
        data["post_trade_il_yahoo_ids"] = {"0": [], "1": ["103"]}
        with self.assertRaises(ValueError):
            trade_packages(ctx, data, [1], [3])
        ctx.rosters["1"] = [3, 4, 5]
        ctx.rosters["2"] = [6]
        ctx.il_eligible_ids = {1, 4, 5}
        data["post_trade_il_yahoo_ids"] = {"0": [], "1": ["101", "104", "105"]}
        with self.assertRaises(ValueError):
            trade_packages(ctx, data, [1], [3])


if __name__ == "__main__":
    unittest.main()

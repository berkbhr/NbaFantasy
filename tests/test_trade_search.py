"""Bounded discovery/counteroffer and source-attributed market regressions."""

import copy
import json
import pickle
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from src.trade_market import assess_market
from src.trade_search import _diverse_shortlist, _shortlist, search_trades
from src.trade_search import main as search_main
from src.trade_search_report import render_search_report
from src.trades import evaluate_trade
from tests.test_trades import bundle, context, protected_slot_scenario


def search_fixture():
    ctx, data = context(), bundle()
    ctx.team_names = {
        "0": "Berk's Best Team",
        "1": "Philadelphia Sikers",
        "2": "Mordor Tulums",
        "3": "MuCa Tandır",
    }
    for pid, name in {
        1: "Desmond Bane",
        2: "Jarrett Allen",
        3: "Lauri Markkanen",
        4: "Darius Garland",
    }.items():
        ctx.engine.players[pid].name = name
    data["completion"] = {"enabled": False}
    data["streaming"] = {"enabled": True}
    data["search"] = {
        "team_ids": ["1"],
        "package_types": ["1x1"],
        "shortlist_size": 4,
        "streaming_finalists": 2,
        "min_gain_per_week": 0,
        "max_partner_loss_per_week": 9,
        "counter_improvement_per_week": 0,
    }
    return ctx, data


def market_snapshot(ctx, metric="rank"):
    return {
        "source": "Controlled test market; not Yahoo data",
        "captured_at": ctx.as_of.isoformat(),
        "metric": metric,
        "players": {
            str(100 + p): {"rank": p + 30, "trade_value": 10.0} for p in ctx.engine.players
        },
    }


def bilateral_fixture():
    """Complementary needs against different opponents; every number is synthetic."""
    ctx, data = search_fixture()
    for pid, pts, reb in (
        (1, 28, 3),
        (2, 32, 6),
        (3, 3, 17),
        (4, 6, 20),
        (5, 4, 10),
        (6, 4, 10),
        (7, 10, 4),
        (8, 10, 4),
    ):
        p = ctx.engine.players[pid]
        p.alphas["PTS"] = pts / 30 * p.betas["PTS"]
        p.alphas["REB"] = reb / 30 * p.betas["REB"]
    fa = copy.deepcopy(ctx.engine.players[5])
    fa.name = "Luke Kennard"
    ctx.engine.players[9] = fa
    ctx.engine.team_map[9] = 1
    ctx.engine.pos_dict[9] = "PG,SG,SF,PF,C"
    ctx.yahoo_ids["109"] = 9
    ctx.available_players[9] = {"status": "FA", "waiver": None, "yahoo_player_id": "109"}
    ctx.availability_audit = {
        "source": "yahoo_available_players",
        "sync_id": ctx.sync_id,
        "updated_at": ctx.as_of.isoformat(),
        "scan_complete": True,
    }
    ctx.warnings = [
        "Controlled fixture: names are real; ownership, forecasts, fixtures and market values are synthetic."
    ]
    data["weeks"] = data["weeks"][:1]
    data["weeks"][0]["fixtures"] = [["0", "2"], ["1", "3"]]
    data["regular_season_end"] = None
    data["eligible_positions"]["109"] = ["PG", "SG", "SF", "PF", "C"]
    data["streaming"] = {
        "enabled": True,
        "candidate_limit": 1,
        "beam_width": 2,
        "finalists": 2,
        "min_gain_per_week": 0.05,
        "adds_used_by_week": {"2026-11-02": {"0": 0}},
    }
    data["search"].update(
        min_gain_per_week=0.05, max_partner_loss_per_week=0.05, counter_improvement_per_week=0.01
    )
    data["market_snapshot"] = market_snapshot(ctx, "replacement_adjusted_trade_value")
    return ctx, data


class TradeMarketTest(unittest.TestCase):
    def test_elite_rank_outlier_is_blocked_without_summing_ordinal_ranks(self):
        ctx, data = search_fixture()
        data["market_snapshot"] = market_snapshot(ctx)
        data["market_snapshot"]["players"]["101"]["rank"] = 150
        data["market_snapshot"]["players"]["103"]["rank"] = 1
        market = assess_market(ctx, data, data["proposal"])
        self.assertTrue(market["blocked"])
        self.assertEqual(market["status"], "outlier")
        self.assertNotIn("totals", market)

    def test_rank_only_data_never_becomes_a_complete_package_price(self):
        ctx, data = search_fixture()
        data["market_snapshot"] = market_snapshot(ctx)
        result = assess_market(ctx, data, data["proposal"])
        self.assertEqual(result["status"], "rank_screen_only")
        self.assertTrue(result["requires_review"])
        self.assertNotIn("totals", result)

    def test_replacement_adjusted_values_and_form_signals_keep_source(self):
        ctx, data = search_fixture()
        data["market_snapshot"] = market_snapshot(ctx, "replacement_adjusted_trade_value")
        data["market_snapshot"]["players"]["103"].update(recent_rank_14d=100, projected_rank=30)
        result = assess_market(ctx, data, data["proposal"])
        self.assertEqual(result["status"], "balanced_value")
        self.assertEqual(result["totals"], {"give": 10.0, "receive": 10.0})
        self.assertEqual(result["form_signals"][0]["name"], "Lauri Markkanen")
        self.assertEqual(result["form_signals"][0]["signal"], "recent_weaker")
        self.assertIn("Controlled", result["source"])
        self.assertNotIn("acceptance_probability", result)

    def test_missing_stale_future_and_incomplete_market_are_explicit(self):
        ctx, data = search_fixture()
        self.assertEqual(assess_market(ctx, data, data["proposal"])["status"], "unavailable")
        for delta in (timedelta(days=-8), timedelta(days=1)):
            data["market_snapshot"] = market_snapshot(ctx)
            data["market_snapshot"]["captured_at"] = (ctx.as_of + delta).isoformat()
            self.assertEqual(assess_market(ctx, data, data["proposal"])["status"], "stale")
        data["market_snapshot"] = market_snapshot(ctx, "replacement_adjusted_trade_value")
        del data["market_snapshot"]["players"]["103"]
        self.assertEqual(assess_market(ctx, data, data["proposal"])["status"], "incomplete")

    def test_zero_side_and_nonfinite_values_never_generate_nan_json(self):
        ctx, data = search_fixture()
        data["market_snapshot"] = market_snapshot(ctx, "replacement_adjusted_trade_value")
        data["market_snapshot"]["players"]["101"]["trade_value"] = 0
        result = assess_market(ctx, data, data["proposal"])
        self.assertTrue(result["blocked"])
        json.dumps(result, allow_nan=False)
        data["market_snapshot"]["players"]["101"]["trade_value"] = float("nan")
        self.assertEqual(assess_market(ctx, data, data["proposal"])["status"], "incomplete")


class TradeSearchTest(unittest.TestCase):
    def test_generic_search_reserves_quality_and_exploration_across_players_and_opponents(self):
        from collections import Counter

        pools = {}
        for team in ("1", "2"):
            rows = []
            for index in range(16):
                rows.append(
                    dict(
                        proposal=dict(
                            our_team="0",
                            other_team=team,
                            give_yahoo_ids=["101"],
                            receive_yahoo_ids=[str(300 + index)],
                        ),
                        shape="1x1",
                        quick=dict(joint=100 - index),
                    )
                )
            for player in range(2, 7):
                rows.append(
                    dict(
                        proposal=dict(
                            our_team="0",
                            other_team=team,
                            give_yahoo_ids=[str(100 + player)],
                            receive_yahoo_ids=[str(400 + player)],
                        ),
                        shape="1x1",
                        quick=dict(joint=10 - player),
                    )
                )
            pools[team] = rows
        first = _diverse_shortlist(copy.deepcopy(pools), 12)
        second = _diverse_shortlist(copy.deepcopy(pools), 12)
        self.assertEqual(first, second)
        self.assertEqual(Counter(c["proposal"]["other_team"] for c in first), {"1": 6, "2": 6})
        self.assertEqual(
            {c["proposal"]["give_yahoo_ids"][0] for c in first}, {str(100 + p) for p in range(1, 7)}
        )
        quality = [c for c in first if c["selection_reason"] == "quick_quality"]
        self.assertEqual(len(quality), 6)
        self.assertTrue(all(c["proposal"]["give_yahoo_ids"] == ["101"] for c in quality))
        self.assertEqual(len({json.dumps(c["proposal"], sort_keys=True) for c in first}), 12)

    def test_generic_shortlist_does_not_discard_all_alternate_outgoing_players_before_screening(
        self,
    ):
        from tests.test_trades import full_context

        ctx, data = full_context(), bundle()
        data["proposal"]["give_yahoo_ids"] = []
        data["search"] = dict(
            team_ids=["1"], package_types=["1x1"], shortlist_size=8, per_shape_candidates=1
        )
        frozen = pickle.dumps(ctx)
        candidates, counts = _shortlist(ctx, data, "opportunities", data["search"])
        self.assertEqual(len(candidates), 8)
        self.assertEqual(counts["quality_selected"], 4)
        self.assertEqual(counts["coverage_selected"], 4)
        self.assertGreater(len({c["proposal"]["give_yahoo_ids"][0] for c in candidates}), 1)
        self.assertEqual(len(counts["shortlisted_outgoing_player_coverage"]), 13)
        self.assertEqual(
            sum(c["evaluated_packages"] for c in counts["shortlisted_outgoing_player_coverage"]), 8
        )
        self.assertEqual(frozen, pickle.dumps(ctx))
        self.assertTrue(
            all(
                ctx.yahoo_ids[y] in ctx.rosters["0"]
                for c in candidates
                for y in c["proposal"]["give_yahoo_ids"]
            )
        )

    def test_finalist_budget_does_not_hide_other_passing_screened_packages(self):
        ctx, data = search_fixture()
        data["streaming"]["enabled"] = False
        data["search"].update(
            streaming_finalists=1, min_gain_per_week=0, max_partner_loss_per_week=9
        )
        result = search_trades(ctx, data)
        self.assertEqual(len(result["finalists"]), 1)
        self.assertEqual(len(result["preliminary_candidates"]), 1)
        self.assertEqual(len(result["evaluated_packages"]), len(result["screened"]))
        self.assertEqual(result["search_diagnostics"]["model_screen_passed"], 2)
        self.assertEqual(result["preliminary_candidates"][0]["evaluation_level"], "screened")
        self.assertFalse(result["preliminary_candidates"][0]["qualified"])
        final = result["finalists"][0]["proposal"]
        self.assertNotEqual(final, result["preliminary_candidates"][0]["proposal"])
        report = render_search_report(result)
        self.assertIn("İncelenen bütün paketler", report)
        self.assertIn("Ön değerlendirmeyi geçen diğer paketler", report)

    def test_common_warnings_are_translated_and_appear_once(self):
        from src.trade_search_report import concise_conditions

        notes = concise_conditions(
            [
                "before 2026-11-02: usage is unknown; additions are blocked for this week.",
                "after 2026-11-09: usage is unknown; additions are blocked for this week.",
                "Trade rules have not been confirmed.",
                "Trade rules have not been confirmed.",
            ]
        )
        self.assertEqual(len(notes), 2)
        self.assertFalse(any("usage is unknown" in note for note in notes))
        self.assertEqual(sum("hamle tüketimi" in note for note in notes), 1)

    def test_unverified_market_never_qualifies_as_automatic_opportunity(self):
        ctx, data = bilateral_fixture()
        data.pop("market_snapshot")
        result = search_trades(ctx, data)
        self.assertTrue(result["finalists"])
        self.assertFalse(result["opportunities"])
        self.assertTrue(result["review_opportunities"])
        for candidate in result["review_opportunities"]:
            self.assertIn(candidate, result["finalists"])
            self.assertFalse(candidate["qualified"])
            self.assertTrue(candidate["model_qualified"])
            self.assertGreaterEqual(candidate["final"]["ours_conservative"], 0.05)
            self.assertGreaterEqual(candidate["final"]["partner_conservative"], -0.05)
        self.assertTrue(
            all(c["market"]["requires_review"] and not c["qualified"] for c in result["finalists"])
        )

    def test_selected_pair_and_single_target_screen_every_receiving_package(self):
        ctx, data = search_fixture()
        data["proposal"]["give_yahoo_ids"] = [101, 102]
        data["search"].update(
            package_types=["1x1", "1x2", "2x1", "2x2"],
            shortlist_size=1,
            per_shape_candidates=1,
        )
        candidates, counts = _shortlist(ctx, data, "opportunities", data["search"])
        self.assertTrue(counts["focused_exhaustive"])
        self.assertEqual(len(candidates), 3)
        self.assertEqual(
            {tuple(sorted(map(int, c["proposal"]["receive_yahoo_ids"]))) for c in candidates},
            {(103,), (104,), (103, 104)},
        )
        self.assertTrue(
            all(set(map(int, c["proposal"]["give_yahoo_ids"])) == {101, 102} for c in candidates)
        )

    def test_single_selected_player_is_exact_package_not_a_superset(self):
        ctx, data = search_fixture()
        data["search"]["package_types"] = ["1x1", "1x2", "2x1", "2x2"]
        candidates, counts = _shortlist(ctx, data, "opportunities", data["search"])
        self.assertTrue(counts["focused_exhaustive"])
        self.assertTrue(candidates)
        self.assertTrue(
            all(list(map(int, c["proposal"]["give_yahoo_ids"])) == [101] for c in candidates)
        )

    def test_selected_package_incompatible_with_explicit_shapes_is_rejected(self):
        ctx, data = search_fixture()
        ctx.rosters["0"] = [1, 2, 5]
        ctx.rosters["2"] = [6]
        data["proposal"]["give_yahoo_ids"] = [101, 102, 105]
        with self.assertRaises(ValueError):
            _shortlist(ctx, data, "opportunities", data["search"])

    def test_four_selected_players_are_preserved_and_fifth_is_rejected(self):
        from tests.test_trades import full_context

        ctx, data = full_context(), bundle()
        data["proposal"]["give_yahoo_ids"] = [101, 102, 103, 104]
        data["search"] = {"shortlist_size": 2, "per_shape_candidates": 1}
        candidates, counts = _shortlist(ctx, data, "opportunities", data["search"])
        self.assertEqual(counts["package_types"], ["4x3", "4x4"])
        self.assertEqual(len(candidates), 2)
        self.assertTrue(
            all(
                set(map(int, c["proposal"]["give_yahoo_ids"])) == {101, 102, 103, 104}
                for c in candidates
            )
        )
        data["proposal"]["give_yahoo_ids"].append(105)
        with self.assertRaises(ValueError):
            _shortlist(ctx, data, "opportunities", data["search"])

    def test_explicit_selected_players_are_not_silently_ignored(self):
        for invalid in ("unknown", "foreign", "protected", "IL"):
            with self.subTest(invalid=invalid):
                ctx, data = search_fixture()
                if invalid == "unknown":
                    data["proposal"]["give_yahoo_ids"] = [99999]
                elif invalid == "foreign":
                    data["proposal"]["give_yahoo_ids"] = [103]
                elif invalid == "protected":
                    data["do_not_trade_yahoo_ids"] = [101]
                else:
                    ctx.engine.yahoo_already_stashed_ids = {1}
                with self.assertRaises(ValueError):
                    _shortlist(ctx, data, "opportunities", data["search"])

    def test_known_bilateral_pass_gets_final_slot_before_larger_selfish_gain(self):
        ctx, data = search_fixture()
        data["proposal"]["give_yahoo_ids"] = []
        data["streaming"]["enabled"] = False
        data["search"].update(
            min_gain_per_week=0.05,
            max_partner_loss_per_week=0.05,
            streaming_finalists=1,
        )
        data["market_snapshot"] = market_snapshot(ctx, "replacement_adjusted_trade_value")
        prototype = evaluate_trade(ctx, bundle())
        candidates = []
        for receive in (103, 104):
            proposal = {**data["proposal"], "give_yahoo_ids": [101], "receive_yahoo_ids": [receive]}
            candidates.append(
                dict(
                    proposal=proposal,
                    market=assess_market(ctx, data, proposal),
                    shape="1x1",
                    quick={"ours": 0, "partner": 0, "joint": 0},
                )
            )

        def analysis(_context, candidate, **_kwargs):
            result = copy.deepcopy(prototype)
            proposal = candidate["proposal"]
            result["proposal"] = proposal
            selfish = int(proposal["receive_yahoo_ids"][0]) == 103
            own, partner = (1.0, -0.2) if selfish else (0.3, -0.05)
            result["decision"].update(delta=own, delta_without_spillover=own)
            result["verdict"] = "conditional_accept"
            for team, delta in (("0", own), ("1", partner)):
                result["teams"][team]["all_supplied_weeks"]["delta"] = delta
                result["teams"][team]["without_spillover_delta"] = delta
            return result

        counts = dict(
            generated_packages=2,
            market_outliers_skipped=0,
            shortlisted=2,
            teams_considered=["1"],
            excluded_il_players=0,
            focused_exhaustive=False,
        )
        with (
            patch("src.trade_search._shortlist", return_value=(candidates, counts)),
            patch("src.trade_search.evaluate_trade", side_effect=analysis),
        ):
            result = search_trades(ctx, data)
        self.assertEqual(len(result["finalists"]), 1)
        self.assertEqual(
            list(map(int, result["finalists"][0]["proposal"]["receive_yahoo_ids"])), [104]
        )
        self.assertTrue(result["opportunities"])

    def test_flat_two_for_one_is_not_cut_before_streaming_can_fill_the_seat(self):
        ctx, data = protected_slot_scenario()
        data["do_not_trade_yahoo_ids"] = [
            100 + p for ids in ctx.rosters.values() for p in ids if p not in (1, 2, 14)
        ]
        data["streaming"] = {
            "enabled": True,
            "candidate_limit": 1,
            "beam_width": 2,
            "finalists": 2,
            "adds_used_by_week": {"2026-11-02": {"0": 0}},
        }
        data["search"] = {
            "team_ids": ["1"],
            "package_types": ["2x1"],
            "shortlist_size": 1,
            "streaming_finalists": 1,
            "max_partner_loss_per_week": 9,
            "screen_with_fa": False,
        }
        data["market_snapshot"] = market_snapshot(ctx, "replacement_adjusted_trade_value")
        data["market_snapshot"]["players"]["114"]["trade_value"] = 20
        result = search_trades(ctx, data)
        self.assertAlmostEqual(result["screened"][0]["screening"]["ours"], 0)
        self.assertTrue(result["opportunities"])
        self.assertEqual(result["opportunities"][0]["final"]["basis"], "trade_plus_streaming")

    def test_cli_market_file_roundtrip_preserves_timestamp_and_input_hash(self):
        ctx, data = bilateral_fixture()
        ctx.as_of = ctx.as_of.replace(microsecond=123456)
        snapshot = data.pop("market_snapshot")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proposal_path, market_path = root / "input.json", root / "market.json"
            proposal_path.write_text(json.dumps(data), encoding="utf-8")
            market_path.write_text(json.dumps(snapshot), encoding="utf-8")
            with (
                patch(
                    "sys.argv",
                    [
                        "trade_search",
                        str(proposal_path),
                        "--market",
                        str(market_path),
                        "--output",
                        str(root / "out"),
                    ],
                ),
                patch("src.trade_search.load_context", return_value=ctx),
                patch("builtins.print"),
            ):
                search_main()
            output = next((root / "out").glob("*.json"))
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn(result["input_sha256"][:12], output.name)
            self.assertEqual(len(list((root / "out").glob("*.md"))), 1)
            self.assertEqual(json.loads(proposal_path.read_text(encoding="utf-8")), data)

    def test_bilateral_opportunity_and_counteroffer_use_actual_final_streaming_comparisons(self):
        ctx, data = bilateral_fixture()
        result = search_trades(ctx, data)
        self.assertTrue(result["opportunities"])
        for candidate in result["opportunities"]:
            self.assertGreaterEqual(candidate["final"]["ours_conservative"], 0.05)
            self.assertGreaterEqual(candidate["final"]["partner_conservative"], -0.05)
            self.assertEqual(candidate["market"]["status"], "balanced_value")
            self.assertEqual(candidate["analysis"]["streaming"]["status"], "planned")
        counter = search_trades(ctx, data, "counter")
        self.assertTrue(counter["opportunities"])
        for candidate in counter["opportunities"]:
            self.assertGreaterEqual(candidate["improvement_over_original"], 0.01)

    def test_streaming_runs_only_on_bounded_finalists_and_context_stays_immutable(self):
        ctx, data = search_fixture()
        original = pickle.dumps(ctx)
        calls = []

        def record(context, candidate, **kwargs):
            calls.append(candidate["streaming"]["enabled"])
            return evaluate_trade(context, candidate, **kwargs)

        with patch("src.trade_search.evaluate_trade", side_effect=record):
            result = search_trades(ctx, data)
        self.assertEqual(pickle.dumps(ctx), original)
        self.assertEqual(calls.count(False), result["counts"]["screen_evaluated"])
        self.assertLessEqual(calls.count(True), 2)
        self.assertTrue(result["finalists"])
        self.assertTrue(result["counts"]["projection_cache_entries"])
        self.assertLessEqual(result["counts"]["shortlisted"], 4)
        self.assertTrue(all(c["market"]["requires_review"] for c in result["finalists"]))
        report = render_search_report(result)
        for name in ("Berk's Best Team", "Philadelphia Sikers"):
            self.assertIn(name, report)
        for candidate in result["finalists"]:
            for name in candidate["display"]["give"] + candidate["display"]["receive"]:
                self.assertIn(name, report)
        self.assertNotIn("Yahoo ID", report)
        json.dumps(result, allow_nan=False)

    def test_projection_cache_matches_fresh_model_for_different_packages(self):
        ctx, data = search_fixture()
        data["streaming"]["enabled"] = False
        cache = {}
        self.assertEqual(
            evaluate_trade(ctx, data), evaluate_trade(ctx, data, projection_cache=cache)
        )
        other = copy.deepcopy(data)
        other["proposal"]["receive_yahoo_ids"] = [104]
        self.assertEqual(
            evaluate_trade(ctx, other), evaluate_trade(ctx, other, projection_cache=cache)
        )

    def test_finalists_match_direct_evaluation_and_selection_is_deterministic(self):
        ctx, data = search_fixture()
        first = search_trades(ctx, data)
        second = search_trades(ctx, data)
        self.assertEqual(first["finalists"], second["finalists"])
        self.assertTrue(first["finalists"])
        for candidate in first["finalists"]:
            direct = copy.deepcopy(data)
            direct["proposal"] = candidate["proposal"]
            direct["post_trade_il_yahoo_ids"], direct["drop_yahoo_ids"] = {}, {}
            self.assertEqual(evaluate_trade(ctx, direct), candidate["analysis"])

    def test_protected_players_and_market_outliers_do_not_enter_screening(self):
        ctx, data = search_fixture()
        data["proposal"]["give_yahoo_ids"] = []
        data["do_not_trade_yahoo_ids"] = [101]
        result = search_trades(ctx, data)
        self.assertTrue(
            all(101 not in map(int, c["proposal"]["give_yahoo_ids"]) for c in result["screened"])
        )
        data.pop("do_not_trade_yahoo_ids")
        data["market_snapshot"] = market_snapshot(ctx)
        for player in ("101", "102"):
            data["market_snapshot"]["players"][player]["rank"] = 150
        for player in ("103", "104"):
            data["market_snapshot"]["players"][player]["rank"] = 1
        with patch("src.trade_search.evaluate_trade") as evaluator:
            result = search_trades(ctx, data)
        self.assertFalse(result["screened"])
        evaluator.assert_not_called()
        self.assertGreater(result["counts"]["market_outliers_skipped"], 0)

    def test_counteroffers_keep_partner_and_change_only_small_neighborhood(self):
        ctx, data = search_fixture()
        result = search_trades(ctx, data, mode="counter")
        self.assertIsNotNone(result["original_analysis"])
        self.assertTrue(result["screened"])
        for candidate in result["screened"]:
            proposal = candidate["proposal"]
            self.assertEqual(proposal["other_team"], "1")
            distance = len(set(map(int, proposal["give_yahoo_ids"])) ^ {101}) + len(
                set(map(int, proposal["receive_yahoo_ids"])) ^ {103}
            )
            self.assertGreater(distance, 0)
            self.assertLessEqual(distance, 2)
            self.assertTrue(
                101 in map(int, proposal["give_yahoo_ids"])
                or 103 in map(int, proposal["receive_yahoo_ids"])
            )
        for candidate in result["opportunities"]:
            self.assertGreaterEqual(candidate["improvement_over_original"], 0)

    def test_manual_incoming_offer_bypasses_market_gate_but_is_flagged(self):
        ctx, data = search_fixture()
        data["market_snapshot"] = market_snapshot(ctx)
        for player in ("101", "102"):
            data["market_snapshot"]["players"][player]["rank"] = 150
        for player in ("103", "104"):
            data["market_snapshot"]["players"][player]["rank"] = 1
        result = search_trades(ctx, data, mode="counter")
        self.assertIsNotNone(result["original_analysis"])
        self.assertTrue(result["original_market"]["blocked"])
        self.assertFalse(result["finalists"])

    def test_strict_market_and_stale_roster_gates(self):
        ctx, data = search_fixture()
        data["search"]["require_market"] = True
        self.assertFalse(search_trades(ctx, data)["screened"])
        ctx.captured_at -= timedelta(hours=25)
        with self.assertRaises(ValueError):
            search_trades(ctx, data)


class PendingOfferAutomationTest(unittest.TestCase):
    def test_periodic_scan_uses_calendar_dates_not_24_hour_completion_gap(self):
        from src.trade_automation import opportunity_due

        now = context().as_of
        self.assertTrue(opportunity_due("daily", now - timedelta(hours=23, minutes=59), now))
        self.assertFalse(opportunity_due("daily", now - timedelta(minutes=1), now))
        self.assertFalse(opportunity_due("off", None, now))
        self.assertTrue(opportunity_due("weekly", now - timedelta(days=7), now))
        self.assertFalse(opportunity_due("weekly", now - timedelta(days=1), now))

    def fixture(self):
        from src.trade_automation import DEFAULTS

        ctx, data = context(), bundle()
        config = copy.deepcopy(DEFAULTS)
        config.update(our_team="0", playoff_enabled=False)
        config["analysis"] = data
        config["analysis"].update(completion={"enabled": False}, streaming={"enabled": False})
        mapping = {str(i + 1): str(i) for i in range(4)}
        state = {
            "league_id": "64691",
            "sync_id": ctx.sync_id,
            "rosters": ctx.rosters,
            "yahoo_team_slots": mapping,
            "yahoo_trade_audit": {"offers": "ready"},
            "pending_offers_snapshot": {
                "source": "yahoo_api_league",
                "captured_at": ctx.as_of.isoformat(),
                "complete": True,
                "league_id": "64691",
                "team_slots": mapping,
                "offers": [
                    {
                        "offer_id": "trade-1",
                        "status": "proposed",
                        "direction": "received",
                        "our_team": "0",
                        "other_team": "1",
                        "give_yahoo_ids": [101],
                        "receive_yahoo_ids": [103],
                    }
                ],
            },
        }
        return ctx, state, config

    def test_real_pending_only_is_cached_and_model_change_invalidates(self):
        from src.trade_automation import monitor_pending_offers

        ctx, state, config = self.fixture()
        first, runtime = monitor_pending_offers(state, now=ctx.as_of, context=ctx, config=config)
        self.assertEqual(first["status"], "analyzed")
        self.assertEqual(first["evaluated"], 1)
        self.assertFalse(first["wide_scan_ran"])
        self.assertTrue(first["offers"][0]["conditions"])
        with patch(
            "src.trade_automation.evaluate_trade", side_effect=AssertionError("cache missed")
        ):
            second, _ = monitor_pending_offers(
                state, now=ctx.as_of, context=ctx, config=config, runtime=runtime
            )
        self.assertEqual(second["cache_hits"], 1)
        ctx.availability_audit["reason"] = "FA evidence expired"
        expired, runtime = monitor_pending_offers(
            state, now=ctx.as_of, context=ctx, config=config, runtime=runtime
        )
        self.assertEqual(expired["evaluated"], 1)
        ctx.source_hashes["src/model_policy.py"] = "changed-model"
        third, _ = monitor_pending_offers(
            state, now=ctx.as_of, context=ctx, config=config, runtime=runtime
        )
        self.assertEqual(third["evaluated"], 1)

    def test_provider_date_selects_complete_weeks_after_it(self):
        from src.trade_automation import _bundle

        ctx, state, config = self.fixture()
        initial = config["analysis"].pop("weeks")[0]
        ctx.fantasy_calendar = {"complete_remaining_season": True, "weeks": []}
        for index in range(5):
            week = copy.deepcopy(initial)
            for field in ("start", "end"):
                week[field] = (
                    date.fromisoformat(initial[field]) + timedelta(weeks=index)
                ).isoformat()
            ctx.fantasy_calendar["weeks"].append(week)
        offer = state["pending_offers_snapshot"]["offers"][0]
        offer["effective_date"] = ctx.fantasy_calendar["weeks"][1]["start"]
        data, conditions = _bundle(ctx, config, offer)
        self.assertEqual(data["weeks"][0]["start"], offer["effective_date"])
        self.assertEqual(len(data["weeks"]), 4)
        self.assertFalse(conditions)

    def test_failed_or_stale_import_never_means_no_offers(self):
        from src.trade_automation import monitor_pending_offers

        ctx, state, config = self.fixture()
        for mutation in ("missing", "stale", "failed", "wrong_league", "malformed"):
            value = copy.deepcopy(state)
            if mutation == "missing":
                del value["pending_offers_snapshot"]
            elif mutation == "stale":
                value["pending_offers_snapshot"]["captured_at"] = (
                    ctx.as_of - timedelta(hours=7)
                ).isoformat()
            elif mutation == "failed":
                value["yahoo_trade_audit"]["offers"] = "unavailable"
            elif mutation == "malformed":
                value["pending_offers_snapshot"]["offers"] = ["invalid"]
            else:
                value["pending_offers_snapshot"]["league_id"] = "wrong"
            result, _ = monitor_pending_offers(value, now=ctx.as_of, context=ctx, config=config)
            self.assertEqual(result["status"], "needs_data")
            self.assertFalse(result["offers"])

    def test_closed_removed_offer_not_replayed_and_no_future_budget_invented(self):
        from src.trade_automation import _bundle, monitor_pending_offers

        ctx, state, config = self.fixture()
        config["analysis"].update(completion={"enabled": True}, streaming={"enabled": False})
        data, _ = _bundle(ctx, config, state["pending_offers_snapshot"]["offers"][0])
        self.assertNotIn("adds_used_by_week", data["completion"])
        state["pending_offers_snapshot"]["offers"] = []
        with patch(
            "src.trade_automation.load_context",
            side_effect=AssertionError("empty offers loaded model"),
        ):
            result, _ = monitor_pending_offers(state, now=ctx.as_of, config=config)
        self.assertEqual(result["status"], "no_pending_offers")

    def test_required_actual_date_policy_and_runtime_budget(self):
        from src.trade_automation import monitor_pending_offers

        ctx, state, config = self.fixture()
        config["effective_date_policy"] = "provider_only"
        result, _ = monitor_pending_offers(state, now=ctx.as_of, context=ctx, config=config)
        self.assertEqual(result["offers"][0]["analysis_status"], "needs_data")
        with self.assertRaises(TimeoutError):
            evaluate_trade(ctx, bundle(), deadline=0)


if __name__ == "__main__":
    unittest.main()

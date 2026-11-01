"""Regressions for the five trade-review claims; no live data or provider calls."""

import copy
import json
import unittest
from types import SimpleNamespace

import pandas as pd

from src.fantasy_calendar import calendar_view
from src.playoffs import estimate_playoff_probabilities
from src.snapshots import BOX_SCORE_KEYS
from src.trade_context import provider_il_eligible_ids, verified_yahoo_positions
from src.trade_market import assess_market
from src.trade_packages import RosterScenario
from src.trade_playoffs import (
    _current_pair,
    _interval_rosters,
    evaluate_playoff_impact,
    paired_qualification,
)
from src.trade_search import effective_gains, search_trades
from src.trade_search_report import render_search_report
from src.trades import evaluate_trade
from tests.test_fantasy_calendar import state_fixture
from tests.test_trade_search import bilateral_fixture, market_snapshot, search_fixture
from tests.test_trades import bundle, context, protected_slot_scenario


def playoff_fixture():
    from tests.test_trades import bundle

    ctx, state, _ = state_fixture()
    ctx.league_id = "64691"
    ctx.team_slots = state["yahoo_team_slots"]
    ctx.fantasy_calendar = calendar_view(state, ctx.as_of)
    matches = []
    for a, b in ctx.fantasy_calendar["current_week"]["fixtures"]:
        matches.append(
            [{**dict.fromkeys(BOX_SCORE_KEYS, 0), "slot": int(team) + 1} for team in (a, b)]
        )
    snapshot = {
        "source": "yahoo_api_standings",
        "captured_at": ctx.as_of.isoformat(),
        "league_id": ctx.league_id,
        "team_slots": ctx.team_slots,
        "completed_through_week": 0,
        "standings": {team: {"W": 0, "L": 0, "T": 0} for team in ctx.rosters},
        "current_scoreboard": {"week": 1, "updated_at": ctx.as_of.isoformat(), "matchups": matches},
    }
    return ctx, bundle(), snapshot


class PlayoffImpactTest(unittest.TestCase):
    def test_last_regular_season_week_still_includes_ongoing_matchups(self):
        ctx, data, snapshot = playoff_fixture()
        ctx.fantasy_calendar["weeks"] = []
        after = RosterScenario(copy.deepcopy(ctx.rosters), set())
        result = evaluate_playoff_impact(
            ctx, data, snapshot, after=after, simulations=100, playoff_spots=2
        )
        self.assertEqual(result["status"], "conditional_estimate", result.get("reasons"))
        self.assertEqual(result["full_future_weeks"], 0)
        self.assertEqual(result["current_week_included"], 1)

    def test_captured_current_production_is_a_constant_not_a_second_projection(self):
        ctx, _, _ = playoff_fixture()
        actual = {
            **dict.fromkeys(BOX_SCORE_KEYS, 0),
            "FGM": 40,
            "FGA": 80,
            "FTM": 10,
            "FTA": 15,
            "FG3M": 10,
            "PTS": 100,
        }
        first, second = _current_pair(
            ctx.engine,
            [1, 2],
            [3, 4],
            "2026-10-30",
            "2026-11-01",
            pd.Timestamp("2026-10-30"),
            {},
            {},
            {},
            {},
            actual,
            dict.fromkeys(BOX_SCORE_KEYS, 0),
        )
        self.assertEqual(first["mean"]["PTS"], 100)
        self.assertEqual(first["mean"]["FGM"], 40)
        self.assertEqual(first["var"]["PTS"], 0)
        self.assertEqual(second["mean"]["PTS"], 0)
        self.assertEqual(actual["PTS"], 100)

    def test_expired_budget_keeps_category_analysis_available_without_playoff_claim(self):
        ctx, data, snapshot = playoff_fixture()
        result = evaluate_playoff_impact(ctx, data, snapshot, deadline=0)
        self.assertEqual(result["status"], "needs_data")
        self.assertIn("time budget exhausted", result["reasons"][0])
        self.assertNotIn("teams", result)

    def test_partial_current_scoreboard_and_already_started_games_are_rejected(self):
        ctx, data, snapshot = playoff_fixture()
        snapshot["current_scoreboard"]["matchups"].pop()
        self.assertEqual(evaluate_playoff_impact(ctx, data, snapshot)["status"], "needs_data")
        ctx, data, snapshot = playoff_fixture()
        today = pd.Timestamp("2026-10-30")
        ctx.engine.schedule = pd.DataFrame(
            [
                {
                    "TEAM_ID": 1,
                    "GAME_DATE": today,
                    "GAME_ID": "now",
                    "TIPOFF_UTC": "2026-10-30T11:00:00Z",
                    "CLOCK_OBSERVED_AT": "2026-10-30T10:00:00Z",
                }
            ]
        )
        result = evaluate_playoff_impact(ctx, data, snapshot)
        self.assertEqual(result["status"], "needs_data")
        self.assertIn("started", result["reasons"][0])

    def test_missing_current_scores_or_standings_never_become_zero_actuals(self):
        for missing in ("standings", "current_scoreboard"):
            ctx, data, snapshot = playoff_fixture()
            del snapshot[missing]
            result = evaluate_playoff_impact(ctx, data, snapshot, playoff_spots=2, simulations=100)
            self.assertEqual(result["status"], "needs_data")
            self.assertNotIn("teams", result)

    def test_live_standings_or_incomplete_calendar_block_double_counting(self):
        ctx, data, snapshot = playoff_fixture()
        snapshot["completed_through_week"] = 1
        self.assertIn("double counting", evaluate_playoff_impact(ctx, data, snapshot)["reasons"][0])
        snapshot["completed_through_week"] = 0
        ctx.fantasy_calendar["complete_remaining_season"] = False
        self.assertEqual(evaluate_playoff_impact(ctx, data, snapshot)["status"], "needs_data")

    def test_identical_rosters_have_exact_zero_paired_delta_and_immutable_context(self):
        ctx, data, snapshot = playoff_fixture()
        original = copy.deepcopy(ctx.rosters)
        before_alphas = copy.deepcopy(ctx.engine.players[1].alphas)
        after = RosterScenario(
            copy.deepcopy(ctx.rosters), set(ctx.engine.yahoo_already_stashed_ids)
        )
        result = evaluate_playoff_impact(
            ctx, data, snapshot, after=after, simulations=500, playoff_spots=2
        )
        self.assertEqual(result["status"], "conditional_estimate", result.get("reasons"))
        self.assertEqual(result["current_week_included"], 1)
        self.assertEqual(result["full_future_weeks"], 2)
        for row in result["teams"].values():
            self.assertEqual(row["delta"], 0)
            self.assertEqual(row["delta_mc_standard_error"], 0)
        self.assertEqual(ctx.rosters, original)
        self.assertEqual(ctx.engine.players[1].alphas, before_alphas)
        self.assertFalse(result["tiebreak_exact"])
        json.dumps(result)

    def test_trade_changes_league_projection_and_current_scores_remain_included(self):
        ctx, data, snapshot = playoff_fixture()
        result = evaluate_playoff_impact(ctx, data, snapshot, simulations=500, playoff_spots=2)
        self.assertEqual(result["status"], "conditional_estimate", result.get("reasons"))
        self.assertEqual(set(result["teams"]), set(ctx.rosters))
        self.assertTrue(any(row["delta"] for row in result["teams"].values()))
        self.assertEqual(result["basis"], "trade_only_fixed_rosters")

    def test_dated_trade_intervals_keep_each_players_old_and_new_fantasy_team(self):
        original = RosterScenario({"0": [1, 2], "1": [3, 4]}, set())
        after = RosterScenario({"0": [3, 2], "1": [1, 4]}, set())
        when = pd.Timestamp("2026-11-01")
        rosters, starts, ends = _interval_rosters(original, after, when)
        self.assertEqual(set(rosters["0"]), {1, 2, 3})
        self.assertEqual(ends["0"][1], pd.Timestamp("2026-10-31"))
        self.assertEqual(starts["1"][1], when)
        self.assertNotIn(1, starts["0"])
        self.assertNotIn(1, ends["1"])

    def test_paired_deterministic_improvement_and_legacy_json_compatibility(self):
        records = {team: {"W": 0, "L": 0, "T": 0} for team in ("0", "1")}

        def fixtures(probability):
            return [
                {
                    "week": 1,
                    "home": "0",
                    "away": "1",
                    "categories": {str(c): {"win": probability, "tie": 0} for c in range(9)},
                }
            ]

        result = paired_qualification(
            records, fixtures(0), fixtures(1), simulations=100, playoff_spots=1
        )
        self.assertEqual(result["teams"]["0"]["delta"], 1)
        self.assertEqual(result["teams"]["0"]["delta_mc_standard_error"], 0)
        baseline = estimate_playoff_probabilities(
            records, fixtures(0), playoff_spots=1, simulations=100
        )
        self.assertNotIn("_qualification_draws", baseline)
        json.dumps(baseline)


def receiver_fixture():
    ctx, data = protected_slot_scenario()
    data["proposal"].update(
        our_team="1", other_team="0", give_yahoo_ids=[114], receive_yahoo_ids=[101, 102]
    )
    data["completion"]["enabled"] = False
    return ctx, data


class TradeReviewTest(unittest.TestCase):
    def test_demo_has_two_players_and_no_hidden_drop(self):
        ctx, data = bilateral_fixture()
        result = search_trades(ctx, data)
        analysis = result["opportunities"][0]["analysis"]
        self.assertEqual(analysis["roster_capacity"]["0"]["before_active"], 2)
        self.assertEqual(analysis["roster_capacity"]["0"]["after_active"], 2)
        self.assertTrue(
            all(a["drop_id"] is None for a in analysis["streaming"]["before"]["actions"])
        )
        report = render_search_report(result)
        self.assertIn("mevcut boş kadro yeri kullanılır", report)
        self.assertNotIn("boş yer bırakılır/kullanılır", report)

    def test_partner_gets_one_fa_and_our_gain_uses_the_same_joint_world(self):
        ctx, data = receiver_fixture()
        original = evaluate_trade(ctx, data)
        managed = evaluate_trade(ctx, data, complete_partner=True)
        partner = managed["partner_completion"]
        self.assertEqual(partner["status"], "applied")
        self.assertEqual(partner["options"][0]["player_id"], 29)
        self.assertEqual(managed["decision"]["basis"], "trade_plus_joint_fa")
        gains = effective_gains(managed)
        self.assertGreater(gains["partner"], effective_gains(original)["partner"])
        self.assertLess(gains["ours"], effective_gains(original)["ours"])
        self.assertAlmostEqual(gains["ours"] + gains["partner"], 0)
        self.assertEqual(partner["options"][0]["baseline_actions"], None)

    def test_missing_partner_budget_is_unknown_not_a_definitive_rejection(self):
        ctx, data = receiver_fixture()
        data["completion"]["adds_used_by_week"] = {}
        result = evaluate_trade(ctx, data, complete_partner=True)
        self.assertEqual(result["verdict"], "needs_data")
        self.assertFalse(effective_gains(result)["partner_replacement_known"])

    def test_fa_reserved_by_our_streaming_cannot_be_assigned_to_partner(self):
        ctx, data = receiver_fixture()
        data["streaming"] = {
            "enabled": True,
            "candidate_limit": 1,
            "beam_width": 2,
            "finalists": 2,
            "adds_used_by_week": {"2026-11-02": {"0": 0, "1": 0}},
        }
        result = evaluate_trade(ctx, data, complete_partner=True)
        self.assertTrue(result["streaming"]["before"]["actions"])
        self.assertIn(29, result["partner_completion"]["reserved_player_ids"])
        self.assertFalse(result["partner_completion"]["options"])

    def test_rank25_against_rank120_and_130_is_flagged_without_invented_price_curve(self):
        ctx, data = search_fixture()
        data["market_snapshot"] = market_snapshot(ctx)
        data["market_snapshot"]["players"]["101"]["rank"] = 120
        data["market_snapshot"]["players"]["102"]["rank"] = 130
        data["market_snapshot"]["players"]["103"]["rank"] = 25
        proposal = copy.deepcopy(data["proposal"])
        proposal["give_yahoo_ids"] = [101, 102]
        result = assess_market(ctx, data, proposal)
        self.assertTrue(result["blocked"])
        self.assertEqual(result["status"], "outlier")
        self.assertNotIn("totals", result)

    def test_negative_raw_two_for_one_reaches_final_with_verified_completion(self):
        ctx, data = protected_slot_scenario()
        for category in ("PTS", "REB", "AST", "STL", "BLK", "TOV", "FG3M"):
            ctx.engine.players[14].alphas[category] *= 0.875
        for category in ("FG", "FT"):
            ctx.engine.players[14].att_alphas[category] *= 0.875
        pure = copy.deepcopy(data)
        pure["completion"]["enabled"] = False
        self.assertLess(evaluate_trade(ctx, pure)["decision"]["delta"], -0.2)
        data["do_not_trade_yahoo_ids"] = [
            100 + p for ids in ctx.rosters.values() for p in ids if p not in (1, 2, 14)
        ]
        data["search"] = {
            "team_ids": ["1"],
            "package_types": ["2x1"],
            "shortlist_size": 1,
            "streaming_finalists": 1,
            "max_partner_loss_per_week": 9,
        }
        data["market_snapshot"] = market_snapshot(ctx, "replacement_adjusted_trade_value")
        data["market_snapshot"]["players"]["114"]["trade_value"] = 20
        result = search_trades(ctx, data)
        self.assertEqual(result["screened"][0]["screening"]["basis"], "trade_plus_fa")
        self.assertGreater(result["screened"][0]["screening"]["ours"], 0.05)
        self.assertTrue(result["opportunities"])


class TradeMathAuditTest(unittest.TestCase):
    def test_a_fifth_outgoing_player_is_rejected_in_both_trade_modes(self):
        ctx, data = context(), bundle()
        ctx.rosters = {"0": [1, 2, 3, 4, 5], "1": [6, 7, 8], "2": [], "3": []}
        data["proposal"]["give_yahoo_ids"] = [101, 102, 103, 104, 105]
        data["proposal"]["receive_yahoo_ids"] = [106, 107, 108]
        with self.assertRaises(ValueError):
            evaluate_trade(ctx, data)
        ctx.rosters = {"0": [1, 2, 3, 4, 5], "1": [6, 7], "2": [8], "3": []}
        data["proposal"]["transfers"] = [
            {"from_team": "0", "to_team": "1", "yahoo_player_id": str(100 + pid)}
            for pid in range(1, 6)
        ] + [
            {"from_team": "1", "to_team": "2", "yahoo_player_id": "106"},
            {"from_team": "1", "to_team": "2", "yahoo_player_id": "107"},
            {"from_team": "2", "to_team": "0", "yahoo_player_id": "108"},
        ]
        with self.assertRaises(ValueError):
            evaluate_trade(ctx, data)

    def test_local_injury_status_never_authorizes_provider_il_placement(self):
        assistant = SimpleNamespace(
            players={
                1: SimpleNamespace(injury_status="OUT"),
                2: SimpleNamespace(injury_status="HEALTHY"),
                3: SimpleNamespace(injury_status="HEALTHY"),
            },
            resolve_player_id=lambda name, **_: {"Local injured": 1, "Yahoo injured": 2}.get(name),
        )
        state = {
            "yahoo_roster_players": {
                "0": [
                    {"name": "Local injured", "status": ""},
                    {"name": "Yahoo injured", "status": "INJ"},
                ]
            }
        }
        self.assertEqual(provider_il_eligible_ids(assistant, state, {3}), {2, 3})
        state["yahoo_roster_players"]["0"][1]["status"] = "QUESTIONABLE"
        self.assertEqual(provider_il_eligible_ids(assistant, state, {3}), {3})

    def test_verified_specific_positions_avoid_false_approximation_warning(self):
        self.assertEqual(verified_yahoo_positions(["PG", "SG", "G", "UTIL"]), ("PG", "SG"))
        self.assertIsNone(verified_yahoo_positions(["G", "UTIL"]))
        self.assertIsNone(verified_yahoo_positions(["PG", "unknown"]))
        ctx, data = context(), bundle()
        data.pop("eligible_positions")
        ctx.verified_position_ids = set(ctx.engine.players)
        result = evaluate_trade(ctx, data)
        self.assertNotIn(
            "Exact Yahoo eligibility is incomplete; NBA positions are approximate.",
            result["conditions"],
        )
        ctx.verified_position_ids.remove(1)
        result = evaluate_trade(ctx, data)
        self.assertIn(
            "Exact Yahoo eligibility is incomplete; NBA positions are approximate.",
            result["conditions"],
        )

    def test_four_players_per_side_are_supported_by_manual_engine(self):
        ctx, data = context(equal=True), bundle()
        ctx.rosters = {"0": [1, 2, 5, 6], "1": [3, 4, 7, 8], "2": [], "3": []}
        data["proposal"]["give_yahoo_ids"] = [101, 102, 105, 106]
        data["proposal"]["receive_yahoo_ids"] = [103, 104, 107, 108]
        result = evaluate_trade(ctx, data)
        self.assertAlmostEqual(result["teams"]["0"]["all_supplied_weeks"]["delta"], 0)

    def test_three_team_twelve_player_cycle_preserves_neutral_equivalent_rosters(self):
        ctx, data = context(equal=True), bundle()
        for pid in range(9, 13):
            ctx.engine.players[pid] = copy.deepcopy(ctx.engine.players[1])
            ctx.engine.players[pid].name = f"Three-team fixture {pid}"
            ctx.yahoo_ids[str(100 + pid)] = pid
            ctx.engine.pos_dict[pid] = "PG,SG,SF,PF,C"
        ctx.engine.team_map = dict.fromkeys(ctx.engine.players, 1)
        ctx.rosters = {"0": [1, 2, 3, 4], "1": [5, 6, 7, 8], "2": [9, 10, 11, 12], "3": []}
        data["proposal"]["transfers"] = [
            {
                "from_team": team,
                "to_team": {"0": "1", "1": "2", "2": "0"}[team],
                "yahoo_player_id": str(100 + pid),
            }
            for team in ("0", "1", "2")
            for pid in ctx.rosters[team]
        ]
        result = evaluate_trade(ctx, data)
        self.assertEqual(len(result["transfers"]), 12)
        for team in result["teams"].values():
            self.assertAlmostEqual(team["all_supplied_weeks"]["delta"], 0)

    def test_small_positive_three_team_gain_has_no_hidden_search_threshold(self):
        ctx, data = context(equal=True), bundle()
        ctx.engine.players[5].alphas["PTS"] *= 1.01
        data["proposal"]["transfers"] = [
            {"from_team": "0", "to_team": "1", "yahoo_player_id": "101"},
            {"from_team": "1", "to_team": "2", "yahoo_player_id": "103"},
            {"from_team": "2", "to_team": "0", "yahoo_player_id": "105"},
        ]
        result = evaluate_trade(ctx, data)
        self.assertGreater(result["decision"]["delta"], 0)
        self.assertLess(result["decision"]["delta"], 0.05 * 2)
        self.assertEqual(result["verdict"], "conditional_accept")
        self.assertEqual(
            result["decision"]["delta"], result["teams"]["0"]["all_supplied_weeks"]["delta"]
        )
        self.assertEqual(
            result["decision"]["delta_without_spillover"],
            result["teams"]["0"]["without_spillover_delta"],
        )

    def test_category_point_arithmetic_and_direct_opponent_complementarity(self):
        result = evaluate_trade(context(), bundle())
        for values in result["teams"].values():
            total = values["all_supplied_weeks"]
            self.assertAlmostEqual(
                total["delta"], sum(c["delta_points"] for c in total["categories"].values())
            )
        for side in ("before", "after"):
            pair_points = sum(
                result["teams"][team]["weekly"][0][side]["points"] for team in ("0", "1")
            )
            self.assertAlmostEqual(pair_points, 9)


if __name__ == "__main__":
    unittest.main()

"""Dated streaming regressions with synthetic rosters, rates and FA evidence."""

import copy
import pickle
import unittest
from datetime import timedelta

import pandas as pd

from src.matchup_engine import MatchupEngine
from src.streaming import apply_move, streaming_comparison
from src.trade_packages import RosterScenario, trade_packages
from src.trade_report import render_trade_report
from src.trades import evaluate_trade
from tests.test_trades import protected_slot_scenario


def streaming_fixture(two_weeks=False):
    """One free post-trade seat; early and late FAs require a real swap."""
    ctx, data = protected_slot_scenario()
    players = copy.deepcopy(ctx.engine.players)
    players[30] = copy.deepcopy(players[29])
    players[30].name = "Norman Powell"
    rows = ctx.engine.schedule[~ctx.engine.schedule.TEAM_ID.isin((1029, 1030))].to_dict("records")
    if two_weeks:
        rows += [
            {
                **row,
                "GAME_DATE": row["GAME_DATE"] + pd.Timedelta(days=7),
                "GAME_ID": row["GAME_ID"] + "-next",
            }
            for row in list(rows)
        ]
        dates = {29: ("2026-11-08",), 30: ("2026-11-09", "2026-11-15")}
        data["weeks"].append(
            {"start": "2026-11-09", "end": "2026-11-15", "fixtures": [["0", "1"], ["2", "3"]]}
        )
    else:
        dates = {29: ("2026-11-02", "2026-11-04"), 30: ("2026-11-06", "2026-11-08")}
    rows += [
        {"TEAM_ID": 1000 + pid, "GAME_DATE": pd.Timestamp(date), "GAME_ID": f"stream-{pid}-{date}"}
        for pid, days in dates.items()
        for date in days
    ]
    ctx.engine = MatchupEngine(
        players,
        pd.DataFrame(rows),
        pd.DataFrame([{"PLAYER_ID": pid, "POSITION": "PG,SG,SF,PF,C"} for pid in players]),
        team_map={pid: 1000 + pid for pid in players},
        yahoo_il_eligible_ids=set(),
        use_positional_depth_and_injury_boost=False,
    )
    ctx.available_players[30] = {"status": "FA", "waiver": None, "yahoo_player_id": "130"}
    data["do_not_drop_yahoo_ids"].append(114)
    data["completion"]["enabled"] = False
    data["streaming"] = {
        "enabled": True,
        "candidate_limit": 2,
        "beam_width": 6,
        "finalists": 6,
        "min_gain_per_week": 0.001,
        "adds_used_by_week": {week["start"]: {"0": 0} for week in data["weeks"]},
    }
    data["rules"]["max_weekly_adds"] = 3
    return ctx, data


def _full_week_score(engine, scenario):
    mine = engine.get_expected_weekly_distribution(
        scenario.projection_roster("0"),
        "2026-11-02",
        "2026-11-08",
        as_of_date="2026-10-30",
        player_start_dates=scenario.starts,
        player_end_dates=scenario.ends,
    )
    opponent = engine.get_expected_weekly_distribution(
        scenario.projection_roster("1"), "2026-11-02", "2026-11-08", as_of_date="2026-10-30"
    )
    value = engine.evaluate_h2h_matchup(mine, opponent)[0]
    return {"0": {"normal": value, "sensitivity": value, "near": value}}


class StreamingTest(unittest.TestCase):
    def test_early_then_late_pickups_keep_all_credited_games(self):
        ctx, data = streaming_fixture()
        result = evaluate_trade(ctx, data)
        stream = result["streaming"]
        self.assertEqual(stream["status"], "planned")
        actions = stream["after"]["actions"]
        self.assertEqual([a["add_id"] for a in actions], [29, 30])
        self.assertEqual(actions[1]["drop_id"], 29)
        self.assertEqual(len({a["date"] for a in actions}), len(actions))
        self.assertEqual(stream["before"]["actions"], [])
        budget = stream["after"]["weekly_budget"]["2026-11-02"]
        self.assertEqual(budget["planned_adds"], 2)
        self.assertEqual(budget["remaining"], 1)
        week = stream["teams"]["0"]["weekly"][0]
        lineups = week["after"]["lineups"]
        for date in ("2026-11-02", "2026-11-04"):
            self.assertIn(29, lineups[date])
            self.assertNotIn(30, lineups[date])
        for date in ("2026-11-06", "2026-11-08"):
            self.assertIn(30, lineups[date])
            self.assertNotIn(29, lineups[date])
        self.assertEqual(result["decision"]["basis"], "trade_plus_streaming")
        self.assertAlmostEqual(result["decision"]["delta"], stream["delta"])
        report = render_trade_report(result)
        self.assertIn("Luke Kennard", report)
        self.assertIn("Norman Powell", report)

    def test_full_weekly_projection_preserves_shared_player_uncertainty(self):
        ctx, data = streaming_fixture()
        result = evaluate_trade(ctx, data)["streaming"]
        package = trade_packages(ctx, data, [1, 2], [14])[0][0]
        for action in result["after"]["actions"]:
            package = apply_move(
                package, "0", action["add_id"], pd.Timestamp(action["date"]), action["drop_id"]
            )
        engine = copy.deepcopy(ctx.engine)
        ids = package.projection_roster("0")
        kwargs = {
            "as_of_date": "2026-10-30",
            "player_start_dates": package.starts,
            "player_end_dates": package.ends,
        }
        weekly = engine.get_expected_weekly_distribution(ids, "2026-11-02", "2026-11-08", **kwargs)
        daily_variance = sum(
            engine.get_expected_weekly_distribution(ids, date, date, **kwargs)["var"]["PTS"]
            for date in pd.date_range("2026-11-02", "2026-11-08")
        )
        self.assertGreater(weekly["var"]["PTS"], daily_variance)
        self.assertAlmostEqual(
            weekly["mean"]["PTS"],
            result["teams"]["0"]["weekly"][0]["after"]["categories"]["PTS"]["production"],
        )

    def test_budget_exhaustion_and_unknown_usage_do_not_assume_zero(self):
        for usage in ({"2026-11-02": {"0": 3}}, {}):
            ctx, data = streaming_fixture()
            data["streaming"]["adds_used_by_week"] = usage
            result = evaluate_trade(ctx, data)["streaming"]
            self.assertEqual(result["before"]["actions"], [])
            self.assertEqual(result["after"]["actions"], [])
            self.assertEqual(result["after"]["weekly_budget"]["2026-11-02"]["planned_adds"], 0)
            if not usage:
                self.assertIsNone(result["after"]["weekly_budget"]["2026-11-02"]["remaining"])

    def test_week_boundary_resets_budget_but_carries_roster_history(self):
        ctx, data = streaming_fixture(two_weeks=True)
        data["rules"]["max_weekly_adds"] = 1
        ctx.available_players[29].update(status="W", waiver={"date": "2026-11-08"})
        result = evaluate_trade(ctx, data)["streaming"]
        actions = result["after"]["actions"]
        self.assertEqual([a["add_id"] for a in actions], [29, 30])
        self.assertEqual(actions[0]["date"], "2026-11-08")
        self.assertGreaterEqual(actions[1]["date"], "2026-11-09")
        self.assertEqual(actions[1]["drop_id"], 29)
        for start in ("2026-11-02", "2026-11-09"):
            self.assertEqual(result["after"]["weekly_budget"][start]["planned_adds"], 1)
            self.assertEqual(result["after"]["weekly_budget"][start]["remaining"], 0)
        self.assertIn(29, result["teams"]["0"]["weekly"][0]["after"]["lineups"]["2026-11-08"])
        self.assertIn(30, result["after"]["final_roster"])
        self.assertNotIn(29, result["after"]["final_roster"])

    def test_waiver_clearance_and_unknown_dates(self):
        ctx, data = streaming_fixture()
        ctx.available_players[29].update(status="W", waiver={"date": "2026-11-04"})
        result = evaluate_trade(ctx, data)["streaming"]
        for action in result["after"]["actions"]:
            if action["add_id"] == 29:
                self.assertGreaterEqual(action["date"], "2026-11-04")
        self.assertNotIn(29, result["teams"]["0"]["weekly"][0]["after"]["lineups"]["2026-11-02"])
        ctx.available_players[29]["waiver"] = {"date": None}
        result = evaluate_trade(ctx, data)["streaming"]
        self.assertNotIn(29, result["candidate_ids"])
        self.assertNotIn(29, [a["add_id"] for a in result["after"]["actions"]])

    def test_protected_and_stashed_players_are_never_displaced(self):
        ctx, data = streaming_fixture()
        ctx.engine.yahoo_already_stashed_ids.add(13)
        ctx.il_eligible_ids.add(13)
        result = evaluate_trade(ctx, data)["streaming"]
        protected = set(range(1, 15))
        for path in (result["before"], result["after"]):
            self.assertTrue(all(a["drop_id"] not in protected for a in path["actions"]))
            self.assertIn(13, path["final_roster"])

    def test_reacquisition_and_two_same_day_moves_are_rejected(self):
        ctx, _ = streaming_fixture()
        start = RosterScenario(copy.deepcopy(ctx.rosters), set())
        first = apply_move(start, "0", 29, pd.Timestamp("2026-11-02"), 13)
        with self.assertRaises(ValueError):
            apply_move(first, "0", 30, pd.Timestamp("2026-11-02"), 29)
        second = apply_move(first, "0", 30, pd.Timestamp("2026-11-03"), 29)
        with self.assertRaises(ValueError):
            apply_move(second, "0", 29, pd.Timestamp("2026-11-04"), 30)
        stashed = RosterScenario(copy.deepcopy(ctx.rosters), {13})
        with self.assertRaises(ValueError):
            apply_move(stashed, "0", 29, pd.Timestamp("2026-11-02"), 13)

    def test_trade_cost_is_charged_only_to_traded_path_and_its_actual_week(self):
        ctx, data = streaming_fixture()
        data["rules"].update(max_weekly_adds=1, trade_add_cost=1)
        data["proposal"]["effective_date"] = "2026-11-02"
        result = evaluate_trade(ctx, data)["streaming"]
        self.assertEqual(result["before"]["weekly_budget"]["2026-11-02"]["trade_cost"], 0)
        self.assertEqual(result["after"]["weekly_budget"]["2026-11-02"]["trade_cost"], 1)
        self.assertEqual(result["after"]["actions"], [])
        data["proposal"]["effective_date"] = "2026-11-01"
        result = evaluate_trade(ctx, data)["streaming"]
        self.assertEqual(result["after"]["weekly_budget"]["2026-11-02"]["trade_cost"], 0)
        self.assertEqual(len(result["after"]["actions"]), 1)

    def test_same_starting_state_has_equal_optimized_values(self):
        ctx, data = streaming_fixture()
        engine = copy.deepcopy(ctx.engine)
        package = trade_packages(ctx, data, [1, 2], [14])[0][0]

        result = streaming_comparison(
            ctx,
            data,
            package,
            copy.deepcopy(package),
            lambda s: _full_week_score(engine, s),
            lambda _before, _after: {},
            engine,
        )
        self.assertEqual(result["before"]["actions"], result["after"]["actions"])
        self.assertAlmostEqual(result["delta"], 0)

    def test_baseline_only_streaming_can_reverse_a_positive_raw_trade(self):
        ctx, data = streaming_fixture()
        # Baseline has one free seat, while the 1-for-2 fills it with protected players.
        ctx.rosters["0"].remove(13)
        ctx.rosters["2"].append(13)
        data["proposal"].update(give_yahoo_ids=[101], receive_yahoo_ids=[114, 115])
        data["drop_yahoo_ids"] = {}
        data["do_not_drop_yahoo_ids"].append(115)
        for pid in (29, 30):
            for cat in ("PTS", "REB", "AST", "STL", "BLK", "TOV", "FG3M"):
                ctx.engine.players[pid].alphas[cat] *= 1.5
            for cat in ("FG", "FT"):
                ctx.engine.players[pid].att_alphas[cat] *= 1.5
        result = evaluate_trade(ctx, data)
        streaming = result["streaming"]
        self.assertGreater(result["teams"]["0"]["all_supplied_weeks"]["delta"], 0)
        self.assertTrue(streaming["before"]["actions"])
        self.assertEqual(streaming["after"]["actions"], [])
        self.assertLess(streaming["delta"], 0)
        self.assertEqual(result["decision"]["basis"], "trade_plus_streaming")
        self.assertEqual(result["verdict"], "reject_suggested")
        self.assertAlmostEqual(result["decision"]["delta"], streaming["delta"])

    def test_same_final_roster_keeps_distinct_history_and_seed_lower_bounds(self):
        ctx, data = streaming_fixture()
        original = RosterScenario(copy.deepcopy(ctx.rosters), set())
        trade = trade_packages(ctx, data, [1, 2], [14])[0][0]
        early = apply_move(trade, "0", 29, pd.Timestamp("2026-11-02"))
        early = apply_move(early, "0", 30, pd.Timestamp("2026-11-06"), 29)
        direct = apply_move(trade, "0", 30, pd.Timestamp("2026-11-06"))
        self.assertEqual(sorted(early.rosters["0"]), sorted(direct.rosters["0"]))
        engine = copy.deepcopy(ctx.engine)
        self.assertGreater(
            _full_week_score(engine, early)["0"]["normal"],
            _full_week_score(engine, direct)["0"]["normal"],
        )
        data["streaming"].update(candidate_limit=1, beam_width=1, finalists=1)
        result = streaming_comparison(
            ctx,
            data,
            original,
            trade,
            lambda s: _full_week_score(engine, s),
            lambda _before, _after: {},
            engine,
            seeds={"after": [direct, early]},
        )
        self.assertEqual(result["search"]["candidate_count"], 2)
        self.assertGreaterEqual(result["search"]["after"]["evaluated"], 3)
        self.assertEqual([a["add_id"] for a in result["after"]["actions"]], [29, 30])
        self.assertGreaterEqual(
            result["after"]["values"]["0"]["normal"], _full_week_score(engine, early)["0"]["normal"]
        )

    def test_context_is_immutable_and_outputs_are_deterministic(self):
        ctx, data = streaming_fixture()
        original = pickle.dumps(ctx)
        result = evaluate_trade(ctx, data)
        self.assertEqual(pickle.dumps(ctx), original)
        self.assertEqual(result, evaluate_trade(ctx, data))

    def test_stale_or_wrong_sync_fa_does_not_create_a_streaming_plan(self):
        for change in (
            {"sync_id": "wrong"},
            {"updated_at": (streaming_fixture()[0].as_of - timedelta(hours=25)).isoformat()},
        ):
            ctx, data = streaming_fixture()
            ctx.availability_audit.update(change)
            result = evaluate_trade(ctx, data)["streaming"]
            self.assertEqual(result["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()

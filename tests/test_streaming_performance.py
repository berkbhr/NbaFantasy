"""Exact streaming surrogate reuse against the previous uncached entry loop."""

import copy
import pickle
import unittest
from unittest.mock import patch

import pandas as pd

from src import streaming
from src.trades import evaluate_trade
from tests.test_streaming import streaming_fixture


class LegacyCandidates:
    """Reference: construct candidate entries for each requested active roster."""

    def __init__(self, engine, player_ids, first, last, as_of):
        self.engine, self.as_of = engine, as_of
        self.stats = {"candidate_requests": 0, "prepared_player_dates": 0}

    def entries(self, when, active):
        self.stats["candidate_requests"] += 1
        projections = self.engine._daily_projections(when, self.as_of, True, active)
        entries = []
        for pid in active:
            tid = self.engine.team_map.get(pid)
            if when not in self.engine._get_player_schedule(tid, when, when):
                continue
            b2b = when - pd.Timedelta(days=1) in self.engine._all_schedule_dates.get(tid, set())
            probability = self.engine.players[pid].get_effective_game_availability(
                is_b2b=b2b, game_date=when, as_of_date=self.as_of
            )
            mu, _ = projections[pid]
            entries.append(
                {
                    "ID": pid,
                    "POS": self.engine.pos_dict.get(pid, "UTIL"),
                    "PROJ": {cat: value * probability for cat, value in mu.items()},
                }
            )
        self.stats["prepared_player_dates"] += len(entries)
        return entries


def without_cache_counters(result):
    result = copy.deepcopy(result)
    result["streaming"]["search"].pop("surrogate_cache", None)
    return result


class StreamingPerformanceTest(unittest.TestCase):
    def test_reused_entries_match_reference_with_injury_return_b2b_and_no_aliases(self):
        ctx, data = streaming_fixture(two_weeks=True)
        ctx.engine.use_positional_depth_and_injury_boost = True
        # NBA teammates retain the same roles regardless of fantasy ownership.
        ctx.engine.team_map[3] = ctx.engine.team_map[29]
        ctx.engine.players[3].update_injury_status(
            "OUT", expected_return="2026-11-04", report_date="2026-10-30"
        )
        ctx.engine.players[29].update_injury_status(
            "QUESTIONABLE", expected_return="2026-11-05", report_date="2026-10-30"
        )
        ctx.engine.players[30].is_b2b_rest = True
        # Also test yesterday's completed game still creates B2B rest today.
        tid = ctx.engine.team_map[30]
        ctx.engine._all_schedule_dates[tid].add(pd.Timestamp("2026-11-11"))
        before = pickle.dumps(ctx.engine.players)
        model, reference_model = copy.deepcopy(ctx.engine), copy.deepcopy(ctx.engine)
        ids = sorted(set(ctx.rosters["0"]) | {3, 14, 29, 30})
        as_of, first, last = map(pd.Timestamp, ("2026-10-30", "2026-11-02", "2026-11-15"))
        fast = streaming._DailySurrogateCandidates(model, ids, first, last, as_of)
        slow = LegacyCandidates(reference_model, ids, first, last, as_of)
        with model.projection_session(), reference_model.projection_session():
            for date in pd.date_range(first, last):
                for active in (tuple(ids), tuple(ids[1:]), tuple(reversed(ids[::2]))):
                    actual, expected = fast.entries(date, active), slow.entries(date, active)
                    self.assertEqual(list(actual), expected)
                    for entry in actual:
                        with self.assertRaises(TypeError):
                            entry["PROJ"]["PTS"] = 0
                        with self.assertRaises(TypeError):
                            entry["POS"] = "C"
        self.assertEqual(pickle.dumps(ctx.engine.players), before)
        self.assertEqual(fast.stats["prepared_days"], 14)
        self.assertGreater(fast.stats["reused_player_dates"], 0)
        self.assertLess(fast.stats["prepared_player_dates"], slow.stats["prepared_player_dates"])

    def test_entire_plans_match_reference_across_week_boundary_and_dated_drops(self):
        ctx, data = streaming_fixture(two_weeks=True)
        data["rules"]["max_weekly_adds"] = 1
        ctx.available_players[29].update(status="W", waiver={"date": "2026-11-08"})
        with patch.object(streaming, "_DailySurrogateCandidates", LegacyCandidates):
            legacy = evaluate_trade(ctx, data)
        actual = evaluate_trade(ctx, data)
        self.assertEqual(without_cache_counters(actual), without_cache_counters(legacy))
        stream = actual["streaming"]
        self.assertEqual([a["add_id"] for a in stream["after"]["actions"]], [29, 30])
        self.assertIn(29, stream["teams"]["0"]["weekly"][0]["after"]["lineups"]["2026-11-08"])
        self.assertEqual(stream["after"]["actions"][1]["drop_id"], 29)
        stats = stream["search"]["surrogate_cache"]
        old_stats = legacy["streaming"]["search"]["surrogate_cache"]
        self.assertGreater(stats["reused_player_dates"], 0)
        self.assertLess(stats["prepared_player_dates"], old_stats["prepared_player_dates"])
        self.assertGreater(stream["search"]["after"]["surrogate_states"]["reused_states"], 0)

    def test_two_week_scoring_period_and_injury_sensitivity_match_reference(self):
        ctx, data = streaming_fixture(two_weeks=True)
        data["weeks"] = [{**data["weeks"][0], "end": data["weeks"][-1]["end"]}]
        data["streaming"]["adds_used_by_week"] = {data["weeks"][0]["start"]: {"0": 0}}
        ctx.engine.use_positional_depth_and_injury_boost = True
        ctx.engine.team_map[3] = ctx.engine.team_map[29]
        ctx.engine.players[3].update_injury_status(
            "OUT", expected_return="2026-11-09", report_date="2026-10-30"
        )
        ctx.engine.players[29].update_injury_status(
            "QUESTIONABLE", expected_return="2026-11-04", report_date="2026-10-30"
        )
        initial = pickle.dumps(ctx)
        with patch.object(streaming, "_DailySurrogateCandidates", LegacyCandidates):
            legacy = evaluate_trade(ctx, data)
        actual = evaluate_trade(ctx, data)
        self.assertEqual(without_cache_counters(actual), without_cache_counters(legacy))
        self.assertEqual(pickle.dumps(ctx), initial)
        self.assertEqual(actual["streaming"]["search"]["surrogate_cache"]["prepared_days"], 14)


if __name__ == "__main__":
    unittest.main()

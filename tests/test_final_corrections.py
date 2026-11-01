"""Independent contracts for the two audits; synthetic data, no user-cache writes."""

import copy
import hashlib
import json
import math
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.bayesian_model import DECAY_LAMBDA_BY_STAT, BayesianPlayer
from src.live_draft_assistant import LiveDraftAssistant
from src.matchup_engine import ALL_CATEGORIES, WEEKLY_VAR_INFLATION_BY_CAT, MatchupEngine
from src.model_policy import ModelPolicy
from src.priors import AGG_COLS, load_prior_season
from src.probability import CategoryProbabilities
from src.trade_projection_cache import TradeProjectionCache
from tests.test_consensus_contracts import _make_player


def total(gp=40.0):
    return {**dict.fromkeys(AGG_COLS, 100.0), "MIN": gp * 30, "GP": gp, "ROLE_MPG": 30.0}


class SeasonEvidenceTests(unittest.TestCase):
    def prior(self, primary=None, secondary=None, live=False, files=True, season="2026_27"):
        pre = pd.DataFrame(
            [
                {**dict.fromkeys(ALL_CATEGORIES, 0.0), "PLAYER_ID": 1, "MIN": 25.0},
                {**dict.fromkeys(ALL_CATEGORIES, 0.0), "PLAYER_ID": 3, "MIN": 24.0},
            ]
        )
        roster = pd.DataFrame({"PLAYER_ID": [1, 3], "DRAFT_NUMBER": [60, 1]})
        seen = []

        def read(path, **kwargs):
            seen.append(str(path))
            return pre.copy() if "preseason" in str(path) else roster.copy()

        def totals(name):
            return (primary if name == season else secondary) or {}, {}

        with (
            patch("src.priors._load_single_season_totals", side_effect=totals),
            patch("src.priors.os.path.exists", return_value=files),
            patch("src.priors.pd.read_parquet", side_effect=read),
        ):
            result = load_prior_season(season, include_target_evidence=live)
        return result, seen

    def test_future_live_preseason_return_rookie_and_gp_separation(self):
        result, seen = self.prior({1: total(40)}, {1: total(70)}, live=True)
        self.assertTrue(any("preseason_logs_2027_28" in p for p in seen))
        self.assertEqual(result[1]["AVAIL_GP"], 40)
        self.assertAlmostEqual(result[1]["GP"], 61.0)
        self.assertTrue(result[3]["IS_ROOKIE_PRIOR"])
        rookie = BayesianPlayer(3, "Rookie")
        rookie.initialize_priors(result[3])
        self.assertEqual(rookie.avail_alpha, 20 + 0.5 * 68)

    def test_replay_never_reads_target_even_when_files_exist(self):
        for season in ["2024_25", "2025_26", "2026_27"]:
            with self.subTest(season=season):
                result, seen = self.prior({1: total(40)}, {1: total(70)}, season=season)
                self.assertEqual(seen, [])
                self.assertNotIn(3, result)
                self.assertAlmostEqual(result[1]["GP"], 52)

    def test_single_season_secondary_only_and_missing_files(self):
        single, _ = self.prior({1: total(40)}, {}, live=False)
        self.assertEqual(single[1]["GP"], 40)
        # A player can lack the primary season while another supplies that file.
        old, _ = self.prior({2: total(40)}, {1: total(70)}, live=False)
        self.assertAlmostEqual(old[1]["GP"], 70 * 0.75)
        missing, seen = self.prior({1: total(40)}, {1: total(70)}, live=True, files=False)
        self.assertEqual(seen, [])
        self.assertNotIn(3, missing)
        self.assertEqual(missing[1]["AVAIL_GP"], 40)

    def test_current_season_uses_identical_live_rules(self):
        current, _ = self.prior({1: total(40)}, {1: total(70)}, live=True, season="2025_26")
        future, _ = self.prior({1: total(40)}, {1: total(70)}, live=True)
        self.assertEqual(current, future)

    def test_live_roster_loader_and_missing_or_replay(self):
        for live, exists in [(True, True), (False, True), (True, False)]:
            obj = LiveDraftAssistant.__new__(LiveDraftAssistant)
            obj.prior_season, obj.target_season = "2026_27", "2027_28"
            obj.include_target_evidence, obj.team_abbr_dict = live, {}
            roster = pd.DataFrame(
                {"PLAYER_ID": [3], "POSITION": ["G"], "TEAM_ABBREVIATION": ["ABC"]}
            )
            seen = []

            def read(path):
                seen.append(str(path))
                if "player_positions" in str(path):
                    return pd.DataFrame({"PLAYER_ID": [1], "POSITION": ["C"]})
                if "schedule" in str(path):
                    return pd.DataFrame({"GAME_DATE": ["2027-10-20"]})
                return roster.copy()

            with (
                patch("src.live_draft_assistant.os.path.exists", return_value=exists),
                patch("src.live_draft_assistant.pd.read_parquet", side_effect=read),
            ):
                obj.load_data()
            self.assertEqual(not obj.active_roster_df.empty, live and exists)
            self.assertEqual(any("active_roster_2027_28" in p for p in seen), live and exists)

    def test_engine_future_roster_and_historical_team_mapping(self):
        for live, exists in [(True, True), (False, True), (True, False)]:
            e = MatchupEngine.__new__(MatchupEngine)
            e.prior_season, e.season = "2026_27", "2027_28"
            e.include_target_evidence, e.prior_team_map = live, {}
            past = pd.DataFrame({"PLAYER_ID": [1], "TEAM_ID": [10], "GAME_DATE": ["2026-12-01"]})
            future = pd.DataFrame({"PLAYER_ID": [1], "TEAM_ID": [20]})
            with (
                patch("pathlib.Path.exists", return_value=exists),
                patch(
                    "src.matchup_engine.pd.read_parquet",
                    side_effect=lambda p, **kw: future if "active_roster" in str(p) else past,
                ),
            ):
                result = e._load_team_map()
            self.assertEqual(result, {1: 20 if live else 10} if exists else {})

    def test_initialize_ai_future_names_and_replay_target_exclusion(self):
        for live in [False, True]:
            obj = LiveDraftAssistant.__new__(LiveDraftAssistant)
            obj.prior_season, obj.target_season = "2026_27", "2027_28"
            obj.include_target_evidence = live
            obj.priors = {1: total(), 2: total()}
            if live:
                obj.priors[3] = total()
            obj.pos_averages, obj.pos_dict, obj.players = {}, {}, {}
            obj.available_player_ids = set()
            obj.external_pool_ids = None
            obj.model_policy = ModelPolicy()
            obj.active_roster_df = (
                pd.DataFrame({"PLAYER_ID": [4], "PLAYER_NAME": ["Roster rookie"]})
                if live
                else pd.DataFrame()
            )
            obj.schedule_df, obj.df_pos = pd.DataFrame(), pd.DataFrame()
            obj.use_positional_depth_and_injury_boost = False
            obj.draw_value, obj.objective = 0.5, "category_points"
            obj._refresh_projected_stats_dict = lambda: None
            seen = []

            def read(path, **kwargs):
                seen.append(str(path))
                pid = 3 if "preseason" in str(path) else 2 if "2025_26" in str(path) else 1
                return pd.DataFrame({"PLAYER_ID": [pid], "PLAYER_NAME": [str(pid)]})

            with (
                patch("src.live_draft_assistant.os.path.exists", return_value=True),
                patch("src.live_draft_assistant.pd.read_parquet", side_effect=read),
                patch("src.live_draft_assistant.MatchupEngine") as factory,
            ):
                obj.initialize_ai()
            self.assertEqual(set(obj.players), {1, 2, 3, 4} if live else {1, 2})
            self.assertEqual(any("preseason_logs_2027_28" in p for p in seen), live)
            self.assertEqual(factory.call_args.kwargs["include_target_evidence"], live)


class RoleAndStateTests(unittest.TestCase):
    def engine(self, rho=0.0):
        players = {1: _make_player(1, 30), 2: _make_player(2, 24)}
        schedule = pd.DataFrame(
            [
                {"TEAM_ID": team, "GAME_DATE": day, "GAME_ID": f"{team}/{day}"}
                for team in [10, 20]
                for day in pd.date_range("2026-10-20", periods=3)
            ]
        )
        return MatchupEngine(
            players,
            schedule,
            pd.DataFrame(),
            team_map={1: 10, 2: 20},
            role_covariance_correlation=rho,
        )

    def test_role_setting_reaches_matchup_simulation_and_cache_key(self):
        base, candidate = self.engine(), self.engine(0.5)
        args = ([1], [2], "2026-10-20", "2026-10-22")
        a, b = base.project_matchup(*args), candidate.project_matchup(*args)
        self.assertGreater(b[0]["var"]["PTS"], a[0]["var"]["PTS"])
        self.assertNotEqual(a[3]["PTS"], b[3]["PTS"])
        self.assertEqual(candidate.simulate_matchup(*args), b[3])
        self.assertNotEqual(
            TradeProjectionCache.engine_key(base), TradeProjectionCache.engine_key(candidate)
        )
        default = candidate.get_expected_weekly_distribution([1], *args[2:])
        zero = candidate.get_expected_weekly_distribution(
            [1], *args[2:], role_covariance_correlation=0
        )
        self.assertGreater(default["var"]["FGA"], zero["var"]["FGA"])

    def test_shooting_impact_with_unequal_minutes_probabilities_and_both_correlations(self):
        e = self.engine(0.4)
        e.availability_correlation = 0.3

        def daily(day, as_of, live, eligible):
            p = e.players[1]
            p.expected_minutes, p.minutes_var = (20.0, 9.0) if day.day == 20 else (32.0, 49.0)
            return {1: e._build_player_game_projection(1)}

        with (
            patch.object(e, "_daily_projections", side_effect=daily),
            patch.object(e.players[1], "get_effective_game_availability", side_effect=[0.6, 0.8]),
        ):
            d = e.get_expected_weekly_distribution([1], "2026-10-20", "2026-10-21")
        a, b = d["players"][0]["games"]
        joint = 0.6 * 0.8 + min(0.3 * math.sqrt(0.6 * 0.4 * 0.8 * 0.2), min(0.6, 0.8) - 0.6 * 0.8)
        for s in ["FG", "FT"]:
            for key in [s + "A", s + "M"]:
                v1, v2 = a["var"][key], b["var"][key]
                mu1, mu2 = a["mean"][key], b["mean"][key]
                cov = math.sqrt(a["var"][key + "_shared"] * b["var"][key + "_shared"])
                cov += 0.4 * math.sqrt(a["var"][key + "_role"] * b["var"][key + "_role"])
                expected = 0.6 * v1 + 0.6 * 0.4 * mu1**2 + 0.8 * v2 + 0.8 * 0.2 * mu2**2
                expected += 2 * (joint * cov + (joint - 0.6 * 0.8) * mu1 * mu2)
                self.assertAlmostEqual(d["var"][key], expected, places=8)
            # With the player's own rate as reference, impact is (P-q)*N.
            q = a["mean"][s + "_rate"]
            vp = a["var"][s + "_rate"]
            cn = math.sqrt(a["var"][s + "A_shared"] * b["var"][s + "A_shared"])
            cn += 0.4 * math.sqrt(a["var"][s + "A_role"] * b["var"][s + "A_role"])
            expected = 0.6 * a["var"][s + "M_cond"] + 0.8 * b["var"][s + "M_cond"]
            expected += 2 * joint * (a["mean"][s + "A"] * b["mean"][s + "A"] + cn) * vp
            self.assertAlmostEqual(e._compute_team_pct_impact_var(d, s, q), expected, places=8)

    def test_a1b_map_is_inert_not_an_active_calibrator(self):
        e = self.engine()
        args = ([1], [2], "2026-10-20", "2026-10-22")
        before = e.project_matchup(*args)[3]
        with patch.dict(WEEKLY_VAR_INFLATION_BY_CAT, {k: 4 for k in WEEKLY_VAR_INFLATION_BY_CAT}):
            self.assertEqual(before, e.project_matchup(*args)[3])

    def test_role_setting_reaches_all_add_drop_distributions(self):
        e = self.engine(0.4)
        e.players[3] = _make_player(3, 34)
        e.team_map[3] = 10
        original = e.get_expected_weekly_distribution
        observed = []

        def distribution(*args, **kwargs):
            result = original(*args, **kwargs)
            observed.append(result["meta"]["role_covariance_correlation"])
            return result

        with patch.object(e, "get_expected_weekly_distribution", side_effect=distribution):
            rows = e.recommend_add_drop_moves([1], [2], [3], "2026-10-20", "2026-10-22")
        self.assertTrue(rows)
        self.assertGreaterEqual(len(observed), 4)
        self.assertEqual(set(observed), {0.4})

    def test_sensitivity_uses_independent_baselines_and_restores_on_success_and_error(self):
        for fail in [False, True]:
            e = self.engine()
            e.players[3] = _make_player(3, 28)
            e.use_positional_depth_and_injury_boost = True
            state = {i: copy.deepcopy(p.__dict__) for i, p in e.players.items()}
            calls = []

            def project(mine, theirs, **kwargs):
                enabled = e.use_positional_depth_and_injury_boost
                calls.append((enabled, tuple(mine)))
                e.players[1].expected_minutes = 99
                e.players[1].minutes_var = 143
                if fail and not enabled:
                    raise RuntimeError("injected neutral projection failure")
                utility = (
                    (0.4 if 3 not in mine else 0.8) if enabled else (0.2 if 3 not in mine else 0.3)
                )
                probs = CategoryProbabilities({"PTS": utility}, {"PTS": 0})
                mean = dict.fromkeys(ALL_CATEGORIES, 10.0)
                return (
                    {"meta": {"il_stashed_ids": []}, "mean": mean},
                    {},
                    utility,
                    probs,
                    {"PTS": 1},
                )

            with (
                patch.object(e, "project_matchup", side_effect=project),
                patch.object(e, "recompute_team_depth_and_injury_minutes"),
            ):
                if fail:
                    with self.assertRaisesRegex(RuntimeError, "injected"):
                        e.recommend_add_drop_moves([1], [2], [3], opportunity_sensitivity=True)
                else:
                    rows = e.recommend_add_drop_moves([1], [2], [3], opportunity_sensitivity=True)
                    self.assertTrue(rows)
                    self.assertAlmostEqual(rows[0]["delta_objective_value"], 0.4)
                    self.assertAlmostEqual(rows[0]["delta_without_spillover"], 0.1)
                    self.assertAlmostEqual(rows[0]["robust_delta_objective_value"], 0.1)
                    self.assertEqual(
                        calls, [(True, (1,)), (True, (1, 3)), (False, (1,)), (False, (1, 3))]
                    )
            self.assertTrue(e.use_positional_depth_and_injury_boost)
            self.assertEqual(state, {i: p.__dict__ for i, p in e.players.items()})


class DecayReferenceTests(unittest.TestCase):
    def test_legacy_source_provenance_is_bound_to_utf8_git_blob(self):
        fixtures = Path(__file__).parent / "fixtures"
        data = json.loads((fixtures / "legacy_decay.json").read_text(encoding="utf-8"))
        self.assertEqual(data["source_revision"], "3e8ff22c8c16f74f648a58c19bb6e18b6a7acdce")
        self.assertEqual(data["source_path"], "src/bayesian_model.py")
        text = (fixtures / data["source_fixture"]).read_bytes().decode("utf-8", errors="strict")
        source = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        self.assertEqual(len(source), 26749)
        self.assertEqual(hashlib.sha256(source).hexdigest(), data["source_sha256"])
        self.assertEqual(
            data["source_sha256"],
            "ca207500df256570af930c9d01e9b88e291c93f69614e6e908a931ff12137635",
        )
        header = f"blob {len(source)}\0".encode("ascii")
        self.assertEqual(hashlib.sha1(header + source).hexdigest(), data["source_git_blob"])

    def test_historical_numeric_outputs_and_posteriors_match_frozen_old_source(self):
        data = json.loads((Path(__file__).parent / "fixtures/legacy_decay.json").read_text())
        for case in data["cases"]:
            with self.subTest(gap=case["gap"], event=case["event"]):
                p = BayesianPlayer(1, "Player 1")
                p.initialize_priors(data["prior"])
                p.expected_minutes = p.base_expected_minutes = 30.0
                p.update_stats(
                    pd.Timestamp("2026-01-01"),
                    32.0,
                    {"PTS": 20, "FGM": 7, "FGA": 15, "FTM": 4, "FTA": 5},
                    game_id="g1",
                )
                p.update_stats(
                    pd.Timestamp("2026-01-01") + pd.Timedelta(days=case["gap"]),
                    28.0,
                    {"PTS": 15, "FGM": 5, "FGA": 12, "FTM": 5, "FTA": 6},
                    is_event_reset=case["event"],
                    game_id="g2",
                )
                for name, expected in case["state"].items():
                    self.assertEqual(getattr(p, name), expected)
                for idle, expected in case["predictions"].items():
                    actual = p.predict_next_game(
                        current_date=p.last_game_date + pd.Timedelta(days=int(idle))
                    )
                    for stat, values in expected.items():
                        self.assertEqual({k: actual[stat][k] for k in values}, values)

    def test_positive_gap_volume_keys_event_floors_and_accuracy_are_independent(self):
        for event in [False, True]:
            for gap in [8, 180]:
                for changed in [False, True]:
                    with self.subTest(event=event, gap=gap, changed=changed):
                        p = _make_player()
                        date = pd.Timestamp("2026-01-01")
                        p.update_stats(
                            date, 30, {"FGM": 7, "FGA": 15, "FTM": 4, "FTA": 5}, game_id="g1"
                        )
                        before = copy.deepcopy(p.__dict__)
                        values = (
                            {"FGA": 0.025, "FTA": 0.02} if changed else {"FGA": 0.008, "FTA": 0.004}
                        )
                        with patch.dict(DECAY_LAMBDA_BY_STAT, values):
                            p.update_stats(
                                date + pd.Timedelta(days=gap),
                                28,
                                {"FGM": 5, "FGA": 12, "FTM": 5, "FTA": 6},
                                is_event_reset=event,
                                game_id="g2",
                            )
                        for s, attempts in [("FG", 12), ("FT", 6)]:
                            beta = max(
                                60.0,
                                before["att_betas"][s]
                                * math.exp(-values[s + "A"] * gap)
                                * (0.2 if event else 1),
                            )
                            self.assertAlmostEqual(p.att_betas[s], beta + 28)
                            self.assertAlmostEqual(
                                p.att_alphas[s],
                                before["att_alphas"][s] / before["att_betas"][s] * beta + attempts,
                            )
                            n = before["alphas"][s] + before["betas"][s]
                            precision = max(
                                15.0,
                                n
                                * math.exp(-DECAY_LAMBDA_BY_STAT[s] * gap)
                                * (0.65 if event else 1),
                            )
                            self.assertAlmostEqual(p.alphas[s] + p.betas[s], precision + attempts)

    def test_raw_and_effective_availability_have_different_ceilings(self):
        p = BayesianPlayer(1, "Ironman")
        p.initialize_priors({"MIN": 2600, "GP": 82})
        self.assertAlmostEqual(p.availability_rate, 61 / 66)
        self.assertAlmostEqual(p.get_effective_game_availability(), 0.35 * 0.92 + 0.65 * 61 / 66)
        for _ in range(1000):
            p.record_team_game_availability(True)
        self.assertEqual(p.availability_rate, 0.98)
        self.assertAlmostEqual(p.get_effective_game_availability(), 0.959)

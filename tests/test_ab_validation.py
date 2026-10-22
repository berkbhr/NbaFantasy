"""
Validation suite for the availability / injury layer.

Classes
  TestDraftData                   draft transcription (no model needed)
  TestScraperParsing              NBA report parser on the REAL report layout (no model needed)
  TestEngineValidationAndSymmetry A/B/C sensitivity, direction-of-effect, symmetry (needs the model)
"""
import sys
import os
import io
import copy
import random
import shutil
import tempfile
import unittest
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src import draft_data
from src.nba_injury_scraper import (
    NBAOfficialInjuryScraper, parse_report_text, reconcilable_team_codes,
    get_official_report_url, candidate_report_urls,
)
from src.live_draft_assistant import LiveDraftAssistant, COUNT_STATS, PERCENTAGE_STATS
from src.matchup_engine import MatchupEngine

# Text as extracted from the official report PDF (layout observed on the 27 Jan 2026 report,
# abbreviated). Replace/extend with a REAL PDF at tests/fixtures/nba_injury_report_real.pdf
# (see test_real_pdf_fixture_if_present).
REAL_FORMAT_REPORT_TEXT = """Injury Report: 01/27/26 12:00 AM
Page 1 of 6
Game Date Game Time Matchup Team Player Name Current Status Reason
01/27/2026 07:00 (ET) POR@WAS Portland Trail Blazers NOT YET SUBMITTED
Washington Wizards Bagley III, Marvin Out Injury/Illness - Thoracic; Strain
Coulibaly, Bilal Questionable Injury/Illness - Lower Back; Strain
Middleton, Khris Questionable Injury/Illness - Left Foot; Soreness
Vukcevic, Tristan Out Injury/Illness - Left Hamstring; Strain
Whitmore, Cam Out
Injury/Illness - Right Shoulder; Deep
Vein Thrombosis
Young, Trae Out
Injury/Illness - Right Knee; MCL
Strain; Quad Contusion
07:30 (ET) SAC@NYK Sacramento Kings LaVine, Zach Questionable Injury/Illness - Lower Back; Soreness
Monk, Malik Questionable Injury/Illness - Right Ankle; Soreness
Murray, Keegan Out Injury/Illness - Left Ankle; Sprain
Plowden, Daeqwon Out G League - Two-Way
Stevens, Isaiah Out G League - Two-Way
New York Knicks Jemison III, Trey Questionable G League - Two-Way
Jones, Dillon Questionable G League - Two-Way
McCullar Jr., Kevin Questionable G League - Two-Way
08:00 (ET) MIL@PHI Milwaukee Bucks Antetokounmpo, Alex Out G League - Two-Way
Antetokounmpo, Giannis Out Injury/Illness - Right Calf; Strain
Porter Jr., Kevin Out
Injury/Illness - Right Oblique Muscle;
Strain
Prince, Taurean Out Injury/Illness - Neck; Surgery
Philadelphia 76ers NOT YET SUBMITTED
10:00 (ET) LAC@UTA LA Clippers Beal, Bradley Out Injury/Illness - Left Hip; Fracture
Dunn, Kris Questionable Injury/Illness - Right Ankle; Sprain
Paul, Chris Out Not With Team
Utah Jazz George, Keyonte Out Rest
Kessler, Walker Out
Injury/Illness - Left Shoulder; Injury
recovery
Markkanen, Lauri Questionable
Return to Competition
Reconditioning
Nurkic, Jusuf Doubtful Injury/Illness - N/A; Illness
"""


# =========================================================================================
# 1. Draft data
# =========================================================================================
class TestDraftData(unittest.TestCase):
    def test_all_182_picks_unique_and_complete(self):
        names = draft_data.all_pick_names()
        self.assertEqual(len(names), 182)
        self.assertEqual(len(set(names)), 182, "a player was drafted twice")
        for r in range(1, draft_data.NUM_ROUNDS + 1):
            self.assertEqual(len(draft_data.DRAFT_PICKS_BY_ROUND[r]), draft_data.NUM_TEAMS)

    def test_snake_order(self):
        self.assertEqual(draft_data.slot_of_pick(1, 0), 0)     # R1 forward
        self.assertEqual(draft_data.slot_of_pick(2, 0), 13)    # R2 reversed
        self.assertEqual(draft_data.slot_of_pick(11, 7), 7)    # R11 forward: Berk is pick 8 -> slot idx 7
        self.assertEqual(draft_data.slot_of_pick(13, 7), 7)

    def test_berk_roster_complete(self):
        rosters = draft_data.build_rosters()
        expected = [
            'Tyrese Maxey', 'James Harden', 'Kawhi Leonard', 'Desmond Bane', 'Jarrett Allen',
            'Jabari Smith Jr.', 'Josh Hart', 'Neemias Queta', 'Brandon Ingram', 'Ayo Dosunmu',
            'Nikola Vučević', 'Julian Champagnie', 'Jay Huff']
        self.assertEqual(rosters[draft_data.MY_TEAM_IDX], expected)
        for slot, names in rosters.items():
            self.assertEqual(len(names), 13, f"slot {slot + 1} has {len(names)} players")

    def test_star_slots(self):
        r = draft_data.build_rosters()
        checks = [(0, 'Nikola Jokić'), (1, 'Victor Wembanyama'), (2, 'Luka Dončić'),
                  (3, 'Shai Gilgeous-Alexander'), (4, 'Cade Cunningham'), (5, 'Giannis Antetokounmpo'),
                  (5, 'Joel Embiid'), (6, 'Jayson Tatum'), (8, 'Anthony Edwards'), (9, 'Tyrese Haliburton'),
                  (9, 'Zion Williamson'), (10, 'Cooper Flagg'), (11, 'Anthony Davis'),
                  (12, 'Scottie Barnes'), (12, 'Julius Randle'), (13, 'Alperen Şengün')]
        for slot, name in checks:
            self.assertIn(name, r[slot], f"{name} should be on slot {slot + 1}")

    def test_matches_markdown_overview(self):
        path = draft_data.find_overview_markdown()
        if not path:
            self.skipTest("league_draft_overview_and_projections.md not found "
                          "(set DRAFT_OVERVIEW_MD to enable this check)")
        self.assertEqual(draft_data.compare_with_markdown(path), [])


# =========================================================================================
# 2. Scraper parsing on the real report layout
# =========================================================================================
class TestScraperParsing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nba_scraper_test_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.scraper = NBAOfficialInjuryScraper(raw_dir=self.tmp)
        self.parsed = parse_report_text(REAL_FORMAT_REPORT_TEXT)
        self.by_raw = {r['raw_name']: r for r in self.parsed['rows']}

    @staticmethod
    def _resolver(name):
        return abs(hash(name)) % 100000 + 1

    def test_parses_every_player_row(self):
        self.assertEqual(len(self.parsed['rows']), 25)
        self.assertEqual(self.parsed['unparsed_lines'], [])

    def test_names_are_flipped_with_suffixes(self):
        for raw, expected in [("Bagley III, Marvin", "Marvin Bagley III"), ("Porter Jr., Kevin", "Kevin Porter Jr."),
                              ("LaVine, Zach", "Zach LaVine"), ("Beal, Bradley", "Bradley Beal"),
                              ("Jemison III, Trey", "Trey Jemison III")]:
            self.assertEqual(self.by_raw[raw]['name'], expected)

    def test_inherited_cells_and_first_row_of_blocks(self):
        # first player of a block is glued to date/time/matchup/team on the same text line
        lav = self.by_raw["LaVine, Zach"]
        self.assertEqual((lav['team'], lav['team_code'], lav['matchup']), ("Sacramento Kings", "SAC", "SAC@NYK"))
        self.assertEqual(self.by_raw["Monk, Malik"]['team'], "Sacramento Kings")
        self.assertEqual(self.by_raw["Monk, Malik"]['game_date'], "01/27/2026")
        self.assertEqual(self.by_raw["Jones, Dillon"]['team'], "New York Knicks")
        self.assertEqual(self.by_raw["Beal, Bradley"]['team'], "LA Clippers")
        self.assertEqual(self.by_raw["Dunn, Kris"]['team'], "LA Clippers")
        self.assertEqual(self.by_raw["Bagley III, Marvin"]['team'], "Washington Wizards")

    def test_wrapped_reasons_and_reason_types(self):
        self.assertTrue(self.by_raw["Whitmore, Cam"]['desc'].endswith("Deep Vein Thrombosis"))
        self.assertEqual(self.by_raw["George, Keyonte"]['reason_type'], "REST")
        self.assertEqual(self.by_raw["Markkanen, Lauri"]['reason_type'], "RETURN_CONDITIONING")
        self.assertEqual(self.by_raw["Plowden, Daeqwon"]['reason_type'], "GLEAGUE")
        self.assertEqual(self.by_raw["Paul, Chris"]['reason_type'], "NOT_WITH_TEAM")
        self.assertEqual(self.by_raw["Beal, Bradley"]['reason_type'], "INJURY")

    def test_unsubmitted_is_tracked_and_never_reconcilable(self):
        unsub = {t['team'] for t in self.parsed['unsubmitted_teams']}
        self.assertEqual(unsub, {"Portland Trail Blazers", "Philadelphia 76ers"})
        ok, clean, _, _ = self.scraper.run_health_checks(self.parsed, games_today_count=3,
                                                         id_resolver_fn=self._resolver)
        recon = reconcilable_team_codes({'clean_injuries': clean,
                                         'unsubmitted_teams': self.parsed['unsubmitted_teams']})
        self.assertNotIn("POR", recon)
        self.assertNotIn("PHI", recon)
        self.assertTrue({"WAS", "SAC", "LAC", "UTA", "MIL"} <= recon)

    def test_g_league_rows_ignored_and_report_healthy(self):
        ok, clean, quarantined, m = self.scraper.run_health_checks(
            self.parsed, games_today_count=3, id_resolver_fn=self._resolver)
        self.assertTrue(ok, m['failure_reasons'])
        self.assertEqual(len(clean), 19)
        self.assertEqual(m['ignored_count'], 6)
        self.assertEqual(quarantined, [])

    def test_low_id_resolution_fails_health_check(self):
        ok, *_ , m = self.scraper.run_health_checks(
            self.parsed, games_today_count=3,
            id_resolver_fn=lambda n: 1 if n.startswith(('K', 'M', 'C')) else None)
        self.assertFalse(ok)
        self.assertLess(m['match_rate'], 0.85)

    def test_silently_dropped_lines_fail_completeness_check(self):
        bad = parse_report_text(REAL_FORMAT_REPORT_TEXT +
                                "Mangled, Name Zzz qqq\nAnother, Row Zzz qqq\nThird, Row Zzz qqq\n")
        self.assertEqual(len(bad['unparsed_lines']), 3)
        ok, _, quarantined, m = self.scraper.run_health_checks(bad, games_today_count=3,
                                                               id_resolver_fn=self._resolver)
        self.assertFalse(ok)
        self.assertEqual(m['unparsed_count'], 3)
        self.assertEqual(len(quarantined), 3)

    def test_unknown_status_in_row_list_is_quarantined(self):
        rows = [{'name': 'Real Player', 'status': 'OUT', 'desc': 'Knee'},
                {'name': 'Fake Player', 'status': 'WEIRD_UNKNOWN_STATUS', 'desc': 'x'}]
        ok, clean, quarantined, _ = self.scraper.run_health_checks(rows, games_today_count=1,
                                                                   id_resolver_fn=lambda n: 7)
        self.assertEqual(len(clean), 1)
        self.assertEqual(quarantined[0]['row']['status'], 'WEIRD_UNKNOWN_STATUS')

    def test_early_report_with_all_teams_unsubmitted_is_not_a_false_alarm(self):
        early = parse_report_text(
            "Injury Report: 01/28/26 12:00 AM\n"
            "01/28/2026 07:00 (ET) CHI@IND Chicago Bulls NOT YET SUBMITTED\n"
            "Indiana Pacers NOT YET SUBMITTED\n")
        ok, *_ = self.scraper.run_health_checks(early, games_today_count=5)
        self.assertTrue(ok)

    def test_report_time_and_url_naming(self):
        self.assertEqual(self.parsed['report_time_utc'].isoformat(), "2026-01-27T05:00:00+00:00")
        self.assertTrue(get_official_report_url(datetime(2026, 1, 27, 5, 0, tzinfo=timezone.utc))
                        .endswith("Injury-Report_2026-01-27_12_00AM.pdf"))
        self.assertTrue(get_official_report_url(datetime(2026, 1, 27, 22, 7, tzinfo=timezone.utc))
                        .endswith("Injury-Report_2026-01-27_05_00PM.pdf"))
        urls = [u for _, u in candidate_report_urls(datetime(2026, 1, 27, 22, 7, tzinfo=timezone.utc), 3)]
        self.assertTrue(urls[1].endswith("_04_45PM.pdf") and urls[2].endswith("_04_30PM.pdf"))

    def test_fetch_flow_with_fake_downloader(self):
        try:
            from reportlab.pdfgen import canvas
            import pdfplumber  # noqa: F401
        except ImportError:
            self.skipTest("reportlab/pdfplumber not installed")
        buf = io.BytesIO()
        cv = canvas.Canvas(buf, pageCompression=1)
        y = 800
        for ln in REAL_FORMAT_REPORT_TEXT.splitlines():
            cv.drawString(20, y, ln)
            y -= 12
            if y < 40:
                cv.showPage()
                y = 800
        cv.save()
        pdf = buf.getvalue()
        calls = []

        def fake(url):
            calls.append(url)
            return pdf if len(calls) == 4 else None       # slots 1-3 are 404

        now = datetime(2026, 1, 27, 22, 7, tzinfo=timezone.utc)
        out = self.scraper.fetch_latest_injuries(games_today_count=3, id_resolver_fn=self._resolver,
                                                 now=now, fetch_bytes_fn=fake, pause_seconds=0)
        self.assertTrue(out['is_healthy'], out['metrics']['failure_reasons'])
        self.assertEqual(len(calls), 4)
        self.assertEqual(len(out['clean_injuries']), 19)
        self.assertTrue(any(f.endswith('.pdf') for f in os.listdir(self.tmp)), "raw PDF was not archived")

        none = self.scraper.fetch_latest_injuries(now=now, fetch_bytes_fn=lambda u: None,
                                                  pause_seconds=0, max_back_steps=3)
        self.assertFalse(none['is_healthy'])

    def test_real_pdf_fixture_if_present(self):
        path = os.path.join(os.path.dirname(__file__), 'fixtures', 'nba_injury_report_real.pdf')
        if not os.path.exists(path):
            self.skipTest("Save a REAL report PDF to tests/fixtures/nba_injury_report_real.pdf "
                          "(copy one from data/raw/injuries/)")
        with open(path, 'rb') as f:
            parsed = self.scraper._parse_payload(f.read())
        self.assertGreater(len(parsed['rows']) + len(parsed['unsubmitted_teams']), 0)
        candidates = max(1, parsed['candidate_count'])
        self.assertLessEqual(len(parsed['unparsed_lines']) / candidates, 0.05,
                             f"unparsed lines: {parsed['unparsed_lines'][:5]}")
        for r in parsed['rows']:
            self.assertTrue(r['team_code'], f"no team for {r['raw_name']}")
            self.assertTrue(r['game_date'], f"no game date for {r['raw_name']}")


# =========================================================================================
# 3. Engine: A/B/C sensitivity, direction of effect, symmetry
# =========================================================================================
class TestEngineValidationAndSymmetry(unittest.TestCase):
    STARTER_GAMES = 3.35          # engine's draft-mode rule (restated here on purpose, see bench test)
    BENCH_GAMES = 2.35

    @classmethod
    def setUpClass(cls):
        cls.assistant = LiveDraftAssistant(prior_season="2025_26", my_team_idx=draft_data.MY_TEAM_IDX,
                                           num_teams=draft_data.NUM_TEAMS)
        # strict: raises DraftResolutionError if ANY of the 182 names fails to resolve
        cls.rosters = draft_data.resolve_rosters(cls.assistant)
        cls.all_pids = [p for slot in sorted(cls.rosters) for p in cls.rosters[slot]]
        cls.berk_pids = cls.rosters[draft_data.MY_TEAM_IDX]
        cls.kawhi_pid = cls.assistant.resolve_player_id('Kawhi Leonard', only_available=False)
        cls.maxey_pid = cls.assistant.resolve_player_id('Tyrese Maxey', only_available=False)
        cls.harden_pid = cls.assistant.resolve_player_id('James Harden', only_available=False)
        cls.ayo_pid = cls.assistant.resolve_player_id('Ayo Dosunmu', only_available=False)

        rostered = set(cls.all_pids)
        avail = cls.assistant.df_base.loc[[p for p in cls.assistant.available_player_ids
                                           if p in cls.assistant.df_base.index]]
        ranked = list(avail.sort_values('BASE_Z', ascending=False).index)
        cls.fa_pool = [p for p in ranked if p not in rostered][:30]      # best free agents, never a rostered player
        cls._orig_avail = {p: cls.assistant.players[p].availability_rate for p in cls.all_pids}

    def setUp(self):
        self.addCleanup(self._restore_state)
        self._restore_state()

    def _restore_state(self):
        for pid in self.all_pids:
            bp = self.assistant.players[pid]
            bp.availability_rate = self._orig_avail[pid]
            bp.update_injury_status('HEALTHY')

    # ---- helpers ------------------------------------------------------------------------
    def _engine(self, players=None, fa=None):
        return MatchupEngine(players or self.assistant.players, pd.DataFrame(), pd.DataFrame(),
                             free_agent_pool=list(fa) if fa else [], num_il_slots=2, max_weekly_adds=3)

    def _pts(self, engine, roster, live=True):
        return engine.get_expected_weekly_distribution(roster, use_live_injuries=live)['mean']['PTS']

    def _gross(self, pid, games=None):
        bp = self.assistant.players[pid]
        ppg = bp.alphas['PTS'] / bp.betas['PTS'] * bp.expected_minutes
        return ppg * (games or self.STARTER_GAMES) * bp.get_effective_game_availability(is_b2b=False)

    # ---- data integrity -----------------------------------------------------------------
    def test_every_drafted_name_resolves_to_a_unique_player(self):
        self.assertEqual(len(self.all_pids), 182)
        self.assertEqual(len(set(self.all_pids)), 182)
        self.assertEqual(len(self.berk_pids), 13)
        self.assertFalse(set(self.fa_pool) & set(self.all_pids))

    # ---- A/B/C sensitivity --------------------------------------------------------------
    def test_three_way_abc_comparison(self):
        """C1 full healthy (rate=1.0), C2 seasonal prior, LIVE baseline (no injuries), C3 Kawhi OUT + IL+ + streaming."""
        for pid in self.berk_pids:
            self.assistant.players[pid].availability_rate = 1.0
        pts_c1 = self._pts(self._engine(), self.berk_pids, live=False)
        for pid in self.berk_pids:
            self.assistant.players[pid].availability_rate = self._orig_avail[pid]
        pts_c2 = self._pts(self._engine(), self.berk_pids, live=False)
        pts_live = self._pts(self._engine(), self.berk_pids, live=True)
        self.assistant.players[self.kawhi_pid].update_injury_status('OUT', desc='Knee management')
        pts_c3 = self._pts(self._engine(fa=self.fa_pool), self.berk_pids, live=True)
        print(f"\nC1 healthy {pts_c1:.1f} | C2 prior {pts_c2:.1f} | live baseline {pts_live:.1f} | "
              f"C3 Kawhi OUT+IL+stream {pts_c3:.1f}")
        self.assertGreaterEqual(pts_c1, pts_c2)
        self.assertLess(pts_c3, pts_live)

    # ---- direction of effect (relative thresholds, not golden numbers) ------------------
    def test_start_date_none_regression(self):
        """live injuries must be honoured when start_date=None."""
        engine = self._engine()
        gross = self._gross(self.kawhi_pid)
        healthy = engine.get_expected_weekly_distribution(self.berk_pids, start_date=None, use_live_injuries=True)['mean']['PTS']
        self.assistant.players[self.kawhi_pid].update_injury_status('OUT')
        out = engine.get_expected_weekly_distribution(self.berk_pids, start_date=None, use_live_injuries=True)['mean']['PTS']
        drop = healthy - out
        self.assertGreater(drop, 0.5 * gross)
        self.assertLess(drop, gross)               # a promoted bench player recovers part of it

    def test_stashed_il_exclusion_regression(self):
        base = self._pts(self._engine(), self.berk_pids)
        self.assistant.players[self.kawhi_pid].update_injury_status('OUT')
        no_stream = self._pts(self._engine(), self.berk_pids)
        stream = self._pts(self._engine(fa=self.fa_pool), self.berk_pids)
        self.assertLess(no_stream, stream)
        self.assertLess(stream, base)

    def test_direction_of_effect_diagnostics(self):
        base = self._pts(self._engine(), self.berk_pids)
        g_kawhi, g_maxey = self._gross(self.kawhi_pid), self._gross(self.maxey_pid)

        self.assistant.players[self.kawhi_pid].update_injury_status('OUT')
        d1 = self._pts(self._engine(), self.berk_pids)
        drop_kawhi = base - d1
        self.assertGreater(drop_kawhi, 0.5 * g_kawhi)

        d2 = self._pts(self._engine(fa=self.fa_pool), self.berk_pids)
        self.assertGreater(d2 - d1, 0.0)
        self.assertLess(d2 - d1, drop_kawhi)

        self.assistant.players[self.kawhi_pid].update_injury_status('HEALTHY')
        self.assistant.players[self.maxey_pid].update_injury_status('OUT')
        d3 = self._pts(self._engine(), self.berk_pids)
        drop_maxey = base - d3
        self.assertGreater(drop_maxey, 0.5 * g_maxey)
        self.assertNotAlmostEqual(drop_maxey, drop_kawhi, places=1)

        for pid in self.berk_pids:
            self.assistant.players[pid].update_injury_status('OUT')
        self.assertEqual(self._pts(self._engine(), self.berk_pids), 0.0)

    def test_bench_replacement_math(self):
        """
        Self-consistency of the engine's draft-mode rule (starters 3.35 games, bench 2.35):
        net drop = Kawhi's gross contribution - the +1.0-game gain of exactly ONE promoted bench player.
        Which player is promoted is data dependent (Ayo today), so the test looks for a match among the
        other 12 players and prints it. This restates the engine's formula; it does NOT prove the rule is right.
        """
        engine = self._engine()
        base = self._pts(engine, self.berk_pids)
        gross = self._gross(self.kawhi_pid)
        self.assistant.players[self.kawhi_pid].update_injury_status('OUT')
        observed = base - self._pts(engine, self.berk_pids)
        promoted = [pid for pid in self.berk_pids if pid != self.kawhi_pid
                    and abs(observed - (gross - self._gross(pid, games=self.STARTER_GAMES - self.BENCH_GAMES))) < 1e-6]
        self.assertTrue(promoted, f"observed drop {observed:.4f} (Kawhi gross {gross:.4f}) matches no single "
                                  f"promoted-bench-player gain")
        print(f"\nbench promotion: {[self.assistant.players[p].name for p in promoted]}")

    # ---- symmetry -----------------------------------------------------------------------
    def _assert_same_distribution(self, a, b, places=9):
        for key in ('mean', 'var'):
            for cat in a[key]:
                self.assertAlmostEqual(a[key][cat], b[key][cat], places=places, msg=f"{key}/{cat}")

    def test_roster_order_invariance_healthy(self):
        engine = self._engine(fa=self.fa_pool)
        ref = engine.get_expected_weekly_distribution(self.berk_pids, use_live_injuries=False)
        self._assert_same_distribution(ref, engine.get_expected_weekly_distribution(
            list(reversed(self.berk_pids)), use_live_injuries=False))

    def test_roster_order_invariance_with_three_out(self):
        """
        3 OUT players but only 2 IL+ slots: the result must not depend on roster order.
        (Under the current engine all OUT players have AVAIL=0 so the choice of stashed players does not
        change the output; this test guards that property if the stash/roster-slot logic is ever changed,
        e.g. when REST or per-player IL eligibility is introduced.)
        """
        for pid in (self.kawhi_pid, self.harden_pid, self.maxey_pid):
            self.assistant.players[pid].update_injury_status('OUT')
        engine = self._engine(fa=self.fa_pool)
        ref = engine.get_expected_weekly_distribution(self.berk_pids, use_live_injuries=True)
        rng = random.Random(2026)
        orders = [list(reversed(self.berk_pids))]
        for _ in range(6):
            o = list(self.berk_pids)
            rng.shuffle(o)
            orders.append(o)
        for o in orders:
            self._assert_same_distribution(ref, engine.get_expected_weekly_distribution(o, use_live_injuries=True))

    def _cat_probs(self, wp):
        cat_p = {c: wp.get(c, 0.5) for c in COUNT_STATS}
        cat_p['FG'] = wp.get('FG_PCT', 0.5)
        cat_p['FT'] = wp.get('FT_PCT', 0.5)
        return cat_p

    def test_matchup_is_antisymmetric_across_real_rosters(self):
        engine = self._engine()
        dists = {s: engine.get_expected_weekly_distribution(self.rosters[s], use_live_injuries=False)
                 for s in sorted(self.rosters)}
        b = draft_data.MY_TEAM_IDX
        for other in sorted(self.rosters):
            if other == b:
                continue
            _, wp_ab, _ = engine.evaluate_h2h_matchup(dists[b], dists[other])
            _, wp_ba, _ = engine.evaluate_h2h_matchup(dists[other], dists[b])
            for cat in list(COUNT_STATS) + ['FG_PCT', 'FT_PCT']:
                if cat in wp_ab:
                    self.assertAlmostEqual(wp_ab[cat] + wp_ba[cat], 1.0, places=8, msg=f"slot {other + 1} {cat}")
            for rho in (0.0, 0.2):
                p_ab = MatchupEngine.compute_matchup_win_prob(self._cat_probs(wp_ab), rho=rho)
                p_ba = MatchupEngine.compute_matchup_win_prob(self._cat_probs(wp_ba), rho=rho)
                self.assertAlmostEqual(p_ab + p_ba, 1.0, places=6, msg=f"slot {other + 1} rho={rho}")

    def test_self_play_is_exactly_even_using_engine_formula(self):
        engine = self._engine()
        dist = engine.get_expected_weekly_distribution(self.berk_pids, use_live_injuries=False)
        _, wp, _ = engine.evaluate_h2h_matchup(dist, copy.deepcopy(dist))
        for rho in (0.0, 0.2):
            self.assertAlmostEqual(MatchupEngine.compute_matchup_win_prob(self._cat_probs(wp), rho=rho),
                                   0.5, places=8)

    def test_clone_teams_respond_identically_to_identical_injuries(self):
        players = dict(self.assistant.players)
        try:
            next_id = max(int(p) for p in players) + 1000
            make_id = lambda k: next_id + k
        except (TypeError, ValueError):
            make_id = lambda k: f"clone_{k}"
        clone_ids = []
        for k, pid in enumerate(self.berk_pids):
            c = copy.deepcopy(players[pid])
            c.player_id = make_id(k)
            c.name = f"{players[pid].name} (clone)"
            players[make_id(k)] = c
            clone_ids.append(make_id(k))

        engine = self._engine(players=players, fa=self.fa_pool)
        self._assert_same_distribution(
            engine.get_expected_weekly_distribution(self.berk_pids, use_live_injuries=True),
            engine.get_expected_weekly_distribution(clone_ids, use_live_injuries=True))

        for idx in (self.berk_pids.index(self.kawhi_pid), self.berk_pids.index(self.maxey_pid)):
            players[self.berk_pids[idx]].update_injury_status('OUT')
            players[clone_ids[idx]].update_injury_status('OUT')
        self._assert_same_distribution(
            engine.get_expected_weekly_distribution(self.berk_pids, use_live_injuries=True),
            engine.get_expected_weekly_distribution(clone_ids, use_live_injuries=True))


if __name__ == '__main__':
    unittest.main()

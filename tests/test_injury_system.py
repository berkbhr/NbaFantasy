import sys
import os
import unittest
import tempfile
import shutil
import sqlite3
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.injury_tracker import InjuryTracker, STATUS_PROBABILITIES, DATA_DIR, DB_PATH
from src.bayesian_model import BayesianPlayer
from src.matchup_engine import MatchupEngine, COUNT_STATS, PERCENTAGE_STATS

class TestInjurySystem(unittest.TestCase):
    def setUp(self):
        # Create a completely isolated temporary directory and SQLite database for testing
        self.test_dir = tempfile.mkdtemp(prefix="nba_test_inj_")
        self.test_db_path = os.path.join(self.test_dir, "isolated_injuries.db")
        self.tracker = InjuryTracker(db_path=self.test_db_path)

    def tearDown(self):
        # Clean up temporary test directory and file
        try:
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_injury_tracker_crud_and_clearance_tracking(self):
        # 1. Set injury
        self.tracker.set_injury(
            player_id=101,
            player_name="Kawhi Leonard",
            status="OUT",
            team="TOR",
            desc="Knee management",
            is_b2b_rest=False
        )

        inj = self.tracker.get_injury(101)
        self.assertIsNotNone(inj)
        self.assertEqual(inj['status'], 'OUT')
        self.assertEqual(inj['injury_desc'], 'Knee management')

        # 2. Check play probability for OUT
        prob_out = self.tracker.get_play_probability(101, base_avail=0.85)
        self.assertEqual(prob_out, 0.0)

        # 3. Test B2B rest
        self.tracker.set_injury(
            player_id=102,
            player_name="Joel Embiid",
            status="B2B_REST",
            team="PHI",
            is_b2b_rest=True
        )
        prob_b2b_no = self.tracker.get_play_probability(102, base_avail=0.85, is_b2b=False)
        prob_b2b_yes = self.tracker.get_play_probability(102, base_avail=0.85, is_b2b=True)
        self.assertEqual(prob_b2b_no, 0.85)
        self.assertEqual(prob_b2b_yes, 0.05)

        # 4. Test REST status (definite single-game rest)
        self.tracker.set_injury(
            player_id=103,
            player_name="LeBron James",
            status="REST",
            team="LAL",
            desc="Load management"
        )
        prob_rest = self.tracker.get_play_probability(103, base_avail=0.85)
        self.assertEqual(prob_rest, 0.0)

        # 5. Test QUESTIONABLE + is_b2b_rest interaction:
        # Non-B2B game should evaluate to 0.52 (not overridden by b2b flag), B2B game evaluates to min(0.52, 0.05) = 0.05
        self.tracker.set_injury(
            player_id=104,
            player_name="Anthony Davis",
            status="QUESTIONABLE",
            team="LAL",
            is_b2b_rest=True
        )
        self.assertEqual(self.tracker.get_play_probability(104, base_avail=0.85, is_b2b=False), 0.52)
        self.assertEqual(self.tracker.get_play_probability(104, base_avail=0.85, is_b2b=True), 0.05)

        # 6. Clear injury and verify snapshot clearance event is logged
        self.tracker.clear_injury(101)
        self.assertIsNone(self.tracker.get_injury(101))

        with self.tracker._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT status, injury_desc FROM injury_snapshots WHERE player_id = 101 ORDER BY id DESC LIMIT 1")
            snap = cur.fetchone()
            self.assertIsNotNone(snap)
            self.assertEqual(snap[0], 'CLEARED')
            self.assertIn("Cleared from active injury list", snap[1])

    def test_bulk_sync_and_unlisted_team_reconciliation(self):
        # Setup active injuries for two teams
        self.tracker.set_injury(201, "Player A", "OUT", team="TOR")
        self.tracker.set_injury(202, "Player B", "QUESTIONABLE", team="TOR")
        self.tracker.set_injury(301, "Player C", "OUT", team="BOS")

        def mock_resolver(name):
            mapping = {"Player A": 201, "Player B": 202, "Player C": 301, "Player D": 203}
            return mapping.get(name)

        # New sync where Player B has recovered (missing from TOR report) and Player D is new OUT
        incoming = [
            {'name': 'Player A', 'status': 'OUT', 'desc': 'Knee', 'team': 'TOR'},
            {'name': 'Player D', 'status': 'OUT', 'desc': 'Ankle', 'team': 'TOR'}
        ]

        self.tracker.bulk_sync_yahoo_statuses(incoming, mock_resolver, clear_unlisted_teams={'TOR'})

        # Player A is still OUT
        self.assertIsNotNone(self.tracker.get_injury(201))
        # Player D is newly added
        self.assertIsNotNone(self.tracker.get_injury(203))
        # Player B should be cleared because TOR was synced and Player B was unlisted
        self.assertIsNone(self.tracker.get_injury(202))
        # Player C (BOS) is unaffected because BOS was not in clear_unlisted_teams
        self.assertIsNotNone(self.tracker.get_injury(301))

    def test_bayesian_player_injury_integration(self):
        bp = BayesianPlayer(player_id=201, name="Tyrese Maxey")
        bp.availability_rate = 0.92

        # Healthy
        self.assertGreater(bp.get_effective_game_availability(), 0.85)

        # OUT
        bp.update_injury_status('OUT', desc='Ankle')
        self.assertEqual(bp.get_effective_game_availability(), 0.0)

        # QUESTIONABLE
        bp.update_injury_status('QUESTIONABLE')
        self.assertEqual(bp.get_effective_game_availability(), 0.52)

        # DOUBTFUL
        bp.update_injury_status('DOUBTFUL')
        self.assertEqual(bp.get_effective_game_availability(), 0.15)

        # B2B REST
        bp.update_injury_status('HEALTHY', is_b2b_rest=True)
        self.assertEqual(bp.get_effective_game_availability(is_b2b=False), float(np.clip(0.35 * 0.92 + 0.65 * 0.92, 0.35, 0.96)))
        self.assertEqual(bp.get_effective_game_availability(is_b2b=True), 0.05)

    def test_matchup_engine_il_streaming(self):
        players = {}
        for pid in range(1, 15):
            bp = BayesianPlayer(player_id=pid, name=f"Player_{pid}")
            bp.expected_minutes = 28.0
            bp.alphas = {s: 10.0 for s in COUNT_STATS + PERCENTAGE_STATS}
            bp.betas = {s: 100.0 for s in COUNT_STATS + PERCENTAGE_STATS}
            bp.att_alphas = {'FG': 10.0, 'FT': 5.0}
            bp.att_betas = {'FG': 25.0, 'FT': 10.0}
            players[pid] = bp

        players[1].update_injury_status('OUT')
        players[2].update_injury_status('OUT')

        roster_ids = list(range(1, 14))
        free_agent_pool = [14]

        engine = MatchupEngine(
            bayesian_players_dict=players,
            df_schedule=pd.DataFrame(),
            df_positions=pd.DataFrame(),
            free_agent_pool=free_agent_pool,
            num_il_slots=2,
            max_weekly_adds=3
        )

        dist = engine.get_expected_weekly_distribution(roster_ids)
        self.assertIn('PTS', dist['mean'])
        self.assertGreater(dist['mean']['PTS'], 0.0)

if __name__ == '__main__':
    unittest.main()

"""SQLite injury persistence and clearance tests, isolated from live state."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.injury_tracker import InjuryTracker


class TestInjurySystem(unittest.TestCase):
    def setUp(self):
        # Create a completely isolated temporary directory and SQLite database for testing
        self.test_dir = tempfile.mkdtemp(
            prefix="nba_test_inj_", dir=Path(__file__).resolve().parent
        )
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
            is_b2b_rest=False,
        )

        inj = self.tracker.get_injury(101)
        self.assertIsNotNone(inj)
        self.assertEqual(inj["status"], "OUT")
        self.assertEqual(inj["injury_desc"], "Knee management")

        # 2. Check play probability for OUT
        prob_out = self.tracker.get_play_probability(101, base_avail=0.85)
        self.assertEqual(prob_out, 0.0)

        # 3. Test B2B rest
        self.tracker.set_injury(
            player_id=102,
            player_name="Joel Embiid",
            status="B2B_REST",
            team="PHI",
            is_b2b_rest=True,
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
            desc="Load management",
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
            is_b2b_rest=True,
        )
        self.assertEqual(
            self.tracker.get_play_probability(104, base_avail=0.85, is_b2b=False), 0.52
        )
        self.assertEqual(self.tracker.get_play_probability(104, base_avail=0.85, is_b2b=True), 0.05)

        # 6. Clear injury and verify snapshot clearance event is logged
        self.tracker.clear_injury(101)
        self.assertIsNone(self.tracker.get_injury(101))

        with self.tracker._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT status, injury_desc FROM injury_snapshots WHERE player_id = 101 ORDER BY id DESC LIMIT 1"
            )
            snap = cur.fetchone()
            self.assertIsNotNone(snap)
            self.assertEqual(snap[0], "CLEARED")
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
            {"name": "Player A", "status": "OUT", "desc": "Knee", "team": "TOR"},
            {"name": "Player D", "status": "OUT", "desc": "Ankle", "team": "TOR"},
        ]

        self.tracker.bulk_sync_yahoo_statuses(incoming, mock_resolver, clear_unlisted_teams={"TOR"})

        # Player A is still OUT
        self.assertIsNotNone(self.tracker.get_injury(201))
        # Player D is newly added
        self.assertIsNotNone(self.tracker.get_injury(203))
        # Player B should be cleared because TOR was synced and Player B was unlisted
        self.assertIsNone(self.tracker.get_injury(202))
        # Player C (BOS) is unaffected because BOS was not in clear_unlisted_teams
        self.assertIsNotNone(self.tracker.get_injury(301))

    def test_partial_espn_feed_clears_only_explicitly_covered_teams(self):
        self.tracker.set_injury(
            201, "Still out", "OUT", team="Missing Team", source="espn_rotowire"
        )
        self.tracker.set_injury(
            202, "Recovered", "OUT", team="Covered Team", source="espn_rotowire"
        )
        response = Mock(status_code=200)
        response.json.return_value = {"injuries": [{"displayName": "Covered Team", "injuries": []}]}
        with patch("requests.get", return_value=response):
            self.tracker.sync_espn_injuries()
        self.assertIsNotNone(self.tracker.get_injury(201))
        self.assertIsNone(self.tracker.get_injury(202))

    def test_failed_official_report_cannot_mutate_database(self):
        self.tracker.set_injury(203, "Existing injury", "OUT", team="Test Team")
        scraper = Mock()
        scraper.run_health_checks.return_value = (
            False,
            [{"name": "Existing injury", "status": "AVAILABLE"}],
            [],
            {},
        )
        count = self.tracker.sync_official_report({"rows": []}, lambda _: 203, scraper)
        self.assertEqual(count, 0)
        self.assertEqual(self.tracker.get_injury(203)["status"], "OUT")

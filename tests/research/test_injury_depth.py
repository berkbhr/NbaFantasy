import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from research.injury_depth import allocate_il, asof_report


class InjuryDepthTests(unittest.TestCase):
    def test_il_is_not_two_free_healthy_roster_slots(self):
        pool = list(range(260))
        rosters = [pool[i * 13 : (i + 1) * 13] for i in range(14)]
        teams, stashes = allocate_il(rosters, pool, set(), 9000)
        self.assertEqual(teams, rosters)
        self.assertFalse(stashes)
        out = {1, 3, 4, 183, 184, 185, 186}
        teams, stashes = allocate_il(rosters, pool, out, 9000)
        self.assertTrue(stashes <= out)
        owned = [p for team in teams for p in team]
        self.assertEqual(len(owned), len(set(owned)))
        self.assertLessEqual(len(owned), 210)
        for team in teams:
            self.assertEqual(len(set(team) - stashes), 13)
            self.assertLessEqual(len(set(team) & stashes), 2)

    def test_future_report_header_is_not_used_even_with_same_file_date(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            root = Path(tmp)
            folder = root / "data/archive/historical_injuries/2024_25"
            folder.mkdir(parents=True)
            for date, stamp in (
                ("2024-11-10", "2024-11-10T17:00Z"),
                ("2024-11-11", "2024-11-11T18:00Z"),
            ):
                (folder / (date + ".json.gz")).write_bytes(
                    gzip.compress(json.dumps({"status": "usable", "report_at": stamp}).encode())
                )
            with patch("research.injury_depth.ROOT", root):
                stamp, _, _ = asof_report("2024_25", pd.Timestamp("2024-11-11T14:00Z"))
            self.assertEqual(stamp, pd.Timestamp("2024-11-10T17:00Z"))


if __name__ == "__main__":
    unittest.main()

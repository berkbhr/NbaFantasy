import unittest

import pandas as pd

from src.research import audit_logs, protocol


class ResearchTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame(
            [
                {
                    "PLAYER_ID": 1,
                    "GAME_ID": "g1",
                    "GAME_DATE": "2024-10-22",
                    "TEAM_ID": 10,
                    "MIN": 20,
                    "PTS": 12,
                    "REB": 3,
                    "AST": 2,
                    "STL": 0,
                    "BLK": 1,
                    "TOV": 2,
                    "FG3M": 1,
                    "FGM": 5,
                    "FGA": 10,
                    "FTM": 1,
                    "FTA": 2,
                }
            ]
        )

    def test_corrupt_caches_fail_before_silent_dedup_or_fit(self):
        frame = self.frame()
        self.assertTrue(audit_logs(frame)["valid"])
        duplicate = pd.concat([frame, frame], ignore_index=True)
        self.assertFalse(audit_logs(duplicate)["valid"])
        for key, value in (
            ("GAME_DATE", "bad"),
            ("GAME_ID", None),
            ("MIN", float("inf")),
            ("FGA", 2),
            ("PTS", 99),
            ("BLK", -1),
        ):
            altered = frame.copy()
            if key == "MIN":
                altered[key] = altered[key].astype(float)
            altered.loc[0, key] = value
            self.assertFalse(audit_logs(altered)["valid"], key)
        self.assertFalse(audit_logs(frame.iloc[:0])["valid"])

    def test_roster_seed_split_and_pilot_boundary_are_frozen(self):
        p = protocol(14)
        seeds = p["roster_seeds"]
        self.assertFalse(set(seeds["development"]) & set(seeds["assessment"]))
        self.assertEqual(len(seeds["development"]), 20)
        self.assertEqual(p["development"]["prior"], "2023_24")
        self.assertFalse(seeds["executed"])
        for days in (0, 29):
            with self.assertRaises(ValueError):
                protocol(days)


if __name__ == "__main__":
    unittest.main()

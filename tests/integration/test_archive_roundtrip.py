import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.prospective import monitor, read_record, settle, write_once


class ArchiveRoundtripTests(unittest.TestCase):
    def test_prediction_settlement_correction_and_earliest_horizon_dedup(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory).resolve()
            archive = root / "data/archive"
            logs_path = root / "data/raw/player_logs_2026_27.parquet"
            logs_path.parent.mkdir(parents=True)
            (root / "reports").mkdir()
            logs = pd.DataFrame(
                [
                    {
                        "PLAYER_ID": 1,
                        "TEAM_ID": 10,
                        "GAME_ID": "g",
                        "GAME_DATE": "2026-10-28",
                        "MIN": 11,
                        "PTS": 8,
                        "REB": 2,
                        "AST": 1,
                        "STL": 0,
                        "BLK": 0,
                        "FG3M": 0,
                        "TOV": 1,
                        "FGM": 4,
                        "FGA": 8,
                        "FTM": 0,
                        "FTA": 0,
                    }
                ]
            )
            logs.to_parquet(logs_path, index=False)
            stamps = ["20261027T200000000000Z", "20261027T220000000000Z"]
            for index, stamp in enumerate(stamps):
                rows = [
                    {
                        "player_id": pid,
                        "name": name,
                        "team_id": 10,
                        "team_code": "AAA",
                        "game_id": "g",
                        "game_date": "2026-10-28",
                        "star": True,
                        "availability": 0.5,
                        "observed_gp": 3,
                        "observed_mpg": 8,
                        "prediction": {"MIN": {"mean": 10 if not index else 50}},
                    }
                    for pid, name in ((1, "Example"), (2, "Benched"))
                ]
                shadow = [{**row, "prediction": {"MIN": {"mean": 13}}} for row in rows]
                write_once(
                    archive / "predictions" / f"{stamp}.json.gz",
                    {
                        "forecast_id": stamp,
                        "cutoff_at": "2026-10-27T20:00:00+00:00",
                        "player_predictions": {"primary": rows, "shadow": shadow},
                    },
                )
            write_once(
                archive / "final_roster_labels/2026-10-28.json.gz",
                {
                    "rows": [
                        {"norm": "example", "team_code": "AAA", "played": True},
                        {"norm": "benched", "team_code": "AAA", "played": False},
                    ]
                },
            )
            before = {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (archive / "predictions").glob("*")
            }
            with (
                patch("src.prospective.ROOT", root),
                patch("src.prospective.ARCHIVE", archive),
                patch("src.prospective.final_boxscore", return_value=None),
                patch("src.prospective.datetime") as clock,
            ):
                clock.now.return_value = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)
                settle()
                initial_outcomes = list((archive / "outcomes").rglob("*.gz"))
                self.assertEqual(len(initial_outcomes), 2)
                initial_hashes = {
                    p: hashlib.sha256(p.read_bytes()).hexdigest() for p in initial_outcomes
                }
                settle()
                self.assertEqual(len(list((archive / "outcomes").rglob("*.gz"))), 2)
                logs.loc[0, "MIN"] = 12
                logs.to_parquet(logs_path, index=False)
                clock.now.return_value = datetime(2026, 10, 29, 12, 1, tzinfo=timezone.utc)
                settle()
                self.assertEqual(len(list((archive / "outcomes").rglob("*.gz"))), 4)
                for path, digest in initial_hashes.items():
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
                monitor()
            result = json.loads((root / "reports/prospective_status.json").read_text())
            self.assertEqual(result["unique_player_games"], 2)
            self.assertEqual(result["stars"]["n"], 1)
            self.assertEqual(result["stars"]["prediction_minute_mae"], 2)
            self.assertEqual(result["availability_descriptive"]["n"], 2)
            self.assertEqual(
                before,
                {
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (archive / "predictions").glob("*")
                },
            )
            self.assertTrue(
                any(not r["played"] for r in read_record(initial_outcomes[0])["labels"])
            )


if __name__ == "__main__":
    unittest.main()

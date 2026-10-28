import unittest

from tests.helpers import assistant, logs


class TestLiveIngestion(unittest.TestCase):
    def test_replaying_logs_does_not_double_count_stats_or_absences(self):
        session = assistant()
        frame = logs()
        session.apply_current_season_logs(frame)
        alpha = session.players[1].alphas.copy()
        availability = (session.players[6].avail_alpha, session.players[6].avail_beta)
        session.apply_current_season_logs(frame)
        self.assertEqual(alpha, session.players[1].alphas)
        self.assertEqual(
            availability, (session.players[6].avail_alpha, session.players[6].avail_beta)
        )
        self.assertEqual(session.players[6].consecutive_dnps, 3)

    def test_batch_and_incremental_ingestion_have_same_posterior(self):
        batch, incremental = assistant(), assistant()
        frame = logs()
        batch.apply_current_season_logs(frame)
        for _, daily in frame.groupby("GAME_DATE", sort=True):
            incremental.apply_current_season_logs(daily)
        for pid in batch.players:
            self.assertEqual(batch.players[pid].alphas, incremental.players[pid].alphas)
            self.assertAlmostEqual(
                batch.players[pid].expected_minutes, incremental.players[pid].expected_minutes
            )
            self.assertEqual(
                batch.players[pid].consecutive_dnps, incremental.players[pid].consecutive_dnps
            )

    def test_zero_minutes_counts_as_dnp(self):
        session = assistant()
        frame = logs(1)
        frame.loc[frame.PLAYER_ID == 1, "MIN"] = 0
        session.apply_current_season_logs(frame)
        self.assertEqual(session.players[1].consecutive_dnps, 1)

    def test_partial_boxscore_cannot_fabricate_absences(self):
        session = assistant()
        session.apply_current_season_logs(logs(1).iloc[:2])
        self.assertEqual(session.players[6].consecutive_dnps, 0)


if __name__ == "__main__":
    unittest.main()

import unittest

import pandas as pd

from src.live_draft_assistant import LiveDraftAssistant
from src.matchup_engine import ALL_CATEGORIES, MatchupEngine
from tests.test_model import player


def assistant():
    """Minimal in-memory session; no user DB, current roster or network."""
    result = LiveDraftAssistant.__new__(LiveDraftAssistant)
    result.players = {i: player(i) for i in range(1, 7)}
    result.engine = MatchupEngine(
        result.players, pd.DataFrame(), pd.DataFrame(), team_map=dict.fromkeys(result.players, 10)
    )
    result._ingested_games = set()
    result._availability_games = set()
    result._role_history = {}
    result._role_prior_minutes = {}
    result.priors = {}
    result.pos_averages = {}
    result.pos_dict = {}
    result.available_player_ids = set(result.players)
    result.team_abbr_dict = {}
    result._suggestion_cache = {}
    result._refresh_projected_stats_dict = lambda: None
    result.calculate_baselines = lambda: None
    return result


def logs(days=3):
    rows = []
    for d in range(days):
        for pid in range(1, 6):
            rows.append(
                {
                    **dict.fromkeys(ALL_CATEGORIES, 0),
                    "PLAYER_ID": pid,
                    "PLAYER_NAME": str(pid),
                    "TEAM_ID": 10,
                    "GAME_ID": str(d),
                    "GAME_DATE": pd.Timestamp("2026-10-20") + pd.Timedelta(days=d),
                    "MIN": 20 + pid,
                    "PTS": 10 + pid,
                }
            )
    return pd.DataFrame(rows)


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

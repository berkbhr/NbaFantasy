"""Shared in-memory fixtures; no network or user-cache writes."""

import pandas as pd

from src.bayesian_model import BayesianPlayer
from src.live_draft_assistant import LiveDraftAssistant
from src.matchup_engine import ALL_CATEGORIES, MatchupEngine


def player(pid=1, minutes=30):
    bp = BayesianPlayer(pid, str(pid))
    bp.initialize_priors(
        {
            "MIN": 2100,
            "GP": 70,
            "PTS": 1400,
            "REB": 600,
            "AST": 250,
            "STL": 70,
            "BLK": 50,
            "TOV": 150,
            "FG3M": 100,
            "FGM": 550,
            "FGA": 1100,
            "FTM": 200,
            "FTA": 250,
        }
    )
    bp.expected_minutes = bp.base_expected_minutes = minutes
    return bp


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

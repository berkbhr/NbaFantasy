"""
Current-season (in-progress) NBA player game log ingestion for the live cloud sync.

The live pipeline is initialized from prior-season priors (load_prior_season). Without feeding the
games of the season in progress, a player whose role collapsed (e.g. 29 -> 5 MPG) or exploded
keeps being projected on last season's role. This module downloads the regular-season player logs
of the current season so they can be applied as Bayesian updates (BayesianPlayer.update_stats).

Network failures (stats.nba.com often throttles cloud runners) fall back to the cached parquet.
"""

import os
import time

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")

REQUIRED_COLS = [
    "PLAYER_ID",
    "PLAYER_NAME",
    "TEAM_ID",
    "TEAM_ABBREVIATION",
    "GAME_ID",
    "GAME_DATE",
    "MIN",
]


def season_cache_path(season="2026-27"):
    return os.path.join(RAW_DIR, f"player_logs_{season.replace('-', '_')}.parquet")


def _load_cache(path):
    if os.path.exists(path):
        try:
            df = pd.read_parquet(path)
            if not df.empty:
                return df
        except Exception as e:
            print(f"  [WARN] Could not read cached season logs {path}: {e}")
    return pd.DataFrame()


def fetch_current_season_logs(season="2026-27", timeout=45, retries=2, use_network=True):
    """
    Returns a DataFrame of regular-season player game logs for `season` (one row per player-game).
    Tries nba_api first (saving to cache on success); on failure returns the cached parquet, or an
    empty DataFrame if neither is available. Returns (df, source) where source in {'live', 'cache', 'none'}.
    """
    path = season_cache_path(season)
    if use_network:
        try:
            from nba_api.stats.endpoints import leaguegamelog
        except Exception as e:
            print(f"  [WARN] nba_api unavailable ({e}); using cached season logs.")
            leaguegamelog = None

        if leaguegamelog is not None:
            for attempt in range(1, retries + 1):
                try:
                    df = leaguegamelog.LeagueGameLog(
                        season=season,
                        season_type_all_star="Regular Season",
                        player_or_team_abbreviation="P",
                        timeout=timeout,
                    ).get_data_frames()[0]
                    if (
                        df is not None
                        and not df.empty
                        and all(c in df.columns for c in REQUIRED_COLS)
                    ):
                        df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"]).dt.normalize()
                        df = df.sort_values(["GAME_DATE", "PLAYER_ID"]).reset_index(drop=True)
                        os.makedirs(RAW_DIR, exist_ok=True)
                        try:
                            df.to_parquet(path, index=False)
                        except Exception as e:
                            print(f"  [WARN] Could not cache season logs: {e}")
                        return df, "live"
                    # Empty response before opening night is legitimate
                    if df is not None and df.empty:
                        cached = _load_cache(path)
                        return (cached, "cache") if not cached.empty else (pd.DataFrame(), "none")
                except Exception as e:
                    print(f"  [WARN] Season log fetch attempt {attempt}/{retries} failed: {e}")
                    time.sleep(2.0 * attempt)

    cached = _load_cache(path)
    if not cached.empty:
        return cached, "cache"
    return pd.DataFrame(), "none"

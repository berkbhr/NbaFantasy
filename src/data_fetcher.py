import os
import time

import pandas as pd
from nba_api.stats.endpoints import (
    leaguegamelog,
    playerindex,
    scheduleleaguev2,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)


def fetch_and_process_season(season="2025-26"):
    print(f"=== Fetching Data for Season {season} ===")

    season_id_format = season
    file_suffix = season.replace("-", "_")

    # 1. Fetch Player Game Logs
    print("1. Fetching Player Game Logs...")
    try:
        player_log = leaguegamelog.LeagueGameLog(
            season=season_id_format, player_or_team_abbreviation="P"
        )
        df_players = player_log.get_data_frames()[0]
        time.sleep(1)
    except Exception as e:
        print(f"Error fetching player logs for {season}: {e}")
        return

    df_players["GAME_DATE"] = pd.to_datetime(df_players["GAME_DATE"])
    df_players = df_players.sort_values(by=["GAME_DATE", "PLAYER_ID"])
    df_players.to_parquet(os.path.join(RAW_DIR, f"player_logs_{file_suffix}.parquet"), index=False)

    # 2. Fetch Team Game Logs
    print("2. Fetching Team Game Logs...")
    try:
        team_log = leaguegamelog.LeagueGameLog(
            season=season_id_format, player_or_team_abbreviation="T"
        )
        df_teams = team_log.get_data_frames()[0]
        time.sleep(1)
    except Exception as e:
        print(f"Error fetching team logs for {season}: {e}")
        return

    df_teams["GAME_DATE"] = pd.to_datetime(df_teams["GAME_DATE"])
    df_teams = df_teams.sort_values(by=["GAME_DATE", "TEAM_ID"])
    df_teams.to_parquet(os.path.join(RAW_DIR, f"team_logs_{file_suffix}.parquet"), index=False)

    # 3. Generate Schedule
    print("3. Generating Team Schedule...")
    df_schedule = df_teams[
        ["GAME_DATE", "TEAM_ID", "TEAM_ABBREVIATION", "GAME_ID", "MATCHUP"]
    ].copy()
    df_schedule.to_parquet(
        os.path.join(PROCESSED_DIR, f"schedule_{file_suffix}.parquet"), index=False
    )

    print(f"=== Successfully processed {season} ===")


def fetch_upcoming_2026_27_pre_draft_assets():
    """
    Downloads all required 2026-27 NBA season assets for the live Yahoo Fantasy Draft:
      1. Active 2026-27 NBA Roster, Positions, Draft Pick Info & Current Teams (PlayerIndex)
      2. Official 2026-27 NBA Regular Season Schedule (ScheduleLeagueV2)
      3. 2026-27 Preseason Player Game Logs (for rookies & offseason role verification)
      4. Merges all new 2026-27 players/positions into player_positions.parquet
    """
    print("=== Fetching Upcoming 2026-27 NBA Season Assets for Live Yahoo Draft ===")

    # 1. Fetch 2026-27 Active Players, Teams, Positions & Draft Info
    print("1. Fetching 2026-27 PlayerIndex (Active Rosters, Positions, Draft Picks)...")
    pi_df = playerindex.PlayerIndex(season="2026-27").get_data_frames()[0]
    pi_df["PLAYER_ID"] = pi_df["PERSON_ID"].astype(int)
    pi_df["PLAYER_NAME"] = (
        pi_df["PLAYER_FIRST_NAME"].fillna("") + " " + pi_df["PLAYER_LAST_NAME"].fillna("")
    ).str.strip()
    pi_df["POSITION"] = pi_df["POSITION"].fillna("G-F").replace("", "G-F")

    roster_cols = [
        "PLAYER_ID",
        "PLAYER_NAME",
        "TEAM_ID",
        "TEAM_ABBREVIATION",
        "POSITION",
        "FROM_YEAR",
        "TO_YEAR",
        "DRAFT_YEAR",
        "DRAFT_ROUND",
        "DRAFT_NUMBER",
    ]
    available_cols = [c for c in roster_cols if c in pi_df.columns]
    df_roster_26_27 = pi_df[available_cols].drop_duplicates(subset=["PLAYER_ID"]).copy()
    roster_out = os.path.join(PROCESSED_DIR, "active_roster_2026_27.parquet")
    df_roster_26_27.to_parquet(roster_out, index=False)
    print(f"   Saved {len(df_roster_26_27)} active 2026-27 players to {roster_out}")

    # Update player_positions.parquet and player_positions_2026_27.parquet
    pos_26_27 = df_roster_26_27[["PLAYER_ID", "PLAYER_NAME", "POSITION"]].copy()
    pos_26_27.to_parquet(
        os.path.join(PROCESSED_DIR, "player_positions_2026_27.parquet"), index=False
    )

    master_pos_path = os.path.join(PROCESSED_DIR, "player_positions.parquet")
    if os.path.exists(master_pos_path):
        old_pos = pd.read_parquet(master_pos_path)
        combined_pos = pd.concat([pos_26_27, old_pos], ignore_index=True)
        combined_pos = combined_pos.drop_duplicates(subset=["PLAYER_ID"], keep="first").reset_index(
            drop=True
        )
    else:
        combined_pos = pos_26_27
    combined_pos.to_parquet(master_pos_path, index=False)
    print(f"   Updated master {master_pos_path} (total unique players: {len(combined_pos)})")

    # 2. Fetch Official 2026-27 NBA Regular Season Schedule
    print("2. Fetching Official 2026-27 NBA Regular Season Schedule...")
    sched_raw = scheduleleaguev2.ScheduleLeagueV2(season="2026-27").get_data_frames()[0]
    # Filter strictly to Regular Season games (gameId starts with '002')
    reg_sched = sched_raw[sched_raw["gameId"].astype(str).str.startswith("002")].copy()
    reg_sched["GAME_DATE"] = pd.to_datetime(reg_sched["gameDate"]).dt.normalize()

    team_rows = []
    for _, row in reg_sched.iterrows():
        gid = str(row["gameId"])
        gdate = row["GAME_DATE"]
        h_id = int(row["homeTeam_teamId"])
        h_tri = str(row["homeTeam_teamTricode"])
        a_id = int(row["awayTeam_teamId"])
        a_tri = str(row["awayTeam_teamTricode"])
        wk = int(row.get("weekNumber", 0)) if pd.notnull(row.get("weekNumber", None)) else 0
        tipoff = pd.to_datetime(row.get("gameDateTimeUTC"), utc=True, errors="coerce")

        team_rows.append(
            {
                "GAME_DATE": gdate,
                "TEAM_ID": h_id,
                "TEAM_ABBREVIATION": h_tri,
                "GAME_ID": gid,
                "MATCHUP": f"{h_tri} vs. {a_tri}",
                "WEEK_NUMBER": wk,
                "TIPOFF_UTC": tipoff,
                "CLOCK_OBSERVED_AT": pd.Timestamp.now(tz="UTC"),
            }
        )
        team_rows.append(
            {
                "GAME_DATE": gdate,
                "TEAM_ID": a_id,
                "TEAM_ABBREVIATION": a_tri,
                "GAME_ID": gid,
                "MATCHUP": f"{a_tri} @ {h_tri}",
                "WEEK_NUMBER": wk,
                "TIPOFF_UTC": tipoff,
                "CLOCK_OBSERVED_AT": pd.Timestamp.now(tz="UTC"),
            }
        )

    df_sched_26_27 = (
        pd.DataFrame(team_rows).sort_values(["GAME_DATE", "TEAM_ID"]).reset_index(drop=True)
    )
    sched_out = os.path.join(PROCESSED_DIR, "schedule_2026_27.parquet")
    df_sched_26_27.to_parquet(sched_out, index=False)
    print(
        f"   Saved {len(df_sched_26_27)} team-games ({len(reg_sched)} NBA games, "
        f"{df_sched_26_27['GAME_DATE'].min().date()} to {df_sched_26_27['GAME_DATE'].max().date()}) to {sched_out}"
    )

    # 3. Fetch 2026-27 Preseason Player Game Logs
    print("3. Fetching 2026-27 Preseason Player Game Logs...")
    try:
        pre_logs = leaguegamelog.LeagueGameLog(
            season="2026-27", season_type_all_star="Pre Season", player_or_team_abbreviation="P"
        ).get_data_frames()[0]
        pre_logs["GAME_DATE"] = pd.to_datetime(pre_logs["GAME_DATE"]).dt.normalize()
        pre_out = os.path.join(RAW_DIR, "preseason_logs_2026_27.parquet")
        pre_logs.to_parquet(pre_out, index=False)
        print(f"   Saved {len(pre_logs)} preseason player-game logs to {pre_out}")

    except Exception as e:
        print(f"   Warning: Could not fetch 2026-27 preseason logs: {e}")

    print("=== All 2026-27 Pre-Draft Assets Ready! ===")


if __name__ == "__main__":
    fetch_upcoming_2026_27_pre_draft_assets()

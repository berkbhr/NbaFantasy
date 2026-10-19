import os
import pandas as pd
import numpy as np
from bayesian_model import BayesianPlayer, COUNT_STATS, PERCENTAGE_STATS

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
RAW_DIR = os.path.join(DATA_DIR, 'raw')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')

AGG_COLS = COUNT_STATS + [f"{s}M" for s in PERCENTAGE_STATS] + [f"{s}A" for s in PERCENTAGE_STATS] + ['MIN', 'GP']


def _load_single_season_totals(season):
    parquet_path = os.path.join(RAW_DIR, f'player_logs_{season}.parquet')
    excel_path = os.path.join(PROCESSED_DIR, f'Master_Database_{season}.xlsx')

    if os.path.exists(parquet_path):
        df = pd.read_parquet(parquet_path)
    elif os.path.exists(excel_path):
        df = pd.read_excel(excel_path, sheet_name='Player_Stats')
    else:
        return {}, {}

    df = df[df['MIN'] > 0].copy()
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df = df.sort_values('GAME_DATE')
    df['GP'] = 1

    for col in AGG_COLS:
        if col not in df.columns:
            df[col] = 0

    totals = df.groupby('PLAYER_ID')[AGG_COLS].sum().reset_index()

    # Also compute late-season (last 15 games) MPG to capture post-trade-deadline role expansions
    last_15_mpg = df.groupby('PLAYER_ID').tail(15).groupby('PLAYER_ID')['MIN'].mean().to_dict()

    prior_dict = {}
    for _, row in totals.iterrows():
        p_id = int(row['PLAYER_ID'])
        d = {col: float(row[col]) for col in AGG_COLS}
        full_mpg = d['MIN'] / max(1.0, d['GP'])
        late_mpg = float(last_15_mpg.get(p_id, full_mpg))
        # Blend 65% full-season MPG + 35% late-season MPG if player played >= 15 games
        if d['GP'] >= 15:
            d['ROLE_MPG'] = 0.65 * full_mpg + 0.35 * late_mpg
        else:
            d['ROLE_MPG'] = full_mpg
        prior_dict[p_id] = d

    return prior_dict, last_15_mpg


def load_prior_season(season="2025_26", blend_prev_season=True):
    """
    Loads prior season data into {player_id: {stats}}.
    When loading '2025_26' for the upcoming 2026-27 Yahoo Draft, blends:
      - 75% weight on 2025-26 regular season (with late-season role MPG boost)
      - 25% weight on 2024-25 regular season (higher anchor if player missed time in 2025-26)
      - 2026-27 Preseason game logs for incoming 2026-27 rookies & low-minute players
    """
    primary_dict, _ = _load_single_season_totals(season)
    if not primary_dict:
        print(f"Prior data for {season} not found.")
        return {}

    prev_season_map = {
        "2025_26": "2024_25",
        "2024_25": "2023_24",
        "2023_24": "2022_23",
    }
    prev_season = prev_season_map.get(season)
    secondary_dict = {}
    if blend_prev_season and prev_season:
        secondary_dict, _ = _load_single_season_totals(prev_season)

    combined_pids = set(primary_dict.keys()) | set(secondary_dict.keys())
    blended_dict = {}

    pre_active_pids = set()
    if season == "2025_26":
        pre_path_chk = os.path.join(RAW_DIR, 'preseason_logs_2026_27.parquet')
        if os.path.exists(pre_path_chk):
            df_pre_chk = pd.read_parquet(pre_path_chk, columns=['PLAYER_ID', 'MIN'])
            pre_active_pids = set(df_pre_chk[df_pre_chk['MIN'] > 0]['PLAYER_ID'].astype(int).tolist())

    for pid in combined_pids:
        p1 = primary_dict.get(pid)
        p0 = secondary_dict.get(pid)

        if p1 and p0:
            gp1 = p1['GP']
            gp0 = p0['GP']
            # If player played >= 50 games in primary season, 78% primary + 22% secondary;
            # if injured in primary season (e.g. < 45 GP), rely more on healthy secondary season
            w1 = min(0.80, max(0.35, gp1 / 65.0))
            w0 = 1.0 - w1
            entry = {}
            for col in AGG_COLS:
                entry[col] = w1 * p1[col] + w0 * p0[col]
            raw_blended_min = max(1.0, entry['MIN'])
            # Effective GP/MIN for availability & MPG: if healthy in 2026-27 preseason after a 2025-26 injury,
            # regress GP and MPG back toward healthy multi-year baseline
            if pid in pre_active_pids and gp0 >= 58 and gp1 < 50:
                eff_gp = max(gp1, 0.30 * gp1 + 0.70 * gp0)
                mpg1 = p1.get('ROLE_MPG', p1['MIN'] / max(1.0, gp1))
                mpg0 = p0.get('ROLE_MPG', p0['MIN'] / max(1.0, gp0))
                role_mpg = max(w1 * mpg1 + w0 * mpg0, 0.35 * mpg1 + 0.65 * mpg0)
            else:
                eff_gp = max(gp1, 0.60 * gp1 + 0.40 * gp0)
                role_mpg = w1 * p1.get('ROLE_MPG', p1['MIN'] / max(1.0, gp1)) + w0 * (p0['MIN'] / max(1.0, gp0))
            entry['GP'] = eff_gp
            target_min = role_mpg * entry['GP']
            scale_m = target_min / raw_blended_min
            for col in AGG_COLS:
                if col != 'GP':
                    entry[col] = entry[col] * scale_m
            entry['MIN'] = target_min
            blended_dict[pid] = entry
        elif p1:
            entry = dict(p1)
            if 'ROLE_MPG' in p1 and p1['GP'] >= 15:
                # Adjust effective MIN to reflect late-season role MPG while preserving per-minute rates
                scale_m = (p1['ROLE_MPG'] * p1['GP']) / max(1.0, p1['MIN'])
                for col in AGG_COLS:
                    if col != 'GP':
                        entry[col] = p1[col] * scale_m
            blended_dict[pid] = entry
        elif p0:
            # Player missed the entire primary season (e.g. season-long injury in 2025-26, returning for 2026-27)
            mult = 0.82 if pid in pre_active_pids else 0.75
            entry = {col: p0[col] * mult for col in AGG_COLS}
            entry['GP'] = p0['GP'] * mult
            blended_dict[pid] = entry

    # If preparing 2025_26 priors for the 2026-27 Draft, integrate 2026-27 Preseason logs for rookies
    if season == "2025_26":
        pre_path = os.path.join(RAW_DIR, 'preseason_logs_2026_27.parquet')
        roster_path = os.path.join(PROCESSED_DIR, 'active_roster_2026_27.parquet')
        if os.path.exists(pre_path) and os.path.exists(roster_path):
            df_pre = pd.read_parquet(pre_path)
            df_pre = df_pre[df_pre['MIN'] > 0].copy()
            df_pre['GP'] = 1
            for col in AGG_COLS:
                if col not in df_pre.columns:
                    df_pre[col] = 0
            pre_totals = df_pre.groupby('PLAYER_ID')[AGG_COLS].sum().reset_index()

            df_rost = pd.read_parquet(roster_path)
            draft_num_map = {}
            for _, r in df_rost.iterrows():
                try:
                    dnum = int(r['DRAFT_NUMBER']) if pd.notnull(r.get('DRAFT_NUMBER')) and str(r.get('DRAFT_NUMBER')).isdigit() else 60
                except Exception:
                    dnum = 60
                draft_num_map[int(r['PLAYER_ID'])] = dnum

            for _, row in pre_totals.iterrows():
                pid = int(row['PLAYER_ID'])
                pre_min = float(row['MIN'])
                pre_gp = float(row['GP'])
                if pre_min < 20 or pre_gp < 1:
                    continue

                existing = blended_dict.get(pid)
                if existing is None or existing.get('MIN', 0) < 150:
                    # Project rookie MPG & availability by draft pedigree, while keeping effective prior_min
                    # proportional to rookie certainty (200-450 mins) so Empirical Bayes shrinks preseason noise!
                    dnum = draft_num_map.get(pid, 60)
                    pre_mpg = pre_min / pre_gp
                    if dnum == 1:
                        target_mpg = max(pre_mpg, 30.0)
                        eff_prior_gp = 16.0  # ~480 effective prior minutes for #1 overall pick (Cooper Flagg)
                        rookie_avail_gp = 68.0
                    elif dnum <= 5:
                        target_mpg = min(27.0, max(pre_mpg, 24.0))
                        eff_prior_gp = 10.0  # ~250 effective prior minutes
                        rookie_avail_gp = 64.0
                    elif dnum <= 14:
                        target_mpg = min(24.0, max(pre_mpg, 20.0))
                        eff_prior_gp = 7.0   # ~150 effective prior minutes
                        rookie_avail_gp = 60.0
                    else:
                        target_mpg = min(pre_mpg, 18.0)
                        eff_prior_gp = 5.0
                        rookie_avail_gp = 52.0

                    scale_factor = (target_mpg * eff_prior_gp) / pre_min
                    entry = {col: float(row[col]) * scale_factor for col in AGG_COLS if col != 'GP'}
                    entry['GP'] = eff_prior_gp
                    entry['MIN'] = target_mpg * eff_prior_gp
                    entry['ROOKIE_AVAIL_GP'] = rookie_avail_gp
                    entry['IS_ROOKIE_PRIOR'] = True
                    blended_dict[pid] = entry

    return blended_dict


def get_positional_averages(prior_dict, pos_dict=None):
    """
    Calculates both league-wide per-minute averages and position-specific ('G', 'F', 'C')
    per-minute averages for Empirical Bayes shrinkage.
    """
    if pos_dict is None:
        pos_file = os.path.join(PROCESSED_DIR, 'player_positions.parquet')
        if os.path.exists(pos_file):
            df_pos = pd.read_parquet(pos_file)
            pos_dict = df_pos.set_index('PLAYER_ID')['POSITION'].to_dict()
        else:
            pos_dict = {}

    valid_items = [(pid, p) for pid, p in prior_dict.items() if p.get('MIN', 0) > 400]
    if not valid_items:
        return {}

    def _compute_rates(player_list):
        total_mins = sum(p['MIN'] for p in player_list)
        if total_mins <= 0:
            return {}
        rates = {}
        for k in AGG_COLS:
            if k == 'MIN':
                continue
            total_stat = sum(p.get(k, 0.0) for p in player_list)
            rates[k] = total_stat / total_mins
        return rates

    all_players = [p for _, p in valid_items]
    avg_dict = _compute_rates(all_players)

    by_pos = {}
    for pos_key in ('G', 'F', 'C'):
        bucket = [
            p for pid, p in valid_items
            if pos_key in str(pos_dict.get(pid, '')).upper()
        ]
        if len(bucket) >= 15:
            by_pos[pos_key] = _compute_rates(bucket)
        else:
            by_pos[pos_key] = dict(avg_dict)

    avg_dict['BY_POS'] = by_pos
    return avg_dict


def simulate_season(target_season="2025_26", prior_season="2024_25", track_players=None):
    print(f"\n--- Starting Bayesian Simulation for {target_season} ---")
    priors = load_prior_season(prior_season)
    pos_file = os.path.join(PROCESSED_DIR, 'player_positions.parquet')
    pos_dict = pd.read_parquet(pos_file).set_index('PLAYER_ID')['POSITION'].to_dict() if os.path.exists(pos_file) else {}
    pos_averages = get_positional_averages(priors, pos_dict=pos_dict)

    player_logs_path = os.path.join(DATA_DIR, 'raw', f'player_logs_{target_season}.parquet')
    trades_path = os.path.join(PROCESSED_DIR, f'trades_{target_season}.parquet')

    df_logs = pd.read_parquet(player_logs_path)
    df_trades = pd.read_parquet(trades_path) if os.path.exists(trades_path) else pd.DataFrame()

    df_logs['GAME_DATE'] = pd.to_datetime(df_logs['GAME_DATE'])
    if not df_trades.empty:
        df_trades['TRADE_DATE'] = pd.to_datetime(df_trades['TRADE_DATE'])

    players = {}
    unique_players = df_logs[['PLAYER_ID', 'PLAYER_NAME']].drop_duplicates()

    for _, row in unique_players.iterrows():
        pid = int(row['PLAYER_ID'])
        bp = BayesianPlayer(pid, row['PLAYER_NAME'])
        player_prior = priors.get(pid, None)
        bp.initialize_priors(player_prior, pos_averages, pos_str=pos_dict.get(pid, 'UTIL'))
        players[pid] = bp

    df_logs = df_logs.sort_values('GAME_DATE')
    dates = df_logs['GAME_DATE'].unique()

    trades_dict = {}
    if not df_trades.empty:
        for _, row in df_trades.iterrows():
            trades_dict[(int(row['PLAYER_ID']), row['TRADE_DATE'])] = True

    tracking_history = {pid: [] for pid in (track_players or [])}
    print(f"Simulating {len(dates)} days...")

    for current_date in dates:
        daily_games = df_logs[df_logs['GAME_DATE'] == current_date]

        for _, row in daily_games.iterrows():
            pid = int(row['PLAYER_ID'])
            minutes = float(row.get('MIN', 0.0))
            is_event = (pid, current_date) in trades_dict

            if pid in players:
                players[pid].update_stats(
                    game_date=current_date,
                    minutes=minutes,
                    stats_dict=row.to_dict(),
                    is_event_reset=is_event
                )

            if track_players and pid in track_players:
                preds = players[pid].predict_next_game()
                tracking_history[pid].append({
                    'date': current_date,
                    'is_event': is_event,
                    'pts_mean': preds.get('PTS', {}).get('mean', 0),
                    'pts_var': preds.get('PTS', {}).get('variance', 0),
                    'fg_rate': preds.get('FG', {}).get('rate', 0),
                    'fg_var': preds.get('FG', {}).get('variance', 0)
                })

    print("Simulation Complete!")
    return players, tracking_history

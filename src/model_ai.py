import math
import pandas as pd
import numpy as np
from datetime import timedelta
from bayesian_model import COUNT_STATS, PERCENTAGE_STATS
from matchup_engine import can_fill_roster_cached, norm_pdf


def get_bayesian_waiver_moves(
    team_roster_ids,
    waiver_pool_ids,
    bayesian_players,
    current_date,
    df_schedule,
    player_team_map,
    pos_dict=None,
    max_moves=2,
    target_minutes=None,
    season_engine=None,
    opp_roster_ids=None,
    week_end_date=None,
):
    """
    Bayesian Core-Protected Waiver / Streaming Engine (fixes Rapor 1 / K12 & Rapor 2 / L5):
      1. Computes reference Z-scores and replacement level (156th player) across the ENTIRE league
         player pool (bayesian_players), NOT just my_roster + scrub waivers!
      2. Protects the top 11 "Core" players on the roster by pure talent (unless a player has a
         season-ending/long-term injury with consecutive_dnps >= 15).
      3. Evaluates candidate (drop_id, add_id) swaps directly via MatchupEngine H2H win probability
         gain Delta Phi against the upcoming week's opponent + remaining season value!
    """
    if not team_roster_ids or not waiver_pool_ids:
        return []

    # 1. Build full-league DataFrame so Z-scores & 156th-player replacement level are unbiased (fixes K12)
    all_league_ids = list(bayesian_players.keys())
    if not all_league_ids:
        return []

    cur_ts = pd.to_datetime(current_date).normalize()
    next_ts = pd.to_datetime(week_end_date).normalize() + timedelta(days=1) if week_end_date is not None else cur_ts + timedelta(days=7)

    rows = []
    for pid in all_league_ids:
        bp = bayesian_players[pid]
        consec_dnps = getattr(bp, 'consecutive_dnps', 0)
        eff_avail = bp.get_effective_game_availability()
        eff_cur_ts = cur_ts
        if eff_cur_ts is not None and getattr(bp, 'last_game_date', None) is not None:
            if (eff_cur_ts - pd.to_datetime(bp.last_game_date).normalize()).days > 14:
                eff_cur_ts = None
        preds = bp.predict_next_game(projected_minutes=target_minutes, current_date=eff_cur_ts)
        row = {
            'PLAYER_ID': pid,
            'CONSEC_DNPS': consec_dnps,
            'EFF_AVAIL': eff_avail,
            'BASE_AVAIL': getattr(bp, 'availability_rate', 0.85),
        }
        for stat in COUNT_STATS:
            row[stat] = preds.get(stat, {}).get('mean', 0.0)
        for stat in PERCENTAGE_STATS:
            rate = preds.get(stat, {}).get('rate', 0.0)
            makes = preds.get(stat, {}).get('mean', 0.0)
            att = preds.get(stat, {}).get('attempts', 10.0)
            row[f'{stat}_rate'] = rate
            row[f'{stat}M'] = makes
            row[f'{stat}A'] = att
        rows.append(row)

    df_all = pd.DataFrame(rows).set_index('PLAYER_ID')

    # Preliminary ranking to find the top 156 league-wide reference population
    prelim = pd.Series(0.0, index=df_all.index)
    for stat in COUNT_STATS:
        s_std = df_all[stat].std()
        z_s = (df_all[stat] - df_all[stat].mean()) / (s_std if s_std and s_std > 0 else 1.0)
        prelim += (-z_s if stat == 'TOV' else z_s)

    ref_df = df_all.loc[prelim.sort_values(ascending=False).head(min(156, len(df_all))).index]

    league_fg = ref_df['FGM'].sum() / ref_df['FGA'].sum() if ref_df['FGA'].sum() > 0 else 0.47
    league_ft = ref_df['FTM'].sum() / ref_df['FTA'].sum() if ref_df['FTA'].sum() > 0 else 0.78
    df_all['FG_Impact'] = (df_all['FG_rate'] - league_fg) * df_all['FGA']
    df_all['FT_Impact'] = (df_all['FT_rate'] - league_ft) * df_all['FTA']
    ref_df = df_all.loc[ref_df.index]

    cat_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG3M', 'TOV', 'FG_Impact', 'FT_Impact']
    for cat in cat_cols:
        mean = ref_df[cat].mean()
        std = ref_df[cat].std()
        z = (df_all[cat] - mean) / std if std and std > 0 else 0.0
        if cat == 'TOV':
            z = -z
        df_all[f'Z_{cat}'] = z

    z_cols = [f'Z_{c}' for c in cat_cols]
    # Pure talent score relative to the top-156 league reference pool
    # Long-term/season-ending injuries (consecutive_dnps >= 15) reduce effective talent so dead roster spots can be replaced
    long_term_injury_mult = np.where(df_all['CONSEC_DNPS'] >= 15, 0.15, 1.0)
    df_all['Base_Total_Z'] = df_all[z_cols].sum(axis=1) * long_term_injury_mult

    # 2. Upcoming schedule game count
    if df_schedule is not None and not df_schedule.empty:
        sched_dates = pd.to_datetime(df_schedule['GAME_DATE']).dt.normalize()
        df_up = df_schedule[(sched_dates >= cur_ts) & (sched_dates < next_ts)]
        team_gp = df_up.drop_duplicates(subset=['TEAM_ID', 'GAME_ID']).groupby('TEAM_ID').size().to_dict()
    else:
        team_gp = {}

    upcoming_gp = []
    for pid in df_all.index:
        tid = player_team_map.get(pid)
        gp_val = float(team_gp.get(tid, 0.0)) if (tid is not None and team_gp) else 3.42
        upcoming_gp.append(gp_val * df_all.loc[pid, 'EFF_AVAIL'])
    df_all['UPCOMING_GP'] = upcoming_gp

    # 3. Compute marginal category weights from MatchupEngine against upcoming opponent if available
    valid_team_ids = [pid for pid in team_roster_ids if pid in df_all.index]
    if season_engine is not None and opp_roster_ids is not None:
        w_end = next_ts - timedelta(days=1)
        my_dist = season_engine.get_expected_weekly_distribution(valid_team_ids, cur_ts, w_end)
        opp_dist = season_engine.get_expected_weekly_distribution(opp_roster_ids, cur_ts, w_end)
        base_exp_wins, win_probs_w, _ = season_engine.evaluate_h2h_matchup(my_dist, opp_dist)
        weights = {
            f'Z_{s}': max(0.15, 4.0 * win_probs_w.get(s, 0.5) * (1.0 - win_probs_w.get(s, 0.5)))
            for s in COUNT_STATS
        }
        p_fg = win_probs_w.get('FG_PCT', 0.5)
        p_ft = win_probs_w.get('FT_PCT', 0.5)
        weights['Z_FG_Impact'] = max(0.15, 4.0 * p_fg * (1.0 - p_fg))
        weights['Z_FT_Impact'] = max(0.15, 4.0 * p_ft * (1.0 - p_ft))
        # Normalize weights so average weight is 1.0
        w_mean = np.mean(list(weights.values())) or 1.0
        weights = {k: v / w_mean for k, v in weights.items()}
    else:
        team_df = df_all.loc[valid_team_ids]
        full_diff_sd = math.sqrt(2.0 * 13.0)
        phi_zero = norm_pdf(0.0)
        weights = {}
        for z_col in z_cols:
            if not team_df.empty:
                team_z_norm = team_df[z_col].sum() / full_diff_sd
                weights[z_col] = 0.15 + 0.85 * (norm_pdf(team_z_norm) / phi_zero)
            else:
                weights[z_col] = 1.0

    df_all['Weighted_Z'] = 0.0
    for z_col in z_cols:
        df_all['Weighted_Z'] += df_all[z_col] * weights[z_col]

    # True league replacement level (156th player across ALL players in the league)
    sorted_wz = df_all['Weighted_Z'].sort_values(ascending=False)
    rep_idx = min(155, len(sorted_wz) - 1)
    replacement_wz = float(sorted_wz.iloc[rep_idx]) if len(sorted_wz) > 0 else 0.0

    avg_weekly_gp = 3.42
    # Blend short-term weekly streaming VORP (70%) + rest-of-season talent VORP (30%) (fixes Rapor 2 / L5)
    weekly_vorp = (df_all['Weighted_Z'] - replacement_wz) * (df_all['UPCOMING_GP'] / avg_weekly_gp)
    ros_vorp = (df_all['Base_Total_Z'] - float(df_all['Base_Total_Z'].sort_values(ascending=False).iloc[rep_idx])) * df_all['BASE_AVAIL']
    df_all['Total_Z'] = 0.70 * weekly_vorp + 0.30 * ros_vorp

    # 4. Core Player Protection: Protect top 11 players by Base_Total_Z, only stream bottom 2
    team_stats = df_all.loc[valid_team_ids].sort_values('Base_Total_Z', ascending=True)
    droppable_count = max(1, len(team_roster_ids) - 11)
    droppable_team_stats = team_stats.head(droppable_count).sort_values('Total_Z', ascending=True)

    valid_waiver_ids = [
        pid for pid in waiver_pool_ids
        if pid in df_all.index and df_all.loc[pid, 'CONSEC_DNPS'] < 2 and df_all.loc[pid, 'UPCOMING_GP'] > 0
    ]
    waiver_stats = df_all.loc[valid_waiver_ids].sort_values('Total_Z', ascending=False).head(25)

    moves = []
    simulated_roster = list(team_roster_ids)
    used_waiver_ids = set()

    for drop_id in droppable_team_stats.index:
        if len(moves) >= max_moves:
            break
        worst_z = float(droppable_team_stats.loc[drop_id, 'Total_Z'])

        for add_id in waiver_stats.index:
            if add_id in used_waiver_ids:
                continue
            best_z = float(waiver_stats.loc[add_id, 'Total_Z'])
            if best_z <= worst_z + 0.35:
                break

            candidate_roster = [add_id if p == drop_id else p for p in simulated_roster]
            if pos_dict is not None:
                pos_tuple = tuple(sorted(pos_dict.get(p, 'UTIL') for p in candidate_roster))
                if not can_fill_roster_cached(pos_tuple):
                    continue

            # If MatchupEngine is provided, verify the swap actually improves expected H2H category wins!
            if season_engine is not None and opp_roster_ids is not None:
                w_end = next_ts - timedelta(days=1)
                cand_dist = season_engine.get_expected_weekly_distribution(candidate_roster, cur_ts, w_end)
                cand_exp_wins, _, _ = season_engine.evaluate_h2h_matchup(cand_dist, opp_dist)
                if cand_exp_wins <= base_exp_wins + 0.015:
                    continue
                base_exp_wins = cand_exp_wins

            simulated_roster = candidate_roster
            used_waiver_ids.add(add_id)
            moves.append((drop_id, add_id, worst_z, best_z))
            break

    return moves

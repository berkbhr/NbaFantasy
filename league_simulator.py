import os
import sys
import math
sys.stdout.reconfigure(encoding='utf-8')
import time
from collections import deque
import pandas as pd
import numpy as np
from scipy.optimize import linear_sum_assignment

# Add src to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
sys.path.append(os.path.join(PROJECT_ROOT, 'src'))

from bayesian_model import BayesianPlayer, COUNT_STATS, PERCENTAGE_STATS
from live_draft_assistant import LiveDraftAssistant
from simulator import load_prior_season, get_positional_averages
from matchup_engine import (
    MatchupEngine,
    can_fill_roster_cached,
    get_optimal_daily_lineup,
    REQUIRED_SLOTS,
    INFEASIBLE_COST,
    _slot_eligibility_mask,
    norm_pdf,
)
from model_ai import get_bayesian_waiver_moves


def calculate_z_scores(df):
    df = df[df['MIN'] >= 500.0].copy()
    if 'GP' not in df.columns:
        df['GP'] = 1
    df['GP'] = df['GP'].replace(0, 1)

    league_fg = df['FGM'].sum() / df['FGA'].sum() if df['FGA'].sum() > 0 else 0.47
    league_ft = df['FTM'].sum() / df['FTA'].sum() if df['FTA'].sum() > 0 else 0.78

    stats_to_avg = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG3M', 'TOV', 'FGM', 'FGA', 'FTM', 'FTA', 'MIN']
    for col in stats_to_avg:
        if col in df.columns:
            df[col] = df[col] / df['GP']

    cats = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG3M', 'TOV']

    df['FG_PCT'] = df['FGM'] / df['FGA'].replace(0, 1)
    df['FT_PCT'] = df['FTM'] / df['FTA'].replace(0, 1)

    df['FG_Impact'] = df['FGA'] * (df['FG_PCT'] - league_fg)
    df['FT_Impact'] = df['FTA'] * (df['FT_PCT'] - league_ft)
    all_cats = cats + ['FG_Impact', 'FT_Impact']

    prelim_z = pd.Series(0.0, index=df.index)
    for cat in all_cats:
        if cat in df.columns:
            c_std = df[cat].std()
            z_c = (df[cat] - df[cat].mean()) / (c_std if c_std and c_std > 0 else 1.0)
            prelim_z += (-z_c if cat == 'TOV' else z_c)

    ref_df = df.loc[prelim_z.sort_values(ascending=False).head(min(156, len(df))).index]

    for cat in all_cats:
        if cat in df.columns:
            mean = ref_df[cat].mean()
            std = ref_df[cat].std()
            df[f'Z_{cat}'] = (df[cat] - mean) / std if std and std > 0 else 0.0
            if cat == 'TOV':
                df[f'Z_{cat}'] = -df[f'Z_{cat}']
    df['Total_Z'] = df[[f'Z_{cat}' for cat in all_cats]].sum(axis=1)
    return df.sort_values('Total_Z', ascending=False)


class BaseBot:
    def __init__(self, name, team_id, df_priors, pos_dict=None, name_dict=None):
        self.pos_dict = pos_dict or {}
        self.name_dict = name_dict or {}
        self.name = name
        self.team_id = team_id
        self.roster = []
        self.df_priors = df_priors.copy()

    def get_pick(self, available_ids, current_round):
        raise NotImplementedError


class DumbBot(BaseBot):
    def __init__(self, name, team_id, df_priors, pos_dict=None, name_dict=None):
        super().__init__(name, team_id, df_priors, pos_dict=pos_dict, name_dict=name_dict)
        if 'BASE_Z' not in self.df_priors.columns:
            self.df_priors['BASE_Z'] = self.df_priors['Total_Z']
        self.df_priors = self.df_priors.sort_values('BASE_Z', ascending=False)

    def get_pick(self, available_ids, current_round):
        for pid in self.df_priors.index:
            if pid in available_ids:
                if self.pos_dict:
                    test_roster = self.roster + [pid]
                    pos_tuple = tuple(sorted(self.pos_dict.get(p, "UTIL") for p in test_roster))
                    if not can_fill_roster_cached(pos_tuple):
                        continue
                return pid
        return sorted(available_ids)[0]


class AverageBot(BaseBot):
    def __init__(self, name, team_id, df_priors, pos_dict=None, name_dict=None):
        super().__init__(name, team_id, df_priors, pos_dict=pos_dict, name_dict=name_dict)
        self.df_priors['RAW_TOTAL'] = self.df_priors[['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG3M']].sum(axis=1)
        self.df_priors = self.df_priors.sort_values('RAW_TOTAL', ascending=False)

    def get_pick(self, available_ids, current_round):
        for pid in self.df_priors.index:
            if pid in available_ids:
                if self.pos_dict:
                    test_roster = self.roster + [pid]
                    pos_tuple = tuple(sorted(self.pos_dict.get(p, "UTIL") for p in test_roster))
                    if not can_fill_roster_cached(pos_tuple):
                        continue
                return pid
        return sorted(available_ids)[0]


class SmartBot(BaseBot):
    def __init__(self, name, team_id, df_priors, pos_dict=None, name_dict=None):
        super().__init__(name, team_id, df_priors, pos_dict=pos_dict, name_dict=name_dict)
        print(f"[{self.name}] Initializing LiveDraftAssistant (Pairwise H2H Rollout + Calibrated Phi)...")
        self.assistant = LiveDraftAssistant(
            prior_season="2024_25",
            my_team_idx=team_id,
            pool_ids=set(df_priors.index.tolist()),
        )
        self.mcts_history = []

    def get_pick(self, available_ids, current_round):
        print(f"\n[{self.name}] Analyzing board for Round {current_round}...")
        df_sug = self.assistant.rank_available_players(enable_logging=True)

        for best_pid in df_sug['ID']:
            if best_pid in available_ids:
                self.mcts_history.append({
                    'Round': current_round,
                    'Selected_ID': best_pid,
                    'df_sug': df_sug.copy()
                })
                return best_pid
        return sorted(available_ids)[0]

    def notify_pick(self, pid, is_mine, picker_team_id=None):
        if is_mine:
            self.assistant.draft_player(pid, team_idx=picker_team_id)
        else:
            self.assistant.pick_player(pid, team_idx=picker_team_id)


def run_draft(bots, df_priors):
    print("\n=== STARTING 12-TEAM SNAKE DRAFT ===")
    available_ids = set(df_priors.index.tolist())
    draft_log = []

    pick_number = 1
    for round_num in range(1, 14):
        team_order = range(12) if round_num % 2 != 0 else reversed(range(12))

        for turn_idx in team_order:
            bot = bots[turn_idx]

            start_time = time.time()
            pid = bot.get_pick(available_ids, round_num)
            elapsed = time.time() - start_time

            player_name = bot.name_dict.get(pid, str(pid))
            print(f"Pick {pick_number} (R{round_num}): {bot.name} selects {player_name} ({elapsed:.1f}s)")

            bot.roster.append(pid)
            available_ids.remove(pid)

            draft_log.append({
                'Pick': pick_number,
                'Round': round_num,
                'Team': bot.name,
                'Player_ID': pid,
                'Player_Name': player_name
            })

            for b in bots:
                if isinstance(b, SmartBot):
                    b.notify_pick(pid, is_mine=(b.team_id == bot.team_id), picker_team_id=bot.team_id)

            pick_number += 1

    return pd.DataFrame(draft_log)


def get_optimal_daily_lineup_basic(roster_ids, eligible_today_ids, pos_dict, priority_dict):
    available_players = []
    for pid in roster_ids:
        if pid in eligible_today_ids:
            score = float(priority_dict.get(pid, 0.0))
            pos = pos_dict.get(pid, 'UTIL')
            available_players.append({
                'ID': pid,
                'POS': pos,
                'SCORE': score
            })
    if not available_players:
        return []

    n_players = len(available_players)
    n_slots = len(REQUIRED_SLOTS)
    cost_matrix = np.full((n_players, n_slots), INFEASIBLE_COST, dtype=np.float64)

    for i, p in enumerate(available_players):
        mask = _slot_eligibility_mask(p['POS'])
        shifted_score = p['SCORE'] + 1e4
        for j, is_ok in enumerate(mask):
            if is_ok:
                cost_matrix[i, j] = -shifted_score

    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    return [
        available_players[r]['ID']
        for r, c in zip(row_ind, col_ind)
        if cost_matrix[r, c] < INFEASIBLE_COST / 2.0
    ]


def get_smart_daily_lineup(
    roster_ids, eligible_today_ids, pos_dict, bayesian_players, category_weights, current_date=None, p_ref_fg=0.47, p_ref_ft=0.78
):
    available_players = []
    for pid in roster_ids:
        if pid in eligible_today_ids and pid in bayesian_players:
            preds = bayesian_players[pid].predict_next_game(projected_minutes=None, current_date=current_date)
            proj = {stat: preds.get(stat, {}).get('mean', 0.0) for stat in COUNT_STATS}
            proj['FGM'] = preds.get('FG', {}).get('mean', 0.0)
            proj['FGA'] = preds.get('FG', {}).get('attempts', 10.0)
            proj['FTM'] = preds.get('FT', {}).get('mean', 0.0)
            proj['FTA'] = preds.get('FT', {}).get('attempts', 10.0)
            available_players.append({
                'ID': pid,
                'POS': pos_dict.get(pid, 'UTIL'),
                'PROJ': proj
            })
    if not available_players:
        return []

    best_lineup = get_optimal_daily_lineup(available_players, category_weights, p_ref_fg=p_ref_fg, p_ref_ft=p_ref_ft)
    return [p['ID'] for p in best_lineup]


def _compute_dynamic_daily_weights(season_engine, my_roster, opp_roster, my_acc_stats, opp_acc_stats, cur_date, end_date):
    """
    Computes dynamic intra-week marginal category weights phi(z_c) combining:
      - Accumulated weekly stats already banked by both teams so far this week
      - Remaining expected weekly stats & variances from cur_date to end_date (fixes Rapor 2 / §5)
    """
    my_rem = season_engine.get_expected_weekly_distribution(my_roster, cur_date, end_date)
    opp_rem = season_engine.get_expected_weekly_distribution(opp_roster, cur_date, end_date)

    for cat in my_rem['mean']:
        my_rem['mean'][cat] += my_acc_stats.get(cat, 0.0)
        opp_rem['mean'][cat] += opp_acc_stats.get(cat, 0.0)

    _, _, marginal_w = season_engine.evaluate_h2h_matchup(my_rem, opp_rem)

    tot_fga = my_rem['mean']['FGA'] + opp_rem['mean']['FGA']
    tot_fta = my_rem['mean']['FTA'] + opp_rem['mean']['FTA']
    p_ref_fg = (my_rem['mean']['FGM'] + opp_rem['mean']['FGM']) / tot_fga if tot_fga > 0 else 0.47
    p_ref_ft = (my_rem['mean']['FTM'] + opp_rem['mean']['FTM']) / tot_fta if tot_fta > 0 else 0.78
    return marginal_w, p_ref_fg, p_ref_ft


def run_season(bots, df_priors, priors_raw):
    print("\n=== STARTING 2025-26 H2H SEASON SIMULATION (CALIBRATED BAYESIAN + DYNAMIC WEIGHTS + WAIVERS) ===")

    df_sched = pd.read_parquet(os.path.join(DATA_DIR, 'processed', 'schedule_2025_26.parquet'))
    df_logs = pd.read_parquet(os.path.join(DATA_DIR, 'raw', 'player_logs_2025_26.parquet'))
    trades_path = os.path.join(DATA_DIR, 'processed', 'trades_2025_26.parquet')
    df_trades = pd.read_parquet(trades_path) if os.path.exists(trades_path) else pd.DataFrame()

    df_sched['GAME_DATE'] = pd.to_datetime(df_sched['GAME_DATE']).dt.normalize()
    df_logs['GAME_DATE'] = pd.to_datetime(df_logs['GAME_DATE']).dt.normalize()
    if not df_trades.empty:
        df_trades['TRADE_DATE'] = pd.to_datetime(df_trades['TRADE_DATE']).dt.normalize()

    pos_file = os.path.join(DATA_DIR, 'processed', 'player_positions_2025_26.parquet')
    if not os.path.exists(pos_file):
        pos_file = os.path.join(DATA_DIR, 'processed', 'player_positions.parquet')
    df_pos = pd.read_parquet(pos_file)
    pos_dict = df_pos.set_index('PLAYER_ID')['POSITION'].to_dict()

    pos_averages = get_positional_averages(priors_raw, pos_dict=pos_dict)
    bayesian_players = {}

    # Initialize all players from 2024-25 priors first (no look-ahead into mid-season 2025-26 call-ups, fixes Rapor 2 / L7)
    for pid, p_data in priors_raw.items():
        pid = int(pid)
        bp = BayesianPlayer(pid, str(pid))
        bp.initialize_priors(p_data, pos_averages, pos_str=pos_dict.get(pid, 'UTIL'))
        bayesian_players[pid] = bp

    unique_players = df_logs[['PLAYER_ID', 'PLAYER_NAME']].drop_duplicates()
    for _, row in unique_players.iterrows():
        pid = int(row['PLAYER_ID'])
        name = row['PLAYER_NAME']
        if pid in bayesian_players:
            bayesian_players[pid].name = name
        else:
            bp = BayesianPlayer(pid, name)
            bp.initialize_priors(priors_raw.get(pid, None), pos_averages, pos_str=pos_dict.get(pid, 'UTIL'))
            bayesian_players[pid] = bp

    trades_set = set()
    if not df_trades.empty:
        for _, row in df_trades.iterrows():
            trades_set.add((int(row['PLAYER_ID']), row['TRADE_DATE']))

    season_engine = MatchupEngine(bayesian_players, df_sched, df_pos, season="2025_26", prior_season="2024_25")
    player_team_map = dict(season_engine.team_map)

    all_dates = sorted(df_sched['GAME_DATE'].unique())
    weeks = [all_dates[i:i + 7] for i in range(0, len(all_dates), 7) if len(all_dates[i:i + 7]) == 7]

    bot_priorities = {}
    for bot in bots:
        if isinstance(bot, AverageBot):
            bot_priorities[bot.name] = bot.df_priors['RAW_TOTAL'].to_dict()
        else:
            bot_priorities[bot.name] = df_priors['BASE_Z'].to_dict()

    # Track both Matchup W-L-T (Most Categories) and Category W-L-T (Each Category 9-Cat) (fixes Rapor 2 / L1)
    standings = {
        bot.name: {'W': 0, 'L': 0, 'T': 0, 'Cat_W': 0, 'Cat_L': 0, 'Cat_T': 0}
        for bot in bots
    }
    team_season_stats = {bot.name: {cat: 0.0 for cat in COUNT_STATS + PERCENTAGE_STATS} for bot in bots}

    bot_by_name = {b.name: b for b in bots}
    bot_names = [b.name for b in bots]
    rotation = deque(bot_names[1:])
    weekly_results = []

    num_weeks = min(22, len(weeks))

    for week_idx, week_dates in enumerate(weeks[:num_weeks]):
        print(f"\n--- Week {week_idx + 1} ({week_dates[0].strftime('%Y-%m-%d')} to {week_dates[-1].strftime('%Y-%m-%d')}) ---")

        matchups = [(bot_names[0], rotation[0])]
        for i in range(5):
            matchups.append((rotation[i + 1], rotation[10 - i]))
        rotation.rotate(1)

        opponent_map = {}
        for t1, t2 in matchups:
            opponent_map[t1] = t2
            opponent_map[t2] = t1

        team_weekly_stats = {bot.name: {cat: 0.0 for cat in COUNT_STATS + ['FGM', 'FGA', 'FTM', 'FTA']} for bot in bots}

        for date in week_dates:
            daily_df = df_logs[df_logs['GAME_DATE'] == date]
            daily_logs = daily_df.set_index('PLAYER_ID')
            teams_playing_today = set(df_sched.loc[df_sched['GAME_DATE'] == date, 'TEAM_ID'].tolist())

            eligible_today_ids = {
                pid
                for pid, tid in player_team_map.items()
                if tid in teams_playing_today
                and getattr(bayesian_players.get(pid), 'consecutive_dnps', 0) < 2
            }

            # 1. Prematch Lineup Optimization (Dynamic Intra-Week Weights for SmartBot)
            for bot in bots:
                if isinstance(bot, SmartBot):
                    opp_bot = bot_by_name[opponent_map[bot.name]]
                    w_dict, p_fg, p_ft = _compute_dynamic_daily_weights(
                        season_engine,
                        bot.roster,
                        opp_bot.roster,
                        team_weekly_stats[bot.name],
                        team_weekly_stats[opp_bot.name],
                        date,
                        week_dates[-1],
                    )
                    active_lineup = get_smart_daily_lineup(
                        bot.roster,
                        eligible_today_ids,
                        pos_dict,
                        bayesian_players,
                        w_dict,
                        current_date=date,
                        p_ref_fg=p_fg,
                        p_ref_ft=p_ft,
                    )
                else:
                    priority_dict = bot_priorities[bot.name]
                    active_lineup = get_optimal_daily_lineup_basic(bot.roster, eligible_today_ids, pos_dict, priority_dict)

                for pid in active_lineup:
                    if pid in daily_logs.index:
                        log = daily_logs.loc[pid]
                        if isinstance(log, pd.DataFrame):
                            log = log.iloc[0]
                        for cat in COUNT_STATS + ['FGM', 'FGA', 'FTM', 'FTA']:
                            team_weekly_stats[bot.name][cat] += float(log.get(cat, 0.0))

            # 2. End-of-Day Bayesian Posterior & Beta-Bernoulli Availability Updates
            played_today_pids = set(daily_df[daily_df['MIN'] > 0]['PLAYER_ID'].astype(int).tolist())
            for pid, tid in list(player_team_map.items()):
                if tid in teams_playing_today and pid in bayesian_players:
                    bayesian_players[pid].record_team_game_availability(played=(pid in played_today_pids))

            for _, row in daily_df.iterrows():
                pid = int(row['PLAYER_ID'])
                tid = int(row['TEAM_ID'])
                player_team_map[pid] = tid
                season_engine.team_map[pid] = tid

                if pid in bayesian_players:
                    is_trade = (pid, date) in trades_set
                    bayesian_players[pid].update_stats(
                        game_date=date,
                        minutes=float(row.get('MIN', 0.0)),
                        stats_dict=row.to_dict(),
                        is_event_reset=is_trade,
                    )

        # 3. Evaluate Weekly H2H Matchups
        for t1, t2 in matchups:
            stats1 = team_weekly_stats[t1]
            stats2 = team_weekly_stats[t2]

            w1, w2, ties = 0, 0, 0
            for cat in COUNT_STATS:
                val1, val2 = stats1[cat], stats2[cat]
                if cat == 'TOV':
                    if val1 < val2:
                        w1 += 1
                    elif val2 < val1:
                        w2 += 1
                    else:
                        ties += 1
                else:
                    if val1 > val2:
                        w1 += 1
                    elif val2 > val1:
                        w2 += 1
                    else:
                        ties += 1

            fg1 = stats1['FGM'] / stats1['FGA'] if stats1['FGA'] > 0 else 0.0
            fg2 = stats2['FGM'] / stats2['FGA'] if stats2['FGA'] > 0 else 0.0
            if fg1 > fg2:
                w1 += 1
            elif fg2 > fg1:
                w2 += 1
            else:
                ties += 1

            ft1 = stats1['FTM'] / stats1['FTA'] if stats1['FTA'] > 0 else 0.0
            ft2 = stats2['FTM'] / stats2['FTA'] if stats2['FTA'] > 0 else 0.0
            if ft1 > ft2:
                w1 += 1
            elif ft2 > ft1:
                w2 += 1
            else:
                ties += 1

            print(f"{t1} ({w1}) - ({w2}) {t2}")
            weekly_results.append({
                'Week': week_idx + 1,
                'Team1': t1, 'Team1_Score': w1,
                'Team2': t2, 'Team2_Score': w2
            })

            standings[t1]['Cat_W'] += w1
            standings[t1]['Cat_L'] += w2
            standings[t1]['Cat_T'] += ties
            standings[t2]['Cat_W'] += w2
            standings[t2]['Cat_L'] += w1
            standings[t2]['Cat_T'] += ties

            if w1 > w2:
                standings[t1]['W'] += 1
                standings[t2]['L'] += 1
            elif w2 > w1:
                standings[t2]['W'] += 1
                standings[t1]['L'] += 1
            else:
                standings[t1]['T'] += 1
                standings[t2]['T'] += 1

        # 4. Accumulate Season Totals
        for b_name in bot_names:
            s = team_weekly_stats[b_name]
            for cat in COUNT_STATS:
                team_season_stats[b_name][cat] += s[cat]
            for sc in ['FGM', 'FGA', 'FTM', 'FTA']:
                team_season_stats[b_name][sc] = team_season_stats[b_name].get(sc, 0.0) + s[sc]

        # 5. Weekly Waiver / Streaming Moves (MatchupEngine Delta-Phi verified)
        if week_idx + 1 < num_weeks:
            rostered_all = {pid for b in bots for pid in b.roster}
            waiver_pool_ids = [pid for pid in bayesian_players.keys() if pid not in rostered_all]
            next_week_dates = weeks[week_idx + 1]

            # Determine next week's matchups so waiver engine targets next week's opponent
            next_matchups = [(bot_names[0], rotation[0])]
            for i in range(5):
                next_matchups.append((rotation[i + 1], rotation[10 - i]))
            next_opp_map = {}
            for t1, t2 in next_matchups:
                next_opp_map[t1] = t2
                next_opp_map[t2] = t1

            for bot in bots:
                if isinstance(bot, SmartBot):
                    next_opp_bot = bot_by_name[next_opp_map[bot.name]]
                    moves = get_bayesian_waiver_moves(
                        team_roster_ids=bot.roster,
                        waiver_pool_ids=waiver_pool_ids,
                        bayesian_players=bayesian_players,
                        current_date=next_week_dates[0],
                        df_schedule=df_sched,
                        player_team_map=player_team_map,
                        pos_dict=pos_dict,
                        max_moves=2,
                        season_engine=season_engine,
                        opp_roster_ids=next_opp_bot.roster,
                        week_end_date=next_week_dates[-1],
                    )
                    for drop_id, add_id, drop_z, add_z in moves:
                        if drop_id in bot.roster and add_id in waiver_pool_ids:
                            bot.roster.remove(drop_id)
                            bot.roster.append(add_id)
                            waiver_pool_ids.remove(add_id)
                            waiver_pool_ids.append(drop_id)
                            d_name = bayesian_players[drop_id].name if drop_id in bayesian_players else str(drop_id)
                            a_name = bayesian_players[add_id].name if add_id in bayesian_players else str(add_id)
                            print(f"  [Waiver - {bot.name}] Dropped {d_name} ({drop_z:.2f}) -> Added {a_name} ({add_z:.2f})")

    for b_name in bot_names:
        stats = team_season_stats[b_name]
        stats['FG'] = stats['FGM'] / stats['FGA'] if stats.get('FGA', 0) > 0 else 0.0
        stats['FT'] = stats['FTM'] / stats['FTA'] if stats.get('FTA', 0) > 0 else 0.0

    df_standings = pd.DataFrame(standings).T
    total_games = df_standings['W'] + df_standings['L'] + df_standings['T']
    df_standings['Win_Pct'] = (df_standings['W'] + 0.5 * df_standings['T']) / total_games.replace(0, 1)
    total_cats = df_standings['Cat_W'] + df_standings['Cat_L'] + df_standings['Cat_T']
    df_standings['Cat_Win_Pct'] = (df_standings['Cat_W'] + 0.5 * df_standings['Cat_T']) / total_cats.replace(0, 1)
    df_standings = df_standings.sort_values('Cat_Win_Pct', ascending=False)

    print("\n=== FINAL STANDINGS (BOTH MATCHUP & EACH-CATEGORY 9-CAT) ===")
    print(df_standings)

    return df_standings, team_season_stats


if __name__ == "__main__":
    print("Loading 2024_25 Priors for Draft...")
    priors = load_prior_season("2024_25")
    df_priors = pd.DataFrame.from_dict(priors, orient='index')

    df_priors = calculate_z_scores(df_priors)
    df_priors['BASE_Z'] = df_priors['Total_Z']

    pos_file = os.path.join(DATA_DIR, 'processed', 'player_positions.parquet')
    df_pos = pd.read_parquet(pos_file) if os.path.exists(pos_file) else pd.DataFrame()
    pos_dict = df_pos.set_index('PLAYER_ID')['POSITION'].to_dict() if not df_pos.empty else {}
    name_dict = df_pos.set_index('PLAYER_ID')['PLAYER_NAME'].to_dict() if not df_pos.empty else {}

    # Place Smart_Bot_1 at Slot #8 (0-indexed: 7) to match the user's real Yahoo Draft slot
    bots = []
    bots.append(AverageBot("Average_Bot_1", 0, df_priors, pos_dict=pos_dict, name_dict=name_dict))
    for i in range(1, 7):
        bots.append(DumbBot(f"Dumb_Bot_{i}", i, df_priors, pos_dict=pos_dict, name_dict=name_dict))
    smart_bot = SmartBot("Smart_Bot_1", 7, df_priors, pos_dict=pos_dict, name_dict=name_dict)
    bots.append(smart_bot)
    for i in range(8, 12):
        bots.append(DumbBot(f"Dumb_Bot_{i-1}", i, df_priors, pos_dict=pos_dict, name_dict=name_dict))

    df_draft_log = run_draft(bots, df_priors)

    print("\nStarting season simulation...")
    df_standings, team_season_stats = run_season(bots, df_priors, priors)
    df_stats = pd.DataFrame(team_season_stats).T

    mcts_logs = []
    actual_picks = []
    for log in smart_bot.mcts_history:
        sel_id = log.get('Selected_ID')
        sel_name = name_dict.get(sel_id, log['df_sug'].iloc[0]['NAME'])
        actual_picks.append(sel_name)

    for idx, log in enumerate(smart_bot.mcts_history):
        r = log['Round']
        top_sug = log['df_sug'].iloc[0]
        sel_name = actual_picks[idx]

        pred_picks = [p for p in top_sug.get('Predicted_Picks', "").split(", ") if p]
        deviation_status = "Yok"
        if r < 13 and len(pred_picks) > 0:
            next_actual = actual_picks[idx + 1] if idx + 1 < len(actual_picks) else ""
            if next_actual != pred_picks[0]:
                deviation_status = f"Saptı (Plan: {pred_picks[0]}, Gerçek: {next_actual})"
            else:
                deviation_status = "Plana Uyuldu"

        mcts_logs.append({
            'Round': r,
            'Selected_Player': sel_name,
            'MCTS_Expected_Z': top_sug['Score'],
            'Active_Punts': top_sug.get('Active_Punts', ""),
            'Predicted_Future_Picks': top_sug.get('Predicted_Picks', ""),
            'Prediction_Accuracy': deviation_status
        })
    df_mcts = pd.DataFrame(mcts_logs)

    max_roster = max([len(b.roster) for b in bots])
    kadro_dict = {}
    for b in bots:
        names = [name_dict.get(pid, str(pid)) for pid in b.roster]
        while len(names) < max_roster:
            names.append("")
        kadro_dict[b.name] = names
    df_kadrolar = pd.DataFrame(kadro_dict)

    simulations_dir = os.path.join(PROJECT_ROOT, 'data', 'simulations', 'simulation_4')
    os.makedirs(simulations_dir, exist_ok=True)
    df_draft_log.to_csv(os.path.join(simulations_dir, 'draft_results.csv'), index=False)

    with pd.ExcelWriter(os.path.join(simulations_dir, 'season_results.xlsx'), engine='xlsxwriter') as writer:
        df_standings.to_excel(writer, sheet_name='Standings')
        df_stats.to_excel(writer, sheet_name='Team_Stats')
        df_draft_log.to_excel(writer, sheet_name='Draft_Board', index=False)
        df_mcts.to_excel(writer, sheet_name='Tahmin_Raporu', index=False)
        df_kadrolar.to_excel(writer, sheet_name='Kadro_Gorunumu', index=False)
    print(f"\nSimulation complete! Results saved to {simulations_dir}")

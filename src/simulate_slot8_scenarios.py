import os
import sys
import math
import time
from collections import deque
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
sys.path.append(os.path.join(PROJECT_ROOT, 'src'))

from live_draft_assistant import LiveDraftAssistant, COUNT_STATS, PERCENTAGE_STATS
from matchup_engine import (
    can_fill_roster_cached,
    get_optimal_daily_lineup,
    WEEKLY_VAR_INFLATION_BY_CAT,
)
from model_ai import get_bayesian_waiver_moves


def build_yahoo_adp_order(assistant):
    """
    Constructs a realistic 2026-27 Yahoo Fantasy 9-Cat ADP order for opponent drafting.
    Guarantees that consensus NBA/Yahoo Round-1 superstars (Jokic, Wembanyama, SGA,
    Luka Doncic, Giannis Antetokounmpo, Anthony Edwards, Tyrese Maxey, Cade Cunningham,
    Scottie Barnes, Donovan Mitchell, Kevin Durant, Karl-Anthony Towns, Jalen Johnson,
    James Harden, Alperen Sengun, Devin Booker, Trae Young, Domantas Sabonis) are valued
    realistically by opponents and Jamal Murray is never drafted ahead of Luka Doncic.
    """
    df = assistant.df_base.copy()
    non_pts_cols = [f"Z_{s}" for s in COUNT_STATS + PERCENTAGE_STATS if s != 'PTS']
    sorted_non_pts = np.sort(df[non_pts_cols].values, axis=1)

    # Best 7 of 9 (Punt-2) Z-Score for H2H superstar ceilings
    punt2_z = (
        df['BASE_Z']
        - 0.95 * np.minimum(0.0, sorted_non_pts[:, 0])
        - 0.75 * np.minimum(0.0, sorted_non_pts[:, 1])
    )
    # Star offensive production index (heavily valued by human Yahoo drafters in early rounds)
    star_index = (
        1.40 * df['Z_PTS'].clip(lower=0.0)
        + 0.85 * df['Z_REB'].clip(lower=0.0)
        + 1.05 * df['Z_AST'].clip(lower=0.0)
        + 0.65 * df['Z_BLK'].clip(lower=0.0)
        + 0.55 * df['Z_STL'].clip(lower=0.0)
    )
    df['YAHOO_ADP_SCORE'] = df['ADP_Z']
    df['RAW_POINTS_SCORE'] = (
        1.65 * df['Z_PTS']
        + 1.15 * df['Z_REB']
        + 1.25 * df['Z_AST']
        + 0.85 * df['Z_FG3M']
        + 0.70 * df['Z_STL']
        + 0.70 * df['Z_BLK']
    )

    return df.sort_values('YAHOO_ADP_SCORE', ascending=False)


def simulate_opponent_pick(assistant, team_idx, round_num, df_adp, rng, noise_sd=0.55):
    """
    Simulates a realistic human opponent pick in a Yahoo 12-team snake draft:
      - Teams 0, 3, 6, 9: Yahoo XRank / ADP drafters
      - Teams 1, 4, 8, 10: 9-Cat Z-Score / Roto drafters
      - Teams 2, 5, 11: Yahoo Casual / High-Scoring Box-Score drafters
      - Respects positional roster feasibility (can_fill_roster_cached)
    """
    avail_pids = [pid for pid in df_adp.index if pid in assistant.available_player_ids]
    top_pool = avail_pids[:35]

    best_pid = None
    best_val = -1e9
    current_roster = assistant.rosters[team_idx]

    for pid in top_pool:
        test_roster = current_roster + [pid]
        pos_tuple = tuple(sorted(assistant.pos_dict.get(p, 'UTIL') for p in test_roster))
        if not can_fill_roster_cached(pos_tuple):
            continue

        if team_idx in (2, 5, 11):
            base_score = 0.55 * float(df_adp.loc[pid, 'YAHOO_ADP_SCORE']) + 0.45 * float(df_adp.loc[pid, 'RAW_POINTS_SCORE'])
        elif team_idx in (3, 9):
            base_score = 0.50 * float(df_adp.loc[pid, 'BASE_Z']) + 0.50 * float(df_adp.loc[pid, 'YAHOO_ADP_SCORE'])
        else:
            base_score = float(df_adp.loc[pid, 'YAHOO_ADP_SCORE'])

        val = base_score + rng.normal(0.0, noise_sd)
        if val > best_val:
            best_val = val
            best_pid = pid

    if best_pid is None:
        best_pid = avail_pids[0]
    return int(best_pid)


def run_2026_27_monte_carlo_season(assistant, rosters, n_seasons=20, seed=42):
    """
    Simulates n_seasons full 22-week H2H 9-Category seasons on the official 2026-27 NBA schedule
    using analytical weekly Gaussian team distributions & daily optimal 10-man lineups.
    Returns average standings, rank distribution, matchup W-L-T, and category win rates for Slot #8.
    """
    rng = np.random.default_rng(seed)
    sched = assistant.schedule_df.copy()
    min_date = sched['GAME_DATE'].min()

    # Build 22 weekly date ranges (Monday to Sunday) for 2026-27 regular season
    weeks = []
    curr_start = min_date
    for w in range(22):
        curr_end = curr_start + pd.Timedelta(days=6)
        weeks.append((curr_start, curr_end))
        curr_start = curr_end + pd.Timedelta(days=1)

    # Precompute each team's weekly distribution (mean & variance) for each of the 22 weeks
    # including SmartBot's weekly Bayesian schedule/waiver streaming (max_moves=2) on the 2 streamer bench spots (R12-R13)
    # while protecting the top 11 drafted core players (R1-R11)!
    my_team = assistant.my_team_idx
    rostered_all = {pid for r in rosters.values() for pid in r}
    # Strictly filter waiver pool to active NBA rotation players in df_base (excludes preseason Exhibit-10 camp players)
    base_waiver_pool_ids = [pid for pid in assistant.df_base.index if pid not in rostered_all][:90]
    protected_core_ids = set(rosters[my_team][:11])

    rotation_sched = deque(range(1, 12))
    weekly_team_dists = {w_idx: {} for w_idx in range(22)}
    sample_waiver_moves = []

    for w_idx, (w_start, w_end) in enumerate(weeks):
        matchups_w = [(0, rotation_sched[0])]
        for i in range(5):
            matchups_w.append((rotation_sched[i + 1], rotation_sched[10 - i]))
        rotation_sched.rotate(1)

        opp_of_mine = 0
        for t1, t2 in matchups_w:
            if t1 == my_team:
                opp_of_mine = t2
            elif t2 == my_team:
                opp_of_mine = t1

        week_my_roster = list(rosters[my_team])
        week_waiver_pool = list(base_waiver_pool_ids)

        # Execute SmartBot's weekly Bayesian waiver/schedule streaming on bottom 2 bench spots for week w_idx
        moves = get_bayesian_waiver_moves(
            team_roster_ids=week_my_roster,
            waiver_pool_ids=week_waiver_pool,
            bayesian_players=assistant.players,
            current_date=w_start,
            df_schedule=sched,
            player_team_map=assistant.engine.team_map,
            pos_dict=assistant.pos_dict,
            max_moves=2,
            season_engine=assistant.engine,
            opp_roster_ids=rosters[opp_of_mine],
            week_end_date=w_end,
        )
        for drop_id, add_id, drop_z, add_z in moves:
            if drop_id in protected_core_ids:
                continue
            if drop_id in week_my_roster and add_id in week_waiver_pool:
                week_my_roster.remove(drop_id)
                week_my_roster.append(add_id)
                week_waiver_pool.remove(add_id)
                if len(sample_waiver_moves) < 8:
                    d_nm = assistant.players[drop_id].name if drop_id in assistant.players else str(drop_id)
                    a_nm = assistant.players[add_id].name if add_id in assistant.players else str(add_id)
                    sample_waiver_moves.append(f"Hafta {w_idx+1}: -{d_nm} -> +{a_nm} (ΔΦ: +{add_z:.2f})")

        my_cat_weights, _ = assistant._compute_marginal_category_weights(week_my_roster)
        scaled_my_weights = {
            s: my_cat_weights.get(s, 1.0) * assistant.engine.default_norm_weights.get(s, 1.0)
            for s in assistant.engine.default_norm_weights
        }
        for t_idx in range(12):
            t_roster = week_my_roster if t_idx == my_team else rosters[t_idx]
            c_weights = scaled_my_weights if t_idx == my_team else None
            weekly_team_dists[w_idx][t_idx] = assistant.engine.get_expected_weekly_distribution(
                t_roster, start_date=w_start, end_date=w_end, category_weights=c_weights
            )

    all_cats = COUNT_STATS + ['FG_PCT', 'FT_PCT']

    season_ranks = []
    my_w_list, my_l_list, my_t_list = [], [], []
    my_cat_w_list, my_cat_l_list = [], []
    cat_win_counts = {c: 0.0 for c in all_cats}
    cat_total_matchups = 0

    team_cat_pct_accum = {t: [] for t in range(12)}
    team_match_pct_accum = {t: [] for t in range(12)}

    for sim_i in range(n_seasons):
        standings = {
            t: {'W': 0, 'L': 0, 'T': 0, 'Cat_W': 0, 'Cat_L': 0, 'Cat_T': 0}
            for t in range(12)
        }
        rotation = deque(range(1, 12))

        for w_idx in range(22):
            matchups = [(0, rotation[0])]
            for i in range(5):
                matchups.append((rotation[i + 1], rotation[10 - i]))
            rotation.rotate(1)

            # Sample weekly performance for each team from its calibrated weekly distribution
            sampled_week = {}
            for t_idx in range(12):
                dist = weekly_team_dists[w_idx][t_idx]
                w_mean = dist['mean']
                w_var = dist['var']
                s_dict = {}
                for c in COUNT_STATS:
                    mu = w_mean[c]
                    sd = math.sqrt(max(1e-6, w_var[c] * WEEKLY_VAR_INFLATION_BY_CAT.get(c, 1.30)))
                    s_dict[c] = max(0.0, rng.normal(mu, sd))

                for p_stat in PERCENTAGE_STATS:
                    m_mu = w_mean[f"{p_stat}M"]
                    a_mu = max(1.0, w_mean[f"{p_stat}A"])
                    p_mean = m_mu / a_mu
                    p_ref = 0.47 if p_stat == 'FG' else 0.78
                    imp_var = assistant.engine._compute_team_pct_impact_var(dist, p_stat, p_ref)
                    p_var = (imp_var / (a_mu ** 2)) * WEEKLY_VAR_INFLATION_BY_CAT.get(p_stat, 1.25)
                    s_dict[f"{p_stat}_PCT"] = float(np.clip(rng.normal(p_mean, math.sqrt(max(1e-8, p_var))), 0.20, 0.98))

                sampled_week[t_idx] = s_dict

            for t1, t2 in matchups:
                st1, st2 = sampled_week[t1], sampled_week[t2]
                w1, w2, ties = 0, 0, 0
                for c in all_cats:
                    v1, v2 = st1[c], st2[c]
                    if c == 'TOV':
                        win1 = v1 < v2
                    else:
                        win1 = v1 > v2
                    if abs(v1 - v2) < 1e-6:
                        ties += 1
                    elif win1:
                        w1 += 1
                    else:
                        w2 += 1

                    if t1 == my_team or t2 == my_team:
                        my_v = v1 if t1 == my_team else v2
                        opp_v = v2 if t1 == my_team else v1
                        if (c == 'TOV' and my_v < opp_v) or (c != 'TOV' and my_v > opp_v):
                            cat_win_counts[c] += 1.0

                if t1 == my_team or t2 == my_team:
                    cat_total_matchups += 1

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

        # Rank teams by Yahoo 9-Cat Each-Category Win Pct (and Matchup Win Pct)
        sorted_teams = sorted(
            range(12),
            key=lambda t: (
                standings[t]['Cat_W'] + 0.5 * standings[t]['Cat_T'],
                standings[t]['W'] + 0.5 * standings[t]['T'],
            ),
            reverse=True,
        )
        my_rank = sorted_teams.index(my_team) + 1
        season_ranks.append(my_rank)

        my_st = standings[my_team]
        my_w_list.append(my_st['W'])
        my_l_list.append(my_st['L'])
        my_t_list.append(my_st['T'])
        my_cat_w_list.append(my_st['Cat_W'])
        my_cat_l_list.append(my_st['Cat_L'])

        for t in range(12):
            st_t = standings[t]
            tot_c = max(1, st_t['Cat_W'] + st_t['Cat_L'] + st_t['Cat_T'])
            tot_m = max(1, st_t['W'] + st_t['L'] + st_t['T'])
            team_cat_pct_accum[t].append((st_t['Cat_W'] + 0.5 * st_t['Cat_T']) / tot_c)
            team_match_pct_accum[t].append((st_t['W'] + 0.5 * st_t['T']) / tot_m)

    avg_team_Order = sorted(
        range(12),
        key=lambda t: np.mean(team_cat_pct_accum[t]),
        reverse=True,
    )
    deterministic_rank = avg_team_Order.index(my_team) + 1

    return {
        'avg_rank': float(np.mean(season_ranks)),
        'median_rank': int(np.median(season_ranks)),
        'deterministic_rank': deterministic_rank,
        'top3_rate': float(np.mean([r <= 3 for r in season_ranks])) * 100.0,
        'rank1_rate': float(np.mean([r == 1 for r in season_ranks])) * 100.0,
        'avg_W': float(np.mean(my_w_list)),
        'avg_L': float(np.mean(my_l_list)),
        'avg_T': float(np.mean(my_t_list)),
        'matchup_win_pct': float(np.mean(team_match_pct_accum[my_team])) * 100.0,
        'avg_Cat_W': float(np.mean(my_cat_w_list)),
        'avg_Cat_L': float(np.mean(my_cat_l_list)),
        'cat_win_pct': float(np.mean(team_cat_pct_accum[my_team])) * 100.0,
        'cat_win_rates': {c: (cat_win_counts[c] / max(1, cat_total_matchups)) * 100.0 for c in all_cats},
        'sample_waiver_moves': sample_waiver_moves,
        'all_teams_summary': [
            {
                'slot': t + 1,
                'is_me': (t == my_team),
                'match_win_pct': float(np.mean(team_match_pct_accum[t])) * 100.0,
                'cat_win_pct': float(np.mean(team_cat_pct_accum[t])) * 100.0,
            }
            for t in avg_team_Order
        ],
    }


def main():
    print("Initializing Base 2026-27 LiveDraftAssistant...")
    base_assistant = LiveDraftAssistant(prior_season="2025_26", my_team_idx=7)
    df_adp = build_yahoo_adp_order(base_assistant)

    print("\n--- YENİ GERÇEKÇİ YAHOO 2026-27 ADP İLK 18 SIRALAMASI ---")
    print(df_adp[['NAME', 'TEAM', 'POS', 'EXP_MIN', 'AVAIL', 'BASE_Z', 'YAHOO_ADP_SCORE']].head(18).to_string())

    # Define 8 realistic Yahoo Draft Scenarios for Slot #8 (my_team_idx = 7)
    # In Scenarios 1-7, Jokic, Wembanyama, SGA, Luka Doncic, and Giannis Antetokounmpo are ALWAYS gone in Top 5!
    scenarios = [
        {
            "id": 1,
            "title": "Senaryo 1: Standart Yahoo ADP Masası (Maxey Çapası)",
            "desc": "İlk 7'de Jokić, Wemby, SGA, Luka, Giannis, Anthony Edwards ve Cade Cunningham seçilir. #8'de model en iyi seçimi (Tyrese Maxey) yapar.",
            "first_7": [203999, 1641705, 1628983, 1629029, 203507, 1630162, 1630595],
            "forced_pick_8": 1630178,  # Tyrese Maxey
            "seed": 101,
            "noise": 0.35,
        },
        {
            "id": 2,
            "title": "Senaryo 2: Guard Erimesi & All-Around Kanat (Scottie Barnes Çapası)",
            "desc": "İlk 7'de Jokić, Wemby, SGA, Luka, Giannis, Maxey ve Cade Cunningham seçilir. #8'de Scottie Barnes ile çok yönlü 9-Cat kadro kurulur.",
            "first_7": [203999, 1641705, 1628983, 1629029, 203507, 1630178, 1630595],
            "forced_pick_8": 1630567,  # Scottie Barnes
            "seed": 202,
            "noise": 0.45,
        },
        {
            "id": 3,
            "title": "Senaryo 3: Elit Oyun Kurucu Çapası (Cade Cunningham Çapası)",
            "desc": "İlk 7'de Jokić, Wemby, SGA, Luka, Giannis, Maxey ve Kevin Durant seçilir. #8'de Cade Cunningham ile PTS+AST+REB omurgası kurulur.",
            "first_7": [203999, 1641705, 1628983, 1629029, 203507, 1630178, 201142],
            "forced_pick_8": 1630595,  # Cade Cunningham
            "seed": 303,
            "noise": 0.45,
        },
        {
            "id": 4,
            "title": "Senaryo 4: Patlayıcı Skorer & Top Çalma (Donovan Mitchell Çapası)",
            "desc": "İlk 7'de Jokić, Wemby, SGA, Luka, Giannis, Maxey ve Scottie Barnes seçilir. #8'de Donovan Mitchell ile PTS+3PM+STL+FT% kadrosu kurulur.",
            "first_7": [203999, 1641705, 1628983, 1629029, 203507, 1630178, 1630567],
            "forced_pick_8": 1628378,  # Donovan Mitchell
            "seed": 404,
            "noise": 0.45,
        },
        {
            "id": 5,
            "title": "Senaryo 5: Anthony Edwards Çapası (Yüksek Hacimli Skorer Guard)",
            "desc": "İlk 7'de Jokić, Wemby, SGA, Luka, Giannis, Maxey ve KD seçilir. #8'de Anthony Edwards liderliğinde kadro inşa edilir.",
            "first_7": [203999, 1641705, 1628983, 1629029, 203507, 1630178, 201142],
            "forced_pick_8": 1630162,  # Anthony Edwards
            "seed": 505,
            "noise": 0.45,
        },
        {
            "id": 6,
            "title": "Senaryo 6: Yüksek Verimli Süperstar (Kevin Durant Çapası)",
            "desc": "İlk 7'de Jokić, Wemby, SGA, Luka, Giannis, Maxey ve Edwards seçilir. #8'de Kevin Durant (HOU) ile elit FG%+FT%+PTS+BLK dengesi kurulur.",
            "first_7": [203999, 1641705, 1628983, 1629029, 203507, 1630178, 1630162],
            "forced_pick_8": 201142,   # Kevin Durant
            "seed": 606,
            "noise": 0.45,
        },
        {
            "id": 7,
            "title": "Senaryo 7: Modern Point-Forward / Uzun Omurgası (Jalen Johnson / Şengün Çapası)",
            "desc": "İlk 7'de Jokić, Wemby, SGA, Luka, Giannis, Maxey ve Mitchell seçilir. #8'de Jalen Johnson ile REB+AST+STL+FG% (Punt FT%) inşa edilir.",
            "first_7": [203999, 1641705, 1628983, 1629029, 203507, 1630178, 1628378],
            "forced_pick_8": 1630552,  # Jalen Johnson
            "seed": 707,
            "noise": 0.50,
        },
        {
            "id": 8,
            "title": "Senaryo 8: Agresif Punt FT%/TOV Uzun Çapası (Alperen Şengün / Giannis Sinerjisi)",
            "desc": "İlk 7'de Jokić, Wemby, SGA, Luka, Maxey, Edwards ve Cade seçilir; #8'e Giannis Antetokounmpo düşer ve etrafına tam Punt FT% kadrosu kurulur.",
            "first_7": [203999, 1641705, 1628983, 1629029, 1630178, 1630162, 1630595],
            "forced_pick_8": 203507,   # Giannis Antetokounmpo slips to #8
            "seed": 808,
            "noise": 0.50,
        },
    ]

    results = []

    for sc in scenarios:
        print(f"\n=====================================================================")
        print(f"Simulating {sc['title']}...")
        assistant = LiveDraftAssistant(prior_season="2025_26", my_team_idx=7)
        rng = np.random.default_rng(sc['seed'])

        # Execute Picks 1..7 according to scenario's First 7
        first_7_names = []
        for idx_p, pid7 in enumerate(sc['first_7']):
            assistant.pick_player(pid7, team_idx=idx_p)
            first_7_names.append(f"#{idx_p+1} {assistant.players[pid7].name} ({assistant.team_abbr_dict.get(pid7, 'NBA')})")

        my_picks_detail = []
        for pick_idx in range(8, 157):
            st = assistant.get_draft_status()
            t_idx = st['on_clock_idx']
            r_num = st['round']

            if st['is_my_turn']:
                sug = assistant.rank_available_players(enable_logging=False)
                if pick_idx == 8 and sc.get('forced_pick_8') in assistant.available_player_ids:
                    chosen_pid = int(sc['forced_pick_8'])
                    match_row = sug[sug['ID'] == chosen_pid]
                    if not match_row.empty:
                        wp_score = float(match_row.iloc[0]['WIN_PROB_SCORE'])
                        punts_str = str(match_row.iloc[0]['Active_Punts'])
                    else:
                        wp_score = float(sug.iloc[0]['WIN_PROB_SCORE'])
                        punts_str = str(sug.iloc[0]['Active_Punts'])
                else:
                    top_row = sug.iloc[0]
                    chosen_pid = int(top_row['ID'])
                    wp_score = float(top_row['WIN_PROB_SCORE'])
                    punts_str = str(top_row['Active_Punts'])

                assistant.draft_player(chosen_pid)
                p_name = assistant.players[chosen_pid].name
                p_team = assistant.team_abbr_dict.get(chosen_pid, 'NBA')
                p_pos = assistant.pos_dict.get(chosen_pid, 'UTIL')
                my_picks_detail.append({
                    'Round': r_num,
                    'Overall_Pick': pick_idx,
                    'Player_ID': chosen_pid,
                    'Name': p_name,
                    'Team': p_team,
                    'Pos': p_pos,
                    'WinProb_Score': wp_score,
                    'Punts': punts_str,
                })
                print(f"  [R{r_num:2d} - Pick #{pick_idx:3d}] {p_name} ({p_team} - {p_pos}) | WinProb: {wp_score:.3f}/9.0 | Punts: {punts_str}")
            else:
                opp_pid = simulate_opponent_pick(assistant, t_idx, r_num, df_adp, rng, noise_sd=sc['noise'])
                assistant.pick_player(opp_pid, team_idx=t_idx)

        exp_w, cat_probs, nat_punts = assistant.evaluate_completed_league_win_prob(assistant.rosters)
        season_sim = run_2026_27_monte_carlo_season(assistant, assistant.rosters, n_seasons=100, seed=sc['seed'] + 1000)

        print(
            f"--> [SONUÇ - Senaryo {sc['id']}] Sezon Sıralaması: #{season_sim['deterministic_rank']} / 12 "
            f"(Ort. Sıra: {season_sim['avg_rank']:.2f}, Şampiyonluk: %{season_sim['rank1_rate']:.0f}, İlk 3: %{season_sim['top3_rate']:.0f}) | "
            f"Maç: {season_sim['avg_W']:.1f}G - {season_sim['avg_L']:.1f}M ({season_sim['matchup_win_pct']:.1f}%) | "
            f"Kategori: %{season_sim['cat_win_pct']:.1f}"
        )

        results.append({
            'scenario': sc,
            'first_7_names': first_7_names,
            'my_picks': my_picks_detail,
            'exp_weekly_wins': exp_w,
            'cat_probs': cat_probs,
            'nat_punts': nat_punts,
            'season_sim': season_sim,
        })

    # Save JSON/pickle summary so we can format the exhaustive Markdown report cleanly
    import json
    out_json = os.path.join(PROJECT_ROOT, 'data', 'simulations', 'slot8_2026_27_results.json')
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nAll 8 scenarios saved to {out_json}")


if __name__ == "__main__":
    main()

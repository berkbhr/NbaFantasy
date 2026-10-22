import os
import sys
import math
import time
import threading
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
from simulator import load_prior_season, get_positional_averages
from bayesian_model import BayesianPlayer, COUNT_STATS, PERCENTAGE_STATS
from matchup_engine import (
    MatchupEngine,
    can_fill_roster_cached,
    norm_cdf,
    norm_pdf,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')


class LiveDraftAssistant:
    def __init__(self, prior_season="2025_26", target_minutes=None, **kwargs):
        self.prior_season = prior_season
        self.target_season = kwargs.get('target_season', "2026_27" if prior_season == "2025_26" else prior_season)
        self.target_minutes = target_minutes
        self.priors = load_prior_season(prior_season)

        self.players = {}
        self.available_player_ids = set()
        self.my_roster = []
        # Default to Slot #8 (0-indexed: 7) for the user's 14-team Yahoo Snake Draft
        self.num_teams = int(kwargs.get('num_teams', 14))
        self.total_rounds = int(kwargs.get('total_rounds', 13))
        self.total_picks = self.num_teams * self.total_rounds
        self.my_team_idx = kwargs.get('my_team_idx', 7)
        self.rosters = {i: [] for i in range(self.num_teams)}
        self.punt_categories = []
        self.pick_history = []  # Stack of (player_id, team_idx, is_my_pick) for undo
        self.lock = threading.RLock()
        self.unresolved_picks = []  # (pick_no, yahoo_name, team_idx) that couldn't be matched exactly
        self.fast_z_dict = {}
        self._suggestion_cache = {}
        self._last_sync_source = "manual"
        self._last_sync_time = None

        self.external_pool_ids = kwargs.get('pool_ids', None)
        self.team_abbr_dict = {}

        self.load_data()
        self.pos_averages = get_positional_averages(self.priors, pos_dict=self.pos_dict)
        self.initialize_ai()
        self.calculate_baselines()

    def load_data(self):
        pos_file = os.path.join(PROCESSED_DIR, 'player_positions.parquet')
        if os.path.exists(pos_file):
            self.df_pos = pd.read_parquet(pos_file)
            self.pos_dict = self.df_pos.set_index('PLAYER_ID')['POSITION'].to_dict()
        else:
            print("WARNING: player_positions.parquet not found. Positions will be generic.")
            self.pos_dict = {}
            self.df_pos = pd.DataFrame()

        self.active_roster_df = pd.DataFrame()
        roster_26_file = os.path.join(PROCESSED_DIR, 'active_roster_2026_27.parquet')
        if self.prior_season == "2025_26" and os.path.exists(roster_26_file):
            self.active_roster_df = pd.read_parquet(roster_26_file)
            for _, r in self.active_roster_df.iterrows():
                pid = int(r['PLAYER_ID'])
                self.team_abbr_dict[pid] = str(r.get('TEAM_ABBREVIATION', 'FA'))
                pos_val = str(r.get('POSITION', '')).strip()
                if pos_val and pos_val != 'UNK':
                    self.pos_dict[pid] = pos_val

        sched_candidates = [
            os.path.join(PROCESSED_DIR, f'schedule_{self.target_season}.parquet'),
            os.path.join(PROCESSED_DIR, f'schedule_{self.prior_season}.parquet'),
            os.path.join(PROCESSED_DIR, 'schedule_2026_27.parquet'),
            os.path.join(PROCESSED_DIR, 'schedule_2024_25.parquet'),
        ]
        self.schedule_df = pd.DataFrame()
        for sched_file in sched_candidates:
            if os.path.exists(sched_file):
                self.schedule_df = pd.read_parquet(sched_file)
                self.schedule_df['GAME_DATE'] = pd.to_datetime(self.schedule_df['GAME_DATE']).dt.normalize()
                break

    def get_eligible_slots(self, pos_str):
        slots = []
        pos_str = str(pos_str).upper()
        if 'G' in pos_str:
            slots.extend(['PG', 'SG', 'G', 'UTIL', 'BENCH'])
        if 'F' in pos_str:
            slots.extend(['SF', 'PF', 'F', 'UTIL', 'BENCH'])
        if 'C' in pos_str:
            slots.extend(['C', 'UTIL', 'BENCH'])

        return list(set(slots)) if slots else ['PG', 'SG', 'G', 'SF', 'PF', 'F', 'C', 'UTIL', 'BENCH']

    def initialize_ai(self):
        logs_file = os.path.join(DATA_DIR, 'raw', f'player_logs_{self.prior_season}.parquet')
        if not os.path.exists(logs_file):
            logs_file = os.path.join(DATA_DIR, 'raw', 'player_logs_2024_25.parquet')
        df_logs = pd.read_parquet(logs_file)
        name_frames = [df_logs[['PLAYER_ID', 'PLAYER_NAME']].drop_duplicates()]

        # Include players from 2024-25 (injured stars) and 2026-27 active roster / preseason rookies
        if self.prior_season == "2025_26":
            prev_logs = os.path.join(DATA_DIR, 'raw', 'player_logs_2024_25.parquet')
            if os.path.exists(prev_logs):
                df_prev = pd.read_parquet(prev_logs, columns=['PLAYER_ID', 'PLAYER_NAME']).drop_duplicates()
                name_frames.append(df_prev)
            if not self.active_roster_df.empty:
                name_frames.append(self.active_roster_df[['PLAYER_ID', 'PLAYER_NAME']].drop_duplicates())
            pre_logs = os.path.join(DATA_DIR, 'raw', 'preseason_logs_2026_27.parquet')
            if os.path.exists(pre_logs):
                df_pre = pd.read_parquet(pre_logs, columns=['PLAYER_ID', 'PLAYER_NAME']).drop_duplicates()
                name_frames.append(df_pre)

        unique_players = pd.concat(name_frames, ignore_index=True).drop_duplicates(subset=['PLAYER_ID'], keep='first')

        if self.external_pool_ids is not None:
            unique_players = unique_players[unique_players['PLAYER_ID'].isin(self.external_pool_ids)]
        else:
            valid_pids = {
                pid for pid, pdata in self.priors.items()
                if pdata.get('MIN', 0) >= 100 or pdata.get('IS_ROOKIE_PRIOR', False)
            }
            if not self.active_roster_df.empty:
                active_ids = set(self.active_roster_df['PLAYER_ID'].astype(int).tolist())
                valid_pids = valid_pids.union(active_ids)
            if valid_pids:
                unique_players = unique_players[unique_players['PLAYER_ID'].isin(valid_pids)]

        self.projected_stats = {}

        for _, row in unique_players.iterrows():
            pid = int(row['PLAYER_ID'])
            name = row['PLAYER_NAME']
            pos_str = self.pos_dict.get(pid, 'UTIL')

            bp = BayesianPlayer(pid, name)
            player_prior = self.priors.get(pid, None)
            bp.initialize_priors(player_prior, self.pos_averages, pos_str=pos_str)
            self.players[pid] = bp
            self.available_player_ids.add(pid)

        self.engine = MatchupEngine(
            self.players, self.schedule_df, self.df_pos, season=self.target_season, prior_season=self.prior_season
        )

        for pid, bp in self.players.items():
            preds = bp.predict_next_game(self.target_minutes)
            avail = getattr(bp, 'availability_rate', 0.85)
            # In a 13-man roster with 10 active slots (+ Yahoo IL/IL+), missed games are partially
            # absorbed by the 3 bench slots rather than producing zero team output
            eff_avail = 0.60 * avail + 0.40 * 0.85
            flat_stats = {'EXP_MIN': preds['MIN']['mean'], 'AVAIL': avail}

            for stat in COUNT_STATS:
                mu = preds.get(stat, {}).get('mean', 0.0)
                var = preds.get(stat, {}).get('variance', 0.0)
                flat_stats[stat] = mu * eff_avail
                # Exact Bernoulli mixture variance: a * sigma^2 + a * (1 - a) * mu^2 (fixes Rapor 1 / 3.3)
                flat_stats[f"{stat}_var"] = avail * var + avail * (1.0 - avail) * (mu ** 2)

            for stat in PERCENTAGE_STATS:
                rate = preds.get(stat, {}).get('rate', 0.0)
                makes = preds.get(stat, {}).get('mean', 0.0) * eff_avail
                att = preds.get(stat, {}).get('attempts', 10.0) * eff_avail
                var_makes = preds.get(stat, {}).get('variance', 0.0) * avail
                flat_stats[f"{stat}_rate"] = rate
                flat_stats[f"{stat}_vol"] = makes
                flat_stats[f"{stat}M"] = makes
                flat_stats[f"{stat}A"] = att
                flat_stats[f"{stat}M_var"] = var_makes

            flat_stats['NAME'] = bp.name
            flat_stats['TEAM'] = self.team_abbr_dict.get(pid, 'NBA')
            flat_stats['POS'] = self.pos_dict.get(pid, 'UTIL')
            flat_stats['ELIGIBLE'] = self.get_eligible_slots(flat_stats['POS'])
            self.projected_stats[pid] = flat_stats

    def calculate_baselines(self):
        """
        Calculates Z-Scores on the consistent 9-category draftable reference population (top 156 players)
        including FG and FT impact in the preliminary ranking (fixes Rapor 1 / 3.4), and computes
        H2H ADP_Z (blending 9-cat BASE_Z with Best-8-of-9 H2H punt value so high-usage stars like
        Luka Doncic or Giannis Antetokounmpo are drafted at realistic Yahoo ADP slots by opponents).
        """
        df = pd.DataFrame.from_dict(self.projected_stats, orient='index')

        self.z_means = {}
        self.z_stds = {}

        prelim_z = pd.Series(0.0, index=df.index)
        for stat in COUNT_STATS:
            s_std = df[stat].std()
            z_s = (df[stat] - df[stat].mean()) / (s_std if s_std and s_std > 0 else 1.0)
            prelim_z += (-z_s if stat == 'TOV' else z_s)

        for stat in PERCENTAGE_STATS:
            tot_m = df[f"{stat}M"].sum()
            tot_a = df[f"{stat}A"].sum()
            p_all = tot_m / tot_a if tot_a > 0 else (0.47 if stat == 'FG' else 0.78)
            imp_all = (df[f"{stat}_rate"] - p_all) * df[f"{stat}A"]
            imp_std = imp_all.std()
            if imp_std and imp_std > 0:
                prelim_z += (imp_all - imp_all.mean()) / imp_std

        ref_size = min(156, len(df))
        top_df = df.loc[prelim_z.sort_values(ascending=False).head(ref_size).index].copy()

        for stat in COUNT_STATS:
            self.z_means[stat] = top_df[stat].mean()
            self.z_stds[stat] = top_df[stat].std()
            z_series = (df[stat] - self.z_means[stat]) / (self.z_stds[stat] if self.z_stds[stat] else 1.0)
            if stat == 'TOV':
                z_series = -z_series
            df[f"Z_{stat}"] = z_series

        for stat in PERCENTAGE_STATS:
            total_m = top_df[f"{stat}M"].sum()
            total_a = top_df[f"{stat}A"].sum()
            avg_rate = (total_m / total_a) if total_a > 0 else top_df[f"{stat}_rate"].mean()
            self.z_means[f"{stat}_rate"] = avg_rate

            df[f"IMPACT_{stat}"] = (df[f"{stat}_rate"] - avg_rate) * df[f"{stat}A"]
            top_impact = (top_df[f"{stat}_rate"] - avg_rate) * top_df[f"{stat}A"]

            impact_mean = top_impact.mean()
            impact_std = top_impact.std()
            self.z_means[f"IMPACT_{stat}"] = impact_mean
            self.z_stds[f"IMPACT_{stat}"] = impact_std

            df[f"Z_{stat}"] = (df[f"IMPACT_{stat}"] - impact_mean) / (impact_std if impact_std else 1.0)

        z_cols = [f"Z_{s}" for s in COUNT_STATS + PERCENTAGE_STATS]
        df['BASE_Z'] = df[z_cols].sum(axis=1)

        # Pure mathematical H2H valuation (Zero hardcoded IDs):
        # 1. Category Scarcity & Waiver Replaceability Weights (TOV is a byproduct of usage; PTS/AST are scarce)
        scarcity_weights = {
            'PTS': 1.35, 'AST': 1.25, 'REB': 1.15, 'STL': 1.05, 'BLK': 1.05,
            'FG3M': 0.95, 'FG': 1.00, 'FT': 0.85, 'TOV': 0.25,
        }
        scarcity_z = sum(df[f"Z_{s}"] * w for s, w in scarcity_weights.items())

        # 2. H2H Structural Punt-2 Envelope (evaluates a player on their Best 7-of-9 weighted categories)
        weighted_non_pts = np.column_stack([
            df[f"Z_{s}"].values * scarcity_weights[s]
            for s in COUNT_STATS + PERCENTAGE_STATS if s != 'PTS'
        ])
        sorted_wnp = np.sort(weighted_non_pts, axis=1)
        punt2_z = (
            scarcity_z
            - 1.00 * np.minimum(0.0, sorted_wnp[:, 0])
            - 0.90 * np.minimum(0.0, sorted_wnp[:, 1])
        )

        # 3. Convex Roster Slot Compression (1 player producing +2.0 sigma in scarce categories + FG% saves a roster slot)
        upside_cols = ['Z_PTS', 'Z_AST', 'Z_REB', 'Z_STL', 'Z_BLK', 'Z_FG3M', 'Z_FG']
        slot_compression = sum(
            0.42 * np.power(np.maximum(0.0, df[c] - 0.85), 1.35)
            for c in upside_cols
        )
        df['ADP_Z'] = 0.80 * punt2_z + slot_compression + 0.20 * df['BASE_Z'].clip(lower=0.0)



        df_sorted = df.sort_values('BASE_Z', ascending=False)
        self.df_base = df_sorted

        all_cats = COUNT_STATS + PERCENTAGE_STATS
        self.fast_z_dict = {
            int(pid): {s: float(row[f"Z_{s}"]) for s in all_cats}
            for pid, row in df_sorted.iterrows()
        }

        # Precompute round-by-round cohort average Z per category (rounds 1..total_rounds, num_teams picks per round)
        # so early picks are compared against same-round opponent picks, NOT 13th-round bench players!
        # Cohorts follow ADP_Z (the order opponents actually draft in), not raw BASE_Z.
        df_adp_sorted = df.sort_values('ADP_Z', ascending=False)
        self.round_cohort_z = {}
        for r_idx in range(self.total_rounds):
            start_i = r_idx * self.num_teams
            end_i = min((r_idx + 1) * self.num_teams, len(df_adp_sorted))
            if start_i < end_i:
                cohort = df_adp_sorted.iloc[start_i:end_i]
                self.round_cohort_z[r_idx + 1] = {
                    s: float(cohort[f"Z_{s}"].mean()) for s in all_cats
                }
            else:
                self.round_cohort_z[r_idx + 1] = {s: 0.0 for s in all_cats}

        # Initialize Free Agent Pool in MatchupEngine from top available players
        avail_in_base = [pid for pid in self.available_player_ids if pid in self.df_base.index]
        self.engine.free_agent_pool = avail_in_base

        # Initialize Injury Tracker & Sync into Players
        from injury_tracker import InjuryTracker
        self.injury_tracker = InjuryTracker()
        self._sync_injuries_into_players()

    def _sync_injuries_into_players(self):
        if not hasattr(self, 'injury_tracker'):
            return
        injuries = self.injury_tracker.get_all_active_injuries()
        for inj in injuries:
            pid = inj['player_id']
            if pid in self.players:
                self.players[pid].update_injury_status(
                    status=inj['status'],
                    desc=inj['injury_desc'],
                    is_b2b_rest=inj['is_b2b_rest'],
                    expected_return=inj['expected_return']
                )

    def _get_state_key(self):
        return (
            self.my_team_idx,
            tuple(self.punt_categories),
            tuple(pid for pid, _, _ in self.pick_history),
        )

    def _compute_marginal_category_weights(self, roster_ids):
        """
        Computes marginal utility weights for each category relative to a full 13-man H2H matchup
        and round-matched opponent cohort (fixes Rapor 1 / K5):
          - Uses precomputed self.fast_z_dict (zero Pandas .loc overhead inside rollout loops).
          - Subtracts the expected Z of same-round opponent picks.
          - Scales by the full 13-man roster difference standard deviation (sqrt(2 * 13) ≈ 5.10).
        """
        all_cats = COUNT_STATS + PERCENTAGE_STATS
        n_picked = len(roster_ids)
        if n_picked == 0:
            return {s: 1.0 for s in all_cats}, {s: 0.5 for s in all_cats}

        valid_ids = [p for p in roster_ids if p in self.fast_z_dict]
        if not valid_ids:
            return {s: 1.0 for s in all_cats}, {s: 0.5 for s in all_cats}

        # Full 13-man H2H difference standard deviation (our 13 players vs opponent's 13 players)
        full_roster_diff_sd = math.sqrt(2.0 * 13.0)  # ≈ 5.10
        phi_zero = norm_pdf(0.0)

        weights = {}
        cat_win_probs = {}

        for s in all_cats:
            if s in self.punt_categories:
                weights[s] = 0.0
                cat_win_probs[s] = 0.0
                continue

            my_z_sum = sum(self.fast_z_dict[p][s] for p in valid_ids)
            opp_cohort_z_sum = sum(
                self.round_cohort_z.get(r_num, {}).get(s, 0.0)
                for r_num in range(1, min(n_picked, 13) + 1)
            )
            raw_diff = my_z_sum - opp_cohort_z_sum
            net_z_diff = raw_diff / full_roster_diff_sd

            cat_win_probs[s] = norm_cdf(net_z_diff)

            if s == 'FT' and raw_diff < -3.3:
                weights[s] = 0.04
            elif n_picked >= 4 and raw_diff < -4.2:
                weights[s] = 0.08
            else:
                weights[s] = max(0.15, norm_pdf(net_z_diff) / phi_zero)

        return weights, cat_win_probs

    def evaluate_completed_league_win_prob(self, sim_rosters):
        """
        Evaluates our completed 13-man roster pairwise against each of the 11 opponent rosters
        using MatchupEngine.evaluate_h2h_matchup:
          - Combines expected weekly category wins with Poisson-Binomial weekly matchup win
            probability P(Cat_W >= 5) so the rollout maximizes both weekly H2H matchup wins
            and total category dominance without unnecessarily sacrificing winnable categories.
        """
        team_dists = {}
        for i in range(self.num_teams):
            team_dists[i] = self.engine.get_expected_weekly_distribution(sim_rosters[i], start_date=None, end_date=None)

        my_dist = team_dists[self.my_team_idx]
        opp_indices = [i for i in range(self.num_teams) if i != self.my_team_idx]

        cat_prob_sums = {stat: 0.0 for stat in COUNT_STATS + PERCENTAGE_STATS}
        total_expected_wins_sum = 0.0
        total_matchup_win_prob_sum = 0.0

        for j in opp_indices:
            _, win_probs_j, _ = self.engine.evaluate_h2h_matchup(my_dist, team_dists[j])
            mu_j = 0.0
            var_j = 0.0
            for stat in COUNT_STATS:
                p_w = 0.0 if stat in self.punt_categories else win_probs_j[stat]
                cat_prob_sums[stat] += p_w
                total_expected_wins_sum += p_w
                mu_j += p_w
                var_j += p_w * (1.0 - p_w)
            for stat in PERCENTAGE_STATS:
                p_w = 0.0 if stat in self.punt_categories else win_probs_j[f"{stat}_PCT"]
                cat_prob_sums[stat] += p_w
                total_expected_wins_sum += p_w
                mu_j += p_w
                var_j += p_w * (1.0 - p_w)

            p_matchup_j = norm_cdf((mu_j - 4.5) / math.sqrt(max(0.25, var_j)))
            total_matchup_win_prob_sum += p_matchup_j

        n_opps = float(len(opp_indices))
        avg_expected_wins = total_expected_wins_sum / n_opps
        avg_matchup_win_prob = total_matchup_win_prob_sum / n_opps
        avg_cat_probs = {stat: val / n_opps for stat, val in cat_prob_sums.items()}

        # Gentle diminishing returns above 66% win prob so the rollout doesn't over-stack 3PM/FT% past 70%
        sat_by_stat = {
            stat: (p_c if p_c <= 0.66 else (0.66 + 0.50 * (p_c - 0.66)))
            for stat, p_c in avg_cat_probs.items()
        }
        # Only allow structural 1-category punts in non-core categories (FT, AST, BLK, FG3M, TOV);
        # never allow FG% or REB to be thrown away as a free punt category!
        puntable_stats = ('FT', 'AST', 'BLK', 'FG3M', 'TOV')
        worst_puntable_stat = min(puntable_stats, key=lambda s: sat_by_stat.get(s, 1.0))
        top8_sat = sum(val for stat, val in sat_by_stat.items() if stat != worst_puntable_stat)

        # Penalize if FG% or REB drops below 44% (prevents correlated big-man collapse)
        core_floor_penalty = 0.0
        for core_stat in ('FG', 'REB', 'PTS'):
            if avg_cat_probs.get(core_stat, 0.5) < 0.44:
                core_floor_penalty += 0.85 * (0.44 - avg_cat_probs[core_stat])

        h2h_dominance_score = (
            0.45 * avg_expected_wins
            + 0.30 * (top8_sat * (9.0 / 8.0))
            + 0.25 * (9.0 * avg_matchup_win_prob)
            - core_floor_penalty
        )

        natural_punts = [stat for stat, prob in avg_cat_probs.items() if prob < 0.38]
        return h2h_dominance_score, avg_cat_probs, natural_punts

    def get_fast_suggestions(self, top_n=10):
        """
        Instantaneous (<1ms) fallback suggestion table using marginal Z-scores + ADP blend.
        Guaranteed to return in <0.002 seconds if the 30-second clock is under emergency pressure.
        """
        with self.lock:
            avail_in_base = [pid for pid in self.available_player_ids if pid in self.df_base.index]
            df_avail = self.df_base.loc[avail_in_base].copy()
            current_weights, cat_win_probs = self._compute_marginal_category_weights(self.my_roster)
            all_cats = COUNT_STATS + PERCENTAGE_STATS
            z_cols = [f"Z_{s}" for s in all_cats]
            w_vec = np.array([current_weights[s] for s in all_cats])
            df_avail['FAST_SCORE'] = df_avail[z_cols].values @ w_vec
            df_avail['ID'] = df_avail.index
            natural_punts = [s for s, p in cat_win_probs.items() if p < 0.38]
            df_avail['Active_Punts'] = ", ".join(natural_punts) if natural_punts else "Dengeli (Yok)"
            return df_avail.sort_values('FAST_SCORE', ascending=False).head(top_n)

    def rank_available_players(self, enable_logging=True, timeout_budget_sec=3.5, use_cache=True):
        """
        Thread-safe, dictionary-accelerated Pairwise H2H Rollout ranking:
          - Returns pre-computed cached result in 0.0ms if state hasn't changed.
          - Uses self.fast_z_dict (zero Pandas .loc inside rollout loop) to finish 20 candidates in ~40-90ms.
          - Enforces a hard timeout_budget_sec guard so a 30-second Yahoo draft clock is never exceeded.
        """
        t_start = time.perf_counter()
        with self.lock:
            state_key = self._get_state_key()
            if use_cache and state_key in self._suggestion_cache:
                return self._suggestion_cache[state_key].copy()

            current_round = len(self.my_roster) + 1
            avail_in_base = [pid for pid in self.available_player_ids if pid in self.df_base.index]
            df_avail = self.df_base.loc[avail_in_base].sort_values('BASE_Z', ascending=False)
            if 'ADP_Z' in df_avail.columns:
                df_opp_order = df_avail.sort_values('ADP_Z', ascending=False)
            else:
                df_opp_order = df_avail

            all_cats = COUNT_STATS + PERCENTAGE_STATS
            current_weights, _ = self._compute_marginal_category_weights(self.my_roster)
            z_cols = [f"Z_{s}" for s in all_cats]
            w_vec = np.array([current_weights[s] for s in all_cats])
            df_avail = df_avail.copy()
            df_avail['MARGINAL_Z'] = df_avail[z_cols].values @ w_vec

            df_avail_for_us = df_avail.sort_values('MARGINAL_Z', ascending=False)
            us_order_list = [int(x) for x in df_avail_for_us.index]
            opp_order_list = [int(x) for x in df_opp_order.index]

            cand_order = list(us_order_list)
            if current_round == 1 and 'ADP_Z' in df_avail.columns:
                top_adp_ids = [int(x) for x in df_avail.sort_values('ADP_Z', ascending=False).head(12).index]
                cand_order = list(dict.fromkeys(us_order_list[:14] + top_adp_ids + cand_order))

            valid_candidates = []
            max_cands = 20 if current_round == 1 else 18
            for pid in cand_order:
                test_my_roster = self.rosters[self.my_team_idx] + [pid]
                pos_tuple = tuple(sorted(self.pos_dict.get(p, 'UTIL') for p in test_my_roster))
                if can_fill_roster_cached(pos_tuple):
                    valid_candidates.append(pid)
                if len(valid_candidates) >= max_cands:
                    break

            if not valid_candidates:
                valid_candidates = [int(x) for x in df_avail.head(18).index]

            base_rosters_snapshot = {i: list(r) for i, r in self.rosters.items()}
            base_avail_snapshot = set(self.available_player_ids)
            my_roster_snapshot = list(self.my_roster)

        if enable_logging:
            print(f"Ranking players (Round {current_round}) via Fast Pairwise H2H Rollout...")

        scores = []
        for idx_c, pid in enumerate(valid_candidates):
            # Hard deadline guard: never block a live 30-second draft clock if budget expires
            if idx_c >= 5 and (time.perf_counter() - t_start) > timeout_budget_sec:
                if enable_logging:
                    print(f"[TIME GUARD] Rollout budget ({timeout_budget_sec:.1f}s) reached at {idx_c}/{len(valid_candidates)} candidates.")
                break

            sim_rosters = {i: list(r) for i, r in base_rosters_snapshot.items()}
            sim_available = set(base_avail_snapshot)

            sim_rosters[self.my_team_idx].append(pid)
            sim_available.discard(pid)

            current_pick_number = sum(len(r) for r in sim_rosters.values()) + 1

            for pick_idx in range(current_pick_number, self.total_picks + 1):
                round_num = ((pick_idx - 1) // self.num_teams) + 1
                turn_in_round = (pick_idx - 1) % self.num_teams
                team_turn = turn_in_round if round_num % 2 != 0 else (self.num_teams - 1) - turn_in_round

                if len(sim_rosters[team_turn]) >= self.total_rounds:
                    continue

                if team_turn == self.my_team_idx:
                    cur_my_team = sim_rosters[team_turn]
                    n_centers = sum(1 for p in cur_my_team if 'C' in self.pos_dict.get(p, ''))
                    n_guards = sum(1 for p in cur_my_team if 'G' in self.pos_dict.get(p, ''))

                    my_weights, _ = self._compute_marginal_category_weights(cur_my_team)
                    best_cand = None
                    best_cand_val = -1e9
                    checked = 0
                    for cand_pid in us_order_list:
                        if cand_pid not in sim_available:
                            continue
                        test_roster = cur_my_team + [cand_pid]
                        pos_tuple = tuple(sorted(self.pos_dict.get(p, 'UTIL') for p in test_roster))
                        if not can_fill_roster_cached(pos_tuple):
                            continue
                        cand_z = self.fast_z_dict[cand_pid]
                        val = sum(cand_z[s] * my_weights[s] for s in all_cats)

                        # Frontcourt / Backcourt balance: prevents perimeter pileup and anchors big-man stats early
                        cand_pos = self.pos_dict.get(cand_pid, '')
                        if len(cur_my_team) >= 1 and n_centers == 0:
                            if 'C' in cand_pos:
                                val += 0.85
                            elif 'G' in cand_pos and 'F' not in cand_pos:
                                val -= 0.50
                        elif len(cur_my_team) >= 3 and n_centers < 2:
                            if 'C' in cand_pos:
                                val += 0.70
                            elif n_guards >= 3 and 'G' in cand_pos:
                                val -= 0.45

                        if val > best_cand_val:
                            best_cand_val = val
                            best_cand = cand_pid
                        checked += 1
                        if checked >= 32:
                            break
                    if best_cand is not None:
                        sim_rosters[team_turn].append(best_cand)
                        sim_available.remove(best_cand)
                else:
                    for cand_pid in opp_order_list:
                        if cand_pid in sim_available:
                            test_roster = sim_rosters[team_turn] + [cand_pid]
                            pos_tuple = tuple(sorted(self.pos_dict.get(p, 'UTIL') for p in test_roster))
                            if not can_fill_roster_cached(pos_tuple):
                                continue
                            sim_rosters[team_turn].append(cand_pid)
                            sim_available.remove(cand_pid)
                            break

            expected_wins, cat_probs, natural_punts = self.evaluate_completed_league_win_prob(sim_rosters)

            predicted_picks_names = ""
            if enable_logging:
                my_sim_roster = sim_rosters[self.my_team_idx]
                future_picks = [p for p in my_sim_roster if p not in my_roster_snapshot and p != pid]
                future_names = [
                    self.df_base.loc[fp]['NAME'] if fp in self.df_base.index else str(fp)
                    for fp in future_picks
                ]
                predicted_picks_names = ", ".join(future_names)

            row_meta = df_avail.loc[pid]
            # Candidate score combines completed 13-man H2H win prob + talent VORP drop-off premium
            # for irreplaceable first-round superstars who will never survive to the next pick
            vorp_premium = 0.07 * max(0.0, float(row_meta['ADP_Z']) - 6.0)
            composite_score = expected_wins + vorp_premium

            scores.append({
                'ID': pid,
                'NAME': row_meta['NAME'],
                'TEAM': row_meta.get('TEAM', 'NBA'),
                'POS': row_meta['POS'],
                'Score': composite_score,
                'WIN_PROB_SCORE': expected_wins,
                'COMPOSITE_SCORE': composite_score,
                'FAST_SCORE': float(row_meta['MARGINAL_Z']),
                'BASE_Z': float(row_meta['BASE_Z']),
                'Predicted_Picks': predicted_picks_names,
                'Active_Punts': ", ".join(natural_punts) if natural_punts else "Dengeli (Yok)",
                'Cat_Probs': cat_probs,
            })

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        df_sug = pd.DataFrame(scores).sort_values('Score', ascending=False)
        df_sug.attrs['elapsed_ms'] = elapsed_ms

        with self.lock:
            if self._get_state_key() == state_key:
                self._suggestion_cache[state_key] = df_sug.copy()

        return df_sug

    def precompute_suggestions_async(self):
        """
        Speculatively computes and caches rank_available_players() in a background daemon thread
        whenever picks are near our turn, so when our 30-second clock starts, the result is ready in 0ms!
        """
        def _worker():
            try:
                self.rank_available_players(enable_logging=False, timeout_budget_sec=3.0, use_cache=True)
            except Exception:
                pass

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _infer_current_snake_team_idx(self):
        """
        Automatically resolves which team is on the clock in the snake draft
        when team_idx is not explicitly passed.
        """
        current_pick_number = sum(len(r) for r in self.rosters.values()) + 1
        round_num = ((current_pick_number - 1) // self.num_teams) + 1
        turn_in_round = (current_pick_number - 1) % self.num_teams
        return turn_in_round if round_num % 2 != 0 else (self.num_teams - 1) - turn_in_round

    def get_draft_status(self):
        """Returns current overall pick, round, team on the clock, and picks until my_team_idx."""
        with self.lock:
            current_pick_number = sum(len(r) for r in self.rosters.values()) + 1
            round_num = ((current_pick_number - 1) // self.num_teams) + 1
            turn_in_round = (current_pick_number - 1) % self.num_teams
            on_clock_idx = turn_in_round if round_num % 2 != 0 else (self.num_teams - 1) - turn_in_round

            picks_until_mine = 0
            for p_idx in range(current_pick_number, self.total_picks + 1):
                r_n = ((p_idx - 1) // self.num_teams) + 1
                t_in_r = (p_idx - 1) % self.num_teams
                t_idx = t_in_r if r_n % 2 != 0 else (self.num_teams - 1) - t_in_r
                if t_idx == self.my_team_idx:
                    break
                picks_until_mine += 1

            return {
                'overall_pick': current_pick_number,
                'round': round_num,
                'pick_in_round': turn_in_round + 1,
                'on_clock_idx': on_clock_idx,
                'on_clock_slot': on_clock_idx + 1,
                'my_slot': self.my_team_idx + 1,
                'picks_until_mine': picks_until_mine,
                'is_my_turn': (on_clock_idx == self.my_team_idx),
                'total_picks_made': len(self.pick_history),
                'last_sync_source': self._last_sync_source,
                'last_sync_time': self._last_sync_time,
            }

    def resolve_player_id(self, query_str, only_available=True):
        """Resolves a player ID from either an integer ID or a partial/fuzzy player name."""
        if query_str is None:
            return None
        query_str = str(query_str).strip()
        if not query_str:
            return None
        if query_str.isdigit():
            pid = int(query_str)
            if pid in self.players:
                if only_available and pid not in self.available_player_ids:
                    return None
                return pid

        import unicodedata
        def _norm(s):
            s_clean = ''.join(
                c for c in unicodedata.normalize('NFD', str(s).lower())
                if unicodedata.category(c) != 'Mn'
            )
            for suffix in (' jr.', ' jr', ' sr.', ' sr', ' iii', ' ii', ' iv'):
                if s_clean.endswith(suffix):
                    s_clean = s_clean[:-len(suffix)].strip()
            return s_clean.replace('.', '').replace("'", "").strip()

        q_norm = _norm(query_str)
        candidates = []
        for pid in self.df_base.index:
            if only_available and pid not in self.available_player_ids:
                continue
            name = self.df_base.loc[pid]['NAME']
            n_norm = _norm(name)
            if q_norm == n_norm or query_str.lower() == str(name).lower():
                return int(pid)
            if q_norm in n_norm:
                candidates.append(int(pid))

        if candidates:
            return candidates[0]  # Already sorted by BASE_Z descending in self.df_base
        return None

    def pick_player(self, player_id, team_idx=None, source="manual"):
        with self.lock:
            if team_idx is None:
                team_idx = self._infer_current_snake_team_idx()
            if team_idx == self.my_team_idx:
                return self.draft_player(player_id, team_idx=team_idx, source=source)
            self.available_player_ids.discard(player_id)
            if team_idx in self.rosters and player_id not in self.rosters[team_idx]:
                self.rosters[team_idx].append(player_id)
                self.pick_history.append((player_id, team_idx, False))
            self._last_sync_source = source
            self._last_sync_time = time.strftime("%H:%M:%S")
            st = self.get_draft_status()
            if st['picks_until_mine'] <= 2:
                self.precompute_suggestions_async()

    def draft_player(self, player_id, team_idx=None, source="manual"):
        with self.lock:
            if team_idx is None:
                team_idx = self.my_team_idx
            self.available_player_ids.discard(player_id)
            if player_id not in self.my_roster:
                self.my_roster.append(player_id)
            if team_idx in self.rosters and player_id not in self.rosters[team_idx]:
                self.rosters[team_idx].append(player_id)
            self.pick_history.append((player_id, team_idx, True))
            self._last_sync_source = source
            self._last_sync_time = time.strftime("%H:%M:%S")
            st = self.get_draft_status()
            if st['picks_until_mine'] <= 2:
                self.precompute_suggestions_async()

    def undo_last_pick(self):
        with self.lock:
            if not self.pick_history:
                return None
            pid, team_idx, is_mine = self.pick_history.pop()
            self.available_player_ids.add(pid)
            if team_idx in self.rosters and pid in self.rosters[team_idx]:
                self.rosters[team_idx].remove(pid)
            if is_mine and pid in self.my_roster:
                self.my_roster.remove(pid)
            return pid, team_idx, is_mine

    def sync_external_picks(self, ordered_picks, source="yahoo_live"):
        """
        Idempotently synchronizes an ordered list of picks from Yahoo Live Draft (Browser Bridge or OAuth API).
        Each item in ordered_picks can be:
          - a player name or ID string/int (in overall pick order 1..N), OR
          - a dict {'pick': int, 'player_name': str, 'player_id': int, 'team_idx': Optional[int]}
        Only applies newly arrived picks beyond len(self.pick_history), preserving manual CLI compatibility.
        Returns a list of newly applied (overall_pick, pid, player_name, team_idx, is_mine) events.
        """
        applied_events = []
        with self.lock:
            already_picked_set = {pid for pid, _, _ in self.pick_history}
            current_count = len(self.pick_history)

            normalized_list = []
            for idx, item in enumerate(ordered_picks):
                if isinstance(item, dict):
                    p_num = int(item.get('pick', idx + 1))
                    p_query = item.get('player_id') or item.get('player_name') or item.get('name')
                    t_idx = item.get('team_idx', None)
                else:
                    p_num = idx + 1
                    p_query = item
                    t_idx = None
                normalized_list.append((p_num, p_query, t_idx))

            normalized_list.sort(key=lambda x: x[0])

            for p_num, p_query, explicit_t_idx in normalized_list:
                if p_num <= current_count:
                    existing_pid, existing_t_idx, existing_is_mine = self.pick_history[p_num - 1]
                    if existing_pid < 0:
                        resolved_pid = self._resolve_exact_for_sync(p_query)
                        if resolved_pid and resolved_pid not in already_picked_set:
                            self.available_player_ids.discard(resolved_pid)
                            if existing_t_idx in self.rosters:
                                if existing_pid in self.rosters[existing_t_idx]:
                                    self.rosters[existing_t_idx].remove(existing_pid)
                                self.rosters[existing_t_idx].append(resolved_pid)
                            if existing_is_mine:
                                if existing_pid in self.my_roster:
                                    self.my_roster.remove(existing_pid)
                                self.my_roster.append(resolved_pid)
                            self.pick_history[p_num - 1] = (resolved_pid, existing_t_idx, existing_is_mine)
                            already_picked_set.discard(existing_pid)
                            already_picked_set.add(resolved_pid)
                            self.unresolved_picks = [(p, q, t) for p, q, t in self.unresolved_picks if p != p_num]
                            p_name = self.players[resolved_pid].name if resolved_pid in self.players else str(resolved_pid)
                            applied_events.append((p_num, resolved_pid, p_name, existing_t_idx, existing_is_mine))
                            print(f"\n[GÜNCELLEME] Geçici yer tutucu (Pick #{p_num}) gerçek oyuncuyla güncellendi: {p_name} (Slot #{existing_t_idx + 1})")
                    continue
                if p_num > current_count + 1:
                    # Fill missing gap picks with placeholders to preserve snake order without stalling
                    for missing_p in range(current_count + 1, p_num):
                        t_idx = self._snake_team_for_pick(missing_p)
                        placeholder_pid = -int(missing_p)
                        self.unresolved_picks.append((missing_p, f"AutoGap #{missing_p}", t_idx))
                        is_m = (t_idx == self.my_team_idx)
                        if is_m:
                            self.draft_player(placeholder_pid, team_idx=t_idx, source=source)
                        else:
                            self.pick_player(placeholder_pid, team_idx=t_idx, source=source)
                        already_picked_set.add(placeholder_pid)
                        current_count = len(self.pick_history)
                        applied_events.append((current_count, placeholder_pid, f"?? Pick #{missing_p}", t_idx, is_m))
                        print(f"\n[BİLGİ] Boşluk dolduruldu: Pick #{missing_p} (Slot #{t_idx + 1}) geçici yer tutucu atandı.")

                pid = self._resolve_exact_for_sync(p_query)
                inferred_t_idx = explicit_t_idx if explicit_t_idx is not None else self._snake_team_for_pick(p_num)

                if pid is None or pid in already_picked_set:
                    # Placeholder keeps the pick count (and thus every later team assignment) correct.
                    pid = -int(p_num)
                    self.unresolved_picks.append((p_num, str(p_query), inferred_t_idx))
                    print(f"\n[UYARI] Pick #{p_num} eşleşmedi: '{p_query}' (Slot #{inferred_t_idx + 1}). "
                          f"Yer tutucu eklendi; gerekirse 'undo' + elle 'pick' ile düzeltin.")

                is_mine = (inferred_t_idx == self.my_team_idx)
                if is_mine:
                    self.draft_player(pid, team_idx=inferred_t_idx, source=source)
                else:
                    self.pick_player(pid, team_idx=inferred_t_idx, source=source)

                already_picked_set.add(pid)
                current_count = len(self.pick_history)
                p_name = self.players[pid].name if pid in self.players else f"?? {p_query}"
                applied_events.append((current_count, pid, p_name, inferred_t_idx, is_mine))

        return applied_events

    def _snake_team_for_pick(self, p_num):
        round_num = ((p_num - 1) // self.num_teams) + 1
        turn_in_round = (p_num - 1) % self.num_teams
        return turn_in_round if round_num % 2 != 0 else (self.num_teams - 1) - turn_in_round

    def _resolve_exact_for_sync(self, p_query):
        """Exact (accent/suffix-normalized) match. Supports Full Name, 'LastName, FirstName', 'Initial. LastName', nicknames, and prefix matching for truncated names."""
        if p_query is None:
            return None
        import re
        q = str(p_query).strip()
        if q.isdigit():
            pid = int(q)
            return pid if pid in self.players else None

        # Strip trailing parenthesized position/team info, e.g. '(C - DEN)', '(PG,SG - OKC)', '(DEN)'
        NBA_TEAMS = r'ATL|BOS|BKN|BRK|CHA|CHI|CLE|DAL|DEN|DET|GSW|GS|HOU|IND|LAC|LAL|MEM|MIA|MIL|MIN|NOP|NO|NYK|NY|OKC|ORL|PHI|PHX|PHO|POR|SAC|SAS|SA|TOR|UTA|UTH|WAS'
        q = re.sub(r'\s*\([^)]*\)\s*$', '', q).strip()
        q = re.sub(rf'\s+(?:(?:PG|SG|SF|PF|C|UTIL|G|F)[,\/\s]*)*[\-\|·]?\s*(?:{NBA_TEAMS})$', '', q, flags=re.IGNORECASE).strip()
        q = re.sub(rf'\s+[\-\|·]?\s*(?:{NBA_TEAMS})$', '', q, flags=re.IGNORECASE).strip()
        q = re.sub(r'\s+(?:PG|SG|SF|PF|C|UTIL|G|F)(?:[,\/](?:PG|SG|SF|PF|C|UTIL|G|F))*$', '', q, flags=re.IGNORECASE).strip()
        # Clean ellipsis and trailing dots (e.g. 'SHAI GILGEOUS-ALEXA...', 'ANT EDW...')
        q = re.sub(r'[\.\s…]+$', '', q).strip()

        if not hasattr(self, '_exact_name_index'):
            import unicodedata
            def _norm(s):
                s_clean = ''.join(
                    c for c in unicodedata.normalize('NFD', str(s).lower())
                    if unicodedata.category(c) != 'Mn'
                )
                for suffix in (' jr.', ' jr', ' sr.', ' sr', ' iii', ' ii', ' iv'):
                    if s_clean.endswith(suffix):
                        s_clean = s_clean[:-len(suffix)].strip()
                return s_clean.replace('.', '').replace("'", "").replace('-', ' ').strip()
            self._norm_name = _norm
            index = {}
            for pid in self.df_base.index:
                index.setdefault(_norm(self.df_base.loc[pid]['NAME']), []).append(int(pid))
            self._exact_name_index = index

        # 1. Direct normalized match
        nq = self._norm_name(q)
        matches = self._exact_name_index.get(nq, [])
        avail = [m for m in matches if m in self.available_player_ids]
        if len(avail) == 1:
            return avail[0]
        elif len(avail) > 1:
            avail_sorted = sorted(avail, key=lambda p: self.df_base.loc[p]['BASE_Z'] if p in self.df_base.index else -999, reverse=True)
            return avail_sorted[0]

        # 2. Reverse 'LastName, FirstName' format
        if ',' in q:
            parts = [p.strip() for p in q.split(',', 1)]
            rev_q = f"{parts[1]} {parts[0]}"
            matches_rev = self._exact_name_index.get(self._norm_name(rev_q), [])
            avail_rev = [m for m in matches_rev if m in self.available_player_ids]
            if len(avail_rev) == 1:
                return avail_rev[0]
            elif len(avail_rev) > 1:
                avail_sorted = sorted(avail_rev, key=lambda p: self.df_base.loc[p]['BASE_Z'] if p in self.df_base.index else -999, reverse=True)
                return avail_sorted[0]

        # 3. 'FirstInitial. LastName' format (e.g. 'N. Jokic', 'L. Doncic', 'V. Wembanyama', 'A. Edwards', 'K. Towns')
        q_tokens = nq.split()
        if len(q_tokens) >= 2 and len(q_tokens[0]) == 1:
            init = q_tokens[0]
            last = ' '.join(q_tokens[1:])
            cand = []
            for pid in self.available_player_ids:
                if pid not in self.players:
                    continue
                p_tokens = self._norm_name(self.players[pid].name).split()
                if p_tokens and p_tokens[0].startswith(init) and (' '.join(p_tokens[1:]) == last or p_tokens[-1] == last or ' '.join(p_tokens[1:]).endswith(' ' + last)):
                    cand.append(pid)
            if len(cand) == 1:
                return cand[0]
            elif len(cand) > 1:
                cand_sorted = sorted(cand, key=lambda p: self.df_base.loc[p]['BASE_Z'] if p in self.df_base.index else -999, reverse=True)
                return cand_sorted[0]

        # 4. Nickname Expansion & Prefix Matching (e.g. 'Ant Edw' -> 'Anthony Edwards', 'Shai Gilgeous-Alexa' -> 'Shai Gilgeous-Alexander')
        COMMON_NICKNAMES = {
            'ant': 'anthony',
            'steph': 'stephen',
            'bub': 'carlton',
            'herb': 'herbert',
            'cam': 'cameron',
            'tre': 'trey',
        }
        tokens = nq.split()
        if tokens and tokens[0] in COMMON_NICKNAMES:
            tokens[0] = COMMON_NICKNAMES[tokens[0]]
            nq = ' '.join(tokens)

        matches_nick = self._exact_name_index.get(nq, [])
        avail_nick = [m for m in matches_nick if m in self.available_player_ids]
        if len(avail_nick) == 1:
            return avail_nick[0]

        if len(nq) >= 5:
            prefix_cands = []
            for norm_name, pids in self._exact_name_index.items():
                if norm_name.startswith(nq):
                    for pid in pids:
                        if pid in self.available_player_ids:
                            prefix_cands.append(pid)
            if len(prefix_cands) == 1:
                return prefix_cands[0]
            elif len(prefix_cands) > 1:
                cands_sorted = sorted(prefix_cands, key=lambda p: self.df_base.loc[p]['BASE_Z'] if p in self.df_base.index else -999, reverse=True)
                return cands_sorted[0]

        # 5. Last-Name Only Match (e.g. 'Jokic', 'Wembanyama', 'Doncic', 'Antetokounmpo')
        if len(nq) >= 4 and ' ' not in nq:
            last_cands = []
            for pid in self.available_player_ids:
                if pid not in self.players:
                    continue
                p_tokens = self._norm_name(self.players[pid].name).split()
                if p_tokens and (p_tokens[-1] == nq or ' '.join(p_tokens[1:]) == nq):
                    last_cands.append(pid)
            if len(last_cands) == 1:
                return last_cands[0]
            elif len(last_cands) > 1:
                last_sorted = sorted(last_cands, key=lambda p: self.df_base.loc[p]['BASE_Z'] if p in self.df_base.index else -999, reverse=True)
                return last_sorted[0]

        return None  # 0 or ambiguous (same-name players) -> caller adds placeholder


def interactive_loop():
    assistant = LiveDraftAssistant(prior_season="2025_26", my_team_idx=7, num_teams=14)
    bridge_mgr = None
    try:
        from yahoo_draft_sync import YahooLiveDraftBridgeManager
        bridge_mgr = YahooLiveDraftBridgeManager(assistant, host="127.0.0.1", port=8765)
        bridge_mgr.start_background_services()
    except Exception as e:
        print(f"[UYARI] Yahoo Canlı Senkron modülü başlatılamadı ({e}). Manuel CLI modu aktif.")

    print("\n======================================================================")
    print("  YAHOO 2026-27 NBA FANTASY 9-CAT H2H LIVE DRAFT ASSISTANT (14-TAKIM, SLOT #8)")
    print("======================================================================")
    print(f"Aktif Havuz: {len(assistant.available_player_ids)} oyuncu | Takım Sayısı: {assistant.num_teams} | Takvim: 2026-27 NBA Normal Sezon")
    if bridge_mgr is not None:
        oauth_st = "AKTİF" if bridge_mgr.oauth_client.is_configured() else "Pasif (Tarayıcı Köprüsü Aktif)"
        print("🟢 CANLI YAHOO KÖPRÜSÜ & DASHBOARD : http://127.0.0.1:8765")
        print(f"🟢 YAHOO OAUTH2 REST API POLLER    : {oauth_st}")
    print("\nManuel Yedek & Kontrol Komutları (Canlı Otomasyonla Eşzamanlı Çalışır):")
    print("  suggest               : Sıradaki seçimin için En İyi 10 Oyuncu (Hızlı Pairwise H2H Rollout).")
    print("  fast                  : <1ms Anlık Marjinal Z-Skor Önerisi (Acil 3 saniye durumu için).")
    print("  pick <isim veya ID>   : Sıradaki takımın seçtiği oyuncuyu elle işle (Yılan sırasını takip eder).")
    print("  my_pick <isim veya ID>: Kendi seçtiğin oyuncuyu kadrona elle ekle (Slot #8).")
    print("  sync                  : Yahoo API'den anlık seçimleri şimdi çek ve senkronize et.")
    print("  undo                  : Son yapılan seçimi geri al.")
    print("  board [N]             : Kalan en yüksek Z-Skorlu N oyuncuyu hızlı listele (varsayılan 15).")
    print("  roster                : Kendi mevcut kadronu ve kategori ağırlıklarını gör.")
    print("  search <isim>         : İsimle oyuncu ara.")
    print(f"  pos <1-{assistant.num_teams}>            : Draft sıranı değiştir (Varsayılan: 8).")
    print("  punt <kat1> <kat2>    : Manuel punt kategorisi belirle (Örn: punt FT TOV).")
    print("  injury list           : Tüm aktif sakatlıkları ve durumları listele.")
    print("  injury set <DURUM> <isim> [aciklama] : Sakatlık/dinlenme ata (Örn: injury set OUT kawhi [diz]).")
    print("  injury clear <isim>   : Oyuncunun sakatlık kaydını temizle (Sağlıklı yap).")
    print("  exit                  : Çıkış.")

    while True:
        st = assistant.get_draft_status()
        turn_tag = f">>> SENİN SIRAN (SLOT #{st['my_slot']})! <<<" if st['is_my_turn'] else f"Sıradaki: Slot #{st['on_clock_slot']} ({st['picks_until_mine']} seçim sonra sen)"
        prompt_str = f"\n[Pick #{st['overall_pick']} | R{st['round']}.{st['pick_in_round']} | {turn_tag}]\nDraft> "
        raw_line = input(prompt_str).strip()
        if not raw_line:
            continue

        cmd = raw_line.split()
        action = cmd[0].lower()

        if action == 'exit':
            break
        elif action == 'pos' and len(cmd) > 1:
            if assistant.pick_history:
                print("Draft başladıktan sonra sıra değiştirilemez (kadrolar bozulur). Önce 'undo' ile tüm seçimleri geri alın.")
                continue
            try:
                slot = int(cmd[1])
                if 1 <= slot <= assistant.num_teams:
                    assistant.my_team_idx = slot - 1
                    assistant.precompute_suggestions_async()
                    print(f"Draft sırası Slot #{slot} (team_idx={assistant.my_team_idx}) olarak güncellendi.")
                else:
                    print(f"Lütfen 1 ile {assistant.num_teams} arasında bir sıra girin.")
            except ValueError:
                print("Geçersiz sıra numarası.")
        elif action == 'punt':
            aliases = {'FG%': 'FG', 'FT%': 'FT', '3PM': 'FG3M', '3PTM': 'FG3M', 'TO': 'TOV'}
            valid = set(COUNT_STATS + PERCENTAGE_STATS)
            cats = [aliases.get(c.upper(), c.upper()) for c in cmd[1:]]
            bad = [c for c in cats if c not in valid]
            if bad:
                print(f"Geçersiz kategori: {bad}. Geçerli: {sorted(valid)}")
                continue
            assistant.punt_categories = cats
            assistant.precompute_suggestions_async()
            print(f"Manuel punt kategorileri: {assistant.punt_categories if cats else 'Yok (Otomatik)'}")
        elif action == 'injury':
            if len(cmd) > 1 and cmd[1].lower() == 'list':
                injuries = assistant.injury_tracker.get_all_active_injuries()
                if not injuries:
                    print("Aktif sakatlık kaydı bulunmuyor (Tüm oyuncular sağlıklı).")
                else:
                    df_inj = pd.DataFrame(injuries)
                    print("\n--- AKTİF SAKATLIK VE KULLANILABİLİRLİK LİSTESİ ---")
                    cols = ['player_name', 'team', 'status', 'injury_desc', 'is_b2b_rest', 'updated_at']
                    print(df_inj[cols].to_string(index=False))
            elif len(cmd) > 3 and cmd[1].lower() == 'set':
                status = cmd[2].upper()
                p_query = " ".join(cmd[3:])
                desc = ""
                if "[" in p_query and "]" in p_query:
                    parts = p_query.split("[")
                    p_query = parts[0].strip()
                    desc = parts[1].replace("]", "").strip()
                pid = assistant.resolve_player_id(p_query, only_available=False)
                if pid is None:
                    print(f"Oyuncu bulunamadı: '{p_query}'")
                else:
                    pname = assistant.players[pid].name if pid in assistant.players else p_query
                    tname = assistant.team_abbr_dict.get(pid, 'NBA')
                    is_b2b = (status == 'B2B_REST')
                    assistant.injury_tracker.set_injury(pid, pname, status, team=tname, desc=desc, is_b2b_rest=is_b2b)
                    if pid in assistant.players:
                        assistant.players[pid].update_injury_status(status, desc=desc, is_b2b_rest=is_b2b)
                    print(f"[SAKATLIK GÜNCELLENDİ] {pname} ({tname}) -> {status} {f'({desc})' if desc else ''}")
            elif len(cmd) > 2 and cmd[1].lower() == 'clear':
                p_query = " ".join(cmd[2:])
                pid = assistant.resolve_player_id(p_query, only_available=False)
                if pid is None:
                    print(f"Oyuncu bulunamadı: '{p_query}'")
                else:
                    pname = assistant.players[pid].name if pid in assistant.players else p_query
                    assistant.injury_tracker.clear_injury(pid)
                    if pid in assistant.players:
                        assistant.players[pid].update_injury_status('HEALTHY')
                    print(f"[SAĞLIKLI] {pname} sakatlık kaydı temizlendi.")
            else:
                print("Kullanım:")
                print("  injury list")
                print("  injury set <STATUS> <isim> [aciklama]  (Örn: injury set OUT kawhi leonard [diz dinlendirme])")
                print("  injury clear <isim>                   (Örn: injury clear kawhi leonard)")
        elif action == 'suggest':
            df_sug = assistant.rank_available_players()
            elapsed_ms = df_sug.attrs.get('elapsed_ms', 0.0)
            print(f"\n--- EN İYİ SEÇİM ÖNERİLERİ (Tur {len(assistant.my_roster)+1} | Slot #{assistant.my_team_idx+1} | Süre: {elapsed_ms:.0f} ms) ---")
            cols = ['ID', 'NAME', 'TEAM', 'POS', 'WIN_PROB_SCORE', 'FAST_SCORE', 'BASE_Z', 'Active_Punts']
            print(df_sug[cols].head(10).to_string(index=False))
        elif action == 'fast':
            t0 = time.perf_counter()
            df_fast = assistant.get_fast_suggestions(top_n=10)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            print(f"\n--- ANLIK HIZLI ÖNERİ (Tur {len(assistant.my_roster)+1} | Süre: {dt_ms:.2f} ms) ---")
            cols = ['ID', 'NAME', 'TEAM', 'POS', 'FAST_SCORE', 'BASE_Z', 'Active_Punts']
            print(df_fast[cols].to_string(index=False))
        elif action == 'sync':
            if bridge_mgr and bridge_mgr.oauth_client.is_configured():
                picks = bridge_mgr.oauth_client.fetch_live_draft_picks()
                applied = assistant.sync_external_picks(picks, source="yahoo_oauth_manual_sync")
                print(f"Yahoo API senkronizasyonu tamamlandı: {len(applied)} yeni seçim işlendi.")
            else:
                print("Yahoo OAuth2 yapılandırılmamış (config/yahoo_oauth.json). Tarayıcı Köprüsü (http://127.0.0.1:8765) otomatik dinlemede.")
        elif action == 'board':
            top_n = int(cmd[1]) if len(cmd) > 1 and cmd[1].isdigit() else 15
            avail_in_base = [pid for pid in assistant.available_player_ids if pid in assistant.df_base.index]
            df_b = assistant.df_base.loc[avail_in_base].head(top_n)
            print(f"\n--- MEVCUT EN İYİ {top_n} OYUNCU (BASE Z-SCORE) ---")
            print(df_b[['NAME', 'TEAM', 'POS', 'EXP_MIN', 'AVAIL', 'BASE_Z']].to_string())
        elif action == 'pick' and len(cmd) > 1:
            query = " ".join(cmd[1:])
            pid = assistant.resolve_player_id(query, only_available=True)
            if pid is None:
                print(f"Oyuncu bulunamadı veya zaten seçildi: '{query}'")
            else:
                on_clock = assistant._infer_current_snake_team_idx()
                p_name = assistant.players[pid].name
                assistant.pick_player(pid, source="manual_cli")
                print(f"[Pick #{st['overall_pick']}] Slot #{on_clock + 1} -> {p_name} ({pid}) seçildi.")
        elif action == 'my_pick' and len(cmd) > 1:
            query = " ".join(cmd[1:])
            pid = assistant.resolve_player_id(query, only_available=True)
            if pid is None:
                print(f"Oyuncu bulunamadı veya zaten seçildi: '{query}'")
            else:
                p_name = assistant.players[pid].name
                assistant.draft_player(pid, source="manual_cli")
                print(f">>> KADRONA EKLENDİ (Slot #{assistant.my_team_idx + 1}): {p_name} ({pid}) <<<")
        elif action == 'undo':
            res = assistant.undo_last_pick()
            if res is None:
                print("Geri alınacak seçim yok.")
            else:
                pid, t_idx, is_mine = res
                p_name = assistant.players[pid].name if pid in assistant.players else str(pid)
                print(f"Son seçim geri alındı: {p_name} (Slot #{t_idx + 1})")
        elif action == 'roster':
            print(f"\n--- KADRON (Slot #{assistant.my_team_idx + 1} | {len(assistant.my_roster)}/13 Oyuncu) ---")
            for idx_p, pid in enumerate(assistant.my_roster, 1):
                name = assistant.players[pid].name if pid in assistant.players else str(pid)
                pos = assistant.pos_dict.get(pid, 'UTIL')
                tm = assistant.team_abbr_dict.get(pid, 'NBA')
                print(f"  {idx_p:2d}. {name} ({tm} - {pos}) [ID: {pid}]")
            if assistant.my_roster:
                weights, win_probs = assistant._compute_marginal_category_weights(assistant.my_roster)
                wp_str = " | ".join(f"{k}: %{v*100:.0f}" for k, v in win_probs.items())
                print(f"\nTahmini Kategori Kazanma Olasılıkları (Tur Bazlı Kohort): {wp_str}")
        elif action == 'search' and len(cmd) > 1:
            query = " ".join(cmd[1:]).lower()
            found = []
            for pid, bp in assistant.players.items():
                if query in bp.name.lower():
                    pos = assistant.pos_dict.get(pid, 'N/A')
                    tm = assistant.team_abbr_dict.get(pid, 'NBA')
                    status = "MÜSAİT" if pid in assistant.available_player_ids else "SEÇİLDİ"
                    found.append(f"{pid}: {bp.name} ({tm} - {pos}) [{status}]")
            print("\nArama Sonuçları:")
            for f in found[:20]:
                print(" ", f)
        else:
            print("Bilinmeyen komut. Komutlar: suggest, fast, pick <isim/id>, my_pick <isim/id>, sync, undo, board, roster, search <isim>, pos <1-12>, punt <kat>, exit")


if __name__ == "__main__":
    interactive_loop()

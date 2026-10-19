import os
import math
import pandas as pd
import numpy as np
from functools import lru_cache
from scipy.optimize import linear_sum_assignment

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

COUNT_STATS = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG3M']
PERCENTAGE_STATS = ['FG', 'FT']
ALL_CATEGORIES = COUNT_STATS + ['FGM', 'FGA', 'FTM', 'FTA']

REQUIRED_SLOTS = ['PG', 'SG', 'G', 'SF', 'PF', 'F', 'C', 'C', 'UTIL', 'UTIL']
MAX_ROSTER_SIZE = 13
INFEASIBLE_COST = 1e9

# Category-specific weekly variance calibration / temperature factors (fixes Rapor 1 / K3)
# Captures unmodeled cross-game / team-pace / opponent defense weekly shocks
WEEKLY_VAR_INFLATION_BY_CAT = {
    'PTS': 1.45,
    'REB': 1.55,
    'AST': 1.30,
    'STL': 1.15,
    'BLK': 1.25,
    'FG3M': 1.35,
    'TOV': 1.25,
    'FG': 1.30,
    'FT': 1.25,
}


def norm_cdf(z):
    """Standard Normal Cumulative Distribution Function Phi(z)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def norm_pdf(z):
    """Standard Normal Probability Density Function phi(z) = d/dz Phi(z)."""
    return math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


@lru_cache(maxsize=None)
def map_position_to_slots(pos_str):
    """Map an NBA API position (e.g. 'G-F' or 'Guard-Forward') to eligible Yahoo active slots."""
    slots = ['UTIL']
    pos_str = str(pos_str).upper().strip()
    tokens = [t.strip() for t in pos_str.replace('/', '-').split('-')]
    for tok in tokens:
        if tok in ('G', 'GUARD', 'PG', 'SG'):
            slots.extend(['PG', 'SG', 'G'])
        elif tok in ('F', 'FORWARD', 'SF', 'PF'):
            slots.extend(['SF', 'PF', 'F'])
        elif tok in ('C', 'CENTER'):
            slots.extend(['C'])
    if len(slots) == 1:
        if 'G' in pos_str:
            slots.extend(['PG', 'SG', 'G'])
        if 'F' in pos_str:
            slots.extend(['SF', 'PF', 'F'])
        if 'C' in pos_str:
            slots.extend(['C'])
    if len(slots) == 1:
        slots.extend(['PG', 'SG', 'G', 'SF', 'PF', 'F', 'C'])
    return tuple(sorted(set(slots)))


@lru_cache(maxsize=None)
def _slot_eligibility_mask(pos_str):
    eligible = set(map_position_to_slots(pos_str))
    return tuple(slot in eligible for slot in REQUIRED_SLOTS)


@lru_cache(maxsize=None)
def can_fill_roster_cached(pos_tuple):
    n_players = len(pos_tuple)
    if n_players == 0:
        return True
    if n_players > MAX_ROSTER_SIZE:
        return False

    target_active = min(n_players, len(REQUIRED_SLOTS))
    cost_matrix = np.full((n_players, len(REQUIRED_SLOTS)), INFEASIBLE_COST, dtype=np.float64)

    for i, pos_str in enumerate(pos_tuple):
        mask = _slot_eligibility_mask(pos_str)
        for j, is_ok in enumerate(mask):
            if is_ok:
                cost_matrix[i, j] = -1.0

    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    valid_matches = int(np.sum(cost_matrix[row_ind, col_ind] < 0.0))
    return valid_matches >= target_active


def can_fill_roster(players):
    pos_tuple = tuple(sorted(str(p.get('POS', 'UTIL')) for p in players))
    return can_fill_roster_cached(pos_tuple)


def get_optimal_daily_lineup(available_players, category_weights, p_ref_fg=0.47, p_ref_ft=0.78):
    """
    Optimizes daily lineup of up to 10 active players using Linear Assignment
    across all 9 categories with consistent reference percentages (fixes Rapor 2 / §5).
    """
    if not available_players:
        return []

    n_players = len(available_players)
    n_slots = len(REQUIRED_SLOTS)
    cost_matrix = np.full((n_players, n_slots), INFEASIBLE_COST, dtype=np.float64)

    for i, p in enumerate(available_players):
        score = 0.0
        proj = p.get('PROJ', {})
        for stat, weight in category_weights.items():
            if stat == 'TOV':
                score -= proj.get('TOV', 0.0) * weight
            elif stat in ('FG', 'FG_PCT'):
                fg_imp = proj.get('FGM', 0.0) - p_ref_fg * proj.get('FGA', 0.0)
                score += fg_imp * weight
            elif stat in ('FT', 'FT_PCT'):
                ft_imp = proj.get('FTM', 0.0) - p_ref_ft * proj.get('FTA', 0.0)
                score += ft_imp * weight
            else:
                score += proj.get(stat, 0.0) * weight

        pos_str = p.get('POS', 'UTIL')
        mask = _slot_eligibility_mask(pos_str)
        shifted_score = score + 1e4
        for j, is_ok in enumerate(mask):
            if is_ok:
                cost_matrix[i, j] = -shifted_score

    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    best_lineup = [
        available_players[r]
        for r, c in zip(row_ind, col_ind)
        if cost_matrix[r, c] < INFEASIBLE_COST / 2.0
    ]
    return best_lineup


class MatchupEngine:
    def __init__(self, bayesian_players_dict, df_schedule, df_positions, season="2024_25", prior_season="2024_25"):
        self.players = bayesian_players_dict
        self.schedule = df_schedule.copy() if df_schedule is not None and not df_schedule.empty else pd.DataFrame()
        if not self.schedule.empty and 'GAME_DATE' in self.schedule.columns:
            self.schedule['GAME_DATE'] = pd.to_datetime(self.schedule['GAME_DATE']).dt.normalize()

        if df_positions is not None and not df_positions.empty:
            if 'PLAYER_ID' in df_positions.columns:
                self.pos_dict = df_positions.set_index('PLAYER_ID')['POSITION'].to_dict()
            else:
                self.pos_dict = df_positions['POSITION'].to_dict()
        else:
            self.pos_dict = {}

        self.season = season
        self.prior_season = prior_season
        # Initialize team_map strictly from prior_season (keep='last') or target season's FIRST game
        # to eliminate look-ahead leakage of mid-season trades (fixes Rapor 2 / L7)
        self.team_map = self._load_leak_free_team_map(prior_season, season)
        self.default_norm_weights = self._compute_pool_unit_weights()

    def _compute_pool_unit_weights(self):
        if not self.players:
            return {stat: 1.0 for stat in COUNT_STATS + PERCENTAGE_STATS}
        sample_stats = {s: [] for s in COUNT_STATS + PERCENTAGE_STATS}
        for bp in self.players.values():
            preds = bp.predict_next_game(projected_minutes=None)
            for s in COUNT_STATS:
                sample_stats[s].append(preds[s]['mean'])
            sample_stats['FG'].append(preds['FG']['mean'] - 0.47 * preds['FG']['attempts'])
            sample_stats['FT'].append(preds['FT']['mean'] - 0.78 * preds['FT']['attempts'])

        weights = {}
        for s, vals in sample_stats.items():
            std = float(np.std(vals)) if len(vals) > 1 else 1.0
            weights[s] = 1.0 / max(std, 0.25)
        return weights

    def _load_leak_free_team_map(self, prior_season, target_season):
        """
        Loads player -> team mapping without look-ahead leakage:
          1. End of prior_season (known before target_season starts)
          2. First game appearance in target_season for rookies/offseason movers (keep='first', NOT 'last')
        """
        team_map = {}
        prior_path = os.path.join(DATA_DIR, 'raw', f'player_logs_{prior_season}.parquet')
        if os.path.exists(prior_path):
            df_prior = pd.read_parquet(prior_path, columns=['PLAYER_ID', 'TEAM_ID', 'GAME_DATE'])
            df_prior = df_prior.sort_values('GAME_DATE')
            team_map.update(
                df_prior.drop_duplicates(subset=['PLAYER_ID'], keep='last').set_index('PLAYER_ID')['TEAM_ID'].to_dict()
            )

        target_path = os.path.join(DATA_DIR, 'raw', f'player_logs_{target_season}.parquet')
        if os.path.exists(target_path):
            df_target = pd.read_parquet(target_path, columns=['PLAYER_ID', 'TEAM_ID', 'GAME_DATE'])
            df_target = df_target.sort_values('GAME_DATE')
            first_map = df_target.drop_duplicates(subset=['PLAYER_ID'], keep='first').set_index('PLAYER_ID')['TEAM_ID'].to_dict()
            # Update offseason team changes and rookies from their initial team at start of target season
            team_map.update(first_map)
        elif target_season == "2026_27" or prior_season == "2025_26":
            roster_26_path = os.path.join(DATA_DIR, 'processed', 'active_roster_2026_27.parquet')
            if os.path.exists(roster_26_path):
                df_r26 = pd.read_parquet(roster_26_path)
                df_r26 = df_r26[df_r26['TEAM_ID'] > 0]
                team_map.update(df_r26.set_index('PLAYER_ID')['TEAM_ID'].to_dict())

        return {int(k): int(v) for k, v in team_map.items()}

    def _get_player_schedule(self, team_id, start_date, end_date):
        if self.schedule.empty or team_id is None:
            return set()
        start_ts = pd.to_datetime(start_date).normalize()
        end_ts = pd.to_datetime(end_date).normalize()
        mask = (
            (self.schedule['TEAM_ID'] == team_id)
            & (self.schedule['GAME_DATE'] >= start_ts)
            & (self.schedule['GAME_DATE'] <= end_ts)
        )
        return set(self.schedule.loc[mask, 'GAME_DATE'].tolist())

    def _build_player_game_projection(self, pid, target_minutes=None, current_date=None):
        bp = self.players[pid]
        proj = bp.predict_next_game(projected_minutes=target_minutes, current_date=current_date)

        flat_mean = {}
        flat_var = {}
        for stat in COUNT_STATS:
            flat_mean[stat] = proj.get(stat, {}).get('mean', 0.0)
            flat_var[stat] = proj.get(stat, {}).get('variance', 0.0)

        for stat in PERCENTAGE_STATS:
            makes = proj.get(stat, {}).get('mean', 0.0)
            attempts = proj.get(stat, {}).get('attempts', 10.0)
            var_makes = proj.get(stat, {}).get('variance', 0.0)
            cond_var_makes = proj.get(stat, {}).get('cond_variance', var_makes)
            var_attempts = proj.get(stat, {}).get('attempts_var', 0.0)
            rate = proj.get(stat, {}).get('rate', 0.0)

            flat_mean[f'{stat}M'] = makes
            flat_mean[f'{stat}A'] = attempts
            flat_mean[f'{stat}_rate'] = rate
            flat_var[f'{stat}M'] = var_makes
            flat_var[f'{stat}M_cond'] = cond_var_makes
            flat_var[f'{stat}A'] = var_attempts

        return flat_mean, flat_var

    def get_expected_weekly_distribution(self, roster_ids, start_date=None, end_date=None, category_weights=None):
        """
        Evaluates a roster's optimal weekly output (both Mean and Calibrated Predictive Variance):
          - Uses consecutive_dnps-aware effective availability (fixes Rapor 1 / K2 & K4)
          - Models autocorrelated multi-game injury/availability variance g^2 * p * (1-p) (fixes Rapor 1 / K3)
          - Tracks per-player percentage heterogeneity for exact Jensen-free impact variance (fixes Rapor 1 / K13)
        """
        if start_date is not None and end_date is not None and not self.schedule.empty:
            dates = pd.date_range(pd.to_datetime(start_date).normalize(), pd.to_datetime(end_date).normalize())
        else:
            dates = []

        if category_weights is None:
            category_weights = self.default_norm_weights

        ref_date = pd.to_datetime(start_date).normalize() if start_date is not None else None

        data = {}
        for pid in roster_ids:
            if pid not in self.players:
                continue
            bp = self.players[pid]
            # Only pass ref_date for idle-days decay if within 14 days of last_game_date (live in-season tracking);
            # prevents 150-day artificial prior decay when forecasting future schedule weeks before season start
            eff_ref_date = ref_date
            if eff_ref_date is not None and getattr(bp, 'last_game_date', None) is not None:
                if (eff_ref_date - pd.to_datetime(bp.last_game_date).normalize()).days > 14:
                    eff_ref_date = None
            flat_mean, flat_var = self._build_player_game_projection(pid, target_minutes=None, current_date=eff_ref_date)
            tid = self.team_map.get(pid)
            sched_dates = self._get_player_schedule(tid, start_date, end_date) if len(dates) > 0 else set()
            # Use injury-conditioned effective availability when evaluating in-season weeks (fixes K2/K4)
            eff_avail = (
                bp.get_effective_game_availability()
                if start_date is not None
                else getattr(bp, 'availability_rate', 0.85)
            )
            data[pid] = {
                'ID': pid,
                'POS': self.pos_dict.get(pid, 'UTIL'),
                'PROJ': flat_mean,
                'VAR': flat_var,
                'AVAIL': eff_avail,
                'CONSEC_DNPS': getattr(bp, 'consecutive_dnps', 0),
                'SCHEDULE': sched_dates,
                'STARTED_GAMES': 0.0,
            }

        var_keys = ALL_CATEGORIES + ['FGM_cond', 'FTM_cond']
        week_mean = {cat: 0.0 for cat in ALL_CATEGORIES}
        week_var = {cat: 0.0 for cat in var_keys}

        if len(dates) == 0:
            # Season-wide expected weekly evaluation (fixes Rapor 1 / K6: realistic 2.35 games/week for bench slots)
            all_p = list(data.values())
            best_starters = get_optimal_daily_lineup(all_p, category_weights)
            starter_ids = {p['ID'] for p in best_starters}
            bench_players = [p for p in all_p if p['ID'] not in starter_ids]

            for p in best_starters:
                p['STARTED_GAMES'] = 3.35
            for p in bench_players[:3]:
                p['STARTED_GAMES'] = 2.35
        else:
            for current_date in dates:
                # Match the simulator's prematch lineup rule: exclude players known to be out (consecutive_dnps >= 2)
                playing_today = [
                    p for p in data.values()
                    if current_date in p['SCHEDULE'] and p['CONSEC_DNPS'] < 2
                ]
                if not playing_today:
                    continue
                best_lineup = get_optimal_daily_lineup(playing_today, category_weights)
                for p in best_lineup:
                    p['STARTED_GAMES'] += 1.0

        # Accumulate weekly mean and autocorrelated weekly variance across each player's started games
        player_Breakdown = []
        for p in data.values():
            g = p['STARTED_GAMES']
            if g <= 0:
                continue
            p_avail = p['AVAIL']
            exp_gp = g * p_avail
            # Autocorrelated weekly availability variance: injuries span multiple games in a week,
            # so Var(N_played) ≈ (0.35 * g + 0.65 * g^2) * p_avail * (1 - p_avail) (fixes Rapor 1 / K3)
            var_gp = (0.35 * g + 0.65 * (g ** 2)) * p_avail * (1.0 - p_avail)

            for cat in ALL_CATEGORIES:
                mu_g = p['PROJ'][cat]
                week_mean[cat] += mu_g * exp_gp
                week_var[cat] += exp_gp * p['VAR'][cat] + var_gp * (mu_g ** 2)

            for ck in ('FGM_cond', 'FTM_cond'):
                week_var[ck] += exp_gp * p['VAR'][ck]

            player_Breakdown.append({
                'exp_gp': exp_gp,
                'var_gp': var_gp,
                'FG_rate': p['PROJ']['FG_rate'],
                'FGA_mean': p['PROJ']['FGA'],
                'FGA_var': p['VAR']['FGA'],
                'FT_rate': p['PROJ']['FT_rate'],
                'FTA_mean': p['PROJ']['FTA'],
                'FTA_var': p['VAR']['FTA'],
            })

        return {'mean': week_mean, 'var': week_var, 'players': player_Breakdown}

    def get_expected_weekly_stats(self, roster_ids, start_date=None, end_date=None, category_weights=None):
        dist = self.get_expected_weekly_distribution(roster_ids, start_date, end_date, category_weights=category_weights)
        return dist['mean']

    @staticmethod
    def _compute_team_pct_impact_var(dist, stat, p_ref):
        """
        Computes exact player-level impact variance sum_i E[Var(M_i|A_i)] + (p_i - p_ref)^2 Var(A_i_week)
        avoiding team-level Jensen loss (fixes Rapor 1 / K13).
        """
        m_key, a_key = f'{stat}M', f'{stat}A'
        cond_key = f'{stat}M_cond'
        base_cond_var = dist['var'].get(cond_key, dist['var'].get(m_key, 0.0))

        players_list = dist.get('players', [])
        if not players_list:
            my_m, my_a = dist['mean'].get(m_key, 0.0), dist['mean'].get(a_key, 0.0)
            my_p = my_m / my_a if my_a > 0 else p_ref
            return base_cond_var + ((my_p - p_ref) ** 2) * dist['var'].get(a_key, 0.0)

        att_var_sum = 0.0
        for pb in players_list:
            p_i = pb[f'{stat}_rate']
            mu_a = pb[f'{stat}A_mean']
            var_a_game = pb[f'{stat}A_var']
            var_a_week = pb['exp_gp'] * var_a_game + pb['var_gp'] * (mu_a ** 2)
            att_var_sum += ((p_i - p_ref) ** 2) * var_a_week

        return base_cond_var + att_var_sum

    @classmethod
    def evaluate_h2h_matchup(cls, my_dist, opp_dist):
        """
        Analytical H2H 9-Category Evaluation using Calibrated Gaussian CDF Phi(z).
        """
        my_mean, my_var = my_dist['mean'], my_dist['var']
        opp_mean, opp_var = opp_dist['mean'], opp_dist['var']

        win_probs = {}
        marginal_weights = {}

        # 1. Count Categories
        for stat in COUNT_STATS:
            diff = my_mean.get(stat, 0.0) - opp_mean.get(stat, 0.0)
            if stat == 'TOV':
                diff = -diff

            infl = WEEKLY_VAR_INFLATION_BY_CAT.get(stat, 1.30)
            total_var = max((my_var.get(stat, 0.0) + opp_var.get(stat, 0.0)) * infl, 1e-6)
            sigma = math.sqrt(total_var)
            z = diff / sigma

            win_probs[stat] = norm_cdf(z)
            marginal_weights[stat] = norm_pdf(z) / sigma

        # 2. Percentage Categories via Linearized Net Impact + Player-Level Law of Total Variance
        for stat in PERCENTAGE_STATS:
            m_key, a_key = f'{stat}M', f'{stat}A'

            my_m, my_a = my_mean.get(m_key, 0.0), my_mean.get(a_key, 0.0)
            opp_m, opp_a = opp_mean.get(m_key, 0.0), opp_mean.get(a_key, 0.0)

            total_a = my_a + opp_a
            p_ref = (my_m + opp_m) / total_a if total_a > 0 else (0.47 if stat == 'FG' else 0.78)

            my_impact = my_m - p_ref * my_a
            opp_impact = opp_m - p_ref * opp_a
            diff_impact = my_impact - opp_impact

            infl = WEEKLY_VAR_INFLATION_BY_CAT.get(stat, 1.25)
            my_impact_var = cls._compute_team_pct_impact_var(my_dist, stat, p_ref)
            opp_impact_var = cls._compute_team_pct_impact_var(opp_dist, stat, p_ref)
            total_var = max((my_impact_var + opp_impact_var) * infl, 1e-6)
            sigma = math.sqrt(total_var)

            z = diff_impact / sigma

            cat_name = f'{stat}_PCT'
            win_probs[cat_name] = norm_cdf(z)
            marginal_weights[stat] = norm_pdf(z) / sigma

        expected_wins = sum(win_probs.values())
        return expected_wins, win_probs, marginal_weights

    def simulate_matchup(self, my_roster_ids, opp_roster_ids, start_date, end_date, n_iterations=1000):
        my_dist = self.get_expected_weekly_distribution(my_roster_ids, start_date, end_date)
        opp_dist = self.get_expected_weekly_distribution(opp_roster_ids, start_date, end_date)
        _, win_probs, _ = self.evaluate_h2h_matchup(my_dist, opp_dist)
        return win_probs

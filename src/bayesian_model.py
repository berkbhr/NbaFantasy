import numpy as np
import datetime

# Categories and their groupings
COUNT_STATS = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG3M', 'TOV']
PERCENTAGE_STATS = ['FG', 'FT']  # Handled via FGM/FGA and FTM/FTA

# Empirical Bayes hyperparameter kappa_c (within-to-between variance ratio in minutes):
# weight_player = prior_min / (prior_min + kappa_c)  (fixes Rapor 1 / K9)
EB_KAPPA_MINUTES_BY_STAT = {
    'PTS': 350.0,
    'REB': 320.0,
    'AST': 320.0,
    'FG3M': 420.0,
    'STL': 550.0,
    'BLK': 500.0,
    'TOV': 420.0,
    'FGA': 350.0,
    'FTA': 400.0,
}

# Compound-Poisson / Overdispersion multipliers phi_c (fixes Rapor 1 / K1):
# PTS comes in 2- and 3-point clusters (E[V^2]/E[V] ≈ 2.15), FTA in 2-3 shot trips (≈ 1.85), FGA in rhythm bursts
DISPERSION_PHI_BY_STAT = {
    'PTS': 2.05,
    'REB': 1.02,
    'AST': 1.02,
    'STL': 1.00,
    'BLK': 1.02,
    'FG3M': 1.08,
    'TOV': 1.02,
    'FG': 1.25,
    'FT': 1.85,
}

# Category-specific daily forgetting rates lambda_c (fixes Rapor 1 / K11):
# Skill rates like FT% are much more stable than role-dependent count rates
DECAY_LAMBDA_BY_STAT = {
    'PTS': 0.015,
    'REB': 0.012,
    'AST': 0.015,
    'STL': 0.010,
    'BLK': 0.010,
    'FG3M': 0.012,
    'TOV': 0.014,
    'FG': 0.008,
    'FT': 0.004,
}

MIN_BETA_MINUTES = 60.0
MIN_BETA_ATTEMPTS = 15.0


class BayesianPlayer:
    def __init__(self, player_id, name):
        self.player_id = player_id
        self.name = name

        self.alphas = {}
        self.betas = {}

        self.att_alphas = {}
        self.att_betas = {}

        # Player-specific role & Beta-Bernoulli availability state (fixes Rapor 1 / K7 & K8)
        self.expected_minutes = 20.0
        self.minutes_var = 42.0  # Empirical residual SD ≈ 6.5 mins -> var ≈ 42.25
        self.avail_alpha = 34.0
        self.avail_beta = 6.0
        self.availability_rate = 0.85
        self.consecutive_dnps = 0
        self.injury_status = 'HEALTHY'
        self.injury_desc = ''
        self.is_b2b_rest = False
        self.expected_return = None

        self.last_game_date = None
        self.decay_lambda = 0.015
        self.delta_event = 0.2

    def _resolve_pos_rates(self, positional_averages, pos_str='UTIL'):
        if not positional_averages:
            return {}
        by_pos = positional_averages.get('BY_POS', {})
        pos_upper = str(pos_str).upper()
        matched = []
        for pk in ('G', 'F', 'C'):
            if pk in pos_upper and pk in by_pos:
                matched.append(by_pos[pk])
        if not matched:
            return positional_averages
        if len(matched) == 1:
            return matched[0]
        # Average across multi-positional eligibility (e.g. 'G-F' or 'F-C')
        blended = {}
        for k in matched[0].keys():
            blended[k] = float(np.mean([m.get(k, 0.0) for m in matched]))
        return blended

    def initialize_priors(self, prior_data, positional_averages=None, pos_str='UTIL'):
        """
        Initializes Empirical Bayes conjugate priors with:
          1. Position-specific target rates ('G', 'F', 'C', fixes K10)
          2. True Empirical Bayes shrinkage w = n / (n + kappa_c) and information-scaled ESS (fixes K9)
          3. Beta-Binomial availability tracking updated in-season (fixes K8)
        """
        has_valid_prior = bool(prior_data and prior_data.get('MIN', 0) >= 50)
        prior_min = float(prior_data['MIN']) if has_valid_prior else 0.0
        prior_gp = float(prior_data.get('GP', 0)) if has_valid_prior else 0.0

        pos_rates = self._resolve_pos_rates(positional_averages, pos_str=pos_str)

        # 1. Expected Minutes & Beta-Bernoulli Availability Prior
        replacement_mpg = 18.0
        if prior_min > 0 and prior_gp > 0:
            obs_mpg = prior_min / prior_gp
            w_min = prior_gp / (prior_gp + 8.0)
            self.expected_minutes = float(np.clip(w_min * obs_mpg + (1.0 - w_min) * replacement_mpg, 8.0, 38.0))

            # Beta(alpha, beta) prior for game availability based on prior season out of 82 games
            avail_gp_ref = float(prior_data.get('ROOKIE_AVAIL_GP', prior_gp))
            obs_played = min(82.0, avail_gp_ref)
            obs_missed = max(0.0, 82.0 - obs_played)
            # Blend 25 pseudo-games of league average (0.80) with 0.5x prior season games
            self.avail_alpha = 20.0 + 0.5 * obs_played
            self.avail_beta = 5.0 + 0.5 * obs_missed
            self.availability_rate = float(np.clip(self.avail_alpha / (self.avail_alpha + self.avail_beta), 0.35, 0.96))
        else:
            self.expected_minutes = replacement_mpg
            self.avail_alpha = 15.0
            self.avail_beta = 5.0
            self.availability_rate = 0.75

        # 2. Count Stats Initialization (Empirical Bayes w = n / (n + kappa_c), ESS scaled by prior_min)
        for stat in COUNT_STATS:
            kappa = EB_KAPPA_MINUTES_BY_STAT.get(stat, 400.0)
            weight_player = (prior_min / (prior_min + kappa)) if prior_min > 0 else 0.0
            weight_pos = 1.0 - weight_player

            player_rate = (prior_data.get(stat, 0.0) / prior_min) if prior_min > 0 else 0.0
            pos_rate = pos_rates.get(stat, 0.0)

            blended_rate = (player_rate * weight_player) + (pos_rate * weight_pos)

            # Scale prior confidence (ESS) with actual observed minutes: rookies get 120m, veterans up to 650m (fixes K9)
            init_beta = float(np.clip(120.0 + 0.25 * prior_min, 120.0, 650.0))
            self.alphas[stat] = max(blended_rate * init_beta, 1e-3)
            self.betas[stat] = init_beta

        # 3. Percentage Stats & Shot Attempt Volume Initialization
        for stat in PERCENTAGE_STATS:
            made_key = f"{stat}M"
            att_key = f"{stat}A"

            made_pos = pos_rates.get(made_key, 0.0)
            att_pos = pos_rates.get(att_key, 0.0)
            pos_rate = (made_pos / att_pos) if att_pos > 0 else (0.47 if stat == 'FG' else 0.78)
            pos_att_per_min = att_pos if att_pos > 0 else (0.38 if stat == 'FG' else 0.10)

            kappa_att = EB_KAPPA_MINUTES_BY_STAT.get(att_key, 380.0)
            w_att = (prior_min / (prior_min + kappa_att)) if prior_min > 0 else 0.0
            init_att_beta = float(np.clip(120.0 + 0.25 * prior_min, 120.0, 650.0))

            if prior_min > 0 and prior_data.get(att_key, 0) > 0:
                obs_att = float(prior_data[att_key])
                obs_made = float(prior_data.get(made_key, 0.0))
                player_rate = obs_made / obs_att
                player_att_per_min = obs_att / prior_min

                kappa_shot = 250.0 if stat == 'FG' else 100.0
                w_rate = obs_att / (obs_att + kappa_shot)
                prior_ess_attempts = float(np.clip(kappa_shot * 0.5 + 0.35 * obs_att, MIN_BETA_ATTEMPTS, 450.0))
            else:
                player_rate = pos_rate
                player_att_per_min = 0.0
                w_rate = 0.0
                prior_ess_attempts = 40.0 if stat == 'FG' else 25.0

            blended_rate = (player_rate * w_rate) + (pos_rate * (1.0 - w_rate))
            blended_att_per_min = (player_att_per_min * w_att) + (pos_att_per_min * (1.0 - w_att))

            self.att_alphas[stat] = max(blended_att_per_min * init_att_beta, 1.0)
            self.att_betas[stat] = init_att_beta

            self.alphas[stat] = max(prior_ess_attempts * blended_rate, 1.0)
            self.betas[stat] = max(prior_ess_attempts * (1.0 - blended_rate), 1.0)

    def record_team_game_availability(self, played: bool):
        """
        Updates the player's Beta-Bernoulli availability posterior and consecutive_dnps counter
        whenever their NBA team plays a scheduled game (fixes Rapor 1 / K8).
        """
        # Mild exponential discounting on availability history so recent health dominates
        self.avail_alpha = max(2.0, self.avail_alpha * 0.985 + (1.0 if played else 0.0))
        self.avail_beta = max(0.5, self.avail_beta * 0.985 + (0.0 if played else 1.0))
        self.availability_rate = float(np.clip(self.avail_alpha / (self.avail_alpha + self.avail_beta), 0.15, 0.98))
        if played:
            self.consecutive_dnps = 0
        else:
            self.consecutive_dnps += 1

    def update_injury_status(self, status='HEALTHY', desc='', is_b2b_rest=False, expected_return=None):
        self.injury_status = str(status).upper().strip() if status else 'HEALTHY'
        self.injury_desc = desc or ''
        self.is_b2b_rest = bool(is_b2b_rest)
        self.expected_return = expected_return

    def get_effective_game_availability(self, is_b2b=False):
        """
        Returns the conditional probability the player plays in an upcoming game this week,
        conditioned on:
          1. Explicit live injury status (OUT, DOUBTFUL, QUESTIONABLE, PROBABLE, B2B_REST).
          2. Multi-game DNP streak (consecutive_dnps).
          3. Long-term Bayesian baseline availability rate.
        """
        st = getattr(self, 'injury_status', 'HEALTHY')
        if st in ('OUT', 'INJ', 'SUSPENDED', 'REST'):
            return 0.0
        if getattr(self, 'is_b2b_rest', False) and is_b2b:
            return 0.05
        if st == 'DOUBTFUL':
            return 0.15
        if st in ('QUESTIONABLE', 'GTD', 'DTD'):
            return 0.52
        if st == 'PROBABLE':
            return 0.90

        if self.consecutive_dnps >= 5:
            return 0.08
        elif self.consecutive_dnps >= 3:
            return 0.18
        elif self.consecutive_dnps == 2:
            return 0.30
        elif self.consecutive_dnps == 1:
            return min(self.availability_rate, 0.72)
        # Preserve player-specific availability prior blended with healthy entry streak
        return float(np.clip(0.35 * 0.92 + 0.65 * self.availability_rate, 0.35, 0.96))

    def _apply_floored_decay(self, delta_days, is_event_reset=False):
        """
        Applies category-specific exponential discounting exp(-lambda_c * delta_days)
        and multiplicative trade shock delta_event (fixes Rapor 1 / K11 & 1.7).
        """
        event_mult = self.delta_event if is_event_reset else 1.0

        for stat in COUNT_STATS:
            lam = DECAY_LAMBDA_BY_STAT.get(stat, self.decay_lambda)
            delta_c = float(np.exp(-lam * delta_days)) * event_mult
            rate = self.alphas[stat] / self.betas[stat] if self.betas[stat] > 0 else 0.0
            new_beta = max(self.betas[stat] * delta_c, MIN_BETA_MINUTES)
            self.betas[stat] = new_beta
            self.alphas[stat] = max(rate * new_beta, 1e-4)

        for stat in PERCENTAGE_STATS:
            lam_att = DECAY_LAMBDA_BY_STAT.get(stat, 0.012)
            delta_att = float(np.exp(-lam_att * delta_days)) * event_mult
            if stat in self.att_betas and self.att_betas[stat] > 0:
                att_rate = self.att_alphas[stat] / self.att_betas[stat]
                new_att_beta = max(self.att_betas[stat] * delta_att, MIN_BETA_MINUTES)
                self.att_betas[stat] = new_att_beta
                self.att_alphas[stat] = max(att_rate * new_att_beta, 0.5)

            # Shooting percentages (especially FT%) decay much slower and aren't wiped out by trades
            lam_pct = DECAY_LAMBDA_BY_STAT.get(stat, 0.005)
            pct_event_mult = 0.65 if is_event_reset else 1.0
            delta_pct = float(np.exp(-lam_pct * delta_days)) * pct_event_mult
            total_att = self.alphas[stat] + self.betas[stat]
            if total_att > 0:
                p = self.alphas[stat] / total_att
                new_total = max(total_att * delta_pct, MIN_BETA_ATTEMPTS)
                self.alphas[stat] = max(p * new_total, 0.5)
                self.betas[stat] = max((1.0 - p) * new_total, 0.5)

    def update_stats(self, game_date, minutes, stats_dict, is_event_reset=False):
        """
        Updates the player's Bayesian belief state and expected minutes based on a new game.
        """
        delta_days = 1
        if self.last_game_date is not None and game_date is not None:
            delta_days = (game_date - self.last_game_date).days
            delta_days = min(max(delta_days, 1), 180)

        self._apply_floored_decay(delta_days, is_event_reset=is_event_reset)

        if minutes > 0:
            self.consecutive_dnps = 0
            ewma_alpha = 0.45 if is_event_reset else 0.18
            diff_min = minutes - self.expected_minutes
            self.expected_minutes = float(np.clip(self.expected_minutes + ewma_alpha * diff_min, 6.0, 40.0))
            # Unclipped up to 144.0 (SD = 12 mins) to capture rotation/foul-trouble/blowout variance (fixes Rapor 1 / K7)
            self.minutes_var = float(np.clip((1.0 - ewma_alpha) * self.minutes_var + ewma_alpha * (diff_min ** 2), 9.0, 144.0))

            for stat in COUNT_STATS:
                val = float(stats_dict.get(stat, 0.0))
                self.alphas[stat] += val
                self.betas[stat] += minutes

            for stat in PERCENTAGE_STATS:
                made_key = f"{stat}M"
                att_key = f"{stat}A"
                makes = float(stats_dict.get(made_key, 0.0))
                attempts = float(stats_dict.get(att_key, 0.0))
                misses = max(0.0, attempts - makes)

                self.att_alphas[stat] += attempts
                self.att_betas[stat] += minutes

                self.alphas[stat] += makes
                self.betas[stat] += misses

        self.last_game_date = game_date

    def predict_next_game(self, projected_minutes=None, projected_attempts=None, current_date=None):
        """
        Returns Expected Value E[X] and Calibrated Predictive Variance Var_pred for the next game:
          - Incorporates compound-Poisson overdispersion phi_c for PTS/FTA/FGA (fixes Rapor 1 / K1)
          - Incorporates full Law of Total Variance minutes term r^2 * Var(M) without arbitrary 0.25 scaling (fixes Rapor 1 / K7)
        """
        m = float(projected_minutes) if projected_minutes is not None else self.expected_minutes
        # If exact minutes are passed (e.g. conditional oracle test), minutes uncertainty is 0; otherwise use self.minutes_var
        min_var = 0.0 if projected_minutes is not None else self.minutes_var

        idle_days = 0
        if current_date is not None and self.last_game_date is not None:
            idle_days = max(0, min((current_date - self.last_game_date).days, 180))

        predictions = {'MIN': {'mean': m, 'variance': self.minutes_var}}

        # 1. Count Stats (Overdispersed Negative Binomial + Full Minutes Variance)
        for stat in COUNT_STATS:
            lam = DECAY_LAMBDA_BY_STAT.get(stat, self.decay_lambda)
            idle_delta = float(np.exp(-lam * idle_days)) if idle_days > 2 else 1.0

            beta_eff = max(self.betas.get(stat, 0.0) * idle_delta, MIN_BETA_MINUTES)
            rate = (self.alphas.get(stat, 0.0) / self.betas[stat]) if self.betas.get(stat, 0.0) > 0 else 0.0
            alpha_eff = max(rate * beta_eff, 1e-4)

            expected_val = rate * m
            phi_c = DISPERSION_PHI_BY_STAT.get(stat, 1.0)

            # Quasi-Negative Binomial count variance given minutes + full Law of Total Variance across minutes
            nb_var = phi_c * expected_val + (expected_val ** 2 / alpha_eff)
            variance = nb_var + (rate ** 2) * min_var

            predictions[stat] = {'mean': expected_val, 'variance': variance, 'rate_per_min': rate}

        # 2. Percentage Stats (Overdispersed Gamma-Poisson Attempts + Minutes Variance + Beta-Binomial Accuracy)
        for stat in PERCENTAGE_STATS:
            lam_pct = DECAY_LAMBDA_BY_STAT.get(stat, 0.005)
            idle_delta_pct = float(np.exp(-lam_pct * idle_days)) if idle_days > 2 else 1.0

            alpha = self.alphas.get(stat, 1.0)
            beta = self.betas.get(stat, 1.0)
            total_ab = max((alpha + beta) * idle_delta_pct, MIN_BETA_ATTEMPTS)
            p = alpha / (alpha + beta) if (alpha + beta) > 0 else (0.47 if stat == 'FG' else 0.78)

            phi_att = DISPERSION_PHI_BY_STAT.get(stat, 1.25)

            if projected_attempts and stat in projected_attempts:
                n = float(projected_attempts[stat])
                var_att = phi_att * n
            else:
                lam_att = DECAY_LAMBDA_BY_STAT.get(stat, 0.012)
                idle_delta_att = float(np.exp(-lam_att * idle_days)) if idle_days > 2 else 1.0
                att_beta_eff = max(self.att_betas.get(stat, 400.0) * idle_delta_att, MIN_BETA_MINUTES)
                att_rate = (
                    self.att_alphas[stat] / self.att_betas[stat]
                    if self.att_betas.get(stat, 0.0) > 0
                    else (0.38 if stat == 'FG' else 0.10)
                )
                att_alpha_eff = max(att_rate * att_beta_eff, 0.5)
                n = max(att_rate * m, 0.1)
                # Include both overdispersion phi_att and minutes uncertainty att_rate^2 * min_var (fixes Rapor 1 / K1 & K7)
                var_att = phi_att * n + (n ** 2 / att_alpha_eff) + (att_rate ** 2) * min_var

            expected_makes = n * p

            # Conditional Beta-Binomial variance E[Var(M | A)]
            cond_var = n * p * (1.0 - p) * (total_ab + n) / (total_ab + 1.0)
            # Unconditional variance via Law of Total Variance: E[Var(M|A)] + p^2 * Var(A)
            total_var = cond_var + (p ** 2) * var_att

            predictions[stat] = {
                'mean': expected_makes,
                'attempts': n,
                'attempts_var': var_att,
                'variance': total_var,
                'cond_variance': cond_var,
                'rate': p,
            }

        return predictions

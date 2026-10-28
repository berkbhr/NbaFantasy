"""Controlled old/new engine audit with known generative assumptions.

These experiments isolate mathematical formulas. They are not historical
fantasy wins and do not establish that the synthetic world matches the NBA.
"""

import argparse
import json
import subprocess
import types
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binom

from . import bayesian_model, matchup_engine
from .compare_versions import ROOT, historical_modules


def load_old_engine(revision):
    source = subprocess.check_output(
        ["git", "show", f"{revision}:src/matchup_engine.py"], cwd=ROOT
    ).decode("utf-8-sig")
    module = types.ModuleType("historical_matchup_engine")
    module.__file__ = str(ROOT / "src/matchup_engine.py")
    exec(compile(source, module.__file__, "exec"), module.__dict__)

    class SyntheticEngine(module.MatchupEngine):
        def _load_leak_free_team_map(self, prior_season, target_season):
            self.prior_team_map = {}
            return {}

    return module, SyntheticEngine


def fixed_attempt_audit(old_module):
    results = []
    for n_a, n_b in [(2, 2), (5, 5), (10, 10), (10, 100), (100, 100), (100, 1000), (400, 800)]:
        for p_a, p_b in [(0.5, 0.5), (0.55, 0.5), (0.6, 0.5), (0.45, 0.5), (0.8, 0.6)]:
            k = np.arange(n_a + 1, dtype=np.int64)
            mass = binom.pmf(k, n_a, p_a)
            threshold = (k * n_b - 1) // n_a
            win = float(np.sum(mass * binom.cdf(threshold, n_b, p_b)))
            tie = float(
                np.sum(mass * ((k * n_b) % n_a == 0) * binom.pmf((k * n_b) // n_a, n_b, p_b))
            )
            truth = win + 0.5 * tie
            distributions = []
            for n, p in [(n_a, p_a), (n_b, p_b)]:
                mean = dict.fromkeys(matchup_engine.ALL_CATEGORIES, 0.0)
                variance = dict.fromkeys(
                    matchup_engine.ALL_CATEGORIES + ["FGM_cond", "FTM_cond"], 0.0
                )
                mean.update(FGM=n * p, FGA=n)
                variance.update(FGM=n * p * (1 - p), FGM_cond=n * p * (1 - p))
                distributions.append({"mean": mean, "var": variance})
            old = old_module.MatchupEngine.evaluate_h2h_matchup(*distributions)[1]["FG_PCT"]
            old_uninflated = old_module.MatchupEngine.evaluate_h2h_matchup(
                *distributions, var_scale=1 / old_module.WEEKLY_VAR_INFLATION_BY_CAT["FG"]
            )[1]["FG_PCT"]
            new_probs = matchup_engine.MatchupEngine.evaluate_h2h_matchup(*distributions)[1]
            new = new_probs["FG_PCT"] + 0.5 * new_probs.ties["FG_PCT"]
            results.append(
                {
                    "attempts_a": n_a,
                    "attempts_b": n_b,
                    "accuracy_a": p_a,
                    "accuracy_b": p_b,
                    "exact_category_credit": truth,
                    "exact_tie": tie,
                    "old_credit": old,
                    "old_uninflated_credit": old_uninflated,
                    "new_credit": new,
                    "old_abs_error": abs(old - truth),
                    "old_uninflated_abs_error": abs(old_uninflated - truth),
                    "new_abs_error": abs(new - truth),
                }
            )
    return pd.DataFrame(results)


def make_player(model, pid, accuracy, beta, availability):
    bp = model.BayesianPlayer(pid, str(pid))
    bp.initialize_priors(None, {})
    bp.expected_minutes = bp.base_expected_minutes = 30.0
    bp.minutes_var = bp.base_minutes_var = 36.0
    bp.availability_rate = availability
    for stat, rate in {
        "PTS": 0.7,
        "REB": 0.2,
        "AST": 0.15,
        "STL": 0.04 if accuracy > 0.5 else 0.03,
        "BLK": 0.03,
        "FG3M": 0.07,
        "TOV": 0.08,
    }.items():
        bp.alphas[stat] = rate * beta
        bp.betas[stat] = beta
    for stat, rate, p in [("FG", 0.4, accuracy), ("FT", 0.1, 0.8)]:
        bp.att_alphas[stat] = rate * beta
        bp.att_betas[stat] = beta
        bp.alphas[stat] = p * 100
        bp.betas[stat] = (1 - p) * 100
    return bp


def synthetic_distribution(
    model, engine_type, n_a, n_b, games, beta, availability, correlation=0.0, old=False
):
    ids_a = list(range(10001, 10001 + n_a))
    ids_b = list(range(20001, 20001 + n_b))
    players = {
        pid: make_player(model, pid, 0.55 if pid in ids_a else 0.5, beta, availability)
        for pid in ids_a + ids_b
    }
    dates = pd.date_range("2020-01-06", periods=games)
    schedule = pd.DataFrame(
        [
            {"TEAM_ID": tid, "GAME_DATE": day, "GAME_ID": str(i)}
            for tid in (10, 20)
            for i, day in enumerate(dates)
        ]
    )
    positions = pd.DataFrame([{"PLAYER_ID": pid, "POSITION": "G-F-C"} for pid in players])
    kwargs = {} if old else {"availability_correlation": correlation, "team_map": {}}
    engine = engine_type(
        players, schedule, positions, use_positional_depth_and_injury_boost=False, **kwargs
    )
    engine.team_map = {pid: (10 if pid in ids_a else 20) for pid in players}
    a = engine.get_expected_weekly_distribution(
        ids_a, dates[0], dates[-1], category_weights={"STL": 1.0}, use_live_injuries=False
    )
    b = engine.get_expected_weekly_distribution(
        ids_b, dates[0], dates[-1], category_weights={"STL": 1.0}, use_live_injuries=False
    )
    _, p, _ = engine.evaluate_h2h_matchup(a, b)
    credit = {c: p[c] + 0.5 * getattr(p, "ties", {}).get(c, 0.0) for c in ("FG_PCT", "STL")}
    return a, b, credit


def sample_team(rng, players, games, beta, availability, correlation, trials, accuracy):
    # Posterior rate and accuracy draws are shared across a player's games.
    shape = (trials, players)
    shot_rate = rng.gamma(0.4 * beta, 1 / beta, size=shape)
    steal_rate = rng.gamma((0.04 if accuracy > 0.5 else 0.03) * beta, 1 / beta, size=shape)
    shooting = rng.beta(accuracy * 100, (1 - accuracy) * 100, size=shape)
    if correlation:
        concentration = 1 / correlation - 1
        play_rate = rng.beta(
            availability * concentration, (1 - availability) * concentration, size=shape
        )
    else:
        play_rate = np.full(shape, availability)
    attempts = np.zeros(trials, dtype=np.int64)
    makes = np.zeros(trials, dtype=np.int64)
    steals = np.zeros(trials, dtype=np.int64)
    # A compound Poisson with jump sizes 1 and 2 gives phi_FGA=1.25.
    jump_two = (1.25 - 1) / (3 - 1.25)
    for _ in range(games):
        minutes = np.where(rng.random(shape) < 0.5, 24.0, 36.0)
        plays = rng.random(shape) < play_rate
        event_mean = shot_rate * minutes / (1 + jump_two)
        n = rng.poisson(event_mean * (1 - jump_two)) + 2 * rng.poisson(event_mean * jump_two)
        k = rng.binomial(n, shooting)
        st = rng.poisson(steal_rate * minutes)
        attempts += (n * plays).sum(axis=1)
        makes += (k * plays).sum(axis=1)
        steals += (st * plays).sum(axis=1)
    return makes, attempts, steals


def weekly_audit(old_model, old_engine, trials=30000):
    results = []
    cases = [
        (a, b, g, beta, avail, 0.0)
        for a, b in [(1, 1), (1, 10), (10, 10)]
        for g in (1, 4)
        for beta in (60, 650)
        for avail in (1.0, 0.8)
    ]
    cases += [(10, 10, 4, beta, 0.8, 0.65) for beta in (60, 650)]
    for index, (n_a, n_b, g, beta, avail, rho) in enumerate(cases):
        old_a, _, old_credit = synthetic_distribution(
            old_model, old_engine, n_a, n_b, g, beta, avail, old=True
        )
        new_a, _, new_credit = synthetic_distribution(
            bayesian_model, matchup_engine.MatchupEngine, n_a, n_b, g, beta, avail
        )
        matched_a, _, matched_credit = synthetic_distribution(
            bayesian_model, matchup_engine.MatchupEngine, n_a, n_b, g, beta, avail, correlation=rho
        )
        rng = np.random.default_rng(20261027 + index)
        ma, aa, sa = sample_team(rng, n_a, g, beta, avail, rho, trials, 0.55)
        mb, ab, sb = sample_team(rng, n_b, g, beta, avail, rho, trials, 0.5)
        # Zero attempts are assigned a zero percentage, matching engine policy.
        pct_a = np.divide(ma, aa, out=np.zeros(trials), where=aa > 0)
        pct_b = np.divide(mb, ab, out=np.zeros(trials), where=ab > 0)
        # Integer cross-products preserve exact ties when both sides attempted.
        both = (aa > 0) & (ab > 0)
        diff = np.where(both, ma * ab - mb * aa, np.sign(pct_a - pct_b))
        truth_fg = (diff > 0) + 0.5 * (diff == 0)
        truth_st = (sa > sb) + 0.5 * (sa == sb)
        # Exact steal variance for this world, before normal approximations.
        r = 0.04
        m = 30.0
        v = 36.0
        rate_var = r / beta
        mu = r * m
        daily = mu + rate_var * (m * m + v) + r * r * v
        cov_play = rho * avail * (1 - avail)
        exact_var = n_a * (
            g * (avail * daily + avail * (1 - avail) * mu * mu)
            + g * (g - 1) * ((avail * avail + cov_play) * m * m * rate_var + cov_play * mu * mu)
        )
        if not np.isclose(matched_a["var"]["STL"], exact_var, rtol=1e-10):
            raise AssertionError(
                "New moments fail the exact shared-rate/availability variance identity"
            )
        for category, truth in [("FG_PCT", truth_fg), ("STL", truth_st)]:
            p = float(truth.mean())
            results.append(
                {
                    "case": index,
                    "category": category,
                    "players_a": n_a,
                    "players_b": n_b,
                    "games": g,
                    "beta_minutes": beta,
                    "availability": avail,
                    "true_availability_correlation": rho,
                    "trials": trials,
                    "mc_category_credit": p,
                    "mc_standard_error": float(truth.std(ddof=1) / np.sqrt(trials)),
                    "old_credit": old_credit[category],
                    "new_credit": new_credit[category],
                    "new_with_known_rho_credit": matched_credit[category],
                    "old_abs_error": abs(old_credit[category] - p),
                    "new_abs_error": abs(new_credit[category] - p),
                    "new_with_known_rho_abs_error": abs(matched_credit[category] - p),
                    "exact_steal_variance_a": exact_var,
                    "old_raw_steal_variance_a": old_a["var"]["STL"],
                    "new_raw_steal_variance_a": new_a["var"]["STL"],
                    "new_with_known_rho_steal_variance_a": matched_a["var"]["STL"],
                    "zero_attempt_rate_a": float(np.mean(aa == 0)),
                    "zero_attempt_rate_b": float(np.mean(ab == 0)),
                }
            )
    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-ref", required=True)
    parser.add_argument("--trials", type=int, default=30000)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/validation")
    args = parser.parse_args()
    old_model, _, _ = historical_modules(args.old_ref)
    old_module, old_engine = load_old_engine(args.old_ref)
    fixed = fixed_attempt_audit(old_module)
    weekly = weekly_audit(old_model, old_engine, args.trials)
    args.output.mkdir(parents=True, exist_ok=True)
    fixed.to_csv(args.output / "fixed_attempt_audit.csv", index=False)
    weekly.to_csv(args.output / "weekly_moment_audit.csv", index=False)
    metadata = {
        "old_ref": args.old_ref,
        "trials": args.trials,
        "seed_base": 20261027,
        "scope": __doc__,
        "scenarios": "1/10 players, 1/4 games, 60/650 prior minutes, availability 1/.8; separate correlated-absence stress",
        "no_tuning": "Production settings unchanged; known-rho variant is an oracle sensitivity, not deployed or fitted from NBA injuries",
        "assumptions": "Shared gamma production/attempt rates and beta accuracy; independent two-point minutes; compound-Poisson attempts; optional beta-Bernoulli absence correlation",
        "fixed_attempt_truth": "Exact binomial summation with half credit for ties",
        "weekly_truth": "Monte Carlo mean category credit; standard errors reported; steal variance independently checked in closed form",
    }
    (args.output / "mathematical_audit_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print("Fixed attempts mean absolute credit error:")
    print(fixed[["old_abs_error", "old_uninflated_abs_error", "new_abs_error"]].mean().to_string())
    print("Weekly Monte Carlo errors by category and absence correlation:")
    print(
        weekly.groupby(["category", "true_availability_correlation"])[
            ["old_abs_error", "new_abs_error", "new_with_known_rho_abs_error"]
        ]
        .mean()
        .to_string()
    )


if __name__ == "__main__":
    main()

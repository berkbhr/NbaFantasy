"""Paired, predict-before-update comparison against a historical Git revision.

This evaluates player-level moments conditional on playing, not the complete
live decision pipeline. Both versions use identical game rows, past-only
priors and pooled positions. No hyperparameters are fitted by this experiment.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from scipy.stats import betabinom

from . import bayesian_model, priors

ROOT = Path(__file__).resolve().parents[1]


def historical_modules(revision):
    def read(path):
        return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT).decode(
            "utf-8-sig"
        )

    model_source, prior_source = read("src/bayesian_model.py"), read("src/simulator.py")
    model = types.ModuleType("historical_bayesian_model")
    model.__file__ = str(ROOT / "src" / "bayesian_model.py")
    exec(compile(model_source, model.__file__, "exec"), model.__dict__)
    old_alias = sys.modules.get("bayesian_model")
    sys.modules["bayesian_model"] = model
    try:
        prior = types.ModuleType("historical_priors")
        prior.__file__ = str(ROOT / "src" / "simulator.py")
        exec(compile(prior_source, prior.__file__, "exec"), prior.__dict__)
    finally:
        if old_alias is None:
            sys.modules.pop("bayesian_model", None)
        else:
            sys.modules["bayesian_model"] = old_alias
    return (
        model,
        prior,
        {
            "old_model_sha256": hashlib.sha256(model_source.encode()).hexdigest(),
            "old_prior_sha256": hashlib.sha256(prior_source.encode()).hexdigest(),
        },
    )


def predict_rows(model, prior_module, rows, season, blend, is_old=False):
    year = int(season[:4]) - 1
    prior_season = f"{year}_{str(year + 1)[-2:]}"
    historical = prior_module.load_prior_season(prior_season, blend_prev_season=blend)
    if not historical:
        raise ValueError(f"Missing completed prior season {prior_season}")
    averages = prior_module.get_positional_averages(historical, pos_dict={})
    players, teams, output, games_seen = {}, {}, [], {}
    for row in rows:
        pid, day = int(row["PLAYER_ID"]), row["GAME_DATE"]
        if pid not in players:
            bp = model.BayesianPlayer(pid, str(pid))
            bp.initialize_priors(historical.get(pid), averages, pos_str="UTIL")
            players[pid] = bp
        bp = players[pid]
        prediction = bp.predict_next_game(current_date=day)
        for stat in model.COUNT_STATS + ["MIN"]:
            output.append(
                (
                    str(day.date()),
                    pid,
                    str(row["GAME_ID"]),
                    stat,
                    float(row.get(stat, 0)),
                    prediction[stat]["mean"],
                    prediction[stat]["variance"],
                    np.nan,
                    np.nan,
                    np.nan,
                    np.nan,
                    games_seen.get(pid, 0),
                )
            )
        for shot in ("FG", "FT"):
            pred = prediction[shot]
            idle = (
                0 if bp.last_game_date is None else max(0, min((day - bp.last_game_date).days, 180))
            )
            decay = np.exp(-model.DECAY_LAMBDA_BY_STAT[shot] * idle) if idle > 2 else 1.0
            total = max((bp.alphas[shot] + bp.betas[shot]) * decay, model.MIN_BETA_ATTEMPTS)
            p = pred["rate"]
            for suffix, mean_key, var_key in [
                ("M", "mean", "variance"),
                ("A", "attempts", "attempts_var"),
            ]:
                output.append(
                    (
                        str(day.date()),
                        pid,
                        str(row["GAME_ID"]),
                        shot + suffix,
                        float(row.get(shot + suffix, 0)),
                        pred[mean_key],
                        pred[var_key],
                        p if suffix == "M" else np.nan,
                        p * total if suffix == "M" else np.nan,
                        (1 - p) * total if suffix == "M" else np.nan,
                        float(row.get(shot + "A", 0)) if suffix == "M" else np.nan,
                        games_seen.get(pid, 0),
                    )
                )
        trade = pid in teams and teams[pid] != int(row["TEAM_ID"])
        kwargs = {} if is_old else {"game_id": row["GAME_ID"]}
        bp.update_stats(day, float(row["MIN"]), row, is_event_reset=trade, **kwargs)
        teams[pid] = int(row["TEAM_ID"])
        games_seen[pid] = games_seen.get(pid, 0) + 1
    return pd.DataFrame(
        output,
        columns=[
            "date",
            "player_id",
            "game_id",
            "stat",
            "actual",
            "mean",
            "variance",
            "accuracy_p",
            "accuracy_alpha",
            "accuracy_beta",
            "actual_attempts",
            "games_seen",
        ],
    )


def compare(old, new, season, mode, reference_mpg=None):
    columns = ["date", "player_id", "game_id", "stat", "actual"]
    paired = old.merge(new, on=columns, suffixes=("_old", "_new"), validate="one_to_one")
    if len(paired) != len(old) or len(old) != len(new):
        raise ValueError("Both versions must evaluate identical observations")
    results = []
    if not np.array_equal(paired.games_seen_old, paired.games_seen_new):
        raise ValueError("Versions disagree about observations available before a forecast")
    paired["reference_mpg"] = paired.player_id.map(reference_mpg or {}).fillna(0)
    populations = {
        "all": np.ones(len(paired), dtype=bool),
        "prior_25plus_mpg": paired.reference_mpg >= 25,
        "prior_15_to_25_mpg": (paired.reference_mpg >= 15) & (paired.reference_mpg < 25),
        "prior_under_15_or_new": paired.reference_mpg < 15,
        "first_10_player_games": paired.games_seen_old < 10,
        "after_10_player_games": paired.games_seen_old >= 10,
    }
    for population, mask in populations.items():
        results.extend(_compare_group(paired.loc[mask], season, mode, population))
    return results


def _compare_group(paired, season, mode, population):
    results = []
    for stat, group in paired.groupby("stat"):
        a = np.abs(group.actual - group.mean_old)
        b = np.abs(group.actual - group.mean_new)
        old_mae, new_mae = float(a.mean()), float(b.mean())
        # Paired calendar-week block bootstrap, approximate uncertainty only.
        week = pd.to_datetime(group.date).dt.to_period("W-SUN")
        weekly = (
            pd.DataFrame({"week": week, "improvement": a - b})
            .groupby("week")
            .improvement.agg(["sum", "count"])
        )
        rng = np.random.default_rng(42)
        selected = rng.integers(0, len(weekly), size=(2000, len(weekly)))
        bootstrap = weekly["sum"].to_numpy()[selected].sum(axis=1) / weekly["count"].to_numpy()[
            selected
        ].sum(axis=1)
        lower, upper = np.quantile(bootstrap, [0.025, 0.975])
        result = {
            "season": season,
            "prior_mode": mode,
            "population": population,
            "stat": stat,
            "n": len(group),
            "old_MAE": old_mae,
            "new_MAE": new_mae,
            "MAE_improvement_percent": 100 * (old_mae - new_mae) / old_mae,
            "paired_MAE_improvement": old_mae - new_mae,
            "weekly_bootstrap_low": float(lower),
            "weekly_bootstrap_high": float(upper),
        }
        for label in ("old", "new"):
            error = group.actual - group["mean_" + label]
            variance = np.maximum(group["variance_" + label], 1e-9)
            result[label + "_RMSE"] = float(np.sqrt(np.mean(error**2)))
            result[label + "_coverage95"] = float(
                np.mean(abs(error) <= 1.95996398 * np.sqrt(variance))
            )
            if stat in ("FGM", "FTM"):
                attempts = group["actual_attempts_" + label].to_numpy()
                p = np.clip(group["accuracy_p_" + label].to_numpy(), 1e-12, 1 - 1e-12)
                made = group.actual.to_numpy()
                result[label + "_accuracy_log_loss_per_attempt"] = float(
                    np.sum(-made * np.log(p) - (attempts - made) * np.log1p(-p)) / attempts.sum()
                )
                mask = attempts > 0
                result[label + "_accuracy_beta_binomial_nll"] = float(
                    -np.mean(
                        betabinom.logpmf(
                            made[mask],
                            attempts[mask],
                            group["accuracy_alpha_" + label].to_numpy()[mask],
                            group["accuracy_beta_" + label].to_numpy()[mask],
                        )
                    )
                )
        results.append(result)
    return results


def leakage_checks(old_model, old_priors, rows, season, blend):
    """Audit prior file access and perturb a future game's complete box score."""
    counts = {}
    for row in rows:
        counts[row["PLAYER_ID"]] = counts.get(row["PLAYER_ID"], 0) + 1
    pid = next(pid for pid, n in counts.items() if n >= 3)
    sample = [dict(row) for row in rows if row["PLAYER_ID"] == pid][:3]
    altered = [dict(row) for row in sample]
    altered[-1]["MIN"] = min(48.0, float(altered[-1]["MIN"]) + 1)
    for stat, increment in [("PTS", 3), ("FGM", 1), ("FGA", 1), ("FG3M", 1)]:
        altered[-1][stat] = float(altered[-1].get(stat, 0)) + increment
    cutoff = pd.Timestamp(rows[0]["GAME_DATE"])
    original_reader = pd.read_parquet
    accessed = []

    def read_past_only(path, *args, **kwargs):
        frame = original_reader(path, *args, **kwargs)
        last = None
        if "GAME_DATE" in frame and not frame.empty:
            last = pd.to_datetime(frame.GAME_DATE).max()
            if last >= cutoff:
                raise AssertionError(f"Prior read reaches evaluation period: {path}")
        accessed.append(
            {
                "path": str(Path(path).resolve().relative_to(ROOT)),
                "max_date": str(last.date()) if last is not None else None,
            }
        )
        return frame

    checks = []
    for label, model, loader, is_old in [
        ("old", old_model, old_priors, True),
        ("new", bayesian_model, priors, False),
    ]:
        accessed.clear()
        with patch("pandas.read_parquet", side_effect=read_past_only):
            before = predict_rows(model, loader, sample, season, blend, is_old)
            after = predict_rows(model, loader, altered, season, blend, is_old)
        np.testing.assert_array_equal(
            before[["mean", "variance"]].to_numpy(), after[["mean", "variance"]].to_numpy()
        )
        checks.append(
            {
                "version": label,
                "season": season,
                "blend": blend,
                "first_evaluation_date": str(cutoff.date()),
                "future_boxscore_perturbation": "passed for all three pre-game forecasts",
                "prior_reads": sorted({json.dumps(row, sort_keys=True) for row in accessed}),
            }
        )
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-ref", required=True)
    parser.add_argument("--seasons", nargs="+", default=["2024_25", "2025_26"])
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "validation")
    args = parser.parse_args()
    old_model, old_priors, metadata = historical_modules(args.old_ref)
    results = []
    metadata.update(
        {
            "old_ref": args.old_ref,
            "scope": __doc__,
            "new_model_sha256": hashlib.sha256(
                (ROOT / "src/bayesian_model.py").read_bytes()
            ).hexdigest(),
            "new_prior_sha256": hashlib.sha256((ROOT / "src/priors.py").read_bytes()).hexdigest(),
            "positions": "Pooled in both arms; no current position snapshot",
            "tuning": "None; this is additional evaluation on previously inspected seasons",
            "accuracy_scoring": "Actual attempts used only as scoring exposure for conditional shooting accuracy, never as a prediction input",
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "bootstrap": "Paired calendar-week blocks, seed 42, 2000 resamples; does not capture all cross-week dependence",
            "data_sha256": {},
            "leakage_checks": [],
        }
    )
    for season in args.seasons:
        if season not in ("2024_25", "2025_26"):
            parser.error("This historical audit supports 2024_25 and 2025_26 only")
        path = ROOT / "data/raw" / f"player_logs_{season}.parquet"
        metadata["data_sha256"][season] = hashlib.sha256(path.read_bytes()).hexdigest()
        logs = pd.read_parquet(path)
        logs["GAME_DATE"] = pd.to_datetime(logs.GAME_DATE)
        logs = (
            logs[logs.MIN > 0]
            .sort_values(["GAME_DATE", "GAME_ID", "PLAYER_ID"])
            .drop_duplicates(["PLAYER_ID", "GAME_ID"])
        )
        rows = logs.to_dict("records")
        prior_year = int(season[:4]) - 1
        reference, _ = priors._load_single_season_totals(f"{prior_year}_{str(prior_year + 1)[-2:]}")
        reference_mpg = {pid: p["MIN"] / p["GP"] for pid, p in reference.items() if p["GP"] > 0}
        for mode, blend in [("single_prior", False), ("two_season_prior", True)]:
            metadata["leakage_checks"].extend(
                leakage_checks(old_model, old_priors, rows, season, blend)
            )
            old = predict_rows(old_model, old_priors, rows, season, blend, is_old=True)
            new = predict_rows(bayesian_model, priors, rows, season, blend)
            results.extend(compare(old, new, season, mode, reference_mpg))
            print(f"Compared {season} / {mode}: {len(rows)} player-games", flush=True)
    args.output.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame(results)
    table.to_csv(args.output / "version_comparison.csv", index=False)
    (args.output / "version_comparison_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()

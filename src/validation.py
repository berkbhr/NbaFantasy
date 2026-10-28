"""Reproducible predict-before-update evaluation using local historical caches.

Player metrics condition on playing (MIN>0); they do not validate availability
or weekly H2H probabilities. Weekly probability scoring is a separate function
requiring actual archived forecasts and outcomes.
"""

import argparse
import hashlib
import json
import platform
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import ndtr

from .bayesian_model import COUNT_STATS, BayesianPlayer
from .priors import get_positional_averages, load_prior_season

ROOT = Path(__file__).resolve().parents[1]


def previous_season(season):
    year = int(season[:4]) - 1
    return f"{year}_{str(year + 1)[-2:]}"


def walk_forward(season, data_dir=None):
    """Return game forecasts. No current injury database or target roster is read."""
    data = Path(data_dir) if data_dir else ROOT / "data"
    path = data / "raw" / f"player_logs_{season}.parquet"
    # The prior loader uses historical completed caches, never the target logs.
    if data_dir is not None:
        from . import priors as prior_module

        old = (prior_module.RAW_DIR, prior_module.PROCESSED_DIR)
        prior_module.RAW_DIR, prior_module.PROCESSED_DIR = (
            str(data / "raw"),
            str(data / "processed"),
        )
        try:
            priors = load_prior_season(previous_season(season), blend_prev_season=False)
        finally:
            prior_module.RAW_DIR, prior_module.PROCESSED_DIR = old
    else:
        priors = load_prior_season(previous_season(season), blend_prev_season=False)
    if not priors:
        raise ValueError("A completed prior-season cache is required")
    # Historical positions are optional. Never use the current position snapshot
    # as if it had been known in a historical evaluation.
    positions_path = data / "processed" / f"player_positions_{previous_season(season)}.parquet"
    positions = (
        pd.read_parquet(positions_path).set_index("PLAYER_ID")["POSITION"].to_dict()
        if positions_path.exists()
        else {}
    )
    averages = get_positional_averages(priors, pos_dict=positions)
    logs = pd.read_parquet(path)
    logs["GAME_DATE"] = pd.to_datetime(logs["GAME_DATE"])
    logs = logs.sort_values(["GAME_DATE", "GAME_ID", "PLAYER_ID"]).drop_duplicates(
        ["PLAYER_ID", "GAME_ID"]
    )
    players, history, ewma, teams = {}, defaultdict(lambda: deque(maxlen=5)), {}, {}
    rows = []
    for row in logs.to_dict("records"):
        if row["MIN"] <= 0:
            continue
        pid = int(row["PLAYER_ID"])
        if pid not in players:
            bp = BayesianPlayer(pid, row.get("PLAYER_NAME", str(pid)))
            bp.initialize_priors(priors.get(pid), averages, pos_str=positions.get(pid, "UTIL"))
            players[pid] = bp
        bp = players[pid]
        pred = bp.predict_next_game(current_date=row["GAME_DATE"])
        prior = priors.get(pid, {})
        gp = max(1, prior.get("GP", 0))
        for stat in COUNT_STATS + ["MIN"]:
            initial = (
                prior.get(stat, 0) / gp
                if prior
                else (bp.expected_minutes if stat == "MIN" else pred[stat]["mean"])
            )
            last5 = float(np.mean([r[stat] for r in history[pid]])) if history[pid] else initial
            rows.append(
                {
                    "season": season,
                    "date": str(row["GAME_DATE"].date()),
                    "player_id": pid,
                    "game_id": str(row["GAME_ID"]),
                    "stat": stat,
                    "actual": float(row.get(stat, 0)),
                    "bayesian": pred[stat]["mean"],
                    "variance": max(pred[stat]["variance"], 1e-9),
                    "season_average": initial,
                    "last5": last5,
                    "ewma": ewma.get((pid, stat), initial),
                }
            )
            ewma[(pid, stat)] = 0.18 * float(row.get(stat, 0)) + 0.82 * ewma.get(
                (pid, stat), initial
            )
        trade = pid in teams and teams[pid] != int(row["TEAM_ID"])
        bp.update_stats(
            row["GAME_DATE"], float(row["MIN"]), row, is_event_reset=trade, game_id=row["GAME_ID"]
        )
        teams[pid] = int(row["TEAM_ID"])
        history[pid].append(row)
    return pd.DataFrame(rows), hashlib.sha256(path.read_bytes()).hexdigest()


def summarize_predictions(frame, scales=None):
    results = []
    for stat, group in frame.groupby("stat"):
        actual = group.actual.to_numpy()
        for model in ["season_average", "last5", "ewma", "bayesian"]:
            error = actual - group[model].to_numpy()
            result = {
                "stat": stat,
                "model": model,
                "n": len(group),
                "MAE": float(np.mean(abs(error))),
                "RMSE": float(np.sqrt(np.mean(error**2))),
            }
            if model == "bayesian":
                for label, scale in [
                    ("raw", 1.0),
                    ("validation_scaled", (scales or {}).get(stat, 1.0)),
                ]:
                    variance = group.variance.to_numpy() * scale
                    sd = np.sqrt(variance)
                    scored = dict(result, model="bayesian_" + label, variance_scale=scale)
                    for level, z in [(50, 0.67448975), (80, 1.28155157), (95, 1.95996398)]:
                        scored[f"coverage_{level}"] = float(np.mean(abs(error) <= z * sd))
                    scored["standardized_mse"] = float(np.mean(error**2 / variance))
                    if stat != "MIN":
                        mass = ndtr((actual + 0.5 - group.bayesian.to_numpy()) / sd) - ndtr(
                            (actual - 0.5 - group.bayesian.to_numpy()) / sd
                        )
                        scored["normal_bin_log_loss"] = float(
                            np.mean(-np.log(np.maximum(mass, 1e-15)))
                        )
                    results.append(scored)
            else:
                results.append(result)
    return pd.DataFrame(results)


def score_matchups(forecasts, outcomes):
    """Multiclass Brier/log loss + win reliability on archived weekly forecasts.

    Each forecast has id, forecast_at, win/loss/draw; each outcome has id,
    completed_at, result. Multiple snapshots are scored separately by caller
    chosen horizon, never silently mixed with forecasts after completion.
    """
    truth = {r["id"]: r for r in outcomes}
    errors = []
    reliability = []
    for row in forecasts:
        if row["id"] not in truth:
            continue
        target = truth[row["id"]]
        if pd.to_datetime(row["forecast_at"], utc=True) >= pd.to_datetime(
            target["completed_at"], utc=True
        ):
            raise ValueError("Forecast must precede matchup completion")
        probs = np.array([row[k] for k in ("win", "loss", "draw")], dtype=float)
        if not np.all(np.isfinite(probs)) or min(probs) < 0 or abs(probs.sum() - 1) > 1e-8:
            raise ValueError("Invalid W/L/D forecast")
        index = ("win", "loss", "draw").index(target["result"])
        observed = np.eye(3)[index]
        errors.append(
            (float(np.sum((probs - observed) ** 2)), -float(np.log(max(probs[index], 1e-15))))
        )
        reliability.append((min(9, int(probs[0] * 10)), probs[0], float(index == 0)))
    bins = []
    for b in range(10):
        values = [r for r in reliability if r[0] == b]
        if values:
            bins.append(
                {
                    "bin": b,
                    "n": len(values),
                    "predicted_win": float(np.mean([r[1] for r in values])),
                    "observed_win": float(np.mean([r[2] for r in values])),
                }
            )
    return {
        "n": len(errors),
        "brier": float(np.mean([e[0] for e in errors])) if errors else None,
        "log_loss": float(np.mean([e[1] for e in errors])) if errors else None,
        "win_reliability": bins,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation", default="2024_25")
    parser.add_argument("--test", default="2025_26")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "validation")
    args = parser.parse_args()
    if int(args.validation[:4]) >= int(args.test[:4]):
        parser.error("Validation season must precede the held-out test season")
    val, val_hash = walk_forward(args.validation)
    # Fit uncertainty scales only on validation outcomes; freeze for test.
    scales = {
        s: float(np.clip(np.mean((g.actual - g.bayesian) ** 2 / g.variance), 0.25, 8))
        for s, g in val.groupby("stat")
    }
    test, test_hash = walk_forward(args.test)
    args.output.mkdir(parents=True, exist_ok=True)
    summary = summarize_predictions(test, scales)
    summary.to_csv(args.output / "player_metrics.csv", index=False)
    test.to_parquet(args.output / "player_forecasts.parquet", index=False)
    standardized = val.assign(residual=(val.actual - val.bayesian) / np.sqrt(val.variance))
    standardized.pivot(
        index=["player_id", "game_id"], columns="stat", values="residual"
    ).corr().to_csv(args.output / "validation_residual_correlation.csv")
    metadata = {
        "validation_season": args.validation,
        "test_season": args.test,
        "validation_sha256": val_hash,
        "test_sha256": test_hash,
        "variance_scales": scales,
        "scope": "Per-game conditional on playing; not weekly matchup calibration",
        "positions": "Prior-season snapshot when available, otherwise pooled prior",
        "model": "Discounted gamma/beta moments, full minutes uncertainty, predict before update",
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "source_sha256": {
            name: hashlib.sha256((ROOT / "src" / name).read_bytes()).hexdigest()
            for name in ("bayesian_model.py", "priors.py", "validation.py")
        },
    }
    (args.output / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(summary.to_string(index=False))
    print(f"Saved reproducible validation artifacts to {args.output}")


if __name__ == "__main__":
    main()

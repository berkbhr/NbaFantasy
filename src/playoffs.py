"""Top-four qualification from category W/L/T standings and future fixtures.

No league fixtures or standings are invented. Ties at the qualification cutoff
are broken uniformly unless the caller supplies an actual tiebreak priority.
"""

import argparse
import json
from pathlib import Path

import numpy as np


def estimate_playoff_probabilities(
    standings,
    fixtures,
    playoff_spots=4,
    simulations=20000,
    seed=42,
    draw_value=0.5,
    tiebreak_priority=None,
):
    """standings: team -> category {W,L,T}; fixtures carry nine category marginals.

    Fixture categories: {category: {win: p, tie: t}}, home perspective.
    Category draws always count half a point. Future categories and weeks are
    conditionally independent. MC error excludes model error. draw_value is
    retained only to reject incompatible category-scoring configurations.
    """
    teams = sorted(standings, key=str)
    if not 1 <= playoff_spots <= len(teams) or simulations < 1 or draw_value != 0.5:
        raise ValueError("Invalid playoff simulation configuration")
    index = {team: i for i, team in enumerate(teams)}
    scores = np.zeros((simulations, len(teams)))
    games = np.zeros(len(teams))
    for team, record in standings.items():
        values = [float(record.get(k, 0)) for k in ("W", "L", "T")]
        if not np.all(np.isfinite(values)) or min(values) < 0:
            raise ValueError("Standings must be nonnegative finite W/L/T records")
        scores[:, index[team]] = values[0] + draw_value * values[2]
        games[index[team]] = sum(values)
    rng = np.random.default_rng(seed)
    seen = set()
    for fixture in fixtures:
        home, away = fixture["home"], fixture["away"]
        if home not in index or away not in index or home == away:
            raise ValueError("Fixture teams must be distinct known teams")
        for team in (home, away):
            key = (fixture["week"], team)
            if key in seen:
                raise ValueError("A team cannot play twice in one fantasy week")
            seen.add(key)
        categories = fixture.get("categories", {})
        if len(categories) != 9:
            raise ValueError(
                "Qualification needs nine category marginals, not a weekly W/L/D probability"
            )
        for marginal in categories.values():
            w, t = float(marginal["win"]), float(marginal.get("tie", 0))
            probs = np.array([w, 1 - w - t, t])
            if not np.all(np.isfinite(probs)) or min(probs) < -1e-12 or max(probs) > 1 + 1e-12:
                raise ValueError("Invalid category probabilities")
            probs = np.maximum(probs, 0)
            probs /= probs.sum()
            outcome = rng.choice(3, size=simulations, p=probs)
            scores[:, index[home]] += (outcome == 0) + 0.5 * (outcome == 2)
            scores[:, index[away]] += (outcome == 1) + 0.5 * (outcome == 2)
        games[index[home]] += 9
        games[index[away]] += 9
    if np.any(games == 0):
        raise ValueError("Each team needs at least one completed or remaining matchup")
    percentages = scores / games
    if tiebreak_priority is None:
        tie_order = rng.random(percentages.shape)
    else:
        if set(tiebreak_priority) != set(teams) or len(tiebreak_priority) != len(teams):
            raise ValueError("Tiebreak priority must list each team exactly once")
        tie_order = np.broadcast_to(
            np.array([len(teams) - tiebreak_priority.index(t) for t in teams]), percentages.shape
        )
    # Lexicographic sorting avoids allowing random jitter to reverse non-ties.
    ranks = np.lexsort((-tie_order, -percentages), axis=1)
    qualified = np.zeros_like(scores, dtype=bool)
    np.put_along_axis(qualified, ranks[:, :playoff_spots], True, axis=1)
    result = {}
    for team, i in index.items():
        p = float(qualified[:, i].mean())
        result[team] = {
            "playoff_probability": p,
            "mc_standard_error": float(np.sqrt(p * (1 - p) / simulations)),
            "expected_final_category_percentage": float(percentages[:, i].mean()),
        }
    return {
        "teams": result,
        "playoff_spots": playoff_spots,
        "simulations": simulations,
        "seed": seed,
        "draw_value": draw_value,
        "tiebreak": "uniform cutoff tie" if tiebreak_priority is None else "provided priority",
        "scoring": "Category wins + 0.5 category ties, divided by categories played",
        "assumption": "Future categories and fixtures independent conditional on supplied probabilities",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON with standings and remaining fixtures")
    parser.add_argument("--output", type=Path, default=Path("reports/playoff_forecast.json"))
    parser.add_argument("--simulations", type=int, default=20000)
    args = parser.parse_args()
    state = json.loads(args.input.read_text(encoding="utf-8"))
    result = estimate_playoff_probabilities(
        state["standings"],
        state["fixtures"],
        playoff_spots=4,
        simulations=args.simulations,
        draw_value=state.get("draw_value", 0.5),
        tiebreak_priority=state.get("tiebreak_priority"),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()

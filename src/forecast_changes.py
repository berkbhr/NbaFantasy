"""Explain weekly forecast updates with frozen moments, not a hindsight story."""

import gzip
import json
import math
from collections import defaultdict
from pathlib import Path

from .matchup_engine import ALL_CATEGORIES, COUNT_STATS, MatchupEngine


def freeze_games(distribution, players):
    days = defaultdict(list)
    for day, ids in sorted(distribution["meta"]["lineups"].items()):
        for pid in ids:
            days[str(pid)].append(day)
    records = []
    for player in distribution.get("players", []):
        pid = player["id"]
        dates = days[str(pid)]
        if len(dates) != len(player["games"]):
            raise ValueError("Cannot match dated projections to their frozen lineup")
        for day, game in zip(dates, player["games"]):
            if game["g"] != 1:
                raise ValueError("Update explanations require dated games")
            records.append(
                {
                    "date": day,
                    "id": pid,
                    "name": players[pid].name,
                    "injury_status": players[pid].injury_status,
                    "p": game["p"],
                    "mean": game["mean"],
                    "var": game["var"],
                }
            )
    return {
        "games": records,
        "availability_correlation": distribution["meta"].get("availability_correlation", 0),
    }


def aggregate(frozen):
    mean = dict.fromkeys(ALL_CATEGORIES, 0.0)
    variance = dict.fromkeys(ALL_CATEGORIES + ["FGM_cond", "FTM_cond"], 0.0)
    by_player = defaultdict(list)
    rho = frozen.get("availability_correlation", 0)
    for game in frozen["games"]:
        p, mu, vv = game["p"], game["mean"], game["var"]
        for cat in ALL_CATEGORIES:
            mean[cat] += p * mu[cat]
            variance[cat] += p * vv[cat] + p * (1 - p) * mu[cat] ** 2
        for cat in ("FGM_cond", "FTM_cond"):
            variance[cat] += p * vv[cat]
        by_player[str(game["id"])].append({"g": 1, "p": p, "mean": mu, "var": vv})
    for games in by_player.values():
        for i, a in enumerate(games):
            for b in games[i + 1 :]:
                pa, pb = a["p"], b["p"]
                cov = min(rho * math.sqrt(pa * (1 - pa) * pb * (1 - pb)), min(pa, pb) - pa * pb)
                for cat in ALL_CATEGORIES:
                    shared = math.sqrt(
                        a["var"].get(cat + "_shared", 0) * b["var"].get(cat + "_shared", 0)
                    )
                    variance[cat] += 2 * (
                        (pa * pb + cov) * shared + cov * a["mean"][cat] * b["mean"][cat]
                    )
    return {
        "mean": mean,
        "var": variance,
        "players": [{"id": pid, "games": games} for pid, games in by_player.items()],
        "meta": {"availability_correlation": rho},
    }


def actual(snapshot, side):
    return snapshot.get("live_score", {}).get("team_a" if side == "mine" else "team_b", {})


def probabilities(future, scores):
    distributions = [
        MatchupEngine.combine_live_and_remaining_dist(scores[side], aggregate(future[side]))
        for side in ("mine", "opponent")
    ]
    return MatchupEngine.evaluate_h2h_matchup(*distributions)[1]


def compare(previous, current):
    if previous.get("id") != current.get("id") or previous.get("week_end") != current.get(
        "week_end"
    ):
        return {"status": "different_matchup"}
    if not previous.get("live_score_valid") or not current.get("live_score_valid"):
        return {"status": "unverified_score"}
    if not previous.get("update_evidence") or not current.get("update_evidence"):
        return {"status": "previous_detail_unavailable", "previous_at": previous.get("forecast_at")}
    core = (
        "bayesian_model.py",
        "priors.py",
        "model_policy.py",
        "rotation.py",
        "rotation_policy.py",
        "matchup_engine.py",
        "probability.py",
        "forecast_changes.py",
    )
    for name in core:
        if previous.get("model_source_sha256_LF", {}).get(name) != current.get(
            "model_source_sha256_LF", {}
        ).get(name):
            return {"status": "model_changed", "previous_at": previous.get("forecast_at")}
    evidence = previous["update_evidence"]
    future = {s: evidence[s] for s in ("mine", "opponent")}
    old_scores = {s: actual(previous, s) for s in future}
    recreated = probabilities(future, old_scores)
    if any(abs(recreated[c] - previous["categories"][c]["win"]) > 0.002 for c in recreated):
        return {"status": "moment_reconstruction_mismatch"}
    completed = {(str(r["id"]), r["date"]): r for r in current["update_evidence"]["completed"]}
    retained, resolved_scores, surprises = {}, {}, []
    for side in future:
        done = [g for g in future[side]["games"] if (str(g["id"]), g["date"]) in completed]
        retained[side] = {
            **future[side],
            "games": [
                g for g in future[side]["games"] if (str(g["id"]), g["date"]) not in completed
            ],
        }
        resolved_scores[side] = {
            c: float(old_scores[side].get(c, 0)) + sum(g["p"] * g["mean"][c] for g in done)
            for c in ALL_CATEGORIES
        }
        for game in done:
            result = completed[(str(game["id"]), game["date"])]
            surprises.append(
                {
                    "side": side,
                    "name": game["name"],
                    "date": game["date"],
                    "expected": {c: game["p"] * game["mean"][c] for c in COUNT_STATS},
                    "observed": result["stats"],
                }
            )
    resolved = probabilities(retained, resolved_scores)
    new_scores = {s: actual(current, s) for s in future}
    scored = probabilities(retained, new_scores)
    remaining_players = []
    for side in future:
        before, after = defaultdict(list), defaultdict(list)
        for game in retained[side]["games"]:
            before[str(game["id"])].append(game)
        for game in current["update_evidence"][side]["games"]:
            after[str(game["id"])].append(game)
        for pid in before.keys() | after.keys():
            old_games, new_games = before[pid], after[pid]
            exemplar = (new_games or old_games)[0]
            remaining_players.append(
                {
                    "side": side,
                    "name": exemplar["name"],
                    "old_active_games": len(old_games),
                    "new_active_games": len(new_games),
                    "old_status": old_games[0].get("injury_status") if old_games else None,
                    "new_status": new_games[0].get("injury_status") if new_games else None,
                    "old_minutes": sum(g["mean"].get("MIN", 0) for g in old_games) / len(old_games)
                    if old_games
                    else None,
                    "new_minutes": sum(g["mean"].get("MIN", 0) for g in new_games) / len(new_games)
                    if new_games
                    else None,
                    "delta": {
                        c: sum(g["p"] * g["mean"][c] for g in new_games)
                        - sum(g["p"] * g["mean"][c] for g in old_games)
                        for c in COUNT_STATS
                    },
                }
            )
    rows = []
    for cat in recreated:
        old, new = previous["categories"][cat]["win"], current["categories"][cat]["win"]
        row = {
            "category": cat,
            "before": old,
            "after": new,
            "games_resolved_pp": 100 * (resolved[cat] - old),
            "score_surprise_pp": 100 * (scored[cat] - resolved[cat]),
            "remaining_outlook_pp": 100 * (new - scored[cat]),
        }
        if cat in COUNT_STATS:
            row["remaining_player_changes"] = [
                {
                    **{k: v for k, v in r.items() if k != "delta"},
                    "expected_stat_change": r["delta"][cat],
                }
                for r in sorted(
                    remaining_players, key=lambda r: abs(r["delta"][cat]), reverse=True
                )[:3]
            ]
            row["score_added"] = {
                s: float(new_scores[s].get(cat, 0)) - float(old_scores[s].get(cat, 0))
                for s in future
            }
            row["score_expected"] = {
                s: resolved_scores[s][cat] - float(old_scores[s].get(cat, 0)) for s in future
            }
            leaders = sorted(
                surprises,
                key=lambda r: abs(r["observed"].get(cat, 0) - r["expected"][cat]),
                reverse=True,
            )
            row["planned_player_surprises"] = [
                {
                    "side": r["side"],
                    "name": r["name"],
                    "date": r["date"],
                    "expected": r["expected"][cat],
                    "observed": r["observed"].get(cat, 0),
                }
                for r in leaders[:3]
            ]
        rows.append(row)
    return {
        "status": "explained",
        "previous_at": previous["forecast_at"],
        "method": "Sequential: resolve old planned games at expected scores, replace with actual scores, then update remaining outlook. Order-dependent arithmetic attribution, not causal identification.",
        "player_note": "Player examples use planned lineup NBA boxscores; actual Yahoo daily starting slots may differ.",
        "categories": sorted(rows, key=lambda r: abs(r["after"] - r["before"]), reverse=True),
    }


def archived_comparisons(current, archive):
    candidates = []
    for path in sorted((Path(archive) / "predictions").glob("*.json.gz"), reverse=True):
        # File names use the cutoff's UTC date. Ignore earlier fantasy weeks.
        week = current["id"].split(":", 1)[0].replace("-", "")
        if path.name[:8] < week:
            break
        if (Path(archive) / "prediction_exclusions" / path.name).exists():
            continue
        try:
            value = json.loads(gzip.decompress(path.read_bytes())).get("primary", {})
        except (ValueError, OSError):
            continue
        if (
            value.get("id") == current.get("id")
            and value.get("forecast_at", "") < current["forecast_at"]
        ):
            candidates.append(value)
    if not candidates:
        return {"status": "no_earlier_same_week_forecast"}
    latest, first = candidates[0], candidates[-1]
    return {
        "since_previous": compare(latest, current),
        "since_first_record": compare(first, current),
        "first_record_at": first["forecast_at"],
    }


def concise_lines(changes, limit=2):
    view = changes.get("since_previous", {})
    if view.get("status") != "explained":
        return []
    result = []
    for row in view["categories"]:
        if abs(row["after"] - row["before"]) < 0.1:
            continue
        label = row["category"].replace("_PCT", "%").replace("FG3M", "3PT")
        result.append(
            f"{label} %{100 * row['before']:.0f} → %{100 * row['after']:.0f}: "
            f"skor {row['score_surprise_pp']:+.0f}, kalan beklenti {row['remaining_outlook_pp']:+.0f}, "
            f"maçların tamamlanması {row['games_resolved_pp']:+.0f} yüzde puan."
        )
        if "score_added" in row:
            a, b = row["score_added"], row["score_expected"]
            result.append(
                f"Eklenen skor sen/rakip: {a['mine']:g}/{a['opponent']:g}; "
                f"önceki aktif kadro planının beklentisi: {b['mine']:.1f}/{b['opponent']:.1f}."
            )
        if len(result) >= limit * 2:
            break
    return result

"""Immutable prospective predictions, frozen inputs, shadow policy and later labels.

Never rewrite a prediction when results arrive. Labels live in a separate tree.
This is forecasting evaluation, not a causal add/drop experiment.
"""

import argparse
import gzip
import hashlib
import json
import sqlite3
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .bayesian_model import COUNT_STATS
from .boxscores import final_boxscore, roster_labels
from .historical_labels import fetch_day
from .injury_tracker import normalize_name

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data" / "archive"


def write_once(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, default=str, allow_nan=False
    ).encode()
    with path.open("xb") as handle:
        handle.write(gzip.compress(raw, mtime=0))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_record(path):
    record = json.loads(gzip.decompress(path.read_bytes()))
    for name, target in record.get("arm_aliases", {}).items():
        record["player_predictions"][name] = record["player_predictions"][target]
    return record


def archive_official_snapshot(parsed, source_url, pdf_bytes, accepted_for_live=None):
    checksum = hashlib.sha256(pdf_bytes).hexdigest()
    path = ARCHIVE / "injury_reports" / f"{checksum}.json.gz"
    if not path.exists():
        write_once(
            path,
            {
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "source_url": source_url,
                "pdf_sha256": checksum,
                "accepted_for_live": accepted_for_live,
                "parsed": parsed,
            },
        )
    return str(path.relative_to(ROOT))


def future_rows(assistant, engine, now):
    today = pd.Timestamp(now).tz_convert("America/New_York").tz_localize(None).normalize()
    target = today + pd.Timedelta(days=1)
    schedule = assistant.schedule_df.copy()
    schedule["GAME_DATE"] = pd.to_datetime(schedule.GAME_DATE).dt.normalize()
    games = schedule[schedule.GAME_DATE == target]
    rows = []
    for team in sorted(games.TEAM_ID.unique()):
        engine.recompute_team_depth_and_injury_minutes(game_date=target, as_of_date=today)
        for pid, bp in assistant.players.items():
            if engine.team_map.get(pid) != team:
                continue
            for game in games[games.TEAM_ID == team].to_dict("records"):
                prior = assistant.priors.get(pid, {})
                prior_mpg = prior.get("MIN", 0) / max(1, prior.get("GP", 0))
                raw_prediction = bp.predict_next_game(current_date=target)
                # Daily scoring needs marginal moments, not every intermediate
                # shared-covariance term. Eight significant digits preserve tiny
                # variances while reducing repeated archive size.
                prediction = {}
                for stat, values in raw_prediction.items():
                    fields = (
                        "mean",
                        "variance",
                        "rate",
                        "rate_variance",
                        "attempts",
                        "attempts_var",
                    )
                    prediction[stat] = {k: float(f"{values[k]:.8g}") for k in fields if k in values}
                b2b = not schedule[(schedule.TEAM_ID == team) & (schedule.GAME_DATE == today)].empty
                rows.append(
                    {
                        "player_id": pid,
                        "name": bp.name,
                        "team_id": int(team),
                        "team_code": game["TEAM_ABBREVIATION"],
                        "game_id": str(game["GAME_ID"]),
                        "game_date": str(target.date()),
                        "star": prior_mpg >= 25,
                        "prior_mpg": prior_mpg,
                        "status": bp.injury_status,
                        "status_as_of": bp.injury_report_date,
                        "availability": bp.get_effective_game_availability(
                            is_b2b=b2b, game_date=target, as_of_date=today
                        ),
                        "base_minutes": bp.base_expected_minutes,
                        "baseline_availability": bp.availability_rate,
                        "observed_gp": int(getattr(bp, "current_season_gp", 0)),
                        "observed_mpg": float(getattr(bp, "current_season_mpg", 0)),
                        "prediction": prediction,
                    }
                )
    return rows


def record_run(include_recommendations=True, fetch_results=False):
    from .forecast import build_local_forecast, local_source_paths

    # Use the actual clock; this entry point deliberately has no historical --as-of option.
    cutoff = datetime.now(timezone.utc)
    initial_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in local_source_paths()
        if path.exists()
    }
    primary, assistant, engine, _ = build_local_forecast(
        now=cutoff, include_recommendations=include_recommendations, return_context=True
    )
    shadow_policy = replace(assistant.model_policy, role="recent_blend")
    shadow, shadow_assistant, shadow_engine, _ = build_local_forecast(
        now=cutoff, include_recommendations=False, model_policy=shadow_policy, return_context=True
    )
    if (
        initial_hashes != primary["source_sha256"]
        or primary["source_sha256"] != shadow["source_sha256"]
    ):
        raise RuntimeError(
            "Input caches changed between primary and shadow forecasts; retry with stable inputs"
        )
    inputs = {
        "cutoff_at": cutoff.isoformat(),
        "source_sha256": primary["source_sha256"],
        "model_source_sha256": primary["model_source_sha256"],
        "protocol": json.loads((ROOT / "config" / "prospective_protocol.json").read_text()),
        "team_map": engine.team_map,
        "positions": assistant.pos_dict,
    }
    official = ROOT / "data/raw/injuries/latest_official_report.pdf"
    if official.exists():
        from .nba_injury_scraper import extract_text_from_pdf, parse_report_text

        raw = official.read_bytes()
        parsed = parse_report_text(extract_text_from_pdf(raw))
        inputs["official_report_archive"] = archive_official_snapshot(
            parsed, "local_rolling_cache", raw
        )
    for name in ("league_state.json", "live_matchup.json"):
        path = ROOT / "data" / "processed" / name
        inputs[name] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    database = ROOT / "data" / "processed" / "injuries.db"
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        inputs["active_injuries"] = [dict(r) for r in conn.execute("select * from active_injuries")]
    primary_rows = future_rows(assistant, engine, cutoff)
    shadow_rows = future_rows(shadow_assistant, shadow_engine, cutoff)
    from .rotation_policy import RotationPolicy

    active_rotation_policy = engine.rotation_policy
    engine.rotation_policy = RotationPolicy()
    untuned_rows = (
        future_rows(assistant, engine, cutoff)
        if active_rotation_policy != RotationPolicy()
        else None
    )
    enabled = engine.use_positional_depth_and_injury_boost
    engine.use_positional_depth_and_injury_boost = False
    spillover_off = future_rows(assistant, engine, cutoff)
    engine.use_positional_depth_and_injury_boost = enabled
    engine.low_role_boost_cap = 2
    low_role_cap2 = future_rows(assistant, engine, cutoff)
    engine.low_role_boost_cap = None
    engine.rotation_policy = active_rotation_policy
    research_path = ROOT / "config/rotation_candidate.json"
    research_rows = None
    research = (
        json.loads(research_path.read_text(encoding="utf-8")) if research_path.exists() else None
    )
    if research and RotationPolicy(**research["policy"]) != active_rotation_policy:
        engine.rotation_policy = RotationPolicy(**research["policy"])
        research_rows = future_rows(assistant, engine, cutoff)
        engine.rotation_policy = active_rotation_policy
    stamp = cutoff.strftime("%Y%m%dT%H%M%S%fZ")
    bundle = {
        "schema_version": 2,
        "numeric_precision": "Player marginal moments: 8 significant digits; live decisions retain full precision",
        "forecast_id": stamp,
        "cutoff_at": cutoff.isoformat(),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "inputs": inputs,
        "primary": primary,
        "shadow": shadow,
        "player_predictions": {
            "primary": primary_rows,
            "shadow": shadow_rows,
            "spillover_off": spillover_off,
            "low_role_cap2": low_role_cap2,
        },
        "arm_aliases": {},
        "role_status": "provisional",
        "horizon": "next_ET_calendar_day",
    }
    if untuned_rows is None:
        bundle["arm_aliases"]["rotation_untuned"] = "primary"
    else:
        bundle["player_predictions"]["rotation_untuned"] = untuned_rows
    if research:
        bundle["rotation_candidate"] = research
        if research_rows is None:
            bundle["arm_aliases"]["rotation_candidate"] = "primary"
        else:
            bundle["player_predictions"]["rotation_candidate"] = research_rows
    write_once(ARCHIVE / "predictions" / f"{stamp}.json.gz", bundle)
    settle(fetch_results=fetch_results)
    monitor()
    primary["prospective_forecast_id"] = stamp
    return primary


def realized_rows(bundle, logs, now, final_rosters=None):
    """Only explicit, completed-day boxscore rows become labels; missing != DNP."""
    today = pd.Timestamp(now).tz_convert("America/New_York").date()
    cutoff = pd.Timestamp(bundle["cutoff_at"])
    lookup = {(int(r["PLAYER_ID"]), str(r["GAME_ID"])): r for r in logs.to_dict("records")}
    final_rosters = final_rosters or {}
    labels = []
    for pred in bundle["player_predictions"]["primary"]:
        day = pd.Timestamp(pred["game_date"]).date()
        if day <= cutoff.tz_convert("America/New_York").date():
            raise ValueError("Forecast was not strictly before the target calendar day")
        if day >= today:
            continue
        key = (pred["player_id"], pred["game_id"])
        actual = lookup.get(key)
        roster = final_rosters.get(key)
        if actual is not None and actual.get("GAME_DATE") is not None:
            actual_day = pd.Timestamp(actual["GAME_DATE"]).date()
            if actual_day >= today or actual_day != day:
                continue  # Incomplete-day or rescheduled games are a different horizon.
        if roster is not None and roster["team_id"] != pred["team_id"]:
            continue
        if actual is None and (roster is None or roster["played"]):
            continue
        if actual is not None and int(actual["TEAM_ID"]) != pred["team_id"]:
            continue
        if actual is None:
            actual = dict.fromkeys(COUNT_STATS + ["MIN", "FGM", "FGA", "FTM", "FTA"], 0)
        labels.append(
            {
                "player_id": pred["player_id"],
                "game_id": pred["game_id"],
                "game_date": pred["game_date"],
                "played": bool(actual["MIN"] > 0),
                "availability_evaluable": roster is not None,
                "actual": {
                    s: float(actual[s]) for s in COUNT_STATS + ["MIN", "FGM", "FGA", "FTM", "FTA"]
                },
            }
        )
    return labels


def settle(fetch_results=False):
    path = ROOT / "data" / "raw" / "player_logs_2026_27.parquet"
    if not path.exists():
        return
    logs = pd.read_parquet(path)
    now = datetime.now(timezone.utc)
    final_rosters = {}
    checked_games = set()
    checked_days = {}
    for prediction in sorted((ARCHIVE / "predictions").glob("*.json.gz")):
        bundle = read_record(prediction)
        for pred in bundle["player_predictions"]["primary"]:
            if (
                pd.Timestamp(pred["game_date"]).date()
                >= pd.Timestamp(now).tz_convert("America/New_York").date()
            ):
                continue
            if pred["game_id"] in checked_games:
                continue
            checked_games.add(pred["game_id"])
            payload = final_boxscore(pred["game_id"], fetch=fetch_results)
            if payload:
                final_rosters.update(
                    {(r["player_id"], r["game_id"]): r for r in roster_labels(payload)}
                )
        for pred in bundle["player_predictions"]["primary"]:
            day = pred["game_date"]
            if pd.Timestamp(day).date() >= pd.Timestamp(now).tz_convert("America/New_York").date():
                continue
            if day not in checked_days:
                directory = ARCHIVE / "final_roster_labels"
                if fetch_results:
                    fetch_day(day, directory)
                cache = directory / f"{day}.json.gz"
                data = read_record(cache) if cache.exists() else {"rows": []}
                checked_days[day] = {(r["norm"], r["team_code"]): r for r in data["rows"]}
            label = checked_days[day].get((normalize_name(pred["name"]), pred.get("team_code")))
            if label:
                final_rosters[(pred["player_id"], pred["game_id"])] = {
                    "team_id": pred["team_id"],
                    "played": label["played"],
                    "source": "ESPN_final_roster",
                }
        labels = realized_rows(bundle, logs, now, final_rosters)
        if not labels:
            continue
        # Content-address revisions: partial results/corrections can be appended,
        # while earlier observed labels remain available for an audit.
        content = hashlib.sha256(json.dumps(labels, sort_keys=True).encode()).hexdigest()[:16]
        destination = (
            ARCHIVE / "outcomes" / prediction.stem.replace(".json", "") / f"{content}.json.gz"
        )
        if not destination.exists():
            write_once(
                destination,
                {
                    "forecast_id": bundle["forecast_id"],
                    "observed_at": now.isoformat(),
                    "prediction_sha256": hashlib.sha256(prediction.read_bytes()).hexdigest(),
                    "logs_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "labels": labels,
                },
            )


def monitor():
    """Descriptive paired metrics; no repeated daily significance tests."""
    selected = {}
    spill_selected = {}
    cap_selected = {}
    rotation_selected = {}
    research_selected = {}
    from .rotation_policy import RotationPolicy, load_rotation_policy

    def policy_key(value):
        return json.dumps(RotationPolicy(**value).to_dict(), sort_keys=True)

    current_policy_key = policy_key(load_rotation_policy().to_dict())
    for path in sorted((ARCHIVE / "predictions").glob("*.json.gz")):
        bundle = read_record(path)
        outcomes = sorted(
            (ARCHIVE / "outcomes" / bundle["forecast_id"]).glob("*.json.gz"),
            key=lambda p: read_record(p)["observed_at"],
        )
        if not outcomes:
            continue
        labels = {(r["player_id"], r["game_id"]): r for r in read_record(outcomes[-1])["labels"]}
        shadow = {(r["player_id"], r["game_id"]): r for r in bundle["player_predictions"]["shadow"]}
        off = {
            (r["player_id"], r["game_id"]): r
            for r in bundle["player_predictions"].get("spillover_off", [])
        }
        capped = {
            (r["player_id"], r["game_id"]): r
            for r in bundle["player_predictions"].get("low_role_cap2", [])
        }
        untuned = {
            (r["player_id"], r["game_id"]): r
            for r in bundle["player_predictions"].get("rotation_untuned", [])
        }
        research = {
            (r["player_id"], r["game_id"]): r
            for r in bundle["player_predictions"].get("rotation_candidate", [])
        }
        for pred in bundle["player_predictions"]["primary"]:
            key = (pred["player_id"], pred["game_id"])
            if key not in research_selected and key in labels and key in research:
                research_selected[key] = {
                    "prediction": pred,
                    "candidate": research[key],
                    "label": labels[key],
                }
            if key not in rotation_selected and key in labels and key in untuned:
                rotation_selected[key] = {
                    "prediction": pred,
                    "untuned": untuned[key],
                    "label": labels[key],
                }
            if key not in cap_selected and key in labels and key in capped:
                cap_selected[key] = {
                    "prediction": untuned.get(key, pred),
                    "capped": capped[key],
                    "label": labels[key],
                }
            if key not in spill_selected and key in labels and key in off:
                spill_selected[key] = {"prediction": pred, "off": off[key], "label": labels[key]}
            if key in selected or key not in labels or key not in shadow:
                continue
            selected[key] = {
                "prediction": pred,
                "shadow": shadow[key],
                "label": labels[key],
                "policy": policy_key(
                    bundle.get("primary", {}).get("rotation_policy", RotationPolicy().to_dict())
                ),
            }
    result = {
        "status": "provisional",
        "unique_player_games": len(selected),
        "review": "pending",
        "note": "Earliest next-day forecast only; no causal category-gain claim",
    }
    for name, star_only in (("all", False), ("stars", True)):
        records = [
            r
            for r in selected.values()
            if r["label"]["played"] and (not star_only or r["prediction"]["star"])
        ]
        metrics = {"n": len(records), "game_dates": len({r["label"]["game_date"] for r in records})}
        for arm in ("prediction", "shadow"):
            if records:
                metrics[arm + "_minute_mae"] = sum(
                    abs(r[arm]["prediction"]["MIN"]["mean"] - r["label"]["actual"]["MIN"])
                    for r in records
                ) / len(records)
        result[name] = metrics
    groups = {}
    for policy in sorted({r["policy"] for r in selected.values()}):
        records = [
            r
            for r in selected.values()
            if r["policy"] == policy and r["label"]["played"] and r["prediction"]["star"]
        ]
        groups[policy] = {
            "n": len(records),
            "game_dates": len({r["label"]["game_date"] for r in records}),
        }
    result["star_rotation_policy_groups"] = groups
    active_group = groups.get(current_policy_key, {"n": 0, "game_dates": 0})
    result["review_ready"] = active_group["n"] >= 1000 and active_group["game_dates"] >= 42
    result["review_rotation_policy"] = current_policy_key
    spill = [r for r in spill_selected.values() if r["label"]["played"]]
    result["spillover_descriptive"] = {"n": len(spill)}
    if spill:
        for arm in ("prediction", "off"):
            result["spillover_descriptive"][arm + "_minute_mae"] = sum(
                abs(r[arm]["prediction"]["MIN"]["mean"] - r["label"]["actual"]["MIN"])
                for r in spill
            ) / len(spill)
    availability = [r for r in selected.values() if r["label"].get("availability_evaluable")]
    low_role = [
        r
        for r in cap_selected.values()
        if r["label"]["played"]
        and r["prediction"].get("observed_gp", 0) >= 2
        and r["prediction"].get("observed_mpg", 20) < 10
    ]
    result["low_role_cap_descriptive"] = {"n": len(low_role), "adoption": "none"}
    for arm in ("prediction", "capped"):
        if low_role:
            error = [
                r[arm]["prediction"]["MIN"]["mean"] - r["label"]["actual"]["MIN"] for r in low_role
            ]
            result["low_role_cap_descriptive"][arm] = {
                "minute_mae": sum(abs(v) for v in error) / len(error),
                "overprediction": sum(max(v, 0) for v in error) / len(error),
                "underprediction": sum(max(-v, 0) for v in error) / len(error),
            }
    result["availability_descriptive"] = {"n": len(availability)}
    rotation_records = [r for r in rotation_selected.values() if r["label"]["played"]]
    result["rotation_tuning_descriptive"] = {"n": len(rotation_records)}
    research_records = [r for r in research_selected.values() if r["label"]["played"]]
    result["rotation_research_candidate"] = {
        "n": len(research_records),
        "adoption": "not_automatic",
    }
    for arm in ("prediction", "candidate"):
        if research_records:
            errors = [
                r[arm]["prediction"]["MIN"]["mean"] - r["label"]["actual"]["MIN"]
                for r in research_records
            ]
            result["rotation_research_candidate"][arm] = {
                "mse": sum(v * v for v in errors) / len(errors),
                "mae": sum(abs(v) for v in errors) / len(errors),
            }
            import math

            for cohort, rows in (
                ("all", research_records),
                (
                    "early",
                    [r for r in research_records if r["prediction"].get("observed_gp", 0) < 10],
                ),
            ):
                scored = []
                for record in rows:
                    variance = record[arm]["prediction"]["MIN"].get("variance")
                    if variance is not None and variance > 0:
                        error = (
                            record[arm]["prediction"]["MIN"]["mean"]
                            - record["label"]["actual"]["MIN"]
                        )
                        scored.append(
                            (
                                0.5 * (math.log(2 * math.pi * variance) + error * error / variance),
                                abs(error) <= 1.95996398454 * math.sqrt(variance),
                            )
                        )
                result["rotation_research_candidate"][arm][cohort + "_uncertainty"] = {
                    "n": len(scored),
                    "nll": sum(v[0] for v in scored) / len(scored) if scored else None,
                    "coverage95": sum(v[1] for v in scored) / len(scored) if scored else None,
                }
    for arm in ("prediction", "untuned"):
        if rotation_records:
            errors = [
                r[arm]["prediction"]["MIN"]["mean"] - r["label"]["actual"]["MIN"]
                for r in rotation_records
            ]
            result["rotation_tuning_descriptive"][arm] = {
                "mse": sum(v * v for v in errors) / len(errors),
                "mae": sum(abs(v) for v in errors) / len(errors),
            }
    if availability:
        result["availability_descriptive"]["brier"] = sum(
            (r["prediction"]["availability"] - r["label"]["played"]) ** 2 for r in availability
        ) / len(availability)
    if result["review_ready"]:
        result["review"] = "Ready for single preregistered review; no automatic promotion"
    path = ROOT / "reports" / "prospective_status.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")


def weekly_category_outcome(a, b):
    from .snapshots import BOX_SCORE_KEYS

    for team in (a, b):
        if any(s not in team or not np_is_finite_nonnegative(team[s]) for s in BOX_SCORE_KEYS):
            raise ValueError("Complete finite final category totals required")
        if any(float(team[s + "M"]) > float(team[s + "A"]) for s in ("FG", "FT")):
            raise ValueError("Makes exceed attempts")
    a = {key: float(a[key]) for key in BOX_SCORE_KEYS}
    b = {key: float(b[key]) for key in BOX_SCORE_KEYS}
    categories = {}
    for stat in COUNT_STATS + ["FG_PCT", "FT_PCT"]:
        if stat.endswith("_PCT"):
            s = stat[:2]
            # Zero attempts follows the engine's explicit zero-percentage convention.
            left = a[s + "M"] / a[s + "A"] if a[s + "A"] else 0
            right = b[s + "M"] / b[s + "A"] if b[s + "A"] else 0
        else:
            left, right = a[stat], b[stat]
        difference = left - right
        if stat.endswith("_PCT") and a[stat[:2] + "A"] and b[stat[:2] + "A"]:
            s = stat[:2]
            difference = a[s + "M"] * b[s + "A"] - b[s + "M"] * a[s + "A"]
        if stat == "TOV":
            difference = -difference
        categories[stat] = "win" if difference > 0 else "loss" if difference < 0 else "draw"
    wins, ties = list(categories.values()).count("win"), list(categories.values()).count("draw")
    losses = 9 - wins - ties
    return {
        "categories": categories,
        "category_points": wins + 0.5 * ties,
        "result": "win" if wins > losses else "loss" if losses > wins else "draw",
    }


def np_is_finite_nonnegative(value):
    import math

    return math.isfinite(float(value)) and float(value) >= 0


def settle_weekly(yahoo_client=None, final=None):
    """Only explicit postevent Yahoo outcomes or supplied final snapshots qualify."""
    now = datetime.now(timezone.utc)
    fetched = {}
    for path in sorted((ARCHIVE / "predictions").glob("*.json.gz")):
        bundle = read_record(path)
        forecast = bundle["primary"]
        if not forecast.get("live_score_valid"):
            continue
        if (
            pd.Timestamp(forecast["week_end"]).date()
            >= pd.Timestamp(now).tz_convert("America/New_York").date()
        ):
            continue
        if list((ARCHIVE / "weekly_outcomes" / bundle["forecast_id"]).glob("*.json.gz")):
            continue
        snapshot = bundle["inputs"].get("live_matchup.json") or {}
        week = snapshot.get("week")
        matchup = snapshot.get("matchup", {})
        my_slot, opp_slot = (
            matchup.get("team_a", {}).get("slot"),
            matchup.get("team_b", {}).get("slot"),
        )
        outcome = final
        if outcome is None and yahoo_client is not None and week:
            if week not in fetched:
                fetched[week] = yahoo_client.fetch_live_scoreboard(week=week)
            board = fetched[week] or {}
            for pair, state in zip(board.get("matchups", []), board.get("matchup_states", [])):
                if state.get("status") != "postevent" or set(state["slots"]) != {my_slot, opp_slot}:
                    continue
                if state.get("week_end") != forecast["week_end"]:
                    continue
                teams = {p["slot"]: p for p in pair}
                outcome = {
                    "week": week,
                    "final": True,
                    "week_end": state["week_end"],
                    "team_a": teams[my_slot],
                    "team_b": teams[opp_slot],
                    "observed_at": now.isoformat(),
                    "source": "Yahoo_postevent",
                }
        if (
            not outcome
            or not outcome.get("final")
            or outcome.get("week") != week
            or outcome.get("week_end") != forecast["week_end"]
        ):
            continue
        if outcome["team_a"].get("slot") != my_slot or outcome["team_b"].get("slot") != opp_slot:
            continue
        value = {
            "forecast_id": bundle["forecast_id"],
            "observed_at": now.isoformat(),
            "final_snapshot": outcome,
            **weekly_category_outcome(outcome["team_a"], outcome["team_b"]),
        }
        write_once(ARCHIVE / "weekly_outcomes" / bundle["forecast_id"] / "final.json.gz", value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settle-only", action="store_true")
    parser.add_argument("--weekly-final", type=Path)
    args = parser.parse_args()
    if args.weekly_final:
        settle_weekly(final=json.loads(args.weekly_final.read_text(encoding="utf-8")))
    elif args.settle_only:
        settle()
        monitor()
    else:
        result = record_run()
        print("Recorded prospective forecast:", result["prospective_forecast_id"])


if __name__ == "__main__":
    main()

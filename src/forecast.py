"""Generate a forecast from local caches, without network access or notifications."""

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import draft_data
from .live_draft_assistant import LiveDraftAssistant
from .matchup_engine import MatchupEngine
from .settings import load_settings
from .snapshots import fantasy_week_window, validate_live_snapshot

ROOT = Path(__file__).resolve().parents[1]


def local_source_paths():
    paths = [
        ROOT / "data" / "raw" / f"player_logs_{season}.parquet"
        for season in ("2024_25", "2025_26", "2026_27")
    ]
    paths += [ROOT / "data" / "raw" / "preseason_logs_2026_27.parquet"]
    paths += [
        ROOT / "data" / "processed" / name
        for name in (
            "league_state.json",
            "live_matchup.json",
            "injuries.db",
            "active_roster_2026_27.parquet",
            "player_positions.parquet",
            "schedule_2026_27.parquet",
        )
    ]
    paths += [
        ROOT / "config" / name
        for name in ("model_policy.json", "league.json", "prospective_protocol.json")
    ]
    return paths


def build_local_forecast(
    now=None, include_recommendations=True, model_policy=None, return_context=False
):
    now = now or datetime.now(timezone.utc)
    settings = load_settings()
    assistant = LiveDraftAssistant(
        use_live_injuries=False,
        objective=settings.objective,
        draw_value=settings.draw_value,
        model_policy=model_policy,
    )
    logs_path = ROOT / "data" / "raw" / "player_logs_2026_27.parquet"
    logs = pd.read_parquet(logs_path) if logs_path.exists() else pd.DataFrame()
    if not logs.empty:
        # A historical as-of run may never consume future cached observations.
        day = pd.Timestamp(now).tz_convert("America/New_York").tz_localize(None).normalize()
        logs = logs[pd.to_datetime(logs.GAME_DATE) < day].copy()
        assistant.apply_current_season_logs(logs)
    db = ROOT / "data" / "processed" / "injuries.db"
    if db.exists():
        # Read-only SQLite: evaluating a forecast must not change live injuries.
        with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute("SELECT * FROM active_injuries"):
                item = dict(row)
                pid = item["player_id"]
                if pid not in assistant.players:
                    pid = assistant.resolve_player_id(
                        item.get("player_name", ""), only_available=False
                    )
                if pid in assistant.players:
                    assistant.players[pid].update_injury_status(
                        item["status"],
                        desc=item.get("injury_desc", ""),
                        is_b2b_rest=bool(item.get("is_b2b_rest")),
                        expected_return=item.get("expected_return"),
                        report_date=item.get("updated_at"),
                    )
    state_path = ROOT / "data" / "processed" / "league_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    roster_names = {str(k): v for k, v in draft_data.build_rosters().items()}
    roster_names.update(state.get("rosters", {}))
    rosters = draft_data.resolve_rosters(assistant, {int(k): v for k, v in roster_names.items()})
    live_path = ROOT / "data" / "processed" / "live_matchup.json"
    live = None
    notes = []
    if live_path.exists():
        try:
            live = validate_live_snapshot(json.loads(live_path.read_text(encoding="utf-8")), now)
        except ValueError as exc:
            notes.append(str(exc))
    my_slot = draft_data.MY_TEAM_IDX
    opponent = int(live["team_b"].get("slot", 13)) - 1 if live else 12
    if opponent not in rosters or opponent == my_slot:
        raise ValueError("Opponent slot must identify a different known team")
    start, end = fantasy_week_window(now, True)
    if assistant.schedule_df.empty:
        raise ValueError("Current-season schedule is required for a live forecast")
    positions = pd.DataFrame(
        [{"PLAYER_ID": pid, "POSITION": pos} for pid, pos in assistant.pos_dict.items()]
    )
    engine = MatchupEngine(
        assistant.players,
        assistant.schedule_df,
        positions,
        team_map=dict(assistant.engine.team_map),
        use_positional_depth_and_injury_boost=True,
        objective=settings.objective,
        draw_value=settings.draw_value,
        max_weekly_adds=settings.max_weekly_adds,
    )
    engine.completed_game_ids = set(logs.GAME_ID.astype(str)) if not logs.empty else set()
    for names in state.get("il_slots", {}).values():
        for name in names:
            pid = assistant.resolve_player_id(name, only_available=False)
            if pid is not None:
                engine.yahoo_already_stashed_ids.add(pid)
    a = live["team_a"] if live else {}
    b = live["team_b"] if live else {}
    my, opp, points, probabilities, _ = engine.project_matchup(
        rosters[my_slot], rosters[opponent], start, end, my_actual_stats=a, opp_actual_stats=b
    )
    outcome = engine.compute_matchup_outcome(probabilities)
    protected = {
        assistant.resolve_player_id(name, only_available=False)
        for name in settings.protected_player_names
    }
    engine.protected_player_ids = protected - {None}
    recommendations = []
    if include_recommendations and live:
        occupied = {pid for roster in rosters.values() for pid in roster}
        # Cached waiver dates remain constraints, never guessed from drop time.
        waivers = {}
        for name, info in state.get("waivers", {}).items():
            pid = assistant.resolve_player_id(name, only_available=False)
            if pid is not None:
                waivers[pid] = info
        recommendations = engine.recommend_add_drop_moves(
            rosters[my_slot],
            rosters[opponent],
            sorted(assistant.available_player_ids - occupied),
            start,
            end,
            my_actual_stats=a,
            opp_actual_stats=b,
            waivers_dict=waivers,
            adds_used=settings.adds_used_this_week,
        )
    elif not live:
        notes.append(
            "No valid live scoreboard: totals describe remaining games only; in-week add/drop recommendations withheld."
        )
    notes.extend(
        [
            "Local caches only; no data fetched and no notifications sent.",
            "Category marginals use moment/normal approximations. Weekly W/L/D assumes category independence.",
            "Return dates, rotations and future lineup choices remain model assumptions.",
        ]
    )
    sources = {}
    data_sources = local_source_paths()
    for path in data_sources:
        if path.exists():
            sources[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = {
        "forecast_at": now.isoformat(),
        "live_score_valid": live is not None,
        "model_policy": assistant.model_policy.to_dict(),
        "id": f"{fantasy_week_window(now, False)[0].date()}:{my_slot}:{opponent}",
        "model_source_sha256": {
            name: hashlib.sha256((ROOT / "src" / name).read_bytes()).hexdigest()
            for name in (
                "bayesian_model.py",
                "priors.py",
                "model_policy.py",
                "live_draft_assistant.py",
                "matchup_engine.py",
                "probability.py",
                "rotation.py",
                "prospective.py",
                "snapshots.py",
            )
        },
        "week_start": str(start.date()),
        "week_end": str(end.date()),
        "my_team": draft_data.TEAM_NAMES[my_slot],
        "opponent": draft_data.TEAM_NAMES[opponent],
        "phase": settings.phase,
        "objective": settings.objective,
        "objective_value": engine.matchup_utility(probabilities),
        "expected_category_points": points,
        "expected_category_wins": sum(probabilities.values()),
        "expected_category_ties": sum(probabilities.ties.values()),
        "win": outcome.win,
        "loss": outcome.loss,
        "draw": outcome.draw,
        "categories": {
            c: {"win": p, "tie": probabilities.ties[c], "loss": 1 - p - probabilities.ties[c]}
            for c, p in probabilities.items()
        },
        "my_projected_stats": my["mean"],
        "opponent_projected_stats": opp["mean"],
        "my_lineups": {
            d: [assistant.players[i].name for i in ids] for d, ids in my["meta"]["lineups"].items()
        },
        "recommendations": recommendations,
        "notes": notes,
        "source_sha256": sources,
    }
    return (result, assistant, engine, logs) if return_context else result


def render_report(result):
    lines = [
        "# NBA Fantasy — cached-data forecast",
        "",
        f"Generated: {result['forecast_at']}",
        f"Matchup: **{result['my_team']} vs {result['opponent']}**",
        f"Window: {result['week_start']} – {result['week_end']}",
        "",
        f"Decision objective: `{result['objective']}` ({result['phase']}).",
        f"Objective value: **{result['objective_value']:.3f}**.",
        f"Expected category points: **{result['expected_category_points']:.2f} / 9**.",
        f"Expected category wins: {result['expected_category_wins']:.2f}; ties: {result['expected_category_ties']:.2f}.",
        f"Secondary weekly W/L/D: {result['win']:.1%} / {result['loss']:.1%} / {result['draw']:.1%}.",
        "",
        "| Category | Win | Tie | Loss |",
        "|---|---:|---:|---:|",
    ]
    for category, p in result["categories"].items():
        lines.append(f"| {category} | {p['win']:.1%} | {p['tie']:.1%} | {p['loss']:.1%} |")
    lines.extend(
        [
            "",
            "## Alternative add/drop recommendations",
            "",
            f"| Add | Drop | Δ {result['objective']} |",
            "|---|---|---:|",
        ]
    )
    for row in result["recommendations"]:
        lines.append(
            f"| {row['add_name']} | {row['drop_name']} | {row['delta_objective_value']:+.3f} |"
        )
    if not result["recommendations"]:
        lines.append("| No eligible recommendation | — | — |")
    lines.extend(["", "## Forecast active lineups", ""])
    for day, names in result["my_lineups"].items():
        lines.append(f"- {day}: {', '.join(names) or 'No active games'}")
    lines.extend(["", "## Assumptions and data quality", ""])
    lines.extend("- " + note for note in result["notes"])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-recommendations", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    from .prospective import record_run

    result = record_run(include_recommendations=not args.no_recommendations)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "latest_forecast.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )
    (args.output / "latest_cloud_summary.md").write_text(render_report(result), encoding="utf-8")
    archive = args.output / "forecasts"
    archive.mkdir(parents=True, exist_ok=True)
    stamp = pd.to_datetime(result["forecast_at"], utc=True).strftime("%Y%m%dT%H%M%S%fZ")
    (archive / f"{stamp}.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )
    print(f"Saved local forecast: {args.output / 'latest_cloud_summary.md'}")


if __name__ == "__main__":
    main()

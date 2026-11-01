"""Conditional playoff impact from actual standings and every remaining fixture.

This does not rank packages or infer standings. Missing current score coverage
produces needs_data rather than silently treating the current week as unplayed.
"""

import copy
import hashlib
import json
import time

import numpy as np
import pandas as pd

from .playoffs import estimate_playoff_probabilities
from .probability import category_points
from .snapshots import validate_live_snapshot, validate_pregame_window
from .trade_context import day
from .trade_packages import RosterScenario, trade_packages, validate_scenario
from .trade_projection_cache import TradeProjectionCache
from .trades import _pair


def _timestamp(value, now):
    stamp = pd.Timestamp(value)
    if pd.isna(stamp) or stamp.tzinfo is None:
        raise ValueError("Playoff source timestamp must be timezone-aware")
    age = pd.Timestamp(now) - stamp
    if age < -pd.Timedelta(minutes=5) or age > pd.Timedelta(hours=24):
        raise ValueError("Playoff standings/current scoreboard snapshot is stale or future-dated")
    return stamp


def _inputs(context, snapshot):
    if not snapshot or not str(snapshot.get("source", "")).startswith("yahoo_"):
        raise ValueError(
            "Actual Yahoo standings and current all-league raw scoreboard are required"
        )
    if not context.league_id or str(snapshot.get("league_id")) != context.league_id:
        raise ValueError("Playoff snapshot league identity does not match current rosters")
    if not context.team_slots or snapshot.get("team_slots") != context.team_slots:
        raise ValueError("Playoff snapshot Yahoo/canonical team mapping differs from rosters")
    _timestamp(snapshot.get("captured_at"), context.as_of)
    calendar = context.fantasy_calendar
    if not calendar.get("complete_remaining_season") or not calendar.get("current_week"):
        raise ValueError("Complete actual remaining normal-season fixture coverage is required")
    current = calendar["current_week"]
    if snapshot.get("completed_through_week") != current["week"] - 1:
        raise ValueError("Standings must exclude the in-progress week to avoid double counting")
    teams = set(context.rosters)
    records = snapshot.get("standings", {})
    if set(records) != teams:
        raise ValueError("Completed category W/L/T standings must cover every league team")
    totals = set()
    for record in records.values():
        values = [record.get(k) for k in ("W", "L", "T")]
        if any(
            type(v) not in (int, float) or not np.isfinite(v) or v < 0 or v != int(v)
            for v in values
        ):
            raise ValueError("Standings require finite nonnegative integer category W/L/T")
        totals.add(sum(values))
    if totals != {9 * snapshot["completed_through_week"]}:
        raise ValueError("Standings category totals disagree or include incomplete live categories")
    board = snapshot.get("current_scoreboard") or {}
    if board.get("week") != current["week"]:
        raise ValueError("Current all-league raw scoreboard is missing or belongs to another week")
    captured = board.get("updated_at", board.get("captured_at"))
    _timestamp(captured, context.as_of)
    stats, actual_pairs = {}, set()
    for pair in board.get("matchups", []):
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("Invalid current scoreboard pair")
        validated = validate_live_snapshot(
            {"updated_at": captured, "matchup": {"team_a": pair[0], "team_b": pair[1]}},
            context.as_of,
        )
        resolved = []
        for side in ("team_a", "team_b"):
            item = validated[side]
            team = str(int(item["slot"]) - 1)
            if team not in teams or team in stats:
                raise ValueError("Current scoreboard has unknown or duplicate canonical teams")
            stats[team] = item
            resolved.append(team)
        actual_pairs.add(tuple(sorted(resolved)))
    expected_pairs = {tuple(sorted(map(str, p))) for p in current["fixtures"]}
    if set(stats) != teams or actual_pairs != expected_pairs:
        raise ValueError("Raw current scores must cover every actual scheduled league matchup")
    validate_pregame_window(context.engine.schedule, context.as_of)
    return calendar, records, stats


def _current_pair(
    engine, ids_a, ids_b, start, end, as_of, starts_a, ends_a, starts_b, ends_b, actual_a, actual_b
):
    """Symmetric two-pass lineups use actual scores plus remaining moments."""

    def project(ids, actual, starts, ends, weights=None):
        remaining = engine.get_expected_weekly_distribution(
            ids,
            start,
            end,
            category_weights=weights,
            as_of_date=as_of,
            player_start_dates=starts,
            player_end_dates=ends,
        )
        return engine.combine_live_and_remaining_dist(actual, remaining)

    a, b = project(ids_a, actual_a, starts_a, ends_a), project(ids_b, actual_b, starts_b, ends_b)
    for _ in range(2):
        _, pa, wa = engine.evaluate_h2h_matchup(a, b)
        _, pb, wb = engine.evaluate_h2h_matchup(b, a)
        trial_a, trial_b = (
            project(ids_a, actual_a, starts_a, ends_a, wa),
            project(ids_b, actual_b, starts_b, ends_b, wb),
        )
        next_a = (
            trial_a
            if category_points(engine.evaluate_h2h_matchup(trial_a, b)[1]) > category_points(pa)
            else a
        )
        next_b = (
            trial_b
            if category_points(engine.evaluate_h2h_matchup(trial_b, a)[1]) > category_points(pb)
            else b
        )
        a, b = next_a, next_b
    return a, b


def _interval_rosters(original, scenario, effective):
    rosters = {team: list(scenario.projection_roster(team)) for team in scenario.rosters}
    starts = {team: dict(scenario.starts) for team in rosters}
    ends = {team: dict(scenario.ends) for team in rosters}
    for team in rosters:
        before, after = set(original.rosters[team]), set(rosters[team])
        for pid in before - after:
            rosters[team].append(pid)
            ends[team][pid] = min(ends[team].get(pid, effective), effective - pd.Timedelta(days=1))
        for pid in after - before:
            starts[team][pid] = max(starts[team].get(pid, effective), effective)
    return rosters, starts, ends


def _checkpoint(deadline):
    if deadline is not None and time.perf_counter() >= deadline:
        raise TimeoutError(
            "Playoff impact time budget exhausted; category trade analysis remains available"
        )


def _project_season(
    context, original, scenario, effective, calendar, actuals, cache, mode, eligibility, deadline
):
    engine = copy.deepcopy(context.engine)
    engine.pos_dict = dict(eligibility)
    engine.use_positional_depth_and_injury_boost = mode == "normal"
    engine.objective, engine.draw_value = "category_points", 0.5
    today = pd.Timestamp(context.as_of).tz_convert("America/New_York").tz_localize(None).normalize()
    current = calendar["current_week"]
    periods = [current] + calendar["weeks"]
    if pd.Timestamp(periods[-1]["end"]) > pd.to_datetime(engine.schedule.GAME_DATE).max():
        raise ValueError("NBA schedule does not cover the full remaining regular season")
    fixtures = []
    with engine.projection_session():
        for period in periods:
            _checkpoint(deadline)
            current_week = period["week"] == current["week"]
            selected = original if day(period["end"]) < effective else scenario
            crossing = day(period["start"]) < effective <= day(period["end"])
            if crossing:
                rosters, starts, ends = _interval_rosters(original, scenario, effective)
            else:
                rosters = {team: selected.projection_roster(team) for team in selected.rosters}
                starts = {team: selected.starts for team in rosters}
                ends = {team: selected.ends for team in rosters}
            engine.yahoo_already_stashed_ids = set(selected.stashed)
            engine_key = cache.engine_key(engine)
            for home, away in sorted(
                (tuple(map(str, p)) for p in period["fixtures"]), key=lambda p: tuple(sorted(p))
            ):
                _checkpoint(deadline)
                if current_week or crossing:
                    start = today if current_week else period["start"]
                    actual_a, actual_b = (
                        (actuals[home], actuals[away]) if current_week else (None, None)
                    )
                    pair_key = (
                        "dated_actuals",
                        engine_key,
                        cache.roster_key(
                            engine,
                            rosters[home],
                            start,
                            period["end"],
                            today,
                            starts[home],
                            ends[home],
                        ),
                        cache.roster_key(
                            engine,
                            rosters[away],
                            start,
                            period["end"],
                            today,
                            starts[away],
                            ends[away],
                        ),
                        hashlib.sha256(
                            json.dumps([actual_a, actual_b], sort_keys=True).encode()
                        ).digest(),
                    )
                    pair = cache.get_pair(pair_key)
                    if pair is None:
                        pair = _current_pair(
                            engine,
                            rosters[home],
                            rosters[away],
                            start,
                            period["end"],
                            today,
                            starts[home],
                            ends[home],
                            starts[away],
                            ends[away],
                            actual_a,
                            actual_b,
                        )
                        cache.put_pair(pair_key, pair)
                else:
                    pair = _pair(
                        engine,
                        rosters[home],
                        rosters[away],
                        period["start"],
                        period["end"],
                        today,
                        selected.starts,
                        selected.ends,
                        cache=cache,
                        engine_key=engine_key,
                    )
                _, probs, _ = engine.evaluate_h2h_matchup(*pair)
                fixtures.append(
                    {
                        "week": period["week"],
                        "home": home,
                        "away": away,
                        "categories": {
                            cat: {"win": float(probs[cat]), "tie": float(probs.ties[cat])}
                            for cat in sorted(probs)
                        },
                    }
                )
    return fixtures


def paired_qualification(
    standings,
    before_fixtures,
    after_fixtures,
    *,
    simulations=5000,
    seed=42,
    playoff_spots=8,
    tiebreak_priority=None,
):
    """Identical fixture/category ordering gives both simulations common draws."""

    def signatures(rows):
        return [(r["week"], r["home"], r["away"], list(r["categories"])) for r in rows]

    if signatures(before_fixtures) != signatures(after_fixtures):
        raise ValueError("Paired playoff simulation requires identical fixture/category order")
    arguments = dict(
        playoff_spots=playoff_spots,
        simulations=simulations,
        seed=seed,
        tiebreak_priority=tiebreak_priority,
        return_draws=True,
    )
    before = estimate_playoff_probabilities(standings, before_fixtures, **arguments)
    after = estimate_playoff_probabilities(standings, after_fixtures, **arguments)
    draw_before, draw_after = before.pop("_qualification_draws"), after.pop("_qualification_draws")
    result = {}
    for i, team in enumerate(sorted(standings, key=str)):
        difference = draw_after[:, i].astype(float) - draw_before[:, i].astype(float)
        result[team] = {
            "before": before["teams"][team]["playoff_probability"],
            "after": after["teams"][team]["playoff_probability"],
            "delta": float(difference.mean()),
            "delta_mc_standard_error": float(difference.std(ddof=1) / np.sqrt(simulations))
            if simulations > 1
            else 0.0,
        }
    return {
        "teams": result,
        "simulations": simulations,
        "seed": seed,
        "tiebreak": before["tiebreak"],
    }


def evaluate_playoff_impact(
    context,
    bundle,
    snapshot,
    *,
    after=None,
    simulations=5000,
    seed=42,
    playoff_spots=8,
    matchup_cache=None,
    deadline=None,
):
    """Compare a fixed-roster trade world to no trade, never future streaming guesses.

    An uneven package must specify legal drops or supply the already selected
    RosterScenario through ``after``; this function does not choose a new drop.
    """
    result = {
        "status": "needs_data",
        "reasons": [],
        "basis": "trade_only_fixed_rosters",
        "assumptions": [
            "Future categories and fixtures are conditionally independent.",
            "Current completed scores stay fixed; the ongoing week is not double counted.",
            "Future roster, IL activation and streaming moves are not invented.",
            "Monte Carlo error excludes projection, injury and role uncertainty.",
        ],
    }
    try:
        if type(simulations) is not int or not 100 <= simulations <= 100000:
            raise ValueError("Playoff simulations must be an integer between 100 and 100000")
        calendar, records, stats = _inputs(context, snapshot)
        _checkpoint(deadline)
        original = RosterScenario(
            copy.deepcopy(context.rosters), set(context.engine.yahoo_already_stashed_ids)
        )
        proposal = bundle["proposal"]
        if proposal.get("snapshot_id") != context.sync_id:
            raise ValueError("Playoff proposal belongs to a different roster snapshot")
        today = (
            pd.Timestamp(context.as_of).tz_convert("America/New_York").tz_localize(None).normalize()
        )
        effective = day(proposal["effective_date"])
        last_period = (calendar["weeks"] or [calendar["current_week"]])[-1]
        if effective < today or effective > day(last_period["end"]):
            raise ValueError("Playoff trade effective date is past or outside the remaining season")
        if after is None:
            outgoing = [context.yahoo_ids[str(pid)] for pid in proposal["give_yahoo_ids"]]
            incoming = [context.yahoo_ids[str(pid)] for pid in proposal["receive_yahoo_ids"]]
            scenarios, _ = trade_packages(context, bundle, outgoing, incoming)
            if len(scenarios) != 1:
                raise ValueError("Choose the required drop before computing playoff impact")
            after = scenarios[0]
        validate_scenario(after, context.engine.players)
        if any(
            context.engine.team_map.get(pid) is None
            for scenario in (original, after)
            for roster in scenario.rosters.values()
            for pid in roster
        ):
            raise ValueError("Every playoff roster player needs a known NBA team")
        if effective <= day(calendar["current_week"]["end"]) and after.stashed != original.stashed:
            raise ValueError("Dated in-week IL reassignment needs explicit activation history")
        if after.stashed != original.stashed and any(
            day(w["start"]) < effective <= day(w["end"]) for w in calendar["weeks"]
        ):
            raise ValueError("Dated in-week IL reassignment needs explicit activation history")
        eligibility = dict(context.engine.pos_dict)
        for yahoo_id, positions in bundle.get("eligible_positions", {}).items():
            if not positions or not set(positions) <= {"PG", "SG", "SF", "PF", "C"}:
                raise ValueError("Invalid Yahoo eligibility in playoff scenario")
            eligibility[context.yahoo_ids[str(yahoo_id)]] = ",".join(sorted(set(positions)))
        priority = snapshot.get("tiebreak_priority")
        if priority is None:
            result["assumptions"].append(
                "Actual cutoff tiebreak is not modeled; tied teams are sampled uniformly."
            )
        cache = matchup_cache or TradeProjectionCache()
        cache.bind(context, eligibility=eligibility)
        variants = {}
        for mode in ("normal", "without_spillover"):
            before_rows = _project_season(
                context,
                original,
                original,
                effective,
                calendar,
                stats,
                cache,
                mode,
                eligibility,
                deadline,
            )
            after_rows = _project_season(
                context,
                original,
                after,
                effective,
                calendar,
                stats,
                cache,
                mode,
                eligibility,
                deadline,
            )
            _checkpoint(deadline)
            variants[mode] = paired_qualification(
                records,
                before_rows,
                after_rows,
                simulations=simulations,
                seed=seed,
                playoff_spots=playoff_spots,
                tiebreak_priority=priority,
            )
        result.update(
            status="conditional_estimate",
            source=snapshot["source"],
            captured_at=snapshot["captured_at"],
            simulations=simulations,
            seed=seed,
            variants=variants,
            teams=variants["normal"]["teams"],
            tiebreak_exact=priority is not None,
            current_week_included=calendar["current_week"]["week"],
            full_future_weeks=len(calendar["weeks"]),
            cache=cache.stats(),
        )
    except (ValueError, KeyError, TypeError, AttributeError, TimeoutError) as exc:
        result["reasons"].append(str(exc))
    return result

"""Bounded dated streaming plans with identical rules on trade/no-trade paths.

The beam uses a fixed-gradient daily-lineup surrogate. Only full weekly model
scores select the final plans; posterior variances are never summed by day.
"""

import copy
import math
from datetime import datetime, timedelta
from types import MappingProxyType

import pandas as pd

from .matchup_engine import MAX_ROSTER_SIZE, get_optimal_daily_lineup
from .trade_context import day
from .trade_packages import drop_protection, validate_scenario, with_pickup


def apply_move(scenario, team, pid, when, drop=None, status="FA"):
    """Apply one chronological daily acquisition; no reacquisition or IL changes."""
    when = day(when)
    if team not in scenario.rosters:
        raise ValueError("Streaming team is unknown")
    active = set(scenario.rosters[team]) - scenario.stashed
    if drop is None and len(active) >= MAX_ROSTER_SIZE:
        raise ValueError("A full roster requires a simultaneous drop")
    if drop is not None and drop not in active:
        raise ValueError("Streaming can only release an owned active/bench player")
    return with_pickup(scenario, team, pid, when, drop=drop, status=status)


def _actions(scenario, team):
    return [
        {
            "date": action["date"],
            "add_id": int(action["add_id"]),
            "drop_id": int(action["drop_id"]) if action.get("drop_id") is not None else None,
        }
        for action in getattr(scenario, "transactions", [])
        if action.get("team", team) == team
    ]


def _history_key(scenario, team):
    return (
        tuple(sorted(scenario.rosters[team])),
        tuple(sorted(scenario.stashed)),
        tuple((p, str(v)) for p, v in sorted(scenario.starts.items())),
        tuple((p, str(v)) for p, v in sorted(scenario.ends.items())),
        tuple(
            (a["date"], a["add_id"], -1 if a["drop_id"] is None else a["drop_id"])
            for a in _actions(scenario, team)
        ),
    )


def _setting_int(settings, name, default, maximum):
    value = settings.get(name, default)
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"streaming.{name} must be an integer from 1 to {maximum}")
    return value


def _source_valid(context):
    audit = context.availability_audit
    try:
        stamp = datetime.fromisoformat(audit["updated_at"].replace("Z", "+00:00"))
        return (
            audit.get("source") == "yahoo_available_players"
            and audit.get("sync_id") == context.sync_id
            and not audit.get("reason")
            and -timedelta(minutes=5) <= context.as_of - stamp <= timedelta(hours=24)
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


class _DailySurrogateCandidates:
    """Immutable dated NBA entries shared by the two fixed-gradient plans.

    Fantasy acquisitions change eligibility intervals, not NBA roles or the
    information date. Weekly model scoring remains outside this cache. The
    cache lives for one comparison and contains only its relevant player/date
    union; matchup-specific weights and assignment results are not shared.
    """

    def __init__(self, engine, player_ids, first, last, as_of):
        self.engine, self.as_of = engine, as_of
        self.player_ids = tuple(sorted(set(player_ids)))
        dates_by_team = {}
        self.schedule = {}
        for pid in self.player_ids:
            tid = engine.team_map.get(pid)
            if tid not in dates_by_team:
                dates_by_team[tid] = frozenset(engine._get_player_schedule(tid, first, last))
            self.schedule[pid] = dates_by_team[tid]
        self.by_day = {}
        self.stats = {
            "relevant_players": len(self.player_ids),
            "schedule_queries": len(dates_by_team),
            "prepared_days": 0,
            "prepared_player_dates": 0,
            "candidate_requests": 0,
            "reused_player_dates": 0,
        }

    def entries(self, when, active):
        self.stats["candidate_requests"] += 1
        if when not in self.by_day:
            playing = tuple(pid for pid in self.player_ids if when in self.schedule[pid])
            projections = (
                self.engine._daily_projections(when, self.as_of, True, playing) if playing else {}
            )
            prepared = {}
            for pid in playing:
                tid = self.engine.team_map.get(pid)
                b2b = when - pd.Timedelta(days=1) in self.engine._all_schedule_dates.get(tid, set())
                probability = self.engine.players[pid].get_effective_game_availability(
                    is_b2b=b2b, game_date=when, as_of_date=self.as_of
                )
                mu, _ = projections[pid]
                prepared[pid] = MappingProxyType(
                    {
                        "ID": pid,
                        "POS": self.engine.pos_dict.get(pid, "UTIL"),
                        "PROJ": MappingProxyType(
                            {cat: value * probability for cat, value in mu.items()}
                        ),
                    }
                )
            self.by_day[when] = prepared
            self.stats["prepared_days"] += 1
            self.stats["prepared_player_dates"] += len(prepared)
        else:
            self.stats["reused_player_dates"] += sum(pid in self.by_day[when] for pid in active)
        return tuple(self.by_day[when][pid] for pid in active if pid in self.by_day[when])


def streaming_comparison(context, bundle, original, trade, score, compare, engine, seeds=None):
    """Optimize dated alternatives independently; return serializable plans only.

    Missing weekly usage blocks acquisitions for that week. A dropped player
    cannot be re-acquired, so each player retains one ownership interval.
    """
    settings = bundle.get("streaming", {})
    if not settings.get("enabled", False):
        return {"status": "disabled"}
    conditions = [
        "Streaming uses bounded search; global optimality is not guaranteed.",
        "Future FA availability and waiver claims must be reverified before each action.",
        "At most one atomic acquisition/drop per day; no reacquisition within the horizon.",
        "IL placement stays fixed; future IL activation is not planned.",
    ]
    if not _source_valid(context):
        reason = "Fresh, matching Yahoo available-player evidence is required for streaming."
        return {"status": "unavailable", "conditions": [reason], "reasons": [reason]}
    if not context.availability_audit.get("scan_complete"):
        conditions.append("Availability scan is partial; only the verified subset is considered.")
    candidate_limit = _setting_int(settings, "candidate_limit", 8, 25)
    beam_width = _setting_int(settings, "beam_width", 6, 50)
    finalist_limit = _setting_int(settings, "finalists", 6, 50)
    minimum = settings.get("min_gain_per_week", 0.05)
    if (
        isinstance(minimum, bool)
        or not isinstance(minimum, (int, float))
        or not math.isfinite(minimum)
        or minimum < 0
    ):
        raise ValueError("streaming.min_gain_per_week must be finite and nonnegative")
    weeks = bundle["weeks"]
    first, last = day(weeks[0]["start"]), day(weeks[-1]["end"])
    team = str(bundle["proposal"]["our_team"])
    effective = day(bundle["proposal"]["effective_date"])
    as_of = pd.Timestamp(context.as_of).tz_convert("America/New_York").tz_localize(None).normalize()
    limits = bundle.get("rules", {})
    limit = limits.get("max_weekly_adds", context.weekly_add_limit)
    trade_cost = limits.get("trade_add_cost", 0)
    if type(limit) is not int or type(trade_cost) is not int or min(limit, trade_cost) < 0:
        raise ValueError("Weekly add limit and trade cost must be nonnegative integers")
    usage = settings.get("adds_used_by_week", {})
    if not isinstance(usage, dict):
        raise ValueError("streaming.adds_used_by_week must be a mapping")
    protection = drop_protection(context, bundle)
    seeds = seeds or {}
    all_owned = {pid for ids in context.rosters.values() for pid in ids}
    # Also exclude owned IDs in each counterfactual, including its compulsory drops.
    all_owned |= {pid for base in (original, trade) for ids in base.rosters.values() for pid in ids}

    proxy_engine = copy.copy(engine)
    proxy_engine.players = copy.deepcopy(engine.players)
    proxy_engine._projection_cache = None
    proxy_engine.recompute_team_depth_and_injury_minutes(game_date=as_of, as_of_date=as_of)
    valid_pool = {}
    for pid, item in sorted(context.available_players.items()):
        if pid in all_owned or pid not in engine.players or not engine.team_map.get(pid):
            continue
        if any(pid in ids for base in (original, trade) for ids in base.drops.values()):
            continue
        status, waiver = item.get("status"), item.get("waiver")
        if status not in ("FA", "W"):
            continue
        if status == "W" and (not waiver or not waiver.get("date")):
            continue
        if waiver is not None and not waiver.get("date"):
            continue
        clear = max(first, day(waiver["date"])) if waiver else first
        if clear > last:
            continue
        mu, _ = proxy_engine._build_player_game_projection(pid, current_date=as_of)
        dates = proxy_engine._get_player_schedule(proxy_engine.team_map[pid], clear, last)
        value = len(dates) * proxy_engine._player_value(
            {"PROJ": mu}, proxy_engine.default_norm_weights
        )
        valid_pool[pid] = {"clear": clear, "status": status, "rank": value}

    def raw_seed_ids(seed):
        actions = _actions(seed, team)
        if actions:
            return {a["add_id"] for a in actions}
        addition = seed.adds.get(team)
        return {addition["player_id"]} if addition else set()

    shortlist = sorted(valid_pool, key=lambda p: (-valid_pool[p]["rank"], p))[:candidate_limit]
    seed_ids = set()
    for path in ("before", "after"):
        for seed in seeds.get(path, []):
            seed_ids |= raw_seed_ids(seed) & valid_pool.keys()
    candidate_ids = sorted(set(shortlist) | seed_ids)
    pool = {pid: valid_pool[pid] for pid in candidate_ids}
    if not pool:
        conditions.append("No verified, eligible FA candidates are available in this horizon.")
    surrogate_candidates = _DailySurrogateCandidates(
        proxy_engine,
        set(original.projection_roster(team)) | set(trade.projection_roster(team)) | set(pool),
        first,
        last,
        as_of,
    )

    def week_for(when):
        return next((w for w in weeks if day(w["start"]) <= when <= day(w["end"])), None)

    def budgets(path, scenario=None):
        counts = {}
        if scenario is not None:
            for action in _actions(scenario, team):
                week = week_for(day(action["date"]))
                if week is None:
                    raise ValueError("Streaming action lies outside the analyzed fantasy weeks")
                counts[week["start"]] = counts.get(week["start"], 0) + 1
        result = {}
        for week in weeks:
            supplied = usage.get(week["start"], {})
            if not isinstance(supplied, dict):
                raise ValueError("Weekly streaming usage must map team IDs to integer counts")
            used = supplied.get(team)
            if used is not None and (type(used) is not int or used < 0):
                raise ValueError("Weekly streaming usage must be a nonnegative integer")
            cost = (
                trade_cost
                if path == "after" and day(week["start"]) <= effective <= day(week["end"])
                else 0
            )
            planned = counts.get(week["start"], 0)
            if cost > limit or (used is not None and used + cost + planned > limit):
                raise ValueError(
                    "Streaming usage or trade cost exceeds the weekly acquisition limit"
                )
            if used is None and planned:
                raise ValueError(
                    "Streaming acquisitions require known usage for their fantasy week"
                )
            result[week["start"]] = {
                "limit": limit,
                "used_before": used,
                "trade_cost": cost,
                "planned_adds": planned,
                "remaining": None if used is None else limit - used - cost - planned,
            }
        return result

    base_budgets = {path: budgets(path) for path in ("before", "after")}
    for path, values in base_budgets.items():
        for week, row in values.items():
            if row["used_before"] is None:
                conditions.append(
                    f"{path} {week}: usage is unknown; additions are blocked for this week."
                )

    def move(state, path, pid, when, drop=None):
        if pid not in pool or when < pool[pid]["clear"] or not first <= when <= last:
            raise ValueError("Streaming acquisition lacks valid dated FA evidence")
        if drop in protection:
            raise ValueError("Streaming cannot release a protected player")
        result = apply_move(state, team, pid, when, drop, status=pool[pid]["status"])
        validate_scenario(result, engine.players)
        budgets(path, result)
        return result

    def replay_seed(base, path, seed):
        if seed.stashed != base.stashed or any(
            seed.rosters[t] != base.rosters[t] for t in base.rosters if t != team
        ):
            raise ValueError("Streaming seed changes another team or its IL assignments")
        actions = _actions(seed, team)
        if not actions:
            addition = seed.adds.get(team)
            if addition:
                removed = set(base.rosters[team]) - set(seed.rosters[team])
                if len(removed) > 1:
                    raise ValueError("Invalid one-pickup streaming seed")
                actions = [
                    {
                        "date": addition["date"],
                        "add_id": addition["player_id"],
                        "drop_id": next(iter(removed), None),
                    }
                ]
        result = copy.deepcopy(base)
        for action in actions:
            result = move(result, path, action["add_id"], day(action["date"]), action["drop_id"])
        if set(result.rosters[team]) != set(seed.rosters[team]):
            raise ValueError("Streaming seed does not reproduce its stated final roster")
        return result

    def fixed_weights(base):
        result = {}
        proxy_engine.yahoo_already_stashed_ids = set(base.stashed)
        for week in weeks:
            fixture = next(pair for pair in week["fixtures"] if team in map(str, pair))
            opponent = str(fixture[1]) if str(fixture[0]) == team else str(fixture[0])
            own_dist = proxy_engine.get_expected_weekly_distribution(
                base.projection_roster(team),
                week["start"],
                week["end"],
                as_of_date=as_of,
                player_start_dates=base.starts,
                player_end_dates=base.ends,
            )
            opponent_dist = proxy_engine.get_expected_weekly_distribution(
                base.projection_roster(opponent),
                week["start"],
                week["end"],
                as_of_date=as_of,
                player_start_dates=base.starts,
                player_end_dates=base.ends,
            )
            _, _, weights = proxy_engine.evaluate_h2h_matchup(own_dist, opponent_dist)
            means = own_dist["mean"]
            fg = means["FGM"] / means["FGA"] if means["FGA"] else 0.47
            ft = means["FTM"] / means["FTA"] if means["FTA"] else 0.78
            for when in pd.date_range(week["start"], week["end"]):
                result[when] = weights, fg, ft
        return result

    def plan(base, path):
        validate_scenario(base, engine.players)
        weights_by_day = fixed_weights(base)
        daily_cache = {}
        proxy_cache = {}
        proxy_counters = {"evaluated_states": 0, "reused_states": 0}

        def proxy(state, history):
            if history in proxy_cache:
                proxy_counters["reused_states"] += 1
                return proxy_cache[history]
            proxy_counters["evaluated_states"] += 1
            total = 0.0
            ids = sorted(set(state.projection_roster(team)) - state.stashed)
            starts = {pid: day(value).value for pid, value in state.starts.items()}
            ends = {pid: day(value).value for pid, value in state.ends.items()}
            for when, (weights, fg, ft) in weights_by_day.items():
                active = tuple(
                    pid
                    for pid in ids
                    if (pid not in starts or when.value >= starts[pid])
                    and (pid not in ends or when.value <= ends[pid])
                )
                key = when, active
                if key not in daily_cache:
                    candidates = surrogate_candidates.entries(when, active)
                    lineup = get_optimal_daily_lineup(candidates, weights, fg, ft)
                    daily_cache[key] = sum(
                        proxy_engine._player_value(p, weights, fg, ft) for p in lineup
                    )
                total += daily_cache[key]
            proxy_cache[history] = total
            return total

        def rank(state):
            actions = _actions(state, team)
            history = _history_key(state, team)
            return (-proxy(state, history), len(actions), history)

        frontier = [copy.deepcopy(base)]
        generated = 0
        for when in pd.date_range(first, last):
            choices = {_history_key(state, team): state for state in frontier}
            choices[_history_key(base, team)] = base
            for state in list(choices.values()):
                weekly = budgets(path, state)[week_for(when)["start"]]
                if weekly["remaining"] is None or weekly["remaining"] == 0:
                    continue
                active = set(state.rosters[team]) - state.stashed
                drops = [None] if len(active) < MAX_ROSTER_SIZE else sorted(active - protection)
                for pid in candidate_ids:
                    if when < pool[pid]["clear"] or pid in state.starts or pid in state.ends:
                        continue
                    if any(pid in ids for ids in state.rosters.values()):
                        continue
                    for drop in drops:
                        candidate = move(state, path, pid, when, drop)
                        choices[_history_key(candidate, team)] = candidate
                        generated += 1
            ranked = sorted(choices.values(), key=rank)
            # Waiting must survive until a later waiver date. Distinct dates for
            # holding one future-game player must not consume the whole beam.
            # These signatures allocate beam slots; they do not merge histories.
            selected = {}
            signatures = set()
            for candidate in ranked:
                signature = (
                    tuple(sorted(candidate.rosters[team])),
                    tuple((w, row["planned_adds"]) for w, row in budgets(path, candidate).items()),
                )
                if signature in signatures:
                    continue
                signatures.add(signature)
                selected[_history_key(candidate, team)] = candidate
                if len(selected) >= beam_width:
                    break
            if len(selected) < beam_width:
                for candidate in ranked:
                    selected[_history_key(candidate, team)] = candidate
                    if len(selected) >= beam_width:
                        break
            frontier = list(selected.values())
        final_candidates = sorted(frontier, key=rank)[:finalist_limit]
        final_candidates.append(copy.deepcopy(base))
        rejected_seeds = 0
        for seed in seeds.get(path, []):
            try:
                final_candidates.append(replay_seed(base, path, seed))
            except (ValueError, KeyError, TypeError):
                rejected_seeds += 1
        unique = {_history_key(state, team): state for state in final_candidates}
        baseline_values = score(base)
        best, best_values, best_gain = base, baseline_values, 0.0
        for state in sorted(
            unique.values(), key=lambda s: (len(_actions(s, team)), _history_key(s, team))
        ):
            values = score(state)
            gain = min(
                values[team][v] - baseline_values[team][v] for v in ("normal", "sensitivity")
            )
            if gain > best_gain + 1e-10:
                best, best_values, best_gain = state, values, gain
        if best_gain <= 1e-10 or best_gain < minimum * len(weeks):
            best, best_values = base, baseline_values
        return (
            best,
            {
                "actions": _actions(best, team),
                "weekly_budget": budgets(path, best),
                "final_roster": sorted(int(p) for p in best.rosters[team]),
                "values": best_values,
            },
            {
                "generated": generated,
                "evaluated": len(unique),
                "rejected_seeds": rejected_seeds,
                "surrogate_states": proxy_counters,
            },
        )

    with proxy_engine.projection_session():
        before_plan, before_result, before_search = plan(original, "before")
        after_plan, after_result, after_search = plan(trade, "after")
    before_values, after_values = before_result["values"][team], after_result["values"][team]
    return {
        "status": "planned",
        "before": before_result,
        "after": after_result,
        "teams": compare(before_plan, after_plan),
        "delta": after_values["normal"] - before_values["normal"],
        "delta_without_spillover": after_values["sensitivity"] - before_values["sensitivity"],
        "near_term_delta": after_values["near"] - before_values["near"],
        "extra_over_trade_only": after_values["normal"] - score(trade)[team]["normal"],
        "conditions": conditions,
        "search": {
            "candidate_limit": candidate_limit,
            "candidate_count": len(candidate_ids),
            "eligible_pool": len(valid_pool),
            "beam_width": beam_width,
            "finalists": finalist_limit,
            "before": before_search,
            "after": after_search,
            "surrogate_cache": dict(surrogate_candidates.stats),
        },
        "candidate_ids": [int(p) for p in candidate_ids],
        "min_gain_per_week": minimum,
    }

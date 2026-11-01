"""One-pickup alternatives with the same verified FA pool and budget on both sides."""

import math
from datetime import datetime, timedelta

import pandas as pd

from .matchup_engine import MAX_ROSTER_SIZE
from .trade_context import day
from .trade_packages import drop_protection, validate_scenario, with_pickup


def _strength(values, base, team):
    return min(values[team][v] - base[team][v] for v in ("normal", "sensitivity"))


def completion_options(
    context, bundle, original, trade, score, engine, *, teams=None, require_positive_trade_gain=True
):
    """Each team's result is an alternative, never a simultaneous multi-add plan."""
    settings = bundle.get("completion", {})
    result = {
        "status": "disabled",
        "options": [],
        "reasons": [],
        "search": {},
        "data_sufficient": False,
    }
    if not settings.get("enabled", True):
        return result
    changed = [
        t
        for t in (str(bundle["proposal"]["our_team"]), str(bundle["proposal"]["other_team"]))
        if len(set(trade.rosters[t]) - trade.stashed) < MAX_ROSTER_SIZE
        and len(set(trade.rosters[t]) - trade.stashed)
        < len(set(original.rosters[t]) - original.stashed)
        and (teams is None or t in teams)
    ]
    if not changed:
        result["status"] = "no_new_open_slot"
        result["data_sufficient"] = True
        return result
    result["status"] = "unavailable"
    audit = context.availability_audit
    try:
        captured = datetime.fromisoformat(audit["updated_at"].replace("Z", "+00:00"))
        valid = (
            audit.get("source") == "yahoo_available_players"
            and audit.get("sync_id") == context.sync_id
            and not audit.get("reason")
            and -timedelta(minutes=5) <= context.as_of - captured <= timedelta(hours=24)
        )
    except (KeyError, ValueError, TypeError, AttributeError):
        valid = False
    if not valid:
        result["reasons"].append("Güncel ve aynı kadro sürümüne ait Yahoo FA kanıtı yok.")
        return result
    if not audit.get("scan_complete"):
        result["reasons"].append("FA taraması eksik; yalnızca doğrulanmış alt küme incelendi.")
    minimum = settings.get("min_gain_per_week", 0.05)
    limit = settings.get("candidate_limit", 8)
    add_limit = bundle.get("rules", {}).get("max_weekly_adds", context.weekly_add_limit)
    cost = bundle.get("rules", {}).get("trade_add_cost", 0)
    if (
        isinstance(minimum, bool)
        or not isinstance(minimum, (int, float))
        or not math.isfinite(minimum)
        or minimum < 0
    ):
        raise ValueError("min_gain_per_week must be finite and nonnegative")
    if type(limit) is not int or not 1 <= limit <= 25:
        raise ValueError("candidate_limit must be between 1 and 25")
    if type(add_limit) is not int or type(cost) is not int or min(add_limit, cost) < 0:
        raise ValueError("Add limit and trade_add_cost must be nonnegative integers")
    threshold = minimum * len(bundle["weeks"])
    first, end = day(bundle["weeks"][0]["start"]), day(bundle["weeks"][-1]["end"])
    start = max(first, day(bundle["proposal"]["effective_date"]))
    occupied = {p for ids in original.rosters.values() for p in ids}
    occupied |= {p for ids in context.rosters.values() for p in ids}
    # Reserve all ownership history on BOTH paths, not only the final rosters.
    # A streamed-out FA has an unknown future waiver state and is not re-used.
    occupied |= {
        p for scenario in (original, trade) for p in scenario.starts.keys() | scenario.ends.keys()
    }
    as_of = pd.Timestamp(context.as_of).tz_convert("America/New_York").tz_localize(None).normalize()
    raw_pool = []
    for pid, item in context.available_players.items():
        if pid in occupied or pid not in engine.players or not engine.team_map.get(pid):
            continue
        status, waiver = item.get("status"), item.get("waiver")
        if status not in ("FA", "W"):
            continue
        if status == "W" and (not waiver or not waiver.get("date")):
            continue
        if waiver is not None and not waiver.get("date"):
            continue
        when = max(start, day(waiver["date"])) if waiver else start
        if when > end:
            continue
        mu, _ = engine._build_player_game_projection(pid, current_date=as_of)
        games = len(engine._get_player_schedule(engine.team_map[pid], when, end))
        rank = games * engine._player_value({"PROJ": mu}, engine.default_norm_weights)
        raw_pool.append((rank, pid, when, status))
    protection = drop_protection(context, bundle)
    original_score, trade_score = score(original), score(trade)
    budgets = settings.get("adds_used_by_week", {})
    result["data_sufficient"] = all(
        budgets.get(week["start"], {}).get(team) is not None
        for week in bundle["weeks"]
        for team in changed
    )
    result.update(
        status="no_material_option",
        threshold_points=threshold,
        min_gain_per_week=minimum,
        candidate_limit=limit,
        search={"eligible_pool": len(raw_pool), "teams": {}},
    )
    for team in changed:
        eligible = []
        eligible_after = set()
        for candidate in raw_pool:
            _, pid, when, status = candidate
            week = next(w for w in bundle["weeks"] if day(w["start"]) <= when <= day(w["end"]))
            used = budgets.get(week["start"], {}).get(team)
            if used is None:
                continue
            if type(used) is not int or used < 0:
                raise ValueError("adds_used_by_week must contain nonnegative integer counts")
            if used + 1 <= add_limit:
                eligible.append(candidate)
            effective = day(bundle["proposal"]["effective_date"])
            dated_cost = cost if day(week["start"]) <= effective <= day(week["end"]) else 0
            if used + dated_cost + 1 <= add_limit:
                eligible_after.add(pid)
        eligible.sort(key=lambda c: (-c[0], c[1]))
        shortlisted = eligible[:limit]
        result["search"]["teams"][team] = {"eligible": len(eligible), "evaluated": len(shortlisted)}
        if not shortlisted:
            result["reasons"].append(
                f"{context.team_names.get(team, f'Takım {team}')}: "
                "doğrulanmış bütçe ve tarihle kullanılabilir aday yok."
            )
            continue
        # The baseline can keep its roster or choose any shortlisted FA and a legal drop.
        best_hold, best_hold_score = original, original_score
        for _, pid, when, status in shortlisted:
            active = set(original.rosters[team]) - original.stashed
            drops = [None] if len(active) < MAX_ROSTER_SIZE else sorted(active - protection)
            for drop in drops:
                hold = with_pickup(original, team, pid, when, drop, status)
                validate_scenario(hold, engine.players)
                values = score(hold)
                if _strength(values, original_score, team) > _strength(
                    best_hold_score, original_score, team
                ):
                    best_hold, best_hold_score = hold, values
        options = []
        for _, pid, when, status in shortlisted:
            if pid not in eligible_after:
                continue
            after = with_pickup(trade, team, pid, when, status=status)
            validate_scenario(after, engine.players)
            values = score(after)
            fair = _strength(values, best_hold_score, team)
            extra = _strength(values, trade_score, team)
            if extra <= 1e-10 or extra < threshold:
                continue
            if require_positive_trade_gain and (fair <= 1e-10 or fair < threshold):
                continue
            options.append(
                {
                    "team": team,
                    "player_id": pid,
                    "name": engine.players[pid].name,
                    "date": when.date().isoformat(),
                    "status": status,
                    "delta": values[team]["normal"] - best_hold_score[team]["normal"],
                    "delta_without_spillover": values[team]["sensitivity"]
                    - best_hold_score[team]["sensitivity"],
                    "near_term_delta": values[team]["near"] - best_hold_score[team]["near"],
                    "extra_over_trade_only": values[team]["normal"] - trade_score[team]["normal"],
                    "robust_delta": fair,
                    "baseline_actions": best_hold.adds.get(team),
                    "baseline_drops": best_hold.drops.get(team, []),
                    "baseline_category_points": best_hold_score[team]["normal"],
                    "after_category_points": values[team]["normal"],
                    "scenario": after,
                    "baseline": best_hold,
                }
            )
        options.sort(key=lambda o: (-o["robust_delta"], o["player_id"]))
        result["options"].extend(options[:3])
    if result["options"]:
        result["status"] = "conditional_options"
    result["reasons"].append(
        "FA/waiver erişimi işlem gününde yeniden doğrulanmalı; alternatifler birlikte uygulanmaz."
    )
    return result

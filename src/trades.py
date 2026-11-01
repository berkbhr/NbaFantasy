"""Offline manual trade packages, roster corrections and verified FA alternatives."""

import argparse
import copy
import hashlib
import json
import math
import sys
import time
from contextlib import ExitStack
from pathlib import Path

import pandas as pd

from .fantasy_calendar import resolve_trade_calendar
from .matchup_engine import COUNT_STATS
from .probability import category_points
from .streaming import streaming_comparison
from .trade_completions import completion_options
from .trade_context import day, load_context, validate_calendar, validate_rules
from .trade_packages import RosterScenario, trade_packages, validate_scenario, with_pickup


def _pair(
    engine, home, away, start, end, as_of, starts=None, ends=None, *, cache=None, engine_key=None
):
    """Use the same two-pass policy and frozen information date for both teams."""
    pair_key = None
    if cache is not None:
        engine_key = engine_key or cache.engine_key(engine)
        pair_key = cache.pair_key(engine, engine_key, home, away, start, end, as_of, starts, ends)
        cached = cache.get_pair(pair_key)
        if cached is not None:
            return cached

    def project(ids, weights=None):
        key = None
        if cache is not None:
            key = cache.distribution_key(
                engine, engine_key, ids, start, end, as_of, starts, ends, weights
            )
            cached = cache.get_distribution(key)
            if cached is not None:
                return cached
        result = engine.get_expected_weekly_distribution(
            ids,
            start,
            end,
            category_weights=weights,
            as_of_date=as_of,
            player_start_dates=starts,
            player_end_dates=ends,
        )
        if cache is not None:
            cache.put_distribution(key, result)
        return result

    a, b = project(home), project(away)
    for _ in range(2):
        _, pa, wa = engine.evaluate_h2h_matchup(a, b)
        _, pb, wb = engine.evaluate_h2h_matchup(b, a)
        ta, tb = project(home, wa), project(away, wb)
        next_a = (
            ta
            if category_points(engine.evaluate_h2h_matchup(ta, b)[1]) > category_points(pa)
            else a
        )
        next_b = (
            tb
            if category_points(engine.evaluate_h2h_matchup(tb, a)[1]) > category_points(pb)
            else b
        )
        a, b = next_a, next_b
    if cache is not None:
        cache.put_pair(pair_key, (a, b))
    return a, b


def _value(mean, cat):
    if cat.endswith("_PCT"):
        prefix = cat[:2]
        return mean[prefix + "M"] / mean[prefix + "A"] if mean[prefix + "A"] else 0
    return mean[cat]


def _summary(engine, mine, opponent):
    _, probabilities, _ = engine.evaluate_h2h_matchup(mine, opponent)
    outcome = engine.compute_matchup_outcome(probabilities)
    return {
        "points": category_points(probabilities),
        "weekly_outcome": {"win": outcome.win, "loss": outcome.loss, "tie": outcome.draw},
        "categories": {
            c: {
                "production": _value(mine["mean"], c),
                "win": p,
                "tie": probabilities.ties[c],
                "points": p + 0.5 * probabilities.ties[c],
            }
            for c, p in probabilities.items()
        },
        "lineups": mine["meta"]["lineups"],
    }


def _aggregate(rows):
    categories = {}
    for cat in rows[0]["before"]["categories"]:
        categories[cat] = {
            "before_win": sum(r["before"]["categories"][cat]["win"] for r in rows) / len(rows),
            "after_win": sum(r["after"]["categories"][cat]["win"] for r in rows) / len(rows),
            "delta_points": sum(
                r["after"]["categories"][cat]["points"] - r["before"]["categories"][cat]["points"]
                for r in rows
            ),
        }
    before = sum(r["before"]["points"] for r in rows)
    after = sum(r["after"]["points"] for r in rows)
    return {
        "weeks": len(rows),
        "before": before,
        "after": after,
        "delta": after - before,
        "categories": categories,
    }


def _normalized_package(engine, outgoing, incoming, as_of):
    """Equal four games per player, current availability; no lineup/probability claim."""
    totals = []
    for ids in (outgoing, incoming):
        total = dict.fromkeys(COUNT_STATS + ["FGM", "FGA", "FTM", "FTA"], 0.0)
        for pid in ids:
            mu, _ = engine._build_player_game_projection(pid, current_date=as_of)
            p = engine.players[pid].get_effective_game_availability(
                game_date=as_of, as_of_date=as_of
            )
            for cat in total:
                total[cat] += 4 * p * mu[cat]
        totals.append(total)
    return {
        "definition": "Four games per player at current availability; package production only. "
        "Excludes daily lineup constraints and is not a team win probability.",
        "outgoing": totals[0],
        "incoming": totals[1],
        "delta": {c: totals[1][c] - totals[0][c] for c in totals[0]},
    }


def evaluate_trade(
    context,
    bundle,
    *,
    projection_cache=None,
    matchup_cache=None,
    complete_partner=False,
    deadline=None,
):
    """Never mutate the supplied context, player posteriors or live ownership."""
    if bundle.get("proposal", {}).get("transfers") is not None:
        from .trade_multiteam import evaluate_multiteam_trade

        return evaluate_multiteam_trade(context, bundle, deadline=deadline)
    bundle = resolve_trade_calendar(context, bundle)
    rules = validate_rules(bundle)
    weeks = validate_calendar(bundle, context.rosters, context.as_of)
    proposal = bundle["proposal"]
    if proposal.get("snapshot_id") != context.sync_id:
        raise ValueError("Proposal must be tied to the current roster sync_id")
    mine, partner = str(proposal["our_team"]), str(proposal["other_team"])
    if mine == partner or mine not in context.rosters or partner not in context.rosters:
        raise ValueError("Proposal needs two distinct known teams")
    outgoing = [context.yahoo_ids[str(i)] for i in proposal["give_yahoo_ids"]]
    incoming = [context.yahoo_ids[str(i)] for i in proposal["receive_yahoo_ids"]]
    if len(outgoing) not in (1, 2, 3, 4) or len(incoming) not in (1, 2, 3, 4):
        raise ValueError("Each side must send between one and four players")
    if len(set(outgoing + incoming)) != len(outgoing + incoming):
        raise ValueError("Duplicate or overlapping proposal players")
    if not set(outgoing) <= set(context.rosters[mine]) or not set(incoming) <= set(
        context.rosters[partner]
    ):
        raise ValueError("Proposal players are not owned by their stated teams")
    locked = {str(i) for i in bundle.get("do_not_trade_yahoo_ids", [])}
    if locked.intersection(map(str, proposal["give_yahoo_ids"])):
        raise ValueError("Proposal includes a player explicitly protected from trades")
    engine = copy.deepcopy(context.engine)
    effective = day(proposal["effective_date"])
    if effective > day(weeks[0]["start"]):
        raise ValueError("Effective date must precede the first analyzed full fantasy week")
    today = pd.Timestamp(context.as_of).tz_convert("America/New_York").tz_localize(None).normalize()
    if effective < today:
        raise ValueError("Effective date cannot precede the analysis date")
    if rules.get("trade_deadline") and effective > day(rules["trade_deadline"]):
        raise ValueError("Effective date exceeds the supplied trade deadline")
    if rules.get("review_days") is not None:
        review_days = rules["review_days"]
        if not isinstance(review_days, int) or review_days < 0:
            raise ValueError("review_days must be a nonnegative integer")
        if effective < today + pd.Timedelta(days=review_days):
            raise ValueError("Effective date precedes the supplied review period")
    if engine.schedule.empty:
        raise ValueError("Dated NBA schedule required")
    end = day(weeks[-1]["end"])
    if end > pd.to_datetime(engine.schedule.GAME_DATE).max():
        raise ValueError("Analyzed weeks exceed NBA schedule coverage")
    affected = set().union(*map(set, context.rosters.values()))
    if any(engine.team_map.get(pid) is None for pid in affected):
        raise ValueError("Every roster player needs a known NBA team")
    positions = bundle.get("eligible_positions", {})
    exact = set(context.verified_position_ids)
    allowed = {"PG", "SG", "SF", "PF", "C"}
    for yahoo_id, slots in positions.items():
        if str(yahoo_id) not in context.yahoo_ids or not slots or not set(slots) <= allowed:
            raise ValueError("Invalid exact Yahoo eligibility override")
        pid = context.yahoo_ids[str(yahoo_id)]
        engine.pos_dict[pid] = ",".join(sorted(set(slots)))
        exact.add(pid)
    conditions = list(context.warnings)
    if not affected <= exact:
        conditions.append("Exact Yahoo eligibility is incomplete; NBA positions are approximate.")
    if not rules.get("verified"):
        conditions.append("Trade rules have not been confirmed.")
    if not bundle.get("calendar_verified"):
        conditions.append("Fantasy fixtures have not been confirmed.")
    if (context.as_of - context.captured_at).total_seconds() > 86400:
        conditions.append("Refresh stale rosters before acting.")
    if any(engine.players[p].injury_status != "HEALTHY" for p in outgoing + incoming):
        conditions.append(
            "A traded player has an injury designation; return-date assumptions matter."
        )
    original = RosterScenario(copy.deepcopy(context.rosters), set(engine.yahoo_already_stashed_ids))
    validate_scenario(original, engine.players)
    packages, drop_decision_team = trade_packages(context, bundle, outgoing, incoming)
    as_of = today
    sensitivity_engine = copy.deepcopy(engine)
    sensitivity_engine.use_positional_depth_and_injury_boost = False
    engines = (engine, sensitivity_engine)
    if matchup_cache is not None and matchup_cache.bind(context, eligibility=engine.pos_dict):
        # The older player-moment dict has no context/posterior/position keys.
        # Keep it paired with this exact-cache scope rather than leaking an old
        # model or eligibility-dependent rotation into a new evaluated bundle.
        if projection_cache is not None:
            projection_cache.clear()
    engine_keys = (
        {id(e): matchup_cache.engine_key(e) for e in engines} if matchup_cache is not None else {}
    )
    # Search may reuse immutable NBA player moments across packages from ONE
    # frozen context/settings bundle. Fantasy ownership does not change NBA roles.
    if projection_cache is not None:
        for selected_engine in engines:
            selected_engine._projection_cache = projection_cache
    score_cache = {}

    def scenario_key(scenario):
        return (
            tuple((t, tuple(sorted(ids))) for t, ids in sorted(scenario.rosters.items())),
            tuple(sorted(scenario.stashed)),
            tuple((p, str(v)) for p, v in sorted(scenario.starts.items())),
            tuple((p, str(v)) for p, v in sorted(scenario.ends.items())),
            tuple(
                (a.get("team"), a["date"], a["add_id"], a.get("drop_id"))
                for a in scenario.transactions
            ),
        )

    def run(selected_engine, scenario):
        selected_engine.yahoo_already_stashed_ids = set(scenario.stashed)
        rows = {mine: [], partner: []}
        for week in weeks:
            for home, away in week["fixtures"]:
                if deadline is not None and time.perf_counter() >= deadline:
                    raise TimeoutError("Trade analysis time budget exhausted")
                home, away = str(home), str(away)
                if not {home, away}.intersection(rows):
                    continue
                pair = _pair(
                    selected_engine,
                    scenario.projection_roster(home),
                    scenario.projection_roster(away),
                    week["start"],
                    week["end"],
                    as_of,
                    scenario.starts,
                    scenario.ends,
                    cache=matchup_cache,
                    engine_key=engine_keys.get(id(selected_engine)),
                )
                for team, index in ((home, 0), (away, 1)):
                    if team in rows:
                        rows[team].append(
                            {
                                "start": week["start"],
                                "end": week["end"],
                                "opponent": away if index == 0 else home,
                                "result": _summary(selected_engine, pair[index], pair[1 - index]),
                            }
                        )
        return rows

    def all_scores(scenario):
        key = scenario_key(scenario)
        if key not in score_cache:
            score_cache[key] = [run(e, scenario) for e in engines]
        return score_cache[key]

    def scores(scenario):
        values = all_scores(scenario)
        return {
            t: {
                "normal": sum(w["result"]["points"] for w in values[0][t]),
                "sensitivity": sum(w["result"]["points"] for w in values[1][t]),
                "near": sum(w["result"]["points"] for w in values[0][t][:4]),
            }
            for t in (mine, partner)
        }

    def compare(before, after):
        a, b = all_scores(before), all_scores(after)
        result = {}
        for team in (mine, partner):
            rows = [
                {
                    "start": x["start"],
                    "end": x["end"],
                    "opponent": x["opponent"],
                    "before": x["result"],
                    "after": y["result"],
                }
                for x, y in zip(a[0][team], b[0][team])
            ]
            result[team] = {
                "all_supplied_weeks": _aggregate(rows),
                "near_term": _aggregate(rows[:4]),
                "weekly": rows,
                "without_spillover_delta": scores(after)[team]["sensitivity"]
                - scores(before)[team]["sensitivity"],
            }
        return result

    with ExitStack() as sessions:
        for selected_engine in engines:
            sessions.enter_context(selected_engine.projection_session())
        base_values = scores(original)

        def package_rank(package):
            values = scores(package)[drop_decision_team]
            return min(
                values[v] - base_values[drop_decision_team][v] for v in ("normal", "sensitivity")
            )

        packages.sort(key=package_rank, reverse=True)
        selected = packages[0]
        summary = compare(original, selected)
        drop_options = [{"drops": p.drops, "teams": scores(p)} for p in packages]
        completion_bundle = bundle
        if bundle.get("streaming", {}).get("enabled", False):
            completion_bundle = copy.deepcopy(bundle)
            completion_bundle.setdefault("completion", {})["adds_used_by_week"] = bundle[
                "streaming"
            ].get("adds_used_by_week", {})
        completions = completion_options(
            context, completion_bundle, original, selected, scores, engine
        )
        seed_options = [o for o in completions["options"] if o["team"] == mine]
        streaming = streaming_comparison(
            context,
            bundle,
            original,
            selected,
            scores,
            compare,
            engine,
            seeds={
                "before": [o["baseline"] for o in seed_options],
                "after": [o["scenario"] for o in seed_options],
            },
        )
        joint_completion = {"status": "not_needed", "data_sufficient": True, "options": []}
        partner_opens = len(set(selected.rosters[partner]) - selected.stashed) < len(
            set(original.rosters[partner]) - original.stashed
        )
        if partner_opens:
            joint_completion.update(status="not_requested", data_sufficient=False, team=partner)
        if complete_partner and partner_opens:
            before_managed, after_managed = original, selected
            if streaming["status"] == "planned":
                for path, base in (("before", original), ("after", selected)):
                    managed = base
                    for action in streaming[path]["actions"]:
                        managed = with_pickup(
                            managed, mine, action["add_id"], day(action["date"]), action["drop_id"]
                        )
                    if path == "before":
                        before_managed = managed
                    else:
                        after_managed = managed
            elif seed_options:
                before_managed, after_managed = (
                    seed_options[0]["baseline"],
                    seed_options[0]["scenario"],
                )
            partner_bundle = copy.deepcopy(completion_bundle)
            partner_settings = partner_bundle.setdefault("completion", {})
            partner_settings.update(enabled=True, min_gain_per_week=0)
            partner_settings["candidate_limit"] = min(partner_settings.get("candidate_limit", 8), 3)
            joint_completion = completion_options(
                context,
                partner_bundle,
                before_managed,
                after_managed,
                scores,
                engine,
                teams=[partner],
                require_positive_trade_gain=False,
            )
            joint_completion["team"] = partner
            joint_completion["reserved_player_ids"] = sorted(
                set(before_managed.starts) | set(after_managed.starts)
            )
            for option in joint_completion["options"]:
                option["teams"] = compare(option.pop("baseline"), option.pop("scenario"))
            if joint_completion["options"]:
                joint_completion["status"] = "applied"
                joint_completion["teams"] = joint_completion["options"][0]["teams"]
        for option in completions["options"]:
            option["teams"] = compare(option.pop("baseline"), option.pop("scenario"))
    if projection_cache is not None:
        # An externally scoped projection session does not perform the usual reset.
        engine.recompute_team_depth_and_injury_minutes()

    gain = summary[mine]["all_supplied_weeks"]["delta"]
    without_spillover = summary[mine]["without_spillover_delta"]
    near_gain = summary[mine]["near_term"]["delta"]
    decision_basis = "trade_only"
    own_options = [o for o in completions["options"] if o["team"] == mine]
    if own_options and streaming["status"] != "planned":
        chosen = own_options[0]
        gain, without_spillover, near_gain = (
            chosen["delta"],
            chosen["delta_without_spillover"],
            chosen["near_term_delta"],
        )
        decision_basis = "trade_plus_fa"
        conditions.append(
            "FA-assisted decision is conditional on the named pickup and acquisition budget."
        )
        if chosen["player_id"] not in exact:
            conditions.append("Suggested FA Yahoo position eligibility is approximate.")
    if streaming["status"] == "planned":
        gain = streaming["delta"]
        without_spillover = streaming["delta_without_spillover"]
        near_gain = streaming["near_term_delta"]
        if streaming["before"]["actions"] or streaming["after"]["actions"]:
            decision_basis = "trade_plus_streaming"
            conditions.append(
                "Streaming-assisted decision is conditional on the full dated action plan."
            )
            if not set(streaming.get("candidate_ids", [])) <= exact:
                conditions.append("Streaming candidate Yahoo position eligibility is approximate.")
    conditions.extend(streaming.get("conditions", []))
    if joint_completion["status"] == "applied":
        joint_ours = joint_completion["teams"][mine]
        gain = joint_ours["all_supplied_weeks"]["delta"]
        without_spillover = joint_ours["without_spillover_delta"]
        near_gain = joint_ours["near_term"]["delta"]
        decision_basis = "trade_plus_joint_fa"
        conditions.append(
            "Joint comparison includes the counterparty's named single FA completion; reserved FAs are not assigned to both teams."
        )
    if selected.stashed != original.stashed:
        conditions.append(
            "Post-trade IL assignment is explicit and assumes players remain stashed throughout the window."
        )
    conservative = min(gain, without_spillover)
    # No fitted acceptance margin or human-acceptance probability is invented.
    if math.isclose(gain, 0, abs_tol=1e-9):
        verdict = "borderline"
    elif conservative <= 0 < gain:
        verdict = "counter_or_review"
        conditions.append("Benefit disappears without injury spillover.")
    elif gain < 0:
        verdict = "reject_suggested"
    else:
        verdict = "conditional_accept"
    if gain * near_gain < 0:
        conditions.append("Near-term and full-window benefits have opposite signs.")
        verdict = "counter_or_review"
    if complete_partner:
        ours_opens = len(set(selected.rosters[mine]) - selected.stashed) < len(
            set(original.rosters[mine]) - original.stashed
        )
        ours_known = completions.get("data_sufficient", False)
        if streaming["status"] == "planned":
            ours_known = all(
                r["used_before"] is not None for r in streaming["after"]["weekly_budget"].values()
            )
        partner_known = joint_completion["status"] == "applied" or joint_completion.get(
            "data_sufficient", False
        )
        if (ours_opens and not ours_known) or (partner_opens and not partner_known):
            verdict = "needs_data"
            conditions.append(
                "Open-slot completion data or acquisition usage is missing; this is not a definitive rejection."
            )
    season_end = bundle.get("regular_season_end")
    next_week = today + pd.Timedelta(days=7 - today.weekday())
    full_season = bool(
        season_end and end == day(season_end) and day(weeks[0]["start"]) == next_week
    )
    if not full_season:
        conditions.append("Supplied weeks do not establish complete remaining-season coverage.")
    playoff_counts = []
    for period in bundle.get("playoff_periods", []):
        start, finish = day(period["start"]), day(period["end"])
        if start <= today or finish > pd.to_datetime(engine.schedule.GAME_DATE).max():
            raise ValueError("Playoff period must be future and within NBA schedule coverage")
        playoff_counts.append(
            {
                "start": period["start"],
                "end": period["end"],
                "scheduled_games": {
                    str(p): len(engine._get_player_schedule(engine.team_map[p], start, finish))
                    for p in outgoing + incoming
                },
            }
        )
    return {
        "schema_version": 4,
        "as_of": context.as_of.isoformat(),
        "sync_id": context.sync_id,
        "proposal": proposal,
        "proposal_display": {
            "our_team": context.team_names.get(mine, f"Takım {mine}"),
            "other_team": context.team_names.get(partner, f"Takım {partner}"),
            "give": [engine.players[p].name for p in outgoing],
            "receive": [engine.players[p].name for p in incoming],
            "effective_date": proposal["effective_date"],
        },
        "team_names": dict(context.team_names),
        "objective": "expected_category_points",
        "decision": {
            "basis": decision_basis,
            "delta": gain,
            "delta_without_spillover": without_spillover,
        },
        "verdict": verdict,
        "conditions": conditions,
        "coverage": "remaining_full_regular_season_weeks" if full_season else "supplied_weeks_only",
        "teams": summary,
        "roster_actions": {
            "drops": selected.drops,
            "post_trade_il": {
                t: sorted(set(selected.rosters[t]) & selected.stashed) for t in (mine, partner)
            },
        },
        "drop_alternatives": drop_options,
        "completion": completions,
        "streaming": streaming,
        "partner_completion": joint_completion,
        "roster_capacity": {
            t: {
                "before_active": len(set(original.rosters[t]) - original.stashed),
                "after_active": len(set(selected.rosters[t]) - selected.stashed),
                "before_open": 13 - len(set(original.rosters[t]) - original.stashed),
                "after_open": 13 - len(set(selected.rosters[t]) - selected.stashed),
            }
            for t in (mine, partner)
        },
        "names": {str(p): player.name for p, player in engine.players.items()},
        "normalized_package": _normalized_package(engine, outgoing, incoming, as_of),
        "playoff_schedule": playoff_counts,
        "assumptions": [
            "Single FA options are alternatives; the separately reported streaming plan carries dated ownership and weekly budgets."
            if streaming["status"] == "planned"
            else "FA options are alternative single pickups held for the remaining window; no streaming modeled.",
            "No manager acceptance probability modeled.",
            "FA shortlist uses a fast proxy; the reported options do not guarantee a global optimum.",
            "Completed/live partial fantasy weeks excluded.",
            "Neutral package totals exclude lineup constraints; playoff counts are raw games.",
            "Sensitivity is a scenario comparison, not a confidence interval.",
            "No calibrated acceptance margin; positive estimates remain conditional.",
        ],
        "source_hashes": context.source_hashes,
        "calendar_source": bundle["calendar_source"],
        "input_sha256": hashlib.sha256(json.dumps(bundle, sort_keys=True).encode()).hexdigest(),
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input", type=Path, nargs="?", help="Manual proposal, rules and real future fixtures"
    )
    parser.add_argument(
        "--inspect", action="store_true", help="Show current team/player IDs without writing files"
    )
    parser.add_argument("--output", type=Path, default=Path("reports/trades"))
    args = parser.parse_args()
    from .trade_report import render_trade_report

    if not args.inspect and args.input is None:
        parser.error("Supply an input JSON or --inspect")
    try:
        context = load_context()
        if args.inspect:
            inverse = {pid: yahoo_id for yahoo_id, pid in context.yahoo_ids.items()}
            print(
                json.dumps(
                    {
                        "sync_id": context.sync_id,
                        "captured_at": context.captured_at.isoformat(),
                        "teams": {
                            team: [
                                {
                                    "name": context.engine.players[p].name,
                                    "yahoo_player_id": inverse[p],
                                }
                                for p in roster
                            ]
                            for team, roster in context.rosters.items()
                        },
                        "warnings": context.warnings,
                        "available_players": [
                            {"name": context.engine.players[p].name, **item}
                            for p, item in context.available_players.items()
                        ],
                        "availability_audit": context.availability_audit,
                        "fantasy_calendar": context.fantasy_calendar,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        bundle = json.loads(args.input.read_text(encoding="utf-8"))
        result = evaluate_trade(context, bundle)
    except (ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    args.output.mkdir(parents=True, exist_ok=True)
    stem = result["input_sha256"][:12] + "_" + result["as_of"].replace(":", "").replace("+", "_")
    json_path = args.output / f"{stem}.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = args.output / f"{stem}.md"
    report.write_text(render_trade_report(result), encoding="utf-8")
    print(f"Saved offline trade analysis: {report.resolve()}")


if __name__ == "__main__":
    main()

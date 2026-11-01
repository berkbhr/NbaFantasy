"""Bounded league trade discovery and local counteroffers; no provider actions."""

import argparse
import copy
import hashlib
import json
import math
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from .trade_context import day, load_context, validate_calendar, validate_rules
from .trade_market import assess_market
from .trade_projection_cache import TradeProjectionCache
from .trades import evaluate_trade


def _integer(settings, key, default, maximum):
    value = settings.get(key, default)
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"search.{key} must be an integer in 1..{maximum}")
    return value


def _amount(settings, key, default):
    value = settings.get(key, default)
    if (
        isinstance(value, bool)
        or not isinstance(value, (float, int))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"search.{key} must be finite and nonnegative")
    return value


def _candidate_bundle(bundle, proposal, screen=False):
    candidate = copy.deepcopy(bundle)
    candidate["proposal"] = proposal
    # These instructions describe the old proposal, not newly generated packages.
    candidate["drop_yahoo_ids"] = {}
    candidate["post_trade_il_yahoo_ids"] = {}
    if screen:
        if candidate.get("streaming", {}).get("enabled"):
            candidate.setdefault("completion", {})["adds_used_by_week"] = candidate[
                "streaming"
            ].get("adds_used_by_week", {})
        candidate.setdefault("streaming", {})["enabled"] = False
        fa_mode = bundle.get("search", {}).get("screen_with_fa", "asymmetric")
        if type(fa_mode) is not bool and fa_mode != "asymmetric":
            raise ValueError("screen_with_fa must be true, false or asymmetric")
        candidate.setdefault("completion", {})["enabled"] = fa_mode is True or (
            fa_mode == "asymmetric"
            and len(proposal["give_yahoo_ids"]) != len(proposal["receive_yahoo_ids"])
        )
        fa_limit = _integer(bundle.get("search", {}), "screen_fa_candidates", 1, 5)
        candidate["completion"]["candidate_limit"] = min(
            candidate["completion"].get("candidate_limit", 8), fa_limit
        )
    return candidate


def effective_team_summaries(result):
    """Both teams in the same comparison that controls the final decision."""
    basis = result["decision"]["basis"]
    if basis == "trade_plus_joint_fa":
        return result["partner_completion"]["teams"]
    if basis == "trade_plus_streaming":
        return result["streaming"]["teams"]
    if basis == "trade_plus_fa":
        team = str(result["proposal"]["our_team"])
        return next(o["teams"] for o in result["completion"]["options"] if o["team"] == team)
    return result["teams"]


def effective_gains(result):
    """Use the exact comparison controlling the verdict, including the other team."""
    team = str(result["proposal"]["our_team"])
    partner = str(result["proposal"]["other_team"])
    summaries = effective_team_summaries(result)
    own = result["decision"]
    other = summaries[partner]
    capacity = result.get("roster_capacity", {})
    ours_opens = capacity.get(team, {}).get("after_open", 0) > capacity.get(team, {}).get(
        "before_open", 0
    )
    partner_opens = capacity.get(partner, {}).get("after_open", 0) > capacity.get(partner, {}).get(
        "before_open", 0
    )
    own_stream = result.get("streaming", {})
    own_known = result.get("completion", {}).get("data_sufficient", False)
    if own_stream.get("status") == "planned":
        own_known = all(
            row["used_before"] is not None for row in own_stream["after"]["weekly_budget"].values()
        )
    partner_data = result.get("partner_completion", {})
    partner_known = partner_data.get("status") == "applied" or partner_data.get(
        "data_sufficient", False
    )
    return {
        "ours": own["delta"],
        "ours_conservative": min(own["delta"], own["delta_without_spillover"]),
        "partner": other["all_supplied_weeks"]["delta"],
        "partner_conservative": min(
            other["all_supplied_weeks"]["delta"], other["without_spillover_delta"]
        ),
        "basis": own["basis"],
        "ours_opens_slot": ours_opens,
        "partner_opens_slot": partner_opens,
        "ours_replacement_known": not ours_opens or own_known,
        "partner_replacement_known": not partner_opens or partner_known,
    }


def _diverse_shortlist(by_team, budget):
    """Reserve deterministic exploration without changing any model utility score.

    Each opponent receives turns, and its package shapes rotate. Within those
    turns, quality and outgoing-coverage selections alternate. Exploration is
    only a choice of what to calculate; it never qualifies a trade.
    """
    queues = {team: list(rows) for team, rows in by_team.items()}
    player_uses, package_uses, shape_uses, team_turns = Counter(), Counter(), Counter(), Counter()
    selected = []

    def package(candidate):
        return tuple(sorted(map(str, candidate["proposal"]["give_yahoo_ids"])))

    def quality_key(candidate):
        return (-candidate["quick"]["joint"], json.dumps(candidate["proposal"], sort_keys=True))

    while len(selected) < budget:
        progress = False
        for team in sorted(queues):
            if not queues[team] or len(selected) >= budget:
                continue
            minimum = min(shape_uses[(team, c["shape"])] for c in queues[team])
            available = [c for c in queues[team] if shape_uses[(team, c["shape"])] == minimum]
            explore = team_turns[team] % 2 == 1
            if explore:

                def coverage_key(candidate):
                    ids = package(candidate)
                    counts = [player_uses[p] for p in ids]
                    return (
                        sum(counts) / len(counts),
                        max(counts),
                        package_uses[ids],
                        *quality_key(candidate),
                    )

                chosen = min(available, key=coverage_key)
            else:
                chosen = min(available, key=quality_key)
            queues[team].remove(chosen)
            chosen["selection_reason"] = "outgoing_coverage" if explore else "quick_quality"
            selected.append(chosen)
            ids = package(chosen)
            player_uses.update(ids)
            package_uses[ids] += 1
            shape_uses[(team, chosen["shape"])] += 1
            team_turns[team] += 1
            progress = True
        if not progress:
            break
    return selected


def _outgoing_coverage(context, bundle, candidates):
    mine = str(bundle["proposal"]["our_team"])
    locked = {context.yahoo_ids[str(i)] for i in bundle.get("do_not_trade_yahoo_ids", [])}
    eligible = set(context.rosters[mine]) - context.engine.yahoo_already_stashed_ids - locked
    uses = Counter(
        context.yahoo_ids[str(yahoo)]
        for c in candidates
        for yahoo in c["proposal"]["give_yahoo_ids"]
    )
    return [
        {"name": context.engine.players[pid].name, "evaluated_packages": uses[pid]}
        for pid in sorted(eligible)
    ]


def _shortlist(context, bundle, mode, settings):
    """Vectorized local gradients shortlist; never the final recommendation score."""
    mine = str(bundle["proposal"]["our_team"])
    types = settings.get("package_types", ["1x1", "2x2", "2x1", "1x2"])
    if not types or not set(types) <= {f"{a}x{b}" for a in range(1, 5) for b in range(1, 5)}:
        raise ValueError("search.package_types must use between one and four players per side")
    per_shape = _integer(settings, "per_shape_candidates", 8, 50)
    budget = _integer(settings, "shortlist_size", 40, 150)
    max_edits = _integer(settings, "max_counter_edits", 2, 2)
    inverse = {p: yahoo for yahoo, p in sorted(context.yahoo_ids.items())}
    locked = {context.yahoo_ids[str(i)] for i in bundle.get("do_not_trade_yahoo_ids", [])}
    eligible = {
        t: sorted(set(ids) - context.engine.yahoo_already_stashed_ids - locked)
        for t, ids in context.rosters.items()
    }
    partners = settings.get("team_ids", [t for t in context.rosters if t != mine])
    if mode == "opportunities" and bundle.get("proposal", {}).get("other_team"):
        target_partner = str(bundle["proposal"]["other_team"])
        if target_partner not in context.rosters or target_partner == mine:
            raise ValueError("Choose a known opponent for the targeted search")
        partners = [target_partner]
    if not isinstance(partners, list) or len(set(map(str, partners))) != len(partners):
        raise ValueError("search.team_ids must be a unique list of known opponent IDs")
    partners = [str(t) for t in partners]
    if any(t == mine or t not in context.rosters for t in partners):
        raise ValueError("Search team must identify another known team")
    selected_give_yahoos = [str(i) for i in bundle.get("proposal", {}).get("give_yahoo_ids", [])]
    selected_give_pids = set()
    if mode == "opportunities" and selected_give_yahoos:
        if (
            len(set(selected_give_yahoos)) != len(selected_give_yahoos)
            or len(selected_give_yahoos) > 4
        ):
            raise ValueError(
                "Fırsat taramasında birlikte verilecek en fazla dört farklı oyuncu seç."
            )
        for yahoo in selected_give_yahoos:
            if yahoo not in context.yahoo_ids or context.yahoo_ids[yahoo] not in eligible[mine]:
                raise ValueError(
                    "Seçilen oyuncu kendi güncel aktif kadrona ait değil veya takas korumasında/IL listesinde."
                )
            selected_give_pids.add(context.yahoo_ids[yahoo])
        if len(selected_give_pids) > 2 and "package_types" not in settings:
            size = len(selected_give_pids)
            types = [f"{size}x{b}" for b in range(max(1, size - 1), min(4, size + 1) + 1)]
        if not any(int(shape.split("x")[0]) == len(selected_give_pids) for shape in types):
            raise ValueError("Arama paket türleri seçtiğin tam giden paketi kapsamıyor.")
    focused_exhaustive = bool(mode == "opportunities" and selected_give_pids and len(partners) == 1)
    diversify = mode == "opportunities" and not selected_give_pids
    if focused_exhaustive:
        total = sum(
            math.comb(len(eligible[partners[0]]), int(shape.split("x")[1]))
            for shape in set(types)
            if int(shape.split("x")[0]) == len(selected_give_pids)
            and int(shape.split("x")[1]) <= len(eligible[partners[0]])
        )
        focused_exhaustive = total <= 200
    original_give, original_receive = set(), set()
    if mode == "counter":
        partner = str(bundle["proposal"]["other_team"])
        if partner not in partners:
            raise ValueError("Counteroffer partner is outside search.team_ids")
        partners = [partner]
        original_give = {context.yahoo_ids[str(i)] for i in bundle["proposal"]["give_yahoo_ids"]}
        original_receive = {
            context.yahoo_ids[str(i)] for i in bundle["proposal"]["receive_yahoo_ids"]
        }
    engine = copy.deepcopy(context.engine)
    for yahoo, slots in bundle.get("eligible_positions", {}).items():
        if (
            str(yahoo) not in context.yahoo_ids
            or not slots
            or not set(slots) <= {"PG", "SG", "SF", "PF", "C"}
        ):
            raise ValueError("Invalid exact Yahoo eligibility override")
        engine.pos_dict[context.yahoo_ids[str(yahoo)]] = ",".join(sorted(set(slots)))
    players = sorted({p for ids in eligible.values() for p in ids})
    if any(
        p not in inverse or p not in engine.players or not engine.team_map.get(p) for p in players
    ):
        raise ValueError("Search players require resolved model/Yahoo/NBA identities")
    as_of = pd.Timestamp(context.as_of).tz_convert("America/New_York").tz_localize(None).normalize()
    marginals = {t: dict.fromkeys(players, 0.0) for t in [mine] + partners}
    with engine.projection_session():
        for week in bundle["weeks"]:
            distributions = {
                t: engine.get_expected_weekly_distribution(
                    ids, week["start"], week["end"], as_of_date=as_of
                )
                for t, ids in context.rosters.items()
            }
            opponents = {}
            for a, b in week["fixtures"]:
                opponents[str(a)], opponents[str(b)] = str(b), str(a)
            for team in marginals:
                own = distributions[team]
                _, _, weights = engine.evaluate_h2h_matchup(own, distributions[opponents[team]])
                mean = own["mean"]
                fg = mean["FGM"] / mean["FGA"] if mean["FGA"] else 0.47
                ft = mean["FTM"] / mean["FTA"] if mean["FTA"] else 0.78
                for pid in players:
                    tid = engine.team_map[pid]
                    for when in engine._get_player_schedule(tid, week["start"], week["end"]):
                        mu, _ = engine._daily_projections(when, as_of, True, [pid])[pid]
                        b2b = when - pd.Timedelta(days=1) in engine._all_schedule_dates.get(
                            tid, set()
                        )
                        probability = engine.players[pid].get_effective_game_availability(
                            game_date=when, as_of_date=as_of, is_b2b=b2b
                        )
                        marginals[team][pid] += probability * engine._player_value(
                            {"PROJ": mu}, weights, fg, ft
                        )
    by_team = defaultdict(list)
    generated = 0
    blocked_market = 0
    for partner in partners:
        for shape in sorted(set(types)):
            a, b = map(int, shape.split("x"))
            gives = list(combinations(eligible[mine], a))
            if selected_give_pids:
                gives = [g for g in gives if set(g) == selected_give_pids]
            receives = list(combinations(eligible[partner], b))
            if not gives or not receives:
                continue
            ours = (
                np.array([sum(marginals[mine][p] for p in pack) for pack in receives])[None, :]
                - np.array([sum(marginals[mine][p] for p in pack) for pack in gives])[:, None]
            )
            theirs = (
                np.array([sum(marginals[partner][p] for p in pack) for pack in gives])[:, None]
                - np.array([sum(marginals[partner][p] for p in pack) for pack in receives])[None, :]
            )
            mask = np.ones(ours.shape, dtype=bool)
            if mode == "counter":
                dg = np.array([len(set(pack) ^ original_give) for pack in gives])
                dr = np.array([len(set(pack) ^ original_receive) for pack in receives])
                distance = dg[:, None] + dr[None, :]
                retained = (
                    np.array([bool(set(pack) & original_give) for pack in gives])[:, None]
                    | np.array([bool(set(pack) & original_receive) for pack in receives])[None, :]
                )
                mask &= (distance > 0) & (distance <= max_edits) & retained
            generated += int(mask.sum())
            joint = ours + np.minimum(theirs, 0)
            order = np.argsort(-joint.ravel(), kind="stable")
            kept = 0
            covered_gives = set()
            for flat in order:
                i, j = np.unravel_index(flat, joint.shape)
                if not mask[i, j]:
                    continue
                if diversify and kept >= per_shape and i in covered_gives:
                    continue
                proposal = {
                    "snapshot_id": context.sync_id,
                    "our_team": mine,
                    "other_team": partner,
                    "give_yahoo_ids": [inverse[p] for p in gives[i]],
                    "receive_yahoo_ids": [inverse[p] for p in receives[j]],
                    "effective_date": bundle["proposal"]["effective_date"],
                }
                market = assess_market(context, bundle, proposal)
                if market["blocked"]:
                    blocked_market += 1
                    continue
                if settings.get("require_market", False) and market["status"] != "balanced_value":
                    continue
                by_team[partner].append(
                    {
                        "proposal": proposal,
                        "market": market,
                        "shape": shape,
                        "quick": {
                            "ours": float(ours[i, j]),
                            "partner": float(theirs[i, j]),
                            "joint": float(joint[i, j]),
                        },
                    }
                )
                covered_gives.add(i)
                kept += 1
                if diversify and kept >= per_shape and len(covered_gives) == len(gives):
                    break
                if kept >= per_shape and not focused_exhaustive and not diversify:
                    break
    # Give each partner and package shape a chance before filling the global budget.
    queues = {}
    for partner, candidates in by_team.items():
        candidates.sort(
            key=lambda c: (-c["quick"]["joint"], json.dumps(c["proposal"], sort_keys=True))
        )
        firsts, rest, seen = [], [], set()
        for candidate in candidates:
            if candidate["shape"] in seen:
                rest.append(candidate)
            else:
                firsts.append(candidate)
                seen.add(candidate["shape"])
        queues[partner] = firsts + rest
    selected = []
    selection_limit = 200 if focused_exhaustive else budget
    while len(selected) < selection_limit:
        progress = False
        for partner in sorted(queues):
            if queues[partner] and len(selected) < selection_limit:
                selected.append(queues[partner].pop(0))
                progress = True
        if not progress:
            break
    if diversify:
        selected = _diverse_shortlist(by_team, budget)
    return selected, {
        "generated_packages": generated,
        "market_outliers_skipped": blocked_market,
        "shortlisted": len(selected),
        "teams_considered": partners,
        "excluded_il_players": len(context.engine.yahoo_already_stashed_ids),
        "focused_exhaustive": focused_exhaustive,
        "selected_give_yahoo_ids": selected_give_yahoos if mode == "opportunities" else [],
        "package_types": sorted(set(types)),
        "selection_policy": "quality_and_outgoing_coverage" if diversify else "quick_quality",
        "quality_selected": sum(c.get("selection_reason") == "quick_quality" for c in selected),
        "coverage_selected": sum(
            c.get("selection_reason") == "outgoing_coverage" for c in selected
        ),
        "shortlisted_outgoing_player_coverage": _outgoing_coverage(context, bundle, selected),
        "outgoing_packages_selected": len(
            {tuple(sorted(c["proposal"]["give_yahoo_ids"])) for c in selected}
        ),
    }


def _screen_priority(candidate, min_gain, partner_loss):
    gains = candidate["screening"]
    known = gains["ours_replacement_known"] and gains["partner_replacement_known"]
    feasible = (
        known
        and gains["ours_conservative"] >= min_gain
        and gains["partner_conservative"] >= -partner_loss
    )
    margin = min(
        gains["ours_conservative"] - min_gain, gains["partner_conservative"] + partner_loss
    )
    return (
        not feasible,
        not known,
        -margin,
        -gains["ours_conservative"],
        json.dumps(candidate["proposal"], sort_keys=True),
    )


def search_trades(context, bundle, mode="opportunities"):
    """Screen without streaming, refine only top packages; return reviewable offers."""
    from .fantasy_calendar import resolve_trade_calendar

    bundle = resolve_trade_calendar(context, bundle)
    started = time.perf_counter()
    if mode not in ("opportunities", "counter"):
        raise ValueError("Search mode must be opportunities or counter")
    rules = validate_rules(bundle)
    weeks = validate_calendar(bundle, context.rosters, context.as_of)
    proposal = bundle["proposal"]
    mine = str(proposal["our_team"])
    if mine not in context.rosters or proposal.get("snapshot_id") != context.sync_id:
        raise ValueError("Search requires a known team and current roster snapshot_id")
    if (context.as_of - context.captured_at).total_seconds() > 86400:
        raise ValueError("Refresh rosters before automatic trade discovery")
    effective = day(proposal["effective_date"])
    today = pd.Timestamp(context.as_of).tz_convert("America/New_York").tz_localize(None).normalize()
    if not today <= effective <= day(weeks[0]["start"]):
        raise ValueError("Effective date must be between analysis day and first full fantasy week")
    if rules.get("trade_deadline") and effective > day(rules["trade_deadline"]):
        raise ValueError("Effective date exceeds the trade deadline")
    if rules.get("review_days") is not None:
        review = rules["review_days"]
        if type(review) is not int or review < 0 or effective < today + pd.Timedelta(days=review):
            raise ValueError("Effective date must respect the known review period")
    if (
        context.engine.schedule.empty
        or day(weeks[-1]["end"]) > pd.to_datetime(context.engine.schedule.GAME_DATE).max()
    ):
        raise ValueError("Dated NBA schedule does not cover the analyzed weeks")
    settings = bundle.get("search", {})
    refine_limit = _integer(settings, "streaming_finalists", 3, 10)
    min_gain = _amount(settings, "min_gain_per_week", 0.05) * len(weeks)
    partner_loss = _amount(settings, "max_partner_loss_per_week", 0.05) * len(weeks)
    improvement = _amount(settings, "counter_improvement_per_week", 0.01) * len(weeks)
    slack = _amount(settings, "refinement_slack_per_week", 0.25) * len(weeks)
    # Validate even an absent market snapshot's policy up front.
    if not bundle.get("market_snapshot"):
        assess_market(context, bundle, {"give_yahoo_ids": [], "receive_yahoo_ids": []})
    candidates, counts = _shortlist(context, bundle, mode, settings)
    generated_at = context.as_of.isoformat()
    projection_cache = {}
    reuse = settings.get("reuse_projections", True)
    if type(reuse) is not bool:
        raise ValueError("search.reuse_projections must be a boolean")
    matchup_cache = TradeProjectionCache() if reuse else None
    evaluated_cache = {}
    timings = {"shortlist_seconds": time.perf_counter() - started}
    errors = []

    def evaluate(candidate_bundle):
        key = json.dumps(candidate_bundle, sort_keys=True)
        if key not in evaluated_cache:
            evaluated_cache[key] = evaluate_trade(
                context,
                candidate_bundle,
                projection_cache=projection_cache,
                complete_partner=True,
                matchup_cache=matchup_cache,
            )
        return evaluated_cache[key]

    original_result = None
    if mode == "counter":
        # Explicit incoming offers bypass automatic opportunity/market filters.
        original_result = evaluate(copy.deepcopy(bundle))
    screen_start = time.perf_counter()
    screened = []
    for candidate in candidates:
        try:
            analysis = evaluate(_candidate_bundle(bundle, candidate["proposal"], screen=True))
        except (ValueError, KeyError) as exc:
            errors.append({"proposal": candidate["proposal"], "reason": str(exc)})
            continue
        candidate["screening"] = effective_gains(analysis)
        candidate["display"] = analysis["proposal_display"]
        candidate["screening_verdict"] = analysis["verdict"]
        screened.append(candidate)
    timings["screen_seconds"] = time.perf_counter() - screen_start
    screened.sort(key=lambda c: _screen_priority(c, min_gain, partner_loss))
    eligible = [
        c
        for c in screened
        if (
            c["screening"]["ours_conservative"] >= min_gain - slack
            or not c["screening"]["ours_replacement_known"]
        )
        and (
            c["screening"]["partner_conservative"] >= -partner_loss - slack
            or (
                not c["screening"]["partner_replacement_known"]
                and c["screening"]["partner_conservative"] >= -partner_loss - slack - 0.35
            )
        )
    ]
    finalists = []
    refine_start = time.perf_counter()
    for candidate in eligible[:refine_limit]:
        try:
            full = evaluate(_candidate_bundle(bundle, candidate["proposal"]))
        except (ValueError, KeyError) as exc:
            errors.append({"proposal": candidate["proposal"], "reason": str(exc)})
            continue
        candidate = copy.deepcopy(candidate)
        gains = effective_gains(full)
        candidate.update(final=gains, analysis=full, display=full["proposal_display"])
        reasons, review_reasons, codes = [], [], []
        if candidate["market"]["requires_review"]:
            review_reasons.append(
                "Piyasa makullüğü doğrulanmadı; model adayıdır, menajerin kabul edeceği anlamına gelmez."
            )
        if not gains["ours_replacement_known"] or not gains["partner_replacement_known"]:
            reasons.append(
                "Açılan yerin FA/hamle verisi doğrulanmadı; boş kadrodan kesin ret sonucu çıkarılmadı."
            )
            codes.append("replacement_data_missing")
        if gains["ours_replacement_known"] and gains["ours_conservative"] < min_gain:
            reasons.append("Son değerlendirmede bizim katkı eşiğimiz karşılanmadı.")
            codes.append("own_gain_below_threshold")
        if gains["partner_conservative"] < -partner_loss:
            reasons.append("Karşı takımın kaybı yapılandırılmış toleransın üzerinde.")
            codes.append("partner_loss_exceeds_tolerance")
        if (
            full["verdict"] in ("reject_suggested", "counter_or_review", "borderline")
            and gains["ours_replacement_known"]
            and gains["partner_replacement_known"]
        ):
            reasons.append("Karar motoru güçlü bir koşullu kabul üretmedi.")
            codes.append("core_verdict")
        if original_result is not None:
            candidate["improvement_over_original"] = (
                gains["ours_conservative"] - effective_gains(original_result)["ours_conservative"]
            )
            if candidate["improvement_over_original"] < improvement:
                reasons.append("Karşı teklif mevcut teklifi yeterince iyileştirmiyor.")
                codes.append("counter_improvement")
        candidate.update(
            model_qualified=not reasons,
            qualified=not reasons and not review_reasons,
            blocking_reasons=reasons,
            review_reasons=review_reasons,
            rejection_codes=codes,
            rejection_reasons=reasons + review_reasons,
            status=(
                "replacement_data_required"
                if not gains["ours_replacement_known"] or not gains["partner_replacement_known"]
                else "conditional_market_review"
                if candidate["market"]["requires_review"]
                else "conditional_opportunity"
            ),
        )
        finalists.append(candidate)
    timings["refine_seconds"] = time.perf_counter() - refine_start
    finalists.sort(
        key=lambda c: (
            -c["final"]["ours_conservative"],
            -c["final"]["partner_conservative"],
            json.dumps(c["proposal"], sort_keys=True),
        )
    )
    final_by_key = {json.dumps(c["proposal"], sort_keys=True): c for c in finalists}
    preliminary = []
    evaluated_packages = []
    model_screen_passed = 0
    for candidate in screened:
        key = json.dumps(candidate["proposal"], sort_keys=True)
        gains = candidate["screening"]
        reasons = []
        if not gains["ours_replacement_known"] or not gains["partner_replacement_known"]:
            reasons.append("FA/hamle verisi eksik")
        if gains["ours_conservative"] < min_gain:
            reasons.append("Bizim kazanç filtresinin altında")
        if gains["partner_conservative"] < -partner_loss:
            reasons.append("Karşı tarafın kayıp filtresini aşıyor")
        if candidate["screening_verdict"] in (
            "reject_suggested",
            "counter_or_review",
            "borderline",
        ):
            reasons.append("Ön karar olumlu değil")
        if not reasons:
            model_screen_passed += 1
        final = final_by_key.get(key)
        if final:
            status = (
                "Nihai model adayı"
                if final["model_qualified"]
                else "Nihai değerlendirmede elendi / veri bekliyor"
            )
            stage_reasons = final["blocking_reasons"]
            display_gains = final["final"]
        else:
            if mode == "counter":
                reasons.append("Karşı teklif için nihai karşılaştırma bekliyor")
            status = (
                "Ön değerlendirmede uygun; nihai hesap bekliyor"
                if not reasons
                else "Ön değerlendirmede elendi / veri bekliyor"
            )
            stage_reasons = reasons
            display_gains = gains
            if not reasons:
                preliminary.append(
                    {
                        "proposal": candidate["proposal"],
                        "display": candidate["display"],
                        "screening": gains,
                        "evaluation_level": "screened",
                        "qualified": False,
                        "market": candidate["market"],
                        "review_reasons": [
                            "Bu paket yalnız ön değerlendirmeden geçti; nihai FA/streaming karşılaştırması yapılmadı."
                        ],
                    }
                )
        evaluated_packages.append(
            {
                "display": candidate["display"],
                "gains": display_gains,
                "evaluation_level": "final" if final else "screened",
                "status": status,
                "reasons": stage_reasons,
            }
        )
    timings["total_seconds"] = time.perf_counter() - started
    return {
        "schema_version": 1,
        "mode": mode,
        "as_of": generated_at,
        "scenario_scope": bundle.get("benchmark_scope") or bundle.get("scenario_note"),
        "sync_id": context.sync_id,
        "our_team": mine,
        "team_names": dict(context.team_names),
        "opportunities": [c for c in finalists if c["qualified"]],
        "review_opportunities": [
            c for c in finalists if c["model_qualified"] and not c["qualified"]
        ],
        "finalists": finalists,
        "preliminary_candidates": preliminary,
        "evaluated_packages": evaluated_packages,
        "search_diagnostics": {
            "screen_evaluated": len(screened),
            "final_evaluated": len(finalists),
            "model_screen_passed": model_screen_passed,
            "not_refined": len(screened) - len(finalists),
            "preliminary_candidates": len(preliminary),
            "final_model_candidates": sum(c["model_qualified"] for c in finalists),
            "search_exhaustive": False,
            "outgoing_player_coverage": _outgoing_coverage(context, bundle, screened),
            "outgoing_packages_evaluated": len(
                {tuple(sorted(c["proposal"]["give_yahoo_ids"])) for c in screened}
            ),
            "selection_policy": counts.get("selection_policy", "quick_quality"),
            "quality_selected": counts.get("quality_selected", 0),
            "coverage_selected": counts.get("coverage_selected", 0),
        },
        "screened": screened,
        "original_analysis": original_result,
        "original_market": assess_market(context, bundle, proposal) if original_result else None,
        "errors": errors,
        "counts": {
            **counts,
            "screen_evaluated": len(screened),
            "refined": len(finalists),
            "refinement_limit": refine_limit,
            "original_evaluated": int(original_result is not None),
            "projection_cache_entries": len(projection_cache),
            "matchup_cache": matchup_cache.stats()
            if matchup_cache is not None
            else {"enabled": False},
        },
        "thresholds": {
            "our_min_gain": min_gain,
            "partner_max_loss": partner_loss,
            "weeks": len(weeks),
            "basis": "user_preference_not_statistical_significance",
            "min_gain_per_week": min_gain / len(weeks),
            "max_partner_loss_per_week": partner_loss / len(weeks),
        },
        "search_scope": {
            "our_team": mine,
            "target_teams": counts["teams_considered"],
            "outgoing_names": [
                context.engine.players[context.yahoo_ids[y]].name
                for y in counts.get("selected_give_yahoo_ids", [])
            ],
            "outgoing_mode": "exact" if counts.get("selected_give_yahoo_ids") else "unrestricted",
            "focused_exhaustive": counts.get("focused_exhaustive", False),
            "screen_evaluated": len(screened),
            "finalist_limit": refine_limit,
            "package_types": counts.get("package_types", []),
        },
        "timings": timings,
        "source_hashes": context.source_hashes,
        "calendar_source": bundle["calendar_source"],
        "input_sha256": hashlib.sha256(json.dumps(bundle, sort_keys=True).encode()).hexdigest(),
        "conditions": list(context.warnings)
        + [
            "Arama sınırlıdır; negatif hızlı puanlar ve kısa liste dışında kalan paketler için optimum iddiası yoktur.",
            "Ön eleme streaming kullanmaz; yalnız son adaylar aynı nihai ayarlarla karşılaştırılır.",
            "Piyasa göstergeleri kategori puanına eklenmez; menajer kabul olasılığı değildir.",
            "Otomatik arama IL oyuncularını taşımaz; mevcut IL yerleşimini korur.",
            "Karşı takımın gelecekteki streaming hamleleri tahmin edilmez.",
            "Paketler birbirinin alternatifidir; birlikte uygulanacak takas listesi değildir.",
        ],
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--mode", choices=("opportunities", "counter"), default="opportunities")
    parser.add_argument("--market", type=Path, help="Source-attributed market snapshot JSON")
    parser.add_argument("--output", type=Path, default=Path("reports/trade_search"))
    args = parser.parse_args()
    from .trade_search_report import render_search_report

    try:
        bundle = json.loads(args.input.read_text(encoding="utf-8"))
        if args.market:
            bundle["market_snapshot"] = json.loads(args.market.read_text(encoding="utf-8"))
        result = search_trades(load_context(), bundle, args.mode)
    except (ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    args.output.mkdir(parents=True, exist_ok=True)
    stamp = result["as_of"].replace(":", "").replace("+", "_")
    path = args.output / f"{args.mode}_{stamp}_{result['input_sha256'][:12]}"
    json_path, report_path = Path(str(path) + ".json"), Path(str(path) + ".md")
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(render_search_report(result), encoding="utf-8")
    print(f"Saved offline trade search: {report_path.resolve()}")


if __name__ == "__main__":
    main()

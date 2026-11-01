"""Simultaneous three-team trades using the shared daily-lineup engine."""

import copy
import hashlib
import json
import time

import pandas as pd

from .fantasy_calendar import resolve_trade_calendar
from .trade_context import day, validate_calendar, validate_rules
from .trade_packages import RosterScenario, drop_protection, trade_il_assignments, validate_scenario
from .trades import _aggregate, _pair, _summary


def evaluate_multiteam_trade(context, bundle, *, deadline=None):
    bundle = resolve_trade_calendar(context, bundle)
    weeks = validate_calendar(bundle, context.rosters, context.as_of)
    rules = validate_rules(bundle)
    proposal = bundle["proposal"]
    if proposal.get("snapshot_id") != context.sync_id:
        raise ValueError("Kadro kaydı değişti; seçimini yenile.")
    effective = day(proposal["effective_date"])
    today = pd.Timestamp(context.as_of).tz_convert("America/New_York").tz_localize(None).normalize()
    if effective < today or effective > day(weeks[0]["start"]):
        raise ValueError("İşlem tarihi analiz edilen ilk tam haftadan önce olmalı.")
    if rules.get("trade_deadline") and effective > day(rules["trade_deadline"]):
        raise ValueError("Takas son tarihi aşılıyor.")
    if rules.get("review_days") is not None and effective < today + pd.Timedelta(
        days=rules["review_days"]
    ):
        raise ValueError("İnceleme süresi işlem tarihine sığmıyor.")
    if (context.as_of - context.captured_at).total_seconds() > 86400:
        raise ValueError("Kadro 24 saatten eski; Yahoo senkronunu yenile.")
    transfers = proposal["transfers"]
    if not isinstance(transfers, list) or not 3 <= len(transfers) <= 12:
        raise ValueError("Üç takım arasında 3–12 oyuncu hareketi seç.")
    participants, seen, resolved = set(), set(), []
    protected_trade = set(map(str, bundle.get("do_not_trade_yahoo_ids", [])))
    for move in transfers:
        source, target = str(move["from_team"]), str(move["to_team"])
        yahoo = str(move["yahoo_player_id"])
        pid = context.yahoo_ids[yahoo]
        if (
            source == target
            or source not in context.rosters
            or target not in context.rosters
            or pid not in context.rosters[source]
            or pid in seen
        ):
            raise ValueError(
                "Oyuncu sahipliği veya hedef takım geçersiz; bir oyuncu bir kez gönderilebilir."
            )
        if yahoo in protected_trade:
            raise ValueError("Korumalı oyuncu takasa eklenemez.")
        participants.update((source, target))
        seen.add(pid)
        resolved.append((source, target, pid))
    if len(participants) != 3 or str(proposal["our_team"]) not in participants:
        raise ValueError("Üç farklı takım ve senin takımın seçilmeli.")
    for team in participants:
        sent = sum(s == team for s, t, p in resolved)
        received = sum(t == team for s, t, p in resolved)
        if not 1 <= sent <= 4 or not 1 <= received <= 4:
            raise ValueError("Her takım 1–4 oyuncu vermeli ve 1–4 oyuncu almalı.")
    before = RosterScenario(
        copy.deepcopy(context.rosters), set(context.engine.yahoo_already_stashed_ids)
    )
    after = copy.deepcopy(before)
    for source, target, pid in resolved:
        after.rosters[source].remove(pid)
    for source, target, pid in resolved:
        after.rosters[target].append(pid)
    after.stashed = trade_il_assignments(context, bundle, after.rosters, seen, participants)
    instructions = bundle.get("drop_yahoo_ids", {})
    if set(instructions) - participants:
        raise ValueError("Bırakma yalnız takasa katılan takımlarda yapılabilir.")
    for team in participants:
        ids = [context.yahoo_ids[str(p)] for p in instructions.get(team, [])]
        needed = max(0, len(set(after.rosters[team]) - after.stashed) - 13)
        if (
            len(ids) != needed
            or len(set(ids)) != len(ids)
            or not set(ids)
            <= set(after.rosters[team]) - after.stashed - seen - drop_protection(context, bundle)
        ):
            raise ValueError(
                f"{context.team_names.get(team, team)}: kadro sınırı için {needed} uygun oyuncu bırakılmalı."
            )
        after.drops[team] = ids
        after.rosters[team] = [p for p in after.rosters[team] if p not in ids]
    validate_scenario(before, context.engine.players)
    validate_scenario(after, context.engine.players)
    if day(weeks[-1]["end"]) > pd.to_datetime(context.engine.schedule.GAME_DATE).max():
        raise ValueError("NBA takvimi analiz ufkunu kapsamıyor.")
    if any(context.engine.team_map.get(p) is None for ids in context.rosters.values() for p in ids):
        raise ValueError("Tüm kadroların NBA takım bilgisi gerekli.")
    modes = {}
    for mode in ("normal", "without_spillover"):
        engine = copy.deepcopy(context.engine)
        engine.use_positional_depth_and_injury_boost = mode == "normal"
        for yahoo, positions in bundle.get("eligible_positions", {}).items():
            if (
                str(yahoo) not in context.yahoo_ids
                or not positions
                or not set(positions) <= {"PG", "SG", "SF", "PF", "C"}
            ):
                raise ValueError("Invalid Yahoo position override")
            engine.pos_dict[context.yahoo_ids[str(yahoo)]] = ",".join(sorted(set(positions)))
        engine.objective = "category_points"
        engine.draw_value = 0.5
        scores = []
        with engine.projection_session():
            for scenario in (before, after):
                engine.yahoo_already_stashed_ids = set(scenario.stashed)
                rows = {team: [] for team in participants}
                for week in weeks:
                    for home, away in week["fixtures"]:
                        home, away = str(home), str(away)
                        if not {home, away} & participants:
                            continue
                        if deadline is not None and time.perf_counter() >= deadline:
                            raise TimeoutError("Analiz süre bütçesi doldu.")
                        pair = _pair(
                            engine,
                            scenario.rosters[home],
                            scenario.rosters[away],
                            week["start"],
                            week["end"],
                            today,
                        )
                        for team, index in ((home, 0), (away, 1)):
                            if team in rows:
                                rows[team].append(
                                    dict(
                                        start=week["start"],
                                        end=week["end"],
                                        opponent=away if index == 0 else home,
                                        result=_summary(engine, pair[index], pair[1 - index]),
                                    )
                                )
                scores.append(rows)
        modes[mode] = {}
        for team in sorted(participants):
            rows = [
                dict(
                    start=a["start"],
                    end=a["end"],
                    opponent=a["opponent"],
                    before=a["result"],
                    after=b["result"],
                )
                for a, b in zip(scores[0][team], scores[1][team])
            ]
            modes[mode][team] = dict(all_supplied_weeks=_aggregate(rows), weekly=rows)
    teams = modes["normal"]
    for team, row in teams.items():
        row["without_spillover_delta"] = modes["without_spillover"][team]["all_supplied_weeks"][
            "delta"
        ]
        row["conservative_delta"] = min(
            row["all_supplied_weeks"]["delta"], row["without_spillover_delta"]
        )
    mine = str(proposal["our_team"])
    delta = teams[mine]["all_supplied_weeks"]["delta"]
    sensitivity_delta = teams[mine]["without_spillover_delta"]
    if abs(delta) <= 1e-9:
        verdict = "borderline"
    elif min(delta, sensitivity_delta) <= 0 < delta:
        verdict = "counter_or_review"
    elif delta < 0:
        verdict = "reject_suggested"
    else:
        verdict = "conditional_accept"
    return dict(
        kind="three_team",
        proposal=proposal,
        teams=teams,
        team_names=context.team_names,
        transfers=[
            dict(from_team=s, to_team=t, name=context.engine.players[p].name)
            for s, t, p in resolved
        ],
        drops={t: [context.engine.players[p].name for p in ids] for t, ids in after.drops.items()},
        decision=dict(delta=delta, delta_without_spillover=sensitivity_delta, basis="trade_only"),
        input_sha256=hashlib.sha256(
            json.dumps(bundle, sort_keys=True, default=str).encode()
        ).hexdigest(),
        as_of=context.as_of.isoformat(),
        verdict=verdict,
        conditions=[
            "Üç takım aynı anda değiştirilir; zorunlu bırakmaların maliyeti dahildir.",
            "Üçlü analiz saf takası değerlendirir; FA/streaming ve playoff katılım etkisi bu sonuca dahil değildir.",
            "Takasın Yahoo üzerinde uygulanabilirliği ve lig kuralları ayrıca doğrulanmalıdır.",
        ]
        + context.warnings,
    )


def render_multiteam_report(result):
    names = result["team_names"]
    lines = [
        "# Üç takımlı takas analizi",
        "",
        "| Oyuncu | Veren takım | Alan takım |",
        "|---|---|---|",
    ]
    for move in result["transfers"]:
        lines.append(
            f"| {move['name']} | {names.get(move['from_team'], move['from_team'])} | {names.get(move['to_team'], move['to_team'])} |"
        )
    for team, values in result["teams"].items():
        total = values["all_supplied_weeks"]
        lines.extend(
            [
                "",
                "## " + names.get(team, team),
                "",
                f"Muhafazakâr Δ: {values['conservative_delta']:+.3f}; normal Δ: {total['delta']:+.3f}; sakatlık dağılımı kapalı Δ: {values['without_spillover_delta']:+.3f}",
                "",
                "| Kategori | Önce kazanma | Sonra kazanma | Δ kategori puanı |",
                "|---|---:|---:|---:|",
            ]
        )
        for cat, row in total["categories"].items():
            lines.append(
                f"| {cat} | {row['before_win']:.1%} | {row['after_win']:.1%} | {row['delta_points']:+.3f} |"
            )
        if result["drops"].get(team):
            lines.append("Bırakılan: " + ", ".join(result["drops"][team]))
    lines.extend(["", "## Koşullar", ""] + ["- " + text for text in result["conditions"]])
    return "\n".join(lines) + "\n"

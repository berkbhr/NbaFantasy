"""Legal roster branches for uneven trades, explicit IL assignment and one pickup."""

import copy
from dataclasses import dataclass, field
from datetime import timedelta
from itertools import combinations, product

from .matchup_engine import MAX_ROSTER_SIZE


@dataclass
class RosterScenario:
    rosters: dict
    stashed: set
    drops: dict = field(default_factory=dict)
    adds: dict = field(default_factory=dict)
    starts: dict = field(default_factory=dict)
    ends: dict = field(default_factory=dict)
    transactions: list = field(default_factory=list)

    def projection_roster(self, team):
        # A pickup later in the week keeps the displaced player until the day before it.
        return self.rosters[team] + [p for p in self.drops.get(team, []) if p in self.ends]


def validate_scenario(scenario, players):
    seen = set()
    for roster in scenario.rosters.values():
        ids = set(roster)
        if len(ids) != len(roster) or ids & seen or not ids <= players.keys():
            raise ValueError("Roster scenario has duplicate, multiply owned or unknown players")
        seen |= ids
        if len(ids & scenario.stashed) > 2 or len(ids - scenario.stashed) > MAX_ROSTER_SIZE:
            raise ValueError("Roster scenario exceeds active/bench or IL capacity")
    if not scenario.stashed <= seen:
        raise ValueError("IL assignment refers to an unowned player")


def drop_protection(context, bundle):
    return context.protected_drop_ids | {
        context.yahoo_ids[str(i)] for i in bundle.get("do_not_drop_yahoo_ids", [])
    }


def trade_packages(context, bundle, outgoing, incoming):
    """Enumerate required single drops; no hypothetical IL or waiver ownership."""
    mine, partner = str(bundle["proposal"]["our_team"]), str(bundle["proposal"]["other_team"])
    rosters = copy.deepcopy(context.rosters)
    rosters[mine] = [p for p in rosters[mine] if p not in outgoing] + incoming
    rosters[partner] = [p for p in rosters[partner] if p not in incoming] + outgoing
    stashed = trade_il_assignments(
        context, bundle, rosters, set(outgoing + incoming), {mine, partner}
    )
    protected = drop_protection(context, bundle)
    manual = bundle.get("drop_yahoo_ids", {})
    if set(manual) - {mine, partner}:
        raise ValueError("Drop instructions may only change the two trade teams")
    choices = {}
    for team in (mine, partner):
        active = set(rosters[team]) - stashed
        needed = max(0, len(active) - MAX_ROSTER_SIZE)
        if team in manual:
            ids = [context.yahoo_ids[str(i)] for i in manual[team]]
            if (
                len(ids) != len(set(ids))
                or len(ids) != needed
                or not set(ids) <= active - protected
            ):
                raise ValueError(
                    "Explicit drops must match required capacity and respect protection"
                )
            choices[team] = [tuple(ids)]
        elif needed > 1:
            raise ValueError("Multiple required drops need explicit drop_yahoo_ids")
        else:
            choices[team] = list(combinations(sorted(active - protected), needed))
        if not choices[team]:
            raise ValueError("No legal drop available without releasing a protected player")
    automatic = [t for t in (mine, partner) if len(choices[t]) > 1]
    if len(automatic) > 1:
        raise ValueError("Both teams need drops: specify at least one team's drop_yahoo_ids")
    scenarios = []
    for a, b in product(choices[mine], choices[partner]):
        drops = {mine: list(a), partner: list(b)}
        scenario = RosterScenario(
            {t: [p for p in ids if p not in drops.get(t, [])] for t, ids in rosters.items()},
            set(stashed),
            drops,
        )
        validate_scenario(scenario, context.engine.players)
        scenarios.append(scenario)
    return scenarios, automatic[0] if automatic else mine


def trade_il_assignments(context, bundle, rosters, traded, participants):
    """Explicit destination slots shared by bilateral and three-team trades."""
    original_stashes = set(context.engine.yahoo_already_stashed_ids)
    assignments = bundle.get("post_trade_il_yahoo_ids", {})
    if set(assignments) - participants:
        raise ValueError("Post-trade IL assignments may only change participating teams")
    traded_stashes = original_stashes & traded
    if traded_stashes and not participants <= assignments.keys():
        raise ValueError(
            "Trading IL players requires explicit post_trade_il_yahoo_ids for all participants"
        )
    stashed = original_stashes - traded
    for team in assignments:
        stashed -= set(context.rosters[team])
    for team, yahoo_ids in assignments.items():
        ids = [context.yahoo_ids[str(i)] for i in yahoo_ids]
        if len(ids) != len(set(ids)) or not set(ids) <= set(rosters[team]):
            raise ValueError("Invalid or unowned post-trade IL player")
        allowed = context.il_eligible_ids | (original_stashes & set(context.rosters[team]))
        if not set(ids) <= allowed or len(ids) > 2:
            raise ValueError(
                "New IL assignments need positive Yahoo eligibility and free IL capacity"
            )
        stashed |= set(ids)
    return stashed


def with_pickup(scenario, team, pid, when, drop=None, status="FA"):
    if any(pid in ids for ids in scenario.rosters.values()):
        raise ValueError("Pickup player is already owned")
    if (
        pid in scenario.starts
        or pid in scenario.ends
        or any(pid in ids for ids in scenario.drops.values())
    ):
        raise ValueError("Reacquisition of a released player is not supported in this horizon")
    if drop is not None and (drop not in scenario.rosters[team] or drop in scenario.stashed):
        raise ValueError("Drop must be an active/bench player owned by the acting team")
    when_text = when.date().isoformat()
    prior = [a for a in scenario.transactions if a.get("team", team) == team]
    if prior and when_text <= prior[-1]["date"]:
        raise ValueError("Pickups must be chronological, at most one per team per day")
    # Player IDs and calendar timestamps are immutable. Copy ownership
    # containers directly instead of recursively visiting all 14 rosters for
    # every beam branch; action metadata still receives an independent copy.
    result = RosterScenario(
        {owner: list(ids) for owner, ids in scenario.rosters.items()},
        set(scenario.stashed),
        {owner: list(ids) for owner, ids in scenario.drops.items()},
        copy.deepcopy(scenario.adds),
        dict(scenario.starts),
        dict(scenario.ends),
        copy.deepcopy(scenario.transactions),
    )
    if drop is not None:
        result.rosters[team].remove(drop)
        result.drops.setdefault(team, []).append(drop)
        result.ends[drop] = when - timedelta(days=1)
    result.rosters[team].append(pid)
    result.starts[pid] = when
    result.adds[team] = {"player_id": pid, "date": when_text, "status": status}
    result.transactions.append({"team": team, "date": when_text, "add_id": pid, "drop_id": drop})
    return result

"""Reversible, budget-constrained teammate absence adjustments.

This is a role heuristic. Minute budgets and caps are explicit; it is not a
fitted causal model of coaching decisions. Unobserved rotation minutes remain
unallocated rather than being assigned to unproven players.
"""

try:
    from .rotation_policy import RotationPolicy
except ImportError:
    from rotation_policy import RotationPolicy


def position_buckets(position):
    value = str(position).upper()
    return {p for p in ("G", "F", "C") if p in value} or {"G", "F", "C"}


def adjust_rotations(
    players,
    team_map,
    positions,
    enabled=True,
    game_date=None,
    as_of_date=None,
    low_role_boost_cap=None,
    policy=None,
):
    policy = policy or RotationPolicy()
    if low_role_boost_cap is not None and not 0 <= low_role_boost_cap <= 10:
        raise ValueError("Experimental low-role boost cap must be in [0,10]")
    teams = {}
    for pid, player in players.items():
        player.expected_minutes = float(player.base_expected_minutes)
        player.minutes_var = float(player.base_minutes_var)
        tid = team_map.get(pid)
        if tid and tid > 0:
            teams.setdefault(tid, []).append(pid)
    summaries = []
    if not enabled:
        return summaries
    for tid, ids in teams.items():
        avail = {
            i: players[i].get_effective_game_availability(
                game_date=game_date, as_of_date=as_of_date
            )
            for i in ids
        }
        base = {i: players[i].base_expected_minutes for i in ids}
        delta = dict.fromkeys(ids, 0.0)
        sources = {i: [] for i in ids}
        for missing in ids:
            player = players[missing]
            if player.injury_status in ("HEALTHY", "AVAILABLE", "ACTIVE", "PROBABLE", ""):
                continue
            absent = 1 - avail[missing]
            remaining = base[missing] * absent
            candidates = []
            for ben in ids:
                if ben == missing or avail[ben] <= 0 or players[ben].prior_min < 40:
                    continue
                # A recently observed role already includes some teammate absence.
                embedded = getattr(players[ben], "baseline_absences", {}).get(missing, 0.0)
                new_absence = max(0.0, absent - embedded)
                if new_absence == 0:
                    continue
                own_pos, lost_pos = (
                    position_buckets(positions.get(ben)),
                    position_buckets(positions.get(missing)),
                )
                affinity = (
                    1.0 if own_pos & lost_pos else (0.55 if "F" in own_pos | lost_pos else 0.15)
                )
                weight = max(1.0, base[ben]) * affinity * new_absence
                ceiling = max(
                    base[ben], 35.5 if base[ben] >= 26 else (31.0 if base[ben] >= 20 else 25.0)
                )
                # The legacy +2 rule is an explicit experimental alternative,
                # not a calibrated physical ceiling. None preserves the current
                # engine. Any cap is cumulative across all missing teammates.
                beneficiary = players[ben]
                observed_gp = int(getattr(beneficiary, "current_season_gp", 0) or 0)
                observed_mpg = float(getattr(beneficiary, "current_season_mpg", base[ben]))
                boost_limit = (
                    low_role_boost_cap
                    if low_role_boost_cap is not None and observed_gp >= 2 and observed_mpg < 10.0
                    else 10.0
                )
                headroom = max(0.0, min(boost_limit, ceiling - base[ben]) - delta[ben])
                candidates.append([ben, weight, headroom])
            # Allocate expected minutes (availability * conditional minutes).
            # Cap the pool to novel absence so observed expansions aren't duplicated.
            if candidates:
                novel = max(
                    max(0.0, absent - getattr(players[b], "baseline_absences", {}).get(missing, 0))
                    for b, _, _ in candidates
                )
                remaining = min(remaining, base[missing] * novel)
            remaining *= policy.redistribution_fraction
            while remaining > 1e-8:
                active = [row for row in candidates if row[2] > 1e-8]
                if not active:
                    break
                total_weight = sum(row[1] for row in active)
                used = 0.0
                for row in active:
                    ben, weight, room = row
                    expected_gain = min(remaining * weight / total_weight, room * avail[ben])
                    gain = expected_gain / avail[ben]
                    delta[ben] += gain
                    row[2] -= gain
                    used += expected_gain
                    if gain > 0 and player.name not in sources[ben]:
                        sources[ben].append(player.name)
                remaining -= used
                if used <= 1e-10:
                    break
        for pid in ids:
            delta[pid] *= policy.evidence_factor(players[pid])
        expected_total = sum(avail[i] * (base[i] + delta[i]) for i in ids)
        scale = min(1.0, 240.0 / expected_total) if expected_total > 0 else 1.0
        for pid in ids:
            bp = players[pid]
            new_minutes = (base[pid] + delta[pid]) * scale
            bp.expected_minutes = new_minutes
            bp.minutes_var = (
                min(144.0, bp.base_minutes_var + 0.35 * delta[pid] ** 2)
                * policy.minute_variance_scale
            )
            if delta[pid] > 0:
                summaries.append(
                    {
                        "player_id": pid,
                        "player_name": bp.name,
                        "team_id": tid,
                        "base_minutes": base[pid],
                        "projected_minutes": new_minutes,
                        "minute_boost": new_minutes - base[pid],
                        "injured_teammates": sources[pid],
                        "depth_rank": 0,
                        "is_transfer": False,
                    }
                )
    return sorted(summaries, key=lambda row: row["minute_boost"], reverse=True)

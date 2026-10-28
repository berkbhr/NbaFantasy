"""Weekly distributions and category-point decisions for NBA Fantasy."""

import math
from contextlib import contextmanager
from functools import lru_cache, wraps
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

try:
    from .probability import (
        CategoryProbabilities,
        decision_value,
        matchup_outcome,
        normal_category,
        utility_gradient,
    )
    from .rotation import adjust_rotations, position_buckets
except ImportError:  # Direct script entry points.
    from probability import (
        CategoryProbabilities,
        decision_value,
        matchup_outcome,
        normal_category,
        utility_gradient,
    )
    from rotation import adjust_rotations, position_buckets

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
COUNT_STATS = ["PTS", "REB", "AST", "STL", "BLK", "TOV", "FG3M"]
PERCENTAGE_STATS = ["FG", "FT"]
ALL_CATEGORIES = COUNT_STATS + ["FGM", "FGA", "FTM", "FTA"]
REQUIRED_SLOTS = ["PG", "SG", "G", "SF", "PF", "F", "C", "C", "UTIL", "UTIL"]
MAX_ROSTER_SIZE = 13
INFEASIBLE_COST = 1e9
# Neutral defaults. Fitted scale factors belong in an out-of-sample calibration
# artifact, not hand-set constants described as empirical calibration.
WEEKLY_VAR_INFLATION_BY_CAT = dict.fromkeys(COUNT_STATS + PERCENTAGE_STATS, 1.0)


def cached_projection(method):
    """Reuse immutable daily player moments only within a single decision call."""

    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self.projection_session():
            return method(self, *args, **kwargs)

    return wrapped


def norm_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def norm_pdf(z):
    return math.exp(-z * z / 2) / math.sqrt(2 * math.pi)


@lru_cache(maxsize=2048)
def map_position_to_slots(pos_str):
    """Respect exact Yahoo positions; broad NBA G/F positions are a fallback."""
    slots = {"UTIL"}
    tokens = str(pos_str).upper().replace("/", ",").replace("-", ",").split(",")
    mapping = {
        "PG": {"PG", "G"},
        "SG": {"SG", "G"},
        "SF": {"SF", "F"},
        "PF": {"PF", "F"},
        "C": {"C"},
        "CENTER": {"C"},
        "G": {"PG", "SG", "G"},
        "GUARD": {"PG", "SG", "G"},
        "F": {"SF", "PF", "F"},
        "FORWARD": {"SF", "PF", "F"},
    }
    for token in tokens:
        slots.update(mapping.get(token.strip(), set()))
    return tuple(sorted(slots))


@lru_cache(maxsize=2048)
def _slot_eligibility_mask(pos_str):
    eligible = map_position_to_slots(pos_str)
    return tuple(slot in eligible for slot in REQUIRED_SLOTS)


@lru_cache(maxsize=8192)
def can_fill_roster_cached(pos_tuple):
    if len(pos_tuple) > MAX_ROSTER_SIZE:
        return False
    if not pos_tuple:
        return True
    costs = np.array(
        [[-1 if ok else INFEASIBLE_COST for ok in _slot_eligibility_mask(p)] for p in pos_tuple]
    )
    rows, cols = linear_sum_assignment(costs)
    return int(np.sum(costs[rows, cols] < 0)) >= min(len(pos_tuple), len(REQUIRED_SLOTS))


def can_fill_roster(players):
    return can_fill_roster_cached(tuple(sorted(p.get("POS", "UTIL") for p in players)))


def get_optimal_daily_lineup(available_players, category_weights, p_ref_fg=0.47, p_ref_ft=0.78):
    """Exact assignment for a linear surrogate, including empty active slots.

    The nonlinear weekly objective is handled by matchup-specific weights and
    candidate re-evaluation. Assignment alone is not a global weekly optimizer.
    """
    if not available_players:
        return []
    n, k = len(available_players), len(REQUIRED_SLOTS)
    costs = np.full((n + k, k), INFEASIBLE_COST)
    costs[n:] = 0  # Dummy players mean voluntarily leaving slots empty.
    for i, player in enumerate(available_players):
        proj, value = player.get("PROJ", {}), 0.0
        for stat, weight in category_weights.items():
            if stat == "TOV":
                value -= weight * proj.get(stat, 0)
            elif stat in ("FG", "FT", "FG_PCT", "FT_PCT"):
                s = stat[:2]
                ref = p_ref_fg if s == "FG" else p_ref_ft
                value += weight * (proj.get(s + "M", 0) - ref * proj.get(s + "A", 0))
            else:
                value += weight * proj.get(stat, 0)
        for j, eligible in enumerate(_slot_eligibility_mask(player.get("POS", "UTIL"))):
            if eligible:
                costs[i, j] = -value
    rows, cols = linear_sum_assignment(costs)
    return [available_players[r] for r, c in zip(rows, cols) if r < n and costs[r, c] < -1e-14]


class MatchupEngine:
    def __init__(
        self,
        bayesian_players_dict,
        df_schedule,
        df_positions,
        season="2026_27",
        prior_season="2025_26",
        free_agent_pool=None,
        num_il_slots=2,
        max_weekly_adds=3,
        il_eligible_statuses=("OUT", "INJ", "O", "IL"),
        yahoo_il_eligible_ids=None,
        consec_dnp_limit=None,
        availability_weighted_lineup=True,
        availability_weighted_draft_lineup=True,
        use_dynamic_add_drop=True,
        use_positional_depth_and_injury_boost=False,
        draw_value=0.5,
        availability_correlation=0.0,
        team_map=None,
        protected_player_ids=None,
        objective="category_points",
        low_role_boost_cap=None,
        rotation_policy=None,
    ):
        self.players = bayesian_players_dict
        self.schedule = df_schedule.copy() if df_schedule is not None else pd.DataFrame()
        if not self.schedule.empty:
            self.schedule["GAME_DATE"] = pd.to_datetime(self.schedule["GAME_DATE"]).dt.normalize()
        self._team_games = {}
        self._all_schedule_dates = {}
        if not self.schedule.empty:
            for row in self.schedule.to_dict("records"):
                self._team_games.setdefault(row["TEAM_ID"], []).append(
                    (row["GAME_DATE"], str(row.get("GAME_ID", "")))
                )
                self._all_schedule_dates.setdefault(row["TEAM_ID"], set()).add(row["GAME_DATE"])
        self.pos_dict = (
            df_positions.set_index("PLAYER_ID")["POSITION"].to_dict()
            if df_positions is not None and not df_positions.empty and "PLAYER_ID" in df_positions
            else (
                df_positions["POSITION"].to_dict()
                if df_positions is not None and not df_positions.empty
                else {}
            )
        )
        self.season, self.prior_season = season, prior_season
        self.num_il_slots, self.max_weekly_adds = int(num_il_slots), int(max_weekly_adds)
        self.free_agent_pool = list(free_agent_pool or [])  # Candidates only; never silently added.
        self.il_eligible_statuses = set(il_eligible_statuses)
        self.yahoo_il_eligible_ids = (
            None if yahoo_il_eligible_ids is None else set(yahoo_il_eligible_ids)
        )
        self.yahoo_already_stashed_ids = set()
        self.completed_game_ids = set()
        self.protected_player_ids = set(protected_player_ids or [])
        self.consec_dnp_limit = consec_dnp_limit  # Explicit optional exclusion, off by default.
        self.availability_weighted_lineup = availability_weighted_lineup
        self.availability_weighted_draft_lineup = availability_weighted_draft_lineup
        self.use_dynamic_add_drop = use_dynamic_add_drop
        self.use_positional_depth_and_injury_boost = use_positional_depth_and_injury_boost
        self.low_role_boost_cap = low_role_boost_cap
        try:
            from .rotation_policy import load_rotation_policy
        except ImportError:
            from rotation_policy import load_rotation_policy
        self.rotation_policy = rotation_policy or load_rotation_policy()
        if not 0 <= draw_value <= 1 or not 0 <= availability_correlation <= 1:
            raise ValueError("Invalid utility/availability configuration")
        self.draw_value, self.availability_correlation = draw_value, availability_correlation
        decision_value(CategoryProbabilities(), objective, draw_value)
        self.objective = objective
        self.prior_team_map = {}
        self.team_map = self._load_team_map() if team_map is None else dict(team_map)
        self.default_norm_weights = self._compute_pool_unit_weights()
        self.last_injury_boost_summary = []
        self._projection_cache = None

    @contextmanager
    def projection_session(self):
        if self._projection_cache is not None:
            yield
            return
        self._projection_cache = {}
        try:
            yield
        finally:
            self._projection_cache = None
            self.recompute_team_depth_and_injury_minutes()

    def _daily_projections(self, day, as_of, live, eligible):
        key = (
            day,
            as_of,
            live,
            self.rotation_policy,
            self.low_role_boost_cap,
            self.use_positional_depth_and_injury_boost,
        )
        if self._projection_cache is not None and key in self._projection_cache:
            return self._projection_cache[key]
        self.recompute_team_depth_and_injury_minutes(live, game_date=day, as_of_date=as_of)
        # Counterfactuals share NBA roles, even when fantasy ownership changes.
        ids = self.players if self._projection_cache is not None else eligible
        result = {pid: self._build_player_game_projection(pid, current_date=as_of) for pid in ids}
        if self._projection_cache is not None:
            self._projection_cache[key] = result
        return result

    def _load_team_map(self):
        """Prior-season teams only; live roster/observed games must explicitly override.

        Do not peek at the target season's first future appearance in backtests.
        """
        path = DATA_DIR / "raw" / f"player_logs_{self.prior_season}.parquet"
        if path.exists():
            df = pd.read_parquet(path, columns=["PLAYER_ID", "TEAM_ID", "GAME_DATE"]).sort_values(
                "GAME_DATE"
            )
            self.prior_team_map = {
                int(k): int(v)
                for k, v in df.drop_duplicates("PLAYER_ID", keep="last")
                .set_index("PLAYER_ID")["TEAM_ID"]
                .to_dict()
                .items()
            }
        mapping = dict(self.prior_team_map)
        # This snapshot is valid only for the live 2026-27 season.
        roster = DATA_DIR / "processed" / "active_roster_2026_27.parquet"
        if self.season == "2026_27" and roster.exists():
            df = pd.read_parquet(roster)
            mapping.update(
                {
                    int(k): int(v)
                    for k, v in df[df.TEAM_ID > 0]
                    .set_index("PLAYER_ID")["TEAM_ID"]
                    .to_dict()
                    .items()
                }
            )
        return mapping

    def _compute_pool_unit_weights(self):
        values = {s: [] for s in COUNT_STATS + PERCENTAGE_STATS}
        for bp in self.players.values():
            prediction = bp.predict_next_game()
            for s in COUNT_STATS:
                values[s].append(prediction[s]["mean"])
            for s, ref in [("FG", 0.47), ("FT", 0.78)]:
                values[s].append(prediction[s]["mean"] - ref * prediction[s]["attempts"])
        return {s: 1 / max(float(np.std(v)) if v else 1, 0.25) for s, v in values.items()}

    _extract_primary_pos_buckets = staticmethod(position_buckets)

    def recompute_team_depth_and_injury_minutes(
        self, use_live_injuries=True, game_date=None, as_of_date=None
    ):
        self.last_injury_boost_summary = adjust_rotations(
            self.players,
            self.team_map,
            self.pos_dict,
            enabled=self.use_positional_depth_and_injury_boost and use_live_injuries,
            game_date=game_date,
            as_of_date=as_of_date,
            low_role_boost_cap=self.low_role_boost_cap,
            policy=self.rotation_policy,
        )
        return self.last_injury_boost_summary

    def _get_player_schedule(self, team_id, start_date, end_date):
        if self.schedule.empty or team_id is None:
            return set()
        start, end = pd.Timestamp(start_date), pd.Timestamp(end_date)
        return {
            day
            for day, gid in self._team_games.get(team_id, [])
            if start <= day <= end and gid not in self.completed_game_ids
        }

    def _build_player_game_projection(self, pid, target_minutes=None, current_date=None):
        prediction = self.players[pid].predict_next_game(
            projected_minutes=target_minutes, current_date=current_date
        )
        means = {s: prediction[s]["mean"] for s in COUNT_STATS}
        means["MIN"] = prediction["MIN"]["mean"]
        variances = {s: prediction[s]["variance"] for s in COUNT_STATS}
        for s in COUNT_STATS:
            variances[s + "_shared"] = prediction[s]["shared_covariance"]
        for s in PERCENTAGE_STATS:
            p = prediction[s]
            means.update({s + "M": p["mean"], s + "A": p["attempts"], s + "_rate": p["rate"]})
            variances.update(
                {
                    s + "M": p["variance"],
                    s + "A": p["attempts_var"],
                    s + "M_cond": p["cond_variance"],
                    s + "_rate": p["rate_variance"],
                    s + "A_shared": p["shared_attempts_covariance"],
                    s + "M_shared": p["shared_covariance"],
                }
            )
        return means, variances

    @staticmethod
    def _player_value(p, category_weights, p_ref_fg=0.47, p_ref_ft=0.78):
        proj = p["PROJ"]
        value = sum(
            (-1 if s == "TOV" else 1) * proj.get(s, 0) * category_weights.get(s, 0)
            for s in COUNT_STATS
        )
        for s, ref in [("FG", p_ref_fg), ("FT", p_ref_ft)]:
            value += (proj.get(s + "M", 0) - ref * proj.get(s + "A", 0)) * category_weights.get(
                s, category_weights.get(s + "_PCT", 0)
            )
        return value

    def _is_il_eligible(self, p):
        pid = p["ID"]
        if pid in self.yahoo_already_stashed_ids:
            return True
        if self.yahoo_il_eligible_ids is not None:
            return pid in self.yahoo_il_eligible_ids
        return self.players[pid].injury_status in self.il_eligible_statuses

    def _make_entry(self, pid, ref_date, start_date, end_date, dates, avail, streamer=False):
        day = pd.Timestamp(ref_date).normalize() if ref_date is not None else None
        means, variances = self._daily_projections(day, day, True, [pid])[pid]
        return {
            "ID": pid,
            "POS": self.pos_dict.get(pid, "UTIL"),
            "PROJ": means,
            "VAR": variances,
            "AVAIL": avail,
            "SCHEDULE": self._get_player_schedule(self.team_map.get(pid), start_date, end_date)
            if len(dates)
            else set(),
        }

    def get_expected_weekly_distribution(
        self,
        roster_ids,
        start_date=None,
        end_date=None,
        category_weights=None,
        use_live_injuries=True,
        player_start_dates=None,
        p_ref_fg=0.47,
        p_ref_ft=0.78,
        as_of_date=None,
    ):
        """Project only the supplied roster; no hypothetical free-agent ownership.

        Game-specific moments retain shared posterior-rate uncertainty across a
        player's games. The optional availability correlation is a sensitivity
        assumption, independent by default until fitted injury histories exist.
        """
        roster_ids = sorted(set(roster_ids), key=str)
        dated = start_date is not None and end_date is not None and not self.schedule.empty
        dates = list(pd.date_range(start_date, end_date)) if dated else [None]
        if (
            start_date is not None
            and end_date is not None
            and pd.Timestamp(end_date) < pd.Timestamp(start_date)
        ):
            dates = []
        as_of = (
            pd.Timestamp(as_of_date or start_date).normalize()
            if as_of_date is not None or start_date is not None
            else None
        )
        weights = self.default_norm_weights if category_weights is None else category_weights
        eligible = [pid for pid in roster_ids if pid in self.players]
        # Actual Yahoo stashes are binding, including returning GTD players.
        actual_stashes = [pid for pid in eligible if pid in self.yahoo_already_stashed_ids]
        inferred = (
            [
                pid
                for pid in eligible
                if pid not in actual_stashes
                and self._is_il_eligible({"ID": pid})
                and self.players[pid].get_effective_game_availability() == 0
                and not self.players[pid].expected_return
            ]
            if use_live_injuries
            else []
        )
        stashed = (
            actual_stashes
            + sorted(inferred, key=lambda i: -self.players[i].base_expected_minutes)[
                : max(0, self.num_il_slots - len(actual_stashes))
            ]
        )
        excluded = {
            pid
            for pid in eligible
            if use_live_injuries
            and self.consec_dnp_limit is not None
            and self.players[pid].consecutive_dnps >= self.consec_dnp_limit
        }
        starts = {pid: [] for pid in eligible}
        lineup_meta = {}
        for day in dates:
            daily_projections = self._daily_projections(day, as_of, use_live_injuries, eligible)
            candidates = []
            for pid in eligible:
                if pid in stashed or pid in excluded:
                    continue
                if dated:
                    if (
                        player_start_dates
                        and pid in player_start_dates
                        and day < pd.Timestamp(player_start_dates[pid])
                    ):
                        continue
                    team_schedule = self._get_player_schedule(
                        self.team_map.get(pid), day - pd.Timedelta(days=1), end_date
                    )
                    if day not in team_schedule:
                        continue
                    # Completed yesterday games still matter for B2B rest.
                    b2b = day - pd.Timedelta(days=1) in self._all_schedule_dates.get(
                        self.team_map.get(pid), set()
                    )
                else:
                    b2b = False
                bp = self.players[pid]
                avail = (
                    bp.get_effective_game_availability(is_b2b=b2b, game_date=day, as_of_date=as_of)
                    if use_live_injuries
                    else bp.availability_rate
                )
                if avail <= 0:
                    continue
                # Forecast rates at decision time, not with hindsight on game day.
                means, variances = daily_projections[pid]
                weighted = (
                    self.availability_weighted_lineup
                    if dated
                    else self.availability_weighted_draft_lineup
                )
                score_projection = {
                    s: v * avail if s in ALL_CATEGORIES and weighted else v
                    for s, v in means.items()
                }
                candidates.append(
                    {
                        "ID": pid,
                        "POS": self.pos_dict.get(pid, "UTIL"),
                        "PROJ": score_projection,
                        "RAW": means,
                        "VAR": variances,
                        "AVAIL": avail,
                    }
                )
            selected = get_optimal_daily_lineup(candidates, weights, p_ref_fg, p_ref_ft)
            lineup_meta[str(day.date()) if day is not None else "undated"] = [
                p["ID"] for p in selected
            ]
            if dated:
                for p in selected:
                    starts[p["ID"]].append((1.0, p["AVAIL"], p["RAW"], p["VAR"]))
            else:
                # Explicit draft-only fallback, not a real calendar forecast.
                selected_ids = {p["ID"] for p in selected}
                for p in candidates:
                    games = 3.35 if p["ID"] in selected_ids else 2.35
                    # Non-positive surrogate value players may be sat for the week.
                    if self._player_value(p, weights, p_ref_fg, p_ref_ft) > 0:
                        starts[p["ID"]].append((games, p["AVAIL"], p["RAW"], p["VAR"]))
        mean = dict.fromkeys(ALL_CATEGORIES, 0.0)
        var = dict.fromkeys(ALL_CATEGORIES + ["FGM_cond", "FTM_cond"], 0.0)
        breakdown = []
        for pid, games in starts.items():
            if not games:
                continue
            # Retain per-game means/variances, since projected recovery changes roles.
            records = []
            for repetitions, prob, mu, vv in games:
                for cat in ALL_CATEGORIES:
                    mean[cat] += repetitions * prob * mu[cat]
                    var[cat] += repetitions * (prob * vv[cat] + prob * (1 - prob) * mu[cat] ** 2)
                for s in PERCENTAGE_STATS:
                    var[s + "M_cond"] += repetitions * prob * vv[s + "M_cond"]
                records.append({"g": repetitions, "p": prob, "mean": mu, "var": vv})
            # For undated fractional games, pair coefficient g(g-1); dated
            # pair coefficient includes both orderings i,j.
            for i, a in enumerate(records):
                for j, b in enumerate(records[i:], start=i):
                    pairs = a["g"] * (a["g"] - 1) if i == j else 2 * a["g"] * b["g"]
                    if pairs <= 0:
                        continue
                    pa, pb = a["p"], b["p"]
                    cov_play = self.availability_correlation * math.sqrt(
                        pa * (1 - pa) * pb * (1 - pb)
                    )
                    cov_play = min(cov_play, min(pa, pb) - pa * pb)
                    joint = pa * pb + cov_play
                    for cat in ALL_CATEGORIES:
                        shared = math.sqrt(
                            a["var"].get(cat + "_shared", 0) * b["var"].get(cat + "_shared", 0)
                        )
                        var[cat] += pairs * (
                            joint * shared + cov_play * a["mean"][cat] * b["mean"][cat]
                        )
            breakdown.append({"id": pid, "games": records})
        return {
            "mean": mean,
            "var": var,
            "players": breakdown,
            "meta": {
                "il_stashed_ids": stashed,
                "il_unverified_ids": inferred if self.yahoo_il_eligible_ids is None else [],
                "streamer_ids": [],
                "dnp_excluded_ids": sorted(excluded, key=str),
                "lineups": lineup_meta,
                "schedule_mode": "dated" if dated else "draft_fallback",
                "availability_correlation": self.availability_correlation,
            },
        }

    def get_expected_weekly_stats(
        self, roster_ids, start_date=None, end_date=None, category_weights=None
    ):
        return self.get_expected_weekly_distribution(
            roster_ids, start_date, end_date, category_weights
        )["mean"]

    @staticmethod
    def _compute_team_pct_impact_var(dist, stat, p_ref):
        """Var(makes - ref * attempts) for future games, at player resolution."""
        players = dist.get("players", [])
        if not players:
            vv = dist["var"]
            a = dist["mean"].get(stat + "A", 0)
            p = dist["mean"].get(stat + "M", 0) / a if a else p_ref
            # Preserve explicit makes/attempts covariance when supplied.
            if stat + "_MA" in vv:
                return max(
                    0,
                    vv.get(stat + "M", 0)
                    + p_ref**2 * vv.get(stat + "A", 0)
                    - 2 * p_ref * vv[stat + "_MA"],
                )
            return vv.get(stat + "M_cond", vv.get(stat + "M", 0)) + (p - p_ref) ** 2 * vv.get(
                stat + "A", 0
            )
        total = 0.0
        rho = dist.get("meta", {}).get("availability_correlation", 0.0)
        for player in players:
            records = player["games"]
            for a in records:
                mu, vv, p, g = a["mean"], a["var"], a["p"], a["g"]
                rate, n = mu[stat + "_rate"], mu[stat + "A"]
                y = (rate - p_ref) * n
                total += g * (
                    p * (vv[stat + "M_cond"] + (rate - p_ref) ** 2 * vv[stat + "A"])
                    + p * (1 - p) * y * y
                )
            for i, a in enumerate(records):
                for j, b in enumerate(records[i:], start=i):
                    pairs = a["g"] * (a["g"] - 1) if i == j else 2 * a["g"] * b["g"]
                    if pairs <= 0:
                        continue
                    pa, pb = a["p"], b["p"]
                    cov_play = min(
                        rho * math.sqrt(pa * (1 - pa) * pb * (1 - pb)), min(pa, pb) - pa * pb
                    )
                    ra, rb = a["mean"][stat + "_rate"], b["mean"][stat + "_rate"]
                    na, nb = a["mean"][stat + "A"], b["mean"][stat + "A"]
                    cov_att = math.sqrt(a["var"][stat + "A_shared"] * b["var"][stat + "A_shared"])
                    var_rate = math.sqrt(a["var"][stat + "_rate"] * b["var"][stat + "_rate"])
                    shared = (na * nb + cov_att) * var_rate + (ra - p_ref) * (rb - p_ref) * cov_att
                    total += pairs * (
                        (pa * pb + cov_play) * shared
                        + cov_play * (ra - p_ref) * na * (rb - p_ref) * nb
                    )
        return max(0.0, total)

    @classmethod
    def evaluate_h2h_matchup(
        cls, my_dist, opp_dist, var_scale=1.0, draw_value=0.5, objective="category_points"
    ):
        """Category point expectation, W/L/T marginals, weekly-utility gradients.

        FG/FT use the delta-method variance of each team's own ratio, rather
        than comparing unweighted volume impacts across unequal denominators.
        """
        if var_scale <= 0:
            raise ValueError("var_scale must be positive")
        probabilities, moments = CategoryProbabilities(), {}
        for s in COUNT_STATS:
            diff = (my_dist["mean"].get(s, 0) - opp_dist["mean"].get(s, 0)) * (
                -1 if s == "TOV" else 1
            )
            variance = (my_dist["var"].get(s, 0) + opp_dist["var"].get(s, 0)) * var_scale
            probabilities[s], probabilities.ties[s] = normal_category(diff, variance, discrete=True)
            moments[s] = diff, variance, True, 1.0
        for s in PERCENTAGE_STATS:
            am, bm = my_dist["mean"].get(s + "A", 0), opp_dist["mean"].get(s + "A", 0)
            ap = my_dist["mean"].get(s + "M", 0) / am if am > 0 else 0.0
            bp = opp_dist["mean"].get(s + "M", 0) / bm if bm > 0 else 0.0
            variance = (
                (cls._compute_team_pct_impact_var(my_dist, s, ap) / am**2 if am > 0 else 0)
                + (cls._compute_team_pct_impact_var(opp_dist, s, bp) / bm**2 if bm > 0 else 0)
            ) * var_scale
            key = s + "_PCT"
            probabilities[key], probabilities.ties[key] = normal_category(ap - bp, variance)
            moments[key] = ap - bp, variance, False, (1 / am if am > 0 else 0)
        weights = {}
        for key, (diff, variance, discrete, scale) in moments.items():
            weights[key[:2] if key.endswith("_PCT") else key] = scale * utility_gradient(
                probabilities, key, diff, variance, discrete, draw_value, objective
            )
        expected_points = sum(probabilities[c] + 0.5 * probabilities.ties[c] for c in probabilities)
        return expected_points, probabilities, weights

    @staticmethod
    def compute_matchup_outcome(win_probs_dict, rho=0.0):
        return matchup_outcome(win_probs_dict, rho=rho)

    @staticmethod
    def compute_matchup_win_prob(win_probs_dict, rho=0.0):
        return matchup_outcome(win_probs_dict, rho=rho).win

    def matchup_utility(self, probabilities):
        """Selected decision objective; regular season uses category points."""
        return decision_value(probabilities, self.objective, self.draw_value)

    @cached_projection
    def project_matchup(
        self,
        my_ids,
        opp_ids,
        start_date=None,
        end_date=None,
        my_actual_stats=None,
        opp_actual_stats=None,
        my_rem_fraction=1.0,
        opp_rem_fraction=1.0,
        player_start_dates=None,
    ):
        """Two-pass lineup policy, retaining the best evaluated weekly utility.

        This is a bounded local heuristic, not proof of the global optimum.
        Opponent uses its default lineup policy; no imaginary acquisitions.
        """
        opp = self.combine_live_and_remaining_dist(
            opp_actual_stats,
            self.get_expected_weekly_distribution(opp_ids, start_date, end_date),
            opp_rem_fraction,
        )
        best = self.combine_live_and_remaining_dist(
            my_actual_stats,
            self.get_expected_weekly_distribution(
                my_ids, start_date, end_date, player_start_dates=player_start_dates
            ),
            my_rem_fraction,
        )
        score, probs, weights = self.evaluate_h2h_matchup(
            best, opp, draw_value=self.draw_value, objective=self.objective
        )
        utility = self.matchup_utility(probs)
        for _ in range(2):
            fg = best["mean"]["FGM"] / best["mean"]["FGA"] if best["mean"]["FGA"] else 0.47
            ft = best["mean"]["FTM"] / best["mean"]["FTA"] if best["mean"]["FTA"] else 0.78
            trial = self.combine_live_and_remaining_dist(
                my_actual_stats,
                self.get_expected_weekly_distribution(
                    my_ids,
                    start_date,
                    end_date,
                    category_weights=weights,
                    player_start_dates=player_start_dates,
                    p_ref_fg=fg,
                    p_ref_ft=ft,
                ),
                my_rem_fraction,
            )
            candidate_score, candidate_probs, candidate_weights = self.evaluate_h2h_matchup(
                trial, opp, draw_value=self.draw_value, objective=self.objective
            )
            candidate_utility = self.matchup_utility(candidate_probs)
            if candidate_utility <= utility + 1e-12:
                break
            best, score, probs, weights, utility = (
                trial,
                candidate_score,
                candidate_probs,
                candidate_weights,
                candidate_utility,
            )
        return best, opp, score, probs, weights

    def simulate_matchup(
        self, my_roster_ids, opp_roster_ids, start_date, end_date, n_iterations=None
    ):
        return self.project_matchup(my_roster_ids, opp_roster_ids, start_date, end_date)[3]

    @classmethod
    def combine_live_and_remaining_dist(cls, actual_stats, rem_dist, rem_fraction=1.0):
        """Realized stats are constants. Fractional fallback is approximate only.

        Fractional fallback scales moments linearly and cannot reconstruct
        calendar/covariance effects. It is flagged and should be avoided for
        live decisions; dated projections always use f=1.
        """
        f = float(rem_fraction)
        if not 0 <= f <= 1:
            raise ValueError("Remaining fraction must be in [0, 1]")
        actual = actual_stats or {}
        # Moment scaling alone cannot recover every covariance component in
        # legacy distributions; retain the linear fallback with an explicit flag.
        return {
            "mean": {
                c: float(actual.get(c, 0)) + f * float(rem_dist["mean"].get(c, 0))
                for c in ALL_CATEGORIES
            },
            "var": {c: f * float(v) for c, v in rem_dist["var"].items()},
            "players": rem_dist.get("players", []) if f == 1 else [],
            "meta": {**rem_dist.get("meta", {}), "fractional_approximation": f not in (0, 1)},
        }

    @staticmethod
    def category_diagnostics(my_dist, opp_dist, my_actual=None, opp_actual=None):
        """Expose the realized/future split without treating realized scores as uncertain."""
        a, b = my_actual or {}, opp_actual or {}
        return {
            cat: {
                "my_actual": float(a.get(cat, 0)),
                "opponent_actual": float(b.get(cat, 0)),
                "my_remaining_mean": float(my_dist["mean"].get(cat, 0)) - float(a.get(cat, 0)),
                "opponent_remaining_mean": float(opp_dist["mean"].get(cat, 0))
                - float(b.get(cat, 0)),
                "difference_sd": math.sqrt(
                    my_dist["var"].get(cat, 0) + opp_dist["var"].get(cat, 0)
                ),
            }
            for cat in COUNT_STATS
        }

    @staticmethod
    def _compute_cat_details(base, new):
        rows = []
        for c, p in new.items():
            delta = p - base.get(c, 0)
            if delta > 0.0001:
                rows.append(
                    {
                        "cat": c,
                        "base_pct": round(100 * base[c]),
                        "new_pct": round(100 * p),
                        "delta_pct": round(100 * delta, 2),
                        "is_flip": base[c] < 0.5 <= p,
                        "is_crit": 0.38 <= base[c] <= 0.62,
                        "score": delta,
                    }
                )
        return sorted(rows, key=lambda r: r["score"], reverse=True)

    @cached_projection
    def recommend_add_drop_moves(
        self,
        my_roster_ids,
        opp_roster_ids,
        candidate_fa_ids,
        start_date=None,
        end_date=None,
        my_actual_stats=None,
        opp_actual_stats=None,
        my_rem_fraction=1.0,
        opp_rem_fraction=1.0,
        top_k=5,
        waivers_dict=None,
        adds_used=0,
        protected_ids=None,
        opportunity_sensitivity=False,
    ):
        """Alternative moves ranked by category points (or explicit playoff objective).

        Core protection is a hard constraint. Explicit protected IDs take
        precedence; by default the top eleven baseline players are protected.
        Recommendations are alternatives, not a jointly executable multi-add plan.
        """
        if adds_used >= self.max_weekly_adds:
            return []
        kwargs = dict(
            start_date=start_date,
            end_date=end_date,
            my_actual_stats=my_actual_stats,
            opp_actual_stats=opp_actual_stats,
            my_rem_fraction=my_rem_fraction,
            opp_rem_fraction=opp_rem_fraction,
        )
        base, opp, base_points, probs, weights = self.project_matchup(
            my_roster_ids, opp_roster_ids, **kwargs
        )
        base_outcome = matchup_outcome(probs)
        base_utility = self.matchup_utility(probs)
        stashed = set(base["meta"]["il_stashed_ids"])
        active = [i for i in my_roster_ids if i in self.players and i not in stashed]
        # Baseline role value, not a one-week injury dip, determines protection.
        values = {}
        for pid in active:
            mu, _ = self._build_player_game_projection(
                pid, target_minutes=self.players[pid].base_expected_minutes
            )
            values[pid] = self._player_value({"PROJ": mu}, self.default_norm_weights)
        if protected_ids is None:
            protection = set(sorted(active, key=lambda i: (-values[i], str(i)))[:11])
        else:
            protection = set(protected_ids)
        protection |= self.protected_player_ids
        drops = [i for i in active if i not in protection]
        options = [None] if len(active) < MAX_ROSTER_SIZE else drops
        refs = {
            s: base["mean"][s + "M"] / base["mean"][s + "A"]
            if base["mean"][s + "A"]
            else (0.47 if s == "FG" else 0.78)
            for s in PERCENTAGE_STATS
        }
        dates = (
            list(pd.date_range(start_date, end_date))
            if start_date is not None and end_date is not None and not self.schedule.empty
            else []
        )
        # Shortlist is a speed approximation; every surviving move is re-evaluated.
        candidates = []
        for pid in sorted(
            set(candidate_fa_ids) - set(my_roster_ids) - set(opp_roster_ids), key=str
        ):
            if pid not in self.players:
                continue
            info = (waivers_dict or {}).get(pid)
            clear = info.get("date") if isinstance(info, dict) else info
            if info is not None and not clear:
                continue  # Waiver claim timing is unknown.
            effective = (
                max(pd.Timestamp(start_date), pd.Timestamp(clear))
                if clear and start_date is not None
                else start_date
            )
            if (
                effective is not None
                and end_date is not None
                and pd.Timestamp(effective) > pd.Timestamp(end_date)
            ):
                continue
            avail = self.players[pid].get_effective_game_availability(
                game_date=effective, as_of_date=start_date
            )
            if avail <= 0:
                continue
            entry = self._make_entry(pid, start_date, effective, end_date, dates, avail)
            games = len(entry["SCHEDULE"]) if dates else 3.35 * my_rem_fraction
            value = self._player_value(entry, weights, refs["FG"], refs["FT"]) * games * avail
            candidates.append((value, pid, info, clear, effective, games, avail, entry["PROJ"]))
        recommendations = []
        for _, pid, info, clear, effective, games, avail, projection in sorted(
            candidates, key=lambda x: (-x[0], str(x[1]))
        )[:25]:
            best = None
            for drop in options:
                roster = [i for i in my_roster_ids if i != drop] + [pid]
                trial, _, points, new_probs, _ = self.project_matchup(
                    roster,
                    opp_roster_ids,
                    player_start_dates={pid: effective} if effective is not None else None,
                    **kwargs,
                )
                outcome = matchup_outcome(new_probs)
                gain = self.matchup_utility(new_probs) - base_utility
                if gain <= 1e-10 or (best is not None and gain <= best["delta_objective_value"]):
                    continue
                details = self._compute_cat_details(probs, new_probs)
                pg = {
                    "PTS": projection["PTS"],
                    "REB": projection["REB"],
                    "AST": projection["AST"],
                    "STL": projection["STL"],
                    "BLK": projection["BLK"],
                    "3PT": projection["FG3M"],
                }
                best = {
                    "action": "ADD (Boş Yuva / IL+)" if drop is None else "ADD / DROP",
                    "add_id": pid,
                    "add_name": self.players[pid].name,
                    "drop_id": drop,
                    "drop_name": self.players[drop].name if drop is not None else "Boş Yuva",
                    "rem_games_add": games,
                    "rem_games_drop": len(
                        self._get_player_schedule(self.team_map.get(drop), start_date, end_date)
                    )
                    if drop is not None and dates
                    else (3.35 if drop is not None else 0),
                    "fa_avail": avail,
                    "observed_games": int(getattr(self.players[pid], "current_season_gp", 0)),
                    "observed_minutes": float(getattr(self.players[pid], "current_season_mpg", 0)),
                    "role_base_minutes": float(self.players[pid].base_expected_minutes),
                    "projected_minutes": float(projection["MIN"]),
                    "prior_role_minutes": float(
                        getattr(
                            self.players[pid],
                            "prior_expected_minutes",
                            self.players[pid].base_expected_minutes,
                        )
                    ),
                    "is_waiver": info is not None,
                    "waiver_clear_date": clear,
                    "waiver_display": info.get("display", "Waiver")
                    if isinstance(info, dict)
                    else str(clear or ""),
                    "base_expected_wins": base_points,
                    "new_expected_wins": points,
                    "delta_expected_wins": points - base_points,
                    "objective": self.objective,
                    "base_objective_value": base_utility,
                    "new_objective_value": self.matchup_utility(new_probs),
                    "delta_objective_value": gain,
                    "base_win_probability": base_outcome.win,
                    "new_win_probability": outcome.win,
                    "new_draw_probability": outcome.draw,
                    "cat_details": details,
                    "cat_gains": [(d["cat"], d["delta_pct"] / 100) for d in details[:2]],
                    "target_cats": [d["cat"] for d in details[:2]],
                    "key_cat_gains": ", ".join(
                        f"{d['cat']} (%{d['base_pct']} → %{d['new_pct']})" for d in details[:2]
                    )
                    or "Haftalık W/L/D",
                    "exp_stats_pg": {k: round(v, 1) for k, v in pg.items()},
                    "exp_stats": {k: round(v * games * avail, 1) for k, v in pg.items()},
                }
            if best:
                recommendations.append(best)
        if (
            opportunity_sensitivity
            and self.use_positional_depth_and_injury_boost
            and recommendations
        ):
            enabled = self.use_positional_depth_and_injury_boost
            try:
                self.use_positional_depth_and_injury_boost = False
                _, _, _, neutral_probs, _ = self.project_matchup(
                    my_roster_ids, opp_roster_ids, **kwargs
                )
                neutral_base = self.matchup_utility(neutral_probs)
                for row in recommendations:
                    roster = [i for i in my_roster_ids if i != row["drop_id"]] + [row["add_id"]]
                    effective = (
                        max(pd.Timestamp(start_date), pd.Timestamp(row["waiver_clear_date"]))
                        if row["waiver_clear_date"] and start_date is not None
                        else start_date
                    )
                    _, _, _, neutral_move, _ = self.project_matchup(
                        roster,
                        opp_roster_ids,
                        player_start_dates={row["add_id"]: effective}
                        if effective is not None
                        else None,
                        **kwargs,
                    )
                    row["delta_without_spillover"] = (
                        self.matchup_utility(neutral_move) - neutral_base
                    )
                    row["robust_delta_objective_value"] = min(
                        row["delta_objective_value"], row["delta_without_spillover"]
                    )
                    row["ranking_basis"] = "minimum_gain_with_and_without_spillover"
            finally:
                self.use_positional_depth_and_injury_boost = enabled
                self.recompute_team_depth_and_injury_minutes()
            recommendations = [
                r for r in recommendations if r["robust_delta_objective_value"] > 1e-10
            ]
        return sorted(
            recommendations,
            key=lambda r: -r.get("robust_delta_objective_value", r["delta_objective_value"]),
        )[:top_k]

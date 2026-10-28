"""Historical prior construction; only completed seasons enter the prior."""

import os

import numpy as np
import pandas as pd

try:
    from .bayesian_model import COUNT_STATS, PERCENTAGE_STATS
except ImportError:
    from bayesian_model import COUNT_STATS, PERCENTAGE_STATS

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

AGG_COLS = (
    COUNT_STATS
    + [f"{s}M" for s in PERCENTAGE_STATS]
    + [f"{s}A" for s in PERCENTAGE_STATS]
    + ["MIN", "GP"]
)


def _load_single_season_totals(season):
    parquet_path = os.path.join(RAW_DIR, f"player_logs_{season}.parquet")

    if os.path.exists(parquet_path):
        df = pd.read_parquet(parquet_path)
    else:
        return {}, {}

    df = df[df["MIN"] > 0].copy()
    if "GAME_ID" in df:
        df = df.drop_duplicates(["PLAYER_ID", "GAME_ID"])
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    df = df.sort_values("GAME_DATE")
    df["GP"] = 1

    for col in AGG_COLS:
        if col not in df.columns:
            df[col] = 0

    totals = df.groupby("PLAYER_ID")[AGG_COLS].sum().reset_index()

    # Also compute late-season (last 15 games) MPG to capture post-trade-deadline role expansions
    last_15_mpg = df.groupby("PLAYER_ID").tail(15).groupby("PLAYER_ID")["MIN"].mean().to_dict()

    prior_dict = {}
    for _, row in totals.iterrows():
        p_id = int(row["PLAYER_ID"])
        d = {col: float(row[col]) for col in AGG_COLS}
        full_mpg = d["MIN"] / max(1.0, d["GP"])
        late_mpg = float(last_15_mpg.get(p_id, full_mpg))
        # Blend 65% full-season MPG + 35% late-season MPG if player played >= 15 games
        if d["GP"] >= 15:
            d["ROLE_MPG"] = 0.65 * full_mpg + 0.35 * late_mpg
        else:
            d["ROLE_MPG"] = full_mpg
        prior_dict[p_id] = d

    return prior_dict, last_15_mpg


def load_prior_season(season="2025_26", blend_prev_season=True, policy=None):
    """Completed-season priors; default primary weight is clip(GP/65, .35, .80).

    Explicit policies support controlled calibration. Only the 2026-27 live
    preparation includes that season's preseason evidence.
    """
    if policy is not None and policy.blend == "single":
        blend_prev_season = False
    primary_dict, _ = _load_single_season_totals(season)
    if not primary_dict:
        print(f"Prior data for {season} not found.")
        return {}

    prev_season_map = {
        "2025_26": "2024_25",
        "2024_25": "2023_24",
        "2023_24": "2022_23",
    }
    prev_season = prev_season_map.get(season)
    secondary_dict = {}
    if blend_prev_season and prev_season:
        secondary_dict, _ = _load_single_season_totals(prev_season)

    combined_pids = set(primary_dict.keys()) | set(secondary_dict.keys())
    blended_dict = {}

    pre_active_pids = set()
    if season == "2025_26":
        pre_path_chk = os.path.join(RAW_DIR, "preseason_logs_2026_27.parquet")
        if os.path.exists(pre_path_chk):
            df_pre_chk = pd.read_parquet(pre_path_chk, columns=["PLAYER_ID", "MIN"])
            pre_active_pids = set(
                df_pre_chk[df_pre_chk["MIN"] > 0]["PLAYER_ID"].astype(int).tolist()
            )

    for pid in combined_pids:
        p1 = primary_dict.get(pid)
        p0 = secondary_dict.get(pid)

        if p1 and p0:
            gp1 = p1["GP"]
            gp0 = p0["GP"]
            w1 = min(0.80, max(0.35, gp1 / 65.0))
            if policy is not None and policy.blend == "fixed":
                w1 = policy.primary_weight
            w0 = 1.0 - w1
            entry = {}
            for col in AGG_COLS:
                entry[col] = w1 * p1[col] + w0 * p0[col]
            raw_blended_min = max(1.0, entry["MIN"])
            # Effective GP/MIN for availability & MPG: if healthy in 2026-27 preseason after a 2025-26 injury,
            # regress GP and MPG back toward healthy multi-year baseline
            if pid in pre_active_pids and gp0 >= 58 and gp1 < 50:
                eff_gp = max(gp1, 0.30 * gp1 + 0.70 * gp0)
                mpg1 = p1.get("ROLE_MPG", p1["MIN"] / max(1.0, gp1))
                mpg0 = p0.get("ROLE_MPG", p0["MIN"] / max(1.0, gp0))
                role_mpg = max(w1 * mpg1 + w0 * mpg0, 0.35 * mpg1 + 0.65 * mpg0)
            else:
                eff_gp = max(gp1, 0.60 * gp1 + 0.40 * gp0)
                role_mpg = w1 * p1.get("ROLE_MPG", p1["MIN"] / max(1.0, gp1)) + w0 * (
                    p0["MIN"] / max(1.0, gp0)
                )
            entry["GP"] = eff_gp
            target_min = role_mpg * entry["GP"]
            scale_m = target_min / raw_blended_min
            for col in AGG_COLS:
                if col != "GP":
                    entry[col] = entry[col] * scale_m
            entry["MIN"] = target_min
            # Blend rates, not totals: a healthy season must not silently gain
            # extra weight solely because it contains more observed minutes.
            for col in AGG_COLS:
                if col not in ("MIN", "GP") and not (
                    policy is not None and policy.legacy_total_rates
                ):
                    entry[col] = target_min * (w1 * p1[col] / p1["MIN"] + w0 * p0[col] / p0["MIN"])
            entry["AVAIL_GP"] = gp1
            blended_dict[pid] = entry
        elif p1:
            entry = dict(p1)
            if "ROLE_MPG" in p1 and p1["GP"] >= 15:
                # Adjust effective MIN to reflect late-season role MPG while preserving per-minute rates
                scale_m = (p1["ROLE_MPG"] * p1["GP"]) / max(1.0, p1["MIN"])
                for col in AGG_COLS:
                    if col != "GP":
                        entry[col] = p1[col] * scale_m
            blended_dict[pid] = entry
        elif p0:
            # Player missed the entire primary season (e.g. season-long injury in 2025-26, returning for 2026-27)
            mult = 0.82 if pid in pre_active_pids else 0.75
            entry = {col: p0[col] * mult for col in AGG_COLS}
            entry["GP"] = p0["GP"] * mult
            blended_dict[pid] = entry

    # If preparing 2025_26 priors for the 2026-27 Draft, integrate 2026-27 Preseason logs for rookies
    if season == "2025_26":
        pre_path = os.path.join(RAW_DIR, "preseason_logs_2026_27.parquet")
        roster_path = os.path.join(PROCESSED_DIR, "active_roster_2026_27.parquet")
        if os.path.exists(pre_path) and os.path.exists(roster_path):
            df_pre = pd.read_parquet(pre_path)
            df_pre = df_pre[df_pre["MIN"] > 0].copy()
            df_pre["GP"] = 1
            for col in AGG_COLS:
                if col not in df_pre.columns:
                    df_pre[col] = 0
            pre_totals = df_pre.groupby("PLAYER_ID")[AGG_COLS].sum().reset_index()

            df_rost = pd.read_parquet(roster_path)
            draft_num_map = {}
            for _, r in df_rost.iterrows():
                try:
                    dnum = (
                        int(r["DRAFT_NUMBER"])
                        if pd.notnull(r.get("DRAFT_NUMBER"))
                        and str(r.get("DRAFT_NUMBER")).isdigit()
                        else 60
                    )
                except Exception:
                    dnum = 60
                draft_num_map[int(r["PLAYER_ID"])] = dnum

            for _, row in pre_totals.iterrows():
                pid = int(row["PLAYER_ID"])
                pre_min = float(row["MIN"])
                pre_gp = float(row["GP"])
                if pre_min < 20 or pre_gp < 1:
                    continue

                existing = blended_dict.get(pid)
                if existing is None or existing.get("MIN", 0) < 150:
                    # Project rookie MPG & availability by draft pedigree, while keeping effective prior_min
                    # proportional to rookie certainty (200-450 mins) so Empirical Bayes shrinks preseason noise!
                    dnum = draft_num_map.get(pid, 60)
                    pre_mpg = pre_min / pre_gp
                    if dnum == 1:
                        target_mpg = max(pre_mpg, 30.0)
                        eff_prior_gp = (
                            16.0  # ~480 effective prior minutes for #1 overall pick (Cooper Flagg)
                        )
                        rookie_avail_gp = 68.0
                    elif dnum <= 5:
                        target_mpg = min(27.0, max(pre_mpg, 24.0))
                        eff_prior_gp = 10.0  # ~250 effective prior minutes
                        rookie_avail_gp = 64.0
                    elif dnum <= 14:
                        target_mpg = min(24.0, max(pre_mpg, 20.0))
                        eff_prior_gp = 7.0  # ~150 effective prior minutes
                        rookie_avail_gp = 60.0
                    else:
                        target_mpg = min(pre_mpg, 18.0)
                        eff_prior_gp = 5.0
                        rookie_avail_gp = 52.0

                    scale_factor = (target_mpg * eff_prior_gp) / pre_min
                    entry = {col: float(row[col]) * scale_factor for col in AGG_COLS if col != "GP"}
                    entry["GP"] = eff_prior_gp
                    entry["MIN"] = target_mpg * eff_prior_gp
                    entry["ROOKIE_AVAIL_GP"] = rookie_avail_gp
                    entry["IS_ROOKIE_PRIOR"] = True
                    entry["EVIDENCE_MIN"] = pre_min
                    entry["EVIDENCE_FGA"] = float(row["FGA"])
                    entry["EVIDENCE_FTA"] = float(row["FTA"])
                    blended_dict[pid] = entry

    return blended_dict


def get_positional_averages(prior_dict, pos_dict=None):
    """
    Calculates both league-wide per-minute averages and position-specific ('G', 'F', 'C')
    per-minute averages for Empirical Bayes shrinkage.
    """
    if pos_dict is None:
        pos_file = os.path.join(PROCESSED_DIR, "player_positions.parquet")
        if os.path.exists(pos_file):
            df_pos = pd.read_parquet(pos_file)
            pos_dict = df_pos.set_index("PLAYER_ID")["POSITION"].to_dict()
        else:
            pos_dict = {}

    valid_items = [(pid, p) for pid, p in prior_dict.items() if p.get("MIN", 0) > 400]
    if not valid_items:
        return {}

    def _compute_rates(player_list):
        total_mins = sum(p["MIN"] for p in player_list)
        if total_mins <= 0:
            return {}
        rates = {}
        for k in AGG_COLS:
            if k == "MIN":
                continue
            total_stat = sum(p.get(k, 0.0) for p in player_list)
            rates[k] = total_stat / total_mins
        # Method-of-moments Poisson rate shrinkage: subtract within-player
        # sampling variance from observed cross-player rate variance.
        kappas = {}
        for stat in COUNT_STATS:
            r = np.array([p.get(stat, 0) / p["MIN"] for p in player_list])
            sampling = np.mean([p.get(stat, 0) / (p["MIN"] ** 2) for p in player_list])
            between = max(1e-8, float(np.var(r, ddof=1)) - sampling) if len(r) > 1 else 1e-8
            kappas[stat] = float(np.clip(float(np.mean(r)) / between, 60, 2000))
        rates["KAPPA"] = kappas
        return rates

    all_players = [p for _, p in valid_items]
    avg_dict = _compute_rates(all_players)

    by_pos = {}
    for pos_key in ("G", "F", "C"):
        bucket = [p for pid, p in valid_items if pos_key in str(pos_dict.get(pid, "")).upper()]
        if len(bucket) >= 15:
            by_pos[pos_key] = _compute_rates(bucket)
        else:
            by_pos[pos_key] = dict(avg_dict)

    avg_dict["BY_POS"] = by_pos
    return avg_dict

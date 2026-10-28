"""Small, explicit policy surface shared by live ingestion and calibration."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class ModelPolicy:
    blend: str = "dynamic"
    primary_weight: float = 0.8
    legacy_total_rates: bool = False
    fixed_kappa: bool = False
    exposure_minutes: float | None = None
    shot_precision_multiplier: float = 1.0
    role: str = "recent_blend"

    def __post_init__(self):
        if self.blend not in {"dynamic", "single", "fixed"}:
            raise ValueError("Unknown seasonal blend")
        if self.role not in {"recent_blend", "ewma", "adaptive_anchor"}:
            raise ValueError("Unknown role updater")
        if not 0 <= self.primary_weight <= 1:
            raise ValueError("Invalid primary season weight")
        if self.exposure_minutes is not None and not 60 <= self.exposure_minutes <= 1000:
            raise ValueError("Invalid effective minutes")
        if not 0.25 <= self.shot_precision_multiplier <= 2:
            raise ValueError("Invalid shot precision")

    def to_dict(self):
        return asdict(self)


def load_model_policy():
    path = Path(__file__).resolve().parents[1] / "config" / "model_policy.json"
    return (
        ModelPolicy(**json.loads(path.read_text(encoding="utf-8")))
        if path.exists()
        else ModelPolicy()
    )


def update_role(bp, history, anchor, policy, recent_window=5, recent_k=3.0):
    """Called AFTER observing a game; predictions must precede this call.

    Caller resets history and anchor after a trade. Histories contain
    (game_id, positive_minutes, date, team_id). EWMA is already updated by bp.
    """
    recent = history[-recent_window:]
    mean = float(np.mean([r[1] for r in recent]))
    k = 1.0 if abs(mean - anchor) >= 6.5 else float(recent_k)
    n = len(history) if policy.role == "adaptive_anchor" else len(recent)
    weight = n / (n + k)
    if policy.role != "ewma":
        bp.expected_minutes = bp.base_expected_minutes = float(
            np.clip(weight * mean + (1 - weight) * anchor, 4, 40)
        )
    bp.prior_expected_minutes = anchor
    bp.current_season_gp = len(history)
    bp.current_season_mpg = float(np.mean([r[1] for r in history]))
    bp.role_observation_weight = weight

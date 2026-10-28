"""Tunable opportunity heuristics; these are not posterior probabilities."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class RotationPolicy:
    redistribution_fraction: float = 1.0
    role_evidence_prior_games: float | None = None
    minute_variance_scale: float = 1.0

    def __post_init__(self):
        if not 0 <= self.redistribution_fraction <= 1:
            raise ValueError("Redistribution fraction must be in [0,1]")
        if not 1 <= self.minute_variance_scale <= 2:
            raise ValueError("Minute variance scale must be in [1,2]")
        if (
            self.role_evidence_prior_games is not None
            and not 0 < self.role_evidence_prior_games <= 100
        ):
            raise ValueError("Role evidence prior games must be positive")

    def evidence_factor(self, player):
        if self.role_evidence_prior_games is None:
            return 1.0
        n = max(0, int(getattr(player, "current_season_gp", 0)))
        observed = max(
            0.0, float(getattr(player, "current_season_mpg", player.base_expected_minutes))
        )
        anchor = max(
            1.0, float(getattr(player, "prior_expected_minutes", player.base_expected_minutes))
        )
        ratio = min(1.0, observed / anchor)
        return 1 - n / (n + self.role_evidence_prior_games) * (1 - ratio)

    def to_dict(self):
        return asdict(self)


def load_rotation_policy():
    path = Path(__file__).resolve().parents[1] / "config/rotation_policy.json"
    return (
        RotationPolicy(**json.loads(path.read_text(encoding="utf-8")))
        if path.exists()
        else RotationPolicy()
    )

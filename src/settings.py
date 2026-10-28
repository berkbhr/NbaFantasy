"""Explicit regular-season and postseason decision policies."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LeagueSettings:
    phase: str = "regular_season"
    playoff_tie_credit: float | None = None
    playoff_spots: int = 4
    max_weekly_adds: int = 3
    adds_used_this_week: int = 0
    protected_player_names: tuple = ()

    def __post_init__(self):
        if self.phase not in ("regular_season", "playoffs"):
            raise ValueError("phase must be regular_season or playoffs")
        if self.playoff_spots != 4:
            raise ValueError("This league qualifies four playoff teams")
        if self.max_weekly_adds < 0 or self.adds_used_this_week < 0:
            raise ValueError("Transaction counts must be nonnegative")
        if self.phase == "playoffs" and self.playoff_tie_credit is None:
            raise ValueError(
                "Configure playoff_tie_credit from your actual playoff tiebreak rule first"
            )
        if self.playoff_tie_credit is not None and not 0 <= self.playoff_tie_credit <= 1:
            raise ValueError("playoff_tie_credit must be in [0,1]")

    @property
    def objective(self):
        return "category_points" if self.phase == "regular_season" else "matchup"

    @property
    def draw_value(self):
        return 0.5 if self.phase == "regular_season" else self.playoff_tie_credit


def load_settings(path=None):
    path = Path(path) if path else Path(__file__).resolve().parents[1] / "config" / "league.json"
    if not path.exists():
        return LeagueSettings()
    return LeagueSettings(**json.loads(path.read_text(encoding="utf-8")))

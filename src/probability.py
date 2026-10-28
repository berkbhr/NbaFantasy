"""Category marginals and weekly W/L/D probabilities.

The dynamic program is exact conditional on independent category outcomes.
Normal category marginals and optional Gaussian-copula sensitivity remain
model approximations, not empirically calibrated probabilities.
"""

import math
from dataclasses import dataclass

import numpy as np
from scipy.special import ndtr, ndtri


class CategoryProbabilities(dict):
    """Mapping of category -> P(win), with P(tie) carried explicitly."""

    def __init__(self, wins=None, ties=None):
        super().__init__(wins or {})
        self.ties = dict(ties or {})

    def copy(self):
        return type(self)(self, self.ties)


@dataclass(frozen=True)
class MatchupOutcome:
    win: float
    loss: float
    draw: float

    def utility(self, draw_value=0.5):
        """Expected standing credit; default one win = two draws."""
        if not 0 <= draw_value <= 1:
            raise ValueError("draw_value must be between 0 and 1")
        return self.win + draw_value * self.draw


def _independent_outcome(wins, ties):
    # Index is category-win minus category-loss balance, offset by category count.
    mass = np.array([1.0])
    for w, t in zip(wins, ties):
        mass = np.convolve(mass, [max(0.0, 1.0 - w - t), t, w])
    middle = len(wins)
    return MatchupOutcome(
        float(mass[middle + 1 :].sum()), float(mass[:middle].sum()), float(mass[middle])
    )


def matchup_outcome(probabilities, tie_probs=None, rho=0.0):
    """P(weekly win/loss/draw), including wins such as 4-3-2.

    rho=0 is exact convolution of independent categorical W/L/T outcomes.
    rho>0 is an optional one-factor Gaussian copula sensitivity, integrated
    with Gauss-Hermite quadrature. rho describes latent Gaussian correlation,
    not correlation of raw box scores or binary win indicators.
    """
    if not 0 <= rho < 1:
        raise ValueError("rho must be in [0, 1)")
    ties_map = getattr(probabilities, "ties", {}) if tie_probs is None else tie_probs
    wins = np.asarray(list(probabilities.values()), dtype=float)
    ties = np.asarray([ties_map.get(c, 0.0) for c in probabilities], dtype=float)
    if (
        not np.all(np.isfinite(wins))
        or not np.all(np.isfinite(ties))
        or np.any(wins < 0)
        or np.any(ties < 0)
        or np.any(wins + ties > 1 + 1e-10)
    ):
        raise ValueError("Invalid category outcome probabilities")
    if rho == 0 or len(wins) == 0:
        return _independent_outcome(wins, ties)
    nodes, weights = np.polynomial.hermite.hermgauss(48)
    # Latent outcomes: low Gaussian = loss, middle = tie, high = win.
    lower = ndtri(np.clip(1 - wins - ties, 0, 1))
    upper = ndtri(np.clip(1 - wins, 0, 1))
    total = np.zeros(3)
    for z, weight in zip(nodes * math.sqrt(2), weights / math.sqrt(math.pi)):
        low = ndtr((lower - math.sqrt(rho) * z) / math.sqrt(1 - rho))
        high = ndtr((upper - math.sqrt(rho) * z) / math.sqrt(1 - rho))
        outcome = _independent_outcome(1 - high, np.maximum(0, high - low))
        total += weight * np.array([outcome.win, outcome.loss, outcome.draw])
    total /= total.sum()
    return MatchupOutcome(*map(float, total))


def normal_category(diff, variance, discrete=False):
    """Normal approximation, with a half-unit tie cell for integer counts."""
    if not math.isfinite(diff) or not math.isfinite(variance) or variance < 0:
        raise ValueError("Category moments must be finite with nonnegative variance")
    if variance <= 1e-12:
        return (1.0, 0.0) if diff > 1e-10 else ((0.0, 0.0) if diff < -1e-10 else (0.0, 1.0))
    sigma = math.sqrt(variance)
    half = 0.5 if discrete else 0.0
    win = float(ndtr((diff - half) / sigma))
    loss = float(ndtr((-diff - half) / sigma))
    return win, max(0.0, 1.0 - win - loss)


def category_points(probabilities):
    """Regular-season objective: E[category wins] + .5 E[category ties]."""
    return sum(
        p + 0.5 * getattr(probabilities, "ties", {}).get(c, 0) for c, p in probabilities.items()
    )


def decision_value(probabilities, objective="category_points", draw_value=0.5):
    if objective == "category_points":
        return category_points(probabilities)
    if objective == "matchup":
        return matchup_outcome(probabilities).utility(draw_value)
    raise ValueError("objective must be category_points or matchup")


def utility_gradient(
    probabilities,
    category,
    diff,
    variance,
    discrete=False,
    draw_value=0.5,
    objective="category_points",
):
    """Local objective derivative with respect to oriented mean, fixed variance."""
    if variance <= 1e-12:
        return 0.0
    step = max(1e-5, math.sqrt(variance) * 1e-4)
    values = []
    for sign in (-1, 1):
        p = probabilities.copy()
        p[category], p.ties[category] = normal_category(diff + sign * step, variance, discrete)
        values.append(decision_value(p, objective, draw_value))
    return (values[1] - values[0]) / (2 * step)

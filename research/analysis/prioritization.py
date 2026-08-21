"""Locked cell-priority score with complete-game bootstrap."""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from statistics import fmean, stdev


@dataclass(frozen=True, slots=True)
class CellPriority:
    effect: float
    standard_error: float
    probability_better: float
    decision_uncertainty: float
    occurrence: float
    score: float


def normal_cdf(value: float) -> float:
    return 0.5 * (1 + math.erf(value / math.sqrt(2)))


def bootstrap_effect(
    games: Sequence[object], effect: Callable[[Sequence[object]], float], *,
    seed: int, replications: int = 2000,
) -> tuple[float, float]:
    """Resample whole game trajectories, never turns."""
    if len(games) < 2:
        raise ValueError("at least two complete games are required")
    rng = random.Random(seed)
    estimate = effect(games)
    draws = [effect([games[rng.randrange(len(games))] for _ in games]) for _ in range(replications)]
    return estimate, stdev(draws)


def priority(effect: float, standard_error: float, occurrence: float) -> CellPriority:
    if standard_error <= 0 or not 0 <= occurrence <= 1:
        raise ValueError("invalid priority inputs")
    z = effect / standard_error
    probability = normal_cdf(z)
    uncertainty = probability * (1 - probability)
    return CellPriority(effect, standard_error, probability, uncertainty, occurrence,
                        occurrence * abs(effect) * uncertainty)

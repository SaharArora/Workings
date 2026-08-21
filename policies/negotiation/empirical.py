"""Frozen theory-anchored empirical response policy with OOD penalty."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

OOD_PENALTY_WEIGHT = 1.0


@dataclass(frozen=True, slots=True)
class FrozenEmpiricalModel:
    version: str
    expected_payoff: Callable[[float, tuple[dict, ...]], float]
    ood_score: Callable[[float, tuple[dict, ...]], float]

    def choose(self, legal_prices: Sequence[float], history: tuple[dict, ...]) -> float:
        if not legal_prices:
            raise ValueError("legal price grid is empty")
        return max(
            legal_prices,
            key=lambda price: self.expected_payoff(price, history) - OOD_PENALTY_WEIGHT * self.ood_score(price, history),
        )

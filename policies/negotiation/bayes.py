"""Bayes-adaptive sequential pricing with a genuine response likelihood."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

BAYES_MIN_GAMES = 200
BAYES_MIN_BSS = 0.10


@dataclass(frozen=True, slots=True)
class BayesEligibility:
    n_games: int
    brier_skill_score: float
    calibrated: bool

    @property
    def eligible(self) -> bool:
        return self.n_games >= BAYES_MIN_GAMES and self.brier_skill_score >= BAYES_MIN_BSS and self.calibrated


@dataclass(slots=True)
class BayesPricingPolicy:
    posterior: dict[float, float]
    rejection_likelihood: Callable[[float, float, tuple[dict, ...]], float]

    def update_rejection(self, price: float, history: tuple[dict, ...], rejected: bool) -> None:
        weights = {}
        for valuation, prior in self.posterior.items():
            rejection = self.rejection_likelihood(valuation, price, history)
            weights[valuation] = prior * (rejection if rejected else 1 - rejection)
        total = sum(weights.values())
        if total <= 0:
            raise ValueError("likelihood assigned zero probability to observation")
        self.posterior = {value: weight / total for value, weight in weights.items()}

    def seller_price(
        self,
        seller_value: float,
        legal_prices: Sequence[float],
        history: tuple[dict, ...] = (),
        continuation_value: Callable[[float], float] = lambda _: 0.0,
    ) -> float:
        def expected(price: float) -> float:
            payoff = 0.0
            for valuation, probability in self.posterior.items():
                rejection = self.rejection_likelihood(valuation, price, history)
                payoff += probability * ((1 - rejection) * (price - seller_value) + rejection * continuation_value(valuation))
            return payoff
        return max(legal_prices, key=lambda price: (expected(price), -price))

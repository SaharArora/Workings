"""Locked negotiation baselines from BUILD_SPEC §4.2."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


def individually_rational_trade(seller_value: float, buyer_value: float) -> bool:
    return buyer_value >= seller_value


def complete_information_price(
    seller_value: float,
    buyer_value: float,
    *,
    max_rounds: int | None,
) -> float | None:
    if not individually_rational_trade(seller_value, buyer_value):
        return None
    if max_rounds is None:
        return (seller_value + buyer_value) / 2
    return buyer_value if max_rounds % 2 else seller_value


def bayes_optimal_posted_price(
    seller_value: float,
    valuation_probabilities: Mapping[float, float],
    legal_prices: Iterable[float],
) -> float:
    """Maximize `(p-V_A) P(V_B>=p)` on the supplied verified price grid."""
    prices = [price for price in legal_prices if price >= seller_value]
    if not prices:
        raise ValueError("no individually rational legal seller price")
    def payoff(price: float) -> float:
        acceptance = sum(mass for value, mass in valuation_probabilities.items() if value >= price)
        return (price - seller_value) * acceptance
    return max(prices, key=lambda price: (payoff(price), -price))


def efficient_outcome(seller_value: float, buyer_value: float, traded: bool) -> bool:
    return traded is (buyer_value >= seller_value)

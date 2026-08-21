"""Evaluation helpers that keep unlimited negotiation distribution separate."""

from __future__ import annotations

from statistics import fmean


def mean_normalized_payoff(values: list[float]) -> float:
    if not values:
        raise ValueError("values are empty")
    return fmean(values)


def negotiation_efficiency(seller_value: float, buyer_value: float, traded: bool) -> bool:
    return traded is (buyer_value >= seller_value)

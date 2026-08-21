"""Cheap-talk baseline and non-deployable persuasion reference levels."""

from __future__ import annotations


def babbling_buyer_buys(prior_high: float, high_value: float) -> bool:
    return prior_high >= 1 / high_value


def full_disclosure_buyer_buys(quality: str) -> bool:
    """P1 reference benchmark; not a deployable equilibrium."""
    return quality == "high"


def commitment_low_signal_probability(prior_high: float, high_value: float) -> float:
    """P2 commitment ceiling; never a deployable baseline or regret target."""
    if prior_high >= 1:
        return 1.0
    return min(prior_high * (high_value - 1) / (1 - prior_high), 1.0)


def commitment_value(prior_high: float, high_value: float) -> float:
    return min(prior_high * high_value, 1.0)

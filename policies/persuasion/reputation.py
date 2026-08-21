"""P3 honest-then-earned-trust seller challenger."""

from __future__ import annotations

import random

REPUTATION_CAP = 0.85
EARLY_FRACTION = 0.30
REPUTATION_BONUS = 0.05


def recommend_buy(
    *, current_quality: str, round_number: int, total_rounds: int, prior_high: float,
    positive_recommendations: int, purchases_after_positive: int,
    population_positive_purchase_rate: float, rng: random.Random,
) -> bool:
    early_rounds = total_rounds * EARLY_FRACTION
    if round_number <= early_rounds:
        return current_quality == "high"
    trust = purchases_after_positive / positive_recommendations if positive_recommendations else 0.0
    bonus = REPUTATION_BONUS if trust > population_positive_purchase_rate else 0.0
    return rng.random() < min(REPUTATION_CAP, prior_high + bonus)

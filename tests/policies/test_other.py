import random

from policies.bargaining.fairness import fair_share
from policies.persuasion.reputation import recommend_buy


def test_bargaining_fairness() -> None:
    assert fair_share(0.8) == 0.77


def test_reputation_is_truthful_early() -> None:
    assert recommend_buy(current_quality="high", round_number=1, total_rounds=10,
        prior_high=0.2, positive_recommendations=0, purchases_after_positive=0,
        population_positive_purchase_rate=0.5, rng=random.Random(1))
    assert not recommend_buy(current_quality="low", round_number=3, total_rounds=10,
        prior_high=0.9, positive_recommendations=0, purchases_after_positive=0,
        population_positive_purchase_rate=0.5, rng=random.Random(1))

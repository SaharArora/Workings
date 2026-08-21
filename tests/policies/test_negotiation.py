import pytest

from policies.negotiation.anchor_favorable import own_favorable_price
from policies.negotiation.bayes import BayesEligibility, BayesPricingPolicy
from policies.negotiation.empirical import FrozenEmpiricalModel
from policies.negotiation.empirical_correction import inferred_buyer_value, inferred_seller_value
from policies.negotiation.fairness_margin import fairness_margin_price
from policies.negotiation.robust import minimax_regret_price


def test_robust_minimax_regret_uses_whole_grid() -> None:
    assert minimax_regret_price(role="seller", own_value=0, legal_prices=[1, 2, 3, 4, 5], opponent_values=[1, 2, 3, 4, 5]) == 3
    assert minimax_regret_price(role="seller", own_value=0, legal_prices=[1, 2, 3, 4, 5], opponent_values=[1, 4, 4, 5, 5]) == 4


def test_bayes_eligibility_and_posterior() -> None:
    assert BayesEligibility(200, 0.10, True).eligible
    policy = BayesPricingPolicy({10: 0.5, 20: 0.5}, lambda value, price, history: 0.9 if value < price else 0.1)
    policy.update_rejection(15, (), True)
    assert policy.posterior[10] == pytest.approx(0.9)


def test_empirical_uses_ood_penalty() -> None:
    model = FrozenEmpiricalModel("v1", lambda price, history: price, lambda price, history: 100 if price == 3 else 0)
    assert model.choose([1, 2, 3], ()) == 2


def test_locked_price_deviations() -> None:
    assert fairness_margin_price(10, 20, extractor="seller") == 18.5
    assert fairness_margin_price(10, 20, extractor="buyer") == 11.5
    assert own_favorable_price(10, 20, role="seller") == 16.5
    assert own_favorable_price(10, 20, role="buyer") == 13.5
    assert inferred_buyer_value(12.5) == 10
    assert inferred_seller_value(15) == 10

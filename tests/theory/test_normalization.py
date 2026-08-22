import pytest

from glee.normalization import (
    NEGOTIATION_PAYOFF_CLIP_MULTIPLIER,
    UnboundedPayoffDomainError,
    bargaining_bounds,
    counterfactual_finite_negotiation_bounds,
    negotiation_clipped_utility_score,
    negotiation_bounds,
    negotiation_payoff_transform,
    negotiation_raw_effect_for_score_delta,
    normalize_payoff,
    persuasion_bounds,
)
from eprocess.experiment import DELTA_MIN


def test_bargaining_bounds() -> None:
    assert normalize_payoff(250, bargaining_bounds(1000)) == 0.25


def test_negotiation_general_negative_safe_bounds() -> None:
    seller = counterfactual_finite_negotiation_bounds("seller", 10, price_min=5, price_max=20)
    buyer = counterfactual_finite_negotiation_bounds("buyer", 15, price_min=5, price_max=20)
    assert (seller.minimum, seller.maximum) == (-5, 10)
    assert (buyer.minimum, buyer.maximum) == (-5, 10)


def test_negotiation_refuses_bounded_transform_for_verified_unbounded_domain() -> None:
    with pytest.raises(UnboundedPayoffDomainError, match="unbounded above"):
        negotiation_bounds("seller", 10, verified_price_min=None, verified_price_max=None)


def test_negotiation_does_not_accept_configured_range_as_mechanism_bound() -> None:
    with pytest.raises(UnboundedPayoffDomainError, match="no observed/configured maximum"):
        negotiation_bounds("seller", 10, verified_price_min=0, verified_price_max=100)


def test_negotiation_bounded_statistical_transform_endpoints() -> None:
    scale = 10
    clip = NEGOTIATION_PAYOFF_CLIP_MULTIPLIER * scale
    assert negotiation_clipped_utility_score(-clip, scale) == 0
    assert negotiation_clipped_utility_score(0, scale) == 0.5
    assert negotiation_clipped_utility_score(clip, scale) == 1


def test_negotiation_transform_clips_extreme_legal_payoffs() -> None:
    positive = negotiation_payoff_transform(1e100, 10)
    negative = negotiation_payoff_transform(-1e100, 10)
    assert positive.score == 1 and positive.clipping_occurred
    assert negative.score == 0 and negative.clipping_occurred
    assert 0 <= positive.score <= 1
    assert 0 <= negative.score <= 1


def test_negotiation_delta_min_local_raw_scale_interpretation() -> None:
    assert DELTA_MIN == 0.01
    assert negotiation_raw_effect_for_score_delta(DELTA_MIN, 100) == 4


def test_negotiation_transform_zero_value_uses_unit_scale() -> None:
    transformed = negotiation_payoff_transform(2, 0)
    assert transformed.scale == 1
    assert transformed.clip_bound == 2
    assert transformed.score == 1


def test_persuasion_cumulative_bounds() -> None:
    buyer = persuasion_bounds(
        "buyer", total_rounds=10, price=1, low_value=0, high_value=2, money_scale=100
    )
    assert (buyer.minimum, buyer.maximum) == (-1000, 1000)

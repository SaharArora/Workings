import pytest

from glee.normalization import (
    UnboundedPayoffDomainError,
    bargaining_bounds,
    counterfactual_finite_negotiation_bounds,
    negotiation_bounds,
    normalize_payoff,
    persuasion_bounds,
)


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


def test_persuasion_cumulative_bounds() -> None:
    buyer = persuasion_bounds(
        "buyer", total_rounds=10, price=1, low_value=0, high_value=2, money_scale=100
    )
    assert (buyer.minimum, buyer.maximum) == (-1000, 1000)

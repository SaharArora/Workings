import pytest

from glee.normalization import (
    bargaining_bounds,
    negotiation_bounds,
    normalize_payoff,
    persuasion_bounds,
)


def test_bargaining_bounds() -> None:
    assert normalize_payoff(250, bargaining_bounds(1000)) == 0.25


def test_negotiation_general_negative_safe_bounds() -> None:
    seller = negotiation_bounds("seller", 10, verified_price_min=5, verified_price_max=20)
    buyer = negotiation_bounds("buyer", 15, verified_price_min=5, verified_price_max=20)
    assert (seller.minimum, seller.maximum) == (-5, 10)
    assert (buyer.minimum, buyer.maximum) == (-5, 10)


def test_negotiation_refuses_unverified_bounds() -> None:
    with pytest.raises(ValueError, match="verified"):
        negotiation_bounds("seller", 10, verified_price_min=None, verified_price_max=None)


def test_persuasion_cumulative_bounds() -> None:
    buyer = persuasion_bounds(
        "buyer", total_rounds=10, price=1, low_value=0, high_value=2, money_scale=100
    )
    assert (buyer.minimum, buyer.maximum) == (-1000, 1000)

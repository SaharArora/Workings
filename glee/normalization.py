"""Generic configuration/role-derived payoff normalization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

NEGOTIATION_PRICE_DOMAIN = "UNBOUNDED_ABOVE"


class UnboundedPayoffDomainError(ValueError):
    """A bounded `[0,1]` transform is undefined for the verified mechanism domain."""


@dataclass(frozen=True, slots=True)
class PayoffBounds:
    minimum: float
    maximum: float

    def normalize(self, payoff: float) -> float:
        if self.maximum <= self.minimum:
            raise ValueError("payoff bounds must have positive width")
        value = (payoff - self.minimum) / (self.maximum - self.minimum)
        if not -1e-12 <= value <= 1 + 1e-12:
            raise ValueError("payoff is outside configuration-derived bounds")
        return min(1.0, max(0.0, value))


def bargaining_bounds(money_to_divide: float) -> PayoffBounds:
    if money_to_divide <= 0:
        raise ValueError("money_to_divide must be positive")
    return PayoffBounds(0.0, money_to_divide)


def negotiation_bounds(
    role: Literal["seller", "buyer"],
    own_value: float,
    *,
    verified_price_min: float | None,
    verified_price_max: float | None,
) -> PayoffBounds:
    """Reject bounded negotiation normalization for the verified unbounded price domain.

    GLEE negotiation prices have no finite mechanism-defined upper bound. The finite
    arguments remain in the signature to make accidental historical call sites fail
    loudly rather than silently reinterpret a configured or observed range as legal
    mechanism support.
    """
    raise UnboundedPayoffDomainError(
        "GLEE negotiation product_price is unbounded above; the locked bounded-payoff "
        "normalization is unavailable and no observed/configured maximum may substitute"
    )


def counterfactual_finite_negotiation_bounds(
    role: Literal["seller", "buyer"],
    own_value: float,
    *,
    price_min: float,
    price_max: float,
) -> PayoffBounds:
    """Pure §9 formula for a future mechanism that independently verifies finite bounds."""
    verified_price_min, verified_price_max = price_min, price_max
    if verified_price_max <= verified_price_min:
        raise ValueError("invalid legal price range")
    if role == "seller":
        return PayoffBounds(
            min(0.0, verified_price_min - own_value),
            max(0.0, verified_price_max - own_value),
        )
    return PayoffBounds(
        min(0.0, own_value - verified_price_max),
        max(0.0, own_value - verified_price_min),
    )


def persuasion_bounds(
    role: Literal["seller", "buyer"],
    *,
    total_rounds: int,
    price: float,
    low_value: float,
    high_value: float,
    money_scale: float,
) -> PayoffBounds:
    if total_rounds < 1 or money_scale <= 0:
        raise ValueError("invalid persuasion configuration")
    if role == "seller":
        stage = (0.0, money_scale * price)
    else:
        stage = (0.0, money_scale * (low_value - price), money_scale * (high_value - price))
    return PayoffBounds(total_rounds * min(stage), total_rounds * max(stage))


def normalize_payoff(payoff: float, bounds: PayoffBounds) -> float:
    return bounds.normalize(payoff)

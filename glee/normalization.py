"""Generic configuration/role-derived payoff normalization."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

NEGOTIATION_PRICE_DOMAIN = "UNBOUNDED_ABOVE"
NEGOTIATION_PAYOFF_CLIP_MULTIPLIER = 2.0


class UnboundedPayoffDomainError(ValueError):
    """Mechanism-derived min-max normalization is undefined for negotiation."""


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


@dataclass(frozen=True, slots=True)
class NegotiationPayoffTransform:
    """Raw utility plus the explicitly clipped negotiation research score."""

    raw_payoff: float
    own_value: float
    scale: float
    clip_bound: float
    clipped_payoff: float
    score: float
    clipping_occurred: bool

    def structured(self) -> dict[str, float | bool | str]:
        return {
            "name": "negotiation_clipped_utility_score_v1",
            "raw_payoff": self.raw_payoff,
            "own_value": self.own_value,
            "scale": self.scale,
            "clip_multiplier": NEGOTIATION_PAYOFF_CLIP_MULTIPLIER,
            "clip_bound": self.clip_bound,
            "clipped_payoff": self.clipped_payoff,
            "Y_t": self.score,
            "clipping_occurred": self.clipping_occurred,
        }


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
        "GLEE negotiation product_price is unbounded above; mechanism-derived min-max "
        "normalization is unavailable and no observed/configured maximum may substitute"
    )


def negotiation_payoff_transform(
    raw_payoff: float, own_value: float
) -> NegotiationPayoffTransform:
    """Map unbounded negotiation utility to the locked bounded statistical score.

    This is a policy-evaluation transform, not mechanism normalization. Raw utility is
    retained in the result so evaluations can detect clipping-induced ranking changes.
    """
    raw = float(raw_payoff)
    value = float(own_value)
    if not math.isfinite(raw) or not math.isfinite(value):
        raise ValueError("raw payoff and own value must be finite")
    scale = max(abs(value), 1.0)
    clip_bound = NEGOTIATION_PAYOFF_CLIP_MULTIPLIER * scale
    clipped = max(-clip_bound, min(raw, clip_bound))
    score = (clipped + clip_bound) / (2 * clip_bound)
    return NegotiationPayoffTransform(
        raw_payoff=raw,
        own_value=value,
        scale=scale,
        clip_bound=clip_bound,
        clipped_payoff=clipped,
        score=score,
        clipping_occurred=clipped != raw,
    )


def negotiation_clipped_utility_score(raw_payoff: float, own_value: float) -> float:
    return negotiation_payoff_transform(raw_payoff, own_value).score


def negotiation_raw_effect_for_score_delta(delta_y: float, own_value: float) -> float:
    """Return the local raw-utility equivalent inside the transform's linear region."""
    delta = float(delta_y)
    value = float(own_value)
    if not math.isfinite(delta) or not math.isfinite(value):
        raise ValueError("delta and own value must be finite")
    scale = max(abs(value), 1.0)
    return 2 * NEGOTIATION_PAYOFF_CLIP_MULTIPLIER * scale * delta


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

"""Persuasion theory export and the distinct production buyer guardrail."""

from __future__ import annotations

import math

from theory.persuasion.baselines import babbling_buyer_buys

PERSUASION_BUY_MARGIN = 0.02
PERSUASION_BUY_TOLERANCE = 1e-12


def production_buyer_buys(expected_value: float, product_price: float) -> bool:
    """Require the locked 2% edge while preserving the weak theory benchmark.

    A free product is bought whenever its expected value is nonnegative. Negative
    prices are outside the production policy's supported mechanism domain.
    """
    expected = float(expected_value)
    price = float(product_price)
    if not math.isfinite(expected) or not math.isfinite(price) or price < 0:
        return False
    threshold = 0.0 if price == 0 else (1.0 + PERSUASION_BUY_MARGIN) * price
    tolerance = PERSUASION_BUY_TOLERANCE * max(1.0, abs(expected), abs(threshold))
    return expected + tolerance >= threshold


__all__ = [
    "PERSUASION_BUY_MARGIN",
    "babbling_buyer_buys",
    "production_buyer_buys",
]

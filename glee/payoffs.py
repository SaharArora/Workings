"""Family-specific raw-payoff semantics for safety and chance constraints."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping


class RawPayoffCategory(StrEnum):
    NEGATIVE = "NEGATIVE"
    ZERO = "ZERO"
    POSITIVE = "POSITIVE"


@dataclass(frozen=True, slots=True)
class BadOutcomeAssessment:
    family: str
    role: str | None
    raw_payoff: float
    category: RawPayoffCategory
    bad: bool
    rule: str


def _category(raw_payoff: float) -> RawPayoffCategory:
    if raw_payoff < 0:
        return RawPayoffCategory.NEGATIVE
    if math.isclose(raw_payoff, 0.0, rel_tol=0.0, abs_tol=1e-12):
        return RawPayoffCategory.ZERO
    return RawPayoffCategory.POSITIVE


def bad_outcome(
    family: str,
    raw_payoff: float,
    config: Mapping[str, Any],
    role: str | None,
) -> BadOutcomeAssessment:
    """Classify material bad outcomes from raw mechanism utility.

    ``config`` is accepted deliberately so future mechanism-specific rules cannot be
    smuggled in through a transformed score.  The currently verified mechanisms all
    use own raw payoff relative to zero, with persuasion retaining a role-specific
    rule label because buyer loss/zero utility and seller no-sale/zero payoff have
    different economic meanings.
    """
    del config  # Reserved for verified configuration-dependent mechanism semantics.
    raw = float(raw_payoff)
    if not math.isfinite(raw):
        raise ValueError("raw payoff must be finite")
    normalized_family = str(family).lower()
    normalized_role = None if role is None else str(role).lower()
    category = _category(raw)
    if normalized_family == "negotiation":
        rule = "RAW_OWN_PAYOFF_LE_ZERO_NO_DEAL_WALKAWAY_OR_NONPOSITIVE_SURPLUS"
    elif normalized_family == "bargaining":
        rule = "RAW_OWN_PAYOFF_LE_ZERO_NO_DEAL_WALKAWAY_OR_ZERO_SHARE"
    elif normalized_family == "persuasion":
        if normalized_role == "buyer":
            rule = "BUYER_RAW_REALIZED_UTILITY_LE_ZERO"
        elif normalized_role == "seller":
            rule = "SELLER_RAW_PAYOFF_LE_ZERO_NO_SALE_OR_ZERO_PAYOFF"
        else:
            raise ValueError("persuasion bad-outcome classification requires buyer/seller role")
    else:
        raise ValueError(f"unknown game family {family!r}")
    return BadOutcomeAssessment(
        family=normalized_family,
        role=normalized_role,
        raw_payoff=raw,
        category=category,
        bad=category in {RawPayoffCategory.NEGATIVE, RawPayoffCategory.ZERO},
        rule=rule,
    )

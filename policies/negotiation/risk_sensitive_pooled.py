"""Continuation-aware risk-sensitive selection for the frozen pooled model.

The response model remains unchanged.  This module changes only how a finite,
IR-safe candidate set is evaluated.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping, Sequence

from glee.normalization import negotiation_clipped_utility_score
from glee.payoffs import bad_outcome

RISK_LAMBDA_GRID = (0.0, 0.10, 0.25, 0.50)
CVAR_ALPHA_GRID = (0.80, 0.90, 0.95)
EPSILON_GRID = (0.10, 0.20, 0.30)

CONTINUATION_MATERIALIZATION_SHRINK = 0.25
MAX_TERMINAL_ZERO_PROBABILITY = 0.50
DOMINANCE_VALUE_TOLERANCE = 0.01
MATERIAL_ACCEPTANCE_ADVANTAGE = 0.10
ENDPOINT_MARGIN_THRESHOLD = 0.75


@dataclass(frozen=True, slots=True)
class RiskParameters:
    risk_lambda: float
    cvar_alpha: float
    epsilon: float

    def __post_init__(self) -> None:
        if self.risk_lambda < 0:
            raise ValueError("risk_lambda must be nonnegative")
        if not 0 < self.cvar_alpha < 1:
            raise ValueError("cvar_alpha must be in (0, 1)")
        if not 0 <= self.epsilon <= 1:
            raise ValueError("epsilon must be in [0, 1]")

    def structured(self) -> dict[str, float]:
        return {
            "lambda": self.risk_lambda,
            "alpha": self.cvar_alpha,
            "epsilon": self.epsilon,
        }


@dataclass(frozen=True, slots=True)
class PayoffBranch:
    name: str
    probability: float
    raw_payoff: float
    normalized_payoff: float

    def structured(self) -> dict[str, float | str]:
        return {
            "name": self.name,
            "probability": self.probability,
            "raw_payoff": self.raw_payoff,
            "Y": self.normalized_payoff,
        }


@dataclass(frozen=True, slots=True)
class RiskCandidate:
    price: float
    source: tuple[str, ...]
    predicted_acceptance: float
    immediate_acceptance_payoff: float
    continuation_target: float
    continuation_target_payoff: float
    next_opportunity_acceptance: float
    conditional_continuation_value: float
    branches: tuple[PayoffBranch, ...]
    expected_raw_payoff: float
    expected_normalized_payoff: float
    cvar_loss: float
    cvar_penalty: float
    risk_adjusted_value: float
    chance_bad_outcome: float
    terminal_zero_probability: float
    chance_constraint_satisfied: bool
    zero_constraint_satisfied: bool
    dominated_for_agreement: bool = False
    dominance_reason: str | None = None

    @property
    def feasible(self) -> bool:
        return (
            self.chance_constraint_satisfied
            and self.zero_constraint_satisfied
            and not self.dominated_for_agreement
        )

    def structured(self) -> dict[str, Any]:
        return {
            "price": self.price,
            "source": list(self.source),
            "predicted_acceptance": self.predicted_acceptance,
            "immediate_acceptance_payoff": self.immediate_acceptance_payoff,
            "continuation_target": self.continuation_target,
            "continuation_target_payoff": self.continuation_target_payoff,
            "next_opportunity_acceptance": self.next_opportunity_acceptance,
            "continuation_materialization_shrink": CONTINUATION_MATERIALIZATION_SHRINK,
            "conditional_continuation_value": self.conditional_continuation_value,
            "branches": [branch.structured() for branch in self.branches],
            "expected_raw_payoff": self.expected_raw_payoff,
            "expected_normalized_payoff": self.expected_normalized_payoff,
            "cvar_loss": self.cvar_loss,
            "cvar_penalty": self.cvar_penalty,
            "risk_adjusted_value": self.risk_adjusted_value,
            "chance_bad_outcome": self.chance_bad_outcome,
            "terminal_zero_probability": self.terminal_zero_probability,
            "chance_constraint_satisfied": self.chance_constraint_satisfied,
            "zero_constraint_satisfied": self.zero_constraint_satisfied,
            "dominated_for_agreement": self.dominated_for_agreement,
            "dominance_reason": self.dominance_reason,
            "feasible": self.feasible,
        }


def payoff_distribution(
    *,
    own_value: float,
    q_accept: float,
    acceptance_payoff: float,
    continuation_target_payoff: float,
    q_next_opportunity_accept: float,
    terminal: bool,
) -> tuple[PayoffBranch, ...]:
    """Build the explicit ACCEPT/CONTINUE/TERMINAL distribution.

    The binary response model supplies both acceptance probabilities.  The fixed
    shrink is a conservative probability/value haircut for the unobserved event that
    one more proposal opportunity materializes.  It is not a fitted walk-away model.
    """
    inputs = (
        own_value,
        q_accept,
        acceptance_payoff,
        continuation_target_payoff,
        q_next_opportunity_accept,
    )
    if not all(math.isfinite(float(value)) for value in inputs):
        raise ValueError("payoff-distribution inputs must be finite")
    if not 0 <= q_accept <= 1 or not 0 <= q_next_opportunity_accept <= 1:
        raise ValueError("probabilities must be in [0, 1]")
    if acceptance_payoff < 0 or continuation_target_payoff < 0:
        raise ValueError("IR-safe candidate payoffs must be nonnegative")
    nonaccept = 1.0 - q_accept
    continue_probability = (
        0.0
        if terminal
        else nonaccept
        * CONTINUATION_MATERIALIZATION_SHRINK
        * q_next_opportunity_accept
    )
    terminal_probability = nonaccept - continue_probability
    raw = (
        ("ACCEPT", q_accept, acceptance_payoff),
        ("NONACCEPT_CONTINUE", continue_probability, continuation_target_payoff),
        ("TERMINAL_NONAGREEMENT", terminal_probability, 0.0),
    )
    branches = tuple(
        PayoffBranch(
            name=name,
            probability=probability,
            raw_payoff=payoff,
            normalized_payoff=negotiation_clipped_utility_score(payoff, own_value),
        )
        for name, probability, payoff in raw
        if probability > 0
    )
    if not math.isclose(
        sum(branch.probability for branch in branches),
        1.0,
        rel_tol=1e-10,
        abs_tol=1e-10,
    ):
        raise AssertionError("payoff branch probabilities must sum to one")
    return branches


def cvar_upper_loss_tail(
    outcomes: Iterable[tuple[float, float]], *, alpha: float
) -> float:
    """Return CVaR_alpha(loss) over the worst ``1-alpha`` probability mass.

    Larger loss values are worse. For bounded utility ``Y``, callers use the genuine
    nonnegative loss ``1 - Y``. For discrete atoms the boundary atom is fractionally
    included to fill the tail exactly.
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    ordered = sorted(
        ((float(loss), float(probability)) for loss, probability in outcomes),
        reverse=True,
    )
    if any(not math.isfinite(loss) or probability < 0 for loss, probability in ordered):
        raise ValueError("invalid loss distribution")
    if not math.isclose(sum(probability for _, probability in ordered), 1.0):
        raise ValueError("loss probabilities must sum to one")
    remaining = 1.0 - alpha
    total = 0.0
    for loss, probability in ordered:
        used = min(probability, remaining)
        total += used * loss
        remaining -= used
        if remaining <= 1e-15:
            break
    return total / (1.0 - alpha)


def bounded_score_loss(normalized_payoff: float) -> float:
    """Return the locked bounded-score loss ``L = 1 - Y``."""
    score = float(normalized_payoff)
    if not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError("normalized payoff must lie in [0, 1]")
    return 1.0 - score


def score_candidate(
    *,
    price: float,
    source: Sequence[str],
    own_value: float,
    q_accept: float,
    acceptance_payoff: float,
    continuation_target: float,
    continuation_target_payoff: float,
    q_next_opportunity_accept: float,
    terminal: bool,
    parameters: RiskParameters,
) -> RiskCandidate:
    branches = payoff_distribution(
        own_value=own_value,
        q_accept=q_accept,
        acceptance_payoff=acceptance_payoff,
        continuation_target_payoff=continuation_target_payoff,
        q_next_opportunity_accept=q_next_opportunity_accept,
        terminal=terminal,
    )
    expected_raw = sum(
        branch.probability * branch.raw_payoff for branch in branches
    )
    expected_normalized = sum(
        branch.probability * branch.normalized_payoff for branch in branches
    )
    cvar_loss = cvar_upper_loss_tail(
        (
            (bounded_score_loss(branch.normalized_payoff), branch.probability)
            for branch in branches
        ),
        alpha=parameters.cvar_alpha,
    )
    chance_bad = sum(
        branch.probability
        for branch in branches
        if bad_outcome("negotiation", branch.raw_payoff, {}, None).bad
    )
    zero_probability = sum(
        branch.probability for branch in branches if branch.raw_payoff <= 0
    )
    penalty = parameters.risk_lambda * cvar_loss
    return RiskCandidate(
        price=float(price),
        source=tuple(sorted(source)),
        predicted_acceptance=q_accept,
        immediate_acceptance_payoff=acceptance_payoff,
        continuation_target=float(continuation_target),
        continuation_target_payoff=continuation_target_payoff,
        next_opportunity_acceptance=q_next_opportunity_accept,
        conditional_continuation_value=(
            0.0
            if terminal
            else CONTINUATION_MATERIALIZATION_SHRINK
            * q_next_opportunity_accept
            * continuation_target_payoff
        ),
        branches=branches,
        expected_raw_payoff=expected_raw,
        expected_normalized_payoff=expected_normalized,
        cvar_loss=cvar_loss,
        cvar_penalty=penalty,
        risk_adjusted_value=expected_normalized - penalty,
        chance_bad_outcome=chance_bad,
        terminal_zero_probability=zero_probability,
        chance_constraint_satisfied=chance_bad <= parameters.epsilon + 1e-12,
        zero_constraint_satisfied=(
            zero_probability <= MAX_TERMINAL_ZERO_PROBABILITY + 1e-12
        ),
    )


def apply_agreement_dominance(
    candidates: Sequence[RiskCandidate],
) -> tuple[RiskCandidate, ...]:
    """Remove near-value candidates with materially worse acceptance probability."""
    output: list[RiskCandidate] = []
    for candidate in candidates:
        dominator = next(
            (
                other
                for other in candidates
                if other is not candidate
                and other.chance_constraint_satisfied
                and other.zero_constraint_satisfied
                and other.risk_adjusted_value
                >= candidate.risk_adjusted_value - DOMINANCE_VALUE_TOLERANCE
                and other.predicted_acceptance
                >= candidate.predicted_acceptance + MATERIAL_ACCEPTANCE_ADVANTAGE
            ),
            None,
        )
        if dominator is None:
            output.append(candidate)
        else:
            output.append(
                replace(
                    candidate,
                    dominated_for_agreement=True,
                    dominance_reason=(
                        f"price={dominator.price}:risk_value_within_"
                        f"{DOMINANCE_VALUE_TOLERANCE}:acceptance_advantage_at_least_"
                        f"{MATERIAL_ACCEPTANCE_ADVANTAGE}"
                    ),
                )
            )
    return tuple(output)


def select_risk_candidate(
    candidates: Sequence[RiskCandidate], *, role: str
) -> RiskCandidate | None:
    dominated = apply_agreement_dominance(candidates)
    feasible = [candidate for candidate in dominated if candidate.feasible]
    if not feasible:
        return None
    tie = (
        lambda candidate: (
            candidate.risk_adjusted_value,
            candidate.predicted_acceptance,
            -candidate.price if role == "seller" else candidate.price,
        )
    )
    selected = max(feasible, key=tie)
    return next(candidate for candidate in dominated if candidate.price == selected.price)


def risk_parameter_grid() -> tuple[RiskParameters, ...]:
    return tuple(
        RiskParameters(risk_lambda, alpha, epsilon)
        for risk_lambda in RISK_LAMBDA_GRID
        for alpha in CVAR_ALPHA_GRID
        for epsilon in EPSILON_GRID
    )

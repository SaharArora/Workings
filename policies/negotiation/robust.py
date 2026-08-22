"""Auditable minimax-regret negotiation policy for an unbounded mechanism.

``pi_ROBUST`` bounds its own decision set for tractability and conservative
decision-making. It does not claim or assume that the GLEE mechanism itself is bounded.
The policy contains no learned component and no probabilistic opponent model.
"""

from __future__ import annotations

import json
import logging
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

NEGOTIATION_ROBUST_SELLER_PRICE_MULTIPLIERS = (1.00, 1.10, 1.25, 1.50, 2.00)
NEGOTIATION_ROBUST_BUYER_PRICE_FRACTIONS = (0.00, 0.25, 0.50, 0.75, 1.00)
NEGOTIATION_ROBUST_BUYER_VALUE_MULTIPLIERS = (1.00, 1.25, 1.50, 2.00)
NEGOTIATION_ROBUST_SELLER_VALUE_FRACTIONS = (0.00, 0.25, 0.50, 0.75, 1.00)
ROBUST_TIE_BREAK = "agreement_favorable:lower_seller_price,higher_buyer_price"


class RobustScaleUnavailable(ValueError):
    """No verified positive quantity can scale a zero-value player's policy grid."""


class RobustActionSetUnavailable(ValueError):
    """Verified action constraints leave no candidate consistent with v1 policy rules."""


@dataclass(frozen=True, slots=True)
class CandidateRegret:
    price: float
    scenario_regrets: tuple[tuple[float, float], ...]
    maximum_regret: float

    def structured(self) -> dict[str, Any]:
        return {
            "price": self.price,
            "scenario_regrets": [
                {"opponent_value": value, "regret": regret}
                for value, regret in self.scenario_regrets
            ],
            "maximum_regret": self.maximum_regret,
        }


@dataclass(frozen=True, slots=True)
class RobustPriceDecision:
    role: str
    own_value: float
    policy_scale: float
    legal_price_min: float | None
    candidate_prices: tuple[float, ...]
    opponent_value_scenarios: tuple[float, ...]
    candidate_regrets: tuple[CandidateRegret, ...]
    chosen_price: float
    tie_break: str = ROBUST_TIE_BREAK

    def structured(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "own_value": self.own_value,
            "policy_scale": self.policy_scale,
            "mechanism_price_upper_bound": None,
            "legal_price_min": self.legal_price_min,
            "candidate_prices": list(self.candidate_prices),
            "opponent_value_scenarios": list(self.opponent_value_scenarios),
            "candidate_regrets": [item.structured() for item in self.candidate_regrets],
            "chosen_price": self.chosen_price,
            "tie_break": self.tie_break,
        }


@dataclass(frozen=True, slots=True)
class RobustActionPlan:
    action: dict[str, Any]
    price_decision: RobustPriceDecision
    observed_offer: float | None
    individually_rational: bool | None
    continuation_available: bool
    decision_rule: str

    def structured(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "price_decision": self.price_decision.structured(),
            "observed_offer": self.observed_offer,
            "individually_rational": self.individually_rational,
            "continuation_available": self.continuation_available,
            "decision_rule": self.decision_rule,
        }


def _numeric_price(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("price must be finite")
    return float(round(value, 10))


def _policy_scale(own_value: float, zero_value_scale: float | None) -> float:
    if not math.isfinite(own_value):
        raise ValueError("own value must be finite")
    if own_value > 0:
        return own_value
    if own_value == 0 and zero_value_scale is not None and zero_value_scale > 0:
        return float(zero_value_scale)
    raise RobustScaleUnavailable("ROBUST_SCALE_UNAVAILABLE")


def _clamp_to_verified_minimum(
    values: Sequence[float], legal_price_min: float | None
) -> tuple[float, ...]:
    minimum = None if legal_price_min is None else _numeric_price(legal_price_min)
    # v1 candidates are already nonnegative; only a positive verified minimum changes
    # them. A nonpositive mechanism minimum therefore needs no clamp.
    if minimum is not None and minimum <= 0:
        minimum = None
    result: list[float] = []
    for value in values:
        candidate = _numeric_price(max(value, minimum) if minimum is not None else value)
        if candidate not in result:
            result.append(candidate)
    return tuple(result)


def seller_candidate_prices(
    reservation_value: float,
    *,
    legal_price_min: float | None = None,
    zero_value_scale: float | None = None,
) -> tuple[float, ...]:
    """Return the finite seller policy set, never a claimed mechanism support."""
    scale = _policy_scale(float(reservation_value), zero_value_scale)
    candidates = _clamp_to_verified_minimum(
        tuple(scale * multiplier for multiplier in NEGOTIATION_ROBUST_SELLER_PRICE_MULTIPLIERS),
        legal_price_min,
    )
    if not candidates or max(candidates) > _numeric_price(2 * scale):
        raise RobustActionSetUnavailable("verified minimum exceeds seller v1 policy cap")
    return candidates


def buyer_candidate_prices(
    buyer_value: float,
    *,
    legal_price_min: float | None = None,
    zero_value_scale: float | None = None,
) -> tuple[float, ...]:
    """Return buyer offers; no candidate deliberately exceeds the buyer's value."""
    scale = _policy_scale(float(buyer_value), zero_value_scale)
    candidates = _clamp_to_verified_minimum(
        tuple(scale * fraction for fraction in NEGOTIATION_ROBUST_BUYER_PRICE_FRACTIONS),
        legal_price_min,
    )
    if not candidates or max(candidates) > float(buyer_value):
        raise RobustActionSetUnavailable("verified minimum exceeds buyer value")
    return candidates


def seller_opponent_scenarios(scale: float) -> tuple[float, ...]:
    return tuple(
        _numeric_price(scale * multiplier)
        for multiplier in NEGOTIATION_ROBUST_BUYER_VALUE_MULTIPLIERS
    )


def buyer_opponent_scenarios(scale: float) -> tuple[float, ...]:
    return tuple(
        _numeric_price(scale * fraction)
        for fraction in NEGOTIATION_ROBUST_SELLER_VALUE_FRACTIONS
    )


def _own_payoff(role: str, own_value: float, price: float, opponent_value: float) -> float:
    if role == "seller":
        return max(price - own_value, 0.0) if price <= opponent_value else 0.0
    return max(own_value - price, 0.0) if price >= opponent_value else 0.0


def _best_possible_payoff(role: str, own_value: float, opponent_value: float) -> float:
    if role == "seller":
        return max(0.0, opponent_value - own_value)
    return max(0.0, own_value - opponent_value)


def minimax_regret_decision(
    *,
    role: str,
    own_value: float,
    candidate_prices: Sequence[float],
    opponent_values: Sequence[float],
    policy_scale: float | None = None,
    legal_price_min: float | None = None,
) -> RobustPriceDecision:
    """Choose minimum maximum regret with deterministic agreement-favorable ties."""
    if role not in {"seller", "buyer"} or not candidate_prices or not opponent_values:
        raise ValueError("invalid robust-policy inputs")
    candidates = tuple(_numeric_price(float(price)) for price in candidate_prices)
    scenarios = tuple(_numeric_price(float(value)) for value in opponent_values)
    regrets: list[CandidateRegret] = []
    for price in candidates:
        by_scenario = tuple(
            (
                value,
                _numeric_price(
                    max(
                        0.0,
                        _best_possible_payoff(role, own_value, value)
                        - _own_payoff(role, own_value, price, value),
                    )
                ),
            )
            for value in scenarios
        )
        regrets.append(
            CandidateRegret(
                price=price,
                scenario_regrets=by_scenario,
                maximum_regret=max(regret for _, regret in by_scenario),
            )
        )
    tie_key = (
        (lambda item: (item.maximum_regret, item.price))
        if role == "seller"
        else (lambda item: (item.maximum_regret, -item.price))
    )
    chosen = min(regrets, key=tie_key).price
    return RobustPriceDecision(
        role=role,
        own_value=float(own_value),
        policy_scale=float(policy_scale if policy_scale is not None else own_value),
        legal_price_min=legal_price_min,
        candidate_prices=candidates,
        opponent_value_scenarios=scenarios,
        candidate_regrets=tuple(regrets),
        chosen_price=chosen,
    )


def minimax_regret_price(
    *,
    role: str,
    own_value: float,
    legal_prices: Sequence[float],
    opponent_values: Sequence[float],
) -> float:
    """Compatibility wrapper: ``legal_prices`` is treated as a policy candidate set."""
    return minimax_regret_decision(
        role=role,
        own_value=own_value,
        candidate_prices=legal_prices,
        opponent_values=opponent_values,
    ).chosen_price


def verified_legal_price_minimum(game: Mapping[str, Any]) -> float | None:
    """Read only an explicitly structured lower bound; never infer one from prose."""
    fields = game.get("valid_actions", {}).get("fields", {})
    field = fields.get("product_price") if isinstance(fields, Mapping) else None
    candidates: list[Any] = []
    if isinstance(field, Mapping):
        candidates.extend((field.get("minimum"), field.get("min")))
    state = game.get("game_state", {})
    legal_range = state.get("legal_price_range") if isinstance(state, Mapping) else None
    if isinstance(legal_range, Mapping):
        candidates.extend((legal_range.get("minimum"), legal_range.get("min")))
    if isinstance(state, Mapping):
        candidates.append(state.get("price_min"))
    for value in candidates:
        if isinstance(value, (int, float)) and math.isfinite(value):
            return float(value)
    return None


def _zero_value_scale(game: Mapping[str, Any]) -> float | None:
    state = game.get("game_state", {})
    value = state.get("product_price_order") if isinstance(state, Mapping) else None
    if isinstance(value, (int, float)) and math.isfinite(value) and value > 0:
        return float(value)
    return None


def robust_price_decision(
    *, role: str, own_value: float, game: Mapping[str, Any] | None = None
) -> RobustPriceDecision:
    legal_minimum = verified_legal_price_minimum(game or {})
    zero_scale = _zero_value_scale(game or {})
    scale = _policy_scale(float(own_value), zero_scale)
    if role == "seller":
        candidates = seller_candidate_prices(
            own_value, legal_price_min=legal_minimum, zero_value_scale=zero_scale
        )
        scenarios = seller_opponent_scenarios(scale)
    elif role == "buyer":
        candidates = buyer_candidate_prices(
            own_value, legal_price_min=legal_minimum, zero_value_scale=zero_scale
        )
        scenarios = buyer_opponent_scenarios(scale)
    else:
        raise ValueError(f"unknown negotiation role {role!r}")
    return minimax_regret_decision(
        role=role,
        own_value=own_value,
        candidate_prices=candidates,
        opponent_values=scenarios,
        policy_scale=scale,
        legal_price_min=legal_minimum,
    )


def _field_description(game: Mapping[str, Any]) -> str:
    fields = game.get("valid_actions", {}).get("fields", {})
    return " ".join(f"{key} {value}" for key, value in fields.items()).lower()


def robust_action_plan(game: Mapping[str, Any]) -> RobustActionPlan:
    """Build an action plus auditable deterministic regret diagnostics.

    Simplified v1 continuation rule: when a counteroffer is legal, accept an
    individually rational current offer only when it is at least as favorable as the
    policy's chosen minimax-regret proposal. On a terminal response with no counteroffer,
    accept any individually rational offer; otherwise reject. The chosen proposal is a
    deterministic reference, not a probabilistic continuation-value estimate.
    """
    state = game["game_state"]
    me = str(state["current_player"])
    role = str(state[f"{me}_role"])
    own_value = float(state[f"{me}_value"])
    price_decision = robust_price_decision(role=role, own_value=own_value, game=game)
    action_type = str(game["valid_actions"]["type"])
    if action_type == "offer":
        return RobustActionPlan(
            action={"product_price": price_decision.chosen_price},
            price_decision=price_decision,
            observed_offer=None,
            individually_rational=None,
            continuation_available=False,
            decision_rule="MINIMAX_REGRET_PROPOSAL",
        )
    if action_type != "decision":
        raise ValueError(f"ROBUST does not support negotiation action type {action_type!r}")

    offered = float(state["last_offer"]["price"])
    individually_rational = offered >= own_value if role == "seller" else offered <= own_value
    fields = game["valid_actions"].get("fields", {})
    continuation_available = "product_price" in fields
    if continuation_available:
        at_least_as_good = (
            offered >= price_decision.chosen_price
            if role == "seller"
            else offered <= price_decision.chosen_price
        )
        accept = individually_rational and at_least_as_good
        if accept:
            action = {"decision": "AcceptOffer"}
            rule = "ACCEPT_IF_IR_AND_AT_LEAST_ROBUST_PROPOSAL"
        else:
            action = {
                "decision": "RejectOffer",
                "product_price": price_decision.chosen_price,
            }
            rule = "REJECT_AND_COUNTER_WITH_ROBUST_PROPOSAL"
    elif individually_rational:
        action = {"decision": "AcceptOffer"}
        rule = "TERMINAL_ACCEPT_IF_INDIVIDUALLY_RATIONAL"
    else:
        description = _field_description(game)
        if "rejectoffer" in description:
            action = {"decision": "RejectOffer"}
            rule = "TERMINAL_REJECT_NON_IR"
        elif "walkaway" in description:
            action = {"decision": "WalkAway"}
            rule = "TERMINAL_WALK_AWAY_NON_IR"
        else:
            raise RobustActionSetUnavailable("no advertised legal non-accept decision")
    return RobustActionPlan(
        action=action,
        price_decision=price_decision,
        observed_offer=offered,
        individually_rational=individually_rational,
        continuation_available=continuation_available,
        decision_rule=rule,
    )


def robust_negotiation_action(game: dict[str, Any]) -> dict[str, Any]:
    plan = robust_action_plan(game)
    logger.info("negotiation_robust %s", json.dumps(plan.structured(), sort_keys=True))
    return dict(plan.action)

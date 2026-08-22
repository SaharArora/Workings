"""Deterministic concession-aware negotiation challenger.

``NEGOTIATION_ADAPTIVE`` is deliberately separate from static ``NEGOTIATION_ROBUST``.
It starts from ROBUST's minimax-regret quote and conditions only on mechanically
observed offers in the current game. It maintains no posterior, fitted response model,
or historical artifact and therefore makes no BAYES claim.
"""

from __future__ import annotations

import json
import logging
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from policies.negotiation.robust import (
    RobustActionSetUnavailable,
    robust_price_decision,
)

logger = logging.getLogger(__name__)

ADAPTIVE_CONCESSION_RATE = 0.35
ADAPTIVE_ACCEPTANCE_FRACTION = 0.90
ADAPTIVE_NO_PROGRESS_REPEAT_LIMIT = 3
ADAPTIVE_RELATIVE_TOLERANCE = 1e-6
ADAPTIVE_ABSOLUTE_TOLERANCE = 1e-9


@dataclass(frozen=True, slots=True)
class AdaptiveActionPlan:
    """One auditable adaptive-policy decision."""

    action: dict[str, Any]
    role: str
    own_value: float
    robust_reference_price: float
    opponent_offers: tuple[float, ...]
    first_opponent_offer: float | None
    best_offer_seen: float | None
    previous_best_offer: float | None
    observed_offer: float | None
    adaptive_counter: float | None
    individually_rational: bool | None
    continuation_available: bool
    current_payoff: float | None
    continuation_target_payoff: float | None
    opponent_offer_improved: bool | None
    proposal_materially_changed: bool | None
    decision_rule: str

    def structured(self) -> dict[str, Any]:
        counter_respects_reservation = (
            self.adaptive_counter is None
            or (
                self.adaptive_counter >= self.own_value
                if self.role == "seller"
                else self.adaptive_counter <= self.own_value
            )
        )
        acceptance_respects_rule = True
        if self.action.get("decision") == "AcceptOffer":
            acceptance_respects_rule = self.individually_rational is True
            if self.continuation_available:
                acceptance_respects_rule = acceptance_respects_rule and bool(
                    self.current_payoff is not None
                    and self.continuation_target_payoff is not None
                    and self.current_payoff
                    >= ADAPTIVE_ACCEPTANCE_FRACTION * self.continuation_target_payoff
                )
        return {
            "policy": "NEGOTIATION_ADAPTIVE",
            "adaptation_kind": "deterministic_observed-history_conditioning_not_bayes",
            "role": self.role,
            "own_value": self.own_value,
            "robust_reference_price": self.robust_reference_price,
            "opponent_offers": list(self.opponent_offers),
            "first_opponent_offer": self.first_opponent_offer,
            "best_offer_seen": self.best_offer_seen,
            "previous_best_offer": self.previous_best_offer,
            "observed_offer": self.observed_offer,
            "adaptive_counter": self.adaptive_counter,
            "individually_rational": self.individually_rational,
            "continuation_available": self.continuation_available,
            "current_payoff": self.current_payoff,
            "continuation_target_payoff": self.continuation_target_payoff,
            "acceptance_fraction": ADAPTIVE_ACCEPTANCE_FRACTION,
            "concession_rate": ADAPTIVE_CONCESSION_RATE,
            "opponent_offer_improved": self.opponent_offer_improved,
            "proposal_materially_changed": self.proposal_materially_changed,
            "decision_rule": self.decision_rule,
            "counter_respects_reservation": counter_respects_reservation,
            "acceptance_respects_rule": acceptance_respects_rule,
            "rule_invariants_satisfied": (
                counter_respects_reservation and acceptance_respects_rule
            ),
        }


def _price(value: Any) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _materially_equal(left: float, right: float) -> bool:
    return math.isclose(
        left,
        right,
        rel_tol=ADAPTIVE_RELATIVE_TOLERANCE,
        abs_tol=ADAPTIVE_ABSOLUTE_TOLERANCE,
    )


def _opponent_history_offers(game: Mapping[str, Any], *, me: str) -> tuple[float, ...]:
    """Extract only mechanically observed opponent offers from public history."""
    state = game["game_state"]
    history = state.get("history", [])
    if not isinstance(history, Sequence):
        return ()
    observed: list[float] = []
    for item in history:
        if not isinstance(item, Mapping):
            continue
        offer = item.get("offer")
        if isinstance(offer, Mapping) and str(offer.get("from_player", "")) != me:
            value = _price(offer.get("price"))
            if value is not None:
                observed.append(value)
        if str(item.get("decided_by", "")) != me:
            value = _price(item.get("counteroffer"))
            if value is not None:
                observed.append(value)
    return tuple(observed)


def _best(role: str, offers: Sequence[float]) -> float | None:
    if not offers:
        return None
    return max(offers) if role == "seller" else min(offers)


def _prior_opponent_offers(
    history_offers: Sequence[float], *, current_offer: float
) -> tuple[float, ...]:
    """Remove the API history entry that materializes the current counteroffer.

    Live negotiation payloads include an opponent's newest counteroffer both as
    ``last_offer`` and as the last response's ``counteroffer`` in ``history``. Removing
    one matching trailing occurrence prevents comparing the current offer with itself.
    """
    values = list(history_offers)
    for index in range(len(values) - 1, -1, -1):
        if _materially_equal(values[index], current_offer):
            values.pop(index)
            break
    return tuple(values)


def _improved(role: str, current: float, previous_best: float | None) -> bool:
    if previous_best is None:
        return True
    if role == "seller":
        return current > previous_best and not _materially_equal(current, previous_best)
    return current < previous_best and not _materially_equal(current, previous_best)


def adaptive_counter_price(
    *,
    role: str,
    own_value: float,
    robust_reference_price: float,
    first_opponent_offer: float,
    best_offer_seen: float,
) -> float:
    """Match 35% of the opponent's concession from its observed first anchor."""
    own = float(own_value)
    target = float(robust_reference_price)
    first = float(first_opponent_offer)
    best = float(best_offer_seen)
    if role == "seller":
        opponent_concession = max(0.0, best - first)
        result = max(own, target - ADAPTIVE_CONCESSION_RATE * opponent_concession)
    elif role == "buyer":
        opponent_concession = max(0.0, first - best)
        result = min(own, target + ADAPTIVE_CONCESSION_RATE * opponent_concession)
    else:
        raise ValueError(f"unknown negotiation role {role!r}")
    if not math.isfinite(result):
        raise ValueError("adaptive counter must be finite")
    return float(round(result, 10))


def _field_description(game: Mapping[str, Any]) -> str:
    fields = game.get("valid_actions", {}).get("fields", {})
    return " ".join(f"{key} {value}" for key, value in fields.items()).lower()


def _proposal_changed(game: Mapping[str, Any], *, me: str, counter: float) -> bool | None:
    history = game["game_state"].get("history", [])
    if not isinstance(history, Sequence):
        return None
    own = [
        item
        for item in history
        if isinstance(item, Mapping)
        and str(item.get("decided_by", "")) == me
        and _price(item.get("counteroffer")) is not None
    ]
    if not own:
        return None
    previous = float(own[-1]["counteroffer"])
    return not _materially_equal(previous, counter)


def _adaptive_no_progress(
    game: Mapping[str, Any], *, me: str, role: str, offered: float, counter: float
) -> bool:
    """Require both an unchanged proposal and no opponent improvement three times."""
    state = game["game_state"]
    if state.get("horizon_known") is not False or "walkaway" not in _field_description(game):
        return False
    history = state.get("history", [])
    if not isinstance(history, Sequence):
        return False
    own_responses = [
        item
        for item in history
        if isinstance(item, Mapping)
        and str(item.get("decided_by", "")) == me
        and str(item.get("decision", "")) == "RejectOffer"
    ]
    needed = ADAPTIVE_NO_PROGRESS_REPEAT_LIMIT - 1
    if len(own_responses) < needed:
        return False
    for item in own_responses[-needed:]:
        prior_counter = _price(item.get("counteroffer"))
        prior_offer = item.get("offer")
        prior_price = _price(prior_offer.get("price")) if isinstance(prior_offer, Mapping) else None
        if prior_counter is None or prior_price is None or not _materially_equal(prior_counter, counter):
            return False
        if _improved(role, offered, prior_price):
            return False
    return True


def adaptive_action_plan(game: Mapping[str, Any]) -> AdaptiveActionPlan:
    """Build a deterministic continuation-aware adaptive negotiation action."""
    state = game["game_state"]
    me = str(state["current_player"])
    role = str(state[f"{me}_role"])
    own_value = float(state[f"{me}_value"])
    robust = robust_price_decision(role=role, own_value=own_value, game=game)
    target = robust.chosen_price
    action_type = str(game["valid_actions"]["type"])
    history_offers = _opponent_history_offers(game, me=me)

    if action_type == "offer":
        return AdaptiveActionPlan(
            action={"product_price": target},
            role=role,
            own_value=own_value,
            robust_reference_price=target,
            opponent_offers=history_offers,
            first_opponent_offer=history_offers[0] if history_offers else None,
            best_offer_seen=_best(role, history_offers),
            previous_best_offer=_best(role, history_offers),
            observed_offer=None,
            adaptive_counter=None,
            individually_rational=None,
            continuation_available=False,
            current_payoff=None,
            continuation_target_payoff=None,
            opponent_offer_improved=None,
            proposal_materially_changed=None,
            decision_rule="INITIAL_ROBUST_REFERENCE_PROPOSAL",
        )
    if action_type != "decision":
        raise ValueError(f"ADAPTIVE does not support negotiation action type {action_type!r}")

    offered = float(state["last_offer"]["price"])
    prior_offers = _prior_opponent_offers(history_offers, current_offer=offered)
    all_offers = (*prior_offers, offered)
    best_seen = _best(role, all_offers)
    assert best_seen is not None
    first_offer = all_offers[0]
    previous_best = _best(role, prior_offers)
    counter = adaptive_counter_price(
        role=role,
        own_value=own_value,
        robust_reference_price=target,
        first_opponent_offer=first_offer,
        best_offer_seen=best_seen,
    )
    fields = game["valid_actions"].get("fields", {})
    continuation_available = "product_price" in fields
    individually_rational = offered >= own_value if role == "seller" else offered <= own_value
    current_payoff = offered - own_value if role == "seller" else own_value - offered
    continuation_payoff = counter - own_value if role == "seller" else own_value - counter
    improved = _improved(role, offered, previous_best)
    proposal_changed = _proposal_changed(game, me=me, counter=counter)

    if not continuation_available:
        if individually_rational:
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
    elif individually_rational and current_payoff >= (
        ADAPTIVE_ACCEPTANCE_FRACTION * continuation_payoff
    ):
        action = {"decision": "AcceptOffer"}
        rule = "ACCEPT_IF_IR_AND_90_PERCENT_OF_ADAPTIVE_CONTINUATION_TARGET"
    elif _adaptive_no_progress(
        game,
        me=me,
        role=role,
        offered=offered,
        counter=counter,
    ):
        action = {"decision": "WalkAway"}
        rule = "WALK_AWAY_AFTER_STRUCTURAL_ADAPTIVE_NO_PROGRESS"
    else:
        action = {"decision": "RejectOffer", "product_price": counter}
        rule = "REJECT_AND_COUNTER_WITH_ADAPTIVE_PROPOSAL"

    return AdaptiveActionPlan(
        action=action,
        role=role,
        own_value=own_value,
        robust_reference_price=target,
        opponent_offers=all_offers,
        first_opponent_offer=first_offer,
        best_offer_seen=best_seen,
        previous_best_offer=previous_best,
        observed_offer=offered,
        adaptive_counter=counter,
        individually_rational=individually_rational,
        continuation_available=continuation_available,
        current_payoff=current_payoff,
        continuation_target_payoff=continuation_payoff,
        opponent_offer_improved=improved,
        proposal_materially_changed=proposal_changed,
        decision_rule=rule,
    )


def adaptive_negotiation_action(game: dict[str, Any]) -> dict[str, Any]:
    plan = adaptive_action_plan(game)
    logger.info("negotiation_adaptive %s", json.dumps(plan.structured(), sort_keys=True))
    return dict(plan.action)

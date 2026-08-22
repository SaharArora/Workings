"""Finite-candidate empirical policy backed by a frozen pooled response model."""

from __future__ import annotations

import json
import logging
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opponent_models.pooled_negotiation import (
    PooledNegotiationModel,
    pooled_feature_map,
)
from policies.negotiation.adaptive import adaptive_counter_price
from policies.negotiation.fairness_margin import fairness_margin_price
from policies.negotiation.robust import (
    buyer_candidate_prices,
    robust_action_plan,
    robust_price_decision,
    seller_candidate_prices,
)
from theory.negotiation.baselines import complete_information_price

logger = logging.getLogger(__name__)

POOLED_CONTINUATION_FRACTION = 0.25
POOLED_NO_PROGRESS_REPEAT_LIMIT = 3


@dataclass(frozen=True, slots=True)
class CandidateValue:
    price: float
    source: tuple[str, ...]
    predicted_acceptance: float
    agreement_payoff: float
    continuation_payoff: float
    expected_value: float
    clipped_features: tuple[str, ...]

    def structured(self) -> dict[str, Any]:
        return {
            "price": self.price,
            "source": list(self.source),
            "predicted_acceptance": self.predicted_acceptance,
            "agreement_payoff": self.agreement_payoff,
            "continuation_payoff": self.continuation_payoff,
            "expected_value": self.expected_value,
            "clipped_features": list(self.clipped_features),
        }


@dataclass(frozen=True, slots=True)
class PooledEmpiricalPlan:
    action: dict[str, Any]
    role: str
    own_value: float
    robust_price: float
    adaptive_price: float
    opponent_category: str
    model_version: str
    candidates: tuple[CandidateValue, ...]
    chosen_price: float
    chosen_expected_value: float
    current_offer: float | None
    current_offer_payoff: float | None
    continuation_payoff: float
    decision_rule: str

    def structured(self) -> dict[str, Any]:
        ir = all(
            candidate.price >= self.own_value
            if self.role == "seller"
            else 0 <= candidate.price <= self.own_value
            for candidate in self.candidates
        )
        return {
            "policy": "NEGOTIATION_POOLED_EMPIRICAL",
            "model_version": self.model_version,
            "role": self.role,
            "own_value": self.own_value,
            "opponent_category": self.opponent_category,
            "robust_price": self.robust_price,
            "adaptive_price": self.adaptive_price,
            "candidate_prices": [candidate.price for candidate in self.candidates],
            "candidates": [candidate.structured() for candidate in self.candidates],
            "chosen_price": self.chosen_price,
            "chosen_expected_value": self.chosen_expected_value,
            "current_offer": self.current_offer,
            "current_offer_payoff": self.current_offer_payoff,
            "continuation_payoff": self.continuation_payoff,
            "continuation_rule": (
                "terminal=0; nonterminal=25% of the model-estimated one-step ROBUST value"
            ),
            "decision_rule": self.decision_rule,
            "candidate_set_is_finite_policy_set_not_mechanism_bound": True,
            "all_candidates_respect_own_ir": ir,
            "rule_invariants_satisfied": ir,
        }


def _numeric(value: Any) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _offer_history(game: Mapping[str, Any]) -> list[tuple[str, float]]:
    state = game["game_state"]
    history = state.get("history", [])
    result: list[tuple[str, float]] = []

    def append(player: Any, price: Any) -> None:
        value = _numeric(price)
        if not player or value is None:
            return
        item = (str(player), value)
        if not result or result[-1] != item:
            result.append(item)

    if isinstance(history, Sequence):
        for response in history:
            if not isinstance(response, Mapping):
                continue
            offer = response.get("offer")
            if isinstance(offer, Mapping):
                append(offer.get("from_player"), offer.get("price"))
            append(response.get("decided_by"), response.get("counteroffer"))
    last = state.get("last_offer")
    if isinstance(last, Mapping):
        append(last.get("from_player"), last.get("price"))
    return result


def _opponent_category(game: Mapping[str, Any]) -> str:
    value = str(game.get("opponent", {}).get("type", "unknown")).lower()
    if value in {"human", "player", "otree"}:
        return "human"
    if value in {"agent", "llm", "bot"}:
        return "llm"
    return "unknown"


def _role_offers(
    game: Mapping[str, Any], *, me: str, role: str
) -> tuple[list[float], list[float]]:
    ours: list[float] = []
    opponent: list[float] = []
    for player, price in _offer_history(game):
        (ours if player == me else opponent).append(price)
    return ours, opponent


def _adaptive_price(
    *, role: str, own_value: float, robust_price: float, opponent_offers: Sequence[float]
) -> float:
    if not opponent_offers:
        return robust_price
    best = max(opponent_offers) if role == "seller" else min(opponent_offers)
    return adaptive_counter_price(
        role=role,
        own_value=own_value,
        robust_reference_price=robust_price,
        first_opponent_offer=opponent_offers[0],
        best_offer_seen=best,
    )


def _fairness_candidate(game: Mapping[str, Any]) -> float | None:
    state = game["game_state"]
    if not bool(state.get("complete_information")):
        return None
    seller = _numeric(state.get("player_1_value"))
    buyer = _numeric(state.get("player_2_value"))
    rounds = state.get("max_rounds")
    if seller is None or buyer is None or not isinstance(rounds, int):
        return None
    theory = complete_information_price(seller, buyer, max_rounds=rounds)
    if theory is None:
        return None
    extractor = "seller" if theory == buyer else "buyer"
    return fairness_margin_price(seller, buyer, extractor=extractor)


def candidate_prices(
    game: Mapping[str, Any], *, role: str, own_value: float, robust_price: float,
    adaptive_price: float, opponent_offers: Sequence[float]
) -> dict[float, set[str]]:
    """Create the finite policy action set without claiming a mechanism bound."""
    candidates: dict[float, set[str]] = {}

    def add(value: float | None, source: str) -> None:
        if value is None or not math.isfinite(value):
            return
        price = float(round(value, 10))
        ir = price >= own_value if role == "seller" else 0 <= price <= own_value
        if ir:
            candidates.setdefault(price, set()).add(source)

    add(robust_price, "ROBUST")
    add(adaptive_price, "ADAPTIVE_FIXED")
    grid = (
        seller_candidate_prices(own_value)
        if role == "seller"
        else buyer_candidate_prices(own_value)
    )
    for price in grid:
        add(price, "OWN_VALUE_NORMALIZED_GRID")
    if opponent_offers:
        recent = opponent_offers[-1]
        best = max(opponent_offers) if role == "seller" else min(opponent_offers)
        add(recent, "RECENT_OPPONENT_OFFER")
        add(best, "BEST_OPPONENT_OFFER")
        add((robust_price + best) / 2.0, "ROBUST_BEST_OPPONENT_MIDPOINT")
    add(_fairness_candidate(game), "COMPLETE_INFORMATION_FAIRNESS_MARGIN")
    if not candidates:
        raise ValueError("no individually rational pooled candidate")
    return candidates


def _payoff(role: str, own_value: float, price: float) -> float:
    return max(0.0, price - own_value) if role == "seller" else max(0.0, own_value - price)


def _feature_map(
    game: Mapping[str, Any], *, role: str, own_value: float, price: float,
    own_offers: Sequence[float], opponent_offers: Sequence[float]
) -> dict[str, float]:
    state = game["game_state"]
    horizon_known = bool(state.get("horizon_known"))
    return pooled_feature_map(
        role=role,
        own_value=own_value,
        proposal_price=price,
        complete_information=bool(state.get("complete_information")),
        horizon_known=horizon_known,
        max_rounds=(int(state["max_rounds"]) if horizon_known else None),
        round_number=int(state.get("round", 1)),
        messages_allowed=bool(state.get("messages_allowed", False)),
        opponent_category=_opponent_category(game),
        source_stratum="live",
        prior_own_offers=own_offers,
        prior_opponent_offers=opponent_offers,
    )


def _no_progress(
    game: Mapping[str, Any], *, me: str, current_offer: float, chosen_price: float
) -> bool:
    state = game["game_state"]
    if state.get("horizon_known") is not False:
        return False
    fields = str(game.get("valid_actions", {}).get("fields", {})).lower()
    if "walkaway" not in fields:
        return False
    responses = [
        item
        for item in state.get("history", [])
        if isinstance(item, Mapping)
        and str(item.get("decided_by")) == me
        and str(item.get("decision")) == "RejectOffer"
    ]
    needed = POOLED_NO_PROGRESS_REPEAT_LIMIT - 1
    if len(responses) < needed:
        return False
    for item in responses[-needed:]:
        offer = item.get("offer")
        if (
            not isinstance(offer, Mapping)
            or not math.isclose(float(offer.get("price", math.nan)), current_offer)
            or not math.isclose(float(item.get("counteroffer", math.nan)), chosen_price)
        ):
            return False
    return True


def pooled_empirical_action_plan(
    game: Mapping[str, Any], model: PooledNegotiationModel
) -> PooledEmpiricalPlan:
    state = game["game_state"]
    me = str(state["current_player"])
    role = str(state[f"{me}_role"])
    own_value = float(state[f"{me}_value"])
    robust = robust_price_decision(role=role, own_value=own_value, game=game).chosen_price
    own_offers, opponent_offers = _role_offers(game, me=me, role=role)
    adaptive = _adaptive_price(
        role=role,
        own_value=own_value,
        robust_price=robust,
        opponent_offers=opponent_offers,
    )
    action_type = str(game["valid_actions"]["type"])
    if action_type == "decision" and "product_price" not in game["valid_actions"].get("fields", {}):
        robust_terminal = robust_action_plan(game)
        return PooledEmpiricalPlan(
            action=dict(robust_terminal.action),
            role=role,
            own_value=own_value,
            robust_price=robust,
            adaptive_price=adaptive,
            opponent_category=_opponent_category(game),
            model_version=model.model_version,
            candidates=(),
            chosen_price=robust,
            chosen_expected_value=0.0,
            current_offer=float(state["last_offer"]["price"]),
            current_offer_payoff=(
                _payoff(role, own_value, float(state["last_offer"]["price"]))
            ),
            continuation_payoff=0.0,
            decision_rule="TERMINAL_DELEGATE_TO_IR_SAFE_ROBUST_RESPONSE",
        )
    if action_type not in {"offer", "decision"}:
        raise ValueError(f"unsupported pooled negotiation action type {action_type!r}")
    raw_candidates = candidate_prices(
        game,
        role=role,
        own_value=own_value,
        robust_price=robust,
        adaptive_price=adaptive,
        opponent_offers=opponent_offers,
    )
    preliminary: dict[float, tuple[float, tuple[str, ...]]] = {}
    for price in raw_candidates:
        features = _feature_map(
            game,
            role=role,
            own_value=own_value,
            price=price,
            own_offers=own_offers,
            opponent_offers=opponent_offers,
        )
        preliminary[price] = model.predict_acceptance(role=role, features=features)
    continuation = 0.0
    if action_type == "decision":
        robust_probability = preliminary[robust][0]
        continuation = (
            POOLED_CONTINUATION_FRACTION
            * robust_probability
            * _payoff(role, own_value, robust)
        )
    candidates = tuple(
        CandidateValue(
            price=price,
            source=tuple(sorted(raw_candidates[price])),
            predicted_acceptance=preliminary[price][0],
            agreement_payoff=_payoff(role, own_value, price),
            continuation_payoff=continuation,
            expected_value=(
                preliminary[price][0] * _payoff(role, own_value, price)
                + (1 - preliminary[price][0]) * continuation
            ),
            clipped_features=preliminary[price][1],
        )
        for price in sorted(raw_candidates)
    )
    tie = (
        (lambda candidate: (candidate.expected_value, -candidate.price))
        if role == "seller"
        else (lambda candidate: (candidate.expected_value, candidate.price))
    )
    chosen = max(candidates, key=tie)
    current_offer = (
        float(state["last_offer"]["price"]) if action_type == "decision" else None
    )
    current_ir = (
        current_offer is not None
        and (current_offer >= own_value if role == "seller" else current_offer <= own_value)
    )
    current_payoff = (
        _payoff(role, own_value, current_offer) if current_ir and current_offer is not None else None
    )
    if action_type == "offer":
        action = {"product_price": chosen.price}
        rule = "MAXIMIZE_MODEL_ESTIMATED_ONE_STEP_VALUE"
    elif current_payoff is not None and current_payoff >= chosen.expected_value:
        action = {"decision": "AcceptOffer"}
        rule = "ACCEPT_IR_OFFER_AT_LEAST_AS_VALUABLE_AS_BEST_MODEL_CANDIDATE"
    elif _no_progress(
        game,
        me=me,
        current_offer=float(current_offer),
        chosen_price=chosen.price,
    ):
        action = {"decision": "WalkAway"}
        rule = "WALK_AWAY_AFTER_THREE_IDENTICAL_OFFER_COUNTER_PAIRS"
    else:
        action = {"decision": "RejectOffer", "product_price": chosen.price}
        rule = "REJECT_AND_COUNTER_WITH_MAXIMUM_MODEL_VALUE_CANDIDATE"
    return PooledEmpiricalPlan(
        action=action,
        role=role,
        own_value=own_value,
        robust_price=robust,
        adaptive_price=adaptive,
        opponent_category=_opponent_category(game),
        model_version=model.model_version,
        candidates=candidates,
        chosen_price=chosen.price,
        chosen_expected_value=chosen.expected_value,
        current_offer=current_offer,
        current_offer_payoff=current_payoff,
        continuation_payoff=continuation,
        decision_rule=rule,
    )


class PooledEmpiricalPolicy:
    """Load one frozen artifact once and expose a router-compatible callable."""

    def __init__(self, artifact_path: Path) -> None:
        self.artifact_path = artifact_path
        self.model = PooledNegotiationModel.load(artifact_path)
        self.last_plan: PooledEmpiricalPlan | None = None

    def plan(self, game: Mapping[str, Any]) -> PooledEmpiricalPlan:
        self.last_plan = pooled_empirical_action_plan(game, self.model)
        return self.last_plan

    def __call__(self, game: dict[str, Any]) -> dict[str, Any]:
        plan = self.plan(game)
        logger.info("negotiation_pooled_empirical %s", json.dumps(plan.structured(), sort_keys=True))
        return dict(plan.action)

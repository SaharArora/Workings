"""Configuration-driven policy routing with structured, fail-closed decisions."""

from __future__ import annotations

import json
import logging
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from glee.retry import fallback_action, sanitize_action
from policies.negotiation.bayes import BayesEligibility
from policies.negotiation.robust import evenly_spaced_grid, minimax_regret_price
from policies.persuasion.babbling import babbling_buyer_buys
from theory.bargaining.baselines import (
    bayes_adaptive_reference,
    finite_horizon_alice_share,
    rubinstein_alice_share,
)
from theory.negotiation.baselines import bayes_optimal_posted_price, complete_information_price

logger = logging.getLogger(__name__)
Policy = Callable[[dict[str, Any]], dict[str, Any]]
RouteKey = tuple[str, str]


class UnsupportedCellError(ValueError):
    """The payload does not match a configuration defined by the build specification."""


class PolicyInputsUnavailable(ValueError):
    """A named policy lacks verified mechanism inputs needed to execute safely."""


@dataclass(slots=True)
class PolicyArtifact:
    """Lazy, frozen policy artifact whose load failure is a routing input, not a crash."""

    name: str
    loader: Callable[[], Policy]
    _loaded: Policy | None = field(default=None, init=False, repr=False)

    @classmethod
    def from_policy(cls, name: str, policy: Policy) -> "PolicyArtifact":
        return cls(name=name, loader=lambda: policy)

    def load(self) -> Policy:
        if self._loaded is None:
            loaded = self.loader()
            if not callable(loaded):
                raise TypeError(f"artifact {self.name!r} did not load a callable policy")
            self._loaded = loaded
        return self._loaded


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    game_family: str
    cell: str
    role: str | None
    theory_baseline: str | None
    bayes_eligible: bool | None
    available_policy_artifacts: tuple[str, ...]
    promoted_policy: str | None
    selected_policy: str
    fallback_reason: str | None
    execution_fallback_reason: str | None = None
    policy: Policy | None = field(default=None, repr=False, compare=False)

    def structured(self) -> dict[str, Any]:
        return {
            "game_family": self.game_family,
            "cell": self.cell,
            "role": self.role,
            "theory_baseline": self.theory_baseline,
            "bayes_eligible": self.bayes_eligible,
            "available_policy_artifacts": list(self.available_policy_artifacts),
            "promoted_policy": self.promoted_policy,
            "selected_policy": self.selected_policy,
            "fallback_reason": self.fallback_reason,
            "execution_fallback_reason": self.execution_fallback_reason,
        }


def cell_key(game: Mapping[str, Any]) -> str:
    """Return a stable exact-cell identifier from server-visible configuration fields."""
    state = game["game_state"]
    family = str(game["game_family"])
    stable = {
        key: state.get(key)
        for key in (
            "complete_information",
            "horizon_known",
            "max_rounds",
            "messages_allowed",
            "seller_message_type",
            "is_seller_know_cv",
            "total_rounds",
            "p",
            "v",
            "u",
            "product_price",
            "money_to_divide",
            "delta_1",
            "delta_2",
        )
        if key in state
    }
    return f"{family}:{json.dumps(stable, sort_keys=True, separators=(',', ':'))}"


def _role(game: Mapping[str, Any]) -> str | None:
    state = game["game_state"]
    player = str(game.get("your_player") or state.get("current_player") or "")
    return state.get(f"{player}_role") or player or None


def _artifact_status(artifact: PolicyArtifact | None) -> tuple[Policy | None, str | None]:
    if artifact is None:
        return None, "MISSING"
    try:
        return artifact.load(), None
    except Exception as exc:
        logger.warning("policy_artifact_load_failed name=%s error=%s", artifact.name, type(exc).__name__)
        return None, "CORRUPT"


class PolicyRouter:
    """Select a named policy solely from cell semantics and recorded policy state."""

    def __init__(
        self,
        *,
        bayes_eligibility: Mapping[RouteKey, BayesEligibility] | None = None,
        bayes_artifacts: Mapping[RouteKey, PolicyArtifact] | None = None,
        promoted_policies: Mapping[RouteKey, PolicyArtifact] | None = None,
    ) -> None:
        self.bayes_eligibility = dict(bayes_eligibility or {})
        self.bayes_artifacts = dict(bayes_artifacts or {})
        self.promoted_policies = dict(promoted_policies or {})
        self.last_routing: RoutingDecision | None = None

    def route(self, game: dict[str, Any]) -> RoutingDecision:
        family = str(game.get("game_family", ""))
        cell = cell_key(game) if "game_state" in game and family else f"{family or 'unknown'}:UNSUPPORTED"
        opponent = str(game.get("opponent", {}).get("type", "hidden"))
        key = (cell, opponent)
        role = _role(game) if "game_state" in game else None
        promoted = self.promoted_policies.get(key)
        promoted_policy, promoted_error = _artifact_status(promoted)
        available: list[str] = []
        if promoted_policy is not None and promoted is not None:
            available.append(promoted.name)

        try:
            baseline, incumbent_name, incumbent_policy, eligible, reason, incumbent_available = self._incumbent(game, key)
            available.extend(incumbent_available)
        except (KeyError, TypeError, ValueError) as exc:
            return RoutingDecision(
                game_family=family or "unknown",
                cell=cell,
                role=role,
                theory_baseline=None,
                bayes_eligible=None,
                available_policy_artifacts=tuple(sorted(set(available))),
                promoted_policy=promoted.name if promoted else None,
                selected_policy="SAFE_LEGAL_FALLBACK",
                fallback_reason=f"UNSUPPORTED_CELL:{type(exc).__name__}",
                policy=None,
            )

        selected_name, selected_policy = incumbent_name, incumbent_policy
        promoted_name = promoted.name if promoted else None
        fallback_reason = reason
        if promoted_policy is not None and promoted is not None:
            selected_name, selected_policy = promoted.name, promoted_policy
            fallback_reason = None
        elif promoted_error is not None and promoted is not None:
            suffix = f"PROMOTED_ARTIFACT_{promoted_error}"
            fallback_reason = f"{fallback_reason};{suffix}" if fallback_reason else suffix

        return RoutingDecision(
            game_family=family,
            cell=cell,
            role=role,
            theory_baseline=baseline,
            bayes_eligible=eligible,
            available_policy_artifacts=tuple(sorted(set(available))),
            promoted_policy=promoted_name,
            selected_policy=selected_name,
            fallback_reason=fallback_reason,
            policy=selected_policy,
        )

    def _incumbent(
        self, game: dict[str, Any], key: RouteKey
    ) -> tuple[str, str, Policy, bool | None, str | None, list[str]]:
        family = str(game["game_family"])
        state = game["game_state"]
        if family == "negotiation":
            if "complete_information" not in state or "horizon_known" not in state:
                raise UnsupportedCellError("negotiation information/horizon fields absent")
            complete = bool(state["complete_information"])
            horizon_known = bool(state["horizon_known"])
            rounds = state.get("max_rounds") if horizon_known else None
            if horizon_known and (not isinstance(rounds, int) or rounds < 1):
                raise UnsupportedCellError("invalid known horizon")
            if complete:
                if rounds == 1:
                    label = "NEGOTIATION_COMPLETE_T1_THEORY"
                elif rounds is None:
                    label = "NEGOTIATION_COMPLETE_UNLIMITED_MIDPOINT"
                elif rounds % 2:
                    label = "NEGOTIATION_COMPLETE_FINITE_ODD_THEORY"
                else:
                    label = "NEGOTIATION_COMPLETE_FINITE_EVEN_THEORY"
                return label, label, negotiation_complete_theory_action, None, None, []
            if rounds == 1:
                if state.get("opponent_value_prior"):
                    label = "NEGOTIATION_INCOMPLETE_T1_BAYES_POSTED_PRICE"
                    return label, label, negotiation_incomplete_t1_bayes_action, None, None, []
                label = "NEGOTIATION_INCOMPLETE_T1_ROBUST"
                return label, label, robust_negotiation_action, None, "NO_TRUSTED_PRIOR", []

            baseline = "NEGOTIATION_INCOMPLETE_MULTIROUND_PORTFOLIO"
            eligibility = self.bayes_eligibility.get(key)
            if eligibility is None:
                return (
                    baseline,
                    "NEGOTIATION_ROBUST",
                    robust_negotiation_action,
                    None,
                    "BAYES_ELIGIBILITY_UNAVAILABLE",
                    [],
                )
            eligible = eligibility.eligible
            if eligible:
                artifact = self.bayes_artifacts.get(key)
                bayes_policy, artifact_error = _artifact_status(artifact)
                if bayes_policy is not None and artifact is not None:
                    return baseline, "NEGOTIATION_BAYES", bayes_policy, True, None, [artifact.name]
                return baseline, "NEGOTIATION_ROBUST", robust_negotiation_action, True, f"BAYES_ARTIFACT_{artifact_error}", []
            return baseline, "NEGOTIATION_ROBUST", robust_negotiation_action, False, "BAYES_INELIGIBLE", []

        if family == "bargaining":
            if "complete_information" not in state or "horizon_known" not in state:
                raise UnsupportedCellError("bargaining information/horizon fields absent")
            complete = bool(state["complete_information"])
            finite = bool(state["horizon_known"])
            if finite and (not isinstance(state.get("max_rounds"), int) or state["max_rounds"] < 1):
                raise UnsupportedCellError("invalid bargaining horizon")
            label = "BARGAINING_" + ("COMPLETE" if complete else "INCOMPLETE") + ("_FINITE" if finite else "_UNLIMITED")
            return label, label, bargaining_theory_action, None, None, []

        if family == "persuasion":
            if "p" not in state or "total_rounds" not in state:
                raise UnsupportedCellError("persuasion configuration fields absent")
            label = "PERSUASION_P0_BABBLING"
            return label, label, persuasion_p0_action, None, None, []

        raise UnsupportedCellError(f"unknown family {family!r}")

    def decide_with_routing(self, game: dict[str, Any]) -> tuple[dict[str, Any], RoutingDecision]:
        decision = self.route(game)
        try:
            if decision.policy is None:
                raise UnsupportedCellError(decision.fallback_reason or "unsupported cell")
            action = sanitize_action(decision.policy(game))
        except Exception as exc:
            decision = replace(decision, execution_fallback_reason=f"{type(exc).__name__}:{exc}")
            logger.warning("policy_execution_fallback %s", json.dumps(decision.structured(), sort_keys=True))
            action = sanitize_action(fallback_action(game))
        self.last_routing = decision
        logger.info("policy_routing %s", json.dumps(decision.structured(), sort_keys=True))
        return action, decision

    def decide(self, game: dict[str, Any]) -> dict[str, Any]:
        return self.decide_with_routing(game)[0]


def negotiation_complete_theory_action(game: dict[str, Any]) -> dict[str, Any]:
    state = game["game_state"]
    action_type = game["valid_actions"]["type"]
    me = str(state["current_player"])
    role = str(state[f"{me}_role"])
    own_value = float(state[f"{me}_value"])
    if action_type == "decision":
        return _negotiation_decision(game, role, own_value, counter_policy=negotiation_complete_theory_action)
    seller = float(state["player_1_value"])
    buyer = float(state["player_2_value"])
    price = complete_information_price(seller, buyer, max_rounds=state.get("max_rounds"))
    return {"product_price": own_value if price is None else price}


def negotiation_incomplete_t1_bayes_action(game: dict[str, Any]) -> dict[str, Any]:
    state = game["game_state"]
    me = str(state["current_player"])
    role = str(state[f"{me}_role"])
    own_value = float(state[f"{me}_value"])
    if game["valid_actions"]["type"] == "decision":
        return _negotiation_decision(game, role, own_value, counter_policy=None)
    if role != "seller":
        raise PolicyInputsUnavailable("posted-price theory requires the seller move")
    prior = {float(value): float(mass) for value, mass in state["opponent_value_prior"].items()}
    return {"product_price": bayes_optimal_posted_price(own_value, prior, _explicit_legal_price_grid(game))}


def _negotiation_decision(
    game: dict[str, Any], role: str, own_value: float, *, counter_policy: Policy | None
) -> dict[str, Any]:
    state = game["game_state"]
    offered = float(state["last_offer"]["price"])
    accept = offered >= own_value if role == "seller" else offered <= own_value
    if accept:
        return {"decision": "AcceptOffer"}
    fields = game["valid_actions"].get("fields", {})
    if "product_price" not in fields:
        return {"decision": "RejectOffer"}
    if counter_policy is None:
        raise PolicyInputsUnavailable("counteroffer policy inputs are unavailable")
    counter = counter_policy({**game, "valid_actions": {"type": "offer", "fields": fields}})
    return {"decision": "RejectOffer", "product_price": counter["product_price"]}


def _range_values(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, Mapping):
        return None
    minimum = value.get("minimum", value.get("min"))
    maximum = value.get("maximum", value.get("max"))
    if isinstance(minimum, (int, float)) and isinstance(maximum, (int, float)):
        minimum, maximum = float(minimum), float(maximum)
        if math.isfinite(minimum) and math.isfinite(maximum) and maximum > minimum:
            return minimum, maximum
    return None


def _explicit_legal_price_grid(game: Mapping[str, Any]) -> tuple[float, ...]:
    field = game["valid_actions"].get("fields", {}).get("product_price")
    if isinstance(field, Mapping):
        values = field.get("values") or field.get("allowed_values")
        if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
            result = tuple(float(value) for value in values)
            if result:
                return result
        bounds = _range_values(field)
        if bounds:
            return evenly_spaced_grid(*bounds)
    state = game["game_state"]
    bounds = _range_values(state.get("legal_price_range"))
    if bounds:
        return evenly_spaced_grid(*bounds)
    if isinstance(state.get("price_min"), (int, float)) and isinstance(state.get("price_max"), (int, float)):
        bounds = _range_values({"min": state["price_min"], "max": state["price_max"]})
        if bounds:
            return evenly_spaced_grid(*bounds)
    raise PolicyInputsUnavailable("verified legal price grid is not exposed")


def _explicit_opponent_value_grid(game: Mapping[str, Any]) -> tuple[float, ...]:
    state = game["game_state"]
    bounds = _range_values(state.get("opponent_valuation_range"))
    if not bounds:
        me = str(state.get("current_player", ""))
        opponent = "player_2" if me == "player_1" else "player_1"
        bounds = _range_values(state.get(f"{opponent}_value_range"))
    if not bounds:
        raise PolicyInputsUnavailable("verified opponent valuation range is not exposed")
    return evenly_spaced_grid(*bounds)


def robust_negotiation_action(game: dict[str, Any]) -> dict[str, Any]:
    """Execute static minimax regret only from explicitly exposed mechanism grids."""
    state = game["game_state"]
    me = str(state["current_player"])
    role = str(state[f"{me}_role"])
    own_value = float(state[f"{me}_value"])
    if game["valid_actions"]["type"] == "decision":
        return _negotiation_decision(game, role, own_value, counter_policy=robust_negotiation_action)
    price = minimax_regret_price(
        role=role,
        own_value=own_value,
        legal_prices=_explicit_legal_price_grid(game),
        opponent_values=_explicit_opponent_value_grid(game),
    )
    return {"product_price": price}


def bargaining_theory_action(game: dict[str, Any]) -> dict[str, Any]:
    state = game["game_state"]
    action_type = game["valid_actions"]["type"]
    money = float(state["money_to_divide"])
    if action_type == "decision":
        offer = state["last_offer"]
        own = float(offer[f"{state['current_player']}_gain"])
        return {"decision": "accept" if own >= money / 2 else "reject"}
    complete = bool(state["complete_information"])
    finite = bool(state["horizon_known"])
    if complete:
        if "delta_1" not in state or "delta_2" not in state:
            raise PolicyInputsUnavailable("complete bargaining discount factors unavailable")
        alice = (
            finite_horizon_alice_share(float(state["delta_1"]), float(state["delta_2"]), int(state["max_rounds"]))
            if finite
            else rubinstein_alice_share(float(state["delta_1"]), float(state["delta_2"]))
        )
    else:
        prior = state.get("opponent_delta_prior")
        if not isinstance(prior, Mapping):
            raise PolicyInputsUnavailable("incomplete bargaining prior unavailable")
        me = str(state["current_player"])
        own_delta = float(state[f"delta_{1 if me == 'player_1' else 2}"])
        own_share = bayes_adaptive_reference(
            own_delta,
            {float(value): float(mass) for value, mass in prior.items()},
            finite_rounds=int(state["max_rounds"]) if finite else None,
            agent_is_alice=me == "player_1",
        )
        alice = own_share if me == "player_1" else 1 - own_share
    return {"alice_gain": money * alice, "bob_gain": money * (1 - alice)}


def persuasion_p0_action(game: dict[str, Any]) -> dict[str, Any]:
    state = game["game_state"]
    action_type = game["valid_actions"]["type"]
    if action_type == "seller_message":
        return {"message": "This product is available."}
    if action_type == "seller_recommendation":
        return {"decision": "yes"}
    if action_type == "buyer_decision":
        if "v" not in state:
            raise PolicyInputsUnavailable("buyer high value unavailable")
        return {"decision": "yes" if babbling_buyer_buys(float(state["p"]), float(state["v"])) else "no"}
    raise UnsupportedCellError(f"unknown persuasion action {action_type!r}")

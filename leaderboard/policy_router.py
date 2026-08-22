"""Configuration-driven policy routing with structured, fail-closed decisions."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from glee.retry import fallback_action, sanitize_action
from leaderboard.experimental_overrides import (
    AuthorizationStatus,
    ExperimentalOverrideRegistry,
)
from policies.negotiation.bayes import BayesEligibility
from policies.negotiation.adaptive import (
    adaptive_action_plan,
    adaptive_negotiation_action,
)
from policies.negotiation.fairness_margin import fairness_margin_price
from policies.negotiation.robust import robust_negotiation_action
from policies.bargaining.fairness import fair_share
from policies.persuasion.babbling import production_buyer_buys
from policies.persuasion.reputation import reputation_action
from theory.bargaining.baselines import (
    bayes_adaptive_reference,
    finite_horizon_offer_alice_share,
    finite_horizon_shares,
    rubinstein_proposer_share,
)
from theory.negotiation.baselines import bayes_optimal_posted_price, complete_information_price

logger = logging.getLogger(__name__)
Policy = Callable[[dict[str, Any]], dict[str, Any]]
PolicyDetailsBuilder = Callable[[dict[str, Any], Mapping[str, Any]], Mapping[str, Any]]
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
    baseline_policy: str | None = None
    experimental_policy: str | None = None
    authorization_status: str | None = None
    authorization_source: str | None = None
    execution_fallback_reason: str | None = None
    policy_details: Mapping[str, Any] = field(default_factory=dict, compare=False)
    policy: Policy | None = field(default=None, repr=False, compare=False)
    details_builder: PolicyDetailsBuilder | None = field(
        default=None, repr=False, compare=False
    )

    def structured(self) -> dict[str, Any]:
        return {
            "game_family": self.game_family,
            "cell": self.cell,
            "role": self.role,
            "theory_baseline": self.theory_baseline,
            "bayes_eligible": self.bayes_eligible,
            "available_policy_artifacts": list(self.available_policy_artifacts),
            "promoted_policy": self.promoted_policy,
            "baseline_policy": self.baseline_policy,
            "experimental_policy": self.experimental_policy,
            "authorization_status": self.authorization_status,
            "authorization_source": self.authorization_source,
            "selected_policy": self.selected_policy,
            "fallback_reason": self.fallback_reason,
            "execution_fallback_reason": self.execution_fallback_reason,
            "policy_details": dict(self.policy_details),
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
            "player_1_value",
            "player_2_value",
            "player_1_role",
            "player_2_role",
        )
        if key in state
    }
    return f"{family}:{json.dumps(stable, sort_keys=True, separators=(',', ':'))}"


def _role(game: Mapping[str, Any]) -> str | None:
    state = game["game_state"]
    player = str(game.get("your_player") or state.get("current_player") or "")
    family = str(game.get("game_family", ""))
    if family == "negotiation":
        return state.get(f"{player}_role") or player or None
    if family == "bargaining":
        return {"player_1": "alice", "player_2": "bob"}.get(player, player or None)
    if family == "persuasion":
        return {"player_1": "seller", "player_2": "buyer"}.get(player, player or None)
    return player or None


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
        pooled_negotiation_artifact: PolicyArtifact | None = None,
        experimental_overrides: ExperimentalOverrideRegistry | None = None,
    ) -> None:
        self.bayes_eligibility = dict(bayes_eligibility or {})
        self.bayes_artifacts = dict(bayes_artifacts or {})
        self.promoted_policies = dict(promoted_policies or {})
        self.pooled_negotiation_artifact = pooled_negotiation_artifact
        self.experimental_overrides = experimental_overrides or ExperimentalOverrideRegistry()
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
        authorization_status = self._incumbent_authorization(incumbent_name)
        authorization_source: str | None = None
        experimental_name: str | None = None
        details_builder: PolicyDetailsBuilder | None = None
        if promoted_policy is not None and promoted is not None:
            selected_name, selected_policy = promoted.name, promoted_policy
            fallback_reason = None
            authorization_status = AuthorizationStatus.E_PROCESS_PROMOTED
        elif promoted_error is not None and promoted is not None:
            suffix = f"PROMOTED_ARTIFACT_{promoted_error}"
            fallback_reason = f"{fallback_reason};{suffix}" if fallback_reason else suffix

        baseline_policy = selected_name
        resolution = (
            None
            if authorization_status == AuthorizationStatus.E_PROCESS_PROMOTED
            else self.experimental_overrides.resolve(
                game,
                baseline_policy=baseline_policy,
                role=role,
            )
        )
        if resolution is not None:
            experimental_name = resolution.override.policy_name
            authorization_source = self.experimental_overrides.authorization_source
            if resolution.available:
                pooled_policy: Policy | None = None
                if experimental_name == "NEGOTIATION_POOLED_EMPIRICAL":
                    pooled_policy, artifact_error = _artifact_status(
                        self.pooled_negotiation_artifact
                    )
                    if pooled_policy is None:
                        unavailable = f"POOLED_ARTIFACT_{artifact_error}"
                        fallback_reason = (
                            f"{fallback_reason};{unavailable}"
                            if fallback_reason
                            else unavailable
                        )
                    elif self.pooled_negotiation_artifact is not None:
                        available.append(self.pooled_negotiation_artifact.name)
                if (
                    experimental_name != "NEGOTIATION_POOLED_EMPIRICAL"
                    or pooled_policy is not None
                ):
                    selected_name, selected_policy, details_builder = self._experimental_execution(
                        experimental_name,
                        baseline_policy=selected_policy,
                        pooled_policy=pooled_policy,
                    )
                    authorization_status = resolution.authorization_status
            else:
                unavailable = resolution.unavailable_reason or "EXPERIMENT_INPUT_UNAVAILABLE"
                fallback_reason = (
                    f"{fallback_reason};{unavailable}" if fallback_reason else unavailable
                )

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
            baseline_policy=baseline_policy,
            experimental_policy=experimental_name,
            authorization_status=str(authorization_status),
            authorization_source=authorization_source,
            policy=selected_policy,
            details_builder=details_builder,
        )

    @staticmethod
    def _incumbent_authorization(policy_name: str) -> AuthorizationStatus:
        if "ROBUST" in policy_name or "EQUAL_SPLIT" in policy_name:
            return AuthorizationStatus.PORTFOLIO_INCUMBENT
        return AuthorizationStatus.THEORY_INCUMBENT

    def _experimental_execution(
        self,
        policy_name: str,
        *,
        baseline_policy: Policy,
        pooled_policy: Policy | None = None,
    ) -> tuple[str, Policy, PolicyDetailsBuilder]:
        if policy_name == "NEGOTIATION_ADAPTIVE":
            return (
                policy_name,
                adaptive_negotiation_action,
                lambda game, action: adaptive_action_plan(game).structured(),
            )
        if policy_name == "NEGOTIATION_FAIRNESS_MARGIN":
            return (
                policy_name,
                negotiation_fairness_margin_action,
                negotiation_fairness_margin_details,
            )
        if policy_name == "NEGOTIATION_POOLED_EMPIRICAL":
            if pooled_policy is None:
                raise PolicyInputsUnavailable("POOLED_ARTIFACT_UNAVAILABLE")

            def details(game: dict[str, Any], action: Mapping[str, Any]) -> Mapping[str, Any]:
                plan = getattr(pooled_policy, "last_plan", None)
                if plan is not None and hasattr(plan, "structured"):
                    return plan.structured()
                return {
                    "policy": policy_name,
                    "selected_live_action": dict(action),
                    "diagnostics": "artifact_callable_did_not_expose_last_plan",
                    "rule_invariants_satisfied": True,
                }

            return policy_name, pooled_policy, details
        if policy_name == "BARGAINING_FAIRNESS":
            policy = lambda game: bargaining_fairness_action(game, baseline_policy)
            details = lambda game, action: bargaining_fairness_details(
                game,
                action,
                baseline_policy,
            )
            return policy_name, policy, details
        if policy_name == "PERSUASION_P3_REPUTATION":
            rate = self.experimental_overrides.population_positive_purchase_rate
            if rate is None:
                raise PolicyInputsUnavailable("P3_EXPERIMENT_INPUT_UNAVAILABLE")
            policy = lambda game: reputation_action(
                game,
                population_positive_purchase_rate=float(rate),
            )
            details = lambda game, action: {
                "population_positive_purchase_rate": float(rate),
                "selected_live_action": dict(action),
                "input_provenance": "frozen_pre_outcome_population_statistic",
                "rule_invariants_satisfied": True,
            }
            return policy_name, policy, details
        raise PolicyInputsUnavailable(f"unknown experimental policy {policy_name!r}")

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
            if complete or isinstance(state.get("opponent_delta_prior"), Mapping):
                return label, label, bargaining_theory_action, None, None, []
            return (
                label + "_BAYES_REFERENCE",
                "BARGAINING_INCOMPLETE_EQUAL_SPLIT",
                bargaining_incomplete_equal_split_action,
                None,
                "OPPONENT_DELTA_PRIOR_UNAVAILABLE",
                [],
            )

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
        else:
            if decision.details_builder is not None:
                try:
                    details = dict(decision.details_builder(game, action))
                except Exception as exc:
                    details = {"diagnostics_error": type(exc).__name__}
                decision = replace(decision, policy_details=details)
        self.last_routing = decision
        logger.info("policy_routing %s", json.dumps(decision.structured(), sort_keys=True))
        return action, decision

    def decide(self, game: dict[str, Any]) -> dict[str, Any]:
        return self.decide_with_routing(game)[0]


def _negotiation_fairness_prices(
    game: Mapping[str, Any],
) -> tuple[float | None, float | None, str | None]:
    state = game["game_state"]
    seller = float(state["player_1_value"])
    buyer = float(state["player_2_value"])
    theory_price = complete_information_price(
        seller,
        buyer,
        max_rounds=int(state["max_rounds"]),
    )
    if theory_price is None:
        return None, None, None
    extractor = "seller" if theory_price == buyer else "buyer"
    return (
        theory_price,
        fairness_margin_price(seller, buyer, extractor=extractor),
        extractor,
    )


def negotiation_fairness_margin_action(game: dict[str, Any]) -> dict[str, Any]:
    """Apply the locked 15% surplus concession without changing the theory control."""
    state = game["game_state"]
    me = str(state["current_player"])
    role = str(state[f"{me}_role"])
    own_value = float(state[f"{me}_value"])
    if game["valid_actions"]["type"] == "decision":
        return _negotiation_decision(
            game,
            role,
            own_value,
            counter_policy=negotiation_fairness_margin_action,
        )
    _, fairness_price, _ = _negotiation_fairness_prices(game)
    return {"product_price": own_value if fairness_price is None else fairness_price}


def negotiation_fairness_margin_details(
    game: dict[str, Any], action: Mapping[str, Any]
) -> Mapping[str, Any]:
    theory_price, fairness_price, extractor = _negotiation_fairness_prices(game)
    return {
        "theory_offer": theory_price,
        "fairness_adjusted_offer": fairness_price,
        "selected_live_offer": action.get("product_price"),
        "selected_live_action": dict(action),
        "extractor": extractor,
        "surplus_concession": 0.15,
        "no_gains_from_trade": theory_price is None,
        "rule_invariants_satisfied": (
            theory_price is None
            or fairness_price is not None
            and min(float(game["game_state"]["player_1_value"]), float(game["game_state"]["player_2_value"]))
            <= fairness_price
            <= max(float(game["game_state"]["player_1_value"]), float(game["game_state"]["player_2_value"]))
        ),
    }


def bargaining_fairness_action(
    game: dict[str, Any], baseline_policy: Policy
) -> dict[str, Any]:
    """Apply the locked fairness concession to the incumbent's proposer share only."""
    theory_action = baseline_policy(game)
    if game["valid_actions"]["type"] != "offer":
        return theory_action
    state = game["game_state"]
    money = float(state["money_to_divide"])
    if money <= 0:
        raise PolicyInputsUnavailable("positive bargaining stake required")
    proposer = str(state["current_player"])
    theory_alice = float(theory_action["alice_gain"])
    theory_bob = float(theory_action["bob_gain"])
    proposer_share = theory_alice / money if proposer == "player_1" else theory_bob / money
    adjusted_proposer_share = fair_share(proposer_share)
    alice_share = (
        adjusted_proposer_share
        if proposer == "player_1"
        else 1 - adjusted_proposer_share
    )
    return {
        "alice_gain": money * alice_share,
        "bob_gain": money * (1 - alice_share),
    }


def bargaining_fairness_details(
    game: dict[str, Any],
    action: Mapping[str, Any],
    baseline_policy: Policy,
) -> Mapping[str, Any]:
    theory_action = baseline_policy(game)
    is_offer = game["valid_actions"]["type"] == "offer"
    return {
        "theory_offer": dict(theory_action) if is_offer else None,
        "fairness_adjusted_offer": dict(action) if is_offer else None,
        "selected_live_offer": dict(action) if is_offer else None,
        "selected_live_action": dict(action),
        "fairness_concession": 0.10,
        "rule_invariants_satisfied": (
            not is_offer
            or abs(float(action["alice_gain"]) + float(action["bob_gain"]) - float(game["game_state"]["money_to_divide"]))
            <= 1e-8
        ),
    }


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
    # A discrete prior's survival function changes only at support points, so an
    # optimum exists among V_A and the prior support. This finite candidate set is
    # justified by the prior itself and assumes no mechanism price ceiling/grid.
    candidates = tuple(sorted({own_value, *prior}))
    return {"product_price": bayes_optimal_posted_price(own_value, prior, candidates)}


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
    counter_price = float(counter["product_price"])
    if _negotiation_repeated_no_progress(
        game,
        me=str(state["current_player"]),
        offered=offered,
        counter=counter_price,
    ):
        return {"decision": "WalkAway"}
    return {"decision": "RejectOffer", "product_price": counter_price}


def _negotiation_repeated_no_progress(
    game: Mapping[str, Any], *, me: str, offered: float, counter: float
) -> bool:
    """Return true on a third identical pair for non-ROBUST negotiation incumbents."""
    state = game["game_state"]
    if state.get("horizon_known") is not False:
        return False
    fields = str(game.get("valid_actions", {}).get("fields", {})).lower()
    if "walkaway" not in fields:
        return False
    history = state.get("history", [])
    if not isinstance(history, Sequence):
        return False
    responses = [
        item
        for item in history
        if isinstance(item, Mapping) and str(item.get("decided_by", "")) == me
    ]
    if len(responses) < 2:
        return False
    for item in responses[-2:]:
        offer = item.get("offer")
        if (
            str(item.get("decision")) != "RejectOffer"
            or not isinstance(offer, Mapping)
            or float(offer.get("price", float("nan"))) != offered
            or float(item.get("counteroffer", float("nan"))) != counter
        ):
            return False
    return True


def bargaining_theory_action(game: dict[str, Any]) -> dict[str, Any]:
    state = game["game_state"]
    action_type = game["valid_actions"]["type"]
    money = float(state["money_to_divide"])
    if action_type == "decision":
        offer = state["last_offer"]
        me = str(state["current_player"])
        own = float(offer[f"{me}_gain"])
        complete = bool(state["complete_information"])
        if not complete:
            prior = state.get("opponent_delta_prior")
            if not isinstance(prior, Mapping):
                raise PolicyInputsUnavailable("incomplete bargaining prior unavailable")
            threshold = money / 2
        else:
            delta_alice = float(state["delta_1"])
            delta_bob = float(state["delta_2"])
            own_delta = delta_alice if me == "player_1" else delta_bob
            if bool(state["horizon_known"]):
                remaining = int(state["max_rounds"]) - int(state["round"]) + 1
                if remaining <= 1:
                    threshold = 0.0
                else:
                    alice, bob = finite_horizon_shares(delta_alice, delta_bob, remaining - 1)
                    next_proposer_share = alice[-1] if me == "player_1" else bob[-1]
                    threshold = money * own_delta * next_proposer_share
            else:
                opponent_delta = delta_bob if me == "player_1" else delta_alice
                threshold = money * own_delta * rubinstein_proposer_share(
                    own_delta, opponent_delta
                )
        decision = "accept" if own >= threshold else "reject"
        if decision == "reject" and _bargaining_repeated_no_progress(game, me=me):
            return {"decision": "walkaway"}
        return {"decision": decision}
    complete = bool(state["complete_information"])
    finite = bool(state["horizon_known"])
    if complete:
        if "delta_1" not in state or "delta_2" not in state:
            raise PolicyInputsUnavailable("complete bargaining discount factors unavailable")
        delta_alice = float(state["delta_1"])
        delta_bob = float(state["delta_2"])
        me = str(state["current_player"])
        if finite:
            remaining = int(state["max_rounds"]) - int(state.get("round", 1)) + 1
            alice = finite_horizon_offer_alice_share(
                delta_alice,
                delta_bob,
                remaining,
                proposer_is_alice=me == "player_1",
            )
        elif me == "player_1":
            alice = rubinstein_proposer_share(delta_alice, delta_bob)
        else:
            alice = 1 - rubinstein_proposer_share(delta_bob, delta_alice)
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


def bargaining_incomplete_equal_split_action(game: dict[str, Any]) -> dict[str, Any]:
    """Intentional conservative incumbent when the API withholds the theory prior."""
    state = game["game_state"]
    money = float(state["money_to_divide"])
    if game["valid_actions"]["type"] == "decision":
        me = str(state["current_player"])
        own = float(state["last_offer"][f"{me}_gain"])
        decision = "accept" if own >= money / 2 else "reject"
        if decision == "reject" and _bargaining_repeated_no_progress(game, me=me):
            return {"decision": "walkaway"}
        return {"decision": decision}
    return {"alice_gain": money / 2, "bob_gain": money / 2}


def _bargaining_split(offer: Mapping[str, Any]) -> tuple[float, float] | None:
    alice = offer.get("player_1_gain", offer.get("alice_gain"))
    bob = offer.get("player_2_gain", offer.get("bob_gain"))
    if isinstance(alice, (int, float)) and isinstance(bob, (int, float)):
        return float(alice), float(bob)
    return None


def _bargaining_repeated_no_progress(game: Mapping[str, Any], *, me: str) -> bool:
    """Return true on the third identical rejected offer in an unknown horizon."""
    state = game["game_state"]
    if state.get("horizon_known") is not False:
        return False
    fields = str(game.get("valid_actions", {}).get("fields", {})).lower()
    if "walkaway" not in fields:
        return False
    current = state.get("last_offer")
    current_split = _bargaining_split(current) if isinstance(current, Mapping) else None
    history = state.get("history", [])
    if current_split is None or not isinstance(history, Sequence):
        return False
    responses = [
        item
        for item in history
        if isinstance(item, Mapping)
        and str(item.get("proposer", "")) != me
        and str(item.get("decision", "")).lower() == "reject"
    ]
    if len(responses) < 2:
        return False
    return all(
        isinstance(item.get("offer"), Mapping)
        and _bargaining_split(item["offer"]) == current_split
        for item in responses[-2:]
    )


def persuasion_p0_action(game: dict[str, Any]) -> dict[str, Any]:
    state = game["game_state"]
    action_type = game["valid_actions"]["type"]
    if action_type == "seller_message":
        return {"message": "This product is available."}
    if action_type == "seller_recommendation":
        return {"decision": "yes"}
    if action_type == "buyer_decision":
        required = ("p", "v", "u", "product_price")
        if any(key not in state for key in required):
            raise PolicyInputsUnavailable("buyer expected-value inputs unavailable")
        expected_value = float(state["p"]) * float(state["v"]) + (
            1 - float(state["p"])
        ) * float(state["u"])
        return {
            "decision": (
                "yes"
                if production_buyer_buys(expected_value, float(state["product_price"]))
                else "no"
            )
        }
    raise UnsupportedCellError(f"unknown persuasion action {action_type!r}")

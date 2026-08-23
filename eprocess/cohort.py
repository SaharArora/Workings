"""Frozen experiment definitions for the post-risk-fix live cohort."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping

COHORT_ID = "POST_RISK_FIX_RANDOMIZED_3000"
FAMILY_CAP = 1_000
FAMILY_SUBCOHORT_IDS = {
    "bargaining": "POST_RISK_FIX_BARGAINING_1000",
    "negotiation": "POST_RISK_FIX_NEGOTIATION_1000",
    "persuasion": "POST_RISK_FIX_PERSUASION_1000",
}
ALPHA_FAMILY = 0.05
DELTA_MIN = 0.01
ASSIGNMENT_PROBABILITY = 0.5
PAYOFF_TRANSFORM_VERSION = "family_bounded_payoff_v1"
ASSIGNMENT_ALGORITHM = "system_csprng_bernoulli_half_atomic_sqlite_v1"


@dataclass(frozen=True, slots=True)
class ExperimentSpec:
    experiment_id: str
    family: str
    priority: int
    control_policy: str
    challenger_policy: str
    policy_version: str
    alpha_family: float
    multiplicity: int
    delta_min: float = DELTA_MIN
    assignment_probability: float = ASSIGNMENT_PROBABILITY

    @property
    def alpha_test(self) -> float:
        return self.alpha_family / self.multiplicity

    @property
    def promotion_threshold(self) -> float:
        return 1.0 / self.alpha_test

    def structured(self) -> dict[str, Any]:
        value = asdict(self)
        value.update(
            {
                "alpha_test": self.alpha_test,
                "promotion_threshold": self.promotion_threshold,
                "assignment_algorithm": ASSIGNMENT_ALGORITHM,
                "payoff_transform_version": PAYOFF_TRANSFORM_VERSION,
            }
        )
        return value


EXPERIMENTS = (
    ExperimentSpec(
        experiment_id="NEG_INCOMPLETE_IBO_VS_ROBUST",
        family="negotiation",
        priority=1,
        control_policy="NEGOTIATION_ROBUST",
        challenger_policy="NEGOTIATION_ADAPTIVE",
        policy_version="negotiation-adaptive-v1-concession-0.35-acceptance-0.90",
        alpha_family=ALPHA_FAMILY,
        multiplicity=2,
    ),
    ExperimentSpec(
        experiment_id="NEG_COMPLETE_FAIRNESS_MARGIN_VS_THEORY",
        family="negotiation",
        priority=2,
        control_policy="CONFIGURATION_SPECIFIC_THEORY",
        challenger_policy="NEGOTIATION_FAIRNESS_MARGIN",
        policy_version="negotiation-fairness-margin-v1-surplus-concession-0.15",
        alpha_family=ALPHA_FAMILY,
        multiplicity=2,
    ),
    ExperimentSpec(
        experiment_id="BARG_COMPLETE_FAIRNESS_VS_THEORY",
        family="bargaining",
        priority=1,
        control_policy="CONFIGURATION_SPECIFIC_THEORY",
        challenger_policy="BARGAINING_FAIRNESS",
        policy_version="bargaining-fairness-v1-concession-0.10",
        alpha_family=ALPHA_FAMILY,
        multiplicity=1,
    ),
    ExperimentSpec(
        experiment_id="PERS_BUY_MARGIN_VS_THEORY",
        family="persuasion",
        priority=1,
        control_policy="PERSUASION_BUY_THEORY",
        challenger_policy="PERSUASION_BUY_MARGIN",
        policy_version="persuasion-buyer-margin-v1-0.02",
        alpha_family=ALPHA_FAMILY,
        multiplicity=2,
    ),
    ExperimentSpec(
        experiment_id="PERS_SELL_EMPIRICAL_VS_P0",
        family="persuasion",
        priority=2,
        control_policy="PERSUASION_P0_BABBLING",
        challenger_policy="PERSUASION_POOLED_EMPIRICAL",
        policy_version="persuasion-pooled-empirical-v1",
        alpha_family=ALPHA_FAMILY,
        multiplicity=2,
    ),
)


def experiment_registry() -> tuple[ExperimentSpec, ...]:
    return EXPERIMENTS


def registry_payload() -> dict[str, Any]:
    return {
        "cohort_id": COHORT_ID,
        "family_caps": {
            "bargaining": FAMILY_CAP,
            "negotiation": FAMILY_CAP,
            "persuasion": FAMILY_CAP,
        },
        "family_subcohort_ids": dict(FAMILY_SUBCOHORT_IDS),
        "assignment_algorithm": ASSIGNMENT_ALGORITHM,
        "payoff_transform_version": PAYOFF_TRANSFORM_VERSION,
        "experiments": [item.structured() for item in EXPERIMENTS],
        "inactive_policies": [
            "NEGOTIATION_POOLED_EMPIRICAL",
            "RISK_SENSITIVE_POOLED_EMPIRICAL",
            "PERSUASION_P3_REPUTATION",
        ],
        "unsupported_experiments": {
            "NEG_INCOMPLETE_T1": "NO_SEPARATELY_VALID_ONE_SHOT_CHALLENGER",
            "BARG_INCOMPLETE_IBO_VS_STATIC": "NO_TESTED_INSTANCE_CONDITIONED_BARGAINING_CHALLENGER",
        },
    }


def registry_hash() -> str:
    encoded = json.dumps(registry_payload(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def role_for_game(game: Mapping[str, Any]) -> str:
    player = str(game.get("your_player") or game.get("game_state", {}).get("current_player") or "")
    family = str(game.get("game_family"))
    state = game.get("game_state", {})
    if family == "negotiation":
        return str(state.get(f"{player}_role", player or "unknown"))
    if family == "bargaining":
        return {"player_1": "alice", "player_2": "bob"}.get(player, player or "unknown")
    if family == "persuasion":
        return {"player_1": "seller", "player_2": "buyer"}.get(player, player or "unknown")
    return player or "unknown"


def family_subcohort_id(family: str) -> str:
    try:
        return FAMILY_SUBCOHORT_IDS[str(family)]
    except KeyError as exc:
        raise ValueError(f"unsupported cohort family {family!r}") from exc


def exact_configuration(game: Mapping[str, Any]) -> dict[str, Any]:
    state = game.get("game_state", {})
    family = str(game.get("game_family"))
    keys = {
        "negotiation": (
            "complete_information", "horizon_known", "max_rounds", "messages_allowed",
            "player_1_role", "player_2_role", "player_1_value", "player_2_value",
            "product_price_order",
        ),
        "bargaining": (
            "complete_information", "horizon_known", "max_rounds", "messages_allowed",
            "money_to_divide", "delta_1", "delta_2", "opponent_delta_prior",
        ),
        "persuasion": (
            "p", "v", "u", "product_price", "total_rounds", "seller_message_type",
            "is_seller_know_cv",
        ),
    }.get(family, ())
    return {key: state[key] for key in keys if key in state}


def opponent_category(game: Mapping[str, Any]) -> str:
    value = str(game.get("opponent", {}).get("type", "hidden")).lower()
    return value if value in {"human", "agent", "hidden"} else "hidden"


def _horizon(state: Mapping[str, Any]) -> str:
    if state.get("horizon_known") is False:
        return "unknown"
    rounds = state.get("max_rounds")
    return "T1" if rounds == 1 else "finite_multi_round"


def structural_cell(game: Mapping[str, Any]) -> str:
    family = str(game.get("game_family"))
    state = game.get("game_state", {})
    role = role_for_game(game)
    opponent = opponent_category(game)
    if family == "negotiation":
        payload = {
            "role": role,
            "information": "complete" if state.get("complete_information") else "incomplete",
            "horizon": _horizon(state),
            "messages": bool(state.get("messages_allowed")),
            "opponent": opponent,
        }
    elif family == "bargaining":
        payload = {
            "role": role,
            "information": "complete" if state.get("complete_information") else "incomplete",
            "horizon": "finite" if state.get("horizon_known") else "unlimited",
            "delta_1": state.get("delta_1"),
            "delta_2": state.get("delta_2"),
            "opponent": opponent,
        }
    elif family == "persuasion":
        prior = float(state.get("p", 0.5))
        prior_bucket = "low" if prior < 1 / 3 else "high" if prior > 2 / 3 else "middle"
        price = float(state.get("product_price", 0.0))
        if "v" in state and "u" in state:
            expected = prior * float(state["v"]) + (1 - prior) * float(state["u"])
            regime = "free" if price == 0 else "ev_above_price" if expected >= price else "ev_below_price"
        else:
            regime = "values_hidden"
        payload = {
            "role": role,
            "seller_knows_values": bool(state.get("is_seller_know_cv")),
            "message_type": state.get("seller_message_type"),
            "prior_bucket": prior_bucket,
            "price_value_regime": regime,
            "opponent": opponent,
        }
    else:
        raise ValueError(f"unsupported family {family!r}")
    return f"{family}:{json.dumps(payload, sort_keys=True, separators=(',', ':'))}"


def eligible_experiment_ids(game: Mapping[str, Any]) -> tuple[str, ...]:
    family = str(game.get("game_family"))
    state = game.get("game_state", {})
    role = role_for_game(game)
    eligible: list[str] = []
    if family == "negotiation":
        complete = state.get("complete_information") is True
        player = str(game.get("your_player", ""))
        own_value = state.get(f"{player}_value")
        robust_inputs = (
            isinstance(own_value, (int, float))
            and math.isfinite(float(own_value))
            and float(own_value) > 0
        )
        if (
            not complete
            and robust_inputs
            and (
                state.get("horizon_known") is False
                or (
                    isinstance(state.get("max_rounds"), int)
                    and int(state["max_rounds"]) > 1
                )
            )
        ):
            eligible.append("NEG_INCOMPLETE_IBO_VS_ROBUST")
        elif (
            complete
            and state.get("horizon_known") is True
            and isinstance(state.get("max_rounds"), int)
            and all(
                isinstance(state.get(key), (int, float))
                for key in ("player_1_value", "player_2_value")
            )
            and float(state["player_1_value"]) <= float(state["player_2_value"])
        ):
            eligible.append("NEG_COMPLETE_FAIRNESS_MARGIN_VS_THEORY")
    elif (
        family == "bargaining"
        and state.get("complete_information") is True
        and all(
            isinstance(state.get(key), (int, float))
            for key in ("money_to_divide", "delta_1", "delta_2")
        )
        and float(state["money_to_divide"]) > 0
    ):
        eligible.append("BARG_COMPLETE_FAIRNESS_VS_THEORY")
    elif family == "persuasion":
        required = ("p", "v", "u", "product_price", "total_rounds")
        valid_rounds = isinstance(state.get("total_rounds"), int) and int(
            state["total_rounds"]
        ) > 0
        if role == "buyer" and valid_rounds and all(key in state for key in required):
            eligible.append("PERS_BUY_MARGIN_VS_THEORY")
        elif (
            role == "seller"
            and valid_rounds
            and all(key in state for key in required)
            and isinstance(state.get("product_price"), (int, float))
            and float(state["product_price"]) > 0
        ):
            eligible.append("PERS_SELL_EMPIRICAL_VS_P0")
    priorities = {item.experiment_id: item.priority for item in EXPERIMENTS}
    return tuple(sorted(eligible, key=priorities.__getitem__))

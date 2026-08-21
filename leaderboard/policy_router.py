"""Route each server-assigned `(cell, opponent-category)` to its active policy."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from policies.persuasion.babbling import babbling_buyer_buys
from theory.bargaining.baselines import finite_horizon_alice_share, rubinstein_alice_share
from theory.negotiation.baselines import complete_information_price

Policy = Callable[[dict[str, Any]], dict[str, Any]]


def cell_key(game: Mapping[str, Any]) -> str:
    state = game["game_state"]
    family = game["game_family"]
    stable = {key: state.get(key) for key in (
        "complete_information", "horizon_known", "max_rounds", "messages_allowed",
        "seller_message_type", "is_seller_know_cv", "total_rounds", "p", "v", "u",
        "money_to_divide", "delta_1", "delta_2",
    ) if key in state}
    return f"{family}:{json.dumps(stable, sort_keys=True, separators=(',', ':'))}"


class PolicyRouter:
    def __init__(self, policy_map: Mapping[tuple[str, str], Policy] | None = None) -> None:
        self.policy_map = dict(policy_map or {})

    def decide(self, game: dict[str, Any]) -> dict[str, Any]:
        opponent = game.get("opponent", {}).get("type", "hidden")
        policy = self.policy_map.get((cell_key(game), opponent), theory_action)
        return policy(game)


def theory_action(game: dict[str, Any]) -> dict[str, Any]:
    family = game["game_family"]
    state, action_type = game["game_state"], game["valid_actions"]["type"]
    if family == "bargaining":
        if action_type == "decision":
            offer = state["last_offer"]
            own = float(offer[f"{state['current_player']}_gain"])
            return {"decision": "accept" if own >= float(state["money_to_divide"]) / 2 else "reject"}
        money = float(state["money_to_divide"])
        if state.get("complete_information") and "delta_1" in state and "delta_2" in state:
            if state.get("horizon_known"):
                alice = finite_horizon_alice_share(float(state["delta_1"]), float(state["delta_2"]), int(state["max_rounds"]))
            else:
                alice = rubinstein_alice_share(float(state["delta_1"]), float(state["delta_2"]))
        else:
            alice = 0.5
        return {"alice_gain": money * alice, "bob_gain": money * (1 - alice)}
    if family == "negotiation":
        me = state["current_player"]
        role = state[f"{me}_role"]
        own_value = float(state[f"{me}_value"])
        if action_type == "decision":
            offered = float(state["last_offer"]["price"])
            accept = offered >= own_value if role == "seller" else offered <= own_value
            if accept:
                return {"decision": "AcceptOffer"}
            fields = game["valid_actions"].get("fields", {})
            return ({"decision": "RejectOffer", "product_price": own_value}
                    if "product_price" in fields else {"decision": "RejectOffer"})
        if state.get("complete_information"):
            seller = float(state["player_1_value"]); buyer = float(state["player_2_value"])
            price = complete_information_price(seller, buyer, max_rounds=state.get("max_rounds"))
            return {"product_price": own_value if price is None else price}
        return {"product_price": own_value}
    if action_type in {"seller_message", "seller_recommendation"}:
        return {"message": "This product is available."} if action_type == "seller_message" else {"decision": "yes"}
    if action_type == "buyer_decision":
        return {"decision": "yes" if babbling_buyer_buys(float(state["p"]), float(state["v"])) else "no"}
    raise ValueError(f"Unsupported family/action: {family}/{action_type}")

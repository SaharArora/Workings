"""Documented representative live-shaped states for offline readiness audits."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def _negotiation(*, complete: bool, rounds: int | None, player: str, messages: bool) -> dict[str, Any]:
    role = "seller" if player == "player_1" else "buyer"
    state: dict[str, Any] = {
        "phase": "offer" if player == "player_1" else "decision",
        "current_player": player,
        "player_1_role": "seller",
        "player_2_role": "buyer",
        "complete_information": complete,
        "horizon_known": rounds is not None,
        "messages_allowed": messages,
        "round": 1,
        "history": [],
        "last_offer": None if player == "player_1" else {"price": 12, "from_player": "player_1", "round": 1},
    }
    if complete or role == "seller":
        state["player_1_value"] = 10.0
    if complete or role == "buyer":
        state["player_2_value"] = 20.0
    if rounds is not None:
        state["max_rounds"] = rounds
    if player == "player_1":
        action_type = "offer"
        fields: dict[str, Any] = {"product_price": "number"}
    else:
        action_type = "decision"
        fields = {"decision": {"values": ["AcceptOffer", "RejectOffer", "WalkAway"]}}
        if rounds != 1:
            fields["product_price"] = "number"
    if messages:
        fields["message"] = "string"
    return {
        "game_id": "latency-negotiation",
        "game_family": "negotiation",
        "your_player": player,
        "phase": state["phase"],
        "opponent": {"type": "hidden", "name": None},
        "game_state": state,
        "valid_actions": {"type": action_type, "fields": fields},
    }


def _bargaining(*, complete: bool, finite: bool, player: str, action_type: str) -> dict[str, Any]:
    state: dict[str, Any] = {
        "phase": action_type,
        "current_player": player,
        "proposer": player if action_type == "offer" else "player_1",
        "complete_information": complete,
        "horizon_known": finite,
        "messages_allowed": True,
        "money_to_divide": 100.0,
        "round": 1,
        "history": [],
        "last_offer": None if action_type == "offer" else {
            "player_1_gain": 50.0,
            "player_2_gain": 50.0,
            "proposer": "player_1",
            "round": 1,
        },
    }
    if finite:
        state["max_rounds"] = 10
    if complete or player == "player_1":
        state["delta_1"] = 0.9
    if complete or player == "player_2":
        state["delta_2"] = 0.8
    fields: dict[str, Any] = (
        {"alice_gain": "number", "bob_gain": "number"}
        if action_type == "offer"
        else {"decision": {"values": ["accept", "reject", "walkaway"]}}
    )
    fields["message"] = "string"
    return {
        "game_id": "latency-bargaining",
        "game_family": "bargaining",
        "your_player": player,
        "phase": action_type,
        "opponent": {"type": "agent", "name": "fixture"},
        "game_state": state,
        "valid_actions": {"type": action_type, "fields": fields},
    }


def _persuasion(action_type: str) -> dict[str, Any]:
    seller = action_type != "buyer_decision"
    state: dict[str, Any] = {
        "phase": "seller_message" if seller else "buyer_decision",
        "current_player": "player_1" if seller else "player_2",
        "p": 0.6,
        "product_price": 100.0,
        "seller_message_type": "text" if action_type == "seller_message" else "binary",
        "round": 1,
        "total_rounds": 10,
        "history": [],
    }
    if seller:
        state["current_quality"] = "high"
    else:
        state.update({"v": 200.0, "u": 0.0})
    fields = (
        {"message": "string"}
        if action_type == "seller_message"
        else {"decision": {"values": ["yes", "no"]}}
    )
    return {
        "game_id": "latency-persuasion",
        "game_family": "persuasion",
        "your_player": "player_1" if seller else "player_2",
        "phase": state["phase"],
        "opponent": {"type": "human", "name": "fixture"},
        "game_state": state,
        "valid_actions": {"type": action_type, "fields": fields},
    }


def representative_policy_games() -> dict[str, dict[str, Any]]:
    games = {
        "negotiation.complete.t1": _negotiation(complete=True, rounds=1, player="player_1", messages=True),
        "negotiation.complete.finite_odd": _negotiation(complete=True, rounds=3, player="player_1", messages=False),
        "negotiation.complete.finite_even": _negotiation(complete=True, rounds=10, player="player_2", messages=True),
        "negotiation.complete.unlimited": _negotiation(complete=True, rounds=None, player="player_1", messages=True),
        "negotiation.incomplete.t1.robust": _negotiation(complete=False, rounds=1, player="player_1", messages=False),
        "negotiation.incomplete.finite.robust": _negotiation(complete=False, rounds=10, player="player_2", messages=True),
        "negotiation.incomplete.unlimited.robust": _negotiation(complete=False, rounds=None, player="player_1", messages=True),
        "bargaining.complete.finite": _bargaining(complete=True, finite=True, player="player_1", action_type="offer"),
        "bargaining.complete.unlimited": _bargaining(complete=True, finite=False, player="player_2", action_type="offer"),
        "bargaining.incomplete.finite.equal_split": _bargaining(complete=False, finite=True, player="player_1", action_type="offer"),
        "bargaining.incomplete.unlimited.equal_split": _bargaining(complete=False, finite=False, player="player_2", action_type="decision"),
        "persuasion.p0.seller_text": _persuasion("seller_message"),
        "persuasion.p0.seller_binary": _persuasion("seller_recommendation"),
        "persuasion.p0.buyer": _persuasion("buyer_decision"),
    }
    return deepcopy(games)

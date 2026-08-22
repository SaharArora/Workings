from __future__ import annotations

import pytest

from glee.actions import ActionValidationError, validate_action


def game(family: str, action_type: str, fields: dict, state: dict) -> dict:
    return {
        "game_family": family,
        "game_state": state,
        "valid_actions": {"type": action_type, "fields": fields},
    }


def test_bargaining_offer_requires_exact_sum() -> None:
    payload = game(
        "bargaining",
        "offer",
        {"alice_gain": "number", "bob_gain": "number"},
        {"money_to_divide": 100},
    )
    assert validate_action({"alice_gain": 60, "bob_gain": 40}, payload)
    with pytest.raises(ActionValidationError, match="sum"):
        validate_action({"alice_gain": 60, "bob_gain": 39}, payload)


def test_negotiation_reject_counter_requires_advertised_price() -> None:
    terminal = game(
        "negotiation",
        "decision",
        {"decision": {"values": ["AcceptOffer", "RejectOffer", "WalkAway"]}},
        {},
    )
    with pytest.raises(ActionValidationError, match="not advertised"):
        validate_action({"decision": "RejectOffer", "product_price": 10}, terminal)


def test_message_is_sanitized_and_internal_limit_enforced() -> None:
    payload = game(
        "persuasion", "seller_message", {"message": "string"}, {}
    )
    result = validate_action({"message": "x" * 2_000}, payload)
    assert len(result["message"]) == 1_800


def test_nonfinite_or_negative_production_price_is_rejected() -> None:
    payload = game(
        "negotiation", "offer", {"product_price": "number"}, {}
    )
    for price in (float("inf"), float("nan"), -1):
        with pytest.raises(ActionValidationError):
            validate_action({"product_price": price}, payload)

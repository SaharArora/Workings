from __future__ import annotations

from glee.retry import INTERNAL_MESSAGE_LIMIT, fallback_action, never_raise


def test_never_raise_uses_final_round_rejection_without_counteroffer() -> None:
    game = {
        "game_family": "negotiation",
        "game_state": {},
        "valid_actions": {
            "type": "decision",
            "fields": {"decision": "'AcceptOffer', 'RejectOffer', or 'WalkAway'"},
        },
    }
    wrapped = never_raise(lambda _: 1 / 0)
    assert wrapped(game) == {"decision": "RejectOffer"}


def test_bargaining_fallback_is_even_split() -> None:
    game = {
        "game_family": "bargaining",
        "game_state": {"money_to_divide": 1000},
        "valid_actions": {"type": "offer", "fields": {}},
    }
    assert fallback_action(game) == {"alice_gain": 500, "bob_gain": 500}


def test_message_is_kept_below_server_limit() -> None:
    game = {
        "game_family": "persuasion",
        "game_state": {},
        "valid_actions": {"type": "seller_message", "fields": {}},
    }
    result = never_raise(lambda _: {"message": "x" * 3000})(game)
    assert len(result["message"]) == INTERNAL_MESSAGE_LIMIT

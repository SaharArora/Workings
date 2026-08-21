"""Strategy validation and never-raise fallbacks.

Network retry belongs to the verified official SDK. This module prevents local strategy
errors from consuming a move attempt. Legal action construction consults the current
``valid_actions`` payload rather than assuming a static family schema.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

logger = logging.getLogger(__name__)
INTERNAL_MESSAGE_LIMIT = 1_800


def _field_text(game: Mapping[str, Any]) -> str:
    fields = game.get("valid_actions", {}).get("fields", {})
    return " ".join(f"{key} {value}" for key, value in fields.items()).lower()


def fallback_action(game: Mapping[str, Any]) -> dict[str, Any]:
    """Return a conservative action allowed by the turn's advertised action type."""
    action_type = game["valid_actions"]["type"]
    state = game.get("game_state", {})
    fields = _field_text(game)
    if action_type == "decision":
        if "rejectoffer" in fields and "product_price" not in fields:
            return {"decision": "RejectOffer"}
        if "walkaway" in fields:
            return {"decision": "WalkAway"}
        if "rejectoffer" in fields:
            own_key = f"{state.get('current_player')}_value"
            price = state.get(own_key, state.get("last_offer", {}).get("price", 0))
            return {"decision": "RejectOffer", "product_price": price}
        if "acceptoffer" in fields:
            return {"decision": "AcceptOffer"}
        if "no" in fields:
            return {"decision": "no"}
    if action_type == "buyer_decision":
        return {"decision": "no"}
    if action_type == "seller_recommendation":
        return {"decision": "no"}
    if action_type == "seller_message":
        return {"message": "No recommendation."}
    if action_type == "offer":
        family = game.get("game_family")
        if family == "bargaining":
            money = float(state["money_to_divide"])
            return {"alice_gain": money / 2, "bob_gain": money / 2}
        own_key = f"{state.get('current_player')}_value"
        return {"product_price": state.get(own_key, 0)}
    raise ValueError(f"No safe fallback for advertised action type {action_type!r}")


def sanitize_action(action: Mapping[str, Any]) -> dict[str, Any]:
    clean = dict(action)
    if "message" in clean:
        clean["message"] = str(clean["message"])[:INTERNAL_MESSAGE_LIMIT]
    return clean


def never_raise(
    strategy: Callable[[dict[str, Any]], Mapping[str, Any]],
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Wrap the outermost move boundary with a deterministic legal fallback."""
    def wrapped(game: dict[str, Any]) -> dict[str, Any]:
        try:
            action = strategy(game)
            if not isinstance(action, Mapping):
                raise TypeError("strategy action must be a mapping")
            return sanitize_action(action)
        except Exception:
            logger.exception("Strategy failed; using valid-actions-derived fallback")
            return sanitize_action(fallback_action(game))

    return wrapped

"""Leaderboard-only rendering that cannot revise the economic action."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

INTERNAL_MESSAGE_LIMIT = 1_800


def render(action: Mapping[str, Any], game: Mapping[str, Any]) -> dict[str, Any]:
    """Attach language after the numeric/decision action is finalized."""
    rendered = dict(action)
    fields = game.get("valid_actions", {}).get("fields", {})
    if "message" not in fields:
        return rendered
    if "product_price" in rendered:
        message = f"I propose the stated price of {rendered['product_price']}."
    elif "alice_gain" in rendered:
        message = "I propose the stated allocation."
    else:
        message = "This is my stated decision."
    rendered["message"] = message[:INTERNAL_MESSAGE_LIMIT]
    return rendered

"""Production action-envelope validation against each turn's advertised schema."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from glee.retry import INTERNAL_MESSAGE_LIMIT, sanitize_action


class ActionValidationError(ValueError):
    """A locally generated action is unsafe to submit to the live API."""


def validate_game_envelope(game: Mapping[str, Any]) -> None:
    """Validate the stable payload envelope while preserving family-specific state."""
    for key in ("game_family", "game_state", "valid_actions"):
        if key not in game:
            raise ActionValidationError(f"missing game envelope field {key}")
    if not isinstance(game["game_state"], Mapping):
        raise ActionValidationError("game_state must be a mapping")
    valid = game["valid_actions"]
    if not isinstance(valid, Mapping) or not isinstance(valid.get("fields"), Mapping):
        raise ActionValidationError("valid_actions must contain a fields mapping")


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ActionValidationError(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ActionValidationError(f"{field} must be finite")
    return number


def _advertised_values(field: Any) -> set[str]:
    if isinstance(field, Mapping):
        values = field.get("values") or field.get("allowed_values") or field.get("enum")
        if isinstance(values, list):
            return {str(value).lower() for value in values}
    return set()


def validate_action(action: Mapping[str, Any], game: Mapping[str, Any]) -> dict[str, Any]:
    """Return a sanitized action or raise before the SDK can consume an attempt."""
    validate_game_envelope(game)
    if not isinstance(action, Mapping):
        raise ActionValidationError("action must be a mapping")
    clean = sanitize_action(action)
    action_type = str(game["valid_actions"]["type"])
    fields = game["valid_actions"]["fields"]
    advertised = set(fields)
    extras = set(clean) - advertised
    if extras:
        raise ActionValidationError(f"fields not advertised this turn: {sorted(extras)}")

    family = str(game["game_family"])
    state = game["game_state"]
    required: set[str]
    if action_type == "offer" and family == "bargaining":
        required = {"alice_gain", "bob_gain"}
        alice = _finite_number(clean.get("alice_gain"), "alice_gain")
        bob = _finite_number(clean.get("bob_gain"), "bob_gain")
        money = _finite_number(state.get("money_to_divide"), "money_to_divide")
        if not math.isclose(alice + bob, money, rel_tol=1e-12, abs_tol=1e-7):
            raise ActionValidationError("bargaining gains must sum to money_to_divide")
        if alice < 0 or bob < 0:
            raise ActionValidationError("bargaining gains must be nonnegative")
    elif action_type == "offer" and family == "negotiation":
        required = {"product_price"}
        if _finite_number(clean.get("product_price"), "product_price") < 0:
            raise ActionValidationError("production negotiation prices must be nonnegative")
    elif action_type in {"decision", "buyer_decision", "seller_recommendation"}:
        required = {"decision"}
        decision = str(clean.get("decision", ""))
        family_values = {
            "bargaining": {"accept", "reject", "walkaway"},
            "negotiation": {"AcceptOffer", "RejectOffer", "WalkAway"},
            "persuasion": {"yes", "no"},
        }.get(family, set())
        if decision not in family_values:
            raise ActionValidationError(f"invalid {family} decision {decision!r}")
        allowed = _advertised_values(fields.get("decision"))
        if allowed and decision.lower() not in allowed:
            raise ActionValidationError(f"decision {decision!r} is not advertised")
        if "product_price" in clean:
            if family != "negotiation" or _finite_number(clean["product_price"], "product_price") < 0:
                raise ActionValidationError("invalid counteroffer price")
    elif action_type == "seller_message":
        required = {"message"}
    else:
        raise ActionValidationError(f"unsupported advertised action type {action_type!r}")

    missing = required - set(clean)
    if missing:
        raise ActionValidationError(f"missing required action fields: {sorted(missing)}")
    if "message" in clean:
        if not isinstance(clean["message"], str) or len(clean["message"]) > INTERNAL_MESSAGE_LIMIT:
            raise ActionValidationError("message exceeds the production internal limit")
    return clean

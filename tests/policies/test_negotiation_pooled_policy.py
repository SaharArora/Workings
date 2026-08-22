from __future__ import annotations

from typing import Any

from policies.negotiation.pooled_empirical import pooled_empirical_action_plan


class PriceSensitiveModel:
    model_version = "test-model"

    def predict_acceptance(
        self, *, role: str, features: dict[str, float]
    ) -> tuple[float, tuple[str, ...]]:
        margin = features["proposal_margin"]
        if role == "seller":
            return (1.0 if margin <= 0.25 else 0.1), ()
        return (1.0 if margin <= 0.25 else 0.1), ()


def game(
    *,
    role: str,
    action_type: str = "offer",
    offer: float | None = None,
    history: list[dict[str, Any]] | None = None,
    continuation: bool = True,
) -> dict[str, Any]:
    me = "player_1" if role == "seller" else "player_2"
    opponent = "player_2" if role == "seller" else "player_1"
    state: dict[str, Any] = {
        "current_player": me,
        "player_1_role": "seller",
        "player_2_role": "buyer",
        f"{me}_value": 100,
        "complete_information": False,
        "horizon_known": False,
        "messages_allowed": False,
        "round": 3,
        "history": history or [],
        "last_offer": (
            {"from_player": opponent, "price": offer, "round": 3}
            if offer is not None
            else None
        ),
    }
    fields: dict[str, str]
    if action_type == "offer":
        fields = {"product_price": "number"}
    else:
        fields = {"decision": "AcceptOffer/RejectOffer/WalkAway"}
        if continuation:
            fields["product_price"] = "number"
    return {
        "game_id": "pooled-policy-test",
        "game_family": "negotiation",
        "your_player": me,
        "opponent": {"type": "agent", "name": "test"},
        "game_state": state,
        "valid_actions": {"type": action_type, "fields": fields},
    }


def test_seller_selects_finite_ir_candidate_by_model_value() -> None:
    plan = pooled_empirical_action_plan(game(role="seller"), PriceSensitiveModel())
    assert plan.action == {"product_price": 125}
    assert all(candidate.price >= 100 for candidate in plan.candidates)
    assert plan.structured()["rule_invariants_satisfied"]


def test_buyer_selects_finite_ir_candidate_by_model_value() -> None:
    plan = pooled_empirical_action_plan(game(role="buyer"), PriceSensitiveModel())
    assert plan.action == {"product_price": 75}
    assert all(0 <= candidate.price <= 100 for candidate in plan.candidates)


def test_immediate_ir_offer_can_dominate_counter_value() -> None:
    plan = pooled_empirical_action_plan(
        game(role="seller", action_type="decision", offer=140),
        PriceSensitiveModel(),
    )
    assert plan.action == {"decision": "AcceptOffer"}
    assert plan.current_offer_payoff == 40


def test_terminal_response_preserves_safe_ir_rule() -> None:
    accepted = pooled_empirical_action_plan(
        game(role="buyer", action_type="decision", offer=90, continuation=False),
        PriceSensitiveModel(),
    )
    rejected = pooled_empirical_action_plan(
        game(role="buyer", action_type="decision", offer=110, continuation=False),
        PriceSensitiveModel(),
    )
    assert accepted.action == {"decision": "AcceptOffer"}
    assert rejected.action == {"decision": "RejectOffer"}


def test_repeated_static_pair_uses_existing_walkaway_safety() -> None:
    response = {
        "decided_by": "player_1",
        "decision": "RejectOffer",
        "offer": {"from_player": "player_2", "price": 50},
        "counteroffer": 125,
    }
    plan = pooled_empirical_action_plan(
        game(
            role="seller",
            action_type="decision",
            offer=50,
            history=[response, response],
        ),
        PriceSensitiveModel(),
    )
    assert plan.action == {"decision": "WalkAway"}

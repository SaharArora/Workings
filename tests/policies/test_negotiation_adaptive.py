from __future__ import annotations

from typing import Any

import pytest

from policies.negotiation.adaptive import (
    ADAPTIVE_ACCEPTANCE_FRACTION,
    ADAPTIVE_CONCESSION_RATE,
    adaptive_action_plan,
)
from policies.negotiation.fairness_margin import (
    SURPLUS_CONCESSION,
    fairness_margin_price,
)


def adaptive_game(
    *,
    role: str,
    action_type: str,
    own_value: float = 100,
    offer: float | None = None,
    history: list[dict[str, Any]] | None = None,
    continuation: bool = True,
) -> dict[str, Any]:
    me = "player_1" if role == "seller" else "player_2"
    opponent = "player_2" if role == "seller" else "player_1"
    state = {
        "current_player": me,
        "player_1_role": "seller",
        "player_2_role": "buyer",
        f"{me}_value": own_value,
        "complete_information": False,
        "horizon_known": False,
        "round": 1,
        "history": history or [],
        "last_offer": (
            None
            if offer is None
            else {"price": offer, "from_player": opponent, "round": 1}
        ),
    }
    if action_type == "offer":
        fields: dict[str, Any] = {"product_price": "number"}
    else:
        fields = {"decision": "'AcceptOffer', 'RejectOffer', or 'WalkAway'"}
        if continuation:
            fields["product_price"] = "number required with RejectOffer"
    return {
        "game_id": "adaptive-test",
        "game_family": "negotiation",
        "your_player": me,
        "game_state": state,
        "valid_actions": {"type": action_type, "fields": fields},
    }


def prior_response(*, role: str, offer: float, counter: float) -> dict[str, Any]:
    me = "player_1" if role == "seller" else "player_2"
    opponent = "player_2" if role == "seller" else "player_1"
    return {
        "decision": "RejectOffer",
        "decided_by": me,
        "offer": {"price": offer, "from_player": opponent},
        "counteroffer": counter,
    }


def test_locked_adaptive_constants() -> None:
    assert ADAPTIVE_CONCESSION_RATE == 0.35
    assert ADAPTIVE_ACCEPTANCE_FRACTION == 0.90


def test_seller_first_proposal_is_static_robust_reference() -> None:
    plan = adaptive_action_plan(adaptive_game(role="seller", action_type="offer"))
    assert plan.robust_reference_price == 150
    assert plan.action == {"product_price": 150}


def test_buyer_first_proposal_is_static_robust_reference() -> None:
    plan = adaptive_action_plan(adaptive_game(role="buyer", action_type="offer"))
    assert plan.robust_reference_price == 50
    assert plan.action == {"product_price": 50}


def test_improving_seller_offer_causes_buyer_counter_to_move_upward() -> None:
    prior = prior_response(role="buyer", offer=90, counter=53.5)
    plan = adaptive_action_plan(
        adaptive_game(role="buyer", action_type="decision", offer=80, history=[prior])
    )
    assert plan.opponent_offer_improved
    assert plan.adaptive_counter == 57
    assert plan.adaptive_counter > 53.5


def test_improving_buyer_offer_causes_seller_counter_to_move_downward() -> None:
    prior = prior_response(role="seller", offer=110, counter=146.5)
    plan = adaptive_action_plan(
        adaptive_game(role="seller", action_type="decision", offer=120, history=[prior])
    )
    assert plan.opponent_offer_improved
    assert plan.adaptive_counter == 143
    assert plan.adaptive_counter < 146.5


def test_live_history_duplicate_of_current_counteroffer_is_not_its_own_baseline() -> None:
    prior = prior_response(role="seller", offer=110, counter=146.5)
    current_materialization = {
        "decision": "RejectOffer",
        "decided_by": "player_2",
        "offer": {"price": 146.5, "from_player": "player_1"},
        "counteroffer": 120,
    }
    plan = adaptive_action_plan(
        adaptive_game(
            role="seller",
            action_type="decision",
            offer=120,
            history=[prior, current_materialization],
        )
    )
    assert plan.previous_best_offer == 110
    assert plan.best_offer_seen == 120
    assert plan.opponent_offer_improved


@pytest.mark.parametrize(
    ("role", "offer"),
    (("seller", 1_000_000), ("buyer", -1_000_000)),
)
def test_adaptive_counter_never_violates_own_ir_bound(role: str, offer: float) -> None:
    plan = adaptive_action_plan(
        adaptive_game(role=role, action_type="decision", offer=offer)
    )
    assert plan.adaptive_counter is not None
    if role == "seller":
        assert plan.adaptive_counter >= plan.own_value
    else:
        assert plan.adaptive_counter <= plan.own_value


def test_terminal_accepts_any_individually_rational_offer() -> None:
    seller = adaptive_action_plan(
        adaptive_game(
            role="seller",
            action_type="decision",
            offer=100,
            continuation=False,
        )
    )
    buyer = adaptive_action_plan(
        adaptive_game(
            role="buyer",
            action_type="decision",
            offer=100,
            continuation=False,
        )
    )
    assert seller.action == {"decision": "AcceptOffer"}
    assert buyer.action == {"decision": "AcceptOffer"}


def test_nonterminal_acceptance_uses_90_percent_continuation_threshold() -> None:
    plan = adaptive_action_plan(
        adaptive_game(role="seller", action_type="decision", offer=147)
    )
    assert plan.current_payoff == 47
    assert plan.continuation_target_payoff == pytest.approx(33.55)
    assert plan.action == {"decision": "AcceptOffer"}


def test_nonterminal_rejects_and_submits_adaptive_counter_below_threshold() -> None:
    plan = adaptive_action_plan(
        adaptive_game(role="seller", action_type="decision", offer=120)
    )
    assert plan.current_payoff == 20
    assert plan.continuation_target_payoff == 43
    assert plan.action == {"decision": "RejectOffer", "product_price": 143}


def test_improving_offers_do_not_trigger_no_progress_walkaway() -> None:
    history = [
        prior_response(role="seller", offer=110, counter=146.5),
        prior_response(role="seller", offer=115, counter=144.75),
    ]
    plan = adaptive_action_plan(
        adaptive_game(role="seller", action_type="decision", offer=120, history=history)
    )
    assert plan.opponent_offer_improved
    assert plan.action == {"decision": "RejectOffer", "product_price": 143}


def test_static_no_improvement_loop_eventually_triggers_structural_guard() -> None:
    repeated = prior_response(role="seller", offer=50, counter=150)
    plan = adaptive_action_plan(
        adaptive_game(
            role="seller",
            action_type="decision",
            offer=50,
            history=[repeated, repeated],
        )
    )
    assert plan.action == {"decision": "WalkAway"}
    assert plan.decision_rule == "WALK_AWAY_AFTER_STRUCTURAL_ADAPTIVE_NO_PROGRESS"


def test_complete_information_seller_extractor_concedes_exactly_15_percent() -> None:
    price = fairness_margin_price(10, 20, extractor="seller")
    assert SURPLUS_CONCESSION == 0.15
    assert price == 18.5
    assert 20 - price == pytest.approx(0.15 * (20 - 10))


def test_complete_information_buyer_extractor_concedes_exactly_15_percent() -> None:
    price = fairness_margin_price(10, 20, extractor="buyer")
    assert price == 11.5
    assert price - 10 == pytest.approx(0.15 * (20 - 10))


def test_complete_information_no_gains_from_trade_remains_no_trade() -> None:
    assert fairness_margin_price(20, 10, extractor="seller") is None
    assert fairness_margin_price(20, 10, extractor="buyer") is None

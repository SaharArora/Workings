import pytest

from policies.negotiation.anchor_favorable import own_favorable_price
from policies.negotiation.bayes import BayesEligibility, BayesPricingPolicy
from policies.negotiation.empirical import FrozenEmpiricalModel
from policies.negotiation.empirical_correction import inferred_buyer_value, inferred_seller_value
from policies.negotiation.fairness_margin import fairness_margin_price
from policies.negotiation.robust import (
    RobustScaleUnavailable,
    buyer_candidate_prices,
    minimax_regret_price,
    robust_action_plan,
    robust_price_decision,
    seller_candidate_prices,
)


def test_robust_minimax_regret_uses_whole_grid() -> None:
    assert minimax_regret_price(role="seller", own_value=0, legal_prices=[1, 2, 3, 4, 5], opponent_values=[1, 2, 3, 4, 5]) == 3
    assert minimax_regret_price(role="seller", own_value=0, legal_prices=[1, 2, 3, 4, 5], opponent_values=[1, 4, 4, 5, 5]) == 4


def test_unbounded_domain_robust_policy_candidate_grids() -> None:
    seller = seller_candidate_prices(100)
    buyer = buyer_candidate_prices(100)
    assert seller == (100, 110, 125, 150, 200)
    assert buyer == (0, 25, 50, 75, 100)
    assert max(seller) <= 2 * 100
    assert max(buyer) <= 100


def test_positive_verified_legal_minimum_only_clamps_policy_candidates_upward() -> None:
    assert seller_candidate_prices(100, legal_price_min=120) == (120, 125, 150, 200)
    assert buyer_candidate_prices(100, legal_price_min=30) == (30, 50, 75, 100)


def test_unbounded_domain_robust_regret_and_tie_break_by_hand() -> None:
    seller = robust_price_decision(role="seller", own_value=100)
    buyer = robust_price_decision(role="buyer", own_value=100)
    assert [(item.price, item.maximum_regret) for item in seller.candidate_regrets] == [
        (100, 100), (110, 90), (125, 75), (150, 50), (200, 50),
    ]
    assert seller.chosen_price == 150  # Tie at 150/200: lower seller price wins.
    assert [(item.price, item.maximum_regret) for item in buyer.candidate_regrets] == [
        (0, 75), (25, 50), (50, 50), (75, 75), (100, 100),
    ]
    assert buyer.chosen_price == 50  # Tie at 25/50: higher buyer offer wins.


def test_robust_zero_value_without_verified_scale_fails_closed() -> None:
    with pytest.raises(RobustScaleUnavailable, match="ROBUST_SCALE_UNAVAILABLE"):
        seller_candidate_prices(0)
    with pytest.raises(RobustScaleUnavailable, match="ROBUST_SCALE_UNAVAILABLE"):
        buyer_candidate_prices(0)


def test_robust_decision_uses_explicit_continuation_reference() -> None:
    game = {
        "game_family": "negotiation",
        "game_state": {
            "current_player": "player_1",
            "player_1_role": "seller",
            "player_1_value": 100,
            "last_offer": {"price": 125},
        },
        "valid_actions": {
            "type": "decision",
            "fields": {
                "decision": "'AcceptOffer', 'RejectOffer', or 'WalkAway'",
                "product_price": "number required with RejectOffer",
            },
        },
    }
    plan = robust_action_plan(game)
    assert plan.individually_rational
    assert plan.action == {"decision": "RejectOffer", "product_price": 150}
    game["game_state"]["last_offer"] = {"price": 160}
    assert robust_action_plan(game).action == {"decision": "AcceptOffer"}


def test_robust_terminal_decision_accepts_ir_and_rejects_non_ir() -> None:
    game = {
        "game_family": "negotiation",
        "game_state": {
            "current_player": "player_2",
            "player_2_role": "buyer",
            "player_2_value": 100,
            "last_offer": {"price": 90},
        },
        "valid_actions": {
            "type": "decision",
            "fields": {"decision": "'AcceptOffer', 'RejectOffer', or 'WalkAway'"},
        },
    }
    assert robust_action_plan(game).action == {"decision": "AcceptOffer"}
    game["game_state"]["last_offer"] = {"price": 110}
    assert robust_action_plan(game).action == {"decision": "RejectOffer"}


def test_bayes_eligibility_and_posterior() -> None:
    assert BayesEligibility(200, 0.10, True).eligible
    policy = BayesPricingPolicy({10: 0.5, 20: 0.5}, lambda value, price, history: 0.9 if value < price else 0.1)
    policy.update_rejection(15, (), True)
    assert policy.posterior[10] == pytest.approx(0.9)


def test_empirical_uses_ood_penalty() -> None:
    model = FrozenEmpiricalModel("v1", lambda price, history: price, lambda price, history: 100 if price == 3 else 0)
    assert model.choose([1, 2, 3], ()) == 2


def test_locked_price_deviations() -> None:
    assert fairness_margin_price(10, 20, extractor="seller") == 18.5
    assert fairness_margin_price(10, 20, extractor="buyer") == 11.5
    assert own_favorable_price(10, 20, role="seller") == 16.5
    assert own_favorable_price(10, 20, role="buyer") == 13.5
    assert inferred_buyer_value(12.5) == 10
    assert inferred_seller_value(15) == 10

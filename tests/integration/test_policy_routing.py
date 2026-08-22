from __future__ import annotations

from typing import Any

from leaderboard.policy_router import PolicyArtifact, PolicyRouter, cell_key
from policies.negotiation.bayes import BayesEligibility


def negotiation_game(*, complete: bool, rounds: int | None) -> dict[str, Any]:
    state: dict[str, Any] = {
        "phase": "offer",
        "current_player": "player_1",
        "player_1_role": "seller",
        "player_2_role": "buyer",
        "player_1_value": 10.0,
        "complete_information": complete,
        "horizon_known": rounds is not None,
        "messages_allowed": True,
        "round": 1,
        "last_offer": None,
    }
    if complete:
        state["player_2_value"] = 20.0
    if rounds is not None:
        state["max_rounds"] = rounds
    return {
        "game_id": "g",
        "game_family": "negotiation",
        "your_player": "player_1",
        "phase": "offer",
        "opponent": {"type": "hidden", "name": None},
        "game_state": state,
        "valid_actions": {"type": "offer", "fields": {"product_price": "number"}},
    }


def bargaining_game() -> dict[str, Any]:
    return {
        "game_id": "b", "game_family": "bargaining", "your_player": "player_1",
        "phase": "offer", "opponent": {"type": "agent", "name": "x"},
        "game_state": {"phase": "offer", "current_player": "player_1",
            "complete_information": True, "horizon_known": True, "max_rounds": 3,
            "messages_allowed": False, "money_to_divide": 100, "delta_1": 0.9, "delta_2": 0.8},
        "valid_actions": {"type": "offer", "fields": {"alice_gain": "number", "bob_gain": "number"}},
    }


def persuasion_game() -> dict[str, Any]:
    return {
        "game_id": "p", "game_family": "persuasion", "your_player": "player_2",
        "phase": "buyer_decision", "opponent": {"type": "human", "name": "h"},
        "game_state": {"phase": "buyer_decision", "p": 0.4, "v": 2.0, "u": 0,
            "total_rounds": 10, "round": 1, "product_price": 1},
        "valid_actions": {"type": "buyer_decision", "fields": {"decision": "yes or no"}},
    }


def direct_policy(price: float):
    return lambda game: {"product_price": price}


def route_key(game: dict[str, Any]) -> tuple[str, str]:
    return cell_key(game), game["opponent"]["type"]


def test_complete_information_t1_uses_its_theory_baseline() -> None:
    route = PolicyRouter().route(negotiation_game(complete=True, rounds=1))
    assert route.selected_policy == "NEGOTIATION_COMPLETE_T1_THEORY"
    assert route.theory_baseline == route.selected_policy


def test_complete_information_even_horizon_uses_buyer_terminal_theory() -> None:
    route = PolicyRouter().route(negotiation_game(complete=True, rounds=10))
    assert route.selected_policy == "NEGOTIATION_COMPLETE_FINITE_EVEN_THEORY"


def test_complete_unknown_horizon_theory_has_intentional_no_progress_exit() -> None:
    game = negotiation_game(complete=True, rounds=None)
    repeated = {
        "decision": "RejectOffer",
        "decided_by": "player_1",
        "offer": {"price": 8},
        "counteroffer": 15,
    }
    game["phase"] = "decision"
    game["game_state"].update(
        {
            "phase": "decision",
            "current_player": "player_1",
            "last_offer": {"price": 8},
            "history": [repeated, repeated],
        }
    )
    game["valid_actions"] = {
        "type": "decision",
        "fields": {
            "decision": "'AcceptOffer', 'RejectOffer', or 'WalkAway'",
            "product_price": "number required with RejectOffer",
        },
    }
    action, route = PolicyRouter().decide_with_routing(game)
    assert route.selected_policy == "NEGOTIATION_COMPLETE_UNLIMITED_MIDPOINT"
    assert route.execution_fallback_reason is None
    assert action == {"decision": "WalkAway"}


def test_underdetermined_bayes_eligible_with_artifact_selects_bayes() -> None:
    game = negotiation_game(complete=False, rounds=10)
    key = route_key(game)
    router = PolicyRouter(
        bayes_eligibility={key: BayesEligibility(200, 0.1, True)},
        bayes_artifacts={key: PolicyArtifact.from_policy("bayes-v1", direct_policy(12))},
    )
    route = router.route(game)
    assert route.selected_policy == "NEGOTIATION_BAYES"
    assert route.bayes_eligible is True
    assert route.available_policy_artifacts == ("bayes-v1",)


def test_underdetermined_multi_round_bayes_ineligible_selects_robust() -> None:
    game = negotiation_game(complete=False, rounds=10)
    key = route_key(game)
    route = PolicyRouter(
        bayes_eligibility={key: BayesEligibility(199, 0.2, False)}
    ).route(game)
    assert route.selected_policy == "NEGOTIATION_ROBUST"
    assert route.fallback_reason == "BAYES_INELIGIBLE"


def test_underdetermined_unknown_horizon_bayes_ineligible_selects_robust() -> None:
    game = negotiation_game(complete=False, rounds=None)
    key = route_key(game)
    route = PolicyRouter(
        bayes_eligibility={key: BayesEligibility(500, 0.05, False)}
    ).route(game)
    assert route.selected_policy == "NEGOTIATION_ROBUST"
    assert route.theory_baseline == "NEGOTIATION_INCOMPLETE_MULTIROUND_PORTFOLIO"


def test_missing_eligibility_record_selects_robust_without_claiming_ineligible() -> None:
    route = PolicyRouter().route(negotiation_game(complete=False, rounds=None))
    assert route.selected_policy == "NEGOTIATION_ROBUST"
    assert route.bayes_eligible is None
    assert route.fallback_reason == "BAYES_ELIGIBILITY_UNAVAILABLE"


def test_robust_runs_without_finite_legal_price_maximum() -> None:
    game = negotiation_game(complete=False, rounds=None)
    action, route = PolicyRouter().decide_with_routing(game)
    assert route.selected_policy == "NEGOTIATION_ROBUST"
    assert route.execution_fallback_reason is None
    assert action == {"product_price": 15.0}


def test_incomplete_t1_explicit_discrete_prior_uses_its_support_not_a_price_grid() -> None:
    game = negotiation_game(complete=False, rounds=1)
    game["game_state"]["opponent_value_prior"] = {12: 0.5, 15: 0.5}
    action, route = PolicyRouter().decide_with_routing(game)
    assert route.selected_policy == "NEGOTIATION_INCOMPLETE_T1_BAYES_POSTED_PRICE"
    assert route.execution_fallback_reason is None
    assert action == {"product_price": 15.0}


def test_robust_zero_value_logs_scale_unavailable_and_fails_closed() -> None:
    game = negotiation_game(complete=False, rounds=None)
    game["game_state"]["player_1_value"] = 0
    action, route = PolicyRouter().decide_with_routing(game)
    assert route.selected_policy == "NEGOTIATION_ROBUST"
    assert "ROBUST_SCALE_UNAVAILABLE" in route.execution_fallback_reason
    assert action == {"product_price": 0}


def test_empirical_unavailable_does_not_displace_robust() -> None:
    route = PolicyRouter().route(negotiation_game(complete=False, rounds=10))
    assert route.promoted_policy is None
    assert route.selected_policy == "NEGOTIATION_ROBUST"


def test_bargaining_clean_cell_keeps_configuration_theory() -> None:
    route = PolicyRouter().route(bargaining_game())
    assert route.selected_policy == "BARGAINING_COMPLETE_FINITE"


def test_incomplete_bargaining_unknown_horizon_has_named_no_progress_exit() -> None:
    game = bargaining_game()
    game["game_state"].update(
        {
            "complete_information": False,
            "horizon_known": False,
            "current_player": "player_2",
            "last_offer": {"player_1_gain": 80, "player_2_gain": 20},
            "history": [
                {
                    "proposer": "player_1",
                    "offer": {"player_1_gain": 80, "player_2_gain": 20},
                    "decision": "reject",
                },
                {
                    "proposer": "player_1",
                    "offer": {"player_1_gain": 80, "player_2_gain": 20},
                    "decision": "reject",
                },
            ],
        }
    )
    game["game_state"].pop("max_rounds")
    game["game_state"].pop("delta_1")
    game["valid_actions"] = {
        "type": "decision",
        "fields": {"decision": "'accept', 'reject', or 'walkaway'"},
    }
    action, route = PolicyRouter().decide_with_routing(game)
    assert route.selected_policy == "BARGAINING_INCOMPLETE_EQUAL_SPLIT"
    assert route.execution_fallback_reason is None
    assert action == {"decision": "walkaway"}


def test_persuasion_no_commitment_keeps_p0() -> None:
    route = PolicyRouter().route(persuasion_game())
    assert route.selected_policy == "PERSUASION_P0_BABBLING"


def test_promoted_challenger_overrides_incumbent_deliberately() -> None:
    game = bargaining_game()
    key = route_key(game)
    router = PolicyRouter(
        promoted_policies={key: PolicyArtifact.from_policy("fairness-promoted-v1", lambda _: {"alice_gain": 55, "bob_gain": 45})}
    )
    route = router.route(game)
    assert route.promoted_policy == "fairness-promoted-v1"
    assert route.selected_policy == "fairness-promoted-v1"


def test_missing_or_corrupt_bayes_artifact_falls_back_to_robust() -> None:
    game = negotiation_game(complete=False, rounds=10)
    key = route_key(game)
    eligibility = {key: BayesEligibility(500, 0.5, True)}
    missing = PolicyRouter(bayes_eligibility=eligibility).route(game)
    assert missing.selected_policy == "NEGOTIATION_ROBUST"
    assert missing.fallback_reason == "BAYES_ARTIFACT_MISSING"

    def corrupt():
        raise ValueError("bad artifact")

    broken = PolicyRouter(
        bayes_eligibility=eligibility,
        bayes_artifacts={key: PolicyArtifact("bayes-corrupt", corrupt)},
    ).route(game)
    assert broken.selected_policy == "NEGOTIATION_ROBUST"
    assert broken.fallback_reason == "BAYES_ARTIFACT_CORRUPT"


def test_unrecognized_cell_fails_closed_and_logs_structured_route() -> None:
    game = {
        "game_id": "x", "game_family": "mystery", "your_player": "player_1",
        "opponent": {"type": "hidden", "name": None}, "game_state": {},
        "valid_actions": {"type": "decision", "fields": {"decision": "no"}},
    }
    router = PolicyRouter()
    action, route = router.decide_with_routing(game)
    assert action == {"decision": "no"}
    assert route.selected_policy == "SAFE_LEGAL_FALLBACK"
    assert route.fallback_reason.startswith("UNSUPPORTED_CELL")
    assert set(route.structured()) >= {
        "game_family", "cell", "role", "theory_baseline", "bayes_eligible",
        "available_policy_artifacts", "promoted_policy", "selected_policy", "fallback_reason",
    }

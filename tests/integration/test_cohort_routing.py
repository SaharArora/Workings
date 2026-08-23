from __future__ import annotations

from pathlib import Path
from time import perf_counter

from eprocess.store import CohortStore
from leaderboard.cohort_overrides import (
    COHORT_AUTHORIZATION_SOURCE,
    CohortOverrideRegistry,
)
from leaderboard.policy_router import PolicyArtifact, PolicyRouter
from policies.persuasion.pooled_empirical import PooledPersuasionPolicy
from research.evaluation.latency import POLICY_MAX_BUDGET_SECONDS


def negotiation_game(game_id: str, *, complete: bool) -> dict:
    return {
        "game_id": game_id,
        "game_family": "negotiation",
        "your_player": "player_1",
        "opponent": {"type": "hidden", "name": None},
        "phase": "offer",
        "game_state": {
            "complete_information": complete,
            "horizon_known": True,
            "max_rounds": 10,
            "messages_allowed": False,
            "round": 1,
            "current_player": "player_1",
            "player_1_role": "seller",
            "player_2_role": "buyer",
            "player_1_value": 10,
            "player_2_value": 20,
            "history": [],
        },
        "valid_actions": {
            "type": "offer",
            "fields": {"product_price": "number"},
        },
    }


def bargaining_game(game_id: str) -> dict:
    return {
        "game_id": game_id,
        "game_family": "bargaining",
        "your_player": "player_1",
        "opponent": {"type": "agent", "name": "opponent"},
        "phase": "offer",
        "game_state": {
            "complete_information": True,
            "horizon_known": True,
            "max_rounds": 10,
            "round": 1,
            "current_player": "player_1",
            "money_to_divide": 100,
            "delta_1": 0.9,
            "delta_2": 0.8,
            "history": [],
        },
        "valid_actions": {
            "type": "offer",
            "fields": {"alice_gain": "number", "bob_gain": "number"},
        },
    }


def persuasion_game(game_id: str, *, seller: bool) -> dict:
    game = {
        "game_id": game_id,
        "game_family": "persuasion",
        "your_player": "player_1" if seller else "player_2",
        "opponent": {"type": "hidden", "name": None},
        "game_state": {
            "p": 0.5,
            "v": 202,
            "u": 0,
            "product_price": 100,
            "total_rounds": 20,
            "seller_message_type": "binary",
            "is_seller_know_cv": True,
            "round": 1,
            "current_player": "player_1" if seller else "player_2",
            "history": [],
        },
    }
    if seller:
        game.update(
            {
                "phase": "seller_recommendation",
                "valid_actions": {
                    "type": "seller_recommendation",
                    "fields": {"decision": "yes or no"},
                },
            }
        )
    else:
        game.update(
            {
                "phase": "buyer_decision",
                "valid_actions": {
                    "type": "buyer_decision",
                    "fields": {"decision": "yes or no"},
                },
            }
        )
    return game


def make_store(tmp_path: Path, *, arm: str | None = None) -> CohortStore:
    draw = None if arm is None else (lambda spec, game_id, cell: arm)
    store = CohortStore(
        tmp_path / "cohort.sqlite3", frozen_commit="frozen", arm_draw=draw
    )
    store.initialize()
    return store


def test_negotiation_assignment_routes_to_exact_frozen_arm(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    registry = CohortOverrideRegistry(store)
    router = PolicyRouter(experimental_overrides=registry)
    game = negotiation_game("neg-incomplete", complete=False)
    action, route = router.decide_with_routing(game)
    assignment = store.assignment(game["game_id"])
    assert assignment is not None
    assert assignment.experiment_id == "NEG_INCOMPLETE_IBO_VS_ROBUST"
    assert route.selected_policy == assignment.assigned_policy
    assert route.authorization_source == COHORT_AUTHORIZATION_SOURCE
    assert action["product_price"] >= 0


def test_configuration_theory_and_fairness_arms_both_use_defined_policy(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    router = PolicyRouter(experimental_overrides=CohortOverrideRegistry(store))
    game = negotiation_game("neg-complete", complete=True)
    action, route = router.decide_with_routing(game)
    assignment = store.assignment(game["game_id"])
    assert assignment is not None
    assert assignment.experiment_id == "NEG_COMPLETE_FAIRNESS_MARGIN_VS_THEORY"
    assert route.selected_policy == assignment.assigned_policy
    assert route.selected_policy in {
        "CONFIGURATION_SPECIFIC_THEORY",
        "NEGOTIATION_FAIRNESS_MARGIN",
    }
    assert 10 <= action["product_price"] <= 20


def test_bargaining_routes_to_atomic_control_or_fairness_arm(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    router = PolicyRouter(experimental_overrides=CohortOverrideRegistry(store))
    game = bargaining_game("barg")
    action, route = router.decide_with_routing(game)
    assignment = store.assignment(game["game_id"])
    assert assignment is not None
    assert route.selected_policy == assignment.assigned_policy
    assert action["alice_gain"] + action["bob_gain"] == 100


def test_promoted_challenger_runs_observationally_without_more_randomization(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    with store._connect() as connection:
        connection.execute(
            "UPDATE experiments SET status='PROMOTE' WHERE experiment_id=?",
            ("BARG_COMPLETE_FAIRNESS_VS_THEORY",),
        )
    router = PolicyRouter(experimental_overrides=CohortOverrideRegistry(store))
    game = bargaining_game("promoted-bargaining")
    _, route = router.decide_with_routing(game)
    assignment = store.assignment(game["game_id"])
    assert assignment is not None and assignment.experiment_id is None
    assert assignment.evidence_class == "OBSERVATIONAL_LIVE_EVIDENCE"
    assert route.selected_policy == "BARGAINING_FAIRNESS"
    assert route.authorization_status == "E_PROCESS_PROMOTED"


def test_buyer_experiment_uses_theory_or_locked_margin_for_whole_game(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    router = PolicyRouter(experimental_overrides=CohortOverrideRegistry(store))
    game = persuasion_game("buyer", seller=False)
    action, route = router.decide_with_routing(game)
    assignment = store.assignment(game["game_id"])
    assert assignment is not None and assignment.informative is True
    assert route.selected_policy == assignment.assigned_policy
    expected = "yes" if assignment.assigned_policy == "PERSUASION_BUY_THEORY" else "no"
    assert action == {"decision": expected}
    game["game_state"]["history"] = [{"buyer_decision": action["decision"]}]
    game["game_state"]["round"] = 2
    assert router.route(game).selected_policy == assignment.assigned_policy


def _challenger_seller_game(store: CohortStore) -> dict:
    for index in range(100):
        game = persuasion_game(f"seller-{index}", seller=True)
        assignment = store.assign_game(
            game, baseline_policy="PERSUASION_P0_BABBLING"
        )
        if assignment.assigned_policy == "PERSUASION_POOLED_EMPIRICAL":
            return game
    raise AssertionError("deterministic half assignment produced no challenger")


def test_ready_persuasion_seller_artifact_routes_without_p3(tmp_path: Path) -> None:
    store = make_store(tmp_path, arm="challenger")
    game = _challenger_seller_game(store)
    artifact_path = Path("research/artifacts/persuasion_pooled_empirical_v1.json")
    router = PolicyRouter(
        experimental_overrides=CohortOverrideRegistry(store),
        pooled_persuasion_artifact=PolicyArtifact(
            "persuasion-pooled-empirical-v1",
            lambda: PooledPersuasionPolicy(artifact_path),
        ),
    )
    action, route = router.decide_with_routing(game)
    assert route.selected_policy == "PERSUASION_POOLED_EMPIRICAL"
    assert route.experimental_policy == "PERSUASION_POOLED_EMPIRICAL"
    assert "persuasion-pooled-empirical-v1" in route.available_policy_artifacts
    assert route.policy_details["uses_p3_trust_artifact"] is False
    assert action["decision"] in {"yes", "no"}
    started = perf_counter()
    for _ in range(100):
        repeated_action, repeated_route = router.decide_with_routing(game)
        assert repeated_route.execution_fallback_reason is None
        assert repeated_action["decision"] in {"yes", "no"}
    assert perf_counter() - started < POLICY_MAX_BUDGET_SECONDS


def test_missing_seller_artifact_keeps_p0_and_exposes_failure(tmp_path: Path) -> None:
    store = make_store(tmp_path, arm="challenger")
    game = _challenger_seller_game(store)
    route = PolicyRouter(
        experimental_overrides=CohortOverrideRegistry(store)
    ).route(game)
    assert route.selected_policy == "PERSUASION_P0_BABBLING"
    assert "PERSUASION_POOLED_ARTIFACT_MISSING" in str(route.fallback_reason)

from __future__ import annotations

import sqlite3
import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from eprocess.cohort import (
    COHORT_ID,
    FAMILY_SUBCOHORT_IDS,
    eligible_experiment_ids,
    experiment_registry,
    registry_hash,
)
from eprocess.store import CohortStore
from leaderboard.cohort_overrides import CohortOverrideRegistry


def bargaining_game(game_id: str = "b-1") -> dict:
    return {
        "game_id": game_id,
        "game_family": "bargaining",
        "your_player": "player_1",
        "opponent": {"type": "hidden", "name": None},
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


def persuasion_buyer_game(game_id: str = "p-1", *, high: float = 202) -> dict:
    return {
        "game_id": game_id,
        "game_family": "persuasion",
        "your_player": "player_2",
        "opponent": {"type": "agent", "name": "opponent"},
        "game_state": {
            "p": 0.5,
            "v": high,
            "u": 0,
            "product_price": 100,
            "total_rounds": 20,
            "seller_message_type": "binary",
            "is_seller_know_cv": False,
            "round": 1,
            "current_quality": "high",
            "seller_message": "yes",
            "history": [],
        },
        "valid_actions": {
            "type": "buyer_decision",
            "fields": {"decision": "yes or no"},
        },
    }


@pytest.fixture
def store(tmp_path: Path) -> CohortStore:
    value = CohortStore(tmp_path / "cohort.sqlite3", frozen_commit="abc123")
    value.initialize()
    return value


def test_registry_freezes_multiplicity_and_thresholds() -> None:
    specs = {item.experiment_id: item for item in experiment_registry()}
    assert registry_hash() == "fd045b13c86e9071bfd0ee1fbfb458e7d6594b0bca4053022a3169e4fb383a52"
    assert specs["NEG_INCOMPLETE_IBO_VS_ROBUST"].multiplicity == 2
    assert specs["BARG_COMPLETE_FAIRNESS_VS_THEORY"].multiplicity == 1
    assert specs["PERS_BUY_MARGIN_VS_THEORY"].alpha_test == pytest.approx(0.025)
    assert specs["PERS_BUY_MARGIN_VS_THEORY"].promotion_threshold == pytest.approx(40)
    assert specs["CONFIRM_PERS_BUY_MARGIN_VS_THEORY"].multiplicity == 1
    assert specs["CONFIRM_PERS_BUY_MARGIN_VS_THEORY"].promotion_threshold == pytest.approx(20)
    assert specs["CONFIRM_PERS_BUY_MARGIN_VS_THEORY"].initial_status == "NOT_STARTED"


def test_assignment_is_atomic_unique_and_has_frozen_subcohort(store: CohortStore) -> None:
    game = bargaining_game()
    with ThreadPoolExecutor(max_workers=8) as pool:
        records = list(
            pool.map(
                lambda _: store.assign_game(
                    game, baseline_policy="BARGAINING_COMPLETE_FINITE"
                ),
                range(32),
            )
        )
    assert {item.game_id for item in records} == {"b-1"}
    assert {item.assigned_arm for item in records} <= {"control", "challenger"}
    assert records[0].cohort_id == COHORT_ID
    assert records[0].subcohort_id == FAMILY_SUBCOHORT_IDS["bargaining"]
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM assignments").fetchone()[0] == 1


def test_assignment_uses_one_fresh_half_probability_draw_per_new_game(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    draws = iter((0, 1))
    monkeypatch.setattr("eprocess.store.secrets.randbits", lambda bits: next(draws))
    value = CohortStore(tmp_path / "draws.sqlite3", frozen_commit="abc123")
    value.initialize()
    control = value.assign_game(
        bargaining_game("control"), baseline_policy="BARGAINING_COMPLETE_FINITE"
    )
    challenger = value.assign_game(
        bargaining_game("challenger"), baseline_policy="BARGAINING_COMPLETE_FINITE"
    )
    assert control.assigned_arm == "control"
    assert challenger.assigned_arm == "challenger"
    assert control.assignment_probability == challenger.assignment_probability == 0.5
    # Re-reading an existing game consumes no new draw and preserves its whole-game arm.
    assert value.assign_game(
        bargaining_game("control"), baseline_policy="changed"
    ) == control


def test_seeded_test_draw_is_reproducible_without_changing_production_csprng(
    tmp_path: Path,
) -> None:
    def sequence(seed: int, name: str) -> list[str]:
        rng = random.Random(seed)
        value = CohortStore(
            tmp_path / f"{name}.sqlite3",
            frozen_commit="abc123",
            arm_draw=lambda spec, game_id, cell: (
                "challenger" if rng.random() < spec.assignment_probability else "control"
            ),
        )
        value.initialize()
        return [
            value.assign_game(
                bargaining_game(f"{name}-{index}"),
                baseline_policy="BARGAINING_COMPLETE_FINITE",
            ).assigned_arm
            for index in range(20)
        ]

    assert sequence(7301, "left") == sequence(7301, "right")


def test_assignment_does_not_change_with_post_treatment_state(store: CohortStore) -> None:
    game = bargaining_game()
    first = store.assign_game(game, baseline_policy="BARGAINING_COMPLETE_FINITE")
    game["game_state"].update(
        {
            "round": 7,
            "last_offer": {"player_1_gain": 1, "player_2_gain": 99},
            "history": [{"decision": "reject"}],
            "current_quality": "post-treatment-noise",
        }
    )
    second = store.assign_game(game, baseline_policy="UNRELATED_LATER_BASELINE")
    assert second == first


def test_duplicate_terminal_does_not_double_update_eprocess(store: CohortStore) -> None:
    assignment = store.assign_game(
        bargaining_game(), baseline_policy="BARGAINING_COMPLETE_FINITE"
    )
    first = store.record_outcome(
        assignment.game_id,
        raw_payoff=50,
        bounded_payoff=0.5,
        payoff_transform={"name": "bargaining_share_v1"},
        terminal_outcome="agreement",
        valid_trace=True,
    )
    duplicate = store.record_outcome(
        assignment.game_id,
        raw_payoff=99,
        bounded_payoff=0.99,
        payoff_transform={"name": "bargaining_share_v1"},
        terminal_outcome="agreement",
        valid_trace=True,
    )
    assert first["valid_for_eprocess"] is True
    assert first["X_t"] in {-0.5, 0.5}
    assert duplicate["duplicate"] is True
    snapshot = store.snapshot()
    experiment = next(
        item
        for item in snapshot["experiments"]
        if item["experiment_id"] == "BARG_COMPLETE_FAIRNESS_VS_THEORY"
    )
    assert experiment["n_control"] + experiment["n_challenger"] == 1


def test_resolved_experiment_receives_no_future_randomized_assignment(
    store: CohortStore,
) -> None:
    first = store.assign_game(
        bargaining_game("first"), baseline_policy="BARGAINING_COMPLETE_FINITE"
    )
    store.safety_pause_for_game(first.game_id, reason="TEST_PREDECLARED_STOP")
    future = store.assign_game(
        bargaining_game("future"), baseline_policy="BARGAINING_COMPLETE_FINITE"
    )
    assert store.experiment_status("BARG_COMPLETE_FAIRNESS_VS_THEORY") == "SAFETY_PAUSED"
    assert future.experiment_id is None
    assert future.evidence_class == "OBSERVATIONAL_LIVE_EVIDENCE"


def test_promoted_policy_becomes_observational_incumbent_for_future_games(
    store: CohortStore,
) -> None:
    with store._connect() as connection:
        connection.execute(
            "UPDATE experiments SET status='PROMOTE' WHERE experiment_id=?",
            ("BARG_COMPLETE_FAIRNESS_VS_THEORY",),
        )
    future = store.assign_game(
        bargaining_game("promoted"), baseline_policy="BARGAINING_COMPLETE_FINITE"
    )
    assert future.experiment_id is None
    assert future.evidence_class == "OBSERVATIONAL_LIVE_EVIDENCE"
    assert future.assigned_policy == "BARGAINING_FAIRNESS"
    assert future.assignment_reason == "PROMOTED_POLICY_OBSERVATIONAL"


def test_persuasion_identical_actions_are_noninformative_until_divergence(
    store: CohortStore,
) -> None:
    registry = CohortOverrideRegistry(store)
    identical = persuasion_buyer_game(high=204)  # EV=102: both buy.
    registry.resolve(identical, baseline_policy="PERSUASION_P0_BABBLING", role="buyer")
    assignment = store.assignment("p-1")
    assert assignment is not None and assignment.informative is False

    divergent = persuasion_buyer_game(high=202)  # EV=101: theory buys, margin does not.
    registry.resolve(divergent, baseline_policy="PERSUASION_P0_BABBLING", role="buyer")
    assignment = store.assignment("p-1")
    assert assignment is not None and assignment.informative is True
    assert assignment.informative_reason == "BUYER_THEORY_AND_MARGIN_ACTIONS_DIVERGED"

    registry.resolve(identical, baseline_policy="PERSUASION_P0_BABBLING", role="buyer")
    assignment = store.assignment("p-1")
    assert assignment is not None and assignment.informative is True


def test_incomplete_t1_negotiation_and_incomplete_bargaining_are_observational() -> None:
    negotiation = {
        "game_family": "negotiation",
        "your_player": "player_1",
        "game_state": {
            "complete_information": False,
            "horizon_known": True,
            "max_rounds": 1,
            "player_1_role": "seller",
        },
    }
    bargaining = bargaining_game()
    bargaining["game_state"]["complete_information"] = False
    assert eligible_experiment_ids(negotiation) == ()
    assert eligible_experiment_ids(bargaining) == ()


def test_first_five_challenger_bad_outcomes_safety_pause(tmp_path: Path) -> None:
    value = CohortStore(
        tmp_path / "first-five.sqlite3",
        frozen_commit="abc123",
        arm_draw=lambda spec, game_id, cell: "challenger",
    )
    value.initialize()
    for index in range(5):
        assignment = value.assign_game(
            bargaining_game(f"bad-{index}"), baseline_policy="BARGAINING_COMPLETE_FINITE"
        )
        value.record_outcome(
            assignment.game_id,
            raw_payoff=0,
            bounded_payoff=0,
            payoff_transform={"name": "test"},
            terminal_outcome="no_deal",
            valid_trace=True,
        )
        expected = "RUNNING" if index < 4 else "SAFETY_PAUSED"
        assert value.experiment_status("BARG_COMPLETE_FAIRNESS_VS_THEORY") == expected


def test_bad_rate_pause_waits_for_eight_and_requires_strictly_above_point_75(
    tmp_path: Path,
) -> None:
    value = CohortStore(
        tmp_path / "rate.sqlite3",
        frozen_commit="abc123",
        arm_draw=lambda spec, game_id, cell: "challenger",
    )
    value.initialize()
    # One positive outcome prevents the first-five rule; seven of eight are bad.
    raw_values = [0, 0, 1, 0, 0, 0, 0, 0]
    for index, raw in enumerate(raw_values):
        assignment = value.assign_game(
            bargaining_game(f"rate-{index}"), baseline_policy="BARGAINING_COMPLETE_FINITE"
        )
        value.record_outcome(
            assignment.game_id,
            raw_payoff=raw,
            bounded_payoff=min(1.0, raw),
            payoff_transform={"name": "test"},
            terminal_outcome="agreement" if raw else "no_deal",
            valid_trace=True,
        )
        expected = "RUNNING" if index < 7 else "SAFETY_PAUSED"
        assert value.experiment_status("BARG_COMPLETE_FAIRNESS_VS_THEORY") == expected


def test_promotion_candidate_activates_fresh_confirmation_then_promotes(
    tmp_path: Path,
) -> None:
    value = CohortStore(
        tmp_path / "confirmation.sqlite3",
        frozen_commit="abc123",
        arm_draw=lambda spec, game_id, cell: "challenger",
    )
    value.initialize()
    components = json.dumps({"0.1": 39.0, "0.25": 39.0, "0.5": 39.0, "0.75": 39.0})
    with value._connect() as connection:
        connection.execute(
            """
            UPDATE experiments SET main_components=?,n_control=1,control_sum_y=0
            WHERE experiment_id='BARG_COMPLETE_FAIRNESS_VS_THEORY'
            """,
            (components,),
        )
    exploration = value.assign_game(
        bargaining_game("exploration-cross"), baseline_policy="BARGAINING_COMPLETE_FINITE"
    )
    value.record_outcome(
        exploration.game_id,
        raw_payoff=100,
        bounded_payoff=1,
        payoff_transform={"name": "test"},
        terminal_outcome="agreement",
        valid_trace=True,
    )
    assert value.experiment_status("BARG_COMPLETE_FAIRNESS_VS_THEORY") == "PROMOTION_CANDIDATE"
    assert value.experiment_status("CONFIRM_BARG_COMPLETE_FAIRNESS_VS_THEORY") == "RUNNING"

    confirm_components = json.dumps(
        {"0.1": 19.0, "0.25": 19.0, "0.5": 19.0, "0.75": 19.0}
    )
    with value._connect() as connection:
        connection.execute(
            """
            UPDATE experiments SET main_components=?,n_control=1,control_sum_y=0
            WHERE experiment_id='CONFIRM_BARG_COMPLETE_FAIRNESS_VS_THEORY'
            """,
            (confirm_components,),
        )
    confirmation = value.assign_game(
        bargaining_game("confirmation-cross"), baseline_policy="BARGAINING_COMPLETE_FINITE"
    )
    assert confirmation.experiment_id == "CONFIRM_BARG_COMPLETE_FAIRNESS_VS_THEORY"
    value.record_outcome(
        confirmation.game_id,
        raw_payoff=100,
        bounded_payoff=1,
        payoff_transform={"name": "test"},
        terminal_outcome="agreement",
        valid_trace=True,
    )
    assert value.experiment_status("CONFIRM_BARG_COMPLETE_FAIRNESS_VS_THEORY") == "PROMOTE"
    future = value.assign_game(
        bargaining_game("post-confirm"), baseline_policy="BARGAINING_COMPLETE_FINITE"
    )
    assert future.experiment_id is None
    assert future.assigned_policy == "BARGAINING_FAIRNESS"


def test_deterministic_replay_recreates_both_eprocesses(store: CohortStore) -> None:
    assignment = store.assign_game(
        bargaining_game("replay"), baseline_policy="BARGAINING_COMPLETE_FINITE"
    )
    update = store.record_outcome(
        assignment.game_id,
        raw_payoff=40,
        bounded_payoff=0.4,
        payoff_transform={"name": "test"},
        terminal_outcome="agreement",
        valid_trace=True,
    )
    replay = store.replay_experiment("BARG_COMPLETE_FAIRNESS_VS_THEORY")
    assert replay["E_t"] == pytest.approx(update["E_t"])
    assert replay["E_t_prime"] == pytest.approx(update["E_t_prime"])


def test_cohort_metadata_cannot_mix_frozen_commits(tmp_path: Path) -> None:
    path = tmp_path / "immutable.sqlite3"
    CohortStore(path, frozen_commit="first").initialize()
    with pytest.raises(RuntimeError, match="frozen_commit"):
        CohortStore(path, frozen_commit="second").initialize()

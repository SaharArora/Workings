from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from eprocess.store import CohortStore


def bargaining_game(game_id: str) -> dict:
    return {
        "game_id": game_id,
        "game_family": "bargaining",
        "your_player": "player_1",
        "opponent": {"type": "hidden", "name": None},
        "game_state": {
            "complete_information": True,
            "horizon_known": True,
            "max_rounds": 10,
            "money_to_divide": 100,
            "delta_1": 0.9,
            "delta_2": 0.8,
        },
    }


def negotiation_game(game_id: str) -> dict:
    return {
        "game_id": game_id,
        "game_family": "negotiation",
        "your_player": "player_1",
        "opponent": {"type": "agent", "name": "published"},
        "game_state": {
            "complete_information": False,
            "horizon_known": False,
            "messages_allowed": True,
            "player_1_role": "seller",
            "player_2_role": "buyer",
            "player_1_value": 100,
            "product_price_order": 100,
        },
    }


def persuasion_game(game_id: str) -> dict:
    return {
        "game_id": game_id,
        "game_family": "persuasion",
        "your_player": "player_2",
        "opponent": {"type": "human", "name": None},
        "game_state": {
            "p": 0.5,
            "v": 200,
            "u": 0,
            "product_price": 100,
            "total_rounds": 20,
            "seller_message_type": "binary",
            "is_seller_know_cv": False,
        },
    }


@pytest.mark.parametrize(
    ("resolve_at", "status"),
    ((100, "PROMOTE"), (150, "SAFETY_PAUSED"), (400, "RETAIN")),
)
def test_resolved_experiment_stops_randomization_but_family_reaches_exactly_1000(
    tmp_path: Path, resolve_at: int, status: str
) -> None:
    store = CohortStore(tmp_path / f"{status}.sqlite3", frozen_commit="frozen")
    store.initialize()
    randomized = 0
    observational = 0
    for index in range(1, 1001):
        if index == resolve_at + 1:
            with store._connect() as connection:
                connection.execute(
                    "UPDATE experiments SET status=? WHERE experiment_id=?",
                    (status, "BARG_COMPLETE_FAIRNESS_VS_THEORY"),
                )
        game_id = f"{status}-{index}"
        store.record_tracked_game(game_id, family="bargaining", family_cap=1000)
        assignment = store.assign_game(
            bargaining_game(game_id), baseline_policy="BARGAINING_COMPLETE_FINITE"
        )
        randomized += int(assignment.experiment_id is not None)
        observational += int(assignment.experiment_id is None)
        store.record_completed_game(game_id, reason="TEST_TERMINAL")
    assert randomized == resolve_at
    assert observational == 1000 - resolve_at
    assert store.family_counts("bargaining")["completed"] == 1000
    with pytest.raises(RuntimeError, match="cap"):
        store.record_tracked_game("game-1001", family="bargaining", family_cap=1000)


def test_999_complete_plus_one_active_finishes_at_1000_without_game_1001(
    tmp_path: Path,
) -> None:
    store = CohortStore(tmp_path / "active-final.sqlite3", frozen_commit="frozen")
    store.initialize()
    for index in range(999):
        game_id = f"done-{index}"
        store.record_tracked_game(game_id, family="persuasion", family_cap=1000)
        store.record_completed_game(game_id, reason="TEST_TERMINAL")
    store.record_tracked_game("active-1000", family="persuasion", family_cap=1000)
    assert store.family_counts("persuasion") == {
        "assigned": 0,
        "outcome_records": 0,
        "tracked": 1000,
        "completed": 999,
    }
    with pytest.raises(RuntimeError, match="cap"):
        store.record_tracked_game("game-1001", family="persuasion", family_cap=1000)
    store.record_completed_game("active-1000", reason="TEST_TERMINAL")
    assert store.family_counts("persuasion")["completed"] == 1000


def test_three_family_executors_share_store_without_duplicate_evidence(
    tmp_path: Path,
) -> None:
    store = CohortStore(
        tmp_path / "concurrent.sqlite3",
        frozen_commit="frozen",
        arm_draw=lambda spec, game_id, cell: "control",
    )
    store.initialize()
    factories = {
        "bargaining": (bargaining_game, "BARGAINING_COMPLETE_FINITE", 0.5),
        "negotiation": (negotiation_game, "NEGOTIATION_ROBUST", 0.5),
        "persuasion": (persuasion_game, "PERSUASION_BUY_THEORY", 0.5),
    }

    def execute_family(family: str) -> None:
        factory, baseline, y = factories[family]
        for index in range(20):
            game_id = f"{family}-{index}"
            store.record_tracked_game(game_id, family=family, family_cap=1000)
            assignment = store.assign_game(factory(game_id), baseline_policy=baseline)
            store.record_outcome(
                game_id,
                raw_payoff=1,
                bounded_payoff=y,
                payoff_transform={"name": "concurrency-test"},
                terminal_outcome="agreement",
                valid_trace=True,
            )
            store.record_completed_game(game_id, reason="TEST_TERMINAL")
            assert assignment.game_id == game_id

    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(execute_family, factories))

    with store._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM family_games").fetchone()[0] == 60
        assert connection.execute("SELECT COUNT(*) FROM assignments").fetchone()[0] == 60
        assert connection.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0] == 60
        valid_randomized = connection.execute(
            "SELECT COUNT(*) FROM outcomes WHERE valid_for_eprocess=1"
        ).fetchone()[0]
        assert connection.execute("SELECT COUNT(*) FROM eprocess_updates").fetchone()[0] == valid_randomized
        assert connection.execute(
            "SELECT COUNT(DISTINCT game_id) FROM eprocess_updates"
        ).fetchone()[0] == valid_randomized

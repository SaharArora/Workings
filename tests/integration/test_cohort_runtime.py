from __future__ import annotations

import json
from pathlib import Path

import pytest

from eprocess.store import CohortStore
from glee.cohort_runtime import CohortRecorder, bounded_payoff
from leaderboard.agent import LeaderboardAgent
from leaderboard.cohort_overrides import CohortOverrideRegistry
from leaderboard.policy_router import PolicyRouter


class NoopClient:
    pass


def bargaining_game(game_id: str = "live-b") -> dict:
    return {
        "game_id": game_id,
        "game_family": "bargaining",
        "your_player": "player_1",
        "opponent": {"type": "hidden", "name": None},
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


@pytest.mark.parametrize(
    ("family", "role", "raw", "configuration", "expected"),
    (
        ("negotiation", "seller", 0, {"player_1_value": 100}, 0.5),
        ("negotiation", "seller", 100, {"player_1_value": 100}, 0.75),
        ("bargaining", "alice", 50, {"money_to_divide": 100}, 0.5),
        (
            "persuasion",
            "buyer",
            0,
            {"total_rounds": 2, "product_price": 100, "u": 0, "v": 200},
            0.5,
        ),
        (
            "persuasion",
            "seller",
            100,
            {"total_rounds": 2, "product_price": 100},
            0.5,
        ),
    ),
)
def test_frozen_family_payoff_transforms(
    family: str,
    role: str,
    raw: float,
    configuration: dict,
    expected: float,
) -> None:
    score, metadata = bounded_payoff(
        family=family,
        role=role,
        raw_payoff=raw,
        configuration=configuration,
    )
    assert score == pytest.approx(expected)
    assert metadata["Y_t"] == pytest.approx(expected)
    assert metadata["raw_payoff"] == raw


def test_recorder_persists_lifecycle_assignment_outcome_and_eprocess(
    tmp_path: Path,
) -> None:
    store = CohortStore(tmp_path / "cohort.sqlite3", frozen_commit="frozen")
    store.initialize()
    recorder = CohortRecorder(
        client=NoopClient(),  # type: ignore[arg-type]
        family="bargaining",
        output_path=tmp_path / "bargaining.jsonl",
        frozen_commit="frozen",
        store=store,
        agent=LeaderboardAgent(
            PolicyRouter(experimental_overrides=CohortOverrideRegistry(store))
        ),
    )
    game = bargaining_game()
    recorder.supervisor_event({"event": "game_tracked", "game_id": game["game_id"]})
    action = recorder.strategy(game)
    assert action["alice_gain"] + action["bob_gain"] == 100
    terminal = {
        "status": "completed",
        "result": {
            "outcome": "agreement",
            "player_1_payoff": 50,
            "player_2_payoff": 50,
        },
    }
    completion = {
        "event": "game_completed",
        "game_id": game["game_id"],
        "completion_reason": "TERMINAL_GAME_STATE",
        "terminal": terminal,
    }
    recorder.supervisor_event(completion)
    recorder.supervisor_event(completion)
    recorder.close()

    assert store.family_counts("bargaining") == {
        "assigned": 1,
        "outcome_records": 1,
        "tracked": 1,
        "completed": 1,
    }
    records = [json.loads(line) for line in (tmp_path / "bargaining.jsonl").read_text().splitlines()]
    result = next(item for item in records if item["event"] == "game_result")
    assert result["valid_trace"] is True
    assert result["bounded_payoff"] == pytest.approx(0.5)
    assert result["evidence_update"]["valid_for_eprocess"] is True


def test_invalid_action_pauses_only_assigned_experiment_and_excludes_trace(
    tmp_path: Path,
) -> None:
    store = CohortStore(tmp_path / "cohort.sqlite3", frozen_commit="frozen")
    store.initialize()
    recorder = CohortRecorder(
        client=NoopClient(),  # type: ignore[arg-type]
        family="bargaining",
        output_path=tmp_path / "invalid.jsonl",
        frozen_commit="frozen",
        store=store,
        agent=LeaderboardAgent(
            PolicyRouter(experimental_overrides=CohortOverrideRegistry(store))
        ),
    )
    game = bargaining_game("invalid")
    recorder.supervisor_event({"event": "game_tracked", "game_id": "invalid"})
    recorder.strategy(game)
    recorder.supervisor_event(
        {"event": "action_result", "game_id": "invalid", "result": {"valid": False}}
    )
    recorder.supervisor_event(
        {
            "event": "game_completed",
            "game_id": "invalid",
            "completion_reason": "MOVE_RESULT",
            "terminal": {
                "status": "completed",
                "result": {"outcome": "invalid_moves", "player_1_payoff": 0},
            },
        }
    )
    recorder.close()
    assert store.experiment_status("BARG_COMPLETE_FAIRNESS_VS_THEORY") == "SAFETY_PAUSED"
    with store._connect() as connection:
        outcome = connection.execute(
            "SELECT valid_for_eprocess,exclusion_reason FROM outcomes WHERE game_id='invalid'"
        ).fetchone()
    assert outcome["valid_for_eprocess"] == 0
    assert outcome["exclusion_reason"] == "INVALID_ACTION_REJECTED"


def test_lifecycle_cap_rejects_an_extra_tracked_game(tmp_path: Path) -> None:
    store = CohortStore(tmp_path / "cohort.sqlite3", frozen_commit="frozen")
    store.initialize()
    store.record_tracked_game("one", family="bargaining", family_cap=1)
    with pytest.raises(RuntimeError, match="cap"):
        store.record_tracked_game("two", family="bargaining", family_cap=1)


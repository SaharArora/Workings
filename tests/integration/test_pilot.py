from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from glee.pilot import PilotRecorder


class StatsClient:
    def stats(self) -> dict[str, Any]:
        return {
            "active_games": 0,
            "scores": {"negotiation": {"rating": 1001.0}},
        }


def negotiation_game() -> dict[str, Any]:
    return {
        "game_id": "g1",
        "game_family": "negotiation",
        "your_player": "player_1",
        "phase": "offer",
        "opponent": {"type": "hidden", "name": None},
        "game_state": {
            "phase": "offer",
            "current_player": "player_1",
            "player_1_role": "seller",
            "player_2_role": "buyer",
            "player_1_value": 10,
            "complete_information": False,
            "horizon_known": False,
            "messages_allowed": False,
            "round": 1,
            "history": [],
            "last_offer": None,
        },
        "valid_actions": {"type": "offer", "fields": {"product_price": "number"}},
    }


def negotiation_decision_game(price: float = 20) -> dict[str, Any]:
    game = negotiation_game()
    game["game_state"].update(
        {
            "phase": "decision",
            "current_player": "player_1",
            "last_offer": {"price": price, "from_player": "player_2", "round": 2},
            "round": 2,
        }
    )
    game["valid_actions"] = {
        "type": "decision",
        "fields": {
            "decision": "'AcceptOffer', 'RejectOffer', or 'WalkAway'",
            "product_price": "number (required if RejectOffer)",
        },
    }
    return game


def records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_pilot_logs_route_action_latency_and_no_secret(tmp_path: Path) -> None:
    path = tmp_path / "pilot.jsonl"
    recorder = PilotRecorder(
        client=StatsClient(),  # type: ignore[arg-type]
        family="negotiation",
        output_path=path,
        frozen_commit="abc123",
    )
    recorder.latest_stats = StatsClient().stats()
    action = recorder.strategy(negotiation_game())
    recorder.close()
    assert action == {"product_price": 15.0}
    item = records(path)[0]
    assert item["event"] == "policy_decision"
    assert item["routing"]["selected_policy"] == "NEGOTIATION_ROBUST"
    assert item["latency_seconds"]["total"] < 30
    assert "GLEE_API_KEY" not in path.read_text()


def test_invalid_action_result_requests_hard_stop(tmp_path: Path) -> None:
    path = tmp_path / "pilot.jsonl"
    recorder = PilotRecorder(
        client=StatsClient(),  # type: ignore[arg-type]
        family="negotiation",
        output_path=path,
        frozen_commit="abc123",
    )
    recorder.supervisor_event(
        {"event": "action_result", "game_id": "g1", "result": {"valid": False}}
    )
    recorder.close()
    assert recorder.stop_requested()
    assert recorder.hard_stop_reasons == ["INVALID_ACTION_REJECTED"]


def test_three_same_cell_floor_results_trigger_strategic_review(tmp_path: Path) -> None:
    path = tmp_path / "pilot.jsonl"
    recorder = PilotRecorder(
        client=StatsClient(),  # type: ignore[arg-type]
        family="negotiation",
        output_path=path,
        frozen_commit="abc123",
    )
    for index in range(3):
        game_id = f"g{index}"
        recorder.game_metadata[game_id] = {
            "cell": "cell-a",
            "role": "seller",
            "your_player": "player_1",
            "opponent": {"type": "hidden", "name": None},
            "configuration": {},
            "rating_before": 1000,
            "selected_incumbent": "NEGOTIATION_ROBUST",
            "own_value": 10,
        }
        recorder.supervisor_event(
            {
                "event": "game_completed",
                "game_id": game_id,
                "terminal": {
                    "result": {"outcome": "no_deal", "player_1_payoff": 0}
                },
            }
        )
    recorder.close()
    assert recorder.strategic_review_cells == ["cell-a"]
    assert any(item["event"] == "STRATEGIC_REVIEW_REQUIRED" for item in records(path))


def test_first_three_zero_payoffs_pause_structural_class_not_operationally_fail(
    tmp_path: Path,
) -> None:
    path = tmp_path / "pilot.jsonl"
    recorder = PilotRecorder(
        client=StatsClient(),  # type: ignore[arg-type]
        family="negotiation",
        output_path=path,
        frozen_commit="abc123",
    )
    structural = "negotiation/ADAPTIVE/incomplete/unknown-horizon"
    for index, value in enumerate((100, 1_000_000, 10_000)):
        game_id = f"structural-{index}"
        recorder.game_metadata[game_id] = {
            "cell": f"exact-cell-value-{value}",
            "role": "buyer",
            "your_player": "player_2",
            "opponent": {"type": "hidden", "name": None},
            "configuration": {"player_2_value": value},
            "rating_before": 1000,
            "selected_incumbent": "NEGOTIATION_ADAPTIVE",
            "selected_policy": "NEGOTIATION_ADAPTIVE",
            "baseline_policy": "NEGOTIATION_ROBUST",
            "experimental_policy": "NEGOTIATION_ADAPTIVE",
            "authorization_status": "HUMAN_AUTHORIZED_EXPERIMENTAL_DIAGNOSTIC",
            "authorization_source": "human_authorized_bounded_pilot",
            "structural_policy_class": structural,
            "own_value": value,
        }
        recorder.supervisor_event(
            {
                "event": "game_completed",
                "game_id": game_id,
                "terminal": {
                    "result": {"outcome": "walked_away", "player_2_payoff": 0}
                },
            }
        )
    recorder.close()
    assert recorder.strategic_review_classes == [structural]
    assert recorder.paused_policy_classes == {
        structural: "FIRST_THREE_OBSERVATIONS_ALL_ZERO_OWN_PAYOFF"
    }
    assert not recorder.stop_requested()
    events = records(path)
    assert any(
        item.get("reason") == "FIRST_THREE_OBSERVATIONS_ALL_ZERO_OWN_PAYOFF"
        for item in events
    )


def test_three_identical_unknown_horizon_exchanges_stop_and_walk_away(tmp_path: Path) -> None:
    path = tmp_path / "pilot.jsonl"
    recorder = PilotRecorder(
        client=StatsClient(),  # type: ignore[arg-type]
        family="negotiation",
        output_path=path,
        frozen_commit="abc123",
    )
    game = negotiation_decision_game(price=5)
    assert recorder.strategy(game)["decision"] == "RejectOffer"
    assert recorder.strategy(game)["decision"] == "RejectOffer"
    assert recorder.strategy(game) == {"decision": "WalkAway"}
    recorder.close()
    assert recorder.hard_stop_reasons == ["DETERMINISTIC_NO_PROGRESS_CYCLE"]
    assert any(item["event"] == "pilot_safety_action" for item in records(path))


def test_materially_changed_unknown_horizon_offer_resets_cycle_count(tmp_path: Path) -> None:
    path = tmp_path / "pilot.jsonl"
    recorder = PilotRecorder(
        client=StatsClient(),  # type: ignore[arg-type]
        family="negotiation",
        output_path=path,
        frozen_commit="abc123",
    )
    for price in (5, 5, 6, 6):
        assert recorder.strategy(negotiation_decision_game(price=price))["decision"] == "RejectOffer"
    recorder.close()
    assert recorder.hard_stop_reasons == []

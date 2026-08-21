from __future__ import annotations

from collections import defaultdict
from typing import Any

import pytest

from glee.supervisor import BoundedRunTimeout, run_bounded


def game(game_id: str) -> dict[str, Any]:
    return {
        "game_id": game_id, "game_family": "negotiation", "your_player": "player_1",
        "phase": "offer", "opponent": {"type": "hidden", "name": None},
        "game_state": {"phase": "offer", "round": 1, "current_player": "player_1",
            "player_1_role": "seller", "player_1_value": 10, "complete_information": False,
            "horizon_known": False, "history": [], "last_offer": None},
        "valid_actions": {"type": "offer", "fields": {"product_price": "number"}},
        "prompt": "",
    }


class FakeTime:
    def __init__(self) -> None:
        self.value = 0.0

    def clock(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += max(seconds, 1.0)


class FakeClient:
    def __init__(
        self,
        *,
        pending: list[Any],
        stats: list[Any] | None = None,
        states: dict[str, list[Any]] | None = None,
        submits: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        self.pending_responses = pending
        self.stats_responses = stats or [{"active_games": 0}]
        self.state_responses = states or {}
        self.submit_responses = submits or {}
        self.queue_calls: list[str] = []
        self.leave_calls: list[str | None] = []
        self.submit_calls: list[str] = []
        self.sdk_completion_counter = 0

    @staticmethod
    def _next(values: list[Any]) -> Any:
        value = values.pop(0) if len(values) > 1 else values[0]
        if isinstance(value, Exception):
            raise value
        return value

    def queue(self, family: str) -> dict:
        self.queue_calls.append(family)
        return {"status": "queued"}

    def leave_queue(self, family: str | None = None) -> dict:
        self.leave_calls.append(family)
        return {}

    def pending_games(self) -> list[dict[str, Any]]:
        return self._next(self.pending_responses)

    def stats(self) -> dict[str, Any]:
        return self._next(self.stats_responses)

    def game_state(self, game_id: str) -> dict[str, Any]:
        values = self.state_responses.get(game_id, [{"status": "active", "game_state": {"phase": "offer"}}])
        return self._next(values)

    def submit(self, game_id: str, action: dict[str, Any]) -> dict[str, Any]:
        self.submit_calls.append(game_id)
        return self._next(self.submit_responses.get(game_id, [{"valid": True, "game_over": False}]))


def run(
    fake: FakeClient,
    *,
    max_games: int = 1,
    concurrency: int = 1,
    requeue: bool = False,
    events: list | None = None,
):
    timer = FakeTime()
    captured = events if events is not None else []
    return run_bounded(
        fake,
        lambda _: {"product_price": 10},
        game_family="negotiation",
        max_games=max_games,
        concurrency=concurrency,
        requeue=requeue,
        poll_interval=1,
        safety_timeout=20,
        event_sink=captured.append,
        clock=timer.clock,
        sleep=timer.sleep,
    )


def test_our_move_ends_game_and_max_one_exits_exactly_once() -> None:
    fake = FakeClient(
        pending=[[], [game("g1")]], stats=[{"active_games": 0}, {"active_games": 0}],
        submits={"g1": [{"valid": True, "game_over": True, "result": {"outcome": "agreement"}}]},
    )
    result = run(fake)
    assert result.completed_game_ids == ("g1",)
    assert result.exit_reason == "MAX_GAMES_COMPLETED"
    assert fake.submit_calls == ["g1"]


def test_opponent_move_ends_game_even_when_sdk_counter_does_not_change() -> None:
    fake = FakeClient(
        pending=[[], [game("g1")]], stats=[{"active_games": 0}, {"active_games": 0}],
        states={"g1": [{"status": "completed", "game_state": {"phase": "completed"}, "result": {"outcome": "agreement"}}]},
    )
    result = run(fake)
    assert result.completed_game_ids == ("g1",)
    assert fake.sdk_completion_counter == 0


def test_disappearance_after_tracking_counts_terminal_once() -> None:
    events: list[dict[str, Any]] = []
    fake = FakeClient(
        pending=[[], [game("g1")], []], stats=[{"active_games": 0}, {"active_games": 0}],
        states={"g1": [LookupError("gone")]},
    )
    result = run(fake, events=events)
    assert result.completed_game_ids == ("g1",)
    completed = [event for event in events if event["event"] == "game_completed"]
    assert len(completed) == 1
    assert completed[0]["completion_reason"] == "DISAPPEARED_AFTER_TRACKING"


def test_transient_poll_failure_is_tolerated() -> None:
    fake = FakeClient(
        pending=[[], RuntimeError("temporary"), [game("g1")]],
        stats=[{"active_games": 0}, {"active_games": 0}],
        submits={"g1": [{"valid": True, "game_over": True, "result": {}}]},
    )
    assert run(fake).completed_game_ids == ("g1",)


def test_outer_strategy_fallback_is_structured_and_submitted() -> None:
    events: list[dict[str, Any]] = []
    fake = FakeClient(
        pending=[[], [game("g1")]], stats=[{"active_games": 0}, {"active_games": 0}],
        submits={"g1": [{"valid": True, "game_over": True, "result": {}}]},
    )
    timer = FakeTime()

    def broken_strategy(_: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("local failure")

    result = run_bounded(
        fake,
        broken_strategy,
        game_family="negotiation",
        max_games=1,
        requeue=False,
        poll_interval=1,
        safety_timeout=20,
        event_sink=events.append,
        clock=timer.clock,
        sleep=timer.sleep,
    )
    assert result.completed_game_ids == ("g1",)
    assert [event["error_type"] for event in events if event["event"] == "strategy_fallback"] == ["RuntimeError"]
    assert fake.submit_calls == ["g1"]


def test_max_three_requeues_only_until_three_and_never_starts_fourth() -> None:
    games = [game(f"g{index}") for index in range(1, 4)]
    fake = FakeClient(
        pending=[[], *[[item] for item in games]],
        stats=[{"active_games": 0}, *[{"active_games": 0} for _ in games]],
        submits={item["game_id"]: [{"valid": True, "game_over": True, "result": {}}] for item in games},
    )
    result = run(fake, max_games=3, requeue=True)
    assert result.completed_game_ids == ("g1", "g2", "g3")
    assert fake.submit_calls == ["g1", "g2", "g3"]
    assert fake.queue_calls == ["negotiation", "negotiation", "negotiation"]


def test_requeue_false_never_creates_a_fourth_game() -> None:
    games = [game(f"g{index}") for index in range(1, 4)]
    fake = FakeClient(
        pending=[[], games], stats=[{"active_games": 0}, {"active_games": 0}],
        submits={item["game_id"]: [{"valid": True, "game_over": True, "result": {}}] for item in games},
    )
    result = run(fake, max_games=3, concurrency=3, requeue=False)
    assert result.completed_game_ids == ("g1", "g2", "g3")
    assert fake.queue_calls == ["negotiation"]


def test_cleanup_always_leaves_queue_on_timeout() -> None:
    fake = FakeClient(pending=[[]], stats=[{"active_games": 0}])
    timer = FakeTime()
    with pytest.raises(BoundedRunTimeout):
        run_bounded(
            fake, lambda _: {}, game_family="negotiation", max_games=1,
            requeue=False, poll_interval=1, safety_timeout=2,
            clock=timer.clock, sleep=timer.sleep,
        )
    assert fake.leave_calls[-1] is None


def test_repeated_terminal_polling_never_double_counts() -> None:
    g1, g2 = game("g1"), game("g2")
    events: list[dict[str, Any]] = []
    fake = FakeClient(
        pending=[[], [g1], [g1, g2]],
        stats=[{"active_games": 0}, {"active_games": 1}, {"active_games": 0}],
        submits={
            "g1": [{"valid": True, "game_over": True, "result": {}}],
            "g2": [{"valid": True, "game_over": True, "result": {}}],
        },
    )
    result = run(fake, max_games=2, concurrency=2, events=events)
    assert result.completed_game_ids == ("g1", "g2")
    completed_ids = [event["game_id"] for event in events if event["event"] == "game_completed"]
    assert completed_ids == ["g1", "g2"]
    assert fake.submit_calls.count("g1") == 1

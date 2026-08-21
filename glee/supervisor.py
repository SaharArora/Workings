"""Authoritative lifecycle supervisor for bounded GLEE runs."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from glee.client import CompetitionClient
from glee.retry import never_raise
from glee.schemas import GameFamily, PendingGame

logger = logging.getLogger(__name__)
EventSink = Callable[[dict[str, Any]], None]


class BoundedRunTimeout(TimeoutError):
    """The hard safety deadline expired before the bounded run completed."""


@dataclass(frozen=True, slots=True)
class BoundedRunResult:
    game_family: str
    max_games: int
    tracked_game_ids: tuple[str, ...]
    completed_game_ids: tuple[str, ...]
    exit_reason: str
    elapsed_seconds: float


def _payload(game: PendingGame | dict[str, Any]) -> dict[str, Any]:
    return game.to_strategy_payload() if isinstance(game, PendingGame) else game


def _is_terminal(value: dict[str, Any]) -> bool:
    status = str(value.get("status", "")).lower()
    state = value.get("game_state") if isinstance(value.get("game_state"), dict) else value
    phase = str(state.get("phase", value.get("phase", ""))).lower()
    return bool(
        value.get("game_over") is True
        or status in {"completed", "finished", "closed"}
        or phase == "completed"
        or (value.get("result") is not None and status not in {"active", "pending"})
    )


def run_bounded(
    client: CompetitionClient,
    strategy: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    game_family: GameFamily | str,
    max_games: int,
    concurrency: int = 1,
    requeue: bool = False,
    poll_interval: float = 2.0,
    safety_timeout: float = 600.0,
    event_sink: EventSink | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> BoundedRunResult:
    """Run a finite queue while counting terminal games independently of SDK ``run``.

    With ``requeue=False`` there is exactly one initial queue call. Every tracked game is
    counted at most once, using explicit terminal move/state indicators first and the
    authoritative ``active_games == 0`` disappearance condition second. Cleanup always
    leaves all queues. The strategy is protected by the outermost never-raise wrapper.
    """

    if max_games < 1 or concurrency < 1 or safety_timeout <= 0:
        raise ValueError("max_games, concurrency, and safety_timeout must be positive")
    family = GameFamily(game_family).value
    emit = event_sink or (lambda event: logger.info("bounded_run %s", event))
    tracked: dict[str, dict[str, Any]] = {}
    completed: set[str] = set()
    acted_states: set[tuple[str, str]] = set()
    pending_last_poll: set[str] = set()
    queue_open = False
    queue_calls = 0
    start = clock()
    exit_reason = ""

    def event(kind: str, **fields: Any) -> None:
        emit({"event": kind, "game_family": family, **fields})

    guarded_strategy = never_raise(
        strategy,
        on_fallback=lambda game, error_type: event(
            "strategy_fallback",
            game_id=str(game.get("game_id", "unknown")),
            error_type=error_type,
        ),
    )

    def mark_completed(game_id: str, reason: str, terminal: dict[str, Any] | None = None) -> None:
        if game_id in completed:
            event("terminal_already_counted", game_id=game_id, reason=reason)
            return
        completed.add(game_id)
        event(
            "game_completed",
            game_id=game_id,
            completion_reason=reason,
            completed_games=len(completed),
            terminal=terminal,
        )

    def queue_once(reason: str) -> None:
        nonlocal queue_open, queue_calls
        client.queue(family)
        queue_open = True
        queue_calls += 1
        event("queue_joined", reason=reason, queue_calls=queue_calls)

    try:
        initial_pending = client.pending_games()
        initial_stats = client.stats()
        if initial_pending or int(initial_stats.get("active_games", 0)) != 0:
            raise RuntimeError("bounded run requires an idle account with no pending games")
        queue_once("initial")
        event(
            "run_started",
            max_games=max_games,
            concurrency=concurrency,
            requeue=requeue,
            safety_timeout=safety_timeout,
        )

        while True:
            elapsed = clock() - start
            if elapsed >= safety_timeout:
                exit_reason = "HARD_SAFETY_TIMEOUT"
                event("run_timeout", elapsed_seconds=elapsed, tracked=list(tracked), completed=list(completed))
                raise BoundedRunTimeout(
                    f"bounded {family} run exceeded {safety_timeout}s with {len(completed)}/{max_games} complete"
                )

            try:
                pending_items = client.pending_games()
                pending_payloads = [_payload(item) for item in pending_items]
            except Exception as exc:
                event("poll_error", operation="pending_games", error_type=type(exc).__name__)
                sleep(poll_interval)
                continue

            pending_ids = {str(game["game_id"]) for game in pending_payloads}
            pending_last_poll = pending_ids
            open_tracked = {game_id for game_id in tracked if game_id not in completed}

            for game in pending_payloads:
                game_id = str(game["game_id"])
                if game_id not in tracked:
                    if len(tracked) >= max_games or len(open_tracked) >= concurrency:
                        event("unexpected_extra_game", game_id=game_id)
                        raise RuntimeError("server assigned a game beyond the bounded run limits")
                    tracked[game_id] = game
                    open_tracked.add(game_id)
                    # A match consumes the server-side queue entry. Keep this state
                    # separate from active-game state so a bounded requeue can top up
                    # without relying on the SDK's local completion counter.
                    queue_open = False
                    event("game_tracked", game_id=game_id, tracked_games=len(tracked))
                    if len(tracked) >= max_games:
                        client.leave_queue(family)
                        queue_open = False
                        event("queue_left", reason="requested_game_count_tracked")
                else:
                    tracked[game_id] = game

                if game_id in completed:
                    continue
                state_fingerprint = json_fingerprint(game)
                action_key = (game_id, state_fingerprint)
                if action_key in acted_states:
                    event("duplicate_pending_state_skipped", game_id=game_id)
                    continue
                action = guarded_strategy(game)
                event("action_submitting", game_id=game_id, action=action)
                try:
                    result = client.submit(game_id, action)
                except Exception as exc:
                    event("submit_error", game_id=game_id, error_type=type(exc).__name__)
                    continue
                event("action_result", game_id=game_id, result=result)
                if result.get("valid") is not False:
                    acted_states.add(action_key)
                if _is_terminal(result):
                    mark_completed(game_id, "MOVE_RESULT", result)

            for game_id in tuple(tracked):
                if game_id in completed:
                    continue
                try:
                    state = client.game_state(game_id)
                except Exception as exc:
                    event("poll_error", operation="game_state", game_id=game_id, error_type=type(exc).__name__)
                    continue
                event("game_state_polled", game_id=game_id, state=state)
                if _is_terminal(state):
                    mark_completed(game_id, "TERMINAL_GAME_STATE", state)

            try:
                stats = client.stats()
                active_games = int(stats.get("active_games", 0))
            except Exception as exc:
                event("poll_error", operation="stats", error_type=type(exc).__name__)
                sleep(poll_interval)
                continue

            if active_games == 0:
                for game_id in tracked:
                    if game_id not in completed and game_id not in pending_last_poll:
                        mark_completed(game_id, "DISAPPEARED_AFTER_TRACKING")

            if len(completed) >= max_games and all(game_id in completed for game_id in tracked):
                exit_reason = "MAX_GAMES_COMPLETED"
                event("run_exiting", reason=exit_reason, completed_games=len(completed))
                break

            if requeue and not queue_open and len(tracked) < max_games and active_games < concurrency:
                queue_once("bounded_top_up")

            sleep(poll_interval)
    finally:
        try:
            client.leave_queue()
            event("queue_cleanup", success=True)
        except Exception as exc:
            event("queue_cleanup", success=False, error_type=type(exc).__name__)

    return BoundedRunResult(
        game_family=family,
        max_games=max_games,
        tracked_game_ids=tuple(tracked),
        completed_game_ids=tuple(sorted(completed)),
        exit_reason=exit_reason,
        elapsed_seconds=clock() - start,
    )


def json_fingerprint(game: dict[str, Any]) -> str:
    """Identify one actionable state without including prompts or credentials."""
    import json

    state = game.get("game_state", {})
    stable = {
        "phase": game.get("phase", state.get("phase")),
        "round": state.get("round"),
        "current_player": state.get("current_player"),
        "last_offer": state.get("last_offer"),
        "history_length": len(state.get("history", [])),
        "valid_actions": game.get("valid_actions"),
    }
    return json.dumps(stable, sort_keys=True, default=str, separators=(",", ":"))

"""Frozen-policy finite pilot orchestration and structured safety logging."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from glee.actions import validate_action
from glee.client import CompetitionClient
from glee.normalization import negotiation_payoff_transform
from glee.retry import fallback_action
from glee.supervisor import BoundedRunResult, BoundedRunTimeout
from leaderboard.agent import LeaderboardAgent
from research.evaluation.latency import POLICY_MAX_BUDGET_SECONDS


HARD_OPERATIONAL_STOP = "HARD_OPERATIONAL_STOP"
STRATEGIC_REVIEW_REQUIRED = "STRATEGIC_REVIEW_REQUIRED"
PAYOFF_FLOOR_OUTCOMES = {
    "no_deal",
    "no deal",
    "walked_away",
    "walkaway",
    "timeout",
    "invalid_moves",
}


@dataclass(frozen=True, slots=True)
class PilotResult:
    family: str
    requested_games: int
    completed_games: int
    exit_reason: str
    hard_stop_reasons: tuple[str, ...]
    strategic_review_cells: tuple[str, ...]
    preflight_stats: Mapping[str, Any]
    postflight_stats: Mapping[str, Any]
    postflight_pending_games: int
    frozen_commit: str
    output_path: str


def _configuration(game: Mapping[str, Any]) -> dict[str, Any]:
    state = game.get("game_state", {})
    family = str(game.get("game_family", "unknown"))
    keys = {
        "bargaining": (
            "complete_information", "horizon_known", "max_rounds", "messages_allowed",
            "money_to_divide", "delta_1", "delta_2",
        ),
        "negotiation": (
            "complete_information", "horizon_known", "max_rounds", "messages_allowed",
            "player_1_role", "player_2_role", "player_1_value", "player_2_value",
            "product_price_order",
        ),
        "persuasion": (
            "p", "v", "u", "product_price", "total_rounds", "seller_message_type",
            "is_seller_know_cv",
        ),
    }.get(family, ())
    return {key: state[key] for key in keys if key in state}


def _terminal_result(terminal: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(terminal, Mapping):
        return {}
    result = terminal.get("result")
    return result if isinstance(result, Mapping) else terminal


def _family_rating(stats: Mapping[str, Any], family: str) -> Any:
    score = stats.get("scores", {}).get(family, {}) if isinstance(stats.get("scores"), Mapping) else {}
    return score.get("rating") if isinstance(score, Mapping) else None


class PilotRecorder:
    """Strategy/event adapter that requests a graceful drain on declared stop events."""

    def __init__(
        self,
        *,
        client: CompetitionClient,
        family: str,
        output_path: Path,
        frozen_commit: str,
        agent: LeaderboardAgent | None = None,
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = output_path.open("x", encoding="utf-8")
        self.client = client
        self.family = family
        self.output_path = output_path
        self.frozen_commit = frozen_commit
        self.agent = agent or LeaderboardAgent()
        self.hard_stop_reasons: list[str] = []
        self.strategic_review_cells: list[str] = []
        self.game_metadata: dict[str, dict[str, Any]] = {}
        self.floor_history: dict[tuple[str, str], list[bool]] = {}
        self.latest_stats: Mapping[str, Any] = {}

    def close(self) -> None:
        self._stream.close()

    def write(self, event: str, **fields: Any) -> None:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "family": self.family,
            "frozen_commit": self.frozen_commit,
            **fields,
        }
        self._stream.write(json.dumps(payload, sort_keys=True, default=str) + "\n")
        self._stream.flush()

    def request_hard_stop(self, reason: str, **evidence: Any) -> None:
        if reason not in self.hard_stop_reasons:
            self.hard_stop_reasons.append(reason)
            self.write(HARD_OPERATIONAL_STOP, reason=reason, evidence=evidence)

    def stop_requested(self) -> bool:
        return bool(self.hard_stop_reasons or self.strategic_review_cells)

    def strategy(self, game: dict[str, Any]) -> dict[str, Any]:
        game_id = str(game["game_id"])
        if self.stop_requested():
            action = validate_action(fallback_action(game), game)
            self.write("drain_fallback_action", game_id=game_id, action=action)
            return action
        action, diagnostics = self.agent.decide_with_diagnostics(game)
        route = diagnostics.routing
        metadata = self.game_metadata.setdefault(
            game_id,
            {
                "cell": route.cell,
                "role": route.role,
                "configuration": _configuration(game),
                "your_player": game.get("your_player"),
                "opponent": game.get("opponent"),
                "rating_before": _family_rating(self.latest_stats, self.family),
                "selected_incumbent": route.selected_policy,
                "own_value": game.get("game_state", {}).get(
                    f"{game.get('your_player')}_value"
                ),
            },
        )
        self.write(
            "policy_decision",
            game_id=game_id,
            configuration=metadata["configuration"],
            role=route.role,
            opponent=game.get("opponent"),
            state=game.get("game_state"),
            valid_actions=game.get("valid_actions"),
            routing=route.structured(),
            action=action,
            latency_seconds={
                "parsing": diagnostics.parsing_seconds,
                "routing_policy": diagnostics.routing_policy_seconds,
                "communication": diagnostics.communication_seconds,
                "validation": diagnostics.validation_seconds,
                "total": diagnostics.total_seconds,
            },
        )
        if route.selected_policy == "SAFE_LEGAL_FALLBACK" or (
            route.fallback_reason and "UNSUPPORTED_CELL" in route.fallback_reason
        ):
            self.request_hard_stop("UNSUPPORTED_CELL", game_id=game_id, routing=route.structured())
        if route.execution_fallback_reason is not None:
            self.request_hard_stop(
                "PRODUCTION_POLICY_EXECUTION_FALLBACK",
                game_id=game_id,
                routing=route.structured(),
            )
        if diagnostics.total_seconds > POLICY_MAX_BUDGET_SECONDS:
            self.request_hard_stop(
                "POLICY_NEAR_TIMEOUT",
                game_id=game_id,
                total_seconds=diagnostics.total_seconds,
            )
        return action

    def supervisor_event(self, event: dict[str, Any]) -> None:
        kind = str(event.get("event"))
        self.write("supervisor_event", supervisor=event)
        if kind == "strategy_fallback":
            self.request_hard_stop("OUTERMOST_NEVER_RAISE_FALLBACK", supervisor=event)
        elif kind == "action_result":
            result = event.get("result")
            if isinstance(result, Mapping) and result.get("valid") is False:
                self.request_hard_stop("INVALID_ACTION_REJECTED", supervisor=event)
        elif kind in {"unexpected_extra_game", "run_timeout"}:
            self.request_hard_stop(kind.upper(), supervisor=event)
        elif kind == "game_completed":
            self._record_completion(event)

    def _record_completion(self, event: Mapping[str, Any]) -> None:
        game_id = str(event.get("game_id"))
        metadata = self.game_metadata.get(game_id, {})
        terminal = event.get("terminal") if isinstance(event.get("terminal"), Mapping) else {}
        result = _terminal_result(terminal)
        try:
            self.latest_stats = self.client.stats()
        except Exception as exc:
            self.write("rating_poll_error", game_id=game_id, error_type=type(exc).__name__)
        player = metadata.get("your_player")
        payoff = result.get(f"{player}_payoff") if player else None
        outcome = str(result.get("outcome", terminal.get("status", ""))).lower()
        cell = str(metadata.get("cell", "unknown"))
        role = str(metadata.get("role", "unknown"))
        rating_after = _family_rating(self.latest_stats, self.family)
        transformed_payoff = None
        if self.family == "negotiation" and isinstance(payoff, (int, float)):
            own_value = metadata.get("own_value")
            if isinstance(own_value, (int, float)):
                transformed_payoff = negotiation_payoff_transform(
                    float(payoff), float(own_value)
                ).structured()
        self.write(
            "game_result",
            game_id=game_id,
            configuration=metadata.get("configuration"),
            cell=cell,
            role=role,
            opponent=metadata.get("opponent"),
            selected_incumbent=metadata.get("selected_incumbent"),
            terminal=terminal,
            outcome=outcome,
            raw_payoff=payoff,
            transformed_payoff=transformed_payoff,
            rating_before=metadata.get("rating_before"),
            rating_after=rating_after,
        )
        key = (cell, role)
        floor = outcome in PAYOFF_FLOOR_OUTCOMES
        observations = self.floor_history.setdefault(key, [])
        observations.append(floor)
        if len(observations) >= 3 and all(observations) and cell not in self.strategic_review_cells:
            self.strategic_review_cells.append(cell)
            self.write(
                STRATEGIC_REVIEW_REQUIRED,
                cell=cell,
                role=role,
                reason="THREE_OR_MORE_SAME_CELL_ROLE_OUTCOMES_AT_NO_DEAL_FLOOR",
                observations=len(observations),
            )


def run_pilot(
    client: CompetitionClient,
    *,
    family: str,
    max_games: int,
    output_path: Path,
    frozen_commit: str,
    poll_interval: float = 4.0,
    safety_timeout: float = 3_600.0,
) -> PilotResult:
    recorder = PilotRecorder(
        client=client,
        family=family,
        output_path=output_path,
        frozen_commit=frozen_commit,
    )
    preflight_stats: Mapping[str, Any] = {}
    postflight_stats: Mapping[str, Any] = {}
    postflight_pending = -1
    bounded: BoundedRunResult | None = None
    try:
        preflight_stats = client.stats()
        preflight_pending = client.pending_games()
        recorder.latest_stats = preflight_stats
        recorder.write(
            "pilot_preflight",
            stats=preflight_stats,
            pending_games=len(preflight_pending),
            max_games=max_games,
            concurrency=1,
            requeue=True,
            poll_interval=poll_interval,
            safety_timeout=safety_timeout,
        )
        if int(preflight_stats.get("active_games", 0)) != 0 or preflight_pending:
            recorder.request_hard_stop("NON_IDLE_PREFLIGHT")
            raise RuntimeError("pilot requires no active or pending games")
        bounded = client.run_bounded(
            recorder.strategy,
            game_family=family,
            max_games=max_games,
            concurrency=1,
            requeue=True,
            poll_interval=poll_interval,
            safety_timeout=safety_timeout,
            event_sink=recorder.supervisor_event,
            stop_requested=recorder.stop_requested,
        )
    except BoundedRunTimeout:
        recorder.request_hard_stop("BOUNDED_SUPERVISOR_TIMEOUT")
        raise
    finally:
        try:
            client.leave_queue()
        except Exception as exc:
            recorder.request_hard_stop("QUEUE_CLEANUP_FAILED", error_type=type(exc).__name__)
        try:
            postflight_stats = client.stats()
            postflight_pending = len(client.pending_games())
            recorder.write(
                "pilot_postflight",
                stats=postflight_stats,
                pending_games=postflight_pending,
                active_games=postflight_stats.get("active_games"),
            )
        finally:
            recorder.close()
    if bounded is None:
        raise RuntimeError("pilot did not start")
    return PilotResult(
        family=family,
        requested_games=max_games,
        completed_games=len(bounded.completed_game_ids),
        exit_reason=bounded.exit_reason,
        hard_stop_reasons=tuple(recorder.hard_stop_reasons),
        strategic_review_cells=tuple(recorder.strategic_review_cells),
        preflight_stats=preflight_stats,
        postflight_stats=postflight_stats,
        postflight_pending_games=postflight_pending,
        frozen_commit=frozen_commit,
        output_path=str(output_path),
    )


def result_json(result: PilotResult) -> str:
    return json.dumps(asdict(result), sort_keys=True, default=str)

"""Frozen-policy finite pilot orchestration and structured safety logging."""

from __future__ import annotations

import json
import math
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
from leaderboard.policy_router import RoutingDecision
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
NO_PROGRESS_REPEAT_LIMIT = 3


@dataclass(frozen=True, slots=True)
class PilotResult:
    family: str
    requested_games: int
    completed_games: int
    exit_reason: str
    hard_stop_reasons: tuple[str, ...]
    strategic_review_cells: tuple[str, ...]
    strategic_review_classes: tuple[str, ...]
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


def structural_policy_class(
    game: Mapping[str, Any], routing: RoutingDecision
) -> str:
    """Aggregate policy-equivalent states while omitting nuisance monetary scales."""
    state = game.get("game_state", {})
    family = str(game.get("game_family", "unknown"))
    role = routing.role or "unknown-role"
    policy = routing.selected_policy
    if family in {"negotiation", "bargaining"}:
        information = "complete-info" if state.get("complete_information") else "incomplete-info"
        if state.get("horizon_known") is False:
            horizon = "unknown-horizon"
        elif int(state.get("max_rounds", 0)) == 1:
            horizon = "T1"
        else:
            horizon = "finite-horizon"
        return f"{family}/{information}/{horizon}/{role}/{policy}"
    if family == "persuasion":
        horizon = "repeated" if int(state.get("total_rounds", 1)) > 1 else "one-shot"
        return f"persuasion/{role}/{horizon}/{policy}"
    return f"{family}/{role}/{policy}"


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
        self.strategic_review_classes: list[str] = []
        self.game_metadata: dict[str, dict[str, Any]] = {}
        self.floor_history: dict[tuple[str, str], list[bool]] = {}
        self.structural_zero_history: dict[str, list[bool]] = {}
        self.no_progress: dict[str, tuple[str, int]] = {}
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
        # Strategic events are report/review gates, not operational hard stops. The
        # frozen bounded family completes unless one of the declared hard-stop events fires.
        return bool(self.hard_stop_reasons)

    def strategy(self, game: dict[str, Any]) -> dict[str, Any]:
        game_id = str(game["game_id"])
        if self.stop_requested():
            action = validate_action(fallback_action(game), game)
            self.write("drain_fallback_action", game_id=game_id, action=action)
            return action
        action, diagnostics = self.agent.decide_with_diagnostics(game)
        route = diagnostics.routing
        structural_class = structural_policy_class(game, route)
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
                "selected_policy": route.selected_policy,
                "baseline_policy": route.baseline_policy,
                "experimental_policy": route.experimental_policy,
                "authorization_status": route.authorization_status,
                "authorization_source": route.authorization_source,
                "structural_policy_class": structural_class,
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
            structural_policy_class=structural_class,
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
        details = route.policy_details
        if (
            route.selected_policy == "NEGOTIATION_ADAPTIVE"
            and details.get("opponent_offer_improved") is True
            and details.get("continuation_available") is True
            and action.get("decision") == "RejectOffer"
            and details.get("proposal_materially_changed") is False
        ):
            structural = metadata["structural_policy_class"]
            if structural not in self.strategic_review_classes:
                self.strategic_review_classes.append(structural)
                self.write(
                    STRATEGIC_REVIEW_REQUIRED,
                    structural_policy_class=structural,
                    reason="ADAPTIVE_IGNORED_MATERIALLY_IMPROVING_OPPONENT_OFFER",
                    game_id=game_id,
                    policy_details=details,
                )
        if (
            route.authorization_status == "HUMAN_AUTHORIZED_EXPERIMENTAL"
            and details.get("rule_invariants_satisfied") is False
        ):
            structural = metadata["structural_policy_class"]
            if structural not in self.strategic_review_classes:
                self.strategic_review_classes.append(structural)
                self.write(
                    STRATEGIC_REVIEW_REQUIRED,
                    structural_policy_class=structural,
                    reason="EXPERIMENTAL_ACTION_DOMINATED_UNDER_OWN_STATED_RULE",
                    game_id=game_id,
                    policy_details=details,
                )
        cycle = self._no_progress_cycle(game_id, game, action)
        if cycle is not None:
            self.request_hard_stop(
                "DETERMINISTIC_NO_PROGRESS_CYCLE",
                game_id=game_id,
                repeated_signature=cycle,
                repeat_count=NO_PROGRESS_REPEAT_LIMIT,
            )
            safe_action = validate_action(fallback_action(game), game)
            self.write(
                "pilot_safety_action",
                game_id=game_id,
                replaces_action=action,
                action=safe_action,
                reason="DETERMINISTIC_NO_PROGRESS_CYCLE",
            )
            return safe_action
        return action

    def _no_progress_cycle(
        self,
        game_id: str,
        game: Mapping[str, Any],
        action: Mapping[str, Any],
    ) -> str | None:
        """Detect a repeating offer/response pair only in mechanisms without a cap."""
        state = game.get("game_state", {})
        if (
            self.family not in {"bargaining", "negotiation"}
            or state.get("horizon_known") is not False
            or game.get("valid_actions", {}).get("type") != "decision"
        ):
            return None
        last_offer = state.get("last_offer")
        if not isinstance(last_offer, Mapping):
            return None
        if self.family == "negotiation":
            observed = {"price": last_offer.get("price")}
        else:
            observed = {
                "player_1_gain": last_offer.get("player_1_gain"),
                "player_2_gain": last_offer.get("player_2_gain"),
            }
        economic_action = {key: value for key, value in action.items() if key != "message"}
        signature = json.dumps(
            {"observed_offer": observed, "economic_action": economic_action},
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        )
        previous, count = self.no_progress.get(game_id, ("", 0))
        count = count + 1 if signature == previous else 1
        self.no_progress[game_id] = (signature, count)
        return signature if count >= NO_PROGRESS_REPEAT_LIMIT else None

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
        scale_adjusted_payoff = None
        if self.family == "negotiation" and isinstance(payoff, (int, float)):
            own_value = metadata.get("own_value")
            if isinstance(own_value, (int, float)):
                transformed_payoff = negotiation_payoff_transform(
                    float(payoff), float(own_value)
                ).structured()
                scale_adjusted_payoff = transformed_payoff.get("Y_t")
        elif self.family == "bargaining" and isinstance(payoff, (int, float)):
            money = metadata.get("configuration", {}).get("money_to_divide")
            if isinstance(money, (int, float)) and money > 0:
                scale_adjusted_payoff = float(payoff) / float(money)
        structural_class = str(metadata.get("structural_policy_class", "unknown"))
        self.write(
            "game_result",
            game_id=game_id,
            configuration=metadata.get("configuration"),
            cell=cell,
            role=role,
            opponent=metadata.get("opponent"),
            selected_incumbent=metadata.get("selected_incumbent"),
            selected_policy=metadata.get("selected_policy"),
            baseline_policy=metadata.get("baseline_policy"),
            experimental_policy=metadata.get("experimental_policy"),
            authorization_status=metadata.get("authorization_status"),
            authorization_source=metadata.get("authorization_source"),
            structural_policy_class=structural_class,
            terminal=terminal,
            outcome=outcome,
            raw_payoff=payoff,
            transformed_payoff=transformed_payoff,
            scale_adjusted_payoff=scale_adjusted_payoff,
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
        zero = isinstance(payoff, (int, float)) and math.isclose(
            float(payoff), 0.0, rel_tol=0.0, abs_tol=1e-12
        )
        structural_observations = self.structural_zero_history.setdefault(
            structural_class, []
        )
        structural_observations.append(zero)
        if (
            len(structural_observations) >= 2
            and all(structural_observations)
            and structural_class not in self.strategic_review_classes
        ):
            self.strategic_review_classes.append(structural_class)
            self.write(
                STRATEGIC_REVIEW_REQUIRED,
                structural_policy_class=structural_class,
                reason="TWO_OR_MORE_STRUCTURAL_POLICY_CLASS_ZERO_PAYOFFS",
                observations=len(structural_observations),
                selected_policy=metadata.get("selected_policy"),
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
    agent: LeaderboardAgent | None = None,
) -> PilotResult:
    recorder = PilotRecorder(
        client=client,
        family=family,
        output_path=output_path,
        frozen_commit=frozen_commit,
        agent=agent,
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
            experimental_override_registry=recorder.agent.router.experimental_overrides.contents(),
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
        strategic_review_classes=tuple(recorder.strategic_review_classes),
        preflight_stats=preflight_stats,
        postflight_stats=postflight_stats,
        postflight_pending_games=postflight_pending,
        frozen_commit=frozen_commit,
        output_path=str(output_path),
    )


def result_json(result: PilotResult) -> str:
    return json.dumps(asdict(result), sort_keys=True, default=str)

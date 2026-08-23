"""Frozen randomized-cohort execution, payoff transforms, and evidence logging."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from eprocess.cohort import COHORT_ID, FAMILY_CAP, family_subcohort_id
from eprocess.store import CohortStore
from glee.client import CompetitionClient
from glee.normalization import (
    bargaining_bounds,
    negotiation_payoff_transform,
    normalize_payoff,
    persuasion_bounds,
)
from glee.supervisor import BoundedRunResult
from leaderboard.agent import LeaderboardAgent


@dataclass(frozen=True, slots=True)
class CohortFamilyResult:
    cohort_id: str
    subcohort_id: str
    family: str
    frozen_commit: str
    family_cap: int
    invocation_completed_games: int
    cumulative_assigned_games: int
    cumulative_completed_games: int
    exit_reason: str
    output_path: str


def _terminal_result(terminal: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(terminal, Mapping):
        return {}
    result = terminal.get("result")
    return result if isinstance(result, Mapping) else terminal


def bounded_payoff(
    *,
    family: str,
    role: str,
    raw_payoff: float,
    configuration: Mapping[str, Any],
) -> tuple[float, dict[str, Any]]:
    """Apply the frozen, family-specific bounded research transform."""
    raw = float(raw_payoff)
    if family == "negotiation":
        value_key = "player_1_value" if role == "seller" else "player_2_value"
        if value_key not in configuration:
            raise ValueError("negotiation transform requires own reservation/value")
        transform = negotiation_payoff_transform(raw, float(configuration[value_key]))
        return transform.score, transform.structured()
    if family == "bargaining":
        bounds = bargaining_bounds(float(configuration["money_to_divide"]))
        score = normalize_payoff(raw, bounds)
        return score, {
            "name": "bargaining_mechanism_bounds_v1",
            "minimum": bounds.minimum,
            "maximum": bounds.maximum,
            "raw_payoff": raw,
            "Y_t": score,
            "clipping_occurred": False,
        }
    if family == "persuasion":
        price = float(configuration["product_price"])
        rounds = int(configuration["total_rounds"])
        low = float(configuration.get("u", 0.0))
        high = float(configuration.get("v", 0.0))
        bounds = persuasion_bounds(
            role,  # type: ignore[arg-type]
            total_rounds=rounds,
            price=price,
            low_value=low,
            high_value=high,
            money_scale=1.0,
        )
        if bounds.maximum == bounds.minimum:
            score = 0.5
            degenerate = True
        else:
            score = normalize_payoff(raw, bounds)
            degenerate = False
        return score, {
            "name": "persuasion_mechanism_bounds_v1",
            "minimum": bounds.minimum,
            "maximum": bounds.maximum,
            "raw_payoff": raw,
            "Y_t": score,
            "degenerate_support": degenerate,
            "clipping_occurred": False,
        }
    raise ValueError(f"unsupported family {family!r}")


class CohortRecorder:
    """Bind one family supervisor to the central assignment/evidence store."""

    def __init__(
        self,
        *,
        client: CompetitionClient,
        family: str,
        output_path: Path,
        frozen_commit: str,
        store: CohortStore,
        agent: LeaderboardAgent,
        resume: bool = False,
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = output_path.open("a" if resume else "x", encoding="utf-8")
        self.client = client
        self.family = family
        self.output_path = output_path
        self.frozen_commit = frozen_commit
        self.store = store
        self.agent = agent
        self.game_metadata: dict[str, dict[str, Any]] = {}
        self.invalid_games: dict[str, str] = {}

    def close(self) -> None:
        self._stream.close()

    def write(self, event: str, **fields: Any) -> None:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "cohort_id": COHORT_ID,
            "subcohort_id": family_subcohort_id(self.family),
            "family": self.family,
            "frozen_commit": self.frozen_commit,
            **fields,
        }
        self._stream.write(json.dumps(payload, sort_keys=True, default=str) + "\n")
        self._stream.flush()

    def _invalidate(self, game_id: str, reason: str, **evidence: Any) -> None:
        self.invalid_games.setdefault(game_id, reason)
        self.store.safety_pause_for_game(game_id, reason=reason)
        self.write("EVIDENCE_TRACE_INVALIDATED", game_id=game_id, reason=reason, evidence=evidence)

    def strategy(self, game: dict[str, Any]) -> dict[str, Any]:
        game_id = str(game["game_id"])
        action, diagnostics = self.agent.decide_with_diagnostics(game)
        route = diagnostics.routing
        assignment = self.store.assignment(game_id)
        if assignment is None:
            raise RuntimeError("policy action generated without atomic assignment")
        metadata = self.game_metadata.setdefault(
            game_id,
            {
                "your_player": game.get("your_player"),
                "role": assignment.role,
                "configuration": dict(assignment.exact_configuration),
                "structural_cell": assignment.structural_cell,
                "assignment": assignment.structured(),
                "selected_policy": route.selected_policy,
            },
        )
        if metadata["selected_policy"] != route.selected_policy:
            self._invalidate(
                game_id,
                "POLICY_CHANGED_WITHIN_GAME",
                prior=metadata["selected_policy"],
                current=route.selected_policy,
            )
        if assignment.experiment_id is not None and route.selected_policy != assignment.assigned_policy:
            self._invalidate(
                game_id,
                "ASSIGNED_POLICY_UNAVAILABLE_OR_NOT_EXECUTED",
                assigned_policy=assignment.assigned_policy,
                selected_policy=route.selected_policy,
                fallback_reason=route.fallback_reason,
            )
        if route.execution_fallback_reason is not None:
            self._invalidate(
                game_id,
                "POLICY_EXECUTION_FALLBACK",
                routing=route.structured(),
            )
        if route.selected_policy == "SAFE_LEGAL_FALLBACK":
            self._invalidate(game_id, "UNSUPPORTED_CELL", routing=route.structured())
        current_assignment = self.store.assignment(game_id)
        self.write(
            "policy_decision",
            game_id=game_id,
            exact_configuration=metadata["configuration"],
            structural_cell=metadata["structural_cell"],
            role=assignment.role,
            opponent=game.get("opponent"),
            assignment=(
                current_assignment.structured()
                if current_assignment is not None
                else assignment.structured()
            ),
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
        return action

    def supervisor_event(self, event: dict[str, Any]) -> None:
        self.write("supervisor_event", supervisor=event)
        kind = str(event.get("event"))
        game_id = str(event.get("game_id", "unknown"))
        if kind == "game_tracked":
            self.store.record_tracked_game(
                game_id,
                family=self.family,
                family_cap=FAMILY_CAP,
            )
        elif kind == "strategy_fallback":
            self._invalidate(
                game_id,
                "OUTERMOST_NEVER_RAISE_FALLBACK",
                supervisor=event,
            )
        elif kind == "action_result":
            result = event.get("result")
            if isinstance(result, Mapping) and result.get("valid") is False:
                self._invalidate(game_id, "INVALID_ACTION_REJECTED", supervisor=event)
        elif kind == "game_completed":
            self.store.record_completed_game(
                game_id,
                reason=str(event.get("completion_reason", "UNKNOWN")),
            )
            self._record_completion(event)

    def _record_completion(self, event: Mapping[str, Any]) -> None:
        game_id = str(event.get("game_id"))
        assignment = self.store.assignment(game_id)
        metadata = self.game_metadata.get(game_id, {})
        terminal = event.get("terminal") if isinstance(event.get("terminal"), Mapping) else {}
        result = _terminal_result(terminal)
        player = metadata.get("your_player")
        raw = result.get(f"{player}_payoff") if player else None
        outcome = str(result.get("outcome", terminal.get("status", ""))).lower()
        valid = (
            assignment is not None
            and isinstance(raw, (int, float))
            and bool(outcome)
            and game_id not in self.invalid_games
        )
        score: float | None = None
        transform: dict[str, Any] | None = None
        exclusion = self.invalid_games.get(game_id)
        if valid and assignment is not None:
            try:
                score, transform = bounded_payoff(
                    family=self.family,
                    role=assignment.role,
                    raw_payoff=float(raw),
                    configuration=assignment.exact_configuration,
                )
            except Exception as exc:
                valid = False
                exclusion = f"PAYOFF_TRANSFORM_FAILURE:{type(exc).__name__}"
                self.store.safety_pause_for_game(game_id, reason=exclusion)
        if assignment is None:
            exclusion = exclusion or "NO_PRETREATMENT_ASSIGNMENT"
        elif not isinstance(raw, (int, float)) or not outcome:
            exclusion = exclusion or "TERMINAL_RESULT_UNAVAILABLE"
            self.store.safety_pause_for_game(game_id, reason=exclusion)

        evidence_update: dict[str, Any] | None = None
        if assignment is not None:
            evidence_update = self.store.record_outcome(
                game_id,
                raw_payoff=float(raw) if isinstance(raw, (int, float)) else None,
                bounded_payoff=score,
                payoff_transform=transform,
                terminal_outcome=outcome,
                valid_trace=valid,
                exclusion_reason=exclusion,
            )
        self.write(
            "game_result",
            game_id=game_id,
            assignment=assignment.structured() if assignment else None,
            terminal=terminal,
            terminal_outcome=outcome,
            raw_payoff=raw,
            bounded_payoff=score,
            payoff_transform=transform,
            valid_trace=valid,
            exclusion_reason=exclusion,
            evidence_update=evidence_update,
        )


def run_cohort_family(
    client: CompetitionClient,
    *,
    family: str,
    output_path: Path,
    store: CohortStore,
    frozen_commit: str,
    agent: LeaderboardAgent,
    poll_interval: float = 12.0,
    safety_timeout: float = 172_800.0,
    resume: bool = False,
) -> CohortFamilyResult:
    """Run one family to its shared 1,000-game cap without crossing it."""
    store.initialize()
    counts = store.family_counts(family)
    if counts["tracked"] > FAMILY_CAP or counts["completed"] > FAMILY_CAP:
        raise RuntimeError("family store already exceeds its frozen cap")
    preflight_pending = [
        game
        for game in client.pending_games()
        if game.to_strategy_payload().get("game_family") == family
    ]
    outstanding = counts["tracked"] - counts["completed"]
    if outstanding != len(preflight_pending):
        raise RuntimeError(
            "stored incomplete-game count does not match authoritative family pending state"
        )
    if counts["tracked"] and not resume:
        raise RuntimeError("existing family cohort state requires --resume")
    remaining_completions = FAMILY_CAP - counts["completed"]
    if remaining_completions == 0:
        store.close_running_experiments(family)
        return CohortFamilyResult(
            COHORT_ID,
            family_subcohort_id(family),
            family,
            frozen_commit,
            FAMILY_CAP,
            0,
            counts["assigned"],
            counts["completed"],
            "FAMILY_CAP_ALREADY_COMPLETE",
            str(output_path),
        )

    recorder = CohortRecorder(
        client=client,
        family=family,
        output_path=output_path,
        frozen_commit=frozen_commit,
        store=store,
        agent=agent,
        resume=resume,
    )
    bounded: BoundedRunResult | None = None
    try:
        recorder.write(
            "cohort_preflight",
            family_counts=counts,
            pending_family_games=len(preflight_pending),
            experiment_registry=agent.router.experimental_overrides.contents(),
            family_cap=FAMILY_CAP,
            remaining_completions=remaining_completions,
            concurrency=1,
            requeue=True,
            poll_interval=poll_interval,
            safety_timeout=safety_timeout,
        )
        bounded = client.run_bounded(
            recorder.strategy,
            game_family=family,
            max_games=remaining_completions,
            concurrency=1,
            requeue=True,
            poll_interval=poll_interval,
            safety_timeout=safety_timeout,
            event_sink=recorder.supervisor_event,
            resume_existing=bool(preflight_pending),
            allow_other_active_families=True,
        )
    finally:
        try:
            client.leave_queue(family)
        finally:
            recorder.close()
    if bounded is None:
        raise RuntimeError("family cohort supervisor did not start")
    final_counts = store.family_counts(family)
    if final_counts["tracked"] > FAMILY_CAP:
        raise RuntimeError("family live-game cap was exceeded")
    if final_counts["completed"] >= FAMILY_CAP:
        store.close_running_experiments(family)
    return CohortFamilyResult(
        COHORT_ID,
        family_subcohort_id(family),
        family,
        frozen_commit,
        FAMILY_CAP,
        len(bounded.completed_game_ids),
        final_counts["assigned"],
        final_counts["completed"],
        bounded.exit_reason,
        str(output_path),
    )

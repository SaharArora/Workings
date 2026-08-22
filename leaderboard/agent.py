"""Production agent: economic routing first, communication rendering second."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from communication.strategic import render
from glee.actions import validate_action, validate_game_envelope
from leaderboard.policy_router import PolicyRouter, RoutingDecision


@dataclass(frozen=True, slots=True)
class DecisionDiagnostics:
    parsing_seconds: float
    routing_policy_seconds: float
    communication_seconds: float
    validation_seconds: float
    total_seconds: float
    routing: RoutingDecision


class LeaderboardAgent:
    def __init__(self, router: PolicyRouter | None = None) -> None:
        self.router = router or PolicyRouter()

    def decide(self, game: dict[str, Any]) -> dict[str, Any]:
        action, _ = self.decide_with_diagnostics(game)
        return action

    def decide_with_routing(
        self, game: dict[str, Any]
    ) -> tuple[dict[str, Any], RoutingDecision]:
        action, diagnostics = self.decide_with_diagnostics(game)
        return action, diagnostics.routing

    def decide_with_diagnostics(
        self, game: dict[str, Any]
    ) -> tuple[dict[str, Any], DecisionDiagnostics]:
        started = perf_counter()
        validate_game_envelope(game)
        parsed = perf_counter()
        economic_action, routing = self.router.decide_with_routing(game)
        routed = perf_counter()
        rendered_action = render(economic_action, game)
        rendered = perf_counter()
        action = validate_action(rendered_action, game)
        finished = perf_counter()
        return action, DecisionDiagnostics(
            parsing_seconds=parsed - started,
            routing_policy_seconds=routed - parsed,
            communication_seconds=rendered - routed,
            validation_seconds=finished - rendered,
            total_seconds=finished - started,
            routing=routing,
        )

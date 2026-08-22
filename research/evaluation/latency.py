"""Reproducible end-to-end production policy latency measurement."""

from __future__ import annotations

import math
import statistics
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from leaderboard.agent import LeaderboardAgent

COMPETITION_TURN_LIMIT_SECONDS = 120.0
POLICY_P95_BUDGET_SECONDS = 10.0
POLICY_MAX_BUDGET_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class LatencySummary:
    path: str
    family: str
    selected_policy: str
    iterations: int
    median_seconds: float
    p95_seconds: float
    max_seconds: float
    median_components_seconds: Mapping[str, float]
    within_budget: bool

    def structured(self) -> dict[str, Any]:
        value = asdict(self)
        value["median_components_seconds"] = dict(self.median_components_seconds)
        return value


def _p95(values: list[float]) -> float:
    return sorted(values)[max(0, math.ceil(0.95 * len(values)) - 1)]


def benchmark_policy_paths(
    games: Mapping[str, dict[str, Any]],
    *,
    iterations: int = 500,
) -> tuple[LatencySummary, ...]:
    if iterations < 1:
        raise ValueError("iterations must be positive")
    summaries: list[LatencySummary] = []
    for name, game in games.items():
        agent = LeaderboardAgent()
        agent.decide_with_diagnostics(game)  # warm caches and imports
        total: list[float] = []
        components: dict[str, list[float]] = {
            "parsing": [],
            "routing_policy": [],
            "communication": [],
            "validation": [],
        }
        selected = ""
        for _ in range(iterations):
            _, diagnostics = agent.decide_with_diagnostics(game)
            if diagnostics.routing.execution_fallback_reason is not None:
                raise RuntimeError(f"{name} exercised an emergency fallback")
            selected = diagnostics.routing.selected_policy
            total.append(diagnostics.total_seconds)
            components["parsing"].append(diagnostics.parsing_seconds)
            components["routing_policy"].append(diagnostics.routing_policy_seconds)
            components["communication"].append(diagnostics.communication_seconds)
            components["validation"].append(diagnostics.validation_seconds)
        p95 = _p95(total)
        maximum = max(total)
        summaries.append(
            LatencySummary(
                path=name,
                family=str(game["game_family"]),
                selected_policy=selected,
                iterations=iterations,
                median_seconds=statistics.median(total),
                p95_seconds=p95,
                max_seconds=maximum,
                median_components_seconds={
                    key: statistics.median(values) for key, values in components.items()
                },
                within_budget=(
                    p95 <= POLICY_P95_BUDGET_SECONDS
                    and maximum <= POLICY_MAX_BUDGET_SECONDS
                ),
            )
        )
    return tuple(summaries)

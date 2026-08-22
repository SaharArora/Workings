"""Explicit, process-scoped authorization for bounded behavioral pilots."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping

HUMAN_AUTHORIZATION_SOURCE = "human_authorized_bounded_pilot"


class AuthorizationStatus(StrEnum):
    THEORY_INCUMBENT = "THEORY_INCUMBENT"
    PORTFOLIO_INCUMBENT = "PORTFOLIO_INCUMBENT"
    E_PROCESS_PROMOTED = "E_PROCESS_PROMOTED"
    HUMAN_AUTHORIZED_EXPERIMENTAL = "HUMAN_AUTHORIZED_EXPERIMENTAL"


@dataclass(frozen=True, slots=True)
class ExperimentalOverride:
    policy_name: str
    game_family: str
    baseline_policies: frozenset[str]
    configuration_scope: str
    seller_only: bool = False

    def structured(self) -> dict[str, Any]:
        return {
            "policy_name": self.policy_name,
            "game_family": self.game_family,
            "baseline_policies": sorted(self.baseline_policies),
            "configuration_scope": self.configuration_scope,
            "seller_only": self.seller_only,
        }


@dataclass(frozen=True, slots=True)
class OverrideResolution:
    override: ExperimentalOverride
    available: bool
    unavailable_reason: str | None


PILOT_OVERRIDES = (
    ExperimentalOverride(
        policy_name="NEGOTIATION_FAIRNESS_MARGIN",
        game_family="negotiation",
        baseline_policies=frozenset(
            {
                "NEGOTIATION_COMPLETE_T1_THEORY",
                "NEGOTIATION_COMPLETE_FINITE_ODD_THEORY",
                "NEGOTIATION_COMPLETE_FINITE_EVEN_THEORY",
            }
        ),
        configuration_scope="complete_information_and_finite_full_extraction_baseline",
    ),
    ExperimentalOverride(
        policy_name="NEGOTIATION_ADAPTIVE",
        game_family="negotiation",
        baseline_policies=frozenset(
            {"NEGOTIATION_INCOMPLETE_T1_ROBUST", "NEGOTIATION_ROBUST"}
        ),
        configuration_scope="incomplete_information_cells_with_static_robust_control",
    ),
    ExperimentalOverride(
        policy_name="BARGAINING_FAIRNESS",
        game_family="bargaining",
        baseline_policies=frozenset(),
        configuration_scope="all_reachable_bargaining_cells",
    ),
    ExperimentalOverride(
        policy_name="PERSUASION_P3_REPUTATION",
        game_family="persuasion",
        baseline_policies=frozenset({"PERSUASION_P0_BABBLING"}),
        configuration_scope="repeated_persuasion_seller_side",
        seller_only=True,
    ),
)


class ExperimentalOverrideRegistry:
    """Resolve only the challengers explicitly enabled for one bounded pilot process."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        authorization_source: str = HUMAN_AUTHORIZATION_SOURCE,
        population_positive_purchase_rate: float | None = None,
    ) -> None:
        self.enabled = bool(enabled)
        self.authorization_source = authorization_source
        self.population_positive_purchase_rate = population_positive_purchase_rate

    @classmethod
    def human_authorized_bounded_pilot(
        cls, *, population_positive_purchase_rate: float | None = None
    ) -> "ExperimentalOverrideRegistry":
        return cls(
            enabled=True,
            authorization_source=HUMAN_AUTHORIZATION_SOURCE,
            population_positive_purchase_rate=population_positive_purchase_rate,
        )

    def contents(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "authorization_source": self.authorization_source,
            "population_positive_purchase_rate_available": (
                self.population_positive_purchase_rate is not None
            ),
            "overrides": [item.structured() for item in PILOT_OVERRIDES],
        }

    def resolve(
        self,
        game: Mapping[str, Any],
        *,
        baseline_policy: str,
        role: str | None,
    ) -> OverrideResolution | None:
        if not self.enabled:
            return None
        family = str(game.get("game_family", ""))
        for override in PILOT_OVERRIDES:
            if override.game_family != family:
                continue
            if override.seller_only and role != "seller":
                continue
            if (
                override.baseline_policies
                and baseline_policy not in override.baseline_policies
            ):
                continue
            if override.policy_name == "PERSUASION_P3_REPUTATION":
                rate = self.population_positive_purchase_rate
                available = isinstance(rate, (int, float)) and 0 <= float(rate) <= 1
                return OverrideResolution(
                    override=override,
                    available=available,
                    unavailable_reason=None if available else "P3_EXPERIMENT_INPUT_UNAVAILABLE",
                )
            return OverrideResolution(override=override, available=True, unavailable_reason=None)
        return None

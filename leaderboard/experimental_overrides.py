"""Explicit, process-scoped authorization for bounded live challenger use."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping

HUMAN_AUTHORIZATION_SOURCE = "human_authorized_bounded_pilot"
HUMAN_TRANCHE_AUTHORIZATION_SOURCE = "human_authorized_time_constrained_tranche"


class AuthorizationStatus(StrEnum):
    THEORY_INCUMBENT = "THEORY_INCUMBENT"
    PORTFOLIO_INCUMBENT = "PORTFOLIO_INCUMBENT"
    E_PROCESS_PROMOTED = "E_PROCESS_PROMOTED"
    HUMAN_AUTHORIZED_EXPERIMENTAL = "HUMAN_AUTHORIZED_EXPERIMENTAL"
    HUMAN_AUTHORIZED_EXPERIMENTAL_DIAGNOSTIC = (
        "HUMAN_AUTHORIZED_EXPERIMENTAL_DIAGNOSTIC"
    )


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
    authorization_status: AuthorizationStatus = (
        AuthorizationStatus.HUMAN_AUTHORIZED_EXPERIMENTAL
    )


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


# This map is deliberately separate from ``PILOT_OVERRIDES``.  The earlier pilot
# authorized ADAPTIVE in every ROBUST cell and attempted P3 when its input existed.
# The time-constrained tranche instead keeps II/T=1 and the general incomplete-
# information portfolio on their incumbent paths, permits at most six diagnostic
# multi-round ADAPTIVE games, and keeps persuasion on P0.
TRANCHE_OVERRIDES = (
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
        baseline_policies=frozenset({"NEGOTIATION_ROBUST"}),
        configuration_scope=(
            "at_most_six_incomplete_information_multi_round_or_unknown_horizon_"
            "diagnostic_games"
        ),
    ),
    ExperimentalOverride(
        policy_name="BARGAINING_FAIRNESS",
        game_family="bargaining",
        baseline_policies=frozenset(),
        configuration_scope="all_reachable_bargaining_cells_where_defined",
    ),
)


def tranche_structural_class(
    game: Mapping[str, Any], policy_name: str, role: str | None
) -> str:
    """Return the predeclared scale-invariant tranche monitoring class."""
    state = game.get("game_state", {})
    family = str(game.get("game_family", "unknown"))
    if policy_name.startswith("BARGAINING_"):
        policy = policy_name.removeprefix("BARGAINING_")
        if not bool(state.get("complete_information")):
            return f"bargaining/{policy}/incomplete"
        horizon = "finite" if bool(state.get("horizon_known")) else "unlimited"
        return f"bargaining/{policy}/complete/{horizon}"
    if policy_name.startswith("NEGOTIATION_"):
        policy = policy_name.removeprefix("NEGOTIATION_")
        information = (
            "complete" if bool(state.get("complete_information")) else "incomplete"
        )
        if state.get("horizon_known") is False:
            horizon = "unknown-horizon"
        elif int(state.get("max_rounds", 0)) == 1:
            horizon = "T1"
        elif information == "incomplete":
            horizon = "multiround"
        else:
            horizon = "finite"
        return f"negotiation/{policy}/{information}/{horizon}"
    if policy_name.startswith("PERSUASION_"):
        policy = policy_name.removeprefix("PERSUASION_").split("_", 1)[0]
        return f"persuasion/{policy}/{role or 'unknown-role'}"
    return f"{family}/{policy_name}/{role or 'unknown-role'}"


class ExperimentalOverrideRegistry:
    """Resolve only the challengers explicitly enabled for one bounded pilot process."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        authorization_source: str = HUMAN_AUTHORIZATION_SOURCE,
        population_positive_purchase_rate: float | None = None,
        overrides: tuple[ExperimentalOverride, ...] = PILOT_OVERRIDES,
        adaptive_diagnostic_limit: int | None = None,
    ) -> None:
        self.enabled = bool(enabled)
        self.authorization_source = authorization_source
        self.population_positive_purchase_rate = population_positive_purchase_rate
        self.overrides = overrides
        self.adaptive_diagnostic_limit = adaptive_diagnostic_limit
        self.adaptive_diagnostic_game_ids: set[str] = set()
        self._adaptive_assignment: dict[str, bool] = {}
        self.paused_structural_classes: dict[str, str] = {}

    @classmethod
    def human_authorized_bounded_pilot(
        cls, *, population_positive_purchase_rate: float | None = None
    ) -> "ExperimentalOverrideRegistry":
        return cls(
            enabled=True,
            authorization_source=HUMAN_AUTHORIZATION_SOURCE,
            population_positive_purchase_rate=population_positive_purchase_rate,
        )

    @classmethod
    def human_authorized_tranche(
        cls, *, adaptive_diagnostic_limit: int = 6
    ) -> "ExperimentalOverrideRegistry":
        if adaptive_diagnostic_limit < 0:
            raise ValueError("adaptive_diagnostic_limit must be nonnegative")
        return cls(
            enabled=True,
            authorization_source=HUMAN_TRANCHE_AUTHORIZATION_SOURCE,
            overrides=TRANCHE_OVERRIDES,
            adaptive_diagnostic_limit=adaptive_diagnostic_limit,
        )

    def contents(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "authorization_source": self.authorization_source,
            "population_positive_purchase_rate_available": (
                self.population_positive_purchase_rate is not None
            ),
            "adaptive_diagnostic_limit": self.adaptive_diagnostic_limit,
            "adaptive_diagnostic_assigned": len(self.adaptive_diagnostic_game_ids),
            "adaptive_assignment_method": (
                "first_eligible_distinct_games_not_randomized"
                if self.adaptive_diagnostic_limit is not None
                else None
            ),
            "paused_structural_classes": dict(self.paused_structural_classes),
            "overrides": [item.structured() for item in self.overrides],
        }

    def pause_structural_class(self, structural_class: str, reason: str) -> None:
        """Prevent a paused challenger class from being assigned to future games."""
        self.paused_structural_classes.setdefault(structural_class, reason)

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
        for override in self.overrides:
            if override.game_family != family:
                continue
            if override.seller_only and role != "seller":
                continue
            if (
                override.baseline_policies
                and baseline_policy not in override.baseline_policies
            ):
                continue
            structural_class = tranche_structural_class(
                game, override.policy_name, role
            )
            game_id = str(game.get("game_id", ""))
            if override.policy_name == "NEGOTIATION_ADAPTIVE":
                if self.adaptive_diagnostic_limit is None:
                    return OverrideResolution(
                        override=override,
                        available=True,
                        unavailable_reason=None,
                    )
                state = game.get("game_state", {})
                eligible_cell = (
                    state.get("complete_information") is False
                    and (
                        state.get("horizon_known") is False
                        or (
                            isinstance(state.get("max_rounds"), int)
                            and int(state["max_rounds"]) > 1
                        )
                    )
                )
                if not eligible_cell:
                    continue
                # A game keeps its frozen assignment for its whole lifecycle.  A
                # stop-loss therefore changes only future games, never policy mid-game.
                assigned = self._adaptive_assignment.get(game_id)
                if assigned is None:
                    limit = int(self.adaptive_diagnostic_limit or 0)
                    assigned = (
                        structural_class not in self.paused_structural_classes
                        and len(self.adaptive_diagnostic_game_ids) < limit
                    )
                    self._adaptive_assignment[game_id] = assigned
                    if assigned:
                        self.adaptive_diagnostic_game_ids.add(game_id)
                if not assigned:
                    reason = self.paused_structural_classes.get(
                        structural_class, "ADAPTIVE_DIAGNOSTIC_CAP_REACHED"
                    )
                    return OverrideResolution(
                        override=override,
                        available=False,
                        unavailable_reason=reason,
                        authorization_status=(
                            AuthorizationStatus.HUMAN_AUTHORIZED_EXPERIMENTAL_DIAGNOSTIC
                        ),
                    )
                return OverrideResolution(
                    override=override,
                    available=True,
                    unavailable_reason=None,
                    authorization_status=(
                        AuthorizationStatus.HUMAN_AUTHORIZED_EXPERIMENTAL_DIAGNOSTIC
                    ),
                )
            if structural_class in self.paused_structural_classes:
                return OverrideResolution(
                    override=override,
                    available=False,
                    unavailable_reason=self.paused_structural_classes[structural_class],
                )
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

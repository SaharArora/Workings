"""Atomic pre-treatment policy assignment for the frozen randomized cohort."""

from __future__ import annotations

from typing import Any, Mapping

from eprocess.store import AssignmentRecord, CohortStore
from leaderboard.experimental_overrides import (
    AuthorizationStatus,
    ExperimentalOverride,
    OverrideResolution,
)
from leaderboard.policy_router import (
    persuasion_margin_buyer_action,
    persuasion_theory_buyer_action,
)

COHORT_AUTHORIZATION_SOURCE = "human_authorized_post_risk_fix_randomized_3000"


class CohortOverrideRegistry:
    """Resolve a persisted whole-game assignment before any policy action runs.

    Eligibility and the control/challenger draw use only the predeclared structural
    configuration. Repeated calls return the existing database row, so later offers,
    messages, qualities, and outcomes cannot change a game's arm or experiment.
    """

    authorization_source = COHORT_AUTHORIZATION_SOURCE
    population_positive_purchase_rate = None
    overrides: tuple[ExperimentalOverride, ...] = ()

    def __init__(self, store: CohortStore) -> None:
        self.store = store

    def contents(self) -> dict[str, Any]:
        snapshot = self.store.snapshot()
        return {
            "enabled": True,
            "authorization_source": self.authorization_source,
            "assignment_source": "atomic_sqlite_pre_treatment_registry",
            "cohort_metadata": snapshot["metadata"],
            "experiments": snapshot["experiments"],
        }

    def assignment(self, game_id: str) -> AssignmentRecord | None:
        return self.store.assignment(game_id)

    def pause_structural_class(self, structural_class: str, reason: str) -> None:
        # Cohort stopping is experiment-level, never ad hoc structural-class mutation.
        del structural_class, reason

    def resolve(
        self,
        game: Mapping[str, Any],
        *,
        baseline_policy: str,
        role: str | None,
    ) -> OverrideResolution | None:
        del role
        assignment = self.store.assign_game(game, baseline_policy=baseline_policy)
        if (
            assignment.experiment_id is None
            and assignment.assigned_policy == baseline_policy
        ):
            return None

        if assignment.experiment_id in {
            "PERS_BUY_MARGIN_VS_THEORY",
            "CONFIRM_PERS_BUY_MARGIN_VS_THEORY",
        }:
            theory = persuasion_theory_buyer_action(dict(game))
            margin = persuasion_margin_buyer_action(dict(game))
            if theory != margin:
                self.store.mark_informative(
                    assignment.game_id,
                    reason="BUYER_THEORY_AND_MARGIN_ACTIONS_DIVERGED",
                )
            elif not assignment.informative:
                self.store.mark_noninformative(
                    assignment.game_id,
                    reason="NONINFORMATIVE_ASSIGNMENT_IDENTICAL_BUYER_ACTIONS_SO_FAR",
                )

        override = ExperimentalOverride(
            policy_name=assignment.assigned_policy,
            game_family=assignment.family,
            baseline_policies=frozenset(),
            configuration_scope=assignment.experiment_id,
            seller_only=(assignment.role == "seller"),
        )
        return OverrideResolution(
            override=override,
            available=True,
            unavailable_reason=None,
            authorization_status=(
                AuthorizationStatus.E_PROCESS_PROMOTED
                if assignment.assignment_reason == "PROMOTED_POLICY_OBSERVATIONAL"
                else AuthorizationStatus.HUMAN_AUTHORIZED_EXPERIMENTAL
            ),
        )

from __future__ import annotations

from pathlib import Path
from typing import Any

from glee.pilot import PilotRecorder, structural_policy_class
from leaderboard.experimental_overrides import ExperimentalOverrideRegistry
from leaderboard.policy_router import PolicyRouter
from scripts.run_tranche import TRANCHE_GAME_LIMITS


class StatsClient:
    def stats(self) -> dict[str, Any]:
        return {
            "active_games": 0,
            "scores": {
                "bargaining": {"rating": 1000.0},
                "negotiation": {"rating": 1000.0},
                "persuasion": {"rating": 1000.0},
            },
        }


def bargaining_game(*, complete: bool, finite: bool) -> dict[str, Any]:
    state: dict[str, Any] = {
        "phase": "offer",
        "current_player": "player_1",
        "complete_information": complete,
        "horizon_known": finite,
        "messages_allowed": False,
        "money_to_divide": 100,
        "delta_1": 0.9,
        "delta_2": 0.8,
        "round": 1,
    }
    if finite:
        state["max_rounds"] = 4
    return {
        "game_id": "b",
        "game_family": "bargaining",
        "your_player": "player_1",
        "opponent": {"type": "agent", "name": "x"},
        "game_state": state,
        "valid_actions": {
            "type": "offer",
            "fields": {"alice_gain": "number", "bob_gain": "number"},
        },
    }


def test_locked_family_game_caps() -> None:
    assert TRANCHE_GAME_LIMITS == {
        "bargaining": 20,
        "negotiation": 20,
        "persuasion": 12,
    }


def test_scale_invariant_structural_classes_match_precommitment() -> None:
    router = PolicyRouter(
        experimental_overrides=ExperimentalOverrideRegistry.human_authorized_tranche()
    )
    complete_finite = bargaining_game(complete=True, finite=True)
    route = router.route(complete_finite)
    assert structural_policy_class(complete_finite, route) == (
        "bargaining/FAIRNESS/complete/finite"
    )
    incomplete = bargaining_game(complete=False, finite=False)
    incomplete["game_state"].pop("delta_1")
    route = router.route(incomplete)
    assert structural_policy_class(incomplete, route) == "bargaining/FAIRNESS/incomplete"


def _metadata(structural: str, selected_policy: str) -> dict[str, Any]:
    return {
        "cell": "cell",
        "role": "seller",
        "your_player": "player_1",
        "opponent": {"type": "hidden", "name": None},
        "configuration": {},
        "rating_before": 1000,
        "selected_incumbent": selected_policy,
        "selected_policy": selected_policy,
        "baseline_policy": "NEGOTIATION_ROBUST",
        "experimental_policy": selected_policy,
        "authorization_status": "HUMAN_AUTHORIZED_EXPERIMENTAL_DIAGNOSTIC",
        "authorization_source": "human_authorized_time_constrained_tranche",
        "structural_policy_class": structural,
        "own_value": 100,
        "policy_latencies": [0.001],
    }


def test_generic_structural_failure_rate_pauses_challenger_at_n_three(
    tmp_path: Path,
) -> None:
    registry = ExperimentalOverrideRegistry.human_authorized_tranche()
    recorder = PilotRecorder(
        client=StatsClient(),  # type: ignore[arg-type]
        family="negotiation",
        output_path=tmp_path / "tranche.jsonl",
        frozen_commit="frozen",
        agent=None,
    )
    recorder.agent.router.experimental_overrides = registry
    structural = "negotiation/ADAPTIVE/incomplete/multiround"
    for index, (outcome, payoff) in enumerate(
        (("no_deal", 0), ("agreement", 10), ("walked_away", 0))
    ):
        game_id = f"g-{index}"
        recorder.game_metadata[game_id] = _metadata(
            structural, "NEGOTIATION_ADAPTIVE"
        )
        recorder.supervisor_event(
            {
                "event": "game_completed",
                "game_id": game_id,
                "terminal": {
                    "result": {"outcome": outcome, "player_1_payoff": payoff}
                },
            }
        )
    recorder.close()
    assert recorder.paused_policy_classes[structural] == (
        "NON_UNAVOIDABLE_ZERO_NO_DEAL_OR_WALKAWAY_RATE_ABOVE_HALF"
    )
    assert registry.paused_structural_classes[structural].startswith("NON_UNAVOIDABLE")


def test_explicitly_unavoidable_failures_do_not_trigger_generic_rate_rule(
    tmp_path: Path,
) -> None:
    recorder = PilotRecorder(
        client=StatsClient(),  # type: ignore[arg-type]
        family="negotiation",
        output_path=tmp_path / "unavoidable.jsonl",
        frozen_commit="frozen",
    )
    structural = "negotiation/ROBUST/incomplete/multiround"
    for index, (outcome, payoff, unavoidable) in enumerate(
        (("no_deal", 0, True), ("agreement", 10, False), ("walked_away", 0, True))
    ):
        game_id = f"u-{index}"
        recorder.game_metadata[game_id] = _metadata(structural, "NEGOTIATION_ROBUST")
        recorder.supervisor_event(
            {
                "event": "game_completed",
                "game_id": game_id,
                "terminal": {
                    "result": {
                        "outcome": outcome,
                        "player_1_payoff": payoff,
                        "mechanically_unavoidable": unavoidable,
                    }
                },
            }
        )
    recorder.close()
    assert recorder.paused_policy_classes == {}
    assert not recorder.stop_requested()

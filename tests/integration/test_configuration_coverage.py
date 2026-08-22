from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from glee.actions import validate_action
from leaderboard.agent import LeaderboardAgent
from leaderboard.coverage import ConfigurationCoverage, configuration_coverage
from leaderboard.experimental_overrides import ExperimentalOverrideRegistry
from leaderboard.policy_router import PolicyRouter


def _messages(signature: str) -> bool:
    return "messages=true" in signature


def negotiation_game(row: ConfigurationCoverage) -> dict[str, Any]:
    signature = row.configuration_signature
    complete = "information=complete" in signature
    role = row.role
    me = "player_1" if role == "seller" else "player_2"
    state: dict[str, Any] = {
        "phase": "offer" if role == "seller" else "decision",
        "current_player": me,
        "player_1_role": "seller",
        "player_2_role": "buyer",
        "complete_information": complete,
        "horizon_known": "unknown/unlimited" not in signature,
        "messages_allowed": _messages(signature),
        "round": 1,
        "history": [],
        "last_offer": None if role == "seller" else {"price": 12, "from_player": "player_1", "round": 1},
    }
    if complete or role == "seller":
        state["player_1_value"] = 10.0
    if complete or role == "buyer":
        state["player_2_value"] = 20.0
    if state["horizon_known"]:
        if "T=1" in signature:
            state["max_rounds"] = 1
        elif "odd" in signature:
            state["max_rounds"] = 3
        else:
            state["max_rounds"] = 10
    fields: dict[str, Any]
    action_type: str
    if role == "seller":
        action_type = "offer"
        fields = {"product_price": "number"}
    else:
        action_type = "decision"
        fields = {
            "decision": {"values": ["AcceptOffer", "RejectOffer", "WalkAway"]}
        }
        if state.get("max_rounds") != 1:
            fields["product_price"] = "number"
    if _messages(signature):
        fields["message"] = "string"
    return {
        "game_id": "coverage-negotiation",
        "game_family": "negotiation",
        "your_player": me,
        "phase": state["phase"],
        "opponent": {"type": "hidden", "name": None},
        "game_state": state,
        "valid_actions": {"type": action_type, "fields": fields},
    }


def bargaining_game(row: ConfigurationCoverage) -> dict[str, Any]:
    signature = row.configuration_signature
    complete = "information=complete" in signature
    me = "player_1" if row.role == "alice" else "player_2"
    action_type = "offer" if row.role == "alice" else "decision"
    state: dict[str, Any] = {
        "phase": action_type,
        "current_player": me,
        "proposer": "player_1" if action_type == "decision" else me,
        "complete_information": complete,
        "horizon_known": "unknown/unlimited" not in signature,
        "messages_allowed": _messages(signature),
        "money_to_divide": 100.0,
        "round": 1,
        "history": [],
        "last_offer": None if action_type == "offer" else {
            "player_1_gain": 50.0,
            "player_2_gain": 50.0,
            "proposer": "player_1",
            "round": 1,
        },
    }
    if state["horizon_known"]:
        state["max_rounds"] = 4
    if complete or me == "player_1":
        state["delta_1"] = 0.9
    if complete or me == "player_2":
        state["delta_2"] = 0.8
    if action_type == "offer":
        fields: dict[str, Any] = {"alice_gain": "number", "bob_gain": "number"}
    else:
        fields = {"decision": {"values": ["accept", "reject", "walkaway"]}}
    if _messages(signature):
        fields["message"] = "string"
    return {
        "game_id": "coverage-bargaining",
        "game_family": "bargaining",
        "your_player": me,
        "phase": state["phase"],
        "opponent": {"type": "agent", "name": "fixture"},
        "game_state": state,
        "valid_actions": {"type": action_type, "fields": fields},
    }


def persuasion_game(row: ConfigurationCoverage) -> dict[str, Any]:
    signature = row.configuration_signature
    message_type = "text" if "message_type=text" in signature else "binary"
    seller_knows = "seller_knows_buyer_values=true" in signature
    seller = row.role == "seller"
    action_type = (
        "seller_message" if seller and message_type == "text"
        else "seller_recommendation" if seller
        else "buyer_decision"
    )
    state: dict[str, Any] = {
        "phase": "seller_message" if seller else "buyer_decision",
        "current_player": "player_1" if seller else "player_2",
        "p": 0.6,
        "product_price": 100.0,
        "seller_message_type": message_type,
        "round": 1,
        "total_rounds": 10,
        "history": [],
    }
    if seller:
        state["current_quality"] = "high"
    if not seller or seller_knows:
        state.update({"v": 200.0, "u": 0.0})
    fields = (
        {"message": "string"}
        if action_type == "seller_message"
        else {"decision": {"values": ["yes", "no"]}}
    )
    return {
        "game_id": "coverage-persuasion",
        "game_family": "persuasion",
        "your_player": "player_1" if seller else "player_2",
        "phase": state["phase"],
        "opponent": {"type": "human", "name": "fixture"},
        "game_state": state,
        "valid_actions": {"type": action_type, "fields": fields},
    }


def representative_game(row: ConfigurationCoverage) -> dict[str, Any]:
    return {
        "negotiation": negotiation_game,
        "bargaining": bargaining_game,
        "persuasion": persuasion_game,
    }[row.family](row)


ROWS = configuration_coverage()


def test_matrix_is_complete_and_has_no_deployment_blocker() -> None:
    assert len(ROWS) == 52
    assert {row.family for row in ROWS} == {"negotiation", "bargaining", "persuasion"}
    assert all(row.executable and row.tested_offline for row in ROWS)
    assert all(row.all_required_inputs_available for row in ROWS)
    assert all(row.deployment_status == "CLEAR" for row in ROWS)
    assert all(row.incomplete_classification == "RESEARCH_BLOCKED" for row in ROWS)


def test_committed_machine_readable_matrix_matches_runtime_declaration() -> None:
    payload = json.loads(Path("docs/configuration_coverage.json").read_text())
    assert payload["deployment_blockers"] == 0
    assert payload["rows"] == [row.structured() for row in ROWS]


@pytest.mark.parametrize("row", ROWS, ids=lambda row: f"{row.family}-{row.role}-{row.configuration_signature}")
def test_every_reachable_configuration_has_an_executable_named_incumbent(
    row: ConfigurationCoverage,
) -> None:
    game = representative_game(row)
    action, diagnostics = LeaderboardAgent().decide_with_diagnostics(game)
    assert diagnostics.routing.selected_policy == row.selected_incumbent
    assert diagnostics.routing.execution_fallback_reason is None
    assert diagnostics.routing.selected_policy != "SAFE_LEGAL_FALLBACK"
    assert validate_action(action, game) == action


@pytest.mark.parametrize("row", ROWS, ids=lambda row: f"pilot-{row.family}-{row.role}-{row.configuration_signature}")
def test_bounded_pilot_registry_keeps_every_reachable_configuration_legal(
    row: ConfigurationCoverage,
) -> None:
    game = representative_game(row)
    agent = LeaderboardAgent(
        PolicyRouter(
            experimental_overrides=ExperimentalOverrideRegistry.human_authorized_bounded_pilot()
        )
    )
    action, diagnostics = agent.decide_with_diagnostics(game)
    assert diagnostics.routing.execution_fallback_reason is None
    assert diagnostics.routing.selected_policy != "SAFE_LEGAL_FALLBACK"
    assert diagnostics.routing.authorization_status != "E_PROCESS_PROMOTED"
    assert validate_action(action, game) == action


def test_bargaining_complete_finite_bob_offer_uses_bob_proposer_sequence() -> None:
    row = next(
        row
        for row in ROWS
        if row.family == "bargaining"
        and row.role == "bob"
        and "information=complete" in row.configuration_signature
        and "horizon=finite" in row.configuration_signature
        and "messages=false" in row.configuration_signature
    )
    game = bargaining_game(row)
    game["game_state"].update({"phase": "offer", "current_player": "player_2", "round": 2})
    game["valid_actions"] = {
        "type": "offer",
        "fields": {"alice_gain": "number", "bob_gain": "number"},
    }
    action, routing = LeaderboardAgent().decide_with_routing(game)
    assert routing.execution_fallback_reason is None
    assert action["bob_gain"] > action["alice_gain"]


def test_persuasion_buyer_p0_uses_actual_price_and_low_value() -> None:
    row = next(row for row in ROWS if row.family == "persuasion" and row.role == "buyer")
    game = persuasion_game(row)
    game["game_state"].update({"p": 0.5, "v": 150, "u": 50, "product_price": 110})
    assert LeaderboardAgent().decide(game) == {"decision": "no"}

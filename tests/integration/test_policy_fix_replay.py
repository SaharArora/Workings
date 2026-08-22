from __future__ import annotations

import json
from pathlib import Path

from research.evaluation.replay_policy_fixes import replay


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")


def test_replay_marks_changed_adaptive_outcome_unknown(tmp_path: Path) -> None:
    state = {
        "current_player": "player_1",
        "player_1_role": "seller",
        "player_2_role": "buyer",
        "player_1_value": 150,
        "complete_information": False,
        "horizon_known": False,
        "round": 3,
        "history": [
            {
                "decision": "RejectOffer",
                "decided_by": "player_1",
                "offer": {"price": 50, "from_player": "player_2"},
                "counteroffer": 225,
            }
        ],
        "last_offer": {"price": 80, "from_player": "player_2"},
    }
    _write(
        tmp_path / "live_negotiation.jsonl",
        [
            {
                "event": "policy_decision",
                "game_id": "g",
                "routing": {"selected_policy": "NEGOTIATION_ADAPTIVE"},
                "action": {"decision": "RejectOffer", "product_price": 225},
                "state": state,
                "valid_actions": {
                    "type": "decision",
                    "fields": {"decision": "AcceptOffer/RejectOffer/WalkAway", "product_price": "number"},
                },
            },
            {"event": "game_result", "game_id": "g", "outcome": "walked_away"},
        ],
    )
    report = replay(tmp_path)["negotiation_adaptive"]
    assert report["adaptive_decisions_changed"] == 1
    game = report["games"][0]
    assert not game["counterfactual_outcome_known"]
    assert game["decisions"][0]["new_counter"] == 214.5


def test_replay_counts_persuasion_indifference_flip(tmp_path: Path) -> None:
    _write(
        tmp_path / "live_persuasion.jsonl",
        [
            {
                "event": "policy_decision",
                "game_id": "p",
                "action": {"decision": "yes"},
                "state": {"p": 0.5, "v": 200, "u": 0, "product_price": 100},
                "valid_actions": {"type": "buyer_decision"},
            }
        ],
    )
    report = replay(tmp_path)["persuasion_buyer_margin"]
    assert report["buyer_decisions_flipped"] == 1
    assert report["games"][0]["new_decision"] == "no"

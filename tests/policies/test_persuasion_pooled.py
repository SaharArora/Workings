from __future__ import annotations

import csv
import json
from pathlib import Path

from opponent_models.pooled_persuasion import (
    FEATURE_NAMES,
    PooledPersuasionModel,
    feature_vector,
    persuasion_feature_map,
)
from policies.persuasion.pooled_empirical import pooled_persuasion_plan
from research.training.persuasion.train_pooled_response import extract_game


def test_persuasion_features_exclude_quality_and_outcome() -> None:
    features = persuasion_feature_map(
        prior_high=0.5,
        high_value=200,
        low_value=0,
        product_price=100,
        round_number=2,
        total_rounds=20,
        seller_knows_values=False,
        opponent_category="llm",
        signal="yes",
        message=None,
        prior_buyer_decisions=("no",),
        prior_seller_signals=("yes",),
    )
    assert set(features) == set(FEATURE_NAMES)
    assert not ({"quality", "bought", "terminal_outcome", "p3_trust"} & set(features))
    assert features["expected_value_edge"] == 0


def test_extracts_public_persuasion_buyer_response(tmp_path: Path) -> None:
    config = {
        "game_type": "persuasion",
        "player_1_type": "litellm",
        "player_2_type": "otree",
        "player_1_args": {"model_name": "seller"},
        "player_2_args": {"model_name": "buyer"},
        "game_args": {
            "p": 0.5,
            "v": 2,
            "c": 0,
            "product_price": 100,
            "total_rounds": 20,
            "is_seller_know_cv": False,
            "seller_message_type": "binary",
        },
    }
    (tmp_path / "config.json").write_text(json.dumps(config))
    with (tmp_path / "game.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("round_quality", "product_worth", "player", "round", "decision"),
        )
        writer.writeheader()
        writer.writerows(
            [
                {"round_quality": "high-quality", "product_worth": 200, "player": "Nature", "round": 1},
                {"player": "Alice", "round": 1, "decision": "yes"},
                {"player": "Bob", "round": 1, "decision": "yes"},
            ]
        )
    rows = extract_game(tmp_path, source="human_vs_llm")
    assert len(rows) == 1
    assert rows[0]["bought"] == 1
    assert "quality" not in rows[0]["feature_map"]


def _artifact(path: Path) -> PooledPersuasionModel:
    width = len(FEATURE_NAMES)
    coefficients = [0.0] * width
    coefficients[FEATURE_NAMES.index("signal_yes")] = 2.0
    path.write_text(
        json.dumps(
            {
                "policy_name": "PERSUASION_POOLED_EMPIRICAL",
                "model_version": "test",
                "feature_names": list(FEATURE_NAMES),
                "response_model": {
                    "intercept": 0,
                    "coefficients": coefficients,
                    "means": [0] * width,
                    "scales": [1] * width,
                    "feature_min": [-10] * width,
                    "feature_max": [10] * width,
                },
                "calibration": {"intercept": 0, "coefficient": 1},
            }
        )
    )
    return PooledPersuasionModel.load(path)


def test_pooled_persuasion_is_distinct_seller_challenger(tmp_path: Path) -> None:
    model = _artifact(tmp_path / "artifact.json")
    game = {
        "game_family": "persuasion",
        "opponent": {"type": "agent"},
        "game_state": {
            "p": 0.5,
            "v": 200,
            "u": 0,
            "product_price": 100,
            "total_rounds": 20,
            "round": 1,
            "history": [],
        },
        "valid_actions": {"type": "seller_recommendation", "fields": {"decision": "yes/no"}},
    }
    plan = pooled_persuasion_plan(game, model)
    assert plan.action == {"decision": "yes"}
    assert plan.structured()["uses_p3_trust_artifact"] is False

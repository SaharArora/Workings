from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from opponent_models.pooled_negotiation import (
    FEATURE_NAMES,
    PooledNegotiationModel,
    economic_margin,
    feature_vector,
    pooled_feature_map,
)
from research.training.negotiation.build_pooled_dataset import extract_game_rows
from research.training.negotiation.train_pooled_response import train


def test_scale_equivalent_states_have_identical_features() -> None:
    first = pooled_feature_map(
        role="seller",
        own_value=100,
        proposal_price=150,
        complete_information=False,
        horizon_known=True,
        max_rounds=10,
        round_number=3,
        messages_allowed=True,
        opponent_category="llm",
        source_stratum="llm_vs_llm",
        prior_own_offers=(160,),
        prior_opponent_offers=(50, 70),
    )
    scaled = pooled_feature_map(
        role="seller",
        own_value=10_000,
        proposal_price=15_000,
        complete_information=False,
        horizon_known=True,
        max_rounds=10,
        round_number=3,
        messages_allowed=True,
        opponent_category="llm",
        source_stratum="llm_vs_llm",
        prior_own_offers=(16_000,),
        prior_opponent_offers=(5_000, 7_000),
    )
    assert feature_vector(first) == pytest.approx(feature_vector(scaled))


def test_history_features_use_only_pre_response_information() -> None:
    features = pooled_feature_map(
        role="buyer",
        own_value=1000,
        proposal_price=600,
        complete_information=False,
        horizon_known=False,
        max_rounds=None,
        round_number=5,
        messages_allowed=False,
        opponent_category="unknown",
        source_stratum="live",
        prior_own_offers=(500,),
        prior_opponent_offers=(1600, 1400),
    )
    assert features["proposal_margin"] == 0.4
    assert features["opponent_concession_from_first"] == 0.2
    assert features["own_concession"] == 0.1
    assert not ({"accepted", "terminal_outcome", "opponent_value"} & set(features))


def test_economic_margin_is_role_specific() -> None:
    assert economic_margin("seller", 150, 100) == 0.5
    assert economic_margin("buyer", 60, 100) == 0.4


def test_extracts_offer_response_pairs_from_original_schema(tmp_path: Path) -> None:
    config = {
        "game_type": "negotiation",
        "player_1_type": "litellm",
        "player_2_type": "otree",
        "player_1_args": {"public_name": "Alice", "model_name": "model-a"},
        "player_2_args": {"public_name": "Bob", "model_name": "otree"},
        "game_args": {
            "seller_value": 1.0,
            "buyer_value": 1.5,
            "product_price_order": 100,
            "max_rounds": 10,
            "messages_allowed": True,
            "complete_information": False,
        },
    }
    (tmp_path / "config.json").write_text(json.dumps(config))
    with (tmp_path / "game.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("message", "product_price", "player", "round", "decision"),
        )
        writer.writeheader()
        writer.writerows(
            [
                {"product_price": 140, "player": "Alice", "round": 1},
                {"player": "Bob", "round": 1, "decision": "RejectOffer"},
                {"product_price": 120, "player": "Bob", "round": 2},
                {"player": "Alice", "round": 2, "decision": "AcceptOffer"},
            ]
        )
    rows, counts = extract_game_rows(tmp_path, source_stratum="human_vs_llm")
    assert [row["accepted"] for row in rows] == [0, 1]
    assert [row["role"] for row in rows] == ["seller", "buyer"]
    assert rows[0]["opponent_category"] == "human"
    assert counts == {"reject_or_counter": 1, "accept": 1}


def test_training_freezes_loadable_separate_role_models(tmp_path: Path) -> None:
    source = tmp_path / "features.jsonl"
    rows = []
    for index in range(400):
        for role in ("seller", "buyer"):
            margin = (index % 20 - 10) / 10
            features = {name: 0.0 for name in FEATURE_NAMES}
            features["proposal_margin"] = margin
            rows.append(
                {
                    "game_id": f"g-{index}",
                    "decision_id": f"g-{index}-{role}",
                    "role": role,
                    "accepted": int(margin >= 0),
                    "features": list(feature_vector(features)),
                    "structural_group": f"{role}|incomplete|known|llm",
                    "opponent_model": "synthetic",
                    "robust_threshold_prediction_nonfeature": int(margin >= 0.5),
                }
            )
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    metadata = tmp_path / "metadata.json"
    metadata.write_text(
        json.dumps(
            {
                "feature_table_sha256": "synthetic",
                "walkaway_model_status": "UNAVAILABLE_NO_HISTORICAL_WALKAWAY_LABELS",
            }
        )
    )
    output = tmp_path / "artifact.json"
    artifact = train(source, metadata, output, version="test-v1")
    assert set(artifact["role_models"]) == {"seller", "buyer"}
    assert artifact["overall_test_metrics_vs_global"]["brier_skill_score"] > 0
    model = PooledNegotiationModel.load(output)
    low = {name: 0.0 for name in FEATURE_NAMES}
    high = dict(low)
    low["proposal_margin"] = -0.5
    high["proposal_margin"] = 0.5
    low_probability, _ = model.predict_acceptance(role="seller", features=low)
    high_probability, _ = model.predict_acceptance(role="seller", features=high)
    assert high_probability > low_probability

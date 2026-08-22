"""Non-live pooled persuasion seller challenger."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opponent_models.pooled_persuasion import (
    PooledPersuasionModel,
    persuasion_feature_map,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PersuasionCandidate:
    action: dict[str, str]
    predicted_purchase: float
    clipped_features: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PooledPersuasionPlan:
    action: dict[str, str]
    model_version: str
    candidates: tuple[PersuasionCandidate, ...]

    def structured(self) -> dict[str, Any]:
        return {
            "policy": "PERSUASION_POOLED_EMPIRICAL",
            "model_version": self.model_version,
            "candidates": [
                {
                    "action": candidate.action,
                    "predicted_purchase": candidate.predicted_purchase,
                    "clipped_features": list(candidate.clipped_features),
                }
                for candidate in self.candidates
            ],
            "chosen_action": self.action,
            "uses_p3_trust_artifact": False,
        }


def pooled_persuasion_plan(
    game: Mapping[str, Any], model: PooledPersuasionModel
) -> PooledPersuasionPlan:
    state = game["game_state"]
    required = ("p", "v", "u", "product_price", "total_rounds")
    if any(key not in state for key in required):
        raise ValueError("POOLED_PERSUASION_INPUT_UNAVAILABLE")
    action_type = str(game["valid_actions"]["type"])
    if action_type == "seller_recommendation":
        raw_candidates = (
            ({"decision": "yes"}, "yes", None),
            ({"decision": "no"}, "no", None),
        )
    elif action_type == "seller_message":
        raw_candidates = (
            ({"message": "I recommend buying this product."}, "text", "I recommend buying this product."),
            ({"message": "This product is available."}, "text", "This product is available."),
        )
    else:
        raise ValueError("pooled persuasion challenger is seller-side only")
    history = state.get("history", [])
    prior_buyer = [
        str(row.get("buyer_decision"))
        for row in history
        if isinstance(row, Mapping) and row.get("buyer_decision") in {"yes", "no"}
    ] if isinstance(history, Sequence) else []
    prior_seller = [
        str(row.get("seller_message"))
        for row in history
        if isinstance(row, Mapping) and row.get("seller_message") in {"yes", "no"}
    ] if isinstance(history, Sequence) else []
    opponent_type = str(game.get("opponent", {}).get("type", "unknown")).lower()
    opponent_category = "human" if opponent_type == "human" else "llm" if opponent_type == "agent" else "unknown"
    candidates: list[PersuasionCandidate] = []
    for action, signal, message in raw_candidates:
        features = persuasion_feature_map(
            prior_high=float(state["p"]),
            high_value=float(state["v"]),
            low_value=float(state["u"]),
            product_price=float(state["product_price"]),
            round_number=int(state.get("round", 1)),
            total_rounds=int(state["total_rounds"]),
            seller_knows_values=bool(state.get("is_seller_know_cv", False)),
            opponent_category=opponent_category,
            signal=signal,
            message=message,
            prior_buyer_decisions=prior_buyer,
            prior_seller_signals=prior_seller,
        )
        probability, clipped = model.predict_purchase(features)
        candidates.append(PersuasionCandidate(action, probability, clipped))
    chosen = max(candidates, key=lambda item: item.predicted_purchase)
    return PooledPersuasionPlan(dict(chosen.action), model.model_version, tuple(candidates))


class PooledPersuasionPolicy:
    def __init__(self, artifact: Path) -> None:
        self.model = PooledPersuasionModel.load(artifact)
        self.last_plan: PooledPersuasionPlan | None = None

    def __call__(self, game: dict[str, Any]) -> dict[str, Any]:
        self.last_plan = pooled_persuasion_plan(game, self.model)
        logger.info("persuasion_pooled_empirical %s", json.dumps(self.last_plan.structured(), sort_keys=True))
        return dict(self.last_plan.action)

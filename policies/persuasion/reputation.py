"""P3 honest-then-earned-trust seller challenger."""

from __future__ import annotations

import hashlib
import random
from collections.abc import Mapping, Sequence
from typing import Any

REPUTATION_CAP = 0.85
EARLY_FRACTION = 0.30
REPUTATION_BONUS = 0.05
POSITIVE_TEXT = "I recommend buying this product."
NEGATIVE_TEXT = "I do not recommend buying this product."


def recommend_buy(
    *, current_quality: str, round_number: int, total_rounds: int, prior_high: float,
    positive_recommendations: int, purchases_after_positive: int,
    population_positive_purchase_rate: float, rng: random.Random,
) -> bool:
    early_rounds = total_rounds * EARLY_FRACTION
    if round_number <= early_rounds:
        return current_quality == "high"
    trust = purchases_after_positive / positive_recommendations if positive_recommendations else 0.0
    bonus = REPUTATION_BONUS if trust > population_positive_purchase_rate else 0.0
    return rng.random() < min(REPUTATION_CAP, prior_high + bonus)


def _positive_recommendation(item: Mapping[str, Any]) -> bool:
    binary = item.get("seller_recommendation", item.get("recommendation"))
    if isinstance(binary, str):
        return binary.lower() == "yes"
    message = item.get("seller_message")
    return isinstance(message, str) and message == POSITIVE_TEXT


def reputation_action(
    game: Mapping[str, Any], *, population_positive_purchase_rate: float
) -> dict[str, str]:
    """Execute P3 only with a validated, pre-outcome population trust-rate input.

    A stable per-game/round seed makes retries of the same state idempotent while retaining
    P3's locked randomized late-round rule. The population statistic is never defaulted.
    """
    rate = float(population_positive_purchase_rate)
    if not 0 <= rate <= 1:
        raise ValueError("population_positive_purchase_rate must be in [0, 1]")
    state = game["game_state"]
    history = state.get("history", [])
    if not isinstance(history, Sequence):
        raise ValueError("persuasion history must be a sequence")
    positive = [item for item in history if isinstance(item, Mapping) and _positive_recommendation(item)]
    purchases = sum(bool(item.get("bought")) for item in positive)
    seed_material = (
        f"P3-v1|{game.get('game_id')}|{state.get('round')}|{len(history)}".encode("utf-8")
    )
    seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "big")
    recommend = recommend_buy(
        current_quality=str(state["current_quality"]).lower(),
        round_number=int(state["round"]),
        total_rounds=int(state["total_rounds"]),
        prior_high=float(state["p"]),
        positive_recommendations=len(positive),
        purchases_after_positive=purchases,
        population_positive_purchase_rate=rate,
        rng=random.Random(seed),
    )
    action_type = str(game["valid_actions"]["type"])
    if action_type == "seller_recommendation":
        return {"decision": "yes" if recommend else "no"}
    if action_type == "seller_message":
        return {"message": POSITIVE_TEXT if recommend else NEGATIVE_TEXT}
    raise ValueError(f"P3 does not support action type {action_type!r}")

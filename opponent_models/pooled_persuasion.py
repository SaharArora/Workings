"""Pre-purchase features and frozen pooled persuasion purchase model."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FEATURE_NAMES = (
    "prior_high",
    "expected_value_edge",
    "round_fraction",
    "seller_knows_values",
    "opponent_human",
    "opponent_llm",
    "signal_yes",
    "signal_no",
    "signal_text",
    "message_mentions_high",
    "message_mentions_low",
    "message_buy_language",
    "message_negation",
    "prior_buy_rate",
    "prior_positive_signal_rate",
    "previous_buyer_bought",
)


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1 + exp_value)


def persuasion_feature_map(
    *,
    prior_high: float,
    high_value: float,
    low_value: float,
    product_price: float,
    round_number: int,
    total_rounds: int,
    seller_knows_values: bool,
    opponent_category: str,
    signal: str | None,
    message: str | None,
    prior_buyer_decisions: Sequence[str] = (),
    prior_seller_signals: Sequence[str] = (),
) -> dict[str, float]:
    p = min(max(float(prior_high), 0.0), 1.0)
    high, low, price = float(high_value), float(low_value), float(product_price)
    if not all(math.isfinite(item) for item in (high, low, price)):
        raise ValueError("persuasion economic inputs must be finite")
    expected = p * high + (1 - p) * low
    scale = max(abs(high), abs(low), abs(price), 1.0)
    normalized_signal = str(signal or "text").strip().lower()
    text = str(message or "").lower()
    buyer = [str(value).lower() for value in prior_buyer_decisions]
    seller = [str(value).lower() for value in prior_seller_signals]
    category = opponent_category if opponent_category in {"human", "llm"} else "unknown"
    return {
        "prior_high": p,
        "expected_value_edge": (expected - price) / scale,
        "round_fraction": min(max(int(round_number), 1) / max(int(total_rounds), 1), 1.0),
        "seller_knows_values": float(bool(seller_knows_values)),
        "opponent_human": float(category == "human"),
        "opponent_llm": float(category == "llm"),
        "signal_yes": float(normalized_signal == "yes"),
        "signal_no": float(normalized_signal == "no"),
        "signal_text": float(normalized_signal not in {"yes", "no"}),
        "message_mentions_high": float("high" in text or "quality" in text),
        "message_mentions_low": float("low" in text),
        "message_buy_language": float(any(word in text for word in ("buy", "purchase", "recommend"))),
        "message_negation": float(any(word in text.split() for word in ("no", "not", "don't", "dont"))),
        "prior_buy_rate": sum(value == "yes" for value in buyer) / len(buyer) if buyer else 0.0,
        "prior_positive_signal_rate": sum(value == "yes" for value in seller) / len(seller) if seller else 0.0,
        "previous_buyer_bought": float(bool(buyer) and buyer[-1] == "yes"),
    }


def feature_vector(features: Mapping[str, float]) -> tuple[float, ...]:
    values = tuple(float(features[name]) for name in FEATURE_NAMES)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("persuasion features must be finite")
    return values


@dataclass(frozen=True, slots=True)
class PooledPersuasionModel:
    model_version: str
    intercept: float
    coefficients: tuple[float, ...]
    means: tuple[float, ...]
    scales: tuple[float, ...]
    feature_min: tuple[float, ...]
    feature_max: tuple[float, ...]
    calibration_intercept: float
    calibration_coefficient: float
    metadata: Mapping[str, Any]

    @classmethod
    def load(cls, path: Path) -> "PooledPersuasionModel":
        artifact = json.loads(path.read_text(encoding="utf-8"))
        if artifact.get("policy_name") != "PERSUASION_POOLED_EMPIRICAL":
            raise ValueError("not a pooled persuasion artifact")
        if tuple(artifact.get("feature_names", ())) != FEATURE_NAMES:
            raise ValueError("persuasion feature schema mismatch")
        response = artifact["response_model"]
        calibration = artifact["calibration"]
        model = cls(
            model_version=str(artifact["model_version"]),
            intercept=float(response["intercept"]),
            coefficients=tuple(float(value) for value in response["coefficients"]),
            means=tuple(float(value) for value in response["means"]),
            scales=tuple(float(value) for value in response["scales"]),
            feature_min=tuple(float(value) for value in response["feature_min"]),
            feature_max=tuple(float(value) for value in response["feature_max"]),
            calibration_intercept=float(calibration["intercept"]),
            calibration_coefficient=float(calibration["coefficient"]),
            metadata=artifact,
        )
        if len(model.coefficients) != len(FEATURE_NAMES):
            raise ValueError("persuasion model width mismatch")
        return model

    def predict_purchase(
        self, features: Mapping[str, float]
    ) -> tuple[float, tuple[str, ...]]:
        values = feature_vector(features)
        clipped: list[str] = []
        standardized: list[float] = []
        for index, value in enumerate(values):
            bounded = min(max(value, self.feature_min[index]), self.feature_max[index])
            if bounded != value:
                clipped.append(FEATURE_NAMES[index])
            standardized.append((bounded - self.means[index]) / self.scales[index])
        raw = self.intercept + sum(
            coefficient * value
            for coefficient, value in zip(self.coefficients, standardized, strict=True)
        )
        return (
            _sigmoid(self.calibration_intercept + self.calibration_coefficient * raw),
            tuple(clipped),
        )

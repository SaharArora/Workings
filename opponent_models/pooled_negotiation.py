"""Scale-normalized features and frozen pooled negotiation response models."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FEATURE_NAMES = (
    "complete_information",
    "horizon_known",
    "max_rounds_scaled",
    "round_scaled",
    "round_fraction",
    "messages_allowed",
    "opponent_human",
    "opponent_llm",
    "opponent_unknown",
    "source_human_vs_llm",
    "proposal_margin",
    "prior_offer_count_scaled",
    "last_opponent_margin",
    "best_opponent_margin",
    "opponent_concession_from_first",
    "opponent_concession_from_previous",
    "previous_own_margin",
    "own_concession",
    "repeated_counters_scaled",
)


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def _finite(value: Any) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def economic_margin(role: str, price: float, own_value: float) -> float:
    scale = max(abs(float(own_value)), 1.0)
    if role == "seller":
        return (float(price) - float(own_value)) / scale
    if role == "buyer":
        return (float(own_value) - float(price)) / scale
    raise ValueError(f"unknown negotiation role {role!r}")


def structural_group(
    *, role: str, complete_information: bool, horizon_known: bool, opponent_category: str
) -> str:
    information = "complete" if complete_information else "incomplete"
    horizon = "known" if horizon_known else "unknown"
    return f"{role}|{information}|{horizon}|{opponent_category}"


def pooled_feature_map(
    *,
    role: str,
    own_value: float,
    proposal_price: float,
    complete_information: bool,
    horizon_known: bool,
    max_rounds: int | None,
    round_number: int,
    messages_allowed: bool,
    opponent_category: str,
    source_stratum: str,
    prior_own_offers: Sequence[float] = (),
    prior_opponent_offers: Sequence[float] = (),
) -> dict[str, float]:
    """Build only features observable before the opponent's response."""
    if role not in {"seller", "buyer"}:
        raise ValueError(f"unknown negotiation role {role!r}")
    own = float(own_value)
    price = float(proposal_price)
    if not all(math.isfinite(value) for value in (own, price)):
        raise ValueError("own value and proposal price must be finite")
    rounds = int(max_rounds) if horizon_known and max_rounds else 0
    current_round = max(1, int(round_number))
    scale = max(abs(own), 1.0)
    opponent = [float(value) for value in prior_opponent_offers]
    ours = [float(value) for value in prior_own_offers]
    best_opponent = (
        (max(opponent) if role == "seller" else min(opponent))
        if opponent
        else None
    )
    last_opponent = opponent[-1] if opponent else None
    first_opponent = opponent[0] if opponent else None
    previous_opponent = opponent[-2] if len(opponent) >= 2 else None
    if first_opponent is None or best_opponent is None:
        concession_from_first = 0.0
    elif role == "seller":
        concession_from_first = max(0.0, best_opponent - first_opponent) / scale
    else:
        concession_from_first = max(0.0, first_opponent - best_opponent) / scale
    if previous_opponent is None or last_opponent is None:
        concession_from_previous = 0.0
    elif role == "seller":
        concession_from_previous = max(0.0, last_opponent - previous_opponent) / scale
    else:
        concession_from_previous = max(0.0, previous_opponent - last_opponent) / scale
    previous_own = ours[-1] if ours else None
    if previous_own is None:
        own_concession = 0.0
    elif role == "seller":
        own_concession = max(0.0, previous_own - price) / scale
    else:
        own_concession = max(0.0, price - previous_own) / scale
    repeated = 0
    for previous in reversed(ours):
        if math.isclose(previous, price, rel_tol=1e-9, abs_tol=1e-9):
            repeated += 1
        else:
            break
    category = opponent_category if opponent_category in {"human", "llm"} else "unknown"
    prior_count = len(ours) + len(opponent)
    return {
        "complete_information": float(bool(complete_information)),
        "horizon_known": float(bool(horizon_known)),
        "max_rounds_scaled": min(rounds, 100) / 100.0 if rounds else 0.0,
        "round_scaled": math.log1p(min(current_round, 100)) / math.log(101),
        "round_fraction": (
            min(current_round / rounds, 1.0) if rounds > 0 else 0.0
        ),
        "messages_allowed": float(bool(messages_allowed)),
        "opponent_human": float(category == "human"),
        "opponent_llm": float(category == "llm"),
        "opponent_unknown": float(category == "unknown"),
        "source_human_vs_llm": float(source_stratum == "human_vs_llm"),
        "proposal_margin": economic_margin(role, price, own),
        "prior_offer_count_scaled": math.log1p(min(prior_count, 100)) / math.log(101),
        "last_opponent_margin": (
            economic_margin(role, last_opponent, own)
            if last_opponent is not None
            else 0.0
        ),
        "best_opponent_margin": (
            economic_margin(role, best_opponent, own)
            if best_opponent is not None
            else 0.0
        ),
        "opponent_concession_from_first": concession_from_first,
        "opponent_concession_from_previous": concession_from_previous,
        "previous_own_margin": (
            economic_margin(role, previous_own, own)
            if previous_own is not None
            else 0.0
        ),
        "own_concession": own_concession,
        "repeated_counters_scaled": min(repeated, 10) / 10.0,
    }


def feature_vector(features: Mapping[str, float]) -> tuple[float, ...]:
    missing = [name for name in FEATURE_NAMES if name not in features]
    if missing:
        raise ValueError(f"missing pooled features: {missing}")
    values = tuple(float(features[name]) for name in FEATURE_NAMES)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("pooled features must be finite")
    return values


@dataclass(frozen=True, slots=True)
class FrozenLogisticModel:
    intercept: float
    coefficients: tuple[float, ...]
    means: tuple[float, ...]
    scales: tuple[float, ...]
    feature_min: tuple[float, ...]
    feature_max: tuple[float, ...]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FrozenLogisticModel":
        model = cls(
            intercept=float(value["intercept"]),
            coefficients=tuple(float(item) for item in value["coefficients"]),
            means=tuple(float(item) for item in value["means"]),
            scales=tuple(float(item) for item in value["scales"]),
            feature_min=tuple(float(item) for item in value["feature_min"]),
            feature_max=tuple(float(item) for item in value["feature_max"]),
        )
        widths = {
            len(model.coefficients), len(model.means), len(model.scales),
            len(model.feature_min), len(model.feature_max),
        }
        if widths != {len(FEATURE_NAMES)}:
            raise ValueError("pooled model feature width mismatch")
        return model

    def raw_logit(self, features: Mapping[str, float]) -> tuple[float, tuple[str, ...]]:
        vector = feature_vector(features)
        clipped: list[str] = []
        standardized: list[float] = []
        for index, value in enumerate(vector):
            bounded = min(max(value, self.feature_min[index]), self.feature_max[index])
            if bounded != value:
                clipped.append(FEATURE_NAMES[index])
            standardized.append((bounded - self.means[index]) / self.scales[index])
        logit = self.intercept + sum(
            coefficient * value
            for coefficient, value in zip(
                self.coefficients, standardized, strict=True
            )
        )
        return logit, tuple(clipped)


@dataclass(frozen=True, slots=True)
class PooledNegotiationModel:
    model_version: str
    role_models: Mapping[str, FrozenLogisticModel]
    calibration: Mapping[str, tuple[float, float]]
    artifact_metadata: Mapping[str, Any]

    @classmethod
    def load(cls, path: Path) -> "PooledNegotiationModel":
        artifact = json.loads(path.read_text(encoding="utf-8"))
        if artifact.get("policy_name") != "NEGOTIATION_POOLED_EMPIRICAL":
            raise ValueError("not a pooled negotiation artifact")
        if tuple(artifact.get("feature_names", ())) != FEATURE_NAMES:
            raise ValueError("pooled artifact feature schema mismatch")
        roles = {
            role: FrozenLogisticModel.from_dict(value["response_model"])
            for role, value in artifact["role_models"].items()
        }
        if set(roles) != {"seller", "buyer"}:
            raise ValueError("pooled artifact requires seller and buyer models")
        calibration = {
            role: (
                float(value.get("calibration", {}).get("intercept", 0.0)),
                float(value.get("calibration", {}).get("coefficient", 1.0)),
            )
            for role, value in artifact["role_models"].items()
        }
        return cls(
            model_version=str(artifact["model_version"]),
            role_models=roles,
            calibration=calibration,
            artifact_metadata=artifact,
        )

    def predict_acceptance(
        self, *, role: str, features: Mapping[str, float]
    ) -> tuple[float, tuple[str, ...]]:
        if role not in self.role_models:
            raise ValueError(f"pooled model has no role {role!r}")
        raw_logit, clipped = self.role_models[role].raw_logit(features)
        intercept, coefficient = self.calibration[role]
        return _sigmoid(intercept + coefficient * raw_logit), clipped

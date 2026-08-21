"""Frozen fitted binary response-likelihood models used by BAYES eligibility."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Iterable


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1 + exp_value)


@dataclass(frozen=True, slots=True)
class LogisticResponseModel:
    intercept: float
    coefficients: tuple[float, ...]

    def predict(self, features: tuple[float, ...]) -> float:
        return _sigmoid(self.intercept + sum(a * b for a, b in zip(self.coefficients, features, strict=True)))

    def to_dict(self) -> dict:
        return asdict(self)


def fit_logistic(
    rows: Iterable[tuple[tuple[float, ...], int]], *, iterations: int = 1000, learning_rate: float = 0.05
) -> LogisticResponseModel:
    data = list(rows)
    if not data:
        raise ValueError("training data is empty")
    width = len(data[0][0])
    intercept, coefficients = 0.0, [0.0] * width
    for _ in range(iterations):
        grad_i, grad = 0.0, [0.0] * width
        for features, target in data:
            prediction = _sigmoid(intercept + sum(a * b for a, b in zip(coefficients, features, strict=True)))
            error = prediction - target
            grad_i += error
            for index, value in enumerate(features):
                grad[index] += error * value
        scale = learning_rate / len(data)
        intercept -= scale * grad_i
        coefficients = [value - scale * gradient for value, gradient in zip(coefficients, grad, strict=True)]
    return LogisticResponseModel(intercept, tuple(coefficients))


def brier_skill_score(targets: list[int], predictions: list[float], baseline_rate: float) -> float:
    if len(targets) != len(predictions) or not targets:
        raise ValueError("targets and predictions must be nonempty and aligned")
    model_brier = sum((prediction - target) ** 2 for target, prediction in zip(targets, predictions, strict=True)) / len(targets)
    baseline_brier = sum((baseline_rate - target) ** 2 for target in targets) / len(targets)
    return 1 - model_brier / baseline_brier if baseline_brier else 0.0

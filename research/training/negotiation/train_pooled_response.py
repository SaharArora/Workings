"""Train, calibrate, and freeze the pooled negotiation acceptance challenger."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

from opponent_models.pooled_negotiation import FEATURE_NAMES


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def _split_name(game_id: str) -> str:
    bucket = int(hashlib.sha256(game_id.encode("utf-8")).hexdigest()[:8], 16) % 10
    if bucket < 6:
        return "train"
    if bucket < 8:
        return "validation"
    return "test"


def _load_rows(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _mean_scale(rows: Sequence[tuple[tuple[float, ...], int]]) -> tuple[list[float], list[float]]:
    width = len(rows[0][0])
    means = [0.0] * width
    for features, _ in rows:
        for index, value in enumerate(features):
            means[index] += value
    means = [value / len(rows) for value in means]
    variances = [0.0] * width
    for features, _ in rows:
        for index, value in enumerate(features):
            variances[index] += (value - means[index]) ** 2
    scales = [max(math.sqrt(value / len(rows)), 1e-8) for value in variances]
    return means, scales


def _standardize(
    rows: Sequence[tuple[tuple[float, ...], int]],
    means: Sequence[float],
    scales: Sequence[float],
) -> list[tuple[tuple[float, ...], int]]:
    return [
        (
            tuple(
                (value - mean) / scale
                for value, mean, scale in zip(features, means, scales, strict=True)
            ),
            target,
        )
        for features, target in rows
    ]


def fit_regularized_logistic(
    rows: Sequence[tuple[tuple[float, ...], int]],
    *,
    seed: int,
    epochs: int = 60,
    learning_rate: float = 0.08,
    l2: float = 0.02,
    batch_size: int = 512,
) -> dict[str, Any]:
    """Fit deterministic mini-batch L2 logistic regression without runtime deps."""
    if not rows:
        raise ValueError("training rows are empty")
    width = len(rows[0][0])
    if any(len(features) != width for features, _ in rows):
        raise ValueError("feature width mismatch")
    means, scales = _mean_scale(rows)
    standardized = _standardize(rows, means, scales)
    prevalence = min(max(sum(target for _, target in rows) / len(rows), 1e-6), 1 - 1e-6)
    intercept = math.log(prevalence / (1 - prevalence))
    coefficients = [0.0] * width
    order = list(range(len(rows)))
    rng = random.Random(seed)
    for epoch in range(epochs):
        rng.shuffle(order)
        rate = learning_rate / math.sqrt(1.0 + 0.08 * epoch)
        for start in range(0, len(order), batch_size):
            batch = order[start : start + batch_size]
            gradient_intercept = 0.0
            gradient = [0.0] * width
            for row_index in batch:
                features, target = standardized[row_index]
                prediction = _sigmoid(
                    intercept
                    + sum(
                        coefficient * value
                        for coefficient, value in zip(
                            coefficients, features, strict=True
                        )
                    )
                )
                error = prediction - target
                gradient_intercept += error
                for index, value in enumerate(features):
                    gradient[index] += error * value
            inverse = 1.0 / len(batch)
            intercept -= rate * gradient_intercept * inverse
            coefficients = [
                coefficient
                - rate * (gradient[index] * inverse + l2 * coefficient)
                for index, coefficient in enumerate(coefficients)
            ]
    columns = list(zip(*(features for features, _ in rows), strict=True))
    return {
        "intercept": intercept,
        "coefficients": coefficients,
        "means": means,
        "scales": scales,
        "feature_min": [min(column) for column in columns],
        "feature_max": [max(column) for column in columns],
        "regularization": {"type": "L2", "strength": l2},
        "optimizer": {
            "type": "deterministic_minibatch_gradient_descent",
            "epochs": epochs,
            "learning_rate": learning_rate,
            "batch_size": batch_size,
            "seed": seed,
        },
    }


def _raw_logit(model: dict[str, Any], features: Sequence[float]) -> float:
    standardized = [
        (min(max(value, low), high) - mean) / scale
        for value, mean, scale, low, high in zip(
            features,
            model["means"],
            model["scales"],
            model["feature_min"],
            model["feature_max"],
            strict=True,
        )
    ]
    return float(model["intercept"]) + sum(
        float(coefficient) * value
        for coefficient, value in zip(model["coefficients"], standardized, strict=True)
    )


def _fit_calibration(logits: list[float], targets: list[int], *, seed: int) -> dict[str, float]:
    rows = [((value,), target) for value, target in zip(logits, targets, strict=True)]
    fitted = fit_regularized_logistic(
        rows,
        seed=seed,
        epochs=80,
        learning_rate=0.05,
        l2=0.005,
        batch_size=256,
    )
    scale = fitted["scales"][0]
    coefficient = fitted["coefficients"][0] / scale
    intercept = fitted["intercept"] - coefficient * fitted["means"][0]
    calibrated = [_sigmoid(intercept + coefficient * value) for value in logits]
    identity = [_sigmoid(value) for value in logits]
    brier_calibrated = _brier(targets, calibrated)
    brier_identity = _brier(targets, identity)
    if brier_calibrated <= brier_identity:
        return {
            "intercept": intercept,
            "coefficient": coefficient,
            "validation_brier": brier_calibrated,
            "identity_validation_brier": brier_identity,
            "selected": True,
        }
    return {
        "intercept": 0.0,
        "coefficient": 1.0,
        "validation_brier": brier_identity,
        "identity_validation_brier": brier_identity,
        "selected": False,
    }


def _brier(targets: Sequence[int], predictions: Sequence[float]) -> float:
    return sum(
        (prediction - target) ** 2
        for target, prediction in zip(targets, predictions, strict=True)
    ) / len(targets)


def _log_loss(targets: Sequence[int], predictions: Sequence[float]) -> float:
    epsilon = 1e-15
    return -sum(
        target * math.log(min(max(prediction, epsilon), 1 - epsilon))
        + (1 - target) * math.log(min(max(1 - prediction, epsilon), 1 - epsilon))
        for target, prediction in zip(targets, predictions, strict=True)
    ) / len(targets)


def _metric_bundle(
    targets: list[int], predictions: list[float], baseline_predictions: list[float]
) -> dict[str, float]:
    brier = _brier(targets, predictions)
    baseline_brier = _brier(targets, baseline_predictions)
    return {
        "brier_score": brier,
        "brier_skill_score": 1.0 - brier / baseline_brier if baseline_brier else 0.0,
        "log_loss": _log_loss(targets, predictions),
        "acceptance_prevalence": sum(targets) / len(targets),
        "baseline_brier_score": baseline_brier,
        "baseline_log_loss": _log_loss(targets, baseline_predictions),
    }


def _calibration_diagnostic(
    targets: Sequence[int], predictions: Sequence[float]
) -> dict[str, Any]:
    bins: list[dict[str, Any]] = []
    absolute_error = 0.0
    for index in range(10):
        low, high = index / 10, (index + 1) / 10
        selected = [
            (target, prediction)
            for target, prediction in zip(targets, predictions, strict=True)
            if low <= prediction < high or (index == 9 and prediction == 1)
        ]
        if not selected:
            continue
        observed = sum(target for target, _ in selected) / len(selected)
        predicted = sum(prediction for _, prediction in selected) / len(selected)
        absolute_error += len(selected) * abs(observed - predicted)
        bins.append(
            {
                "lower": low,
                "upper": high,
                "n": len(selected),
                "mean_prediction": predicted,
                "observed_rate": observed,
            }
        )
    return {
        "bins": bins,
        "expected_calibration_error": absolute_error / len(targets),
        "max_bin_gap": max(
            (abs(row["mean_prediction"] - row["observed_rate"]) for row in bins),
            default=None,
        ),
    }


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(int(fraction * (len(ordered) - 1)), len(ordered) - 1)
    return ordered[index]


def train(source: Path, metadata_source: Path, output: Path, *, version: str) -> dict[str, Any]:
    rows = _load_rows(source)
    metadata = json.loads(metadata_source.read_text(encoding="utf-8"))
    if not rows:
        raise ValueError("pooled feature table is empty")
    by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_split[_split_name(str(row["game_id"]))].append(row)
    if any(not by_split[name] for name in ("train", "validation", "test")):
        raise ValueError("train/validation/test splits must all be nonempty")
    split_games = {
        name: {str(row["game_id"]) for row in split_rows}
        for name, split_rows in by_split.items()
    }
    if any(
        split_games[left] & split_games[right]
        for left, right in (("train", "validation"), ("train", "test"), ("validation", "test"))
    ):
        raise AssertionError("game leakage across splits")
    global_train_rate = sum(int(row["accepted"]) for row in by_split["train"]) / len(
        by_split["train"]
    )
    group_train: dict[str, list[int]] = defaultdict(list)
    for row in by_split["train"]:
        group_train[str(row["structural_group"])].append(int(row["accepted"]))
    group_rates = {
        group: (sum(values) + 2 * global_train_rate) / (len(values) + 2)
        for group, values in group_train.items()
    }
    role_models: dict[str, Any] = {}
    all_targets: list[int] = []
    all_predictions: list[float] = []
    all_global_baseline: list[float] = []
    all_group_baseline: list[float] = []
    all_robust_baseline: list[float] = []
    for role_index, role in enumerate(("seller", "buyer")):
        role_splits = {
            name: [row for row in split_rows if row["role"] == role]
            for name, split_rows in by_split.items()
        }
        if any(not role_splits[name] for name in ("train", "validation", "test")):
            raise ValueError(f"{role} split is empty")
        train_rows = [
            (tuple(float(value) for value in row["features"]), int(row["accepted"]))
            for row in role_splits["train"]
        ]
        model = fit_regularized_logistic(train_rows, seed=1729 + role_index)
        validation_logits = [
            _raw_logit(model, row["features"]) for row in role_splits["validation"]
        ]
        validation_targets = [int(row["accepted"]) for row in role_splits["validation"]]
        calibration = _fit_calibration(
            validation_logits, validation_targets, seed=2718 + role_index
        )
        test_logits = [_raw_logit(model, row["features"]) for row in role_splits["test"]]
        predictions = [
            _sigmoid(
                calibration["intercept"] + calibration["coefficient"] * value
            )
            for value in test_logits
        ]
        targets = [int(row["accepted"]) for row in role_splits["test"]]
        global_baseline = [global_train_rate] * len(targets)
        group_baseline = [
            group_rates.get(str(row["structural_group"]), global_train_rate)
            for row in role_splits["test"]
        ]
        robust_baseline = [
            float(row["robust_threshold_prediction_nonfeature"])
            for row in role_splits["test"]
        ]
        latencies: list[float] = []
        for row in role_splits["test"][:2000]:
            started = time.perf_counter()
            _sigmoid(
                calibration["intercept"]
                + calibration["coefficient"] * _raw_logit(model, row["features"])
            )
            latencies.append(time.perf_counter() - started)
        role_models[role] = {
            "response_model": model,
            "calibration": calibration,
            "split_counts": {
                name: {
                    "rows": len(role_splits[name]),
                    "games": len({row["game_id"] for row in role_splits[name]}),
                }
                for name in ("train", "validation", "test")
            },
            "test_metrics_vs_global": _metric_bundle(
                targets, predictions, global_baseline
            ),
            "test_metrics_vs_structural_group": _metric_bundle(
                targets, predictions, group_baseline
            ),
            "robust_threshold_diagnostic": {
                **_metric_bundle(targets, robust_baseline, global_baseline),
                "nondeployable_input_note": (
                    "uses the historical responder value and is not a model feature"
                ),
            },
            "calibration_diagnostic": _calibration_diagnostic(targets, predictions),
            "inference_latency_seconds": {
                "n": len(latencies),
                "median": statistics.median(latencies),
                "p95": _percentile(latencies, 0.95),
                "maximum": max(latencies),
            },
        }
        all_targets.extend(targets)
        all_predictions.extend(predictions)
        all_global_baseline.extend(global_baseline)
        all_group_baseline.extend(group_baseline)
        all_robust_baseline.extend(robust_baseline)
    opponent_models = {
        name: {str(row["opponent_model"]) for row in split_rows}
        for name, split_rows in by_split.items()
    }
    artifact = {
        "policy_name": "NEGOTIATION_POOLED_EMPIRICAL",
        "model_version": version,
        "model_class": "separate_role_L2_logistic_with_optional_Platt_calibration",
        "frozen": True,
        "feature_names": list(FEATURE_NAMES),
        "feature_table_sha256": metadata["feature_table_sha256"],
        "source_metadata": metadata,
        "split_method": "sha256(game_id) 60/20/20; every game remains in one split",
        "split_counts": {
            name: {
                "rows": len(split_rows),
                "games": len(split_games[name]),
            }
            for name, split_rows in by_split.items()
        },
        "structural_group_counts": dict(
            sorted(Counter(row["structural_group"] for row in rows).items())
        ),
        "global_train_accept_rate": global_train_rate,
        "role_models": role_models,
        "overall_test_metrics_vs_global": _metric_bundle(
            all_targets, all_predictions, all_global_baseline
        ),
        "overall_test_metrics_vs_structural_group": _metric_bundle(
            all_targets, all_predictions, all_group_baseline
        ),
        "overall_robust_threshold_diagnostic": _metric_bundle(
            all_targets, all_robust_baseline, all_global_baseline
        ),
        "overall_calibration_diagnostic": _calibration_diagnostic(
            all_targets, all_predictions
        ),
        "leakage_checks": {
            "game_id_disjoint": True,
            "post_outcome_features_present": False,
            "hidden_opponent_values_in_features": False,
            "terminal_outcomes_in_features": False,
            "opponent_model_identity_in_features": False,
            "opponent_model_identity_overlap": {
                "train_validation": len(opponent_models["train"] & opponent_models["validation"]),
                "train_test": len(opponent_models["train"] & opponent_models["test"]),
                "validation_test": len(opponent_models["validation"] & opponent_models["test"]),
            },
            "identity_overlap_note": (
                "Model identities recur in the dense cross-play graph. Separating identities "
                "would violate game-level integrity or collapse the connected graph into one "
                "split; identity is excluded from features and residual confounding is reported."
            ),
        },
        "walkaway_response_model": {
            "status": metadata["walkaway_model_status"],
            "reason": "The public historical corpus contains accept and RejectOffer labels only.",
        },
        "code_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("metadata_source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    train(args.source, args.metadata_source, args.output, version=args.version)


if __name__ == "__main__":
    main()

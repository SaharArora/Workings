"""Extract and train a pooled historical persuasion purchase model."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from opponent_models.pooled_persuasion import (
    FEATURE_NAMES,
    feature_vector,
    persuasion_feature_map,
)
from research.training.negotiation.train_pooled_response import (
    _calibration_diagnostic,
    _fit_calibration,
    _metric_bundle,
    _raw_logit,
    fit_regularized_logistic,
)


def _category(value: Any) -> str:
    normalized = str(value or "").lower()
    if normalized == "otree":
        return "human"
    if "llm" in normalized or normalized in {"litellm", "http"}:
        return "llm"
    return "unknown"


def _game_dirs(root: Path) -> Iterable[tuple[str, Path]]:
    for source in ("human_vs_llm", "llm_vs_llm"):
        for config in sorted((root / source / "persuasion").rglob("config.json")):
            if (config.parent / "game.csv").is_file():
                yield source, config.parent


def extract_game(directory: Path, *, source: str) -> list[dict[str, Any]]:
    config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
    args = config["game_args"]
    price = float(args["product_price"])
    high = float(args["v"]) * price
    low = float(args.get("c", args.get("u", 0.0))) * price
    total = int(args.get("total_rounds", 20))
    seller_type = config.get("player_1_type")
    prior_buyer: list[str] = []
    prior_seller: list[str] = []
    current_signal: str | None = None
    current_message: str | None = None
    output: list[dict[str, Any]] = []
    with (directory / "game.csv").open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    for index, row in enumerate(rows):
        player = str(row.get("player") or "").strip().lower()
        decision = str(row.get("decision") or "").strip().lower()
        message = str(row.get("message") or "").strip()
        if player == "alice":
            current_signal = decision if decision in {"yes", "no"} else "text"
            current_message = message or None
            continue
        if player not in {"bob", "the buyer"} or decision not in {"yes", "no"}:
            continue
        round_number = int(float(row.get("round") or 1))
        features = persuasion_feature_map(
            prior_high=float(args["p"]),
            high_value=high,
            low_value=low,
            product_price=price,
            round_number=round_number,
            total_rounds=total,
            seller_knows_values=bool(args.get("is_seller_know_cv", False)),
            opponent_category=_category(seller_type),
            signal=current_signal,
            message=current_message,
            prior_buyer_decisions=prior_buyer,
            prior_seller_signals=prior_seller,
        )
        output.append(
            {
                "game_id": directory.name,
                "decision_id": f"{directory.name}:{index}",
                "source": source,
                "bought": int(decision == "yes"),
                "features": list(feature_vector(features)),
                "feature_map": features,
                "seller_message_type": str(args.get("seller_message_type", "unknown")),
                "seller_model": str(config.get("player_1_args", {}).get("model_name", seller_type)),
                "buyer_model": str(config.get("player_2_args", {}).get("model_name", config.get("player_2_type"))),
            }
        )
        prior_buyer.append(decision)
        prior_seller.append(str(current_signal or "text"))
        current_signal = None
        current_message = None
    return output


def build_table(root: Path, output: Path, metadata_output: Path) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    counts: Counter[str] = Counter()
    games: set[str] = set()
    with output.open("w", encoding="utf-8") as handle:
        for source, directory in _game_dirs(root):
            for row in extract_game(directory, source=source):
                serialized = json.dumps(row, sort_keys=True, separators=(",", ":"))
                handle.write(serialized + "\n")
                digest.update(serialized.encode())
                games.add(row["game_id"])
                counts[f"source:{source}"] += 1
                counts[f"message_type:{row['seller_message_type']}"] += 1
                counts[f"bought:{row['bought']}"] += 1
    metadata = {
        "dataset_name": "persuasion_pooled_pre_purchase_v1",
        "source_commit": subprocess.run(
            ["git", "-C", str(root.parent), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "games": len(games),
        "rows": counts["bought:0"] + counts["bought:1"],
        "counts": dict(sorted(counts.items())),
        "feature_table_sha256": digest.hexdigest(),
        "p3_inputs_used": False,
        "quality_or_terminal_leakage_used": False,
    }
    metadata_output.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return metadata


def _split(game_id: str) -> str:
    bucket = int(hashlib.sha256(game_id.encode()).hexdigest()[:8], 16) % 10
    return "train" if bucket < 6 else "validation" if bucket < 8 else "test"


def _sigmoid(value: float) -> float:
    if value >= 0:
        exp_neg = math.exp(-value)
        return 1.0 / (1.0 + exp_neg)
    exp_pos = math.exp(value)
    return exp_pos / (1.0 + exp_pos)


def train(table: Path, metadata_path: Path, output: Path, *, version: str) -> dict[str, Any]:
    rows = [json.loads(line) for line in table.read_text().splitlines() if line.strip()]
    splits: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        splits[_split(str(row["game_id"]))].append(row)
    fitted = fit_regularized_logistic(
        [(tuple(row["features"]), int(row["bought"])) for row in splits["train"]],
        seed=4242,
        epochs=30,
        learning_rate=0.06,
        l2=0.02,
        batch_size=1024,
    )
    validation_logits = [_raw_logit(fitted, row["features"]) for row in splits["validation"]]
    validation_targets = [int(row["bought"]) for row in splits["validation"]]
    calibration = _fit_calibration(validation_logits, validation_targets, seed=4343)
    test_logits = [_raw_logit(fitted, row["features"]) for row in splits["test"]]
    predictions = [
        _sigmoid(calibration["intercept"] + calibration["coefficient"] * value)
        for value in test_logits
    ]
    targets = [int(row["bought"]) for row in splits["test"]]
    baseline_rate = sum(int(row["bought"]) for row in splits["train"]) / len(splits["train"])
    artifact = {
        "policy_name": "PERSUASION_POOLED_EMPIRICAL",
        "model_version": version,
        "model_class": "L2_logistic_with_optional_Platt_calibration",
        "feature_names": list(FEATURE_NAMES),
        "response_model": fitted,
        "calibration": calibration,
        "split_method": "sha256(game_id) 60/20/20",
        "split_counts": {
            name: {"rows": len(value), "games": len({row['game_id'] for row in value})}
            for name, value in splits.items()
        },
        "test_metrics": _metric_bundle(targets, predictions, [baseline_rate] * len(targets)),
        "calibration_diagnostic": _calibration_diagnostic(targets, predictions),
        "source_metadata": json.loads(metadata_path.read_text()),
        "leakage_checks": {
            "game_id_disjoint": True,
            "nature_quality_in_features": False,
            "terminal_outcome_in_features": False,
            "p3_trust_artifact_used": False,
            "model_identity_in_features": False,
        },
        "frozen": True,
        "code_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("table", type=Path)
    parser.add_argument("metadata", type=Path)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    build_table(args.source_root, args.table, args.metadata)
    train(args.table, args.metadata, args.artifact, version=args.version)


if __name__ == "__main__":
    main()

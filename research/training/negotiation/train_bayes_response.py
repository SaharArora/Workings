"""Fit, Platt-calibrate, and test a BAYES rejection likelihood artifact.

Input JSONL rows require `game_id`, `features` (numeric list), and `rejected` (0/1).
The caller supplies the already-filtered exact cell/opponent-category snapshot.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from opponent_models.response import brier_skill_score, fit_logistic
from research.training.negotiation.common import (
    code_commit, deterministic_split, file_hash, load_rows, write_artifact,
)


def train(source: Path, output: Path, *, cell: str, opponent_category: str, version: str, prior: dict) -> dict:
    rows = load_rows(source)
    train_rows, validation_rows, test_rows = deterministic_split(rows)
    if not train_rows or not validation_rows or not test_rows:
        raise ValueError("train/validation/test splits must all be nonempty")
    base = fit_logistic((tuple(row["features"]), int(row["rejected"])) for row in train_rows)
    calibration = fit_logistic(
        (((base.predict(tuple(row["features"])),), int(row["rejected"]))) for row in validation_rows
    )
    predictions = [calibration.predict((base.predict(tuple(row["features"])),)) for row in test_rows]
    targets = [int(row["rejected"]) for row in test_rows]
    baseline_rate = sum(int(row["rejected"]) for row in train_rows) / len(train_rows)
    bss = brier_skill_score(targets, predictions, baseline_rate)
    artifact = {
        "model_version": version, "cell": cell, "opponent_category": opponent_category,
        "training_data_hash": file_hash(source), "n_games": len({row["game_id"] for row in rows}),
        "prior": prior, "response_model": base.to_dict(), "calibration_transform": calibration.to_dict(),
        "calibration_method": "Platt", "brier_skill_score": bss,
        "code_commit": code_commit(), "frozen": True,
    }
    write_artifact(output, artifact)
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path); parser.add_argument("output", type=Path)
    parser.add_argument("--cell", required=True); parser.add_argument("--opponent-category", required=True)
    parser.add_argument("--version", required=True); parser.add_argument("--prior", required=True)
    args = parser.parse_args()
    import json
    train(args.source, args.output, cell=args.cell, opponent_category=args.opponent_category,
          version=args.version, prior=json.loads(args.prior))


if __name__ == "__main__":
    main()

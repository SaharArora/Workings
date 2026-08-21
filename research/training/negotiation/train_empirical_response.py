"""Fit and freeze an empirical opponent-response model with support metadata."""

from __future__ import annotations

import argparse
from pathlib import Path

from opponent_models.response import fit_logistic
from research.training.negotiation.common import code_commit, file_hash, load_rows, write_artifact


def train(source: Path, output: Path, *, cell: str, opponent_category: str, version: str) -> dict:
    rows = load_rows(source)
    if not rows:
        raise ValueError("training data is empty")
    model = fit_logistic((tuple(row["features"]), int(row["accepted"])) for row in rows)
    prices = [float(row["price"]) for row in rows]
    artifact = {
        "model_version": version, "cell": cell, "opponent_category": opponent_category,
        "training_data_hash": file_hash(source), "n_games": len({row["game_id"] for row in rows}),
        "response_model": model.to_dict(), "ood_threshold": {"price_min": min(prices), "price_max": max(prices)},
        "feature_preprocessing": "caller-supplied normalized numeric features",
        "code_commit": code_commit(), "frozen": True,
    }
    write_artifact(output, artifact)
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path); parser.add_argument("output", type=Path)
    parser.add_argument("--cell", required=True); parser.add_argument("--opponent-category", required=True)
    parser.add_argument("--version", required=True); args = parser.parse_args()
    train(args.source, args.output, cell=args.cell, opponent_category=args.opponent_category, version=args.version)


if __name__ == "__main__":
    main()

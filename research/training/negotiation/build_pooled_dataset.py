"""Build a pooled pre-response negotiation feature table from public GLEE data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from opponent_models.pooled_negotiation import (
    feature_vector,
    pooled_feature_map,
    structural_group,
)

ACCEPT_DECISIONS = {"acceptoffer", "buyfromjhon", "selltojhon"}
REJECT_DECISIONS = {"rejectoffer"}


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _player_index(config: dict[str, Any], player: str) -> int | None:
    normalized = player.strip().lower()
    for index in (1, 2):
        args = config.get(f"player_{index}_args", {})
        names = {
            str(args.get("public_name", "")).strip().lower(),
            "alice" if index == 1 else "bob",
            f"player_{index}",
        }
        if normalized in names:
            return index
    return None


def _opponent_category(config: dict[str, Any], proposer_index: int) -> str:
    value = str(config.get(f"player_{3 - proposer_index}_type", "")).lower()
    if value == "otree":
        return "human"
    if "llm" in value or value in {"litellm", "http"}:
        return "llm"
    return "unknown"


def _model_name(config: dict[str, Any], player_index: int) -> str:
    args = config.get(f"player_{player_index}_args", {})
    return str(args.get("model_name") or config.get(f"player_{player_index}_type") or "unknown")


def _iter_game_dirs(root: Path) -> Iterable[tuple[str, Path]]:
    for source in ("human_vs_llm", "llm_vs_llm"):
        family_root = root / source / "negotiation"
        for config_path in sorted(family_root.rglob("config.json")):
            csv_path = config_path.parent / "game.csv"
            if csv_path.is_file():
                yield source, config_path.parent


def _horizon(max_rounds: Any) -> tuple[bool, int | None]:
    rounds = int(max_rounds) if isinstance(max_rounds, (int, float)) else None
    return (False, None) if rounds in {None, 99} else (True, rounds)


def extract_game_rows(
    directory: Path, *, source_stratum: str
) -> tuple[list[dict[str, Any]], Counter[str]]:
    config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
    args = config["game_args"]
    order = float(args.get("product_price_order", 1.0))
    seller_value = float(args["seller_value"]) * order
    buyer_value = float(args["buyer_value"]) * order
    horizon_known, max_rounds = _horizon(args.get("max_rounds"))
    history: dict[str, list[float]] = {"seller": [], "buyer": []}
    pending: dict[str, Any] | None = None
    output: list[dict[str, Any]] = []
    responses: Counter[str] = Counter()
    with (directory / "game.csv").open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    for row_index, row in enumerate(rows):
        price = _number(row.get("product_price"))
        player = str(row.get("player") or "")
        player_index = _player_index(config, player)
        if price is not None and player_index is not None:
            role = "seller" if player_index == 1 else "buyer"
            opponent_role = "buyer" if role == "seller" else "seller"
            own_value = seller_value if role == "seller" else buyer_value
            round_number = int(_number(row.get("round")) or 1)
            opponent_category = _opponent_category(config, player_index)
            features = pooled_feature_map(
                role=role,
                own_value=own_value,
                proposal_price=price,
                complete_information=bool(args["complete_information"]),
                horizon_known=horizon_known,
                max_rounds=max_rounds,
                round_number=round_number,
                messages_allowed=bool(args.get("messages_allowed", False)),
                opponent_category=opponent_category,
                source_stratum=source_stratum,
                prior_own_offers=history[role],
                prior_opponent_offers=history[opponent_role],
            )
            responder_value = buyer_value if role == "seller" else seller_value
            robust_threshold = (
                price <= 0.5 * responder_value
                if role == "seller"
                else price >= 1.5 * responder_value
            )
            pending = {
                "game_id": directory.name,
                "decision_id": f"{directory.name}:{row_index}",
                "source_stratum": source_stratum,
                "role": role,
                "opponent_category": opponent_category,
                "proposer_model": _model_name(config, player_index),
                "opponent_model": _model_name(config, 3 - player_index),
                "complete_information": bool(args["complete_information"]),
                "horizon_known": horizon_known,
                "max_rounds": max_rounds,
                "round_number": round_number,
                "messages_allowed": bool(args.get("messages_allowed", False)),
                "structural_group": structural_group(
                    role=role,
                    complete_information=bool(args["complete_information"]),
                    horizon_known=horizon_known,
                    opponent_category=opponent_category,
                ),
                "price": price,
                "own_value": own_value,
                "scale": max(abs(own_value), 1.0),
                "features": list(feature_vector(features)),
                "feature_map": features,
                "robust_threshold_prediction_nonfeature": int(robust_threshold),
            }
            history[role].append(price)
        decision = str(row.get("decision") or "").strip()
        if not decision or pending is None:
            continue
        normalized = decision.lower()
        if normalized in ACCEPT_DECISIONS:
            accepted = 1
            response_class = "accept"
        elif normalized in REJECT_DECISIONS:
            accepted = 0
            response_class = "reject_or_counter"
        else:
            responses[f"unsupported:{decision}"] += 1
            pending = None
            continue
        pending["accepted"] = accepted
        pending["response_class"] = response_class
        output.append(pending)
        responses[response_class] += 1
        pending = None
    return output, responses


def build_feature_table(root: Path, output: Path, metadata_output: Path) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    counts: Counter[str] = Counter()
    structural: Counter[str] = Counter()
    game_ids: set[str] = set()
    with output.open("w", encoding="utf-8") as handle:
        for source, directory in _iter_game_dirs(root):
            rows, response_counts = extract_game_rows(
                directory, source_stratum=source
            )
            counts.update(response_counts)
            if rows:
                game_ids.add(directory.name)
            for row in rows:
                serialized = json.dumps(row, sort_keys=True, separators=(",", ":"))
                handle.write(serialized + "\n")
                digest.update(serialized.encode("utf-8"))
                structural[row["structural_group"]] += 1
                counts[f"role:{row['role']}"] += 1
                counts[f"source:{row['source_stratum']}"] += 1
    metadata = {
        "dataset_name": "negotiation_pooled_pre_response_v1",
        "source": "public_original_GLEE_Data",
        "games": len(game_ids),
        "rows": sum(structural.values()),
        "feature_table_sha256": digest.hexdigest(),
        "counts": dict(sorted(counts.items())),
        "structural_group_counts": dict(sorted(structural.items())),
        "walkaway_model_status": (
            "UNAVAILABLE_NO_HISTORICAL_WALKAWAY_LABELS"
            if counts["walk_away"] == 0
            else "AVAILABLE"
        ),
        "feature_leakage_guard": (
            "feature_map contains only pre-response observables; responder values are "
            "used only for the explicitly named nonfeature ROBUST diagnostic"
        ),
    }
    metadata_output.parent.mkdir(parents=True, exist_ok=True)
    metadata_output.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("metadata_output", type=Path)
    args = parser.parse_args()
    build_feature_table(args.source_root, args.output, args.metadata_output)


if __name__ == "__main__":
    main()

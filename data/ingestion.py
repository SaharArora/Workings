"""Incremental ingestion for historical per-game GLEE directories."""

from __future__ import annotations

import csv
import hashlib
import json
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

BAYES_MIN_HISTORICAL_GAMES = 200


@dataclass(frozen=True, slots=True)
class HistoricalGame:
    game_id: str
    source_stratum: str
    family: str
    cell: str
    config: dict[str, Any]
    turns: list[dict[str, str]]


@dataclass(frozen=True, slots=True)
class IngestionProfile:
    source: str
    files: int
    bytes: int
    games: int
    parse_seconds: float
    cell_counts: dict[str, int]
    eligible_cells: tuple[str, ...]


def negotiation_cell(game_args: dict[str, Any]) -> str:
    """Create an exact, stable configuration-cell identifier."""
    horizon = game_args.get("max_rounds")
    fields = {
        "complete_information": bool(game_args["complete_information"]),
        "horizon": "unlimited" if horizon is None else int(horizon),
        "messages_allowed": bool(game_args["messages_allowed"]),
        "seller_value": float(game_args["seller_value"]),
        "buyer_value": float(game_args["buyer_value"]),
        "product_price_order": int(game_args["product_price_order"]),
    }
    return "negotiation:" + ":".join(f"{key}={fields[key]}" for key in sorted(fields))


def iter_game_directories(root: Path) -> Iterable[Path]:
    for config_path in sorted(root.rglob("config.json")):
        if (config_path.parent / "game.csv").is_file():
            yield config_path.parent


def parse_negotiation_game(directory: Path, source_stratum: str) -> HistoricalGame:
    config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
    if config.get("game_type") != "negotiation":
        raise ValueError(f"Expected negotiation config at {directory}")
    with (directory / "game.csv").open(newline="", encoding="utf-8-sig") as handle:
        turns = list(csv.DictReader(handle))
    return HistoricalGame(
        game_id=directory.name,
        source_stratum=source_stratum,
        family="negotiation",
        cell=negotiation_cell(config["game_args"]),
        config=config,
        turns=turns,
    )


def profile_and_ingest(
    root: Path,
    *,
    source_stratum: str,
    output_jsonl: Path | None = None,
) -> tuple[list[HistoricalGame], IngestionProfile]:
    start = time.perf_counter()
    files = [path for path in root.rglob("*") if path.is_file()]
    games = [parse_negotiation_game(path, source_stratum) for path in iter_game_directories(root)]
    counts = Counter(game.cell for game in games)
    if output_jsonl is not None:
        output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with output_jsonl.open("w", encoding="utf-8") as handle:
            for game in games:
                handle.write(json.dumps(asdict(game), sort_keys=True) + "\n")
    profile = IngestionProfile(
        source=str(root),
        files=len(files),
        bytes=sum(path.stat().st_size for path in files),
        games=len(games),
        parse_seconds=time.perf_counter() - start,
        cell_counts=dict(sorted(counts.items())),
        eligible_cells=tuple(sorted(cell for cell, count in counts.items() if count >= BAYES_MIN_HISTORICAL_GAMES)),
    )
    return games, profile


def snapshot_hash(games: Iterable[HistoricalGame]) -> str:
    digest = hashlib.sha256()
    for game in sorted(games, key=lambda item: item.game_id):
        digest.update(json.dumps(asdict(game), sort_keys=True).encode())
    return digest.hexdigest()

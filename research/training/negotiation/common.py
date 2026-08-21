"""Deterministic split and artifact helpers for frozen negotiation models."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def deterministic_split(rows: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    ordered = sorted(rows, key=lambda row: hashlib.sha256(str(row["game_id"]).encode()).hexdigest())
    train_end = int(0.6 * len(ordered))
    validation_end = int(0.8 * len(ordered))
    return ordered[:train_end], ordered[train_end:validation_end], ordered[validation_end:]


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def write_artifact(path: Path, artifact: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

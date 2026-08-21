#!/usr/bin/env python3
"""Incrementally ingest and profile one historical GLEE negotiation subtree."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from data.ingestion import profile_and_ingest, snapshot_hash


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--stratum", required=True, choices=("human_vs_llm", "llm_vs_llm"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    games, profile = profile_and_ingest(
        args.source, source_stratum=args.stratum, output_jsonl=args.output
    )
    result = asdict(profile)
    result["snapshot_hash"] = snapshot_hash(games)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run one bounded randomized research experiment through the live family queue."""

from __future__ import annotations

import argparse
from pathlib import Path

from eprocess.experiment import Experiment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment_id"); parser.add_argument("cell")
    parser.add_argument("opponent_category", choices=("human", "agent", "hidden"))
    parser.add_argument("incumbent"); parser.add_argument("candidate")
    parser.add_argument("--seed", type=int, required=True); parser.add_argument("--M", type=int, required=True)
    parser.add_argument("--concurrency", type=int, default=1); parser.add_argument("--family", required=True)
    parser.add_argument("--log-dir", type=Path, default=Path("experiments")); args = parser.parse_args()
    experiment = Experiment(args.experiment_id, args.cell, args.opponent_category,
        args.incumbent, args.candidate, args.seed, args.M, args.log_dir / f"{args.experiment_id}.jsonl",
        args.concurrency, (args.family,))
    print(f"Configured {experiment.experiment_id}; alpha_test={experiment.alpha_test}; threshold={experiment.threshold}")
    print("Live execution requires GLEE_API_KEY and cell-matched arrivals; no game was queued by this setup command.")


if __name__ == "__main__":
    main()

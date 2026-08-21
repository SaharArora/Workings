#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import fmean


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("log", type=Path); args = parser.parse_args()
    rows = [json.loads(line) for line in args.log.read_text().splitlines() if line.strip()]
    by_arm = {arm: [row["Y_t"] for row in rows if row["assigned_arm"] == arm] for arm in ("incumbent", "candidate")}
    result = {arm: {"n": len(values), "mean": fmean(values) if values else None} for arm, values in by_arm.items()}
    result["E_t_final"] = rows[-1]["E_t"] if rows else 1.0
    result["E_t_prime_final"] = rows[-1]["E_t_prime"] if rows else 1.0
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

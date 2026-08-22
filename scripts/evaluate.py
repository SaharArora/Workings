#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.evaluation.metrics import payoff_report


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("log", type=Path); args = parser.parse_args()
    rows = [json.loads(line) for line in args.log.read_text().splitlines() if line.strip()]
    result = payoff_report(rows)
    result["E_t_final"] = rows[-1]["E_t"] if rows else 1.0
    result["E_t_prime_final"] = rows[-1]["E_t_prime"] if rows else 1.0
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

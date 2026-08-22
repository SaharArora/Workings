#!/usr/bin/env python3
"""Write the reproducible MVL policy-latency benchmark artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.evaluation.latency import (
    COMPETITION_TURN_LIMIT_SECONDS,
    POLICY_MAX_BUDGET_SECONDS,
    POLICY_P95_BUDGET_SECONDS,
    benchmark_policy_paths,
)
from research.evaluation.representative_states import representative_policy_games


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1_000)
    parser.add_argument("--json", type=Path, default=Path("docs/latency_benchmark.json"))
    parser.add_argument("--markdown", type=Path, default=Path("docs/latency_benchmark.md"))
    args = parser.parse_args()
    results = benchmark_policy_paths(representative_policy_games(), iterations=args.iterations)
    payload = {
        "competition_turn_limit_seconds": COMPETITION_TURN_LIMIT_SECONDS,
        "policy_p95_budget_seconds": POLICY_P95_BUDGET_SECONDS,
        "policy_max_budget_seconds": POLICY_MAX_BUDGET_SECONDS,
        "network_latency_included": False,
        "results": [result.structured() for result in results],
    }
    args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Production policy latency benchmark",
        "",
        f"Authoritative turn limit: **{COMPETITION_TURN_LIMIT_SECONDS:.0f}s**. Internal budgets: "
        f"p95 <= **{POLICY_P95_BUDGET_SECONDS:.0f}s**, maximum <= **{POLICY_MAX_BUDGET_SECONDS:.0f}s**. "
        "Measurements include envelope parsing, routing and policy computation, communication "
        "rendering, and local action validation. Network/API time is excluded.",
        "",
        "| Path | Family | Selected policy | n | Median (ms) | p95 (ms) | Max (ms) | Budget |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for result in results:
        lines.append(
            f"| `{result.path}` | {result.family} | `{result.selected_policy}` | "
            f"{result.iterations} | {result.median_seconds * 1_000:.4f} | "
            f"{result.p95_seconds * 1_000:.4f} | {result.max_seconds * 1_000:.4f} | "
            f"{'PASS' if result.within_budget else 'DEPLOYMENT_BLOCKER'} |"
        )
    args.markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not all(result.within_budget for result in results):
        raise SystemExit("one or more policy paths exceeded the production latency budget")


if __name__ == "__main__":
    main()

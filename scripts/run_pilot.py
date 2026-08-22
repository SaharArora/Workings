#!/usr/bin/env python3
"""Run one explicitly bounded frozen-policy MVL family pilot."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from glee.client import CompetitionClient
from glee.pilot import result_json, run_pilot
from leaderboard.agent import LeaderboardAgent
from leaderboard.config import DEFAULT_GAME_FAMILIES
from leaderboard.experimental_overrides import ExperimentalOverrideRegistry
from leaderboard.policy_router import PolicyRouter


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", choices=DEFAULT_GAME_FAMILIES, required=True)
    parser.add_argument("--max-games", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    parser.add_argument("--poll-interval", type=float, default=4.0)
    parser.add_argument("--safety-timeout", type=float, default=3_600.0)
    parser.add_argument(
        "--human-authorized-experimental",
        action="store_true",
        help="Enable only the process-scoped bounded-pilot challenger registry",
    )
    args = parser.parse_args()
    current = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    if current != args.frozen_commit:
        parser.error(f"HEAD {current} does not match frozen commit {args.frozen_commit}")
    registry = (
        ExperimentalOverrideRegistry.human_authorized_bounded_pilot()
        if args.human_authorized_experimental
        else ExperimentalOverrideRegistry()
    )
    agent = LeaderboardAgent(PolicyRouter(experimental_overrides=registry))
    result = run_pilot(
        CompetitionClient(),
        family=args.family,
        max_games=args.max_games,
        output_path=args.output,
        frozen_commit=args.frozen_commit,
        poll_interval=args.poll_interval,
        safety_timeout=args.safety_timeout,
        agent=agent,
    )
    print(result_json(result), flush=True)


if __name__ == "__main__":
    main()

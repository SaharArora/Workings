#!/usr/bin/env python3
"""Run exactly one family of the frozen, human-authorized leaderboard tranche."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from glee.client import CompetitionClient
from glee.pilot import result_json, run_pilot
from leaderboard.agent import LeaderboardAgent
from leaderboard.experimental_overrides import ExperimentalOverrideRegistry
from leaderboard.policy_router import PolicyRouter

TRANCHE_GAME_LIMITS = {
    "bargaining": 20,
    "negotiation": 20,
    "persuasion": 12,
}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", choices=tuple(TRANCHE_GAME_LIMITS), required=True)
    parser.add_argument("--frozen-commit", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--poll-interval", type=float, default=4.0)
    parser.add_argument("--safety-timeout", type=float, default=14_400.0)
    args = parser.parse_args()

    current = _git("rev-parse", "HEAD")
    if current != args.frozen_commit:
        parser.error(f"HEAD {current} does not match frozen commit {args.frozen_commit}")
    if _git("diff", "--name-only") or _git("diff", "--cached", "--name-only"):
        parser.error("tracked files changed after the tranche commit was frozen")

    output = args.output or Path(
        f"research/evaluation/leaderboard_tranche_{args.family}.jsonl"
    )
    registry = ExperimentalOverrideRegistry.human_authorized_tranche(
        adaptive_diagnostic_limit=6
    )
    agent = LeaderboardAgent(PolicyRouter(experimental_overrides=registry))
    result = run_pilot(
        CompetitionClient(),
        family=args.family,
        max_games=TRANCHE_GAME_LIMITS[args.family],
        output_path=output,
        frozen_commit=args.frozen_commit,
        poll_interval=args.poll_interval,
        safety_timeout=args.safety_timeout,
        agent=agent,
    )
    print(result_json(result), flush=True)


if __name__ == "__main__":
    main()

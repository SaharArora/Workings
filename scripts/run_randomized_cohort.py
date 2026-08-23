#!/usr/bin/env python3
"""Run one executor of the frozen post-risk-fix randomized live cohort."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from eprocess.cohort import COHORT_ID
from eprocess.store import CohortStore
from glee.client import CompetitionClient
from glee.cohort_runtime import run_cohort_family
from leaderboard.agent import LeaderboardAgent
from leaderboard.cohort_overrides import CohortOverrideRegistry
from leaderboard.policy_router import PolicyArtifact, PolicyRouter
from policies.persuasion.pooled_empirical import PooledPersuasionPolicy

FAMILIES = ("bargaining", "negotiation", "persuasion")
DEFAULT_STORE = Path("research/evaluation/cohorts") / COHORT_ID / "evidence.sqlite3"
PERSUASION_ARTIFACT = Path("research/artifacts/persuasion_pooled_empirical_v1.json")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", choices=FAMILIES, required=True)
    parser.add_argument("--frozen-commit", required=True)
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--poll-interval", type=float, default=12.0)
    parser.add_argument("--safety-timeout", type=float, default=172_800.0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    current = _git("rev-parse", "HEAD")
    if current != args.frozen_commit:
        parser.error(f"HEAD {current} does not match frozen commit {args.frozen_commit}")
    if _git("diff", "--name-only") or _git("diff", "--cached", "--name-only"):
        parser.error("tracked files changed after the cohort commit was frozen")

    # Loading is part of preflight even for non-persuasion executors, so every process
    # verifies the same frozen artifact before any of the three queues is joined.
    pooled_persuasion = PooledPersuasionPolicy(PERSUASION_ARTIFACT)
    artifact = PolicyArtifact.from_policy(
        "persuasion-pooled-empirical-v1", pooled_persuasion
    )
    store = CohortStore(args.store, frozen_commit=args.frozen_commit)
    store.initialize()
    registry = CohortOverrideRegistry(store)
    agent = LeaderboardAgent(
        PolicyRouter(
            experimental_overrides=registry,
            pooled_persuasion_artifact=artifact,
        )
    )
    output = args.output or (
        Path("research/evaluation/cohorts")
        / COHORT_ID
        / f"{args.family}.jsonl"
    )
    result = run_cohort_family(
        CompetitionClient(),
        family=args.family,
        output_path=output,
        store=store,
        frozen_commit=args.frozen_commit,
        agent=agent,
        poll_interval=args.poll_interval,
        safety_timeout=args.safety_timeout,
        resume=args.resume,
    )
    print(json.dumps(asdict(result), sort_keys=True, default=str), flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run persistent leaderboard service or an authoritatively supervised bounded run."""

from __future__ import annotations

import argparse

from glee.client import CompetitionClient
from leaderboard.agent import LeaderboardAgent
from leaderboard.config import DEFAULT_CONCURRENCY, DEFAULT_GAME_FAMILIES, DEFAULT_POLL_INTERVAL


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", choices=DEFAULT_GAME_FAMILIES, action="append")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL)
    parser.add_argument("--max-games", type=int)
    parser.add_argument("--no-requeue", action="store_true")
    parser.add_argument("--safety-timeout", type=float, default=600.0)
    args = parser.parse_args()

    client = CompetitionClient()
    agent = LeaderboardAgent()
    families = args.family or list(DEFAULT_GAME_FAMILIES)
    if args.max_games is not None:
        if len(families) != 1:
            parser.error("bounded runs require exactly one --family")
        result = client.run_bounded(
            agent.decide,
            game_family=families[0],
            max_games=args.max_games,
            concurrency=args.concurrency,
            requeue=not args.no_requeue,
            poll_interval=args.poll_interval,
            safety_timeout=args.safety_timeout,
        )
        print(result)
        return
    client.run(
        agent.decide,
        game_families=families,
        concurrency=args.concurrency,
        poll_interval=args.poll_interval,
    )


if __name__ == "__main__":
    main()

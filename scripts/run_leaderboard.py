#!/usr/bin/env python3
from glee.client import CompetitionClient
from leaderboard.agent import LeaderboardAgent
from leaderboard.config import DEFAULT_CONCURRENCY, DEFAULT_GAME_FAMILIES, DEFAULT_POLL_INTERVAL


def main() -> None:
    client = CompetitionClient()
    client.run(LeaderboardAgent().decide, game_families=DEFAULT_GAME_FAMILIES,
               concurrency=DEFAULT_CONCURRENCY, poll_interval=DEFAULT_POLL_INTERVAL)


if __name__ == "__main__":
    main()

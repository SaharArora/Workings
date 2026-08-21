"""Production agent: economic routing first, communication rendering second."""

from __future__ import annotations

from typing import Any

from communication.strategic import render
from leaderboard.policy_router import PolicyRouter


class LeaderboardAgent:
    def __init__(self, router: PolicyRouter | None = None) -> None:
        self.router = router or PolicyRouter()

    def decide(self, game: dict[str, Any]) -> dict[str, Any]:
        economic_action = self.router.decide(game)
        return render(economic_action, game)

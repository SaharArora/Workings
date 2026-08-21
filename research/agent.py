"""IBO and EG-SPM research variants with identical neutral communication."""

from __future__ import annotations

from typing import Any

from communication.neutral import neutral_message
from leaderboard.policy_router import PolicyRouter


def _neutralize(action: dict[str, Any], game: dict[str, Any]) -> dict[str, Any]:
    result = dict(action)
    if "message" in game.get("valid_actions", {}).get("fields", {}):
        result["message"] = neutral_message()
    return result


class IBOAgent:
    def __init__(self) -> None:
        self.router = PolicyRouter()

    def decide(self, game: dict[str, Any]) -> dict[str, Any]:
        return _neutralize(self.router.decide(game), game)


class EGSPMAgent:
    def __init__(self, router: PolicyRouter) -> None:
        self.router = router

    def decide(self, game: dict[str, Any]) -> dict[str, Any]:
        return _neutralize(self.router.decide(game), game)

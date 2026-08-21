from __future__ import annotations

from typing import Any

import pytest

from glee.client import CompetitionClient
from glee.schemas import GameFamily, OpponentCategory


class FakeSDK:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def queue(self, family: str) -> dict:
        self.calls.append(("queue", family))
        return {"status": "queued"}

    def leave_queue(self, family: str | None = None) -> dict:
        self.calls.append(("leave", family))
        return {}

    def pending_games(self) -> list[dict]:
        return [{
            "game_id": "g1", "game_family": "negotiation", "your_player": "player_2",
            "phase": "decision", "opponent": {"type": "hidden", "name": None},
            "game_state": {}, "valid_actions": {"type": "decision", "fields": {}},
            "prompt": "choose",
        }]

    def move(self, game_id: str, action: dict) -> dict:
        self.calls.append(("move", (game_id, action)))
        return {"valid": True}

    def game_state(self, game_id: str) -> dict:
        return {"game_id": game_id}

    def stats(self) -> dict:
        return {"rating": 1000}

    def run(self, strategy: Any, **kwargs: Any) -> None:
        self.calls.append(("run", kwargs))


def test_adapter_normalizes_and_delegates() -> None:
    sdk = FakeSDK()
    client = CompetitionClient(sdk_client=sdk)
    assert client.queue(GameFamily.NEGOTIATION) == {"status": "queued"}
    game = client.pending_games()[0]
    assert game.opponent_category is OpponentCategory.HIDDEN
    assert client.submit(game.game_id, {"decision": "WalkAway"}) == {"valid": True}
    assert client.stats() == {"rating": 1000}


def test_missing_key_fails_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GLEE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GLEE_API_KEY"):
        CompetitionClient()

"""Thin adapter around the verified official :mod:`glee_sdk` transport."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Mapping
from typing import Any, Protocol

from glee_sdk import GleeClient

from glee.retry import never_raise
from glee.schemas import GameFamily, PendingGame

API_KEY_ENV = "GLEE_API_KEY"
DEFAULT_BASE_URL = "https://glee-competition.com"


class SDKClient(Protocol):
    def queue(self, game_family: str) -> dict: ...
    def leave_queue(self, family: str | None = None) -> dict: ...
    def pending_games(self) -> list[dict]: ...
    def move(self, game_id: str, action: dict) -> dict: ...
    def game_state(self, game_id: str) -> dict: ...
    def stats(self) -> dict: ...
    def run(self, strategy: Callable[[dict], dict], **kwargs: Any) -> None: ...


class CompetitionClient:
    """Normalize SDK payloads while leaving queue/retry/rate limits to the SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        sdk_client: SDKClient | None = None,
    ) -> None:
        if sdk_client is not None:
            self._client = sdk_client
            return
        resolved = api_key or os.environ.get(API_KEY_ENV)
        if not resolved:
            raise ValueError(f"Set {API_KEY_ENV} or pass api_key")
        self._client = GleeClient(api_key=resolved, base_url=base_url)

    def queue(self, family: GameFamily | str) -> dict:
        return self._client.queue(GameFamily(family).value)

    def leave_queue(self, family: GameFamily | str | None = None) -> dict:
        value = GameFamily(family).value if family is not None else None
        return self._client.leave_queue(value)

    def pending_games(self) -> list[PendingGame]:
        return [PendingGame.from_sdk(item) for item in self._client.pending_games()]

    def submit(self, game_id: str, action: Mapping[str, Any]) -> dict:
        return self._client.move(game_id, dict(action))

    def game_state(self, game_id: str) -> dict:
        return self._client.game_state(game_id)

    def stats(self) -> dict:
        return self._client.stats()

    def run(
        self,
        strategy: Callable[[dict[str, Any]], Mapping[str, Any]],
        *,
        game_families: Iterable[GameFamily | str] | None = None,
        concurrency: int = 1,
        poll_interval: float = 2.0,
        max_games: int | None = None,
        max_time: float | None = None,
    ) -> None:
        families = None
        if game_families is not None:
            families = [GameFamily(family).value for family in game_families]
        self._client.run(
            never_raise(strategy),
            game_families=families,
            concurrency=concurrency,
            poll_interval=poll_interval,
            max_games=max_games,
            max_time=max_time,
        )

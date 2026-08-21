"""Typed internal views of live GLEE payloads.

The server-provided ``valid_actions`` object remains authoritative. These models validate
only stable envelope fields and deliberately retain mechanism-specific dictionaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping


class GameFamily(StrEnum):
    BARGAINING = "bargaining"
    NEGOTIATION = "negotiation"
    PERSUASION = "persuasion"


class OpponentCategory(StrEnum):
    HUMAN = "human"
    AGENT = "agent"
    HIDDEN = "hidden"


@dataclass(frozen=True, slots=True)
class PendingGame:
    game_id: str
    game_family: GameFamily
    your_player: str
    phase: str
    opponent_category: OpponentCategory
    opponent_name: str | None
    game_state: Mapping[str, Any]
    valid_actions: Mapping[str, Any]
    prompt: str

    @classmethod
    def from_sdk(cls, payload: Mapping[str, Any]) -> "PendingGame":
        opponent = payload.get("opponent") or {"type": "hidden", "name": None}
        return cls(
            game_id=str(payload["game_id"]),
            game_family=GameFamily(payload["game_family"]),
            your_player=str(payload["your_player"]),
            phase=str(payload["phase"]),
            opponent_category=OpponentCategory(opponent["type"]),
            opponent_name=opponent.get("name"),
            game_state=payload["game_state"],
            valid_actions=payload["valid_actions"],
            prompt=str(payload.get("prompt", "")),
        )

    def to_strategy_payload(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "game_family": self.game_family.value,
            "your_player": self.your_player,
            "phase": self.phase,
            "opponent": {
                "type": self.opponent_category.value,
                "name": self.opponent_name,
            },
            "game_state": dict(self.game_state),
            "valid_actions": dict(self.valid_actions),
            "prompt": self.prompt,
        }

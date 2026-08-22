from __future__ import annotations

import pytest

from leaderboard.policy_router import persuasion_p0_action
from policies.persuasion.babbling import (
    PERSUASION_BUY_MARGIN,
    production_buyer_buys,
)
from theory.persuasion.baselines import babbling_buyer_buys


@pytest.mark.parametrize(
    ("expected_value", "price", "expected"),
    (
        (100, 100, False),
        (101, 100, False),
        (102, 100, True),
        (103, 100, True),
    ),
)
def test_locked_production_margin(
    expected_value: float, price: float, expected: bool
) -> None:
    assert PERSUASION_BUY_MARGIN == 0.02
    assert production_buyer_buys(expected_value, price) is expected


def test_zero_price_is_bought_only_for_nonnegative_expected_value() -> None:
    assert production_buyer_buys(0, 0)
    assert production_buyer_buys(1, 0)
    assert not production_buyer_buys(-1, 0)


def test_theory_weak_inequality_remains_unchanged() -> None:
    assert babbling_buyer_buys(0.5, 2.0)


def test_live_p0_buyer_path_uses_production_margin() -> None:
    game = {
        "game_family": "persuasion",
        "game_state": {"p": 0.5, "v": 200, "u": 0, "product_price": 100},
        "valid_actions": {"type": "buyer_decision", "fields": {"decision": "yes/no"}},
    }
    assert persuasion_p0_action(game) == {"decision": "no"}
    game["game_state"]["v"] = 204
    assert persuasion_p0_action(game) == {"decision": "yes"}

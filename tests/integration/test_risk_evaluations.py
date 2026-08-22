from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from research.evaluation.evaluate_negotiation_risk_selector import (
    _selector_holdout_game,
)
from research.evaluation.evaluate_persuasion_margin_tail import (
    _parse_game,
    _tail_mean,
)


def test_selector_holdout_is_whole_game_and_excludes_consumed_test_split() -> None:
    game_id = "same-game"
    assert _selector_holdout_game(game_id) is _selector_holdout_game(game_id)
    # Find a previously consumed response-test game deterministically.
    from research.evaluation.backtest_population_layer import _split_name

    test_game = next(
        f"candidate-{index}"
        for index in range(100)
        if _split_name(f"candidate-{index}") == "test"
    )
    assert not _selector_holdout_game(test_game)


def test_fractional_lower_tail_mean() -> None:
    assert _tail_mean([-10, 0, 10, 20], alpha=0.75) == -10
    assert _tail_mean([-10, 0, 10, 20], alpha=0.50) == -5


def test_persuasion_exact_indifference_replay_uses_realized_quality(
    tmp_path: Path,
) -> None:
    config = {
        "game_args": {
            "p": 0.5,
            "v": 2.0,
            "c": 0.0,
            "product_price": 100,
            "seller_message_type": "binary",
        }
    }
    (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")
    with (tmp_path / "game.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "round_quality",
                "product_worth",
                "player",
                "round",
                "message",
                "decision",
            ),
        )
        writer.writeheader()
        writer.writerows(
            [
                {"product_worth": 0, "player": "Nature", "round": 1},
                {"player": "Alice", "round": 1, "decision": "yes"},
                {"player": "Bob", "round": 1, "decision": "yes"},
            ]
        )
    game = _parse_game("synthetic", tmp_path)
    assert game["theory_buy"] is True
    assert game["production_buy"] is False
    assert game["theory_payoff"] == -100
    assert game["production_payoff"] == 0

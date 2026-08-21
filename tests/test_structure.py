from __future__ import annotations

import importlib


def test_top_level_packages_are_importable() -> None:
    for package in (
        "communication",
        "eprocess",
        "glee",
        "leaderboard",
        "opponent_models",
        "policies",
        "research",
        "theory",
    ):
        assert importlib.import_module(package) is not None

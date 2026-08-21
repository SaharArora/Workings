from __future__ import annotations

import random
from statistics import mean

from eprocess.betting import BETTING_FRACTIONS, BettingProcess


def test_known_trajectory() -> None:
    process = BettingProcess()
    expected = []
    components = {value: 1.0 for value in BETTING_FRACTIONS}
    for x in (0.5, -0.25, 1.0):
        for value in BETTING_FRACTIONS:
            components[value] *= 1 + value * x
        expected.append(sum(components.values()) / 4)
        assert process.update(x) == expected[-1]


def test_synthetic_null_validity() -> None:
    rng = random.Random(9173)
    finals: list[float] = []
    crossings = 0
    replications, steps, alpha = 3000, 40, 0.05
    for _ in range(replications):
        process = BettingProcess()
        crossed = False
        for _ in range(steps):
            z = 1 if rng.random() < 0.5 else -1
            # Equal Bernoulli(0.5) potential-outcome distributions under both arms.
            observed = 1.0 if rng.random() < 0.5 else 0.0
            crossed |= process.update(z * observed) >= 1 / alpha
        finals.append(process.value)
        crossings += crossed
    assert abs(mean(finals) - 1.0) < 0.08
    assert crossings / replications <= alpha

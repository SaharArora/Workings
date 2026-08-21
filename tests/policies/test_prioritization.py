import pytest

from research.analysis.prioritization import bootstrap_effect, priority


def test_priority_locked_formula() -> None:
    result = priority(0.1, 0.1, 0.5)
    assert result.score == pytest.approx(0.5 * 0.1 * result.probability_better * (1 - result.probability_better))


def test_bootstrap_resamples_games() -> None:
    games = [1.0, 2.0, 3.0, 4.0]
    estimate, standard_error = bootstrap_effect(games, lambda sample: sum(sample) / len(sample), seed=3, replications=100)
    assert estimate == 2.5
    assert standard_error > 0

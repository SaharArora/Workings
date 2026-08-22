from pathlib import Path

import pytest

from eprocess.experiment import Experiment
from research.evaluation.metrics import payoff_report


def test_persistence_and_replay(tmp_path: Path) -> None:
    experiment = Experiment(
        "e1", "cell", "hidden", "A", "B", 42, 1,
        tmp_path / "e1.jsonl", 2, ("negotiation",),
    )
    arm = experiment.assign()
    record = experiment.observe_negotiation(arm, raw_payoff=50, own_value=100)
    assert record["X_t"] in (-0.625, 0.625)
    assert record["raw_payoff"] == 50
    assert record["Y_t"] == 0.625
    assert record["payoff_transform"]["clipping_occurred"] is False
    assert experiment.log_path.with_suffix(".assignments.jsonl").exists()
    original = experiment.main.value
    expected_next_arm = experiment.assign()
    experiment.main.update(1)
    restored = Experiment(
        "e1", "cell", "hidden", "A", "B", 42, 1,
        tmp_path / "e1.jsonl", 2, ("negotiation",),
    )
    restored.replay()
    assert restored.main.value == original
    assert restored._pending == [expected_next_arm]
    assert restored.outcome(window_closed=True) == "INCONCLUSIVE"


def test_negotiation_experiment_requires_transform_and_clips_extremes(tmp_path: Path) -> None:
    positive = Experiment(
        "positive", "cell", "hidden", "A", "B", 1, 1,
        tmp_path / "positive.jsonl", 1, ("negotiation",),
    )
    arm = positive.assign()
    with pytest.raises(ValueError, match="observe_negotiation"):
        positive.observe(arm, 1.0, 1e100)
    record = positive.observe_negotiation(arm, raw_payoff=1e100, own_value=10)
    assert record["Y_t"] == 1
    assert record["raw_payoff"] == 1e100
    assert record["payoff_transform"]["clipping_occurred"] is True

    negative = Experiment(
        "negative", "cell", "hidden", "A", "B", 2, 1,
        tmp_path / "negative.jsonl", 1, ("negotiation",),
    )
    arm = negative.assign()
    record = negative.observe_negotiation(arm, raw_payoff=-1e100, own_value=10)
    assert record["Y_t"] == 0
    assert record["payoff_transform"]["clipping_occurred"] is True


def test_offline_payoff_report_keeps_raw_and_transformed_metrics() -> None:
    report = payoff_report([
        {
            "assigned_arm": "incumbent", "raw_payoff": 1000, "Y_t": 1,
            "payoff_transform": {"clipping_occurred": True},
        },
        {
            "assigned_arm": "candidate", "raw_payoff": 1, "Y_t": 0.55,
            "payoff_transform": {"clipping_occurred": False},
        },
    ])
    assert report["incumbent"]["mean_raw_payoff"] == 1000
    assert report["incumbent"]["mean_bounded_payoff_Y"] == 1
    assert report["incumbent"]["clipping_observations"] == 1
    assert report["candidate_minus_incumbent"]["raw_payoff"] == -999
    assert report["candidate_minus_incumbent"]["bounded_payoff_Y"] == pytest.approx(-0.45)

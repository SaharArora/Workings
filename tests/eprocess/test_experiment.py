from pathlib import Path

from eprocess.experiment import Experiment


def test_persistence_and_replay(tmp_path: Path) -> None:
    experiment = Experiment(
        "e1", "cell", "hidden", "A", "B", 42, 1,
        tmp_path / "e1.jsonl", 2, ("negotiation",),
    )
    arm = experiment.assign()
    record = experiment.observe(arm, 0.5, 50)
    assert record["X_t"] in (-0.5, 0.5)
    assert experiment.log_path.with_suffix(".assignments.jsonl").exists()
    original = experiment.main.value
    experiment.main.update(1)
    experiment.replay()
    assert experiment.main.value == original
    assert experiment.outcome(window_closed=True) == "INCONCLUSIVE"

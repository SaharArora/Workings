"""Auditable randomized experiment wrapper around the pure betting primitive."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from eprocess.betting import BettingProcess

ALPHA_FAMILY = 0.05
DELTA_MIN = 0.01
ASSIGNMENT_PROBABILITY = 0.5


@dataclass(slots=True)
class Experiment:
    experiment_id: str
    cell: str
    opponent_category: str
    incumbent: str
    candidate: str
    seed: int
    challenger_count: int
    log_path: Path
    concurrency: int
    game_family_queue: tuple[str, ...]
    main: BettingProcess = field(default_factory=BettingProcess)
    mirror: BettingProcess = field(default_factory=BettingProcess)
    candidate_sum: float = 0.0
    incumbent_sum: float = 0.0
    candidate_n: int = 0
    incumbent_n: int = 0
    _rng: random.Random = field(init=False, repr=False)
    _pending: list[str] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.challenger_count < 1 or self.concurrency < 1:
            raise ValueError("challenger_count and concurrency must be positive")
        self._rng = random.Random(self.seed)

    @property
    def alpha_test(self) -> float:
        return ALPHA_FAMILY / self.challenger_count

    @property
    def threshold(self) -> float:
        return 1 / self.alpha_test

    @property
    def effect_estimate(self) -> float:
        if not self.candidate_n or not self.incumbent_n:
            return 0.0
        return self.candidate_sum / self.candidate_n - self.incumbent_sum / self.incumbent_n

    def assign(self) -> str:
        arm = "candidate" if self._rng.random() < ASSIGNMENT_PROBABILITY else "incumbent"
        self._pending.append(arm)
        assignment_log = self.log_path.with_suffix(".assignments.jsonl")
        assignment_log.parent.mkdir(parents=True, exist_ok=True)
        with assignment_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "experiment_id": self.experiment_id,
                "cell": self.cell,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "assigned_arm": arm,
                "assignment_probability": ASSIGNMENT_PROBABILITY,
            }, sort_keys=True) + "\n")
        return arm

    def observe(self, arm: str, normalized_payoff: float, raw_payoff: float) -> dict:
        if not self._pending or self._pending.pop(0) != arm:
            raise ValueError("outcome must match a pre-committed assignment in order")
        if not 0 <= normalized_payoff <= 1:
            raise ValueError("normalized payoff must lie in [0, 1]")
        z = 1 if arm == "candidate" else -1
        x = z * normalized_payoff
        main_value = self.main.update(x)
        mirror_value = self.mirror.update(-x)
        if arm == "candidate":
            self.candidate_sum += normalized_payoff
            self.candidate_n += 1
        else:
            self.incumbent_sum += normalized_payoff
            self.incumbent_n += 1
        record = {
            "experiment_id": self.experiment_id, "cell": self.cell,
            "opponent_category": self.opponent_category, "incumbent": self.incumbent,
            "candidate": self.candidate, "experiment_seed": self.seed,
            "timestamp": datetime.now(timezone.utc).isoformat(), "assigned_arm": arm,
            "assignment_probability": ASSIGNMENT_PROBABILITY, "raw_payoff": raw_payoff,
            "Y_t": normalized_payoff, "X_t": x, "X_t_prime": -x,
            "E_components": self.main.copy_components(),
            "E_prime_components": self.mirror.copy_components(),
            "E_t": main_value, "E_t_prime": mirror_value,
            "concurrency": self.concurrency, "game_family_queue": self.game_family_queue,
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record

    def outcome(self, window_closed: bool = False) -> str | None:
        if self.main.value >= self.threshold and self.effect_estimate > DELTA_MIN:
            return "PROMOTE"
        if self.mirror.value >= self.threshold:
            return "RETAIN"
        return "INCONCLUSIVE" if window_closed else None

    def replay(self) -> None:
        """Reconstruct all running state from the append-only completed-game log."""
        self.main = BettingProcess()
        self.mirror = BettingProcess()
        self.candidate_sum = self.incumbent_sum = 0.0
        self.candidate_n = self.incumbent_n = 0
        self._rng = random.Random(self.seed)
        assignment_log = self.log_path.with_suffix(".assignments.jsonl")
        assignments = []
        if assignment_log.exists():
            assignments = [
                json.loads(line)["assigned_arm"]
                for line in assignment_log.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        for _ in assignments:
            self._rng.random()
        completed = 0
        if not self.log_path.exists():
            self._pending = assignments
            return
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            completed += 1
            x = float(record["X_t"])
            self.main.update(x)
            self.mirror.update(-x)
            payoff = float(record["Y_t"])
            if record["assigned_arm"] == "candidate":
                self.candidate_sum += payoff
                self.candidate_n += 1
            else:
                self.incumbent_sum += payoff
                self.incumbent_n += 1
        self._pending = assignments[completed:]

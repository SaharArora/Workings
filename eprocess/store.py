"""Concurrency-safe assignment and e-process persistence for live cohorts."""

from __future__ import annotations

import json
import math
import secrets
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from collections.abc import Callable
from typing import Any, Mapping

from eprocess.betting import BETTING_FRACTIONS
from eprocess.cohort import (
    ASSIGNMENT_ALGORITHM,
    COHORT_ID,
    PAYOFF_TRANSFORM_VERSION,
    SAFETY_BAD_RATE_LIMIT,
    SAFETY_FIRST_BAD_COUNT,
    SAFETY_RATE_MIN_CHALLENGER,
    ExperimentSpec,
    confirmation_experiment_id,
    eligible_experiment_ids,
    exact_configuration,
    experiment_registry,
    family_subcohort_id,
    opponent_category,
    registry_hash,
    role_for_game,
    structural_cell,
)
from glee.payoffs import bad_outcome

EXPERIMENT_STATUSES = {
    "NOT_STARTED",
    "RUNNING",
    "PROMOTION_CANDIDATE",
    "PROMOTE",
    "RETAIN",
    "INCONCLUSIVE",
    "SAFETY_PAUSED",
    "RESOLVED_OBSERVATIONAL_FALLBACK",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))


def _components() -> dict[str, float]:
    return {str(value): 1.0 for value in BETTING_FRACTIONS}


def _wealth(components: Mapping[str, float]) -> float:
    return sum(float(value) for value in components.values()) / len(components)


def _updated_components(
    components: Mapping[str, float], observation: float
) -> dict[str, float]:
    if not -1 <= observation <= 1:
        raise ValueError("e-process observation must lie in [-1, 1]")
    return {
        str(fraction): float(components[str(fraction)]) * (1 + fraction * observation)
        for fraction in BETTING_FRACTIONS
    }


@dataclass(frozen=True, slots=True)
class AssignmentRecord:
    cohort_id: str
    subcohort_id: str
    game_id: str
    family: str
    structural_cell: str
    exact_configuration: Mapping[str, Any]
    role: str
    opponent_category: str
    opponent_identity: str | None
    experiment_id: str | None
    evidence_class: str
    assigned_arm: str
    assignment_probability: float
    incumbent: str
    challenger: str | None
    assigned_policy: str
    policy_version: str
    payoff_transform_version: str
    alpha_family: float | None
    multiplicity: int | None
    alpha_test: float | None
    delta_min: float | None
    frozen_commit: str
    informative: bool
    informative_reason: str | None
    assignment_reason: str

    def structured(self) -> dict[str, Any]:
        return asdict(self)


class CohortStore:
    """SQLite-backed single source of truth shared by all family executors."""

    def __init__(
        self,
        path: Path,
        *,
        frozen_commit: str,
        arm_draw: Callable[[ExperimentSpec, str, str], str] | None = None,
    ) -> None:
        self.path = Path(path)
        self.frozen_commit = str(frozen_commit)
        self.specs = {item.experiment_id: item for item in experiment_registry()}
        self._arm_draw = arm_draw

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id TEXT PRIMARY KEY,
                    family TEXT NOT NULL,
                    spec_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    decision_reason TEXT,
                    main_components TEXT NOT NULL,
                    mirror_components TEXT NOT NULL,
                    n_control INTEGER NOT NULL DEFAULT 0,
                    n_challenger INTEGER NOT NULL DEFAULT 0,
                    control_sum_y REAL NOT NULL DEFAULT 0,
                    challenger_sum_y REAL NOT NULL DEFAULT 0,
                    control_sum_raw REAL NOT NULL DEFAULT 0,
                    challenger_sum_raw REAL NOT NULL DEFAULT 0,
                    control_bad INTEGER NOT NULL DEFAULT 0,
                    challenger_bad INTEGER NOT NULL DEFAULT 0,
                    clipping_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS family_games (
                    game_id TEXT PRIMARY KEY,
                    family TEXT NOT NULL,
                    tracked_at TEXT NOT NULL,
                    completed_at TEXT,
                    completion_reason TEXT
                );
                CREATE TABLE IF NOT EXISTS family_runs (
                    family TEXT PRIMARY KEY,
                    subcohort_id TEXT NOT NULL,
                    target_completed INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    start_rating REAL,
                    start_games_played INTEGER,
                    ended_at TEXT,
                    end_rating REAL,
                    final_status TEXT,
                    checkpoints_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS assignments (
                    game_id TEXT PRIMARY KEY,
                    cohort_id TEXT NOT NULL,
                    subcohort_id TEXT NOT NULL,
                    family TEXT NOT NULL,
                    structural_cell TEXT NOT NULL,
                    exact_configuration TEXT NOT NULL,
                    role TEXT NOT NULL,
                    opponent_category TEXT NOT NULL,
                    opponent_identity TEXT,
                    experiment_id TEXT,
                    evidence_class TEXT NOT NULL,
                    assigned_arm TEXT NOT NULL,
                    assignment_probability REAL NOT NULL,
                    incumbent TEXT NOT NULL,
                    challenger TEXT,
                    assigned_policy TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    payoff_transform_version TEXT NOT NULL,
                    alpha_family REAL,
                    multiplicity INTEGER,
                    alpha_test REAL,
                    delta_min REAL,
                    frozen_commit TEXT NOT NULL,
                    assignment_algorithm TEXT NOT NULL,
                    assigned_at TEXT NOT NULL,
                    informative INTEGER NOT NULL DEFAULT 1,
                    informative_reason TEXT,
                    assignment_reason TEXT NOT NULL,
                    trace_status TEXT NOT NULL DEFAULT 'ASSIGNED',
                    FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id)
                );
                CREATE TABLE IF NOT EXISTS outcomes (
                    game_id TEXT PRIMARY KEY,
                    experiment_id TEXT,
                    assigned_arm TEXT NOT NULL,
                    raw_payoff REAL,
                    bounded_payoff REAL,
                    payoff_transform TEXT,
                    clipping_occurred INTEGER NOT NULL DEFAULT 0,
                    bad_outcome INTEGER,
                    bad_outcome_category TEXT,
                    terminal_outcome TEXT,
                    valid_for_eprocess INTEGER NOT NULL,
                    exclusion_reason TEXT,
                    completed_at TEXT NOT NULL,
                    FOREIGN KEY(game_id) REFERENCES assignments(game_id)
                );
                CREATE TABLE IF NOT EXISTS eprocess_updates (
                    game_id TEXT PRIMARY KEY,
                    experiment_id TEXT NOT NULL,
                    E_t REAL NOT NULL,
                    E_t_prime REAL NOT NULL,
                    n_control INTEGER NOT NULL,
                    n_challenger INTEGER NOT NULL,
                    X_t REAL NOT NULL,
                    X_t_prime REAL NOT NULL,
                    main_components TEXT NOT NULL,
                    mirror_components TEXT NOT NULL,
                    transformed_effect REAL NOT NULL,
                    raw_effect REAL NOT NULL,
                    clipping_count INTEGER NOT NULL,
                    clipping_rate REAL NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(game_id) REFERENCES assignments(game_id)
                );
                """
            )
            expected_metadata = {
                "cohort_id": COHORT_ID,
                "frozen_commit": self.frozen_commit,
                "registry_hash": registry_hash(),
                "assignment_algorithm": ASSIGNMENT_ALGORITHM,
                "payoff_transform_version": PAYOFF_TRANSFORM_VERSION,
            }
            for key, value in expected_metadata.items():
                existing = connection.execute(
                    "SELECT value FROM metadata WHERE key=?", (key,)
                ).fetchone()
                if existing is not None and existing["value"] != value:
                    raise RuntimeError(f"cohort metadata mismatch for {key}")
                connection.execute(
                    "INSERT OR IGNORE INTO metadata(key,value) VALUES (?,?)",
                    (key, value),
                )
            for spec in self.specs.values():
                existing = connection.execute(
                    "SELECT spec_json FROM experiments WHERE experiment_id=?",
                    (spec.experiment_id,),
                ).fetchone()
                encoded = _json(spec.structured())
                if existing is not None and existing["spec_json"] != encoded:
                    raise RuntimeError(f"experiment definition changed: {spec.experiment_id}")
                connection.execute(
                    """
                    INSERT OR IGNORE INTO experiments(
                        experiment_id,family,spec_json,status,main_components,
                        mirror_components,updated_at
                    ) VALUES (?,?,?,?,?,?,?)
                    """,
                    (
                        spec.experiment_id,
                        spec.family,
                        encoded,
                        spec.initial_status,
                        _json(_components()),
                        _json(_components()),
                        _now(),
                    ),
                )

    def _assignment_arm(
        self, spec: ExperimentSpec, game_id: str, cell: str
    ) -> str:
        arm = (
            self._arm_draw(spec, game_id, cell)
            if self._arm_draw is not None
            else ("challenger" if secrets.randbits(1) else "control")
        )
        if arm not in {"control", "challenger"}:
            raise ValueError("assignment draw must return control or challenger")
        return arm

    @staticmethod
    def _row_to_assignment(row: sqlite3.Row) -> AssignmentRecord:
        return AssignmentRecord(
            cohort_id=row["cohort_id"],
            subcohort_id=row["subcohort_id"],
            game_id=row["game_id"],
            family=row["family"],
            structural_cell=row["structural_cell"],
            exact_configuration=json.loads(row["exact_configuration"]),
            role=row["role"],
            opponent_category=row["opponent_category"],
            opponent_identity=row["opponent_identity"],
            experiment_id=row["experiment_id"],
            evidence_class=row["evidence_class"],
            assigned_arm=row["assigned_arm"],
            assignment_probability=float(row["assignment_probability"]),
            incumbent=row["incumbent"],
            challenger=row["challenger"],
            assigned_policy=row["assigned_policy"],
            policy_version=row["policy_version"],
            payoff_transform_version=row["payoff_transform_version"],
            alpha_family=row["alpha_family"],
            multiplicity=row["multiplicity"],
            alpha_test=row["alpha_test"],
            delta_min=row["delta_min"],
            frozen_commit=row["frozen_commit"],
            informative=bool(row["informative"]),
            informative_reason=row["informative_reason"],
            assignment_reason=row["assignment_reason"],
        )

    def assign_game(
        self, game: Mapping[str, Any], *, baseline_policy: str
    ) -> AssignmentRecord:
        """Persist one assignment atomically before treatment policy execution."""
        game_id = str(game["game_id"])
        family = str(game["game_family"])
        config = exact_configuration(game)
        cell = structural_cell(game)
        role = role_for_game(game)
        opponent = opponent_category(game)
        disclosed_opponent = game.get("opponent", {})
        opponent_identity = (
            str(disclosed_opponent.get("name"))
            if isinstance(disclosed_opponent, Mapping)
            and disclosed_opponent.get("name") not in {None, ""}
            else None
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM assignments WHERE game_id=?", (game_id,)
            ).fetchone()
            if existing is not None:
                connection.commit()
                return self._row_to_assignment(existing)
            candidates: list[tuple[int, int, ExperimentSpec]] = []
            promoted: ExperimentSpec | None = None
            for experiment_id in eligible_experiment_ids(game):
                exploration = self.specs[experiment_id]
                row = connection.execute(
                    "SELECT status,n_control,n_challenger FROM experiments WHERE experiment_id=?",
                    (experiment_id,),
                ).fetchone()
                if row is None:
                    continue
                if row["status"] == "RUNNING":
                    candidates.append(
                        (
                            exploration.priority,
                            int(row["n_control"]) + int(row["n_challenger"]),
                            exploration,
                        )
                    )
                    continue
                confirmation_id = confirmation_experiment_id(experiment_id)
                confirmation = self.specs[confirmation_id]
                confirmation_row = connection.execute(
                    "SELECT status,n_control,n_challenger FROM experiments WHERE experiment_id=?",
                    (confirmation_id,),
                ).fetchone()
                if (
                    row["status"] == "PROMOTION_CANDIDATE"
                    and confirmation_row is not None
                    and confirmation_row["status"] == "RUNNING"
                ):
                    candidates.append(
                        (
                            confirmation.priority,
                            int(confirmation_row["n_control"])
                            + int(confirmation_row["n_challenger"]),
                            confirmation,
                        )
                    )
                if row["status"] == "PROMOTE":
                    promoted = promoted or exploration
                elif confirmation_row is not None and confirmation_row["status"] == "PROMOTE":
                    promoted = promoted or confirmation
            # Priority is frozen. Effective randomized n is a tie-breaker only and
            # never depends on observed payoffs or current treatment effects.
            chosen = min(candidates, key=lambda item: (item[0], item[1], item[2].experiment_id))[2] if candidates else None
            if chosen is None:
                promoted_policy = (
                    promoted.challenger_policy if promoted is not None else baseline_policy
                )
                fields = {
                    "experiment_id": None,
                    "evidence_class": "OBSERVATIONAL_LIVE_EVIDENCE",
                    "assigned_arm": "observational",
                    "assignment_probability": 1.0,
                    "incumbent": promoted_policy,
                    "challenger": None,
                    "assigned_policy": promoted_policy,
                    "policy_version": (
                        promoted.policy_version
                        if promoted is not None
                        else "frozen-production-incumbent-v1"
                    ),
                    "alpha_family": None,
                    "multiplicity": None,
                    "alpha_test": None,
                    "delta_min": None,
                    "assignment_reason": (
                        "PROMOTED_POLICY_OBSERVATIONAL"
                        if promoted is not None
                        else "NO_RUNNING_ELIGIBLE_EXPERIMENT"
                    ),
                    "informative": True,
                }
            else:
                arm = self._assignment_arm(chosen, game_id, cell)
                assigned_policy = (
                    chosen.challenger_policy
                    if arm == "challenger"
                    else chosen.control_policy
                )
                fields = {
                    "experiment_id": chosen.experiment_id,
                    "evidence_class": "RANDOMIZED_LIVE_EVIDENCE",
                    "assigned_arm": arm,
                    "assignment_probability": chosen.assignment_probability,
                    "incumbent": chosen.control_policy,
                    "challenger": chosen.challenger_policy,
                    "assigned_policy": assigned_policy,
                    "policy_version": chosen.policy_version,
                    "alpha_family": chosen.alpha_family,
                    "multiplicity": chosen.multiplicity,
                    "alpha_test": chosen.alpha_test,
                    "delta_min": chosen.delta_min,
                    "assignment_reason": "PRETREATMENT_RANDOMIZED_PAIRWISE_ASSIGNMENT",
                    "informative": chosen.experiment_id not in {
                        "PERS_BUY_MARGIN_VS_THEORY",
                        "CONFIRM_PERS_BUY_MARGIN_VS_THEORY",
                    },
                }
            connection.execute(
                """
                INSERT INTO assignments(
                    game_id,cohort_id,subcohort_id,family,structural_cell,exact_configuration,
                    role,opponent_category,opponent_identity,experiment_id,evidence_class,assigned_arm,
                    assignment_probability,incumbent,challenger,assigned_policy,
                    policy_version,payoff_transform_version,alpha_family,multiplicity,
                    alpha_test,delta_min,frozen_commit,assignment_algorithm,assigned_at,
                    assignment_reason,informative,informative_reason
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    game_id,
                    COHORT_ID,
                    family_subcohort_id(family),
                    family,
                    cell,
                    _json(config),
                    role,
                    opponent,
                    opponent_identity,
                    fields["experiment_id"],
                    fields["evidence_class"],
                    fields["assigned_arm"],
                    fields["assignment_probability"],
                    fields["incumbent"],
                    fields["challenger"],
                    fields["assigned_policy"],
                    fields["policy_version"],
                    PAYOFF_TRANSFORM_VERSION,
                    fields["alpha_family"],
                    fields["multiplicity"],
                    fields["alpha_test"],
                    fields["delta_min"],
                    self.frozen_commit,
                    ASSIGNMENT_ALGORITHM,
                    _now(),
                    fields["assignment_reason"],
                    int(fields["informative"]),
                    (
                        None
                        if fields["informative"]
                        else "AWAITING_BUYER_POLICY_ACTION_DIVERGENCE"
                    ),
                ),
            )
            row = connection.execute(
                "SELECT * FROM assignments WHERE game_id=?", (game_id,)
            ).fetchone()
            connection.commit()
        assert row is not None
        return self._row_to_assignment(row)

    def assignment(self, game_id: str) -> AssignmentRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM assignments WHERE game_id=?", (str(game_id),)
            ).fetchone()
        return None if row is None else self._row_to_assignment(row)

    def start_family_run(
        self, family: str, *, family_cap: int, stats: Mapping[str, Any]
    ) -> None:
        """Freeze the family start rating/count once; restarts reuse the same baseline."""
        score = stats.get("scores", {}).get(str(family), {})
        rating = score.get("rating") if isinstance(score, Mapping) else None
        games = score.get("games_played") if isinstance(score, Mapping) else None
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT target_completed FROM family_runs WHERE family=?", (str(family),)
            ).fetchone()
            if existing is not None and int(existing["target_completed"]) != int(family_cap):
                raise RuntimeError("family target changed after cohort launch")
            connection.execute(
                """
                INSERT OR IGNORE INTO family_runs(
                    family,subcohort_id,target_completed,started_at,start_rating,start_games_played
                ) VALUES (?,?,?,?,?,?)
                """,
                (
                    str(family),
                    family_subcohort_id(str(family)),
                    int(family_cap),
                    _now(),
                    None if rating is None else float(rating),
                    None if games is None else int(games),
                ),
            )
            connection.commit()

    def record_family_checkpoint(
        self, family: str, *, checkpoint: int, stats: Mapping[str, Any]
    ) -> None:
        """Persist reporting metadata without changing assignment or evidence state."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT checkpoints_json FROM family_runs WHERE family=?", (str(family),)
            ).fetchone()
            if row is None:
                raise RuntimeError("family run has not started")
            checkpoints = json.loads(row["checkpoints_json"])
            checkpoints.setdefault(str(int(checkpoint)), {"timestamp": _now(), "stats": dict(stats)})
            connection.execute(
                "UPDATE family_runs SET checkpoints_json=? WHERE family=?",
                (_json(checkpoints), str(family)),
            )
            connection.commit()

    def complete_family_run(
        self, family: str, *, status: str, stats: Mapping[str, Any]
    ) -> None:
        score = stats.get("scores", {}).get(str(family), {})
        rating = score.get("rating") if isinstance(score, Mapping) else None
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE family_runs
                SET ended_at=?,end_rating=?,final_status=?
                WHERE family=?
                """,
                (
                    _now(),
                    None if rating is None else float(rating),
                    str(status),
                    str(family),
                ),
            )

    def emitted_checkpoints(self, family: str) -> set[int]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT checkpoints_json FROM family_runs WHERE family=?", (str(family),)
            ).fetchone()
        if row is None:
            return set()
        return {int(value) for value in json.loads(row["checkpoints_json"])}

    def record_tracked_game(self, game_id: str, *, family: str, family_cap: int) -> None:
        """Count an authoritative live match once, even before strategy execution."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT family FROM family_games WHERE game_id=?", (str(game_id),)
            ).fetchone()
            if existing is not None:
                if existing["family"] != str(family):
                    raise RuntimeError("tracked game family changed")
                connection.commit()
                return
            count = connection.execute(
                "SELECT COUNT(*) AS n FROM family_games WHERE family=?",
                (str(family),),
            ).fetchone()
            if count is not None and int(count["n"]) >= int(family_cap):
                raise RuntimeError("family live-game cap already reached")
            connection.execute(
                "INSERT INTO family_games(game_id,family,tracked_at) VALUES (?,?,?)",
                (str(game_id), str(family), _now()),
            )
            connection.commit()

    def record_completed_game(self, game_id: str, *, reason: str) -> None:
        """Mark one tracked match terminal without double-counting repeat polls."""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE family_games SET completed_at=?,completion_reason=?
                WHERE game_id=? AND completed_at IS NULL
                """,
                (_now(), str(reason), str(game_id)),
            )
            if cursor.rowcount == 0:
                row = connection.execute(
                    "SELECT game_id FROM family_games WHERE game_id=?", (str(game_id),)
                ).fetchone()
                if row is None:
                    raise RuntimeError("cannot complete an untracked family game")

    def mark_noninformative(self, game_id: str, *, reason: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE assignments
                SET informative=0, informative_reason=?
                WHERE game_id=? AND trace_status='ASSIGNED'
                """,
                (reason, str(game_id)),
            )

    def mark_informative(self, game_id: str, *, reason: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE assignments
                SET informative=1, informative_reason=?
                WHERE game_id=? AND trace_status='ASSIGNED'
                """,
                (reason, str(game_id)),
            )

    def safety_pause_for_game(self, game_id: str, *, reason: str) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT experiment_id FROM assignments WHERE game_id=?", (str(game_id),)
            ).fetchone()
            if row is not None and row["experiment_id"] is not None:
                connection.execute(
                    """
                    UPDATE experiments SET status='SAFETY_PAUSED',decision_reason=?,updated_at=?
                    WHERE experiment_id=? AND status='RUNNING'
                    """,
                    (reason, _now(), row["experiment_id"]),
                )
            connection.commit()

    def record_outcome(
        self,
        game_id: str,
        *,
        raw_payoff: float | None,
        bounded_payoff: float | None,
        payoff_transform: Mapping[str, Any] | None,
        terminal_outcome: str,
        valid_trace: bool,
        exclusion_reason: str | None = None,
    ) -> dict[str, Any]:
        """Record one terminal result and update at most one e-process exactly once."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute(
                "SELECT * FROM outcomes WHERE game_id=?", (str(game_id),)
            ).fetchone()
            if prior is not None:
                connection.commit()
                return {"duplicate": True, "game_id": str(game_id)}
            assignment = connection.execute(
                "SELECT * FROM assignments WHERE game_id=?", (str(game_id),)
            ).fetchone()
            if assignment is None:
                raise RuntimeError("terminal outcome has no pre-treatment assignment")
            numeric_raw = None if raw_payoff is None else float(raw_payoff)
            numeric_y = None if bounded_payoff is None else float(bounded_payoff)
            if numeric_y is not None and not 0 <= numeric_y <= 1:
                raise ValueError("bounded payoff must lie in [0, 1]")
            assessment = (
                None
                if numeric_raw is None
                else bad_outcome(
                    assignment["family"],
                    numeric_raw,
                    json.loads(assignment["exact_configuration"]),
                    assignment["role"],
                )
            )
            transform = dict(payoff_transform or {})
            clipped = bool(transform.get("clipping_occurred", False))
            randomized = assignment["experiment_id"] is not None
            valid_for_eprocess = bool(
                randomized
                and assignment["informative"]
                and valid_trace
                and numeric_raw is not None
                and numeric_y is not None
            )
            reason = exclusion_reason
            if randomized and not valid_for_eprocess and reason is None:
                reason = (
                    "NONINFORMATIVE_ASSIGNMENT"
                    if not assignment["informative"]
                    else "INCOMPLETE_OR_INVALID_TRACE"
                )
            connection.execute(
                """
                INSERT INTO outcomes(
                    game_id,experiment_id,assigned_arm,raw_payoff,bounded_payoff,
                    payoff_transform,clipping_occurred,bad_outcome,bad_outcome_category,
                    terminal_outcome,valid_for_eprocess,exclusion_reason,completed_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    str(game_id),
                    assignment["experiment_id"],
                    assignment["assigned_arm"],
                    numeric_raw,
                    numeric_y,
                    _json(transform) if transform else None,
                    int(clipped),
                    None if assessment is None else int(assessment.bad),
                    None if assessment is None else str(assessment.category),
                    str(terminal_outcome),
                    int(valid_for_eprocess),
                    reason,
                    _now(),
                ),
            )
            connection.execute(
                "UPDATE assignments SET trace_status=? WHERE game_id=?",
                ("COMPLETED" if valid_trace else "EXCLUDED", str(game_id)),
            )
            if randomized and not valid_trace:
                connection.execute(
                    """
                    UPDATE experiments SET status='SAFETY_PAUSED',decision_reason=?,updated_at=?
                    WHERE experiment_id=? AND status='RUNNING'
                    """,
                    (reason or "INVALID_OR_INCOMPLETE_TRACE", _now(), assignment["experiment_id"]),
                )
            update: dict[str, Any] = {
                "duplicate": False,
                "game_id": str(game_id),
                "experiment_id": assignment["experiment_id"],
                "valid_for_eprocess": valid_for_eprocess,
                "exclusion_reason": reason,
            }
            if valid_for_eprocess:
                update.update(
                    self._update_experiment(
                        connection,
                        assignment=assignment,
                        raw_payoff=numeric_raw,
                        bounded_payoff=numeric_y,
                        clipped=clipped,
                        bad=bool(assessment and assessment.bad),
                    )
                )
            connection.commit()
            return update

    def _update_experiment(
        self,
        connection: sqlite3.Connection,
        *,
        assignment: sqlite3.Row,
        raw_payoff: float,
        bounded_payoff: float,
        clipped: bool,
        bad: bool,
    ) -> dict[str, Any]:
        experiment_id = str(assignment["experiment_id"])
        state = connection.execute(
            "SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,)
        ).fetchone()
        assert state is not None
        arm = str(assignment["assigned_arm"])
        sign = 1.0 if arm == "challenger" else -1.0
        observation = sign * bounded_payoff
        main = _updated_components(json.loads(state["main_components"]), observation)
        mirror = _updated_components(json.loads(state["mirror_components"]), -observation)
        n_control = int(state["n_control"]) + int(arm == "control")
        n_challenger = int(state["n_challenger"]) + int(arm == "challenger")
        control_sum_y = float(state["control_sum_y"]) + (
            bounded_payoff if arm == "control" else 0.0
        )
        challenger_sum_y = float(state["challenger_sum_y"]) + (
            bounded_payoff if arm == "challenger" else 0.0
        )
        control_sum_raw = float(state["control_sum_raw"]) + (
            raw_payoff if arm == "control" else 0.0
        )
        challenger_sum_raw = float(state["challenger_sum_raw"]) + (
            raw_payoff if arm == "challenger" else 0.0
        )
        control_bad = int(state["control_bad"]) + int(arm == "control" and bad)
        challenger_bad = int(state["challenger_bad"]) + int(arm == "challenger" and bad)
        clipping_count = int(state["clipping_count"]) + int(clipped)
        transformed_effect = (
            challenger_sum_y / n_challenger - control_sum_y / n_control
            if n_control and n_challenger
            else 0.0
        )
        raw_effect = (
            challenger_sum_raw / n_challenger - control_sum_raw / n_control
            if n_control and n_challenger
            else 0.0
        )
        E_t = _wealth(main)
        E_t_prime = _wealth(mirror)
        spec = self.specs[experiment_id]
        status = str(state["status"])
        decision_reason = state["decision_reason"]
        if status == "RUNNING" and n_challenger >= SAFETY_FIRST_BAD_COUNT:
            first_bad_window = connection.execute(
                """
                SELECT o.bad_outcome FROM outcomes o
                JOIN assignments a ON a.game_id=o.game_id
                WHERE a.experiment_id=? AND a.assigned_arm='challenger'
                  AND o.valid_for_eprocess=1
                ORDER BY o.completed_at LIMIT ?
                """,
                (experiment_id, SAFETY_FIRST_BAD_COUNT),
            ).fetchall()
            if len(first_bad_window) == SAFETY_FIRST_BAD_COUNT and all(
                bool(item["bad_outcome"]) for item in first_bad_window
            ):
                status = "SAFETY_PAUSED"
                decision_reason = "FIRST_FIVE_CHALLENGER_OUTCOMES_ALL_BAD"
            elif (
                n_challenger >= SAFETY_RATE_MIN_CHALLENGER
                and challenger_bad / n_challenger > SAFETY_BAD_RATE_LIMIT
            ):
                status = "SAFETY_PAUSED"
                decision_reason = "CHALLENGER_BAD_OUTCOME_RATE_ABOVE_0_75_AFTER_8"
        if status == "RUNNING" and E_t >= spec.promotion_threshold and transformed_effect > spec.delta_min:
            if spec.stage == "exploration":
                status = "PROMOTION_CANDIDATE"
                decision_reason = "EXPLORATION_CROSSED_THRESHOLD_PENDING_FRESH_CONFIRMATION"
                connection.execute(
                    """
                    UPDATE experiments
                    SET status='RUNNING',decision_reason='ACTIVATED_BY_EXPLORATION_PROMOTION_CANDIDATE',updated_at=?
                    WHERE experiment_id=? AND status='NOT_STARTED'
                    """,
                    (_now(), confirmation_experiment_id(experiment_id)),
                )
            else:
                status = "PROMOTE"
                decision_reason = "FRESH_CONFIRMATION_CROSSED_THRESHOLD_WITH_MINIMUM_EFFECT"
        elif status == "RUNNING" and E_t_prime >= spec.promotion_threshold:
            status = "RETAIN"
            decision_reason = "MIRROR_EPROCESS_CROSSED_THRESHOLD"
        connection.execute(
            """
            UPDATE experiments SET
                status=?,decision_reason=?,main_components=?,mirror_components=?,
                n_control=?,n_challenger=?,control_sum_y=?,challenger_sum_y=?,
                control_sum_raw=?,challenger_sum_raw=?,control_bad=?,challenger_bad=?,
                clipping_count=?,updated_at=?
            WHERE experiment_id=?
            """,
            (
                status,
                decision_reason,
                _json(main),
                _json(mirror),
                n_control,
                n_challenger,
                control_sum_y,
                challenger_sum_y,
                control_sum_raw,
                challenger_sum_raw,
                control_bad,
                challenger_bad,
                clipping_count,
                _now(),
                experiment_id,
            ),
        )
        total = n_control + n_challenger
        connection.execute(
            """
            INSERT INTO eprocess_updates(
                game_id,experiment_id,E_t,E_t_prime,n_control,n_challenger,
                X_t,X_t_prime,main_components,mirror_components,transformed_effect,
                raw_effect,clipping_count,clipping_rate,status,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                assignment["game_id"],
                experiment_id,
                E_t,
                E_t_prime,
                n_control,
                n_challenger,
                observation,
                -observation,
                _json(main),
                _json(mirror),
                transformed_effect,
                raw_effect,
                clipping_count,
                clipping_count / total,
                status,
                _now(),
            ),
        )
        return {
            "E_t": E_t,
            "E_t_prime": E_t_prime,
            "n_control": n_control,
            "n_challenger": n_challenger,
            "X_t": observation,
            "X_t_prime": -observation,
            "transformed_effect": transformed_effect,
            "raw_effect": raw_effect,
            "clipping_count": clipping_count,
            "clipping_rate": clipping_count / total,
            "status": status,
            "decision_reason": decision_reason,
        }

    def close_running_experiments(self, family: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE experiments
                SET status='INCONCLUSIVE',decision_reason='FAMILY_COHORT_CAP_REACHED',updated_at=?
                WHERE family=? AND status='RUNNING'
                """,
                (_now(), str(family)),
            )
            connection.execute(
                """
                UPDATE experiments
                SET decision_reason='PROMOTION_PENDING_CONFIRMATION_FAMILY_CAP_REACHED',updated_at=?
                WHERE family=? AND status='PROMOTION_CANDIDATE'
                """,
                (_now(), str(family)),
            )

    def experiment_status(self, experiment_id: str) -> str:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM experiments WHERE experiment_id=?",
                (str(experiment_id),),
            ).fetchone()
        if row is None:
            raise KeyError(experiment_id)
        return str(row["status"])

    def family_counts(self, family: str) -> dict[str, int]:
        with self._connect() as connection:
            assigned = connection.execute(
                "SELECT COUNT(*) AS n FROM assignments WHERE family=?",
                (str(family),),
            ).fetchone()
            outcomes = connection.execute(
                """
                SELECT COUNT(*) AS n FROM outcomes o
                JOIN assignments a ON a.game_id=o.game_id
                WHERE a.family=?
                """,
                (str(family),),
            ).fetchone()
            tracked = connection.execute(
                "SELECT COUNT(*) AS n FROM family_games WHERE family=?",
                (str(family),),
            ).fetchone()
            completed = connection.execute(
                """
                SELECT COUNT(*) AS n FROM family_games
                WHERE family=? AND completed_at IS NOT NULL
                """,
                (str(family),),
            ).fetchone()
        return {
            "assigned": int(assigned["n"] if assigned else 0),
            "outcome_records": int(outcomes["n"] if outcomes else 0),
            "tracked": int(tracked["n"] if tracked else 0),
            "completed": int(completed["n"] if completed else 0),
        }

    def snapshot(self) -> dict[str, Any]:
        with self._connect() as connection:
            metadata = {
                row["key"]: row["value"]
                for row in connection.execute("SELECT key,value FROM metadata")
            }
            experiments = []
            for row in connection.execute("SELECT * FROM experiments ORDER BY experiment_id"):
                total = int(row["n_control"]) + int(row["n_challenger"])
                experiments.append(
                    {
                        "experiment_id": row["experiment_id"],
                        "family": row["family"],
                        "status": row["status"],
                        "decision_reason": row["decision_reason"],
                        "E_t": _wealth(json.loads(row["main_components"])),
                        "E_t_prime": _wealth(json.loads(row["mirror_components"])),
                        "n_control": row["n_control"],
                        "n_challenger": row["n_challenger"],
                        "mean_y_control": (
                            row["control_sum_y"] / row["n_control"]
                            if row["n_control"] else None
                        ),
                        "mean_y_challenger": (
                            row["challenger_sum_y"] / row["n_challenger"]
                            if row["n_challenger"] else None
                        ),
                        "mean_raw_control": (
                            row["control_sum_raw"] / row["n_control"]
                            if row["n_control"] else None
                        ),
                        "mean_raw_challenger": (
                            row["challenger_sum_raw"] / row["n_challenger"]
                            if row["n_challenger"] else None
                        ),
                        "bad_outcome_rate_control": (
                            row["control_bad"] / row["n_control"]
                            if row["n_control"] else None
                        ),
                        "bad_outcome_rate_challenger": (
                            row["challenger_bad"] / row["n_challenger"]
                            if row["n_challenger"] else None
                        ),
                        "transformed_effect": (
                            row["challenger_sum_y"] / row["n_challenger"]
                            - row["control_sum_y"] / row["n_control"]
                            if row["n_control"] and row["n_challenger"]
                            else 0.0
                        ),
                        "raw_effect": (
                            row["challenger_sum_raw"] / row["n_challenger"]
                            - row["control_sum_raw"] / row["n_control"]
                            if row["n_control"] and row["n_challenger"]
                            else 0.0
                        ),
                        "clipping_count": row["clipping_count"],
                        "clipping_rate": row["clipping_count"] / total if total else 0.0,
                        "spec": json.loads(row["spec_json"]),
                    }
                )
            counts = {
                row["family"]: int(row["n"])
                for row in connection.execute(
                    "SELECT family,COUNT(*) AS n FROM assignments GROUP BY family"
                )
            }
            family_runs = {
                row["family"]: dict(row)
                for row in connection.execute("SELECT * FROM family_runs ORDER BY family")
            }
        return {
            "metadata": metadata,
            "family_assignment_counts": counts,
            "family_runs": family_runs,
            "experiments": experiments,
        }

    def replay_experiment(self, experiment_id: str) -> dict[str, Any]:
        """Independently replay the append-only SQL evidence rows for audit."""
        main = _components()
        mirror = _components()
        n_control = 0
        n_challenger = 0
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT u.game_id,u.X_t,u.X_t_prime,a.assigned_arm
                FROM eprocess_updates u
                JOIN assignments a ON a.game_id=u.game_id
                WHERE u.experiment_id=?
                ORDER BY u.rowid
                """,
                (str(experiment_id),),
            ).fetchall()
        for row in rows:
            main = _updated_components(main, float(row["X_t"]))
            mirror = _updated_components(mirror, float(row["X_t_prime"]))
            n_control += int(row["assigned_arm"] == "control")
            n_challenger += int(row["assigned_arm"] == "challenger")
        return {
            "experiment_id": str(experiment_id),
            "n_updates": len(rows),
            "n_control": n_control,
            "n_challenger": n_challenger,
            "main_components": main,
            "mirror_components": mirror,
            "E_t": _wealth(main),
            "E_t_prime": _wealth(mirror),
        }

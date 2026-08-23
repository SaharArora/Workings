"""Read-only dashboards and auditable reports for the fixed 3,000-game cohort."""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from eprocess.cohort import (
    COHORT_ID,
    FAMILY_CAP,
    REPORTING_CHECKPOINTS,
    experiment_registry,
    registry_hash,
    registry_payload,
)
from eprocess.store import CohortStore

BAD_OUTCOME_DEFINITIONS = {
    "negotiation": "raw own payoff <= 0 (negative, zero-margin agreement, no-deal, or walkaway)",
    "bargaining": "raw own mechanism utility <= 0 (zero/no-deal/walkaway or negative)",
    "persuasion:buyer": "raw realized buyer utility <= 0, with negative/zero retained separately",
    "persuasion:seller": "raw seller payoff <= 0 (zero/no-sale or negative)",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def distribution(values: Iterable[float], *, bad_count: int = 0) -> dict[str, Any]:
    sample = [float(value) for value in values]
    return {
        "n": len(sample),
        "mean": statistics.fmean(sample) if sample else None,
        "median": statistics.median(sample) if sample else None,
        "standard_deviation": statistics.pstdev(sample) if sample else None,
        "q10": _quantile(sample, 0.10),
        "q25": _quantile(sample, 0.25),
        "q75": _quantile(sample, 0.75),
        "q90": _quantile(sample, 0.90),
        "bad_outcome_mass": bad_count / len(sample) if sample else None,
    }


def _load_events(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                events.append(value)
    return events


def _operational(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    invalid = 0
    fallbacks = 0
    timeouts = 0
    poll_errors = 0
    integrity_reasons: Counter[str] = Counter()
    for item in events:
        event = str(item.get("event", ""))
        if event == "EVIDENCE_TRACE_INVALIDATED":
            reason = str(item.get("reason", "UNKNOWN"))
            integrity_reasons[reason] += 1
            invalid += int("INVALID_ACTION" in reason or "UNSUPPORTED" in reason)
            fallbacks += int("FALLBACK" in reason)
        if event == "supervisor_event":
            supervisor = item.get("supervisor", {})
            kind = str(supervisor.get("event", "")) if isinstance(supervisor, Mapping) else ""
            invalid += int(kind == "action_result" and supervisor.get("result", {}).get("valid") is False)
            fallbacks += int(kind == "strategy_fallback")
            timeouts += int(kind == "run_timeout")
            poll_errors += int(kind == "poll_error")
    return {
        "invalid_actions": invalid,
        "fallbacks": fallbacks,
        "timeouts": timeouts,
        "transient_poll_errors": poll_errors,
        "assignment_or_trace_integrity_events": dict(integrity_reasons),
    }


def family_dashboard(
    store: CohortStore,
    *,
    family: str,
    stats: Mapping[str, Any] | None = None,
    log_path: Path | None = None,
    checkpoint: int | None = None,
) -> dict[str, Any]:
    """Build a report without mutating assignment, policy, or e-process state."""
    counts = store.family_counts(family)
    snapshot = store.snapshot()
    with store._connect() as connection:
        assignment_rows = connection.execute(
            "SELECT * FROM assignments WHERE family=? ORDER BY assigned_at", (family,)
        ).fetchall()
        outcome_rows = connection.execute(
            """
            SELECT o.*,a.structural_cell,a.role,a.opponent_category,a.opponent_identity,
                   a.evidence_class,a.exact_configuration,a.assigned_policy
            FROM outcomes o JOIN assignments a ON a.game_id=o.game_id
            WHERE a.family=? ORDER BY o.completed_at
            """,
            (family,),
        ).fetchall()

    randomized = sum(row["experiment_id"] is not None for row in assignment_rows)
    observational = sum(row["experiment_id"] is None for row in assignment_rows)
    excluded = sum(
        row["experiment_id"] is not None and not bool(row["valid_for_eprocess"])
        for row in outcome_rows
    )
    by_experiment_arm: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for row in outcome_rows:
        if row["experiment_id"]:
            by_experiment_arm[(str(row["experiment_id"]), str(row["assigned_arm"]))].append(row)

    experiments: list[dict[str, Any]] = []
    for item in snapshot["experiments"]:
        if item["family"] != family:
            continue
        detail = dict(item)
        arm_distributions: dict[str, Any] = {}
        for arm in ("control", "challenger"):
            rows = by_experiment_arm.get((str(item["experiment_id"]), arm), [])
            raw_values = [float(row["raw_payoff"]) for row in rows if row["raw_payoff"] is not None]
            y_values = [float(row["bounded_payoff"]) for row in rows if row["bounded_payoff"] is not None]
            bad = sum(bool(row["bad_outcome"]) for row in rows)
            arm_distributions[arm] = {
                "raw_payoff": distribution(raw_values, bad_count=bad),
                "bounded_payoff_Y": distribution(y_values, bad_count=bad),
            }
        detail["arm_distributions"] = arm_distributions
        detail["eligible_games"] = sum(
            row["experiment_id"] == item["experiment_id"] for row in assignment_rows
        )
        detail["randomized_games"] = detail["n_control"] + detail["n_challenger"]
        detail["excluded_games"] = sum(
            row["experiment_id"] == item["experiment_id"] and not bool(row["valid_for_eprocess"])
            for row in outcome_rows
        )
        if checkpoint and checkpoint > 0:
            frequency = detail["eligible_games"] / checkpoint
            projected = frequency * FAMILY_CAP
            detail["eligibility_frequency"] = frequency
            detail["projected_eligible_by_1000"] = projected
            detail["projected_control_n_by_1000"] = projected / 2
            detail["projected_challenger_n_by_1000"] = projected / 2
        experiments.append(detail)

    structural = Counter(str(row["structural_cell"]) for row in assignment_rows)
    opponents: dict[str, dict[str, Any]] = {}
    for category in sorted({str(row["opponent_category"]) for row in assignment_rows}):
        rows = [row for row in outcome_rows if str(row["opponent_category"]) == category]
        values = [float(row["raw_payoff"]) for row in rows if row["raw_payoff"] is not None]
        opponents[category] = {
            "assignments": sum(str(row["opponent_category"]) == category for row in assignment_rows),
            "raw_payoff": distribution(values, bad_count=sum(bool(row["bad_outcome"]) for row in rows)),
            "disclosed_identities": sorted(
                {str(row["opponent_identity"]) for row in assignment_rows if str(row["opponent_category"]) == category and row["opponent_identity"]}
            ),
        }

    score = (stats or {}).get("scores", {}).get(family, {})
    run = snapshot.get("family_runs", {}).get(family, {})
    start_rating = run.get("start_rating") if isinstance(run, Mapping) else None
    current_rating = score.get("rating") if isinstance(score, Mapping) else None
    events = _load_events(log_path)
    outcome_counts = Counter(str(row["terminal_outcome"]) for row in outcome_rows)
    family_specific: dict[str, Any] = {"terminal_outcome_counts": dict(outcome_counts)}
    if family == "negotiation":
        terminal_diagnostics = [
            item.get("negotiation_terminal_diagnostics", {})
            for item in events
            if item.get("event") == "game_result"
            and isinstance(item.get("negotiation_terminal_diagnostics"), Mapping)
        ]
        agreements = sum(bool(item.get("agreement")) for item in terminal_diagnostics)
        no_deals = sum(bool(item.get("no_deal")) for item in terminal_diagnostics)
        walkaways = sum(bool(item.get("walkaway")) for item in terminal_diagnostics)
        agreed_prices = [
            float(item["agreed_price"])
            for item in terminal_diagnostics
            if isinstance(item.get("agreed_price"), (int, float))
        ]
        margins = [
            float(item["final_agreement_margin"])
            for item in terminal_diagnostics
            if isinstance(item.get("final_agreement_margin"), (int, float))
        ]
        rounds = [
            float(item["rounds_played"])
            for item in terminal_diagnostics
            if isinstance(item.get("rounds_played"), (int, float))
        ]
        n_terminal = len(terminal_diagnostics)
        family_specific.update(
            {
                "agreement_rate": agreements / n_terminal if n_terminal else None,
                "no_deal_rate": no_deals / n_terminal if n_terminal else None,
                "walkaway_rate": walkaways / n_terminal if n_terminal else None,
                "agreed_price_distribution": distribution(agreed_prices),
                "seller_final_margin_distribution": distribution(margins),
                "rounds_to_agreement_distribution": distribution(rounds),
                "support_diagnostics": {
                    "status": "COLLECTED_WHERE_AVAILABLE_WITHOUT_AFFECTING_ASSIGNMENT",
                    "pooled_negotiation_policy_active": False,
                },
            }
        )
    elif family == "bargaining":
        normalized_shares = []
        for row in outcome_rows:
            if row["raw_payoff"] is None:
                continue
            config = json.loads(row["exact_configuration"])
            money = config.get("money_to_divide")
            if isinstance(money, (int, float)) and float(money) > 0:
                normalized_shares.append(float(row["raw_payoff"]) / float(money))
        n_terminal = len(outcome_rows)
        family_specific.update(
            {
                "agreement_rate": sum("agreement" in str(row["terminal_outcome"]) for row in outcome_rows) / n_terminal if n_terminal else None,
                "walkaway_or_no_deal_rate": sum(
                    "walk" in str(row["terminal_outcome"])
                    or str(row["terminal_outcome"]) in {"no_deal", "no-deal", "timeout"}
                    for row in outcome_rows
                ) / n_terminal if n_terminal else None,
                "normalized_own_share": distribution(normalized_shares),
            }
        )
    elif family == "persuasion":
        seller_rows = [row for row in outcome_rows if row["role"] == "seller"]
        buyer_rows = [row for row in outcome_rows if row["role"] == "buyer"]
        seller_values = [float(row["raw_payoff"]) for row in seller_rows if row["raw_payoff"] is not None]
        buyer_values = [float(row["raw_payoff"]) for row in buyer_rows if row["raw_payoff"] is not None]
        family_specific.update(
            {
                "seller_zero_payoff_rate": sum(value == 0 for value in seller_values) / len(seller_values) if seller_values else None,
                "buyer_negative_payoff_rate": sum(value < 0 for value in buyer_values) / len(buyer_values) if buyer_values else None,
                "buyer_zero_payoff_rate": sum(value == 0 for value in buyer_values) / len(buyer_values) if buyer_values else None,
                "seller_payoff_distribution": distribution(seller_values, bad_count=sum(value <= 0 for value in seller_values)),
                "buyer_payoff_distribution": distribution(buyer_values, bad_count=sum(value <= 0 for value in buyer_values)),
            }
        )
    return {
        "generated_at": _now(),
        "inspection_is_read_only": True,
        "cohort_id": COHORT_ID,
        "family": family,
        "checkpoint": checkpoint,
        "target_completed": FAMILY_CAP,
        "completed_games": counts["completed"],
        "active_games": (stats or {}).get("active_games"),
        "pending_games": (stats or {}).get("pending_games"),
        "randomized_experimental_games": randomized,
        "observational_games": observational,
        "excluded_experimental_observations": excluded,
        "current_rating": current_rating,
        "start_rating": start_rating,
        "rating_change": (
            float(current_rating) - float(start_rating)
            if current_rating is not None and start_rating is not None else None
        ),
        "operational": _operational(events),
        "structural_cell_counts": dict(structural),
        "opponent_category_diagnostics": opponents,
        "family_specific_diagnostics": family_specific,
        "experiments": experiments,
    }


def write_family_dashboard(
    store: CohortStore,
    *,
    family: str,
    output_dir: Path,
    stats: Mapping[str, Any] | None,
    log_path: Path | None,
    checkpoint: int | None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"checkpoint_{checkpoint}" if checkpoint is not None else "final"
    path = output_dir / f"{family}_{suffix}.json"
    payload = family_dashboard(
        store, family=family, stats=stats, log_path=log_path, checkpoint=checkpoint
    )
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def preflight_payload(*, frozen_commit: str, prior_bargaining: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": _now(),
        "cohort_id": COHORT_ID,
        "frozen_commit": frozen_commit,
        "registry_hash": registry_hash(),
        "registry": registry_payload(),
        "reporting_checkpoints": list(REPORTING_CHECKPOINTS),
        "bad_outcome_definitions": BAD_OUTCOME_DEFINITIONS,
        "experiments": [
            {
                **spec.structured(),
                "eligible_structural_cells": (
                    "incomplete negotiation, finite multi-round or unknown horizon"
                    if spec.experiment_id.endswith("NEG_INCOMPLETE_IBO_VS_ROBUST")
                    else "complete negotiation with finite, mathematically defined extraction"
                    if spec.experiment_id.endswith("NEG_COMPLETE_FAIRNESS_MARGIN_VS_THEORY")
                    else "complete-information bargaining"
                    if spec.experiment_id.endswith("BARG_COMPLETE_FAIRNESS_VS_THEORY")
                    else "persuasion buyer states with visible p,v,u,price,total_rounds"
                    if spec.experiment_id.endswith("PERS_BUY_MARGIN_VS_THEORY")
                    else "persuasion seller states with visible p,v,u,positive price,total_rounds"
                ),
                "bad_outcome_definition": (
                    BAD_OUTCOME_DEFINITIONS.get(spec.family)
                    or BAD_OUTCOME_DEFINITIONS[f"{spec.family}:buyer"]
                    + "; "
                    + BAD_OUTCOME_DEFINITIONS[f"{spec.family}:seller"]
                ),
                "current_status": spec.initial_status,
            }
            for spec in experiment_registry()
        ],
        "prior_bargaining_200": {
            "cohort_id": prior_bargaining.get("cohort_id"),
            "randomized_eligible_count": 0,
            "observational_count": prior_bargaining.get("unique_tracked_games", 200),
            "excluded_count": prior_bargaining.get("missing_terminal_traces", 1),
            "reason": "ordinary nonrandom production play; no pre-treatment randomized assignment",
        },
    }


def write_preflight_markdown(payload: Mapping[str, Any], path: Path) -> None:
    rows = []
    details = []
    for item in payload["experiments"]:
        rows.append(
            "| `{experiment_id}` | {stage} | {priority} | `{control_policy}` | `{challenger_policy}` | "
            "{assignment_probability:.1f} | {alpha_family:.3f}/{alpha_test:.3f} | {multiplicity} | "
            "{promotion_threshold:.0f} | {delta_min:.2f} | {current_status} |".format(**item)
        )
        details.append(
            f"- `{item['experiment_id']}`: eligible={item['eligible_structural_cells']}; "
            f"payoff transform=`{item['payoff_transform_version']}`; "
            f"BAD_OUTCOME={item['bad_outcome_definition']}."
        )
    prior = payload["prior_bargaining_200"]
    text = "\n".join(
        [
            "# POST_RISK_FIX_RANDOMIZED_3000 preflight",
            "",
            f"Frozen registry hash: `{payload['registry_hash']}`.",
            "",
            "| Experiment | Stage | Priority | Control | Challenger | P(challenger) | alpha family/test | M | Threshold | delta | Status |",
            "|---|---|---:|---|---|---:|---:|---:|---:|---:|---|",
            *rows,
            "",
            "## Eligibility, payoff transforms, and bad events",
            "",
            *details,
            "",
            "Every exploration/confirmation assignment is a fresh 50/50 draw persisted before the first treatment-dependent action. Confirmation rows are predeclared `NOT_STARTED`, use fresh games and M=1, and activate only after the corresponding exploration becomes `PROMOTION_CANDIDATE`.",
            "",
            "## Prior bargaining cohort",
            "",
            f"`{prior['cohort_id']}` contributes randomized={prior['randomized_eligible_count']}, observational={prior['observational_count']}, excluded={prior['excluded_count']}. It is not promotion evidence because no pre-treatment randomized assignment existed.",
            "",
            "## Locked safety and reporting",
            "",
            "A challenger safety-pauses if its first five valid challenger outcomes are all bad, or once n_challenger>=8 when its bad-outcome rate is strictly above 0.75. Integrity failures pause immediately. Family execution nevertheless continues observationally or through another unresolved experiment to exactly 1,000 completed games. Checkpoints at 200/500/750 are read-only.",
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def combined_final_payload(
    store: CohortStore,
    *,
    stats: Mapping[str, Any],
    log_paths: Mapping[str, Path],
) -> dict[str, Any]:
    families = {
        family: family_dashboard(
            store, family=family, stats=stats, log_path=log_paths.get(family)
        )
        for family in ("bargaining", "negotiation", "persuasion")
    }
    snapshot = store.snapshot()
    experiments = {item["experiment_id"]: item for item in snapshot["experiments"]}
    production_map: dict[str, str] = {}
    formal_evidence: dict[str, Any] = {}
    for spec in experiment_registry():
        if spec.stage != "exploration":
            continue
        confirmation = experiments[confirmation_id := f"CONFIRM_{spec.experiment_id}"]
        selected = (
            spec.challenger_policy
            if confirmation["status"] == "PROMOTE"
            else spec.control_policy
        )
        production_map[spec.experiment_id] = selected
        formal_evidence[spec.experiment_id] = {
            "exploration_status": experiments[spec.experiment_id]["status"],
            "confirmation_experiment_id": confirmation_id,
            "confirmation_status": confirmation["status"],
            "formally_promoted": confirmation["status"] == "PROMOTE",
        }
    total_randomized = sum(item["randomized_experimental_games"] for item in families.values())
    total_observational = sum(item["observational_games"] for item in families.values())
    total_excluded = sum(item["excluded_experimental_observations"] for item in families.values())
    replays = {
        spec.experiment_id: store.replay_experiment(spec.experiment_id)
        for spec in experiment_registry()
    }
    integrity = {
        experiment_id: (
            math.isclose(replay["E_t"], experiments[experiment_id]["E_t"], rel_tol=1e-12)
            and math.isclose(
                replay["E_t_prime"], experiments[experiment_id]["E_t_prime"], rel_tol=1e-12
            )
        )
        for experiment_id, replay in replays.items()
    }
    return {
        "generated_at": _now(),
        "cohort_id": COHORT_ID,
        "total_completed_new_games": sum(item["completed_games"] for item in families.values()),
        "total_randomized_games": total_randomized,
        "total_observational_games": total_observational,
        "excluded_experimental_observations": total_excluded,
        "families": families,
        "active_games_after_shutdown": stats.get("active_games"),
        "pending_games_after_shutdown": stats.get("pending_games"),
        "evidence_store_replay": replays,
        "evidence_store_integrity": {
            "all_replays_match": all(integrity.values()),
            "by_experiment": integrity,
        },
        "recommended_production_policy_map": production_map,
        "formal_evidence": formal_evidence,
        "descriptive_only_evidence": [
            "all OBSERVATIONAL_LIVE_EVIDENCE rows",
            "opponent-category and structural-cell subgroup summaries",
            "rating changes",
            "PRE_RISK_FIX_BARGAINING_200",
            "incomplete T=1 negotiation",
            "incomplete-information bargaining",
        ],
        "remaining_weak_configurations": [
            "incomplete T=1 negotiation: no separately validated challenger",
            "incomplete-information bargaining: no instance-conditioned challenger",
            "negotiation pooled empirical/risk-sensitive selector: paused",
            "persuasion P3: population trust artifact unavailable",
        ],
        "post_cohort_execution": "STOP_AND_WAIT_FOR_HUMAN_REVIEW",
    }

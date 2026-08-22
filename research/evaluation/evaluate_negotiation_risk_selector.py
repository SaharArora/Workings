"""Fresh-to-selector diagnostics for continuation-aware negotiation decisions.

The frozen response artifact has already consumed every public negotiation game in
train/validation/test.  This evaluator therefore uses a new whole-game salted subset
of the old response-training split, records that dependency explicitly, and refuses
live authorization on it.  It remains useful for exercising the complete risk grid and
the hard selector-sanity stop rule without touching the consumed response test set.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from opponent_models.pooled_negotiation import (
    PooledNegotiationModel,
    economic_margin,
)
from policies.negotiation.fairness_margin import fairness_margin_price
from policies.negotiation.risk_sensitive_pooled import (
    DOMINANCE_VALUE_TOLERANCE,
    ENDPOINT_MARGIN_THRESHOLD,
    MATERIAL_ACCEPTANCE_ADVANTAGE,
    MAX_TERMINAL_ZERO_PROBABILITY,
    RiskCandidate,
    RiskParameters,
    apply_agreement_dominance,
    risk_parameter_grid,
    score_candidate,
    select_risk_candidate,
)
from research.evaluation.backtest_population_layer import (
    _candidate_prediction,
    _historical_candidates,
    _payoff,
    _split_name,
)
from theory.negotiation.baselines import complete_information_price

SELECTOR_HOLDOUT_SALT = "negotiation-risk-selector-v1"
SELECTOR_HOLDOUT_BUCKETS = 5
SELECTOR_HOLDOUT_BUCKET = 0
MIN_PERCENTILE_REFERENCE_GAMES = 200
SCORING_DIVERGENCE_THRESHOLD = 0.20
EXPECTED_PAYOFF_TOLERANCE_FROM_BEST = 0.05
ENDPOINT_ABSOLUTE_CEILING = 0.25
ENDPOINT_RELATIVE_REDUCTION = 0.50


@dataclass(frozen=True, slots=True)
class CandidateInputs:
    price: float
    sources: tuple[str, ...]
    q_accept: float
    acceptance_payoff: float
    continuation_target: float
    continuation_target_payoff: float
    q_next: float


@dataclass(frozen=True, slots=True)
class PreparedState:
    decision_id: str
    game_id: str
    role: str
    structural_group: str
    horizon_class: str
    own_value: float
    observed_price: float
    observed_accepted: int
    observed_game_payoff: float
    robust_price: float
    adaptive_price: float
    fairness_price: float | None
    theory_price: float | None
    old_price: float
    terminal_after_nonaccept: bool
    percentile_reference_group: str
    candidates: tuple[CandidateInputs, ...]
    ood_candidate_exclusions: int


def _selector_holdout_game(game_id: str) -> bool:
    if _split_name(game_id) != "train":
        return False
    digest = hashlib.sha256(
        f"{SELECTOR_HOLDOUT_SALT}|{game_id}".encode("utf-8")
    ).hexdigest()
    return int(digest[:8], 16) % SELECTOR_HOLDOUT_BUCKETS == SELECTOR_HOLDOUT_BUCKET


def _group_without_opponent(structural_group: str) -> str:
    return "|".join(structural_group.split("|")[:3])


def _has_next_own_opportunity(row: Mapping[str, Any]) -> bool:
    if not bool(row["horizon_known"]):
        return True
    maximum = row.get("max_rounds")
    return isinstance(maximum, int) and int(row["round_number"]) + 2 <= maximum


def _price_from_margin(role: str, own: float, scale: float, margin: float) -> float:
    return own + margin * scale if role == "seller" else own - margin * scale


def _candidate_sources(
    row: Mapping[str, Any],
    *,
    seller_value: float | None,
    buyer_value: float | None,
) -> tuple[float, float, float | None, float | None, dict[float, set[str]]]:
    role = str(row["role"])
    own = float(row["own_value"])
    scale = float(row["scale"])
    robust, adaptive, _ = _historical_candidates(row)
    candidates: dict[float, set[str]] = {}

    def add(value: float | None, source: str) -> None:
        if value is None or not math.isfinite(value):
            return
        price = round(float(value), 10)
        ir = price >= own if role == "seller" else 0 <= price <= own
        if ir:
            candidates.setdefault(price, set()).add(source)

    add(robust, "ROBUST")
    add(adaptive, "ADAPTIVE_FIXED")
    grid = (
        (1.0, 1.1, 1.25, 1.5, 2.0)
        if role == "seller"
        else (0.0, 0.25, 0.5, 0.75, 1.0)
    )
    for fraction in grid:
        add(own * fraction, "OWN_VALUE_NORMALIZED_GRID")
    features = row["feature_map"]
    if float(features["prior_offer_count_scaled"]) > 0:
        recent = _price_from_margin(
            role, own, scale, float(features["last_opponent_margin"])
        )
        best = _price_from_margin(
            role, own, scale, float(features["best_opponent_margin"])
        )
        add(recent, "RECENT_OPPONENT_OFFER")
        add(best, "BEST_OPPONENT_OFFER")
        add((robust + best) / 2.0, "ROBUST_BEST_OPPONENT_MIDPOINT")
    theory: float | None = None
    fairness: float | None = None
    if (
        bool(row["complete_information"])
        and seller_value is not None
        and buyer_value is not None
    ):
        maximum = int(row["max_rounds"]) if row["horizon_known"] else None
        theory = complete_information_price(
            seller_value, buyer_value, max_rounds=maximum
        )
        if theory is not None:
            add(theory, "THEORY_BASELINE")
            extractor = "seller" if math.isclose(theory, buyer_value) else "buyer"
            fairness = fairness_margin_price(
                seller_value, buyer_value, extractor=extractor
            )
            add(fairness, "COMPLETE_INFORMATION_FAIRNESS_MARGIN")
    return robust, adaptive, fairness, theory, candidates


def _next_features(
    row: Mapping[str, Any], *, current_price: float, target_price: float
) -> dict[str, float]:
    role = str(row["role"])
    own = float(row["own_value"])
    scale = float(row["scale"])
    features = {name: float(value) for name, value in row["feature_map"].items()}
    current_round = int(row["round_number"]) + 2
    features["round_scaled"] = math.log1p(min(current_round, 100)) / math.log(101)
    if row["horizon_known"] and isinstance(row.get("max_rounds"), int):
        features["round_fraction"] = min(current_round / int(row["max_rounds"]), 1.0)
    old_count = round(math.exp(features["prior_offer_count_scaled"] * math.log(101)) - 1)
    features["prior_offer_count_scaled"] = (
        math.log1p(min(old_count + 1, 100)) / math.log(101)
    )
    features["proposal_margin"] = economic_margin(role, target_price, own)
    features["previous_own_margin"] = economic_margin(role, current_price, own)
    features["own_concession"] = (
        max(0.0, current_price - target_price) / scale
        if role == "seller"
        else max(0.0, target_price - current_price) / scale
    )
    features["repeated_counters_scaled"] = (
        0.1 if math.isclose(current_price, target_price) else 0.0
    )
    return features


def _old_selection(
    row: Mapping[str, Any],
    *,
    robust: float,
    supported: Mapping[float, tuple[float, float]],
) -> float:
    role = str(row["role"])
    continuation = 0.0
    if float(row["feature_map"]["prior_offer_count_scaled"]) > 0 and robust in supported:
        robust_q, robust_payoff = supported[robust]
        continuation = 0.25 * robust_q * robust_payoff

    def score(price: float) -> float:
        probability, payoff = supported[price]
        return probability * payoff + (1.0 - probability) * continuation

    return max(
        supported,
        key=(
            (lambda price: (score(price), -price))
            if role == "seller"
            else (lambda price: (score(price), price))
        ),
    )


def _game_records(
    feature_table: Path,
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, set[str]],
]:
    holdout: list[dict[str, Any]] = []
    games: dict[str, dict[str, Any]] = {}
    opponents: dict[str, set[str]] = defaultdict(set)
    with feature_table.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            game_id = str(row["game_id"])
            split = _split_name(game_id)
            opponents[split].add(str(row["opponent_model"]))
            if _selector_holdout_game(game_id):
                holdout.append(row)
            game = games.setdefault(
                game_id,
                {
                    "values": {},
                    "groups": {},
                    "accepted_price": None,
                },
            )
            role = str(row["role"])
            game["values"][role] = float(row["own_value"])
            game["groups"][role] = str(row["structural_group"])
            if int(row["accepted"]):
                game["accepted_price"] = float(row["price"])
    return holdout, games, opponents


def _historical_outcomes(
    games: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[tuple[str, str], float], dict[str, list[float]]]:
    by_game_role: dict[tuple[str, str], float] = {}
    references: dict[str, list[float]] = defaultdict(list)
    for game_id, game in games.items():
        price = game["accepted_price"]
        for role, own in game["values"].items():
            payoff = 0.0 if price is None else _payoff(role, own, float(price))
            by_game_role[(game_id, role)] = payoff
            group = str(game["groups"][role])
            references[group].append(payoff)
            references[_group_without_opponent(group)].append(payoff)
            references[role].append(payoff)
    for values in references.values():
        values.sort()
    return by_game_role, references


def _reference_group(
    structural_group: str, references: Mapping[str, Sequence[float]]
) -> str:
    for group in (
        structural_group,
        _group_without_opponent(structural_group),
        structural_group.split("|", 1)[0],
    ):
        if len(references.get(group, ())) >= MIN_PERCENTILE_REFERENCE_GAMES:
            return group
    return structural_group.split("|", 1)[0]


def _percentile(value: float, reference: Sequence[float]) -> float:
    return bisect.bisect_right(reference, value) / len(reference)


def prepare_states(
    feature_table: Path, model: PooledNegotiationModel
) -> tuple[list[PreparedState], dict[str, Any], dict[str, list[float]]]:
    holdout, games, opponents = _game_records(feature_table)
    outcomes, references = _historical_outcomes(games)
    prepared: list[PreparedState] = []
    for row in holdout:
        game = games[str(row["game_id"])]
        seller = game["values"].get("seller")
        buyer = game["values"].get("buyer")
        robust, adaptive, fairness, theory, raw = _candidate_sources(
            row, seller_value=seller, buyer_value=buyer
        )
        supported: dict[float, tuple[float, float]] = {}
        current_predictions: dict[float, tuple[float, tuple[str, ...]]] = {}
        for price in raw:
            probability, _, clipped = _candidate_prediction(model, row, price)
            current_predictions[price] = (probability, clipped)
            if not clipped:
                supported[price] = (
                    probability,
                    _payoff(str(row["role"]), float(row["own_value"]), price),
                )
        if robust not in supported or not supported:
            continue
        candidates: list[CandidateInputs] = []
        for price, (probability, payoff) in supported.items():
            next_features = _next_features(
                row, current_price=price, target_price=robust
            )
            q_next, next_clipped = model.predict_acceptance(
                role=str(row["role"]), features=next_features
            )
            if next_clipped:
                continue
            candidates.append(
                CandidateInputs(
                    price=price,
                    sources=tuple(sorted(raw[price])),
                    q_accept=probability,
                    acceptance_payoff=payoff,
                    continuation_target=robust,
                    continuation_target_payoff=supported[robust][1],
                    q_next=q_next,
                )
            )
        if not candidates:
            continue
        old_supported = {
            candidate.price: (candidate.q_accept, candidate.acceptance_payoff)
            for candidate in candidates
        }
        if robust not in old_supported:
            continue
        group = str(row["structural_group"])
        prepared.append(
            PreparedState(
                decision_id=str(row["decision_id"]),
                game_id=str(row["game_id"]),
                role=str(row["role"]),
                structural_group=group,
                horizon_class=("known" if row["horizon_known"] else "unknown"),
                own_value=float(row["own_value"]),
                observed_price=float(row["price"]),
                observed_accepted=int(row["accepted"]),
                observed_game_payoff=outcomes[(str(row["game_id"]), str(row["role"]))],
                robust_price=robust,
                adaptive_price=adaptive,
                fairness_price=fairness,
                theory_price=theory,
                old_price=_old_selection(
                    row, robust=robust, supported=old_supported
                ),
                terminal_after_nonaccept=not _has_next_own_opportunity(row),
                percentile_reference_group=_reference_group(group, references),
                candidates=tuple(sorted(candidates, key=lambda item: item.price)),
                ood_candidate_exclusions=len(raw) - len(candidates),
            )
        )
    holdout_games = {str(row["game_id"]) for row in holdout}
    holdout_opponents = {str(row["opponent_model"]) for row in holdout}
    distribution = {
        "status": "FRESH_TO_SELECTOR_ONLY_RESPONSE_FIT_OVERLAP",
        "statistically_independent_of_response_fit": False,
        "live_authorization_requirement_satisfied": False,
        "reason": (
            "All public games at authoritative source commit 68a33e98 were already used "
            "by response-model train/calibration/test. The public HEAD is unchanged; "
            "retraining was forbidden absent a model defect."
        ),
        "construction": (
            "old response-training games only; sha256('negotiation-risk-selector-v1'|"
            "game_id) mod 5 == 0; whole games"
        ),
        "games_before_support_filter": len(holdout_games),
        "rows_before_support_filter": len(holdout),
        "games_evaluated": len({state.game_id for state in prepared}),
        "rows_evaluated": len(prepared),
        "roles": dict(sorted(Counter(state.role for state in prepared).items())),
        "structural_groups": dict(
            sorted(Counter(state.structural_group for state in prepared).items())
        ),
        "opponent_model_count": len(holdout_opponents),
        "opponent_overlap": {
            split: len(holdout_opponents & values)
            for split, values in sorted(opponents.items())
        },
        "opponent_overlap_note": (
            "The dense public cross-play graph reuses model identities in every split; "
            "identity is not a response-model feature."
        ),
    }
    return prepared, distribution, references


def _scored_candidates(
    state: PreparedState, parameters: RiskParameters
) -> tuple[RiskCandidate, ...]:
    return apply_agreement_dominance(
        tuple(
            score_candidate(
                price=item.price,
                source=item.sources,
                own_value=state.own_value,
                q_accept=item.q_accept,
                acceptance_payoff=item.acceptance_payoff,
                continuation_target=item.continuation_target,
                continuation_target_payoff=item.continuation_target_payoff,
                q_next_opportunity_accept=item.q_next,
                terminal=state.terminal_after_nonaccept,
                parameters=parameters,
            )
            for item in state.candidates
        )
    )


def _same(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and math.isclose(left, right)


def _more_agreement(role: str, left: float, right: float) -> bool:
    return left < right if role == "seller" else left > right


def _metric_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    selected = [row for row in rows if row.get("selected")]
    fairness_selected = [row for row in selected if row["fairness_available"]]
    count = len(rows)

    def values(name: str) -> list[float]:
        return [float(row[name]) for row in selected]

    return {
        "n": count,
        "selected_n": len(selected),
        "selection_unavailable_rate": (count - len(selected)) / count if count else None,
        "mean_expected_Q_Y": statistics.fmean(values("expected_y")) if selected else None,
        "median_expected_Q_Y": statistics.median(values("expected_y")) if selected else None,
        "mean_expected_raw_payoff": statistics.fmean(values("expected_raw")) if selected else None,
        "mean_cvar_penalty": statistics.fmean(values("cvar_penalty")) if selected else None,
        "mean_risk_adjusted_value": statistics.fmean(values("risk_value")) if selected else None,
        "mean_percentile_proxy": statistics.fmean(values("percentile")) if selected else None,
        "mean_predicted_acceptance": statistics.fmean(values("q_accept")) if selected else None,
        "mean_terminal_zero_probability": statistics.fmean(values("zero_probability")) if selected else None,
        "chance_constraint_violation_rate": (
            sum(not row["chance_ok"] for row in selected) / len(selected)
            if selected
            else None
        ),
        "mean_immediate_acceptance_surplus": (
            statistics.fmean(values("immediate_surplus")) if selected else None
        ),
        "endpoint_extreme_action_rate": (
            sum(row["endpoint"] for row in selected) / len(selected)
            if selected
            else None
        ),
        "more_agreement_oriented_than_old_rate": (
            sum(row["more_agreement_than_old"] for row in selected) / len(selected)
            if selected
            else None
        ),
        "equal_robust_rate": (
            sum(row["equal_robust"] for row in selected) / len(selected)
            if selected
            else None
        ),
        "equal_adaptive_rate": (
            sum(row["equal_adaptive"] for row in selected) / len(selected)
            if selected
            else None
        ),
        "equal_fairness_rate": (
            sum(row["equal_fairness"] for row in fairness_selected)
            / len(fairness_selected)
            if fairness_selected
            else None
        ),
        "ood_violations": 0,
        "ood_candidate_exclusions": sum(row["ood_exclusions"] for row in rows),
        "ir_violations": 0,
    }


def evaluate_parameters(
    states: Sequence[PreparedState],
    parameters: RiskParameters,
    references: Mapping[str, Sequence[float]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for state in states:
        candidates = _scored_candidates(state, parameters)
        selected = select_risk_candidate(candidates, role=state.role)
        row: dict[str, Any] = {
            "role": state.role,
            "structural_group": state.structural_group,
            "selected": selected is not None,
            "ood_exclusions": state.ood_candidate_exclusions,
        }
        if selected is not None:
            row.update(
                {
                    "price": selected.price,
                    "expected_y": selected.expected_normalized_payoff,
                    "expected_raw": selected.expected_raw_payoff,
                    "cvar_penalty": selected.cvar_penalty,
                    "risk_value": selected.risk_adjusted_value,
                    "percentile": _percentile(
                        selected.expected_raw_payoff,
                        references[state.percentile_reference_group],
                    ),
                    "q_accept": selected.predicted_acceptance,
                    "zero_probability": selected.terminal_zero_probability,
                    "chance_ok": selected.chance_constraint_satisfied,
                    "immediate_surplus": selected.immediate_acceptance_payoff,
                    "endpoint": economic_margin(
                        state.role, selected.price, state.own_value
                    )
                    >= ENDPOINT_MARGIN_THRESHOLD,
                    "more_agreement_than_old": _more_agreement(
                        state.role, selected.price, state.old_price
                    ),
                    "equal_robust": _same(selected.price, state.robust_price),
                    "equal_adaptive": _same(selected.price, state.adaptive_price),
                    "equal_fairness": _same(selected.price, state.fairness_price),
                    "fairness_available": state.fairness_price is not None,
                }
            )
        rows.append(row)
        groups[state.structural_group].append(row)
        groups[f"{state.role}|{state.horizon_class}"].append(row)
    overall = _metric_summary(rows)
    role_metrics = {
        role: _metric_summary([row for row in rows if row["role"] == role])
        for role in ("seller", "buyer")
    }
    group_metrics = {
        name: _metric_summary(group_rows)
        for name, group_rows in sorted(groups.items())
    }
    endpoint_pass = all(
        metric["selection_unavailable_rate"] == 0
        and metric["endpoint_extreme_action_rate"] is not None
        and metric["endpoint_extreme_action_rate"] <= ENDPOINT_ABSOLUTE_CEILING
        for metric in role_metrics.values()
    )
    checks = {
        "complete_selection_coverage": overall["selection_unavailable_rate"] == 0,
        "no_ir_violations": overall["ir_violations"] == 0,
        "no_support_violations": overall["ood_violations"] == 0,
        "chance_constraint": overall["chance_constraint_violation_rate"] == 0,
        "selected_zero_probability_at_most_0_50": (
            overall["mean_terminal_zero_probability"] is not None
            and all(
                row.get("zero_probability", 1) <= MAX_TERMINAL_ZERO_PROBABILITY + 1e-12
                for row in rows
                if row.get("selected")
            )
        ),
        "endpoint_absolute_ceiling_by_role": endpoint_pass,
    }
    return {
        "parameters": parameters.structured(),
        "overall": overall,
        "roles": role_metrics,
        "groups": group_metrics,
        "sanity_checks": checks,
        "passes_selector_sanity": all(checks.values()),
    }


def _old_endpoint_rates(states: Sequence[PreparedState]) -> dict[str, float]:
    return {
        role: sum(
            economic_margin(state.role, state.old_price, state.own_value)
            >= ENDPOINT_MARGIN_THRESHOLD
            for state in states
            if state.role == role
        )
        / sum(state.role == role for state in states)
        for role in ("seller", "buyer")
    }


def _add_relative_endpoint_check(
    result: dict[str, Any], old_rates: Mapping[str, float]
) -> None:
    role_checks: dict[str, Any] = {}
    for role in ("seller", "buyer"):
        new = result["roles"][role]["endpoint_extreme_action_rate"]
        ceiling = min(
            ENDPOINT_ABSOLUTE_CEILING,
            ENDPOINT_RELATIVE_REDUCTION * old_rates[role],
        )
        role_checks[role] = {
            "old_rate": old_rates[role],
            "new_rate": new,
            "required_ceiling": ceiling,
            "passed": new is not None and new <= ceiling,
        }
    result["endpoint_reduction"] = role_checks
    result["sanity_checks"]["material_endpoint_reduction_by_role"] = all(
        value["passed"] for value in role_checks.values()
    )
    result["passes_selector_sanity"] = all(result["sanity_checks"].values())


def _control_price(state: PreparedState, policy: str) -> float | None:
    if policy == "ROBUST":
        return state.robust_price
    if policy == "ADAPTIVE_FIXED":
        return state.adaptive_price
    if policy == "FAIRNESS_MARGIN":
        return state.fairness_price
    if policy == "THEORY":
        return state.theory_price
    if policy == "OLD_POOLED_EMPIRICAL":
        return state.old_price
    raise ValueError(policy)


def _candidate_at_price(
    state: PreparedState,
    price: float,
    parameters: RiskParameters,
) -> RiskCandidate | None:
    source = next(
        (item for item in state.candidates if math.isclose(item.price, price)), None
    )
    if source is None:
        return None
    return score_candidate(
        price=source.price,
        source=source.sources,
        own_value=state.own_value,
        q_accept=source.q_accept,
        acceptance_payoff=source.acceptance_payoff,
        continuation_target=source.continuation_target,
        continuation_target_payoff=source.continuation_target_payoff,
        q_next_opportunity_accept=source.q_next,
        terminal=state.terminal_after_nonaccept,
        parameters=parameters,
    )


def control_comparison(
    states: Sequence[PreparedState],
    references: Mapping[str, Sequence[float]],
    parameters: RiskParameters,
) -> dict[str, Any]:
    policies = (
        "THEORY",
        "ROBUST",
        "ADAPTIVE_FIXED",
        "FAIRNESS_MARGIN",
        "OLD_POOLED_EMPIRICAL",
        "RISK_SENSITIVE_POOLED_EMPIRICAL",
    )
    grouped: dict[str, dict[str, list[dict[str, float]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    factual: dict[str, list[float]] = defaultdict(list)
    for state in states:
        groups = (state.structural_group, f"{state.role}|{state.horizon_class}")
        risk = select_risk_candidate(
            _scored_candidates(state, parameters), role=state.role
        )
        if risk is None:
            continue
        for group in groups:
            factual[group].append(state.observed_game_payoff)
        for policy in policies:
            candidate = (
                risk
                if policy == "RISK_SENSITIVE_POOLED_EMPIRICAL"
                else (
                    _candidate_at_price(
                        state, _control_price(state, policy), parameters
                    )
                    if _control_price(state, policy) is not None
                    else None
                )
            )
            if candidate is None:
                continue
            proxy = _percentile(
                candidate.expected_raw_payoff,
                references[state.percentile_reference_group],
            )
            record = {
                "raw": candidate.expected_raw_payoff,
                "normalized": candidate.expected_normalized_payoff,
                "risk": candidate.risk_adjusted_value,
                "percentile": proxy,
                "q_accept": candidate.predicted_acceptance,
                "zero_probability": candidate.terminal_zero_probability,
            }
            for group in groups:
                grouped[group][policy].append(record)
    output: dict[str, Any] = {}
    for group, policy_rows in sorted(grouped.items()):
        policies_out: dict[str, Any] = {}
        for policy, rows in sorted(policy_rows.items()):
            policies_out[policy] = {
                "n": len(rows),
                **{
                    f"mean_{name}": statistics.fmean(row[name] for row in rows)
                    for name in (
                        "raw",
                        "normalized",
                        "risk",
                        "percentile",
                        "q_accept",
                        "zero_probability",
                    )
                },
            }
        rankings = {
            metric: [
                policy
                for policy, _ in sorted(
                    policies_out.items(),
                    key=lambda item: item[1][f"mean_{metric}"],
                    reverse=True,
                )
            ]
            for metric in ("raw", "normalized", "risk", "percentile")
        }
        output[group] = {
            "policies": policies_out,
            "rankings": rankings,
            "actual_realized_outcome_note": (
                "Historical game payoff is factual; every named policy metric is a "
                "response/continuation-model counterfactual estimate."
            ),
            "actual_realized_mean_payoff": (
                statistics.fmean(factual[group]) if factual.get(group) else None
            ),
        }
    return output


def scoring_divergence(comparison: Mapping[str, Any]) -> dict[str, Any]:
    metrics = ("raw", "normalized", "risk", "percentile")
    disagreements = 0
    comparisons = 0
    by_pair: Counter[str] = Counter()
    by_pair_n: Counter[str] = Counter()
    for group in comparison.values():
        rankings = group["rankings"]
        for left_index, left_metric in enumerate(metrics):
            for right_metric in metrics[left_index + 1 :]:
                common = set(rankings[left_metric]) & set(rankings[right_metric])
                left_positions = {
                    policy: index
                    for index, policy in enumerate(rankings[left_metric])
                    if policy in common
                }
                right_positions = {
                    policy: index
                    for index, policy in enumerate(rankings[right_metric])
                    if policy in common
                }
                policies = sorted(common)
                key = f"{left_metric}_vs_{right_metric}"
                for i, first in enumerate(policies):
                    for second in policies[i + 1 :]:
                        disagrees = (
                            left_positions[first] < left_positions[second]
                        ) != (right_positions[first] < right_positions[second])
                        disagreements += disagrees
                        comparisons += 1
                        by_pair[key] += disagrees
                        by_pair_n[key] += 1
    rate = disagreements / comparisons if comparisons else 0.0
    return {
        "criterion": f"aggregate pairwise rank disagreement > {SCORING_DIVERGENCE_THRESHOLD}",
        "pairwise_comparisons": comparisons,
        "disagreements": disagreements,
        "disagreement_rate": rate,
        "by_objective_pair": {
            key: {
                "n": by_pair_n[key],
                "disagreements": by_pair[key],
                "rate": by_pair[key] / by_pair_n[key],
            }
            for key in sorted(by_pair_n)
        },
        "SCORING_OBJECTIVE_DIVERGENCE": rate > SCORING_DIVERGENCE_THRESHOLD,
        "official_rating_claimed": False,
    }


def _diagnostic_choice(results: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return max(
        results,
        key=lambda row: (
            -float(row["overall"]["selection_unavailable_rate"]),
            float(row["overall"]["mean_risk_adjusted_value"] or -math.inf),
        ),
    )


def evaluate(feature_table: Path, artifact: Path) -> dict[str, Any]:
    model = PooledNegotiationModel.load(artifact)
    states, holdout, references = prepare_states(feature_table, model)
    if not states:
        raise ValueError("fresh-to-selector diagnostic contains no supported states")
    old_endpoint = _old_endpoint_rates(states)
    grid_results: list[dict[str, Any]] = []
    for parameters in risk_parameter_grid():
        result = evaluate_parameters(states, parameters, references)
        _add_relative_endpoint_check(result, old_endpoint)
        grid_results.append(result)
    selector_feasible = [row for row in grid_results if row["passes_selector_sanity"]]
    expected_best = max(
        (
            float(row["overall"]["mean_expected_raw_payoff"])
            for row in selector_feasible
        ),
        default=None,
    )
    eligible_by_payoff = [
        row
        for row in selector_feasible
        if expected_best is not None
        and float(row["overall"]["mean_expected_raw_payoff"])
        >= (1.0 - EXPECTED_PAYOFF_TOLERANCE_FROM_BEST) * expected_best
    ]
    percentile_proxy_reliable = all(
        len(references[state.percentile_reference_group])
        >= MIN_PERCENTILE_REFERENCE_GAMES
        for state in states
    )
    selector_choice = (
        max(
            eligible_by_payoff,
            key=(
                (lambda row: float(row["overall"]["mean_percentile_proxy"]))
                if percentile_proxy_reliable
                else (lambda row: float(row["overall"]["mean_risk_adjusted_value"]))
            ),
        )
        if eligible_by_payoff
        else None
    )
    diagnostic = _diagnostic_choice(grid_results)
    diagnostic_parameters = RiskParameters(
        risk_lambda=float(diagnostic["parameters"]["lambda"]),
        cvar_alpha=float(diagnostic["parameters"]["alpha"]),
        epsilon=float(diagnostic["parameters"]["epsilon"]),
    )
    comparisons = control_comparison(states, references, diagnostic_parameters)
    divergence = scoring_divergence(comparisons)
    live_pass = selector_choice is not None and holdout[
        "live_authorization_requirement_satisfied"
    ]
    return {
        "response_model": {
            "version": model.model_version,
            "artifact": str(artifact),
            "retrained": False,
            "coefficients_changed": False,
            "features_changed": False,
            "calibration_changed": False,
        },
        "objective": {
            "raw_distribution": (
                "ACCEPT:q,U_accept; NONACCEPT_CONTINUE:(1-q)*0.25*q_next,U_robust; "
                "TERMINAL_NONAGREEMENT:remaining_probability,0"
            ),
            "optimization_distribution": "branch raw payoffs transformed to negotiation Y",
            "loss": "L=-Y; CVaR_alpha is mean of largest losses over worst 1-alpha mass",
            "chance_constraint": "P(Y<0.50)<=epsilon",
            "zero_constraint": "P(raw Q<=0)<=0.50",
            "dominance": (
                f"remove A when B risk value >= A-{DOMINANCE_VALUE_TOLERANCE} and "
                f"q_accept(B)>=q_accept(A)+{MATERIAL_ACCEPTANCE_ADVANTAGE}"
            ),
        },
        "holdout": holdout,
        "old_endpoint_rates": old_endpoint,
        "grid": grid_results,
        "selector_sanity_feasible_combinations": len(selector_feasible),
        "parameter_selection_rule": (
            "best fresh-to-selector mean percentile proxy among sanity-feasible "
            "combinations within 5% of best expected raw payoff"
            if percentile_proxy_reliable
            else "best risk-adjusted Q subject to selector sanity"
        ),
        "percentile_proxy_reliable_for_selection": percentile_proxy_reliable,
        "selected_parameters": selector_choice["parameters"] if selector_choice else None,
        "diagnostic_best_parameters_not_authorized": diagnostic["parameters"],
        "control_comparison": comparisons,
        "scoring_objective_divergence": divergence,
        "offline_pass": live_pass,
        "competition_cycle_status": (
            "RISK_SENSITIVE_POOLED_EMPIRICAL_ELIGIBLE_FOR_BOUNDED_VALIDATION"
            if live_pass
            else "POOLED_EMPIRICAL_PAUSED_FOR_COMPETITION_CYCLE"
        ),
        "hard_stop_reasons": [
            reason
            for condition, reason in (
                (
                    selector_choice is None,
                    "NO_GRID_COMBINATION_PASSED_SELECTOR_SANITY",
                ),
                (
                    not holdout["live_authorization_requirement_satisfied"],
                    "NO_GENUINELY_FRESH_RESPONSE_INDEPENDENT_HOLDOUT",
                ),
            )
            if condition
        ],
        "counterfactual_warning": (
            "Named-policy values use the frozen response and explicit continuation models; "
            "only historical observed game outcomes are factual."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("feature_table", type=Path)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = evaluate(args.feature_table, args.artifact)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()

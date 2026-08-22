"""Offline diagnostics for the pooled population layer and secondary families."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from opponent_models.pooled_negotiation import (
    PooledNegotiationModel,
    economic_margin,
)
from opponent_models.pooled_persuasion import PooledPersuasionModel
from policies.negotiation.adaptive import adaptive_action_plan
from policies.negotiation.pooled_empirical import (
    PooledFeatureSupportUnavailable,
    pooled_empirical_action_plan,
)
from policies.negotiation.robust import robust_action_plan


def _split_name(game_id: str) -> str:
    bucket = int(hashlib.sha256(game_id.encode("utf-8")).hexdigest()[:8], 16) % 10
    return "train" if bucket < 6 else "validation" if bucket < 8 else "test"


def _payoff(role: str, own_value: float, price: float) -> float:
    return max(0.0, price - own_value) if role == "seller" else max(0.0, own_value - price)


def _candidate_prediction(
    model: PooledNegotiationModel,
    row: Mapping[str, Any],
    price: float,
) -> tuple[float, float, tuple[str, ...]]:
    role = str(row["role"])
    own = float(row["own_value"])
    scale = float(row["scale"])
    features = dict(row["feature_map"])
    features["proposal_margin"] = economic_margin(role, price, own)
    previous_margin = float(features["previous_own_margin"])
    previous_price = own + previous_margin * scale if role == "seller" else own - previous_margin * scale
    features["own_concession"] = (
        max(0.0, previous_price - price) / scale
        if role == "seller"
        else max(0.0, price - previous_price) / scale
    )
    features["repeated_counters_scaled"] = (
        0.1 if math.isclose(previous_price, price, rel_tol=1e-9, abs_tol=1e-9) else 0.0
    )
    probability, clipped = model.predict_acceptance(role=role, features=features)
    return probability, probability * _payoff(role, own, price), clipped


def _historical_candidates(row: Mapping[str, Any]) -> tuple[float, float, list[float]]:
    role = str(row["role"])
    own = float(row["own_value"])
    scale = float(row["scale"])
    features = row["feature_map"]
    robust = 1.5 * own if role == "seller" else 0.5 * own
    opponent_concession = float(features["opponent_concession_from_first"]) * scale
    adaptive = (
        max(own, robust - 0.35 * opponent_concession)
        if role == "seller"
        else min(own, robust + 0.35 * opponent_concession)
    )
    grid = (
        [own * value for value in (1.0, 1.1, 1.25, 1.5, 2.0)]
        if role == "seller"
        else [own * value for value in (0.0, 0.25, 0.5, 0.75, 1.0)]
    )
    best_margin = float(features["best_opponent_margin"])
    best_opponent = own + best_margin * scale if role == "seller" else own - best_margin * scale
    candidates = [*grid, robust, adaptive, float(row["price"])]
    if bool(features["prior_offer_count_scaled"]):
        candidates.extend((best_opponent, (robust + best_opponent) / 2))
    candidates = [
        value
        for value in candidates
        if math.isfinite(value)
        and (value >= own if role == "seller" else 0 <= value <= own)
    ]
    return robust, adaptive, sorted({round(value, 10) for value in candidates})


def historical_negotiation_diagnostic(
    feature_table: Path, model: PooledNegotiationModel
) -> dict[str, Any]:
    summaries: dict[str, Counter[str]] = defaultdict(Counter)
    values: dict[str, defaultdict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    with feature_table.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if _split_name(str(row["game_id"])) != "test":
                continue
            role = str(row["role"])
            robust, adaptive, candidates = _historical_candidates(row)
            predicted = {
                price: _candidate_prediction(model, row, price) for price in candidates
            }
            supported_candidates = [
                price
                for price in candidates
                if "proposal_margin" not in predicted[price][2]
            ]
            if not supported_candidates:
                continue
            tie = (
                (lambda price: (predicted[price][1], -price))
                if role == "seller"
                else (lambda price: (predicted[price][1], price))
            )
            pooled = max(supported_candidates, key=tie)
            observed = float(row["price"])
            accepted = int(row["accepted"])
            summary = summaries[role]
            summary["n"] += 1
            summary["pooled_differs_from_robust"] += not math.isclose(pooled, robust)
            summary["pooled_differs_from_adaptive"] += not math.isclose(pooled, adaptive)
            summary["adaptive_differs_from_robust"] += not math.isclose(adaptive, robust)
            summary["pooled_more_agreement_oriented_than_robust"] += (
                pooled < robust if role == "seller" else pooled > robust
            )
            values[role]["observed_policy_realized_payoff"].append(
                accepted * _payoff(role, float(row["own_value"]), observed)
            )
            for name, price in (("robust", robust), ("adaptive_fixed", adaptive), ("pooled", pooled)):
                probability, expected, _ = predicted[price]
                values[role][f"{name}_predicted_acceptance"].append(probability)
                values[role][f"{name}_model_estimated_payoff"].append(expected)
    result: dict[str, Any] = {}
    for role in ("seller", "buyer"):
        n = summaries[role]["n"]
        result[role] = {
            **dict(summaries[role]),
            **{
                key: statistics.fmean(items) if items else None
                for key, items in values[role].items()
            },
            "pooled_different_from_robust_rate": (
                summaries[role]["pooled_differs_from_robust"] / n if n else None
            ),
            "pooled_more_agreement_oriented_rate": (
                summaries[role]["pooled_more_agreement_oriented_than_robust"] / n
                if n
                else None
            ),
        }
    result["interpretation"] = {
        "observed_policy_realized_payoff": "fully observed historical factual outcome",
        "predicted_acceptance_and_payoff": "off-policy model estimate, not realized payoff",
        "counterfactual_payoff": "not identified from replay",
    }
    return result


def _jsonl_records(paths: Iterable[Path]) -> Iterable[tuple[Path, dict[str, Any]]]:
    for path in sorted(paths):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                yield path, json.loads(line)


def live_negotiation_diagnostic(
    evaluation_dir: Path, model: PooledNegotiationModel
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    results: dict[str, dict[str, Any]] = {}
    for _, event in _jsonl_records(evaluation_dir.glob("*negotiation*.jsonl")):
        if event.get("event") == "game_result":
            results[str(event["game_id"])] = event
        if event.get("event") != "policy_decision":
            continue
        game = {
            "game_id": event["game_id"],
            "game_family": "negotiation",
            "your_player": event["state"].get("current_player"),
            "game_state": event["state"],
            "valid_actions": event["valid_actions"],
            "opponent": event.get("opponent", {}),
        }
        try:
            robust = robust_action_plan(game).action
            adaptive = adaptive_action_plan(game).action
            pooled_plan = pooled_empirical_action_plan(game, model)
        except PooledFeatureSupportUnavailable as exc:
            rows.append(
                {
                    "game_id": event["game_id"],
                    "round": event["state"].get("round"),
                    "eligibility": "INELIGIBLE_UNSUPPORTED_FEATURES",
                    "eligibility_reason": str(exc),
                }
            )
            continue
        except Exception as exc:
            rows.append(
                {
                    "game_id": event["game_id"],
                    "round": event["state"].get("round"),
                    "diagnostic_error": f"{type(exc).__name__}:{exc}",
                }
            )
            continue
        comparable = lambda action: {
            key: action[key]
            for key in ("decision", "product_price")
            if key in action
        }
        rows.append(
            {
                "game_id": event["game_id"],
                "round": event["state"].get("round"),
                "role": pooled_plan.role,
                "observed_historical_action": comparable(event["action"]),
                "robust_action": comparable(robust),
                "adaptive_fixed_action": comparable(adaptive),
                "pooled_empirical_action": comparable(pooled_plan.action),
                "pooled_differs_from_robust": comparable(pooled_plan.action)
                != comparable(robust),
                "pooled_differs_from_adaptive": comparable(pooled_plan.action)
                != comparable(adaptive),
                "pooled_details": pooled_plan.structured(),
            }
        )
    by_game: list[dict[str, Any]] = []
    for game_id in sorted({str(row["game_id"]) for row in rows}):
        game_rows = [row for row in rows if row["game_id"] == game_id]
        result = results.get(game_id, {})
        by_game.append(
            {
                "game_id": game_id,
                "decisions": len(game_rows),
                "pooled_differs_from_robust": sum(
                    bool(row.get("pooled_differs_from_robust")) for row in game_rows
                ),
                "pooled_differs_from_adaptive": sum(
                    bool(row.get("pooled_differs_from_adaptive")) for row in game_rows
                ),
                "historical_outcome": result.get("outcome", "UNOBSERVED"),
                "historical_raw_payoff": result.get("raw_payoff"),
                "counterfactual_payoff_known": False,
            }
        )
    return {
        "decisions": rows,
        "games": by_game,
        "decision_count": len(rows),
        "pooled_differs_from_robust_count": sum(
            bool(row.get("pooled_differs_from_robust")) for row in rows
        ),
        "pooled_differs_from_adaptive_count": sum(
            bool(row.get("pooled_differs_from_adaptive")) for row in rows
        ),
        "counterfactual_warning": (
            "Live-state action replay is observable; opponent responses to changed actions are not."
        ),
    }


def bargaining_structural_diagnostic(evaluation_dir: Path) -> dict[str, Any]:
    games: dict[str, dict[str, Any]] = {}
    for _, event in _jsonl_records(evaluation_dir.glob("*bargaining*.jsonl")):
        if event.get("event") == "game_result":
            games[str(event["game_id"])] = event
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in games.values():
        config = event.get("configuration", {})
        if not bool(config.get("complete_information")):
            structural = "incomplete"
        elif bool(config.get("horizon_known")):
            structural = "complete_finite"
        else:
            structural = "complete_unlimited"
        groups[f"{structural}|{event.get('role', 'unknown')}"] .append(event)
    report: dict[str, Any] = {}
    for group, rows in sorted(groups.items()):
        normalized = [
            float(row["scale_adjusted_payoff"])
            for row in rows
            if isinstance(row.get("scale_adjusted_payoff"), (int, float))
        ]
        theory = [
            float(row["theory_reference_normalized_payoff"])
            for row in rows
            if isinstance(row.get("theory_reference_normalized_payoff"), (int, float))
        ]
        outcomes = Counter(str(row.get("outcome")) for row in rows)
        report[group] = {
            "n": len(rows),
            "agreement_rate": outcomes["agreement"] / len(rows),
            "mean_normalized_own_payoff": statistics.fmean(normalized) if normalized else None,
            "median_normalized_own_payoff": statistics.median(normalized) if normalized else None,
            "walkaway_rate": outcomes["walked_away"] / len(rows),
            "no_deal_rate": outcomes["no_deal"] / len(rows),
            "theory_reference_normalized_payoff_mean": (
                statistics.fmean(theory) if theory else None
            ),
            "outcomes": dict(outcomes),
        }
    return {
        "groups": report,
        "games": len(games),
        "recommendation": (
            "Do not globally retune FAIRNESS_CONCESSION; incomplete-information FAIRNESS "
            "is the weak observed subclass and requires targeted future work."
        ),
    }


def persuasion_challenger_diagnostic(
    feature_table: Path, model: PooledPersuasionModel
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    probabilities: dict[str, list[float]] = defaultdict(list)
    with feature_table.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if _split_name(str(row["game_id"])) != "test":
                continue
            actual = dict(row["feature_map"])
            actual_probability, _ = model.predict_purchase(actual)
            message_type = str(row["seller_message_type"])
            candidates: dict[str, dict[str, float]] = {}
            if message_type == "binary":
                for signal in ("yes", "no"):
                    features = dict(actual)
                    features.update(
                        {
                            "signal_yes": float(signal == "yes"),
                            "signal_no": float(signal == "no"),
                            "signal_text": 0.0,
                            "message_mentions_high": 0.0,
                            "message_mentions_low": 0.0,
                            "message_buy_language": 0.0,
                            "message_negation": 0.0,
                        }
                    )
                    candidates[signal] = features
                p0 = "yes"
            else:
                recommend = dict(actual)
                recommend.update(
                    {
                        "signal_yes": 0.0,
                        "signal_no": 0.0,
                        "signal_text": 1.0,
                        "message_mentions_high": 0.0,
                        "message_mentions_low": 0.0,
                        "message_buy_language": 1.0,
                        "message_negation": 0.0,
                    }
                )
                neutral = dict(recommend)
                neutral["message_buy_language"] = 0.0
                candidates = {"recommend_buy": recommend, "neutral": neutral}
                p0 = "neutral"
            scored = {
                name: model.predict_purchase(features)[0]
                for name, features in candidates.items()
            }
            chosen = max(scored, key=scored.get)  # type: ignore[arg-type]
            counts[f"n:{message_type}"] += 1
            counts[f"chosen:{message_type}:{chosen}"] += 1
            counts[f"different_from_p0:{message_type}"] += chosen != p0
            probabilities[f"actual:{message_type}"].append(actual_probability)
            probabilities[f"chosen:{message_type}"].append(scored[chosen])
    return {
        "policy": "PERSUASION_POOLED_EMPIRICAL",
        "status": "OFFLINE_CHALLENGER_NOT_LIVE_AUTHORIZED",
        "counts": dict(sorted(counts.items())),
        "mean_predicted_purchase": {
            key: statistics.fmean(values) for key, values in sorted(probabilities.items())
        },
        "p3_trust_artifact_used": False,
        "counterfactual_warning": (
            "Alternative-message purchase outcomes are model estimates, not observed counterfactuals."
        ),
    }


def run(
    feature_table: Path,
    artifact: Path,
    persuasion_feature_table: Path,
    persuasion_artifact: Path,
    evaluation_dir: Path,
) -> dict[str, Any]:
    model = PooledNegotiationModel.load(artifact)
    return {
        "negotiation_historical_test": historical_negotiation_diagnostic(
            feature_table, model
        ),
        "negotiation_recent_live_states": live_negotiation_diagnostic(
            evaluation_dir, model
        ),
        "bargaining_structural_diagnostic": bargaining_structural_diagnostic(
            evaluation_dir
        ),
        "persuasion_pooled_challenger": persuasion_challenger_diagnostic(
            persuasion_feature_table,
            PooledPersuasionModel.load(persuasion_artifact),
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("feature_table", type=Path)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("persuasion_feature_table", type=Path)
    parser.add_argument("persuasion_artifact", type=Path)
    parser.add_argument("evaluation_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = run(
        args.feature_table,
        args.artifact,
        args.persuasion_feature_table,
        args.persuasion_artifact,
        args.evaluation_dir,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()

"""Render the pre-change pooled-negotiation objective audit.

This module deliberately reproduces the selector that existed before the
continuation-aware risk work.  It must not import or approximate the replacement
objective.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from opponent_models.pooled_negotiation import PooledNegotiationModel
from policies.negotiation.pooled_empirical import POOLED_CONTINUATION_FRACTION
from research.evaluation.backtest_population_layer import (
    _candidate_prediction,
    _historical_candidates,
    _payoff,
    _split_name,
)

AUDIT_CLASSIFICATION = "CONTINUATION_TERM_PRESENT_BUT_MISSPECIFIED"


def _nonterminal(row: Mapping[str, Any]) -> bool:
    if not bool(row["horizon_known"]):
        return True
    maximum = row.get("max_rounds")
    return isinstance(maximum, int) and int(row["round_number"]) < maximum


def _action_context(row: Mapping[str, Any]) -> str:
    prior = float(row["feature_map"]["prior_offer_count_scaled"])
    if prior > 0 and _nonterminal(row):
        return "NONTERMINAL_COUNTER"
    if _nonterminal(row):
        return "NONTERMINAL_OFFER"
    return "TERMINAL_OFFER_RESPONSE_OBSERVATION"


def _stratum(row: Mapping[str, Any]) -> str:
    return "|".join(
        (
            str(row["role"]),
            "complete" if row["complete_information"] else "incomplete",
            "known" if row["horizon_known"] else "unknown",
            str(row["opponent_category"]),
            _action_context(row),
        )
    )


def _priority(row: Mapping[str, Any]) -> str:
    identity = f"{row['decision_id']}|objective-audit-v1"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def select_representative_rows(
    feature_table: Path, *, state_count: int = 20
) -> list[dict[str, Any]]:
    """Choose a deterministic, structurally diverse sample from the consumed test set."""
    strata: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with feature_table.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if _split_name(str(row["game_id"])) != "test":
                continue
            if row["opponent_category"] not in {"human", "llm"}:
                continue
            if _action_context(row) == "TERMINAL_OFFER_RESPONSE_OBSERVATION":
                continue
            strata[_stratum(row)].append(row)
    for rows in strata.values():
        rows.sort(key=_priority)
    chosen: list[dict[str, Any]] = []
    depth = 0
    while len(chosen) < state_count:
        added = False
        for name in sorted(strata):
            if depth < len(strata[name]):
                chosen.append(strata[name][depth])
                added = True
                if len(chosen) == state_count:
                    break
        if not added:
            break
        depth += 1
    if len(chosen) != state_count:
        raise ValueError(f"only {len(chosen)} representative states available")
    return chosen


def audit_state(
    row: Mapping[str, Any], model: PooledNegotiationModel
) -> dict[str, Any]:
    role = str(row["role"])
    own = float(row["own_value"])
    robust, adaptive, prices = _historical_candidates(row)
    predictions = {
        price: _candidate_prediction(model, row, price) for price in prices
    }
    supported = [
        price
        for price in prices
        if "proposal_margin" not in predictions[price][2]
    ]
    if robust not in supported:
        continuation = 0.0
    elif _action_context(row) == "NONTERMINAL_COUNTER":
        robust_q = predictions[robust][0]
        continuation = (
            POOLED_CONTINUATION_FRACTION * robust_q * _payoff(role, own, robust)
        )
    else:
        continuation = 0.0
    candidates: list[dict[str, Any]] = []
    for price in supported:
        probability = predictions[price][0]
        immediate = _payoff(role, own, price)
        rejection = (1.0 - probability) * continuation
        candidates.append(
            {
                "price": price,
                "predicted_acceptance": probability,
                "immediate_acceptance_payoff": immediate,
                "probability_nonacceptance": 1.0 - probability,
                "old_continuation_value": continuation,
                "old_rejection_contribution": rejection,
                "total_old_score": probability * immediate + rejection,
                "selected": False,
            }
        )
    tie = (
        (lambda item: (item["total_old_score"], -item["price"]))
        if role == "seller"
        else (lambda item: (item["total_old_score"], item["price"]))
    )
    selected = max(candidates, key=tie)
    selected["selected"] = True
    return {
        "decision_id": row["decision_id"],
        "game_id": row["game_id"],
        "role": role,
        "structural_group": row["structural_group"],
        "action_context": _action_context(row),
        "round_number": row["round_number"],
        "own_value": own,
        "robust_price": robust,
        "adaptive_price": adaptive,
        "selected_price": selected["price"],
        "candidates": candidates,
    }


def build_audit(
    feature_table: Path, artifact: Path, *, state_count: int = 20
) -> dict[str, Any]:
    model = PooledNegotiationModel.load(artifact)
    states = [
        audit_state(row, model)
        for row in select_representative_rows(feature_table, state_count=state_count)
    ]
    return {
        "classification": AUDIT_CLASSIFICATION,
        "response_model_version": model.model_version,
        "response_model_retrained": False,
        "sample_source": "previously consumed response-model test split",
        "sample_selection": (
            "deterministic SHA256 priority, round-robin across role/information/"
            "horizon/opponent/action-context strata"
        ),
        "state_count": len(states),
        "old_formula": {
            "score": "q_accept(a)*U_accept(a) + (1-q_accept(a))*V_old",
            "nonterminal_offer_V_old": "0",
            "nonterminal_counter_V_old": (
                "0.25*q_accept(ROBUST)*U_accept(ROBUST), constant across candidates"
            ),
            "terminal": "delegate to ROBUST IR response without candidate scoring",
        },
        "states": states,
    }


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def render_markdown(audit: Mapping[str, Any]) -> str:
    lines = [
        "# Negotiation decision-objective audit",
        "",
        "This audit was frozen before the pooled selector was modified. It uses the already-consumed response-model test split only to diagnose the old decision objective; it is not the fresh risk-selector holdout.",
        "",
        "## Exact old objective",
        "",
        "For candidate `a`, the implementation scored:",
        "",
        "```text",
        "S_old(a) = q_accept(a) * U_accept(a) + (1-q_accept(a)) * V_old",
        "",
        "V_old = 0                                      on action_type=offer",
        "V_old = 0.25*q_accept(ROBUST)*U_accept(ROBUST) on a nonterminal counter",
        "```",
        "",
        "`V_old` was constant across all candidates in a counter state. At a terminal response without a legal counter, the empirical selector did not score candidates and delegated to ROBUST's IR-safe terminal response.",
        "",
        f"**Classification: `{audit['classification']}`.** The term existed, but it was zero on genuinely nonterminal opening offers, candidate-independent on counters, did not distinguish continuation from terminal nonagreement, and provided neither a payoff distribution nor a lower-tail/no-deal calculation. It was therefore not a valid candidate-specific continuation approximation.",
        "",
        "## Representative state construction",
        "",
        f"The {audit['state_count']} states below were selected deterministically by SHA-256 priority, round-robin across role, information, known/unknown horizon, opponent category, and inferred offer/counter context. They come from the previously consumed test split and cover the old objective only.",
        "",
        "## Candidate-by-candidate decomposition",
        "",
        "| State | Cell/context | Candidate | q(accept) | Accept payoff | P(nonaccept) | Old continuation | Rejection contribution | Total old score | Selected |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for index, state in enumerate(audit["states"], start=1):
        cell = f"{state['structural_group']} / {state['action_context']}"
        for candidate in state["candidates"]:
            lines.append(
                "| {} | `{}` | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                    index,
                    cell,
                    _fmt(candidate["price"]),
                    _fmt(candidate["predicted_acceptance"]),
                    _fmt(candidate["immediate_acceptance_payoff"]),
                    _fmt(candidate["probability_nonacceptance"]),
                    _fmt(candidate["old_continuation_value"]),
                    _fmt(candidate["old_rejection_contribution"]),
                    _fmt(candidate["total_old_score"]),
                    "yes" if candidate["selected"] else "",
                )
            )
    lines.extend(
        [
            "",
            "The selected endpoint/long-shot offers are a decision-objective result. No response-model coefficient, feature, calibration parameter, or artifact version is changed by this audit.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("feature_table", type=Path)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("json_output", type=Path)
    parser.add_argument("markdown_output", type=Path)
    parser.add_argument("--state-count", type=int, default=20)
    args = parser.parse_args()
    audit = build_audit(
        args.feature_table, args.artifact, state_count=args.state_count
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(audit), encoding="utf-8")


if __name__ == "__main__":
    main()

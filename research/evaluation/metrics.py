"""Evaluation helpers that report raw and bounded transformed payoff together."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from statistics import fmean
from typing import Any


def mean_normalized_payoff(values: list[float]) -> float:
    if not values:
        raise ValueError("values are empty")
    return fmean(values)


def negotiation_efficiency(seller_value: float, buyer_value: float, traded: bool) -> bool:
    return traded is (buyer_value >= seller_value)


def payoff_report(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize both raw utility and Y so clipping cannot be hidden."""
    result: dict[str, Any] = {}
    for arm in ("incumbent", "candidate"):
        selected = [row for row in rows if row.get("assigned_arm") == arm]
        raw = [float(row["raw_payoff"]) for row in selected]
        transformed = [float(row["Y_t"]) for row in selected]
        clipped = [
            bool(row.get("payoff_transform", {}).get("clipping_occurred"))
            for row in selected
            if isinstance(row.get("payoff_transform"), Mapping)
        ]
        result[arm] = {
            "n": len(selected),
            "mean_raw_payoff": fmean(raw) if raw else None,
            "mean_bounded_payoff_Y": fmean(transformed) if transformed else None,
            "clipping_metadata_n": len(clipped),
            "clipping_observations": sum(clipped) if clipped else None,
            "clipping_rate": fmean(clipped) if clipped else None,
        }
    if result["candidate"]["n"] and result["incumbent"]["n"]:
        result["candidate_minus_incumbent"] = {
            "raw_payoff": (
                result["candidate"]["mean_raw_payoff"]
                - result["incumbent"]["mean_raw_payoff"]
            ),
            "bounded_payoff_Y": (
                result["candidate"]["mean_bounded_payoff_Y"]
                - result["incumbent"]["mean_bounded_payoff_Y"]
            ),
        }
    return result

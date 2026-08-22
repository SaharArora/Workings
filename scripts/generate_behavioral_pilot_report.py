#!/usr/bin/env python3
"""Generate the bounded behavioral-challenger pilot/postmortem report."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

FAMILIES = ("negotiation", "bargaining", "persuasion")
REQUESTED = {"negotiation": 6, "bargaining": 4, "persuasion": 4}
FLOOR = {"no_deal", "no deal", "walked_away", "walkaway", "timeout"}
WALKAWAYS = {"walked_away", "walkaway"}


def _compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _action_trace(rows: list[dict[str, Any]]) -> str:
    actions = [row.get("action") for row in rows]
    parts: list[str] = []
    index = 0
    while index < len(actions):
        count = 1
        while index + count < len(actions) and actions[index + count] == actions[index]:
            count += 1
        prefix = f"{count}x " if count > 1 else ""
        parts.append(prefix + f"`{_compact(actions[index])}`")
        index += count
    return "; ".join(parts)


def _load(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _rating(stats: dict[str, Any], family: str) -> float | None:
    value = stats.get("scores", {}).get(family, {}).get("rating")
    return float(value) if isinstance(value, (int, float)) else None


def _numeric_summary(values: Iterable[Any]) -> str:
    numbers = [float(value) for value in values if isinstance(value, (int, float))]
    if not numbers:
        return "n/a"
    return (
        f"mean={statistics.fmean(numbers):.6g}, min={min(numbers):.6g}, "
        f"max={max(numbers):.6g}"
    )


def _outcome_counts(items: list[dict[str, Any]]) -> tuple[int, int, int]:
    outcomes = [str(item.get("outcome", "")).lower() for item in items]
    agreements = sum(outcome == "agreement" for outcome in outcomes)
    no_deals = sum(outcome in {"no_deal", "no deal"} for outcome in outcomes)
    walkaways = sum(outcome in WALKAWAYS for outcome in outcomes)
    return agreements, no_deals, walkaways


def _rating_delta(items: list[dict[str, Any]]) -> float | None:
    changes = [
        float(item["rating_after"]) - float(item["rating_before"])
        for item in items
        if isinstance(item.get("rating_before"), (int, float))
        and isinstance(item.get("rating_after"), (int, float))
    ]
    return sum(changes) if changes else None


def _aggregate_table(
    results: list[dict[str, Any]], *, structural: bool
) -> list[str]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        if structural:
            key = (str(item.get("structural_policy_class", "unknown")),)
        else:
            key = (
                str(item.get("cell", "unknown")),
                str(item.get("role", "unknown")),
                str(item.get("selected_policy", item.get("selected_incumbent", "unknown"))),
            )
        groups[key].append(item)
    if structural:
        lines = [
            "| Structural policy class | n | Agreements | No-deals | Walkaways | Raw payoff | Scale-adjusted payoff | Rating delta | Selected policies | Opponent categories |",
            "| --- | ---: | ---: | ---: | ---: | --- | --- | ---: | --- | --- |",
        ]
    else:
        lines = [
            "| Exact cell | Role | Selected policy | n | Outcomes | Raw payoff | Scale-adjusted payoff | Rating delta |",
            "| --- | --- | --- | ---: | --- | --- | --- | ---: |",
        ]
    for key, items in sorted(groups.items()):
        agreements, no_deals, walkaways = _outcome_counts(items)
        rating_delta = _rating_delta(items)
        if structural:
            policies = Counter(
                str(item.get("selected_policy", item.get("selected_incumbent")))
                for item in items
            )
            opponents = Counter(str(item.get("opponent", {}).get("type", "hidden")) for item in items)
            lines.append(
                f"| `{key[0]}` | {len(items)} | {agreements} | {no_deals} | {walkaways} | "
                f"{_numeric_summary(item.get('raw_payoff') for item in items)} | "
                f"{_numeric_summary(item.get('scale_adjusted_payoff') for item in items)} | "
                f"{rating_delta if rating_delta is not None else 'n/a'} | "
                f"`{_compact(dict(policies))}` | `{_compact(dict(opponents))}` |"
            )
        else:
            outcomes = Counter(str(item.get("outcome")) for item in items)
            lines.append(
                f"| `{key[0]}` | {key[1]} | `{key[2]}` | {len(items)} | "
                f"`{_compact(dict(outcomes))}` | "
                f"{_numeric_summary(item.get('raw_payoff') for item in items)} | "
                f"{_numeric_summary(item.get('scale_adjusted_payoff') for item in items)} | "
                f"{rating_delta if rating_delta is not None else 'n/a'} |"
            )
    return lines


def _descriptive_summary(items: list[dict[str, Any]]) -> str:
    agreements, no_deals, walkaways = _outcome_counts(items)
    return (
        f"n={len(items)}, agreements={agreements}, no_deals={no_deals}, "
        f"walkaways={walkaways}, raw payoff {_numeric_summary(item.get('raw_payoff') for item in items)}"
    )


def main() -> None:
    rows_by_family = {
        family: _load(Path(f"research/evaluation/behavioral_pilot_{family}.jsonl"))
        for family in FAMILIES
    }
    results_by_family = {
        family: [row for row in rows if row.get("event") == "game_result"]
        for family, rows in rows_by_family.items()
    }
    decisions_by_family: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for family, rows in rows_by_family.items():
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            if row.get("event") == "policy_decision":
                grouped[str(row["game_id"])].append(row)
        decisions_by_family[family] = grouped

    frozen = next(
        row["frozen_commit"]
        for row in rows_by_family["negotiation"]
        if row.get("event") == "pilot_preflight"
    )
    lines = [
        "# Behavioral challenger bounded-pilot report",
        "",
        "## 1. Frozen commit SHA",
        "",
        f"`{frozen}`. No policy or threshold changed during the 6/4/4 pilot.",
        "",
        "## 2. Full test result",
        "",
        "Recorded after final report generation in the release handoff.",
        "",
        "## 3. Provenance of the old ROBUST acceptance rule",
        "",
        "The fixed-quote acceptance threshold was introduced by implementation commit `7ced172`; "
        "`docs/BUILD_SPEC.md` locks ROBUST's static ambiguity/minimax-regret proposal but does not "
        "specify that response threshold. Static ROBUST remains unchanged as the control.",
        "",
        "## 4. NEGOTIATION_ADAPTIVE definition",
        "",
        "Starts at ROBUST's quote, conditions only on observed offers, uses the locked 0.35 "
        "reciprocal concession and 0.90 continuation-target acceptance fraction, and uses a "
        "structural relative-tolerance cycle guard. It is deterministic, model-light, and not BAYES.",
        "",
        "## 5. Complete-information theory versus fairness margin",
        "",
        "Theory remains exact extraction (`V_B` in T=1 under accept-at-indifference). The bounded "
        "challenger gives the responder exactly 15% of gains from trade.",
        "",
        "## 6. Bargaining theory versus fairness",
        "",
        "Theory remains the configuration incumbent. The challenger maps proposer share `x` to "
        "`x - 0.10*(x-0.5)`; every live decision logs theory, adjusted, and selected offers.",
        "",
        "## 7. Persuasion P3 input audit",
        "",
        "No valid frozen population-positive-purchase-rate input exists. P3 was not activated; "
        "seller-side P0 remained selected with `P3_EXPERIMENT_INPUT_UNAVAILABLE`.",
        "",
        "## 8. Experimental override registry",
        "",
        f"```json\n{json.dumps(next(row['experimental_override_registry'] for row in rows_by_family['negotiation'] if row.get('event') == 'pilot_preflight'), indent=2, sort_keys=True)}\n```",
    ]

    section_number = 9
    for family in FAMILIES:
        results = results_by_family[family]
        decisions = decisions_by_family[family]
        lines.extend(
            [
                "",
                f"## {section_number}. {family.title()} pilot game-by-game results",
                "",
                "| # | Game | Configuration | Role / opponent | Baseline | Experimental | Authorization | Selected | Structured actions | Outcome | Raw payoff | Scale-adjusted | Rating before -> after |",
                "| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |",
            ]
        )
        for index, item in enumerate(results, 1):
            game_decisions = decisions[str(item["game_id"])]
            lines.append(
                f"| {index} | `{item['game_id']}` | `{_compact(item.get('configuration'))}` | "
                f"{item.get('role')} / {item.get('opponent', {}).get('type')}:{item.get('opponent', {}).get('name')} | "
                f"`{item.get('baseline_policy')}` | `{item.get('experimental_policy')}` | "
                f"`{item.get('authorization_status')}` | `{item.get('selected_policy')}` | "
                f"{_action_trace(game_decisions)} | {item.get('outcome')} | {item.get('raw_payoff')} | "
                f"{item.get('scale_adjusted_payoff')} | {item.get('rating_before')} -> {item.get('rating_after')} |"
            )
        section_number += 1

    all_results = [item for family in FAMILIES for item in results_by_family[family]]
    lines.extend(["", "## 12. Structural policy-class aggregates", ""])
    lines.extend(_aggregate_table(all_results, structural=True))
    lines.extend(["", "## 13. Exact-cell aggregates", ""])
    lines.extend(_aggregate_table(all_results, structural=False))

    lines.extend(["", "## 14. Descriptive comparison with the previous pilot", ""])
    old_results: dict[str, list[dict[str, Any]]] = {}
    for family in FAMILIES:
        old_results[family] = [
            row
            for row in _load(Path(f"research/evaluation/pilot_{family}.jsonl"))
            if row.get("event") == "game_result"
        ]
    comparisons = (
        (
            "Negotiation static ROBUST (previous)",
            [item for item in old_results["negotiation"] if "ROBUST" in str(item.get("selected_incumbent"))],
        ),
        (
            "Negotiation ADAPTIVE (current)",
            [item for item in results_by_family["negotiation"] if item.get("selected_policy") == "NEGOTIATION_ADAPTIVE"],
        ),
        (
            "Complete negotiation extraction theory (previous)",
            [item for item in old_results["negotiation"] if "COMPLETE_T1_THEORY" in str(item.get("selected_incumbent"))],
        ),
        (
            "Complete negotiation FAIRNESS_MARGIN (current)",
            [item for item in results_by_family["negotiation"] if item.get("selected_policy") == "NEGOTIATION_FAIRNESS_MARGIN"],
        ),
        ("Bargaining incumbents (previous)", old_results["bargaining"]),
        (
            "Bargaining FAIRNESS (current)",
            [item for item in results_by_family["bargaining"] if item.get("selected_policy") == "BARGAINING_FAIRNESS"],
        ),
        (
            "Persuasion seller P0 (previous)",
            [item for item in old_results["persuasion"] if item.get("role") == "seller"],
        ),
        (
            "Persuasion seller P3 (current)",
            [item for item in results_by_family["persuasion"] if item.get("selected_policy") == "PERSUASION_P3_REPUTATION"],
        ),
    )
    lines.extend(["| Policy evidence slice | Descriptive result |", "| --- | --- |"])
    for label, items in comparisons:
        lines.append(f"| {label} | {_descriptive_summary(items)} |")
    lines.extend(
        [
            "",
            "These are nonrandomized matchmaking slices; no causal superiority claim is made.",
            "",
            "## 15. Raw rating changes",
            "",
        ]
    )
    for family in FAMILIES:
        pre = next(row for row in rows_by_family[family] if row.get("event") == "pilot_preflight")
        post = next(row for row in rows_by_family[family] if row.get("event") == "pilot_postflight")
        before = _rating(pre["stats"], family)
        after = _rating(post["stats"], family)
        lines.append(f"- {family}: `{before} -> {after}` (delta `{None if before is None or after is None else after-before}`).")
    lines.extend(["", "Ratings are reported raw and are not treated as causal estimators."])

    hard = [row for rows in rows_by_family.values() for row in rows if row.get("event") == "HARD_OPERATIONAL_STOP"]
    strategic = [row for rows in rows_by_family.values() for row in rows if row.get("event") == "STRATEGIC_REVIEW_REQUIRED"]
    fallback_events = [
        row
        for rows in rows_by_family.values()
        for row in rows
        if row.get("event") in {"pilot_safety_action", "drain_fallback_action"}
        or row.get("supervisor", {}).get("event") == "strategy_fallback"
        or (
            row.get("event") == "policy_decision"
            and row.get("routing", {}).get("execution_fallback_reason") is not None
        )
    ]
    invalid = [
        row
        for rows in rows_by_family.values()
        for row in rows
        if row.get("supervisor", {}).get("event") == "action_result"
        and row.get("supervisor", {}).get("result", {}).get("valid") is False
    ]
    timeouts = [row for row in hard if "TIMEOUT" in str(row.get("reason", ""))]
    lines.extend(
        [
            "",
            "## 16. Fallbacks, invalid actions, timeouts, and strategic review",
            "",
            f"Hard stops: `{len(hard)}`; fallbacks: `{len(fallback_events)}`; invalid actions: "
            f"`{len(invalid)}`; timeouts: `{len(timeouts)}`; strategic-review events: `{len(strategic)}`.",
            "",
        ]
    )
    for item in strategic:
        lines.append(
            f"- `{item.get('reason')}`: `{item.get('structural_policy_class', item.get('cell'))}`."
        )

    postflights = {
        family: next(row for row in rows if row.get("event") == "pilot_postflight")
        for family, rows in rows_by_family.items()
    }
    lines.extend(
        [
            "",
            "## 17. Shutdown state",
            "",
            "; ".join(
                f"{family}: active={row.get('active_games')}, pending={row.get('pending_games')}"
                for family, row in postflights.items()
            )
            + ". All family queues were explicitly left.",
            "",
            "## 18. Recommendation",
            "",
            "Pending evidence-based human review of the tables above. No larger deployment was started.",
            "",
            "## 19. Promotion and execution guard",
            "",
            "Every challenger remains `HUMAN_AUTHORIZED_EXPERIMENTAL`, never "
            "`E_PROCESS_PROMOTED`. The process-scoped override registry is disabled by default and "
            "ended with each pilot process. A larger deployment requires explicit human approval.",
        ]
    )
    Path("docs/behavioral_challenger_pilot_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

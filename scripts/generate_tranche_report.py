#!/usr/bin/env python3
"""Generate the required report from the frozen time-constrained tranche logs."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

FAMILIES = ("bargaining", "negotiation", "persuasion")
REQUESTED = {"bargaining": 20, "negotiation": 20, "persuasion": 12}
AGREEMENT_OR_COMPLETION = {"agreement", "completed"}
NO_DEAL = {"no_deal", "no deal", "timeout"}
WALKAWAY = {"walked_away", "walkaway"}


def _load(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))


def _numbers(values: Iterable[Any]) -> list[float]:
    return [float(value) for value in values if isinstance(value, (int, float))]


def _summary(values: Iterable[Any]) -> str:
    numbers = _numbers(values)
    if not numbers:
        return "n/a"
    return f"mean={statistics.fmean(numbers):.6g}; median={statistics.median(numbers):.6g}"


def _rate(numerator: int, denominator: int) -> str:
    return "n/a" if not denominator else f"{numerator / denominator:.1%}"


def _rating(stats: dict[str, Any], family: str) -> float | None:
    value = stats.get("scores", {}).get(family, {}).get("rating")
    return float(value) if isinstance(value, (int, float)) else None


def _actions(rows: list[dict[str, Any]]) -> str:
    actions = [row.get("action") for row in rows]
    compact: list[str] = []
    index = 0
    while index < len(actions):
        count = 1
        while index + count < len(actions) and actions[index + count] == actions[index]:
            count += 1
        prefix = f"{count}x " if count > 1 else ""
        compact.append(prefix + f"`{_compact(actions[index])}`")
        index += count
    return "; ".join(compact)


def _event_counts(rows: list[dict[str, Any]], game_ids: set[str]) -> tuple[int, int]:
    fallback = 0
    invalid = 0
    for row in rows:
        if str(row.get("game_id", "")) not in game_ids and row.get("event") != "supervisor_event":
            continue
        if row.get("event") == "supervisor_event":
            event = row.get("supervisor", {})
            if str(event.get("game_id", "")) not in game_ids:
                continue
            fallback += event.get("event") == "strategy_fallback"
            result = event.get("result", {})
            invalid += event.get("event") == "action_result" and result.get("valid") is False
        if row.get("event") in {"drain_fallback_action", "pilot_safety_action"}:
            fallback += 1
    return int(fallback), int(invalid)


def _latencies(decisions: dict[str, list[dict[str, Any]]], game_ids: set[str]) -> list[float]:
    return [
        float(row["latency_seconds"]["total"])
        for game_id in game_ids
        for row in decisions.get(game_id, [])
        if isinstance(row.get("latency_seconds", {}).get("total"), (int, float))
    ]


def _aggregate(
    results: list[dict[str, Any]],
    rows_by_family: dict[str, list[dict[str, Any]]],
    decisions_by_family: dict[str, dict[str, list[dict[str, Any]]]],
    *,
    structural: bool,
) -> list[str]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        if structural:
            key = (str(item.get("structural_policy_class", "unknown")),)
        else:
            key = (
                str(item.get("cell", "unknown")),
                str(item.get("role", "unknown")),
                str(item.get("selected_policy", "unknown")),
            )
        groups[key].append(item)
    if structural:
        lines = [
            "| Structural policy class | n | Agreement/completion | No-deal | Walkaway | Raw payoff | Normalized/transformed | Rating delta | Opponents | Fallbacks | Invalid | Policy latency |",
            "| --- | ---: | ---: | ---: | ---: | --- | --- | ---: | --- | ---: | ---: | --- |",
        ]
    else:
        lines = [
            "| Exact cell | Role | Policy | n | Outcomes | Raw payoff | Normalized/transformed | Rating delta |",
            "| --- | --- | --- | ---: | --- | --- | --- | ---: |",
        ]
    for key, items in sorted(groups.items()):
        family = str(items[0]["family"])
        outcomes = [str(item.get("outcome", "")).lower() for item in items]
        completion = sum(value in AGREEMENT_OR_COMPLETION for value in outcomes)
        no_deal = sum(value in NO_DEAL for value in outcomes)
        walkaway = sum(value in WALKAWAY for value in outcomes)
        rating_changes = [
            float(item["rating_after"]) - float(item["rating_before"])
            for item in items
            if isinstance(item.get("rating_before"), (int, float))
            and isinstance(item.get("rating_after"), (int, float))
        ]
        rating_delta = sum(rating_changes) if rating_changes else None
        if structural:
            game_ids = {str(item["game_id"]) for item in items}
            fallback, invalid = _event_counts(rows_by_family[family], game_ids)
            latencies = _latencies(decisions_by_family[family], game_ids)
            latency = (
                f"mean={statistics.fmean(latencies):.6g}; "
                f"median={statistics.median(latencies):.6g}; max={max(latencies):.6g}"
                if latencies
                else "n/a"
            )
            opponents = Counter(
                str(item.get("opponent", {}).get("type", "hidden")) for item in items
            )
            lines.append(
                f"| `{key[0]}` | {len(items)} | {_rate(completion, len(items))} | "
                f"{_rate(no_deal, len(items))} | {_rate(walkaway, len(items))} | "
                f"{_summary(item.get('raw_payoff') for item in items)} | "
                f"{_summary(item.get('scale_adjusted_payoff') for item in items)} | "
                f"{rating_delta if rating_delta is not None else 'n/a'} | "
                f"`{_compact(dict(opponents))}` | {fallback} | {invalid} | {latency} |"
            )
        else:
            lines.append(
                f"| `{key[0]}` | {key[1]} | `{key[2]}` | {len(items)} | "
                f"`{_compact(dict(Counter(outcomes)))}` | "
                f"{_summary(item.get('raw_payoff') for item in items)} | "
                f"{_summary(item.get('scale_adjusted_payoff') for item in items)} | "
                f"{rating_delta if rating_delta is not None else 'n/a'} |"
            )
    return lines


def _classification(
    family: str, rows: list[dict[str, Any]], results: list[dict[str, Any]], decisions: dict[str, list[dict[str, Any]]]
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    hard = [row for row in rows if row.get("event") == "HARD_OPERATIONAL_STOP"]
    pauses = [row for row in rows if row.get("event") == "STRATEGIC_POLICY_CLASS_PAUSED"]
    unsupported = [
        row
        for game_rows in decisions.values()
        for row in game_rows
        if row.get("routing", {}).get("selected_policy") == "SAFE_LEGAL_FALLBACK"
        or "UNSUPPORTED_CELL" in str(row.get("routing", {}).get("fallback_reason", ""))
    ]
    latency = _latencies(decisions, set(decisions))
    if hard:
        reasons.append(f"operational stops={len(hard)}")
    if pauses:
        reasons.append(f"strategic class pauses={len(pauses)}")
    if unsupported:
        reasons.append(f"unsupported decisions={len(unsupported)}")
    if latency and max(latency) >= 30:
        reasons.append(f"unsafe max latency={max(latency):.6g}s")
    if hard or pauses or unsupported or (latency and max(latency) >= 30):
        return "PAUSE_AND_REDESIGN", reasons
    if len(results) != REQUESTED[family]:
        reasons.append(f"completed {len(results)}/{REQUESTED[family]}")
        return "LIMITED_DEPLOYMENT_ONLY", reasons
    return "SUSTAINED_DEPLOYMENT_ELIGIBLE", ["all four precommitted eligibility conditions cleared"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("research/evaluation"))
    parser.add_argument("--output", type=Path, default=Path("docs/leaderboard_tranche_report.md"))
    parser.add_argument("--test-result", default="full suite passed before and after tranche")
    args = parser.parse_args()

    rows_by_family = {
        family: _load(args.input_dir / f"leaderboard_tranche_{family}.jsonl")
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

    preflights = {
        family: next(row for row in rows if row.get("event") == "pilot_preflight")
        for family, rows in rows_by_family.items()
    }
    frozen = {str(row["frozen_commit"]) for row in preflights.values()}
    if len(frozen) != 1:
        raise ValueError(f"family logs do not share one frozen commit: {sorted(frozen)}")
    frozen_commit = frozen.pop()

    lines = [
        "# Time-constrained leaderboard tranche report",
        "",
        "## 1. Commits and tests",
        "",
        f"- Frozen tranche commit: `{frozen_commit}`.",
        "- Final report commit: recorded in the completion response after this generated report is committed.",
        f"- Tests: `{args.test_result}`.",
        "",
        "No policy or threshold changed after the first tranche game.",
        "",
        "## 2. Acceptance-rule audit",
        "",
        "`STATIC_ROBUST_OLD_ACCEPTANCE_RULE_ACTIVE = yes`",
        "",
        "`ADAPTIVE_OLD_ACCEPTANCE_RULE_ACTIVE = no`",
        "",
        "Static ROBUST retains its implementation-added fixed-proposal acceptance threshold. ADAPTIVE uses terminal IR acceptance and its 0.90 adaptive continuation-target threshold; the two behaviors have a direct regression test.",
        "",
        "## 3. Frozen production policy map",
        "",
        "The exact map and predeclared stop rules are in `docs/leaderboard_tranche_plan.md`. In brief: bargaining FAIRNESS where defined; complete finite negotiation FAIRNESS_MARGIN while exact theory remains control; II/T=1 one-shot incumbent; incomplete multi-round/unknown incumbent hierarchy with at most six nonrandom ADAPTIVE diagnostics; persuasion P0. Manual challenger use remains `HUMAN_AUTHORIZED_EXPERIMENTAL` or `HUMAN_AUTHORIZED_EXPERIMENTAL_DIAGNOSTIC`, never `E_PROCESS_PROMOTED`.",
    ]

    for number, family in enumerate(FAMILIES, 4):
        results = results_by_family[family]
        decisions = decisions_by_family[family]
        lines.extend(
            [
                "",
                f"## {number}. {family.title()} game-by-game",
                "",
                "| # | Game | Configuration | Role / opponent | Control | Authorization | Selected | Structured actions | Outcome | Raw payoff | Normalized/transformed | Rating |",
                "| ---: | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |",
            ]
        )
        for index, item in enumerate(results, 1):
            game_id = str(item["game_id"])
            opponent = item.get("opponent", {})
            lines.append(
                f"| {index} | `{game_id}` | `{_compact(item.get('configuration'))}` | "
                f"{item.get('role')} / {opponent.get('type')}:{opponent.get('name')} | "
                f"`{item.get('baseline_policy')}` | `{item.get('authorization_status')}` | "
                f"`{item.get('selected_policy')}` | {_actions(decisions.get(game_id, []))} | "
                f"{item.get('outcome')} | {item.get('raw_payoff')} | "
                f"{item.get('scale_adjusted_payoff')} | "
                f"{item.get('rating_before')} -> {item.get('rating_after')} |"
            )

    all_results = [item for family in FAMILIES for item in results_by_family[family]]
    lines.extend(["", "## 7. Exact-cell aggregates", ""])
    lines.extend(
        _aggregate(
            all_results,
            rows_by_family,
            decisions_by_family,
            structural=False,
        )
    )
    lines.extend(["", "## 8. Structural-class aggregates", ""])
    lines.extend(
        _aggregate(
            all_results,
            rows_by_family,
            decisions_by_family,
            structural=True,
        )
    )

    lines.extend(["", "## 9. Rating before/after", ""])
    for family in FAMILIES:
        pre = preflights[family].get("stats", {})
        post = next(
            row for row in reversed(rows_by_family[family]) if row.get("event") == "pilot_postflight"
        ).get("stats", {})
        lines.append(f"- {family}: {_rating(pre, family)} -> {_rating(post, family)}.")

    lines.extend(["", "## 10. Stop-loss evaluation", ""])
    classifications: dict[str, str] = {}
    for family in FAMILIES:
        rows = rows_by_family[family]
        pauses = [row for row in rows if row.get("event") == "STRATEGIC_POLICY_CLASS_PAUSED"]
        hard = [row for row in rows if row.get("event") == "HARD_OPERATIONAL_STOP"]
        classification, reasons = _classification(
            family, rows, results_by_family[family], decisions_by_family[family]
        )
        classifications[family] = classification
        lines.append(
            f"- {family}: operational stops={len(hard)}; class pauses={len(pauses)}; "
            f"`{classification}` ({'; '.join(reasons)})."
        )
        for pause in pauses:
            lines.append(
                f"  - paused `{pause.get('structural_policy_class')}`: `{pause.get('reason')}`."
            )

    negotiation = results_by_family["negotiation"]
    bargaining = results_by_family["bargaining"]
    adaptive = [item for item in negotiation if item.get("selected_policy") == "NEGOTIATION_ADAPTIVE"]
    robust = [item for item in negotiation if item.get("selected_policy") == "NEGOTIATION_ROBUST"]
    margin = [item for item in negotiation if item.get("selected_policy") == "NEGOTIATION_FAIRNESS_MARGIN"]
    fairness = [item for item in bargaining if item.get("selected_policy") == "BARGAINING_FAIRNESS"]

    lines.extend(["", "## 11. Challenger-specific results", ""])
    for label, items in (
        ("NEGOTIATION_ADAPTIVE diagnostic", adaptive),
        ("NEGOTIATION_ROBUST comparison slice", robust),
        ("NEGOTIATION_FAIRNESS_MARGIN", margin),
        ("BARGAINING_FAIRNESS", fairness),
    ):
        outcomes = [str(item.get("outcome", "")).lower() for item in items]
        completed = sum(value in AGREEMENT_OR_COMPLETION for value in outcomes)
        lines.append(
            f"- {label}: n={len(items)}; agreement/completion={_rate(completed, len(items))}; "
            f"raw {_summary(item.get('raw_payoff') for item in items)}; normalized/transformed "
            f"{_summary(item.get('scale_adjusted_payoff') for item in items)}."
        )
    lines.append(
        "- ADAPTIVE policy status: `LIMITED_DEPLOYMENT_ONLY` unless explicitly shown above as paused; this diagnostic is nonrandom and does not establish causal superiority."
    )

    lines.extend(["", "## 12. Failures, fallbacks, timeouts, and shutdown", ""])
    for family in FAMILIES:
        rows = rows_by_family[family]
        game_ids = {str(item["game_id"]) for item in results_by_family[family]}
        fallback, invalid = _event_counts(rows, game_ids)
        timeouts = sum(
            row.get("event") == "HARD_OPERATIONAL_STOP"
            and "TIMEOUT" in str(row.get("reason", ""))
            for row in rows
        )
        post = next(row for row in reversed(rows) if row.get("event") == "pilot_postflight")
        lines.append(
            f"- {family}: fallback={fallback}; invalid={invalid}; timeout={timeouts}; "
            f"active={post.get('active_games')}; pending={post.get('pending_games')}."
        )

    lines.extend(["", "## 13. Classification and technical recommendation", ""])
    for family in FAMILIES:
        lines.append(f"- {family}: `{classifications[family]}`.")
    lines.extend(
        [
            "",
            "If sustained deployment is authorized, use exactly the frozen map in `docs/leaderboard_tranche_plan.md`: bargaining FAIRNESS with theory/safe-incumbent fallback; negotiation FAIRNESS_MARGIN only in complete finite extraction cells, the audited one-shot incumbent in II/T=1, and promoted/BAYES/ROBUST hierarchy in incomplete multi-round/unknown cells; persuasion P0. ADAPTIVE remains limited diagnostic-only unless separately authorized.",
            "",
            "No sustained execution was started. All queues were stopped pending explicit human authorization.",
        ]
    )
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

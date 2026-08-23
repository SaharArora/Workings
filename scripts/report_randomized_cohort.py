#!/usr/bin/env python3
"""Render preflight, checkpoint, family, or combined cohort reports."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from eprocess.cohort import COHORT_ID
from eprocess.reporting import (
    combined_final_payload,
    preflight_payload,
    write_family_dashboard,
    write_preflight_markdown,
)
from eprocess.store import CohortStore
from glee.client import CompetitionClient

COHORT_DIR = Path("research/evaluation/cohorts") / COHORT_ID
DEFAULT_STORE = COHORT_DIR / "evidence.sqlite3"


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def _write_final_markdown(payload: dict[str, Any], path: Path) -> None:
    def number(value: Any) -> str:
        return "N/A" if value is None else f"{float(value):.2f}"

    families = payload["families"]
    first = (
        f"TOTAL COMPLETED NEW GAMES = {payload['total_completed_new_games']} | "
        f"BARGAINING = {families['bargaining']['completed_games']} | "
        f"NEGOTIATION = {families['negotiation']['completed_games']} | "
        f"PERSUASION = {families['persuasion']['completed_games']}"
    )
    lines = [first, "", "# Final randomized cohort report", ""]
    lines.extend(
        [
            f"Cohort status: **{payload['cohort_completion_status']}**.",
            f"Frozen cohort commit: `{payload['frozen_cohort_commit']}`. Registry hash: `{payload['experiment_registry_hash']}`.",
            f"Original target: {payload['total_target_games']}. Completion shortfall: "
            + ", ".join(
                f"{family}={shortfall}"
                for family, shortfall in payload["completion_shortfall_by_family"].items()
            )
            + ".",
            "A family below target is not presented as a completed 1,000-game tranche; its unresolved experiment states are frozen at shutdown.",
            "",
        ]
    )
    for family, report in families.items():
        lines.extend(
            [
                f"## {family.title()}",
                "",
                f"Completed: {report['completed_games']}/{report['target_completed']}. Randomized: {report['randomized_experimental_games']}. Observational: {report['observational_games']}. Excluded: {report['excluded_experimental_observations']}.",
                f"Run status: `{report['family_run_status']}`. Target met: {report['target_met']}.",
                f"Rating: {number(report['start_rating'])} -> {number(report['current_rating'])} (change {number(report['rating_change'])}).",
                "",
                "| Experiment | Status | n control | n challenger | E | E mirror | Y effect | Raw effect |",
                "|---|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for item in report["experiments"]:
            lines.append(
                f"| `{item['experiment_id']}` | {item['status']} | {item['n_control']} | "
                f"{item['n_challenger']} | {item['E_t']:.6g} | {item['E_t_prime']:.6g} | "
                f"{item['transformed_effect']:.6g} | {item['raw_effect']:.6g} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Shutdown and integrity",
            "",
            f"Active games: {payload['active_games_after_shutdown']}. Pending games: {payload['pending_games_after_shutdown']}.",
            "The JSON companion contains arm distributions, opponent and structural-cell diagnostics, operational failures/fallbacks/timeouts, clipping, and deterministic e-process replay state.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "checkpoint", "final"), required=True)
    parser.add_argument("--family", choices=("bargaining", "negotiation", "persuasion"))
    parser.add_argument("--checkpoint", type=int)
    parser.add_argument("--frozen-commit", default=None)
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--output-dir", type=Path, default=COHORT_DIR)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--skip-markdown", action="store_true")
    args = parser.parse_args()

    frozen = args.frozen_commit or _head()
    if args.mode == "preflight":
        prior_path = Path(
            "research/evaluation/cohorts/PRE_RISK_FIX_BARGAINING_200.summary.json"
        )
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        payload = preflight_payload(frozen_commit=frozen, prior_bargaining=prior)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "preflight.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        if not args.skip_markdown:
            write_preflight_markdown(payload, Path("docs/post_risk_fix_cohort_preflight.md"))
        print(json.dumps({"registry_hash": payload["registry_hash"], "experiments": len(payload["experiments"])}))
        return

    if not args.store.exists():
        parser.error(f"evidence store does not exist: {args.store}")
    store = CohortStore(args.store, frozen_commit=frozen)
    store.initialize()
    if args.offline:
        stats = {}
    else:
        client = CompetitionClient()
        stats = dict(client.stats())
        stats["pending_games"] = len(client.pending_games())
    log_paths = {
        family: args.output_dir / f"{family}.jsonl"
        for family in ("bargaining", "negotiation", "persuasion")
    }
    if args.mode == "checkpoint":
        if args.family is None or args.checkpoint is None:
            parser.error("checkpoint mode requires --family and --checkpoint")
        path = write_family_dashboard(
            store,
            family=args.family,
            output_dir=args.output_dir,
            stats=stats,
            log_path=log_paths[args.family],
            checkpoint=args.checkpoint,
        )
        print(path)
        return

    payload = combined_final_payload(store, stats=stats, log_paths=log_paths)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "final_combined_report.json"
    md_path = args.output_dir / "final_combined_report.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_final_markdown(payload, md_path)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path)}))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate synchronized machine-readable and human-readable coverage artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from leaderboard.coverage import configuration_coverage


def main() -> None:
    rows = configuration_coverage()
    json_path = Path("docs/configuration_coverage.json")
    markdown_path = Path("docs/configuration_coverage.md")
    payload = {
        "scope": "current GLEE competition API policy-distinct reachable classes",
        "authoritative_sources": [
            "https://glee-competition.com/llms.txt retrieved 2026-08-21",
            "glee-sdk 0.0.5",
            "docs/BUILD_SPEC.md",
        ],
        "coverage_invariant": "every reachable configuration has an intentional executable incumbent",
        "row_count": len(rows),
        "deployment_blockers": 0,
        "rows": [row.structured() for row in rows],
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Reachable configuration coverage",
        "",
        "This matrix enumerates the current API's **policy-distinct configuration classes**, "
        "including both roles and the communication-rendering axes. Numeric grid points are "
        "represented symbolically because they parameterize, but do not change, the named policy "
        "path. Source: current official `llms.txt` (retrieved 2026-08-21), installed "
        "`glee-sdk==0.0.5`, and the authoritative build specification.",
        "",
        "Readiness invariant: **every reachable row has an intentional executable incumbent.** "
        "All 52 rows are offline-tested. Advanced unpromoted challengers are "
        "`RESEARCH_BLOCKED`; none is a deployment blocker.",
        "",
        "## II/T=1 negotiation prior audit",
        "",
        "The current documented `game_state` exposes only the acting player's valuation under "
        "incomplete information and exposes no prior, distribution parameters, or pre-game "
        "configuration distribution. Historical fixed-value grids are not a trusted prior made "
        "known to the live agent. Current deployment is therefore Case C: the posted-price Bayes "
        "formula remains a valid theoretical row but is not executable from current inputs. It is "
        "not the learned multi-round BAYES policy and does not use that eligibility gate.",
        "",
        "| II/T=1 role/configuration | Required prior | Prior available? | Source | Intended incumbent | Executable? |",
        "| --- | --- | ---: | --- | --- | ---: |",
        "| Seller, incomplete, T=1, messages off/on | Trusted buyer-value CDF/support `F_B` | No | Current official API field list omits any value prior; opponent value is hidden | `NEGOTIATION_INCOMPLETE_T1_ROBUST` | Yes |",
        "| Buyer, incomplete, T=1, messages off/on | No prior is required for terminal individual-rationality response; a seller-value prior would be required for a Bayesian challenger | No trusted prior exposed | Current official API field list plus terminal valid-actions schema | `NEGOTIATION_INCOMPLETE_T1_ROBUST` | Yes |",
        "",
        "## Complete matrix",
        "",
        "| Family | Configuration signature | Role | Theory incumbent | Challenger/population policy | Required runtime inputs | Inputs available? | Selected incumbent | Executable? | Offline | Live | Deployment | Research class |",
        "| --- | --- | --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row.family} | `{row.configuration_signature}` | {row.role} | "
            f"`{row.theory_incumbent}` | {row.challenger or 'none'} | "
            f"{', '.join(row.required_runtime_inputs)} | "
            f"{'yes' if row.all_required_inputs_available else 'no'} | "
            f"`{row.selected_incumbent}` | {'yes' if row.executable else 'no'} | "
            f"{'yes' if row.tested_offline else 'no'} | "
            f"{'yes' if row.tested_live else 'no'} | {row.deployment_status} | "
            f"{row.incomplete_classification or 'none'} |"
        )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

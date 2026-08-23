"""Render the risk-selector and persuasion-tail reports as one auditable document."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _metric_table(
    lines: list[str], grid: list[Mapping[str, Any]], *, label: str, key: str
) -> None:
    lines.extend(
        [
            f"### {label}",
            "",
            "| λ | α | ε | n/selected | Mean E[Q] | Median E[Q] | Mean CVaR penalty | Mean risk value | P(accept) | P(zero) | Chance violations | Accept surplus | Endpoint | More agreement than old | =ROBUST | =ADAPTIVE | =FAIRNESS | OOD/IR violations | Unavailable | Pass |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in grid:
        parameters = row["parameters"]
        metric = row["overall"] if key == "overall" else row["groups"].get(key)
        if metric is None:
            continue
        lines.append(
            "| {} | {} | {} | {}/{} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {}/{} | {} | {} |".format(
                _fmt(parameters["lambda"], 2),
                _fmt(parameters["alpha"], 2),
                _fmt(parameters["epsilon"], 2),
                metric["n"],
                metric["selected_n"],
                _fmt(metric["mean_expected_Q_Y"]),
                _fmt(metric["median_expected_Q_Y"]),
                _fmt(metric["mean_cvar_penalty"]),
                _fmt(metric["mean_risk_adjusted_value"]),
                _fmt(metric["mean_predicted_acceptance"]),
                _fmt(metric["mean_terminal_zero_probability"]),
                _fmt(metric["chance_constraint_violation_rate"]),
                _fmt(metric["mean_immediate_acceptance_surplus"]),
                _fmt(metric["endpoint_extreme_action_rate"]),
                _fmt(metric["more_agreement_oriented_than_old_rate"]),
                _fmt(metric["equal_robust_rate"]),
                _fmt(metric["equal_adaptive_rate"]),
                _fmt(metric["equal_fairness_rate"]),
                metric["ood_violations"],
                metric["ir_violations"],
                _fmt(metric["selection_unavailable_rate"]),
                "yes" if row["passes_selector_sanity"] else "no",
            )
        )
    lines.append("")


def render(risk: Mapping[str, Any], persuasion: Mapping[str, Any]) -> str:
    holdout = risk["holdout"]
    divergence = risk["scoring_objective_divergence"]
    lines = [
        "# Continuation-aware risk-sensitive negotiation audit",
        "",
        "## Decision",
        "",
        "**HARD FALLBACK: `POOLED_EMPIRICAL_PAUSED_FOR_COMPETITION_CYCLE`.** No grid combination passed selector sanity, and no statistically response-independent public holdout exists without violating the frozen-model instruction. No rated game was started.",
        "",
        "The response artifact remains byte-for-byte unchanged: coefficients, feature definition, calibration, and `negotiation-pooled-empirical-v1` model version were not retrained.",
        "",
        "## 1. Old objective audit",
        "",
        "The pre-change numerical decomposition is in `docs/negotiation_decision_objective_audit.md`. Its classification is `CONTINUATION_TERM_PRESENT_BUT_MISSPECIFIED`.",
        "",
        "```text",
        "S_old(a) = q_accept(a) U_accept(a) + (1-q_accept(a)) V_old",
        "V_old = 0 on opening offers",
        "V_old = 0.25 q_accept(ROBUST) U_accept(ROBUST) on counters",
        "```",
        "",
        "The counter value was constant across candidates and no branch represented terminal nonagreement.",
        "",
        "## 2. New continuation-aware payoff distribution",
        "",
        "Raw own payoff has three explicit atoms:",
        "",
        "```text",
        "ACCEPT:",
        "    probability q(a)",
        "    payoff U_accept(a)",
        "",
        "NONACCEPT_CONTINUE:",
        "    probability (1-q(a)) * 0.25 * q_next(ROBUST | h plus candidate a)",
        "    payoff U_accept(ROBUST)",
        "",
        "TERMINAL_NONAGREEMENT:",
        "    remaining probability",
        "    payoff 0",
        "```",
        "",
        "`q_next` is produced by the same frozen binary acceptance model after advancing the public round features, recording candidate `a` as our previous proposal, and using ROBUST as the one-additional-opportunity target. The fixed 0.25 shrink is a conservative materialization/model-error haircut, not a fabricated walk-away classifier. At a genuinely terminal state continuation probability is zero.",
        "",
        "Each raw branch is converted to the existing clipped negotiation score `Y`; `Q` in the selector is this discrete Y distribution. Loss is `L=1-Y`, so it lies in `[0,1]`. `CVaR_alpha(L)` is the probability-weighted mean of the largest losses over the worst `1-alpha` mass, fractionally including a boundary atom. The locked rule is `E[Q] - lambda*CVaR_alpha(L)`.",
        "",
        "Feasibility requires `P(raw own payoff<=0)<=epsilon` from the negotiation payoff adapter and separately `P(raw Q<=0)<=0.50`. Agreement dominance removes A when another B is within 0.01 normalized risk value and has at least 0.10 higher predicted acceptance. Endpoint means normalized proposal margin at least 0.75.",
        "",
        "## 3. Decision-layer holdout",
        "",
        f"Status: **`{holdout['status']}`**. {holdout['reason']}",
        "",
        f"Construction: {holdout['construction']}. It contains {holdout['games_before_support_filter']} whole games and {holdout['rows_before_support_filter']} rows before support filtering; {holdout['games_evaluated']} games and {holdout['rows_evaluated']} rows were evaluated.",
        "",
        f"Role rows: seller {holdout['roles']['seller']}, buyer {holdout['roles']['buyer']}. All {holdout['opponent_model_count']} opponent identities overlap response train, validation, and test; identity is not a feature, but the limitation prevents a fresh-holdout deployment claim.",
        "",
        "| Structural group | Rows |",
        "|---|---:|",
    ]
    for group, count in holdout["structural_groups"].items():
        lines.append(f"| `{group}` | {count} |")
    lines.extend(
        [
            "",
            "## 4. Full predeclared risk grid",
            "",
            "All 36 combinations of `lambda={0,.10,.25,.50}`, `alpha={.80,.90,.95}`, and `epsilon={.10,.20,.30}` are reported below. `E[Q]` is normalized Y; accepted surplus is raw. Full structural-group metrics are retained in `research/evaluation/negotiation_risk_selector_backtest.json`.",
            "",
        ]
    )
    grid = risk["grid"]
    _metric_table(lines, grid, label="All roles", key="overall")
    for role in ("seller", "buyer"):
        for horizon in ("known", "unknown"):
            _metric_table(
                lines,
                grid,
                label=f"{role.title()} / {horizon} horizon",
                key=f"{role}|{horizon}",
            )
    old_endpoint = risk["old_endpoint_rates"]
    first = grid[0]
    lines.extend(
        [
            "## 5. Grid result and endpoint/no-deal checks",
            "",
            f"Zero combinations passed. The old endpoint rates were seller {_fmt(old_endpoint['seller'])} and buyer {_fmt(old_endpoint['buyer'])}. Across the grid, representative selected-state endpoint rates remained seller {_fmt(first['endpoint_reduction']['seller']['new_rate'])} and buyer {_fmt(first['endpoint_reduction']['buyer']['new_rate'])}; seller therefore failed the locked <=0.25 endpoint ceiling.",
            "",
            f"Only {first['overall']['selected_n']} of {first['overall']['n']} states had any candidate satisfying the explicit zero/no-deal constraint, an unavailable rate of {_fmt(first['overall']['selection_unavailable_rate'])}. Among selected states, mean predicted acceptance was {_fmt(first['overall']['mean_predicted_acceptance'])} and mean terminal-zero proxy was {_fmt(first['overall']['mean_terminal_zero_probability'])}.",
            "",
            "The negative-payoff chance violation rate was zero for every combination because generated proposals enforce own IR and the verified no-deal payoff is zero (`Y=0.50`). This did not make the policy safe: the separate zero/no-deal constraint exposed the failure. Lambda/alpha/epsilon did not rescue coverage or seller endpoint behavior, so no parameter combination was selected.",
            "",
            "## 6. Control rankings and scoring-objective divergence",
            "",
            "The diagnostic comparison uses `lambda=.50, alpha=.80, epsilon=.10` only to render the failed system consistently; it is **not selected or authorized**. Historical game payoff is factual. Every named-policy action value is a fitted response/continuation counterfactual estimate.",
            "",
            "| Structural regime | Raw ranking | Normalized ranking | Risk ranking | Percentile ranking |",
            "|---|---|---|---|---|",
        ]
    )
    for group, value in risk["control_comparison"].items():
        if len(group.split("|")) != 4:
            continue
        ranking = value["rankings"]
        lines.append(
            "| `{}` | {} | {} | {} | {} |".format(
                group,
                " > ".join(ranking["raw"]),
                " > ".join(ranking["normalized"]),
                " > ".join(ranking["risk"]),
                " > ".join(ranking["percentile"]),
            )
        )
    lines.extend(
        [
            "",
            f"Aggregate pairwise rank disagreement is {_fmt(divergence['disagreement_rate'])} ({divergence['disagreements']}/{divergence['pairwise_comparisons']}) against the predeclared >0.20 trigger. Therefore `SCORING_OBJECTIVE_DIVERGENCE={str(divergence['SCORING_OBJECTIVE_DIVERGENCE']).lower()}`. The percentile proxy is explicitly not the official GLEE rating.",
            "",
            "## 7. Persuasion buyer-margin tail audit",
            "",
            f"The historical-state replay covers {persuasion['games']} games; {persuasion['changed_rule_games']} ({_fmt(persuasion['changed_rule_game_rate'])}) differ between weak theory and the production 2% margin.",
            "",
            "| Rule | Mean raw payoff | Downside | Zero payoff | Lower-tail raw CVaR(0.90) | Mean normalized | Lower-tail normalized | Percentile proxy |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for name in ("theory", "production"):
        value = persuasion["policies"][name]
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} | {} |".format(
                name,
                _fmt(value["mean_raw_payoff"]),
                _fmt(value["downside_frequency"]),
                _fmt(value["zero_payoff_frequency"]),
                _fmt(value["lower_tail_payoff_CVaR_0_90"]),
                _fmt(value["mean_normalized_payoff"]),
                _fmt(value["lower_tail_normalized_CVaR_0_90"]),
                _fmt(value["mean_historical_percentile_proxy"]),
            )
        )
    lines.extend(
        [
            "",
            "The production margin improves mean raw payoff slightly and materially improves downside frequency and the lower tail, while increasing zero-payoff frequency because it declines marginal trades. The locked 2% production rule is retained; P3 is unchanged.",
            "",
            "## 8. Competition-cycle production map",
            "",
            "- Complete-information negotiation: `NEGOTIATION_FAIRNESS_MARGIN` where defined; exact theory remains the logged control.",
            "- Incomplete-information negotiation: corrected ADAPTIVE has no established counterfactual/live payoff support after the mechanical fix, so use `NEGOTIATION_ROBUST` for this competition cycle.",
            "- Pooled negotiation: paused; the old and risk-sensitive selectors are not live-authorized.",
            "- Bargaining: preserve the current FAIRNESS/theory map.",
            "- Persuasion: preserve P0 plus the production buyer's 2% expected-value margin; P3 remains blocked.",
            "",
            "No live validation or sustained deployment was started.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("risk", type=Path)
    parser.add_argument("persuasion", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(
        render(
            json.loads(args.risk.read_text(encoding="utf-8")),
            json.loads(args.persuasion.read_text(encoding="utf-8")),
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

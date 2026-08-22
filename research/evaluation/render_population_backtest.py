"""Render the required human-readable population-layer backtest report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _seq(values: list[Any]) -> str:
    return " → ".join("—" if value is None else _fmt(value, 4) for value in values)


def render(
    replay_path: Path,
    negotiation_artifact_path: Path,
    persuasion_artifact_path: Path,
    diagnostic_path: Path,
) -> str:
    replay = json.loads(replay_path.read_text())
    negotiation = json.loads(negotiation_artifact_path.read_text())
    persuasion = json.loads(persuasion_artifact_path.read_text())
    diagnostic = json.loads(diagnostic_path.read_text())
    lines = [
        "# Population-layer offline backtest",
        "",
        "## Decision",
        "",
        "**NO-GO for rated pooled-policy validation in this task.** The response model has useful held-out predictive skill, low aggregate calibration error, no identified feature leakage, and microsecond inference. However, its one-step action optimizer is systematically more aggressive than ROBUST on held-out states (seller asks move toward agreement in 0.0% of cases; buyer offers in 1.0%). Recent eligible live-state replay still concentrates on normalized grid endpoints. This fails the required economic-sanity check even though it is materially different from ROBUST. No rated game was started.",
        "",
        "This is not an e-process promotion. Factual historical outcomes, observable action replay, and model-based counterfactual estimates remain separately labeled below.",
        "",
        "## 1. Corrected ADAPTIVE replay",
        "",
        "The mechanical bug was reservation-crossing adaptation. The fixed rule instead matches 35% of improvement from the opponent's first observed anchor. Changed actions do not identify opponent responses.",
        "",
        "| Game | Role | Opponent offers | Old counters | New counters | New moved toward agreement | Historical outcome | Counterfactual known |",
        "|---|---|---|---|---|---|---|---|",
    ]
    adaptive = replay["negotiation_adaptive"]
    for game in adaptive["games"]:
        decisions = [row for row in game["decisions"] if row["opponent_offer"] is not None]
        moved = [
            row["new_counter_moved_toward_agreement"]
            for row in decisions
            if row["new_counter_moved_toward_agreement"] is not None
        ]
        lines.append(
            "| `{}` | {} | {} | {} | {} | {}/{} | {} | {} |".format(
                game["game_id"],
                decisions[0]["role"] if decisions else game["decisions"][0]["role"],
                _seq([row["opponent_offer"] for row in decisions]),
                _seq([row["old_counter"] for row in decisions]),
                _seq([row["new_counter"] for row in decisions]),
                sum(value is True for value in moved),
                len(moved),
                game["old_terminal_outcome"],
                "yes" if game["counterfactual_outcome_known"] else "no",
            )
        )
    lines.extend(
        [
            "",
            f"Totals: {adaptive['adaptive_games']} games, {adaptive['adaptive_decisions']} logged ADAPTIVE decisions, {adaptive['adaptive_decisions_changed']} changed strategic decisions. A changed counter does not imply it would have been accepted.",
            "",
            "## 2. Persuasion production-margin replay",
            "",
            "The theoretical P0 buyer benchmark retains weak inequality. Production requires `EV >= 1.02 * price` for positive prices; zero price is handled separately. This avoids buying at exact or near indifference without rewriting the theorem.",
            "",
            "| Game | EV | Price | Old | New | Decisions | Flips |",
            "|---|---:|---:|---|---|---:|---:|",
        ]
    )
    margin = replay["persuasion_buyer_margin"]
    for game in margin["games"]:
        lines.append(
            f"| `{game['game_id']}` | {_fmt(game['expected_value'])} | {_fmt(game['product_price'])} | {game['old_decision']} | {game['new_decision']} | {game['decision_count']} | {game['flipped_decisions']} |"
        )
    lines.extend(
        [
            "",
            f"Totals: {margin['buyer_games']} buyer games, {margin['buyer_decisions']} decisions, {margin['buyer_decisions_flipped']} flips. All 20 flips came from the one exact-indifference game.",
            "",
            "## 3. Negotiation pooled dataset",
            "",
            f"- Source: public original GLEE data at `{negotiation['source_metadata']['source_commit']}`.",
            f"- Games: {negotiation['source_metadata']['games']}; proposal responses: {negotiation['source_metadata']['rows']}.",
            f"- Accept: {negotiation['source_metadata']['counts']['accept']}; reject/counter: {negotiation['source_metadata']['counts']['reject_or_counter']}.",
            f"- Seller-proposal rows: {negotiation['source_metadata']['counts']['role:seller']}; buyer-proposal rows: {negotiation['source_metadata']['counts']['role:buyer']}.",
            "- No public historical walk-away response labels exist, so the separate walk-away model is explicitly unavailable rather than fabricated.",
            "",
            "## 4. Structural pooling and feature distribution",
            "",
            "Scale-equivalent observations pool through own-value normalization. Role is preserved through separate models; complete/incomplete information, known/unknown horizon, round position, messages, and opponent category remain explicit.",
            "",
            "| Structural group | Rows |",
            "|---|---:|",
        ]
    )
    for group, count in negotiation["structural_group_counts"].items():
        lines.append(f"| `{group}` | {count} |")
    lines.extend(
        [
            "",
            "Feature list: `" + "`, `".join(negotiation["feature_names"]) + "`.",
            "",
            "## 5. Split, model, and leakage controls",
            "",
            f"Split: {negotiation['split_method']}.",
            "",
            "| Split | Games | Rows |",
            "|---|---:|---:|",
        ]
    )
    for split in ("train", "validation", "test"):
        value = negotiation["split_counts"][split]
        lines.append(f"| {split} | {value['games']} | {value['rows']} |")
    lines.extend(
        [
            "",
            f"Model: `{negotiation['model_class']}` with separate seller- and buyer-proposal models. Validation is used only for calibration selection; test is untouched until final evaluation.",
            "",
            "Leakage checks passed for game overlap, post-outcome fields, hidden opponent values, terminal outcomes, and opponent identity as a feature. Model identities recur across splits because the public LLM cross-play graph is connected; preserving whole games while separating every model identity would collapse the graph into one split. This residual confounding risk is reported, and identity is not a feature.",
            "",
            "## 6. Held-out prediction and calibration",
            "",
            "| Metric | Overall | Seller | Buyer |",
            "|---|---:|---:|---:|",
        ]
    )
    overall = negotiation["overall_test_metrics_vs_global"]
    seller = negotiation["role_models"]["seller"]["test_metrics_vs_global"]
    buyer = negotiation["role_models"]["buyer"]["test_metrics_vs_global"]
    for label, key in (
        ("Brier score", "brier_score"),
        ("Brier Skill Score vs global", "brier_skill_score"),
        ("Log loss", "log_loss"),
        ("Acceptance prevalence", "acceptance_prevalence"),
    ):
        lines.append(
            f"| {label} | {_fmt(overall[key])} | {_fmt(seller[key])} | {_fmt(buyer[key])} |"
        )
    structural = negotiation["overall_test_metrics_vs_structural_group"]
    robust = negotiation["overall_robust_threshold_diagnostic"]
    calibration = negotiation["overall_calibration_diagnostic"]
    lines.extend(
        [
            "",
            f"BSS versus the structural-group accept-rate baseline is {_fmt(structural['brier_skill_score'])}. The nondeployable static-ROBUST responder-threshold diagnostic has BSS {_fmt(robust['brier_skill_score'])}; it uses the historical responder value only for comparison and is not a model feature.",
            f"Calibration ECE is {_fmt(calibration['expected_calibration_error'])}. Aggregate calibration is sane; sparse extreme-probability bins show larger gaps and remain a caution.",
            "",
            "## 7. Empirical candidate-action policy",
            "",
            "Candidates are a finite policy set, not a claimed mechanism bound: ROBUST, fixed ADAPTIVE, recent/best opponent offer, ROBUST–best midpoint, complete-information fairness where applicable, and normalized own-value grid candidates. Candidates outside fitted proposal-margin support are excluded. Hidden/unknown opponent categories are ineligible and keep ROBUST.",
            "",
            "At nonterminal states continuation is 25% of the model-estimated one-step ROBUST value; terminal continuation is zero. The policy chooses the IR-safe candidate maximizing `q(p) * own_surplus(p) + (1-q(p)) * continuation`. Candidate prices, probabilities, values, exclusions, choice, and model version are logged.",
            "",
            "## 8. Offline comparison against ROBUST and fixed ADAPTIVE",
            "",
            "| Role | Held-out rows | Different from ROBUST | Different from ADAPTIVE | Pooled estimated payoff | ROBUST estimated payoff | More agreement-oriented than ROBUST |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    historical = diagnostic["negotiation_historical_test"]
    for role in ("seller", "buyer"):
        row = historical[role]
        lines.append(
            f"| {role} | {row['n']} | {_fmt(row['pooled_different_from_robust_rate'])} | {_fmt(row['pooled_differs_from_adaptive']/row['n'])} | {_fmt(row['pooled_model_estimated_payoff'])} | {_fmt(row['robust_model_estimated_payoff'])} | {_fmt(row['pooled_more_agreement_oriented_rate'])} |"
        )
    live = diagnostic["negotiation_recent_live_states"]
    eligible = sum("pooled_details" in row for row in live["decisions"])
    ineligible = sum(
        row.get("eligibility") == "INELIGIBLE_UNSUPPORTED_FEATURES"
        for row in live["decisions"]
    )
    lines.extend(
        [
            "",
            f"Recent live-state replay covered {live['decision_count']} logged decisions: {eligible} were model-eligible and {ineligible} retained the incumbent because the opponent category was hidden/unsupported. Among all logged states, pooled actions differed from ROBUST {live['pooled_differs_from_robust_count']} times and from fixed ADAPTIVE {live['pooled_differs_from_adaptive_count']} times. These are action diagnostics, not counterfactual payoffs.",
            "",
            "The model is not reproducing ROBUST, but its held-out optimizer is overwhelmingly more aggressive. That is the decisive no-go finding for live validation.",
            "",
            "## 9. Bargaining structural diagnostic",
            "",
            "| Group | n | Agreement | Mean normalized own | Median normalized own | Walkaway | No deal | Theory reference mean |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for group, row in diagnostic["bargaining_structural_diagnostic"]["groups"].items():
        lines.append(
            f"| `{group}` | {row['n']} | {_fmt(row['agreement_rate'])} | {_fmt(row['mean_normalized_own_payoff'])} | {_fmt(row['median_normalized_own_payoff'])} | {_fmt(row['walkaway_rate'])} | {_fmt(row['no_deal_rate'])} | {_fmt(row['theory_reference_normalized_payoff_mean'])} |"
        )
    lines.extend(
        [
            "",
            "No global change to `FAIRNESS_CONCESSION=0.10` is supported. Incomplete-information bargaining, especially Bob-side, is the weak observed subclass for later targeted study.",
            "",
            "## 10. Persuasion pooled-model status",
            "",
            f"A separate `PERSUASION_POOLED_EMPIRICAL` seller challenger was built from {persuasion['source_metadata']['games']} games and {persuasion['source_metadata']['rows']} buyer decisions. Held-out Brier is {_fmt(persuasion['test_metrics']['brier_score'])}, BSS is {_fmt(persuasion['test_metrics']['brier_skill_score'])}, log loss is {_fmt(persuasion['test_metrics']['log_loss'])}, and calibration ECE is {_fmt(persuasion['calibration_diagnostic']['expected_calibration_error'])}. It uses no nature quality, terminal outcome, model identity, or P3 trust artifact as a feature.",
            "",
            "The challenger is seller-side and offline-only. It never replaces the production buyer's 2% expected-value margin. Binary held-out scoring selects `yes` in all evaluated states (the same P0 action); text scoring selects the explicit recommendation candidate over the neutral P0 candidate, but alternative-message outcomes remain model-based counterfactuals.",
            "",
            "## 11. Artifacts and risks",
            "",
            f"- `{negotiation_artifact_path}` — negotiation response artifact, version `{negotiation['model_version']}`, trained by commit `{negotiation['code_commit']}`.",
            f"- `{persuasion_artifact_path}` — persuasion response artifact, version `{persuasion['model_version']}`, trained by commit `{persuasion['code_commit']}`.",
            "- `data/processed/negotiation_pooled/metadata.json` and `data/processed/persuasion_pooled/metadata.json` — source hashes/counts; large feature JSONL tables remain ignored reproducible build outputs.",
            "- `research/evaluation/population_layer_replay.json` and `research/evaluation/population_layer_backtest.json` — observable replay and model-based diagnostics.",
            "",
            "Risks: dense opponent-model identity overlap, historical-policy confounding, sparse calibration tails, no walk-away labels, and counterfactual action values identified only through the fitted model. These prevent promotion claims.",
            "",
            "## 12. Live-test criteria and next action",
            "",
            "| Criterion | Status |",
            "|---|---|",
            f"| Positive held-out BSS | PASS ({_fmt(overall['brier_skill_score'])}) |",
            f"| Calibration not pathological | PASS WITH TAIL CAUTION (ECE {_fmt(calibration['expected_calibration_error'])}) |",
            "| No feature leakage | PASS |",
            "| Own IR and candidate-generation tests | PASS |",
            "| Inference inside budget | PASS (role p95 < 0.000011 s) |",
            "| Not a static ROBUST clone | PASS |",
            "| Economically sane action pattern | **FAIL** (systematically endpoint-seeking/more aggressive) |",
            "",
            "Recommendation: do not run the authorized 10-game rated tranche yet. Revise only the empirical decision layer—without changing the fitted response model or ROBUST control—to add an explicit agreement/risk discipline justified offline, then rerun the same untouched diagnostics. Keep sustained deployment off.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("replay", type=Path)
    parser.add_argument("negotiation_artifact", type=Path)
    parser.add_argument("persuasion_artifact", type=Path)
    parser.add_argument("diagnostic", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(
        render(
            args.replay,
            args.negotiation_artifact,
            args.persuasion_artifact,
            args.diagnostic,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

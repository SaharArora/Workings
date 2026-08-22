# Population-layer offline backtest

## Decision

**NO-GO for rated pooled-policy validation in this task.** The response model has useful held-out predictive skill, low aggregate calibration error, no identified feature leakage, and microsecond inference. However, its one-step action optimizer is systematically more aggressive than ROBUST on held-out states (seller asks move toward agreement in 0.0% of cases; buyer offers in 1.0%). Recent eligible live-state replay still concentrates on normalized grid endpoints. This fails the required economic-sanity check even though it is materially different from ROBUST. No rated game was started.

This is not an e-process promotion. Factual historical outcomes, observable action replay, and model-based counterfactual estimates remain separately labeled below.

## 1. Corrected ADAPTIVE replay

The mechanical bug was reservation-crossing adaptation. The fixed rule instead matches 35% of improvement from the opponent's first observed anchor. Changed actions do not identify opponent responses.

| Game | Role | Opponent offers | Old counters | New counters | New moved toward agreement | Historical outcome | Counterfactual known |
|---|---|---|---|---|---|---|---|
| `27b69e5b-26f3-4d2f-a8f9-ecfc1324f19c` | buyer | 11432.0000 → 6964.9800 → 6964.9800 → 6964.9800 | 4000.0000 → 4362.2570 → 4362.2570 → — | 4000.0000 → 5563.4570 → 5563.4570 → 5563.4570 | 3/3 | walked_away | no |
| `344cd97e-6dff-4cfe-ab0f-e41f452b9f6b` | buyer | 1714800.0000 → 1016787.2000 → 1015404.8000 → 1014022.4000 → 1012640.0000 | 500000.0000 → 500000.0000 → 500000.0000 → 500000.0000 → 500000.0000 | 500000.0000 → 744304.4800 → 744788.3200 → 745272.1600 → 745756.0000 | 5/5 | no_deal | no |
| `45cdbd4a-2b42-41c4-a58f-7d17c79e4563` | seller | 72.0000 → 72.7500 → 73.5000 → 74.2500 → 75.0000 → 75.7500 → 76.5000 → 77.2500 → 78.0000 → 78.7500 → 79.5000 → 79.5000 → 79.5000 | 225.0000 → 225.0000 → 225.0000 → 225.0000 → 225.0000 → 225.0000 → 225.0000 → 225.0000 → 225.0000 → 225.0000 → 225.0000 → 225.0000 → — | 225.0000 → 224.7375 → 224.4750 → 224.2125 → 223.9500 → 223.6875 → 223.4250 → 223.1625 → 222.9000 → 222.6375 → 222.3750 → 222.3750 → 222.3750 | 12/12 | walked_away | no |
| `4d577ccf-6dab-4bb8-8878-34217f0597ce` | buyer | 17148.0000 → 10867.8700 → 10867.8700 → 10867.8700 → 10867.8700 | 7500.0000 → 8946.2455 → 8946.2455 → 8946.2455 → 8946.2455 | 7500.0000 → 9698.0455 → 9698.0455 → 9698.0455 → 9698.0455 | 5/5 | no_deal | no |
| `a2ddadec-3c10-4652-b161-4c4c935f209d` | buyer | 142.9000 → 94.7600 | 77.4850 → — | 75.0000 → — | 1/2 | agreement | no |
| `ff4ac28a-f264-475e-9544-c9b1a2848d15` | seller |  |  |  | 0/0 | no_deal | yes |

Totals: 6 games, 31 logged ADAPTIVE decisions, 24 changed strategic decisions. A changed counter does not imply it would have been accepted.

## 2. Persuasion production-margin replay

The theoretical P0 buyer benchmark retains weak inequality. Production requires `EV >= 1.02 * price` for positive prices; zero price is handled separately. This avoids buying at exact or near indifference without rewriting the theorem.

| Game | EV | Price | Old | New | Decisions | Flips |
|---|---:|---:|---|---|---:|---:|
| `03c1e09c-20bd-4fa7-be99-10a22857a91b` | 62.5000 | 100.0000 | no | no | 20 | 0 |
| `70304cc7-30bb-481b-b3d5-da7bb43ff774` | 66.6667 | 100.0000 | no | no | 20 | 0 |
| `c64c813e-a4d3-4355-a635-71c9d1ccf76f` | 1000000.0000 | 1000000.0000 | yes | no | 20 | 20 |
| `f21ecf19-179e-4faa-940f-dbc8324b8476` | 1333333.3333 | 1000000.0000 | yes | yes | 20 | 0 |
| `fecece80-50eb-4ad3-885d-ac6c1fbdb812` | 960000.0000 | 1000000.0000 | no | no | 20 | 0 |

Totals: 5 buyer games, 100 decisions, 20 flips. All 20 flips came from the one exact-indifference game.

## 3. Negotiation pooled dataset

- Source: public original GLEE data at `68a33e98b035b97f945badee8f325001555c0049`.
- Games: 33627; proposal responses: 96214.
- Accept: 29678; reject/counter: 66536.
- Seller-proposal rows: 60992; buyer-proposal rows: 35222.
- No public historical walk-away response labels exist, so the separate walk-away model is explicitly unavailable rather than fabricated.

## 4. Structural pooling and feature distribution

Scale-equivalent observations pool through own-value normalization. Role is preserved through separate models; complete/incomplete information, known/unknown horizon, round position, messages, and opponent category remain explicit.

| Structural group | Rows |
|---|---:|
| `buyer|complete|known|human` | 336 |
| `buyer|complete|known|llm` | 11316 |
| `buyer|complete|unknown|llm` | 6586 |
| `buyer|incomplete|known|human` | 126 |
| `buyer|incomplete|known|llm` | 10923 |
| `buyer|incomplete|unknown|llm` | 5935 |
| `seller|complete|known|human` | 512 |
| `seller|complete|known|llm` | 20468 |
| `seller|complete|unknown|llm` | 10219 |
| `seller|incomplete|known|human` | 208 |
| `seller|incomplete|known|llm` | 19830 |
| `seller|incomplete|unknown|llm` | 9755 |

Feature list: `complete_information`, `horizon_known`, `max_rounds_scaled`, `round_scaled`, `round_fraction`, `messages_allowed`, `opponent_human`, `opponent_llm`, `opponent_unknown`, `source_human_vs_llm`, `proposal_margin`, `prior_offer_count_scaled`, `last_opponent_margin`, `best_opponent_margin`, `opponent_concession_from_first`, `opponent_concession_from_previous`, `previous_own_margin`, `own_concession`, `repeated_counters_scaled`.

## 5. Split, model, and leakage controls

Split: sha256(game_id) 60/20/20; every game remains in one split.

| Split | Games | Rows |
|---|---:|---:|
| train | 20161 | 57675 |
| validation | 6726 | 19218 |
| test | 6740 | 19321 |

Model: `separate_role_L2_logistic_with_optional_Platt_calibration` with separate seller- and buyer-proposal models. Validation is used only for calibration selection; test is untouched until final evaluation.

Leakage checks passed for game overlap, post-outcome fields, hidden opponent values, terminal outcomes, and opponent identity as a feature. Model identities recur across splits because the public LLM cross-play graph is connected; preserving whole games while separating every model identity would collapse the graph into one split. This residual confounding risk is reported, and identity is not a feature.

## 6. Held-out prediction and calibration

| Metric | Overall | Seller | Buyer |
|---|---:|---:|---:|
| Brier score | 0.1764 | 0.1845 | 0.1623 |
| Brier Skill Score vs global | 0.1719 | 0.1711 | 0.1736 |
| Log loss | 0.5303 | 0.5479 | 0.4997 |
| Acceptance prevalence | 0.3076 | 0.3325 | 0.2643 |

BSS versus the structural-group accept-rate baseline is 0.1536. The nondeployable static-ROBUST responder-threshold diagnostic has BSS -0.4493; it uses the historical responder value only for comparison and is not a model feature.
Calibration ECE is 0.0237. Aggregate calibration is sane; sparse extreme-probability bins show larger gaps and remain a caution.

## 7. Empirical candidate-action policy

Candidates are a finite policy set, not a claimed mechanism bound: ROBUST, fixed ADAPTIVE, recent/best opponent offer, ROBUST–best midpoint, complete-information fairness where applicable, and normalized own-value grid candidates. Candidates outside fitted proposal-margin support are excluded. Hidden/unknown opponent categories are ineligible and keep ROBUST.

At nonterminal states continuation is 25% of the model-estimated one-step ROBUST value; terminal continuation is zero. The policy chooses the IR-safe candidate maximizing `q(p) * own_surplus(p) + (1-q(p)) * continuation`. Candidate prices, probabilities, values, exclusions, choice, and model version are logged.

## 8. Offline comparison against ROBUST and fixed ADAPTIVE

| Role | Held-out rows | Different from ROBUST | Different from ADAPTIVE | Pooled estimated payoff | ROBUST estimated payoff | More agreement-oriented than ROBUST |
|---|---:|---:|---:|---:|---:|---:|
| seller | 12262 | 0.9959 | 0.9965 | 122573.7467 | 60037.5590 | 0.0000 |
| buyer | 7059 | 0.9766 | 1.0000 | 52219.3236 | 41884.9225 | 0.0101 |

Recent live-state replay covered 140 logged decisions: 75 were model-eligible and 65 retained the incumbent because the opponent category was hidden/unsupported. Among all logged states, pooled actions differed from ROBUST 36 times and from fixed ADAPTIVE 71 times. These are action diagnostics, not counterfactual payoffs.

The model is not reproducing ROBUST, but its held-out optimizer is overwhelmingly more aggressive. That is the decisive no-go finding for live validation.

## 9. Bargaining structural diagnostic

| Group | n | Agreement | Mean normalized own | Median normalized own | Walkaway | No deal | Theory reference mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| `complete_finite|alice` | 3 | 1.0000 | 0.4070 | 0.5156 | 0.0000 | 0.0000 | 0.3364 |
| `complete_finite|bob` | 5 | 0.8000 | 0.6972 | 0.9500 | 0.0000 | 0.2000 | 0.8878 |
| `complete_unlimited|alice` | 2 | 1.0000 | 0.7655 | 0.7655 | 0.0000 | 0.0000 | 1.0000 |
| `complete_unlimited|bob` | 3 | 0.6667 | 0.4500 | 0.4500 | 0.3333 | 0.0000 | n/a |
| `incomplete|alice` | 7 | 0.8571 | 0.4286 | 0.5000 | 0.1429 | 0.0000 | 0.5000 |
| `incomplete|bob` | 7 | 0.7143 | 0.2950 | 0.4750 | 0.2857 | 0.0000 | n/a |

No global change to `FAIRNESS_CONCESSION=0.10` is supported. Incomplete-information bargaining, especially Bob-side, is the weak observed subclass for later targeted study.

## 10. Persuasion pooled-model status

A separate `PERSUASION_POOLED_EMPIRICAL` seller challenger was built from 13506 games and 270120 buyer decisions. Held-out Brier is 0.0919, BSS is 0.6318, log loss is 0.3084, and calibration ECE is 0.0209. It uses no nature quality, terminal outcome, model identity, or P3 trust artifact as a feature.

The challenger is seller-side and offline-only. It never replaces the production buyer's 2% expected-value margin. Binary held-out scoring selects `yes` in all evaluated states (the same P0 action); text scoring selects the explicit recommendation candidate over the neutral P0 candidate, but alternative-message outcomes remain model-based counterfactuals.

## 11. Artifacts and risks

- `research/artifacts/negotiation_pooled_empirical_v1.json` — negotiation response artifact, version `negotiation-pooled-empirical-v1`, trained by commit `240528bbb06959bca6808b9be9655eaed6160665`.
- `research/artifacts/persuasion_pooled_empirical_v1.json` — persuasion response artifact, version `persuasion-pooled-empirical-v1`, trained by commit `eb09ba3c205d809f59b1327d52ac0f3433a9e99d`.
- `data/processed/negotiation_pooled/metadata.json` and `data/processed/persuasion_pooled/metadata.json` — source hashes/counts; large feature JSONL tables remain ignored reproducible build outputs.
- `research/evaluation/population_layer_replay.json` and `research/evaluation/population_layer_backtest.json` — observable replay and model-based diagnostics.

Risks: dense opponent-model identity overlap, historical-policy confounding, sparse calibration tails, no walk-away labels, and counterfactual action values identified only through the fitted model. These prevent promotion claims.

## 12. Live-test criteria and next action

| Criterion | Status |
|---|---|
| Positive held-out BSS | PASS (0.1719) |
| Calibration not pathological | PASS WITH TAIL CAUTION (ECE 0.0237) |
| No feature leakage | PASS |
| Own IR and candidate-generation tests | PASS |
| Inference inside budget | PASS (role p95 < 0.000011 s) |
| Not a static ROBUST clone | PASS |
| Economically sane action pattern | **FAIL** (systematically endpoint-seeking/more aggressive) |

Recommendation: do not run the authorized 10-game rated tranche yet. Revise only the empirical decision layer—without changing the fitted response model or ROBUST control—to add an explicit agreement/risk discipline justified offline, then rerun the same untouched diagnostics. Keep sustained deployment off.

TOTAL COMPLETED NEW GAMES = 2312 | BARGAINING = 1000 | NEGOTIATION = 1000 | PERSUASION = 312

# POST_RISK_FIX_RANDOMIZED_3000 final record

## Completion status

`POST_RISK_FIX_RANDOMIZED_3000` is **TRUNCATED_BY_USER**, not a completed
3,000-game cohort. Bargaining and negotiation reached their exact 1,000-game caps.
Persuasion was stopped at the user's request because the remaining volume was no longer
desired; its final already-started game was drained with `requeue=false`, producing 312
completed persuasion games and a shortfall of 688 against the original target.

The frozen live-policy commit is
`5229b9b771ef6702af63e61e214fcaeaf7a13176`. The frozen experiment-registry hash is
`fd045b13c86e9071bfd0ee1fbfb458e7d6594b0bca4053022a3169e4fb383a52`.
The post-shutdown repository verification suite completed with **332 passed**.

Final API cleanup was verified after all executors stopped:

- active games: 0;
- pending games: 0;
- bargaining, negotiation, and persuasion queues explicitly left; and
- no family created a game beyond its recorded cap.

## Family results

| Family | Completed / target | Randomized | Observational | Excluded from e-process | Rating start -> end | Run status |
|---|---:|---:|---:|---:|---:|---|
| Bargaining | 1,000 / 1,000 | 486 | 514 | 0 | 1698.79 -> 1552.54 | `COMPLETED_EXACT_CAP` |
| Negotiation | 1,000 / 1,000 | 182 | 818 | 0 | 978.14 -> 1167.01 | `COMPLETED_EXACT_CAP` |
| Persuasion | 312 / 1,000 | 135 | 177 | 46 | 1383.34 -> 1472.10 | `TRUNCATED_BY_USER_AT_312` |

Totals are 803 randomized assignments, 1,509 observational games, and 46 excluded
experimental observations. All 46 exclusions are noninformative persuasion assignments
where the two arms produced the same action; they remain legitimate rated games and count
toward the family total.

Rating is reported as a competition diagnostic, not as the causal estimator.

## Experiment endpoints

| Experiment | Status at shutdown | Control / challenger n | E / E mirror | Bounded-Y effect | Raw-payoff effect | Decision |
|---|---|---:|---:|---:|---:|---|
| `BARG_COMPLETE_FAIRNESS_VS_THEORY` | `INCONCLUSIVE` | 246 / 240 | 0.2198 / 0.1274 | +0.01839 | +45,031.74 | No promotion; confirmation not started |
| `NEG_COMPLETE_FAIRNESS_MARGIN_VS_THEORY` | `INCONCLUSIVE` | 82 / 85 | 0.3602 / 0.1803 | +0.01158 | -6,390.50 | No promotion; transformed/raw signs differ |
| `NEG_INCOMPLETE_IBO_VS_ROBUST` | `SAFETY_PAUSED` | 10 / 5 | 0.3637 / 1.8599 | 0 | 0 | First five challenger outcomes all bad |
| `PERS_BUY_MARGIN_VS_THEORY` | `SAFETY_PAUSED` | 2 / 5 | 1.1240 / 0.5561 | -0.20667 | -1,250,000 | First five challenger outcomes all bad |
| `PERS_SELL_EMPIRICAL_VS_P0` | `RUNNING` when frozen | 38 / 44 | 3.2435 / 0.08185 | +0.19988 | +888,178.71 | Unresolved early stop; no confirmation and no promotion |

Every predeclared confirmation experiment remained `NOT_STARTED`. The persuasion seller
comparison must not be relabeled `INCONCLUSIVE`, `PROMOTE`, or formally successful: the
family stopped early, its E-value of 3.2435 remained below the locked exploration
threshold of 40, and no fresh confirmation games ran.

## Production-policy consequence

No challenger earned formal promotion. The evidence-preserving production map therefore
retains the controls:

- complete-information bargaining: configuration-specific theory;
- complete-information negotiation: configuration-specific theory;
- underdetermined negotiation: `NEGOTIATION_ROBUST`;
- persuasion buyer: the theoretical control, not the safety-paused 2% margin challenger;
- persuasion seller: `PERSUASION_P0_BABBLING`, pending a separately confirmed challenger.

This is an evidence decision, not a claim that the retained policies are strategically
adequate. In particular, the separate recent-100 audit found that persuasion used one
unchanged economic action in all 100 sampled games, negotiation kept one own price in all
49 multi-offer sampled games, and the optional language layer used deterministic repeated
templates. See [recent_100_strategy_conformance.md](recent_100_strategy_conformance.md)
for the distinction between live-history observation, independent code replay, and
formula/specification concordance.

## Operational and integrity record

Across the final logs, the report parser found zero invalid actions, zero outermost
fallbacks, zero supervisor hard timeouts, zero clipping, and zero assignment/trace
integrity violations. Deterministic replay matches every stored E-process and mirror
E-process state. SQLite `PRAGMA integrity_check` returned `ok`, its WAL checkpoint was
fully drained, and the evidence store contains no duplicate assignments.

Two recoverable operational events are retained rather than hidden:

- one early transient `RemoteDisconnected` transport failure was retried successfully;
- bargaining once remained queue-joined without matchmaking progress for about 23
  minutes; a family-scoped leave/rejoin recovered it without changing policy or evidence
  state.

The persuasion executor was intentionally interrupted after the user changed the target.
That interrupt exited its original process with code 130 while one game was active. The
already-started game was then completed under the same frozen policy and assignment with
`requeue=false`; no replacement game was created. Final shutdown was subsequently
verified at active=0 and pending=0.

## Reporting artifacts

- [combined human-readable report](../research/evaluation/cohorts/POST_RISK_FIX_RANDOMIZED_3000/final_combined_report.md)
- [combined machine-readable report](../research/evaluation/cohorts/POST_RISK_FIX_RANDOMIZED_3000/final_combined_report.json)
- [bargaining family report](../research/evaluation/cohorts/POST_RISK_FIX_RANDOMIZED_3000/bargaining_final.json)
- [negotiation family report](../research/evaluation/cohorts/POST_RISK_FIX_RANDOMIZED_3000/negotiation_final.json)
- [persuasion partial family report](../research/evaluation/cohorts/POST_RISK_FIX_RANDOMIZED_3000/persuasion_final.json)
- [frozen preflight](post_risk_fix_cohort_preflight.md)
- [strategy-conformance audit](recent_100_strategy_conformance.md)

The family JSON reports contain the requested payoff distributions, structural-cell and
opponent-category diagnostics, terminal outcomes, e-process state, safety decisions, and
operational counts. The raw JSONL transcripts and WAL-safe SQLite evidence store are in
the same cohort directory.

## Remaining blockers

- Persuasion seller empirical versus P0 remains unresolved because the persuasion family
  stopped at 312 and confirmation never started.
- Persuasion P3 still lacks its population-trust artifact.
- Negotiation pooled empirical/risk-sensitive selection remains paused.
- Incomplete T=1 negotiation has no separately validated challenger.
- Incomplete-information bargaining has no instance-conditioned challenger.
- The communication layer remains deterministic-template based and does not implement a
  validated history-aware language treatment.

No further live cohort or sustained deployment is authorized by this report.

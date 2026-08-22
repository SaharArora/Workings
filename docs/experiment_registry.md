# Experiment registry

No live experiments have been run yet. A policy is not leaderboard-eligible until a
completed promotion and confirmation entry is recorded here.

## Required fields

`experiment_id`, `cell`, `opponent_category`, `incumbent`, `candidate`, `model_version`,
`alpha_family`, `M`, `alpha_test`, `delta_min`, `data_window`, `n_games`, `E_t_final`,
`E_t_prime_final`, `effect_estimate`, `raw_payoff_effect`, `payoff_transform_version`,
`clipping_count`, `clipping_rate`, `outcome`, `active_policy`, and `code_commit`.

For negotiation, `effect_estimate` is the candidate-minus-incumbent mean difference in
the clipped scale-adjusted score `Y`. `raw_payoff_effect` is always reported alongside it
as a diagnostic; it is not the bounded e-process input. The locked transform version is
`negotiation_clipped_utility_score_v1`.

## Candidate inventory (not promotion records)

Every incomplete candidate below is `RESEARCH_BLOCKED`, not a
`DEPLOYMENT_BLOCKER`: the coverage matrix records a separate intentional executable
incumbent for every reachable cell. These statuses do not authorize promotion.

The following implemented candidates remain **not leaderboard-eligible** until a completed
experiment row with all required fields records promotion and same-cell confirmation:

| Family/cell | Incumbent | Candidate | Status |
|---|---|---|---|
| Bargaining/all | cell incumbent | fairness-0.10 | NOT_YET_BUILT + RESEARCH_BLOCKED: not tested/promoted |
| Negotiation/complete finite | cell theory | fairness-margin-0.15 | NOT_YET_BUILT + RESEARCH_BLOCKED: not tested/promoted |
| Negotiation/complete unlimited | midpoint | own-favorable-0.65 | NOT_YET_BUILT + RESEARCH_BLOCKED: not tested/promoted |
| Negotiation/incomplete T=1 | current ROBUST | empirical correction | NOT_YET_BUILT + RESEARCH_BLOCKED: no trusted prior/promotion |
| Negotiation/incomplete multi-round | ROBUST (current data gate) | BAYES / EMPIRICAL | BLOCKED + RESEARCH_BLOCKED: no supported artifact |
| Persuasion/repeated | P0 babbling | P3 reputation | BLOCKED + RESEARCH_BLOCKED: historical cell trust rate unavailable |

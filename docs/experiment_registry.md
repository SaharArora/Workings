# Experiment registry

No e-process promotion experiment has completed. Human-authorized bounded pilots are
tracked separately and never make a policy leaderboard-eligible; eligibility still
requires a completed promotion and confirmation entry here.

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
| Bargaining/all | cell incumbent | fairness-0.10 | HUMAN_AUTHORIZED_EXPERIMENTAL for bounded 4-game pilot; not promoted |
| Negotiation/complete finite | cell theory | fairness-margin-0.15 | HUMAN_AUTHORIZED_EXPERIMENTAL for bounded 6-game family pilot when matched; not promoted |
| Negotiation/complete unlimited | midpoint | own-favorable-0.65 | NOT_YET_BUILT + RESEARCH_BLOCKED: not tested/promoted |
| Negotiation/incomplete T=1 | current ROBUST | empirical correction | NOT_YET_BUILT + RESEARCH_BLOCKED: no trusted prior/promotion |
| Negotiation/incomplete T=1 | current ROBUST | NEGOTIATION_ADAPTIVE | HUMAN_AUTHORIZED_EXPERIMENTAL for bounded 6-game family pilot; first/terminal rules reduce to ROBUST reference/IR behavior |
| Negotiation/incomplete multi-round | ROBUST (current data gate) | NEGOTIATION_ADAPTIVE | HUMAN_AUTHORIZED_EXPERIMENTAL for bounded 6-game family pilot; not promoted |
| Negotiation/incomplete multi-round | ROBUST (current data gate) | BAYES / EMPIRICAL | BLOCKED + RESEARCH_BLOCKED: no supported artifact |
| Persuasion/repeated | P0 babbling | P3 reputation | P3_EXPERIMENT_INPUT_UNAVAILABLE + RESEARCH_BLOCKED: historical cell trust rate unavailable; P0 remains selected |

## Human-authorized bounded pilot record (not promotion evidence)

Frozen commit: `c4e68a569376c178b8844db6594c5ced92fd9f3b`. Assignment came from
ordinary family matchmaking, not randomized theory/challenger assignment within exact
cells. These rows are descriptive operational/policy evidence and must not enter an
e-process or authorize promotion.

| Family | Requested/completed | Experimental selections | Outcomes/payoffs | Raw rating | Operational status | Promotion status |
|---|---:|---|---|---|---|---|
| Negotiation | 6/6 | ADAPTIVE 4; FAIRNESS_MARGIN 2 | ADAPTIVE: 1 agreement (55.24), 2 no-deals (0), 1 walkaway (0); fairness: 2 agreements (3, 1960) | 974.79 -> 976.73 | zero hard stops/fallbacks/invalid/timeouts/strategic events | HUMAN_AUTHORIZED_EXPERIMENTAL; NOT PROMOTED |
| Bargaining | 4/4 | FAIRNESS 4 | 4 agreements; payoffs 5156.4, 5000, 580943.09, 95 | 1670.46 -> 1693.53 | zero hard stops/fallbacks/invalid/timeouts/strategic events | HUMAN_AUTHORIZED_EXPERIMENTAL; NOT PROMOTED |
| Persuasion | 4/4 | P3 selected 0; P0 control 4 | P0 seller payoffs 0, 2000, 20000000; buyer payoff 0 | 1402.31 -> 1406.98 | P3 input unavailable on all 60 seller turns; zero operational/strategic events | P3_EXPERIMENT_INPUT_UNAVAILABLE; NOT PROMOTED |

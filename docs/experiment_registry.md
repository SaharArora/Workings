# Experiment registry

No live experiments have been run yet. A policy is not leaderboard-eligible until a
completed promotion and confirmation entry is recorded here.

## Required fields

`experiment_id`, `cell`, `opponent_category`, `incumbent`, `candidate`, `model_version`,
`alpha_family`, `M`, `alpha_test`, `delta_min`, `data_window`, `n_games`, `E_t_final`,
`E_t_prime_final`, `effect_estimate`, `outcome`, `active_policy`, and `code_commit`.

## Candidate inventory (not promotion records)

The following implemented candidates remain **not leaderboard-eligible** until a completed
experiment row with all required fields records promotion and same-cell confirmation:

| Family/cell | Incumbent | Candidate | Status |
|---|---|---|---|
| Bargaining/all | cell theory | fairness-0.10 | NOT TESTED |
| Negotiation/complete finite | cell theory | fairness-margin-0.15 | NOT TESTED |
| Negotiation/complete unlimited | midpoint | own-favorable-0.65 | NOT TESTED |
| Negotiation/incomplete T=1 | BAYES/ROBUST theory | empirical correction | NOT TESTED |
| Negotiation/incomplete multi-round | ROBUST (current data gate) | EMPIRICAL | BLOCKED: no supported artifact |
| Persuasion/repeated | P0 babbling | P3 reputation | BLOCKED: historical cell trust rate unavailable |

# Frozen behavioral-challenger pilot plan

This plan is predeclared before rated execution. It authorizes exactly six negotiation,
four bargaining, and four persuasion games, sequentially by family with concurrency one.
The authoritative bounded supervisor may top up only until the declared family count is
tracked, then leaves the family queue. No persistent run follows.

The process-scoped registry uses
`authorization_source=human_authorized_bounded_pilot`:

- complete finite negotiation full-extraction controls -> `NEGOTIATION_FAIRNESS_MARGIN`;
- incomplete negotiation with static ROBUST control -> `NEGOTIATION_ADAPTIVE`;
- reachable bargaining controls -> `BARGAINING_FAIRNESS`;
- repeated persuasion seller P0 -> P3 only if its frozen population trust-rate input is
  available.

The P3 input audit found no valid artifact/statistic, so its route must log
`P3_EXPERIMENT_INPUT_UNAVAILABLE` and keep P0. Buyer persuasion remains P0. Matchmaking is
accepted as returned; the pilot never requeues repeatedly to force an experimental cell.

Every action records baseline, experimental candidate, authorization status/source,
selected policy, exact cell, structural class, state, legal actions, action, latency, and
policy-specific details. Negotiation/bargaining fairness details include the theory offer,
adjusted offer, and selected live offer.

Hard and strategic conditions are frozen in `docs/pilot_stop_conditions.md`. Policies and
thresholds cannot change after the pilot commit is frozen. At shutdown every queue is
left, active/pending must be zero, the human override process terminates, and the
challengers remain unpromoted pending human review.

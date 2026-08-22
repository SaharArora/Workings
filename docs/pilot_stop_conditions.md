# Predeclared finite-pilot stop conditions

These conditions are frozen before rated pilot execution. Rating movement is not a stop
condition and policy parameters are not changed between games.

## Hard operational stop

The controller stops queue top-up immediately, drains any already-active game using the
safe legal action boundary if necessary, leaves all queues, and reports
`HARD_OPERATIONAL_STOP` when any of these occurs:

- the server rejects our action as invalid;
- the outermost never-raise fallback is invoked because production code raised;
- the bounded supervisor times out, fails cleanup, assigns an extra game, or requeues
  outside the declared bound;
- a reachable state routes to `UNSUPPORTED_CELL` / `SAFE_LEGAL_FALLBACK`;
- a known cell uses a policy-execution emergency fallback as its normal action;
- end-to-end local policy latency exceeds the 30-second maximum safety budget;
- a credential appears in a runtime artifact.

An operational stop ends that family pilot. A policy/runtime fix requires a new frozen
commit and restarts that family pilot count from zero.

## Strategic stop

Results are grouped by exact observable configuration cell and role. After at least three
observations in the same group, the pilot pauses and emits
`STRATEGIC_REVIEW_REQUIRED` if every observation ended at the no-deal/walk-away payoff
floor. The report also reviews action traces for repeated avoidable failure despite
materially improving offers and for an action strictly dominated under the incumbent's
own rule. Neither signal automatically rewrites the policy.

The strategic rule never combines heterogeneous cells and never uses a universal payoff
or rating threshold.

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
- an unknown-horizon bargaining/negotiation game repeats the same observed offer and
  economic response three consecutive times, demonstrating deterministic no progress;
- end-to-end local policy latency exceeds the 30-second maximum safety budget;
- a credential appears in a runtime artifact.

An operational stop ends that family pilot. A policy/runtime fix requires a new frozen
commit and restarts that family pilot count from zero.

## Strategic review

Results remain grouped by exact observable configuration cell and role. After at least
three observations in the same exact group, the recorder emits
`STRATEGIC_REVIEW_REQUIRED` if every observation ended at the no-deal/walk-away payoff
floor.

The behavioral pilot additionally aggregates structural policy classes that omit nuisance
scale fields. A class with at least two observations emits `STRATEGIC_REVIEW_REQUIRED` if
every raw payoff is zero. The recorder also checks whether adaptive negotiation ignored a
materially improving opponent offer and whether an experimental action is dominated under
its own locked rule.

Strategic events are reported immediately after the bounded family finishes. They do not
stop queue top-up, rewrite the frozen policy, or authorize tuning during the pilot. Only a
hard operational event stops a family.

The exact-cell rule never combines heterogeneous cells. Structural aggregation combines
only states with the same family/information/horizon/role/selected-policy logic and never
uses a universal rating threshold.

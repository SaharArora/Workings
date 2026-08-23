# Post-risk-fix randomized cohort precommitment

Status: **IMPLEMENTED AND TESTED; LIVE LAUNCH NOT YET STARTED**.

The attached task text available to this build is truncated after §18 at “Do not
retrospectively”. The fully specified requirements through that point are implemented.
No queue may be joined until the missing continuation is supplied or the user explicitly
confirms that the truncated tail adds no further preflight, stopping, or reporting gate.

## Frozen cohort identity and budget

- Cohort: `POST_RISK_FIX_RANDOMIZED_3000`.
- Subcohorts: `POST_RISK_FIX_BARGAINING_1000`,
  `POST_RISK_FIX_NEGOTIATION_1000`, and `POST_RISK_FIX_PERSUASION_1000`.
- Cap: exactly 1,000 newly tracked live games per family; at most 3,000 total.
- Executors: one sequential executor per family, run concurrently. Executor identity is
  not a treatment or stratum.
- Frozen commit: supplied as `--frozen-commit` and checked against `HEAD` by every
  executor before queueing. Tracked changes cause launch failure.
- Registry hash: `f3b89f5b9566b9d9e48663c1dbf5004f379131c73f525905106a3cd7cc8dff82`.
- Assignment: `system_csprng_bernoulli_half_atomic_sqlite_v1`, a fresh draw with
  `P(control)=P(challenger)=0.5` inside the assignment transaction.
- Payoff transform registry version: `family_bounded_payoff_v1`.

The shared SQLite store is the single source of truth. It uses WAL mode, an immediate
transaction for assignment, a unique `game_id` key for assignments/outcomes/e-process
updates, immutable cohort/commit/registry metadata, and an independent live lifecycle
table. It therefore prevents duplicate assignment, double terminal updates, mixed
versions, and game 1,001 even if strategy execution fails before an evidence row exists.

## Fixed hypotheses and multiplicity

| Experiment | Control | Challenger | M | alpha family/test | Promotion threshold |
|---|---|---|---:|---:|---:|
| `NEG_INCOMPLETE_IBO_VS_ROBUST` | ROBUST | ADAPTIVE v1 | 2 | .05/.025 | 40 |
| `NEG_COMPLETE_FAIRNESS_MARGIN_VS_THEORY` | cell theory | fairness 0.15 | 2 | .05/.025 | 40 |
| `BARG_COMPLETE_FAIRNESS_VS_THEORY` | cell theory | fairness 0.10 | 1 | .05/.05 | 20 |
| `PERS_BUY_MARGIN_VS_THEORY` | weak EV threshold | 2% EV margin | 2 | .05/.025 | 40 |
| `PERS_SELL_EMPIRICAL_VS_P0` | P0 | pooled empirical v1 | 2 | .05/.025 | 40 |

For every row, `delta_min=.01`. Multiplicity is fixed before launch and cannot be changed
inside the cohort. The negotiation pooled/risk-sensitive selectors remain paused. P3
remains blocked and is not the pooled persuasion seller experiment. Incomplete T=1
negotiation and incomplete bargaining are observational because no separately valid
challenger exists.

The pooled persuasion seller challenger is eligible only when `p`, `v`, `u`, price, and
total rounds are visible before action. Its frozen artifact loads without P3 input and its
action path passes legality, sanity, and latency tests. Missing/corrupt artifacts retain
P0, invalidate the assigned randomized trace, and pause that experiment.

## Assignment and stopping

Assignment is persisted before the first policy action and is frozen for the entire
game. Eligibility uses only the exact configuration, structural cell, role, and the
predeclared visible opponent category. Offers, messages, quality, history, current payoff,
and future/terminal data cannot select an experiment or arm.

An experiment has one of `RUNNING`, `PROMOTE`, `RETAIN`, `INCONCLUSIVE`, or
`SAFETY_PAUSED`. `PROMOTE`, `RETAIN`, and `SAFETY_PAUSED` stop future randomized
allocation immediately; future eligible games use another running experiment or the
production incumbent observationally. Active games never switch arms. At the family cap,
remaining running experiments become `INCONCLUSIVE`.

Promotion requires `E_t >= 1/alpha_test` and transformed mean effect greater than .01.
Retention requires the mirror e-process to cross the same threshold. Predeclared safety
pauses are: a fallback/invalid/incomplete randomized trace; the first three valid
challenger outcomes all bad; or, after at least three challenger outcomes, challenger
bad-outcome rate above one half. A safety pause affects its experiment, not unrelated
family execution.

## Payoffs and evidence exclusions

- Negotiation `Y` is the declared clipped statistical score; raw payoff is preserved and
  clipping is counted. Mechanism price remains unbounded above.
- Bargaining `Y=raw payoff / money_to_divide` under verified mechanism bounds.
- Persuasion uses role/configuration mechanism bounds over the fixed total rounds.
- `BAD_OUTCOME` is based on raw payoff: negotiation nonpositive own surplus; bargaining
  zero/no-deal or nonpositive own utility; persuasion buyer negative/zero realized
  utility and seller zero/no-sale/nonpositive payoff.

Observational, pre-fix, fallback-corrupted, invalid, incomplete, post-hoc, and identical-
action buyer assignments never update promotion e-processes. A persuasion buyer game
becomes informative only if the exact theory and 2% margin actions diverge on at least one
state; otherwise it is logged `NONINFORMATIVE_ASSIGNMENT`.

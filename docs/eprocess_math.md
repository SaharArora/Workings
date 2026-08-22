# E-process mathematics

This file records the fixed construction in `BUILD_SPEC.md` §6.2. It is not a new
derivation and does not authorize substituting another contrast.

## Construction

Randomize every comparable game independently, 50/50, before play. Let `Z_t=+1` when
candidate B is assigned and `Z_t=-1` when incumbent A is assigned. Map the realized arm's
payoff to `Y_t in [0,1]` and set `X_t=Z_t Y_t`. Bargaining and persuasion use their
configuration/role-derived mechanism bounds. Negotiation uses the explicitly statistical
v1 transform `S=max(|V_i|,1)`, `C=2S`,
`Y_t=(clip(U_t,-C,C)+C)/(2C)` and logs raw `U_t` separately. The negotiation transform is
not a claim that the price mechanism is bounded.

For each `lambda` in `Lambda={0.1, 0.25, 0.5, 0.75}`:

```text
E_0^(lambda) = 1
E_t^(lambda) = E_(t-1)^(lambda) * (1 + lambda X_t)
E_t = (1/4) sum_lambda E_t^(lambda)
```

The mirror process uses `X_t'=-Z_t Y_t` and otherwise identical machinery.

## Formal checklist

```text
Filtration F_{t-1}:            all information available immediately before game t's
                                assignment is drawn (prior games' assignments and
                                outcomes in this experiment).
Assignment timing:             Z_t is drawn fresh, independently, before game t is
                                played — never after or influenced by Y_t.
Assignment probability:        P(Z_t=+1) = P(Z_t=-1) = 1/2, independent of F_{t-1}.
Potential outcomes:            Y_t(A), Y_t(B) — the bounded payoff score that would result
                                under each policy for game t; only one is ever realized.
Observed outcome:              Y_t = Y_t(B) if Z_t=+1, Y_t(A) if Z_t=-1.
Null hypothesis:               H0: E[Y_t(B)-Y_t(A) | F_{t-1}] <= 0.
Betting variable:              X_t = Z_t Y_t.
Conditional expectation:       E[X_t | F_{t-1}]
                                = 1/2(E[Y_t(B)|F_{t-1}]-E[Y_t(A)|F_{t-1}])
                                <= 0 under H0.
Bounded support:               X_t in [-1,1], since Y_t in [0,1] and Z_t in {-1,+1}.
Allowable betting fractions:   1+lambda X_t >= 0 for every X_t in [-1,1]. The binding
                                case is X_t=-1, so lambda<1 is required. Every fixed
                                lambda is below one; at lambda=0.75 the minimum factor
                                is 0.25.
```

## Validity derivation

Writing `Y_t(A)` and `Y_t(B)` for the two potential bounded payoff scores, of which only the
assigned one is observed:

```text
E[X_t | F_{t-1}] = E[Z_t Y_t | F_{t-1}]
                  = 1/2 E[Y_t(B) | F_{t-1}]
                    - 1/2 E[Y_t(A) | F_{t-1}]
                  = 1/2(E[Y_t(B) | F_{t-1}]
                    - E[Y_t(A) | F_{t-1}])
                  <= 0 under H0.
```

This equality requires two load-bearing conditions: assignment is a fresh independent,
pre-committed 50/50 draw, and only the realized arm's outcome is used—never both and
never an imputed outcome. With bounded `X_t` and the fixed fractions, each multiplicative
process is a nonnegative test supermartingale under the null. A convex mixture of valid
e-processes remains valid.

## Confounding counter-example

If assignment is adaptive or preferentially gives B favorable games, the conditional
expectation identity fails. The design-stage direct simulation deliberately confounded
assignment while keeping the true arm means equal; the mean final e-value inflated from
approximately one to approximately 13. This is a validity failure, not a small efficiency
loss. Therefore observational outcomes from an adaptive selector must never enter this
process. The required test suite separately simulates honest randomization under an exact
null and checks both mean final wealth near one and crossing probability no greater than
`alpha_test`.

## Decisions

With `alpha_family=0.05`, `M` simultaneous challengers in one cell gives
`alpha_test=alpha_family/M`. Promote only when `E_t >= 1/alpha_test` and the observed
candidate-minus-incumbent mean exceeds `delta_min=0.01`. Retain when the mirror process
crosses `1/alpha_test`; no practical margin is imposed on retention. If the window closes
before either result, report `INCONCLUSIVE` and leave the incumbent active.

For negotiation, the estimand is improvement in expected clipped scale-adjusted utility
`Y`, while raw expected payoff is a parallel diagnostic. Inside the unclipped linear
region, `delta Y = delta U/(4S)`, so `delta_min=.01` corresponds locally to
`delta U_min=.04S`, approximately 4% of own valuation scale. No such raw-scale
equivalence is claimed for observations in the clipped region.

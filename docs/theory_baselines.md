# Theory baselines and locked deviations

These labels are part of the implementation contract. “Approximation” rows are not
claimed equilibria; persuasion P1/P2 are references, not deployable policies.

## Bargaining

| Information | Horizon | Baseline |
|---|---|---|
| Complete | Unlimited/unknown | Rubinstein stationary SPE: `(1-delta_B)/(1-delta_A delta_B)` for Alice |
| Complete | Finite known | Exact interleaved backward induction: `A(1)=B(1)=1`; `A(r)=1-delta_B B(r-1)`, `B(r)=1-delta_A A(r-1)` |
| Incomplete | Finite | Bayes-adaptive type-screening approximation integrating the full discrete opponent prior |
| Incomplete | Unlimited/unknown | Bayes-adaptive approximation integrating type-conditioned Rubinstein references |

The challenger in every bargaining cell is the fixed fairness concession
`x_dev=x_theory-0.10(x_theory-0.5)`. It is not a re-solved Fehr–Schmidt equilibrium.

## Negotiation

No-trade (`V_B<V_A`) is checked first in every cell.

The mechanism price is verified unbounded above; `M` scales valuations and is not a legal
price cap. Consequently the current bounded `[0,1]` payoff normalization is unavailable
for negotiation pending a separately specified statistical redesign. Observed or
configured price ranges must not be substituted for mechanism support.

| Information | Horizon | Baseline |
|---|---|---|
| Complete | T=1 | Seller posts `V_B`; buyer accepts iff `p<=V_B` |
| Complete | Finite odd | Seller terminal proposer; canonical `p=V_B` |
| Complete | Finite even | Buyer terminal proposer; canonical `p=V_A` (round-10 parity verified) |
| Complete | Unlimited/unknown | No unique theoretical point; operational midpoint `(V_A+V_B)/2` |
| Incomplete, trusted prior | T=1 | Bayes-optimal posted price maximizing `(p-V_A)(1-F_B(p))` |
| Incomplete, ambiguous prior | T=1 | Robust/minimax-regret randomized pricing |
| Incomplete | Multi-round/unlimited | No clean closed form; BAYES/ROBUST/EMPIRICAL portfolio |

Determined-cell challengers are exactly: 15% surplus fairness margin for the three
complete finite rows; own-favorable `gamma=0.65` anchor for complete unlimited; and the
fixed buyer-opening `/1.25` / seller-opening `/1.50` empirical corrections for incomplete
T=1. The corrections are fixed constants, not learned models.

### ROBUST v1 fallback policy

ROBUST uses five evenly spaced opponent valuation scenarios over the verified legal range.
For each legal price and grid point it computes own payoff, the best payoff possible had
that scenario been known, and regret as their difference. It selects
`argmin_p max_g regret(p,g)`. The ambiguity grid is static throughout a game and never
reweighted from history.

Pure worst-case/maximin payoff was rejected because it degenerates to the single lowest
valuation scenario: altering the other four points does not change its choice. Minimax
regret uses the grid's composition and changes choices when that composition changes. It
is a conservative fallback decision rule, not an equilibrium solution and not learned.

The formal mechanism and reference implementation now verify that the current negotiation
price domain has no finite upper endpoint. Therefore the finite legal-price grid assumed
by this locked ROBUST v1 rule does not exist for the live mechanism. Routing still selects
ROBUST for the specified underdetermined cells; action execution fails closed until a
separately authorized unbounded-domain ROBUST formulation is specified and tested. A
valuation scale, observed offer range, or historical maximum is not used as a substitute.

BAYES uses a frozen, calibrated rejection-likelihood model and a posterior updated by
Bayes' rule. Its prior is empirical only at `n>=200`, otherwise uniform on the verified
grid. Eligibility requires `n>=200`, completed Platt/isotonic calibration, and held-out
`BSS>=0.10`. A failing BAYES is excluded from live testing. EMPIRICAL is a frozen fitted
response model maximizing expected payoff minus `lambda_OOD*OOD`; growing history is an
input, never in-game retraining.

## Persuasion

- P0 babbling: deployable theory baseline in every no-commitment cell; ignore messages
  and buy iff `p>=1/v`.
- P1 full disclosure: reference only, not an equilibrium or deployable policy.
- P2 commitment benchmark: reference ceiling only; `sigma(buy|H)=1`,
  `sigma(buy|L)=min(p(v-1)/(1-p),1)`, value `min(pv,1)`.
- P3 reputation: behavioral challenger in every repeated cell. It is truthful for the
  first 30% of rounds, then recommends buy with probability `min(0.85,p+0.05)` only while
  observed trust exceeds the historical cell rate; otherwise `min(0.85,p)`.

Buyer belief logic must respect purchase-censored quality. P3 is seller-side and uses only
the seller's observed quality plus public buy/no-buy outcomes.

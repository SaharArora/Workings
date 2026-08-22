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

Production complete-information offers use the current proposer and the number of rounds
remaining, rather than replaying the round-one Alice allocation after every rejection.
Responder acceptance compares the current split with the correct one-step-discounted
continuation share. For the undiscounted unlimited edge case `delta_A=delta_B=1`, theory
does not select a unique split; the symmetric equal split is the explicit operational
convention.

The current incomplete-information API hides the opponent discount and exposes no prior.
Accordingly, the two Bayes-adaptive rows remain theoretical references while the named
production incumbent is `BARGAINING_INCOMPLETE_EQUAL_SPLIT`. This input limitation is
`RESEARCH_BLOCKED`; execution does not enter the emergency fallback.

## Negotiation

No-trade (`V_B<V_A`) is checked first in every cell.

The mechanism price is verified unbounded above; `M` scales valuations and is not a legal
price cap. Mechanism-derived min-max payoff normalization is therefore unavailable.
Negotiation research instead uses the separately labeled clipped statistical transform
documented below; no policy grid or transform clip is interpreted as mechanism support.

| Information | Horizon | Baseline |
|---|---|---|
| Complete | T=1 | Seller posts `V_B`; buyer accepts iff `p<=V_B` |
| Complete | Finite odd | Seller terminal proposer; canonical `p=V_B` |
| Complete | Finite even | Buyer terminal proposer; canonical `p=V_A` (round-10 parity verified) |
| Complete | Unlimited/unknown | No unique theoretical point; operational midpoint `(V_A+V_B)/2` |
| Incomplete, trusted prior | T=1 | Bayes-optimal posted price maximizing `(p-V_A)(1-F_B(p))` |
| Incomplete, ambiguous prior | T=1 | Robust/minimax-regret randomized pricing |
| Incomplete | Multi-round/unlimited | No clean closed form; BAYES/ROBUST/EMPIRICAL portfolio |

The current API exposes no trusted valuation prior or distribution parameters in an
incomplete T=1 state, and the historical parameter grid is not a prior announced to the
agent. Current live routing therefore instantiates the ambiguous-prior row and selects
one-shot ROBUST for both roles. The trusted-prior formula remains distinct from learned
multi-round BAYES and would not use its eligibility gate if a future authoritative prior
were exposed.

Determined-cell challengers are exactly: 15% surplus fairness margin for the three
complete finite rows; own-favorable `gamma=0.65` anchor for complete unlimited; and the
fixed buyer-opening `/1.25` / seller-opening `/1.50` empirical corrections for incomplete
T=1. The corrections are fixed constants, not learned models.

### ROBUST v1 fallback policy

`pi_ROBUST` bounds its own decision set for tractability and conservative
decision-making. It does not claim or assume that the GLEE mechanism itself is bounded.

For seller reservation value `V_S>0`, its candidates are
`A_S={V_S,1.10V_S,1.25V_S,1.50V_S,2V_S}` and buyer-value scenarios are
`{V_S,1.25V_S,1.50V_S,2V_S}`. A scenario buyer accepts iff `p<=v`; seller utility is
`p-V_S` on acceptance and zero otherwise; ex-post best utility is `max(0,v-V_S)`.

For buyer value `V_B>0`, candidates are
`A_B={0,.25V_B,.50V_B,.75V_B,V_B}` and the analogous seller-value scenarios use those
same fractions. A scenario seller accepts iff `p>=v`; buyer utility is `V_B-p` on
acceptance and zero otherwise; ex-post best utility is `max(0,V_B-v)`. Buyer candidates
never deliberately exceed `V_B`.

For every candidate, ROBUST computes regret against each scenario and selects
`argmin_p max_v R(p;v)`. Ties favor agreement probability: lower ask for a seller, higher
offer for a buyer. The scenario set remains static and is never reweighted from history.
If an authoritative positive legal minimum is later exposed it clamps candidates upward,
provided the seller `2V_S` cap or buyer `V_B` cap remains feasible. There is no policy
upper bound inferred from mechanism metadata.

Pure worst-case/maximin payoff was rejected because it degenerates to the single lowest
valuation scenario: altering the other four points does not change its choice. Minimax
regret uses the grid's composition and changes choices when that composition changes. It
is a conservative fallback decision rule, not an equilibrium solution and not learned.

For current offers, v1 uses an explicit simplified continuation rule rather than a latent
belief model: if countering is legal, accept only an individually rational offer at least
as favorable as the chosen ROBUST proposal; otherwise counter with that proposal. If no
counteroffer is legal, accept any individually rational offer and reject otherwise. A
zero-value player without a verified positive scale fails closed as
`ROBUST_SCALE_UNAVAILABLE`.

### Negotiation bounded statistical payoff transform

This transform is not mechanism normalization. For raw own utility `U` and private value
`V_i`, set `S=max(|V_i|,1)`, `C=2S`, then
`Y=(clip(U,-C,C)+C)/(2C)`. Thus `-C -> 0`, `0 -> .5`, `C -> 1`, and more extreme values
clip to the endpoints. Logs and offline reports retain both raw `U` and transformed `Y`,
including whether clipping occurred.

The negotiation promotion estimand is expected clipped scale-adjusted utility `Y`.
Within the unclipped region, `delta_U=4S*delta_Y`; therefore `delta_min=.01` corresponds
locally to `.04S`, about 4% of own valuation scale. This equivalence does not hold after
clipping. Raw expected payoff remains a separately reported diagnostic.

BAYES uses a frozen, calibrated rejection-likelihood model and a posterior updated by
Bayes' rule. Its prior is empirical only at `n>=200`, otherwise uniform on the verified
grid. Eligibility requires `n>=200`, completed Platt/isotonic calibration, and held-out
`BSS>=0.10`. A failing BAYES is excluded from live testing. EMPIRICAL is a frozen fitted
response model maximizing expected payoff minus `lambda_OOD*OOD`; growing history is an
input, never in-game retraining.

## Persuasion

- P0 babbling: deployable theory baseline in every no-commitment cell; ignore messages
  and buy iff `p*v+(1-p)*u >= product_price`. This is exactly `p>=1/v` in the canonical
  normalized `u=0`, `product_price=1` representation.
- P1 full disclosure: reference only, not an equilibrium or deployable policy.
- P2 commitment benchmark: reference ceiling only; `sigma(buy|H)=1`,
  `sigma(buy|L)=min(p(v-1)/(1-p),1)`, value `min(pv,1)`.
- P3 reputation: behavioral challenger in every repeated cell. It is truthful for the
  first 30% of rounds, then recommends buy with probability `min(0.85,p+0.05)` only while
  observed trust exceeds the historical cell rate; otherwise `min(0.85,p)`.

Buyer belief logic must respect purchase-censored quality. P3 is seller-side and uses only
the seller's observed quality plus public buy/no-buy outcomes.
